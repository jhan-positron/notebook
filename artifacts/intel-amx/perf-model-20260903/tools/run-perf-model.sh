#!/usr/bin/env bash
# run-perf-model.sh - measurements M0..M8 of perf-model/action-plan.html, run ON
# delphi-3bda. Tron runs ONLY in its AVX form (kill switch TRON_AMX_DISABLE=1 on
# the fence-branch probe binary); the AMX path of Tron is never executed here.
# Launch from the editing host with launch.sh (writes src/SHA256SUMS, then
# starts this script over ssh with nohup). Direct form:
#   ssh delphi-3bda 'nohup bash ~/workspace/intel-AMX/exec/perf-model-20260903/run-perf-model.sh >/dev/null 2>&1 &'
# RESUME=1 skips stages that finished (done-<stage> files); the default moves old
# results aside and runs a fresh campaign.
# Progress: exec/results/perf-model-20260903/campaign.log; marker campaign.done
# (ok | stopped-early | failed | aborted | serving-in-use | guard-refused).
set -u
EXEC=~/workspace/intel-AMX/exec
HERE=$EXEC/perf-model-20260903
SRC=$HERE/src
OUT=$EXEC/results/perf-model-20260903
BIN=/var/tmp/jhan/perf-model-bin            # local disk on the DUT, not NFS
LOG=$OUT/campaign.log
MARKER=$OUT/campaign.done
APP27="24-35,48-59,151-153"                  # Tron's app CPU set minus 154 (27 attention workers)
BG26="25-35,48-59,151-153"                   # background readers for the loaded-latency probe (victim = 24)
TS_SHOW="Time_Of_Day_Seconds,CPU,Busy%,Bzy_MHz"
# --- Tron (AVX form only) ---
WT=~/workspace/ai-runs/tron-fence-amx
EXPECT_COMMIT=8fd1e7798d104b6efa90c3169a1746e3a49dedd5   # fence branch + phase probe (single-attn round, 2026-09-01)
TRON_BIN=$WT/gen/runtron.samirror            # same binary as the 2026-09-01 "disable" arm; kill switch makes it AVX-only
EXTRACT=$EXEC/single-attn-20260901/extract-sa.py
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
HP=/dev/hugepages/amx-pm
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file $HP --nr_hugepages 128 -o"

