#!/bin/bash
# Spokane repeat of GA13 request 4045: asimov-bench cme-perf, row set pf.
# Prepared 2026-11-24 by Claude Code for Jibin. Launch only with Jibin's yes.
#
# Run this ON palladium-94a4 (the host that drives the emulator). Then run.sh
# makes no ssh hop, and no setting depends on the list of forwarded variables.
# (At commit 5645dbfd1 that list does hold ASIMOV_OS_DIR, HEMI_LINUX_BOOT and
# EMU_VDEBUG_PORT, so a launch from alpha would also keep them.)
#
# The run takes all 4 boards of the Spokane emulator.
# Cap: 3,600,000,000 cycles = 1.8 s of chip time. CME,done is expected near
# 1.5 s (SCP boot 0.45 s + Linux uptime 1.03 s in request 4045).

T=/scratch/jhan/agent-builds/asimov-a10181848-pf   # run tree at RTL commit 5645dbfd1
S=/scratch/jhan/agent-builds/cme-perf-pf2          # copy of Jacob's boot files

[[ $(hostname -s) == palladium-94a4 ]] || { echo WRONG_HOST; exit 3; }
cd "$T" || exit 2
unset MODULESHOME HEMI_EMU_BOARDS PROBE_TIMES_NS
export HEMI_LINUX_BOOT=1 ASIMOV_OS_DIR=$S/os EMU_VDEBUG_PORT=8293

(cd "$S" && sha256sum -c --quiet SHA256SUMS.os) || { echo SUMS_BAD; exit 4; }
[[ $(git log -1 --format=%h) == 5645dbfd1 ]] || { echo COMMIT_BAD; exit 5; }
grep -Fqx 'c_test_profile: gc,wmem' results/build.hemi_rtws_tlm.z3/ELAB_MANIFEST \
  || { echo PROFILE_BAD; exit 6; }

echo "LAUNCH_UTC=$(date -u +%FT%TZ) host=$(hostname -s) tree=$(git log -1 --format=%h) release=a10181848 os=$ASIMOV_OS_DIR vdebug_port=$EMU_VDEBUG_PORT"
emu/common/scripts/run.sh --task emu --test hemi_tlm --rtws --run-only \
  --run-cycles 3600000000 --timelimit 10800
echo "RUNSH_EXIT=$? END_UTC=$(date -u +%FT%TZ)"
