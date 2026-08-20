#!/usr/bin/env bash
set -u

# Deep-dive campaign harness for delphi-3bda (derived from PDJN
# perfetto-5cat-campaign-v4.sh, tools-u1 variant).
# Differences from the reference:
#   - NO perfetto daemons/capture, NO turbostat, NO dmar perf stat, NO
#     trace-processor validation (spec: tron execution must not be impacted
#     by perfetto or instrumentation).
#   - Adds --pay-for-determinism and --output-token-file (token sha256 per
#     draw, determinism check across draws).
#   - Parameterized: MODEL (required), SLICE_OF, ROUNDS, CAPTURE.
#   - CAPTURE=perf: per-draw `perf stat -p <runtron>` over the benchmark and
#     a decode-window `perf record` on the slice's tron+peer+dev cores.
#   - Explicit CI-window guard (02:30-11:30 UTC refuse) in addition to the
#     runner-active check and the 60 s traffic gate.
#
# Environment:
#   MODEL           required, e.g. ingested-qwen-3-4b-instruct-2507-tp1
#   SLICE_OF        8 -> 1 card, 4 -> 2 cards, 2 -> 4 cards (default 8)
#   ROUNDS          number of draws after smoke (default 20)
#   CAPTURE         none | perf (default none)
#   CAMPAIGN_ROOT   default /scratch/jhan/perf-fluctuation/deep-dive/<ts>
#   PERF_FREQ       perf record sample frequency (default 499)
#   PERF_CALLGRAPH  lbr | fp | dwarf (default lbr; validate at smoke)
#   PERF_DELAY_S    seconds after model-load before perf record (default 10)
#   PERF_WINDOW_S   perf record duration (default 60)
#   PERF_STAT_EXTRA extra comma-joined events appended to the stat list

: "${MODEL:?set MODEL}"
SLICE_OF=${SLICE_OF:-8}
ROUNDS=${ROUNDS:-20}
CAPTURE=${CAPTURE:-none}
CAMPAIGN_ROOT=${CAMPAIGN_ROOT:-/scratch/jhan/perf-fluctuation/deep-dive/dd-$(date -u +%Y%m%dT%H%M%SZ)}
echo "CAMPAIGN_ROOT=$CAMPAIGN_ROOT"

case "$CAPTURE" in none|perf|vtune) ;; *) echo "bad CAPTURE=$CAPTURE" >&2; exit 1;; esac
case "$SLICE_OF" in 2|4|8) ;; *) echo "bad SLICE_OF=$SLICE_OF" >&2; exit 1;; esac

# Default: stock trunk build 12804a81. Overridable for probe builds
# (e.g. install-kvprobe, same rev + TRON_KVWAIT_FILE probe).
INSTALL=${INSTALL:-/scratch/jhan/tron-perfetto-install-20260809}
BIN=$INSTALL/bin/runtron
LIB=$INSTALL/lib
EXPECTED_BIN_SHA=${EXPECTED_BIN_SHA:-17da8295a0004e9a5206a611ab4628ac2e2db69b2773979bdb7ae20ab6d6255f}
KVWAIT=${KVWAIT:-0}
CKB=/home/jhan/workspace/run_checkerboard/checkerboard
SWEEPLOGS=$CKB/sweeps/logs
HP_DIR=/dev/hugepages
FAST112=7-14,24-71,79-86,96-143,151-158,168-215,223-230,240-287
REST112=0-6,15-23,72-78,87-95,144-150,159-167,216-222,231-239
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
RUNNER_SERVICE=actions.runner.positron-ai.delphi-3bda-0.service
GATE_COUNT=/scratch/jhan/perf-fluctuation/deep-dive/tools/gate_count.sh
MIN_FREE_KB=52428800

# vtune (CAPTURE=vtune): per-draw analysis type cycles through VTUNE_TYPES.
# Driverless (perf-based) collection; kernel.perf_event_paranoid is set to 0
# for the campaign and restored in finish().
VTUNE=${VTUNE:-/opt/intel/oneapi/vtune/latest/bin64/vtune}
VTUNE_TYPES=${VTUNE_TYPES:-hotspots,hotspots,uarch-exploration,threading}
VTUNE_DELAY_S=${VTUNE_DELAY_S:-3}
VTUNE_WINDOW_S=${VTUNE_WINDOW_S:-14}
SAVED_PARANOID=
SAVED_PTRACE=

PERF_FREQ=${PERF_FREQ:-499}
PERF_CALLGRAPH=${PERF_CALLGRAPH:-lbr}
PERF_DELAY_S=${PERF_DELAY_S:-10}
PERF_WINDOW_S=${PERF_WINDOW_S:-60}
PERF_STAT_EVENTS="cycles,instructions,cache-references,cache-misses,LLC-loads,LLC-load-misses,dTLB-load-misses,iTLB-load-misses,page-faults,context-switches,cpu-migrations${PERF_STAT_EXTRA:+,$PERF_STAT_EXTRA}"

