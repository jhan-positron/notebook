# `run_mesh.sh` explained, line by line

- Source file: `asct-2026-11-16/crb/run_mesh.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 63 lines, 4051 bytes).
- sha256 of the source when this page was built: `f8e25fa9e3b9b0a27dcbc38ae515846948e643dac15f073448786de7f0a97e0b`.

## Short version: purpose

`run_mesh.sh` is the script for the mesh-counter runs of the ASCT cross-check on CRB. For each line of a spec file it starts one ASCT benchmark process and reads the counters of the mesh as root with `perf stat -a` while the process runs, one counting window per event set. These runs did not happen, so no result of this script exists [Ref1].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **CMN**: Coherent Mesh Network, the name that Arm gives to the mesh. The mesh links the cores, the shared cache and the memory ports.
- **Mesh unit**: the counter unit that Linux shows for one mesh. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **Mesh counter, mesh event**: a hardware counter of the mesh counts events such as requests, retries or stalls. It does not belong to a core. Linux reads it through the `perf` interface.
- **`perf stat`**: the Linux command that counts events while another command runs.
- **Event set**: a named list of mesh events that one counting window counts together. The sets file holds one set per line.
- **Counting window**: one run of `perf stat -a` for the command `sleep`. Its length is `WIN` seconds.
- **Spec file of `run_mesh.sh`**: the input of the script. Each line has the form `tag|layout|bytes|nops|duration` and gives one process, or one idle pass.
- **Layout**: the CPUs that get a thread. `6456` is 64 threads on mesh 0 plus 56 on mesh 1. `6400` is mesh 0 only. `c2` is the one CPU 2. `idle` is no process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one spec line. The output file of its process is `TAG.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next spec line when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists (lines 9 to 10).
2. Read the two arguments and the settings `WIN` and `DELAY` (lines 11 to 14).
3. Stop when `sudo` would need a password (line 15).
4. Create the result folder, write the start state to `env.txt` and copy the sets file (lines 16 to 18).
5. Test every event of the sets file with a short `perf stat` run, and write the events that can be counted to `sets.ok` (lines 19 to 26).
6. For each spec line: check the two stop files, wait for a quiet machine, pause 5 s and write a `launch` line. Then start the benchmark process in the background, unless the layout is `idle`. The function `cpuflags` gives the `--bw-cpu` options. Then wait `DELAY` seconds (lines 31 to 45).
7. For each event set of `sets.ok`: run one counting window of `WIN` seconds and write its start time and its end time to `launches.txt` (lines 46 to 55).
8. Wait for the end of the process and write its exit status (lines 56 to 59).
9. After the last spec line: give the result files to the user and print a short summary (lines 61 to 63).

## Behavior a reader must know

