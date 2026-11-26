# `run_partA.sh` explained, line by line

- Source file: `new-test-kernel/run_partA.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 123 lines, 9318 bytes).
- sha256 of the source when this page was built: `0f496ca60a1127880ae48ef14a63d28205dce3d9d8bc9edb7feefbf28f84d167`.

## Short version: purpose

`run_partA.sh` runs Part A, the screening part of the test plan of 2026-11-13, on CRB, the Arm server under test: in the steps A1 to A6 it starts the two existing benchmark binaries `bw_old` and `bw_new` one process at a time, and in step A7 it reads system information. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan: the commands, what each step runs, and how to analyse the results.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The steps A1 to A6 start benchmark processes. Step A7 only reads system files.
- **Part C of the plan**: a later part of the plan. It reads the counters of the cores while the benchmark runs. This is not the part C of the later rerun.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`asmwrite`**: the hand-written write loop of the benchmark.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of this script**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`. The option `--reps` gives the number of repetitions per kernel, and `--min-ms` gives the shortest length of each.
- **Tag**: the short name of a process in its csv file, for example `read_old-r1`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. The script starts no process that could run past it, and it ends a process that still runs at that time. The value `none` sets no limit.
- **`MARGIN`**: a number of seconds. The script starts a process only when `STOP_AT` is more than `MARGIN` seconds away. It is 150 s when the variable is not set or is empty.
- **Block**: a time window that another user has reserved on CRB.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter device**: the name under which Linux offers one group of hardware counters, as a folder in `/sys/bus/event_source/devices/`.
- **SVE**: the scalable vector instructions of Arm. The length of an SVE vector register is set per process.
- **Process group**: a set of processes that one signal can reach together.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **est.**: an estimate, not a measurement.

## Main flow

1. Limit the script and everything that it starts to the CPUs 0 to 119 (lines 11 to 12).
2. Require `STOP_AT` and set the stop controls: the paths of the marker file and of the stop file, the stop time, `MARGIN` and the trap for an interruption (lines 13 to 31).
3. Test the stop reasons once, before any file is written (line 32).
4. Check that `bw_old` and `bw_new` lie beside the script and have the expected sha256 (lines 33 to 40).
5. Read the step list, make the result folder and write the state of the machine to `env.txt` (lines 41 to 52).
6. Run the steps in the order of the call (lines 85 to 120). The steps A1 to A6 start their processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line, starts the binary, and tests the stop reasons once per second until the binary ends.
7. Step A1: the six kernels with 120 threads and 256 MiB per thread, 3 repetitions of at least 0.5 s, in 2 rounds with reversed order: 12 processes (lines 86 to 88).
8. Step A2: the same with repetitions of at least 6 s for the read kernels and 15 s for the write kernels: 12 processes (lines 89 to 92).
9. Step A3: the old read kernel with one buffer per thread and with two, at 0.5 s and at 6 s: 12 processes. The step is skipped when less than 70 GiB of memory are available (lines 93 to 99).
10. Step A4: the old read kernel and `asmread` at 11 thread counts per mesh, 2 repetitions of at least 6 s: 22 processes (lines 100 to 104).
11. Step A5: `asmread` with one thread and 8 MiB, 30 repetitions of at least 0.3 s, 2 processes on CPU 2 and 2 on CPU 41 (lines 105 to 108).
12. Step A6: `asmread` with one thread on CPU 2 and 8 MiB, 8 processes with huge pages allowed and 8 with `--no-thp`, alternating (lines 109 to 113).
13. Step A7: write the SVE vector length, the event list of `perf`, the names of the counter devices and the event codes of the cores to four files (lines 114 to 118).
14. Append the end line and the huge page counters to `env.txt`, and print the path of the result folder (lines 121 to 123).

## Behavior a reader must know

- The script times nothing. All timing happens inside `bw_old` and `bw_new`. The script sets how long and how often they time: `--reps` and `--min-ms`.
- What the benchmark times in one repetition (function `worker` of `bandwidth.c` and of `bandwidth.orig.c`): each thread first makes one warm-up pass over its buffer, which is not timed. Then a barrier releases all threads together, and each thread reads the clock for its own start time. Each thread runs whole passes and reads the clock after each pass, for the two buffer sizes of Part A. It stops at the first clock reading at which at least `--min-ms` have passed after its own start. So the threads of one repetition stop at different times (whole-pass stop).
- Eight things end the run early:
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A benchmark process ends with a status other than 0: status 1. The next process does not start. The header comment does not list this status.
  - A value of `STOP_AT` that `date` cannot read, a missing binary, a wrong sha256 of a binary, or an unknown step name: status 2. The unknown step name is found only when its turn comes, after the steps before it have run (line 119).
  - `STOP_AT` is empty or not set: the shell ends the script at line 15. The line names no status. A test with bash 5.1.16 gave status 1.
  - Any other command that fails where no line handles the failure, for example `mkdir` in line 43: the shell option `-e` ends the script with the status of that command (line 11).
