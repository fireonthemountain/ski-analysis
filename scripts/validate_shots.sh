#!/bin/bash
# Validate one section of an EDITED video (cuts between camera shots): cut the section out,
# split it at the camera cuts, and run the validation CLI on every shot long enough to use.
#
#   scripts/validate_shots.sh VIDEO START END ASSESSMENT.json OUTDIR [MIN_SHOT_SECONDS]
#
# START / END: seconds or [h:]mm:ss in the source video. MIN_SHOT_SECONDS defaults to 3.
# Writes OUTDIR/shot_NN.mp4, OUTDIR/shot_NN/ (result.json, frames/, annotated.mp4), OUTDIR/shot_NN.txt
# (CLI output), OUTDIR/shots.tsv (where each shot is in the source) and OUTDIR/summary.md (one row per shot).
# Needs ffmpeg (brew install ffmpeg) and backend/venv.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ $# -lt 5 ]; then sed -n '2,10p' "$0"; exit 1; fi
command -v ffmpeg >/dev/null 2>&1 || { echo "Need ffmpeg: brew install ffmpeg"; exit 1; }
ffmpeg -hide_banner -version >/dev/null 2>&1 || { echo "ffmpeg is installed but will not start: brew upgrade ffmpeg (or brew reinstall ffmpeg)"; exit 1; }
[ -x "$ROOT/backend/venv/bin/python" ] || { echo "Need backend/venv (run scripts/run_dev.sh once)"; exit 1; }

abspath() { echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; }
secs() { awk -F: '{s=0; for (i=1; i<=NF; i++) s=s*60+$i; print s}' <<<"$1"; }
mmss() { awk -v t="$1" 'BEGIN{m=int(t/60); printf "%d:%04.1f", m, t-60*m}'; }
calc() { awk "BEGIN{print $1}"; }

VIDEO="$(abspath "$1")"
ASSESS="$(abspath "$4")"
S="$(secs "$2")"; E="$(secs "$3")"; DUR="$(calc "$E - $S")"
MIN="${6:-3}"
mkdir -p "$5"; OUT="$(cd "$5" && pwd)"
[ -f "$VIDEO" ] || { echo "No such video: $VIDEO"; exit 1; }
[ -f "$ASSESS" ] || { echo "No such assessment: $ASSESS"; exit 1; }

echo "Cutting $(mmss "$S")-$(mmss "$E") (${DUR}s) out of $(basename "$VIDEO") ..."
SECTION="$OUT/section.mp4"
ffmpeg -nostdin -loglevel error -y -ss "$S" -i "$VIDEO" -t "$DUR" -an \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$SECTION"

echo "Finding camera cuts ..."
CUTS="$(ffmpeg -nostdin -hide_banner -i "$SECTION" -vf "select='gt(scene,0.30)',showinfo" -an -f null - 2>&1 \
  | grep -o 'pts_time:[0-9.]*' | cut -d: -f2 || true)"
BOUNDS=(0 $CUTS "$DUR")
echo "  $(( ${#BOUNDS[@]} - 1 )) shots before dropping ones shorter than ${MIN}s"

: > "$OUT/shots.tsv"
n=0
for (( i=0; i<${#BOUNDS[@]}-1; i++ )); do
  a="${BOUNDS[$i]}"; b="${BOUNDS[$((i+1))]}"
  len="$(calc "$b - $a")"
  awk -v l="$len" -v m="$MIN" 'BEGIN{exit !(l >= m)}' || continue
  n=$((n+1)); tag="$(printf 'shot_%02d' "$n")"
  # drop 0.2 s at each end so a dissolve between shots does not leak in
  ffmpeg -nostdin -loglevel error -y -ss "$(calc "$a + 0.2")" -i "$SECTION" -t "$(calc "$len - 0.4")" -an \
    -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$OUT/$tag.mp4"
  printf '%s\t%s\t%s\n' "$tag" "$(mmss "$(calc "$S + $a")")" "$(mmss "$(calc "$S + $b")")" >> "$OUT/shots.tsv"
  echo
  echo "=== $tag  source $(mmss "$(calc "$S + $a")")-$(mmss "$(calc "$S + $b")")  (${len}s)"
  ( cd "$ROOT/backend" && ./venv/bin/python -m pipeline.cli --assessment "$ASSESS" "$OUT/$tag.mp4" --out "$OUT/$tag" ) \
    2>&1 | tee "$OUT/$tag.txt" || echo "  !! $tag failed - see $OUT/$tag.txt"
done
[ "$n" -gt 0 ] || { echo "No shot was at least ${MIN}s long."; exit 1; }

echo
"$ROOT/backend/venv/bin/python" - "$OUT" <<'EOF'
import csv, glob, json, os, sys
out = sys.argv[1]
where = {}
for row in csv.reader(open(os.path.join(out, "shots.tsv")), delimiter="\t"):
    if row:
        where[row[0]] = f"{row[1]}-{row[2]}"
def fmt(v):
    return "-" if v is None else (f"{v:.2f}" if abs(v) < 10 else f"{v:.0f}")
runs, items = [], []
for path in sorted(glob.glob(os.path.join(out, "shot_*", "result.json"))):
    r = json.load(open(path))
    runs.append((os.path.basename(os.path.dirname(path)), r))
    for x in r["results"]:
        if x["item_id"] not in items:
            items.append(x["item_id"])
hdr = ["shot", "source", "frames", "detected", "confident", "s/frame", "view", "turns"] + items
lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
for tag, r in runs:
    p = r["pose"]; n = max(1, p["frames"])
    row = [tag, where.get(tag, "?"), str(p["frames"]), f"{p['frames_detected'] / n:.0%}", f"{p['frames_confident'] / n:.0%}",
           f"{r['processing_seconds'] / n:.2f}", f"{r['view']['view']}/{r['view']['facing'] or '-'}", str(len(r["turns"]))]
    by = {x["item_id"]: x for x in r["results"]}
    for k in items:
        x = by.get(k)
        m = (x or {}).get("measured") or {}
        row.append("-" if not x else f"{fmt(m.get('value'))} ({x['verdict'][:4]})")
    lines.append("| " + " | ".join(row) + " |")
def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + float(s)
long = []
for tag, span in where.items():
    a_, b_ = span.split("-")
    if secs(b_) - secs(a_) > 40:
        long.append(f"{tag} ({secs(b_) - secs(a_):.0f} s)")
if long:
    lines.append("")
    lines.append("Shots longer than 40 s probably contain several camera shots that the cut detector missed "
                 "(flat light hides cuts): " + ", ".join(long) + ". Check their annotated.mp4; the pipeline keeps only the "
                 "longest-tracked person in each, and says so in its warnings.")
text = "\n".join(lines)
print(text)
with open(os.path.join(out, "summary.md"), "w") as fh:
    fh.write(text + "\n")
print(f"\nWritten: {os.path.join(out, 'summary.md')}  (watch each shot_NN/annotated.mp4 before trusting a row)")
EOF
