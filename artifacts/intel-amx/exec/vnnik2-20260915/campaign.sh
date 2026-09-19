#!/usr/bin/env bash
# vnnik2-20260915: measure the two K-store remedies of the VNNIed-K branch (commit
# 9928cb2849: (a) 16-token block store, (b) striping over the idle main helpers) against
# the AMX baseline and the unchanged VNNI store, qwen3-4b, 8 users, on OUR half of
# delphi-3bda. Fork of exec/vnnik-20260914/campaign.sh (runtron cells + greedy smoke).
#
# Words used here: tron = the inference program under test; runtron = its command-line
# tool; AMX = the Intel matrix instruction set used for CPU attention; VNNI layout = the
# pair-interleaved K layout the branch stores K in; TPS = generated tokens per second per
# user in decode; TTFT = time to first token = runtron's "Parsing the prompt took" time.
#
# Arms (CPU attention, USE_HW_ATTN=0, AMX on in all; one new binary with two runtime
# switches so the arms interleave inside each repetition):
#   base  = runtron.p0perf13 (commit 544ca05c7a, row-major K)           [control, PR #3879]
#   vnni  = runtron.vnnik    (tip 5e45ae55ae, VNNI K, per-token scatter) [control, Monday's binary]
#   vnni0 = runtron.vnnik2 with TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=0 (the old store in the new binary)
#   a     = runtron.vnnik2 with TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=0 (block store only)
#   b     = runtron.vnnik2 with TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=1 (helper striping only)
#   ab    = runtron.vnnik2 with both on (the branch default)
# Cells: tp2 (--instance 2,4) prompt 1024 / 2048 x RT_REPS (default 3); tp4 (--instance
# 1,2) x TP4_REPS (default 2); then prompt 8192 at tp2 and tp4 x LONG_REPS (default 2);
# arms interleaved inside each repetition. 256 generated tokens per user.
# Phases: wait for the build marker -> greedy smoke (1 user, temperature 0; arms vnni
# vnni0 a b ab + ab2 A/A; the K store is data movement, so every VNNI arm must produce
# identical tokens) -> Perfetto traces of the four new arms (exec/vnnik-trace-20260914/
# trace.sh, prompt 1024, tp2 + tp4) -> runtron cells -> summary.
# Guards as before: campaign guard per run (lease + flock + our runtron + serving), 10-s
# watcher kills OUR binaries if the lease turns busy, pre-CI hold 01:40-03:45 UTC,
# `env -u SYSTEM_CONFIG` on every tron process.
# Idle-serving takeover (2026-09-15): when the lease is free and an active rinzler@N unit
# is the only blocker, wait_clear calls rinzler_takeover_if_idle (lib-guard.sh) on every
# poll; it stops the units and removes their hugepage slice files once the journal shows
# 10 min without requests and no remote connections.
# Never edit this file while a campaign runs it: bash re-reads a running script from
# its byte offset after every forked command (2026-09-14: an edit during the tp2 loop
# had to be compensated by shortening this header by the same byte count).
# Outputs: exec/results/vnnik2-20260915/{smoke/, rt-results.txt, rt/, summary.json,
# summary.md}, traces in exec/results/vnnik2-trace-20260915/; log
# exec/logs/vnnik2-20260915.log; status .status; marker .done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/vnnik2-20260915
NAME=${NAME:-vnnik2-20260915}   # results/log/marker name; a second round sets NAME, WT, SUFFIX
RES=$EXEC/results/$NAME
TRES=$EXEC/results/${NAME/vnnik2-/vnnik2-trace-}
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
WT=${WT:-/var/tmp/jhan/tron-vnnik2}
SUFFIX=${SUFFIX:-vnnik2}
RT_BASE=/var/tmp/jhan/tron-p0perf13/gen/runtron.p0perf13
RT_VNNI=/var/tmp/jhan/tron-vnnik/gen/runtron.vnnik
RT_NEW=$WT/gen/runtron.$SUFFIX
OUR_RT_RE='^/var/tmp/jhan/tron-(vnnik[234]?|p0perf13)/gen/runtron[.](vnnik[234]?|p0perf13) '
RUN_TRACES=${RUN_TRACES:-1}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
RT_REPS=${RT_REPS:-3}; TP4_REPS=${TP4_REPS:-2}; LONG_REPS=${LONG_REPS:-2}
PROMPTS=${PROMPTS:-"1024 2048"}
ARMS=${ARMS:-"base vnni vnni0 a b ab"}
SMOKE_ARMS=${SMOKE_ARMS:-"vnni vnni0 a b ab ab2"}
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
BILL_UID=1062305141
mkdir -p "$RES/rt" "$RES/smoke" "$TRES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
arm_bin() { case $1 in base) echo "$RT_BASE" ;; vnni) echo "$RT_VNNI" ;; vnni0|a|b|ab) echo "$RT_NEW" ;; *) return 1 ;; esac; }
arm_env() {
  case $1 in
    base|vnni) echo "" ;;
    vnni0) echo "TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=0" ;;
    a) echo "TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=0" ;;
    b) echo "TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=1" ;;
    ab) echo "TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=1" ;;
    *) return 1 ;;
  esac
}
arm_tip() { case $1 in base) echo 544ca05c7a ;; vnni) echo 5e45ae55ae ;; *) echo "$TIP" ;; esac; }

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  return 1
}
wait_clear() {
  local why waited=0
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    # 2026-09-15: the nightly leaves its rinzler@N units up; when they are the only blocker,
    # stop them once idle (lib-guard.sh recipe) instead of waiting for a person to do it.
    [ "$why" = "rinzler@N unit active" ] && rinzler_takeover_if_idle && continue
    sleep 120
  done
  return 0
}
take_guard() {
  local waited=0
  until campaign_guard_acquire; do
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; pgrep -a -x 'runtron(\.[a-z0-9]+)?' 2>/dev/null | cut -c1-160 | sed 's/^/  runtron seen: /'; }
    sleep 60; wait_clear
  done
}
kill_ours() { local pids; pids=$(pgrep -u jhan -f "$OUR_RT_RE" | tr '\n' ' '); [ -n "$pids" ] && { echo "$(ts) kill_ours: TERM runtron pids $pids"; pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; }; return 0; }
watch_run() {
  local sf=$1 why main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || { kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; sleep 2; remove_our_slice_files; exit 0; }
    why=""; if ci_lease_busy; then why="CI lease busy"; elif rinzler_active; then why="rinzler@N unit active"; fi
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill"
}
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-vnnik*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
finish() {
  stop_watcher
  if [ "$1" = aborted ]; then
    trap '' TERM
    kill_ours
    for _ in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
    pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: SIGKILL to our runtron"; sleep 2; }
  fi
  remove_our_slice_files
  campaign_guard_release 2>/dev/null
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}

