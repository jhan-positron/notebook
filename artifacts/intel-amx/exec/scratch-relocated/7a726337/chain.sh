#!/bin/bash
cd /var/tmp/jhan/tron-issue4525 || exit 1
T=/var/tmp/jhan/tron-issue4525-tests
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
CFG="-DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF"
PROGRESS='^\[[0-9]+/[0-9]+\] '
date -u
until grep -q "LLAMA DONE" $T/llama.run.log 2>/dev/null; do sleep 20; done
echo "=== STEP build4: every target, 16-lane AMX on ($(date -u))"
$NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo BUILD4 EXIT \${PIPESTATUS[0]}"
echo "=== STEP lint-notes ($(date -u))"
$NIX "make lint-notes 2>&1 | tail -15; echo LINTNOTES EXIT \${PIPESTATUS[0]}"
echo "=== STEP C2: 16-lane AMX off ($(date -u))"
$NIX "cmake --preset native -B gen-amxoff -DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo $CFG 2>&1 | grep -E 'AVX512|Disabling|Configuring done|Error'; grep -E '^(AVX512|TRON_AMX_DISPATCH|CMAKE_BUILD_TYPE):' gen-amxoff/CMakeCache.txt; cmake --build gen-amxoff -j 48 --target t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo BUILDC2 EXIT \${PIPESTATUS[0]}"
for t in t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler; do
  taskset -c 72-143 env USE_HW_ATTN=1 gen-amxoff/$t > $T/c2.$t.log 2>&1; echo "C2 $t EXIT $? ($(grep -E 'All tests passed|test cases' $T/c2.$t.log | tail -1))"
done
echo "=== STEP C4: Debug 16-lane AMX off ($(date -u))"
$NIX "cmake --preset native -B gen-debug -DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=Debug $CFG 2>&1 | grep -E 'AVX512|Disabling|Configuring done|Error'; grep -E '^(CMAKE_BUILD_TYPE|TRON_AMX_DISPATCH):' gen-debug/CMakeCache.txt; cmake --build gen-debug -j 48 --target t_llama_unit -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo BUILDC4 EXIT \${PIPESTATUS[0]}"
echo "TRON_IGNORE_NAN occurrences in the Debug t_llama_unit compile command: $(grep t_llama_unit.cpp gen-debug/compile_commands.json | grep -c TRON_IGNORE_NAN)"
taskset -c 72-143 gen-debug/t_llama_unit "[kv_data]" --skip-benchmarks > $T/c4.t_llama_unit.kv_data.log 2>&1; echo "C4 t_llama_unit [kv_data] EXIT $? ($(grep -E 'All tests passed|test cases' $T/c4.t_llama_unit.kv_data.log | tail -1))"
echo "=== STEP C3: 8-lane AMX off ($(date -u))"
$NIX "cmake --preset native -B gen-avx2 -DAVX512=OFF -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo $CFG 2>&1 | grep -E 'AVX512|Disabling|Configuring done|Error'; grep -E '^(AVX512|TRON_AMX_DISPATCH):' gen-avx2/CMakeCache.txt; cmake --build gen-avx2 -j 48 --target tron t_amx_dispatch_dtype -- -k 0 2>&1 | grep -vE '$PROGRESS'; echo BUILDC3 EXIT \${PIPESTATUS[0]}"
taskset -c 72-143 gen-avx2/t_amx_dispatch_dtype > $T/c3.t_amx_dispatch_dtype.log 2>&1; echo "C3 t_amx_dispatch_dtype EXIT $? ($(grep -E 'All tests passed|test cases' $T/c3.t_amx_dispatch_dtype.log | tail -1))"
echo "CHAIN DONE ($(date -u))"
