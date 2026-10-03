#!/usr/bin/env bash
# attnstats-20260929-w1 (runs ON delphi-3bda): build the review-round-4 W1 commit of PR #4596 (software-join T5)
# into the existing head tree /var/tmp/jhan/tron-attn-head (incremental, same configure line as the 09-25 round),
# run the unit tests with the fake device on our half (build2.sh), then the switch-on runs (TRON_ATTN_STATS=1)
# and the bad-value run (TRON_ATTN_STATS=yes must print the "ignored" warning). Usage: build-test.sh <commit>.
# Copy of exec/attnstats-20260925-review/build-test.sh with NAME changed and the T5 evidence grep added.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=attnstats-20260929-w1
RES=$EXEC/results/$NAME; LOG=$EXEC/logs/$NAME.log
COMMIT=${1:?commit}
CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
TARGETS="runtron t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_page_share_counters t_tronstats_convention t_heterogeneous_scheduler t_compute_attention_unit"
TESTS="t_page_share_counters t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler t_compute_attention_unit"
WT=/var/tmp/jhan/tron-attn-head
mkdir -p "$RES" "$EXEC/logs"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }; say() { echo "$(ts) $*"; }
say "=== started pid $$ commit $COMMIT on $(hostname) ==="
# NFS attribute cache: the commit was made on claude-box; wait until this host sees it.
for i in $(seq 1 20); do git -C /home/jhan/workspace/tron cat-file -e "$COMMIT^{commit}" 2>/dev/null && break; sleep 30; done
say "commit visible after $i polls"
RES=$RES SRC=/home/jhan/workspace/tron COMMIT=$COMMIT WT=$WT SUFFIX=attnhead4 CONFIGURE_ARGS="$CONFIGURE" \
  TARGETS="$TARGETS" TESTS="$TESTS" JOBS=48 bash "$EXEC/i4525-20260922/build2.sh"
say "build marker: $(cat "$RES/build-attnhead4.done" 2>/dev/null)"
if [ "$(cat "$RES/build-attnhead4.done" 2>/dev/null)" = ok ]; then
  for t in t_llama_unit t_heterogeneous_scheduler; do
    ( cd "$WT" && TRON_ATTN_STATS=1 USE_HW_ATTN=1 nice -n10 taskset -c 72-143,216-287 env SYSTEM_CONFIG="--instance 1,2" "$WT/gen/$t" --skip-benchmarks ) >"$RES/tests-on-$t.out" 2>&1
    say "switch-on $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$RES/tests-on-$t.out" | tail -1))"
  done
  # The bad-value check needs a REAL model state (env_enabled() runs in the state ctor); the t_attn_stats cases pass bools and never
  # read the environment, so the 09-25 script's t_llama_unit "[attn_stats]" run only counted info lines (2026-09-29 correction).
  ( cd "$WT" && TRON_ATTN_STATS=yes taskset -c 72-75 env SYSTEM_CONFIG="--instance 1,2" "$WT/gen/t_heterogeneous_scheduler" --skip-benchmarks ) >"$RES/tests-badvalue.out" 2>&1
  say "bad value t_heterogeneous_scheduler EXIT $? (ignored-warning lines: $(grep -c "TRON_ATTN_STATS='yes' ignored" "$RES/tests-badvalue.out"))"
  grep -h "^\[attn-stats\]" "$RES/tests-on-t_llama_unit.out" | head -8 >"$RES/exit-report-sample.txt"
  # T5 evidence: the software-join test's stats object prints its own [attn-stats] summary when destroyed.
  grep -h "join_wait_cycles" "$RES/tests-on-t_heterogeneous_scheduler.out" "$RES/tests-attnhead4-t_heterogeneous_scheduler.out" 2>/dev/null | head -12 >"$RES/t5-evidence.txt"
  say "T5 evidence lines: $(wc -l <"$RES/t5-evidence.txt")"
fi
say "=== finished ==="; echo done >"$RES/.done"
