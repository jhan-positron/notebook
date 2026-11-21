#!/usr/bin/env bash
# visit8.sh - one visit to CRB for the design tackle-8mb.md: marker check, then run_bwx8.sh with the steps given.
# Usage: STOP_AT=<UTC|none> SESSION=<1|2> [SESSION1_END=<UTC>] [BWX8_SHA256=<digest>] [ENVV="NAME=value ..."]
#        visit8.sh <log name> [--dry-run] [--from IDX] STEP...
# Run only after the Slack check of handoff.md. The log goes to new-test-kernel/<log name>.log.
# STOP_AT and SESSION have no default here: decide them from the current reservations at every visit.
N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel
: "${STOP_AT:?set STOP_AT to a UTC time or to none}" "${SESSION:?set SESSION to 1 or 2}" "${1:?give a log name}"
# These four values go into the remote command line. A blank or a shell character would split or change it.
for v in STOP_AT SESSION SESSION1_END BWX8_SHA256; do
  [[ ${!v:-} =~ ^[A-Za-z0-9:.+-]*$ ]] || { echo "$v holds a character outside A-Z a-z 0-9 : . + - (write a time as 2026-11-15T03:00Z): no login" >&2; exit 2; }
done
log=$N/$1.log; shift
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'
ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \
  "$M; cd ~/cache-perf/bwx8-20261114 && STOP_AT=$STOP_AT SESSION=$SESSION SESSION1_END=${SESSION1_END:-} BWX8_SHA256=${BWX8_SHA256:-} ${ENVV:-} ./run_bwx8.sh $*" < /dev/null > "$log" 2>&1
echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"
