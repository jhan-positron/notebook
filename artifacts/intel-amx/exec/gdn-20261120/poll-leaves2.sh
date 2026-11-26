#!/usr/bin/env bash
# gdn-20261120 leaf poller. Runs ON delphi-3b35 next to campaign.sh. Read-only.
# While one of OUR runtron processes runs, it copies the live attention statistics files ("leaves") of the model
# from tron's FUSE stats mount into exec/results/$NAME/leaves/<run>/ once per POLL_S seconds. The per-layer and
# per-worker timers exist only in these files; the report that runtron prints at exit holds totals only.
# The run name is taken from the newest rt/*.log.attempt file. A snapshot replaces the previous one only when it
# holds at least one counted decode forward, so the kept copy is the last full one before the run ended.
# Stop it with: touch /var/tmp/jhan/$NAME.poll2.stop   (it also ends by itself after IDLE_MAX seconds without a run).
set -u
NAME=${NAME:-gdn-20261120}
TAG=${TAG:-base}
POLL_S=${POLL_S:-1}
IDLE_MAX=${IDLE_MAX:-900}
EXEC=/home/jhan/workspace/intel-AMX/exec
RES=$EXEC/results/$NAME
WT=/var/tmp/jhan/b35-gdn-$TAG
BIN=$WT/gen/runtron
STOP=/var/tmp/jhan/$NAME.poll2.stop
mkdir -p "$RES/leaves"
rm -f "$STOP"
exec {POLL_LOCK_FD}>"/var/tmp/jhan/$NAME.poll2.lock"
flock -n "$POLL_LOCK_FD" || { echo "another poller runs"; exit 1; }
idle=0
while [ ! -e "$STOP" ] && [ "$idle" -lt "$IDLE_MAX" ]; do
  if ! pgrep -u "$(id -u)" -f "^$BIN " >/dev/null 2>&1; then sleep "$POLL_S"; idle=$((idle + POLL_S)); continue; fi
  idle=0
  run=$(ls -t "$RES"/rt/*.log.attempt 2>/dev/null | head -1); run=$(basename "${run:-none}" .log.attempt)
  A=$(find "$WT/stats" -maxdepth 4 -type d -path '*/attention' 2>/dev/null | head -1)
  if [ -n "$A" ] && [ "$run" != none ] && grep -q '"forwards":[1-9]' "$A/decode_like_forwards" 2>/dev/null; then
    T=$RES/leaves/$run.tmp; rm -rf "$T"; mkdir -p "$T"
    for f in "$A"/*; do timeout 5 cat "$f" >"$T/$(basename "$f")" 2>/dev/null; done
    # keep the snapshot only when the model state was still alive after the last file was read (a dead state reads {})
    if grep -q '"forwards":[1-9]' "$A/decode_like_forwards" 2>/dev/null; then date -u +%FT%TZ >"$T/.taken"; rm -rf "$RES/leaves/$run"; mv "$T" "$RES/leaves/$run"; else rm -rf "$T"; fi
  fi
  sleep "$POLL_S"
done
