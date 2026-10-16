#!/usr/bin/env bash
# The exit handler of the pr3-20261012 chain (PR3-handoff.md step 6, "The exit handler"). Sourced by chain.sh and,
# with stubs, by cleanup-test.sh. It needs these names from the sourcing script: ts, machine, DUT (dut.sh path),
# BILL_SHARE (bill-share.sh path), OUR_RT_RE (regex of our runtron binaries' command lines), NAME, and the two
# flags MARKER_TAKEN and SERVING_DOWN_BY_US, plus ci_lease_busy and rinzler_active (lib-guard.sh or stubs).
# Order: stop this chain's remaining workload and wait for it; restore serving when this chain took it down,
# unless the CI lease is busy or the units are already active; release Bill's marker when this chain took it;
# print the machine line. FINISHED guards against a second run (the TERM trap and the EXIT trap both call it).
FINISHED=0
stop_workload() {  # TERM our runtron binaries (user jhan, the three arms' paths), wait up to 60 s, then KILL; drop our unmapped hugepage files
  local pids n
  pids=$(pgrep -u jhan -f "$OUR_RT_RE" | tr '\n' ' ')
  if [ -n "$pids" ]; then
    echo "$(ts) finish: TERM our runtron pids $pids"; pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null
    for n in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
    pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: KILL to our runtron"; sleep 2; }
  else
    echo "$(ts) finish: no runtron of ours running"
  fi
  local f
  for f in ${HUGEPAGES_DIR:-/dev/hugepages}/slice-*-of-8 ${HUGEPAGES_DIR:-/dev/hugepages}/amx-$NAME*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) finish: removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
restore_serving() {
  if [ "$SERVING_DOWN_BY_US" != 1 ]; then echo "$(ts) finish: serving: this chain did not take it down, nothing to restore"; return 0; fi
  if ci_lease_busy 600; then echo "$(ts) finish: serving: CI lease busy, left alone"; return 0; fi
  if rinzler_active; then echo "$(ts) finish: serving: rinzler units active, nothing to bring up"; return 0; fi
  echo "$(ts) finish: serving-up through platformd (dut.sh serving-up)"
  timeout 900 bash "$DUT" serving-up || echo "$(ts) finish: serving-up rc=$? (jhan: check platformd)"
}
release_marker() {
  if [ "$MARKER_TAKEN" = 1 ]; then bash "$BILL_SHARE" release 2>&1 | tail -1; echo "$(ts) finish: Bill marker released"
  else echo "$(ts) finish: marker not taken by this chain, nothing to release"; fi
}
finish() {
  [ "$FINISHED" = 1 ] && return 0
  FINISHED=1
  trap '' TERM
  echo "$(ts) finish: begin (reason: ${1:-exit})"
  stop_workload
  restore_serving
  release_marker
  echo "$(ts) machine at exit: $(machine)"
}
