#!/usr/bin/env bash
# run_h2.sh - the test of hypothesis H2 on CRB: the ORIGINAL program at 8 MiB, many processes.
# H2 (handoff tackle-8mb-handoff.md): the original gain of 0.94 % was measured while the new read
# loop was at its low level. This script repeats the original protocol of run_kernels.sh (2026-11-13)
# for the read kernel at 8 MiB only, with the two original binaries, which it does NOT rebuild:
#   bw_old (old read) and bw_new (new read) in ~/cache-perf/scratch-kernels-20261113/
# Every process is started exactly as the original "one" function started it:
#   <binary> --threads 1 --cpus <cpu> --bytes 8M --kernel read --reps 3 --min-ms 500
# Usage: STOP_AT=<UTC time or "none"> SESSION=<1|2> run_h2.sh [--dry-run] [--from IDX]
#   Worker CPUs: 2 and 0 (as in the original) and 41. SESSION=1 uses the CPU order 2,0,41.
#   SESSION=2 uses 41,0,2. The CPUs are run one after the other.
#   Each CPU gets 12 pairs of processes. A pair is one bw_old process and one bw_new process that
#   run directly one after the other. The first binary of a pair alternates (ABBA): in session 1
#   the pairs 1,3,5,.. start with bw_old and the pairs 2,4,6,.. start with bw_new. Session 2 is the
#   reverse. So each binary is first in 6 pairs and second in 6 pairs on every CPU.
#   That is 3 CPUs x 12 pairs x 2 binaries = 72 processes per session. The order is saved in
#   order.tsv of the result folder (columns idx, cpu, pair, pos, binary) before the first process.
#   STOP_AT is required. Example: STOP_AT=2026-11-15T15:00Z (start nothing that could run past this
#   time), or STOP_AT=none when no block is announced.
#   SESSION is required. SESSION=2 also needs SESSION1_END=<UTC time>, the end of session 1 OF THIS
#   SCRIPT (line "## end utc=" in env.txt of the h2-s1 folder), written as 2026-11-15T03:00Z or
#   2026-11-15T03:00:00Z. The script refuses to start session 2 earlier than 3 hours after it (status 2).
#   --dry-run: prints every command line and the count. It starts no benchmark, makes no result
#   folder, checks no binary, and needs neither STOP_AT nor SESSION1_END.
#   --from IDX: continue a stopped session at the process with this idx (0 to 71). The value is
#   written to env.txt. The processes go to a new result folder.
#   Optional: RESERVE (seconds added to the nominal work of one process to give MARGIN, default 90).
#   For local tests with dummy binaries only: H2_DIR (folder of bw_old and bw_new), H2_SHA256_OLD,
#   H2_SHA256_NEW (expected digests), BWX8_MARKER, BWX8_STOPFILE, BWX8_RESULTS.
#   The script prints a warning for each one that is set, and env.txt records the values in use.
# Before the first process the script compares the sha256 digests of both binaries with the digests
#   of handoff.md (section "Files"). If one differs or a binary is missing, it stops with status 2.
# Exit status: 0 done; 1 a benchmark failed; 2 usage, missing setting, missing or changed binary, or
#   session 2 too early; 3 marker file appeared; 4 STOP_AT reached; 5 stop file ~/cache-perf/STOP
#   found; 130 interrupted. In every case the files written so far are kept.
# Uses CPUs 0-119 only, writes only under $HOME/cache-perf/results/h2-s<session>-<UTC>/
#   (H2.csv, env.txt, launches.txt, stderr.txt, order.tsv), no sudo.
# Status: written 2026-11-14. Dry run, stop controls and order tested with dummy binaries
#   (test_h2.py). Never run on CRB.
set -euo pipefail
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi
DRY=0; FROM=0
while (( $# )); do case $1 in
  --dry-run) DRY=1 ;;
  --from) [[ ${2:-} =~ ^[0-9]+$ ]] || { echo "--from needs a process index" >&2; exit 2; }; FROM=$((10#$2)); shift ;;
  *) echo "unknown option: $1   (usage: STOP_AT=<UTC|none> SESSION=<1|2> $0 [--dry-run] [--from IDX])" >&2; exit 2 ;;
esac; shift; done
[[ ${SESSION:-} == 1 || ${SESSION:-} == 2 ]] || { echo "set SESSION to 1 or 2" >&2; exit 2; }
(( DRY )) && STOP_AT=${STOP_AT:-none}

for v in H2_DIR H2_SHA256_OLD H2_SHA256_NEW BWX8_MARKER BWX8_STOPFILE BWX8_RESULTS; do
  [[ -z ${!v:-} ]] || echo "warning: $v is set (for local tests only): $v=${!v}" >&2
done

# ---- stop controls: copied from run_bwx8.sh. Changed only in "one": the header line has the form
# ---- of run_kernels.sh, and the binary is an argument (two binaries here, one there). ----
MARKER=${BWX8_MARKER:-/tmp/positron-perf.RUNNING}
STOPFILE=${BWX8_STOPFILE:-$HOME/cache-perf/STOP}     # ours: "touch ~/cache-perf/STOP" from another login stops this script
[[ -n ${STOP_AT:-} ]] || { echo "set STOP_AT to a UTC time like 2026-11-15T15:00Z, or to none" >&2; exit 2; }
if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) || { echo "bad STOP_AT" >&2; exit 2; }; fi
RESERVE=${RESERVE:-90}             # seconds: allocation, first touch, warm-up passes and output of one process (est.)
MARGIN=$RESERVE                    # seconds: set below to the nominal work of one process plus RESERVE
CHILD=""; CUR_CSV=""; CUR_TAG=""  # the running benchmark, its csv file and its tag (set by one)
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
trap 'echo "interrupted: stopping the benchmark" >&2; if [[ -n $CHILD ]]; then echo "-- killed tag $CUR_TAG status 130 utc $(date -u +%T)" >> "$OUT/$CUR_CSV"; fi; stop_child; exit 130' INT TERM HUP
# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.
# The field is read with the shell builtin, so the check itself starts no process.
# The marker and the stop file are checked in every turn. The wait is returned in WAITED.
settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 || t >= 20 )) && break; sleep 2 & wait $! || true; t=$((t+2)); done; WAITED=$t; }
# one <csv> <idx> <tag> <binary> <cpu> <pair> <pos>: one process, with a header line.
# The header starts like the header of run_kernels.sh ("-- binary .. kernel .. threads .. cpus ..
# bytes .. round .. load .. utc .."), with the session in the place of the round. More fields follow.
one() {
  local csv=$1 idx=$2 tag=$3 bin=$4 cpu=$5 pair=$6 pos=$7
  CUR_CSV=$csv; CUR_TAG=$tag
  check_marker; check_deadline
  settle                                  # checks the marker in every turn
  # evidence for the load of this launch: users logged in and the 5 busiest processes
  { echo "== $csv idx $idx $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu | head -6; } >> "$OUT/launches.txt"
  check_marker; check_deadline            # again, directly before the launch
  echo "-- binary $bin kernel $KERNEL threads 1 cpus $cpu bytes $BYTES round $SESSION load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T) session $SESSION idx $idx pair $pair pos $pos tag $tag waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who | wc -l)" >> "$OUT/$csv"
  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears
  setsid "$DIR/$bin" --threads 1 --cpus "$cpu" --bytes "$BYTES" --kernel "$KERNEL" --reps 3 --min-ms 500 >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!
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
DIR=${H2_DIR:-$HOME/cache-perf/scratch-kernels-20261113}
RESULTS=${BWX8_RESULTS:-$HOME/cache-perf/results}
# expected digests: handoff.md, section "Files" (its Ref4)
SHA_OLD=${H2_SHA256_OLD:-e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa}
SHA_NEW=${H2_SHA256_NEW:-fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6}
KERNEL=read; BYTES=8M              # 8 MiB, written as the original wrote it
PAIRS=12                           # pairs per CPU: 12 processes of each binary
PROC_MS=1500                       # nominal kernel work of one process: 3 repetitions x 500 ms
if (( SESSION == 1 )); then CPUS=(2 0 41); else CPUS=(41 0 2); fi

# ---- the order: CPU after CPU, 12 pairs each, first binary alternating (see the head of this file) ----
R_CPU=(); R_PAIR=(); R_POS=(); R_BIN=(); R_TAG=()
for cpu in "${CPUS[@]}"; do
  for (( p = 1; p <= PAIRS; p++ )); do
    if (( (p + SESSION) % 2 == 0 )); then two=(bw_old bw_new); else two=(bw_new bw_old); fi
    for pos in 1 2; do
      b=${two[pos-1]}
      R_CPU+=("$cpu"); R_PAIR+=("$p"); R_POS+=("$pos"); R_BIN+=("$b")
      R_TAG+=("$(printf 's%d-c%d-p%02d-%s' "$SESSION" "$cpu" "$p" "${b#bw_}")")
    done
  done
done
P_N=${#R_BIN[@]}
(( FROM < P_N )) || { echo "session $SESSION has no process with idx $FROM or above: stop" >&2; exit 2; }
RUN_N=$((P_N - FROM))
MARGIN=$(( (PROC_MS + 999) / 1000 + RESERVE ))

# ---- checks before the first process ----
if (( SESSION == 2 && ! DRY )); then
  [[ -n ${SESSION1_END:-} ]] || { echo "session 2 needs SESSION1_END (UTC time of the end of session 1), and it is not set: stop" >&2; exit 2; }
  # A full UTC time only: "date -d" also accepts a date without a time and relative words.
  [[ $SESSION1_END =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z$ ]] || { echo "bad SESSION1_END: write it as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z" >&2; exit 2; }
  S1_EPOCH=$(date -u -d "$SESSION1_END" +%s) || { echo "bad SESSION1_END" >&2; exit 2; }
  if (( $(date -u +%s) < S1_EPOCH + 10800 )); then
    echo "session 2 may start 3 hours after SESSION1_END $SESSION1_END at the earliest: stop" >&2; exit 2
  fi
fi
if (( ! DRY )); then
  for b in bw_old bw_new; do [[ -x $DIR/$b ]] || { echo "missing $DIR/$b: stop (this script does not rebuild it)" >&2; exit 2; }; done
  [[ $(sha256sum < "$DIR/bw_old" | cut -d' ' -f1) == "$SHA_OLD" ]] || { echo "$DIR/bw_old does not have the expected sha256 $SHA_OLD: stop (this script does not rebuild it)" >&2; exit 2; }
  [[ $(sha256sum < "$DIR/bw_new" | cut -d' ' -f1) == "$SHA_NEW" ]] || { echo "$DIR/bw_new does not have the expected sha256 $SHA_NEW: stop (this script does not rebuild it)" >&2; exit 2; }
  check_marker
fi

# Printed before execution, in a real run too.
printf 'H2 session %d: %d processes (CPUs %s, %d pairs of bw_old and bw_new each), nominal kernel work %d.%03d s (%d.%02d min); to run from idx %d: %d processes, %d.%03d s; one process %d.%03d s, MARGIN %d s, waits between processes at most %d s more\n' \
  "$SESSION" "$P_N" "${CPUS[*]}" "$PAIRS" $((P_N*PROC_MS/1000)) $((P_N*PROC_MS%1000)) $((P_N*PROC_MS/60000)) $((P_N*PROC_MS%60000/600)) \
  "$FROM" "$RUN_N" $((RUN_N*PROC_MS/1000)) $((RUN_N*PROC_MS%1000)) $((PROC_MS/1000)) $((PROC_MS%1000)) "$MARGIN" $((RUN_N*20))
if (( DRY )); then
  for (( i = FROM; i < P_N; i++ )); do
    echo "${R_BIN[i]} --threads 1 --cpus ${R_CPU[i]} --bytes $BYTES --kernel $KERNEL --reps 3 --min-ms 500  # idx $i, pair ${R_PAIR[i]}, pos ${R_POS[i]}, tag ${R_TAG[i]}"
  done
  echo "count: $RUN_N command lines"
  exit 0
fi

check_marker; check_deadline
OUT=$RESULTS/h2-s$SESSION-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
echo "result folder: $OUT"
{
  printf 'idx\tcpu\tpair\tpos\tbinary\n'
  for (( i = 0; i < P_N; i++ )); do printf '%d\t%s\t%s\t%s\t%s\n' "$i" "${R_CPU[i]}" "${R_PAIR[i]}" "${R_POS[i]}" "${R_BIN[i]}"; done
} > "$OUT/order.tsv"
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who | wc -l) step=H2"
  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"
  echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree|MemAvailable' /proc/meminfo | tr -s ' ' | tr '\n' ' ')"
  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
  echo "## sha256:"; sha256sum "$DIR/bw_old" "$DIR/bw_new" "$SRC/run_h2.sh"
  echo "## vmstat thp:"; grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat || true
  echo "## command line of every process: <binary> --threads 1 --cpus <cpu> --bytes $BYTES --kernel $KERNEL --reps 3 --min-ms 500"
  echo "## settings: session=$SESSION from=$FROM SESSION1_END=${SESSION1_END:-} STOP_AT=$STOP_AT MARGIN=$MARGIN cpu_order=${CPUS[*]} pairs_per_cpu=$PAIRS planned_processes=$P_N planned_nominal_ms=$((P_N*PROC_MS)) to_run_processes=$RUN_N to_run_nominal_ms=$((RUN_N*PROC_MS)) SHA_OLD=$SHA_OLD SHA_NEW=$SHA_NEW MARKER=$MARKER STOPFILE=$STOPFILE DIR=$DIR RESULTS=$RESULTS"
} > "$OUT/env.txt"
for (( i = FROM; i < P_N; i++ )); do
  one H2.csv "$i" "${R_TAG[i]}" "${R_BIN[i]}" "${R_CPU[i]}" "${R_PAIR[i]}" "${R_POS[i]}"
done
echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"
grep -E '^thp_(fault_alloc|fault_fallback|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt" || true
echo "$OUT"
