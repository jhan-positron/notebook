#!/usr/bin/env bash
# fetch.sh <result folder name>...: one login to CRB (marker check first) that copies result folders to crb/results/.
R=/home/jhan/workspace/titan/cache-perf/crb/results
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop" >&2; exit 3; fi'
ssh -o BatchMode=yes -o ConnectTimeout=15 jhan@192.168.2.45 "$M; tar cf - -C ~/cache-perf/results $*" | tar xf - --no-same-owner -C $R/
echo "status ${PIPESTATUS[*]}"
