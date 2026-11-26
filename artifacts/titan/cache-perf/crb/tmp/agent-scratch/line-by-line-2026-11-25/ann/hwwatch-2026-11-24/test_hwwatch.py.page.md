## Short version: purpose

`test_hwwatch.py` checks the code of the hardware record without CRB: the program `hwwatch.py`, the shell functions of `hw.sh`, the script `clock_from_counts.py`, and the calls of the hardware record in the three run scripts and the two drivers. It uses a fake file tree in place of `/sys` and `/proc`, and stand-in programs in place of `atx`, of the benchmark binaries and of `taskset`. It prints one line per check and ends with exit status 0 only when every check passed.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **Check**: one call of the function `check` of this file. It has a name that says what it proves, and it prints `PASS` or `FAIL`.
- **Copied file tree, fake tree**: a folder with normal text files that have the paths and the content of files of `/sys` and `/proc`. The function `make_tree` writes it. `hwwatch.py` reads it in place of the real files when it gets the option `--root`, and `hw.sh` passes the folder in the variable `HW_ROOT`.
- **Stand-in**: a small program that the checks use in place of a real one: for `atx`, for the benchmark binaries, for `taskset`, `sleep`, `gcc` and `objdump`.
- **Run script**: `ra.sh`, `rx.sh` or `run_kernels.sh`. A run script starts benchmark processes.
- **Driver**: `go.sh` or `go2.sh`. A driver starts run scripts, one after the other.
- **Step**: one call of a run script by a driver. Each step writes one result folder.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process**: one start of a benchmark binary.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process.
- **Session**: one pass of `go.sh` through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the binaries `bw_old` and `bw_new`.
- **Part L**: one `bwx12` process with the kernel sequence `oldread`, `asmread`, `read_nop96`, `read_nop256`, `read_1pl`.
- **Part C**: one `bwx12` process with the sequence `oldread`, `read`, `asmread` (spec file `cfwd.spec`) or the reverse order (`crev.spec`).
- **Frequency sampler, sampler**: the program `hwwatch.py watch`. It runs in the background and writes the clock rate of each core once per period.
- **Snapshot**: one read of a small set of files for a list of CPUs, written to one file (`hwwatch.py snap`). `hw.sh` takes one before and one after each process.
- **Probe**: the file `probe.txt` of a hardware record (`hwwatch.py probe`). It is written once per result folder.
- **Window of a process**: the time from the end of the snapshot before a process to the start of the snapshot after it.
- **`atx`**: Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware.
- **Collection**: one run of the command `atx collect`. `hw.sh` ends it with a signal and then waits for the reports of `atx`.
- **Collectors**: the word of this file for the sampler and `atx` together.
- **Self-test of the record**: the function `hw_check` of `hw.sh`. It tests the files of Linux, the sampler and `atx` before a test. Its test of `atx` is a short collection, the trial collection.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Clock rate**: the frequency at which a core runs, in kHz or GHz. 2800000 kHz is 2.8 GHz.
- **The two counters**: `ref` and `del` in the file `acpi_cppc/feedback_ctrs` of a CPU. `ref` counts at a fixed reference rate. `del` counts at the rate that the core delivered.
- **Counter ratio**: the change of `del` divided by the change of `ref` between two snapshots of one CPU.
- **Performance unit**: one step of the scale of the firmware table. In the fake tree 280 units stand for 2800 MHz.
- **Limit**: the clock rate below which the report flags a value. It is 99 % of the highest frequency of the CPU unless `--tol` says otherwise. In the fake tree it is 2772000 kHz.
- **Flag**: a word in capital letters that the report prints for a process, for example `LOW_AVG`.
- **Throttle flag**: the file `cpufreq/perf_limited` of a CPU. The firmware sets it to a value other than 0 when a limit made the core deliver less than Linux requested.
- **Rail**: one power supply line of the chip.
- **Metric, target**: words of the summary file of `atx`. A metric is one measured quantity, for example the power of one rail. A target is the source that a row of values comes from.
- **Interval**: one timed measurement inside a process.
- **Trial layout**: a second layout of a runner csv file. It has one row per trial in place of one row per interval.
- **`C` row**: a row of a runner csv file that starts with `C`. It holds the counter values of one thread in one interval or trial.
- **Scaled**: the word of `clock_from_counts.py` for a row or a line whose counter did not run for the whole time. The script does not use such a value.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **`perf stat`**: a Linux tool that counts events for a time and prints the counts.
- **Tag**: the name that a run script gives to one process. It starts the names of the files of that process.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **MemTotal**: the usable memory that Linux reports in the file `/proc/meminfo`, in kB.
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Signal**: a message that Linux delivers to a process. SIGINT is the interrupt signal. SIGTERM asks a process to end. SIGKILL ends a process at once.
- **Trap**: a command that the shell runs when it receives a signal or when it ends.
- **Sourced**: a script reads another file with the shell command `.` and runs its lines in its own shell. The functions and variables of that file exist in the script afterwards.
- **Strict shell options**: the line `set -euo pipefail`. With it, Bash stops a script at a failed command, at a variable that was never set, and at a failed stage of a pipeline.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **Place holder**: a mark in a text, such as `%s` or `%(bench)s`, that the Python operator `%` replaces with a value.

