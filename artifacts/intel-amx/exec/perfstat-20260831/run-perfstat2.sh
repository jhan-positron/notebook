#!/usr/bin/env bash
# perf-stat round 2 (2026-08-31, jhan-approved sysctl lift): three arms, 1u/ctx8192.
# Sets kernel.perf_event_paranoid=0 for the campaign and ALWAYS restores 4 (EXIT trap).
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/perfstat2-20260831; OUT=$DIR/perfstat2.txt
LOG=$EXEC/logs/perfstat2-20260831.log; MARKER=$EXEC/logs/perfstat2-20260831.done
WT=~/workspace/tron-amx
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
APPCORES=151-152,24-29,48-53,153-154,30-35,54-59
mkdir -p "$DIR" "$EXEC/logs"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
PARANOID_SET=0
restore_paranoid() {
  if [ "$PARANOID_SET" = 1 ]; then
    sudo -n sysctl -w kernel.perf_event_paranoid=4 >/dev/null 2>&1
    echo "paranoid restored: $(cat /proc/sys/kernel/perf_event_paranoid)" >>"$OUT"
    PARANOID_SET=0
  fi
}
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; restore_paranoid; rm -f /dev/hugepages/amx-pstat* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== perfstat2 start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
for b in runtron.canon runtron.mirror; do [ -x $WT/gen/$b ] || { echo missing-$b >"$MARKER"; exit 1; }; done

{ echo "### binaries"; sha256sum $WT/gen/runtron.canon $WT/gen/runtron.mirror
  echo "### paranoid before: $(cat /proc/sys/kernel/perf_event_paranoid)"; } >"$OUT"
if sudo -n sysctl -w kernel.perf_event_paranoid=0 >/dev/null 2>&1; then
  PARANOID_SET=1; echo "### paranoid set to: $(cat /proc/sys/kernel/perf_event_paranoid)" >>"$OUT"
else
  echo "### SUDO-SYSCTL-FAILED - perf windows will fail" >>"$OUT"
fi

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }

G1="instructions,cycles,ref-cycles,cpu/event=0xc2,umask=0x02,name=uops_retired_slots/,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/"
G2="cpu/event=0x12,umask=0x02,name=dtlb_ld_walk_4k/,cpu/event=0x12,umask=0x08,name=dtlb_ld_walk_1g/,cpu/event=0x12,umask=0x04,name=dtlb_ld_walk_2m4m/,cpu/event=0x12,umask=0x10,cmask=1,name=dtlb_ld_walk_active/"
G3="dtlb_load_misses.walk_completed,dtlb_store_misses.walk_completed,cpu/event=0x13,umask=0x02,name=dtlb_st_walk_4k/,cpu/event=0x13,umask=0x08,name=dtlb_st_walk_1g/"
G4="uncore_imc/cas_count_read/,uncore_imc/cas_count_write/"
G5="msr/aperf/,msr/mperf/,msr/tsc/"
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores $APPCORES --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-pstat --nr_hugepages 128 -o"

RPID=0; RLOG=""
launch_run() { # arm
  local arm=$1 bin envset
  case $arm in canon) bin=$WT/gen/runtron.canon; envset="env -u TRON_AMX_DISABLE";;
               mirror) bin=$WT/gen/runtron.mirror; envset="env -u TRON_AMX_DISABLE";;
               disable) bin=$WT/gen/runtron.mirror; envset="env TRON_AMX_DISABLE=1";; esac
  RLOG=$DIR/runtron-$arm-$(date -u +%H%M%S).log
  $envset USE_HW_ATTN=0 timeout 600 $bin stream-generate-text -m $MODEL $COMMON \
    --prompt-length 8192 -l 8192 -u 1 >"$RLOG" 2>&1 &
  RPID=$!
  local t0=$(date +%s)
  until grep -q "Parsing the prompt took" "$RLOG" 2>/dev/null; do
    sleep 2; kill -0 $RPID 2>/dev/null || { echo "RUN-DIED-EARLY"; tail -2 "$RLOG"; return 1; }
    [ $(( $(date +%s)-t0 )) -gt 240 ] && { echo "PREFILL-TIMEOUT"; kill $RPID; return 1; }
  done
  sleep 3
}
ensure_decoding() { # arm - relaunch if the run ended (EOS) mid-windows
  kill -0 $RPID 2>/dev/null && return 0
  echo "(run ended early - relaunching $1 for remaining windows)"
  grep -E "average tok/s" "$RLOG"
  launch_run "$1"
}
run_arm() { # arm rep
  local arm=$1 rep=$2
  echo "### arm=$arm rep=$rep ctx=8192 users=1 len=8192 $(date -u +%FT%TZ)"
  launch_run "$arm" || return 1
  for g in 1 2 3 5; do
    ensure_decoding "$arm" || return 1
    eval ev=\$G$g
    echo "--- group G$g cores=$APPCORES window=12s"
    perf stat -C $APPCORES -e "$ev" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  done
  ensure_decoding "$arm" || return 1
  echo "--- group G4 (uncore, system-wide) window=12s"
  perf stat -a -e "$G4" -- sleep 12 2>&1 | grep -vE "^\s*$|Performance counter|time elapsed"
  ensure_decoding "$arm" || return 1
  echo "--- turbostat window=12s (app-core rows + package)"
  sudo -n turbostat --quiet --show Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt --interval 12 --num_iterations 1 2>&1 | awk 'NR<=2 || $2 ~ /^(24|25|26|27|28|29|30|31|32|33|34|35|48|49|50|51|52|53|54|55|56|57|58|59|151|152|153|154)$/' | head -40
  wait $RPID 2>/dev/null
  grep -E "average tok/s" "$RLOG" | tail -1
}
{ for rep in 1 2; do
    for arm in canon mirror disable; do
      stop_now 700 && break 2
      run_arm $arm $rep
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
restore_paranoid
rm -f /dev/hugepages/amx-pstat* 2>/dev/null || true
campaign_guard_release
if grep -qE "Access to performance monitoring|SUDO-SYSCTL-FAILED|RUN-DIED-EARLY|PREFILL-TIMEOUT|not supported|<not" "$OUT"; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== perfstat2 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