# Per-card profiling CPU sets: tron_cores[i] + dev_cores[i] from
# config/resource-map.yaml (granite_rapids_6962p) plus the HT sibling
# (+144) of every physical core, so both --peer and non-peer thread
# placements are covered. platform_cores and rinzler_cores excluded.
PERF_CPUS_CARD0="3,7-8,24-29,48-53,147,151-152,168-173,192-197"
PERF_CPUS_CARD1="4,9-10,30-35,54-59,148,153-154,174-179,198-203"
PERF_CPUS_CARD2="5,11-12,36-41,60-65,149,155-156,180-185,204-209"
PERF_CPUS_CARD3="6,13-14,42-47,66-71,150,157-158,186-191,210-215"

NCARDS=$((8 / SLICE_OF))
PERF_CPUS=$PERF_CPUS_CARD0
[ "$NCARDS" -ge 2 ] && PERF_CPUS="$PERF_CPUS,$PERF_CPUS_CARD1"
[ "$NCARDS" -ge 3 ] && PERF_CPUS="$PERF_CPUS,$PERF_CPUS_CARD2"
[ "$NCARDS" -ge 4 ] && PERF_CPUS="$PERF_CPUS,$PERF_CPUS_CARD3"

ALL_DEVS="10:00.0 13:00.0 38:00.0 3b:00.0 90:00.0 93:00.0 b9:00.0 bc:00.0"
STATECAP_DEVS="0000:10:00.0 0000:13:00.0 0000:38:00.0 0000:3b:00.0"
EXPECTED_DEVS=$(printf '%s\n' $ALL_DEVS | head -n "$NCARDS" | LC_ALL=C sort -u)

MUTATED=0
RESTORED=0
FINISHED=0
ROOT_BASHPID=$BASHPID
STAT_PID=
RECORD_PID=

mkdir -p "$CAMPAIGN_ROOT/results" "$CAMPAIGN_ROOT/smoke"
exec 9>"$CAMPAIGN_ROOT/lock"
flock -n 9 || { echo "campaign lock held: $CAMPAIGN_ROOT/lock" >&2; exit 1; }

log() {
  printf '%s %s\n' "$(date -u '+%F %T')" "$*" | tee -a "$CAMPAIGN_ROOT/journal.log"
}

write_status() {
  printf '%s\n' "$1" > "$CAMPAIGN_ROOT/status.txt"
  log "STATUS $1"
}

# runtron renames its main thread, so liveness/kill must also match the full
# command line (see reference harness).
engine_alive() {
  pgrep -u jhan -x runtron >/dev/null 2>&1 || pgrep -u jhan -f "^$BIN " >/dev/null 2>&1
}

kill_engine() {
  pkill -u jhan -f '[r]un-benchmark\.sh' 2>/dev/null || true
  pkill -u jhan -x runtron 2>/dev/null || true
  pkill -u jhan -f "^$BIN " 2>/dev/null || true
  local i
  for i in $(seq 1 20); do
    engine_alive || return 0
    sleep 1
  done
  pkill -9 -u jhan -x runtron 2>/dev/null || true
  pkill -9 -u jhan -f "^$BIN " 2>/dev/null || true
  sleep 2
  ! engine_alive
}

stop_perf() {
  [ -n "$STAT_PID" ] && sudo -n kill -INT "$STAT_PID" 2>/dev/null || true
  STAT_PID=
  [ -n "$RECORD_PID" ] && sudo -n kill -INT "$RECORD_PID" 2>/dev/null || true
  RECORD_PID=
  sudo -n pkill -INT -f '[p]erf record -F' 2>/dev/null || true
  sudo -n pkill -INT -f '[p]erf stat -e' 2>/dev/null || true
  pkill -f '[v]tune -collect' 2>/dev/null || true
  sleep 2
}

set_paranoid() {
  SAVED_PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid)
  SAVED_PTRACE=$(cat /proc/sys/kernel/yama/ptrace_scope)
  sudo -n sysctl -q kernel.perf_event_paranoid=0
  # vtune threading analysis attaches via ptrace (hotspots/uarch do not).
  sudo -n sysctl -q kernel.yama.ptrace_scope=0
  log "perf_event_paranoid: $SAVED_PARANOID -> 0, ptrace_scope: $SAVED_PTRACE -> 0 (vtune)"
}

restore_paranoid() {
  [ -n "$SAVED_PARANOID" ] || return 0
  sudo -n sysctl -q "kernel.perf_event_paranoid=$SAVED_PARANOID" 2>/dev/null || true
  sudo -n sysctl -q "kernel.yama.ptrace_scope=${SAVED_PTRACE:-1}" 2>/dev/null || true
  log "perf_event_paranoid restored to $SAVED_PARANOID, ptrace_scope to ${SAVED_PTRACE:-1}"
  SAVED_PARANOID=
}

