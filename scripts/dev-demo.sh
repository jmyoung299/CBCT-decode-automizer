#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "[1/4] Installing backend dependencies..."
python3 -m pip install -e "$ROOT_DIR[dev]"

echo "[2/4] Installing frontend dependencies..."
npm install --prefix "$FRONTEND_DIR"

if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
  echo "[3/4] Creating frontend .env from example..."
  cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
fi

echo "[4/4] Starting backend and frontend..."
echo "Backend:  http://127.0.0.1:8000/api/ui"
echo "Frontend: http://127.0.0.1:5173"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

python3 -m dicom_decoder.web_demo --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

npm run dev --prefix "$FRONTEND_DIR" -- --host 0.0.0.0 --port 5173
