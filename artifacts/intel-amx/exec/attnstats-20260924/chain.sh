#!/usr/bin/env bash
# attnstats-20260924 chain (runs ON delphi-3bda, launched with setsid nohup): the machine steps of the
# attention path stats PR (branch jhan-attn-path-stats, base = main 66c7bb8db1), in this order:
#   1. wait for the base build marker (build-attnbase.done = ok; started separately with build2.sh);
#   2. build the head runtron + unit tests from HEAD_COMMIT into /var/tmp/jhan/tron-attn-head with the same
#      configure line as the base (cross-avx512 preset, ingest models on, AMX on), run the unit tests with the
#      fake device (build-attnhead.done);
#   3. runtron cells on OUR half with campaign.sh: arms base (main), head (branch, switch unset), headon (branch,
#      TRON_ATTN_STATS=1), base2 (main again = same-binary control), 3 repetitions, CPU attention, qwen-3-4b tp2
#      8 users, prompt 1024 and 8192; then headon vs headkill (TRON_AMX_DISABLE=1) once for the kill-switch check;
#   4. a side poller copies the FUSE leaves of the head runtron (dev-build mount under the worktree's stats/) into
#      $RES/fuse-poll.log every 15 s while a runtron of ours runs, so the live-read claim has evidence.
# Words: base = main binary; head = branch binary; the switch = the environment variable TRON_ATTN_STATS;
# our half = socket 1, FPGA cards 90/93/b9/bc (--instance 2,4 for tp2); TPS = generated tokens per second.
# Never edit this file while it runs (bash reads it incrementally).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20260924
B=$EXEC/i4525-20260922            # build2.sh lives there (generic build step)
export NAME=${NAME:-attnstats-20260924}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
HEAD_COMMIT=${HEAD_COMMIT:?HEAD_COMMIT (sha of the branch commit to build) is required}
CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
TARGETS="runtron t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_page_share_counters t_tronstats_convention t_attn_stats"
TESTS="t_attn_stats t_page_share_counters t_llama_unit t_amx_numerics t_amx_dispatch_dtype"
RT_BASE=/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase
RT_HEAD=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead
STATS_DIR=/var/tmp/jhan/tron-attn-head/stats
REPS=${REPS:-3}
CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024\nq3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192'
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
say() { echo "$(ts) $*"; }
say "=== chain started pid $$ HEAD_COMMIT=$HEAD_COMMIT REPS=$REPS ==="

# 1. base build marker
while [ "$(cat "$RES/build-attnbase.done" 2>/dev/null)" != ok ]; do
  if [ -f "$RES/build-attnbase.done" ]; then say "base build marker: $(cat "$RES/build-attnbase.done"); giving up"; exit 1; fi
  sleep 30
done
say "base build ok: $(ls -la "$RT_BASE" 2>/dev/null)"

# 2. head build + unit tests (fake device)
RES=$RES SRC=$REPO COMMIT=$HEAD_COMMIT WT=/var/tmp/jhan/tron-attn-head SUFFIX=attnhead CONFIGURE_ARGS="$CONFIGURE" \
  TARGETS="$TARGETS" TESTS="$TESTS" JOBS=48 bash "$B/build2.sh"
say "head build marker: $(cat "$RES/build-attnhead.done" 2>/dev/null)"
[ "$(cat "$RES/build-attnhead.done" 2>/dev/null)" = ok ] || { say "head build or tests failed; see $RES/build-attnhead.log"; exit 1; }
# the stats-on unit test pass: the same tests once more with the switch on (the leaf test and the tally tests
# cover the on path directly; this run shows the env var itself is harmless for the fake-device tests)
for t in t_attn_stats t_llama_unit; do
  TRON_ATTN_STATS=1 taskset -c 72-143,216-287 /var/tmp/jhan/tron-attn-head/gen/$t --skip-benchmarks >"$RES/tests-on-$t.out" 2>&1
  say "switch-on $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$RES/tests-on-$t.out" | tail -1))"
done

# 4. FUSE poller (background): while a head runtron runs, copy the attention leaves
(
  while :; do
    if pgrep -u jhan -f "^$RT_HEAD " >/dev/null 2>&1; then
      for f in $(find "$STATS_DIR" -path '*/attention/*' -type f 2>/dev/null | grep -E '/(summary|decode_like_totals|prompt_or_mixed_totals|decode_like_forwards|prompt_or_mixed_forwards|decode_like_layer_0)$'); do
        echo "$(ts) $f $(cat "$f" 2>/dev/null | head -c 1500)"
      done >>"$RES/fuse-poll.log"
    fi
    sleep 15
  done
) &
POLLER=$!
say "fuse poller pid $POLLER"

# 3. cells
export RT_BASE RT_HEAD TIP_BASE=66c7bb8db1 TIP_HEAD=$HEAD_COMMIT
export ARM_ENV_headon="TRON_ATTN_STATS=1" ARM_ENV_headkill="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"
export WEDPERF_ARMS="base head headon base2 headkill"
CELLS_ALL="$CELLS_ALL" ARMS="base head headon base2" ATTNS=cpu REPS=$REPS DEADLINE_HHMM=0130 bash "$C/campaign.sh"
say "main cells marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
# kill-switch cross-check: one repetition, prompt 1024 only, same results folder (campaign.sh skips runs already done)
CELLS_ALL="$CELLS_ALL" CELLS="q3-4b-tp2-8u-p1024" ARMS="headon headkill" ATTNS=cpu REPS=1 DEADLINE_HHMM=0130 bash "$C/campaign.sh"
say "kill-switch cells marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
kill $POLLER 2>/dev/null
# exit reports of the head runs (stderr lines) for the record
grep -h "^\[attn-stats\]" "$RES"/rt/*.log 2>/dev/null | head -100 >"$RES/exit-reports.txt"
say "=== chain finished ==="
