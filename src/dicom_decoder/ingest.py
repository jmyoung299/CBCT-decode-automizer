from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable, Protocol

from .models import ParseResult
from .parser import parse_dicom_bytes


class BlobReader(Protocol):
    def read_bytes(self, uri: str) -> bytes:
        """Read object bytes from a URI-like location."""


@dataclass
class S3ObjectRef:
    bucket: str
    key: str

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


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


S3IngestResult = S3ParseSummary


class S3Reader:
    """
    boto3-backed object reader for S3 URIs in the form s3://bucket/key.
    """

    def __init__(self, bucket: str, client: object) -> None:
        self.bucket = bucket
        self._s3_client = client

    def read_bytes(self, uri: str) -> bytes:
        if not uri.startswith("s3://"):
            raise ValueError(f"Unsupported URI for S3Reader: {uri}")
        bucket_and_key = uri[5:]
        if "/" not in bucket_and_key:
            raise ValueError(f"Invalid S3 URI: {uri}")
        bucket, key = bucket_and_key.split("/", 1)
        response = self._s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        if hasattr(body, "read"):
            return body.read()
        if isinstance(body, (bytes, bytearray)):
            return bytes(body)
        raise ValueError("Unsupported S3 body type returned by client.")

    def list_refs(self, *, prefix: str = "") -> list[S3ObjectRef]:
        return list_s3_objects(self._s3_client, bucket=self.bucket, prefix=prefix)


def list_s3_objects(
    s3_client: object,
    *,
    bucket: str,
    prefix: str = "",
) -> list[S3ObjectRef]:
    """
    List object references under a bucket/prefix using paginator when available.
    """
    refs: list[S3ObjectRef] = []
    paginator = None
    if hasattr(s3_client, "get_paginator"):
        paginator = s3_client.get_paginator("list_objects_v2")

    if paginator is not None:
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            for item in page.get("Contents", []):
                key = item.get("Key")
                if isinstance(key, str):
                    refs.append(S3ObjectRef(bucket=bucket, key=key))
        return refs

    # Fallback for simple/mocked clients without paginator.
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    for item in response.get("Contents", []):
        key = item.get("Key")
        if isinstance(key, str):
            refs.append(S3ObjectRef(bucket=bucket, key=key))
    return refs


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


def parse_s3_prefix(
    reader: S3Reader | None = None,
    prefix: str = "",
    *,
    s3_client: object | None = None,
    bucket: str | None = None,
) -> S3ParseSummary:
    """
    Enumerate objects from S3 and parse each object directly from bytes.

    Supports two call styles:
    1) parse_s3_prefix(reader, prefix="studies/")
    2) parse_s3_prefix(prefix="studies/", s3_client=client, bucket="my-bucket")
    """
    if reader is None:
        if s3_client is None or bucket is None:
            raise ValueError("Provide either reader or both s3_client and bucket.")
        reader = S3Reader(bucket=bucket, client=s3_client)

    refs = reader.list_refs(prefix=prefix)
    uris = [ref.uri for ref in refs]
    parsed = parse_uris(uris, reader=reader)

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

