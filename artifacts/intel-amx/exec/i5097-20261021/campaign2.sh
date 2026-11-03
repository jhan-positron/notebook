#!/usr/bin/env bash
# i5097-20261021 campaign2.sh = pr5047-20261020/campaign.sh with two more binaries: fix = PR 5098 head + the dense-page live-mask
# fast path (b79dfb9fed, option OFF) -> /var/tmp/jhan/tron-b47f/gen/runtron.b47f, and c1 = PR 5047 commit 1 alone (e17a12ff09, OFF)
# -> /var/tmp/jhan/tron-b47c1/gen/runtron.b47c1. Arms fix/c1 and fixoff/c1off (kill switch). Guards and run recipe unchanged.
# pr5047-20261020 runtron cells on OUR half of delphi-3bda: throughput and attention path stats of FOUR binaries built with
# one recipe from two commits x two values of the CMake option TRON_K_VNNI:
#   base  = PR 5047's base (= PR 4956 head a5697f86d3), option OFF   -> /var/tmp/jhan/tron-b47b/gen/runtron.b47b
#   head  = PR 5047 head ade89a9d9c, option OFF                        -> /var/tmp/jhan/tron-b47h/gen/runtron.b47h
#   basev = the same base commit, option ON                            -> /var/tmp/jhan/tron-b47bv/gen/runtron.b47bv
#   headv = the same head commit, option ON                            -> /var/tmp/jhan/tron-b47hv/gen/runtron.b47hv
# The question: does PR 5047 (Ben's refactor of PR 4956's K-layout code) change decode throughput or prefill time on
# llama-3.1-8b (CPU attention), qwen3-4b and gpt-oss-120b (FPGA attention)? Pairs that answer it: head vs base (the option
# off, the value every preset ships) and headv vs basev (the option on, the configuration PR 4956 adds).
# Fork of exec/glimext-20261018/campaign.sh; changes here: four binaries, arm_bin / arm_tip for them, an 8th cell field
# "arms" (the arms a cell runs; default $ARMS), ARM_FILTER (arms dropped by the chain when a build failed), NAME, header text.
# Guards, run recipe, watcher, pre-CI hold, idle-serving takeover through platformd, leaf poller, exit-report collection
# are unchanged from the parent.
#   arms: base head basev headv, plus <arm>off = the same binary with TRON_AMX_DISABLE=1 (the kill switch);
#         every arm runs with TRON_ATTN_STATS=1 (the exit report with AVX / AMX / FPGA visit counts per layer).
#   cell: key|model|tp|users|prompt|attn|len|arms (attn = cpu -> USE_HW_ATTN=0, fpga -> USE_HW_ATTN unset; len = -l value).
# Words: our half = socket 1 + cards 90/93/b9/bc (SYSTEM_CONFIG is unset for runtron, placement() pins it); the lease =
# /run/lock/systems-test-ci.lease (nightly CI); takeover = stopping idle production engines through platformd's API.
#   NAME      results/log/marker name (default pr5047-20261020)
#   RT_BASE RT_HEAD RT_BASEV RT_HEADV  binary paths (defaults above)
#   ARMS      default arm list for cells without field 8 ("base head basev headv"), REPS 4 (default)
#   ARM_FILTER arms to drop everywhere (space separated; set by the chain when a build failed)
#   CELLS_ALL cell table lines (default below); CELLS the keys to run (default: every key of CELLS_ALL, in table order)
#   DEADLINE_HHMM UTC deadline (default 0130 -> no run starts after 01:30 UTC), START_NOT_BEFORE ISO UTC
#   SKIP_SERVING_UP=1: do not bring production back at the end (the caller does)
# Every run: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE, then ARM_ENV_<arm>; campaign guard; 10-s watcher; pre-CI hold
# 01:40-03:45 UTC; idle-serving takeover through platformd. Per-run timeout 2400 s. A run whose log already has the TPS
# lines is skipped (resume = relaunch).
# Never edit this file while a campaign runs it (bash re-reads a running script from its byte offset after every forked command).
# Outputs: exec/results/$NAME/{rt/, leaves/, rt-results.txt, exit-reports.txt}; log exec/logs/$NAME.log; .status; .done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i5097-20261021
NAME=${NAME:-i5097-20261021}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME.log
MARKER=$EXEC/logs/$NAME.done
STATUS=$EXEC/logs/$NAME.status
RT_BASE=${RT_BASE:-/var/tmp/jhan/tron-b47b/gen/runtron.b47b}
RT_HEAD=${RT_HEAD:-/var/tmp/jhan/tron-b47h/gen/runtron.b47h}
RT_BASEV=${RT_BASEV:-/var/tmp/jhan/tron-b47bv/gen/runtron.b47bv}
RT_HEADV=${RT_HEADV:-/var/tmp/jhan/tron-b47hv/gen/runtron.b47hv}
RT_FIX=${RT_FIX:-/var/tmp/jhan/tron-b47f/gen/runtron.b47f}
RT_C1=${RT_C1:-/var/tmp/jhan/tron-b47c1/gen/runtron.b47c1}
re_escape() { printf '%s' "$1" | sed 's/[.[\*^$()+?{}|]/\\&/g'; }
OUR_RT_RE="^($(re_escape "$RT_BASE")|$(re_escape "$RT_HEAD")|$(re_escape "$RT_BASEV")|$(re_escape "$RT_HEADV")|$(re_escape "$RT_FIX")|$(re_escape "$RT_C1")) "
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
REPS=${REPS:-4}
ARMS=${ARMS:-"base head fix c1"}
ARM_FILTER=${ARM_FILTER:-}
ARM_ENV_base=${ARM_ENV_base:-"TRON_ATTN_STATS=1"}
ARM_ENV_head=${ARM_ENV_head:-"TRON_ATTN_STATS=1"}
ARM_ENV_basev=${ARM_ENV_basev:-"TRON_ATTN_STATS=1"}
ARM_ENV_headv=${ARM_ENV_headv:-"TRON_ATTN_STATS=1"}
ARM_ENV_baseoff=${ARM_ENV_baseoff:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
ARM_ENV_headoff=${ARM_ENV_headoff:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
ARM_ENV_basevoff=${ARM_ENV_basevoff:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
ARM_ENV_headvoff=${ARM_ENV_headvoff:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
ARM_ENV_fix=${ARM_ENV_fix:-"TRON_ATTN_STATS=1"}
ARM_ENV_c1=${ARM_ENV_c1:-"TRON_ATTN_STATS=1"}
ARM_ENV_fixoff=${ARM_ENV_fixoff:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
ARM_ENV_c1off=${ARM_ENV_c1off:-"TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1"}
POLL_S=${POLL_S:-1}
DEADLINE_HHMM=${DEADLINE_HHMM:-0130}      # UTC, HHMM digits only
START_NOT_BEFORE=${START_NOT_BEFORE:-}   # ISO UTC; empty = start at once
HPFILE=/dev/hugepages/amx-$NAME
BILL_UID=1062305141
SERVING_UP_HELPER=$EXEC/q4b-fpga-20260921/dut.sh
# cell table: key|model|tp|users|prompt|attn|len|arms. Order = run order: the cheap production-relevant cells first.
# llama runs software attention on the CPU (its only path here: AMX dense pages + the dotter tail); qwen and gpt-oss run
# FPGA attention (the model default), where PR 5047 changes the K staging copy. gpt-oss has 64-dim heads: the option
# never applies to it, so its cells run the option-off binaries only.
CELLS_ALL=${CELLS_ALL:-$'l8b-tp2-8u-p8192-off|llama-3.1-8b-instruct-good-tp2|2|8|8192|cpu|256|baseoff headoff fixoff c1off
l8b-tp2-8u-p8192-cpu|llama-3.1-8b-instruct-good-tp2|2|8|8192|cpu|256|base head fix
l8b-tp2-8u-p1024-cpu|llama-3.1-8b-instruct-good-tp2|2|8|1024|cpu|256|head fix'}
CELLS=${CELLS:-$(cut -d"|" -f1 <<<"$CELLS_ALL" | tr "\n" " ")}
mkdir -p "$RES/rt" "$RES/leaves" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
export GUARD_TAKEOVER_LAST
[ -e "$RES/serving-taken-down.marker" ] && GUARD_TAKEOVER_LAST=$(stat -c %Y "$RES/serving-taken-down.marker")
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
arm_bin() { case $1 in base|baseoff) echo "$RT_BASE" ;; head|headoff) echo "$RT_HEAD" ;; basev|basevoff) echo "$RT_BASEV" ;; headv|headvoff) echo "$RT_HEADV" ;; fix|fixoff) echo "$RT_FIX" ;; c1|c1off) echo "$RT_C1" ;; *) return 1 ;; esac; }
arm_env() { local v="ARM_ENV_$1"; echo "${!v:-}"; }
arm_tip() { case $1 in base|baseoff) echo "${TIP_BASE:-?}" ;; head|headoff) echo "${TIP_HEAD:-?}" ;; basev|basevoff) echo "${TIP_BASEV:-?}" ;; headv|headvoff) echo "${TIP_HEADV:-?}" ;; fix|fixoff) echo "${TIP_FIX:-?}" ;; c1|c1off) echo "${TIP_C1:-?}" ;; *) echo "?" ;; esac; }
wt_of() { dirname "$(dirname "$1")"; }
cell_field() {  # $1 key $2 field (2 model, 3 tp, 4 users, 5 prompt, 6 attn, 7 len, 8 arms)
  local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1
  cut -d'|' -f"$2" <<<"$line"
}
arm_dropped() { local a; for a in $ARM_FILTER; do [ "$a" = "$1" ] && return 0; done; return 1; }
cell_arms() {  # the arms of a cell after ARM_FILTER, space separated (field 8, default $ARMS)
  local raw a out=""; raw=$(cell_field "$1" 8); [ -n "$raw" ] || raw=$ARMS
  for a in $raw; do arm_dropped "$a" || out="$out $a"; done
  echo "${out# }"
}

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
NEED_HUGEPAGES=${NEED_HUGEPAGES:-256}
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
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
poll_leaves() {
  local out=$1 wt=$2 A T main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  [ -n "${INST_LOCK_FD:-}" ] && exec {INST_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || exit 0
    pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || { sleep "$POLL_S"; continue; }
    A=$(find "$wt/stats" -maxdepth 4 -type d -path '*/attention' 2>/dev/null | head -1)
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
serving_back_up() {
  [ "${SKIP_SERVING_UP:-0}" = 1 ] && { echo "$(ts) serving: SKIP_SERVING_UP=1, the chain brings production up at its end"; return 0; }
  [ "${GUARD_TAKEOVER_LAST:-0}" != 0 ] || { echo "$(ts) serving: this script did not stop production, nothing to bring up"; return 0; }
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, leaving serving alone"; return 0; fi
  if rinzler_active; then echo "$(ts) serving: rinzler units already active"; return 0; fi
  [ -x "$SERVING_UP_HELPER" ] || { echo "$(ts) serving: helper $SERVING_UP_HELPER missing"; return 0; }
  echo "$(ts) serving: bringing production up through platformd (dut.sh serving-up)"
  if timeout 900 bash "$SERVING_UP_HELPER" serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving: serving-up returned rc=$? (jhan: check platformd; chain.sh retries)"; fi
}
exit_reports() {
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
  local key=$1 arm=$2 rep=$3 model tp users prompt attn len run rlog attempt stops=0 rc res hwenv args tmo hdr lose exh bin wt m
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  tp=$(cell_field "$key" 3); users=$(cell_field "$key" 4); prompt=$(cell_field "$key" 5); attn=$(cell_field "$key" 6); len=$(cell_field "$key" 7)
  len=${len:-256}
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; return 1; }
  wt=$(wt_of "$bin")
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
    hdr="### runtron kind=rt cell=$key model=$model tp=$tp users=$users attn=$attn prompt=$prompt len=$len arm=$arm armenv=[$(arm_env "$arm")] rep=$rep attempt=$attempt bin=$bin tip=$(arm_tip "$arm") $(ts) $(machine_line)"
    echo "$hdr" >>"$RES/rt-results.txt"
    for m in "$wt"/stats/instance-*; do [ -d "$m" ] && mountpoint -q "$m" && ! pgrep -u jhan -f "$OUR_RT_RE" >/dev/null && { fusermount3 -u "$m" 2>/dev/null || fusermount -u "$m" 2>/dev/null; echo "$(ts) unmounted a stale FUSE mount $m"; }; done
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    poll_leaves "$RES/leaves/$run" "$wt" & PPID_POLL=$!
    (cd "$wt" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv $(arm_env "$arm") TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 "$tmo" "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o $args) >"$rlog.attempt$attempt" 2>&1
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

[ "${CAMPAIGN_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME campaign started $(ts) pid $$ REPS=$REPS ARMS=[$ARMS] ARM_FILTER=[$ARM_FILTER] CELLS=[$CELLS] START_NOT_BEFORE=${START_NOT_BEFORE:-none} deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
USED_ARMS=""
for key in $CELLS; do
  for fld in 2 3 4 5 6; do [ -n "$(cell_field "$key" $fld)" ] || { echo "$(ts) cell $key: field $fld empty"; finish "bad-cell-$key"; exit 1; }; done
  placement "$(cell_field "$key" 3)" >/dev/null || { echo "$(ts) cell $key: tp $(cell_field "$key" 3) has no placement"; finish "bad-cell-$key"; exit 1; }
  [ -n "$(cell_arms "$key")" ] || { echo "$(ts) cell $key: no arms left after ARM_FILTER [$ARM_FILTER]"; finish "bad-cell-$key"; exit 1; }
  for arm in $(cell_arms "$key"); do case " $USED_ARMS " in *" $arm "*) ;; *) USED_ARMS="$USED_ARMS $arm" ;; esac; done
done
for arm in $USED_ARMS; do
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
TIP_BASE=$(git -C "$(wt_of "$RT_BASE")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_HEAD=$(git -C "$(wt_of "$RT_HEAD")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_BASEV=$(git -C "$(wt_of "$RT_BASEV")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_HEADV=$(git -C "$(wt_of "$RT_HEADV")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_FIX=$(git -C "$(wt_of "$RT_FIX")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_C1=$(git -C "$(wt_of "$RT_C1")" rev-parse --short HEAD 2>/dev/null || echo "?")
echo "$(ts) tips: base=$TIP_BASE head=$TIP_HEAD basev=$TIP_BASEV headv=$TIP_HEADV; used arms [$USED_ARMS]; $(machine_line)"
{
  echo "# $NAME runtron results: throughput and attention path stats of base = PR 5047 base (PR 4956 head $TIP_BASE, TRON_K_VNNI OFF) vs head = PR 5047 head ($TIP_HEAD, OFF), and basev ($TIP_BASEV, ON) vs headv ($TIP_HEADV, ON), on llama-3.1-8b, qwen3-4b and gpt-oss-120b, on our half of $(hostname); started $(ts)"
  echo "# binaries (same recipe: plain shell, clang-19, --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF|ON): base = $RT_BASE ($TIP_BASE); head = $RT_HEAD ($TIP_HEAD); basev = $RT_BASEV ($TIP_BASEV); headv = $RT_HEADV ($TIP_HEADV)"
  for arm in $USED_ARMS; do echo "#   $arm = $(arm_bin "$arm") with ARM_ENV_$arm=[$(arm_env "$arm")]"; done
  echo "# attn=cpu: USE_HW_ATTN=0 (software attention on the CPU for all layers); attn=fpga: USE_HW_ATTN unset (the model default: qwen and gpt-oss send attention to the FPGA)"
  echo "# every run: env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE; TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE; --dont-stop (every user generates the full len tokens)"
  echo "# HBM-EXHAUSTION line per run: counts of tron's 'lose HW attention' and 'HBM bypass space exhausted' warnings (card K/V space full -> that shard's attention on the CPU)"
  echo "# ATTN-STATS line per run: number of [attn-stats] stderr lines (the exit report) and of live FUSE leaves copied into leaves/<run>/"
  echo "# cells: key|model|tp|users|prompt|attn|len|arms:"; sed 's/^/#   /' <<<"$CELLS_ALL"
  echo "# placement tp2: $(placement 2)"; echo "# placement tp4: $(placement 4)"
  for arm in $USED_ARMS; do b=$(arm_bin "$arm"); sha256sum "$b"; ( cd "$(dirname "$b")" && echo "version $(basename "$b"): $("./$(basename "$b")" --version 2>&1 | head -1)" ); done
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

# the cells and their arms interleaved inside every repetition (the arms of one cell run back to back); the arm order
# alternates per repetition so that a slow drift of the machine does not favour one arm
for rep in $(seq 1 "$REPS"); do
  for key in $CELLS; do
    arms_rep=$(cell_arms "$key")
    [ $((rep % 2)) -eq 0 ] && arms_rep=$(tr ' ' '\n' <<<"$arms_rep" | tac | tr '\n' ' ')
    for arm in $arms_rep; do rt "$key" "$arm" "$rep"; end_check $?; done
  done
  echo "$(ts) repetition $rep done, failed runs so far: $fails"
  exit_reports
done

status "exit reports"
exit_reports
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
