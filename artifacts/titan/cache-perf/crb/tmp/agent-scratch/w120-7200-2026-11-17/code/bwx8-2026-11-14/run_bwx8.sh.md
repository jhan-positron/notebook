# `run_bwx8.sh` explained, line by line

- Source file: `bwx8-2026-11-14/run_bwx8.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 201 lines, 14337 bytes).
- sha256 of the source when this page was built: `2d326dd3f095389614548bbb1f7931c3f1f7a0fd3978aa392973550a278b9828`.

## Short version: purpose

`run_bwx8.sh` runs the steps of round 1 on CRB: for each step it starts the processes of a schedule file one at a time with the runner `bwx8`. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1**: the first set of tests of the investigation into the buffer size of 8 MiB. This script runs its steps.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **`bwx8`**: the runner version that round 1 uses. The script starts the binary that lies beside it.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **Visit**: one login to CRB that starts one script.
- **Step**: one batch of processes of a round, for example `S2`. One schedule file lists its processes.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **Generator**: the program `schedule8.py`. It writes the schedules and the plan files of round 1.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Window**: one timed period of one kernel inside a trial.
- **Condition**: the label of a trial in its plan file. It names what the trial measures, for example the kernel and the buffer size.
- **Trial mode, interval mode**: the two modes of a runner. In the trial mode (`--trial`) one process runs the trials of a plan file. In the interval mode (`--seq`) it times a sequence of kernels and has no plan file.
- **`--rounds`**: an option of the interval mode. It gives the number of times that the runner repeats its sequence of kernels. These rounds are not the rounds of the investigation.
- **Nominal kernel work**: the sum of the planned durations of all timed parts of a process or of a step. The real run time is longer.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. A process starts only when this time is more than `MARGIN` seconds away, and a process that still runs at this time is ended. The value `none` sets no limit.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s when the variable is not set or is empty. `MARGIN` is the nominal work of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Build record**: the file `build.txt`. The build script of the runner writes it. This script copies it into every result folder.
- **Test variable**: one of the four variables `BWX8_MARKER`, `BWX8_STOPFILE`, `BWX8_BIN` and `BWX8_RESULTS`. They give other paths for local tests with a dummy binary.
- **Dummy binary**: a stand-in program for the benchmark. The local tests of this script use one.
- **Dry run**: a call with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file of a step is `<STEP>.csv` in the result folder. Before the output of each process the script writes a header line into it. That line starts with `-- step`.
- **Load record**: the lines that the script appends to the file `launches.txt` before a launch: the first four fields of `/proc/loadavg`, the number of logins and the 5 processes with the highest `pcpu` value of `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the part of a core that holds the hardware counters.
- **Counter device**: the hardware counters of the CPU cores, as Linux lists them. Linux gives the device a type number. The variable `BWX_PMU_TYPE` carries that number.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Process group**: a set of processes that one signal can reach together.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The header comment gives the usage, the settings and the exit statuses (lines 1 to 26).
2. Limit the script and everything that it starts to the CPUs 0 to 119 (lines 27 to 28).
3. Read the options and the step names, and check `SESSION` (lines 29 to 42).
4. Print a warning for each test variable that is set and not empty (lines 44 to 46).
5. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption (lines 49 to 68).
6. Set the path of the binary `bwx8` and the place of the result folders, and make the folder of the script the working folder (lines 96 to 99).
7. For session 2, refuse a start earlier than 3 hours after `SESSION1_END` (lines 102 to 110).
8. For each step, check the counter settings when the step is `CS`, `CM` or `C4`, and check the schedule file (lines 111 to 118).
9. In a real run, check the binary, its `build.txt` and its digest. Then test the stop reasons once (lines 119 to 126).
10. For each step, read the schedule with `load_step`, compute the nominal work and `MARGIN`, and print the summary (lines 160 to 169).
11. In a dry run, print one command line per process and go to the next step (lines 170 to 176).
12. In a real run, test the stop reasons and the distance to `STOP_AT`, make the result folder and write `schedule.tsv`, `build.txt` and `env.txt` (lines 177 to 192).
13. Run the processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line and starts the runner. Then it tests the stop reasons once per second until the runner ends (lines 193 to 197).
14. Append the end line to `env.txt` and print the path of the result folder (lines 198 to 200).

## Behavior a reader must know

- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. The rule of line 67 is: stop when the current time plus `MARGIN` is at or after `STOP_AT`. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing setting or file, a wrong digest, or a session 2 that would start too early: status 2.
- A seventh thing stops the run without a message of the script. With `set -e` (line 27) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder or `cp` cannot write its copy (lines 179 to 182). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- Most checks with status 2 run before the first process of the call (lines 30 to 41, lines 51 to 52, lines 102 to 124). Two run later, when their step is reached and before its first process: a defect in a row of the schedule or a missing plan file (lines 135 to 155), and a `--from` value past the last `idx` (line 162). So in a call with several steps such a defect of a later step stops the run after the earlier steps have run.
- The steps run in the order in which the call names them (line 160). On CRB each of the two sessions of round 1 was one call with the steps `B6W`, `S2` and `S4` [Ref1] [Ref2].
- The first three stop reasons are tested in a fixed order: the marker file, then the stop file, then `STOP_AT` (lines 60 to 65). When two of them hold, the first one gives the exit status.
- The first three stop reasons are tested at these places: once before the first step (line 125), once before each result folder is made (line 177), twice before each launch (line 77, line 81), in every turn of the wait for a quiet system (line 72), and once per second while a process runs (line 87).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later (line 56). Before that, the script appends a line that starts with `-- killed` to the output file of the step (line 68, line 88).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message (line 72). There is no fixed pause. The header line of the process records the waited seconds as `waited_s` (line 82).
- For each launch the script records the load in two places. `launches.txt` gets a line with the first four fields of `/proc/loadavg` and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` (line 80). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in `<STEP>.csv` gets the waited seconds, the first four fields of `/proc/loadavg`, the number of logins, the UTC time and the options (line 82).
- The file `env.txt` records the state of the machine at the start of a step and the sha256 of the binary, of this script, of the schedule and of `build.txt` (lines 183 to 192). The sha256 of the plan files is not recorded. The end of the step adds the UTC time, the content of `/proc/loadavg` and three huge page counters (lines 198 to 199).
- A result folder holds these files: `<STEP>.csv` with the header line and the output of every process, `launches.txt`, `env.txt`, `stderr.txt` with the error output of the runner, and the copies `schedule.tsv` and `build.txt`.
- A process that ends with a status other than 0 gets a line that starts with `-- failed` in `<STEP>.csv` (line 92). The script does not test the output of a process. It tests the exit status only.
- The script times nothing. All timing happens inside the runner.
- The script pins no benchmark thread. It only limits itself and everything that it starts to the CPUs 0 to 119 (line 28). A caller that has already set `_PINNED` to a text that is not empty gets no such limit. The schedule row gives the runner its CPU with the option `--cpus`.
- The steps `CS`, `CM` and `C4` need the counter settings `BWX_PMU_TYPE` and `BWX_EVENTS` in the environment, in a dry run too (lines 113 to 115). The script exports them, and the runner reads them from its environment.
- In the schedules of the generator `schedule8.py` only the step `B6W` has rows without a plan file. Its processes run the interval mode, and the branch of lines 139 to 145 computes their nominal work. Every other step has one plan file per process.
- The generator writes the schedules of the steps `BIN` and `CS` only when its option `--select` names kernels and sizes. Without the schedule file the script ends with exit status 2 for such a step (line 117).
- A value of the form `${X:-default}` is the default when the variable `X` is not set or is empty. The script uses this form for `RESERVE` and the four test variables, and in a dry run for `STOP_AT` (line 42).
- A dry run needs `SESSION`, the schedule files and the plan files. For the steps `CS`, `CM` and `C4` it also needs the two counter settings (line 114). It does not test the binary, `build.txt`, the digest, the stop reasons or the 3 hour rule of session 2 (line 102, line 119).
- The script does not test whether a schedule was made with the option `--test-divisor` of the generator, which shortens every duration for local tests. The note `DECISIONS-bwx8.md` lists this check as not done.
- The script never repeats a process. A stopped step is continued with `--from IDX`, in a new result folder.
- The script deletes nothing. At every stop the files that were written before stay.
- The exit status is 0 only when every step of the call ran to its end.
- The text of this file is the text that ran on CRB in round 1 [Ref1].

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/run_bwx8.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (201 lines, 14337 bytes, sha256 `2d326dd3f095389614548bbb1f7931c3f1f7a0fd3978aa392973550a278b9828`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: purpose, steps, `STOP_AT`, session, options, counter settings (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_bwx8.sh - the steps of the design tackle-8mb.md on CRB, one visit per call.` | Comment: the name and the purpose of the file. The script runs the steps of the design on CRB. The design is the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB. One call of the script is one visit to CRB, that is one login. |
| 3 | `# Usage: STOP_AT=<UTC time or "none"> SESSION=<1\|2> run_bwx8.sh [--dry-run] [--from IDX] STEP...` | Comment: the usage. The caller sets two environment variables: `STOP_AT` (a UTC time or the word `none`) and `SESSION` (`1` or `2`). The arguments are the two optional options `--dry-run` and `--from IDX`, and one or more step names. |
| 4 | `#   STEP: B6W S2 S4 P3G P3 S3G S3 BIN CS CM C4   (run in the order given)` | Comment: the 11 step names that the script accepts. The steps run in the order in which the call names them. The note `DECISIONS-bwx8.md` has a table that says what each step holds. |
| 5 | `#   The processes of a step come from sched/s<SESSION>/<STEP>.tsv beside this script (schedule8.py` | Comment: the processes of a step come from the schedule file `sched/s<SESSION>/<STEP>.tsv` in the folder of this script. The generator `schedule8.py` writes that file. |
| 6 | `#   writes it). The script runs them in that order, one at a time. It never repeats a process.` | Continues the comment: the script runs the processes in the order of the schedule, one at a time. It never runs a process a second time. |
| 7 | `#   STOP_AT is required. Example: STOP_AT=2026-11-15T15:00Z (start nothing that could run past this` | Comment: `STOP_AT` must be set. With a time such as `2026-11-15T15:00Z` the script starts nothing that could still run at that time. |
| 8 | `#   time), or STOP_AT=none when no block is announced.` | Continues the comment: `STOP_AT=none` sets no time limit. It is for a visit at which no block is announced. A block is a time window that another user has reserved on CRB. |
| 9 | `#   SESSION is required. SESSION=2 also needs SESSION1_END=<UTC time>, the end of session 1, written` | Comment: `SESSION` must be set. Session 2 repeats the steps of session 1. With `SESSION=2` the caller must also set `SESSION1_END` to the UTC time at which session 1 ended. |
| 10 | `#   as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z (no other form is accepted). The` | Continues the comment: that time must have the form `2026-11-15T03:00Z` or `2026-11-15T03:00:00Z`. The script accepts no other form. |
| 11 | `#   script refuses to start session 2 earlier than 3 hours after that time (status 2).` | Continues the comment: the script does not start session 2 earlier than 3 hours after the end of session 1. It then ends with exit status 2. |
| 12 | `#   --dry-run: prints every command line and the counts of each step. It starts no benchmark, makes` | Comment: with `--dry-run` the script prints the command line of every process and the counts of each step. It starts no benchmark. |
| 13 | `#   no result folder, and needs neither STOP_AT nor SESSION1_END.` | Continues the comment: a dry run makes no result folder. It needs no `STOP_AT` and no `SESSION1_END`. The code still asks for `SESSION` in a dry run (line 41). For the steps `CS`, `CM` and `C4` it also asks for the two counter settings in a dry run (line 114). |
| 14 | `#   --from IDX: continue a stopped step at the process with this idx. Only with one STEP. The value` | Comment: `--from IDX` continues a step that was stopped. The script starts at the process whose `idx` is `IDX`. The `idx` is the number of a process in its schedule, counted from 0. The option is allowed only when the call names one step. |
| 15 | `#   is written to env.txt. The processes go to a new result folder.` | Continues the comment: the script writes the value of `--from` to the file `env.txt`. The processes of the continued step go to a new result folder. |
| 16 | `#   CS CM C4 need BWX_PMU_TYPE (the "type" file of the core PMU) and BWX_EVENTS (NAME=CODE,...).` | Comment: the steps `CS`, `CM` and `C4` need two counter settings in the environment. `BWX_PMU_TYPE` is the type number that Linux gives to the counter device of the cores. Linux shows it in the file `type` of that device. PMU means performance monitoring unit, the part of a core that holds the hardware counters. `BWX_EVENTS` is the list of the counter events, in the form `NAME=CODE,...`. |

### Header comment: optional settings, exit statuses, needs, status (lines 17 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `#   Optional: BWX8_SHA256 (expected digest of bwx8; status 2 if bwx8 differs),` | Comment: the optional variable `BWX8_SHA256`. It holds the digest that the binary `bwx8` must have. A digest is the sha256 checksum of a file. When the binary differs, the script ends with exit status 2. |
| 18 | `#             RESERVE (seconds added to the longest process of a step to give MARGIN, default 90).` | Comment: the optional variable `RESERVE`, 90 s when it is not set or is empty. `MARGIN` is the longest process of a step plus `RESERVE`, in seconds. A process starts only when `STOP_AT` is more than `MARGIN` seconds away (line 67). |
| 19 | `#   For local tests with a dummy binary only: BWX8_MARKER, BWX8_STOPFILE, BWX8_BIN, BWX8_RESULTS.` | Comment: four variables that are for local tests with a dummy binary only. A dummy binary is a stand-in program for the benchmark. `BWX8_MARKER` gives another path for the marker file, `BWX8_STOPFILE` another path for the stop file, `BWX8_BIN` another path for the binary, and `BWX8_RESULTS` another place for the result folders. |
| 20 | `#   The script prints a warning for each one that is set, and env.txt records the four paths in use.` | Continues the comment: the script prints a warning for each of these variables that is set. The file `env.txt` records the four paths that the run used. |
| 21 | `# Exit status: 0 done; 1 a benchmark failed; 2 usage, missing setting, missing file, or session 2` | Comment: the exit statuses. 0: all steps are done. 1: a benchmark process failed. 2: a wrong usage, a missing setting or a missing file. The code gives 2 also for a binary that differs from its digest (line 123), and for a defect in a row of the schedule. |
| 22 | `#   too early; 3 marker file appeared; 4 STOP_AT reached; 5 stop file ~/cache-perf/STOP found;` | Continues the comment: 2 also when session 2 would start too early. 3: the marker file exists. 4: the time `STOP_AT` is reached. 5: the stop file `~/cache-perf/STOP` exists. The code gives 4 also before a launch when `STOP_AT` is `MARGIN` seconds away or less (line 67). |
| 23 | `#   130 interrupted. In every case the files written so far are kept.` | Continues the comment: 130: a signal interrupted the script. In every case the files that were written before the stop are kept. |
| 24 | `# Needs bwx8, build.txt and sched/ in the same folder as this script.` | Comment: the script needs three things in its own folder: the binary `bwx8`, the build record `build.txt` and the schedule folder `sched/`. |
| 25 | `# Uses CPUs 0-119 only, writes only under $HOME/cache-perf/results/bwx8-<step>-s<session>-<UTC>/, no sudo.` | Comment: the script uses the CPUs 0 to 119 only. It writes only into result folders with the name `$HOME/cache-perf/results/bwx8-<step>-s<session>-<UTC>/`. It never uses `sudo`, the command that runs a program as root. |
| 26 | `# Status: written 2026-11-14. Syntax, dry run and stop controls tested with a dummy bwx8. Never run on CRB.` | Comment: the state of the file when it was written, on 2026-11-14. The syntax, the dry run and the stop controls were tested with a dummy `bwx8`, a stand-in program for the benchmark. The words `Never run on CRB` give the state at the time of writing. Later this text ran on CRB: the file `env.txt` of each of the 6 result folders of round 1 records the sha256 of this file [Ref1]. |

