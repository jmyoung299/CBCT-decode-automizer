# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

DICOM Decoder ("CBCT-decode-automizer") is a monorepo with a **Python backend** (FastAPI) and a **React/TypeScript frontend** (Vite). It parses DICOM/DCX medical imaging files and provides a web dashboard for uploads.

### Services

| Service | Command | Port | Notes |
|---|---|---|---|
| Backend API | `python3 -c "import uvicorn; uvicorn.run('dicom_decoder.web_demo:create_app', host='0.0.0.0', port=8000, factory=True)"` | 8000 | Embedded HTML dashboard at `/api/ui` |
| Frontend (Vite) | `npm run dev --prefix frontend -- --host 0.0.0.0 --port 5173` | 5173 | Requires `frontend/.env` (copy from `.env.example`) |

### Gotchas

- **`python3 -m dicom_decoder.web_demo` may silently exit in tmux.** Use the uvicorn invocation shown above instead, or run `dicom-web-demo` (the console script entry point).
- The frontend needs `frontend/.env` with `VITE_API_BASE_URL=http://127.0.0.1:8000`. Copy from `frontend/.env.example` if missing.
- No database or external services are required for local development.
- Python binary is `python3` (not `python`) in this environment.

### Standard commands

See `README.md` for full reference. Quick summary:

- **Tests:** `python3 -m pytest -q`
- **Lint (frontend):** `npm run lint --prefix frontend`
- **Build (frontend):** `npm run build --prefix frontend`
- **CLI parse:** `dicom-parse /path/to/file.dcm`
- **Batch parse:** `dicom-parse-batch /path/to/folder`
- **Golden tests:** `dicom-golden tests/fixtures/vendor-cases --pretty`
