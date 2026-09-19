#!/usr/bin/env bash
# Tests for exec/bill-share.sh. A sandbox copy of the script sources a fake lib-guard.sh whose
# other_user_active answers from the BILL_ACTIVE variable; sudo is a pass-through function;
# the marker and the log live in a temp dir. So the test runs on any host and touches nothing.
# Protocol under test: "take" removes the marker only when Bill is idle (exit 2 and marker kept
# when he is active); "release" re-creates it; both are idempotent; the activity check is
# restricted to the user bill.
set -u
SCRIPT=${SCRIPT:-/home/jhan/workspace/intel-AMX/exec/bill-share.sh}
T=$(mktemp -d)
mkdir -p "$T/exec/logs"
cat >"$T/exec/lib-guard.sh" <<'FAKE'
other_user_active() { echo "fake other_user_active users=${GUARD_OTHER_USERS:-unset} excl=${GUARD_EXCLUDE_USERS:-unset} active=${BILL_ACTIVE:-0}" >&2; [ "${BILL_ACTIVE:-0}" = 1 ]; }
FAKE
sed "s#^EXEC=/home/jhan/workspace/intel-AMX/exec\$#EXEC=$T/exec#" "$SCRIPT" >"$T/bill-share.sh"
grep -q "^EXEC=$T/exec\$" "$T/bill-share.sh" || { echo "sandbox EXEC substitution failed"; exit 2; }
export BILL_MARKER=$T/bill-has-instance-0,2 BILL_SHARE_LOG=$T/exec/logs/bill-share.log

run() {  # run <bill_active 0|1> <command> -> prints the script's output (stdout+stderr), returns its exit code
  BILL_ACTIVE=$1 bash -c 'set -u; sudo() { [ "${1:-}" = -n ] && shift; "$@"; }; source "$0" "$1"' "$T/bill-share.sh" "$2" 2>&1
}
PASS=0; FAIL=0
check() {  # check <name> <want_rc> <want_marker 0|1> <want_substring> <rc> <out>
  local name=$1 want_rc=$2 want_m=$3 want_out=$4 rc=$5 out=$6 ok=1 have_m
  [ -e "$BILL_MARKER" ] && have_m=1 || have_m=0
  [ "$rc" = "$want_rc" ] || { echo "  [$name] rc=$rc want $want_rc"; ok=0; }
  [ "$have_m" = "$want_m" ] || { echo "  [$name] marker exists=$have_m want $want_m"; ok=0; }
  [[ "$out" == *"$want_out"* ]] || { echo "  [$name] output lacks '$want_out':"; echo "$out" | sed 's/^/    | /'; ok=0; }
  if [ $ok = 1 ]; then PASS=$((PASS + 1)); echo "PASS $name"; else FAIL=$((FAIL + 1)); echo "FAIL $name"; fi
}

rm -f "$BILL_MARKER"
out=$(run 0 release); check release_creates_marker 0 1 "release: created" $? "$out"
out=$(run 0 release); check release_idempotent 0 1 "already present" $? "$out"
out=$(run 0 status);  check status_present_idle 0 1 "Bill is idle now" $? "$out"
[[ "$out" == *"users=bill excl=jhan nobody positron packer"* ]] && { PASS=$((PASS + 1)); echo "PASS activity_check_restricted_to_bill"; } || { FAIL=$((FAIL + 1)); echo "FAIL activity_check_restricted_to_bill: $out"; }
out=$(run 1 status);  check status_present_active 0 1 "Bill is ACTIVE now" $? "$out"
out=$(run 1 take);    check take_refused_when_bill_active 2 1 "take REFUSED" $? "$out"
out=$(run 0 take);    check take_removes_when_idle 0 0 "take: removed" $? "$out"
out=$(run 1 take);    check take_idempotent_even_if_active 0 0 "already absent" $? "$out"
out=$(run 0 status);  check status_absent 0 0 "marker absent" $? "$out"
out=$(run 0 bogus);   check usage_error 64 0 "usage:" $? "$out"
n=$(grep -c . "$BILL_SHARE_LOG")
if [ "$n" -ge 8 ]; then PASS=$((PASS + 1)); echo "PASS log_has_${n}_lines"; else FAIL=$((FAIL + 1)); echo "FAIL log lines=$n want >= 8"; fi

rm -rf "$T"
echo "== $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
