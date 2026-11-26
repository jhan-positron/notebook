# `facts_data.py` explained

- Source file: `facts_data.py` in this folder (Python script, 485 lines, 23123 bytes).
- sha256 of the source when this page was built: `630b3c775d00071d282228310710c54639bc0bef778e580629fc71ad7c319206`.
- Role in the whole-chip test: Parsers of the raw result files and range functions for the facts sheet.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

This module reads the raw result files of the rerun (csv files, logs, state records) and gives one rate in GB/s for every timed interval. It also holds the functions that select intervals and compute the range (lowest, highest, median) that the facts sheet reports for each kernel.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rerun**: the whole-chip read test of 2026-11-17 on CRB, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Data set**: a named group of interval records. `build_facts.py` writes the name into the key `dataset` of each record [Ref3]. The files of the rerun give four data sets: `rerun-A`, `rerun-L`, `rerun-C` and `control-I`. Each one holds the intervals of all result folders of that part. The earlier runs have other names, for example `A-1` and `L-1`.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **GB/s**: gigabytes per second. GB = 1e9 bytes.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Page state**: what a P row holds for one buffer. `kB_total` is the size of the memory area of the buffer in kB. `kB_huge` is the part of this area that lies on transparent huge pages, in kB. The four other numbers are counters of Linux for the whole system. In a run with more than one thread, bwx12 prints a comment line `# page_read` after each reading of the page state. The line holds the time that the reading took, in ms [Ref2]. In such a run a P row with `pos` = -1 holds the state before the first interval of the process. Every other P row holds the state after the interval of its `round` and `pos` [Ref2].
- **Flag `late`**: With the common stop, bwx12 sets one start time for all threads of an interval. It writes `late` in the last field of a T row when the thread started more than 100 microseconds after that time. In every other case it writes `-`.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at nearly the same time (after 6 s). The runner sets one deadline for all threads. Each thread stops after the 2 MiB chunk in which the deadline passes [Ref2]. In the 74 intervals of the 9 bwx12 csv files of the rerun, the end times of the 120 threads of one interval differ by less than 0.5 ms (computed from the field `t_end_s` of the T rows with `read_bwx` of this module on 2026-11-21).
- **Pass count (`passes`)**: total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. For the kernels copy and asmcopy the same division gives 2 x the number of buffer passes. The reason: the binary counts the bytes read plus the bytes written for these two kernels [Ref1].
- **`best` row**: a row that bandwidth.c prints after the interval rows of one kernel. It holds the highest aggregate_GBps of these rows [Ref1]. This module takes no value from it.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **Log of go.sh, log of go2.sh**: the files go-T72-20261117T221209Z.log and go2-T72-20261117T222335Z.log in R. Each file holds the standard output and the error output of one script. The command that started the script sent both outputs to the file. No script of S holds this command [Ref10].
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time that a process has used, divided by the time since the process started.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **Tag**: a short name of a run step or of a process. Three kinds occur. First, the name that go.sh or go2.sh gives to a run script (T72A1, T72L1). Second, the first field of a spec line (a6456, cfwd, crev). Third, the tag of a `-- step` line of an earlier script.
- **Spec file**: the input file of rx.sh. Each line holds a tag, the character `|` and the arguments of one runner process.
- **Marker file**: /tmp/positron-perf.RUNNING. ra.sh and rx.sh stop when this file exists.
- **Journal**: the system log of Linux. The files read here are saved text copies with the messages of the Linux kernel.
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues).
- **thp**: transparent huge pages of Linux. In a csv header, `thp=madvise` says that the binary asked Linux for huge pages for its buffers (call madvise with MADV_HUGEPAGE).
- **SHA-256 checksum**: a value of 64 hexadecimal digits computed from the content of a file. The scripts use it to check that a binary or script is the expected file.
- **UTC**: Coordinated Universal Time. All dates and times of day in the run files are UTC. The values `t_start_s` and `t_end_s` of a T row are not times of day. They count the seconds from the process start.
- **Facts sheet, facts.json**: S/FACTS.md is the facts sheet: the text source for the report of the rerun. S/facts.json holds the interval records. build_facts.py writes both.
- **R, S**: R is the results folder crb/results. S is the scratch folder of the rerun, crb/tmp/agent-scratch/w120-7200-2026-11-17.
- **csv**: a text file with one row per line. Commas separate the fields of a row.
- **CPU frequency governor**: the Linux policy that selects the clock frequency of a CPU.
- **Tuple, `None`**: Python terms. A tuple is a fixed list of values. `None` is the value for "no value".
- **Pattern (regular expression)**: a text template. A line matches when it has the form of the template. The parts in round brackets are taken out as values.

</details>

## Main flow

1. The module has no main program and takes no arguments. Another script imports it. At import it derives the folder paths from its own place and imports `stat_bwx.py` and `stat_k120.py` (lines 23-34).
2. `build_facts.py` reads the machine records first: `read_try6` (line 206), `read_boot_table` (line 405), and `read_log` for the logs of `go.sh` and `go2.sh` [Ref3] (lines 83-114).
3. Part A: for each tag of `RERUN_A`, `find` gives the folder, `read_probe` reads `probe.txt` and `read_k120` reads `threads120.csv`. Each file of the rerun gives 24 processes with 3 intervals each. The rate of an interval is the printed column `aggregate_GBps` (lines 264-304).
4. Parts L and C and control I: for each tag of `RERUN_L`, `RERUN_C`, `RERUN_I`, `read_bwx` reads the one csv of the folder. It keeps the T rows of each interval (lines 313-353).
5. `bwx_intervals` forms the rate of each bwx12 interval: the sum over its T rows of bytes / elapsed_s / 1e9 (lines 356-383).
6. `read_env` and `read_launches` read the run records of each bwx12 folder: checksum of the runner, launch time, load at launch, exit status (lines 137-171).
7. `build_facts.py` copies every interval of the rerun into one record of `base_record`. `GBps` holds the rate and `rate_kind` holds `KIND_A` or `KIND_X` [Ref3] (lines 421-437).
8. `facts_text.py` and `facts_text4.py` pick the intervals of one kernel with `sel` and summarise them with `rng`. They compare two ranges with `overlap`, `gap` and `width_pct` [Ref4] (lines 442-485).

## Behavior a reader must know

- The module reads files and writes none. Every file it opens is recorded in the list `OPENED`.
- Part A rate: field 7 (`aggregate_GBps`) of each interval row, taken as printed. The binary computed it as the sum of the bytes of all threads / the longest per-thread time / 1e9 [Ref1]. The time of a thread starts at its clock read after the binary releases all threads together. It ends at its clock read after its last whole pass over the buffer. One warm-up pass of the same kernel comes before this time and is not timed [Ref1]. The `best` row and the column title row are left out. No kernel is left out: the rows of all six kernels of `bw_old` and `bw_new` are returned. For the kernels `copy` and `asmcopy` the binary counts the bytes read plus the bytes written [Ref1].
- bwx rate: the sum over all T rows of one interval of bytes / elapsed_s / 1e9. Each thread is divided by its own time. No T row is left out, also not a row with the flag `late`. The 9 bwx12 csv files of the rerun (parts L and C, control I) hold no row with this flag. The value `aggregate_GBps` of the I row is kept only for a cross-check. For a read kernel `bytes` is the size of the buffer ranges that the runner gave to the kernel. For the test loop `read_1pl` this is more than the bytes that the loop loads [Ref2].
- This module returns every interval of a file that it reads. The one exception is the argument `only_tags` of `read_k120`. `build_facts.py` keeps every interval of the rerun. For some bwx csv files outside the rerun it keeps only named kernels or positions (arguments `kernels` and `positions` of its function `add_bwx`) [Ref3].
- The two kinds of rate are not the same formula. For the same threads the part A form (all bytes / the longest time) can never be higher than the bwx form (sum of the per-thread rates). The two are equal when all threads have the same time. Example of the size of the difference at a common stop: T72L1, `a6456.csv`, round 0, position 0, `oldread`: 462.30 GB/s from the T rows and 462.29 GB/s in the I row [Ref8]. Example of the size of the difference at the whole-pass stop of part A: the first interval row of `threads120.csv` of T72A1 has `aggregate_GBps` = 467.83 GB/s. Its column `per_thread_avg_GBps` (3.99 GB/s, rounded to 2 decimals) x 120 threads gives about 478.8 GB/s (est.) for the sum of the per-thread rates [Ref9].
- This module rounds no rate. So `overlap` and `gap` compare the unrounded values of `rng`. The part A values have 2 decimals, as the binary printed them. `build_facts.py` rounds to 0.001 GB/s when it writes `facts.json` [Ref3]. `facts_text.py` rounds to 0.01 GB/s, half up, when it writes the facts sheet [Ref4].
- The result for one kernel is a range, not a mean: `rng` returns the lowest value, the highest value and the median of the selected intervals. Each interval counts once.
- The drop in percent of the new read kernel against the old read kernel is not formed in this module. It is also not formed from the ranges of `rng`. The function `analyse` of `facts_text.py` forms one drop per pair: (1 - new rate / old rate) x 100 [Ref4]. In part A a pair is the `bw_new` process and the `bw_old` process with the kernel `read` of the same session and round. Each of the two rates is the median of the 3 intervals of the process. For bwx12 a pair is one interval of `read` or `asmread` and the `oldread` interval of the same process and round.
- The module stops the script with an error in these cases. `find`: a result folder is missing or exists twice. `read_k120`: an interval row has another kernel name than its header line. `read_bwx`: a T row does not have 13 fields. `bwx_intervals`: a kernel name does not fit the sequence of the header. `read_try6`: row 0 of `boots.txt` is not the boot of `try6.txt`, or it has another form than expected. `base_record`: the caller passes a key that the record does not have.
- Most readers take values out of a matched pattern without a test. A file that lacks an expected line therefore also ends the script, with a Python error.
- The `-- step` header form, the argument `only_tags` and the per-thread rows (`thread,...`) are used only for csv files of earlier runs. The csv files of the rerun of 2026-11-17 do not hold them.

