"""Identity tracking (one person per video) and the seated / not-skiing check."""
import numpy as np
import pytest

from pipeline import identity as I
from pipeline import metrics as M
from pipeline.keypoints import N_KP, PoseFrame, PoseSequence
from pipeline.metrics import MetricSeries


def sig(peak: int) -> np.ndarray:
    """A colour signature concentrated in one hue bin (a plainly coloured jacket)."""
    h = np.full(I.H_BINS * I.S_BINS, 0.002, np.float32)
    h[peak] = 1.0
    return h / h.sum()


A, B = sig(5), sig(30)


def test_one_person_is_one_identity():
    seg, switches = I.segment_identities([A] * 20)
    assert switches == 0 and set(seg) == {0}


def test_single_frame_glitch_is_not_a_switch():
    seg, switches = I.segment_identities([A] * 10 + [B] + [A] * 10)
    assert switches == 0 and set(seg) == {0}


def test_hop_to_someone_else_and_back_reuses_the_identity():
    seg, switches = I.segment_identities([A] * 10 + [B] * 8 + [A] * 10)
    assert switches == 2
    assert set(seg) == {0, 1}                       # two people, not three
    assert seg[:10] == [0] * 10 and seg[10:18] == [1] * 8 and seg[18:] == [0] * 10


def test_missing_signatures_are_skipped():
    seg, switches = I.segment_identities([A, None, A, A, None, A])
    assert switches == 0 and seg == [0, -1, 0, 0, -1, 0]


def _frame(i, appearance, detected=True):
    f = PoseFrame(index=i, t=i / 15, width=100, height=100, detected=detected,
                  xy=np.zeros((N_KP, 2)), vis=np.ones(N_KP) if detected else np.zeros(N_KP))
    f.appearance = appearance if detected else None
    return f


def test_keep_main_identity_drops_the_other_person():
    frames = [_frame(i, A) for i in range(12)] + [_frame(12 + i, B) for i in range(5)]
    seq, info = I.keep_main_identity(PoseSequence(frames=frames, fps=15, is_video=True))
    assert info.switches == 1 and info.kept_frames == 12 and info.dropped_frames == 5
    assert all(f.detected for f in seq.frames[:12]) and not any(f.detected for f in seq.frames[12:])


def test_keep_main_identity_ignores_short_noise_and_stills():
    frames = [_frame(0, B), _frame(1, B)] + [_frame(2 + i, A) for i in range(20)]   # 2-frame start = noise
    seq, info = I.keep_main_identity(PoseSequence(frames=frames, fps=15, is_video=True))
    assert info.switches == 0 and info.dropped_frames == 0
    stills = PoseSequence(frames=[_frame(0, A), _frame(1, B)], fps=0, is_video=False)
    assert I.keep_main_identity(stills)[0] is stills


def test_torso_signature_reads_the_jacket_colour():
    img = np.zeros((200, 200, 3), np.uint8)
    img[40:140, 60:140] = (0, 0, 255)               # red jacket (BGR)
    xy = np.zeros((N_KP, 2))
    from pipeline import keypoints as K
    xy[K.L_SHOULDER], xy[K.R_SHOULDER], xy[K.L_HIP], xy[K.R_HIP] = (130, 50), (70, 50), (125, 130), (75, 130)
    s = I.torso_signature(img, xy, np.ones(N_KP))
    assert s is not None and s.sum() == pytest.approx(1.0, abs=1e-5)
    assert int(np.argmax(s)) // I.S_BINS == 0       # hue bin 0 = red
    vis = np.ones(N_KP); vis[K.L_HIP] = 0.1
    assert I.torso_signature(img, xy, vis) is None  # torso not fully visible


# ---------------------------------------------------------------- seated / not skiing
def _ms(ratios, view="frontal", is_video=True):
    n = len(ratios)
    ms = MetricSeries(t=np.arange(n) / 15.0, fps=15.0, is_video=is_video, view=view)
    for name in M.SERIES_NAMES:
        ms.values[name] = np.full(n, np.nan)
        ms.conf[name] = np.zeros(n)
    ms.values["thigh_shin_2d"] = np.asarray(ratios, float)
    ms.conf["thigh_shin_2d"] = np.ones(n)
    return ms


def test_seated_reason_flags_foreshortened_thighs_from_the_front():
    assert M.seated_reason(_ms([0.55] * 30)) is not None                     # chairlift-like
    assert M.seated_reason(_ms([0.70] * 30)) is None                         # deep dynamic skiing
    assert M.seated_reason(_ms([0.55] * 30, view="side")) is None            # side view: thighs not foreshortened
    assert M.seated_reason(_ms([0.55] * 5)) is None                          # too few frames to judge
    assert M.seated_reason(_ms([0.55] * 30, is_video=False)) is None         # stills are not checked
