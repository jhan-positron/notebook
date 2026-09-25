#!/bin/bash
# Verify the boolean-literal naming change of jhan-kv-typed-tensors on delphi-3bda:
# lint-notes, the 16-lane AMX-on tree (all targets), the AMX-off tree (four tests),
# the tests in both trees, and the symbol sets of two test binaries before/after.
EXEC=/home/jhan/workspace/intel-AMX/exec
WT=/var/tmp/jhan/tron-issue4525
T=/var/tmp/jhan/tron-issue4525-tests/boolnames
LOG=/var/tmp/jhan/tron-issue4525-boolnames.log
DONE=/var/tmp/jhan/tron-issue4525-boolnames.done
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
mkdir -p "$T"; rm -f "$DONE"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
source "$EXEC/lib-guard.sh"
echo "=== boolnames check started $(ts) pid $$"
if ci_lease_busy; then echo "$(ts) CI lease busy: abort"; echo lease >"$DONE"; exit 1; fi
builtin cd "$WT" || exit 1
echo "named-flag uses in tree: $(grep -rn --include='*.hpp' --include='*.cpp' -w -E 'VIEW_ALIGNED_TRUE|VIEW_DMA_FALSE|RECLAIMABLE_FALSE|RECLAIMABLE_TRUE' h t src | wc -l)"
for b in t_llama_unit t_amx_numerics; do
  nm --defined-only "gen/$b" | awk '{print $3}' | sort >"$T/$b.syms.before"
done
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
$PIN $NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -60; echo BUILD-AMXON EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen build took $(( $(date +%s) - t0 )) s; flags: $(grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS):' gen/CMakeCache.txt | tr '\n' ' ')"
for b in t_llama_unit t_amx_numerics; do
  nm --defined-only "gen/$b" | awk '{print $3}' | sort >"$T/$b.syms.after"
  echo "$b defined symbols before/after: $(wc -l <"$T/$b.syms.before")/$(wc -l <"$T/$b.syms.after"), differing lines: $(diff "$T/$b.syms.before" "$T/$b.syms.after" | grep -c '^[<>]')"
done
run_tests gen amxon
TRON_AMX_DISABLE=1 $PIN gen/t_amx_numerics --skip-benchmarks >"$T/amxon.t_amx_numerics.disabled.log" 2>&1
echo "amxon t_amx_numerics kill-switch EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/amxon.t_amx_numerics.disabled.log" | tail -1); 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.disabled.log"))"
echo "amxon t_amx_numerics real-AMX run 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.log")"
# 2. AMX-off tree, the four tests
t0=$(date +%s)
$PIN $NIX "cmake --build gen-amxoff -j 48 --target $TESTS -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -60; echo BUILD-AMXOFF EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen-amxoff build took $(( $(date +%s) - t0 )) s; flags: $(grep -E '^(CMAKE_BUILD_TYPE|AVX512|TRON_AMX_DISPATCH|BUILD_INGEST_MODELS):' gen-amxoff/CMakeCache.txt | tr '\n' ' ')"
run_tests gen-amxoff amxoff
echo "=== boolnames check finished $(ts)"
echo done >"$DONE"
