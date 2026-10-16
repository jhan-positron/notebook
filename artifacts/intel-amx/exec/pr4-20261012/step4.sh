#!/bin/bash
# PR4-handoff.md step 4 on claude-box: the 22-cell syntax matrix, the two controls, the 38-cell variant,
# clang-format 19.1.7, git diff --check, the cassert count and the line widths, on the current head of
# the worktree. usage: bash step4.sh <label>   (logs: matrix-<label>.log, control-a-<label>.log, ...)
# Fork of exec/pr3-20261012/step4.sh (worktree, folder, base). Since d0e6f816dd (2026-10-15) no cell warns: the two
# gen-amxoff t_amx_dispatch_dtype warning cells of decision D12 went with the move of the test's named bools into the
# dispatch-only test case (reference summary updated; the old one is out-38/summary-before-d0e6f816dd.txt).
L=${1:?label}
EX=/home/jhan/workspace/intel-AMX/exec/pr4-20261012
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
W=/home/jhan/workspace/ai-runs/tron-split-pr4
BASE=jhan-vnnik-3-shared-save
cd "$EX" || exit 1
echo "head: $(git -C $W rev-parse HEAD) $(date -u +%FT%TZ)"
echo "=== 22-cell matrix ==="
W=$W bash $HM/probe/matrix.sh "pr4-$L" > matrix-$L.log 2>&1; echo "matrix rc=$?"; tail -1 matrix-$L.log
echo "22-cell summary vs the probe's: $(diff <(sort $HM/probe/out/pr4-$L/summary.txt) <(sort $HM/probe-pr4/out-22/summary.txt) > /dev/null && echo identical || echo DIFFERENT)"
echo "=== control (a): a broken file through lcheck-vnni.sh (expect rc=1, 2 error lines) ==="
printf 'int broken( { return 1; }\n' > $W/t/probe_bad.cpp
ERRLIM=0 bash $HM/probe/lcheck-vnni.sh gen t/probe_bad.cpp $W > control-a-$L.log 2>&1; echo "control-a rc=$? errors=$(grep -c 'error:' control-a-$L.log) bytes=$(wc -c < control-a-$L.log)"
rm -f $W/t/probe_bad.cpp; echo "status lines after the probe file: $(git -C $W status --porcelain | wc -l)"
echo "=== control (b): matrix without uvx on PATH (expect rc=127 in every cell, MATRIX FAILED) ==="
PATH=/usr/bin:/bin W=$W bash $HM/probe/matrix.sh "ctrl-nouvx-$L" > control-b-$L.log 2>&1; echo "control-b rc=$? cells-rc127=$(grep -c ' rc=127 ' control-b-$L.log)"; tail -1 control-b-$L.log
echo "=== 38-cell matrix ==="
W=$W O=$EX/pr4check-out-$L bash $HM/pr1check/run.sh > pr4check-38-$L.log 2>&1; echo "38-cell rc=$?"; tail -1 pr4check-38-$L.log
echo "cells with warnings != 0 (expected none since d0e6f816dd; before it 2: gen-amxoff t_amx_dispatch_dtype, decision D12):"; grep -v 'warnings=0' $EX/pr4check-out-$L/summary.txt; cat $EX/pr4check-out-$L/commit.txt
for cell in gen-amxoff-vnnioff-t_amx_dispatch_dtype gen-amxoff-vnnion-t_amx_dispatch_dtype; do
  f=$(ls $EX/pr4check-out-$L/ | grep "$cell" | grep -v summary | head -1); echo "$cell: $(grep -c 'warning:' $EX/pr4check-out-$L/$f 2>/dev/null) warning lines: $(grep -o "warning: unused variable '[A-Z_]*' \[-Wunused-const-variable\]" $EX/pr4check-out-$L/$f 2>/dev/null | tr '\n' ' ')"
done
echo "38-cell summary vs the probe's: $(diff <(sort $EX/pr4check-out-$L/summary.txt) <(sort $HM/probe-pr4/out-38/summary.txt) > /dev/null && echo identical || echo DIFFERENT)"
echo "=== format checks (against $BASE) ==="
cd $W || exit 1
files=$(git diff --name-only $BASE HEAD -- '*.hpp' '*.cpp'); echo "C++ files: $(echo $files | wc -w)"
uvx --from clang-format==19.1.7 clang-format --dry-run --Werror $files > $EX/format-$L.log 2>&1; echo "clang-format rc=$?"
git diff --check $BASE HEAD -- ':!lib/**'; echo "diff-check rc=$?"
echo "cassert-in-diff $(git diff $BASE HEAD | grep -c '^+.*<cassert>')"
echo "longest added C++ line: $(git diff $BASE HEAD -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk '{print length($0)-1}' | sort -n | tail -1)"
echo "added C++ lines over 80 columns: $(git diff $BASE HEAD -- '*.hpp' '*.cpp' | grep '^+' | grep -v '^+++' | awk 'length($0)-1 > 80' | wc -l)"
python3 -c 'import json; p=json.load(open("CMakePresets.json")); d=[c for c in p["configurePresets"] if c["name"]=="deb"][0]["cacheVariables"]; assert d["TRON_AMX_DISPATCH"]=="ON" and d["TRON_K_VNNI"]=="ON", d; print("deb preset:", d["TRON_AMX_DISPATCH"], d["TRON_K_VNNI"]); print("presets with TRON_K_VNNI:", [c["name"] for c in p["configurePresets"] if "TRON_K_VNNI" in c.get("cacheVariables", {})])'
echo "done $(date -u +%FT%TZ)"
