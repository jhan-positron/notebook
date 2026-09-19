#!/usr/bin/env bash
# Unit tests for rinzler_takeover_if_idle and the ci_lease_busy grace argument in
# exec/lib-guard.sh (revision of 2026-09-15).
# Every external command the function calls (systemctl, sudo, stat, fuser, sleep) is
# replaced by a bash function here, so the test runs on any host. The tests check the
# one thing that matters: `systemctl stop rinzler@0..3` fires only when the lease is free
# for more than 600 s AND no blackout window is open AND the UTC time is outside the
# 01:40-04:30 hold AND this process did not stop the units in the last 6 h AND every
# active unit has been active for at least 10 min AND the journal is readable and shows
# no requests and no non-idle stats (or is empty with an idle stats line last) AND no
# remote connection exists. Everything else must fail closed (return 1, no stop).
set -u
LIB=${LIB:-/home/jhan/workspace/intel-AMX/exec/lib-guard.sh}
T=$(mktemp -d)
export GUARD_HUGEPAGES_DIR=$T/hp
source "$LIB"
eval "real_$(declare -f ci_lease_busy)"   # keep the real lease reader for the grace tests

IDLE='#EVT# SYSTEM_STATS: Sessions: Open=0, Closed=0, Busy=0, Total=485; Tokens: Prompted=1, Generated=2'
# ---- knobs (reset by reset_case) ----
reset_case() {
  ACTIVE=1; LEASE_BUSY=0; LEASE_FIXTURE=""; BLACKOUT=0; HHMM=1300; GUARD_TAKEOVER_LAST=0
  UNIT_AGE_S=3600; UNIT_AGE_UNREADABLE=0
  JOURNAL_RC=0; JOURNAL="$IDLE"$'\n'"$IDLE"; JOURNAL_STDERR=""
  PROBE="$IDLE"
  SS_RC=0; SS_OUT=""; SS_FILTER=""
  STOP_RC=0; STOP_KEEPS_ACTIVE=0; STOP_CALLS=0; STOP_ARGS=""
  OWNER_POSITRON=""; MAPPED=""
  rm -rf "$GUARD_HUGEPAGES_DIR"; mkdir -p "$GUARD_HUGEPAGES_DIR"
}

# ---- stubs ----
ci_lease_busy() {  # LEASE_BUSY=1 forces busy; LEASE_FIXTURE=<file> runs the real reader on that file (grace tests)
  [ "$LEASE_BUSY" = 1 ] && return 0
  [ -n "$LEASE_FIXTURE" ] && { GUARD_LEASE_FILE=$LEASE_FIXTURE real_ci_lease_busy "$@"; return; }
  return 1
}
blackout_active() { [ "$BLACKOUT" = 1 ]; }
guard_utc_hhmm() { echo "$HHMM"; }
systemctl() {
  case "$1" in
    is-active) [ "$ACTIVE" = 1 ] ;;
    show)  # systemctl show -p ActiveEnterTimestamp --value rinzler@N
      [ "$UNIT_AGE_UNREADABLE" = 1 ] && { echo ""; return 0; }
      date -u -d "@$(( $(date +%s) - UNIT_AGE_S ))" '+%a %Y-%m-%d %H:%M:%S UTC' ;;
    *) echo "unexpected direct systemctl $*" >&2; return 99 ;;
  esac
}
sudo() {
  [ "${1:-}" = -n ] && shift
  case "$1" in
    journalctl)
      case "$*" in
        *" -n 1 "*) printf '%s' "$PROBE"; return 0 ;;
        *) [ -n "$JOURNAL_STDERR" ] && echo "$JOURNAL_STDERR" >&2; printf '%s' "$JOURNAL"; return "$JOURNAL_RC" ;;
      esac ;;
    ss) SS_FILTER=${*: -1}; echo "$SS_FILTER" >"$T/ss-filter"; printf '%s\n' "$SS_OUT"; return "$SS_RC" ;;
    systemctl)
      STOP_CALLS=$((STOP_CALLS + 1)); STOP_ARGS="$*"
      [ "$STOP_RC" = 0 ] && [ "$STOP_KEEPS_ACTIVE" = 0 ] && ACTIVE=0
      return "$STOP_RC" ;;
    *) echo "unexpected sudo $*" >&2; return 99 ;;
  esac
}
sleep() { :; }
stat() {  # stat -c %U <file>
  local f=${*: -1} b; b=$(basename "$f")
  case " $OWNER_POSITRON " in *" $b "*) echo positron ;; *) echo jhan ;; esac
}
fuser() {  # fuser -s <file>: 0 = mapped/in use
  local b; b=$(basename "$2")
  case " $MAPPED " in *" $b "*) return 0 ;; *) return 1 ;; esac
}
lease_fixture() {  # lease_fixture <state> <expires_offset_s> -> writes a lease file, prints its path
  local f=$T/lease.json
  printf '{"state":"%s","owner":"system_ci","expires_at_epoch":%s}\n' "$1" "$(( $(date +%s) + $2 ))" >"$f"
  echo "$f"
}

