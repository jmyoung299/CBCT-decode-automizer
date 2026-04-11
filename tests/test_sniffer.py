from dicom_decoder.plugins import (
    PrefixBytesWrapperPlugin,
    UnwrapError,
    VendorDcXHeaderPlugin,
)
from dicom_decoder.sniffer import detect_raw_dicom, find_embedded_dicom_preamble, sniff_and_unwrap


def test_detect_raw_dicom_at_standard_offset() -> None:
    data = (b"\x00" * 128) + b"DICM" + b"\x02\x00\x00\x00"
    assert detect_raw_dicom(data)


def test_find_embedded_dicom_preamble() -> None:
    payload = (b"\x00" * 128) + b"DICM" + b"\x08\x00\x00\x00"
    wrapped = b"HEADER" + payload
    assert find_embedded_dicom_preamble(wrapped) == len(b"HEADER")


def test_sniff_and_unwrap_returns_direct_dicom() -> None:
    data = (b"\x00" * 128) + b"DICM" + b"\x02\x00\x00\x00"
    result = sniff_and_unwrap(data, plugins=[])
    assert result.classification == "dicom_p10"
    assert result.method == "direct"
    assert result.payload == data


def test_sniff_and_unwrap_returns_embedded_slice() -> None:
    payload = (b"\x00" * 128) + b"DICM" + b"\x08\x00\x00\x00"
    wrapped = b"WRAPPED" + payload + b"TAIL"
    result = sniff_and_unwrap(wrapped, plugins=[])
    assert result.classification == "embedded_dicom_p10"
    assert result.method == "embedded"
    assert result.payload == payload + b"TAIL"


def test_prefix_plugin_can_unwrap() -> None:
    payload = (b"\x00" * 128) + b"DICM" + b"\x02\x00\x00\x00"
    wrapped = b"DCX1" + payload
    plugin = PrefixBytesWrapperPlugin(name="dcx-v1", magic_prefix=b"DCX1", strip_bytes=4)
    result = sniff_and_unwrap(wrapped, plugins=[plugin])
    assert result.classification == "wrapped_by_plugin"
    assert result.method == "plugin:dcx-v1"
    assert result.plugin_name == "dcx-v1"
    assert result.payload == payload


def test_prefix_plugin_raises_for_short_payload() -> None:
    plugin = PrefixBytesWrapperPlugin(name="dcx-v1", magic_prefix=b"DCX1", strip_bytes=100)
    wrapped = b"DCX1SHORT"
    try:
        plugin.unwrap(wrapped)
    except UnwrapError:
        return
    raise AssertionError("Expected UnwrapError")


def test_vendor_header_plugin_can_unwrap() -> None:
    payload = (b"\x00" * 128) + b"DICM" + b"\x02\x00\x00\x00"
    wrapped = b"VENDX1" + payload
    plugin = VendorDcXHeaderPlugin(
        name="vendx-fixture",
        header=b"VENDX1",
    )
    result = sniff_and_unwrap(wrapped, plugins=[plugin])
    assert result.is_dicom
    assert result.plugin_name == "vendx-fixture"
    assert result.classification == "wrapped_by_plugin"
