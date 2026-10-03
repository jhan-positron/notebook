#!/usr/bin/env bash
# attnstats-20260925-fpga: measurement 6 of counter.html section 10, "FPGA steady state".
# Runs the attention path stats (TRON_ATTN_STATS=1, branch binary runtron.attnhead2 = cbf1bb6c0c, PR #4596) with
# FPGA attention (USE_HW_ATTN unset) on OUR half of delphi-3bda through campaign.sh (guards, lease wait, idle takeover,
# restore all unchanged). Question answered: does the AMX path run in decode when attention is on the FPGA, and how much
# (ready_amx_visits / pending_amx_visits / ready_empty_visits / token_jobs_by_path_set in the [attn-stats] exit report)?
# Cells (qwen-3-4b tp2, 256 generated tokens, --dont-stop):
#   q3-4b-tp2-8u-p1024  the Table 1 cell (8 users, prompt 1024)
#   q3-4b-tp2-1u-p1024  one user (DMA lag with no batch, closest to the 2026-09-17 perf measurement shape)
#   q3-4b-tp2-8u-p64    prompt 64: the first 63 decode queries sit below the engagement point 127 (all-CPU, page 0 dense)
#   q3-4b-tp2-8u-p8192  the Table 1 8192 cell
# Arms: headon2 = stats on, AMX on; headkill2 = stats on + TRON_AMX_DISABLE=1 (control: amx visits must be 0, the
# avx_full_page counters show the dense pages the kernel would have taken). REPS=1.
# Launch (on delphi-3bda): setsid nohup bash ~/workspace/intel-AMX/exec/attnstats-20260924/fpga-cell.sh >/dev/null 2>&1 &
# Stop: kill -TERM $(pgrep -f 'bash .*attnstats-20260924/campaign.sh')  (campaign.sh restores serving on TERM)
# Outputs: exec/results/attnstats-20260925-fpga/{rt/,rt-results.txt,exit-reports.txt,summary.md}; log exec/logs/attnstats-20260925-fpga.log
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20260924
export NAME=attnstats-20260925-fpga
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "$(ts) === fpga-cell started pid $$ ==="
export RT_BASE=/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase
export RT_HEAD=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2
export TIP_BASE=66c7bb8db1 TIP_HEAD=cbf1bb6c0c
export ARM_ENV_headon2="TRON_ATTN_STATS=1"
export ARM_ENV_headkill2="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"
export WEDPERF_ARMS="headon2 headkill2"
CELLS_ALL=$'q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024\nq3-4b-tp2-1u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024\nq3-4b-tp2-8u-p64|ingested-qwen-3-4b-instruct-2507-tp2|2|8|64\nq3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192'
CELLS_ALL="$CELLS_ALL" CELLS="q3-4b-tp2-8u-p1024 q3-4b-tp2-1u-p1024 q3-4b-tp2-8u-p64 q3-4b-tp2-8u-p8192" \
  ARMS="headon2 headkill2" ATTNS=fpga REPS=1 DEADLINE_HHMM=0130 bash "$C/campaign.sh"
echo "$(ts) campaign marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
for f in "$RES"/rt/*.log; do
  [ -e "$f" ] || continue
  echo "## $(basename "$f")"
  grep -h -m2 "HW attention\|Hw-Attn model params" "$f" | cut -c1-200
  grep -h "^\[attn-stats\]" "$f"
  echo "HBM-EXHAUSTION lose=$(grep -c 'lose HW attention' "$f") exhausted=$(grep -c 'HBM bypass space exhausted' "$f")"
done >"$RES/exit-reports.txt"
echo "$(ts) === fpga-cell finished ==="
