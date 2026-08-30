#!/usr/bin/env bash
# Gate 3 (revised): BEYOND the page budget - 56 users x ctx 8192 (> ~54u
# budget). Captures admission/failure semantics on both binaries; full logs.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/cap-over.txt
LOG=$EXEC/logs/p2-cap-over.log
MARKER=$EXEC/logs/p2-cap-over.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== cap-over start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
{
  echo "# Beyond-page-budget probe: 56u x ctx8192 (budget ~54u), $(date -u +%FT%TZ)"
  for arm in "runtron.inc1b canonical" "runtron.inc3arena arena-mirror"; do
    set -- $arm; bin=$1; name=$2
    echo "### arm=$name users=56"
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=0 timeout 1800 ./gen/$bin \
      stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
      --instance 0,4 --devices 10:00.0,13:00.0 \
      --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
      --numa 0 --hugepage_file /dev/hugepages/amx-co --nr_hugepages 128 -o \
      --prompt-length 8192 -l 64 -u 56 >"$DIR/capover-$name.log" 2>&1
    echo "exit=$?"
    grep -m1 -E "type=batch" "$DIR/capover-$name.log" || echo NO-SUMMARY
    grep -iE "alloc|out of|evict|fail|abort|assert" "$DIR/capover-$name.log" | head -4
  done
} >"$OUT"
rm -f /dev/hugepages/amx-co* 2>/dev/null
echo ok >"$MARKER"
echo "=== cap-over done $(date -u +%FT%TZ) ==="
