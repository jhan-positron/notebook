#!/usr/bin/env bash
# Launcher for the single-attention campaign. Run ON delphi-3bda:
#   nohup bash ~/workspace/intel-AMX/exec/single-attn-20260901/launch-after-peer.sh >/dev/null 2>&1 &
# 1. waits for the peer session's last marker (exec/logs/fallback-20260901.done, ~21:00Z);
# 2. cherry-picks the probe commit (ref sa-probe-8e9296b) onto jhan-amx-fence, on this host;
# 3. verifies the probe text is visible here, then runs run-single-attn.sh with EXPECT_COMMIT.
set -u
EXEC=~/workspace/intel-AMX/exec
LOG=$EXEC/logs/single-attn-20260901.launcher.log
WT=~/workspace/tron-fence-amx
PEER_MARKER=$EXEC/logs/fallback-20260901.done
exec >>"$LOG" 2>&1
echo "=== launcher start $(date -u +%FT%TZ) ==="
deadline=$(( $(date -u +%s) + 4*3600 ))
while [ ! -e "$PEER_MARKER" ]; do
  [ $(date -u +%s) -ge $deadline ] && { echo "peer marker never appeared; giving up $(date -u +%FT%TZ)"; echo peer-timeout >"$EXEC/logs/single-attn-20260901.done"; exit 1; }
  sleep 60
done
echo "peer marker present ($(cat "$PEER_MARKER")) at $(date -u +%FT%TZ); waiting 90 s for the peer's cleanup"
sleep 90
if pgrep -x 'runtron(\.[a-z0-9]+)?' >/dev/null; then echo "runtron still running after peer marker; waiting up to 15 min"; for i in $(seq 1 30); do pgrep -x 'runtron(\.[a-z0-9]+)?' >/dev/null || break; sleep 30; done; fi
cd "$WT" || exit 1
if [ -n "$(git status --porcelain -- h src)" ]; then echo "worktree dirty, not touching:"; git status --porcelain -- h src; echo dirty-worktree >"$EXEC/logs/single-attn-20260901.done"; exit 1; fi
if grep -q "namespace attn_phase" h/tron/models/self_attention.hpp; then
  echo "probe already on the branch: $(git log --oneline -1)"
else
  git cherry-pick -x sa-probe-8e9296b || { echo "cherry-pick failed"; git cherry-pick --abort 2>/dev/null; echo cherry-pick-failed >"$EXEC/logs/single-attn-20260901.done"; exit 1; }
  echo "cherry-picked: $(git log --oneline -1)"
fi
sync; sleep 3
grep -q "namespace attn_phase" h/tron/models/self_attention.hpp || { echo "probe not visible after cherry-pick"; echo probe-not-visible >"$EXEC/logs/single-attn-20260901.done"; exit 1; }
export EXPECT_COMMIT=$(git rev-parse HEAD)
echo "launching run-single-attn.sh with EXPECT_COMMIT=$EXPECT_COMMIT at $(date -u +%FT%TZ)"
bash "$EXEC/single-attn-20260901/run-single-attn.sh"
echo "=== launcher end $(date -u +%FT%TZ) marker=$(cat $EXEC/logs/single-attn-20260901.done 2>/dev/null) ==="
