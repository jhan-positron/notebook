#!/bin/bash
# Verify the merge of origin/main (e5fa372c19) into jhan-kv-typed-tensors (PR #4557) on
# delphi-3bda: lint-notes, the AMX-on tree (all targets), the AMX-off tree (four tests),
# and the tests in both trees. Pinned to our half (socket 1).
EXEC=/home/jhan/workspace/intel-AMX/exec
WT=/var/tmp/jhan/tron-issue4525
T=/var/tmp/jhan/tron-issue4525-tests/merge-20261005
LOG=/var/tmp/jhan/tron-issue4525-merge-20261005.log
DONE=/var/tmp/jhan/tron-issue4525-merge-20261005.done
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
mkdir -p "$T"; rm -f "$DONE"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
source "$EXEC/lib-guard.sh"
echo "=== merge check started $(ts) pid $$"
if ci_lease_busy; then echo "$(ts) CI lease busy: abort"; echo lease >"$DONE"; exit 1; fi
builtin cd "$WT" || exit 1
# files main deleted since the merge base must not linger in the synced tree
if [ -s "$T/deleted.txt" ]; then
  while read -r f; do [ -e "$f" ] && { rm -f "$f"; echo "removed stale $f"; }; done <"$T/deleted.txt"
fi
echo "TRON_CHUNK_SIZE guards left in PR files: $(grep -rn 'TRON_CHUNK_SIZE' h/tron/models/kv_cache.hpp h/tron/models/model.hpp h/tron/tensor/v_vnni.hpp t/t_llama_unit.cpp | wc -l)"
$PIN $NIX "make lint-notes >$T/lint-notes.log 2>&1; echo LINT-NOTES EXIT \$?"
run_tests() {  # $1 = build dir, $2 = prefix
  local g=$1 p=$2 t
  for t in $TESTS; do
    $PIN "$g/$t" --skip-benchmarks >"$T/$p.$t.log" 2>&1
    echo "$p $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.$t.log" | tail -1))"
  done
  $PIN "$g/t_llama_unit" "Sliding KV chunks reserve and restore transactionally" --skip-benchmarks >"$T/$p.sliding.log" 2>&1
  echo "$p sliding-chunk case EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.sliding.log" | tail -1))"
  $PIN "$g/t_llama_unit" 'packed V rows keep their bits through set_v\, get_v and expression reads' --skip-benchmarks >"$T/$p.packedbits.log" 2>&1
  echo "$p packed-bits case EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.packedbits.log" | tail -1))"
}
# 1. AMX-on tree, every target
t0=$(date +%s)
$PIN $NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXON EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen build took $(( $(date +%s) - t0 )) s; flags: $(grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS):' gen/CMakeCache.txt | tr '\n' ' ')"
run_tests gen amxon
TRON_AMX_DISABLE=1 $PIN gen/t_amx_numerics --skip-benchmarks >"$T/amxon.t_amx_numerics.disabled.log" 2>&1
echo "amxon t_amx_numerics kill-switch EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/amxon.t_amx_numerics.disabled.log" | tail -1); 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.disabled.log"))"
echo "amxon t_amx_numerics real-AMX run 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.log")"
# 2. AMX-off tree, the four tests
t0=$(date +%s)
$PIN $NIX "cmake --build gen-amxoff -j 48 --target $TESTS -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXOFF EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen-amxoff build took $(( $(date +%s) - t0 )) s; flags: $(grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS):' gen-amxoff/CMakeCache.txt | tr '\n' ' ')"
run_tests gen-amxoff amxoff
echo "=== merge check finished $(ts)"
echo done >"$DONE"
