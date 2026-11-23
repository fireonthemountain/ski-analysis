# Assessment-validation pipeline

Goal: you rate a run (stance width, edge angle, angulation, ...), the app measures the same things
from your video or screenshots and answers, per item, **agrees / disagrees / inconclusive** with the
measured value, a confidence, and the frames that show it.

```
 assessment (form/JSON) ─────────────────────────────────────────────┐
                                                                     ▼
 media ─► ingest ─► pose ─► tracking + ─► turn ─► metrics ─► validation ─► report
 (1 video  (frame   (MediaPipe  smoothing   segmen-  (per-frame  engine       (result.json,
  or N      sampling) BlazePose)            tation   series)     (thresholds,  annotated frames,
  images)                                                        confidence)   annotated.mp4, charts)
```

Code: `backend/pipeline/` — one module per stage. API: `backend/api/validations.py`. UI: `frontend/src/`.

| Stage | Module | What it does |
|---|---|---|
| Ingest | `ingest.py` | Video: OpenCV/FFmpeg decode, every Nth frame to reach ~15 fps (`ANALYSIS_FPS`), first 90 s (`MAX_ANALYSIS_SECONDS`), long side ≤ 1280 px, phone rotation honoured. Images: jpg/png/webp, HEIC via macOS `sips`. One video **or** 1–40 images, never a mix. |
| Pose | `pose.py` | MediaPipe PoseLandmarker (BlazePose, 33 landmarks, 2D + estimated 3D "world" landmarks + per-landmark visibility). |
| Tracking | `pose.py`, `smoothing.py` | The crop for each frame follows the previous detection (1.8× box, widening while lost); a distant skier is found by a 3×3 tile search at 2× zoom; with several people the one nearest the last box is kept. A frame whose hip centre jumps more than a body length and back is rejected. |
| Smoothing | `smoothing.py` | Gaps ≤ 0.3 s are linearly interpolated, then a zero-phase 2nd-order Butterworth low-pass at 6 Hz. Interpolated samples get visibility 0.4, i.e. **below the 0.5 trust gate**: they keep the filter continuous but are never evidence. |
| Turn segmentation | `segmentation.py` | Leg-axis lean (2 Hz low-pass) changes sign at each edge change. A span between sign changes is a turn if peak lean ≥ 6° and duration ≥ 0.35 s. Direction is the skier's own left/right (the image side is flipped when the skier faces the camera). Needs a front/back view. |
| Metrics | `metrics.py` | Pure functions on keypoints, table below. |
| Assessment schema | `assessment.py` | Catalog of 12 rateable items with ordered rating bands and explicit thresholds; pydantic `Assessment` model. |
| Validation | `validation.py` | Per item: value, uncertainty, verdict, confidence, evidence frames. |
| Report | `report.py`, `runner.py` | `result.json`, `frames/frame_NNNNN.jpg` (skeleton + measured axes + values), `annotated.mp4` (H.264 via ffmpeg), time series for the charts. Uploaded originals are deleted after processing. |

## Why MediaPipe Pose

| | MediaPipe PoseLandmarker (chosen) | YOLO-pose (Ultralytics) | RTMPose (MMPose) |
|---|---|---|---|
| Runs on Apple-silicon Mac Mini | CPU via XNNPACK, `pip install`, no PyTorch. Measured here (M1, heavy model): ~0.1 s for a frame with no person, which includes the 9-tile search; per-frame time with a skier in view is not yet measured | needs PyTorch (MPS) | needs PyTorch + MMCV/ONNX build |
| Keypoints | 33 incl. **heel and toe** (boot-sole line → slope-independent fore-aft) | 17 COCO, no feet | 17 (26 with Halpe) |
| 3D | estimated world landmarks (needed for rotation/separation and view-independent knee angle) | none | none (separate lifter) |
| Licence | Apache-2.0 | AGPL-3.0 — conflicts with this repo's MIT | Apache-2.0 |
| Weakness | single person per crop; small/distant or heavily bundled skiers; depth is a guess | better multi-person detection | best 2D accuracy, heaviest setup |