## Call sequence in the whole-chip test

- `build_facts.py:main`: entry point: writes facts.json and FACTS.md
  - `build_facts.py:collect`: reads all raw files and builds the interval records
    - `read_try6` (line 206): record of 12 modules at 7200 MT/s in the boot of the rerun
    - `read_boot_table` (line 405): boot history, used for the folders of earlier runs
    - `read_log` (line 83): state lines of the logs of go.sh and go2.sh
    - `find` (line 397): result folder of each tag of the rerun
    - `read_probe` (line 117): probe.txt of each part A folder
    - `read_k120` (line 264): part A csv: processes, interval rows, printed rate
    - `read_bwx` (line 313): bwx12 csv of parts L, C and control I
      - `_new_section` (line 309): empty container for the rows of the process
    - `bwx_intervals` (line 356): sum of the per-thread rates of each interval
    - `read_env` (line 159): env.txt: checksum of the runner, process list
    - `read_launches` (line 137): launches.txt: launch time, load, exit status
      - `clock` (line 68): time of day to full date and time
        - `folder_date` (line 62): date and time of the folder name
    - `build_facts.py:add_k120`: one record per part A interval, rate = agg
      - `rel` (line 46): folder path in the form R/...
      - `base_record` (line 421): record with all keys, rate kind KIND_A
    - `build_facts.py:add_bwx`: one record per bwx12 interval, rate = total
      - `bwx_intervals` (line 356): called again for the same section
      - `base_record` (line 421): record with all keys, rate kind KIND_X
    - `read_k120` (line 264): again, for the 8000 MT/s baseline files of part A
    - `build_facts.py:open_probe13`: records of the run of 2026-11-13
      - `read_error_records` (line 174): hardware error records of a saved journal
      - `step_headers` (line 193): step lines of the csv files of run_partA.sh
    - `read_bwx` (line 313): again, for the bwx csv files of earlier runs
    - `build_facts.py:hw_records`: hardware error records inside process windows
      - `read_error_records` (line 174): the same saved journal
  - `build_facts.py:run_checks`: integrity checks of the files and the records
    - `sha256` (line 55): checksums of the local copies of the run scripts
  - `facts_text.py:render`: text of the facts sheet
    - `facts_text.py:analyse`: pairs of old and new intervals, and record groups of several data sets
      - `sel` (line 442): intervals of one data set and kernel
    - `facts_text.py:compare`: 7200 MT/s range against 8000 MT/s range
      - `rng` (line 461): lowest, highest, median, counts
      - `overlap` (line 471): decides the wording of the comparison
      - `gap` (line 475): distance between the nearest ends
      - `width_pct` (line 484): width of the 8000 MT/s range in percent
  - `build_facts.py:write_json`: writes facts.json, rates rounded to 3 decimals

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `_open` | 39-43 | Records the absolute path in `OPENED`, then opens the file. | - | - |
| `rel` | 46-52 | Writes a path as `R/...` or `S/...` for the facts sheet. | - | - |
| `sha256` | 55-59 | Returns the SHA-256 checksum of a file. | `_open` | - |
| `folder_date` | 62-65 | Reads the date and time from a result folder name. | - | - |
| `clock` | 68-74 | Turns a time of day into a full date and time, with the date of the folder name. | `folder_date` | - |
| `read_log` | 83-114 | Reads the state lines and the other `== ` lines of a `go.sh` or `go2.sh` log. | `_open` | - |
| `read_probe` | 117-130 | Reads `probe.txt` of a part A folder: times, load, boot id, MemTotal, checksums. | `_open` | - |
| `read_launches` | 137-156 | Reads `launches.txt` of `rx.sh`: one entry per launch, with its exit status. | `_open`, `clock` | - |
| `read_env` | 159-171 | Reads `env.txt` of `rx.sh`: start time, load, process list, checksum of the runner. | `_open` | - |
| `read_error_records` | 174-190 | Lists the hardware error records of a saved journal with time, number and severity. | `_open` | - |
| `step_headers` | 193-203 | Lists the `-- step` header lines of a csv of the earlier script `run_partA.sh`. | `_open`, `clock` | - |
| `read_try6` | 206-255 | Reads the record of 12 modules at 7200 MT/s, checks its boot id against `boots.txt` and reads `gaps.txt`. | `_open` | - |
| `read_k120` | 264-304 | Reads a part A csv: one entry per process, with the interval rows and the printed rate `aggregate_GBps`. | `_open` | - |
| `_new_section` | 309-310 | Returns an empty container for the rows of one bwx process. | - | - |
| `read_bwx` | 313-353 | Reads a bwx csv: header values, T rows per interval, I rows, P rows, count of C rows. | `_open`, `_new_section` | - |
| `bwx_intervals` | 356-383 | Forms one entry per interval: the sum of the per-thread rates, in total and per mesh, plus checks. | - | - |
| `find` | 397-402 | Returns the one result folder whose name starts with a prefix. | - | - |
| `read_boot_table` | 405-418 | Reads the boot history and the end time of the 8000 MT/s setting from the DIMM report. | `_open` | - |
| `base_record` | 421-433 | Returns one interval record for `facts.json` with all 40 keys. | - | - |
| `sel` | 442-458 | Returns the records that match every condition. | - | - |
| `rng` | 461-468 | Returns lowest, highest and median value of a record list, with counts of intervals, processes, sessions and boots. | - | - |
| `overlap` | 471-472 | Says whether two ranges share at least one value. | - | - |
| `gap` | 475-481 | Returns the distance between the nearest ends of two ranges, with a sign. | - | - |
| `width_pct` | 484-485 | Returns the width of a range in percent of its lower end. | - | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Module comment: inputs and the two kinds of rate</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env python3
  2  """facts_data.py - parsers and the data model for the facts sheet of the 7200 MT/s rerun (2026-11-17).
  3
  4  Used by build_facts.py. It reads raw result files and writes nothing.
  5
  6  R = results folder, S = scratch folder of this task (both derived from the location of this file).
  7  GB = 1e9 bytes everywhere.
  8
  9  Two kinds of rate exist in the raw files, and this module never mixes them:
 10  - part A (binaries bw_old, bw_new of bandwidth.c): the column aggregate_GBps of the csv
 11    (the binary computes it as sum(bytes) / max(per-thread elapsed_s)).
 12  - bwx runners (bwx12, bwx11, bwx): sum over the T rows (threads) of bytes / elapsed_s / 1e9,
 13    the method of stat_bwx.py.
 14  """</pre></td><td valign="top">The module comment. The module only reads files, and GB means 1e9 bytes. It names two kinds of rate, and the code below keeps them separate:<ul><li><b>Part A</b> (binaries <code>bw_old</code> and <code>bw_new</code>): the rate is the csv column <code>aggregate_GBps</code>, as the binary printed it.</li><li><b>bwx runners</b> (<code>bwx12</code> and its older versions): this module computes the rate from the T rows (one row per thread). Each thread gives bytes / elapsed_s / 1e9. The values of all threads are added.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 15  import datetime as dt
 16  import glob
 17  import hashlib
 18  import os
 19  import re
 20  import statistics
 21  import sys
 22
 23  sys.dont_write_bytecode = True
 24</pre></td><td valign="top">Imports of the Python standard library. <code>sys.dont_write_bytecode = True</code>: Python writes no compiled copy (<code>.pyc</code> file) of the modules that are imported after this line.</td></tr>
<tr><td colspan="2"><b>Folder paths, derived from the place of this file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 25  S = os.path.dirname(os.path.abspath(__file__))
 26  CRB = os.path.normpath(os.path.join(S, '..', '..', '..'))
 27  R = os.path.join(CRB, 'results')
 28  W15 = os.path.join(CRB, 'tmp', 'agent-scratch', 'w120-2026-11-15')
 29  K13 = os.path.join(CRB, 'tmp', 'agent-scratch', 'kernels-2026-11-13')
 30  DIMM_REPORT = os.path.normpath(os.path.join(CRB, '..', '..', '..', 'machines', 'arm-crb', 'DIMM-flaky-report.md'))
 31</pre></td><td valign="top"><ul><li><code>S</code>: the folder of this file, the scratch folder of the rerun.</li><li><code>CRB</code>: three levels above <code>S</code>. Here the name means the project folder <code>crb</code>, not the machine.</li><li><code>R</code>: <code>crb/results</code>, the result folders that were copied back from the machine.</li><li><code>W15</code>, <code>K13</code>: the scratch folders of 2026-11-15 (script <code>rx.sh</code>) and of 2026-11-13 (benchmark sources).</li><li><code>DIMM_REPORT</code>: the report on the memory modules, <code>machines/arm-crb/DIMM-flaky-report.md</code>, three levels above <code>crb</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 32  sys.path.insert(0, S)
 33  import stat_bwx    # noqa: E402  (existing tool, used as a cross-check)
 34  import stat_k120   # noqa: E402  (existing tool, used as a cross-check)
 35</pre></td><td valign="top"><code>sys.path.insert(0, S)</code> makes Python search the folder <code>S</code> first when it imports a module. The next two lines import the two quick statistics scripts of that folder. This module uses <code>stat_k120.HDR</code>, the pattern of a part A header line, in <code>read_k120</code> (line 271). <code>build_facts.py</code> also calls both scripts through this module to cross-check the numbers [Ref3].</td></tr>
