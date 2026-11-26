# `hostwatch.py` explained, line by line

- Source file: `bwx11-2026-11-15/hostwatch.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 490 lines, 20948 bytes).
- sha256 of the source when this page was built: `61998bf64c3a5d0ed9bb624c814182e5eb9ace92984bb1fb89206a4a10b13ed0`.
- This file is equal to `bwx10-2026-11-15/hostwatch.py` of the same repo (same sha256). Both pages hold the same explanation.

## Short version: purpose

`hostwatch.py` is the host sampler: while one benchmark process runs, it reads files under `/proc` 20 times per second and writes what changed for that process and on its CPU. The run scripts `run_bwx9.sh`, `run_bwx10.sh` and `run_bwx11.sh` start it beside every process of a step that has a `.watch` file. Its output file shows scheduler activity, interrupts, memory statistics and the threads of other processes on the watched CPU, each with a time on one clock.

## Words used here

- **Host sampler**: this program. It records what the Linux kernel does on one CPU while one process runs.
- **Target**: the watched process, given with `--pid`. The run script gives the process id of the benchmark.
- **Watched CPU**: the CPU given with `--cpu`. The run script gives the CPU of the benchmark from its schedule.
- **Run script**: the script that starts the benchmark processes of a step and, beside them, this sampler.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **`/proc`**: a folder in which Linux shows its state as text files. Reading such a file changes no setting.
- **Sample**: one reading of all watched files at one time.
- **Sample grid, slot**: the planned sample times. They lie one period apart, 50 ms at 20 samples per second. A slot is one of these times.
- **Key**: the name of one value in the output, for example `w.run_ns`.
- **Delta line**: a sample line that holds only the values that changed, each as a difference to the last sample.
- **Absolute line**: a sample line with the word `ABS` that holds the full value of every key.
- **State item**: an item of the form `key:=value`. It gives a new state and not a difference.
- **Scan**: one pass over all threads of the host. It finds the threads of other processes whose last CPU is the watched CPU.
- **Tracked thread**: a thread of another process that a scan found on the watched CPU. The sampler reads its values in every sample.
- **Thread id (`tid`), process id (`pid`)**: the numbers that Linux gives to a thread and to a process.
- **`comm`**: the command name of a process or thread, as Linux shows it.
- **Time slice**: one uninterrupted period in which a thread runs on a CPU.
- **Context switch**: the moment at which Linux takes a thread off a CPU. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU away.
- **Page fault**: the event in which a thread touches a memory page that Linux must first provide. It is minor when no disk read is needed, and major when one is needed.
- **Clock tick**: the unit in which Linux reports the CPU time and the start time of a process. `SC_CLK_TCK` gives the number of ticks per second.
- **Soft interrupt**: a piece of work that the Linux kernel puts off to a later moment, for example work for timers or for the network.
- **`CLOCK_MONOTONIC`**: a Linux clock that only moves forward. All sample times come from it.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Read the options `--pid`, `--cpu`, `--out`, `--hz` and `--max-s`, and check their values (lines 393 to 401).
2. Set the handler for the signals SIGTERM and SIGINT, and open the output file (lines 402 to 404).
3. Write four header lines: the settings, three clocks, the start time and the name of the target, and the CPU list of the sampler (lines 412 to 418).
4. Scan all threads of the host once. Write one `# th` line per thread of another process whose last CPU is the watched CPU, and one scan line (lines 419 to 422).
5. Start the sample grid and take one sample per slot (lines 423 to 434). A sample reads the threads of the target, the line of the watched CPU in `/proc/schedstat`, `/proc/softirqs`, the tracked threads, `/proc/vmstat` and, twice per second, `/proc/interrupts` (lines 347 to 354).
6. Write a delta line when something changed, and an absolute line as the first line and then every 5 s (lines 355 to 389, lines 443 to 444).
7. Leave the loop when the time limit is over or when the target is gone (lines 429 to 431, lines 448 to 449).
8. Between two samples, run a part of a new scan every 2 s, count skipped slots, and sleep until the next slot (lines 454 to 475).
9. Write the footer line with the end reason and the counters, and close the file (lines 481 to 485).

## Behavior a reader must know

- The sampler only reads. It opens files under `/proc` for reading and writes one file, the one named by `--out`.
- The sampler pins nothing. The run script pins it with `taskset` to a CPU that is not a CPU of the benchmark. The fourth header line of the output records the CPU list that the sampler really has (line 418).
- Every sample line starts with one time: `CLOCK_MONOTONIC` in ns, read once before the files of the sample are read (line 428). The files are read one after the other, so the values of one line are not from exactly the same moment.
- The sampler ends in four ways. The footer line names the way (line 484).
  - The target is gone: reason `pid_gone`, exit status 0.
  - The time limit `--max-s` is over: reason `max_s`, exit status 0.
  - The signal SIGTERM or SIGINT arrives: reason `signal`, exit status 0.
  - An error outside a sample: reason `error`, exit status 1.
