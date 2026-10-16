#!/usr/bin/env bash
# i4557squash-20261006 chain2 (runs ON delphi-3bda, setsid nohup): steps 3-5 only; the unit tests of chain.sh passed at 13:31-13:36 UTC,
# its runtron builds failed because the cross-avx512 preset no longer exists on main.
#   1. wait for the nightly CI lease to clear, then claim the machine (people-check);
#   2. unit tests in the rsynced tree /var/tmp/jhan/tron-issue4525 (lint-notes, gen all targets, gen-amxoff 4 tests);
#   3. build runtron for base = main dd6e85226b (tron-main0922, SUFFIX main1006) and head = c5d44bd86f (tron-i4525rt2, SUFFIX squash);
#   4. Step D token identity: cpu p1024 arms base head head2 baseoff headoff, then fpga p1024 base head;
#   5. serving back up through platformd, claim released, evidence copied.
# Fork of exec/results/i4557final-20261001/chain-final.sh. Never edit while it runs (NFS stale-handle trap).
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4557squash-20261006
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/squash-3bda
REPO=/home/jhan/workspace/tron
BASE_SHA=dd6e85226b
HEAD_SHA=c5d44bd86fe97914d2d3c7144b8045ebfad9fba0
UT=/var/tmp/jhan/tron-issue4525
T=/var/tmp/jhan/tron-issue4525-tests/squash-20261006
export RT_BASE=/var/tmp/jhan/tron-main0922/gen/runtron.main1006
export RT_HEAD=/var/tmp/jhan/tron-i4525rt2/gen/runtron.squash
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
RT_CONFIGURE='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='   # cross-avx512 preset removed by PR 4726; native = explicit AVX-512 flags, no -march=native
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
mkdir -p "$RES" "$EXEC/logs" "$EV" "$T"; rm -f "$RES/chain.done"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
finish() {
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
  elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
  else t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up; echo "$(ts) serving-up rc=$? in $(( $(date +%s) - t0 )) s"; fi
  echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
  bash "$EXEC/people-check.sh" --release; echo "$(ts) claim release rc=$?"
  cp -r "$RES"/. "$EV/" 2>/dev/null; cp "$T"/*.log "$EV/" 2>/dev/null; cp "$EXEC/logs/$NAME.log" "$LOG" "$EV/" 2>/dev/null
  step_done end "$1"
  echo "$1" >"$RES/chain.done"
  echo "=== $NAME chain finished $(ts): $1 ==="
}
exec >>"$LOG" 2>&1
echo "=== $NAME chain started $(ts) pid $$ base=$BASE_SHA head=$HEAD_SHA ==="
# ---- 1. wait for the lease, then claim ----
wait_for_ci_release 50400 || { step_done start "lease still busy after 14 h: abort"; echo lease >"$RES/chain.done"; exit 1; }
n=0; until bash "$EXEC/people-check.sh" --claim "PR 4557 squash re-run (unit tests + token identity), ~1.5 h"; do
  n=$((n+1)); [ "$n" -ge 12 ] && { step_done start "machine not free after 12 checks: abort"; echo busy >"$RES/chain.done"; exit 1; }; sleep 1800; done
step_done start "lease clear, claimed at $(ts)"
echo "$(ts) machine: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo)"
# ---- 3. build base and head runtron ----
for spec in "main1006|$BASE_SHA|/var/tmp/jhan/tron-main0922" "squash|$HEAD_SHA|/var/tmp/jhan/tron-i4525rt2"; do
  suf=${spec%%|*}; rest=${spec#*|}; sha=${rest%%|*}; wt=${rest#*|}
  [ "$(git -C "$wt" status --porcelain | wc -l)" -eq 0 ] || { step_done build "$wt dirty: abort"; finish chain-failed-dirty-worktree; exit 1; }
  t0=$(date +%s)
  RES=$RES SRC=$REPO COMMIT=$sha WT=$wt SUFFIX=$suf CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=48 bash "$B"; brc=$?
  bin=$wt/gen/runtron.$suf; n=0; [ -x "$bin" ] && n=$(strings "$bin" | grep -c ingested-qwen-3-4b-instruct-2507)
  if [ "$(cat "$RES/build-$suf.done" 2>/dev/null)" = ok ] && [ "${n:-0}" -gt 0 ]; then step_done build-$suf "ok tip=$(git -C "$wt" rev-parse HEAD) in $(( $(date +%s) - t0 )) s"
  else step_done build-$suf "FAILED rc=$brc done=$(cat "$RES/build-$suf.done" 2>/dev/null)"; finish chain-failed-build-$suf; exit 1; fi
done
sha256sum "$RT_BASE" "$RT_HEAD" | tee "$RES/binaries.sha256"
# ---- 4. Step D ----
if rinzler_active; then
  t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down; echo "$(ts) serving-down rc=$? in $(( $(date +%s) - t0 )) s"
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
# ---- 5. finish ----
finish chain-finished