- This script did not run in the cross-check. The permission system of the agent session refused the command with `sudo -n perf stat -a` [Ref1]. So this page describes the code only.
- Root is used by three kinds of commands: the test `sudo -n true` (line 15), `perf stat -a` (line 23, line 52) and `chown` on the result folder (line 61). The header comment names `perf stat -a` only. None of them changes a system setting.
- What is counted: `perf stat -a` counts on the whole system. A count holds the mesh events of everything that runs on the machine during the window, not only of the benchmark process.
- What a window covers: `perf` counts while `sleep $WIN` runs. The two `win` times in `launches.txt` are read by the shell before and after the `sudo` command. So they also hold the start time and the end time of `sudo` and `perf`.
- Nothing ties a window to the measured phase of the process. The first window starts `DELAY` seconds after the launch. By the decisions file, the analysis script `analyze.py` checks that every window lies inside the measured phase [Ref1].
- The event test of line 23 uses the unit `arm_cmn_0` only. An event that opens there is then counted on both units.
- Exit statuses: 3 for the marker file (at the start, before every spec line, before every window, and during the wait for the process), 4 for the STOP file (before every spec line), 5 when `sudo` needs a password, 2 for a one-core layout with CPU 120 to 127.
- When the marker file appears during a process, the script sends the termination signal to that process before it ends.
- A layout name that `cpuflags` does not know, such as `5656`, does not stop the script (line 28). The binary would start without any `--bw-cpu` option.
- The exit status of the benchmark process is written to `launches.txt` but not tested.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/run_mesh.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (63 lines, 4051 bytes, sha256 `f8e25fa9e3b9b0a27dcbc38ae515846948e643dac15f073448786de7f0a97e0b`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 62. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Header comment (lines 1 to 7)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_mesh.sh NAME SETS < spec - mesh (CMN) counters while one ASCT bandwidth process runs. ROOT IS USED FOR` | Comment: the usage. The script takes two arguments, a name and the file with the event sets. It reads a spec file as its input. It reads the counters of the mesh (CMN) while one bandwidth process of ASCT runs. |
| 3 | `# 'perf stat -a' ONLY (read-only counters, as rc.sh of 2026-11-15). No system setting is changed. The benchmark` | Comment, continued: root rights are used for `perf stat -a` only. That command reads counters and changes nothing, as `rc.sh` of 2026-11-15 does. No system setting is changed. The code uses `sudo` at two more places: for the test `true` in line 15 and for `chown` in line 61. |
| 4 | `# process itself runs without root. CPUs 0-119 only for the benchmark.` | Comment, continued: the benchmark process itself runs without root rights, and on the CPUs 0 to 119 only. |
| 5 | `# spec lines: tag\|layout\|bytes\|nops\|duration   layout: 6456, 6400, c<cpu> (one core), idle (no process, sleep only)` | Comment: a spec line has the form `tag\|layout\|bytes\|nops\|duration`. The layout is `6456`, `6400`, the letter `c` with a CPU number for one core, or `idle`. With `idle` no process starts, and the script counts while the machine does nothing. The code also accepts the layout `0056` (line 28). |
| 6 | `# SETS: one event set per line, setname\|ev1;ev2;...  Each event is counted as arm_cmn_0/EV/ and arm_cmn_1/EV/.` | Comment: the file SETS holds one event set per line, in the form `setname\|ev1;ev2;...`. Each event is counted on both mesh units, as `arm_cmn_0/EV/` and as `arm_cmn_1/EV/`. |
| 7 | `# Environment: WIN = seconds per counting window (default 4), DELAY = seconds from launch to the first window.` | Comment: two environment variables. `WIN` is the length of one counting window in seconds, default 4. `DELAY` is the time in seconds from the launch to the first window. The comment gives no default for `DELAY`. Line 11 sets 8. |

### Settings, checks and the record of the start state (lines 8 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 8 | `set -u` | `set -u`: the script stops when it uses a variable that was never set. There is no `set -e`. So a failed command alone does not stop the script. |
| 9 | `M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP` | `M`: the path of the marker file. `STOP`: the path of the STOP file, `cache-perf/STOP` in the home folder of the user. |
| 10 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check at the start. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 11 | `name=$1; sets=$2; WIN=${WIN:-4}; DELAY=${DELAY:-8}` | Reads the two arguments and two settings. `name` becomes a part of the name of the result folder. `sets` is the path of the file with the event sets. `WIN`: the length of one counting window, default 4 s. `DELAY`: the wait between the start of the process and the first window, default 8 s. `${WIN:-4}` gives 4 when `WIN` is not set or is empty. |
| 12 | `W=$HOME/cache-perf/asct-20261116` | `W`: the work folder on CRB. No later line of this script uses it. |
| 13 | `PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin` | `PLAIN`: the installed binary, the benchmark program that the installer of ASCT built. This script uses no probe binary. |
| 14 | `NUMA=$(command -v numactl \|\| ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)` | `NUMA`: the path of `numactl`. `command -v` gives the one in the search path. When there is none, `ls` gives the copy in the ASCT installation if it exists. If both fail, `NUMA` is empty. |
| 15 | `sudo -n true 2>/dev/null \|\| { echo "sudo needs a password: stop, nothing was run"; exit 5; }` | Root test. `sudo -n true` runs the command `true`, which does nothing, as root. `-n` means that `sudo` never asks for a password and fails when it would need one. On failure the script prints `sudo needs a password: stop, nothing was run` and ends with exit status 5. It has written no file at this point. |
| 16 | `out=$HOME/cache-perf/results/asct-mesh-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `asct-mesh-`, the name of argument 1 and the UTC time of this moment (`date -u`). `mkdir -p` creates it. |
| 17 | `{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; sha256sum $PLAIN; echo "WIN $WIN DELAY $DELAY sets $sets"; } > $out/env.txt 2>&1` | Writes the file `env.txt`: the UTC date and time, the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), the sha256 of the installed binary, and one line with `WIN`, `DELAY` and the path of the sets file. The braces group the commands. The output and the error messages (`2>&1`) of the group go to the file. |
| 18 | `cp $sets $out/sets.txt` | Copies the sets file into the result folder under the name `sets.txt`. |
| 19 | `: > $out/sets.ok` | Creates the empty file `sets.ok`. The command `:` does nothing, and `>` creates the file or empties it. |

### Test of every event: which ones can be counted (lines 20 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `while IFS='\|' read -r sn evs; do` | Starts a loop over the lines of the sets file (line 26). `IFS='\|'` splits each line at the first `\|`. The set name goes to `sn`. The list of events goes to `evs`. `-r` keeps each backslash as it is. |
| 21 | `  [ -z "$sn" ] && continue; ok=` | Skips a line with an empty set name (`-z`). Then it empties `ok`. `ok` collects the events of this set that can be counted. |
| 22 | `  for e in ${evs//;/ }; do` | Starts a loop over the events of the set. `${evs//;/ }` replaces every `;` of the list with a space. The shell then splits the text into single event names. |
| 23 | `    if sudo -n perf stat -a -x, -e "arm_cmn_0/$e/" -o /dev/null -- true 2>/dev/null < /dev/null; then ok="$ok;$e"; else echo "unsupported $sn $e" >> $out/unsupported.txt; fi` | Tests one event. `sudo -n` runs `perf stat` as root. `perf stat` counts events while a command runs. `-a`: count on all CPUs of the system, not only for the command. `-x,`: print the result as fields with a comma between them. `-e "arm_cmn_0/$e/"`: the event to count, here the event `e` of the mesh unit `arm_cmn_0` only. `-o /dev/null`: discard the result. `--` ends the options of `perf`. The command is `true`, which ends at once. Error messages are discarded, and the input is empty. On success the line adds `;` and the event name to `ok`. On failure it appends `unsupported`, the set name and the event name to `unsupported.txt` [Ref2]. |
| 24 | `  done` | Ends the loop of line 22. |
| 25 | `  [ -n "$ok" ] && echo "$sn\|${ok#;}" >> $out/sets.ok` | When `ok` is not empty (`-n`): appends one line to `sets.ok`, in the form of the sets file. `${ok#;}` is `ok` without its first `;`. A set in which no event passed the test gets no line. |
| 26 | `done < $sets` | Ends the loop of line 20. Its input is the sets file. |

### Function `cpuflags`: the `--bw-cpu` options of a layout (lines 27 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `cpuflags() {` | Starts the function `cpuflags`. It gets a layout name and prints the `--bw-cpu` options for that layout, one option per CPU. |
| 28 | `  case $1 in 6456) r="0-119";; 6400) r="0-63";; 0056) r="64-119";; c*) r="${1#c}-${1#c}";; *) echo "bad layout $1" >&2; exit 2;; esac` | Chooses the CPU ranges. `6456`: the CPUs 0 to 119. `6400`: the CPUs 0 to 63, mesh 0 only. `0056`: the CPUs 64 to 119, mesh 1 only. A name that starts with `c`: `${1#c}` is the name without the `c`, so the range holds this one CPU. Any other name: the function prints `bad layout` and the name to the error output and calls `exit 2`. Line 41 calls `cpuflags` inside `$( )`, which runs it in a copy of the shell. This `exit` therefore ends only the copy, and the script goes on. The binary then gets no `--bw-cpu` option. |
| 29 | `  for part in $r; do for c in $(seq ${part%-*} ${part#*-}); do printf -- '--bw-cpu %d ' $c; done; done` | Prints the options. The outer loop takes each range of `r`. `${part%-*}` is the range without its last `-` and what follows, so the first CPU. `${part#*-}` is the range without everything up to the first `-`, so the last CPU. `seq` prints all numbers from the first to the last. `printf` writes `--bw-cpu`, the number and a space for each. The `--` in front tells `printf` that the next word is the format text and not an option. |
| 30 | `}` | Ends the function `cpuflags`. |

### Main loop: checks and launch of one process per spec line (lines 31 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `while IFS='\|' read -r tag lay bytes nops dur <&3; do` | Starts the main loop, one pass per line of the spec file. `IFS='\|'` splits the line into five fields: `tag` (the name of the case), `lay` (the layout), `bytes` (the buffer size of each thread), `nops` (the number of injected NOPs) and `dur` (the length of the measured phase in seconds). `<&3` makes `read` take the line from file descriptor 3, which line 60 makes a copy of the standard input of the script. |
| 32 | `  [ -z "$tag" ] && continue` | Skips a line with an empty tag. |
| 33 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check before every spec line. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 34 | `  [ -e $STOP ] && { echo "STOP file: stop"; exit 4; }` | Check of the STOP file before every spec line. When it exists, the script prints `STOP file: stop` and ends with exit status 4. |
| 35 | `  for i in $(seq 60); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 60 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, which has a form such as `1/1100`. `cut -d/ -f1` keeps the number in front of the slash. This is the number of tasks that are runnable now. When `r` is 2 or less (`-le`), `break` ends the loop. If not, the script sleeps 1 s and tests again. After 60 tries the script goes on without a message. |
| 36 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 37 | `  echo "launch $tag epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who \| wc -l) layout $lay bytes $bytes nops $nops duration $dur" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the time of this moment in seconds with nanoseconds (`date +%s.%N` counts from 1970-01-01 UTC), the content of `/proc/loadavg`, the number of logins, and the four other fields of the spec line. The script `analyze.py` reads the layout, the size, the NOP count and the duration from this line. |
| 38 | `  pid=` | Empties `pid`. An empty `pid` means that this pass has no benchmark process. |
| 39 | `  if [ "$lay" != idle ]; then` | The lines lines 40 to 43 run for every layout other than `idle`. |
| 40 | `    case $lay in c*) case ${lay#c} in 12[0-7]) echo "CPU ${lay#c} is not allowed"; exit 2;; esac;; esac` | Guard for a one-core layout. `${lay#c}` is the CPU number. When it matches `12[0-7]`, so 120 to 127, the script prints `CPU N is not allowed` and ends with exit status 2. The `launch` line of line 37 is already written at this point. |
| 41 | `    taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PLAIN --duration $dur --delay-seconds 0 $(cpuflags $lay) --bw-buflen $bytes \` | Starts the installed binary. `taskset -c 0-119` allows the process to run on the CPUs 0 to 119 only. `${NUMA:+$NUMA --membind 0}` gives `numactl --membind 0` when `NUMA` is not empty. The process then gets its memory from NUMA node 0 only. `--duration $dur`: the length of the measured phase in seconds. `--delay-seconds 0`: the delay setting of the binary is 0 s. `$(cpuflags $lay)` puts one `--bw-cpu` option per CPU of the layout here. The binary runs one read thread on each of these CPUs. `--bw-buflen $bytes`: the buffer size of each thread. The backslash at the end continues the command in the next line. |
| 42 | `        --bw-fine-delay $nops --bw-write=0 --bw-cacheline-bytes 64 > $out/$tag.out 2>&1 < /dev/null &` | Continues the command of line 41. `--bw-fine-delay $nops`: the number of injected NOPs. `--bw-write=0`: all accesses are reads. `--bw-cacheline-bytes 64`: one cache line has 64 bytes. The output and the error messages of the binary go to the file `TAG.out` in the result folder. The input is `/dev/null`, an empty input. The `&` at the end starts the process in the background. The script goes on immediately. |
| 43 | `    pid=$!` | `pid`: the process id of the process that line 41 started. `taskset` and `numactl` replace themselves with the next program in the same process. So this is the process id of the binary. |
| 44 | `  fi` | Ends the `if` of line 39. |
| 45 | `  sleep $DELAY` | Sleeps `DELAY` seconds. With a process, this is the time between its start and the first counting window. With the layout `idle` the script sleeps too. |

### The counting windows: one `perf stat` run per event set (lines 46 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `  while IFS='\|' read -r sn evs; do` | Starts a loop over the event sets that passed the test: one line of `sets.ok` per pass (line 54). The set name goes to `sn`, the events to `evs`. |
| 47 | `    if [ -n "$pid" ]; then kill -0 $pid 2>/dev/null \|\| { echo "process ended before set $sn of $tag" >> $out/launches.txt; break; }; fi` | Only when this pass has a process: `kill -0 $pid` sends no signal and only tests whether the process still exists. When it has ended, the script appends `process ended before set SN of TAG` to `launches.txt`, and `break` leaves the loop of the sets. The sets that are left get no window. |
| 48 | `    [ -e $M ] && { [ -n "$pid" ] && kill $pid; echo "marker: killed"; exit 3; }` | Marker check before every window. When the marker file exists, the script sends the termination signal to the process if there is one (`kill $pid`), prints `marker: killed` and ends with exit status 3. |
| 49 | `    el=` | Empties `el`, the event list of this window. |
| 50 | `    for e in ${evs//;/ }; do el="$el,arm_cmn_0/$e/,arm_cmn_1/$e/"; done` | Builds the event list. For each event of the set it appends `,arm_cmn_0/EV/,arm_cmn_1/EV/` to `el`. So each event is counted once on each mesh unit. |
| 51 | `    echo "win $tag $sn start $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win TAG SN start` with the time of this moment to `launches.txt`. The shell reads this time before `sudo` and `perf` start. |
| 52 | `    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/$el" -o $out/$tag.$sn.perf -- sleep $WIN 2>> $out/stderr.txt < /dev/null` | One counting window. `sudo -n` runs `perf stat` as root. `-a`: all CPUs of the system, so the counts hold the mesh traffic of every process of the machine. `-x,`: fields with a comma between them. `-e`: the events, first `dtc_cycles` (the cycle counter of a mesh unit [Ref3]) of both units, then the events of `el`. `-o`: the result file `TAG.SN.perf`. After `--` stands the command `sleep $WIN`. `perf` counts from the start to the end of that command, so for about `WIN` seconds. Error messages are appended to `stderr.txt`. The input is empty. Each result line holds the count, the event name, the time that the counter ran and the share of the window in percent for which it ran [Ref2]. |
| 53 | `    echo "win $tag $sn end $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win TAG SN end` with the time of this moment to `launches.txt`. The shell reads this time after `perf` has ended. |
| 54 | `  done < $out/sets.ok` | Ends the loop of line 46. Its input is the file `sets.ok`. |
| 55 | `  echo "sets done $tag $(date +%s.%N)" >> $out/launches.txt` | Appends the line `sets done`, the tag and the time of this moment to `launches.txt`. |

### End of the process and summary (lines 56 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `  if [ -n "$pid" ]; then` | The lines lines 57 to 58 run only when this pass has a process. |
| 57 | `    while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done` | Waits for the process and watches the marker file. The loop runs as long as the process exists (`kill -0`). Once per second: when the marker file exists, `kill $pid` sends the termination signal to the process, and the script prints `marker: killed` and ends with exit status 3. If not, `sleep 1` waits 1 s. |
| 58 | `    wait $pid; echo "rc $? $tag epoch $(date +%s.%N)" >> $out/launches.txt` | `wait $pid` returns the exit status of the binary. The line appends `rc`, that status, the tag and the time of this moment to `launches.txt`. The time can be up to about 1 s later than the real end of the process. The status is not tested. The script `analyze.py` takes this time as the end of the measured phase. |
| 59 | `  fi` | Ends the `if` of line 56. |
| 60 | `done 3<&0` | Ends the main loop of line 31. `3<&0` makes file descriptor 3 a copy of the standard input of the script for the whole loop. So line 31 reads the spec lines from descriptor 3, and the loop of line 46 can use the standard input for `sets.ok`. |
| 61 | `sudo -n chown -R $(id -un): $out 2>/dev/null` | Gives the result folder and all files in it to the user of the script. `sudo -n chown -R` runs as root. `$(id -un):` is the user name with a colon. It makes the user the owner and sets the group to the login group of the user. `perf` ran as root, so root owns the `.perf` files before this line. Error messages are discarded. |

Line 62 holds a backslash directly before a `|`. It stands outside the table:

```text
echo "done $out"; cat $out/unsupported.txt 2>/dev/null; grep -c '^win .* start' $out/launches.txt; grep '^rc\|ended' $out/launches.txt
```

Explanation of line 62: Prints `done` and the path of the result folder. Then it prints `unsupported.txt` when the file exists. Then the number of windows: the lines of `launches.txt` that start with `win` and hold ` start`. Then the lines that start with `rc` or hold `ended`.

| Line | Source | Explanation |
|---:|---|---|
| 63 | `wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt; grep -h "Total Bandwidth (MB/sec)" $out/*.out 2>/dev/null; cat /proc/loadavg` | Prints the size of `stderr.txt` in bytes (`wc -c`) and its first 600 bytes (`head -c 600`). Then it prints the line `Total Bandwidth (MB/sec)` of every output file, without file names (`-h`), and the content of `/proc/loadavg`. The exit status of the script is the status of this last command. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs, check in `analyze.py`) and "Record of 2026-11-16 23:50 UTC" (the mesh-counter runs did not happen).
- [Ref2] external source: Linux manual page perf-stat(1), options `-a`, `-x`, `-e`, `-o` and section "CSV FORMAT".
- [Ref3] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": one counter unit per mesh, and the cycle counter of the DTC node of a mesh.
