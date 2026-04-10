from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .parser import parse_dicom
from .plugins import WrapperDecoder


@dataclass
class BatchResult:
    scanned_files: int
    parsed_files: int
    failed_files: int
    results: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def discover_input_files(path: str) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p]

    if not p.exists():
        return []

    extensions = {".dcm", ".dicom", ".dcm30", ".dcx"}
    files: list[Path] = []
    for candidate in sorted(p.rglob("*")):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() in extensions:
            files.append(candidate)
    return files


def parse_batch(path: str, decoders: list[WrapperDecoder] | None = None) -> BatchResult:
    files = discover_input_files(path)
    results: list[dict[str, object]] = []

    failed = 0
    for file_path in files:
        parsed = parse_dicom(str(file_path), decoders=decoders)
        if parsed.errors:
            failed += 1
        results.append(parsed.to_dict())

    return BatchResult(
        scanned_files=len(files),
        parsed_files=len(files) - failed,
        failed_files=failed,
        results=results,
    )
