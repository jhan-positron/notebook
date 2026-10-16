#!/usr/bin/env bash
# sync4424b-20261007 add-on (runs ON delphi-3bda, detached): isolate the typed K port from main's own changes.
#   headm = commit c6ec38813d = PR #4424 merged with today's main, K plane still a raw pointer (the textual merge +
#           the CMake fix, before the typed owner/view port), built into /var/tmp/jhan/tron-headm (runtron.headm)
#   new   = runtron.sync6 (37064d72b2, the typed port), the binary the chain measured
# If headm and new sit inside each other's band, the TTFT gain of new over the 2026-09-17 head comes from main's
# 916 commits, not from the typed tensors. Arms: head (= headm here), new. Smoke identity first (headm == new).
# Serializes with chain.sh through the campaign guard flock. Usage: bash headm.sh (see the sleeper in the memory file).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
export NAME=sync4424b-20261007
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-headm.log
export RT_HEAD=/var/tmp/jhan/tron-headm/gen/runtron.headm
export RT_BASE=$RT_HEAD
export RT_NEW=/var/tmp/jhan/tron-sync6/gen/runtron.sync6
export SKIP_SERVING_UP=1
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
exec >>"$LOG" 2>&1
echo "=== $NAME headm add-on started $(ts) pid $$ ==="
[ -x "$RT_HEAD" ] || { step_done headm "binary $RT_HEAD missing: abort"; exit 1; }
[ -x "$RT_NEW" ] || { step_done headm "binary $RT_NEW missing: abort"; exit 1; }
# wait for the chain relaunch to finish (it writes chain.done at its end; the sleeper starts it at 13:30 UTC)
while ! { [ -e "$RES/chain.done" ] && [ "$(stat -c %Y "$RES/chain.done")" -gt "$(date -u -d 2026-10-08T13:00:00Z +%s)" ]; }; do sleep 120; done
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$?"
fi
export MUST_MATCH="new:head"
# own NAME for the smoke: the chain's smoke dir already holds head/new token files (head = the 2026-09-17 binary)
NAME=sync4424b-headm ATTN=cpu PROMPT=1024 LEN=256 SMOKE_ARMS="head new" bash "$S/smoke.sh"
step_done headm-smoke "cpu p1024: $(cat "$EXEC/results/sync4424b-headm/smoke/cpu-p1024/smoke.done" 2>/dev/null)"
cells() { local p out=""; for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
for spec in "sync6-E-headm-cpu cpu 1024 8192" "sync6-E-headm-fpga fpga 1024"; do
  set -- $spec; name=$1; attn=$2; shift 2
  NAME=$name CELLS_ALL="$(cells "$@")" ARMS="head new" ATTNS="$attn" REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="head new" WEDPERF_PAIRS="new:head" bash "$S/campaign.sh"
  step_done "$name" "$(cat "$EXEC/logs/$name.done" 2>/dev/null)"
done
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$?"; fi
step_done headm-end "add-on finished"
echo "=== $NAME headm add-on finished $(ts) ==="
