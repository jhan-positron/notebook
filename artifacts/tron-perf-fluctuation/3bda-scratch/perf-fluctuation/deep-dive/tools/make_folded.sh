#!/usr/bin/env bash
# Run ON delphi-3bda. Convert a draw's perf.data into a folded-stack file
# (for flame graphs and symbol-class attribution) plus a per-symbol report.
#
# Usage: make_folded.sh <draw-dir> [<draw-dir> ...]
# Needs: FlameGraph checkout at /scratch/jhan/perf-fluctuation/deep-dive/tools/FlameGraph
set -eu
FG=/scratch/jhan/perf-fluctuation/deep-dive/tools/FlameGraph
for d in "$@"; do
  data=$d/perf.data
  [ -s "$data" ] || { echo "skip $d: no perf.data" >&2; continue; }
  # runtron threads only (comm filter happens in stackcollapse output; keep
  # everything here so interference from other tasks stays visible).
  sudo -n perf script -f -i "$data" --no-inline > "$d/perf.script" 2> "$d/perf.script.err"
  "$FG/stackcollapse-perf.pl" "$d/perf.script" > "$d/perf.folded"
  sudo -n perf report -f -i "$data" --stdio --no-children --percent-limit 0.2 \
    > "$d/perf-report-flat.txt" 2>/dev/null || echo "WARN perf report flat failed: $d" >&2
  sudo -n perf report -f -i "$data" --stdio --sort comm --percent-limit 0.1 \
    > "$d/perf-report-bycomm.txt" 2>/dev/null || echo "WARN perf report bycomm failed: $d" >&2
  echo "done $d"
done
