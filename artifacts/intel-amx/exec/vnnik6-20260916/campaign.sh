#!/usr/bin/env bash
# vnnik6-20260916: repeat the qwen-3-30b-a3b (kv_mul 8) cells of PR #4424's open item against a
# main binary, with a third binary that has the layout compiled off, on OUR half of delphi-3bda.
# Fork of exec/vnnik2-20260915/campaign.sh (same guards, same run recipe).
#
# Words used here: tron = the inference program under test; runtron = its command-line tool;
# VNNI layout = the pair-interleaved K layout of PR #4424; kv_mul = query heads per KV head
# (qwen-3-30b-a3b: 32 / 4 = 8; the AMX kernel serves kv_mul 4 only, so this model always runs
# the software attention path); TPS = generated tokens per second per user in decode; TTFT =
# time to first token = runtron's "Parsing the prompt took" time; smoke = 1-user greedy run
# whose token ids are saved; A/A = the same binary run twice (noise control).
#
# Arms (CPU attention, USE_HW_ATTN=0; TRON_AMX_DISABLE unset: it changes nothing for this shape):
#   base    = runtron.main0916    (main c7844ca2ce, TRON_AMX_DISPATCH=ON; row-major K, the dotter)
#   headoff = runtron.headoff0916 (PR head ff680c8020 built with TRON_K_VNNI off: the PR's code
#                                  with the layout off = what a kv_mul gate would run here)
#   vnni    = runtron.vnnik5      (65a1c41d72 = PR head minus the cost-data JSON commit;
#                                  TRON_K_VNNI=ON: VNNI layout, AVX-512 reader on every page)
# Cells: model ingested-qwen-3-30b-a3b-instruct-2507-tp2 / -tp4, 8 users, 256 generated tokens.
#   phase 2  smoke (1 user, prompt 1024, 128 tokens, temperature 0): base base2 headoff vnni vnni2
#   phase 3a tp2 (--instance 2,4) prompt 1024 x RT_REPS (6)
#   phase 3b tp4 (--instance 1,2) prompt 1024 x TP4_REPS (4)
#   phase 3c traces (vnnik6-20260916/trace.sh): every arm at tp2 and tp4, prompt 1024, 32 tokens
#   phase 3d tp2 prompt 2048 x MID_REPS (3)
#   phase 3e tp2 prompt 8192 x LONG_REPS (3), tp4 prompt 8192 x LONG_TP4_REPS (2)
# Arms interleave inside each repetition. Every run: env -u SYSTEM_CONFIG, campaign guard
# (lease + other persons + blackout + flock + no runtron of ours + no serving), a 10-s watcher
# that kills OUR binaries if the lease turns busy, pre-CI hold 01:40-03:45 UTC, idle-serving
# takeover through lib-guard.sh rinzler_takeover_if_idle.
# Never edit this file while a campaign runs it (bash re-reads a running script from its byte
# offset after every forked command).
# Outputs: exec/results/vnnik6-20260916/{smoke/, rt/, rt-results.txt, summary.json, summary.md},
# traces in exec/results/vnnik6-trace-20260916/; log exec/logs/vnnik6-20260916.log; status
# .status; marker .done (ok | ok-with-N-failed-runs | build:... | no-...-binary | aborted).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/vnnik6-20260916
NAME=${NAME:-vnnik6-20260916}
RES=$EXEC/results/$NAME
TRES=$EXEC/results/${NAME/vnnik6-/vnnik6-trace-}
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
RT_BASE=/var/tmp/jhan/tron-main0916/gen/runtron.main0916
RT_HEADOFF=/var/tmp/jhan/tron-headoff0916/gen/runtron.headoff0916
RT_VNNI=/var/tmp/jhan/tron-vnnik5/gen/runtron.vnnik5
OUR_RT_RE='^/var/tmp/jhan/tron-(main0916|headoff0916|vnnik5)/gen/runtron[.](main0916|headoff0916|vnnik5) '
RUN_TRACES=${RUN_TRACES:-1}
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
RT_REPS=${RT_REPS:-6}; TP4_REPS=${TP4_REPS:-4}; MID_REPS=${MID_REPS:-3}; LONG_REPS=${LONG_REPS:-3}; LONG_TP4_REPS=${LONG_TP4_REPS:-2}
ARMS=${ARMS:-"base headoff vnni"}
SMOKE_ARMS=${SMOKE_ARMS:-"base base2 headoff vnni vnni2"}
MODEL2=ingested-qwen-3-30b-a3b-instruct-2507-tp2
MODEL4=ingested-qwen-3-30b-a3b-instruct-2507-tp4
HPFILE=/dev/hugepages/amx-vnnik6
BILL_UID=1062305141
mkdir -p "$RES/rt" "$RES/smoke" "$TRES" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
# the child trace.sh must apply the same 6-h takeover rule: bash keeps the export attribute
# when rinzler_takeover_if_idle reassigns the variable
export GUARD_TAKEOVER_LAST
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
arm_bin() { case $1 in base) echo "$RT_BASE" ;; headoff) echo "$RT_HEADOFF" ;; vnni) echo "$RT_VNNI" ;; *) return 1 ;; esac; }
arm_tip() { case $1 in base) echo "${TIP_BASE:-?}" ;; headoff) echo "${TIP_HEADOFF:-?}" ;; vnni) echo "${TIP_VNNI:-?}" ;; *) echo "?" ;; esac; }
model_for_tp() { case $1 in 2) echo "$MODEL2" ;; 4) echo "$MODEL4" ;; *) return 1 ;; esac; }

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
    # the nightly leaves its rinzler@N units up; when they are the only blocker, stop them once
    # idle (lib-guard.sh recipe) instead of waiting for a person to do it
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
  [ -n "${INST_LOCK_FD:-}" ] && exec {INST_LOCK_FD}>&-
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
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
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
  local arm base_arm bin rc out stops
  for arm in $SMOKE_ARMS; do
    base_arm=${arm%2}; bin=$(arm_bin "$base_arm") || { echo "$(ts) smoke: unknown arm $arm"; continue; }
    out=$RES/smoke/$arm; stops=0
    while :; do
      [ -s "$out.tokens" ] && { echo "$(ts) smoke $arm already done"; break; }
      wait_clear; take_guard
      status "phase 2: smoke $arm"
      echo "### smoke arm=$arm bin=$bin tip=$(arm_tip "$base_arm") model=$MODEL2 prompt=1024 len=128 users=1 temperature=0 pay-for-determinism $(ts) $(machine_line)" >>"$RES/smoke/smoke.txt"
      rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
      (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=info \
          timeout -k 60 900 "$bin" stream-generate-text -m "$MODEL2" $(placement 2) --hugepage_file "$HPFILE" -o \
          --prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
      rc=$?
      stop_watcher; campaign_guard_release; remove_our_slice_files
      echo "smoke $arm rc=$rc $(grep -E 'Version:|average tok/s|Parsing the prompt took' "$out.log" | cut -c1-200 | tr '\n' ' ' | cut -c1-400)" >>"$RES/smoke/smoke.txt"
      if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then
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
  local tp=$1 prompt=$2 arm=$3 rep=$4 model rlog attempt stops=0 rc res bin
  model=$(model_for_tp "$tp") || return 1
  bin=$(arm_bin "$arm") || { echo "$(ts) run_rt: unknown arm $arm"; return 1; }
  rlog=$RES/rt/tp${tp}__p${prompt}__${arm}__rep${rep}.log
  if grep -q "average tok/s" "$rlog" 2>/dev/null; then echo "$(ts) runtron tp$tp p$prompt $arm rep$rep already done"; return 0; fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    attempt=$((attempt + 1))
    wait_clear; take_guard
    status "phase 3: runtron tp$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt"
    echo "### runtron tp=$tp prompt=$prompt arm=$arm rep=$rep attempt=$attempt bin=$bin tip=$(arm_tip "$arm") model=$model len=256 users=8 $(ts) $(machine_line)" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 1500 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o \
        --prompt-length "$prompt" -l 256 -u 8) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then
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

