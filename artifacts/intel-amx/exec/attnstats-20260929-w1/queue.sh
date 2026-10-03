#!/usr/bin/env bash
# attnstats-20260929-w1 (runs ON delphi-3bda): wait until the nightly CI lease is clear and no other person is
# active (lib-guard.sh wait_for_dut_free; jhan and bill are excluded), then hold the campaign flock while
# build-test.sh <commit> runs (incremental build of PR #4596 + the unit tests on our half), so the i4500 chain's
# steps C/D (which take the same flock) cannot overlap the tests. Agreed with the i4500 session on 2026-09-29.
# The flock is taken with --allow-serving: production serving stays up, the tests use the fake device.
# TRAP (2026-09-29 03:36Z): launched before the nightly's lease file existed, wait_for_dut_free returned at once and the build
# started 2 min before the CI; killed by hand. Hence NOT_BEFORE (default 13:00Z, the nightly's lease clears ~13:20Z) and a
# 600 s lease grace, the same gate as exec/i4500fix-20260928/chain.sh.
# Usage: [NOT_BEFORE=2026-09-29T13:00:00Z] queue.sh <commit>
set -u
NOT_BEFORE=${NOT_BEFORE:-2026-09-29T13:00:00Z}
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=attnstats-20260929-w1
RES=$EXEC/results/$NAME; LOG=$EXEC/logs/$NAME-queue.log
COMMIT=${1:?commit}
mkdir -p "$EXEC/logs" "$RES"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }; say() { echo "$(ts) $*"; }
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
export GUARD_RUNTRON_USER=jhan
source "$EXEC/lib-guard.sh"
say "=== queue started pid $$ commit $COMMIT on $(hostname): NOT_BEFORE $NOT_BEFORE, then the DUT (CI lease + 600 s grace, other users, blackout), up to 12 h ==="
nb=$(date -u -d "$NOT_BEFORE" +%s) || { say "bad NOT_BEFORE '$NOT_BEFORE'"; exit 1; }
while [ "$(date -u +%s)" -lt "$nb" ]; do sleep 60; done
say "NOT_BEFORE passed"
deadline=$(( $(date +%s) + 43200 ))
while ci_lease_busy 600 || other_user_active 2>/dev/null || blackout_active; do
  [ "$(date +%s)" -ge "$deadline" ] && { say "TIMEOUT: the DUT stayed busy for 12 h; not building"; echo timeout >"$RES/.queue-timeout"; exit 1; }
  sleep 300
done
say "DUT free"
n=0
until campaign_guard_acquire --allow-serving; do
  n=$((n + 1)); [ $n -gt 360 ] && { say "guard refused for 6 h; giving up"; exit 1; }
  sleep 60
done
say "campaign flock held (--allow-serving); launching build-test.sh $COMMIT"
bash "$EXEC/$NAME/build-test.sh" "$COMMIT"; rc=$?
campaign_guard_release
say "=== queue finished (build-test exit $rc), flock released ==="
