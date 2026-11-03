#!/usr/bin/env bash
# benstack-20261021: run run-one.sh for ONE branch only after the PR 5047 chain (exec/pr5047-20261020/chain.sh) has
# written its final marker, so that no build or test of ours overlaps the chain's performance repetitions on 3bda.
# Usage (on 3bda, detached): N=2|3|4 SHA=<full 40-hex sha> bash run-after-chain.sh
# Log: exec/logs/benstack-20261021-run-after-chain-bpN.log. Then run-one.sh's own log and marker.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
set -u
N=${N:?N=2|3|4 is required}
SHA=${SHA:?SHA=<full sha> is required}
EXEC=/home/jhan/workspace/intel-AMX/exec
CHAIN_DONE=$EXEC/results/pr5047-20261020/chain.done
LOG=$EXEC/logs/benstack-20261021-run-after-chain-bp$N.log
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
echo "=== run-after-chain bp$N started $(ts) pid $$ sha=$SHA; waiting for $CHAIN_DONE ==="
while [ ! -s "$CHAIN_DONE" ]; do sleep 300; done
echo "$(ts) chain.done: $(cat "$CHAIN_DONE"); launching run-one.sh"
N=$N SHA=$SHA bash "$EXEC/benstack-20261021/run-one.sh"
echo "=== run-after-chain bp$N finished $(ts): $(cat "$EXEC/results/benstack-20261021/run-one-bp$N.done" 2>/dev/null) ==="
