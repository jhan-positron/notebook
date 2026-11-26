#!/usr/bin/env bash
# run_all.sh [SCENARIO ...] - end-to-end test of manual-run.sh WITHOUT CRB.
#
# The real file /home/jhan/workspace/ai-proj/arm-crb/manual-run.sh runs unchanged. A fake "ssh" (bin/ssh)
# is first in PATH. It contacts no machine: it runs the command string with bash in a fake home folder.
# Stand-in drivers (standin/go.sh, standin/go2.sh) copy the result folders of the agent run of 2026-11-17.
# Each scenario gets a fresh fake home under work/<scenario>/. Output of the script: out/<scenario>.out.
# The folder that a scenario creates under tests/ of the repository is deleted after the scenario.
# Result: summary.txt (one line per scenario: PASS or FAIL against the expectation written in this file).
# Without arguments all scenarios run, one after the other (no parallel jobs). Run time: about 45 s.
# Expected result on the file with sha256 2f34a0cf... (2026-11-25): PASS 41, FAIL 2 (p2, tb), 15 observations.
set -u
H=$(builtin cd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null && pwd)
REPO=/home/jhan/workspace/ai-proj/arm-crb
SCRIPT=$REPO/manual-run.sh
SRC=$REPO/tests/2026-11-17-whole-chip-7200
STAT=$REPO/code/w120-7200-2026-11-17
ASRUN=$(dirname "$H")/crb-asrun
OUTD=$H/out; WORK=$H/work; SUMMARY=$H/summary.txt
DEST_RE='^/home/jhan/workspace/ai-proj/arm-crb/tests/[0-9]{4}-[0-9]{2}-[0-9]{2}-whole-chip-7200-manual-[0-9]{6}Z$'
# Scenario "sh" is not in the list: it runs only when named (see its comment).
ALL="a a2 b b2 b3 b4 c c2 c3 d e f g1 g2 g3 h i j k l m n o p p2 p3 p4 p5 p6 q r s t u v w x y z6 z7 z7b z13 tb"
EXPECTED_STEPS="k120-T72A1 k120-T72A2 k120-T72A3 w120-T72C1 w120-T72C2 w120-T72C3 w120-T72C4 w120-T72I1 w120-T72I2 w120-T72L1 w120-T72L2 w120-T72L3 "
GO_STEPS="k120-T72A1 k120-T72A2 k120-T72A3 w120-T72C1 w120-T72C2 w120-T72C3 w120-T72C4 w120-T72L1 w120-T72L2 w120-T72L3 "

