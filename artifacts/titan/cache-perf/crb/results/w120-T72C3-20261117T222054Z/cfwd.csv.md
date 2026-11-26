# `cfwd.csv` explained: part C, session 3 (spec file cfwd.spec)

## Short version

This file is the output of one process of the runner `bwx12` at 120 threads: part C, session 3 (spec file cfwd.spec) of the whole-chip rerun at 7200 MT/s of 2026-11-17.
The process timed the kernel sequence `oldread`, `read`, `asmread`, 2 times (6 intervals).
Summed over the 120 thread rows of each interval, in GB/s (GB = 1e9 bytes): the old read kernel (`oldread`) gave 467.83 and 467.49, the new read kernel (`read`) gave 322.02 and 324.98, `asmread` (a hand-written load-only loop) gave 322.07 and 323.41.

## This file

- File: `cfwd.csv` in this folder (`crb/results/w120-T72C3-20261117T222054Z`).
- Size: 2299 lines, 170613 bytes. sha256 when this page was built: `8b32b72d5d89ecdbfca144d14dc5eb8ea05c29d7a1e5c19146c1f769e5ce7a8a`.
- Written by: the runner `bwx12` (its standard output). The script `rx.sh` started it and named the file after the tag `cfwd` of the spec file.
- Step of the run: part C, session 3 (spec file cfwd.spec), folder tag `T72C3`.

## What this file holds

| Round | Position | Kernel | Which kernel | Line of the I row | Thread rows | Sum over the thread rows, GB/s | `aggregate_GBps` of the I row, GB/s | Thread rows with a flag |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | `oldread` | old read kernel | 128 | 120 | 467.83 | 467.83 | 0 |
| 0 | 1 | `read` | new read kernel | 490 | 120 | 322.02 | 322.02 | 0 |
| 0 | 2 | `asmread` | asmread (hand-written load-only loop) | 852 | 120 | 322.07 | 322.06 | 0 |
| 1 | 0 | `oldread` | old read kernel | 1214 | 120 | 467.49 | 467.49 | 0 |
| 1 | 1 | `read` | new read kernel | 1576 | 120 | 324.98 | 324.97 | 0 |
| 1 | 2 | `asmread` | asmread (hand-written load-only loop) | 1938 | 120 | 323.41 | 323.40 | 0 |

- One row of the table is one timed interval: one kernel, timed once, on all threads.
- "Sum over the thread rows" is the sum over the T rows of the interval of bytes / elapsed_s / 1e9. This is the rate that the analysis of the rerun uses.
- "`aggregate_GBps` of the I row" is the rate that `bwx12` itself printed for the interval.
- "Thread rows with a flag" counts the T rows whose last field is not `-`.
- This table was computed from the file with the parser of `stat_bwx.py`.
- Lines of each kind in this file: 6 `# header`, 7 `# page_read`, 720 `C`, 6 `I`, 840 `P`, 720 `T`.

## The header lines and the first row of each kind (copied from the file by a script)

The number at the left is the line number in the file.

```text
  1  # bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; threads=120 bytes_per_thread=268435456 min_ms=6000 thp=madvise
  2  # bwx: seq=oldread,read,asmread rounds=2 stop=common start=common two_buffers=0 count=1 kernels=aarch64; round and pos count from 0; times are seconds since process start
  3  # I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps
  4  # T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags
  5  # P,round,pos,tid,buffer,kB_total,kB_huge,thp_fault_alloc,thp_fault_fallback,thp_collapse_alloc,pgmigrate_success
  6  # C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns,cbusy0,cbusy1,cbusy2,cbusy3,cbusy_mt,bus_access; pmu_type=11 codes=0x198,0x199,0x19a,0x19b,0x19c,0x19
  7  P,0,-1,0,a,262144,262144,1671327,0,2,0
127  # page_read,0,-1,4.826 ms
128  I,0,0,oldread,268435456,120,2807071506432,6.000258,467.83
129  T,0,0,oldread,0,0,29408362496,6.000067,0.399948,0.399961,6.400028,109.555,-
249  C,0,0,oldread,0,0,5998822008,5998822008,5986581232,265947327,675730933,127364604,533458910,1118051598,954742824
```

The sections below explain the file type. The same text stands in the companion of every file of this type.

This text explains one file format. It holds for the 9 files listed under "What this file is".

## The file type in short

Each file is the standard output of one process of bwx12 (the runner program that times a sequence of kernels, here read kernels on 120 threads). For each timed interval of 6 s the file holds 1 summary row (I), 120 thread rows (T), 120 counter rows (C) and 120 page state rows (P). The analysis computes its rate from the T rows as the sum over the threads of bytes / elapsed_s / 1e9, and it uses the column `aggregate_GBps` of the I row only for a comparison with that sum.

"Kernel" in this text means the inner loop of the benchmark that reads memory. It never means the Linux kernel.

Folder letters used below:

| Letter | Folder |
|---|---|
| `R` | `/home/jhan/workspace/titan/cache-perf/crb/results`. It holds the copies of the result folders of CRB. On CRB the folder was `~/cache-perf/results` |
| `S` | `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17` |
| `BWX12` | `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15` |
| `W15` | `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15` |

## What this file is

- **Writer.** The runner script `rx.sh` starts one bwx12 process per line of a spec file (a file with lines of the form `tag|arguments`). It sends the standard output of the process to `<tag>.csv` in a new result folder `R/w120-<name>-<UTC time>` [Ref1]. So every line of the file comes from bwx12, and one file is one process.
- **File names.** The tag of the spec line gives the file name: `a6456` in `like.spec`, `cfwd` in `cfwd.spec`, `crev` in `crev.spec` [Ref2].
- **Step of the run.** The driver script `go.sh` ran 3 sessions. In each session it ran part A, then part L (`like.spec`), then part C (`cfwd.spec`, or `crev.spec` in session 2). After session 3 it ran one more part C process with `crev.spec`. Later the script `go2.sh` ran the line of `like.spec` 2 more times. These 2 processes are control I [Ref4].
- **Arguments.** The 9 processes had the same arguments apart from the kernel sequence `--seq` [Ref2]:
  - `--threads 120 --cpus 0-63,64-119`: 120 threads. Thread i is pinned to CPU i.
  - `--bytes 256M`: each thread has its own buffer of 256 MiB (268435456 bytes).
  - `--stop common --min-ms 6000`: all threads of an interval stop at a common deadline. The deadline is 6000 ms after a common start time.
  - `--start common`: every thread starts each interval at offset 0 of its buffer.
  - `--rounds 2`: the kernel sequence runs 2 times.
  - `--count --pmu-type 11 --events ...`: each thread counts 6 hardware events, and the file gets C rows.
- **One row per what.** One I row per interval. One T row and one C row per thread and interval. One P row per thread and page state reading. A page state reading happens once before the first interval and once after each interval.
- **Standard error.** `rx.sh` appends the error messages of bwx12 to `stderr.txt` in the same folder [Ref1]. This file is empty (0 bytes) in the 9 folders.

The 9 instances:

