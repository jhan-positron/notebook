#!/usr/bin/env bash
# q4b-rt8u-20260922: qwen3-4b tp2 with 8 users on ONE engine (our half of delphi-3bda), prompt 1024 / 2048 / 4096 / 8192,
# attention on the FPGA against attention on the CPU, AVX build against canonical-AMX build, interleaved inside every
# repetition. Answers jhan's question of 2026-09-22 ("was 4k or 8k prompt length + 8 users per engine tested?"): with FPGA
# attention it was not. Two-user cells at 4096 and 8192 are included as the clean reference (the CI layout's load per engine).
# Fork of exec/wedperf-20260916/campaign.sh (guards, run recipe, watcher, takeover kept; see campaign.sh.wedperf-orig).
#
# Words used here: tron = the inference program under test; runtron = its command-line tool; TPS = generated tokens per
# second per user in decode; TTFT = time to first token = runtron's "Parsing the prompt took" time (max over the users);
# CPU attention = USE_HW_ATTN=0; FPGA attention = USE_HW_ATTN unset (the nightly's default for ingested models);
# HBM exhaustion = tron's warning "HBM bypass space exhausted; caller degrades to SW attention" (the card's K/V space is
# full and that shard's attention runs on the CPU); counted per run into rt-results.txt (line HBM-EXHAUSTION).
#
# Arms:  base  = runtron.pre3879  (main eb2de0265a, before PR #3879: no AMX code, AVX attention kernel)
#        canon = runtron.main0916 (main c7844ca2ce, after the PR #3879 merge: canonical AMX kernel, row-major K)
# Cells: key|model|tp|users|prompt (256 generated tokens, --dont-stop). Order inside a repetition: cell, then attention
#        mode cpu/fpga, then arm, so the four runs of one cell sit within minutes of each other.
# Every run: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE, campaign guard (lease + other persons + blackout + flock + no runtron
# of ours + no serving), a 10-s watcher that kills OUR binaries if the lease turns busy, pre-CI hold 01:40-03:45 UTC,
# deadline = the next DEADLINE_HHMM UTC after the start, idle-serving takeover through lib-guard.sh rinzler_takeover_if_idle.
# START_NOT_BEFORE (ISO UTC): the script sleeps until then before touching the machine (the whole-machine q4b-fpga launch
# of 2026-09-22 runs 13:20 to about 17:10 UTC and holds the campaign flock; this campaign waits for it).
# End: production serving is brought back up through platformd when this script had taken it down (dut.sh serving-up of
# the q4b-fpga campaign, best effort).
# Never edit this file while a campaign runs it (bash re-reads a running script from its byte offset after every forked command).
# Outputs: exec/results/q4b-rt8u-20260922/{rt/, rt-results.txt, summary.json, summary.md}; log exec/logs/q4b-rt8u-20260922.log;
# status .status; marker .done (ok | ok-with-N-failed-runs | no-...-binary | deadline | aborted...).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/q4b-rt8u-20260922
NAME=${NAME:-q4b-rt8u-20260922}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
RT_BASE=/var/tmp/jhan/tron-pre3879/gen/runtron.pre3879
RT_CANON=/var/tmp/jhan/tron-main0916/gen/runtron.main0916
OUR_RT_RE='^/var/tmp/jhan/tron-(pre3879|main0916)/gen/runtron[.](pre3879|main0916) '
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
REPS=${REPS:-3}
ARMS=${ARMS:-"base canon"}
ATTNS=${ATTNS:-"cpu fpga"}
DEADLINE_HHMM=${DEADLINE_HHMM:-130}      # UTC, HHMM digits only
START_NOT_BEFORE=${START_NOT_BEFORE:-}   # ISO UTC; empty = start at once
HPFILE=/dev/hugepages/amx-rt8u
BILL_UID=1062305141
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
# cell table: key|model|tp|users|prompt
CELLS_ALL="q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024
q3-4b-tp2-8u-p2048|ingested-qwen-3-4b-instruct-2507-tp2|2|8|2048
q3-4b-tp2-8u-p4096|ingested-qwen-3-4b-instruct-2507-tp2|2|8|4096
q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192
q3-4b-tp2-2u-p4096|ingested-qwen-3-4b-instruct-2507-tp2|2|2|4096
q3-4b-tp2-2u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|2|8192"
CELLS=${CELLS:-"q3-4b-tp2-8u-p1024 q3-4b-tp2-8u-p2048 q3-4b-tp2-8u-p4096 q3-4b-tp2-8u-p8192 q3-4b-tp2-2u-p4096 q3-4b-tp2-2u-p8192"}
mkdir -p "$RES/rt" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_TAKEOVER_LAST
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
case $DEADLINE_HHMM in ''|*[!0-9]*) status "rejected: DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
[ "$DEADLINE_HHMM" -le 2359 ] && [ $((DEADLINE_HHMM % 100)) -le 59 ] || { status "rejected: DEADLINE_HHMM=$DEADLINE_HHMM is not a clock time"; exit 1; }
DEADLINE_EPOCH=$(date -u -d "today $(printf '%02d:%02d' $((DEADLINE_HHMM / 100)) $((DEADLINE_HHMM % 100)))" +%s)
[ "$DEADLINE_EPOCH" -gt "$(date -u +%s)" ] || DEADLINE_EPOCH=$((DEADLINE_EPOCH + 86400))
if [ -n "$START_NOT_BEFORE" ]; then
  SNB_EPOCH=$(date -u -d "$START_NOT_BEFORE" +%s) || { status "rejected: START_NOT_BEFORE='$START_NOT_BEFORE' is not a date"; exit 1; }
  [ "$SNB_EPOCH" -lt "$DEADLINE_EPOCH" ] || { status "rejected: START_NOT_BEFORE is not before the deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ)"; exit 1; }
