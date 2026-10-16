#!/usr/bin/env bash
# i4934-20261015 driver (runs ON delphi-3bda, detached; fork of exec/pr4-20261012/probe-lazy.sh): build and test the issue
# #4934 fix branch (jhan-vnnik-5-i4934, commit COMMIT, based on PR #4901's head 175b1837b9), then measure it against PR #4901
# (new/newoff) and PR #4898 (head/headoff) in the three CPU cells of the issue and the two FPGA cells of PR4-handoff.md step 6.
# Words: "our half" = socket 1 (cpus 72-143,216-287, SYSTEM_CONFIG="--instance 1,2" for the fake device); "the option" =
# TRON_K_VNNI; "AMX dispatch" = TRON_AMX_DISPATCH; "kill switch" = TRON_AMX_DISABLE=1; "fix" = runtron.fix built from COMMIT.
# Our-half steps (next to production serving; each waits for the CI lease with 600 s grace, for other people, and outside the
# 02:10-03:45 UTC pre-CI hold):
#   A.    option on + AMX dispatch on (CONF_VNNI): runtron + 6 unit tests (--skip-benchmarks), into /var/tmp/jhan/tron-i4934
#   A-ks. the same tree: t_llama_unit, t_amx_numerics and t_heterogeneous_scheduler once more with the kill switch (exit 0)
#   ourhalf.done = ok only when both build-*.done are ok (build ok and every test binary exited 0); the whole-machine part
#   needs that. After the whole-machine part, next to the restored serving:
#   B.    option off (CONF_RM, row-major K): the 5 layout-independent tests, into /var/tmp/jhan/tron-i4934rm
#   A3.   option on + AMX dispatch OFF (CONF_A3): the 6 tests, into /var/tmp/jhan/tron-i4934nd
#   otherbuilds.done = ok | failed-<suffix>: a failure there is a finding, not a stop (the cells already ran).
# Whole-machine steps (exec/bill-share.sh take first, on jhan's order; refused while Bill is active -> probe.done=stopped-marker):
#   1.    serving down through platformd (exec/q4b-fpga-20260921/dut.sh serving-down)
#   T.    Perfetto traces (informational, tracing distorts timing): newoff and fixoff at tp2, prompt 1024 (passes 1, 8, 120-150)
#         and prompt 8192 (passes 1, 2, 64, 100-110), --trace-gen in-process; files $RES/trace-<arm>-p<prompt>.pftrace
#   E.    CPU attention cells tp2 p1024, tp2 p8192, tp4 p1024; arms head headoff new newoff fix fixoff; 3 reps (campaign-fix.sh)
#   F.    FPGA attention cells tp2 p1024, tp4 p1024; arms head new fix; 3 reps
#   end.  probe.done = E=<..> F=<..>; the exit handler (chain-finish.sh): serving up, Bill's marker released, machine line.
# Usage (on 3bda): COMMIT=<full sha> END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] [SKIP_OURHALF=1] bash probe-fix.sh
# Stop: kill -- -<pid> (setsid: the pid is the group id); the exit handler restores serving and releases the marker.
# Never edit this file while it runs (bash re-reads a running script over NFS): copy to a new name.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
P4=$EXEC/pr4-20261012
B=$EXEC/i4525-20260922/build2.sh
DUT=$EXEC/q4b-fpga-20260921/dut.sh
BILL_SHARE=$EXEC/bill-share.sh
export NAME=i4934-20261015
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-probe.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?COMMIT (full sha of the fix commit) is required}
END_BY=${END_BY:?END_BY (ISO UTC) is required}
START_NOT_BEFORE=${START_NOT_BEFORE:-}
SKIP_OURHALF=${SKIP_OURHALF:-0}
OUR_CPUS=72-143,216-287
WT=/var/tmp/jhan/tron-i4934
WT_RM=/var/tmp/jhan/tron-i4934rm
WT_ND=/var/tmp/jhan/tron-i4934nd
export RT_FIX=$WT/gen/runtron.fix
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_fixoff=TRON_AMX_DISABLE=1 ARM_ENV_baseoff=TRON_AMX_DISABLE=1
export SKIP_SERVING_UP=1
CONF_VNNI='--preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_A3='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=OFF -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
TESTS_6='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler t_phase1_integration'
TESTS_RM='t_k_vnni_layout t_amx_dispatch_dtype t_amx_numerics t_llama_unit t_heterogeneous_scheduler'
TESTS_KS='t_llama_unit t_amx_numerics t_heterogeneous_scheduler'
mkdir -p "$RES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_RUNTRON_USER=jhan GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
past_end() { [ "$(date -u +%s)" -ge "$(date -u -d "$END_BY" +%s)" ]; }
step_done() { echo "$(ts) STEP $1: $2" | tee -a "$RES/steps.txt"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 210 ] && [ "$hm" -lt 345 ]; }
wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/probe.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }
machine() { echo "lease=$(ci_lease_busy && echo busy || echo free) units=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 | tr '\n' ' ') load=$(cut -d' ' -f1-3 /proc/loadavg) hp_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"; }
OUR_RT_RE="^($(printf '%s' "$RT_BASE" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_HEAD" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_NEW" | sed 's/[.[\*^$()+?{}|]/\\&/g')|$(printf '%s' "$RT_FIX" | sed 's/[.[\*^$()+?{}|]/\\&/g')) "
MARKER_TAKEN=0
SERVING_DOWN_BY_US=0
MARKER=/var/tmp/jhan/$NAME.not-used   # chain-finish.sh needs the name; this driver never creates a hand-off marker
MARKER_CREATED=0
source "$P4/chain-finish.sh"
trap 'finish term; exit 143' TERM
trap 'finish exit' EXIT
exec >>"$LOG" 2>&1
rm -f "$RES/probe.done"
echo "=== $NAME driver started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) COMMIT=$COMMIT END_BY=$END_BY START_NOT_BEFORE=${START_NOT_BEFORE:-none} SKIP_OURHALF=$SKIP_OURHALF ==="
echo "$(ts) machine: $(machine)"
git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || { step_done start "$COMMIT not in the shared store: abort"; echo failed-start >"$RES/probe.done"; exit 1; }
for b in "$RT_NEW" "$RT_HEAD" "$RT_BASE"; do [ -x "$b" ] || { step_done start "$b missing: abort"; echo failed-binary >"$RES/probe.done"; exit 1; }; done
if [ -n "$START_NOT_BEFORE" ]; then
  snb=$(date -u -d "$START_NOT_BEFORE" +%s) || { step_done start "bad START_NOT_BEFORE: abort"; echo failed-start >"$RES/probe.done"; exit 1; }
  while [ "$(date -u +%s)" -lt "$snb" ]; do left=$(( snb - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800; echo "$(ts) holding until $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"; done
fi
# ---- our-half steps ----
build() {  # build <suffix> <wt> <conf> <targets> <tests> [test_env]
  local sfx=$1 wt=$2 conf=$3 targets=$4 tests=$5 tenv=${6:-}
  wait_slot "build $sfx"
  env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT="$wt" SUFFIX="$sfx" CONFIGURE_ARGS="$conf" TARGETS="$targets" TESTS="$tests" TEST_ENV="$tenv" TEST_ARGS=--skip-benchmarks JOBS=64 bash "$B"
  step_done "build-$sfx" "$(cat "$RES/build-$sfx.done" 2>/dev/null); $(grep -m1 '^cache:' "$RES/build-$sfx.txt" 2>/dev/null | cut -c1-160); tests: $(cut -c1-200 "$RES/tests-$sfx.txt" 2>/dev/null | tr '\n' '|')"
}
if [ "$SKIP_OURHALF" != 1 ]; then
  build fix "$WT" "$CONF_VNNI" "runtron $TESTS_6" "$TESTS_6"
  [ "$(cat "$RES/build-fix.done" 2>/dev/null)" = ok ] && [ -x "$RT_FIX" ] || { echo failed-build >"$RES/probe.done"; exit 1; }
  for m in tp2 tp4; do n=$(strings "$RT_FIX" | grep -c "ingested-qwen-3-4b-instruct-2507-$m"); [ "${n:-0}" -gt 0 ] || { step_done build "runtron.fix lacks the qwen3-4b $m plugin: abort"; echo failed-plugin >"$RES/probe.done"; exit 1; }; done
  step_done build "runtron.fix $(sha256sum "$RT_FIX" | cut -c1-16) at $(git -C "$WT" rev-parse HEAD)"
  build fixks "$WT" "$CONF_VNNI" "t_llama_unit" "$TESTS_KS" "TRON_AMX_DISABLE=1"
  oh=ok; for s in fix fixks; do [ "$(cat "$RES/build-$s.done" 2>/dev/null)" = ok ] || oh="failed-$s"; done
  echo "$oh" >"$RES/ourhalf.done"; step_done ourhalf "$oh"
  [ "$oh" = ok ] || { echo "stopped-ourhalf-$oh" >"$RES/probe.done"; exit 1; }
else
  [ -x "$RT_FIX" ] || { step_done start "SKIP_OURHALF=1 but $RT_FIX missing: abort"; echo failed-binary >"$RES/probe.done"; exit 1; }
fi
# ---- whole-machine part ----
past_end && { step_done 0 "past END_BY before the whole-machine part"; echo stopped-end-by >"$RES/probe.done"; exit 1; }
wait_slot "step 0"
tout=$(bash "$BILL_SHARE" take 2>&1); trc=$?; echo "$(ts) bill-share take rc=$trc: $(printf "%s" "$tout" | tail -1)"
case $trc in 0) MARKER_TAKEN=1;; *) step_done 0 "Bill marker not taken (rc $trc)"; echo stopped-marker >"$RES/probe.done"; exit 1;; esac
if rinzler_active; then SERVING_DOWN_BY_US=1; IDLE_MIN=5 timeout 1500 bash "$DUT" serving-down || echo "$(ts) serving-down rc=$?"; fi
step_done 1 "serving: $(machine)"
cells() { local s tp p out=""; for s in "$@"; do tp=${s%%:*}; p=${s##*:}; out+="q3-4b-tp$tp-8u-p$p|ingested-qwen-3-4b-instruct-2507-tp$tp|$tp|8|$p"$'\n'; done; printf '%s' "${out%$'\n'}"; }
# ---- T. traces (same placement and flags as campaign-fix.sh run_one at tp2, plus --trace-gen/--trace-passes) ----
PLACE2="--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128"
HPT=/dev/hugepages/amx-$NAME-trace
trace_one() {  # trace_one <arm> <bin> <prompt> <passes>
  local arm=$1 bin=$2 prompt=$3 spec=$4 rc
  local out="$RES/trace-$arm-p$prompt"   # a second statement: bash expands every word of one `local` before it assigns any
  past_end && { echo "$(ts) trace $arm p$prompt skipped: past END_BY"; return 0; }
  until campaign_guard_acquire; do past_end && return 0; sleep 60; done
  echo "$(ts) trace $arm p$prompt start ($(machine))"
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_AMX_DISABLE=1 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
      timeout -k 60 2400 "$bin" stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 $PLACE2 --hugepage_file "$HPT" -o --prompt-length "$prompt" -l 256 -u 8 --dont-stop --trace-gen "$out.pftrace" --trace-passes "$spec") >"$out.log" 2>&1
  rc=$?
  campaign_guard_release
  [ -e "$HPT" ] && [ -O "$HPT" ] && ! fuser -s "$HPT" 2>/dev/null && rm -f "$HPT"
  echo "$(ts) trace $arm p$prompt rc=$rc file=$(stat -c %s "$out.pftrace" 2>/dev/null || echo missing) B; $(grep -E 'average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-200)"
}
trace_one newoff "$RT_NEW" 1024 "1,8,120-150"
trace_one fixoff "$RT_FIX" 1024 "1,8,120-150"
trace_one newoff "$RT_NEW" 8192 "1,2,64,100-110"
trace_one fixoff "$RT_FIX" 8192 "1,2,64,100-110"
step_done T "traces: $(ls -la "$RES"/trace-*.pftrace 2>/dev/null | awk '{print $5, $9}' | tr '\n' ';')"
# ---- E. CPU attention cells ----
if past_end; then step_done E "skipped: past END_BY"; e=skipped; else
  NAME=i4934-E-cpu CELLS_ALL="$(cells 2:1024 2:8192 4:1024)" ARMS="head headoff new newoff fix fixoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \
    SUMMARY_TITLE="# i4934-E-cpu summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch $COMMIT; <arm>off = the same binary with TRON_AMX_DISABLE=1; attn = cpu)" \
    WEDPERF_ARMS="head headoff new newoff fix fixoff" WEDPERF_PAIRS="fixoff:headoff fixoff:newoff fix:new fix:head newoff:headoff new:head" bash "$D/campaign-fix.sh"
  e=$(cat "$EXEC/logs/i4934-E-cpu.done" 2>/dev/null)
  step_done E "$e; head line: $(grep -m1 '^# arms:' "$EXEC/results/i4934-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-240)"