[ "${VNNIK6_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock   # one campaign.sh instance per NAME (local disk, held for the life of the script)
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ RT_REPS=$RT_REPS TP4_REPS=$TP4_REPS MID_REPS=$MID_REPS LONG_REPS=$LONG_REPS LONG_TP4_REPS=$LONG_TP4_REPS ARMS=[$ARMS] SMOKE_ARMS=[$SMOKE_ARMS] RUN_TRACES=$RUN_TRACES ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"

# phase 1: the build markers (build.sh writes ok | build-failed rc=N | worktree-failed | checkout-failed | no-qwen30b)
arm_marker() { case $1 in base) echo "$RES/build-main0916.done" ;; headoff) echo "$RES/build-headoff0916.done" ;; *) echo "" ;; esac; }
status "phase 1: waiting for the build markers of the arms [$ARMS]"
waited=0
while :; do
  all_ok=1
  for arm in $ARMS; do
    mf=$(arm_marker "$arm"); [ -n "$mf" ] || continue
    m=$(cat "$mf" 2>/dev/null || true)
    case $m in
      ok) ;;
      build-failed*|worktree-failed|checkout-failed|no-qwen30b|cache-mismatch*) echo "$(ts) build marker of $arm says '$m'; campaign ends"; finish "build:$arm:$m"; exit 1 ;;
      *) all_ok=0 ;;
    esac
  done
  [ $all_ok = 1 ] && break
  waited=$((waited + 30)); [ $waited -ge 14400 ] && { echo "$(ts) build markers still missing after 4 h; campaign ends"; finish "build:no-marker"; exit 1; }
  sleep 30
done
for arm in $ARMS; do
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; finish "unknown-arm-$arm"; exit 1; }
  [ -x "$bin" ] || { echo "$(ts) $bin missing"; finish "no-$arm-binary"; exit 1; }
