import { useMemo, useState } from "react";
import "./App.css";

type ParseResult = {
  tags?: Record<string, string>;
  warnings?: string[];
  errors?: string[];
  source_format?: string;
  unwrap_plugin?: string | null;
  transfer_syntax_uid?: string;
  has_pixel_data?: boolean;
  rows?: number | null;
  columns?: number | null;
  bits_allocated?: number | null;
  number_of_frames?: number | null;
};

type ParseResponse = {
  job_id: string;
  filename: string;
  created_at: string;
  result: ParseResult;
};

type JobsResponse = {
  count: number;
  jobs: ParseResponse[];
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000";

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

const STEPS = [
  {
    number: 1,
    title: "Select a DICOM file",
    description:
      "Choose a .dcm, .dicom, or .dcx file from your computer. The parser supports standard DICOM P10 files as well as proprietary vendor-wrapped formats.",
  },
  {
    number: 2,
    title: "Upload & parse",
    description:
      "Submit the file to the decoder API. It will run byte-level sniffing, attempt DICOM P10 parsing, try registered wrapper decoders, and extract metadata.",
  },
  {
    number: 3,
    title: "Review results",
    description:
      "Inspect the parsed DICOM tags, transfer syntax, pixel data info, and any warnings or errors. You can also view your parse history.",
  },
];

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="stepper">
      {STEPS.map((step) => {
        const state =
          currentStep > step.number
            ? "completed"
            : currentStep === step.number
              ? "active"
              : "upcoming";
        return (
          <div key={step.number} className={`step ${state}`}>
            <div className="step-circle">
              {state === "completed" ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                step.number
              )}
            </div>
            <div className="step-label">{step.title}</div>
          </div>
        );
      })}
      <div className="step-connector-track">
        <div
          className="step-connector-fill"
          style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}

function StepPrompt({ step }: { step: (typeof STEPS)[number] }) {
  return (
    <div className="step-prompt">
      <div className="step-prompt-badge">Step {step.number} of {STEPS.length}</div>
      <h2 className="step-prompt-title">{step.title}</h2>
      <p className="step-prompt-desc">{step.description}</p>
    </div>
  );
}