| No. | File | Part of the run | Kernel sequence (`seq=` in line 2) | Lines | Bytes |
|---|---|---|---|---|---|
| 1 | `R/w120-T72L1-20261117T221329Z/a6456.csv` | part L, session 1 | oldread, asmread, read_nop96, read_nop256, read_1pl | 3747 | 286889 |
| 2 | `R/w120-T72L2-20261117T221638Z/a6456.csv` | part L, session 2 | the same | 3747 | 288214 |
| 3 | `R/w120-T72L3-20261117T221947Z/a6456.csv` | part L, session 3 | the same | 3747 | 288275 |
| 4 | `R/w120-T72I1-20261117T222700Z/a6456.csv` | control I, process 1 | the same | 3747 | 288218 |
| 5 | `R/w120-T72I2-20261117T223227Z/a6456.csv` | control I, process 2 | the same | 3747 | 288216 |
| 6 | `R/w120-T72C1-20261117T221436Z/cfwd.csv` | part C, session 1 | oldread, read, asmread | 2299 | 169773 |
| 7 | `R/w120-T72C3-20261117T222054Z/cfwd.csv` | part C, session 3 | oldread, read, asmread | 2299 | 170613 |
| 8 | `R/w120-T72C2-20261117T221745Z/crev.csv` | part C, session 2 | asmread, read, oldread | 2299 | 170613 |
| 9 | `R/w120-T72C4-20261117T222136Z/crev.csv` | part C, extra process after session 3 | asmread, read, oldread | 2299 | 170681 |

Layout of every file:

```
lines 1-6     header lines, each starts with "#"
lines 7-126   120 P rows with round 0, pos -1
line 127      "# page_read,0,-1,..."
then one block of 362 lines per interval, in the order
round 0 pos 0, round 0 pos 1, ..., round 1 last pos:
    1 I row
  120 T rows   (tid 0 to 119)
  120 C rows   (tid 0 to 119)
  120 P rows   (tid 0 to 119)
    1 "# page_read" line
```

- `a6456.csv`: 5 kernels x 2 rounds = 10 intervals. 6 + 121 + 10 x 362 = 3747 lines.
- `cfwd.csv` and `crev.csv`: 3 kernels x 2 rounds = 6 intervals. 6 + 121 + 6 x 362 = 2299 lines.

## Line kinds

| Kind | How to recognise it | Lines per file: `a6456.csv` / `cfwd.csv`, `crev.csv` | What it holds |
|---|---|---|---|
| Header line 1 | starts with `# bandwidth:` | 1 / 1 | the unit GB, the formula of `aggregate_GBps`, thread count, buffer size, interval length, huge page request |
| Header line 2 | starts with `# bwx:` | 1 / 1 | kernel sequence, rounds, stop rule, start rule, counter switch |
| Column name lines | start with `# I,`, `# T,`, `# P,`, `# C,` (lines 3 to 6) | 4 / 4 | the column names of the 4 row kinds. The `# C` line also holds the PMU type number and the event codes |
| P row | starts with `P,` | 1320 / 840 | page state of the buffer of one thread at one reading |
| Page read line | starts with `# page_read,` | 11 / 7 | the time that one page state reading took |
| I row | starts with `I,` | 10 / 6 | one interval: totals over the 120 threads |
| T row | starts with `T,` | 1200 / 720 | one thread in one interval: bytes and clock times |
| C row | starts with `C,` | 1200 / 720 | one thread in one interval: counter values |

- The 9 files together hold 74 I rows, 8880 T rows, 8880 C rows, 9960 P rows and 83 page read lines.
- `stat_bwx.py` and `facts_data.py` take header fields from lines that start with `#`. They read nothing else from such lines. No analysis script uses the time of a page read line.
- bwx12.c has a second mode (trial mode) that prints other row kinds: S, W, B, E, X, TR, M, K [Ref15]. The 9 files hold none of them.

## Columns

Column numbers count from 1. Column 1 is the letter of the row kind. The analysis scripts split a row at the commas into a list `p`, so column n is `p[n-1]`.

### Columns `round` and `pos` (in every row kind)

- `round`: the repeat of the kernel sequence, counted from 0. With `--rounds 2` the values are 0 and 1.
- `pos`: the place of the kernel in the sequence, counted from 0. The values are 0 to 4 in `a6456.csv` and 0 to 2 in `cfwd.csv` and `crev.csv`.
- `pos` = -1 occurs only in P rows and page read lines, and only with round 0. It marks the page state reading before the first interval. At that time each thread has allocated its buffer and has written it once, and no kernel of the sequence has run [Ref5].
- A P row or page read line with `pos` 0 or higher holds the state after the interval with that round and pos [Ref10].

### Header lines 1 and 2

```
# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; threads=120 bytes_per_thread=268435456 min_ms=6000 thp=madvise
# bwx: seq=oldread,asmread,read_nop96,read_nop256,read_1pl rounds=2 stop=common start=common two_buffers=0 count=1 kernels=aarch64; round and pos count from 0; times are seconds since process start
```

Sample: lines 1 to 2 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
# bwx: seq=asmread,read,oldread rounds=2 stop=common start=common two_buffers=0 count=1 kernels=aarch64; round and pos count from 0; times are seconds since process start
```

Sample: line 2 of `R/w120-T72C4-20261117T222136Z/crev.csv`.

Line 1 is the same text in all 9 files. Line 2 differs only in `seq=`. bwx12 prints both lines once, before the first interval [Ref3].

| Field | Line | Meaning |
|---|---|---|
| `GB = 1e9 bytes` | 1 | 1 GB is 1 000 000 000 bytes. GB/s is the unit of `aggregate_GBps` |
| `aggregate_GBps = sum(bytes) / max(per-thread elapsed_s)` | 1 | the formula of column 9 of the I row |
| `copy counts read+write bytes` | 1 | a rule for copy kernels. The sequences of the 9 files hold read kernels only |
| `threads=120` | 1 | the value of `--threads` |
| `bytes_per_thread=268435456` | 1 | the value of `--bytes` in bytes (256 MiB) |
| `min_ms=6000` | 1 | the value of `--min-ms`. With the common stop it is the time from the common start to the deadline, in ms |
| `thp=madvise` | 1 | bwx12 asked Linux for huge pages for each buffer with `madvise(MADV_HUGEPAGE)`. The other value is `nohugepage` (option `--no-thp`) [Ref8] |
| `seq=` | 2 | the kernel sequence of `--seq`. Entry k of the list (counted from 0) runs at pos k |
| `rounds=2` | 2 | the value of `--rounds` |
| `stop=common` | 2 | the stop rule: common stop. The other value is `pass` |
| `start=common` | 2 | every thread starts at offset 0 of its buffer. The other value is `offset` |
| `two_buffers=0` | 2 | each thread has one buffer (buffer `a`). 1 would mean a second buffer `b` |
| `count=1` | 2 | `--count` was given. The file has C rows |
| `kernels=aarch64` | 2 | the binary holds the real Arm kernels. On another processor type the source builds plain C loops in their place (the source calls them stand-ins) and prints a warning here [Ref3] |

### I row: one interval (9 fields)

```
I,0,0,oldread,268435456,120,2773875687424,6.000276,462.29
```

Sample: line 128 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
I,1,2,oldread,268435456,120,2784046874624,6.000297,463.98
```

