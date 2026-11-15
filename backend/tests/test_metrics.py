"""Unit tests: synthetic keypoints with known angles -> known metric values."""
import math

import numpy as np
import pytest

from pipeline import keypoints as K
from pipeline import metrics as M
from pipeline.keypoints import PoseFrame
from pipeline.synthetic import SkierParams, make_frame


def val(frame, name):
    return M.frame_metrics(frame)[name][0]


# ---------------------------------------------------------------- primitives
def test_joint_angle_known_values():
    assert M.joint_angle((1, 0), (0, 0), (0, 1)) == pytest.approx(90.0)
    assert M.joint_angle((0, -1), (0, 0), (0, 1)) == pytest.approx(180.0)
    assert M.joint_angle((1, 0, 0), (0, 0, 0), (math.cos(math.radians(60)), math.sin(math.radians(60)), 0)) == pytest.approx(60.0)


def test_joint_angle_degenerate_is_nan():
    assert math.isnan(M.joint_angle((0, 0), (0, 0), (1, 1)))


def test_tilt_from_vertical_sign_and_size():
    assert M.tilt_from_vertical((0, -1)) == pytest.approx(0.0)            # straight up (image y is down)
    assert M.tilt_from_vertical((1, -1)) == pytest.approx(45.0)           # leaning image-right
    assert M.tilt_from_vertical((-math.tan(math.radians(20)), -1)) == pytest.approx(-20.0)


def test_wrap_deg():
    assert M.wrap_deg(190) == pytest.approx(-170)
    assert M.wrap_deg(-190) == pytest.approx(170)


def test_axis_yaw_convention():
    assert M.axis_yaw(np.array([1.0, 0, 0])) == pytest.approx(0.0)        # skier's right = image right -> facing away
    assert abs(M.axis_yaw(np.array([-1.0, 0, 0]))) == pytest.approx(180.0)  # facing the camera
    assert M.axis_yaw(np.array([0, 0, -1.0])) == pytest.approx(90.0)      # facing image right


# ------------------------------------------------------------- frontal plane
@pytest.mark.parametrize("heading", [0.0, 180.0])
@pytest.mark.parametrize("incl", [-35.0, -10.0, 0.0, 15.0, 40.0])
def test_inclination_recovered_in_skier_frame(heading, incl):
    f = make_frame(SkierParams(heading_deg=heading, inclination_deg=incl))
    assert val(f, "lean_skier") == pytest.approx(incl, abs=0.01)
    # image sign flips with the view: back view keeps it, front view mirrors it
    assert val(f, "inclination") == pytest.approx(incl if heading == 0 else -incl, abs=0.01)
    assert val(f, "facing") == (1.0 if heading == 0 else -1.0)


@pytest.mark.parametrize("incl,ang", [(30.0, 0.0), (30.0, 12.0), (-30.0, 20.0), (20.0, -5.0)])
def test_angulation_recovered(incl, ang):
    f = make_frame(SkierParams(heading_deg=180, inclination_deg=incl, angulation_deg=ang))
    assert val(f, "angulation") == pytest.approx(ang, abs=0.01)


@pytest.mark.parametrize("incl", [-45.0, -20.0, 25.0, 50.0])
def test_edge_proxy_is_outside_shin_tilt_into_turn(incl):
    f = make_frame(SkierParams(heading_deg=0, inclination_deg=incl, stance_ratio=1.0, fore_aft_deg=0))
    assert val(f, "edge_proxy") == pytest.approx(abs(incl), abs=0.01)


@pytest.mark.parametrize("ratio", [0.4, 1.0, 1.8])
@pytest.mark.parametrize("incl", [0.0, 35.0])
def test_stance_width_ratio_2d_and_3d(ratio, incl):
    f = make_frame(SkierParams(heading_deg=180, stance_ratio=ratio, inclination_deg=incl))
    assert val(f, "stance_width_2d") == pytest.approx(ratio, abs=0.01)
    assert val(f, "stance_width_3d") == pytest.approx(ratio, abs=0.01)


def test_stance_width_3d_works_from_side_view():
    f = make_frame(SkierParams(heading_deg=90, stance_ratio=1.6))
    assert val(f, "stance_width_3d") == pytest.approx(1.6, abs=0.01)


# -------------------------------------------------------------- joint angles
@pytest.mark.parametrize("heading", [0.0, 90.0, 180.0, 45.0])
@pytest.mark.parametrize("knee", [95.0, 130.0, 165.0])
def test_knee_angle_3d_is_view_independent(heading, knee):
    f = make_frame(SkierParams(heading_deg=heading, knee_angle_deg=knee))
    m = M.frame_metrics(f)
    assert m["knee_left"][0] == pytest.approx(knee, abs=0.01)
    assert m["knee_right"][0] == pytest.approx(knee, abs=0.01)
    assert m["knee_mean"][0] == pytest.approx(knee, abs=0.01)


def test_knee_angle_2d_side_view_matches_but_front_view_foreshortens():
    side = make_frame(SkierParams(heading_deg=90, knee_angle_deg=120), with_world=False)
    front = make_frame(SkierParams(heading_deg=180, knee_angle_deg=120), with_world=False)
    assert val(side, "knee_mean") == pytest.approx(120.0, abs=0.01)
    assert val(front, "knee_mean") > 170.0          # the documented 2D limitation
    assert val(front, "angles_3d") == 0.0


def test_hip_angle_straight_and_folded():
    straight = make_frame(SkierParams(heading_deg=90, knee_angle_deg=179.9, fore_aft_deg=0, torso_forward_deg=0))
    assert val(straight, "hip_angle") == pytest.approx(180.0, abs=0.5)
    folded = make_frame(SkierParams(heading_deg=90, knee_angle_deg=179.9, fore_aft_deg=0, torso_forward_deg=60))
    assert val(folded, "hip_angle") == pytest.approx(120.0, abs=0.5)


