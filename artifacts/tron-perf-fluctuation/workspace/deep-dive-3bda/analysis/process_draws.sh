#!/usr/bin/env bash
# Incrementally process completed pfgate draws (runs on alpha over NFS).
set -u
ROOT=$(cat /home/jhan/workspace/perf-fluctuation/deep-dive-3bda/CURRENT_CAMPAIGN_PFGATE)
OUT=/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out
cd /home/jhan/workspace/perf-fluctuation/deep-dive-3bda
while :; do
  new=0
  while IFS=, read -r draw status gen _; do
    [ "$status" = ok ] || continue
    [ -s "$ROOT/results/$draw/trace.pftrace" ] || continue
    [ -f "$OUT/$draw/$draw.summary.json" ] && continue
    mkdir -p "$OUT/$draw"
    echo "processing $draw (gen=$gen)"
    python3 analysis/pfgate_windows.py "$ROOT/results/$draw/trace.pftrace" "$OUT/$draw/$draw" --gap-us 1500 \
      || echo "FAILED $draw"
    new=1
  done < <(tail -n +2 "$ROOT/results.csv")
  if [ -f "$ROOT/ALL_DRAWS_SCHEDULED" ] && [ "$new" -eq 0 ]; then
    echo "ALL-PROCESSED $(ls $OUT | grep -c draw_) draws"
    break
  fi
  sleep 45
done
