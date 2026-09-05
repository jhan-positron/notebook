#!/usr/bin/env bash
# Smoke: start the canon arm on qwen tp4, list models, one completion, stop.
set -u
H=~/workspace/intel-AMX/exec/more-testing-r1
RES=~/workspace/intel-AMX/exec/results/more-testing-r1
mkdir -p $RES/smoke
source $H/rz.sh
exec >$RES/smoke/smoke.log 2>&1
echo "smoke start $(date -u +%FT%TZ)"
if rz_start canon 13100 4 $RES/smoke/rinzler.log ingested-qwen-3-4b-instruct-2507-tp4; then
  curl -s -m 10 http://127.0.0.1:13100/v1/models; echo
  grep -E "HW attention|K mirror|AMX|amx|Stats/config|FUSE|hugepage" $RES/smoke/rinzler.log | head -20
  echo smoke-ok
else
  echo smoke-failed
fi
rz_stop
echo "smoke end $(date -u +%FT%TZ)"
