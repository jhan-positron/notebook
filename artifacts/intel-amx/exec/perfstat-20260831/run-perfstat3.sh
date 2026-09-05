#!/usr/bin/env bash
# perf-stat round 3 v2 (Sol-reviewed): three arms, 1u/ctx8192, PHASE-LOCKED
# windows - fresh launch per measurement, window starts when the workload
# reaches decode token 400 (counted from the binary's stamp records), so all
# arms/groups sample the same sequence depth. Counter groups are brace groups
# of <=3 GP events (NMI watchdog holds one of the 4 GP counters; verified
# nmi_watchdog=1 on this host). Aborts if the sysctl lift fails; verifies the
# restore with retries. Requires per-run approval for the sysctl lift.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perfstat3-20260901; OUT=$DIR/perfstat3.txt
LOG=$EXEC/logs/perfstat3-20260901.log; MARKER=$EXEC/logs/perfstat3-20260901.done
WT=~/workspace/ai-runs/tron-fence-amx
PATCHER=$EXEC/fence-20260831/patch-gen-stamps.py
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
APPCORES=151-152,24-29,48-53,153-154,30-35,54-59
TOKEN_INDEX=400
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0; PARANOID_SET=0
restore_paranoid() {
  [ "$PARANOID_SET" = 1 ] || return 0
  for i in 1 2 3; do
    sudo -n sysctl -w kernel.perf_event_paranoid=4 >/dev/null 2>&1
    [ "$(cat /proc/sys/kernel/perf_event_paranoid)" = "4" ] && { echo "paranoid restored: 4" >>"$OUT"; PARANOID_SET=0; return 0; }
    sleep 2
  done
  echo "PARANOID-RESTORE-FAILED (still $(cat /proc/sys/kernel/perf_event_paranoid))" >>"$OUT"
  echo paranoid-restore-FAILED >"$MARKER.paranoid"
}
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; restore_paranoid; rm -f /dev/hugepages/amx-ps3* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

echo "=== perfstat3 v2 start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1

# Stamped binaries RUN FROM gen/ - runtron's RUNPATH is $ORIGIN-relative, so a
# copy outside the build dir cannot resolve its libraries (2026-09-01 failure).
FMIRROR=$WT/gen/runtron.fence          # mirror-config stamped
FCANON=$WT/gen/runtron.fcanon          # canon-config stamped
[ -x "$FMIRROR" ] || { echo missing-stamped-mirror >"$MARKER"; exit 1; }
cd "$WT"
if [ ! -x "$FCANON" ]; then
  PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=OFF -DCMAKE_CXX_FLAGS= >/dev/null && true" \
    || { echo reconfig-failed >"$MARKER"; exit 1; }
  python3 "$PATCHER" || { echo gen-patch-failed >"$MARKER"; exit 1; }
  grep -q "site 7605" gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp || { echo stamps-missing >"$MARKER"; exit 1; }
  PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
    "set -o pipefail; cmake --build gen --target runtron -j96 2>&1 | tail -1" \
    || { echo build-failed-fcanon >"$MARKER"; exit 1; }
  cp gen/runtron "$FCANON"
fi
for b in "$FCANON" "$FMIRROR"; do
  timeout 15 "$b" --help >/dev/null 2>&1 || { echo "binary wont exec: $b"; ldd "$b" 2>/dev/null | grep "not found"; echo binary-wont-exec >"$MARKER"; exit 1; }
done
{ echo "### binaries"; sha256sum "$FCANON" "$FMIRROR"
  echo "### nmi_watchdog: $(cat /proc/sys/kernel/nmi_watchdog)"
  echo "### paranoid before: $(cat /proc/sys/kernel/perf_event_paranoid)"; } >"$OUT"

sudo -n sysctl -w kernel.perf_event_paranoid=0 >/dev/null 2>&1 \
  && [ "$(cat /proc/sys/kernel/perf_event_paranoid)" = "0" ] \
  || { echo "sysctl lift failed" >>"$OUT"; echo sysctl-lift-failed >"$MARKER"; exit 1; }
PARANOID_SET=1; echo "### paranoid set to: 0" >>"$OUT"

# Brace groups, <=3 GP each (fixed counters: instructions/cycles/ref-cycles).
declare -A GRP
GRP[core]='{instructions,cycles,ref-cycles,cpu/event=0xc2,umask=0x02,name=uops_slots/,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/}'
GRP[dtlb_ld]='{cpu/event=0x12,umask=0x02,name=ld_walk_4k/,cpu/event=0x12,umask=0x08,name=ld_walk_1g/,cpu/event=0x12,umask=0x04,name=ld_walk_2m4m/}'
GRP[dtlb_mix]='{cpu/event=0x12,umask=0x10,cmask=1,name=ld_walk_active/,cpu/event=0x13,umask=0x02,name=st_walk_4k/,cpu/event=0x13,umask=0x08,name=st_walk_1g/}'
GRP[dtlb_tot]='{dtlb_load_misses.walk_completed,dtlb_store_misses.walk_completed}'
GRP[cache]='{cpu/event=0xd1,umask=0x08,name=l1_miss/,cpu/event=0xd1,umask=0x10,name=l2_miss/,cpu/event=0xd1,umask=0x20,name=l3_miss/}'
GRP[llc_numa]='{cpu/event=0x2e,umask=0x41,name=llc_miss/,cpu/event=0xd3,umask=0x01,name=l3m_local/,cpu/event=0xd3,umask=0x02,name=l3m_remote/}'
GRP[msr]='{msr/aperf/,msr/mperf/,msr/tsc/}'
GROUPS_CORE="core dtlb_ld dtlb_mix dtlb_tot cache llc_numa msr"

