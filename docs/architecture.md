# System Architecture

What runs where, how a validation run flows through the system, and where data lives. The measurement design
(items, metrics, thresholds, verdict rules) is in [PIPELINE.md](PIPELINE.md).

## Components

```
 Browser (any device on the LAN)
   │  http://<mac>:5177        React 18 + Vite dev server; proxies /api and /health to :8003
   ▼
 FastAPI app  :8003  (backend/main.py)
   ├── /api/v1/assessment/catalog       items, rating bands, upload limits
   ├── /api/v1/validations              POST upload (202), GET list, GET one, GET files, DELETE
   │        │
   │        ▼  one worker thread (ThreadPoolExecutor, max_workers=1)
   │     pipeline.runner.run_validation()
   │        ingest → pose → identity → smoothing → metrics → segmentation → validation → report
   │
   ├── legacy single-photo endpoints   /api/v1/videos, /api/v1/analysis (backend/analysis/; not used by the UI)
   └── serves frontend/dist at /       when the UI has been built (one URL for the LAN)
```

| Module (`backend/pipeline/`) | Job |
|---|---|
| `ingest.py` | sample a video at 15 fps (first 90 s) or load 1–40 stills (HEIC via `sips`) |
| `pose.py` | MediaPipe Pose Landmarker (heavy/full/lite); crop tracking, full-frame and tiled fall-backs; marker estimator for the synthetic figure |
| `identity.py` | torso-colour signature per frame; keeps the longest single-person track |
| `smoothing.py` | gap filling, low-pass, identity-jump rejection; filled frames are flagged so they are never evidence |
| `metrics.py` | per-frame metrics (2D frontal/sagittal, 3D rotation and joint angles), view classification, sanity gates, seated check |
| `segmentation.py` | turns from the zero crossings of the smoothed lean |
| `assessment.py` | the item catalogue: options, bands, uncertainty floors, confidence caps |
| `validation.py` | one evaluator per item; `decide()` turns value ± uncertainty into agree / disagree / inconclusive + confidence |
| `report.py` | annotated evidence frames and `annotated.mp4` (ffmpeg, skipped if ffmpeg is missing or broken) |
| `runner.py` | orchestrates a run, writes `result.json` |
| `cli.py` | the same pipeline from the command line |

## A validation run, step by step

1. The UI posts the assessment JSON and the media (one video or 1–40 images) with an `X-User-Id` header
   (identification, not authentication; default `anonymous`).
2. The API validates both, stores the upload, creates a `ValidationRun` row (status `pending`) and queues the job.
   It returns `202` with the run id.
3. The worker runs the pipeline, updating `progress` as it goes (status `processing`).
4. Results land in the run folder; the row becomes `completed` (or `failed` with the error).
5. The UI polls `GET /api/v1/validations/{id}` and renders `result.json`: summary, agreement table, evidence frames,
   annotated video, charts.

Only one run processes at a time. A run that is queued or processing when the server restarts is marked failed
("Interrupted"); there is no persistent queue yet.

## Storage

Default (`scripts/run_dev.sh`): no services needed.

```
backend/data/                      (git-ignored; DATA_DIR overrides it)
├── ski.db                         SQLite: users, validation runs (DATABASE_URL overrides it)
└── validations/<run id>/
    ├── media files as uploaded
    ├── result.json                schema_version 1: assessment, media, pose, view, turns, results, series, warnings
    ├── frames/                    annotated evidence frames
    └── annotated.mp4              skeleton overlay video (if ffmpeg works)
```

`docker compose up` (optional) runs the same app with PostgreSQL and MinIO; secrets come from `.env`
(see `.env.example`).

## Ports and processes

| Port | What |
|---|---|
| 5177 | Vite dev server (UI), all interfaces |
| 8003 | FastAPI (API, and the built UI if `frontend/dist` exists), all interfaces |
| 5432 / 9000 | PostgreSQL / MinIO, docker compose only |

The MediaPipe model (`pose_landmarker_<variant>.task`) is downloaded once into `backend/models/`. Note that
MediaPipe's native library tries to send usage telemetry to Google (`play.googleapis.com/log`); see ledger
`ski-analysis-9` in ANALYSIS-2026-11.md.

## Limits of the current design

- One worker thread: runs queue behind each other; a restart drops queued runs.
- `X-User-Id` scopes runs per name; there is no login. Keep the app on a trusted network.
- Processing is about 0.1 s per analysed frame on an M1 Mac mini (heavy model), so a 30 s clip takes under a minute.
