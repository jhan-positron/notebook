#!/usr/bin/env bash
# i4934-20261015 token-identity driver (runs ON delphi-3bda, detached; the whole-machine part of probe-fix.sh with the D step
# of exec/pr4-20261012/chain2.sh instead of the cells). Why a second driver: the first one has no identity step, and a
# running script is never edited (NFS). Steps, each after wait_slot (CI lease with 600 s grace, other people, the
# 02:10-03:45 UTC pre-CI hold) and END_BY:
#   0.  Bill's marker taken (exec/bill-share.sh take, on jhan's order; refused while Bill is active -> identity.done=stopped-marker)
#   1.  serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down)
#   D.  token identity, qwen3-4b tp2, 1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens (smoke-fix.sh):
#       cells cpu p1024, cpu p8192, fpga p1024; arms fix fix2 new fixoff (cpu) and fix fix2 new (fpga). Must match: fix == fix2
#       (the A/A control). fix vs new is expected identical in the cpu cells (the same dotter on row-major rows, the same
#       reader on VNNI blocks) and is judged by hand; fixoff vs fix follows issue #4444. After each cell validate-smoke.py
#       checks every arm's rc=0 line and 256 tokens.
#   end. identity.done = ok | failed-<cell>; the exit handler (chain-finish.sh): serving up, the marker released, machine line.
# Usage (on 3bda): END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] bash identity-fix.sh
# Stop: kill -- -<pid> (setsid: the pid is the group id); the exit handler restores serving and releases the marker.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
P4=$EXEC/pr4-20261012
DUT=$EXEC/q4b-fpga-20260921/dut.sh
BILL_SHARE=$EXEC/bill-share.sh
export NAME=i4934-identity
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-driver.log
END_BY=${END_BY:?END_BY (ISO UTC) is required}
START_NOT_BEFORE=${START_NOT_BEFORE:-}
export RT_FIX=/var/tmp/jhan/tron-i4934/gen/runtron.fix
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_fixoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/identity.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
machine() { echo "lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
OUR_RT_RE="^($(printf '%s' "$RT_BASE" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_HEAD" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_NEW" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_FIX" | sed 's/[.[\*^$()+?{}|]/\\&/g')) "
MARKER_TAKEN=0
SERVING_DOWN_BY_US=0
MARKER=/var/tmp/jhan/$NAME.not-used
MARKER_CREATED=0
source "$P4/chain-finish.sh"
trap 'finish term; exit 143' TERM
trap 'finish exit' EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/identity.done"
echo "=== $NAME driver started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) END_BY=$END_BY START_NOT_BEFORE=${START_NOT_BEFORE:-none} ==="
echo "$(ts) machine: $(machine)"
for b in "$RT_NEW" "$RT_HEAD" "$RT_BASE" "$RT_FIX"; do [ -x "$b" ] || { step_done start "$b missing: abort"; echo failed-binary >"$RES/identity.done"; exit 1; }; done
echo "$(ts) fix tip: $(git -C /var/tmp/jhan/tron-i4934 rev-parse HEAD) sha256 $(sha256sum "$RT_FIX" | cut -c1-16)"
if [ -n "$START_NOT_BEFORE" ]; then
  snb=$(date -u -d "$START_NOT_BEFORE" +%s) || { step_done start "bad START_NOT_BEFORE: abort"; echo failed-start >"$RES/identity.done"; exit 1; }
  while [ "$(date -u +%s)" -lt "$snb" ]; do left=$(( snb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) holding until $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"; done
fi
past_end && { step_done 0 "past END_BY before the whole-machine part"; echo stopped-end-by >"$RES/identity.done"; exit 1; }
wait_slot "step 0"
tout=$(bash "$BILL_SHARE" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc)"; echo stopped-marker >"$RES/identity.done"; exit 1;; esac
if rinzler_active; then SERVING_DOWN_BY_US=1; IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$?"; fi
step_done 1 "serving: $(machine)"
export DEADLINE_HHMM=0130
verdict=ok
for spec in "cpu 1024 fix fix2 new fixoff" "cpu 8192 fix fix2 new fixoff" "fpga 1024 fix fix2 new"; do
  past_end && { step_done D "skipped $spec: past END_BY"; verdict=failed-end-by; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  export MUST_MATCH="fix:fix2"
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$D/smoke-fix.sh"
  v=$(python3 "$P4/validate-smoke.py" "$RES/smoke/$attn-p$prompt" 256 "$@" 2>&1 | tail -1); echo "$v" >"$RES/smoke/$attn-p$prompt/validate.txt"
  [ "$(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)" = ok ] && [ "$v" = "VALIDATE ok" ] || verdict="failed-$attn-p$prompt"
  step_done D "$attn p$prompt: smoke.done=$(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null) $v; $(grep -E ' vs .*(identical|first difference)' "$RES/smoke/$attn-p$prompt/smoke.txt" | tail -8 | cut -c1-120 | tr '\n' ';')"
done
echo "$verdict" >"$RES/identity.done"
step_done end "$(cat "$RES/identity.done")"
echo "=== $NAME driver finished $(ts): $(cat "$RES/identity.done") (the exit handler restores serving and releases the marker next) ==="