<tr><td colspan="2"><b>Function <code>_open</code>: open a file and record its path</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 36  OPENED = []  # every file that a reader of this module opened, in order (for the file list of the facts sheet)
 37
 38
 39  def _open(path, mode='r'):
 40      path = os.path.abspath(path)
 41      if path not in OPENED:
 42          OPENED.append(path)
 43      return open(path, mode)
 44
 45</pre></td><td valign="top"><code>OPENED</code> is the list of the files that this module opened, in order, each path once. <code>_open</code> adds the absolute path to the list and then opens the file. Every reader below opens its file through <code>_open</code>. <code>facts_text.py</code> stops the script when the file list of the facts sheet does not name every file of <code>OPENED</code> [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>rel</code>: short path for the facts sheet</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 46  def rel(path):
 47      """Path as written in the facts sheet: R/... or S/..."""
 48      path = os.path.abspath(path)
 49      for name, root in (('R', R), ('S', S)):
 50          if path.startswith(root + os.sep):
 51              return name + '/' + os.path.relpath(path, root)
 52      return path
 53
 54</pre></td><td valign="top">Shortens a path for the facts sheet. A path under the results folder becomes <code>R/...</code>. A path under the scratch folder becomes <code>S/...</code>. Any other path is returned as an absolute path.</td></tr>
<tr><td colspan="2"><b>Function <code>sha256</code>: checksum of a file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 55  def sha256(path):
 56      h = hashlib.sha256()
 57      with _open(path, 'rb') as f:
 58          h.update(f.read())
 59      return h.hexdigest()
 60
 61</pre></td><td valign="top">Returns the SHA-256 checksum of a file as 64 hexadecimal digits.</td></tr>
<tr><td colspan="2"><b>Function <code>folder_date</code>: time in a folder name</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 62  def folder_date(folder):
 63      """Date and time in a folder name such as k120-T72A1-20261117T221209Z."""
 64      m = re.search(r'(\d{8})T(\d{6})Z', os.path.basename(folder))
 65      return dt.datetime.strptime(m[1] + m[2], '%Y%m%d%H%M%S')
 66
 67</pre></td><td valign="top">Reads the date and time from the name of a result folder. Example: <code>k120-T72A1-20261117T221209Z</code> gives 2026-11-17 22:12:09. <code>ra.sh</code> and <code>rx.sh</code> put the UTC time at which they create the folder into its name [Ref5] [Ref6].</td></tr>
<tr><td colspan="2"><b>Function <code>clock</code>: time of day to full date and time</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 68  def clock(folder, hms):
 69      """HH:MM:SS of a run file -&gt; datetime, with the date of the folder name (next day if earlier)."""
 70      base = folder_date(folder)
 71      t = dt.datetime.combine(base.date(), dt.datetime.strptime(hms, '%H:%M:%S').time())
 72      if t &lt; base - dt.timedelta(seconds=1):
 73          t += dt.timedelta(days=1)
 74      return t
 75
 76</pre></td><td valign="top">Turns a time of day <code>HH:MM:SS</code> from a run file into a full date and time. The date comes from the folder name. When the result lies more than 1 s before the time of the folder name, one day is added. That is the case of a run that passed midnight.</td></tr>
<tr><td colspan="2"><b>Readers of logs and state files</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 77  # ----------------------------------------------------------------------------- logs and state files
 78
 79  STATE = re.compile(r'^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) '
 80                     r'users (\d+) marker (\S+) processes per user:\s*(.*)$')
 81
 82</pre></td><td valign="top"><code>STATE</code> is the pattern (regular expression) of one state line. <code>go.sh</code> and <code>go2.sh</code> print state lines at the start, around the run steps and at the end [Ref7]. The fields of the line, in order:<ul><li>a label, the UTC time and the boot id.</li><li><code>MemTotal</code> in kB.</li><li>the five fields of <code>/proc/loadavg</code>.</li><li><code>users</code>: the number of logins.</li><li><code>marker</code>: <code>present</code> or <code>absent</code>. It says whether the file <code>/tmp/positron-perf.RUNNING</code> existed.</li><li>the number of processes per user.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_log</code>: log of <code>go.sh</code> or <code>go2.sh</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 83  def read_log(path):
 84      """State lines and the other '== ' lines of a go.sh or go2.sh log."""
 85      out = dict(path=path, states=[], other={}, lines=[], alldone=False, failed=[])
 86      with _open(path) as f:
 87          for ln, line in enumerate(f, 1):
 88              line = line.rstrip('\n')
 89              out['lines'].append(line)
 90              m = STATE.match(line)
 91              if m:
 92                  users = {}
 93                  for part in m[13].split(';'):
 94                      part = part.strip()
 95                      if part:
 96                          n, name = part.split()
 97                          users[name] = int(n)
 98                  out['states'].append(dict(
 99                      label=m[1], utc=dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%SZ'), boot=m[3], memtotal_kB=int(m[4]),
100                      load1=float(m[5]), load5=float(m[6]), load15=float(m[7]), runnable=int(m[8]), tasks=int(m[9]),
101                      logins=int(m[11]), marker=m[12], procs=users, line=ln, file=path))</pre></td><td valign="top">Reads the log line by line and keeps every line in <code>lines</code>. A state line becomes one entry in <code>states</code>:<ul><li><code>label</code>: for example <code>start</code>, <code>after T72A1</code> or <code>idle before T72I1</code>.</li><li><code>utc</code>, <code>boot</code>, <code>memtotal_kB</code>.</li><li><code>load1</code>, <code>load5</code>, <code>load15</code>: the load averages over 1, 5 and 15 minutes.</li><li><code>runnable</code>, <code>tasks</code>: the tasks that are runnable now, and the number of all tasks.</li><li><code>logins</code>, <code>marker</code>, and <code>procs</code> (user name to number of processes).</li><li><code>line</code>: the line number in the log. The fifth field of <code>/proc/loadavg</code> (the id of the newest process) is matched and not stored.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">102              elif line.startswith('== cmdline '):
103                  out['other']['cmdline'] = (line[len('== cmdline '):], ln)
104              elif line.startswith('== governors'):
105                  out['other']['governors'] = (line[3:], ln)
106              elif line.startswith('== thp '):
107                  out['other']['thp'] = (line[3:], ln)
108              elif line.startswith('== affinity'):
109                  out['other']['affinity'] = (line[3:], ln)
110              elif line == 'ALLDONE':
111                  out['alldone'] = True
112              elif line.startswith('FAILED'):
113                  out['failed'].append(line)
114      return out
115
116</pre></td><td valign="top">The other lines of the log:<ul><li><code>== cmdline</code>, <code>== governors</code>, <code>== thp</code>, <code>== affinity</code>: the text and the line number go to <code>other</code>. These four lines hold the Linux boot arguments, the CPU frequency governors, the huge-page setting and the CPU list of the shell. Only <code>go.sh</code> prints them.</li><li>The line <code>ALLDONE</code> sets <code>alldone</code> to true. <code>go.sh</code> and <code>go2.sh</code> print it as their last line.</li><li>A line that starts with <code>FAILED</code> is added to <code>failed</code>. The two scripts print such a line when a check or a run step fails.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_probe</code>: <code>probe.txt</code> of a part A folder</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">117  def read_probe(path):
118      """probe.txt of ra.sh (part A)."""
119      txt = _open(path).read()
120      m1 = re.search(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+) name=(\S+)', txt)
121      m2 = re.search(r'## boot_id=(\S+) MemTotal: (\d+) kB runnable=(\d+)', txt)
122      m3 = re.search(r'## kernel=(\S+) thp=(.*)', txt)
123      m4 = re.search(r'## load_after=(\S+) (\S+) (\S+) utc=(\S+) MemTotal: (\d+) kB', txt)
124      shas = dict((os.path.basename(n), h) for h, n in re.findall(r'^([0-9a-f]{64})  (\S+)$', txt, re.M))
125      pcpu = [float(x) for x in re.findall(r'^\s*(\d+\.\d+) \S+\s+\S+', txt, re.M)]
126      T = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
127      return dict(path=path, utc=T(m1[1]), load_before=(float(m1[2]), float(m1[3]), float(m1[4])), logins=int(m1[5]),
128                  name=m1[6], boot=m2[1], memtotal_kB=int(m2[2]), runnable=int(m2[3]), kernel=m3[1], thp=m3[2].strip(),
129                  load_after=(float(m4[1]), float(m4[2]), float(m4[3])), utc_after=T(m4[4]), memtotal_after_kB=int(m4[5]),
130                  sha=shas, pcpu_max=max(pcpu) if pcpu else None)
131
132</pre></td><td valign="top">Reads the file <code>probe.txt</code> that <code>ra.sh</code> writes into a part A folder [Ref5]. It returns:<ul><li><code>utc</code>, <code>load_before</code>, <code>logins</code>, <code>name</code>: the time, the three load averages, the number of logins and the name of the step, read directly before the first process.</li><li><code>boot</code>, <code>memtotal_kB</code>, <code>runnable</code>: the boot id, <code>MemTotal</code> and the number of runnable tasks. <code>ra.sh</code> reads this number in its wait loop, 5 s or more before the time <code>utc</code> [Ref5].</li><li><code>kernel</code>: the Linux kernel release. <code>thp</code>: the huge-page setting of Linux.</li><li><code>load_after</code>, <code>utc_after</code>, <code>memtotal_after_kB</code>: read after the last process.</li><li><code>sha</code>: file name to SHA-256 checksum, for <code>bw_old</code>, <code>bw_new</code> and <code>ra.sh</code>.</li><li><code>pcpu_max</code>: the highest %CPU value of the process list in the file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">133  LAUNCH = re.compile(r'^launch (\S+) utc (\S+) load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) users (\d+) args (.*)$')
134  RC = re.compile(r'^rc (\S+) (\S+) utc (\S+)$')
135
136</pre></td><td valign="top">The patterns of the two line kinds of <code>launches.txt</code> [Ref6].<ul><li><code>rx.sh</code> writes a <code>launch</code> line directly before it starts a process: tag, time of day, the five fields of <code>/proc/loadavg</code>, number of logins, arguments of the binary. The tag is the first field of the spec line, for example <code>a6456</code>.</li><li>It writes an <code>rc</code> line when the process has ended: exit status, tag, time of day.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_launches</code>: <code>launches.txt</code> of <code>rx.sh</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">137  def read_launches(folder):
138      """launches.txt of rx.sh: one dict per launch, with its rc line."""
139      out = []
140      with _open(os.path.join(folder, 'launches.txt')) as f:
141          for ln, line in enumerate(f, 1):
142              line = line.rstrip('\n')
143              m = LAUNCH.match(line)
144              if m:
145                  out.append(dict(tag=m[1], utc=clock(folder, m[2]), load1=float(m[3]), load5=float(m[4]),
146                                  load15=float(m[5]), runnable=int(m[6]), tasks=int(m[7]), logins=int(m[9]), args=m[10],
147                                  rc=None, rc_utc=None, line=ln))
148                  continue
149              m = RC.match(line)
150              if m:
151                  for la in out:
152                      if la['tag'] == m[2] and la['rc'] is None:
153                          la['rc'] = m[1]
154                          la['rc_utc'] = clock(folder, m[3])
155                          break
156      return out
157
158</pre></td><td valign="top">Returns one entry per <code>launch</code> line: tag, launch time (through <code>clock</code>), the three load averages, the runnable tasks, the number of all tasks, the logins, the arguments and the line number. An <code>rc</code> line fills <code>rc</code> (the exit status, kept as text) and <code>rc_utc</code> of the first entry with the same tag that has no exit status yet.</td></tr>
<tr><td colspan="2"><b>Function <code>read_env</code>: <code>env.txt</code> of <code>rx.sh</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">159  def read_env(folder):
160      """env.txt of rx.sh."""
161      lines = _open(os.path.join(folder, 'env.txt')).read().splitlines()
162      m = None
163      for l in lines:
164          m = re.match(r'binary (\S+) ([0-9a-f]{64})', l) or m
165      pcpu = [float(x) for x in re.findall(r'^\S+\s+(\d+(?:\.\d+)?) \S+', '\n'.join(lines[3:]), re.M)]
166      # the process list of `ps -eo user,pcpu,comm --sort=-pcpu | head -6`: (user, %CPU, command, line number)
167      top = [(t[1], float(t[2]), t[3], ln) for ln, t in ((ln, re.match(r'^(\S+)\s+(\d+(?:\.\d+)?) (\S+)', l))
168                                                        for ln, l in enumerate(lines, 1) if ln &gt; 3) if t]
169      start = dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y')
170      return dict(start=start, kernel=lines[1], loadavg=lines[2], binary=m[1] if m else None, sha=m[2] if m else None,
171                  pcpu_max=max(pcpu) if pcpu else None, top=top, n_lines=len(lines))
172
173</pre></td><td valign="top"><code>rx.sh</code> writes <code>env.txt</code> once, before its first process [Ref6]. The function returns:<ul><li><code>start</code>: line 1, the date and time.</li><li><code>kernel</code>: line 2, the Linux kernel release.</li><li><code>loadavg</code>: line 3, the content of <code>/proc/loadavg</code>, as text.</li><li><code>binary</code>, <code>sha</code>: the path and the SHA-256 checksum of the runner, from the last line of the form <code>binary PATH CHECKSUM</code>. Both are <code>None</code> when the file has no such line.</li><li><code>top</code>: the rows of the process list after line 3, as (user, %CPU, command, line number). <code>pcpu_max</code> is the highest %CPU value.</li><li><code>n_lines</code>: the number of lines of the file.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_error_records</code>: hardware error records of a journal</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">174  def read_error_records(path):
175      """Hardware error records of a saved journal. One record = one line
176      'Hardware error from APEI Generic Hardware Error Source'. Returns line, time, record number, severity."""
177      out, by_id = [], {}
178      with _open(path) as f:
179          for ln, l in enumerate(f, 1):
180              m = re.match(r'(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$', l.rstrip('\n'))
181              if not m:
182                  continue
183              if m[3].startswith('Hardware error from APEI'):
184                  rec = dict(line=ln, utc=dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S'), id=int(m[2]), severity=None)
185                  out.append(rec)
186                  by_id[int(m[2])] = rec
187              s = re.match(r'event severity: (\S+)', m[3])
188              if s and int(m[2]) in by_id and by_id[int(m[2])]['severity'] is None:
189                  by_id[int(m[2])]['severity'] = s[1]
190      return out
191
192</pre></td><td valign="top">Reads a saved text copy of the journal. It uses only lines that carry <code>{N}[Hardware Error]:</code>, where N is the record number. A line whose text starts with <code>Hardware error from APEI</code> opens a new record with its line number, its time and N. The first later line <code>event severity: ...</code> with the same N gives the severity of that record, for example <code>corrected</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>step_headers</code>: <code>-- step</code> lines of an earlier csv</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">193  def step_headers(path):
194      """Every '-- step' line of a run_partA.sh csv: line, tag, binary, kernel, launch time."""
195      out = []
196      folder = os.path.dirname(path)
197      with _open(path) as f:
198          for ln, l in enumerate(f, 1):
199              m = HDR_STEP.match(l.rstrip('\n'))
200              if m:
201                  out.append(dict(line=ln, tag=m[2], binary=m[3], kernel=re.search(r'--kernel (\S+)', m[12])[1],
202                                  utc=clock(folder, m[11]), args=m[12], load1=float(m[5]), step=m[1]))
203      return out
204
205</pre></td><td valign="top">Returns one entry per line that matches <code>HDR_STEP</code> (line 260): line number, tag, binary, kernel name (the word after <code>--kernel</code> in the arguments), launch time, arguments, 1-minute load average and step name. The csv files of the rerun of 2026-11-17 have no <code>-- step</code> line. <code>build_facts.py</code> calls this function for csv files of the earlier script <code>run_partA.sh</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>read_try6</code>: record of 12 modules at 7200 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">206  def read_try6():
207      """R/dimm7200-20261117/try6.txt: the record of 12 modules at 7200 MT/s in the boot of the rerun."""
208      path = os.path.join(R, 'dimm7200-20261117', 'try6.txt')
209      lines = _open(path).read().splitlines()
210      out = dict(path=path, utc=dt.datetime.strptime(lines[0], '%Y-%m-%dT%H:%M:%SZ'), boot=lines[1].strip(),
211                 utc_line=1, boot_line=2, n_lines=len(lines))
212      for ln, l in enumerate(lines, 1):
213          m = re.match(r'MemTotal:\s+(\d+) kB', l)
214          if m:
215              out['memtotal_kB'], out['memtotal_line'] = int(m[1]), ln
216          m = re.search(r'This system has (\d+) DIMM sockets', l)
217          if m:
218              out['dimm_sockets'], out['dimm_line'] = int(m[1]), ln
219          m = re.match(r'\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s', l)
220          if m:
221              out['speed_count'], out['speed_MTps'], out['speed_line'] = int(m[1]), int(m[2]), ln
222          m = re.match(r'hwerr=(\d+)', l)
223          if m:
224              out['hwerr'], out['hwerr_line'] = int(m[1]), ln</pre></td><td valign="top">Reads <code>R/dimm7200-20261117/try6.txt</code>, the record of the memory modules in the boot of the rerun. Line 1 gives the time and line 2 gives the boot id. The loop finds four more values, each with its line number:<ul><li><code>memtotal_kB</code>: <code>MemTotal</code> in kB.</li><li><code>dimm_sockets</code>: the number in the Linux kernel message <code>This system has N DIMM sockets</code>.</li><li><code>speed_count</code>, <code>speed_MTps</code>: the leading count and the speed of the line <code>12 Configured Memory Speed: 7200 MT/s</code>.</li><li><code>hwerr</code>: the number after <code>hwerr=</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">225      # gaps.txt and boots.txt number the boots of the journal; row 0 must be the boot of try6.txt
226      boots = os.path.join(R, 'dimm7200-20261117', 'boots.txt')
227      row0 = [(ln, l.split()) for ln, l in enumerate(_open(boots), 1) if l.split()[:1] == ['0']]
228      if len(row0) != 1 or row0[0][1][1] != out['boot'].replace('-', ''):
229          sys.exit('boots.txt: row 0 is not the boot of try6.txt')
230      out['boots_path'], out['boots_line'] = boots, row0[0][0]
231      f = row0[0][1]              # 0 &lt;boot id&gt; Tue 2026-11-17 20:02:21 UTC Tue 2026-11-17 20:06:19 UTC
232      if len(f) != 10 or f[5] != 'UTC' or f[9] != 'UTC':
233          sys.exit('boots.txt: row 0 has another form than expected')
234      out['boots_first'] = dt.datetime.strptime(f[3] + ' ' + f[4], '%Y-%m-%d %H:%M:%S')
235      out['boots_last'] = dt.datetime.strptime(f[7] + ' ' + f[8], '%Y-%m-%d %H:%M:%S')</pre></td><td valign="top">Checks <code>boots.txt</code> of the same folder. That file lists the boots of the journal, one per row: boot number, boot id, first time, last time.<ul><li>Exactly one row must have the number 0. Its boot id must equal the boot id of <code>try6.txt</code>, compared without the <code>-</code> characters.</li><li>That row must have 10 fields, with <code>UTC</code> as field 6 and field 10.</li><li>When one of these tests fails, the script stops with an error.</li><li><code>boots_first</code> and <code>boots_last</code> are the two times of that row.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">236      # first kernel log line of this boot (gaps.txt, row "0 first=...")
237      gaps = os.path.join(R, 'dimm7200-20261117', 'gaps.txt')
238      for ln, l in enumerate(_open(gaps), 1):
239          m = re.match(r'0 first=(\S+)\+00:00 last=(\S+)\+00:00 dimm=has (\d+) DIMM hwerr=(\d+) ', l)
240          if m:
241              out['first_log_utc'] = dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S')
242              out['last_log_utc'] = dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%S')
243              out['gaps_dimm'], out['gaps_hwerr'] = int(m[3]), int(m[4])
244              out['gaps_path'], out['gaps_line'] = gaps, ln
245              continue
246          # lines after row 0: output of `uptime` and of the process list, taken when gaps.txt was written
247          m = re.match(r'\s*(\d\d:\d\d:\d\d) up ', l)
248          if m and 'first_log_utc' in out:
249              out['gaps_uptime_utc'] = dt.datetime.combine(out['first_log_utc'].date(),
250                                                           dt.datetime.strptime(m[1], '%H:%M:%S').time())
251              out['gaps_uptime_line'] = ln
252          m = re.match(r'(\S+)\s+(\d+\.\d+) (\S+)$', l.rstrip())
253          if m and 'gaps_uptime_utc' in out:
254              out.setdefault('gaps_top', []).append((m[1], float(m[2]), m[3], ln))
255      return out
256
257</pre></td><td valign="top">Reads <code>gaps.txt</code> of the same folder. The row that starts with <code>0 first=</code> gives the first and the last time of the Linux kernel log of this boot, a DIMM count and a <code>hwerr</code> count. The lines after that row are the output of <code>uptime</code> and a process list. The function stores the time of the <code>uptime</code> line (with the date of the first log time) and the rows of the process list as (user, %CPU, command, line number).</td></tr>
<tr><td colspan="2"><b>Part A files: csv of <code>bw_old</code> and <code>bw_new</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">258  # ----------------------------------------------------------------------------- part A files (bandwidth.c)
259
260  HDR_STEP = re.compile(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\d+)/(\d+) '
261                        r'logins (\d+) utc (\S+) args (.*)$')
262
263</pre></td><td valign="top"><code>HDR_STEP</code> is the pattern of a <code>-- step</code> header line. The earlier scripts <code>run_partA.sh</code> and <code>run_bwx.sh</code> wrote such a line as the header of each process. <code>ra.sh</code> and <code>rx.sh</code> of the rerun do not write this form. The fields of the line, in order:<ul><li>step, tag and binary.</li><li>the wait time (<code>waited_s</code>).</li><li>the three load averages, the runnable tasks and the number of all tasks.</li><li>the logins, the time of day and the arguments of the binary.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_k120</code>: processes and intervals of a part A csv</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">264  def read_k120(path, only_tags=None):
265      """Processes of a bandwidth.c csv. Header lines are '-- binary ...' (run_kernels.sh, ra.sh)
266      or '-- step ...' (run_partA.sh). Returns the processes in file order."""
267      procs, cur = [], None
268      with _open(path) as f:
269          for ln, line in enumerate(f, 1):
270              line = line.rstrip('\n')
271              m = stat_k120.HDR.match(line)
272              if m:
273                  cur = dict(file=path, hdr_line=ln, binary=m[1], kernel=m[2], round=int(m[6]), load1=float(m[7]),
274                             utc=m[8], tag=None, args=None, iv=[], hdr_threads=m[3], hdr_cpus=m[4], hdr_bytes=m[5])
275                  procs.append(cur)
276                  continue</pre></td><td valign="top">Reads a part A csv such as <code>threads120.csv</code> line by line. A line that matches <code>stat_k120.HDR</code> (<code>-- binary ...</code>) starts a new process. <code>ra.sh</code> writes this line directly before it starts the binary [Ref5]. The entry holds:<ul><li><code>binary</code>: <code>bw_old</code> or <code>bw_new</code>. <code>kernel</code>: the kernel name. With the kernel <code>read</code>, <code>bw_old</code> is the old read kernel and <code>bw_new</code> is the new read kernel.</li><li><code>round</code>: the round of the script (1 or 2).</li><li><code>load1</code>: the 1-minute load average at launch. <code>utc</code>: the time of day.</li><li><code>hdr_threads</code>, <code>hdr_cpus</code>, <code>hdr_bytes</code>: thread count, CPU list and buffer size of the header line, as text.</li><li><code>iv</code>: the list of intervals, empty at first.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">277              m = HDR_STEP.match(line)
278              if m:
279                  k = re.search(r'--kernel (\S+)', m[12])[1]
280                  rd = re.search(r'-r?(\d+)$', m[2])
281                  cur = dict(file=path, hdr_line=ln, binary=m[3], kernel=k, round=int(rd[1]), load1=float(m[5]),
282                             utc=m[11], tag=m[2], args=m[12], iv=[])
283                  if only_tags is None or only_tags(m[2]):
284                      procs.append(cur)
285                  else:
286                      cur['skip'] = True
287                  continue</pre></td><td valign="top">The header form of the earlier script <code>run_partA.sh</code>. The csv files of the rerun have no such header.<ul><li>The kernel name is the word after <code>--kernel</code> in the arguments.</li><li>The round is the number at the end of the tag.</li><li>When the caller passes a test function <code>only_tags</code>, a process whose tag fails the test is not added to the result. The interval rows after it are then dropped with it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">288              if cur is not None and line.startswith('# bandwidth:'):
289                  # header line that the binary prints: it says how the copy kernels count their bytes
290                  cur['copy_note'] = 'copy counts read+write bytes' in line
291                  cur['bw_hdr'] = line.split('; ')[-1]       # threads=... bytes_per_thread=... min_ms=... thp=...
292                  continue</pre></td><td valign="top">The comment line that the binary prints first. <code>copy_note</code> records whether the line holds the text <code>copy counts read+write bytes</code>. The text means that the binary counts the bytes read plus the bytes written for the kernels <code>copy</code> and <code>asmcopy</code> [Ref1]. <code>bw_hdr</code> keeps the last part of the line: threads, bytes per thread, <code>min_ms</code> (the shortest length of one interval in ms) and <code>thp</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">293              p = line.split(',')
294              if cur is not None and p[0] == 'thread' and len(p) == 6:
295                  # row of the option --per-thread: thread,index,cpu,kernel,rep,GBps
296                  cur.setdefault('thr', {}).setdefault(int(p[4]), []).append(float(p[5]))
297                  continue</pre></td><td valign="top">Splits the line at the commas. A row with 6 fields that starts with <code>thread</code> is a per-thread row of the option <code>--per-thread</code>. Its rate (field 6, GB/s) is stored per repetition in <code>thr</code>. The csv files of the rerun hold no such row: <code>ra.sh</code> does not pass <code>--per-thread</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">298              if cur is not None and len(p) &gt; 9 and p[3].isdigit():
299                  if p[0] != cur['kernel'] and cur['kernel'] != 'all':
300                      sys.exit(f'{path}:{ln}: interval line does not belong to the header line before it')</pre></td><td valign="top"><b>Which rows count as interval rows.</b> A row after a header line is an interval row when it has at least 10 fields and its field 4 (<code>rep</code>) is a number. This test leaves out the column title row and the <code>best</code> row. The script stops with an error when field 1 (the kernel name) differs from the kernel of the header line before it, unless that header says <code>all</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">301                  cur['iv'].append(dict(rep=int(p[3]), total_bytes=int(p[4]), elapsed_s=float(p[5]), agg=float(p[6]),
302                                        tmin=float(p[7]), tmax=float(p[8]), tavg=float(p[9]),
303                                        passes=int(p[4]) // int(p[2]), threads=int(p[1]), line=ln, kernel=p[0]))
304      return procs
305
306</pre></td><td valign="top"><b>The part A rate.</b> Each interval row becomes one entry in <code>iv</code>. No value is computed again here, except <code>passes</code>:<ul><li><code>agg</code> = field 7, <code>aggregate_GBps</code>. This is the rate of the interval. The binary computed it as the sum of the bytes of all threads / the longest per-thread time / 1e9, and printed it with 2 decimals [Ref1].</li><li><code>total_bytes</code> = field 5. <code>elapsed_s</code> = field 6, the longest per-thread time in seconds.</li><li><code>tmin</code>, <code>tmax</code>, <code>tavg</code> = fields 8, 9, 10: the lowest, highest and mean per-thread rate in GB/s.</li><li><code>passes</code> = field 5 / field 3 (<code>bytes_per_thread</code>), rounded down.</li><li><code>rep</code>, <code>threads</code>, <code>kernel</code> and the line number of the row.</li><li>Example: the first interval row of <code>threads120.csv</code> of T72A1 is <code>read,120,268435456,0,256087425024,0.5474,467.83,2.98,4.93,3.99</code>. It gives <code>agg</code> = 467.83 GB/s and <code>passes</code> = 954 [Ref9].</li></ul></td></tr>
<tr><td colspan="2"><b>bwx csv files. Function <code>_new_section</code>: empty container for one process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">307  # ----------------------------------------------------------------------------- bwx csv files
308
309  def _new_section(path, step=None, line=None):
310      return dict(file=path, step=step, step_line=line, hdr={}, T={}, Tl={}, I={}, P=[], C=0)
311
312</pre></td><td valign="top">Returns an empty container for the rows of one process:<ul><li><code>step</code>, <code>step_line</code>: the values and the line number of the <code>-- step</code> header line, if the file has one.</li><li><code>hdr</code>: the values of the comment lines at the top of the csv.</li><li><code>T</code>: the T rows. <code>Tl</code>: the line range of the T rows.</li><li><code>I</code>: the I rows. <code>P</code>: the P rows. <code>C</code>: the number of C rows.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>read_bwx</code>: rows of a bwx csv</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">313  def read_bwx(path):
314      """Sections of a bwx csv. A file of rx.sh has one section. A file of run_bwx.sh (B7, C3, B5)
315      has one section per '-- step' line."""
316      secs, cur = [], None
317      with _open(path) as f:
318          for ln, line in enumerate(f, 1):
319              line = line.rstrip('\n')
320              if line.startswith('-- step'):
321                  m = HDR_STEP.match(line)
322                  cur = _new_section(path, dict(step=m[1], tag=m[2], binary=m[3], load1=float(m[5]), load5=float(m[6]),
323                                                load15=float(m[7]), runnable=int(m[8]), logins=int(m[10]), utc=m[11],
324                                                args=m[12]), ln)
325                  secs.append(cur)
326                  continue
327              if cur is None:
328                  cur = _new_section(path)
329                  secs.append(cur)</pre></td><td valign="top">Reads the csv of a runner, for example <code>a6456.csv</code> (part L, control I) or <code>cfwd.csv</code> and <code>crev.csv</code> (part C).<ul><li>A csv that <code>rx.sh</code> wrote has no <code>-- step</code> line. The whole file is then one section, and it holds one process.</li><li>A csv of the earlier script <code>run_bwx.sh</code> has one <code>-- step</code> line per process. Each such line starts a new section and its values are stored in <code>step</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">330              if line.startswith('#'):
331                  if line.startswith('# bandwidth:') or line.startswith('# bwx:'):
332                      for key in ('min_ms', 'thp', 'seq', 'rounds', 'stop', 'start', 'two_buffers', 'count'):
333                          m = re.search(r'\b%s=([^\s;]+)' % key, line)
334                          if m and key not in cur['hdr']:
335                              cur['hdr'][key] = m[1]
336                  continue</pre></td><td valign="top">Comment lines start with <code>#</code>.<ul><li>From the lines <code># bandwidth:</code> and <code># bwx:</code> the function stores 8 values in <code>hdr</code>, as text: <code>min_ms</code>, <code>thp</code>, <code>seq</code>, <code>rounds</code>, <code>stop</code>, <code>start</code>, <code>two_buffers</code>, <code>count</code>. The first value found is kept.</li><li><code>seq</code> is the kernel sequence of the process, for example <code>oldread,asmread,read_nop96,read_nop256,read_1pl</code>.</li><li><code>stop</code> is the stop rule [Ref2]. <code>common</code>: the runner sets one start time and one deadline, <code>min_ms</code> milliseconds later, for all threads. Each thread stops after the chunk (2 MiB here) in which the deadline passes. <code>pass</code>: each thread stops after a whole pass over its buffer, <code>min_ms</code> milliseconds or more after its own start.</li><li><code>start</code> is not a time. It is the place in its buffer where a thread starts: <code>common</code> (the start of the buffer) or <code>offset</code> (a 2 MiB chunk that depends on the thread number) [Ref2].</li><li>All 9 bwx12 csv files of the rerun (parts L and C, control I) say <code>stop=common</code> and <code>start=common</code>.</li><li>Every other comment line is skipped, for example the column title lines and the <code># page_read</code> lines.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">337              p = line.split(',')
338              if p[0] == 'T':
339                  if len(p) != 13:
340                      sys.exit(f'{path}:{ln}: a T row with {len(p)} fields, 13 expected')
341                  # cpu, bytes, elapsed_s, flags, t_start_s, t_end_s (seconds since the process start)
342                  cur['T'].setdefault((int(p[1]), int(p[2]), p[3]), []).append(
343                      (int(p[5]), int(p[6]), float(p[7]), p[-1], float(p[9]), float(p[10])))
344                  tl = cur['Tl'].setdefault((int(p[1]), int(p[2]), p[3]), [ln, ln])
345                  tl[1] = ln</pre></td><td valign="top"><b>T rows: one row per thread and interval.</b> A T row must have 13 fields, or the script stops. The key of an interval is (round, pos, kernel name), from fields 2 to 4. For each thread 6 values are kept [Ref2]:<ul><li><code>cpu</code> = field 6: the CPU of the thread.</li><li><code>bytes</code> = field 7: the bytes that the runner counted for this thread in the interval. For a read kernel it adds the size of every buffer range that it gave to the kernel. <code>oldread</code>, <code>read</code>, <code>asmread</code>, <code>read_nop96</code> and <code>read_nop256</code> read every byte of the range. <code>read_1pl</code> loads only 16 of every 64 bytes, and the runner still counts the full size.</li><li><code>elapsed_s</code> = field 8: the time of this thread in seconds, printed with 6 decimals. It runs from the clock read directly before the first timed kernel call of the thread to the clock read after its last kernel call. The warm-up call of the interval comes before this time.</li><li>flags = field 13: <code>late</code> or <code>-</code>.</li><li><code>t_start_s</code>, <code>t_end_s</code> = fields 10 and 11: the start and the end of the time <code>elapsed_s</code> of this thread, in seconds since the process start.</li><li><code>Tl</code> keeps the first and the last line number of the T rows of each interval. Fields 5, 9 and 12 (<code>tid</code>, <code>t_sched_s</code>, <code>passes</code>) are not kept.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">346              elif p[0] == 'I':
347                  cur['I'][(int(p[1]), int(p[2]), p[3])] = dict(threads=int(p[5]), total_bytes=int(p[6]),
348                                                               max_elapsed_s=float(p[7]), agg=float(p[8]), line=ln)</pre></td><td valign="top"><b>I rows: one row per interval.</b> Stored under the same key: <code>threads</code> = field 6, <code>total_bytes</code> = field 7, <code>max_elapsed_s</code> = field 8, <code>agg</code> = field 9 and the line number. <code>agg</code> is <code>aggregate_GBps</code> as the runner printed it: total bytes / longest per-thread time, with 2 decimals [Ref2]. This module does not use <code>agg</code> as the rate of the interval. <code>build_facts.py</code> checks that it differs from the total of the T rows by less than 0.05 GB/s [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">349              elif p[0] == 'P':
350                  cur['P'].append(tuple([int(p[1]), int(p[2]), int(p[3]), p[4]] + [int(x) for x in p[5:11]]))
351              elif p[0] == 'C':
352                  cur['C'] += 1
353      return secs
354
355</pre></td><td valign="top"><ul><li>A P row holds the page state of one buffer. It is stored as a tuple: round, pos, thread, buffer letter and the 6 numbers of fields 6 to 11 (the first two are <code>kB_total</code> and <code>kB_huge</code>). The buffer letter is <code>a</code> for the first buffer of a thread and <code>b</code> for its second buffer. The 9 bwx12 csv files of the rerun hold only <code>a</code> rows.</li><li>C rows hold counter values. They are only counted.</li><li>A row of any other kind is ignored.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>bwx_intervals</code>: one rate per interval from the T rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">356  def bwx_intervals(sec):
357      """One dict per interval (round, pos, kernel) of a section, in file order."""
358      seq = sec['hdr'].get('seq', '').split(',')
359      out = []
360      for (rnd, pos, kernel), tl in sec['T'].items():
361          rate = lambda t: t[1] / t[2] / 1e9
362          m0 = [rate(t) for t in tl if t[0] &lt; 64]
363          m1 = [rate(t) for t in tl if t[0] &gt;= 64]
364          cpus = [t[0] for t in tl]</pre></td><td valign="top">Takes one section and returns one entry per interval, in file order. <code>seq</code> is the kernel sequence of the header, as a list of names. For each interval <code>tl</code> is the list of its T rows, one per thread.<ul><li><code>rate</code>: bytes / elapsed_s / 1e9 of one thread, in GB/s. Each thread is divided by its own time.</li><li><code>m0</code>: the rates of the threads on CPUs 0 to 63 (mesh 0).</li><li><code>m1</code>: the rates of the threads on CPUs 64 and higher (mesh 1).</li><li>No T row is left out. A row with the flag <code>late</code> is used like every other row. The 9 bwx12 csv files of the rerun hold no row with this flag.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">365          i = sec['I'].get((rnd, pos, kernel))
366          if pos &gt; 0:
367              before = seq[pos - 1]
368          elif rnd &gt; 0:
369              before = seq[-1]
370          else:
371              before = None
372          assert seq[pos] == kernel, (sec['file'], rnd, pos, kernel, seq)</pre></td><td valign="top"><ul><li><code>i</code> is the I row of the same interval, or <code>None</code> when the file has none.</li><li><code>before</code> is the kernel that was timed directly before this interval in the same process. For a position above 0 it is the kernel one position earlier in <code>seq</code>. For position 0 of a later round it is the last kernel of <code>seq</code>. For the first interval of the process it is <code>None</code>.</li><li>The value comes from <code>seq</code>, not from a time in the file. Before each timed interval the runner also makes one warm-up pass with the kernel of that interval. This pass is not timed [Ref2].</li><li>The <code>assert</code> stops the script when the kernel name of the rows is not the name at this position of <code>seq</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">373          out.append(dict(round=rnd, pos=pos, kernel=kernel, kernel_before=before, threads=len(tl),
374                          total=sum(m0) + sum(m1), mesh0=sum(m0), mesh1=sum(m1), n0=len(m0), n1=len(m1),
375                          m0_min=min(m0) if m0 else None, m0_max=max(m0) if m0 else None,
376                          m1_min=min(m1) if m1 else None, m1_max=max(m1) if m1 else None,
377                          is_64_56=(len(m0) == 64 and len(m1) == 56 and max(cpus) &lt;= 119 and len(set(cpus)) == 120),</pre></td><td valign="top"><b>The bwx rate.</b><ul><li><code>total</code> = sum of <code>m0</code> + sum of <code>m1</code>: the sum of the per-thread rates of all threads of the interval, in GB/s. <code>build_facts.py</code> takes this value as the rate of a bwx12 interval [Ref3].</li><li><code>mesh0</code>, <code>mesh1</code>: the same sum for each mesh. <code>threads</code>: the number of T rows of the interval. <code>n0</code>, <code>n1</code>: the thread counts per mesh.</li><li><code>m0_min</code> to <code>m1_max</code>: the lowest and the highest per-thread rate of each mesh.</li><li><code>is_64_56</code>: true when 64 threads ran on CPUs 0 to 63 and 56 threads on CPUs 64 to 119, on 120 different CPUs.</li><li>Nothing is rounded here.</li><li>Example: T72L1, <code>a6456.csv</code>, round 0, position 0, <code>oldread</code>. The 120 T rows give 305.13 GB/s on mesh 0 and 157.17 GB/s on mesh 1. Their sum <code>total</code> is 462.30 GB/s. The I row says 462.29 GB/s [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">378                          flagged=sum(t[3] != '-' for t in tl), flags=sorted(set(t[3] for t in tl)),
379                          I_agg=i['agg'] if i else None, line=i['line'] if i else None,
380                          max_elapsed_s=i['max_elapsed_s'] if i else None,
381                          t_start=min(t[4] for t in tl), t_end=max(t[5] for t in tl),
382                          T_first=sec['Tl'][(rnd, pos, kernel)][0], T_last=sec['Tl'][(rnd, pos, kernel)][1]))
383      return out
384
385</pre></td><td valign="top">The other values of the entry:<ul><li><code>flagged</code>: the number of T rows whose flag is not <code>-</code>. <code>flags</code>: the different flag values of the interval.</li><li><code>I_agg</code>, <code>line</code>, <code>max_elapsed_s</code>: taken from the I row. <code>line</code> is the line number of the I row. All three are <code>None</code> when the interval has no I row.</li><li><code>t_start</code>: the earliest <code>t_start_s</code> of the T rows of the interval. <code>t_end</code>: the latest <code>t_end_s</code>. Both are in seconds since the process start.</li><li><code>T_first</code>, <code>T_last</code>: the first and the last line number of the T rows.</li></ul></td></tr>
<tr><td colspan="2"><b>The data sets of the rerun</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">386  # ----------------------------------------------------------------------------- the data sets
387
388  RERUN_A = [('T72A1', 1), ('T72A2', 2), ('T72A3', 3)]
389  RERUN_L = [('T72L1', 1), ('T72L2', 2), ('T72L3', 3)]
390  RERUN_C = [('T72C1', 1, 'cfwd'), ('T72C2', 2, 'crev'), ('T72C3', 3, 'cfwd'), ('T72C4', None, 'crev')]
391  RERUN_I = [('T72I1', 1), ('T72I2', 2)]
392</pre></td><td valign="top">The result folders of the rerun, as (tag, number). The tag is the name that <code>go.sh</code> or <code>go2.sh</code> gave to the run script. It is part of the folder name.<ul><li><code>RERUN_A</code>: part A, sessions 1 to 3.</li><li><code>RERUN_L</code>: part L, sessions 1 to 3.</li><li><code>RERUN_C</code>: part C, with the name of the spec file as third value. <code>T72C4</code> has no session (<code>None</code>): it ran after session 3.</li><li><code>RERUN_I</code>: control I. Its number counts the control processes. It is not a session.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">393  SHA_NAMES = {  # short names of the binaries, by sha256 prefix, as the result files record them
394      'e8fc0205': 'bw_old', 'fd7c14df': 'bw_new', 'cd58e564': 'bwx12', 'f1215f9e': 'bwx11', '5b702073': 'bwx'}
395
396</pre></td><td valign="top">Short names of five binaries, each found by the first 8 hexadecimal digits of its SHA-256 checksum.</td></tr>
<tr><td colspan="2"><b>Function <code>find</code>: result folder of a tag</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">397  def find(prefix):
398      """The one result folder whose name starts with prefix."""
399      hits = sorted(glob.glob(os.path.join(R, prefix + '-2026*')))
400      if len(hits) != 1:
401          sys.exit(f'expected one folder for {prefix}, found {hits}')
402      return hits[0]
403
404</pre></td><td valign="top">Returns the one folder under <code>R</code> whose name starts with the prefix followed by <code>-2026</code>. Example: <code>k120-T72A1</code> gives <code>R/k120-T72A1-20261117T221209Z</code>. The script stops with an error when it finds no folder or more than one.</td></tr>
<tr><td colspan="2"><b>Function <code>read_boot_table</code>: boot history of the DIMM report</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">405  def read_boot_table():
406      """Boot history of the DIMM report (section 3): list of (boot number, Linux start, modules),
407      and the time until which the memory speed setting was 8000 MT/s."""
408      path = DIMM_REPORT
409      boots, until = [], None
410      for ln, line in enumerate(_open(path), 1):
411          m = re.match(r'\| (-?\d+) \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \| \**(\d+)\** \|', line)
412          if m:
413              boots.append(dict(no=int(m[1]), start=dt.datetime.strptime(m[2], '%Y-%m-%d %H:%M'), modules=int(m[3]),
414                                line=ln))
415          m = re.match(r'\| Memory speed until (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC \| (\d+) MT/s', line)
416          if m:
417              until = dict(utc=dt.datetime.strptime(m[1], '%Y-%m-%d %H:%M'), speed=int(m[2]), line=ln)
418      return dict(path=path, boots=sorted(boots, key=lambda b: b['start']), until=until)
419
420</pre></td><td valign="top">Reads two things from the tables of <code>DIMM-flaky-report.md</code>. <code>build_facts.py</code> uses the table for the result folders of earlier runs [Ref3].<ul><li>A table row with a boot number, a start time and a module count gives one boot. The count may be written in bold.</li><li>The row <code>Memory speed until ... UTC | N MT/s</code> gives the time until which the memory speed setting was N MT/s.</li><li>The boots are returned in the order of their start time.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>base_record</code>: one interval record of <code>facts.json</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">421  def base_record(**kw):
422      """One flat interval record of facts.json. Every record has every key."""
423      rec = dict(dataset=None, part=None, role=None, speed_MTps=None, modules=None, boot=None,
424                 folder=None, file=None, line=None, tag=None, session=None, process=None, proc_key=None, round=None,
425                 pos=None, interval=None, kernel=None, kernel_before=None, binary=None, binary_sha256=None, GBps=None,
426                 rate_kind=None, mesh0_GBps=None, mesh1_GBps=None, passes=None, per_thread_min_GBps=None,
427                 per_thread_max_GBps=None, per_thread_avg_GBps=None, threads=None, is_64_56=None, flagged=None,
428                 stop=None, start=None, min_ms=None, count=None, thp=None, load1_at_launch=None, launch_utc=None,
429                 gap_s=None, start_state=None)
430      unknown = set(kw) - set(rec)
431      assert not unknown, unknown
432      rec.update(kw)
433      return rec
434
435</pre></td><td valign="top">Returns a record with 40 keys. <code>build_facts.py</code> creates one record per interval [Ref3].<ul><li>Each key is <code>None</code> unless the caller passes a value.</li><li>A key that is not in the list stops the script.</li><li>The rate goes into <code>GBps</code>, and <code>rate_kind</code> says how the rate was formed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">436  KIND_A = 'aggregate_GBps column of the csv (sum of bytes / longest per-thread time)'
437  KIND_X = 'sum over the T rows (threads) of bytes / elapsed_s / 1e9'
438
439</pre></td><td valign="top">The two texts for <code>rate_kind</code>. <code>KIND_A</code> marks a part A record: the rate is the csv column <code>aggregate_GBps</code>. <code>KIND_X</code> marks a record of a bwx runner: the rate is the sum over the T rows of bytes / elapsed_s / 1e9.</td></tr>
<tr><td colspan="2"><b>Selection and statistics. Function <code>sel</code>: records that match conditions</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">440  # ----------------------------------------------------------------------------- selection and statistics
441
442  def sel(recs, **cond):
443      """Records that match every condition. A condition value may be a value, a set, or a function."""
444      out = []
445      for r in recs:
446          for k, v in cond.items():
447              x = r[k]
448              if callable(v):
449                  ok = v(x)
450              elif isinstance(v, (set, frozenset, list, tuple)):
451                  ok = x in v
452              else:
453                  ok = x == v
454              if not ok:
455                  break
456          else:
457              out.append(r)
458      return out
459
460</pre></td><td valign="top">Returns the records that pass every condition. A condition is written <code>key=value</code>.<ul><li>A plain value must be equal to the value of the record.</li><li>A set, list or tuple must contain the value of the record.</li><li>A function must return true for the value of the record.</li><li>Example of a call in <code>facts_text.py</code>: <code>sel(recs, dataset='rerun-L', kernel='oldread')</code> returns the part L intervals of the old read kernel [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>rng</code>: lowest, highest, median and counts</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">461  def rng(rs, key='GBps'):
462      """min, max, median, number of intervals and number of processes of a list of records."""
463      v = [r[key] for r in rs]
464      if not v:
465          return None
466      return dict(lo=min(v), hi=max(v), med=statistics.median(v), n=len(v), procs=len({r['proc_key'] for r in rs}),
467                  sessions=len({r['session'] for r in rs if r['session'] is not None}),
468                  boots=len({r['boot'] for r in rs}))
469
470</pre></td><td valign="top">Summarises a list of records, by default over the key <code>GBps</code>. An empty list gives <code>None</code>.<ul><li><code>lo</code>, <code>hi</code>: the lowest and the highest value.</li><li><code>med</code>: the median. For an even number of values it is the mean of the two middle values.</li><li><code>n</code>: the number of records, that is the number of intervals.</li><li><code>procs</code>: the number of different processes (key <code>proc_key</code>).</li><li><code>sessions</code>: the number of different values of the key <code>session</code>. A record without a value is not counted. In a control I record the key holds the number of the control process, and <code>rng</code> counts it like a session. <code>boots</code>: the number of different boots.</li><li>No value is left out and nothing is rounded. The function forms no mean over all values. The facts sheet prints a result as <code>lo</code> to <code>hi</code> with these counts [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>overlap</code>: do two ranges share a value</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">471  def overlap(a, b):
472      return a['lo'] &lt;= b['hi'] and b['lo'] &lt;= a['hi']
473
474</pre></td><td valign="top">True when the two ranges share at least one value. Two ranges that only touch at one end count as overlapping. The function <code>compare</code> of <code>facts_text.py</code> sets the wording "no difference seen" when the 7200 MT/s range and the 8000 MT/s range overlap. It sets "differs between the 8000 MT/s boot and the 7200 MT/s boot" when they do not [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>gap</code>: distance between two ranges</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">475  def gap(a, b):
476      """Distance between the nearest ends of two ranges, GB/s. Positive: a is above b. Zero: they overlap."""
477      if a['lo'] &gt; b['hi']:
478          return a['lo'] - b['hi']
479      if a['hi'] &lt; b['lo']:
480          return a['hi'] - b['lo']
481      return 0.0
482
483</pre></td><td valign="top">Gives the distance between the nearest ends of two ranges, in GB/s. The value is positive when range <code>a</code> lies fully above range <code>b</code>. It is negative when <code>a</code> lies fully below <code>b</code>. It is 0.0 when the ranges overlap.</td></tr>
<tr><td colspan="2"><b>Function <code>width_pct</code>: width of a range in percent</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">484  def width_pct(a):
485      return (a['hi'] - a['lo']) / a['lo'] * 100</pre></td><td valign="top">Gives the width of a range in percent of its lower end: (<code>hi</code> - <code>lo</code>) / <code>lo</code> x 100.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: lines 572 to 605: the print statements of the part A csv. `agg = total / max_el / 1e9` is printed with `%.2f`, then the `best` row. The old source `bandwidth.orig.c` in the same folder has the same statements at lines 415 to 448. Lines 418 to 444: the function `pass` returns the bytes of one buffer pass, and 2 x that number for `copy` and `asmcopy`. The old source has the same function at lines 260 to 286. Lines 468 to 479: the timed loop of a thread (warm-up pass, barrier, clock reads `t0` and `t1`). The old source has the same loop at lines 311 to 322. The SHA-256 checksum of this local text of `bandwidth.c` starts with f1985072. The script `run_kernels.sh` of the test of 2026-11-13 recorded this value in a run of 18:32:18 UTC that built the binaries and timed nothing (file `probe.txt` in the folder `kernels-20261113T183218Z` of R, line 15). The timed run of 18:12:22 UTC recorded a checksum that starts with c1406e02 for `bandwidth.c` (file `probe.txt` in the folder `kernels-20261113T181222Z` of R, line 15). Both files record the same checksum for the binary `bw_new` on line 20. It starts with fd7c14df. `ra.sh` checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 3018 to 3028: the header lines of a bwx csv. Lines 3077 to 3084: the print statements of the I row and the T row (bytes, `t_end - t_start`, flag). The T row prints `t_end - t_start` in seconds with 6 decimals. Lines 1688 to 1723: a thread reads the clock before its first chunk (`t0`) and after each chunk (`t1`), and stores them as `t_start` and `t_end`. Lines 133 and 1725: the flag `late` (start more than 100000 ns after the common start time). Lines 3058 to 3062 and 1676 to 1683: with `--stop common` the runner sets one start time and one deadline for all threads, and each thread waits for the start time. Lines 1690 to 1716: the two stop rules. Lines 1661 to 1662: the start place of a thread with `--start offset`. Line 1669: the warm-up call before each timed interval. Lines 1663, 1696 and 1712: the bytes that a thread counts for each kernel call. Lines 984 to 986: `read_1pl` reads bytes 0 to 15 of every 64 B line and no other byte. Lines 461 to 473: `oldread` adds every 8-byte word of its range. Lines 1515 to 1559: the runner reads the page state of a buffer from the file `/proc/self/smaps` (lines `Size` and `AnonHugePages`) and four counters from `/proc/vmstat`. Lines 3105 to 3118: the P rows and the `# page_read` line after each reading. Lines 3040 to 3049 and 3106 to 3108: the reading with `pos` = -1 comes before the first interval, and every other reading comes after the interval `pos`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 50 to 290: function `collect`, the order of the calls into this module. Lines 119 to 160: `add_k120` takes `iv['agg']` and `add_bwx` takes `iv['total']` as `GBps`. Lines 736 to 740 and 806 to 832: cross-checks with the I rows, `stat_k120.py` and `stat_bwx.py`. Line 1027: rounding to 3 decimals for `facts.json`. Lines 1033 to 1041: function `main`, the order collect, run_checks, render, write_json. Lines 142 to 149: `add_bwx` leaves out intervals by kernel name or position when the caller asks for it. Lines 207 to 221, 253 and 280: the calls for files outside the rerun that ask for it. Lines 166 and 177: the data set names of the rerun. Lines 201, 253 and 280: the data set names of the earlier runs.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`: lines 21 to 22: the two wordings of a comparison. Lines 41 to 51: rounding to 0.01 GB/s, half up, and the text form `lo` to `hi`. Lines 98 to 105: the counts of intervals, processes, sessions and boots. Lines 333 to 336: function `compare` with `rng`, `overlap`, `gap`, `width_pct`. Line 414: the `sel` call of the example. Lines 1474 to 1475: the script stops when the file list of the facts sheet does not name every file of `OPENED`. Lines 279 to 321: the function `med` and the pairs that `analyse` forms, with the drop in percent of each pair.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: lines 21 to 22: folder name with the UTC time. Lines 30 to 36 and 49: content of `probe.txt`. Lines 41 to 42: the `-- binary` header line and the arguments of `bw_old` and `bw_new` (`--reps 3 --min-ms 500`, no `--per-thread`). Lines 26 to 28: the wait loop that reads the number of runnable tasks, then a wait of 5 s.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: line 9: folder name with the UTC time. Line 10: content of `env.txt`. Lines 16 and 20: the `launch` line and the `rc` line of `launches.txt`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: line 17: the function `state` that prints a state line. Lines 18 and 48: the `FAILED` line and the `ALLDONE` line. `go2.sh` in the same folder has the same function at line 13.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: line 128: the I row of round 0, position 0, `oldread` (462.29 GB/s). Lines 129 to 248: its 120 T rows. Their per-thread rates add up to 462.30 GB/s (computed with `read_bwx` and `bwx_intervals` of this module on 2026-11-21).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: line 1: a `-- binary` header line. Line 4: the interval row of the example. Line 7: a `best` row. The file has 24 header lines and 72 interval rows.
- [Ref10] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the record of the Claude Code session of 2026-11-17. This record lies outside the project folder. Line 313 holds the command that started `go.sh`. Line 365 holds the command that started `go2.sh`. Each command holds `> $L 2>&1`. This part sends the standard output and the error output of the script to the log file `$L`.
