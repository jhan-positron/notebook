#!/usr/bin/env bash
# i4557final-20261001 chain (runs ON delphi-3bda, setsid nohup): Step D token identity for the final head of PR #4557.
#   base = main 996f58ec82 (existing binary runtron.main0924, built 2026-09-24), head = jhan-kv-typed-tensors c12df586b6.
# Steps: 1. build runtron.final in /var/tmp/jhan/tron-i4525rt2 (build2.sh, cross-avx512, AMX dispatch on);
#        2. Step D cpu p1024 arms base head head2 baseoff headoff (smoke.sh of i4587-20260924), then fpga p1024 base head
#           when the cpu cell took 25 min or less; 3. serving back up through platformd; claim released; evidence copied.
# Fork of exec/i4587-20260924/chain.sh with one head binary and no Step E. Never edit while it runs (NFS stale-handle trap).
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4557final-20261001
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/final-3bda
REPO=/home/jhan/workspace/tron
BASE_SHA=996f58ec828615789f1cc3aca8ee02baac78643b
HEAD_SHA=c12df586b654d026ca2640bd78d977fa4ebeccfe
WT=/var/tmp/jhan/tron-i4525rt2
export RT_BASE=/var/tmp/jhan/tron-main0922/gen/runtron.main0924
export RT_HEAD=$WT/gen/runtron.final
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
RT_CONFIGURE='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
mkdir -p "$RES" "$EXEC/logs" "$EV"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
finish() {  # $1 marker text; serving up + claim release + evidence copy always run
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
  elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
  else t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up; echo "$(ts) serving-up rc=$? in $(( $(date +%s) - t0 )) s"; fi
  echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
  bash "$EXEC/people-check.sh" --release; echo "$(ts) claim release rc=$?"
  cp -r "$RES"/. "$EV/" 2>/dev/null; cp "$EXEC/logs/$NAME.log" "$LOG" "$EV/" 2>/dev/null
  step_done end "$1"
  echo "$1" >"$RES/chain.done"
  echo "=== $NAME chain finished $(ts): $1 ==="
}
exec >>"$LOG" 2>&1
echo "=== $NAME chain started $(ts) pid $$ base=$BASE_SHA head=$HEAD_SHA ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent) claim=$(cat /var/tmp/3bda-claim.jhan 2>/dev/null)"
if ci_lease_busy; then step_done start "CI lease busy: abort"; echo lease >"$RES/chain.done"; exit 1; fi

# ---- 1. build runtron.final ----
PRE_SHA=$(git -C "$WT" rev-parse HEAD); PRE_STATUS=$(git -C "$WT" status --porcelain | wc -l)
echo "$(ts) worktree $WT before checkout: $PRE_SHA, uncommitted lines=$PRE_STATUS" | tee "$RES/worktree-before.txt"
[ "$PRE_STATUS" -eq 0 ] || { step_done build "worktree has uncommitted changes: abort"; finish chain-failed-dirty-worktree; exit 1; }
[ -x "$RT_BASE" ] && echo "$(ts) base binary $RT_BASE ok: $(ls -la "$RT_BASE" | cut -c1-80) tip=$(git -C /var/tmp/jhan/tron-main0922 rev-parse HEAD)" || { step_done build "base binary missing"; finish chain-failed-no-base; exit 1; }
t0=$(date +%s)
RES=$RES SRC=$REPO COMMIT=$HEAD_SHA WT=$WT SUFFIX=final CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=48 bash "$B"; brc=$?
n=0; [ -x "$RT_HEAD" ] && n=$(strings "$RT_HEAD" | grep -c ingested-qwen-3-4b-instruct-2507)
echo "$(ts) build final: rc=$brc done=$(cat "$RES/build-final.done" 2>/dev/null) tip=$(git -C "$WT" rev-parse HEAD) qwen3-4b plugin strings=$n in $(( $(date +%s) - t0 )) s"
if [ "$(cat "$RES/build-final.done" 2>/dev/null)" = ok ] && [ "${n:-0}" -gt 0 ]; then step_done build "ok head=$RT_HEAD tip=$(git -C "$WT" rev-parse HEAD) in $(( $(date +%s) - t0 )) s"
else step_done build "FAILED rc=$brc done=$(cat "$RES/build-final.done" 2>/dev/null) (see $RES/build-final.log)"; finish chain-failed-build; exit 1; fi
sha256sum "$RT_BASE" "$RT_HEAD" | tee "$RES/binaries.sha256"

# ---- 2. Step D ----
if rinzler_active; then
  t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down; echo "$(ts) serving-down rc=$? in $(( $(date +%s) - t0 )) s (nonzero: engines busy?; smoke.sh retries through the idle takeover)"
fi
t0=$(date +%s)
ATTN=cpu PROMPT=1024 LEN=256 SMOKE_ARMS="base head head2 baseoff headoff" bash "$C/smoke.sh"; src=$?
cpu_s=$(( $(date +%s) - t0 ))
step_done D-cpu "p1024: $(cat "$RES/smoke/cpu-p1024/smoke.done" 2>/dev/null) (smoke.sh rc=$src, $cpu_s s)"
if [ "$cpu_s" -le 1500 ]; then
  t0=$(date +%s)
  ATTN=fpga PROMPT=1024 LEN=256 SMOKE_ARMS="base head" bash "$C/smoke.sh"; src=$?
  step_done D-fpga "p1024: $(cat "$RES/smoke/fpga-p1024/smoke.done" 2>/dev/null) (smoke.sh rc=$src, $(( $(date +%s) - t0 )) s)"
else
  step_done D-fpga "skipped: the cpu cell took $cpu_s s (more than 25 min)"
fi

# ---- 3. serving back up, claim release, evidence ----
finish chain-finished
