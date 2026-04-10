import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.parser import parse_dicom
from dicom_decoder.plugins import PrefixBytesWrapperPlugin


def _create_minimal_dicom(path: Path) -> None:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    sop_instance_uid = generate_uid()
    meta.MediaStorageSOPInstanceUID = sop_instance_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.PatientID = "12345"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = sop_instance_uid
    ds.Modality = "CT"
    ds.Rows = 2
    ds.Columns = 2
    ds.BitsAllocated = 8
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 0
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelData = b"\x00\x01\x02\x03"
    ds.save_as(str(path), enforce_file_format=True)


def test_parse_dicom_reads_embedded_candidate() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        dicom_path = Path(tmp_dir) / "input.dcm"
        _create_minimal_dicom(dicom_path)

        raw = dicom_path.read_bytes()
        wrapped = b"WRAPPER_HEADER" + raw
        wrapped_path = Path(tmp_dir) / "input.dcx"
        wrapped_path.write_bytes(wrapped)

        result = parse_dicom(str(wrapped_path), decoders=[])

        assert not result.errors
        assert result.source_format == "embedded_dicom_p10"
        assert result.unwrap_plugin is None
        assert result.has_pixel_data is True
        assert result.tags["PatientID"] == "12345"


def test_parse_dicom_rejects_unknown_payload() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        payload_path = Path(tmp_dir) / "unknown.dcx"
        payload_path.write_bytes(b"NOT_A_DICOM_FILE")

        result = parse_dicom(str(payload_path), decoders=[])
        assert result.errors
    assert result.source_format == "encrypted_or_unknown"


def test_parse_dicom_reports_pixel_length_mismatch() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        dicom_path = Path(tmp_dir) / "bad_pixel_length.dcm"
        _create_minimal_dicom(dicom_path)
        # Corrupt the pixel payload length from 4 to 3 bytes.
        ds_bytes = dicom_path.read_bytes()
        dicom_path.write_bytes(ds_bytes[:-1])

        result = parse_dicom(str(dicom_path), decoders=[])

        assert result.has_pixel_data
        assert result.pixel_data_length == 3
        assert any("PixelData length mismatch" in err for err in result.errors)


def test_parse_dicom_with_prefix_plugin() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        dicom_path = Path(tmp_dir) / "source.dcm"
        _create_minimal_dicom(dicom_path)

        raw = dicom_path.read_bytes()
        wrapped = b"DCX1" + raw
        wrapped_path = Path(tmp_dir) / "wrapped.dcx"
        wrapped_path.write_bytes(wrapped)

        result = parse_dicom(
            str(wrapped_path),
            decoders=[PrefixBytesWrapperPlugin(name="dcx-v1", magic_prefix=b"DCX1", strip_bytes=4)],
        )

        assert not result.errors
        assert result.unwrap_plugin == "dcx-v1"
        assert result.source_format == "wrapped_by_plugin"
        assert result.has_pixel_data is True


def test_parse_bytes_matches_parse_dicom_for_raw_input() -> None:
    from dicom_decoder.parser import parse_bytes

    with tempfile.TemporaryDirectory() as tmp_dir:
        dicom_path = Path(tmp_dir) / "raw.dcm"
        _create_minimal_dicom(dicom_path)
        raw = dicom_path.read_bytes()

        by_path = parse_dicom(str(dicom_path), decoders=[])
        by_bytes = parse_bytes(raw, source_id="memory://raw.dcm", decoders=[])

        assert by_path.transfer_syntax_uid == by_bytes.transfer_syntax_uid
        assert by_path.tags == by_bytes.tags
        assert by_bytes.path == "memory://raw.dcm"