- A wrong option ends the program with exit status 2 before any file is written (lines 399 to 401).
- An error inside a sample or inside a scan does not end the sampling. It is counted in `errors` and written as an item `hw.error:=` (lines 437 to 439, lines 465 to 468).
- A sample or a part of a scan that takes too long makes the loop skip grid slots. The skipped slots are counted in `missed` and reported with the item `hw.missed:=` (lines 469 to 471).
- At most 512 threads of other processes are tracked at one time (line 58, line 327).
- An absolute line leaves out every interrupt key whose count is 0 (line 384).
- A file without the footer line means that the sampler did not end normally. The run script prints a warning for such a file.
- The folders `bwx8-2026-11-14`, `bwx10-2026-11-15` and `bwx11-2026-11-15` hold the same text of this file.

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/hostwatch.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (490 lines, 20948 bytes, sha256 `61998bf64c3a5d0ed9bb624c814182e5eb9ace92984bb1fb89206a4a10b13ed0`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text: usage, format of the output file, keys (lines 1 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""hostwatch.py - host sampler: what the kernel does on one CPU while one process runs.` | Starts the description text of the file. First line: the name and the purpose. The host sampler records what the Linux kernel does on one CPU while one process runs. `main` uses this line as the description in the help text (line 393). |
| 4 | `Usage: hostwatch.py --pid PID --cpu N --out FILE [--hz 20] [--max-s 120]` | Text of the description: the usage. `--pid` names the process to watch, `--cpu` the CPU to watch and `--out` the output file. `--hz` is the number of samples per second, 20 when it is not given. `--max-s` is the longest run time in seconds, 120 when it is not given. |
| 6 | `It only reads files under /proc. It pins nothing: the caller pins it (taskset) to a CPU` | Text of the description: the program only reads files under `/proc`, the folder in which Linux shows its state as text files. It pins nothing. The caller must pin it with the tool `taskset`. |
| 7 | `other than N. It ends when PID is gone, after --max-s seconds, or on SIGTERM or SIGINT.` | Continues the text: the caller must pin the sampler to a CPU other than the watched one. The sampler ends in three ways: the watched process is gone, the `--max-s` time is over, or the signal SIGTERM or SIGINT arrives. |
| 8 | `Exit status 0 in all three cases, 2 for a usage error, 1 if an error outside a sample ended it.` | Continues the text: the exit status is 0 in all three cases. It is 2 for a wrong usage, and 1 when an error outside a sample ended the run. |
| 10 | `Output file. Lines that start with "#" are header or footer lines:` | Text of the description: the format of the output file. Lines that start with `#` are header lines or the footer line. |
| 11 | `  # hostwatch v1 pid=.. cpu=.. hz=.. max_s=..` | The first header line of the output file: the format version and the four settings. |
| 12 | `  # clocks mono_ns=.. boot_ns=.. real_ns=..     CLOCK_MONOTONIC, CLOCK_BOOTTIME, CLOCK_REALTIME, read together` | The second header line: three Linux clocks in ns, read one directly after the other. `CLOCK_MONOTONIC` is the clock of all sample times. `CLOCK_BOOTTIME` counts from the boot. `CLOCK_REALTIME` is the time of day. With this line a sample time can be converted to the other two clocks. |
| 13 | `  # target starttime_ticks=.. clk_tck=.. comm=..   field 22 of /proc/PID/stat (ticks after boot) and SC_CLK_TCK` | The third header line: the start time of the watched process in clock ticks after the boot (field 22 of the file `/proc/PID/stat`), the number of clock ticks per second (`SC_CLK_TCK`), and the command name of the process (`comm`). |
| 14 | `  # sampler pid=.. allowed_cpus=..              this process and the CPUs that it may run on` | The fourth header line: the process id of the sampler and the CPUs on which the sampler may run. |
| 15 | `  # th tid=.. pid=.. comm=..                    one line per thread of the host whose last CPU was N at the start` | Then one header line per thread of another process whose last CPU was the watched CPU at the start: its thread id (`tid`), its process id and its command name. |
| 16 | `  # scan threads=.. on_cpu=.. took_ms=..` | Then one header line about the first scan of all threads of the host: the number of threads seen, the number found on the watched CPU, and the time that the scan took in ms. |
| 17 | `  # end reason=pid_gone\|max_s\|signal\|error samples=.. missed=.. max_sample_us=.. errors=..` | The footer line, the last line of the file: why the sampler ended (`pid_gone`, `max_s`, `signal` or `error`), the number of samples, the number of sample slots that were skipped, the longest time of one sample in microseconds, and the number of errors. |
| 18 | `                                                errors: samples or scan parts that raised an error. Such a sample` | Continues the text about the footer: `errors` counts the samples and the parts of a scan in which an error was raised. |
| 19 | `                                                writes the line "<t_mono_ns> hw.error:=<error type>" and the` | Continues the text: a sample with an error writes a line with the sample time and the item `hw.error:=`, followed by the type of the error. |
| 20 | `                                                sampler goes on. reason=error: an error outside a sample ended it.` | Continues the text: the sampler goes on after such an error. The reason `error` in the footer means that an error outside a sample ended the run. |
| 21 | `Sample lines:` | Text of the description: the heading of the two kinds of sample lines. |
| 22 | `  <t_mono_ns> key=delta key:=value ...          only when something changed since the last sample` | A delta line: the sample time in ns on `CLOCK_MONOTONIC`, then one item per value that changed after the last sample. The line is written only when at least one value changed. |
| 23 | `                                                (a key that appears after the first sample: key:=its value)` | Continues the text: a key that is seen for the first time after the first sample is written as `key:=` with its value. |
| 24 | `  <t_mono_ns> ABS key=value ...                 every 5 s, and as the first line: all absolute values.` | An absolute line: the sample time, the word `ABS`, then every key with its full value. It is the first sample line, and it is written again every 5 s. The code leaves out an interrupt key whose value is 0 (line 384). |
| 25 | `                                                With a delta line of the same time, the delta line comes first.` | Continues the text: when one sample writes both lines, the delta line comes first. |
| 26 | `"key=delta" is the change of a counter. "key:=value" is a new state, not a difference` | Text of the description: an item with `=` gives the change of a counter after the last sample. An item with `:=` gives a new state and is not a difference. |
| 27 | `(a CPU number, "na" for a value that could not be read, a thread that appeared or left).` | Continues the text: examples of a state are a CPU number, the word `na` for a value that could not be read, and a thread that appeared or left. |
| 29 | `Keys:` | Text of the description: the heading of the list of keys. |
| 30 | `  m.<f>            main thread of the target (tid == PID)` | Keys that start with `m.` belong to the main thread of the watched process. Its thread id is equal to the process id. |
| 31 | `  w.<f>, w2.<f>..  other threads of the target in the order they appear (bwx8: w is the pinned worker)` | Keys that start with `w.`, `w2.` and so on belong to the other threads of the watched process, in the order in which the sampler first sees them. For the runner `bwx8`, `w` is the worker thread that is pinned to the benchmark CPU. |
| 32 | `                   <f>: run_ns wait_ns slices (schedstat), nvcsw nivcsw (status),` | The values per thread, first part. From the file `schedstat` of the thread: `run_ns` (time on a CPU in ns), `wait_ns` (time waiting for a CPU in ns) and `slices` (the number of time slices that it ran) [Ref1]. From the file `status`: `nvcsw` and `nivcsw`, the counts of voluntary and involuntary context switches. |
| 33 | `                        minflt majflt utime stime (stat; utime and stime in clock ticks),` | The values per thread, second part, from the file `stat`: `minflt` and `majflt` (minor and major page faults), `utime` and `stime` (CPU time in user mode and inside the Linux kernel, both in clock ticks) [Ref2]. |
| 34 | `                        cpu (state: the CPU it ran on last), tid (state)` | The values per thread, third part: `cpu` is the CPU on which the thread ran last, and `tid` is its thread id. Both are states, not counters. |
| 35 | `  cpu.<f>          the cpuN line of /proc/schedstat: yld legacy sched goidle ttwu ttwu_local` | Keys that start with `cpu.` come from the line of the watched CPU in the file `/proc/schedstat`, the scheduler statistics of Linux. The first six values: calls of `sched_yield` (`yld`), a field that is always 0 (`legacy`), calls of the scheduler (`sched`), calls that left the CPU idle (`goidle`), wake-ups of a task (`ttwu`), and wake-ups for this same CPU (`ttwu_local`) [Ref1]. |
| 36 | `                   run_ns wait_ns pcount` | The last three values of the CPU line: the time that tasks ran on this CPU in ns (`run_ns`), the time that tasks waited to run on it in ns (`wait_ns`), and the number of time slices that ran on it (`pcount`) [Ref1]. |
| 37 | `  sirq.<NAME>      column N of /proc/softirqs` | Keys that start with `sirq.` hold the column of the watched CPU in the file `/proc/softirqs`. That file counts the soft interrupts per kind and per CPU. A soft interrupt is a piece of work that the Linux kernel puts off to a later moment, for example work for timers or for the network. |
| 38 | `  th.<tid>.<comm>.<f>   a thread of another process whose last CPU is N: run_ns wait_ns slices.` | Keys that start with `th.` belong to a thread of another process whose last CPU is the watched CPU. The key holds the thread id and the command name. The values are `run_ns`, `wait_ns` and `slices`. |
| 39 | `                   The comm is read again when the thread ran (the comm of a kworker names its work).` | Continues the text: the sampler reads the command name again each time such a thread ran. The reason: the name of a `kworker`, a worker thread of the Linux kernel, names the work that it does at that moment. |
| 40 | `                   th.<tid>.<comm>.new:=<slices> a thread found on CPU N by a later scan (every 2 s);` | Continues the text: the item `.new:=` with the slice count reports a thread that a later scan found on the watched CPU. A scan starts every 2 s. |
| 41 | `                   .left:=<cpu> it ran on another CPU and is dropped; .gone:=1 it ended.` | Continues the text: the item `.left:=` with a CPU number reports that the thread ran on another CPU. The sampler then stops tracking it. The item `.gone:=1` reports that the thread ended. |
| 42 | `  vm.<key>         every key of /proc/vmstat whose value changed` | Keys that start with `vm.` hold the counters of the file `/proc/vmstat`, the memory statistics of Linux. A delta line shows only those that changed. |
| 43 | `  irq.<label>[.<description>]   column N of every row of /proc/interrupts, read twice per second` | Keys that start with `irq.` hold the column of the watched CPU in every row of the file `/proc/interrupts`, which counts the hardware interrupts per CPU. The key holds the label of the row and, when the row has one, its description. The sampler reads this file twice per second. |
| 44 | `  hw.missed        sample slots that were skipped because a sample or a scan ran long` | The key `hw.missed` gives the number of sample slots that were skipped up to now. A slot is skipped when a sample or a part of a scan took too long. |
| 45 | `"""` | Ends the description text. |

### Imports, constants and small helpers (lines 46 to 82)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `import argparse` | Loads the Python module `argparse`, which reads the command line options. |
| 47 | `import os` | Loads `os`: file access, process ids and the CPU list. |
| 48 | `import re` | Loads `re`: regular expressions. |
| 49 | `import signal` | Loads `signal`: the handling of the signals SIGTERM and SIGINT. |
| 50 | `import sys` | Loads `sys`: the error output and the exit status. |
| 51 | `import time` | Loads `time`: the clocks and the sleep. |
| 53 | `CPU_FIELDS = ["yld", "legacy", "sched", "goidle", "ttwu", "ttwu_local", "run_ns", "wait_ns", "pcount"]` | `CPU_FIELDS`: the names that the sampler gives to the 9 values of a CPU line of `/proc/schedstat`, in the order of the file [Ref1]. |
| 54 | `BAD = re.compile(r"[^A-Za-z0-9_/:+.@-]")` | `BAD`: a compiled pattern. It matches one character that is not a letter, not a digit and not one of `_`, `/`, `:`, `+`, `.`, `@` and `-`. The function `clean` replaces such a character. |
| 55 | `CLOCK_BOOTTIME = getattr(time, "CLOCK_BOOTTIME", 7)` | `CLOCK_BOOTTIME`: the number of the Linux clock that counts from the boot. The value comes from the module `time`. When that module does not have the name, the number 7 is used. |
| 56 | `ABS_PERIOD_NS = 5 * 10 ** 9` | `ABS_PERIOD_NS`: 5 s in ns. An absolute line is written when this time has passed after the last one. |
| 57 | `SCAN_PERIOD_NS = 2 * 10 ** 9` | `SCAN_PERIOD_NS`: 2 s in ns. A new scan of all threads of the host starts when this time has passed after the start of the last one. |
| 58 | `MAX_FOREIGN = 512` | `MAX_FOREIGN`: 512, the largest number of threads of other processes that the sampler tracks at one time. |
| 61 | `class Stop(Exception):` | Defines the exception `Stop`. The signal handler raises it to end the sampling. |
| 62 | `    pass` | The class has no content of its own. |
| 65 | `def on_signal(signum, frame):` | Starts the function `on_signal`, the handler for the signals SIGTERM and SIGINT. Python gives it the signal number and the place in the code, which are not used. |
| 66 | `    raise Stop()` | Raises `Stop`. The exception ends the sampling loop of `main`, which then writes the footer line. |
| 69 | `def clock_ns(clock):` | Starts the function `clock_ns`. It returns the value of the clock with the number `clock`, in ns. |
| 70 | `    if hasattr(time, "clock_gettime_ns"):` | Tests whether this Python has the function `clock_gettime_ns`, which gives whole ns. |
| 71 | `        return time.clock_gettime_ns(clock)` | If so: returns its value. |
| 72 | `    return int(time.clock_gettime(clock) * 1e9)` | If not: reads the clock in seconds as a floating point number and converts it to whole ns. |
| 75 | `def mono():` | Starts the function `mono`. It returns `CLOCK_MONOTONIC` in ns. This clock only moves forward, and a change of the time of day does not move it. All sample times come from it. |
| 76 | `    return clock_ns(time.CLOCK_MONOTONIC)` | Reads the clock with `clock_ns`. |
| 79 | `def clean(text):` | Starts the function `clean`. It makes a text usable as a part of a key: no blank and no unusual character. |
| 80 | `    return BAD.sub("_", text) or "_"` | Replaces every character that `BAD` matches with `_`. An empty result becomes one `_`. |

### Class `Src`: one file under `/proc` that is read many times (lines 83 to 127)

| Line | Source | Explanation |
|---:|---|---|
| 83 | `class Src:` | Starts the class `Src`: one file under `/proc` that is read many times. |
| 84 | `    """One /proc file, opened once and read again from offset 0. A read that fails is tried` | Description text of the class: the file is opened once and then read again from its start each time. A read that fails is tried a second time. |
| 85 | `    once more after a new open. read() returns bytes, or None if the file cannot be read.` | Continues the text: the second try opens the file again. `read` returns the content as bytes, or `None` when the file cannot be read. |
| 86 | `    single: a per-thread file (stat, status, schedstat). The kernel gives it in one piece, so one` | Continues the text: `single` marks a file of one thread (`stat`, `status`, `schedstat`). The Linux kernel gives such a file in one piece. |
| 87 | `    read holds it. Every other file is read until a read returns nothing: the kernel gives` | Continues the text: so one read call holds the whole per-thread file. Every other file is read until a read call returns no data. |
| 88 | `    /proc/vmstat and /proc/interrupts in pieces of about one memory page (4 KiB on many hosts),` | Continues the text: the reason is that the Linux kernel gives `/proc/vmstat` and `/proc/interrupts` in pieces of about one memory page, 4 KiB on many hosts. |
| 89 | `    and a shorter first piece does not mean that the file has ended."""` | Continues the text: so a first piece that is shorter than the request does not mean that the file has ended. The line also ends the description text. |
| 91 | `    def __init__(self, path, single=False):` | Starts the constructor of `Src`. `single` is false unless the caller gives it. |
| 92 | `        self.path, self.fd, self.single = path, -1, single` | Stores the path and the `single` mark. `fd` is the file descriptor. The value -1 means that the file is not open. |
| 94 | `    def _read(self, upto):` | Starts the method `_read`: one read of the file from its start. `upto` is `None` or a function that says when enough data was read. |
| 95 | `        if self.fd < 0:` | Tests whether the file is not open. |
| 96 | `            self.fd = os.open(self.path, os.O_RDONLY)` | Opens the file for reading only. The descriptor stays open for the later reads. |
| 97 | `        parts, off = [], 0` | `parts`: the pieces read up to now. `off`: the offset of the next read, 0 at first. |
| 98 | `        while True:` | Starts the read loop. |
| 99 | `            b = os.pread(self.fd, 1 << 16, off)` | `os.pread` reads at most 65536 bytes (`1 << 16`) at the offset `off`. It does not move the position of the open file. So the next call of `_read` starts at offset 0 again and gets the current content. |
| 100 | `            if not b:` | An empty result means the end of the file. |
| 101 | `                break` | Leaves the loop at the end of the file. |
| 102 | `            parts.append(b)` | Keeps the piece. |
| 103 | `            off += len(b)` | Moves the offset forward by the number of bytes read. |
| 104 | `            if upto is not None:` | The case with a stop function. |
| 105 | `                if upto(b"".join(parts)):` | Calls the function with all data read up to now. |
| 106 | `                    break` | Leaves the loop when the function says that the data is enough. The rest of the file is not read. |
| 107 | `            elif self.single and len(b) < (1 << 16):` | The case of a per-thread file without a stop function: a piece shorter than 65536 bytes is the whole file. |
| 108 | `                break                      # a per-thread file: one read holds it` | Leaves the loop after that one read. This saves the second read call, which would only report the end of the file. |
| 109 | `        return b"".join(parts)` | Returns all pieces joined to one byte string. |
| 111 | `    def read(self, upto=None):` | Starts the method `read`, the one that the rest of the program calls. |
| 112 | `        for _ in (0, 1):` | Starts a loop of at most two tries. |
| 113 | `            try:` | Starts the block whose error is caught. |
| 114 | `                return self._read(upto)` | Returns the content when the read works. |
| 115 | `            except OSError:` | Catches an error of the operating system, for example for a file that is gone. |
| 116 | `                self.close()` | Closes the file. The second try then opens it again. |
| 117 | `        return None` | Both tries failed: returns `None`. |
| 119 | `    def close(self):` | Starts the method `close`. |
| 120 | `        if self.fd >= 0:` | Only when the file is open. |
| 121 | `            try:` | Starts the block whose error is caught. |
| 122 | `                os.close(self.fd)` | Closes the file descriptor. |
| 123 | `            except OSError:` | Catches an error of the close. |
| 124 | `                pass` | Ignores it. |
| 125 | `            self.fd = -1` | Marks the file as not open. |

### Functions `stat_fields` and `column_table` (lines 128 to 159)

| Line | Source | Explanation |
|---:|---|---|
| 128 | `def stat_fields(data):` | Starts the function `stat_fields`. It splits the content of the file `stat` of a process or of a thread. |
| 129 | `    """(comm, fields after the comm) of a stat file; field k of proc(5) is fields[k - 3]."""` | Description text: the function returns the command name and the list of the fields after it. Field k in the numbering of the Linux manual page proc(5) is entry `k - 3` of the list. So entry 0 is field 3, the state of the thread [Ref2]. |
| 130 | `    try:` | Starts the block whose errors are caught. |
| 131 | `        text = data.decode("ascii", "replace")` | Converts the bytes to text. A byte that is not ASCII becomes a replacement character. |
| 132 | `        a, b = text.index("("), text.rindex(")")` | `a`: the place of the first `(`. `b`: the place of the last `)`. The command name stands between them. The name can hold blanks and parentheses itself, so the last `)` is used. |
| 133 | `        return text[a + 1:b], text[b + 2:].split()` | Returns two values: the command name, and the text after the `)` and one blank, split at blanks into the list of fields. |
| 134 | `    except (ValueError, AttributeError):` | Catches two errors: no parenthesis in the text (`ValueError`), and `data` equal to `None` after a failed read (`AttributeError`). |
| 135 | `        return None, None` | Returns `None` for both values in that case. |
| 138 | `def column_table(data, cpu):` | Starts the function `column_table`. It takes the column of one CPU from the content of `/proc/softirqs` or of `/proc/interrupts`. |
| 139 | `    """Rows of /proc/softirqs or /proc/interrupts: [(label, value of column cpu, description)]."""` | Description text: the function returns one entry per row, with the label and the value of the column of `cpu`. The text names three items per entry. The code returns four (line 156). |
| 140 | `    rows = []` | `rows`: the result list, empty at first. |
| 141 | `    if data is None:` | The file could not be read. |
| 142 | `        return None` | Returns `None` in that case. |
| 143 | `    lines = data.split(b"\n")` | Splits the content into lines. |
| 144 | `    head = lines[0].split()` | `head`: the words of the first line. They are the column heads `CPU0`, `CPU1` and so on. |
| 145 | `    try:` | Starts the block whose error is caught. |
| 146 | `        col = head.index(b"CPU%d" % cpu)` | `col`: the place of the column of the watched CPU among the column heads. |
| 147 | `    except ValueError:` | The head has no column for this CPU. |
| 148 | `        return None` | Returns `None` in that case. |
| 149 | `    for line in lines[1:]:` | Starts a loop over the data rows. |
| 150 | `        label, sep, rest = line.partition(b":")` | Splits the row at the first colon: `label` is the text before it, `rest` the text after it. `sep` is empty when the row has no colon. |
| 151 | `        if not sep:` | A row without a colon. |
| 152 | `            continue` | Skips it. |
| 153 | `        parts = rest.split(None, col + 1)` | Splits the rest at blanks into at most `col + 2` pieces: the values of the columns up to the wanted one, and one piece with everything after it. |
| 154 | `        if len(parts) <= col or not parts[col].isdigit():` | Tests whether the row has too few columns, or whether the wanted piece is not a number. |
| 155 | `            continue` | Skips such a row. |
| 156 | `        rows.append((label.strip(), int(parts[col]), rest, len(head)))` | Adds one entry with four items: the label without blanks around it, the value of the column as a number, the whole text after the colon, and the number of column heads. |
| 157 | `    return rows` | Returns the list. |

### Class `Watch`: its state, and `target` (the threads of the watched process) (lines 160 to 217)

| Line | Source | Explanation |
|---:|---|---|
| 160 | `class Watch:` | Starts the class `Watch`. It holds the whole state of the sampler and takes the samples. |
| 161 | `    def __init__(self, pid, cpu, out):` | Starts the constructor. `pid`: the watched process, called the target. `cpu`: the watched CPU. `out`: the open output file. |
| 162 | `        self.pid, self.cpu, self.out = pid, cpu, out` | Stores the three arguments. |
| 163 | `        self.prev = {}                      # key -> last value (int, str, or None for "na")` | `prev`: the last value of every key. A value is a whole number, a text, or `None`. The output shows `None` as `na`. |
| 164 | `        self.threads = {}                   # tid -> (prefix, schedstat, status, stat) of the target` | `threads`: the known threads of the target. For each thread id it holds the key prefix (`m`, `w`, `w2` and so on) and the three `Src` objects of its files `schedstat`, `status` and `stat`. |
| 165 | `        self.nworkers = 0` | `nworkers`: the number of threads of the target seen up to now, without the main thread. |
| 166 | `        self.foreign = {}                   # tid -> [pid, comm, schedstat Src, stat Src]` | `foreign`: the tracked threads of other processes. For each thread id it holds the process id, the command name and the `Src` objects of its files `schedstat` and `stat`. |
| 167 | `        self.schedstat = Src("/proc/schedstat")` | The source for `/proc/schedstat`, the scheduler statistics per CPU. |
| 168 | `        self.softirqs = Src("/proc/softirqs")` | The source for `/proc/softirqs`, the counts of soft interrupts per CPU. |
| 169 | `        self.vmstat = Src("/proc/vmstat")` | The source for `/proc/vmstat`, the memory statistics. |
| 170 | `        self.interrupts = Src("/proc/interrupts")` | The source for `/proc/interrupts`, the counts of hardware interrupts per CPU. |
| 171 | `        self.irq_names = {}` | `irq_names`: the key name of each row of `/proc/interrupts`. It is kept, so each name is built only once. |
| 172 | `        self.cpu_tag = b"\ncpu%d " % cpu` | `cpu_tag`: the text that starts the line of the watched CPU in `/proc/schedstat`: a newline, the word `cpu`, the number and a blank. With the blank, `cpu2` does not match the line of `cpu20`. |
| 173 | `        self.events = []                    # "key:=value" items made outside a sample` | `events`: state items that were made outside the comparison of a sample, for example by a scan. The next sample writes them. |
| 174 | `        self.scan = None` | `scan`: the scan of the host that is running, or `None`. |
| 175 | `        self.scan_count = 0` | `scan_count`: the number of threads that the last complete scan looked at. |
| 177 | `    # ---- the target ----` | Comment: the code for the target, the watched process, starts here. |
| 178 | `    def target(self, cur):` | Starts the method `target`. It reads the values of every thread of the target into the dictionary `cur`, which holds the values of this sample. |
| 179 | `        """Reads every thread of the target. Returns False if the target is gone."""` | Description text: the method reads every thread of the target. It returns `False` when the target is gone. |
| 180 | `        try:` | Starts the block whose error is caught. |
| 181 | `            tids = os.listdir("/proc/%d/task" % self.pid)` | `tids`: the names in the folder `/proc/PID/task`. Each name is the id of one thread of the target. |
| 182 | `        except OSError:` | The folder cannot be listed: the process is gone. |
| 183 | `            return False` | Returns `False`. |
| 184 | `        alive = False` | `alive`: becomes `True` when at least one thread is still alive. |
| 185 | `        for name in tids:` | Starts the loop over the threads. |
| 186 | `            tid = int(name)` | The thread id as a number. |
| 187 | `            t = self.threads.get(tid)` | Looks the thread up among the known threads. |
| 188 | `            if t is None:` | A thread that the sampler sees for the first time. |
| 189 | `                if tid == self.pid:` | The main thread: its thread id is the process id. |
| 190 | `                    pre = "m"` | Its key prefix is `m`. |
| 191 | `                else:` | Every other thread. |
| 192 | `                    self.nworkers += 1` | Counts it. |
| 193 | `                    pre = "w" if self.nworkers == 1 else "w%d" % self.nworkers` | Its key prefix is `w` for the first such thread, then `w2`, `w3` and so on. |
| 194 | `                base = "/proc/%d/task/%d/" % (self.pid, tid)` | `base`: the folder of the thread under `/proc`. |
| 195 | `                t = self.threads[tid] = (pre, Src(base + "schedstat", True), Src(base + "status", True), Src(base + "stat", True))` | Stores the prefix and three sources, for the files `schedstat`, `status` and `stat` of the thread. `True` marks each as a per-thread file that one read holds. |
| 196 | `            pre = t[0]` | The key prefix of this thread. |
| 197 | `            cur[pre + ".tid"] = tid` | Stores the thread id under the key `tid`. |
| 198 | `            f = (t[1].read() or b"").split()` | Reads the file `schedstat` of the thread and splits it into its fields. A failed read gives an empty list. |
| 199 | `            for i, k in enumerate(("run_ns", "wait_ns", "slices")):` | Starts a loop over the three fields of that file: the time on a CPU in ns, the time waiting for a CPU in ns, and the number of time slices [Ref1]. |
| 200 | `                cur[pre + "." + k] = int(f[i]) if len(f) == 3 and f[i].isdigit() else None` | Stores the field as a number. When the file does not have exactly 3 fields, or the field is not a number, the value is `None`. |
| 201 | `            s = t[2].read() or b""` | Reads the file `status` of the thread. A failed read gives an empty text. |
| 202 | `            for k, tag in (("nvcsw", b"\nvoluntary_ctxt_switches:"), ("nivcsw", b"\nnonvoluntary_ctxt_switches:")):` | Starts a loop over two lines of that file: the count of voluntary context switches (the thread gave up the CPU) and the count of involuntary ones (Linux took the CPU away). |
| 203 | `                i = s.find(tag)` | Finds the start of the line. |
| 204 | `                v = s[i + len(tag):].split(None, 1)[:1] if i >= 0 else []` | `v`: a list with the first word after the line name, or an empty list when the line is missing. |
| 205 | `                cur[pre + "." + k] = int(v[0]) if v and v[0].isdigit() else None` | Stores the count as a number, or `None` when it could not be read. |
| 206 | `            _, sf = stat_fields(t[3].read())` | Reads the file `stat` of the thread and splits it. `sf` is the list of the fields after the command name. |
| 207 | `            ok = sf is not None and len(sf) > 36` | `ok`: the file was read and has at least 37 fields after the name. |
| 208 | `            for k, i in (("minflt", 7), ("majflt", 9), ("utime", 11), ("stime", 12)):` | Starts a loop over four values with their places in `sf`. In the numbering of proc(5) they are field 10 (minor page faults), field 12 (major page faults), field 14 (CPU time in user mode) and field 15 (CPU time inside the Linux kernel). Both times are in clock ticks [Ref2]. |
| 209 | `                cur[pre + "." + k] = int(sf[i]) if ok else None` | Stores the value as a number, or `None`. |
| 210 | `            cur[pre + ".cpu"] = sf[36] if ok else None` | Stores field 39, the CPU on which the thread ran last [Ref2]. It is kept as text. So the output shows it as a state and not as a difference. |
| 211 | `            if ok and sf[0] not in ("Z", "X"):` | Tests field 3, the state of the thread. `Z` means a zombie: a thread that has ended and waits to be collected. `X` means dead [Ref2]. |
| 212 | `                alive = True` | A thread in any other state counts as alive. |
| 213 | `        for tid in [t for t in self.threads if str(t) not in tids]:` | Builds the list of the known threads that are no longer in the folder, and starts a loop over them. |
| 214 | `            for src in self.threads.pop(tid)[1:]:` | Removes such a thread from `threads` and starts a loop over its three sources. |
| 215 | `                src.close()` | Closes the file. The last values of the thread stay in `prev`. |
| 216 | `        return alive` | Returns whether the target is alive. |

### `Watch`: the CPU line, soft interrupts, hardware interrupts, memory statistics (lines 218 to 263)

| Line | Source | Explanation |
|---:|---|---|
| 218 | `    # ---- the CPU ----` | Comment: the code for the watched CPU starts here. |
| 219 | `    def cpu_line(self, cur):` | Starts the method `cpu_line`. It reads the line of the watched CPU from `/proc/schedstat` into `cur`. |
| 220 | `        tag = self.cpu_tag` | The text that starts the wanted line. |
| 221 | `        data = self.schedstat.read(lambda b: b.find(b"\n", b.find(tag) + 1) > 0 if tag in b else False)` | Reads `/proc/schedstat` only as far as needed. The stop function returns true when the data holds the tag and a newline after it, that is the complete line of the CPU. The rest of the file is not read. |
| 222 | `        i = data.find(tag) if data else -1` | `i`: the place of the tag in the data, or -1 when the read failed or gave no data. |
| 223 | `        if i < 0:` | The line was not found. |
| 224 | `            cur["cpu.pcount"] = None` | Marks this with the value `None` for the key `cpu.pcount`. The output shows it as `na`. |
| 225 | `            return` | Ends the method. |
| 226 | `        f = data[i + len(tag):].split(b"\n", 1)[0].split()` | `f`: the fields of the line after the tag, up to the end of the line. |
| 227 | `        for n, v in enumerate(f):` | Starts a loop over the fields. |
| 228 | `            name = CPU_FIELDS[n] if len(f) == len(CPU_FIELDS) else "f%d" % (n + 1)` | The name of the field. It comes from `CPU_FIELDS` when the line has exactly 9 fields. A line with another number of fields gets the names `f1`, `f2` and so on. |
| 229 | `            cur["cpu." + name] = int(v) if v.isdigit() else None` | Stores the field as a number, or `None`. |
| 231 | `    def softirq(self, cur):` | Starts the method `softirq`. It reads the column of the watched CPU from `/proc/softirqs` into `cur`. |
| 232 | `        rows = column_table(self.softirqs.read(), self.cpu)` | Reads the file and takes the column with `column_table`. |
| 233 | `        if rows is None:` | The file or the column could not be read. |
| 234 | `            cur["sirq.TIMER"] = None` | Marks this with the value `None` for the key `sirq.TIMER`. |
| 235 | `            return` | Ends the method. |
| 236 | `        for label, v, _, _ in rows:` | Starts a loop over the rows. Only the label and the value are used. |
| 237 | `            cur["sirq." + clean(label.decode("ascii", "replace"))] = v` | Stores the count under the key `sirq.` plus the cleaned label, for example `sirq.TIMER`. |
| 239 | `    def irq(self, cur):` | Starts the method `irq`. It reads the column of the watched CPU from `/proc/interrupts` into `cur`. |
| 240 | `        rows = column_table(self.interrupts.read(), self.cpu)` | Reads the file and takes the column. |
| 241 | `        if rows is None:` | The file or the column could not be read. |
| 242 | `            cur["irq.na"] = None` | Marks this with the value `None` for the key `irq.na`. |
| 243 | `            return` | Ends the method. |
| 244 | `        for label, v, rest, ncpu in rows:` | Starts a loop over the rows. |
| 245 | `            name = self.irq_names.get(label)` | Looks up the key name of this row. |
| 246 | `            if name is None:` | The row is seen for the first time: its key name is built now. |
| 247 | `                desc = "_".join(x.decode("ascii", "replace") for x in rest.split()[ncpu:])` | `desc`: the words of the row that follow the CPU columns, joined with `_`. They describe the interrupt. |
| 248 | `                name = "irq." + clean(label.decode("ascii", "replace"))` | The key starts with `irq.` and the cleaned label. |
| 249 | `                if desc:` | When the row has a description. |
| 250 | `                    name += "." + clean(desc)[:48]` | Adds a dot and the first 48 characters of the cleaned description. |
| 251 | `                self.irq_names[label] = name` | Keeps the key name for the next samples. |
| 252 | `            cur[name] = v` | Stores the count. |
| 254 | `    def vm(self, cur):` | Starts the method `vm`. It reads every counter of `/proc/vmstat` into `cur`. |
| 255 | `        data = self.vmstat.read()` | Reads the whole file. |
| 256 | `        if data is None:` | The read failed. |
| 257 | `            cur["vm.na"] = None` | Marks this with the value `None` for the key `vm.na`. |
| 258 | `            return` | Ends the method. |
| 259 | `        for line in data.split(b"\n"):` | Starts a loop over the lines. Each line is a name, a blank and a number. |
| 260 | `            k, _, v = line.partition(b" ")` | Splits the line at the first blank into the name `k` and the value `v`. |
| 261 | `            if v.isdigit():` | Only a line whose value is a number. |
| 262 | `                cur["vm." + k.decode("ascii", "replace")] = int(v)` | Stores the value under the key `vm.` plus the name. |

### `Watch`: threads of other processes (`foreign_sample`, `drop`, `scanner`) (lines 264 to 343)

| Line | Source | Explanation |
|---:|---|---|
| 264 | `    # ---- threads of other processes on the CPU ----` | Comment: the code for the threads of other processes on the watched CPU starts here. |
| 265 | `    def foreign_sample(self, cur):` | Starts the method `foreign_sample`. It reads the tracked threads of other processes into `cur`. |
| 266 | `        for tid in list(self.foreign):` | Starts a loop over a copy of the list of tracked thread ids. With the copy the loop can drop a thread. |
| 267 | `            ent = self.foreign[tid]` | The entry of the thread. |
| 268 | `            f = (ent[2].read() or b"").split()` | Reads the file `schedstat` of the thread and splits it into fields. |
| 269 | `            base = "th.%d.%s." % (tid, ent[1])` | `base`: the key prefix of the thread: `th.`, the thread id, a dot, the command name and a dot. |
| 270 | `            if len(f) != 3:` | The file does not give 3 fields: the thread has ended. |
| 271 | `                self.events.append(base + "gone:=1")` | Adds the state item `gone:=1` for this thread. This sample writes it. |
| 272 | `                self.drop(tid)` | Stops tracking the thread. |
| 273 | `                continue` | Goes on with the next thread. |
| 274 | `            slices = int(f[2])` | `slices`: the number of time slices that the thread ran up to now. |
| 275 | `            old = self.prev.get(("th", tid))` | The values of the thread from the last sample. |
| 276 | `            if old is not None and slices != old[2]:` | The slice count changed: the thread ran after the last sample. |
| 277 | `                # It ran: read the comm again, and the CPU it ran on last.` | Comment: in that case the sampler reads the command name again, and the CPU on which the thread ran last. |
| 278 | `                comm, sf = stat_fields(ent[3].read())` | Reads and splits the file `stat` of the thread. |
| 279 | `                if comm is not None and len(sf) > 36:` | Only when the file was read and has at least 37 fields after the name. |
| 280 | `                    if clean(comm) != ent[1]:` | The command name changed. |
| 281 | `                        ent[1] = clean(comm)` | Stores the new name. |
| 282 | `                        base = "th.%d.%s." % (tid, ent[1])` | Builds the key prefix again, with the new name. |
| 283 | `                    if int(sf[36]) != self.cpu:` | Tests field 39: the thread ran last on a CPU other than the watched one. |
| 284 | `                        self.events.append("%sleft:=%s" % (base, sf[36]))` | Adds the state item `left:=` with that CPU number. |
| 285 | `                        self.drop(tid)` | Stops tracking the thread. |
| 286 | `                        continue` | Goes on with the next thread. |
| 287 | `            cur[("th", tid)] = (int(f[0]), int(f[1]), slices)` | Stores the three values of the thread: the run time in ns, the wait time in ns and the slice count. The key is a pair: the word `th` and the thread id. |
| 289 | `    def drop(self, tid):` | Starts the method `drop`. It stops tracking one thread of another process. |
| 290 | `        ent = self.foreign.pop(tid)` | Removes the entry from `foreign`. |
| 291 | `        ent[2].close()` | Closes its `schedstat` file. |
| 292 | `        ent[3].close()` | Closes its `stat` file. |
| 293 | `        self.prev.pop(("th", tid), None)` | Removes its last values from `prev`. So the thread does not appear in a later absolute line. |
| 295 | `    def scanner(self, first):` | Starts the method `scanner`, a generator. It looks once at all threads of the host and starts tracking those whose last CPU is the watched CPU. `first` is true for the scan before the first sample. |
| 296 | `        """A generator that walks all threads of the host once. It yields after every process,` | Description text: the generator walks all threads of the host once. It returns control to the caller after every process. |
| 297 | `        so that the caller can stop at a deadline. New threads on the CPU are tracked."""` | Continues the text: so the caller can pause the scan when the next sample is due. New threads on the watched CPU are tracked. |
| 298 | `        me = os.getpid()` | `me`: the process id of the sampler. |
| 299 | `        n = 0` | `n`: the number of threads looked at, 0 at first. |
| 300 | `        try:` | Starts the block whose error is caught. |
| 301 | `            pids = [d for d in os.listdir("/proc") if d.isdigit()]` | `pids`: the names in `/proc` that hold digits only. Each one is the id of a process. |
| 302 | `        except OSError:` | The folder `/proc` cannot be listed. |
| 303 | `            pids = []` | The list is empty in that case. |
| 304 | `        for name in pids:` | Starts the loop over the processes. |
| 305 | `            pid = int(name)` | The process id as a number. |
| 306 | `            if pid == self.pid or pid == me:` | Tests for the target and for the sampler itself. |
| 307 | `                continue` | Skips both. The method `target` reads the threads of the target. |
| 308 | `            try:` | Starts the block whose error is caught. |
| 309 | `                tids = os.listdir("/proc/%s/task" % name)` | `tids`: the thread ids of this process. |
| 310 | `            except OSError:` | The process has ended in the meantime. |
| 311 | `                continue` | Skips it. |
| 312 | `            for t in tids:` | Starts the loop over the threads of the process. |
| 313 | `                tid = int(t)` | The thread id as a number. |
| 314 | `                n += 1` | Counts the thread. |
| 315 | `                if tid in self.foreign:` | The thread is tracked already. |
| 316 | `                    continue` | Skips it. |
| 317 | `                path = "/proc/%s/task/%s/stat" % (name, t)` | `path`: the `stat` file of the thread. |
| 318 | `                try:` | Starts the block whose error is caught. |
| 319 | `                    fd = os.open(path, os.O_RDONLY)` | Opens the file for this one read. |
| 320 | `                    try:` | Starts a block with a cleanup. |
| 321 | `                        data = os.read(fd, 4096)` | Reads at most 4096 bytes of the file. |
| 322 | `                    finally:` | The cleanup runs in every case, also after an error of the read. |
| 323 | `                        os.close(fd)` | Closes the file. |
| 324 | `                except OSError:` | The thread has ended in the meantime, or the file cannot be read. |
| 325 | `                    continue` | Skips the thread. |
| 326 | `                comm, sf = stat_fields(data)` | Splits the content into the command name and the fields. |
| 327 | `                if comm is None or len(sf) <= 36 or int(sf[36]) != self.cpu or len(self.foreign) >= MAX_FOREIGN:` | Four reasons to skip the thread: the content could not be split, it has too few fields, the thread ran last on another CPU than the watched one (field 39), or `MAX_FOREIGN` threads (512) are tracked already. |
| 328 | `                    continue` | Skips the thread. |
| 329 | `                ent = [pid, clean(comm), Src("/proc/%s/task/%s/schedstat" % (name, t), True), Src(path, True)]` | Builds the entry of the new thread: the process id, the cleaned command name, and sources for its files `schedstat` and `stat`. |
| 330 | `                f = (ent[2].read() or b"").split()` | Reads its `schedstat` file once. |
| 331 | `                if len(f) != 3:` | The file does not give 3 fields. |
| 332 | `                    ent[2].close()` | Closes the file. |
| 333 | `                    continue` | Skips the thread. |
| 334 | `                self.foreign[tid] = ent` | Starts tracking the thread. |
| 335 | `                self.prev[("th", tid)] = (int(f[0]), int(f[1]), int(f[2]))` | Stores its three values as the start values. The first sample after this gives the differences to them. |
| 336 | `                if first:` | The scan before the first sample. |
| 337 | `                    self.out.write("# th tid=%d pid=%d comm=%s\n" % (tid, pid, ent[1]))` | Writes a header line `# th` with the thread id, the process id and the command name. |
| 338 | `                else:` | A later scan. |
| 339 | `                    self.events.append("th.%d.%s.new:=%s" % (tid, ent[1], f[2].decode()))` | Adds the state item `new:=` with the slice count of the thread. The next sample writes it. |
| 340 | `            yield False` | After each process: returns control to the caller with the value `False`. It means that the scan is not complete. |
| 341 | `        self.scan_count = n` | After the last process: stores the number of threads looked at. |
| 342 | `        yield True` | Returns control to the caller with the value `True`: the scan is complete. |

### `Watch.sample`: one sample and its output line (lines 344 to 391)

| Line | Source | Explanation |
|---:|---|---|
| 344 | `    # ---- one sample ----` | Comment: the code for one sample starts here. |
| 345 | `    def sample(self, t, with_irq, absolute, first):` | Starts the method `sample`. `t`: the sample time in ns. `with_irq`: read `/proc/interrupts` in this sample. `absolute`: write an absolute line too. `first`: this is the first sample. |
| 346 | `        """Returns (target alive, text of the line or None)."""` | Description text: the method returns whether the target is alive, and the text of the line. The text is `None` when there is nothing to write. |
| 347 | `        cur = {}` | `cur`: the values of this sample, empty at first. |
| 348 | `        alive = self.target(cur)` | Reads the threads of the target. `alive` is false when the target is gone. |
| 349 | `        self.cpu_line(cur)` | Reads the line of the watched CPU from `/proc/schedstat`. |
| 350 | `        self.softirq(cur)` | Reads the soft interrupt counts of the watched CPU. |
| 351 | `        self.foreign_sample(cur)` | Reads the tracked threads of other processes. |
| 352 | `        self.vm(cur)` | Reads the memory statistics. |
| 353 | `        if with_irq:` | Only in the samples that the caller selects, about twice per second. |
| 354 | `            self.irq(cur)` | Reads the hardware interrupt counts of the watched CPU. |
| 355 | `        items = self.events` | `items`: the items of the delta line. The list starts with the state items that were made before the comparison below. |
| 356 | `        self.events = []` | Empties the list of the object for the next sample. |
| 357 | `        prev = self.prev` | A short name for the last values. |
| 358 | `        for k, v in cur.items():` | Starts a loop over the values of this sample. |
| 359 | `            old = prev.get(k, v)` | `old`: the last value of the key. For a new key it is the value itself. |
| 360 | `            if isinstance(k, tuple):                     # a thread of another process` | A key that is a pair belongs to a thread of another process. |
| 361 | `                if v != old:` | Its values changed. |
| 362 | `                    base = "th.%d.%s." % (k[1], self.foreign[k[1]][1])` | The key prefix of the thread. |
| 363 | `                    for i, name in enumerate(("run_ns", "wait_ns", "slices")):` | Starts a loop over its three values. |
| 364 | `                        if v[i] != old[i]:` | Only a value that changed. |
| 365 | `                            items.append("%s%s=%d" % (base, name, v[i] - old[i]))` | Adds an item with the difference to the last sample, for example the ns that the thread ran in between. |
| 366 | `            elif k not in prev:` | A key that the sampler sees for the first time. |
| 367 | `                if not first:                            # a key that appeared after the first sample` | Not in the first sample. There every key is new, and the absolute line holds all of them. |
| 368 | `                    items.append("%s:=%s" % (k, "na" if v is None else v))` | Adds a state item with the full value, or with `na`. |
| 369 | `            elif v != old:` | A known key whose value changed. |
| 370 | `                if isinstance(v, int) and isinstance(old, int):` | Both values are whole numbers: the key is a counter. |
| 371 | `                    items.append("%s=%d" % (k, v - old))` | Adds an item with the difference: the new value minus the last value. |
| 372 | `                else:` | One of the two values is a text or `None`. |
| 373 | `                    items.append("%s:=%s" % (k, "na" if v is None else v))` | Adds a state item with the new value, or with `na`. |
| 374 | `            prev[k] = v` | Stores the value as the last value of the key. |
| 375 | `        line = None` | `line`: the text to write. `None` means nothing. |
| 376 | `        if absolute:` | An absolute line is due. |
| 377 | `            full = []` | `full`: its items, empty at first. |
| 378 | `            for k in sorted(prev, key=str):` | Starts a loop over all known keys, sorted by their text form. |
| 379 | `                v = prev[k]` | The last value of the key. |
| 380 | `                if isinstance(k, tuple):` | A thread of another process. |
| 381 | `                    if k[1] in self.foreign:` | Only when the thread is still tracked. |
| 382 | `                        base = "th.%d.%s." % (k[1], self.foreign[k[1]][1])` | Its key prefix. |
| 383 | `                        full += ["%s%s=%d" % (base, name, v[i]) for i, name in enumerate(("run_ns", "wait_ns", "slices"))]` | Adds three items with the full values of the thread. |
| 384 | `                elif not (k.startswith("irq.") and v == 0):` | Every other key, except an interrupt key whose count is 0. So an interrupt that never occurred on the watched CPU does not appear in the line. |
| 385 | `                    full.append("%s=%s" % (k, "na" if v is None else v))` | Adds the item with the full value, or with `na`. |
| 386 | `            line = "%d ABS %s\n" % (t, " ".join(full))` | Builds the absolute line: the sample time, the word `ABS` and all items, with one blank between them. |
| 387 | `        if items and not first:                          # the first line of the file is the absolute line` | A delta line is due: at least one item exists, and this is not the first sample. |
| 388 | `            line = "%d %s\n%s" % (t, " ".join(items), line or "")` | Builds the delta line: the sample time and the items. When the same sample has an absolute line, that line follows. |
| 389 | `        return alive, line` | Returns the state of the target and the text. |

### `main`: options, header lines and the first scan (lines 392 to 426)

| Line | Source | Explanation |
|---:|---|---|
| 392 | `def main():` | Starts the function `main`. |
| 393 | `    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])` | Creates the reader of the command line. Its description is the first line of the text of lines 2 to 45. |
| 394 | `    ap.add_argument("--pid", type=int, required=True)` | The option `--pid`: the process id of the target, a whole number. It is required. |
| 395 | `    ap.add_argument("--cpu", type=int, required=True)` | The option `--cpu`: the number of the watched CPU. It is required. |
| 396 | `    ap.add_argument("--out", required=True)` | The option `--out`: the path of the output file. It is required. |
| 397 | `    ap.add_argument("--hz", type=float, default=20.0)` | The option `--hz`: the number of samples per second, 20 when it is not given. |
| 398 | `    ap.add_argument("--max-s", type=float, default=120.0)` | The option `--max-s`: the longest time of the sampling in seconds, 120 when it is not given. |
| 399 | `    a = ap.parse_args()` | Reads the command line. A missing or wrong option prints the usage and ends the program with exit status 2. |
| 400 | `    if a.pid < 1 or a.cpu < 0 or not 0.1 <= a.hz <= 1000 or a.max_s <= 0:` | Checks the values: the process id is at least 1, the CPU number is 0 or more, the sample rate lies from 0.1 to 1000 per second, and the time limit is above 0. |
| 401 | `        ap.error("--pid above 0, --cpu 0 or above, --hz from 0.1 to 1000, --max-s above 0")` | A wrong value prints the usage and this message, and ends the program with exit status 2. |
| 402 | `    signal.signal(signal.SIGTERM, on_signal)` | From now on the signal SIGTERM calls `on_signal`. The run script ends the sampler with this signal. |
| 403 | `    signal.signal(signal.SIGINT, on_signal)` | The same for SIGINT, the signal of Ctrl-C. |
| 404 | `    out = open(a.out, "w", buffering=1 << 16)` | Opens the output file for writing. An old file with this name is emptied. The file object collects up to 65536 bytes before it writes them to the file. |
| 405 | `    w = Watch(a.pid, a.cpu, out)` | Creates the `Watch` object for the target and the watched CPU. |
| 406 | `    period = int(1e9 / a.hz)` | `period`: the time between two samples in ns. At 20 samples per second it is 50000000 ns, that is 50 ms. |
| 407 | `    irq_every = max(1, int(round(a.hz / 2)))` | `irq_every`: `/proc/interrupts` is read in every sample whose number is a multiple of this value. The value is half the sample rate, at least 1. So the file is read about twice per second: in every 10th sample at 20 samples per second. |
| 408 | `    samples = missed = max_us = errors = 0` | Start values of four counters: the samples taken, the sample slots skipped, the longest sample in microseconds, and the errors. |
| 409 | `    reason = "pid_gone"` | `reason`: the end reason for the footer line. It starts as `pid_gone`. That is the case in which the loop ends when the target is gone. |
| 410 | `    status = 0` | `status`: the exit status. It is 0 unless an error outside a sample changes it. |
| 411 | `    try:` | Starts the block that the handlers of lines 476 to 480 and the cleanup of lines 481 to 485 belong to. |
| 412 | `        t0 = mono()` | `t0`: the clock before the header is written. |
| 413 | `        out.write("# hostwatch v1 pid=%d cpu=%d hz=%g max_s=%g\n" % (a.pid, a.cpu, a.hz, a.max_s))` | Writes the first header line: the format version `v1`, the process id of the target, the watched CPU, the sample rate and the time limit. `%g` prints a number in its shortest form, so 20.0 becomes `20`. |
| 414 | `        out.write("# clocks mono_ns=%d boot_ns=%d real_ns=%d\n" % (t0, clock_ns(CLOCK_BOOTTIME), clock_ns(time.CLOCK_REALTIME)))` | Writes the second header line: `t0` on `CLOCK_MONOTONIC`, then the clock that counts from the boot and the time of day. The last two are read at this moment. All three are in ns. |
| 415 | `        comm, sf = stat_fields(Src("/proc/%d/stat" % a.pid).read())` | Reads the file `stat` of the target once and splits it. |
| 416 | `        out.write("# target starttime_ticks=%s clk_tck=%d comm=%s\n" % (` | Starts the third header line, about the target. The values follow in line 417. |
| 417 | `            sf[19] if sf and len(sf) > 19 else "na", os.sysconf("SC_CLK_TCK"), clean(comm) if comm else "na"))` | The values: field 22 of the `stat` file, the start time of the process in clock ticks after the boot [Ref2]. Then the number of clock ticks per second, from `os.sysconf`. Then the cleaned command name. `na` stands for a value that could not be read. |
| 418 | `        out.write("# sampler pid=%d allowed_cpus=%s\n" % (os.getpid(), ",".join(map(str, sorted(os.sched_getaffinity(0))))))` | Writes the fourth header line: the process id of the sampler and its CPU list. `os.sched_getaffinity(0)` gives the CPUs on which this process may run. They are sorted and joined with commas. The line shows whether the caller pinned the sampler. |
| 419 | `        for _ in w.scanner(True):` | Runs the first scan of all threads of the host to its end, without a pause. |
| 420 | `            pass` | The loop body does nothing. The scan writes its `# th` lines itself. |
| 421 | `        out.write("# scan threads=%d on_cpu=%d took_ms=%.1f\n" % (w.scan_count, len(w.foreign), (mono() - t0) / 1e6))` | Writes the scan line: the number of threads looked at, the number of threads that are tracked now, and the time from `t0` to this moment in ms with one decimal place. That time also holds the writing of the header lines. |
| 422 | `        out.flush()` | Writes the header to the file now. |
| 423 | `        t0 = mono()` | Sets `t0` again. From here it is the start of the sample grid: the sample slots lie at `t0` plus a whole number of periods. |
| 424 | `        last_abs = last_scan = last_flush = t0` | Start values of three times: the last absolute line, the start of the last scan and the last write to the file. |
| 425 | `        slot = 0` | `slot`: the number of the grid slot that the loop planned last. |
| 426 | `        first = True` | `first`: true until the first sample is taken. |

### `main`: the sampling loop, the end reasons and the footer line (lines 427 to 490)

| Line | Source | Explanation |
|---:|---|---|
| 427 | `        while True:` | Starts the sampling loop. Each turn takes one sample. |
| 428 | `            t = mono()` | `t`: the time of this sample. The clock is read once, before the files are read. Every item of the sample carries this one time. |
| 429 | `            if t - t0 >= a.max_s * 1e9:` | Tests whether the time limit `--max-s` is over, counted from the start of the grid. |
| 430 | `                reason = "max_s"` | If so: the end reason is `max_s`. |
| 431 | `                break` | Leaves the loop. |
| 432 | `            absolute = first or t - last_abs >= ABS_PERIOD_NS` | `absolute`: this sample writes an absolute line. That is the case in the first sample, and when 5 s have passed after the last absolute line. |
| 433 | `            try:` | Starts the block whose errors are caught. |
| 434 | `                alive, line = w.sample(t, samples % irq_every == 0, absolute, first)` | Takes the sample. The second argument is true in every sample whose number is a multiple of `irq_every`. |
| 435 | `            except Stop:` | A signal arrived during the sample. |
| 436 | `                raise` | Passes it on to the handler of line 476. |
| 437 | `            except Exception as e:           # an error must not end the sampling, and must not pass as "pid_gone"` | Any other error in a sample. By the comment it must not end the sampling, and it must not look like the end of the target. |
| 438 | `                errors += 1` | Counts the error. |
| 439 | `                alive, line = os.path.exists("/proc/%d" % a.pid), "%d hw.error:=%s\n" % (t, clean(type(e).__name__))` | In place of the sample: `alive` is true when the folder of the target still exists under `/proc`. The line holds the sample time and the item `hw.error:=` with the type name of the error. |
| 440 | `            first = False` | The first sample is done. |
| 441 | `            if absolute:` | When this sample was an absolute one. |
| 442 | `                last_abs = t` | Stores its time as the time of the last absolute line. |
| 443 | `            if line:` | When the sample gave a text. |
| 444 | `                out.write(line)` | Writes it to the output file object. |
| 445 | `            samples += 1` | Counts the sample. |
| 446 | `            done = mono()` | `done`: the clock after the sample. |
| 447 | `            max_us = max(max_us, (done - t) // 1000)` | Keeps the longest time of one sample in microseconds, for the footer line. |
| 448 | `            if not alive:` | The target is gone. |
| 449 | `                break` | Leaves the loop. The end reason stays `pid_gone`. |
| 450 | `            if done - last_flush >= 10 ** 9:` | When 1 s has passed after the last write to the file. |
| 451 | `                out.flush()` | Writes the collected lines to the file. |
| 452 | `                last_flush = done` | Stores the time of this write. |
| 453 | `            # The next slot on the fixed grid t0 + k x period.` | Comment: the next sample is taken at the next slot of a fixed grid: `t0` plus a whole number of periods. |
| 454 | `            nxt = (done - t0) // period + 1` | `nxt`: the number of the first grid slot after this moment. |
| 455 | `            deadline = t0 + nxt * period` | `deadline`: the time of that slot. |
| 456 | `            # A part of the host scan, in the time that is left before the next sample.` | Comment: the time that is left before the next sample is used for a part of the scan of the host. |
| 457 | `            if w.scan is None and done - last_scan >= SCAN_PERIOD_NS:` | When no scan runs and 2 s have passed after the start of the last one. |
| 458 | `                w.scan, last_scan = w.scanner(False), done` | Starts a new scan and stores its start time. |
| 459 | `            while w.scan is not None and mono() < deadline - period // 4:` | Runs the scan in pieces. The loop goes on while a scan is active and more than a quarter of a period is left before the deadline. |
| 460 | `                try:` | Starts the block whose errors are caught. |
| 461 | `                    if next(w.scan):` | Runs the scan for one more process. The value is true when the scan is complete. |
| 462 | `                        w.scan = None` | A complete scan is removed. |
| 463 | `                except Stop:` | A signal arrived during the scan. |
| 464 | `                    raise` | Passes it on. |
| 465 | `                except Exception as e:       # this scan ends; the next one starts after 2 s` | Any other error in the scan. By the comment this scan ends, and the next one starts when its 2 s are over. |
| 466 | `                    errors += 1` | Counts the error. |
| 467 | `                    w.scan = None` | Ends this scan. |
| 468 | `                    w.events.append("hw.error:=scan_%s" % clean(type(e).__name__))` | Adds a state item `hw.error:=scan_` with the type name of the error. The next sample writes it. |
| 469 | `            if nxt > slot + 1:` | Tests whether at least one grid slot passed without a sample. |
| 470 | `                missed += nxt - slot - 1` | Adds the number of skipped slots to `missed`. |
| 471 | `                w.events.append("hw.missed:=%d" % missed)` | Adds a state item `hw.missed:=` with the total. The next sample writes it. |
| 472 | `            slot = nxt` | Stores the slot of the next sample. |
| 473 | `            wait = deadline - mono()` | `wait`: the ns that are left to the deadline. |
| 474 | `            if wait > 0:` | Only when time is left. |
| 475 | `                time.sleep(wait / 1e9)` | Sleeps until the deadline. `time.sleep` takes seconds, so the ns are divided by 1e9. |
| 476 | `    except Stop:` | The handler for a signal, from the header, a sample, a scan or the sleep. |
| 477 | `        reason = "signal"` | The end reason is `signal`. The exit status stays 0. |
| 478 | `    except Exception as e:                   # an error outside a sample (header, first scan, output file)` | The handler for every other error that reaches this place. By the comment these are errors outside a sample: in the header, in the first scan or at the output file. |
| 479 | `        reason, status = "error", 1` | The end reason is `error`, and the exit status is 1. |
| 480 | `        sys.stderr.write("hostwatch: %s: %s\n" % (type(e).__name__, e))` | Prints the type and the text of the error to the error output. |
| 481 | `    finally:` | The cleanup. It runs in every case, after the loop or after a handler. |
| 482 | `        signal.signal(signal.SIGTERM, signal.SIG_IGN)` | From now on SIGTERM is ignored. So a late signal cannot stop the writing of the footer line. |
| 483 | `        signal.signal(signal.SIGINT, signal.SIG_IGN)` | The same for SIGINT. |
| 484 | `        out.write("# end reason=%s samples=%d missed=%d max_sample_us=%d errors=%d\n" % (reason, samples, missed, max_us, errors))` | Writes the footer line: the end reason, the number of samples, the number of skipped slots, the longest sample in microseconds and the number of errors. The run script looks for this line. A file without it means that the sampler did not end normally. |
| 485 | `        out.close()` | Writes the rest of the collected lines and closes the file. |
| 486 | `    return status` | Returns the exit status to the caller. |
| 489 | `if __name__ == "__main__":` | True when the file is run as a program, and false when it is loaded as a module. |
| 490 | `    sys.exit(main())` | Runs `main` and ends the program with its return value as the exit status. |

## References

- [Ref1] external source: Linux kernel documentation, page "Scheduler Statistics" (https://docs.kernel.org/scheduler/sched-stats.html). It gives the 9 values of a CPU line of `/proc/schedstat` and the 3 values of the file `schedstat` of a process.
- [Ref2] external source: Linux manual page `proc_pid_stat(5)` (https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html). It gives the numbered fields of the file `stat` of a process: 3 state, 10 minor faults, 12 major faults, 14 user time, 15 system time, 22 start time, 39 last CPU.