# ---- runner ----
PASS=0; FAIL=0
check() {  # check <case> <expected_rc> <expected_stop_calls> [<expected substring in output>]
  local name=$1 want_rc=$2 want_stops=$3 want_out=${4:-} rc out
  rinzler_takeover_if_idle >"$T/out" 2>&1; rc=$?
  out=$(cat "$T/out")
  local ok=1
  [ "$rc" = "$want_rc" ] || { echo "  [$name] rc=$rc want $want_rc"; ok=0; }
  [ "$STOP_CALLS" = "$want_stops" ] || { echo "  [$name] stop calls=$STOP_CALLS want $want_stops"; ok=0; }
  if [ -n "$want_out" ] && [[ "$out" != *"$want_out"* ]]; then echo "  [$name] output lacks '$want_out'"; echo "$out" | sed 's/^/    | /'; ok=0; fi
  if [ $ok = 1 ]; then PASS=$((PASS + 1)); echo "PASS $name"; else FAIL=$((FAIL + 1)); echo "FAIL $name"; fi
}
with_lease() { local f=$1; shift; GUARD_LEASE_FILE=$f "$@"; }   # `env` cannot run a shell function
expect() {  # expect <name> <want_rc> <command...>
  local name=$1 want=$2; shift 2
  if "$@" >/dev/null 2>&1; then rc=0; else rc=$?; fi
  if [ "$rc" = "$want" ]; then PASS=$((PASS + 1)); echo "PASS $name"; else FAIL=$((FAIL + 1)); echo "FAIL $name (rc=$rc want $want)"; fi
}
assert() {  # assert <name> <condition...>
  local name=$1; shift
  if "$@"; then PASS=$((PASS + 1)); echo "PASS $name"; else FAIL=$((FAIL + 1)); echo "FAIL $name"; fi
}

# --- ci_lease_busy grace argument (real reader on fixture files) ---
reset_case
f=$(lease_fixture busy 500);   expect lease_valid_is_busy 0 with_lease "$f" real_ci_lease_busy
f=$(lease_fixture busy -100);  expect lease_expired_100s_not_busy_without_grace 1 with_lease "$f" real_ci_lease_busy
f=$(lease_fixture busy -100);  expect lease_expired_100s_busy_with_600s_grace 0 with_lease "$f" real_ci_lease_busy 600
f=$(lease_fixture busy -700);  expect lease_expired_700s_not_busy_with_600s_grace 1 with_lease "$f" real_ci_lease_busy 600
f=$(lease_fixture released -100); expect lease_released_not_busy_with_grace 1 with_lease "$f" real_ci_lease_busy 600
expect lease_missing_not_busy_with_grace 1 with_lease "$T/no-such-file" real_ci_lease_busy 600

# --- takeover: refusals ---
reset_case; ACTIVE=0
check not_active 0 0
[ -s "$T/out" ] && { echo "  [not_active] expected no output"; FAIL=$((FAIL + 1)); }

