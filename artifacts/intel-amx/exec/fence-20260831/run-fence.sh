#!/usr/bin/env bash
# Fence campaign 2026-08-31: per-token fence + attention-span stamps, AMX vs kill switch.
# 1u only (jhan directive 2026-08-31: make sense of 1u first; 8u held).
# Single binary (mirror build of tron-fence-amx); arms differ only by TRON_AMX_DISABLE.
# Run ON delphi-3bda: bash ~/workspace/intel-AMX/exec/fence-20260831/run-fence.sh
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/fence-20260831; OUT=$DIR/fence.txt
LOG=$EXEC/logs/fence-20260831.log; MARKER=$EXEC/logs/fence-20260831.done
WT=~/workspace/ai-runs/tron-fence-amx
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-fence* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

echo "=== fence-20260831 start $(date -u +%FT%TZ) ==="
# Stage A: CI lease; serving must already be down (never restarted per policy).
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
# Stage B
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi

# Stage C: verify the stamped binary (built + gen-patched beforehand; no rebuild here)
BIN=$WT/gen/runtron.fence
[ -x "$BIN" ] || { echo "missing $BIN" ; echo build-missing >"$MARKER"; exit 1; }
grep -q 7603 $WT/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp \
  || { echo "gen header lost the stamps"; echo stamps-missing >"$MARKER"; exit 1; }
sha256sum "$BIN" | tee -a "$OUT"

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }

COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-fence --nr_hugepages 128 -o"

run_cell() { # arm ctx rep tmo len
  local arm=$1 ctx=$2 rep=$3 tmo=$4 len=$5
  local kv=$DIR/kvwait-$arm-c$ctx-r$rep.bin rc
  echo "### model=$MODEL arm=$arm ctx=$ctx len=$len users=1 rep=$rep kv=$(basename $kv)"
  if [ "$arm" = disable ]; then
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=1 TRON_KVWAIT_FILE=$kv timeout "$tmo" \
      "$BIN" stream-generate-text -m "$MODEL" $COMMON \
      --prompt-length "$ctx" -l "$len" -u 1 2>&1 | grep -E "Parsing the prompt took|average tok/s"
  else
    env -u TRON_AMX_DISABLE USE_HW_ATTN=0 TRON_KVWAIT_FILE=$kv timeout "$tmo" \
      "$BIN" stream-generate-text -m "$MODEL" $COMMON \
      --prompt-length "$ctx" -l "$len" -u 1 2>&1 | grep -E "Parsing the prompt took|average tok/s"
  fi
  rc=("${PIPESTATUS[@]}")
  { [ "${rc[0]}" -ne 0 ] || [ "${rc[1]}" -ne 0 ]; } && echo "RUN-FAILED rc=${rc[0]}/${rc[1]}"
  [ -s "$kv" ] || echo "KVWAIT-EMPTY $kv"
  local n; n=$(python3 -c "import struct,sys;print(struct.unpack('<Q',open('$kv','rb').read(8))[0])" 2>/dev/null || echo 0)
  echo "kvwait records: $n"
}

{ # smoke: 8 tokens, must produce records for all 5 tags
  stop_now 300 && { echo window-closed >"$MARKER"; exit 1; }
  run_cell mirror 256 0 300 8
  python3 ~/workspace/intel-AMX/exec/fence-20260831/extract.py --check $DIR/kvwait-mirror-c256-r0.bin \
    || { echo "SMOKE-FAILED: missing tags"; echo smoke-failed >"$MARKER"; exit 1; }
  echo "### smoke ok $(date -u +%FT%TZ)"
  for rep in 1 2 3; do
    for ctx in 256 2048 8192; do
      for arm in mirror disable; do
        stop_now 900 && break 3
        run_cell "$arm" "$ctx" "$rep" 900 256
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1

rm -f /dev/hugepages/amx-fence* 2>/dev/null || true
campaign_guard_release
if grep -qE "RUN-FAILED|KVWAIT-EMPTY|SMOKE-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== fence-20260831 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
