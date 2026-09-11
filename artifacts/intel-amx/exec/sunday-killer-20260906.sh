#!/usr/bin/env bash
# One-shot: at Sunday 2026-09-06 00:00 PDT (1788678000) stop every process of the
# PR 3879 split chain on delphi-3bda (jhan promised Bill the machine that day).
# Logs to ~/workspace/intel-AMX/exec/logs/sunday-killer.log.
LOG=~/workspace/intel-AMX/exec/logs/sunday-killer.log
now=$(date +%s); wait=$(( 1788678000 - now )); [ $wait -gt 0 ] && sleep $wait
{
  echo "=== $(date -u +%FT%TZ) Sunday blackout: stopping the split chain ==="
  leader=$(pgrep -f 'PR0-on.*R-cano[n]' | head -1)
  if [ -n "$leader" ]; then echo "chain leader pid $leader -> TERM process group"; kill -TERM -- -$leader 2>/dev/null; fi
  pkill -TERM -f 'split-verif[y]2' 2>/dev/null
  pkill -TERM -f 'tron-spli[t]-' 2>/dev/null
  sleep 15
  [ -n "$leader" ] && kill -KILL -- -$leader 2>/dev/null
  pkill -KILL -f 'split-verif[y]2' 2>/dev/null
  pkill -KILL -f 'tron-spli[t]-' 2>/dev/null
  echo "remaining: $(pgrep -af 'split-verif[y]2|tron-spli[t]-' | wc -l) processes"
  echo "chain stopped for the Sunday blackout; resume Monday 2026-09-07 00:00 PDT" > ~/workspace/intel-AMX/exec/logs/split-SUNDAY-STOP.marker
} >> "$LOG" 2>&1
