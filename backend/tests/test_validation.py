"""Segmentation, smoothing and the validation engine on scripted runs with known ground truth."""
import numpy as np
import pytest
from pydantic import ValidationError

from pipeline import keypoints as K
from pipeline.assessment import CATALOG, CATALOG_BY_ID, Assessment
from pipeline.keypoints import PoseFrame, PoseSequence
from pipeline.runner import analyze_sequence
from pipeline.segmentation import segment_turns
from pipeline.smoothing import fill_gaps, lowpass, smooth_sequence
from pipeline.synthetic import RunSpec, SkierParams, make_frame, run_sequence
from pipeline.validation import MIN_CONFIDENCE, Measurement, decide, eval_counter, eval_separation, summarize, validate


def assess(seq, ratings: dict, view="auto"):
    a = Assessment(camera_view=view, items=[{"item_id": k, "rating": v} for k, v in ratings.items()])
    _, ms, ctx, _ = analyze_sequence(seq, a)
    return {r["item_id"]: r for r in validate(a, ctx)}, ctx


# --------------------------------------------------------------- catalog/schema
def test_catalog_is_consistent():
    for it in CATALOG:
        assert len(it.bounds) == len(it.options) - 1
        assert list(it.bounds) == sorted(it.bounds)
        assert it.base_uncertainty > 0 and 0 < it.conf_cap <= 1
        # every middle band must be wider than 2x the uncertainty, otherwise it could never be confirmed
        for lo, hi in zip(it.bounds, it.bounds[1:]):
            assert hi - lo > 2 * it.base_uncertainty, it.id


def test_category_for_and_range():
    it = CATALOG_BY_ID["edge_angle"]
    assert it.category_for(5).id == "low" and it.category_for(20).id == "moderate" and it.category_for(55).id == "high"
    assert it.range_for("moderate") == (20.0, 40.0)


def test_schema_rejects_unknown_item_and_rating_and_duplicates():
    with pytest.raises(ValidationError):
        Assessment(items=[{"item_id": "nope", "rating": "x"}])
    with pytest.raises(ValidationError):
        Assessment(items=[{"item_id": "edge_angle", "rating": "gigantic"}])
    with pytest.raises(ValidationError):
        Assessment(items=[{"item_id": "edge_angle", "rating": "low"}, {"item_id": "edge_angle", "rating": "high"}])
    with pytest.raises(ValidationError):
        Assessment(items=[])


# ------------------------------------------------------------ smoothing
def test_fill_gaps_only_short_interior_gaps():
    x = np.array([0, 1, np.nan, 3, np.nan, np.nan, np.nan, 7, np.nan], float)
    y, filled = fill_gaps(x, max_gap=2)
    assert y[2] == pytest.approx(2.0) and filled[2]
    assert np.isnan(y[4:7]).all() and np.isnan(y[8])


def test_lowpass_removes_jitter_keeps_signal():
    fps = 30.0
    t = np.arange(0, 6, 1 / fps)
    clean = 30 * np.sin(2 * np.pi * 0.5 * t)
    noisy = clean + np.random.default_rng(1).normal(0, 3, len(t))
    out = lowpass(noisy, fps, 6.0)
    assert np.std(out - clean) < 0.55 * np.std(noisy - clean)
    assert np.std(out - clean) < 2.0              # noise sd was 3.0


def test_smoothing_interpolated_frames_are_not_trusted():
    seq = run_sequence(RunSpec(duration_s=3))
    for i in (20, 21):                                   # drop two frames
        seq.frames[i] = PoseFrame(index=i, t=seq.frames[i].t, width=960, height=720)
    out, stats = smooth_sequence(seq)
    assert stats["joint_samples_interpolated"] > 0
    assert np.isfinite(out.frames[20].xy[K.L_HIP]).all()          # filled for continuity
    assert out.frames[20].vis[K.L_HIP] < 0.5                      # ...but below the trust gate
    assert out.frames[10].vis[K.L_HIP] > 0.9


def test_smoothing_rejects_identity_jump():
    seq = run_sequence(RunSpec(duration_s=3))
    seq.frames[30].xy = seq.frames[30].xy + np.array([600.0, 0.0])      # one frame locks onto someone else
    out, stats = smooth_sequence(seq)
    assert stats["jump_frames_rejected"] == 1
    assert abs(out.frames[30].xy[K.L_HIP, 0] - out.frames[29].xy[K.L_HIP, 0]) < 30


