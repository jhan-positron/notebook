## Short version: purpose

`test_schedule8.py` checks the three scripts of round 1 without CRB: the generator `schedule8.py`, the run script `run_bwx8.sh` and the visit script `visit8.sh`. It tests the generated schedules against rules that are written a second time in this file, and it runs the run script with a dummy binary through its stop cases. The validator, the comparison of the nominal work and seven rule functions are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 1**: the first set of tests of the investigation into the buffer size of 8 MiB. The three scripts under test belong to it.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation. Its parts are called stages. Stage 2 is the size comparison of step `S2`, and Stage 3 is the test of mixed sequences of step `S3`.
- **Contract**: the note `DECISIONS-bwx8.md`. It fixes what the parts of the implementation share: the plan format, the table of the steps and the nominal kernel work of each step.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule8.py`. It writes the schedules and the plan files of round 1.
- **Run script**: the script `run_bwx8.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit8.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `S2`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Target, window**: the target is the kernel that a trial measures. A window is one timed period of it.
- **Same-kernel trial**: a trial in which the target kernel is also the prefix: a prefix of 4 window lengths and then 4 target windows. The trials of step `S2` have this form.
- **Interval mode**: the mode of the runner that times a kernel sequence from the option `--seq`. The processes of step `B6W` use it and have no plan file.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Condition**: one setting that a step compares, and the label that names it in the plan, for example `K=read|S=8M`.
- **Cycle, row**: a cycle is a group of trials of one process that holds every condition of the step once. A row is the list of the condition labels of one cycle, in run order.
- **Replicate set, block**: a replicate set is the three processes of step `S2` that have the same size, CPU and replicate number, one per kernel. A block is the 30 processes of one replicate number.
- **Start order, shift**: the start order is the fixed order of 12 condition numbers that the design gives for step `S3`. A shift adds one number to every entry and takes the rest of a division by 12.
- **Base seed, seed**: the base seed is the one number that the caller of the generator can set with `--seed`. The seed of a step and session is derived from it.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `open` means that the counters are open and are not read at the window boundaries. `read` means that the runner reads them at the boundaries of the target windows.
- **Bins**: records of 10 ms inside a target window. The field `bins` of a trial turns them on (1) or off (0).
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`BWX_PMU_TYPE`, `BWX_EVENTS`**: the two counter settings that the run script needs in its environment for the steps `CS`, `CM` and `C4`: the type number of the counter device, and the list of the counter events.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Dummy binary**: a small shell script that stands in for the runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Stand-in**: a program that takes the place of another one in the test, here of `ps` and of `ssh`.
- **Box**: the test setup of the run script: a copy of the script, the dummies and a schedule in a temporary folder.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts a process only when this time is more than `MARGIN` seconds away, and it ends a process that still runs at this time.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step, rounded up to whole seconds, plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file of a step is `<STEP>.csv` in the result folder. Before the output of each process the run script writes a header line into it. That line starts with `-- step`.
- **Load record**: the lines that the run script appends to the file `launches.txt` before a launch: the load averages, the number of logins and the 5 processes with the highest `pcpu` value of `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB**: 1024 bytes.

## Main flow

1. The values that the contract expects are written as fixed values: the nominal work of 7 steps and the counts of all 11 steps ({L30-35}).
2. The helper `check` prints one line per check and collects the failures ({L40-43}).
3. The validator of the plan format and the reader of a generated folder ({L46-128}, {L131-193}).
4. The rules of the rows, of the CPU order and of step `S2`, each as a function ({L196-350}).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the effect of the seed, the option `--select`, the saved folder, `--report` and the test divisor ({L353-613}).
6. Group 2, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, and five bad settings ({L733-770}).
7. Group 3, `run_checks`: the run script with a dummy binary: syntax, a step named twice, the warnings, damaged schedule fields, the dry run, a normal run, `--from`, the CPU limit, the stop controls, `MARGIN`, session 2 and other refusals ({L773-974}).
8. `main` runs the groups in this order, removes the temporary folder and prints the summary ({L977-989}).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` ({L750}). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binary and the results ({L692-693}).
- The test starts local programs: the generator, `bash`, the copy of the run script and the dummies. The copy of the run script sets its own CPU list to the CPUs 0 to 119 with `taskset`, as the real script does.
- The exit status is 0 only when every check passed ({L989}). With `--no-run` the checks of the run script are left out: the test prints a `SKIP` line, and the status does not change ({L982-983}).
- The expected values are written a second time in this file ({L31-35}, {L226}, {L445-448}). So a change in the generator alone makes a check fail.
- The validator, the comparison of the nominal work and seven rule functions are tested twice: once on the real output, and once on an input that must not pass. The seven are `cpu_blocks`, `s2_rules`, `williams`, `from_start_order`, `rows_shuffled`, `order_varies` and `perms_four_times`.
- These second tests are 24 checks: 11 damaged plans for the validator ({L364-377}), a copy of `S2` with one trial removed for the nominal work ({L385-388}), the schedule of `S3` of session 1 read with the CPU order of session 2 for the rule of the CPU order ({L420}), 5 variants for the rules of `S2` ({L426-442}), and 6 checks with changed rows for the rules of the balance, of the start order, of the shuffle, of the row order and of the order count ({L471-480}, {L555-561}). One of the 5 variants is the unchanged schedule of session 1, read with the CPU order of session 2.
- The other rules of this file have no such second test. Examples: the header pairs ({L401-409}), the conditions of a cycle ({L453-454}), the trial form of `S3` and `CM` ({L455-459}) and the alternating orders of `BIN` ({L540-541}). Inside `s2_rules`, no variant makes the rules of the sizes ({L281-285}) or of the `rep_set` value ({L301-302}) fail.
- No check of this file gives a plan to the runner. The plans are tested against the validator of this file only ({L57-120}).
- The only selection that the generator accepts in this test is `read@1M,asmread@8M` ({L28}, {L355}). So the steps `BIN` and `CS` are tested for these two pairs only. Two base seeds are used: 20261114 and 7 ({L572}).
- The run script is tested with a schedule that was made with the test divisor 100 ({L605}, {L613}). So the durations in its summaries are a hundredth of the real ones, for example 0.624 s for `B6W`.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases that are tested ({L863-928}): the marker file during a process, at the start, between two processes and directly before a launch. The stop file during a process. The signal TERM during a process. A `STOP_AT` that is nearer than `MARGIN`, and a `STOP_AT` that is reached during a process. A failing process. The cases with a running process test the exit status, the `-- killed` line and that no process is left.
- Not tested: a stop file that exists before a launch, and the signals INT and HUP.
- The checks of `MARGIN` use stop times that lie far inside or far outside the margin: 30 s against 91 s and against 92 s, and 45 s against 1 s ({L907-920}). No check tests a stop time that is exactly `MARGIN` seconds away.
- The check of the saved folder compares every file of `sched/` beside this file with the output of the generator ({L594-596}). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails. The other checks do not need that folder: the box gets a newly generated schedule ({L666}).
- The check of step `B6W` reads the kernel sequence from `run_bwx.sh` in the folder `bwx-2026-11-13` beside the folder of this file ({L26}, {L564}).
- Some checks test less than their names say. This item and the next one name five of them. The check of {L833-834} is named for header lines that are each followed by their output. It counts the output lines and does not test their places. The check of {L474-475} is named for rows that are not shifts. Its input is 24 equal rows, which the rule rejects for the count of the shifts.
- The check of {L607-610} is named for every duration divided by 100. It compares the sums of the nominal work of each step and session. The check of {L410-414} is named for labels that agree with the trial. It compares the counter mode, the bins flag and the target kernel, and no other key of a label. The check of {L836-838} is named for the digests in `env.txt`. It tests the heading `## sha256:` and not the digest lines.
- The check of the CPU limit compares the CPU list of the dummy with the CPUs that the test itself may use ({L852-857}). It needs a machine with 2 or more CPUs. A machine that has no CPU with the number 120 or higher cannot show that such CPUs are left out. Hypothesis, not tested: when the test itself was started with a narrower CPU list by `taskset`, the script still sets the list 0 to 119, the dummy then sees more CPUs than the test may use, and the check fails. One run of the test under such a narrower list would confirm or reject it.
- The test reads these files: `schedule8.py`, `run_bwx8.sh`, `visit8.sh` and the folder `sched` of its own folder, and `run_bwx.sh` of the folder `bwx-2026-11-13`.
- The test writes into a temporary folder only and removes it at the end ({L978}, {L987}).
- The name `M8` of {L29} is set and never used.
