#!/bin/bash
# Start the ski-analysis app for local/LAN use. No Docker, no database server:
# SQLite + files under backend/data. Ports: API 8003, UI 5177 (unique to this project).
#
#   scripts/run_dev.sh            # API + dev UI
#   scripts/run_dev.sh --api      # API only (serves the built UI too, if frontend/dist exists)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.11 python3.12 python3.13; do command -v "$c" >/dev/null 2>&1 && PY="$c" && break; done
fi
[ -n "$PY" ] || { echo "Need Python 3.11-3.13 (MediaPipe has no wheels for newer versions yet): brew install python@3.11"; exit 1; }

cd "$ROOT/backend"
if [ ! -x venv/bin/python ]; then
  echo "Creating backend/venv with $PY ..."
  "$PY" -m venv venv
  venv/bin/pip install -q --upgrade pip
  venv/bin/pip install -q -r requirements.txt
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Note: ffmpeg not found - the annotated video will be skipped (brew install ffmpeg)."
elif ! ffmpeg -hide_banner -version >/dev/null 2>&1; then
  echo "Note: ffmpeg is installed but will not start - the annotated video will be skipped (brew upgrade ffmpeg, or brew reinstall ffmpeg)."
fi

IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo localhost)"
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

PYTHONUNBUFFERED=1 venv/bin/python main.py &
PIDS+=($!)

if [ "${1:-}" != "--api" ]; then
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install
  npm run dev -- --clearScreen false &
  PIDS+=($!)
  echo
  echo "  Open on this Mac:   http://localhost:5177"
  echo "  Open on the LAN:    http://$IP:5177"
  echo
fi
wait