### Shell options, CPU limit, arguments and first checks (lines 27 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `set -euo pipefail` | `set -e`: the script stops when a command fails. A command that is tested by `if` or `while`, or that stands before `\|\|` or `&&`, does not stop it. `set -u`: the script stops when it uses a variable that was never set. `set -o pipefail`: a pipeline fails when any of its commands fails, not only the last one. |
| 28 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Limits the script and everything that it starts to the CPUs 0 to 119. `${_PINNED:-}` gives the value of `_PINNED`, or an empty text when the variable is not set. `-z` tests for an empty text. On the first pass the variable is empty. Then `exec` replaces the shell with `taskset -c 0-119`. That tool sets the CPU list and starts this script again (`$0`) with the same arguments (`"$@"`) and with `_PINNED=1` in its environment. On the second pass the variable is set, and the script goes on. When the caller has already set `_PINNED` to a text that is not empty, the script sets no CPU limit. |
| 29 | `DRY=0; FROM=0; STEPS=()` | Start values. `DRY`: 1 in a dry run. `FROM`: the `idx` of the first process to run. `STEPS`: the list of the step names, empty at first. |
| 30 | `while (( $# )); do case $1 in` | Starts the loop over the arguments. `$#` is the number of arguments that are left. The loop runs while it is not 0. `case` compares the first argument (`$1`) with the patterns that follow. |
| 31 | `  --dry-run) DRY=1 ;;` | The option `--dry-run` sets `DRY` to 1. |
| 32 | `  --from) [[ ${2:-} =~ ^[0-9]+$ ]] \|\| { echo "--from needs a process index" >&2; exit 2; }; FROM=$((10#$2)); shift ;;` | The option `--from`. The next argument (`$2`) must hold digits only: the pattern `^[0-9]+$` matches one or more digits and nothing else. If not, the script prints `--from needs a process index` to the error output (`>&2`) and ends with exit status 2. `FROM=$((10#$2))` stores the number. `10#` makes the shell read it as a decimal number, also when it starts with a zero. `shift` drops the option. The `shift` of line 35 then drops its value. |
| 33 | `  B6W\|S2\|S4\|P3G\|P3\|S3G\|S3\|BIN\|CS\|CM\|C4) STEPS+=("$1") ;;` | An argument that is one of the 11 step names is added to the list `STEPS`. The `\|` separates the alternatives of the pattern. |
| 34 | `  *) echo "unknown step or option: $1" >&2; exit 2 ;;` | Every other argument: the script prints `unknown step or option:` with the argument to the error output and ends with exit status 2. |
| 35 | `esac; shift; done` | Ends the `case`. `shift` drops the argument that was handled. `done` ends the loop of line 30. |
| 36 | `(( ${#STEPS[@]} )) \|\| { echo "usage: STOP_AT=<UTC\|none> SESSION=<1\|2> $0 [--dry-run] [--from IDX] STEP...   (see the head of this file)" >&2; exit 2; }` | `${#STEPS[@]}` is the number of step names. When it is 0, the script prints the usage line to the error output and ends with exit status 2. |
| 37 | `for (( i = 0; i < ${#STEPS[@]}; i++ )); do for (( j = 0; j < i; j++ )); do` | Two nested loops compare every step name with every name before it in the list. |
| 38 | `  [[ ${STEPS[i]} != "${STEPS[j]}" ]] \|\| { echo "step ${STEPS[i]} is named twice: stop (the script never repeats a process)" >&2; exit 2; }` | When two names are equal, the script prints that the step is named twice and ends with exit status 2. So one call cannot run a step twice. |
| 39 | `done; done` | Ends the two loops of line 37. |
| 40 | `(( FROM == 0 \|\| ${#STEPS[@]} == 1 )) \|\| { echo "--from needs exactly one step" >&2; exit 2; }` | A `--from` value above 0 is allowed only with exactly one step. If the call names more steps, the script prints `--from needs exactly one step` and ends with exit status 2. |
| 41 | `[[ ${SESSION:-} == 1 \|\| ${SESSION:-} == 2 ]] \|\| { echo "set SESSION to 1 or 2" >&2; exit 2; }` | `SESSION` must be `1` or `2`. If not, the script prints `set SESSION to 1 or 2` and ends with exit status 2. |
| 42 | `(( DRY )) && STOP_AT=${STOP_AT:-none}` | In a dry run only: when `STOP_AT` is not set or is empty, it becomes `none`. So a dry run needs no `STOP_AT`. |
| 44 | `for v in BWX8_MARKER BWX8_STOPFILE BWX8_BIN BWX8_RESULTS; do` | Starts a loop over the names of the four variables that are for local tests only. |
| 45 | `  [[ -z ${!v:-} ]] \|\| echo "warning: $v is set (for local tests only): $v=${!v}" >&2` | `${!v:-}` gives the value of the variable whose name is in `v`. When that value is not empty, the script prints a warning with the name and the value to the error output. The script goes on. |
| 46 | `done` | Ends the loop of line 44. |

