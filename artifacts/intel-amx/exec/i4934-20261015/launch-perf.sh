#!/usr/bin/env bash
# Launch perf-fix.sh detached on delphi-3bda from claude-box. The driver itself waits until the chain (chain-fix.sh) has
# finished, then runs on our half under campaign-fix.sh's guards (idle serving takeover through platformd, serving back up
# at its end). Usage: END_BY=<ISO UTC> [REPS=2] [WINDOW=10] bash launch-perf.sh
set -u
END_BY=${END_BY:?END_BY is required (ISO UTC)}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date"; exit 64; }
vis=$(ssh -n delphi-3bda "for f in perf-fix.sh campaign-fix.sh; do bash -n /home/jhan/workspace/intel-AMX/exec/i4934-20261015/\$f 2>/dev/null && echo \$f-ok || echo \$f-syntax; done; grep -c 'run_perf()' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/perf-fix.sh; pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/perf-fix\\.sh' | wc -l; which perf; sudo -n true && echo sudo-ok")
echo "3bda visibility: $(echo "$vis" | tr '\n' ' ')"
echo "$vis" | grep -q syntax && { echo "a script has a syntax error on 3bda (or is not visible yet)"; exit 1; }
[ "$(echo "$vis" | sed -n 3p)" = 1 ] || { echo "perf-fix.sh (run_perf) is not visible on 3bda yet: wait and retry"; exit 1; }
[ "$(echo "$vis" | sed -n 4p)" = 0 ] || { echo "perf-fix.sh already runs on 3bda"; exit 1; }
echo "$vis" | grep -q '^sudo-ok$' || { echo "sudo -n refused on 3bda"; exit 1; }
ssh -n delphi-3bda "END_BY=$END_BY REPS=${REPS:-2} WINDOW=${WINDOW:-10} setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/perf-fix.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
