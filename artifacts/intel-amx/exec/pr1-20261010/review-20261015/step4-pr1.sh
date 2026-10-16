#!/bin/bash
# PR-1 (#4868) checks on claude-box for the 2026-10-15 review-thread edits: the 38-cell syntax matrix on the
# WORKING TREE of the PR-1 worktree (compared with the reference at 82d05e94be), clang-format 19.1.7 on the files
# that differ from main's merge base, git diff --check, the cassert count and the longest added line.
# usage: bash step4-pr1.sh <label>   (outputs: pr1check-out-<label>/, matrix-<label>.log, format-<label>.log)
L=${1:?label}
EX=/home/jhan/workspace/intel-AMX/exec/pr1-20261010
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
W=/home/jhan/workspace/ai-runs/tron-split-pr1
BASE=72308ec90c80318403c4575dd9ce4a3bc9af5033   # merge base with main
REF=$EX/pr1check-out-b/summary.txt               # 38-cell reference at 82d05e94be
cd "$EX/review-20261015" || exit 1
echo "head: $(git -C $W rev-parse HEAD) working tree: $(git -C $W status --porcelain | wc -l) changed files $(date -u +%FT%TZ)"
echo "=== 38-cell matrix (working tree) ==="
W=$W O=$EX/review-20261015/pr1check-out-$L bash $HM/pr1check/run.sh > matrix-$L.log 2>&1; echo "38-cell rc=$?"; tail -1 matrix-$L.log
echo "cells with warnings != 0:"; grep -v 'warnings=0' $EX/review-20261015/pr1check-out-$L/summary.txt
echo "38-cell summary vs the reference at 82d05e94be: $(diff <(sort $EX/review-20261015/pr1check-out-$L/summary.txt) <(sort $REF) > /dev/null && echo identical || echo DIFFERENT)"
echo "=== format checks ==="
cd $W || exit 1
files=$(git diff --name-only $BASE -- '*.hpp' '*.cpp'); echo "C++ files vs base: $(echo $files | wc -w)"
uvx --from clang-format==19.1.7 clang-format --dry-run --Werror $files > $EX/review-20261015/format-$L.log 2>&1; echo "clang-format rc=$? ($(grep -c 'warning:' $EX/review-20261015/format-$L.log) warnings)"
git diff --check HEAD -- ':!lib/**'; echo "diff-check (working tree vs HEAD) rc=$?"
git diff --check $BASE -- ':!lib/**'; echo "diff-check (working tree vs base) rc=$?"
echo "cassert-in-diff $(git diff $BASE | grep -c '^+.*<cassert>')"
echo "longest added C++ line vs HEAD: $(git diff HEAD -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk '{print length($0)-1}' | sort -n | tail -1)"
echo "added C++ lines over 88 columns vs HEAD: $(git diff HEAD -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk 'length($0)-1 > 88' | wc -l)"
echo "diffstat vs HEAD:"; git diff --stat HEAD | tail -15
echo "done $(date -u +%FT%TZ)"
