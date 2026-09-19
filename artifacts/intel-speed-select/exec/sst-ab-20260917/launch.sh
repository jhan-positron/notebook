#!/usr/bin/env bash
# Launch the sst-ab-20260917 build and campaign detached ON delphi-3bda (run this from claude-box).
# build.sh (wedperf's, reused) waits for the CI lease and the campaign flock, builds runtron from the
# deployed deb's commit into /var/tmp/jhan/tron-sst0917 and writes results/.../build-sst0917.done.
# campaign.sh waits for that marker, then runs the arms. Both log under $PROJ/logs.
set -u
PROJ=/home/jhan/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect
C=$PROJ/exec/sst-ab-20260917
RES=$PROJ/results/sst-ab-20260917
COMMIT=31b80a18fa12f70382e36611b41891ac76c0bb74   # tron deb 2026.09.17-31b80a18 installed on delphi-3bda (dpkg -l tron, 2026-09-17)
ssh -o BatchMode=yes delphi-3bda "
  set -u
  mkdir -p $RES $PROJ/logs
  if pgrep -u jhan -f '^bash $C/campaign\.sh$' >/dev/null; then echo 'campaign.sh already running'; else
    RES=$RES LOG=$PROJ/logs/sst-ab-20260917-build.log EXPECT_K_VNNI=OFF EXPECT_AMX_DISPATCH=OFF \
      setsid nohup bash /home/jhan/workspace/intel-AMX/exec/wedperf-20260916/build.sh $COMMIT /var/tmp/jhan/tron-sst0917 sst0917 -DBUILD_PRODUCTION_MODELS=ON </dev/null >/dev/null 2>&1 &
    sleep 1
    setsid nohup bash $C/campaign.sh </dev/null >/dev/null 2>&1 &
    sleep 2
    echo launched; pgrep -u jhan -af '^bash [^ ]*(sst-ab-20260917/campaign\.sh|wedperf-20260916/build\.sh)' | cut -c1-200
  fi
"