### Stop controls: settings, `why_stop`, `check_marker`, `check_deadline`, the trap, `settle` (lines 48 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `# ---- stop controls: copied from run_bwx.sh, behaviour unchanged except the two test settings and the line that the trap writes ----` | Comment: the part from here to line 94 holds the stop controls. By the comment it is a copy from the older script `run_bwx.sh`, the run script of the first runner. The comment names two changes: the two test settings `BWX8_MARKER` and `BWX8_STOPFILE` (lines 49 to 50), and the line that the trap of line 68 writes into the output file. The function `one` of this part also differs from the one of `run_bwx.sh`: it has an argument for the `idx` and none for a binary name, and its header line holds the session and the `idx` in place of the binary name. |
| 49 | `MARKER=${BWX8_MARKER:-/tmp/positron-perf.RUNNING}` | `MARKER`: the path of the marker file. It is `/tmp/positron-perf.RUNNING` unless the test variable `BWX8_MARKER` gives another path. `${X:-default}` gives the value of `X`, or the default when `X` is empty or not set. |
| 50 | `STOPFILE=${BWX8_STOPFILE:-$HOME/cache-perf/STOP}     # ours: "touch ~/cache-perf/STOP" from another login stops this script` | `STOPFILE`: the path of the stop file. It is `$HOME/cache-perf/STOP` unless `BWX8_STOPFILE` gives another path. The stop file is our own stop signal: the command `touch ~/cache-perf/STOP` from another login creates it, and the script then stops (line 62). |
| 51 | `[[ -n ${STOP_AT:-} ]] \|\| { echo "set STOP_AT to a UTC time like 2026-11-15T15:00Z, or to none" >&2; exit 2; }` | `-n` tests for a text that is not empty. When `STOP_AT` is empty or not set, the script prints a message that asks for a UTC time or for `none`, and ends with exit status 2. |
| 52 | `if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) \|\| { echo "bad STOP_AT" >&2; exit 2; }; fi` | `STOP_EPOCH`: the stop time as a number. With `STOP_AT=none` it is 0, which stands for no limit. In every other case `date -u -d "$STOP_AT" +%s` converts the text to a number of seconds, counted from 1970-01-01 00:00 UTC. When `date` cannot read the text, the script prints `bad STOP_AT` and ends with exit status 2. |
| 53 | `RESERVE=${RESERVE:-90}             # seconds: allocation, first touch, page reads and output of one process (est.)` | `RESERVE`: the value that the caller set, or 90 s when the variable is not set or is empty. By the comment it is an estimate of the time that one process needs beside its kernel work: the allocation of the buffer, the first touch, the reads of the page state and the output. |
| 54 | `MARGIN=$RESERVE                    # seconds: set for each step to its longest process plus RESERVE` | `MARGIN`: a number of seconds. A process may start only when `STOP_AT` is more than `MARGIN` seconds away (line 67). It starts as `RESERVE`. The main loop sets it for each step to the longest process of the step plus `RESERVE` (line 163). |
| 55 | `CHILD=""; CUR_CSV=""; CUR_TAG=""  # the running benchmark, its csv file and its tag (set by one)` | `CHILD`: the process id of the running benchmark. It is empty when none runs. `CUR_CSV` and `CUR_TAG`: the output file and the tag of that benchmark. The function `one` sets the three variables. The trap of line 68 reads them. |
| 56 | `stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null \|\| true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null \|\| true; wait "$CHILD" 2>/dev/null \|\| true; CHILD=""; fi; }` | Defines `stop_child`, which ends the running benchmark. The benchmark runs in its own process group (line 84). When `CHILD` is not empty: `kill -- -"$CHILD"` sends the termination signal (TERM) to every process of that group. The minus sign before the id selects the group. `2>/dev/null` discards an error message, for example when the group has ended before. With `\|\| true`, such a failure does not make `set -e` stop the script. After 1 s (`sleep 1`), `kill -9` sends the signal KILL to the group. No process can ignore that signal. `wait` then collects the ended benchmark, and `CHILD` is emptied. |
| 57 | `# why_stop: prints the reason and returns the exit status to use, or returns 0 if nothing asks us to stop.` | Comment: the function `why_stop` prints the reason for a stop and returns the exit status that the script must use. It returns 0 when nothing asks for a stop. |
| 58 | `# It is called in every turn of the wait and every second while a benchmark runs, so STOP_AT itself is` | Continues the comment: the script calls `why_stop` in every turn of the wait before a launch, and once per second while a benchmark runs. |
| 59 | `# enforced on a running benchmark. check_deadline adds the margin before a launch.` | Continues the comment: so the time `STOP_AT` also stops a benchmark that is running. Before a launch the function `check_deadline` asks for more: `STOP_AT` must be more than `MARGIN` seconds away. |
| 60 | `why_stop() {` | Starts the function `why_stop`. It tests three stop reasons in a fixed order: the marker file, the stop file, the time `STOP_AT`. |
| 61 | `  if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; return 3; fi` | `-e` tests whether a file exists. When the marker file exists, the function prints `RUNNING file present: stop` to the error output and returns 3. |
| 62 | `  if [[ -e $STOPFILE ]]; then echo "stop file $STOPFILE present: stop" >&2; return 5; fi` | When the stop file exists, the function prints `stop file`, the path and `present: stop`, and returns 5. |
| 63 | `  if (( STOP_EPOCH && $(date -u +%s) >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT reached: stop" >&2; return 4; fi` | When a stop time is set (`STOP_EPOCH` is not 0) and the current time in seconds (`date -u +%s`) has reached it, the function prints that `STOP_AT` is reached and returns 4. The shell starts one `date` process in every call, also when no stop time is set: it fills in `$( )` before it computes the expression. |
| 64 | `  return 0` | No stop reason exists: the function returns 0. |
| 65 | `}` | Ends the function `why_stop`. |
| 66 | `check_marker() { local rc=0; why_stop \|\| rc=$?; if (( rc )); then stop_child; exit $rc; fi; }` | Defines `check_marker`. It calls `why_stop` and keeps the return value in `rc` (`$?` is the status of the last command). When the value is not 0, the function ends a running benchmark with `stop_child` and ends the script with that value as the exit status: 3, 5 or 4. So the function tests all three stop reasons, not only the marker file. |
| 67 | `check_deadline() { if (( STOP_EPOCH && $(date -u +%s) + MARGIN >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT is less than $MARGIN s away: stop" >&2; exit 4; fi; }` | Defines `check_deadline`, the test of the time that is left before a launch. It does nothing when no stop time is set (`STOP_EPOCH` is 0). If one is set, it adds `MARGIN` seconds to the current time (`date -u +%s`). When the sum is at or after the stop time, the script prints `STOP_AT`, the time, and `is less than`, the value of `MARGIN` and `s away: stop`, and ends with exit status 4. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away. At exactly `MARGIN` seconds the script stops too, although the message says `less than`. |
| 68 | `trap 'echo "interrupted: stopping the benchmark" >&2; if [[ -n $CHILD ]]; then echo "-- killed tag $CUR_TAG status 130 utc $(date -u +%T)" >> "$OUT/$CUR_CSV"; fi; stop_child; exit 130' INT TERM HUP` | `trap` sets what the script does when it gets one of the signals INT (Ctrl-C), TERM (termination) or HUP (the connection was closed). It prints `interrupted: stopping the benchmark`. When a benchmark runs, it appends the line `-- killed tag <tag> status 130 utc <time>` to the output file of the step. Then it ends the benchmark with `stop_child` and ends the script with exit status 130. |
| 69 | `# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.` | Comment: the function `settle` waits until at most 2 tasks are runnable, for at most 20 s. The number is the part before the slash in the fourth field of the file `/proc/loadavg`. |
| 70 | `# The field is read with the shell builtin, so the check itself starts no process.` | Continues the comment: the shell reads the field with its own command `read`. So the reading starts no process. The call of `check_marker` in the same turn does start one `date` process (line 63). That process has ended before the field is read. |
| 71 | `# The marker and the stop file are checked in every turn. The wait is returned in WAITED.` | Continues the comment: every turn of the wait tests the marker file and the stop file. The code tests the time `STOP_AT` in the same turn (line 63). The function gives the waited time in the variable `WAITED`. |
| 72 | `settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 \|\| t >= 20 )) && break; sleep 2 & wait $! \|\| true; t=$((t+2)); done; WAITED=$t; }` | Defines `settle`, the wait for a quiet system before a launch. The loop has no end condition of its own (`while :`). Each turn first calls `check_marker`. Then `read` takes the fourth field of `/proc/loadavg`, for example `1/1019`, into `r`. `${r%/*}` cuts the slash and the text after it. The rest is the number of tasks that are runnable now. The loop ends when that number is 2 or less, or when 20 s have passed. If not, the script waits 2 s and adds 2 to `t`. `sleep 2 & wait $!` runs the sleep in the background and waits for it. A signal then ends the wait immediately, and the trap of line 68 runs. `WAITED` gets the waited time: 0 to 20 s. After 20 s the script goes on without a message. |

### Function `one`: one benchmark process (lines 73 to 95)

