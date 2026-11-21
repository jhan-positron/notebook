#!/usr/bin/env bash
# pr5022-final-20261119 mutation check of the test exit code. Runs ON delphi-3b35 (shared machine: Brian Hamon
# and John Pruitt use the first half of the FPGA cards). Uses our CPUs only (96-143, low priority), the fake
# device, no FPGA card, no huge page.
#
# Question: when the transposing store of the AMX QK kernel is broken, which exit code does gen/t_amx_numerics
# return? An automated review of the PR head says "4, the number of failed assertions", and that the CTest
# property SKIP_RETURN_CODE 4 would then report the failure as a skip. The pinned Catch2 (the test framework,
# v3.7.1) source says 42 for any failed assertion (catch_session.cpp:37, :356).
#
# What it does, in the build tree of the final head (/var/tmp/jhan/b35-pr5022-final):
#   1. breaks one line of h/tron/kernels/amx_attn_transpose.hpp (stage 1 of the transpose reads the high halves
#      instead of the low halves; every store still goes to the same addresses),
#   2. rebuilds gen/t_amx_numerics and runs it with AMX on, with the kill switch TRON_AMX_DISABLE=1, and through
#      ctest (the test runner of CMake, which applies SKIP_RETURN_CODE),
#   3. restores the line, rebuilds, and checks that the tree hash and the sha256 of the binary are back.
# The restore also runs when the script stops early (trap).
# Usage (on 3b35): bash mutation-exit-code-3b35.sh      Output: exec/results/pr5022-final-20261119/mutation-exit-code.txt
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-final-20261119
RES=$EXEC/results/$NAME
OUT=$RES/mutation-exit-code.txt
LOG=$EXEC/logs/$NAME-mutation.log
WT=/var/tmp/jhan/b35-pr5022-final
HDR=h/tron/kernels/amx_attn_transpose.hpp
OUR_CPUS=96-143
PIN="nice -n10 taskset -c $OUR_CPUS"
GOOD='__m512 t0 = _mm512_unpacklo_ps(r0, r1);'
BAD='__m512 t0 = _mm512_unpackhi_ps(r0, r1);'
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
exec {LOCK_FD}>"/var/tmp/jhan/$NAME.mutation.lock"
flock -n "$LOCK_FD" || { echo "another copy runs"; exit 1; }
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
ts() { date -u +%FT%TZ; }
build() { ( cd "$WT" >/dev/null 2>&1 && $PIN cmake --build gen --target t_amx_numerics -j40 ) >>"$LOG" 2>&1; }
restore() {
  git -C "$WT" checkout -- "$HDR" >>"$LOG" 2>&1
  build
}
trap restore EXIT
run() {   # run <label> <extra env or -> <args...>: prints the exit code and the Catch2 summary lines
  local label=$1 extra=$2; shift 2
  [ "$extra" = - ] && extra=
  local f=$RES/tests/mutation-$label.log
  ( cd "$WT" >/dev/null 2>&1 && $PIN env SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 600 gen/t_amx_numerics "$@" ) >"$f" 2>&1
  local rc=$?
  echo "$label: exit code $rc | $(grep -E '^(test cases|assertions|All tests passed)' "$f" | tr -s ' ' | tr '\n' ';')"
}
{
  echo "# mutation check on $(hostname), $(ts); build tree $WT"
  WANT_TREE=$(cat "$RES/tree.txt")
  git -C "$WT" add -A; echo "tree before: $(git -C "$WT" write-tree) (final head: $WANT_TREE)"
  SHA_BEFORE=$(sha256sum "$WT/gen/t_amx_numerics" | cut -c1-64); echo "sha256 of gen/t_amx_numerics before: $SHA_BEFORE"
  [ "$(grep -c -F "$GOOD" "$WT/$HDR")" = 1 ] || { echo "the line to break was not found exactly once"; exit 1; }
  run unmutated-amx-on - --skip-benchmarks
  sed -i "s|$GOOD|$BAD|" "$WT/$HDR"
  echo "mutation: $(git -C "$WT" diff --stat -- "$HDR" | tail -1 | sed 's/^ *//')"
  git -C "$WT" diff -U0 -- "$HDR" | grep -E '^[+-] ' | sed 's/^/    /'
  build || { echo "build of the mutated tree failed, see $LOG"; exit 1; }
  echo "sha256 of the mutated binary: $(sha256sum "$WT/gen/t_amx_numerics" | cut -c1-64)"
  run mutated-amx-on - --skip-benchmarks
  run mutated-kill-switch TRON_AMX_DISABLE=1 --skip-benchmarks
  echo "ctest on the mutated binary (it applies SKIP_RETURN_CODE 4):"
  CT=$RES/tests/mutation-ctest.log
  ( cd "$WT/gen" >/dev/null 2>&1 && $PIN env SYSTEM_CONFIG="--instance 1,2" ctest -R '^t_amx_numerics$' --timeout 600 ) >"$CT" 2>&1
  echo "    ctest exit code: $?"
  grep -E 'Test +#|tests passed|tests failed|Not Run|Skipped|Failed' "$CT" | sed 's/^/    /'
  trap - EXIT
  restore
  git -C "$WT" add -A; GOT_TREE=$(git -C "$WT" write-tree)
  SHA_AFTER=$(sha256sum "$WT/gen/t_amx_numerics" | cut -c1-64)
  echo "restored: tree $GOT_TREE ($([ "$GOT_TREE" = "$WANT_TREE" ] && echo "equals the final head" || echo "DIFFERS from the final head")); sha256 $SHA_AFTER ($([ "$SHA_AFTER" = "$SHA_BEFORE" ] && echo "same binary as before" || echo "binary DIFFERS from before"))"
  run restored-amx-on - --skip-benchmarks
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
