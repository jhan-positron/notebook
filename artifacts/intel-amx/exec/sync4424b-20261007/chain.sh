#!/usr/bin/env bash
# sync4424b-20261007 chain (runs ON delphi-3bda, detached): build and test the PR #4424 branch after it took main
# (PR #4557 typed KV-cache tensors, merged 2026-10-07) and the typed K port of PR #4746, against two references.
#   base = main at be0d5565b3 (the PR #4557 merge commit; row-major K, AMX dispatch ON), built here into
#          /var/tmp/jhan/tron-main1007 (runtron.main1007)
#   head = PR #4424 head 30c4ac82cb (/var/tmp/jhan/tron-tilec/gen/runtron, VNNI K, built 2026-09-17)
#   new  = COMMIT of the synced branch, built here into /var/tmp/jhan/tron-sync6 (runtron.sync6)
# The port changes no stored byte and no kernel: new must reproduce head token for token, and its TPS/TTFT must sit
# inside head's band. new vs base gives the PR #4424 "measure against a main binary" open item.
# Steps (every step waits for the CI lease with 600 s grace and for other people's activity to end; bill is excluded by
# the half-split agreement):
#   A.  VNNI build (preset native = explicit AVX-512 flags; AMX dispatch ON, TRON_K_VNNI ON, ingest models ON):
#       runtron + the unit tests, run with the fake device on our half; then t_amx_numerics once more with
#       TRON_AMX_DISABLE=1 (kill-switch control).
#   A2. the ingest Haskell test suite (bin/ingest-cabal test) in the same worktree.
#   B.  row-major build (TRON_K_VNNI OFF, ingest OFF) in /var/tmp/jhan/tron-sync6rm: the layout-independent tests.
#   A0. base build: main be0d5565b3, runtron only (TRON_K_VNNI OFF, ingest ON).
#   serving-down, then
#   C.  the whole host test suite in the VNNI build tree (make build-test-host + make test-host, fake device, our half).
#       References: PR #4424 89/1/0; 2026-10-02 sync chain 90/1/0; 2026-10-06 savek chain 89/1/0.
#   D.  token identity (1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2):
#       new == head, new == new2, newoff == headoff; cpu p1024, fpga p1024, cpu p8192. new vs base is expected to
#       diverge at token 52 (issue #4444).
#   E.  performance (8 users, 256 tokens, 3 repetitions, arms interleaved): E-cpu prompt 1024/8192, E-fpga prompt 1024,
#       arms base head new. Pass = new inside the band of head (max(2*max sd, 0.4 TPS / 0.15 s)).
#   F.  cost rows: bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics in the VNNI tree, ONLY when the
#       whole machine is free (serving down, bill idle: other_user_active without the bill exclusion). Diff saved to
#       RES/bench-update.diff for a commit on claude-box.
#   4.  production serving back up through platformd when this chain took it down.
# Usage (on 3bda): COMMIT=<full sha of the synced branch> [END_BY=ISO] bash chain.sh   (see launch.sh)
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/sync4424b-20261007
S=$EXEC/sync4424-20261002
B=$EXEC/i4525-20260922/build2.sh
export NAME=sync4424b-20261007
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the synced branch) is required}
BASE_COMMIT=be0d5565b355a90b6018529d3310565c3f5909cb
export RT_HEAD=/var/tmp/jhan/tron-tilec/gen/runtron
export RT_BASE=/var/tmp/jhan/tron-main1007/gen/runtron.main1007
export RT_NEW=/var/tmp/jhan/tron-sync6/gen/runtron.sync6
export ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
WT=/var/tmp/jhan/tron-sync6
# --preset cross-avx512 no longer exists on main (PR 4726); native = explicit AVX-512 flags, no -march=native.
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
CONF_BASE='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TARGETS_VNNI='runtron t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_gof_dma t_gof_staging_leaks t_phase1_integration'
TESTS_VNNI='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
END_BY=${END_BY:-$(date -u -d 'today 01:30' +%FT%TZ)}
END_EPOCH=$(date -u -d "$END_BY" +%s); [ "$END_EPOCH" -gt "$(date -u +%s)" ] || END_EPOCH=$((END_EPOCH + 86400))
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$END_EPOCH" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/chain-steps.txt"; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy or another person active"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
exec >>"$LOG" 2>&1
rm -f "$RES/chain.done"
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT base=$BASE_COMMIT end=$(date -u -d @"$END_EPOCH" +%FT%TZ) ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
[ -x "$RT_HEAD" ] || { step_done start "reference binary $RT_HEAD missing: abort"; echo missing-reference >"$RES/chain.done"; exit 1; }

