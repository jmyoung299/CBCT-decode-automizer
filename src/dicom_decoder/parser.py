from __future__ import annotations

import io
from pathlib import Path

from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from pydicom.uid import UID

from .models import ParseResult
from .plugins import WrapperDecoder, default_decoders
from .sniffer import sniff_and_unwrap
from .validators import validate_pixel_data

KEY_TAGS = {
    "PatientID": "PatientID",
    "PatientName": "PatientName",
    "StudyInstanceUID": "StudyInstanceUID",
    "SeriesInstanceUID": "SeriesInstanceUID",
    "SOPInstanceUID": "SOPInstanceUID",
    "Modality": "Modality",
    "StudyDate": "StudyDate",
    "SeriesDescription": "SeriesDescription",
    "ImagePositionPatient": "ImagePositionPatient",
    "ImageOrientationPatient": "ImageOrientationPatient",
    "PixelSpacing": "PixelSpacing",
    "SliceThickness": "SliceThickness",
}


def _is_encapsulated_transfer_syntax(ts_uid: str | None) -> bool:
    if ts_uid is None:
        return False
    try:
        return UID(ts_uid).is_encapsulated
    except Exception:
        return False


def parse_dicom_bytes(
    payload: bytes,
    *,
    source_name: str = "<memory>",
    decoders: list[WrapperDecoder] | None = None,
) -> ParseResult:
    warnings: list[str] = []
    errors: list[str] = []

    sniff = sniff_and_unwrap(
        payload,
        plugins=default_decoders() if decoders is None else decoders,
    )
    if not sniff.is_dicom:
        return ParseResult(
            path=source_name,
            transfer_syntax_uid=None,
            is_little_endian=True,
            is_implicit_vr=True,
            has_pixel_data=False,
            rows=None,
            columns=None,
            bits_allocated=None,
            number_of_frames=None,
            pixel_data_length=None,
            expected_pixel_data_length=None,
            tags={},
            warnings=warnings,
            errors=[f"Unable to decode DICOM payload (classification: {sniff.classification})."],
            source_format=sniff.classification,
            unwrap_plugin=sniff.plugin_name,
        )

    try:
        ds = dcmread(io.BytesIO(sniff.payload), force=False)
    except InvalidDicomError as exc:
        return ParseResult(
            path=source_name,
            transfer_syntax_uid=None,
            is_little_endian=True,
            is_implicit_vr=True,
            has_pixel_data=False,
            rows=None,
            columns=None,
            bits_allocated=None,
            number_of_frames=None,
            pixel_data_length=None,
            expected_pixel_data_length=None,
            tags={},
            warnings=warnings,
            errors=[f"Invalid DICOM after unwrap: {exc}"],
            source_format=sniff.classification,
            unwrap_plugin=sniff.plugin_name,
        )

    ts_uid = None
    if hasattr(ds, "file_meta") and getattr(ds.file_meta, "TransferSyntaxUID", None):
        ts_uid = str(ds.file_meta.TransferSyntaxUID)

    tags: dict[str, object] = {}
    for out_key, attr in KEY_TAGS.items():
        value = getattr(ds, attr, None)
        if value is not None:
            tags[out_key] = str(value)

    has_pixel_data = "PixelData" in ds
    rows = int(ds.Rows) if getattr(ds, "Rows", None) is not None else None
    cols = int(ds.Columns) if getattr(ds, "Columns", None) is not None else None
    bits_allocated = int(ds.BitsAllocated) if getattr(ds, "BitsAllocated", None) is not None else None

    n_frames_raw = getattr(ds, "NumberOfFrames", None)
    number_of_frames = int(n_frames_raw) if n_frames_raw is not None else (1 if has_pixel_data else None)

    pixel_data_length = len(ds.PixelData) if has_pixel_data else None
    expected_pixel_data_length = None

    if has_pixel_data:
        if pixel_data_length is not None and pixel_data_length <= 0:
            errors.append("PixelData exists but byte payload is empty.")
        ts_encapsulated = _is_encapsulated_transfer_syntax(ts_uid)
        validation_warnings, validation_errors, raw_length, expected_len = validate_pixel_data(
            ds,
            strict_length_check=not ts_encapsulated,
        )
        warnings.extend(validation_warnings)
        pixel_data_length = raw_length
        expected_pixel_data_length = expected_len
        if ts_encapsulated:
            warnings.append(
                "Encapsulated transfer syntax detected; strict raw PixelData byte-length "
                "validation skipped."
            )
        else:
            errors.extend(validation_errors)

    return ParseResult(
        path=source_name,
        transfer_syntax_uid=ts_uid,
        is_little_endian=bool(ds.is_little_endian),
        is_implicit_vr=bool(ds.is_implicit_VR),
        has_pixel_data=has_pixel_data,
        rows=rows,
        columns=cols,
        bits_allocated=bits_allocated,
        number_of_frames=number_of_frames,
        pixel_data_length=pixel_data_length,
        expected_pixel_data_length=expected_pixel_data_length,
        tags=tags,
        warnings=warnings,
        errors=errors,
        source_format=sniff.classification,
        unwrap_plugin=sniff.plugin_name,
    )


def parse_dicom(
    path: str,
    decoders: list[WrapperDecoder] | None = None,
    *,
    dump_unwrapped_path: str | None = None,
) -> ParseResult:
    p = Path(path)
    payload = p.read_bytes()
    if dump_unwrapped_path is not None:
        sniff = sniff_and_unwrap(
            payload,
            plugins=default_decoders() if decoders is None else decoders,
        )
        if sniff.is_dicom:
            dump_path = Path(dump_unwrapped_path)
            dump_path.parent.mkdir(parents=True, exist_ok=True)
            dump_path.write_bytes(sniff.payload)
    return parse_dicom_bytes(
        payload,
        source_name=str(p),
        decoders=decoders,
    )


def parse_bytes(
    payload: bytes,
    *,
    source_id: str = "<memory>",
    decoders: list[WrapperDecoder] | None = None,
) -> ParseResult:
    """Backwards-compatible alias for in-memory parsing."""
    return parse_dicom_bytes(payload, source_name=source_id, decoders=decoders)
