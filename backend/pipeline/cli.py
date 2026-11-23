"""Command-line runner:  python -m pipeline.cli --assessment my.json run.mp4
                         python -m pipeline.cli --assessment my.json shot1.jpg shot2.jpg
                         python -m pipeline.cli --list-items
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .assessment import CATALOG, Assessment
from .pose import get_estimator
from .runner import run_validation

MARK = {"agree": "AGREE       ", "disagree": "DISAGREE    ", "inconclusive": "INCONCLUSIVE"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a ski assessment against a video or screenshots.")
    ap.add_argument("media", nargs="*", help="one video, or one or more images")
    ap.add_argument("--assessment", help="assessment JSON file (see examples/assessment.example.json)")
    ap.add_argument("--out", default="validation-output", help="output folder (result.json, frames/, annotated.mp4)")
    ap.add_argument("--estimator", default=None, help="mediapipe (default) or marker (synthetic stick figure only)")
    ap.add_argument("--fps", type=float, default=15.0, help="frames per second to analyse")
    ap.add_argument("--max-seconds", type=float, default=90.0)
    ap.add_argument("--list-items", action="store_true", help="print the assessable items and their ratings")
    a = ap.parse_args(argv)

    if a.list_items:
        for it in CATALOG:
            needs = ", ".join(x for x in ("video" if it.needs_video else "", f"{it.needs_view} view" if it.needs_view else "") if x)
            print(f"{it.id:18} {it.label}  [{needs or 'video or stills, any view'}]")
            for o in it.all_options():
                print(f"{'':20}- {o.id}: {o.label}")
        return 0
    if not a.media or not a.assessment:
        ap.error("give --assessment FILE and at least one media file")
    with open(a.assessment) as fh:
        assessment = Assessment(**json.load(fh))
    est = get_estimator(a.estimator)
    last = [""]

    def progress(frac, msg):
        if msg != last[0] and sys.stderr.isatty():
            print(f"\r{frac * 100:5.1f}%  {msg:60}", end="", file=sys.stderr)
        last[0] = msg

    res = run_validation(assessment, a.media, a.out, estimator=est, progress=progress, target_fps=a.fps, max_seconds=a.max_seconds)
    est.close()
    print(file=sys.stderr)
    p = res["pose"]
    print(f"{res['assessment']['run_label']}: {res['media']['kind']}, {p['frames']} frames, {p['frames_confident']} with a confident pose, "
          f"view={res['view']['view']}, turns={len(res['turns'])}")
    for w in res["warnings"]:
        print(f"  WARNING: {w}")
    print()
    for r in res["results"]:
        m = r["measured"]
        val = "not measured" if not m else (m["category_label"] if m["value"] is None else f"{m['value']:.2f} +/- {m['uncertainty']:.2f} {r['unit']}")
        print(f"{MARK[r['verdict']]} {r['label']:34} assessed: {r['assessed']['label']:26} measured: {val:28} conf {r['confidence']:.2f}")
        print(f"{'':13}{r['reason']}")
    s = res["summary"]
    print(f"\n{s['agree']} agree, {s['disagree']} disagree, {s['inconclusive']} inconclusive of {s['total']}.  Details: {os.path.abspath(a.out)}/result.json, frames/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