fi
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    *) return 1 ;;
  esac
}
arm_bin() { case $1 in base) echo "$RT_BASE" ;; canon) echo "$RT_CANON" ;; *) return 1 ;; esac; }
arm_tip() { case $1 in base) echo "${TIP_BASE:-?}" ;; canon) echo "${TIP_CANON:-?}" ;; *) echo "?" ;; esac; }
cell_field() {  # $1 key $2 field (2 model, 3 tp, 4 users, 5 prompt)
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
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-rt8u*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
serving_back_up() {  # best effort: production engines up again when this script took them down (the takeover latch is set)
  [ "${GUARD_TAKEOVER_LAST:-0}" != 0 ] || { echo "$(ts) serving: this script did not stop production, nothing to bring up"; return 0; }
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, leaving serving alone"; return 0; fi
  if rinzler_active; then echo "$(ts) serving: rinzler units already active"; return 0; fi
  [ -x "$SERVING_UP_HELPER" ] || { echo "$(ts) serving: helper $SERVING_UP_HELPER missing"; return 0; }
  echo "$(ts) serving: bringing production up through platformd (dut.sh serving-up)"
  timeout 900 bash "$SERVING_UP_HELPER" serving-up || echo "$(ts) serving: serving-up returned rc=$? (jhan: check platformd)"
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
  serving_back_up
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}

# one runtron invocation; $1 key $2 attn (cpu|fpga) $3 arm $4 rep
run_one() {
  local key=$1 attn=$2 arm=$3 rep=$4 model tp users prompt bin rlog attempt stops=0 rc res hwenv args tmo hdr lose exh
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  tp=$(cell_field "$key" 3); users=$(cell_field "$key" 4); prompt=$(cell_field "$key" 5)
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; return 1; }
  if [ "$attn" = fpga ]; then hwenv="-u USE_HW_ATTN"; else hwenv="USE_HW_ATTN=0"; fi
  rlog=$RES/rt/${key}__${attn}__${arm}__rep${rep}.log
  grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) runtron $key $attn $arm rep$rep already done"; return 0; }
  args="--prompt-length $prompt -l 256 -u $users --dont-stop"; tmo=2400
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    past_deadline && { echo "$(ts) deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) reached before rt $key $attn $arm rep$rep"; return 2; }
    attempt=$((attempt + 1))
    wait_clear || { echo "$(ts) deadline reached while waiting before rt $key $attn $arm rep$rep"; return 2; }
    take_guard || { echo "$(ts) deadline reached while waiting for the guard before rt $key $attn $arm rep$rep"; return 2; }
    status "rt $key attn=$attn arm=$arm rep=$rep attempt=$attempt"
    hdr="### runtron kind=rt cell=$key model=$model tp=$tp users=$users attn=$attn prompt=$prompt len=256 arm=$arm rep=$rep attempt=$attempt bin=$bin tip=$(arm_tip "$arm") $(ts) $(machine_line)"
    echo "$hdr" >>"$RES/rt-results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 "$tmo" "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o $args) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null | cut -c1-240)
    lose=$(grep -c "lose HW attention" "$rlog.attempt$attempt" 2>/dev/null || true); exh=$(grep -c "HBM bypass space exhausted" "$rlog.attempt$attempt" 2>/dev/null || true)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog.attempt$attempt)" >>"$RES/rt-results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP after 3 stops" >>"$RES/rt-results.txt"; return 1; }
      sleep 120; continue
    fi
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
      { echo "RUN-FAILED rc=$rc (full output: $rlog.attempt$attempt)"; echo "$res"; grep -i -m3 -E "error|abort|assert|exception|terminate|not found|unknown model" "$rlog.attempt$attempt" | cut -c1-240; } >>"$RES/rt-results.txt"
      return 1
    fi
    cp "$rlog.attempt$attempt" "$rlog"
    { echo "$res"; echo "HBM-EXHAUSTION lose=${lose:-0} exhausted=${exh:-0} (warning lines in this run's log: 'lose HW attention' = a 1024-token shard scored on the CPU instead of the card)"; } >>"$RES/rt-results.txt"
    return 0
  done
}

