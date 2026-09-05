#!/usr/bin/env bash
# Extension to p2-perf-round-20260830.sh (same night): the two gpt-oss-120b
# 8-user decode cells were noisy (per-arm rep spreads up to ~13% peak to
# peak) and the mirror arm sat below the kill-switch arm in all 3 reps of
# the 2K cell. Two follow-ups:
#   1. Diagnostics: one short mirror-binary run each for gpt-oss-120b and
#      qwen (eligible control), full output captured, to read the
#      "KV cache footprint" line - it reports the K mirror arena bytes, so
#      it shows directly whether the arena is allocated for the ineligible
#      model (it must be 0.00 GB there).
#   2. Six more reps (4-9) of the two 8u cells x all three arms, arm order
#      rotated per rep, so per-rep matched ratios get real statistics.
# Binaries: gen/runtron.{canon,mirror} from tonight's main round (not rebuilt).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perf-round-20260830
OUT=$DIR/perf-round-ext.txt
LOG=$EXEC/logs/p2-perf-round-20260830-ext.log
MARKER=$EXEC/logs/p2-perf-round-20260830-ext.done
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== perf-round-ext start $(date -u +%FT%TZ) ==="
source "$EXEC/lib-guard.sh"
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-perf* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
cd ~/workspace/tron-amx || { echo missing-tree >"$MARKER"; exit 1; }
[ -x gen/runtron.canon ] && [ -x gen/runtron.mirror ] || { echo missing-binaries >"$MARKER"; exit 1; }
sha256sum gen/runtron.canon gen/runtron.mirror

stop_now() {  # $1 = the next run's timeout in seconds
  local tmo=${1:-0} now prep
  now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s)
  [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now + tmo + 300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }
  return 1
}
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-perf --nr_hugepages 128 -o"

# --- 1. footprint diagnostics (full output kept) ---
diag() {  # $1 = model, $2 = users, $3 = capture file
  env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout 900 ./gen/runtron.mirror stream-generate-text \
    -m "$1" $COMMON --prompt-length 2048 -l 16 -u "$2" >"$3" 2>&1
  echo "diag $1: rc=$? footprint lines:"
  grep -i "KV cache footprint" "$3" || echo "  (no footprint line found)"
}
diag ingested-gpt-oss-120b-tp2 8 "$DIR/diag-gptoss-mirror.txt"
diag ingested-qwen-3-4b-instruct-2507-tp2 1 "$DIR/diag-qwen-mirror.txt"

# --- 2. extension reps ---
run_arm() {  # $1 arm, $2 model, $3 ctx, $4 users, $5 timeout
  local arm=$1 model=$2 ctx=$3 users=$4 tmo=$5 bin rc
  case $arm in
    canon)   bin=./gen/runtron.canon ;;
    mirror)  bin=./gen/runtron.mirror ;;
    disable) bin=./gen/runtron.canon ;;
  esac
  if [ "$arm" = disable ]; then
    env USE_HW_ATTN=0 TRON_AMX_DISABLE=1 timeout "$tmo" $bin stream-generate-text -m "$model" $COMMON \
      --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
      | grep -E "Parsing the prompt took|average tok/s"
  else
    env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout "$tmo" $bin stream-generate-text -m "$model" $COMMON \
      --prompt-length "$ctx" -l 256 -u "$users" 2>&1 \
      | grep -E "Parsing the prompt took|average tok/s"
  fi
  rc=("${PIPESTATUS[@]}")
  if [ "${rc[0]}" -ne 0 ] || [ "${rc[1]}" -ne 0 ]; then
    echo "RUN-FAILED rc=${rc[0]}/${rc[1]}"
  fi
}
ORDERS=("disable canon mirror" "canon mirror disable" "mirror disable canon")
{
  echo "# perf round EXTENSION $(git rev-parse --short HEAD), $(date -u +%FT%TZ)"
  echo "# 6 extra reps of the two noisy gpt-oss-120b 8u cells; arm order rotated per rep."
  for rep in 4 5 6 7 8 9; do
    arms=${ORDERS[$(( rep % 3 ))]}
    for spec in "ingested-gpt-oss-120b-tp2 2048 8 1800" \
                "ingested-gpt-oss-120b-tp2 8192 8 2400"; do
      set -- $spec; model=$1; ctx=$2; users=$3; tmo=$4
      for arm in $arms; do
        if stop_now "$tmo"; then break 3; fi
        echo "### model=$model arm=$arm ctx=$ctx len=256 users=$users rep=$rep"
        run_arm "$arm" "$model" "$ctx" "$users" "$tmo"
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT"
rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
campaign_guard_release
if grep -qE "RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== perf-round-ext done $(date -u +%FT%TZ) ==="
