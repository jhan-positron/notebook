#!/bin/bash
# First delphi-3bda check of draft PR #4587 (branch jhan-kv-alloc-creates-blocks):
# build the AMX-on tree (all targets) and the AMX-off tree (tests), run the unit
# tests in both, compare the machine code of the KV functions with the previous
# build of PR #4557 (content 5051264d80), and run lint-notes. Our half only.
EXEC=/home/jhan/workspace/intel-AMX/exec
SRC=/home/jhan/workspace/ai-runs/tron-issue4525-a2min
WT=/var/tmp/jhan/tron-issue4525
E=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda
T=/var/tmp/jhan/pr4587-test
LOG=$T/run.log
DONE=$T/run.done
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler t_heap_v2"
CHANGED="h/system/memory.hpp h/tron/models/kv_cache.hpp h/tron/tensor/v_vnni.hpp t/t_heap_v2.cpp t/t_llama_unit.cpp"
mkdir -p "$T"; rm -f "$DONE"; exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
source "$EXEC/lib-guard.sh"
echo "=== pr4587 check started $(ts) pid $$ source $(git -C $SRC rev-parse --short HEAD)"
if ci_lease_busy; then echo "$(ts) CI lease busy: abort"; echo lease >"$DONE"; exit 1; fi
builtin cd "$WT" || exit 1
# 0. Baseline machine code from the existing build (PR #4557 content 5051264d80).
echo "baseline kv_cache.hpp md5 $(md5sum h/tron/models/kv_cache.hpp | cut -c1-32) (5051264d80 = 4b4ba3d6af1ef8bef86259c547ef8283)"
objdump -d -C --no-show-raw-insn gen/t_llama_unit >"$T/objdump.before.txt" 2>/dev/null
objdump -d -C gen/t_llama_unit >"$T/objdump.before.raw.txt" 2>/dev/null
# 1. Bring in the #4587 content. rsync -rlc keeps untouched files' mtimes; no --delete.
rsync -rlc --exclude=/.git --exclude=/gen --exclude='/gen-*' --exclude=/ingest/traces \
  --exclude=/ingest/dist-newstyle --exclude=/compile_commands.json "$SRC/" "$WT/"
for f in $CHANGED; do
  a=$(md5sum <"$SRC/$f" | cut -c1-32); b=$(md5sum <"$WT/$f" | cut -c1-32)
  echo "md5 $f src=$a wt=$b $([ "$a" = "$b" ] && echo OK || echo MISMATCH)"
  [ "$a" = "$b" ] || { echo "content mismatch (NFS attribute cache?): abort"; echo mismatch >"$DONE"; exit 1; }
done
run_tests() {  # $1 = build dir, $2 = prefix
  local g=$1 p=$2 t
  for t in $TESTS; do
    [ -x "$g/$t" ] || { echo "$p $t MISSING"; continue; }
    $PIN "$g/$t" --skip-benchmarks >"$T/$p.$t.log" 2>&1
    echo "$p $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.$t.log" | tail -1))"
  done
  $PIN "$g/t_llama_unit" "Sliding KV chunks reserve and restore transactionally" --skip-benchmarks >"$T/$p.sliding.log" 2>&1
  echo "$p sliding-chunk case EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.sliding.log" | tail -1))"
  $PIN "$g/t_llama_unit" 'packed V rows keep their bits through set_v\, get_v and expression reads' --skip-benchmarks >"$T/$p.packedbits.log" 2>&1
  echo "$p packed-bits case EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.packedbits.log" | tail -1))"
}
# 2. AMX-on tree, every target (runtron and rinzler link memperf.cpp's operator new replacements).
t0=$(date +%s)
$PIN $NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -60; echo BUILD-AMXON EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen build took $(( $(date +%s) - t0 )) s"
ls -la --time-style=+%FT%T gen/runtron gen/rinzler gen/t_llama_unit 2>&1
run_tests gen amxon
TRON_AMX_DISABLE=1 $PIN gen/t_amx_numerics --skip-benchmarks >"$T/amxon.t_amx_numerics.disabled.log" 2>&1
echo "amxon t_amx_numerics kill-switch EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/amxon.t_amx_numerics.disabled.log" | tail -1); 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.disabled.log"))"
echo "amxon t_amx_numerics real-AMX run 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.log")"
# 3. Machine code: allocation paths and KV functions, before vs after.
objdump -d -C --no-show-raw-insn gen/t_llama_unit >"$T/objdump.after.txt" 2>/dev/null
objdump -d -C gen/t_llama_unit >"$T/objdump.after.raw.txt" 2>/dev/null
echo "--- allocation paths, before (5051264d80):"; python3 "$E/alloc_kind_summary.py" "$T/objdump.before.txt"
echo "--- allocation paths, after (#4587):"; python3 "$E/alloc_kind_summary.py" "$T/objdump.after.txt"
echo "--- KV function comparison:"; python3 "$E/fn_diff.py" "$T/objdump.before.raw.txt" "$T/objdump.after.raw.txt"
rm -f "$T/objdump.before.raw.txt" "$T/objdump.after.raw.txt"
# 4. AMX-off tree, the tests.
t0=$(date +%s)
$PIN $NIX "cmake --build gen-amxoff -j 48 --target $TESTS -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -60; echo BUILD-AMXOFF EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen-amxoff build took $(( $(date +%s) - t0 )) s"
run_tests gen-amxoff amxoff
# 5. lint-notes.
$PIN $NIX "make lint-notes >$T/lint-notes.log 2>&1; echo LINT-NOTES EXIT \$?"
echo "=== pr4587 check finished $(ts)"
echo done >"$DONE"
