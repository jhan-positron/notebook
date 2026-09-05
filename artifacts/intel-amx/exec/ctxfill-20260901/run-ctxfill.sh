#!/usr/bin/env bash
# Context-axis fill v2 (Sol-reviewed 2026-09-01, NO-GO fixes applied):
#  P0: observability fails CLOSED; lock acquired (--allow-serving) BEFORE any
#      serving inspection/stop; cleanup kills only the tracked runtron PID.
#  P1: clock/CI truncation -> marker stopped-early, never ok; both binaries
#      built fresh from one pinned commit in separate local build dirs;
#      balanced context order (two Latin squares) + unmeasured warmups.
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/ctxfill-20260901; OUT=$DIR/ctxfill.txt
LOG=$EXEC/logs/ctxfill-20260901.log; MARKER=$EXEC/logs/ctxfill-20260901.done
SRC=~/workspace/tron-amx
PIN_COMMIT=60d66d9c04428d907069ced375b93265add02db7   # jhan-amx-p0 as measured tonight
WTC=/var/tmp/jhan/ctxfill-clean; WTM=/var/tmp/jhan/ctxfill-mirror
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-ctxf* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

echo "=== ctxfill v2 queued-start $(date -u +%FT%TZ); sleeping until 09:15Z ==="
while [ "$(date -u +%s)" -lt "$(date -u -d 'today 09:15' +%s)" ]; do sleep 600; done
echo "=== 09:15Z reached; waiting for CI lease release ==="
wait_for_ci_release 21600 || { echo ci-never-released >"$MARKER"; exit 1; }

# P0 fix: take the campaign lock FIRST (serving may still be up), then inspect.
if ! campaign_guard_acquire --allow-serving; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1

# Serving state, fail-closed: each privileged READ must itself succeed (rc 0)
# before anything is counted; counting greps run on the captured file, where
# a zero count is a legitimate result. Any read failure aborts WITHOUT
# touching serving.
fail_closed() { echo "OBSERVABILITY-FAILED: $1"; echo observability-failed >"$MARKER"; exit 1; }
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  quiet=0; JLOG=$DIR/journal-window.txt; SSLOG=$DIR/ss-window.txt
  for try in 1 2 3 4 5 6 7 8; do
    ci_took_dut && { echo "CI re-took the DUT"; echo stopped >"$MARKER"; exit 1; }
    sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager >"$JLOG" 2>/dev/null       || fail_closed "journalctl rc=$?"
    [ -s "$JLOG" ] || fail_closed "journal window empty while rinzler units are active"
    sudo -n ss -Htn state established       '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' >"$SSLOG" 2>/dev/null       || fail_closed "ss rc=$?"
    traffic=$(grep -vE '#EVT# (SYSTEM_STATS|Harvester stats)' "$JLOG" | grep -icE 'session|request|prompt|generat|token' || true)
    busy_hb=$(grep -cE '#EVT# SYSTEM_STATS:.*Busy=[1-9]' "$JLOG" || true)
    conns=$(awk '$4 !~ /^127\.0\.0\.1:/' "$SSLOG" | wc -l)
    [[ "$traffic" =~ ^[0-9]+$ && "$busy_hb" =~ ^[0-9]+$ && "$conns" =~ ^[0-9]+$ ]] || fail_closed "non-numeric counts t=$traffic b=$busy_hb c=$conns"
    if [ "$conns" -ne 0 ] || [ "$busy_hb" -ne 0 ]; then
      echo "rinzler in use (conns=$conns busy_hb=$busy_hb) - not touching it"; echo serving-in-use >"$MARKER"; exit 1
    fi
    [ "$traffic" -eq 0 ] && { quiet=1; break; }
    echo "try $try: journal lines=$traffic - waiting 300s"; sleep 300
  done
  [ "$quiet" -eq 1 ] || { echo serving-quiet-timeout >"$MARKER"; exit 1; }
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
  sleep 5
  if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then rm -f /dev/hugepages/slice-*-of-8; fi
fi

