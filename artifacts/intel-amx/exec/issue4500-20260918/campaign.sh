#!/usr/bin/env bash
# issue4500-20260918: root-cause measurements for positron-ai/tron issue #4500 (qwen-3-4b decode
# TPS loss with FPGA attention under the VNNI K layout of PR #4424). Design: VNNIed-K-in-place/
# issue4500/root-cause-debug.html. Runs on delphi-3bda, OUR half (socket 1, cards 90/93/b9/bc).
#
# Words used here: tron = the inference program under test; runtron = its command-line tool;
# arm = one binary plus its environment; cell = one (block, arm, tp, users) combination; rep = one
# repetition of a cell; TPS = generated tokens per second per user; step = 1000 / TPS = the period of
# one batched decode step in ms; TTFT = time to first token = runtron's "Parsing the prompt took" (max
# over users); FPGA attention = USE_HW_ATTN unset (the default for this ingested model); VNNI = the
# pair-interleaved K layout (TRON_K_VNNI).
#
# Arms (all RelWithDebInfo, TRON_AMX_DISPATCH=ON, built on 3bda):
#   base     = runtron.main0916    c7844ca2ce  main = the PR's merge base (row-major K)
#   headoff  = runtron.headoff0916 ff680c8020  PR code with TRON_K_VNNI=OFF (row-major K, same source as vnni)
#   vnni     = runtron.pr4424      ff680c8020  PR code with TRON_K_VNNI=ON
#   vnni2    = the same binary as vnni (A/A control)
#   vnnikill = vnni + TRON_AMX_DISABLE=1 (kill switch: same layout, no AMX kernel)
#   head30   = tron-tilec/gen/runtron 30c4ac82cb = the PR head on GitHub (equivalence check, 1 rep)
# Blocks (env BLOCKS selects; default order = priority):
#   m1   attribution: base headoff vnni vnni2 vnnikill (+head30 rep 1) x tp2/tp4 x 8 users, REPS
#   m2   launch-phase knob: headoff vnni x TRON_HWATTN_EARLY_LAUNCH_MIN_B=1|100 x users 2,8 x tp2/tp4, REPS_M2 (3)
#   m3   Perfetto traces (in-process, --trace-gen): base headoff vnni x tp2/tp4 x 8 users, gen 40, passes 10- (decode
#        only: the prefill passes emit about 250k hw-wait spans each and filled the 100 MB file in 2.3 s on night 1),
#        categories A = -*,+model,+scheduler,+hwattention and B = A + hwattention-detail; plus users 2 tp2
#   m4   perf record first, then perf counters (sudo -n perf) on headoff and vnni x tp2/tp4 x 8 users, gen 4096
#   m1b  per-engine load: base headoff vnni x users 2,4 x tp2/tp4, REPS_B
# Every run: prompt 1024 tokens (runtron -u N: N distinct Moby Dick chapters, equal length), --dont-stop,
# env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN, TRON_LOG_LEVEL=info, our placement per tp.
# Machine handling: waits for the CI lease; never starts a run inside the 01:40-03:45 UTC pre-CI hold;
# WAITS (does not act) while any rinzler@N unit is active or fewer than 256 hugepages are free (the idle
# production engines are the operator's to take down: see launch.sh). Every run takes the campaign
# guard (lease + flock + no runtron of ours); a 10-s watcher kills OUR runtron if the lease turns busy
# or a production unit comes up. Resume: relaunch; a run whose log has "average tok/s" is skipped.
# Never edit this file while it runs (bash re-reads a running script). Outputs:
#   exec/results/issue4500-20260918/{rt-results.txt, rt/*.log, traces/*.perfetto-trace, perf/*, summary.md}
#   log exec/logs/issue4500-20260918.log; status .status; marker .done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/issue4500-20260918
RES=$EXEC/results/issue4500-20260918
LOG=$EXEC/logs/issue4500-20260918.log
MARKER=$EXEC/logs/issue4500-20260918.done
STATUS=$EXEC/logs/issue4500-20260918.status
LOCAL=/var/tmp/jhan/traces/issue4500-20260918
HPFILE=/dev/hugepages/amx-i4500
BILL_UID=1062305141
BLOCKS=${BLOCKS:-"m1 m2 m3 m4 m1b"}
REPS=${REPS:-3}
REPS_B=${REPS_B:-2}
REPS_M2=${REPS_M2:-3}
GEN=${GEN:-256}
QWEN2=ingested-qwen-3-4b-instruct-2507-tp2
QWEN4=ingested-qwen-3-4b-instruct-2507-tp4
ARM_base_BIN=/var/tmp/jhan/tron-main0916/gen/runtron.main0916
ARM_headoff_BIN=/var/tmp/jhan/tron-headoff0916/gen/runtron.headoff0916
ARM_vnni_BIN=/var/tmp/jhan/tron-pr4424/gen/runtron.pr4424
ARM_vnni2_BIN=/var/tmp/jhan/tron-pr4424/gen/runtron.pr4424
ARM_vnnikill_BIN=/var/tmp/jhan/tron-pr4424/gen/runtron.pr4424
ARM_vnnikill_ENV="TRON_AMX_DISABLE=1"
ARM_head30_BIN=/var/tmp/jhan/tron-tilec/gen/runtron
OUR_RT_RE='^/var/tmp/jhan/tron-(main0916|headoff0916|pr4424|tilec)/gen/runtron(\.[a-z0-9]+)? '
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
mkdir -p "$RES/rt" "$RES/traces" "$RES/perf" "$LOCAL" "$EXEC/logs"
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
arm_bin() { local v="ARM_${1}_BIN"; echo "${!v:-}"; }
arm_env() { local v="ARM_${1}_ENV"; echo "${!v:-}"; }
placement() {
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
  esac
}
model_of() { case $1 in 2) echo "$QWEN2" ;; 4) echo "$QWEN4" ;; esac; }
hp_free() { awk '/^HugePages_Free/{print $2}' /proc/meminfo; }
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(hp_free) units_active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active$') $bill"
}

