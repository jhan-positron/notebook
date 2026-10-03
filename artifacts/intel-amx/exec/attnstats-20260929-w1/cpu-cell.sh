#!/usr/bin/env bash
# attnstats-20260929-cpu (runs ON delphi-3bda): one CPU-attention runtron cell of PR #4596 head bff317e0d3 with the switch on,
# through exec/attnstats-20260924/campaign.sh (our half, guards, lease wait, idle takeover, restore), plus a poller that keeps the
# last live snapshot of every attention leaf (the worker and layer leaves are not in the stderr report). Purpose: refreshed leaf
# samples for the PR body, the first software-join T5 of a real model, and the forward/token-job counts after forward_scope (W2).
# Cell: qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, USE_HW_ATTN=0, arm headon4 = runtron.attnhead4 + TRON_ATTN_STATS=1, 1 rep.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=${NAME:-attnstats-20260929-cpu}
RES=$EXEC/results/$NAME; LOG=$EXEC/logs/$NAME-cell.log
mkdir -p "$RES/leaves-latest" "$EXEC/logs"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }; say() { echo "$(ts) $*"; }
STATS_DIR=/var/tmp/jhan/tron-attn-head/stats
export RT_BASE=/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase
export RT_HEAD=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead4
export ARM_ENV_headon4="TRON_ATTN_STATS=1"
say "=== cpu cell started pid $$ on $(hostname): head $(git -C /var/tmp/jhan/tron-attn-head rev-parse --short HEAD), STATS_DIR=$STATS_DIR ==="
(
  while :; do
    if pgrep -u jhan -f "^$RT_HEAD " >/dev/null 2>&1; then
      A=$(find "$STATS_DIR" -type d -path '*/attention' 2>/dev/null | head -1)
      if [ -n "$A" ] && grep -q '"forwards":[1-9]' "$A/decode_like_forwards" 2>/dev/null; then
        T=$RES/leaves-latest.tmp; rm -rf "$T"; mkdir -p "$T"
        for f in "$A"/*; do cat "$f" >"$T/$(basename "$f")" 2>/dev/null; done
        echo "$(ts) $A" >"$T/.taken"; rm -rf "$RES/leaves-latest"; mv "$T" "$RES/leaves-latest"
        echo "$(ts) snapshot: $(cat "$A/decode_like_forwards" | head -c 300)" >>"$RES/fuse-poll.log"
      fi
    fi
    sleep ${POLL_S:-10}
  done
) &
POLLER=$!
say "poller pid $POLLER"
CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024' ARMS="headon4" ATTNS=cpu REPS=1 DEADLINE_HHMM=0130 bash "$EXEC/attnstats-20260924/campaign.sh"
say "campaign marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
kill $POLLER 2>/dev/null
grep -h "^\[attn-stats\]" "$RES"/rt/*.log 2>/dev/null >"$RES/exit-reports.txt"
say "exit-report lines: $(wc -l <"$RES/exit-reports.txt"), snapshot: $(cat "$RES/leaves-latest/.taken" 2>/dev/null)"
say "=== cpu cell finished ==="
