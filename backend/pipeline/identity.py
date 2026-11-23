"""Keep one person per video: detect when the tracked skeleton jumps to someone else.

The pose tracker follows whoever is nearest the last box. With several people close
together (a chairlift, skiers in follow formation) it can hop between them, and every
metric then mixes different bodies. Position alone cannot tell a hop from fast skiing,
so each detected frame also carries a colour signature of the torso (jacket). A hop
shows as an abrupt, sustained change in that signature. The track is cut there and the
longest stretch is kept as "the skier"; frames of the other stretches are dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import cv2
import numpy as np

from . import keypoints as K

H_BINS, S_BINS = 12, 4
MIN_TORSO_PX = 30              # torso height (px); smaller boxes are mostly snow, so their colour is noise (A2 clip: false switches at 8)
SWITCH_DIST = 0.45             # Bhattacharyya distance to the segment reference that counts as "someone else"
CONFIRM_FRAMES = 2             # the change must persist this many detected frames (lighting glitches don't)
REF_FRAMES = 6                 # reference = median signature of the last N frames of the current segment
MIN_SEGMENT_FRAMES = 3         # shorter stretches are noise, not a second person


def torso_signature(image_bgr: np.ndarray, xy: np.ndarray, vis: np.ndarray) -> Optional[np.ndarray]:
    """Hue/saturation histogram of the box spanned by shoulders and hips (shrunk 15%), or None."""
    idx = [K.L_SHOULDER, K.R_SHOULDER, K.L_HIP, K.R_HIP]
    if np.min(vis[idx]) < 0.5:
        return None
    pts = xy[idx]
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    w, h = x1 - x0, y1 - y0
    if h < MIN_TORSO_PX or w < MIN_TORSO_PX / 2:
        return None
    x0, x1 = x0 + 0.15 * w, x1 - 0.15 * w
    y0, y1 = y0 + 0.15 * h, y1 - 0.15 * h
    H, W = image_bgr.shape[:2]
    xa, xb = int(max(0, x0)), int(min(W, x1))
    ya, yb = int(max(0, y0)), int(min(H, y1))
    if xb - xa < 2 or yb - ya < 2:
        return None
    hsv = cv2.cvtColor(image_bgr[ya:yb, xa:xb], cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [H_BINS, S_BINS], [0, 180, 0, 256]).flatten().astype(np.float32)
    s = float(hist.sum())
    return hist / s if s > 0 else None


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(cv2.compareHist(a.astype(np.float32), b.astype(np.float32), cv2.HISTCMP_BHATTACHARYYA))


def segment_identities(signatures: list[Optional[np.ndarray]]) -> tuple[list[int], int]:
    """(identity id per frame, -1 where there is no signature; number of switches).

    The identity changes where the signature differs from the current identity's reference by
    more than SWITCH_DIST for CONFIRM_FRAMES consecutive signed frames. A change back to someone
    seen before (signature matches an earlier identity's reference) reuses that id, so A-B-A is
    two switches between two people, not three people."""
    seg = [-1] * len(signatures)
    refs: dict[int, list[np.ndarray]] = {0: []}
    cur, pending, switches = 0, [], 0
    ref_of = lambda k: np.median(np.array(refs[k][-REF_FRAMES:]), axis=0)
    for i, s in enumerate(signatures):
        if s is None:
            continue
        if len(refs[cur]) < 2:
            refs[cur].append(s)
            seg[i] = cur
            continue
        if _dist(ref_of(cur), s) > SWITCH_DIST:
            pending.append((i, s))
            if len(pending) >= CONFIRM_FRAMES:
                probe = np.median(np.array([p[1] for p in pending]), axis=0)
                known = [k for k in refs if k != cur and refs[k] and _dist(ref_of(k), probe) <= SWITCH_DIST]
                cur = min(known, key=lambda k: _dist(ref_of(k), probe)) if known else max(refs) + 1
                refs.setdefault(cur, [])
                refs[cur] += [p[1] for p in pending]
                for j, _ in pending:
                    seg[j] = cur
                pending, switches = [], switches + 1
            continue
        for j, _ in pending:            # a glitch: those frames still belong to the current person
            seg[j] = cur
        pending = []
        refs[cur].append(s)
        seg[i] = cur
    for j, _ in pending:
        seg[j] = cur
    return seg, switches


@dataclass
class IdentityInfo:
    switches: int = 0
    kept_frames: int = 0
    dropped_frames: int = 0
    kept_t: tuple[float, float] = (0.0, 0.0)


def keep_main_identity(seq: K.PoseSequence) -> tuple[K.PoseSequence, IdentityInfo]:
    """Drop detections that belong to a different person than the longest track.

    Frames without a signature (torso not visible) inherit the segment of the nearest signed
    frame before them. Only acts on video; stills and signature-less runs pass through."""
    info = IdentityInfo()
    if not seq.is_video:
        return seq, info
    sigs = [f.appearance if f.detected else None for f in seq.frames]
    seg, switches = segment_identities(sigs)
    last = -1
    for i, f in enumerate(seq.frames):          # unsigned detections follow the previous signed frame
        if seg[i] >= 0:
            last = seg[i]
        elif f.detected:
            seg[i] = last
    counts: dict[int, int] = {}
    for i, f in enumerate(seq.frames):
        if f.detected and seg[i] >= 0:
            counts[seg[i]] = counts.get(seg[i], 0) + 1
    real = {k: n for k, n in counts.items() if n >= MIN_SEGMENT_FRAMES}
    if len(real) <= 1:
        return seq, info
    keep = max(real, key=lambda k: real[k])
    frames = []
    kept_t = [f.t for i, f in enumerate(seq.frames) if f.detected and seg[i] == keep]
    for i, f in enumerate(seq.frames):
        if f.detected and seg[i] != keep and seg[i] >= 0:
            frames.append(K.PoseFrame(index=f.index, t=f.t, width=f.width, height=f.height, source=f.source))
            info.dropped_frames += 1
        else:
            frames.append(f)
    info.switches = switches
    info.kept_frames = real[keep]
    info.kept_t = (min(kept_t), max(kept_t))
    return replace(seq, frames=frames), info