cleanup_draw() {
  stop_perf
  kill_engine || log "WARN runtron survived kill escalation"
  sudo -n find "$HP_DIR" -maxdepth 1 -type f \( -name 'libpos*' -o -name 'slice-*' \) -delete 2>/dev/null || true
  sleep 2
}

# Per-card PCIe state: link speed/width, device/error status, AER counters.
# Read-only; used by STATECAP=1 draws post-load and post-benchmark.
capture_card_state() {
  local outfile=$1 dev
  {
    date -u '+%FT%T.%3NZ'
    for dev in $STATECAP_DEVS; do
      echo "== $dev"
      sudo -n lspci -vvv -s "$dev" 2>/dev/null | grep -E 'LnkSta:|DevSta:|CESta:|UESta:'
      cat "/sys/bus/pci/devices/$dev/current_link_speed" "/sys/bus/pci/devices/$dev/current_link_width" 2>/dev/null
      for f in aer_dev_correctable aer_dev_nonfatal aer_dev_fatal; do
        echo "-- $f"; cat "/sys/bus/pci/devices/$dev/$f" 2>/dev/null
      done
    done
  } > "$outfile" 2>&1
}

check_storage() {
  local free_kb
  free_kb=$(df -Pk /scratch | awk 'NR==2 {print $4}')
  if [ "${free_kb:-0}" -lt "$MIN_FREE_KB" ]; then
    log "FAIL storage below floor: ${free_kb}kB free"
    return 1
  fi
  return 0
}

# platformd config PATCH with dual-format support: pre-0.11 uses one engine
# template + count; v0.11.0 removed count and requires explicitly named
# engines (Rhys Jordan, 2026-08-11). Try old format; on HTTP >=400 send the
# equivalent named-engine payload (default-0..default-3).
patch_config() {
  local models_json=$1 code named=""
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 30 -X PATCH -H 'Content-Type: application/json'     -d "{\"inference\":{\"engines\":{\"default\":{\"models\":$models_json,\"tensor_parallelism\":2,\"count\":4}}}}"     http://localhost:8080/api/config 2>/dev/null)
  if [ "${code:-000}" -ge 400 ] 2>/dev/null; then
    local i
    for i in 0 1 2 3; do
      named="$named${named:+,}\"default-$i\":{\"models\":$models_json,\"tensor_parallelism\":2}"
    done
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 30 -X PATCH -H 'Content-Type: application/json'       -d "{\"inference\":{\"engines\":{$named}}}" http://localhost:8080/api/config 2>/dev/null)
    log "platformd v0.11+ named-engine config used (http $code)"
  fi
}

restore_body() {
  # 3c51: no serving to restore (no rinzler; platformd auto_start=false).
  # Reset core-power classes and clean hugepages only.
  $ISST --cpu "$FAST112" core-power assoc --clos 0 >/dev/null 2>&1 || true
  $ISST --cpu "$REST112" core-power assoc --clos 3 >/dev/null 2>&1 || true
  sudo -n find /dev/hugepages -type f -delete 2>/dev/null || true
  RESTORED=1
  touch "$CAMPAIGN_ROOT/RESTORED"
  date +%s > "$CAMPAIGN_ROOT/restored-epoch.txt"
  log "RESTORE done (3c51 minimal: hugepages + core-power)"
  return 0
}

restore_all() {
  [ "$MUTATED" -eq 1 ] || return 0
  log "RESTORE begin"
  restore_body || restore_body || touch "$CAMPAIGN_ROOT/RESTORE_FAILED"
}

finish() {
  local rc=$?
  [ "$BASHPID" -eq "$ROOT_BASHPID" ] || return 0
  [ "$FINISHED" -eq 0 ] || return 0
  FINISHED=1
  trap - EXIT TERM INT HUP
  if [ "$MUTATED" -eq 1 ]; then
    cleanup_draw
    restore_all
  fi
  restore_paranoid
  date +%s > "$CAMPAIGN_ROOT/finished-epoch.txt"
  [ "$RESTORED" -eq 1 ] || [ "$MUTATED" -eq 0 ] || rc=1
  if [ "$RESTORED" -eq 1 ]; then
    printf '%s\n' restored > "$CAMPAIGN_ROOT/status.txt"
  fi
  printf '%s\n' "$rc" > "$CAMPAIGN_ROOT/harness-exit-code.txt"
  exit "$rc"
}
trap finish EXIT
trap 'exit 143' TERM INT HUP

wait_marker() {
  local file=$1 pattern=$2 limit=$3 i
  for i in $(seq 1 "$limit"); do
    [ -f "$file" ] && grep -aq "$pattern" "$file" && return 0
    sleep 1
  done
  return 1
}

# Prints: generate_mean parse_mean ttft_mean ttlt_mean
read_metrics() {
  python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))["metrics"]
def g(k):
    try: return d[k]["mean"]
    except Exception: return ""
print(g("generate"), g("parse"), g("ttft"), g("ttlt"))
PY
}

