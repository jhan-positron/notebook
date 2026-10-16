#!/bin/bash
# PR-2 step 4 on claude-box (fork of exec/pr4-20261012/step4.sh for the PR-2 worktree and base): the 22-cell
# syntax matrix, the two controls, the 38-cell variant, clang-format 19.1.7, git diff --check, the cassert count
# and the line widths, on the WORKING TREE of the worktree (the matrix compiles the files as they are).
# References: the step-5 re-run at 0ee8671d35 (probe/out/pr2b 22 cells, exec/pr2-20261011/pr2check-out-b 38 cells).
# usage: bash step4.sh <label>
L=${1:?label}
EX=/home/jhan/workspace/intel-AMX/exec/pr2-20261011
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
W=/home/jhan/workspace/ai-runs/tron-split-pr2
BASE=jhan-vnnik-1-layout
cd "$EX" || exit 1
echo "head: $(git -C $W rev-parse HEAD) dirty-files: $(git -C $W status --porcelain | wc -l) $(date -u +%FT%TZ)"
echo "=== 22-cell matrix ==="
W=$W bash $HM/probe/matrix.sh "pr2-$L" > matrix-$L.log 2>&1; echo "matrix rc=$?"; tail -1 matrix-$L.log
echo "22-cell summary vs the step-5 reference (pr2b): $(diff <(sort $HM/probe/out/pr2-$L/summary.txt) <(sort $HM/probe/out/pr2b/summary.txt) > /dev/null && echo identical || echo DIFFERENT)"
echo "=== control (a): a broken file through lcheck-vnni.sh (expect rc=1, 2 error lines) ==="
printf 'int broken( { return 1; }\n' > $W/t/probe_bad.cpp
ERRLIM=0 bash $HM/probe/lcheck-vnni.sh gen t/probe_bad.cpp $W > control-a-$L.log 2>&1; echo "control-a rc=$? errors=$(grep -c 'error:' control-a-$L.log) bytes=$(wc -c < control-a-$L.log)"
rm -f $W/t/probe_bad.cpp; echo "status lines after the probe file: $(git -C $W status --porcelain | wc -l)"
echo "=== control (b): matrix without uvx on PATH (expect rc=127 in every cell, MATRIX FAILED) ==="
PATH=/usr/bin:/bin W=$W bash $HM/probe/matrix.sh "ctrl-nouvx-$L" > control-b-$L.log 2>&1; echo "control-b rc=$? cells-rc127=$(grep -c ' rc=127 ' control-b-$L.log)"; tail -1 control-b-$L.log
echo "=== 38-cell matrix ==="
W=$W O=$EX/pr2check-out-$L bash $HM/pr1check/run.sh > pr2check-38-$L.log 2>&1; echo "38-cell rc=$?"; tail -1 pr2check-38-$L.log
echo "cells with warnings != 0 (expected none):"; grep -v 'warnings=0' $EX/pr2check-out-$L/summary.txt; cat $EX/pr2check-out-$L/commit.txt
echo "38-cell summary vs the step-5 reference (pr2check-out-b): $(diff <(sort $EX/pr2check-out-$L/summary.txt) <(sort $EX/pr2check-out-b/summary.txt) > /dev/null && echo identical || echo DIFFERENT)"
echo "=== format checks (working tree against $BASE) ==="
cd $W || exit 1
files=$(git diff --name-only $BASE -- '*.hpp' '*.cpp'); echo "C++ files: $(echo $files | wc -w)"
uvx --from clang-format==19.1.7 clang-format --dry-run --Werror $files > $EX/format-$L.log 2>&1; echo "clang-format rc=$?"
git diff --check $BASE -- ':!lib/**'; echo "diff-check rc=$?"
echo "cassert-in-diff $(git diff $BASE | grep -c '^+.*<cassert>')"
echo "longest added C++ line: $(git diff $BASE -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk '{print length($0)-1}' | sort -n | tail -1)"
echo "added C++ lines over 88 columns: $(git diff $BASE -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk 'length($0)-1 > 88' | wc -l)"
echo "done $(date -u +%FT%TZ)"
