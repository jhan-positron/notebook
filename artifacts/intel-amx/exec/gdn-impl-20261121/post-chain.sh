#!/usr/bin/env bash
# gdn-impl-20261121: the steps after final-chain.sh. Runs ON delphi-3b35. It waits for the marker of the chain.
#
# Words: tron = the inference program; arm = one build with one set of switches; measured commits = the commits
# that sessions 2 ran (tags ctr, pa, pab at d5093e07c2, 8351e4ad52, aacdd287c0); head commits = the same three
# commits with the comment and test fixes of the second review folded in. The two sets differ in comments, in
# tests and in README.stats.md only.
# Steps:
#   1. token-check.sh with a second run of four arms and with the stand-alone Part B build (tag partb), prompt 1,024.
#      Question: is a token difference repeatable, and does it come from the AMX attention kernels alone?
#   2. build-all.sh at the head commits (CTR, PA, PAB), then unit-tests.sh.
# Log: exec/logs/gdn-impl-20261121-post-chain.log   Marker: exec/logs/gdn-impl-20261121-post-chain.done
set -u
E=/home/jhan/workspace/intel-AMX/exec
D=$E/gdn-impl-20261121
R=$E/results/gdn-impl-20261121
M=$E/logs/gdn-impl-20261121-post-chain.done
rm -f "$M"
exec >>"$E/logs/gdn-impl-20261121-post-chain.log" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
echo "=== post chain started $(ts) pid $$; waits for the final chain ==="
until [ -e "$E/logs/gdn-impl-20261121-final-chain.done" ]; do sleep 15; done
echo "$(ts) final chain: $(cat "$E/logs/gdn-impl-20261121-final-chain.done")"
echo "$(ts) step 1: token check, second runs and the stand-alone Part B build"
PROMPTS=1024 ARMS="orig base p0 a0 a b ab base2 a2 b2 ab2 bonly" bash "$D/token-check.sh"
PROMPTS=4096 ARMS="orig base p0 a0 a b ab bonly" bash "$D/token-check.sh" | tail -9
cp "$R/unit-tests.txt" "$R/unit-tests-measured.txt"
echo "$(ts) step 2: builds at the head commits"
CTR=${CTR:?} PA=${PA:?} PAB=${PAB:?} bash "$D/build-all.sh"
echo "$(ts) builds: $(cat "$R/build-all.done" 2>/dev/null)"
if grep -q "ctr=ok pa=ok pab=ok" "$R/build-all.done" 2>/dev/null; then
  bash "$D/unit-tests.sh" >/dev/null
  cat "$R/unit-tests.txt"
  echo ok >"$M"
else
  echo "build-failed" >"$M"
fi
echo "=== post chain finished $(ts): $(cat "$M") ==="
