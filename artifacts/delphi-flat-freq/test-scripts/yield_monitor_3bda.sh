#!/usr/bin/env bash
# yield_monitor_3bda.sh — guard for window tests on the CI machine 3bda.
# The CI/production owners have priority: on ANY of
#   - a non-jhan user logging in (e.g. Hannah),
#   - a rinzler process appearing (platformd/CI bringing serving up),
#   - a runtron process OUTSIDE our runner's process group,
#   - a talos process appearing (CI harness),
#   - hard deadline (default 3 h),
# it SIGTERM/SIGKILLs the runner's whole process group (never touches the
# foreign process), deletes our hugepage files, and writes $D/YIELDED with
# the reason. Exits normally when the runner writes $D/DONE.
# Usage: yield_monitor_3bda.sh <runner-output-dir> [max-secs]
set -u
D="$1"; MAX_SECS="${2:-10800}"
LOG="$D/yield_monitor.log"
log(){ echo "$(date -u '+%F %T') $*" >> "$LOG"; }
log "monitor start pid=$$ max_secs=$MAX_SECS"

# wait up to 60 s for the runner to publish its PGID
PGID=""
for i in $(seq 60); do
  [ -f "$D/RUNNER_PGID" ] && PGID=$(cat "$D/RUNNER_PGID") && break
  sleep 1
done
[ -z "$PGID" ] && { log "no RUNNER_PGID after 60s — exiting"; exit 1; }
log "guarding pgid=$PGID"

cleanup_hugepages(){
  find /dev/hugepages -maxdepth 1 -user "$USER" -name "libpos*" -delete 2>>"$LOG"
  log "hugepages after cleanup: $(grep HugePages_Free /proc/meminfo | tr -s ' ')"
}

yield(){
  local why="$1"
  log "YIELD triggered: $why"
  echo "$(date -u '+%F %T') $why" > "$D/YIELDED"
  kill -TERM -- "-$PGID" 2>/dev/null
  sleep 8
  kill -KILL -- "-$PGID" 2>/dev/null
  # safety: reap any of OUR runtron stragglers (match by pgid only —
  # never kill a runtron/rinzler we don't own)
  for pid in $(pgrep -x runtron); do
    pg=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
    [ "$pg" = "$PGID" ] && kill -KILL "$pid" 2>/dev/null && log "killed straggler $pid"
  done
  sleep 2
  cleanup_hugepages
  log "yield complete — machine returned"
  exit 0
}

START=$(date +%s)
while true; do
  # normal completion
  if [ -f "$D/DONE" ]; then
    cleanup_hugepages
    log "runner DONE — normal exit"
    exit 0
  fi
  # runner vanished without DONE (crash): clean up and record
  if ! pgrep -g "$PGID" > /dev/null 2>&1; then
    sleep 10
    if [ ! -f "$D/DONE" ] && ! pgrep -g "$PGID" > /dev/null 2>&1; then
      cleanup_hugepages
      echo "$(date -u '+%F %T') runner-vanished" > "$D/ABORTED"
      log "runner vanished without DONE — cleaned up, exiting"
      exit 1
    fi
    continue
  fi
  # 1. any non-jhan login
  U=$(who | awk '{print $1}' | grep -v "^jhan$" | head -1)
  [ -n "$U" ] && yield "login:$U"
  # 2. rinzler serving coming up (CI/production)
  pgrep -x rinzler > /dev/null 2>&1 && yield "rinzler-started"
  # 3. foreign runtron (not in our process group)
  for pid in $(pgrep -x runtron); do
    pg=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ -n "$pg" ] && [ "$pg" != "$PGID" ]; then yield "foreign-runtron:$pid"; fi
  done
  # 4. talos CI harness process
  T=$(pgrep -f "[t]alos" | head -1)
  [ -n "$T" ] && yield "talos-process:$T"
  # 5. hard deadline — never risk colliding with tonight's nightly
  NOW=$(date +%s)
  [ $((NOW - START)) -gt "$MAX_SECS" ] && yield "deadline-${MAX_SECS}s"
  sleep 15
done