run_smoke() {
  local arm base_arm bin envv rc out stops
  for arm in $SMOKE_ARMS; do
    base_arm=${arm%2}; bin=$(arm_bin "$base_arm"); envv=$(arm_env "$base_arm"); out=$RES/smoke/$arm; stops=0
    while :; do
      [ -s "$out.tokens" ] && { echo "$(ts) smoke $arm already done"; break; }
      wait_clear; take_guard
      status "phase 2: smoke $arm"
      echo "### smoke arm=$arm bin=$bin env=${envv:-unset} tip=$(arm_tip "$base_arm") prompt=1024 len=128 users=1 temperature=0 pay-for-determinism $(ts) $(machine_line)" >>"$RES/smoke/smoke.txt"
      rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
      (cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info ${envv:+env $envv} \
          timeout 600 "$bin" stream-generate-text -m "$QWEN2" $(placement 2) --hugepage_file /dev/hugepages/amx-vnnik -o \
          --prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
      rc=$?
      stop_watcher; campaign_guard_release; remove_our_slice_files
      echo "smoke $arm rc=$rc $(grep -E 'average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-200)" >>"$RES/smoke/smoke.txt"
      if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
        echo "SMOKE-STOPPED arm=$arm rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)" >>"$RES/smoke/smoke.txt"
        rm -f "$out.tokens"; stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "SMOKE-GIVEN-UP arm=$arm" >>"$RES/smoke/smoke.txt"; break; }
        sleep 120; continue
      fi
      [ $rc -eq 0 ] && [ -s "$out.tokens" ] || echo "SMOKE-FAILED arm=$arm rc=$rc" >>"$RES/smoke/smoke.txt"
      break
    done
  done
  python3 "$C/compare_tokens.py" "$RES/smoke" >>"$RES/smoke/smoke.txt" 2>&1 || true
  tail -12 "$RES/smoke/smoke.txt"
}

run_rt() {  # $1 tp  $2 prompt  $3 arm  $4 rep
  local tp=$1 prompt=$2 arm=$3 rep=$4 model rlog attempt stops=0 rc res envv bin
  case $tp in 2) model=$QWEN2 ;; 4) model=$QWEN4 ;; esac
  bin=$(arm_bin "$arm"); envv=$(arm_env "$arm")
  rlog=$RES/rt/tp${tp}__p${prompt}__${arm}__rep${rep}.log
  if grep -q "average tok/s" "$rlog" 2>/dev/null; then echo "$(ts) runtron tp$tp p$prompt $arm rep$rep already done"; return 0; fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    attempt=$((attempt + 1))
    wait_clear; take_guard
    status "phase 3: runtron tp$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt"
    echo "### runtron tp=$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt bin=$bin tip=$(arm_tip "$arm") env=${envv:-none} len=256 users=8 $(ts) $(machine_line)" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug ${envv:+env $envv} \
        timeout 1200 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file /dev/hugepages/amx-vnnik -o \
        --prompt-length "$prompt" -l 256 -u 8) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog.attempt$attempt)" >>"$RES/rt-results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP after 3 stops" >>"$RES/rt-results.txt"; return 1; }
      sleep 120; continue
    fi
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
      { echo "RUN-FAILED rc=$rc (full output: $rlog.attempt$attempt)"; echo "$res"; } >>"$RES/rt-results.txt"; return 1
    fi
    cp "$rlog.attempt$attempt" "$rlog"
    echo "$res" >>"$RES/rt-results.txt"
    return 0
  done
}

