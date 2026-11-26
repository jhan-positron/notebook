#!/usr/bin/env bash
# pr5022-optb-20261124: the three unit tests at the pushed head of tron PR 5022 (commit e863b27272), on delphi-3b35.
# Runs on our CPUs only (96-143, low priority). The tests link the fake device, so no FPGA card is opened.
#
# It moves the build tree of arm b (/var/tmp/jhan/b35-optb-b) from "187da02163 plus the uncommitted declaration"
# to the commit e863b27272, which holds that declaration and two comment lines. Then it rebuilds the three test
# programs and runs each one with AMX enabled and with the kill switch TRON_AMX_DISABLE=1.
# After this script, tree b is at the pushed head. Its runtron binary still is the arm b binary of the A/B test.
# Output: exec/results/pr5022-optb-20261124/tests-head.txt. Log: exec/logs/pr5022-optb-20261124-tests-head-ninja.log.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
SHA=e863b27272c13eded2f5c991f6201a1bc66cbfb6
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-optb-20261124
RES=$EXEC/results/$NAME
WT=/var/tmp/jhan/b35-optb-b
F=h/tron/models/self_attention.hpp
TESTS='t_amx_numerics t_amx_dispatch_dtype t_llama_unit'
OUR_CPUS=96-143
PIN="nice -n10 taskset -c $OUR_CPUS"
export SYSTEM_CONFIG="--instance 1,2"
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
exec >"$RES/tests-head.txt" 2>&1
fail() { echo "FAILED: $*"; echo "=== finished $(ts): failed ==="; exit 1; }
exec {LOCK_FD}>"/var/tmp/jhan/$NAME.build-b.lock"
flock -n "$LOCK_FD" || fail "another build runs in $WT"
echo "=== unit tests at the head started $(ts) on $(hostname), tree $WT ==="
git -C "$WT" cat-file -e "$SHA^{commit}" 2>/dev/null || fail "$SHA not visible"
git -C "$WT" checkout -q -- "$F" || fail "could not drop the uncommitted declaration"
git -C "$WT" checkout -q --detach "$SHA" || fail "git checkout $SHA"
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || fail "$WT is not at $SHA"
git -C "$WT" diff --quiet HEAD || fail "$WT has changes in tracked files"
echo "tree at $(git -C "$WT" rev-parse HEAD) ($(git -C "$WT" log -1 --format=%s)), tracked files unchanged"
cd "$WT" >/dev/null 2>&1 || fail "cd $WT"
t0=$(date +%s)
# shellcheck disable=SC2086
$PIN cmake --build gen --target $TESTS -j40 >"$EXEC/logs/$NAME-tests-head-ninja.log" 2>&1 || fail "the build failed (see the ninja log)"
echo "build ok in $(( $(date +%s) - t0 )) s, compiler warnings: $(grep -c 'warning:' "$EXEC/logs/$NAME-tests-head-ninja.log")"
echo "cache: $(grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH):' gen/CMakeCache.txt | tr '\n' ' '); compiler: $(clang++-19 --version | head -1)"
nfail=0
for t in $TESTS; do
  for mode in amx-enabled kill-switch; do
    if [ "$mode" = kill-switch ]; then out=$(TRON_AMX_DISABLE=1 $PIN "gen/$t" 2>&1); rc=$?; else out=$(env -u TRON_AMX_DISABLE $PIN "gen/$t" 2>&1); rc=$?; fi
    echo "$t [$mode] exit code $rc: $(grep -E 'All tests passed|^test cases:|^assertions:' <<<"$out" | tr -s ' ' | tr '\n' ' ')"
    [ $rc -eq 0 ] || nfail=$((nfail + 1))
  done
done
echo "=== finished $(ts): runs with a non-zero exit code = $nfail ==="
