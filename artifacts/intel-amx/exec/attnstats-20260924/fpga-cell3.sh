#!/usr/bin/env bash
# attnstats-20260925-warm (fpga-cell3.sh, replaces fpga-cell2.sh which never started a run): case 5 of the FPGA-attention question, "warm prefix-cache hit".
# Waits for the attnstats-20260925-fpga campaign (fpga-cell.sh) to finish, then runs runtron cells with --iterations 3:
# iteration 1 = cold (prefill + decode), iterations 2 and 3 = the same prompts again in the same scheduler instance, so their
# prompt tokens are prefix-cache hits ("[Iteration k/3] Processed X new and Y reused tokens" in the runtron log).
# The [attn-stats] exit report sums all 3 iterations; warm-iteration counters = (this run - the matching 1-iteration run of
# attnstats-20260925-fpga) / 2, per counter. Same binary, same prompts, 256 tokens per user (--dont-stop), so the visit
# counts depend only on positions and are the same across runs.
# Cells (fpga-cell3, 2026-09-25 revision): prompt 1000, not 1024. A cached prefix that ends INSIDE a shard's 1024-token range makes
# the new branch create its own shard and re-copy the shared GOFs (backfill: full.hpp split_edge_at / find_or_create_shard /
# backfill_shard); a cached prefix that ends exactly at the shard end (1024) reuses the landed shard. So:
#   q3-4b-tp2-1u-p1000-it3 / q3-4b-tp2-8u-p1000-it3 = the warm-branch-inside-a-shard case (like the 2026-09-17 cached_tokens 910 shape)
#   q3-4b-tp2-1u-p1000-it1 / q3-4b-tp2-8u-p1000-it1 = their 1-iteration baselines for the subtraction
#   q3-4b-tp2-1u-p1024-it3 = the contrast cell (branch at the shard end: shard reuse expected, 0 AMX in the warm iterations)
# Arms: headon2 (stats on, AMX on) under FPGA attention; headkill2 (kill switch) as the control on the 1-user cell;
# headon2 under CPU attention on the 1-user cell as the bookkeeping control (reused tokens, no FPGA).
# Launch (delphi-3bda): setsid nohup bash ~/workspace/intel-AMX/exec/attnstats-20260924/fpga-cell2.sh >/dev/null 2>&1 &
# Stop: kill -TERM $(pgrep -f 'bash .*attnstats-20260924/campaign-iter.sh')
# Outputs: exec/results/attnstats-20260925-warm/{rt/,rt-results.txt,exit-reports.txt,summary.md}; log exec/logs/attnstats-20260925-warm.log
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20260924
export NAME=attnstats-20260925-warm
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
FIRST_DONE=$EXEC/logs/attnstats-20260925-fpga.done
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "$(ts) === fpga-cell2 started pid $$; waiting for $FIRST_DONE ==="
until [ -e "$FIRST_DONE" ]; do sleep 120; done
echo "$(ts) first campaign marker: $(cat "$FIRST_DONE")"
export RT_BASE=/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase
export RT_HEAD=/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead2
export TIP_BASE=66c7bb8db1 TIP_HEAD=cbf1bb6c0c
export ARM_ENV_headon2="TRON_ATTN_STATS=1"
export ARM_ENV_headkill2="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"
export WEDPERF_ARMS="headon2 headkill2"
CELLS_ALL=$'q3-4b-tp2-1u-p1000-it3|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1000|--iterations 3\nq3-4b-tp2-8u-p1000-it3|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1000|--iterations 3\nq3-4b-tp2-1u-p1000-it1|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1000|\nq3-4b-tp2-8u-p1000-it1|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1000|\nq3-4b-tp2-1u-p1024-it3|ingested-qwen-3-4b-instruct-2507-tp2|2|1|1024|--iterations 3'
# pass 1: both cells, FPGA attention, stats on
CELLS_ALL="$CELLS_ALL" CELLS="q3-4b-tp2-1u-p1000-it1 q3-4b-tp2-1u-p1000-it3 q3-4b-tp2-8u-p1000-it1 q3-4b-tp2-8u-p1000-it3 q3-4b-tp2-1u-p1024-it3" ARMS="headon2" ATTNS=fpga REPS=1 DEADLINE_HHMM=0130 bash "$C/campaign-iter.sh"
echo "$(ts) pass 1 marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
# pass 2: the 1-user cell with the kill switch (FPGA) and under CPU attention (bookkeeping control); same results dir
rm -f "$EXEC/logs/$NAME.done"
CELLS_ALL="$CELLS_ALL" CELLS="q3-4b-tp2-1u-p1000-it3" ARMS="headkill2 headon2" ATTNS="fpga cpu" REPS=1 DEADLINE_HHMM=0130 bash "$C/campaign-iter.sh"
echo "$(ts) pass 2 marker: $(cat "$EXEC/logs/$NAME.done" 2>/dev/null)"
for f in "$RES"/rt/*.log; do
  [ -e "$f" ] || continue
  echo "## $(basename "$f")"
  grep -h -m2 "HW attention\|Hw-Attn model params" "$f" | cut -c1-200
  grep -h "\[Iteration \|\[Total over" "$f" | cut -c1-220
  grep -h "^\[attn-stats\]" "$f"
  echo "HBM-EXHAUSTION lose=$(grep -c 'lose HW attention' "$f") exhausted=$(grep -c 'HBM bypass space exhausted' "$f")"
done >"$RES/exit-reports.txt"
echo "$(ts) === fpga-cell2 finished ==="
