#!/usr/bin/env bash
# gdn-20261120 traces: one Perfetto trace per cell of Qwen3.5 4B on OUR half of delphi-3b35.
# Purpose: the wall time of the GDN (GatedDeltaNet) host work inside one forward pass. The attention statistics
# (TRON_ATTN_STATS) do not see GDN; tron's only GDN timing instrument is the trace slice "GatedDeltaNet".
# Each cell runs through run-one.sh (load snapshot first, SYSTEM_CONFIG="--instance 1,2") with runtron's in-process
# recorder: --trace-gen FILE --trace-passes SPEC, categories model + scheduler only (keeps the file small).
# A traced run is slower than an untraced one, so its tokens per second are NOT a baseline; only time shares are used.
#   cell table: key|users|prompt|len|passes
# Outputs: exec/results/$NAME/trace/<key>.perfetto-trace, rt/trace-<key>.log, one block in rt-results.txt.
# Usage (on 3b35): bash trace.sh   [CELLS="key ..."]
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/gdn-20261120
NAME=${NAME:-gdn-20261120}
TAG=${TAG:-base}
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-trace.log
MARKER=$EXEC/logs/$NAME-trace.done
LOCAL=/var/tmp/jhan/traces/$NAME
MODEL=${MODEL:-ingested-qwen-3.5-4b-tp4}
CELLS_ALL=${CELLS_ALL:-$'t-1u-p1024|1|1024|32|1-48
t-8u-p1024|8|1024|32|1-48
t-1u-p8192|1|8192|32|1-104
t-8u-p8192|8|8192|32|1-104'}
CELLS=${CELLS:-$(cut -d"|" -f1 <<<"$CELLS_ALL" | tr "\n" " ")}
mkdir -p "$RES/trace" "$LOCAL" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
rm -f "$MARKER"
echo "=== $NAME trace started $(ts) pid $$ CELLS=[$CELLS] ==="
fails=0
for key in $CELLS; do
  line=$(grep -m1 "^$key|" <<<"$CELLS_ALL") || { echo "$(ts) unknown cell $key"; fails=$((fails + 1)); continue; }
  users=$(cut -d'|' -f2 <<<"$line"); prompt=$(cut -d'|' -f3 <<<"$line"); len=$(cut -d'|' -f4 <<<"$line"); passes=$(cut -d'|' -f5 <<<"$line")
  tracef=$LOCAL/$key.perfetto-trace
  [ -s "$RES/trace/$key.perfetto-trace" ] && { echo "$(ts) $key already done"; continue; }
  rm -f "$tracef"
  echo "$(ts) start trace $key users=$users prompt=$prompt len=$len passes=$passes"
  RUN=trace-$key MODEL=$MODEL USERS=$users PROMPT=$prompt LEN=$len TAG=$TAG NAME=$NAME \
    ARMENV="TRON_ATTN_STATS=1 TRON_TRACE_CATEGORIES=-*,+model,+scheduler" \
    EXTRA="--trace-gen $tracef --trace-passes $passes" bash "$C/run-one.sh" 2>&1 | tail -6
  rc=${PIPESTATUS[0]}
  if [ "$rc" -eq 0 ] && [ -s "$tracef" ]; then
    cp "$tracef" "$RES/trace/$key.perfetto-trace" && echo "$(ts) ok $key trace_bytes=$(stat -c %s "$tracef")"
  else
    echo "$(ts) FAILED $key rc=$rc trace_bytes=$(stat -c %s "$tracef" 2>/dev/null || echo 0)"; fails=$((fails + 1))
  fi
  sleep 3
done
echo "$([ $fails -eq 0 ] && echo ok || echo "failed-$fails")" >"$MARKER"
echo "=== trace finished $(ts): $(cat "$MARKER") ==="
