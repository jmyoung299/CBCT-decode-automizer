from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .parser import parse_dicom
from .plugins import WrapperDecoder


@dataclass
class BatchResult:
    total_files: int
    parsed_ok: int
    parsed_with_errors: int
    results: list[dict[str, object]]
    error_files: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def scanned_files(self) -> int:
        return self.total_files

    @property
    def parsed_files(self) -> int:
        return self.parsed_ok

    @property
    def failed_files(self) -> int:
        return self.parsed_with_errors


def discover_input_files(path: str, recursive: bool = True) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p]

    if not p.exists():
        return []

    extensions = {".dcm", ".dicom", ".dcm30", ".dcx"}
    iterator = p.rglob("*") if recursive else p.glob("*")
    files: list[Path] = []
    for candidate in sorted(iterator):
        if candidate.is_file() and candidate.suffix.lower() in extensions:
            files.append(candidate)
    return files


def parse_batch(
    path: str,
    decoders: list[WrapperDecoder] | None = None,
    recursive: bool = True,
) -> BatchResult:
    files = discover_input_files(path, recursive=recursive)
    results: list[dict[str, object]] = []
    error_files: list[str] = []
    ok_count = 0

    for file_path in files:
        parsed = parse_dicom(str(file_path), decoders=decoders)
        parsed_dict = parsed.to_dict()
        results.append(parsed_dict)
        if parsed.errors:
            error_files.append(str(file_path))
        else:
            ok_count += 1

    return BatchResult(
        total_files=len(files),
        parsed_ok=ok_count,
        parsed_with_errors=len(error_files),
        results=results,
        error_files=error_files,
    )


def parse_directory(
    path: str,
    decoders: list[WrapperDecoder] | None = None,
    recursive: bool = True,
) -> BatchResult:
    """Backwards-compatible alias for older callers."""
    return parse_batch(path=path, decoders=decoders, recursive=recursive)
