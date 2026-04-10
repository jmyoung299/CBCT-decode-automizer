import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.golden import run_vendor_fixture_suite
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


def test_run_vendor_fixture_suite_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        case = root / "case-001"
        case.mkdir(parents=True)

        raw = _create_minimal_dicom(case / "source.dcm", patient_id="GOLDEN-1")
        (case / "wrapped.dcx").write_bytes(b"VENDHDR" + raw)
        (case / "expected.json").write_text(
            '{\n'
            '  "plugin": {"name": "vendor-case", "header_ascii": "VENDHDR"},\n'
            '  "expected": {"PatientID": "GOLDEN-1"}\n'
            '}\n',
            encoding="utf-8",
        )

        summary = run_vendor_fixture_suite(root)
        assert summary.total_cases == 1
        assert summary.passed_cases == 1
        assert summary.failed_cases == 0


def test_run_vendor_fixture_suite_with_custom_plugin_map() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        case = root / "case-002"
        case.mkdir(parents=True)

        raw = _create_minimal_dicom(case / "source.dcm", patient_id="GOLDEN-2")
        (case / "wrapped.dcx").write_bytes(b"CUSTOM1" + raw)
        (case / "expected.json").write_text(
            '{\n'
            '  "plugin": {"name": "custom-plugin"},\n'
            '  "expected": {"PatientID": "GOLDEN-2"}\n'
            '}\n',
            encoding="utf-8",
        )

        plugin_map = {
            "custom-plugin": VendorDcXHeaderPlugin(name="custom-plugin", header=b"CUSTOM1")
        }
        summary = run_vendor_fixture_suite(root, plugin_map=plugin_map)
        assert summary.total_cases == 1
        assert summary.passed_cases == 1
        assert summary.failed_cases == 0
