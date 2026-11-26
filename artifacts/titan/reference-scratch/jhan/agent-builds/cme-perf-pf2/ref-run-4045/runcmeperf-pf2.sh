#!/bin/bash
# asimov-bench cme-perf CME prefetch from SMS, OCM and SPM (pf2), rows pf (qitem-20261023195042-fdf092d436c75526, decision 63). runcmeperf-isa2.sh pattern with S=dpa/cme-perf-pf2 and --run-cycles 5000000000 (2.5 s bound), --timelimit 18000.
# Runs from the second build dir (farm) asimov-a10181848-cme (qitem-20261020222522). EMU_VDEBUG_PORT=8293: try 1 (#3844) on 8198 hit Error 98, since Cadence DBEngine/xmsim take dynamic ports from 8192 up.
cd /projects/positronem/work/jgeldbach/dpa/asimov-a10181848-cme || exit 2
S=/projects/positronem/work/jgeldbach/dpa/cme-perf-pf2
export TOOLS_DIR=/projects/positronem/tools PALLADIUM_HOST=ga13pd01 HEMI_LINUX_BOOT=1 ASIMOV_OS_DIR=$S/os EMU_VDEBUG_PORT=8293
unset HEMI_EMU_BOARDS PROBE_TIMES_NS
export LM_LICENSE_FILE=5280@192.168.1.226
echo "ENV LM_LICENSE_FILE=$LM_LICENSE_FILE CDS_LIC_FILE=${CDS_LIC_FILE-unset}"
(cd $S && sha256sum -c --quiet SHA256SUMS) || { echo SUMS_BAD; exit 4; }
grep -Fqx 'c_test_profile: gc,wmem' results/build.hemi_rtws_tlm.z3/ELAB_MANIFEST || { echo PROFILE_BAD; exit 6; }
echo "LAUNCH_UTC=$(date -u +%FT%TZ) host=$(hostname) clone=$(git -c safe.directory='*' log -1 --format=%h)+clone-diff release=a10181848 vdebug_port=$EMU_VDEBUG_PORT lm=$LM_LICENSE_FILE"
touch cmeperfpf2-release.marker
emu/common/scripts/run.sh --task emu --test hemi_tlm --rtws --run-only --run-cycles 5000000000 --timelimit 18000
echo "RUNSH_EXIT=$? END_UTC=$(date -u +%FT%TZ)"
./release-check.sh cmeperfpf2-release.marker release-writes-cmeperfpf2.txt
