#!/usr/bin/env bash
# i4587-20260924 chain (runs ON delphi-3bda, launched with setsid nohup after the nightly CI lease clears and after the
# #4587 unit-test run /var/tmp/jhan/pr4587-test/run.done): runtron correctness and performance of three binaries.
#   base = main 996f58ec82 (the base of PR #4557), head = PR #4557 633cb88896, new = draft PR #4587 c73e7fb2f9.
# Steps:
#   1. build the three runtron binaries with the qwen3-4b plugin (cross-avx512 preset, AMX dispatch on, RelWithDebInfo),
#      reusing the runtron trees of the 2026-09-22 campaign (incremental builds): base in /var/tmp/jhan/tron-main0922,
#      head in /var/tmp/jhan/tron-i4525rt, new in /var/tmp/jhan/tron-i4525rt2 (tree names are historical).
#   2. Step D, token identity: 1 user, temperature 0, --pay-for-determinism, seed 1, 256 generated tokens, qwen3-4b tp2.
#      CPU attention p1024 (arms base head head2 new new2 baseoff headoff newoff) and p8192 (base head new baseoff headoff
#      newoff); FPGA attention p1024 and p8192 (base head new). Pass = every must-match pair identical (smoke.sh).
#   3. Step E, performance: 8 users, 256 tokens, 3 repetitions, arms interleaved inside every repetition.
#      E-cpu:  CPU attention, prompt 1024/2048/8192, arms base head new.
#      E-fpga: FPGA attention, prompt 1024/8192, arms base head new.
#      E-off:  CPU attention with TRON_AMX_DISABLE=1 (the AVX path), prompt 1024/8192, arms baseoff headoff newoff.
#   4. production serving back up through platformd; evidence copied to issue4525/evidence/pr4587-3bda/runtron/.
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap).
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4587-20260924
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/runtron
REPO=/home/jhan/workspace/tron
BASE_SHA=996f58ec828615789f1cc3aca8ee02baac78643b
HEAD_SHA=633cb88896ecb5daddbf74c77fb403e9f40c930c
NEW_SHA=c73e7fb2f99c8f369c809929d1df15bea507cdc3
export RT_BASE=/var/tmp/jhan/tron-main0922/gen/runtron.main0924
export RT_HEAD=/var/tmp/jhan/tron-i4525rt/gen/runtron.pr4557
export RT_NEW=/var/tmp/jhan/tron-i4525rt2/gen/runtron.pr4587
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
RT_CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
END_BY=${END_BY:-$(date -u -d 'today 01:30' +%FT%TZ)}
END_EPOCH=$(date -u -d "$END_BY" +%s); [ "$END_EPOCH" -gt "$(date -u +%s)" ] || END_EPOCH=$((END_EPOCH + 86400))
mkdir -p "$RES" "$EXEC/logs" "$EV"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$END_EPOCH" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
exec >>"$LOG" 2>&1
echo "=== $NAME chain started $(ts) pid $$ base=$BASE_SHA head=$HEAD_SHA new=$NEW_SHA end=$(date -u -d @"$END_EPOCH" +%FT%TZ) ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
if ci_lease_busy; then step_done start "CI lease busy: abort"; echo lease >"$RES/chain.done"; exit 1; fi

# ---- 1. builds (sequential, our half) ----
build() {  # $1 sha $2 worktree $3 suffix
  RES=$RES SRC=$REPO COMMIT=$1 WT=$2 SUFFIX=$3 CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  local bin=$2/gen/runtron.$3 n=0
  [ -x "$bin" ] && n=$(strings "$bin" | grep -c ingested-qwen-3-4b-instruct-2507)
  echo "$(ts) build $3: $(cat "$RES/build-$3.done" 2>/dev/null) tip=$(git -C "$2" rev-parse --short HEAD) qwen3-4b plugin strings=$n"
  [ "$(cat "$RES/build-$3.done" 2>/dev/null)" = ok ] && [ "${n:-0}" -gt 0 ]
}
build "$BASE_SHA" /var/tmp/jhan/tron-main0922 main0924 && build "$HEAD_SHA" /var/tmp/jhan/tron-i4525rt pr4557 &&
  build "$NEW_SHA" /var/tmp/jhan/tron-i4525rt2 pr4587 ||
  { step_done builds "FAILED (see $RES/build-*.log)"; echo chain-failed-builds >"$RES/chain.done"; exit 1; }
step_done builds "ok base=$RT_BASE head=$RT_HEAD new=$RT_NEW"

# ---- 2. Step D: token identity ----
# Production engines hold our cards. dut.sh serving-down checks that they are idle, then stops them through platformd.
# If it refuses, smoke.sh keeps retrying through the idle takeover of lib-guard.sh.
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); smoke.sh retries"
fi
for spec in "cpu 1024 base head head2 new new2 baseoff headoff newoff" "cpu 8192 base head new baseoff headoff newoff" \
            "fpga 1024 base head new" "fpga 8192 base head new"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$C/smoke.sh"
  step_done D "$attn p$prompt: $(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)"
done

# ---- 3. Step E: performance ----
cells() {  # prompt lengths -> CELLS_ALL lines
  local p out=""
  for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done
  printf '%s' "${out%$'\n'}"
}
run_e() {  # $1 name $2 attns $3 arms $4 pairs $5.. prompts
  local name=$1 attns=$2 arms=$3 pairs=$4; shift 4
  past_end && { step_done "$name" "skipped: past END_BY"; return; }
  NAME=$name CELLS_ALL="$(cells "$@")" ARMS="$arms" ATTNS="$attns" REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="$arms" WEDPERF_PAIRS="$pairs" bash "$C/campaign.sh"
  step_done "$name" "$(cat "$EXEC/logs/$name.done" 2>/dev/null)"
}
run_e i4587-E-cpu cpu "base head new" "head:base new:base new:head" 1024 2048 8192
run_e i4587-E-fpga fpga "base head new" "head:base new:base new:head" 1024 8192
run_e i4587-E-off cpu "baseoff headoff newoff" "headoff:baseoff newoff:baseoff newoff:headoff" 1024 8192

# ---- 4. serving back up, evidence copy ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
for n in $NAME i4587-E-cpu i4587-E-fpga i4587-E-off; do
  [ -d "$EXEC/results/$n" ] && mkdir -p "$EV/$n" && cp -r "$EXEC/results/$n"/. "$EV/$n/" 2>/dev/null
  cp "$EXEC/logs/$n.log" "$EV/" 2>/dev/null
done
cp "$LOG" "$EV/" 2>/dev/null
step_done end "chain finished"
echo "chain-finished" >"$RES/chain.done"
echo "=== $NAME chain finished $(ts) ==="
