#!/usr/bin/env bash
# vnnik4-20260915 re-verification of the cleaned-up jhan-amx-vnniK head (handoff section 5,
# item 2): wait until the nightly CI releases delphi-3bda, build the commit into
# /var/tmp/jhan/tron-vnnik4 (runtron.vnnik4) with vnnik2-20260915/build.sh (configure,
# syntax check, runtron + 4 unit tests, the tests, the Haskell suite), then run
# vnnik2-20260915/campaign.sh under NAME=vnnik4-20260915 with the arms base (PR #3879
# binary) and ab (the new binary; the arm's switch variables are ignored since the
# switches were removed) at prompt 1024, tp2 and tp4, 2 repetitions, plus the greedy
# smoke ab / ab2. The smoke tokens of the review-fixed binary runtron.vnnik3
# (results/vnnik2-confirm-20260915/smoke/ab.tokens) are copied in as "vnni.tokens" so
# that compare_tokens.py reports "vnni vs ab" = old binary vs new binary.
# Usage (on delphi-3bda): verify.sh <commit>
set -u
COMMIT=$1
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=vnnik4-20260915
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
mkdir -p "$RES/smoke" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
{
echo "=== verify.sh $COMMIT started $(ts) pid $$"
while ci_lease_busy; do echo "$(ts) CI lease busy; build waits"; sleep 120; done
echo "$(ts) CI lease free"
} >>"$LOG" 2>&1
RES=$RES LOG=$EXEC/logs/$NAME-build.log WT=/var/tmp/jhan/tron-vnnik4 SUFFIX=vnnik4 bash "$EXEC/vnnik2-20260915/build.sh" "$COMMIT"
echo "$(ts) build marker: $(cat "$RES/build.done" 2>/dev/null)" >>"$LOG"
# Cost data for the slice check (doc/slice-benchmark-lifecycle.md, t/AGENTS.md): the new
# test needs a row in config/test-benchmarks.json, and the two tests that gained a case
# are refreshed; measured while the box is idle (CI released, no cells yet). The diff is
# saved for the NFS worktree.
if [ "$(cat "$RES/build.done" 2>/dev/null)" = ok ]; then
  ( cd /var/tmp/jhan/tron-vnnik4 && env -u SYSTEM_CONFIG /home/jhan/.nix-profile/bin/nix develop --command bash -c \
      'bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics 2>&1 | tail -25; echo "bench rc=${PIPESTATUS[0]}"; git diff --stat -- config/test-benchmarks.json' ;
    git -C /var/tmp/jhan/tron-vnnik4 diff -- config/test-benchmarks.json >"$RES/bench-update.diff" ) >"$RES/bench-update.txt" 2>&1
  echo "$(ts) bench --update: $(tail -3 "$RES/bench-update.txt" | tr '\n' ' ')" >>"$LOG"
fi
cp -n "$EXEC/results/vnnik2-confirm-20260915/smoke/ab.tokens" "$RES/smoke/vnni.tokens" 2>/dev/null
NAME=$NAME WT=/var/tmp/jhan/tron-vnnik4 SUFFIX=vnnik4 ARMS="base ab" SMOKE_ARMS="ab ab2" PROMPTS=1024 RT_REPS=2 TP4_REPS=2 LONG_REPS=0 RUN_TRACES=0 \
  bash "$EXEC/vnnik2-20260915/campaign.sh"
echo "$(ts) verify.sh done: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" >>"$LOG"
