#!/usr/bin/env bash
# Fence round 3: THREE stamped arms (canonical / mirror / kill switch), 1u,
# ctx {256,2048,8192} x 2 reps x 256 tokens. Binaries come from perfstat3's
# build stage (runtron.fcanon / runtron.fmirror in its results dir).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/fence3-20260901; OUT=$DIR/fence.txt
LOG=$EXEC/logs/fence3-20260901.log; MARKER=$EXEC/logs/fence3-20260901.done
BINDIR=~/workspace/ai-runs/tron-fence-amx/gen
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-f3* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== fence3 start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1
for b in runtron.fcanon runtron.fence; do
  [ -x "$BINDIR/$b" ] || { echo missing-$b >"$MARKER"; exit 1; }
  timeout 15 "$BINDIR/$b" --help >/dev/null 2>&1 || { echo "binary wont exec: $b"; echo binary-wont-exec >"$MARKER"; exit 1; }
done
sha256sum "$BINDIR/runtron.fcanon" "$BINDIR/runtron.fence" >"$OUT"
stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-f3 --nr_hugepages 128 -o"
run_cell() { # arm ctx rep tmo len
  local arm=$1 ctx=$2 rep=$3 tmo=$4 len=$5 bin envset rc
  local kv=$DIR/kvwait-$arm-c$ctx-r$rep.bin rlog=$DIR/cell.log
  case $arm in fcanon) bin=$BINDIR/runtron.fcanon; envset="env -u TRON_AMX_DISABLE";;
               fmirror) bin=$BINDIR/runtron.fence; envset="env -u TRON_AMX_DISABLE";;
               disable) bin=$BINDIR/runtron.fence; envset="env TRON_AMX_DISABLE=1";; esac
  echo "### model=$MODEL arm=$arm ctx=$ctx len=$len users=1 rep=$rep kv=$(basename $kv)"
  $envset USE_HW_ATTN=0 TRON_KVWAIT_FILE=$kv timeout "$tmo" "$bin" stream-generate-text -m "$MODEL" $COMMON \
    --prompt-length "$ctx" -l "$len" -u 1 >"$rlog" 2>&1 &
  RUNPID=$!; wait "$RUNPID"; rc=$?; RUNPID=0
  grep -E "Parsing the prompt took|average tok/s" "$rlog"
  [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
  [ -s "$kv" ] || echo "KVWAIT-EMPTY $kv"
}
STOPPED=0
{ stop_now 300 && { echo window-closed >"$MARKER"; exit 1; }
  run_cell fmirror 256 0 300 8
  python3 $EXEC/fence-20260831/extract.py --check $DIR/kvwait-fmirror-c256-r0.bin \
    || { echo "SMOKE-FAILED"; echo smoke-failed >"$MARKER"; exit 1; }
  echo "### smoke ok"
  for rep in 1 2; do
    for ctx in 256 2048 8192; do
      for arm in fcanon fmirror disable; do
        stop_now 900 && { STOPPED=1; break 3; }
        run_cell "$arm" "$ctx" "$rep" 900 256
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
rm -f /dev/hugepages/amx-f3* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ "$STOPPED" = 1 ]; then echo stopped-early >"$MARKER"
elif grep -qE "RUN-FAILED|KVWAIT-EMPTY|SMOKE-FAILED" "$OUT"; then echo check-output >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== fence3 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
