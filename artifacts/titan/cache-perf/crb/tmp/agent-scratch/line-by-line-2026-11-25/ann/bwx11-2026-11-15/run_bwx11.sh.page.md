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

1. The header comment gives the usage, the settings and the exit statuses ({L1-59}).
2. Limit the script and everything that it starts to the CPUs 0 to 119 ({L60-61}).
3. Read the options and the step names, and check `SESSION` ({L62-74}).
4. Print a warning for each test variable that is set ({L76-78}).
5. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption ({L81-103}).
6. Set the paths of the three runners and make the folder of the script the working folder ({L137-155}).
7. For session 2, refuse a start earlier than 3 hours after `SESSION1_END` ({L158-166}).
8. For each step, check the schedule file, the counter settings and the `.bin` file ({L167-182}).
9. In a real run, check each binary, its `build.txt`, its digest and what the host sampler needs. Then test the stop reasons once ({L183-200}).
10. For each step, read the schedule, compute the nominal work and `MARGIN`, and print the summary ({L236-255}).
11. In a dry run, print one command line per process and go to the next step ({L256-262}).
12. In a real run, make the result folder and write `schedule.tsv`, `build.txt` and `env.txt` ({L263-279}).
13. With a host sampler, run its start check ({L280-286}).
14. Run the processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line, starts the runner, and tests the stop reasons once per second until the runner ends ({L287-292}).
15. Append the end line to `env.txt` and print the path of the result folder ({L293-296}).

## Behavior a reader must know

- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing setting or file, a wrong digest, or a session 2 that would start too early: status 2. Most of these checks run before the first process of the call. The checks of one step run when that step starts: the schedule rows and the plan files ({L212-224}), the test that a process is left to run ({L239}), the test that `WATCH_CPU` is no CPU of the schedule ({L253}) and the start check of the host sampler ({L283-285}). In a call with several steps the earlier steps have run by then.
- A seventh thing stops the run without a message of the script. With `set -e` ({L60}) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder or `cp` cannot write its copy ({L265-268}). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- The first three stop reasons are tested at these places: once before the first step ({L199}), once before each result folder is made ({L263}), twice before each launch ({L112}, {L116}), in every turn of the wait for a quiet system ({L107}), and once per second while a process runs ({L126}).
- A process that runs at a stop is ended. First the script appends a line that starts with `-- killed` to the output file ({L103}, {L127}). Then the signal TERM goes to the process group of the process, and the signal KILL follows 1 s later ({L91}).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message ({L107}). There is no fixed pause.
- For each launch the script records the load in two places. `launches.txt` gets a line with the load averages and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` ({L115}). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in `<STEP>.csv` gets the waited seconds, the load averages, the number of logins, the UTC time and the options ({L117}).
- The script times nothing. All timing happens inside the runner.
- The script never repeats a process. A stopped step is continued with `--from IDX`, in a new result folder.
- The script deletes nothing. At every stop the files that were written before stay.
- The script and the runner may use the CPUs 0 to 119 only ({L61}). A caller that has already set `_PINNED` to a text that is not empty gets no such limit. The host sampler gets its own CPU from `taskset`, and {L196} keeps that CPU at 119 or below.
- The exit status is 0 only when every step of the call ran to its end.
- The text of this file is the text that ran on CRB in round 4 [Ref1].

## References

- [Ref1] the files `env.txt` of the 11 result folders `bwx11-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`. In each file the list after the line `## sha256:` gives `911644f1e8c8f7d6c9c4253910657347674593fcd5c32bff8d6cbf7ef75de2a8` for `run_bwx11.sh`. The file in the code folder has the same sha256.
