from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
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
    *{box-sizing:border-box}
    body{font-family:Inter,system-ui,Arial,sans-serif;margin:0;background:#f9fafb;color:#111827}
    .page{max-width:720px;margin:0 auto;padding:32px 20px 64px}
    h1{margin:0 0 4px;font-size:1.75rem;font-weight:700}
    .muted{color:#6b7280;font-size:.9rem}

    /* stepper */
    .stepper{position:relative;display:flex;justify-content:space-between;margin:0 0 24px;padding:0 4px}
    .step{display:flex;flex-direction:column;align-items:center;gap:6px;z-index:1;min-width:80px}
    .step-circle{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;
      font-size:.85rem;font-weight:600;border:2px solid #d1d5db;background:#fff;color:#9ca3af;transition:all .25s}
    .step.active .step-circle{border-color:#2563eb;background:#2563eb;color:#fff}
    .step.completed .step-circle{border-color:#16a34a;background:#16a34a;color:#fff}
    .step-label{font-size:.78rem;font-weight:500;color:#9ca3af;text-align:center;white-space:nowrap;transition:color .25s}
    .step.active .step-label{color:#2563eb;font-weight:600}
    .step.completed .step-label{color:#16a34a}
    .step-track{position:absolute;top:16px;left:44px;right:44px;height:2px;background:#e5e7eb;z-index:0}
    .step-fill{height:100%;background:#16a34a;transition:width .4s}

    /* prompt */
    .prompt{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:16px 20px;margin-bottom:20px}
    .prompt-badge{display:inline-block;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
      color:#2563eb;background:#dbeafe;border-radius:4px;padding:2px 8px;margin-bottom:6px}
    .prompt h2{margin:0 0 4px;font-size:1.1rem;font-weight:600;color:#1e3a5f}
    .prompt p{margin:0;font-size:.9rem;color:#3b6fa0;line-height:1.5}

    .card{border:1px solid #d1d5db;border-radius:10px;padding:20px;background:#fff;animation:fadeSlide .3s ease}
    @keyframes fadeSlide{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}

    /* drop zone */
    .drop-zone{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;
      padding:40px 20px;border:2px dashed #c7d2fe;border-radius:10px;background:#f8faff;cursor:pointer;transition:border-color .2s,background .2s}
    .drop-zone:hover{border-color:#818cf8;background:#eef2ff}
    .drop-zone svg{color:#6366f1}
    .drop-zone span{font-size:.95rem;color:#4b5563;text-align:center}

    /* selected file */
    .file-info{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:16px;color:#166534}
    .actions{display:flex;gap:10px;flex-wrap:wrap}
    .btn{border:none;border-radius:8px;padding:10px 18px;font-size:.9rem;font-weight:500;cursor:pointer;transition:background .15s,opacity .15s}
    .btn-p{background:#2563eb;color:#fff}.btn-p:hover{background:#1d4ed8}
    .btn-s{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1}.btn-s:hover{background:#e2e8f0}
    .btn:disabled{opacity:.55;cursor:default}

    .status{margin:8px 0 0;font-size:.88rem}
    .status-ok{color:#16a34a}.status-err{color:#dc2626}

    /* result */
    .r-header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}
    .r-fname{margin:0 0 2px;font-size:1.05rem}
    .r-time{font-size:.82rem;color:#6b7280}
    .badge{display:inline-block;font-size:.78rem;font-weight:600;padding:3px 10px;border-radius:12px;white-space:nowrap}
    .badge-ok{background:#dcfce7;color:#166534}.badge-err{background:#fee2e2;color:#991b1b}
    .meta-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-bottom:16px}
    .meta-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:8px 12px}
    .meta-label{display:block;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em;color:#6b7280;margin-bottom:2px}
    .meta-val{font-size:.88rem;color:#111827;word-break:break-all}
    table{width:100%;border-collapse:collapse;font-size:.88rem}
    th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #e5e7eb}
    th{font-weight:600;color:#6b7280;font-size:.78rem;text-transform:uppercase;letter-spacing:.03em}
    .sec{margin-top:16px}.sec h4{margin:0 0 8px;font-size:.9rem;font-weight:600}
    ul.msgs{margin:0;padding-left:20px;font-size:.88rem}
    .w-warn li{color:#a16207}.w-err li{color:#dc2626}
    .sec-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
    .sec-hdr h2{margin:0;font-size:1.1rem}
    .btn-sm{padding:6px 12px;font-size:.82rem}
    .badge-sm{font-size:.72rem;padding:2px 8px;border-radius:12px;display:inline-block;font-weight:600}
    .hide{display:none}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <h1>DICOM Decoder Web Demo</h1>
      <p class="muted">Upload and parse DICOM files step by step</p>
    </header>

    <div class="stepper">
      <div class="step active" id="s1"><div class="step-circle">1</div><div class="step-label">Select file</div></div>
      <div class="step" id="s2"><div class="step-circle">2</div><div class="step-label">Upload &amp; parse</div></div>
      <div class="step" id="s3"><div class="step-circle">3</div><div class="step-label">Review results</div></div>
      <div class="step-track"><div class="step-fill" id="track-fill" style="width:0%"></div></div>
    </div>

    <div class="prompt" id="prompt">
      <div class="prompt-badge" id="prompt-badge">Step 1 of 3</div>
      <h2 id="prompt-title">Select a DICOM file</h2>
      <p id="prompt-desc">Choose a .dcm, .dicom, or .dcx file from your computer. The parser supports standard DICOM P10 files as well as proprietary vendor-wrapped formats.</p>
    </div>

    <!-- Step 1 -->
    <div class="card" id="panel1">
      <label class="drop-zone" for="file-input">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <span>Click to browse or drag a <strong>.dcm / .dicom / .dcx</strong> file</span>
        <input type="file" id="file-input" accept=".dcm,.dicom,.dcx" style="display:none"/>
      </label>
    </div>

    <!-- Step 2 -->
    <div class="card hide" id="panel2">
      <div class="file-info" id="file-info"></div>
      <div class="actions">
        <button class="btn btn-p" id="btn-upload">Upload &amp; Parse</button>
        <button class="btn btn-s" id="btn-change">Choose different file</button>
      </div>
      <p class="status" id="status"></p>
    </div>

    <!-- Step 3 -->
    <div class="hide" id="panel3">
      <div class="card" id="result-card"></div>
      <div class="card" style="margin-top:1rem" id="history-card">
        <div class="sec-hdr">
          <h2>Parse history</h2>
          <button class="btn btn-s btn-sm" id="btn-refresh">Refresh</button>
        </div>
        <div id="history-body"><p class="muted">No previous jobs yet.</p></div>
      </div>
    </div>
  </main>

  <script>
    const STEPS = [
      {title:"Select a DICOM file", desc:"Choose a .dcm, .dicom, or .dcx file from your computer. The parser supports standard DICOM P10 files as well as proprietary vendor-wrapped formats."},
      {title:"Upload & parse", desc:"Submit the file to the decoder API. It will run byte-level sniffing, attempt DICOM P10 parsing, try registered wrapper decoders, and extract metadata."},
      {title:"Review results", desc:"Inspect the parsed DICOM tags, transfer syntax, pixel data info, and any warnings or errors. You can also view your parse history."}
    ];

    let currentStep = 1;
    let selectedFile = null;
    let latestResult = null;

    const $ = id => document.getElementById(id);
    const panels = [null, $("panel1"), $("panel2"), $("panel3")];

    function setStep(n) {
      currentStep = n;
      ["s1","s2","s3"].forEach((id,i) => {
        const el = $(id);
        el.className = i+1 < n ? "step completed" : i+1 === n ? "step active" : "step";
        el.querySelector(".step-circle").innerHTML = i+1 < n
          ? '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8.5L6.5 12L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
          : (i+1);
      });
      $("track-fill").style.width = ((n-1)/2*100)+"%";
      $("prompt-badge").textContent = "Step "+n+" of 3";
      $("prompt-title").textContent = STEPS[n-1].title;
      $("prompt-desc").textContent = STEPS[n-1].desc;
      panels.forEach((p,i) => { if(p) p.classList.toggle("hide", i!==n); });
    }

    $("file-input").addEventListener("change", e => {
      const f = e.target.files[0];
      if(!f) return;
      selectedFile = f;
      $("file-info").innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
        + '<div><strong>'+f.name+'</strong> <span class="muted">('+( f.size/1024).toFixed(1)+' KB)</span></div>';
      $("status").textContent = "";
      setStep(2);
    });

    $("btn-change").addEventListener("click", () => { selectedFile = null; $("file-input").value=""; setStep(1); });

    $("btn-upload").addEventListener("click", async () => {
      if(!selectedFile) return;
      $("btn-upload").disabled = true;
      $("btn-upload").textContent = "Parsing...";
      $("status").textContent = "Uploading and parsing...";
      $("status").className = "status";
      try {
        const fd = new FormData(); fd.append("file", selectedFile);
        const res = await fetch("/api/upload", {method:"POST", body:fd});
        latestResult = await res.json();
        $("status").textContent = "";
        renderResult();
        setStep(3);
        refreshJobs();
      } catch(e) {
        $("status").textContent = "Upload failed. Is the API running?";
        $("status").className = "status status-err";
      } finally {
        $("btn-upload").disabled = false;
        $("btn-upload").textContent = "Upload & Parse";
      }
    });

    function renderResult() {
      if(!latestResult) return;
      const r = latestResult.result || {};
      const hasErr = r.errors && r.errors.length > 0;
      const hasWarn = r.warnings && r.warnings.length > 0;
      let h = '<div class="r-header"><div><h3 class="r-fname">'+latestResult.filename+'</h3>'
        +'<span class="r-time">'+new Date(latestResult.created_at).toLocaleString()+'</span></div>'
        +'<span class="badge '+(hasErr?"badge-err":"badge-ok")+'">'+(hasErr?"Parse errors":"Parsed OK")+'</span></div>';

      h += '<div class="meta-grid">';
      h += meta("Format", r.source_format||"unknown");
      h += meta("Transfer Syntax", r.transfer_syntax_uid||"N/A");
      h += meta("Pixel Data", r.has_pixel_data?"Yes":"No");
      if(r.unwrap_plugin) h += meta("Unwrap Plugin", r.unwrap_plugin);
      if(r.rows!=null) h += meta("Dimensions", r.rows+" x "+r.columns);
      if(r.bits_allocated!=null) h += meta("Bits Allocated", r.bits_allocated);
      h += '</div>';

      if(r.tags && Object.keys(r.tags).length) {
        h += '<div class="sec"><h4>DICOM Tags</h4><table><thead><tr><th>Tag</th><th>Value</th></tr></thead><tbody>';
        for(const [k,v] of Object.entries(r.tags)) h += '<tr><td style="font-weight:500;color:#374151">'+k+'</td><td>'+v+'</td></tr>';
        h += '</tbody></table></div>';
      }
      if(hasWarn) {
        h += '<div class="sec"><h4>Warnings</h4><ul class="msgs w-warn">';
        r.warnings.forEach(w => h += '<li>'+w+'</li>');
        h += '</ul></div>';
      }
      if(hasErr) {
        h += '<div class="sec"><h4>Errors</h4><ul class="msgs w-err">';
        r.errors.forEach(e => h += '<li>'+e+'</li>');
        h += '</ul></div>';
      }
      h += '<div class="actions" style="margin-top:1rem"><button class="btn btn-p" id="btn-again">Parse another file</button></div>';
      $("result-card").innerHTML = h;
      $("btn-again").addEventListener("click", () => { selectedFile=null; latestResult=null; $("file-input").value=""; setStep(1); });
    }

    function meta(label, val) {
      return '<div class="meta-item"><span class="meta-label">'+label+'</span><span class="meta-val">'+val+'</span></div>';
    }

    async function refreshJobs() {
      try {
        const res = await fetch("/api/jobs");
        const data = await res.json();
        if(!data.jobs || data.jobs.length===0) { $("history-body").innerHTML='<p class="muted">No previous jobs yet.</p>'; return; }
        let h = '<table><thead><tr><th>Filename</th><th>Format</th><th>Status</th><th>Time</th></tr></thead><tbody>';
        data.jobs.forEach(j => {
          const err = j.result.errors && j.result.errors.length>0;
          h += '<tr><td>'+j.filename+'</td><td>'+(j.result.source_format||"—")+'</td>'
            +'<td><span class="badge-sm '+(err?"badge-err":"badge-ok")+'">'+(err?"Error":"OK")+'</span></td>'
            +'<td class="muted">'+new Date(j.created_at).toLocaleTimeString()+'</td></tr>';
        });
        h += '</tbody></table>';
        $("history-body").innerHTML = h;
      } catch(e) {}
    }

    $("btn-refresh").addEventListener("click", refreshJobs);
    refreshJobs();
  </script>
</body>
</html>
"""


def create_app() -> FastAPI:
    app = FastAPI(title="DICOM Decoder Demo API")
    jobs: dict[str, ParseJob] = {}
    jobs_lock = Lock()

    cors_origins = os.environ.get("CORS_ORIGINS", "*")
    allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

