#!/usr/bin/env bash
# Launch abl-build.sh and abl-run.sh detached on delphi-3bda from claude-box (our-half steps; the run driver uses
# campaign-fix.sh's idle serving takeover). Both wait for their predecessors (probe.done; the two perf drivers' done files
# and abl.done). Usage: COMMIT=<full sha> BUILD_END_BY=<ISO UTC> RUN_END_BY=<ISO UTC> bash launch-abl.sh
set -u
COMMIT=${COMMIT:?}
for v in BUILD_END_BY RUN_END_BY; do date -u -d "${!v:?$v is required (ISO UTC)}" +%s >/dev/null 2>&1 || { echo "$v '${!v}' is not a date"; exit 64; }; done
vis=$(ssh -n delphi-3bda "git -C /home/jhan/workspace/tron cat-file -e $COMMIT^{commit} 2>/dev/null && echo commit-ok || echo commit-missing; for f in abl-build.sh abl-run.sh campaign-fix.sh; do bash -n /home/jhan/workspace/intel-AMX/exec/i4934-20261015/\$f 2>/dev/null && echo \$f-ok || echo \$f-syntax; done; python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/ablations.py 2>/dev/null && echo ablations.py-ok || echo ablations.py-syntax; grep -c 'PERF2_DONE' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/abl-run.sh; pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/abl-(build|run)\\.sh' | wc -l; ls -d /var/tmp/jhan/tron-i4934abl 2>/dev/null | wc -l")
echo "3bda visibility: $(echo "$vis" | tr '\n' ' ')"
echo "$vis" | grep -q '^commit-ok$' || { echo "the commit is not visible on 3bda"; exit 1; }
echo "$vis" | grep -q syntax && { echo "a script has a syntax error on 3bda (or is not visible yet)"; exit 1; }
[ "$(echo "$vis" | sed -n 6p)" -ge 2 ] || { echo "abl-run.sh's PERF2_DONE wait is not visible on 3bda yet: wait and retry"; exit 1; }
[ "$(echo "$vis" | sed -n 7p)" = 0 ] || { echo "an ablation driver already runs on 3bda"; exit 1; }
[ "$(echo "$vis" | sed -n 8p)" = 0 ] || { echo "/var/tmp/jhan/tron-i4934abl already exists on 3bda"; exit 1; }
ssh -n delphi-3bda "COMMIT=$COMMIT END_BY=$BUILD_END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/abl-build.sh >/dev/null 2>&1 </dev/null & echo launched abl-build pid \$!; END_BY=$RUN_END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/abl-run.sh >/dev/null 2>&1 </dev/null & echo launched abl-run pid \$!"