MediaPipe was already the project's dependency, is the only one of the three giving feet + 3D without
PyTorch, and its weaknesses are the ones the crop tracker addresses. `pose.py` defines a small
`PoseEstimator` protocol, so RTMPose can be added behind the same interface later.
Model files (`pose_landmarker_{heavy,full,lite}.task`) download once from Google's model host into
`backend/models/`; pick with `POSE_MODEL` (default `heavy`).

**Not yet validated on real ski footage** — see "Known limits".

## Metrics

Image coordinates: x right, y down. 3D: metres, origin mid-hip, x right, y down, z away from camera.
A metric is only produced for a frame when every landmark it needs has visibility ≥ 0.5.

| Metric | Definition | Needs |
|---|---|---|
| Inclination (lean) | angle of ankle-mid → hip-mid from image vertical | front/back view |
| Edge-angle proxy | lateral tilt of the **outside** leg's shin (knee–ankle) from vertical, signed into the turn. Outside leg is chosen geometrically (ankle on the far side from the lean), so left/right label swaps do not matter | front/back view |
| Angulation | leg-axis lean minus torso lean (hip-mid → shoulder-mid), positive = torso more upright | front/back view |
| Stance width | ankle spacing measured **across the leg axis** ÷ hip-joint width (so the long-leg/short-leg offset in a carve is not counted as width) | front/back view (2D) or 3D |
| Fore-aft | angle from ankle to centre-of-mass proxy (0.45 hip + 0.374 shoulder + 0.112 knee + 0.064 ankle) relative to the slope normal, taken from the heel→toe boot-sole line; falls back to image vertical (confidence ×0.6) when the feet are not visible | side view |
| Knee angle | included hip–knee–ankle angle, 3D; in 2D only from a side view (a front view foreshortens it, so no value is reported) | 3D or side view |
| Hip angle | torso axis vs thigh, 3D | 3D or side view |
| Flexion/extension range | 90th − 10th percentile of knee angle | video ≥ 2 s |
| Separation | yaw of the shoulder line minus yaw of the feet (heel→toe), 3D; falls back to shoulders vs pelvis | 3D |
| Counter / rotation | separation signed by turn direction, median over the **second half of each turn** (peak lean → edge change): + = upper body faces the outside of the turn. A downhill-facing upper body faces the *inside* of the turn before the fall line, so a whole-turn median cancels to ~0 | 3D + front/back view; video needs segmented turns |
| Turn shape | fraction of the turn elapsed when lean reaches 70 % of its peak (sine ≈ 0.25, snapped edge < 0.1) | video, ≥ 2 complete turns |
| Symmetry | (right peak lean − left peak lean) / mean | video, both directions |
| Pole plant timing (experimental) | a ≥ 0.12-torso-length downward reach of the new inside wrist near each edge change, timed as a fraction of turn duration | video, ≥ 3 edge changes |

Camera view is auto-detected from how wide the shoulders/hips look across the torso axis
(≥ 0.62 = front/back, ≤ 0.27 = side, between = oblique) and can be set by hand in the form.

3D sanity gates (per frame): a 3D body with shoulder joints < 0.20 m or hip joints < 0.10 m apart is "collapsed"
(seen on distant skiers) and that frame gets no 3D metrics: rotation, 3D stance width, joint angles. There is no 2D
fallback, so foreshortened angles never mix in. A separation beyond ±110° (anatomically impossible; it comes from left/right labels
swapped between upper and lower body) is dropped too. `result.json` reports `pose.frames_3d_rejected`, and the run
warns when that is ≥ 10 % of detected frames. Evidence frames show the frame nearest the reported value (and the
5th/95th percentile frames for range ends), not the extreme frame, which is usually a bad pose.

## Thresholds (defaults — tune in `backend/pipeline/assessment.py`)

