from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SnifferResult:
    detected_format: str
    classification: str
    method: str
    payload: bytes
    is_dicom: bool
    plugin_name: str | None = None


@dataclass
class ParseResult:
    path: str
    transfer_syntax_uid: str | None
    is_little_endian: bool
    is_implicit_vr: bool
    has_pixel_data: bool
    rows: int | None
    columns: int | None
    bits_allocated: int | None
    number_of_frames: int | None
    pixel_data_length: int | None
    expected_pixel_data_length: int | None
    tags: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    source_format: str
    unwrap_plugin: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Bytes are kept internal; JSON payload should stay serializable.
        return data