[ "${RT8U_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ REPS=$REPS ARMS=[$ARMS] ATTNS=[$ATTNS] CELLS=[$CELLS] START_NOT_BEFORE=${START_NOT_BEFORE:-none} deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
for arm in $ARMS; do
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; finish "unknown-arm-$arm"; exit 1; }
  [ -x "$bin" ] || { echo "$(ts) $bin missing"; finish "no-$arm-binary"; exit 1; }
done
if [ -n "$START_NOT_BEFORE" ]; then
  while [ "$(date -u +%s)" -lt "$SNB_EPOCH" ]; do
    left=$(( SNB_EPOCH - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800
    status "waiting: START_NOT_BEFORE $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"
  done
  status "START_NOT_BEFORE passed"
fi
TIP_BASE=$(git -C /var/tmp/jhan/tron-pre3879 rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_CANON=$(git -C /var/tmp/jhan/tron-main0916 rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$(ts) tips: base=$TIP_BASE canon=$TIP_CANON; $(machine_line)"
{
  echo "# $NAME runtron results: qwen3-4b tp2 on one engine (our half), 8 users (and 2 users) x prompt 1024..8192, CPU vs FPGA attention, AVX vs canonical-AMX build; host $(hostname); started $(ts)"
  echo "# arms: base = runtron.pre3879 ($TIP_BASE, main before PR #3879, no AMX code); canon = runtron.main0916 ($TIP_CANON, main after the PR #3879 merge, canonical AMX)"
  echo "# attn=cpu: USE_HW_ATTN=0; attn=fpga: USE_HW_ATTN unset; env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE; --dont-stop (every user generates the full 256 tokens)"
  echo "# HBM-EXHAUSTION line per run: counts of tron's 'lose HW attention' and 'HBM bypass space exhausted' warnings (card K/V space full -> that shard's attention on the CPU)"
  echo "# cells: key|model|tp|users|prompt:"; sed 's/^/#   /' <<<"$CELLS_ALL"
  echo "# placement tp2: $(placement 2)"
  for arm in $ARMS; do b=$(arm_bin "$arm"); sha256sum "$b"; ( cd "$(dirname "$b")" && echo "version $(basename "$b"): $("./$(basename "$b")" --version 2>&1 | head -1)" ); done
} >>"$RES/rt-results.txt"

fails=0; consec=0
declare -A CELL_FAILS=()
rt() {  # $1 key $2 attn $3 arm $4 rep
  local k="$1|$2|$3" rc
  [ "${CELL_FAILS[$k]:-0}" -ge 2 ] && { echo "$(ts) skip rt $1 $2 $3 rep$4: failed twice before"; return 0; }
  run_one "$1" "$2" "$3" "$4"; rc=$?
  [ $rc -eq 2 ] && return 2
  if [ $rc -eq 0 ]; then consec=0; return 0; fi
  fails=$((fails + 1)); consec=$((consec + 1)); CELL_FAILS[$k]=$(( ${CELL_FAILS[$k]:-0} + 1 ))
  [ $consec -ge 5 ] && { echo "$(ts) 5 consecutive failed runs; campaign ends"; return 3; }
  return 1
}
end_check() { case $1 in 2) finish deadline; exit 0 ;; 3) finish aborted-5-consecutive-failures; exit 1 ;; esac; }

# the cells, attention modes and arms interleaved inside every repetition
for rep in $(seq 1 "$REPS"); do
  for key in $CELLS; do for attn in $ATTNS; do for arm in $ARMS; do rt "$key" "$attn" "$arm" "$rep"; end_check $?; done; done; done
  echo "$(ts) repetition $rep done, failed runs so far: $fails"
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
done

status "summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
