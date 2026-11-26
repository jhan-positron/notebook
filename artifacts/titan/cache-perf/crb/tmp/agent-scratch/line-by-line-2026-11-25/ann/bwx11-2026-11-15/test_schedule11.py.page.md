## Short version: purpose

`test_schedule11.py` checks the three scripts of round 4 without CRB: the generator `schedule11.py`, the run script `run_bwx11.sh` and the visit script `visit11.sh`. It tests the generated schedules against rules that are written a second time in this file, it puts every plan through a runner that is built on the local machine, and it runs the run script with dummy binaries through its stop cases. The validator and the rule functions of the steps are also applied to inputs that must not pass, to show that they can fail.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation into the buffer size of 8 MiB.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **Check**: one call of the function `check`. It prints `PASS` or `FAIL` and one sentence that says what was tested.
- **Generator**: the program `schedule11.py`. It writes the schedules and the plan files of round 4.
- **Run script**: the script `run_bwx11.sh`. It starts the processes of a schedule on CRB, one at a time.
- **Visit script**: the script `visit11.sh`. It makes one login to CRB and starts the run script there.
- **Step**: one batch of processes of a round, for example `ZD`.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later, with the two CPUs in the reverse order.
- **Schedule**: the file `<STEP>.tsv` of a step. It has one row per process, with six columns that tabs separate: `idx`, `tag`, `cpu`, `bytes`, `plan` and `args`.
- **`idx`, tag**: the number of a process in its schedule, counted from 0, and the short name of the process.
- **Plan file**: a text file that tells the runner what one process does. It has three header lines and then one line per trial.
- **Trial**: one timed sequence inside a process: an optional previous activity, an optional prefix, an optional predecessor, and the target windows.
- **Previous activity, prefix, predecessor**: three optional phases of a trial that run before the target windows. Each runs one kernel for a planned time.
- **Prefix, target, window**: the target is the kernel that a trial measures. A window is one timed period of it. The prefix is a phase before the target that prepares the core.
- **`S2` form**: a process of 4 equal trials, each with a prefix of 1200 ms of the target kernel and 4 target windows of 300 ms. Step `S2` of round 1 had this form first.
- **Nominal kernel work**: the sum of the planned durations of all phases and windows. The real run time of a process is longer.
- **Cell**: one combination of the factors of a step, for example one kernel with one evict condition.
- **Replicate set, block**: a replicate set is one run of every cell of a step for one size and CPU. A block is the group of processes of one replicate on one CPU in the steps `ZC` and `ZM`.
- **Williams square**: a set of n orders of n items in which every item stands once at every position, and every ordered pair of different items stands once as direct neighbours.
- **Test divisor**: a number by which the generator divides every duration, for local tests only. The test uses 100.
- **Evict step, `E0`, `E512`**: with the option `--evict-mb 512` the runner `bwx11` writes another buffer of 512 MiB twice before the first trial. `E512` is the condition with that option, and `E0` the condition without it.
- **Counter mode**: the field `count` of a trial. `closed` means no counters. `read` means that the runner reads the counters for each window.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
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

1. The values that the task expects are written as fixed values: the counts, the nominal work, the kernels, the sizes and the events of each step ({L46-68}).
2. The helper `check` prints one line per check and collects the failures ({L84-90}).
3. The validator of the plan format and the reader of a generated folder ({L93-176}, {L180-222}).
4. The rules of the steps, one function per step ({L263-422}).
5. Group 1, `schedule_checks`: run the generator. Test the format of every file, the counts and the printed report, the header pairs, the CPU order, the rules of each step with damaged variants, the `.bin` files, the effect of the seed, the saved folder and the test divisor ({L425-722}).
6. Group 2, `bwx10_checks`: a locally built `bwx10` refuses the options and the plans that are new in round 4 ({L796-821}).
7. Group 3, `bwx11_checks`: a locally built `bwx11` accepts all 870 plans, refuses damaged plans, and runs the 10 real plans of one block of `ZM` ({L824-893}).
8. Group 4, `visit_checks`: the visit script with a stand-in for `ssh`: the remote command, bad settings, and the comparison with `visit10.sh` ({L1073-1127}).
9. Group 5, `run_checks`: the run script with dummy binaries: syntax, comparison with the older run scripts, step names and the dry run, a normal run, the binary of a step, the digests, the counter settings, the host sampler, the stop controls, `MARGIN`, session 2 and other refusals ({L1141-1537}).
10. `main` runs the groups in this order, removes the temporary folder and prints the summary ({L1540-1562}).

## Behavior a reader must know

- The test contacts no other machine. The visit script runs with a stand-in for `ssh` and a search path that holds no real `ssh` ({L1090}). The run script runs as a copy in a temporary folder, with test paths for the marker file, the stop file, the binaries and the results ({L1022-1023}).
- The test starts local programs: the generator, `gcc`, the stand-in runners (4 at a time, and once 10 at a time for 30 s), the copy of the run script, the dummies and the host sampler.
- The exit status is 0 only when every check passed ({L1562}). A part that did not run prints a `SKIP` line and does not change the status. The last line of the output gives the number of such parts.
- Four options leave out parts: `--no-run`, `--no-bwx10`, `--no-bwx11` and `--no-long`. The part with the stand-in `bwx11` is also left out when `bwx11.c` is missing or cannot be built ({L827-836}).
- The expected values are written a second time in this file ({L48-65}). So a change in the generator alone makes a check fail.
- The validator, the rule for the CPU order and the rule functions of the steps are tested twice: once on the real output, and once on an input that must not pass. Not every rule inside a rule function has such a second test.
- The check that starts at {L708} is named for every duration divided by 100. The test compares the nominal work per step and session and the window counts, not each duration.
- The checks of the run script take minutes on a loaded machine. Before each launch the script waits up to 20 s until at most 2 tasks are runnable.
- The check of the saved folder compares every file of `sched11/` beside this file with the output of the generator ({L695-696}). It fails when that folder holds the files of step `ZS`, which `schedule_zs.py` adds.
- The check of a wrong `.bin` content tests "nothing starts" with the log of the dry run only ({L1283-1287}). For the real run it tests the exit status and the message.
- The stand-in runs need CPU 0, CPU 2 and one more CPU below 120 on the local machine ({L781}). CPU 41 is replaced by a local CPU in a copy of the schedule ({L741-744}).
- The test reads files of the folders of rounds 1 to 3, which must lie beside the folder of round 4 ({L34-35}).
- The test writes into a temporary folder only and removes it at the end ({L1543}, {L1557}).
