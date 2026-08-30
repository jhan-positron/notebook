#!/usr/bin/env bash
# R0 phase A: build runtron (main 1407f48dd + router trace markers, branch
# jhan-router-p0) in the isolated tron-router-p0 worktree (shared via NFS home).
# Safe to run while serving is still up (nice 19, safe cores); once serving
# stops we rebuild/continue at full width (ninja is incremental).
set -u
EXEC=~/workspace/intel-AMX/exec
LOG="$EXEC/logs/r0-build.log"
MARKER="$EXEC/logs/r0-build.done"
mkdir -p "$EXEC/logs"
exec >>"$LOG" 2>&1
echo "=== r0 build start $(date -u +%FT%TZ) ==="
rm -f "$MARKER"
cd ~/workspace/tron-router-p0 || { echo tree-missing >"$MARKER"; exit 1; }

# Record the exact source state (trace markers may be committed or not).
echo "HEAD=$(git -C ~/workspace/tron-router-p0 rev-parse HEAD)"
echo "git status --short (empty = markers committed):"
git -C ~/workspace/tron-router-p0 status --short

# Parallelism: the CI lease (authoritative, lib-guard.sh) or live rinzler
# forces the safe-core light-load config; only a free machine builds wide.
source "$EXEC/lib-guard.sh"
if ci_lease_busy; then CI_BUSY=1; else CI_BUSY=0; fi
if [ "$CI_BUSY" -eq 1 ] || pgrep -x rinzler >/dev/null; then
  CPUS=89,94,96,108,233,238,240,252; J=8
else
  CPUS=0-287; J=96
fi
echo "ci_lease_busy=$CI_BUSY serving_up=$(pgrep -cx rinzler || true) cpus=$CPUS j=$J"

nix develop --command bash -c \
  "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON && \
   nice -n19 taskset -c $CPUS cmake --build gen --target runtron -j$J" \
  || { echo build-failed >"$MARKER"; exit 1; }

sha256sum gen/runtron

# Ingested plugin inventory: r0-campaign.sh reads the gpt-oss-120b-plugin=
# line below to decide whether a 120b runnability attempt is possible.
echo "ingested plugin names in runtron:"
PLUGINS=$(strings gen/runtron | grep -o 'ingested-[A-Za-z0-9._-]*' | sort -u)
echo "$PLUGINS"
# Prefer a tp2 name (the 3bda capture config is tp2: --instance 0,4, 2 cards).
M120=$(echo "$PLUGINS" | grep '^ingested-gpt-oss-120b' | grep -m1 'tp2$' || true)
[ -n "$M120" ] || M120=$(echo "$PLUGINS" | grep -m1 '^ingested-gpt-oss-120b' || true)
echo "gpt-oss-120b-plugin=${M120:-none}"

if echo "$PLUGINS" | grep -q 'ingested-gpt-oss-20b-tp2'; then
  echo "gpt-oss-20b-tp2 plugin present in runtron"
  echo ok >"$MARKER"
else
  echo "gpt-oss-20b-tp2 plugin MISSING from runtron"
  echo built-but-no-20b >"$MARKER"
fi
echo "=== r0 build end $(date -u +%FT%TZ) ==="
