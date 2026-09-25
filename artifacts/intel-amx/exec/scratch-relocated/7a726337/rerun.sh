#!/bin/bash
cd /var/tmp/jhan/tron-issue4525 || exit 1
T=/var/tmp/jhan/tron-issue4525-tests
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PROGRESS='^\[[0-9]+/[0-9]+\] '
date -u
$NIX "clang-format-19 --dry-run -Werror t/t_llama_unit.cpp && echo FORMAT CLEAN; cmake --build gen -j 48 --target t_llama_unit -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo REBUILD-REL EXIT \${PIPESTATUS[0]}; cmake --build gen-debug -j 48 --target t_llama_unit -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo REBUILD-DBG EXIT \${PIPESTATUS[0]}"
taskset -c 72-143 gen/t_llama_unit > $T/t_llama_unit.rerun.log 2>&1; echo "REL t_llama_unit EXIT $? ($(grep -E 'All tests passed|test cases' $T/t_llama_unit.rerun.log | tail -1))"
taskset -c 72-143 gen-debug/t_llama_unit "[kv_data]" --skip-benchmarks > $T/c4.t_llama_unit.kv_data.rerun.log 2>&1; echo "DBG t_llama_unit [kv_data] EXIT $? ($(grep -E 'All tests passed|test cases' $T/c4.t_llama_unit.kv_data.rerun.log | tail -1))"
echo "RERUN DONE ($(date -u))"
