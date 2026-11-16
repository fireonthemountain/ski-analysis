"""Validation engine: measured evidence vs the assessor's rating.

For every assessed item:

1. measure one value (per-item evaluator below) with an uncertainty
   ``u = sqrt(base_uncertainty^2 + spread^2)`` where spread is the robust
   standard error of the samples (1.4826 * MAD / sqrt(n_independent));
2. look at where the value sits relative to the band the assessor chose:
      inside the band by >= u            -> AGREE
      outside the band by >= u           -> DISAGREE
      within u of the band's edge        -> INCONCLUSIVE (borderline)
3. anything that could not be measured properly is INCONCLUSIVE with the
   reason spelled out - wrong camera view, stills where video is needed, too
   few confident frames, no turns found, no 3D, or overall confidence below
   ``MIN_CONFIDENCE``. The engine never guesses a verdict.

Only frames whose required landmarks have visibility >= 0.5 are used
(metrics.VIS_OK); interpolated frames (visibility 0.4) are never evidence.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

import numpy as np

from .assessment import CATALOG_BY_ID, Assessment, Item
from .metrics import MetricSeries
from .segmentation import Turn, transitions

MIN_CONFIDENCE = 0.30          # below this the verdict is forced to inconclusive
MIN_FRAMES_VIDEO = 5           # confident frames needed for a per-frame statistic on video
ANGULATION_MIN_LEAN = 12.0     # deg of leg lean before angulation is meaningful
POLE_MIN_PROMINENCE = 0.12     # wrist drop (torso lengths) that counts as a plant movement
POLE_MIN_TRANSITIONS = 3


@dataclass
class Measurement:
    value: Optional[float] = None
    spread: float = 0.0                 # robust standard error of the samples
    n_frames: int = 0
    n_turns: Optional[int] = None
    pose_conf: float = 0.0              # mean landmark confidence of the frames used
    sample_factor: float = 1.0
    extra_factor: float = 1.0           # view / fallback penalties
    method: str = ""
    evidence: list[tuple[int, str]] = field(default_factory=list)   # (frame index, caption)
    notes: list[str] = field(default_factory=list)
    unavailable: Optional[str] = None   # reason this could not be measured
    category_override: Optional[str] = None   # for categories that are not on the number line


@dataclass
class Context:
    ms: MetricSeries
    turns: list[Turn]
    incl_smooth: np.ndarray

    @property
    def n(self) -> int:
        return len(self.ms)


# ------------------------------------------------------------------ helpers
def robust_se(x: np.ndarray, n_ind: float) -> float:
    if len(x) < 3:
        return 0.0
    mad = float(np.median(np.abs(x - np.median(x))))
    return 1.4826 * mad / math.sqrt(max(1.0, n_ind))


def _n_independent(ctx: Context, count: int) -> float:
    """Consecutive video frames are not independent: count ~2 samples per second."""
    if not ctx.ms.is_video or ctx.ms.fps <= 0:
        return float(count)
    return max(1.0, count / ctx.ms.fps * 2.0)


def _sample_factor(ctx: Context, count: int, n_turns: Optional[int] = None) -> float:
    if n_turns is not None:
        return 0.5 + 0.5 * min(1.0, n_turns / 4.0)
    if ctx.ms.is_video:
        return 0.5 + 0.5 * min(1.0, count / max(1.0, ctx.ms.fps * 2.0))
    return 0.6 + 0.4 * min(1.0, count / 4.0)


def _view_gate(ctx: Context, item: Item, m: Measurement) -> bool:
    """Apply the item's camera-view requirement. Returns False when unavailable."""
    need, view = item.needs_view, ctx.ms.view
    if need is None:
        return True
    names = {"frontal": "front or back", "side": "side"}
    want = names[need]
    if view == need:
        return True
    if view == "oblique":
        m.unavailable = (f"Camera view is oblique (between front and side). This is measured in the image plane and needs a {want} view; "
                         "at an oblique angle the angle would be biased. If the view really is close to "
                         f"{want}, set the camera view manually and re-run.")
        return False
    if view == "unknown" and not np.any(ctx.ms.pose_conf > 0):
        m.unavailable = "No skier was detected in the media."
    elif view == "unknown":
        m.unavailable = "Could not determine the camera view (shoulders and hips not confidently detected)."
    else:
        m.unavailable = f"Needs a {want} view; this media is a {names.get(view, view)} view."
    return False