Sample: line 1938 of `R/w120-T72C4-20261117T222136Z/crev.csv`.

| Col | `p[]` | Name | Unit | Meaning |
|---|---|---|---|---|
| 1 | 0 | (row kind) | - | the letter `I` |
| 2 | 1 | `round` | count from 0 | repeat of the sequence |
| 3 | 2 | `pos` | count from 0 | place of the kernel in the sequence |
| 4 | 3 | `kernel` | name | name of the kernel that this interval timed |
| 5 | 4 | `bytes_per_thread` | bytes | size of the buffer range that the kernel works on. Here it is the whole buffer, 268435456 bytes |
| 6 | 5 | `threads` | count | the value of `--threads`: the number of threads that run the kernel (120) |
| 7 | 6 | `total_bytes` | bytes | sum of the column `bytes` of the 120 T rows of this interval |
| 8 | 7 | `max_elapsed_s` | s, 6 decimals | the longest elapsed time (`t_end` - `t_start`) of a thread in this interval |
| 9 | 8 | `aggregate_GBps` | GB/s, 2 decimals | `total_bytes` divided by the longest elapsed time |

How bwx12 computes `aggregate_GBps` [Ref6]:

```
total  = sum over the 120 threads of bytes          (bytes)
max_el = largest (t_end - t_start) of the 120       (whole ns)
aggregate_GBps = total / max_el                     (bytes per ns)
```

- 1 byte per ns is 1e9 bytes per s. So the quotient is in GB/s without a further factor.
- bwx12 prints the quotient with 2 decimals (steps of 0.01 GB/s).
- Example with line 128 of instance 1: 2773875687424 bytes / 6.000276 s / 1e9 = 462.29 GB/s.

### T row: one thread in one interval (13 fields)

```
T,0,0,oldread,0,0,28934406144,6.000122,0.409142,0.409156,6.409277,107.789,-
```

Sample: line 129 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
T,0,0,asmread,0,0,16601055232,6.000213,0.417584,0.417596,6.417809,61.844,-
```

Sample: line 129 of `R/w120-T72C4-20261117T222136Z/crev.csv`.

| Col | `p[]` | Name | Unit | Meaning |
|---|---|---|---|---|
| 1 | 0 | (row kind) | - | the letter `T` |
| 2 | 1 | `round` | count from 0 | repeat of the sequence |
| 3 | 2 | `pos` | count from 0 | place of the kernel in the sequence |
| 4 | 3 | `kernel` | name | name of the kernel |
| 5 | 4 | `tid` | index, 0 to 119 | the number of the thread inside the process. It is not the thread id of Linux |
| 6 | 5 | `cpu` | CPU number | the CPU that the thread pinned itself to. Thread i gets entry i of the `--cpus` list. In the 9 files `cpu` equals `tid` in every row |
| 7 | 6 | `bytes` | bytes | the bytes that the thread counted in the interval. The thread adds 2097152 (one chunk of 2 MiB) after each kernel call |
| 8 | 7 | `elapsed_s` | s, 6 decimals | `t_end` - `t_start` of this thread |
| 9 | 8 | `t_sched_s` | s since process start | the common start time that `main()` set for the interval. It is the same in the 120 rows of an interval |
| 10 | 9 | `t_start_s` | s since process start | the clock value that the thread read directly before its first timed kernel call. The warm-up pass ends before this clock read |
| 11 | 10 | `t_end_s` | s since process start | the clock value that the thread read after its last chunk |
| 12 | 11 | `passes` | passes, 3 decimals | `bytes` / `bytes_per_thread`: how many times the thread went through its buffer |
| 13 | 12 | `flags` | text | `late` when the thread started more than 100 us (microseconds) after `t_sched`. Otherwise `-` |

What a T row times, and what it does not time [Ref7]:

- **Clock.** Every time comes from `clock_gettime(CLOCK_MONOTONIC)` in whole ns. "Process start" is the clock value that the first statement of `main()` read [Ref9].
- **Not timed: setup.** Before the first interval each thread pins itself to its CPU, allocates its buffer and writes the whole buffer once.
- **Not timed: warm-up pass.** Before each interval each thread runs the kernel once over its whole buffer.
- **Common start.** `main()` waits until all threads have finished the warm-up pass. It then sets `t_sched` to the clock value plus 2 ms. It sets the deadline to `t_sched` + 6 s.
- **Start of a thread.** Each thread waits in a loop that reads the clock until `t_sched`. Then it reads its counters (the start values of the C row). Then it reads the clock. This value is `t_start`.
- **Timed work.** The thread calls the kernel on one chunk of 2 MiB, adds 2097152 to `bytes`, and reads the clock. It repeats this until a clock value is at or after the deadline. That clock value is `t_end`. The chunks follow each other through the buffer. After the last chunk of the buffer the next chunk starts at offset 0. The clock reads between the chunks lie inside the timed window.
- **Result.** `bytes` and `elapsed_s` of one T row belong to the same time window of one thread. Each thread finishes the chunk that it is in when the deadline comes.
- **Main thread, and when the rows are printed.** The process has 121 threads: the 120 threads of the T rows and the main thread that runs `main()`. The main thread is not pinned to one CPU. It may run on CPUs 0 to 119 only, the CPUs of the 120 threads. During a timed interval it waits in `pthread_barrier_wait` (a call that returns when all 120 threads have finished the interval). It prints the I, T and C rows of an interval after that call returns. It prints the P rows and the page read line after the page state reading. At that time the threads run the warm-up pass of the next interval, when there is one. `main()` sets the next common start only after these prints [Ref10]. So no row is printed during a timed interval [Ref22].
- **The runner script during a timed interval.** While the bwx12 process runs, the shell of `rx.sh` repeats three steps about once per second. It tests whether the process still exists. It tests whether the marker file `/tmp/positron-perf.RUNNING` exists (when it exists, `rx.sh` kills the process and ends). It starts one `sleep 1` process [Ref1]. So these steps also run during the timed intervals. `rx.sh` sets a CPU list (the CPUs on which Linux may run a process) only for the bwx12 process. Its own shell and the `sleep` processes keep the CPU list of the script that started `rx.sh` [Ref26]. The log of `go.sh` records the CPU list 0-119 for the shell of `go.sh` [Ref25]. These are the CPUs of the 120 threads. The log of `go2.sh` records no CPU list. `Insufficient data: how much time these steps took from a thread during a timed interval. A scheduler record of the threads during a run would resolve it.`
- **`bytes` counts buffer ranges, not loads.** The thread counts the full size of every chunk for every kernel. The kernel `read_1pl` loads only 16 bytes of each 64-byte line, and its chunks still count as 2097152 bytes [Ref11].

Values found in the 9 files (8880 T rows, 74 intervals):

- `elapsed_s` lies between 5.999979 s and 6.000457 s.
- The elapsed times of the 120 threads of one interval differ by at most 0.000454 s.
- `t_start_s` - `t_sched_s` lies between 0.000002 s and 0.000034 s. The limit for the flag `late` is 0.000100 s.
- `flags` is `-` in all 8880 rows.
- `t_sched_s` of the first interval lies between 0.396 s and 0.464 s (rounded to 0.001 s).
- From the last `t_end_s` of an interval to `t_sched_s` of the next interval the time is between 0.064 s and 0.140 s (rounded to 0.001 s). The page state reading, the warm-up pass of the next kernel and the 2 ms that `main()` adds to the clock value for the common start happen in this time.

### P row: page state of one buffer at one reading (11 fields)

```
P,0,-1,0,a,262144,262144,611480,0,2,0
```

Sample: line 7 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
P,0,-1,0,a,262144,262144,1686688,0,2,0
```

