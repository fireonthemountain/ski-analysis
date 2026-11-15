"""Orchestrates one validation run: media -> poses -> metrics -> verdicts -> report files."""
from __future__ import annotations

import json
import os
import shutil
import time
from typing import Callable, Optional

import cv2
import numpy as np

from . import ingest, report
from .assessment import Assessment
from .keypoints import PoseFrame, PoseSequence
from .metrics import MetricSeries, compute_series
from .pose import PoseEstimator, get_estimator
from .segmentation import segment_turns
from .smoothing import smooth_sequence
from .validation import Context, summarize, validate

Progress = Callable[[float, str], None]

CHART_SERIES = ["inclination", "edge_proxy", "angulation", "torso_tilt", "knee_left", "knee_right", "knee_mean",
                "hip_angle", "stance_width_2d", "stance_width_3d", "fore_aft", "separation", "counter",
                "wrist_drop_left", "wrist_drop_right"]


def _clean(v):
    """numpy -> JSON-safe (NaN -> None)."""
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 3)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, np.ndarray):
        return [_clean(x) for x in v.tolist()]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def analyze_sequence(seq: PoseSequence, assessment: Assessment) -> tuple[PoseSequence, MetricSeries, Context, dict]:
    """Pose sequence -> smoothed sequence, metric series, validation context, smoothing stats."""
    seq_s, stats = smooth_sequence(seq)
    view = None if assessment.camera_view == "auto" else assessment.camera_view
    ms = compute_series(seq_s, view=view)
    turns, incl_s = [], np.full(len(ms), np.nan)
    if seq.is_video and ms.view in ("frontal", "oblique"):
        fac = ms.values["facing"][np.isfinite(ms.values["facing"])]
        facing_sign = float(np.sign(np.median(fac))) if len(fac) else None
        turns, incl_s = segment_turns(ms.t, ms.values["inclination"], ms.valid("inclination"), ms.fps, facing_sign)
    return seq_s, ms, Context(ms=ms, turns=turns, incl_smooth=incl_s), stats


