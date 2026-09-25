#!/usr/bin/env bash
# i4525-20260922 host test suite step (runs ON delphi-3bda): in worktree WT (already configured and built by build.sh),
# run `make build-test-host` (every host test target) and `make test-host` (bin/slice run --filter=host --exclude-tag=slow)
# inside nix develop, on our half of the machine, with SYSTEM_CONFIG="--instance 1,2" (core set only; the fake device
# touches no hugepage file). Records the CMake cache feature values before and after: the Make targets reconfigure gen/
# and may drop non-default options (design G27 / vnnik4 chain 2026-09-15 "cache: TRON_K_VNNI=ON kept" check).
# Waits for the CI lease and the campaign flock like exec/vnnik4-20260915/chain.sh step 2.
# Usage: RES=... WT=/var/tmp/jhan/tron-<name> SUFFIX=<name> [OUR_CPUS=72-143,216-287] bash host-suite.sh
: "${RES:?}" "${WT:?}" "${SUFFIX:?}"
OUR_CPUS=${OUR_CPUS:-72-143,216-287}
NIX=/home/jhan/.nix-profile/bin/nix
EXEC=/home/jhan/workspace/intel-AMX/exec
LOG=${LOG:-$RES/host-suite-$SUFFIX.log}
mkdir -p "$RES"
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
echo "=== host suite $SUFFIX in $WT started $(ts) pid $$ ==="
rm -f "$RES/host-suite-$SUFFIX.done"
while ci_lease_busy; do echo "$(ts) CI lease busy; host suite waits"; sleep 120; done
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
until flock -n "$LOCK_FD"; do echo "$(ts) campaign flock held; host suite waits"; sleep 30; done
cache_line() { grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|TRON_K_VNNI|BUILD_INGEST_MODELS|TRON_IGNORE_NAN):' "$WT/gen/CMakeCache.txt" 2>/dev/null | tr '\n' ' '; }
echo "cache before: $(cache_line)"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c "$OUR_CPUS" "$NIX" develop --command bash -c '
    set -o pipefail
    make build-test-host NPROC_BUILD=96 2>&1 | grep -E "error|FAILED|ninja: no work|Linking CXX executable" | tail -60; echo "build-test-host rc=${PIPESTATUS[0]}"
    SYSTEM_CONFIG="--instance 1,2" make test-host 2>&1 | tail -80; echo "test-host rc=${PIPESTATUS[0]}"' ) >"$RES/host-suite-$SUFFIX.txt" 2>&1
echo "cache after:  $(cache_line)"
echo "$(ts) host suite done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=' "$RES/host-suite-$SUFFIX.txt" | tr '\n' ' ')"
grep -E 'passed|failed|skipped|makespan' "$RES/host-suite-$SUFFIX.txt" | tail -5
exec {LOCK_FD}>&-
if grep -q 'build-test-host rc=0' "$RES/host-suite-$SUFFIX.txt" && grep -q 'test-host rc=0' "$RES/host-suite-$SUFFIX.txt"; then echo ok >"$RES/host-suite-$SUFFIX.done"; else echo failed >"$RES/host-suite-$SUFFIX.done"; fi
echo "=== host suite $SUFFIX finished $(ts): $(cat "$RES/host-suite-$SUFFIX.done") ==="
