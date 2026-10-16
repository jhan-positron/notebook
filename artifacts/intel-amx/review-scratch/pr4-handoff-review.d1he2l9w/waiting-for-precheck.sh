set -u
trace() { printf '%s\n' "$*" >>"$TRACE_FILE"; }
wait_dut() { trace "wait_dut $*"; return 0; }
status() { :; }
say() { :; }
dut_retry_ssh() { trace "dut_retry_ssh $*"; return 0; }
dut_retry() { trace "dut_retry $*"; echo '2026.10.12-restore sha'; }
bill() { trace "bill $*"; return 0; }
release_lock() { trace release_lock; }
timeout() { trace "timeout $*"; echo 0; }
lease_state() { trace 'lease_state busy'; echo busy; }
ci_lease_busy() { trace 'ci_lease_busy true'; return 0; }
SSH_OPTS= DUT_ALIAS=delphi-3bda
RESTORED=0 problems= LOCK_STILL_HELD=0 HANDOFF=up
RESTORE_SHA=sha RESTORE_FILE=restore.deb
restore_and_release() {
  [ "$RESTORED" = 1 ] && return 0; RESTORED=1
  # the DUT outage that stopped the campaign may still last: wait for it (bounded 30 min), then retry ssh-level failures
  wait_dut 1800 || { problems="$problems DUT-UNREACHABLE"; status "RESTORE: DUT unreachable for 30 min; steps below will fail; see the RECOVERY sequence in the header"; }
  # config.env FIRST: production engines must never start with USE_HW_ATTN=0 (they would run software attention)
  if [ "$HWATTN_SET" = 1 ]; then
    if dut_retry_ssh 120 hwattn-clear; then HWATTN_SET=0; say "hwattn-clear ok: config.env 0 bytes"
    else
      local cb; cb=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null)
      if [ "$cb" = 0 ]; then HWATTN_SET=0; say "hwattn-clear reported a failure but config.env is 0 bytes: treated as cleared"
      else problems="$problems HWATTN-CLEAR-FAILED"; status "HWATTN-CLEAR FAILED (config.env ${cb:-unread} bytes): USE_HW_ATTN=0 may still be set; production is NOT brought up (jhan: sudo truncate -s 0 /opt/positron/user/config.env, then dut.sh serving-down, serving-up)"; fi
    fi
  fi
  if [ -n "$RESTORE_VERSION" ]; then
    local restored=0
    if dut_retry_ssh 900 ensure-base "$RESTORE_VERSION" "$RESTORE_SHA" "$RESTORE_FILE"; then restored=1; status "restore ok: $(dut_retry 120 installed)"; else problems="$problems RESTORE-FAILED"; status "RESTORE FAILED: $(dut_retry 120 installed) (wanted $RESTORE_VERSION from $RESTORE_FILE); jhan must reinstall tron by hand"; fi
    if [ "$HANDOFF" = up ] && [ $restored = 1 ] && [ "$HWATTN_SET" = 0 ]; then
      # engines of the last pass still run the deleted binary until restarted: down, then up (skip up when down failed)
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then dut_retry_ssh 900 serving-up || { problems="$problems SERVING-UP-FAILED"; say "WARNING serving-up did not complete"; }
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log); engines may still run a deleted binary"; fi
    elif [ "$HANDOFF" = up ]; then
      # never bring production up on a binary that is not the nightly's, or with USE_HW_ATTN=0 still in config.env: down only, jhan decides
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "restore failed or config.env not cleared: production engines taken DOWN (not brought up)"; else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: restore failed (or config.env not cleared) and serving-down failed"; fi
    else
      if DUT_ENV="IDLE_MIN=5" dut_retry_ssh 1500 serving-down; then status "handoff: production engines down, hugepages free"
      else problems="$problems HANDOFF-INCOMPLETE"; status "HANDOFF INCOMPLETE: serving-down failed (see log)"; fi
    fi
    local cfgbytes n
    for n in 1 2 3; do cfgbytes=$(timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" 'stat -c %s /opt/positron/user/config.env' 2>/dev/null); [ -n "$cfgbytes" ] && break; sleep 30; done
    if [ "$cfgbytes" = 0 ]; then say "config.env is 0 bytes (ok)"; else problems="$problems CONFIG-ENV-${cfgbytes:-unread}-BYTES"; say "WARNING: /opt/positron/user/config.env has '${cfgbytes:-unread}' bytes (must be 0)"; fi
  else
    say "no restore target recorded (aborted before preflight): nothing to restore"
  fi
  local rel_out rel_rc n
  for n in 1 2 3; do rel_out=$(bill release 2>&1); rel_rc=$?; [ "$rel_rc" -eq 0 ] && break; say "bill release attempt $n rc=$rel_rc"; sleep 30; done
  printf '%s\n' "$rel_out" | tail -1
  [ "$rel_rc" -eq 0 ] || { problems="$problems MARKER-NOT-RELEASED"; say "WARNING: bill-share release rc=$rel_rc; run bill-share.sh release by hand"; }
  release_lock
  [ "$LOCK_STILL_HELD" = 1 ] && problems="$problems FLOCK-STILL-HELD"
}
RESTORE_VERSION= HWATTN_SET=0
restore_and_release