mkdir -p "$OUTD" "$WORK"
[ "$(PATH="$H/bin:$PATH" command -v ssh)" = "$H/bin/ssh" ] || { echo "the fake ssh is not first in PATH: stop"; exit 1; }
if ls -d "$REPO"/tests/*-whole-chip-7200-manual-* > /dev/null 2>&1; then
  echo "a folder tests/*-whole-chip-7200-manual-* exists before the test: stop"; ls -d "$REPO"/tests/*-whole-chip-7200-manual-*; exit 1
fi
ls -1 "$REPO/tests" > "$H/tests-before.txt"
printf 'y\n' > "$H/in-y"; printf 'n\n' > "$H/in-n"; printf 'Y\n' > "$H/in-Y"
: > "$SUMMARY"

# ---------- helpers ----------
setup() { # NAME: fresh fake home and state
  SCN=$1; W=$WORK/$SCN; FAILS=(); NOTES=(); PATH_PREFIX=; DEST=; T=; RC=; CALLS=; CMDLINE=
  rm -rf "$W"; mkdir -p "$W/state" "$W/tmp" "$W/home/cache-perf/results" "$W/home/cache-perf/w120-7200-20261117"
  export HARNESS_STATE=$W/state HARNESS_HOME=$W/home HARNESS_RBIN=$H/rbin HARNESS_SRC=$SRC
  D=$W/home/cache-perf/w120-7200-20261117; R=$W/home/cache-perf/results; O=$OUTD/$SCN.out
  cp "$H/standin/go.sh" "$H/standin/go2.sh" "$ASRUN/w120-7200-20261117/"{ra.sh,like.spec,cfwd.spec,crev.spec} "$D/"
  chmod +x "$D/go.sh" "$D/go2.sh" "$D/ra.sh"
  (builtin cd "$D" && sha256sum go.sh ra.sh like.spec cfwd.spec crev.spec > local.sha && sha256sum go2.sh > go2.sha)
  # Older results with the same step names: the run of 2026-11-17, a run of 2026-11-23 and a run that
  # started 3 s before this scenario. Each older folder holds a file OLD-RUN.
  local d b s near; near=$(date -u -d '3 seconds ago' +%Y%m%dT%H%M%SZ)
  for d in "$SRC"/k120-T72A?-* "$SRC"/w120-T72[LCI]?-*; do
    b=$(basename "$d")
    for s in "${b##*-}" "20261123T${b: -7}" "$near"; do cp -r "$d" "$R/${b%-*}-$s"; : > "$R/${b%-*}-$s/OLD-RUN"; done
  done
  cp "$ASRUN"/results/* "$R/"
  echo "old log" > "$R/go-T72-$near.log"; echo "old log" > "$R/go2-T72-$near.log"; echo old > "$R/memcheck-$near.txt"
  printf 'MemTotal:       395392804 kB\nMemFree:        390000000 kB\n' > "$HARNESS_STATE/meminfo"
  echo "00000000-0000-0000-0000-harness00000" > "$HARNESS_STATE/boot_id"; echo 11 > "$HARNESS_STATE/pmu_type"
  : > "$HARNESS_STATE/conf"; : > "$HARNESS_STATE/started.log"; : > "$HARNESS_STATE/ssh-calls.log"; echo 0 > "$HARNESS_STATE/ssh-count"
}
conf() { printf '%s\n' "$@" >> "$HARNESS_STATE/conf"; }
parse() { # after a run: run id, results folder, number of ssh calls
  DEST=$(sed -n 's/^== run id [0-9TZ]*, results go to //p' "$O" | head -1)
  T=$(sed -n 's/^== run id \([0-9TZ]*\), results go to .*/\1/p' "$O" | head -1)
  CALLS=$(cat "$HARNESS_STATE/ssh-count")
}
run() { # STDIN_FILE ARGS...: the console command "./manual-run.sh ARGS" in the repository folder
  local in=$1; shift
  CMDLINE="cd $REPO && PATH=<harness>/bin:\$PATH ./manual-run.sh $* < ${in/#$H\//<harness>/}"
  (builtin cd "$REPO" > /dev/null && env TMPDIR="$W/tmp" PATH="${PATH_PREFIX}$H/bin:$PATH" ./manual-run.sh "$@" < "$in" > "$O" 2>&1); RC=$?
  parse
}
run_abs() { # the same with the absolute path, from the harness folder
  local in=$1; shift
  CMDLINE="cd <harness> && PATH=<harness>/bin:\$PATH $SCRIPT $* < ${in/#$H\//<harness>/}"
  (builtin cd "$H" > /dev/null && env TMPDIR="$W/tmp" PATH="${PATH_PREFIX}$H/bin:$PATH" "$SCRIPT" "$@" < "$in" > "$O" 2>&1); RC=$?
  parse
}
run_sig() { # WAIT_REGEX DELAY SIGNAL TARGET: "./manual-run.sh -y" with a signal while it runs
  CMDLINE="./manual-run.sh -y, then $3 to the $4 after the line /$1/ plus $2 s"
  SIGLINE=$(builtin cd "$REPO" > /dev/null && /usr/bin/python3 -B "$H/sig_run.py" "$O" "$1" "$2" "$3" "$4" 60 env TMPDIR="$W/tmp" PATH="$H/bin:$PATH" ./manual-run.sh -y)
  RC=$(echo "$SIGLINE" | sed -n 's/^status \([0-9]*\) .*/\1/p'); NOTES+=("sig_run: $SIGLINE")
  parse
}
obs() { NOTES+=("OBSERVATION: $1"); }   # something that looks wrong but is no part of the expectation
ck() { # DESCRIPTION COMMAND...: the description is recorded as a failed check when the command fails
  local what=$1; shift
  "$@" || FAILS+=("$what")
}
has() { grep -qE -- "$1" "$O"; }
hasnt() { ! grep -qE -- "$1" "$O"; }
rc_is() { [ "$RC" = "$1" ]; }
eq() { [ "$1" = "$2" ]; }
started() { cut -d' ' -f1 "$HARNESS_STATE/started.log" | tr '\n' ' '; }
dest_dirs() { find "$DEST" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | LC_ALL=C sort; }
dest_steps() { dest_dirs | sed 's/-[0-9TZ]*$//' | tr '\n' ' '; }
dest_files() { find "$DEST" -mindepth 1 -maxdepth 1 ! -type d -printf '%f\n' | LC_ALL=C sort | tr '\n' ' '; }
dest_old() { # prints every sign of an older run in the results folder
  find "$DEST" -name OLD-RUN; dest_dirs | while read -r d; do [[ ${d##*-} < $T ]] && echo "stamp before run id: $d"; done
}
dest_equals_source() { # every copied folder holds the same files as the folder of 2026-11-17 with that step name
  local d; for d in $(dest_dirs); do diff -rq "$DEST/$d" "$(ls -d "$SRC/${d%-*}-"*)" > /dev/null || return 1; done
}
block() { awk -v a="$1" -v b="$2" '$0 ~ b {on=0} on {print} $0 ~ a {on=1}' "$O"; }
no_start() { ck "a driver was started: $(started)" eq "$(started)" ""; }
no_dest() { ck "a results folder was created: $DEST" eq "$DEST" ""; }
finish() { # EXPECTED_STATUS
  ck "exit status $RC, expected $1" rc_is "$1"
  ck "temp file left in TMPDIR: $(ls -A "$W/tmp" | tr '\n' ' ')" eq "$(ls -A "$W/tmp")" ""
  ck "file left on the CRB side: $(ls "$D" | grep -F .tmp | tr '\n' ' ')" eq "$(ls "$D" | grep -F .tmp)" ""
  local left; left=$(pgrep -f "$D/go2?-direct.sh" | tr '\n' ' ')
  ck "a stand-in driver still runs: $left" eq "$left" ""
  [ -z "$left" ] || pkill -KILL -f "$D/go2?-direct.sh"
  if [ -n "$DEST" ] && [ -d "$DEST" ] && [ -z "$(ls -A "$DEST")" ]; then obs "an EMPTY results folder stays under tests/: $(basename "$DEST")"; fi
  if grep -q '^tar: ' "$O"; then obs "error lines of tar are printed: $(grep -c '^tar: ' "$O") lines"; fi
  local verdict=PASS f; [ ${#FAILS[@]} = 0 ] || verdict=FAIL
  {
    printf '%-3s %s  status %s (expected %s), ssh calls %s, drivers started: %s\n' "$SCN" "$verdict" "$RC" "$1" "$CALLS" "$(started)"
    echo "      command: $CMDLINE"
    for f in ${FAILS[@]+"${FAILS[@]}"}; do echo "      FAILED CHECK: $f"; done
    for f in ${NOTES[@]+"${NOTES[@]}"}; do echo "      note: $f"; done
    grep -E '^(manual-run.sh:|NOT STARTED|CHECK FAILED|RUNNING file|A driver may|Killed|tar:|ssh:|sh:|client_loop|fake|FAILED)' "$O" | cut -c1-250 | sed 's/^/      out: /'
    if [ -n "$DEST" ] && [ -d "$DEST" ]; then echo "      results folder: $(basename "$DEST"): $(ls -1 "$DEST" | wc -l) entries: $(dest_steps)| $(dest_files)"; fi
  } >> "$SUMMARY"
  # delete exactly the folder that this scenario created under tests/
  if [ -n "$DEST" ]; then
    if [[ $DEST =~ $DEST_RE ]] && [ -d "$DEST" ] && ! grep -qxF "$(basename "$DEST")" "$H/tests-before.txt"; then
      ls -la "$DEST" > "$OUTD/$SCN.results-listing.txt"; rm -rf -- "$DEST"
    elif [[ $DEST =~ $DEST_RE ]] && [ ! -e "$DEST" ]; then :   # the script created no folder
    else
      echo "      HARNESS: not deleted (unexpected name or state): $DEST" >> "$SUMMARY"
    fi
  fi
  [ "$verdict" = FAIL ] || rm -rf "$W/home/cache-perf/results"   # keep the fake results only for a failed scenario
  echo "$SCN $verdict (status $RC)"
}
complete_run_checks() { # the checks of a complete run: 12 folders, 3 files, 3 tables
  ck "ssh calls $CALLS, expected 5" eq "$CALLS" 5
  ck "an ssh call without -n, BatchMode or the host" eq "$(grep -c '^call .* -n -o BatchMode=yes .* jhan@192.168.2.45$' "$HARNESS_STATE/ssh-calls.log")" 5
  ck "drivers started: $(started)" eq "$(started)" "go go2 "
  ck "folders in the results folder: $(dest_steps)" eq "$(dest_steps)" "$EXPECTED_STEPS"
  ck "files in the results folder: $(dest_files)" eq "$(dest_files)" "go-T72-$T.log go2-T72-$T.log memcheck-$T.txt "
  ck "older run in the results folder: $(dest_old | tr '\n' ' ')" eq "$(dest_old)" ""
  ck "a copied folder differs from its source" dest_equals_source
  ck "memcheck record has no line '12 Configured Memory Speed: 7200 MT/s'" grep -qE '^ +12 .Configured Memory Speed: 7200 MT/s$' "$DEST/memcheck-$T.txt"
  ck "go log does not end with ALLDONE" eq "$(tail -n 1 "$DEST/go-T72-$T.log")" ALLDONE
  ck "go2 log does not end with ALLDONE" eq "$(tail -n 1 "$DEST/go2-T72-$T.log")" ALLDONE
  local g
  for g in go go2; do
    ck "$g-direct.sh is not executable" test -x "$D/$g-direct.sh"
    ck "$g-direct.sh still holds the boot id line" eq "$(grep -c 'boot id is not the boot checked' "$D/$g-direct.sh")" 0
    ck "$g-direct.sh is not $g.sh minus one line" eq "$(diff "$D/$g.sh" "$D/$g-direct.sh" | grep -c '^[<>]')" 1
    ck "$g.sh was changed on the CRB side" eq "$(builtin cd "$D" && sha256sum -c local.sha go2.sha 2>&1 | grep -c ': OK$')" 6
  done
  # the three tables hold the numbers that the statistics scripts give for the folders of 2026-11-17
  local a lc i
  a=$(builtin cd "$SRC" && python3 -B "$STAT/stat_k120.py" --pool k120-T72A?-* | sed -n '/^== pool of/,$p' | grep -E '^[a-z]+ +bw_')
  lc=$(builtin cd "$SRC" && python3 -B "$STAT/stat_bwx.py" --pool w120-T72[LC]?-* | sed -n '/^== POOLED/,$p' | cut -c1-68)
  i=$(builtin cd "$SRC" && python3 -B "$STAT/stat_bwx.py" --pool w120-T72I?-* | sed -n '/^== POOLED/,$p' | cut -c1-68)
  ck "table of part A: not 12 rows" eq "$(block '^== part A ' '^== parts L and C ' | grep -cE '^[a-z]+ +bw_(old|new) +n=18 ')" 12
  ck "table of part A differs from the reference" eq "$(block '^== part A ' '^== parts L and C ')" "$a"
  ck "table of parts L and C differs from the reference" eq "$(block '^== parts L and C ' '^== control ')" "$lc"
  ck "table of the control differs from the reference" eq "$(block '^== control ' '^== complete')" "$i"
  ck "table of parts L and C has fewer than 3 kernel rows" test "$(echo "$lc" | grep -cE '^   [a-z0-9_]+ +[0-9]+ +[0-9.]+')" -ge 3
  ck "no line '== complete'" has "^== complete: run id $T, results in $DEST\$"
}

# ---------- scenarios ----------
scn_a() { # happy path with -y
  setup a; run /dev/null -y; complete_run_checks; finish 0; }
scn_a2() { # happy path with drivers that start their folders 2 s after the run id (stamps later than the run id)
  setup a2; conf GO_SLEEP=2 GO2_SLEEP=2; run /dev/null -y; complete_run_checks
  ck "no copied folder has a stamp later than the run id" eval '[ -n "$(dest_dirs | while read -r d; do [[ ${d##*-} > $T ]] && echo later; done)" ]'
  finish 0; }
scn_b() { # no argument, answer n
  setup b; run "$H/in-n"; ck "ssh was called $CALLS times" eq "$CALLS" 0; ck "no message 'not confirmed'" has 'not confirmed: no login was made'; no_dest; finish 2; }
scn_b2() { # no argument, end of input in place of an answer
  setup b2; run /dev/null; ck "ssh was called $CALLS times" eq "$CALLS" 0; ck "no message 'not confirmed'" has 'not confirmed: no login was made'; no_dest; finish 2; }
scn_b3() { # no argument, answer y: complete run. Started with the absolute path from another folder.
  setup b3; run_abs "$H/in-y"; complete_run_checks; ck "the question was not printed" has 'read the Slack channel #phoenix-crb'; finish 0; }
scn_b4() { # no argument, answer Y (capital): by the usage text only "y" confirms
  setup b4; run "$H/in-Y"; ck "ssh was called $CALLS times" eq "$CALLS" 0; no_dest; finish 2; }
scn_c() { # wrong argument
  setup c; run /dev/null -x; ck "ssh was called $CALLS times" eq "$CALLS" 0; ck "no usage line" has 'usage: ./manual-run.sh \[-y\]'; no_dest; finish 2; }
scn_c2() { # two arguments
  setup c2; run /dev/null -y -y; ck "ssh was called $CALLS times" eq "$CALLS" 0; ck "no usage line" has 'usage: ./manual-run.sh \[-y\]'; no_dest; finish 2; }
scn_c3() { # empty argument
  setup c3; run /dev/null ""; ck "ssh was called $CALLS times" eq "$CALLS" 0; ck "no usage line" has 'usage: ./manual-run.sh \[-y\]'; no_dest; finish 2; }
scn_d() { # marker file present
  setup d; : > "$HARNESS_STATE/positron-perf.RUNNING"; run /dev/null -y
  ck "ssh calls $CALLS, expected 1" eq "$CALLS" 1; no_start; no_dest
  ck "no message 'RUNNING file present'" has '^RUNNING file present, Jeremy or someone else is using CRB: stop$'
  ck "sudo was called" test ! -e "$HARNESS_STATE/sudo-calls.log"
  ck "a direct copy was written" test ! -e "$D/go-direct.sh"
  finish 3; }
scn_e() { # local.sha mismatch (ra.sh changed)
  setup e; echo "# changed" >> "$D/ra.sh"; run /dev/null -y; no_start; no_dest
  ck "no message 'a script differs'" has '^NOT STARTED: a script differs from local.sha or go2.sha$'
  ck "sudo was called before the checksum test" test ! -e "$HARNESS_STATE/sudo-calls.log"
  finish 4; }
scn_f() { # go2.sha mismatch
  setup f; echo "# changed" >> "$D/go2.sh"; run /dev/null -y; no_start; no_dest
  ck "no message 'a script differs'" has '^NOT STARTED: a script differs from local.sha or go2.sha$'
  finish 4; }
scn_g1() { # 10 modules by MemTotal
  setup g1; printf 'MemTotal:       329000000 kB\n' > "$HARNESS_STATE/meminfo"; run /dev/null -y; no_start; no_dest
  ck "no message 'memory is not confirmed'" has '^NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s$'
  ck "a direct copy was written" test ! -e "$D/go-direct.sh"; finish 5; }
scn_g2() { # 10 lines from dmidecode
  setup g2; conf SUDO_LINES=10; run /dev/null -y; no_start; no_dest
  ck "no message 'memory is not confirmed'" has '^NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s$'; finish 5; }
scn_g3() { # 12 modules at 8000 MT/s
  setup g3; conf SUDO_SPEED=8000; run /dev/null -y; no_start; no_dest
  ck "no message 'memory is not confirmed'" has '^NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s$'; finish 5; }
scn_h() { # sudo needs a password
  setup h; conf SUDO_FAIL=1; run /dev/null -y; no_start; no_dest
  ck "no message 'memory is not confirmed'" has '^NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s$'
  ck "the sudo error is not shown" has 'sudo: a password is required'; finish 5; }
scn_i() { # go.sh exits 1 after 4 folders
  setup i; conf GO_FAIL_AFTER=4; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "folders copied: $(dest_steps)" eq "$(dest_steps)" "k120-T72A1 k120-T72A2 w120-T72C1 w120-T72L1 "
  ck "files copied: $(dest_files)" eq "$(dest_files)" "go-T72-$T.log memcheck-$T.txt "
  ck "older run in the results folder" eq "$(dest_old)" ""
  ck "no message with status and folder" has "^manual-run.sh: go.sh ended with status 1. What it wrote is in $DEST\$"
  ck "the log is not shown" has '^FAILED: stand-in: failure after 4 folders$'; finish 10; }
scn_j() { # go.sh fine, go2.sh exits 1 after 1 folder
  setup j; conf GO2_FAIL_AFTER=1; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go go2 "
  ck "folders copied: $(dest_steps)" eq "$(dest_steps)" "${GO_STEPS/w120-T72L1/w120-T72I1 w120-T72L1}"
  ck "files copied: $(dest_files)" eq "$(dest_files)" "go-T72-$T.log go2-T72-$T.log memcheck-$T.txt "
  ck "no message with status and folder" has "^manual-run.sh: go2.sh ended with status 1. What it wrote is in $DEST\$"; finish 11; }
scn_k() { # go.sh exits 0, one k120 folder has 20 header lines
  setup k; conf GO_SHORT_K120=T72A2; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "no CHECK FAILED line for the folder" has '^CHECK FAILED: k120-T72A2-[0-9TZ]+: expected 24 headers and 72 intervals$'
  ck "no final message" has "^manual-run.sh: 1 checks failed for go.sh. The copied results are in $DEST\$"; finish 13; }
scn_l() { # go.sh exits 0, one w120-T72C folder is missing
  setup l; conf GO_SKIP=T72C3; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "no CHECK FAILED line for the count" has '^CHECK FAILED: w120-T72C\?-\*: 3 folders, expected 4$'
  ck "no final message" has "^manual-run.sh: 1 checks failed for go.sh. The copied results are in $DEST\$"; finish 13; }
scn_m() { # no ssh connection at the driver call
  setup m; conf SSH_FAIL_AT=2; run /dev/null -y; no_start
  ck "no message 'the ssh connection failed'" has "^manual-run.sh: the ssh connection failed. If go.sh was started, it runs on. Its log on CRB: ~/cache-perf/results/go-T72-$T.log\$"
  finish 255; }
scn_n() { # marker file appears after go.sh ended and before the copy
  setup n; conf MARKER_AT=3; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "no message 'no copy from CRB'" has "^manual-run.sh: no copy from CRB: marker file present. The results stay on CRB under run id $T\$"
  ck "results are not on the CRB side under the run id" test -s "$R/go-T72-$T.log"
  ck "something was copied: $(ls -A "$DEST" | tr '\n' ' ')" eq "$(ls -A "$DEST")" ""; finish 3; }
scn_o() { # python3 fails
  setup o; PATH_PREFIX="$H/pybad:"; run /dev/null -y
  ck "no message 'a read rate table was not printed'" has "^manual-run.sh: a read rate table was not printed. The results are complete in $DEST\$"
  ck "folders in the results folder: $(dest_steps)" eq "$(dest_steps)" "$EXPECTED_STEPS"; finish 14; }
stop_with_printed_command() { # NAME: the kill command of the message names the driver, the driver runs on, the command stops it
  local line pid spid
  line=$(sed -n 's/^A driver may still run on CRB. This command stops it: //p' "$O")
  pid=$(echo "$line" | sed -n "s/.*'kill -TERM -- -\([0-9]*\)'\$/\1/p"); spid=$(awk -v n="$1" '$1 == n {print $2}' "$HARNESS_STATE/started.log")
  NOTES+=("printed command: $line"); NOTES+=("pid of the stand-in $1: $spid")
  ck "no message 'interrupted'" has '^manual-run.sh: interrupted$'
  ck "the printed command does not name the pid of $1 ($spid): $pid" eq "$pid" "$spid"
  [ -n "$spid" ] || return 0
  ck "the driver did not run on after the interrupt" kill -0 "$spid"
  [ -n "$line" ] && PATH="$H/bin:$PATH" eval "$line"
  sleep 0.5
  ck "the printed command did not stop the driver" eval "! kill -0 $spid 2> /dev/null"
}
scn_p() { # SIGINT to the process group (Ctrl-C at the console) while go.sh runs
  setup p; conf GO_SLEEP=25; run_sig '^log .*/go-T72-.* pid [0-9]+$' 1 SIGINT group
  stop_with_printed_command go; ck "go2 was started" eq "$(started)" "go "; finish 130; }
scn_p2() { # SIGTERM to the script process alone ("kill PID" from another terminal) while go.sh runs for 8 s
  setup p2; conf GO_SLEEP=8; run_sig '^log .*/go-T72-.* pid [0-9]+$' 1 SIGTERM pid
  local secs; secs=$(echo "$SIGLINE" | sed -n 's/.*seconds_after_signal \([0-9.]*\).*/\1/p')
  ck "the script ended $secs s after the signal (limit for this check: 3 s)" eval "awk 'BEGIN{exit !($secs < 3)}'"
  ck "the message says that a driver may still run, but the stand-in driver had ended" eval "! { has '^A driver may still run' && grep -q '^ALLDONE' '$O'; }"
  finish 130; }
scn_p3() { # SIGINT to the process group while go2.sh runs
  setup p3; conf GO2_SLEEP=25; run_sig '^log .*/go2-T72-.* pid [0-9]+$' 1 SIGINT group
  stop_with_printed_command go2; ck "go.sh results were not copied before: $(dest_steps)" eq "$(dest_steps)" "$GO_STEPS"; finish 130; }
scn_p4() { # SIGINT to the process group during the checks (no driver started yet)
  setup p4; conf SUDO_SLEEP=6; run_sig '^== checks on CRB$' 1.5 SIGINT group
  ck "no message 'interrupted'" has '^manual-run.sh: interrupted$'; ck "a kill command is printed" hasnt 'A driver may still run'; no_start; no_dest; finish 130; }
scn_q() { # no ssh connection at the first call
  setup q; conf SSH_FAIL_AT=1; run /dev/null -y; no_start; no_dest
  ck "no message 'nothing was started'" has '^manual-run.sh: the checks on CRB ended with status 255: nothing was started$'; finish 255; }
scn_r() { # no ssh connection at the copy call after go.sh (usage text: 12 = copy failed, 255 = no ssh connection)
  setup r; conf SSH_FAIL_AT=3; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "no message about the copy" has 'the copy from CRB failed \(ssh status 255'; finish 12; }
scn_s() { # marker file appears between the checks and the start of go.sh
  setup s; conf MARKER_AT=2; run /dev/null -y; no_start
  ck "no message 'go.sh was not started'" has '^manual-run.sh: go.sh was not started: marker file present$'; finish 3; }
scn_t() { # marker file appears between the copy of the go.sh results and the start of go2.sh
  setup t; conf MARKER_AT=4; run /dev/null -y
  ck "drivers started: $(started)" eq "$(started)" "go "
  ck "no message 'go2.sh was not started'" has '^manual-run.sh: go2.sh was not started: marker file present$'
  ck "go.sh results not copied: $(dest_steps)" eq "$(dest_steps)" "$GO_STEPS"; finish 3; }
scn_u() { # marker file appears while go.sh runs: the driver fails with status 1, the marker file stays
  setup u; conf GO_FAIL_AFTER=2 MARKER_AT=3; run /dev/null -y
  ck "no message 'no copy from CRB'" has "^manual-run.sh: no copy from CRB: marker file present. The results stay on CRB under run id $T\$"; finish 3; }
scn_w() { # two complete runs, one after the other, in the same fake home: the second copies only its own folders
  setup w; run /dev/null -y
  local d1=$DEST t1=$T rc1=$RC d
  ck "first run: status $rc1" eq "$rc1" 0
  for d in $(dest_dirs); do : > "$R/$d/OLD-RUN"; done
  if [[ $d1 =~ $DEST_RE ]] && [ -d "$d1" ]; then rm -rf -- "$d1"; fi
  sleep 2; echo 0 > "$HARNESS_STATE/ssh-count"; : > "$HARNESS_STATE/started.log"; : > "$HARNESS_STATE/ssh-calls.log"
  run /dev/null -y; NOTES+=("first run id $t1, second run id $T"); complete_run_checks; finish 0; }
scn_x() { # one bwx12 folder has text in stderr.txt (the checks print the size and do not test it)
  setup x; conf GO_STDERR=T72L2; run /dev/null -y
  obs "text in stderr.txt does not change the result: $(grep -E '^w120-T72L2-.*stderr' "$O")"; finish 0; }
scn_y() { # the ssh connection ends 1 s after the start of go.sh; the driver runs on for 3 s
  setup y; conf SSH_DROP_AT=2 GO_SLEEP=3; run /dev/null -y
  ck "no message 'the ssh connection failed'" has "^manual-run.sh: the ssh connection failed. If go.sh was started, it runs on. Its log on CRB: ~/cache-perf/results/go-T72-$T.log\$"
  sleep 4
  ck "the driver did not run on to its end" eq "$(tail -n 1 "$R/go-T72-$T.log" 2> /dev/null)" ALLDONE
  finish 255; }

scn_p5() { # SIGHUP to the process group (the terminal closes) while go.sh runs. The usage text names no status for it:
  # the expectation here is only what bash does by default (status 129) and that the driver runs on.
  setup p5; conf GO_SLEEP=25; run_sig '^log .*/go-T72-.* pid [0-9]+$' 1 SIGHUP group
  local spid; spid=$(awk '$1 == "go" {print $2}' "$HARNESS_STATE/started.log")
  ck "the driver did not run on after SIGHUP" kill -0 "$spid"
  NOTES+=("last lines of the output: $(tail -n 2 "$O" | cut -c1-120 | tr '\n' '|')")
  has 'kill -TERM -- -' || obs "the script printed no message of its own (no pid, no kill command); the driver ran on"
  kill -TERM -- "-$spid" 2> /dev/null; sleep 0.5; finish 129; }
scn_p6() { # as p, but the fake ssh dies from SIGINT (default action) in place of ending with status 255
  setup p6; conf GO_SLEEP=25 SSH_INT=default; run_sig '^log .*/go-T72-.* pid [0-9]+$' 1 SIGINT group
  stop_with_printed_command go; finish 130; }
scn_v() { # go.sh ends with status 0, all folders complete, but the log does not end with ALLDONE
  setup v; conf GO_NO_ALLDONE=1; run /dev/null -y
  ck "no CHECK FAILED line for the log" has "^CHECK FAILED: go-T72-$T.log does not end with ALLDONE\$"; ck "drivers started: $(started)" eq "$(started)" "go "; finish 13; }
scn_z6() { # the direct copy cannot be written (go-direct.tmp is a folder)
  setup z6; mkdir "$D/go-direct.tmp"; run /dev/null -y; no_start; no_dest
  ck "no message 'could not be written'" has '^NOT STARTED: go-direct.sh could not be written$'; rmdir "$D/go-direct.tmp"; finish 6; }
scn_z7() { # the checks end with a status that the usage text does not list (1)
  setup z7; conf SSH_EXIT_AT=1 SSH_EXIT_CODE=1; run /dev/null -y; no_start; no_dest
  ck "no message with the status" has '^manual-run.sh: the checks on CRB ended with status 1: nothing was started$'; finish 7; }
scn_z7b() { # the checks end with status 0 but print no run id
  setup z7b; conf SSH_TRUE_AT=1; run /dev/null -y; no_start; no_dest
  ck "no message 'printed no run id'" has '^manual-run.sh: the checks on CRB printed no run id$'; finish 7; }
scn_z13() { # go2.sh ends with status 0 but wrote one folder in place of two
  setup z13; conf GO2_ONLY_ONE=1; run /dev/null -y
  ck "no CHECK FAILED line for the count" has '^CHECK FAILED: w120-T72I\?-\*: 1 folders, expected 2$'
  ck "no final message" has "^manual-run.sh: 1 checks failed for go2.sh. The copied results are in $DEST\$"; finish 13; }
scn_tb() { # the bwx12 files of go.sh hold 119 thread rows per interval: stat_bwx.py then prints no pooled row.
  # Usage text: "14 a read rate table was not printed".
  setup tb; conf GO_NO_CPU0=1; run /dev/null -y
  NOTES+=("lines between the heading of parts L and C and the next heading: $(block '^== parts L and C ' '^== control ' | wc -l)")
  ck "the table of parts L and C is empty and the script ends with 'complete'" eval '! { [ -z "$(block "^== parts L and C " "^== control ")" ] && has "^== complete"; }'
  finish 14; }
scn_sh() { # the login shell on the CRB side is sh (dash), not bash. This scenario FAILS by design of the script:
  # the copy command uses [[ ]]. CRB is not affected: the login of 2026-11-25 printed "shell /bin/bash bash 5.2.21".
  setup sh; conf REMOTE_SHELL=sh; run /dev/null -y; complete_run_checks; finish 0; }

for s in ${*:-$ALL}; do
  if declare -F "scn_$s" > /dev/null; then "scn_$s"; else echo "unknown scenario: $s"; fi
done
echo
echo "== summary: $SUMMARY"
cat "$SUMMARY"
echo
echo "== folders under tests/ that were not there before the test (expected: none)"
ls -1 "$REPO/tests" | diff "$H/tests-before.txt" - && echo none
echo "== git status --short of the repository"
git -C "$REPO" status --short
echo "== PASS $(grep -cE '^[a-z0-9]+ +PASS ' "$SUMMARY"), FAIL $(grep -cE '^[a-z0-9]+ +FAIL ' "$SUMMARY"), observations $(grep -c 'OBSERVATION' "$SUMMARY")"
echo "== sha256 of the tested file: $(sha256sum "$SCRIPT")"
