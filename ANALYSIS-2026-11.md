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
- `ski-analysis-4` November 22, 2026: the unattended run was blocked; an interactive run the same day did checks 1–3 on a
  public instructor clip (convention confirmed, signs confirmed, counter-aggregation flaw found). Check 4 (band
  calibration) still needs csather's own rated clips. See §9.
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
| ddee44b | Docs: this file, `docs/PIPELINE.md`, README quick start, MAC_SETUP note |

Nothing was pushed, merged or deployed.

## 8. Final report (short form)

- **Works:** assessment form → upload (one video or screenshots) → pose → smoothing → turns → 12 metrics → per-item
  agree / disagree / inconclusive with value ± uncertainty, confidence and annotated evidence frames → results page with
  agreement table, annotated video and charts. Runs with `scripts/run_dev.sh`, no Docker, reachable on the LAN at port 5177.
- **Tests:** 116 passed, 0 failed (73 metric unit tests, 35 engine tests, 8 HTTP end-to-end tests); frontend build passes.
- **Not proven:** accuracy on real ski footage. Everything above was verified on a synthetic stick figure; MediaPipe
  itself has only been shown to load, run, and return "no skier" on that figure. Thresholds are uncalibrated defaults.
- **Not done:** `ski-analysis-1` (open-source checklist); refresh of the older docs; full `docker compose up` run.
- **Next step for csather:** run one front-on clip of his own through it and look at the overlay (`ski-analysis-4`).

## 9. `ski-analysis-4` — first real-footage validation (November 22, 2026): checks 1–3 run on a public stand-in clip

**Status: checks 1–3 done on public instructor footage; check 4 (band calibration) still needs your own rated clips.**
Results are in "Results: stand-in clip run" below. Short version: the world-landmark convention is confirmed
(x right, y down, z away). Separation and turn-direction signs are confirmed against the skier's actual path. Speed
is about 0.1 s per frame. Detection is reliable once the skier is at least 15% of frame height. Two problems
surfaced: the `counter` item read about 0 for countered skiers because it took the median over the whole turn; and
Homebrew's ffmpeg on this Mac was broken. **Both are repaired (§10)**, along with 3D sanity gates and evidence-frame
choice. Thresholds are unchanged.

History: an unattended run earlier on November 22 was blocked
(below) and added `scripts/validate_shots.sh` and git-ignored files under `videos/`, all untested. An interactive
session the same evening ran the checks.

### Why the first (unattended) attempt was blocked

| Blocker | Evidence |
|---|---|
| No footage of csather in the project | Searched the whole repo, git-ignored folders included, for mp4/mov/m4v/avi/mkv/webm/jpg/jpeg/png/heic: only `examples/synthetic/` (the stick figure). `backend/data/` is empty, so nothing has been uploaded through the UI either. Per the task rules I did not download footage of real people and did not look outside the project folder. |
| The unattended session could not run the backend Python | Every venv Python call needed interactive permission approval, which an unattended run cannot give: `./venv/bin/python -m pipeline.cli --list-items`, `./venv/bin/python -m pytest --version`, and a plain `-c "import mediapipe"` were all refused. So no MediaPipe run, no speed measurement, and the test suite was **not** re-run (the 116-passed figure in §4 is from November 15). |

To unblock: put clips in `videos/` (step 0 below) and either follow the runbook yourself or run the task in an
interactive session where the venv Python can be approved.

### What I could establish without running anything

**(a) The world-landmark axis convention is not documented locally.** The installed MediaPipe 0.10.35 says only
"z: The z coordinate" (`venv/.../mediapipe/tasks/python/components/containers/landmark.py`). MediaPipe's online guide gives
a direction only for the *normalised* z (smaller = closer to the camera) and describes world landmarks as metres from
the hip midpoint without stating axis directions. The x right / y down / z away assumption in `axis_yaw`
(`backend/pipeline/metrics.py:82`) is therefore still unverified, as §4 said.

**(b) A wrong convention is loud, so any front-on clip with the boots visible tests it — not only an obvious-counter
clip.** Working through `axis_yaw` and `forward_yaw`: if MediaPipe's world frame had the other handedness (z toward the
camera, or x mirrored), the shoulder/hip headings (from left→right vectors) and the feet heading (heel→toe) would come
out about **180° apart in every camera view**. What that looks like:
- *Feet visible (the normal case):* `separation` reads roughly 130–180°, rated "strong" and far beyond anything a skier
  does; the separation chart sits near ±180°. With the right convention real values should be well under 90°.