- The first three stop reasons are tested at these places: once before any file is written (line 32), twice before each launch (line 61, line 65), in every turn of the wait for a quiet system (line 57), once at the start of step A7 (line 114), and once per second while a process runs (line 71).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later (line 19). After a stop by the marker file, the stop file or `STOP_AT`, the csv file gets a line that starts with `-- killed` (line 72). After an interruption by a signal it gets no such line (line 31).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message (line 57). There is no fixed pause. The header line of each process gives the waited seconds as `waited_s`.
- For each launch the script records the load in two places. `launches.txt` gets a line with the load averages and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` (line 64). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in the csv file gets the waited seconds, the load averages, the number of logins, the UTC time and the options (line 66).
- While a benchmark runs, the script starts one `date` process and one `sleep` process per second (line 26, line 73). They may run on any of the CPUs 0 to 119. In the steps with 120 threads each of these CPUs also runs one pinned benchmark thread.
- An old kernel and a hand-written kernel never come from the same binary: `read_old` and `write_old` run in `bw_old`, and `asmread` and `asmwrite` run in `bw_new` (line 80).
- Step A3 is skipped without an error when less than 70 GiB of memory are available. The message goes to `env.txt` and to the error output (line 94).
- The second process of an A5 pair does not always start at once. It starts after the same wait for a quiet system as every other process (line 105).
- The script deletes nothing. At every stop the files that were written before stay. The end line of `env.txt` is written only when no stop ended the script before (line 121). A skipped step A3 does not prevent the end line (line 94).
- The text of this file is the text that ran on CRB on 2026-11-13, in two calls: first the steps A7, A5 and A6, then the steps A1 to A4 [Ref1]. The comment of line 10 is older than that run.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/run_partA.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (123 lines, 9318 bytes, sha256 `0f496ca60a1127880ae48ef14a63d28205dce3d9d8bc9edb7feefbf28f84d167`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: purpose, usage, exit statuses, needs, status (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_partA.sh - Part A (screening) of new-test-kernel/plan.md, on CRB.` | Comment: the name and the purpose of the file. The script runs Part A of the test plan `plan.md` on CRB. Part A is screening: a first look with the two existing benchmark binaries. By the plan it closes no hypothesis. |
| 3 | `# Usage: STOP_AT=<UTC time or "none"> run_partA.sh [A1 A2 A3 A4 A5 A6 A7]   (no step: all steps)` | Comment: the usage. The caller sets the environment variable `STOP_AT` to a UTC time or to the word `none`. The arguments are step names from `A1` to `A7`. The steps run in the order of the call. Without an argument all seven steps run. |
| 4 | `#   STOP_AT is required. Example: STOP_AT=2026-11-14T15:00Z (start nothing that could run past this` | Comment: `STOP_AT` must be set. The example `2026-11-14T15:00Z` is a UTC time. With a time the script starts nothing that could still run at that time. The sentence ends in line 5. |
| 5 | `#   time, e.g. 30 min before a block of Jeremy), or STOP_AT=none when no block is announced.` | Continues the comment: the example is a time 30 min before a block. A block is a time window that another user has reserved on CRB. `STOP_AT=none` sets no time limit. It is for a run at which no block is announced. |
| 6 | `# Exit status: 0 done; 2 usage or wrong binaries; 3 marker file appeared; 4 STOP_AT reached;` | Comment: the exit statuses. 0: all steps are done. 2: a wrong usage or wrong binaries. 3: the marker file exists. 4: the time `STOP_AT` is reached. The list is not complete. The code also ends with status 1 when a benchmark process fails (line 76). It ends with status 4 also before a launch when `STOP_AT` is `MARGIN` seconds away or less (line 30). The check for a missing `STOP_AT` names no status (line 15). |
| 7 | `#   5 stop file ~/cache-perf/STOP found; 130 interrupted. In every case the csv files written so far are kept.` | Continues the comment: 5: the stop file `~/cache-perf/STOP` exists. 130: a signal interrupted the script. In every case the csv files that were written before the stop are kept. The script holds no command that deletes a file. |
| 8 | `# Needs bw_old and bw_new in the same folder as this script (see handoff.md).` | Comment: the two binaries `bw_old` and `bw_new` must lie in the folder of this script. The handoff note `handoff.md` names that folder on CRB and the sha256 that each binary must have. |
| 9 | `# Uses CPUs 0-119 only, writes only under $HOME/cache-perf, no sudo.` | Comment: the script uses the CPUs 0 to 119 only (line 12). It writes only below `$HOME/cache-perf`. It never uses `sudo`, the tool that runs a command as root. |
| 10 | `# Status: written 2026-11-13, syntax-checked only, never run.` | Comment: the state of the file when it was written, on 2026-11-13: only its syntax was checked, and it had never run. Later this text ran on CRB: the file `env.txt` of each of the two result folders of Part A records the sha256 of this file [Ref1]. |

### Shell options, restart on the CPUs 0 to 119, settings of the stop controls (lines 11 to 18)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `set -euo pipefail` | Sets three shell options. `-e`: the script stops when a command fails (exit status not 0). A command that is tested by `if` or `while`, or that stands before `\|\|` or `&&`, does not stop it. `-u`: the script stops when it uses a variable that was never set. `-o pipefail`: a pipeline (commands joined with `\|`) counts as failed when any command of it fails, not only the last one. |
| 12 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Limits the script and everything that it starts to the CPUs 0 to 119. `${_PINNED:-}` gives the value of `_PINNED`, or an empty text when the variable is not set. `-z` tests for an empty text. On the first pass the variable is empty. Then `exec` replaces the shell with `taskset -c 0-119`. That tool sets the CPU list and starts this script again (`$0`) with the same arguments (`"$@"`) and with `_PINNED=1` in its environment. On the second pass the variable is set, and the script goes on. Every benchmark process inherits this CPU list. The benchmark itself then pins each of its threads to one CPU of its option `--cpus`. A caller that has already set `_PINNED` to a text that is not empty gets no CPU limit from this line. |
| 13 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. |
| 14 | `STOPFILE=$HOME/cache-perf/STOP     # ours: "touch ~/cache-perf/STOP" from another login stops this script` | `STOPFILE`: the path of the stop file, `$HOME/cache-perf/STOP`. The stop file is our own stop signal. By the comment the command `touch ~/cache-perf/STOP` from another login creates it, and the script then stops (line 25). |
| 15 | `: "${STOP_AT:?set STOP_AT to a UTC time like 2026-11-14T15:00Z, or to none}"` | Requires `STOP_AT`. The command `:` does nothing. The shell only expands its argument. `${STOP_AT:?text}` gives the value of `STOP_AT`. When the variable is empty or not set, the shell prints the text to the error output and ends the script. The line names no exit status. A test of this construct with bash 5.1.16 gave exit status 1, not the 2 that line 6 names for a wrong usage. |
| 16 | `if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) \|\| { echo "bad STOP_AT" >&2; exit 2; }; fi` | `STOP_EPOCH`: the stop time as a number. With `STOP_AT=none` it is 0, which stands for no limit. In every other case `date -u -d "$STOP_AT" +%s` converts the text to a number of seconds, counted from 1970-01-01 00:00 UTC. When `date` cannot read the text, the script prints `bad STOP_AT` to the error output (`>&2`) and ends with exit status 2. |
| 17 | `MARGIN=${MARGIN:-150}              # seconds: longest single process of this script (est.) plus reserve` | `MARGIN`: a number of seconds. A process starts only when `STOP_AT` is more than `MARGIN` seconds away (line 30). It is 150 s when `MARGIN` is not set or is empty. `${X:-default}` gives the value of `X`, or the default when `X` is empty or not set. By the comment 150 s is an estimate (est.) of the longest single process of this script plus a reserve. |
| 18 | `CHILD=""` | `CHILD`: the process id of the running benchmark. It is empty when none runs. |

