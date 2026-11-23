"""Pose estimators.

``MediaPipePoseEstimator`` is the real one (BlazePose via the MediaPipe Tasks
PoseLandmarker; runs on the Apple-silicon CPU, no PyTorch). It also does the
single-skier tracking: the crop for each frame follows the previous
detection, which keeps a small, distant skier large in the model's input.

``MarkerPoseEstimator`` reads the colour-coded joints of the synthetic stick
figure straight from pixels; it exists so the end-to-end test exercises real
decode -> pose-from-pixels -> metrics without footage of real people.

``ScriptedPoseEstimator`` replays known keypoints (tests).
"""
from __future__ import annotations

import os
import urllib.request
from typing import Optional, Protocol

import cv2
import numpy as np

from . import keypoints as K
from .keypoints import PoseFrame
from .identity import torso_signature

MODEL_DIR = os.environ.get("POSE_MODEL_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{v}/float16/latest/pose_landmarker_{v}.task"


class PoseEstimator(Protocol):
    name: str

    def reset(self) -> None: ...
    def estimate(self, image_bgr: np.ndarray, index: int, t: float, source: str = "", track: bool = True) -> PoseFrame: ...
    def close(self) -> None: ...


def model_path(variant: str) -> str:
    """Path to the .task model; downloaded once from Google's model host if missing."""
    path = os.path.join(MODEL_DIR, f"pose_landmarker_{variant}.task")
    if not os.path.exists(path):
        os.makedirs(MODEL_DIR, exist_ok=True)
        print(f"Downloading MediaPipe pose model ({variant}) ...")
        urllib.request.urlretrieve(MODEL_URL.format(v=variant), path + ".part")
        os.replace(path + ".part", path)
    return path


class MediaPipePoseEstimator:
    def __init__(self, variant: Optional[str] = None, min_detection_confidence: float = 0.4, num_poses: int = 3):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self.variant = variant or os.environ.get("POSE_MODEL", "heavy")
        self.name = f"mediapipe-pose-landmarker-{self.variant}"
        self._mp = mp
        opts = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path(self.variant)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=num_poses,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_detection_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(opts)
        self._box: Optional[tuple[float, float, float, float]] = None   # last skier box x0,y0,x1,y1 (px)
        self._lost = 0

    def reset(self) -> None:
        self._box, self._lost = None, 0

    def close(self) -> None:
        self._landmarker.close()

    # -- one detection pass on a crop; returns candidates in full-image pixels
    def _detect(self, image_bgr: np.ndarray, crop: Optional[tuple[int, int, int, int]]):
        x0, y0, x1, y1 = crop if crop else (0, 0, image_bgr.shape[1], image_bgr.shape[0])
        sub = image_bgr[y0:y1, x0:x1]
        if sub.size == 0:
            return []
        h, w = sub.shape[:2]
        if max(h, w) < 384:                       # upscale small crops so a distant skier fills the input
            s = 384.0 / max(h, w)
            sub = cv2.resize(sub, (int(w * s), int(h * s)), interpolation=cv2.INTER_CUBIC)
        rgb = np.ascontiguousarray(cv2.cvtColor(sub, cv2.COLOR_BGR2RGB))
        res = self._landmarker.detect(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb))
        out = []
        for i, lms in enumerate(res.pose_landmarks or []):
            xy = np.array([[lm.x * w + x0, lm.y * h + y0] for lm in lms], float)
            vis = np.array([min(getattr(lm, "visibility", 1.0) or 0.0, getattr(lm, "presence", 1.0) or 0.0) for lm in lms], float)
            world = None
            if res.pose_world_landmarks and i < len(res.pose_world_landmarks):
                world = np.array([[lm.x, lm.y, lm.z] for lm in res.pose_world_landmarks[i]], float)
            out.append((xy, vis, world))
        return out

    @staticmethod
    def _bbox(xy: np.ndarray, vis: np.ndarray):
        pts = xy[vis > 0.3] if np.any(vis > 0.3) else xy
        return float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())

    def estimate(self, image_bgr: np.ndarray, index: int, t: float, source: str = "", track: bool = True) -> PoseFrame:
        H, W = image_bgr.shape[:2]
        frame = PoseFrame(index=index, t=t, width=W, height=H, source=source)
        cands = []
        if track and self._box is not None:
            bx0, by0, bx1, by1 = self._box
            bw, bh = bx1 - bx0, by1 - by0
            side = max(bw, bh) * (1.8 + 0.4 * self._lost)
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            crop = (int(max(0, cx - side / 2)), int(max(0, cy - side / 2)), int(min(W, cx + side / 2)), int(min(H, cy + side / 2)))
            cands = self._detect(image_bgr, crop)
        if not cands:
            cands = self._detect(image_bgr, None)
        if not cands and (not track or self._box is None):
            # distant skier: search overlapping tiles at 2x zoom
            th, tw = H // 2, W // 2
            for ty in (0, H // 4, H - th):
                for tx in (0, W // 4, W - tw):
                    cands += self._detect(image_bgr, (tx, ty, tx + tw, ty + th))
        if not cands:
            self._lost += 1
            if self._lost > 8:
                self._box = None
            return frame

        def score(c):
            xy, vis, _ = c
            x0, y0, x1, y1 = self._bbox(xy, vis)
            if track and self._box is not None:    # stay on the same skier: nearest to the last box
                pcx, pcy = (self._box[0] + self._box[2]) / 2, (self._box[1] + self._box[3]) / 2
                return -np.hypot((x0 + x1) / 2 - pcx, (y0 + y1) / 2 - pcy)
            return float(np.mean(vis[K.CORE])) * np.sqrt(max(1.0, (x1 - x0) * (y1 - y0)))   # biggest, clearest person

        xy, vis, world = max(cands, key=score)
        frame.detected, frame.xy, frame.vis, frame.world = True, xy, vis, world
        if track:
            frame.appearance = torso_signature(image_bgr, xy, vis)
        if track:
            self._box, self._lost = self._bbox(xy, vis), 0
        return frame


class MarkerPoseEstimator:
    """Recovers the synthetic figure's colour-coded joints from pixels (2D only)."""

    name = "synthetic-marker"

    def __init__(self):
        from .synthetic import marker_colors
        self._hues = {}
        for j, bgr in marker_colors().items():
            hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0, 0]
            self._hues[j] = int(hsv[0])
        self._tol = max(2, int(180 / len(self._hues) / 2) - 1)

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass

    def estimate(self, image_bgr: np.ndarray, index: int, t: float, source: str = "", track: bool = True) -> PoseFrame:
        from .synthetic import MARKER_RADIUS
        H, W = image_bgr.shape[:2]
        frame = PoseFrame(index=index, t=t, width=W, height=H, source=source)
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        sat = (hsv[..., 1] > 150) & (hsv[..., 2] > 120)
        full_area = np.pi * MARKER_RADIUS ** 2
        found = 0
        for j, hue in self._hues.items():
            d = np.abs(hsv[..., 0].astype(int) - hue)
            d = np.minimum(d, 180 - d)
            ys, xs = np.nonzero(sat & (d <= self._tol))
            if len(xs) < 0.15 * full_area:
                continue
            frame.xy[j] = (xs.mean(), ys.mean())
            # a marker partly hidden behind another gives a biased centroid -> lower confidence
            frame.vis[j] = float(np.clip(len(xs) / (0.85 * full_area), 0.0, 1.0)) * 0.98
            found += 1
        frame.detected = found >= 8
        return frame


class ScriptedPoseEstimator:
    """Returns pre-computed PoseFrames in order, ignoring the pixels."""

    name = "scripted"

    def __init__(self, frames: list[PoseFrame]):
        self._frames = frames

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass

    def estimate(self, image_bgr: np.ndarray, index: int, t: float, source: str = "", track: bool = True) -> PoseFrame:
        f = self._frames[index]
        f.index, f.t, f.source = index, t, source
        f.height, f.width = image_bgr.shape[:2]
        return f


def get_estimator(name: Optional[str] = None) -> PoseEstimator:
    name = name or os.environ.get("POSE_ESTIMATOR", "mediapipe")
    if name == "marker":
        return MarkerPoseEstimator()
    if name.startswith("mediapipe"):
        return MediaPipePoseEstimator()
    raise ValueError(f"unknown pose estimator '{name}'")