- *Feet not visible* (the item's notes say "Feet not confidently visible ... against the pelvis"): `separation` and
  `counter` just change sign, with nothing to flag it. A countered skier would read "rotated".

Handedness belongs to the model, not the clip, so one front-on clip with boots visible and separation < 90° confirms
the convention for both paths. The obvious-counter clip is still worth filming, but what it tests is different:
whether MediaPipe's depth estimate is good enough to get the *sign* of real counter right.

**(c) Front/back label confusion does not change counter.** If MediaPipe mistakes a back-view skier for a front-facing
one and swaps left/right (plausible with helmet and goggles), the turn direction (from `facing`) and the separation sign
flip together, so `counter` is unchanged, and the separation item uses |separation|. Do the convention check on a clip
where you ski **toward** the camera (face visible, labels most reliable). Near-180° separation on only *some* frames of
a back-view clip is label swapping, not the convention.

**(d) Speed and detection rate go together.** Per frame, `pose.py` runs the heavy model on a crop around the last skier
box; if that misses, on the full frame; and once the skier has been lost for 8 frames, on the full frame **plus 9
half-frame tiles** — up to 10 model passes per frame (`backend/pipeline/pose.py:106-120`). A skier who is too small in
frame therefore makes a run both slow and low-detection; the fix is filming tighter or cropping, not a faster model.
Knobs: `POSE_MODEL=full` or `POSE_MODEL=lite` (both already in `backend/models/`) and `--fps 10`.

**(e) Bands most likely to need tuning — hypotheses to check, nothing changed:**
- `stance_height` (120/155°) and `hip_flexion` (105/150°) use the 3D estimate. Seen front-on, most knee and hip bend is
  along the depth axis, the poorly estimated one, so these may read straighter than reality ("tall"/"upright"
  over-reported). If your clips show that, raise the bounds.
- `stance_width` (0.75/1.5×) divides by the distance between MediaPipe's hip *joint* landmarks, which is narrower than
  the hips you see; a stance that looks "hip width" may measure 1.2–1.5× and tip into "wide".
- `fore_aft` (−4/12°): the centred band is about as narrow as the pose noise (§4); expect "inconclusive" rather than wrong.

### Runbook (when you have clips)

**0. Footage.** Put clips and screenshots in `videos/` at the project root: that folder is git-ignored as a whole.
Elsewhere only `.mp4/.mov/.avi/.mkv` are ignored, so `.m4v`, `.webm`, `.jpg`, `.png` and `.heic` would show up in
`git status`. Minimum set — you, full body with boots visible, at your usual filming distance, 3+ turns each:
- **A** front-on, skiing toward the camera, normal skiing (checks 1, 2, 3a, 4)
- **B** same, deliberately exaggerated counter: upper body facing down the hill / to the outside of each turn (check 3b)
- **C** (optional) same, deliberately rotating the shoulders into each turn (the opposite sign)
- **D** (optional) side-on, for fore-aft

**1. Environment check**
```
cd backend                                   # from the repo root
./venv/bin/python -m pytest tests -q          # expect 116 passed
./venv/bin/python -m pipeline.cli --list-items
```

**2. Rate clip A blind, then run it.** Copy `examples/assessment.example.json` to `videos/clipA.json` and, *before*
looking at any output, set every rating to what you see. Add `fore_aft` and `hip_flexion` (the example leaves them out)
so all 12 items get measured. Then:
```
./venv/bin/python -m pipeline.cli --assessment ../videos/clipA.json ../videos/clipA.mov --out ../videos/out-clipA
```
Keep `--out` under `videos/`: the CLI default (`backend/validation-output/`) is not git-ignored and holds frames of you.

Summary of the numbers checks 1–3 need (stdlib only, so system `python3` is fine; written but not run here):
```
python3 - ../videos/out-clipA/result.json <<'EOF'
import json, sys
r = json.load(open(sys.argv[1])); p = r["pose"]
print(f"{p['frames']} frames, {p['frames_detected']} detected ({p['frames_detected']/p['frames']:.0%}), "
      f"{p['frames_confident']} confident ({p['frames_confident']/p['frames']:.0%}), 3D={p['has_3d']}")
print(f"{r['processing_seconds']/p['frames']:.2f} s/frame, {r['processing_seconds']:.0f} s total, view={r['view']}")
for x in r["results"]:
    if x["item_id"] in ("separation", "counter"):
        m = x["measured"] or {}
        print(x["label"], m.get("value"), "+/-", m.get("uncertainty"), "|", x["verdict"], "|", "; ".join(x["notes"]) or "-")
EOF
```

**3. Check 1 — overlay and detection.** Play `videos/out-clipA/annotated.mp4`: the skeleton should sit on you (not on
another skier or a lift tower), with the ankle/heel/toe points on the boots. My acceptance assumption: ≥ 80% of frames
detected and no WARNING line from the CLI (it warns below 50% detected or 60% confident). If it fails, zoom or crop so
you fill more of the frame and re-run.

**4. Check 2 — speed.** Read s/frame from the summary. It is an upper bound (it includes decode, JPEG writes,
annotation and video encoding). My assumption for "acceptable": a 30 s clip finishes in under 5 minutes. If slower,
look at the detection rate first (see (d)), then try `POSE_MODEL=full`.

**5. Check 3a — axis convention (clip A).** Look at the separation line of the summary:
- notes say "Feet not confidently visible" → this clip cannot test it; use one with boots visible
- value < ~60° → convention OK
- value > 90° → convention wrong. Stop and do not trust separation or counter. The fix is a sign change on one world
  axis where `world` is built (`backend/pipeline/pose.py:93`); which axis needs a look at the raw world landmarks, so
  bring the clip to an interactive session.

**6. Check 3b — counter sign (clip B, and C if filmed).** Run B the same way. Counter should be positive, ideally above
+10° ("countered"); C should be negative.
- B clearly negative while 3a passed → the 2D turn-direction side (`facing`/`lean_skier` on real left/right labels) is
  wrong, not the 3D convention
- B near 0 → depth is too weak to see counter; keep the item low-trust (it is already capped at confidence 0.6)

**7. Check 4 — calibrate the bands.** For each clip, write one row per item: item | clip | your rating | measured ±
uncertainty | band it fell in. Move a bound (`bounds=` in `backend/pipeline/assessment.py`) only when at least 2 clips
disagree in the same direction **and** the measured value sits outside your band by more than its ± uncertainty. Put
the new edge midway between the measured values you rated on either side. Every middle band must stay wider than
2 × `base_uncertainty` (`test_catalog_is_consistent`, `backend/tests/test_validation.py:23`, fails otherwise). Re-run
`pytest`, and record the before/after bounds and the clips behind them in this file.

### Public stand-in clip (added November 22, 2026, after csather sent a link)

csather sent a YouTube link: **Nordica, "Pro Series Level 2: How to Pass Your Level 2 Ski Instructor Certification
Exam"** (`Tmlx2mtBIWU`, 15:40). It shows demo skiing by PSIA-AASI National Team members and a Pacific Northwest
examiner. I took the link as the go-ahead to use this published footage as a stand-in, setting aside the "no footage of
real people" rule for this one clip. It is Nordica's video, so it is local test material only: it lives in git-ignored
`videos/` and should not be committed or redistributed.

The unattended session **could not run it**: `yt-dlp`, `ffmpeg` and the venv Python all needed approval. (It was run
later that day in an interactive session; see "Results: stand-in clip run" below. That run cut its own clips and did
not use `run.sh`/`validate_shots.sh`, which are still untested.) What `curl`
(allowed) did get: the chapter list from the public description, and YouTube's storyboard previews (one frame per 10 s,
saved in `videos/yt-Tmlx2mtBIWU-thumbs/`), which show the camera angles.

