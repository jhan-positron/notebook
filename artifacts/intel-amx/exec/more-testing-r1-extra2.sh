#!/usr/bin/env bash
# Second extra stage for round 1: a 20-minute soak on the OFF arm with the same
# two models and 25 users, as the host-memory baseline for the mirror soak
# (which grew host memory by ~40 GiB while the K mirror arena filled). Runs
# after more-testing-r1-extra.sh and only if the 02:30Z deadline allows.
set -u
EXEC=~/workspace/intel-AMX/exec
H=$EXEC/more-testing-r1
RES=$EXEC/results/more-testing-r1
LOG=$EXEC/logs/more-testing-r1.log
MARKER=$EXEC/logs/more-testing-r1-extra2.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== extra2 queued $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
source "$H/rz.sh"
status() { python3 "$H/gen_status.py" 2>&1 | tail -1; }
while [ ! -e "$EXEC/logs/more-testing-r1-extra.done" ]; do sleep 60; done
echo "=== extra2 start $(date -u +%FT%TZ) (extra marker: $(cat "$EXEC/logs/more-testing-r1-extra.done")) ==="
trap '[ -e "$MARKER" ] || { rz_stop; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; status; }' EXIT
if pgrep -x 'rinzler(\.[a-z0-9]+)?' >/dev/null; then echo "a rinzler is still running"; echo busy >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
DEADLINE=$(date -u -d "02:30" +%s); [ "$DEADLINE" -le "$(date -u +%s)" ] && DEADLINE=$(date -u -d "tomorrow 02:30" +%s)
stop_now() { local now; now=$(date -u +%s); [ $((now + $1 + 300)) -ge "$DEADLINE" ] && { echo "CLOCK-STOP (est $1 s)"; return 0; }; ci_took_dut && { echo CI-TOOK-DUT; return 0; }; rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
if stop_now 1700; then mkdir -p "$RES/soak__off20"; echo skipped >"$RES/soak__off20/STATUS"; status
else
  echo "### soak arm=off minutes=20 users=25 tag=off20 $(date -u +%FT%TZ)"
  bash "$H/soak_cell.sh" off 20 25 off20; echo "soak rc=$?"
  status
  echo "### done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
fi
campaign_guard_release
echo ok >"$MARKER"
status
echo "=== extra2 done $(date -u +%FT%TZ) ==="
