## Short version

Each `threads120.csv` of part A of the rerun (the test of 2026-11-17 at 7200 MT/s) holds the records of 24 benchmark processes with 120 threads each, 7 lines per process: 1 header line that the script `ra.sh` writes and 6 lines that the process prints. The rate that the analysis uses is column 7 (`aggregate_GBps`) of the three interval rows of a process. The header line above these rows names the binary: `bw_old` holds the old read kernel, and `bw_new` holds the new read kernel.

## What this file is

Path names used in this text:

- `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`
- `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`
- `K13` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13`

Scope of this text:

- It describes the three `threads120.csv` files of the rerun (table below).
- Two converted copies of 8000 MT/s data under `S/base8000` have the same file name and the same row formats.
- The counts, the line numbers and the statements about `ra.sh` of this text do not hold for the two copies. The section "Converted copies under S/base8000" lists what differs.

The files of this type (7200 MT/s, 2026-11-17):

| Session | File | Lines | Size |
|---|---|---|---|
| 1 | `R/k120-T72A1-20261117T221209Z/threads120.csv` [Ref1] | 168 | 15338 bytes |
| 2 | `R/k120-T72A2-20261117T221518Z/threads120.csv` [Ref2] | 168 | 15362 bytes |
| 3 | `R/k120-T72A3-20261117T221827Z/threads120.csv` [Ref3] | 168 | 15361 bytes |

This text holds for all three files. Each example names the file and the line that it comes from.

Who writes the file:

- `go.sh` (the driver script of the rerun) starts `ra.sh` once per session. It passes the name `T72A1`, `T72A2` or `T72A3` [Ref5].
- `ra.sh` (the script of part A) creates the folder `k120-<name>-<UTC time of its start>`. It writes `threads120.csv` into this folder [Ref4].
- The function `one` of `ra.sh` runs once per process. First it appends the `-- binary` header line to the file. Then it starts the binary, and the binary appends its standard output to the same file [Ref4].
- The command line of every process is:

```
<binary> --threads 120 --cpus 0-119 --bytes 256M --kernel <kernel> --reps 3 --min-ms 500
```

- All other lines of the file come from `printf` calls in the function `main` of the benchmark program.
- `bw_old` was built from `K13/bandwidth.orig.c`. `bw_new` was built from `K13/bandwidth.c` [Ref8].
- The text of `main` is the same in both source files [Ref6] [Ref7]. So both binaries print the same line formats.
- The local `K13/bandwidth.c` has the sha256 checksum f1985072... A run of `run_kernels.sh` (the script of the test of 2026-11-13) recorded this value at 18:32:18 UTC on 2026-11-13. That run built the binaries and timed nothing. The timed run of 18:12:22 UTC recorded another checksum for `bandwidth.c`: c1406e02... Both runs recorded the same checksum for `bw_new` [Ref18]. So the machine code is not in doubt.
- The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref20]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.

One process, one kernel:

- One process times one kernel of one binary. No process times two kernels.
- 2 binaries x 6 kernels x 2 rounds give 24 processes per file.
- Round 1 takes the kernels in the order read, write, copy, asmread, asmwrite, asmcopy. For each kernel `bw_old` runs first, then `bw_new`.
- Round 2 runs the same 12 processes in the exact reverse order [Ref4].
- `ra.sh` starts a process directly after the process before it. It does not wait between two processes.
- `ra.sh` waits only before the first process of the file: until at most 2 tasks are runnable, then 5 s more [Ref4].
- In this wait `ra.sh` reads the count of runnable tasks at most 40 times, 1 s apart. It stops the run when the count is still above 2 [Ref4]. Then no `threads120.csv` exists.
- Before every process `ra.sh` tests whether the marker file `/tmp/positron-perf.RUNNING` exists. It stops when the file exists [Ref4]. It does not run this test while a process runs. So the marker file does not stop a process that has already started.
- `ra.sh` also stops when a process ends with an error status (`set -e`) [Ref4]. After such a stop the file would hold fewer than 24 complete processes.
- Every process adds 7 lines. 24 x 7 = 168 lines per file.

What one process does (needed to read the columns) [Ref6] [Ref7]:

- `ra.sh` restarts itself under the tool `taskset` with the CPU list 0-119. So the script and every process that it starts may run on CPUs 0-119 only [Ref4].
- The binary starts 120 threads. Thread number i is pinned to CPU i. A thread pins itself first, before it allocates its buffer.
- The program pins only these 120 threads. Its main thread may run on any of the CPUs 0-119. During a timed interval the main thread waits at the barrier (a meeting point of the 120 threads and the main thread). The steps under "How `aggregate_GBps` is computed in the C source" show where [Ref6].
- Each thread allocates its own buffer of 256 MiB (268435456 bytes).
- Each thread asks Linux for huge pages for its buffer (call `madvise` with `MADV_HUGEPAGE`).
- Each thread writes its whole buffer once before any timing (first touch). So a timed interval holds no first page fault of the buffer.
- For the kernels `copy` and `asmcopy` each thread prepares a second buffer in the same way.
- Then the process times 3 intervals (`--reps 3`). In an interval each thread runs whole passes over its buffer until at least 0.5 s have passed (`--min-ms 500`).

## Line kinds

| Kind | How to recognise it | Lines per file | Written by | What it holds |
|---|---|---|---|---|
| Process header line | starts with `-- binary ` | 24 | `ra.sh`, function `one` | binary, kernel, arguments, round, load, time of day |
| Formula line | starts with `# bandwidth:` | 24 | binary, `main` | the unit, the formula of the rate, the settings of the process |
| Column name line | starts with `kernel,threads,` | 24 | binary, `main` | the names of the 10 columns of the rows below it |
| Interval row | 10 fields separated by commas, field 4 is `0`, `1` or `2` | 72 | binary, `main` | one timed interval of 120 threads |
| Best row | 10 fields separated by commas, field 4 is the word `best` | 24 | binary, `main` | the highest rate of the 3 interval rows above it |

