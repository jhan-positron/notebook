## Short version: purpose

`run_bwx.sh` runs the steps of Parts B and C of the test plan of 2026-11-13 on CRB: for each step of the call it starts a fixed list of processes of the first runner `bwx`, one at a time. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D [Ref3].
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan. Its sections B.1 to B.10 specify the runner `bwx`, the steps and the decision rules [Ref2].
- **`DEVIATIONS-scripts.md`**: a note of the writer of this script. It lists the points where the script adds to the handoff note or differs from it [Ref4].
- **Parts B and C**: the deciding measurements of the plan that need no root. They use the runner `bwx`. Part C also reads the counters of the cores. These are not the part C of the later rerun.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. Its run script is `run_partA.sh`. Its step A7 writes the type number and the event codes of the core counters to the file `A7-core-events.txt`. This is not the part A of the later rerun.
- **Step**: one named batch of processes of Parts B and C, for example `B7` or `C3`. A step function of this script, for example `step_B7`, lists the processes of the step.
- **`SHORT`**: a trial step: one short run of every kernel sequence, with intervals of at least 100 ms. No decision uses it.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **`bwx`, B3 binaries**: `bwx` is the first runner. `bwx_o0`, `bwx_o36` and `bwx_o52` are three more builds of it for step B3. Their copy loops are planned to start at 0, 36 and 52 modulo 64.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of this script**: `read`, `write` and `copy` are the new C kernels. `oldread` and `oldwrite` are the old C kernels. `asmread`, `asmwrite` and `asmcopy` are the hand-written kernels. `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2` are second copies of a kernel under another name. `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` are the hand-written copy kernels of step B2. `read_nop4`, `read_nop8`, `read_nop16`, `read_nop32` and `read_sparse` are load-only read kernels with added `nop` instructions, for step B5 [Ref2].
- **Kernel sequence, entry**: the list of kernels that one process times, in the option `--seq`. An entry is a kernel name, or a name with `@SIZE` for the first `SIZE` bytes of the buffer. Each entry gives one timed interval per round.
- **Process**: one start of a benchmark binary.
- **Tag, process index**: the tag is the short name of a process in its csv file, for example `pass-500-common-p1`. The process index is the number of a process among the processes of the same kind in a step, counted from 1. Every tag of a step other than `SHORT` ends with the letter `p` and this number.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Reference interval**: a term of the plan: an interval of `asmread` that is timed directly before or after the intervals that are compared [Ref3].
- **Rate**: bytes divided by time, in GB/s.
- **Pattern**: a term of the plan for the rates of the threads of one interval with many threads. In the split pattern the slowest thread has about half the rate of the fastest. In the uniform pattern all threads have nearly the same rate [Ref3].
- **Page state**: two values of a buffer from the Linux file `/proc/self/smaps`: the size of its mapping and the part of it on 2 MiB pages, both in kB of 1024 bytes.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Stop rule**: the option `--stop` of the runner. `--stop pass` selects the whole-pass stop. `--stop common` selects the common stop.
- **Start rule**: the option `--start` of the runner. With `--start common` every thread starts at the start of its buffer. With `--start offset` thread number i, counted from 0, starts at an offset of its own: i times 37, modulo the number of 2 MiB pieces of the range, times 2 MiB.
- **Setting**: one combination of stop rule, interval length and start rule, written `stop:min_ms:start`, for example `pass:500:common`.
- **Planned time**: the entries of the kernel sequence times the rounds times the `--min-ms` value of a process. It is the shortest total length of its timed intervals. The real run time is longer.
- **Warm-up pass**: one pass of the kernel of an interval that the runner makes before the interval. It is not timed.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **`a+b` threads**: `a` threads on mesh 0, on the CPUs 0 to `a-1`, and `b` threads on mesh 1, on the CPUs 64 to `64+b-1`.
- **Visit**: one login to CRB that runs one call of this script. The script `visit.sh` makes it.
- **Session 1, session 2**: the two runs of all steps of Parts B and C. The plan asks for 2 sessions some hours apart. This script has no setting for the session. This is not the session of the later rerun.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. A process starts only when this time is more than `MARGIN` seconds away, and a process that still runs at this time is ended. The value `none` sets no limit.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its timed intervals, 90 s when the variable is not set or is empty. `MARGIN` is the planned time of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Dry run**: a call with `--dry-run`. It prints what would run and starts nothing.
- **Output file, csv file, header line**: the output file of a step is the csv file `<STEP>.csv` in the result folder. Both halves of step B10 write a file with the name `B10.csv`. Before the output of each process the script writes a header line into the csv file. That line starts with `-- step`.
- **Load record**: the lines that the script appends to the file `launches.txt` before a launch: the first four fields of `/proc/loadavg`, the number of logins and the 5 processes with the highest `pcpu` value.
- **`pcpu`**: a value that the tool `ps` prints for a process: the CPU time of the process divided by the time from its start to now, in percent.
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
- **Linux session**: a set of process groups. The tool `setsid` starts a program in a new one. It is not a session of the test.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The header comment gives the usage, the settings and the exit statuses ({L1-23}).
2. Limit the script and everything that it starts to the CPUs 0 to 119 ({L24-25}).
3. Read the option `--dry-run` and the step names ({L26-33}).
4. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption ({L36-59}).
5. For each step of the call, check the settings that the step needs. In a real run also check that its binaries exist ({L115-119}).
6. In a real run, check the digest of `bwx` when `BWX_SHA256` is given, and test the stop reasons once ({L120-123}).
7. Define the kernel sequences and one step function per step. A step function lists the processes of its step as calls of the function `run` ({L147-252}).
8. For each step, call its step function in the mode `plan`: `run` counts the processes and adds up their planned times. Then compute `MARGIN` and print the summary line ({L254-260}).
9. In a dry run, go to the next step. The call in the mode `plan` has printed one command line per process ({L261}).
10. In a real run, test the stop reasons and the distance to `STOP_AT`, make the result folder and write `env.txt` ({L262-274}).
11. Call the step function again in the mode `exec`: `run` now runs each process with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line and starts the runner. Then it tests the stop reasons once per second until the runner ends ({L275-276}).
12. Append the end line to `env.txt` and print the path of the result folder ({L277-279}).
13. After the last step, end with exit status 6 when a process was skipped for lack of memory ({L281}).

