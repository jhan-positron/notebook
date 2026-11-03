#!/usr/bin/env bash
# td-20261016 (runs ON delphi-3bda, detached, our half only): build the "clean" runtron of issue #4444 = main 72308ec90c
# with TRON_AMX_DISPATCH=OFF and TRON_K_VNNI=OFF (the row-major binary: every page scored by the AVX-512 dotter), as a
# 3bda-local worktree of the shared repo, like the earlier /var/tmp/jhan/tron-* worktrees. Output: /var/tmp/jhan/tron-td-clean/gen/runtron.clean
# Usage (on 3bda): bash build-clean.sh    Log: exec/logs/td-build-clean.log
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
LOG=$EXEC/logs/td-build-clean.log
REPO=/home/jhan/workspace/tron
SHA=72308ec90c80318403c4575dd9ce4a3bc9af5033
WT=/var/tmp/jhan/tron-td-clean
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
CONF='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== build-clean started $(ts) on $(hostname) ==="
if [ ! -d "$WT" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || { echo "$(ts) worktree add failed"; exit 1; }
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || { echo "$(ts) $WT is not at $SHA"; exit 1; }
[ -d "$WT/ingest/traces" ] || cp -r /var/tmp/jhan/tron-main1010/ingest/traces "$WT/ingest/"
cd "$WT" || exit 1
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c "cmake $CONF 2>&1 | tail -3; echo configure rc=\${PIPESTATUS[0]}"
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'cmake --build gen --target runtron -j48 2>&1 | grep -E "error|FAILED|warning: unused" | head -20; echo "build rc=${PIPESTATUS[0]}"'
echo "$(ts) build wall=$(( $(date +%s) - t0 ))s"
if [ -x gen/runtron ]; then cp gen/runtron gen/runtron.clean && sha256sum gen/runtron.clean && grep -c "TRON_AMX_DISPATCH:BOOL=OFF" gen/CMakeCache.txt; echo "$(ts) ok runtron.clean"; else echo "$(ts) FAILED no gen/runtron"; fi
echo "=== build-clean finished $(ts) ==="
