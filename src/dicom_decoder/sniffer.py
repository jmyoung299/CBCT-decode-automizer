from __future__ import annotations

from .models import SnifferResult
from .plugins import UnwrapError, WrapperDecoder

DICOM_MAGIC = b"DICM"
STANDARD_PREAMBLE_OFFSET = 128


def detect_raw_dicom(blob: bytes) -> bool:
    """True when bytes look like a standard P10 stream."""
    if len(blob) < STANDARD_PREAMBLE_OFFSET + 4:
        return False
    return blob[STANDARD_PREAMBLE_OFFSET : STANDARD_PREAMBLE_OFFSET + 4] == DICOM_MAGIC


def find_embedded_dicom_preamble(blob: bytes) -> int | None:
    """
    Returns start offset of an embedded P10 preamble, if present.

    Example: wrapper bytes + [128-byte preamble + DICM + dataset].
    """
    marker_offset = blob.find(DICOM_MAGIC)
    if marker_offset < 0:
        return None
    preamble_start = marker_offset - STANDARD_PREAMBLE_OFFSET
    if preamble_start < 0:
        return None
    return preamble_start


def _pick_plugin(blob: bytes, plugins: list[WrapperDecoder]) -> WrapperDecoder | None:
    scored = [(plugin.match(blob), plugin) for plugin in plugins]
    scored = [entry for entry in scored if entry[0] > 0.0]
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def sniff_and_unwrap(blob: bytes, plugins: list[WrapperDecoder] | None = None) -> SnifferResult:
    """Sniff payload bytes and produce a candidate unwrapped DICOM stream."""
    plugins = plugins or []

    if detect_raw_dicom(blob):
        return SnifferResult(
            detected_format="dicom_p10",
            classification="dicom_p10",
            method="direct",
            payload=blob,
            is_dicom=True,
        )

    plugin = _pick_plugin(blob, plugins)
    if plugin is not None:
        try:
            payload = plugin.unwrap(blob)
            return SnifferResult(
                detected_format="wrapped_plugin",
                classification="wrapped_by_plugin",
                method=f"plugin:{plugin.name}",
                plugin_name=plugin.name,
                payload=payload,
                is_dicom=detect_raw_dicom(payload),
            )
        except UnwrapError:
            # Continue to embedded detection fallback.
            pass

    embedded_start = find_embedded_dicom_preamble(blob)
    if embedded_start is not None:
        payload = blob[embedded_start:]
        return SnifferResult(
            detected_format="embedded_dicom_magic",
            classification="embedded_dicom_p10",
            method="embedded",
            payload=payload,
            is_dicom=detect_raw_dicom(payload),
        )

    return SnifferResult(
        detected_format="unknown",
        classification="encrypted_or_unknown",
        method="none",
        payload=blob,
        is_dicom=False,
    )