The three files hold no other kind of line. The binary can print one more kind (rows that start with `thread,`). It prints them only with the option `--per-thread`, and `ra.sh` does not pass this option [Ref4] [Ref6].

Sample: the first process of the session 1 file, lines 1 to 7 [Ref1]:

```
-- binary bw_old kernel read threads 120 cpus 0-119 bytes 256M round 1 load 0.07 utc 22:12:14
# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; threads=120 bytes_per_thread=268435456 min_ms=500 thp=madvise
kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps
read,120,268435456,0,256087425024,0.5474,467.83,2.98,4.93,3.99
read,120,268435456,1,255282118656,0.5456,467.92,2.99,4.94,3.99
read,120,268435456,2,253403070464,0.5445,465.38,2.99,4.95,3.99
read,120,268435456,best,,,467.92,,,
```

## Columns

### Process header line (`-- binary ...`)

The line holds 17 words separated by one space: the marker `--`, then 8 pairs of a name and a value. `ra.sh` writes it directly before it starts the process [Ref4]. The example values are those of line 1 of the session 1 file [Ref1].

| Words | Name | Example | Unit | Meaning |
|---|---|---|---|---|
| 1 | `--` | `--` | none | Marker of a process header line. |
| 2, 3 | `binary` | `bw_old` | none | File name of the benchmark binary. `bw_old` holds the old read kernel. `bw_new` holds the new read kernel. |
| 4, 5 | `kernel` | `read` | none | The value given to `--kernel`. It selects the one loop that this process times: `read`, `write`, `copy`, `asmread`, `asmwrite` or `asmcopy`. |
| 6, 7 | `threads` | `120` | threads | The value given to `--threads`. |
| 8, 9 | `cpus` | `0-119` | CPU list | The value given to `--cpus`. Thread number i is pinned to the CPU at place i of this list. |
| 10, 11 | `bytes` | `256M` | bytes, with a size letter | The value given to `--bytes`: the buffer size of one thread. `M` means 2^20, so `256M` is 268435456 bytes (256 MiB). |
| 12, 13 | `round` | `1` | none | The round of the script: 1 or 2. Round 2 runs the processes in the reverse order of round 1. |
| 14, 15 | `load` | `0.07` | tasks | The 1-minute load average. `ra.sh` reads the first field of the file `/proc/loadavg` when it writes the line. |
| 16, 17 | `utc` | `22:12:14` | hours:minutes:seconds, UTC | The time of day at which the line was written. The line holds no date. The date is in the folder name. |

Notes on `load`:

- The value is an average over the last minute. It is not the number of busy CPUs at the moment of the launch.
- In the session 1 file it rises from 0.07 (line 1) to 77.06 (line 162) [Ref1]. Line 1 of the session 2 file holds 98.64 [Ref2]. Line 1 of the session 3 file holds 102.96 [Ref3].
- `ra.sh` does not test this value. Its only wait rule uses the number of runnable tasks, before the first process of the file [Ref4].
- Hypothesis of the facts sheet: the high values come from the 120-thread processes of the rerun itself [Ref13]. The facts sheet names the check that would confirm or reject it: sample `/proc/loadavg` and the list of running processes once per second between two steps. This check was not done [Ref13].

### Formula line (`# bandwidth: ...`)

The line is the same text in all 72 processes of the three files. It has four parts, separated by `; ` [Ref6] [Ref7]:

| Part | Text | Meaning |
|---|---|---|
| 1 | `# bandwidth: GB = 1e9 bytes` | Every rate of the file uses GB = 1e9 bytes. |
| 2 | `aggregate_GBps = sum(bytes) / max(per-thread elapsed_s)` | The formula of column 7. See "How `aggregate_GBps` is computed" below. |
| 3 | `copy counts read+write bytes` | For the kernels `copy` and `asmcopy` one pass counts 2 x the buffer size: the bytes read plus the bytes written. |
| 4 | `threads=120 bytes_per_thread=268435456 min_ms=500 thp=madvise` | The settings of the process: 120 threads, 268435456 bytes of buffer per thread, a minimum of 500 ms per timed interval, and the huge page request. |

