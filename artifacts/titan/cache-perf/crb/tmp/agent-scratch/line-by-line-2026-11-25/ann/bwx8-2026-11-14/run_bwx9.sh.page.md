## Short version: purpose

`run_bwx9.sh` runs the steps of round 2 on CRB: for each step it starts the processes of a schedule file one at a time with the runner `bwx8`, and for some steps it runs a host sampler beside each process. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1, round 2**: the first and the second set of tests of the investigation into the buffer size of 8 MiB. The steps of round 2 have names that start with `X`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **`bwx8`**: the runner version that round 1 and round 2 use. Round 2 starts the binary that lies beside this script.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **Visit**: one login to CRB that starts one script.
- **Step**: one batch of processes of a round, for example `XW`. One schedule file lists its processes.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **Generator**: the program `schedule9.py`. It writes the schedules, the plan files and the `.watch` files of round 2.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **`.watch` file**: the empty file `<STEP>.watch` of a step. When it exists, the step runs with the host sampler.
- **Host sampler**: the program `hostwatch.py`. It records what the Linux kernel does on one CPU while one process runs.
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
- **Start check**: a run of the host sampler of 0.3 s that the script makes before the first process of a step with a sampler. The sampler then watches the script itself.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the part of a core that holds the hardware counters.
- **Counter device**: the hardware counters of the CPU cores, as Linux lists them. Linux gives the device a type number. The option `--pmu-type` and the variable `BWX_PMU_TYPE` carry that number.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Process group**: a set of processes that one signal can reach together.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The header comment gives the usage, the settings and the exit statuses ({L1-44}).
2. Limit the script and everything that it starts to the CPUs 0 to 119 ({L45-46}).
3. Read the options and the step names, and check `SESSION` ({L47-59}).
4. Print a warning for each test variable that is set ({L61-63}).
5. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption ({L66-88}).
6. Set the path of the binary `bwx8` and the place of the result folders, and make the folder of the script the working folder ({L122-125}).
7. For session 2, refuse a start earlier than 3 hours after `SESSION1_END` ({L128-136}).
8. For each step, check the schedule file and the counter settings ({L137-151}).
9. In a real run, check the binary, its `build.txt`, its digest and what the host sampler needs. Then test the stop reasons once ({L152-167}).
10. For each step, read the schedule with `load_step`, compute the nominal work and `MARGIN`, print the summary, and turn the host sampler on when the step has a `.watch` file ({L203-220}).
11. In a dry run, print one command line per process and go to the next step ({L221-227}).
12. In a real run, test the stop reasons and the distance to `STOP_AT`, make the result folder and write `schedule.tsv`, `build.txt` and `env.txt` ({L228-244}).
13. With a host sampler, run its start check ({L245-251}).
14. Run the processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line, starts the runner and, when the sampler is on, the sampler beside it. Then it tests the stop reasons once per second until the runner ends ({L252-257}).
15. Append the end line to `env.txt` and print the path of the result folder ({L258-260}).

## Behavior a reader must know

- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. The rule of {L87} is: stop when the current time plus `MARGIN` is at or after `STOP_AT`. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing setting or file, a wrong digest, or a session 2 that would start too early: status 2.
- A seventh thing stops the run without a message of the script. With `set -e` ({L45}) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder or `cp` cannot write its copy ({L230-233}). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- Most checks with status 2 run before the first process of the call ({L48-58}, {L68-69}, {L128-165}). Four run later, when their step is reached and before its first process: a defect in a row of the schedule or a missing plan file ({L176-198}), a `--from` value past the last `idx` ({L205}), a `WATCH_CPU` that is a CPU of the schedule ({L218}), and a failed start check of the host sampler ({L248-250}). So in a call with several steps such a defect of a later step stops the run after the earlier steps have run.
- The steps run in the order in which the call names them ({L203}). The note `DECISIONS-bwx8.md` gives the planned order of a session of round 2: `XEV` in a visit of its own, in session 1 only, then `XW`, `XCA`, `XCB`, `XCC`, `XN` and `XF`.
- The first three stop reasons are tested in a fixed order: the marker file, then the stop file, then `STOP_AT` ({L80-85}). When two of them hold, the first one gives the exit status.
- The first three stop reasons are tested at these places: once before the first step ({L166}), once before each result folder is made ({L228}), twice before each launch ({L97}, {L101}), in every turn of the wait for a quiet system ({L92}), and once per second while a process runs ({L111}).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later ({L76}). Before that, the script appends a line that starts with `-- killed` to the output file of the step ({L88}, {L112}). The host sampler of the process is ended too ({L75}).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message ({L92}). There is no fixed pause. The header line of the process records the waited seconds as `waited_s` ({L102}).
- For each launch the script records the load in two places. `launches.txt` gets a line with the first four fields of `/proc/loadavg` and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` ({L100}). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in `<STEP>.csv` gets the waited seconds, the first four fields of `/proc/loadavg`, the number of logins, the UTC time and the options ({L102}).
- The file `env.txt` records the state of the machine at the start of a step and the sha256 of the binary, of this script, of the schedule and of `build.txt` ({L234-244}). The end of the step adds the UTC time, the content of `/proc/loadavg` and three huge page counters ({L258-259}).
- A result folder holds these files: `<STEP>.csv` with the header line and the output of every process, `launches.txt`, `env.txt`, `stderr.txt` with the error output of the runner, and the copies `schedule.tsv` and `build.txt`. A step with the sampler adds one file `watch-<idx>.txt` per process, `watch-selftest.txt` and `watch-stderr.txt`.
- A process that ends with a status other than 0 gets a line that starts with `-- failed` in `<STEP>.csv` ({L118}). The script does not test the output of a process. It tests the exit status only.
- The script times nothing. All timing happens inside the runner.
- The script pins no benchmark thread. It only limits itself and everything that it starts to the CPUs 0 to 119 ({L46}). A caller that has already set `_PINNED` to a text that is not empty gets no such limit. The schedule row gives the runner its CPU with the option `--cpus`.
- In a step with a `.watch` file a second program runs while each process measures: the host sampler. It starts directly after the runner ({L107}) and is ended after the runner has ended ({L116}). It runs on the CPU `WATCH_CPU`, which is CPU 100 when the variable is not set or is empty. That CPU must be one of the CPUs 0 to 119 ({L163}) and must not be a CPU of the schedule ({L218}).
- The sampler has a time limit of its own: the nominal work of the process, rounded up to whole seconds, plus 30 s ({L255}). A sampler file without an end line gives a warning only, and the run goes on ({L117}).
- A value of the form `${X:-default}` is the default when the variable `X` is not set or is empty. The script uses this form for `WATCH_CPU`, `RESERVE` and the four test variables.
- The generator `schedule9.py` writes a plan file for every process of round 2. So the branch of `load_step` for a row without a plan file ({L182-188}) is not used by its schedules.
- A dry run needs `SESSION`, the schedule files and the plan files. It does not test the binary, `build.txt`, the digest, the stop reasons or the 3 hour rule of session 2 ({L128}, {L152}).
- The script never repeats a process. A stopped step is continued with `--from IDX`, in a new result folder.
- The script deletes nothing. At every stop the files that were written before stay.
- The exit status is 0 only when every step of the call ran to its end.
- The text of this file is the text that ran on CRB in round 2 [Ref1].

## References

- [Ref1] the files `env.txt` of the 13 result folders `bwx9-<step>-s<session>-<UTC>` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`, for example `bwx9-XW-s1-20261115T052114Z`. In each file the list after the line `## sha256:` gives `142c24a2dcdde6b1830d1b9e3a3381b00da9d350cf795eff384da8eb2ff5265a` for `run_bwx9.sh`. The file in the code folder has the same sha256.
