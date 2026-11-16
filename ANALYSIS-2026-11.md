# Ski analysis — state, design and build log (November 15, 2026)

Branch: `feature/2026-11-validation-pipeline` (not pushed, not merged). Design detail: `docs/PIPELINE.md`.

## 1. Where the project stood (main @ 9f7e56b)

What existed: a FastAPI backend (`backend/main.py`) with a single-photo upload endpoint that ran MediaPipe on one
image and produced a 0–100 "PSIA-aligned" score with canned tips; SQLAlchemy models; a MinIO/S3 storage service; a
React/Vite page with a drop zone and a score card; a lot of documentation (README, roadmap, testing guides, open-source
checklist). `Movement_Analysis` next door is a README + LICENSE stub and was left untouched.

What I verified by running it:

| Finding | Evidence |
|---|---|
| The app could not be installed | `pip install -r backend/requirements.txt` fails: `pytest==8.0.0` conflicts with `pytest-asyncio==0.23.4` (needs pytest < 8) |
| The pose code could not run on a current install | `analysis/pose_detector.py` used `mp.solutions.pose`; MediaPipe 0.10.35 (what pip resolves today) has no `mp.solutions` |
| No tests existed | no `tests/` directory, no test files; TESTING.md describes manual photo checks only |
| `docker compose up` (the README's recommended path) could not work | compose builds `backend/Dockerfile` and `frontend/Dockerfile.dev`; neither file existed |
| The API could not start without PostgreSQL and MinIO | models used PostgreSQL-only `UUID`/`JSONB`; `StorageService()` connected to MinIO at import time |
| The UI pointed at the wrong port | components defaulted to `http://localhost:8000/api/v1` (backend moved to 8003 in the last commit; 8000 belongs to another app on this Mac) and used `localhost`, so it could not work from another LAN device |
| `npm run build` could not pass | `tsconfig.json` referenced a missing `tsconfig.node.json`; `index.html` referenced a missing icon |
| Hardcoded user | every upload was stored under a fixed UUID with email `temp@example.com` (`main.py:225`) |
| Dev credentials inline | `docker-compose.yml` carried the Postgres/MinIO/SECRET_KEY values in plain text |
| System Python is 3.15 | MediaPipe has no wheel for it; 3.11 is installed and is what the venv uses |
| `examples/` had no media | only a CSV of illustrative scores and a README; `scripts/setup_test_images.sh` downloads stock photos of people (not used) |

Gap against the goal: nothing accepted an assessment, nothing handled video, nothing compared a claim with a
measurement, and there was no notion of confidence or "inconclusive". The existing score was a set of fixed ranges on
five 2D angles from one photo.

## 2. Pipeline design (summary; full version in docs/PIPELINE.md)

ingest (1 video or N images; OpenCV/FFmpeg, ~15 fps, first 90 s) → pose (MediaPipe PoseLandmarker, 33 landmarks with
feet, 2D + estimated 3D) → tracking (crop follows the skier, tile search when lost, jump rejection) → smoothing (gap
fill ≤ 0.3 s, 6 Hz zero-phase Butterworth) → turn segmentation (sign changes of leg-axis lean) → metrics → assessment
schema (12 items, ordered bands, explicit thresholds) → validation engine → report (annotated frames, annotated video,
per-metric charts, agreement table).

MediaPipe was chosen over YOLO-pose and RTMPose because it runs on the Mac Mini's CPU from a plain `pip install` with no
PyTorch, is the only one of the three that gives heel/toe landmarks and a 3D estimate (needed for a slope-independent
fore-aft reference and for rotation/separation), and is Apache-2.0 (Ultralytics YOLO is AGPL, which conflicts with this
repo's MIT licence).

Verdict rule: uncertainty `u = sqrt(floor² + spread²)`; inside your band by ≥ u → agree; outside by ≥ u → disagree;
closer than u to the edge → inconclusive. Anything not properly measurable is inconclusive with the reason; confidence
below 0.30 withdraws the verdict.

## 3. What was built

Backend (`backend/`)
- `pipeline/` (about 2,500 lines): `keypoints`, `ingest`, `pose` (MediaPipe + two test estimators), `smoothing`,
  `segmentation`, `metrics`, `assessment` (catalog + pydantic schema), `validation`, `report`, `runner`, `cli`, `synthetic`.
- `api/validations.py`: `GET /api/v1/assessment/catalog`, `POST /api/v1/validations` (assessment JSON + one video or
  several images), `GET /api/v1/validations`, `GET /api/v1/validations/{id}`, file serving for frames/annotated video,
  `DELETE`. Runs are processed one at a time in a background thread with live progress.
- `api/users.py`: caller identified by `X-User-Id` (default `anonymous`); runs and legacy uploads are stored per user.
- Runs with no services: SQLite + local files in `backend/data/` by default; PostgreSQL/MinIO/S3 still selectable.
- Legacy photo endpoint kept working (ported off the removed MediaPipe API, reads from local storage).
- `requirements.txt` rewritten to what actually installs; `requirements-optional.txt` for Postgres/MinIO/S3.

Frontend (`frontend/`)
- Assessment form: 12 items grouped by PSIA fundamental, rating buttons that show their numeric band, per-item notes,
  camera-view selector, live hints for what will be inconclusive (e.g. video-only items when you add screenshots).
- Media drop zone for one video or up to 40 images.
- Results: summary tiles, agreement table (assessed / measured ± uncertainty / band bar / verdict / confidence / why),
  expandable evidence frames with skeleton overlay, annotated video, one chart per metric with turn bands, rating
  thresholds and evidence markers (click a chart to seek the video), image gallery for stills, history page.
- Wide layout, 12-hour times, light/dark. `/api` is proxied by Vite, so the same URL works from any LAN device.
- Removed: the old single-photo score page (`VideoUpload`, `AnalysisResults`) and unused dependencies (three.js,
  video.js, zustand, ...). The legacy API endpoints remain.

Ops
- `scripts/run_dev.sh` (API 8003 + UI 5177 on 0.0.0.0, prints LAN URLs), `scripts/make_sample_media.py`,
  `examples/assessment.example.json`, `examples/synthetic/` (rendered stick-figure clip + 3 stills).
- `docker-compose.yml` reads secrets from `.env`; `.env.example` rewritten; the two missing Dockerfiles added.

## 4. Test results (run on this Mac, November 15, 2026)

`cd backend && ./venv/bin/python -m pytest tests -q` → **116 passed, 0 failed** (Python 3.11.x, MediaPipe 0.10.35).

| File | Passed | Covers |
|---|---|---|
| `tests/test_metrics.py` | 73 | synthetic 3D skeletons with known angles → inclination, angulation, edge proxy, stance width (2D/3D), knee/hip angles, fore-aft incl. slope independence, separation/counter sign in front and back views, visibility gating, view classification |
| `tests/test_validation.py` | 35 | smoothing, jump rejection, turn segmentation, agree/disagree/borderline, low-confidence → inconclusive, view and 3D requirements, stills vs video, pole-plant timing, asymmetry, confidence floor |
| `tests/test_e2e.py` | 8 | HTTP API with a rendered H.264 clip and PNG stills: upload → decode → pose from pixels → verdicts → frames served; wrong assessment disagrees; blank image never gets a verdict; bad requests; per-user scoping; legacy upload with `X-User-Id` |

`cd frontend && npm run build` (type-check + build) passes. I also ran the app with `scripts/run_dev.sh`, submitted
the sample clip through the browser form, and checked the results, stills and history pages by eye; no console errors.

Things the tests caught and I changed as a result: hip angle was biased ~8° by shoulders being wider than hips (now
measured against the torso axis); a front-view 2D knee angle read ~175° and "agreed" with "tall" (now refused without
3D unless side-on); a side-on skier with rotated shoulders was classified as oblique and still got an edge verdict
(view detection now uses hips too, measured across the torso, and oblique views give no verdict on plane-dependent
items); separation and counter bands were narrower than twice their uncertainty, so "moderate"/"square" could never be
confirmed (bands widened, and a test now enforces this for every item).

**What is not tested, stated plainly**
- **No real skiing footage has been through this.** I did not download video of real people and there was none in
  `examples/`. The end-to-end tests use a stick figure whose joints are read from pixels by a colour-marker estimator;
  MediaPipe is exercised only to the extent that it loads, runs through the whole pipeline on the sample clip, finds no
  person in a stick figure, and every item correctly comes back inconclusive. Its landmark accuracy on a skier, its 3D
  axis convention against my assumption (z away from camera, per the MediaPipe docs), and the per-frame speed with a
  person in view are unverified. The first real clip is the real test; look at the overlay before believing a number.
- The thresholds are my engineering defaults, not PSIA figures, and are uncalibrated against instructor judgement.
- Pole-plant timing and turn shape are proxies marked experimental.
- Docker: `docker compose config` resolves with `.env.example` copied to `.env`. The backend image builds and the app imports inside it (it resolves MediaPipe 0.10.18 on Linux arm64, not the 0.10.35 used on the Mac). `docker compose up` with PostgreSQL + MinIO was **not** run end to end.

## 5. Run your first validation

1. `cd "/Users/csather/AI Apps/ski-analysis" && git checkout feature/2026-11-validation-pipeline`
2. `scripts/run_dev.sh` — the venv and node_modules already exist on this Mac; the pose models are already in
   `backend/models/`. Leave it running. It prints `http://localhost:5177` and the LAN URL (`http://192.168.6.89:5177` today).
3. Open the URL. Optional: put a name in the *User* box (top right) so your runs are listed under it.
4. Drop **one video** (mp4/mov/m4v/avi/mkv/webm, ≤ 500 MB, first 90 s analysed) or **1–40 screenshots** (jpg/png/webp/heic).
   Best footage: one skier, full body, as large in frame as possible, coming straight at or going straight away from
   the camera (edging, angulation, rotation, turns) or side-on (fore-aft).
5. Rate only what you observed; add a note per item if you like. Leave *Camera view* on Auto-detect.
6. Click **Validate**. Wait for the progress bar (pose estimation is the slow part).
7. Read the agreement table. Click a row for the evidence frames; click a chart to jump the annotated video there.
   **First check the overlay sits on the skier** — if it does not, treat the run as inconclusive regardless of the table.

Command line: `cd backend && ./venv/bin/python -m pipeline.cli --assessment ../examples/assessment.example.json /path/to/run.mov --out ~/Desktop/run1`
(`--list-items` prints the item and rating ids).

No footage handy: `POSE_ESTIMATOR=marker scripts/run_dev.sh` and upload `examples/synthetic/synthetic_run_front.mp4`.

## 6. Ledger

- `ski-analysis-2` done — `X-User-Id` header (default `anonymous`) replaces the hardcoded user on the upload endpoint
  and scopes validation runs. It is identification, not authentication.
- `ski-analysis-3` done — secrets moved to `.env`. Differs from the ticket in one way: the four secrets have **no**
  inline fallback (compose refuses to start without `.env`) and the placeholder values changed, rather than keeping the
  old defaults. The old placeholder values remain in git history and in `RECREATION_PROMPT.md`.
- `ski-analysis-1` (open-source checklist) not started; still open.
- New: `ski-analysis-4` (high) first real-footage validation + threshold calibration; `ski-analysis-5` refresh the stale
  docs (lower half of README, TESTING.md, QUICKSTART_TESTING.md, docs/architecture.md, RECREATION_PROMPT.md, legacy scripts);
  `ski-analysis-6` pipeline follow-ups (skier picker/trim, persistent queue, side-view turn segmentation, slope
  correction, thresholds file, RTMPose comparison, full Docker run).

## 7. Commits on `feature/2026-11-validation-pipeline`

| Commit | What |
|---|---|
| 55a54a7 | Pipeline core: metrics, segmentation, validation engine, synthetic model, unit tests, installable requirements |
| b51e7d9 | Validation API, `X-User-Id`, zero-service local run, end-to-end tests |
| e55034e | Compose secrets to `.env`, missing Dockerfiles |
| fc66b4f | Assessment form + results UI, CLI, `run_dev.sh`, sample media |
| (next) | Docs: this file, `docs/PIPELINE.md`, README quick start, MAC_SETUP note |

Nothing was pushed, merged or deployed.
