#!/usr/bin/env bash
# One-screen status of the sst-ab-20260917 chain (run from claude-box; reads the NFS-shared files).
P=/home/jhan/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect; R=$P/results/sst-ab-20260917; L=$P/logs
echo "now $(date -u +%FT%TZ)"
echo "build marker: $(cat $R/build-sst0917.done 2>/dev/null || echo none) | campaign marker: $(cat $L/sst-ab-20260917.done 2>/dev/null || echo none)"
echo "status: $(cat $L/sst-ab-20260917.status 2>/dev/null || echo none)"
echo "build log tail:"; tail -n 3 $L/sst-ab-20260917-build.log 2>/dev/null | cut -c1-200
echo "campaign log tail:"; tail -n ${1:-8} $L/sst-ab-20260917.log 2>/dev/null | cut -c1-220
echo "runs done: $(ls $R/rt/*.log 2>/dev/null | grep -vc attempt) smokes: $(ls $R/smoke/*.log 2>/dev/null | grep -vc attempt) failed/stopped lines: $(grep -cE '^RUN-(FAILED|STOPPED|GIVEN)' $R/rt-results.txt 2>/dev/null || echo 0)"