### Stop controls: `stop_child`, `why_stop`, `check_marker`, `check_deadline`, the trap (lines 19 to 32)

| Line | Source | Explanation |
|---:|---|---|
| 19 | `stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null \|\| true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null \|\| true; wait "$CHILD" 2>/dev/null \|\| true; CHILD=""; fi; }` | Defines `stop_child`, which ends the running benchmark. The benchmark runs in its own process group (line 68). `-n` tests for a text that is not empty. When `CHILD` is not empty: `kill -- -"$CHILD"` sends the termination signal (TERM) to every process of that group. The minus sign before the id selects the group. After 1 s (`sleep 1`), `kill -9` sends the signal KILL to the group. No process can ignore that signal. `wait` then collects the ended benchmark, and `CHILD` is emptied. `2>/dev/null` discards an error message, for example when the group has ended before. `\|\| true` keeps `set -e` from stopping the script after such a failure. |
| 20 | `# why_stop: prints the reason and returns the exit status to use, or returns 0 if nothing asks us to stop.` | Comment: the function `why_stop` prints the reason for a stop and returns the exit status that the script must use. It returns 0 when nothing asks for a stop. |
| 21 | `# It is called in every turn of the wait and every second while a benchmark runs, so STOP_AT itself is` | Continues the comment: the script calls `why_stop` in every turn of the wait before a launch, and once per second while a benchmark runs. The sentence ends in line 22. |
| 22 | `# enforced on a running benchmark. check_deadline adds the margin before a launch.` | Continues the comment: so the time `STOP_AT` also stops a benchmark that is running. Before a launch the function `check_deadline` asks for more: `STOP_AT` must be at least `MARGIN` seconds away. |
| 23 | `why_stop() {` | Starts the function `why_stop`. It tests three stop reasons in a fixed order: the marker file, the stop file, the time `STOP_AT`. |
| 24 | `  if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; return 3; fi` | `-e` tests whether a file exists. When the marker file exists, the function prints `RUNNING file present: stop` to the error output and returns 3. |
| 25 | `  if [[ -e $STOPFILE ]]; then echo "stop file $STOPFILE present: stop" >&2; return 5; fi` | When the stop file exists, the function prints `stop file`, the path and `present: stop` to the error output, and returns 5. |
| 26 | `  if (( STOP_EPOCH && $(date -u +%s) >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT reached: stop" >&2; return 4; fi` | `(( ))` computes an arithmetic expression. A result other than 0 counts as true. When a stop time is set (`STOP_EPOCH` is not 0) and the current time in seconds (`date -u +%s`) has reached it, the function prints that `STOP_AT` is reached and returns 4. The shell starts `date` in every call, also with `STOP_AT=none`: it fills in `$( )` before it computes the expression. |
| 27 | `  return 0` | No stop reason exists: the function returns 0. |
| 28 | `}` | Ends the function `why_stop`. |
| 29 | `check_marker() { local rc=0; why_stop \|\| rc=$?; if (( rc )); then stop_child; exit $rc; fi; }` | Defines `check_marker`. It calls `why_stop` and keeps the return value in the local variable `rc` (`$?` is the status of the last command). When the value is not 0, the function ends a running benchmark with `stop_child` and ends the script with that value as the exit status: 3, 5 or 4. So the function tests all three stop reasons, not only the marker file. |
| 30 | `check_deadline() { if (( STOP_EPOCH && $(date -u +%s) + MARGIN >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT is less than $MARGIN s away: stop" >&2; exit 4; fi; }` | Defines `check_deadline`. When a stop time is set and the current time plus `MARGIN` seconds reaches it, the script prints that `STOP_AT` is less than `MARGIN` s away, and ends with exit status 4. The message says less than, but the test also stops at exactly `MARGIN` seconds. So a process starts only when more than `MARGIN` seconds are left. |
| 31 | `trap 'echo "interrupted: stopping the benchmark" >&2; stop_child; exit 130' INT TERM HUP` | `trap` sets what the script does when it gets one of the signals INT (Ctrl-C), TERM (termination) or HUP (the connection was closed). It prints `interrupted: stopping the benchmark` to the error output, ends a running benchmark with `stop_child`, and ends the script with exit status 130. This path writes no `-- killed` line to the csv file. The handoff note says that every stop writes such a line when a benchmark runs. For an interruption the code does not do that. |
| 32 | `check_marker; check_deadline` | First test of the stop reasons (`check_marker`) and of the distance to `STOP_AT` (`check_deadline`). The script has written no file at this point. |

