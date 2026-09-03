#!/usr/bin/env bash
# launch.sh - run from the editing host. Writes src/SHA256SUMS (so the DUT can
# verify it sees the same source content through NFS), then starts the
# campaign on delphi-3bda with nohup. RESUME=1 is passed through.
set -eu
HERE=~/workspace/intel-AMX/exec/perf-model-20260903
cd "$HERE/src" && sha256sum unit_bench.cpp memrate.c latency.c insn_loops.cpp >SHA256SUMS && cat SHA256SUMS
sync
ssh -o BatchMode=yes delphi-3bda "RESUME=${RESUME:-0} nohup bash ~/workspace/intel-AMX/exec/perf-model-20260903/run-perf-model.sh >/dev/null 2>&1 &"
echo "launched at $(date -u +%FT%TZ); follow ~/workspace/intel-AMX/exec/results/perf-model-20260903/campaign.log"
