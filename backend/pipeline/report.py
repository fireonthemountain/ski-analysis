"""Report assets: annotated frames (skeleton overlay + measured lines) and an annotated clip."""
from __future__ import annotations

import os
import subprocess
from typing import Optional

import cv2
import numpy as np

from . import keypoints as K
from .keypoints import PoseFrame
from .metrics import MetricSeries, VIS_OK
from .synthetic import ffmpeg_path

COLORS = {"left": (255, 170, 60), "right": (80, 200, 255), "torso": (240, 240, 240)}   # BGR
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _text(img, text, org, scale, color=(255, 255, 255), thick=1):
    cv2.putText(img, text, org, FONT, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thick, cv2.LINE_AA)


def draw_skeleton(img: np.ndarray, f: PoseFrame, view: str = "frontal") -> np.ndarray:
    """Overlay bones (left = blue, right = orange), joints, and the measured axes."""
    if not f.detected:
        _text(img, "no skier detected", (12, 28), 0.7, (80, 80, 255), 2)
        return img
    h = img.shape[0]
    lw = max(2, int(round(h / 300)))
    ok = lambda j: f.vis[j] >= 0.3 and np.all(np.isfinite(f.xy[j]))
    pt = lambda j: (int(round(f.xy[j, 0])), int(round(f.xy[j, 1])))
    for a, b, group in K.BONES:
        if ok(a) and ok(b):
            solid = f.vis[a] >= VIS_OK and f.vis[b] >= VIS_OK
            cv2.line(img, pt(a), pt(b), COLORS[group] if solid else (150, 150, 150), lw if solid else 1, cv2.LINE_AA)
    for j in K.CORE + K.FEET + [K.L_ELBOW, K.R_ELBOW, K.L_WRIST, K.R_WRIST, K.NOSE]:
        if ok(j):
            cv2.circle(img, pt(j), lw + 2, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(img, pt(j), lw + 1, (90, 255, 120) if f.vis[j] >= VIS_OK else (0, 140, 255), -1, cv2.LINE_AA)
    # measured axes: leg axis (ankle-mid -> hip-mid), torso axis, and the vertical reference
    core_ok = all(ok(j) for j in K.CORE)
    if core_ok and view != "side":
        ank = (f.xy[K.L_ANKLE] + f.xy[K.R_ANKLE]) / 2
        hip = (f.xy[K.L_HIP] + f.xy[K.R_HIP]) / 2
        sh = (f.xy[K.L_SHOULDER] + f.xy[K.R_SHOULDER]) / 2
        P = lambda p: (int(round(p[0])), int(round(p[1])))
        length = float(np.linalg.norm(hip - ank))
        cv2.line(img, P(ank), (int(ank[0]), int(ank[1] - length * 1.9)), (200, 200, 200), 1, cv2.LINE_AA)
        cv2.line(img, P(ank), P(hip), (60, 60, 255), lw, cv2.LINE_AA)
        cv2.line(img, P(hip), P(sh), (60, 255, 255), lw, cv2.LINE_AA)
    return img


def annotate(img: np.ndarray, f: PoseFrame, ms: MetricSeries, i: int, captions: Optional[list[str]] = None) -> np.ndarray:
    out = draw_skeleton(img.copy(), f, ms.view)
    h, w = out.shape[:2]
    s = max(0.45, h / 1100)
    lines = []
    def add(name, label, fmt="{:+.0f}"):
        v = ms.values[name][i]
        if np.isfinite(v) and ms.conf[name][i] >= VIS_OK:
            lines.append(f"{label} {fmt.format(v)}")
    if ms.view != "side":
        add("inclination", "lean"); add("edge_proxy", "shin tilt"); add("angulation", "angulation")
        add("stance_width_2d", "stance", "{:.2f}x")
    if ms.view != "frontal":
        add("fore_aft", "fore-aft")
    add("knee_mean", "knee", "{:.0f}"); add("separation", "separation")
    head = f"t={f.t:.2f}s  pose conf {ms.pose_conf[i]:.2f}" if ms.is_video else f"{f.source}  pose conf {ms.pose_conf[i]:.2f}"
    y = int(26 * s / 0.6)
    _text(out, head, (10, y), s, (255, 255, 255), 1)
    for k, line in enumerate(lines):
        _text(out, line, (10, y + int((k + 1) * 30 * s / 0.6)), s, (120, 255, 255), 1)
    for k, cap in enumerate(captions or []):
        _text(out, cap[:110], (10, h - 12 - int(k * 28 * s / 0.6)), s, (140, 255, 140), 1)
    return out


def encode_video(frame_paths: list[str], out_path: str, fps: float) -> Optional[str]:
    """H.264 mp4 (browser playable) from a list of image files. Needs ffmpeg; returns None without it."""
    ff = ffmpeg_path()
    if not ff or not frame_paths:
        return None
    listing = out_path + ".txt"
    with open(listing, "w") as fh:
        for p in frame_paths:
            fh.write(f"file '{os.path.abspath(p)}'\nduration {1.0 / fps:.6f}\n")
    cmd = [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
           "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-r", f"{fps:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-crf", "23", "-movflags", "+faststart", out_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except Exception:
        return None
    finally:
        if os.path.exists(listing):
            os.remove(listing)
    return out_path if os.path.exists(out_path) else None
