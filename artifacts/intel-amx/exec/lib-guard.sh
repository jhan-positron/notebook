#!/usr/bin/env bash
# Shared launch guards for AMX campaigns on delphi-3bda. Source this from
# every campaign script:   . ~/workspace/intel-AMX/exec/lib-guard.sh
#
# Authority order (2026-08-19, per Rhys's systems_test PR #180 + jhan):
#   1. CI lease  /run/lock/systems-test-ci.lease  - AUTHORITATIVE for
#      "is System CI holding the DUT right now". Busy only if the file
#      exists AND state == "busy" AND now < expires_at_epoch. Missing,
#      non-busy, or expired => CI is not holding: rinzler cleanup, hugepage
#      cleanup, and FPGA claiming are allowed.
#   2. Cross-session campaign flock /var/tmp/jhan/3bda-campaign.lock
#      (adopted from the trace-sync-points session) + no-runtron launch guard.
#   3. The clock window (nightly prep ~03:30Z) is ADVISORY only: the lease
#      says "holding now", not "starts in five minutes" - so long campaigns
#      must re-check ci_lease_busy between runs and stop when it turns busy.

ci_lease_busy() {
  python3 - <<'PY'
import json, re, sys, time
p = '/run/lock/systems-test-ci.lease'
try:
    raw = open(p).read()
except OSError:
    sys.exit(1)  # no file -> not busy
state, exp = '', 0.0
try:
    d = json.loads(raw)
    state = str(d.get('state', '')).strip().lower()
    exp = float(d.get('expires_at_epoch', 0))
except Exception:
    m = re.search(r'state["\s:=]+([A-Za-z_-]+)', raw)
    if m: state = m.group(1).lower()
    m = re.search(r'expires_at_epoch["\s:=]+(\d+(?:\.\d+)?)', raw)
    if m: exp = float(m.group(1))
sys.exit(0 if (state == 'busy' and time.time() < exp) else 1)
PY
}

# Take the cross-session lock and verify no runtron is running. Uses a
# DYNAMICALLY allocated file descriptor (bash 4.1+), stored in
# $CAMPAIGN_LOCK_FD, so sourcing this never collides with a script's own
# fds (a hardcoded fd 9 bit the trace-sync-points harness on 2026-08-19).
# Returns nonzero (with a message) if the machine is not launchable.
campaign_guard_acquire() {
  if ci_lease_busy; then echo "GUARD: System CI holds the DUT (lease busy)"; return 1; fi
  exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
  if ! flock -n "$CAMPAIGN_LOCK_FD"; then
    echo "GUARD: campaign flock held by another session"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  if pgrep -x runtron >/dev/null; then
    echo "GUARD: runtron already running"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  # Production serving check (added 2026-08-19 after the peakbw handback
  # restored live rinzler serving): campaigns must not launch next to active
  # serving unless the script deliberately implements a stop-and-restore flow
  # and says so by passing --allow-serving.
  if [ "${1:-}" != "--allow-serving" ] && rinzler_active; then
    echo "GUARD: rinzler serving is active (pass --allow-serving only if your script stops and restores it)"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  return 0
}

rinzler_active() {
  systemctl is-active --quiet rinzler@0 || systemctl is-active --quiet rinzler@1 ||   systemctl is-active --quiet rinzler@2 || systemctl is-active --quiet rinzler@3
}

campaign_guard_release() {
  if [ -n "${CAMPAIGN_LOCK_FD:-}" ]; then
    flock -u "$CAMPAIGN_LOCK_FD" 2>/dev/null || true
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
  fi
}

# Between-runs check: stop the campaign if CI has taken the DUT.
ci_took_dut() { ci_lease_busy; }

# Wait until CI releases the DUT (poll every 5 min, up to $1 seconds,
# default 6 h). Returns nonzero on timeout.
wait_for_ci_release() {
  local deadline=$(( $(date +%s) + ${1:-21600} ))
  while ci_lease_busy; do
    [ "$(date +%s)" -ge "$deadline" ] && return 1
    sleep 300
  done
  return 0
}
