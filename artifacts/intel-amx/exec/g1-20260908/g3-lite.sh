#!/usr/bin/env bash
# G3-lite: the existing standalone single-K AVX prototype (PR3879-codex/single-k-evidence/
# single_k_probe.cpp, written 2026-09-04 and run only on an AMD Ryzen desktop) compiled with the
# system g++ and run on ONE socket-1 core of delphi-3bda. Gives the first Granite Rapids number
# for gate G3 (AVX fallback reader on VNNI K vs the canonical dotter transcription): one query,
# one L1-hot full 64-token page. Indicative only: not linked to tron, no 4-query K reuse, no
# partial pages, no RAM regime. Half-machine work (one core, nice 19); needs no guard.
# Output: exec/results/g3-lite-20260908/{build.log,run.log,cpu.txt,summary.txt}
set -u
EXEC=~/workspace/intel-AMX/exec
SRC=~/workspace/intel-AMX/PR3879-codex/single-k-evidence/single_k_probe.cpp
OUT=$EXEC/results/g3-lite-20260908
CORE=${G3_CORE:-141}          # a socket-1 core (72-143, 216-287); pick one the campaign's builds do not pin to (they use the whole socket, so run this between builds)
mkdir -p "$OUT"; cd "$OUT" || exit 1
echo "=== g3-lite $(date -u +%FT%TZ) host $(hostname) core $CORE ===" | tee -a summary.txt
grep -m1 'model name' /proc/cpuinfo | tee cpu.txt; g++ --version | head -1 | tee -a cpu.txt
grep -o -E 'avx512_bf16|amx_bf16' /proc/cpuinfo | sort -u | tr '\n' ' ' >>cpu.txt; echo >>cpu.txt
nice -n 19 taskset -c "$CORE" g++ -std=c++20 -O3 -mavx2 -mfma -Wall -Wextra -Wpedantic -o single_k_probe "$SRC" >build.log 2>&1 || { echo "build failed (see build.log)" | tee -a summary.txt; exit 1; }
echo "load before: $(cut -d' ' -f1-3 /proc/loadavg)" | tee -a summary.txt
for rep in 1 2 3; do
  nice -n 19 taskset -c "$CORE" ./single_k_probe >"run$rep.log" 2>&1; rc=$?
  echo "rep $rep rc=$rc" | tee -a summary.txt
  sed -n '/hot-page single-query/,$p' "run$rep.log" | tee -a summary.txt
done
echo "load after: $(cut -d' ' -f1-3 /proc/loadavg)" | tee -a summary.txt
echo "=== done $(date -u +%FT%TZ) ===" | tee -a summary.txt