### Folder of the script, check of the two binaries, step list, result folder (lines 33 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 33 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC`: the full path of the folder that holds this script. `dirname "$0"` gives the folder part of the path of the script. Inside the command substitution `$( )`, `cd` goes to that folder and `pwd` prints its full path. The script takes the two binaries from this folder. |
| 34 | `for b in bw_old bw_new; do [[ -x $SRC/$b ]] \|\| { echo "missing $SRC/$b" >&2; exit 2; }; done` | Tests that both binaries exist and may be executed (`-x`). When one is missing, the script prints `missing` with its path to the error output and ends with exit status 2. |
| 35 | `# the binaries of the run of 2026-11-13 (results/kernels-20261113T181222Z/probe.txt); stop if they are others` | Comment: the two checksums below belong to the binaries of the run of 2026-11-13. By the comment they come from the file `probe.txt` of the result folder `kernels-20261113T181222Z`. That file lists both values [Ref2]. The script stops when the binaries are other ones. |
| 36 | `(cd "$SRC" && sha256sum -c --quiet - <<'SUMS'` | Checksum check of the two binaries. The parentheses run the commands in a subshell, so the working folder of the script does not change. `sha256sum -c -` reads a checksum list from its input. It computes the sha256 of every file that the list names and compares it with the value in the list. `--quiet` prints a line only for a file that fails. `<<'SUMS'` gives the text of lines 37 to 38 as the input: all lines up to the line `SUMS`. The quotes around `SUMS` keep the shell from changing that text. |
| 37 | `e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old` | Line of the checksum list: the sha256 that `bw_old` must have. `bw_old` is the benchmark built from the old source `bandwidth.orig.c`. It holds the old read kernel. |
| 38 | `fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new` | Line of the checksum list: the sha256 that `bw_new` must have. `bw_new` is the benchmark built from the new source `bandwidth.c`. It holds the new read kernel. |
| 39 | `SUMS` | Ends the checksum list that began after line 36. |
| 40 | `) \|\| { echo "bw_old or bw_new is not the binary of 2026-11-13: stop (see handoff.md, Files)" >&2; exit 2; }` | Ends the subshell of line 36. When a checksum differs or a file cannot be read, the script prints `bw_old or bw_new is not the binary of 2026-11-13: stop`, with a pointer to the section `Files` of the handoff note, and ends with exit status 2. |
| 41 | `STEPS=${*:-A1 A2 A3 A4 A5 A6 A7}` | `STEPS`: the list of the steps to run. `$*` is the text of all arguments, joined with spaces. When the call has no argument, the list is `A1 A2 A3 A4 A5 A6 A7`. This line does not check the names. A wrong name is found only when the loop of line 85 reaches it (line 119). |
| 42 | `OUT=$HOME/cache-perf/results/partA-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder. Its name is `partA-` plus the UTC time of this moment (`date -u`), written as date, `T`, time, `Z`. It lies below `$HOME/cache-perf/results`. Each call of the script makes its own result folder. Part A of 2026-11-13 has two result folders. The first line of the file `env.txt` of each folder names the steps of its call [Ref1]. |
| 43 | `mkdir -p "$OUT"` | `mkdir -p` creates the result folder, with its parent folders when they are missing. |
| 44 | `echo "result folder: $OUT"` | Prints `result folder:` and the path to the standard output. So the log of the caller names the folder from the start of the run. |

### The file `env.txt`: state of the machine at the start (lines 45 to 53)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `{` | Opens a group of commands. Line 52 closes the group and writes the output of lines 46 to 51 to the new file `env.txt`. |
| 46 | `  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who \| wc -l) steps=$STEPS"` | First line of `env.txt`: the host name, the UTC date and time (`%FT%TZ` prints the date, the letter `T`, the time and the letter `Z`), the whole content of `/proc/loadavg`, the number of logins and the list of the steps. `/proc/loadavg` holds five fields: the load averages over 1, 5 and 15 minutes, then the tasks that are runnable now and the number of all tasks, then the newest process id [Ref4]. `who` prints one line per login, and `wc -l` counts the lines. |
| 47 | `  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Line of `env.txt`: the two system settings for transparent huge pages. `enabled` says for which memory Linux may use pages of 2 MiB. `defrag` says how hard Linux tries to make such a page free when none is ready [Ref3]. In each value the word in square brackets is the active one. |
| 48 | `  echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree\|MemAvailable' /proc/meminfo \| tr -s ' ' \| tr '\n' ' ')"` | Line of `env.txt`: the seconds that have passed after the boot (`cut -d' ' -f1` splits `/proc/uptime` at spaces and keeps the first field), then the free memory and the available memory. `grep -E` keeps the lines of `/proc/meminfo` that hold `MemFree` or `MemAvailable`. `tr -s ' '` reduces each run of spaces to one space. The second `tr` turns each line end into a space, so both values stand on one line. The values are in kB. |
| 49 | `  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6` | Writes a title line, then the busiest processes. `ps -eo pcpu,user,comm --sort=-pcpu` lists all processes with their `pcpu` value, their user and their command name, highest value first. `head -6` keeps the title line of `ps` and 5 processes. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. |
| 50 | `  echo "## sha256:"; (cd "$SRC" && sha256sum bw_old bw_new run_partA.sh)` | Writes a title line, then the sha256 of the two binaries and of this script. So `env.txt` records which three files ran. |
| 51 | `  echo "## vmstat thp:"; grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat` | Writes a title line, then three counters of Linux from the file `/proc/vmstat`. They count for the whole system, from the boot on. `thp_fault_alloc` counts the pages of 2 MiB that Linux gave at a page fault. A page fault is an access to memory that has no page yet. `thp_fault_fallback` counts the page faults at which no 2 MiB page could be given, so Linux used small pages. `thp_collapse_alloc` counts the pages of 2 MiB that Linux made later by joining small pages [Ref3]. Line 122 writes the same counters again at the end. |
| 52 | `} > "$OUT/env.txt"` | Closes the group of line 45. `>` writes the output of all its commands to the new file `env.txt` in the result folder. |

### Function `settle`: the wait for a quiet system (lines 54 to 57)