Sample: line 7 of `R/w120-T72C4-20261117T222136Z/crev.csv`.

| Col | `p[]` | Name | Unit | Meaning |
|---|---|---|---|---|
| 1 | 0 | (row kind) | - | the letter `P` |
| 2 | 1 | `round` | count from 0 | round of the interval that ended before the reading. 0 for the reading before the first interval |
| 3 | 2 | `pos` | count from 0, or -1 | pos of the interval that ended before the reading. -1: the reading before the first interval |
| 4 | 3 | `tid` | index, 0 to 119 | the thread that owns the buffer |
| 5 | 4 | `buffer` | letter | `a` is the buffer that the read kernels read. `b` exists only with two buffers. The 9 files hold `a` only |
| 6 | 5 | `kB_total` | kB (1024 bytes) | the line `Size:` of the entry of this buffer in `/proc/self/smaps` (the Linux file that lists the memory ranges of the process) |
| 7 | 6 | `kB_huge` | kB (1024 bytes) | the line `AnonHugePages:` of the same entry. The facts sheet interprets it as the part of the buffer that lies on 2 MiB pages [Ref17] |
| 8 | 7 | `thp_fault_alloc` | count | the value with this name in `/proc/vmstat` (a Linux file with counters of the memory system) |
| 9 | 8 | `thp_fault_fallback` | count | the value with this name in `/proc/vmstat` |
| 10 | 9 | `thp_collapse_alloc` | count | the value with this name in `/proc/vmstat` |
| 11 | 10 | `pgmigrate_success` | count | the value with this name in `/proc/vmstat` |

- **Which smaps entry.** bwx12 takes the entry whose start address is the buffer address and whose length is the buffer size, rounded up to a multiple of 2 MiB [Ref12]. Here that length is 256 MiB.
- **Columns 8 to 11 count for the whole system.** They are not per thread and not per process. bwx12 reads `/proc/vmstat` once per reading and prints the same 4 values in all 120 rows [Ref12].
- **`NA`.** bwx12 prints `NA` in place of a value that it could not read. The 9 files hold no `NA`.
- **When the reading happens.** `main()` reads the page state while all threads wait. The threads have finished the interval. For the reading with pos -1 they have finished the first write of their buffers [Ref5]. They start the warm-up pass of the next interval only after the reading [Ref10].
- **Meaning of the 4 counter names.** The meanings below follow the public Linux kernel documentation [Ref23].
  - `thp_fault_alloc`: the counter grows each time a page fault gets a newly allocated huge page.
  - `thp_fault_fallback`: the counter grows when a page fault does not get a huge page and uses small pages instead.
  - `thp_collapse_alloc`: the counter grows when khugepaged has found a range of pages to join into one huge page and has allocated the new huge page. khugepaged is the Linux background task that scans memory and joins sequences of small pages into huge pages.
  - `pgmigrate_success`: each count means that a page was migrated. Page migration moves a page to another physical place in memory. The documentation writes this name in capital letters (`PGMIGRATE_SUCCESS`).

Values found in the 9 files (9960 P rows):

- `kB_total` is 262144 in every row. 262144 x 1024 = 268435456 bytes, the buffer size.
- `kB_huge` equals `kB_total` in every row.
- `thp_fault_fallback` is 0, `thp_collapse_alloc` is 2 and `pgmigrate_success` is 0 in every row.
- `thp_fault_alloc` has one value per file. It does not change from the first reading to the last reading of a file.

### Page read line (4 fields)

```
# page_read,0,-1,3.765 ms
```

Sample: line 127 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

| Col | Name | Unit | Meaning |
|---|---|---|---|
| 1 | (line kind) | - | the text `# page_read` |
| 2 | round | count from 0 | as in the 120 P rows before this line |
| 3 | pos | count from 0, or -1 | as in the 120 P rows before this line |
| 4 | (time) | ms, 3 decimals, with the text ` ms` | the time that `main()` needed to read `/proc/self/smaps` and `/proc/vmstat` for this reading [Ref10] |

In the 9 files the time lies between 3.745 ms and 4.947 ms (83 lines).

### C row: counters of one thread in one interval (15 fields)

```
# C,round,pos,kernel,tid,cpu,enabled_ns,running_ns,cputime_ns,cbusy0,cbusy1,cbusy2,cbusy3,cbusy_mt,bus_access; pmu_type=11 codes=0x198,0x199,0x19a,0x19b,0x19c,0x19
```

