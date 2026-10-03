#!/usr/bin/env bash
# i4500c-20260930 perf block (runs ON delphi-3bda, our half): why is the main thread's Save K span of the policy build
# (fixS1, 452b2052c9) still about twice the canonical build's per decode pass (105 vs 58 us at tp2 with 2 users, traces
# of 2026-09-30) while both write the same 4 lines per (token, KV head)? Recipe of block m4 of exec/issue4500-20260918/
# campaign.sh (perf_capture): runtron, qwen-3-4b tp2, 2 users, prompt 1024, 4096 generated tokens, FPGA attention;
# after every user's prefill, perf record -g 6 s on the process, then perf stat per thread. Arms: base = runtron.main0916
# (c7844ca2ce, row-major K), fixS1 = runtron.fixS1 (452b2052c9). Reports are made here with perf report (whole process
# by symbol, and the main thread = the process pid, which owns the Save K spans).
# Outputs: exec/results/i4500c-20260930/perf/<arm>/{threads.txt, perf-record.txt, perf-threads.txt, report-all.txt,
#   report-main.txt}, rt/<arm>.log, perf/perf.done; data files under /var/tmp/jhan/traces/i4500c-20260930/.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500c-20260930
RES=$EXEC/results/i4500c-20260930
LOCAL=/var/tmp/jhan/traces/i4500c-20260930
HPFILE=/dev/hugepages/amx-i4500c-perf
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
BIN_base=${BIN_base:-/var/tmp/jhan/tron-main0916/gen/runtron.main0916}
BIN_fixS1=${BIN_fixS1:-/var/tmp/jhan/tron-i4500b/gen/runtron.fixS1}
PERF_ARMS=${PERF_ARMS:-"base fixS1"}
USERS=${USERS:-2}; GEN=${GEN:-4096}
OUR_RT_RE='runtron[.a-z0-9A-Z]* .*--hugepage_file /dev/hugepages/amx-i4500c-perf'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
mkdir -p "$RES/perf" "$RES/rt" "$LOCAL"
exec >>"$RES/perf.log" 2>&1
rm -f "$RES/perf/perf.done"; gaveup=0
placement2="--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128"
arm_bin() { local v="BIN_$1"; echo "${!v:-}"; }
kill_ours() { pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; return 0; }
RT_PID=""
trap 'stop_watcher; kill_ours; remove_our_hugepage_files "$HPFILE"; campaign_guard_release 2>/dev/null' EXIT
echo "=== i4500c perf started $(ts) pid $$ arms=[$PERF_ARMS] users=$USERS gen=$GEN ==="
perf_capture() {  # ARM BIN RLOG
  local arm=$1 bin=$2 rlog=$3 pid n deadline out=$RES/perf/$arm
  mkdir -p "$out"; deadline=$(( $(date +%s) + 600 ))
  while :; do
    n=$(grep -c "Parsing the prompt took" "$rlog" 2>/dev/null || echo 0)
    [ "${n:-0}" -ge "$USERS" ] && break
    kill -0 "$RT_PID" 2>/dev/null || { echo "$(ts) perf_capture $arm: runtron exited before decode"; return 1; }
    [ "$(date +%s)" -ge "$deadline" ] && { echo "$(ts) perf_capture $arm: prefill did not finish in 600 s"; return 1; }
    sleep 0.5
  done
  sleep 3
  pid=$(pgrep -u jhan -f "^${bin} stream-generate-text" | head -1)
  [ -n "$pid" ] || { echo "$(ts) perf_capture $arm: runtron pid not found"; return 1; }
  echo "$(ts) perf_capture $arm pid=$pid: record 6 s, then per-thread counters 6 s"
  { echo "pid=$pid start=$(ts)"; for t in /proc/$pid/task/*; do echo "$(basename "$t") $(cat "$t/comm" 2>/dev/null)"; done; } >"$out/threads.txt" 2>/dev/null
  sudo -n perf record -g -F 1999 -p "$pid" -o "$LOCAL/$arm.perf.data" -- sleep 6 >"$out/perf-record.txt" 2>&1
  sudo -n chown jhan:jhan "$LOCAL/$arm.perf.data" 2>/dev/null
  sudo -n perf stat --per-thread -e cycles,instructions -p "$pid" -- sleep 6 >"$out/perf-threads.txt" 2>&1
  echo "pid=$pid" >"$out/pid.txt"
  echo "$(ts) perf_capture $arm done"
  return 0
}
for arm in $PERF_ARMS; do
  bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "$(ts) PERF-FAILED arm=$arm: $bin missing"; gaveup=1; continue; }
  rlog=$RES/rt/$arm.log; stops=0
  while :; do
    [ -s "$RES/perf/$arm/report-all.txt" ] && { echo "$(ts) perf $arm already done"; break; }
    NEED_HUGEPAGES=128 wait_clear || { echo "$(ts) blocked while waiting; perf gives up"; gaveup=1; break 2; }
    take_guard || { echo "$(ts) guard refused; perf gives up"; gaveup=1; break 2; }
    status "perf $arm"
    rm -f "$RES/perf.STOPPED"; watch_run "$RES/perf.STOPPED" "$OUR_RT_RE" "$HPFILE" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && exec env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN -u TRON_HWATTN_EARLY_LAUNCH_MIN_B TRON_LOG_LEVEL=info \
        timeout -k 60 1200 "$bin" stream-generate-text -m "$MODEL" $placement2 --hugepage_file "$HPFILE" -o --prompt-length 1024 -l "$GEN" -u "$USERS" --dont-stop) >"$rlog" 2>&1 &
    RT_PID=$!
    perf_capture "$arm" "$bin" "$rlog"; prc=$?
    # The capture is done: the rest of the 4096 tokens is not needed.
    kill -TERM "$RT_PID" 2>/dev/null; sleep 3; kill -KILL "$RT_PID" 2>/dev/null; wait "$RT_PID" 2>/dev/null; RT_PID=""
    stop_watcher; campaign_guard_release; remove_our_hugepage_files "$HPFILE"
    if [ -e "$RES/perf.STOPPED" ]; then
      echo "$(ts) PERF-STOPPED $arm $(cat "$RES/perf.STOPPED")"; stops=$((stops + 1)); [ $stops -ge 3 ] && { gaveup=1; break; }; sleep 120; continue
    fi
    [ $prc -eq 0 ] || { echo "$(ts) PERF-FAILED $arm (capture rc=$prc)"; gaveup=1; break; }
    out=$RES/perf/$arm; pid=$(sed 's/pid=//' "$out/pid.txt")
    status "perf report $arm"
    sudo -n perf report -i "$LOCAL/$arm.perf.data" --no-children --sort sym --percent-limit 0.2 --stdio 2>/dev/null | grep -v "^$" | head -150 >"$out/report-all.txt"
    sudo -n perf report -i "$LOCAL/$arm.perf.data" --no-children --tid "$pid" --sort sym --percent-limit 0.2 --stdio 2>/dev/null | grep -v "^$" | head -150 >"$out/report-main.txt"
    sudo -n perf report -i "$LOCAL/$arm.perf.data" --children --tid "$pid" --sort sym --percent-limit 0.5 --stdio 2>/dev/null | grep -v "^$" | head -120 >"$out/report-main-children.txt"
    echo "$(ts) perf $arm reports: $(wc -l <"$out/report-all.txt") / $(wc -l <"$out/report-main.txt") lines"
    break
  done
done
missing=0; for arm in $PERF_ARMS; do [ -s "$RES/perf/$arm/report-main.txt" ] || missing=$((missing + 1)); done
if [ $missing -eq 0 ] && [ $gaveup -eq 0 ]; then echo done >"$RES/perf/perf.done"; else echo "incomplete ($missing reports missing, gaveup=$gaveup)" >"$RES/perf/perf.done"; fi
status "perf finished: $(cat "$RES/perf/perf.done")"
echo "=== i4500c perf finished $(ts) ==="
