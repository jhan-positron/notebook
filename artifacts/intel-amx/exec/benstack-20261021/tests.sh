#!/usr/bin/env bash
# benstack-20261021 tests (runs ON delphi-3bda): the five test binaries of every built tag (bp2 bp2v bp3 bp3v bp4 bp4v =
# the three re-expressed branches, TRON_K_VNNI OFF / ON) on our cpus with the fake device (SYSTEM_CONFIG="--instance 1,2"),
# with USE_HW_ATTN unset (t_heterogeneous_scheduler skips its software-scored section when it is set), plus two kill-switch runs (TRON_AMX_DISABLE=1 on the option-ON builds: t_amx_numerics of bp2v must WARN-skip its AMX
# cases, t_llama_unit of bp4v must pass). Fork of exec/pr5047-20261020/tests.sh: the tag's sha is read from its build
# record (build-$tag.txt "tip <sha>"), the test list is longer. Production serving is left alone (unit tests only).
# Usage (on 3bda): bash tests.sh   [TEST_ARGS=--skip-benchmarks] [TAGS="bp2 bp2v bp3 bp3v bp4 bp4v"]
# Log: exec/logs/benstack-20261021-tests.log. Marker: exec/results/benstack-20261021/tests.done = "ok" or "failed-<n>".
# Outputs: exec/results/benstack-20261021/{tests.txt,tests/<tag>-<name>.log}.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=benstack-20261021
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-tests.log
TAGS=${TAGS:-"bp2 bp2v bp3 bp3v bp4 bp4v"}
OUR_CPUS=72-143,216-287
TEST_ARGS=${TEST_ARGS:---skip-benchmarks}
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/tests" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/tests.done"; echo "=== tests finished $(ts): $1 ==="; }
rm -f "$RES/tests.done"
echo "=== tests started $(ts) pid $$ on $(hostname) tags=[$TAGS] args=[$TEST_ARGS] ==="
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {
  pgrep -u jhan -x 'runtron(\.[a-z0-9]+)?' >/dev/null 2>&1 && { echo "a jhan runtron is running"; return 0; }
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy 600 && { echo "CI lease busy"; return 0; }
  other_user_active 2>/dev/null && { echo "another person active"; return 0; }
  blackout_active && { echo "blackout window"; return 0; }
  return 1
}
wait_clear() {
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
# appends: run-one.sh launches tests.sh once per branch; each launch adds a header line below
echo "# tag | test name | assertions | rc   (SYSTEM_CONFIG=--instance 1,2 on cpus $OUR_CPUS; args $TEST_ARGS; the tag sha is in build-<tag>.txt)" >>"$RES/tests.txt"
run_test() {  # $1 tag $2 label $3 binary name $4 extra env (may be empty) $5 "killswitch" when the AMX cases must WARN-skip
  local tag=$1
  local label=$2
  local bin=$3
  local extra=$4
  local mode=${5:-}
  local wt=/var/tmp/jhan/tron-$tag
  local out=$RES/tests/$tag-$label.log
  local rc n skips
  [ -x "$wt/gen/$bin" ] || { echo "$tag | $label | ? | missing | $wt/gen/$bin missing" >>"$RES/tests.txt"; fails=$((fails + 1)); return 0; }
  wait_clear
  echo "$(ts) test $tag $label: $bin env=[$extra] start"
  ( cd "$wt" && nice -n10 taskset -c "$OUR_CPUS" env -u USE_HW_ATTN SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 3600 "$wt/gen/$bin" $TEST_ARGS ) >"$out" 2>&1
  rc=$?
  n=$(assertions "$out")
  skips=$(grep -c 'AMX unavailable' "$out" || true)
  if [ "$mode" = killswitch ] && [ "$rc" -eq 0 ] && [ "${skips:-0}" -eq 0 ]; then
    echo "$(ts) test $tag $label: rc 0 but no 'AMX unavailable' skip line: the kill switch did not take"; rc=99
  fi
  echo "$tag | $label | $n | $rc | env=[$extra] skips=$skips | $(summary "$out")" >>"$RES/tests.txt"
  echo "$(ts) test $tag $label: rc=$rc assertions=$n skips=$skips"
  [ "$rc" -eq 0 ] || fails=$((fails + 1))
  return 0
}
for tag in $TAGS; do
  [ "$(cat "$RES/build-$tag.done" 2>/dev/null)" = ok ] || { echo "$tag | (all) | ? | skipped | build-$tag.done is not ok" >>"$RES/tests.txt"; fails=$((fails + 1)); continue; }
  tagsha=$(grep -oE '^tip [0-9a-f]{40}' "$RES/build-$tag.txt" 2>/dev/null | cut -d' ' -f2)
  [ -n "$tagsha" ] && [ "$(git -C "/var/tmp/jhan/tron-$tag" rev-parse HEAD 2>/dev/null)" = "$tagsha" ] || { echo "$tag | (all) | ? | skipped | worktree not at the built sha ${tagsha:-?}" >>"$RES/tests.txt"; fails=$((fails + 1)); continue; }
  run_test "$tag" t_k_vnni_layout t_k_vnni_layout ""
  run_test "$tag" t_amx_numerics t_amx_numerics ""
  run_test "$tag" t_amx_dispatch_dtype t_amx_dispatch_dtype ""
  run_test "$tag" t_llama_unit t_llama_unit ""
  run_test "$tag" t_heterogeneous_scheduler t_heterogeneous_scheduler ""
done
case " $TAGS " in *" bp2v "*) run_test bp2v t_amx_numerics-killswitch t_amx_numerics "TRON_AMX_DISABLE=1" killswitch ;; esac
case " $TAGS " in *" bp4v "*) run_test bp4v t_llama_unit-killswitch t_llama_unit "TRON_AMX_DISABLE=1" ;; esac
cat "$RES/tests.txt"
mark "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")"
[ $fails -eq 0 ]