def _select(ctx: Context, name: str, m: Measurement, extra_mask: Optional[np.ndarray] = None,
            what: str = "") -> Optional[np.ndarray]:
    """Indices of confident frames for ``name`` or None (and set m.unavailable)."""
    mask = ctx.ms.valid(name)
    if extra_mask is not None:
        mask = mask & extra_mask
    idx = np.flatnonzero(mask)
    need = MIN_FRAMES_VIDEO if ctx.ms.is_video else 1
    if len(idx) < need:
        detected = int(np.sum(ctx.ms.pose_conf > 0))
        if detected == 0:
            m.unavailable = "No skier was detected in the media."
        elif len(np.flatnonzero(ctx.ms.valid(name))) < need:
            m.unavailable = (f"Pose confidence too low: only {len(np.flatnonzero(ctx.ms.valid(name)))} of {ctx.n} frames have the "
                             f"needed joints above the 0.5 visibility gate (need {need}).")
        else:
            m.unavailable = what or f"Only {len(idx)} usable frames (need {need})."
        return None
    m.n_frames = len(idx)
    m.pose_conf = float(np.mean(ctx.ms.conf[name][idx]))
    return idx


def _nearest(idx: np.ndarray, vals: np.ndarray, target: float) -> int:
    return int(idx[int(np.argmin(np.abs(vals - target)))])


def _turn_peak_values(ctx: Context, name: str, q: float = 95.0) -> list[tuple[Turn, float, int]]:
    """Per turn: (turn, q-th percentile of ``name`` within the turn, frame of its max)."""
    out = []
    valid = ctx.ms.valid(name)
    v = ctx.ms.values[name]
    for turn in ctx.turns:
        idx = np.arange(turn.start, turn.end + 1)
        idx = idx[valid[idx]]
        if len(idx) >= 3:
            out.append((turn, float(np.percentile(v[idx], q)), int(idx[int(np.argmax(v[idx]))])))
    return out


# --------------------------------------------------------------- evaluators
def _median_item(series: str, label: str, fmt: str = "{:.0f}"):
    def run(ctx: Context, item: Item) -> Measurement:
        m = Measurement(method=item.measure)
        if not _view_gate(ctx, item, m):
            return m
        idx = _select(ctx, series, m)
        if idx is None:
            return m
        v = ctx.ms.values[series][idx]
        m.value = float(np.median(v))
        m.spread = robust_se(v, _n_independent(ctx, len(idx)))
        m.sample_factor = _sample_factor(ctx, len(idx))
        f_med = _nearest(idx, v, m.value)
        m.evidence = [(f_med, f"typical: {label} {fmt.format(ctx.ms.values[series][f_med])}")]
        for f, tag in ((int(idx[int(np.argmin(v))]), "lowest"), (int(idx[int(np.argmax(v))]), "highest")):
            if f != f_med and len(idx) > 1:
                m.evidence.append((f, f"{tag}: {label} {fmt.format(ctx.ms.values[series][f])}"))
        return m
    return run


def eval_stance_width(ctx: Context, item: Item) -> Measurement:
    if ctx.ms.view == "frontal" or not np.any(ctx.ms.valid("stance_width_3d")):
        probe = Measurement()
        frontal_item = replace(item, needs_view="frontal")
        if _view_gate(ctx, frontal_item, probe):
            m = _median_item("stance_width_2d", "stance", "{:.2f}x")(ctx, item)
            m.extra_factor *= probe.extra_factor
            m.notes += probe.notes
            return m
        probe.method = item.measure
        probe.unavailable += " No 3D landmarks are available to estimate it from this view."
        return probe
    m = _median_item("stance_width_3d", "stance", "{:.2f}x")(ctx, item)
    m.extra_factor *= 0.7
    m.notes.append("Not a front/back view, so this uses estimated 3D landmarks (lower confidence).")
    return m


