# `run_bwx11.sh` explained, line by line

- Source file: `bwx11-2026-11-15/run_bwx11.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 296 lines, 22200 bytes).
- sha256 of the source when this page was built: `911644f1e8c8f7d6c9c4253910657347674593fcd5c32bff8d6cbf7ef75de2a8`.

## Short version: purpose

`run_bwx11.sh` runs the steps of round 4 on CRB: for each step it starts the processes of a schedule file one at a time, each with the runner that the schedule names. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **Step**: one batch of processes of a round, for example `ZD`. One schedule file lists its processes.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **Generator**: the program `schedule11.py`. It writes the schedules and the plan files of round 4.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Window**: one timed period of one kernel inside a trial.
- **Trial mode, interval mode**: the two modes of the runner. With `--trial` one pinned worker thread runs the trials of a plan file. With `--seq` the runner times a sequence of kernels in intervals and reads no plan file.
- **Nominal kernel work**: the sum of the planned durations of all timed parts of a process or of a step. The real run time is longer.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. The script starts no process that could run past it, and it ends a process that still runs at that time. The value `none` sets no limit.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s when the variable is not set or is empty. `MARGIN` is the nominal work of the longest process of a step plus `RESERVE`.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Host sampler**: the program `hostwatch.py`. It records what the Linux kernel does on one CPU while one process runs.
- **Dry run**: a call with `--dry-run`. It prints what would run and starts nothing.
- **Evict step**: a step of the runner `bwx11` before the first trial, asked for with `--evict-mb N`. The runner writes N MiB of other memory twice.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the part of a core that holds the hardware counters.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Process group**: a set of processes that one signal can reach together.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The header comment gives the usage, the settings and the exit statuses (lines 1 to 59).
2. Limit the script and everything that it starts to the CPUs 0 to 119 (lines 60 to 61).
3. Read the options and the step names, and check `SESSION` (lines 62 to 74).
4. Print a warning for each test variable that is set (lines 76 to 78).
5. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption (lines 81 to 103).
6. Set the paths of the three runners and make the folder of the script the working folder (lines 137 to 155).
7. For session 2, refuse a start earlier than 3 hours after `SESSION1_END` (lines 158 to 166).
8. For each step, check the schedule file, the counter settings and the `.bin` file (lines 167 to 182).
9. In a real run, check each binary, its `build.txt`, its digest and what the host sampler needs. Then test the stop reasons once (lines 183 to 200).
10. For each step, read the schedule, compute the nominal work and `MARGIN`, and print the summary (lines 236 to 255).
11. In a dry run, print one command line per process and go to the next step (lines 256 to 262).
12. In a real run, make the result folder and write `schedule.tsv`, `build.txt` and `env.txt` (lines 263 to 279).
13. With a host sampler, run its start check (lines 280 to 286).
14. Run the processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line, starts the runner, and tests the stop reasons once per second until the runner ends (lines 287 to 292).
15. Append the end line to `env.txt` and print the path of the result folder (lines 293 to 296).

## Behavior a reader must know

- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing setting or file, a wrong digest, or a session 2 that would start too early: status 2. Most of these checks run before the first process of the call. The checks of one step run when that step starts: the schedule rows and the plan files (lines 212 to 224), the test that a process is left to run (line 239), the test that `WATCH_CPU` is no CPU of the schedule (line 253) and the start check of the host sampler (lines 283 to 285). In a call with several steps the earlier steps have run by then.
- A seventh thing stops the run without a message of the script. With `set -e` (line 60) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder or `cp` cannot write its copy (lines 265 to 268). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- The first three stop reasons are tested at these places: once before the first step (line 199), once before each result folder is made (line 263), twice before each launch (line 112, line 116), in every turn of the wait for a quiet system (line 107), and once per second while a process runs (line 126).
- A process that runs at a stop is ended. First the script appends a line that starts with `-- killed` to the output file (line 103, line 127). Then the signal TERM goes to the process group of the process, and the signal KILL follows 1 s later (line 91).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message (line 107). There is no fixed pause.
- For each launch the script records the load in two places. `launches.txt` gets a line with the load averages and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` (line 115). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in `<STEP>.csv` gets the waited seconds, the load averages, the number of logins, the UTC time and the options (line 117).
- The script times nothing. All timing happens inside the runner.
- The script never repeats a process. A stopped step is continued with `--from IDX`, in a new result folder.
- The script deletes nothing. At every stop the files that were written before stay.
- The script and the runner may use the CPUs 0 to 119 only (line 61). A caller that has already set `_PINNED` to a text that is not empty gets no such limit. The host sampler gets its own CPU from `taskset`, and line 196 keeps that CPU at 119 or below.
- The exit status is 0 only when every step of the call ran to its end.
- The text of this file is the text that ran on CRB in round 4 [Ref1].

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/run_bwx11.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (296 lines, 22200 bytes, sha256 `911644f1e8c8f7d6c9c4253910657347674593fcd5c32bff8d6cbf7ef75de2a8`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: purpose, steps, binaries, `STOP_AT`, session, options, counter settings (lines 1 to 29)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_bwx11.sh - the steps of round 4 of the 8 MiB investigation on CRB, one visit per call.` | Comment: the name and the purpose of the file. The script runs the steps of round 4 on CRB. Round 4 is the fourth set of tests of the investigation into the buffer size of 8 MiB. One call of the script is one visit to CRB, that is one login. |
| 3 | `# A copy of run_bwx10.sh. The differences: step names, the folder sched11/, the binary of a step (the` | Comment: the file is a copy of `run_bwx10.sh`, the run script of round 3. The list of the differences starts here: the step names, the schedule folder `sched11/`, and the binary of a step. |
| 4 | `# accepted bwx8 or bwx10, or the new bwx11, named by the schedule), one digest check per binary, and the name of` | Continues the list of differences. A step uses one of three runners: the accepted `bwx8`, the accepted `bwx10` or the new `bwx11`. A runner is accepted when its build on CRB has passed the acceptance checks of its round. The schedule names the binary of a step. Each binary has its own digest check. A digest is the sha256 checksum of a file. |
| 5 | `# the result folders. The stop controls (marker file, STOP_AT, stop file, interruption, the wait for a` | Comment: the last difference is the name of the result folders. Then the comment names what is the same as in the older script: the stop controls. These are the marker file, `STOP_AT`, the stop file, the handling of an interruption, the wait for a quiet system and the load record. |
| 6 | `# quiet system, the load record) and the host sampler are the same.` | Continues the comment: the host sampler is the same too. The host sampler is the program `hostwatch.py`. It records what the Linux kernel does on one CPU while a benchmark process runs. |
| 7 | `# Usage: STOP_AT=<UTC time or "none"> SESSION=<1\|2> run_bwx11.sh [--dry-run] [--from IDX] STEP...` | Comment: the usage. The caller sets two environment variables: `STOP_AT` (a UTC time or the word `none`) and `SESSION` (`1` or `2`). The arguments are the two optional options `--dry-run` and `--from IDX`, and one or more step names. |
| 8 | `#   STEP: any name that matches ^Z[A-Z0-9]+$ and has a schedule (schedule11.py writes ZA ZD ZC ZN ZM).` | Comment: a step name is the letter `Z` followed by one or more capital letters or digits, and the step must have a schedule file. The generator `schedule11.py` writes the schedules of the steps `ZA`, `ZD`, `ZC`, `ZN` and `ZM`. |
| 9 | `#   The steps run in the order given.` | Comment: the steps run in the order in which the call names them. |
| 10 | `#   The processes of a step come from sched11/s<SESSION>/<STEP>.tsv beside this script (schedule11.py` | Comment: the processes of a step come from the schedule file `sched11/s<SESSION>/<STEP>.tsv` in the folder of this script. The generator `schedule11.py` writes that file. |
| 11 | `#   writes it). The script runs them in that order, one at a time. It never repeats a process.` | Continues the comment: the script runs the processes in the order of the schedule, one at a time. It never runs a process a second time. |
| 12 | `#   Binary of a step: the file sched11/s<SESSION>/<STEP>.bin holds one word. "bwx11" means bwx11 beside` | Comment: the file `sched11/s<SESSION>/<STEP>.bin` holds one word. The word names the binary of the step. The word `bwx11` means the file `bwx11` in the folder of this script. |
| 13 | `#   this script. "bwx8" means the accepted binary of round 1, $HOME/cache-perf/bwx8-20261114/bwx8. "bwx10"` | Continues the comment: the word `bwx8` means the accepted binary of round 1, `$HOME/cache-perf/bwx8-20261114/bwx8`. The sentence about the word `bwx10` starts at the end of this line. |
| 14 | `#   means the accepted binary of round 3, $HOME/cache-perf/bwx10-20261115/bwx10. Any other content, or a` | Continues the comment: the word `bwx10` means the accepted binary of round 3, `$HOME/cache-perf/bwx10-20261115/bwx10`. Any other content of the `.bin` file stops the script. |
| 15 | `#   missing file, stops the script with status 2. build.txt is copied into the result folder from the` | Continues the comment: a missing `.bin` file stops the script too. The exit status is 2 in both cases. The script copies `build.txt`, the record of the build of a binary, into the result folder. |
| 16 | `#   folder of the binary that the step uses. schedule11.py names bwx11 for every step.` | Continues the comment: `build.txt` comes from the folder of the binary that the step uses. The generator `schedule11.py` writes the word `bwx11` for every step. |
| 17 | `#   STOP_AT is required. Example: STOP_AT=2026-11-15T15:00Z (start nothing that could run past this` | Comment: `STOP_AT` must be set. With a time such as `2026-11-15T15:00Z` the script starts nothing that could still run at that time. |
| 18 | `#   time), or STOP_AT=none when no block is announced.` | Continues the comment: `STOP_AT=none` sets no time limit. It is for a visit at which no block is announced. A block is a time window that another user has reserved on CRB. |
| 19 | `#   SESSION is required. SESSION=2 also needs SESSION1_END=<UTC time>, the end of session 1, written` | Comment: `SESSION` must be set. Session 2 repeats the steps of session 1. With `SESSION=2` the caller must also set `SESSION1_END` to the UTC time at which session 1 ended. |
| 20 | `#   as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z (no other form is accepted). The` | Continues the comment: that time must have the form `2026-11-15T03:00Z` or `2026-11-15T03:00:00Z`. The script accepts no other form. |
| 21 | `#   script refuses to start session 2 earlier than 3 hours after that time (status 2).` | Continues the comment: the script does not start session 2 earlier than 3 hours after the end of session 1. It then ends with exit status 2. |
| 22 | `#   --dry-run: prints every command line and the counts of each step. It starts no benchmark, makes` | Comment: with `--dry-run` the script prints the command line of every process and the counts of each step. It starts no benchmark. |
| 23 | `#   no result folder, and needs neither STOP_AT nor SESSION1_END nor the binaries.` | Continues the comment: a dry run makes no result folder. It needs no `STOP_AT`, no `SESSION1_END` and no binary. |
| 24 | `#   --from IDX: continue a stopped step at the process with this idx. Only with one STEP. The value` | Comment: `--from IDX` continues a step that was stopped. The script starts at the process whose `idx` is `IDX`. The `idx` is the number of a process in its schedule, counted from 0. The option is allowed only when the call names one step. |
| 25 | `#   is written to env.txt. The processes go to a new result folder.` | Continues the comment: the script writes the value of `--from` to the file `env.txt`. The processes of the continued step go to a new result folder. |
| 26 | `#   Counter settings: a step needs BWX_PMU_TYPE (the "type" file of the core PMU) and BWX_EVENTS` | Comment: the counter settings. `BWX_PMU_TYPE` is the type number that Linux gives to the counter device of the cores. Linux shows it in the file `type` of that device. PMU means performance monitoring unit, the part of a core that holds the hardware counters. `BWX_EVENTS` is the list of the counter events. |
| 27 | `#   (NAME=CODE,...) in the environment only if one of its processes has neither --pmu-type nor --events` | Continues the comment: `BWX_EVENTS` has the form `NAME=CODE,...`. A step needs the two variables in the environment only when one of its processes has neither `--pmu-type` nor `--events` in the `args` column of the schedule. |
| 28 | `#   in the args column of the schedule and its plan has a trial with count open or read. The` | Continues the comment: and only when the plan of that process has a trial whose `count` field is `open` or `read`. Such a trial uses the counters. A trial with `count` equal to `closed` uses none. |
| 29 | `#   schedules of schedule11.py give both options in the args column, so they need no setting.` | Continues the comment: the schedules that `schedule11.py` writes give both options in the `args` column. So they need no counter setting in the environment. |

### Header comment: host sampler, optional settings, exit statuses, needs, status (lines 30 to 59)

| Line | Source | Explanation |
|---:|---|---|
| 30 | `#   Host sampler: if sched11/s<SESSION>/<STEP>.watch exists, hostwatch.py (beside this script) runs` | Comment: the host sampler. When the file `sched11/s<SESSION>/<STEP>.watch` exists, the program `hostwatch.py` from the folder of this script runs beside every process of the step. |
| 31 | `#   beside every process of the step, pinned to CPU WATCH_CPU (default 100). It reads /proc only and` | Continues the comment: the sampler is pinned to the CPU that `WATCH_CPU` names. That is CPU 100 when the variable is not set or is empty. The sampler only reads files under `/proc`. |
| 32 | `#   writes watch-<idx>.txt into the result folder (its messages go to watch-stderr.txt). It is stopped` | Continues the comment: the sampler writes one file `watch-<idx>.txt` per process into the result folder. Its messages go to the file `watch-stderr.txt`. |
| 33 | `#   when the benchmark ends or is stopped. Such a step needs python3: without it the script stops` | Continues the comment: the script stops the sampler when the benchmark ends or is stopped. A step with a sampler needs the program `python3`. |
| 34 | `#   with status 2 before the first process of the call. WATCH_CPU must be a CPU from 0 to 119 that` | Continues the comment: without `python3` the script ends with exit status 2 before the first process of the call. `WATCH_CPU` must be a CPU from 0 to 119. |
| 35 | `#   is not a CPU of the schedule (status 2 otherwise). Before the first process of such a step the` | Continues the comment: `WATCH_CPU` must not be a CPU of the schedule. If it is one, the script ends with exit status 2. |
| 36 | `#   sampler runs once for 0.3 s on this script (watch-selftest.txt): if it does not end cleanly, the` | Continues the comment: before the first process of such a step the sampler runs once for 0.3 s with this script as the watched process. Its output file is `watch-selftest.txt`. |
| 37 | `#   step stops with status 2. A process whose sampler file has no "# end" line gives a warning.` | Continues the comment: when that short run of the sampler does not end without an error, the script ends with exit status 2. The script prints a warning for a process whose sampler file has no line that starts with `# end`. |
| 38 | `#   schedule11.py writes no .watch file: no step of round 4 runs with the sampler.` | Comment: `schedule11.py` writes no `.watch` file. So no step of round 4 runs with the host sampler. |
| 39 | `#   Optional: BWX8_SHA256, BWX10_SHA256 and BWX11_SHA256 (the expected digest of bwx8, bwx10 and bwx11).` | Comment: three optional variables. `BWX8_SHA256`, `BWX10_SHA256` and `BWX11_SHA256` hold the digest that the binary `bwx8`, `bwx10` or `bwx11` must have. |
| 40 | `#             Each one is checked if it is set and a step of the call uses that binary: status 2 if the` | Continues the comment: the script checks a digest only when its variable is set and a step of the call uses that binary. |
| 41 | `#             binary differs, before the first process of the call;` | Continues the comment: when a binary differs from its digest, the script ends with exit status 2 before the first process of the call. |
| 42 | `#             RESERVE (seconds added to the longest process of a step to give MARGIN, default 90),` | Comment: the optional variable `RESERVE`, 90 s when it is not set or is empty. `MARGIN` is the longest process of a step plus `RESERVE`, in seconds. The script starts a process only when `STOP_AT` is more than `MARGIN` seconds away. |
| 43 | `#             WATCH_CPU (CPU of the host sampler, default 100; not a CPU of the schedule).` | Comment: the optional variable `WATCH_CPU`, the CPU of the host sampler. It is CPU 100 when the variable is not set or is empty. It must not be a CPU of the schedule. |
| 44 | `#   For local tests with a dummy binary only: BWX8_MARKER, BWX8_STOPFILE, BWX8_BIN (the path used for` | Comment: variables for local tests with a dummy binary only. `BWX8_MARKER` gives another path for the marker file, and `BWX8_STOPFILE` another path for the stop file. The explanation of `BWX8_BIN` starts at the end of this line. |
| 45 | `#   the word bwx8), BWX10_BIN (the path used for the word bwx10), BWX11_BIN (the path used for the word` | Continues the comment: `BWX8_BIN` is the path that the script uses for the word `bwx8`. `BWX10_BIN` is the path for the word `bwx10`. The explanation of `BWX11_BIN` starts here. |
| 46 | `#   bwx11), BWX8_RESULTS.` | Continues the comment: `BWX11_BIN` is the path for the word `bwx11`. The last test variable is `BWX8_RESULTS`, another place for the result folders. |
| 47 | `#   The script prints a warning for each one that is set, and env.txt records the paths in use.` | Comment: the script prints a warning for each of these test variables that is set. The file `env.txt` records the paths that the run used. |
| 48 | `# Exit status: 0 done; 1 a benchmark failed; 2 usage, missing setting, missing file, wrong digest, or` | Comment: the exit statuses. 0: all steps are done. 1: a benchmark process failed. 2: a wrong usage, a missing setting, a missing file or a wrong digest. |
| 49 | `#   session 2 too early; 3 marker file appeared; 4 STOP_AT reached; 5 stop file ~/cache-perf/STOP found;` | Continues the comment: 2 also when session 2 would start too early. 3: the marker file exists. 4: the time `STOP_AT` is reached. 5: the stop file `~/cache-perf/STOP` exists. The code gives 4 also before a launch when `STOP_AT` is `MARGIN` seconds away or less (line 102). |
| 50 | `#   130 interrupted. In every case the files written so far are kept.` | Continues the comment: 130: a signal interrupted the script. In every case the files that were written before the stop are kept. |
| 51 | `# Needs sched11/ and hostwatch.py in the same folder as this script, and each binary with its build.txt` | Comment: the script needs the folder `sched11/` and the file `hostwatch.py` in its own folder. The sentence about the binaries starts here: each binary lies beside its `build.txt`. |
| 52 | `# in one folder.` | Continues the comment: each binary and its `build.txt` lie in one folder. |
| 53 | `# Uses CPUs 0-119 only, writes only under $HOME/cache-perf/results/bwx11-<step>-s<session>-<UTC>/, no sudo.` | Comment: the script uses the CPUs 0 to 119 only. It writes only into result folders with the name `$HOME/cache-perf/results/bwx11-<step>-s<session>-<UTC>/`. It never uses `sudo`, the command that runs a program as root. The code sets the CPU limit in line 61. It does so only when the caller has not already set `_PINNED` to a text that is not empty. |
| 54 | `# Time: the nominal kernel work that the script prints leaves out the evict step of a process with` | Comment: the nominal kernel work is the sum of the planned durations of the timed parts of all processes. The script prints it. It does not hold the evict step of a process. |
| 55 | `# "--evict-mb N" in its args (est. 0.3 to 1 s of real time per process). MARGIN is the longest process of the` | Continues the comment: a process with `--evict-mb N` in its options has an evict step. In that step the runner `bwx11` writes N MiB of other memory twice before the first trial. The comment gives est. 0.3 to 1 s of real time per process for it. |
| 56 | `# step plus RESERVE, and RESERVE covers that step.` | Continues the comment: `MARGIN` is the longest process of the step plus `RESERVE`. By the comment `RESERVE` is large enough to hold the evict step. |
| 57 | `# Status: written 2026-11-15 from run_bwx10.sh (which ran session 1 of round 3 on CRB). Syntax, dry run,` | Comment: the state of the file when it was written, on 2026-11-15. It was made from `run_bwx10.sh`. By the comment that script ran session 1 of round 3 on CRB. |
| 58 | `# stop controls, the choice of the binary and the three digest checks tested locally with dummy binaries` | Continues the comment: the syntax, the dry run, the stop controls, the choice of the binary and the three digest checks were tested with dummy binaries, not on CRB. |
| 59 | `# (test_schedule11.py). This script itself has not run on CRB yet.` | Continues the comment: the test file is `test_schedule11.py`. The last sentence says that this script has not run on CRB yet. It gives the state at the time of writing. Later this text ran on CRB: the file `env.txt` of each result folder of round 4 records the sha256 of this file [Ref1]. |

### Shell options, CPU limit, arguments and first checks (lines 60 to 79)

| Line | Source | Explanation |
|---:|---|---|
| 60 | `set -euo pipefail` | `set -e`: the script stops when a command fails. A command that is tested by `if` or `while`, or that stands before `\|\|` or `&&`, does not stop it. `set -u`: the script stops when it uses a variable that was never set. `set -o pipefail`: a pipeline fails when any of its commands fails, not only the last one. |
| 61 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Limits the script and everything that it starts to the CPUs 0 to 119. `${_PINNED:-}` gives the value of `_PINNED`, or an empty text when the variable is not set. `-z` tests for an empty text. On the first pass the variable is empty. Then `exec` replaces the shell with `taskset -c 0-119`. That tool sets the CPU list and starts this script again (`$0`) with the same arguments (`"$@"`) and with `_PINNED=1` in its environment. On the second pass the variable is set, and the script goes on. When the caller has already set `_PINNED` to a text that is not empty, the script sets no CPU limit. |
| 62 | `DRY=0; FROM=0; STEPS=()` | Start values. `DRY`: 1 in a dry run. `FROM`: the `idx` of the first process to run. `STEPS`: the list of the step names, empty at first. |
| 63 | `while (( $# )); do case $1 in` | Starts the loop over the arguments. `$#` is the number of arguments that are left. The loop runs while it is not 0. `case` compares the first argument (`$1`) with the patterns that follow. |
| 64 | `  --dry-run) DRY=1 ;;` | The option `--dry-run` sets `DRY` to 1. |
| 65 | `  --from) [[ ${2:-} =~ ^[0-9]+$ ]] \|\| { echo "--from needs a process index" >&2; exit 2; }; FROM=$((10#$2)); shift ;;` | The option `--from`. The next argument (`$2`) must hold digits only: the pattern `^[0-9]+$` matches one or more digits and nothing else. If not, the script prints `--from needs a process index` to the error output (`>&2`) and ends with exit status 2. `FROM=$((10#$2))` stores the number. `10#` makes the shell read it as a decimal number, also when it starts with a zero. `shift` drops the option. The `shift` of line 67 then drops its value. |
| 66 | `  *) [[ $1 =~ ^Z[A-Z0-9]+$ ]] \|\| { echo "unknown step or option: $1" >&2; exit 2; }; STEPS+=("$1") ;;` | Every other argument must be a step name: the letter `Z` followed by one or more capital letters or digits (pattern `^Z[A-Z0-9]+$`). If not, the script prints `unknown step or option:` with the argument and ends with exit status 2. A valid name is added to the list `STEPS`. |
| 67 | `esac; shift; done` | Ends the `case`. `shift` drops the argument that was handled. `done` ends the loop of line 63. |
| 68 | `(( ${#STEPS[@]} )) \|\| { echo "usage: STOP_AT=<UTC\|none> SESSION=<1\|2> $0 [--dry-run] [--from IDX] STEP...   (see the head of this file)" >&2; exit 2; }` | `${#STEPS[@]}` is the number of step names. When it is 0, the script prints the usage line to the error output and ends with exit status 2. |
| 69 | `for (( i = 0; i < ${#STEPS[@]}; i++ )); do for (( j = 0; j < i; j++ )); do` | Two nested loops compare every step name with every name before it in the list. |
| 70 | `  [[ ${STEPS[i]} != "${STEPS[j]}" ]] \|\| { echo "step ${STEPS[i]} is named twice: stop (the script never repeats a process)" >&2; exit 2; }` | When two names are equal, the script prints that the step is named twice and ends with exit status 2. So one call cannot run a step twice. |
| 71 | `done; done` | Ends the two loops of line 69. |
| 72 | `(( FROM == 0 \|\| ${#STEPS[@]} == 1 )) \|\| { echo "--from needs exactly one step" >&2; exit 2; }` | A `--from` value above 0 is allowed only with exactly one step. If the call names more steps, the script prints `--from needs exactly one step` and ends with exit status 2. |
| 73 | `[[ ${SESSION:-} == 1 \|\| ${SESSION:-} == 2 ]] \|\| { echo "set SESSION to 1 or 2" >&2; exit 2; }` | `SESSION` must be `1` or `2`. If not, the script prints `set SESSION to 1 or 2` and ends with exit status 2. |
| 74 | `(( DRY )) && STOP_AT=${STOP_AT:-none}` | In a dry run only: when `STOP_AT` is not set or is empty, it becomes `none`. So a dry run needs no `STOP_AT`. |
| 76 | `for v in BWX8_MARKER BWX8_STOPFILE BWX8_BIN BWX10_BIN BWX11_BIN BWX8_RESULTS; do` | Starts a loop over the names of the six variables that are for local tests only. |
| 77 | `  [[ -z ${!v:-} ]] \|\| echo "warning: $v is set (for local tests only): $v=${!v}" >&2` | `${!v:-}` gives the value of the variable whose name is in `v`. When that value is not empty, the script prints a warning with the name and the value to the error output. The script goes on. |
| 78 | `done` | Ends the loop over the names of the test variables. |

### Stop controls: settings, `why_stop`, `check_marker`, `check_deadline`, the trap, `settle` (lines 80 to 107)

| Line | Source | Explanation |
|---:|---|---|
| 80 | `# ---- stop controls and host sampler: copied from run_bwx9.sh, unchanged ----` | Comment: the part from here to line 135 holds the stop controls and the start of the host sampler. By the comment it is an unchanged copy from the older script `run_bwx9.sh`. |
| 81 | `MARKER=${BWX8_MARKER:-/tmp/positron-perf.RUNNING}` | `MARKER`: the path of the marker file. It is `/tmp/positron-perf.RUNNING` unless the test variable `BWX8_MARKER` gives another path. `${X:-default}` gives the value of `X`, or the default when `X` is empty or not set. |
| 82 | `STOPFILE=${BWX8_STOPFILE:-$HOME/cache-perf/STOP}     # ours: "touch ~/cache-perf/STOP" from another login stops this script` | `STOPFILE`: the path of the stop file. It is `$HOME/cache-perf/STOP` unless `BWX8_STOPFILE` gives another path. The stop file is our own stop signal: the command `touch ~/cache-perf/STOP` from another login creates it, and the script then stops (line 97). |
| 83 | `[[ -n ${STOP_AT:-} ]] \|\| { echo "set STOP_AT to a UTC time like 2026-11-15T15:00Z, or to none" >&2; exit 2; }` | `-n` tests for a text that is not empty. When `STOP_AT` is empty or not set, the script prints a message that asks for a UTC time or for `none`, and ends with exit status 2. |
| 84 | `if [[ $STOP_AT == none ]]; then STOP_EPOCH=0; else STOP_EPOCH=$(date -u -d "$STOP_AT" +%s) \|\| { echo "bad STOP_AT" >&2; exit 2; }; fi` | `STOP_EPOCH`: the stop time as a number. With `STOP_AT=none` it is 0, which stands for no limit. In every other case `date -u -d "$STOP_AT" +%s` converts the text to a number of seconds, counted from 1970-01-01 00:00 UTC. When `date` cannot read the text, the script prints `bad STOP_AT` and ends with exit status 2. |
| 85 | `RESERVE=${RESERVE:-90}             # seconds: allocation, first touch, page reads and output of one process (est.)` | `RESERVE`: 90 s when the caller sets no value or an empty one. By the comment it is an estimate of the time that one process needs beside its kernel work: the allocation of the buffer, the first touch, the reads of the page state and the output. |
| 86 | `MARGIN=$RESERVE                    # seconds: set for each step to its longest process plus RESERVE` | `MARGIN`: a number of seconds. A process may start only when `STOP_AT` is more than `MARGIN` seconds away (line 102). It starts as `RESERVE`. The main loop sets it for each step to the longest process of the step plus `RESERVE` (line 240). |
| 87 | `CHILD=""; CUR_CSV=""; CUR_TAG=""  # the running benchmark, its csv file and its tag (set by one)` | `CHILD`: the process id of the running benchmark. It is empty when none runs. `CUR_CSV` and `CUR_TAG`: the output file and the tag of that benchmark. The function `one` sets the three variables. The trap of line 103 reads them. |
| 88 | `WATCH=""; WATCH_ON=0; CUR_CPU=""; CUR_MAXS=0   # the running host sampler; set per step and per process by the main loop` | `WATCH`: the process id of the running host sampler, empty when none runs. `WATCH_ON`: 1 when the step runs with the sampler. `CUR_CPU`: the CPU of the current process, which the sampler watches. `CUR_MAXS`: the time limit of the sampler, in seconds. |
| 89 | `# stop_watch: ends the host sampler of the current process, if one runs. The sampler also ends by itself.` | Comment: the function `stop_watch` ends the host sampler of the current process when one runs. The sampler also ends without this call, when the watched process is gone or when its time limit is over. |
| 90 | `stop_watch() { if [[ -n $WATCH ]]; then kill "$WATCH" 2>/dev/null \|\| true; wait "$WATCH" 2>/dev/null \|\| true; WATCH=""; fi; }` | Defines `stop_watch`. When `WATCH` is not empty: `kill` sends the termination signal (TERM) to the sampler, and `wait` waits until the sampler has ended. Then `WATCH` is emptied. `2>/dev/null` discards an error message, for example when the sampler has ended before. With `\|\| true`, such a failure does not make `set -e` stop the script. |
| 91 | `stop_child() { if [[ -n $CHILD ]]; then kill -- -"$CHILD" 2>/dev/null \|\| true; sleep 1; kill -9 -- -"$CHILD" 2>/dev/null \|\| true; wait "$CHILD" 2>/dev/null \|\| true; CHILD=""; fi; stop_watch; }` | Defines `stop_child`, which ends the running benchmark. The benchmark runs in its own process group (line 119). When `CHILD` is not empty: `kill -- -"$CHILD"` sends the termination signal to every process of that group. The minus sign before the id selects the group. After 1 s (`sleep 1`), `kill -9` sends the signal KILL to the group. No process can ignore that signal. `wait` then collects the ended benchmark, and `CHILD` is emptied. In every case the function calls `stop_watch` at its end. |
| 92 | `# why_stop: prints the reason and returns the exit status to use, or returns 0 if nothing asks us to stop.` | Comment: the function `why_stop` prints the reason for a stop and returns the exit status that the script must use. It returns 0 when nothing asks for a stop. |
| 93 | `# It is called in every turn of the wait and every second while a benchmark runs, so STOP_AT itself is` | Continues the comment: the script calls `why_stop` in every turn of the wait before a launch, and once per second while a benchmark runs. |
| 94 | `# enforced on a running benchmark. check_deadline adds the margin before a launch.` | Continues the comment: so the time `STOP_AT` also stops a benchmark that is running. Before a launch the function `check_deadline` asks for more: `STOP_AT` must be more than `MARGIN` seconds away. |
| 95 | `why_stop() {` | Starts the function `why_stop`. It tests three stop reasons in a fixed order: the marker file, the stop file, the time `STOP_AT`. |
| 96 | `  if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; return 3; fi` | `-e` tests whether a file exists. When the marker file exists, the function prints `RUNNING file present: stop` to the error output and returns 3. |
| 97 | `  if [[ -e $STOPFILE ]]; then echo "stop file $STOPFILE present: stop" >&2; return 5; fi` | When the stop file exists, the function prints `stop file`, the path and `present: stop`, and returns 5. |
| 98 | `  if (( STOP_EPOCH && $(date -u +%s) >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT reached: stop" >&2; return 4; fi` | When a stop time is set (`STOP_EPOCH` is not 0) and the current time in seconds (`date -u +%s`) has reached it, the function prints that `STOP_AT` is reached and returns 4. The shell starts one `date` process in every call, also when no stop time is set: it fills in `$( )` before it computes the expression. |
| 99 | `  return 0` | No stop reason exists: the function returns 0. |
| 100 | `}` | Ends the function `why_stop`. |
| 101 | `check_marker() { local rc=0; why_stop \|\| rc=$?; if (( rc )); then stop_child; exit $rc; fi; }` | Defines `check_marker`. It calls `why_stop` and keeps the return value in `rc` (`$?` is the status of the last command). When the value is not 0, the function ends a running benchmark with `stop_child` and ends the script with that value as the exit status: 3, 5 or 4. So the function tests all three stop reasons, not only the marker file. |
| 102 | `check_deadline() { if (( STOP_EPOCH && $(date -u +%s) + MARGIN >= STOP_EPOCH )); then echo "STOP_AT $STOP_AT is less than $MARGIN s away: stop" >&2; exit 4; fi; }` | Defines `check_deadline`. When a stop time is set and the current time plus `MARGIN` seconds reaches it, the script prints that `STOP_AT` is less than `MARGIN` s away, and ends with exit status 4. The message says less than, but the test also stops at exactly `MARGIN` seconds. So a process starts only when the time that is left is longer than the longest process of the step plus `RESERVE`. |
| 103 | `trap 'echo "interrupted: stopping the benchmark" >&2; if [[ -n $CHILD ]]; then echo "-- killed tag $CUR_TAG status 130 utc $(date -u +%T)" >> "$OUT/$CUR_CSV"; fi; stop_child; exit 130' INT TERM HUP` | `trap` sets what the script does when it gets one of the signals INT (Ctrl-C), TERM (termination) or HUP (the connection was closed). It prints `interrupted: stopping the benchmark`. When a benchmark runs, it appends the line `-- killed tag <tag> status 130 utc <time>` to the output file of the step. Then it ends the benchmark with `stop_child` and ends the script with exit status 130. |
| 104 | `# Wait until at most 2 tasks are runnable (field 4 of /proc/loadavg, before the slash), 20 s at most.` | Comment: the function `settle` waits until at most 2 tasks are runnable, for at most 20 s. The number is the part before the slash in the fourth field of the file `/proc/loadavg`. |
| 105 | `# The field is read with the shell builtin, so the check itself starts no process.` | Continues the comment: the shell reads the field with its own command `read`. So the reading starts no process. The call of `check_marker` in the same turn does start one `date` process (line 98). That process has ended before the field is read. |
| 106 | `# The marker and the stop file are checked in every turn. The wait is returned in WAITED.` | Continues the comment: every turn of the wait tests the marker file and the stop file. The code tests the time `STOP_AT` in the same turn (line 98). The function gives the waited time in the variable `WAITED`. |
| 107 | `settle() { local t=0 r; while :; do check_marker; read -r _ _ _ r _ < /proc/loadavg; r=${r%/*}; (( r <= 2 \|\| t >= 20 )) && break; sleep 2 & wait $! \|\| true; t=$((t+2)); done; WAITED=$t; }` | Defines `settle`, the wait for a quiet system before a launch. The loop has no end condition of its own (`while :`). Each turn first calls `check_marker`. Then `read` takes the fourth field of `/proc/loadavg`, for example `1/1019`, into `r`. `${r%/*}` cuts the slash and the text after it. The rest is the number of tasks that are runnable now. The loop ends when that number is 2 or less, or when 20 s have passed. If not, the script waits 2 s and adds 2 to `t`. `sleep 2 & wait $!` runs the sleep in the background and waits for it. A signal then ends the wait immediately, and the trap of line 103 runs. `WAITED` gets the waited time: 0 to 20 s. After 20 s the script goes on without a message. |

### Function `one`: one benchmark process (lines 108 to 136)

| Line | Source | Explanation |
|---:|---|---|
| 108 | `# one <csv> <idx> <tag> <benchmark options...>: one process, with a header line.` | Comment: the function `one` runs one benchmark process. Its arguments are the name of the output file, the `idx` of the process, its tag and the options of the benchmark. It writes a header line before the output of the process. |
| 109 | `one() {` | Starts the function `one`. |
| 110 | `  local csv=$1 idx=$2 tag=$3; shift 3` | Takes the first three arguments into the local variables `csv`, `idx` and `tag`. `shift 3` drops them. The arguments that are left (`$@`) are the options of the benchmark. |
| 111 | `  CUR_CSV=$csv; CUR_TAG=$tag` | Stores the output file and the tag for the trap of line 103. |
| 112 | `  check_marker; check_deadline` | First test before the launch: the three stop reasons (`check_marker`), then the distance to `STOP_AT` (`check_deadline`). |
| 113 | `  settle                                  # checks the marker in every turn` | Waits for a quiet system (`settle`): until at most 2 tasks are runnable, for at most 20 s. Each turn of the wait tests the stop reasons again. |
| 114 | `  # evidence for the load of this launch: users logged in and the 5 busiest processes` | Comment: the next line records the load of the machine at this launch: the number of logins and the 5 processes that use the most CPU time. The code takes the 5 processes with the highest `pcpu` value of `ps` (line 115). That value is an average over the whole life of a process. So a process that became busy only a short time ago can be missing from the list. |
| 115 | `  { echo "== $csv idx $idx $tag utc $(date -u +%T) loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l)"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6; } >> "$OUT/launches.txt"` | Appends the load record of this launch to `launches.txt` in the result folder. Its first line starts with `==`. It holds the output file, the `idx`, the tag, the UTC time (`date -u +%T` prints hours, minutes and seconds), the first four fields of `/proc/loadavg` and the number of logins. `who` prints one line per login, and `wc -l` counts the lines. Then come 6 lines of `ps`: a header and the 5 processes with the highest `pcpu` value. `-e` selects all processes. `-o pcpu,user,comm` prints `pcpu`, the user and the command name. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. `--sort=-pcpu` sorts from high to low, and `head -6` keeps the first 6 lines. The braces group the commands, and `>>` appends their output to the file. |
| 116 | `  check_marker; check_deadline            # again, directly before the launch` | Second test, directly before the launch: the stop reasons and the distance to `STOP_AT` again. The wait and the load record took time. |
| 117 | `  echo "-- step ${csv%.csv} session $SESSION idx $idx tag $tag waited_s $WAITED loadavg $(cut -d' ' -f1-4 /proc/loadavg) logins $(who \| wc -l) utc $(date -u +%T) args $*" >> "$OUT/$csv"` | Appends the header line of the process to the output file of the step. The line starts with `-- step`. It holds the step name (`${csv%.csv}` cuts the ending `.csv`), the session, the `idx`, the tag, the seconds that `settle` waited (`waited_s`), the first four fields of `/proc/loadavg`, the number of logins, the UTC time, and after the word `args` all options of the benchmark (`$*`). This is the last reading of the machine state before the process starts. |
| 118 | `  # run in an own process group; poll the marker and the stop file every second; kill the group if one appears` | Comment: the benchmark runs in its own process group. While it runs, the script tests the marker file and the stop file once per second. When one of them appears, the script ends the whole group. The code tests the time `STOP_AT` in the same place. |
| 119 | `  setsid "$BIN" "$@" >> "$OUT/$csv" 2>> "$OUT/stderr.txt" & CHILD=$!` | Starts the benchmark. `setsid` runs the binary `BIN` with the options (`"$@"`) in a new Linux session and a new process group. A Linux session is a set of process groups. It is not a session of the test. One signal to the new group reaches the benchmark and every process that it starts. The standard output of the benchmark is appended to the output file of the step. Its error output is appended to `stderr.txt` (`2>>`). `&` runs it in the background, and the script goes on. `CHILD` gets its process id (`$!`). The script measures no time. All timing happens inside the benchmark. |
| 120 | `  # The host sampler of this process: read-only on /proc, on its own CPU, never on a CPU of the schedule.` | Comment: the host sampler of this process only reads files under `/proc`. It runs on its own CPU, never on a CPU of the schedule. |
| 121 | `  if (( WATCH_ON )); then` | Tests whether the step runs with the host sampler. |
| 122 | `    taskset -c "${WATCH_CPU:-100}" python3 "$SRC/hostwatch.py" --pid "$CHILD" --cpu "$CUR_CPU" --out "$OUT/watch-$idx.txt" --max-s "$CUR_MAXS" >> "$OUT/watch-stderr.txt" 2>&1 & WATCH=$!` | Starts the host sampler in the background. `taskset -c` limits it to the CPU `WATCH_CPU`, or to CPU 100 when that variable is not set or is empty. `--pid`: the process id of the benchmark. `--cpu`: the CPU of the benchmark, from the schedule. `--out`: the file `watch-<idx>.txt` in the result folder. `--max-s`: the time limit `CUR_MAXS`, in seconds. The output of the sampler is appended to `watch-stderr.txt`, and `2>&1` sends its error messages to the same file. `WATCH` gets the process id of the sampler. |
| 123 | `  fi` | Ends the `if` of line 121. |
| 124 | `  local rc=0` | `rc`: the stop reason, or later the exit status of the benchmark. 0 means none. |
| 125 | `  while kill -0 "$CHILD" 2>/dev/null; do` | Starts the loop that waits for the benchmark. `kill -0` sends no signal. It only tests whether the process still exists. The loop runs while it exists. |
| 126 | `    why_stop \|\| rc=$?` | Once per turn: tests the three stop reasons and keeps the return value in `rc`. |
| 127 | `    if (( rc )); then echo "-- killed tag $tag status $rc utc $(date -u +%T)" >> "$OUT/$csv"; stop_child; exit $rc; fi` | When a stop reason exists: the script appends the line `-- killed tag <tag> status <rc> utc <time>` to the output file, ends the benchmark with `stop_child`, and ends with the exit status 3, 5 or 4. |
| 128 | `    sleep 1 & wait $! \|\| true` | Waits 1 s, in the form that a signal can end immediately. So the script tests the stop reasons once per second, and it sees the end of the benchmark up to about 1 s late. Each turn of this loop starts one `date` process (line 98) and one `sleep` process while the benchmark measures. They may run on any of the CPUs 0 to 119, also on the CPU of the benchmark thread. |
| 129 | `  done` | Ends the loop of line 125. |
| 130 | `  wait "$CHILD" \|\| rc=$?; CHILD=""` | The benchmark has ended. `wait` returns its exit status. A status other than 0 goes to `rc`. `CHILD` is emptied. |
| 131 | `  stop_watch` | Ends the host sampler of this process, when one runs. |
| 132 | `  if (( WATCH_ON )) && ! grep -q '^# end reason=' "$OUT/watch-$idx.txt" 2>/dev/null; then echo "warning: the sampler file watch-$idx.txt has no end line (see $OUT/watch-stderr.txt)" >&2; fi` | With a sampler only: `grep -q` tests, without output, whether the sampler file holds a line that starts with `# end reason=`. The sampler writes that line when it ends normally. When the line is missing, the script prints a warning that names the file and `watch-stderr.txt`. The script goes on. |
| 133 | `  if (( rc )); then echo "-- failed tag $tag exit $rc" >> "$OUT/$csv"; echo "benchmark failed ($tag, exit $rc): stop" >&2; exit 1; fi` | When the benchmark ended with a status other than 0: the script appends the line `-- failed tag <tag> exit <rc>` to the output file, prints `benchmark failed` with the tag and the status, and ends with exit status 1. The next process does not start. |
| 134 | `}` | Ends the function `one`. |
| 135 | `# ---- end of the copied part ----` | Comment: the copied part that began in line 80 ends here. |

### Paths of the binaries and the function `pick_bin` (lines 137 to 156)

| Line | Source | Explanation |
|---:|---|---|
| 137 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC`: the full path of the folder that holds this script. `dirname "$0"` gives the folder part of the path of the script. Inside the command substitution `$( )`, `cd` goes to that folder and `pwd` prints its full path. |
| 138 | `BIN8=${BWX8_BIN:-$HOME/cache-perf/bwx8-20261114/bwx8}   # the accepted binary of round 1` | `BIN8`: the path that the word `bwx8` stands for. It is the accepted binary of round 1, `$HOME/cache-perf/bwx8-20261114/bwx8`, unless the test variable `BWX8_BIN` gives another path. |
| 139 | `BIN10=${BWX10_BIN:-$HOME/cache-perf/bwx10-20261115/bwx10} # the accepted binary of round 3` | `BIN10`: the path that the word `bwx10` stands for. It is the accepted binary of round 3, `$HOME/cache-perf/bwx10-20261115/bwx10`, unless the test variable `BWX10_BIN` gives another path. |
| 140 | `BIN11=${BWX11_BIN:-$SRC/bwx11}` | `BIN11`: the path that the word `bwx11` stands for. It is the file `bwx11` in the folder of this script, unless the test variable `BWX11_BIN` gives another path. |
| 141 | `BIN=""                             # the binary of the current step (set by pick_bin)` | `BIN`: the path of the binary of the current step. It is empty until the function `pick_bin` sets it. |
| 142 | `# pick_bin: reads the word in sched11/s<SESSION>/<STEP_NAME>.bin and sets BIN_WORD and BIN.` | Comment: the function `pick_bin` reads the word in the file `sched11/s<SESSION>/<STEP_NAME>.bin`. It sets `BIN_WORD` to that word and `BIN` to the path of the binary. |
| 143 | `pick_bin() {` | Starts the function `pick_bin`. It finds the binary of the step whose name is in `STEP_NAME`. |
| 144 | `  local f=sched11/s$SESSION/$STEP_NAME.bin` | `f`: the path of the `.bin` file of the step, relative to the folder of this script. |
| 145 | `  [[ -r $f ]] \|\| { echo "missing $SRC/$f (the binary of step $STEP_NAME): stop" >&2; exit 2; }` | `-r` tests whether a file exists and is readable. When the `.bin` file is not readable, the script prints `missing`, the path and the step, and ends with exit status 2. |
| 146 | `  BIN_WORD=$(< "$f")` | `BIN_WORD`: the whole content of the file. `$(< file)` reads a file without starting a program and drops the newline at its end. |
| 147 | `  case $BIN_WORD in` | Compares the word with the names of the binaries. |
| 148 | `    bwx8) BIN=$BIN8 ;;` | The word `bwx8` selects the path `BIN8`. |
| 149 | `    bwx10) BIN=$BIN10 ;;` | The word `bwx10` selects the path `BIN10`. |
| 150 | `    bwx11) BIN=$BIN11 ;;` | The word `bwx11` selects the path `BIN11`. |
| 151 | `    *) echo "$SRC/$f must hold the one word bwx8, bwx10 or bwx11: stop" >&2; exit 2 ;;` | Any other content: the script prints that the file must hold the one word `bwx8`, `bwx10` or `bwx11`, and ends with exit status 2. So an empty file, two words, a path or a shell command cannot select a program. |
| 152 | `  esac` | Ends the `case` of line 147. |
| 153 | `}` | Ends the function `pick_bin`. |
| 154 | `RESULTS=${BWX8_RESULTS:-$HOME/cache-perf/results}` | `RESULTS`: the folder that holds the result folders. It is `$HOME/cache-perf/results` unless the test variable `BWX8_RESULTS` gives another path. |
| 155 | `cd "$SRC"                          # the plan paths in the schedules are relative to this folder` | Makes the folder of the script the working folder. The schedules name each plan file with a path that is relative to this folder, and the benchmark opens the plan with that path. |

### Checks before the first step (lines 157 to 201)

| Line | Source | Explanation |
|---:|---|---|
| 157 | `# ---- checks before the first step starts ----` | Comment: the checks from here to line 200 run before the first step starts. |
| 158 | `if (( SESSION == 2 && ! DRY )); then` | The checks of lines 159 to 165 apply to session 2 only, and not in a dry run. |
| 159 | `  [[ -n ${SESSION1_END:-} ]] \|\| { echo "session 2 needs SESSION1_END (UTC time of the end of session 1), and it is not set: stop" >&2; exit 2; }` | `SESSION1_END` must be set and not empty. If not, the script prints that session 2 needs the UTC time of the end of session 1, and ends with exit status 2. |
| 160 | `  # A full UTC time only: "date -d" also accepts a date without a time and relative words.` | Comment: the next line accepts a full UTC time only. The reason: `date -d` also accepts a date without a time, and relative words such as `yesterday`. |
| 161 | `  [[ $SESSION1_END =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z$ ]] \|\| { echo "bad SESSION1_END: write it as 2026-11-15T03:00Z or 2026-11-15T03:00:00Z" >&2; exit 2; }` | The value must match this pattern: 4 digits, a hyphen, 2 digits, a hyphen, 2 digits, the letter `T`, 2 digits, a colon, 2 digits, then an optional group of a colon and 2 digits (the seconds), then the letter `Z`. If not, the script prints `bad SESSION1_END` with the two allowed forms, and ends with exit status 2. |
| 162 | `  S1_EPOCH=$(date -u -d "$SESSION1_END" +%s) \|\| { echo "bad SESSION1_END" >&2; exit 2; }` | `S1_EPOCH`: the end of session 1 as a number of seconds, counted from 1970-01-01 00:00 UTC. When `date` cannot convert the text, for example for a day that does not exist, the script prints `bad SESSION1_END` and ends with exit status 2. |
| 163 | `  if (( $(date -u +%s) < S1_EPOCH + 10800 )); then` | Tests whether the current time is earlier than the end of session 1 plus 10800 s (3 hours). |
| 164 | `    echo "session 2 may start 3 hours after SESSION1_END $SESSION1_END at the earliest: stop" >&2; exit 2` | If so, the script prints that session 2 may start 3 hours after `SESSION1_END` at the earliest, and ends with exit status 2. |
| 165 | `  fi` | Ends the `if` of line 163. |
| 166 | `fi` | Ends the `if` of line 158. |
| 167 | `if [[ -n ${BWX_PMU_TYPE:-} && ! $BWX_PMU_TYPE =~ ^[0-9]+$ ]]; then echo "BWX_PMU_TYPE must be a whole number (the content of the type file of the core PMU)" >&2; exit 2; fi` | When `BWX_PMU_TYPE` is set and not empty, it must hold digits only. `!` negates the pattern test. When the value holds another character, the script prints that it must be a whole number and ends with exit status 2. |
| 168 | `for STEP_NAME in "${STEPS[@]}"; do` | Starts a loop over the step names of the call. It runs before any process starts, also in a dry run. For every step it checks that the schedule file can be read (line 169), and that the counter settings are given when a process of the step needs them (lines 170 to 180). A missing plan file and a defect in a row of the schedule are not found here. They are found when their step is reached. |
| 169 | `  [[ -r sched11/s$SESSION/$STEP_NAME.tsv ]] \|\| { echo "missing schedule $SRC/sched11/s$SESSION/$STEP_NAME.tsv (step $STEP_NAME): stop" >&2; exit 2; }` | The schedule file of the step, `sched11/s<SESSION>/<STEP>.tsv`, must be readable. If not, the script prints `missing schedule` with the path and the step, and ends with exit status 2. |
| 170 | `  # The counter settings must come from the environment only for a process that has neither` | Comment: the counter settings must come from the environment only for a process that has neither `--pmu-type` nor `--events` in its `args` column. |
| 171 | `  # --pmu-type nor --events in its args and whose plan has a trial with count open or read (field 10).` | Continues the comment: and whose plan has a trial with `count` equal to `open` or `read`. `count` is field 10 of a trial line of the plan. |
| 172 | `  NEED=()` | `NEED`: the list of the plan files that must be searched for a trial that uses the counters. It is empty at first. |
| 173 | `  while IFS=$'\t' read -r idx tag cpu bytes plan args; do` | Starts a loop over the rows of the schedule file. `IFS=$'\t'` splits each row at the tab characters into the six columns `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`. `-r` keeps each backslash as it is. |
| 174 | `    [[ $idx == idx \|\| $plan == - \|\| $args == *--pmu-type* \|\| $args == *--events* ]] && continue` | Skips a row (`continue`) in four cases: the header row, whose first column is the word `idx`. A row without a plan file, whose `plan` column is `-`. A row whose `args` hold the text `--pmu-type`. A row whose `args` hold the text `--events`. So a row that has only one of the two options is skipped too. |
| 175 | `    if [[ -r sched11/s$SESSION/$STEP_NAME/$plan ]]; then NEED+=("sched11/s$SESSION/$STEP_NAME/$plan"); fi` | When the plan file of the row is readable, its path is added to `NEED`. A missing plan file is reported later, by the function `load_step`. |
| 176 | `  done < "sched11/s$SESSION/$STEP_NAME.tsv"` | Ends the loop of line 173. `<` gives the schedule file of the step to the loop as its input. |
| 177 | `  if (( ${#NEED[@]} )) && awk '!/^#/ && ($10 == "open" \|\| $10 == "read") { f = 1; exit } END { exit !f }' "${NEED[@]}"; then` | Runs only when `NEED` holds at least one file. `awk` reads these plan files. For a line that does not start with `#` and whose field 10 (`count`) is `open` or `read`, it sets `f` to 1 and stops reading. Its exit status is 0 when such a line was found, and 1 if not (`exit !f`). So the `if` is true when a plan uses the counters and its schedule row gives no counter options. |
| 178 | `    for v in BWX_PMU_TYPE BWX_EVENTS; do [[ -n ${!v:-} ]] \|\| { echo "step $STEP_NAME needs $v, and it is not set: stop (see the head of this file)" >&2; exit 2; }; done` | In that case both `BWX_PMU_TYPE` and `BWX_EVENTS` must be set and not empty. When one is missing, the script prints that the step needs it and ends with exit status 2. |
| 179 | `    export BWX_PMU_TYPE BWX_EVENTS        # the binary reads them from its environment` | `export` puts the two variables into the environment of every program that the script starts. The benchmark reads them from there. |
| 180 | `  fi` | Ends the `if` of line 177. |
| 181 | `  pick_bin` | Calls `pick_bin` for this step. A missing `.bin` file or a wrong word stops the script here with exit status 2, before any process, also in a dry run. |
| 182 | `done` | Ends the loop of line 168. |
| 183 | `if (( ! DRY )); then` | The checks of lines 184 to 199 run in a real run only, not in a dry run. |
| 184 | `  for STEP_NAME in "${STEPS[@]}"; do` | Starts a second loop over the step names. It checks the files that a real run needs. |
| 185 | `    pick_bin` | Sets `BIN` and `BIN_WORD` for this step. |
| 186 | `    [[ -x $BIN ]] \|\| { echo "missing $BIN (the binary $BIN_WORD of step $STEP_NAME)" >&2; exit 2; }` | `-x` tests whether a file exists and is executable. When the binary is not, the script prints `missing` with the path, the word and the step, and ends with exit status 2. |
| 187 | `    [[ -r ${BIN%/*}/build.txt ]] \|\| { echo "missing ${BIN%/*}/build.txt (the record of the build of $BIN_WORD)" >&2; exit 2; }` | `${BIN%/*}` is the path of the binary without its last part, that is its folder. The file `build.txt` in that folder must be readable. If not, the script prints `missing` with the path, and ends with exit status 2. |
| 188 | `    case $BIN_WORD in bwx8) WANT=${BWX8_SHA256:-} ;; bwx10) WANT=${BWX10_SHA256:-} ;; *) WANT=${BWX11_SHA256:-} ;; esac` | `WANT`: the digest that the binary of this step must have. For the word `bwx8` it is the value of `BWX8_SHA256`, for `bwx10` the value of `BWX10_SHA256`, and for every other word (here only `bwx11`) the value of `BWX11_SHA256`. It is empty when that variable is not set. |
| 189 | `    if [[ -n $WANT ]]; then` | The digest check runs only when a digest was given. |
| 190 | `      [[ $(sha256sum < "$BIN" \| cut -d' ' -f1) == "$WANT" ]] \|\| { echo "$BIN_WORD ($BIN, step $STEP_NAME) is not the binary with the digest given for it: stop" >&2; exit 2; }` | `sha256sum` reads the binary from its input and prints the sha256 and a hyphen in the place of a file name. `cut -d' ' -f1` keeps the first field, the checksum. When it differs from `WANT`, the script prints that the binary is not the one with the digest given for it, and ends with exit status 2. This happens before the first process of the call. |
| 191 | `    fi` | Ends the `if` of line 189. |
| 192 | `    if [[ -e sched11/s$SESSION/$STEP_NAME.watch ]]; then` | Tests whether the file `sched11/s<SESSION>/<STEP>.watch` exists. If so, the step runs with the host sampler, and lines 193 to 196 check what the sampler needs. |
| 193 | `      command -v python3 > /dev/null \|\| { echo "step $STEP_NAME runs with the host sampler, and python3 is missing: stop" >&2; exit 2; }` | `command -v python3` tests whether a program with the name `python3` can be found. Its output goes to `/dev/null`, which discards it. When the program is missing, the script prints that the step runs with the host sampler and that `python3` is missing, and ends with exit status 2. |
| 194 | `      [[ -r $SRC/hostwatch.py ]] \|\| { echo "missing $SRC/hostwatch.py (the host sampler of step $STEP_NAME): stop" >&2; exit 2; }` | The file `hostwatch.py` in the folder of the script must be readable. If not, the script prints `missing` with the path, and ends with exit status 2. |
| 195 | `      # taskset can leave the CPUs 0-119 of this script, so the CPU of the sampler is checked here (never CPUs 120-127).` | Comment: `taskset` can place a program on a CPU outside the CPUs 0 to 119 to which this script is limited. So the CPU of the sampler is checked here. It must never be one of the CPUs 120 to 127. |
| 196 | `      { [[ ${WATCH_CPU:-100} =~ ^(0\|[1-9][0-9]{0,2})$ ]] && (( ${WATCH_CPU:-100} <= 119 )); } \|\| { echo "WATCH_CPU must be a CPU from 0 to 119: stop" >&2; exit 2; }` | `WATCH_CPU` (100 when it is not set or is empty) must match the pattern `^(0\|[1-9][0-9]{0,2})$`: the digit 0 alone, or a number of 1 to 3 digits that does not start with 0. It must also be 119 or less. If not, the script prints `WATCH_CPU must be a CPU from 0 to 119: stop` and ends with exit status 2. |
| 197 | `    fi` | Ends the `if` that tests for the `.watch` file. |
| 198 | `  done` | Ends the loop of line 184. |
| 199 | `  check_marker` | Tests the three stop reasons once before the first step. When the marker file or the stop file exists, or when `STOP_AT` is reached, the script ends here with exit status 3, 5 or 4. It has written no file at this point. |
| 200 | `fi` | Ends the `if` of line 183. |

### Function `load_step`: read a schedule and add up the nominal kernel work (lines 202 to 235)

| Line | Source | Explanation |
|---:|---|---|
| 202 | `# load_step: reads the schedule of STEP_NAME into arrays and adds up the nominal kernel work.` | Comment: the function `load_step` reads the schedule of the step `STEP_NAME` into arrays and adds up the nominal kernel work. |
| 203 | `# Work of a plan: previous activity + prefix + predecessor + windows x window length, over all trials.` | Continues the comment: the work of a plan is the sum over all its trials of four parts: the previous activity, the prefix, the predecessor, and the number of windows times the window length. |
| 204 | `# Work of a --seq process: entries of the sequence x rounds x min-ms.` | Continues the comment: the work of a process with `--seq` is the number of entries of its kernel sequence times the rounds times the `--min-ms` value. Such a process runs the interval mode of the runner and has no plan file. |
| 205 | `load_step() {` | Starts the function `load_step`. |
| 206 | `  local idx tag cpu bytes plan args ms a i seq rounds min c` | Declares the local variables of the function. |
| 207 | `  R_IDX=(); R_TAG=(); R_CPU=(); R_ARGS=(); R_MS=(); PLANS=()` | Empties the arrays. `R_IDX`, `R_TAG`, `R_CPU`, `R_ARGS` and `R_MS` get one entry per process: its `idx`, its tag, its CPU, its options and its nominal work in ms. `PLANS` gets the paths of the plan files. |
| 208 | `  P_N=0; P_SUM_MS=0; P_MAX_MS=0; RUN_N=0; RUN_SUM_MS=0; CONDS_SEQ=""` | Start values of the sums. `P_N`: the number of processes of the step. `P_SUM_MS`: their nominal work in ms. `P_MAX_MS`: the nominal work of the longest process. `RUN_N` and `RUN_SUM_MS`: the count and the sum for the processes that this call runs, those with an `idx` at or above `FROM`. `CONDS_SEQ`: the condition text of a step without plan files. |
| 209 | `  while IFS=$'\t' read -r idx tag cpu bytes plan args; do` | Starts the loop over the rows of the schedule file. Each row is split at the tab characters into the six columns. |
| 210 | `    [[ $idx == idx ]] && continue` | Skips the header row. |
| 211 | `    # idx, rounds and min-ms go into shell arithmetic, which would run a command written inside them.` | Comment: `idx`, the rounds and the `--min-ms` value are used in shell arithmetic. The shell would run a command that is written inside such a value. So the values are checked first. |
| 212 | `    [[ $idx =~ ^(0\|[1-9][0-9]*)$ ]] \|\| { echo "bad idx in $SRC/sched11/s$SESSION/$STEP_NAME.tsv: stop" >&2; exit 2; }` | `idx` must be `0` or a number that does not start with 0 (pattern `^(0\|[1-9][0-9]*)$`). If not, the script prints `bad idx in` with the path of the schedule, and ends with exit status 2. |
| 213 | `    # The cpu column is the CPU that the host sampler watches.` | Comment: the `cpu` column is the CPU that the host sampler watches. |
| 214 | `    [[ $cpu =~ ^(0\|[1-9][0-9]*)$ ]] \|\| { echo "bad cpu in $SRC/sched11/s$SESSION/$STEP_NAME.tsv (idx $idx): stop" >&2; exit 2; }` | The `cpu` column must be a whole number of the same form. If not, the script prints `bad cpu in` with the path and the `idx`, and ends with exit status 2. |
| 215 | `    if [[ $plan == - ]]; then` | A `-` in the `plan` column means a process without a plan file: a process of the interval mode with `--seq`. |
| 216 | `      read -ra a <<< "$args"; seq=""; rounds=1; min=0` | `read -ra a` splits the options at the blanks into the array `a`. `<<<` gives the text of `args` to `read` as its input. Start values: no sequence, 1 round, 0 ms. |
| 217 | `      for (( i = 0; i < ${#a[@]}; i++ )); do case ${a[i]} in` | Starts a loop over the words of the options. |
| 218 | `        --seq) seq=${a[i+1]} ;; --rounds) rounds=${a[i+1]} ;; --min-ms) min=${a[i+1]} ;; esac; done` | Takes the word after `--seq` as the kernel sequence, the word after `--rounds` as the number of rounds, and the word after `--min-ms` as the shortest time of one interval in ms. Then the line ends the `case` and the loop of line 217. |
| 219 | `      [[ $rounds =~ ^(0\|[1-9][0-9]*)$ && $min =~ ^(0\|[1-9][0-9]*)$ ]] \|\| { echo "bad --rounds or --min-ms in $SRC/sched11/s$SESSION/$STEP_NAME.tsv (idx $idx): stop" >&2; exit 2; }` | The rounds and the `--min-ms` value must be whole numbers. If not, the script prints `bad --rounds or --min-ms in` with the path and the `idx`, and ends with exit status 2. |
| 220 | `      c=${seq//[^,]/}; ms=$(( (${#c} + 1) * rounds * min ))` | `${seq//[^,]/}` removes every character that is not a comma. So the length of `c` is the number of commas, and the sequence has one entry more. `ms`: the entries times the rounds times the `--min-ms` value. This is the nominal work of the process in ms. |
| 221 | `      CONDS_SEQ="seq=$seq"` | Keeps the sequence as the condition text of the step. |
| 222 | `    else` | The other case: a process with a plan file. |
| 223 | `      plan=sched11/s$SESSION/$STEP_NAME/$plan` | `plan` becomes the path of the plan file, relative to the folder of the script. |
| 224 | `      [[ -r $plan ]] \|\| { echo "missing plan file $SRC/$plan: stop" >&2; exit 2; }` | The plan file must be readable. If not, the script prints `missing plan file` with the path, and ends with exit status 2. This happens before the first launch of the step. |
| 225 | `      ms=$(awk '!/^#/ { split($4, a, ":"); split($5, b, ":"); split($6, c, ":"); ms += a[2] + b[2] + c[2] + $8 * $9 } END { print ms + 0 }' "$plan")` | `awk` adds up the nominal work of the plan in ms. Each line that does not start with `#` is one trial. The fields 4, 5 and 6 are the previous activity, the prefix and the predecessor. Each is `-` or has the form `KERNEL@SIZE:MS`. `split` cuts each at the colon, and the three durations are added. Then field 8 times field 9 is added: the number of target windows times the window length in ms. `print ms + 0` prints the sum as a number, also for a plan without a trial. |
| 226 | `      PLANS+=("$plan")` | Adds the path of the plan file to the list `PLANS`. |
| 227 | `    fi` | Ends the `if` of line 215. |
| 228 | `    R_IDX+=("$idx"); R_TAG+=("$tag"); R_CPU+=("$cpu"); R_ARGS+=("$args"); R_MS+=("$ms")` | Appends the values of this process to the five arrays. |
| 229 | `    P_N=$((P_N+1)); P_SUM_MS=$((P_SUM_MS+ms)); (( ms > P_MAX_MS )) && P_MAX_MS=$ms` | Counts the process, adds its work to the sum of the step, and keeps the largest work of one process in `P_MAX_MS`. |
| 230 | `    if (( idx >= FROM )); then RUN_N=$((RUN_N+1)); RUN_SUM_MS=$((RUN_SUM_MS+ms)); fi` | When the `idx` is at or above `FROM`, this call runs the process. It is then counted in `RUN_N` and `RUN_SUM_MS` too. |
| 231 | `  done < "sched11/s$SESSION/$STEP_NAME.tsv"` | Ends the loop of line 209. The input of the loop is the schedule file of the step. |
| 232 | `  if (( ${#PLANS[@]} )); then CONDS=$(awk '!/^#/ { print $2 }' "${PLANS[@]}" \| sort -u \| tr '\n' ' ')` | With plan files: `CONDS` becomes the list of the conditions of the step. `awk` prints field 2, the condition label, of every trial line of all plan files. `sort -u` sorts the labels and drops duplicates. `tr` replaces each newline with a blank. So the list is one line. |
| 233 | `  else CONDS=$CONDS_SEQ; fi` | Without plan files: `CONDS` is the sequence text of line 221. `fi` ends the `if`. |
| 234 | `}` | Ends the function `load_step`. |

### Main loop: the summary of a step, and the dry run (lines 236 to 262)

| Line | Source | Explanation |
|---:|---|---|
| 236 | `for STEP_NAME in "${STEPS[@]}"; do` | Starts the main loop: one pass per step, in the order of the call. |
| 237 | `  pick_bin` | Sets `BIN` and `BIN_WORD` to the binary of this step. |
| 238 | `  load_step` | Reads the schedule of the step and computes its counts and its nominal work. |
| 239 | `  (( RUN_N )) \|\| { echo "step $STEP_NAME session $SESSION has no process with idx $FROM or above: stop" >&2; exit 2; }` | When no process has an `idx` at or above `FROM`, the script prints that the step has no such process, and ends with exit status 2. |
| 240 | `  MARGIN=$(( (P_MAX_MS + 999) / 1000 + RESERVE ))` | `MARGIN` for this step, in seconds: the nominal work of the longest process, rounded up to whole seconds, plus `RESERVE`. Adding 999 before the whole-number division by 1000 rounds up. |
| 241 | `  # Printed before execution, in a real run too (design line 356).` | Comment: the summary of lines 243 to 247 is printed before the first process of the step starts, in a real run too. The comment points to the design file `tackle-8mb.md`. That file asks that a runner print the selected conditions, the process count and the nominal work before execution. |
| 242 | `  (( DRY )) && echo "# ---- step $STEP_NAME session $SESSION ----"` | In a dry run only: prints a heading line with the step and the session. |
| 243 | `  printf 'step %s session %d: %d processes, nominal kernel work %d.%03d s (%d.%02d min); to run from idx %d: %d processes, %d.%03d s; longest process %d s, MARGIN %d s, waits between processes at most %d s more\n' \` | Prints the summary line of the step: the number of processes, the nominal kernel work of the whole step in seconds with three decimal places and in minutes with two, the `idx` from which this call runs, the number of processes and the nominal work that this call runs, the longest process in whole seconds, `MARGIN`, and the longest sum of the waits before the launches. The values follow in lines 244 to 245. The backslash at the end joins the next line to this command. |
| 244 | `    "$STEP_NAME" "$SESSION" $P_N $((P_SUM_MS/1000)) $((P_SUM_MS%1000)) $((P_SUM_MS/60000)) $((P_SUM_MS%60000/600)) \` | Continues the `printf` of line 243: the step, the session, `P_N`, and `P_SUM_MS` as whole seconds (`/1000`), the ms that are left (`%1000`), whole minutes (`/60000`) and hundredths of a minute (`%60000/600`). |
| 245 | `    $FROM $RUN_N $((RUN_SUM_MS/1000)) $((RUN_SUM_MS%1000)) $(( (P_MAX_MS+999)/1000 )) $MARGIN $((RUN_N*20))` | Continues the `printf` of line 243: `FROM`, `RUN_N`, `RUN_SUM_MS` as seconds and ms, the longest process rounded up to whole seconds, `MARGIN`, and `RUN_N*20`. The last value is 20 s for each process to run, the longest wait of `settle`. |
| 246 | `  echo "step $STEP_NAME selected conditions ($(wc -w <<< "$CONDS")): $CONDS"` | Prints the selected conditions of the step. `wc -w` counts the words of `CONDS`, that is the number of different conditions. The list follows. |
| 247 | `  echo "step $STEP_NAME binary: $BIN_WORD"` | Prints the word that names the binary of the step. |
| 248 | `  WATCH_ON=0` | The host sampler is off unless the next lines turn it on. |
| 249 | `  if [[ -e sched11/s$SESSION/$STEP_NAME.watch ]]; then` | Tests whether the file `sched11/s<SESSION>/<STEP>.watch` exists. If so, the step runs with the host sampler. |
| 250 | `    WATCH_ON=1` | Turns the host sampler on for this step. |
| 251 | `    echo "step $STEP_NAME host sampler: hostwatch.py on CPU ${WATCH_CPU:-100} beside each process, at most the nominal time of the process + 30 s"` | Prints that `hostwatch.py` runs on the CPU `WATCH_CPU` (100 when it is not set or is empty) beside each process, for at most the nominal time of the process plus 30 s. |
| 252 | `    for c in "${R_CPU[@]}"; do` | Starts a loop over the CPUs of all processes of the step. |
| 253 | `      [[ $c != "${WATCH_CPU:-100}" ]] \|\| { echo "WATCH_CPU ${WATCH_CPU:-100} is a CPU of the schedule of step $STEP_NAME: stop" >&2; exit 2; }` | When a CPU of the schedule is equal to `WATCH_CPU`, the script prints that `WATCH_CPU` is a CPU of the schedule, and ends with exit status 2. So the sampler never runs on a CPU that a benchmark uses. |
| 254 | `    done` | Ends the loop of line 252. |
| 255 | `  fi` | Ends the `if` that tests for the `.watch` file. |
| 256 | `  if (( DRY )); then` | The dry run: it prints the command lines and starts nothing. |
| 257 | `    for (( i = 0; i < ${#R_IDX[@]}; i++ )); do` | Starts a loop over the processes of the step. |
| 258 | `      (( R_IDX[i] < FROM )) && continue` | Skips a process whose `idx` is below `FROM`. |
| 259 | `      printf '%s %s  # idx %d, tag %s, nominal %d.%03d s\n' "$BIN_WORD" "${R_ARGS[i]}" "${R_IDX[i]}" "${R_TAG[i]}" $((R_MS[i]/1000)) $((R_MS[i]%1000))` | Prints one line per process: the word of the binary, the options from the `args` column, and after `#` the `idx`, the tag and the nominal work in seconds with three decimal places. |
| 260 | `    done` | Ends the loop of line 257. |
| 261 | `    continue` | Goes on with the next step. A dry run does nothing of lines 263 to 295. |
| 262 | `  fi` | Ends the `if` of line 256. |

### Main loop: result folder, `env.txt`, the processes of the step (lines 263 to 296)

| Line | Source | Explanation |
|---:|---|---|
| 263 | `  check_marker; check_deadline` | Before the result folder is made: tests the three stop reasons and the distance to `STOP_AT`, now with the `MARGIN` of this step. |
| 264 | `  OUT=$RESULTS/bwx11-$STEP_NAME-s$SESSION-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder of this step. Its name is `bwx11-`, the step, `-s`, the session, a hyphen and the UTC time of this moment in the form `YYYYMMDDTHHMMSSZ`. |
| 265 | `  mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders and reports no error when the folder exists. |
| 266 | `  echo "result folder: $OUT"` | Prints the path of the result folder. |
| 267 | `  cp "sched11/s$SESSION/$STEP_NAME.tsv" "$OUT/schedule.tsv"` | Copies the schedule file of the step into the result folder, with the name `schedule.tsv`. |
| 268 | `  cp "${BIN%/*}/build.txt" "$OUT/build.txt"` | Copies the build record `build.txt` from the folder of the binary into the result folder. |
| 269 | `  {` | Opens a group of commands. All their output goes to the file `env.txt` (line 279). |
| 270 | `    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg) logins=$(who \| wc -l) step=$STEP_NAME steps=${STEPS[*]}"` | First line of `env.txt`: the host name, the UTC date and time (`%FT%TZ` prints a form such as `2026-11-15T03:00:00Z`), the whole content of `/proc/loadavg`, the number of logins, this step, and all steps of the call. |
| 271 | `    echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag=$(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Second line: the setting of transparent huge pages (file `enabled`) and of their defragmentation (file `defrag`), both read from the folder `/sys/kernel/mm/transparent_hugepage/`. |
| 272 | `    echo "## uptime=$(cut -d' ' -f1 /proc/uptime) $(grep -E 'MemFree\|MemAvailable' /proc/meminfo \| tr -s ' ' \| tr '\n' ' ')"` | Third line: the time after the boot in seconds, which is the first field of `/proc/uptime`. Then the lines `MemFree` and `MemAvailable` of `/proc/meminfo`. `grep -E` selects the two lines, `tr -s ' '` reduces each run of blanks to one blank, and `tr '\n' ' '` joins the lines. |
| 273 | `    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6` | A heading line, then the header and the 5 processes with the highest `pcpu` value, from the same `ps` command as in line 115. |
| 274 | `    echo "## sha256:"; sha256sum "$BIN" "$SRC/run_bwx11.sh" "$SRC/sched11/s$SESSION/$STEP_NAME.tsv" "${BIN%/*}/build.txt"` | A heading line, then the sha256 of four files: the binary of the step, this script (`run_bwx11.sh`), the schedule file of the step and the build record. So the result folder shows which files ran. |
| 275 | `    if (( WATCH_ON )); then echo "## host sampler: WATCH_CPU=${WATCH_CPU:-100} $(python3 --version 2>&1) sha256 $(sha256sum < "$SRC/hostwatch.py" \| cut -d' ' -f1)"; fi` | With a host sampler only: one line with `WATCH_CPU`, the version of `python3` and the sha256 of `hostwatch.py`. |
| 276 | `    echo "## vmstat thp:"; grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat \|\| true` | A heading line, then three counters of `/proc/vmstat` at the start of the step: `thp_fault_alloc`, `thp_fault_fallback` and `thp_collapse_alloc`. They count the huge pages that Linux gave at a page fault, the page faults that got no huge page, and the huge pages that Linux built later from small pages. `\|\| true` keeps the script running when `grep` finds no such line. |
| 277 | `    echo "## settings: session=$SESSION from=$FROM SESSION1_END=${SESSION1_END:-} STOP_AT=$STOP_AT MARGIN=$MARGIN planned_processes=$P_N planned_nominal_ms=$P_SUM_MS to_run_processes=$RUN_N to_run_nominal_ms=$RUN_SUM_MS BWX8_SHA256=${BWX8_SHA256:-} BWX10_SHA256=${BWX10_SHA256:-} BWX11_SHA256=${BWX11_SHA256:-} binary=$BIN_WORD BWX_PMU_TYPE=${BWX_PMU_TYPE:-} BWX_EVENTS=${BWX_EVENTS:-} MARKER=$MARKER STOPFILE=$STOPFILE BIN=$BIN RESULTS=$RESULTS"` | The settings line: the session, `FROM`, `SESSION1_END`, `STOP_AT`, `MARGIN`, the number and the nominal ms of all processes of the step and of the processes that this call runs, the three digest settings, the word of the binary, the two counter settings, and the paths in use (`MARKER`, `STOPFILE`, `BIN`, `RESULTS`). |
| 278 | `    echo "## selected conditions: $CONDS"` | The last line of the group: the selected conditions of the step. |
| 279 | `  } > "$OUT/env.txt"` | Ends the group of line 269. `>` writes its output to a new file `env.txt` in the result folder. |
| 280 | `  if (( WATCH_ON )); then` | With a host sampler only: the start check of lines 283 to 285. |
| 281 | `    # Start check of the sampler, before the first process: 0.3 s on this script, on the CPU of the sampler.` | Comment: the start check of the sampler runs before the first process. The sampler watches this script for 0.3 s, on the CPU of the sampler. |
| 282 | `    # It finds a CPU that is not usable, a python3 that cannot run hostwatch.py, and a /proc that it cannot read.` | Continues the comment: the check finds a CPU that cannot be used, a `python3` that cannot run `hostwatch.py`, and a `/proc` that the sampler cannot read. |
| 283 | `    { taskset -c "${WATCH_CPU:-100}" python3 "$SRC/hostwatch.py" --pid $$ --cpu "${R_CPU[0]}" --out "$OUT/watch-selftest.txt" --max-s 0.3 >> "$OUT/watch-stderr.txt" 2>&1 \` | Runs the sampler once: on the CPU `WATCH_CPU`, with the process id of this script (`$$`) as the watched process, the CPU of the first schedule row as the watched CPU, the output file `watch-selftest.txt`, and a time limit of 0.3 s. Its messages are appended to `watch-stderr.txt`. |
| 284 | `      && grep -q '^# end reason=max_s .* errors=0$' "$OUT/watch-selftest.txt"; } \` | Continues the check: the sampler must end with status 0, and `watch-selftest.txt` must hold an end line that names the reason `max_s` (the time limit ended the run) and ends with `errors=0`. |
| 285 | `      \|\| { echo "step $STEP_NAME: the start check of the host sampler failed (see $OUT/watch-stderr.txt and watch-selftest.txt): stop" >&2; exit 2; }` | When one of the two conditions fails: the script prints that the start check of the host sampler failed, names the two files, and ends with exit status 2. |
| 286 | `  fi` | Ends the `if` of line 280. |
| 287 | `  for (( i = 0; i < ${#R_IDX[@]}; i++ )); do` | Starts the loop over the processes of the step, in the order of the schedule. |
| 288 | `    (( R_IDX[i] < FROM )) && continue` | Skips a process whose `idx` is below `FROM`. |
| 289 | `    read -ra ARGV <<< "${R_ARGS[i]}"` | Splits the options of the process at the blanks into the array `ARGV`. Each word becomes one argument of the benchmark. |
| 290 | `    CUR_CPU=${R_CPU[i]}; CUR_MAXS=$(( (R_MS[i] + 999) / 1000 + 30 ))` | `CUR_CPU`: the CPU of this process. `CUR_MAXS`: the time limit of the host sampler, in seconds. It is the nominal work of the process rounded up to whole seconds, plus 30 s. |
| 291 | `    one "$STEP_NAME.csv" "${R_IDX[i]}" "${R_TAG[i]}" "${ARGV[@]}"` | Runs the process with the function `one`: the checks, the wait, the load record, the header line, the launch and the wait for the end. The output file is `<STEP>.csv`. The script goes to the next process only when this one ended with status 0. |
| 292 | `  done` | Ends the loop of line 287. |
| 293 | `  echo "## end utc=$(date -u +%FT%TZ) loadavg=$(cat /proc/loadavg)" >> "$OUT/env.txt"` | After the last process: appends an end line to `env.txt` with the UTC time and the content of `/proc/loadavg`. |
| 294 | `  grep -E '^thp_(fault_alloc\|fault_fallback\|collapse_alloc) ' /proc/vmstat >> "$OUT/env.txt" \|\| true` | Appends the three huge page counters of `/proc/vmstat` again. The difference to the values of line 276 shows what changed during the step. |
| 295 | `  echo "$OUT"` | Prints the path of the result folder once more, as the last line of the step. |
| 296 | `done` | Ends the main loop of line 236. After the last step the script ends with exit status 0. |

## References

- [Ref1] the files `env.txt` of the 11 result folders `bwx11-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`. In each file the list after the line `## sha256:` gives `911644f1e8c8f7d6c9c4253910657347674593fcd5c32bff8d6cbf7ef75de2a8` for `run_bwx11.sh`. The file in the code folder has the same sha256.
