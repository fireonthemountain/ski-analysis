# Running Ski Analysis on a Mac

The default setup needs no Docker and no database server: SQLite and files under `backend/data/`.

## Prerequisites

```bash
# Homebrew: https://brew.sh
brew install python@3.11 node ffmpeg git
```

- **Python 3.11–3.13.** MediaPipe has no wheels for newer versions yet; `run_dev.sh` picks the first of 3.11/3.12/3.13 it finds.
- **ffmpeg** encodes the annotated video. If Homebrew upgrades a library underneath it and it stops starting,
  the app skips the video and says so; fix it with `brew upgrade ffmpeg` (or `brew reinstall ffmpeg`).

## Start it

```bash
git clone https://github.com/fireonthemountain/ski-analysis.git
cd ski-analysis
scripts/run_dev.sh            # API on :8003, UI on :5177; prints the LAN URL
```

First run creates `backend/venv`, installs the Python packages, runs `npm install`, and downloads the pose model
(about 30 MB) into `backend/models/`.

- This Mac: http://localhost:5177
- Phone/laptop on the same network: http://<this Mac's IP>:5177 (the script prints it)
- API docs: http://localhost:8003/api/docs

`scripts/run_dev.sh --api` starts only the API; after `cd frontend && npm run build` it also serves the UI on :8003.

## First validation

See the Quick Start in [README.md](README.md) and the filming tips in [TESTING.md](TESTING.md): skier coming
toward the camera, at least ~15% of the frame height, boots visible, one continuous shot.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Need Python 3.11-3.13" | `brew install python@3.11` |
| Phone can't reach :5177 | macOS firewall: allow incoming connections for the Python and Node binaries when prompted (System Settings → Network → Firewall) |
| No annotated video | ffmpeg missing or broken: `ffmpeg -version`; then `brew upgrade ffmpeg` |
| "No skier was detected" | skier too small or not in frame; zoom or crop so the skier is larger |
| Port already in use | `lsof -i :8003` / `lsof -i :5177` to find the other process |
| Start over | stop the script, delete `backend/data/` (all runs and results) |

## Optional: Docker stack (PostgreSQL + MinIO)

```bash
cp .env.example .env        # set the change-me secrets
docker compose up
```