def eval_fore_aft(ctx: Context, item: Item) -> Measurement:
    m = _median_item("fore_aft", "fore-aft", "{:+.0f} deg")(ctx, item)
    if m.value is not None:
        idx = np.flatnonzero(ctx.ms.valid("fore_aft"))
        sole = float(np.mean(ctx.ms.values["fore_aft_ref"][idx]))
        if sole < 0.5:
            m.extra_factor *= 0.6
            m.notes.append("Feet were not confidently visible, so image vertical is the reference: this assumes a level camera and ignores slope pitch.")
        else:
            m.notes.append("Slope reference: boot-sole line (heel to toe).")
    return m


def eval_knee(ctx: Context, item: Item) -> Measurement:
    m = _median_item("knee_mean", "knee", "{:.0f} deg")(ctx, item)
    _note_2d(ctx, m, "knee_mean")
    return m


def eval_hip(ctx: Context, item: Item) -> Measurement:
    m = _median_item("hip_angle", "hip", "{:.0f} deg")(ctx, item)
    _note_2d(ctx, m, "hip_angle")
    return m


def _note_2d(ctx: Context, m: Measurement, name: str) -> None:
    """Joint angles without 3D are only trustworthy when the joint bends in the image plane (side view)."""
    if m.value is None:
        return
    idx = np.flatnonzero(ctx.ms.valid(name))
    if float(np.mean(ctx.ms.values["angles_3d"][idx])) < 0.5:
        if ctx.ms.view == "side":
            m.notes.append("Measured in the 2D image plane (side view, so foreshortening is small).")
        else:
            m.value = None
            m.evidence = []
            m.unavailable = ("No 3D landmarks from this pose estimator, and the view is not side-on: a 2D image "
                             "foreshortens the joint (legs look straighter than they are), so no value is reported.")


