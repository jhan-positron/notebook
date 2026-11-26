# `test_hwwatch.py` explained, line by line

- Source file: `hwwatch-2026-11-24/test_hwwatch.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 748 lines, 52430 bytes).
- sha256 of the source when this page was built: `a09b3e353c1f452a26a538427f625838722a9c7fb997a583b34521d1c524c2c5`.

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

1. The first lines set the paths of the files under test and import `hwwatch.py` and `clock_from_counts.py` as modules (lines 31 to 46).
2. The helpers follow. `check` counts and prints one check. `make_tree` builds the fake tree: one text file per file of `/sys` and `/proc` that the programs read, for a given number of CPUs (lines 49 to 109).
3. `tool_checks`: 23 checks of the commands of `hwwatch.py` on a tree of 4 CPUs: the CPU limit, `check`, `snap`, `probe` and `watch` (lines 114 to 200).
4. `report_checks`: 22 checks of `hwwatch.py report`. Each case builds a result folder with the real commands, changes the tree between the two snapshots, and tests the rates and the flags of the report (lines 203 to 329).
5. `counts_checks`: 7 checks of `clock_from_counts.py` on small input files (lines 332 to 357).
6. The stand-in programs and the helpers that run shell text with them (lines 362 to 464).
7. `hwsh_checks`: 22 checks of `hw.sh`: `hw_check`, a whole record under strict shell options, and the failures after `hw_init` (lines 469 to 546).
8. `static_checks`: 18 checks of the texts of the scripts, without a script start (lines 591 to 615).
9. `run_checks`: 25 checks that start `rx.sh`, `ra.sh`, `go.sh`, `go2.sh` and `run_kernels.sh` with the stand-ins in a test home (lines 552 to 588, lines 618 to 722).
10. `main` runs the groups in this order: `static_checks`, `tool_checks`, `report_checks`, `counts_checks`, `hwsh_checks`, `run_checks`. Then it deletes the temporary folder, prints the result line and sets the exit status (lines 725 to 744).

## Behavior a reader must know

- No check needs CRB, and no check proves anything about CRB. The docstring says so (line 8), and the design note repeats it [Ref1].
- The numbers of checks per group in "Main flow" are counted from the calls of `check` in the source. They add up to 117. A group has fewer checks when an earlier step failed, for example when a script under test wrote no result folder.
- The values of the fake tree are invented. So the expected rates of the checks (2800000, 2799720, 2520000 and 2660000 kHz) follow from the tree and say nothing about CRB.
- No benchmark runs. Every benchmark binary is a stand-in that advances the two counters in the tree and ends at once. The stand-in `taskset` pins nothing, and the stand-in `sleep` makes every pause last one tenth of its time.
- `rx.sh` and `run_kernels.sh` run with their unchanged text. `ra.sh`, `go.sh` and `go2.sh` run as copies with the eight text changes of `COPY_CHANGES` (lines 552 to 561).
- `--no-run` leaves out `run_checks`. Then 92 checks run.
- Four checks compare a file with the last commit of the git repository (line 606, line 615). By the header of the trial script, they always fail in a copy of the code that is not a git repository [Ref3].
- `write_result` and `install` use `assert`. When a command of the tool fails there, or when an old text of `COPY_CHANGES` does not occur exactly once, the test ends with a Python error. `main` then prints no result line.
- The test writes only below a new temporary folder and deletes it at its end. It also kills every stand-in `atx` and every sampler of the test that still runs (lines 735 to 742).
- The output of one run of this file is kept. The run was on the agent server, on 2026-11-25 at 01:49 UTC: 117 checks, 117 passed, 141 s. The sha256 values of the nine files under test in that output are equal to the sha256 values of these files in the code repo, as computed for this page on 2026-11-25 [Ref2].
- The output of seven defect trials is kept. Each trial put one defect into a copy of the code and ran this file with `--no-run`. In each trial at least one check failed, in addition to the four checks that always fail in a copy [Ref3].

## Source and explanation, line by line

- Text shown: the file `hwwatch-2026-11-24/test_hwwatch.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (748 lines, 52430 bytes, sha256 `a09b3e353c1f452a26a538427f625838722a9c7fb997a583b34521d1c524c2c5`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 249. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Docstring: what the checks cover and what they use in place of CRB (lines 1 to 17)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_hwwatch.py - checks of hwwatch.py, hw.sh and of the hooks in rx.sh, ra.sh, run_kernels.sh, go.sh and go2.sh.` | Starts the docstring of the file. It ends in line 17. This first line names what is checked: `hwwatch.py`, `hw.sh`, and the calls of the hardware record (the "hooks") in the five scripts `rx.sh`, `ra.sh`, `run_kernels.sh`, `go.sh` and `go2.sh`. |
| 4 | `Usage: test_hwwatch.py [--no-run]` | Docstring: the usage. The option `--no-run` may be left out. |
| 5 | `Prints one line per check. Exit status 0 only if every check passed.` | Docstring: the script prints one line per check. Its exit status is 0 only when every check passed. |
| 6 | `--no-run leaves out the checks that start the run scripts with stand-in programs (they take a few minutes).` | Docstring: `--no-run` leaves out the checks that start the run scripts with stand-in programs. By the docstring these checks take a few minutes. |
| 8 | `No check needs CRB, and no check proves anything about CRB. The checks use:` | Docstring: no check needs CRB, and no check proves anything about CRB. The next lines list what the checks use in place of CRB. |
| 9 | `- a copied file tree: a folder with files as Linux shows them under /sys and /proc for N CPUs (hwwatch.py --root).` | Docstring: first, a copied file tree. It is a folder with files as Linux shows them below `/sys` and `/proc` for a number of CPUs. `hwwatch.py` reads it through its option `--root`. |
| 10 | `  Its values are invented. 280 performance units stand for 2800 MHz, so a counter ratio of 0.9 is 2520000 kHz.` | Docstring: the values of the tree are invented. 280 performance units stand for 2800 MHz. So a counter ratio of 0.9 gives 2520000 kHz. |
| 11 | `- stand-in programs: an "atx" that writes a summary file when it gets SIGINT, benchmark programs that advance the` | Docstring: second, stand-in programs. These are small programs that the checks use in place of the real ones. The first is an `atx` that writes a summary file when it receives the signal SIGINT. The second kind is benchmark programs. The sentence goes on in line 12. |
| 12 | `  two counters of their CPUs, and "taskset", "sleep", "gcc" and "objdump" in front of PATH. This taskset does not` | Docstring: the benchmark stand-ins advance the two counters of their CPUs. Four more stand-ins lie at the front of the search path `PATH`: `taskset`, `sleep`, `gcc` and `objdump`. This `taskset` does not pin. The sentence goes on in line 13. |
| 13 | `  pin (the test machine has other CPUs than CRB) and writes its arguments to a file. This sleep divides its time by 10.` | Docstring: the reason: the machine of the test has other CPUs than CRB. This `taskset` writes its arguments to a file. This `sleep` divides its time by 10. |
| 14 | `- copies of ra.sh, go.sh and go2.sh with the text changes that COPY_CHANGES lists. rx.sh and run_kernels.sh run` | Docstring: third, copies of `ra.sh`, `go.sh` and `go2.sh` with the text changes that the table `COPY_CHANGES` lists (lines 552 to 561). `rx.sh` and `run_kernels.sh` run without a change. The sentence ends in line 15. |
| 15 | `  unchanged.` | Docstring: the last word of the sentence of line 14: "unchanged". |
| 16 | `A rule is also applied to a defective input, and such a check passes only if the defect is reported.` | Docstring: a rule is also applied to an input with a defect. Such a check passes only when the defect is reported. |
| 17 | `"""` | Ends the docstring. |

### Imports (lines 18 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 18 | `import contextlib` | `contextlib` gives `redirect_stdout`, which keeps printed lines away from the output (line 137). |
| 19 | `import hashlib` | `hashlib` computes sha256 checksums (line 428). |
| 20 | `import io` | `io` gives a text buffer in memory (line 137). |
| 21 | `import json` | `json` reads the JSON output of `hwwatch.py report` (line 223). |
| 22 | `import os` | `os` gives the functions for files, folders and processes. |
| 23 | `import re` | `re` gives regular expressions (patterns for text). |
| 24 | `import shutil` | `shutil` copies files, finds programs in the search path and deletes folder trees. |
| 25 | `import signal` | `signal` gives the signal numbers and the setting of signal actions. |
| 26 | `import subprocess` | `subprocess` starts other programs and collects their output. |
| 27 | `import sys` | `sys` gives the arguments of the command line, the Python program in use and the exit of the script. |
| 28 | `import tempfile` | `tempfile` creates the temporary folder of the test (line 726). |
| 29 | `import time` | `time` gives the pauses and the time measurements of the checks. |

### The files under test, and the counters of the checks (lines 31 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled copies of the modules that it imports. So the import of `hwwatch` leaves no folder `__pycache__` in the code folder. |
| 32 | `X = os.path.dirname(os.path.abspath(__file__))` | `X`: the folder that holds this test file, `hwwatch-2026-11-24`. |
| 33 | `CODE = os.path.dirname(X)` | `CODE`: the folder above it, the code folder of the repository. |
| 34 | `TOOL = os.path.join(X, "hwwatch.py")` | `TOOL`: the path of `hwwatch.py`. |
| 35 | `HWSH = os.path.join(X, "hw.sh")` | `HWSH`: the path of `hw.sh`. |
| 36 | `RX = os.path.join(CODE, "w120-2026-11-15", "rx.sh")` | `RX`: the path of `rx.sh` in the folder `w120-2026-11-15`. |
| 37 | `W72 = os.path.join(CODE, "w120-7200-2026-11-17")` | `W72`: the folder `w120-7200-2026-11-17`. It holds `ra.sh`, `go.sh`, `go2.sh` and the spec files. |
| 38 | `KERNELS = os.path.join(CODE, "kernels-2026-11-13", "run_kernels.sh")` | `KERNELS`: the path of `run_kernels.sh` in the folder `kernels-2026-11-13`. |
| 39 | `CPU = "/sys/devices/system/cpu"` | `CPU`: the folder of Linux with one folder per CPU. The fake tree has the same folder below its root. |
| 40 | `REAL_SLEEP = shutil.which("sleep")` | `REAL_SLEEP`: the full path of the real program `sleep`. The stand-ins use it. A stand-in named `sleep` stands first in the search path of the scripts under test (lines 407 to 409). |
| 41 | `sys.path.insert(0, X)` | Puts the folder `X` at the front of the search path of Python. So the next two lines import the files beside this one. |
| 42 | `import hwwatch  # noqa: E402` | Imports `hwwatch.py` as a module. Some checks call its functions directly. `# noqa: E402` tells a style checker not to report an import that does not stand at the top of the file. |
| 43 | `import clock_from_counts  # noqa: E402` | Imports `clock_from_counts.py` as a module, for the checks of lines 332 to 357. |
| 45 | `FAILS = []` | `FAILS`: the names of the checks that failed, empty at the start. |
| 46 | `COUNT = [0]` | `COUNT`: a list with one number, the count of checks so far. The function `check` changes the number inside the list. So it needs no `global` statement. |

### Helpers `check` and `put` (lines 48 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 49 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of the file goes through it. `name` says what the check proves. `ok` is the result of the test. `detail` is shown when the check fails. |
| 50 | `    COUNT[0] += 1` | Adds 1 to the count of checks. |
| 51 | `    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [" + str(detail)[:700] + "]") if detail and not ok else ""))` | Prints one line: `PASS` or `FAIL`, two spaces and the name. For a failed check with a detail, the line also holds the first 700 characters of the detail in square brackets. |
| 52 | `    sys.stdout.flush()` | Passes the line to the output at once. Without this, Python would keep the line in a buffer for some time when the output is a file or a pipe. |
| 53 | `    if not ok:` | Tests whether the check failed. |
| 54 | `        FAILS.append(name)` | Then: adds its name to `FAILS`. |
| 55 | `    return ok` | Returns the result of the test. |
| 58 | `def put(path, text):` | Starts the function `put`. It writes a text file and creates the folders above it. |
| 59 | `    os.makedirs(os.path.dirname(path), exist_ok=True)` | Creates the folder of the file with all folders above it. `exist_ok=True`: a folder that exists is no error. |
| 60 | `    with open(path, "w") as f:` | Opens the file for writing. An older file is replaced. |
| 61 | `        f.write(text + "\n")` | Writes the text and one line break. |

### Function `make_tree`: the fake `/sys` and `/proc` tree (lines 64 to 91)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `def make_tree(root, ncpu, with_energy=True):` | Starts the function `make_tree`. It builds the copied file tree below the folder `root`: files as Linux shows them below `/sys` and `/proc`, for `ncpu` CPUs. Each file is a normal text file that `put` writes. `hwwatch.py` reads the tree when it gets `--root` with this folder, and `hw.sh` passes the folder in `HW_ROOT`. With `with_energy=False` the tree has no sensor files. |
| 65 | `    """Files as Linux shows them for ncpu CPUs with the driver cppc_cpufreq. All values are invented."""` | Docstring: the files are those that Linux shows for `ncpu` CPUs with the frequency driver `cppc_cpufreq`. All values are invented. |
| 66 | `    for name, text in (("online", "0-%d" % (ncpu - 1)), ("offline", ""), ("isolated", ""), ("possible", "0-%d" % (ncpu - 1)),` | Starts a loop over five files for the whole system, each with its text. `online` and `possible` hold the CPU list from 0 to `ncpu` minus 1, for example `0-3`. `offline` and `isolated` are empty. The list continues in line 67. |
| 67 | `                       ("cpufreq/boost", "0")):` | The fifth file: `cpufreq/boost` holds `0`. So boost is off. |
| 68 | `        put("%s%s/%s" % (root, CPU, name), text)` | Writes the file below `root`, in the folder `/sys/devices/system/cpu`. |
| 69 | `    for c in range(ncpu):` | Starts a loop over the CPUs. |
| 70 | `        base = "%s%s/cpu%d/" % (root, CPU, c)` | `base`: the folder of the CPU in the tree. |
| 71 | `        for name, text in (("cpuinfo_max_freq", "2800000"), ("cpuinfo_min_freq", "1600000"), ("scaling_cur_freq", "2800000"),` | Starts a loop over ten files of the folder `cpufreq`, each with its text. The highest frequency `cpuinfo_max_freq` is 2800000 kHz (2.8 GHz). The lowest frequency `cpuinfo_min_freq` is 1600000 kHz. The requested rate `scaling_cur_freq` is 2800000 kHz. The list continues in lines 72 to 74. |
| 72 | `                           ("scaling_max_freq", "2800000"), ("scaling_min_freq", "1600000"), ("cpuinfo_avg_freq", "2797265"),` | Continues the list: Linux may request rates from 1600000 kHz (`scaling_min_freq`) to 2800000 kHz (`scaling_max_freq`). The average clock rate `cpuinfo_avg_freq` is 2797265 kHz. |
| 73 | `                           ("perf_limited", "0"), ("scaling_governor", "performance"), ("scaling_driver", "cppc_cpufreq"),` | Continues the list: the throttle flag `perf_limited` is 0. The governor is `performance`, and the driver is `cppc_cpufreq`. |
| 74 | `                           ("cpuinfo_cur_freq", "1")):` | Ends the list: `cpuinfo_cur_freq` holds `1`. The probe must never read this file, and a check tests that (line 172). |
| 75 | `            put(base + "cpufreq/" + name, text)` | Writes the file into the folder `cpufreq` of the CPU. |
| 76 | `        for name, text in (("feedback_ctrs", "ref:1000 del:1000"), ("highest_perf", "280"), ("nominal_perf", "280"),` | Starts a loop over ten files of the folder `acpi_cppc`, each with its text. The counter file `feedback_ctrs` starts with `ref:1000 del:1000`. `highest_perf` and `nominal_perf` are 280. The list continues in lines 77 to 79. |
| 77 | `                           ("lowest_perf", "160"), ("lowest_nonlinear_perf", "160"), ("reference_perf", "280"),` | Continues the list: `lowest_perf` and `lowest_nonlinear_perf` are 160, and `reference_perf` is 280. |
| 78 | `                           ("nominal_freq", "2800"), ("lowest_freq", "1600"), ("guaranteed_perf", "0"),` | Continues the list: `nominal_freq` is 2800 MHz and `lowest_freq` is 1600 MHz. So one performance unit stands for 10 MHz, and 280 units stand for 2800 MHz. `guaranteed_perf` is 0. |
| 79 | `                           ("wraparound_time", "18446744073709551615")):` | Ends the list: `wraparound_time` holds 18446744073709551615, the largest number of 64 bits. |
| 80 | `            put(base + "acpi_cppc/" + name, text)` | Writes the file into the folder `acpi_cppc` of the CPU. |
| 81 | `    put(root + "/proc/sys/kernel/random/boot_id", "00000000-test-boot")` | Writes the boot id of the tree: the text `00000000-test-boot`. |
| 82 | `    put(root + "/proc/uptime", "100.00 1000.00")` | Writes `/proc/uptime` of the tree: `100.00 1000.00`. |
| 83 | `    put(root + "/proc/loadavg", "0.00 0.00 0.00 1/100 1234")` | Writes `/proc/loadavg` of the tree: three load averages of 0.00, then 1 runnable task of 100 tasks, then a process id. |
| 84 | `    put(root + "/proc/cmdline", "test")` | Writes `/proc/cmdline` of the tree: the word `test`. |
| 85 | `    if with_energy:` | The three sensor files and the file `uevent` are written only with `with_energy`. |
| 86 | `        put(root + "/sys/class/hwmon/hwmon0/name", "power_meter")` | Writes the name of one sensor device, `hwmon0`: `power_meter`. |
| 87 | `        put(root + "/sys/class/hwmon/hwmon0/energy1_input", "5000000")` | Writes its energy counter `energy1_input`: 5000000 microjoules, which is 5 J. |
| 88 | `        put(root + "/sys/class/hwmon/hwmon0/power1_average", "100000000")` | Writes its file `power1_average`: 100000000 microwatts, which is 100 W. |
| 89 | `        put(root + "/sys/class/hwmon/hwmon0/uevent", "must not be read")` | Writes a file `uevent` with the text `must not be read`. The pattern of the sensor files does not accept this name. A check tests that the snapshot leaves it out (line 163). |

### Helpers `setv`, `advance`, `tool` and `lines` (lines 92 to 111)

| Line | Source | Explanation |
|---:|---|---|
| 92 | `def setv(root, cpu, rel, text):` | Starts the function `setv`. It writes a new text into one file of one CPU of a tree. `rel` is the path below the folder of the CPU. |
| 93 | `    put("%s%s/cpu%d/%s" % (root, CPU, cpu, rel), text)` | Writes the file with `put`. |
| 96 | `def advance(root, cpu, dref, ddel):` | Starts the function `advance`. It adds `dref` to the counter `ref` and `ddel` to the counter `del` of one CPU of a tree. So a check decides which counter ratio a process seems to have had. |
| 97 | `    path = "%s%s/cpu%d/acpi_cppc/feedback_ctrs" % (root, CPU, cpu)` | `path`: the counter file of the CPU. |
| 98 | `    m = re.match(r"ref:(\d+) del:(\d+)", open(path).read())` | Reads the file. The pattern takes the two numbers: group 1 holds `ref` and group 2 holds `del`. |
| 99 | `    put(path, "ref:%d del:%d" % (int(m.group(1)) + dref, int(m.group(2)) + ddel))` | Writes the file again with both numbers raised. |
| 102 | `def tool(*args, **kw):` | Starts the function `tool`. It runs `hwwatch.py` with the given arguments and waits for its end. |
| 103 | `    return subprocess.run([sys.executable, TOOL] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Starts `hwwatch.py` with the same Python program that runs this test (`sys.executable`). The standard output and the error output are collected, each on its own. The call continues in line 104. |
| 104 | `                          universal_newlines=True, **kw)` | `universal_newlines=True` gives the outputs as text. `**kw` passes more options on. The function returns an object with the exit status (`returncode`) and the two outputs (`stdout`, `stderr`). |
| 107 | `def lines(path):` | Starts the function `lines`. It returns the lines of a text file. |
| 108 | `    with open(path) as f:` | Opens the file. |
| 109 | `        return f.read().split("\n")` | Returns its text, split at the line breaks. A file that ends with a line break gives an empty last entry. |

### `tool_checks`: the CPU limit and the command `check` (lines 112 to 150)

| Line | Source | Explanation |
|---:|---|---|
| 112 | `# ----------------------------------------------------------------------------- hwwatch.py` | Comment: a divider. The checks of `hwwatch.py` follow. |
| 114 | `def tool_checks(tmp):` | Starts the function `tool_checks`. `tmp` is the temporary folder of the test. |
| 115 | `    root = os.path.join(tmp, "tree4")` | `root`: the folder of a tree, named `tree4`. |
| 116 | `    make_tree(root, 4)` | Builds the tree with 4 CPUs. This is the first use of the fake tree: `make_tree` writes 20 small text files per CPU (10 in `cpufreq`, 10 in `acpi_cppc`) and 13 files for the whole system (lines 64 to 89). |
| 117 | `    out = os.path.join(tmp, "o")` | `out`: a folder for the output files of the tool. |
| 118 | `    os.makedirs(out)` | Creates it. |
| 120 | `    # The sharing rule of CRB: the per-CPU files of CPUs 126 and 127 must never be read.` | Comment: the sharing rule of CRB. The files of the CPUs 126 and 127 must never be read. |
| 121 | `    for cpus in ("126", "0-127", "120", "0,127"):` | Starts a loop over four CPU lists that each hold a CPU above 119: `126`, `0-127`, `120` and `0,127`. |
| 122 | `        r = tool("snap", "--cpus", cpus, "--root", root, "--out", os.path.join(out, "bad.txt"))` | Runs `hwwatch.py snap` with this list and with the output file `bad.txt`. |
| 123 | `        check("a CPU above 119 is refused, and no file is written: --cpus %s" % cpus,` | Check, once per list: a CPU above 119 is refused, and no file is written. It matters for the sharing rule of line 120: a wrong CPU list in a run script must not lead to a read of a CPU that another user of CRB uses. The call continues in line 124. |
| 124 | `              r.returncode != 0 and "126 and 127" in r.stderr and not os.path.exists(os.path.join(out, "bad.txt")), r.stderr)` | The check passes when three things hold: the exit status is not 0, the error message holds the text `126 and 127`, and the file `bad.txt` does not exist. |
| 125 | `    r = tool("snap", "--cpus", "1,1", "--root", root, "--out", os.path.join(out, "bad.txt"))` | Runs `snap` with the list `1,1`. |
| 126 | `    check("a CPU that is named twice is refused", r.returncode != 0 and "twice" in r.stderr, r.stderr)` | Check: a CPU that is named twice is refused. The exit status must not be 0, and the message must hold the word `twice`. So a mistake in a CPU list is reported. |
| 127 | `    check("CPU lists keep the order of the text", hwwatch.parse_cpus("2,0-1,119") == [2, 0, 1, 119])` | Check: a CPU list keeps the order of its text. `parse_cpus` must turn `2,0-1,119` into 2, 0, 1, 119. It matters for the sampler file: its columns follow the order of the list. |
| 129 | `    # check: what the tool cannot work without` | Comment: the command `check` tests what the tool cannot work without. |
| 130 | `    r = tool("check", "--cpus", "0-3", "--root", root)` | Runs `hwwatch.py check` for the CPUs 0 to 3 of the tree. |
| 131 | `    check("check passes when the two counters, the average rate and the requested rate are readable", r.returncode == 0 and r.stdout.startswith("ok:"), r.stdout + r.stderr)` | Check: `check` passes when the two counters, the average rate and the requested rate are readable. The exit status must be 0 and the output must start with `ok:`. This is the normal case of the test that `hw_check` runs before a benchmark. |
| 132 | `    os.rename("%s%s/cpu2/acpi_cppc/feedback_ctrs" % (root, CPU), os.path.join(tmp, "moved"))` | Moves the counter file of CPU 2 out of the tree. `os.rename` gives it the name `moved` in the temporary folder. |
| 133 | `    r = tool("check", "--cpus", "0-3", "--root", root)` | Runs `check` again. |
| 134 | `    check("check fails and names the CPU when one CPU has no counter file", r.returncode == 1 and "FAILED: cpu2 acpi_cppc/feedback_ctrs: !ENOENT" in r.stdout, r.stdout)` | Check: `check` fails and names the CPU when one CPU has no counter file. The exit status must be 1, and the output must hold `FAILED: cpu2 acpi_cppc/feedback_ctrs: !ENOENT`. Without the counters the report cannot compute a clock rate. So this must be found before a benchmark starts. |
| 135 | `    os.rename(os.path.join(tmp, "moved"), "%s%s/cpu2/acpi_cppc/feedback_ctrs" % (root, CPU))` | Moves the counter file back. |
| 136 | `    real = hwwatch.read_value` | `real`: the real function `read_value` of the module `hwwatch`, kept for line 149. |
| 137 | `    quiet = contextlib.redirect_stdout(io.StringIO())       # cmd_check prints its lines; they are not test output` | `quiet`: an object that sends printed lines into a buffer in memory while it is active. Comment: `cmd_check` prints its lines, and they are not test output. |
| 138 | `    hwwatch.read_value = lambda p: "!EAGAIN" if p.endswith("cpuinfo_avg_freq") else real(p)` | Replaces `read_value` in the module with a function that returns `!EAGAIN` for every path that ends with `cpuinfo_avg_freq`. For every other path it calls the real function. So the tree behaves like a machine whose cores are idle. |
| 139 | `    try:` | Starts a block. Lines 148 to 149 put the real function back also when a statement of the block fails. |
| 140 | `        a = type("A", (), dict(cpus="0-3", root=root))` | `a`: a small object with the two options that `cmd_check` reads: the CPU list `0-3` and the root of the tree. `type` creates a class with these two values. |
| 141 | `        with quiet:` | Hides the printed lines of the next call. |
| 142 | `            rc = hwwatch.cmd_check(a)` | `rc`: the result of a direct call of `cmd_check` inside this Python process. |
| 143 | `        check("check accepts EAGAIN for the average rate: an idle core gives it, the file exists", rc == 0)` | Check: `check` accepts `EAGAIN` for the average rate. An idle core gives this error, and the file exists. The result must be 0. Without this rule `hw_check` would fail whenever the tested core is idle. |
| 144 | `        hwwatch.read_value = lambda p: "!ENOENT" if p.endswith("cpuinfo_avg_freq") else real(p)` | Replaces `read_value` again: now the average rate gives `!ENOENT`, as if the file did not exist. |
| 145 | `        with quiet:` | Hides the printed lines of the next call. |
| 146 | `            rc = hwwatch.cmd_check(a)` | `rc`: the result of a second direct call of `cmd_check`. |
| 147 | `        check("check fails when the file of the average rate is missing", rc == 1)` | Check: `check` fails when the file of the average rate is missing. The result must be 1. So only `EAGAIN` is accepted, not every error. |
| 148 | `    finally:` | The `finally` part runs in every case. |
| 149 | `        hwwatch.read_value = real` | Puts the real `read_value` back into the module. |

### `tool_checks`: the commands `snap` and `probe` (lines 151 to 174)

| Line | Source | Explanation |
|---:|---|---|
| 151 | `    # snap` | Comment: the checks of the command `snap` follow. |
| 152 | `    os.remove("%s%s/cpu3/cpufreq/perf_limited" % (root, CPU))` | Deletes the file `perf_limited` of CPU 3 from the tree. So one value of the snapshot cannot be read. |
| 153 | `    snap = os.path.join(out, "s.txt")` | `snap`: the path of the output file `s.txt`. |
| 154 | `    r = tool("snap", "--cpus", "0-3", "--root", root, "--label", "my label", "--out", snap)` | Runs `hwwatch.py snap` for the CPUs 0 to 3 with the label `my label`, which holds a space. |
| 155 | `    s = hwwatch.read_snap(snap) if r.returncode == 0 else None` | `s`: the snapshot as the function `read_snap` of `hwwatch.py` reads it, or `None` when the command failed. |
| 156 | `    check("snap writes one line per CPU with the six values", bool(s) and sorted(s["cpu"]) == [0, 1, 2, 3]` | Check: `snap` writes one line per CPU with the six values. The file must hold exactly the CPUs 0 to 3. The call continues in line 157. |
| 157 | `          and all(set(s["cpu"][c]) == {"t_ns", "scaling_cur_freq", "scaling_max_freq", "scaling_min_freq", "cpuinfo_avg_freq", "perf_limited", "ref", "del"} for c in s["cpu"]), r.stderr)` | Each CPU line must hold exactly eight keys: `t_ns`, the five files of `cpufreq`, and `ref` and `del` from the sixth file. The report needs these values to compute the rates and the flags. |
| 158 | `    check("snap writes a missing file as !ENOENT and counts it in the end line",` | Check: `snap` writes a missing file as `!ENOENT` and counts it in its footer. So a value that could not be read stays visible in the record. The call continues in line 159. |
| 159 | `          bool(s) and s["cpu"][3]["perf_limited"] == "!ENOENT" and s["end"]["unreadable"] == "1" and s["complete"])` | Three things must hold: `perf_limited` of CPU 3 is `!ENOENT`, the footer holds `unreadable=1`, and the file has a footer (`complete`). |
| 160 | `    check("snap records the label without spaces, the boot id and the energy counter",` | Check: `snap` records the label without spaces, the boot id and the energy counter. The call continues in lines 161 to 162. |
| 161 | `          bool(s) and s["head"]["label"] == "my_label" and s["s"]["/proc/sys/kernel/random/boot_id"] == "00000000-test-boot"` | The label must be `my_label`: the space became an underscore. So the header line can still be split at spaces. The boot id must be the text of the tree. |
| 162 | `          and s["s"]["/sys/class/hwmon/hwmon0/energy1_input"] == "5000000")` | The energy counter `energy1_input` must be 5000000. The report computes the energy of a process from this value in two snapshots. |
| 163 | `    check("snap reads only the sensor files of its list (not uevent)", bool(s) and "/sys/class/hwmon/hwmon0/uevent" not in s["s"])` | Check: `snap` reads only the sensor files of its list. The file `uevent` of the tree must not be in the snapshot. So the tool reads no file of a sensor folder that its patterns do not name. |
| 164 | `    put("%s%s/cpu3/cpufreq/perf_limited" % (root, CPU), "0")` | Writes the file `perf_limited` of CPU 3 again, with `0`. |
| 166 | `    # probe` | Comment: the checks of the command `probe` follow. |
| 167 | `    probe = os.path.join(out, "p.txt")` | `probe`: the path of the output file `p.txt`. |
| 168 | `    r = tool("probe", "--cpus", "0-3", "--root", root, "--out", probe)` | Runs `hwwatch.py probe` for the CPUs 0 to 3. |
| 169 | `    p = hwwatch.read_snap(probe) if r.returncode == 0 else None` | `p`: the probe as `read_snap` reads it, or `None` when the command failed. |
| 170 | `    check("probe writes every file of cpufreq and acpi_cppc", bool(p) and p["f"][1]["acpi_cppc/nominal_freq"] == "2800"` | Check: `probe` writes every file of `cpufreq` and `acpi_cppc`. For CPU 1 the value of `acpi_cppc/nominal_freq` must be 2800. The call continues in line 171. |
| 171 | `          and p["f"][1]["cpufreq/cpuinfo_max_freq"] == "2800000" and len(p["f"][1]) == 19, r.stderr or (p and sorted(p["f"][1])))` | `cpufreq/cpuinfo_max_freq` of CPU 1 must be 2800000, and CPU 1 must have exactly 19 files: 9 of `cpufreq` (10 minus the one that is skipped) and 10 of `acpi_cppc`. The report takes the constants for the conversion to kHz from these lines. |
| 172 | `    check("probe never reads cpuinfo_cur_freq (a read interrupts the core and needs root)", bool(p) and all("cpufreq/cpuinfo_cur_freq" not in p["f"][c] for c in p["f"]))` | Check: `probe` never reads `cpuinfo_cur_freq`. No CPU of the probe may have a line for this file. By the name of the check, a read of it interrupts the core and needs root. |
| 173 | `    check("probe lists the telemetry folders and says when one is missing", bool(p) and p["l"]["/dev/scmi"] == "!ENOENT" and p["l"]["/sys/class/hwmon"] == "hwmon0")` | Check: `probe` lists the telemetry folders and says when one is missing. The tree has no folder `/dev/scmi`. So its line must hold `!ENOENT`. The line of `/sys/class/hwmon` must hold `hwmon0`. |

### `tool_checks`: the command `watch` (lines 175 to 202)

| Line | Source | Explanation |
|---:|---|---|
| 175 | `    # watch` | Comment: the checks of the command `watch` follow. |
| 176 | `    w = os.path.join(out, "w.txt")` | `w`: the path of the output file `w.txt`. |
| 177 | `    child = subprocess.Popen([REAL_SLEEP, "30"])` | `child`: a process for the sampler to watch. It is the real `sleep` with 30 s. |
| 178 | `    os.remove("%s%s/cpu1/cpufreq/cpuinfo_avg_freq" % (root, CPU))` | Deletes the file `cpuinfo_avg_freq` of CPU 1 from the tree. The sampler cannot open it. |
| 179 | `    proc = subprocess.Popen([sys.executable, TOOL, "watch", "--cpus", "0-3", "--root", root, "--pid", str(child.pid), "--period-s", "0.05", "--max-s", "20", "--out", w])` | `proc`: the sampler, started in the background for the CPUs 0 to 3. It watches `child`, takes a sample each 0.05 s and has a time limit of 20 s. |
| 180 | `    time.sleep(0.5)` | Waits 0.5 s while the sampler takes samples. |
| 181 | `    setv(root, 2, "cpufreq/cpuinfo_avg_freq", "2400000")` | Changes the average rate of CPU 2 in the tree to 2400000 kHz while the sampler runs. |
| 182 | `    time.sleep(0.4)` | Waits 0.4 s more. |
| 183 | `    child.kill()` | Kills the watched process. |
| 184 | `    child.wait()` | Waits until it has ended. |
| 185 | `    rc = proc.wait(timeout=10)` | `rc`: the exit status of the sampler. `wait` allows at most 10 s for its end. |
| 186 | `    cpus, rows, end = hwwatch.read_watch(w)` | Reads the sampler file with `read_watch`: the CPU list, the rows and the footer. |
| 187 | `    check("watch ends with status 0 when the watched process is gone", rc == 0 and end.get("reason") == "pid_gone", end)` | Check: `watch` ends with status 0 when the watched process is gone. The footer must give the reason `pid_gone`. In a test the sampler watches the run script. So it ends by itself when the script is gone and `hw_done` did not run. |
| 188 | `    check("watch writes one value per CPU and sample, and na for a CPU without the file",` | Check: `watch` writes one value per CPU and sample, and `na` for a CPU without the file. The call continues in line 189. |
| 189 | `          cpus == [0, 1, 2, 3] and len(rows) >= 5 and all(len(r[1]) == 4 for r in rows) and all(r[1][1] is None for r in rows) and rows[0][1][0] == 2797265, rows[:2])` | The conditions: the CPU list is 0 to 3, there are at least 5 rows, each row has 4 values, the value of CPU 1 is missing in every row, and the first value of CPU 0 is 2797265 kHz. So a column always belongs to the same CPU, also when a file is missing. |
| 190 | `    check("watch reads the file again for each sample (a later sample holds the new value)", rows and rows[0][1][2] == 2797265 and rows[-1][1][2] == 2400000)` | Check: `watch` reads the file again for each sample. The first row must hold 2797265 kHz for CPU 2, and the last row 2400000 kHz. The sampler keeps each file open. So this check proves that a later sample holds the value of its own moment and not the first value. |
| 191 | `    check("watch counts the na values in its end line", end.get("na") == str(len(rows)), end)` | Check: `watch` counts the `na` values in its footer. The count must be equal to the number of rows: one missing value per row, for CPU 1. |
| 192 | `    put("%s%s/cpu1/cpufreq/cpuinfo_avg_freq" % (root, CPU), "2797265")` | Writes the file `cpuinfo_avg_freq` of CPU 1 again. |
| 193 | `    setv(root, 2, "cpufreq/cpuinfo_avg_freq", "2797265")` | Sets the average rate of CPU 2 back to 2797265 kHz. |
| 194 | `    proc = subprocess.Popen([sys.executable, TOOL, "watch", "--cpus", "0", "--root", root, "--pid", str(os.getpid()), "--period-s", "0.05", "--max-s", "20", "--out", w])` | Starts a second sampler for CPU 0. It watches the process of this test, which does not end. |
| 195 | `    time.sleep(0.4)` | Waits 0.4 s. |
| 196 | `    proc.send_signal(signal.SIGTERM)` | Sends the signal SIGTERM to the sampler. `hw_done` stops the sampler of a test in the same way. |
| 197 | `    rc = proc.wait(timeout=10)` | `rc`: its exit status. |
| 198 | `    check("watch ends with status 0 and an end line on SIGTERM", rc == 0 and hwwatch.read_watch(w)[2].get("reason") == "signal")` | Check: `watch` ends with status 0 and a footer on SIGTERM. The footer must give the reason `signal`. `hw_done` writes a `FAILED` line when it finds no such footer. So a normal stop must write it. |
| 199 | `    r = tool("watch", "--cpus", "0", "--root", root, "--pid", str(os.getpid()), "--period-s", "0.05", "--max-s", "0.2", "--out", w)` | Runs a third sampler in the foreground with a time limit of 0.2 s. |
| 200 | `    check("watch ends by itself after --max-s", r.returncode == 0 and hwwatch.read_watch(w)[2].get("reason") == "max_s")` | Check: `watch` ends by itself after `--max-s`. The exit status must be 0 and the reason `max_s`. The time limit ends a sampler that nothing else stops. `hw_check` also looks for this reason in its short run of the sampler. |

### Functions `write_result` and `report`: a result folder made with the tool (lines 203 to 225)

| Line | Source | Explanation |
|---:|---|---|
| 203 | `def write_result(folder, root, cpus, during, label="001-p"):` | Starts the function `write_result`. It builds the folder `hw` of a result folder with the real commands of `hwwatch.py`, in the order in which `hw.sh` runs them. `during` is a function that stands for the benchmark process: it changes the tree between the two snapshots. |
| 204 | `    """A result folder as hw.sh writes it, made with the tool: probe, snapshot, during(), snapshot. The watch file` | Docstring: the function writes a result folder as `hw.sh` writes it, made with the tool: the probe, a snapshot, `during()`, a snapshot. The sentence goes on in line 205. |
| 205 | `    is written while during() runs."""` | Docstring: the watch file is written while `during()` runs. |
| 206 | `    hw = os.path.join(folder, "hw")` | `hw`: the folder `hw` in the result folder. |
| 207 | `    os.makedirs(hw, exist_ok=True)` | Creates it. |
| 208 | `    assert tool("probe", "--cpus", cpus, "--root", root, "--out", os.path.join(hw, "probe.txt")).returncode == 0` | Writes `probe.txt` with the command `probe`. `assert` stops the test with an error when the command fails. |
| 209 | `    proc = subprocess.Popen([sys.executable, TOOL, "watch", "--cpus", cpus, "--root", root, "--pid", str(os.getpid()), "--period-s", "0.05", "--max-s", "30", "--out", os.path.join(hw, "watch.txt")])` | Starts the sampler in the background. It samples the CPUs of the list each 0.05 s into `watch.txt`, watches the process of this test and has a time limit of 30 s. |
| 210 | `    time.sleep(0.3)` | Waits 0.3 s. This gives the sampler time to start before the first snapshot. |
| 211 | `    assert tool("snap", "--cpus", cpus, "--root", root, "--label", label, "--out", os.path.join(hw, label + ".before.txt")).returncode == 0` | Writes the snapshot before the process: the file with the label and `.before.txt`. |
| 212 | `    time.sleep(0.2)` | Waits 0.2 s. The sampler takes samples inside the window. |
| 213 | `    during()` | Calls `during`. It changes the counters and other files of the tree, as a process would. |
| 214 | `    time.sleep(0.2)` | Waits 0.2 s. |
| 215 | `    assert tool("snap", "--cpus", cpus, "--root", root, "--label", label, "--out", os.path.join(hw, label + ".after.txt")).returncode == 0` | Writes the snapshot after the process: the file with the label and `.after.txt`. |
| 216 | `    proc.send_signal(signal.SIGTERM)` | Sends the signal SIGTERM to the sampler. |
| 217 | `    proc.wait(timeout=10)` | Waits until the sampler has ended, at most 10 s. |
| 218 | `    put(os.path.join(hw, "status.txt"), "ok utc x done: 1 processes")` | Writes a file `status.txt` with one `ok` line. |
| 221 | `def report(folder, *extra):` | Starts the function `report`. It runs `hwwatch.py report --json` for one folder and returns the result as Python data. `extra` holds more options, for example `--tol`. |
| 222 | `    r = tool("report", "--json", *extra, folder)` | Runs the command. |
| 223 | `    return json.loads(r.stdout)[0] if r.returncode == 0 else {"error": r.stderr}` | Returns the first entry of the JSON list, which is the result of this folder. When the command failed, it returns a dictionary with the error text. |

### `report_checks`: a process at full speed (lines 226 to 250)

| Line | Source | Explanation |
|---:|---|---|
| 226 | `def report_checks(tmp):` | Starts the function `report_checks`. It tests the rules of `hwwatch.py report` on result folders that `write_result` builds. |
| 227 | `    # 1. a process at full speed: no flag may fire` | Comment: case 1 is a process at full speed. No flag may be set. |
| 228 | `    root = os.path.join(tmp, "treeA")` | `root`: the folder of a second tree, `treeA`. |
| 229 | `    make_tree(root, 4)` | Builds it with 4 CPUs. |
| 231 | `    def full():` | Starts the inner function `full`. It stands for a process at full speed. |
| 232 | `        for c in range(4):` | Starts a loop over the 4 CPUs. |
| 233 | `            advance(root, c, 1000000, 999900)      # ratio 0.9999: 2799720 kHz` | Advances `ref` by 1000000 and `del` by 999900. Comment: the ratio is 0.9999, which gives 2799720 kHz. That is above the limit of 2772000 kHz (99 % of 2800000 kHz). |
| 234 | `        put(root + "/sys/class/hwmon/hwmon0/energy1_input", "9000000")` | Raises the energy counter of the tree from 5000000 to 9000000. The change is 4000000 microjoules, which is 4 J. |
| 235 | `    fa = os.path.join(tmp, "resA")` | `fa`: the result folder `resA`. |
| 236 | `    write_result(fa, root, "0-3", full)` | Builds the folder with `full` as the process. |
| 237 | `    p = report(fa)["processes"][0]` | `p`: the entry of the first process in the report. |
| 238 | `    check("report: a process at full speed gets no flag", p.get("flags") == [], p)` | Check: a process at full speed gets no flag. The list of flags must be empty. This is the control case for all flag checks below: a flag that was set here would be wrong. |
| 239 | `    check("report: the rate of a core is reference_perf * (change of del) / (change of ref), in kHz by the linear rule",` | Check: the rate of a core is `reference_perf` times (change of `del`) divided by (change of `ref`), in kHz by the rule `linear`. This check proves the rule and the direction of the ratio: `del` divided by `ref`, not the reverse. The call continues in line 240. |
| 240 | `          p.get("conversion") == ["linear"] and abs(p["avg_khz"][0] - 2799720) < 1 and abs(p["avg_khz"][2] - 2799720) < 1 and p["counter_cpus"] == 4, p)` | The conditions: the only rule is `linear`, the lowest and the highest rate are within 1 kHz of 2799720, and all 4 CPUs have a ratio. The number follows from the tree: 280 units times 0.9999 are 279.972 units, and one unit is 10000 kHz. |
| 241 | `    check("report: the sampled rates of the process come from the samples between its two snapshots", p["samples"] >= 8 and p["sample_khz"][0] == 2797265 and p["samples_low"] == 0, p)` | Check: the sampled rates of the process come from the samples between its two snapshots. There must be at least 8 values, the lowest must be 2797265 kHz, and none may be below the limit. |
| 242 | `    key = "/sys/class/hwmon/hwmon0/energy1_input"` | `key`: the path of the energy counter. |
| 243 | `    check("report: an energy counter gives the energy between the two snapshots", p["energy"].get(key) == 4000000, p["energy"])` | Check: an energy counter gives the energy between the two snapshots. The change must be 4000000, the difference of line 234. |
| 244 | `    check("report: the time of the energy runs to the end of the second snapshot, where the sensor files are read", p["sensor_seconds"] > p["seconds"] > 0.3, p)` | Check: the time of the energy runs to the end of the second snapshot, where the sensor files are read. `sensor_seconds` must be above `seconds`, and `seconds` must be above 0.3 s. With the shorter time the average power would be too high. |
| 245 | `    text = tool("report", fa).stdout` | `text`: the text form of the report of this folder. |
| 246 | `    m = re.search(r"energy 001-p %s: 4\.000 J, (\d+\.\d\d) W on average over (\d+\.\d) s" % re.escape(key), text)` | The pattern looks for the energy line of the process `001-p`: the path of the counter, `4.000 J`, then the average power in W with 2 decimals (group 1) and the time in s with one decimal (group 2). `re.escape` makes every character of the path stand for itself in the pattern. |
| 247 | `    check("report: the text form prints the energy in J and the average power in W (energy / time)", bool(m) and abs(float(m.group(1)) - 4.0 / p["sensor_seconds"]) < 0.02, text)` | Check: the text form prints the energy in J and the average power in W, which is the energy divided by the time. The printed power must be within 0.02 W of 4.0 J divided by `sensor_seconds`. |
| 248 | `    check("report: the text form prints the median counter ratio and how long the snapshots took",` | Check: the text form prints the median counter ratio and how long the snapshots took. The call continues in line 249. |

Line 249 holds a backslash directly before a `|`. It stands outside the table:

```text
          re.search(r"001-p +4 +\d+\.\d \| +2799720 +2799720 +2799720 +\d+ +0\.9999 \|", text) is not None and "a snapshot took " in text, text)
```

Explanation of line 249: The pattern looks for the row of the process: the name `001-p`, 4 CPUs, the window with one decimal, a `|`, three times 2799720 (the lowest, the median and the highest rate), the number of the lowest CPU, the ratio `0.9999` and a second `|`. The text must also hold `a snapshot took`.

### `report_checks`: a slow core, the throttle flag, limits of Linux, CPU list and boot (lines 251 to 286)

| Line | Source | Explanation |
|---:|---|---|
| 251 | `    # 2. one core at 90 %: only that core is flagged` | Comment: case 2 is one core at 90 %. Only that core may be flagged. |
| 252 | `    def slow():` | Starts the inner function `slow`. |
| 253 | `        for c in range(4):` | Starts a loop over the 4 CPUs. |
| 254 | `            advance(root, c, 1000000, 900000 if c == 1 else 1000000)` | Advances `ref` by 1000000 for every CPU. `del` advances by 900000 for CPU 1 and by 1000000 for the others. So CPU 1 has a ratio of 0.9, which gives 2520000 kHz. |
| 255 | `        setv(root, 2, "cpufreq/cpuinfo_avg_freq", "2400000")` | Sets the average rate of CPU 2 to 2400000 kHz. So the samples of CPU 2 fall below the limit. |
| 256 | `    fb = os.path.join(tmp, "resB")` | `fb`: the result folder `resB`. |
| 257 | `    write_result(fb, root, "0-3", slow)` | Builds the folder with `slow` as the process. |
| 258 | `    p = report(fb)["processes"][0]` | `p`: the entry of the process. |
| 259 | `    check("report: a core whose counters give 90 % is flagged LOW_AVG, with its rate and its number, and no other core is named",` | Check: a core whose counters give 90 % is flagged `LOW_AVG`, with its rate and its number, and no other core is named. This is the main purpose of the record: to see a core that ran below its full clock rate during a process. The call continues in line 260. |
| 260 | `          "LOW_AVG" in p["flags"] and abs(p["avg_khz"][0] - 2520000) < 1 and p["avg_khz_min_cpu"] == 1 and p["low_avg_cpus"] == [1] and abs(p["avg_khz"][2] - 2800000) < 1, p)` | The conditions: the flag is set, the lowest rate is within 1 kHz of 2520000, the lowest CPU is CPU 1, the list of low CPUs holds only CPU 1, and the highest rate is within 1 kHz of 2800000. |
| 261 | `    check("report: a sampled rate below the limit is flagged LOW_SAMPLE and counted", "LOW_SAMPLE" in p["flags"] and p["samples_low"] >= 1 and p["sample_khz"][0] == 2400000, p)` | Check: a sampled rate below the limit is flagged `LOW_SAMPLE` and counted. The flag must be set, at least one sample must be counted as low, and the lowest sample must be 2400000 kHz. So the second source, the sampler, sets its own flag. |
| 262 | `    p5 = report(fb, "--tol", "0.2")["processes"][0]` | `p5`: the report of the same folder with `--tol 0.2`. |
| 263 | `    check("report: --tol sets the limit (20 %: neither 2520000 nor 2400000 kHz is flagged)", "LOW_AVG" not in p5["flags"] and "LOW_SAMPLE" not in p5["flags"], p5)` | Check: `--tol` sets the limit. With 20 % the limit is 2240000 kHz. So neither 2520000 nor 2400000 kHz may be flagged. |
| 264 | `    setv(root, 2, "cpufreq/cpuinfo_avg_freq", "2797265")` | Sets the average rate of CPU 2 back to 2797265 kHz. |
| 266 | `    # 3. the firmware flag, the limits of Linux, the CPU list, the boot` | Comment: case 3 covers the firmware flag, the limits of Linux, the list of online CPUs and the boot. |
| 267 | `    def limited():` | Starts the inner function `limited`. |
| 268 | `        for c in range(4):` | Starts a loop over the 4 CPUs. |
| 269 | `            advance(root, c, 1000000, 1000000)` | Advances both counters by 1000000: full speed. |
| 270 | `        setv(root, 0, "cpufreq/perf_limited", "1")` | Sets the throttle flag `perf_limited` of CPU 0 to 1. |
| 271 | `        setv(root, 3, "cpufreq/scaling_max_freq", "2400000")` | Lowers `scaling_max_freq` of CPU 3 to 2400000 kHz. |
| 272 | `        setv(root, 3, "cpufreq/scaling_cur_freq", "2400000")` | Lowers the requested rate `scaling_cur_freq` of CPU 3 to 2400000 kHz. |
| 273 | `        put("%s%s/online" % (root, CPU), "0-2")` | Changes the list of online CPUs to `0-2`: CPU 3 seems to be offline. |
| 274 | `        put(root + "/proc/sys/kernel/random/boot_id", "another-boot")` | Changes the boot id to `another-boot`: the machine seems to have rebooted. |
| 275 | `    fc = os.path.join(tmp, "resC")` | `fc`: the result folder `resC`. |
| 276 | `    write_result(fc, root, "0-3", limited)` | Builds the folder with `limited` as the process. |
| 277 | `    p = report(fc)["processes"][0]` | `p`: the entry of the process. |
| 278 | `    check("report: perf_limited that goes from 0 to 1 during the process is flagged PERF_LIMITED", "PERF_LIMITED" in p["flags"] and p["perf_limited_set_during"] == 1 and "PERF_LIMITED_ALREADY_SET" not in p["flags"], p)` | Check: a `perf_limited` that goes from 0 to 1 during the process is flagged `PERF_LIMITED`. One CPU must be counted, and `PERF_LIMITED_ALREADY_SET` must not be set. This flag is the direct sign that the firmware throttled a core during the process. |
| 279 | `    check("report: a lowered scaling_max_freq and a lowered request are flagged", "LIMIT_LOWERED" in p["flags"] and "REQUEST_BELOW_MAX" in p["flags"] and p["scaling_cur_freq_min"] == 2400000, p)` | Check: a lowered `scaling_max_freq` and a lowered request are flagged. `LIMIT_LOWERED` and `REQUEST_BELOW_MAX` must be set, and the lowest request must be 2400000 kHz. With these flags a reader can see whether Linux asked a core to run slower, or whether the core was throttled. |
| 280 | `    check("report: a changed list of online CPUs and a reboot are flagged", "ONLINE_CHANGED" in p["flags"] and "BOOT_CHANGED" in p["flags"], p)` | Check: a changed list of online CPUs and a reboot are flagged (`ONLINE_CHANGED`, `BOOT_CHANGED`). By the design note these are the only two signs of a shutdown of the chip that the record can show [Ref1]. |
| 281 | `    fd = os.path.join(tmp, "resD")` | `fd`: the result folder `resD`. |
| 282 | `    write_result(fd, root, "0-3", lambda: [advance(root, c, 1000000, 1000000) for c in range(4)])` | Builds one more folder on the same tree. The process only advances the counters at full speed. The throttle flag of CPU 0 is still 1 from case 3. The list comprehension is used as a short loop. |
| 283 | `    p = report(fd)["processes"][0]` | `p`: the entry of the process. |
| 284 | `    check("report: a flag that was set before the process is reported as ALREADY_SET, not as a new event",` | Check: a flag that was set before the process is reported as `PERF_LIMITED_ALREADY_SET`, not as a new event. The flag stays set until root clears it. So without this rule every later process would report a throttle event that happened earlier. The call continues in line 285. |
| 285 | `          "PERF_LIMITED_ALREADY_SET" in p["flags"] and "PERF_LIMITED" not in p["flags"] and p["perf_limited_set_before"] == 1, p)` | The conditions: `PERF_LIMITED_ALREADY_SET` is set, `PERF_LIMITED` is not set, and one CPU is counted as set before. |

### `report_checks`: missing sources, and the summary of `atx` (lines 287 to 331)

| Line | Source | Explanation |
|---:|---|---|
| 287 | `    # 4. missing sources are named, not guessed` | Comment: case 4. Missing sources are named, not guessed. |
| 288 | `    root2 = os.path.join(tmp, "treeE")` | `root2`: the folder of a third tree, `treeE`. |
| 289 | `    make_tree(root2, 2, with_energy=False)` | Builds it with 2 CPUs and without the sensor files. |
| 290 | `    for c in range(2):` | Starts a loop over the 2 CPUs. |
| 291 | `        os.remove("%s%s/cpu%d/cpufreq/perf_limited" % (root2, CPU, c))` | Deletes the throttle flag file `perf_limited`. |
| 292 | `        setv(root2, c, "acpi_cppc/nominal_freq", "0")` | Sets `nominal_freq` to 0. |
| 293 | `        setv(root2, c, "acpi_cppc/lowest_freq", "0")` | Sets `lowest_freq` to 0. Without these two frequencies the rule `linear` cannot be used. |
| 294 | `    fe = os.path.join(tmp, "resE")` | `fe`: the result folder `resE`. |
| 295 | `    write_result(fe, root2, "0-1", lambda: [advance(root2, c, 1000000, 950000) for c in range(2)])` | Builds the folder. The process advances `ref` by 1000000 and `del` by 950000 for both CPUs: a ratio of 0.95. |
| 296 | `    res = report(fe)` | `res`: the whole report of the folder. |
| 297 | `    p = res["processes"][0]` | `p`: the entry of the process. |
| 298 | `    check("report: without the two frequencies of the firmware table the rule is cpuinfo_max_freq * perf / nominal_perf, and its name is printed",` | Check: without the two frequencies of the firmware table the rule is `cpuinfo_max_freq` times the performance value divided by `nominal_perf`, and the report gives the name of the rule. So a reader of the report can see which rule gave the kHz values. The call continues in line 299. |
| 299 | `          p["conversion"] == ["max"] and abs(p["avg_khz"][0] - 2660000) < 1, p)` | The conditions: the only rule is `max`, and the lowest rate is within 1 kHz of 2660000. That is 2800000 kHz times 0.95. |
| 300 | `    check("report: without a readable perf_limited the process gets NO_THROTTLE_FLAG", "NO_THROTTLE_FLAG" in p["flags"], p)` | Check: without a readable `perf_limited` the process gets `NO_THROTTLE_FLAG`. So a report without a throttle event cannot be read as a proof that no throttling happened. |
| 301 | `    check("report: a result folder without the summary of atx says so", any("no atx_summary.csv" in n for n in res["notes"]), res["notes"])` | Check: a result folder without the summary of `atx` says so. A note must hold the text `no atx_summary.csv`. |
| 302 | `    ff = os.path.join(tmp, "resF")` | `ff`: the result folder `resF`. |
| 303 | `    write_result(ff, root2, "0-1", lambda: None)` | Builds a folder whose process does nothing (`lambda: None`). The counters do not move. |
| 304 | `    p = report(ff)["processes"][0]` | `p`: the entry of the process. |
| 305 | `    check("report: counters that did not move give NO_COUNTERS and no rate", "NO_COUNTERS" in p["flags"] and p["avg_khz"] == [None, None, None], p)` | Check: counters that did not move give `NO_COUNTERS` and no rate. The three rate values must be `None`. A change of 0 allows no ratio, and the report must not print a number in that case. |
| 306 | `    os.remove(os.path.join(ff, "hw", "001-p.after.txt"))` | Deletes the snapshot after the process from `resF`. |
| 307 | `    os.remove(os.path.join(ff, "hw", "watch.txt"))` | Deletes the sampler file from `resF`. |
| 308 | `    res = report(ff)` | `res`: the report of the folder in this state. |
| 309 | `    check("report: a process without the second snapshot gets NO_AFTER, and a missing watch file is named",` | Check: a process without the second snapshot gets `NO_AFTER`, and a missing watch file is named. A process has no second snapshot when the run script was stopped inside it. The call continues in line 310. |
| 310 | `          res["processes"][0]["flags"] == ["NO_AFTER"] and any("no watch.txt" in n for n in res["notes"]), res)` | The conditions: `NO_AFTER` is the only flag, and a note holds `no watch.txt`. |
| 311 | `    res = report(os.path.join(tmp, "nothing-here"))` | `res`: the report of a folder that does not exist. |
| 312 | `    check("report: a folder without hw says that the run has no hardware record", res.get("notes") == ["no folder hw: this run has no hardware record"], res)` | Check: a folder without `hw` says that the run has no hardware record. The notes must hold exactly this one sentence. This is the case of a run with `HW=off`, and of a result folder that was written before the hardware record existed. |
| 314 | `    # 5. the summary file of atx, in the two header forms (its guide and its program text differ)` | Comment: case 5 is the summary file of `atx` in the two forms of its header. The guide of `atx` and its program text differ. |
| 315 | `    sample = ("Collection Date/Time,2026-11-24\n\n"` | `sample`: the text of a summary file. Its first line is a date line that belongs to no table. |
| 316 | `              "Metric: vcpu-c0-power - VCPU_C power (W)\nTarget,Min,Max,Average,Time Weighted Average,Count\nscmi-tlm_0,100.5,300.25,200,210.5,60\n\n"` | A first metric, `vcpu-c0-power` in W. Its header uses the column name `Time Weighted Average`. One row follows for the target `scmi-tlm_0`: lowest 100.5, highest 300.25, average 200, time weighted average 210.5, count 60. |
| 317 | `              "Histogram Summary\nTarget,Type,Value/Range,Count\nscmi-tlm_0,Discrete,100,3\n\n"` | A histogram table. Its header holds `Type` and no `Min`. The reader must skip it. |
| 318 | `              "Metric: vcpu-c1-power - VCPU_C power (W)\nTarget,Min,Max,Average,TimeWeightedAvg,Count\nscmi-tlm_1,90,310,190,189.5,60\n\n"` | A second metric, `vcpu-c1-power`. Its header uses the other spelling, `TimeWeightedAvg`. One row follows for the target `scmi-tlm_1`: 90, 310, 190, 189.5 and 60. |
| 319 | `              "Metric: core0-frequency - Core frequency (MHz)\nTarget,Min,Max,Average,Time Weighted Average,Count\nscmi-tlm_0,2400,2800,2790,2795,60\n")` | A third metric, `core0-frequency` in MHz, with one row: lowest 2400, highest 2800, average 2790, time weighted average 2795, count 60. The parenthesis ends the text. |
| 320 | `    put(os.path.join(fa, "hw", "atx", "atx_summary.csv"), sample)` | Writes the text as `atx_summary.csv` into the folder `hw/atx` of the result folder `resA`. |
| 321 | `    rows = report(fa)["atx"]` | `rows`: the rows of `atx` in the report of that folder. |
| 322 | `    check("report: the summary of atx is read in both header forms, and the histogram table is skipped",` | Check: the summary of `atx` is read in both header forms, and the histogram table is skipped. By the design note, the guide of `atx` and its program text differ in one column name [Ref1]. So the reader must accept both. The call continues in lines 323 to 325. |
| 323 | `          [(r["metric"], r["unit"], r["target"], r["min"], r["max"], r["twa"], r["count"]) for r in rows]` | Builds one tuple per row with seven of its values: the metric, the unit, the target, the lowest value, the highest value, the time weighted average and the count. |
| 324 | `          == [("vcpu-c0-power", "W", "scmi-tlm_0", 100.5, 300.25, 210.5, 60.0), ("vcpu-c1-power", "W", "scmi-tlm_1", 90.0, 310.0, 189.5, 60.0),` | The expected list, first two rows: the two power metrics with their numbers. There is no row of the histogram. |
| 325 | `              ("core0-frequency", "MHz", "scmi-tlm_0", 2400.0, 2800.0, 2795.0, 60.0)], rows)` | The third expected row: the frequency metric. Then the list ends, and `rows` is the detail for a failed check. |
| 326 | `    text = tool("report", fa).stdout` | `text`: the text form of the report of `resA`. |
| 327 | `    check("report: the text form sums the average power of a rail family and prints the lowest frequency",` | Check: the text form sums the average power of a rail family and prints the lowest frequency. A rail is one power supply line of the chip. The call continues in lines 328 to 329. |
| 328 | `          re.search(r"vcpu-c-power +W +series +2 +lowest min 90\.00 +highest max 310\.00 +sum of avg 400\.00", text) is not None` | The first pattern looks for the line of the family `vcpu-c-power`: the unit `W`, 2 rows (`series`), the lowest value 90.00, the highest value 310.00, and the sum of the averages 400.00. That is 210.5 plus 189.5. |
| 329 | `          and re.search(r"core-frequency +MHz +series +1 +lowest min 2400\.00", text) is not None, text)` | The second pattern looks for the line of the family `core-frequency`: the unit `MHz`, 1 row and the lowest value 2400.00. |

### `counts_checks`: the script `clock_from_counts.py` (lines 332 to 359)

| Line | Source | Explanation |
|---:|---|---|
| 332 | `def counts_checks(tmp):` | Starts the function `counts_checks`. |
| 333 | `    """clock_from_counts.py on small files in the three layouts of the earlier result files."""` | Docstring: the function runs `clock_from_counts.py` on small files in the three layouts of the earlier result files. |
| 334 | `    d = os.path.join(tmp, "w120-OLD")` | `d`: a result folder for the test, `w120-OLD`. |
| 335 | `    put(os.path.join(d, "a.csv"), "# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns,cycles,instructions; pmu_type=11\n"` | Writes the csv file `a.csv`. This line holds its header: the columns of a `C` row, with `enabled_ns`, `running_ns` and `cycles`, and a remark after a `;`. |
| 336 | `        "C,0,0,oldread,0,0,6000000000,6000000000,5990000000,16800000000,1\nC,0,0,oldread,1,1,6000000000,6000000000,5990000000,16740000000,1\n"` | Two rows of the kernel `oldread`, for thread 0 and thread 1. Both have an enabled time and a running time of 6000000000 ns (6 s). The cycle counts are 16800000000 and 16740000000. |
| 337 | `        "C,0,1,asmread,0,0,6000000000,3000000000,5990000000,16800000000,1\nC,0,1,asmread,1,1,6000000000,6000000000,5990000000,NA,1")` | Two rows of the kernel `asmread`. In the first the counter ran for 3 s of the 6 s. In the second the cycle count is `NA`. |
| 338 | `    r = clock_from_counts.core_clock(os.path.join(d, "a.csv"))` | `r`: the result of `core_clock` for this file. |
| 339 | `    check("counts: core clock = cycles / enabled time (16800000000 cycles in 6 s = 2.8 GHz), one value per thread and interval",` | Check: core clock = cycles divided by enabled time, with one value per thread and interval. 16800000000 cycles in 6 s are 2.8 GHz. This check proves the rule and the unit of the script. The call continues in line 340. |
| 340 | `          r["ghz"] == [2.8, 2.79] and r["intervals"] == 1 and r["threads"] == [2] and r["kernels"] == ["oldread"], r)` | The conditions: the values are 2.8 and 2.79 GHz, there is 1 interval with 2 rows, and the only kernel is `oldread`. The two rows of `asmread` gave no value. |
| 341 | `    check("counts: a row whose counter ran for a part of the time is counted as scaled and not used, and NA is not a value", r["scaled"] == 1, r)` | Check: a row whose counter ran for a part of the time is counted as scaled and not used, and `NA` is not a value. The count of scaled rows must be 1. Such a count would give a wrong clock rate. So it must not enter the statistics. |
| 342 | `    put(os.path.join(d, "t.csv"), "# C,trial,widx,enabled_ns,running_ns,cputime_ns,cpu_cycles,inst_retired\nC,0,0,300000000,300000000,299000000,840000000,1\nC,1,0,300000000,300000000,299000000,837000000,1")` | Writes the csv file `t.csv` in the trial layout: the columns `trial` and `widx` in place of round, position and kernel, and the cycle column `cpu_cycles`. Two rows: 840000000 and 837000000 cycles in 300000000 ns (0.3 s). |
| 343 | `    r = clock_from_counts.core_clock(os.path.join(d, "t.csv"))` | `r`: the result of `core_clock` for this file. |
| 344 | `    check("counts: the trial layout with the column cpu_cycles is read too", r["ghz"] == [2.8, 2.79] and r["intervals"] == 2, r)` | Check: the trial layout with the column `cpu_cycles` is read too. The values must be 2.8 and 2.79 GHz, in 2 intervals. |
| 345 | `    put(os.path.join(d, "n.csv"), "# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns,cbusy0\nC,0,0,oldread,0,0,6000000000,6000000000,1,5")` | Writes the csv file `n.csv`. Its `C` rows have a counter `cbusy0` and no cycle column. |
| 346 | `    check("counts: a csv file without a cycle column gives no result", clock_from_counts.core_clock(os.path.join(d, "n.csv")) is None)` | Check: a csv file without a cycle column gives no result (`None`). So a file of a run without a cycle counter does not appear in the table. |
| 347 | `    put(os.path.join(d, "launches.txt"), "launch tagA utc 19:02:14 load 1 args --threads 120 --seq oldread\nrc 0 tagA")` | Writes `launches.txt`: one launch line for the tag `tagA` with `--seq oldread`, and one `rc` line. |
| 348 | `    put(os.path.join(d, "tagA.s01.perf"), "# started on Sun Nov 15\n\n8000000000,,arm_cmn_0/dtc_cycles/,4000000000,100.00,,\n7996000000,,arm_cmn_1/dtc_cycles/,4000000000,100.00,,\n9,,arm_cmn_0/other/,4000000000,100.00,,")` | Writes the file `tagA.s01.perf` in the form of `perf stat -x,`: a comment line, an empty line, one `dtc_cycles` line per mesh device with a share of 100.00 (8000000000 and 7996000000 counts in 4000000000 ns), and one line of another event. |
| 349 | `    put(os.path.join(d, "tagA.s02.perf"), "5958000000,,arm_cmn_0/dtc_cycles/,2000000000,66.00,,")` | Writes the file `tagA.s02.perf`: one `dtc_cycles` line with a share of 66.00. |
| 350 | `    m = clock_from_counts.mesh_clock(d)` | `m`: the result of `mesh_clock` for the folder. |
| 351 | `    check("counts: mesh clock = dtc_cycles / time the counter ran, per mesh, with the kernel of the launch line",` | Check: mesh clock = `dtc_cycles` divided by the time that the counter ran, per mesh, with the kernel of the launch line. The call continues in line 352. |
| 352 | `          m[("oldread", "arm_cmn_0")]["ghz"] == [2.0] and m[("oldread", "arm_cmn_1")]["ghz"] == [1.999], m)` | The conditions: the key (`oldread`, `arm_cmn_0`) holds 2.0 GHz, and the key (`oldread`, `arm_cmn_1`) holds 1.999 GHz. The line of the other event gave no value. |
| 353 | `    check("counts: a perf line with a share below 100 % (a count that perf scaled) is counted as scaled and not used", m[("oldread", "arm_cmn_0")]["scaled"] == 1, m)` | Check: a `perf` line with a share below 100 % is counted as scaled and not used. `perf` scaled such a count up from a part of the time. The count of scaled lines of `arm_cmn_0` must be 1. |
| 354 | `    r = subprocess.run([sys.executable, os.path.join(X, "clock_from_counts.py"), d], stdout=subprocess.PIPE, universal_newlines=True)` | Runs the script as a program on the folder and collects its output. |
| 355 | `    check("counts: the text form ends each part with the lowest and highest value and the number of rows that were not used",` | Check: the text form ends each part with the lowest and the highest value and the number of rows that were not used. The call continues in lines 356 to 357. |
| 356 | `          "all 2 csv files: 4 values in 3 intervals, lowest 2.7900 GHz, highest 2.8000 GHz, 1 scaled rows not used" in r.stdout` | The summary of the core table must be: 2 csv files, 4 values in 3 intervals, lowest 2.7900 GHz, highest 2.8000 GHz, 1 scaled row. |
| 357 | `          and "all folders: 2 values, lowest 1.99900 GHz, highest 2.00000 GHz, 1 scaled lines not used" in r.stdout, r.stdout)` | The summary of the mesh table must be: 2 values, lowest 1.99900 GHz, highest 2.00000 GHz, 1 scaled line. |

### The stand-in for `atx` (lines 360 to 380)

| Line | Source | Explanation |
|---:|---|---|
| 360 | `# ----------------------------------------------------------------------------- stand-in programs` | Comment: a divider. The stand-in programs follow. |
| 362 | `STUB_ATX = r"""#!/usr/bin/env bash` | Starts the text `STUB_ATX`, the stand-in for `atx`. It is a Bash script. This is its first line, which tells Linux to run it with `bash`. The letter `r` in front of the quotation marks keeps each backslash of the text as it is. |
| 363 | `# Stand-in for atx: "atx collect ... -o DIR -n NAME". It writes NAME_summary.csv when it gets SIGINT.` | Text of the stand-in, a comment: it takes the arguments of `atx collect` with `-o DIR` and `-n NAME`. It writes the file `NAME_summary.csv` when it receives SIGINT. |
| 364 | `# STUB_ATX_MODE: ok (default), nosummary (ends without a file), nopower (a summary without a power metric),` | Text of the stand-in, a comment: the variable `STUB_ATX_MODE` chooses its behavior. `ok` is the default. `nosummary`: it ends without a file. `nopower`: it writes a summary without a power metric. |
| 365 | `# ignore (does not end on SIGINT), dies (ends by itself after 0.3 s).` | Text of the stand-in, a comment: two more modes. `ignore`: it does not end on SIGINT. `dies`: it ends by itself after 0.3 s. |
| 366 | `echo "$* @ $PWD" >> "${STUB_LOG:-/dev/null}"` | Text of the stand-in: appends its arguments and its working folder to the log file `STUB_LOG`. Without that variable the line goes to `/dev/null`. The checks read this log to see how `hw.sh` called `atx`. |
| 367 | `out=.; name=ATX` | Text of the stand-in: the defaults of the output folder (`.`) and of the name (`ATX`). |
| 368 | `while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift;; -n) name=$2; shift;; esac; shift; done` | Text of the stand-in: a loop over the arguments. `-o` sets the output folder and `-n` the name, each from the argument that follows it. All other arguments are skipped. |
| 369 | `finish() {` | Text of the stand-in: starts the function `finish`, which runs when SIGINT arrives. |
| 370 | `  case "${STUB_ATX_MODE:-ok}" in` | Text of the stand-in: the function acts by the mode. |
| 371 | `    ok) printf 'Metric: vcpu-c0-power - VCPU_C power (W)\nTarget,Min,Max,Average,Time Weighted Average,Count\nstub,100,300,200,210,5\n' > "$out/${name}_summary.csv"; echo t,v > "$out/${name}_interval.csv";;` | Text of the stand-in: the mode `ok` writes a summary with one power metric, `vcpu-c0-power` in W, and one row of values. It also writes a small file `NAME_interval.csv`. |
| 372 | `    nopower) printf 'Metric: core0-temp - temp (C)\nTarget,Min,Max,Average,Time Weighted Average,Count\nstub,40,50,45,45,5\n' > "$out/${name}_summary.csv";;` | Text of the stand-in: the mode `nopower` writes a summary with one temperature metric and no power metric. |
| 373 | `  esac` | Text of the stand-in: ends the `case`. Every other mode writes no file. |
| 374 | `  exit 0` | Text of the stand-in: the script ends with exit status 0. |
| 375 | `}` | Text of the stand-in: ends the function `finish`. |
| 376 | `case "${STUB_ATX_MODE:-ok}" in ignore) trap '' INT;; *) trap finish INT;; esac` | Text of the stand-in: sets the action for SIGINT. In the mode `ignore` the signal is ignored (`trap ''`). In every other mode it calls `finish`. Bash cannot set an action for a signal that was already ignored when the script started. So this stand-in reacts to SIGINT only when it starts with the default action, which `env --default-signal` in `hw.sh` gives it. |
| 377 | `[ "${STUB_ATX_MODE:-ok}" = dies ] && { %(sleep)s 0.3; exit 9; }` | Text of the stand-in: in the mode `dies` the script waits 0.3 s with the real `sleep` and then ends with exit status 9. `%(sleep)s` is a place holder that line 379 fills. |
| 378 | `while :; do %(sleep)s 0.05; done` | Text of the stand-in: an endless loop of pauses of 0.05 s with the real `sleep`. Bash runs the action of a signal only after the command that is running has ended. So `finish` starts at most about 0.05 s after the signal. |
| 379 | `""" % {"sleep": REAL_SLEEP}` | Ends the text. The operator `%` puts the path of the real `sleep` into the two place holders `%(sleep)s`. |

### The stand-ins for the benchmark, `taskset`, `sleep` and `gcc` (lines 381 to 420)

| Line | Source | Explanation |
|---:|---|---|
| 381 | `STUB_BENCH = r"""#!/usr/bin/env python3` | Starts the text `STUB_BENCH`, the stand-in for a benchmark binary. It is a Python script. This is its first line. |
| 382 | `# Stand-in for a benchmark binary: it advances the two counters of each of its CPUs in the copied file tree by the` | Text of the stand-in, a comment: it advances the two counters of each of its CPUs in the copied file tree by the same amount, which stands for full speed. The sentence goes on in line 383. |
| 383 | `# same amount (full speed), prints one line and ends with the status STUB_BENCH_RC (0 if not set).` | Text of the stand-in, a comment: it prints one line and ends with the exit status of the variable `STUB_BENCH_RC`, or with 0 when that is not set. |
| 384 | `import os, re, sys` | Text of the stand-in: imports three modules. |
| 385 | `a = sys.argv[1:]` | Text of the stand-in: `a` holds its arguments. |
| 386 | `cpus = a[a.index("--cpus") + 1] if "--cpus" in a else "0-119"` | Text of the stand-in: the CPU list is the value after `--cpus`. Without that option it is `0-119`. |
| 387 | `out = []` | Text of the stand-in: `out` will hold the CPU numbers. |
| 388 | `for part in cpus.split(","):` | Text of the stand-in: a loop over the parts of the list between commas. |
| 389 | `    lo, _, hi = part.partition("-")` | Text of the stand-in: splits a part at its hyphen into the first and the last CPU. |
| 390 | `    out += range(int(lo), int(hi or lo) + 1)` | Text of the stand-in: adds the CPUs of the part. A single number is also the last CPU. |
| 391 | `for c in out:` | Text of the stand-in: a loop over the CPUs. |
| 392 | `    p = "%s/sys/devices/system/cpu/cpu%d/acpi_cppc/feedback_ctrs" % (os.environ["FAKE_ROOT"], c)` | Text of the stand-in: the path of the counter file of the CPU in the tree. The variable `FAKE_ROOT` gives the root of the tree. |
| 393 | `    m = re.match(r"ref:(\d+) del:(\d+)", open(p).read())` | Text of the stand-in: reads the two counters. Group 1 holds `ref` and group 2 holds `del`. |
| 394 | `    open(p, "w").write("ref:%d del:%d\n" % (int(m.group(1)) + 1000000, int(m.group(2)) + 1000000))` | Text of the stand-in: writes both counters back, each raised by 1000000. The ratio of the two changes is 1. So the report gives the full 2800000 kHz for a process of this stand-in. |
| 395 | `print("stand-in " + " ".join(a))` | Text of the stand-in: prints the word `stand-in` and its arguments. This line takes the place of the benchmark output. |
| 396 | `sys.exit(int(os.environ.get("STUB_BENCH_RC", "0")))` | Text of the stand-in: ends with the exit status of `STUB_BENCH_RC`, or with 0. |
| 397 | `"""` | Ends the text. This text has no place holder. |
| 399 | `SHIM_TASKSET = r"""#!/usr/bin/env bash` | Starts the text `SHIM_TASKSET`, the stand-in for `taskset`. It is a Bash script. This is its first line. |
| 400 | `# Stand-in for taskset: it does not pin. "taskset -c LIST CMD..." writes LIST and CMD to the log and runs CMD.` | Text of the stand-in, a comment: it does not pin. A call `taskset -c LIST CMD` writes the list and the command to the log and runs the command. |
| 401 | `if [ "$1" = -cp ]; then echo "pid $2's current affinity list: (stand-in)"; exit 0; fi` | Text of the stand-in: the form `taskset -cp PID` asks for the CPU list of a process. The stand-in prints a fixed answer and ends. `go.sh` uses this form for one of its state lines. |
| 402 | `echo "$*" >> "${SHIM_LOG:-/dev/null}"` | Text of the stand-in: appends all its arguments to the log file `SHIM_LOG`. The checks read this log to see on which CPU `hw.sh` wanted to run a program. |
| 403 | `shift 2` | Text of the stand-in: drops the first two arguments, `-c` and the list. |
| 404 | `exec "$@"` | Text of the stand-in: replaces itself with the command. So the process id stays the same, as with the real `taskset`. |
| 405 | `"""` | Ends the text. |
| 407 | `SHIM_SLEEP = r"""#!/usr/bin/env bash` | Starts the text `SHIM_SLEEP`, the stand-in for `sleep`. It is a Bash script. This is its first line. |
| 408 | `exec %s "$(awk -v s="$1" 'BEGIN { printf "%%.3f", s / 10 }')"` | Text of the stand-in: replaces itself with the real `sleep`. `awk` divides the wanted time by 10 and prints it with 3 decimals. So every pause of a script under test lasts one tenth of its time: the pause of 5 s in `rx.sh` lasts 0.5 s. `%s` is the place holder for the path of the real `sleep`, and `%%` gives one percent sign. |
| 409 | `""" % REAL_SLEEP` | Ends the text and fills the place holder. |
| 411 | `SHIM_GCC = r"""#!/usr/bin/env bash` | Starts the text `SHIM_GCC`, the stand-in for the compiler `gcc`. It is a Bash script. This is its first line. |
| 412 | `# Stand-in for gcc in run_kernels.sh: "-o FILE" gets the stand-in benchmark (bw_old, bw_new), a program that ends` | Text of the stand-in, a comment: it serves `run_kernels.sh`. The output file after `-o` becomes the stand-in benchmark when its name is `bw_old` or `bw_new`. The sentence goes on in line 413. |
| 413 | `# with status 0 (selftest) or an empty file (probe.o).` | Text of the stand-in, a comment: for the name `selftest` the output is a program that ends with status 0. For `probe.o` it is an empty file. |
| 414 | `if [ "$1" = --version ]; then echo "gcc (stand-in)"; exit 0; fi` | Text of the stand-in: the call `gcc --version` prints `gcc (stand-in)` and ends. |
| 415 | `while [ $# -gt 0 ]; do [ "$1" = -o ] && o=$2; shift; done` | Text of the stand-in: a loop over the arguments. It keeps the value after `-o` in the variable `o`. |
| 416 | `case "$(basename "$o")" in bw_old\|bw_new) cp "$STUB_BENCH" "$o";; selftest) printf '#!/bin/sh\nexit 0\n' > "$o";; *) : > "$o";; esac` | Text of the stand-in: acts by the file name of the output. `bw_old` and `bw_new`: copies the stand-in benchmark, whose path is in `STUB_BENCH`. `selftest`: writes a shell script that ends with status 0. Every other name: writes an empty file. |
| 417 | `chmod +x "$o"` | Text of the stand-in: makes the output file executable. |
| 418 | `"""` | Ends the text. |

### Helpers `exe`, `sha`, `stand_ins`, `bash` and `no_leftover` (lines 421 to 466)

| Line | Source | Explanation |
|---:|---|---|
| 421 | `def exe(path, text):` | Starts the function `exe`. It writes a script file and makes it executable. |
| 422 | `    put(path, text.rstrip("\n"))` | Writes the text with `put`. `put` adds one line break. So `rstrip` first removes the line breaks at the end of the text. |
| 423 | `    os.chmod(path, 0o755)` | Sets the access rights `755`: the owner may read, write and run the file. All others may read and run it. |
| 424 | `    return path` | Returns the path. |
| 427 | `def sha(path):` | Starts the function `sha`. It returns the sha256 of a file. |
| 428 | `    return hashlib.sha256(open(path, "rb").read()).hexdigest()` | Reads the file as bytes and returns the checksum as 64 hexadecimal digits. |
| 431 | `def stand_ins(tmp):` | Starts the function `stand_ins`. It prepares what a run of `hw.sh` or of a run script needs in place of CRB. |
| 432 | `    """Folder with the stand-in programs and the environment that every run uses."""` | Docstring: the function makes a folder with the stand-in programs, and the environment that every run uses. |
| 433 | `    b = os.path.join(tmp, "bin")` | `b`: the folder `bin` in the temporary folder. It will stand first in the search path. |
| 434 | `    exe(os.path.join(b, "taskset"), SHIM_TASKSET)` | Writes the stand-in `taskset` into it. |
| 435 | `    exe(os.path.join(b, "sleep"), SHIM_SLEEP)` | Writes the stand-in `sleep` into it. |
| 436 | `    exe(os.path.join(b, "gcc"), SHIM_GCC)` | Writes the stand-in `gcc` into it. |
| 437 | `    exe(os.path.join(b, "objdump"), "#!/bin/sh\nexit 0\n")` | Writes a stand-in `objdump` that does nothing and ends with status 0. `run_kernels.sh` calls `objdump` for the machine-code listings. |
| 438 | `    atx = exe(os.path.join(tmp, "stub", "atx"), STUB_ATX)` | `atx`: the path of the stand-in `atx`, in the folder `stub`. |
| 439 | `    bench = exe(os.path.join(tmp, "stub", "bench"), STUB_BENCH)` | `bench`: the path of the stand-in benchmark, in the folder `stub`. |
| 440 | `    root = os.path.join(tmp, "tree120")` | `root`: the folder of a tree, `tree120`. |
| 441 | `    make_tree(root, 120)` | Builds the tree with 120 CPUs, as many as our tests use on CRB. |
| 442 | `    home = os.path.join(tmp, "home")` | `home`: a folder that takes the place of the home folder. |
| 443 | `    os.makedirs(os.path.join(home, "cache-perf", "results"))` | Creates the folder `cache-perf/results` in it. The scripts write their result folders there. |
| 444 | `    env = dict(os.environ, PATH=b + os.pathsep + os.environ["PATH"], HOME=home, TMPDIR=tmp, HWDIR=X, HW_ROOT=root, FAKE_ROOT=root,` | `env`: the environment of the runs. It is the environment of this test with twelve values set. This line holds six. `PATH`: the folder `bin` first. `HOME`: the test home. `TMPDIR`: the temporary folder. `HWDIR`: the folder of this file, so the scripts read the `hw.sh` under test. `HW_ROOT` and `FAKE_ROOT`: the tree. The call continues in lines 445 to 446. |
| 445 | `               HW_ATX=atx, HW_CPU="119", HW_PERIOD_S="1", STUB_BENCH=bench, SHIM_LOG=os.path.join(tmp, "taskset.log"),` | Continues the call: `HW_ATX` is the stand-in `atx`. `HW_CPU` is 119 and `HW_PERIOD_S` is 1, as the defaults of `hw.sh`. `STUB_BENCH` is the stand-in benchmark. `SHIM_LOG` is the log of the stand-in `taskset`. |
| 446 | `               STUB_LOG=os.path.join(tmp, "atx.log"))` | Ends the call: `STUB_LOG` is the log of the stand-in `atx`. |
| 447 | `    for k in ("HW", "HW_POWER", "HW_CHECKED", "HW_ATX_STOP", "STUB_ATX_MODE", "STUB_BENCH_RC"):` | Starts a loop over six variables that could come from the shell of the person who starts the test: `HW`, `HW_POWER`, `HW_CHECKED`, `HW_ATX_STOP`, `STUB_ATX_MODE` and `STUB_BENCH_RC`. |
| 448 | `        env.pop(k, None)` | Removes the variable from `env` when it is there. So each run starts with the defaults of `hw.sh` and of the stand-ins. |
| 449 | `    return env, root, home, atx, bench` | Returns the environment and four paths: the tree, the test home, the stand-in `atx` and the stand-in benchmark. |
| 452 | `def bash(script, env, ignore_int=False, **more):` | Starts the function `bash`. It runs a piece of shell text and returns its exit status and its output. |
| 453 | `    """Runs a bash script. ignore_int: the script starts with SIGINT ignored, as a driver that was started with` | Docstring: the function runs a Bash script. With `ignore_int` the script starts with SIGINT ignored. The sentence goes on in line 454. |
| 454 | `    "nohup setsid go.sh &" from a shell without job control."""` | Docstring: a driver is in this state when it was started with `nohup setsid go.sh &` from a shell without job control. |
| 455 | `    e = dict(env, **more)` | `e`: the environment of the run: `env` with the values of the keyword arguments `more`, for example `STUB_ATX_MODE`. |
| 456 | `    pre = (lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)) if ignore_int else None` | `pre`: a function that runs in the new process directly before Bash starts. With `ignore_int` it sets the action of SIGINT to "ignore". Without `ignore_int`, `pre` is `None`. |
| 457 | `    return subprocess.run(["bash", "-c", script], env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, preexec_fn=pre)` | Runs `bash -c` with the text. The error output goes into the standard output, and both are collected as one text. |
| 460 | `def no_leftover(tmp):` | Starts the function `no_leftover`. It looks for processes of this test that still run. |
| 461 | `    """No stand-in atx and no sampler of this test may still run."""` | Docstring: no stand-in `atx` and no sampler of this test may still run. |
| 462 | `    time.sleep(0.3)` | Waits 0.3 s. A process that was stopped shortly before has time to end. |
| 463 | `    r = subprocess.run(["ps", "-eo", "pid=,args="], stdout=subprocess.PIPE, universal_newlines=True)` | Runs `ps` for all processes of the machine. `-eo pid=,args=` prints the process id and the command line of each, without a header line. |
| 464 | `    return [l for l in r.stdout.split("\n") if tmp in l and ("stub/atx" in l or "hwwatch.py watch" in l)]` | Returns the lines that hold the path of the temporary folder and one of two texts: `stub/atx` or `hwwatch.py watch`. An empty list means that no such process is left. |

### `hwsh_checks`: the function `hw_check` (lines 467 to 499)

| Line | Source | Explanation |
|---:|---|---|
| 467 | `# ----------------------------------------------------------------------------- hw.sh` | Comment: a divider. The checks of `hw.sh` follow. |
| 469 | `def hwsh_checks(tmp):` | Starts the function `hwsh_checks`. `tmp` is the folder `sh` in the temporary folder of the test. |
| 470 | `    env, root, home, atx, bench = stand_ins(tmp)` | Prepares the stand-ins, the tree of 120 CPUs and the environment. |
| 471 | `    src = '. "$HWDIR/hw.sh"; '` | `src`: the shell text that sources `hw.sh` from the folder `HWDIR`. Every script of this function starts with it. |
| 473 | `    r = bash(src + 'hw_check && echo "CHECKED=$HW_CHECKED"', env)` | Runs a script that calls `hw_check` and then prints the variable `HW_CHECKED`. |
| 474 | `    check("hw_check passes with usable files and a usable atx, and remembers the boot and the power setting",` | Check: `hw_check` passes with usable files and a usable `atx`, and it remembers the boot and the power setting. With this memory the steps of a driver skip the test that the driver already ran. The call continues in line 475. |
| 475 | `          r.returncode == 0 and "hw: check ok" in r.stdout and "CHECKED=00000000-test-boot:require" in r.stdout, r.stdout)` | The conditions: exit status 0, the output holds `hw: check ok`, and `HW_CHECKED` is the boot id of the tree, a colon and `require`. |
| 476 | `    log = lines(env["SHIM_LOG"])` | `log`: the lines of the log of the stand-in `taskset`. |
| 477 | `    check("hw_check starts the sampler and atx through taskset on the CPU of HW_CPU",` | Check: `hw_check` starts the sampler and `atx` through `taskset` on the CPU of `HW_CPU`. The log of the stand-in `taskset` shows for which CPU `hw_check` asked: CPU 119 for both programs. The stand-in itself pins nothing. The call continues in line 478. |
| 478 | `          any(l.startswith("-c 119 python3 ") and " watch " in l for l in log) and any(l.startswith("-c 119 env --default-signal=INT ") and " collect " in l for l in log), log)` | The conditions: one log line starts with `-c 119 python3` and holds the word `watch`. One log line starts with `-c 119 env --default-signal=INT` and holds the word `collect`. |
| 479 | `    check("atx is asked for the three metric groups, both reports and its sampling interval",` | Check: `atx` is asked for the three metric groups, both reports and its sampling interval. The call continues in line 480. |
| 480 | `          any(re.search(r"^collect -i 1000 -d 3600 -g power -g thermal -g frequency -r summary -r interval -o \. -n atx @ \S+/hwcheck\.\S+/atx$", l) for l in lines(env["STUB_LOG"])), lines(env["STUB_LOG"]))` | A line of the log of the stand-in `atx` must fit this pattern: `collect -i 1000 -d 3600`, the three `-g` options for `power`, `thermal` and `frequency`, `-r summary -r interval`, `-o .` and `-n atx`. Then the working folder follows. Its end must be a folder whose name starts with `hwcheck.`, and `/atx`. So the trial collection of `hw_check` gets the same options as a collection of a test. |
| 481 | `    r = bash(src + "hw_check", env, ignore_int=True)` | Runs `hw_check` once more, in a shell that starts with SIGINT ignored. |
| 482 | `    check("hw_check passes when the script itself ignores SIGINT (the way the drivers are started): atx still gets a SIGINT that it can act on",` | Check: `hw_check` passes when the script itself ignores SIGINT, which is the way the drivers are started. `atx` must still get a SIGINT on which it can act. Without that, no collection could be ended with its reports. `env --default-signal` in `hw.sh` is there for this case. The call continues in line 483. |
| 483 | `          r.returncode == 0 and "hw: check ok" in r.stdout, r.stdout)` | The conditions: exit status 0, and `hw: check ok` in the output. |
| 484 | `    r = bash(src + "hw_check", env, HW_ATX=os.path.join(tmp, "no-such-atx"))` | Runs `hw_check` with `HW_ATX` set to a path that does not exist. |
| 485 | `    check("hw_check fails without atx and names the two ways out", r.returncode != 0 and "no atx at" in r.stdout and "HW_POWER=off" in r.stdout and "HW_ATX" in r.stdout, r.stdout)` | Check: `hw_check` fails without `atx` and names the two ways to go on. The output must hold `no atx at`, `HW_POWER=off` and `HW_ATX`. So a run without the power values needs a choice of the person who starts it. |
| 486 | `    r = bash(src + "hw_check", env, HW_ATX=os.path.join(tmp, "no-such-atx"), HW_POWER="off")` | Runs `hw_check` with the same missing `atx` and with `HW_POWER=off`. |
| 487 | `    check("hw_check with HW_POWER=off does not need atx and says that power is not recorded", r.returncode == 0 and "power by atx: no, HW_POWER=off" in r.stdout, r.stdout)` | Check: with `HW_POWER=off`, `hw_check` does not need `atx` and says that power is not recorded. The exit status must be 0, and the output must hold `power by atx: no, HW_POWER=off`. |
| 488 | `    for mode, why in (("nosummary", "writes no summary"), ("nopower", "writes a summary without a power metric"), ("dies", "ends before the stop signal")):` | Starts a loop over three failure modes of the stand-in `atx`, each with a text for the name of the check: `nosummary`, `nopower` and `dies`. |
| 489 | `        r = bash(src + "hw_check", env, STUB_ATX_MODE=mode)` | Runs `hw_check` with this mode. |
| 490 | `        check("hw_check fails when atx %s, and names the root step of the tool" % why, r.returncode != 0 and "gave no summary with a power metric" in r.stdout and "setup_arm_agi_cpu_telemetry.sh" in r.stdout, r.stdout)` | Check, once per mode: `hw_check` fails when `atx` writes no summary, writes a summary without a power metric, or ends before the stop signal. The output must hold `gave no summary with a power metric` and the name of the vendor script `setup_arm_agi_cpu_telemetry.sh`. So a collection that gives no power values is found before a benchmark starts. |
| 491 | `    t0 = time.time()` | `t0`: the time before the next run, in seconds. |
| 492 | `    r = bash(src + "hw_check", env, STUB_ATX_MODE="ignore")` | Runs `hw_check` with the mode `ignore`: the stand-in `atx` does not end on SIGINT. |
| 493 | `    check("hw_check fails when atx does not end on the stop signal, after the wait, and leaves no process",` | Check: `hw_check` fails when `atx` does not end on the stop signal, after the wait, and it leaves no process. The call continues in line 494. |
| 494 | `          r.returncode != 0 and 2.5 < time.time() - t0 < 30 and not no_leftover(tmp), (r.stdout, time.time() - t0, no_leftover(tmp)))` | The conditions: the exit status is not 0, the run took between 2.5 s and 30 s, and `no_leftover` finds nothing. The stand-in `sleep` divides each pause by 10. So the wait of 30 s in `hw_atx_stop` lasts about 3 s here. The time shows that `hw.sh` waited before it killed `atx`. |
| 495 | `    os.rename("%s%s/cpu0/acpi_cppc/feedback_ctrs" % (root, CPU), os.path.join(tmp, "moved"))` | Moves the counter file of CPU 0 out of the tree. |
| 496 | `    r = bash(src + "hw_check", env)` | Runs `hw_check`. |
| 497 | `    check("hw_check fails when the counter file of Linux is missing and names HW=off", r.returncode != 0 and "FAILED: cpu0 acpi_cppc/feedback_ctrs" in r.stdout and "HW=off" in r.stdout, r.stdout)` | Check: `hw_check` fails when the counter file of Linux is missing, and it names `HW=off`. The output must hold `FAILED: cpu0 acpi_cppc/feedback_ctrs` and `HW=off`. |
| 498 | `    os.rename(os.path.join(tmp, "moved"), "%s%s/cpu0/acpi_cppc/feedback_ctrs" % (root, CPU))` | Moves the counter file back. |

### `hwsh_checks`: a whole record under the strict shell options (lines 500 to 527)

| Line | Source | Explanation |
|---:|---|---|
| 500 | `    # a whole result folder, under the strict shell options of ra.sh` | Comment: the next checks run a whole result folder under the strict shell options of `ra.sh`. |
| 501 | `    d = os.path.join(tmp, "cycle")` | `d`: the result folder `cycle`. |
| 502 | `    cyc = ('set -euo pipefail; ' + src + 'hw_init "%s"; hw_begin "bw old/read" 0-3; "$STUB_BENCH" --cpus 0-3 > /dev/null; sleep 3; hw_end; '` | `cyc`: the script. It sets `set -euo pipefail` and sources `hw.sh`. Then it calls `hw_init`. Then, for a first process with the label `bw old/read` on the CPUs 0 to 3, it calls `hw_begin`, the stand-in benchmark, a pause of 3 s (0.3 s with the stand-in `sleep`) and `hw_end`. The text continues in line 503. |
| 503 | `           'hw_begin second 7; "$STUB_BENCH" --cpus 7 > /dev/null; sleep 3; hw_end; hw_done; echo "failures=$(hw_failures "%s")"; echo END' % (d, d))` | Continues the script: the same for a second process with the label `second` on CPU 7. Then `hw_done`, a line with the result of `hw_failures`, and the word `END`. The operator `%` puts the folder `d` into the two place holders. |
| 504 | `    r = bash(cyc, env, HW_PERIOD_S="0.1")` | Runs the script with a sample period of 0.1 s. |
| 505 | `    hw = os.path.join(d, "hw")` | `hw`: the folder `hw` of the result folder. |
| 506 | `    names = sorted(os.listdir(hw)) if os.path.isdir(hw) else []` | `names`: the sorted names in that folder, or an empty list when it does not exist. |
| 507 | `    check("hw.sh under set -euo pipefail: the script reaches its end and counts 0 failures", r.returncode == 0 and "failures=0" in r.stdout and r.stdout.strip().endswith("END"), r.stdout)` | Check: under `set -euo pipefail` the script reaches its end and counts 0 failures. The exit status must be 0, and the output must hold `failures=0` and end with `END`. `ra.sh` and `run_kernels.sh` use these options. With these options, one failed command of `hw.sh` without a guard such as `\|\| true` would end a test early. |
| 508 | `    check("hw.sh writes the probe, the samples, two snapshots per process with a number and a clean label, the folder of atx and the status",` | Check: `hw.sh` writes the probe, the samples, two snapshots per process with a number and a clean label, the folder of `atx` and the status file. The call continues in line 509. |
| 509 | `          names == ["001-bw_old_read.after.txt", "001-bw_old_read.before.txt", "002-second.after.txt", "002-second.before.txt", "atx", "errors.txt", "probe.txt", "status.txt", "watch.txt"], names)` | The folder must hold exactly nine names: the two snapshots of `001-bw_old_read`, the two snapshots of `002-second`, `atx`, `errors.txt`, `probe.txt`, `status.txt` and `watch.txt`. The label `bw old/read` became `bw_old_read`. |
| 510 | `    if os.path.isdir(hw):` | The next four checks run only when the folder `hw` exists. |
| 511 | `        st = lines(os.path.join(hw, "status.txt"))` | `st`: the lines of `status.txt`. |
| 512 | `        check("status.txt holds the settings, the checksums of the three tools, one line per process and the end line",` | Check: `status.txt` holds the settings, the checksums of the three tools, one line per process and the last line. So the record says with which settings and with which texts of the tools it was made. The call continues in lines 513 to 515. |
| 513 | `              st[0].startswith("settings HW_POWER=require HW_CPU=119 HW_PERIOD_S=0.1 ") and [l.split()[-1] for l in st[1:4]] == ["hw.sh", "hwwatch.py", "atx"]` | The first line must start with `settings HW_POWER=require HW_CPU=119 HW_PERIOD_S=0.1`. The next three lines must end with the names `hw.sh`, `hwwatch.py` and `atx`. |
| 514 | `              and st[1].split()[1] == sha(HWSH) and st[2].split()[1] == sha(TOOL)` | The checksums in the second and in the third line must be the sha256 of `hw.sh` and of `hwwatch.py`. |
| 515 | `              and sum(1 for l in st if l.startswith("ok ") and " process 00" in l) == 2 and any(l.endswith("done: 2 processes") for l in st), st)` | Two lines must start with `ok` and hold `process 00`, and one line must end with `done: 2 processes`. |
| 516 | `        check("the snapshot of a process holds exactly the CPUs of that process (one CPU for a one-thread process)",` | Check: the snapshot of a process holds exactly the CPUs of that process, which is one CPU for a process with one thread. The user asked for the clock rate of the single core in single-core tests [Ref1]. The call continues in lines 517 to 518. |
| 517 | `              sorted(hwwatch.read_snap(os.path.join(hw, "002-second.before.txt"))["cpu"]) == [7]` | The first snapshot of the second process must hold only CPU 7. |
| 518 | `              and sorted(hwwatch.read_snap(os.path.join(hw, "001-bw_old_read.after.txt"))["cpu"]) == [0, 1, 2, 3])` | The second snapshot of the first process must hold the CPUs 0 to 3. |
| 519 | `        check("the sampler covers CPUs 0-119, ends with its end line, and atx leaves its summary",` | Check: the sampler covers the CPUs 0 to 119 and ends with its footer, and `atx` leaves its summary. The call continues in lines 520 to 521. |
| 520 | `              hwwatch.read_watch(os.path.join(hw, "watch.txt"))[2].get("reason") == "signal" and len(hwwatch.read_watch(os.path.join(hw, "watch.txt"))[0]) == 120` | The footer of `watch.txt` must give the reason `signal`, and the file must have 120 CPUs. |
| 521 | `              and os.path.getsize(os.path.join(hw, "atx", "atx_summary.csv")) > 0)` | The file `atx_summary.csv` must not be empty. |
| 522 | `        res = report(d)` | `res`: the report of this result folder. |
| 523 | `        check("the report of this folder gives 2800000 kHz, sampled rates and no flag for both processes, and the power row of atx",` | Check: the report of this folder gives 2800000 kHz, sampled rates and no flag for both processes, and the power row of `atx`. This check tests the parts together: the files that `hw.sh` writes are the files that `hwwatch.py report` reads. The call continues in lines 524 to 525. |
| 524 | `              [p["flags"] for p in res["processes"]] == [[], []] and all(abs(p["avg_khz"][0] - 2800000) < 1 and p["samples"] >= 1 for p in res["processes"])` | Both processes must have no flag, a lowest rate within 1 kHz of 2800000, and at least one sampled value. |
| 525 | `              and [p["cpus"] for p in res["processes"]] == [4, 1] and res["atx"][0]["metric"] == "vcpu-c0-power", res)` | The CPU counts must be 4 and 1, and the first row of `atx` must be the metric `vcpu-c0-power`. |
| 526 | `    check("after hw_done no sampler and no atx is left", not no_leftover(tmp), no_leftover(tmp))` | Check: after `hw_done` no sampler and no `atx` is left. A program that is left would go on using CPU 119 during later tests. |

### `hwsh_checks`: failures after `hw_init` (lines 528 to 548)

| Line | Source | Explanation |
|---:|---|---|
| 528 | `    # failures after hw_init are written down, and the test goes on` | Comment: failures after `hw_init` are written down, and the test goes on. |
| 529 | `    d2 = os.path.join(tmp, "cycle2")` | `d2`: the result folder `cycle2`. |
| 530 | `    r = bash('set -euo pipefail; ' + src + 'hw_init "%s"; hw_begin a 0-3; sleep 6; hw_end; hw_done; echo "failures=$(hw_failures "%s")"; echo END' % (d2, d2), env, STUB_ATX_MODE="dies", HW_CHECKED="00000000-test-boot:require")` | Runs a script under `set -euo pipefail`: `hw_init`, one process with a pause of 6 s (0.6 s with the stand-in `sleep`) and no benchmark, `hw_done`, the failure count and `END`. The stand-in `atx` is in the mode `dies`: it ends by itself after 0.3 s. `HW_CHECKED` is set to the value that `hw_check` would store. So `hw_check` is skipped, and `atx` ends by itself during the record. |
| 531 | `    st = lines(os.path.join(d2, "hw", "status.txt")) if os.path.isdir(os.path.join(d2, "hw")) else []` | `st`: the lines of `status.txt`, or an empty list. |
| 532 | `    check("atx that dies after the self-test: the script still reaches its end, and status.txt holds two FAILED lines (not running, no summary)",` | Check: when `atx` ends by itself after the self-test of the record, the script still reaches its end, and `status.txt` holds two `FAILED` lines. By decision 4 of the design note, a failure of the record does not stop a test after its start [Ref1]. The call continues in lines 533 to 535. |
| 533 | `          r.returncode == 0 and r.stdout.strip().endswith("END") and "failures=2" in r.stdout` | The conditions: exit status 0, the output ends with `END`, and the failure count is 2. |
| 534 | `          and any(l.startswith("FAILED") and "atx was not running at the end of 001-a" in l for l in st)` | One `FAILED` line must say that `atx` was not running at the end of the process `001-a`. |
| 535 | `          and any(l.startswith("FAILED") and "atx wrote no summary" in l for l in st), (r.stdout, st))` | One `FAILED` line must say that `atx` wrote no summary. |
| 536 | `    d3 = os.path.join(tmp, "cycle3")` | `d3`: the result folder `cycle3`. |
| 537 | `    r = bash(src + 'hw_init "%s"; hw_begin a 0-3; exit 3' % d3, env)` | Runs a script without the strict options: `hw_init`, `hw_begin`, and then `exit 3` inside the process. |
| 538 | `    st = lines(os.path.join(d3, "hw", "status.txt")) if os.path.isdir(os.path.join(d3, "hw")) else []` | `st`: the lines of `status.txt`, or an empty list. |
| 539 | `    check("a script that exits inside a process: the EXIT trap stops both collectors and writes the open process as FAILED",` | Check: when a script exits inside a process, the `EXIT` trap stops both collectors and writes the open process as `FAILED`. `rx.sh` ends in this way, with exit status 3, when it finds the marker file while a process runs. So such a stop leaves no sampler and no `atx` behind. The call continues in line 540. |
| 540 | `          r.returncode == 3 and not no_leftover(tmp) and any(l.startswith("FAILED") and "ended inside the process 001-a" in l for l in st), (r.stdout, st, no_leftover(tmp)))` | The conditions: the exit status is 3, `no_leftover` finds nothing, and a `FAILED` line holds `ended inside the process 001-a`. |
| 541 | `    d4 = os.path.join(tmp, "cycle4")` | `d4`: the result folder `cycle4`. |
| 542 | `    r = bash(src + 'hw_init "%s"; hw_begin a 5; hw_end; hw_done; ls "%s/hw"' % (d4, d4), env, HW_POWER="off")` | Runs a script with `HW_POWER=off`: one process on CPU 5, `hw_done`, and a listing of the folder `hw`. |
| 543 | `    check("HW_POWER=off: no folder of atx, and the status has no FAILED line", r.returncode == 0 and "atx" not in r.stdout.split() and "status.txt" in r.stdout` | Check: with `HW_POWER=off` there is no folder of `atx`, and the status file has no `FAILED` line. So a missing `atx` is not reported as a failure when the power record is switched off. This line holds three conditions: exit status 0, no name `atx` in the listing, and the name `status.txt` in the listing. The call continues in line 544. |
| 544 | `          and not any(l.startswith("FAILED") for l in lines(os.path.join(d4, "hw", "status.txt"))), r.stdout)` | The fourth condition: no line of `status.txt` starts with `FAILED`. |
| 545 | `    r = bash(src + 'hw_failures "%s"' % os.path.join(tmp, "nothing"), env)` | Runs `hw_failures` for a folder that does not exist. |
| 546 | `    check("hw_failures prints missing for a result folder without a status file", r.stdout.strip() == "missing", r.stdout)` | Check: `hw_failures` prints `missing` for a result folder without a status file. `missing` is not `0`. So a driver counts such a step as incomplete. |

### Table `COPY_CHANGES`: the text changes of the copied scripts (lines 549 to 563)

| Line | Source | Explanation |
|---:|---|---|
| 549 | `# ----------------------------------------------------------------------------- the run scripts` | Comment: a divider. The checks of the run scripts follow. |
| 551 | `# Text changes of the copies that the stand-in runs use. Each old text must occur exactly once.` | Comment: the table of lines 552 to 561 lists the text changes of the copies that the runs with stand-ins use. Each old text must occur exactly once in its script. |
| 552 | `COPY_CHANGES = {` | Starts the table `COPY_CHANGES`. It holds a list of entries per script. An entry holds the old text, the new text and the reason. |
| 553 | `    "ra.sh": [("e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old", "%(bench)s  bw_old", "checksum of the stand-in"),` | `ra.sh`, first change: in the line with the expected sha256 of `bw_old`, the checksum becomes the place holder `%(bench)s`. `install` fills it with the sha256 of the stand-in benchmark (line 573). So the checksum test of `ra.sh` accepts the stand-in. |
| 554 | `              ("fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new", "%(bench)s  bw_new", "checksum of the stand-in"),` | `ra.sh`, second change: the same for the sha256 of `bw_new`. |
| 555 | `              ("r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1)", "r=1", "the test machine is not quiet")],` | `ra.sh`, third change: the command that reads the number of runnable tasks from `/proc/loadavg` becomes `r=1`. Reason given: the test machine is not quiet. With the real number, `ra.sh` could stop with its message `not quiet`. |
| 556 | `    "go.sh": [("SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a", "SHA=%(bench)s", "checksum of the stand-in"),` | `go.sh`, first change: in the line `SHA=`, the expected sha256 of `bwx12` becomes the place holder. |
| 557 | `              ('[ "$(awk \'/^MemTotal/{print $2}\' /proc/meminfo)" -ge 395000000 ]', "[ 395392808 -ge 395000000 ]", "the test machine has another memory size")],` | `go.sh`, second change: the test that reads MemTotal from `/proc/meminfo` of the machine becomes a test of the fixed number 395392808 against 395000000. Reason given: the test machine has another memory size. |
| 558 | `    "go2.sh": [("SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a", "SHA=%(bench)s", "checksum of the stand-in"),` | `go2.sh`, first change: the same as line 556. |
| 559 | `               ('[ "$(awk \'/^MemTotal/{print $2}\' /proc/meminfo)" -ge 395000000 ]', "[ 395392808 -ge 395000000 ]", "the test machine has another memory size"),` | `go2.sh`, second change: the same as line 557. |
| 560 | `               ("awk '{exit !($1 < 1.0)}' /proc/loadavg", "true", "the test machine is not idle")],` | `go2.sh`, third change: the `awk` command that tests whether the load average of the last minute is below 1.0 becomes `true`. Reason given: the test machine is not idle. |
| 561 | `}` | Ends the table. It holds eight changes: four checksums of stand-ins, and four reads of the load or of the memory size. |

### Functions `install` and `result_folders`: the scripts in a test home (lines 564 to 590)

| Line | Source | Explanation |
|---:|---|---|
| 564 | `def install(home, bench):` | Starts the function `install`. It builds the folders of CRB below the test home. |
| 565 | `    """The CRB layout under the test HOME: copies of the scripts (changed as COPY_CHANGES says) and the stand-ins."""` | Docstring: the function makes the CRB layout under the test `HOME`: copies of the scripts, changed as `COPY_CHANGES` says, and the stand-ins. |
| 566 | `    cp = os.path.join(home, "cache-perf")` | `cp`: the folder `cache-perf` in the test home. |
| 567 | `    d = os.path.join(cp, "w120-7200-20261117")` | `d`: the folder `w120-7200-20261117` in it, the place of the drivers and of `ra.sh` on CRB. |
| 568 | `    os.makedirs(d, exist_ok=True)` | Creates it. |
| 569 | `    for name in ("ra.sh", "go.sh", "go2.sh"):` | Starts a loop over the three scripts that get changed copies. |
| 570 | `        text = open(os.path.join(W72, name)).read()` | `text`: the text of the script in the repository. |
| 571 | `        for old, new, _ in COPY_CHANGES[name]:` | Starts a loop over the changes of this script. |
| 572 | `            assert text.count(old) == 1, (name, old)` | `assert` stops the test when the old text does not occur exactly once. So an edit of the script that changes this text stops the test. |
| 573 | `            text = text.replace(old, new % {"bench": sha(bench)})` | Replaces the old text with the new one. The operator `%` puts the sha256 of the stand-in benchmark into the place holder `%(bench)s`. |
| 574 | `        exe(os.path.join(d, name), text)` | Writes the changed copy into `d` and makes it executable. |
| 575 | `    for name in ("like.spec", "cfwd.spec", "crev.spec"):` | Starts a loop over the three spec files. |
| 576 | `        shutil.copy(os.path.join(W72, name), d)` | Copies each spec file into `d` without a change. |
| 577 | `    os.makedirs(os.path.join(cp, "w120-20261115"), exist_ok=True)` | Creates the folder `w120-20261115`, the place of `rx.sh` on CRB. |
| 578 | `    shutil.copy(RX, os.path.join(cp, "w120-20261115", "rx.sh"))` | Copies `rx.sh` into it without a change. |
| 579 | `    for folder, names in (("bwx12-20261115", ["bwx12"]), ("scratch-kernels-20261113", ["bw_old", "bw_new"])):` | Starts a loop over two folders of binaries: `bwx12-20261115` with `bwx12`, and `scratch-kernels-20261113` with `bw_old` and `bw_new`. |
| 580 | `        os.makedirs(os.path.join(cp, folder), exist_ok=True)` | Creates the folder. |
| 581 | `        for n in names:` | Starts a loop over the names of the binaries. |
| 582 | `            shutil.copy(bench, os.path.join(cp, folder, n))` | Copies the stand-in benchmark to each of these names. So every benchmark binary of the runs is the stand-in. |
| 583 | `    return d` | Returns `d`. |
| 586 | `def result_folders(home, prefix):` | Starts the function `result_folders`. It returns the result folders of the test home whose names start with `prefix`. |
| 587 | `    base = os.path.join(home, "cache-perf", "results")` | `base`: the folder `cache-perf/results` in the test home. |
| 588 | `    return sorted(os.path.join(base, n) for n in os.listdir(base) if n.startswith(prefix) and os.path.isdir(os.path.join(base, n)))` | Returns the full paths of the entries that start with the prefix and are folders, sorted by name. |

### `static_checks`: the texts of the scripts, without a script start (lines 591 to 617)

| Line | Source | Explanation |
|---:|---|---|
| 591 | `def static_checks():` | Starts the function `static_checks`. It reads the script texts of the repository and starts none of the scripts. |
| 592 | `    for name in ("go.sh", "go2.sh"):` | Starts a loop over the two drivers, `go.sh` and `go2.sh`. |
| 593 | `        text = open(os.path.join(W72, name)).read()` | `text`: the text of the driver. |
| 594 | `        check("%s holds no fixed boot id and no check of the boot id" % name,` | Check, once per driver: the script holds no fixed boot id and no check of the boot id. The user asked to remove this check. By the design note, the fixed boot id stops a driver in every other boot [Ref1]. The call continues in line 595. |
| 595 | `              "BOOT" not in text and "3bfc57a1" not in text and "boot id is not" not in text, [l for l in text.split("\n") if "BOOT" in l or "boot id" in l])` | The text must hold none of three texts: `BOOT`, `3bfc57a1` and `boot id is not`. The detail for a failed check is the list of the lines that hold `BOOT` or `boot id`. |
| 596 | `        check("%s still prints the boot id in its state lines and still checks MemTotal" % name,` | Check, once per driver: the script still prints the boot id in its state lines and still checks MemTotal. So the removal took away only the comparison with a fixed boot id. The call continues in line 597. |
| 597 | `              "boot $(cat /proc/sys/kernel/random/boot_id)" in text and '-ge 395000000 ] \|\| fail "MemTotal below 395000000 kB: not 12 modules"' in text)` | The text must hold the command that reads the boot id for a state line, and the test of MemTotal against 395000000 kB with its message `not 12 modules`. |
| 598 | `        m = re.search(r"^RXSHA=([0-9a-f]{64})$", text, re.M)` | The pattern looks for a whole line that is `RXSHA=` and 64 hexadecimal digits. `re.M` lets `^` and the end mark fit at each line of the text. Group 1 holds the checksum. |
| 599 | `        check("%s holds the checksum of the rx.sh of this repository" % name, bool(m) and m.group(1) == sha(RX), (m and m.group(1), sha(RX)))` | Check, once per driver: the script holds the checksum of the `rx.sh` of this repository. The drivers stop when `rx.sh` does not have this sha256. So an edit of `rx.sh` without a new checksum in both drivers fails here and not on CRB. |
| 600 | `    # manual-run/run.sh starts a copy of go.sh that it makes with this sed command (it removed the boot id check).` | Comment: `manual-run/run.sh` starts a copy of `go.sh` that it makes with a `sed` command. That command removed the boot id check. |
| 601 | `    run_sh = open(os.path.join(CODE, "manual-run", "run.sh")).read()` | `run_sh`: the text of `run.sh`. |
| 602 | `    r = subprocess.run(["sed", "/boot id is not the boot checked/d", os.path.join(W72, "go.sh")], stdout=subprocess.PIPE)` | Runs the same `sed` command on the `go.sh` of the repository and collects its output. The command deletes every line that holds the text `boot id is not the boot checked`. |
| 603 | `    check("run.sh still fits: the sed command of run.sh now deletes no line of go.sh, so the copy that run.sh starts is go.sh itself",` | Check: `run.sh` still fits. Its `sed` command now deletes no line of `go.sh`. So the copy that `run.sh` starts is `go.sh` itself. The call continues in line 604. |
| 604 | `          'sed "/boot id is not the boot checked/d" $D/go.sh' in run_sh and r.stdout == open(os.path.join(W72, "go.sh"), "rb").read())` | The conditions: `run.sh` holds this `sed` command, and the output of the command is equal to the bytes of `go.sh`. |
| 605 | `    r = subprocess.run(["git", "-C", CODE, "diff", "--quiet", "HEAD", "--", os.path.join(CODE, "manual-run", "run.sh")])` | Runs `git diff --quiet` for `run.sh` against the last commit of the repository. The exit status is 0 when the file has no change. |
| 606 | `    check("run.sh is unchanged against the last commit", r.returncode == 0)` | Check: `run.sh` is unchanged against the last commit. By the design note, `run.sh` is the saved start command of the user and was left as it is [Ref1]. |
| 607 | `    rx = open(RX).read()` | `rx`: the text of `rx.sh`. |
| 608 | `    check("rx.sh takes the snapshot after the wait for a quiet machine and before the 5 s pause, so the launch still follows the pause directly",` | Check: `rx.sh` takes the snapshot after the wait for a quiet machine (at most 2 runnable tasks) and before the pause of 5 s. So the launch still follows the pause directly, as before the change. The call continues in line 609. |
| 609 | `          rx.index("[ \"$r\" -le 2 ] && break") < rx.index("hw_begin ") < rx.index("\n  sleep 5\n") < rx.index("taskset -c 0-119 $BW $args"))` | `index` gives the position of a text in the script. Four positions must rise in this order: the test that ends the wait for a quiet machine, the call `hw_begin`, the line `sleep 5`, and the launch with `taskset -c 0-119`. |
| 610 | `    for path in (RX, os.path.join(W72, "ra.sh"), os.path.join(W72, "go.sh"), os.path.join(W72, "go2.sh"), KERNELS, HWSH):` | Starts a loop over six scripts: `rx.sh`, `ra.sh`, `go.sh`, `go2.sh`, `run_kernels.sh` and `hw.sh`. |
| 611 | `        r = subprocess.run(["bash", "-n", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)` | Runs `bash -n` on the script. With `-n`, Bash reads the script and reports syntax errors, and it runs no command. |
| 612 | `        check("bash -n accepts %s" % os.path.relpath(path, CODE), r.returncode == 0, r.stdout)` | Check, once per script: `bash -n` accepts the script. The exit status must be 0. So a syntax error is found also with `--no-run`, when no script is started. |
| 613 | `    for name in ("like.spec", "cfwd.spec", "crev.spec"):` | Starts a loop over the three spec files. |
| 614 | `        r = subprocess.run(["git", "-C", CODE, "diff", "--quiet", "HEAD", "--", os.path.join(W72, name)])` | Runs `git diff --quiet` for the spec file against the last commit. |
| 615 | `        check("%s is unchanged against the last commit (the benchmark arguments stay the same)" % name, r.returncode == 0)` | Check, once per spec file: the file is unchanged against the last commit. So the arguments of the benchmark are the same as in the last commit of the repository. |

### `run_checks`: the script `rx.sh` (lines 618 to 651)

| Line | Source | Explanation |
|---:|---|---|
| 618 | `def run_checks(tmp):` | Starts the function `run_checks`. It starts the real run scripts and drivers with the stand-ins. `tmp` is the folder `run` in the temporary folder of the test. `--no-run` leaves this function out. |
| 619 | `    env, root, home, atx, bench = stand_ins(tmp)` | Prepares the stand-ins, the tree of 120 CPUs and the environment. |
| 620 | `    d = install(home, bench)` | `d`: the folder of the drivers in the test home, built by `install`. |
| 621 | `    cp = os.path.join(home, "cache-perf")` | `cp`: the folder `cache-perf` in the test home. |
| 623 | `    # rx.sh, unchanged text: two spec lines, one of them a one-thread line, one without --cpus` | Comment: `rx.sh` runs with its unchanged text and a spec file of two lines, one of them with one thread and one without `--cpus`. The count of the comment does not fit the code: the file of line 625 holds three lines. |
| 624 | `    spec = os.path.join(tmp, "two.spec")` | `spec`: the path of the spec file `two.spec`. |
| 625 | `    put(spec, "whole\|--threads 120 --cpus 0-63,64-119 --bytes 256M --seq oldread\nsingle\|--threads 1 --cpus 2 --bytes 8M\nfree\|--bytes 1M")` | Writes three spec lines. `whole`: 120 threads on the CPUs `0-63,64-119`. `single`: 1 thread on CPU 2. `free`: no `--cpus`. |
| 626 | `    r = bash('bash "%s" TRX "%s" %s < "%s"' % (os.path.join(cp, "w120-20261115", "rx.sh"), os.path.join(cp, "bwx12-20261115", "bwx12"), sha(bench), spec), env)` | Runs `rx.sh` with the name `TRX`, the path of the stand-in `bwx12` and its sha256. The spec file is the input. |
| 627 | `    f = result_folders(home, "w120-TRX-")` | `f`: the result folders whose names start with `w120-TRX-`. |
| 628 | `    ok = r.returncode == 0 and len(f) == 1` | `ok`: exit status 0 and exactly one result folder. |
| 629 | `    check("rx.sh runs its three spec lines with status 0", ok and [l.split()[:3] for l in lines(os.path.join(f[0], "launches.txt")) if l.startswith("rc ")] == [["rc", "0", "whole"], ["rc", "0", "single"], ["rc", "0", "free"]], r.stdout)` | Check: `rx.sh` runs its three spec lines with status 0. The `rc` lines of `launches.txt` must be `rc 0 whole`, `rc 0 single` and `rc 0 free`, in this order. So the loop of `rx.sh` still works with the calls of the hardware record in it. |
| 630 | `    if ok:` | The next three checks run only when `ok` holds. |
| 631 | `        hw = os.path.join(f[0], "hw")` | `hw`: the folder `hw` of the result folder. |
| 632 | `        check("rx.sh: the snapshot CPUs are the --cpus of each spec line: 120 CPUs, one CPU, and 0-119 for a line without --cpus",` | Check: the snapshot CPUs are the `--cpus` of each spec line: 120 CPUs, one CPU, and `0-119` for a line without `--cpus`. This tests the `sed` command of `rx.sh` that takes the CPU list out of the arguments. The call continues in lines 633 to 634. |
| 633 | `              [len(hwwatch.read_snap(os.path.join(hw, n))["cpu"]) for n in ("001-whole.before.txt", "002-single.after.txt", "003-free.before.txt")] == [120, 1, 120]` | The numbers of CPUs in three snapshots must be 120, 1 and 120. |
| 634 | `              and sorted(hwwatch.read_snap(os.path.join(hw, "002-single.before.txt"))["cpu"]) == [2])` | The snapshot before the process `single` must hold only CPU 2. |
| 635 | `        check("rx.sh: env.txt says that the hardware record was on, and the record has no FAILED line",` | Check: `env.txt` says that the hardware record was on, and the record has no `FAILED` line. The call continues in line 636. |
| 636 | `              "hw on power require" in open(os.path.join(f[0], "env.txt")).read() and not any(l.startswith("FAILED") for l in lines(os.path.join(hw, "status.txt"))), lines(os.path.join(hw, "status.txt")))` | `env.txt` must hold `hw on power require`, and no line of `status.txt` may start with `FAILED`. |
| 637 | `        res = report(f[0])` | `res`: the report of the result folder. |
| 638 | `        check("rx.sh: the report gives each process its rate (2800000 kHz in the copied tree) and no flag (NO_SAMPLES is allowed: a stand-in ends at once)",` | Check: the report gives each process its rate and no flag. The rate is 2800000 kHz in the copied tree. The flag `NO_SAMPLES` is allowed: a stand-in ends at once, so the sampler may take no sample inside the window. The call continues in line 639. |
| 639 | `              [p["cpus"] for p in res["processes"]] == [120, 1, 120] and all(abs(p["avg_khz"][1] - 2800000) < 1 and set(p["flags"]) <= {"NO_SAMPLES"} for p in res["processes"]), res["processes"])` | The conditions: the CPU counts are 120, 1 and 120. For each process the median rate is within 1 kHz of 2800000, and it has no flag other than `NO_SAMPLES`. |
| 640 | `    r = bash('bash "%s" TOFF "%s" %s < "%s"' % (os.path.join(cp, "w120-20261115", "rx.sh"), os.path.join(cp, "bwx12-20261115", "bwx12"), sha(bench), spec), env, HW="off", HWDIR=os.path.join(tmp, "no-hw-dir"))` | Runs `rx.sh` again with the name `TOFF`, with `HW=off`, and with `HWDIR` set to a folder that does not exist. |
| 641 | `    f = result_folders(home, "w120-TOFF-")` | `f`: the result folders of this run. |
| 642 | `    check("rx.sh with HW=off runs as before: no folder hw, hw.sh is not needed, env.txt says off",` | Check: with `HW=off`, `rx.sh` runs as before the change: no folder `hw`, `hw.sh` is not needed, and `env.txt` says `off`. So the behavior without the record stays available. The call continues in lines 643 to 644. |
| 643 | `          r.returncode == 0 and len(f) == 1 and not os.path.exists(os.path.join(f[0], "hw")) and "hw off " in open(os.path.join(f[0], "env.txt")).read()` | The conditions: exit status 0, one result folder, no folder `hw` in it, and the text `hw off` in `env.txt`. |
| 644 | `          and sum(1 for l in lines(os.path.join(f[0], "launches.txt")) if l.startswith("rc 0 ")) == 3, r.stdout)` | `launches.txt` must hold three lines that start with `rc 0`. |
| 645 | `    r = bash('bash "%s" TMISS "%s" %s < "%s"' % (os.path.join(cp, "w120-20261115", "rx.sh"), os.path.join(cp, "bwx12-20261115", "bwx12"), sha(bench), spec), env, HWDIR=os.path.join(tmp, "no-hw-dir"))` | Runs `rx.sh` with the name `TMISS`, with the record on, and with `HWDIR` set to a folder that does not exist. |
| 646 | `    check("rx.sh without hw.sh stops with status 7 before any process", r.returncode == 7 and not result_folders(home, "w120-TMISS-"), r.stdout)` | Check: without `hw.sh`, `rx.sh` stops with status 7 before any process. No result folder with this name may exist. So a missing file is found before a benchmark runs. |
| 647 | `    r = bash('bash "%s" TBAD "%s" %s < "%s"' % (os.path.join(cp, "w120-20261115", "rx.sh"), os.path.join(cp, "bwx12-20261115", "bwx12"), sha(bench), spec), env, STUB_ATX_MODE="nosummary")` | Runs `rx.sh` with the name `TBAD` and the stand-in `atx` in the mode `nosummary`. |
| 648 | `    f = result_folders(home, "w120-TBAD-")` | `f`: the result folders of this run. |
| 649 | `    check("rx.sh stops with status 7 before any process when the power record is required and atx is not usable",` | Check: `rx.sh` stops with status 7 before any process when the power record is required and `atx` is not usable. The call continues in line 650. |
| 650 | `          r.returncode == 7 and "hardware record not usable" in r.stdout and (not f or not os.path.exists(os.path.join(f[0], "launches.txt"))), r.stdout)` | The conditions: exit status 7, the output holds `hardware record not usable`, and no `launches.txt` exists. A result folder may exist: `rx.sh` creates it before it calls `hw_init`. |

### `run_checks`: the script `ra.sh` (lines 652 to 672)

| Line | Source | Explanation |
|---:|---|---|
| 652 | `    # ra.sh (copy): 24 processes on CPUs 0-119` | Comment: `ra.sh` runs as a changed copy: 24 processes on the CPUs 0 to 119. |
| 653 | `    r = bash('"%s/ra.sh" TRA' % d, env)` | Runs the copy of `ra.sh` with the name `TRA`. |
| 654 | `    f = result_folders(home, "k120-TRA-")` | `f`: the result folders whose names start with `k120-TRA-`. |
| 655 | `    ok = r.returncode == 0 and len(f) == 1` | `ok`: exit status 0 and exactly one result folder. |
| 656 | `    check("ra.sh runs to its end with status 0", ok, r.stdout)` | Check: `ra.sh` runs to its end with status 0. `ra.sh` uses `set -euo pipefail`. So this also shows that no call of the hardware record ends the script. |
| 657 | `    if ok:` | The next three checks run only when `ok` holds. |
| 658 | `        hw = os.path.join(f[0], "hw")` | `hw`: the folder `hw` of the result folder. |
| 659 | `        names = sorted(n for n in os.listdir(hw) if n.endswith(".before.txt"))` | `names`: the sorted names of the first snapshots, which are the files that end with `.before.txt`. |
| 660 | `        check("ra.sh: 24 processes, each with a snapshot before and after, named by binary, kernel and round",` | Check: there are 24 processes, each with a snapshot before and after, named by binary, kernel and round. The call continues in lines 661 to 662. |
| 661 | `              len(names) == 24 and names[0] == "001-bw_old-read-r1.before.txt" and names[23] == "024-bw_old-read-r2.before.txt"` | The conditions: 24 names, the first is `001-bw_old-read-r1.before.txt`, and the last is `024-bw_old-read-r2.before.txt`. |
| 662 | `              and all(os.path.isfile(os.path.join(hw, n.replace(".before.", ".after."))) for n in names), names)` | Each of them must have a partner file with `.after.` in place of `.before.`. |
| 663 | `        res = report(f[0])` | `res`: the report of the result folder. |
| 664 | `        check("ra.sh: the report has 24 processes of 120 CPUs with a rate and no flag (NO_SAMPLES is allowed: a stand-in ends at once)",` | Check: the report has 24 processes of 120 CPUs with a rate and no flag. The flag `NO_SAMPLES` is allowed, as in line 638. The call continues in line 665. |
| 665 | `              len(res["processes"]) == 24 and all(p["cpus"] == 120 and p["counter_cpus"] == 120 and abs(p["avg_khz"][0] - 2800000) < 1 and set(p["flags"]) <= {"NO_SAMPLES"} for p in res["processes"]), [p["flags"] for p in res["processes"]])` | The conditions for each of the 24 processes: 120 CPUs, 120 CPUs with a counter ratio, a lowest rate within 1 kHz of 2800000, and no flag other than `NO_SAMPLES`. |
| 666 | `        check("ra.sh: probe.txt of the run says that the hardware record was on, and threads120.csv holds 24 header lines",` | Check: the file `probe.txt` that `ra.sh` itself writes says that the hardware record was on, and `threads120.csv` holds 24 header lines. So the result file of the benchmark is still complete. The call continues in line 667. |
| 667 | `              "## hw=on hw_power=require" in open(os.path.join(f[0], "probe.txt")).read() and sum(1 for l in lines(os.path.join(f[0], "threads120.csv")) if l.startswith("-- binary")) == 24)` | `probe.txt` must hold `## hw=on hw_power=require`, and `threads120.csv` must hold 24 lines that start with `-- binary`. |
| 668 | `    r = bash('"%s/ra.sh" TRAF' % d, env, STUB_BENCH_RC="5")` | Runs `ra.sh` with the name `TRAF` and with `STUB_BENCH_RC=5`: the benchmark stand-in ends with status 5. |
| 669 | `    f = result_folders(home, "k120-TRAF-")` | `f`: the result folders of this run. |
| 670 | `    check("ra.sh: a benchmark process that fails still ends ra.sh with its status, and the collectors are stopped",` | Check: a benchmark process that fails still ends `ra.sh` with its status, and the collectors are stopped. So the failure of a benchmark still reaches the caller of `ra.sh`, and the `EXIT` trap stops the sampler and `atx`. The call continues in line 671. |
| 671 | `          r.returncode == 5 and not no_leftover(tmp) and len(f) == 1 and any("ended inside the process 001-" in l for l in lines(os.path.join(f[0], "hw", "status.txt"))), (r.returncode, r.stdout[-300:], no_leftover(tmp)))` | The conditions: exit status 5, `no_leftover` finds nothing, one result folder, and a line of `status.txt` that holds `ended inside the process 001-`. |

### `run_checks`: the drivers `go.sh` and `go2.sh` (lines 673 to 696)

| Line | Source | Explanation |
|---:|---|---|
| 673 | `    # go.sh (copy): the whole driver in a boot that is not the boot of 2026-11-17` | Comment: `go.sh` runs as a changed copy: the whole driver, in a boot that is not the boot of 2026-11-17. |
| 674 | `    golog = os.path.join(tmp, "atx-go.log")` | `golog`: a log file of the stand-in `atx` for this run alone. |
| 675 | `    r = bash('"%s/go.sh"' % d, env, STUB_LOG=golog)` | Runs the copy of `go.sh`. |
| 676 | `    out = r.stdout` | `out`: its output. |
| 677 | `    check("go.sh runs to ALLDONE with status 0 in a boot other than the one of 2026-11-17", r.returncode == 0 and out.strip().endswith("ALLDONE") and "FAILED" not in out, out[-1500:])` | Check: `go.sh` runs to `ALLDONE` with status 0 in a boot other than the one of 2026-11-17. The output must end with `ALLDONE` and must not hold `FAILED`. The older text of `go.sh` held a fixed boot id and a check of it. So this check shows that the driver no longer depends on one boot. |
| 678 | `    check("go.sh tests the hardware record once, before the first state line", "hw: check ok" in out and out.index("hw: check ok") < out.index("== start "), out[:600])` | Check: `go.sh` tests the hardware record once, before the first state line. The text `hw: check ok` must stand before `== start` in the output. So a record that is not usable stops the run before any benchmark. |
| 679 | `    steps = ["k120-T72A1-", "w120-T72L1-", "w120-T72C1-", "k120-T72A2-", "w120-T72L2-", "w120-T72C2-", "k120-T72A3-", "w120-T72L3-", "w120-T72C3-", "w120-T72C4-"]` | `steps`: the starts of the names of the 10 result folders of one run. For each of the 3 sessions: one folder of part A (`k120-T72A`), one of part L and one of part C. Then the fourth folder of part C. |
| 680 | `    fol = [result_folders(home, s) for s in steps]` | `fol`: the result folders found for each step. |
| 681 | `    check("go.sh: each of the 10 steps has one result folder with a hardware record without a FAILED line",` | Check: each of the 10 steps has one result folder with a hardware record without a `FAILED` line. The call continues in line 682. |
| 682 | `          all(len(x) == 1 for x in fol) and all(not any(l.startswith("FAILED") for l in lines(os.path.join(x[0], "hw", "status.txt"))) for x in fol), [len(x) for x in fol])` | The conditions: one folder per step, and no line of its `status.txt` starts with `FAILED`. |
| 683 | `    calls = [l for l in lines(golog) if " collect " in " " + l + " "]` | `calls`: the lines of `golog` that hold the word `collect`. |
| 684 | `    check("go.sh: atx ran one trial collection in the whole run (the steps do not repeat the self-test) and one collection per step",` | Check: `atx` ran one trial collection in the whole run and one collection per step. So the steps do not repeat the self-test of the record that the driver ran, and each step has exactly one collection. The call continues in line 685. |
| 685 | `          sum(1 for l in calls if "/hwcheck." in l) == 1 and sum(1 for l in calls if "/cache-perf/results/" in l) == 10, calls)` | One call must have a working folder that holds `/hwcheck.`, and 10 calls must have a working folder below `/cache-perf/results/`. |
| 686 | `    r = bash('"%s/go.sh"' % d, env, STUB_ATX_MODE="dies", HW_ATX_TRIAL_S="0.1")` | Runs `go.sh` with the stand-in `atx` in the mode `dies` and a trial length of 0.1 s. |
| 687 | `    check("go.sh: when the trial of atx fails the run does not start (status 1, no state line 'start')", r.returncode == 1 and "FAILED: hardware record not usable" in r.stdout and "== start " not in r.stdout, r.stdout[-600:])` | Check: when the trial collection of `atx` fails, the run does not start. The exit status must be 1, the output must hold `FAILED: hardware record not usable`, and there must be no state line `== start`. This is decision 2 of the design note: power is required by default [Ref1]. |
| 688 | `    r = bash('"%s/go.sh"' % d, env, STUB_ATX_MODE="dies", HW_CHECKED="00000000-test-boot:require")` | Runs `go.sh` with the mode `dies` again. `HW_CHECKED` is set. So `hw_check` is skipped, and `atx` ends by itself in every step. |
| 689 | `    check("go.sh: when atx dies in every step, all 10 steps still run, and the run ends with status 4 and without ALLDONE",` | Check: when `atx` ends by itself in every step, all 10 steps still run, and the run ends with status 4 and without `ALLDONE`. So a failure of the record loses no benchmark data, and the exit status and the missing word `ALLDONE` show it. The call continues in lines 690 to 691. |
| 690 | `          r.returncode == 4 and "ALLDONE" not in r.stdout and "DONE, but the hardware record of 10 steps is incomplete" in r.stdout` | The conditions: exit status 4, no `ALLDONE`, and the sentence `DONE, but the hardware record of 10 steps is incomplete` in the output. |
| 691 | `          and r.stdout.count("== hardware record of ") == 10 and "== end " in r.stdout, r.stdout[-900:])` | The output must hold 10 lines with `== hardware record of`, and the state line `== end`. |
| 692 | `    r = bash('"%s/go2.sh"' % d, env, HW_POWER="off")` | Runs the copy of `go2.sh` with `HW_POWER=off`. |
| 693 | `    f = result_folders(home, "w120-T72I")` | `f`: the result folders whose names start with `w120-T72I`. |
| 694 | `    check("go2.sh runs to ALLDONE in this boot with HW_POWER=off, and its two steps have a record without atx",` | Check: `go2.sh` runs to `ALLDONE` in this boot with `HW_POWER=off`, and its two steps have a record without `atx`. So the control run also works without the fixed boot id, and the power record can be switched off for a whole driver. The call continues in line 695. |
| 695 | `          r.returncode == 0 and r.stdout.strip().endswith("ALLDONE") and len(f) == 2 and all(not os.path.exists(os.path.join(x, "hw", "atx")) and os.path.isfile(os.path.join(x, "hw", "watch.txt")) for x in f), r.stdout[-800:])` | The conditions: exit status 0, the output ends with `ALLDONE`, there are two result folders, none of them has a folder `hw/atx`, and each has a file `hw/watch.txt`. |

### `run_checks`: the script `run_kernels.sh` (lines 697 to 724)

| Line | Source | Explanation |
|---:|---|---|
| 697 | `    # run_kernels.sh, unchanged text, mode all: the one-thread processes and the 120-thread processes` | Comment: `run_kernels.sh` runs with its unchanged text in the mode `all`: the processes with one thread and the processes with 120 threads. |
| 698 | `    src = os.path.join(cp, "scratch-kernels-test")` | `src`: a folder `scratch-kernels-test` in the test home. `run_kernels.sh` builds and runs in its own folder. |
| 699 | `    os.makedirs(src)` | Creates it. |
| 700 | `    shutil.copy(KERNELS, src)` | Copies `run_kernels.sh` into it. |
| 701 | `    for n in ("bandwidth.orig.c", "bandwidth.c", "selftest.c", "probe.c"):` | Starts a loop over the four source files that the script builds. |
| 702 | `        put(os.path.join(src, n), "/* stand-in */")` | Writes each as a file with one comment. The stand-in `gcc` does not read them. |
| 703 | `    put(os.path.join(cp, "bench", "bandwidth.c"), "/* stand-in */")` | Writes one more such file, `bench/bandwidth.c`. The script computes its checksum. |
| 704 | `    r = bash('"%s/run_kernels.sh" all' % src, env)` | Runs `run_kernels.sh all`. |
| 705 | `    f = result_folders(home, "kernels-")` | `f`: the result folders whose names start with `kernels-`. |
| 706 | `    ok = r.returncode == 0 and len(f) == 1` | `ok`: exit status 0 and exactly one result folder. |
| 707 | `    check("run_kernels.sh all runs to its end with status 0", ok, r.stdout[-800:])` | Check: `run_kernels.sh all` runs to its end with status 0. This script also uses `set -euo pipefail`. |
| 708 | `    if ok:` | The next three checks run only when `ok` holds. |
| 709 | `        hw = os.path.join(f[0], "hw")` | `hw`: the folder `hw` of the result folder. |
| 710 | `        names = sorted(n for n in os.listdir(hw) if n.endswith(".before.txt"))` | `names`: the sorted names of the first snapshots. |
| 711 | `        one = [n for n in names if "-t1-" in n]` | `one`: the names that hold `-t1-`. These are the processes with one thread. |
| 712 | `        check("run_kernels.sh: 192 one-thread processes and 24 processes of 120 threads have a snapshot pair",` | Check: 192 processes with one thread and 24 processes with 120 threads have a pair of snapshots. The call continues in line 713. |
| 713 | `              len(names) == 216 and len(one) == 192 and names[0] == "001-bw_old-read-t1-c0-32K-r1.before.txt" and names[-1] == "216-bw_old-read-t120-c0-119-256M-r2.before.txt", (len(names), names[:1], names[-1:]))` | The conditions: 216 names, 192 of them with one thread, the first is `001-bw_old-read-t1-c0-32K-r1.before.txt`, and the last is `216-bw_old-read-t120-c0-119-256M-r2.before.txt`. |
| 714 | `        cpus = {len(hwwatch.read_snap(os.path.join(hw, n))["cpu"]) for n in one}` | `cpus`: the set of the CPU counts of the snapshots of the processes with one thread. |
| 715 | `        which = {tuple(sorted(hwwatch.read_snap(os.path.join(hw, n))["cpu"])) for n in one}` | `which`: the set of the CPU lists of these snapshots. |
| 716 | `        check("run_kernels.sh: the snapshot of a one-thread process holds only the CPU of that process (CPU 0 or CPU 2)", cpus == {1} and which == {(0,), (2,)}, (cpus, which))` | Check: the snapshot of a process with one thread holds only the CPU of that process, CPU 0 or CPU 2. The only count must be 1, and the lists must be CPU 0 and CPU 2. So the counter read of such a process interrupts only the core of that process. |
| 717 | `        check("run_kernels.sh: the record has no FAILED line and ends with 216 processes", [l for l in lines(os.path.join(hw, "status.txt")) if l.startswith("FAILED")] == []` | Check: the record has no `FAILED` line and ends with 216 processes. No line of `status.txt` may start with `FAILED`. The call continues in line 718. |
| 718 | `              and any(l.endswith("done: 216 processes") for l in lines(os.path.join(hw, "status.txt"))))` | A line of `status.txt` must end with `done: 216 processes`. |
| 719 | `    r = bash('"%s/run_kernels.sh" probe' % src, env, HWDIR=os.path.join(tmp, "no-hw-dir"))` | Runs `run_kernels.sh probe` with `HWDIR` set to a folder that does not exist. |
| 720 | `    f2 = [x for x in result_folders(home, "kernels-") if x not in f]` | `f2`: the result folders of this second run. |
| 721 | `    check("run_kernels.sh probe needs no hw.sh and writes no hardware record", r.returncode == 0 and len(f2) == 1 and not os.path.exists(os.path.join(f2[0], "hw")), r.stdout[-300:])` | Check: `run_kernels.sh probe` needs no `hw.sh` and writes no hardware record. The mode `probe` builds the binaries, prints their machine code and runs the self-test. It times nothing. The exit status must be 0, and the new result folder must have no folder `hw`. |
| 722 | `    check("no sampler and no atx of the test is left running", not no_leftover(tmp), no_leftover(tmp))` | Check: no sampler and no `atx` of the test is left running. |

### Function `main`: the order of the groups and the result line (lines 725 to 748)

| Line | Source | Explanation |
|---:|---|---|
| 725 | `def main():` | Starts the function `main`. |
| 726 | `    tmp = tempfile.mkdtemp(prefix="hwtest.")` | `tmp`: a new temporary folder whose name starts with `hwtest.`. All trees, stand-ins and result folders of the test lie in it. |
| 727 | `    try:` | Starts a block. Lines 735 to 742 run in every case: they end the processes that are left and delete the temporary folder. |
| 728 | `        static_checks()` | First group: `static_checks`, the checks of the script texts (lines 591 to 615). |
| 729 | `        tool_checks(tmp)` | Second group: `tool_checks`, the commands of `hwwatch.py` (lines 114 to 200). |
| 730 | `        report_checks(tmp)` | Third group: `report_checks`, the rules of the report (lines 226 to 329). |
| 731 | `        counts_checks(tmp)` | Fourth group: `counts_checks`, the script `clock_from_counts.py` (lines 332 to 357). |
| 732 | `        hwsh_checks(os.path.join(tmp, "sh"))` | Fifth group: `hwsh_checks`, the functions of `hw.sh`. Its files go to the folder `sh` (lines 469 to 546). |
| 733 | `        if "--no-run" not in sys.argv[1:]:` | Tests whether `--no-run` is not among the arguments. |
| 734 | `            run_checks(os.path.join(tmp, "run"))` | Then: the sixth group, `run_checks`, the run scripts with the stand-ins. Its files go to the folder `run` (lines 618 to 722). |
| 735 | `    finally:` | The `finally` part runs also when a group ended with an error. |
| 736 | `        left = no_leftover(tmp)` | `left`: the lines of `ps` for a stand-in `atx` or a sampler of this test that still runs. |
| 737 | `        for l in left:` | Starts a loop over these lines. |
| 738 | `            try:` | Starts the block whose errors line 740 handles. |
| 739 | `                os.kill(int(l.split()[0]), signal.SIGKILL)` | Sends the signal SIGKILL to the process. Its process id is the first word of the line. |
| 740 | `            except (OSError, ValueError):` | The process is already gone, or the line does not start with a number. |
| 741 | `                pass` | Then nothing is done. |
| 742 | `        shutil.rmtree(tmp, ignore_errors=True)` | Deletes the temporary folder with everything in it. Errors are ignored. |
| 743 | `    print("# checks: %d, passed: %d, failed: %d%s" % (COUNT[0], COUNT[0] - len(FAILS), len(FAILS), "" if not FAILS else " (" + "; ".join(FAILS)[:800] + ")"))` | Prints the result line: `# checks:` with the number of checks, the number that passed and the number that failed. When a check failed, the names of the failed checks follow in parentheses, cut to 800 characters. |
| 744 | `    sys.exit(1 if FAILS else 0)` | Ends the script with exit status 1 when a check failed. If not, the exit status is 0. |
| 747 | `if __name__ == "__main__":` | Lines 747 to 748 run `main` only when the file is started as a program. |
| 748 | `    main()` | Calls `main`. |

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Section 1: the request for the clock rate of the single core in single-core tests. Section 5: decision 1 (the fixed boot id stops `go2.sh` in every other boot), decision 2 (power is required by default), decision 4 (a failure of the record does not stop a started test) and decision 9 (`run.sh`, the saved start command, is unchanged). Section 6: the two signs of a shutdown of the chip. Section 7: the checks ran on the agent server and prove nothing about CRB. Section 8, item 4: the guide of `atx` and its program text differ in one column name of the summary.
- [Ref2] The file `status/2026-11-24-hw-record-evidence/test_hwwatch.out` of the same repo: the output of a run of this file. Its first line gives the time 2026-11-25T01:49:20Z and the agent server. The next lines give the sha256 of the nine files under test. Then one line per check follows. The last two lines hold `# checks: 117, passed: 117, failed: 0` and `# exit status 0 wall time 141 s`.
- [Ref3] The files `defect_trials.sh` and `defect_trials.out` in the folder `status/2026-11-24-hw-record-evidence` of the same repo: the seven defect trials and their output. The header of the script names the four checks that always fail in a copy.
