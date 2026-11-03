#!/usr/bin/env bash
# glimmer-20261016 tests (runs ON delphi-3bda, called by chain.sh step T or by hand): the three AMX test binaries of the
# g16 build on our half of the machine, the way exec/i4525-20260922/build2.sh runs them (fake device through
# SYSTEM_CONFIG="--instance 1,2", pinned to our cpus), plus t_amx_numerics a second time under the kill switch
# (TRON_AMX_DISABLE=1: the AMX kernel cases must WARN-skip with "AMX unavailable", the gate and pack cases must pass).
# Then, best effort and not gating: a preservation check of main's three non-template kernels (runtron.main1010,
# main 72308ec90c) against the branch's <4> instantiations (disassembly diff after address stripping).
# Words: our half = socket 1 cpus 72-143,216-287; the probe marker = exec/results/td-20261016/probe.done, written by
# another session's whole-machine probe (first round) that removes the hugepage slice files between its runs (the tests
# map hugepages through those files, so they must not overlap); the lease =
# /run/lock/systems-test-ci.lease (nightly CI).
# Usage (on 3bda): SHA=<full sha> bash tests.sh   [TESTS_WAIT_MARKERS="<file> ..."] [TEST_ARGS=--skip-benchmarks]
# Log: exec/logs/glimmer-20261016-tests.log. Marker: exec/results/glimmer-20261016/tests.done = "ok" or "failed-<n>".
# Outputs: exec/results/glimmer-20261016/{tests.txt,tests/<name>.log,preservation.txt}.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
SHA=${SHA:?SHA=<full 40-hex commit sha of jhan-amx-kvmul16> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=glimmer-20261016
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-tests.log
WT=/var/tmp/jhan/tron-g16
BIN=$WT/gen/runtron.g16
MAIN_BIN=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
MAIN_SHA=72308ec90c
OUR_CPUS=72-143,216-287
TEST_ARGS=${TEST_ARGS:---skip-benchmarks}
TESTS_WAIT_MARKERS=${TESTS_WAIT_MARKERS:-"$EXEC/results/td-20261016/probe.done"}   # the first probe round only (the lead's condition); chain.sh step G waits for all rounds
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/tests" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/tests.done"; echo "=== tests finished $(ts): $1 ==="; }
rm -f "$RES/tests.done"
echo "=== tests started $(ts) pid $$ on $(hostname) sha=$SHA wait_markers=[$TESTS_WAIT_MARKERS] args=[$TEST_ARGS] ==="
[ "$(cat "$RES/build.done" 2>/dev/null)" = ok ] || { mark "failed-build-not-ok"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || { mark "failed-worktree-not-at-sha"; exit 1; }
for t in t_amx_numerics t_amx_dispatch_dtype t_llama_unit; do [ -x "$WT/gen/$t" ] || { mark "failed-missing-$t"; exit 1; }; done
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {  # prints the reason and returns 0 while the tests must not run
  local m
  for m in $TESTS_WAIT_MARKERS; do [ -s "$m" ] || { echo "probe marker $m missing"; return 0; }; done
  pgrep -u jhan -x 'runtron(\.[a-z0-9]+)?' >/dev/null 2>&1 && { echo "a jhan runtron is running"; return 0; }
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy 600 && { echo "CI lease busy"; return 0; }
  other_user_active 2>/dev/null && { echo "another person active"; return 0; }
  blackout_active && { echo "blackout window"; return 0; }
  return 1
}
wait_clear() {  # one log line per state change
  local why last=""
  while why=$(blocked); do
    [ "$why" = "$last" ] || { echo "$(ts) waiting: $why"; last=$why; }
    sleep 60
  done
  [ -n "$last" ] && echo "$(ts) clear (was: $last)"
  return 0
}
summary() {  # Catch2 summary of one test log, one line
  grep -E 'All tests passed|^test cases:|^assertions:|AMX unavailable' "$1" | tr '\n' ' ' | tr -s ' ' | cut -c1-400
}
assertions() {  # the assertion count of one test log ("All tests passed (N assertions in M test cases)" or "assertions: N | ...")
  local n
  n=$(grep -oE 'All tests passed \([0-9]+ assertions' "$1" | grep -oE '[0-9]+' | head -1)
  [ -n "$n" ] || n=$(grep -oE '^assertions: *[0-9]+' "$1" | grep -oE '[0-9]+' | head -1)
  echo "${n:-?}"
}
fails=0
: >"$RES/tests.txt"
echo "# test name | assertions | rc   (tip $SHA; SYSTEM_CONFIG=--instance 1,2 on cpus $OUR_CPUS; args $TEST_ARGS)" >>"$RES/tests.txt"
run_test() {  # $1 label $2 binary name $3 extra env (may be empty) $4 "killswitch" when the AMX cases must WARN-skip
  local label=$1
  local bin=$2
  local extra=$3
  local mode=${4:-}
  local out=$RES/tests/$label.log
  local rc n skips
  wait_clear
  echo "$(ts) test $label: $bin env=[$extra] start"
  ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" env SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 3600 "$WT/gen/$bin" $TEST_ARGS ) >"$out" 2>&1
  rc=$?
  n=$(assertions "$out")
  skips=$(grep -c 'AMX unavailable' "$out" || true)
  if [ "$mode" = killswitch ] && [ "$rc" -eq 0 ] && [ "${skips:-0}" -eq 0 ]; then
    echo "$(ts) test $label: rc 0 but no 'AMX unavailable' skip line: the kill switch did not take"; rc=99
  fi
  echo "$label | $n | $rc | env=[$extra] skips=$skips | $(summary "$out")" >>"$RES/tests.txt"
  echo "$(ts) test $label: rc=$rc assertions=$n skips=$skips"
  [ "$rc" -eq 0 ] || fails=$((fails + 1))
  return 0
}
run_test t_amx_numerics t_amx_numerics ""
run_test t_amx_dispatch_dtype t_amx_dispatch_dtype ""
run_test t_llama_unit t_llama_unit ""
run_test t_amx_numerics-killswitch t_amx_numerics "TRON_AMX_DISABLE=1" killswitch
cat "$RES/tests.txt"

# ---- preservation check (best effort, never changes the marker) ----
# main's kernels are plain functions (nm: "T tron::amx_attn_h128g4::qk_rowmajor_128x4(...)"); the branch's are template
# instantiations ("tron::amx_attn_h128g4::qk_rowmajor_128x4<4ul>(...)"). The disassembly of each pair is compared after
# stripping addresses, jump targets and rip-relative comments; displacement differences from the different binary layout remain.
dis_fn() {  # $1 binary $2 demangled-name regex (up to the opening parenthesis) -> normalised disassembly on stdout; rc 1 when not found
  local addr size line
  line=$(nice -n10 taskset -c "$OUR_CPUS" nm -S -C "$1" 2>/dev/null | grep -E -m1 " [TtWw] $2\(" ) || return 1
  addr=$(cut -d' ' -f1 <<<"$line"); size=$(cut -d' ' -f2 <<<"$line")
  [ -n "$addr" ] && [ -n "$size" ] || return 1
  nice -n10 taskset -c "$OUR_CPUS" objdump -d --no-show-raw-insn --start-address="0x$addr" --stop-address="$((16#$addr + 16#$size))" "$1" 2>/dev/null |
    sed -n '/^ *[0-9a-f]*:/p' | sed -E 's/^ *[0-9a-f]+:\t//; s/ *# [0-9a-f]+ <[^>]*>//; s/\b[0-9a-f]{6,}\b <[^>]*>/<target>/g; s/<[^>]*\+0x[0-9a-f]+>/<target>/g'
}
{
  echo "# preservation check $(ts): main $MAIN_SHA ($MAIN_BIN) non-template kernels vs branch $SHA <4> instantiations ($BIN)"
  echo "# normalised objdump -d --no-show-raw-insn per function; counts = instruction lines; diff = lines only in main (-) / only in the branch (+)"
  if [ ! -x "$MAIN_BIN" ]; then echo "n/a: $MAIN_BIN missing"; else
    P=$RES/tests/preservation; mkdir -p "$P"
    for k in pack_q_group_128x4 qk_rowmajor_128x4 weights_times_v_128x4; do
      if ! dis_fn "$MAIN_BIN" "tron::amx_attn_h128g4::$k" >"$P/$k.main.s"; then echo "$k: n/a (symbol not found in main)"; continue; fi
      if ! dis_fn "$BIN" "tron::amx_attn_h128g4::$k<4(ul)?>" >"$P/$k.g16.s"; then echo "$k: n/a (symbol <4> not found in the branch; see $RES/build-symbols.txt)"; continue; fi
      diff -u "$P/$k.main.s" "$P/$k.g16.s" >"$P/$k.diff"; drc=$?
      minus=$(grep -c '^-[^-]' "$P/$k.diff" || true); plus=$(grep -c '^+[^+]' "$P/$k.diff" || true)
      echo "$k: main $(wc -l <"$P/$k.main.s") lines, branch $(wc -l <"$P/$k.g16.s") lines, diff rc=$drc minus=$minus plus=$plus"
    done
    for k in pack_q_group_128x4 qk_rowmajor_128x4 weights_times_v_128x4; do [ -s "$P/$k.diff" ] && { echo; echo "## diff $k"; cat "$P/$k.diff"; }; done
  fi
} >"$RES/preservation.txt" 2>&1
echo "$(ts) preservation check written: $(grep -E '^(pack_q|qk_row|weights_times)' "$RES/preservation.txt" | tr '\n' ';' | cut -c1-300)"
mark "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")"
[ $fails -eq 0 ]
