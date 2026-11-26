#!/usr/bin/env bash
# visit_h2.sh - one visit to CRB for the test of hypothesis H2: marker check, then run_h2.sh.
# Usage: STOP_AT=<UTC|none> SESSION=<1|2> [SESSION1_END=<UTC>] [ENVV="NAME=value ..."]
#        visit_h2.sh <log name> [--dry-run] [--from IDX]
# Run only after the Slack check of handoff.md. The log goes to new-test-kernel/<log name>.log.
# STOP_AT and SESSION have no default here: decide them from the current reservations at every visit.
# SESSION1_END is the end of session 1 of run_h2.sh (line "## end utc=" in env.txt of the h2-s1 folder).
N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel
: "${STOP_AT:?set STOP_AT to a UTC time or to none}" "${SESSION:?set SESSION to 1 or 2}" "${1:?give a log name}"
# These three values go into the remote command line. A blank or a shell character would split or change it.
for v in STOP_AT SESSION SESSION1_END; do
  [[ ${!v:-} =~ ^[A-Za-z0-9:.+-]*$ ]] || { echo "$v holds a character outside A-Z a-z 0-9 : . + - (write a time as 2026-11-15T03:00Z): no login" >&2; exit 2; }
done
log=$N/$1.log; shift
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'
ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \
  "$M; cd ~/cache-perf/bwx8-20261114 && STOP_AT=$STOP_AT SESSION=$SESSION SESSION1_END=${SESSION1_END:-} ${ENVV:-} ./run_h2.sh $*" < /dev/null > "$log" 2>&1
echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"