reset_case; LEASE_BUSY=1
check lease_busy 1 0 "CI lease busy or expired less than 600 s ago"
reset_case; LEASE_FIXTURE=$(lease_fixture busy -300)
check lease_expired_300s_ago_still_refused 1 0 "CI lease busy or expired less than 600 s ago"
reset_case; LEASE_FIXTURE=$(lease_fixture busy -900)
check lease_expired_900s_ago_allows 0 1 "all checks passed"

reset_case; BLACKOUT=1
check blackout_refuses 1 0 "blackout window"

reset_case; HHMM=140
check hold_starts_0140 1 0 "inside the 01:40-04:30 UTC hold"
reset_case; HHMM=345
check hold_covers_0345_gap 1 0 "inside the 01:40-04:30 UTC hold"
reset_case; HHMM=429
check hold_ends_after_0429 1 0 "inside the 01:40-04:30 UTC hold"
reset_case; HHMM=430
check hold_over_at_0430 0 1 "all checks passed"
reset_case; HHMM=139
check before_hold_0139_allows 0 1 "all checks passed"

reset_case; GUARD_TAKEOVER_LAST=$(( $(date +%s) - 3600 ))
check latch_refuses_within_6h 1 0 "stopped serving 60 min ago and units are active again"
reset_case; GUARD_TAKEOVER_LAST=$(( $(date +%s) - 21601 ))
check latch_open_after_6h 0 1 "all checks passed"
reset_case
check first_takeover_sets_latch 0 1 "all checks passed"
assert latch_recorded_after_stop [ "$GUARD_TAKEOVER_LAST" -gt 0 ]
ACTIVE=1; STOP_CALLS=0   # the units come back 1 s later: the same process must not stop them again
check second_takeover_same_process_refused 1 0 "units are active again, so someone started them"

reset_case; UNIT_AGE_S=300
check unit_younger_than_10min 1 0 "active for less than 10 min"
reset_case; UNIT_AGE_S=599
check unit_age_599s_is_young 1 0 "active for less than 10 min"
reset_case; UNIT_AGE_S=601
check unit_age_601s_is_old_enough 0 1 "all checks passed"
reset_case; UNIT_AGE_UNREADABLE=1
check unit_age_unreadable_counts_as_young 1 0 "active for less than 10 min"

# --- takeover: journal rules ---
reset_case; JOURNAL_RC=1; JOURNAL=""
check journal_fail 1 0 "journalctl failed (rc=1)"
reset_case; JOURNAL=""; PROBE=""
check journal_unreadable_no_last_line 1 0 "journal not readable (no last line)"
reset_case; JOURNAL=""; JOURNAL_STDERR="sudo: unable to resolve host delphi-3bda: Name or service not known"; PROBE="[info] Version: 1.2.3"
check stderr_warning_is_not_journal_text 1 0 "journal empty for the last 10 min and the last line is not an idle SYSTEM_STATS line"
reset_case; JOURNAL=""; PROBE="$IDLE"
check empty_window_with_idle_last_line_is_idle 0 1 "window=empty,last-line=idle-stats"
reset_case; JOURNAL=""; PROBE='#EVT# SYSTEM_STATS: Sessions: Open=3, Closed=0, Busy=1, Total=9'
check empty_window_with_busy_last_line_refused 1 0 "last line is not an idle SYSTEM_STATS line"
reset_case; JOURNAL=""; PROBE="handling request id=7"
check empty_window_with_request_last_line_refused 1 0 "last line is not an idle SYSTEM_STATS line"
reset_case; JOURNAL="$IDLE"$'\n''handling request id=5 from 10.0.0.9'
check traffic_line 1 0 "journal-request-lines=1 non-idle-stats-lines=0"
reset_case; JOURNAL=$'#EVT# request accepted\n'"$IDLE"
check evt_lines_not_counted_as_traffic 0 1 "journal-request-lines=0"
reset_case; JOURNAL='#EVT# SYSTEM_STATS: Sessions: Open=25, Closed=27, Busy=0, Total=27'$'\n'"$IDLE"
check open_sessions_count_as_busy 1 0 "non-idle-stats-lines=1"

