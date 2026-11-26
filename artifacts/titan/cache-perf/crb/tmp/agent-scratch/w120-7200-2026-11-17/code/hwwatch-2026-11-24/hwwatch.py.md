# `hwwatch.py` explained, line by line

- Source file: `hwwatch-2026-11-24/hwwatch.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 671 lines, 32707 bytes).
- sha256 of the source when this page was built: `eb2884d5f6263e3e031fa2e58687542888aeea4a625c1c0f093e26fe19b97d81`.

## Short version: purpose

`hwwatch.py` is the program that reads the files of Linux for the hardware record of a test. Four commands run beside a test: `check` tests the files, `probe` copies the frequency files once per result folder, `snap` reads six files per CPU before and after a process, and `watch` samples the clock rate of each core once per period. The fifth command, `report`, reads the recorded files after the test and prints the clock rate of the cores per process, with flags for a core that ran slow or was throttled.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **`hw.sh`**: the shell file beside this program. The run scripts of the tests call its functions, and these functions start this program.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process**: one start of a benchmark binary.
- **Clock rate**: the frequency at which a core runs, in kHz or GHz. 2800000 kHz is 2.8 GHz.
- **Throttling**: the chip or its firmware makes a core run slower than Linux requested.
- **Firmware**: the software of the chip that runs below Linux. It controls voltage, frequency and power limits.
- **Snapshot**: one read of a small set of files for a list of CPUs, written to one file (command `snap`).
- **Probe**: the file `probe.txt` of a hardware record (command `probe`). It is written once per result folder.
- **Frequency sampler, sampler**: the command `watch`. It runs in the background and writes the clock rate of each core once per period.
- **Window of a process**: the time from the end of the snapshot before a process to the start of the snapshot after it.
- **`/sys` and `/proc`**: two file trees of Linux. Their files are not on a disk. The Linux kernel computes the content when a program reads a file.
- **`cpufreq`**: the part of the Linux kernel that sets the frequency of the CPUs. Each CPU has a folder `cpufreq` with its files.
- **`acpi_cppc`**: the folder of a CPU with the values of CPPC. CPPC (Collaborative Processor Performance Control) is the interface through which Linux requests a performance level from the firmware and reads the two counters.
- **The two counters**: `ref` and `del` in the file `acpi_cppc/feedback_ctrs` of a CPU. `ref` counts at a fixed reference rate. `del` counts at the rate that the core delivered.
- **Performance value**: a number on the scale of the firmware table of CPPC. The scale has no unit. The firmware table also gives the frequency for two of these numbers.
- **Counter ratio**: the change of `del` divided by the change of `ref` between two snapshots of one CPU.
- **Limit**: the clock rate below which the report flags a value. It is 99 % of the highest frequency of the CPU (`cpuinfo_max_freq`) unless `--tol` says otherwise.
- **Flag**: a word in capital letters that the report prints for a process, for example `LOW_AVG`.
- **`atx`**: Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware.
- **Metric, target**: words of the summary file of `atx`. A metric is one measured quantity, for example the power of one supply. A target is the source that a row of values comes from.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **Signal**: a message that Linux delivers to a process. SIGINT is the interrupt signal. SIGTERM asks a process to end.
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Governor**: the Linux policy that sets the CPU frequency.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it. In this file the words also stand for the value of `--cpus`, the CPUs that a command reads.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the command and its options from the command line and calls the function of the command (lines 645 to 667).
2. Command `check`: for each CPU of the list, test that the counter file, the average rate and the requested rate are readable. Print the failures and return 1 when there is one (lines 221 to 246).
3. Command `probe`: write the files of the folders `cpufreq`, `cpufreq/stats` and `acpi_cppc` of each CPU without four file names that are left out, the system and sensor files, and the entry names of five folders (lines 186 to 218).
4. Command `snap`: for each CPU read five files of `cpufreq`, then the time, then the two counters. Then read the system and sensor files and write one file (lines 176 to 183).
5. Command `watch`: open the file of the average rate of each CPU once, then write one line of values per period, until the watched process is gone, the time limit is reached or a signal arrives (lines 249 to 309).
6. Command `report`: for each result folder read the probe, the samples and each pair of snapshots (`report_folder`), compute the clock rates and the flags per process, read the summary of `atx`, and print the result as text or as JSON (lines 425 to 552, lines 559 to 618, lines 633 to 642).

## Behavior a reader must know

- No test on CRB has run with this file. It was written on 2026-11-24, after all tests [Ref7].
- A CPU list with a CPU above 119 ends the program with exit status 2 before any file of a CPU is read (lines 119 to 122).
- Reads that interrupt a core: by the docstring, a read of the counter file `feedback_ctrs` interrupts the core. `snap` reads it once per CPU, and `probe` and `check` read it too. `watch` never reads it.
- What is timed: the window of a process starts at the value `mono_ns` in the footer of the first snapshot and ends at the value `mono_ns` in the header of the second snapshot (lines 469 to 470). The clock is `CLOCK_MONOTONIC`.
- How a clock rate is computed from the two counters (lines 477 to 488):
  - Counter ratio of one CPU = (change of `del`) divided by (change of `ref`) between its two snapshot lines. No time enters this ratio.
  - Performance value = `reference_perf` times the ratio. `perf_to_khz` turns it into kHz (lines 365 to 382).
  - The two counter reads of a CPU lie inside the two snapshots. So the ratio covers the window and a part of each snapshot.
  - A CPU gets no ratio when a counter is unreadable, when `ref` did not advance, or when `del` went backwards. The process gets the flag `NO_COUNTERS` when no CPU has a ratio.
  - By the design note, Linux on Arm64 can read `ref` and `del` from two counters of the core that stop while the core is idle. Which counters the firmware of CRB names for them was not checked [Ref7].
- Four flags compare a value with the `cpuinfo_max_freq` of the probe: `LOW_AVG`, `LOW_SAMPLE`, `LIMIT_LOWERED` and `REQUEST_BELOW_MAX`. A CPU without that value cannot set any of the four, and a record without `probe.txt` gets none of them (lines 475 to 476, line 497, line 511, line 524).
- Sampled rates of a process: the values of the sampler whose time stamp lies inside the window, both ends included, for the CPUs of the process (lines 501 to 515).
- The energy of a process is the change of an energy counter between the two snapshots. The average power divides it by the time from the end of the first snapshot to the end of the second (lines 471 to 472, lines 588 to 593).
- The report sets no flag from a value of `atx`. It prints these values for the whole result folder, not per process [Ref7].
- Exit statuses: 0 on success. `check` returns 1 when a source is not usable. A bad option value or a bad CPU list gives 2.
- `watch` ends with exit status 0 and a footer line in three cases: the watched process is gone, the time limit is reached, or the signal SIGTERM or SIGINT arrived inside the loop. A sampler that is killed leaves a file without a footer.

## Source and explanation, line by line

- Text shown: the file `hwwatch-2026-11-24/hwwatch.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (671 lines, 32707 bytes, sha256 `eb2884d5f6263e3e031fa2e58687542888aeea4a625c1c0f093e26fe19b97d81`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: the usage and the rules of the program (lines 1 to 13)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""hwwatch.py - records the clock rate of the cores and the signs of throttling beside a CRB test.` | Starts the docstring, a text at the top of the file that describes the program. It ends in line 49. This first line says what the program does: it records the clock rate of the cores and the signs of throttling beside a CRB test. `main` uses this line as the description of the program (line 646). |
| 4 | `Usage:` | Docstring: the heading of the usage. The next five lines give the five commands. |
| 5 | `  hwwatch.py check  --cpus LIST [--root DIR]` | Docstring: the command `check`. `--cpus LIST` names the CPUs. The square brackets mark an option that may be left out: `--root DIR`. |
| 6 | `  hwwatch.py probe  --cpus LIST --out FILE [--root DIR]` | Docstring: the command `probe`. It needs the CPU list and the output file (`--out FILE`). |
| 7 | `  hwwatch.py snap   --cpus LIST --out FILE [--label TEXT] [--root DIR]` | Docstring: the command `snap`. It needs the CPU list and the output file. `--label TEXT` gives the snapshot a label. |
| 8 | `  hwwatch.py watch  --cpus LIST --out FILE --pid PID [--period-s 1] [--max-s 900] [--root DIR]` | Docstring: the command `watch`. It needs the CPU list, the output file and the process id of the process to watch (`--pid PID`). `--period-s` is the time between two samples. Its default is 1 s. `--max-s` is the time limit. Its default is 900 s (15 minutes). |
| 9 | `  hwwatch.py report [--tol 0.01] [--json] RESULT_FOLDER...` | Docstring: the command `report`. It takes one or more result folders. `--tol` is the tolerance of the limit below which a rate is flagged. Its default is 0.01, which is 1 %. `--json` prints the result as JSON, a text format for data. |
| 11 | `It only reads files under /sys and /proc and lists /dev/scmi. It writes only FILE. It changes no setting.` | Docstring: the program only reads files below `/sys` and `/proc`, and it lists the names in the folder `/dev/scmi`. It writes only the file `FILE`, and it changes no setting of the machine. The code does three more things. `probe` reads the text of this program for a checksum (lines 189 to 190). `snap` and `probe` write a file `FILE.tmp` first and then rename it (lines 169 to 173). `report` reads the files of a hardware record. |
| 12 | `It refuses a CPU above 119: the sharing rules of CRB forbid a read of the per-CPU files of CPUs 126 and 127,` | Docstring: the program refuses a CPU number above 119. First reason: the sharing rules of CRB forbid a read of the files of the CPUs 126 and 127. The sentence goes on in line 13. |
| 13 | `and our tests use CPUs 0 to 119 only. --root DIR reads DIR/sys and DIR/proc (for tests with a copied file tree).` | Docstring: second reason: our tests use the CPUs 0 to 119 only. Then a new sentence: with `--root DIR` the program reads `DIR/sys` and `DIR/proc` in place of `/sys` and `/proc`. The tests use this with a copied file tree. |

### Docstring: the files of Linux that the program reads (lines 14 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 15 | `Sources, per CPU N, under /sys/devices/system/cpu/cpuN (file meanings: Linux documents cpufreq.rst, cppc_sysfs.rst and` | Docstring: the heading of the list of sources. Each file lies in the folder `/sys/devices/system/cpu/cpuN` of the CPU with the number N. The meanings come from three documents of the Linux kernel: `cpufreq.rst`, `cppc_sysfs.rst` and the one that line 16 names. |
| 16 | `ABI/testing/sysfs-devices-system-cpu):` | Docstring: the third document is the file `ABI/testing/sysfs-devices-system-cpu`. |
| 17 | `  cpufreq/cpuinfo_avg_freq   kHz. Clock rate of the core, averaged by Linux over its last scheduler tick. Linux` | Docstring: `cpufreq/cpuinfo_avg_freq` holds the clock rate of the core in kHz. Linux averages it over its last scheduler tick. The scheduler tick is the periodic timer interrupt of the Linux kernel on a core. The sentence goes on in line 18. |
| 18 | `                             computes it from two hardware counters of the core (AMU, the Activity Monitors Unit).` | Docstring: Linux computes this value from two hardware counters of the core. They belong to the AMU, the Activity Monitors Unit of an Arm core. |
| 19 | `                             A read sends no interrupt to the core. For an idle core the read fails (EAGAIN).` | Docstring: a read of this file sends no interrupt to the core. For an idle core the read fails with the error `EAGAIN` ("try again"). |
| 20 | `  acpi_cppc/feedback_ctrs    "ref:R del:D", two counters that never reset. Between two reads,` | Docstring: `acpi_cppc/feedback_ctrs` holds one line of the form `ref:R del:D`. R and D are two counters that never reset. Linux calls them the reference counter and the delivered counter [Ref2]. The sentence goes on in line 21. |
| 21 | `                             delivered performance = reference_perf * (change of D) / (change of R).` | Docstring: the rule for the time between two reads: delivered performance = `reference_perf` times (change of D) divided by (change of R). `reference_perf` is the performance level at which the reference counter counts [Ref2]. So the ratio of the two changes gives the speed of the core as a share of the reference level. |
| 22 | `                             A read interrupts the core, so only "snap" and "probe" read it, never "watch".` | Docstring: a read of this file interrupts the core. So, by this line, only `snap` and `probe` read it, and `watch` never does. The code differs in one point: the command `check` reads this file too (line 227). |
| 23 | `  cpufreq/perf_limited       a flag that the firmware sets: not 0 means that a thermal, power or current limit made` | Docstring: `cpufreq/perf_limited` is a flag that the firmware sets. A value other than 0 means that a thermal, power or current limit made the core deliver less than Linux requested. The sentence goes on in line 24. |
| 24 | `                             the core deliver less than Linux requested. Only root can clear it.` | Docstring: only root can clear the flag. |
| 25 | `  cpufreq/scaling_cur_freq   kHz. The rate that Linux requested (not a measured rate on this machine).` | Docstring: `cpufreq/scaling_cur_freq` holds the rate that Linux requested, in kHz. On this machine it is not a measured rate. |
| 26 | `  cpufreq/scaling_max_freq, scaling_min_freq   kHz. The range that Linux may request.` | Docstring: `cpufreq/scaling_max_freq` and `cpufreq/scaling_min_freq` hold the range of rates that Linux may request, in kHz. |

### Docstring: the five commands (lines 28 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `check   tests that the sources exist for the CPUs of LIST. Exit status 0 = usable, 1 = not usable.` | Docstring: `check` tests that the sources exist for the CPUs of the list. Exit status 0 means usable, 1 means not usable. |
| 29 | `probe   writes every file of cpuN/cpufreq and cpuN/acpi_cppc for the CPUs of LIST, the sensor files of` | Docstring: `probe` writes every file of the folders `cpufreq` and `acpi_cppc` of each CPU of the list. The code differs in two points: it leaves out the four file names of `SKIP` (lines 68 to 69), and it also reads the folder `cpufreq/stats` (line 197). The sentence goes on in line 30. |
| 30 | `        /sys/class/hwmon, thermal and powercap, and facts about the system. Run it once per result folder.` | Docstring: `probe` also writes the sensor files of `/sys/class/hwmon`, of `thermal` and of `powercap`, and facts about the system. It is meant to run once per result folder. |
| 31 | `snap    writes the six files above for the CPUs of LIST, and the sensor files. Run it before and after a process.` | Docstring: `snap` writes the six files of lines 17 to 26 for the CPUs of the list, and the sensor files. It is meant to run before and after a process. The code also writes the nine system files, for example the boot id (lines 150 to 151). |
| 32 | `watch   writes cpuinfo_avg_freq of the CPUs of LIST every --period-s seconds. It ends when PID is gone, after` | Docstring: `watch` writes `cpuinfo_avg_freq` of the CPUs of the list once per `--period-s` seconds. It ends when the process `PID` is gone. The sentence goes on in line 33. |
| 33 | `        --max-s seconds, or on SIGTERM or SIGINT. Exit status 0 in these cases. The caller pins it (taskset).` | Docstring: `watch` also ends after `--max-s` seconds, or when it receives the signal SIGTERM or SIGINT. The exit status is 0 in all these cases. The program does not pin itself: the caller pins it with `taskset`. |
| 34 | `report  reads the folder "hw" of each result folder (written by hw.sh) and prints, per process: the clock rate of` | Docstring: `report` reads the folder `hw` of each result folder, which `hw.sh` wrote. Per process it prints the clock rate of each core from the two counters. The code prints less than "each core": the lowest, the median and the highest core (line 568). The list goes on in line 35. |
| 35 | `        each core from the two counters, the sampled rates, the requested rate, the flags, and the power, temperature` | Docstring: `report` also prints the sampled rates, the requested rate, the flags, and the power and temperature values. The sentence goes on in line 36. |
| 36 | `        and frequency values of the vendor tool (atx) when its summary file is there.` | Docstring: the power, temperature and frequency values come from the vendor tool `atx`. They are printed only when the summary file of `atx` exists. |

### Docstring: the output files and the clocks (lines 38 to 49)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `Output files. Lines that start with "#" are header or footer lines. "!NAME" stands for a value that could not be` | Docstring: the form of the output files. A line that starts with `#` is a header line or a footer line. `!NAME` stands for a value that could not be read. The sentence goes on in line 39. |
| 39 | `read: NAME is the error (EAGAIN, ENOENT, EACCES, ...) or PARSE.` | Docstring: `NAME` is the name of the error (`EAGAIN`, `ENOENT`, `EACCES` or another one), or the word `PARSE` for a text that does not have the expected form. `ENOENT` means that the file does not exist. `EACCES` means that the user may not read it. |
| 40 | `  snap:   cpu N t_ns=.. scaling_cur_freq=.. scaling_max_freq=.. scaling_min_freq=.. cpuinfo_avg_freq=.. perf_limited=.. ref=.. del=..` | Docstring: a line of a `snap` file: the word `cpu`, the CPU number, the time of the counter read in ns (`t_ns`), the five values of the folder `cpufreq`, and the two counters `ref` and `del`. |
| 41 | `          s PATH VALUE                      one sensor or system file` | Docstring: the second kind of line of a `snap` file: the letter `s`, a path and the value of one sensor file or system file. |
| 42 | `  probe:  f N RELATIVE_PATH VALUE           one file of cpuN/cpufreq or cpuN/acpi_cppc` | Docstring: a line of a `probe` file: the letter `f`, the CPU number, the path below the folder of the CPU, and the value of one file of `cpufreq` or `acpi_cppc`. |
| 43 | `          s PATH VALUE                      one sensor or system file` | Docstring: a `probe` file also holds `s` lines, as in line 41. |
| 44 | `          l PATH NAME NAME ...              the entries of a folder ("!ENOENT" when the folder is missing)` | Docstring: the third kind of line of a `probe` file: the letter `l`, the path of a folder and the names of its entries. The value is `!ENOENT` when the folder does not exist. |
| 45 | `  watch:  T_MONO_NS V V V ...               one value per CPU of LIST, in kHz, or "na"` | Docstring: a line of a `watch` file: the time of the sample (`T_MONO_NS`), then one value per CPU of the list, in kHz, or the word `na` for no value. |
| 46 | `Clocks: mono_ns is CLOCK_MONOTONIC, boot_ns is CLOCK_BOOTTIME, real_ns is CLOCK_REALTIME.` | Docstring: the three clocks in the files, all in ns. `mono_ns` is `CLOCK_MONOTONIC`, a clock that only runs forward and that a change of the date does not move. `boot_ns` is `CLOCK_BOOTTIME`, which also counts the time while the machine is suspended. `real_ns` is `CLOCK_REALTIME`, the date and time. |
| 48 | `Python 3 standard library only.` | Docstring: the program needs only the standard library of Python 3. |
| 49 | `"""` | Ends the docstring. |

### Imports (lines 50 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 50 | `import argparse` | `argparse` reads the options of the command line (lines 645 to 667). |
| 51 | `import errno` | `errno` gives the names of the error numbers of Linux, such as `ENOENT` (line 132). |
| 52 | `import glob` | `glob` finds files and folders by a name pattern (line 153, line 455). |
| 53 | `import hashlib` | `hashlib` computes the sha256 of this program (line 190). |
| 54 | `import json` | `json` writes the report as JSON (line 636). |
| 55 | `import os` | `os` gives the file and process functions of Linux: open, read, list a folder, rename. |
| 56 | `import platform` | `platform` gives the Python version, the release of the Linux kernel and the machine type (lines 192 to 193). |
| 57 | `import re` | `re` gives regular expressions (patterns for text). |
| 58 | `import signal` | `signal` sets the signal handlers of the sampler (lines 253 to 254). |
| 59 | `import statistics` | `statistics` computes the median and the mean (line 422, line 613). |
| 60 | `import sys` | `sys` gives the error output, the standard output and the exit of the program. |
| 61 | `import time` | `time` gives the clocks and the sleep of the sampler. |

### Constants: the CPU limit, the file lists and the sensor patterns (lines 63 to 84)

| Line | Source | Explanation |
|---:|---|---|
| 63 | `MAX_CPU = 119` | `MAX_CPU`: 119, the highest CPU number that the program accepts. `parse_cpus` ends the program for a higher number (lines 119 to 122). |
| 64 | `CPU_DIR = "/sys/devices/system/cpu"` | `CPU_DIR`: the folder of Linux that holds one folder per CPU (`cpu0`, `cpu1` and so on) and some files for the whole system. |
| 65 | `LIGHT = ["cpufreq/scaling_cur_freq", "cpufreq/scaling_max_freq", "cpufreq/scaling_min_freq",` | `LIGHT`: the five files of the folder `cpufreq` that a snapshot reads for each CPU. This line holds three of them. `scaling_cur_freq`: the rate that Linux requested, in kHz. `scaling_max_freq` and `scaling_min_freq`: the highest and the lowest rate that Linux may request, in kHz (lines 25 to 26) [Ref1]. |
| 66 | `         "cpufreq/cpuinfo_avg_freq", "cpufreq/perf_limited"]` | Continues the list of line 65. `cpuinfo_avg_freq`: the clock rate of the core in kHz, which Linux averages over a few milliseconds at most (lines 17 to 19) [Ref1]. `perf_limited`: the throttle flag of the firmware (lines 23 to 24) [Ref3]. |
| 67 | `FEEDBACK = "acpi_cppc/feedback_ctrs"` | `FEEDBACK`: the path of the counter file below the folder of a CPU. The file holds the two counters in one line of the form `ref:R del:D` (lines 20 to 22). By the Linux document, `ref` counts in proportion to the reference performance of the processor, and `del` counts in proportion to the performance that it delivered [Ref2]. The counters have no unit. |
| 68 | `# Not read by probe: the first is readable by root only and interrupts the core, the others are not values.` | Comment: the probe does not read the four files of line 69. The first is readable by root only, and a read of it interrupts the core. The other three are not values. |
| 69 | `SKIP = {"cpuinfo_cur_freq", "scaling_setspeed", "trans_table", "reset"}` | `SKIP`: the set of these four file names. `cpuinfo_cur_freq` is the first name of the comment. By the Linux document it holds the frequency in kHz as the hardware reports it [Ref1]. `scaling_setspeed` works only with the governor `userspace` [Ref1]. `trans_table` is a table that counts the changes from each frequency to each other frequency. `reset` is a write-only file that clears these statistics [Ref6]. |
| 70 | `SYSTEM_FILES = ["/proc/sys/kernel/random/boot_id", "/proc/uptime", "/proc/loadavg", "/proc/cmdline",` | `SYSTEM_FILES`: nine files for the whole system. Each snapshot and the probe read them (lines 150 to 151). This line holds four. `boot_id`: the boot id, a random identifier that Linux creates once per boot. `/proc/uptime`: two numbers in seconds, the time from the boot until now and the time that the idle process has used [Ref5]. `/proc/loadavg`: the load averages of the last 1, 5 and 15 minutes, and the number of tasks that are runnable now. `/proc/cmdline`: the arguments that the Linux kernel got at boot [Ref5]. |
| 71 | `                CPU_DIR + "/online", CPU_DIR + "/offline", CPU_DIR + "/isolated", CPU_DIR + "/possible",` | Continues the list: four lists of CPUs in the folder `CPU_DIR` [Ref3]. `online`: the CPUs that are online and that the scheduler uses. `offline`: the CPUs that are not online. `isolated`: the CPUs that are kept out of the load balancing of the scheduler. `possible`: the CPUs that can be brought online when they are present. |
| 72 | `                CPU_DIR + "/cpufreq/boost"]` | Ends the list. `cpufreq/boost` holds the boost setting of the whole system. 1 means that the cores may run above their sustained frequency for a short time. 0 means that they may not [Ref1]. The report uses the value in its conversion rule `max` (line 379). |
| 73 | `LISTED = ["/sys/class/hwmon", "/sys/class/thermal", "/sys/class/powercap", "/sys/fs/arm_telemetry", "/dev/scmi"]` | `LISTED`: five folders. The probe writes the names of their entries, not the content of the entries (lines 210 to 215). `/sys/class/hwmon`: hardware sensors. `/sys/class/thermal`: thermal zones and cooling devices. `/sys/class/powercap`: power limits. `/sys/fs/arm_telemetry` and `/dev/scmi`: the telemetry folders. By the design note, the device files in `/dev/scmi` pass the values of the firmware to programs [Ref7]. |
| 74 | `# Sensor files: folder pattern and the file names that are read in each matching folder.` | Comment: the list `SENSORS` holds one entry per kind of sensor folder. An entry is a pattern for the folder names, and the file names that are read in each folder that matches. |
| 75 | `SENSORS = [` | Starts the list `SENSORS`. `sensor_lines` uses it (lines 152 to 161). |
| 76 | `    ("/sys/class/hwmon/hwmon*", re.compile(r"^(name\|(temp\|power\|energy\|curr\|in\|freq\|fan)\d+_\w+)$")),` | Entry 1: the folders `hwmon0`, `hwmon1` and so on below `/sys/class/hwmon` (hardware sensors). The name pattern accepts `name` (the name of the sensor chip). It also accepts each name that is one of seven words, then digits, an underscore and more letters, digits or underscores, for example `temp1_input`. The words are `temp`, `power`, `energy`, `curr`, `in`, `freq` and `fan`. Group 1 holds the whole name and group 2 the word. Units of the `input` files by the Linux file: temperature in millidegrees Celsius, power in microwatts, energy in microjoules, current in milliamperes, voltage (`in`) in millivolts, fan speed in revolutions per minute [Ref4]. |
| 77 | `    ("/sys/class/thermal/thermal_zone*", re.compile(r"^(type\|temp\|mode\|policy\|trip_point_\d+_(temp\|type))$")),` | Entry 2: the folders of the thermal zones. The name pattern accepts `type` (the kind of the zone), `temp` (its temperature in millidegrees Celsius), `mode` (enabled or disabled), `policy` (the governor of the zone), and the temperature and the type of each trip point, for example `trip_point_0_temp` [Ref4]. A trip point is a temperature limit of the zone. Group 1 holds the whole name, and group 2 the last word of a trip point name. The code only tests whether a name fits. |
| 78 | `    ("/sys/class/thermal/cooling_device*", re.compile(r"^(type\|cur_state\|max_state)$")),` | Entry 3: the folders of the cooling devices. The name pattern accepts `type` (the kind of device), `cur_state` (the cooling state now) and `max_state` (the highest cooling state) [Ref4]. Group 1 holds the name. |
| 79 | `    ("/sys/class/powercap/*", re.compile(r"^(name\|enabled\|power_uw\|energy_uj\|max_energy_range_uj\|max_power_range_uw"` | Entry 4: each entry of the folder `/sys/class/powercap` (power limits). The name pattern accepts `name`, `enabled`, `power_uw` (the power now, in microwatts), `energy_uj` (an energy counter in microjoules), and the ranges of these two values (`max_energy_range_uj`, `max_power_range_uw`) [Ref4]. The pattern goes on in line 80. |
| 80 | `                                         r"\|constraint_\d+_(name\|power_limit_uw\|max_power_uw\|time_window_us))$")),` | Continues the pattern of line 79: four files per constraint, with the number of the constraint in the name. A constraint is one power limit of the zone. The files hold its name, its power limit in microwatts, its highest allowed power in microwatts, and its time window in microseconds [Ref4]. Group 1 of the whole pattern holds the file name, and group 2 the last part of the name of a constraint file. |
| 81 | `]` | Ends the list `SENSORS`. |
| 82 | `CLOCK_BOOTTIME = getattr(time, "CLOCK_BOOTTIME", 7)` | `CLOCK_BOOTTIME`: the number of the Linux clock of that name. `getattr` takes it from the module `time`. When this Python has no such name, the value is 7. |

### Small helpers: `Stop`, `on_signal`, `die`, `mono` and `clocks` (lines 85 to 105)

| Line | Source | Explanation |
|---:|---|---|
| 85 | `class Stop(Exception):` | Defines the exception class `Stop`. The signal handler raises it to end the sampling loop of `cmd_watch` (line 305). |
| 86 | `    pass` | `pass`: the class adds nothing to its base class `Exception`. |
| 89 | `def on_signal(signum, frame):` | Starts the function `on_signal`, the signal handler of the sampler (lines 253 to 254). Python calls it with the signal number and the place in the program at which the signal arrived. |
| 90 | `    raise Stop()` | Raises `Stop` at that place. |
| 93 | `def die(msg, status=2):` | Starts the function `die`. It prints an error message and ends the program. The exit status is 2 unless the caller gives another one. |
| 94 | `    sys.stderr.write("hwwatch.py: ERROR: %s\n" % msg)` | Writes `hwwatch.py: ERROR:` and the message to the error output. |
| 95 | `    sys.exit(status)` | Ends the program with the exit status `status`. |
| 98 | `def mono():` | Starts the function `mono`. It returns the time of the clock `CLOCK_MONOTONIC` in ns. The durations of the program and the time stamps `t_ns`, `t_mono_ns` and `mono_ns` of its output files come from it. |
| 99 | `    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)` | `time.clock_gettime_ns` reads the clock as a whole number of ns. |
| 102 | `def clocks():` | Starts the function `clocks`. It returns one text with three clock readings, for a header line or a footer line. |
| 103 | `    return "mono_ns=%d boot_ns=%d real_ns=%d" % (mono(), time.clock_gettime_ns(CLOCK_BOOTTIME), time.time_ns())` | The text has the form `mono_ns=N boot_ns=N real_ns=N`. The three values are `CLOCK_MONOTONIC`, `CLOCK_BOOTTIME`, and the date and time as ns counted from 1970-01-01 00:00 UTC (`time.time_ns`). The three clocks are read one after the other. |

### Function `parse_cpus`: from the text of a CPU list to a list of numbers (lines 106 to 125)

| Line | Source | Explanation |
|---:|---|---|
| 106 | `def parse_cpus(text):` | Starts the function `parse_cpus`. It turns the text of a CPU list into a list of CPU numbers. It ends the program for a bad list. |
| 107 | `    """ "0-63,64-119" -> [0, ..., 119]. Order of the text, no CPU twice, no CPU above MAX_CPU."""` | Docstring: the text `0-63,64-119` gives the numbers 0 to 119. The numbers keep the order of the text. No CPU may be named twice, and no CPU may be above `MAX_CPU`. |
| 108 | `    out = []` | `out`: the list of CPU numbers, empty at the start. |
| 109 | `    for part in text.split(","):` | Splits the text at the commas and handles each part. |
| 110 | `        m = re.match(r"^(\d+)(?:-(\d+))?$", part.strip())` | The pattern accepts a part that is one number, or two numbers with a hyphen between them. `part.strip()` removes spaces at both ends first. Group 1 holds the first number. Group 2 holds the second number. It is empty when the part is one number. |
| 111 | `        if not m:` | Tests whether the part does not have this form. |
| 112 | `            die("bad CPU list %r" % text)` | Then `die` prints `bad CPU list` with the whole text and ends the program with exit status 2. |
| 113 | `        a, b = int(m.group(1)), int(m.group(2) or m.group(1))` | `a`: the first CPU of the part. `b`: the last CPU. For a single number, `b` is equal to `a`. |
| 114 | `        if b < a:` | Tests whether the range runs backwards, as in `5-3`. |
| 115 | `            die("bad CPU range %r" % part)` | Then `die` prints `bad CPU range` with the part and ends the program. |
| 116 | `        out.extend(range(a, b + 1))` | Adds the CPUs `a` to `b` to the list, both ends included. |
| 117 | `    if len(set(out)) != len(out):` | Tests whether a CPU is named twice. A set holds each value once. So the set is smaller than the list when a number occurs twice. |
| 118 | `        die("CPU list %r names a CPU twice" % text)` | Then `die` prints that the list names a CPU twice, and ends the program. |
| 119 | `    for c in out:` | Starts a loop over all CPU numbers of the list. |
| 120 | `        if c > MAX_CPU:` | Tests whether the number is above `MAX_CPU` (119). |
| 121 | `            die("CPU %d is above %d. CPUs 126 and 127 are isolated for another user of CRB, and their per-CPU files "` | Then `die` prints that the CPU is above 119, and that the CPUs 126 and 127 are isolated for another user of CRB. The message goes on in line 122. The test also refuses the CPUs 120 to 125. |
| 122 | `                "must not be read. Our tests use CPUs 0 to %d only." % (c, MAX_CPU, MAX_CPU))` | The rest of the message: the files of those CPUs must not be read, and our tests use the CPUs 0 to 119 only. Each command calls `parse_cpus` before it reads a file of a CPU. So the program ends with exit status 2 before any such read. |
| 123 | `    return out` | Returns the list. |

### Functions `read_value` and `read_cpu_light`: one file, and one snapshot line of a CPU (lines 126 to 146)

| Line | Source | Explanation |
|---:|---|---|
| 126 | `def read_value(path):` | Starts the function `read_value`. It reads one file and returns its text in one line. `check`, `probe` and `snap` read every file of `/sys` and `/proc` through this function. |
| 127 | `    """The text of a file, in one line, or "!NAME" for the error that the read gave."""` | Docstring: the function returns the text of the file in one line, or `!NAME` for the error that the read gave. |
| 128 | `    try:` | Starts the block whose errors line 131 handles. |
| 129 | `        with open(path, "rb", buffering=0) as f:` | Opens the file for reading, in binary mode. `buffering=0`: Python keeps no buffer of its own. So line 130 is one read request to Linux. |
| 130 | `            data = f.read(65536)` | Reads at most 65536 bytes with one request. A longer file would be cut there. |
| 131 | `    except OSError as e:` | The open or the read failed with an error of the operating system. |
| 132 | `        return "!" + errno.errorcode.get(e.errno, "E%d" % (e.errno or 0))` | Returns `!` and the name of the error number, for example `!ENOENT` for a missing file or `!EAGAIN` for an idle core. An error number without a known name gives `!E` and the number. |
| 133 | `    return data.decode("utf-8", "replace").strip().replace("\n", "\\n")` | Turns the bytes into text. With `replace`, a byte that is not valid UTF-8 becomes a replacement mark. `strip` removes white space at both ends. Each line break inside the text is written as the two characters `\n`. So the value fits in one line of the output file. |
| 136 | `def read_cpu_light(root, cpu):` | Starts the function `read_cpu_light`. It reads the six files of one CPU for a snapshot and returns them as one line. `root` is the prefix of `--root`. |
| 137 | `    """One snapshot line of a CPU. The time is read directly before the two counters."""` | Docstring: the function returns one snapshot line of a CPU. The time is read directly before the two counters. |
| 138 | `    base = "%s%s/cpu%d/" % (root, CPU_DIR, cpu)` | `base`: the folder of the CPU with the prefix `root` in front, for example `/sys/devices/system/cpu/cpu5/`. |
| 139 | `    vals = [(os.path.basename(rel), read_value(base + rel)) for rel in LIGHT]` | `vals`: a list of five pairs, one per file of `LIGHT`, in that order. Each pair holds the file name without its folder (`os.path.basename`) and the value that `read_value` returns. |
| 140 | `    t = mono()` | `t`: the time in ns, read directly before the counter file. It becomes `t_ns` of the line. |
| 141 | `    fb = read_value(base + FEEDBACK)` | `fb`: the text of the counter file `acpi_cppc/feedback_ctrs`. By the docstring of the file, this read interrupts the core (line 22). |
| 142 | `    m = re.match(r"^ref:(\d+) del:(\d+)$", fb)` | The pattern accepts a text of exactly this form: `ref:`, digits, one space, `del:`, digits. Group 1 holds the reference counter and group 2 the delivered counter. |
| 143 | `    ref, dele = (m.group(1), m.group(2)) if m else ((fb, fb) if fb.startswith("!") else ("!PARSE", "!PARSE"))` | `ref` and `dele`: the two counters as text. When the text has the form of line 142, they are the two groups. When the read failed, both hold the error text, which starts with `!`. In every other case both hold `!PARSE`. |
| 144 | `    return "cpu %d t_ns=%d %s ref=%s del=%s" % (cpu, t, " ".join("%s=%s" % kv for kv in vals), ref, dele)` | Returns the line: the word `cpu`, the CPU number, `t_ns=` with the time, the five `name=value` pairs with spaces between them, then `ref=` and `del=` with the counters. Here `kv` is one pair of line 139. It is not the function `kv` of line 314. |

### Functions `sensor_lines`, `unreadable` and `write_file` (lines 147 to 175)

| Line | Source | Explanation |
|---:|---|---|
| 147 | `def sensor_lines(root):` | Starts the function `sensor_lines`. It reads the system files and the sensor files and returns one output line per file. |
| 148 | `    """One "s" line per sensor file and per system file."""` | Docstring: the function returns one `s` line per sensor file and per system file. |
| 149 | `    out = []` | `out`: the list of lines, empty at the start. |
| 150 | `    for p in SYSTEM_FILES:` | Starts a loop over the nine system files of lines 70 to 72. |
| 151 | `        out.append("s %s %s" % (p, read_value(root + p)))` | Adds the line: the letter `s`, the path without the prefix `root`, and the value. A file that cannot be read gives `!NAME` as its value. |
| 152 | `    for pattern, names in SENSORS:` | Starts a loop over the four entries of `SENSORS`. Each entry is a folder pattern and a name pattern. |
| 153 | `        for folder in sorted(glob.glob(root + pattern)):` | `glob.glob` finds every folder below `root` that matches the folder pattern. The loop handles the folders in the order of their names. |
| 154 | `            try:` | Starts the block whose errors line 156 handles. |
| 155 | `                entries = sorted(os.listdir(folder))` | `entries`: the names in the folder, sorted. |
| 156 | `            except OSError:` | The folder cannot be listed. |
| 157 | `                continue` | Then the folder is skipped without an output line. |
| 158 | `            for name in entries:` | Starts a loop over the names in the folder. |
| 159 | `                path = os.path.join(folder, name)` | `path`: the full path of the entry. |
| 160 | `                if names.match(name) and os.path.isfile(path):` | Takes the entry only when its name fits the name pattern and it is a regular file, not a folder. |
| 161 | `                    out.append("s %s %s" % (path[len(root):], read_value(path)))` | Adds the `s` line of this file: the path without the prefix `root`, and the value. |
| 162 | `    return out` | Returns the lines. |
| 165 | `def unreadable(lines):` | Starts the function `unreadable`. It counts the values in a list of output lines that could not be read. |
| 166 | `    return sum(line.count("=!") + (1 if re.search(r" ![A-Z0-9]+$", line) else 0) for line in lines)` | Adds two counts per line. First count: how often `=!` occurs, which is one per failed value of a `cpu` line. Second count: 1 when the line ends with a space, a `!` and capital letters or digits, which is a failed value of an `s`, `f` or `l` line. A counter file that could not be read counts as 2: once for `ref` and once for `del`. The value `!EAGAIN` that an idle core gives for `cpuinfo_avg_freq` (line 19) counts as 1 too. |
| 169 | `def write_file(path, lines):` | Starts the function `write_file`. It writes a list of lines to a file. No reader sees a file that is half written. |
| 170 | `    tmp = path + ".tmp"` | `tmp`: the name of a temporary file beside the output file: the output path with `.tmp` at its end. |
| 171 | `    with open(tmp, "w") as f:` | Opens the temporary file for writing. |
| 172 | `        f.write("\n".join(lines) + "\n")` | Writes all lines, each with a line break at its end. |
| 173 | `    os.replace(tmp, path)` | `os.replace` gives the temporary file the name of the output file and replaces an older file of that name. So the output file appears only after all lines are written. |

### Function `cmd_snap`: one snapshot (lines 176 to 185)

| Line | Source | Explanation |
|---:|---|---|
| 176 | `def cmd_snap(a):` | Starts the function `cmd_snap`, the command `snap`. `a` holds the options of the command line. |
| 177 | `    cpus = parse_cpus(a.cpus)` | `cpus`: the CPU numbers of `--cpus`. `parse_cpus` ends the program for a bad list or for a CPU above 119. |
| 178 | `    t0 = mono()` | `t0`: the time at the start, for the duration in the footer. |
| 179 | `    out = ["# hwwatch v1 snap label=%s cpus=%s" % (re.sub(r"\s+", "_", a.label) or "-", a.cpus), "# clocks " + clocks()]` | `out`: the lines of the file. It starts with two header lines. The first holds `# hwwatch v1 snap`, the label and the CPU list as given. `re.sub` replaces each run of white space in the label with one underscore, and an empty label becomes `-`. The second holds `# clocks` and the three clocks at the start of the snapshot. The report takes `mono_ns` of this line of the second snapshot as the end of the window of a process (line 469). |
| 180 | `    body = [read_cpu_light(a.root, c) for c in cpus] + sensor_lines(a.root)` | `body`: one `cpu` line per CPU, in the order of the list, then the `s` lines. The comprehension calls `read_cpu_light` for one CPU after the other. So the CPUs are read at different times, each with its own `t_ns`. The system and sensor files are read last. |
| 181 | `    out += body` | Appends the body to the header lines. |
| 182 | `    out.append("# end %s took_ms=%.1f unreadable=%d" % (clocks(), (mono() - t0) / 1e6, unreadable(body)))` | Adds the footer: `# end`, the three clocks at the end of the snapshot, `took_ms` (the duration of the snapshot in ms, with one decimal) and `unreadable` (the count of lines 165 to 166). The report takes `mono_ns` of this line of the first snapshot as the start of the window of a process (line 469). |
| 183 | `    write_file(a.out, out)` | Writes the file through `write_file`. The function returns no value. `main` turns that into exit status 0 (line 667). |

### Function `cmd_probe`: the files of the frequency folders, once per result folder (lines 186 to 220)

| Line | Source | Explanation |
|---:|---|---|
| 186 | `def cmd_probe(a):` | Starts the function `cmd_probe`, the command `probe`. |
| 187 | `    cpus = parse_cpus(a.cpus)` | `cpus`: the CPU numbers of `--cpus`. |
| 188 | `    t0 = mono()` | `t0`: the time at the start. |
| 189 | `    with open(os.path.abspath(__file__), "rb") as f:` | Opens the file of this program itself (`__file__`) in binary mode. |
| 190 | `        sha = hashlib.sha256(f.read()).hexdigest()` | `sha`: the sha256 of the program text, as hexadecimal digits. So the probe records which text of the tool wrote it. |
| 191 | `    out = ["# hwwatch v1 probe cpus=%s" % a.cpus, "# clocks " + clocks(),` | `out` starts with four header lines. This line holds two: `# hwwatch v1 probe` with the CPU list as given, and `# clocks` with the three clocks. |
| 192 | `           "# tool sha256=%s python=%s" % (sha, platform.python_version()),` | The third header line: `# tool` with the sha256 of this program and the version of Python. |
| 193 | `           "# uname %s %s" % (platform.release(), platform.machine())]` | The fourth header line: `# uname` with the release of the running Linux kernel and the machine type. |
| 194 | `    body = []` | `body`: the data lines, empty at the start. |
| 195 | `    for cpu in cpus:` | Starts a loop over the CPUs. |
| 196 | `        base = "%s%s/cpu%d" % (a.root, CPU_DIR, cpu)` | `base`: the folder of the CPU. |
| 197 | `        for sub in ("cpufreq", "cpufreq/stats", "acpi_cppc"):` | Starts a loop over three folders of the CPU: `cpufreq`, `cpufreq/stats` (statistics of the frequency changes) and `acpi_cppc`. |
| 198 | `            folder = os.path.join(base, sub)` | `folder`: the full path. |
| 199 | `            try:` | Starts the block whose errors line 201 handles. |
| 200 | `                entries = sorted(os.listdir(folder))` | `entries`: the names in the folder, sorted. |
| 201 | `            except OSError as e:` | The folder cannot be listed, for example when it does not exist. |
| 202 | `                if sub != "cpufreq/stats":` | A missing `cpufreq/stats` gives no line. For the other two folders line 203 writes a line. |
| 203 | `                    body.append("f %d %s !%s" % (cpu, sub, errno.errorcode.get(e.errno, "E%d" % (e.errno or 0))))` | Adds the line: the letter `f`, the CPU number, the folder name, and `!` with the name of the error. |
| 204 | `                continue` | Goes on with the next folder. |
| 205 | `            for name in entries:` | Starts a loop over the names in the folder. |
| 206 | `                path = os.path.join(folder, name)` | `path`: the full path of the entry. |
| 207 | `                if name not in SKIP and os.path.isfile(path):` | Takes the entry only when its name is not in `SKIP` and it is a regular file. The folder `stats` inside `cpufreq` is not a regular file. The loop of line 197 handles it as its own folder. |
| 208 | `                    body.append("f %d %s/%s %s" % (cpu, sub, name, read_value(path)))` | Adds the line: the letter `f`, the CPU number, the path below the folder of the CPU, and the value. One of these files is the counter file `acpi_cppc/feedback_ctrs`. So the probe reads the counter file of each CPU of its list once, and by the docstring such a read interrupts the core (line 22). The lines also hold `cpufreq/cpuinfo_max_freq` (the highest frequency of the CPU in kHz [Ref1]) and the values of `acpi_cppc` that the report needs for the conversion to kHz (lines 440 to 442). |
| 209 | `    body += sensor_lines(a.root)` | Adds the `s` lines of the system files and the sensor files. |
| 210 | `    for folder in LISTED:` | Starts a loop over the five folders of `LISTED`. |
| 211 | `        try:` | Starts the block whose errors line 213 handles. |
| 212 | `            names = " ".join(sorted(os.listdir(a.root + folder))) or "(empty)"` | `names`: the names in the folder, sorted, with spaces between them. An empty folder gives the text `(empty)`. |
| 213 | `        except OSError as e:` | The folder cannot be listed. |
| 214 | `            names = "!" + errno.errorcode.get(e.errno, "E%d" % (e.errno or 0))` | Then `names` becomes `!` and the name of the error, for example `!ENOENT`. |
| 215 | `        body.append("l %s %s" % (folder, names))` | Adds the line: the letter `l`, the path of the folder and the names. |
| 216 | `    out += body` | Appends the body to the header lines. |
| 217 | `    out.append("# end %s took_ms=%.1f unreadable=%d" % (clocks(), (mono() - t0) / 1e6, unreadable(body)))` | Adds the footer, as in line 182: the three clocks, the duration in ms and the number of unreadable values. |
| 218 | `    write_file(a.out, out)` | Writes the file through `write_file`. |

### Function `cmd_check`: are the sources usable (lines 221 to 248)

| Line | Source | Explanation |
|---:|---|---|
| 221 | `def cmd_check(a):` | Starts the function `cmd_check`, the command `check`. It returns the exit status: 0 for usable, 1 for not usable. |
| 222 | `    """The sources that the tool cannot work without, tested on the CPUs of LIST."""` | Docstring: the function tests the sources that the tool cannot work without, on the CPUs of the list. |
| 223 | `    cpus = parse_cpus(a.cpus)` | `cpus`: the CPU numbers of `--cpus`. |
| 224 | `    bad, notes = [], []` | `bad`: the list of failures. `notes`: the list of remarks that do not fail the check. |
| 225 | `    for cpu in cpus:` | Starts a loop over the CPUs. |
| 226 | `        base = "%s%s/cpu%d/" % (a.root, CPU_DIR, cpu)` | `base`: the folder of the CPU. |
| 227 | `        fb = read_value(base + FEEDBACK)` | `fb`: the text of the counter file. The docstring of the file does not name `check` among the commands that read this file (line 22). |
| 228 | `        if not re.match(r"^ref:\d+ del:\d+$", fb):` | Tests whether the text does not have the form `ref:`, digits, a space, `del:`, digits. |
| 229 | `            bad.append("cpu%d %s: %s" % (cpu, FEEDBACK, fb))` | Then: adds a failure with the CPU, the file name and the text that was read, for example `!ENOENT`. |
| 230 | `        avg = read_value(base + "cpufreq/cpuinfo_avg_freq")` | `avg`: the text of `cpufreq/cpuinfo_avg_freq`, the average clock rate. |
| 231 | `        if not (avg.isdigit() or avg == "!EAGAIN"):      # EAGAIN: the core is idle, the file exists` | The value is good when it holds digits only, or when the read gave `!EAGAIN`. Comment: `EAGAIN` means that the core is idle. The file exists in that case. |
| 232 | `            bad.append("cpu%d cpufreq/cpuinfo_avg_freq: %s" % (cpu, avg))` | If not: adds a failure. |
| 233 | `        cur = read_value(base + "cpufreq/scaling_cur_freq")` | `cur`: the text of `cpufreq/scaling_cur_freq`, the requested rate. |
| 234 | `        if not cur.isdigit():` | Tests whether the value holds anything other than digits. |
| 235 | `            bad.append("cpu%d cpufreq/scaling_cur_freq: %s" % (cpu, cur))` | Then: adds a failure. |
| 236 | `        lim = read_value(base + "cpufreq/perf_limited")` | `lim`: the text of `cpufreq/perf_limited`, the throttle flag. |
| 237 | `        if not lim.isdigit():` | Tests whether the value is not a number. |
| 238 | `            notes.append("cpu%d cpufreq/perf_limited: %s" % (cpu, lim))` | Then: adds a note. A missing throttle flag does not fail the check. |
| 239 | `    for n in notes:` | Starts a loop over the notes. |
| 240 | `        print("note: no throttle flag: " + n)` | Prints `note: no throttle flag:` and the note. |
| 241 | `    for b in bad:` | Starts a loop over the failures. |
| 242 | `        print("FAILED: " + b)` | Prints `FAILED:` and the failure. |
| 243 | `    if bad:` | Tests whether any failure was found. |
| 244 | `        return 1` | Then: returns 1. The program ends with exit status 1. |
| 245 | `    print("ok: the two counters, the average rate and the requested rate are readable for CPUs %s" % a.cpus)` | Prints one line that starts with `ok:`. It says that the two counters, the average rate and the requested rate are readable for the CPUs of the list. |
| 246 | `    return 0` | Returns 0. |

### Function `cmd_watch`: the setup of the frequency sampler (lines 249 to 275)

| Line | Source | Explanation |
|---:|---|---|
| 249 | `def cmd_watch(a):` | Starts the function `cmd_watch`, the command `watch`. This is the frequency sampler. |
| 250 | `    cpus = parse_cpus(a.cpus)` | `cpus`: the CPU numbers of `--cpus`. |
| 251 | `    if a.period_s <= 0 or a.max_s <= 0:` | Tests whether the period or the time limit is 0 or below. |
| 252 | `        die("--period-s and --max-s must be above 0")` | Then `die` prints that both must be above 0, and ends the program with exit status 2. |
| 253 | `    signal.signal(signal.SIGTERM, on_signal)` | Sets `on_signal` as the handler of the signal SIGTERM. `hw_done` of `hw.sh` sends this signal to stop the sampler. |
| 254 | `    signal.signal(signal.SIGINT, on_signal)` | Sets the same handler for SIGINT, the interrupt signal. |
| 255 | `    fds = []` | `fds`: one open file per CPU, empty at the start. |
| 256 | `    for cpu in cpus:` | Starts a loop over the CPUs. |
| 257 | `        try:` | Starts the block whose errors line 259 handles. |
| 258 | `            fds.append(os.open("%s%s/cpu%d/cpufreq/cpuinfo_avg_freq" % (a.root, CPU_DIR, cpu), os.O_RDONLY))` | Opens the file `cpufreq/cpuinfo_avg_freq` of the CPU for reading and keeps the file descriptor (the number of the open file). The file is opened once and stays open for the whole run. |
| 259 | `        except OSError:` | The file cannot be opened. |
| 260 | `            fds.append(-1)` | Then -1 is stored for this CPU. Its column holds `na` in every sample (line 282). |
| 261 | `    period = int(a.period_s * 1e9)` | `period`: the time between two samples in ns. |
| 262 | `    samples = nas = missed = 0` | Three counters start at 0. `samples`: the samples written. `nas`: the values that were `na`. `missed`: the time slots that were skipped. |
| 263 | `    worst = 0` | `worst`: the longest duration of one sample so far, in ns. |
| 264 | `    reason = "error"` | `reason`: why the sampler ended. It starts as `error`. |
| 265 | `    with open(a.out, "w", buffering=1) as out:` | Opens the output file for writing. `buffering=1`: Python passes each finished line to the file at once. So the file holds every sample taken so far, also when the sampler is killed. |
| 266 | `        out.write("# hwwatch v1 watch pid=%d cpus=%s period_s=%g max_s=%g\n" % (a.pid, a.cpus, a.period_s, a.max_s))` | The first header line: `# hwwatch v1 watch`, the process id of the watched process, the CPU list, the period and the time limit in seconds. |
| 267 | `        out.write("# clocks %s\n" % clocks())` | The second header line: `# clocks` with the three clocks. |
| 268 | `        try:` | Starts the block whose errors line 270 handles. |
| 269 | `            allowed = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)))` | `allowed`: the CPUs on which Linux may run this process, as numbers with commas between them. `os.sched_getaffinity(0)` gives this set for the calling process. |
| 270 | `        except (AttributeError, OSError):` | The call does not exist on this system, or it failed. |
| 271 | `            allowed = "na"` | Then `allowed` becomes `na`. |
| 272 | `        out.write("# sampler pid=%d allowed_cpus=%s\n" % (os.getpid(), allowed))` | The third header line: `# sampler` with the process id of the sampler and the CPUs on which it may run. So the file records where the sampler ran. With the `taskset` of `hw.sh` this is one CPU, by default CPU 119. |
| 273 | `        out.write("# cols t_mono_ns, then cpuinfo_avg_freq in kHz for each CPU of the list in its order; na = no value\n")` | The fourth header line names the columns: the time `t_mono_ns`, then `cpuinfo_avg_freq` in kHz for each CPU of the list, in the order of the list. `na` stands for no value. |
| 274 | `        start = mono()` | `start`: the time at which the sampling schedule starts. |
| 275 | `        slot = 0` | `slot`: the number of the time slot. Slot number k starts at `start` plus k periods. |

### Function `cmd_watch`: the sampling loop and the footer (lines 276 to 311)

| Line | Source | Explanation |
|---:|---|---|
| 276 | `        try:` | Starts the block that catches `Stop` (line 305). Only the loop is inside this block. A signal that arrives before it, in lines 255 to 275, raises `Stop` outside the block. The program then ends with a Python error and without a footer. |
| 277 | `            while True:` | Starts the loop. Each pass takes one sample. |
| 278 | `                t = mono()` | `t`: the time stamp of the sample in ns, read before the files. |
| 279 | `                vals = []` | `vals`: the values of this sample. |
| 280 | `                for fd in fds:` | Starts a loop over the open files, one per CPU. |
| 281 | `                    try:` | Starts the block whose errors line 283 handles. |
| 282 | `                        v = os.pread(fd, 32, 0).strip() if fd >= 0 else b""` | `os.pread` reads at most 32 bytes from position 0 of the open file. So each sample gets the value of this moment without a new open. `strip` removes the line break. A CPU without an open file (-1) gives an empty value. |
| 283 | `                    except OSError:` | The read failed. By the docstring this happens for an idle core, with the error `EAGAIN` (line 19). |
| 284 | `                        v = b""` | Then the value becomes empty. |
| 285 | `                    if v.isdigit():` | Tests whether the value holds digits only. |
| 286 | `                        vals.append(v.decode())` | Then: adds the number, in kHz, as text. |
| 287 | `                    else:` | If not: lines 288 to 289 run. |
| 288 | `                        vals.append("na")` | Adds the word `na`. |
| 289 | `                        nas += 1` | Adds 1 to the count of `na` values. |
| 290 | `                out.write("%d %s\n" % (t, " ".join(vals)))` | Writes the sample line: the time stamp, then the values with spaces between them. |
| 291 | `                samples += 1` | Adds 1 to the count of samples. |
| 292 | `                worst = max(worst, mono() - t)` | `worst`: the longest time from the time stamp of a sample to the end of its write, in ns. |
| 293 | `                if not os.path.exists("/proc/%d" % a.pid):` | Tests whether the watched process is gone. Linux shows a folder `/proc/PID` for each process that exists. This test uses the real `/proc`, not the prefix of `--root`. |
| 294 | `                    reason = "pid_gone"` | Then `reason` becomes `pid_gone`. |
| 295 | `                    break` | Leaves the loop. |
| 296 | `                if mono() - start >= a.max_s * 1e9:` | Tests whether the time from `start` until now has reached the time limit `--max-s`. |
| 297 | `                    reason = "max_s"` | Then `reason` becomes `max_s`. |
| 298 | `                    break` | Leaves the loop. |
| 299 | `                slot += 1` | Goes to the next time slot. |
| 300 | `                late = (mono() - start) // period` | `late`: the number of whole periods that have passed after `start`. |
| 301 | `                if late >= slot:                  # a sample ran longer than one period: skip the lost slots` | Tests whether the start time of the next slot has already passed. Comment: a sample ran longer than one period, so the lost slots are skipped. |
| 302 | `                    missed += late - slot + 1` | Then: adds the number of lost slots to `missed`. |
| 303 | `                    slot = late + 1` | The next sample uses the first slot that has not started yet. |
| 304 | `                time.sleep(max(0.0, (start + slot * period - mono()) / 1e9))` | Sleeps until the start time of the slot, which is `start` plus `slot` periods. The start times depend on `start` only. So a late sample does not move the later samples. `max(0.0, ...)` avoids a negative sleep time. |
| 305 | `        except Stop:` | Catches `Stop`: a signal SIGTERM or SIGINT arrived inside the loop. |
| 306 | `            reason = "signal"` | Then `reason` becomes `signal`. |
| 307 | `        out.write("# end reason=%s %s samples=%d na=%d missed=%d max_sample_us=%.0f\n"` | Writes the footer: `# end`, the reason, the three clocks, and four numbers. The statement continues in line 308. |
| 308 | `                  % (reason, clocks(), samples, nas, missed, worst / 1e3))` | The four numbers: the samples written, the `na` values, the skipped slots, and `max_sample_us`, the longest duration of one sample in microseconds. |
| 309 | `    return 0 if reason != "error" else 1` | Returns exit status 0 unless `reason` is still `error`. Every way out of the loop sets another reason. So the function returns 0 whenever it reaches this line. |

### Report: the helpers `kv` and `num` (lines 312 to 322)

| Line | Source | Explanation |
|---:|---|---|
| 312 | `# ----------------------------------------------------------------------------- report` | Comment: a divider. The functions of the command `report` follow. |
| 314 | `def kv(line):` | Starts the function `kv`. It reads the `key=value` parts of one line. |
| 315 | `    return dict(p.split("=", 1) for p in line.split() if "=" in p)` | Splits the line at white space, keeps the parts that hold `=`, and splits each at its first `=`. It returns a dictionary from the key to the value. Both are text. Example: the line `# end mono_ns=5 took_ms=1.2` gives `mono_ns` with `5` and `took_ms` with `1.2`. |
| 318 | `def num(text):` | Starts the function `num`. It turns a text into a whole number. |
| 319 | `    """int or None for a missing value or a "!NAME" value."""` | Docstring: the function returns an integer, or `None` for a missing value or a `!NAME` value. |
| 320 | `    return int(text) if text is not None and re.match(r"^-?\d+$", text) else None` | The pattern accepts an optional minus sign and then digits only. Every other text, and `None`, gives `None`. |

### Function `read_snap`: read a snapshot file or a probe file (lines 323 to 348)

| Line | Source | Explanation |
|---:|---|---|
| 323 | `def read_snap(path):` | Starts the function `read_snap`. It reads a file that `snap` or `probe` wrote and returns its content as a dictionary. |
| 324 | `    """{"head": {...}, "end": {...}, "cpu": {n: {key: text}}, "s": {path: text}} of a snap or probe file."""` | Docstring: it names four keys of the result: `head`, `end`, `cpu` and `s`. The dictionary of line 325 has three more: `f`, `l` and `complete`. |
| 325 | `    d = {"head": {}, "end": {}, "cpu": {}, "s": {}, "f": {}, "l": {}, "complete": False}` | `d`: the result. `head`: the values of the header lines. `end`: the values of the footer. `cpu`: per CPU number, the values of its `cpu` line. `s`: per path, the value of a system file or sensor file. `f`: per CPU number, the files of the probe. `l`: per folder, its entry names. `complete`: `False` until a footer is found. |
| 326 | `    with open(path) as fh:` | Opens the file. |
| 327 | `        for line in fh:` | Starts a loop over its lines. |
| 328 | `            line = line.rstrip("\n")` | Removes the line break at the end. |
| 329 | `            if line.startswith("# end "):` | A line that starts with `# end` is the footer. |
| 330 | `                d["end"] = kv(line)` | `end`: the `key=value` parts of the footer, for example `mono_ns`, `took_ms` and `unreadable`. |
| 331 | `                d["complete"] = True` | `complete` becomes `True`: the file was written to its end. |
| 332 | `            elif line.startswith("#"):` | Every other line that starts with `#` is a header line. |
| 333 | `                d["head"].update(kv(line))` | Adds the `key=value` parts of the line to `head`. So `head` holds the label, the CPU list and the three clocks of the start. |
| 334 | `            elif line.startswith("cpu "):` | A line that starts with `cpu` and a space. |
| 335 | `                p = line.split(" ", 2)` | Splits the line at its first two spaces: the word `cpu`, the CPU number and the rest. |
| 336 | `                d["cpu"][int(p[1])] = kv(p[2])` | Stores the `key=value` parts of the rest under the CPU number. |
| 337 | `            elif line.startswith("s "):` | An `s` line. |
| 338 | `                p = line.split(" ", 2)` | Splits the line at its first two spaces: the letter, the path and the value. The value may hold spaces. |
| 339 | `                d["s"][p[1]] = p[2] if len(p) > 2 else ""` | Stores the value under the path. A line without a value gives an empty text. |
| 340 | `            elif line.startswith("f "):` | An `f` line. |
| 341 | `                p = line.split(" ", 3)` | Splits the line at its first three spaces: the letter, the CPU number, the path and the value. |
| 342 | `                d["f"].setdefault(int(p[1]), {})[p[2]] = p[3] if len(p) > 3 else ""` | Stores the value under the CPU number and the path. `setdefault` creates the inner dictionary of a CPU at its first line. |
| 343 | `            elif line.startswith("l "):` | An `l` line. |
| 344 | `                p = line.split(" ", 2)` | Splits the line at its first two spaces: the letter, the folder and the names. |
| 345 | `                d["l"][p[1]] = p[2] if len(p) > 2 else ""` | Stores the names under the folder. |
| 346 | `    return d` | Returns the dictionary. |

### Function `read_watch`: read the file of the sampler (lines 349 to 364)

| Line | Source | Explanation |
|---:|---|---|
| 349 | `def read_watch(path):` | Starts the function `read_watch`. It reads a file that the sampler wrote. |
| 350 | `    """(CPU list of the file, [(t_mono_ns, [kHz or None, ...])], footer dict)."""` | Docstring: the function returns three things: the CPU list of the file, a list of rows, and the footer as a dictionary. Each row holds the time in ns and one value per CPU, in kHz or `None`. |
| 351 | `    cpus, rows, end = [], [], {}` | The three results start empty. |
| 352 | `    with open(path) as fh:` | Opens the file. |
| 353 | `        for line in fh:` | Starts a loop over its lines. |
| 354 | `            if line.startswith("# hwwatch"):` | The first header line starts with `# hwwatch`. |
| 355 | `                cpus = parse_cpus(kv(line)["cpus"])` | `cpus`: the CPU numbers of its `cpus=` part. They give the meaning of the columns. |
| 356 | `            elif line.startswith("# end "):` | The footer starts with `# end`. |
| 357 | `                end = kv(line)` | `end`: its `key=value` parts, for example `reason`, `samples`, `na` and `missed`. |
| 358 | `            elif not line.startswith("#"):` | Every line that does not start with `#` is a sample. |
| 359 | `                p = line.split()` | Splits the line at white space. |
| 360 | `                if len(p) == len(cpus) + 1:           # a line that was cut by a kill has fewer fields` | Takes the line only when it has one field for the time and one field per CPU. Comment: a line that was cut when the sampler was killed has fewer fields. |
| 361 | `                    rows.append((int(p[0]), [int(v) if v.isdigit() else None for v in p[1:]]))` | Adds the row: the time as an integer, and a list with one entry per CPU. An entry is an integer in kHz, or `None` for `na`. |
| 362 | `    return cpus, rows, end` | Returns the three results. |

### Function `perf_to_khz`: from a performance value to kHz (lines 365 to 384)

| Line | Source | Explanation |
|---:|---|---|
| 365 | `def perf_to_khz(perf, caps, max_khz, boost):` | Starts the function `perf_to_khz`. `perf` is a performance value on the scale of the firmware table. `caps` holds the values of the folder `acpi_cppc` of one CPU. `max_khz` is its `cpuinfo_max_freq`. `boost` says whether boost is on. |
| 366 | `    """kHz for a performance value, and the name of the conversion.` | Docstring: the function returns the kHz value for a performance value, and the name of the conversion rule. |
| 367 | `    "linear": the line through (lowest_perf, lowest_freq) and (nominal_perf, nominal_freq), as the function` | Docstring: the rule `linear` uses the straight line through two points: (`lowest_perf`, `lowest_freq`) and (`nominal_perf`, `nominal_freq`). The sentence goes on in line 368. |
| 368 | `    cppc_perf_to_khz of the Linux file drivers/acpi/cppc_acpi.c computes it.` | Docstring: the function `cppc_perf_to_khz` in the file `drivers/acpi/cppc_acpi.c` of Linux computes the value in the same way. |
| 369 | `    "max": cpuinfo_max_freq * perf / (the performance value that cpuinfo_max_freq stands for), used when the two` | Docstring: the rule `max` computes `cpuinfo_max_freq` times `perf`, divided by the performance value that `cpuinfo_max_freq` stands for. It is used when the two frequencies are not reported. The sentence goes on in line 370. |
| 370 | `    frequencies are not reported. "none": no conversion possible."""` | Docstring: the rule `none` means that no conversion is possible. The three quotation marks end the docstring. |
| 371 | `    lf, nf = caps.get("lowest_freq"), caps.get("nominal_freq")` | `lf` and `nf`: the values of the files `lowest_freq` and `nominal_freq`. By the Linux document they are the frequencies that belong to `lowest_perf` and `nominal_perf`, in MHz [Ref2]. |
| 372 | `    lp, npf, hp = caps.get("lowest_perf"), caps.get("nominal_perf"), caps.get("highest_perf")` | `lp`, `npf` and `hp`: the values of `lowest_perf`, `nominal_perf` and `highest_perf`. They are performance values on an abstract scale without a unit [Ref2]. |
| 373 | `    if lf and nf and npf:` | The rule `linear` needs both frequencies and the nominal performance. Each must be present and not 0. |
| 374 | `        if lf == nf or lp is None or npf == lp:` | Tests three special cases: both frequencies are equal, `lowest_perf` is missing, or both performance values are equal. In these cases the two points give no slope. |
| 375 | `            mul, div = nf * 1000.0, float(npf)` | Then the line goes through zero and the nominal point. `mul` is the nominal frequency in kHz (MHz times 1000) and `div` is the nominal performance. |
| 376 | `        else:` | In the normal case line 377 runs. |
| 377 | `            mul, div = (nf - lf) * 1000.0, float(npf - lp)` | `mul`: the difference of the two frequencies in kHz. `div`: the difference of the two performance values. `mul` divided by `div` is the slope of the line, in kHz per performance unit. |
| 378 | `        return nf * 1000.0 - npf * mul / div + perf * mul / div, "linear"` | Returns the kHz value and the name `linear`. The value is the nominal frequency in kHz, minus the nominal performance times the slope, plus `perf` times the slope. So a `perf` equal to `nominal_perf` gives exactly `nominal_freq`. |
| 379 | `    top = hp if boost else npf` | The rule `max`. `top`: the performance value that `cpuinfo_max_freq` stands for. It is `highest_perf` when boost is on. If not, it is `nominal_perf`. |
| 380 | `    if max_khz and top:` | The rule needs `cpuinfo_max_freq` and `top`. Both must be present and not 0. |
| 381 | `        return max_khz * perf / float(top), "max"` | Returns `cpuinfo_max_freq` times `perf` divided by `top`, and the name `max`. |
| 382 | `    return None, "none"` | No rule can be used: returns `None` and the name `none`. |

### Functions `read_atx_summary` and `stats3` (lines 385 to 424)

| Line | Source | Explanation |
|---:|---|---|
| 385 | `def read_atx_summary(path):` | Starts the function `read_atx_summary`. It reads the summary file of `atx` and returns one dictionary per data row. |
| 386 | `    """[{"metric", "unit", "target", "min", "max", "avg", "twa", "count"}] of the summary file of atx.` | Docstring: the keys of a row: `metric`, `unit`, `target`, `min`, `max`, `avg`, `twa` (the time weighted average) and `count`. |
| 387 | `    Layout: a line "Metric: NAME - TEXT (UNIT)", a header line that starts with "Target," and holds "Min",` | Docstring: the layout of the file. A line `Metric: NAME - TEXT (UNIT)` starts a metric. A header line follows that starts with `Target,` and holds `Min`. The sentence goes on in line 388. |
| 388 | `    then one line per target. A table whose header holds "Type" (the histogram) is skipped."""` | Docstring: then one line per target follows. A table whose header holds `Type` is the histogram, and it is skipped. The quotation marks end the docstring. |
| 389 | `    rows, metric, unit, cols = [], None, "", None` | `rows`: the result. `metric` and `unit`: the metric that is open now. `cols`: the column names of the open table, or `None` when no table is open. |
| 390 | `    with open(path, errors="replace") as fh:` | Opens the file. `errors="replace"`: a byte that is not valid text is replaced and does not stop the read. |
| 391 | `        for raw in fh:` | Starts a loop over the lines. |
| 392 | `            line = raw.strip()` | `line`: the line without white space at both ends. |
| 393 | `            if line.startswith("Metric:"):` | A line that starts with `Metric:` opens a new metric. |
| 394 | `                text = line[len("Metric:"):].strip()` | `text`: the rest of the line after `Metric:`. |
| 395 | `                metric = text.split(" - ", 1)[0].strip()` | `metric`: the part before the first ` - ` (a hyphen with a space at each side), for example `vcpu-c0-power`. |
| 396 | `                m = re.search(r"\(([^()]*)\)\s*$", text)` | The pattern finds a pair of parentheses at the end of the text. Only white space may follow the pair. Group 1 holds the text between the parentheses. That text holds no parenthesis. |
| 397 | `                unit = m.group(1) if m else ""` | `unit`: group 1, for example `W`. It is an empty text when the line has no such pair. |
| 398 | `                cols = None` | `cols` becomes `None`: the table of the new metric has no header yet. |
| 399 | `            elif line.startswith("Target,"):` | A line that starts with `Target,` is the header of a table. |
| 400 | `                names = [re.sub(r"[^a-z]", "", c.lower()) for c in line.split(",")]` | `names`: the column names in small letters, without every character that is not a letter from a to z. So `Time Weighted Average` becomes `timeweightedaverage`. |
| 401 | `                cols = names if "min" in names else None` | The table is used only when it has a column `min`. The header of the histogram has none. Then `cols` becomes `None`, and the rows of the histogram are skipped. |
| 402 | `            elif not line or "," not in line:` | An empty line, or a line without a comma. |
| 403 | `                cols = None` | Such a line ends the open table. |
| 404 | `            elif cols and metric:` | Every other line is a data row when a table and a metric are open. |
| 405 | `                p = line.split(",")` | `p`: the fields of the row, split at the commas. |
| 406 | `                if len(p) != len(cols):` | Tests whether the row has another number of fields than the header. |
| 407 | `                    continue` | Then the row is skipped. |
| 408 | `                d = dict(zip(cols, p))` | `d`: a dictionary from each column name to the field of this row. |
| 410 | `                def fl(key):` | Starts the inner function `fl`. It returns the field of one column as a floating-point number. |
| 411 | `                    try:` | Starts the block whose errors line 413 handles. |
| 412 | `                        return float(d[key])` | Returns the number. |
| 413 | `                    except (KeyError, ValueError):` | The column does not exist, or the field is not a number. |
| 414 | `                        return None` | Then `fl` returns `None`. |
| 415 | `                rows.append(dict(metric=metric, unit=unit, target=d.get("target", ""), min=fl("min"), max=fl("max"),` | Adds the row to the result: the metric, the unit, the column `Target`, and the columns `Min` and `Max` as numbers. The call continues in line 416. |
| 416 | `                                 avg=fl("average"), twa=fl("timeweightedaverage") if "timeweightedaverage" in d` | Continues the call: `avg` is the column `Average`. `twa` is the column `Time Weighted Average` when the header has that name. The expression continues in line 417. |
| 417 | `                                 else fl("timeweightedavg"), count=fl("count")))` | Continues the call: if not, `twa` is the column `TimeWeightedAvg`. So both spellings of this header are read. `count` is the column `Count`. |
| 418 | `    return rows` | Returns the rows. |
| 421 | `def stats3(values):` | Starts the function `stats3`. It returns three values of a list of numbers. |
| 422 | `    return (min(values), statistics.median(values), max(values)) if values else (None, None, None)` | Returns the lowest value, the median and the highest value. An empty list gives three times `None`. |

### Function `report_folder`: the status file, the probe and the samples (lines 425 to 454)

| Line | Source | Explanation |
|---:|---|---|
| 425 | `def report_folder(folder, tol):` | Starts the function `report_folder`. It reads the hardware record of one result folder and returns the facts as a dictionary. `tol` is the tolerance of the limit (0.01 by default). |
| 426 | `    """The facts of one result folder as a dict. Nothing is estimated: a value that the files do not give is None."""` | Docstring: the function returns the facts of one result folder as a dictionary. It estimates nothing: a value that the files do not give is `None`. |
| 427 | `    hw = os.path.join(folder, "hw")` | `hw`: the folder `hw` inside the result folder. |
| 428 | `    res = {"folder": folder, "notes": [], "processes": [], "atx": None, "status": []}` | `res`: the result. `notes`: remarks about missing files. `processes`: one entry per process. `atx`: the rows of the summary of `atx`. `status`: the lines of `status.txt`. |
| 429 | `    if not os.path.isdir(hw):` | Tests whether the folder `hw` is missing. |
| 430 | `        res["notes"].append("no folder hw: this run has no hardware record")` | Then: adds the note that this run has no hardware record. |
| 431 | `        return res` | Returns the result with this one note. |
| 432 | `    st = os.path.join(hw, "status.txt")` | `st`: the path of `status.txt`, the file to which `hw.sh` writes its `ok` and `FAILED` lines. |
| 433 | `    if os.path.isfile(st):` | Tests whether the file exists. |
| 434 | `        res["status"] = [l.rstrip("\n") for l in open(st)]` | Then: `res["status"]` gets its lines without the line breaks. |
| 435 | `    caps, max_khz, boost = {}, {}, False` | `caps`: per CPU, the values of its folder `acpi_cppc`. `max_khz`: per CPU, its highest frequency in kHz. `boost`: `False` unless the probe says that boost is on. |
| 436 | `    pp = os.path.join(hw, "probe.txt")` | `pp`: the path of `probe.txt`. |
| 437 | `    if os.path.isfile(pp):` | Tests whether the file exists. |
| 438 | `        probe = read_snap(pp)` | `probe`: the content of the probe. |
| 439 | `        boost = probe["s"].get(CPU_DIR + "/cpufreq/boost") == "1"` | `boost` becomes `True` when the system file `cpufreq/boost` held `1` in the probe. |
| 440 | `        for cpu, files in probe["f"].items():` | Starts a loop over the CPUs of the probe and their `f` lines. |
| 441 | `            caps[cpu] = {k.split("/")[-1]: num(v) for k, v in files.items() if k.startswith("acpi_cppc/")}` | `caps` of the CPU: a dictionary for the files of `acpi_cppc`, from the file name without its folder to the value as an integer. Examples of names: `reference_perf`, `nominal_perf`, `nominal_freq`. A value that is not a whole number becomes `None`. |
| 442 | `            max_khz[cpu] = num(files.get("cpufreq/cpuinfo_max_freq"))` | `max_khz` of the CPU: the value of `cpufreq/cpuinfo_max_freq`, the highest frequency at which the CPU can run, in kHz [Ref1]. |
| 443 | `        res["probe"] = {"took_ms": probe["end"].get("took_ms"), "listed": probe["l"], "complete": probe["complete"]}` | Keeps three facts about the probe in the result: its duration in ms, the listed folders, and whether the file is complete. |
| 444 | `    else:` | If `probe.txt` is missing, line 445 runs. |
| 445 | `        res["notes"].append("no probe.txt: rates cannot be converted to kHz")` | Adds the note that rates cannot be converted to kHz. |
| 446 | `    wcpus, wrows, wend = [], [], {}` | `wcpus`, `wrows` and `wend`: the CPU list, the rows and the footer of the sampler file. They start empty. |
| 447 | `    wp = os.path.join(hw, "watch.txt")` | `wp`: the path of `watch.txt`. |
| 448 | `    if os.path.isfile(wp):` | Tests whether the file exists. |
| 449 | `        wcpus, wrows, wend = read_watch(wp)` | Then: reads the file with `read_watch`. |
| 450 | `        res["watch"] = {"samples": len(wrows), "end": wend}` | Keeps the number of sample rows and the footer in the result. |
| 451 | `        if not wend:` | Tests whether the footer is missing. |
| 452 | `            res["notes"].append("watch.txt has no end line: the sampler was killed or is still running")` | Then: adds the note that the sampler was killed or is still running. |
| 453 | `    else:` | If `watch.txt` is missing, line 454 runs. |
| 454 | `        res["notes"].append("no watch.txt: no sampled rates")` | Adds the note that there are no sampled rates. |

### Function `report_folder`: the two snapshots and the window of one process (lines 455 to 476)

| Line | Source | Explanation |
|---:|---|---|
| 455 | `    for before in sorted(glob.glob(os.path.join(hw, "*.before.txt"))):` | Starts the loop over the processes. Each file in the folder `hw` whose name ends with `.before.txt` stands for one process. The names start with the 3-digit number of the process. So the sorted order is the order in which the processes ran. |
| 456 | `        name = os.path.basename(before)[:-len(".before.txt")]` | `name`: the file name without `.before.txt`, for example `001-p`. |
| 457 | `        p = {"name": name, "flags": []}` | `p`: the entry of this process, with its name and an empty list of flags. |
| 458 | `        res["processes"].append(p)` | Adds the entry to the result. |
| 459 | `        b = read_snap(before)` | `b`: the content of the snapshot before the process. |
| 460 | `        after = before[:-len(".before.txt")] + ".after.txt"` | `after`: the path of the snapshot after the process. It is the same name with `.after.txt` at its end. |
| 461 | `        if not os.path.isfile(after):` | Tests whether that file is missing. |
| 462 | `            p["flags"].append("NO_AFTER")` | Then: the process gets the flag `NO_AFTER`. |
| 463 | `            continue` | Goes on with the next process. This entry holds no other value. |
| 464 | `        a = read_snap(after)` | `a`: the content of the snapshot after the process. |
| 465 | `        if not (b["complete"] and a["complete"]):` | Tests whether one of the two files has no footer. |
| 466 | `            p["flags"].append("CUT_FILE")` | Then: the process gets the flag `CUT_FILE`. The values that the files hold are still used. |
| 467 | `        cpus = sorted(set(b["cpu"]) & set(a["cpu"]))` | `cpus`: the CPUs that both snapshots hold, sorted. |
| 468 | `        p["cpus"] = len(cpus)` | `p["cpus"]`: their number. |
| 469 | `        t0, t1 = num(b["end"].get("mono_ns")), num(a["head"].get("mono_ns"))` | `t0`: `mono_ns` in the footer of the first snapshot, the end of that snapshot. `t1`: `mono_ns` in the header of the second snapshot, the start of that snapshot. Both are readings of `CLOCK_MONOTONIC` in ns. |
| 470 | `        p["seconds"] = (t1 - t0) / 1e9 if t0 is not None and t1 is not None else None` | `p["seconds"]`: the window of the process in seconds: `t1` minus `t0`, divided by 1e9. It is `None` when a time is missing. The benchmark process runs inside this window. The window also holds what the run script does between `hw_begin` and the launch, and between the end of the process and `hw_end`. |
| 471 | `        t2 = num(a["end"].get("mono_ns"))                # the sensor files are read at the end of each snapshot` | `t2`: `mono_ns` in the footer of the second snapshot. Comment: the sensor files are read at the end of each snapshot. |
| 472 | `        p["sensor_seconds"] = (t2 - t0) / 1e9 if t0 is not None and t2 is not None else None` | `p["sensor_seconds"]`: the time from the end of the first snapshot to the end of the second, in seconds. The average power of an energy counter uses this time (lines 591 to 593). |
| 473 | `        p["snap_ms"] = [float(x["end"]["took_ms"]) for x in (b, a) if "took_ms" in x["end"]]` | `p["snap_ms"]`: the durations of the two snapshots in ms, taken from `took_ms` of their footers. |
| 474 | `        khz, ratio, conv = {}, {}, set()` | `khz`: per CPU, the clock rate from the counters. `ratio`: per CPU, the counter ratio. `conv`: the set of the conversion rules that were used. |
| 475 | `        top = {c: max_khz[c] for c in cpus if max_khz.get(c)}` | `top`: per CPU of the process, its `cpuinfo_max_freq` in kHz. A CPU without that value is left out. |
| 476 | `        low = {c: (1 - tol) * top[c] for c in top}       # per CPU: the rate below which a value is flagged` | `low`: per CPU, the limit. It is `top` times (1 minus `tol`). With the default 0.01 this is 99 % of `cpuinfo_max_freq`. Comment: a value below this rate is flagged. A CPU without a `cpuinfo_max_freq` in the probe has no limit. So no value of such a CPU is flagged as low. |

### Function `report_folder`: the clock rate of each core from its two counters (lines 477 to 499)

| Line | Source | Explanation |
|---:|---|---|
| 477 | `        for c in cpus:` | Starts a loop over the CPUs of the process. |
| 478 | `            r0, r1, d0, d1 = (num(b["cpu"][c].get("ref")), num(a["cpu"][c].get("ref")),` | `r0` and `r1`: the counter `ref` of this CPU in the first and in the second snapshot. The statement continues in line 479. |
| 479 | `                              num(b["cpu"][c].get("del")), num(a["cpu"][c].get("del")))` | `d0` and `d1`: the counter `del` in the first and in the second snapshot. `num` gives `None` for a value that could not be read. |
| 480 | `            if None in (r0, r1, d0, d1) or r1 <= r0 or d1 < d0:` | Tests three cases in which the CPU is skipped: a counter is missing, `ref` did not advance, or `del` went backwards. |
| 481 | `                continue` | Then: goes on with the next CPU. This CPU gets no ratio and no rate. |
| 482 | `            ratio[c] = (d1 - d0) / (r1 - r0)` | `ratio` of the CPU: the change of `del` divided by the change of `ref` between the two snapshots. This is the rule of line 21. A ratio of 1 gives a delivered performance equal to `reference_perf`. No clock time enters the ratio. |
| 483 | `            cap = caps.get(c, {})` | `cap`: the values of `acpi_cppc` of this CPU from the probe, or an empty dictionary. |
| 484 | `            if cap.get("reference_perf"):` | The conversion needs `reference_perf`. It must be present and not 0. |
| 485 | `                k, how = perf_to_khz(cap["reference_perf"] * ratio[c], cap, max_khz.get(c), boost)` | Delivered performance = `reference_perf` times the ratio. `perf_to_khz` turns it into kHz and names the rule (lines 365 to 382). |
| 486 | `                conv.add(how)` | Remembers the name of the rule. |
| 487 | `                if k is not None:` | Tests whether a kHz value was found. |
| 488 | `                    khz[c] = k` | Then: stores it as the clock rate of this CPU. By the rule of the Linux document, it is the average rate between the two counter reads of the CPU [Ref2]. Time in which the two counters do not count does not enter this average. By the design note, that can be the time in which the core is idle [Ref7]. |
| 489 | `        p["counter_cpus"] = len(ratio)` | `p["counter_cpus"]`: the number of CPUs that have a ratio. |
| 490 | `        p["ratio"] = stats3(list(ratio.values()))` | `p["ratio"]`: the lowest, the median and the highest ratio of the CPUs. |
| 491 | `        p["avg_khz"] = stats3(list(khz.values()))` | `p["avg_khz"]`: the lowest, the median and the highest clock rate of the CPUs, in kHz. |
| 492 | `        p["avg_khz_min_cpu"] = min(khz, key=khz.get) if khz else None` | `p["avg_khz_min_cpu"]`: the number of the CPU with the lowest clock rate, or `None`. |
| 493 | `        p["conversion"] = sorted(conv)` | `p["conversion"]`: the names of the rules that were used, sorted. |
| 494 | `        p["max_khz"] = max(top.values()) if top else None` | `p["max_khz"]`: the highest `cpuinfo_max_freq` of the CPUs of the process, or `None`. |
| 495 | `        if not ratio:` | Tests whether no CPU has a ratio. |
| 496 | `            p["flags"].append("NO_COUNTERS")` | Then: the process gets the flag `NO_COUNTERS`. |
| 497 | `        p["low_avg_cpus"] = sorted(c for c in khz if c in low and khz[c] < low[c])` | `p["low_avg_cpus"]`: the CPUs whose clock rate from the counters is below their limit, sorted. |
| 498 | `        if p["low_avg_cpus"]:` | Tests whether there is such a CPU. |
| 499 | `            p["flags"].append("LOW_AVG")` | Then: the process gets the flag `LOW_AVG`. |

### Function `report_folder`: the sampled rates inside the window (lines 500 to 520)

| Line | Source | Explanation |
|---:|---|---|
| 500 | `        # sampled rates between the two snapshots, for the CPUs of this process` | Comment: the next block takes the sampled rates between the two snapshots, for the CPUs of this process. |
| 501 | `        idx = [(wcpus.index(c), c) for c in cpus if c in wcpus]` | `idx`: a list of pairs for the CPUs of the process that the sampler also read. Each pair holds the column of the CPU in a sample row, and the CPU number. |
| 502 | `        vals, na, nlow = [], 0, 0` | `vals`: the sampled values. `na`: the count of missing values. `nlow`: the count of values below the limit. |
| 503 | `        if t0 is not None and t1 is not None:` | The samples are used only when both times of the window are known. |
| 504 | `            for t, row in wrows:` | Starts a loop over the sample rows: the time stamp `t` and the values of the row. |
| 505 | `                if t0 <= t <= t1:` | Takes a row only when its time stamp lies inside the window, both ends included. The time stamp of a sample is read before its files (line 278). |
| 506 | `                    for i, c in idx:` | Starts a loop over the CPUs of the process. |
| 507 | `                        if row[i] is None:` | Tests whether the row has no value for this CPU. |
| 508 | `                            na += 1` | Then: adds 1 to `na`. |
| 509 | `                        else:` | If the row has a value, lines 510 to 511 run. |
| 510 | `                            vals.append(row[i])` | Adds the value, in kHz, to `vals`. |
| 511 | `                            nlow += 1 if c in low and row[i] < low[c] else 0` | Adds 1 to `nlow` when the value is below the limit of this CPU. |
| 512 | `        p["samples"] = len(vals)` | `p["samples"]`: the number of sampled values, over all CPUs of the process and all rows of the window. |
| 513 | `        p["samples_na"] = na` | `p["samples_na"]`: the number of missing values. |
| 514 | `        p["sample_khz"] = stats3(vals)` | `p["sample_khz"]`: the lowest, the median and the highest sampled value in kHz. |
| 515 | `        p["samples_low"] = nlow` | `p["samples_low"]`: the number of sampled values below the limit. |
| 516 | `        if not vals:` | Tests whether there is no sampled value. |
| 517 | `            p["flags"].append("NO_SAMPLES")` | Then: the process gets the flag `NO_SAMPLES`. |
| 518 | `        elif p["samples_low"]:` | If not: tests whether a value was below the limit. |
| 519 | `            p["flags"].append("LOW_SAMPLE")` | Then: the process gets the flag `LOW_SAMPLE`. |

### Function `report_folder`: the limits of Linux, the throttle flag, energy and `atx` (lines 521 to 554)

| Line | Source | Explanation |
|---:|---|---|
| 521 | `        for key, flag in (("scaling_max_freq", "LIMIT_LOWERED"), ("scaling_cur_freq", "REQUEST_BELOW_MAX")):` | Starts a loop over two files and their flags. `scaling_max_freq` belongs to the flag `LIMIT_LOWERED`. `scaling_cur_freq` belongs to the flag `REQUEST_BELOW_MAX`. |
| 522 | `            seen = [(num(snap["cpu"][c].get(key)), c) for snap in (b, a) for c in cpus if num(snap["cpu"][c].get(key)) is not None]` | `seen`: a list of pairs, the value and the CPU, for both snapshots and all CPUs of the process. A value that could not be read is left out. |
| 523 | `            p[key + "_min"] = min(v for v, _ in seen) if seen else None` | Stores the lowest of these values under the name of the file with `_min` at its end, for example `scaling_cur_freq_min`. It is `None` when there is no value. |
| 524 | `            if any(c in top and v < top[c] for v, c in seen):` | Tests whether any value is below the `cpuinfo_max_freq` of its CPU. |
| 525 | `                p["flags"].append(flag)` | Then: the process gets the flag of this file. |
| 526 | `        lim_b = {c: num(b["cpu"][c].get("perf_limited")) for c in cpus}` | `lim_b`: per CPU, the throttle flag `perf_limited` in the first snapshot, as a number or `None`. |
| 527 | `        lim_a = {c: num(a["cpu"][c].get("perf_limited")) for c in cpus}` | `lim_a`: the same for the second snapshot. |
| 528 | `        p["perf_limited_readable"] = sum(1 for c in cpus if lim_b[c] is not None and lim_a[c] is not None)` | `p["perf_limited_readable"]`: the number of CPUs whose flag was readable in both snapshots. |
| 529 | `        p["perf_limited_set_during"] = sum(1 for c in cpus if lim_b[c] == 0 and lim_a[c])` | `p["perf_limited_set_during"]`: the number of CPUs whose flag was 0 before the process and not 0 after it. The flag is read at the two snapshots only. |
| 530 | `        p["perf_limited_set_before"] = sum(1 for c in cpus if lim_b[c])` | `p["perf_limited_set_before"]`: the number of CPUs whose flag was not 0 before the process. |
| 531 | `        if p["perf_limited_set_during"]:` | Tests whether a flag was set during the process. |
| 532 | `            p["flags"].append("PERF_LIMITED")` | Then: the process gets the flag `PERF_LIMITED`. |
| 533 | `        if p["perf_limited_set_before"]:` | Tests whether a flag was set before the process. |
| 534 | `            p["flags"].append("PERF_LIMITED_ALREADY_SET")` | Then: the process gets the flag `PERF_LIMITED_ALREADY_SET`. For such a CPU the run cannot show a new event. |
| 535 | `        if not p["perf_limited_readable"]:` | Tests whether no CPU had a readable flag. |
| 536 | `            p["flags"].append("NO_THROTTLE_FLAG")` | Then: the process gets the flag `NO_THROTTLE_FLAG`. |
| 537 | `        for key, flag in ((CPU_DIR + "/online", "ONLINE_CHANGED"), ("/proc/sys/kernel/random/boot_id", "BOOT_CHANGED")):` | Starts a loop over two system files and their flags. The list of online CPUs belongs to `ONLINE_CHANGED`. The boot id belongs to `BOOT_CHANGED`. |
| 538 | `            if b["s"].get(key) != a["s"].get(key):` | Tests whether the value in the first snapshot differs from the value in the second. |
| 539 | `                p["flags"].append(flag)` | Then: the process gets the flag. |
| 540 | `        # sensor files that hold a counter of energy: the change between the two snapshots` | Comment: some sensor files hold a counter of energy. The next block computes its change between the two snapshots. |
| 541 | `        p["energy"] = {}` | `p["energy"]`: per sensor file, the change of the counter. It starts empty. |
| 542 | `        for key, v0 in b["s"].items():` | Starts a loop over the `s` lines of the first snapshot: the path and the value. |
| 543 | `            if re.search(r"/(energy_uj\|energy\d+_input)$", key) and num(v0) is not None and num(a["s"].get(key)) is not None:` | Takes a path that ends with `/energy_uj`, or with `/energy`, digits and `_input`. Group 1 of the pattern holds that file name. Both values, before and after, must be whole numbers. |
| 544 | `                p["energy"][key] = num(a["s"][key]) - num(v0)` | Stores the value after the process minus the value before it. A counter that started again from a lower value would give a negative number. The code does not correct that. |
| 545 | `    ap = os.path.join(hw, "atx", "atx_summary.csv")` | `ap`: the path of the summary file of `atx`: `atx_summary.csv` in the folder `atx` of the record. |
| 546 | `    if os.path.isfile(ap):` | Tests whether the file exists. |
| 547 | `        res["atx"] = read_atx_summary(ap)` | Then: `res["atx"]` gets the rows that `read_atx_summary` returns. |
| 548 | `        if not res["atx"]:` | Tests whether there is no row. |
| 549 | `            res["notes"].append("atx_summary.csv holds no table that this script can read")` | Then: adds the note that the file holds no table that this script can read. |
| 550 | `    else:` | If the file is missing, line 551 runs. |
| 551 | `        res["notes"].append("no atx_summary.csv: no power, temperature or firmware frequency values")` | Adds the note that there are no power, temperature or firmware frequency values. |
| 552 | `    return res` | Returns the result. |

### Functions `fmt` and `print_report`: the table of the processes (lines 555 to 593)

| Line | Source | Explanation |
|---:|---|---|
| 555 | `def fmt(v, digits=0):` | Starts the function `fmt`. It turns a number into text for the report. `digits` is the number of decimals (0 by default). |
| 556 | `    return "-" if v is None else ("%.*f" % (digits, v))` | Returns `-` for `None`. If not, it returns the number with `digits` decimals. |
| 559 | `def print_report(res, tol):` | Starts the function `print_report`. It prints the facts of one result folder as text. |
| 560 | `    print("== %s" % res["folder"])` | Prints `==` and the path of the result folder. |
| 561 | `    for n in res["notes"]:` | Starts a loop over the notes. |
| 562 | `        print("   note: %s" % n)` | Prints each note after the word `note:`. |
| 563 | `    bad = [s for s in res["status"] if s.startswith("FAILED")]` | `bad`: the lines of `status.txt` that start with `FAILED`. |
| 564 | `    for s in bad:` | Starts a loop over these lines. |
| 565 | `        print("   status: %s" % s)` | Prints each one after the word `status:`. |
| 566 | `    if res["processes"]:` | The table is printed only when the folder has a process. |
| 567 | `        print("   One row per process. window s: the time between its two snapshots (in rx.sh it holds the 5 s pause before the launch).")` | Prints the first of five lines that explain the table. One row stands for one process. `window s` is the time between its two snapshots. In `rx.sh` this window holds the pause of 5 s before the launch. |
| 568 | `        print("   counters: the clock rate of each core from its two counters, for the lowest, the median and the highest core,")` | The second of the five lines: the columns under `counters` give the clock rate of each core from its two counters, for the lowest, the median and the highest core. |
| 569 | `        print("   the number of the lowest core, and the median of (change of del) / (change of ref).")` | The third: they also give the number of the lowest core, and the median of (change of `del`) divided by (change of `ref`). |
| 570 | `        print("   sampled: the cpuinfo_avg_freq samples of the same cores inside the window. low: samples below the limit.")` | The fourth: the columns under `sampled` give the `cpuinfo_avg_freq` samples of the same cores inside the window. `low` is the number of samples below the limit. |
| 571 | `        print("   The limit of a core is %.1f %% of its cpuinfo_max_freq. request: the lowest scaling_cur_freq. Flags: list at the end." % (100 * (1 - tol)))` | The fifth: the limit of a core as a percentage of its `cpuinfo_max_freq`. The value is 100 times (1 minus `tol`), which is 99.0 by default. `request` is the lowest `scaling_cur_freq`. The flags are listed at the end of the report. |
| 572 | `        print("   %-34s %4s %8s \| %9s %9s %9s %4s %7s \| %6s %9s %9s %5s \| %9s \| %s" % (` | Prints the header row of the table. The format gives each column a fixed width. Four `\|` characters separate five groups of columns: the process, the counters, the samples, the request and the flags. The statement continues in line 573. |
| 573 | `            "process", "cpus", "window s", "min kHz", "med kHz", "max kHz", "cpu", "ratio", "n", "min kHz", "med kHz", "low", "request", "flags"))` | The 14 column names: `process`, `cpus` and `window s`, then `min kHz`, `med kHz`, `max kHz`, `cpu` and `ratio` for the counters, then `n`, `min kHz`, `med kHz` and `low` for the samples, then `request` and `flags`. |
| 574 | `        for p in res["processes"]:` | Starts a loop over the processes. |
| 575 | `            if "cpus" not in p:` | Tests whether the entry has no CPU count. That is a process without a second snapshot (lines 461 to 463). |
| 576 | `                print("   %-34s %s" % (p["name"], " ".join(p["flags"])))` | Then: prints only its name and its flags. |
| 577 | `                continue` | Goes on with the next process. |
| 578 | `            print("   %-34s %4d %8s \| %9s %9s %9s %4s %7s \| %6d %9s %9s %5d \| %9s \| %s" % (` | Prints the row of the process. The statement continues in lines 579 to 582. |
| 579 | `                p["name"][:34], p["cpus"], fmt(p["seconds"], 1), fmt(p["avg_khz"][0]), fmt(p["avg_khz"][1]),` | The values: the name cut to 34 characters, the number of CPUs, the window in seconds with one decimal, and the lowest and the median clock rate from the counters in kHz. |
| 580 | `                fmt(p["avg_khz"][2]), "-" if p["avg_khz_min_cpu"] is None else p["avg_khz_min_cpu"], fmt(p["ratio"][1], 4),` | Continues the values: the highest clock rate from the counters, the number of the CPU with the lowest rate (or `-`), and the median counter ratio with 4 decimals. |
| 581 | `                p["samples"], fmt(p["sample_khz"][0]), fmt(p["sample_khz"][1]), p["samples_low"],` | Continues the values: the number of sampled values, the lowest and the median sampled rate in kHz, and the number of samples below the limit. |
| 582 | `                fmt(p["scaling_cur_freq_min"]), " ".join(p["flags"]) or "none"))` | Ends the values: the lowest requested rate (`scaling_cur_freq`) in kHz, and the flags with spaces between them. A process without a flag gets the word `none`. |
| 583 | `        conv = sorted({c for p in res["processes"] for c in p.get("conversion", [])})` | `conv`: the names of all conversion rules that the processes of this folder used, sorted and without duplicates. |
| 584 | `        print("   rule that turned the counter ratio into kHz: %s" % (", ".join(conv) or "none"))` | Prints which rule turned the counter ratio into kHz, or `none`. |
| 585 | `        took = [ms for p in res["processes"] for ms in p.get("snap_ms", [])]` | `took`: the durations of all snapshots of the folder in ms. |
| 586 | `        if took:` | Tests whether there is a duration. |
| 587 | `            print("   a snapshot took %.0f ms at most (%d snapshots); the probe took %s ms" % (max(took), len(took), res.get("probe", {}).get("took_ms", "-")))` | Then: prints the longest duration of a snapshot in ms, the number of snapshots, and the duration of the probe in ms. |
| 588 | `        for p in res["processes"]:` | Starts a loop over the processes, for the energy lines. |
| 589 | `            for key, counts in sorted(p.get("energy", {}).items()):` | Starts a loop over the energy counters of the process, sorted by path. |
| 590 | `                joules = counts / 1e6                    # hwmon energyN_input and powercap energy_uj count microjoules` | `joules`: the change of the counter divided by 1e6. Comment: the counters `energyN_input` of `hwmon` and `energy_uj` of `powercap` count microjoules [Ref4]. |
| 591 | `                sec = p.get("sensor_seconds")` | `sec`: the time from the end of the first snapshot to the end of the second, in seconds (line 472). |
| 592 | `                print("   energy %s %s: %.3f J%s" % (p["name"], key, joules,` | Prints one line: the word `energy`, the process, the path of the counter and the energy in J with 3 decimals. The statement continues in line 593. |
| 593 | `                                                      "" if not sec else ", %.2f W on average over %.1f s" % (joules / sec, sec)))` | When the time is known and not 0, the line also gives the average power in W with 2 decimals, and the time in seconds with one decimal. The average power is the energy divided by the time. |

### Function `print_report`: the values of `atx` (lines 594 to 620)

| Line | Source | Explanation |
|---:|---|---|
| 594 | `    if res["atx"]:` | Lines 595 to 618 run only when the summary of `atx` gave rows. |
| 595 | `        rows = res["atx"]` | `rows`: these rows. |
| 596 | `        metrics = sorted({r["metric"] for r in rows})` | `metrics`: the names of the metrics, sorted and without duplicates. |
| 597 | `        print("   vendor tool (atx), whole result folder, %d metrics, %d rows. avg = time weighted average when the file has it." % (len(metrics), len(rows)))` | Prints a heading. It says that the values of the vendor tool cover the whole result folder. It gives the number of metrics and the number of rows. It also says that `avg` is the time weighted average when the file has it. |
| 598 | `        groups = {}` | `groups`: the rows per family of metrics. It starts empty. |
| 599 | `        for r in rows:` | Starts a loop over the rows. |
| 600 | `            m = re.match(r"^(.*?)(\d+)?-(power\|current\|voltage\|temp\|frequency\|energy)$", r["metric"])` | The pattern splits a metric name that ends with a hyphen and one of six kinds: `power`, `current`, `voltage`, `temp`, `frequency` or `energy`. Group 1 holds the start of the name. Group 2 holds a number that stands directly before the last hyphen, when there is one. Group 3 holds the kind. Example: `vcpu-c0-power` gives `vcpu-c`, `0` and `power`. |
| 601 | `            kind = m.group(3) if m else "other"` | `kind`: group 3, or `other` for a name that does not fit the pattern. |
| 602 | `            fam = (re.sub(r"\d+$", "", m.group(1)) + "-" + kind) if m else r["metric"]` | `fam`: the name of the family. It is group 1 without digits at its end, a hyphen and the kind, for example `vcpu-c-power`. So metrics that differ only in their number form one family. A name that does not fit the pattern is its own family. |
| 603 | `            groups.setdefault((kind, fam, r["unit"]), []).append(r)` | Adds the row to the group with the key (kind, family, unit). |
| 604 | `        for (kind, fam, unit), rs in sorted(groups.items()):` | Starts a loop over the groups, sorted by kind, family and unit. |
| 605 | `            av = [r["twa"] if r["twa"] is not None else r["avg"] for r in rs]` | `av`: one average per row. It is the time weighted average when the row has one. If not, it is the plain average. |
| 606 | `            av = [v for v in av if v is not None]` | Drops the averages that are `None`. |
| 607 | `            lo = [r["min"] for r in rs if r["min"] is not None]` | `lo`: the `min` values of the rows that have one. |
| 608 | `            hi = [r["max"] for r in rs if r["max"] is not None]` | `hi`: the `max` values of the rows that have one. |
| 609 | `            line = "   %-22s %-8s series %3d  lowest min %s  highest max %s" % (fam, unit, len(rs), fmt(min(lo) if lo else None, 2), fmt(max(hi) if hi else None, 2))` | `line`: the family, the unit, the number of rows (`series`), the lowest `min` and the highest `max`. The two values have 2 decimals. |
| 610 | `            if kind in ("power", "current") and av:` | Tests whether the kind is `power` or `current` and an average exists. |
| 611 | `                line += "  sum of avg %s" % fmt(sum(av), 2)` | Then: the line gets `sum of avg`, the sum of the averages of the rows. |
| 612 | `            elif av:` | If not: tests whether an average exists. |
| 613 | `                line += "  mean of avg %s" % fmt(statistics.mean(av), 2)` | Then: the line gets `mean of avg`, the mean of the averages of the rows. |
| 614 | `            print(line)` | Prints the line. |
| 615 | `        for r in rows:` | Starts a second loop over all rows. |
| 616 | `            if r["metric"].endswith("-power"):` | Takes the rows whose metric name ends with `-power`. |
| 617 | `                print("   power %-18s target %-28s avg %s W  max %s W  n %s" % (` | Prints one line per such row: the metric, the target cut to 28 characters, the average in W, the highest value in W and the value of the column `Count` (`n`). The statement continues in line 618. |
| 618 | `                    r["metric"], r["target"][:28], fmt(r["twa"] if r["twa"] is not None else r["avg"], 2), fmt(r["max"], 2), fmt(r["count"])))` | The values of the line. The average is the time weighted average when the row has one. If not, it is the plain average. |

### Text `FLAGS`: the list of flags that the report prints at its end (lines 621 to 632)

| Line | Source | Explanation |
|---:|---|---|
| 621 | `FLAGS = """flags:` | Starts the text `FLAGS`. `cmd_report` prints it after the last result folder (line 641). Its first line is the heading `flags:`. |
| 622 | `  LOW_AVG            a core ran below the limit on average, by its two counters` | Text of the list: `LOW_AVG`: a core ran below the limit on average, by its two counters (lines 497 to 499). |
| 623 | `  LOW_SAMPLE         a sampled rate of a core was below the limit` | Text of the list: `LOW_SAMPLE`: a sampled rate of a core was below the limit (lines 518 to 519). |
| 624 | `  LIMIT_LOWERED      scaling_max_freq was below cpuinfo_max_freq: Linux was told to request less` | Text of the list: `LIMIT_LOWERED`: `scaling_max_freq` was below `cpuinfo_max_freq`. So Linux was told to request less (lines 521 to 525). |
| 625 | `  REQUEST_BELOW_MAX  scaling_cur_freq was below cpuinfo_max_freq: Linux requested less` | Text of the list: `REQUEST_BELOW_MAX`: `scaling_cur_freq` was below `cpuinfo_max_freq`. So Linux requested less (lines 521 to 525). |
| 626 | `  PERF_LIMITED       the firmware flag perf_limited went from 0 to not 0 during the process` | Text of the list: `PERF_LIMITED`: the firmware flag `perf_limited` went from 0 to a value other than 0 during the process (lines 529 to 532). |
| 627 | `  PERF_LIMITED_ALREADY_SET  the flag was not 0 before the process, so this run cannot show a new event (root clears it)` | Text of the list: `PERF_LIMITED_ALREADY_SET`: the flag was not 0 before the process. So this run cannot show a new event. Root clears the flag (lines 533 to 534). |
| 628 | `  NO_THROTTLE_FLAG   perf_limited could not be read on any core` | Text of the list: `NO_THROTTLE_FLAG`: `perf_limited` could not be read on any core (lines 535 to 536). |
| 629 | `  ONLINE_CHANGED     the list of online CPUs changed.   BOOT_CHANGED  the machine rebooted` | Text of the list: `ONLINE_CHANGED`: the list of online CPUs changed. `BOOT_CHANGED`: the machine rebooted (lines 537 to 539). |
| 630 | `  NO_COUNTERS, NO_SAMPLES, NO_AFTER, CUT_FILE   a record is missing or incomplete"""` | Text of the list: `NO_COUNTERS`, `NO_SAMPLES`, `NO_AFTER` and `CUT_FILE`: a part of the record is missing or incomplete. The three quotation marks end the text. |

### Function `cmd_report`: the command `report` (lines 633 to 644)

| Line | Source | Explanation |
|---:|---|---|
| 633 | `def cmd_report(a):` | Starts the function `cmd_report`, the command `report`. |
| 634 | `    out = [report_folder(f.rstrip("/"), a.tol) for f in a.folders]` | `out`: one result per folder of the command line, from `report_folder`. `rstrip("/")` removes a slash at the end of a folder name. |
| 635 | `    if a.json:` | Tests whether `--json` was given. |
| 636 | `        json.dump(out, sys.stdout, indent=1)` | Then: writes all results as JSON to the standard output. `indent=1` puts each value on its own line, with one space of indent per level. |
| 637 | `        print()` | Prints a line break after the JSON text. |
| 638 | `    else:` | If not: lines 639 to 641 print the text form. |
| 639 | `        for res in out:` | Starts a loop over the results. |
| 640 | `            print_report(res, a.tol)` | Prints the text form of each result. |
| 641 | `        print(FLAGS)` | Prints the list of flags once, after the last folder. |
| 642 | `    return 0` | Returns exit status 0. |

### Function `main`: the command line (lines 645 to 671)

| Line | Source | Explanation |
|---:|---|---|
| 645 | `def main():` | Starts the function `main`. |
| 646 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | `ap`: the reader of the command line. Its description is the first line of the docstring of the file (line 2). |
| 647 | `    sub = ap.add_subparsers(dest="cmd")` | `sub`: the set of commands. The name of the chosen command is stored in `a.cmd`. |
| 648 | `    for name in ("check", "probe", "snap", "watch"):` | Starts a loop over the four commands that share options: `check`, `probe`, `snap` and `watch`. |
| 649 | `        s = sub.add_parser(name)` | `s`: the option reader of this command. |
| 650 | `        s.add_argument("--cpus", required=True)` | `--cpus` is required for all four. |
| 651 | `        s.add_argument("--root", default="")` | `--root` is optional. Its default is an empty text, which stands for the real `/sys` and `/proc`. |
| 652 | `        if name != "check":` | Every command except `check` writes a file. |
| 653 | `            s.add_argument("--out", required=True)` | So `--out` is required for `probe`, `snap` and `watch`. |
| 654 | `        if name == "snap":` | Only `snap` has a label. |
| 655 | `            s.add_argument("--label", default="-")` | `--label` has the default `-`. |
| 656 | `        if name == "watch":` | Only `watch` has the next three options. |
| 657 | `            s.add_argument("--pid", type=int, required=True)` | `--pid`: a whole number, required. It names the process that the sampler watches. |
| 658 | `            s.add_argument("--period-s", type=float, default=1.0)` | `--period-s`: a number with decimals, default 1.0 s. `argparse` stores it as `a.period_s`. |
| 659 | `            s.add_argument("--max-s", type=float, default=900.0)` | `--max-s`: a number with decimals, default 900.0 s. `argparse` stores it as `a.max_s`. |
| 660 | `    s = sub.add_parser("report")` | `s`: the option reader of the command `report`. |
| 661 | `    s.add_argument("--tol", type=float, default=0.01)` | `--tol`: a number with decimals, default 0.01. The limit of a core is (1 minus this value) times its `cpuinfo_max_freq` (line 476). |
| 662 | `    s.add_argument("--json", action="store_true")` | `--json`: a switch without a value. `a.json` is `True` when it is given. |
| 663 | `    s.add_argument("folders", nargs="+")` | `folders`: one or more result folders (`nargs="+"`). |
| 664 | `    a = ap.parse_args()` | `a`: the options that were read. `argparse` ends the program with exit status 2 for an option that is wrong or missing. |
| 665 | `    if not a.cmd:` | Tests whether no command was given. |
| 666 | `        ap.error("a command is needed: check, probe, snap, watch or report")` | Then `ap.error` prints that a command is needed, and ends the program with exit status 2. |
| 667 | `    return {"check": cmd_check, "probe": cmd_probe, "snap": cmd_snap, "watch": cmd_watch, "report": cmd_report}[a.cmd](a) or 0` | Picks the function of the command from a dictionary, calls it with the options, and returns its result as the exit status. `or 0` turns the `None` of `cmd_snap` and `cmd_probe` into 0. |
| 670 | `if __name__ == "__main__":` | Lines 670 to 671 run `main` only when the file is started as a program, not when another file imports it. The test file imports it. |
| 671 | `    sys.exit(main())` | Calls `main` and ends the program. The value that `main` returns is the exit status. |

## References

- [Ref1] external source: Linux kernel documentation, document "CPU Performance Scaling" (source file `Documentation/admin-guide/pm/cpufreq.rst`), read on 2026-11-25 at https://docs.kernel.org/admin-guide/pm/cpufreq.html . It defines the files `cpuinfo_avg_freq`, `cpuinfo_cur_freq`, `cpuinfo_max_freq`, `scaling_cur_freq`, `scaling_max_freq`, `scaling_min_freq` and `scaling_setspeed` with the unit kHz, and the file `boost`.
- [Ref2] external source: Linux kernel documentation, document "Collaborative Processor Performance Control (CPPC)" (source file `Documentation/admin-guide/acpi/cppc_sysfs.rst`), read on 2026-11-25 at https://docs.kernel.org/admin-guide/acpi/cppc_sysfs.html . It defines the files of the folder `acpi_cppc`, and its section "Computing Average Delivered Performance" gives the rule for the two counters.
- [Ref3] external source: Linux kernel file `Documentation/ABI/testing/sysfs-devices-system-cpu`, read on 2026-11-25 at https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-devices-system-cpu . Entries `perf_limited`, `online`, `offline`, `possible` and `isolated`.
- [Ref4] external source: Linux kernel files `sysfs-class-hwmon`, `sysfs-class-thermal` and `sysfs-class-powercap` in the folder `Documentation/ABI/testing`, read on 2026-11-25 at https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-hwmon , https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-thermal and https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-powercap . They give the meaning and the unit of the sensor files.
- [Ref5] external source: Linux manual pages `proc_uptime(5)` and `proc_cmdline(5)`, read on 2026-11-25 at https://man7.org/linux/man-pages/man5/proc_uptime.5.html and https://man7.org/linux/man-pages/man5/proc_cmdline.5.html .
- [Ref6] external source: Linux kernel documentation, source file `Documentation/cpu-freq/cpufreq-stats.rst`, read on 2026-11-25 at https://docs.kernel.org/cpu-freq/cpufreq-stats.html . It describes the files `trans_table` and `reset` of the folder `cpufreq/stats`.
- [Ref7] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its short version says that nothing ran on CRB. Its list of words describes the two counters. Its section 4 lists the sources and the flags of the report. Its section 6 says that the report sets no flag from a power or a temperature value, and that it prints the values of `atx` for a whole result folder.