Sample: line 6 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
C,0,0,oldread,0,0,5999401252,5999401252,5986650304,286094550,656404747,110736244,520389099,1096840424,939638922
```

Sample: line 249 of `R/w120-T72L1-20261117T221329Z/a6456.csv`.

```
C,0,0,asmread,0,0,5996970596,5996970596,5985009616,490510615,95294277,11263052,278535328,607253038,541030772
```

Sample: line 249 of `R/w120-T72C4-20261117T222136Z/crev.csv`.

The column names are the 15 names of line 6 up to the `;`. The text after the `;` is not a column. It gives the PMU type number and the 6 event codes in the order of columns 10 to 15.

| Col | `p[]` | Name | Unit | Meaning |
|---|---|---|---|---|
| 1 | 0 | (row kind) | - | the letter `C` |
| 2 | 1 | `round` | count from 0 | repeat of the sequence |
| 3 | 2 | `pos` | count from 0 | place of the kernel in the sequence |
| 4 | 3 | `kernel` | name | name of the kernel |
| 5 | 4 | `tid` | index, 0 to 119 | number of the thread, as in the T row |
| 6 | 5 | `cpu` | CPU number | CPU of the thread, as in the T row |
| 7 | 6 | `enabled_ns` | ns | growth of the value `time_enabled` of the counter group of the thread, from the reading before the interval to the reading after it |
| 8 | 7 | `running_ns` | ns | growth of the value `time_running` of the same group between the same two readings |
| 9 | 8 | `cputime_ns` | ns | CPU time that the thread used between two readings of `CLOCK_THREAD_CPUTIME_ID` (the Linux clock of the CPU time of one thread) |
| 10 | 9 | `cbusy0` | count | growth of the counter of event code 0x198 |
| 11 | 10 | `cbusy1` | count | growth of the counter of event code 0x199 |
| 12 | 11 | `cbusy2` | count | growth of the counter of event code 0x19a |
| 13 | 12 | `cbusy3` | count | growth of the counter of event code 0x19b |
| 14 | 13 | `cbusy_mt` | count | growth of the counter of event code 0x19c |
| 15 | 14 | `bus_access` | count | growth of the counter of event code 0x19 |

How the values are taken [Ref7] [Ref13]:

- **One counter group per thread.** Each thread opens its 6 events for itself with the Linux call `perf_event_open`. The events count in user mode only. The names and codes come from the argument `--events`. The type number comes from `--pmu-type`.
- **Order of the readings.** Before the interval: counter group, then CPU time, then the clock (`t_start`). After the interval: the clock (`t_end`), then CPU time, then counter group. So the counter window encloses the timed interval of the T row.
- **`enabled_ns` and `running_ns`.** One read of the group returns the number of counters, `time_enabled`, `time_running` and one value per counter. bwx12 prints the growth of each value. In its trial mode the source of bwx12 calls a window "multiplexed" when `running_ns` is below `enabled_ns`. Its comment says that the counters then ran for less time than they were enabled [Ref14].
- **`NA`.** bwx12 prints `NA,NA` in columns 7 and 8 when the thread has no counter group, and `NA` for an event that did not open. The 9 files hold no `NA`.

Values found in the 9 files (8880 C rows):

- `enabled_ns` equals `running_ns` in every row. By the rule of the source no window was multiplexed.
- `enabled_ns` is not the elapsed time of the T row. It lies between 35.859 ms below and 0.013 ms above `elapsed_s` of the same thread and interval (rounded to 0.001 ms).
- `cputime_ns` lies between 4.436 ms and 14.986 ms below `enabled_ns` (rounded to 0.001 ms).
- The manual page of `perf_event_open` does not define `time_enabled` for the time in which the thread of the counter is not on a CPU [Ref24].
- `Insufficient data: the cause of these two differences. The Linux kernel source (how it counts time_enabled for a counter of one thread) and a scheduler record of the threads during a run would resolve it.`

What the 6 events are. A file of 2026-11-16 holds the output of `perf list --details` on CRB [Ref16]. It lists these events for the PMU `armv8_pmuv3_0`:

| Column | Code | Name in the perf list | Description in the perf list |
|---|---|---|---|
| `cbusy0` | 0x198 | `l2_chi_cbusy0` | Number of RXDAT or RXRSP response received with CBusy of 0 |
| `cbusy1` | 0x199 | `l2_chi_cbusy1` | Number of RXDAT or RXRSP response received with CBusy of 1 |
| `cbusy2` | 0x19a | `l2_chi_cbusy2` | Number of RXDAT or RXRSP response received with CBusy of 2 |
| `cbusy3` | 0x19b | `l2_chi_cbusy3` | Number of RXDAT or RXRSP response received with CBusy of 3 |
| `cbusy_mt` | 0x19c | `l2_chi_cbusy_mt` | Number of RXDAT or RXRSP response received with CBusy Multi-threaded set |
| `bus_access` | 0x19 | `bus_access` | Attributable Bus access |

- The same folder of 2026-11-16 records the type number 11 for the PMU `armv8_pmuv3_0` [Ref16].
- `Insufficient data: the type number of this PMU in the boot of the rerun on 2026-11-17. The file /sys/bus/event_source/devices/armv8_pmuv3_0/type, read in that boot, would resolve it.`
- `Insufficient data: the meaning of RXDAT, RXRSP and CBusy. The perf list gives no definition. The Arm documentation of the processor would resolve it.`
- No analysis script of this run reads a counter value of a C row (see "Which code reads this file").

## Old read kernel and new read kernel in this file

The kernel name is column 4 of the I, T and C rows.

| Name in column 4 | What it is | In which files |
|---|---|---|
| `oldread` | the **old read kernel**: portable C code with 16 running sums. Each load is followed by an add | all 9 files |
| `read` | the **new read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only | `cfwd.csv` and `crev.csv` only (4 files) |
| `asmread` | a hand-written load-only loop. It is neither the old nor the new read kernel. It has the same 8 `ldp q` loads per 256 bytes as the new read kernel | all 9 files |
| `read_nop96`, `read_nop256` | test loops: the `asmread` loop with 96 or 256 no-operation instructions per 256 bytes | `a6456.csv` only (5 files) |
| `read_1pl` | test loop: one load of 16 bytes per 64-byte line | `a6456.csv` only (5 files) |

- **`a6456.csv` has no row of the new read kernel.** The load-only loop of these 5 files is `asmread`.
- **Machine code of the build that ran** [Ref11]:
  - `oldread`: one loop pass reads 128 bytes with 4 `ldp q` instructions and adds the loaded values to 8 vector sums with 8 vector add instructions. Each vector sum holds 2 of the 16 running sums of the source.
  - `read`: one loop pass reads 256 bytes with 8 `ldp q` instructions. No instruction uses the loaded values.
  - `asmread`: one loop pass reads 256 bytes with 8 `ldp q` instructions. No instruction uses the loaded values. Like the loop of `read`, the loop has 8 `ldp q`, one add to the pointer, one compare and one conditional branch. The registers differ.
- **The name `read` in other files.** In these 9 files `read` is always the new read kernel. In `threads120.csv` of part A the kernel name `read` is the old read kernel in the rows of the binary bw_old, and the new read kernel in the rows of the binary bw_new [Ref17].
- **Position of each kernel in each file:**

| File | pos 0 | pos 1 | pos 2 | pos 3 | pos 4 |
|---|---|---|---|---|---|
| `a6456.csv` | oldread | asmread | read_nop96 | read_nop256 | read_1pl |
| `cfwd.csv` | oldread | read | asmread | - | - |
| `crev.csv` | asmread | read | oldread | - | - |

- **Rows per kernel.** Each kernel of a file has 2 I rows (round 0 and round 1), 240 T rows and 240 C rows.
- **P rows and page read lines have no kernel column.** Take round and pos, and read the kernel from `seq=` in line 2. A row with pos -1 belongs to no kernel.
- **How to select the rows of one kernel.** Match the whole field. The text `read` is also part of the other names. Example for the T rows of the new read kernel: `grep '^T,[01],[0-9]*,read,' cfwd.csv` gives 240 lines for instance 6.
- **Order.** The kernel that ran directly before an interval is the kernel at pos - 1 of the same round. For pos 0 of round 1 it is the last kernel of the sequence. For pos 0 of round 0 there is none. Before each interval the threads also run one warm-up pass of the kernel of that interval.

## Which code reads this file

| Script | Rows that it reads | Columns that it uses | What it computes |
|---|---|---|---|
| `S/stat_bwx.py` [Ref18] | header lines, T, I | header: `min_ms`, `stop`, `thp`. T: round, pos, kernel, `cpu`, `bytes`, `elapsed_s`, `flags`. I: round, pos, kernel, `aggregate_GBps` | per interval: the rate (sum over the T rows), the same sum for CPUs 0-63 and for CPUs 64-127, the test for 64 + 56 threads, the number of rows with a flag, and `aggregate_GBps` for comparison |
| `S/facts_data.py` [Ref19] | header lines 1 and 2, T, I, P, C | header: `min_ms`, `thp`, `seq`, `rounds`, `stop`, `start`, `two_buffers`, `count`. T: round, pos, kernel, `cpu`, `bytes`, `elapsed_s`, `t_start_s`, `t_end_s`, `flags`. I: round, pos, kernel, `threads`, `total_bytes`, `max_elapsed_s`, `aggregate_GBps`, and the line number. P: all columns. C: none (it counts the rows) | per interval: the rate, the rate of mesh 0 and of mesh 1, the test for 64 + 56 threads, the number of rows with a flag, the kernel that ran directly before, the first `t_start_s` and the last `t_end_s` |
| `S/build_facts.py` [Ref20] | through `facts_data.py` | the values above | one record per interval in `S/facts.json` (74 records from the 9 files), and the checks listed below |
| `S/make_report.py` [Ref21] | T and I rows of the intervals that the report uses. Header line 2 of every csv file under `R` | T: round, pos, kernel, `cpu`, `bytes`, `elapsed_s`. The script also converts `t_start_s` and `t_end_s` to numbers. It uses these two values only for one interval of an earlier file, not for the 9 files. I: round, pos, kernel, `threads`, `aggregate_GBps`. Header: `seq`. For the 4 part C files also `start` and `count` | the rate of each used record again from the T rows, for the report page. From `seq`: a check that only the 4 part C folders hold a part C sequence. From `start` and `count`: a requirement that each of the 4 part C files holds `start=common` and `count=1` |

### The rate of the analysis

`stat_bwx.py`, `facts_data.py` and `make_report.py` use the same formula [Ref18] [Ref19] [Ref21]:

```
rate of thread i = bytes_i / elapsed_s_i / 1e9
                   (T row: column 7 / column 8 / 1e9, in GB/s)