`thp=madvise` means: the program asked for huge pages with `madvise`. The program prints this text whenever the option `--no-thp` is absent. The text does not say whether the buffers were placed on huge pages. For part A this is not recorded [Ref13].

### Interval rows (10 columns)

One row is one timed interval of one process. The names are those of the column name line. The examples are from line 4 of the session 1 file [Ref1]. The source lines that print each column are in [Ref6] (old source) and [Ref7] (new source).

| No. | Name | Example | Unit | Meaning |
|---|---|---|---|---|
| 1 | `kernel` | `read` | none | Name of the timed loop. Both binaries print `read` for their read kernel. So this column does not tell the old read kernel from the new one. |
| 2 | `threads` | `120` | threads | Number of threads of the process. |
| 3 | `bytes_per_thread` | `268435456` | bytes | Buffer size of one thread (256 MiB). |
| 4 | `rep` | `0` | none | Number of the timed interval inside the process: 0, 1, 2. |
| 5 | `total_bytes` | `256087425024` | bytes | Sum over the 120 threads of the bytes that each thread counted in this interval. A thread counts `bytes_per_thread` for each whole pass over its buffer (2 x `bytes_per_thread` for `copy` and `asmcopy`). |
| 6 | `elapsed_s` | `0.5474` | s | The longest elapsed time of a single thread in this interval, printed with 4 decimals. Every thread measures its own time. |
| 7 | `aggregate_GBps` | `467.83` | GB/s | The rate of the 120 threads together: `total_bytes` / longest per-thread time / 1e9, printed with 2 decimals. This is the value that the analysis uses. |
| 8 | `per_thread_min_GBps` | `2.98` | GB/s | The lowest rate of a single thread. The rate of a thread is its own bytes / its own elapsed time / 1e9. |
| 9 | `per_thread_max_GBps` | `4.93` | GB/s | The highest rate of a single thread. |
| 10 | `per_thread_avg_GBps` | `3.99` | GB/s | The sum of the 120 thread rates, divided by 120. |

Facts about these columns in the three files (216 interval rows):

- Column 2 is 120 threads and column 3 is 268435456 bytes in every row.
- Column 5 is a whole multiple of column 3 in every row. Column 5 / column 3 is the pass count. Line 4 of the session 1 file gives 954 passes. Line 11 of the same file gives 664 passes [Ref1].
- Column 6 lies between 0.5197 s and 0.8382 s.
- Column 5 / column 6 / 1e9 gives column 7 again. The difference is at most 0.04 GB/s. It comes from the rounding of column 6 to 4 decimals.

### How `aggregate_GBps` is computed in the C source

The timing steps are the same in both source files. One detail of the call of the read kernel differs. The old source stores the sum that the old read kernel returns into a variable of the thread. The new read kernel returns no value [Ref6] [Ref7].

Inside each thread (function `worker`), for one interval:

1. The thread runs one pass over its buffer that is not timed (warm-up).
2. The thread waits at a barrier (a meeting point of the 120 threads and the main thread). All threads continue together.
3. The thread reads the clock `CLOCK_MONOTONIC` (a clock of Linux that never jumps back). This is its start time `t0`.
4. The thread runs one whole pass over its buffer. It adds the bytes of the pass to its counter `bytes`. Then it reads the clock again (`t1`).
5. The thread repeats step 4 while `t1 - t0` is below 0.5 s.
6. The thread stores `bytes` and `elapsed_s = t1 - t0`.
7. The thread waits at the barrier again.

The program fixes the number of passes between two clock reads: 8 MiB divided by the buffer size, rounded down, and at least 1. The buffer is 256 MiB. This gives 1. So each thread reads the clock after every pass.

Inside the main thread (function `main`), after all 120 threads reached the barrier of step 7:

8. `total` = the sum of `bytes` over the 120 threads (column 5).
9. `max_el` = the largest `elapsed_s` of the 120 threads (column 6).
10. `agg = (double)total / max_el / 1e9` (column 7). It is printed with the format `%.2f`.

What this means for a reader of column 7:

- The bytes of all threads are counted, each over the thread's own interval.
- One time divides them: the time of the thread that ran longest.
- The threads stop at different times. Each thread finishes the pass that it is in when the 0.5 s are over (whole-pass stop).
- A thread that has stopped waits at the barrier (step 7). It reads no memory while the other threads finish their last pass. So at the end of an interval fewer than 120 threads read memory. This time lies inside `max_el`, the time that divides the bytes.
- The 120 start times `t0` are 120 separate clock reads. The formula uses no common start time and no common end time.
- Each thread's own time is at most `max_el`. So column 7 can never be higher than the sum of the 120 thread rates.
- Column 10 x 120 gives the sum of the 120 thread rates. Column 10 is rounded to 0.01 GB/s. So this product is exact to 0.6 GB/s (0.005 GB/s x 120).
- Line 4 of the session 1 file (old read kernel): 3.99 x 120 = 478.8 GB/s against 467.83 GB/s in column 7 [Ref1].
- Line 11 of the session 1 file (new read kernel): 2.84 x 120 = 340.8 GB/s against 330.59 GB/s in column 7 [Ref1].
- The main thread prints the row between two timed intervals. The next interval cannot start before the main thread is back at the barrier.

