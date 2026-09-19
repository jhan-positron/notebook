#!/usr/bin/env bash
# sst-ab-20260917: does the Intel Speed Select core-frequency policy on delphi-3bda still raise
# tron's decode throughput on the current engine and the current resource map?
#
# Words used here: tron = the inference program; runtron = its command-line tool; TPS = generated
# tokens per second per user in decode (runtron's "average tok/s", one per user); TTFT = time to
# first token = runtron's "Parsing the prompt took" (max over the users); CLOS = a speed-select
# frequency class (CLOS0: 2.7 to 4.4 GHz allowed; CLOS3: capped at 2.7 GHz); the shipped policy =
# /etc/default/intel-speed-select-state (FAST_CORE_RANGES) applied at boot by
# intel-speed-select-state.service; our half = socket 1 (cpus 72-143 and their HT siblings
# 216-287) with FPGA cards 90:00.0 93:00.0 b9:00.0 bc:00.0; Bill's half = socket 0 and cards
# 10 13 38 3b, never touched here.
#
# Arms (every arm changes ONLY the CLOS association of socket-1 cpus; socket 0 is left alone):
#   boot      = the machine's boot default on socket 1 (16 fixed PCT cpus fast, all else capped)
#               = what delphi-3bda would run without our tune-up
#   tuned     = the shipped policy as it is today (the 56 tron app cores of socket 1 fast,
#               platform/front-end/dev cores 72-78 and unassigned cores 87-95 capped)
#   tunedplus = tuned + the socket-1 platform, front-end and dev cores 72-78 fast
#               (the July 2026 "front-end un-clamp" ship candidate, extended to the dev cores)
# Cells: 4 tp2 models at the nightly's user count (8), prompt 1024 tokens, GEN_LEN generated tokens,
# production attention path (USE_HW_ATTN unset), on our half (--instance 2,4, cards 90 and 93).
# Order: per repetition, per cell, the three arms back to back (arm order follows a Williams square over 6 reps).
# After EVERY run attempt socket 1 is parked in the shipped (tuned) association, so a long wait
# (lease, serving, deadline) never leaves it capped or widened.
#
# Guards (same rules as the AMX campaigns in ~/workspace/intel-AMX/exec): CI lease, blackout,
# other people, campaign flock, pre-CI hold, deadline; a 10-s watcher kills our runtron when the
# lease turns busy, when a production unit comes up on our half, or when the CLOS state drifts
# (two consecutive mismatching probes). Production serving on OUR half only is stopped when idle
# (half-takeover, see takeover_ours); units on Bill's half are never touched. At the end the shipped
# association is restored on socket 1 (set_arm tuned) and the whole-machine CLOS map is compared
# with the start snapshot; only on a mismatch is the machine-wide service restarted.
# Never edit this file while a campaign runs it.
set -u
PROJ=/home/jhan/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$PROJ/exec/sst-ab-20260917
NAME=${NAME:-sst-ab-20260917}
RES=$PROJ/results/$NAME
LOG=$PROJ/logs/$NAME.log
MARKER=$PROJ/logs/$NAME.done
STATUS=$PROJ/logs/$NAME.status
INST_LOCK=/var/tmp/jhan/$NAME.instance.lock   # one campaign.sh instance per NAME; also read by the sst-watch process
ISST=/opt/intel-speed-select/intel-speed-select
RT=${RT:-/var/tmp/jhan/tron-sst0917/gen/runtron.sst0917}
RT_FALLBACK=/var/tmp/jhan/tron-pre3879/gen/runtron.pre3879
ALLOW_FALLBACK=${ALLOW_FALLBACK:-1}   # 1: if the sst0917 build fails, measure with runtron.pre3879 (stock main of 2026-09-15) and say so loudly
BIN_NOTE="deployed-deb-commit"
OUR_RT_RE="^${RT//./[.]} "   # argv[0] of the one binary this campaign runs; re-derived once the fallback decision is made
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
REPS=${REPS:-6}                       # 6 = each arm takes each of the 3 positions twice
ARMS=${ARMS:-"boot tuned tunedplus"}
GEN_LEN=${GEN_LEN:-1024}
DO_SMOKE=${DO_SMOKE:-1}
DEADLINE_HHMM=${DEADLINE_HHMM:-130}      # UTC HHMM; the 02:45 UTC prep step brings serving up
HPFILE=/dev/hugepages/sst-ab-20260917
BILL_UID=1062305141
OUR_CARDS_RE='(90|93|b9|bc):00\.0'
# cells: key|model slug|users  (users = the nightly perf user count, systems_test scripts/perf.py)
CELLS_ALL="l8b|llama-3.1-8b-instruct-good-tp2|8
q3-4b|ingested-qwen-3-4b-instruct-2507-tp2|8
mixtral|mixtral-8x7b-instruct-v0.1-tp2|8
q25-32b|qwen-2.5-32b-it-fast-tp2|8"
CELLS=${CELLS:-"l8b q3-4b mixtral q25-32b"}
# socket-1 CLOS segments per arm (HT siblings always in the same class as their physical core)
BOOT_CLOS0="72-73 90-91 108-109 126-127 216-217 234-235 252-253 270-271"
BOOT_CLOS3="74-89 92-107 110-125 128-143 218-233 236-251 254-269 272-287"
TUNED_CLOS0="79-86 96-143 223-230 240-287"
TUNED_CLOS3="72-78 87-95 216-222 231-239"
TUNEDPLUS_CLOS0="72-86 96-143 216-230 240-287"
TUNEDPLUS_CLOS3="87-95 231-239"
S1_ALL="72-143,216-287"
APP_CORES_TP2="223-224,96-101,120-125,225-226,102-107,126-131"
mkdir -p "$RES/rt" "$RES/smoke" "$RES/power" "$PROJ/logs"
source "$EXEC/lib-guard.sh"
export GUARD_TAKEOVER_LAST
ts() { date -u +%FT%TZ; }
status() { echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
case $DEADLINE_HHMM in ''|*[!0-9]*) status "rejected: DEADLINE_HHMM='$DEADLINE_HHMM' is not HHMM digits"; exit 1 ;; esac
DEADLINE_HHMM=$((10#$DEADLINE_HHMM))
[ "$DEADLINE_HHMM" -le 2359 ] && [ $((DEADLINE_HHMM % 100)) -le 59 ] || { status "rejected: DEADLINE_HHMM=$DEADLINE_HHMM is not a clock time"; exit 1; }
DEADLINE_EPOCH=$(date -u -d "today $(printf '%02d:%02d' $((DEADLINE_HHMM / 100)) $((DEADLINE_HHMM % 100)))" +%s)
[ "$DEADLINE_EPOCH" -gt "$(date -u +%s)" ] || DEADLINE_EPOCH=$((DEADLINE_EPOCH + 86400))

placement() { echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores $APP_CORES_TP2 --dev-cores 75,76 --numa 1 --nr_hugepages 128"; }
cell_field() { local line; line=$(grep -m1 "^$1|" <<<"$CELLS_ALL") || return 1; cut -d'|' -f"$2" <<<"$line"; }
arm_segments() {  # $1 arm $2 clos -> segment list
  case "$1:$2" in
    boot:0) echo "$BOOT_CLOS0" ;; boot:3) echo "$BOOT_CLOS3" ;;
    tuned:0) echo "$TUNED_CLOS0" ;; tuned:3) echo "$TUNED_CLOS3" ;;
    tunedplus:0) echo "$TUNEDPLUS_CLOS0" ;; tunedplus:3) echo "$TUNEDPLUS_CLOS3" ;;
    *) return 1 ;;
  esac
}
arm_probe_expect() {  # expected classes of probe cpus 96 (tron app core), 73 (front-end core), 126 (app core that is also a boot PCT core)
  case $1 in boot) echo "3 0 0" ;; tuned) echo "0 3 0" ;; tunedplus) echo "0 0 0" ;; esac
}
seg_count() { local n=0 s; for s in $1; do if [[ $s == *-* ]]; then n=$((n + ${s#*-} - ${s%-*} + 1)); else n=$((n + 1)); fi; done; echo $n; }
isst() { sudo -n "$ISST" "$@" 2>&1; }
assoc_map() {  # $1 cpu list -> "cpu clos" lines
  isst --cpu "$1" core-power get-assoc | awk '/cpu-[0-9]+/{c=$1; sub("cpu-","",c)} /clos:[0-9]+/{split($1,a,":"); print c, a[2]}'
}
assoc_counts() { assoc_map "$1" | awk '{n[$2]++} END {for (k in n) print k, n[k]}' | sort -n | awk '{printf "clos%s=%d ", $1, $2} END {print ""}' | sed 's/ $//'; }
probe_of_map() { awk '$1==96{a=$2} $1==73{b=$2} $1==126{c=$2} END {print a, b, c}' <<<"$1"; }
probe_now() { probe_of_map "$(assoc_map "96,73,126")"; }
set_arm() {  # associate socket-1 cpus for arm $1; nonzero if any assoc failed or the readback mismatches
  local arm=$1 clos seg out want rc=0 have m c0 c3 w0 w3 pe
  for clos in 3 0; do
    for seg in $(arm_segments "$arm" "$clos"); do
      want=$(seg_count "$seg")
      out=$(isst --cpu "$seg" core-power assoc --clos "$clos")
      have=$(grep -c 'assoc:success' <<<"$out")
      [ "$have" -eq "$want" ] || { echo "$(ts) SET-ARM FAIL arm=$arm clos=$clos seg=$seg success=$have want=$want"; echo "$out" | head -5; rc=1; }
    done
  done
  m=$(assoc_map "$S1_ALL")
  c0=$(awk '$2==0' <<<"$m" | wc -l); c3=$(awk '$2==3' <<<"$m" | wc -l)
  w0=$(seg_count "$(arm_segments "$arm" 0)"); w3=$(seg_count "$(arm_segments "$arm" 3)")
  [ "$c0" -eq "$w0" ] && [ "$c3" -eq "$w3" ] || { echo "$(ts) SET-ARM READBACK MISMATCH arm=$arm clos0=$c0 (want $w0) clos3=$c3 (want $w3)"; rc=1; }
  pe=$(probe_of_map "$m")
  [ "$pe" = "$(arm_probe_expect "$arm")" ] || { echo "$(ts) SET-ARM PROBE MISMATCH arm=$arm probe [$pe] expected [$(arm_probe_expect "$arm")]"; rc=1; }
  echo "$(ts) arm $arm applied on socket 1: clos0=$c0 clos3=$c3 probe cpu96/73/126=[$pe] cpu87=$(awk '$1==87{print $2}' <<<"$m")"
  return $rc
}
PARKED=1   # 1 = socket 1 verified in the shipped association by the last park (or the start snapshot); the wait loops re-park while 0
park() {
  if set_arm tuned >/dev/null 2>&1 || { echo "$(ts) PARK WARN: socket 1 not back to the shipped association; retrying with details"; set_arm tuned; }; then PARKED=1
  else PARKED=0; echo "$(ts) PARK FAILED: socket 1 left in a non-shipped association; the wait loops retry"; fi
}

# ---- production serving on OUR half (half-takeover) ----
unit_pid() { systemctl show -p MainPID --value "rinzler@$1" 2>/dev/null; }
unit_devices() { local p; p=$(unit_pid "$1"); [ -n "$p" ] && [ "$p" != 0 ] && tr '\0' ' ' <"/proc/$p/cmdline" 2>/dev/null | grep -oE -- '--devices [0-9a-f:.,]+' | cut -d' ' -f2; }
ours_units() {  # active rinzler@N units whose cards are on our half, decided from the live process command line
  local i d p aff
  for i in 0 1 2 3; do
    systemctl is-active --quiet "rinzler@$i" || continue
    d=$(unit_devices "$i")
    if grep -qE "$OUR_CARDS_RE" <<<"$d"; then echo "$i"; continue; fi
    if [ -z "$d" ]; then  # no command line yet (starting?): fall back to the affinity of the main pid
      p=$(unit_pid "$i"); aff=$(taskset -pc "$p" 2>/dev/null | sed 's/.*: //')
      grep -qE '(^|,)(7[2-9]|[89][0-9]|1[0-3][0-9]|14[0-3]|21[6-9]|2[2-7][0-9]|28[0-7])(-|,|$)' <<<"$aff" && echo "$i"
    fi
  done
}
rinzler_ours_active() { [ -n "$(ours_units)" ]; }
GUARD_TAKEOVER_LAST=${GUARD_TAKEOVER_LAST:-0}
takeover_ours() {  # stop idle production units on our half only; 0 = our half is free afterwards
  # Idle = for each our-half unit: active >= 10 min, and in its journal for the last 10 min no line other than
  # the periodic #EVT# stats trio (an idle unit logs only those; requests log KV-cache, HBM and shard lines)
  # and no SYSTEM_STATS line with Open, Closed or Busy above 0. Remote serving connections are counted for
  # the record only: clients reach units through the proxy ports 3000-3020, so a connection cannot be
  # attributed to a unit; the unit's own journal is the signal.
  local now epoch units u j rc probe traffic busy note sso conns f t s
  now=$(ts); epoch=$(date +%s)
  units=$(ours_units); [ -n "$units" ] || return 0
  if ci_lease_busy 600; then echo "$now TAKEOVER: CI lease busy or expired less than 600 s ago, serving left running"; return 1; fi
  if blackout_active; then echo "$now TAKEOVER: blackout window, serving left running"; return 1; fi
  if rinzler_takeover_hold; then echo "$now TAKEOVER: inside the 01:40-04:30 UTC hold, serving left running"; return 1; fi
  if [ $((epoch - GUARD_TAKEOVER_LAST)) -lt 21600 ]; then echo "$now TAKEOVER: this process stopped serving $(( (epoch - GUARD_TAKEOVER_LAST) / 60 )) min ago and a unit is active again on our half, so someone started it: serving left running"; return 1; fi
  for u in $units; do
    t=$(systemctl show -p ActiveEnterTimestamp --value "rinzler@$u" 2>/dev/null) || t=""; s=""; [ -n "$t" ] && { s=$(date -d "$t" +%s 2>/dev/null) || s=""; }
    if [ -z "$s" ] || [ $((epoch - s)) -lt 600 ]; then echo "$now TAKEOVER: rinzler@$u active for less than 10 min (or start time unreadable), serving left running"; return 1; fi
    j=$(sudo -n journalctl -q -u "rinzler@$u" --since '-10 min' --no-pager 2>/dev/null); rc=$?
    [ "$rc" -eq 0 ] || { echo "$now TAKEOVER: journalctl failed (rc=$rc), serving left running"; return 1; }
    probe=$(sudo -n journalctl -u "rinzler@$u" -n 5 -o cat --no-pager 2>/dev/null) || true   # last 5 lines hold the last stats trio (SYSTEM_STATS, Harvester, history)
    [ -n "$probe" ] || { echo "$now TAKEOVER: journal of rinzler@$u not readable, serving left running"; return 1; }
    if [ -n "$j" ]; then
      traffic=$(printf '%s\n' "$j" | grep -vc '#EVT#') || true   # every non-#EVT# line of a unit older than 10 min is request-driven
      busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
      note="window=10min"
    elif printf '%s\n' "$probe" | grep -q 'SYSTEM_STATS.*Open=0, Closed=0, Busy=0'; then
      traffic=0; busy=0; note="window=empty,last-line=idle-stats"
    else
      echo "$now TAKEOVER: rinzler@$u journal empty for 10 min and its last stats trio is not idle, serving left running"; return 1
    fi
    echo "$now TAKEOVER: rinzler@$u (cards $(unit_devices "$u" | tr '\n' ' ')) journal-non-EVT-lines=${traffic:-?} non-idle-stats-lines=${busy:-?} $note"
    { [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ]; } || { echo "$now TAKEOVER: rinzler@$u not idle, serving left running"; return 1; }
  done
  sso=$(ss -Htn state established '( sport >= :3000 and sport <= :3020 ) or ( sport >= :13000 and sport <= :13020 )' 2>/dev/null) || sso=''
  conns=$(printf '%s\n' "$sso" | awk 'NF && $4 !~ /^127\.0\.0\.1:/' | wc -l)
  echo "$now TAKEOVER: stopping our-half unit(s) rinzler@{$(tr '\n' ',' <<<"$units" | sed 's/,$//')} (lease free, idle for 10 min); remote serving connections machine-wide=$conns (not attributable to a unit, informational); Bill's-half units untouched"
  for u in $units; do sudo -n systemctl stop "rinzler@$u" || { echo "$now TAKEOVER: systemctl stop rinzler@$u returned nonzero"; return 1; }; done
  GUARD_TAKEOVER_LAST=$epoch
  sleep 5
  rinzler_ours_active && { echo "$now TAKEOVER: a unit is active again on our half after the stop"; return 1; }
  for f in /dev/hugepages/slice-4-of-8 /dev/hugepages/slice-5-of-8 /dev/hugepages/slice-6-of-8 /dev/hugepages/slice-7-of-8; do
    [ -e "$f" ] || continue
    if fuser -s "$f" 2>/dev/null || ! flock -n "$f" true 2>/dev/null; then echo "$now TAKEOVER: $f still mapped or locked by a mapper (tron holds LOCK_EX on every mapped slice file; flock -n sees it across users, fuser does not), kept"; continue; fi
    if [ "$(stat -c %U "$f" 2>/dev/null)" = positron ] || [ -O "$f" ]; then rm -f "$f" && echo "$now TAKEOVER: removed $f (our half, unmapped)"; else echo "$now TAKEOVER: $f belongs to $(stat -c %U "$f" 2>/dev/null || echo '?'), kept"; fi
  done
  ! rinzler_ours_active
}

preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
past_deadline() { [ "$(date -u +%s)" -ge "$DEADLINE_EPOCH" ]; }
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy && { echo "CI lease busy"; return 0; }
  rinzler_ours_active && { echo "rinzler unit active on our half"; return 0; }
  return 1
}
wait_clear() {
  local why waited=0
  while why=$(blocked); do
    past_deadline && return 2
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    [ "$why" = "rinzler unit active on our half" ] && takeover_ours && continue
    [ "$PARKED" = 1 ] || park
    sleep 120
  done
  return 0
}
take_guard() {  # --allow-serving: Bill's-half production unit may stay up; our half is checked by blocked()
  local waited=0
  until campaign_guard_acquire --allow-serving; do
    past_deadline && return 2
    [ $waited = 0 ] && { status "waiting: campaign guard refused (see the GUARD line in the log)"; waited=1; pgrep -a -x 'runtron(\.[a-z0-9]+)?' 2>/dev/null | cut -c1-160 | sed 's/^/  runtron seen: /'; }
    [ "$PARKED" = 1 ] || park
    sleep 60; wait_clear || return 2
  done
  return 0
}
kill_ours() { local pids; pids=$(pgrep -u jhan -f "$OUR_RT_RE" | tr '\n' ' '); [ -n "$pids" ] && { echo "$(ts) kill_ours: TERM runtron pids $pids"; pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; }; return 0; }
# ---- power / frequency capture (turbostat, 5-s samples, whole machine; parsed per socket and per cpu) ----
TS_PAT='(^|/)turbostat --quiet --show Package[, ]Core'   # matches the turbostat binary only (argv[0] is a path; sudo's argv does not start with it)
power_start() {  # $1 dir, $2 max number of 5-s samples (bounds the capture if main and the watcher both die by SIGKILL);
  # the lock fds are closed in the subshell so a root turbostat can never hold the campaign flock or the instance lock
  mkdir -p "$1"
  ( { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } &&
    exec setsid nohup sudo -n turbostat --quiet --show Package,Core,CPU,Avg_MHz,Busy%,Bzy_MHz,PkgWatt,RAMWatt -i 5 -n "$2" >"$1/power.tsv" 2>"$1/power.err" </dev/null ) &
  echo $! >"$1/.power_pid"
}
power_stop() { sudo -n pkill -f "$TS_PAT" 2>/dev/null; sleep 1; sudo -n pkill -9 -f "$TS_PAT" 2>/dev/null; return 0; }
remove_our_files() {  # tron names its slice files [<prefix>-]slice-<k>-of-8 whatever --hugepage_file says; only jhan-owned, unmapped files go
  local f
  for f in /dev/hugepages/*; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && flock -n "$f" true 2>/dev/null && rm -f "$f" && echo "$(ts) removed hugepage file $f (unmapped, ours)"; done
  return 0
}
s1_rows() { awk '($1>=72 && $1<=143) || ($1>=216 && $1<=287)' "$1"; }   # socket-1 rows of a "cpu clos" map
s1_same() { diff -q <(s1_rows "$RES/clos-before.txt") <(s1_rows "$RES/clos-after.txt") >/dev/null 2>&1; }
note_s0() { diff -q "$RES/clos-before.txt" "$RES/clos-after.txt" >/dev/null 2>&1 || echo "$(ts) RESTORE NOTE: socket 0 differs from the start snapshot ($(diff "$RES/clos-before.txt" "$RES/clos-after.txt" | grep -c '^<') cpus); not ours, left alone"; }
restore_policy() {  # restore what the campaign changed (socket-1 association) and prove it against the socket-1 rows of the start snapshot
  local try
  echo "$(ts) restoring the shipped socket-1 association (set_arm tuned; socket 0 untouched)"
  for try in 1 2; do
    set_arm tuned || true
    assoc_map "0-287" >"$RES/clos-after.txt"
    if s1_same; then echo "$(ts) RESTORE OK (try $try): socket-1 CLOS rows identical to the start snapshot ($(assoc_counts "$S1_ALL") on socket 1)"; note_s0; return 0; fi
    echo "$(ts) socket-1 rows still differ after set_arm tuned (try $try)"
  done
  echo "$(ts) falling back to the machine-wide service restart (re-applies the shipped policy on both sockets)"
  sudo -n systemctl restart intel-speed-select-state || echo "$(ts) systemctl restart intel-speed-select-state returned nonzero"
  assoc_map "0-287" >"$RES/clos-after.txt"
  if s1_same; then echo "$(ts) RESTORE OK after service restart: socket-1 CLOS rows identical to the start snapshot"; note_s0; return 0; fi
  echo "$(ts) RESTORE MISMATCH: socket-1 rows differ from the start snapshot after the service restart; $(assoc_counts 0-287); diff start vs now:"; diff "$RES/clos-before.txt" "$RES/clos-after.txt" | head -20; return 1
}
watch_run() {  # $1 stop-flag file $2 expected probe classes for the arm $3 main pid; runs as its own process "sst-watch" (see run_one)
  local sf=$1 expect=$2 main=${3:-$$} why p miss=0 rounds=0 o
  while :; do
    if ! kill -0 "$main" 2>/dev/null; then
      kill_ours; sleep 10; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; sleep 2; power_stop; remove_our_files
      echo "$(ts) WATCH: main pid $main gone, restoring the shipped policy"
      o=aborted-main-gone; restore_policy || o="$o-RESTORE-FAILED"
      if flock -n "$INST_LOCK" true 2>/dev/null; then   # no new campaign instance has started: close the bookkeeping
        python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true; echo "$o" >"$MARKER"; status "finished: $o"
      else echo "$(ts) WATCH: a new campaign instance holds $INST_LOCK; marker and status left to it"; fi
      exit 0
    fi
    why=""
    if ci_lease_busy; then why="CI lease busy"
    elif rinzler_ours_active; then why="rinzler unit active on our half"
    elif [ -e "$sf.ARMED" ]; then   # drift probes only while main says the arm is applied (not during set_arm or park)
      p=$(probe_now)
      if [ "$p" = "$expect" ]; then miss=0; else miss=$((miss + 1)); echo "$(ts) WATCH: probe cpu96/73/126 = [$p], expected [$expect] (mismatch #$miss; stop at 2)"; [ $miss -ge 2 ] && why="CLOS drift: probe cpu96/73/126 = [$p], expected [$expect], twice"; fi
    fi
    if [ -n "$why" ]; then
      [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"
      rounds=$((rounds + 1)); kill_ours
      [ $rounds -eq 6 ] && pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 && { echo "$(ts) WATCH: our runtron still alive 60 s after the first TERM, sending KILL"; pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null; }
    else rounds=0; fi
    sleep 10
  done
}
WPID=""
stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
machine_line() {
  local bill; bill=$(ps -u "$BILL_UID" -o pcpu= -o comm= 2>/dev/null | awk '{n++; c+=$1} END {printf "bill_procs=%d bill_cpu_pct=%.0f", n, c}')
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(awk '/^HugePages_Free/{print $2}' /proc/meminfo) $bill bill_marker=$([ -e /bill-has-instance-0,2 ] && echo present || echo absent) units_ours=[$(ours_units | tr '\n' ' ')] units_active=[$(for i in 0 1 2 3; do systemctl is-active --quiet rinzler@$i && printf '%s ' $i; done)]"
}
finish() {
  local outcome=$1
  power_stop
  if [ "${1#aborted}" != "$1" ]; then
    trap '' TERM
    if [ -n "${CAMPAIGN_LOCK_FD:-}" ]; then   # our runtron can only be alive while we hold the campaign flock; the fallback binary is shared with the wedperf-family campaigns
      kill_ours
      for _ in $(seq 1 60); do pgrep -u jhan -f "$OUR_RT_RE" >/dev/null 2>&1 || break; sleep 1; done
      pkill -KILL -u jhan -f "$OUR_RT_RE" 2>/dev/null && { echo "$(ts) finish: SIGKILL to our runtron"; sleep 2; }
    else echo "$(ts) finish: no run in progress (campaign flock not held), nothing of ours to kill"; fi
  fi
  remove_our_files
  restore_policy || outcome="$outcome-RESTORE-FAILED"
  rm -f "$RES/rt.STOPPED.ARMED"
  stop_watcher   # after the restore: sst-watch is the only restore path if main dies during the wait above
  campaign_guard_release 2>/dev/null
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
  echo "$outcome" >"$MARKER"
  status "finished: $outcome"
  echo "=== campaign finished $(ts): $outcome ==="
}

# one runtron invocation; $1 key $2 arm $3 kind (smoke|rt) $4 rep
run_one() {
  local key=$1 arm=$2 kind=$3 rep=$4 model users rlog pdir attempt stops=0 rc res args tmo hdr expect
  model=$(cell_field "$key" 2) || { echo "$(ts) unknown cell $key"; return 1; }
  users=$(cell_field "$key" 3)
  if [ "$kind" = smoke ]; then
    rlog=$RES/smoke/${key}__${arm}.log; pdir=$RES/power/smoke__${key}__${arm}
    grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) smoke $key $arm already done"; return 0; }
    args="--prompt-length 1024 -l 64 -u 1"; tmo=1500
  else
    rlog=$RES/rt/${key}__${arm}__rep${rep}.log; pdir=$RES/power/${key}__${arm}__rep${rep}
    grep -q "average tok/s" "$rlog" 2>/dev/null && { echo "$(ts) runtron $key $arm rep$rep already done"; return 0; }
    args="--prompt-length 1024 -l $GEN_LEN -u $users --dont-stop"; tmo=2400
  fi
  attempt=$(ls "$rlog".attempt* 2>/dev/null | wc -l)
  while :; do
    past_deadline && { echo "$(ts) deadline $(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) reached before $kind $key $arm rep$rep"; return 2; }
    attempt=$((attempt + 1))
    wait_clear || { echo "$(ts) deadline reached while waiting before $kind $key $arm rep$rep"; return 2; }
    take_guard || { echo "$(ts) deadline reached while waiting for the guard before $kind $key $arm rep$rep"; return 2; }
    status "$kind $key arm=$arm rep=$rep attempt=$attempt"
    expect=$(arm_probe_expect "$arm")
    rm -f "$RES/rt.STOPPED" "$RES/rt.STOPPED.ARMED"
    # the watcher runs as a separate process named sst-watch (not a fork with main's command line), so a
    # pkill by the campaign.sh pattern cannot remove main and its only restore path at the same time; it is
    # alive from before set_arm until after park, so a SIGKILL to main while socket 1 is in an arm state still
    # has a restore path; drift probes run only while rt.STOPPED.ARMED exists
    ( { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } &&
      exec env SST_SELF="$C/campaign.sh" NAME="$NAME" RT="$RT" bash -c 'SST_FUNCTIONS_ONLY=1 . "$SST_SELF"; watch_run "$@"' sst-watch "$RES/rt.STOPPED" "$expect" $$ ) & WPID=$!
    if ! set_arm "$arm"; then echo "RUN-FAILED set_arm $arm (see the SET-ARM lines in the log)" >>"$RES/rt-results.txt"; park; stop_watcher; campaign_guard_release; return 1; fi
    touch "$RES/rt.STOPPED.ARMED"
    hdr="### runtron kind=$kind cell=$key model=$model tp=2 users=$([ "$kind" = smoke ] && echo 1 || echo "$users") attn=default prompt=1024 len=$([ "$kind" = smoke ] && echo 64 || echo "$GEN_LEN") arm=$arm rep=$rep attempt=$attempt bin=$RT tip=$RT_TIP $(ts) $(machine_line)"
    echo "$hdr" >>"$RES/rt-results.txt"
    rm -rf "$pdir"; power_start "$pdir" $(( (tmo + 300) / 5 ))
    (cd "$(dirname "$(dirname "$RT")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; [ -z "${INST_LOCK_FD:-}" ] || exec {INST_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
        timeout -k 60 "$tmo" "$RT" stream-generate-text -m "$model" $(placement) --hugepage_file "$HPFILE" -o $args) >"$rlog.attempt$attempt" 2>&1
    rc=$?
    kill -0 "$WPID" 2>/dev/null || { echo "$(ts) WATCHER DIED during $kind $key $arm rep$rep (pid $WPID): this run had no lease, rinzler or drift check"; echo "RUN-UNMONITORED: watcher died during $kind $key $arm rep$rep attempt$attempt (see the log)" >>"$RES/rt-results.txt"; }
    power_stop
    echo "$(ts) post-run probe cpu96/73/126 = [$(probe_now)] expected [$expect]" >>"$rlog.attempt$attempt"
    rm -f "$RES/rt.STOPPED.ARMED"
    park
    stop_watcher
    campaign_guard_release; remove_our_files
    python3 "$C/power_summary.py" "$pdir/power.tsv" "$APP_CORES_TP2" >"$pdir/summary.txt" 2>"$pdir/summary.err" || true
    res=$(grep -E "Version:|Configured instance|App CPU list|HW attention|Parsing the prompt took|average tok/s|estimated response throughput" "$rlog.attempt$attempt" 2>/dev/null | cut -c1-240)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null) (full output: $rlog.attempt$attempt)" >>"$RES/rt-results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP after 3 stops" >>"$RES/rt-results.txt"; return 1; }
      sleep 120; continue
    fi
    if [ $rc -ne 0 ] || ! grep -q "average tok/s" <<<"$res"; then
      { echo "RUN-FAILED rc=$rc (full output: $rlog.attempt$attempt)"; echo "$res"; grep -i -m3 -E "error|abort|assert|exception|terminate|not found|unknown model" "$rlog.attempt$attempt" | cut -c1-240; } >>"$RES/rt-results.txt"
      return 1
    fi
    cp "$rlog.attempt$attempt" "$rlog"
    { echo "$res"; echo "POWER $(cat "$pdir/summary.txt" 2>/dev/null | tr '\n' ' ')"; } >>"$RES/rt-results.txt"
    return 0
  done
}
rotate_arms() {  # $1 rep -> Williams square: reps 1-3 rotate ARMS, reps 4-6 rotate the reversed list
  # (each arm in each position twice and each ordered neighbour pair twice over 6 reps, so carry-over is balanced)
  local a=($ARMS) n i k rev; n=${#a[@]}; k=$(( ($1 - 1) % n )); rev=$(( (($1 - 1) / n) % 2 ))
  for i in $(seq 0 $((n - 1))); do
    if [ $rev = 1 ]; then printf '%s ' "${a[$(( (n - 1 - i + k) % n ))]}"; else printf '%s ' "${a[$(( (i + k) % n ))]}"; fi
  done; echo
}

[ "${SST_FUNCTIONS_ONLY:-0}" = 1 ] && { return 0 2>/dev/null || exit 0; }

# ======================= main flow =======================
exec >>"$LOG" 2>&1
exec {INST_LOCK_FD}>"$INST_LOCK"
flock -n "$INST_LOCK_FD" || { echo "$(ts) another campaign.sh instance holds $INST_LOCK; this one exits"; exit 1; }
rm -f "$MARKER"
echo "=== $NAME campaign started $(ts) pid $$ REPS=$REPS ARMS=[$ARMS] CELLS=[$CELLS] GEN_LEN=$GEN_LEN DO_SMOKE=$DO_SMOKE ALLOW_FALLBACK=$ALLOW_FALLBACK deadline=$(date -u -d @"$DEADLINE_EPOCH" +%FT%TZ) ==="
sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "$(ts) could not raise memlock limit (ulimit -l = $(ulimit -l)); the reference campaign ran fine this way"

# phase 0: the CLOS start snapshot must be the shipped policy (clos0=224 clos3=64, tron cores fast, front-end cores capped)
assoc_map "0-287" >"$RES/clos-before.txt"
counts=$(assoc_counts 0-287)
echo "$(ts) CLOS at start: $counts; probe cpu96/73/126 = [$(probe_now)]"
if [ "$counts" != "clos0=224 clos3=64" ] || [ "$(probe_now)" != "0 3 0" ]; then
  echo "$(ts) unexpected CLOS state at start (want clos0=224 clos3=64 and probe [0 3 0]); campaign ends without changing anything"
  echo "unexpected-clos-state" >"$MARKER"; status "finished: unexpected-clos-state"; exit 1
fi
trap '[ -e "$MARKER" ] || finish aborted' EXIT

# phase 1: the binary. build.sh (wedperf's) waits for the CI lease and the flock itself, so the 4-h timer
# below counts only lease-free ticks (normal path: peer build ~15 min + our build ~8 min after the lease clears).
status "phase 1: waiting for the build marker"
waited=0
while :; do
  m=$(cat "$RES/build-sst0917.done" 2>/dev/null || true)
  case $m in
    ok) break ;;
    build-failed*|worktree-failed|checkout-failed|missing-models*|cache-mismatch*)
      if [ "$ALLOW_FALLBACK" = 1 ]; then echo "$(ts) BUILD MARKER '$m': FALLBACK to $RT_FALLBACK (stock main 2026-09-15, main before PR #3879); the report must say so"; RT=$RT_FALLBACK; BIN_NOTE="FALLBACK-pre3879:$m"; break
      else echo "$(ts) build marker says '$m'; campaign ends"; finish "build:$m"; exit 1; fi ;;
  esac
  past_deadline && { echo "$(ts) deadline reached while waiting for the build marker; campaign ends"; finish deadline; exit 0; }
  ci_lease_busy || waited=$((waited + 30))   # counts lease-free time only; build.sh has no timeout, so a hung build also ends here
  if [ $waited -ge 14400 ]; then
    if [ "$ALLOW_FALLBACK" = 1 ]; then echo "$(ts) NO BUILD MARKER after 4 h of lease-free time (build process present or not): FALLBACK to $RT_FALLBACK; the report must say so"; RT=$RT_FALLBACK; BIN_NOTE="FALLBACK-pre3879:no-marker"; break
    else echo "$(ts) no build marker; campaign ends"; finish "build:no-marker"; exit 1; fi
  fi
  sleep 30
done
[ -x "$RT" ] || { echo "$(ts) $RT missing"; finish "no-binary"; exit 1; }
OUR_RT_RE="^${RT//./[.]} "   # RT is final here; the kill paths must match only this campaign's binary
RT_TIP=$(git -C "$(dirname "$(dirname "$RT")")" rev-parse --short HEAD 2>/dev/null || echo "?")
{
  echo "# $NAME runtron results; host $(hostname); started $(ts); binary note: $BIN_NOTE"
  echo "# arms: boot = socket-1 boot-default CLOS (16 PCT cpus fast, rest capped 2.7 GHz); tuned = shipped policy (56 socket-1 tron app cores fast); tunedplus = tuned + socket-1 cpus 72-78/216-222 fast"
  echo "# env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN (production attention default); TRON_LOG_LEVEL=SPDLOG_LEVEL=debug; hugepage file $HPFILE; rt runs: prompt 1024, $GEN_LEN generated tokens, --dont-stop; socket 1 parked in the tuned association after every run"
  echo "# cells: key|model|users:"; sed 's/^/#   /' <<<"$CELLS_ALL"
  echo "# placement: $(placement)"
  sha256sum "$RT"; ( cd "$(dirname "$RT")" && echo "version: $("./$(basename "$RT")" --version 2>&1 | head -1)" )
} >>"$RES/rt-results.txt"
echo "$(ts) binary $RT tip=$RT_TIP note=$BIN_NOTE; $(machine_line)"

fails=0; consec=0
declare -A CELL_FAILS=()
rt() {  # $1 key $2 arm $3 kind $4 rep
  local k="$1|$2|$3" rc
  [ "${CELL_FAILS[$k]:-0}" -ge 2 ] && { echo "$(ts) skip $3 $1 $2 rep$4: failed twice before"; return 0; }
  run_one "$1" "$2" "$3" "$4"; rc=$?
  [ $rc -eq 2 ] && return 2
  if [ $rc -eq 0 ]; then consec=0; return 0; fi
  fails=$((fails + 1)); consec=$((consec + 1)); CELL_FAILS[$k]=$(( ${CELL_FAILS[$k]:-0} + 1 ))
  [ $consec -ge 5 ] && { echo "$(ts) 5 consecutive failed runs; campaign ends"; return 3; }
  return 1
}
end_check() { case $1 in 2) finish deadline; exit 0 ;; 3) finish aborted-5-consecutive-failures; exit 1 ;; esac; }

# phase 2: smokes, one short run per model; the arms rotate over the cells so every arm is applied at least
# once (a real class change from the parked tuned state) before the measured runs
if [ "$DO_SMOKE" = 1 ]; then
  sm=($ARMS); i=0; n0=$(wc -l <"$RES/rt-results.txt")
  for key in $CELLS; do rt "$key" "${sm[$((i % ${#sm[@]}))]}" smoke 1; end_check $?; i=$((i + 1)); done
  if tail -n +"$((n0 + 1))" "$RES/rt-results.txt" | grep -q '^RUN-FAILED set_arm'; then
    echo "$(ts) an arm could not be applied during the smokes (see the SET-ARM lines above); campaign ends"; finish aborted-set-arm; exit 1
  fi
  tail -n +"$((n0 + 1))" "$RES/rt-results.txt" | grep -q '^POWER .*intervals=[1-9]' || echo "$(ts) WARNING: no smoke produced a turbostat sample (see $RES/power/smoke__*/power.err); the app MHz verification would be missing"
  echo "$(ts) smokes done, failed runs so far: $fails"
fi

# phase 3: the measured runs; arms back to back inside a cell, arm order rotated per repetition
for rep in $(seq 1 "$REPS"); do
  order=$(rotate_arms "$rep")
  echo "$(ts) repetition $rep arm order: $order"
  for key in $CELLS; do for arm in $order; do rt "$key" "$arm" rt "$rep"; end_check $?; done; done
  echo "$(ts) repetition $rep done, failed runs so far: $fails"
  python3 "$C/summarize.py" "$RES" >"$RES/summary.md" 2>"$RES/summary.err" || true
done

status "phase 4: summary"
finish "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")"