# ---------------------------------------------------------- segmentation
def test_segmentation_counts_and_directions():
    spec = RunSpec(duration_s=8, turn_period_s=2, peak_inclination_deg=30, heading_deg=180)
    res, ctx = assess(run_sequence(spec), {"edge_angle": "moderate"})
    assert len(ctx.turns) == 8
    assert [t.direction for t in ctx.turns][:4] == ["right", "left", "right", "left"]   # skier's own left/right
    assert all(t.direction_frame == "skier" for t in ctx.turns)
    for t in ctx.turns:
        assert abs(t.peak_deg) == pytest.approx(30.0, abs=1.0)
        assert t.duration == pytest.approx(1.0, abs=0.12)


def test_segmentation_same_directions_from_behind():
    spec = RunSpec(duration_s=4, heading_deg=0)
    _, ctx = assess(run_sequence(spec), {"edge_angle": "moderate"})
    assert [t.direction for t in ctx.turns][:2] == ["right", "left"]


def test_segmentation_ignores_jitter_around_neutral():
    t = np.arange(0, 5, 1 / 30)
    x = np.random.default_rng(0).normal(0, 1.5, len(t))
    turns, _ = segment_turns(t, x, np.ones(len(t), bool), 30.0, 1.0)
    assert turns == []


# -------------------------------------------------------------- verdicts
GOOD = dict(stance_width="functional", stance_height="athletic", vertical_movement="active", edge_angle="moderate",
            angulation="moderate", turn_shape="round", turn_symmetry="symmetric", pole_plant="on_time",
            counter="countered")


def spec_good(**kw):
    base = dict(duration_s=8, peak_inclination_deg=30, angulation_deg=14, knee_min_deg=118, knee_max_deg=166,
                counter_deg=30, stance_ratio=1.1, heading_deg=180)
    base.update(kw)
    return RunSpec(**base)


def test_correct_assessment_agrees_everywhere_measurable():
    res, _ = assess(run_sequence(spec_good(), noise_px=1.0), GOOD)
    for k in ("stance_width", "stance_height", "vertical_movement", "edge_angle", "angulation", "turn_shape",
              "turn_symmetry", "pole_plant", "counter"):
        assert res[k]["verdict"] == "agree", (k, res[k]["reason"])
        assert res[k]["confidence"] >= MIN_CONFIDENCE
        assert res[k]["evidence"], k
    assert res["edge_angle"]["measured"]["value"] == pytest.approx(30, abs=2)
    assert res["edge_angle"]["measured"]["n_turns"] == 8


def test_separation_magnitude():
    res, _ = assess(run_sequence(spec_good(counter_deg=22), noise_px=1.0), {"separation": "moderate"})
    r = res["separation"]
    assert r["verdict"] == "agree" and r["measured"]["value"] == pytest.approx(22, abs=2)
    assert r["confidence"] <= 0.6                    # monocular-3D cap
    res, _ = assess(run_sequence(spec_good(counter_deg=0)), {"separation": "strong"})
    assert res["separation"]["verdict"] == "disagree"


def test_counter_is_judged_on_the_finish_phase():
    # Real skiers keep the upper body facing the fall line: it faces the inside of the turn before the fall
    # line and the outside after it, so a whole-turn median cancels to ~0 ("square"). Only the second half
    # of each turn shows the counter.
    res, ctx = assess(run_sequence(spec_good(stable_upper_body=True, counter_deg=40), noise_px=1.0),
                      {"counter": "countered"})
    whole_turn = ctx.ms.values["counter"][ctx.ms.valid("counter")]
    assert abs(float(np.median(whole_turn))) < 5                 # what the old whole-turn median reported
    r = res["counter"]
    assert r["verdict"] == "agree", r["reason"]
    assert r["measured"]["value"] > 15
    # the mirror image (shoulders lead into the turn in its second half) reads as rotated
    res, _ = assess(run_sequence(spec_good(stable_upper_body=True, counter_deg=-40), noise_px=1.0),
                    {"counter": "rotated"})
    assert res["counter"]["verdict"] == "agree", res["counter"]["reason"]


