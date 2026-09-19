#!/usr/bin/env bash
# Integration test of wait_clear in exec/vnnik2-20260915/campaign.sh after the 2026-09-15
# change: the takeover must be tried only when the blocker is exactly "rinzler@N unit
# active", a successful takeover must re-check without sleeping, and a failed takeover must
# fall back to the 120 s sleep. campaign.sh is sourced from a sandbox copy whose EXEC points
# into a scratch directory, so nothing under exec/results or exec/logs is touched.
# Note: wait_clear calls blocked inside $(...), a subshell, so the scripted sequence of
# blocked() answers is indexed through a file, not a shell variable.
set -u
SRC=${SRC:-/home/jhan/workspace/intel-AMX/exec}
T=$(mktemp -d)
mkdir -p "$T/exec/vnnik2-20260915"
cp "$SRC/lib-guard.sh" "$T/exec/lib-guard.sh"
sed "s#^EXEC=/home/jhan/workspace/intel-AMX/exec\$#EXEC=$T/exec#" "$SRC/vnnik2-20260915/campaign.sh" >"$T/exec/vnnik2-20260915/campaign.sh"
grep -q "^EXEC=$T/exec\$" "$T/exec/vnnik2-20260915/campaign.sh" || { echo "sandbox EXEC substitution failed"; exit 2; }
VNNIK2_FUNCTIONS_ONLY=1 NAME=wait-clear-test source "$T/exec/vnnik2-20260915/campaign.sh"

# ---- stubs ----
BLOCKED_SEQ=(); BI=$T/blocked-index
blocked() {  # prints the next scripted reason; an empty entry means "clear" (return 1). Runs in a subshell.
  local i r; i=$(cat "$BI"); echo $((i + 1)) >"$BI"
  r=${BLOCKED_SEQ[$i]:-}
  [ -n "$r" ] && { echo "$r"; return 0; }
  return 1
}
TAKEOVER_SEQ=(); TAKEOVER_I=0; TAKEOVER_CALLS=0
rinzler_takeover_if_idle() {
  TAKEOVER_CALLS=$((TAKEOVER_CALLS + 1))
  local r=${TAKEOVER_SEQ[$TAKEOVER_I]:-1}; TAKEOVER_I=$((TAKEOVER_I + 1))
  return "$r"
}
SLEEP_CALLS=0; sleep() { SLEEP_CALLS=$((SLEEP_CALLS + 1)); }
STATUS_LINES=(); status() { STATUS_LINES+=("$*"); }

PASS=0; FAIL=0
run() {  # run <name> <want_takeover_calls> <want_sleep_calls>
  local name=$1 want_t=$2 want_s=$3 ok=1
  echo 0 >"$BI"; TAKEOVER_I=0; TAKEOVER_CALLS=0; SLEEP_CALLS=0; STATUS_LINES=()
  timeout 20 bash -c 'exit 0' >/dev/null 2>&1   # keep a real timeout binary reachable for the guard below
  wait_clear || { echo "  [$name] wait_clear returned nonzero"; ok=0; }
  [ "$TAKEOVER_CALLS" = "$want_t" ] || { echo "  [$name] takeover calls=$TAKEOVER_CALLS want $want_t"; ok=0; }
  [ "$SLEEP_CALLS" = "$want_s" ] || { echo "  [$name] sleep calls=$SLEEP_CALLS want $want_s"; ok=0; }
  [ "${#STATUS_LINES[@]}" -le 1 ] || { echo "  [$name] status written ${#STATUS_LINES[@]} times, want at most 1"; ok=0; }
  if [ $ok = 1 ]; then PASS=$((PASS + 1)); echo "PASS $name"; else FAIL=$((FAIL + 1)); echo "FAIL $name"; fi
}

BLOCKED_SEQ=(""); run already_clear 0 0

BLOCKED_SEQ=("rinzler@N unit active" ""); TAKEOVER_SEQ=(0)
run rinzler_takeover_succeeds_no_sleep 1 0

BLOCKED_SEQ=("rinzler@N unit active" "rinzler@N unit active" "rinzler@N unit active" ""); TAKEOVER_SEQ=(1 1 0)
run rinzler_busy_twice_then_taken 3 2

BLOCKED_SEQ=("CI lease busy" ""); TAKEOVER_SEQ=(0)
run lease_busy_never_takes_over 0 1

BLOCKED_SEQ=("pre-CI hold (01:40-03:45 UTC)" ""); TAKEOVER_SEQ=(0)
run preci_hold_never_takes_over 0 1

BLOCKED_SEQ=("CI lease busy" "rinzler@N unit active" ""); TAKEOVER_SEQ=(0)
run lease_then_leftover_rinzler 1 1

rm -rf "$T"
echo "== $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
