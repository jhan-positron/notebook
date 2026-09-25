#!/usr/bin/env bash
# attnstats-20260924 chain2 (runs ON delphi-3bda, launched with setsid nohup): the confirmation round for the
# final commit of the attention path stats branch. Steps:
#   1. wait until chain.sh has finished (its log ends with "=== chain finished");
#   2. read the commit to build from head2.sha (written on claude-box; re-read at that moment, so the sha can be
#      updated while this script waits), build it into /var/tmp/jhan/tron-attn-head (incremental: same tree, same
#      configure line), copy runtron to runtron.attnhead2, run the unit tests with the fake device, this time
#      including t_heterogeneous_scheduler (its direct run_joins call changed);
#   3. confirmation cells on OUR half with campaign.sh under NAME=attnstats-20260924b: arms base3 (main binary),
#      head2 (final commit, switch unset) and headon2 (final commit, TRON_ATTN_STATS=1), 3 repetitions, CPU
#      attention, qwen-3-4b tp2 8 users prompt 1024 (the cell with the largest per-step visit rate);
#   4. the objdump comparison for the final binary.
# Words: see chain.sh. Never edit this file while it runs.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20260924
B=$EXEC/i4525-20260922
export NAME=attnstats-20260924b
RES=$EXEC/results/attnstats-20260924
RES2=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain2.log
CHAIN1_LOG=$EXEC/logs/attnstats-20260924-chain.log
REPO=/home/jhan/workspace/tron
CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
TARGETS="runtron t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_page_share_counters t_tronstats_convention t_heterogeneous_scheduler"
TESTS="t_page_share_counters t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"   # t_attn_stats.cpp is part of t_llama_unit since cbf1bb6c0c
RT_BASE=/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase
RT_HEAD=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2
CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024'
mkdir -p "$RES2" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
say() { echo "$(ts) $*"; }
say "=== chain2 started pid $$ ==="
until grep -q "=== chain finished" "$CHAIN1_LOG" 2>/dev/null; do sleep 60; done
HEAD2=$(head -1 "$C/head2.sha" 2>/dev/null | tr -d '[:space:]')
[ -n "$HEAD2" ] || { say "head2.sha missing"; exit 1; }
say "chain1 finished; building $HEAD2"
RES=$RES2 SRC=$REPO COMMIT=$HEAD2 WT=/var/tmp/jhan/tron-attn-head SUFFIX=attnhead2 CONFIGURE_ARGS="$CONFIGURE" \
  TARGETS="$TARGETS" TESTS="$TESTS" JOBS=48 bash "$B/build2.sh"
say "head2 build marker: $(cat "$RES2/build-attnhead2.done" 2>/dev/null)"
[ "$(cat "$RES2/build-attnhead2.done" 2>/dev/null)" = ok ] || { say "head2 build or tests failed; see $RES2/build-attnhead2.log"; exit 1; }
for t in t_llama_unit t_heterogeneous_scheduler; do
  TRON_ATTN_STATS=1 USE_HW_ATTN=1 taskset -c 72-143,216-287 /var/tmp/jhan/tron-attn-head/gen/$t --skip-benchmarks >"$RES2/tests-on-$t.out" 2>&1
  say "switch-on $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$RES2/tests-on-$t.out" | tail -1))"
done
TRON_ATTN_STATS=yes taskset -c 72-75 /var/tmp/jhan/tron-attn-head/gen/t_llama_unit "[attn_stats]" --skip-benchmarks >"$RES2/tests-badvalue-attn_stats.out" 2>&1
say "bad switch value [attn_stats] cases EXIT $? (warning lines: $(grep -c 'TRON_ATTN_STATS=' "$RES2/tests-badvalue-attn_stats.out"))"
bash "$C/objdump-check.sh" "$RT_BASE" "$RT_HEAD" >/dev/null 2>&1; cp "$RES/objdump-check.txt" "$RES2/objdump-check-head2.txt" 2>/dev/null
say "objdump check done"
export RT_BASE RT_HEAD TIP_BASE=66c7bb8db1 TIP_HEAD=$HEAD2
export ARM_ENV_headon2="TRON_ATTN_STATS=1"
export WEDPERF_ARMS="base3 head2 headon2"
CELLS_ALL="$CELLS_ALL" ARMS="base3 head2 headon2" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 bash "$C/campaign.sh"
say "confirmation cells marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
grep -h "^\[attn-stats\]" "$RES2"/rt/*.log 2>/dev/null | head -60 >"$RES2/exit-reports.txt"
say "=== chain2 finished ==="
