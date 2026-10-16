#!/bin/bash
# PR3-handoff.md step 4 on claude-box: the 22-cell syntax matrix, the two controls, the 38-cell variant,
# clang-format 19.1.7, git diff --check, the cassert count and the line widths, on the current head of
# the worktree. usage: bash step4.sh <label>   (logs: matrix-<label>.log, control-a-<label>.log, ...)
L=${1:?label}
EX=/home/jhan/workspace/intel-AMX/exec/pr3-20261012
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
W=/home/jhan/workspace/ai-runs/tron-split-pr3
cd "$EX" || exit 1
echo "head: $(git -C $W rev-parse HEAD) $(date -u +%FT%TZ)"
echo "=== 22-cell matrix ==="
W=$W bash $HM/probe/matrix.sh "pr3-$L" > matrix-$L.log 2>&1; echo "matrix rc=$?"; tail -1 matrix-$L.log
echo "=== control (a): a broken file through lcheck-vnni.sh (expect rc=1, 2 error lines) ==="
printf 'int broken( { return 1; }\n' > $W/t/probe_bad.cpp
ERRLIM=0 bash $HM/probe/lcheck-vnni.sh gen t/probe_bad.cpp $W > control-a-$L.log 2>&1; echo "control-a rc=$? errors=$(grep -c 'error:' control-a-$L.log) bytes=$(wc -c < control-a-$L.log)"
rm -f $W/t/probe_bad.cpp; echo "status lines after the probe file: $(git -C $W status --porcelain | wc -l)"
echo "=== control (b): matrix without uvx on PATH (expect rc=127 in every cell, MATRIX FAILED) ==="
PATH=/usr/bin:/bin W=$W bash $HM/probe/matrix.sh "ctrl-nouvx-$L" > control-b-$L.log 2>&1; echo "control-b rc=$? cells-rc127=$(grep -c ' rc=127 ' control-b-$L.log)"; tail -1 control-b-$L.log
echo "=== 38-cell matrix ==="
W=$W O=$EX/pr3check-out-$L bash $HM/pr1check/run.sh > pr3check-38-$L.log 2>&1; echo "38-cell rc=$?"; tail -1 pr3check-38-$L.log
echo "cells with warnings != 0: $(grep -vc 'warnings=0' $EX/pr3check-out-$L/summary.txt)"; cat $EX/pr3check-out-$L/commit.txt
echo "=== format checks (against jhan-vnnik-2-amx) ==="
cd $W || exit 1
files=$(git diff --name-only jhan-vnnik-2-amx HEAD -- '*.hpp' '*.cpp'); echo "C++ files: $(echo $files | wc -w)"
uvx --from clang-format==19.1.7 clang-format --dry-run --Werror $files > $EX/format-$L.log 2>&1; echo "clang-format rc=$?"
git diff --check jhan-vnnik-2-amx HEAD -- ':!lib/**'; echo "diff-check rc=$?"
echo "cassert-in-diff $(git diff jhan-vnnik-2-amx HEAD | grep -c '^+.*<cassert>')"
echo "longest added C++ line: $(git diff jhan-vnnik-2-amx HEAD -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk '{print length($0)-1}' | sort -n | tail -1)"
echo "added Haskell lines over 88: $(git diff jhan-vnnik-2-amx HEAD -- '*.hs' | grep '^+' | grep -v '^+++' | awk 'length($0)-1 > 88' | wc -l)"
echo "done $(date -u +%FT%TZ)"
