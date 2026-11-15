"""Turn segmentation from the frontal-plane inclination signal.

The skier's leg axis leans left, then right, then left... The zero crossings
of the (2 Hz low-passed) inclination are the edge changes / transitions; the
span between two crossings is one turn. A span only counts as a turn when the
lean clearly leaves the neutral band (peak >= ``min_peak_deg``) and lasts at
least ``min_duration_s``, so jitter around neutral never creates a turn.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from .smoothing import fill_gaps, lowpass


@dataclass
class Turn:
    start: int            # frame index (inclusive)
    end: int              # frame index (inclusive)
    peak: int             # frame of peak |inclination|
    t_start: float
    t_end: float
    peak_deg: float       # signed image inclination at the peak (+ = image right)
    direction: str        # 'left' | 'right' in the SKIER's frame when facing is known, else image side
    direction_frame: str  # 'skier' | 'image'
    complete: bool        # bounded by an edge change at both ends

    @property
    def duration(self) -> float:
        return self.t_end - self.t_start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration"] = round(self.duration, 3)
        return d


def segment_turns(t: np.ndarray, inclination: np.ndarray, valid: np.ndarray, fps: float,
                  facing_sign: float | None = None, min_peak_deg: float = 6.0,
                  min_duration_s: float = 0.35, max_gap_s: float = 0.5) -> tuple[list[Turn], np.ndarray]:
    """Return (turns, smoothed_inclination). ``facing_sign`` +1 = back view, -1 = front view."""
    n = len(t)
    if n < 5 or fps <= 0:
        return [], np.full(n, np.nan)
    x = np.where(valid, inclination, np.nan).astype(float)
    x, _ = fill_gaps(x, max(1, int(round(max_gap_s * fps))))
    xs = lowpass(x, fps, cutoff_hz=2.0)
    turns: list[Turn] = []
    finite = np.isfinite(xs)
    i = 0
    while i < n:
        if not finite[i] or xs[i] == 0:
            i += 1
            continue
        sign = np.sign(xs[i])
        j = i
        while j + 1 < n and finite[j + 1] and np.sign(xs[j + 1]) == sign:
            j += 1
        seg = xs[i:j + 1]
        peak_rel = int(np.argmax(np.abs(seg)))
        dur = t[j] - t[i]
        if abs(seg[peak_rel]) >= min_peak_deg and dur >= min_duration_s:
            starts_at_crossing = i > 0 and finite[i - 1] and np.sign(xs[i - 1]) == -sign
            ends_at_crossing = j + 1 < n and finite[j + 1] and np.sign(xs[j + 1]) == -sign
            image_right = sign > 0
            if facing_sign:
                right = image_right if facing_sign > 0 else not image_right
                direction, dframe = ("right" if right else "left"), "skier"
            else:
                direction, dframe = ("right" if image_right else "left"), "image"
            turns.append(Turn(start=i, end=j, peak=i + peak_rel, t_start=float(t[i]), t_end=float(t[j]),
                              peak_deg=float(seg[peak_rel]), direction=direction, direction_frame=dframe,
                              complete=bool(starts_at_crossing and ends_at_crossing)))
        i = j + 1
    return turns, xs


def transitions(turns: list[Turn]) -> list[tuple[float, Turn]]:
    """Edge changes: (time, the turn that begins there), for consecutive turns of opposite direction."""
    out = []
    for a, b in zip(turns, turns[1:]):
        if a.direction != b.direction and b.start - a.end <= 3:
            out.append(((a.t_end + b.t_start) / 2.0, b))
    return out
