#!/usr/bin/env bash
# attnstats-20261002 runtron cells on OUR half of delphi-3bda: attention path stats (TRON_ATTN_STATS=1) of tron main with
# the AMX kernel enabled and disabled, three models, CPU and FPGA attention.
# Fork of exec/attnstats-20260924/campaign.sh (itself a copy of exec/i4525-20260922/campaign.sh: guards, run recipe,
# watcher, pre-CI hold, idle-serving takeover through platformd, restore). Changes in this fork:
#   - ONE binary (RT_MAIN) for every arm; the arm picks only the environment (ARM_ENV_<arm>), e.g.
#     ARM_ENV_amxon="TRON_ATTN_STATS=1", ARM_ENV_amxoff="TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1".
#   - the attention mode and the generated length are cell fields: key|model|tp|users|prompt|attn|len
#     (attn = cpu -> USE_HW_ATTN=0, fpga -> USE_HW_ATTN unset, fpga1 -> USE_HW_ATTN=1 for models whose default is
#     CPU attention; len = -l value, default 256). ATTNS is gone.
#   - a leaf poller per run copies the live FUSE attention leaves of the model (worker and layer leaves are not in the
#     stderr report) into RES/leaves/<run>/ every POLL_S seconds (default 1 s; decode at prompt 1024 lasts 2-4 s,
#     so a run gets 1-3 snapshots); the last snapshot stays. It is an in-flight sample for the worker/layer rows, it
#     may be missing for a short run, and gen_compare.py does not read it.
#   - no summarize.py; the chain runs gen_compare.py on the whole result folder.
# Words: our half = socket 1 + cards 90/93/b9/bc (SYSTEM_CONFIG is unset for runtron, placement() pins it); the lease =
# /run/lock/systems-test-ci.lease (nightly CI); takeover = stopping idle production engines through platformd's API.
#   NAME      results/log/marker name (default attnstats-20261002)
#   RT_MAIN   path of the runtron binary (tron main, TRON_AMX_DISPATCH=ON build)
#   ARMS      "amxon amxoff" (default), REPS 1
#   CELLS_ALL cell table lines; CELLS the keys to run (default: every key of CELLS_ALL)
#   DEADLINE_HHMM UTC deadline (default 0130 -> 01:30 UTC), START_NOT_BEFORE ISO UTC
# Every run: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE, then ARM_ENV_<arm>; campaign guard; 10-s watcher; pre-CI hold
# 01:40-03:45 UTC; idle-serving takeover through platformd; production serving brought back up at the end when this
# script took it down.
# Never edit this file while a campaign runs it (bash re-reads a running script from its byte offset after every forked command).
# Outputs: exec/results/$NAME/{rt/, leaves/, rt-results.txt, exit-reports.txt}; log exec/logs/$NAME.log; .status; .done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/attnstats-20261002
NAME=${NAME:-attnstats-20261002}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
RT_MAIN=${RT_MAIN:?RT_MAIN (runtron path) is required}
OUR_RT_RE="^$(printf '%s' "$RT_MAIN" | sed 's/[.[\*^$()+?{}|]/\\&/g') "
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
REPS=${REPS:-1}
ARMS=${ARMS:-"amxon amxoff"}
POLL_S=${POLL_S:-1}
DEADLINE_HHMM=${DEADLINE_HHMM:-0130}      # UTC, HHMM digits only
START_NOT_BEFORE=${START_NOT_BEFORE:-}   # ISO UTC; empty = start at once
HPFILE=/dev/hugepages/amx-$NAME
BILL_UID=1062305141
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
# cell table: key|model|tp|users|prompt|attn|len
CELLS_ALL=${CELLS_ALL:?CELLS_ALL (cell table key|model|tp|users|prompt|attn|len, one per line) is required}
CELLS=${CELLS:-$(cut -d"|" -f1 <<<"$CELLS_ALL" | tr "\n" " ")}
WT=$(dirname "$(dirname "$RT_MAIN")")       # the worktree: runtron mounts its stats under $WT/stats/instance-N
mkdir -p "$RES/rt" "$RES/leaves" "$EXEC/logs"
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
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
arm_env() { local v="ARM_ENV_$1"; echo "${!v:-}"; }
cell_field() {  # $1 key $2 field (2 model, 3 tp, 4 users, 5 prompt, 6 attn, 7 len)
  local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1
  cut -d'|' -f"$2" <<<"$line"
}

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
NEED_HUGEPAGES=${NEED_HUGEPAGES:-256}
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  # after the serving check: production engines hold every hugepage while they run (HugePages_Free 0 seen 2026-10-02 00:59Z),
  # and the takeover in wait_clear is what frees them
  local hp; hp=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo); [ "${hp:-0}" -ge "$NEED_HUGEPAGES" ] || { echo "only $hp free hugepages (need $NEED_HUGEPAGES)"; return 0; }
  return 1
}
wait_clear() {  # returns 2 when the deadline passes while waiting
  local why waited=0
  while why=$(blocked); do
    past_deadline && return 2
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    [ "$why" = "rinzler@N unit active" ] && rinzler_takeover_if_idle && { echo "$(ts) takeover by campaign pid $$" >>"$RES/serving-taken-down.marker"; continue; }
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
# Leaf poller: while our runtron runs, copy every file of the model's attention leaf directory (FUSE, one read per
# file) into RES/leaves/<run>/; a snapshot replaces the previous one only when it has at least one counted forward.
# A multi-leaf snapshot is not one consistent read (the run advances between files); it is for the worker/layer rows.
poll_leaves() {
  local out=$1 A T main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  [ -n "${INST_LOCK_FD:-}" ] && exec {INST_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || exit 0
    pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || { sleep "$POLL_S"; continue; }
    A=$(find "$WT/stats" -maxdepth 4 -type d -path '*/attention' 2>/dev/null | head -1)
    if [ -n "$A" ] && grep -q '"forwards":[1-9]' "$A/decode_like_forwards" 2>/dev/null; then
      T=$out.tmp; rm -rf "$T"; mkdir -p "$T"
      for f in "$A"/*; do timeout 5 cat "$f" >"$T/$(basename "$f")" 2>/dev/null; done
      echo "$(ts) $A" >"$T/.taken"; rm -rf "$out"; mv "$T" "$out"
    fi
    sleep "$POLL_S"
  done
}
PPID_POLL=""
stop_poller() { [ -n "$PPID_POLL" ] && { kill "$PPID_POLL" 2>/dev/null; wait "$PPID_POLL" 2>/dev/null; }; PPID_POLL=""; }
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent)"
}
remove_our_slice_files() {
  local f
  for f in /dev/hugepages/slice-*-of-8 /dev/hugepages/amx-$NAME*; do
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
  if timeout 900 bash "$SERVING_UP_HELPER" serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving: serving-up returned rc=$? (jhan: check platformd; chain.sh retries)"; fi
}
exit_reports() {  # every [attn-stats] line of every finished run, with the run name in front
  local f
  for f in "$RES"/rt/*.log; do
    [ -e "$f" ] || continue
    echo "## $(basename "$f" .log)"
    grep -h -m1 "HW attention" "$f" | cut -c1-400
    grep -h "^\[attn-stats\]" "$f"
    echo "HBM-EXHAUSTION lose=$(grep -c 'lose HW attention' "$f") exhausted=$(grep -c 'HBM bypass space exhausted' "$f")"
  done >"$RES/exit-reports.txt"
}
finish() {
  stop_watcher; stop_poller
  if [ "${1#aborted}" != "$1" ]; then
    trap '' TERM
    kill_ours
    for _ in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
    pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: SIGKILL to our runtron"; sleep 2; }
  fi
  remove_our_slice_files
  campaign_guard_release 2>/dev/null
  exit_reports
  serving_back_up
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}

# one runtron invocation; $1 key $2 arm $3 rep
run_one() {
  local key=$1 arm=$2 rep=$3 model tp users prompt attn len run rlog attempt stops=0 rc res hwenv args tmo hdr lose exh
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  tp=$(cell_field "$key" 3); users=$(cell_field "$key" 4); prompt=$(cell_field "$key" 5); attn=$(cell_field "$key" 6); len=$(cell_field "$key" 7)
  len=${len:-256}
  case $attn in cpu) hwenv="USE_HW_ATTN=0" ;; fpga) hwenv="-u USE_HW_ATTN" ;; fpga1) hwenv="USE_HW_ATTN=1" ;; *) echo "$(ts) cell $key: attn '$attn' is not cpu, fpga or fpga1"; return 1 ;; esac
  run=${key}__${attn}__${arm}__rep${rep}
  rlog=$RES/rt/$run.log
  grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) runtron $run already done"; return 0; }
  args="--prompt-length $prompt -l $len -u $users --dont-stop"; tmo=2400
  NEED_HUGEPAGES=$([ "$tp" = 4 ] && echo 256 || echo 128)
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    past_deadline && { echo "$(ts) deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) reached before rt $run"; return 2; }
    attempt=$((attempt + 1))
    wait_clear || { echo "$(ts) deadline reached while waiting before rt $run"; return 2; }
    take_guard || { echo "$(ts) deadline reached while waiting for the guard before rt $run"; return 2; }
    status "rt $key attn=$attn arm=$arm rep=$rep attempt=$attempt"
    hdr="### runtron kind=rt cell=$key model=$model tp=$tp users=$users attn=$attn prompt=$prompt len=$len arm=$arm armenv=[$(arm_env "$arm")] rep=$rep attempt=$attempt bin=$RT_MAIN tip=$TIP_MAIN $(ts) $(machine_line)"
    echo "$hdr" >>"$RES/rt-results.txt"
    # a runtron killed before its unmount leaves its FUSE mount; the next run at the same --instance would fail (README.stats.md)
    for m in "$WT"/stats/instance-*; do [ -d "$m" ] && mountpoint -q "$m" && ! pgrep -u jhan -f "$OUR_RT_RE" >/dev/null && { fusermount3 -u "$m" 2>/dev/null || fusermount -u "$m" 2>/dev/null; echo "$(ts) unmounted a stale FUSE mount $m"; }; done
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    poll_leaves "$RES/leaves/$run" & PPID_POLL=$!
    (cd "$WT" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv $(arm_env "$arm") TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 "$tmo" "$RT_MAIN" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o $args) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; stop_poller; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s" "$rlog.attempt$attempt" 2>/dev/null | cut -c1-400)
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
    { echo "$res"; echo "HBM-EXHAUSTION lose=${lose:-0} exhausted=${exh:-0} (warning lines in this run's log: 'lose HW attention' = a 1024-token shard scored on the CPU instead of the card)"
      echo "ATTN-STATS lines=$(grep -c '^\[attn-stats\]' "$rlog") leaves=$(ls "$RES/leaves/$run" 2>/dev/null | wc -l) taken=$(cat "$RES/leaves/$run/.taken" 2>/dev/null | cut -d' ' -f1) snapshot_decode_forwards=$(grep -o '"forwards":[0-9]*' "$RES/leaves/$run/decode_like_forwards" 2>/dev/null | cut -d: -f2)"; } >>"$RES/rt-results.txt"
    return 0
  done
}

[ "${I4525_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ REPS=$REPS ARMS=[$ARMS] CELLS=[$CELLS] START_NOT_BEFORE=${START_NOT_BEFORE:-none} deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
[ -x "$RT_MAIN" ] || { echo "$(ts) $RT_MAIN missing"; finish "no-binary"; exit 1; }
for key in $CELLS; do
  for fld in 2 3 4 5 6; do [ -n "$(cell_field "$key" $fld)" ] || { echo "$(ts) cell $key: field $fld empty"; finish "bad-cell-$key"; exit 1; }; done
  placement "$(cell_field "$key" 3)" >/dev/null || { echo "$(ts) cell $key: tp $(cell_field "$key" 3) has no placement"; finish "bad-cell-$key"; exit 1; }
done
if [ -n "$START_NOT_BEFORE" ]; then
  while [ "$(date -u +%s)" -lt "$SNB_EPOCH" ]; do
    left=$(( SNB_EPOCH - $(date -u +%s) )); [ "$left" -gt 1800 ] && left=1800
    status "waiting: START_NOT_BEFORE $START_NOT_BEFORE (next check in $((left / 60)) min)"; sleep "$left"
  done
  status "START_NOT_BEFORE passed"
fi
TIP_MAIN=$(git -C "$WT" rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$(ts) tip: main=$TIP_MAIN; $(machine_line)"
{
  echo "# $NAME runtron results: attention path stats of tron main ($TIP_MAIN) with the AMX kernel enabled and disabled, on our half of $(hostname); started $(ts)"
  echo "# binary: $RT_MAIN (one build, TRON_AMX_DISPATCH=ON); arms pick the environment only:"
  for arm in $ARMS; do echo "#   $arm = ARM_ENV_$arm=[$(arm_env "$arm")]"; done
  echo "# attn=cpu: USE_HW_ATTN=0 (software attention on the CPU); attn=fpga: USE_HW_ATTN unset (the model default: FPGA attention for generated plugins); attn=fpga1: USE_HW_ATTN=1 (FPGA attention forced on, engagement 127)"
  echo "# every run: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE; --dont-stop (every user generates the full len tokens)"
  echo "# HBM-EXHAUSTION line per run: counts of tron's 'lose HW attention' and 'HBM bypass space exhausted' warnings (card K/V space full -> that shard's attention on the CPU)"
  echo "# ATTN-STATS line per run: number of [attn-stats] stderr lines (the exit report) and of live FUSE leaves copied into leaves/<run>/"
  echo "# cells: key|model|tp|users|prompt|attn|len:"; sed 's/^/#   /' <<<"$CELLS_ALL"
  echo "# placement tp2: $(placement 2)"; echo "# placement tp4: $(placement 4)"
  sha256sum "$RT_MAIN"; ( cd "$(dirname "$RT_MAIN")" && echo "version $(basename "$RT_MAIN"): $("./$(basename "$RT_MAIN")" --version 2>&1 | head -1)" )
} >>"$RES/rt-results.txt"

fails=0; consec=0
declare -A CELL_FAILS=()
rt() {  # $1 key $2 arm $3 rep
  local k="$1|$2" rc
  [ "${CELL_FAILS[$k]:-0}" -ge 2 ] && { echo "$(ts) skip rt $1 $2 rep$3: failed twice before"; return 0; }
  run_one "$1" "$2" "$3"; rc=$?
  [ $rc -eq 2 ] && return 2
  if [ $rc -eq 0 ]; then consec=0; return 0; fi
  fails=$((fails + 1)); consec=$((consec + 1)); CELL_FAILS[$k]=$(( ${CELL_FAILS[$k]:-0} + 1 ))
  [ $consec -ge 5 ] && { echo "$(ts) 5 consecutive failed runs; campaign ends"; return 3; }
  return 1
}
end_check() { case $1 in 2) finish deadline; exit 0 ;; 3) finish aborted-5-consecutive-failures; exit 1 ;; esac; }

# the cells and arms interleaved inside every repetition (arm pairs of one cell run back to back)
for rep in $(seq 1 "$REPS"); do
  for key in $CELLS; do for arm in $ARMS; do rt "$key" "$arm" "$rep"; end_check $?; done; done
  echo "$(ts) repetition $rep done, failed runs so far: $fails"
  exit_reports
done

status "exit reports"
exit_reports
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