rate of interval = sum of the 120 thread rates   (GB = 1e9 bytes)
```

- `stat_bwx.py` adds the 120 thread rates in file order.
- `facts_data.py` and `make_report.py` add the rates of the threads on CPUs 0-63 (mesh 0), add the rates of the threads on CPUs 64 and higher (mesh 1), and then add the two sums.
- `build_facts.py` compares the result of `facts_data.py` with the result of `stat_bwx.py`. It accepts a difference of at most 1e-9 GB/s [Ref20].
- `facts.json` holds the rate rounded to 0.001 GB/s. `make_report.py` sums the T rows again, requires that its sum rounds to the value of the record, and prints the rate with 2 decimals [Ref21].
- "Requires" has one meaning for `make_report.py` in this text. When the condition does not hold, the script stops at once with a message. It then writes no report page [Ref21].

### How this differs from `aggregate_GBps` of the I row

```
I row:     aggregate_GBps = (sum of bytes_i) / (largest elapsed_i)
analysis:  rate           = sum of (bytes_i / elapsed_i)
```

- **The divisor.** The I row divides the bytes of all threads by one time: the longest elapsed time of a thread. The analysis divides the bytes of each thread by the elapsed time of that same thread, and then adds the 120 quotients.
- **The direction.** No thread has a longer elapsed time than the longest one. So with exact values the analysis rate is not below the I row value. The file holds rounded values: `elapsed_s` is rounded to 1 us and `aggregate_GBps` to 0.01 GB/s (next point). So for the values of the file this order holds only within the rounding.
- **The precision.** bwx12 computes the I row value from whole nanoseconds and prints 2 decimals. The analysis starts from `elapsed_s` as printed, with 6 decimals (steps of 1 us).
- **The size of the difference here.** With the common stop the 120 elapsed times of an interval differ by at most 0.000454 s (0.008 % of 6 s). In the 74 intervals of the 9 files the analysis rate is higher than the printed `aggregate_GBps` by 0.0004 GB/s to 0.0180 GB/s (rounded to 0.0001 GB/s).
- **The checks.** `build_facts.py` checks that the difference is below 0.05 GB/s in every interval of the 9 files [Ref20]. A failed check does not stop that script at the place of the check. The script stops later, before it writes its two files (see "What a failed check does" below). `make_report.py` requires at most 0.02 GB/s between its printed rate and the I row value for every bwx12 record that the report uses [Ref21].

Example, instance 1, interval round 0, pos 0, `oldread`:

| Quantity | Value | Source |
|---|---|---|
| `aggregate_GBps` of the I row | 462.29 GB/s | line 128 |
| rate of thread 0 | 28934406144 / 6.000122 / 1e9 = 4.822303 GB/s | line 129 |
| sum of the thread rates on CPUs 0-63 | 305.128 GB/s | lines 129 to 192 |
| sum of the thread rates on CPUs 64-119 | 157.172 GB/s | lines 193 to 248 |
| rate of the analysis | 462.300017 GB/s, in `facts.json` 462.3 | lines 129 to 248 |
| analysis minus I row | 0.010 GB/s | |

Example, instance 9, interval round 1, pos 2, `oldread`: the I row at line 1938 prints 463.98 GB/s. The sum over the T rows at lines 1939 to 2058 is 463.995101 GB/s. `facts.json` holds 463.995.

### From the interval rate to the report

- `make_report.py` reads `S/facts.json`. Each record names the folder, the file and the line of its I row. The script requires that the 120 T rows of the interval are the 120 lines directly after that line [Ref21].
- From the 9 files the report uses 44 of the 74 interval records [Ref21]:
  - part L (instances 1 to 3): `oldread` at pos 0 (6 intervals) and `asmread` at pos 1 (6 intervals).
  - control I (instances 4 and 5): `oldread` at pos 0 (4 intervals) and `asmread` at pos 1 (4 intervals).
  - part C (instances 6 to 9): `oldread`, `read` and `asmread` at every position (8 intervals each).
- The report does not use the 30 intervals of `read_nop96`, `read_nop256` and `read_1pl`.
- For each selection the script computes the lowest, the median and the highest interval rate (class `Rg`) [Ref21].

### Checks that `build_facts.py` runs on the 9 files [Ref20]

- Each folder holds exactly one csv file, and the file is one section. `facts_data.py` starts a new section at each line that begins with `-- step`. A csv file of another runner script (`run_bwx.sh`) holds one such line per section. A file of `rx.sh` has none.
- The number of I rows is 10 for part L and control I, and 6 for part C.
- Every interval has 120 threads: 64 on CPUs 0-63 and 56 on CPUs 64-119, on 120 different CPUs.
- The column `flags` is `-` in every T row.
- `kB_huge` equals `kB_total` in every P row.
- The analysis rate and `aggregate_GBps` differ by less than 0.05 GB/s in every interval.
- The rate, the two mesh sums, the test for 64 + 56 threads and the number of rows with a flag are equal to the values of `stat_bwx.py` (the rate and the two mesh sums within 1e-9 GB/s).

The same script also checks other files of the 9 folders [Ref20]:

- `launches.txt` holds one launch with exit status 0.
- `stderr.txt` has 0 bytes.
- The tag and the arguments of the launch line are equal to the spec file.
- `env.txt` holds the same sha256 value of bwx12 in the 9 folders. It is the value of `SHA=` in `go.sh`.
- `env.txt` holds the same Linux kernel release in the 9 folders.
- The launch line of `launches.txt` records the number of runnable tasks. The check accepts 2 or fewer. The value is 1 in the 9 folders.
- The launch line records the number of logged-in users. It is 0 in the 9 folders.

What a failed check does:

- **The first check (one csv file, one section) stops the script.** It is written as two `assert` statements. The script ends at once and writes no file [Ref20].
- **The other checks do not stop the script at the place of the check.** The script stores the result of each one and goes on [Ref20].
- **A stored failure stops the script later, before it writes a file.** After the checks the script builds the text of the facts sheet. Section 6 of that text holds the sentence that all checks pass. The code of that section requires that every stored result is a pass. When a check has failed, the script ends at that place with a message and exit status 1. One of the other conditions listed below can end the script before that place. The script writes `facts.json` and `FACTS.md` only after the text is built. So a run with a failed check writes neither file. The two files of an earlier run stay as they were [Ref20].
- **The last lines of `main` print each failed check and set exit status 1.** These lines come after the two writes. With the requirement of the point above they find no failed check [Ref20].
- **Other conditions also stop the script before it writes a file.** This list of them is not complete.
  - `facts_data.py` ends the script when a T row does not have 13 fields [Ref19].
  - `facts_data.py` ends the script when the kernel name of a T row is not the entry of `seq=` at the pos of that row [Ref19].
  - `facts_data.py` converts fields of the T, I and P rows to numbers. A field that is not a number ends the script with a Python error. `NA` in a P row is such a field [Ref19].
  - `facts_text.py` and `facts_text4.py` write the text of the facts sheet. Some of their sentences state a pattern of the data. These modules end the script when the data do not show such a pattern [Ref20].
  - `build_facts.py` holds further `assert` statements. All of them run before the two files are written [Ref20].
- **Result of the stored run.** `facts.json` holds the stored results under the key `meta.checks`. It lists 27 checks. None of them is stored as failed [Ref20].

<details>
<summary>Words used here</summary>

Definitions marked (F) are copied from the word list of the facts sheet `S/FACTS.md` [Ref17].

- **CRB** (F): the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1** (F): the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56** (F): our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel** (F): the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel** (F): portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel** (F): NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread** (F): a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop** (F): the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl** (F): test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new** (F): the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx** (F): later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position** (F): a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session** (F): one pass of go.sh through part A, part L and part C.
- **Part A** (F): the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L** (F): one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C** (F): one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I** (F): the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line** (F): the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Idle start** (F): a launch at a 1-minute load average below 1.0.
- **I, T, P, C rows** (F): the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Common stop** (F): the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **2 MiB pages** (F): transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.
- **Rate, total** (F): part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **pos**: the column name of the position.
- **GB, MiB, kB**: 1 GB = 1e9 bytes. 1 MiB = 1048576 bytes. 1 kB in the P rows = 1024 bytes.
- **Chunk**: a part of the buffer of 2 MiB (2097152 bytes). With the common stop a thread reads the clock after each chunk.
- **Warm-up pass**: one run of the kernel over the whole buffer before the timed interval. It is not timed.
- **Elapsed time**: `t_end` - `t_start` of one thread in one interval.
- **tid**: the number of a thread inside the bwx12 process, from 0 to 119.
- **Pinned**: a pinned thread may run on one CPU only.
- **Page state**: the size of a buffer and the part of it on huge pages, as `/proc/self/smaps` reports them, plus 4 counters of `/proc/vmstat`.
- **PMU**: performance monitoring unit, the hardware that counts events in a CPU. Linux gives each PMU a type number.
- **Event code**: the number that selects what a hardware counter counts.
- **Counter group**: the counters of one thread that one read call returns together.
- **Spec file**: a file whose lines hold a tag and the arguments of one bwx12 process, in the form `tag|arguments`.
- **rx.sh**: the runner script. It starts one bwx12 process per spec line and stores its output.
- **Marker file** (F): `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **env.txt**: a file that `rx.sh` writes in the result folder before it starts a process. It holds the date, the Linux kernel release, the load, the logged-in users, a list of processes, and the path of the binary with the sha256 value that `rx.sh` got as an argument [Ref1].
- **launches.txt, launch line**: a file that `rx.sh` writes in the result folder. Directly before `rx.sh` starts a process it appends the launch line. This line holds the tag, the time, the content of `/proc/loadavg` (the Linux file with the load averages and the number of runnable tasks), the number of logged-in users and the arguments. After the process ends `rx.sh` appends a line with the exit status [Ref1].
- **Rerun**: the whole-chip test of 2026-11-17 at a memory speed of 7200 MT/s (million transfers per second). `go.sh` and `go2.sh` ran it. The 9 files are a part of its results.
- **go.sh, go2.sh**: the driver scripts of the rerun. They call rx.sh.
- **Facts sheet, facts.json**: the file `S/FACTS.md` and its data file `S/facts.json`. `facts.json` holds one record per interval, built from the raw files.
- **Huge page**: a memory page of 2 MiB. It is larger than the normal page of the system. The facts sheet calls it a 2 MiB page.
- **sha256** (F): a checksum. Two files with the same sha256 have the same content.
- **Instance**: one of the 9 files of the table under "What this file is".