# ------------------------------------------------------------------ fore/aft
@pytest.mark.parametrize("heading", [90.0, 270.0])
@pytest.mark.parametrize("lean", [-15.0, 0.0, 10.0, 20.0])
def test_fore_aft_straight_body_equals_lean(heading, lean):
    # straight legs with the torso on the same line: ankle->COM is exactly the lean angle
    f = make_frame(SkierParams(heading_deg=heading, knee_angle_deg=179.99, fore_aft_deg=lean, torso_forward_deg=lean))
    m = M.frame_metrics(f)
    assert m["fore_aft"][0] == pytest.approx(lean, abs=0.2)
    assert m["fore_aft_ref"][0] == 1.0             # boot-sole reference used


@pytest.mark.parametrize("slope", [-25.0, 15.0])
def test_fore_aft_is_slope_independent_with_sole_reference(slope):
    p = SkierParams(heading_deg=90, knee_angle_deg=179.99, fore_aft_deg=8, torso_forward_deg=8, slope_roll_deg=slope)
    assert val(make_frame(p), "fore_aft") == pytest.approx(8.0, abs=0.2)


def test_fore_aft_falls_back_to_vertical_without_feet():
    f = make_frame(SkierParams(heading_deg=90, knee_angle_deg=179.99, fore_aft_deg=8, torso_forward_deg=8))
    f.vis[K.FEET] = 0.1
    m = M.frame_metrics(f)
    assert m["fore_aft"][0] == pytest.approx(8.0, abs=0.2)
    assert m["fore_aft_ref"][0] == 0.0


# --------------------------------------------------------- rotation (3D yaw)
@pytest.mark.parametrize("heading", [0.0, 180.0, 60.0])
@pytest.mark.parametrize("yaw", [-30.0, 0.0, 20.0])
def test_separation_vs_feet_is_view_independent(heading, yaw):
    f = make_frame(SkierParams(heading_deg=heading, shoulder_yaw_deg=yaw, pelvis_yaw_deg=yaw / 2))
    m = M.frame_metrics(f)
    assert m["separation"][0] == pytest.approx(yaw, abs=0.05)             # + = turned to skier's right
    assert m["separation_pelvis"][0] == pytest.approx(yaw / 2, abs=0.6)
    assert m["separation_ref"][0] == 1.0


def test_separation_falls_back_to_pelvis_without_feet():
    f = make_frame(SkierParams(heading_deg=180, shoulder_yaw_deg=20, pelvis_yaw_deg=0))
    f.vis[K.FEET] = 0.0
    m = M.frame_metrics(f)
    assert m["separation"][0] == pytest.approx(20.0, abs=0.05)
    assert m["separation_ref"][0] == 0.0


@pytest.mark.parametrize("heading", [0.0, 180.0])
def test_counter_sign(heading):
    # right turn (leaning right) with shoulders turned LEFT = facing the outside = countered (+)
    f = make_frame(SkierParams(heading_deg=heading, inclination_deg=25, shoulder_yaw_deg=-18))
    assert val(f, "counter") == pytest.approx(18.0, abs=0.05)
    # left turn with shoulders turned further left = rotated into the turn (-)
    f = make_frame(SkierParams(heading_deg=heading, inclination_deg=-25, shoulder_yaw_deg=-18))
    assert val(f, "counter") == pytest.approx(-18.0, abs=0.05)


def test_counter_undefined_without_lean():
    f = make_frame(SkierParams(heading_deg=180, inclination_deg=2, shoulder_yaw_deg=-18))
    assert "counter" not in M.frame_metrics(f)


def test_no_3d_means_no_rotation_metrics():
    f = make_frame(SkierParams(heading_deg=180, shoulder_yaw_deg=20), with_world=False)
    m = M.frame_metrics(f)
    assert "separation" not in m and "stance_width_3d" not in m


# ------------------------------------------------------- confidence handling
def test_low_visibility_joints_produce_no_metric():
    f = make_frame(SkierParams(heading_deg=180, inclination_deg=20))
    f.vis[[K.L_ANKLE, K.R_ANKLE]] = 0.2
    m = M.frame_metrics(f)
    for name in ("inclination", "edge_proxy", "stance_width_2d", "knee_mean", "angulation"):
        assert name not in m
    assert "torso_tilt" in m                       # does not need the ankles


def test_undetected_frame_has_no_metrics():
    assert M.frame_metrics(PoseFrame(index=0, t=0, width=10, height=10)) == {}


def test_one_visible_side_is_enough_for_midpoints():
    f = make_frame(SkierParams(heading_deg=90, knee_angle_deg=179.99, fore_aft_deg=8, torso_forward_deg=8))
    f.vis[[K.L_SHOULDER, K.L_HIP, K.L_KNEE, K.L_ANKLE, K.L_HEEL, K.L_TOE]] = 0.0   # far side hidden
    assert val(f, "fore_aft") == pytest.approx(8.0, abs=0.3)


def test_view_classification():
    mk = lambda h: M.compute_series(__import__("pipeline.keypoints", fromlist=["PoseSequence"]).PoseSequence(
        frames=[make_frame(SkierParams(heading_deg=h))], fps=0, is_video=False))
    assert mk(180).view == "frontal" and mk(180).facing == "toward camera"
    assert mk(0).view == "frontal" and mk(0).facing == "away from camera"
    assert mk(90).view == "side"
    assert mk(50).view == "oblique"
