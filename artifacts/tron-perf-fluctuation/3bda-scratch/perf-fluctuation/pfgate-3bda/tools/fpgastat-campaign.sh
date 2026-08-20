#!/usr/bin/env bash
set -u

# One unattended 20-draw Perfetto campaign on delphi-3bda.
# Five-category variant: scheduler, model, matmul, driver, gen (no driver-detail).
# v3: per-draw Perfetto configs generated from the shared template
# (~/workspace/common/perfetto.cfg-template, RING_BUFFER fill policy) and a
# per-draw turbostat capture (results/<draw>/power.tsv) for the core-frequency
# and package-power section of the report.
# Required environment: MODEL. CAMPAIGN_ROOT may be overridden; it defaults to
# a timestamped directory under /scratch/jhan/perf-fluctuation.
#
# pfgate variant (2026-08-12, RUNBOOK-perfetto-gated-inter-fwd-pass.md):
# gated-trace binary at install-pfgate (window gate: trace events emitted only
# inside the inter-fwd-pass window during decode); runtron additionally runs
# with --pay-for-determinism and --output-token-file <draw>/tokens.out.
# Campaign roots live under /scratch/jhan/perf-fluctuation/pfgate-3bda/.

: "${MODEL:?set MODEL}"
CAMPAIGN_ROOT=${CAMPAIGN_ROOT:-/scratch/jhan/perf-fluctuation/pfgate-3bda/fpgastat-$(date -u +%Y%m%dT%H%M%SZ)}
echo "CAMPAIGN_ROOT=$CAMPAIGN_ROOT"

ROUNDS=${ROUNDS:-20}
INSTALL=${INSTALL:-/scratch/jhan/perf-fluctuation/deep-dive/install-fpgause}
BIN=$INSTALL/bin/runtron
LIB=$INSTALL/lib
EXPECTED_BIN_SHA=${EXPECTED_BIN_SHA:?set EXPECTED_BIN_SHA for install-fpgause}
CKB=/home/jhan/workspace/run_checkerboard/checkerboard
SWEEPLOGS=$CKB/sweeps/logs
TB=/scratch/jhan/tools/tracebox
TP=/usr/local/bin/trace_processor
REPORT_PY=/scratch/jhan/perf-fluctuation/pfgate-3bda/fence13pf-tp4-20260813T210954Z/perfetto-5cat-report-v3.py
HP_DIR=/dev/hugepages
FAST112=7-14,24-71,79-86,96-143,151-158,168-215,223-230,240-287
REST112=0-6,15-23,72-78,87-95,144-150,159-167,216-222,231-239
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
RUNNER_SERVICE=actions.runner.positron-ai.delphi-3bda-0.service
EXPECTED_DEVS="10:00.0
13:00.0
38:00.0
3b:00.0"
MIN_FREE_KB=52428800
CATEGORIES="scheduler"
PERFETTO_TPL_SRC=${PERFETTO_TPL_SRC:-/home/jhan/workspace/common/perfetto.cfg-fpgastat}
# arm B review (2026-08-17): smoke barrier + matched-control knobs.
# SMOKE_MIN_TPS: single hard threshold, no ambiguous band — below it the
# campaign refuses to start (arm A precedent: capture halved TPS and 16
# perturbed draws ran anyway). EXPECTED_TOKENS_SHA: deterministic qwen-3-4b
# tp4 token reference (identical across wadefix on/off draws); empty string
# skips the check. CONTROL_ROUNDS: extra draws with fence-flip AND poller
# both disabled — same binary/config/host state — for flip-overhead
# accounting (the wadefix-on campaign is NOT a matched control).
SMOKE_MIN_TPS=${SMOKE_MIN_TPS:-160}
EXPECTED_TOKENS_SHA=${EXPECTED_TOKENS_SHA:-66af1d583183f4b09a47a253e4eb909235b8cfdd19da9bf2c631720934f193c4}
CONTROL_ROUNDS=${CONTROL_ROUNDS:-3}
# Tracer core: MUST NOT collide with a runtron-pinned core. Instance-0 pins
# observed on 3bda tp4: TX 3/4/5/6, work_queue 24, worker 25, RX 147-150.
# core 5 collided with TX-38 and halved TPS (arm A + arm B smoke 2026-08-17).
TRACER_CORE=${TRACER_CORE:-16}
# Columns from ~/workspace/common/template-commands.sh; the 5 s interval (vs the
# template's 30 s) fits ~25-30 samples into the post-load benchmark window.
TURBOSTAT_SHOW=Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt,RAMWatt
TURBOSTAT_INTERVAL=5

TRACED_PID=
PROBES_PID=
TURBOSTAT_PID=
DAEMONS_STARTED=0
MUTATED=0
RESTORED=0
FINISHED=0
ROOT_BASHPID=$BASHPID

mkdir -p "$CAMPAIGN_ROOT/results" "$CAMPAIGN_ROOT/smoke" "$CAMPAIGN_ROOT/analysis"
exec 9>"$CAMPAIGN_ROOT/lock"
flock -n 9 || { echo "campaign lock held: $CAMPAIGN_ROOT/lock" >&2; exit 1; }
# Host-wide lock: the per-root lock cannot serialize two differently named
# campaign roots (other sessions also run campaigns on this machine). Local
# filesystem on purpose — flock over NFS is not trusted here.
mkdir -p /var/tmp/jhan
exec 8>/var/tmp/jhan/3bda-campaign.lock
flock -n 8 || { echo "host campaign lock held: /var/tmp/jhan/3bda-campaign.lock" >&2; exit 1; }
printf '%s\n' "$$" > "$CAMPAIGN_ROOT/harness.pid"
hostname > "$CAMPAIGN_ROOT/harness.host"