| Line | Source | Explanation |
|---:|---|---|
| 73 | `# one <csv> <idx> <tag> <benchmark options...>: one process, with a header line.` | Comment: the function `one` runs one benchmark process. Its arguments are the name of the output file, the `idx` of the process, its tag and the options of the benchmark. It writes a header line before the output of the process. |
| 74 | `one() {` | Starts the function `one`. |
| 75 | `  local csv=$1 idx=$2 tag=$3; shift 3` | Takes the first three arguments into the local variables `csv`, `idx` and `tag`. `shift 3` drops them. The arguments that are left (`$@`) are the options of the benchmark. |
| 76 | `  CUR_CSV=$csv; CUR_TAG=$tag` | Stores the output file and the tag for the trap of line 68. |
| 77 | `  check_marker; check_deadline` | First test before the launch: the three stop reasons (`check_marker`), then the distance to `STOP_AT` (`check_deadline`). |
| 78 | `  settle                                  # checks the marker in every turn` | Waits for a quiet system (`settle`): until at most 2 tasks are runnable, for at most 20 s. Each turn of the wait tests the stop reasons again. |
| 79 | `  # evidence for the load of this launch: users logged in and the 5 busiest processes` | Comment: the next line records the load of the machine at this launch: the number of logins and the 5 processes that use the most CPU time. The code of the next line takes the 5 processes with the highest `pcpu` value of `ps`. That value is an average over the whole life of a process. So a process that became busy only a short time ago can be missing from the list. |
| 80 | `  { echo "== $csv idx $idx $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6; } >> "$OUT/launches.txt"` | Appends the load record of this launch to `launches.txt` in the result folder. Its first line starts with `==`. It holds the output file, the `idx`, the tag, the UTC time (`date -u +%T` prints hours, minutes and seconds), the first four fields of `/proc/loadavg` and the number of logins. `who` prints one line per login, and `wc -l` counts the lines. Then come 6 lines of `ps`: a header and the 5 processes with the highest `pcpu` value. `-e` selects all processes. `-o pcpu,user,comm` prints `pcpu`, the user and the command name. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. `--sort=-pcpu` sorts from high to low, and `head -6` keeps the first 6 lines. The braces group the commands, and `>>` appends their output to the file. |
| 81 | `  check_marker; check_deadline            # again, directly before the launch` | Second test, directly before the launch: the stop reasons and the distance to `STOP_AT` again. The wait and the load record took time. |
| 82 | `  echo "-- step ${csv%.csv} session $SESSION idx $idx tag $tag waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"` | Appends the header line of the process to the output file of the step. The line starts with `-- step`. It holds the step name (`${csv%.csv}` cuts the ending `.csv`), the session, the `idx`, the tag, the seconds that `settle` waited (`waited_s`), the first four fields of `/proc/loadavg`, the number of logins, the UTC time, and after the word `args` all options of the benchmark (`$*`). This is the last reading of the machine state before the process starts. |
| 83 | `  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears` | Comment: the benchmark runs in its own process group. While it runs, the script tests the marker file and the stop file once per second. When one of them appears, the script ends the whole group. The code tests the time `STOP_AT` in the same place. |
| 84 | `  setsid "$BIN" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!` | Starts the benchmark. `setsid` runs the binary `BIN` with the options (`"$@"`) in a new Linux session and a new process group. A Linux session is a set of process groups. It is not a session of the test. One signal to the new group reaches the benchmark and every process that it starts. The standard output of the benchmark is appended to the output file of the step. Its error output is appended to `stderr.txt` (`2>>`). `&` runs it in the background, and the script goes on. `CHILD` gets its process id (`$!`). The script measures no time. All timing happens inside the benchmark. |
| 85 | `  local rc=0` | `rc`: the stop reason, or later the exit status of the benchmark. 0 means none. |
| 86 | `  while kill -0 "$CHILD" 2>/dev/null; do` | Starts the loop that waits for the benchmark. `kill -0` sends no signal. It only tests whether the process still exists. The loop runs while it exists. |
| 87 | `    why_stop \|\| rc=$?` | Once per turn: tests the three stop reasons and keeps the return value in `rc`. |
| 88 | `    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi` | When a stop reason exists: the script appends the line `-- killed tag <tag> status <rc> utc <time>` to the output file, ends the benchmark with `stop_child`, and ends with the exit status 3, 5 or 4. |
| 89 | `    sleep 1 & wait $! \|\| true` | Waits 1 s, in the form that a signal can end immediately. So the script tests the stop reasons once per second, and it sees the end of the benchmark up to about 1 s late. Each turn of this loop starts one `date` process (line 63) and one `sleep` process while the benchmark measures. They may run on any of the CPUs 0 to 119, also on the CPU of the benchmark thread. |
| 90 | `  done` | Ends the loop of line 86. |
| 91 | `  wait "$CHILD" \|\| rc=$?; CHILD=""` | The benchmark has ended. `wait` returns its exit status. A status other than 0 goes to `rc`. `CHILD` is emptied. |
| 92 | `  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi` | When the benchmark ended with a status other than 0: the script appends the line `-- failed tag <tag> exit <rc>` to the output file, prints `benchmark failed` with the tag and the status, and ends with exit status 1. The next process does not start. |
| 93 | `}` | Ends the function `one`. |
| 94 | `# ---- end of the copied part ----` | Comment: the copied part that began in line 48 ends here. |

### Paths of the binary and of the result folders (lines 96 to 100)

| Line | Source | Explanation |
|---:|---|---|
| 96 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC`: the full path of the folder that holds this script. `dirname "$0"` gives the folder part of the path of the script. Inside the command substitution `$( )`, `cd` goes to that folder and `pwd` prints its full path. |
| 97 | `BIN=${BWX8_BIN:-$SRC/bwx8}` | `BIN`: the path of the benchmark binary. When the test variable `BWX8_BIN` is set and not empty, its value is the path. If not, the path is the file `bwx8` in the folder of this script. |
| 98 | `RESULTS=${BWX8_RESULTS:-$HOME/cache-perf/results}` | `RESULTS`: the folder that holds the result folders. It is `$HOME/cache-perf/results` unless the test variable `BWX8_RESULTS` gives another path. |
| 99 | `cd "$SRC"                          # the plan paths in the schedules are relative to this folder` | Makes the folder of the script the working folder. The schedules name each plan file with a path that is relative to this folder, and the benchmark opens the plan with that path. |

### Checks before the first step (lines 101 to 127)