| Line | Source | Explanation |
|---:|---|---|
| 54 | `# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.` | Comment: the function `settle` waits until at most 2 tasks are runnable, for at most 20 s. The number is the part before the slash in the fourth field of the file `/proc/loadavg`. The script is itself one of these tasks while it reads the file. |
| 55 | `# The field is read with the shell builtin, so the check itself starts no process.` | Continues the comment: the shell reads the field with its own command `read`. So the reading starts no process. The call of `check_marker` in the same turn does start one `date` process (line 26). That process has ended before the field is read. |
| 56 | `# The marker and the stop file are checked in every turn. The wait is returned in WAITED.` | Continues the comment: every turn of the wait tests the marker file and the stop file. The function gives the waited time in the variable `WAITED`. The code tests the time `STOP_AT` in the same place (line 26). |
| 57 | `settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 \|\| t >= 20 )) && break; sleep 2 & wait $! \|\| true; t=$((t+2)); done; WAITED=$t; }` | Defines `settle`, the wait for a quiet system before a launch. The loop has no end condition of its own (`while :`). Each turn first calls `check_marker`. Then `read` takes the fourth field of `/proc/loadavg`, for example `2/1400`, into `r`. `${r%/*}` cuts the slash and the text after it. The rest is the number of tasks that are runnable now. The loop ends when that number is 2 or less, or when 20 s have passed. If not, the script waits 2 s and adds 2 to `t`. `sleep 2 & wait $!` runs the sleep in the background and waits for it. A signal then ends the wait at once, and the trap of line 31 runs. `WAITED` gets the waited time: 0 to 20 s, in steps of 2 s. After 20 s the script goes on without a message. |

### Function `one`: one benchmark process (lines 58 to 77)

| Line | Source | Explanation |
|---:|---|---|
| 58 | `# one <csv> <tag> <binary> <benchmark options...>: one process, with a header line.` | Comment: the function `one` runs one benchmark process. Its arguments are the name of the csv file, the tag of the process, the binary and the options of the benchmark. It writes a header line before the output of the process. |
| 59 | `one() {` | Starts the function `one`. |
| 60 | `  local csv=$1 tag=$2 bin=$3; shift 3` | Takes the first three arguments into the local variables `csv`, `tag` and `bin`. `shift 3` drops them. The arguments that are left (`$@`) are the options of the benchmark. |
| 61 | `  check_marker; check_deadline` | First test before the launch: the three stop reasons (`check_marker`), then the distance to `STOP_AT` (`check_deadline`). |
| 62 | `  settle                                  # checks the marker in every turn` | Waits for a quiet system (`settle`): until at most 2 tasks are runnable, for at most 20 s. Each turn of the wait tests the stop reasons again. The script has no fixed pause before a launch. |
| 63 | `  # evidence for the load of this launch: users logged in and the 5 busiest processes` | Comment: the next line records the load of the machine at this launch: the number of logins and the 5 processes that use the most CPU time. |
| 64 | `  { echo "== $csv $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6; } >> "$OUT/launches.txt"` | Appends the load record of this launch to `launches.txt` in the result folder. Its first line starts with `==`. It holds the name of the csv file, the tag, the UTC time (`date -u +%T` prints hours, minutes and seconds), the first four fields of `/proc/loadavg` (`cut -d' ' -f1-4`) and the number of logins. Then come 6 lines of `ps`: a title line and the 5 processes with the highest `pcpu` value (line 49). The braces group the commands, and `>>` appends their output to the file. |
| 65 | `  check_marker; check_deadline            # again, directly before the launch` | Second test, directly before the launch: the stop reasons and the distance to `STOP_AT` again. The wait and the load record took time. |
| 66 | `  echo "-- step ${csv%.csv} tag $tag binary $bin waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"` | Appends the header line of the process to the csv file of the step. The line starts with `-- step`. It holds the step name (`${csv%.csv}` cuts the ending `.csv`), the tag, the binary, the seconds that `settle` waited (`waited_s`), the first four fields of `/proc/loadavg`, the number of logins, the UTC time, and after the word `args` all options of the benchmark (`$*`). This is the last reading of the machine state before the process starts. |
| 67 | `  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears` | Comment: the benchmark runs in its own process group. While it runs, the script tests the marker file and the stop file once per second. When one of them appears, the script ends the whole group. The code tests the time `STOP_AT` in the same place. |
| 68 | `  setsid "$SRC/$bin" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!` | Starts the benchmark. `setsid` runs the binary with the options (`"$@"`) in a new session and a new process group. So one signal to the group reaches the whole benchmark. The standard output of the benchmark is appended to the csv file of the step. Its error output is appended to `stderr.txt` (`2>>`). `&` runs it in the background, and the script goes on. `CHILD` gets its process id (`$!`). The script measures no time. All timing happens inside the benchmark. |
| 69 | `  local rc=0` | `rc`: the stop reason, or later the exit status of the benchmark. 0 means none. |
| 70 | `  while kill -0 "$CHILD" 2>/dev/null; do` | Starts the loop that waits for the benchmark. `kill -0` sends no signal. It only tests whether the process still exists. The loop runs while it exists. |
| 71 | `    why_stop \|\| rc=$?` | Once per turn: tests the three stop reasons and keeps the return value in `rc`. |
| 72 | `    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi` | When a stop reason exists: the script appends the line `-- killed tag <tag> status <rc> utc <time>` to the csv file, ends the benchmark with `stop_child`, and ends with the exit status 3, 5 or 4. |
| 73 | `    sleep 1 & wait $! \|\| true` | Waits 1 s, in the form that a signal can end at once. So the script tests the stop reasons once per second, and it sees the end of the benchmark up to about 1 s late. Each turn of this loop starts one `date` process (line 26) and one `sleep` process on the CPUs 0 to 119, while the benchmark measures. |
| 74 | `  done` | Ends the loop of line 70. |
| 75 | `  wait "$CHILD" \|\| rc=$?; CHILD=""` | The benchmark has ended. `wait` returns its exit status. A status other than 0 goes to `rc`. `CHILD` is emptied. |
| 76 | `  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi` | When the benchmark ended with a status other than 0: the script appends the line `-- failed tag <tag> exit <rc>` to the csv file, prints `benchmark failed` with the tag and the status to the error output, and ends with exit status 1. The next process does not start. |
| 77 | `}` | Ends the function `one`. |

