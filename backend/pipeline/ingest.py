"""Media ingest: video frame sampling and still-image loading (OpenCV + ffmpeg)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Iterator, Optional

import cv2
import numpy as np

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif"}


def kind_of(filename: str) -> Optional[str]:
    ext = os.path.splitext(filename)[1].lower()
    return "video" if ext in VIDEO_EXT else "image" if ext in IMAGE_EXT else None


@dataclass
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int
    duration: float


def probe_video(path: str) -> VideoInfo:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {os.path.basename(path)}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if fps <= 0 or fps > 1000:
        fps = 30.0
    return VideoInfo(fps=fps, frame_count=n, width=w, height=h, duration=n / fps if n else 0.0)


def _fit(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    s = max_side / max(h, w)
    if s < 1.0:
        img = cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA)
    return img


def sampling_plan(info: VideoInfo, target_fps: float, max_seconds: float) -> tuple[int, float]:
    """(step, effective_fps): take every ``step``-th source frame."""
    step = max(1, int(round(info.fps / target_fps))) if target_fps > 0 else 1
    return step, info.fps / step


def iter_video_frames(path: str, target_fps: float = 15.0, max_seconds: float = 90.0,
                      max_side: int = 1280, start_s: float = 0.0) -> Iterator[tuple[int, float, np.ndarray]]:
    """Yield (source_frame_number, t_seconds_from_start, BGR image) at ~target_fps.

    OpenCV applies the rotation metadata phones write, so portrait clips come out upright.
    """
    info = probe_video(path)
    step, _ = sampling_plan(info, target_fps, max_seconds)
    cap = cv2.VideoCapture(path)
    first = int(round(start_s * info.fps))
    if first > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    i = first
    try:
        while True:
            ok = cap.grab()
            if not ok:
                break
            t = (i - first) / info.fps
            if t > max_seconds:
                break
            if (i - first) % step == 0:
                ok, img = cap.retrieve()
                if ok and img is not None:
                    yield i, t, _fit(img, max_side)
            i += 1
    finally:
        cap.release()


def load_image(path: str, max_side: int = 1600) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None and shutil.which("sips"):          # HEIC from an iPhone: convert with macOS sips
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "converted.jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", path, "--out", out], capture_output=True)
            img = cv2.imread(out, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image: {os.path.basename(path)}")
    return _fit(img, max_side)