One more fact on the rows of the new read kernel:

- 16 of the 18 interval rows of `bw_new` with kernel `read` hold the same `total_bytes`: 178241142784 bytes (664 passes).
- In these 16 rows a difference in column 7 comes only from column 6.
- The 2 other rows are lines 158 and 160 of the session 3 file (719 and 718 passes) [Ref3].
- Hypothesis: in the 16 rows 64 threads completed 6 passes and 56 threads completed 5 passes (6 x 64 + 5 x 56 = 664). The facts sheet states the same hypothesis: 6 passes on the 64 threads of mesh 0 and 5 passes on the 56 threads of mesh 1 [Ref13]. The file holds no row per thread. A run with the option `--per-thread` would confirm or reject this.

### Best row

- Columns 1 to 3 are the same as in the interval rows.
- Column 4 holds the word `best`.
- Column 7 holds the highest `aggregate_GBps` of the 3 interval rows above it. This holds in all 72 processes of the three files.
- Columns 5, 6, 8, 9 and 10 are empty.
- No analysis script of the rerun uses this row.

## Old read kernel and new read kernel in this file

- The rows of both kernels say `read` in column 1. Only the process header line above them names the binary.
- A header line that starts with `-- binary bw_old kernel read` opens a process of the old read kernel.
- A header line that starts with `-- binary bw_new kernel read` opens a process of the new read kernel.
- The order of the processes is fixed, so the line numbers are the same in all three files:

| Kernel | Binary | Round | Place in the file | Header line | Interval rows | Best row |
|---|---|---|---|---|---|---|
| Old read kernel | `bw_old` | 1 | process 1 of 24 | 1 | 4 to 6 | 7 |
| New read kernel | `bw_new` | 1 | process 2 of 24 | 8 | 11 to 13 | 14 |
| New read kernel | `bw_new` | 2 | process 23 of 24 | 155 | 158 to 160 | 161 |
| Old read kernel | `bw_old` | 2 | process 24 of 24 | 162 | 165 to 167 | 168 |

- In round 1 the two read processes are the first two of the file: first the old read kernel, then the new read kernel. In round 2 they are the last two of the file: first the new read kernel, then the old read kernel.
- Each file holds 6 interval rows of each read kernel. The three files together hold 18 rows of each.
- This command lists the rows of the old read kernel: `grep -n -A6 -- '-- binary bw_old kernel read' threads120.csv`. With `bw_new` it lists the rows of the new read kernel.

All 36 values of the two read kernels (column 7, GB/s), with the line numbers in each file [Ref1] [Ref2] [Ref3]:

| Session | Round | Old read kernel: lines, `aggregate_GBps` (GB/s) | Median (GB/s) | New read kernel: lines, `aggregate_GBps` (GB/s) | Median (GB/s) | New below old |
|---|---|---|---|---|---|---|
| 1 | 1 | 4-6: 467.83, 467.92, 465.38 | 467.83 | 11-13: 330.59, 330.09, 333.25 | 330.59 | 29.3 % |
| 1 | 2 | 165-167: 461.71, 461.33, 459.90 | 461.33 | 158-160: 327.60, 332.82, 326.68 | 327.60 | 29.0 % |
| 2 | 1 | 4-6: 468.21, 468.62, 467.85 | 468.21 | 11-13: 322.67, 325.26, 324.42 | 324.42 | 30.7 % |
| 2 | 2 | 165-167: 467.52, 467.55, 465.89 | 467.52 | 158-160: 330.32, 328.62, 328.96 | 328.96 | 29.6 % |
| 3 | 1 | 4-6: 474.15, 469.73, 469.37 | 469.73 | 11-13: 315.55, 320.46, 320.89 | 320.46 | 31.8 % |
| 3 | 2 | 165-167: 465.61, 465.55, 466.63 | 465.61 | 158-160: 336.41, 331.45, 332.96 | 332.96 | 28.5 % |

The other 20 processes of a file time the kernels `write`, `copy`, `asmread`, `asmwrite` and `asmcopy` of both binaries. The report of the rerun takes rates only from the `read` rows of part A. It uses the records of the other kernels only to count the processes and to check their order [Ref12].

The facts sheet prints the `asmread` rows of both binaries next to the `read` rows. It compares the medians of the processes. `asmread` gives 0.678 to 0.729 of the rate of the old read kernel in both binaries. The facts sheet concludes that the lower rate belongs to the loops that only load (the new read kernel and `asmread`), not to the binary [Ref13].

