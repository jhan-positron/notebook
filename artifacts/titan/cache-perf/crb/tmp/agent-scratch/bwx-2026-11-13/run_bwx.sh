#!/usr/bin/env bash
# run_bwx.sh - Parts B and C of new-test-kernel/plan.md on CRB, one visit per call (handoff.md, B.9).
# Usage: STOP_AT=<UTC time or "none"> run_bwx.sh [--dry-run] STEP...
#   STEP: SHORT B1 B2 B3 B4 B6 B7 B10a B10b B8 B5 B9 C1 C2 C3   (run in the order given)
#   STOP_AT is required. Example: STOP_AT=2026-11-14T15:00Z (start nothing that could run past this
#   time, e.g. 30 min before a block of Jeremy), or STOP_AT=none when no block is announced.
#   --dry-run: prints every command line and the planned duration of each step. It starts no benchmark,
#   makes no result folder, and does not need STOP_AT.
# Settings that depend on earlier results have NO default. A step that needs one refuses to run without it:
#   B8:           B8_COUNTS   thread counts "a+b" (a on mesh 0, b on mesh 1), e.g. B8_COUNTS="64+36 64+40 64+44"
#   B8 B5 B9 C3:  BWX_STOP (pass|common)  BWX_START (common|offset)  BWX_MIN_MS (milliseconds)
#   C3:           C3_B7_SETTINGS   the B7 settings to repeat with counters, "stop:min_ms:start" each,
#                 e.g. C3_B7_SETTINGS="pass:500:common common:6000:offset"
#   C1 C2 C3:     BWX_PMU_TYPE (the "type" file of the core PMU, from A7-core-events.txt) and
#                 BWX_EVENTS (5 event codes: cycles,instructions,L1D refill,L2D refill,last-level read miss)
#   Optional: BWX_SHA256 (expected digest of bwx; the script stops with status 2 if bwx differs),
#             RESERVE (seconds added to the longest process of a step to give MARGIN, default 90).
# Exit status: 0 done; 1 a benchmark failed; 2 usage, missing setting or missing binary; 3 marker file
#   appeared; 4 STOP_AT reached; 5 stop file ~/cache-perf/STOP found; 6 all steps ended but a process was
#   skipped for lack of memory; 130 interrupted. In every case the csv files written so far are kept.
# Needs bwx (B3: bwx_o0, bwx_o36, bwx_o52) in the same folder as this script.
# Uses CPUs 0-119 only, writes only under $HOME/cache-perf/results/<step>-<UTC>/, no sudo.
# Status: written 2026-11-13. Syntax, dry run and stop controls tested with a dummy bwx. Never run on CRB.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
DRY=0; STEPS=()
for a in "$@"; do case $a in
  --dry-run) DRY=1 ;;
  SHORT|B1|B2|B3|B4|B6|B7|B10a|B10b|B8|B5|B9|C1|C2|C3) STEPS+=("$a") ;;
  *) echo "unknown step or option: $a" >&2; exit 2 ;;
