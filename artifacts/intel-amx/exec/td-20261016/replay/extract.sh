#!/usr/bin/env bash
# extract.sh: pull the layer-0 and layer-1 attention inputs (WQ roped, WK roped, WV) and the
# o_proj output (WO) of one td-20261016 arm out of its 20 GB --intermediates-file on delphi-3bda.
# One grep pass per arm on the local NVMe disk, output under /var/tmp/jhan/td/replay/ (NOT NFS).
# Usage (from claude-box): bash extract.sh <arm> [<arm> ...]     (an arm must be finished:
# 'run <arm> rc=0' in exec/results/td-20261016/runs.txt).
set -u
RUNS=/home/jhan/workspace/intel-AMX/exec/results/td-20261016/runs.txt
for arm in "$@"; do
  grep -q "^run $arm rc=0" "$RUNS" || { echo "$arm: not finished (no 'run $arm rc=0' in runs.txt)"; continue; }
  ssh delphi-3bda "mkdir -p /var/tmp/jhan/td/replay && cd /var/tmp/jhan/td/replay && \
    nice -n10 taskset -c 72-143 env LC_ALL=C grep -E '^ *(WQ roped|WK roped|WV|WO) layer (0|1) of token ' /var/tmp/jhan/td/$arm.full > $arm-L01.txt && \
    echo done > $arm-L01.done && ls -la $arm-L01.txt && cut -c1-50 $arm-L01.txt | sed -E 's/ of token [0-9]+//; s/^ *//' | sort | uniq -c"
done
