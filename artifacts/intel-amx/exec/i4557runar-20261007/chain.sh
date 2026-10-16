#!/usr/bin/env bash
# i4557runar-20261007 chain (runs ON delphi-3bda, setsid nohup): verify commit 79478c254a of PR #4557
# (the third-review edits: pair_base bounds assert, row alignment asserts, no Cols % 32 clause, no writable at()).
#   1. claim the machine (people-check; jhan said the whole machine is ours, 2026-10-07 17:0x UTC);
#   2. rsync the NFS worktree into /var/tmp/jhan/tron-issue4525, clang-format check, lint-notes, gen (all targets) and
#      gen-amxoff (4 tests) builds, unit tests in both trees;
#   3. build runtron.runar at 79478c254a in tron-i4525rt2 (same configure as runtron.squash) and compare its KV and
#      attention functions with runtron.squash (c5d44bd86f) after address normalization (fn_diff2.py);
#   4. serving down; Step D token identity cpu p1024 arms base (main dd6e85226b) head (79478c254a) headoff;
#   5. bench row: bin/slice bench --update t_llama_unit (whole machine, both sockets); keep the resulting JSON;
#   6. serving back up through platformd, claim released, evidence copied.
# Fork of exec/i4557squash-20261006/chain.sh. Never edit while it runs (NFS stale-handle trap).
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4587-20260924
B=$EXEC/i4525-20260922/build2.sh
export NAME=i4557runar-20261007
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
EV=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/runar-3bda
SRCWT=/home/jhan/workspace/ai-runs/tron-issue4525
HEAD_SHA=79478c254a97495d37a5cac29fb6167c726ed1cb
PREV_SHA=c5d44bd86fe97914d2d3c7144b8045ebfad9fba0
UT=/var/tmp/jhan/tron-issue4525
T=/var/tmp/jhan/tron-issue4525-tests/runar-20261007
export RT_BASE=/var/tmp/jhan/tron-main0922/gen/runtron.main1006
export RT_HEAD=/var/tmp/jhan/tron-i4525rt2/gen/runtron.runar
RT_PREV=/var/tmp/jhan/tron-i4525rt2/gen/runtron.squash
export ARM_ENV_baseoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
# same cache values as runtron.squash: AVX512=ON BUILD_INGEST_MODELS=ON RelWithDebInfo TRON_AMX_DISPATCH=ON (CMakeCache read 2026-10-07)
RT_CONFIGURE='--preset native -DAVX512=ON -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo'
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command bash -c"
PIN="taskset -c 72-143,216-287 nice -n 10"
PROGRESS='^\[[0-9]+/[0-9]+\] '
TESTS="t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler"
FNDIFF=/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/pr4587-3bda/fn_diff2.py
mkdir -p "$RES" "$EXEC/logs" "$EV" "$T"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
finish() {
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
  elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
  else t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up; echo "$(ts) serving-up rc=$? in $(( $(date +%s) - t0 )) s"; fi
  echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
  bash "$EXEC/people-check.sh" --release; echo "$(ts) claim release rc=$?"
  cp -r "$RES"/. "$EV/" 2>/dev/null; cp "$T"/*.log "$T"/*.txt "$EV/" 2>/dev/null; cp "$LOG" "$EV/" 2>/dev/null
  step_done end "$1"
  echo "$1" >"$RES/chain.done"
  echo "=== $NAME chain finished $(ts): $1 ==="
}
exec >>"$LOG" 2>&1
echo "=== $NAME chain started $(ts) pid $$ head=$HEAD_SHA prev=$PREV_SHA ==="
# ---- 1. claim ----
if ci_lease_busy 600; then step_done start "CI lease busy: abort"; echo lease >"$RES/chain.done"; exit 1; fi
bash "$EXEC/people-check.sh" --claim "PR 4557 third-review edits: unit tests, objdump, token identity, bench row, ~2 h" || {
  step_done start "people-check refused (rc=$?): abort"; echo busy >"$RES/chain.done"; exit 1; }
step_done start "claimed at $(ts)"
echo "$(ts) machine: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
# ---- 2. rsync + unit tests ----
[ "$(git -C "$SRCWT" rev-parse HEAD)" = "$HEAD_SHA" ] || { step_done sync "NFS worktree is not at $HEAD_SHA: abort"; finish chain-failed-src; exit 1; }
rsync -rlc --exclude .git --exclude 'gen*' --exclude init.txt --exclude compile_commands.json "$SRCWT/" "$UT/" && echo "$(ts) rsync ok" || { step_done sync "rsync failed"; finish chain-failed-rsync; exit 1; }
builtin cd "$UT" || exit 1
git add -A . >/dev/null 2>&1; git rm -r -q --cached gen-amxoff gen-avx2 gen-debug >/dev/null 2>&1   # nix needs the new files tracked
echo "rsynced tree: pair_base assert = $(grep -c 'TRON_ASSERT_LT(token, Rows)' h/tron/tensor/v_vnni.hpp), is_aligned asserts = $(grep -c 'is_aligned(row, chunk_alignment)' h/tron/tensor/v_vnni.hpp), % 32 clauses = $(grep -c 'Cols % 32' h/tron/tensor/v_vnni.hpp), writable at = $(grep -c 'T& at(size_t token' h/tron/tensor/v_vnni.hpp), fixture = $(grep -c fixture h/tron/tensor/v_vnni.hpp h/tron/models/kv_cache.hpp | tr '\n' ' ')"
$PIN $NIX "clang-format --version; clang-format --dry-run -Werror h/tron/tensor/v_vnni.hpp h/tron/models/kv_cache.hpp t/t_llama_unit.cpp >$T/clang-format.log 2>&1; echo CLANG-FORMAT EXIT \$?"
$PIN $NIX "make lint-notes >$T/lint-notes.log 2>&1; echo LINT-NOTES EXIT \$?"
run_tests() {
  local g=$1 p=$2 t
  for t in $TESTS; do
    $PIN "$g/$t" --skip-benchmarks >"$T/$p.$t.log" 2>&1
    echo "$p $t EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/$p.$t.log" | tail -1))"
  done
  for c in "Sliding KV chunks reserve and restore transactionally|sliding" 'packed V rows keep their bits through set_v\, get_v and at()|packedbits' "append_v_row matches the independent packed-V formula|formula" "scaled_v padding NaN|poison"; do
    name=${c%|*}; tag=${c#*|}
    $PIN "$g/t_llama_unit" "$name" --skip-benchmarks >"$T/$p.$tag.log" 2>&1
    echo "$p $tag case EXIT $? ($(grep -E 'All tests passed|test cases:|No tests ran' "$T/$p.$tag.log" | tail -1))"
  done
}
t0=$(date +%s)
$PIN $NIX "cmake --build gen -j 48 -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXON EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen build took $(( $(date +%s) - t0 )) s; t_llama_unit mtime $(stat -c %y gen/t_llama_unit | cut -c1-19)"
run_tests gen amxon
TRON_AMX_DISABLE=1 $PIN gen/t_amx_numerics --skip-benchmarks >"$T/amxon.t_amx_numerics.disabled.log" 2>&1
echo "amxon t_amx_numerics kill-switch EXIT $? ($(grep -E 'All tests passed|test cases:' "$T/amxon.t_amx_numerics.disabled.log" | tail -1); 'AMX unavailable' lines: $(grep -c 'AMX unavailable' "$T/amxon.t_amx_numerics.disabled.log"))"
t0=$(date +%s)
$PIN $NIX "cmake --build gen-amxoff -j 48 --target $TESTS -- -k 0 2>&1 | grep -vE '$PROGRESS' | grep -E 'error|FAILED|warning: |ninja: build stopped' | head -80; echo BUILD-AMXOFF EXIT \${PIPESTATUS[0]}"
echo "$(ts) gen-amxoff build took $(( $(date +%s) - t0 )) s; t_llama_unit mtime $(stat -c %y gen-amxoff/t_llama_unit | cut -c1-19)"
run_tests gen-amxoff amxoff
step_done unit "done (see $LOG)"
# ---- 3. runtron.runar + objdump comparison ----
wt=/var/tmp/jhan/tron-i4525rt2
[ "$(git -C "$wt" status --porcelain | wc -l)" -eq 0 ] || { step_done build "$wt dirty: abort"; finish chain-failed-dirty-worktree; exit 1; }
t0=$(date +%s)
RES=$RES SRC=$SRCWT COMMIT=$HEAD_SHA WT=$wt SUFFIX=runar CONFIGURE_ARGS="$RT_CONFIGURE" TARGETS=runtron TESTS= JOBS=48 bash "$B"; brc=$?
n=0; [ -x "$RT_HEAD" ] && n=$(strings "$RT_HEAD" | grep -c ingested-qwen-3-4b-instruct-2507)
if [ "$(cat "$RES/build-runar.done" 2>/dev/null)" = ok ] && [ "${n:-0}" -gt 0 ]; then step_done build-runar "ok tip=$(git -C "$wt" rev-parse HEAD) in $(( $(date +%s) - t0 )) s"
else step_done build-runar "FAILED rc=$brc done=$(cat "$RES/build-runar.done" 2>/dev/null)"; finish chain-failed-build-runar; exit 1; fi
sha256sum "$RT_BASE" "$RT_PREV" "$RT_HEAD" | tee "$RES/binaries.sha256"
objdump -d -C "$RT_PREV" >"$T/objdump.squash.txt" 2>/dev/null
objdump -d -C "$RT_HEAD" >"$T/objdump.runar.txt" 2>/dev/null
{ echo "--- KV + attention functions, runtron.squash (c5d44bd86f) vs runtron.runar ($HEAD_SHA), default pattern:"
  python3 "$FNDIFF" "$T/objdump.squash.txt" "$T/objdump.runar.txt"
  echo "--- row-path functions only:"
  python3 "$FNDIFF" "$T/objdump.squash.txt" "$T/objdump.runar.txt" 'set_v|get_v|save_v|v_source_row|v_destination_row|pair_base|append_v_row|load_row|copy_token|copy_from|scaled_v_expr|v_head_fn'
} >"$RES/fn-diff.txt" 2>&1
echo "$(ts) fn-diff summary: $(sed -n 2p "$RES/fn-diff.txt")"
rm -f "$T/objdump.squash.txt" "$T/objdump.runar.txt"
step_done objdump "done ($RES/fn-diff.txt)"
# ---- 4. Step D token identity ----
if rinzler_active; then
  t0=$(date +%s); timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down; echo "$(ts) serving-down rc=$? in $(( $(date +%s) - t0 )) s"
fi
t0=$(date +%s)
ATTN=cpu PROMPT=1024 LEN=256 SMOKE_ARMS="base head headoff" bash "$C/smoke.sh"; src=$?
step_done D-cpu "p1024: $(cat "$RES/smoke/cpu-p1024/smoke.done" 2>/dev/null) (smoke.sh rc=$src, $(( $(date +%s) - t0 )) s)"
# ---- 5. bench row (whole machine) ----
builtin cd "$UT" || exit 1
cp config/test-benchmarks.json "$RES/test-benchmarks.before.json"
t0=$(date +%s)
$NIX "env -u SYSTEM_CONFIG bin/slice bench --check-platform >$T/bench-check-platform.log 2>&1; echo BENCH-CHECK-PLATFORM EXIT \$?; head -5 $T/bench-check-platform.log"
$NIX "env -u SYSTEM_CONFIG bin/slice bench --update t_llama_unit >$T/bench-update.log 2>&1; echo BENCH-UPDATE EXIT \$?"
echo "$(ts) bench took $(( $(date +%s) - t0 )) s"
tail -30 "$T/bench-update.log"
cp config/test-benchmarks.json "$RES/test-benchmarks.after.json"
diff "$RES/test-benchmarks.before.json" "$RES/test-benchmarks.after.json" >"$RES/test-benchmarks.diff"; echo "bench json diff lines: $(wc -l <"$RES/test-benchmarks.diff")"
cat "$RES/test-benchmarks.diff"
step_done bench "done"
# ---- 6. finish ----
finish chain-finished
