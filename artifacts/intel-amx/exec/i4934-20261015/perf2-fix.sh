#!/usr/bin/env bash
# i4934-20261015 perf driver, generalized copy of perf-fix.sh (that one runs; a running script is never edited): the
# attention mode (ATTN=cpu|fpga), the cells (CELLS_ALL), the arms (ARMS), the generated tokens per prompt (GEN_P1024,
# GEN_P8192), the name (NAME) and a predecessor file to wait for (WAIT_FOR) come from the environment.
# Original header follows. Question: where does the kill-switch decode of
# the fix (fixoff) spend the cycles that PR #4898 (headoff) does not spend? The E-cpu campaign of 2026-10-15 left fixoff
# 1.5-1.7 % behind headoff in decode TPS at tp2 (prompts 1024 and 8192), TTFT at parity.
# Cells: q3-4b tp2, 8 users, CPU attention, prompt 1024 (1024 generated tokens, so the decode lasts ~14 s) and prompt
# 8192 (256 tokens, ~17 s); arms headoff fixoff newoff (campaign-fix.sh's recipe, placement and guards, sourced with
# SYNC_FUNCTIONS_ONLY=1). Per run: runtron starts in the background, the driver waits for the prompt-parsed log line, then
# `sudo perf stat` (cycles, instructions, LLC loads and misses) and `sudo perf record -F 999` run side by side on our
# CPUs for WINDOW s of decode. After the run: perf report (by thread name, binary and symbol; by symbol) and perf annotate
# of the three hottest user symbols.
# Guards: the chain (chain-fix.sh and its three drivers) must have finished; then campaign-fix.sh's wait_clear and
# take_guard before every run (CI lease, other people, the pre-CI hold, idle serving takeover through platformd), the
# 10-s watcher during it, serving back up at the end (finish).
# Outputs: exec/results/i4934-perf/<cell>__<arm>__rep<N>.{log,stat.txt,record.txt,report.txt,bysym.txt,top.txt,annotate-<k>.txt},
# perf data under /var/tmp/jhan/perf-i4934/ (local disk); log exec/logs/i4934-perf.log; exec/logs/i4934-perf.done = ok |
# ok-with-<n>-failed-runs | deadline | aborted.
# Usage (on 3bda): END_BY=<ISO UTC> [NAME=..] [ATTN=cpu|fpga] [CELLS_ALL=..] [ARMS=..] [GEN_P1024=1024] [GEN_P8192=256] [WAIT_FOR=<file>] [REPS=2] [WINDOW=10] bash perf2-fix.sh. Stop: kill -- -<pid> (setsid: pid = group id).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
END_BY=${END_BY:?END_BY (ISO UTC) is required}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date"; exit 64; }
export NAME=${NAME:-i4934-perf2}
export RT_FIX=/var/tmp/jhan/tron-i4934/gen/runtron.fix
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export ARM_ENV_newoff=TRON_AMX_DISABLE=1 ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_fixoff=TRON_AMX_DISABLE=1
export CELLS_ALL=${CELLS_ALL:-"q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024
q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192"}
ATTN=${ATTN:-cpu}
case $ATTN in cpu) HWENV="USE_HW_ATTN=0" ;; fpga) HWENV="-u USE_HW_ATTN" ;; *) echo "ATTN must be cpu or fpga"; exit 64 ;; esac
WAIT_FOR=${WAIT_FOR:-}
export ARMS=${ARMS:-"headoff fixoff newoff"} ATTNS=$ATTN REPS=${REPS:-2}
export DEADLINE_HHMM=$(date -u -d "$END_BY" +%H%M)
export SUMMARY_TITLE="# $NAME (perf runs, no summary table)"
SYNC_FUNCTIONS_ONLY=1 source "$D/campaign-fix.sh"
OUR_CPUS=${OUR_CPUS:-72-143,216-287}
PERFDIR=${PERFDIR:-/var/tmp/jhan/perf-i4934}
WINDOW=${WINDOW:-10}
PERF_EVENTS=cycles,instructions,LLC-loads,LLC-load-misses,cache-misses
mkdir -p "$PERFDIR" "$RES"
WPID=""
exec >>"$LOG" 2>&1
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) ATTN=$ATTN REPS=$REPS ARMS=[$ARMS] WINDOW=${WINDOW}s cpus=$OUR_CPUS WAIT_FOR=${WAIT_FOR:-none} deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
for arm in $ARMS; do
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; finish "unknown-arm-$arm"; exit 1; }
  [ -x "$bin" ] || { echo "$(ts) $bin missing"; finish "no-$arm-binary"; exit 1; }
done
echo "$(ts) tips: head=$(git -C /var/tmp/jhan/tron-pr3 rev-parse --short HEAD) new=$(git -C /var/tmp/jhan/tron-pr4 rev-parse --short HEAD) fix=$(git -C /var/tmp/jhan/tron-i4934 rev-parse --short HEAD); $(machine_line)"

chain_running() { pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/(chain|probe|identity|mutate)-fix\.sh' >/dev/null; }
waited=0
while chain_running; do
  past_deadline && { echo "$(ts) deadline reached while the chain still runs"; finish deadline; exit 0; }
  [ $waited = 0 ] && { status "waiting: the chain (chain-fix.sh) still runs"; waited=1; }
  sleep 120
done
[ $waited = 1 ] && echo "$(ts) the chain has finished"
waited=0
while [ -n "$WAIT_FOR" ] && [ ! -e "$WAIT_FOR" ]; do
  past_deadline && { echo "$(ts) deadline reached while waiting for $WAIT_FOR"; finish deadline; exit 0; }
  [ $waited = 0 ] && { status "waiting: $WAIT_FOR"; waited=1; }
  sleep 120
done
[ $waited = 1 ] && echo "$(ts) $WAIT_FOR exists"

gen_tokens() { case $1 in 1024) echo "${GEN_P1024:-1024}" ;; 8192) echo "${GEN_P8192:-256}" ;; *) echo 256 ;; esac; }

# one profiled runtron run; $1 key $2 arm $3 rep. Returns 2 when the deadline passes.
run_perf() {
  local key=$1 arm=$2 rep=$3
  local model tp users prompt bin tag rlog data gen rc pid i stat_pid rec_pid k line sym
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  tp=$(cell_field "$key" 3); users=$(cell_field "$key" 4); prompt=$(cell_field "$key" 5)
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; return 1; }
  tag=${key}__${arm}__rep${rep}
  rlog=$RES/$tag.log
  data=$PERFDIR/$tag.data
  gen=$(gen_tokens "$prompt")
  [ -s "$RES/$tag.report.txt" ] && [ -s "$RES/$tag.stat.txt" ] && { echo "$(ts) $tag already done"; return 0; }
  past_deadline && { echo "$(ts) deadline reached before $tag"; return 2; }
  wait_clear || { echo "$(ts) deadline reached while waiting before $tag"; return 2; }
  take_guard || { echo "$(ts) deadline reached while waiting for the guard before $tag"; return 2; }
  status "perf $tag"
  echo "$(ts) $tag start: bin=$bin env=[$(arm_env "$arm")] prompt=$prompt gen=$gen users=$users; $(machine_line)"
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $HWENV $(arm_env "$arm") TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
      timeout -k 60 2400 "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o --prompt-length "$prompt" -l "$gen" -u "$users" --dont-stop) >"$rlog" 2>&1 &
  pid=$!
  # The prompt-parsed line: every user's prompt is parsed in the same batch, so the first line marks the start of decode.
  for i in $(seq 1 900); do
    grep -q "Parsing the prompt took" "$rlog" 2>/dev/null && break
    kill -0 "$pid" 2>/dev/null || break
    [ -e "$RES/rt.STOPPED" ] && break
    sleep 1
  done
  if grep -q "Parsing the prompt took" "$rlog" 2>/dev/null && kill -0 "$pid" 2>/dev/null; then
    sleep 1
    echo "$(ts) $tag perf window ${WINDOW}s starts"
    sudo -n perf stat -e "$PERF_EVENTS" -a -C "$OUR_CPUS" -- sleep "$WINDOW" >"$RES/$tag.stat.txt" 2>&1 &
    stat_pid=$!
    sudo -n perf record -F 999 -a -C "$OUR_CPUS" -o "$data" -- sleep "$WINDOW" >"$RES/$tag.record.txt" 2>&1 &
    rec_pid=$!
    wait "$stat_pid"; wait "$rec_pid"
    echo "$(ts) $tag perf window done"
  else
    echo "$(ts) $tag: no prompt-parsed line while runtron ran (stopped=$([ -e "$RES/rt.STOPPED" ] && cat "$RES/rt.STOPPED" || echo no))"
  fi
  wait "$pid"; rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  grep -E "Parsing the prompt took|average tok/s" "$rlog" 2>/dev/null | head -2 | cut -c1-200
  if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then echo "$(ts) $tag RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)"; return 1; fi
  [ $rc -eq 0 ] || { echo "$(ts) $tag runtron rc=$rc"; return 1; }
  [ -s "$data" ] || { echo "$(ts) $tag: no perf data"; return 1; }
  sudo -n chown jhan "$data" 2>/dev/null || true
  sudo -n perf report -i "$data" --stdio --sort comm,dso,symbol --percent-limit 0.2 2>/dev/null >"$RES/$tag.report.txt"
  sudo -n perf report -i "$data" --stdio --sort symbol -F overhead,symbol --percent-limit 0.1 2>/dev/null >"$RES/$tag.bysym.txt"
  grep -v '^#' "$RES/$tag.bysym.txt" | grep -v '^$' | grep '\[\.\]' | head -5 >"$RES/$tag.top.txt"
  k=0
  while IFS= read -r line; do
    sym=${line#*\] }
    k=$((k + 1)); [ $k -gt 3 ] && break
    sudo -n perf annotate -i "$data" --stdio -s "$sym" 2>/dev/null | head -8000 >"$RES/$tag.annotate-$k.txt"
    echo "$(ts) $tag annotate $k: $(cut -c1-120 <<<"$line") -> $(wc -l <"$RES/$tag.annotate-$k.txt") lines"
  done <"$RES/$tag.top.txt"
  echo "$(ts) $tag done: $(head -3 "$RES/$tag.top.txt" | cut -c1-100 | tr '\n' ';')"
  return 0
}

fails=0
for rep in $(seq 1 "$REPS"); do
  for key in $(cut -d'|' -f1 <<<"$CELLS_ALL"); do
    for arm in $ARMS; do
      run_perf "$key" "$arm" "$rep"; rc=$?
      case $rc in 2) finish deadline; exit 0 ;; 0) ;; *) fails=$((fails + 1)); [ $fails -ge 4 ] && { finish aborted-4-failed-runs; exit 1; } ;; esac
    done
  done
  echo "$(ts) repetition $rep done, failed runs so far: $fails"
done
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