# Group smoke on idle cores: every event must count (no <not counted/supported>).
for g in $GROUPS_CORE; do
  out=$(perf stat -C 60-63 -e "${GRP[$g]}" -- sleep 1 2>&1)
  echo "$out" | grep -qE "<not counted>|<not supported>|Bad event|invalid" \
    && { echo "GROUP-SMOKE-FAILED $g"; echo "$out" | head -8; echo group-smoke-failed >"$MARKER"; exit 1; }
done >>"$OUT" 2>&1
echo "### group smoke ok" >>"$OUT"

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores $APPCORES --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-ps3 --nr_hugepages 128 -o"

wait_token() { # kvfile index -> 0 when decode token INDEX reached; 1 on death/timeout
  local kv=$1 want=$2 t0=$(date +%s) n
  while :; do
    n=$(python3 - "$kv" <<'PY' 2>/dev/null
import struct,sys
try:
    b=open(sys.argv[1],'rb').read()
    c=struct.unpack('<Q',b[:8])[0]
    print(sum(1 for i in range(min(c,(len(b)-8)//24)) if struct.unpack_from('<QQQ',b,8+24*i)[2]==7602))
except Exception: print(-1)
PY
)
    [ "${n:-0}" -ge "$want" ] 2>/dev/null && return 0
    kill -0 "$RUNPID" 2>/dev/null || { echo "RUN-DIED before token $want"; return 1; }
    [ $(( $(date +%s)-t0 )) -gt 200 ] && { echo "TOKEN-WAIT-TIMEOUT"; return 1; }
    sleep 0.5
  done
}
measure() { # arm group rep   (group=turbostat|uncore|<core group>)
  local arm=$1 g=$2 rep=$3 bin envset kv=$DIR/kv-$1-$2-r$3.bin rlog=$DIR/run-$1-$2-r$3.log rc
  case $arm in fcanon) bin=$FCANON; envset="env -u TRON_AMX_DISABLE";;
               fmirror) bin=$FMIRROR; envset="env -u TRON_AMX_DISABLE";;
               disable) bin=$FMIRROR; envset="env TRON_AMX_DISABLE=1";; esac
  echo "### arm=$arm group=$g rep=$rep token_index=$TOKEN_INDEX $(date -u +%FT%TZ)"
  $envset USE_HW_ATTN=0 TRON_KVWAIT_FILE=$kv timeout 300 "$bin" stream-generate-text -m "$MODEL" $COMMON \
    --prompt-length 8192 -l 2600 -u 1 >"$rlog" 2>&1 &
  RUNPID=$!
  wait_token "$kv" "$TOKEN_INDEX" || { kill -TERM "$RUNPID" 2>/dev/null; wait "$RUNPID" 2>/dev/null; RUNPID=0; echo "WINDOW-SKIPPED"; return 1; }
  case $g in
    turbostat) sudo -n turbostat --quiet --show Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt --interval 12 --num_iterations 1 2>&1 | awk 'NR<=2' ;;
    uncore)    perf stat -a -e 'uncore_imc/cas_count_read/,uncore_imc/cas_count_write/' -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
               rc=${PIPESTATUS[0]}; [ "$rc" -ne 0 ] && echo "PERF-FAILED rc=$rc" ;;
    *)         perf stat -C $APPCORES -e "${GRP[$g]}" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
               rc=${PIPESTATUS[0]}; [ "$rc" -ne 0 ] && echo "PERF-FAILED rc=$rc" ;;
  esac
  kill -0 "$RUNPID" 2>/dev/null || echo "RUN-ENDED-DURING-WINDOW"
  kill -TERM "$RUNPID" 2>/dev/null; wait "$RUNPID" 2>/dev/null; RUNPID=0
  rm -f "$kv"   # 400MB each; depth is in the log line below
  grep -E "average tok/s" "$rlog" | tail -1
}
{ for rep in 1 2; do
    for arm in fcanon fmirror disable; do
      for g in $GROUPS_CORE uncore turbostat; do
        stop_now 400 && break 3
        measure "$arm" "$g" "$rep" || true
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
restore_paranoid
rm -f /dev/hugepages/amx-ps3* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ -e "$MARKER.paranoid" ]; then echo paranoid-restore-FAILED >"$MARKER"
elif grep -qE "PERF-FAILED|WINDOW-SKIPPED|RUN-ENDED-DURING-WINDOW|RUN-DIED|<not counted>|<not supported>|Access to performance" "$OUT"; then echo check-output >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== perfstat3 v2 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
