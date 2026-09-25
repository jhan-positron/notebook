#!/usr/bin/env bash
# i4587-20260924 alignment test (runs ON delphi-3bda, setsid nohup): is the kill-switch (AVX) prefill gap of #4587 vs #4557
# (+1.25 s at prompt 8192, two sessions) a code-layout effect? The attention functions of both runtron binaries have identical
# instructions, but 132 of the 138 qwen3-4b attention functions start at a different offset within a 64-byte line.
# This run rebuilds #4557 and #4587 with -falign-functions=64 (every function starts on a 64-byte boundary) and measures four
# binaries interleaved, all with TRON_AMX_DISABLE=1, model qwen3-4b tp2, 8 users:
#   slot base = #4557 633cb88896 (runtron.pr4557, as built on 2026-09-24), slot head = #4587 c73e7fb2f9 (runtron.pr4587),
#   slot new  = #4557 aligned (runtron.pr4557a64),                           slot alt  = #4587 aligned (runtron.pr4587a64).
# Prompt 8192 x 4 repetitions, then prompt 1024 x 3. Starts after the isolation run (results/i4587-iso/chain.done).
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4587-align
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/runtron
HEAD_SHA=633cb88896ecb5daddbf74c77fb403e9f40c930c
NEW_SHA=c73e7fb2f99c8f369c809929d1df15bea507cdc3
export RT_BASE=/var/tmp/jhan/tron-i4525rt/gen/runtron.pr4557
export RT_HEAD=/var/tmp/jhan/tron-i4525rt2/gen/runtron.pr4587
export RT_NEW=/var/tmp/jhan/tron-i4525rt/gen/runtron.pr4557a64
export RT_ALT=/var/tmp/jhan/tron-i4525rt2/gen/runtron.pr4587a64
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_altoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
A64_CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS=-falign-functions=64'
mkdir -p "$RES" "$EXEC/logs" "$EV"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
exec >>"$LOG" 2>&1
echo "=== $NAME started $(ts) pid $$ ==="
until [ -e "$EXEC/results/i4587-iso/chain.done" ]; do sleep 60; done
echo "$(ts) isolation run finished: $(cat "$EXEC/results/i4587-iso/chain.done")"
if ci_lease_busy; then step_done start "CI lease busy: abort"; echo lease >"$RES/chain.done"; exit 1; fi
for x in unaligned-base:$RT_BASE unaligned-head:$RT_HEAD; do [ -x "${x#*:}" ] || { step_done start "missing ${x#*:}"; echo missing >"$RES/chain.done"; exit 1; }; done
build() {  # $1 sha $2 worktree $3 suffix
  RES=$RES SRC=/home/jhan/workspace/tron COMMIT=$1 WT=$2 SUFFIX=$3 CONFIGURE_ARGS="$A64_CONFIGURE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  local bin=$2/gen/runtron.$3 n=0 odd=0
  [ -x "$bin" ] && n=$(strings "$bin" | grep -c ingested-qwen-3-4b-instruct-2507)
  # alignment proof: qwen3-4b self_attention functions whose start address is not a multiple of 64
  [ -x "$bin" ] && odd=$(nm -C --defined-only "$bin" | awk '$2 ~ /^[tTwW]$/' | grep qwen_3_4b_instruct_2507_impl | grep self_attention |
    awk '{ if (strtonum("0x" $1) % 64 != 0) c++ } END { print c + 0 }')
  echo "$(ts) build $3: $(cat "$RES/build-$3.done" 2>/dev/null) plugin strings=$n qwen self_attention functions not 64-aligned=$odd"
  [ "$(cat "$RES/build-$3.done" 2>/dev/null)" = ok ] && [ "${n:-0}" -gt 0 ]
}
build "$HEAD_SHA" /var/tmp/jhan/tron-i4525rt pr4557a64 && build "$NEW_SHA" /var/tmp/jhan/tron-i4525rt2 pr4587a64 ||
  { step_done builds "FAILED"; echo chain-failed-builds >"$RES/chain.done"; exit 1; }
step_done builds "ok $RT_NEW $RT_ALT"
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); campaign4.sh retries"
fi
ARMS="baseoff headoff newoff altoff"
PAIRS="headoff:baseoff altoff:newoff newoff:baseoff altoff:headoff"
NAME=i4587-align-p8192 CELLS_ALL='q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192' ARMS="$ARMS" ATTNS=cpu \
  REPS=4 DEADLINE_HHMM=0130 WEDPERF_ARMS="$ARMS" WEDPERF_PAIRS="$PAIRS" bash "$C/campaign4.sh"
step_done p8192 "$(cat "$EXEC/logs/i4587-align-p8192.done" 2>/dev/null)"
NAME=i4587-align-p1024 CELLS_ALL='q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024' ARMS="$ARMS" ATTNS=cpu \
  REPS=3 DEADLINE_HHMM=0130 WEDPERF_ARMS="$ARMS" WEDPERF_PAIRS="$PAIRS" bash "$C/campaign4.sh"
step_done p1024 "$(cat "$EXEC/logs/i4587-align-p1024.done" 2>/dev/null)"
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ')"
for n in $NAME i4587-align-p8192 i4587-align-p1024; do
  [ -d "$EXEC/results/$n" ] && mkdir -p "$EV/$n" && cp -r "$EXEC/results/$n"/. "$EV/$n/" 2>/dev/null
  cp "$EXEC/logs/$n.log" "$EV/" 2>/dev/null
done
cp "$LOG" "$EV/" 2>/dev/null
step_done end "finished"
echo chain-finished >"$RES/chain.done"
