#!/usr/bin/env bash
# jeremy-measure-20260831: the measurements behind the replies to PR3879
# review threads r3858305362 (eager tile region + Q pack) and r3858305367
# (packed-Q alignment), plus build+test of the qpack alignment fix.
#
# Runs ON delphi-3bda only (tile instructions + FPGAs + the CI lease live
# there). Home is NFS-shared, so this file and all results are visible on the
# agent host at the same paths.
#
# Stages (each behind the CI lease + campaign guard):
#   0  wait for CI to release the DUT, then acquire the campaign guard
#   1  tron-amx (jhan-amx-p0 + uncommitted qpack-alignment fix in the working
#      tree): build + run t_amx_mirror t_amx_numerics t_amx_arena_leak
#      t_amx_dispatch_dtype t_llama_unit
#   2  microbenches linking the REAL kernel TU: bench_qpack (pack cost on the
#      6962P) and bench_qk_align (qk_mirror per page, packed-Q base 0 vs 16
#      mod 64)
#   3  counter run: tron-dd (jhan-dd-debug @ 8d02eaba8c, per-call dispatch
#      counters) mirror build; qwen-3-4b decode cells; AMX-DEBUG exit lines
#      answer "how often is the eager setup pure overhead"
set -u
EXEC=~/workspace/intel-AMX/exec
DIR=$EXEC/results/jeremy-measure-20260831
LOG=$EXEC/logs/jeremy-measure-20260831.log
MARKER=$EXEC/logs/jeremy-measure-20260831.done
mkdir -p "$EXEC/logs" "$EXEC/results"
[ -d "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ] && \
  mv "$DIR" "$DIR.prev.$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== jeremy-measure start $(date -u +%FT%TZ) host=$(hostname) ==="
source "$EXEC/lib-guard.sh"
FAIL=0
trap '[ -e "$MARKER" ] || { pkill -TERM -f "gen/runtron\." 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-perf* 2>/dev/null; campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT

# ---- Stage 0: wait out CI, then take the guard --------------------------
if ci_lease_busy; then
  echo "CI lease busy at start; waiting (poll 300s, timeout 12h)"
  wait_for_ci_release 43200 || { echo ci-wait-timeout >"$MARKER"; exit 1; }
fi
# Lookahead (epoch arithmetic, evening-safe): the campaign needs ~1 h; refuse
# a start that would cross the next 03:30Z CI prep.
now=$(date -u +%s)
next_prep=$(date -u -d "$(date -u +%F) 03:30" +%s)
[ "$now" -ge "$next_prep" ] && next_prep=$(date -u -d "$(date -u +%F) 03:30 tomorrow" +%s)
if [ $((now + 3600)) -gt "$next_prep" ]; then
  echo "too close to the next 03:30Z CI prep ($(date -u -d @$next_prep +%FT%TZ)) - not starting"
  echo ci-prep-too-close >"$MARKER"; exit 1
fi

# Stage A (perf-round-20260830 reviewed procedure): stop rinzler serving only
# if it is verifiably idle; never restart it afterwards (jhan's policy).
# Right after CI releases, the 10-minute journal window still holds CI's own
# request storm (observed: 61473 lines at 11:36Z with zero remote clients), so
# the idle check is retried until the window is clean - the criteria themselves
# are unchanged. Remote connections > 0 means a real user: bail immediately.
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  # Amendment to the reviewed check (discovered 2026-08-31, see the campaign
  # report): idle rinzlers emit periodic '#EVT# SYSTEM_STATS' / 'Harvester
  # stats' heartbeat lines whose text matches the keyword grep even at
  # Sessions Open=0 Busy=0, so the raw count never reaches zero. The heartbeats
  # are excluded from the traffic count, and instead any heartbeat reporting
  # Busy>0 counts as in-use (a positive idleness check on the same lines).
  quiet=0
  for try in 1 2 3 4 5 6 7 8; do
    if ci_lease_busy; then echo "CI re-took the DUT during the quiet wait"; echo stopped >"$MARKER"; exit 1; fi
    traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
      | grep -vE '#EVT# (SYSTEM_STATS|Harvester stats)' \
      | grep -icE 'session|request|prompt|generat|token') || true
    busy_hb=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null \
      | grep -cE '#EVT# SYSTEM_STATS:.*Busy=[1-9]') || true
    conns=$(sudo -n ss -Htn state established \
      '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null \
      | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
    if [ "${conns:-0}" -ne 0 ] || [ "${busy_hb:-0}" -ne 0 ]; then
      echo "rinzler in use (remote conns=$conns, Busy>0 heartbeats=$busy_hb) - not touching it"
      echo serving-in-use >"$MARKER"; exit 1
    fi
    if [ "${traffic:-0}" -eq 0 ]; then quiet=1; break; fi
    echo "try $try: non-heartbeat journal lines=$traffic (conns=0, busy_hb=0) - waiting 300s"
    sleep 300
  done
  if [ "$quiet" -ne 1 ]; then
    echo "journal window never went quiet - not touching serving"
    echo serving-quiet-timeout >"$MARKER"; exit 1
  fi
  echo "rinzlers active, zero journal traffic (10 min) and no remote client connections - stopping per policy"
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || { echo stop-failed >"$MARKER"; exit 1; }
  sleep 5
  if ! fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null; then
    rm -f /dev/hugepages/slice-*-of-8
    echo "hugepage slices removed (fuser: no open handles)"
  fi
fi

if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
echo "guard acquired $(date -u +%FT%TZ)"

# ---- Stage 1: qpack-alignment fix build + tests (tron-amx) ---------------
cd ~/workspace/tron-amx || { echo tree-missing >"$MARKER"; exit 1; }
{
  echo "# stage 1: fix build+tests, $(date -u +%FT%TZ)"
  echo "tree: $(git rev-parse --short HEAD) dirty: $(git status --short | tr '\n' ' ')"
  git diff --stat
} >"$DIR/tests-summary.txt"
if nix develop --command bash -c \
  'set -o pipefail; cmake --build gen --target t_amx_mirror t_amx_numerics t_amx_arena_leak t_amx_dispatch_dtype t_llama_unit -j96 2>&1 | tail -4'; then
  for t in t_amx_mirror t_amx_numerics t_amx_arena_leak t_amx_dispatch_dtype t_llama_unit; do
    BIN=$(find gen -name "$t" -type f -executable | head -1)
    if [ -z "$BIN" ]; then echo "$t BINARY-MISSING" >>"$DIR/tests-summary.txt"; FAIL=1; continue; fi
    if env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE "$BIN" >"$DIR/tests-$t.txt" 2>&1; then
      echo "$t PASS $(grep -Eo 'All tests passed.*|[0-9]+ assertions? in [0-9]+ test cases?' "$DIR/tests-$t.txt" | tail -1)" >>"$DIR/tests-summary.txt"
    else
      echo "$t FAIL rc=$? (see tests-$t.txt)" >>"$DIR/tests-summary.txt"; FAIL=1
    fi
  done
else
  echo "BUILD-FAILED stage 1" >>"$DIR/tests-summary.txt"
  campaign_guard_release; echo build-failed >"$MARKER"; exit 1
fi
echo "stage 1 done $(date -u +%FT%TZ)"; cat "$DIR/tests-summary.txt"

if ci_took_dut; then echo CI-TOOK-DUT; campaign_guard_release; echo stopped >"$MARKER"; exit 1; fi

# ---- Stage 2: microbenches (real kernel TU under nix clang) --------------
nix develop --command bash -c '
  set -e
  KFLAGS="-O3 -std=gnu++23 -DNDEBUG -DTRON_IGNORE_NAN -DTRON_IGNORE_FTZ -Ih \
    -mamx-tile -mamx-bf16 -mavx512f -mavx512bw -mavx512vl -mavx512dq -mavx512bf16 -mavx2 -mfma"
  clang++ $KFLAGS -c src/tron/kernels/amx_attn.cpp -o /tmp/amx_attn_real.o
  clang++ -O3 -std=gnu++23 ~/workspace/intel-AMX/exec/bench_qpack.cpp /tmp/amx_attn_real.o -o /tmp/bench_qpack
  clang++ -O3 -std=gnu++23 ~/workspace/intel-AMX/exec/bench_qk_align.cpp /tmp/amx_attn_real.o -o /tmp/bench_qk_align
' || { campaign_guard_release; echo bench-build-failed >"$MARKER"; exit 1; }
{
  echo "# bench_qpack + bench_qk_align, $(date -u +%FT%TZ), delphi-3bda cpu 96 (nice default, idle slot)"
  echo "# kernel TU: src/tron/kernels/amx_attn.cpp @ $(git rev-parse --short HEAD) (packers/kernels untouched by the working-tree fix)"
  sha256sum /tmp/bench_qpack /tmp/bench_qk_align
  for fn in rows group; do
    case $fn in rows) it=10000000 ;; group) it=3000000 ;; esac
    for rep in 1 2 3; do
      env -u TRON_AMX_DISABLE taskset -c 96 /tmp/bench_qpack "$fn" "$it" \
        || { echo "RUN-FAILED qpack $fn rep$rep"; FAIL=1; }
    done
  done
} >"$DIR/bench-qpack.txt"
{
  echo "# bench_qk_align: qk_mirror_128x4 per 64-token page, packed-Q base +0 vs +16 bytes"
  echo "# $(date -u +%FT%TZ), delphi-3bda cpu 96; interleaved A/B inside each rep"
  sha256sum /tmp/bench_qk_align
  for pages in 1 512 16384; do
    case $pages in 1) iters=200000 ;; 512) iters=800 ;; 16384) iters=25 ;; esac
    if ci_took_dut; then echo "CI-TOOK-DUT before pages=$pages"; FAIL=1; break; fi
    for rep in 1 2 3; do
      for off in 0 16 0 16; do
        env -u TRON_AMX_DISABLE taskset -c 96 /tmp/bench_qk_align "$off" "$iters" "$pages" \
          || { echo "RUN-FAILED qk off=$off pages=$pages rep=$rep"; FAIL=1; }
      done
    done
  done
} >"$DIR/bench-qk-align.txt"
echo "stage 2 done $(date -u +%FT%TZ)"

