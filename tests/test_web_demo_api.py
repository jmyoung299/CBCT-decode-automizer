import io
import os
from pathlib import Path

from fastapi.testclient import TestClient
from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_decoder.web_demo import create_app


def _build_minimal_dicom_bytes(patient_id: str) -> bytes:
    temp_path = Path("/tmp") / f"{generate_uid()}.dcm"

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    sop_instance_uid = generate_uid()
    meta.MediaStorageSOPInstanceUID = sop_instance_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(temp_path), {}, file_meta=meta, preamble=b"\0" * 128)
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
    ds.save_as(str(temp_path), enforce_file_format=True)
    payload = temp_path.read_bytes()
    temp_path.unlink(missing_ok=True)
    return payload


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_parse_endpoint_returns_results() -> None:
    app = create_app()
    client = TestClient(app)

    dcm_bytes = _build_minimal_dicom_bytes("WEB-DEMO")
    response = client.post(
        "/api/parse",
        files={"file": ("sample.dcm", io.BytesIO(dcm_bytes), "application/dicom")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["result"]["tags"]["PatientID"] == "WEB-DEMO"


def test_upload_parse_endpoint_handles_invalid_payload() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/parse",
        files={"file": ("bad.dcx", io.BytesIO(b"NOT_A_DICOM"), "application/octet-stream")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["result"]["errors"]


def test_cors_allowed_origin_header_is_returned() -> None:
    old = os.environ.get("ALLOWED_ORIGINS")
    os.environ["ALLOWED_ORIGINS"] = "https://frontend.example.com"
    try:
        app = create_app()
        client = TestClient(app)
        response = client.options(
            "/api/parse",
            headers={
                "Origin": "https://frontend.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin") == "https://frontend.example.com"
    finally:
        if old is None:
            os.environ.pop("ALLOWED_ORIGINS", None)
        else:
            os.environ["ALLOWED_ORIGINS"] = old
