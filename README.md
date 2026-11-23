# 🎿 Ski Technique Analysis

Check your own read of a ski run against measurements. Rate what you saw using PSIA-style fundamentals, upload the video or screenshots, and pose estimation tells you where the evidence agrees, disagrees, or cannot say.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)](https://mediapipe.dev/)

[Quick Start](#-quick-start) | [Documentation](#-documentation) | [Testing](#-testing) | [Contributing](CONTRIBUTING.md)

---

## What it does now (November 2026): validate your own assessment

You rate a run the way an instructor would (stance width, fore-aft balance, edge angle, angulation,
upper/lower separation, rotation/counter, pole-plant timing, turn shape, ...), upload **one video or a
few screenshots**, and for each rating the app answers:

- **Agrees / Disagrees / Inconclusive**
- the measured value with its uncertainty, and the band thresholds
- a confidence score
- the annotated frames (skeleton overlay) that show it

A low-confidence pose, the wrong camera angle, or a value too close to a threshold gives
*inconclusive* with the reason, never a guessed verdict. Design, metrics and thresholds:
[docs/PIPELINE.md](docs/PIPELINE.md). Current state and test results: [ANALYSIS-2026-11.md](ANALYSIS-2026-11.md).

> Real-footage checks so far use public instructor clips (ANALYSIS-2026-11.md §9–12); the thresholds are not yet
> calibrated against your own judgement. Check the skeleton overlay on your footage before trusting a number.

---

## 🚀 Quick Start (no Docker, no database server)

Needs Python 3.11–3.13, Node 18+, and `ffmpeg` (`brew install python@3.11 node ffmpeg`).

```bash
cd "ski-analysis"
scripts/run_dev.sh
```

It creates `backend/venv`, installs dependencies, downloads the pose model on first use (~30 MB, from
Google's MediaPipe model host), then prints the URLs, e.g.

```
  Open on this Mac:   http://localhost:5177
  Open on the LAN:    http://192.168.6.89:5177
```

API: port **8003** (`/api/docs`). UI: port **5177**. Both listen on all interfaces.
Data (SQLite, results, annotated frames) lives in `backend/data/`.

### Your first validation

1. Film or pick a clip: **skier coming straight at the camera or going straight away** for edging,
   angulation, separation and turns; **side-on** for fore-aft. One skier, whole body in frame, as large
   as possible. Up to 500 MB; the first 90 s are analysed.
2. Open the UI, drop the video (or 1–40 screenshots: jpg/png/webp/heic).
3. Rate only the items you actually observed. Each rating button shows its numeric band.
4. Leave *Camera view* on Auto-detect unless it guesses wrong.
5. Click **Validate**. The results page shows the agreement table; click a row for its evidence frames,
   and click any chart to jump the annotated video to that moment.

Command line instead of the UI:

```bash
cd backend
./venv/bin/python -m pipeline.cli --list-items
./venv/bin/python -m pipeline.cli --assessment ../examples/assessment.example.json ~/Movies/my_run.mov --out ~/Desktop/my_run_validation
```

Try it without footage (rendered stick figure; MediaPipe does not treat it as a person, so use the
marker estimator): `backend/venv/bin/python scripts/make_sample_media.py`, then
`POSE_ESTIMATOR=marker scripts/run_dev.sh` and upload `examples/synthetic/synthetic_run_front.mp4`.

### Tests

```bash
cd backend && ./venv/bin/python -m pytest tests -q
cd frontend && npm run build                              # type-check + build
```

### Docker (optional: PostgreSQL + MinIO stack)

```bash
cp .env.example .env      # set the four change-me secrets
docker compose up
```

---

## 🏗️ Architecture

| Layer | What | Where |
|---|---|---|
| UI | React 18 + TypeScript + Vite: assessment form, results (agreement table, evidence frames, annotated video, charts), history | `frontend/` (dev server :5177) |
| API | FastAPI: `/api/v1/assessment/catalog`, `/api/v1/validations` (upload, list, get, files, delete), `/health` | `backend/main.py`, `backend/api/validations.py` (:8003) |
| Pipeline | ingest → pose → identity → smoothing → metrics → turn segmentation → per-item measurement → verdict | `backend/pipeline/` |
| Pose | MediaPipe Pose Landmarker (heavy by default; `POSE_MODEL=full\|lite`), 2D + 3D world landmarks | `backend/pipeline/pose.py` |
| Storage | SQLite + files under `backend/data/` by default; PostgreSQL + MinIO only with `docker compose` | `backend/config.py` |
| Jobs | one in-process worker thread; queued runs are marked failed if the server restarts | `backend/api/validations.py` |

The original single-photo scoring endpoints (`/api/v1/videos`, `/api/v1/analysis`, `backend/analysis/`) are still
in `main.py` for compatibility, but the UI no longer uses them. Details: [docs/architecture.md](docs/architecture.md).

```
ski-analysis/
├── backend/
│   ├── pipeline/        # ingest, pose, identity, smoothing, metrics, segmentation, validation, runner, cli, report
│   ├── api/             # validation API (+ X-User-Id identification)
│   ├── tests/           # metric unit tests, engine tests, HTTP end-to-end tests
│   └── main.py          # FastAPI app; serves frontend/dist when built
├── frontend/src/        # App.tsx, components/ (AssessmentForm, ResultsView, Charts, History)
├── scripts/             # run_dev.sh, make_sample_media.py, validate_shots.sh
├── examples/            # assessment.example.json, synthetic/ stick-figure media with ground truth
└── docs/                # PIPELINE.md (design, metrics, thresholds), architecture.md
```

---

## 📊 How It Works

1. **Ingest:** a video is sampled at 15 fps (first 90 s), or 1–40 stills are loaded.
2. **Pose:** MediaPipe finds the skier in each frame (tracking a crop, with full-frame and tiled fall-backs for distant
   skiers). A torso-colour signature keeps the analysis on one person when several are close together.
3. **Smoothing:** short gaps are filled, jitter low-passed, identity jumps rejected; filled frames are never evidence.
4. **Metrics:** frontal-plane angles (lean, edge proxy, angulation, stance width) from 2D; rotation (separation,
   counter) and joint angles from the 3D world landmarks, with sanity gates for collapsed or mislabelled poses.
5. **Turns:** edge changes are the zero crossings of the smoothed lean; counter is judged on the second half of each turn.
6. **Verdict:** each rated item gets a value ± uncertainty, then *agree* (inside your band by at least the
   uncertainty), *disagree* (outside by at least it), or *inconclusive* (borderline, wrong view, too few frames, not
   skiing...), plus a confidence score.

Items, thresholds and confidence rules: [docs/PIPELINE.md](docs/PIPELINE.md). The thresholds are engineering
defaults, not published PSIA numbers, and are not yet calibrated against your own judgement.

---

## 🧪 Testing

```bash
cd backend && ./venv/bin/python -m pytest tests -q     # unit, engine and HTTP end-to-end tests
cd frontend && npm run build                           # type-check + build
```

CI runs both on every push and pull request. For real footage (filming tips, the CLI, splitting an edited video
into shots with `scripts/validate_shots.sh`, how to read the results) see [TESTING.md](TESTING.md).

---

## 📚 Documentation

- **[docs/PIPELINE.md](docs/PIPELINE.md)** - design, items, metrics, thresholds, verdict rules, known limits
- **[ANALYSIS-2026-11.md](ANALYSIS-2026-11.md)** - project state, real-footage checks (§9–12), what is validated
- **[TESTING.md](TESTING.md)** - automated tests and how to test with real footage
- **[docs/architecture.md](docs/architecture.md)** - components, request flow, storage, deployment
- **[scripts/README.md](scripts/README.md)** - the helper scripts
- **[docs/technique-guide.md](docs/technique-guide.md)** - skiing technique reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - how to contribute
- **[RECREATION_PROMPT.md](RECREATION_PROMPT.md)** - brief for rebuilding the project from scratch

---

## 🗺️ Roadmap

**Done:** validation pipeline for video and stills, assessment form and results UI, CLI, CI, real-footage checks on
public instructor clips (3D axis convention and rotation signs confirmed, counter scored on the turn finish phase,
seated / not-skiing detection, one-person tracking).

**Next:**
- Calibrate the thresholds against your own rated clips (the runbook is in ANALYSIS-2026-11.md §9)
- Pick the skier / trim the clip in the upload form for footage with several people
- A persistent job queue; side-view turn segmentation; slope correction for fore-aft

**Later:** progress tracking across runs, coach/student sharing, a comparison view.

---

## 📝 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

**What this means:**
- ✅ Free to use, modify, and distribute
- ✅ Can be used commercially
- ✅ Only requirement: include license notice
- ✅ No warranty provided

---

## 🙏 Acknowledgments

- **[MediaPipe](https://mediapipe.dev/)** - Pose estimation technology
- **[OpenCV](https://opencv.org/)** - Computer vision library
- **[PSIA](https://www.thepsia.org/)** - Professional ski instruction standards
- **Ski instructors and coaches** - Domain expertise and validation
- **Open source community** - For amazing tools and libraries

---

## 🐛 Known Limitations

- **Thresholds are uncalibrated defaults.** They have been checked against expert demos, not against your judgement.
- **Camera view matters.** Edging, angulation, rotation and turns need a front or back view; fore-aft needs side-on.
  The app says so instead of guessing.
- **Distance matters.** Detection is reliable once the skier is at least ~15% of the frame height.
- **Depth comes from one camera.** Separation and counter are capped at 0.6 confidence.
- **One skier.** With several people close together the longest track is kept; people in identical clothing can't
  be told apart, so trim or crop multi-person footage.
- **Image-plane angles assume a level camera.** Camera roll or a side-hill biases lean, edge angle and symmetry.

---

## 📧 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/fireonthemountain/ski-analysis/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fireonthemountain/ski-analysis/discussions)
- **Project Link:** [https://github.com/fireonthemountain/ski-analysis](https://github.com/fireonthemountain/ski-analysis)

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Built with ⛷️ by skiers, for skiers**

*Disclaimer: This tool provides educational feedback and is not a substitute for professional ski instruction. Always ski within your ability and follow mountain safety guidelines.*