# lowered_freq: direct MSR access via /dev/cpu/N/msr (rdmsr/wrmsr are not
# installed on 3bda; the msr module is loaded). Read prints hex64 or empty.
msr_read() {
  sudo -n dd if=/dev/cpu/$1/msr bs=8 count=1 skip=$(($2)) iflag=skip_bytes 2>/dev/null | od -An -tx8 | tr -d " "
}
msr_clear() {
  printf '\0\0\0\0\0\0\0\0' | sudo -n dd of=/dev/cpu/$1/msr bs=8 count=1 seek=$(($2)) oflag=seek_bytes conv=notrunc 2>/dev/null || true
}

log() {
  printf '%s %s\n' "$(date -u '+%F %T')" "$*" | tee -a "$CAMPAIGN_ROOT/journal.log"
}

write_status() {
  printf '%s\n' "$1" > "$CAMPAIGN_ROOT/status.txt"
  log "STATUS $1"
}

# runtron renames its main thread (comm reads " 24/0-Main"), so pgrep/pkill -x
# never matches it. Every liveness and kill path must also match the full
# command line, or leftover engines survive into the next draw.
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

cleanup_draw() {
  stop_turbostat
  stop_dmarstat
  kill_engine || log "WARN runtron survived kill escalation"
  sudo -n find "$HP_DIR" -maxdepth 1 -type f \( -name 'libpos*' -o -name 'slice-*' \) -delete 2>/dev/null || true
  sleep 2
}

# turbostat runs as root under setsid, so both the pid kill and the pkill
# fallback must go through sudo.
stop_turbostat() {
  [ -n "$TURBOSTAT_PID" ] && sudo -n kill "$TURBOSTAT_PID" 2>/dev/null || true
  sudo -n pkill -f '[t]urbostat --quiet' 2>/dev/null || true
  TURBOSTAT_PID=
}

start_turbostat() {
  local out=$1
  stop_turbostat
  stop_dmarstat
  setsid sudo -n turbostat --quiet --show "$TURBOSTAT_SHOW" -i "$TURBOSTAT_INTERVAL" -o "$out/power.tsv" </dev/null >>"$CAMPAIGN_ROOT/daemons.log" 2>&1 9>&- &
  TURBOSTAT_PID=$!
}

# PDJN: per-draw Intel IOMMU (VT-d) PMU capture for the dmar units covering the
# four instance-0 FPGA cards (dmar9: 10/13, dmar11: 38/3b). 1 Hz interval CSV.
DMARSTAT_PID=
stop_dmarstat() {
  [ -n "$DMARSTAT_PID" ] && sudo -n kill "$DMARSTAT_PID" 2>/dev/null || true
  sudo -n pkill -f '[p]erf stat.*dmar9/iotlb_lookup' 2>/dev/null || true
  DMARSTAT_PID=
}

