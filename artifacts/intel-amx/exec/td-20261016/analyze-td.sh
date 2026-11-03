#!/usr/bin/env bash
# td-20261016 (runs ON delphi-3bda, our CPUs, after probe-td.sh): the per-layer comparison of the full intermediates records
# of the probe's arms with exec/dd/dd_first_divergence.py (threshold 0 = any difference). One python process per pair, in
# parallel, nice 10, pinned to cpus 72-143. Outputs: exec/results/td-20261016/layers-<off>-vs-<on>.{json,txt,csv}.
# Usage (on 3bda): [PAIRS="off:on ..."] bash analyze-td.sh   ("off:on" = reference, test). Log: exec/logs/td-analyze.log
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/td-20261016
D=/var/tmp/jhan/td
DD=$EXEC/dd
LOG=$EXEC/logs/td-analyze.log
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
PAIRS=${PAIRS:-"base:poc baseoff:pocoff clean:baseoff base:new new:newoff newoff:trunc new:trunc baseoff:base baseoff:newoff clean:new"}
echo "=== analyze started $(ts) pairs=[$PAIRS] ==="
for pr in $PAIRS; do off=${pr%%:*}; on=${pr##*:}
  [ -s "$D/$off.full" ] && [ -s "$D/$on.full" ] || { echo "$(ts) skip $off vs $on: missing full record"; continue; }
  ( t0=$(date +%s); nice -n10 taskset -c 72-143 python3 "$DD/dd_first_divergence.py" --off "$D/$off.full" --on "$D/$on.full" --out "$RES/layers-$off-vs-$on.json" --threshold 0 --csv "$RES/layers-$off-vs-$on.csv" > "$RES/layers-$off-vs-$on.txt" 2>&1; echo "$(ts) $off vs $on rc=$? wall=$(( $(date +%s) - t0 ))s" ) &
done
wait
echo "=== analyze finished $(ts) ==="
