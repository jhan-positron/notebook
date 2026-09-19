#!/usr/bin/env bash
# vnnik6-20260916 driver: the whole after-CI campaign of PLAN.md in order, on delphi-3bda:
#   1. wait until the nightly CI releases the lease (/run/lock/systems-test-ci.lease)
#   2. build.sh: runtron.main0916 from main c7844ca2ce (TRON_AMX_DISPATCH=ON) into
#      /var/tmp/jhan/tron-main0916
#   3. build.sh: runtron.headoff0916 from the PR head ff680c8020 (TRON_AMX_DISPATCH=ON, the
#      layout option TRON_K_VNNI left off) into /var/tmp/jhan/tron-headoff0916
#   4. campaign.sh: smoke, cells, traces, summary (it waits for the two build markers itself)
# Every step writes to its own log; this driver logs the step boundaries to
# exec/logs/vnnik6-chain.log. The commits and options are fixed here on purpose: the campaign
# must measure exactly the binaries PLAN.md names.
# Usage (on delphi-3bda): nohup chain.sh &     (launch.sh does this)
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/vnnik6-20260916
RES=$EXEC/results/vnnik6-20260916
LOG=$EXEC/logs/vnnik6-chain.log
BASE_COMMIT=c7844ca2ceb73e59268b3fcfe3465c3cfae77325      # origin/main at the rebase = merge base of PR #4424
HEAD_COMMIT=ff680c80201926907189bf803e6eb44b6717399e      # PR #4424 head
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== vnnik6 chain.sh started $(ts) pid $$ base=$BASE_COMMIT head=$HEAD_COMMIT ==="
while ci_lease_busy; do echo "$(ts) CI lease busy; chain waits"; sleep 120; done
echo "$(ts) CI lease free; step 2: build base"
SKIP_LEASE_WAIT=1 EXPECT_K_VNNI=OFF bash "$C/build.sh" "$BASE_COMMIT" /var/tmp/jhan/tron-main0916 main0916 -DTRON_AMX_DISPATCH=ON; rc=$?
[ -s "$RES/build-main0916.done" ] || echo "build-failed rc=$rc (build.sh left no marker)" >"$RES/build-main0916.done"
echo "$(ts) step 2 done: $(cat "$RES/build-main0916.done")"
echo "$(ts) step 3: build headoff (build.sh re-checks the lease first)"
EXPECT_K_VNNI=OFF bash "$C/build.sh" "$HEAD_COMMIT" /var/tmp/jhan/tron-headoff0916 headoff0916 -DTRON_AMX_DISPATCH=ON; rc=$?
[ -s "$RES/build-headoff0916.done" ] || echo "build-failed rc=$rc (build.sh left no marker)" >"$RES/build-headoff0916.done"
echo "$(ts) step 3 done: $(cat "$RES/build-headoff0916.done")"
m1=$(cat "$RES/build-main0916.done"); m2=$(cat "$RES/build-headoff0916.done")
# a failed build drops its arm; the campaign still answers what it can with the other two
if [ "$m1" = ok ] && [ "$m2" = ok ]; then
  echo "$(ts) step 4: campaign (arms base headoff vnni)"
  bash "$C/campaign.sh"
elif [ "$m1" = ok ]; then
  echo "$(ts) step 4: headoff build '$m2': campaign runs base vs vnni only"
  ARMS="base vnni" SMOKE_ARMS="base base2 vnni vnni2" bash "$C/campaign.sh"
elif [ "$m2" = ok ]; then
  echo "$(ts) step 4: base build '$m1': campaign runs headoff vs vnni only (the pre-registered vnni-vs-main rule cannot be applied)"
  ARMS="headoff vnni" SMOKE_ARMS="headoff headoff2 vnni vnni2" bash "$C/campaign.sh"
else
  echo "$(ts) both builds failed ('$m1', '$m2'); no campaign"
  echo "build:base:$m1;headoff:$m2" >"$EXEC/logs/vnnik6-20260916.done"
  echo "$(ts) finished: build:base:$m1;headoff:$m2" >"$EXEC/logs/vnnik6-20260916.status"
fi
echo "$(ts) step 4 done: $(cat "$EXEC/logs/vnnik6-20260916.done" 2>/dev/null)"
echo "=== vnnik6 chain.sh finished $(ts) ==="
