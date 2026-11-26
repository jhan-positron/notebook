## Short version: purpose

`test_schedule9.py` checks the four scripts of round 2 without CRB: the generator `schedule9.py`, the host sampler `hostwatch.py`, the run script `run_bwx9.sh` and the visit script `visit9.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, it runs the sampler beside busy test processes, and it runs the run script with a dummy binary through these stop cases: the marker file, the stop file, a signal, `STOP_AT` and a failing process. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1, round 2**: the first and the second set of tests of the investigation into the buffer size of 8 MiB. The steps of round 2 have names that start with `X`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_nop16`, `read_nop32`**: two kernels of the runner `bwx8`. Each is the `asmread` loop with 16 or 32 `nop` instructions added to each loop pass of 256 B. A `nop` is an instruction that does nothing.
- **`read_sparse`**: a kernel of the runner `bwx8`. Each loop pass handles 128 B with 4 `ldp q` loads and 9 `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule9.py`. It writes the schedules, the plan files and the `.watch` files of round 2.
- **Run script**: the script `run_bwx9.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit9.sh`. It makes one login to CRB and starts the run script there.
- **Host sampler**: the program `hostwatch.py`. It records what the Linux kernel does on one CPU while one process runs. The run script starts it beside a process when the step has a `.watch` file.
- **Step**: one batch of processes of a round, for example `XW`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **`.watch` file**: the empty file `<STEP>.watch` of a step. When it exists, the step runs with the host sampler.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan. In `XW` it is one target kernel at one size with or without a previous activity.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, block**: a replicate set is one run of every kernel of step `XN` for one size and CPU. A block is the group of processes of one replicate on one CPU in the other steps.
- **Event set**: one of the three lists A, B and C of 6 counter events each.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters at the boundaries of the target windows.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`--pmu-type`, `--events`**: the two counter options of the runner. `--pmu-type` gives the type number that Linux gives to the counter device of the cores, 11 on CRB by the notes of the project. `--events` gives the list of counter events, each as a name and a code. The variables `BWX_PMU_TYPE` and `BWX_EVENTS` carry the same two values in the environment.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Stand-in**: a program that takes the place of another one in the test. The stand-in runner is built from the runner source on the local machine. Its kernels are plain C loops, and its rates mean nothing.
- **Dummy binary**: a small shell script that stands in for the runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Box**: the test setup of the run script: a copy of the script and of the sampler, the dummies and a schedule in a temporary folder.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts a process only when this time is more than `MARGIN` seconds away, and it ends a process that still runs at this time.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Sample**: one reading of all watched files of the sampler at one time.
- **Key**: the name of one value in the output of the sampler, for example `w.run_ns`. The prefix `m.` stands for the main thread of the watched process and `w.` for its worker thread.
- **Absolute line**: a sample line with the word `ABS` that holds the full value of every key.
- **Delta line**: a sample line that holds only the values that changed, each as a difference to the last sample.
- **State item**: an item of the form `key:=value`. It gives a new state and not a difference.
- **Scan**: one pass of the sampler over all threads of the host. It finds the threads of other processes whose last CPU is the watched CPU.
- **Footer**: the last line of a sampler file. It starts with `# end reason=` and gives the reason of the end and four values: the samples taken, the sample times that were missed, the longest time of one sample in microseconds, and the errors.
- **Context switch**: the moment at which Linux takes a thread off a CPU. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU away.
- **Time slice**: one uninterrupted period in which a thread runs on a CPU.
- **Clock tick**: the unit in which Linux reports the CPU time and the start time of a process. `SC_CLK_TCK` gives the number of ticks per second.
- **Soft interrupt**: a piece of work that the Linux kernel puts off to a later moment, for example work for timers or for the network.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file of a step is `<STEP>.csv` in the result folder. Before the output of each process the run script writes a header line into it. That line starts with `-- step`.
- **Load record**: the lines that the run script appends to the file `launches.txt` before a launch: the load averages, the number of logins and the 5 processes with the highest `pcpu` value of `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent.
- **Start check**: a run of the host sampler of 0.3 s that the run script makes before the first process of a step with a sampler.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. The values that the task expects are written as fixed values: the counts and the nominal work, the steps with a `.watch` file, the event sets, the conditions, the kernels and the sizes of each step ({L37-54}).
2. The helper `check` prints one line per check and collects the failures ({L60-66}).
3. The validator of the plan format and the reader of a generated folder ({L69-151}, {L154-197}).
4. The rules of the steps, in four functions: one for `XW`, one for the three counter steps, one for `XN` and one for `XF` ({L233-365}). The step `XEV` has no rule function. One check of group 1 tests the form of its processes ({L479-485}).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.watch` files, the effect of the seed, the saved folder and the test divisor ({L368-567}).
6. Group 2, `bwx8_checks`: a locally built `bwx8` accepts all 635 plans of both sessions in their form with the test divisor 100, refuses three damaged plans, and refuses the plan of `XEV` without its event options ({L571-648}).
7. Group 3, `hostwatch_checks`: the host sampler beside a busy test process: the header, the absolute line, whole-file reads, errors inside the sampler, the sample rate, a shared CPU, the time limit, a signal, a missing process, a missing CPU, the usage and the source text ({L686-841}).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit8.sh` ({L992-1032}).
9. Group 5, `run_checks`: the run script with a dummy binary: syntax, comparison of the stop controls with `run_bwx8.sh`, step names and the dry run, a normal run, the counter settings, the host sampler, the stop controls with and without a sampler, `MARGIN`, session 2 and other refusals ({L1035-1372}).
10. `main` prints the system load, runs the groups in this order, removes the temporary folder and prints the summary ({L1375-1397}).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` ({L1009}). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binary and the results ({L947-948}).
- The test starts local programs: the generator, `gcc`, the stand-in runner (6 at a time, {L621}), two busy test processes on one CPU, the host sampler, the copy of the run script and the dummies.
- The exit status is 0 only when every check passed ({L1397}). A part that did not run prints a `SKIP` line and does not change the status. The summary line does not count the `SKIP` lines.
- Two options leave out parts: `--no-run` and `--no-bwx8` ({L1381-1390}). The checks of the generator, of the sampler and of the visit script always run. A failed build of the stand-in `bwx8` is a failed check and ends that group ({L577-578}).
- The expected values are written a second time in this file ({L38-53}). So a change in the generator alone makes a check fail.
- The validator, the comparison of the nominal work, the rule for the CPU order and the four rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Such an input is a damaged copy, or the real output with a wrong expectation, for example the CPU order of the other session. These second tests are 25 checks. Not every rule inside a rule function has such a second test. For example, no check gives a rule function a schedule with a wrong number of processes.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases run twice. With the sampler, on step `XW` ({L1160-1193}): the stop file, the marker file, a signal, `STOP_AT` during a process, and a failing process. Without the sampler, on step `XEV` ({L1233-1312}): the same five, and also the marker file at the start, between two processes and directly before a launch, the stop file at the start, and a `STOP_AT` that is nearer than `MARGIN`.
- What a stop case tests depends on the case. Every case tests the exit status. A case that ends a running process also tests the `-- killed` line and that no process is left. A case in which nothing may start tests that no dummy was started. The case of the marker file between two processes tests that the first process was not cut and that no second one started. A case of a failing process tests the `-- failed` line.
- The checks of `MARGIN` use stop times that lie far inside or far outside the margin: 30 s against 91 s, 100 s against 123 s, and 45 s against 1 s ({L1275-1277}, {L1283-1285}, {L1301}). No check tests a stop time that is exactly `MARGIN` seconds away.
- The check of the saved folder compares every file of `sched9/` beside this file with the output of the generator ({L550-552}). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails, and the copy in {L1282} raises an error that ends the test without its summary.
- Two checks test less than their names say. By the name of the first, every item of a delta line is `key=number` or `key:=state`. The test accepts a state item only when its value is a number ({L786-788}). The second, which starts at {L558}, is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The check that the sampler follows a thread of the other process takes the busiest followed thread of any process ({L778-781}). It does not test which process that thread belongs to.
- The check of the source text of the sampler reads the text only ({L837-841}). It does not watch which files the sampler opens when it runs.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine ({L579}). CPU 41 is replaced by a local CPU in a copy of the schedule ({L593-596}). The checks of the sampler need 3 allowed CPUs ({L688}).
- The box gives the run script the highest allowed CPU as `WATCH_CPU` ({L928}). The case of an empty `WATCH_CPU` has two expected results: it runs when the machine allows CPU 100, and it stops at the start check of the sampler when not ({L1202-1206}).
- The variable `real` of {L1280} is set and never used.
- The test reads these files of its own folder: `schedule9.py`, `hostwatch.py`, `run_bwx9.sh`, `visit9.sh`, `bwx8.c`, `run_bwx8.sh`, `visit8.sh` and the folder `sched9`.
- The test writes into a temporary folder only and removes it at the end ({L1378}, {L1392}).