def run_validation(assessment: Assessment, media_paths: list[str], out_dir: str,
                   estimator: Optional[PoseEstimator] = None, progress: Optional[Progress] = None,
                   target_fps: float = 15.0, max_seconds: float = 90.0, make_video: bool = True) -> dict:
    """Run the whole pipeline. ``media_paths`` is one video OR one-or-more still images.
    Writes result.json + frames/ (+ annotated.mp4) into ``out_dir`` and returns the result dict."""
    t0 = time.time()
    progress = progress or (lambda p, msg: None)
    kinds = {ingest.kind_of(p) for p in media_paths}
    if None in kinds:
        raise ValueError("Unsupported file type. Use one video (mp4/mov/m4v/avi/mkv/webm) or images (jpg/png/webp/heic).")
    if "video" in kinds and (len(media_paths) != 1 or "image" in kinds):
        raise ValueError("Upload either ONE video or a set of still images, not a mix.")
    is_video = kinds == {"video"}

    os.makedirs(out_dir, exist_ok=True)
    raw_dir, frames_dir = os.path.join(out_dir, "raw"), os.path.join(out_dir, "frames")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    own_estimator = estimator is None
    est = estimator or get_estimator()
    est.reset()
    frames: list[PoseFrame] = []
    raw_paths: list[str] = []
    media_info: dict = {"kind": "video" if is_video else "images", "files": [os.path.basename(p) for p in media_paths]}

    try:
        if is_video:
            info = ingest.probe_video(media_paths[0])
            step, fps = ingest.sampling_plan(info, target_fps, max_seconds)
            expected = max(1, int(min(info.duration or max_seconds, max_seconds) * fps))
            media_info.update(source_fps=round(info.fps, 3), analysis_fps=round(fps, 3), width=info.width, height=info.height,
                              duration_s=round(info.duration, 2), truncated=bool(info.duration > max_seconds + 0.5),
                              max_seconds=max_seconds)
            for k, (src, t, img) in enumerate(ingest.iter_video_frames(media_paths[0], target_fps, max_seconds)):
                frames.append(est.estimate(img, k, t, source=f"frame {src}", track=True))
                p = os.path.join(raw_dir, f"{k:05d}.jpg")
                cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                raw_paths.append(p)
                if k % 10 == 0:
                    progress(0.05 + 0.75 * min(1.0, k / expected), f"Pose estimation: frame {k + 1} of ~{expected}")
            seq = PoseSequence(frames=frames, fps=fps, is_video=True, estimator=est.name)
        else:
            for k, path in enumerate(media_paths):
                img = ingest.load_image(path)
                est.reset()
                frames.append(est.estimate(img, k, 0.0, source=os.path.basename(path), track=False))
                p = os.path.join(raw_dir, f"{k:05d}.jpg")
                cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                raw_paths.append(p)
                progress(0.05 + 0.75 * (k + 1) / len(media_paths), f"Pose estimation: image {k + 1} of {len(media_paths)}")
            seq = PoseSequence(frames=frames, fps=0.0, is_video=False, estimator=est.name)
    finally:
        if own_estimator:
            est.close()
    if not frames:
        raise ValueError("No frames could be read from the media.")

    progress(0.82, "Smoothing, turn segmentation and metrics")
    seq_s, ms, ctx, smooth_stats = analyze_sequence(seq, assessment)
    results = validate(assessment, ctx)

    progress(0.88, "Rendering annotated frames")
    captions: dict[int, list[str]] = {}
    for r in results:
        for ev in r["evidence"]:
            captions.setdefault(ev["frame"], []).append(f"{r['label']}: {ev['caption']}")
    for r in results:
        for ev in r["evidence"]:
            i = ev["frame"]
            name = f"frame_{i:05d}.jpg"
            dst = os.path.join(frames_dir, name)
            if not os.path.exists(dst):
                img = cv2.imread(raw_paths[i])
                cv2.imwrite(dst, report.annotate(img, seq_s.frames[i], ms, i, captions[i]), [cv2.IMWRITE_JPEG_QUALITY, 90])
            ev.update(image=f"frames/{name}", t=round(float(ms.t[i]), 3), source=seq_s.frames[i].source,
                      pose_conf=round(float(ms.pose_conf[i]), 3))
    # stills: always show every image with its overlay so the user can judge the pose fit
    gallery = []
    if not is_video:
        for i in range(len(frames)):
            name = f"frame_{i:05d}.jpg"
            dst = os.path.join(frames_dir, name)
            if not os.path.exists(dst):
                cv2.imwrite(dst, report.annotate(cv2.imread(raw_paths[i]), seq_s.frames[i], ms, i, captions.get(i)))
            gallery.append({"frame": i, "image": f"frames/{name}", "source": frames[i].source,
                            "pose_conf": round(float(ms.pose_conf[i]), 3), "detected": bool(frames[i].detected)})

    annotated_video = None
    if is_video and make_video:
        progress(0.92, "Encoding annotated video")
        ann_dir = os.path.join(out_dir, "ann")
        os.makedirs(ann_dir, exist_ok=True)
        ann_paths = []
        for i, p in enumerate(raw_paths):
            q = os.path.join(ann_dir, f"{i:05d}.jpg")
            cv2.imwrite(q, report.annotate(cv2.imread(p), seq_s.frames[i], ms, i), [cv2.IMWRITE_JPEG_QUALITY, 85])
            ann_paths.append(q)
        if report.encode_video(ann_paths, os.path.join(out_dir, "annotated.mp4"), ms.fps):
            annotated_video = "annotated.mp4"
        shutil.rmtree(ann_dir, ignore_errors=True)
    shutil.rmtree(raw_dir, ignore_errors=True)

    detected = np.array([f.detected for f in frames])
    confident = ms.pose_conf >= 0.5
    warnings = []
    if detected.mean() < 0.5:
        warnings.append(f"A skier was found in only {int(detected.sum())} of {len(frames)} frames. Zoom/crop the media so the skier fills more of the frame.")
    elif confident.mean() < 0.6:
        warnings.append(f"Only {int(confident.sum())} of {len(frames)} frames have a confident pose; verdicts rest on those frames alone.")
    if media_info.get("truncated"):
        warnings.append(f"Only the first {max_seconds:.0f} s of the clip were analysed.")
    if is_video and ms.view in ("frontal", "oblique") and not ctx.turns:
        warnings.append("No turns were segmented (lean never clearly left neutral), so turn-based items are inconclusive.")
    if ms.view_source == "user":
        auto = compute_series(seq_s).view
        if auto not in (ms.view, "unknown"):
            warnings.append(f"You set the camera view to '{ms.view}', but the poses look like a '{auto}' view.")

    series = {"t": _clean(ms.t), "pose_conf": _clean(ms.pose_conf), "inclination_smooth": _clean(ctx.incl_smooth)}
    for name in CHART_SERIES:
        v = np.where(ms.valid(name), ms.values[name], np.nan)
        if np.any(np.isfinite(v)):
            series[name] = _clean(v)

    result = {
        "schema_version": 1,
        "assessment": assessment.model_dump(),
        "media": media_info,
        "pose": {
            "estimator": est.name, "frames": len(frames), "frames_detected": int(detected.sum()),
            "frames_confident": int(confident.sum()),
            "mean_confidence": round(float(ms.pose_conf[detected].mean()), 3) if detected.any() else 0.0,
            "has_3d": seq.has_world, "smoothing": smooth_stats,
        },
        "view": {"view": ms.view, "source": ms.view_source, "facing": ms.facing},
        "turns": [t.to_dict() for t in ctx.turns],
        "results": results,
        "summary": summarize(results),
        "series": series,
        "gallery": gallery,
        "annotated_video": annotated_video,
        "warnings": warnings,
        "processing_seconds": round(time.time() - t0, 2),
    }
    result = _clean(result)
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=1)
    progress(1.0, "Done")
    return result
