#!/usr/bin/env bash
# run_bwx10.sh - the steps of round 3 of the 8 MiB investigation on CRB, one visit per call.
# A copy of run_bwx9.sh. The differences: step names, the folder sched10/, the binary of a step (the
# accepted old bwx8 or the new bwx10, named by the schedule), one digest check per binary, and the name of
# the result folders. The stop controls (marker file, STOP_AT, stop file, interruption, the wait for a
# quiet system, the load record) and the host sampler are the same.
# Usage: STOP_AT=<UTC time or "none"> SESSION=<1|2> run_bwx10.sh [--dry-run] [--from IDX] STEP...
#   STEP: any name that matches ^Y[A-Z0-9]+$ and has a schedule (schedule10.py writes YA YL YP YF YC).
#   The steps run in the order given.
#   The processes of a step come from sched10/s<SESSION>/<STEP>.tsv beside this script (schedule10.py
#   writes it). The script runs them in that order, one at a time. It never repeats a process.
#   Binary of a step: the file sched10/s<SESSION>/<STEP>.bin holds one word. "bwx10" means bwx10 beside
#   this script. "bwx8" means the accepted binary of round 1, $HOME/cache-perf/bwx8-20261114/bwx8. Any
#   other content, or a missing file, stops the script with status 2. build.txt is copied into the result
#   folder from the folder of the binary that the step uses.
#   STOP_AT is required. Example: STOP_AT=2026-11-15T15:00Z (start nothing that could run past this
#   time), or STOP_AT=none when no block is announced.
#   SESSION is required. SESSION=2 also needs SESSION1_END=<UTC time>, the end of session 1, written
#   as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z (no other form is accepted). The
#   script refuses to start session 2 earlier than 3 hours after that time (status 2).
#   --dry-run: prints every command line and the counts of each step. It starts no benchmark, makes
#   no result folder, and needs neither STOP_AT nor SESSION1_END nor the binaries.
#   --from IDX: continue a stopped step at the process with this idx. Only with one STEP. The value
#   is written to env.txt. The processes go to a new result folder.
#   Counter settings: a step needs BWX_PMU_TYPE (the "type" file of the core PMU) and BWX_EVENTS
#   (NAME=CODE,...) in the environment only if one of its processes has neither --pmu-type nor --events
#   in the args column of the schedule and its plan has a trial with count open or read. The
#   schedules of schedule10.py give both options in the args column, so they need no setting.
#   Host sampler: if sched10/s<SESSION>/<STEP>.watch exists, hostwatch.py (beside this script) runs
#   beside every process of the step, pinned to CPU WATCH_CPU (default 100). It reads /proc only and
#   writes watch-<idx>.txt into the result folder (its messages go to watch-stderr.txt). It is stopped
#   when the benchmark ends or is stopped. Such a step needs python3: without it the script stops
#   with status 2 before the first process of the call. WATCH_CPU must be a CPU from 0 to 119 that
#   is not a CPU of the schedule (status 2 otherwise). Before the first process of such a step the
#   sampler runs once for 0.3 s on this script (watch-selftest.txt): if it does not end cleanly, the
#   step stops with status 2. A process whose sampler file has no "# end" line gives a warning.
#   schedule10.py writes no .watch file: no step of round 3 runs with the sampler.
#   Optional: BWX8_SHA256 (expected digest of bwx8) and BWX10_SHA256 (expected digest of bwx10). Each
#             one is checked if it is set and a step of the call uses that binary: status 2 if the
#             binary differs, before the first process of the call;
#             RESERVE (seconds added to the longest process of a step to give MARGIN, default 90),
#             WATCH_CPU (CPU of the host sampler, default 100; not a CPU of the schedule).
#   For local tests with a dummy binary only: BWX8_MARKER, BWX8_STOPFILE, BWX8_BIN (the path used for
#   the word bwx8), BWX10_BIN (the path used for the word bwx10), BWX8_RESULTS.
#   The script prints a warning for each one that is set, and env.txt records the paths in use.
# Exit status: 0 done; 1 a benchmark failed; 2 usage, missing setting, missing file, wrong digest, or
#   session 2 too early; 3 marker file appeared; 4 STOP_AT reached; 5 stop file ~/cache-perf/STOP found;
#   130 interrupted. In every case the files written so far are kept.
# Needs sched10/ and hostwatch.py in the same folder as this script, and each binary with its build.txt
# in one folder.
# Uses CPUs 0-119 only, writes only under $HOME/cache-perf/results/bwx10-<step>-s<session>-<UTC>/, no sudo.
# Status: written 2026-11-15 from run_bwx9.sh (which ran session 1 of round 2 on CRB). Syntax, dry run,
# stop controls, the choice of the binary and both digest checks tested locally with dummy binaries
# (test_schedule10.py). This script itself has not run on CRB yet.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
DRY=0; FROM=0; STEPS=()
while (( $# )); do case $1 in
  --dry-run) DRY=1 ;;
  --from) [[ ${2:-} =~ ^[0-9]+$ ]] || { echo "--from needs a process index" >&2; exit 2; }; FROM=$((10#$2)); shift ;;
  *) [[ $1 =~ ^Y[A-Z0-9]+$ ]] || { echo "unknown step or option: $1" >&2; exit 2; }; STEPS+=("$1") ;;
esac; shift; done
(( ${#STEPS[@]} )) || { echo "usage: STOP_AT=<UTC|none> SESSION=<1|2> $0 [--dry-run] [--from IDX] STEP...   (see the head of this file)" >&2; exit 2; }
for (( i = 0; i < ${#STEPS[@]}; i++ )); do for (( j = 0; j < i; j++ )); do
  [[ ${STEPS[i]} != "${STEPS[j]}" ]] || { echo "step ${STEPS[i]} is named twice: stop (the script never repeats a process)" >&2; exit 2; }
done; done
(( FROM == 0 || ${#STEPS[@]} == 1 )) || { echo "--from needs exactly one step" >&2; exit 2; }
[[ ${SESSION:-} == 1 || ${SESSION:-} == 2 ]] || { echo "set SESSION to 1 or 2" >&2; exit 2; }
(( DRY )) && STOP_AT=${STOP_AT:-none}

for v in BWX8_MARKER BWX8_STOPFILE BWX8_BIN BWX10_BIN BWX8_RESULTS; do
  [[ -z ${!v:-} ]] || echo "warning: $v is set (for local tests only): $v=${!v}" >&2
done

# ---- stop controls and host sampler: copied from run_bwx9.sh, unchanged ----
MARKER=${BWX8_MARKER:-/tmp/positron-perf.RUNNING}
STOPFILE=${BWX8_STOPFILE:-$HOME/cache-perf/STOP}     # ours: "touch ~/cache-perf/STOP" from another login stops this script
[[ -n ${STOP_AT:-} ]] || { echo "set STOP_AT to a UTC time like 2026-11-15T15:00Z, or to none" >&2; exit 2; }
if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) || { echo "bad STOP_AT" >&2; exit 2; }; fi
RESERVE=${RESERVE:-90}             # seconds: allocation, first touch, page reads and output of one process (est.)
MARGIN=$RESERVE                    # seconds: set for each step to its longest process plus RESERVE
CHILD=""; CUR_CSV=""; CUR_TAG=""  # the running benchmark, its csv file and its tag (set by one)
WATCH=""; WATCH_ON=0; CUR_CPU=""; CUR_MAXS=0   # the running host sampler; set per step and per process by the main loop
# stop_watch: ends the host sampler of the current process, if one runs. The sampler also ends by itself.
stop_watch() { if [[ -n $WATCH ]]; then kill "$WATCH" 2>/dev/null || true; wait "$WATCH" 2>/dev/null || true; WATCH=""; fi; }
stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null || true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null || true; wait "$CHILD" 2>/dev/null || true; CHILD=""; fi; stop_watch; }
# why_stop: prints the reason and returns the exit status to use, or returns 0 if nothing asks us to stop.
# It is called in every turn of the wait and every second while a benchmark runs, so STOP_AT itself is
# enforced on a running benchmark. check_deadline adds the margin before a launch.
why_stop() {
  if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; return 3; fi
  if [[ -e $STOPFILE ]]; then echo "stop file $STOPFILE present: stop" >&2; return 5; fi
  if (( STOP_EPOCH && $(date -u +%s) >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT reached: stop" >&2; return 4; fi
  return 0
}
check_marker() { local rc=0; why_stop || rc=$?; if (( rc )); then stop_child; exit $rc; fi; }
check_deadline() { if (( STOP_EPOCH && $(date -u +%s) + MARGIN >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT is less than $MARGIN s away: stop" >&2; exit 4; fi; }
trap 'echo "interrupted: stopping the benchmark" >&2; if [[ -n $CHILD ]]; then echo "-- killed tag $CUR_TAG status 130 utc $(date -u +%T)" >> "$OUT/$CUR_CSV"; fi; stop_child; exit 130' INT TERM HUP
# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.
# The field is read with the shell builtin, so the check itself starts no process.
# The marker and the stop file are checked in every turn. The wait is returned in WAITED.
settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 || t >= 20 )) && break; sleep 2 & wait $! || true; t=$((t+2)); done; WAITED=$t; }
# one <csv> <idx> <tag> <benchmark options...>: one process, with a header line.
one() {
  local csv=$1 idx=$2 tag=$3; shift 3
  CUR_CSV=$csv; CUR_TAG=$tag
  check_marker; check_deadline
  settle                                  # checks the marker in every turn
  # evidence for the load of this launch: users logged in and the 5 busiest processes
  { echo "== $csv idx $idx $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu | head -6; } >> "$OUT/launches.txt"
  check_marker; check_deadline            # again, directly before the launch
  echo "-- step ${csv%.csv} session $SESSION idx $idx tag $tag waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"
  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears
  setsid "$BIN" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!
  # The host sampler of this process: read-only on /proc, on its own CPU, never on a CPU of the schedule.
  if (( WATCH_ON )); then
    taskset -c "${WATCH_CPU:-100}" python3 "$SRC/hostwatch.py" --pid "$CHILD" --cpu "$CUR_CPU" --out "$OUT/watch-$idx.txt" --max-s "$CUR_MAXS" >> "$OUT/watch-stderr.txt" 2>&1 & WATCH=$!
  fi
  local rc=0
  while kill -0 "$CHILD" 2>/dev/null; do
    why_stop || rc=$?
    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi
    sleep 1 & wait $! || true
  done
  wait "$CHILD" || rc=$?; CHILD=""
  stop_watch
  if (( WATCH_ON )) && ! grep -q '^# end reason=' "$OUT/watch-$idx.txt" 2>/dev/null; then echo "warning: the sampler file watch-$idx.txt has no end line (see $OUT/watch-stderr.txt)" >&2; fi
  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi
}
# ---- end of the copied part ----

SRC=$(cd "$(dirname "$0")" && pwd)
BIN8=${BWX8_BIN:-$HOME/cache-perf/bwx8-20261114/bwx8}   # the accepted binary of round 1
BIN10=${BWX10_BIN:-$SRC/bwx10}
BIN=""                             # the binary of the current step (set by pick_bin)
# pick_bin: reads the word in sched10/s<SESSION>/<STEP_NAME>.bin and sets BIN_WORD and BIN.
pick_bin() {
  local f=sched10/s$SESSION/$STEP_NAME.bin
  [[ -r $f ]] || { echo "missing $SRC/$f (the binary of step $STEP_NAME): stop" >&2; exit 2; }
  BIN_WORD=$(< "$f")
  case $BIN_WORD in
    bwx8) BIN=$BIN8 ;;
    bwx10) BIN=$BIN10 ;;
    *) echo "$SRC/$f must hold the one word bwx8 or bwx10: stop" >&2; exit 2 ;;
  esac
}
RESULTS=${BWX8_RESULTS:-$HOME/cache-perf/results}
cd "$SRC"                          # the plan paths in the schedules are relative to this folder

# ---- checks before the first step starts ----
if (( SESSION == 2 && ! DRY )); then
  [[ -n ${SESSION1_END:-} ]] || { echo "session 2 needs SESSION1_END (UTC time of the end of session 1), and it is not set: stop" >&2; exit 2; }
  # A full UTC time only: "date -d" also accepts a date without a time and relative words.
  [[ $SESSION1_END =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z$ ]] || { echo "bad SESSION1_END: write it as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z" >&2; exit 2; }
  S1_EPOCH=$(date -u -d "$SESSION1_END" +%s) || { echo "bad SESSION1_END" >&2; exit 2; }
  if (( $(date -u +%s) < S1_EPOCH + 10800 )); then
    echo "session 2 may start 3 hours after SESSION1_END $SESSION1_END at the earliest: stop" >&2; exit 2
  fi
fi
if [[ -n ${BWX_PMU_TYPE:-} && ! $BWX_PMU_TYPE =~ ^[0-9]+$ ]]; then echo "BWX_PMU_TYPE must be a whole number (the content of the type file of the core PMU)" >&2; exit 2; fi
for STEP_NAME in "${STEPS[@]}"; do
  [[ -r sched10/s$SESSION/$STEP_NAME.tsv ]] || { echo "missing schedule $SRC/sched10/s$SESSION/$STEP_NAME.tsv (step $STEP_NAME): stop" >&2; exit 2; }
  # The counter settings must come from the environment only for a process that has neither
  # --pmu-type nor --events in its args and whose plan has a trial with count open or read (field 10).
  NEED=()
  while IFS=$'\t' read -r idx tag cpu bytes plan args; do
    [[ $idx == idx || $plan == - || $args == *--pmu-type* || $args == *--events* ]] && continue
    if [[ -r sched10/s$SESSION/$STEP_NAME/$plan ]]; then NEED+=("sched10/s$SESSION/$STEP_NAME/$plan"); fi
  done < "sched10/s$SESSION/$STEP_NAME.tsv"
  if (( ${#NEED[@]} )) && awk '!/^#/ && ($10 == "open" || $10 == "read") { f = 1; exit } END { exit !f }' "${NEED[@]}"; then
    for v in BWX_PMU_TYPE BWX_EVENTS; do [[ -n ${!v:-} ]] || { echo "step $STEP_NAME needs $v, and it is not set: stop (see the head of this file)" >&2; exit 2; }; done
    export BWX_PMU_TYPE BWX_EVENTS        # the binary reads them from its environment
  fi
  pick_bin
done
if (( ! DRY )); then
  for STEP_NAME in "${STEPS[@]}"; do
    pick_bin
    [[ -x $BIN ]] || { echo "missing $BIN (the binary $BIN_WORD of step $STEP_NAME)" >&2; exit 2; }
    [[ -r ${BIN%/*}/build.txt ]] || { echo "missing ${BIN%/*}/build.txt (the record of the build of $BIN_WORD)" >&2; exit 2; }
    if [[ $BIN_WORD == bwx8 ]]; then WANT=${BWX8_SHA256:-}; else WANT=${BWX10_SHA256:-}; fi
    if [[ -n $WANT ]]; then
      [[ $(sha256sum < "$BIN" | cut -d' ' -f1) == "$WANT" ]] || { echo "$BIN_WORD ($BIN, step $STEP_NAME) is not the binary with the digest given for it: stop" >&2; exit 2; }
    fi
    if [[ -e sched10/s$SESSION/$STEP_NAME.watch ]]; then
      command -v python3 > /dev/null || { echo "step $STEP_NAME runs with the host sampler, and python3 is missing: stop" >&2; exit 2; }
      [[ -r $SRC/hostwatch.py ]] || { echo "missing $SRC/hostwatch.py (the host sampler of step $STEP_NAME): stop" >&2; exit 2; }
      # taskset can leave the CPUs 0-119 of this script, so the CPU of the sampler is checked here (never CPUs 120-127).
      { [[ ${WATCH_CPU:-100} =~ ^(0|[1-9][0-9]{0,2})$ ]] && (( ${WATCH_CPU:-100} <= 119 )); } || { echo "WATCH_CPU must be a CPU from 0 to 119: stop" >&2; exit 2; }
    fi
  done
  check_marker
fi

# load_step: reads the schedule of STEP_NAME into arrays and adds up the nominal kernel work.
# Work of a plan: previous activity + prefix + predecessor + windows x window length, over all trials.
# Work of a --seq process: entries of the sequence x rounds x min-ms.
load_step() {
  local idx tag cpu bytes plan args ms a i seq rounds min c
  R_IDX=(); R_TAG=(); R_CPU=(); R_ARGS=(); R_MS=(); PLANS=()
  P_N=0; P_SUM_MS=0; P_MAX_MS=0; RUN_N=0; RUN_SUM_MS=0; CONDS_SEQ=""
  while IFS=$'\t' read -r idx tag cpu bytes plan args; do
    [[ $idx == idx ]] && continue
    # idx, rounds and min-ms go into shell arithmetic, which would run a command written inside them.
    [[ $idx =~ ^(0|[1-9][0-9]*)$ ]] || { echo "bad idx in $SRC/sched10/s$SESSION/$STEP_NAME.tsv: stop" >&2; exit 2; }
    # The cpu column is the CPU that the host sampler watches.
    [[ $cpu =~ ^(0|[1-9][0-9]*)$ ]] || { echo "bad cpu in $SRC/sched10/s$SESSION/$STEP_NAME.tsv (idx $idx): stop" >&2; exit 2; }
    if [[ $plan == - ]]; then
      read -ra a <<< "$args"; seq=""; rounds=1; min=0
      for (( i = 0; i < ${#a[@]}; i++ )); do case ${a[i]} in
        --seq) seq=${a[i+1]} ;; --rounds) rounds=${a[i+1]} ;; --min-ms) min=${a[i+1]} ;; esac; done
      [[ $rounds =~ ^(0|[1-9][0-9]*)$ && $min =~ ^(0|[1-9][0-9]*)$ ]] || { echo "bad --rounds or --min-ms in $SRC/sched10/s$SESSION/$STEP_NAME.tsv (idx $idx): stop" >&2; exit 2; }
      c=${seq//[^,]/}; ms=$(( (${#c} + 1) * rounds * min ))
      CONDS_SEQ="seq=$seq"
    else
      plan=sched10/s$SESSION/$STEP_NAME/$plan
      [[ -r $plan ]] || { echo "missing plan file $SRC/$plan: stop" >&2; exit 2; }
      ms=$(awk '!/^#/ { split($4, a, ":"); split($5, b, ":"); split($6, c, ":"); ms += a[2] + b[2] + c[2] + $8 * $9 } END { print ms + 0 }' "$plan")
      PLANS+=("$plan")
    fi
    R_IDX+=("$idx"); R_TAG+=("$tag"); R_CPU+=("$cpu"); R_ARGS+=("$args"); R_MS+=("$ms")
    P_N=$((P_N+1)); P_SUM_MS=$((P_SUM_MS+ms)); (( ms > P_MAX_MS )) && P_MAX_MS=$ms
    if (( idx >= FROM )); then RUN_N=$((RUN_N+1)); RUN_SUM_MS=$((RUN_SUM_MS+ms)); fi
  done < "sched10/s$SESSION/$STEP_NAME.tsv"
  if (( ${#PLANS[@]} )); then CONDS=$(awk '!/^#/ { print $2 }' "${PLANS[@]}" | sort -u | tr '\n' ' ')
  else CONDS=$CONDS_SEQ; fi
}

for STEP_NAME in "${STEPS[@]}"; do
  pick_bin
  load_step
  (( RUN_N )) || { echo "step $STEP_NAME session $SESSION has no process with idx $FROM or above: stop" >&2; exit 2; }
  MARGIN=$(( (P_MAX_MS + 999) / 1000 + RESERVE ))
  # Printed before execution, in a real run too (design line 356).
  (( DRY )) && echo "# ---- step $STEP_NAME session $SESSION ----"
  printf 'step %s session %d: %d processes, nominal kernel work %d.%03d s (%d.%02d min); to run from idx %d: %d processes, %d.%03d s; longest process %d s, MARGIN %d s, waits between processes at most %d s more\n' \
    "$STEP_NAME" "$SESSION" $P_N $((P_SUM_MS/1000)) $((P_SUM_MS%1000)) $((P_SUM_MS/60000)) $((P_SUM_MS%60000/600)) \
    $FROM $RUN_N $((RUN_SUM_MS/1000)) $((RUN_SUM_MS%1000)) $(( (P_MAX_MS+999)/1000 )) $MARGIN $((RUN_N*20))
  echo "step $STEP_NAME selected conditions ($(wc -w <<< "$CONDS")): $CONDS"
  echo "step $STEP_NAME binary: $BIN_WORD"
  WATCH_ON=0
  if [[ -e sched10/s$SESSION/$STEP_NAME.watch ]]; then
    WATCH_ON=1
    echo "step $STEP_NAME host sampler: hostwatch.py on CPU ${WATCH_CPU:-100} beside each process, at most the nominal time of the process + 30 s"
    for c in "${R_CPU[@]}"; do
      [[ $c != "${WATCH_CPU:-100}" ]] || { echo "WATCH_CPU ${WATCH_CPU:-100} is a CPU of the schedule of step $STEP_NAME: stop" >&2; exit 2; }
    done
  fi
  if (( DRY )); then
    for (( i = 0; i < ${#R_IDX[@]}; i++ )); do
      (( R_IDX[i] < FROM )) && continue
      printf '%s %s  # idx %d, tag %s, nominal %d.%03d s\n' "$BIN_WORD" "${R_ARGS[i]}" "${R_IDX[i]}" "${R_TAG[i]}" $((R_MS[i]/1000)) $((R_MS[i]%1000))
    done
    continue
  fi
  check_marker; check_deadline
  OUT=$RESULTS/bwx10-$STEP_NAME-s$SESSION-$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "$OUT"
  echo "result folder: $OUT"
  cp "sched10/s$SESSION/$STEP_NAME.tsv" "$OUT/schedule.tsv"
  cp "${BIN%/*}/build.txt" "$OUT/build.txt"
  {
    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who | wc -l) step=$STEP_NAME steps=${STEPS[*]}"
    echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"
    echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree|MemAvailable' /proc/meminfo | tr -s ' ' | tr '\n' ' ')"
    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
    echo "## sha256:"; sha256sum "$BIN" "$SRC/run_bwx10.sh" "$SRC/sched10/s$SESSION/$STEP_NAME.tsv" "${BIN%/*}/build.txt"
    if (( WATCH_ON )); then echo "## host sampler: WATCH_CPU=${WATCH_CPU:-100} $(python3 --version 2>&1) sha256 $(sha256sum < "$SRC/hostwatch.py" | cut -d' ' -f1)"; fi
    echo "## vmstat thp:"; grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat || true
    echo "## settings: session=$SESSION from=$FROM SESSION1_END=${SESSION1_END:-} STOP_AT=$STOP_AT MARGIN=$MARGIN planned_processes=$P_N planned_nominal_ms=$P_SUM_MS to_run_processes=$RUN_N to_run_nominal_ms=$RUN_SUM_MS BWX8_SHA256=${BWX8_SHA256:-} BWX10_SHA256=${BWX10_SHA256:-} binary=$BIN_WORD BWX_PMU_TYPE=${BWX_PMU_TYPE:-} BWX_EVENTS=${BWX_EVENTS:-} MARKER=$MARKER STOPFILE=$STOPFILE BIN=$BIN RESULTS=$RESULTS"
    echo "## selected conditions: $CONDS"
  } > "$OUT/env.txt"
  if (( WATCH_ON )); then
    # Start check of the sampler, before the first process: 0.3 s on this script, on the CPU of the sampler.
    # It finds a CPU that is not usable, a python3 that cannot run hostwatch.py, and a /proc that it cannot read.
    { taskset -c "${WATCH_CPU:-100}" python3 "$SRC/hostwatch.py" --pid $$ --cpu "${R_CPU[0]}" --out "$OUT/watch-selftest.txt" --max-s 0.3 >> "$OUT/watch-stderr.txt" 2>&1 \
      && grep -q '^# end reason=max_s .* errors=0$' "$OUT/watch-selftest.txt"; } \
      || { echo "step $STEP_NAME: the start check of the host sampler failed (see $OUT/watch-stderr.txt and watch-selftest.txt): stop" >&2; exit 2; }
  fi
  for (( i = 0; i < ${#R_IDX[@]}; i++ )); do
    (( R_IDX[i] < FROM )) && continue
    read -ra ARGV <<< "${R_ARGS[i]}"
    CUR_CPU=${R_CPU[i]}; CUR_MAXS=$(( (R_MS[i] + 999) / 1000 + 30 ))
    one "$STEP_NAME.csv" "${R_IDX[i]}" "${R_TAG[i]}" "${ARGV[@]}"
  done
  echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"
  grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt" || true
  echo "$OUT"
done