## Behavior a reader must know

- What each step runs. Every process is one start of `bwx`. The exceptions are step B3 and up to three processes of `SHORT`, which start a B3 binary.
  - `B1` ({L165-168}): 64 processes with one thread: 4 for each of the sizes 4, 8, 16 and 32 MiB on each of the CPUs 0, 2, 41 and 94. The sequence `B1SEQ` (13 entries) in 4 rounds, intervals of at least 300 ms, whole-pass stop.
  - `B2` ({L169-172}): 48 processes with one thread at 8 MiB: 4 for each of the three kernel variants on each of the four CPUs. The B1 sequence with `copy` replaced by the variant, 4 rounds, 300 ms, whole-pass stop.
  - `B3` ({L173-176}): 48 processes with one thread at 8 MiB: 4 for each of the three B3 binaries on each of the four CPUs. The B1 sequence, 4 rounds, 300 ms, whole-pass stop.
  - `B4` ({L177-181}): 8 processes with one thread at 8 MiB on the CPUs 2 and 41: `asmread` alone in 200 rounds, 300 ms, whole-pass stop. On each CPU 2 processes run with `--no-thp` and 2 without.
  - `B6` ({L182-185}): 24 processes with one thread at 8 MiB: 8 on each of the CPUs 2, 41 and 94. The sequence `B6SEQ` (13 entries) in 4 rounds, 300 ms, whole-pass stop.
  - `B7` ({L186-193}): 48 processes with 120 threads and 256 MiB per thread. 32 of them run `B7SEQ` (8 entries) in 2 rounds: 4 for each of the 8 settings from the stop rules `pass` and `common`, the interval lengths 500 ms and 6000 ms, and the start rules `common` and `offset`. 16 of them run one kernel alone in 3 rounds with the setting `pass:500:common`: 4 for each of `oldread`, `read`, `asmread` and `asmread2`.
  - `B10a` and `B10b` ({L194-196}): 16 processes each, with 120 threads and 256 MiB per thread: `B10SEQ` (8 entries) in 2 rounds, 2 for each of the 8 settings with the interval lengths 500 ms and 15000 ms.
  - `B8` ({L197-200}): 2 processes for each entry of `B8_COUNTS`, with `a+b` threads and 256 MiB per thread: `B8SEQ` (6 entries) in 1 round, with the three timing settings of the caller.
  - `B5` ({L201-204}): 4 processes with 120 threads and 256 MiB per thread: the 9 entries of `B5SEQ` in 1 round, in the order forward, reverse, forward, reverse, with the three timing settings of the caller.
  - `B9` ({L205-210}): 6 processes with 120 threads and 256 MiB per thread: `oldread` alone in 3 rounds with the three timing settings of the caller. 3 of them have one buffer per thread and 3 have `--two-buffers`, alternating.
  - `C1` ({L211-214}): 4 processes: the B4 process without `--no-thp` and with `--count`, 2 on each of the CPUs 2 and 41.
  - `C2` ({L215-218}): 8 processes: the B1 process at 8 MiB with `--count`, 2 on each of the four CPUs.
  - `C3` ({L219-223}): processes with 120 threads and `--count`: 2 of the B7 sequence for each entry of `C3_B7_SETTINGS`, then the B5 sequence once forward and once in reverse.
  - `SHORT` ({L224-252}): up to 32 processes with intervals of at least 100 ms: one or more for each sequence above, the one-thread ones on CPU 2.
