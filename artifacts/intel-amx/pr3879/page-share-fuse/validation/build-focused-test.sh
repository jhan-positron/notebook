#!/usr/bin/env bash
set -euxo pipefail
task_src=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR0-FUSE/tron
task_deps=/home/jhan/workspace/tron/gen
task_validation=/tmp/page-share-validation
task_fuse="$task_deps/libfuse3_external-prefix/src"
cd "$task_src"

# This focused binary uses the checked-out test and implementation, actual
# supporting sources, and the pinned dependency sources cached by Tron.
g++ -std=c++2b -O0 -pthread -ffunction-sections -fdata-sections \
  -c "$task_deps/_deps/catch2-src/extras/catch_amalgamated.cpp" \
  -o "$task_validation/catch2.o"
bin/make-version.sh "$task_validation/version.cpp"
g++ -std=c++2b -O0 -pthread -ffunction-sections -fdata-sections \
  -DTRON_PAGE_SHARE_COUNTERS \
  -Ih \
  -I"$task_deps/_deps/catch2-src/src" \
  -I"$task_deps/_deps/catch2-build/generated-includes" \
  -I"$task_deps/_deps/spdlog-src/include" \
  -I"$task_deps/_deps/json-src/include" \
  -I"$task_deps/src/system/h" \
  -I"$task_fuse/libfuse3_external/include_wrapper" \
  -I"$task_fuse/libfuse3_external-build" \
  t/t_page_share_counters.cpp src/system/fuse_sysfs.cpp src/common/assert.cpp \
  "$task_validation/version.cpp" "$task_validation/catch2.o" \
  -L"$task_fuse/libfuse3_external-build/lib" -lfuse3 \
  -Wl,--gc-sections -Wl,-rpath,"$task_fuse/libfuse3_external-build/lib" \
  -o "$task_validation/t_page_share_counters"
