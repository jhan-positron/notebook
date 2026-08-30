#!/usr/bin/env bash
# T4 power stage retry: turbostat --Summary (PkgWatt confirmed present) during
# the decode phase of an 8u/8K run, per arm, plus an idle baseline.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/t4
OUT=$DIR/t4-power.txt
LOG=$EXEC/logs/p2-t4-power.log
MARKER=$EXEC/logs/p2-t4-power.done
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== t4-power start $(date -u +%FT%TZ) ==="
cd ~/workspace/tron-amx
RTARGS="stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
  --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-t4p --nr_hugepages 128 -o"
{
  echo "# T4 power capture (turbostat --Summary, 5s intervals), $(date -u +%FT%TZ)"
  echo "### idle baseline"
  sudo -n turbostat --quiet --Summary --show Avg_MHz,Bzy_MHz,PkgWatt --interval 5 --num_iterations 4 2>/dev/null
  for arm in "runtron.clean clean TRON_AMX_DISABLE=1" \
             "runtron.inc1b canonical-amx TRON_AMX_DISABLE=0" \
             "runtron.inc2mir mirror-amx TRON_AMX_DISABLE=0"; do
    set -- $arm; bin=$1; name=$2; mode=$3
    echo "### power arm=$name ctx=8192 users=8 len=512"
    env USE_HW_ATTN=0 $mode timeout 900 ./gen/$bin $RTARGS \
      --prompt-length 8192 -l 512 -u 8 >"$DIR/power2-$name.log" 2>&1 &
    rpid=$!
    # wait until decode has started (prefill line present), then sample 40 s
    for i in $(seq 1 120); do
      grep -q "Parsing the prompt took" "$DIR/power2-$name.log" && break
      kill -0 "$rpid" 2>/dev/null || break
      sleep 1
    done
    sleep 3
    sudo -n turbostat --quiet --Summary --show Avg_MHz,Bzy_MHz,PkgWatt --interval 5 --num_iterations 8 2>/dev/null
    wait "$rpid" 2>/dev/null
    grep -m1 -E "average tok/s" "$DIR/power2-$name.log" || echo NO-TIMING
  done
} >"$OUT"
rm -f /dev/hugepages/amx-t4p* 2>/dev/null
echo ok >"$MARKER"
echo "=== t4-power done $(date -u +%FT%TZ) ==="