- Inside a step the process index is the outer loop ({L163-164}). So one process of every setting runs before the second process of any setting.
- Settings that a step needs, each without a default ({L111}): `B8_COUNTS` for B8. The timing settings `BWX_STOP`, `BWX_START` and `BWX_MIN_MS` for B8, B5, B9 and C3. `C3_B7_SETTINGS` for C3. The counter settings `BWX_PMU_TYPE` and `BWX_EVENTS` for C1, C2 and C3. The script exports the counter settings, and the runner reads them from its environment ({L97}).
- The script times nothing. All timing happens inside the runner.
- What the runner times in one interval (function `worker` of `bwx.c`). The stop rule decides how an interval ends.
  - Before the timed part each thread makes one warm-up pass with the kernel of the interval. In a process with one thread the thread then reads the page state of its buffers. Both are not timed.
  - With `--stop pass` the thread reads the clock, runs whole passes and reads the clock after each group of passes, until the `--min-ms` time has passed. A group is 8 MiB divided by the size of the range, rounded down, and at least 1 pass.
  - With `--stop common` all threads get one common start time and one common deadline, which is the start time plus the `--min-ms` value. Each thread waits for the start time and reads the clock. Then it calls the kernel on pieces of 2 MiB and reads the clock after each piece. It ends its interval at its first clock read at or after the deadline.
  - With `--stop common` the elapsed time of a thread can be a little shorter than the `--min-ms` value. The deadline counts from the common start time, and the thread reads its own start time later.
- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. The rule of {L54} is: stop when the current time plus `MARGIN` is at or after `STOP_AT`. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing or wrong setting, a missing binary or a wrong digest of `bwx`: status 2.
- A seventh thing stops the run without a message of the script. With `set -e` ({L24}) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder ({L264}) or when `env.txt` cannot be written ({L266-274}). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- One more exit status does not stop the run. When a process was skipped for lack of memory, the script still runs all steps of the call. Then it prints a message and ends with status 6 ({L281}).
- All checks with status 2 run before the first step of the call ({L27-32}, {L38-39}, {L115-121}). A setting that only a later step needs is checked there too.
- The plan of a step, its summary line and its stop tests come when the main loop reaches the step ({L254-262}). So in a call with several steps the summary of a later step is printed after the earlier steps have run.
- The first three stop reasons are tested in a fixed order: the marker file, then the stop file, then `STOP_AT` ({L47-52}). When two of them hold, the first one gives the exit status.
- The first three stop reasons are tested at these places: once before the first step ({L123}), once before each result folder is made ({L262}), twice before each launch ({L63}, {L67}), in every turn of the wait for a quiet system ({L59}), and once per second while a process runs ({L73}).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later ({L43}). After a stop by the marker file, the stop file or `STOP_AT`, the csv file gets a line that starts with `-- killed` ({L74}). After an interruption by a signal it gets no such line ({L55}).
- Before a launch the script waits until at most 2 tasks are runnable. The shell that reads the count is itself one of these tasks. The script tests the count every 2 s, for at most 20 s. After 20 s it starts the process without a message ({L59}). There is no fixed pause. The header line of the process records the waited seconds as `waited_s` ({L68}).
- The wait looks only at the tasks that are runnable at that moment. It does not look at the load averages. So directly after a process with 120 threads the next header line can show a high load average together with `waited_s 0`.
- For each launch the script records the load in two places. `launches.txt` gets a line with the first four fields of `/proc/loadavg` and the number of logins, and the 5 processes with the highest `pcpu` value ({L66}). The header line of the process in the csv file gets the waited seconds, the first four fields of `/proc/loadavg`, the number of logins, the UTC time and the options ({L68}).
- The load averages of these records include the benchmark processes of this script that ran in the minutes before. So from the second process on they do not show the load of other users alone.
- The list of the 5 processes does not show which processes are busy at the launch. `pcpu` is an average over the whole life of a process, not the CPU use of the last second.
- While a benchmark runs, the script starts one `date` process and one `sleep` process per second ({L50}, {L75}). They may run on any of the CPUs 0 to 119. In a process with 120 threads each of these CPUs also runs one pinned benchmark thread.
- The script pins no benchmark thread. It only limits itself and everything that it starts to the CPUs 0 to 119 ({L25}). A caller that has already set `_PINNED` to a text that is not empty gets no such limit. The runner pins thread number i to entry i of its `--cpus` list.
- The file `env.txt` records the state of the machine at the start of a step, the sha256 of the binaries that exist and of this script, and the settings ({L266-274}). The end of the step adds the UTC time, the content of `/proc/loadavg` and three huge page counters ({L277-278}).
- A result folder holds four files: the csv file with the header line and the output of every process, `launches.txt`, `env.txt`, and `stderr.txt` with the error output of the runner. Each step of a call gets its own result folder.
- A process that ends with a status other than 0 gets a line that starts with `-- failed` in the csv file ({L78}). The script does not test the output of a process. It tests the exit status only.
- Memory check: in a real run step B9 runs only when at least 70 GiB of memory are available. If not, all 6 processes of B9 are skipped, also the 3 with one buffer ({L206}). In `SHORT` only the process with two buffers is skipped ({L242}). Both cases write a message to `env.txt` and give exit status 6 at the end.
- `SHORT` leaves out a run without a change of the exit status in two cases: a B3 binary is missing ({L231}), or a counter setting is not set or is empty ({L250}). The message stands in `env.txt`.
- The digest check covers only `bwx`, and only when `BWX_SHA256` is given ({L120-121}). The script holds no expected digest of its own, and the three B3 binaries are not checked. `env.txt` records the sha256 of every binary that exists ({L271}).
- A value of the form `${X:-default}` is the default when the variable `X` is not set or is empty. The script uses this form for `RESERVE` ({L40}) and, in a dry run, for `STOP_AT` ({L33}).
- A dry run needs the settings of the steps that it names. It does not test the binaries, the digest or the stop reasons ({L118}, {L120}, {L123}).
- The path of the marker file and the place of the result folders are fixed in the file ({L36}, {L263}). The script has no test variable for them.
- The script does not test whether the call names a step twice. Such a step runs twice, each time into its own result folder ({L29}).
- The script cannot continue a step at one of its processes. A step that was stopped runs again from its first process when a later call names it.
- The script deletes nothing. At every stop the files that were written before stay.
- The exit status is 0 only when every step of the call ran to its end and no process was skipped for lack of memory, or after a dry run.
- The script `visit.sh` starts this script on CRB through `ssh`, with `STOP_AT`, `BWX_SHA256` and the settings of the caller. The script `session2.sh` calls `visit.sh` seven times for session 2.
- The text of this file is the text that ran on CRB in all steps of Parts B and C [Ref1]. The words `Never run on CRB` of {L23} are older than those runs.

## References

- [Ref1] the files `env.txt` of the 29 result folders of this script in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the folder `SHORT-20261113T214338Z` and 28 step folders, 2 for each of the 14 other step names, for example `B7-20261113T232859Z`. In each file the list after the line `## sha256:` gives `b52725d29ab3a80a4f37293916e99007421896367ea90ab4110a6824aa7b98ee` for `run_bwx.sh`. The file in the code folder has the same sha256.
- [Ref2] the file `report/handoff.md` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`, the handoff note. Its section B.1 lists the kernels of `bwx`, B.2 its options, B.4 the two stop methods and B.5 the start offsets. B.8 asks for a short counter test with one thread at 32 KiB. B.9 gives the sequence, the options and the number of processes of each step, the rule `Order of the processes` and the rule `Settings after B7`. Its section `Order of work` asks in step 2 for one short run of every sequence with `--min-ms 100`. Its section `Stop controls` says that in each of four stop cases the script writes a line `-- killed` into the csv file if a benchmark was running.
- [Ref3] the file `report/plan.md` in the same folder, the plan. Its tables of Part B say what each step runs and which prediction it tests. Its table of Part C says what each step runs and what it gives. Its list of terms defines the reference interval, the split pattern and the uniform pattern. Its row of step B7 defines the reproduction condition.
- [Ref4] the file `DEVIATIONS-scripts.md` in the folder of this script, a note of the writer of the script. Its table `Run script` lists 20 points, S1 to S20, where the script adds to the handoff note or differs from it. Point S4 is about the counter settings in the environment, and point S19 is about the missing `-- killed` line after an interruption.
