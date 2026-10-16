#!/usr/bin/env bash
# i4934-20261015 ablation runs (run ON delphi-3bda, our half, detached): campaign-fix.sh with the two timing probes of
# abl-build.sh as extra arms, after the two perf drivers (exec/logs/i4934-perf.done, i4934-perf-fpga.done) and the ablation
# builds (results/i4934-abl/abl.done = ok).
# Arm mapping (campaign-fix.sh has fixed arm names): headoff = PR #4898 (runtron.pr3), fixoff = the fix (runtron.fix),
# lazyoff = ablation a1 (runtron.a1: tail rows through the reader), baseoff = ablation a2 (runtron.a2: constant block mask).
# Cells: q3-4b tp2 8 users prompt 1024 and 8192, CPU attention, 3 repetitions. Results exec/results/i4934-abl-cpu/.
# Usage (on 3bda): END_BY=<ISO UTC> bash abl-run.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
END_BY=${END_BY:?END_BY (ISO UTC) is required}
PERF_DONE=$EXEC/logs/i4934-perf.done
PERF2_DONE=$EXEC/logs/i4934-perf-fpga.done
ABL_DONE=$EXEC/results/i4934-abl/abl.done
LOG=$EXEC/logs/i4934-abl-run.log
mkdir -p "$EXEC/logs"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
exec >>"$LOG" 2>&1
echo "=== abl-run started $(ts) pid $$ on $(hostname) END_BY=$END_BY ==="
w=0
until [ -e "$PERF_DONE" ] && [ -e "$PERF2_DONE" ] && [ -e "$ABL_DONE" ]; do past_end && { echo "$(ts) past END_BY before the perf driver and the ablation builds finished"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for $PERF_DONE, $PERF2_DONE and $ABL_DONE"; w=1; sleep 120; done
[ "$(cat "$ABL_DONE")" = ok ] || { echo "$(ts) ablation builds: $(cat "$ABL_DONE"): no runs"; exit 1; }
export NAME=i4934-abl-cpu
export RT_FIX=/var/tmp/jhan/tron-i4934/gen/runtron.fix
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_LAZY=/var/tmp/jhan/tron-i4934abl/gen/runtron.a1
export RT_BASE=/var/tmp/jhan/tron-i4934abl/gen/runtron.a2
export ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_fixoff=TRON_AMX_DISABLE=1 ARM_ENV_lazyoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export CELLS_ALL="q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024
q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192"
export ARMS="headoff fixoff lazyoff baseoff" ATTNS=cpu REPS=${REPS:-3}
export DEADLINE_HHMM=$(date -u -d "$END_BY" +%H%M)
export SUMMARY_TITLE="# $NAME summary: ablation probes of the issue #4934 fix (headoff = PR #4898 dfafd13dce, fixoff = the fix c30a86f252, lazyoff = ablation a1 (tail rows through the reader, mask read kept), baseoff = ablation a2 (constant block mask, no per-page read); all with TRON_AMX_DISABLE=1; attn = cpu)"
echo "$(ts) starting campaign-fix.sh: ARMS=[$ARMS] REPS=$REPS deadline HHMM=$DEADLINE_HHMM"
bash "$D/campaign-fix.sh"
echo "=== abl-run finished $(ts): $(cat "$EXEC/logs/$NAME.done" 2>/dev/null) ==="