. "$EXEC/lib-guard.sh"
RESUME=${RESUME:-0}
if [ "$RESUME" != 1 ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"; fi
mkdir -p "$OUT" "$BIN" /var/tmp/jhan
exec >>"$LOG" 2>&1
exec 3>>"$LOG"            # fd 3: campaign.log even from inside redirected stage blocks
rm -f "$MARKER"
RUNPID=0; GUARDED=0; TSPID=0; PARANOID_SET=0
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; [ "$TSPID" -gt 0 ] && sudo -n pkill -INT -x turbostat 2>/dev/null; [ "$PARANOID_SET" = 1 ] && sudo -n sysctl -w kernel.perf_event_paranoid=4 >/dev/null 2>&1; sleep 2; rm -f '"$HP"'* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== perf-model campaign start $(date -u +%FT%TZ) on $(hostname) RESUME=$RESUME"

say() { echo "$*"; echo "$*" >&3; }
fail() { say "FAILED: $*"; echo failed >"$MARKER"; exit 1; }
stop_early() { say "STOPPED EARLY: $*"; echo stopped-early >"$MARKER"; exit 2; }
stop_now() {  # nonzero = keep going. Clock window advisory (03:30Z prep), lease and rinzler authoritative.
  local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { say CLOCK-STOP; return 0; }
  ci_took_dut && { say CI-TOOK-DUT; return 0; }
  rinzler_active && { say RINZLER-BACK; return 0; }
  return 1
}
check_ci() { stop_now "${2:-600}" && stop_early "before $1"; return 0; }
stage_due()  { if [ "$RESUME" = 1 ] && [ -e "$OUT/done-$1" ]; then say "--- $1 already done (done-$1 exists), skipped"; return 1; fi; return 0; }
stage_done() { touch "$OUT/done-$1"; say "--- $1 done $(date -u +%FT%TZ)"; }
# turbostat runs under sudo. sudo 1.9.9 drops a SIGINT whose sender shares sudo's
# process group (every process of this script does), so the stop signal goes to the
# turbostat child itself; --num_iterations caps the run if that fails, so the wait
# below cannot hang. Trailing samples are excluded by parse.py (RUN window, Busy%).
ts_start() {  # cpus outfile max_iterations
  sudo -n turbostat --quiet --interval 1 --num_iterations "$3" --cpu "$1" --show "$TS_SHOW" >"$2" 2>&1 &
  TSPID=$!; sleep 1.2
}
ts_stop() {
  local child; child=$(pgrep -P "$TSPID" -x turbostat)
  if [ -n "$child" ] && sudo -n kill -INT "$child" 2>/dev/null; then :; else
    echo "TURBOSTAT-STOP-FAILED sudo_pid=$TSPID child=${child:-none}: turbostat ends by its iteration cap instead"
  fi
  wait "$TSPID" 2>/dev/null; TSPID=0
}

# ---- Stage A: wait for CI, then the rinzler policy (copied from p2-perf-round-20260830.sh)
wait_for_ci_release 50400 || fail "CI did not release the DUT within 14 h"
active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active') || true
if [ "${active:-0}" -gt 0 ]; then
  # Traffic test. The periodic '#EVT# SYSTEM_STATS' / 'Harvester stats' lines of an idle
  # instance contain the words Sessions and Tokens; they are not requests and are excluded.
  # In addition the newest SYSTEM_STATS line of each instance must show Open=0 and Busy=0.
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
  busy=$(sudo -n journalctl -u 'rinzler@*' --since '-30 min' --no-pager 2>/dev/null | grep 'SYSTEM_STATS' | tail -4 | grep -vcE 'Open=0, Closed=[0-9]+, Busy=0') || true
  conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  echo "rinzler traffic test: non-stats request lines (10 min)=$traffic, stats lines with open/busy sessions=$busy, remote conns=$conns"
  if [ "${traffic:-0}" -ne 0 ] || [ "${busy:-0}" -ne 0 ] || [ "${conns:-0}" -ne 0 ]; then
    say "rinzler serving looks in use (request lines=$traffic, busy stats=$busy, remote conns=$conns) - not touching it"
    echo serving-in-use >"$MARKER"; exit 1
  fi
  say "rinzlers active, zero journal traffic (10 min) and no remote client connections - stopping per policy (not restarted)"
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 || fail "rinzler stop failed"
  sleep 5
fi
# Stale rinzler slices (serving stopped, files still on hugetlbfs) hold the 1 GiB pool.
# Policy: remove only fuser-clean slices while serving is down.
if ! rinzler_active; then
  for f in /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] || continue
    if fuser -s "$f" 2>/dev/null; then echo "keeping $f (fuser: still open)"; else rm -f "$f"; echo "removed stale $f (fuser: no open handles)"; fi
  done
fi
free0=$(cat /sys/devices/system/node/node0/hugepages/hugepages-1048576kB/free_hugepages 2>/dev/null || echo 0)
say "node 0 free 1 GiB pages: $free0"
[ "$free0" -ge 128 ] || fail "node 0 has $free0 free 1 GiB pages; Tron needs 128 (stale hugepage files? ls -la /dev/hugepages)"
# ---- Stage B: cross-session guard
campaign_guard_acquire || { say guard-refused; echo guard-refused >"$MARKER"; exit 1; }
GUARDED=1
echo "--- machine state"; uptime; cat /run/lock/systems-test-ci.lease 2>/dev/null || echo "(no lease file)"
grep -E "HugePages_(Total|Free)" /proc/meminfo; pgrep -a runtron || echo "no runtron"