# --- takeover: connection rules ---
reset_case; SS_OUT="0      0      10.0.0.7:13000     10.0.0.9:51234"
check remote_conn 1 0 "remote-conns=1"
reset_case; SS_OUT="0      0      127.0.0.1:13000    127.0.0.1:51234"
check local_conn_ignored 0 1 "remote-conns=0"
reset_case; SS_RC=1
check ss_fail_counts_as_conn 1 0 "remote-conns=1"
reset_case; check ss_filter_probe 0 1
assert ss_filter_covers_platformd_range grep -q 'sport >= :3000 and sport <= :3020' "$T/ss-filter"
assert ss_filter_covers_engine_ports grep -q 'sport >= :13000 and sport <= :13020' "$T/ss-filter"

# --- takeover: the stop path ---
reset_case
for f in slice-0-of-8 slice-1-of-8 slice-2-of-8 slice-3-of-8 other-file; do : >"$GUARD_HUGEPAGES_DIR/$f"; done
OWNER_POSITRON="slice-0-of-8"          # the nightly's file -> removed
MAPPED="slice-2-of-8 slice-3-of-8"     # ours but still mapped -> kept; slice-1-of-8: ours, unmapped -> removed
check idle_stop_ok 0 1 "all checks passed, stopping rinzler@0..3"
[ "$STOP_ARGS" = "systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3" ] || { echo "  [idle_stop_ok] stop args: $STOP_ARGS"; FAIL=$((FAIL + 1)); }
[ ! -e "$GUARD_HUGEPAGES_DIR/slice-0-of-8" ] || { echo "  [idle_stop_ok] positron slice-0 not removed"; FAIL=$((FAIL + 1)); }
[ ! -e "$GUARD_HUGEPAGES_DIR/slice-1-of-8" ] || { echo "  [idle_stop_ok] our unmapped slice-1 not removed"; FAIL=$((FAIL + 1)); }
[ -e "$GUARD_HUGEPAGES_DIR/slice-2-of-8" ] || { echo "  [idle_stop_ok] our mapped slice-2 was removed"; FAIL=$((FAIL + 1)); }
[ -e "$GUARD_HUGEPAGES_DIR/slice-3-of-8" ] || { echo "  [idle_stop_ok] mapped slice-3 was removed"; FAIL=$((FAIL + 1)); }
[ -e "$GUARD_HUGEPAGES_DIR/other-file" ] || { echo "  [idle_stop_ok] non-slice file was removed"; FAIL=$((FAIL + 1)); }
grep -q "removed $GUARD_HUGEPAGES_DIR/slice-0-of-8 (rinzler@N stopped)" "$T/out" || { echo "  [idle_stop_ok] no removal line for slice-0"; FAIL=$((FAIL + 1)); }
grep -q "removed $GUARD_HUGEPAGES_DIR/slice-1-of-8 (unmapped, ours)" "$T/out" || { echo "  [idle_stop_ok] no removal line for slice-1"; FAIL=$((FAIL + 1)); }

reset_case; STOP_RC=1
: >"$GUARD_HUGEPAGES_DIR/slice-0-of-8"; OWNER_POSITRON="slice-0-of-8"
check stop_fails 1 1 "systemctl stop returned nonzero, slice files kept"
assert stop_fails_keeps_slice_file [ -e "$GUARD_HUGEPAGES_DIR/slice-0-of-8" ]

reset_case; STOP_KEEPS_ACTIVE=1
: >"$GUARD_HUGEPAGES_DIR/slice-0-of-8"; OWNER_POSITRON="slice-0-of-8"
check unit_active_again_after_stop 1 1 "active again after the stop, slice files kept"
assert active_again_keeps_positron_slice_file [ -e "$GUARD_HUGEPAGES_DIR/slice-0-of-8" ]

rm -rf "$T"
echo "== $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