### Helper functions and lists: CPU list, binary and kernel option of a kernel name (lines 78 to 84)

| Line | Source | Explanation |
|---:|---|---|
| 78 | `# a threads on mesh 0 (CPUs 0..a-1), b threads on mesh 1 (CPUs 64..64+b-1): same rule as bench/run_followup3.sh` | Comment: the rule for a CPU list. `a` threads go to mesh 0, on the CPUs 0 to `a-1`. `b` threads go to mesh 1, on the CPUs 64 to `64+b-1`. By the comment the older script `run_followup3.sh` uses the same rule. |
| 79 | `cpulist() { local a=$1 b=$2 l=""; (( a > 0 )) && l="0-$((a-1))"; (( b > 0 )) && l="${l:+$l,}64-$((64+b-1))"; echo "$l"; }` | Defines `cpulist`. It prints the CPU list for `a` threads on mesh 0 and `b` threads on mesh 1. With `a` above 0 the list starts with the range `0` to `a-1`. With `b` above 0 it gets the range `64` to `64+b-1`. `${l:+$l,}` puts a comma between the two ranges only when the first range exists. Examples: `cpulist 64 56` prints `0-63,64-119`, `cpulist 64 0` prints `0-63`, and `cpulist 32 32` prints `0-31,64-95`. |
| 80 | `bin_of() { case $1 in read_old\|write_old) echo bw_old;; *) echo bw_new;; esac; }   # old C kernels from bw_old, all others from bw_new` | Defines `bin_of`. It prints the binary for a kernel name: `bw_old` for `read_old` and `write_old`, and `bw_new` for every other name. By the comment the old C kernels come from `bw_old` and all others from `bw_new`. So the two hand-written kernels `asmread` and `asmwrite` always come from `bw_new`. |
| 81 | `ker_of() { case $1 in read_old\|read_new) echo read;; write_old\|write_new) echo write;; *) echo "$1";; esac; }` | Defines `ker_of`. It prints the value of the benchmark option `--kernel` for a kernel name: `read` for `read_old` and `read_new`, `write` for `write_old` and `write_new`, and the name itself for every other name (`asmread`, `asmwrite`). Both binaries call their C read kernel `read`. So the binary decides whether the old or the new kernel runs. |
| 82 | `K6="read_old read_new asmread write_old write_new asmwrite"; K6R="asmwrite write_new write_old asmread read_new read_old"` | `K6`: the six kernel names in the order of round 1: old read, new read, `asmread`, old write, new write, `asmwrite`. `K6R`: the same names in the reverse order, for round 2. |
| 83 | `ALL=(--threads 120 --cpus "$(cpulist 64 56)" --bytes 256M --per-thread)` | `ALL`: the options of every process with 120 threads. `--threads 120`: 120 threads. `--cpus 0-63,64-119` (from `cpulist 64 56`): the benchmark pins thread number i to the i-th CPU of this list, so 64 threads run on mesh 0 and 56 on mesh 1. `--bytes 256M`: each thread allocates its own buffer of 256 MiB (268435456 bytes). `--per-thread`: the benchmark also prints one `thread` line per thread and repetition, with the CPU and the rate of that thread. |

