#!/usr/bin/env bash
# Row-15 follow-up: decode-phase-only counters for the layout penalty.
# Long generation (-l 2560) at 1u/8K, AVX arm; attach sudo perf stat AFTER the
# prefill line appears, sample 15 s inside pure decode. Arms: layout-only
# (gen/runtron, 3-plane blocks) vs canonical (gen/runtron.inc1b).
# perf_event_paranoid=4 blocks user perf; sudo attach is read-only monitoring
# (no system change). Guard: no start at/after 03:00 UTC.
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-perf-decode.txt
DIR=$EXEC/results/slot1/perf-decode-logs
LOG=$EXEC/logs/p2-perf-decode.log
MARKER=$EXEC/logs/p2-perf-decode.done
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-perf-decode start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
if t=$(hhmm); [ "$t" -ge 300 ] && [ "$t" -lt 2100 ]; then
  echo guard-stop >"$MARKER"; exit 1
fi

cd ~/workspace/tron-amx
RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2e --nr_hugepages 128 -o"
{
  echo "# Decode-phase perf counters, 1u/8K AVX arm, $(date -u +%FT%TZ)"
  for pair in "gen/runtron layout-only" "gen/runtron.inc1b canonical"; do
    set -- $pair; bin=$1; name=$2
    echo "### perf-decode bin=$name ($bin) TRON_AMX_DISABLE=1 ctx=8192 len=2560"
    : >"$DIR/perf-$name.log"
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=1 ./$bin $RTARGS \
      --prompt-length 8192 -l 2560 -u 1 >"$DIR/perf-$name.log" 2>&1 &
    rpid=$!
    ( sleep 280; kill "$rpid" 2>/dev/null ) &
    watchdog=$!
    ok=0
    for i in $(seq 1 120); do
      grep -q "Parsing the prompt took" "$DIR/perf-$name.log" && { ok=1; break; }
      kill -0 "$rpid" 2>/dev/null || break
      sleep 1
    done
    if [ "$ok" = 1 ]; then
      sleep 2
      sudo -n perf stat \
        -e cycles,instructions,LLC-loads,LLC-load-misses,dTLB-loads,dTLB-load-misses \
        -p "$rpid" -- sleep 15 2>&1
    else
      echo "PREFILL-NOT-SEEN"
    fi
    wait "$rpid" 2>/dev/null
    kill "$watchdog" 2>/dev/null
    grep -E "average tok/s" "$DIR/perf-$name.log" || echo NO-TIMING
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2e* 2>/dev/null
grep -q "PREFILL-NOT-SEEN\|NO-TIMING" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
echo "=== p2-perf-decode done $(date -u +%FT%TZ) ==="