## Which code reads this file

`S/stat_k120.py` (quick statistics) [Ref9]:

- It matches the process header line with one regular expression. It keeps the binary, the kernel, the round, the load and the time.
- It takes a line as an interval row when the line has more than 8 fields and field 4 holds only digits. So it skips the best rows.
- It stops with an error when column 1 of an interval row is not the kernel of the header line above it.
- It uses column 7 (rate), column 8 and column 9 (lowest and highest thread rate), and column 5 / column 3 (pass count).
- It prints the number of intervals, the lowest value, the median and the highest value of column 7 for each pair of kernel and binary. With `--pool` it prints the same over several folders together.

`S/facts_data.py`, function `read_k120` [Ref10]:

- It uses the regular expression of `stat_k120.py` for the header line. It keeps the line number of the header line and the header values of threads, cpus and bytes too.
- From the formula line it keeps two things: whether the text "copy counts read+write bytes" is present, and the last part with the settings.
- It takes a line as an interval row when the line has more than 9 fields and field 4 holds only digits. It keeps columns 1, 2 and 4 to 10, the pass count (column 5 / column 3) and the line number.
- `S/build_facts.py` calls this function for the three files. It writes one record per interval row into `facts.json` (the data file of the facts sheet): 72 records per file [Ref11].
- The field `GBps` of a record is column 7, unchanged. The field `launch_utc` is the date of the folder name plus the `utc` value of the header line. The field `load1_at_launch` is the `load` value of the header line.
- `build_facts.py` also checks the files: 24 processes with 3 interval rows each, 120 threads in every row, and the same order of processes as in the file of 2026-11-13. It compares its values with those of `stat_k120.py` [Ref11].

`S/make_report.py` (the script that builds the report page) [Ref12]:

- It reads the records of `facts.json`. It selects the records of part A with kernel `read`: 18 records from 6 processes for `bw_old`, and the same for `bw_new`.
- For each record it opens the csv file and reads the line that the record names. It stops when this line does not hold 10 fields, the kernel, 120 threads, the interval number and the rate of the record.
- It counts the process header lines above that line. This gives the number of the process in the file.
- It also scans every csv file under `R` for lines that start with `# bwx`. A file of this type holds no such line.

How the final numbers of part A come from the columns [Ref12]:

- The rate of an interval is column 7 as the binary printed it. No analysis script of the rerun recomputes it from columns 5 and 6.
- The range of a kernel is the lowest and the highest column 7 value of its 18 interval rows. Old read kernel: 459.90 to 474.15 GB/s. New read kernel: 315.55 to 336.41 GB/s.
- For each session and round the script takes the median of the 3 intervals of the `bw_old` process and the median of the 3 intervals of the `bw_new` process.
- The drop of that pair is (1 - new median / old median) x 100 %.
- Example, session 1, round 1: (1 - 330.59 / 467.83) x 100 = 29.3 %.
- The 6 pairs give 28.5 % to 31.8 %. This is the result under review: at 7200 MT/s the new read kernel is still about 30 % below the old read kernel [Ref13].
- The facts sheet states a limit of these values: with the whole-pass stop the pass count moves in steps, and the rate moves with it. So the percent values of part A are less exact than those of parts L and C [Ref13]. Parts L and C are the parts of the rerun that use the runner bwx12. There all threads stop at the same time, after 6 s.

## Converted copies under S/base8000

Two more files have the name `threads120.csv` and the same row formats. They are not data of the rerun.

| Copy | Lines | Size | Made from | Baseline row |
|---|---|---|---|---|
| `S/base8000/partA-A1/threads120.csv` [Ref15] | 4404 | 122915 bytes | `R/partA-20261113T205055Z/A1.csv`, all 12 processes | A-2 |
| `S/base8000/partA-A3-onebuf500/threads120.csv` [Ref16] | 1101 | 29094 bytes | `R/partA-20261113T205055Z/A3.csv`, 3 of its 12 processes | A-3 |

What they are:

- They hold data of 2026-11-13, measured at 8000 MT/s with the same two binaries [Ref14].
- `sed` and `awk` commands made them on 2026-11-17, before the rerun started. The commands are in the rules file of the rerun [Ref14].
- The purpose: `stat_k120.py` can read these two baselines without a change of the script and without a change of a result file [Ref14].

What differs from the three files of the rerun:

