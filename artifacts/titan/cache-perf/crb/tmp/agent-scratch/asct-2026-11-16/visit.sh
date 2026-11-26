#!/usr/bin/env bash
# visit.sh LOG COMMAND...  - one login to CRB: marker check first, then COMMAND in ~/cache-perf/asct-20261116.
# With SEND=1 the folder crb/ of this directory is copied to CRB first (tar through the same ssh call).
# Run only after reading Slack #phoenix-crb. The log goes to this folder as LOG.log.
X=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/asct-2026-11-16
log=$X/$1.log; shift
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'
W='mkdir -p ~/cache-perf/asct-20261116 ~/cache-perf/results && cd ~/cache-perf/asct-20261116'
if [ "${SEND:-0}" = 1 ]; then
  tar cf - -C $X/crb . | ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \
    "$M; $W && tar xf - --no-same-owner && $*" > "$log" 2>&1
else
  ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 "$M; $W && $*" < /dev/null > "$log" 2>&1
fi
echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"
