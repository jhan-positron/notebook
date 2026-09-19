#!/usr/bin/env bash
# wedperf-20260916 build driver (run ON delphi-3bda, detached by launch-builds.sh):
#   1. wait until the nightly CI releases the lease (/run/lock/systems-test-ci.lease)
#   2. build.sh: runtron.pre3879 from main eb2de0265a = the main commit just before PR #3879
#      merged (first parent of the merge commit 3fd5edaa66); no AMX code exists there, so no
#      AMX option is passed; production-tagged models included for the CI perf list
#   3. build.sh: runtron.pr4424 from the PR #4424 head ff680c8020 with TRON_AMX_DISPATCH=ON
#      and TRON_K_VNNI=ON (the layout the PR proposes), production-tagged models included
# The campaign (campaign.sh) is launched separately and waits for the two build markers.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
RES=$EXEC/results/wedperf-20260916
LOG=$EXEC/logs/wedperf-build-chain.log
BASE_COMMIT=eb2de0265a2fb6bed64a289079f75129c8cc2d40      # main just before the PR #3879 merge (parent 1 of 3fd5edaa66)
HEAD_COMMIT=ff680c80201926907189bf803e6eb44b6717399e      # PR #4424 head
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== wedperf build-chain.sh started $(ts) pid $$ base=$BASE_COMMIT head=$HEAD_COMMIT ==="
# stale markers of an earlier build must not let a campaign.sh launched during the lease wait pass
# phase 1 on the old binaries or end on an old failure: remove both before waiting. Run
# launch-builds.sh BEFORE launch-campaign.sh (campaign.sh reads the markers at once on start).
rm -f "$RES/build-pre3879.done" "$RES/build-pr4424.done"
while ci_lease_busy; do echo "$(ts) CI lease busy; chain waits"; sleep 120; done
echo "$(ts) CI lease free; step 2: build pre3879"
SKIP_LEASE_WAIT=1 EXPECT_K_VNNI=OFF EXPECT_AMX_DISPATCH=OFF bash "$C/build.sh" "$BASE_COMMIT" /var/tmp/jhan/tron-pre3879 pre3879 -DBUILD_PRODUCTION_MODELS=ON; rc=$?
[ -s "$RES/build-pre3879.done" ] || echo "build-failed rc=$rc (build.sh left no marker)" >"$RES/build-pre3879.done"
echo "$(ts) step 2 done: $(cat "$RES/build-pre3879.done")"
echo "$(ts) step 3: build pr4424 (build.sh re-checks the lease first)"
EXPECT_K_VNNI=ON EXPECT_AMX_DISPATCH=ON bash "$C/build.sh" "$HEAD_COMMIT" /var/tmp/jhan/tron-pr4424 pr4424 -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DBUILD_PRODUCTION_MODELS=ON; rc=$?
[ -s "$RES/build-pr4424.done" ] || echo "build-failed rc=$rc (build.sh left no marker)" >"$RES/build-pr4424.done"
echo "$(ts) step 3 done: $(cat "$RES/build-pr4424.done")"
echo "=== wedperf build-chain.sh finished $(ts) ==="
