#!/usr/bin/env bash
# i4934-20261015 ablation builds (run ON delphi-3bda, our half, detached): two timing probes of the fix built from COMMIT
# in the worktree /var/tmp/jhan/tron-i4934abl (ablations.py: a1 tail rows through the reader, a2 constant block mask).
# Steps, each after wait_slot (CI lease with 600 s grace, other people, the 02:10-03:45 UTC pre-CI hold) and END_BY:
#   0. wait until WAIT_FOR exists (default exec/logs/i4934-perf-fpga.done: both perf drivers are done, so the build disturbs no profile)
#   1. build2.sh: the unmodified COMMIT, CONF_VNNI (BUILD_INGEST_MODELS=ON, AMX dispatch ON, K_VNNI ON), TARGETS=runtron,
#      no tests -> gen/runtron.abl (the base of both probes; its sha256 must equal runtron.fix's build? no: a fresh build,
#      recorded, not compared)
#   2. per ablation: apply, `cmake --build gen --target runtron -j64` inside nix develop, copy gen/runtron -> gen/runtron.<a>,
#      check the qwen3-4b tp2 plugin is in, git checkout -- the file.
#   end. results/i4934-abl/abl.done = ok | failed-<list>; log exec/logs/i4934-abl.log
# Usage (on 3bda): COMMIT=<full sha> END_BY=<ISO UTC> [WAIT_FOR=<file>] bash abl-build.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
B=$EXEC/i4525-20260922/build2.sh
NIX=/home/jhan/.nix-profile/bin/nix
export NAME=i4934-abl
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
COMMIT=${COMMIT:?COMMIT (full sha of the fix commit) is required}
END_BY=${END_BY:?END_BY (ISO UTC) is required}
WT=/var/tmp/jhan/tron-i4934abl
OUR_CPUS=${OUR_CPUS:-72-143,216-287}
REPO=/home/jhan/workspace/tron
CONF='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
PROBE_DONE=${WAIT_FOR:-$EXEC/logs/i4934-perf-fpga.done}   # the builds start after this file exists (default: after both perf drivers, so no build disturbs a profile)
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/abl.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
exec >>"$LOG" 2>&1
rm -f "$RES/abl.done"
echo "=== $NAME started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT END_BY=$END_BY ==="
git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || { step_done start "$COMMIT not in the shared store: abort"; echo failed-start >"$RES/abl.done"; exit 1; }
w=0
until [ -e "$PROBE_DONE" ]; do past_end && { step_done 0 "past END_BY before probe.done"; echo stopped-end-by >"$RES/abl.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting for $PROBE_DONE"; w=1; sleep 120; done
wait_slot "build abl"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=abl CONFIGURE_ARGS="$CONF" TARGETS=runtron TESTS="" JOBS=64 bash "$B"
bd=$(cat "$RES/build-abl.done" 2>/dev/null || echo missing)
step_done 1 "build abl: $bd; $(head -c 300 "$RES/build-abl.txt" 2>/dev/null | tr '\n' ' ')"
[ "$bd" = ok ] || { echo failed-build >"$RES/abl.done"; exit 1; }
failed=""
while IFS='|' read -r a file meaning; do
  past_end && { step_done "$a" "skipped: past END_BY"; failed="$failed $a-skipped"; continue; }
  wait_slot "ablation $a"
  if ! python3 "$D/ablations.py" apply "$a" "$WT"; then step_done "$a" "apply failed"; failed="$failed $a-apply"; continue; fi
  echo "$(ts) $a: $(git -C "$WT" diff --stat | tail -1)"
  t0=$(date +%s)
  ( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" "$NIX" develop --command bash -c '
      set -o pipefail
      cmake --build gen --target runtron -j64 2>&1 | grep -E "error|FAILED" | sed -n 1,60p
      exit ${PIPESTATUS[0]}' ) >"$RES/$a-build.log" 2>&1
  brc=$?
  echo "$(ts) $a: build of runtron rc=$brc in $(( $(date +%s) - t0 )) s"
  if [ $brc -ne 0 ]; then
    step_done "$a" "build failed rc=$brc (see $a-build.log)"; failed="$failed $a-build"
  else
    cp "$WT/gen/runtron" "$WT/gen/runtron.$a"
    n=$(strings "$WT/gen/runtron.$a" | grep -c "ingested-qwen-3-4b-instruct-2507-tp2")
    if [ "${n:-0}" -gt 0 ]; then step_done "$a" "ok: runtron.$a $(sha256sum "$WT/gen/runtron.$a" | cut -c1-16) ($meaning)"; else step_done "$a" "runtron.$a lacks the qwen3-4b tp2 plugin"; failed="$failed $a-plugin"; fi
  fi
  git -C "$WT" checkout -- "$file" && echo "$(ts) $a: $file restored ($(git -C "$WT" status --short | wc -l) files still changed)"
done < <(python3 "$D/ablations.py" list)
if [ -z "$failed" ]; then echo ok >"$RES/abl.done"; else echo "failed-$(echo $failed | tr ' ' ',')" >"$RES/abl.done"; fi
step_done end "$(cat "$RES/abl.done")"
echo "=== $NAME finished $(ts): $(cat "$RES/abl.done") ==="