1. **Memory speed and date.** 8000 MT/s on 2026-11-13, not 7200 MT/s on 2026-11-17. The folder name of a copy holds no date. The date is in the name of the folder of the original files, `partA-20261113T205055Z`.
2. **The process header lines are rewritten.** The original files have header lines that start with `-- step`. The `sed` command turned each one into the `-- binary` form. All other lines are byte for byte those of the original files.
3. **The meaning of `round`.** In the copy of A1.csv it is the digit at the end of the tag (`-r1` or `-r2`). In the copy of A3.csv it is the number at the end of the tag `onebuf-ms500-1`, `-2` or `-3`. There it is a repeat number from 1 to 3. It is not a round with reversed order.
4. **The value of `load`.** It is the first of the three load averages of the original line (the 1-minute value). The other values of the original line are dropped. These are the step, the waiting time, the 5-minute and 15-minute load average, the counts of runnable tasks and of all tasks, the number of logins, and three options of the argument list: `--per-thread`, `--reps 3` and `--min-ms 500`. Of the tag only the last digit is kept.
5. **The value of `cpus`.** It is `0-63,64-119`. The program reads this as CPUs 0 to 63 and then 64 to 119. These are the same 120 CPUs in the same order as `0-119` [Ref6].
6. **Rows per thread.** The processes of 2026-11-13 ran with the option `--per-thread`. So each process has 360 more rows after its best row: one row per thread and interval (120 x 3). Each process takes 367 lines, not 7. The program prints these rows after the last timed interval of the process. So the option does not change what is timed [Ref6] [Ref14].
7. **Other processes.** The copy of A1.csv holds 12 processes: `bw_old` read, `bw_new` read, `bw_new` asmread, `bw_old` write, `bw_new` write, `bw_new` asmwrite, and then the same six in reverse order. It holds no copy kernel. The copy of A3.csv holds 3 processes, all `bw_old` read.
8. **Left out.** The `awk` command kept only the processes of A3.csv with the tags `onebuf-ms500-1`, `-2` and `-3`. In the original file other processes ran between them.
9. **The script.** `ra.sh` did not start these processes. The script `run_partA.sh` of 2026-11-13 started them and wrote the original header lines [Ref19]. It waits before every process until at most 2 tasks are runnable, for at most 20 s. The value `waited_s` of an original header line holds the length of this wait. It is 0 s in all 15 original header lines of the two copies [Ref17]. While a process runs, `run_partA.sh` tests once per second whether it must stop. The reasons to stop are the marker file, a stop file of the script itself, and an end time that the caller can set. Then it writes a line that starts with `-- killed` and ends the process. The two copies and their original files hold no such line. `ra.sh` runs no test while a process runs. `run_partA.sh` restarts itself under `taskset` with the CPU list 0-119, as `ra.sh` does. So its test runs on the CPUs of the benchmark threads [Ref19].

Example of a rewritten header line. Line 1 of `R/partA-20261113T205055Z/A1.csv` [Ref17]:

```
-- step A1 tag read_old-r1 binary bw_old waited_s 0 loadavg 0.64 0.21 0.07 1/1076 logins 0 utc 20:50:55 args --threads 120 --cpus 0-63,64-119 --bytes 256M --per-thread --kernel read --reps 3 --min-ms 500
```

Line 1 of `S/base8000/partA-A1/threads120.csv` [Ref15]:

```
-- binary bw_old kernel read threads 120 cpus 0-63,64-119 bytes 256M round 1 load 0.64 utc 20:50:55
```

The rows per thread have 6 columns [Ref6] [Ref7]. Example: line 8 of `S/base8000/partA-A1/threads120.csv` [Ref15]:

```
thread,0,0,read,0,5.08
```

| No. | Name in the source comment | Example | Unit | Meaning |
|---|---|---|---|---|
| 1 | `thread` | `thread` | none | Marker of a row per thread. |
| 2 | index | `0` | none | Number of the thread inside the process, from 0 to 119. |
| 3 | cpu | `0` | CPU number | The CPU that the thread is pinned to. |
| 4 | kernel | `read` | none | Name of the timed loop. |
| 5 | rep | `0` | none | Number of the timed interval: 0, 1, 2. |
| 6 | GB/s | `5.08` | GB/s | The rate of this thread in this interval: its own bytes / its own elapsed time / 1e9. |

Which code reads the copies:

- `stat_k120.py` reads them like the files of the rerun. The rows per thread have 6 fields. So the script skips them [Ref9].
- `build_facts.py` reads them only for a cross-check. It parses the original files A1.csv and A3.csv itself. Then it compares its values with those that `stat_k120.py` reads from the copies [Ref11].
- No record of `facts.json` names a copy. The records of rows A-2 and A-3 name the original files. So `make_report.py` opens the original files, not the copies.

Values of the copies (column 7, GB/s), computed from the interval rows:

- Copy of A1.csv, `bw_old` read: 464.66 to 467.06, median 465.825, 6 intervals.
- Copy of A1.csv, `bw_new` read: 288.94 to 316.31, median 304.425, 6 intervals.
- Copy of A3.csv, `bw_old` read: 463.58 to 469.03, median 466.42, 9 intervals.
- `stat_k120.py` prints the same lowest and highest values. It prints the medians with 2 decimals: 465.82, 304.43 and 466.42.

<details>
<summary>Words used here</summary>