function TagsTable({ tags }: { tags: Record<string, string> }) {
  const entries = Object.entries(tags);
  if (entries.length === 0) return <p className="muted">No tags found.</p>;
  return (
    <table className="tags-table">
      <thead>
        <tr>
          <th>Tag</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <td className="tag-name">{key}</td>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ResultCard({ result }: { result: ParseResponse }) {
  const r = result.result;
  const hasErrors = r.errors && r.errors.length > 0;
  const hasWarnings = r.warnings && r.warnings.length > 0;

  return (
    <div className="result-detail">
      <div className="result-header">
        <div>
          <h3 className="result-filename">{result.filename}</h3>
          <span className="result-time">
            {new Date(result.created_at).toLocaleString()}
          </span>
        </div>
        <span className={`result-badge ${hasErrors ? "badge-error" : "badge-success"}`}>
          {hasErrors ? "Parse errors" : "Parsed OK"}
        </span>
      </div>

      <div className="result-meta-grid">
        <div className="meta-item">
          <span className="meta-label">Format</span>
          <span className="meta-value">{r.source_format ?? "unknown"}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Transfer Syntax</span>
          <span className="meta-value">{r.transfer_syntax_uid ?? "N/A"}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Pixel Data</span>
          <span className="meta-value">{r.has_pixel_data ? "Yes" : "No"}</span>
        </div>
        {r.unwrap_plugin && (
          <div className="meta-item">
            <span className="meta-label">Unwrap Plugin</span>
            <span className="meta-value">{r.unwrap_plugin}</span>
          </div>
        )}
        {r.rows != null && (
          <div className="meta-item">
            <span className="meta-label">Dimensions</span>
            <span className="meta-value">{r.rows} x {r.columns}</span>
          </div>
        )}
        {r.bits_allocated != null && (
          <div className="meta-item">
            <span className="meta-label">Bits Allocated</span>
            <span className="meta-value">{r.bits_allocated}</span>
          </div>
        )}
      </div>

      {r.tags && Object.keys(r.tags).length > 0 && (
        <div className="result-section">
          <h4>DICOM Tags</h4>
          <TagsTable tags={r.tags} />
        </div>
      )}

      {hasWarnings && (
        <div className="result-section">
          <h4>Warnings</h4>
          <ul className="msg-list msg-warn">
            {r.warnings!.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {hasErrors && (
        <div className="result-section">
          <h4>Errors</h4>
          <ul className="msg-list msg-error">
            {r.errors!.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [latestResult, setLatestResult] = useState<ParseResponse | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [uploading, setUploading] = useState(false);

  const currentStep = useMemo(() => {
    if (latestResult) return 3;
    if (selectedFile) return 2;
    return 1;
  }, [selectedFile, latestResult]);

  const statusClass = useMemo(() => {
    if (!status) return "status";
    if (status.toLowerCase().includes("failed")) return "status status-error";
    return "status status-ok";
  }, [status]);

  async function refreshJobs() {
    setLoadingJobs(true);
    try {
      const response = await fetch(apiUrl("/api/jobs"));
      const payload = (await response.json()) as JobsResponse;
      setJobs(payload);
    } finally {
      setLoadingJobs(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile) {
      setStatus("Select a file first.");
      return;
    }

    setUploading(true);
    setStatus("Uploading and parsing...");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const response = await fetch(apiUrl("/api/upload"), {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as ParseResponse;
      setLatestResult(payload);
      setStatus("Upload complete.");
      await refreshJobs();
    } catch {
      setStatus("Upload failed. Check that the backend API is running.");
    } finally {
      setUploading(false);
    }
  }

  function handleReset() {
    setSelectedFile(null);
    setLatestResult(null);
    setStatus("");
  }

  return (
    <main className="page">
      <header className="header">
        <h1>DICOM Decoder Dashboard</h1>
        <p className="muted">
          Upload and parse DICOM files step by step &middot; API: <code>{API_BASE_URL}</code>
        </p>
      </header>

      <StepIndicator currentStep={currentStep} />
      <StepPrompt step={STEPS[currentStep - 1]} />

      {currentStep === 1 && (
        <section className="card step-card">
          <label className="file-drop-zone" htmlFor="file-input">
            <svg className="drop-icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="drop-text">
              Click to browse or drag a <strong>.dcm / .dicom / .dcx</strong> file
            </span>
            <input
              id="file-input"
              type="file"
              accept=".dcm,.dicom,.dcx"
              className="file-input-hidden"
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null;
                setSelectedFile(file);
                if (file) setStatus("");
              }}
            />
          </label>
        </section>
      )}

      {currentStep === 2 && selectedFile && (
        <section className="card step-card">
          <div className="selected-file-info">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <div>
              <strong>{selectedFile.name}</strong>
              <span className="muted"> ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
            </div>
          </div>
          <div className="step-actions">
            <button onClick={handleUpload} disabled={uploading} className="btn-primary">
              {uploading ? "Parsing..." : "Upload & Parse"}
            </button>
            <button onClick={handleReset} className="btn-secondary" disabled={uploading}>
              Choose different file
            </button>
          </div>
          {status && <p className={statusClass}>{status}</p>}
        </section>
      )}

      {currentStep === 3 && latestResult && (
        <>
          <section className="card step-card">
            <ResultCard result={latestResult} />
            <div className="step-actions" style={{ marginTop: "1rem" }}>
              <button onClick={handleReset} className="btn-primary">
                Parse another file
              </button>
            </div>
          </section>

          <section className="card" style={{ marginTop: "1rem" }}>
            <div className="section-header">
              <h2>Parse history</h2>
              <button onClick={refreshJobs} disabled={loadingJobs} className="btn-secondary btn-sm">
                {loadingJobs ? "Refreshing..." : "Refresh"}
              </button>
            </div>
            {jobs && jobs.count > 0 ? (
              <table className="jobs-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Format</th>
                    <th>Status</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.jobs.map((job) => (
                    <tr key={job.job_id}>
                      <td>{job.filename}</td>
                      <td>{job.result.source_format ?? "—"}</td>
                      <td>
                        <span
                          className={`result-badge-sm ${
                            job.result.errors && job.result.errors.length > 0
                              ? "badge-error"
                              : "badge-success"
                          }`}
                        >
                          {job.result.errors && job.result.errors.length > 0 ? "Error" : "OK"}
                        </span>
                      </td>
                      <td className="muted">{new Date(job.created_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No previous jobs yet.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}

export default App;
