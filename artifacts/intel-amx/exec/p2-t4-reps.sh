#!/usr/bin/env bash
# Gate 5 remainder: replication for confidence intervals. 5 additional reps of
# the two most decision-relevant workloads (1u/8K, 8u/8K) on all three
# binaries (clean / canonical / arena-mirror) = 30 runs. Takes the host-wide
# campaign flock adopted from the trace-sync-points session.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/t4-reps.txt
LOG=$EXEC/logs/p2-t4-reps.log
MARKER=$EXEC/logs/p2-t4-reps.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== t4-reps start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
guard() { t=$(hhmm); [ "$t" -ge 245 ] && [ "$t" -lt 930 ]; }

exec 9>/var/tmp/jhan/3bda-campaign.lock
if ! flock -n 9; then
  echo "campaign lock held by another session - aborting"
  echo lock-held >"$MARKER"; exit 1
fi
if pgrep -x runtron >/dev/null; then
  echo "runtron already running (launch guard) - aborting"
  echo guard-runtron >"$MARKER"; exit 1
fi
echo "lock acquired $(date -u +%FT%TZ)"

cd ~/workspace/tron-amx
RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-t4r --nr_hugepages 128 -o"
{
  echo "# T4 replication: 5 extra reps x {1u/8K, 8u/8K} x 3 binaries, $(date -u +%FT%TZ)"
  sha256sum gen/runtron.clean gen/runtron.inc1b gen/runtron.inc3arena
  for arm in "runtron.clean clean TRON_AMX_DISABLE=1" \
             "runtron.inc1b canonical TRON_AMX_DISABLE=0" \
             "runtron.inc3arena arena-mirror TRON_AMX_DISABLE=0"; do
    set -- $arm; bin=$1; name=$2; mode=$3
    for w in "8192 1" "8192 8"; do
      set -- $w; ctx=$1; users=$2
      for rep in 4 5 6 7 8; do
        if guard; then echo GUARD-STOP; break 3; fi
        echo "### arm=$name ctx=$ctx len=256 users=$users rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 ./gen/$bin $RTARGS \
          --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
          | grep -E "average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-t4r* 2>/dev/null
flock -u 9
if grep -qE "GUARD-STOP|RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== t4-reps done $(date -u +%FT%TZ) ==="
