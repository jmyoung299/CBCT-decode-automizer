import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.fixtures import discover_vendor_fixture_cases
from dicom_decoder.parser import parse_dicom
from dicom_decoder.plugins import VendorDcXHeaderPlugin


def _create_minimal_dicom(path: Path, patient_id: str) -> bytes:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    sop_instance_uid = generate_uid()
    meta.MediaStorageSOPInstanceUID = sop_instance_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.PatientID = patient_id
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
    return path.read_bytes()


def test_vendor_header_plugin_unwraps_and_parses() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        dcm_path = root / "source.dcm"
        raw = _create_minimal_dicom(dcm_path, patient_id="FIXTURE-PATIENT")
        wrapped = b"VEND\x01\x00\x00\x00" + raw
        wrapped_path = root / "sample.dcx"
        wrapped_path.write_bytes(wrapped)

        result = parse_dicom(
            str(wrapped_path),
            decoders=[VendorDcXHeaderPlugin(name="vendor-dcx-skeleton", header=b"VEND\x01\x00\x00\x00")],
        )
        assert not result.errors
        assert result.unwrap_plugin == "vendor-dcx-skeleton"
        assert result.tags["PatientID"] == "FIXTURE-PATIENT"


def test_discover_vendor_fixture_cases_empty_when_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cases = discover_vendor_fixture_cases(Path(tmp_dir))
        assert cases == []
