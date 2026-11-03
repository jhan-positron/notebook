#!/usr/bin/env bash
# td-20261016 (runs ON delphi-3bda, detached, our half only): build one runtron variant for the issue #4444 root-cause
# campaign as a 3bda-local worktree of the shared repo at a given commit. The commit comes from the NFS worktrees under
# ~/workspace/ai-runs/ (same object store). Output: /var/tmp/jhan/tron-td-<tag>/gen/runtron.<tag>
# Usage (on 3bda): TAG=<tag> SHA=<full sha> CONF='<cmake args>' bash build-variant.sh    Log: exec/logs/td-build-<tag>.log
set -u
TAG=${TAG:?}; SHA=${SHA:?}; CONF=${CONF:?}
EXEC=/home/jhan/workspace/intel-AMX/exec
LOG=$EXEC/logs/td-build-$TAG.log
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-td-$TAG
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== build-variant $TAG started $(ts) on $(hostname) sha=$SHA conf=[$CONF] ==="
if [ ! -d "$WT" ]; then
  git -C "$REPO" cat-file -e "$SHA^{commit}" || { echo "$(ts) $SHA not visible in $REPO"; exit 1; }
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || { echo "$(ts) worktree add failed"; exit 1; }
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || { echo "$(ts) $WT is not at $SHA"; exit 1; }
[ -d "$WT/ingest/traces" ] || cp -r /var/tmp/jhan/tron-pr4/ingest/traces "$WT/ingest/"
cd "$WT" || exit 1
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c "cmake $CONF 2>&1 | tail -3; echo configure rc=\${PIPESTATUS[0]}"
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'cmake --build gen --target runtron -j40 2>&1 | grep -E "error|FAILED" | head -20; echo "build rc=${PIPESTATUS[0]}"'
echo "$(ts) build wall=$(( $(date +%s) - t0 ))s"
if [ -x gen/runtron ]; then cp gen/runtron "gen/runtron.$TAG" && sha256sum "gen/runtron.$TAG" && grep -E "^TRON_(AMX_DISPATCH|K_VNNI):" gen/CMakeCache.txt | tr '\n' ' '; echo; echo "$(ts) ok runtron.$TAG"; else echo "$(ts) FAILED no gen/runtron"; fi
echo "=== build-variant $TAG finished $(ts) ==="