The entries marked (facts sheet) are copied word for word from the word list of the facts sheet `S/FACTS.md` [Ref13]. One exception: the entry "Read kernel" says "On this page" where the facts sheet says "In this sheet". "This sheet" in the entry "Pass count" means the facts sheet.

- **CRB** (facts sheet): the Arm reference server under test. It has 128 CPUs.
- **Whole chip, 120 threads, 64+56** (facts sheet): our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1** (facts sheet): the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **MT/s** (facts sheet): million transfers per second, the unit of memory speed.
- **Read kernel** (facts sheet): the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel** (facts sheet): portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel** (facts sheet): NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread** (facts sheet): a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **bandwidth.c, bw_old, bw_new** (facts sheet): the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx** (facts sheet): later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position** (facts sheet): a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session** (facts sheet): one pass of go.sh through part A, part L and part C.
- **Part A** (facts sheet): the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Whole-pass stop** (facts sheet): the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Pass count** (facts sheet): total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. This sheet prints a pass count for these two kernels only. For copy and asmcopy the same division gives 2 x the number of buffer passes, because the binary counts read plus written bytes (header line of each process in threads120.csv: "copy counts read+write bytes"). facts.json holds that value in the field "passes".
- **Load average** (facts sheet, without its reference mark): the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). "Load at launch" is the 1-minute value read directly before a process starts. The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Pass**: one run of a kernel over the whole buffer of a thread, from the first byte to the last.
- **Rep**: the name of an interval in the csv file (column 4). The option `--reps 3` asks for 3 intervals per process.
- **GB**: 1e9 bytes. **MiB**: 2^20 bytes. 256 MiB are 268435456 bytes.
- **GB/s**: 1e9 bytes per second, the unit of every rate in the file.
- **UTC**: Coordinated Universal Time, the time zone of every time in the file and in the folder names.
- **Huge pages, thp**: memory pages of 2 MiB that Linux can use in place of the small standard pages. "thp" stands for transparent huge pages, the Linux feature that provides them. `madvise` with `MADV_HUGEPAGE` is the call with which a program asks for them.
- **First touch**: the first write to a new buffer. Linux places the memory pages of the buffer at this moment.
- **Barrier**: a meeting point of the pthread library. A thread that reaches it waits until all 121 parties (120 threads and the main thread) have reached it.
- **Median**: the middle value of a sorted list. For 3 intervals it is the second highest value. For an even number of values it is the mean of the two middle values.
- **sha256 checksum**: a number of 64 hexadecimal digits that the tool `sha256sum` computes from the bytes of a file. Two files with the same checksum are taken as the same file.
- **Rerun**: the whole-chip read test of 2026-11-17, run by `go.sh` at a memory speed of 7200 MT/s. The earlier runs that it is compared with had a memory speed of 8000 MT/s.
- **Marker file** (facts sheet): `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **ra.sh**: the script of part A. **go.sh**: the driver script of the rerun. It runs 3 sessions.
- **facts.json, FACTS.md**: the data file and the text of the facts sheet of the rerun. `build_facts.py` writes both from the raw result files.
- **facts_data.py**: the file with the functions that read the raw result files for the facts sheet. `build_facts.py` uses these functions.
- **Rows A-1, A-2, A-3**: the three 8000 MT/s baselines of part A in the fixed list of the rules file. A-1 is the test of 2026-11-13 itself. A-2 and A-3 are later runs of the same day with the same binaries.
- **Rules file**: `S/baselines-and-rules.txt`, the list of baselines and comparison rules that was written before the rerun.
- **Tag**: the name that the script of the A-2 and A-3 runs gave to a process, for example `read_old-r1`.

</details>

## References

- [Ref1] `R/k120-T72A1-20261117T221209Z/threads120.csv`: session 1 file (first instance). Lines 1 to 7: first process, old read kernel. Lines 8 to 14: new read kernel, round 1. Lines 155 to 161: new read kernel, round 2. Lines 162 to 168: old read kernel, round 2.
- [Ref2] `R/k120-T72A2-20261117T221518Z/threads120.csv`: session 2 file. Same line numbers as [Ref1].
- [Ref3] `R/k120-T72A3-20261117T221827Z/threads120.csv`: session 3 file (last instance). Same line numbers as [Ref1]. Lines 158 and 160: the two rows of the new read kernel with another `total_bytes`.
- [Ref4] `S/ra.sh`: line 8 (`set -e`: the script stops at the first failed command), line 9 (the script runs on CPUs 0-119 only), lines 11 to 13 and line 40 (test of the marker file), lines 21 to 23 (folder name), lines 26 to 28 (wait before the first process), lines 39 to 43 (function `one`: header line and process start), lines 44 to 48 (order of the 24 processes).
- [Ref5] `S/go.sh`: lines 40 to 42 (one call of `ra.sh` per session, names T72A1 to T72A3).
- [Ref6] `K13/bandwidth.orig.c` (source of `bw_old`): lines 62 to 77 (size letters of `--bytes`), lines 79 to 105 (CPU list), lines 107 to 133 (pinning, buffer allocation, `madvise`), lines 257 to 286 (bytes counted per pass. Line 264 stores the sum that the old read kernel returns), lines 288 to 327 (function `worker`: pinning, first touch, warm-up, barrier, clock reads, stop rule), line 23 and lines 295 to 297 (number of passes between two clock reads), line 402 (barrier for 120 threads plus the main thread), lines 425 and 426 (the main thread waits at the barrier during a timed interval), lines 415 to 419 (formula line and column name line), lines 420 to 448 (sums, `agg`, interval row, best row), lines 449 to 457 (rows per thread of `--per-thread`).
- [Ref7] `K13/bandwidth.c` (source of `bw_new`): line 184 (the new read kernel returns no value), lines 417 to 444 (bytes counted per pass), lines 446 to 484 (function `worker`), lines 572 to 576 (formula line and column name line), lines 577 to 605 (sums, `agg`, interval row, best row), lines 606 to 614 (rows per thread). Lines 496 to 620 (`main`) are the same text as lines 339 to 463 of [Ref6].
- [Ref8] `K13/run_kernels.sh`: lines 31 and 32 (build of `bw_old` and `bw_new` on 2026-11-13). The companion text of `probe.txt` of part A lists the checksums that prove this.
- [Ref9] `S/stat_k120.py`: line 21 (regular expression of the header line), lines 24 to 44 (function `load`), lines 47 to 67 (statistics per kernel and binary).
- [Ref10] `S/facts_data.py`: lines 264 to 304 (function `read_k120`), line 436 (name of the rate kind of part A).
- [Ref11] `S/build_facts.py`: lines 66 to 72 (reads the three files), lines 119 to 140 (one record per interval row), lines 695 to 708 (shape and order checks), lines 798 to 815 (cross-check with `stat_k120.py`, with the copies under `S/base8000`).
- [Ref12] `S/make_report.py`: lines 166 to 173 (function `file_process`), lines 176 to 183 (the rate of a part A record is the csv value), lines 192 to 202 (range and median), lines 272 and 273 (selection of the `read` records of part A), lines 417 and 418 (function `drop`), lines 444 to 457 (pairs of process medians), lines 1209 to 1215 (scan of all csv files for `# bwx` lines), lines 2308 to 2316 (counts and order check over the records of all six kernels).
- [Ref13] `S/FACTS.md`: lines 38 to 67 and line 77 (word list), line 23 (part A: 28.5 % to 31.8 %), line 209 (hypothesis on the high load values, with the check that would confirm or reject it), line 241 (huge pages of part A are not recorded), lines 315 to 340 (table of the `read` and `asmread` processes of part A), lines 344 to 351 (medians per session and round), lines 354 and 355 (`asmread` against the old read kernel), line 357 (limit of part A), lines 359 and 385 (parts L and C: bwx12, common stop, 6 s), line 947 (hypothesis H4 on the pass counts of part A).
- [Ref14] `S/baselines-and-rules.txt`: lines 18 and 21 to 24 (baselines A-1 to A-3: 8000 MT/s, same binaries), lines 45 to 53 (the `sed` and `awk` commands of the copies), lines 55 to 58 (expected values).
- [Ref15] `S/base8000/partA-A1/threads120.csv`: line 1 (header), line 8 (first row per thread). Header lines at lines 1, 368, 735 and so on, every 367 lines.
- [Ref16] `S/base8000/partA-A3-onebuf500/threads120.csv`: header lines at lines 1, 368 and 735.
- [Ref17] `R/partA-20261113T205055Z/A1.csv` (4404 lines) and `R/partA-20261113T205055Z/A3.csv` (8772 lines): the original files of the copies. Line 1 of A1.csv is the sample header line. The 12 header lines of A1.csv and the header lines at lines 1, 1463 and 2925 of A3.csv (tags `onebuf-ms500-1`, `-2`, `-3`) hold `waited_s 0`.
- [Ref18] `R/kernels-20261113T181222Z/probe.txt` (timed run of 18:12:22 UTC on 2026-11-13) and `R/kernels-20261113T183218Z/probe.txt` (run of 18:32:18 UTC that built the binaries and timed nothing): line 1 (mode `all` or `probe`), line 15 (checksum of `bandwidth.c`), line 20 (checksum of `bw_new`). `K13/run_kernels.sh`: lines 4 to 6 and line 56 (the mode `probe` ends before the timed runs). The checksum of the local `K13/bandwidth.c` was computed with `sha256sum` in this task.
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh`: line 12 (the script runs on CPUs 0-119 only), lines 23 to 28 (function `why_stop`: the reasons to stop), lines 54 to 57 (function `settle`: the wait), lines 59 to 68 (function `one`: wait, header line, process start), lines 70 to 74 (the test once per second while a process runs, and the `-- killed` line). Its sha256 checksum (0f496ca6...) is equal to line 14 of `R/partA-20261113T205055Z/env.txt`.
- [Ref20] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