## Main flow

1. The first lines set the paths of the files under test and import `hwwatch.py` and `clock_from_counts.py` as modules ({L31-46}).
2. The helpers follow. `check` counts and prints one check. `make_tree` builds the fake tree: one text file per file of `/sys` and `/proc` that the programs read, for a given number of CPUs ({L49-109}).
3. `tool_checks`: 23 checks of the commands of `hwwatch.py` on a tree of 4 CPUs: the CPU limit, `check`, `snap`, `probe` and `watch` ({L114-200}).
4. `report_checks`: 22 checks of `hwwatch.py report`. Each case builds a result folder with the real commands, changes the tree between the two snapshots, and tests the rates and the flags of the report ({L203-329}).
5. `counts_checks`: 7 checks of `clock_from_counts.py` on small input files ({L332-357}).
6. The stand-in programs and the helpers that run shell text with them ({L362-464}).
7. `hwsh_checks`: 22 checks of `hw.sh`: `hw_check`, a whole record under strict shell options, and the failures after `hw_init` ({L469-546}).
8. `static_checks`: 18 checks of the texts of the scripts, without a script start ({L591-615}).
9. `run_checks`: 25 checks that start `rx.sh`, `ra.sh`, `go.sh`, `go2.sh` and `run_kernels.sh` with the stand-ins in a test home ({L552-588}, {L618-722}).
10. `main` runs the groups in this order: `static_checks`, `tool_checks`, `report_checks`, `counts_checks`, `hwsh_checks`, `run_checks`. Then it deletes the temporary folder, prints the result line and sets the exit status ({L725-744}).

## Behavior a reader must know

- No check needs CRB, and no check proves anything about CRB. The docstring says so ({L8}), and the design note repeats it [Ref1].
- The numbers of checks per group in "Main flow" are counted from the calls of `check` in the source. They add up to 117. A group has fewer checks when an earlier step failed, for example when a script under test wrote no result folder.
- The values of the fake tree are invented. So the expected rates of the checks (2800000, 2799720, 2520000 and 2660000 kHz) follow from the tree and say nothing about CRB.
- No benchmark runs. Every benchmark binary is a stand-in that advances the two counters in the tree and ends at once. The stand-in `taskset` pins nothing, and the stand-in `sleep` makes every pause last one tenth of its time.
- `rx.sh` and `run_kernels.sh` run with their unchanged text. `ra.sh`, `go.sh` and `go2.sh` run as copies with the eight text changes of `COPY_CHANGES` ({L552-561}).
- `--no-run` leaves out `run_checks`. Then 92 checks run.
- Four checks compare a file with the last commit of the git repository ({L606}, {L615}). By the header of the trial script, they always fail in a copy of the code that is not a git repository [Ref3].
- `write_result` and `install` use `assert`. When a command of the tool fails there, or when an old text of `COPY_CHANGES` does not occur exactly once, the test ends with a Python error. `main` then prints no result line.
- The test writes only below a new temporary folder and deletes it at its end. It also kills every stand-in `atx` and every sampler of the test that still runs ({L735-742}).
- The output of one run of this file is kept. The run was on the agent server, on 2026-11-25 at 01:49 UTC: 117 checks, 117 passed, 141 s. The sha256 values of the nine files under test in that output are equal to the sha256 values of these files in the code repo, as computed for this page on 2026-11-25 [Ref2].
- The output of seven defect trials is kept. Each trial put one defect into a copy of the code and ran this file with `--no-run`. In each trial at least one check failed, in addition to the four checks that always fail in a copy [Ref3].

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Section 1: the request for the clock rate of the single core in single-core tests. Section 5: decision 1 (the fixed boot id stops `go2.sh` in every other boot), decision 2 (power is required by default), decision 4 (a failure of the record does not stop a started test) and decision 9 (`run.sh`, the saved start command, is unchanged). Section 6: the two signs of a shutdown of the chip. Section 7: the checks ran on the agent server and prove nothing about CRB. Section 8, item 4: the guide of `atx` and its program text differ in one column name of the summary.
- [Ref2] The file `status/2026-11-24-hw-record-evidence/test_hwwatch.out` of the same repo: the output of a run of this file. Its first line gives the time 2026-11-25T01:49:20Z and the agent server. The next lines give the sha256 of the nine files under test. Then one line per check follows. The last two lines hold `# checks: 117, passed: 117, failed: 0` and `# exit status 0 wall time 141 s`.
- [Ref3] The files `defect_trials.sh` and `defect_trials.out` in the folder `status/2026-11-24-hw-record-evidence` of the same repo: the seven defect trials and their output. The header of the script names the four checks that always fail in a copy.