| Chapter | What the previews show | Use |
|---|---|---|
| Short Radius Turns 12:53–14:31 | Mostly front-on, skiers coming toward the camera. Often two skiers in follow formation, often small and distant in flat light, falling snow. One close single-skier shot around 14:30. | Checks 1, 2, 3a, 3b. Task definition: "turn legs separately from the upper body through the entire turn", so counter should be clearly positive. |
| Railroad Tracks 14:31–14:45 | Two skiers side by side, front-on, close | Contrast case: pure edging, so counter should be near 0 and separation small |
| Hockey Stops 0:42–1:14 | One distant and one close hockey-stop shot, plus talk | Legs turned across the hill under a downhill-facing upper body: separation should be the largest of the three |
| Funnel Turn 10:50–12:53 | Mostly a tiny, distant skier; text overlays | Skipped |

**What it can and can't tell us**
- *Can:* check 1 at YouTube distances and with two skiers in frame (does the tracker stay on one?); check 2; check 3a
  (front-on, skiing toward the camera, boots visible); check 3b against an expert reference (short-radius counter
  clearly positive, railroad tracks near 0).
- *Can't:* check 4. The ratings in the assessment files come from the PSIA task definitions, not from your eye. The
  measured values are a first look at where expert demos land on each scale, not a calibration.
