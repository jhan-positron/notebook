#!/usr/bin/env bash
# glimext-20261018 tests (runs ON delphi-3bda, called by chain.sh step T): the three AMX test binaries of the HEAD build
# (runtron.g16h's worktree, PR #5015 head rebuilt with the host clang 19) on our half of the machine, the way
# exec/glimpl-20261017/tests.sh runs them (fake device through SYSTEM_CONFIG="--instance 1,2", pinned to our cpus), plus
# t_amx_numerics a second time under the kill switch (TRON_AMX_DISABLE=1: the AMX kernel cases must WARN-skip with
# "AMX unavailable", the gate and pack cases must pass). Then, best effort and not gating: the preservation check of the
# BASE build's three plain kernels against the head's <4> instantiations (same compiler this time; disassembly diff after
# address stripping). Fork of exec/glimpl-20261017/tests.sh: worktree/binary names, no probe markers to wait for, the
# preservation reference is the base build of this campaign.
# Usage (on 3bda): SHA=<full sha of the head> bash tests.sh   [TEST_ARGS=--skip-benchmarks]
# Log: exec/logs/glimext-20261018-tests.log. Marker: exec/results/glimext-20261018/tests.done = "ok" or "failed-<n>".
# Outputs: exec/results/glimext-20261018/{tests.txt,tests/<name>.log,preservation.txt}.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
SHA=${SHA:?SHA=<full 40-hex commit sha of the head> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=glimext-20261018
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-tests.log
WT=/var/tmp/jhan/tron-g16h
BIN=$WT/gen/runtron.g16h
MAIN_BIN=/var/tmp/jhan/tron-g16b/gen/runtron.g16b
OUR_CPUS=72-143,216-287
TEST_ARGS=${TEST_ARGS:---skip-benchmarks}
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/tests" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/tests.done"; echo "=== tests finished $(ts): $1 ==="; }
rm -f "$RES/tests.done"
echo "=== tests started $(ts) pid $$ on $(hostname) sha=$SHA args=[$TEST_ARGS] ==="
[ "$(cat "$RES/build-g16h.done" 2>/dev/null)" = ok ] || { mark "failed-build-not-ok"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || { mark "failed-worktree-not-at-sha"; exit 1; }
for t in t_amx_numerics t_amx_dispatch_dtype t_llama_unit; do [ -x "$WT/gen/$t" ] || { mark "failed-missing-$t"; exit 1; }; done
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {  # prints the reason and returns 0 while the tests must not run
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
summary() { grep -E 'All tests passed|^test cases:|^assertions:|AMX unavailable' "$1" | tr '\n' ' ' | tr -s ' ' | cut -c1-400; }
assertions() {
  local n
  n=$(grep -oE 'All tests passed \([0-9]+ assertions' "$1" | grep -oE '[0-9]+' | head -1)
  [ -n "$n" ] || n=$(grep -oE '^assertions: *[0-9]+' "$1" | grep -oE '[0-9]+' | head -1)
  echo "${n:-?}"
}
fails=0
: >"$RES/tests.txt"
echo "# test name | assertions | rc   (head $SHA, binaries of $WT; SYSTEM_CONFIG=--instance 1,2 on cpus $OUR_CPUS; args $TEST_ARGS)" >>"$RES/tests.txt"
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

# ---- preservation check (best effort, never changes the marker): base's plain kernels vs the head's <4> instantiations ----
dis_fn() {  # $1 binary $2 demangled-name regex (up to the opening parenthesis) -> normalised disassembly on stdout; rc 1 when not found
  local addr size line
  line=$(nice -n10 taskset -c "$OUR_CPUS" nm -S -C "$1" 2>/dev/null | grep -E -m1 " [TtWw] $2\(" ) || return 1
  addr=$(cut -d' ' -f1 <<<"$line"); size=$(cut -d' ' -f2 <<<"$line")
  [ -n "$addr" ] && [ -n "$size" ] || return 1
  nice -n10 taskset -c "$OUR_CPUS" objdump -d --no-show-raw-insn --start-address="0x$addr" --stop-address="$((16#$addr + 16#$size))" "$1" 2>/dev/null |
    sed -n '/^ *[0-9a-f]*:/p' | sed -E 's/^ *[0-9a-f]+:\t//; s/ *# [0-9a-f]+ <[^>]*>//; s/\b[0-9a-f]{6,}\b <[^>]*>/<target>/g; s/<[^>]*\+0x[0-9a-f]+>/<target>/g'
}
{
  echo "# preservation check $(ts): base build ($MAIN_BIN) plain kernels vs head $SHA <4> instantiations ($BIN); both built with the host clang 19"
  echo "# normalised objdump -d --no-show-raw-insn per function; counts = instruction lines; diff = lines only in base (-) / only in the head (+)"
  if [ ! -x "$MAIN_BIN" ]; then echo "n/a: $MAIN_BIN missing"; else
    P=$RES/tests/preservation; mkdir -p "$P"
    for k in pack_q_group_128x4 qk_rowmajor_128x4 weights_times_v_128x4; do
      if ! dis_fn "$MAIN_BIN" "tron::amx_attn_h128g4::$k" >"$P/$k.base.s"; then echo "$k: n/a (symbol not found in base)"; continue; fi
      if ! dis_fn "$BIN" "tron::amx_attn_h128g4::$k<4(ul)?>" >"$P/$k.head.s"; then echo "$k: n/a (symbol <4> not found in the head; the host nm may not demangle the requires-clause template)"; continue; fi
      diff -u "$P/$k.base.s" "$P/$k.head.s" >"$P/$k.diff"; drc=$?
      minus=$(grep -c '^-[^-]' "$P/$k.diff" || true); plus=$(grep -c '^+[^+]' "$P/$k.diff" || true)
      echo "$k: base $(wc -l <"$P/$k.base.s") lines, head $(wc -l <"$P/$k.head.s") lines, diff rc=$drc minus=$minus plus=$plus"
    done
    for k in pack_q_group_128x4 qk_rowmajor_128x4 weights_times_v_128x4; do [ -s "$P/$k.diff" ] && { echo; echo "## diff $k"; cat "$P/$k.diff"; }; done
  fi
} >"$RES/preservation.txt" 2>&1
echo "$(ts) preservation check written: $(grep -E '^(pack_q|qk_row|weights_times)' "$RES/preservation.txt" | tr '\n' ';' | cut -c1-300)"
mark "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")"
[ $fails -eq 0 ]
