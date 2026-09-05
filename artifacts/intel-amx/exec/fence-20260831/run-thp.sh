#!/usr/bin/env bash
# THP experiment on the K mirror arena: same stamped mirror binary, arms
# base (default) vs thp (TRON_AMX_MIRROR_THP=1). Part A: fence grid (period +
# 7605 attention) at ctx {2048,8192} x 3 reps. Part B: phase-locked counters
# (dtlb_ld + core groups) at 1u/8K, 2 reps. THP take-up verified per run from
# /proc/<pid>/smaps_rollup AnonHugePages. Sysctl lift: standing approval.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/thp-20260901; OUT=$DIR/thp.txt
LOG=$EXEC/logs/thp-20260901.log; MARKER=$EXEC/logs/thp-20260901.done
WT=~/workspace/ai-runs/tron-fence-amx; PATCHER=$EXEC/fence-20260831/patch-gen-stamps.py
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
APPCORES=151-152,24-29,48-53,153-154,30-35,54-59
mkdir -p "$DIR" "$EXEC/logs"; [ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0; PARANOID_SET=0
restore_paranoid() { [ "$PARANOID_SET" = 1 ] || return 0
  for i in 1 2 3; do sudo -n sysctl -w kernel.perf_event_paranoid=4 >/dev/null 2>&1
    [ "$(cat /proc/sys/kernel/perf_event_paranoid)" = "4" ] && { echo "paranoid restored: 4" >>"$OUT"; PARANOID_SET=0; return 0; }; sleep 2; done
  echo paranoid-restore-FAILED >"$MARKER.paranoid"; }
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; restore_paranoid; rm -f /dev/hugepages/amx-thp* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== thp start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1
# build: mirror config + stamps (gen currently holds the canon config)
cd "$WT"
grep -q "TRON_AMX_MIRROR_THP" h/tron/models/kv_cache.hpp || { echo thp-patch-missing >"$MARKER"; exit 1; }
PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
  "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DCMAKE_CXX_FLAGS= >/dev/null" || { echo reconfig-failed >"$MARKER"; exit 1; }
python3 "$PATCHER" || { echo gen-patch-failed >"$MARKER"; exit 1; }
grep -q "site 7605" gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp || { echo stamps-missing >"$MARKER"; exit 1; }
PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
  "set -o pipefail; cmake --build gen --target runtron -j96 2>&1 | tail -1" || { echo build-failed >"$MARKER"; exit 1; }
cp gen/runtron gen/runtron.fthp
BIN=$WT/gen/runtron.fthp
timeout 15 "$BIN" --help >/dev/null 2>&1 || { echo binary-wont-exec >"$MARKER"; exit 1; }
{ echo "### binary"; sha256sum "$BIN"; echo "### thp policy: $(cat /sys/kernel/mm/transparent_hugepage/enabled)"; echo "### paranoid before: $(cat /proc/sys/kernel/perf_event_paranoid)"; } >"$OUT"
stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }; rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 --app-cores $APPCORES --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/amx-thp --nr_hugepages 128 -o"
envfor() { [ "$1" = thp ] && echo "env TRON_AMX_MIRROR_THP=1" || echo "env -u TRON_AMX_MIRROR_THP"; }
thp_kb() { local p; p=$(pgrep -P "$1" -x runtron 2>/dev/null | head -1); p=${p:-$(pgrep -P "$1" 2>/dev/null | head -1)}; grep AnonHugePages /proc/${p:-$1}/smaps_rollup 2>/dev/null | awk "{print \$2}"; }
# ---- Part A: fence grid ----
run_cell() { # arm ctx rep
  local arm=$1 ctx=$2 rep=$3 kv=$DIR/kvwait-$arm-c$ctx-r$rep.bin rlog=$DIR/cell.log rc
  echo "### model=$MODEL arm=$arm ctx=$ctx len=256 users=1 rep=$rep kv=$(basename $kv)"
  $(envfor $arm) USE_HW_ATTN=0 TRON_KVWAIT_FILE=$kv timeout 900 "$BIN" stream-generate-text -m "$MODEL" $COMMON --prompt-length "$ctx" -l 256 -u 1 >"$rlog" 2>&1 &
  RUNPID=$!
  ( sleep 20; echo "AnonHugePages_kB_at20s=$(thp_kb $RUNPID)" ) &
  wait "$RUNPID"; rc=$?; RUNPID=0; wait
  grep -E "Parsing the prompt took|average tok/s" "$rlog"; [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"; [ -s "$kv" ] || echo "KVWAIT-EMPTY"
}
STOPPED=0
{ echo "### PART A fence grid"
  for rep in 1 2 3; do for ctx in 2048 8192; do for arm in base thp; do
    stop_now 900 && { STOPPED=1; break 3; }; run_cell $arm $ctx $rep; done; done
    echo "### rep $rep complete $(date -u +%FT%TZ)"; done
} >>"$OUT" 2>&1
# ---- Part B: phase-locked counters ----
if [ "$STOPPED" = 0 ]; then
  sudo -n sysctl -w kernel.perf_event_paranoid=0 >/dev/null 2>&1 && [ "$(cat /proc/sys/kernel/perf_event_paranoid)" = "0" ] \
    || { echo sysctl-lift-failed >"$MARKER"; exit 1; }
  PARANOID_SET=1; echo "### paranoid set to: 0" >>"$OUT"
  declare -A GRP
  GRP[core]='{instructions,cycles,ref-cycles,cpu/event=0xc2,umask=0x02,name=uops_slots/,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/}'
  GRP[dtlb_ld]='{cpu/event=0x12,umask=0x02,name=ld_walk_4k/,cpu/event=0x12,umask=0x08,name=ld_walk_1g/,cpu/event=0x12,umask=0x04,name=ld_walk_2m4m/}'
  GRP[dtlb_mix]='{cpu/event=0x12,umask=0x10,cmask=1,name=ld_walk_active/,cpu/event=0x13,umask=0x02,name=st_walk_4k/,cpu/event=0x13,umask=0x04,name=st_walk_2m4m/}'
  wait_token() { local kv=$1 want=$2 t0=$(date +%s) n
    while :; do n=$(python3 -c "
import struct,sys
try:
    b=open(sys.argv[1],'rb').read(); c=struct.unpack('<Q',b[:8])[0]
    print(sum(1 for i in range(min(c,(len(b)-8)//24)) if struct.unpack_from('<QQQ',b,8+24*i)[2]==7602))
except Exception: print(-1)" "$kv" 2>/dev/null)
      [ "${n:-0}" -ge "$want" ] 2>/dev/null && return 0
      kill -0 "$RUNPID" 2>/dev/null || { echo "RUN-DIED before token $want"; return 1; }
      [ $(( $(date +%s)-t0 )) -gt 200 ] && { echo "TOKEN-WAIT-TIMEOUT"; return 1; }; sleep 0.5; done; }
  measure() { # arm group rep
    local arm=$1 g=$2 rep=$3 kv=$DIR/kv-$1-$2-r$3.bin rlog=$DIR/run-$1-$2-r$3.log rc
    echo "### arm=$arm group=$g rep=$rep token_index=400 $(date -u +%FT%TZ)"
    $(envfor $arm) USE_HW_ATTN=0 TRON_KVWAIT_FILE=$kv timeout 300 "$BIN" stream-generate-text -m "$MODEL" $COMMON --prompt-length 8192 -l 2600 -u 1 >"$rlog" 2>&1 &
    RUNPID=$!
    wait_token "$kv" 400 || { kill -TERM "$RUNPID" 2>/dev/null; wait "$RUNPID" 2>/dev/null; RUNPID=0; echo WINDOW-SKIPPED; return 1; }
    echo "AnonHugePages_kB=$(thp_kb $RUNPID)"
    perf stat -C $APPCORES -e "${GRP[$g]}" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"; rc=${PIPESTATUS[0]}; [ "$rc" -ne 0 ] && echo "PERF-FAILED rc=$rc"
    kill -0 "$RUNPID" 2>/dev/null || echo RUN-ENDED-DURING-WINDOW
    kill -TERM "$RUNPID" 2>/dev/null; wait "$RUNPID" 2>/dev/null; RUNPID=0; rm -f "$kv"
    grep -E "average tok/s" "$rlog" | tail -1
  }
  { echo "### PART B counters"; for rep in 1 2; do for arm in base thp; do for g in core dtlb_ld dtlb_mix; do
      stop_now 400 && break 3; measure $arm $g $rep || true; done; done; done
  } >>"$OUT" 2>&1
  restore_paranoid
fi
rm -f /dev/hugepages/amx-thp* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ -e "$MARKER.paranoid" ]; then echo paranoid-restore-FAILED >"$MARKER"
elif [ "$STOPPED" = 1 ]; then echo stopped-early >"$MARKER"
elif grep -qE "RUN-FAILED|KVWAIT-EMPTY|PERF-FAILED|WINDOW-SKIPPED|RUN-ENDED-DURING|<not counted>|Access to performance" "$OUT"; then echo check-output >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== thp end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