# P1 fix: both arms from one pinned commit, separate local build dirs.
build_arm() { # worktree k_mirror dispatch name
  local wt=$1 km=$2 disp=$3 name=$4
  cd "$SRC" || return 1
  git worktree remove --force "$wt" 2>/dev/null; rm -rf "$wt"
  git worktree add --detach "$wt" "$PIN_COMMIT" >/dev/null || return 1
  cd "$wt" || return 1
  PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=$disp -DTRON_AMX_K_MIRROR=$km -DCMAKE_CXX_FLAGS= >/dev/null && cmake --build gen --target runtron -j96 2>&1 | tail -1" || return 1
  cp gen/runtron "gen/runtron.$name" || return 1
  grep -E "^TRON_AMX" gen/CMakeCache.txt | sed "s/^/cache[$name] /"
}
{ echo "### provenance"; echo "commit $PIN_COMMIT"; uname -r; date -u +%FT%TZ; } >"$OUT"
build_arm "$WTC" OFF OFF clean  >>"$OUT" 2>&1 || { echo build-failed-clean  >"$MARKER"; exit 1; }
build_arm "$WTM" ON  ON  mirror >>"$OUT" 2>&1 || { echo build-failed-mirror >"$MARKER"; exit 1; }
cmp -s "$WTC/gen/runtron.clean" "$WTM/gen/runtron.mirror" && { echo build-identical >"$MARKER"; exit 1; }
{ sha256sum "$WTC/gen/runtron.clean" "$WTM/gen/runtron.mirror"
  echo "### topology"; lscpu -e=CPU,NODE,SOCKET,CORE 2>/dev/null | awk 'NR==1 || $1 ~ /^(24|29|30|35|48|53|54|59|151|154)$/'
  for n in 0 1; do echo "node$n 1G hugepages free: $(cat /sys/devices/system/node/node$n/hugepages/hugepages-1048576kB/free_hugepages 2>/dev/null)"; done; } >>"$OUT"

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-ctxf --nr_hugepages 128 -o"
run_cell() { # arm ctx rep tmo label
  local arm=$1 ctx=$2 rep=$3 tmo=$4 label=$5 bin rc rlog=$DIR/cell.log
  case $arm in clean) bin=$WTC/gen/runtron.clean;; mirror) bin=$WTM/gen/runtron.mirror;; esac
  echo "### model=$MODEL arm=$arm ctx=$ctx len=256 users=1 rep=$rep label=$label"
  env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout "$tmo" "$bin" stream-generate-text -m "$MODEL" $COMMON \
    --prompt-length "$ctx" -l 256 -u 1 >"$rlog" 2>&1 &
  RUNPID=$!
  wait "$RUNPID"; rc=$?
  RUNPID=0
  grep -E "Parsing the prompt took|average tok/s" "$rlog"
  [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
}
CTXS=(256 512 1024 4096 16384)
ORDERS=("0 1 2 3 4" "1 2 3 4 0" "2 3 4 0 1" "3 4 0 1 2" "4 3 2 1 0" "0 4 3 2 1" "1 0 4 3 2" "2 1 0 4 3")
STOPPED=0
{ echo "### warmups (unmeasured)"
  run_cell clean 2048 0 300 warmup; run_cell mirror 2048 0 300 warmup
  for rep in 1 2 3 4 5 6 7 8; do
    if [ $((rep % 2)) -eq 1 ]; then ARMS="clean mirror"; else ARMS="mirror clean"; fi
    for ix in ${ORDERS[$((rep-1))]}; do
      ctx=${CTXS[$ix]}; tmo=300; [ "$ctx" -ge 4096 ] && tmo=600
      for arm in $ARMS; do
        stop_now "$tmo" && { STOPPED=1; break 3; }
        run_cell "$arm" "$ctx" "$rep" "$tmo" grid
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
rm -f /dev/hugepages/amx-ctxf* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ "$STOPPED" = 1 ]; then echo stopped-early >"$MARKER"
elif grep -qE "RUN-FAILED" "$OUT"; then echo check-output >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== ctxfill v2 end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