</details>

## References

- [Ref1] `W15/rx.sh`, lines 9 to 21: the result folder, the loop over the spec lines, and line 17 that starts bwx12 under `taskset -c 0-119` (the process may run on CPUs 0 to 119 only) with standard output to `<tag>.csv` and standard error to `stderr.txt`. Line 19: the loop that runs while the process exists, with `kill -0` (a test whether the process exists, no signal is sent), the test of the marker file and `sleep 1`.
- [Ref2] `S/like.spec`, `S/cfwd.spec`, `S/crev.spec`, line 1 of each: the tag and the arguments of the bwx12 process. `launches.txt` in each of the 9 result folders, line 1: the tag and the arguments that the process got. They are equal to the spec line in the 9 folders.
- [Ref3] `BWX12/bwx12.c`, lines 3018 to 3037: `main()` prints the 6 header lines. Lines 491 to 492 and 851 to 857: the real kernels and the stand-in loops.
- [Ref4] `S/go.sh`, lines 40 to 46: the 3 sessions and the extra part C process. `S/go2.sh`, lines 27 to 33: control I.
- [Ref5] `BWX12/bwx12.c`, lines 3039 to 3049: the loops over round and pos in `main()`, and the case pos -1. Lines 1645 to 1654: the thread allocates and writes its buffer before that reading.
- [Ref6] `BWX12/bwx12.c`, lines 3051 to 3078: `main()` sets the common start and the deadline, sums the bytes, finds the longest elapsed time, and prints the I row.
- [Ref7] `BWX12/bwx12.c`, lines 1632 to 1735: the function `worker` (one thread): pinning, buffer, warm-up pass, wait for the common start, counter readings, the timed loop. Lines 3079 to 3085: `main()` prints the T rows. Lines 126 to 133: the constants for the chunk size (2 MiB), the time that `main()` adds to the clock value for the common start (2 ms) and the limit of the flag `late` (100 us).
- [Ref8] `BWX12/bwx12.c`, lines 415 to 451: `pin_cpu`, `buf_len`, `alloc_buf` (the `madvise` request). Lines 388 to 413 and 3009 to 3011: the `--cpus` list and the CPU of thread i.
- [Ref9] `BWX12/bwx12.c`, lines 327 to 332: `now_ns` reads `CLOCK_MONOTONIC`. Line 2908: `main()` stores the clock value of the process start.
- [Ref10] `BWX12/bwx12.c`, lines 3105 to 3120: `main()` reads the page state, lets the threads go on, prints the P rows and the page read line, and writes its buffered output to the file. Lines 1727 to 1731: the thread waits for that reading.
- [Ref11] Kernel source in `BWX12/bwx12.c`: lines 461 to 474 (`oldread`), 500 to 528 (`read`), 616 to 642 (`asmread`), 1063 (`read_nop96`), 1199 (`read_nop256`), 984 to 1004 (`read_1pl`). Lines 1487 to 1509: the function `call` passes a buffer range to the kernel. Machine code of the build that ran, in `BWX12/crb-build-1/listing.txt`: lines 2 to 15 (`k_read`), 60 to 81 (`k_asmread`), 161 to 176 (the loop of `k_oldread`), 755 to 764 (`k_read_1pl`), and the functions that start at line 855 (`k_read_nop96`) and line 2127 (`k_read_nop256`). `BWX12/crb-build-1/build.txt`, lines 16 to 23: the sha256 values of this build. The local `listing.txt` has the value of line 21. The binary bwx12 is not in the local folders. Its sha256 value (line 20) is known only from the records. `S/go.sh`, lines 13 and 23, and `S/go2.sh`, lines 10 and 19: each driver script stops before its first process when bwx12 does not have the sha256 value of this build. `env.txt` in each of the 9 result folders, line 10: the sha256 value that `rx.sh` got as its third argument. It is the value of this build in the 9 folders. `W15/rx.sh`, lines 8 and 10: the script compares the binary with this value (`sha256sum -c`) and ends when they differ. After that it writes the value to `env.txt`. It does not compute the value that it writes.
- [Ref12] `BWX12/bwx12.c`, lines 1511 to 1578: `read_smaps`, `read_vmstat`, `print_na`, `print_p`.
- [Ref13] `BWX12/bwx12.c`, lines 1580 to 1630: `open_counters`, `cpu_ns`, `read_group`. Lines 3086 to 3103: `main()` prints the C rows. Lines 1737 to 1748: the usage text for `--pmu-type` and `--events`.
- [Ref14] `BWX12/bwx12.c`, lines 2163 to 2171 (`first_multiplexed`) and lines 2367 to 2372 (the message `count_multiplexed` of the trial mode).
- [Ref15] `BWX12/bwx12.c`, lines 2297 to 2552: the code that prints the rows of the trial mode.
- [Ref16] `R/asct-prep-20261116T231215Z/perf-list-details.txt`, lines 1148 to 1150 (`bus_access`) and 1240 to 1259 (`l2_chi_cbusy0` to `l2_chi_cbusy_mt`). `R/asct-prep-20261116T231215Z/env.txt`, line 17: `core pmu type 11`. The script `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/asct-2026-11-16/crb/prep.sh` wrote both: line 24 reads the type number of `armv8_pmuv3_0`, line 56 runs `perf list --details`.
- [Ref17] `S/FACTS.md`, lines 38 to 65 (word list), line 76 (2 MiB pages), line 77 (marker file) and line 80 (sha256).
- [Ref18] `S/stat_bwx.py`, lines 38 to 58 (`read_csv`) and 61 to 81 (`interval_rows`).
- [Ref19] `S/facts_data.py`, lines 313 to 353 (`read_bwx`) and 356 to 383 (`bwx_intervals`).
- [Ref20] `S/build_facts.py`, lines 74 to 86 (reads the 9 files), 142 to 160 (one record per interval), 709 to 746 (the checks), 816 to 834 (comparison with `stat_bwx.py`), 661 to 662 (`chk` stores the result of a check and does not stop the script), 1033 to 1052 (`main`: line 1037 builds the text, lines 1038 to 1041 write the two files, lines 1044 to 1052 print the failed checks and set exit status 1). `S/facts.json`, key `meta.checks`: the stored results of the 27 checks. `S/build_facts.py`, lines 687 to 694 (logged-in users), 764 to 771 (sha256 of bwx12 in `env.txt`), 782 to 797 (Linux kernel release, runnable tasks), 807 and 858 (two of the further `assert` statements). `S/facts_text.py`, lines 36 to 38: the function `need` ends the script. Line 1464: the function `render` of this module calls the function `section4` of `S/facts_text4.py`. `S/facts_text4.py`, lines 1461 and 1472: `section4` requires that every stored check passed, and it writes the sentence that all checks pass. `build_facts.py` calls `render` in line 1037, before it writes the two files.
- [Ref21] `S/make_report.py`, lines 124 to 139 (`t_rows`), 158 to 163 (`i_row_rate`), 176 to 189 (`val`), 192 to 202 (class `Rg`: lowest, median and highest rate), 275 to 284 (the selections), 340 to 343 (the comparison with the I row), 1209 to 1224 (the scan of the `# bwx:` header lines and the check of the part C folders), 1269 to 1275 (the requirement on `start` and `count` in header line 2 of the 4 part C files), 1016 to 1019 (the only use of `t_start_s` and `t_end_s`: the `asmread` interval with the lowest rate among the earlier 8000 MT/s runs that the report uses, in the file `R/w120-R1-20261115T185140Z/p2add.csv`), 42 to 49 (`stop` and `need`: a requirement that does not hold ends the script), 2828 to 2830 (the only place that writes the report page, at the end of the script).
- [Ref22] `BWX12/bwx12.c`, lines 365 to 385 (`restrict_cpus`: `main()` removes every CPU above 119 from the allowed CPUs and pins nothing), 3057 to 3064 (`main()` between the start and the end of an interval: it sets the common start and waits), 3077 to 3103 (it prints the I, T and C rows after the wait). `W15/rx.sh`, line 17: `taskset -c 0-119`.
- [Ref23] External source: the public Linux kernel documentation at `docs.kernel.org`, read on 2026-11-21. Page "Transparent Hugepage Support" (`admin-guide/mm/transhuge.html`), section "Monitoring usage": the counters `thp_fault_alloc`, `thp_fault_fallback` and `thp_collapse_alloc` of `/proc/vmstat`. Section "Objective" of the same page: what khugepaged does. Page "Page migration" (`mm/page_migration.html`), section "Monitoring Migration": the counter `PGMIGRATE_SUCCESS`. These pages document the newest Linux kernel. `env.txt` of the 9 folders records the release `7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858` for CRB (line 2). The documentation of that release was not read.
- [Ref24] External source: the Linux manual page `perf_event_open(2)` at `man7.org`, read on 2026-11-21. It names one case in which `time_enabled` and `time_running` differ: more events than counters of the PMU. It does not define `time_enabled` for the time in which the thread of the counter is not on a CPU.
- [Ref25] `R/go-T72-20261117T221209Z.log`, line 5: `affinity of this shell: pid 4864's current affinity list: 0-119`. Line 38 of `S/go.sh` prints it. `S/go.sh`, line 31, and `S/go2.sh`, line 30: the lines that start `rx.sh`. `R/go2-T72-20261117T222335Z.log` holds no line with a CPU list.
- [Ref26] External source: the Linux manual page `sched_setaffinity(2)` at `man7.org`, read on 2026-11-21. A child process gets the CPU list (the page calls it the CPU affinity mask) of its parent. The list stays the same when the process starts another program.
