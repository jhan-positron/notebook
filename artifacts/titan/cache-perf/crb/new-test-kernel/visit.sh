#!/usr/bin/env bash
# visit.sh - one visit to CRB for Parts B and C: marker check, then run_bwx.sh with the steps given.
# Usage: [STOP_AT=<UTC|none>] [ENVV="NAME=value ..."] visit.sh <log name> STEP...
# Run only after the Slack check of handoff.md. The log goes to new-test-kernel/<log name>.log.
N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel
log=$N/$1.log; shift
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'
ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \
  "$M; cd ~/cache-perf/bwx-20261113 && STOP_AT=${STOP_AT:-none} BWX_SHA256=5b702073586a536e85002a39eaf01c144167e4a494bdbe90353c8e2caad826f1 ${ENVV:-} ./run_bwx.sh $*" < /dev/null > "$log" 2>&1
echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"
