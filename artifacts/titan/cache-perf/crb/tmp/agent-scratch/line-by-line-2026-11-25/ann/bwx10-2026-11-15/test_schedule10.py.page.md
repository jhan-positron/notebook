## Short version: purpose

`test_schedule10.py` checks the three scripts of round 3 without CRB: the generator `schedule10.py`, the run script `run_bwx10.sh` and the visit script `visit10.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, and it runs the run script with dummy binaries through its stop cases. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 3**: the third set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Y`.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048`**: the four prefetch kernels of the runner `bwx10`. Each is the `asmread` loop with one software prefetch per 64 B line, 256, 512, 1024 or 2048 bytes ahead.
- **`read_1pl`**: a kernel of the runner `bwx10` that makes one load of 16 bytes at the start of each 64 B line.
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule10.py`. It writes the schedules, the plan files and the `.bin` files of round 3.
- **Run script**: the script `run_bwx10.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit10.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `YP`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **`.bin` file**: the file `<STEP>.bin` of a step. It holds one word, `bwx8` or `bwx10`, the name of the runner that the step uses.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Header pairs**: the pairs of the form `key=value` in the second line of a plan file, for example `kernel=asmread`.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix, target, window**: the target is the kernel that a trial measures. A window is one timed period of it. The prefix is a phase before the target that gives every trial the same preparation.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Window plan**: one of the four ways in which step `YL` cuts 30 s of target time into windows: `L100`, `L300`, `L1000` and `L30000`.
- **Condition**: one setting that a step compares. In `YL` it is one kernel with one window plan. In `YP` it is one record pad or `hot`.
- **Cell**: one combination of the factors of a step, for example one kernel at one buffer size.
- **Replicate set, block**: a replicate set is one run of every kernel of step `YF` for one size and CPU. A block is the group of processes of one replicate on one CPU in the steps `YL` and `YP`, or the processes of one CPU in `YC`.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **`--rec-pad P`**: an option of the runner `bwx10`. It puts P unused bytes before the records in which the runner stores the times of its windows.
- **`--hot-copy`**: an option of the runner `bwx10`. The window loop then works on a local copy of its window record.
- **`--trace`**: an option of the runner. The runner then prints a log of the events around its timed parts. The rates of such a run are not used.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **`bins`**: a field of a trial, 0 or 1. With 1 the runner also stores the time and the byte count about every 10 ms inside a target window. One such entry is a bin record.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`--pmu-type`, `--events`**: the two counter options of the runner. `--pmu-type` gives the type number that Linux gives to the counter device of the cores, 11 on CRB by the notes of the project. `--events` gives the list of counter events, each as a name and a code. The variables `BWX_PMU_TYPE` and `BWX_EVENTS` carry the same two values in the environment.
- **Validator**: the function `parse_plan` of this file. It tests a plan file against the rules of the plan format.
- **Stand-in**: a program that takes the place of another one in the test. The stand-in runners are built from the runner sources on the local machine. Their kernels are plain C loops, and their rates mean nothing.
- **Dummy binary**: a small shell script that stands in for a runner. It records how it was started, sleeps, and ends with a chosen exit status.
- **Box**: the test setup of the run script: a copy of the script, the dummies and a schedule in a temporary folder.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop the run script.
- **`STOP_AT`**: a UTC time that the caller sets. The run script starts no process that could run past it.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s by default. `MARGIN` is the nominal work of the longest process of a step plus `RESERVE`.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Host sampler**: the program `hostwatch.py`. The run script starts it beside a process when the step has a `.watch` file.
- **Dry run**: a call of the run script with `--dry-run`. It prints what would run and starts nothing.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. The values that the task expects are written as fixed values: the counts, the nominal work, the binary, the kernels, the sizes, the options and the events of each step ({L43-64}).
2. The helper `check` prints one line per check and collects the failures ({L70-76}).
3. The validator of the plan format and the reader of a generated folder ({L79-162}, {L165-208}).
4. The rules of the steps, one function per step ({L249-394}).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.bin` files, the effect of the seed, the saved folder and the test divisor ({L397-624}).
6. Group 2, `bwx8_checks`: a locally built `bwx8` accepts all 64 plans of `YL`, runs the 8 real window plans of one block for 30 s each, refuses damaged plans, and refuses the options of a `YP` process ({L683-742}).
7. Group 3, `bwx10_checks`: a locally built `bwx10` lists the new kernels and accepts all 725 plans of `YA`, `YP`, `YF` and `YC` ({L745-782}).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit9.sh` ({L952-1003}).
9. Group 5, `run_checks`: the run script with dummy binaries: syntax, comparison of the stop controls with `run_bwx9.sh`, step names and the dry run, a normal run, the binary of a step, the digests, the counter settings, the host sampler, the stop controls, `MARGIN`, session 2 and other refusals ({L1006-1365}).
10. `main` runs the groups in this order, removes the temporary folder and prints the summary ({L1368-1390}).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` ({L969}). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binaries and the results ({L901-902}).
- The test starts local programs: the generator, `gcc`, the stand-in runners (6 at a time, and once 8 at a time for 30 s), the copy of the run script, the dummies and the host sampler.
- The exit status is 0 only when every check passed ({L1390}). A part that did not run prints a `SKIP` line and does not change the status. The summary line does not count the `SKIP` lines.
- Four options leave out parts: `--no-run`, `--no-bwx8`, `--no-long` and `--no-bwx10`. The part with the stand-in `bwx10` is also left out when `bwx10.c` is missing or cannot be built ({L750-760}). A failed build of the stand-in `bwx8` is a failed check ({L688}).
- The expected values are written a second time in this file ({L44-63}). So a change in the generator alone makes a check fail.
- The validator, the rule for the CPU order and the rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Not every rule inside a rule function has such a second test.
- The check that starts at {L612} is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The stop cases run once for a step of each binary, `YL` with the dummy `bwx8` and `YA` with the dummy `bwx10` ({L1229}): the marker file and the stop file during a process and at the start, a signal, `STOP_AT` before and during a process, and a failing process. Each case tests the exit status. The four cases that stop a running process also test the `-- killed` line and that no process is left. The three cases with a stop reason before the first launch test that nothing starts. The case of a failing process tests the `-- failed` line and that the next process does not start.
- The check of the saved folder compares every file of `sched10/` beside this file with the output of the generator ({L598-600}). The repo README lists the folders `sched*` among those that were left out of the repo. So in the repo folder this check fails, and the copy in {L1292} raises an error that ends the test without its summary.
- The check of a wrong `.bin` content tests "nothing starts" with the log of the dry run only ({L1124-1128}). For the real run it tests the exit status and the message.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine ({L678}). CPU 41 is replaced by a local CPU in a copy of the schedule ({L643-646}).
- The test reads four files of the folder `bwx8-2026-11-14`, which must lie beside the folder of round 3 ({L33}): `bwx8.c`, `run_bwx9.sh`, `visit9.sh` and `hostwatch.py`.
- The test writes into a temporary folder only and removes it at the end ({L1371}, {L1385}).