start_dmarstat() {
  local out=$1
  stop_dmarstat
  setsid sudo -n perf stat -I 1000 -x, -o "$out/dmar.csv" \
    -e dmar9/iotlb_lookup/ -e dmar9/iotlb_hit/ \
    -e dmar9/fs_nonleaf_lookup/ -e dmar9/fs_nonleaf_hit/ \
    -e dmar9/iommu_requests/ -e dmar9/iommu_mem_blocked/ \
    -e dmar11/iotlb_lookup/ -e dmar11/iotlb_hit/ \
    -e dmar11/fs_nonleaf_lookup/ -e dmar11/fs_nonleaf_hit/ \
    -e dmar11/iommu_requests/ -e dmar11/iommu_mem_blocked/ \
    -a sleep 1200 </dev/null >/dev/null 2>>"$CAMPAIGN_ROOT/daemons.log" &
  DMARSTAT_PID=$!
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

check_sockets() {
  [ -S /tmp/perfetto-producer ] && [ -S /tmp/perfetto-consumer ]
}

stop_daemons() {
  [ "$DAEMONS_STARTED" -eq 1 ] || return 0
  [ -n "$TRACED_PID" ] && sudo -n kill "$TRACED_PID" 2>/dev/null || true
  [ -n "$PROBES_PID" ] && sudo -n kill "$PROBES_PID" 2>/dev/null || true
  sleep 1
  sudo -n pkill -f '[t]racebox.*traced' 2>/dev/null || true
  sudo -n pkill -f '[p]erfetto --txt -c' 2>/dev/null || true
  sudo -n rm -f /run/perfetto/traced-producer.sock /run/perfetto/traced-consumer.sock 2>/dev/null || true
  sudo -n rm -f /tmp/perfetto-producer /tmp/perfetto-consumer 2>/dev/null || true
  DAEMONS_STARTED=0
  log "Perfetto daemons stopped"
}

start_daemons() {
  [ -x "$TB" ] || return 1
  if pgrep -f '[t]racebox' >/dev/null 2>&1 || [ -e /tmp/perfetto-producer ] || [ -e /tmp/perfetto-consumer ]; then
    log "REFUSED pre-existing tracebox process/socket"
    return 1
  fi
  DAEMONS_STARTED=1
  setsid sudo -n env PERFETTO_PRODUCER_SOCK_NAME=/tmp/perfetto-producer PERFETTO_CONSUMER_SOCK_NAME=/tmp/perfetto-consumer "$TB" traced </dev/null >>"$CAMPAIGN_ROOT/daemons.log" 2>&1 9>&- &
  TRACED_PID=$!
  sleep 2
  setsid sudo -n env PERFETTO_PRODUCER_SOCK_NAME=/tmp/perfetto-producer PERFETTO_CONSUMER_SOCK_NAME=/tmp/perfetto-consumer "$TB" traced_probes </dev/null >>"$CAMPAIGN_ROOT/daemons.log" 2>&1 9>&- &
  PROBES_PID=$!
  sleep 2
  sudo -n mkdir -p /run/perfetto
  sudo -n ln -sf /tmp/perfetto-producer /run/perfetto/traced-producer.sock
  sudo -n ln -sf /tmp/perfetto-consumer /run/perfetto/traced-consumer.sock
  local i
  for i in $(seq 1 15); do
    if check_sockets; then
      sudo -n chmod 0777 /tmp/perfetto-producer /tmp/perfetto-consumer
      log "Perfetto daemons ready"
      return 0
    fi
    sleep 2
  done
  return 1
}

restore_body() {
  $ISST --cpu "$FAST112" core-power assoc --clos 0 >/dev/null 2>&1 || true
  $ISST --cpu "$REST112" core-power assoc --clos 3 >/dev/null 2>&1 || true
  
sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null || true
  sleep 5
  sudo -n find /dev/hugepages -type f -delete 2>/dev/null || true
  curl -s -m 30 -X PATCH -H 'Content-Type: application/json' -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.1-8b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' http://localhost:8080/api/config >/dev/null
  sleep 3
  curl -s -m 30 -X PATCH -H 'Content-Type: application/json' -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.2-3b-instruct-fast"},{"shape":"llama-3.1-8b-instruct-good"},{"shape":"llama-3.3-70b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' http://localhost:8080/api/config >/dev/null
  sleep 20
  [ "$(pgrep -x rinzler | wc -l)" -eq 0 ] && sudo -n systemctl start rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null || true
  local models=0 i
  for i in $(seq 1 25); do
    models=$(curl -s -m 3 http://localhost/v1/models 2>/dev/null | grep -o '"id"' | wc -l)
    if [ "$models" -ge 3 ]; then
      RESTORED=1
      touch "$CAMPAIGN_ROOT/RESTORED"
      date +%s > "$CAMPAIGN_ROOT/restored-epoch.txt"
      log "RESTORE verified: trio serving"
      return 0
    fi
    sleep 12
  done
  log "RESTORE FAILED: only $models models visible"
  return 1
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
    stop_daemons
    restore_all
    if [ "$RESTORED" -eq 1 ] && [ -f "$CAMPAIGN_ROOT/identity.env" ] && [ -f "$CAMPAIGN_ROOT/results.csv" ]; then
      log "lowfreq: 5cat final report skipped (scheduler-only trace; analysis on alpha)"
      touch "$CAMPAIGN_ROOT/FINAL_REPORT_DONE"
    fi
  fi
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

gen_mean() {
  python3 - "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(d["metrics"]["generate"]["mean"])
PY
}

write_config() {
  local producer=$1 out=$2
  sed "s|__PRODUCER__|$producer|g" "$CAMPAIGN_ROOT/perfetto.cfg.tpl" > "$out"
}

capture_identity() {
  local pid=$1 out=$2
  tr '\0' ' ' < "/proc/$pid/cmdline" > "$out/runtron-command.txt"
  printf '\n' >> "$out/runtron-command.txt"
  {
    tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(USE_HW_ATTN|TRON_USE_SPECULATION|TRON_LOG_PLACEMENT|TRON_MAX_LOGITS_CHUNK_SIZE|TRON_KVWAIT_FILE|TRON_FPGA_USE_POLL_MS|TRON_FPGA_USE_FENCE|LD_LIBRARY_PATH)=' || true
    if tr '\0' '\n' < "/proc/$pid/environ" | grep -q '^SYSTEM_CONFIG='; then
      tr '\0' '\n' < "/proc/$pid/environ" | grep '^SYSTEM_CONFIG='
    else
      printf 'SYSTEM_CONFIG=<unset>\n'
    fi
  } > "$out/runtron-environment.txt"
  date -u '+%FT%TZ' > "$out/capture-timestamp.txt"
}

capture_trace() {
  local name=$1 pid=$2 out=$3 producer cfg stage
  kill -USR1 "$pid"
  sleep 1
  producer=$(cat "$CAMPAIGN_ROOT/producer-name.txt" 2>/dev/null || true)
  if [ -z "$producer" ]; then
    timeout 20 sudo -n env PERFETTO_PRODUCER_SOCK_NAME=/tmp/perfetto-producer PERFETTO_CONSUMER_SOCK_NAME=/tmp/perfetto-consumer "$TB" perfetto --query > "$out/service-state.txt" 2>&1 || true
    producer=$(grep -aoE 'name: "[^"]*"' "$out/service-state.txt" | sed 's/^name: "//;s/"$//' | grep -i tron | head -1 || true)
    [ -n "$producer" ] || producer=runtron
    printf '%s\n' "$producer" > "$CAMPAIGN_ROOT/producer-name.txt"
  fi
  cfg="$out/perfetto.cfg"
  write_config "$producer" "$cfg"
  stage="/var/tmp/jhan/perfetto-5cat-${name}-$$.pftrace"
  sudo -n rm -f "$stage" 2>/dev/null || true
  timeout -k 20 150 sudo -n env PERFETTO_PRODUCER_SOCK_NAME=/tmp/perfetto-producer PERFETTO_CONSUMER_SOCK_NAME=/tmp/perfetto-consumer "$TB" perfetto --txt -c "$cfg" -o "$stage" > "$out/perfetto.log" 2>&1
  local rc=$?
  sudo -n chown jhan:jhan "$stage" 2>/dev/null || true
  [ -f "$stage" ] && mv "$stage" "$out/trace.pftrace"
  printf '%s\n' "$rc" > "$out/perfetto.rc"
  return "$rc"
}

validate_trace() {
  local out=$1 hard_categories=$2 trace=$out/trace.pftrace rc=0 category
  local required_runtime_categories="scheduler"
  : > "$out/soft-observations.txt"
  if [ ! -s "$trace" ]; then
    printf 'trace_missing_or_empty\n' > "$out/trace-hard-failure.txt"
    return 1
  fi
  "$TP" query -f "$CAMPAIGN_ROOT/trace-validation.sql" "$trace" > "$out/trace-validation.csv" 2> "$out/trace-processor.log" || rc=$?
  printf '%s\n' "$rc" > "$out/trace-processor.rc"
  [ "$rc" -eq 0 ] || { printf 'trace_processor_open_failed\n' > "$out/trace-hard-failure.txt"; return 1; }

  for category in $CATEGORIES; do
    if ! grep -Eq "^\"?${category}\"?,[1-9][0-9]*" "$out/trace-validation.csv"; then
      printf 'missing_category=%s\n' "$category" >> "$out/category-observations.txt"
      # Scheduler/model carry the phase and MoE analysis. Other enabled
      # categories may legitimately emit no event for a specific workload.
      if [ "$hard_categories" -ne 0 ] && [[ " $required_runtime_categories " == *" $category "* ]]; then
        rc=1
      fi
    fi
  done
  grep -Eq '^"soft_moe",0$' "$out/trace-validation.csv" && printf 'exact_moe_interval_not_found\n' >> "$out/soft-observations.txt" || true
  grep -Eq '^"soft_routing",0$' "$out/trace-validation.csv" && printf 'exact_routing_interval_not_found\n' >> "$out/soft-observations.txt" || true
  grep -Eq '^"soft_parse",0$' "$out/trace-validation.csv" && printf 'parse_phase_not_distinguishable\n' >> "$out/soft-observations.txt" || true
  grep -Eq '^"soft_generation",0$' "$out/trace-validation.csv" && printf 'generation_phase_not_distinguishable\n' >> "$out/soft-observations.txt" || true
  grep -Eq '^"soft_invalid_duration",0$' "$out/trace-validation.csv" || printf 'invalid_or_incomplete_durations_present\n' >> "$out/soft-observations.txt"
  return "$rc"
}

append_result() {
  local name=$1 status=$2 gen=$3 out=$4 logf=$5 reason=$6
  reason=${reason//,/;}
  printf '%s,%s,%s,%s,%s,%s,%s\n' "$name" "$status" "$gen" "$out/runtron.log" "$logf" "$out/trace.pftrace" "$reason" >> "$CAMPAIGN_ROOT/results.csv"
}

run_draw() {
  local name=$1 out=$2 hard_categories=$3 mark wrap logdir logf pid cfg devs ndev i metrics gen placement_count
  mkdir -p "$out"
  log "$name begin"

  # PDJN chunk-size A/B: odd-numbered draws run with TRON_MAX_LOGITS_CHUNK_SIZE=1.
  local chunk_arm=""
  local arm_label="control"
  if [[ "$name" =~ ^draw_([0-9]+)$ ]] && [ $(( 10#${BASH_REMATCH[1]} % 2 )) -eq 99 ]; then
    chunk_arm=1
    arm_label="chunk1"
  fi
  echo "$arm_label" > "$out/arm.txt"
  log "$name arm=$arm_label"

  # Per-draw preflight: stop leftovers, drop stale hugepage files, confirm
  # tracing sockets are live and that there is still room for another trace.
  cleanup_draw
  if ! check_sockets; then
    log "$name WARN perfetto sockets missing, restarting daemons"
    stop_daemons
    start_daemons || { append_result "$name" failed '' "$out" '' 'perfetto sockets unavailable'; return 1; }
  fi
  if ! check_storage; then
    append_result "$name" failed '' "$out" '' 'insufficient storage'
    return 1
  fi

  mark="/var/tmp/jhan/perfetto-5cat-${name}-$$.mark"
  touch "$mark"
  (
    cd "$CKB" || exit 1
    env -u SYSTEM_CONFIG USE_HW_ATTN=0 ${chunk_arm:+TRON_MAX_LOGITS_CHUNK_SIZE=$chunk_arm} TRON_LOG_PLACEMENT=1 TRON_KVWAIT_FILE="$out/kvwait.bin" TRON_FPGA_USE_POLL_MS=${FPGA_USE_POLL_MS:-1000} TRON_FPGA_USE_FENCE=${FPGA_USE_FENCE:-0} EXTRA_RUNTRON_ARGS="-s 2954953865 --dont-stop --threshold_p 0 --pay-for-determinism --tracer-core $TRACER_CORE --output-token-file $out/tokens.out" RUNTRON_BIN="$BIN" LD_LIBRARY_PATH="$LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" timeout 1200 ./run-benchmark.sh \
      -m "$MODEL" -u 1 -i 1 --slice-of 2 --slice-start 0 \
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
    append_result "$name" failed '' "$out" '' 'no log directory'
    return 1
  fi
  logf=$(ls "$logdir"/log.* | head -1)
  printf '%s\n' "$logf" > "$out/placement-log-source.txt"
  if ! wait_marker "$logf" 'Configured instance' 90; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'no configured marker'
    return 1
  fi
  cfg=$(grep -a 'Configured instance' "$logf" | head -1)
  if ! printf '%s\n' "$cfg" | grep -q 'Configured instance 0,2 '; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'wrong instance'
    return 1
  fi
  if ! wait_marker "$logf" 'Bitfile Release Code' 120; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'no bitfile lines'
    return 1
  fi
  sleep 2
  devs=$(grep -a 'Bitfile Release Code' "$logf" | awk '{for(i=2;i<=NF;i++) if($i=="Bitfile") print tolower($(i-1))}' | sed 's/:$//' | LC_ALL=C sort -u)
  ndev=$(printf '%s\n' "$devs" | grep -c .)
  if [ "$ndev" -ne 4 ] || [ "$devs" != "$EXPECTED_DEVS" ]; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'wrong device set'
    return 1
  fi
  # PDJN bitfile consistency check (owner request 2026-08-10): the nightly can
  # install a new FPGA bitfile; record per draw and fail hard on mid-campaign change.
  bitrel=$(grep -a -m1 'Bitfile Release Code' "$logf" | grep -oE 'Release Code [0-9.]+ Release Date [0-9-]+')
  printf '%s
' "$bitrel" > "$out/bitfile.txt"
  if [ -z "${CAMPAIGN_BITREL:-}" ]; then
    CAMPAIGN_BITREL="$bitrel"
    log "$name bitfile: $bitrel"
  elif [ "$bitrel" != "$CAMPAIGN_BITREL" ]; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'bitfile changed mid-campaign'
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
    append_result "$name" failed '' "$out" "$logf" 'no runtron pid'
    return 1
  fi
  capture_identity "$pid" "$out"
  if ! wait_marker "$logf" 'Allocating and loading the model took' 300; then
    kill_engine
    append_result "$name" failed '' "$out" "$logf" 'model load timeout'
    return 1
  fi
  # Power/frequency capture spans the post-load benchmark window only, so the
  # samples reflect inference and not model load.
  start_turbostat "$out"
  start_dmarstat "$out"
  # lowered_freq: clear sticky throttle-log bits + RAPL energy snapshot (pre)
  for c in 24 25 48 151; do
    msr_clear $c 0x19C
    msr_clear $c 0x64F
  done
  msr_clear 0 0x1B1
  { printf 'range %s\n' "$(sudo -n cat /sys/class/powercap/intel-rapl:0/max_energy_range_uj 2>/dev/null)";
    printf 'pre %s %s\n' "$(date +%s.%N)" "$(sudo -n cat /sys/class/powercap/intel-rapl:0/energy_uj 2>/dev/null)"; } > "$out/rapl.txt"
  capture_trace "$name" "$pid" "$out" || log "$name WARN Perfetto client returned nonzero"

  for i in $(seq 1 1260); do
    kill -0 "$wrap" 2>/dev/null || break
    sleep 1
  done
  wait "$wrap" || true
  stop_turbostat
  stop_dmarstat
  # lowered_freq: read sticky throttle-log bits + RAPL energy snapshot (post)
  { for c in 24 25 48 151; do
      printf 'cpu%s 19C %s 64F %s\n' "$c" "$(msr_read $c 0x19C)" "$(msr_read $c 0x64F)"
    done
    printf 'pkg 1B1 %s\n' "$(msr_read 0 0x1B1)"; } > "$out/throttle.txt"
  printf 'post %s %s\n' "$(date +%s.%N)" "$(sudo -n cat /sys/class/powercap/intel-rapl:0/energy_uj 2>/dev/null)" >> "$out/rapl.txt"
  [ -s "$out/power.tsv" ] || log "$name WARN power.tsv missing or empty"
  kill_engine || true
  cp "$logf" "$out/runtron.log"
  placement_count=$(grep -ac 'Tensor device counts:' "$out/runtron.log" || true)
  printf '%s\n' "$placement_count" > "$out/placement-count.txt"
  metrics="$logdir/metrics.json"
  if [ ! -f "$metrics" ]; then
    append_result "$name" failed '' "$out" "$logf" 'no metrics'
    return 1
  fi
  cp "$metrics" "$out/metrics.json"
  gen=$(gen_mean "$out/metrics.json" 2>/dev/null || true)
  if [ -z "$gen" ]; then
    append_result "$name" failed '' "$out" "$logf" 'unreadable generation metric'
    return 1
  fi
  if validate_trace "$out" "$hard_categories"; then
    append_result "$name" ok "$gen" "$out" "$logf" ''
    log "$name OK generate=$gen tok/s"
    return 0
  fi
  append_result "$name" failed "$gen" "$out" "$logf" 'hard trace validation failed'
  log "$name FAIL hard trace validation"
  return 1
}

# Extract the timing profile of the fastest and slowest successful draws so the
# report can weigh their trace-level deltas against the throughput delta.
analyze_fast_slow() {
  local pair fast slow which draw trace kind
  pair=$(python3 - "$CAMPAIGN_ROOT/results.csv" <<'PY'
import csv, sys
rows = []
with open(sys.argv[1], newline="") as fh:
    for r in csv.DictReader(fh):
        if r.get("status") != "ok":
            continue
        try:
            rows.append((r["draw"], float(r["generate_tok_s"])))
        except (ValueError, TypeError, KeyError):
            pass
if rows:
    print(max(rows, key=lambda x: x[1])[0], min(rows, key=lambda x: x[1])[0])
PY
)
  fast=$(printf '%s' "$pair" | awk '{print $1}')
  slow=$(printf '%s' "$pair" | awk '{print $2}')
  if [ -z "$fast" ] || [ -z "$slow" ]; then
    log "ANALYSIS skipped: no successful draws"
    return 0
  fi
  printf 'fast=%s\nslow=%s\n' "$fast" "$slow" > "$CAMPAIGN_ROOT/analysis/selection.env"
  for which in fast slow; do
    [ "$which" = fast ] && draw=$fast || draw=$slow
    trace="$CAMPAIGN_ROOT/results/$draw/trace.pftrace"
    if [ ! -s "$trace" ]; then
      log "ANALYSIS $which draw $draw has no trace"
      continue
    fi
    for kind in phase category topslices; do
      "$TP" query -f "$CAMPAIGN_ROOT/analysis-${kind}.sql" "$trace" \
        > "$CAMPAIGN_ROOT/analysis/${which}-${kind}.csv" \
        2> "$CAMPAIGN_ROOT/analysis/${which}-${kind}.log" || log "ANALYSIS $which $kind query failed"
    done
  done
  log "ANALYSIS complete: fast=$fast slow=$slow"
}

write_status preparing

if systemctl is-active --quiet "$RUNNER_SERVICE" || pgrep -f '[R]unner.Worker' >/dev/null 2>&1; then
  log "PREFLIGHT FAIL: CI runner is active"
  exit 1
fi
if pgrep -x runtron >/dev/null 2>&1 || pgrep -f "^$BIN " >/dev/null 2>&1 || pgrep -f '[r]un-benchmark\.sh' >/dev/null 2>&1; then
  log "PREFLIGHT FAIL: existing runtron/run-benchmark process"
  exit 1
fi

# Per-draw Perfetto configs come from the shared template: fill in the binary
# path and add the discovered-producer placeholder that write_config()
# substitutes at capture time. The config-parse preflight below validates the
# result before anything mutates the machine.
[ -f "$PERFETTO_TPL_SRC" ] || { log "PREFLIGHT FAIL: missing $PERFETTO_TPL_SRC"; exit 1; }
sed -e "s|<full path to runtron>|$BIN|" \
    -e '/producer_name: "runtron"/i\producers { producer_name: "__PRODUCER__" shm_size_kb: 32768 }' \
    "$PERFETTO_TPL_SRC" > "$CAMPAIGN_ROOT/perfetto.cfg.tpl"

cat > "$CAMPAIGN_ROOT/trace-validation.sql" <<'SQL'
SELECT category, COUNT(*) AS samples
FROM slice
WHERE category IN ('scheduler','model','matmul','driver','gen')
GROUP BY category
UNION ALL
SELECT 'soft_moe' AS category,
       COUNT(*) AS samples
FROM slice
WHERE category = 'model'
  AND (LOWER(name) LIKE '%moe%' OR LOWER(name) LIKE '%mixture%')
UNION ALL
SELECT 'soft_routing' AS category,
       COUNT(*) AS samples
FROM slice
WHERE category = 'model' AND LOWER(name) LIKE '%rout%'
UNION ALL
SELECT 'soft_parse' AS category,
       COUNT(*) AS samples
FROM slice
WHERE name = 'forward'
  AND CAST(EXTRACT_ARG(arg_set_id, 'debug.n_token_jobs') AS INT) > 8
UNION ALL
SELECT 'soft_generation' AS category,
       COUNT(*) AS samples
FROM slice
WHERE name = 'forward'
  AND CAST(EXTRACT_ARG(arg_set_id, 'debug.n_token_jobs') AS INT) BETWEEN 1 AND 8
UNION ALL
SELECT 'soft_invalid_duration' AS category,
       COUNT(*) AS samples
FROM slice
WHERE dur < 0
UNION ALL
SELECT 'compute_forward_args' AS category,
       COUNT(*) AS samples
FROM slice
WHERE name = 'compute_forward_args';
SQL

cat > "$CAMPAIGN_ROOT/analysis-phase.sql" <<'SQL'
SELECT 'generation_forward' AS metric,
       COUNT(*) AS samples,
       CAST(AVG(dur) AS INT) AS mean_ns,
       CAST(SUM(dur) AS INT) AS total_ns
FROM slice
WHERE name = 'forward'
  AND CAST(EXTRACT_ARG(arg_set_id, 'debug.n_token_jobs') AS INT) BETWEEN 1 AND 8
UNION ALL
SELECT 'parse_forward', COUNT(*), CAST(AVG(dur) AS INT), CAST(SUM(dur) AS INT)
FROM slice
WHERE name = 'forward'
  AND CAST(EXTRACT_ARG(arg_set_id, 'debug.n_token_jobs') AS INT) > 8
UNION ALL
SELECT 'all_forward', COUNT(*), CAST(AVG(dur) AS INT), CAST(SUM(dur) AS INT)
FROM slice
WHERE name = 'forward';
SQL

cat > "$CAMPAIGN_ROOT/analysis-category.sql" <<'SQL'
SELECT category AS metric,
       COUNT(*) AS samples,
       CAST(AVG(dur) AS INT) AS mean_ns,
       CAST(SUM(dur) AS INT) AS total_ns
FROM slice
WHERE category IN ('scheduler','model','matmul','driver','gen')
GROUP BY category
ORDER BY category;
SQL

cat > "$CAMPAIGN_ROOT/analysis-topslices.sql" <<'SQL'
SELECT name AS metric,
       COUNT(*) AS samples,
       CAST(AVG(dur) AS INT) AS mean_ns,
       CAST(SUM(dur) AS INT) AS total_ns
FROM slice
WHERE dur >= 0
GROUP BY name
ORDER BY total_ns DESC
LIMIT 20;
SQL

actual_sha=$(sha256sum "$BIN" 2>/dev/null | awk '{print $1}')
free_kb=$(df -Pk /scratch | awk 'NR==2 {print $4}')
preflight_fail=
[ -x "$BIN" ] || preflight_fail="$preflight_fail binary"
[ "$actual_sha" = "$EXPECTED_BIN_SHA" ] || preflight_fail="$preflight_fail binary-hash"
[ -x "$TB" ] || preflight_fail="$preflight_fail tracebox"
[ -x "$TP" ] || preflight_fail="$preflight_fail trace-processor"
[ -x "$CKB/run-benchmark.sh" ] || preflight_fail="$preflight_fail checkerboard"
[ -f "$REPORT_PY" ] || preflight_fail="$preflight_fail report-generator"
[ "${free_kb:-0}" -ge "$MIN_FREE_KB" ] || preflight_fail="$preflight_fail storage"
sudo -n true 2>/dev/null || preflight_fail="$preflight_fail sudo"
timeout 30 sudo -n turbostat --quiet --show "$TURBOSTAT_SHOW" -i 1 -n 1 -o "$CAMPAIGN_ROOT/turbostat-check.tsv" >/dev/null 2>&1 || true
[ -s "$CAMPAIGN_ROOT/turbostat-check.tsv" ] || preflight_fail="$preflight_fail turbostat"
sed 's|__PRODUCER__|parse-test|g' "$CAMPAIGN_ROOT/perfetto.cfg.tpl" | timeout 30 env PERFETTO_CONSUMER_SOCK_NAME=/tmp/perfetto-5cat-parse-test "$TB" perfetto --txt -c - -o /dev/null > "$CAMPAIGN_ROOT/config-parse.log" 2>&1 || true
grep -aq 'trace config is invalid' "$CAMPAIGN_ROOT/config-parse.log" && preflight_fail="$preflight_fail config-parse"
[ -z "$preflight_fail" ] || { log "PREFLIGHT FAIL:$preflight_fail"; exit 1; }

cat > "$CAMPAIGN_ROOT/identity.env" <<EOF
MODEL=$MODEL
ROUNDS=$ROUNDS
BIN=$BIN
BIN_SHA256=$actual_sha
PERFETTO_CATEGORIES=$(grep -v '^[[:space:]]*#' "$CAMPAIGN_ROOT/perfetto.cfg.tpl" | grep -ao 'enabled_categories: "[a-z-]*"' | sed 's/.*"\(.*\)"/\1/' | paste -sd,)
PERFETTO_CFG_TEMPLATE=$PERFETTO_TPL_SRC
TRACE_DURATION_MS=$(grep -ao 'duration_ms: *[0-9]*' "$CAMPAIGN_ROOT/perfetto.cfg.tpl" | head -1 | grep -o '[0-9]*$')
TRACE_BUFFER_KB=$(grep -ao 'buffers { size_kb: *[0-9]*' "$CAMPAIGN_ROOT/perfetto.cfg.tpl" | head -1 | grep -o '[0-9]*$')
TRACE_FILL_POLICY=$(grep -ao 'fill_policy: *[A-Z_]*' "$CAMPAIGN_ROOT/perfetto.cfg.tpl" | head -1 | awk '{print $2}')
TURBOSTAT_COLUMNS=$TURBOSTAT_SHOW
TURBOSTAT_INTERVAL_S=$TURBOSTAT_INTERVAL
SEED_LITERAL=2954953865
SEED_EFFECTIVE=2954953984
THRESHOLD_P=0
PROMPT_LENGTH=1024
GEN_LENGTH=4096
SHARED_SYSTEM_PROMPT_LENGTH=256
USERS=1
INSTANCE=0,2
TRON_FPGA_USE_FENCE=${FPGA_USE_FENCE:-0}
TRON_FPGA_USE_POLL_MS=${FPGA_USE_POLL_MS:-1000}
SMOKE_MIN_TPS=$SMOKE_MIN_TPS
EXPECTED_TOKENS_SHA=$EXPECTED_TOKENS_SHA
CONTROL_ROUNDS=$CONTROL_ROUNDS
TRACER_CORE=$TRACER_CORE
SPECULATION=0
EOF
printf 'draw,status,generate_tok_s,archived_placement_log,source_placement_log,perfetto_capture,reason\n' > "$CAMPAIGN_ROOT/results.csv"
log "PREFLIGHT OK: runner idle, binary hash, tools, config, storage, sudo, turbostat"

if [ "${PREFLIGHT_ONLY:-0}" = 1 ]; then
  touch "$CAMPAIGN_ROOT/PREFLIGHT_ONLY_OK"
  write_status preflight_only_ok
  exit 0
fi

date +%s > "$CAMPAIGN_ROOT/mutation-start-epoch.txt"
MUTATED=1
write_status mutating_machine

# PDJN traffic gate v3 (2026-08-10): refuse to take serving down while genuine
# remote clients are connected (nightly soak protection). Counting logic lives
# in /scratch/jhan/pdjn/gate_count.sh (non-self established conns to :80).
traffic_hits=0
for _ts in 1 2 3 4 5 6; do
  _out=$(bash /scratch/jhan/pdjn/gate_count.sh)
  _conns=$(printf '%s
' "$_out" | head -1)
  log "traffic gate sample $_ts: $_conns non-self conns$(printf '%s
' "$_out" | sed -n 2p | sed 's/^/ peers:/')"
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
start_daemons || { log "FAIL Perfetto daemons"; exit 1; }

write_status smoke
if ! run_draw smoke "$CAMPAIGN_ROOT/smoke" 1; then
  log "HARD SMOKE FAILURE"
  exit 1
fi
tail -n 1 "$CAMPAIGN_ROOT/results.csv" > "$CAMPAIGN_ROOT/smoke/result.csv"

# Smoke barrier (arm B review): a detached campaign must not proceed from a
# perturbed or mis-instrumented smoke. Every check below hard-fails the run;
# the EXIT trap then restores the machine before any campaign draw starts.
write_status smoke_barrier
smoke_tps=$(awk -F, 'END{print $3}' "$CAMPAIGN_ROOT/smoke/result.csv")
barrier_fail=""
awk -v t="${smoke_tps:-0}" -v m="$SMOKE_MIN_TPS" 'BEGIN{exit !(t+0>=m+0)}' \
  || barrier_fail="$barrier_fail tps=${smoke_tps:-?}<min=$SMOKE_MIN_TPS"
smoke_tok=""
if [ -n "$EXPECTED_TOKENS_SHA" ]; then
  smoke_tok=$(sha256sum "$CAMPAIGN_ROOT/smoke/tokens.out" 2>/dev/null | awk '{print $1}')
  [ "$smoke_tok" = "$EXPECTED_TOKENS_SHA" ] \
    || barrier_fail="$barrier_fail token-sha=${smoke_tok:-missing}"
fi
python3 - "$CAMPAIGN_ROOT/smoke/kvwait.bin" "${FPGA_USE_FENCE:-0}" \
    > "$CAMPAIGN_ROOT/smoke/kvwait-liveness.txt" 2>&1 <<'PY' \
  || barrier_fail="$barrier_fail kvwait-liveness"
import array
import sys
from collections import Counter

# stdlib only: numpy is not guaranteed on the target machine.
path, fence = sys.argv[1], sys.argv[2] == "1"
raw = array.array("Q")
try:
    with open(path, "rb") as fh:
        buf = fh.read()
except OSError as e:
    print(f"FAIL cannot read kvwait.bin: {e}")
    sys.exit(1)
raw.frombytes(buf[: len(buf) - len(buf) % 8])
if len(raw) < 4:
    print("FAIL kvwait.bin missing or empty")
    sys.exit(1)
n = int(raw[0])
present = (len(raw) - 1) // 3
if present < n:
    print(f"FAIL truncated: header count {n}, records present {present}")
    sys.exit(1)
c = Counter(raw[3 + 3 * i] for i in range(n))
f1, f3 = c.get(7601, 0), c.get(7600, 0)
ok = f1 >= 4000 and f3 >= 4000
print(f"fences: 7601(F1)={f1} 7600(F3)={f3} -> {'ok' if ok else 'FAIL'}")
if fence:
    # Each flip writes fields 0-6 in one pass: within a (dev,seg) group the
    # seven counts must match, and the group count must match its closing
    # fence count (+20 closes at F3, +40 closes at F1). Tolerance 2 covers a
    # shutdown landing between a fence stamp and its flip; real truncation
    # loses thousands of records and fails loudly.
    for dev in range(4):
        for seg, fence_tag in ((20, 7600), (40, 7601)):
            counts = [c.get(8000 + dev * 100 + seg + f, 0) for f in range(7)]
            exp = c.get(fence_tag, 0)
            good = (max(counts) - min(counts) <= 1
                    and abs(counts[0] - exp) <= 2 and counts[0] >= 4000)
            print(f"dev{dev} seg+{seg}: fields={counts} closing-fence={exp}"
                  f" -> {'ok' if good else 'FAIL'}")
            ok = ok and good
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
PY
{ printf 'smoke_tps=%s min=%s\n' "${smoke_tps:-?}" "$SMOKE_MIN_TPS"
  printf 'token_sha=%s expected=%s\n' "${smoke_tok:-unchecked}" "${EXPECTED_TOKENS_SHA:-unchecked}"
  printf 'fail=[%s]\n' "$barrier_fail"; } > "$CAMPAIGN_ROOT/smoke-barrier.txt"
if [ -n "$barrier_fail" ]; then
  log "SMOKE BARRIER FAIL:$barrier_fail (see smoke-barrier.txt, smoke/kvwait-liveness.txt)"
  touch "$CAMPAIGN_ROOT/SMOKE_BARRIER_FAIL"
  exit 1
fi
log "SMOKE BARRIER PASS tps=$smoke_tps"

printf 'draw,status,generate_tok_s,archived_placement_log,source_placement_log,perfetto_capture,reason\n' > "$CAMPAIGN_ROOT/results.csv"
touch "$CAMPAIGN_ROOT/SMOKE_OK"

write_status campaign
scheduled=0
successful=0
for n in $(seq 1 "$ROUNDS"); do
  scheduled=$((scheduled + 1))
  name=$(printf 'draw_%02d' "$n")
  run_draw "$name" "$CAMPAIGN_ROOT/results/$name" 0 && successful=$((successful + 1))
done
printf '%s\n' "$scheduled" > "$CAMPAIGN_ROOT/scheduled-count.txt"
printf '%s\n' "$successful" > "$CAMPAIGN_ROOT/successful-count.txt"
touch "$CAMPAIGN_ROOT/ALL_DRAWS_SCHEDULED"
log "CAMPAIGN finished: $successful/$scheduled successful draws"

# Matched control (arm B review): same binary, config, harness, and host
# state, with fence-flip AND poller both disabled, so the flip's MMIO cost
# can be isolated by comparison instead of against an unmatched campaign.
ctrl_scheduled=0
ctrl_successful=0
if [ "$CONTROL_ROUNDS" -gt 0 ]; then
  write_status control
  FPGA_USE_FENCE=0
  FPGA_USE_POLL_MS=0
  for n in $(seq 1 "$CONTROL_ROUNDS"); do
    ctrl_scheduled=$((ctrl_scheduled + 1))
    name=$(printf 'control_%02d' "$n")
    run_draw "$name" "$CAMPAIGN_ROOT/results/$name" 0 && ctrl_successful=$((ctrl_successful + 1))
  done
  printf '%s\n' "$ctrl_scheduled" > "$CAMPAIGN_ROOT/control-scheduled-count.txt"
  printf '%s\n' "$ctrl_successful" > "$CAMPAIGN_ROOT/control-successful-count.txt"
  log "CONTROL finished: $ctrl_successful/$ctrl_scheduled successful draws"
fi

final_rc=0
if [ "$successful" -ne "$scheduled" ] || [ "$ctrl_successful" -ne "$ctrl_scheduled" ]; then
  final_rc=1
  log "FAIL incomplete: campaign $successful/$scheduled, control $ctrl_successful/$ctrl_scheduled"
fi

write_status analyzing
log "lowfreq: fast/slow 5cat trace analysis skipped (done on alpha afterward)"

write_status reporting
python3 "$REPORT_PY" "$CAMPAIGN_ROOT" || { log "FAIL report generation"; exit 1; }
touch "$CAMPAIGN_ROOT/REPORT_DONE"
write_status awaiting_restore
exit "$final_rc"
