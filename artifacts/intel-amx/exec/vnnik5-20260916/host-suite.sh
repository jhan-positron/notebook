#!/usr/bin/env bash
# vnnik5-20260916 step 2: the whole host test suite with TRON_K_VNNI=ON on the rebased
# head (worktree /var/tmp/jhan/tron-vnnik5, built by build.sh). Waits for build.sh to
# finish with "ok", then for the CI lease and the campaign flock, then runs
# make build-test-host (every test target compiles with the option) and make test-host
# (bin/slice run --filter=host --exclude-tag=slow) on our half (SYSTEM_CONFIG=--instance 1,2).
# Copy of chain.sh step 2 (vnnik4-20260915) with vnnik5 paths. Usage (on delphi-3bda):
# nohup host-suite.sh &
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/vnnik5-20260916
LOG=$EXEC/logs/vnnik5-host-suite.log
WT=/var/tmp/jhan/tron-vnnik5
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== host-suite.sh started $(ts) pid $$ ==="
rm -f "$RES/host-suite.done"
for i in $(seq 1 360); do [ -f "$RES/build.done" ] && break; sleep 20; done
b=$(cat "$RES/build.done" 2>/dev/null)
echo "$(ts) build.done = '$b'"
if [ "$b" != ok ]; then echo "build not ok; host suite skipped" | tee "$RES/host-suite.done"; exit 1; fi
while ci_lease_busy; do echo "$(ts) CI lease busy; host suite waits"; sleep 120; done
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; host suite waits"; sleep 30; done
echo "$(ts) step 2: host test suite with TRON_K_VNNI=ON"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --command bash -c '
    set -o pipefail
    make build-test-host NPROC_BUILD=96 2>&1 | grep -E "error|FAILED|warning: .*(k_vnni|save_k)|Linking|ninja: no work" | tail -40; echo "build-test-host rc=${PIPESTATUS[0]}"
    grep -q "TRON_K_VNNI:BOOL=ON" gen/CMakeCache.txt && echo "cache: TRON_K_VNNI=ON kept" || echo "cache: TRON_K_VNNI NOT ON (reconfigure dropped it)"
    SYSTEM_CONFIG="--instance 1,2" make test-host 2>&1 | tail -80; echo "test-host rc=${PIPESTATUS[0]}"' ) >"$RES/host-suite.txt" 2>&1
echo "$(ts) step 2 done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|cache:' "$RES/host-suite.txt" | tr '\n' ' ')"
exec {LOCK_FD}>&-
grep -E 'rc=|cache:|passed|failed|skipped' "$RES/host-suite.txt" | tail -8 > "$RES/host-suite.done"
echo "=== host-suite.sh finished $(ts) ==="
