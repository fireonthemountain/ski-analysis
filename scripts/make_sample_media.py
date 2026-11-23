#!/usr/bin/env python3
"""Generate the synthetic sample media in examples/synthetic/ (a rendered stick-figure skier).

No real people: the figure is drawn from a parametric skeleton with known angles, so it doubles
as ground truth. Use it to try the app end to end:

    backend/venv/bin/python scripts/make_sample_media.py
    POSE_ESTIMATOR=marker scripts/run_dev.sh        # the marker estimator reads the stick figure

MediaPipe (the real estimator) does not recognise a stick figure as a person - that is expected.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from pipeline.synthetic import RunSpec, SkierParams, write_sample_clip, write_sample_stills  # noqa: E402

out = os.path.join(ROOT, "examples", "synthetic")
os.makedirs(out, exist_ok=True)
spec = RunSpec(duration_s=8, fps=30, peak_inclination_deg=30, angulation_deg=14, knee_min_deg=118, knee_max_deg=166,
               stance_ratio=1.1, heading_deg=180)
print(write_sample_clip(os.path.join(out, "synthetic_run_front.mp4"), spec))
for p in write_sample_stills(out, [
    SkierParams(heading_deg=180, inclination_deg=33, angulation_deg=14, knee_angle_deg=130, stance_ratio=1.1),
    SkierParams(heading_deg=180, inclination_deg=-30, angulation_deg=12, knee_angle_deg=135, stance_ratio=1.1),
    SkierParams(heading_deg=180, inclination_deg=5, knee_angle_deg=150, stance_ratio=1.0),
]):
    print(p)
truth = {"edge_angle": "moderate (30 deg peak)", "angulation": "moderate (14 deg at apex)", "stance_width": "functional (1.1x)",
         "turn_shape": "round", "turn_symmetry": "symmetric", "pole_plant": "on_time", "turns": 8}
with open(os.path.join(out, "ground_truth.json"), "w") as fh:
    json.dump(truth, fh, indent=1)
