#!/usr/bin/env bash
# gdn-impl-20261121: everything that is measured on the FINAL commits, in one chain. Runs ON delphi-3b35 after
# build-all.sh has built the tags ctr, pa and pab at the final commits. One step at a time, so no step disturbs
# the timing of another one.
#
# Words: tron = the inference program; GDN = GatedDeltaNet, the recurrent layer type of Qwen3.5 4B; AMX = Intel
# tile-matrix instructions; arm = one build with one set of switches (campaign.sh); session 2 = the campaign
# repetitions 11 to 13, which run the final commits (session 1, repetitions 1 and 2, ran the earlier commits).
# Steps:
#   1. unit-tests.sh           all unit-test programs of the three builds. The chain stops when one fails.
#   2. token-check.sh          same prompt, fixed settings: which arms generate the tokens of the base arm
#   3. campaign.sh             session 2: 6 cells x 6 arms x repetitions 11-13
#   4. campaign.sh             control arms base / nost / orig on three cells, repetitions 21-23
#   5. bench/task3.sh, bench/task3_burst.sh   stand-alone timing of the GDN recurrence kernels (final harness)
# Log: exec/logs/gdn-impl-20261121-final-chain.log   Marker: exec/logs/gdn-impl-20261121-final-chain.done
# Never edit this file while a copy of it runs (NFS: bash reads the script incrementally).
set -u
E=/home/jhan/workspace/intel-AMX/exec
D=$E/gdn-impl-20261121
R=$E/results/gdn-impl-20261121
M=$E/logs/gdn-impl-20261121-final-chain.done
rm -f "$M"
exec >>"$E/logs/gdn-impl-20261121-final-chain.log" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
echo "=== final chain started $(ts) pid $$; builds: $(cat "$R/build-all.done" 2>/dev/null) ==="
for tag in ctr pa pab; do echo "build $tag at $(git -C /var/tmp/jhan/b35-gdn-$tag rev-parse --short=10 HEAD)"; done
if [ -z "${SKIP_UNIT:-}" ]; then
  echo "$(ts) step 1: unit tests"
  bash "$D/unit-tests.sh" >/dev/null
  cat "$R/unit-tests.txt"
  if grep -v '^#' "$R/unit-tests.txt" | grep -qE "FAILED|missing"; then echo "unit-tests-failed" >"$M"; echo "$(ts) chain stops: a unit test failed"; exit 1; fi
fi
echo "$(ts) step 2: token check"
bash "$D/token-check.sh"
echo "$(ts) step 3: session 2 of the campaign"
FIRST_REP=11 REPS=13 bash "$D/campaign.sh"
echo "$(ts) session 2: $(cat "$E/logs/gdn-impl-20261121-campaign.done" 2>/dev/null)"
cp "$E/logs/gdn-impl-20261121-campaign.done" "$R/campaign-session2.done" 2>/dev/null
echo "$(ts) step 4: control arms"
ARMS="base nost orig" CELLS="q35-tp4-1u-p1024 q35-tp4-8u-p1024 q35-tp4-1u-p4096" FIRST_REP=21 REPS=23 bash "$D/campaign.sh"
echo "$(ts) controls: $(cat "$E/logs/gdn-impl-20261121-campaign.done" 2>/dev/null)"
cp "$E/logs/gdn-impl-20261121-campaign.done" "$R/campaign-controls.done" 2>/dev/null
echo "$(ts) step 5: stand-alone kernel timing"
bash "$D/bench/task3.sh"; echo "task3 rc=$?"
bash "$D/bench/task3_burst.sh"; echo "task3_burst rc=$?"
echo ok >"$M"
echo "=== final chain finished $(ts) ==="
