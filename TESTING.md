# Testing

Two kinds of testing: the automated suite (synthetic data with known answers), and checking the app on real ski
footage. Design and thresholds: [docs/PIPELINE.md](docs/PIPELINE.md). What has been validated so far:
[ANALYSIS-2026-11.md](ANALYSIS-2026-11.md) §9–12.

## Automated tests

```bash
cd backend && ./venv/bin/python -m pytest tests -q
cd frontend && npm run build          # TypeScript type-check + production build
```

| File | Covers |
|---|---|
| `backend/tests/test_metrics.py` | every per-frame metric on synthetic skeletons of known geometry (lean, angulation, edge proxy, stance width, knee/hip angles, fore-aft, separation, counter sign, 3D sanity gates, view classification) |
| `backend/tests/test_validation.py` | smoothing, turn segmentation, every evaluator and verdict rule on scripted runs (correct and wrong assessments, borderline values, low confidence, wrong view, no 3D, counter on the turn finish phase, not-skiing short-circuit, broken ffmpeg fallback) |
| `backend/tests/test_identity.py` | one-person tracking (switch detection, glitch rejection, returning person) and the seated check |
| `backend/tests/test_e2e.py` | the HTTP API end to end with the marker estimator on rendered synthetic media |

The tests never load the MediaPipe model (`POSE_ESTIMATOR=marker`) and never touch `backend/data`. CI
(`.github/workflows/ci.yml`) runs the backend suite and the frontend build on every push and pull request.

## Quick check without footage

```bash
backend/venv/bin/python scripts/make_sample_media.py     # renders examples/synthetic/ (stick figure + ground truth)
POSE_ESTIMATOR=marker scripts/run_dev.sh                 # MediaPipe doesn't see a stick figure as a person
```

Open http://localhost:5177, upload `examples/synthetic/synthetic_run_front.mp4`, rate a few items, and compare the
measured values with `examples/synthetic/ground_truth.json`.

## Testing with real footage

### Film it so it can be measured

- **One continuous shot, one skier**, 10–30 s, at least 3 turns. Edited videos with camera cuts: see below.
- **Skiing toward (or away from) the camera** for edging, angulation, rotation/counter, turn shape, symmetry and pole
  plants; **side-on** for fore-aft.
- **Big enough:** the skier at least ~15% of the frame height (about 160 px in 1080p). Below ~8% detection mostly fails.
  Zoom rather than walk closer.
- **Boots visible.** The feet set the ski direction for separation and counter.
- No slow motion (it distorts the timing items).

### Run it

UI: `scripts/run_dev.sh`, then open the URL it prints. Or the command line:

```bash
cd backend
./venv/bin/python -m pipeline.cli --list-items                     # items and rating options
cp ../examples/assessment.example.json ~/my_run.json               # set your ratings BEFORE looking at results
./venv/bin/python -m pipeline.cli --assessment ~/my_run.json ~/Movies/my_run.mov --out ~/my_run_validation
```

`--out` holds `result.json`, the annotated evidence frames (`frames/`) and `annotated.mp4` (needs a working
`ffmpeg`). Keep it out of the repo: it contains images of you.

### Edited videos (several camera shots)

```bash
scripts/validate_shots.sh VIDEO START END ASSESSMENT.json OUTDIR
```

Cuts the section out, splits it at camera cuts, validates every shot of at least 3 s, and writes `OUTDIR/summary.md`
with one row per shot. Shots longer than 40 s are listed as probably several camera shots (flat light can hide cuts).

### Read the results

1. **Look at the overlay first** (`annotated.mp4` or the evidence frames). If the skeleton isn't on the skier, the
   numbers mean nothing.
2. **Read the warnings**: few confident frames, collapsed 3D poses, a person switch, "seated, not skiing".
3. **Inconclusive is an answer**: it says why (wrong view, too few frames, borderline). It never guesses.
4. A *disagree* with high confidence is where your eye and the measurement differ most. Check those frames.

### What has been checked on real footage

Public instructor clips (Nordica Pro Series Level 1–3) confirmed the 3D axis convention and the rotation signs
against the skier's actual path, ~0.1 s per frame on an M1 Mac mini, and that edge angle and knee flexion rank the
three levels correctly. Not done: calibrating the thresholds against a skier's own rated clips (runbook in
ANALYSIS-2026-11.md §9).