esac; done
(( ${#STEPS[@]} )) || { echo "usage: STOP_AT=<UTC|none> $0 [--dry-run] STEP...   (see the head of this file)" >&2; exit 2; }
(( DRY )) && STOP_AT=${STOP_AT:-none}

# ---- stop controls: copied from run_partA.sh, behaviour unchanged ----
MARKER=/tmp/positron-perf.RUNNING
STOPFILE=$HOME/cache-perf/STOP     # ours: "touch ~/cache-perf/STOP" from another login stops this script
[[ -n ${STOP_AT:-} ]] || { echo "set STOP_AT to a UTC time like 2026-11-14T15:00Z, or to none" >&2; exit 2; }
if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) || { echo "bad STOP_AT" >&2; exit 2; }; fi
RESERVE=${RESERVE:-90}             # seconds: allocation, first touch, warm-up passes and output of one process (est.)
MARGIN=$RESERVE                    # seconds: set for each step to its longest process plus RESERVE
CHILD=""
stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null || true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null || true; wait "$CHILD" 2>/dev/null || true; CHILD=""; fi; }
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
trap 'echo "interrupted: stopping the benchmark" >&2; stop_child; exit 130' INT TERM HUP
# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.
# The field is read with the shell builtin, so the check itself starts no process.
# The marker and the stop file are checked in every turn. The wait is returned in WAITED.
settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 || t >= 20 )) && break; sleep 2 & wait $! || true; t=$((t+2)); done; WAITED=$t; }
# one <csv> <tag> <binary> <benchmark options...>: one process, with a header line.
one() {
  local csv=$1 tag=$2 bin=$3; shift 3
  check_marker; check_deadline
  settle                                  # checks the marker in every turn
  # evidence for the load of this launch: users logged in and the 5 busiest processes
  { echo "== $csv $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu | head -6; } >> "$OUT/launches.txt"
  check_marker; check_deadline            # again, directly before the launch
  echo "-- step ${csv%.csv} tag $tag binary $bin waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"
  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears
  setsid "$SRC/$bin" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!
  local rc=0
  while kill -0 "$CHILD" 2>/dev/null; do
    why_stop || rc=$?
    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi
    sleep 1 & wait $! || true
  done
  wait "$CHILD" || rc=$?; CHILD=""
  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi
}
# ---- end of the copied part ----

SRC=$(cd "$(dirname "$0")" && pwd)
# a threads on mesh 0 (CPUs 0..a-1), b threads on mesh 1 (CPUs 64..64+b-1): same rule as run_partA.sh
cpulist() { local a=$1 b=$2 l=""; (( a > 0 )) && l="0-$((a-1))"; (( b > 0 )) && l="${l:+$l,}64-$((64+b-1))"; echo "$l"; }

# ---- settings without a default ----
need() { local v; for v in "$@"; do [[ -n ${!v:-} ]] || { echo "step $STEP_NAME needs $v, and it is not set: stop (see the head of this file)" >&2; exit 2; }; done; }
need_q2() {   # the timing settings that the analysis of B7 chose (handoff B.9, "Settings after B7")
  need BWX_STOP BWX_START BWX_MIN_MS
  [[ $BWX_STOP == pass || $BWX_STOP == common ]] || { echo "BWX_STOP must be pass or common" >&2; exit 2; }
  [[ $BWX_START == common || $BWX_START == offset ]] || { echo "BWX_START must be common or offset" >&2; exit 2; }
  [[ $BWX_MIN_MS =~ ^[1-9][0-9]*$ ]] || { echo "BWX_MIN_MS must be a whole number of milliseconds" >&2; exit 2; }
}
need_events() {
  need BWX_PMU_TYPE BWX_EVENTS
  [[ $BWX_EVENTS =~ ^[^,]+(,[^,]+){4}$ ]] || { echo "BWX_EVENTS must hold 5 codes separated by commas" >&2; exit 2; }
  export BWX_PMU_TYPE BWX_EVENTS      # bwx --count reads them from its environment (see DEVIATIONS-scripts.md)
}
need_counts() {
  need B8_COUNTS; local c a b
  for c in $B8_COUNTS; do
    [[ $c =~ ^[0-9]+\+[0-9]+$ ]] || { echo "B8_COUNTS entry '$c' is not a+b" >&2; exit 2; }
    a=${c%+*}; b=${c#*+}
    (( a <= 64 && b <= 56 && a + b >= 1 )) || { echo "B8_COUNTS entry '$c': a must be at most 64 and b at most 56 (CPUs 0-119 only)" >&2; exit 2; }
  done
}
need_c3() {
  need C3_B7_SETTINGS; local s
  for s in $C3_B7_SETTINGS; do [[ $s =~ ^(pass|common):[1-9][0-9]*:(common|offset)$ ]] || { echo "C3_B7_SETTINGS entry '$s' is not stop:min_ms:start" >&2; exit 2; }; done
}
requirements() { case $1 in B8) need_counts; need_q2 ;; B5|B9) need_q2 ;; C1|C2) need_events ;; C3) need_q2; need_c3; need_events ;; esac; }
binaries() { case $1 in B3) echo "bwx_o0 bwx_o36 bwx_o52" ;; *) echo bwx ;; esac; }
# all requirements of all named steps are checked before the first step starts
# bwx refuses a PMU type that is not a whole number (exit 2). Refuse it here, before the first launch.
if [[ -n ${BWX_PMU_TYPE:-} && ! $BWX_PMU_TYPE =~ ^[0-9]+$ ]]; then echo "BWX_PMU_TYPE must be a whole number (the content of the type file of the core PMU)" >&2; exit 2; fi
for STEP_NAME in "${STEPS[@]}"; do
  requirements "$STEP_NAME"
  if (( ! DRY )); then for b in $(binaries "$STEP_NAME"); do [[ -x $SRC/$b ]] || { echo "missing $SRC/$b (step $STEP_NAME)" >&2; exit 2; }; done; fi