[ "${VNNIK2_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
instck=$(mktemp /tmp/vnnik2-instck.XXXXXX)
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/vnnik2-20260915/campaign[.]sh$' >"$instck"
others=$(grep -vx "$$" "$instck" | tr '\n' ' '); rm -f "$instck"
if [ -n "$others" ]; then echo "$(ts) another campaign.sh instance is running (pids $others); this one exits"; exit 1; fi
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ RT_REPS=$RT_REPS TP4_REPS=$TP4_REPS LONG_REPS=$LONG_REPS PROMPTS=[$PROMPTS] ARMS=[$ARMS] ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"

# phase 1: the build marker (build.sh writes ok | build-failed | tests-failed-N)
status "phase 1: waiting for the build marker"
while :; do
  m=$(cat "$RES/build.done" 2>/dev/null || true)
  [ "$m" = ok ] && break
  case $m in build-failed*|tests-failed*|worktree-failed|checkout-failed|no-qwen) echo "$(ts) build marker says '$m'; campaign ends"; finish "build:$m"; exit 1 ;; esac
  sleep 30
done
TIP=$(git -C "$WT" rev-parse HEAD)
[ -x "$RT_NEW" ] || { echo "$(ts) $RT_NEW missing"; finish no-new-binary; exit 1; }
[ -x "$RT_BASE" ] && [ -x "$RT_VNNI" ] || { echo "$(ts) control binary missing"; finish no-control-binary; exit 1; }
echo "$(ts) TIP=$TIP; $(machine_line)"
cat "$RES/build.txt"

# phase 2: smoke
run_smoke

# phase 2b: traces of the new arms (Save K span), prompt 1024, tp2 + tp4
if [ "$RUN_TRACES" = 1 ]; then
status "phase 2b: traces"
wait_clear
ARMS="vnni0 a b ab" TPS="2 4" RES="$TRES" LOG="$EXEC/logs/${NAME/vnnik2-/vnnik2-trace-}.log" MARKER="$EXEC/logs/${NAME/vnnik2-/vnnik2-trace-}.done" \
  ARM_vnni0_BIN="$RT_NEW" ARM_vnni0_ENV="TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=0" \
  ARM_a_BIN="$RT_NEW" ARM_a_ENV="TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=0" \
  ARM_b_BIN="$RT_NEW" ARM_b_ENV="TRON_K_VNNI_BLOCK=0 TRON_K_VNNI_STRIPE=1" \
  ARM_ab_BIN="$RT_NEW" ARM_ab_ENV="TRON_K_VNNI_BLOCK=1 TRON_K_VNNI_STRIPE=1" \
  bash "$EXEC/vnnik-trace-20260914/trace.sh"
echo "$(ts) traces: $(cat "$EXEC/logs/${NAME/vnnik2-/vnnik2-trace-}.done" 2>/dev/null)"
fi

# phase 3: cells
{
  echo "# $NAME runtron results: qwen-3-4b, 8 users, 256 generated; host $(hostname); started $(ts)"
  echo "# new tip $TIP (runtron.$SUFFIX); controls: runtron.vnnik 5e45ae55ae, runtron.p0perf13 544ca05c7a"
  echo "# placement tp2: $(placement 2)"
  echo "# placement tp4: $(placement 4)"
  echo "# arms: base = p0perf13; vnni = vnnik (old store); vnni0/a/b/ab = vnnik2 with TRON_K_VNNI_BLOCK/TRON_K_VNNI_STRIPE = 0/0, 1/0, 0/1, 1/1; USE_HW_ATTN=0; env -u SYSTEM_CONFIG; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug"
  sha256sum "$RT_BASE" "$RT_VNNI" "$RT_NEW"
} >>"$RES/rt-results.txt"
rt_fail=0
for rep in $(seq 1 "$RT_REPS"); do for prompt in $PROMPTS; do for arm in $ARMS; do run_rt 2 "$prompt" "$arm" "$rep" || rt_fail=$((rt_fail + 1)); done; done; done
echo "$(ts) tp2 cells done, failed runs: $rt_fail"
for rep in $(seq 1 "$TP4_REPS"); do for prompt in $PROMPTS; do for arm in $ARMS; do run_rt 4 "$prompt" "$arm" "$rep" || rt_fail=$((rt_fail + 1)); done; done; done
echo "$(ts) tp4 cells done, failed runs total: $rt_fail"
for rep in $(seq 1 "$LONG_REPS"); do for tp in 2 4; do for arm in ${LONG_ARMS:-$ARMS}; do run_rt "$tp" 8192 "$arm" "$rep" || rt_fail=$((rt_fail + 1)); done; done; done
echo "$(ts) prompt-8192 cells done, failed runs total: $rt_fail"

status "phase 4: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
finish "$([ $rt_fail -eq 0 ] && echo ok || echo "ok-with-$rt_fail-failed-runs")"
