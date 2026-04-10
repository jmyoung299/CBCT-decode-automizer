import json
import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.cli_golden import main


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


def test_cli_golden_writes_output_file(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        case = root / "case-001"
        case.mkdir(parents=True)

        raw = _create_minimal_dicom(case / "source.dcm", patient_id="GOLDEN-CLI")
        (case / "wrapped.dcx").write_bytes(b"VENDHDR" + raw)
        (case / "expected.json").write_text(
            json.dumps(
                {
                    "plugin": {"name": "vendor-case", "header_ascii": "VENDHDR"},
                    "expected": {"PatientID": "GOLDEN-CLI"},
                }
            ),
            encoding="utf-8",
        )

        out_path = root / "golden.json"
        monkeypatch.setattr(
            "sys.argv",
            [
                "dicom-golden",
                str(root),
                "--output",
                str(out_path),
            ],
        )
        main()

        assert out_path.exists()
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert payload["total_cases"] == 1
        assert payload["passed_cases"] == 1
