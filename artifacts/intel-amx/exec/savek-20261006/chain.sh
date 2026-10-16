#!/usr/bin/env bash
# savek-20261006 chain (runs ON delphi-3bda, detached): build and test branch jhan-amx-vnniK-savek-worker
# (PR #4424 "VNNI K" + the fold of save_k_helper into save_k(worker_ix), Ben's review suggestion r4065141577)
# against the PR #4424 head binary.
#   head = PR #4424 head 30c4ac82cb (/var/tmp/jhan/tron-tilec/gen/runtron, VNNI K, built 2026-09-17)
#   new  = COMMIT of the fold branch, built here into /var/tmp/jhan/tron-savek (runtron.savek)
# The fold changes no stored byte and no kernel: new must reproduce head token for token, and its TPS/TTFT must sit
# inside head's band. Steps (every step waits for the CI lease with 600 s grace and for other people's activity to
# end; bill is excluded by the half-split agreement):
#   A.  VNNI build (cross-avx512 preset, AMX dispatch ON, TRON_K_VNNI ON, ingest models ON: the generated plugins
#       compile the new save_k calls): runtron + the unit tests, run with the fake device on our half; then
#       t_amx_numerics once more with TRON_AMX_DISABLE=1 (kill-switch control).
#   A2. the ingest Haskell test suite (bin/ingest-cabal test) in the same worktree: LoopyTronSpec checks the
#       generated save_k call text on both sides.
#   B.  row-major build (TRON_K_VNNI OFF, ingest OFF) in /var/tmp/jhan/tron-savekrm: the layout-independent tests
#       (the helper side returns at once when the layout is off).
#   D.  serving-down, then
#   C.  the whole host test suite in the VNNI build tree (make build-test-host + make test-host, fake device, our half).
#       PR #4424's reference: 89 passed, 1 skipped (t_proxy_lib), 0 failed; 2026-10-02 sync chain: 90/1/0.
#   D.  token identity (1 user, temperature 0, --pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2):
#       new == head, new == new2, newoff == headoff; cpu p1024, fpga p1024, cpu p8192.
#   E.  performance (8 users, 256 tokens, 3 repetitions, arms interleaved): E-cpu prompt 1024/8192, E-fpga prompt 1024,
#       arms head new. Pass = new inside the band of head (max(2*max sd, 0.4 TPS / 0.15 s)).
#   4.  production serving back up through platformd when this chain took it down.
# Usage (on 3bda): COMMIT=<full sha of the fold branch> [END_BY=ISO] bash chain.sh   (see launch.sh)
# Never edit this file while it runs (bash re-reads a running script; NFS stale-handle trap).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/savek-20261006
S=$EXEC/sync4424-20261002
B=$EXEC/i4525-20260922/build2.sh
export NAME=savek-20261006
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-chain.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the fold branch) is required}
export RT_HEAD=/var/tmp/jhan/tron-tilec/gen/runtron
export RT_BASE=$RT_HEAD   # campaign.sh requires a base; no base arm is run
export RT_NEW=/var/tmp/jhan/tron-savek/gen/runtron.savek
export ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_newoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
WT=/var/tmp/jhan/tron-savek
CONF_VNNI='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
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
echo "=== $NAME chain started $(ts) pid $$ on $(hostname) COMMIT=$COMMIT end=$(date -u -d @"$END_EPOCH" +%FT%TZ) ==="
echo "$(ts) machine: lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
[ -x "$RT_HEAD" ] || { step_done start "reference binary $RT_HEAD missing: abort"; echo missing-reference >"$RES/chain.done"; exit 1; }