def eval_vertical(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    idx = _select(ctx, "knee_mean", m)
    if idx is None:
        return m
    span = ctx.ms.t[idx[-1]] - ctx.ms.t[idx[0]]
    if span < 2.0:
        m.unavailable = f"Only {span:.1f} s of usable footage; a flexion/extension range needs at least 2 s."
        return m
    v = ctx.ms.values["knee_mean"][idx]
    lo, hi = np.percentile(v, [10, 90])
    m.value = float(hi - lo)
    m.spread = 0.0
    m.sample_factor = 0.5 + 0.5 * min(1.0, span / 4.0)
    m.evidence = [(int(idx[int(np.argmin(v))]), f"most flexed: knee {v.min():.0f} deg"),
                  (int(idx[int(np.argmax(v))]), f"most extended: knee {v.max():.0f} deg")]
    _note_2d(ctx, m, "knee_mean")
    return m


def eval_edge(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    idx = _select(ctx, "edge_proxy", m)
    if idx is None:
        return m
    v = ctx.ms.values["edge_proxy"]
    per_turn = _turn_peak_values(ctx, "edge_proxy") if ctx.ms.is_video else []
    if per_turn:
        peaks = np.array([p[1] for p in per_turn])
        m.value = float(np.median(peaks))
        m.n_turns = len(per_turn)
        m.spread = robust_se(peaks, len(peaks))
        m.sample_factor = _sample_factor(ctx, len(idx), len(per_turn))
        top = sorted(per_turn, key=lambda p: -p[1])[:3]
        m.evidence = [(f, f"{t.direction} turn peak: shin tilt {v[f]:.0f} deg") for t, _, f in top]
    elif ctx.ms.is_video:
        m.value = float(np.percentile(v[idx], 95))
        m.sample_factor = 0.5
        m.notes.append("No complete turns were segmented, so this is the 95th percentile over the whole clip.")
        m.evidence = [(int(idx[int(np.argmax(v[idx]))]), f"largest shin tilt {v[idx].max():.0f} deg")]
    else:
        m.value = float(np.max(v[idx]))
        m.sample_factor = _sample_factor(ctx, len(idx))
        m.notes.append("Stills: this is the largest value among the frames you supplied - it is only the peak if one of them is at the turn apex.")
        order = idx[np.argsort(-v[idx])][:3]
        m.evidence = [(int(f), f"shin tilt {v[f]:.0f} deg") for f in order]
    return m


def eval_angulation(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    incl = ctx.ms.values["inclination"]
    leaning = np.abs(np.nan_to_num(incl, nan=0.0)) >= ANGULATION_MIN_LEAN
    idx = _select(ctx, "angulation", m, leaning,
                  what=f"No frames where the legs are inclined at least {ANGULATION_MIN_LEAN:.0f} deg, so there is nothing to angulate against.")
    if idx is None:
        return m
    v = ctx.ms.values["angulation"][idx]
    m.value = float(np.median(v))
    n_turns = len([t for t in ctx.turns if abs(t.peak_deg) >= ANGULATION_MIN_LEAN]) if ctx.ms.is_video else None
    m.n_turns = n_turns or None
    m.spread = robust_se(v, n_turns if n_turns else _n_independent(ctx, len(idx)))
    m.sample_factor = _sample_factor(ctx, len(idx), n_turns or None)
    order = idx[np.argsort(-np.abs(incl[idx]))]
    picked: list[int] = []
    for f in order:                       # most-inclined frames, spread apart in time
        if all(abs(int(f) - p) > max(3, int(ctx.ms.fps * 0.4)) for p in picked) or not ctx.ms.is_video:
            picked.append(int(f))
        if len(picked) == 3:
            break
    m.evidence = [(f, f"legs {abs(incl[f]):.0f} deg, torso {abs(ctx.ms.values['torso_tilt'][f]):.0f} deg -> angulation {ctx.ms.values['angulation'][f]:+.0f} deg") for f in picked]
    return m


def eval_separation(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not np.any(np.isfinite(ctx.ms.values["separation"])):
        m.unavailable = "Needs 3D landmarks, which this pose estimator did not provide."
        return m
    idx = _select(ctx, "separation", m)
    if idx is None:
        return m
    a = np.abs(ctx.ms.values["separation"][idx])
    if ctx.ms.is_video:
        m.value = float(np.percentile(a, 90))
        m.sample_factor = _sample_factor(ctx, len(idx))
    else:
        m.value = float(np.max(a))
        m.sample_factor = _sample_factor(ctx, len(idx))
        m.notes.append("Stills: largest value among the frames supplied.")
    if float(np.mean(ctx.ms.values["separation_ref"][idx])) < 0.5:
        m.extra_factor *= 0.8
        m.notes.append("Feet not confidently visible: measured shoulders against the pelvis (spinal twist) instead of against the skis, which under-reads leg rotation.")
    order = idx[np.argsort(-a)][:1]
    m.evidence = [(int(f), f"shoulders vs feet {ctx.ms.values['separation'][f]:+.0f} deg") for f in order]
    return m


def eval_counter(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    if not np.any(np.isfinite(ctx.ms.values["separation"])):
        m.unavailable = "Needs 3D landmarks, which this pose estimator did not provide."
        return m
    idx = _select(ctx, "counter", m, what="No frames with enough lean (8 deg) to tell which way the skier is turning.")
    if idx is None:
        return m
    v = ctx.ms.values["counter"][idx]
    m.value = float(np.median(v))
    n_turns = len(ctx.turns) if ctx.ms.is_video and ctx.turns else None
    m.n_turns = n_turns
    m.spread = robust_se(v, n_turns if n_turns else _n_independent(ctx, len(idx)))
    m.sample_factor = _sample_factor(ctx, len(idx), n_turns)
    f = _nearest(idx, v, m.value)
    m.evidence = [(f, f"typical: counter {v[int(np.argmin(np.abs(v - m.value)))]:+.0f} deg")]
    return m


def eval_turn_shape(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    incl, valid, t = ctx.ms.values["inclination"], ctx.ms.valid("inclination"), ctx.ms.t
    fracs, ev = [], []
    for turn in ctx.turns:
        if not turn.complete:
            continue
        idx = np.arange(turn.start, turn.end + 1)
        if valid[idx].mean() < 0.8:
            continue
        x = np.abs(np.where(valid[idx], incl[idx], np.nan))
        ok = np.isfinite(x)
        x = np.interp(np.arange(len(x)), np.flatnonzero(ok), x[ok])
        target = 0.7 * float(np.max(x))
        k = int(np.argmax(x >= target))
        if k == 0:
            cross = 0.0
        else:
            cross = (k - 1) + (target - x[k - 1]) / max(1e-9, x[k] - x[k - 1])
        fracs.append(cross / max(1, len(x) - 1))
        ev.append((int(turn.start + k), f"{turn.direction} turn: lean reaches 70% of peak {fracs[-1] * 100:.0f}% of the way in"))
    if len(fracs) < 2:
        m.unavailable = f"Found {len(fracs)} complete turn(s) with clean tracking; turn shape needs at least 2."
        return m
    f = np.array(fracs)
    m.value = float(np.median(f))
    m.n_turns = len(f)
    m.n_frames = int(np.sum(valid))
    m.pose_conf = float(np.mean(ctx.ms.conf["inclination"][valid]))
    m.spread = robust_se(f, len(f))
    m.sample_factor = _sample_factor(ctx, 0, len(f))
    m.evidence = ev[:3]
    return m


def eval_symmetry(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    turns = [t for t in ctx.turns if t.direction_frame == "skier"]
    left = [t for t in turns if t.direction == "left"]
    right = [t for t in turns if t.direction == "right"]
    if not left or not right:
        m.unavailable = f"Found {len(left)} left and {len(right)} right turn(s); symmetry needs at least one of each (two of each is better)."
        return m
    L = float(np.median([abs(t.peak_deg) for t in left]))
    R = float(np.median([abs(t.peak_deg) for t in right]))
    m.value = (R - L) / ((R + L) / 2.0) * 100.0
    m.n_turns = len(left) + len(right)
    valid = ctx.ms.valid("inclination")
    m.n_frames = int(np.sum(valid))
    m.pose_conf = float(np.mean(ctx.ms.conf["inclination"][valid]))
    se = [robust_se(np.array([abs(t.peak_deg) for t in g]), len(g)) for g in (left, right)]
    m.spread = float(np.hypot(*se)) / ((R + L) / 2.0) * 100.0
    m.sample_factor = 0.5 + 0.5 * min(1.0, min(len(left), len(right)) / 2.0)
    bl = max(left, key=lambda t: abs(t.peak_deg))
    br = max(right, key=lambda t: abs(t.peak_deg))
    m.evidence = [(bl.peak, f"left turn peak lean {abs(bl.peak_deg):.0f} deg (median {L:.0f})"),
                  (br.peak, f"right turn peak lean {abs(br.peak_deg):.0f} deg (median {R:.0f})")]
    return m


def eval_pole_plant(ctx: Context, item: Item) -> Measurement:
    m = Measurement(method=item.measure)
    if not _view_gate(ctx, item, m):
        return m
    trans = transitions(ctx.turns)
    if len(trans) < POLE_MIN_TRANSITIONS:
        m.unavailable = f"Found {len(trans)} edge change(s); pole-plant timing needs at least {POLE_MIN_TRANSITIONS}."
        return m
    mean_dur = float(np.mean([t.duration for t in ctx.turns]))
    t = ctx.ms.t
    offsets, ev, usable, confs = [], [], 0, []
    for t_edge, new_turn in trans:
        hands = (["wrist_drop_right"] if new_turn.direction == "right" else ["wrist_drop_left"]) \
            if new_turn.direction_frame == "skier" else ["wrist_drop_left", "wrist_drop_right"]
        win = np.flatnonzero((t >= t_edge - 0.45 * mean_dur) & (t <= t_edge + 0.45 * mean_dur))
        best = None
        window_ok = False
        for hand in hands:
            ok = ctx.ms.valid(hand)[win]
            if len(win) < 5 or ok.mean() < 0.7:
                continue
            window_ok = True
            confs.append(float(np.mean(ctx.ms.conf[hand][win][ok])))
            w = win[ok]
            x = ctx.ms.values[hand][w]
            k = int(np.argmax(x))
            prominence = float(x[k] - np.median(x))
            if prominence >= POLE_MIN_PROMINENCE and 0 < k < len(x) - 1 and (best is None or prominence > best[0]):
                best = (prominence, int(w[k]), (t[w[k]] - t_edge) / mean_dur)
        usable += int(window_ok)
        if best:
            offsets.append(best[2])
            ev.append((best[1], f"hand reaches down {best[2] * 100:+.0f}% of a turn from the edge change"))
    if usable < POLE_MIN_TRANSITIONS:
        m.unavailable = f"Wrists were confidently tracked around only {usable} of {len(trans)} edge changes (need {POLE_MIN_TRANSITIONS})."
        return m
    rate = len(offsets) / usable
    m.n_turns = usable
    m.n_frames = int(np.sum(ctx.ms.valid("wrist_drop_left") | ctx.ms.valid("wrist_drop_right")))
    m.pose_conf = float(np.mean(confs)) if confs else 0.0
    m.sample_factor = 0.5 + 0.5 * min(1.0, usable / 6.0)
    m.notes.append(f"A plant-like hand movement was found at {len(offsets)} of {usable} edge changes.")
    if rate >= 0.6:
        o = np.array(offsets)
        m.value = float(np.median(o))
        m.spread = robust_se(o, len(o))
        m.evidence = ev[:3]
    elif rate <= 0.2:
        m.category_override = "none"
        m.evidence = ev[:1]
    else:
        m.unavailable = (f"A plant-like hand movement shows at only {len(offsets)} of {usable} edge changes - "
                         "too inconsistent to time, and too frequent to call absent.")
    return m


EVALUATORS: dict[str, Callable[[Context, Item], Measurement]] = {
    "stance_width": eval_stance_width,
    "fore_aft": eval_fore_aft,
    "stance_height": eval_knee,
    "hip_flexion": eval_hip,
    "vertical_movement": eval_vertical,
    "edge_angle": eval_edge,
    "angulation": eval_angulation,
    "separation": eval_separation,
    "counter": eval_counter,
    "turn_shape": eval_turn_shape,
    "turn_symmetry": eval_symmetry,
    "pole_plant": eval_pole_plant,
}


# ------------------------------------------------------------------ verdict
def confidence_label(c: float) -> str:
    return "high" if c >= 0.7 else "medium" if c >= 0.5 else "low"


def decide(item: Item, rating: str, m: Measurement) -> dict:
    """Turn a Measurement into the per-item result dict."""
    opt = {o.id: o for o in item.all_options()}
    res = {
        "item_id": item.id, "label": item.label, "group": item.group, "fundamental": item.fundamental,
        "experimental": item.experimental,
        "assessed": {"rating": rating, "label": opt[rating].label},
        "measured": None, "verdict": "inconclusive", "reason": "", "confidence": 0.0, "confidence_label": "none",
        "method": item.measure, "unit": item.unit,
        "thresholds": {"bounds": list(item.bounds), "options": [o.id for o in item.options],
                       "labels": [o.label for o in item.options]},
        "notes": list(m.notes), "limitations": list(item.limitations),
        "evidence": [{"frame": f, "caption": c} for f, c in m.evidence],
    }
    if m.unavailable:
        res["reason"] = m.unavailable
        return res

    base_conf = item.conf_cap * m.extra_factor * m.pose_conf * m.sample_factor

    if m.category_override is not None:           # e.g. "no visible pole plant"
        cat = opt[m.category_override]
        res["measured"] = {"value": None, "category": cat.id, "category_label": cat.label, "uncertainty": None,
                           "n_frames": m.n_frames, "n_turns": m.n_turns}
        conf = base_conf * 0.8
        verdict, reason = ("agree", f"Measured: {cat.label}.") if rating == cat.id else \
            ("disagree", f"Measured '{cat.label}', assessed '{opt[rating].label}'.")
    else:
        u = math.sqrt(item.base_uncertainty ** 2 + m.spread ** 2)
        cat = item.category_for(m.value)
        res["measured"] = {"value": round(m.value, 3), "category": cat.id, "category_label": cat.label,
                           "uncertainty": round(u, 3), "n_frames": m.n_frames, "n_turns": m.n_turns}
        val = f"{m.value:.2f}" if abs(m.value) < 10 and item.unit != "deg" else f"{m.value:.0f}"
        shown = f"{val} {item.unit} (+/- {u:.2f})" if u < 1 else f"{val} {item.unit} (+/- {u:.0f})"
        if rating not in [o.id for o in item.options]:
            # assessor chose an off-axis category (e.g. "no pole plant") but a value was measured
            margin, verdict = 2 * u, "disagree"
            reason = f"Measured {shown} = '{cat.label}', but the assessment says '{opt[rating].label}'."
        else:
            lo, hi = item.range_for(rating)
            margin = min(m.value - lo, hi - m.value)       # + inside the assessed band, - outside
            band = _band_text(item, lo, hi)
            if margin >= u:
                verdict = "agree"
                reason = f"Measured {shown} sits inside the '{opt[rating].label}' band ({band})."
            elif margin <= -u:
                verdict = "disagree"
                reason = f"Measured {shown} is '{cat.label}', outside the '{opt[rating].label}' band ({band})."
            else:
                verdict = "inconclusive"
                side = "inside" if margin >= 0 else "outside"
                reason = (f"Borderline: measured {shown} is just {side} the '{opt[rating].label}' band ({band}) - "
                          "closer to the threshold than the measurement uncertainty.")
        conf = base_conf * (0.6 + 0.4 * min(1.0, abs(margin) / (2 * u)))

    if verdict != "inconclusive" and conf < MIN_CONFIDENCE:
        reason = (f"Confidence {conf:.2f} is below the {MIN_CONFIDENCE:.2f} floor, so no verdict is given. "
                  f"(The measurement itself pointed to: {reason})")
        verdict = "inconclusive"
    res.update(verdict=verdict, reason=reason, confidence=round(float(conf), 3), confidence_label=confidence_label(conf))
    return res


def _band_text(item: Item, lo: float, hi: float) -> str:
    f = (lambda x: f"{x:g}")
    if lo == float("-inf"):
        return f"below {f(hi)} {item.unit}"
    if hi == float("inf"):
        return f"{f(lo)} {item.unit} or more"
    return f"{f(lo)} to {f(hi)} {item.unit}"


def validate(assessment: Assessment, ctx: Context) -> list[dict]:
    results = []
    for a in assessment.items:
        item = CATALOG_BY_ID[a.item_id]
        if item.needs_video and not ctx.ms.is_video:
            m = Measurement(method=item.measure,
                            unavailable="Needs video: this is about movement over time and cannot be read from still frames.")
        else:
            m = EVALUATORS[item.id](ctx, item)
        r = decide(item, a.rating, m)
        r["assessed"]["notes"] = a.notes
        results.append(r)
    return results


def summarize(results: list[dict]) -> dict:
    c = {v: sum(1 for r in results if r["verdict"] == v) for v in ("agree", "disagree", "inconclusive")}
    decided = c["agree"] + c["disagree"]
    return {**c, "total": len(results), "decided": decided,
            "agreement_rate": round(c["agree"] / decided, 3) if decided else None}
