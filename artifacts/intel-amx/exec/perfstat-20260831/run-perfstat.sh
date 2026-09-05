#!/usr/bin/env bash
# perf-stat round 2026-08-31: three arms (canon / mirror / disable), 1u/ctx8192.
# Event names verified against intel/perfmon GNR JSON; missing-from-kernel events
# use raw encodings. AMX_OPS_RETIRED / CORE_POWER.LVL*_TURBO_LICENSE do not exist
# in the GNR event list - frequency comes from cycles vs ref-cycles + msr PMU.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perfstat-20260831; OUT=$DIR/perfstat.txt
LOG=$EXEC/logs/perfstat-20260831.log; MARKER=$EXEC/logs/perfstat-20260831.done
WT=~/workspace/tron-amx
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
APPCORES=151-152,24-29,48-53,153-154,30-35,54-59
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-pstat* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== perfstat-20260831 start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
for b in runtron.canon runtron.mirror; do [ -x $WT/gen/$b ] || { echo missing-$b >"$MARKER"; exit 1; }; done

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }

{ echo "### host topology"; numactl -H 2>/dev/null | head -4; grep -h . /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
  echo "### binaries"; sha256sum $WT/gen/runtron.canon $WT/gen/runtron.mirror; } >>"$OUT"

G1="instructions,cycles,ref-cycles,cpu/event=0xc2,umask=0x02,name=uops_retired_slots/,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/"
G2="cpu/event=0x12,umask=0x02,name=dtlb_ld_walk_4k/,cpu/event=0x12,umask=0x08,name=dtlb_ld_walk_1g/,cpu/event=0x12,umask=0x04,name=dtlb_ld_walk_2m4m/,cpu/event=0x12,umask=0x10,cmask=1,name=dtlb_ld_walk_active/"
G3="dtlb_load_misses.walk_completed,dtlb_store_misses.walk_completed,cpu/event=0x13,umask=0x02,name=dtlb_st_walk_4k/,cpu/event=0x13,umask=0x08,name=dtlb_st_walk_1g/"
G4="uncore_imc/cas_count_read/,uncore_imc/cas_count_write/"
G5="msr/aperf/,msr/mperf/,msr/tsc/"

COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores $APPCORES --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-pstat --nr_hugepages 128 -o"

run_arm() { # arm rep
  local arm=$1 rep=$2 bin envset rlog=$DIR/runtron-$1-r$2.log
  case $arm in canon) bin=$WT/gen/runtron.canon; envset="env -u TRON_AMX_DISABLE";;
               mirror) bin=$WT/gen/runtron.mirror; envset="env -u TRON_AMX_DISABLE";;
               disable) bin=$WT/gen/runtron.mirror; envset="env TRON_AMX_DISABLE=1";; esac
  echo "### arm=$arm rep=$rep ctx=8192 users=1 len=8192 $(date -u +%FT%TZ)"
  $envset USE_HW_ATTN=0 timeout 600 $bin stream-generate-text -m $MODEL $COMMON \
    --prompt-length 8192 -l 8192 -u 1 >"$rlog" 2>&1 &
  local rpid=$!
  local t0=$(date +%s)
  until grep -q "Parsing the prompt took" "$rlog" 2>/dev/null; do
    sleep 2; kill -0 $rpid 2>/dev/null || { echo "RUN-DIED-EARLY"; cat "$rlog" | tail -3; return 1; }
    [ $(( $(date +%s)-t0 )) -gt 240 ] && { echo "PREFILL-TIMEOUT"; kill $rpid; return 1; }
  done
  sleep 3   # settle into steady decode
  for g in 1 2 3 5; do
    eval ev=\$G$g
    echo "--- group G$g cores=$APPCORES window=12s"
    perf stat -C $APPCORES -e "$ev" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  done
  echo "--- group G4 (uncore, system-wide) window=12s"
  perf stat -a -e "$G4" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  wait $rpid
  grep -E "average tok/s" "$rlog"
}

{ for rep in 1 2; do
    for arm in canon mirror disable; do
      stop_now 700 && break 2
      run_arm $arm $rep
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
rm -f /dev/hugepages/amx-pstat* 2>/dev/null || true
campaign_guard_release
grep -qE "RUN-DIED-EARLY|PREFILL-TIMEOUT|not supported|<not|Access to performance monitoring" "$OUT" && echo check-output >"$MARKER" || echo ok >"$MARKER"
echo "=== perfstat-20260831 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