fi
# ---- F. FPGA attention cells ----
if past_end; then step_done F "skipped: past END_BY"; f=skipped; else
  NAME=i4934-E-fpga CELLS_ALL="$(cells 2:1024 4:1024)" ARMS="head new fix" ATTNS=fpga REPS=3 DEADLINE_HHMM=0130 \
    SUMMARY_TITLE="# i4934-E-fpga summary (head = PR #4898 dfafd13dce, new = PR #4901 ea94e95a4e, fix = issue #4934 branch $COMMIT; attn = fpga)" \
    WEDPERF_ARMS="head new fix" WEDPERF_PAIRS="fix:new fix:head new:head" bash "$D/campaign-fix.sh"
  f=$(cat "$EXEC/logs/i4934-E-fpga.done" 2>/dev/null)
  step_done F "$f; head line: $(grep -m1 '^# arms:' "$EXEC/results/i4934-E-fpga/rt-results.txt" 2>/dev/null | cut -c1-240)"
fi
echo "E=$e F=$f" >"$RES/probe.done"
# ---- the other two build configurations, after the cells (serving is restored by the exit handler only at exit; these
# builds run on our half next to whatever serves; a failure is recorded, not a stop) ----
if [ "$SKIP_OURHALF" != 1 ]; then
  build fixrm "$WT_RM" "$CONF_RM" "$TESTS_RM" "$TESTS_RM"
  build fixnd "$WT_ND" "$CONF_A3" "$TESTS_6" "$TESTS_6"
  ob=ok; for s in fixrm fixnd; do [ "$(cat "$RES/build-$s.done" 2>/dev/null)" = ok ] || ob="failed-$s"; done
  echo "$ob" >"$RES/otherbuilds.done"; step_done otherbuilds "$ob"
fi
step_done end "$(cat "$RES/probe.done")"
echo "=== $NAME driver finished $(ts): $(cat "$RES/probe.done") (the exit handler restores serving and releases the marker next) ==="
