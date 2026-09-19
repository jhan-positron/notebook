#!/usr/bin/env bash
# wedperf-20260916: the nightly CI's perf models, base (main just before PR #3879) vs target
# (PR #4424 head with AMX dispatch and the VNNI K layout on), on OUR half of delphi-3bda.
# Fork of exec/vnnik6-20260916/campaign.sh (same guards, same run recipe); cells replaced.
#
# Words used here: tron = the inference program under test; runtron = its command-line tool;
# the nightly = the System CI workflow of positron-ai/systems_test that runs every night on
# this machine; CI perf model = one entry of scripts/perf.py `configs` there (model slug,
# tensor-parallel width tp2/tp4, user count); TPS = generated tokens per second per user in
# decode; TTFT = time to first token = runtron's "Parsing the prompt took" time (max over the
# users of a run); smoke = 1-user greedy run whose token ids are saved; CPU attention =
# USE_HW_ATTN=0 (the attention runs on the host cores: the only path PR #3879 and PR #4424
# change); FPGA attention = USE_HW_ATTN unset = the nightly's default for ingested models
# (hand-written plugins run CPU attention by default, h/tron/models/hw_attn_config.hpp).
#
# Arms:
#   base   = runtron.pre3879 (main eb2de0265a = parent 1 of the PR #3879 merge 3fd5edaa66;
#            no AMX code; production-tagged models included)
#   target = runtron.pr4424  (PR #4424 head ff680c8020, TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON;
#            production-tagged models included)
# Cells (the 12 CI perf configs at their CI user counts; prompt 1024, 256 generated tokens):
#   block A  CPU attention, every cell, REPS repetitions (arms interleave inside a repetition)
#   block B  FPGA attention (USE_HW_ATTN unset), the 4 ingested cells only (the hand-written
#            plugins already ran their default mode in block A), REPS_B repetitions
#   smoke    before block A: every model slug once per arm, 1 user, prompt 1024, 128 tokens,
#            temperature 0, pay-for-determinism; token ids compared base vs target
# Deviations from the nightly's perf test (scripts/perf.py): runtron instead of rinzler + the
# CI client; fixed prompt length 1024 and 256 generated tokens for every cell (CI: sharegpt
# prompts, 1024 prompt / 1536 generated; the 3b cell uses 800 shared + 200 prompt / 845
# generated); one engine on our half instead of 2-4 engines behind the proxy.
# Every run: env -u SYSTEM_CONFIG, campaign guard (lease + other persons + blackout + flock +
# no runtron of ours + no serving), a 10-s watcher that kills OUR binaries if the lease turns
# busy, pre-CI hold 01:40-03:45 UTC, deadline = the next DEADLINE_HHMM UTC after the start (a
# fixed instant, checked before every run and inside every wait loop: no new run after it, and
# a campaign that waits through the deadline ends instead of resuming after the nightly),
# idle-serving takeover through lib-guard.sh rinzler_takeover_if_idle. The rt runs pass
# --dont-stop (the CI client's ignore_eos) so every user generates the full 256 tokens; the
# smokes do not (a stop at the same token in both binaries is a valid comparison).
# Never edit this file while a campaign runs it (bash re-reads a running script from its byte
# offset after every forked command).
# Outputs: exec/results/wedperf-20260916/{smoke/, rt/, rt-results.txt, summary.json, summary.md};
# log exec/logs/wedperf-20260916.log; status .status; marker .done
# (ok | ok-with-N-failed-runs | build:... | no-...-binary | deadline | aborted...).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/wedperf-20260916
NAME=${NAME:-wedperf-20260916}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
RT_BASE=/var/tmp/jhan/tron-pre3879/gen/runtron.pre3879
RT_TARGET=/var/tmp/jhan/tron-pr4424/gen/runtron.pr4424
OUR_RT_RE='^/var/tmp/jhan/tron-(pre3879|pr4424)/gen/runtron[.](pre3879|pr4424) '
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
REPS=${REPS:-3}; REPS_B=${REPS_B:-2}
ARMS=${ARMS:-"base target"}
DO_SMOKE=${DO_SMOKE:-1}; DO_A=${DO_A:-1}; DO_B=${DO_B:-1}
DEADLINE_HHMM=${DEADLINE_HHMM:-130}      # UTC, HHMM digits only: 130 or 0130 = 01:30, 2300 = 23:00 (validated below status())
HPFILE=/dev/hugepages/amx-wedperf
BILL_UID=1062305141
# cell table: key|model slug|tp|users   (scripts/perf.py at systems_test 6b20db0, 2026-09-15)
CELLS_ALL="l3b-tp2-32u|llama-3.2-3b-instruct-fast-tp2|2|32
l8b-tp2-8u|llama-3.1-8b-instruct-good-tp2|2|8
l70b-tp2-8u|llama-3.3-70b-instruct-good-tp2|2|8
l70b-tp2-4u|llama-3.3-70b-instruct-good-tp2|2|4
l70b-tp4-4u|llama-3.3-70b-instruct-good-tp4|4|4
mixtral-tp2-8u|mixtral-8x7b-instruct-v0.1-tp2|2|8
q25-32b-tp2-8u|qwen-2.5-32b-it-fast-tp2|2|8
q3-4b-tp2-8u|ingested-qwen-3-4b-instruct-2507-tp2|2|8
q3-4b-tp4-8u|ingested-qwen-3-4b-instruct-2507-tp4|4|8
g2-9b-tp2-8u|gemma-2-9b-it-fast-tp2|2|8
gptoss-tp4-8u|ingested-gpt-oss-120b-tp4|4|8
g4-31b-tp2-8u|ingested-gemma-4-31b-it-tp2|2|8"
CELLS_A=${CELLS_A:-"l3b-tp2-32u l8b-tp2-8u l70b-tp2-8u l70b-tp2-4u l70b-tp4-4u mixtral-tp2-8u q25-32b-tp2-8u q3-4b-tp2-8u q3-4b-tp4-8u g2-9b-tp2-8u gptoss-tp4-8u g4-31b-tp2-8u"}
CELLS_B=${CELLS_B:-"q3-4b-tp2-8u q3-4b-tp4-8u gptoss-tp4-8u g4-31b-tp2-8u"}
SMOKE_CELLS=${SMOKE_CELLS:-"l3b-tp2-32u l8b-tp2-8u l70b-tp2-8u l70b-tp4-4u mixtral-tp2-8u q25-32b-tp2-8u q3-4b-tp2-8u q3-4b-tp4-8u g2-9b-tp2-8u gptoss-tp4-8u g4-31b-tp2-8u"}
mkdir -p "$RES/rt" "$RES/smoke" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_TAKEOVER_LAST
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
case $DEADLINE_HHMM in ''|*[!0-9]*) status "rejected: DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
[ "$DEADLINE_HHMM" -le 2359 ] && [ $((DEADLINE_HHMM % 100)) -le 59 ] || { status "rejected: DEADLINE_HHMM=$DEADLINE_HHMM is not a clock time"; exit 1; }
# the deadline as a fixed instant: the next DEADLINE_HHMM UTC after now (today if still ahead, else tomorrow)
DEADLINE_EPOCH=$(date -u -d "today $(printf '%02d:%02d' $((DEADLINE_HHMM / 100)) $((DEADLINE_HHMM % 100)))" +%s)
[ "$DEADLINE_EPOCH" -gt "$(date -u +%s)" ] || DEADLINE_EPOCH=$((DEADLINE_EPOCH + 86400))
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
arm_bin() { case $1 in base) echo "$RT_BASE" ;; target) echo "$RT_TARGET" ;; *) return 1 ;; esac; }
arm_tip() { case $1 in base) echo "${TIP_BASE:-?}" ;; target) echo "${TIP_TARGET:-?}" ;; *) echo "?" ;; esac; }
cell_field() {  # $1 key $2 field (2 model, 3 tp, 4 users)
  local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1
  cut -d'|' -f"$2" <<<"$line"
}

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  return 1
}
wait_clear() {  # returns 2 when the deadline passes while waiting
  local why waited=0
  while why=$(blocked); do
    past_deadline && return 2
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    [ "$why" = "rinzler@N unit active" ] && rinzler_takeover_if_idle && continue
    sleep 120
  done
  return 0
}
take_guard() {  # returns 2 when the deadline passes while waiting
  local waited=0
  until campaign_guard_acquire; do
    past_deadline && return 2
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; pgrep -a -x 'runtron(\.[a-z0-9]+)?' 2>/dev/null | cut -c1-160 | sed 's/^/  runtron seen: /'; }
    sleep 60; wait_clear || return 2
  done
  return 0
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
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-wedperf*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
finish() {
  stop_watcher
  if [ "${1#aborted}" != "$1" ]; then
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

# one runtron invocation; $1 key $2 attn (cpu|fpga) $3 arm $4 kind (smoke|rt) $5 rep
run_one() {
  local key=$1 attn=$2 arm=$3 kind=$4 rep=$5 model tp users bin out rlog attempt stops=0 rc res hwenv args tmo hdr
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  tp=$(cell_field "$key" 3); users=$(cell_field "$key" 4)
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; return 1; }
  if [ "$attn" = fpga ]; then hwenv="-u USE_HW_ATTN"; else hwenv="USE_HW_ATTN=0"; fi
  if [ "$kind" = smoke ]; then
    out=$RES/smoke/${key}__${attn}__${arm}
    [ -s "$out.tokens" ] && { echo "$(ts) smoke $key $attn $arm already done"; return 0; }
    args="--prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file $out.tokens"; tmo=1500
    rlog=$out.log
  else
    rlog=$RES/rt/${key}__${attn}__${arm}__rep${rep}.log
    grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) runtron $key $attn $arm rep$rep already done"; return 0; }
    args="--prompt-length 1024 -l 256 -u $users --dont-stop"; tmo=1800
  fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    past_deadline && { echo "$(ts) deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) reached before $kind $key $attn $arm rep$rep"; return 2; }
    attempt=$((attempt + 1))
    wait_clear || { echo "$(ts) deadline reached while waiting before $kind $key $attn $arm rep$rep"; return 2; }
    take_guard || { echo "$(ts) deadline reached while waiting for the guard before $kind $key $attn $arm rep$rep"; return 2; }
    status "$kind $key attn=$attn arm=$arm rep=$rep attempt=$attempt"
    hdr="### runtron kind=$kind cell=$key model=$model tp=$tp users=$([ "$kind" = smoke ] && echo 1 || echo "$users") attn=$attn prompt=1024 len=$([ "$kind" = smoke ] && echo 128 || echo 256) arm=$arm rep=$rep attempt=$attempt bin=$bin tip=$(arm_tip "$arm") $(ts) $(machine_line)"
    echo "$hdr" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 "$tmo" "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o $args) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null | cut -c1-240)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog.attempt$attempt)" >>"$RES/rt-results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP after 3 stops" >>"$RES/rt-results.txt"; return 1; }
      [ "$kind" = smoke ] && rm -f "$out.tokens"   # a stopped smoke may have left a partial token file
      sleep 120; continue
    fi
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
      { echo "RUN-FAILED rc=$rc (full output: $rlog.attempt$attempt)"; echo "$res"; grep -i -m3 -E "error|abort|assert|exception|terminate|not found|unknown model" "$rlog.attempt$attempt" | cut -c1-240; } >>"$RES/rt-results.txt"
      return 1
    fi
    cp "$rlog.attempt$attempt" "$rlog"
    echo "$res" >>"$RES/rt-results.txt"
    if [ "$kind" = smoke ]; then
      echo "smoke $key $attn $arm rc=$rc $(grep -E 'Version:|average tok/s|Parsing the prompt took' "$rlog" | cut -c1-200 | tr '\n' ' ' | cut -c1-400)" >>"$RES/smoke/smoke.txt"
      [ -s "$out.tokens" ] || { echo "SMOKE-NO-TOKENS $key $attn $arm" >>"$RES/smoke/smoke.txt"; return 1; }
    fi
    return 0
  done
}