### Steps A1, A2 and A3: 120 threads (lines 85 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 85 | `for s in $STEPS; do case $s in` | Starts the loop over the step names, in the order of the call. `case` compares the name `s` with the patterns `A1)` to `A7)` that follow. |
| 86 | `A1) # default 0.5 s interval, per-thread rows, 2 rounds, round 2 in reversed order` | Step A1. Comment: the six kernels with the default interval of 0.5 s and with per-thread rows, in 2 rounds. Round 2 runs the kernels in the reversed order. |
| 87 | `  for round in 1 2; do [[ $round == 1 ]] && L=$K6 \|\| L=$K6R` | Loop over the rounds 1 and 2. `L` is the kernel list of the round: `K6` in round 1 and `K6R` in round 2. |
| 88 | `    for k in $L; do one A1.csv "$k-r$round" "$(bin_of $k)" "${ALL[@]}" --kernel "$(ker_of $k)" --reps 3 --min-ms 500; done; done ;;` | For each kernel of the round: one process (`one`). Output file `A1.csv`. Tag: the kernel name, `-r` and the round, for example `read_old-r1`. The binary comes from `bin_of` and the kernel option from `ker_of`. Options: those of `ALL` (line 83), then `--reps 3` (3 timed repetitions) and `--min-ms 500` (each repetition lasts at least 500 ms). So A1 starts 12 processes: 6 kernels in 2 rounds. `;;` ends the step. |
| 89 | `A2) # long interval: 6 s for read kernels, 15 s for write kernels` | Step A2. Comment: the same six kernels with a long interval: 6 s for the read kernels and 15 s for the write kernels. |
| 90 | `  for round in 1 2; do [[ $round == 1 ]] && L=$K6 \|\| L=$K6R` | Loop over the rounds 1 and 2, with the kernel list of the round as in line 87. |
| 91 | `    for k in $L; do case $k in *read*) ms=6000;; *) ms=15000;; esac` | For each kernel of the round: `ms` is 6000 when the kernel name holds the text `read`. It is 15000 for the other names, which are the three write kernels. |
| 92 | `      one A2.csv "$k-r$round" "$(bin_of $k)" "${ALL[@]}" --kernel "$(ker_of $k)" --reps 3 --min-ms $ms; done; done ;;` | One process per kernel and round, as in A1, with the output file `A2.csv` and with `--min-ms` set to `ms`. So each of the 3 repetitions lasts at least 6 s for a read kernel and at least 15 s for a write kernel. A2 starts 12 processes. |
| 93 | `A3) avail=$(awk '/^MemAvailable:/{print int($2/1048576)}' /proc/meminfo)   # two buffers of 256 MiB for 120 threads need 60 GiB` | Step A3. `avail`: the available memory in GiB. `awk` takes the line of `/proc/meminfo` that starts with `MemAvailable:`. It divides the second field, a value in kB, by 1048576 and drops the fraction. By the comment two buffers of 256 MiB for each of 120 threads need 60 GiB. |
| 94 | `  if (( avail < 70 )); then echo "A3 skipped: MemAvailable is $avail GiB, below 70 GiB" \| tee -a "$OUT/env.txt" >&2; continue; fi` | Memory check. When less than 70 GiB are available, the script skips step A3. `tee -a` appends the message `A3 skipped: MemAvailable is <avail> GiB, below 70 GiB` to `env.txt`, and `>&2` sends the same message to the error output. `continue` goes to the next step. The skip does not change the exit status of the script. |
| 95 | `  # old read with one buffer per thread (--kernel read) and with two (--kernel all: also times write and copy; compare the read rows only)` | Comment: the old read kernel with one buffer per thread (`--kernel read`) and with two buffers (`--kernel all`). With `all` the benchmark also times its write kernel and its copy kernel, and each thread allocates a second buffer for the copy. By the comment only the read rows are to be compared. |
| 96 | `  for ms in 500 6000; do for i in 1 2 3; do` | Two loops: the interval `ms` (500 ms, then 6000 ms) and the process number `i` (1 to 3). |
| 97 | `      one A3.csv "onebuf-ms$ms-$i" bw_old "${ALL[@]}" --kernel read --reps 3 --min-ms $ms` | One process of `bw_old` with one buffer per thread: `--kernel read` times the old read kernel only. Output file `A3.csv`, tag for example `onebuf-ms500-1`. Options: those of `ALL`, then 3 repetitions of at least `ms` milliseconds each. |
| 98 | `      one A3.csv "twobuf-ms$ms-$i" bw_old "${ALL[@]}" --kernel all  --reps 3 --min-ms $ms` | One process of `bw_old` with two buffers per thread: `--kernel all` times read, then write, then copy, each with 3 repetitions of at least `ms` milliseconds. Tag for example `twobuf-ms500-1`. The two kinds of process alternate. A3 starts 12 processes: 3 of each kind for each of the two intervals. With 6000 ms the timed intervals of one such process sum to at least 54 s (3 kernels x 3 repetitions x 6 s). |
| 99 | `  done; done ;;` | Ends the two loops of line 96 and the step A3. |

### Steps A4, A5 and A6 (lines 100 to 113)

| Line | Source | Explanation |
|---:|---|---|
| 100 | `A4) # threads per mesh: 64+b and a+a, old read and asm read, 6 s interval` | Step A4. Comment: the thread count per mesh varies. The counts are 64 threads on mesh 0 plus `b` threads on mesh 1, and `a` threads on each mesh. The kernels are the old read kernel and `asmread`, with an interval of 6 s. |
| 101 | `  for ab in 64,0 64,16 64,32 64,40 64,48 64,52 64,56 32,32 40,40 48,48 56,56; do a=${ab%,*}; b=${ab#*,}` | Loop over 11 thread counts, each written as `a,b`. `${ab%,*}` keeps the part before the comma: the threads on mesh 0. `${ab#*,}` keeps the part after it: the threads on mesh 1. Seven counts have 64 threads on mesh 0 and 0, 16, 32, 40, 48, 52 or 56 threads on mesh 1. Four counts have 32, 40, 48 or 56 threads on each mesh. |
| 102 | `    for k in read_old asmread; do` | Loop over the two kernels: the old read kernel (`read_old`, from `bw_old`) and `asmread` (from `bw_new`). |
| 103 | `      one A4.csv "$k-$a+$b" "$(bin_of $k)" --threads $((a+b)) --cpus "$(cpulist $a $b)" --bytes 256M --per-thread --kernel "$(ker_of $k)" --reps 2 --min-ms 6000` | One process per count and kernel. Output file `A4.csv`, tag for example `read_old-64+16`. `--threads` is the sum `a+b`, and `--cpus` is the list from `cpulist` (line 79). Each thread has a buffer of 256 MiB. The benchmark prints the per-thread lines and times 2 repetitions of at least 6000 ms each. A4 starts 22 processes. |
| 104 | `    done; done ;;` | Ends the two loops of lines 101 to 102 and the step A4. |
| 105 | `A5) # one thread, 8 MiB, 30 intervals of 0.3 s, then at once a second process on the same CPU` | Step A5. Comment: one thread with a buffer of 8 MiB and 30 intervals of 0.3 s, then at once a second process on the same CPU. The code does not force the second process to start at once: `one` first waits for a quiet system, for up to 20 s (line 62). The header line of the second process gives that wait as `waited_s`. |
| 106 | `  for cpu in 2 41; do for i in 1 2; do` | Two loops: the CPU (2, then 41) and the process number `i` (1, then 2). |
| 107 | `      one A5.csv "cpu$cpu-proc$i" bw_new --threads 1 --cpus $cpu --bytes 8M --kernel asmread --reps 30 --min-ms 300` | One process of `bw_new`: one thread, pinned to the CPU `cpu`, a buffer of 8 MiB (8388608 bytes), the kernel `asmread`, 30 repetitions of at least 300 ms each. Output file `A5.csv`, tag for example `cpu2-proc1`. The call has no `--per-thread`: with one thread the total of a repetition is the rate of the thread. A5 starts 4 processes: 2 on CPU 2, then 2 on CPU 41. |
| 108 | `  done; done ;;` | Ends the two loops of line 106 and the step A5. |
| 109 | `A6) # one thread, 8 MiB, with and without 2 MiB pages, alternating` | Step A6. Comment: one thread with a buffer of 8 MiB, with and without pages of 2 MiB, alternating. |
| 110 | `  for i in 1 2 3 4 5 6 7 8; do` | Loop over the pair number `i`, from 1 to 8. |
| 111 | `      one A6.csv "thp-$i"   bw_new --threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500` | One process with pages of 2 MiB allowed: `bw_new`, one thread on CPU 2, a buffer of 8 MiB, the kernel `asmread`, 3 repetitions of at least 500 ms each. Output file `A6.csv`, tag `thp-` plus `i`. Without `--no-thp` the benchmark asks Linux for transparent huge pages for its buffer (the call `madvise` with `MADV_HUGEPAGE`). It does not check how much of the buffer got such pages. |
| 112 | `      one A6.csv "nothp-$i" bw_new --threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500 --no-thp` | The same process with `--no-thp`, tag `nothp-` plus `i`. With this option the benchmark asks Linux to use no huge pages for the buffer (`MADV_NOHUGEPAGE`). So the buffer lies on the small standard pages. |
| 113 | `  done ;;` | Ends the loop of line 110 and the step A6. A6 starts 16 processes: 8 of each kind, alternating. |