# ---- Stage C: build the non-Tron tools on the DUT. Sources come over NFS; wait
# until their content matches the SHA256SUMS written on the editing host at launch
# (NFS attribute-cache trap of 2026-08-31), then build.
if [ -s "$SRC/SHA256SUMS" ]; then
  ok=0
  for i in $(seq 1 24); do (cd "$SRC" && sha256sum -c --quiet SHA256SUMS >/dev/null 2>&1) && { ok=1; break; }; sleep 15; done
  [ "$ok" = 1 ] || fail "source content on the DUT does not match SHA256SUMS after 6 min (NFS cache?)"
  echo "--- sources match SHA256SUMS"
else
  echo "--- no SHA256SUMS file; building the sources as seen (content not verified)"
fi
echo "--- sources"; sha256sum "$SRC"/*.c "$SRC"/*.cpp
for f in unit_bench.cpp memrate.c latency.c insn_loops.cpp; do [ -s "$SRC/$f" ] || fail "empty or missing $SRC/$f"; done
g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 -pthread "$SRC/unit_bench.cpp" -o "$BIN/unit_bench" || fail "build unit_bench"
gcc -O3 -std=gnu11 -march=x86-64-v4 -mamx-tile -pthread "$SRC/memrate.c" -o "$BIN/memrate" || fail "build memrate"
gcc -O3 -std=gnu11 "$SRC/latency.c" -o "$BIN/latency" || fail "build latency"
g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 "$SRC/insn_loops.cpp" -o "$BIN/insn_loops" || fail "build insn_loops"
echo "--- binaries"; sha256sum "$BIN"/*; g++ --version | head -1; sudo --version | head -1
echo "--- vdpbf16ps count in insn_loops: $(objdump -d "$BIN/insn_loops" | grep -c vdpbf16ps); stack stores between vdpbf16ps in the tp loops are checked by the reviewer's assembly note"

# ---- M0 hardware check (always)
{
  echo "# M0 hardware check $(date -u +%FT%TZ)"
  lscpu | egrep "Model name|Socket|Core|Thread|NUMA|L1d|L2|L3|MHz"
  echo "## dmidecode memory"; sudo -n dmidecode -t memory 2>/dev/null | egrep "^\s+(Size|Speed|Configured Memory Speed|Part Number|Type):" | sort | uniq -c || echo "dmidecode not permitted"
  echo "## numactl"; numactl -H
  echo "## hugepages"; grep -i huge /proc/meminfo; echo "node0 free 1 GiB pages: $free0"
  echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled
  echo "## governor"; cat /sys/devices/system/cpu/cpu24/cpufreq/scaling_governor 2>/dev/null
  echo "## kernel"; uname -r
  echo "## fpga"; lspci | grep -E "10:00.0|13:00.0"
} >"$OUT/m0-hardware.txt"

# ---- M7 Tron, AVX form (kill switch + phase probe): fresh baseline at prompts 256 / 2048 / 8192
if stage_due M7; then
{
  echo "# M7 Tron AVX-form baseline $(date -u +%FT%TZ)"
  cd "$WT" || fail "no worktree"
  HEAD=$(git rev-parse HEAD); echo "worktree HEAD $HEAD"
  [ "$HEAD" = "$EXPECT_COMMIT" ] || fail "worktree HEAD $HEAD != expected $EXPECT_COMMIT"
  [ -z "$(git status --porcelain -- h src)" ] || { git status --porcelain -- h src; fail "worktree dirty"; }
  [ -x "$TRON_BIN" ] || fail "missing $TRON_BIN"
  sha256sum "$TRON_BIN"
  timeout 20 "$TRON_BIN" --help >/dev/null 2>&1 || fail "runtron.samirror does not execute"
  run_cell() {  # ctx rep tmo len
    local ctx=$1 rep=$2 tmo=$3 len=$4 rc
    local kv=$OUT/m7-kvwait-disable-c$ctx-r$rep.bin rlog=$OUT/m7-cell-disable-c$ctx-r$rep.log
    echo "### model=$MODEL arm=disable(kill switch, AVX) ctx=$ctx len=$len users=1 rep=$rep kv=$(basename $kv) bin=$(basename $TRON_BIN) $(date -u +%FT%TZ)"
    env TRON_AMX_DISABLE=1 USE_HW_ATTN=0 TRON_ATTN_PHASE=1 TRON_KVWAIT_FILE=$kv timeout "$tmo" "$TRON_BIN" stream-generate-text -m "$MODEL" $COMMON \
      --prompt-length "$ctx" -l "$len" -u 1 >"$rlog" 2>&1 &
    RUNPID=$!; wait "$RUNPID"; rc=$?; RUNPID=0
    grep -E "Parsing the prompt took|average tok/s|Worker speeds" "$rlog"
    [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
    [ -s "$kv" ] || echo "KVWAIT-EMPTY $kv"
    rm -f "$HP"* 2>/dev/null
  }
  run_cell 256 0 300 8
  python3 "$EXTRACT" --check --arm disable "$OUT/m7-kvwait-disable-c256-r0.bin" || { echo "SMOKE-FAILED"; fail "Tron AVX smoke failed"; }
  echo "### smoke ok"
  for rep in 1 2; do
    for ctx in 256 2048 8192; do
      stop_now 900 && stop_early "M7 ctx $ctx rep $rep"
      run_cell "$ctx" "$rep" 900 256
    done
  done
  for ctx in 256 2048 8192; do
    echo "### extract ctx=$ctx (two reps)"
    python3 "$EXTRACT" "$OUT/m7-kvwait-disable-c$ctx-r1.bin" "$OUT/m7-kvwait-disable-c$ctx-r2.bin" >"$OUT/m7-phases-disable-c$ctx.json" 2>"$OUT/m7-extract-c$ctx.err" || echo "EXTRACT-FAILED ctx=$ctx"
    head -c 400 "$OUT/m7-phases-disable-c$ctx.json"; echo
  done
  cd "$HERE"
} >"$OUT/m7-tron-avx.txt" 2>&1
grep -qE "RUN-FAILED|KVWAIT-EMPTY|EXTRACT-FAILED" "$OUT/m7-tron-avx.txt" && say "WARNING: M7 has failed cells (see m7-tron-avx.txt)"
gzip -f "$OUT"/m7-kvwait-*.bin 2>/dev/null || true   # raw-data policy: the kvwait files are sparse, keep them gzipped
stage_done M7
fi
check_ci M1

# ---- correctness checks of the unit benchmark (both paths, on the DUT; always)
ck_ok=1
{
  echo "# unit_bench --check $(date -u +%FT%TZ)"
  numactl --membind=0 "$BIN/unit_bench" --check --variant avx --pages 3 --threads 1 --cpus 24 --huge none || { echo "CHECK-RC avx rc=$?"; ck_ok=0; }
  numactl --membind=0 "$BIN/unit_bench" --check --variant amx --pages 3 --threads 1 --cpus 24 --huge none || { echo "CHECK-RC amx rc=$?"; ck_ok=0; }
} >"$OUT/check.txt" 2>&1
[ "$ck_ok" = 1 ] && [ "$(grep -c ' OK$' "$OUT/check.txt")" -eq 2 ] || fail "unit_bench correctness check did not pass on both paths (see check.txt)"
say "--- unit_bench check OK on both paths"

# ---- M1 per-core streaming rate vs number of readers
if stage_due M1; then
{
  echo "# M1 memrate $(date -u +%FT%TZ)  cpus=$APP27  1 GiB per reader, node 0"
  for n in 1 2 4 8 14 27; do for rep in 1 2 3; do
    numactl --membind=0 "$BIN/memrate" --cpus "$APP27" --threads "$n" --mb 1024 --seconds 6 --mode load | tail -1 || echo "MEMRATE-FAILED load n=$n"
  done; done
  for n in 1 27; do for rep in 1 2 3; do
    numactl --membind=0 "$BIN/memrate" --cpus "$APP27" --threads "$n" --mb 1024 --seconds 6 --mode tile | tail -1 || echo "MEMRATE-FAILED tile n=$n"
  done; done
  echo "## per-thread detail, 27 readers, load mode"
  numactl --membind=0 "$BIN/memrate" --cpus "$APP27" --threads 27 --mb 1024 --seconds 6 --mode load
  echo "## 4 KiB pages, 1 and 27 readers, load and tile"
  for n in 1 27; do
    numactl --membind=0 "$BIN/memrate" --cpus "$APP27" --threads "$n" --mb 1024 --seconds 6 --mode load --huge none | tail -1
    numactl --membind=0 "$BIN/memrate" --cpus "$APP27" --threads "$n" --mb 1024 --seconds 6 --mode tile --huge none | tail -1
  done
} >"$OUT/m1-memrate.txt" 2>&1
stage_done M1
fi
check_ci M2

# ---- M2 latency, idle and loaded (8 GiB on 1 GiB pages = DRAM; 1 GiB rows for comparison; 64 MiB = L3)
if stage_due M2; then
{
  echo "# M2 latency $(date -u +%FT%TZ)  victim cpu 24"
  for rep in 1 2; do
    numactl --membind=0 "$BIN/latency" --cpu 24 --mb 8192 --hops 20000000 --huge 1g
    numactl --membind=0 "$BIN/latency" --cpu 24 --mb 1024 --hops 20000000 --huge thp
    numactl --membind=0 "$BIN/latency" --cpu 24 --mb 1024 --hops 20000000 --huge none
    numactl --membind=0 "$BIN/latency" --cpu 24 --mb 64 --hops 20000000 --huge thp
  done
  echo "## loaded: 26 readers streaming on $BG26 (started first, stopped after the chase returns) while cpu 24 chases (8 GiB, 1 GiB pages)"
  for rep in 1 2; do
    numactl --membind=0 "$BIN/memrate" --cpus "$BG26" --threads 26 --mb 1024 --seconds 600 --mode load >"$OUT/m2-bg-$rep.txt" 2>&1 &
    bgpid=$!
    sleep 8
    echo "chase start $(date -u +%s)"
    numactl --membind=0 "$BIN/latency" --cpu 24 --mb 8192 --hops 20000000 --huge 1g
    echo "chase end $(date -u +%s); readers still running: $(kill -0 $bgpid 2>/dev/null && echo yes || echo NO)"
    kill "$bgpid" 2>/dev/null; wait "$bgpid" 2>/dev/null
  done
} >"$OUT/m2-latency.txt" 2>&1
stage_done M2
fi
check_ci M5

# ---- M5 instruction floors (cpu 24), one loop per run with its own turbostat capture (iteration cap 12 s)
if stage_due M5; then
for loop in vdp_tp4 vdp_tp8 vdp_tp16 vdp_lat hred_tp hred_lat dotter_l1 tdp_tp tdp_lat tld_l1; do
  ts_start 24 "$OUT/m5-turbostat-$loop.txt" 12
  "$BIN/insn_loops" --cpu 24 --only "$loop" --seconds 4 >"$OUT/m5-$loop.txt" 2>&1 || echo "INSN-FAILED $loop" >>"$OUT/m5-$loop.txt"
  ts_stop
done
stage_done M5
fi
check_ci M3

# ---- M3 unit benchmark (+ M4 turbostat on the sampled runs)
run_ub() {  # name, then unit_bench args
  local name=$1; shift
  echo "## $name  $(date -u +%FT%TZ)"
  numactl --membind=0 "$BIN/unit_bench" "$@" --cpus "$APP27" --json "$OUT/m3-$name.json" 2>&1 || echo "UNIT-BENCH-FAILED $name"
  case " $* " in *" --huge 1g "*) grep -q '"huge": "1g/' "$OUT/m3-$name.json" 2>/dev/null || echo "PAGESIZE-FALLBACK $name (requested 1g; JSON huge field: $(grep -o '"huge": "[^"]*"' "$OUT/m3-$name.json" 2>/dev/null))";; esac
}
run_ub_ts() {  # sampled by turbostat (M4); iteration cap 120 s
  local name=$1; shift
  ts_start "$APP27" "$OUT/m4-turbostat-$name.txt" 120
  run_ub "$name" "$@"
  ts_stop
  python3 - "$OUT/m3-$name.json" "$name" <<'PY' || true
import json, sys
d = json.load(open(sys.argv[1])); span = d.get("run_end_epoch", 0) - d.get("run_start_epoch", 0)
print(f"timed phase {span:.1f} s" + ("" if span >= 3 else f"  WARNING: {sys.argv[2]} timed phase under 3 s: turbostat window empty"))
PY
}
if stage_due M3; then
{
  echo "# M3 unit_bench $(date -u +%FT%TZ)"
  for rep in 1 2 3; do
    for v in avx amx; do
      run_ub_ts "$v-hot-t1-r$rep"        --variant $v --hot --pages 130 --threads 1  --passes 150  --warmup 3  --huge 1g
      run_ub    "$v-hot-t27-r$rep"       --variant $v --hot --pages 130 --threads 27 --passes 60   --warmup 5  --huge 1g
      run_ub    "$v-p130-t1-r$rep"       --variant $v --pages 130 --threads 1  --passes 20   --warmup 3  --huge 1g
      run_ub    "$v-p34-t1-r$rep"        --variant $v --pages 34  --threads 1  --passes 40   --warmup 3  --huge 1g
      run_ub    "$v-p6-t1-r$rep"         --variant $v --pages 6   --threads 1  --passes 200  --warmup 10 --huge 1g
      run_ub_ts "$v-p130-t27-r$rep"      --variant $v --pages 130 --threads 27 --passes 2000 --warmup 20 --huge 1g
      run_ub    "$v-p34-t27-r$rep"       --variant $v --pages 34  --threads 27 --passes 600  --warmup 40 --huge 1g
      run_ub    "$v-p6-t27-r$rep"        --variant $v --pages 6   --threads 27 --passes 2000 --warmup 100 --huge 1g
      run_ub    "$v-p130-t27-shuf-r$rep" --variant $v --pages 130 --threads 27 --passes 300  --warmup 20 --huge 1g --shuffle
      stop_now 600 && stop_early "M3 $v rep $rep"
    done
  done
  echo "## 2 MiB pages instead of 1 GiB pages, one repeat, prompt-8192 working set"
  for v in avx amx; do run_ub "$v-p130-t27-thp" --variant $v --pages 130 --threads 27 --passes 300 --warmup 20 --huge thp; done
  echo "## hot mode clock sample (M4): 27-thread hot run sized to >= 12 s of timed phase from the r3 pass time"
  for v in avx amx; do
    pass_us=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['all_median']['pass_us'])" "$OUT/m3-$v-hot-t27-r3.json" 2>/dev/null || echo 0)
    passes=$(python3 -c "import math,sys; pu=float(sys.argv[1]); print(min(60000, max(400, math.ceil(12e6/pu))) if pu > 0 else 12000)" "$pass_us")
    echo "## $v hot-t27-long: pass_us=$pass_us -> passes=$passes"
    run_ub_ts "$v-hot-t27-long" --variant $v --hot --pages 130 --threads 27 --passes "$passes" --warmup 5 --huge 1g
  done
} >"$OUT/m3-unit-bench.txt" 2>&1
grep -E "UNIT-BENCH-FAILED|PAGESIZE-FALLBACK|WARNING" "$OUT/m3-unit-bench.txt" | while read -r l; do say "M3: $l"; done
stage_done M3
fi
check_ci M6

# ---- M6 counters on the 27-thread runs (perf_event_paranoid 4 -> 0 -> 4, standing approval, logged), with a fill-only control.
# perf stat counts the command's own threads (per-process mode); -C is not used because it is ignored without -a.
if stage_due M6; then
{
  echo "# M6 perf stat $(date -u +%FT%TZ)  (per-process counting: all threads of unit_bench)"
  echo "perf_event_paranoid before: $(cat /proc/sys/kernel/perf_event_paranoid)"
  if sudo -n sysctl -w kernel.perf_event_paranoid=0; then
    PARANOID_SET=1
    EV="cycles,instructions,cpu/event=0xd1,umask=0x08,name=l1_miss/,cpu/event=0xd1,umask=0x10,name=l2_miss/,cpu/event=0xd1,umask=0x20,name=l3_miss/,cpu/event=0x12,umask=0x0e,name=dtlb_ld_walk/"   # MEM_LOAD_RETIRED.L1/L2/L3_MISS and DTLB_LOAD_MISSES.WALK_COMPLETED as raw codes (perfstat-20260831 spelling; the symbolic names are not in this perf)
    for v in avx amx; do
      echo "## $v p130 t27 counters (passes 2000)"
      perf stat -e "$EV" -- numactl --membind=0 "$BIN/unit_bench" --variant $v --pages 130 --threads 27 --passes 2000 --warmup 20 --huge 1g --cpus "$APP27" 2>&1 || echo "perf stat failed for $v"
      echo "## $v p130 t27 counters, fill-only control (passes 0)"
      perf stat -e "$EV" -- numactl --membind=0 "$BIN/unit_bench" --variant $v --pages 130 --threads 27 --passes 0 --warmup 0 --huge 1g --cpus "$APP27" 2>&1 || echo "perf stat control failed for $v"
      echo "## $v p130 t27 topdown"
      perf stat -M tma_memory_bound,tma_core_bound,tma_frontend_bound,tma_bad_speculation,tma_retiring -- numactl --membind=0 "$BIN/unit_bench" --variant $v --pages 130 --threads 27 --passes 2000 --warmup 20 --huge 1g --cpus "$APP27" 2>&1 || echo "perf stat topdown failed for $v"
    done
    sudo -n sysctl -w kernel.perf_event_paranoid=4 && PARANOID_SET=0
    echo "perf_event_paranoid after: $(cat /proc/sys/kernel/perf_event_paranoid)"
    [ "$(cat /proc/sys/kernel/perf_event_paranoid)" = "4" ] || echo "WARNING: paranoid not restored to 4"
  else
    echo "could not lift perf_event_paranoid; M6 skipped"
  fi
} >"$OUT/m6-perf.txt" 2>&1
stage_done M6
fi
check_ci M8

# ---- M8 (optional) one traced Tron AVX run at prompt 8192 for the per-layer split of the non-attention work
if stage_due M8; then
{
  echo "# M8 traced Tron AVX run $(date -u +%FT%TZ) (tracing slows attention; used only for the FPGA/main-thread record split)"
  cd "$WT" || fail "no worktree"
  env TRON_AMX_DISABLE=1 USE_HW_ATTN=0 timeout 900 "$TRON_BIN" stream-generate-text -m "$MODEL" $COMMON \
    --prompt-length 8192 -l 256 -u 1 --trace-gen "$OUT/m8-avx-1u-8192.perfetto-trace" >"$OUT/m8-cell.log" 2>&1 &
  RUNPID=$!; wait "$RUNPID"; rc=$?; RUNPID=0
  grep -E "Parsing the prompt took|average tok/s" "$OUT/m8-cell.log"; [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
  rm -f "$HP"* 2>/dev/null; ls -la "$OUT"/m8-*.perfetto-trace 2>/dev/null
  cd "$HERE"
} >"$OUT/m8-trace.txt" 2>&1
stage_done M8
fi

say "=== campaign done $(date -u +%FT%TZ)"
echo ok >"$MARKER"
campaign_guard_release; GUARDED=0
