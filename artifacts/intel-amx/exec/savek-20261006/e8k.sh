#!/usr/bin/env bash
# savek-20261006 follow-up (runs ON delphi-3bda after chain.sh): the CPU-attention prompt-8192 cell once more, 5 repetitions,
# arm order REVERSED (new first, then head) to separate a run-order effect from a binary effect. In the chain's E-cpu
# step the new binary's TTFT was 61.5 / 53.1 / 53.2 s against head 52.9 / 52.7 / 52.7 s (rep 1 an outlier; reps 2-3
# +0.4 s). Then final.sh (t_llama_unit at the final commit + ingest tests) so the builds do not disturb the cell.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
S=$EXEC/sync4424-20261002
export RT_HEAD=/var/tmp/jhan/tron-tilec/gen/runtron RT_BASE=/var/tmp/jhan/tron-tilec/gen/runtron RT_NEW=/var/tmp/jhan/tron-savek/gen/runtron.savek
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill" SKIP_SERVING_UP=1
NAME=savek-E-cpu8k CELLS_ALL="q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192" ARMS="new head" ATTNS=cpu REPS=5 DEADLINE_HHMM=0130 \
  WEDPERF_ARMS="new head" WEDPERF_PAIRS="new:head" bash "$S/campaign.sh"
echo "$(date -u +%FT%TZ) E-cpu8k: $(cat $EXEC/logs/savek-E-cpu8k.done 2>/dev/null)" >>$EXEC/results/savek-20261006/chain-steps.txt
COMMIT=${COMMIT:?} bash $EXEC/savek-20261006/final.sh
source "$EXEC/lib-guard.sh"
if ci_lease_busy 600; then echo "serving: CI lease busy, left alone"; elif rinzler_active; then echo "serving: active"; else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up; fi >>$EXEC/logs/savek-20261006-final.log 2>&1
echo "$(date -u +%FT%TZ) FINAL: $(cat $EXEC/results/savek-20261006/final.done 2>/dev/null) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ')" >>$EXEC/results/savek-20261006/chain-steps.txt
