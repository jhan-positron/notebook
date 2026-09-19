#!/usr/bin/env bash
# vnnik6 extra traces at prompt 2048: the prompt-2048 cells showed a decode loss for vnni while
# prompt 1024 showed none and prompt 8192 a large gain, so the attribution needs a trace at 2048
# too. Runs trace.sh for base and vnni at tp2, prompt 2048, 8 users, 32 generated tokens, passes
# 1-40 (16 prefill passes of 1024 token jobs and 24 decode steps), AFTER the prompt-8192 traces
# have written their .done marker.
# Usage (on delphi-3bda): setsid nohup bash extra3-trace2048.sh &
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
LOG=$EXEC/logs/vnnik6-trace2048-20260916.log
exec >>"$LOG" 2>&1
echo "=== extra3-trace2048 started $(ts) pid $$: waits for $EXEC/logs/vnnik6-trace8192-20260916.done ==="
while [ ! -s "$EXEC/logs/vnnik6-trace8192-20260916.done" ]; do sleep 60; done
echo "$(ts) prompt-8192 traces done: $(cat "$EXEC/logs/vnnik6-trace8192-20260916.done")"
tl=$(grep -h "GUARD takeover: all checks passed" "$EXEC/logs/vnnik6-20260916.log" "$EXEC/logs/vnnik6-oldbase-20260916.log" "$EXEC/logs/vnnik6-trace8192-20260916.log" 2>/dev/null | tail -1 | cut -d' ' -f1)
if [ -n "$tl" ]; then GUARD_TAKEOVER_LAST=$(date -d "$tl" +%s 2>/dev/null || echo 0); echo "$(ts) inherited takeover time $tl ($GUARD_TAKEOVER_LAST)"; fi
export GUARD_TAKEOVER_LAST
ARMS="base vnni" TPS="2" PROMPT=2048 GEN=32 PASSES=1-40 \
  RES="$EXEC/results/vnnik6-trace2048-20260916" LOG="$LOG" MARKER="$EXEC/logs/vnnik6-trace2048-20260916.done" \
  bash "$EXEC/vnnik6-20260916/trace.sh"
echo "=== extra3-trace2048 finished $(ts): $(cat "$EXEC/logs/vnnik6-trace2048-20260916.done" 2>/dev/null) ==="