# ---- A. VNNI build + unit tests ----
wait_slot "step A"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$WT" SUFFIX=savek CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_VNNI" TESTS="$TESTS_VNNI" JOBS=64 bash "$B"
step_done A "$(cat "$RES/build-savek.done" 2>/dev/null) $(cat "$RES/tests-savek.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"
[ "$(cat "$RES/build-savek.done" 2>/dev/null)" = ok ] || { echo chain-failed-A >"$RES/chain.done"; exit 1; }
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS env SYSTEM_CONFIG="--instance 1,2" TRON_AMX_DISABLE=1 timeout -k 60 1800 ./gen/t_amx_numerics ) >"$RES/tests-savek-t_amx_numerics-killswitch.out" 2>&1
echo "t_amx_numerics killswitch rc=$? $(grep -E 'test cases:|assertions|All tests passed|FAILED|AMX unavailable' "$RES/tests-savek-t_amx_numerics-killswitch.out" | tr '\n' ' ' | cut -c1-400)" | tee -a "$RES/tests-savek.txt"
n=$(strings "$RT_NEW" | grep -c ingested-qwen-3-4b-instruct-2507); echo "$(ts) runtron.savek qwen3-4b plugin strings=$n"
[ "${n:-0}" -gt 0 ] || { step_done A "runtron.savek lacks the qwen3-4b plugin: abort"; echo chain-failed-plugin >"$RES/chain.done"; exit 1; }
# the generated plugin text: both save_k call forms must be present, save_k_helper absent
gen_dir=$(ls -d "$WT"/gen/ingest* "$WT"/gen/models* 2>/dev/null | head -3)
echo "$(ts) generated plugin grep: save_k main-side=$(grep -rlE 'save_k<[^;]*k, *0, *n_workers' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l) files, helper-side=$(grep -rlE 'save_k<[^;]*k, *worker_ix, *n_workers' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l) files, save_k_helper=$(grep -rl 'save_k_helper' "$WT/gen" --include=*.cpp --include=*.hpp 2>/dev/null | wc -l) files (dirs: $gen_dir)" | tee -a "$RES/tests-savek.txt"

# ---- A2. ingest Haskell tests ----
wait_slot "step A2"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-savek.txt" 2>&1
echo "$(ts) ingest tests done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|examples,|failures' "$RES/ingest-test-savek.txt" | tr '\n' ' ' | cut -c1-300)" | tee -a "$RES/tests-savek.txt"
step_done A2 "$(grep -E 'ingest-cabal-test rc=' "$RES/ingest-test-savek.txt") $(grep -E 'examples,' "$RES/ingest-test-savek.txt" | tail -1)"

# ---- B. row-major build + tests ----
wait_slot "step B"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-savekrm SUFFIX=savekrm CONFIGURE_ARGS="$CONF_RM" TARGETS="$TESTS_RM" TESTS="$TESTS_RM" JOBS=64 bash "$B"
step_done B "$(cat "$RES/build-savekrm.done" 2>/dev/null) $(cat "$RES/tests-savekrm.txt" 2>/dev/null | cut -c1-160 | tr '\n' ';')"

# ---- D (serving down), C (host suite), D (token identity) ----
if rinzler_active; then
  timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-down || echo "$(ts) serving-down rc=$? (engines busy?); smoke.sh retries"
fi
wait_slot "step C"
env RES="$RES" WT="$WT" SUFFIX=savek bash "$EXEC/i4525-20260922/host-suite.sh"
step_done C "$(cat "$RES/host-suite-savek.done" 2>/dev/null) $(grep -E '^(build-test-host|test-host) rc=|passed|skipped|failed' "$RES/host-suite-savek.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"

export MUST_MATCH="new:new2 new:head newoff:headoff headoff:head newoff:new"
for spec in "cpu 1024 head new new2 headoff newoff" "fpga 1024 head new" "cpu 8192 head new"; do
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
run_e savek-E-cpu cpu "head new" "new:head" 1024 8192
run_e savek-E-fpga fpga "head new" "new:head" 1024

# ---- 4. serving back up ----
if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, left alone"
elif rinzler_active; then echo "$(ts) serving: rinzler units active, nothing to bring up"
else timeout 900 bash "$EXEC/q4b-fpga-20260921/dut.sh" serving-up || echo "$(ts) serving-up rc=$? (jhan: check platformd)"; fi
echo "$(ts) serving: units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
step_done end "chain finished"
echo chain-finished >"$RES/chain.done"
echo "=== $NAME chain finished $(ts) ==="