[ "${WEDPERF_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock   # one campaign.sh instance per NAME (local disk, held for the life of the script)
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ REPS=$REPS REPS_B=$REPS_B ARMS=[$ARMS] DO_SMOKE=$DO_SMOKE DO_A=$DO_A DO_B=$DO_B deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) CELLS_A=[$CELLS_A] CELLS_B=[$CELLS_B] ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"

# phase 1: the build markers (build.sh writes ok | build-failed rc=N | worktree-failed | checkout-failed | missing-models... | cache-mismatch...)
arm_marker() { case $1 in base) echo "$RES/build-pre3879.done" ;; target) echo "$RES/build-pr4424.done" ;; *) echo "" ;; esac; }
status "phase 1: waiting for the build markers of the arms [$ARMS]"
waited=0
while :; do
  all_ok=1
  for arm in $ARMS; do
    mf=$(arm_marker "$arm"); [ -n "$mf" ] || continue
    m=$(cat "$mf" 2>/dev/null || true)
    case $m in
      ok) ;;
      build-failed*|worktree-failed|checkout-failed|missing-models*|cache-mismatch*) echo "$(ts) build marker of $arm says '$m'; campaign ends"; finish "build:$arm:$m"; exit 1 ;;
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
TIP_BASE=$(git -C /var/tmp/jhan/tron-pre3879 rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_TARGET=$(git -C /var/tmp/jhan/tron-pr4424 rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$(ts) tips: base=$TIP_BASE target=$TIP_TARGET; $(machine_line)"
cat "$RES/build-pre3879.txt" "$RES/build-pr4424.txt" 2>/dev/null
{
  echo "# $NAME runtron results: the nightly CI perf models, base vs target; host $(hostname); started $(ts)"
  echo "# arms: base = runtron.pre3879 ($TIP_BASE, main before PR #3879, no AMX code); target = runtron.pr4424 ($TIP_TARGET, PR #4424 head, TRON_AMX_DISPATCH=ON TRON_K_VNNI=ON)"
  echo "# attn=cpu: USE_HW_ATTN=0; attn=fpga: USE_HW_ATTN unset (the nightly's default for ingested models); env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE; rt runs pass --dont-stop (= the CI client's ignore_eos: every user generates the full 256 tokens); smokes do not"
  echo "# cells: key|model|tp|users:"; sed 's/^/#   /' <<<"$CELLS_ALL"
  echo "# placement tp2: $(placement 2)"
  echo "# placement tp4: $(placement 4)"
  for arm in $ARMS; do b=$(arm_bin "$arm"); sha256sum "$b"; ( cd "$(dirname "$b")" && echo "version $(basename "$b"): $("./$(basename "$b")" --version 2>&1 | head -1)" ); done
} >>"$RES/rt-results.txt"

fails=0; consec=0
declare -A CELL_FAILS=()
# a run with a cap: a (cell, attn, arm) that failed twice is skipped afterwards (a model that
# does not load in one binary must not cost a timeout per repetition); 5 consecutive failed
# runs end the campaign (a systematic failure must not eat the window one timeout at a time)
rt() {  # $1 key $2 attn $3 arm $4 kind $5 rep
  local k="$1|$2|$3|$4" rc
  [ "${CELL_FAILS[$k]:-0}" -ge 2 ] && { echo "$(ts) skip $4 $1 $2 $3 rep$5: failed twice before"; return 0; }
  run_one "$1" "$2" "$3" "$4" "$5"; rc=$?
  [ $rc -eq 2 ] && return 2
  if [ $rc -eq 0 ]; then consec=0; return 0; fi
  fails=$((fails + 1)); consec=$((consec + 1)); CELL_FAILS[$k]=$(( ${CELL_FAILS[$k]:-0} + 1 ))
  [ $consec -ge 5 ] && { echo "$(ts) 5 consecutive failed runs; campaign ends"; return 3; }
  return 1
}
end_check() {  # $1 = rt's return code; ends the campaign on deadline or the consecutive-failure cap
  case $1 in
    2) finish deadline; exit 0 ;;
    3) finish aborted-5-consecutive-failures; exit 1 ;;
  esac
}

