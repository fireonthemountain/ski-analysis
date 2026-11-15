"""Biomechanical metrics from pose keypoints.

Every function here is pure numpy on keypoints, so it is unit-tested with
synthetic skeletons of known geometry (tests/test_metrics.py).

Per-frame series produced by :func:`compute_series` (NaN where a metric cannot
be measured in that frame; a parallel confidence series holds the visibility
of the landmarks it used):

Frontal plane (2D image, needs a front/back view)
  inclination       leg-axis (ankle-mid -> hip-mid) angle from image vertical, + = image right
  lean_skier        inclination in the skier's frame, + = leaning to the skier's right
  torso_tilt        hip-mid -> shoulder-mid angle from vertical, + = image right
  angulation        legs inclined more than torso, + = torso stays more upright (toward the outside)
  edge_proxy        outside-leg shin lateral tilt, + = tipped into the turn (edge-angle proxy)
  stance_width      ankle spacing perpendicular to the leg axis / hip width
Sagittal plane (2D image, needs a side view)
  fore_aft          ankle -> centre-of-mass angle vs the slope normal, + = forward
View independent (3D world landmarks when available, else 2D projection)
  knee_left/right/mean   included hip-knee-ankle angle (180 = straight)
  hip_angle         included shoulder-hip-knee angle (180 = upright)
  separation        upper-body yaw minus feet (ski) yaw, + = upper body turned to skier's right
  separation_pelvis shoulders yaw minus pelvis yaw (spinal twist)
  counter           separation signed by turn direction, + = countered (facing outside of turn)
Helpers
  view_ratio        2D shoulder (and scaled hip) width / torso length (frontal ~0.75, side ~0.1)
  facing            +1 back view (skier's right is image right), -1 front view
  wrist_drop_left/right  wrist below shoulder, in torso lengths (pole-plant proxy)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import keypoints as K
from .keypoints import PoseFrame, PoseSequence

VIS_OK = 0.5          # a landmark below this is not trusted
MIN_LEAN_FOR_TURN_SIGN = 8.0   # deg of inclination before a frame has a turn direction

HIP_TO_SHOULDER = 1.58          # typical shoulder width / hip-joint width
VIEW_FRONTAL_MIN = 0.62         # view_ratio at or above this = front/back view (within ~35 deg)
VIEW_SIDE_MAX = 0.27            # at or below = side view (within ~20 deg of side-on)

# Rough segment-mass weights for a whole-body centre-of-mass proxy
COM_WEIGHTS = {"hip": 0.45, "shoulder": 0.374, "knee": 0.112, "ankle": 0.064}


# ---------------------------------------------------------------- primitives
def angle_between(u, v) -> float:
    """Unsigned angle in degrees between two vectors (any dimension)."""
    u, v = np.asarray(u, float), np.asarray(v, float)
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu == 0 or nv == 0 or not np.isfinite(nu * nv):
        return float("nan")
    return math.degrees(math.acos(float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))))


def joint_angle(a, b, c) -> float:
    """Included angle at ``b`` formed by a-b-c, degrees (180 = straight)."""
    return angle_between(np.asarray(a, float) - np.asarray(b, float), np.asarray(c, float) - np.asarray(b, float))


def tilt_from_vertical(v) -> float:
    """Signed angle of a 2D image vector from image 'up'. + = leaning image-right."""
    v = np.asarray(v, float)
    if not np.all(np.isfinite(v)) or np.linalg.norm(v) == 0:
        return float("nan")
    return math.degrees(math.atan2(v[0], -v[1]))


def wrap_deg(a: float) -> float:
    """Wrap an angle to (-180, 180]."""
    if not np.isfinite(a):
        return float("nan")
    return (a + 180.0) % 360.0 - 180.0


def axis_yaw(right_vec) -> float:
    """Heading (deg) of a body 'right' axis given in camera coords (x right, y down, z away).

    0 = facing away from the camera, 90 = facing image right, 180 = facing the camera.
    Increasing = turning to the skier's own right, whatever the camera view.
    """
    return math.degrees(math.atan2(-right_vec[2], right_vec[0]))


def forward_yaw(fwd_vec) -> float:
    """Heading (deg) of a 'forward' vector (e.g. heel -> toe), same convention as axis_yaw."""
    return math.degrees(math.atan2(fwd_vec[0], fwd_vec[2]))


def _pair(arr: np.ndarray, vis: np.ndarray, a: int, b: int):
    """Midpoint of a left/right pair. Uses both sides when both are visible,
    otherwise the visible one (typical in side views). Returns (point, conf)."""
    va, vb = vis[a], vis[b]
    if va >= VIS_OK and vb >= VIS_OK:
        return (arr[a] + arr[b]) / 2, float((va + vb) / 2)
    if va >= VIS_OK:
        return arr[a].copy(), float(va) * 0.9
    if vb >= VIS_OK:
        return arr[b].copy(), float(vb) * 0.9
    return np.full(arr.shape[1], np.nan), float(max(va, vb))


def _minvis(vis: np.ndarray, idx) -> float:
    return float(np.min(vis[list(idx)]))


# ----------------------------------------------------------- per-frame maths
def frame_metrics(f: PoseFrame) -> dict[str, tuple[float, float]]:
    """All per-frame metrics as name -> (value, confidence). Missing -> (nan, conf)."""
    out: dict[str, tuple[float, float]] = {}
    nan = float("nan")
    if not f.detected:
        return out
    xy, vis, W = f.xy, f.vis, f.world

    sh_mid, c_sh = _pair(xy, vis, K.L_SHOULDER, K.R_SHOULDER)
    hip_mid, c_hip = _pair(xy, vis, K.L_HIP, K.R_HIP)
    knee_mid, c_knee = _pair(xy, vis, K.L_KNEE, K.R_KNEE)
    ank_mid, c_ank = _pair(xy, vis, K.L_ANKLE, K.R_ANKLE)
    torso_len = float(np.linalg.norm(sh_mid - hip_mid))
    both_sh = _minvis(vis, (K.L_SHOULDER, K.R_SHOULDER))
    both_hip = _minvis(vis, (K.L_HIP, K.R_HIP))
    both_ank = _minvis(vis, (K.L_ANKLE, K.R_ANKLE))

    # --- view helpers
    if both_sh >= VIS_OK and np.isfinite(torso_len) and torso_len > 0:
        # widths are taken ACROSS the torso axis, so leaning toward/away from a side-on camera
        # (which stacks the shoulders vertically) does not look like a wide, frontal body
        t_axis = (sh_mid - hip_mid) / torso_len
        across = lambda v: abs(float(v[0] * -t_axis[1] + v[1] * t_axis[0]))
        ratio = across(xy[K.R_SHOULDER] - xy[K.L_SHOULDER]) / torso_len
        if both_hip >= VIS_OK:
            # hips are ~0.63x as wide as shoulders; scale so both read alike, and take the smaller:
            # a side-on skier with rotated shoulders still has a narrow pelvis in the image
            ratio = min(ratio, across(xy[K.R_HIP] - xy[K.L_HIP]) / torso_len * HIP_TO_SHOULDER)
        out["view_ratio"] = (ratio, min(both_sh, c_hip))
    if both_sh >= VIS_OK and both_hip >= VIS_OK:
        d = (xy[K.R_SHOULDER, 0] - xy[K.L_SHOULDER, 0]) + (xy[K.R_HIP, 0] - xy[K.L_HIP, 0])
        out["facing"] = (1.0 if d >= 0 else -1.0, min(both_sh, both_hip))

    # --- frontal plane
    incl = nan
    c_leg = min(c_hip, c_ank)
    if c_leg >= VIS_OK:
        incl = tilt_from_vertical(hip_mid - ank_mid)
        out["inclination"] = (incl, c_leg)
        if "facing" in out:
            out["lean_skier"] = (incl * out["facing"][0], min(c_leg, out["facing"][1]))
    c_torso = min(c_sh, c_hip)
    if c_torso >= VIS_OK:
        torso_tilt = tilt_from_vertical(sh_mid - hip_mid)
        out["torso_tilt"] = (torso_tilt, c_torso)
        if np.isfinite(incl):
            sgn = 1.0 if incl >= 0 else -1.0
            out["angulation"] = ((incl - torso_tilt) * sgn, min(c_torso, c_leg))

    if both_ank >= VIS_OK and _minvis(vis, (K.L_KNEE, K.R_KNEE)) >= VIS_OK and np.isfinite(incl):
        # outside leg = the one whose ankle is on the far side from the lean (robust to L/R label swaps)
        left_is_image_left = xy[K.L_ANKLE, 0] <= xy[K.R_ANKLE, 0]
        lean_right = incl >= 0
        outside_left = left_is_image_left if lean_right else not left_is_image_left
        knee, ankle = (K.L_KNEE, K.L_ANKLE) if outside_left else (K.R_KNEE, K.R_ANKLE)
        shin = tilt_from_vertical(xy[knee] - xy[ankle])
        out["edge_proxy"] = (shin * (1.0 if lean_right else -1.0), min(vis[knee], vis[ankle], c_leg))

    if both_ank >= VIS_OK and both_hip >= VIS_OK and np.isfinite(incl):
        axis = hip_mid - ank_mid
        n = np.linalg.norm(axis)
        hip_w = float(np.linalg.norm(xy[K.R_HIP] - xy[K.L_HIP]))
        if n > 0 and hip_w > 0:
            perp = np.array([-axis[1], axis[0]]) / n
            width = abs(float(np.dot(xy[K.R_ANKLE] - xy[K.L_ANKLE], perp)))
            out["stance_width_2d"] = (width / hip_w, min(both_ank, both_hip))

    # --- sagittal plane: fore/aft
    if min(c_hip, c_ank, c_sh, c_knee) >= VIS_OK:
        com = (COM_WEIGHTS["hip"] * hip_mid + COM_WEIGHTS["shoulder"] * sh_mid
               + COM_WEIGHTS["knee"] * knee_mid + COM_WEIGHTS["ankle"] * ank_mid)
        c = com - ank_mid
        feet = []
        for heel, toe in ((K.L_HEEL, K.L_TOE), (K.R_HEEL, K.R_TOE)):
            if min(vis[heel], vis[toe]) >= VIS_OK:
                feet.append(xy[toe] - xy[heel])
        conf = min(c_hip, c_ank, c_sh, c_knee)
        if feet:
            fvec = np.mean(feet, axis=0)
            if np.linalg.norm(fvec) > 0:
                u_f = fvec / np.linalg.norm(fvec)
                normal = np.array([u_f[1], -u_f[0]])
                if normal[1] > 0:
                    normal = -normal
                out["fore_aft"] = (math.degrees(math.atan2(float(np.dot(c, u_f)), float(np.dot(c, normal)))), conf)
                out["fore_aft_ref"] = (1.0, conf)       # 1 = boot-sole line used as slope reference
        if "fore_aft" not in out and vis[K.NOSE] >= VIS_OK:
            direction = 1.0 if xy[K.NOSE, 0] >= sh_mid[0] else -1.0
            out["fore_aft"] = (tilt_from_vertical(c) * direction, conf)
            out["fore_aft_ref"] = (0.0, conf)           # 0 = image vertical (assumes level camera, gentle slope)

    # --- joint angles (3D when available)
    P = W if W is not None else xy
    knees = []
    for name, hip, knee, ankle in (("knee_left", K.L_HIP, K.L_KNEE, K.L_ANKLE), ("knee_right", K.R_HIP, K.R_KNEE, K.R_ANKLE)):
        conf = _minvis(vis, (hip, knee, ankle))
        if conf >= VIS_OK:
            a = joint_angle(P[hip], P[knee], P[ankle])
            out[name] = (a, conf)
            knees.append((a, conf))
    if knees:
        out["knee_mean"] = (float(np.mean([k[0] for k in knees])), float(np.mean([k[1] for k in knees])))
    # hip angle: torso axis (hip-mid -> shoulder-mid) vs each thigh, so that shoulders being
    # wider than hips does not read as flexion
    hips = []
    if both_sh >= VIS_OK and both_hip >= VIS_OK or (W is None and c_torso >= VIS_OK):
        if both_sh >= VIS_OK and both_hip >= VIS_OK:
            torso_axis = (P[K.L_SHOULDER] + P[K.R_SHOULDER]) / 2 - (P[K.L_HIP] + P[K.R_HIP]) / 2
        else:                                   # side view with the far side hidden: 2D midpoints
            torso_axis = sh_mid - hip_mid
        for hip, knee in ((K.L_HIP, K.L_KNEE), (K.R_HIP, K.R_KNEE)):
            conf = min(_minvis(vis, (hip, knee)), c_torso)
            if conf >= VIS_OK:
                hips.append((angle_between(torso_axis, P[knee] - P[hip]), conf))
    if hips:
        out["hip_angle"] = (float(np.mean([h[0] for h in hips])), float(np.mean([h[1] for h in hips])))
    out["angles_3d"] = (1.0 if W is not None else 0.0, 1.0)

    # --- 3D only: rotation / separation, stance width
    if W is not None:
        if both_sh >= VIS_OK and both_hip >= VIS_OK:
            psi_sh = axis_yaw(W[K.R_SHOULDER] - W[K.L_SHOULDER])
            psi_hip = axis_yaw(W[K.R_HIP] - W[K.L_HIP])
            out["separation_pelvis"] = (wrap_deg(psi_sh - psi_hip), min(both_sh, both_hip))
            feet = []
            for heel, toe in ((K.L_HEEL, K.L_TOE), (K.R_HEEL, K.R_TOE)):
                if min(vis[heel], vis[toe]) >= VIS_OK:
                    feet.append(W[toe] - W[heel])
            if len(feet) == 2:
                fv = feet[0] / np.linalg.norm(feet[0]) + feet[1] / np.linalg.norm(feet[1])
                sep = wrap_deg(psi_sh - forward_yaw(fv))
                out["separation"] = (sep, min(both_sh, _minvis(vis, K.FEET)))
                out["separation_ref"] = (1.0, 1.0)      # 1 = vs feet/skis
            else:
                out["separation"] = out["separation_pelvis"]
                out["separation_ref"] = (0.0, 1.0)      # 0 = vs pelvis only
            if "lean_skier" in out and abs(out["lean_skier"][0]) >= MIN_LEAN_FOR_TURN_SIGN:
                turn = 1.0 if out["lean_skier"][0] > 0 else -1.0     # +1 = right turn
                out["counter"] = (-out["separation"][0] * turn, min(out["separation"][1], out["lean_skier"][1]))
        if both_ank >= VIS_OK and both_hip >= VIS_OK:
            hip_c, ank_c = (W[K.L_HIP] + W[K.R_HIP]) / 2, (W[K.L_ANKLE] + W[K.R_ANKLE]) / 2
            axis = hip_c - ank_c
            pel = W[K.R_HIP] - W[K.L_HIP]
            if np.linalg.norm(axis) > 0 and np.linalg.norm(pel) > 0:
                axis = axis / np.linalg.norm(axis)
                lat = pel - np.dot(pel, axis) * axis
                if np.linalg.norm(lat) > 0:
                    lat = lat / np.linalg.norm(lat)
                    width = abs(float(np.dot(W[K.R_ANKLE] - W[K.L_ANKLE], lat)))
                    out["stance_width_3d"] = (width / float(np.linalg.norm(pel)), min(both_ank, both_hip))

    # --- pole-plant proxy
    if np.isfinite(torso_len) and torso_len > 0:
        for name, sh, wr in (("wrist_drop_left", K.L_SHOULDER, K.L_WRIST), ("wrist_drop_right", K.R_SHOULDER, K.R_WRIST)):
            conf = _minvis(vis, (sh, wr))
            if conf >= VIS_OK:
                out[name] = ((xy[wr, 1] - xy[sh, 1]) / torso_len, conf)
    return out


SERIES_NAMES = [
    "view_ratio", "facing", "inclination", "lean_skier", "torso_tilt", "angulation", "edge_proxy",
    "stance_width_2d", "stance_width_3d", "fore_aft", "fore_aft_ref", "knee_left", "knee_right",
    "knee_mean", "hip_angle", "angles_3d", "separation", "separation_pelvis", "separation_ref",
    "counter", "wrist_drop_left", "wrist_drop_right",
]


@dataclass
class MetricSeries:
    t: np.ndarray                               # seconds, one per sampled frame
    values: dict[str, np.ndarray] = field(default_factory=dict)
    conf: dict[str, np.ndarray] = field(default_factory=dict)
    pose_conf: np.ndarray = None                # type: ignore[assignment]  core-joint confidence per frame
    fps: float = 0.0
    is_video: bool = False
    view: str = "unknown"                       # frontal | side | oblique | unknown
    view_source: str = "auto"
    facing: Optional[str] = None                # 'toward camera' | 'away from camera'

    def valid(self, name: str, min_conf: float = VIS_OK) -> np.ndarray:
        """Boolean mask of frames where ``name`` is finite and confidently measured."""
        return np.isfinite(self.values[name]) & (self.conf[name] >= min_conf)

    def __len__(self) -> int:
        return len(self.t)


def classify_view(view_ratio: np.ndarray) -> str:
    r = view_ratio[np.isfinite(view_ratio)]
    if len(r) == 0:
        return "unknown"
    m = float(np.median(r))
    if m >= VIEW_FRONTAL_MIN:
        return "frontal"
    if m <= VIEW_SIDE_MAX:
        return "side"
    return "oblique"


def compute_series(seq: PoseSequence, view: Optional[str] = None) -> MetricSeries:
    n = len(seq.frames)
    ms = MetricSeries(t=np.array([f.t for f in seq.frames], float), fps=seq.fps, is_video=seq.is_video)
    for name in SERIES_NAMES:
        ms.values[name] = np.full(n, np.nan)
        ms.conf[name] = np.zeros(n)
    ms.pose_conf = np.array([f.core_confidence() for f in seq.frames], float)
    for i, f in enumerate(seq.frames):
        for name, (v, c) in frame_metrics(f).items():
            ms.values[name][i] = v
            ms.conf[name][i] = c
    auto = classify_view(ms.values["view_ratio"])
    if view in ("frontal", "side", "oblique"):
        ms.view, ms.view_source = view, "user"
    else:
        ms.view, ms.view_source = auto, "auto"
    fac = ms.values["facing"][np.isfinite(ms.values["facing"])]
    if len(fac) and ms.view != "side":
        ms.facing = "away from camera" if np.median(fac) > 0 else "toward camera"
    return ms
