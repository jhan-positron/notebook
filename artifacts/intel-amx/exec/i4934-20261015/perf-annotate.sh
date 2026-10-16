#!/usr/bin/env bash
# perf-annotate.sh <results dir> <perf data dir> <tag> [cpus]: perf annotate of the hottest user symbol whose short name
# holds "apply_page_range" in the run <tag> (runs ON delphi-3bda, pinned to idle cores at nice 19). The symbol name is
# taken from the run's .bysym.txt (the row with the largest share among the apply_page_range rows), with the trailing
# spaces removed: perf annotate -s needs the exact demangled name. Output: <results>/<tag>.annotate-apr.txt (the
# instruction listing with per-instruction sample percentages) and .annotate-apr.err.
set -u
RES=${1:?}; DATA=${2:?}; TAG=${3:?}; CPUS=${4:-80-95}
sym=$(grep '\[\.\]' "$RES/$TAG.bysym.txt" | grep 'apply_page_range' | sort -rn | head -1 | sed -e 's/^ *[0-9.]*% *\[\.\] //' -e 's/ *$//')
[ -n "$sym" ] || { echo "$TAG: no apply_page_range row"; exit 1; }
echo "$(date -u +%FT%TZ) $TAG: annotating '$(cut -c1-80 <<<"$sym")...' ($(wc -c <<<"$sym") chars)"
taskset -c "$CPUS" nice -n19 sudo -n perf annotate -f -i "$DATA/$TAG.data" --stdio -s "$sym" 2>"$RES/$TAG.annotate-apr.err" | head -20000 >"$RES/$TAG.annotate-apr.txt"
echo "$(date -u +%FT%TZ) $TAG: $(wc -l <"$RES/$TAG.annotate-apr.txt") lines, errors: $(head -c 200 "$RES/$TAG.annotate-apr.err" | tr '\n' ' ')"