| Line | Source | Explanation |
|---:|---|---|
| 101 | `# ---- checks before the first step starts ----` | Comment: the checks from here to line 126 run before the first step starts. |
| 102 | `if (( SESSION == 2 && ! DRY )); then` | The checks of lines 103 to 109 apply to session 2 only, and not in a dry run. |
| 103 | `  [[ -n ${SESSION1_END:-} ]] \|\| { echo "session 2 needs SESSION1_END (UTC time of the end of session 1), and it is not set: stop" >&2; exit 2; }` | `SESSION1_END` must be set and not empty. If not, the script prints that session 2 needs the UTC time of the end of session 1, and ends with exit status 2. |
| 104 | `  # A full UTC time only: "date -d" also accepts a date without a time and relative words.` | Comment: the next line accepts a full UTC time only. The reason: `date -d` also accepts a date without a time, and relative words such as `yesterday`. |
| 105 | `  [[ $SESSION1_END =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z$ ]] \|\| { echo "bad SESSION1_END: write it as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z" >&2; exit 2; }` | The value must match this pattern: 4 digits, a hyphen, 2 digits, a hyphen, 2 digits, the letter `T`, 2 digits, a colon, 2 digits, then an optional group of a colon and 2 digits (the seconds), then the letter `Z`. If not, the script prints `bad SESSION1_END` with the two allowed forms, and ends with exit status 2. |
| 106 | `  S1_EPOCH=$(date -u -d "$SESSION1_END" +%s) \|\| { echo "bad SESSION1_END" >&2; exit 2; }` | `S1_EPOCH`: the end of session 1 as a number of seconds, counted from 1970-01-01 00:00 UTC. When `date` cannot convert the text, for example for a day that does not exist, the script prints `bad SESSION1_END` and ends with exit status 2. |
| 107 | `  if (( $(date -u +%s) < S1_EPOCH + 10800 )); then` | Tests whether the current time is earlier than the end of session 1 plus 10800 s (3 hours). |
| 108 | `    echo "session 2 may start 3 hours after SESSION1_END $SESSION1_END at the earliest: stop" >&2; exit 2` | If so, the script prints that session 2 may start 3 hours after `SESSION1_END` at the earliest, and ends with exit status 2. |
| 109 | `  fi` | Ends the `if` of line 107. |
| 110 | `fi` | Ends the `if` of line 102. |
| 111 | `if [[ -n ${BWX_PMU_TYPE:-} && ! $BWX_PMU_TYPE =~ ^[0-9]+$ ]]; then echo "BWX_PMU_TYPE must be a whole number (the content of the type file of the core PMU)" >&2; exit 2; fi` | When `BWX_PMU_TYPE` is set and not empty, it must hold digits only. `!` negates the pattern test. When the value holds another character, the script prints that it must be a whole number and ends with exit status 2. |
| 112 | `for STEP_NAME in "${STEPS[@]}"; do` | Starts a loop over the step names of the call. It runs before any process starts, also in a dry run. For every step it checks that the counter settings are given when the step needs them (lines 113 to 115), and that the schedule file can be read (line 117). A missing plan file and a defect in a row of the schedule are not found here. The function `load_step` finds them when their step is reached (lines 138 to 148). |
| 113 | `  case $STEP_NAME in CS\|CM\|C4)` | `case` tests whether the step is one of the three counter steps `CS`, `CM` or `C4`. Only for these steps lines 114 to 115 run. |
| 114 | `    for v in BWX_PMU_TYPE BWX_EVENTS; do [[ -n ${!v:-} ]] \|\| { echo "step $STEP_NAME needs $v, and it is not set: stop (see the head of this file)" >&2; exit 2; }; done` | For these three steps both `BWX_PMU_TYPE` and `BWX_EVENTS` must be set and not empty. The loop tests the two names one after the other. `${!v:-}` gives the value of the variable whose name is in `v`. When one is missing, the script prints that the step needs it and ends with exit status 2. This check runs in a dry run too. |
| 115 | `    export BWX_PMU_TYPE BWX_EVENTS ;;     # bwx8 reads them from its environment` | `export` puts the two variables into the environment of every program that the script starts. The runner reads each of them from there when a trial of the plan uses the counters and the matching option is missing from its command line. The schedules of `schedule8.py` give no counter option in the `args` column. `;;` ends the branch of the `case`. |
| 116 | `  esac` | Ends the `case` of line 113. |
| 117 | `  [[ -r sched/s$SESSION/$STEP_NAME.tsv ]] \|\| { echo "missing schedule $SRC/sched/s$SESSION/$STEP_NAME.tsv (step $STEP_NAME): stop" >&2; exit 2; }` | `-r` tests whether a file exists and is readable. The schedule file of the step, `sched/s<SESSION>/<STEP>.tsv`, must be readable. If not, the script prints `missing schedule` with the path and the step, and ends with exit status 2. |
| 118 | `done` | Ends the loop of line 112. |
| 119 | `if (( ! DRY )); then` | Starts the checks that run in a real run only, not in a dry run. They end at line 126. |
| 120 | `  [[ -x $BIN ]] \|\| { echo "missing $BIN" >&2; exit 2; }` | `-x` tests whether a file exists and is executable. When the binary `BIN` is not, the script prints `missing` with the path and ends with exit status 2. |
| 121 | `  [[ -r build.txt ]] \|\| { echo "missing $SRC/build.txt (the record of the build)" >&2; exit 2; }` | The build record `build.txt` must exist and be readable in the working folder, which is the folder of the script (line 99). If not, the script prints `missing` with the path and the words `the record of the build`, and ends with exit status 2. |
| 122 | `  if [[ -n ${BWX8_SHA256:-} ]]; then` | The digest check of line 123 runs only when `BWX8_SHA256` is set and not empty. |
| 123 | `    [[ $(sha256sum < "$BIN" \| cut -d' ' -f1) == "$BWX8_SHA256" ]] \|\| { echo "bwx8 is not the binary with digest BWX8_SHA256: stop" >&2; exit 2; }` | `sha256sum` reads the binary from its input and prints the sha256 and a file name. `cut -d' ' -f1` keeps the first field, the checksum. When it differs from the value of `BWX8_SHA256`, the script prints `bwx8 is not the binary with digest BWX8_SHA256: stop` and ends with exit status 2. This happens before the first process of the call. |
| 124 | `  fi` | Ends the `if` of line 122. |
| 125 | `  check_marker` | Tests the three stop reasons once before the first step. When the marker file or the stop file exists, or when `STOP_AT` is reached, the script ends here with exit status 3, 5 or 4. It has written no file at this point. |
| 126 | `fi` | Ends the `if` of line 119. |

### Function `load_step`: read a schedule and add up the nominal kernel work (lines 128 to 159)

