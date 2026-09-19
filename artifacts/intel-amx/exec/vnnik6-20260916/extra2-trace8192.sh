#!/usr/bin/env bash
# vnnik6 extra traces at prompt 8192: the prompt-2048 cells showed a decode loss for vnni that the
# prompt-1024 cells did not, so the attribution (reader against store) needs traces at a long
# prompt. Runs trace.sh for base and vnni at tp2, prompt 8192, 8 users, 32 generated tokens,
# passes 1-90 (64 prefill passes of 1024 token jobs + 26 decode steps), AFTER the extra old-base
# cell has written its .done marker (so the machine is ours and idle).
# Usage (on delphi-3bda): setsid nohup bash extra2-trace8192.sh &
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
LOG=$EXEC/logs/vnnik6-trace8192-20260916.log
exec >>"$LOG" 2>&1
echo "=== extra2-trace8192 started $(ts) pid $$: waits for $EXEC/logs/vnnik6-oldbase-20260916.done ==="
while [ ! -s "$EXEC/logs/vnnik6-oldbase-20260916.done" ]; do sleep 60; done
echo "$(ts) old-base cell done: $(cat "$EXEC/logs/vnnik6-oldbase-20260916.done")"
tl=$(grep -h "GUARD takeover: all checks passed" "$EXEC/logs/vnnik6-20260916.log" "$EXEC/logs/vnnik6-oldbase-20260916.log" 2>/dev/null | tail -1 | cut -d' ' -f1)
if [ -n "$tl" ]; then GUARD_TAKEOVER_LAST=$(date -d "$tl" +%s 2>/dev/null || echo 0); echo "$(ts) inherited takeover time $tl ($GUARD_TAKEOVER_LAST)"; fi
export GUARD_TAKEOVER_LAST
ARMS="base vnni" TPS="2" PROMPT=8192 GEN=32 PASSES=1-90 \
  RES="$EXEC/results/vnnik6-trace8192-20260916" LOG="$LOG" MARKER="$EXEC/logs/vnnik6-trace8192-20260916.done" \
  bash "$EXEC/vnnik6-20260916/trace.sh"
echo "=== extra2-trace8192 finished $(ts): $(cat "$EXEC/logs/vnnik6-trace8192-20260916.done" 2>/dev/null) ==="
