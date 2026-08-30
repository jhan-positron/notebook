#!/usr/bin/env bash
# Follow-up to p3-q-scalar-gate.sh for codex finding #4 (K mirror arena
# accounting, 2026-08-28): on delphi-3bda, build the given commit in an
# isolated worktree (mirror config) and run the tests claude-box cannot:
#   t_tronstats_convention  - needs a live FUSE mount (/dev/fuse); validates the
#                             new /rinzler/stats/memory_pressure/k_mirror_arena_bytes
#                             manifest entry against the on-disk descriptors;
#   t_amx_arena_leak        - the real arena path (available() is link-wrapped
#                             to true in that binary, so it runs anywhere, but
#                             here AMX is real as well);
#   t_amx_numerics, t_llama_unit - regression on the AMX host at this commit.
# Usage: p3b-mirror-accounting.sh <commit-sha>
set -u
EXEC=~/workspace/intel-AMX/exec
TAG=p3b-mirror-accounting
LOG=$EXEC/logs/$TAG.log
MARKER=$EXEC/logs/$TAG.done
OUT=$EXEC/logs/$TAG.txt
COMMIT=${1:?usage: $0 <commit-sha>}
WT=/var/tmp/jhan/tron-$TAG
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== $TAG queued $(date -u +%FT%TZ) commit=$COMMIT host=$(hostname) ==="
source "$EXEC/lib-guard.sh"
wait_for_ci_release 28800 || { echo ci-never-released >"$MARKER"; exit 1; }
echo "=== CI released $(date -u +%FT%TZ) ==="
if rinzler_active; then J="-j6"; PIN="nice -n19 taskset -c 23,24,36,167,168,180"; else J="-j96"; PIN="nice -n10"; fi
# p3-q-scalar-gate.sh may still hold the campaign flock: wait for it (up to 2 h).
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
TESTS="t_amx_arena_leak t_tronstats_convention t_amx_numerics t_llama_unit"
echo "### mirror build $(date -u +%FT%TZ)" >>"$OUT"
if $PIN nix develop --command bash -c \
    "cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS= >/dev/null &&
     cmake --build gen --target $TESTS rinzler $J 2>&1 | grep -E 'error|FAILED' | head -20; exit \${PIPESTATUS[0]}"; then
  for t in $TESTS; do
    printf "%s: " "$t" >>"$OUT"
    $PIN ./gen/$t 2>/dev/null | grep -E "All tests passed|FAILED|failed|assertions|skipped" | tail -1 >>"$OUT" || echo "NO-RESULT" >>"$OUT"
  done
else
  echo "BUILD FAILED" >>"$OUT"
fi
echo "### done $(date -u +%FT%TZ)" >>"$OUT"
if grep -qE "FAILED|NO-RESULT" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== $TAG done $(date -u +%FT%TZ) marker=$(cat "$MARKER") ==="
