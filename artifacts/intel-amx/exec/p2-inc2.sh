#!/usr/bin/env bash
# P2 increment 2 FULL suite: mirror-orientation binary (already built by
# p2-inc2-smoke.sh), same 18-run same-binary A/B as increments 1/1b.
# Guard: no new run at/after 02:00 UTC (inference-up timer 02:45).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-inc2.txt
LOG=$EXEC/logs/p2-inc2.log
MARKER=$EXEC/logs/p2-inc2.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-inc2 start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
ci_guard() { t=$(hhmm); [ "$t" -ge 200 ] && [ "$t" -lt 2100 ]; }

cd ~/workspace/tron-amx
RT="./gen/runtron stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2c --nr_hugepages 128 -o"
{
  echo "# P2 increment 2 (K mirror) same-binary A/B, $(date -u +%FT%TZ)"
  sha256sum gen/runtron
  for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
    for w in "2048 256 1" "8192 256 1" "2048 256 8"; do
      set -- $w
      for rep in 1 2 3; do
        if ci_guard; then echo GUARD-STOP; break 3; fi
        echo "### mode=$mode ctx=$1 len=$2 users=$3 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 $RT --prompt-length "$1" -l "$2" -u "$3" 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2c* 2>/dev/null
if grep -q GUARD-STOP "$OUT"; then echo guard-stop >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== p2-inc2 done $(date -u +%FT%TZ) ==="
