import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.batch import parse_batch
from dicom_decoder.ingest import parse_s3_objects


def _create_minimal_dicom(path: Path, patient_id: str) -> None:
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


def test_parse_batch_collects_mixed_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _create_minimal_dicom(root / "a.dcm", patient_id="A")
        _create_minimal_dicom(root / "b.dicom", patient_id="B")
        (root / "bad.dcx").write_bytes(b"NOT_A_DICOM")

        summary = parse_batch(str(root))
        assert summary.scanned_files == 3
        assert summary.parsed_files == 2
        assert summary.failed_files == 1


def test_parse_many_alias_matches_parse_batch() -> None:
    from dicom_decoder.batch import parse_many

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _create_minimal_dicom(root / "a.dcm", patient_id="A")
        batch_summary = parse_batch(str(root))
        many_summary = parse_many(str(root))
        assert batch_summary.total_files == many_summary.total_files
        assert batch_summary.parsed_ok == many_summary.parsed_ok


def test_parse_s3_objects_reports_results() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        dcm_path = root / "a.dcm"
        _create_minimal_dicom(dcm_path, patient_id="A")
        bad_blob = b"NOT_A_DICOM"
        dcm_blob = dcm_path.read_bytes()

        summary = parse_s3_objects(
            [
                ("s3://bucket/a.dcm", dcm_blob),
                ("s3://bucket/bad.dcx", bad_blob),
            ]
        )
        assert summary.scanned_objects == 2
        assert summary.parsed_objects == 1
        assert summary.failed_objects == 1
