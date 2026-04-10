from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .models import ParseResult
from .parser import parse_dicom_bytes


class BlobReader(Protocol):
    def read_bytes(self, uri: str) -> bytes:
        """Read object bytes from a URI-like location."""


@dataclass
class IngestedObjectResult:
    uri: str
    result: ParseResult

    def to_dict(self) -> dict[str, object]:
        payload = self.result.to_dict()
        payload["uri"] = self.uri
        return payload


@dataclass
class S3ParseSummary:
    scanned_objects: int
    parsed_objects: int
    failed_objects: int
    results: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "scanned_objects": self.scanned_objects,
            "parsed_objects": self.parsed_objects,
            "failed_objects": self.failed_objects,
            "results": self.results,
        }


def parse_uris(
    uris: list[str],
    reader: BlobReader,
    *,
    parser: Callable[..., ParseResult] = parse_dicom_bytes,
) -> list[IngestedObjectResult]:
    results: list[IngestedObjectResult] = []
    for uri in uris:
        blob = reader.read_bytes(uri)
        parsed = parser(blob, source_name=uri)
        results.append(IngestedObjectResult(uri=uri, result=parsed))
    return results


def parse_object_blobs(objects: list[tuple[str, bytes]]) -> list[IngestedObjectResult]:
    class _InlineReader:
        def __init__(self, mapping: dict[str, bytes]) -> None:
            self._mapping = mapping

        def read_bytes(self, uri: str) -> bytes:
            return self._mapping[uri]

    mapping = {uri: blob for uri, blob in objects}
    return parse_uris([uri for uri, _ in objects], reader=_InlineReader(mapping))


@dataclass
class ObjectBlob:
    uri: str
    blob: bytes


def parse_s3_objects(objects: list[tuple[str, bytes]] | list[ObjectBlob]) -> S3ParseSummary:
    tuples: list[tuple[str, bytes]] = []
    for item in objects:
        if isinstance(item, ObjectBlob):
            tuples.append((item.uri, item.blob))
        else:
            tuples.append(item)

    parsed = parse_object_blobs(tuples)
    failed = 0
    results: list[dict[str, object]] = []
    for item in parsed:
        row = item.to_dict()
        results.append(row)
        errors = row.get("errors", [])
        if isinstance(errors, list) and errors:
            failed += 1

    return S3ParseSummary(
        scanned_objects=len(parsed),
        parsed_objects=len(parsed) - failed,
        failed_objects=failed,
        results=results,
    )

