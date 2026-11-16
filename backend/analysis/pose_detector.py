"""Single-photo pose detection for the legacy /videos/upload endpoint.

Thin adapter over the pipeline's MediaPipe estimator (the old ``mp.solutions``
API this file used was removed from MediaPipe). The model loads on first use.
"""
from typing import Any, Dict, Optional

import cv2
import numpy as np

from pipeline import keypoints as K
from pipeline.keypoints import PoseFrame
from pipeline.pose import get_estimator
from pipeline.report import draw_skeleton


class PoseDetector:
    def __init__(self):
        self._estimator = None

    @property
    def estimator(self):
        if self._estimator is None:
            self._estimator = get_estimator()
        return self._estimator

    def detect_from_file(self, file_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Landmarks in the legacy format (normalised x/y, visibility) or None when no pose is found."""
        image = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return None
        frame = self.estimator.estimate(image, 0, 0.0, track=False)
        if not frame.detected:
            return None
        h, w = image.shape[:2]
        landmarks = []
        for i, name in enumerate(K.NAMES):
            x, y = frame.xy[i]
            ok = bool(np.isfinite(x) and np.isfinite(y))
            landmarks.append({
                "id": i, "name": name.upper(),
                "x": float(x / w) if ok else 0.0, "y": float(y / h) if ok else 0.0,
                "z": float(frame.world[i, 2]) if frame.world is not None else 0.0,
                "visibility": float(frame.vis[i]) if ok else 0.0,
            })
        return {"landmarks": landmarks, "image_width": w, "image_height": h,
                "pose_detected": True, "num_landmarks": len(landmarks)}

    def draw_landmarks(self, image_bytes: bytes, landmarks_data: Dict[str, Any]) -> Optional[bytes]:
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return None
        h, w = image.shape[:2]
        frame = PoseFrame(index=0, t=0.0, width=w, height=h, detected=True)
        for lm in landmarks_data["landmarks"]:
            frame.xy[lm["id"]] = (lm["x"] * w, lm["y"] * h)
            frame.vis[lm["id"]] = lm["visibility"]
        ok, enc = cv2.imencode(".jpg", draw_skeleton(image, frame))
        return enc.tobytes() if ok else None


pose_detector = PoseDetector()
