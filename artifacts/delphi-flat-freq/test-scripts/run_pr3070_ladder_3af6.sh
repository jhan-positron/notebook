#!/usr/bin/env bash
# A->B->C ladder on delphi-3af6 to decompose PR#3070 impact:
#   A: main runtron    + universal flat (all 288 CPUs ~4100-class)
#   B: PR3070 runtron  + universal flat            -> B-A = software effect
#   C: PR3070 runtron  + matched select shape      -> C-B = shape effect
#      (fast 7-14,24-71,79-86,96-143 +sibs; rest <=2700; validated ==
#       gen_tron_flatfreq.py output for the PR resource map)
# Each phase: gpt-oss-tp4 + 8b-good tp4/tp2, lengths 256-2048 x users 2-32.
set -u
TS=$(date -u +%Y-%m-%d)
BASE=/scratch/jhan/flat_freq_tests
MAIN_BIN=/home/jhan/workspace/run_checkerboard/tron/gen/runtron
PR_BIN=/scratch/jhan/tron-pr3070/gen/runtron
UTILS=/home/jhan/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
ISST=/home/jhan/workspace/intel-vs-amd/speed-select/workspace/intel-speed-select/intel-speed-select
LADDER_LOG="$BASE/${TS}_pr3070-ladder-3af6.log"

unset SYSTEM_CONFIG TRON_LOG_LEVEL SPDLOG_LEVEL
source "$UTILS"

log() { date -u +"%F %T $*" >> "$LADDER_LOG"; }

run_phase() {
  local name="$1" bin="$2" D="$3" probe_fast="$4" probe_low="$5"
  rm -rf "$D"; mkdir -p "$D"
  cd /home/jhan/workspace/run_checkerboard/checkerboard || { echo norepo > "$D/DONE"; return 1; }
  export RUNTRON_BIN="$bin"
  log "phase $name start bin=$bin"
  date -u +"%F %T phase $name start on $(hostname) RUNTRON_BIN=$bin" > "$D/runner_timeline.txt"
  "$bin" --version >> "$D/runner_timeline.txt" 2>&1 || true

  timeout 7200 sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,CPU%c1,CPU%c6,PkgWatt,RAMWatt -i 30 > "$D/turbostat_per_cpu.tsv" 2> "$D/turbostat.err" &
  local TURBO=$!
  (
    while true; do
      echo "# $(date -u "+%F %T")"
      for c in $probe_fast $probe_low; do
        sudo -n "$ISST" --cpu $c core-power get-assoc 2>&1 | grep -E "cpu-|clos:" | tr "\n" " "; echo
      done
      sleep 600
    done
  ) > "$D/shape_watch.log" 2>&1 &
  local WATCH=$!

  # ===== THE BENCHMARK COMMAND =====
  CHECKERBOARD_MEMLOCK_KB=197971044 ./run-multi-sweep.sh \
    --models ingested-gpt-oss-120b-tp4,llama-3.1-8b-instruct-good-tp4,llama-3.1-8b-instruct-good-tp2 \
    -p 256,512,1024,2048 \
    -g 256,512,1024,2048 \
    --shared-system-prompt-lengths 64,128,256,512 \
    -s 0 \
    -u 2,4,8,16,32 > "$D/sweep_console.log" 2>&1
  local RC=$?
  # =================================
  echo "$RC" > "$D/SWEEP_EXIT_CODE"
  date -u +"%F %T phase $name sweep exited rc=$RC" >> "$D/runner_timeline.txt"
  kill "$TURBO" "$WATCH" 2>/dev/null

  local SWEEP_REL
  SWEEP_REL=$(grep -m1 "Output directory:" "$D/sweep_console.log" | sed "s/.*Output directory: //" | tr -d "[:space:]" | sed "s|^sweeps/||")
  if [ -n "$SWEEP_REL" ]; then
    ./post-processing/export_to_spreadsheet.py "sweeps/$SWEEP_REL" > "$D/export.log" 2>&1
    cp -r "/var/tmp/jhan/checkerboard/sweeps/$SWEEP_REL" "$D/sweep-results" 2>> "$D/export.log"
  fi
  echo done > "$D/DONE"
  log "phase $name done rc=$RC"
  return $RC
}

log "ladder start"

# Phase A: main + universal flat
flat_freq_apply >> "$LADDER_LOG" 2>&1 || { log "flat apply FAILED"; echo failed > "$BASE/${TS}_ladder-FAILED"; exit 1; }
run_phase A "$MAIN_BIN" "$BASE/${TS}_ladderA-flat4100-main-3af6_baseline-matrix" 2 16

# Phase B: PR3070 + universal flat (same shape, re-assert anyway)
flat_freq_apply >> "$LADDER_LOG" 2>&1
run_phase B "$PR_BIN" "$BASE/${TS}_ladderB-flat4100-pr3070-3af6_baseline-matrix" 2 16

# Phase C: PR3070 + matched select shape
flat_freq_apply 7-14,24-71,79-86,96-143 >> "$LADDER_LOG" 2>&1 || { log "select apply FAILED"; echo failed > "$BASE/${TS}_ladder-FAILED"; exit 1; }
run_phase C "$PR_BIN" "$BASE/${TS}_ladderC-tron112-pr3070-3af6_baseline-matrix" 7 16

log "ladder complete"
echo done > "$BASE/${TS}_ladder-DONE"
