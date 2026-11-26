#!/usr/bin/env bash
# Option B check for tron PR 5022 (2026-11-24). Runs ON delphi-3b35, on our CPUs 96-143 only (low priority).
# It opens no FPGA card: the test links the fake device (a software stand-in for the cards).
#
# Question: does the dense AMX page function still compile and pass its test when s_pages is an array of
# one-dimensional tensors, each built with the `uninitialized` tag ("option B")?
#
# What it does, in the option-ON build tree of the earlier check (/var/tmp/jhan/b35-pr5606-on, commit 90a9110be5,
# whose h/tron/models/self_attention.hpp is the same blob as at the rebased head 187da02163):
#   1. runs the existing test binary t_amx_dispatch_dtype as the baseline,
#   2. replaces the ONE declaration line of s_pages, and adds a static_assert on the new type,
#   3. rebuilds and runs t_amx_dispatch_dtype with AMX on and with the kill switch TRON_AMX_DISABLE=1,
#   4. restores the file, rebuilds, and checks that the binary has the baseline sha256 again.
# Output: optb-check.txt and optb-ninja.log next to this script.
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
OUT=/home/jhan/workspace/ai-runs/pr5022-rebase-20261124
WT=$(wt_of on)
F=h/tron/models/self_attention.hpp
T=t_amx_dispatch_dtype
only_3b35
exec >"$OUT/optb-check.txt" 2>&1
echo "=== option B check started $(ts) on $(hostname), tree $WT ==="
echo "uptime: $(uptime)"
echo "busy share of our CPUs $OUR_CPUS before the run: $(busy_pct)"
fail() { echo "FAILED: $*"; echo "=== finished $(ts): failed ==="; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$S2" ] || fail "$WT is not at $S2"
[ -z "$(dirty_of "$WT")" ] || fail "$WT has changes: $(dirty_of "$WT" | head -3 | tr '\n' ' ')"
grep -q '^TRON_AMX_DISPATCH:BOOL=ON' "$WT/gen/CMakeCache.txt" || fail "the tree is not configured with TRON_AMX_DISPATCH=ON"
exec {LOCK_FD}>"$WT/gen/keep/build.lock"
flock -n "$LOCK_FD" || fail "another build runs in $WT"
cd "$WT" >/dev/null 2>&1 || fail "cd $WT"
restore() { git -C "$WT" checkout -- "$F"; }
trap restore EXIT
# Prints the last result lines of one test run and its exit code.
run_test() { # $1 = label, rest = environment assignments
  local label=$1; shift
  local log="$OUT/optb-run-$label.log"
  env "$@" $PIN "gen/$T" >"$log" 2>&1
  local rc=$?
  echo "run [$label] exit code $rc: $(grep -E 'All tests passed|test cases:|assertions:' "$log" | tr '\n' ' ')"
  return $rc
}
echo "--- 1. baseline (unchanged source)"
BASE_SHA256=$(sha256sum "gen/$T" | cut -d' ' -f1)
echo "baseline binary sha256: $BASE_SHA256"
run_test baseline-amx-on DUMMY=1 || fail "the baseline run failed"
echo "--- 2. edit"
python3 - "$F" <<'EOF' || fail "the edit did not apply"
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = "      tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};\n"
new = ("      auto s_pages =\n"
       "          make_array_of<tensor<page::page_size>, operation_kv_mul>(uninitialized);\n"
       "      static_assert(std::is_same_v<decltype(s_pages),\n"
       "          std::array<tensor<page::page_size>, operation_kv_mul>>);\n")
n = s.count(old)
if n != 1:
    sys.exit(f"expected 1 match of the declaration, found {n}")
open(p, "w", encoding="utf-8").write(s.replace(old, new))
EOF
git -C "$WT" diff -- "$F"
echo "--- 3. build and run with the edit"
t0=$(date +%s)
$PIN cmake --build gen --target "$T" -j"$JOBS" >"$OUT/optb-ninja.log" 2>&1
rc=$?
echo "build exit code $rc, wall $(( $(date +%s) - t0 )) s, compiler warnings: $(grep -c 'warning:' "$OUT/optb-ninja.log"), errors: $(grep -c 'error:' "$OUT/optb-ninja.log")"
if [ $rc -ne 0 ]; then grep -E 'error|FAILED|static assertion' "$OUT/optb-ninja.log" | sed -n 1,30p | cut -c1-400; fail "the build with the edit failed"; fi
echo "binary sha256 with the edit: $(sha256sum "gen/$T" | cut -d' ' -f1)"
EDIT_OK=yes
run_test optb-amx-on DUMMY=1 || EDIT_OK=no
run_test optb-kill-switch TRON_AMX_DISABLE=1 || EDIT_OK=no
echo "tests with the edit pass: $EDIT_OK"
echo "--- 4. restore"
restore
trap - EXIT
[ -z "$(dirty_of "$WT")" ] || fail "$WT still has changes after the restore"
$PIN cmake --build gen --target "$T" -j"$JOBS" >>"$OUT/optb-ninja.log" 2>&1 || fail "the rebuild after the restore failed"
NOW_SHA256=$(sha256sum "gen/$T" | cut -d' ' -f1)
echo "binary sha256 after the restore: $NOW_SHA256 ($([ "$NOW_SHA256" = "$BASE_SHA256" ] && echo "equals the baseline" || echo "DIFFERS from the baseline"))"
echo "busy share of our CPUs $OUR_CPUS after the run: $(busy_pct)"
echo "=== finished $(ts): edit builds and passes = $EDIT_OK ==="
