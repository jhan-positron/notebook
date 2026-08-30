#!/usr/bin/env bash
# Row 16 first item (Sol-requested): the heavy 8-user/ctx-8192 point, on the
# preserved inc-1b (canonical) and inc-2 (mirror) binaries, both kill-switch
# modes, 2 reps (time-boxed to tonight's window). Guard: no new run at/after
# 02:50 UTC; abort if rinzler serving comes up (02:45 timer).
set -u
EXEC=~/workspace/intel-AMX/exec
OUT=$EXEC/results/slot1/p2-8u8k.txt
LOG=$EXEC/logs/p2-8u8k.log
MARKER=$EXEC/logs/p2-8u8k.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== p2-8u8k start $(date -u +%FT%TZ) ==="
hhmm() { echo $((10#$(date -u +%H%M))); }
stop_now() {
  t=$(hhmm)
  { [ "$t" -ge 250 ] && [ "$t" -lt 2100 ]; } && return 0
  systemctl is-active --quiet rinzler@0 && return 0
  return 1
}

cd ~/workspace/tron-amx
RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-p2f --nr_hugepages 128 -o"
{
  echo "# 8u/ctx8192 point, canonical (inc-1b) vs mirror (inc-2) binaries, $(date -u +%FT%TZ)"
  sha256sum gen/runtron.inc1b gen/runtron.inc2mir
  for pair in "gen/runtron.inc1b canonical" "gen/runtron.inc2mir mirror"; do
    set -- $pair; bin=$1; name=$2
    for mode in "TRON_AMX_DISABLE=1" "TRON_AMX_DISABLE=0"; do
      for rep in 1 2; do
        if stop_now; then echo GUARD-STOP; break 3; fi
        echo "### bin=$name mode=$mode ctx=8192 len=256 users=8 rep=$rep"
        env USE_HW_ATTN=0 $mode timeout 900 ./$bin $RTARGS \
          --prompt-length 8192 -l 256 -u 8 2>&1 \
          | grep -E "Parsing the prompt took|average tok/s" || echo RUN-FAILED
      done
    done
  done
} >"$OUT"
rm -f /dev/hugepages/amx-p2f* 2>/dev/null
if grep -q "GUARD-STOP\|RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== p2-8u8k done $(date -u +%FT%TZ) ==="