capture_identity() {
  local pid=$1 out=$2
  tr '\0' ' ' < "/proc/$pid/cmdline" > "$out/runtron-command.txt"
  printf '\n' >> "$out/runtron-command.txt"
  {
    tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(USE_HW_ATTN|TRON_USE_SPECULATION|TRON_LOG_PLACEMENT|TRON_MAX_LOGITS_CHUNK_SIZE|TRON_KVWAIT_FILE|LD_LIBRARY_PATH)=' || true
    if tr '\0' '\n' < "/proc/$pid/environ" | grep -q '^SYSTEM_CONFIG='; then
      tr '\0' '\n' < "/proc/$pid/environ" | grep '^SYSTEM_CONFIG='
    else
      printf 'SYSTEM_CONFIG=<unset>\n'
    fi
  } > "$out/runtron-environment.txt"
  date -u '+%FT%TZ' > "$out/capture-timestamp.txt"
}

append_result() {
  local name=$1 status=$2 gen=$3 parse=$4 ttft=$5 ttlt=$6 tokensha=$7 out=$8 logf=$9 reason=${10}
  reason=${reason//,/;}
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$name" "$status" "$gen" "$parse" "$ttft" "$ttlt" "$tokensha" "$out" "$logf" "$reason" >> "$CAMPAIGN_ROOT/results.csv"
}

run_draw() {
  local name=$1 out=$2 mark wrap logdir logf pid cfg devs ndev i metrics stage=
  local gen parse ttft ttlt tokensha placement_count
  mkdir -p "$out"
  log "$name begin (CAPTURE=$CAPTURE)"

  cleanup_draw
  if ! check_storage; then
    append_result "$name" failed '' '' '' '' '' "$out" '' 'insufficient storage'
    return 1
  fi

  mark="/var/tmp/jhan/deepdive-${name}-$$.mark"
  mkdir -p /var/tmp/jhan
  touch "$mark"
  (
    cd "$CKB" || exit 1
    env -u SYSTEM_CONFIG USE_HW_ATTN=0 TRON_LOG_PLACEMENT=1 \
      ${KVWAIT:+$( [ "$KVWAIT" = 1 ] && printf 'TRON_KVWAIT_FILE=%s' "$out/kvwait.bin" )} \
      ${CHUNKSIZE:+TRON_MAX_LOGITS_CHUNK_SIZE=$CHUNKSIZE} \
      EXTRA_RUNTRON_ARGS="-s 2954953865 --pay-for-determinism --dont-stop --threshold_p 0 --output-token-file $out/tokens.out" \
      RUNTRON_BIN="$BIN" LD_LIBRARY_PATH="$LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
      timeout 1200 ./run-benchmark.sh \
      -m "$MODEL" -u 1 -i 1 --slice-of "$SLICE_OF" --slice-start 0 \
      --prompt-length 1024 --gen-length 4096 \
      --shared-system-prompt-length 256 --speculation 0 \
      > "$out/run-benchmark.log" 2>&1
  ) &
  wrap=$!

  logdir=
  for i in $(seq 1 120); do
    logdir=$(find "$SWEEPLOGS" -maxdepth 1 -type d -name "*-1-1" -newer "$mark" 2>/dev/null | sort | tail -1)
    [ -n "$logdir" ] && ls "$logdir"/log.* >/dev/null 2>&1 && break
    logdir=
    sleep 1
  done
  if [ -z "$logdir" ]; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" '' 'no log directory'
    return 1
  fi
  logf=$(ls "$logdir"/log.* | head -1)
  printf '%s\n' "$logf" > "$out/log-source.txt"
  if ! wait_marker "$logf" 'Configured instance' 90; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'no configured marker'
    return 1
  fi
  cfg=$(grep -a 'Configured instance' "$logf" | head -1)
  if ! printf '%s\n' "$cfg" | grep -q "Configured instance 0,$SLICE_OF "; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'wrong instance'
    return 1
  fi
  if ! wait_marker "$logf" 'Bitfile Release Code' 120; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'no bitfile lines'
    return 1
  fi
  sleep 2
  devs=$(grep -a 'Bitfile Release Code' "$logf" | awk '{for(i=2;i<=NF;i++) if($i=="Bitfile") print tolower($(i-1))}' | sed 's/:$//' | LC_ALL=C sort -u)
  ndev=$(printf '%s\n' "$devs" | grep -c .)
  if [ "$ndev" -ne "$NCARDS" ] || [ "$devs" != "$EXPECTED_DEVS" ]; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'wrong device set'
    return 1
  fi
  # Bitfile consistency: the nightly can install a new FPGA bitfile; record
  # per draw and fail hard on a mid-campaign change.
  bitrel=$(grep -a -m1 'Bitfile Release Code' "$logf" | grep -oE 'Release Code [0-9.]+ Release Date [0-9-]+')
  printf '%s\n' "$bitrel" > "$out/bitfile.txt"
  if [ -z "${CAMPAIGN_BITREL:-}" ]; then
    CAMPAIGN_BITREL="$bitrel"
    log "$name bitfile: $bitrel"
  elif [ "$bitrel" != "$CAMPAIGN_BITREL" ]; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'bitfile changed mid-campaign'
    log "$name FAIL bitfile changed: [$bitrel] vs [$CAMPAIGN_BITREL]"
    return 1
  fi
  pid=
  for i in $(seq 1 10); do
    pid=$(pgrep -n -u jhan -x runtron 2>/dev/null || true)
    [ -n "$pid" ] || pid=$(pgrep -n -u jhan -f "^$BIN " 2>/dev/null || true)
    [ -n "$pid" ] && break
    sleep 1
  done
  if [ -z "$pid" ]; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'no runtron pid'
    return 1
  fi
  capture_identity "$pid" "$out"
  if ! wait_marker "$logf" 'Allocating and loading the model took' 300; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'model load timeout'
    return 1
  fi
  # Software-attention hard gate (standing rule): the banner must be present.
  # The banner lands ~15-55 ms AFTER the load-complete line, so poll rather
  # than grep once (instant grep lost that race on the tp4 smoke draw).
  if ! wait_marker "$logf" 'HW attention disabled' 30; then
    kill_engine
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'sw-attention banner missing'
    return 1
  fi

  if [ "${PAGEMAP:-0}" = 1 ]; then
    # Physical placement snapshot: PFNs of hugepage-backed VMAs (one sample
    # per 1 GiB page) + per-VMA NUMA breakdown. Read-only, after model load.
    sudo -n python3 /scratch/jhan/perf-fluctuation/deep-dive/tools/pagemap_dump.py "$pid" \
      > "$out/pagemap.txt" 2> "$out/pagemap.err" || log "$name WARN pagemap dump failed"
    sudo -n cat "/proc/$pid/numa_maps" > "$out/numa_maps.txt" 2>/dev/null || true
  fi

  if [ "${STATECAP:-0}" = 1 ]; then
    capture_card_state "$out/cardstate-postload.txt"
  fi

  if [ "${SMICOUNT:-0}" = 1 ]; then
    # SMI counter (MSR 0x34) before the benchmark window; cpu0 + a tron core.
    { printf 'pre cpu0 %s\n' "$(sudo -n rdmsr -p 0 0x34 2>/dev/null)";
      printf 'pre cpu24 %s\n' "$(sudo -n rdmsr -p 24 0x34 2>/dev/null)"; } > "$out/smi.txt"
  fi

  if [ "${RAPLCAP:-0}" = 1 ]; then
    # package energy counter before the benchmark; wraps at max_energy_range_uj.
    { printf 'range %s\n' "$(sudo -n cat /sys/class/powercap/intel-rapl:0/max_energy_range_uj 2>/dev/null)";
      printf 'pre %s %s\n' "$(date +%s.%N)" "$(sudo -n cat /sys/class/powercap/intel-rapl:0/energy_uj 2>/dev/null)"; } > "$out/rapl.txt"
  fi

  if [ "${THROTTLELOG:-0}" = 1 ]; then
    # clear sticky throttle-log bits so the post-benchmark read shows only
    # events from this draw (status bits are read-only; write-0 clears logs).
    for c in 24 25 48 151; do
      sudo -n wrmsr -p $c 0x19C 0 2>/dev/null
      sudo -n wrmsr -p $c 0x64F 0 2>/dev/null
    done
    sudo -n wrmsr -p 0 0x1B1 0 2>/dev/null
  fi

  if [ "${SAMPLER:-0}" = 1 ]; then
    # 150us MSR sampler (APERF/MPERF/THERM on cpu24+cpu151, pkg energy+therm),
    # pinned to cpu1, self-terminates after 40s; covers the whole benchmark.
    sudo -n nohup /scratch/jhan/perf-fluctuation/deep-dive/tools/msrsamp \
      "$out/msrsamp.bin" 150 40 24 151 1 > "$out/msrsamp.log" 2>&1 &
    SAMPPID=$!
  fi

  if [ "${UNCORESTAT:-0}" = 1 ]; then
    # system-wide memory-path counters over the benchmark, split per socket.
    sudo -n nohup perf stat -a --per-socket \
      -e uncore_imc/cas_count_read_sch0/,uncore_imc/cas_count_read_sch1/,uncore_imc/cas_count_write_sch0/,uncore_imc/cas_count_write_sch1/,LLC-load-misses,LLC-loads \
      -o "$out/uncore-stat.txt" -- sleep 30 > /dev/null 2>&1 &
  fi

  if [ "$CAPTURE" = perf ]; then
    # Whole-benchmark counters for the runtron process (load already done;
    # covers prefill + decode; decode dominates at gen-length 4096).
    sudo -n perf stat -e "$PERF_STAT_EVENTS" -p "$pid" -o "$out/perf-stat.txt" &
    STAT_PID=$!
    # Decode-window sampled profile on the slice's cores (system-wide on
    # those CPUs: catches runtron threads AND any interfering task).
    # perf.data is staged on LOCAL disk (/scratch is NFS; writing the sample
    # stream over NFS during the measured window would add I/O jitter) and
    # moved to $out after the benchmark ends.
    stage="/var/tmp/jhan/deepdive-${name}-$$.perf.data"
    sudo -n rm -f "$stage" 2>/dev/null || true
    (
      sleep "$PERF_DELAY_S"
      sudo -n perf record -F "$PERF_FREQ" --call-graph "$PERF_CALLGRAPH" \
        -C "$PERF_CPUS" -o "$stage" -- sleep "$PERF_WINDOW_S" \
        >> "$out/perf-record.log" 2>&1
    ) &
    RECORD_PID=$!
    printf 'freq=%s callgraph=%s cpus=%s delay=%s window=%s\n' \
      "$PERF_FREQ" "$PERF_CALLGRAPH" "$PERF_CPUS" "$PERF_DELAY_S" "$PERF_WINDOW_S" > "$out/perf-record-params.txt"
  fi

  if [ "$CAPTURE" = vtune ]; then
    # Analysis type cycles through VTUNE_TYPES by draw number (smoke uses
    # the first). Attach to runtron for a fixed decode window.
    local vtypes vtype nidx
    IFS=, read -ra vtypes <<< "$VTUNE_TYPES"
    nidx=0
    [[ "$name" =~ ^draw_([0-9]+)$ ]] && nidx=$(( (10#${BASH_REMATCH[1]} - 1) % ${#vtypes[@]} ))
    vtype=${vtypes[$nidx]}
    printf '%s\n' "$vtype" > "$out/vtune-type.txt"
    log "$name vtune analysis: $vtype"
    (
      sleep "$VTUNE_DELAY_S"
      case "$vtype" in
        hotspots)
          "$VTUNE" -collect hotspots -knob sampling-mode=hw \
            -target-pid "$pid" -d "$VTUNE_WINDOW_S" -r "$out/vtune_r" \
            > "$out/vtune.log" 2>&1 ;;
        *)
          "$VTUNE" -collect "$vtype" \
            -target-pid "$pid" -d "$VTUNE_WINDOW_S" -r "$out/vtune_r" \
            > "$out/vtune.log" 2>&1 ;;
      esac
    ) &
    RECORD_PID=$!
  fi

  for i in $(seq 1 1260); do
    kill -0 "$wrap" 2>/dev/null || break
    sleep 1
  done
  wait "$wrap" || true
  if [ "$CAPTURE" = perf ]; then
    [ -n "$RECORD_PID" ] && wait "$RECORD_PID" 2>/dev/null || true
    RECORD_PID=
    [ -n "$STAT_PID" ] && sudo -n kill -INT "$STAT_PID" 2>/dev/null || true
    sleep 2
    [ -n "$STAT_PID" ] && wait "$STAT_PID" 2>/dev/null || true
    STAT_PID=
    if [ -n "${stage:-}" ] && sudo -n test -s "$stage"; then
      sudo -n chown jhan:jhan "$stage" 2>/dev/null || true
      mv "$stage" "$out/perf.data" || true
    fi
    stage=
  fi
  if [ "$CAPTURE" = vtune ]; then
    # vtune finalization (symbol resolution) continues after the collection
    # window; give it up to 5 min before declaring the draw's capture failed.
    for i in $(seq 1 300); do
      kill -0 "$RECORD_PID" 2>/dev/null || break
      sleep 1
    done
    wait "$RECORD_PID" 2>/dev/null || true
    RECORD_PID=
  fi
  if [ "${STATECAP:-0}" = 1 ]; then
    capture_card_state "$out/cardstate-postbench.txt"
  fi
  if [ "${SMICOUNT:-0}" = 1 ]; then
    { printf 'post cpu0 %s\n' "$(sudo -n rdmsr -p 0 0x34 2>/dev/null)";
      printf 'post cpu24 %s\n' "$(sudo -n rdmsr -p 24 0x34 2>/dev/null)"; } >> "$out/smi.txt"
  fi
  if [ "${RAPLCAP:-0}" = 1 ]; then
    printf 'post %s %s\n' "$(date +%s.%N)" "$(sudo -n cat /sys/class/powercap/intel-rapl:0/energy_uj 2>/dev/null)" >> "$out/rapl.txt"
  fi
  if [ "${THROTTLELOG:-0}" = 1 ]; then
    { for c in 24 25 48 151; do
        printf 'cpu%s 19C %s 64F %s\n' "$c" "$(sudo -n rdmsr -p $c 0x19C 2>/dev/null)" "$(sudo -n rdmsr -p $c 0x64F 2>/dev/null)"
      done
      printf 'pkg 1B1 %s\n' "$(sudo -n rdmsr -p 0 0x1B1 2>/dev/null)"; } > "$out/throttle.txt"
  fi
  if [ "${SAMPLER:-0}" = 1 ]; then
    wait "$SAMPPID" 2>/dev/null || true
    sudo -n chown jhan "$out/msrsamp.bin" 2>/dev/null || true
  fi
  if [ "${UNCORESTAT:-0}" = 1 ]; then
    sleep 2
    sudo -n chown jhan "$out/uncore-stat.txt" 2>/dev/null || true
  fi
  kill_engine || true
  cp "$logf" "$out/runtron.log"
  placement_count=$(grep -ac 'Tensor device counts:' "$out/runtron.log" || true)
  printf '%s\n' "$placement_count" > "$out/placement-count.txt"
  metrics="$logdir/metrics.json"
  if [ ! -f "$metrics" ]; then
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'no metrics'
    return 1
  fi
  cp "$metrics" "$out/metrics.json"
  read -r gen parse ttft ttlt <<< "$(read_metrics "$out/metrics.json" 2>/dev/null || true)"
  if [ -z "$gen" ]; then
    append_result "$name" failed '' '' '' '' '' "$out" "$logf" 'unreadable generation metric'
    return 1
  fi
  tokensha=
  [ -s "$out/tokens.out" ] && tokensha=$(sha256sum "$out/tokens.out" | awk '{print $1}')
  [ -n "$tokensha" ] || log "$name WARN tokens.out missing or empty"
  if [ "$CAPTURE" = perf ]; then
    [ -s "$out/perf.data" ] || { append_result "$name" failed "$gen" "$parse" "$ttft" "$ttlt" "$tokensha" "$out" "$logf" 'perf.data missing'; return 1; }
    [ -s "$out/perf-stat.txt" ] || log "$name WARN perf-stat.txt missing"
  fi
  if [ "$KVWAIT" = 1 ] && [ ! -s "$out/kvwait.bin" ]; then
    append_result "$name" failed "$gen" "$parse" "$ttft" "$ttlt" "$tokensha" "$out" "$logf" 'kvwait.bin missing'
    return 1
  fi
  if [ "$CAPTURE" = vtune ]; then
    if ! ls "$out"/vtune_r*/ >/dev/null 2>&1; then
      append_result "$name" failed "$gen" "$parse" "$ttft" "$ttlt" "$tokensha" "$out" "$logf" 'vtune result missing'
      return 1
    fi
  fi
  append_result "$name" ok "$gen" "$parse" "$ttft" "$ttlt" "$tokensha" "$out" "$logf" ''
  log "$name OK generate=$gen tok/s token_sha=${tokensha:0:12}"
  return 0
}

write_status preparing

# --- Preflight (read-only; nothing mutated before the gates below) ---

# delphi-3c51 (Bill's machine, exclusive use per owner 2026-08-12): no nightly
# CI on this host — no time-window guard. Traffic gate below still applies.
log "host=delphi-3c51: no CI window on this machine" 

if systemctl is-active --quiet "$RUNNER_SERVICE" || pgrep -f '[R]unner.Worker' >/dev/null 2>&1; then
  log "PREFLIGHT FAIL: CI runner is active"
  exit 1
fi
if pgrep -x runtron >/dev/null 2>&1 || pgrep -f "^$BIN " >/dev/null 2>&1 || pgrep -f '[r]un-benchmark\.sh' >/dev/null 2>&1; then
  log "PREFLIGHT FAIL: existing runtron/run-benchmark process"
  exit 1
fi

actual_sha=$(sha256sum "$BIN" 2>/dev/null | awk '{print $1}')
free_kb=$(df -Pk /scratch | awk 'NR==2 {print $4}')
preflight_fail=
[ -x "$BIN" ] || preflight_fail="$preflight_fail binary"
[ "$actual_sha" = "$EXPECTED_BIN_SHA" ] || preflight_fail="$preflight_fail binary-hash"
[ -x "$CKB/run-benchmark.sh" ] || preflight_fail="$preflight_fail checkerboard"
[ -x "$GATE_COUNT" ] || [ -f "$GATE_COUNT" ] || preflight_fail="$preflight_fail gate-count"
[ "${free_kb:-0}" -ge "$MIN_FREE_KB" ] || preflight_fail="$preflight_fail storage"
sudo -n true 2>/dev/null || preflight_fail="$preflight_fail sudo"
if [ "$CAPTURE" = perf ]; then
  command -v perf >/dev/null 2>&1 || preflight_fail="$preflight_fail perf"
  sudo -n perf record -F 99 --call-graph "$PERF_CALLGRAPH" -C 3 -o "$CAMPAIGN_ROOT/perf-selftest.data" -- sleep 1 >/dev/null 2>&1 \
    || preflight_fail="$preflight_fail perf-record-selftest"
  sudo -n rm -f "$CAMPAIGN_ROOT/perf-selftest.data" 2>/dev/null || true
fi
if [ "$CAPTURE" = vtune ]; then
  [ -x "$VTUNE" ] || preflight_fail="$preflight_fail vtune-binary"
fi
[ -z "$preflight_fail" ] || { log "PREFLIGHT FAIL:$preflight_fail"; exit 1; }

cat > "$CAMPAIGN_ROOT/identity.env" <<EOF
HOST=delphi-3c51
MODEL=$MODEL
SLICE_OF=$SLICE_OF
NCARDS=$NCARDS
ROUNDS=$ROUNDS
CAPTURE=$CAPTURE
BIN=$BIN
BIN_SHA256=$actual_sha
SEED_LITERAL=2954953865
PAY_FOR_DETERMINISM=1
THRESHOLD_P=0
PROMPT_LENGTH=1024
GEN_LENGTH=4096
SHARED_SYSTEM_PROMPT_LENGTH=256
USERS=1
INSTANCES=1
SPECULATION=0
USE_HW_ATTN=0
PERF_FREQ=$PERF_FREQ
PERF_CALLGRAPH=$PERF_CALLGRAPH
PERF_DELAY_S=$PERF_DELAY_S
PERF_WINDOW_S=$PERF_WINDOW_S
PERF_CPUS=$PERF_CPUS
PERF_STAT_EVENTS=$PERF_STAT_EVENTS
VTUNE_TYPES=$VTUNE_TYPES
VTUNE_DELAY_S=$VTUNE_DELAY_S
VTUNE_WINDOW_S=$VTUNE_WINDOW_S
EOF
printf 'draw,status,generate_tok_s,parse_tok_s,ttft_s,ttlt_s,token_sha256,result_dir,source_log,reason\n' > "$CAMPAIGN_ROOT/results.csv"
log "PREFLIGHT OK: window, runner idle, binary hash, tools, storage, sudo"

if [ "${PREFLIGHT_ONLY:-0}" = 1 ]; then
  touch "$CAMPAIGN_ROOT/PREFLIGHT_ONLY_OK"
  write_status preflight_only_ok
  exit 0
fi

date +%s > "$CAMPAIGN_ROOT/mutation-start-epoch.txt"
MUTATED=1
write_status mutating_machine

# Traffic gate (PDJN v3): refuse to take serving down while genuine remote
# clients are connected (nightly-soak protection; catches bad-night overruns).
traffic_hits=0
for _ts in 1 2 3 4 5 6; do
  _out=$(bash "$GATE_COUNT")
  _conns=$(printf '%s\n' "$_out" | head -1)
  log "traffic gate sample $_ts: $_conns non-self conns$(printf '%s\n' "$_out" | sed -n 2p | sed 's/^/ peers:/')"
  [ "$_conns" -gt 0 ] 2>/dev/null && traffic_hits=$((traffic_hits+1))
  sleep 10
done
if [ "$traffic_hits" -ge 3 ] && [ "${FORCE_TRAFFIC_OK:-0}" != "1" ]; then
  log "REFUSED: persistent client traffic on :80 ($traffic_hits/6 samples nonzero) — a remote driver (nightly soak?) may be active. Set FORCE_TRAFFIC_OK=1 to override."
  exit 1
fi

sudo -n /opt/positron/ci/ci-runner.sh stop >> "$CAMPAIGN_ROOT/journal.log" 2>&1 || true

sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null || true
for i in $(seq 1 13); do
  [ "$(pgrep -x rinzler | wc -l)" -eq 0 ] && break
  sleep 5
done
[ "$(pgrep -x rinzler | wc -l)" -eq 0 ] || { log "FAIL rinzler did not stop"; exit 1; }
sudo -n find /dev/hugepages -type f -delete 2>/dev/null || true
$ISST --cpu "$FAST112" core-power assoc --clos 0 >/dev/null 2>&1 || true
$ISST --cpu "$REST112" core-power assoc --clos 3 >/dev/null 2>&1 || true

[ "$CAPTURE" = vtune ] && set_paranoid

write_status smoke
if ! run_draw smoke "$CAMPAIGN_ROOT/smoke" ; then
  log "HARD SMOKE FAILURE"
  exit 1
fi
tail -n 1 "$CAMPAIGN_ROOT/results.csv" > "$CAMPAIGN_ROOT/smoke/result.csv"
printf 'draw,status,generate_tok_s,parse_tok_s,ttft_s,ttlt_s,token_sha256,result_dir,source_log,reason\n' > "$CAMPAIGN_ROOT/results.csv"
touch "$CAMPAIGN_ROOT/SMOKE_OK"

write_status campaign
scheduled=0
successful=0
for n in $(seq 1 "$ROUNDS"); do
  scheduled=$((scheduled + 1))
  name=$(printf 'draw_%02d' "$n")
  run_draw "$name" "$CAMPAIGN_ROOT/results/$name" && successful=$((successful + 1))
done
printf '%s\n' "$scheduled" > "$CAMPAIGN_ROOT/scheduled-count.txt"
printf '%s\n' "$successful" > "$CAMPAIGN_ROOT/successful-count.txt"
touch "$CAMPAIGN_ROOT/ALL_DRAWS_SCHEDULED"
log "CAMPAIGN finished: $successful/$scheduled successful draws"

write_status awaiting_restore
exit 0
