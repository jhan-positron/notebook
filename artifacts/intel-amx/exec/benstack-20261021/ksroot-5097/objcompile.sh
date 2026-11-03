#!/bin/bash
# usage: objcompile.sh <worktree> <tu .cpp (absolute)> <out .o>
# Copy of /home/jhan/workspace/ai-runs/lcheck/lcheck.sh: compiles to an object (-c -o) with the
# production flags of the only src/tron line in flags.txt (gen src/tron/kernels/amx_attn.cpp),
# which equal the tron_model_compile_config flags of src/tron/CMakeLists.txt minus -flto=thin.
SP=/home/jhan/workspace/ai-runs/lcheck
M=$SP/mirror; R=/var/tmp/jhan/tron-issue4525; T=gen; W=$1; SRC=$2; OUT=$3
FL=$(grep -F "$T src/tron/kernels/amx_attn.cpp " $SP/flags.txt | head -1 | cut -d' ' -f3-)
FL=$(echo "$FL" | sed -E 's/-fcolor-diagnostics//; s/-fmacro-prefix-map=[^ ]*//g; s/-g(dwarf-4)? / /g; s/ -g$//; s/ -gz / /')
echo "FLAGS: $FL" >&2
exec uvx --from ziglang==0.14.0 python -m ziglang clang --driver-mode=g++ --target=x86_64-linux-gnu -x c++ -c -o "$OUT" -nostdinc -nostdinc++ \
  -isystem $M/nix/store/kzq78n13l8w24jn8bx4djj79k5j717f1-gcc-14.3.0/include/c++/14.3.0 \
  -isystem $M/nix/store/kzq78n13l8w24jn8bx4djj79k5j717f1-gcc-14.3.0/include/c++/14.3.0/x86_64-unknown-linux-gnu \
  -isystem $M/nix/store/hmsiklng1qz2iw1njqpha4qd1g93vnsy-clang-wrapper-19.1.7/resource-root/include \
  -isystem $M/nix/store/gi4cz4ir3zlwhf1azqfgxqdnczfrwsr7-glibc-2.40-66-dev/include \
  -isystem $M$R/gen/libfuse3_external-prefix/src/libfuse3_external/include_wrapper \
  -isystem $M$R/gen/libfuse3_external-prefix/src/libfuse3_external-build \
  -I$M$R/$T/_deps/catch2-build/generated-includes -I$M$R/gen/_deps/catch2-src/src -I$M$R/gen/_deps/json-src/include \
  -I$M$R/gen/_deps/perfetto-src -I$M$R/gen/_deps/picosha2-src -I$M$R/gen/_deps/spdlog-src/include \
  -I$M$R/gen/_deps/yaml-cpp-src/include -I$M$R/$T/src/system/h -I$M$R/$T/src/tron/h -I$W/h -I$W/lib/moodycamel \
  $(for d in $(cat $SP/extra_inc.txt 2>/dev/null); do echo -isystem $M$d; done) $FL -ferror-limit=${ERRLIM:-30} "$SRC"
