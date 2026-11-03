#!/bin/bash
# usage: lto-build.sh <base|head> <worktree>
# Compiles the tp2-only model TU with the production flags PLUS -flto=thin (bitcode), then runs the
# ThinLTO backend through lld (--lto-O3) into a shared object with unresolved symbols ignored.
K=/tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot
A=$1; W=$2; O=$K/h7/lto; Z="uvx --from ziglang==0.14.0 python -m ziglang"
SP=/home/jhan/workspace/ai-runs/lcheck; M=$SP/mirror; R=/var/tmp/jhan/tron-issue4525; T=gen
FL=$(grep -F "$T src/tron/kernels/amx_attn.cpp " $SP/flags.txt | head -1 | cut -d' ' -f3-)
FL=$(echo "$FL" | sed -E 's/-fcolor-diagnostics//; s/-fmacro-prefix-map=[^ ]*//g; s/-g(dwarf-4)? / /g; s/ -g$//; s/ -gz / /')
echo "$(date -u +%FT%TZ) compile $A" > $O/$A.log
$Z clang --driver-mode=g++ --target=x86_64-linux-gnu -x c++ -c -o $O/$A.tp2only.bc -nostdinc -nostdinc++ \
  -isystem $M/nix/store/kzq78n13l8w24jn8bx4djj79k5j717f1-gcc-14.3.0/include/c++/14.3.0 \
  -isystem $M/nix/store/kzq78n13l8w24jn8bx4djj79k5j717f1-gcc-14.3.0/include/c++/14.3.0/x86_64-unknown-linux-gnu \
  -isystem $M/nix/store/hmsiklng1qz2iw1njqpha4qd1g93vnsy-clang-wrapper-19.1.7/resource-root/include \
  -isystem $M/nix/store/gi4cz4ir3zlwhf1azqfgxqdnczfrwsr7-glibc-2.40-66-dev/include \
  -isystem $M$R/gen/libfuse3_external-prefix/src/libfuse3_external/include_wrapper \
  -isystem $M$R/gen/libfuse3_external-prefix/src/libfuse3_external-build \
  -I$M$R/$T/_deps/catch2-build/generated-includes -I$M$R/gen/_deps/catch2-src/src -I$M$R/gen/_deps/json-src/include \
  -I$M$R/gen/_deps/perfetto-src -I$M$R/gen/_deps/picosha2-src -I$M$R/gen/_deps/spdlog-src/include \
  -I$M$R/gen/_deps/yaml-cpp-src/include -I$M$R/$T/src/system/h -I$M$R/$T/src/tron/h -I$W/h -I$W/lib/moodycamel \
  $(for d in $(cat $SP/extra_inc.txt 2>/dev/null); do echo -isystem $M$d; done) $FL -flto=thin -ferror-limit=30 \
  $K/tu/model_llama_3p1_8b_tp2only.cpp >> $O/$A.log 2>&1; echo "compile rc=$?" >> $O/$A.log
echo "$(date -u +%FT%TZ) link $A" >> $O/$A.log
$Z ld.lld -shared --lto-O3 --unresolved-symbols=ignore-all -o $O/$A.tp2only.lto.so $O/$A.tp2only.bc >> $O/$A.log 2>&1; echo "link rc=$?" >> $O/$A.log
objdump -d --no-show-raw-insn $O/$A.tp2only.lto.so > $O/$A.lto.dis 2>>$O/$A.log
echo "$(date -u +%FT%TZ) done $A" >> $O/$A.log