def test_counter_on_video_needs_turns():
    a = Assessment(items=[{"item_id": "counter", "rating": "countered"}])
    _, _, ctx, _ = analyze_sequence(run_sequence(spec_good()), a)
    ctx.turns = []
    m = eval_counter(ctx, CATALOG_BY_ID["counter"])
    assert m.value is None and "No turns" in m.unavailable


def test_separation_evidence_is_a_typical_frame_not_the_extreme():
    a = Assessment(items=[{"item_id": "separation", "rating": "moderate"}])
    _, _, ctx, _ = analyze_sequence(run_sequence(spec_good(counter_deg=22)), a)
    valid = np.flatnonzero(ctx.ms.valid("separation"))
    outlier = int(valid[len(valid) // 2])
    ctx.ms.values["separation"][outlier] = 95.0                 # one bad-pose frame, still under the 110 ceiling
    m = eval_separation(ctx, CATALOG_BY_ID["separation"])
    frame, caption = m.evidence[0]
    assert frame != outlier and "shoulders vs feet" in caption
    assert abs(abs(ctx.ms.values["separation"][frame]) - m.value) < 3


def test_broken_ffmpeg_counts_as_missing(tmp_path, monkeypatch):
    # e.g. Homebrew upgraded a library under ffmpeg: the binary is on PATH but aborts at start-up
    from pipeline import synthetic
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\nexit 134\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert synthetic.ffmpeg_path() is None
    out = synthetic.write_video([np.zeros((32, 32, 3), np.uint8)] * 3, str(tmp_path / "clip.mp4"), 10.0)
    assert (tmp_path / "clip.mp4").stat().st_size > 0 and out.endswith("clip.mp4")


def test_wrong_assessment_disagrees():
    wrong = dict(stance_width="narrow", stance_height="tall", vertical_movement="static", edge_angle="high",
                 angulation="banked", turn_shape="abrupt", turn_symmetry="left_stronger", pole_plant="none",
                 counter="rotated")
    res, _ = assess(run_sequence(spec_good(), noise_px=1.0), wrong)
    for k, r in res.items():
        assert r["verdict"] == "disagree", (k, r["reason"])


def test_borderline_value_is_inconclusive_not_a_verdict():
    # peak edge 21 deg is 1 deg from the low/moderate threshold (20) with +/-4 deg uncertainty
    res, _ = assess(run_sequence(spec_good(peak_inclination_deg=21)), {"edge_angle": "moderate"})
    r = res["edge_angle"]
    assert r["verdict"] == "inconclusive" and "Borderline" in r["reason"]
    assert r["measured"]["value"] == pytest.approx(21, abs=1.5)      # the value is still reported
    res, _ = assess(run_sequence(spec_good(peak_inclination_deg=21)), {"edge_angle": "low"})
    assert res["edge_angle"]["verdict"] == "inconclusive"


def test_low_confidence_pose_is_inconclusive():
    seq = run_sequence(spec_good(), vis=0.35)                # every landmark below the 0.5 trust gate
    res, _ = assess(seq, GOOD, view="frontal")
    for k, r in res.items():
        assert r["verdict"] == "inconclusive", k
        assert r["measured"] is None
    assert "confidence too low" in res["edge_angle"]["reason"].lower()


def test_no_skier_detected_is_inconclusive():
    frames = [PoseFrame(index=i, t=i / 15, width=640, height=480) for i in range(60)]
    res, _ = assess(PoseSequence(frames=frames, fps=15, is_video=True), GOOD)
    assert all(r["verdict"] == "inconclusive" for r in res.values())


def test_partial_low_confidence_uses_only_confident_frames():
    seq = run_sequence(spec_good())
    for f in seq.frames[::2]:
        f.vis[:] = 0.2
    res, _ = assess(seq, {"stance_width": "functional"}, view="frontal")
    assert res["stance_width"]["verdict"] == "agree"
    assert res["stance_width"]["measured"]["n_frames"] <= len(seq.frames) // 2 + 1


def test_view_requirements():
    side = run_sequence(spec_good(heading_deg=90, fore_aft_deg=-20, base=SkierParams(torso_forward_deg=5)))  # hips well behind the feet
    res, _ = assess(side, {"fore_aft": "aft", "edge_angle": "moderate", "turn_shape": "round"})
    assert res["fore_aft"]["verdict"] == "agree"
    assert res["fore_aft"]["measured"]["value"] < -4
    assert res["edge_angle"]["verdict"] == "inconclusive" and "front or back" in res["edge_angle"]["reason"]
    assert res["turn_shape"]["verdict"] == "inconclusive"
    front, _ = assess(run_sequence(spec_good()), {"fore_aft": "centered"})
    assert front["fore_aft"]["verdict"] == "inconclusive" and "side view" in front["fore_aft"]["reason"]


def test_oblique_view_gives_no_verdict_on_plane_dependent_items():
    seq = run_sequence(spec_good(heading_deg=130))
    res, ctx = assess(seq, {"edge_angle": "moderate", "angulation": "moderate", "fore_aft": "centered", "stance_height": "athletic"})
    assert ctx.ms.view == "oblique"
    for k in ("edge_angle", "angulation", "fore_aft"):
        assert res[k]["verdict"] == "inconclusive" and "oblique" in res[k]["reason"]
    assert res["stance_height"]["verdict"] == "agree"        # 3D joint angle does not depend on the view


def test_fore_aft_disagree_when_clearly_forward():
    side = run_sequence(RunSpec(heading_deg=90, fore_aft_deg=24, peak_inclination_deg=0, base=SkierParams(torso_forward_deg=35)))
    res, _ = assess(side, {"fore_aft": "aft"})
    assert res["fore_aft"]["verdict"] == "disagree" and res["fore_aft"]["measured"]["category"] == "forward"


def test_2d_only_estimator_cannot_rule_on_rotation_or_front_view_knee_angle():
    seq = run_sequence(spec_good(), with_world=False)
    res, _ = assess(seq, {"separation": "moderate", "counter": "countered", "stance_height": "athletic", "edge_angle": "moderate"})
    assert res["separation"]["verdict"] == "inconclusive" and "3D" in res["separation"]["reason"]
    assert res["counter"]["verdict"] == "inconclusive"
    assert res["stance_height"]["verdict"] == "inconclusive" and "foreshortens" in res["stance_height"]["reason"]
    assert res["stance_height"]["measured"] is None         # a biased 2D angle must not be reported
    assert res["edge_angle"]["verdict"] == "agree"          # frontal 2D metric is unaffected


def test_asymmetry_detected_in_skier_frame():
    res, _ = assess(run_sequence(spec_good(right_turn_scale=0.55)), {"turn_symmetry": "left_stronger"})
    assert res["turn_symmetry"]["verdict"] == "agree"
    assert res["turn_symmetry"]["measured"]["value"] < -40
    res, _ = assess(run_sequence(spec_good(right_turn_scale=0.55, heading_deg=0)), {"turn_symmetry": "right_stronger"})
    assert res["turn_symmetry"]["verdict"] == "disagree"


def test_abrupt_turns_detected():
    res, _ = assess(run_sequence(spec_good(abrupt=True)), {"turn_shape": "abrupt"})
    assert res["turn_shape"]["verdict"] == "agree" and res["turn_shape"]["measured"]["value"] < 0.11


def test_banked_and_rotated_detected():
    res, _ = assess(run_sequence(spec_good(angulation_deg=0, counter_deg=-30)), {"angulation": "banked", "counter": "rotated"})
    assert res["angulation"]["verdict"] == "agree"
    assert res["counter"]["verdict"] == "agree" and res["counter"]["measured"]["value"] < -10


@pytest.mark.parametrize("offset,expected", [(-0.3, "early"), (0.0, "on_time"), (0.3, "late")])
def test_pole_plant_timing(offset, expected):
    res, _ = assess(run_sequence(spec_good(pole_plant_offset=offset)), {"pole_plant": expected})
    r = res["pole_plant"]
    assert r["verdict"] == "agree", r["reason"]
    assert r["measured"]["value"] == pytest.approx(offset, abs=0.06)
    assert r["experimental"] and r["confidence"] <= 0.55


def test_no_pole_plant():
    res, _ = assess(run_sequence(spec_good(pole_plant_offset=None)), {"pole_plant": "none"})
    assert res["pole_plant"]["verdict"] == "agree" and res["pole_plant"]["measured"]["category"] == "none"
    res, _ = assess(run_sequence(spec_good(pole_plant_offset=None)), {"pole_plant": "on_time"})
    assert res["pole_plant"]["verdict"] == "disagree"


def test_too_short_clip_cannot_time_poles_or_shape():
    res, _ = assess(run_sequence(spec_good(duration_s=1.2)), {"pole_plant": "on_time", "turn_shape": "round", "vertical_movement": "active"})
    assert all(r["verdict"] == "inconclusive" for r in res.values())


# ----------------------------------------------------------------- stills
def stills(params):
    return PoseSequence(frames=[make_frame(p, i) for i, p in enumerate(params)], fps=0.0, is_video=False)


def test_stills_measure_static_items_and_refuse_dynamic_ones():
    seq = stills([SkierParams(heading_deg=180, inclination_deg=34, angulation_deg=14, knee_angle_deg=130, stance_ratio=1.0),
                  SkierParams(heading_deg=180, inclination_deg=-31, angulation_deg=12, knee_angle_deg=136, stance_ratio=1.1),
                  SkierParams(heading_deg=180, inclination_deg=4, knee_angle_deg=150, stance_ratio=1.0)])
    res, ctx = assess(seq, dict(edge_angle="moderate", angulation="moderate", stance_width="functional", stance_height="athletic",
                                vertical_movement="active", turn_shape="round", turn_symmetry="symmetric", pole_plant="on_time"))
    assert ctx.turns == []
    for k in ("edge_angle", "angulation", "stance_width", "stance_height"):
        assert res[k]["verdict"] == "agree", (k, res[k]["reason"])
    assert res["edge_angle"]["measured"]["value"] == pytest.approx(34, abs=0.5)
    assert any("Stills" in n for n in res["edge_angle"]["notes"])
    for k in ("vertical_movement", "turn_shape", "turn_symmetry", "pole_plant"):
        assert res[k]["verdict"] == "inconclusive" and "Needs video" in res[k]["reason"]


def test_single_still_works_with_reduced_confidence():
    one = stills([SkierParams(heading_deg=0, inclination_deg=50, angulation_deg=20)])
    three = stills([SkierParams(heading_deg=0, inclination_deg=50, angulation_deg=20)] * 4)
    r1 = assess(one, {"edge_angle": "high"})[0]["edge_angle"]
    r4 = assess(three, {"edge_angle": "high"})[0]["edge_angle"]
    assert r1["verdict"] == "agree" and r1["confidence"] < r4["confidence"]


def test_still_without_lean_cannot_judge_angulation():
    res, _ = assess(stills([SkierParams(heading_deg=180, inclination_deg=3)]), {"angulation": "banked"})
    assert res["angulation"]["verdict"] == "inconclusive" and "nothing to angulate" in res["angulation"]["reason"]


# ------------------------------------------------------------ decide()
def test_decide_confidence_floor_forces_inconclusive():
    item = CATALOG_BY_ID["separation"]                       # conf cap 0.6
    m = Measurement(value=60.0, n_frames=3, pose_conf=0.55, sample_factor=0.6, extra_factor=0.8)
    r = decide(item, "strong", m)
    assert r["verdict"] == "inconclusive" and "below" in r["reason"] and r["confidence"] < MIN_CONFIDENCE
    assert r["measured"]["value"] == 60.0


def test_decide_margins():
    item = CATALOG_BY_ID["edge_angle"]                       # bounds 20/40, u = 4
    mk = lambda v: Measurement(value=v, n_frames=50, pose_conf=0.9)
    assert decide(item, "moderate", mk(30))["verdict"] == "agree"
    assert decide(item, "moderate", mk(23))["verdict"] == "inconclusive"
    assert decide(item, "moderate", mk(43))["verdict"] == "inconclusive"
    assert decide(item, "moderate", mk(45))["verdict"] == "disagree"
    assert decide(item, "high", mk(30))["verdict"] == "disagree"
    assert decide(item, "moderate", mk(30))["confidence"] > decide(item, "moderate", mk(25))["confidence"]


def test_summary_counts():
    s = summarize([{"verdict": "agree"}, {"verdict": "agree"}, {"verdict": "disagree"}, {"verdict": "inconclusive"}])
    assert s == {"agree": 2, "disagree": 1, "inconclusive": 1, "total": 4, "decided": 3, "agreement_rate": 0.667}
