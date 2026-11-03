#!/usr/bin/env bash
# benstack-20261021: the branch gates (run-one.sh for N = 2, 3, 4) one after another, and only after the PR 5047 chain
# (exec/pr5047-20261020/chain.sh) has written its final marker, so that no build or unit test of ours overlaps the
# chain's performance repetitions on 3bda. The sha of branch N is read from exec/results/benstack-20261021/sha-bpN.txt
# when the driver reaches N (a branch that becomes final later still joins). A branch whose two builds already exist
# at that sha (build-bpN.txt / build-bpNv.txt say "tip <sha>" and the .done markers say ok) is not rebuilt.
# Usage (on 3bda, detached): N_LIST="2 3 4" bash run-gates-after-chain.sh
# Log: exec/logs/benstack-20261021-run-gates-after-chain.log. Then run-one.sh's own logs and markers.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
N_LIST=${N_LIST:-"2 3 4"}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/benstack-20261021
CHAIN_DONE=$EXEC/results/pr5047-20261020/chain.done
LOG=$EXEC/logs/benstack-20261021-run-gates-after-chain.log
mkdir -p "$RES" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== run-gates-after-chain started $(ts) pid $$ on $(hostname) N_LIST=[$N_LIST]; waiting for $CHAIN_DONE ==="
while [ ! -s "$CHAIN_DONE" ]; do sleep 300; done
echo "$(ts) chain.done: $(cat "$CHAIN_DONE")"
built_at() {  # $1 tag, $2 sha: true when the tag's build is ok at that sha
  [ "$(cat "$RES/build-$1.done" 2>/dev/null)" = ok ] && grep -q "^tip $2\$" "$RES/build-$1.txt" 2>/dev/null
}
for N in $N_LIST; do
  sha=$(tr -d '[:space:]' <"$RES/sha-bp$N.txt" 2>/dev/null)
  if ! [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then echo "$(ts) bp$N: no sha in $RES/sha-bp$N.txt, skipped"; continue; fi
  skip=0
  if built_at "bp$N" "$sha" && built_at "bp${N}v" "$sha"; then skip=1; fi
  echo "$(ts) bp$N: sha=$sha SKIP_BUILD=$skip; launching run-one.sh"
  SKIP_BUILD=$skip N=$N SHA=$sha bash "$EXEC/benstack-20261021/run-one.sh"
  echo "$(ts) bp$N: run-one-bp$N.done = $(cat "$RES/run-one-bp$N.done" 2>/dev/null)"
done
echo "=== run-gates-after-chain finished $(ts) ==="
