from __future__ import annotations

from pydicom.dataset import FileDataset


def _safe_int(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def expected_pixel_data_length_bytes(
    *,
    rows: int | None,
    cols: int | None,
    bits_allocated: int | None,
    samples_per_pixel: int | None,
    number_of_frames: int | None,
) -> int | None:
    if rows is None or cols is None or bits_allocated is None:
        return None

    if bits_allocated <= 0:
        return None

    samples = samples_per_pixel if samples_per_pixel is not None else 1
    frames = number_of_frames if number_of_frames is not None else 1
    if samples <= 0 or frames <= 0:
        return None

    total_samples = rows * cols * samples * frames
    if bits_allocated == 1:
        return (total_samples + 7) // 8

    if bits_allocated % 8 != 0:
        return None

    return total_samples * (bits_allocated // 8)


def validate_pixel_data(
    ds: FileDataset,
    *,
    strict_length_check: bool,
) -> tuple[list[str], list[str], int | None, int | None]:
    """
    Validate pixel-data consistency and return:
    (warnings, errors, raw_length_bytes, expected_length_bytes).
    """
    warnings: list[str] = []
    errors: list[str] = []

    if "PixelData" not in ds:
        warnings.append("No PixelData present (metadata-only object or incomplete file).")
        return warnings, errors, None, None

    rows = _safe_int(getattr(ds, "Rows", None))
    cols = _safe_int(getattr(ds, "Columns", None))
    bits_allocated = _safe_int(getattr(ds, "BitsAllocated", None))
    samples_per_pixel = _safe_int(getattr(ds, "SamplesPerPixel", None))
    number_of_frames = _safe_int(getattr(ds, "NumberOfFrames", None))

    if rows is None or cols is None:
        errors.append("PixelData exists but Rows/Columns missing.")
    if bits_allocated is None:
        warnings.append("PixelData exists but BitsAllocated missing.")
    if number_of_frames is not None and number_of_frames <= 0:
        errors.append("NumberOfFrames must be >= 1 when present.")
    if samples_per_pixel is None:
        warnings.append("SamplesPerPixel missing; assuming 1.")

    raw_length = len(ds.PixelData)
    expected_length = expected_pixel_data_length_bytes(
        rows=rows,
        cols=cols,
        bits_allocated=bits_allocated,
        samples_per_pixel=samples_per_pixel,
        number_of_frames=number_of_frames,
    )
    if strict_length_check and expected_length is not None and raw_length != expected_length:
        errors.append(
            f"PixelData length mismatch: expected {expected_length} bytes, got {raw_length}."
        )

    return warnings, errors, raw_length, expected_length
