#!/usr/bin/env bash
# Formulation gate 3 (capacity): canonical vs arena-mirror near the KV page
# budget (64 GB -> ~54 users at ctx 8192). Also verifies the arena insight:
# the mirror arena lives in ordinary RAM, NOT the hugepage/DMA budget, so the
# arena build's page capacity should now EQUAL canonical's.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/cap-sweep.txt
LOG=$EXEC/logs/p2-cap-sweep.log
MARKER=$EXEC/logs/p2-cap-sweep.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== cap-sweep start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
guard() { t=$(hhmm); [ "$t" -ge 245 ] && [ "$t" -lt 930 ]; }
cd ~/workspace/tron-amx
{
  echo "# Capacity sweep at ctx 8192, len 64, 1 rep, $(date -u +%FT%TZ)"
  sha256sum gen/runtron.inc1b gen/runtron.inc3arena
  for arm in "runtron.inc1b canonical" "runtron.inc3arena arena-mirror"; do
    set -- $arm; bin=$1; name=$2
    RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
      --instance 0,4 --devices 10:00.0,13:00.0 \
      --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
      --numa 0 --hugepage_file /dev/hugepages/amx-cap --nr_hugepages 128 -o"
    for users in 32 48; do
      if guard; then echo GUARD-STOP; break 2; fi
      echo "### arm=$name ctx=8192 users=$users"
      env USE_HW_ATTN=0 TRON_AMX_DISABLE=0 timeout 1800 ./gen/$bin $RTARGS \
        --prompt-length 8192 -l 64 -u "$users" >"$DIR/capsweep-$name-u$users.log" 2>&1 \
        || echo "EXIT-NONZERO"
      grep -m1 -E "type=batch" "$DIR/capsweep-$name-u$users.log" || echo NO-SUMMARY
      grep -ciE "alloc.*fail|out of memory|cannot allocate|evict" "$DIR/capsweep-$name-u$users.log" || true
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-cap* 2>/dev/null
grep -qE "GUARD-STOP|EXIT-NONZERO|NO-SUMMARY" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
echo "=== cap-sweep done $(date -u +%FT%TZ) ==="