# ---- A. VNNI build + unit tests ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=sync6 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_VNNI" TESTS="$TESTS_VNNI" JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-sync6.done" 2>/dev/null) $(cat "$RES/tests-sync6.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"
[ "$(cat "$RES/build-sync6.done" 2>/dev/null)" = ok ] || { echo chain-failed-A >"$RES/chain.done"; exit 1; }
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" TRON_AMX_DISABLE=1 timeout -k 60 1800 ./gen/t_amx_numerics ) >"$RES/tests-sync6-t_amx_numerics-killswitch.out" 2>&1
echo "t_amx_numerics killswitch rc=$? $(grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$RES/tests-sync6-t_amx_numerics-killswitch.out" | tr '\n' ' ' | cut -c1-400)" | tee -a "$RES/tests-sync6.txt"
n=$(strings "$RT_NEW" | grep -c ingested-qwen-3-4b-instruct-2507); echo "$(ts) runtron.sync6 qwen3-4b plugin strings=$n"
[ "${n:-0}" -gt 0 ] || { step_done A "runtron.sync6 lacks the qwen3-4b plugin: abort"; echo chain-failed-plugin >"$RES/chain.done"; exit 1; }
echo "$(ts) generated plugin grep: save_k main-side=$(grep -rlE 'save_k<' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l) files, save_k_helper=$(grep -rl 'save_k_helper' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l) files" | tee -a "$RES/tests-sync6.txt"

# ---- A2. ingest Haskell tests ----
wait_slot "step A2"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-sync6.txt" 2>&1
echo "$(ts) ingest tests done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|examples,|failures' "$RES/ingest-test-sync6.txt" | tr '\n' ' ' | cut -c1-300)" | tee -a "$RES/tests-sync6.txt"
step_done A2 "$(grep -E 'ingest-cabal-test rc=' "$RES/ingest-test-sync6.txt") $(grep -E 'examples,' "$RES/ingest-test-sync6.txt" | tail -1)"

# ---- B. row-major build + tests ----
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-sync6rm SUFFIX=sync6rm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" JOBS=64 bash "$B"
step_done B "$(cat "$RES/build-sync6rm.done" 2>/dev/null) $(cat "$RES/tests-sync6rm.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"

# ---- A0. base build (main, runtron only) ----
if [ ! -x "$RT_BASE" ]; then
  wait_slot "step A0"
  env RES="$RES" SRC="$REPO" COMMIT="$BASE_COMMIT" WT=/var/tmp/jhan/tron-main1007 SUFFIX=main1007 CONFIGURE_ARGS="$CONF_BASE" TARGETS=runtron TESTS= JOBS=64 bash "$B"
  step_done A0 "$(cat "$RES/build-main1007.done" 2>/dev/null)"
else
  step_done A0 "base binary present, build skipped"
fi
[ -x "$RT_BASE" ] || { echo chain-failed-A0 >"$RES/chain.done"; exit 1; }

# ---- serving down, C (host suite), D (token identity) ----
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); smoke.sh retries"
fi
wait_slot "step C"
env RES="$RES" WT="$WT" SUFFIX=sync6 bash "$EXEC/i4525-20260922/host-suite.sh"
step_done C "$(cat "$RES/host-suite-sync6.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-sync6.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"

export MUST_MATCH="new:new2 new:head newoff:headoff headoff:head newoff:new"
for spec in "cpu 1024 base head new new2 headoff newoff" "fpga 1024 base head new" "cpu 8192 base head new"; do
  past_end && { step_done D "skipped $spec: past END_BY"; continue; }
  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
  step_done D "$attn p$prompt: $(cat "$RES/smoke/$attn-p$prompt/smoke.done" 2>/dev/null)"
done

# ---- E. performance ----
cells() { local p out=""; for p in "$@"; do out+="q3-4b-tp2-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp2|2|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
run_e() {  # $1 name $2 attns $3 arms $4 pairs $5.. prompts
  local name=$1 attns=$2 arms=$3 pairs=$4; shift 4
  past_end && { step_done "$name" "skipped: past END_BY"; return; }
  NAME=$name CELLS_ALL="$(cells "$@")" ARMS="$arms" ATTNS="$attns" REPS=3 DEADLINE_HHMM=0130 \
    WEDPERF_ARMS="$arms" WEDPERF_PAIRS="$pairs" bash "$S/campaign.sh"
  step_done "$name" "$(cat "$EXEC/logs/$name.done" 2>/dev/null)"
}
run_e sync6-E-cpu cpu "base head new" "new:head new:base" 1024 8192
run_e sync6-E-fpga fpga "base head new" "new:head new:base" 1024

# ---- F. cost rows (whole machine: serving down and bill idle) ----
if past_end; then step_done F "skipped: past END_BY"
elif ci_lease_busy 600; then step_done F "skipped: CI lease busy"
elif rinzler_active; then step_done F "skipped: serving active"
elif GUARD_EXCLUDE_USERS="jhan nobody positron packer" other_user_active 2>/dev/null; then step_done F "skipped: another person (bill?) active"
else
  t0=$(date +%s)
  ( cd "$WT" && git diff --quiet -- config/test-benchmarks.json && "$NIX" develop --accept-flake-config --command bash -c 'env -u SYSTEM_CONFIG bin/slice bench --update t_llama_unit t_k_vnni_layout t_amx_numerics 2>&1 | tail -30; echo "bench-update rc=${PIPESTATUS[0]}"' ) >"$RES/bench-update.log" 2>&1
  ( cd "$WT" && git diff -- config/test-benchmarks.json ) >"$RES/bench-update.diff"
  step_done F "$(grep -E 'bench-update rc=' "$RES/bench-update.log") in $(( $(date +%s) - t0 )) s, diff $(wc -l <"$RES/bench-update.diff") lines"
fi

# ---- 4. serving back up ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
step_done end "chain finished"
echo chain-finished >"$RES/chain.done"
echo "=== $NAME chain finished $(ts) ==="
