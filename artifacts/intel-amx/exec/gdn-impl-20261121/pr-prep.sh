#!/usr/bin/env bash
# gdn-impl-20261121: the checks of the branch head before the draft PR is opened. Runs ON delphi-3b35.
# Words: tron = the inference program; AMX = Intel tile-matrix instructions; AMX dispatch = the build option
# TRON_AMX_DISPATCH that compiles the AMX kernels; build tags ctr / pa / pab = the three commits of the branch.
# Steps:
#   1. build-all.sh at the three commits (CTR, PA, PAB), then unit-tests.sh               -> unit-tests.txt
#   2. a build of the head with the build type Debug and without AMX dispatch (tag noamx), then its unit tests
#      (the configuration of the asan, tsan and coverage presets; it must link without the AMX kernel files)
#                                                                                          -> unit-tests-noamx.txt
#   3. make lint-notes at the head (the Note checker of the CI lint job)                   -> lint-notes.txt
# Log: exec/logs/gdn-impl-20261121-pr-prep.log   Marker: exec/logs/gdn-impl-20261121-pr-prep.done
set -u
E=/home/jhan/workspace/intel-AMX/exec
D=$E/gdn-impl-20261121
R=$E/results/gdn-impl-20261121
M=$E/logs/gdn-impl-20261121-pr-prep.done
rm -f "$M"
exec >>"$E/logs/gdn-impl-20261121-pr-prep.log" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
echo "=== pr prep started $(ts) CTR=${CTR:?} PA=${PA:?} PAB=${PAB:?} ==="
bash "$D/build-all.sh"
echo "$(ts) builds: $(cat "$R/build-all.done" 2>/dev/null)"
grep -q "ctr=ok pa=ok pab=ok" "$R/build-all.done" 2>/dev/null || { echo build-failed >"$M"; exit 1; }
bash "$D/unit-tests.sh" >/dev/null
cat "$R/unit-tests.txt"
TAG=noamx SHA=$PAB CONF_FLAGS='-DCMAKE_BUILD_TYPE=Debug' TARGETS='t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype' CPUS=96-143 JOBS=44 bash "$D/build.sh"
echo "$(ts) noamx build: $(cat "$R/build-noamx.done" 2>/dev/null)"
if [ "$(cat "$R/build-noamx.done" 2>/dev/null)" = ok ]; then
  TAGS=noamx TESTS="t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype" OUT=$R/unit-tests-noamx.txt bash "$D/unit-tests.sh" >/dev/null
  grep "^noamx" "$R/unit-tests-noamx.txt"
  echo ok >"$M"
else
  echo noamx-build-failed >"$M"
fi
# 3. the Note checker of the CI lint job (it needs GHC and Cabal, which this server has), at the head tree
( cd /var/tmp/jhan/b35-gdn-pab && PATH=$HOME/.ghcup/bin:$HOME/.cabal/bin:$PATH timeout 900 make lint-notes ) >"$R/lint-notes.txt" 2>&1
echo "lint-notes rc=$?" | tee -a "$R/lint-notes.txt"
tail -5 "$R/lint-notes.txt"
echo "=== pr prep finished $(ts): $(cat "$M") ==="