if ci_took_dut; then echo CI-TOOK-DUT; campaign_guard_release; echo stopped >"$MARKER"; exit 1; fi

# ---- Stage 3: per-call dispatch counters under real decode (tron-dd) -----
cd ~/workspace/ai-runs/tron-dd || { echo dd-tree-missing >"$MARKER"; exit 1; }
echo "dd tree: $(git rev-parse --short HEAD) ($(git log -1 --format=%s | head -c 60))"
nix develop --command bash -c \
  'set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON -DTRON_AMX_PV_TRUNC=OFF -DCMAKE_CXX_FLAGS= >/dev/null &&
   cmake --build gen --target runtron -j96 2>&1 | tail -2' \
  || { campaign_guard_release; echo counter-build-failed >"$MARKER"; exit 1; }
cp gen/runtron gen/runtron.counter
sha256sum gen/runtron.counter
# Leave the dd cache in its canonical configuration (house convention).
nix develop --command bash -c \
  'cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_PV_TRUNC=OFF -DCMAKE_CXX_FLAGS= >/dev/null' || true

COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-perf --nr_hugepages 128 -o"
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
counter_cell() {  # name ctx users tmo
  local name=$1 ctx=$2 users=$3 tmo=$4
  if ci_took_dut; then echo "CI-TOOK-DUT before $name"; FAIL=1; return 1; fi
  env -u TRON_AMX_DISABLE USE_HW_ATTN=0 timeout "$tmo" ./gen/runtron.counter stream-generate-text \
    -m "$MODEL" $COMMON --prompt-length "$ctx" -l 256 -u "$users" \
    >"$DIR/counter-$name.txt" 2>&1
  local rc=$?
  echo "cell $name rc=$rc $(date -u +%FT%TZ)"
  [ $rc -ne 0 ] && FAIL=1
  rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
}
# Perf-round cells (realistic decode: >=32 dense pages + cycling partial tail):
counter_cell qwen-ctx2048-u1 2048 1 900
counter_cell qwen-ctx2048-u8 2048 8 900
counter_cell qwen-ctx8192-u8 8192 8 900
# Off-grid cell, deliberately: a sequence under one 64-token KV page, the
# zero-dense-page shape the lazy-begin ask optimizes. Not in the reviewed grid.
counter_cell qwen-ctx32-u1-OFFGRID 32 1 900
{
  echo "# per-call dispatch counters, $(date -u +%FT%TZ); binary gen/runtron.counter (tron-dd @ $(git rev-parse --short HEAD))"
  echo "# fraction of interest = calls_amx_zero / calls_amx_on (eager region+packs spent, no AMX page)"
  for f in "$DIR"/counter-*.txt; do
    echo "--- $(basename "$f")"
    grep -E "AMX-DEBUG|average tok/s|Parsing the prompt took" "$f" | tail -6
  done
} >"$DIR/counter-summary.txt"
echo "stage 3 done $(date -u +%FT%TZ)"; cat "$DIR/counter-summary.txt"

# ---- Stage 4: cleanup ----------------------------------------------------
rm -f /dev/hugepages/amx-perf* 2>/dev/null || true
campaign_guard_release
if [ "$FAIL" -ne 0 ]; then echo check-output >"$MARKER"; else echo ok >"$MARKER"; fi
echo "=== jeremy-measure done $(date -u +%FT%TZ) marker=$(cat "$MARKER") ==="
