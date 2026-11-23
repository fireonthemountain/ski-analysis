# Rebuild brief: Ski Assessment Validation

Use this to recreate the project from scratch (or to brief an agent). The source of truth for measurement details
is [docs/PIPELINE.md](docs/PIPELINE.md); for project state and evidence, [ANALYSIS-2026-11.md](ANALYSIS-2026-11.md).
No secrets belong in this file: docker-compose secrets live in `.env` (template: `.env.example`).

## What to build

A local web app that checks a skier's *own assessment* of a run against pose measurements. The user rates PSIA-style
items (stance width, fore-aft, stance height, hip flexion, flexion/extension range, edge angle, angulation,
separation, rotation/counter, turn shape, symmetry, pole-plant timing), uploads one video or 1–40 stills, and gets
per item: agree / disagree / inconclusive, the measured value ± uncertainty, the band edges, a confidence, and
annotated evidence frames. It must never guess: anything it can't measure properly is inconclusive with the reason.

## Stack and layout

- Backend: Python 3.11, FastAPI, MediaPipe Pose Landmarker (Tasks API, heavy model), OpenCV, NumPy, SQLAlchemy.
  Default storage SQLite + files in `backend/data/`; optional PostgreSQL + MinIO via docker compose.
- Frontend: React 18 + TypeScript + Vite. Assessment form, results page (agreement table, evidence frames,
  annotated video, clickable charts), history.
- Ports: API 8003, UI 5177, both on all interfaces (LAN use). `scripts/run_dev.sh` starts both.
- Pipeline modules in `backend/pipeline/`: ingest, pose, identity, smoothing, metrics, segmentation, assessment
  (item catalogue), validation (evaluators + `decide`), report, runner, cli. See docs/architecture.md.

## Key decisions (and why)

1. **Validate the user's rating instead of scoring the skier.** Thresholds are engineering defaults, not PSIA numbers;
   a verdict against the user's own band is honest about that.
2. **Uncertainty first.** `u = sqrt(floor² + robust_se²)`; agree/disagree only when the value is at least `u` inside/
   outside the band; borderline is inconclusive. Confidence = cap × pose visibility × sample factor × penalties ×
   margin term; below 0.30 the verdict is withdrawn.
3. **View gating.** Image-plane items need a front/back view; fore-aft needs side-on; view is auto-detected.
4. **3D only where 2D can't work** (rotation, joint angles from the front), capped at 0.6 confidence (monocular depth).
5. **Synthetic stick figure with known geometry for tests;** a colour-marker estimator so tests never need MediaPipe.

## Lessons from real footage (keep these)

- MediaPipe world landmarks are x right, y down, z away from the camera (verified on real frames).
- Counter must be judged on the **second half of each turn** (peak lean to edge change). A downhill-facing upper body
  faces the inside of the turn before the fall line, so a whole-turn median cancels to about 0.
- Reject 3D frames whose shoulders are < 0.20 m or hips < 0.10 m apart (collapsed distant poses) and separations
  beyond ±110° (left/right labels swapped between upper and lower body). Show evidence frames near the reported
  value, not the extreme.
- Detect **not skiing**: seated people facing the camera have 2D thigh/shin ratio < 0.62 (chairlift 0.51–0.57,
  skiing 0.67–1.12).
- Keep **one person per video** with a torso-colour signature; torsos under 30 px are too small to read.
- Detection needs the skier at ≥ ~15% of frame height. Speed is ~0.1 s per analysed frame on an M1.
- Treat a broken ffmpeg as missing (check it actually starts); fall back to OpenCV.

## Done when

`pytest` passes (metric unit tests, engine tests on scripted runs, HTTP end-to-end), `npm run build` passes, CI runs
both, and a real front-on clip produces a skeleton on the skier with sensible values (see TESTING.md).