done
if (( ! DRY )) && [[ -n ${BWX_SHA256:-} ]]; then
  [[ $(sha256sum < "$SRC/bwx" | cut -d' ' -f1) == "$BWX_SHA256" ]] || { echo "bwx is not the binary with digest BWX_SHA256: stop" >&2; exit 2; }
fi
(( DRY )) || check_marker

# ---- plan and execution ----
# Every step function is called twice: first with MODE=plan (it adds up the timed intervals and finds the
# longest process, and prints the command lines in a dry run), then with MODE=exec (it runs the processes).
MODE=plan; P_N=0; P_SUM_MS=0; P_MAX_MS=0; SKIPPED=0
run() {   # run <csv> <tag> <binary> <bwx options...>
  if [[ $MODE == exec ]]; then one "$@"; return; fi
  local tag=$2 bin=$3; shift 3
  local args=("$@") i seq="" rounds=1 ms=0 c t
  for (( i = 0; i < ${#args[@]}; i++ )); do case ${args[i]} in
    --seq) seq=${args[i+1]} ;; --rounds) rounds=${args[i+1]} ;; --min-ms) ms=${args[i+1]} ;; esac; done
  c=${seq//[^,]/}; t=$(( (${#c} + 1) * rounds * ms ))        # timed intervals of the process, in ms
  P_N=$((P_N+1)); P_SUM_MS=$((P_SUM_MS+t)); (( t > P_MAX_MS )) && P_MAX_MS=$t
  if (( DRY )); then printf '%s  # tag %s, timed %d.%d s\n' "$bin $*" "$tag" $((t/1000)) $((t%1000/100)); fi
}
# mem_ok <GiB> <what>: false if less memory is available. Then the process is skipped, and the script says so.
mem_ok() {
  [[ $MODE == exec ]] || return 0
  local avail; avail=$(awk '/^MemAvailable:/{print int($2/1048576)}' /proc/meminfo)
  (( avail >= $1 )) && return 0
  echo "$2 SKIPPED: MemAvailable is $avail GiB, below $1 GiB" | tee -a "$OUT/env.txt" >&2; SKIPPED=1; return 1
}

B1SEQ=asmread,copy,asmcopy,asmread,asmcopy,copy,asmread,asmcopy,asmcopy2,asmread,asmcopy2,asmcopy,asmread
B6SEQ=asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,oldread,oldread2,asmread,oldread2,oldread,asmread
B7SEQ=oldread,read,asmread,asmread2,asmread2,asmread,read,oldread
B8SEQ=oldread,asmread,asmread2,asmread2,asmread,oldread
B5SEQ=oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2
B5REV=asmread2,asmread,read_nop32,read_nop16,read_nop8,read_nop4,read_sparse,read,oldread
B10SEQ=oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite
ALL=(--threads 120 --cpus "$(cpulist 64 56)" --bytes 256M)
ONE8=(--bytes 8M --rounds 4 --min-ms 300 --stop pass)
b2seq() { echo "${B1SEQ//,copy,/,$1,}"; }      # the B1 sequence with copy replaced by the kernel $1
# the 8 combinations of the three timing factors; the two intervals are $1 and $2 (ms)
combos() { local stop ms start; for stop in pass common; do for ms in "$1" "$2"; do for start in common offset; do echo "$stop:$ms:$start"; done; done; done; }
# b7like <csv> <sequence> <stop:ms:start> <process index> [more options]: one process of a 120-thread step
b7like() { local csv=$1 seq=$2 s=$3 i=$4; shift 4; local stop=${s%%:*} start=${s##*:} ms=${s#*:}; ms=${ms%:*}
  run "$csv" "$stop-$ms-$start-p$i" bwx "${ALL[@]}" --seq "$seq" --rounds 2 --stop "$stop" --min-ms "$ms" --start "$start" "$@"; }

# Interleaving (handoff B.9, "Order of the processes"): the outer loop is the process index, so one process
# of each setting runs, then the second process of each setting, and so on.
step_B1() { local i size cpu
  for i in 1 2 3 4; do for size in 4M 8M 16M 32M; do for cpu in 0 2 41 94; do
    run B1.csv "$size-cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --bytes $size --seq $B1SEQ --rounds 4 --min-ms 300 --stop pass
  done; done; done; }
step_B2() { local i v cpu
  for i in 1 2 3 4; do for v in asmcopy_c asmcopy_c_add asmcopy_c_reg; do for cpu in 0 2 41 94; do
    run B2.csv "$v-cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --seq "$(b2seq $v)" "${ONE8[@]}"
  done; done; done; }
step_B3() { local i o cpu
  for i in 1 2 3 4; do for o in o0 o36 o52; do for cpu in 0 2 41 94; do
    run B3.csv "$o-cpu$cpu-p$i" bwx_$o --threads 1 --cpus $cpu --seq $B1SEQ "${ONE8[@]}"
  done; done; done; }
step_B4() { local i cpu     # per CPU: 2 processes with 2 MiB pages allowed and 2 with --no-thp
  for i in 1 2; do for cpu in 2 41; do
    run B4.csv "thp-cpu$cpu-p$i"   bwx --threads 1 --cpus $cpu --bytes 8M --seq asmread --rounds 200 --min-ms 300 --stop pass
    run B4.csv "nothp-cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --bytes 8M --seq asmread --rounds 200 --min-ms 300 --stop pass --no-thp
  done; done; }
step_B6() { local i cpu
  for i in 1 2 3 4 5 6 7 8; do for cpu in 2 41 94; do
    run B6.csv "cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --seq $B6SEQ "${ONE8[@]}"
  done; done; }
step_B7() { local i s k
  for i in 1 2 3 4; do
    for s in $(combos 500 6000); do b7like B7.csv $B7SEQ "$s" $i; done
    # the reproduction condition with one kernel per process, as on 2026-11-13
    for k in oldread read asmread asmread2; do
      run B7.csv "single-$k-p$i" bwx "${ALL[@]}" --seq $k --rounds 3 --stop pass --min-ms 500 --start common
    done
  done; }
b10half() { local i s; for i in "$@"; do for s in $(combos 500 15000); do b7like B10.csv $B10SEQ "$s" $i; done; done; }
step_B10a() { b10half 1 2; }      # processes 1 and 2 of every combination
step_B10b() { b10half 3 4; }      # processes 3 and 4 of every combination
step_B8() { local i c a b
  for i in 1 2; do for c in $B8_COUNTS; do a=${c%+*}; b=${c#*+}
    run B8.csv "$c-p$i" bwx --threads $((a+b)) --cpus "$(cpulist $a $b)" --bytes 256M --seq $B8SEQ --rounds 1 --stop "$BWX_STOP" --min-ms "$BWX_MIN_MS" --start "$BWX_START"
  done; done; }
b5pair() { local csv=$1 i=$2; shift 2      # one process in the forward order, then one in the reversed order
  run "$csv" "b5-fwd-p$i" bwx "${ALL[@]}" --seq $B5SEQ --rounds 1 --stop "$BWX_STOP" --min-ms "$BWX_MIN_MS" --start "$BWX_START" "$@"
  run "$csv" "b5-rev-p$i" bwx "${ALL[@]}" --seq $B5REV --rounds 1 --stop "$BWX_STOP" --min-ms "$BWX_MIN_MS" --start "$BWX_START" "$@"; }
step_B5() { b5pair B5.csv 1; b5pair B5.csv 2; }
step_B9() { local i
  mem_ok 70 "B9 (two buffers of 256 MiB for 120 threads need 60 GiB)" || return 0
  for i in 1 2 3; do
    run B9.csv "onebuf-p$i" bwx "${ALL[@]}" --seq oldread --rounds 3 --stop "$BWX_STOP" --min-ms "$BWX_MIN_MS" --start "$BWX_START"
    run B9.csv "twobuf-p$i" bwx "${ALL[@]}" --seq oldread --rounds 3 --stop "$BWX_STOP" --min-ms "$BWX_MIN_MS" --start "$BWX_START" --two-buffers
  done; }
step_C1() { local i cpu
  for i in 1 2; do for cpu in 2 41; do
    run C1.csv "cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --bytes 8M --seq asmread --rounds 200 --min-ms 300 --stop pass --count
  done; done; }
step_C2() { local i cpu
  for i in 1 2; do for cpu in 0 2 41 94; do
    run C2.csv "cpu$cpu-p$i" bwx --threads 1 --cpus $cpu --seq $B1SEQ "${ONE8[@]}" --count
  done; done; }
step_C3() { local i s
  for i in 1 2; do
    for s in $C3_B7_SETTINGS; do b7like C3.csv $B7SEQ "$s" $i --count; done
  done
  b5pair C3.csv 1 --count; }      # "2 for each": one process in each order of the B5 sequence
# SHORT: one run of every sequence with --min-ms 100 (handoff, "Order of work", step 2). No decision uses it.
step_SHORT() { local size v o s k
  local T1=(--threads 1 --cpus 2 --min-ms 100 --stop pass)
  for size in 4M 8M 16M 32M; do run SHORT.csv "b1-$size" bwx "${T1[@]}" --bytes $size --seq $B1SEQ --rounds 1; done
  for v in asmcopy_c asmcopy_c_add asmcopy_c_reg; do run SHORT.csv "b2-$v" bwx "${T1[@]}" --bytes 8M --seq "$(b2seq $v)" --rounds 1; done
  for o in o0 o36 o52; do
    if (( DRY )) || [[ -x $SRC/bwx_$o ]]; then run SHORT.csv "b3-$o" bwx_$o "${T1[@]}" --bytes 8M --seq $B1SEQ --rounds 1
    elif [[ $MODE == exec ]]; then echo "SHORT: bwx_$o is not present, its run is left out" | tee -a "$OUT/env.txt" >&2; fi
  done
  run SHORT.csv b4-thp   bwx "${T1[@]}" --bytes 8M --seq asmread --rounds 5
  run SHORT.csv b4-nothp bwx "${T1[@]}" --bytes 8M --seq asmread --rounds 5 --no-thp
  run SHORT.csv b6 bwx "${T1[@]}" --bytes 8M --seq $B6SEQ --rounds 1
  for s in pass:100:common pass:100:offset common:100:common common:100:offset; do b7like SHORT.csv $B7SEQ "$s" b7; done
  for k in oldread read asmread asmread2; do run SHORT.csv "b7-single-$k" bwx "${ALL[@]}" --seq $k --rounds 3 --stop pass --min-ms 100 --start common; done
  run SHORT.csv b8-64+32 bwx --threads 96 --cpus "$(cpulist 64 32)" --bytes 256M --seq $B8SEQ --rounds 1 --stop common --min-ms 100 --start common
  run SHORT.csv b5-fwd bwx "${ALL[@]}" --seq $B5SEQ --rounds 1 --stop common --min-ms 100 --start common
  run SHORT.csv b5-rev bwx "${ALL[@]}" --seq $B5REV --rounds 1 --stop common --min-ms 100 --start common
  run SHORT.csv b9-onebuf bwx "${ALL[@]}" --seq oldread --rounds 3 --stop common --min-ms 100 --start common
  if mem_ok 70 "SHORT b9-twobuf"; then run SHORT.csv b9-twobuf bwx "${ALL[@]}" --seq oldread --rounds 3 --stop common --min-ms 100 --start common --two-buffers; fi
  for s in pass:100:common common:100:offset; do b7like SHORT.csv $B10SEQ "$s" b10; done
  if [[ -n ${BWX_PMU_TYPE:-} && -n ${BWX_EVENTS:-} ]]; then
    export BWX_PMU_TYPE BWX_EVENTS
    run SHORT.csv count-32K bwx --threads 1 --cpus 2 --bytes 32K --seq asmread --rounds 3 --min-ms 100 --stop pass --count   # handoff B.8: instructions per byte
    run SHORT.csv count-c1  bwx "${T1[@]}" --bytes 8M --seq asmread --rounds 5 --count
    run SHORT.csv count-c2  bwx "${T1[@]}" --bytes 8M --seq $B1SEQ --rounds 1 --count
    b7like SHORT.csv $B7SEQ common:100:common count-c3 --count
  elif [[ $MODE == exec ]]; then echo "SHORT: BWX_PMU_TYPE or BWX_EVENTS is not set, the runs with --count are left out" | tee -a "$OUT/env.txt" >&2
  else echo "# SHORT: BWX_PMU_TYPE or BWX_EVENTS is not set, the runs with --count are left out"; fi
}

for STEP_NAME in "${STEPS[@]}"; do
  MODE=plan; P_N=0; P_SUM_MS=0; P_MAX_MS=0
  (( DRY )) && echo "# ---- step $STEP_NAME ----"
  "step_$STEP_NAME"
  MARGIN=$(( (P_MAX_MS + 999) / 1000 + RESERVE ))
  printf 'step %s: %d processes, timed intervals sum %d s (%d.%d min, est.), longest process %d s, MARGIN %d s, waits between processes at most %d s more\n' \
    "$STEP_NAME" $P_N $((P_SUM_MS/1000)) $((P_SUM_MS/60000)) $((P_SUM_MS%60000/6000)) $(( (P_MAX_MS+999)/1000 )) $MARGIN $((P_N*20))
  (( DRY )) && continue
  check_marker; check_deadline
  OUT=$HOME/cache-perf/results/$STEP_NAME-$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "$OUT"
  echo "result folder: $OUT"
  {
    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who | wc -l) step=$STEP_NAME steps=${STEPS[*]}"
    echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"
    echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree|MemAvailable' /proc/meminfo | tr -s ' ' | tr '\n' ' ')"
    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
    echo "## sha256:"; (cd "$SRC" && for f in bwx bwx_o0 bwx_o36 bwx_o52 run_bwx.sh; do [[ -e $f ]] && sha256sum "$f"; done; true)
    echo "## vmstat thp:"; grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat || true
    echo "## settings: STOP_AT=$STOP_AT MARGIN=$MARGIN planned_processes=$P_N planned_timed_s=$((P_SUM_MS/1000)) B8_COUNTS=${B8_COUNTS:-} BWX_STOP=${BWX_STOP:-} BWX_START=${BWX_START:-} BWX_MIN_MS=${BWX_MIN_MS:-} C3_B7_SETTINGS=${C3_B7_SETTINGS:-} BWX_PMU_TYPE=${BWX_PMU_TYPE:-} BWX_EVENTS=${BWX_EVENTS:-}"
  } > "$OUT/env.txt"
  MODE=exec
  "step_$STEP_NAME"
  echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"
  grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt" || true
  echo "$OUT"
done
if (( SKIPPED )); then echo "a process was skipped for lack of memory: see env.txt of the step" >&2; exit 6; fi
