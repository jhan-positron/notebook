#!/usr/bin/env bash
# AMX dense-path fallback causes (jhan's 92.2% question). Builds the fence
# worktree (mirror config + stamps) with -DTRON_AMX_FALLBACK_COUNTERS=1, runs
# the mirror arm at ctx {256,2048,8192} (1u, 256 tokens) and keeps the
# process-exit [amx-fallback] dump per run. NOTE: leaves gen/ built WITH the
# counter flag; later fence rounds must rebuild without it.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/fallback-20260901; OUT=$DIR/fallback.txt
LOG=$EXEC/logs/fallback-20260901.log; MARKER=$EXEC/logs/fallback-20260901.done
WT=~/workspace/ai-runs/tron-fence-amx; PATCHER=$EXEC/fence-20260831/patch-gen-stamps.py
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$DIR" "$EXEC/logs"; [ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-fb* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== fallback start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1
cd "$WT"
grep -q "amx_fallback::tl" h/tron/models/self_attention.hpp || { echo instrumentation-missing >"$MARKER"; exit 1; }
PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
  "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS=-DTRON_AMX_FALLBACK_COUNTERS=1 >/dev/null" || { echo reconfig-failed >"$MARKER"; exit 1; }
python3 "$PATCHER" || { echo gen-patch-failed >"$MARKER"; exit 1; }
PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
  "set -o pipefail; cmake --build gen --target runtron -j96 2>&1 | tail -3" || { echo build-failed >"$MARKER"; exit 1; }
cp gen/runtron gen/runtron.ffb; BIN=$WT/gen/runtron.ffb
timeout 15 "$BIN" --help >/dev/null 2>&1 || { echo binary-wont-exec >"$MARKER"; exit 1; }
{ echo "### binary"; sha256sum "$BIN"; } >"$OUT"
stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }; rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/amx-fb --nr_hugepages 128 -o"
STOPPED=0
{ for ctx in 256 2048 8192; do for rep in 1 2; do
    stop_now 900 && { STOPPED=1; break 2; }
    rlog=$DIR/run-c$ctx-r$rep.log
    echo "### model=$MODEL arm=mirror ctx=$ctx len=256 users=1 rep=$rep"
    env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout 900 "$BIN" stream-generate-text -m "$MODEL" $COMMON --prompt-length "$ctx" -l 256 -u 1 >"$rlog" 2>&1 &
    RUNPID=$!; wait "$RUNPID"; rc=$?; RUNPID=0
    grep -E "Parsing the prompt took|average tok/s|\[amx-fallback\]" "$rlog"; [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
    grep -q "\[amx-fallback\]" "$rlog" || echo "NO-DUMP"
  done; done
} >>"$OUT" 2>&1
rm -f /dev/hugepages/amx-fb* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ "$STOPPED" = 1 ]; then echo stopped-early >"$MARKER"
elif grep -qE "RUN-FAILED|NO-DUMP" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== fallback end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
