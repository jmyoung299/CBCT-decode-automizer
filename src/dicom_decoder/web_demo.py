from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

from .parser import parse_dicom_bytes


@dataclass
class ParseJob:
    job_id: str
    filename: str
    created_at: str
    result: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "created_at": self.created_at,
            "result": self.result,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_payload(raw: bytes, filename: str) -> dict[str, object]:
    parsed = parse_dicom_bytes(raw, source_name=filename)
    result = parsed.to_dict()
    return {"ok": not bool(parsed.errors), "result": result}


def _dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DICOM Decoder Demo</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; max-width: 1000px; }
    .row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; flex: 1; min-width: 300px; }
    button { padding: 0.5rem 1rem; cursor: pointer; }
    pre { background: #f8f8f8; border-radius: 6px; padding: 1rem; overflow: auto; max-height: 420px; }
    .muted { color: #666; font-size: 0.95rem; }
  </style>
</head>
<body>
  <h1>DICOM Decoder Web Demo</h1>
  <p class="muted">Upload .dcm/.dicom/.dcx files and inspect parse output.</p>
  <div class="row">
    <div class="card">
      <h3>Upload file</h3>
      <form id="upload-form">
        <input type="file" id="file" name="file" required />
        <button type="submit">Upload & Parse</button>
      </form>
      <p id="status" class="muted"></p>
    </div>
    <div class="card">
      <h3>Recent jobs</h3>
      <button id="refresh-jobs">Refresh</button>
      <pre id="jobs"></pre>
    </div>
  </div>
  <div class="card" style="margin-top:1rem;">
    <h3>Latest result</h3>
    <pre id="result"></pre>
  </div>
  <script>
    const statusEl = document.getElementById("status");
    const resultEl = document.getElementById("result");
    const jobsEl = document.getElementById("jobs");
    const formEl = document.getElementById("upload-form");

    async function refreshJobs() {
      const res = await fetch("/api/jobs");
      const payload = await res.json();
      jobsEl.textContent = JSON.stringify(payload, null, 2);
    }

    document.getElementById("refresh-jobs").addEventListener("click", refreshJobs);

    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      const fileInput = document.getElementById("file");
      if (!fileInput.files || fileInput.files.length === 0) {
        statusEl.textContent = "Select a file first.";
        return;
      }
      const data = new FormData();
      data.append("file", fileInput.files[0]);
      statusEl.textContent = "Uploading...";
      try {
        const res = await fetch("/api/upload", { method: "POST", body: data });
        const payload = await res.json();
        resultEl.textContent = JSON.stringify(payload, null, 2);
        statusEl.textContent = "Upload complete.";
        await refreshJobs();
      } catch (err) {
        statusEl.textContent = "Upload failed.";
      }
    });

    refreshJobs();
  </script>
</body>
</html>
"""


def create_app() -> FastAPI:
    app = FastAPI(title="DICOM Decoder Demo API")
    jobs: dict[str, ParseJob] = {}
    jobs_lock = Lock()

    @app.get("/", response_class=HTMLResponse)
    @app.get("/api/ui", response_class=HTMLResponse)
    def dashboard() -> str:
        return _dashboard_html()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/jobs")
    def list_jobs() -> dict[str, object]:
        with jobs_lock:
            ordered = sorted(jobs.values(), key=lambda item: item.created_at, reverse=True)
            return {"count": len(ordered), "jobs": [job.to_dict() for job in ordered[:25]]}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        with jobs_lock:
            job = jobs.get(job_id)
        if job is None:
            return {"error": "job_not_found", "job_id": job_id}
        return job.to_dict()

    @app.post("/api/parse")
    async def parse(file: UploadFile = File(...)) -> dict[str, object]:
        raw = await file.read()
        filename = file.filename or "upload.bin"
        return _parse_payload(raw, filename)

    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)) -> dict[str, object]:
        raw = await file.read()
        filename = file.filename or "upload.bin"
        parsed = parse_dicom_bytes(raw, source_name=filename)
        job = ParseJob(
            job_id=uuid4().hex,
            filename=filename,
            created_at=_now_iso(),
            result=parsed.to_dict(),
        )
        with jobs_lock:
            jobs[job.job_id] = job
        return job.to_dict()

    @app.get("/api/demo/sample")
    def parse_sample_fixture() -> dict[str, object]:
        sample = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "vendor-cases"
            / "sample-case"
            / "wrapped.dcx"
        )
        if not sample.exists():
            return {"ok": False, "error": "sample_not_found"}
        return _parse_payload(sample.read_bytes(), sample.name)

    return app


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Run DICOM Decoder web demo.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "dicom_decoder.web_demo:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )

