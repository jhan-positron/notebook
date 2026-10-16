#!/usr/bin/env bash
# i4934-20261015 trace driver (runs ON delphi-3bda, our half, detached): Perfetto traces of headoff (PR #4898) next to
# fixoff under the same conditions, so the main-thread spans of the two save paths can be compared (the T step of
# probe-fix.sh traced only newoff and fixoff). Runs after WAIT_FOR exists (default: the ablation campaign's done file),
# under campaign-fix.sh's guards (sourced with SYNC_FUNCTIONS_ONLY=1: CI lease, other people, the pre-CI hold, idle
# serving takeover through platformd, serving back up at the end). Same placement, flags and passes as probe-fix.sh's
# trace_one: tp2, 8 users, kill switch, prompt 1024 (passes 1,8,120-150) and prompt 8192 (passes 1,2,64,100-110).
# Outputs: exec/results/i4934-trace2/trace-<arm>-p<prompt>.{pftrace,log}; log exec/logs/i4934-trace2.log; done file
# exec/logs/i4934-trace2.done = ok | ok-with-N-failed-runs | deadline | aborted.
# Usage (on 3bda): END_BY=<ISO UTC> [WAIT_FOR=<file>] bash trace-head.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
D=$EXEC/i4934-20261015
END_BY=${END_BY:?END_BY (ISO UTC) is required}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date"; exit 64; }
export NAME=i4934-trace2
export RT_FIX=/var/tmp/jhan/tron-i4934/gen/runtron.fix
export RT_NEW=/var/tmp/jhan/tron-pr4/gen/runtron.pr4
export RT_HEAD=/var/tmp/jhan/tron-pr3/gen/runtron.pr3
export RT_BASE=/var/tmp/jhan/tron-main1010/gen/runtron.main1010
export ARM_ENV_headoff=TRON_AMX_DISABLE=1 ARM_ENV_fixoff=TRON_AMX_DISABLE=1
export CELLS_ALL="q3-4b-tp2-8u-p1024|ingested-qwen-3-4b-instruct-2507-tp2|2|8|1024
q3-4b-tp2-8u-p8192|ingested-qwen-3-4b-instruct-2507-tp2|2|8|8192"
export ARMS="headoff fixoff" ATTNS=cpu REPS=1
export DEADLINE_HHMM=$(date -u -d "$END_BY" +%H%M)
export SUMMARY_TITLE="# $NAME (trace runs, no summary table)"
WAIT_FOR=${WAIT_FOR:-$EXEC/logs/i4934-abl-cpu.done}
SYNC_FUNCTIONS_ONLY=1 source "$D/campaign-fix.sh"
WPID=""
exec >>"$LOG" 2>&1
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME started $(ts) pid $$ pgid $(ps -o pgid= -p $$ | tr -d ' ') on $(hostname) WAIT_FOR=$WAIT_FOR deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
for arm in $ARMS; do bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "$(ts) $bin missing"; finish "no-$arm-binary"; exit 1; }; done
waited=0
while [ ! -e "$WAIT_FOR" ]; do
  past_deadline && { echo "$(ts) deadline reached while waiting for $WAIT_FOR"; finish deadline; exit 0; }
  [ $waited = 0 ] && { status "waiting: $WAIT_FOR"; waited=1; }
  sleep 120
done
[ $waited = 1 ] && echo "$(ts) $WAIT_FOR exists"

passes_of() { case $1 in 1024) echo "1,8,120-150" ;; *) echo "1,2,64,100-110" ;; esac; }
# one traced run; $1 arm $2 prompt. Returns 2 when the deadline passes.
trace_run() {
  local arm=$1 prompt=$2
  local bin out rc
  bin=$(arm_bin "$arm") || { echo "$(ts) unknown arm $arm"; return 1; }
  out=$RES/trace-$arm-p$prompt
  [ -s "$out.pftrace" ] && grep -q "average tok/s" "$out.log" 2>/dev/null && { echo "$(ts) trace $arm p$prompt already done"; return 0; }
  past_deadline && { echo "$(ts) deadline reached before trace $arm p$prompt"; return 2; }
  wait_clear || { echo "$(ts) deadline reached while waiting before trace $arm p$prompt"; return 2; }
  take_guard || { echo "$(ts) deadline reached while waiting for the guard before trace $arm p$prompt"; return 2; }
  status "trace $arm p$prompt"
  echo "$(ts) trace $arm p$prompt start: bin=$bin env=[$(arm_env "$arm")] passes=$(passes_of "$prompt"); $(machine_line)"
  rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
  (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 $(arm_env "$arm") TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
      timeout -k 60 2400 "$bin" stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 $(placement 2) --hugepage_file "$HPFILE" -o --prompt-length "$prompt" -l 256 -u 8 --dont-stop --trace-gen "$out.pftrace" --trace-passes "$(passes_of "$prompt")") >"$out.log" 2>&1
  rc=$?
  stop_watcher; campaign_guard_release; remove_our_slice_files
  echo "$(ts) trace $arm p$prompt rc=$rc file=$(stat -c %s "$out.pftrace" 2>/dev/null || echo missing) B; $(grep -E 'average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-200)"
  if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then echo "$(ts) trace $arm p$prompt RUN-STOPPED $(cat "$RES/rt.STOPPED" 2>/dev/null)"; return 1; fi
  [ $rc -eq 0 ] && [ -s "$out.pftrace" ] || return 1
  return 0
}
fails=0
for prompt in 1024 8192; do
  for arm in $ARMS; do
    trace_run "$arm" "$prompt"; rc=$?
    case $rc in 2) finish deadline; exit 0 ;; 0) ;; *) fails=$((fails + 1)); [ $fails -ge 3 ] && { finish aborted-3-failed-runs; exit 1; } ;; esac
  done
done
remove_our_slice_files
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
