# Scripts

| Script | What it does |
|---|---|
| `run_dev.sh` | Starts the app for local/LAN use: creates `backend/venv` on first run, starts the API (:8003) and the Vite UI (:5177), prints the LAN URL. `--api` starts the API only (it serves `frontend/dist` if built). Warns if ffmpeg is missing or won't start. |
| `make_sample_media.py` | Renders the synthetic stick-figure media in `examples/synthetic/` (a front-view clip, three stills, `ground_truth.json`). Run with the backend venv: `backend/venv/bin/python scripts/make_sample_media.py`. Use it with `POSE_ESTIMATOR=marker`, because MediaPipe does not see the figure as a person. |
| `validate_shots.sh` | Validates an **edited** video one camera shot at a time: `scripts/validate_shots.sh VIDEO START END ASSESSMENT.json OUTDIR [MIN_SHOT_SECONDS]`. Cuts the section out, splits it at camera cuts (ffmpeg scene detection), runs the CLI on every shot of at least 3 s, and writes `OUTDIR/summary.md` (one row per shot; shots over 40 s are flagged as probably several shots). Needs a working ffmpeg. |

The command-line validator itself is `backend/venv/bin/python -m pipeline.cli` (run from `backend/`); see
[TESTING.md](../TESTING.md).

Removed in November 2026: `setup_test_images.sh` (downloaded stock photos of people) and `batch_test.py` (drove the
retired single-photo analyzer). Both are in git history.
