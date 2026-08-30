#!/usr/bin/env bash
# Capture the failure text of t_generate_host on the UNFIXED PR head 609dabba83
# (codex P1 on PR #3879): p3-q-scalar-gate.sh's negative control aborted
# (apport recorded SIGABRT) but discarded stderr and let apport spend 25 min
# dumping a 6 GB core. This run builds the pre-fix commit in an isolated
# worktree, disables core dumps, keeps stdout+stderr, and bounds the run.
# Usage: p3c-prefix-abort-message.sh [<unfixed-sha>]
set -u
EXEC=~/workspace/intel-AMX/exec
TAG=p3c-prefix-abort-message
LOG=$EXEC/logs/$TAG.log
MARKER=$EXEC/logs/$TAG.done
OUT=$EXEC/logs/$TAG.txt
COMMIT=${1:-609dabba83}
WT=/var/tmp/jhan/tron-$TAG
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== $TAG queued $(date -u +%FT%TZ) commit=$COMMIT host=$(hostname) ==="
source "$EXEC/lib-guard.sh"
wait_for_ci_release 28800 || { echo ci-never-released >"$MARKER"; exit 1; }
if rinzler_active; then J="-j6"; PIN="nice -n19 taskset -c 23,24,36,167,168,180"; else J="-j96"; PIN="nice -n10"; fi
deadline=$(( $(date +%s) + 7200 ))
until campaign_guard_acquire --allow-serving; do
  [ "$(date +%s)" -ge "$deadline" ] && { echo guard-refused >"$MARKER"; exit 1; }
  sleep 60
done
cleanup() {
  cd ~/workspace/tron-amx && git worktree remove --force "$WT" 2>/dev/null
  campaign_guard_release
}
cd ~/workspace/tron-amx || { echo no-checkout >"$MARKER"; campaign_guard_release; exit 1; }
git worktree remove --force "$WT" 2>/dev/null
git worktree add --detach "$WT" "$COMMIT" || { echo worktree-failed >"$MARKER"; campaign_guard_release; exit 1; }
trap cleanup EXIT
cd "$WT" || exit 1
: >"$OUT"
echo "commit $(git rev-parse HEAD) $(git log -1 --format=%s)" >>"$OUT"
echo "### mirror build of the UNFIXED head $(date -u +%FT%TZ)" >>"$OUT"
if $PIN nix develop --command bash -c \
    "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target t_generate_host $J 2>&1 | grep -E 'error|FAILED' | head -20; exit \${PIPESTATUS[0]}"; then
  echo "### t_generate_host, AMX on, core dumps off, 20 min bound (stdout+stderr, last 60 lines) $(date -u +%FT%TZ)" >>"$OUT"
  ( ulimit -c 0; $PIN timeout 20m ./gen/t_generate_host "Generate 400 tokens from a canned prompt with LLaMa 3 8B (2 layers)" 2>&1 | grep -v "^\[20" | tail -60 ) >>"$OUT"
  echo "exit=${PIPESTATUS[0]} (Catch2: nonzero = failed; 134 = SIGABRT; 124 = timeout)" >>"$OUT"
  echo "### same test with TRON_AMX_DISABLE=1 (kill switch) - must pass $(date -u +%FT%TZ)" >>"$OUT"
  ( ulimit -c 0; TRON_AMX_DISABLE=1 $PIN timeout 20m ./gen/t_generate_host "Generate 400 tokens from a canned prompt with LLaMa 3 8B (2 layers)" 2>&1 | grep -E "All tests passed|FAILED|failed|assertions" | tail -2 ) >>"$OUT"
else
  echo "BUILD FAILED" >>"$OUT"
fi
echo "### done $(date -u +%FT%TZ)" >>"$OUT"
echo recorded >"$MARKER"
echo "=== $TAG done $(date -u +%FT%TZ) ==="
