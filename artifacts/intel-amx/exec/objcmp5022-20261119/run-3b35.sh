#!/usr/bin/env bash
# Object compare of the AMX kernel translation unit (src/tron/kernels/amx_attn.cpp) between two commits.
# Runs ON delphi-3b35 (needs clang++-19; needs no AMX hardware and no FPGA card). Compile only, pinned to our CPUs.
# Usage: run-3b35.sh <results dir> <tag A> <tag B>     (sources already exported to <results dir>/src-<tag>/)
set -u
RES=$1; A=$2; B=$3
PIN="nice -n 10 taskset -c 96-143"
CXX=clang++-19
# Flags: the compile command CMake recorded for kernels/amx_attn.cpp in an earlier RelWithDebInfo build with
# TRON_AMX_DISPATCH=ON (ai-runs/tron-vnnik-typed/gen/compile_commands.json, 2026-10-02), with two changes:
# the include paths point at the exported sources, and three defines that no file at 4c4b7b8864 sets or reads
# are dropped (TRON_AVX512_ENABLED, TRON_K_VNNI, YAML_CPP_STATIC_DEFINE). spdlog v1.17.0 is the version
# cmake/versions.cmake pins at 4c4b7b8864; its headers come from that earlier build tree.
SPDLOG=/home/jhan/workspace/ai-runs/tron-vnnik-typed/gen/_deps/spdlog-src/include
BASE=(-DSPDLOG_COMPILED_LIB -DTRON_AMX_DISPATCH -I h -I "$SPDLOG"
  -O2 -DNDEBUG -std=gnu++23 -fPIC -Wno-deprecated-declarations
  -fno-omit-frame-pointer -ffunction-sections -fdata-sections -Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed
  --start-no-unused-arguments --rtlib=compiler-rt --end-no-unused-arguments
  -msse4.2 -mavx -mbmi2 -mfma -mavx2 -mclflushopt -ftree-vectorize -funroll-loops
  -mavx512f -mavx512dq -mavx512bw -mavx512vl -mavx512vbmi2 -mavx512vpopcntdq -mavx512vp2intersect -mavx512bf16
  -O3 -DTRON_IGNORE_NAN -DTRON_IGNORE_FTZ
  -mamx-tile -mamx-bf16 -mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 -mavx2 -mfma)
DEBUG=(-g -gdwarf-4 -gz)   # as in the recorded command; left out of the bitcode build so line numbers do not show up as differences
TU=src/tron/kernels/amx_attn.cpp
{
  echo "host: $(hostname)   date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "compiler: $($CXX --version | head -1)"
  echo "flags (object build): ${BASE[*]} ${DEBUG[*]}"
  echo "flags (bitcode build): the same without ${DEBUG[*]}, plus -flto=thin"
} >"$RES/build-info.txt"
rc=0
for t in "$A" "$B"; do
  S=$RES/src-$t; O=$RES/out-$t; mkdir -p "$O"
  ( cd "$S" || exit 9
    # 1. native object, no link-time optimization: the code the compiler emits for this file alone
    $PIN $CXX "${BASE[@]}" "${DEBUG[@]}" -c $TU -o "$O/amx_attn.o" 2>"$O/compile.err" || exit 1
    # 2. thin-LTO bitcode (what the real build hands to the linker), as text
    $PIN $CXX "${BASE[@]}" -flto=thin -c $TU -o "$O/amx_attn.bc" 2>"$O/compile-lto.err" || exit 2
  ) || { rc=$?; echo "compile failed for $t (rc=$rc)"; continue; }
  $PIN llvm-objdump-19 -d -r --no-show-raw-insn --no-leading-addr "$O/amx_attn.o" >"$O/amx_attn.dis"
  $PIN llvm-nm-19 -S --defined-only "$O/amx_attn.o" >"$O/amx_attn.nm"
  $PIN llvm-dis-19 "$O/amx_attn.bc" -o "$O/amx_attn.ll"
  echo "$t: object $(stat -c %s "$O/amx_attn.o") bytes, warnings $(grep -c 'warning:' "$O/compile.err"), text symbols $(grep -c ' [TtWw] ' "$O/amx_attn.nm")"
done | tee -a "$RES/build-info.txt"
exit $rc
