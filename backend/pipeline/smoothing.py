"""Tracking clean-up and smoothing of a pose sequence (video only).

1. Jump rejection - a frame whose hip centre teleports by more than one body
   length from its neighbours is treated as a mis-detection (wrong person).
2. Gap filling - joints missing/untrusted for <= ``max_gap_s`` are linearly
   interpolated. Interpolated values get visibility ``INTERP_VIS`` (below the
   0.5 trust gate) so they keep the filter continuous but are never used as
   evidence for a verdict.
3. Low-pass - zero-phase 2nd-order Butterworth (filtfilt), default 6 Hz, the
   standard choice for human-movement kinematics; skiing joint motion is well
   below that, pose jitter is mostly above.
"""
from __future__ import annotations

import copy

import numpy as np
from scipy.signal import butter, filtfilt

from . import keypoints as K
from .keypoints import PoseSequence

INTERP_VIS = 0.4
TRUST_VIS = 0.5


def _runs(mask: np.ndarray):
    """Yield (start, end_exclusive) for each run of True in ``mask``."""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(int), [0]))))
    return list(zip(idx[::2], idx[1::2]))


def lowpass(x: np.ndarray, fps: float, cutoff_hz: float = 6.0) -> np.ndarray:
    """Zero-phase low-pass each finite run of a 1D series; NaNs are preserved."""
    y = x.copy()
    if fps <= 0:
        return y
    cutoff = min(cutoff_hz, fps / 3.0)
    b, a = butter(2, cutoff / (fps / 2.0))
    padlen = 3 * max(len(a), len(b))
    for s, e in _runs(np.isfinite(x)):
        if e - s > padlen:
            y[s:e] = filtfilt(b, a, x[s:e])
    return y


def fill_gaps(x: np.ndarray, max_gap: int) -> tuple[np.ndarray, np.ndarray]:
    """Linear interpolation over interior NaN runs of length <= max_gap.
    Returns (filled, was_interpolated)."""
    y = x.copy()
    filled = np.zeros(len(x), bool)
    for s, e in _runs(~np.isfinite(x)):
        if s == 0 or e == len(x) or (e - s) > max_gap:
            continue
        y[s:e] = np.interp(np.arange(s, e), [s - 1, e], [x[s - 1], x[e]])
        filled[s:e] = True
    return y, filled


def smooth_sequence(seq: PoseSequence, cutoff_hz: float = 6.0, max_gap_s: float = 0.3) -> tuple[PoseSequence, dict]:
    """Return a cleaned copy of ``seq`` plus a small stats dict for the report."""
    stats = {"jump_frames_rejected": 0, "joint_samples_interpolated": 0, "cutoff_hz": None}
    if not seq.is_video or len(seq.frames) < 5 or seq.fps <= 0:
        return seq, stats
    frames = [copy.copy(f) for f in seq.frames]
    n = len(frames)
    xy = np.stack([f.xy for f in frames]).astype(float)             # (n, 33, 2)
    vis = np.stack([f.vis for f in frames]).astype(float)           # (n, 33)
    has_world = all((f.world is not None) or (not f.detected) for f in frames) and any(f.world is not None for f in frames)
    world = np.stack([f.world if f.world is not None else np.full((K.N_KP, 3), np.nan) for f in frames]) if has_world else None
    detected = np.array([f.detected for f in frames])
    xy[~detected] = np.nan
    vis[~detected] = 0.0

    # 1. jump rejection on hip centre, in units of body size
    hip = (xy[:, K.L_HIP] + xy[:, K.R_HIP]) / 2
    sh = (xy[:, K.L_SHOULDER] + xy[:, K.R_SHOULDER]) / 2
    torso = np.linalg.norm(sh - hip, axis=1)
    size = float(np.median(torso[np.isfinite(torso)])) * 3.0 if np.isfinite(torso).any() else float('nan')   # ~ body length in px
    if np.isfinite(size) and size > 0:
        for i in range(1, n - 1):
            if not (detected[i - 1] and detected[i] and detected[i + 1]):
                continue
            d_prev = np.linalg.norm(hip[i] - hip[i - 1])
            d_next = np.linalg.norm(hip[i] - hip[i + 1])
            d_skip = np.linalg.norm(hip[i + 1] - hip[i - 1])
            if d_prev > size and d_next > size and d_skip < size:
                xy[i] = np.nan
                vis[i] = 0.0
                if world is not None:
                    world[i] = np.nan
                detected[i] = False
                stats["jump_frames_rejected"] += 1

    # 2 + 3. per-joint gap fill and low-pass
    max_gap = max(1, int(round(max_gap_s * seq.fps)))
    untrusted = vis < 0.3
    stats["cutoff_hz"] = round(min(cutoff_hz, seq.fps / 3.0), 2)
    for j in range(K.N_KP):
        interp_j = np.zeros(n, bool)
        for arr in ([xy] + ([world] if world is not None else [])):
            for c in range(arr.shape[2]):
                x = arr[:, j, c].copy()
                x[untrusted[:, j]] = np.nan
                x, filled = fill_gaps(x, max_gap)
                interp_j |= filled
                arr[:, j, c] = lowpass(x, seq.fps, cutoff_hz)
        vis[interp_j, j] = INTERP_VIS
        stats["joint_samples_interpolated"] += int(interp_j.sum())

    for i, f in enumerate(frames):
        ok = np.isfinite(xy[i]).all(axis=1)
        f.xy = xy[i]
        f.vis = np.where(ok, vis[i], 0.0)
        f.xy = np.where(ok[:, None], f.xy, np.nan)
        if world is not None:
            f.world = world[i] if np.isfinite(world[i][K.CORE]).all() else None
            if f.world is not None:
                f.world = np.nan_to_num(f.world, nan=0.0)
        f.detected = bool(np.isfinite(f.xy[K.CORE]).any())
    return PoseSequence(frames=frames, fps=seq.fps, is_video=True, estimator=seq.estimator), stats
