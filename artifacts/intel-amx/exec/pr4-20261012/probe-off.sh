#!/usr/bin/env bash
# pr4off-20261014 campaign (runs ON delphi-3bda, detached; fork of probe-lazy.sh): PR-4 against main with the kill switch
# (TRON_AMX_DISABLE=1) on both, plus PR-3 and the lazy-dotter probe build, in the three CPU cells of PR4-handoff.md step 6 row E.
# Why (jhan, 2026-10-14): PR-4 is the last PR of the stack, so its AMX-off path must be compared with main's AMX-off path, not
# only with PR-3's; the lazy-dotter probe is the candidate partial fix. No build: the four binaries exist from 2026-10-12/13.
# Original header of the fork source follows. Why: PR-4's
# kill-switch arm is 2.0 to 3.4 % slower than PR-3's in those cells (split-status.md "PR-4 Step 6, run 2"); the variant
# (commit COMMIT on the probe branch jhan-vnnik-4-probe-lazydot) builds the dotters of a VNNI slot at the first row-major
# token only. Steps: build runtron.pr4lazy on our half (build2.sh, CONF_VNNI, target runtron), then the whole-machine part
# (Bill's marker taken on jhan's order, serving down through platformd, the cells with campaign-probe.sh, the exit handler
# of chain-finish.sh: serving up, the marker released). Arms: new (runtron.pr4), newoff, head (runtron.pr3), headoff, lazy
# (runtron.pr4lazy), lazyoff; pairs lazyoff:newoff, lazyoff:headoff, lazy:new, lazy:head, newoff:headoff. 54 runs, about
# 74 min (est., 81.7 s per run), plus the takeover. No hand-off marker (campaign W is not involved).
# Usage (on 3bda): END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] bash probe-off.sh
# Stop: kill -- -<pid> (setsid: the pid is the group id); the exit handler restores serving and releases the marker.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/pr4-20261012
B=$EXEC/i4525-20260922/build2.sh
DUT=$EXEC/q4b-fpga-20260921/dut.sh
BILL_SHARE=$EXEC/bill-share.sh
export NAME=pr4off-20261014
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-probe.log
REPO=/home/jhan/workspace/tron
END_BY=${END_BY:?END_BY (ISO UTC) is required}
START_NOT_BEFORE=${START_NOT_BEFORE:-}
OUR_CPUS=72-143,216-287
WT=/var/tmp/jhan/tron-pr4lazy
export RT_LAZY=$WT/gen/runtron.pr4lazy
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_lazyoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
machine() { echo "lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
OUR_RT_RE="^($(printf '%s' "$RT_BASE" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_HEAD" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_NEW" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_LAZY" | sed 's/[.[\*^$()+?{}|]/\\&/g')) "
MARKER_TAKEN=0
SERVING_DOWN_BY_US=0
MARKER=/var/tmp/jhan/pr4off-20261014.not-used   # chain-finish.sh needs the name; this probe never creates a hand-off marker
MARKER_CREATED=0
source "$D/chain-finish.sh"
trap 'finish term; exit 143' TERM
trap 'finish exit' EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/probe.done"
echo "=== $NAME campaign started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) END_BY=$END_BY START_NOT_BEFORE=${START_NOT_BEFORE:-none} ==="
echo "$(ts) machine: $(machine)"
for b in "$RT_NEW" "$RT_HEAD" "$RT_BASE" "$RT_LAZY"; do [ -x "$b" ] || { step_done start "$b missing: abort"; echo failed-binary >"$RES/probe.done"; exit 1; }; done
if [ -n "$START_NOT_BEFORE" ]; then
  snb=$(date -u -d "$START_NOT_BEFORE" +%s) || { step_done start "bad START_NOT_BEFORE: abort"; echo failed-start >"$RES/probe.done"; exit 1; }
  while [ "$(date -u +%s)" -lt "$snb" ]; do left=$(( snb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) holding until $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"; done
fi
# ---- whole-machine part ----
past_end && { step_done 0 "past END_BY before the whole-machine part"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
wait_slot "step 0"
tout=$(bash "$BILL_SHARE" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc)"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then SERVING_DOWN_BY_US=1; IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$?"; fi
step_done 1 "serving: $(machine)"
cells() { local s tp p out=""; for s in "$@"; do tp=${s%%:*}; p=${s##*:}; out+="q3-4b-tp$tp-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp$tp|$tp|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
if past_end; then step_done E "skipped: past END_BY"; e=skipped; else
  NAME=pr4off-E-cpu CELLS_ALL="$(cells 2:1024 2:8192 4:1024)" ARMS="baseoff headoff newoff lazyoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="baseoff headoff newoff lazyoff" WEDPERF_PAIRS="newoff:baseoff lazyoff:baseoff headoff:baseoff lazyoff:newoff newoff:headoff" bash "$D/campaign-probe.sh"
  e=$(cat "$EXEC/logs/pr4off-E-cpu.done" 2>/dev/null)
  step_done E "$e; head line: $(grep -m1 '^# arms:' "$EXEC/results/pr4off-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-240)"
fi
echo "E=$e" >"$RES/probe.done"
step_done end "$(cat "$RES/probe.done")"
echo "=== $NAME campaign finished $(ts): $(cat "$RES/probe.done") (the exit handler restores serving and releases the marker next) ==="
