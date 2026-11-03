#!/usr/bin/env bash
# pr5047-20261020 tests (runs ON delphi-3bda, called by chain.sh step T): the three AMX test binaries of the two HEAD builds
# (b47h = PR 5047 head with TRON_K_VNNI OFF, b47hv = the same commit with the option ON) on our half of the machine (fake
# device through SYSTEM_CONFIG="--instance 1,2", pinned to our cpus), plus t_amx_numerics of b47h a second time under the
# kill switch (TRON_AMX_DISABLE=1: the AMX kernel cases must WARN-skip with "AMX unavailable"). Fork of
# exec/glimext-20261018/tests.sh: two tags, no preservation check.
# Usage (on 3bda): SHA=<full sha of the head> bash tests.sh   [TEST_ARGS=--skip-benchmarks] [TAGS="b47h b47hv"]
# Log: exec/logs/pr5047-20261020-tests.log. Marker: exec/results/pr5047-20261020/tests.done = "ok" or "failed-<n>".
# Outputs: exec/results/pr5047-20261020/{tests.txt,tests/<tag>-<name>.log}.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
SHA=${SHA:?SHA=<full 40-hex commit sha of the head> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5047-20261020
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-tests.log
TAGS=${TAGS:-"b47h b47hv"}
OUR_CPUS=72-143,216-287
TEST_ARGS=${TEST_ARGS:---skip-benchmarks}
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/tests" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/tests.done"; echo "=== tests finished $(ts): $1 ==="; }
rm -f "$RES/tests.done"
echo "=== tests started $(ts) pid $$ on $(hostname) sha=$SHA tags=[$TAGS] args=[$TEST_ARGS] ==="
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
: >"$RES/tests.txt"
echo "# tag | test name | assertions | rc   (head $SHA; SYSTEM_CONFIG=--instance 1,2 on cpus $OUR_CPUS; args $TEST_ARGS)" >>"$RES/tests.txt"
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
  ( cd "$wt" && nice -n10 taskset -c "$OUR_CPUS" env SYSTEM_CONFIG="--instance 1,2" $extra timeout -k 60 3600 "$wt/gen/$bin" $TEST_ARGS ) >"$out" 2>&1
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
  [ "$(git -C "/var/tmp/jhan/tron-$tag" rev-parse HEAD 2>/dev/null)" = "$SHA" ] || { echo "$tag | (all) | ? | skipped | worktree not at $SHA" >>"$RES/tests.txt"; fails=$((fails + 1)); continue; }
  run_test "$tag" t_amx_numerics t_amx_numerics ""
  run_test "$tag" t_amx_dispatch_dtype t_amx_dispatch_dtype ""
  run_test "$tag" t_llama_unit t_llama_unit ""
done
run_test b47h t_amx_numerics-killswitch t_amx_numerics "TRON_AMX_DISABLE=1" killswitch
cat "$RES/tests.txt"
mark "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")"
[ $fails -eq 0 ]
