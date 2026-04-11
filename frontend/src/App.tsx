import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

type ParseResponse = {
  job_id: string;
  filename: string;
  created_at: string;
  result: {
    tags?: Record<string, string>;
    warnings?: string[];
    errors?: string[];
    source_format?: string;
    unwrap_plugin?: string | null;
  };
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

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [latestResult, setLatestResult] = useState<ParseResponse | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [uploading, setUploading] = useState(false);

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

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!selectedFile) {
      setStatus("Select a file first.");
      return;
    }

    setUploading(true);
    setStatus("Uploading...");
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
      setStatus("Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="page">
      <header>
        <h1>DICOM Decoder Dashboard</h1>
        <p className="muted">
          Standalone frontend for Vercel/Firebase hosting. API base URL:{" "}
          <code>{API_BASE_URL}</code>
        </p>
      </header>

      <section className="grid">
        <article className="card">
          <h2>Upload file</h2>
          <form onSubmit={handleUpload} className="upload-form">
            <input
              type="file"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            <button type="submit" disabled={uploading}>
              {uploading ? "Uploading..." : "Upload & Parse"}
            </button>
          </form>
          <p className={statusClass}>{status}</p>
        </article>

        <article className="card">
          <h2>Recent jobs</h2>
          <button onClick={refreshJobs} disabled={loadingJobs}>
            {loadingJobs ? "Refreshing..." : "Refresh"}
          </button>
          <pre>{JSON.stringify(jobs, null, 2)}</pre>
        </article>
      </section>

      <section className="card">
        <h2>Latest result</h2>
        <pre>{JSON.stringify(latestResult, null, 2)}</pre>
      </section>
    </main>
  );
}

export default App;
