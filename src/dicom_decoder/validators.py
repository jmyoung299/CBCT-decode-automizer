from __future__ import annotations

from pydicom.dataset import FileDataset


def _safe_int(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_pixel_data(ds: FileDataset) -> tuple[list[str], list[str], int | None]:
    """
    Validate core pixel-data consistency and return (warnings, errors, expected_bytes).
    """
    warnings: list[str] = []
    errors: list[str] = []

    if "PixelData" not in ds:
        warnings.append("No PixelData present (metadata-only object or incomplete file).")
        return warnings, errors, None

    rows = _safe_int(getattr(ds, "Rows", None))
    cols = _safe_int(getattr(ds, "Columns", None))
    bits_allocated = _safe_int(getattr(ds, "BitsAllocated", None))
    samples_per_pixel = _safe_int(getattr(ds, "SamplesPerPixel", None))
    number_of_frames = _safe_int(getattr(ds, "NumberOfFrames", None)) or 1

    if rows is None or cols is None:
        errors.append("PixelData exists but Rows/Columns missing.")
        return warnings, errors, None
    if bits_allocated is None:
        warnings.append("PixelData exists but BitsAllocated missing.")
        return warnings, errors, None
    if samples_per_pixel is None:
        samples_per_pixel = 1
        warnings.append("SamplesPerPixel missing; assuming 1.")
    if number_of_frames <= 0:
        errors.append("NumberOfFrames must be >= 1 when present.")
        return warnings, errors, None

    # DICOM packs 1-bit pixels; otherwise bytes per sample is bits/8.
    total_samples = rows * cols * samples_per_pixel * number_of_frames
    if bits_allocated == 1:
        expected_len = (total_samples + 7) // 8
    else:
        if bits_allocated % 8 != 0:
            warnings.append(
                f"BitsAllocated={bits_allocated} is not byte-aligned; exact byte length check skipped."
            )
            return warnings, errors, None
        expected_len = total_samples * (bits_allocated // 8)

    actual_len = len(ds.PixelData)
    if actual_len < expected_len:
        errors.append(
            "PixelData shorter than expected: "
            f"expected>={expected_len} bytes, got {actual_len}."
        )
    elif actual_len > expected_len:
        warnings.append(
            "PixelData larger than expected by simple geometry check: "
            f"expected {expected_len}, got {actual_len}. "
            "This can be valid for encapsulated/compressed transfer syntaxes."
        )

    return warnings, errors, expected_len
