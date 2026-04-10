import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.parser import parse_dicom


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