# phase 2: smokes (CPU attention), every model slug once per arm, token ids saved
if [ "$DO_SMOKE" = 1 ]; then
  for key in $SMOKE_CELLS; do for arm in $ARMS; do rt "$key" cpu "$arm" smoke 1; end_check $?; done; done
  python3 "$C/compare_tokens.py" "$RES/smoke" >"$RES/smoke/compare.txt" 2>&1 || true
  cat "$RES/smoke/compare.txt"
  echo "$(ts) smokes done, failed runs so far: $fails"
fi

# phase 3: block A, CPU attention, REPS repetitions; arms interleave inside a repetition
if [ "$DO_A" = 1 ]; then
  for rep in $(seq 1 "$REPS"); do
    for key in $CELLS_A; do for arm in $ARMS; do rt "$key" cpu "$arm" rt "$rep"; end_check $?; done; done
    echo "$(ts) block A repetition $rep done, failed runs so far: $fails"
    python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  done
fi

# phase 4: block B, FPGA attention (USE_HW_ATTN unset), the ingested cells, REPS_B repetitions
if [ "$DO_B" = 1 ]; then
  for rep in $(seq 1 "$REPS_B"); do
    for key in $CELLS_B; do for arm in $ARMS; do rt "$key" fpga "$arm" rt "$rep"; end_check $?; done; done
    echo "$(ts) block B repetition $rep done, failed runs so far: $fails"
    python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  done
fi

status "phase 5: summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