| Line | Source | Explanation |
|---:|---|---|
| 128 | `# load_step: reads the schedule of STEP_NAME into arrays and adds up the nominal kernel work.` | Comment: the function `load_step` reads the schedule of the step `STEP_NAME` into arrays and adds up the nominal kernel work. |
| 129 | `# Work of a plan: previous activity + prefix + predecessor + windows x window length, over all trials.` | Continues the comment: the work of a plan is the sum over all its trials of four parts: the previous activity, the prefix, the predecessor, and the number of windows times the window length. |
| 130 | `# Work of a --seq process: entries of the sequence x rounds x min-ms.` | Continues the comment: the work of a process with `--seq` is the number of entries of its kernel sequence times the rounds times the `--min-ms` value. Such a process runs the interval mode of the runner and has no plan file. |
| 131 | `load_step() {` | Starts the function `load_step`. |
| 132 | `  local idx tag cpu bytes plan args ms a i seq rounds min c` | Declares the local variables of the function. |
| 133 | `  R_IDX=(); R_TAG=(); R_ARGS=(); R_MS=(); PLANS=()` | Empties five arrays. `R_IDX`, `R_TAG`, `R_ARGS` and `R_MS` get one entry per process: its `idx`, its tag, its options and its nominal work in ms. `PLANS` gets the paths of the plan files of the step. |
| 134 | `  P_N=0; P_SUM_MS=0; P_MAX_MS=0; RUN_N=0; RUN_SUM_MS=0; CONDS_SEQ=""` | Start values of the sums. `P_N`: the number of processes of the step. `P_SUM_MS`: their nominal work in ms. `P_MAX_MS`: the nominal work of the longest process. `RUN_N` and `RUN_SUM_MS`: the count and the sum for the processes that this call runs, those with an `idx` at or above `FROM`. `CONDS_SEQ`: the condition text of a step without plan files. |
| 135 | `  while IFS=$'\t' read -r idx tag cpu bytes plan args; do` | Starts the loop over the rows of the schedule file. `IFS=$'\t'` splits each row at the tab characters into the six columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. `-r` keeps each backslash as it is. The script uses the columns `idx`, `tag`, `plan` and `args`. It does not use the columns `cpu` and `bytes`: the runner gets its CPU and its buffer size from the options in `args`. |
| 136 | `    [[ $idx == idx ]] && continue` | Skips the header row, whose first column is the word `idx`. |
| 137 | `    # idx, rounds and min-ms go into shell arithmetic, which would run a command written inside them.` | Comment: `idx`, the rounds and the `--min-ms` value are used in shell arithmetic. The shell would run a command that is written inside such a value. So the values are checked first. |
| 138 | `    [[ $idx =~ ^(0\|[1-9][0-9]*)$ ]] \|\| { echo "bad idx in $SRC/sched/s$SESSION/$STEP_NAME.tsv: stop" >&2; exit 2; }` | `idx` must be `0` or a number that does not start with 0 (pattern `^(0\|[1-9][0-9]*)$`). If not, the script prints `bad idx in` with the path of the schedule, and ends with exit status 2. |
| 139 | `    if [[ $plan == - ]]; then` | A `-` in the `plan` column means a process without a plan file: a process of the interval mode with `--seq`. |
| 140 | `      read -ra a <<< "$args"; seq=""; rounds=1; min=0` | `read -ra a` splits the options at the blanks into the array `a`. `<<<` gives the text of `args` to `read` as its input. Start values: no sequence, 1 round, 0 ms. |
| 141 | `      for (( i = 0; i < ${#a[@]}; i++ )); do case ${a[i]} in` | Starts a loop over the words of the options. |
| 142 | `        --seq) seq=${a[i+1]} ;; --rounds) rounds=${a[i+1]} ;; --min-ms) min=${a[i+1]} ;; esac; done` | Takes the word after `--seq` as the kernel sequence, the word after `--rounds` as the number of rounds, and the word after `--min-ms` as the shortest time of one interval in ms. Then the line ends the `case` and the loop of line 141. |
| 143 | `      [[ $rounds =~ ^(0\|[1-9][0-9]*)$ && $min =~ ^(0\|[1-9][0-9]*)$ ]] \|\| { echo "bad --rounds or --min-ms in $SRC/sched/s$SESSION/$STEP_NAME.tsv (idx $idx): stop" >&2; exit 2; }` | The rounds and the `--min-ms` value must be whole numbers of the same form. If not, the script prints `bad --rounds or --min-ms in` with the path and the `idx`, and ends with exit status 2. |
| 144 | `      c=${seq//[^,]/}; ms=$(( (${#c} + 1) * rounds * min ))` | `${seq//[^,]/}` removes every character that is not a comma. So the length of `c` is the number of commas, and the sequence has one entry more. `ms`: the entries times the rounds times the `--min-ms` value. This is the nominal work of the process in ms. |
| 145 | `      CONDS_SEQ="seq=$seq"` | Keeps the sequence as the condition text of the step. |
| 146 | `    else` | The other case: a process with a plan file. |
| 147 | `      plan=sched/s$SESSION/$STEP_NAME/$plan` | `plan` becomes the path of the plan file, relative to the folder of the script: the folder `sched/s<SESSION>/<STEP>/` and the file name from the schedule. |
| 148 | `      [[ -r $plan ]] \|\| { echo "missing plan file $SRC/$plan: stop" >&2; exit 2; }` | The plan file must be readable. If not, the script prints `missing plan file` with the path, and ends with exit status 2. This happens before the first launch of the step. |
| 149 | `      ms=$(awk '!/^#/ { split($4, a, ":"); split($5, b, ":"); split($6, c, ":"); ms += a[2] + b[2] + c[2] + $8 * $9 } END { print ms + 0 }' "$plan")` | `awk` adds up the nominal work of the plan in ms. Each line that does not start with `#` is one trial. The fields 4, 5 and 6 are the previous activity, the prefix and the predecessor. Each is `-` or has the form `KERNEL@SIZE:MS`. `split` cuts each at the colon, and the three durations are added. Then field 8 times field 9 is added: the number of target windows times the window length in ms. `print ms + 0` prints the sum as a number, also for a plan without a trial. |
| 150 | `      PLANS+=("$plan")` | Adds the path of the plan file to the list `PLANS`. |
| 151 | `    fi` | Ends the `if` of line 139. |
| 152 | `    R_IDX+=("$idx"); R_TAG+=("$tag"); R_ARGS+=("$args"); R_MS+=("$ms")` | Appends the `idx`, the tag, the options and the nominal work of the process to the four arrays. |
| 153 | `    P_N=$((P_N+1)); P_SUM_MS=$((P_SUM_MS+ms)); (( ms > P_MAX_MS )) && P_MAX_MS=$ms` | Counts the process, adds its work to the sum of the step, and keeps the largest work of one process in `P_MAX_MS`. |
| 154 | `    if (( idx >= FROM )); then RUN_N=$((RUN_N+1)); RUN_SUM_MS=$((RUN_SUM_MS+ms)); fi` | When the `idx` is at or above `FROM`, this call runs the process. It is then counted in `RUN_N` and `RUN_SUM_MS` too. |
| 155 | `  done < "sched/s$SESSION/$STEP_NAME.tsv"` | Ends the loop of line 135. `<` gives the schedule file of the step to the loop as its input. |
| 156 | `  if (( ${#PLANS[@]} )); then CONDS=$(awk '!/^#/ { print $2 }' "${PLANS[@]}" \| sort -u \| tr '\n' ' ')` | With plan files: `CONDS` becomes the list of the conditions of the step. `awk` prints field 2, the condition label, of every trial line of all plan files. `sort -u` sorts the labels and drops duplicates. `tr` replaces each newline with a blank. So the list is one line. |
| 157 | `  else CONDS=$CONDS_SEQ; fi` | Without plan files: `CONDS` is the sequence text of line 145. `fi` ends the `if`. |
| 158 | `}` | Ends the function `load_step`. |

### Main loop: the summary of a step and the dry run (lines 160 to 176)

