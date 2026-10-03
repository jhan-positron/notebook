#!/usr/bin/env bash
# attnstats-20260925-review (runs ON delphi-3bda): wait until the nightly CI lease is clear and no other
# person is active on the host (lib-guard.sh: wait_for_dut_free), then run build-test.sh <commit>
# (incremental build of PR #4596 in /var/tmp/jhan/tron-attn-head + the unit tests on our half).
# The previous run's results move to results/<name>-<prev commit> first, the convention of this round.
# Usage: queue-after-ci.sh <commit> [<previous commit>]
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=attnstats-20260925-review
RES=$EXEC/results/$NAME; LOG=$EXEC/logs/$NAME-queue.log
COMMIT=${1:?commit}; PREV=${2:-}
mkdir -p "$EXEC/logs"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }; say() { echo "$(ts) $*"; }
source "$EXEC/lib-guard.sh"
say "=== queue started pid $$ commit $COMMIT on $(hostname): waiting for the DUT (CI lease, other users, blackout), up to 12 h ==="
if wait_for_dut_free 43200; then
  say "DUT free"
else
  say "TIMEOUT: the DUT stayed busy for 12 h; not building"
  echo timeout >"$RES.queue-timeout"; exit 1
fi
if [ -n "$PREV" ] && [ -d "$RES" ] && [ ! -e "$RES-$PREV" ]; then
  mv "$RES" "$RES-$PREV" && say "previous results moved to $RES-$PREV"
fi
say "launching build-test.sh $COMMIT"
bash "$EXEC/$NAME/build-test.sh" "$COMMIT"
say "=== queue finished (build-test exit $?) ==="
