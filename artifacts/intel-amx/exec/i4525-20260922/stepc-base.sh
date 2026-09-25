#!/usr/bin/env bash
# i4525-20260922 Step C, base half (runs ON delphi-3bda, by hand after chain4 finishes): the plan's pass rule compares the
# host-suite pass/fail set of the branch with the one of main, so main 0a51385e95 gets the same 16-lane AMX-off tree
# (/var/tmp/jhan/tron-i4525cbase), `make build-test-host` and `make test-host`, with production serving taken down through
# platformd after the idle check (dut.sh serving-down) and brought back up at the end (dut.sh serving-up).
# Usage: nohup bash stepc-base.sh </dev/null >/dev/null 2>&1 &
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4525-20260922
RES=$EXEC/results/i4525-20260922
LOG=$EXEC/logs/i4525-20260922-stepc-base.log
WT=/var/tmp/jhan/tron-i4525cbase
NIX=/home/jhan/.nix-profile/bin/nix
END_BY=${END_BY:-2026-09-23T01:35:00Z}; END_EPOCH=$(date -u -d "$END_BY" +%s)
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$END_EPOCH" ]; }
exec >>"$LOG" 2>&1
echo "=== stepc-base started $(ts) pid $$ ==="
rm -f "$RES/stepc-base.done"
# 1. tree + configure (A2 flags) and the build half; serving may be up during the build
RES=$RES SRC=/home/jhan/workspace/tron COMMIT=0a51385e95aabbe99876b3f6eea880b846d7117a WT=$WT SUFFIX=i4525cbase \
  CONFIGURE_ARGS='--preset native -DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF' \
  TARGETS=libfuse3_external TESTS= JOBS=8 bash "$C/build2.sh"
[ "$(cat "$RES/build-i4525cbase.done" 2>/dev/null)" = ok ] || { echo "$(ts) configure failed"; echo configure-failed >"$RES/stepc-base.done"; exit 1; }
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c 72-143,216-287 "$NIX" develop --command bash -c '
    set -o pipefail; make build-test-host NPROC_BUILD=48 2>&1 | grep -E "error|FAILED|ninja: no work|Linking CXX executable" | tail -80; echo "build-test-host rc=${PIPESTATUS[0]}"
    grep -E "^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS|BUILD_TEST_MODELS):" gen/CMakeCache.txt | tr "\n" " "; echo' ) >"$RES/build-test-host-i4525cbase.txt" 2>&1
echo "$(ts) build-test-host (base) done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=' "$RES/build-test-host-i4525cbase.txt" | tr '\n' ' ')"
grep -q 'build-test-host rc=0' "$RES/build-test-host-i4525cbase.txt" || { echo "$(ts) build failed; rebuilding with -k 0"
  ( cd "$WT" && nice -n10 taskset -c 72-143,216-287 "$NIX" develop --command bash -c '
      set -o pipefail; targets=$(bin/slice build-targets --build-dir=gen --filter=host); cmake --build gen --target $targets -j 48 -- -k 0 2>&1 | grep -E "error:|FAILED:" | head -40; echo "build-k0 rc=${PIPESTATUS[0]}"
      for t in $targets; do [ -x "gen/$t" ] || echo "missing binary: $t"; done' ) >"$RES/build-test-host-k0-i4525cbase.txt" 2>&1; }
past_end && { echo "$(ts) past END_BY; test-host skipped"; echo "build-only" >"$RES/stepc-base.done"; exit 0; }
# 2. serving down (idle check inside dut.sh), test-host, serving up
if rinzler_active; then IDLE_MIN=5 timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || { echo "$(ts) serving-down refused/failed; test-host skipped"; echo "serving-busy" >"$RES/stepc-base.done"; exit 1; }; TOOK_DOWN=1; else TOOK_DOWN=0; fi
( cd "$WT" && nice -n10 taskset -c 72-143,216-287 "$NIX" develop --command bash -c '
    set -o pipefail; SYSTEM_CONFIG="--instance 1,2" timeout -k 60 3600 make test-host 2>&1 | tail -100; echo "test-host rc=${PIPESTATUS[0]}"' ) >"$RES/test-host-i4525cbase.txt" 2>&1
echo "$(ts) test-host (base): $(grep -E 'test-host rc=|passed|failed' "$RES/test-host-i4525cbase.txt" | tail -3 | tr '\n' ' ')"
if [ "$TOOK_DOWN" = 1 ] && ! ci_lease_busy 600 && ! rinzler_active; then timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$?"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ')"
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/3bda-first-test; mkdir -p "$EV"; cp "$RES"/*i4525cbase* "$EV/" 2>/dev/null; cp "$LOG" "$EV/" 2>/dev/null
echo done >"$RES/stepc-base.done"
echo "=== stepc-base finished $(ts) ==="
