#!/usr/bin/env bash
# perf-report.sh <results dir> <perf data dir> [cpus]: (re)generate the perf reports of perf-fix.sh / perf2-fix.sh runs
# from their perf.data files (runs ON delphi-3bda). Why: the drivers chown the data file to jhan and then run perf report
# as root, which refuses a file owned by another user without --force, so their report, bysym, top and annotate files
# came out empty. Per data file: perf report by thread, binary and symbol; by symbol; the three hottest user symbols
# annotated. Pinned to CPUS (default 80-95: our half, outside the engines' app and device cores) at nice 19, so a
# running measurement is not disturbed. Files that already have a non-empty report are skipped.
set -u
RES=${1:?results dir}; DATA=${2:?perf data dir}; CPUS=${3:-80-95}
for data in "$DATA"/*.data; do
  tag=$(basename "$data" .data)
  [ -s "$RES/$tag.report.txt" ] && { echo "$tag: report exists"; continue; }
  taskset -c "$CPUS" nice -n19 sudo -n perf report -f -i "$data" --stdio --sort comm,dso,symbol --percent-limit 0.2 2>"$RES/$tag.report.err" >"$RES/$tag.report.txt"
  taskset -c "$CPUS" nice -n19 sudo -n perf report -f -i "$data" --stdio --sort symbol -F overhead,symbol --percent-limit 0.1 2>>"$RES/$tag.report.err" >"$RES/$tag.bysym.txt"
  grep -v '^#' "$RES/$tag.bysym.txt" | grep -v '^$' | grep '\[\.\]' | head -5 >"$RES/$tag.top.txt"
  k=0
  while IFS= read -r line; do
    sym=${line#*\] }
    k=$((k + 1)); [ $k -gt 3 ] && break
    taskset -c "$CPUS" nice -n19 sudo -n perf annotate -f -i "$data" --stdio -s "$sym" 2>>"$RES/$tag.report.err" | head -8000 >"$RES/$tag.annotate-$k.txt"
  done <"$RES/$tag.top.txt"
  echo "$(date -u +%FT%TZ) $tag: report $(wc -l <"$RES/$tag.report.txt") lines, bysym $(wc -l <"$RES/$tag.bysym.txt"), top: $(head -1 "$RES/$tag.top.txt" | cut -c1-90), errors: $(wc -l <"$RES/$tag.report.err")"
done
