#!/usr/bin/env bash
# Option A verification on delphi-3bda: full t_llama_unit, negative control
# (tests must FAIL on the unpatched kv_cache.hpp), restore, rebuild, re-run.
set -u
cd ~/workspace/tron-amx || exit 1
. ~/workspace/intel-AMX/exec/lib-guard.sh
KV=h/tron/models/kv_cache.hpp
SAVE=/var/tmp/jhan/optA-kv_cache.hpp.patched
mkdir -p /var/tmp/jhan
cp "$KV" "$SAVE"
restore() { cp "$SAVE" "$KV"; echo "=== restored patched $KV ($(git diff --stat -- $KV | tail -1))"; }
trap restore EXIT
CASES='"EAGLE shifts storage without shifting logical KV completion","K mirror stays coherent for both physical slots under the EAGLE view","heterogeneous EAGLE append preserves both views and embeddings"'
build() { nix develop --command bash -c "nice -n10 cmake --build gen --target $* -j64" 2>&1 | grep -v "^warning: \|^\[" | tail -3; }

echo "=== 1. full t_llama_unit (patched) $(date -u +%FT%TZ)"
ci_lease_busy && { echo "CI BUSY"; exit 3; }
nice -n10 ./gen/t_llama_unit --skip-benchmarks 2>&1 | grep -v "\[info\] Catch2 \(starting\|passed\)" | tail -8
echo "full exit=${PIPESTATUS[0]}"
echo "WARN lines: $(nice -n10 ./gen/t_llama_unit $CASES --skip-benchmarks -s 2>&1 | grep -c 'mirror arena absent')"

echo "=== 2. NEGATIVE CONTROL: unpatched kv_cache.hpp $(date -u +%FT%TZ)"
git checkout -- "$KV" && git diff --stat -- "$KV" | tail -1
build t_llama_unit
echo "--- expected: the three cases FAIL"
eval nice -n10 ./gen/t_llama_unit $CASES --skip-benchmarks 2>&1 | grep -E "FAILED|passed|failed|REQUIRE|test cases|with expansion|^  [a-z_]+\[|==" | head -40
echo "negative exit=${PIPESTATUS[0]} (nonzero expected)"

echo "=== 3. restore + rebuild $(date -u +%FT%TZ)"
restore
trap - EXIT
build t_llama_unit t_amx_mirror t_amx_arena_leak
echo "--- expected: all pass"
eval nice -n10 ./gen/t_llama_unit $CASES --skip-benchmarks 2>&1 | tail -3
echo "positive exit=${PIPESTATUS[0]}"
for t in t_amx_mirror t_amx_arena_leak; do
  B=$(find gen -maxdepth 2 -name $t -type f | head -1)
  echo "--- $t ($B)"; nice -n10 "$B" --skip-benchmarks 2>&1 | tail -2; echo "$t exit=${PIPESTATUS[0]}"
done
echo "=== done $(date -u +%FT%TZ)"
