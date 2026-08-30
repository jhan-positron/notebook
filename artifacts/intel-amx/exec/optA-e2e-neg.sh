#!/usr/bin/env bash
# Negative end-to-end control: rebuild t_generate_2 with the PRE-FIX
# kv_cache.hpp (parent commit 8e22b0aa5), run the 1100-token EAGLE case with
# all-software attention (validator on the AMX mirror path), then restore
# HEAD's header and rebuild so gen/t_generate_2 matches the tree again.
set -u
cd ~/workspace/tron-amx || exit 1
. ~/workspace/intel-AMX/exec/lib-guard.sh
KV=h/tron/models/kv_cache.hpp
OUT=~/workspace/intel-AMX/exec/logs/optA-e2e2-runs; mkdir -p "$OUT"
restore() { git checkout -- "$KV"; echo "=== restored $KV to HEAD: $(git status --short -- $KV | wc -l) modified"; }
trap restore EXIT
build() { nix develop --command bash -c "nice -n10 cmake --build gen --target t_generate_2 -j64" 2>&1 | grep -v "^warning: \|^\[" | tail -2; }
echo "=== 1. pre-fix header (8e22b0aa5) $(date -u +%FT%TZ)"
git show 8e22b0aa5:"$KV" > "$KV" && git diff --stat -- "$KV" | tail -1
build
campaign_guard_acquire || { echo "guard refused"; exit 3; }
f="$OUT/G-shard-sw-PREFIX.log"
echo "=== G. 1100-token EAGLE, all-software attention, PRE-FIX header $(date -u +%FT%TZ)"
env USE_HW_ATTN=0 nice -n5 ./gen/t_generate_2 "Speculation via EAGLE\, crosses shard boundary" --skip-benchmarks > "$f" 2>&1
echo "exit=$?"
grep -o "Generating [0-9]* response tokens with [0-9]* context took [0-9.]* s at [0-9.]* average tok/s" "$f" | head -3
grep -o "Speculation mean acceptance length = [0-9.]* rate = [0-9.]* over [0-9]* tokens" "$f" | head -3
grep -E "Catch2 (passed|failed)|FAILED|^All tests passed|^test cases:|^assertions:" "$f" | sed 's/^\[[^]]*\] //' | head -6
campaign_guard_release
echo "=== 2. restore HEAD header + rebuild $(date -u +%FT%TZ)"
restore; trap - EXIT
build
echo "=== done $(date -u +%FT%TZ)"
