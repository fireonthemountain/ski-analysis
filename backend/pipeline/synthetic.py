"""Synthetic skier: a parametric 3D stick figure with known joint angles.

Used for (a) unit tests - known angles in, known metrics out, (b) the
generated sample clip / stills for the end-to-end test and the demo, so no
footage of real people is needed.

Skier frame: r = skier's right, u = up, f = forward (direction of travel).
Camera frame (same as MediaPipe world landmarks): x right, y down, z away.
``heading_deg``: 0 = skier moving away from camera (back view),
180 = toward camera (front view), 90 = moving image-right (side view).
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, replace
from typing import Iterable, Optional

import cv2
import numpy as np

from . import keypoints as K
from .keypoints import PoseFrame, PoseSequence


@dataclass
class SkierParams:
    heading_deg: float = 0.0        # camera view, see module docstring
    inclination_deg: float = 0.0    # leg-axis lateral lean, + = to skier's right
    angulation_deg: float = 0.0     # torso more upright than legs by this much
    knee_angle_deg: float = 140.0   # included hip-knee-ankle angle (180 = straight)
    fore_aft_deg: float = 4.0       # leg-axis forward lean vs slope normal
    torso_forward_deg: float = 25.0 # torso forward lean vs slope normal
    stance_ratio: float = 1.0       # ankle spacing / hip width
    shoulder_yaw_deg: float = 0.0   # + = turned to skier's right (vs direction of travel)
    pelvis_yaw_deg: float = 0.0
    feet_yaw_deg: float = 0.0
    left_wrist_drop: float = 0.0    # metres the wrist is lowered (pole plant)
    right_wrist_drop: float = 0.0
    slope_roll_deg: float = 0.0     # rotates the whole image (camera roll / slope)
    hip_width: float = 0.24
    shoulder_width: float = 0.38
    torso_len: float = 0.50


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def _yaw_axes(yaw_deg: float):
    """(right, forward) unit vectors in the skier frame after a yaw to the right."""
    a = math.radians(yaw_deg)
    return np.array([math.cos(a), 0.0, -math.sin(a)]), np.array([math.sin(a), 0.0, math.cos(a)])


def skeleton_skier_frame(p: SkierParams) -> np.ndarray:
    """33x3 joints in the skier frame (r, u, f), metres."""
    J = np.zeros((K.N_KP, 3))
    th, ph = math.radians(p.inclination_deg), math.radians(p.fore_aft_deg)
    e_leg = np.array([math.sin(th) * math.cos(ph), math.cos(th) * math.cos(ph), math.sin(ph)])
    sgn = 0.0 if p.inclination_deg == 0 else math.copysign(1.0, p.inclination_deg)
    tt = math.radians(p.inclination_deg - sgn * p.angulation_deg)
    ta = math.radians(p.torso_forward_deg)
    e_torso = np.array([math.sin(tt) * math.cos(ta), math.cos(tt) * math.cos(ta), math.sin(ta)])

    fwd = np.array([0.0, 0.0, 1.0])
    lat = _unit(np.cross(e_leg, fwd) * -1.0)          # lateral axis, perpendicular to the leg axis
    if lat[0] < 0:
        lat = -lat
    fwd_perp = _unit(fwd - np.dot(fwd, e_leg) * e_leg)  # "knee forward" direction

    leg_len = 0.90 * math.sin(math.radians(p.knee_angle_deg) / 2) if p.knee_angle_deg < 180 else 0.90
    ankle_mid = np.array([0.0, 0.10, 0.0])
    pelvis = ankle_mid + leg_len * e_leg

    r_p, _ = _yaw_axes(p.pelvis_yaw_deg)
    r_p = _unit(r_p - np.dot(r_p, e_leg) * e_leg)
    J[K.L_HIP] = pelvis - r_p * p.hip_width / 2
    J[K.R_HIP] = pelvis + r_p * p.hip_width / 2
    half = p.stance_ratio * p.hip_width / 2
    J[K.L_ANKLE] = ankle_mid - lat * half
    J[K.R_ANKLE] = ankle_mid + lat * half

    for hip, knee, ankle in ((K.L_HIP, K.L_KNEE, K.L_ANKLE), (K.R_HIP, K.R_KNEE, K.R_ANKLE)):
        d = np.linalg.norm(J[hip] - J[ankle])
        half_angle = math.radians(p.knee_angle_deg) / 2
        seg = d / (2 * math.sin(half_angle))            # equal shank/thigh -> exact knee angle
        J[knee] = (J[hip] + J[ankle]) / 2 + fwd_perp * seg * math.cos(half_angle)

    r_f, f_f = _yaw_axes(p.feet_yaw_deg)
    for ankle, heel, toe in ((K.L_ANKLE, K.L_HEEL, K.L_TOE), (K.R_ANKLE, K.R_HEEL, K.R_TOE)):
        J[heel] = J[ankle] + np.array([0, -0.07, 0]) - f_f * 0.06
        J[toe] = J[ankle] + np.array([0, -0.07, 0]) + f_f * 0.20

    r_s, f_s = _yaw_axes(p.shoulder_yaw_deg)
    sh_mid = pelvis + p.torso_len * e_torso
    J[K.L_SHOULDER] = sh_mid - r_s * p.shoulder_width / 2
    J[K.R_SHOULDER] = sh_mid + r_s * p.shoulder_width / 2

    head = sh_mid + 0.20 * e_torso
    J[K.NOSE] = head + f_s * 0.10
    for name, dr, du in (("left_eye_inner", -0.015, 0.03), ("left_eye", -0.03, 0.03), ("left_eye_outer", -0.045, 0.03),
                         ("right_eye_inner", 0.015, 0.03), ("right_eye", 0.03, 0.03), ("right_eye_outer", 0.045, 0.03),
                         ("mouth_left", -0.025, -0.04), ("mouth_right", 0.025, -0.04)):
        J[K.IDX[name]] = head + f_s * 0.09 + r_s * dr + np.array([0, du, 0])
    J[K.IDX["left_ear"]] = head - r_s * 0.08
    J[K.IDX["right_ear"]] = head + r_s * 0.08

    down = np.array([0.0, -1.0, 0.0])
    for side, sh, el, wr, drop in ((-1, K.L_SHOULDER, K.L_ELBOW, K.L_WRIST, p.left_wrist_drop),
                                   (1, K.R_SHOULDER, K.R_ELBOW, K.R_WRIST, p.right_wrist_drop)):
        J[el] = J[sh] + 0.28 * _unit(down * 0.8 + r_s * side * 0.45 + f_s * 0.35)
        J[wr] = J[el] + 0.26 * _unit(down * 0.15 + r_s * side * 0.2 + f_s * 0.95) + down * drop
        base = J[wr]
        prefix = "left" if side < 0 else "right"
        J[K.IDX[f"{prefix}_pinky"]] = base + f_s * 0.07 + r_s * side * 0.02
        J[K.IDX[f"{prefix}_index"]] = base + f_s * 0.08
        J[K.IDX[f"{prefix}_thumb"]] = base + f_s * 0.04 - r_s * side * 0.02
    return J


def to_camera(J: np.ndarray, heading_deg: float) -> np.ndarray:
    """Skier frame (r, u, f) -> camera frame (x right, y down, z away)."""
    a = math.radians(heading_deg)
    fwd_c = np.array([math.sin(a), 0.0, math.cos(a)])
    right_c = np.array([math.cos(a), 0.0, -math.sin(a)])
    up_c = np.array([0.0, -1.0, 0.0])
    return J[:, [0]] * right_c + J[:, [1]] * up_c + J[:, [2]] * fwd_c


def make_frame(p: SkierParams, index: int = 0, t: float = 0.0, width: int = 960, height: int = 720,
               scale: float = 300.0, center: Optional[tuple] = None, vis: float = 0.95,
               with_world: bool = True) -> PoseFrame:
    """Build a PoseFrame with exact (noise-free) keypoints for the given parameters."""
    cam = to_camera(skeleton_skier_frame(p), p.heading_deg)
    hip_mid = (cam[K.L_HIP] + cam[K.R_HIP]) / 2
    world = cam - hip_mid
    pts = world[:, :2].copy()
    if p.slope_roll_deg:
        a = math.radians(p.slope_roll_deg)
        rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        pts = pts @ rot.T
    cx, cy = center if center else (width / 2, height * 0.42)
    xy = pts * scale + np.array([cx, cy])
    return PoseFrame(index=index, t=t, width=width, height=height, detected=True, xy=xy,
                     vis=np.full(K.N_KP, vis), world=world if with_world else None, source=f"synthetic-{index}")


# --------------------------------------------------------------------------
# A scripted run: linked turns with sinusoidal edge build-up
# --------------------------------------------------------------------------
@dataclass
class RunSpec:
    duration_s: float = 8.0
    fps: float = 30.0
    turn_period_s: float = 2.0        # one left + one right turn
    peak_inclination_deg: float = 30.0
    right_turn_scale: float = 1.0     # <1 = weaker right turns (asymmetry)
    angulation_deg: float = 15.0      # at the apex
    knee_min_deg: float = 115.0       # most flexed (apex)
    knee_max_deg: float = 150.0       # most extended (transition)
    counter_deg: float = 15.0         # upper body turned to the outside at the apex
    stance_ratio: float = 1.0
    fore_aft_deg: float = 4.0
    heading_deg: float = 180.0
    abrupt: bool = False              # Z-shaped turns: edge angle snaps to the peak
    pole_plant_offset: Optional[float] = 0.0  # fraction of a turn relative to edge change; None = no plants
    base: SkierParams = None  # type: ignore[assignment]


def run_params(spec: RunSpec) -> list[tuple[float, SkierParams]]:
    base = spec.base or SkierParams()
    n = int(round(spec.duration_s * spec.fps))
    turn_dur = spec.turn_period_s / 2
    out = []
    for i in range(n):
        t = i / spec.fps
        phase = 2 * math.pi * t / spec.turn_period_s
        s = math.sin(phase)
        if spec.abrupt:
            s = math.tanh(6.0 * s) / math.tanh(6.0)
        shape = abs(s)
        incl = spec.peak_inclination_deg * s
        if incl > 0:
            incl *= spec.right_turn_scale
        knee = spec.knee_max_deg - (spec.knee_max_deg - spec.knee_min_deg) * shape
        lw = rw = 0.0
        if spec.pole_plant_offset is not None:
            # edge changes happen at t = k * turn_dur; plant the new inside hand
            k = round(t / turn_dur - spec.pole_plant_offset)
            t_plant = (k + spec.pole_plant_offset) * turn_dur
            bump = 0.22 * math.exp(-((t - t_plant) / 0.09) ** 2)
            if k % 2 == 0:      # next turn has positive inclination -> right turn -> right hand
                rw = bump
            else:
                lw = bump
        p = replace(
            base,
            heading_deg=spec.heading_deg,
            inclination_deg=incl,
            angulation_deg=spec.angulation_deg * shape,
            knee_angle_deg=knee,
            fore_aft_deg=spec.fore_aft_deg,
            stance_ratio=spec.stance_ratio,
            shoulder_yaw_deg=-spec.counter_deg * s,   # right turn (s>0): turned left = countered
            pelvis_yaw_deg=-spec.counter_deg * s * 0.5,
            feet_yaw_deg=0.0,
            left_wrist_drop=lw,
            right_wrist_drop=rw,
        )
        out.append((t, p))
    return out


def run_sequence(spec: RunSpec, noise_px: float = 0.0, vis: float = 0.95, seed: int = 0,
                 with_world: bool = True, width: int = 960, height: int = 720) -> PoseSequence:
    """Exact keypoints for a scripted run (no rendering)."""
    rng = np.random.default_rng(seed)
    frames = []
    for i, (t, p) in enumerate(run_params(spec)):
        f = make_frame(p, i, t, width=width, height=height, vis=vis, with_world=with_world)
        if noise_px:
            f.xy = f.xy + rng.normal(0, noise_px, f.xy.shape)
        frames.append(f)
    return PoseSequence(frames=frames, fps=spec.fps, is_video=True, estimator="synthetic-exact")


# --------------------------------------------------------------------------
# Rendering (stick figure with colour-coded joint markers)
# --------------------------------------------------------------------------
# Joints the marker estimator recovers from pixels. Each gets a unique colour.
MARKER_JOINTS = [K.NOSE, K.L_SHOULDER, K.R_SHOULDER, K.L_ELBOW, K.R_ELBOW, K.L_WRIST, K.R_WRIST,
                 K.L_HIP, K.R_HIP, K.L_KNEE, K.R_KNEE, K.L_ANKLE, K.R_ANKLE,
                 K.L_HEEL, K.R_HEEL, K.L_TOE, K.R_TOE]


def marker_colors() -> dict[int, tuple[int, int, int]]:
    """Joint index -> BGR colour. Hues are spread evenly at full saturation."""
    colors = {}
    n = len(MARKER_JOINTS)
    for i, j in enumerate(MARKER_JOINTS):
        hsv = np.uint8([[[int(round(i * 180 / n)), 255, 255]]])
        b, g, r = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        colors[j] = (int(b), int(g), int(r))
    return colors


MARKER_RADIUS = 9


def render(frame: PoseFrame, background: int = 235) -> np.ndarray:
    """Draw the figure. Grey limbs + head, then saturated joint markers on top."""
    img = np.full((frame.height, frame.width, 3), background, np.uint8)
    cv2.line(img, (0, int(frame.height * 0.93)), (frame.width, int(frame.height * 0.93)), (215, 215, 215), 2)
    pt = lambda j: (int(round(frame.xy[j, 0])), int(round(frame.xy[j, 1])))
    depth = frame.world[:, 2] if frame.world is not None else np.zeros(K.N_KP)
    for a, b, _ in sorted(K.BONES, key=lambda bone: -(depth[bone[0]] + depth[bone[1]])):
        cv2.line(img, pt(a), pt(b), (95, 95, 95), 6, cv2.LINE_AA)
    head = (frame.xy[K.IDX["left_ear"]] + frame.xy[K.IDX["right_ear"]]) / 2
    cv2.circle(img, (int(head[0]), int(head[1])), 20, (120, 120, 120), -1, cv2.LINE_AA)
    colors = marker_colors()
    for j in sorted(MARKER_JOINTS, key=lambda j: -depth[j]):   # far joints first, near ones on top
        cv2.circle(img, pt(j), MARKER_RADIUS, colors[j], -1)
    return img


def ffmpeg_path() -> Optional[str]:
    return shutil.which("ffmpeg")


def write_video(frames: Iterable[np.ndarray], path: str, fps: float) -> str:
    """Encode BGR frames as H.264 mp4 (ffmpeg) or, without ffmpeg, mp4v via OpenCV."""
    frames = list(frames)
    h, w = frames[0].shape[:2]
    ff = ffmpeg_path()
    if ff:
        with tempfile.TemporaryDirectory() as tmp:
            for i, img in enumerate(frames):
                cv2.imwrite(os.path.join(tmp, f"f{i:05d}.png"), img)
            cmd = [ff, "-y", "-loglevel", "error", "-framerate", f"{fps}", "-i", os.path.join(tmp, "f%05d.png"),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", path]
            subprocess.run(cmd, check=True)
        return path
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for img in frames:
        vw.write(img)
    vw.release()
    return path


def write_sample_clip(path: str, spec: Optional[RunSpec] = None) -> str:
    spec = spec or RunSpec()
    seq = run_sequence(spec)
    return write_video((render(f) for f in seq.frames), path, spec.fps)


def write_sample_stills(out_dir: str, params: list[SkierParams], prefix: str = "still") -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, p in enumerate(params):
        path = os.path.join(out_dir, f"{prefix}_{i + 1:02d}.png")
        cv2.imwrite(path, render(make_frame(p, i)))
        paths.append(path)
    return paths
