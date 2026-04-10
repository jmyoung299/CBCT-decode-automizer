import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.batch import parse_batch


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