### Step A7, unknown step names, end of the run (lines 114 to 123)

| Line | Source | Explanation |
|---:|---|---|
| 114 | `A7) check_marker; check_deadline` | Step A7. It starts no benchmark. It reads system information that the later parts need. First it tests the stop reasons and the distance to `STOP_AT`. |
| 115 | `  { echo "## sve_default_vector_length (bytes):"; cat /proc/sys/abi/sve_default_vector_length 2>&1 \|\| true; } > "$OUT/A7-sve.txt"` | Writes the file `A7-sve.txt`: a title line, then the content of `/proc/sys/abi/sve_default_vector_length`. That file holds the default vector length for SVE, the scalable vector instructions of Arm. It is the size of one SVE vector register in bytes, and a new program gets it when it starts [Ref5]. `2>&1` sends an error message of `cat` into the file too. `\|\| true` lets the script go on when the file cannot be read. |
| 116 | `  perf list > "$OUT/A7-perf-list.txt" 2>&1 \|\| echo "perf list failed" >> "$OUT/A7-perf-list.txt"` | Writes the output of `perf list` to `A7-perf-list.txt`, with its error messages (`2>&1`). `perf list` prints the names of the events that the Linux tool `perf` can count. When the command fails, the line `perf list failed` is appended to the file, and the script goes on. |
| 117 | `  ls /sys/bus/event_source/devices/ > "$OUT/A7-pmu-devices.txt" 2>&1 \|\| true` | Writes the names of the counter devices to `A7-pmu-devices.txt`. `ls` lists the folder `/sys/bus/event_source/devices/`, which holds one entry per counter device. A failure does not stop the script. |
| 118 | `  for d in /sys/bus/event_source/devices/armv8*; do echo "== $d type=$(cat "$d/type" 2>/dev/null)"; grep -H . "$d"/events/* 2>/dev/null; done > "$OUT/A7-core-events.txt" \|\| true ;;` | Writes `A7-core-events.txt`. The loop runs over every counter device whose name starts with `armv8`. These are the counter devices of the cores. For each device it writes one line that starts with `==`, with the path of the device and its type number (the content of its file `type`). Then `grep -H .` prints every non-empty line of each file in its folder `events`, with the file path and a colon before the line. Each such line gives one event name and its code, in the form `<path>/events/<name>:event=<code>`. Part C of the plan needs the type number and the codes to open the counters. `\|\| true` lets the script go on after a failure. `;;` ends the step A7. |
| 119 | `*) echo "unknown step $s" >&2; exit 2 ;;` | Every other step name: the script prints `unknown step` with the name to the error output and ends with exit status 2. The steps before it in the list have run by then. No end line is written to `env.txt`. |
| 120 | `esac; done` | Ends the `case` and the loop of line 85. |
| 121 | `echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"` | Appends the end line to `env.txt`: the UTC time and the content of `/proc/loadavg` after the last step. The script reaches this line only when no stop occurred. So a missing end line shows a run that stopped early. |
| 122 | `grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt"` | Appends the three counters of line 51 again. The difference to the first reading is the number of these events in the whole system during the run. The counters are not limited to our processes. |
| 123 | `echo "$OUT"` | Prints the path of the result folder as the last line of the standard output. The exit status of the script is then 0. |

## References

- [Ref1] the files `env.txt` of the result folders `partA-20261113T204939Z` and `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. Their first lines end with `steps=A7 A5 A6` and with `steps=A1 A2 A3 A4`. In each file the list after the line `## sha256:` gives `0f496ca60a1127880ae48ef14a63d28205dce3d9d8bc9edb7feefbf28f84d167` for `run_partA.sh`. The file in the code folder has the same sha256.
- [Ref2] the file `probe.txt` of the result folder `kernels-20261113T181222Z` in the same test folder. The list after its line `## sha256:` gives the two values of lines 37 to 38 for `bw_old` and `bw_new`.
- [Ref3] external source: Linux kernel documentation, "Transparent Hugepage Support", the settings `enabled` and `defrag` and the counters `thp_fault_alloc`, `thp_fault_fallback` and `thp_collapse_alloc`: https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html
- [Ref4] external source: Linux manual page `proc_loadavg(5)`, the five fields of `/proc/loadavg`: https://man7.org/linux/man-pages/man5/proc_loadavg.5.html
- [Ref5] external source: Linux kernel documentation, "Scalable Vector Extension support for AArch64 Linux", the file `/proc/sys/abi/sve_default_vector_length`: https://www.kernel.org/doc/html/latest/arch/arm64/sve.html
