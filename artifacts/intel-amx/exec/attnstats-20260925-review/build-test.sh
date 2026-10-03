#!/usr/bin/env bash
# attnstats-20260925-review (runs ON delphi-3bda): build the review-round commit of PR #4596 into the existing
# head tree /var/tmp/jhan/tron-attn-head (incremental, same configure line as exec/attnstats-20260924/chain2.sh),
# run the unit tests with the fake device on our half (build2.sh), then the switch-on runs (TRON_ATTN_STATS=1)
# and the bad-value run (TRON_ATTN_STATS=yes must print the "ignored" warning). Usage: build-test.sh <commit>.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=attnstats-20260925-review
RES=$EXEC/results/$NAME; LOG=$EXEC/logs/$NAME.log
COMMIT=${1:?commit}
CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
TARGETS="runtron t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_page_share_counters t_tronstats_convention t_heterogeneous_scheduler"
TESTS="t_page_share_counters t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
WT=/var/tmp/jhan/tron-attn-head
mkdir -p "$RES" "$EXEC/logs"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }; say() { echo "$(ts) $*"; }
say "=== started pid $$ commit $COMMIT on $(hostname) ==="
# NFS attribute cache: the commit was made on claude-box seconds ago; wait until this host sees it.
for i in $(seq 1 20); do git -C /home/jhan/workspace/tron cat-file -e "$COMMIT^{commit}" 2>/dev/null && break; sleep 30; done
say "commit visible after $i polls"
RES=$RES SRC=/home/jhan/workspace/tron COMMIT=$COMMIT WT=$WT SUFFIX=attnhead3 CONFIGURE_ARGS="$CONFIGURE" \
  TARGETS="$TARGETS" TESTS="$TESTS" JOBS=48 bash "$EXEC/i4525-20260922/build2.sh"
say "build marker: $(cat "$RES/build-attnhead3.done" 2>/dev/null)"
if [ "$(cat "$RES/build-attnhead3.done" 2>/dev/null)" = ok ]; then
  for t in t_llama_unit t_heterogeneous_scheduler; do
    ( cd "$WT" && TRON_ATTN_STATS=1 USE_HW_ATTN=1 nice -n10 taskset -c 72-143,216-287 "$WT/gen/$t" --skip-benchmarks ) >"$RES/tests-on-$t.out" 2>&1
    say "switch-on $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$RES/tests-on-$t.out" | tail -1))"
  done
  ( cd "$WT" && TRON_ATTN_STATS=yes taskset -c 72-75 "$WT/gen/t_llama_unit" "[attn_stats]" --skip-benchmarks ) >"$RES/tests-badvalue.out" 2>&1
  say "bad value [attn_stats] EXIT $? (warning lines: $(grep -c 'TRON_ATTN_STATS=' "$RES/tests-badvalue.out"))"
  grep -h "^\[attn-stats\]" "$RES/tests-on-t_llama_unit.out" | head -8 >"$RES/exit-report-sample.txt"
fi
say "=== finished ==="; echo done >"$RES/.done"
