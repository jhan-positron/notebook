#!/usr/bin/env bash
# i4587-20260924 isolation run (runs ON delphi-3bda, setsid nohup): which #4587 commit slows the kill-switch (AVX) path?
# The chain of 2026-09-24 measured, with TRON_AMX_DISABLE=1, prompt 8192: TTFT #4587 = #4557 + 1.25 s (+1.0 %, paired t 19.5),
# and at prompt 1024 decode #4587 = #4557 - 0.64 TPS/user. This run builds commit 1 of #4587 alone (39a6899446: allocation
# creates the blocks, std::launder, no K1) and measures three binaries on the same cells, 4 repetitions at prompt 8192 and
# 3 at prompt 1024, arms interleaved:
#   slot base = PR #4557 633cb88896 (runtron.pr4557), slot head = #4587 commit 1 39a6899446 (runtron.pr4587c1, tree
#   /var/tmp/jhan/tron-main0916, name historical), slot new = #4587 c73e7fb2f9 (runtron.pr4587).
# The arm names in the results are the slot names with "off": baseoff = #4557, headoff = commit 1, newoff = full #4587.
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4587-iso
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/runtron
C1_SHA=39a68994465f3fb753623eec18378544be806862
export RT_BASE=/var/tmp/jhan/tron-i4525rt/gen/runtron.pr4557
export RT_HEAD=/var/tmp/jhan/tron-main0916/gen/runtron.pr4587c1
export RT_NEW=/var/tmp/jhan/tron-i4525rt2/gen/runtron.pr4587
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
RT_CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
mkdir -p "$RES" "$EXEC/logs" "$EV"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
exec >>"$LOG" 2>&1
echo "=== $NAME started $(ts) pid $$ c1=$C1_SHA ==="
if ci_lease_busy; then step_done start "CI lease busy: abort"; echo lease >"$RES/chain.done"; exit 1; fi
RES=$RES SRC=/home/jhan/workspace/tron COMMIT=$C1_SHA WT=/var/tmp/jhan/tron-main0916 SUFFIX=pr4587c1 \
  CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
n=0; [ -x "$RT_HEAD" ] && n=$(strings "$RT_HEAD" | grep -c ingested-qwen-3-4b-instruct-2507)
if [ "$(cat "$RES/build-pr4587c1.done" 2>/dev/null)" != ok ] || [ "${n:-0}" -eq 0 ]; then
  step_done build "FAILED ($(cat "$RES/build-pr4587c1.done" 2>/dev/null), plugin strings $n)"; echo chain-failed-build >"$RES/chain.done"; exit 1
fi
step_done build "ok $RT_HEAD tip $(git -C /var/tmp/jhan/tron-main0916 rev-parse --short HEAD)"
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); campaign.sh retries"
fi
PAIRS="headoff:baseoff newoff:baseoff newoff:headoff"
NAME=i4587-iso-p8192 CELLS_ALL='q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192' ARMS="baseoff headoff newoff" ATTNS=cpu \
  REPS=4 DEADLINE_HHMM=0130 WEDPERF_ARMS="baseoff headoff newoff" WEDPERF_PAIRS="$PAIRS" bash "$C/campaign.sh"
step_done p8192 "$(cat "$EXEC/logs/i4587-iso-p8192.done" 2>/dev/null)"
NAME=i4587-iso-p1024 CELLS_ALL='q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024' ARMS="baseoff headoff newoff" ATTNS=cpu \
  REPS=3 DEADLINE_HHMM=0130 WEDPERF_ARMS="baseoff headoff newoff" WEDPERF_PAIRS="$PAIRS" bash "$C/campaign.sh"
step_done p1024 "$(cat "$EXEC/logs/i4587-iso-p1024.done" 2>/dev/null)"
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ')"
for n in $NAME i4587-iso-p8192 i4587-iso-p1024; do
  [ -d "$EXEC/results/$n" ] && mkdir -p "$EV/$n" && cp -r "$EXEC/results/$n"/. "$EV/$n/" 2>/dev/null
  cp "$EXEC/logs/$n.log" "$EV/" 2>/dev/null
done
cp "$LOG" "$EV/" 2>/dev/null
step_done end "finished"
echo chain-finished >"$RES/chain.done"