- *Footage caveats:* the video is cut every few seconds (hence the shot splitting), so each shot holds only 1–4 turns
  and turn-based items will often be inconclusive. Two skiers in one frame can make the tracker switch skier. Any
  slow-motion segments would distort the timing items (turn shape, pole plant) but not the angles. YouTube compression
  costs some detail.

**How to run (one command; written but not run here)**
```
cd <repo root>
videos/nordica-l2/run.sh            # all three chapters; or: run.sh short | railroad | hockey
```
- `run.sh` downloads the clip once (1080p H.264, no audio) into `videos/yt-Tmlx2mtBIWU/source.mp4`, then calls
  `scripts/validate_shots.sh` for each chapter.
- `scripts/validate_shots.sh VIDEO START END ASSESSMENT.json OUTDIR` is new and generic, so it works on your own edited
  clips too. It cuts the section out, splits it at camera cuts (ffmpeg scene detection), runs `pipeline.cli` on every
  shot of at least 3 s, and writes `OUTDIR/summary.md` with one row per shot (source time, frames, detected %,
  confident %, s/frame, view, turns, and each item's measured value and verdict).
- Assessment files: `videos/nordica-l2/{short_radius,railroad_tracks,hockey_stops}.json`. Every item is rated so that
  every item gets measured. Ratings marked `expected` follow the task definition; `placeholder` ratings only exist to get
  a measurement, so ignore their verdicts.

**Reading the result** (`videos/nordica-l2/out-*/summary.md`; skip talk-to-camera rows)

| Check | Look at | Pass |
|---|---|---|
| 1 | each `shot_NN/annotated.mp4`; detected / confident columns | skeleton on one demo skier for the whole shot (no jumping to the second skier); ≥ 80% detected where the skier is reasonably large |
| 2 | s/frame | record it; slow *and* low detection together means the skier is too small (see (d)) |
| 3a | separation on front-on shots | well below 90° everywhere; 130–180° means the axis convention is wrong (step 5 above) |
| 3b | counter | short radius clearly positive (above +10°); railroad tracks within ±10°; short radius above railroad tracks every time |
| sanity | separation by chapter | hockey stops largest, railroad tracks smallest |

A pass on 3a/3b here settles the convention question without your footage. Checks 1, 2 and 4 still need your own clips
at your usual filming distance, rated by you.

### Results: stand-in clip run (November 22, 2026, interactive session)

**Setup.** The 1080p H.264 video stream (format 137, no audio) was downloaded to the session scratchpad, not the repo.
Clips were cut with OpenCV at shot boundaries found by eye from contact sheets; ffmpeg could not be used (see
"Environment" below). Each clip ran through `backend/venv/bin/python -m pipeline.cli --assessment X.json clip.mp4`
(MediaPipe heavy, 15 fps analysis, Mac Mini). The assessment ratings were rough, non-expert placeholders, so the
agree/disagree verdicts carry no weight. Only the measured values matter here.

| Clip | Source time | What it is | Frames | Detected | Confident | s/frame | View |
|---|---|---|---|---|---|---|---|
| A | 11:58.6–12:23.4 (Funnel) | green skier, handheld panning camera, skis toward it from very far to close, ~12 turns | 298 | 53% | 49% | 0.095 | frontal |
| A2 | 14:16.7–14:30.2 (Short Radius) | red/blue skier, static camera below, far to close, 10 turns | 162 | 98% | 96% | 0.103 | frontal |
| B1 | 1:05.6–1:07.65 (Hockey Stops) | ground-level hockey stop, 2 s shot | 25 | 96% | 64% | 0.118 | oblique |
| B2 | 1:01.35–1:03.1 (Hockey Stops) | green skier hockey stop, 1.75 s shot | 21 | 95% | 33% | 0.112 | oblique |

Correction to the table above: the Funnel chapter is not "mostly a tiny, distant skier". 11:58.6–12:23.4 is one
continuous handheld front-on shot, the closest match to how you would film yourself, and the best clip for check 1.

**Check 1: overlay and detection.** In every evidence frame the skeleton sits on the demo skier, with ankle, heel and
toe on the boots when the skier is close. Detection depends on the skier's size in the frame. From clip A, measuring
the green suit (shoulders to boots, about 85% of full height) in every sampled frame:

| Suit height, 1080p | Share of frame height | Detected | Confident |
|---|---|---|---|
| < 60 px | < 6% | 0% | 0% |
| 60–90 px | 6–8% | 34% | 14% |
| 90–120 px | 8–11% | 70% | 44% |
| 120–160 px | 11–15% | 92% | 92% |
| ≥ 160 px | ≥ 15% | 95–100% | 95–100% |

**Rule: keep the skier at least about 15% of frame height** (about 160 px at 1080p, 110 px at 720p). Rough distance
at that size, assuming a phone's 1× main camera (about 26 mm equivalent, landscape vertical field of view about 43°)
and a skier about 1.5 m tall in stance: roughly 13 m at 1×, 26 m at 2×, 40 m at 3×. That is an estimate; check it
against one of your own clips. Small skiers sometimes get a **collapsed** pose: left and right shoulders and hips
land on top of each other. Those frames give impossible 3D values (separation −114°, stance
width 3.6–6.6× hip width). The −114° frame was the one the separation item showed as its evidence. They are rare
(1 of the 6 frames with a separation value in the 60–90 px bin), so the 90th-percentile separation value barely moved.
A follow-up per-frame analysis (§10) found a size cutoff is the wrong gate: it would discard 232 good frames to catch 8
bad ones. A 3D body-width check catches the collapse directly.

**Check 2: speed.** 0.095–0.12 s per analysed frame, covering pose, metrics and evidence JPEGs, but not
`annotated.mp4`, which was skipped (see "Environment"). At 15 fps that is about 1.5 s of compute per second of video.
Clip A (24.8 s) took 31 s wall time including model load, about 6× inside the "30 s clip in under 5 minutes" target.
Frames where the skier is lost (up to 10 model passes each) did not noticeably slow the average.

**Check 3a: world-landmark axis convention: confirmed (x right, y down, z away from the camera).** Raw MediaPipe
world landmarks were read on 14 frames where the person clearly faces the camera: presenters standing to camera,
plus skiers coming straight at it.

| Test (person facing camera) | Expected if the convention holds | Observed, 13 of 14 frames |
|---|---|---|
| nose z minus hip-centre z | negative (closer) | −0.16 to −0.58 m |
| toe z minus heel z | negative (toes toward camera) | −0.02 to −0.11 |
| world x (R shoulder − L shoulder) | same sign as image x | both negative |
| nose y | negative (up) | −0.37 to −0.63 |

The 14th frame (14:29.0) had every sign flipped at once: MediaPipe swapped left/right and read the skier as facing away.
Separation still came out small (6°), which confirms prediction (c) above that a front/back label swap leaves counter
alone. On the front-on clips, separation (90th percentile of |value|) was 33–35°, far below the 90° failure threshold.

**Check 3b: separation and counter signs: correct. The counter *item* is not.** Two independent checks on the
static-camera clip A2 compare against the skier's actual path in the image, so they don't depend on MediaPipe depth:

| Check | Physical expectation | Result |
|---|---|---|
| separation vs hip image-x velocity | positive: with a steady upper body, separation ≈ −(ski heading); heading to the skier's right moves the skier image-left in a front view | r = +0.56, 77% sign agreement |
| `lean_skier` vs hip image-x acceleration | negative: a right turn accelerates toward the skier's right, which is image-left | r = −0.90, 93% sign agreement |

Separation swings ±20–40° once per turn and crosses zero near peak lean. That is the pattern of a stable,
downhill-facing upper body with the skis turning under it. **But the item reports the median over every frame with at
least 8° of lean, and that cancels out:**

| Counter, median | Clip A | Clip A2 |
|---|---|---|
| before peak lean (initiation) | −14.8° | −18.4° |
| after peak lean (shaping/finish) | **+12.2°** | **+11.3°** |
| all frames (what the item reports) | −1.6° → "square" | −1.3° → "square" |

Before the skis cross the fall line, a downhill-facing upper body faces the *inside* of the new turn; after, it faces
the outside. So whole-turn averaging makes a textbook-countered skier read "square". This is a flaw in how the
metric is defined, not a sign or depth problem. It contradicts step 6's reading of "B near 0" as "depth too weak".
Fixed in §10: counter is now measured on the shaping/finish phase only (peak lean to the edge change). L2 demos now
read +10.5° and +10.9°, right on the edge of "countered", so the ±10° band is the open calibration question.

The hockey-stop shots were not usable: 1–2 s each, oblique, so `counter` is withheld by the view gate and separation
lacks confident frames. The two short-radius clips served as the obvious-counter test instead.

**Check 4: band calibration: not done.** It needs your ratings of your own clips. For reference only (expert demos,
not calibration): stance height 129–144°, hip flexion 119–131°, stance width 0.98–1.22× hip width (the hypothesis in
(e), that hip-width stances would read 1.2–1.5×, did not show), edge angle 41–50° peak, flexion/extension range 33–44°.

**Environment.**
- Homebrew ffmpeg 8.1.2 cannot start: `dyld: Library not loaded: /opt/homebrew/opt/x265/lib/libx265.216.dylib`
  (x265 was upgraded underneath it). `shutil.which("ffmpeg")` still finds it, so:
  - `report.encode_video` swallows the error and silently skips `annotated.mp4`.
  - `synthetic.write_video` raises, so **3 e2e tests error** (113 passed + 3 errors). With Homebrew off PATH (OpenCV
    fallback), **116 passed**. No code regression.
  - `scripts/validate_shots.sh` would stop at its first ffmpeg call.
  - Fixed in §10: `brew upgrade ffmpeg` to 9.0.2, and `ffmpeg_path()` now ignores a binary that won't start.

### Follow-ups for `ski-analysis-6`
- Automatic handedness self-check: per frame `wrap(forward_yaw(feet) − axis_yaw(hips))`; if its median magnitude is
  above 90°, add a run warning and withhold separation/counter. That makes check 3a happen on every run.
- Record pose-only time (`pose_seconds`) in `result.json` so speed can be measured without the rendering overhead.
- ~~Separation evidence captioned "shoulders vs feet" even on the pelvis fallback~~: done in §10.
- ~~Counter by turn phase; collapsed far-away poses; evidence by max |value|; `ffmpeg_path()` check~~: done in §10
  (ledger `ski-analysis-8`).

## 10. Repairs after the stand-in run (November 22, 2026; ledger `ski-analysis-8`)

**Status: done; uncommitted.** Tests: **122 passed** (116 existing + 6 new) with the working ffmpeg 9.0.2.
Thresholds/bands unchanged.

| Change | Where | Why |
|---|---|---|
| Homebrew ffmpeg 8.1.2 → 9.0.2 (`brew upgrade ffmpeg`) | this Mac, not the repo | 8.1.2 linked a removed `libx265.216.dylib` and aborted at start-up |
| `ffmpeg_path()` only returns an ffmpeg that actually starts (cached per resolved binary); `write_video` falls back to OpenCV if the encode fails | `pipeline/synthetic.py` | a broken install passed `shutil.which`, so the e2e tests errored and `annotated.mp4` was silently skipped |
| Startup and script checks now say "installed but will not start" | `scripts/run_dev.sh`, `scripts/validate_shots.sh` | same failure, caught before a run |
| **Counter scored on the second half of each turn only** (peak lean → edge change); video without segmented turns → unavailable with the reason; stills get a note | `pipeline/validation.py` `eval_counter`, `_finish_phase_mask`; measure text in `pipeline/assessment.py` | whole-turn median cancelled to ~0 (§9 check 3b) |
| **3D sanity gates**: a frame whose 3D shoulders are < 0.20 m or hips < 0.10 m apart gets no 3D metrics (rotation, 3D stance, joint angles; no 2D fallback); separation beyond ±110° is dropped | `pipeline/metrics.py` `world_plausible`, `MIN_WORLD_SHOULDER_W`, `MIN_WORLD_HIP_W`, `MAX_SEPARATION_DEG`, `world_rejected` series | collapsed far-away poses and upper/lower label swaps gave impossible values |
| `pose.frames_3d_rejected` in `result.json`; run warning when ≥ 10% of detected frames | `pipeline/runner.py` | make the gate visible |
| Evidence frames = frame nearest the reported value; range ends at 5th/95th (stance etc.) or 10th/90th (flexion range) percentile; edge-angle turn evidence nearest the per-turn 95th percentile; separation caption says feet or pelvis | `pipeline/validation.py` | the max-\|value\| frame was the −114° collapse frame |
| `RunSpec.stable_upper_body` (shoulders on the fall line, counter a quarter-turn out of phase with lean) | `pipeline/synthetic.py` | lets tests reproduce the real-skier pattern the old generator could not |
| Counter row, 3D gates, known limits | `docs/PIPELINE.md` | docs match behaviour |

**How the gates were chosen** (every frame of clips A and A2, 648 detected frames, tracking on):
- 11 frames looked implausible. A pixel-size cutoff would have been the wrong tool: excluding skiers of 80–140 px
  would discard 232 good frames to catch 8 bad ones, and 3 bad frames were close-ups.
- 3D body width separates them directly. Plausible frames have shoulder-joint width at the 5th percentile 0.27 m
  (median 0.33) and hip-joint width at the 5th percentile 0.15 m (median 0.20); collapsed frames measured
  0.07–0.14 m. The 0.20/0.10 m gate rejects 22/648 frames (3.4%). Most of those had no separation value anyway or
  were bogus 12–31 px detections.
- The ±110° ceiling catches the one remaining label swap (−142°). The largest plausible separation was 69°.

**New tests**: collapsed 3D body → no 3D metrics and no 2D joint-angle fallback; swapped feet labels → separation
dropped, pelvis twist kept; stable-upper-body run → whole-turn median ≈ 0 but counter judged "countered" (and the
mirror case "rotated"); video with no turns → counter unavailable; separation evidence is a typical frame even with
an injected 95° outlier; a fake ffmpeg that aborts counts as missing and `write_video` still produces a file.

**Re-run on the real clips**

| | Clip A (funnel) | Clip A2 (short radius) |
|---|---|---|
| counter before → after | −2.1° → **+10.9°** (12 turns, 58 frames) | −1.3° → **+10.5°** (10 turns, 65 frames) |
| counter verdict for "countered" | borderline (10.9 ± 9.0 vs the +10° edge; confidence 0.29) | borderline (10.5 ± 9.7; confidence 0.27) |
| separation evidence frame | −114° collapse frame → typical +33° | typical +34° (pelvis fallback, now labelled) |
| frames with 3D rejected | 12 / 158 detected | 9 / 158 detected |
| `annotated.mp4` | written (4.7 MB) | written (3.7 MB) |

**`scripts/validate_shots.sh` tested** on 13:40–14:31: 5 shots found, 1 dropped (< 3 s), 4 validated, `summary.md`
written, 1 min 42 s total. Counter on the four short-radius shots: **+16, +16, +12, +11°**. That includes shot_02, a
drone shot from behind ("USA" on the back), which was correctly labelled "away from camera", so the sign also holds
in a back view. `videos/nordica-l2/run.sh` itself (its download step) was not run; the script it calls was.

**Still open**
- **Check 4 (bands).** L2 short-radius demos measure +10 to +16° counter with about ±9–10° uncertainty, against a
  +10° "countered" edge. At that uncertainty counter only reaches a verdict when it is clearly beyond about ±20°.
  Whether to move the edge (and to where) needs your ratings of your own clips.
- Nothing is committed or pushed.