PSIA describes the fundamentals qualitatively; **these cut-offs are this tool's engineering defaults,
not published PSIA numbers.** Each is shown in the UI next to the verdict.

| Item | Bands | Uncertainty floor | Confidence cap |
|---|---|---|---|
| Stance width | narrow < 0.75 ≤ functional < 1.5 ≤ wide (× hip width) | 0.15 | 1.0 |
| Fore-aft | aft < −4° ≤ centered < 12° ≤ forward | 5° | 1.0 |
| Stance height (knee) | low < 120° ≤ athletic < 155° ≤ tall | 6° | 1.0 |
| Hip flexion | folded < 105° ≤ athletic < 150° ≤ upright | 7° | 1.0 |
| Flexion/extension range | static < 15° ≤ moderate < 30° ≤ active | 5° | 1.0 |
| Edge angle (peak) | low < 20° ≤ moderate < 40° ≤ high | 4° | 1.0 |
| Angulation | banked < 5° ≤ moderate < 18° ≤ strong | 4° | 1.0 |
| Separation | little < 10° ≤ moderate < 35° ≤ strong | 8° | 0.6 (monocular depth) |
| Counter | rotated < −10° ≤ square < 10° ≤ countered | 8° | 0.6 |
| Turn shape | abrupt < 0.15 ≤ round | 0.04 | 0.7 (experimental) |
| Symmetry | left stronger < −20 % ≤ symmetric < 20 % ≤ right stronger | 8 % | 1.0 |
| Pole plant | early < −0.15 ≤ on time < 0.12 ≤ late; or "no visible plant" | 0.06 | 0.55 (experimental) |

## Verdict and confidence rules

1. `u = sqrt(floor² + spread²)`, spread = 1.4826·MAD/√n (n = turns, or ~2 per second of video, or number of stills).
2. `margin` = distance from the measured value to the nearest edge of the band **you** chose (+ inside, − outside).
   - `margin ≥ u` → **agree**; `margin ≤ −u` → **disagree**; otherwise → **inconclusive (borderline)**, value still shown.
3. Always **inconclusive**, with the reason stated, when: no skier detected; fewer than 5 confident frames (video) or 0 (stills);
   wrong or oblique camera view for a view-dependent item; stills given for a video-only item; no turns / too few turns;
   no 3D landmarks for a 3D item; knee/hip angle without 3D from a non-side view.
4. `confidence = cap × pose visibility × sample factor × penalties × (0.6 + 0.4·min(1, |margin|/2u))`.
   Below **0.30** the verdict is withdrawn (inconclusive), and the UI says what the measurement pointed to.
   Labels: high ≥ 0.7, medium ≥ 0.5, low below.

Video vs screenshots: stills support stance width, fore-aft, knee/hip angle, edge angle, angulation, separation and
counter — "edge angle" then means *the largest among the frames you supplied*. Turn shape, symmetry, flexion range and
pole-plant timing need video and say so.

## Known limits

- **Real-footage validation so far: public instructor clips only** (ANALYSIS-2026-11.md §9). They confirmed the 3D axis
  convention and the separation/turn-direction signs, and that detection is reliable once the skier is ≥ ~15 % of
  frame height. The thresholds are still uncalibrated defaults. Check the skeleton overlay on your own footage before
  trusting numbers.
- Angles in the image plane are relative to image vertical: camera roll or a side-hill biases lean, edge angle, symmetry.
- Edge angle is a shin-tilt proxy; skis are not tracked. Pole plants are inferred from the hand; poles are not tracked.
- Depth is estimated from one camera: separation/counter are capped at 0.6 confidence. Counter's measurement
  uncertainty on real footage is about ±9–10°, so it only reaches a verdict when counter is clearly beyond about ±20°.
- One skier. One run at a time (in-process queue). The follow-cam case (camera moving with the skier) is fine for
  joint angles; nothing here uses the skier's path through the image.