# ---------- stop rules ----------
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_active && { echo "rinzler@N unit active (idle production engines; operator takes them down, see launch.sh)"; return 0; }
  [ "$(hp_free)" -ge 256 ] || { echo "only $(hp_free) free 1 GiB hugepages (need 256 for the tp4 placement)"; return 0; }
  return 1
}
PRECI_STOP=0
wait_clear() {
  local why waited=0
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    if preci_hold; then echo "$(ts) pre-CI hold reached; ending the campaign"; PRECI_STOP=1; return 1; fi
    sleep 60
  done
  return 0
}
take_guard() {
  local waited=0
  until campaign_guard_acquire; do
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; }
    sleep 60; wait_clear || return 1
  done
  return 0
}
kill_ours() { pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; return 0; }
remove_our_slice_files() {  # only files WE own and nobody maps
  local f
  for f in /dev/hugepages/slice-*-of-8 "$HPFILE"*; do
    [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"
  done
  return 0
}
watch_run() {  # background: stop our run within ~10 s when CI takes the lease or a production unit comes up
  local sf=$1 why main=$$
  [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
  while :; do
    kill -0 "$main" 2>/dev/null || { kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; exit 0; }
    why=""
    if ci_lease_busy; then why="CI lease busy"; elif rinzler_active; then why="rinzler@N unit active"; fi
    if [ -n "$why" ]; then [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; kill_ours; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
finish() {  # $1 = marker word; also the abort path (EXIT trap)
  stop_watcher
  if [ "$1" = aborted ]; then trap '' TERM; [ "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" = "$$" ] && kill -TERM -- -$$ 2>/dev/null; fi
  kill_ours
  for _ in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
  pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null
  remove_our_slice_files
  campaign_guard_release 2>/dev/null
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  echo "$1" >"$MARKER"
  status "finished: $1"
  echo "=== campaign finished $(ts): $1 ==="
}

# ---------- one runtron run ----------
# rt_run BLOCK ARM TP USERS GEN REP EXTRA_ENV TAG [TRACE_FILE PASSES CATS]
# Writes rt/<name>.log, appends a header + key lines to rt-results.txt. Return 0 ok, 1 failed, 2 stopped/hold.
RT_PID=""
rt_run() {
  local block=$1 arm=$2 tp=$3 users=$4 gen=$5 rep=$6 xenv=$7 tag=$8 tracef=${9:-} passes=${10:-} cats=${11:-}
  local bin envv name rlog model rc res args tmo
  bin=$(arm_bin "$arm"); [ -x "$bin" ] || { echo "$(ts) binary of arm $arm missing: $bin"; return 1; }
  envv="$(arm_env "$arm") $xenv"; envv=${envv## }; envv=${envv%% }
  model=$(model_of "$tp")
  name="${block}__${arm}__tp${tp}__${users}u__${tag}__rep${rep}"
  rlog=$RES/rt/$name.log
  if grep -q "average tok/s" "$rlog" 2>/dev/null; then
    if [ -z "$tracef" ] || [ -s "$RES/traces/$(basename "$tracef")" ]; then echo "$(ts) $name already done"; return 0; fi
  fi
  wait_clear || return 2
  take_guard || return 2
  args="--prompt-length 1024 -l $gen -u $users --dont-stop"; tmo=1200
  [ -n "$tracef" ] && { rm -f "$tracef"; args="$args --trace-gen $tracef --trace-passes $passes"; }
  echo "### rt block=$block arm=$arm tp=$tp users=$users gen=$gen rep=$rep tag=$tag env=[${envv:-none}] cats=[${cats:-none}] bin=$bin model=$model ts=$(ts) $(machine_line)" | tee -a "$RES/rt-results.txt"
  echo running >"$RES/rt/$name.STATUS"; rm -f "$RES/rt/$name.STOPPED"
  watch_run "$RES/rt/$name.STOPPED" & WPID=$!
  ( cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && \
    exec env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN TRON_LOG_LEVEL=info ${cats:+TRON_TRACE_CATEGORIES=$cats} $envv \
      timeout -k 60 "$tmo" "$bin" stream-generate-text -m "$model" $(placement "$tp") --hugepage_file "$HPFILE" -o $args ) >"$rlog" 2>&1 &
  RT_PID=$!
  if [ "$block" = m4 ]; then perf_capture "$name" "$bin" "$users"; fi
  wait "$RT_PID"; rc=$?; RT_PID=""
  stop_watcher
  campaign_guard_release; remove_our_slice_files
  res=$(grep -E "Version:|Configured instance|App CPU list|HW attention (enabled|disabled)|Parsing the prompt took|average tok/s|Tracing session|perfetto" "$rlog" 2>/dev/null | cut -c1-240)
  if [ -e "$RES/rt/$name.STOPPED" ]; then
    echo "RUN-STOPPED $name rc=$rc $(cat "$RES/rt/$name.STOPPED")" | tee -a "$RES/rt-results.txt"; echo stopped >"$RES/rt/$name.STATUS"; return 2
  fi
  if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
    echo "RUN-FAILED $name rc=$rc" | tee -a "$RES/rt-results.txt"; printf '%s\n' "$res" >>"$RES/rt-results.txt"; tail -5 "$rlog" | cut -c1-200 >>"$RES/rt-results.txt"
    echo failed >"$RES/rt/$name.STATUS"; return 1
  fi
  if [ -n "$tracef" ]; then
    if [ -s "$tracef" ]; then cp "$tracef" "$RES/traces/"; echo "trace_bytes=$(stat -c %s "$tracef") -> $RES/traces/$(basename "$tracef")" | tee -a "$RES/rt-results.txt"
    else echo "RUN-FAILED $name no-trace" | tee -a "$RES/rt-results.txt"; echo failed >"$RES/rt/$name.STATUS"; return 1; fi
  fi
  printf '%s\n' "$res" >>"$RES/rt-results.txt"
  echo "ok $name $(grep -E 'average tok/s' "$rlog" | awk '{for(i=1;i<=NF;i++) if($i=="average") print $(i-1)}' | sort -n | awk '{a[NR]=$1} END {printf "tps_min=%s tps_max=%s n=%d", a[1], a[NR], NR}') $(grep -E 'Parsing the prompt took' "$rlog" | awk '{print $(NF-3)}' | sort -n | tail -1 | sed 's/^/ttft_max_s=/')" | tee -a "$RES/rt-results.txt"
  echo done >"$RES/rt/$name.STATUS"
  sleep 3
  return 0
}

# ---------- perf capture inside a run (block m4): counts and samples OUR runtron only ----------
perf_capture() {  # NAME BIN USERS: wait until every user finished the prompt, then count + sample the runtron process
  local name=$1 bin=$2 users=$3 pid n deadline out=$RES/perf/$name
  mkdir -p "$out"
  deadline=$(( $(date +%s) + 600 ))
  while :; do
    n=$(grep -c "Parsing the prompt took" "$RES/rt/$name.log" 2>/dev/null || echo 0)
    [ "${n:-0}" -ge "$users" ] && break
    kill -0 "$RT_PID" 2>/dev/null || { echo "$(ts) perf_capture $name: runtron exited before decode"; return 1; }
    [ "$(date +%s)" -ge "$deadline" ] && { echo "$(ts) perf_capture $name: prefill did not finish in 600 s"; return 1; }
    sleep 0.5
  done
  sleep 2
  pid=$(pgrep -u jhan -f "^${bin} stream-generate-text" | head -1)
  [ -n "$pid" ] || { echo "$(ts) perf_capture $name: runtron pid not found"; return 1; }
  echo "$(ts) perf_capture $name pid=$pid decode started; record 6 s first (steady decode, tokens ~250-1000 of 4096), then counters 6 s, cache groups 3+3 s, stores 3 s"
  { echo "pid=$pid start=$(ts)"; for t in /proc/$pid/task/*; do echo "$(basename "$t") $(cat "$t/comm" 2>/dev/null)"; done; } >"$out/threads.txt" 2>/dev/null
  sudo -n perf record -g -F 1999 -p "$pid" -o "$LOCAL/$name.perf.data" -- sleep 6 >"$out/perf-record.txt" 2>&1
  sudo -n chown jhan:jhan "$LOCAL/$name.perf.data" 2>/dev/null
  sudo -n perf stat --per-thread -e cycles,instructions -p "$pid" -- sleep 6 >"$out/perf-threads.txt" 2>&1
  sudo -n perf stat --per-thread -e '{cpu/event=0xd1,umask=0x08,name=l1_miss/,cpu/event=0xd1,umask=0x10,name=l2_miss/,cpu/event=0xd1,umask=0x20,name=l3_miss/}' -p "$pid" -- sleep 3 >"$out/perf-cache1.txt" 2>&1
  sudo -n perf stat --per-thread -e '{cpu/event=0x2e,umask=0x41,name=llc_miss/,cpu/event=0xd3,umask=0x01,name=l3m_local/,cpu/event=0xd3,umask=0x02,name=l3m_remote/}' -p "$pid" -- sleep 3 >"$out/perf-cache2.txt" 2>&1
  sudo -n perf stat -e mem_inst_retired.all_stores,mem_inst_retired.all_loads,ocr.demand_rfo.l3_miss,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/ -p "$pid" -- sleep 3 >"$out/perf-stores.txt" 2>&1
  echo "$(ts) perf_capture $name done; runtron still running: $(kill -0 "$RT_PID" 2>/dev/null && echo yes || echo no)"
  return 0
}

[ "${I4500_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
instck=$(mktemp /tmp/i4500-instck.XXXXXX)
pgrep -f '(^|/)bash /home/jhan/workspace/intel-AMX/exec/issue4500-20260918/campaign[.]sh$' >"$instck"
others=$(grep -vx "$$" "$instck" | tr '\n' ' '); rm -f "$instck"
if [ -n "$others" ]; then echo "$(ts) another campaign.sh instance is running (pids $others); this one exits"; exit 1; fi
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== issue4500-20260918 campaign started $(ts) pid $$ BLOCKS=[$BLOCKS] REPS=$REPS REPS_M2=$REPS_M2 REPS_B=$REPS_B GEN=$GEN ==="
for a in base headoff vnni head30; do b=$(arm_bin $a); [ -x "$b" ] || { status "ABORT: binary missing $b"; finish binary-missing; exit 1; }; echo "$(ts) arm $a = $b sha256 $(sha256sum "$b" | cut -c1-16) commit $(git -C "$(dirname "$(dirname "$b")")" rev-parse --short=10 HEAD 2>/dev/null)"; done
kill_ours; sleep 2; remove_our_slice_files
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l))"
[ -s "$RES/rt-results.txt" ] || {
  echo "# issue4500-20260918 runtron results; host delphi-3bda; started $(ts)"
  echo "# arms: base=runtron.main0916 c7844ca2ce (row-major K); headoff=runtron.headoff0916 ff680c8020 TRON_K_VNNI=OFF; vnni=runtron.pr4424 ff680c8020 TRON_K_VNNI=ON; vnni2 = vnni (A/A); vnnikill = vnni + TRON_AMX_DISABLE=1; head30 = tron-tilec/gen/runtron 30c4ac82cb"
  echo "# every run: FPGA attention (USE_HW_ATTN unset), env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE, TRON_LOG_LEVEL=info, prompt 1024, --dont-stop, hugepage file $HPFILE; TPS = 'average tok/s' per user; step ms = 1000/TPS; TTFT = max 'Parsing the prompt took'"
} >>"$RES/rt-results.txt"

status "phase 0: waiting for the CI lease, inactive production units and 256 free hugepages"
echo "$(ts) $(machine_line)"
wait_clear || { finish "preci-hold-before-start"; exit 0; }
echo "$(ts) clear: $(machine_line)"

fail=0
run_or_count() { rt_run "$@"; local rc=$?; [ $rc -eq 0 ] || fail=$((fail + 1)); [ $rc -eq 2 ] && [ $PRECI_STOP = 1 ] && return 2; return 0; }
for block in $BLOCKS; do
  [ $PRECI_STOP = 1 ] && break
  case $block in
    m1)
      status "block m1: attribution, 8 users, tp2/tp4, arms base headoff vnni vnni2 vnnikill (+head30 rep 1)"
      for rep in $(seq 1 "$REPS"); do
        arms="base headoff vnni vnni2 vnnikill"; [ $rep = 1 ] && arms="$arms head30"
        [ $((rep % 2)) -eq 0 ] && arms=$(echo $arms | tr ' ' '\n' | tac | tr '\n' ' ')
        for tp in 2 4; do for arm in $arms; do run_or_count m1 "$arm" "$tp" 8 "$GEN" "$rep" "" fpga || break 3; done; done
        echo "$(ts) m1 repetition $rep done, failed so far: $fail"
      done ;;
    m2)
      status "block m2: launch-phase knob TRON_HWATTN_EARLY_LAUNCH_MIN_B 1 (early) / 100 (late), headoff vs vnni, users 2 and 8, $REPS_M2 repetitions"
      for rep in $(seq 1 "$REPS_M2"); do
        arms="headoff vnni"; [ $((rep % 2)) -eq 0 ] && arms="vnni headoff"
        for tp in 2 4; do for users in 2 8; do for minb in 1 100; do for arm in $arms; do
          run_or_count m2 "$arm" "$tp" "$users" "$GEN" "$rep" "TRON_HWATTN_EARLY_LAUNCH_MIN_B=$minb" "minb$minb" || break 5
        done; done; done; done
        echo "$(ts) m2 repetition $rep done, failed so far: $fail"
      done ;;
    m3)
      status "block m3: Perfetto traces (8 users gen 40, decode passes 10-; categories A and B), plus users 2 tp2"
      CA='-*,+model,+scheduler,+hwattention'; CB="$CA,+hwattention-detail"
      for tp in 2 4; do for arm in base headoff vnni; do
        run_or_count m3 "$arm" "$tp" 8 40 1 "" catA "$LOCAL/m3__${arm}__tp${tp}__8u__catA.perfetto-trace" "10-" "$CA" || break 2
        run_or_count m3 "$arm" "$tp" 8 40 1 "" catB "$LOCAL/m3__${arm}__tp${tp}__8u__catB.perfetto-trace" "10-" "$CB" || break 2
      done; done
      for arm in headoff vnni; do
        run_or_count m3 "$arm" 2 2 40 1 "" catA "$LOCAL/m3__${arm}__tp2__2u__catA.perfetto-trace" "10-" "$CA" || break
      done ;;
    m4)
      status "block m4: perf record then perf counters on headoff and vnni, 8 users, gen 4096"
      for tp in 2 4; do for arm in headoff vnni; do run_or_count m4 "$arm" "$tp" 8 4096 1 "" perf || break 2; done; done ;;
    m1b)
      status "block m1b: per-engine load, users 2 and 4, arms base headoff vnni"
      for rep in $(seq 1 "$REPS_B"); do
        arms="base headoff vnni"; [ $((rep % 2)) -eq 0 ] && arms="vnni headoff base"
        for tp in 2 4; do for users in 2 4; do for arm in $arms; do run_or_count m1b "$arm" "$tp" "$users" "$GEN" "$rep" "" fpga || break 4; done; done; done
        echo "$(ts) m1b repetition $rep done, failed so far: $fail"
      done ;;
    *) echo "$(ts) unknown block $block" ;;
  esac
done

status "summary"
python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" && cat "$RES/summary.md" || { echo "summarize.py failed:"; cat "$RES/summary.err"; }
if [ $PRECI_STOP = 1 ]; then finish "preci-hold (failed $fail)"; elif [ $fail -eq 0 ]; then finish ok; else finish "check-output (failed $fail)"; fi
exit 0