| Line | Source | Explanation |
|---:|---|---|
| 160 | `for STEP_NAME in "${STEPS[@]}"; do` | Starts the main loop: one pass per step, in the order of the call. |
| 161 | `  load_step` | Reads the schedule of the step and computes its counts and its nominal work. |
| 162 | `  (( RUN_N )) \|\| { echo "step $STEP_NAME session $SESSION has no process with idx $FROM or above: stop" >&2; exit 2; }` | When no process has an `idx` at or above `FROM`, the script prints that the step has no such process, and ends with exit status 2. |
| 163 | `  MARGIN=$(( (P_MAX_MS + 999) / 1000 + RESERVE ))` | `MARGIN` for this step, in seconds: the nominal work of the longest process, rounded up to whole seconds, plus `RESERVE`. Adding 999 before the whole-number division by 1000 rounds up. |
| 164 | `  # Printed before execution, in a real run too (design line 356).` | Comment: the summary of lines 166 to 169 is printed before the first process of the step starts, in a real run too. The comment points to the design file `tackle-8mb.md`, the plan of the investigation. That file asks that a runner print the selected conditions, the process count and the nominal work before execution. |
| 165 | `  (( DRY )) && echo "# ---- step $STEP_NAME session $SESSION ----"` | In a dry run only: prints a heading line with the step and the session. |
| 166 | `  printf 'step %s session %d: %d processes, nominal kernel work %d.%03d s (%d.%02d min); to run from idx %d: %d processes, %d.%03d s; longest process %d s, MARGIN %d s, waits between processes at most %d s more\n' \` | Prints the summary line of the step: the number of processes, the nominal kernel work of the whole step in seconds with three decimal places and in minutes with two, the `idx` from which this call runs, the number of processes and the nominal work that this call runs, the longest process in whole seconds, `MARGIN`, and the longest sum of the waits before the launches. The values follow in lines 167 to 168. The backslash at the end joins the next line to this command. |
| 167 | `    "$STEP_NAME" "$SESSION" $P_N $((P_SUM_MS/1000)) $((P_SUM_MS%1000)) $((P_SUM_MS/60000)) $((P_SUM_MS%60000/600)) \` | Continues the `printf` of line 166: the step, the session, `P_N`, and `P_SUM_MS` as whole seconds (`/1000`), the ms that are left (`%1000`), whole minutes (`/60000`) and hundredths of a minute (`%60000/600`). |
| 168 | `    $FROM $RUN_N $((RUN_SUM_MS/1000)) $((RUN_SUM_MS%1000)) $(( (P_MAX_MS+999)/1000 )) $MARGIN $((RUN_N*20))` | Continues the `printf` of line 166: `FROM`, `RUN_N`, `RUN_SUM_MS` as seconds and ms, the longest process rounded up to whole seconds, `MARGIN`, and `RUN_N*20`. The last value is 20 s for each process to run, the longest wait of `settle`. |
| 169 | `  echo "step $STEP_NAME selected conditions ($(wc -w <<< "$CONDS")): $CONDS"` | Prints the selected conditions of the step. `wc -w` counts the words of `CONDS`, that is the number of different conditions. The list follows. |
| 170 | `  if (( DRY )); then` | The dry run: it prints the command lines and starts nothing. |
| 171 | `    for (( i = 0; i < ${#R_IDX[@]}; i++ )); do` | Starts a loop over the processes of the step. |
| 172 | `      (( R_IDX[i] < FROM )) && continue` | Skips a process whose `idx` is below `FROM`. |
| 173 | `      printf 'bwx8 %s  # idx %d, tag %s, nominal %d.%03d s\n' "${R_ARGS[i]}" "${R_IDX[i]}" "${R_TAG[i]}" $((R_MS[i]/1000)) $((R_MS[i]%1000))` | Prints one line per process: the word `bwx8`, the options from the `args` column, and after `#` the `idx`, the tag and the nominal work in seconds with three decimal places. The line shows the command in a short form. The real launch uses the path `BIN` (line 84). |
| 174 | `    done` | Ends the loop of line 171. |
| 175 | `    continue` | Goes to the next step. A dry run makes no result folder and starts no process. |
| 176 | `  fi` | Ends the `if` of line 170. |

### Main loop: result folder, `env.txt`, the processes (lines 177 to 201)

| Line | Source | Explanation |
|---:|---|---|
| 177 | `  check_marker; check_deadline` | Before the result folder is made: tests the three stop reasons and the distance to `STOP_AT`, now with the `MARGIN` of this step. |
| 178 | `  OUT=$RESULTS/bwx8-$STEP_NAME-s$SESSION-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder of this step. Its name is `bwx8-`, the step, `-s`, the session, a hyphen and the UTC time of this moment in the form `YYYYMMDDTHHMMSSZ`, for example `bwx8-S2-s1-20261115T003207Z` [Ref1]. |
| 179 | `  mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders and reports no error when the folder exists. |
| 180 | `  echo "result folder: $OUT"` | Prints the path of the result folder. |
| 181 | `  cp "sched/s$SESSION/$STEP_NAME.tsv" "$OUT/schedule.tsv"` | Copies the schedule file of the step into the result folder, with the name `schedule.tsv`. |
| 182 | `  cp build.txt "$OUT/build.txt"` | Copies the build record `build.txt` from the folder of the script into the result folder. |
| 183 | `  {` | Opens a group of commands. All their output goes to the file `env.txt` (line 192). |
| 184 | `    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who \| wc -l) step=$STEP_NAME steps=${STEPS[*]}"` | First line of `env.txt`: the host name, the UTC date and time (`%FT%TZ` prints a form such as `2026-11-15T03:00:00Z`), the whole content of `/proc/loadavg`, the number of logins, this step, and all steps of the call. |
| 185 | `    echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Second line: the setting of transparent huge pages (file `enabled`) and of their defragmentation (file `defrag`), both read from the folder `/sys/kernel/mm/transparent_hugepage/`. |
| 186 | `    echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree\|MemAvailable' /proc/meminfo \| tr -s ' ' \| tr '\n' ' ')"` | Third line: the time after the boot in seconds, which is the first field of `/proc/uptime`. Then the lines `MemFree` and `MemAvailable` of `/proc/meminfo`. `grep -E` selects the two lines, `tr -s ' '` reduces each run of blanks to one blank, and `tr '\n' ' '` joins the lines. |
| 187 | `    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6` | A heading line, then the header and the 5 processes with the highest `pcpu` value, from the same `ps` command as in line 80. |
| 188 | `    echo "## sha256:"; sha256sum "$BIN" "$SRC/run_bwx8.sh" "$SRC/sched/s$SESSION/$STEP_NAME.tsv" "$SRC/build.txt"` | A heading line, then the sha256 of four files: the binary, this script (`run_bwx8.sh`), the schedule file of the step and the build record. So the result folder shows which files ran. The plan files are not in this list. The runner prints a hash of its plan file in its own output (row `M,plan_fnv1a64`). |
| 189 | `    echo "## vmstat thp:"; grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat \|\| true` | A heading line, then three counters of `/proc/vmstat` at the start of the step: `thp_fault_alloc`, `thp_fault_fallback` and `thp_collapse_alloc`. They count the huge pages that Linux gave at a page fault, the page faults that got no huge page, and the huge pages that Linux built later from small pages. `\|\| true` keeps the script running when `grep` finds no such line. |
| 190 | `    echo "## settings: session=$SESSION from=$FROM SESSION1_END=${SESSION1_END:-} STOP_AT=$STOP_AT MARGIN=$MARGIN planned_processes=$P_N planned_nominal_ms=$P_SUM_MS to_run_processes=$RUN_N to_run_nominal_ms=$RUN_SUM_MS BWX8_SHA256=${BWX8_SHA256:-} BWX_PMU_TYPE=${BWX_PMU_TYPE:-} BWX_EVENTS=${BWX_EVENTS:-} MARKER=$MARKER STOPFILE=$STOPFILE BIN=$BIN RESULTS=$RESULTS"` | The settings line: the session, `FROM`, `SESSION1_END`, `STOP_AT`, `MARGIN`, the number and the nominal ms of all processes of the step and of the processes that this call runs, the digest setting `BWX8_SHA256`, the two counter settings, and the four paths in use (`MARKER`, `STOPFILE`, `BIN`, `RESULTS`). A setting that is not set gives an empty value. |
| 191 | `    echo "## selected conditions: $CONDS"` | The last line of the group: the selected conditions of the step. |
| 192 | `  } > "$OUT/env.txt"` | Ends the group of line 183. `>` writes its output to a new file `env.txt` in the result folder. |
| 193 | `  for (( i = 0; i < ${#R_IDX[@]}; i++ )); do` | Starts the loop over the processes of the step, in the order of the schedule. |
| 194 | `    (( R_IDX[i] < FROM )) && continue` | Skips a process whose `idx` is below `FROM`. |
| 195 | `    read -ra ARGV <<< "${R_ARGS[i]}"` | Splits the options of the process at the blanks into the array `ARGV`. Each word becomes one argument of the benchmark. |
| 196 | `    one "$STEP_NAME.csv" "${R_IDX[i]}" "${R_TAG[i]}" "${ARGV[@]}"` | Runs the process with the function `one`: the checks, the wait, the load record, the header line, the launch and the wait for the end. The output file is `<STEP>.csv`. The script goes to the next process only when this one ended with status 0. |
| 197 | `  done` | Ends the loop of line 193. |
| 198 | `  echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"` | After the last process: appends an end line to `env.txt` with the UTC time and the content of `/proc/loadavg`. |
| 199 | `  grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt" \|\| true` | Appends the three huge page counters of `/proc/vmstat` again. The difference to the values of line 189 shows what changed during the step. |
| 200 | `  echo "$OUT"` | Prints the path of the result folder once more, as the last line of the step. |
| 201 | `done` | Ends the main loop of line 160. After the last step the script ends with exit status 0. |

## References

- [Ref1] the files `env.txt` of the 6 result folders `bwx8-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`, for example `bwx8-S2-s1-20261115T003207Z`. In each file the list after the line `## sha256:` gives `2d326dd3f095389614548bbb1f7931c3f1f7a0fd3978aa392973550a278b9828` for `run_bwx8.sh`. The file in the code folder has the same sha256. The first line of each file ends with `steps=B6W S2 S4`.
- [Ref2] the log files `visit8-s1-B6W-S2-S4.log` and `visit8-s2-B6W-S2-S4.log` in `tests/2026-11-15-tackle-8mb/logs/` of the repo `arm-crb`. Each holds the summary lines and the result folder names of the three steps `B6W`, `S2` and `S4` of one session, in this order. Each has one line `ssh status 0`, its last line. The script `visit8.sh` writes one such line per login.
