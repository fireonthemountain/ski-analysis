"""Keypoint layout and the per-frame pose container shared by every stage.

Layout is MediaPipe BlazePose (33 landmarks). Conventions:

* ``xy``    - image pixels, x right, y DOWN, shape (33, 2)
* ``world`` - metres, origin at mid-hip, camera-aligned axes: x right,
              y down, z away from the camera, shape (33, 3). Optional
              (None when the estimator only sees 2D).
* ``vis``   - per-landmark confidence 0..1, shape (33,)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner",
    "right_eye", "right_eye_outer", "left_ear", "right_ear", "mouth_left",
    "mouth_right", "left_shoulder", "right_shoulder", "left_elbow",
    "right_elbow", "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
    "left_heel", "right_heel", "left_foot_index", "right_foot_index",
]
IDX = {n: i for i, n in enumerate(NAMES)}
N_KP = len(NAMES)

NOSE = IDX["nose"]
L_SHOULDER, R_SHOULDER = IDX["left_shoulder"], IDX["right_shoulder"]
L_ELBOW, R_ELBOW = IDX["left_elbow"], IDX["right_elbow"]
L_WRIST, R_WRIST = IDX["left_wrist"], IDX["right_wrist"]
L_HIP, R_HIP = IDX["left_hip"], IDX["right_hip"]
L_KNEE, R_KNEE = IDX["left_knee"], IDX["right_knee"]
L_ANKLE, R_ANKLE = IDX["left_ankle"], IDX["right_ankle"]
L_HEEL, R_HEEL = IDX["left_heel"], IDX["right_heel"]
L_TOE, R_TOE = IDX["left_foot_index"], IDX["right_foot_index"]

# Landmarks every body metric depends on; their visibility drives pose quality.
CORE = [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE]
FEET = [L_HEEL, R_HEEL, L_TOE, R_TOE]

# Bones drawn in overlays: (a, b, group)
BONES = [
    (L_SHOULDER, R_SHOULDER, "torso"), (L_HIP, R_HIP, "torso"),
    (L_SHOULDER, L_HIP, "torso"), (R_SHOULDER, R_HIP, "torso"),
    (L_SHOULDER, L_ELBOW, "left"), (L_ELBOW, L_WRIST, "left"),
    (R_SHOULDER, R_ELBOW, "right"), (R_ELBOW, R_WRIST, "right"),
    (L_HIP, L_KNEE, "left"), (L_KNEE, L_ANKLE, "left"),
    (R_HIP, R_KNEE, "right"), (R_KNEE, R_ANKLE, "right"),
    (L_ANKLE, L_HEEL, "left"), (L_HEEL, L_TOE, "left"), (L_ANKLE, L_TOE, "left"),
    (R_ANKLE, R_HEEL, "right"), (R_HEEL, R_TOE, "right"), (R_ANKLE, R_TOE, "right"),
]


@dataclass
class PoseFrame:
    """Pose for one sampled frame. ``detected`` False means no skier was found."""

    index: int                 # index into the sampled frame list
    t: float                   # seconds from the start of the clip (0 for stills)
    width: int
    height: int
    detected: bool = False
    xy: np.ndarray = field(default_factory=lambda: np.full((N_KP, 2), np.nan))
    vis: np.ndarray = field(default_factory=lambda: np.zeros(N_KP))
    world: Optional[np.ndarray] = None
    source: str = ""           # file name (stills) or source frame number (video)
    appearance: Optional[np.ndarray] = None   # torso colour signature (identity.torso_signature), video only

    def core_confidence(self) -> float:
        """Mean visibility of the 8 core joints (0 when nothing was detected)."""
        if not self.detected:
            return 0.0
        return float(np.mean(self.vis[CORE]))


@dataclass
class PoseSequence:
    frames: list[PoseFrame]
    fps: float                 # sampling rate of ``frames`` (0 for unordered stills)
    is_video: bool
    estimator: str = ""

    def __len__(self) -> int:
        return len(self.frames)

    @property
    def has_world(self) -> bool:
        return any(f.world is not None for f in self.frames)