done
TIP_BASE=$(git -C /var/tmp/jhan/tron-main0916 rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_HEADOFF=$(git -C /var/tmp/jhan/tron-headoff0916 rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_VNNI=$(git -C /var/tmp/jhan/tron-vnnik5 rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$(ts) tips: base=$TIP_BASE headoff=$TIP_HEADOFF vnni=$TIP_VNNI; $(machine_line)"
cat "$RES/build-main0916.txt" "$RES/build-headoff0916.txt" 2>/dev/null
{
  echo "# $NAME runtron results: qwen-3-30b-a3b (kv_mul 8), 8 users, 256 generated; host $(hostname); started $(ts)"
  echo "# arms: base = runtron.main0916 ($TIP_BASE, main, TRON_AMX_DISPATCH=ON); headoff = runtron.headoff0916 ($TIP_HEADOFF, PR head, TRON_K_VNNI off); vnni = runtron.vnnik5 ($TIP_VNNI, PR head code, TRON_K_VNNI=ON)"
  echo "# USE_HW_ATTN=0; env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE"
  echo "# placement tp2: $(placement 2)"
  echo "# placement tp4: $(placement 4)"
  for arm in $ARMS; do b=$(arm_bin "$arm"); sha256sum "$b"; ( cd "$(dirname "$b")" && echo "version $(basename "$b"): $("./$(basename "$b")" --version 2>&1 | head -1)" ); done
} >>"$RES/rt-results.txt"

# phase 2: smoke
run_smoke

# phase 3a/3b: the reported cell (prompt 1024) at tp2 and tp4
rt_fail=0; consec=0
rt() {  # run_rt with a cap: 3 consecutive failed runs end the current phase (a systematic failure must not eat the
        # window one timeout at a time); in the primary cell (tp2 prompt 1024) they end the campaign
  if run_rt "$@"; then consec=0; return 0; fi
  rt_fail=$((rt_fail + 1)); consec=$((consec + 1))
  [ $consec -lt 3 ] && return 0
  if [ "$1" = 2 ] && [ "$2" = 1024 ]; then echo "$(ts) 3 consecutive failed runs in the primary cell; campaign ends"; finish aborted-3-consecutive-failures; exit 1; fi
  echo "$(ts) 3 consecutive failed runs; the rest of the tp$1 prompt-$2 phase is skipped"; return 1
}
for rep in $(seq 1 "$RT_REPS"); do for arm in $ARMS; do rt 2 1024 "$arm" "$rep" || break 2; done; done; consec=0
echo "$(ts) tp2 prompt-1024 cells done, failed runs: $rt_fail"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
for rep in $(seq 1 "$TP4_REPS"); do for arm in $ARMS; do rt 4 1024 "$arm" "$rep" || break 2; done; done; consec=0
echo "$(ts) tp4 prompt-1024 cells done, failed runs total: $rt_fail"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true

# phase 3c: traces (Save K span and attention-worker time per pass), prompt 1024, tp2 + tp4
if [ "$RUN_TRACES" = 1 ]; then
  status "phase 3c: traces"
  wait_clear
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  ARMS="$ARMS" TPS="2 4" RES="$TRES" LOG="$EXEC/logs/${NAME/vnnik6-/vnnik6-trace-}.log" MARKER="$EXEC/logs/${NAME/vnnik6-/vnnik6-trace-}.done" \
    ARM_base_BIN="$RT_BASE" ARM_headoff_BIN="$RT_HEADOFF" ARM_vnni_BIN="$RT_VNNI" \
    bash "$C/trace.sh"
  stop_watcher; remove_our_slice_files
  t=$(cat "$TRES/takeover.last" 2>/dev/null); [ -n "$t" ] && [ "$t" -gt "$GUARD_TAKEOVER_LAST" ] 2>/dev/null && GUARD_TAKEOVER_LAST=$t
  echo "$(ts) traces: $(cat "$EXEC/logs/${NAME/vnnik6-/vnnik6-trace-}.done" 2>/dev/null) $([ -e "$RES/rt.STOPPED" ] && echo "(a trace run was stopped: $(cat "$RES/rt.STOPPED"))")"
fi

# phase 3d/3e: the prompt-length trend
for rep in $(seq 1 "$MID_REPS"); do for arm in $ARMS; do rt 2 2048 "$arm" "$rep" || break 2; done; done; consec=0
echo "$(ts) tp2 prompt-2048 cells done, failed runs total: $rt_fail"
for rep in $(seq 1 "$LONG_REPS"); do for arm in $ARMS; do rt 2 8192 "$arm" "$rep" || break 2; done; done; consec=0
echo "$(ts) tp2 prompt-8192 cells done, failed runs total: $rt_fail"
for rep in $(seq 1 "$LONG_TP4_REPS"); do for arm in $ARMS; do rt 4 8192 "$arm" "$rep" || break 2; done; done; consec=0
echo "$(ts) tp4 prompt-8192 cells done, failed runs total: $rt_fail"

status "phase 4: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
finish "$([ $rt_fail -eq 0 ] && echo ok || echo "ok-with-$rt_fail-failed-runs")"
