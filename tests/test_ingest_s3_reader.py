import tempfile
from pathlib import Path

from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.ingest import S3Reader, parse_s3_prefix


class _FakeS3Client:
    def __init__(self, data: dict[str, bytes]) -> None:
        self._data = data

    def get_paginator(self, _operation_name: str):
        data_keys = list(self._data.keys())

        class _Paginator:
            def __init__(self, keys: list[str]) -> None:
                self._keys = keys

            def paginate(self, Bucket: str, Prefix: str):
                contents = [{"Key": key} for key in self._keys if key.startswith(Prefix)]
                return [{"Contents": contents}] if contents else [{"Contents": []}]

        return _Paginator(data_keys)

    def get_object(self, Bucket: str, Key: str):
        return {"Body": _FakeBody(self._data[Key])}


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


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


def test_parse_s3_prefix_with_fake_client() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        dcm_path = root / "input.dcm"
        _create_minimal_dicom(dcm_path, patient_id="S3-PATIENT")
        payload = dcm_path.read_bytes()

        fake_client = _FakeS3Client(
            {
                "studies/a.dcm": payload,
                "studies/b.dcx": b"NOT_A_DICOM",
            }
        )
        reader = S3Reader(bucket="test-bucket", client=fake_client)
        summary = parse_s3_prefix(reader, prefix="studies/")

        assert summary.scanned_objects == 2
        assert summary.parsed_objects == 1
        assert summary.failed_objects == 1
