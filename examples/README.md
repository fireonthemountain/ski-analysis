# Examples

| File | What |
|---|---|
| `assessment.example.json` | A complete assessment file for the CLI (`--assessment`). Copy it, set each rating to what *you* saw before looking at any results, and remove items you didn't observe. `python -m pipeline.cli --list-items` lists every item and option. |
| `synthetic/` | Rendered stick-figure media with known geometry: `synthetic_run_front.mp4` (front view, linked turns), `still_01-03.png`, and `ground_truth.json` (the angles used to draw them). Regenerate with `scripts/make_sample_media.py`. Use with `POSE_ESTIMATOR=marker`; MediaPipe does not treat the figure as a person. |
| `sample-test-results.csv` | Output of the retired single-photo scoring version (kept for history; not produced by the current app). |

How to run and read a validation: [TESTING.md](../TESTING.md). What the numbers mean: [docs/PIPELINE.md](../docs/PIPELINE.md).
