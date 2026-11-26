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

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/facts_data.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (485 lines, 23123 bytes, sha256 `630b3c775d00071d282228310710c54639bc0bef778e580629fc71ad7c319206`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- 2 lines hold a backslash directly before a `|`: line 411, line 415. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Module comment: the inputs and the two kinds of rate (lines 1 to 14)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3` when the file is started as a program. The tool `env` finds `python3` in the search path of the user. The file has no main program. Another script imports it (line 4). |
| 2 | `"""facts_data.py - parsers and the data model for the facts sheet of the 7200 MT/s rerun (2026-11-17).` | Comment: starts the module comment. It is a text between two `"""` marks, and Python does not run it. This line names the file and its content: the parsers and the data model for the facts sheet of the rerun at 7200 MT/s of 2026-11-17. A parser is a function that reads a file and takes values out of it. |
| 4 | `Used by build_facts.py. It reads raw result files and writes nothing.` | Comment: the script `build_facts.py` uses this module. The module reads raw result files and writes no file. |
| 6 | `R = results folder, S = scratch folder of this task (both derived from the location of this file).` | Comment: `R` is the results folder and `S` is the scratch folder of this task. Both paths are computed from the place of this file (lines 25 to 27). |
| 7 | `GB = 1e9 bytes everywhere.` | Comment: GB means 1e9 bytes in every rate of this module. |
| 9 | `Two kinds of rate exist in the raw files, and this module never mixes them:` | Comment: the raw files give two kinds of rate, and this module never mixes them. Lines 10 to 13 name the two kinds. |
| 10 | `- part A (binaries bw_old, bw_new of bandwidth.c): the column aggregate_GBps of the csv` | Comment: first kind, part A (the binaries `bw_old` and `bw_new` of `bandwidth.c`). The rate is the column `aggregate_GBps` of the csv, as the binary printed it. |
| 11 | `  (the binary computes it as sum(bytes) / max(per-thread elapsed_s)).` | Comment: the binary computes `aggregate_GBps` as the sum of the bytes of all threads, divided by the longest elapsed time of one thread. |
| 12 | `- bwx runners (bwx12, bwx11, bwx): sum over the T rows (threads) of bytes / elapsed_s / 1e9,` | Comment: second kind, the bwx runners (`bwx12`, `bwx11`, `bwx`). This module computes the rate from the T rows of the csv, one row per thread. Each thread gives `bytes / elapsed_s / 1e9`. The values of all threads are added. |
| 13 | `  the method of stat_bwx.py.` | Comment: this sum is the method of `stat_bwx.py`, an earlier statistics script of the same folder. |
| 14 | `"""` | Ends the module comment. |

### Imports, folder paths and the list `OPENED` (lines 15 to 38)

| Line | Source | Explanation |
|---:|---|---|
| 15 | `import datetime as dt` | Loads the Python module `datetime` under the short name `dt`. The readers use it to turn the time texts of the files into time values. |
| 16 | `import glob` | Loads the Python module `glob`. The function `find` (line 397) uses it to list the folders whose names fit a pattern. |
| 17 | `import hashlib` | Loads the Python module `hashlib`. The function `sha256` (line 55) uses it to compute a checksum. |
| 18 | `import os` | Loads the Python module `os`. This file uses it for path functions such as `os.path.join`. |
| 19 | `import re` | Loads the Python module `re`. It gives regular expressions. A regular expression is a text pattern. A line matches when it has the form of the pattern. The parts of the pattern in round brackets are called groups. Their text is taken out as values, counted from group 1. |
| 20 | `import statistics` | Loads the Python module `statistics`. The function `rng` (line 461) uses its function `median`. |
| 21 | `import sys` | Loads the Python module `sys`. This file uses `sys.exit`, `sys.path` and the setting of line 23. |
| 23 | `sys.dont_write_bytecode = True` | Python writes no compiled copy (`.pyc` file) of the modules that are imported after this line. So the two imports of lines 33 to 34 write no file into a folder `__pycache__`. |
| 25 | `S = os.path.dirname(os.path.abspath(__file__))` | `S`: the absolute path of the folder that holds this file. The comment of line 6 calls it the scratch folder of this task. `__file__` is the path of this file. |
| 26 | `CRB = os.path.normpath(os.path.join(S, '..', '..', '..'))` | `CRB`: the folder three levels above `S`. The script was written for a place `crb/tmp/agent-scratch/NAME`. There `CRB` is the project folder `crb`. Here the name means this folder, not the machine. `os.path.normpath` removes the `..` steps from the path. |
| 27 | `R = os.path.join(CRB, 'results')` | `R`: the folder `results` in `CRB`. It holds the result folders that were copied back from the machine. |
| 28 | `W15 = os.path.join(CRB, 'tmp', 'agent-scratch', 'w120-2026-11-15')` | `W15`: the folder `tmp/agent-scratch/w120-2026-11-15` in `CRB`, the scratch folder of 2026-11-15. It holds the scripts `rx.sh` and `r0.sh`. `build_facts.py` reads both. |
| 29 | `K13 = os.path.join(CRB, 'tmp', 'agent-scratch', 'kernels-2026-11-13')` | `K13`: the folder `tmp/agent-scratch/kernels-2026-11-13` in `CRB`, the scratch folder of 2026-11-13. It holds the benchmark sources and the script `run_kernels.sh`. `build_facts.py` reads that script. |
| 30 | `DIMM_REPORT = os.path.normpath(os.path.join(CRB, '..', '..', '..', 'machines', 'arm-crb', 'DIMM-flaky-report.md'))` | `DIMM_REPORT`: the path of the report on the memory modules, `machines/arm-crb/DIMM-flaky-report.md`. The folder `machines` lies in the folder three levels above `CRB`. The function `read_boot_table` (line 405) reads this file. |
| 32 | `sys.path.insert(0, S)` | Puts the folder `S` at the first place of the list of folders in which Python searches a module. So the two imports below find the scripts of this folder. |
| 33 | `import stat_bwx    # noqa: E402  (existing tool, used as a cross-check)` | Loads the script `stat_bwx.py` of the folder `S` as a module. The comment says that it is an existing tool that serves as a cross-check. `build_facts.py` calls its function `interval_rows` through this module to compare the rates of the bwx csv files [Ref3]. The mark `# noqa: E402` tells a style checker not to report that this import stands below other code. |
| 34 | `import stat_k120   # noqa: E402  (existing tool, used as a cross-check)` | Loads the script `stat_k120.py` of the folder `S` in the same way. This module uses its pattern `HDR` for the header line of a part A process (line 271). `build_facts.py` calls its function `load` through this module to compare the values of the part A csv files [Ref3]. |
| 36 | `OPENED = []  # every file that a reader of this module opened, in order (for the file list of the facts sheet)` | `OPENED`: the list of the files that the readers of this module opened, in the order of the first opening, each path once. The comment gives the purpose: the file list of the facts sheet. `facts_text.py` stops the script when that file list does not name every file of `OPENED` [Ref4]. `build_facts.py` also adds a few paths to this list directly. |

### Functions `_open`, `rel` and `sha256`: record a file, shorten a path, checksum (lines 39 to 61)

| Line | Source | Explanation |
|---:|---|---|
| 39 | `def _open(path, mode='r'):` | Starts the function `_open`. It records the path of a file in `OPENED` and then opens the file. Every reader below opens its file through `_open`. `mode` is the open mode. The default `'r'` opens the file as text for reading. |
| 40 | `    path = os.path.abspath(path)` | Turns the path into an absolute path. So one file always has the same text in the list. |
| 41 | `    if path not in OPENED:` | Tests whether the list already holds this path. |
| 42 | `        OPENED.append(path)` | Adds the path at the end of the list. This happens only the first time that the file is opened. |
| 43 | `    return open(path, mode)` | Opens the file and returns the open file to the caller. |
| 46 | `def rel(path):` | Starts the function `rel`. It shortens a path to the form that the facts sheet prints. `build_facts.py` also writes this form into the key `folder` of each record. |
| 47 | `    """Path as written in the facts sheet: R/... or S/..."""` | Comment: the path as the facts sheet writes it, `R/...` or `S/...`. |
| 48 | `    path = os.path.abspath(path)` | Turns the path into an absolute path. |
| 49 | `    for name, root in (('R', R), ('S', S)):` | Tries the two known folders in turn: first the results folder with the name `R`, then the scratch folder with the name `S`. |
| 50 | `        if path.startswith(root + os.sep):` | Tests whether the path lies inside this folder. `os.sep` is the character `/` that separates the parts of a path on Linux. |
| 51 | `            return name + '/' + os.path.relpath(path, root)` | Returns the short form: the name, a `/` and the rest of the path below that folder. A file `x/y.csv` in the results folder becomes `R/x/y.csv`. |
| 52 | `    return path` | A path outside both folders is returned as an absolute path. |
| 55 | `def sha256(path):` | Starts the function `sha256`. It returns the sha256 checksum of the content of a file. `build_facts.py` calls it for local text files: the run scripts and the spec files. |
| 56 | `    h = hashlib.sha256()` | `h`: a new sha256 computation, empty at first. |
| 57 | `    with _open(path, 'rb') as f:` | Opens the file through `_open` (line 39) in the mode `'rb'`, which gives the bytes of the file unchanged. So the file is also recorded in `OPENED`. `with` closes the file at the end of the block. |
| 58 | `        h.update(f.read())` | Reads the whole file and feeds its bytes into the computation. |
| 59 | `    return h.hexdigest()` | Returns the checksum as text: 64 hexadecimal digits. |

### Functions `folder_date` and `clock`: full times from a folder name and a time of day (lines 62 to 76)

| Line | Source | Explanation |
|---:|---|---|
| 62 | `def folder_date(folder):` | Starts the function `folder_date`. It reads the date and the time from the name of a result folder. `ra.sh` and `rx.sh` put the UTC time at which they create the folder into its name [Ref5] [Ref6]. |
| 63 | `    """Date and time in a folder name such as k120-T72A1-20261117T221209Z."""` | Comment: the function returns the date and time in a folder name such as `k120-T72A1-20261117T221209Z`. This name gives 2026-11-17 22:12:09 (UTC). |
| 64 | `    m = re.search(r'(\d{8})T(\d{6})Z', os.path.basename(folder))` | Searches the last part of the path (`os.path.basename`) for 8 digits, the letter `T`, 6 digits and the letter `Z`. Group 1 holds the 8 digits of the date. Group 2 holds the 6 digits of the time of day. |
| 65 | `    return dt.datetime.strptime(m[1] + m[2], '%Y%m%d%H%M%S')` | Joins the two groups to 14 digits and reads them as year, month, day, hour, minute and second (`strptime` with the form `'%Y%m%d%H%M%S'`). Returns a `datetime` value, the Python value for a date with a time of day. The value carries no time zone. When the folder name does not have this form, `m` is `None` and the script ends with a Python error. |
| 68 | `def clock(folder, hms):` | Starts the function `clock`. Some run files give a time as a time of day only, in the form `HH:MM:SS`. `clock` turns such a time into a full date and time. The date comes from the folder name. |
| 69 | `    """HH:MM:SS of a run file -> datetime, with the date of the folder name (next day if earlier)."""` | Comment: `HH:MM:SS` of a run file becomes a `datetime` value with the date of the folder name, or with the next day if the time is earlier. |
| 70 | `    base = folder_date(folder)` | `base`: the date and time of the folder name (line 62). |
| 71 | `    t = dt.datetime.combine(base.date(), dt.datetime.strptime(hms, '%H:%M:%S').time())` | `t`: the date of `base` joined with the time of day `hms`. |
| 72 | `    if t < base - dt.timedelta(seconds=1):` | Tests whether `t` lies more than 1 s before the time of the folder name. That is the case of a run that passed midnight. |
| 73 | `        t += dt.timedelta(days=1)` | In that case one day is added to `t`. |
| 74 | `    return t` | Returns the full date and time. |

### Pattern `STATE` and function `read_log`: the log of `go.sh` or `go2.sh` (lines 77 to 116)

| Line | Source | Explanation |
|---:|---|---|
| 77 | `# ----------------------------------------------------------------------------- logs and state files` | Comment: a divider line. The block below reads logs and state files. |
| 79 | `STATE = re.compile(r'^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) '` | `STATE`: a compiled pattern for one state line. `go.sh` and `go2.sh` print state lines at the start, around the run steps and at the end [Ref7]. A state line starts with `== `. Group 1: the label, which is the text before the word `utc`. Group 2: the UTC time. Group 3: the boot id. Group 4: `MemTotal` in kB. Groups 5 to 7: the three load averages. Groups 8 and 9: the tasks that are runnable now and the number of all tasks, from the field of the form `runnable/all`. Group 10: the fifth field of `/proc/loadavg`, the id of the newest process. |
| 80 | `                   r'users (\d+) marker (\S+) processes per user:\s*(.*)$')` | Continues the pattern of line 79. Group 11: the number after `users`, which is the number of logins. Group 12: the word after `marker`, `present` or `absent`. It says whether the marker file `/tmp/positron-perf.RUNNING` existed. Group 13: the rest of the line after `processes per user:`, the number of processes of each user. |
| 83 | `def read_log(path):` | Starts the function `read_log`. It reads the log of `go.sh` or of `go2.sh`. `build_facts.py` calls it once for each of the two logs [Ref3]. |
| 84 | `    """State lines and the other '== ' lines of a go.sh or go2.sh log."""` | Comment: the function returns the state lines and the other lines that start with `== ` of a log of `go.sh` or `go2.sh`. |
| 85 | `    out = dict(path=path, states=[], other={}, lines=[], alldone=False, failed=[])` | `out`: the result, empty at first. `states`: the list of the state lines. `other`: the four machine lines of lines 102 to 109. `lines`: every line of the log. `alldone`: whether the line `ALLDONE` was found. `failed`: the lines that start with `FAILED`. |
| 86 | `    with _open(path) as f:` | Opens the log through `_open` (line 39) as text. |
| 87 | `        for ln, line in enumerate(f, 1):` | Loop over the lines of the log. `ln` is the line number, counted from 1. |
| 88 | `            line = line.rstrip('\n')` | Removes the line end character from the line. |
| 89 | `            out['lines'].append(line)` | Keeps every line of the log in `lines`, also a line that no test below uses. |
| 90 | `            m = STATE.match(line)` | Compares the line with the pattern `STATE` (line 79). `m` is `None` when the line does not fit. |
| 91 | `            if m:` | The line is a state line. |
| 92 | `                users = {}` | `users`: the number of processes per user, empty at first. |
| 93 | `                for part in m[13].split(';'):` | Splits group 13 at each `;`. Each part holds a count and a user name. |
| 94 | `                    part = part.strip()` | Removes the spaces at both ends of the part. |
| 95 | `                    if part:` | Skips an empty part, such as the text after the last `;`. |
| 96 | `                        n, name = part.split()` | Splits the part at the space into the count `n` and the user name `name`. |
| 97 | `                        users[name] = int(n)` | Stores the count as a number under the user name. |
| 98 | `                out['states'].append(dict(` | Adds one entry for this state line to `states`. Lines 99 to 101 give its values. |
| 99 | `                    label=m[1], utc=dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%SZ'), boot=m[3], memtotal_kB=int(m[4]),` | Continues the entry of line 98. `label`: group 1, for example `start`, `after T72A1` or `idle before T72I1`. `utc`: group 2 as a `datetime` value. The text has the form `YYYY-MM-DDTHH:MM:SSZ`. `boot`: the boot id. `memtotal_kB`: `MemTotal` in kB, as a number. |
| 100 | `                    load1=float(m[5]), load5=float(m[6]), load15=float(m[7]), runnable=int(m[8]), tasks=int(m[9]),` | Continues the entry of line 98. `load1`, `load5`, `load15`: the load averages over 1, 5 and 15 minutes. `runnable`: the tasks that are runnable now. `tasks`: the number of all tasks. |
| 101 | `                    logins=int(m[11]), marker=m[12], procs=users, line=ln, file=path))` | Ends the entry of line 98. `logins`: the number of logins. `marker`: `present` or `absent`. `procs`: the dictionary `users` of lines 92 to 97, from user name to number of processes. `line`: the line number in the log. `file`: the path of the log. Group 10, the id of the newest process, is matched and not stored. |
| 102 | `            elif line.startswith('== cmdline '):` | A line that is not a state line: tests whether it starts with `== cmdline `. `go.sh` prints the boot arguments of the Linux kernel in this line (the content of `/proc/cmdline`). |
| 103 | `                out['other']['cmdline'] = (line[len('== cmdline '):], ln)` | Stores the text after `== cmdline ` and the line number in `other` under the key `cmdline`. |
| 104 | `            elif line.startswith('== governors'):` | Tests whether the line starts with `== governors`. `go.sh` prints the governors of the CPUs 0 to 119 in this line. A governor is the Linux policy that sets the CPU frequency. |
| 105 | `                out['other']['governors'] = (line[3:], ln)` | Stores the line without its first 3 characters (`== `) and the line number under the key `governors`. |
| 106 | `            elif line.startswith('== thp '):` | Tests whether the line starts with `== thp `. `go.sh` prints the settings of Linux for transparent huge pages in this line. |
| 107 | `                out['other']['thp'] = (line[3:], ln)` | Stores the line without its first 3 characters and the line number under the key `thp`. |
| 108 | `            elif line.startswith('== affinity'):` | Tests whether the line starts with `== affinity`. `go.sh` prints the CPU list of its own shell in this line (output of `taskset -cp`). |
| 109 | `                out['other']['affinity'] = (line[3:], ln)` | Stores the line without its first 3 characters and the line number under the key `affinity`. Only `go.sh` prints these four lines. `go2.sh` does not. |
| 110 | `            elif line == 'ALLDONE':` | Tests whether the line is `ALLDONE`. `go.sh` and `go2.sh` print it as their last line [Ref7]. |
| 111 | `                out['alldone'] = True` | Records that the log holds the line `ALLDONE`. |
| 112 | `            elif line.startswith('FAILED'):` | Tests whether the line starts with `FAILED`. The two scripts print such a line when a check or a run step fails [Ref7]. |
| 113 | `                out['failed'].append(line)` | Adds the line to the list `failed`. |
| 114 | `    return out` | Returns the result. |

### Function `read_probe`: the file `probe.txt` of a part A folder (lines 117 to 132)

| Line | Source | Explanation |
|---:|---|---|
| 117 | `def read_probe(path):` | Starts the function `read_probe`. It reads the file `probe.txt` that `ra.sh` writes into a part A folder [Ref5]. |
| 118 | `    """probe.txt of ra.sh (part A)."""` | Comment: `probe.txt` of `ra.sh` (part A). |
| 119 | `    txt = _open(path).read()` | `txt`: the whole text of the file, opened through `_open` (line 39). |
| 120 | `    m1 = re.search(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+) name=(\S+)', txt)` | `m1`: the match of the line that starts with `## host=`. Group 1: the UTC time after `utc=`. Groups 2 to 4: the three load averages after `load_before=`. Group 5: the number of logins. Group 6: the name of the step after `name=`, for example `T72A1`. `ra.sh` reads these values directly before the first process [Ref5]. |
| 121 | `    m2 = re.search(r'## boot_id=(\S+) MemTotal: (\d+) kB runnable=(\d+)', txt)` | `m2`: the match of the line that starts with `## boot_id=`. Group 1: the boot id. Group 2: `MemTotal` in kB. Group 3: the number after `runnable=`, the number of runnable tasks. `ra.sh` reads this number in its wait loop, 5 s or more before the time of line 120 [Ref5]. |
| 122 | `    m3 = re.search(r'## kernel=(\S+) thp=(.*)', txt)` | `m3`: the match of the line that starts with `## kernel=`. Group 1: the release of the Linux kernel. Group 2: the rest of the line after `thp=`, the setting of Linux for transparent huge pages. |
| 123 | `    m4 = re.search(r'## load_after=(\S+) (\S+) (\S+) utc=(\S+) MemTotal: (\d+) kB', txt)` | `m4`: the match of the line that starts with `## load_after=`. `ra.sh` appends this line after the last process [Ref5]. Groups 1 to 3: the three load averages. Group 4: the UTC time. Group 5: `MemTotal` in kB. |
| 124 | `    shas = dict((os.path.basename(n), h) for h, n in re.findall(r'^([0-9a-f]{64})  (\S+)$', txt, re.M))` | `shas`: a dictionary from file name to sha256. `re.findall` with the flag `re.M` tests every line of the text. A line fits when it holds 64 hexadecimal digits, two spaces and a name, and nothing more. `os.path.basename` drops the folder part of the name. `ra.sh` writes three such lines: for `bw_old`, for `bw_new` and for `ra.sh` itself [Ref5]. |
| 125 | `    pcpu = [float(x) for x in re.findall(r'^\s*(\d+\.\d+) \S+\s+\S+', txt, re.M)]` | `pcpu`: the `%CPU` values of the process list in the file, as numbers. A line fits when it starts, after spaces if it has any, with a number with a decimal point, then one space, a word, spaces and one more word. This is a row of the process list: `%CPU`, user, command. `%CPU` is the column `pcpu` of the tool `ps`: the CPU time that a process has used, divided by the time that has passed from the start of the process. |
| 126 | `    T = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')` | `T`: a small function that turns a text of the form `YYYY-MM-DDTHH:MM:SSZ` into a `datetime` value. |
| 127 | `    return dict(path=path, utc=T(m1[1]), load_before=(float(m1[2]), float(m1[3]), float(m1[4])), logins=int(m1[5]),` | Returns the values as a dictionary. `path`: the path of the file. `utc`: the time of `m1`, as a `datetime` value. `load_before`: the three load averages of `m1`, as numbers. `logins`: the number of logins. |
| 128 | `                name=m1[6], boot=m2[1], memtotal_kB=int(m2[2]), runnable=int(m2[3]), kernel=m3[1], thp=m3[2].strip(),` | Continues the dictionary of line 127. `name`: the name of the step. `boot`: the boot id. `memtotal_kB`: `MemTotal` at the start, in kB. `runnable`: the number of runnable tasks of the wait loop. `kernel`: the Linux kernel release. `thp`: the huge-page setting, without spaces at its ends. |
| 129 | `                load_after=(float(m4[1]), float(m4[2]), float(m4[3])), utc_after=T(m4[4]), memtotal_after_kB=int(m4[5]),` | Continues the dictionary of line 127. `load_after`, `utc_after`, `memtotal_after_kB`: the three load averages, the time and `MemTotal` in kB, read after the last process. |
| 130 | `                sha=shas, pcpu_max=max(pcpu) if pcpu else None)` | Ends the dictionary of line 127. `sha`: the checksums of line 124. `pcpu_max`: the highest `%CPU` value of the process list, or `None` when no row was found. When one of the four lines of lines 120 to 123 is missing, its match is `None` and the script ends with a Python error. |

### Patterns `LAUNCH` and `RC`, function `read_launches`: the file `launches.txt` (lines 133 to 158)

| Line | Source | Explanation |
|---:|---|---|
| 133 | `LAUNCH = re.compile(r'^launch (\S+) utc (\S+) load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) users (\d+) args (.*)$')` | `LAUNCH`: a compiled pattern for a `launch` line of `launches.txt`. `rx.sh` writes such a line directly before it starts a process [Ref6]. Group 1: the tag. It is the first field of the spec line, for example `a6456`. Group 2: the time of day in UTC. Groups 3 to 5: the three load averages. Groups 6 and 7: the tasks that are runnable now and the number of all tasks. Group 8: the id of the newest process. Group 9: the number of logins. Group 10: the arguments of the binary, to the end of the line. |
| 134 | `RC = re.compile(r'^rc (\S+) (\S+) utc (\S+)$')` | `RC`: a compiled pattern for an `rc` line of `launches.txt`. `rx.sh` writes it when the process has ended [Ref6]. Group 1: the exit status. Group 2: the tag. Group 3: the time of day in UTC. |
| 137 | `def read_launches(folder):` | Starts the function `read_launches`. It reads the file `launches.txt` of one result folder of `rx.sh`. |
| 138 | `    """launches.txt of rx.sh: one dict per launch, with its rc line."""` | Comment: the function returns one dictionary per launch, with the values of its `rc` line. |
| 139 | `    out = []` | `out`: the list of the launches, empty at first. |
| 140 | `    with _open(os.path.join(folder, 'launches.txt')) as f:` | Opens the file `launches.txt` of the folder through `_open` (line 39). |
| 141 | `        for ln, line in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 142 | `            line = line.rstrip('\n')` | Removes the line end character from the line. |
| 143 | `            m = LAUNCH.match(line)` | Compares the line with the pattern `LAUNCH` (line 133). |
| 144 | `            if m:` | The line is a `launch` line. |
| 145 | `                out.append(dict(tag=m[1], utc=clock(folder, m[2]), load1=float(m[3]), load5=float(m[4]),` | Adds one entry for this launch. `tag`: the tag. `utc`: the launch time as a full date and time. The function `clock` (line 68) takes the date from the folder name. `load1`, `load5`: the load averages over 1 and 5 minutes. |
| 146 | `                                load15=float(m[5]), runnable=int(m[6]), tasks=int(m[7]), logins=int(m[9]), args=m[10],` | Continues the entry of line 145. `load15`: the load average over 15 minutes. `runnable`: the tasks that are runnable now. `tasks`: the number of all tasks. `logins`: the number of logins. `args`: the arguments of the binary, as one text. |
| 147 | `                                rc=None, rc_utc=None, line=ln))` | Ends the entry of line 145. `rc` (the exit status) and `rc_utc` (the end time) are `None` until the `rc` line is found. `line`: the line number of the `launch` line. |
| 148 | `                continue` | Goes on with the next line of the file. |
| 149 | `            m = RC.match(line)` | Compares the line with the pattern `RC` (line 134). |
| 150 | `            if m:` | The line is an `rc` line. |
| 151 | `                for la in out:` | Loop over the launches found so far, in file order. |
| 152 | `                    if la['tag'] == m[2] and la['rc'] is None:` | Takes the first launch with the same tag that has no exit status yet. |
| 153 | `                        la['rc'] = m[1]` | Stores the exit status. It is kept as text, for example `0`. |
| 154 | `                        la['rc_utc'] = clock(folder, m[3])` | Stores the time of the `rc` line as a full date and time (line 68). |
| 155 | `                        break` | Ends the search. So one `rc` line fills one launch. |
| 156 | `    return out` | Returns the list of launches. |

### Function `read_env`: the file `env.txt` of `rx.sh` (lines 159 to 173)

| Line | Source | Explanation |
|---:|---|---|
| 159 | `def read_env(folder):` | Starts the function `read_env`. It reads the file `env.txt` of one result folder. `rx.sh` writes this file once, before its first process [Ref6]. |
| 160 | `    """env.txt of rx.sh."""` | Comment: `env.txt` of `rx.sh`. |
| 161 | `    lines = _open(os.path.join(folder, 'env.txt')).read().splitlines()` | `lines`: the lines of `env.txt`, without the line end characters. The file is opened through `_open` (line 39). |
| 162 | `    m = None` | `m`: the match of the `binary` line. `None` means that no such line was found so far. |
| 163 | `    for l in lines:` | Loop over the lines of the file. |
| 164 | `        m = re.match(r'binary (\S+) ([0-9a-f]{64})', l) or m` | A line fits when it starts with the word `binary`, then a path, then 64 hexadecimal digits. Group 1: the path of the runner binary. Group 2: its sha256. When the line does not fit, `m` keeps its value. So `m` ends as the match of the last fitting line. |
| 165 | `    pcpu = [float(x) for x in re.findall(r'^\S+\s+(\d+(?:\.\d+)?) \S+', '\n'.join(lines[3:]), re.M)]` | `pcpu`: the `%CPU` values of the process list, as numbers. The search covers the text from the fourth line of the file to its end. A line fits when it starts with a word, then spaces, then a number with or without decimals, one space and one more word. This is a row of the process list: user, `%CPU`, command. |
| 166 | ``    # the process list of `ps -eo user,pcpu,comm --sort=-pcpu \| head -6`: (user, %CPU, command, line number)`` | Comment: the process list is the output of `ps -eo user,pcpu,comm --sort=-pcpu \| head -6`, which is a title row and the 5 processes with the highest `%CPU`. The list `top` holds each row as user, `%CPU`, command and line number. |
| 167 | `    top = [(t[1], float(t[2]), t[3], ln) for ln, t in ((ln, re.match(r'^(\S+)\s+(\d+(?:\.\d+)?) (\S+)', l))` | `top`: a list with one entry per row of the process list: the user, the `%CPU` value as a number, the command and the line number. The pattern is the pattern of line 165 with three groups: the user, the `%CPU` value and the command. |
| 168 | `                                                      for ln, l in enumerate(lines, 1) if ln > 3) if t]` | Continues the list of line 167. Only the lines after the third line of the file are tested. A line that does not fit the pattern gives no entry. |
| 169 | `    start = dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y')` | `start`: the first line of the file as a `datetime` value. The line is the output of `date -u`. The form string reads a weekday, a month name, a day, a time on the 12-hour clock with `AM` or `PM`, the word `UTC` and a year. |
| 170 | `    return dict(start=start, kernel=lines[1], loadavg=lines[2], binary=m[1] if m else None, sha=m[2] if m else None,` | Returns the values. `start`: the time of line 169. `kernel`: the second line of the file, the release of the Linux kernel. `loadavg`: the third line, the content of `/proc/loadavg`, as text. `binary` and `sha`: the path and the sha256 of the runner, from the `binary` line. Both are `None` when the file has no such line. |
| 171 | `                pcpu_max=max(pcpu) if pcpu else None, top=top, n_lines=len(lines))` | Ends the dictionary of line 170. `pcpu_max`: the highest `%CPU` value, or `None` when no row was found. `top`: the list of line 167. `n_lines`: the number of lines of the file. |

### Function `read_error_records`: hardware error records of a saved journal (lines 174 to 192)

| Line | Source | Explanation |
|---:|---|---|
| 174 | `def read_error_records(path):` | Starts the function `read_error_records`. It lists the hardware error records in a saved text copy of the journal. The journal is the system log of Linux. A hardware error record is a message that the firmware passes to Linux when hardware reports an error. |
| 175 | `    """Hardware error records of a saved journal. One record = one line` | Comment: the function reads the hardware error records of a saved journal. One record is one line with the text of line 176. |
| 176 | `    'Hardware error from APEI Generic Hardware Error Source'. Returns line, time, record number, severity."""` | Comment: that text is `Hardware error from APEI Generic Hardware Error Source`. The function returns the line number, the time, the record number and the severity of each record. APEI is the ACPI Platform Error Interface, the way in which the firmware reports errors to Linux. |
| 177 | `    out, by_id = [], {}` | `out`: the list of the records, empty at first. `by_id`: the newest record of each record number. |
| 178 | `    with _open(path) as f:` | Opens the journal file through `_open` (line 39). |
| 179 | `        for ln, l in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 180 | `            m = re.match(r'(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$', l.rstrip('\n'))` | A line of interest has this form: a time that ends with `+00:00`, a host name, the word `kernel:`, a record number in curly braces, the mark `[Hardware Error]:` and a message. Group 1: the time without `+00:00`. Group 2: the record number. Group 3: the message. |
| 181 | `            if not m:` | Tests whether the line has another form. |
| 182 | `                continue` | Such a line is skipped. |
| 183 | `            if m[3].startswith('Hardware error from APEI'):` | A message that starts with `Hardware error from APEI` opens a new record. |
| 184 | `                rec = dict(line=ln, utc=dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S'), id=int(m[2]), severity=None)` | `rec`: the new record. `line`: the line number. `utc`: the time of group 1 as a `datetime` value. `id`: the record number. `severity`: `None` for now. |
| 185 | `                out.append(rec)` | Adds the record to the result. |
| 186 | `                by_id[int(m[2])] = rec` | Remembers the record under its number. A later record with the same number takes its place in `by_id`. |
| 187 | `            s = re.match(r'event severity: (\S+)', m[3])` | Tests whether the message starts with `event severity:`. Group 1 is the word after it, for example `corrected` in the saved journal `h-5.txt`. |
| 188 | `            if s and int(m[2]) in by_id and by_id[int(m[2])]['severity'] is None:` | The severity is taken when a record with this number exists and has no severity yet. |
| 189 | `                by_id[int(m[2])]['severity'] = s[1]` | Stores the severity in that record. So each record gets the first severity line that follows it with the same record number. |
| 190 | `    return out` | Returns the list of records. |

### Function `step_headers`: the `-- step` header lines of an earlier csv (lines 193 to 205)

| Line | Source | Explanation |
|---:|---|---|
| 193 | `def step_headers(path):` | Starts the function `step_headers`. It lists the `-- step` header lines of one csv file. `build_facts.py` calls it for csv files of the earlier script `run_partA.sh`. The csv files of the rerun of 2026-11-17 have no `-- step` line. These are the 3 files `threads120.csv` and the 9 bwx12 csv files in the result folders of the rerun. `ra.sh` and `rx.sh` write no such line [Ref5] [Ref6]. |
| 194 | `    """Every '-- step' line of a run_partA.sh csv: line, tag, binary, kernel, launch time."""` | Comment: every `-- step` line of a csv of `run_partA.sh` gives its line number, tag, binary, kernel and launch time. |
| 195 | `    out = []` | `out`: the list of the header lines, empty at first. |
| 196 | `    folder = os.path.dirname(path)` | `folder`: the folder of the csv file. Its name gives the date for `clock` (line 68). |
| 197 | `    with _open(path) as f:` | Opens the csv through `_open` (line 39). |
| 198 | `        for ln, l in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 199 | `            m = HDR_STEP.match(l.rstrip('\n'))` | Compares the line, without its line end character, with the pattern `HDR_STEP` (line 260). |
| 200 | `            if m:` | The line is a `-- step` header line. |
| 201 | `                out.append(dict(line=ln, tag=m[2], binary=m[3], kernel=re.search(r'--kernel (\S+)', m[12])[1],` | Adds one entry. `line`: the line number. `tag`: the tag of the process. `binary`: the name of the binary. `kernel`: the word after `--kernel` in the arguments of the binary. |
| 202 | `                                utc=clock(folder, m[11]), args=m[12], load1=float(m[5]), step=m[1]))` | Ends the entry of line 201. `utc`: the launch time as a full date and time (line 68). `args`: the arguments of the binary. `load1`: the 1-minute load average of the header line. `step`: the name of the step. |
| 203 | `    return out` | Returns the list. |

### Function `read_try6`: the record of 12 memory modules at 7200 MT/s (lines 206 to 257)

| Line | Source | Explanation |
|---:|---|---|
| 206 | `def read_try6():` | Starts the function `read_try6`. It reads three files of the folder `dimm7200-20261117` in `R`: `try6.txt`, `boots.txt` and `gaps.txt`. It takes no argument. |
| 207 | `    """R/dimm7200-20261117/try6.txt: the record of 12 modules at 7200 MT/s in the boot of the rerun."""` | Comment: `R/dimm7200-20261117/try6.txt` is the record of 12 memory modules at 7200 MT/s in the boot of the rerun. |
| 208 | `    path = os.path.join(R, 'dimm7200-20261117', 'try6.txt')` | `path`: the path of `try6.txt`. |
| 209 | `    lines = _open(path).read().splitlines()` | `lines`: the lines of the file, opened through `_open` (line 39). |
| 210 | `    out = dict(path=path, utc=dt.datetime.strptime(lines[0], '%Y-%m-%dT%H:%M:%SZ'), boot=lines[1].strip(),` | `out`: the result. `path`: the path of the file. `utc`: the first line of the file as a `datetime` value. The line has the form `YYYY-MM-DDTHH:MM:SSZ`. `boot`: the second line, the boot id, without spaces at its ends. |
| 211 | `               utc_line=1, boot_line=2, n_lines=len(lines))` | Ends the dictionary of line 210. `utc_line` and `boot_line`: the places of these two values in the file, the first and the second line. `n_lines`: the number of lines of the file. |
| 212 | `    for ln, l in enumerate(lines, 1):` | Loop over all lines of `try6.txt`. Each of the four tests below keeps a value and the number of the line that holds it. |
| 213 | `        m = re.match(r'MemTotal:\s+(\d+) kB', l)` | Tests for the line `MemTotal:` of the Linux file `/proc/meminfo`. Group 1 is the number of kB. |
| 214 | `        if m:` | The line fits. |
| 215 | `            out['memtotal_kB'], out['memtotal_line'] = int(m[1]), ln` | Stores `MemTotal` in kB as `memtotal_kB`, and the line number as `memtotal_line`. |
| 216 | `        m = re.search(r'This system has (\d+) DIMM sockets', l)` | Tests for the Linux kernel message `This system has N DIMM sockets`. Group 1 is the number N. |
| 217 | `        if m:` | The line holds this message. |
| 218 | `            out['dimm_sockets'], out['dimm_line'] = int(m[1]), ln` | Stores the number as `dimm_sockets`, and the line number as `dimm_line`. `build_facts.py` takes the module count of the records of the rerun from `dimm_sockets`. |
| 219 | `        m = re.match(r'\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s', l)` | Tests for a count line: a number, then the text `Configured Memory Speed:`, a speed and the unit `MT/s`. Group 1: the leading count, which is the number of entries with this speed. Group 2: the speed in MT/s. In the file `try6.txt` this line holds the count 12 and the speed 7200 MT/s. |
| 220 | `        if m:` | The line fits. |
| 221 | `            out['speed_count'], out['speed_MTps'], out['speed_line'] = int(m[1]), int(m[2]), ln` | Stores the count as `speed_count`, the speed as `speed_MTps` and the line number as `speed_line`. `build_facts.py` takes the memory speed of the records of the rerun from `speed_MTps`. |
| 222 | `        m = re.match(r'hwerr=(\d+)', l)` | Tests for a line that starts with `hwerr=`. Group 1 is the number after it. |
| 223 | `        if m:` | The line fits. |
| 224 | `            out['hwerr'], out['hwerr_line'] = int(m[1]), ln` | Stores the number as `hwerr`, and the line number as `hwerr_line`. |
| 225 | `    # gaps.txt and boots.txt number the boots of the journal; row 0 must be the boot of try6.txt` | Comment: the files `gaps.txt` and `boots.txt` number the boots of the journal. Row 0 must be the boot of `try6.txt`. |
| 226 | `    boots = os.path.join(R, 'dimm7200-20261117', 'boots.txt')` | `boots`: the path of `boots.txt` in the same folder. That file lists the boots of the journal, one per row: the boot number, the boot id, a first time and a last time. |
| 227 | `    row0 = [(ln, l.split()) for ln, l in enumerate(_open(boots), 1) if l.split()[:1] == ['0']]` | `row0`: the rows of `boots.txt` whose first field is `0`, each as the line number and the list of the fields. `l.split()` splits a row at the spaces. |
| 228 | `    if len(row0) != 1 or row0[0][1][1] != out['boot'].replace('-', ''):` | Two tests. Exactly one row must have the number 0. Its second field, the boot id, must be equal to the boot id of `try6.txt` with the `-` characters removed. |
| 229 | `        sys.exit('boots.txt: row 0 is not the boot of try6.txt')` | If one of the two tests fails, `sys.exit` prints this message to the error output and ends the script with exit status 1. |
| 230 | `    out['boots_path'], out['boots_line'] = boots, row0[0][0]` | Stores the path of `boots.txt` as `boots_path` and the line number of row 0 as `boots_line`. |
| 231 | `    f = row0[0][1]              # 0 <boot id> Tue 2026-11-17 20:02:21 UTC Tue 2026-11-17 20:06:19 UTC` | `f`: the fields of row 0. The comment shows the form of the row: the number 0, the boot id, then two times. Each time is a weekday, a date, a time of day and the word `UTC`. |
| 232 | `    if len(f) != 10 or f[5] != 'UTC' or f[9] != 'UTC':` | The row must have 10 fields, with `UTC` as field 6 and as field 10. |
| 233 | `        sys.exit('boots.txt: row 0 has another form than expected')` | If not, the script prints this message and ends with exit status 1. |
| 234 | `    out['boots_first'] = dt.datetime.strptime(f[3] + ' ' + f[4], '%Y-%m-%d %H:%M:%S')` | `boots_first`: the first time of the row, from the date in field 4 and the time of day in field 5, as a `datetime` value. |
| 235 | `    out['boots_last'] = dt.datetime.strptime(f[7] + ' ' + f[8], '%Y-%m-%d %H:%M:%S')` | `boots_last`: the last time of the row, from fields 8 and 9. |
| 236 | `    # first kernel log line of this boot (gaps.txt, row "0 first=...")` | Comment: the first line of the Linux kernel log of this boot comes from `gaps.txt`, from the row that starts with `0 first=`. |
| 237 | `    gaps = os.path.join(R, 'dimm7200-20261117', 'gaps.txt')` | `gaps`: the path of `gaps.txt` in the same folder. |
| 238 | `    for ln, l in enumerate(_open(gaps), 1):` | Loop over the lines of `gaps.txt`, opened through `_open` (line 39). |
| 239 | `        m = re.match(r'0 first=(\S+)\+00:00 last=(\S+)\+00:00 dimm=has (\d+) DIMM hwerr=(\d+) ', l)` | Tests for row 0 of `gaps.txt`. The row starts with `0 first=`. Group 1: the first time of the Linux kernel log of this boot. Group 2: its last time. Both times end with `+00:00` in the file. Group 3: the DIMM count after `dimm=has`. Group 4: the number after `hwerr=`. |
| 240 | `        if m:` | The line is row 0. |
| 241 | `            out['first_log_utc'] = dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S')` | `first_log_utc`: the first time as a `datetime` value. |
| 242 | `            out['last_log_utc'] = dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%S')` | `last_log_utc`: the last time as a `datetime` value. |
| 243 | `            out['gaps_dimm'], out['gaps_hwerr'] = int(m[3]), int(m[4])` | `gaps_dimm`: the DIMM count. `gaps_hwerr`: the number after `hwerr=`. |
| 244 | `            out['gaps_path'], out['gaps_line'] = gaps, ln` | `gaps_path`: the path of `gaps.txt`. `gaps_line`: the line number of row 0. |
| 245 | `            continue` | Goes on with the next line of the file. |
| 246 | ``        # lines after row 0: output of `uptime` and of the process list, taken when gaps.txt was written`` | Comment: the lines after row 0 are the output of the command `uptime` and of the process list. They were taken when `gaps.txt` was written. |
| 247 | `        m = re.match(r'\s*(\d\d:\d\d:\d\d) up ', l)` | Tests for the `uptime` line: a time of day and the word `up`. Group 1 is the time of day. |
| 248 | `        if m and 'first_log_utc' in out:` | The line counts only after row 0 was found. |
| 249 | `            out['gaps_uptime_utc'] = dt.datetime.combine(out['first_log_utc'].date(),` | `gaps_uptime_utc`: the time of day of the `uptime` line, joined with the date of `first_log_utc`. |
| 250 | `                                                         dt.datetime.strptime(m[1], '%H:%M:%S').time())` | Continues the call of line 249: the time of day of group 1, read in the form `HH:MM:SS`. |
| 251 | `            out['gaps_uptime_line'] = ln` | `gaps_uptime_line`: the line number of the `uptime` line. |
| 252 | `        m = re.match(r'(\S+)\s+(\d+\.\d+) (\S+)$', l.rstrip())` | Tests for a row of the process list: a user, spaces, a `%CPU` value with a decimal point, one space and a command at the end of the line. |
| 253 | `        if m and 'gaps_uptime_utc' in out:` | The row counts only after the `uptime` line was found. |
| 254 | `            out.setdefault('gaps_top', []).append((m[1], float(m[2]), m[3], ln))` | Adds the row to the list `gaps_top` as user, `%CPU` value, command and line number. `setdefault` creates the list at the first row. |
| 255 | `    return out` | Returns the result. |

### Part A files: pattern `HDR_STEP` and function `read_k120` (lines 258 to 306)

| Line | Source | Explanation |
|---:|---|---|
| 258 | `# ----------------------------------------------------------------------------- part A files (bandwidth.c)` | Comment: a divider line. The block below reads the part A files, the csv output of `bandwidth.c`. |
| 260 | `HDR_STEP = re.compile(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\d+)/(\d+) '` | `HDR_STEP`: a compiled pattern for a `-- step` header line. The earlier scripts `run_partA.sh` and `run_bwx.sh` write such a line as the header of each process. `ra.sh` and `rx.sh` of the rerun do not write this form [Ref5] [Ref6]. Group 1: the step. Group 2: the tag. Group 3: the binary. Group 4: the wait time after `waited_s`. Groups 5 to 7: the three load averages. Groups 8 and 9: the tasks that are runnable now and the number of all tasks. |
| 261 | `                      r'logins (\d+) utc (\S+) args (.*)$')` | Continues the pattern of line 260. Group 10: the number of logins. Group 11: the time of day in UTC. Group 12: the arguments of the binary, to the end of the line. |
| 264 | `def read_k120(path, only_tags=None):` | Starts the function `read_k120`. It reads a part A csv such as `threads120.csv` line by line. `only_tags` is an optional test function for the tags of a csv of `run_partA.sh` (line 283). |
| 265 | `    """Processes of a bandwidth.c csv. Header lines are '-- binary ...' (run_kernels.sh, ra.sh)` | Comment: the function returns the processes of a `bandwidth.c` csv. A header line has the form `-- binary ...` (scripts `run_kernels.sh` and `ra.sh`). |
| 266 | `    or '-- step ...' (run_partA.sh). Returns the processes in file order."""` | Comment: or it has the form `-- step ...` (script `run_partA.sh`). The processes are returned in file order. |
| 267 | `    procs, cur = [], None` | `procs`: the list of the processes found so far. `cur`: the process whose rows are read now. It is `None` before the first header line. |
| 268 | `    with _open(path) as f:` | Opens the csv through `_open` (line 39). |
| 269 | `        for ln, line in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 270 | `            line = line.rstrip('\n')` | Removes the line end character from the line. |
| 271 | `            m = stat_k120.HDR.match(line)` | Compares the line with the pattern `HDR` of `stat_k120.py`. It fits a header line that starts with `-- binary`. `ra.sh` writes this line directly before it starts the binary [Ref5]. The 8 groups hold the binary, the kernel, the thread count, the CPU list, the buffer size, the round, the load value and, when the line has one, the UTC time of day. |
| 272 | `            if m:` | The line is a `-- binary` header line. It starts a new process. |
| 273 | `                cur = dict(file=path, hdr_line=ln, binary=m[1], kernel=m[2], round=int(m[6]), load1=float(m[7]),` | `cur`: the entry of the new process. `file`, `hdr_line`: the csv and the line number of the header line. `binary`: `bw_old` or `bw_new`. `kernel`: the kernel name. With the kernel `read`, `bw_old` is the old read kernel and `bw_new` is the new read kernel. `round`: the round of the script (1 or 2). `load1`: the load value of the header line, the 1-minute load average at the launch. |
| 274 | `                           utc=m[8], tag=None, args=None, iv=[], hdr_threads=m[3], hdr_cpus=m[4], hdr_bytes=m[5])` | Ends the entry of line 273. `utc`: the time of day of the launch, as text. `tag` and `args` are `None` for this header form. `iv`: the list of the intervals, empty at first. `hdr_threads`, `hdr_cpus`, `hdr_bytes`: the thread count, the CPU list and the buffer size of the header line, as text. |
| 275 | `                procs.append(cur)` | Adds the process to the result. |
| 276 | `                continue` | Goes on with the next line of the file. |
| 277 | `            m = HDR_STEP.match(line)` | Compares the line with the pattern `HDR_STEP` (line 260), the header form of the earlier script `run_partA.sh`. The 3 files `threads120.csv` of the rerun have no such header. `ra.sh` writes the `-- binary` form [Ref5]. |
| 278 | `            if m:` | The line is a `-- step` header line. It starts a new process too. |
| 279 | `                k = re.search(r'--kernel (\S+)', m[12])[1]` | `k`: the kernel name, the word after `--kernel` in the arguments of the binary. |
| 280 | `                rd = re.search(r'-r?(\d+)$', m[2])` | `rd`: a match of the number at the end of the tag. The number stands after a `-` or after `-r`. Group 1 holds its digits. A tag `onebuf-ms500-3` gives 3. |
| 281 | `                cur = dict(file=path, hdr_line=ln, binary=m[3], kernel=k, round=int(rd[1]), load1=float(m[5]),` | `cur`: the entry of the new process for this header form. `round`: the number of line 280. `load1`: the first load average of the header line. |
| 282 | `                           utc=m[11], tag=m[2], args=m[12], iv=[])` | Ends the entry of line 281. `utc`: the time of day, as text. `tag`, `args`: the tag and the arguments of the header line. This form stores no `hdr_threads`, `hdr_cpus` and `hdr_bytes`. |
| 283 | `                if only_tags is None or only_tags(m[2]):` | Without `only_tags` every process is kept. With `only_tags` a process is kept only when that function returns true for its tag. |
| 284 | `                    procs.append(cur)` | Adds the process to the result. |
| 285 | `                else:` | The other case: the tag failed the test of `only_tags`. |
| 286 | `                    cur['skip'] = True` | The process is not added to the result, and it gets the mark `skip`. `cur` still points to it. So the interval rows after it are stored in this entry and are dropped with it. |
| 287 | `                continue` | Goes on with the next line of the file. |
| 288 | `            if cur is not None and line.startswith('# bandwidth:'):` | Tests for the comment line that the binary prints first. It starts with `# bandwidth:`. |
| 289 | `                # header line that the binary prints: it says how the copy kernels count their bytes` | Comment: this header line of the binary says how the copy kernels count their bytes. |
| 290 | `                cur['copy_note'] = 'copy counts read+write bytes' in line` | `copy_note`: true when the line holds the text `copy counts read+write bytes`. The text means that the binary counts the bytes read plus the bytes written for the kernels `copy` and `asmcopy` [Ref1]. |
| 291 | `                cur['bw_hdr'] = line.split('; ')[-1]       # threads=... bytes_per_thread=... min_ms=... thp=...` | `bw_hdr`: the part of the line after the last `; `. The comment shows its four settings: `threads`, `bytes_per_thread`, `min_ms` (the shortest length of one interval in ms) and `thp`. |
| 292 | `                continue` | Goes on with the next line of the file. |
| 293 | `            p = line.split(',')` | `p`: the fields of the line, split at the commas. |
| 294 | `            if cur is not None and p[0] == 'thread' and len(p) == 6:` | Tests for a per-thread row: 6 fields, and the first field is the word `thread`. |
| 295 | `                # row of the option --per-thread: thread,index,cpu,kernel,rep,GBps` | Comment: such a row comes from the option `--per-thread` of the binary. Its fields are the word `thread`, the index of the thread, its CPU, the kernel, the repetition and the rate of this thread in GB/s. |
| 296 | `                cur.setdefault('thr', {}).setdefault(int(p[4]), []).append(float(p[5]))` | Stores the rate of the thread (field 6) in `thr`, in the list of its repetition (field 5). The 3 files `threads120.csv` of the rerun hold no such row: `ra.sh` does not pass `--per-thread` [Ref5]. |
| 297 | `                continue` | Goes on with the next line of the file. |
| 298 | `            if cur is not None and len(p) > 9 and p[3].isdigit():` | Which rows count as interval rows: a row after a header line that has at least 10 fields and whose field 4 (`rep`) is a number. This test leaves out the column title row and the `best` row. The `best` row holds the highest `aggregate_GBps` of the interval rows of one kernel, and its field 4 is the word `best` [Ref1]. This module takes no value from it. |
| 299 | `                if p[0] != cur['kernel'] and cur['kernel'] != 'all':` | Tests whether field 1, the kernel name of the row, differs from the kernel of the header line before it. A header line with the kernel `all` allows every name. |
| 300 | `                    sys.exit(f'{path}:{ln}: interval line does not belong to the header line before it')` | If the names differ, `sys.exit` prints the file, the line number and this message, and ends the script with exit status 1. |
| 301 | `                cur['iv'].append(dict(rep=int(p[3]), total_bytes=int(p[4]), elapsed_s=float(p[5]), agg=float(p[6]),` | The part A rate. Adds one entry per interval row to `iv`. `rep`: field 4, the number of the interval in the process. `total_bytes`: field 5, the bytes of all threads. `elapsed_s`: field 6, the longest per-thread time in seconds. `agg`: field 7, the column `aggregate_GBps`. This is the rate of the interval, taken as printed. The binary computed it as the sum of the bytes of all threads / the longest per-thread time / 1e9, and printed it with 2 decimals [Ref1]. |
| 302 | `                                      tmin=float(p[7]), tmax=float(p[8]), tavg=float(p[9]),` | Continues the entry of line 301. `tmin`, `tmax`, `tavg`: fields 8, 9 and 10, the lowest, the highest and the mean per-thread rate in GB/s. The time of a thread starts at its clock read after the binary releases all threads together. It ends at its clock read after its last whole pass over the buffer. One warm-up pass of the same kernel comes before this time and is not timed [Ref1]. |
| 303 | `                                      passes=int(p[4]) // int(p[2]), threads=int(p[1]), line=ln, kernel=p[0]))` | Ends the entry of line 301. `passes`: field 5 divided by field 3 (`bytes_per_thread`), rounded down. It is the only value that this function computes. For the kernels `read`, `asmread`, `write` and `asmwrite` it is the number of buffer passes of all threads in the interval. For `copy` and `asmcopy` it is 2 x that number: the binary counts the bytes read plus the bytes written for these two kernels [Ref1]. `threads`: field 2. `line`: the line number of the row. `kernel`: field 1. Example: the first interval row of `threads120.csv` of T72A1 is `read,120,268435456,0,256087425024,0.5474,467.83,2.98,4.93,3.99`. It gives `agg` = 467.83 GB/s and `passes` = 954 [Ref9]. |
| 304 | `    return procs` | Returns the processes in file order. |

### bwx csv files: functions `_new_section` and `read_bwx` (lines 307 to 355)

| Line | Source | Explanation |
|---:|---|---|
| 307 | `# ----------------------------------------------------------------------------- bwx csv files` | Comment: a divider line. The block below reads the csv files of the bwx runners. |
| 309 | `def _new_section(path, step=None, line=None):` | Starts the function `_new_section`. It returns an empty container for the rows of one process of a bwx csv. A section is the part of a csv file that one process wrote. |
| 310 | `    return dict(file=path, step=step, step_line=line, hdr={}, T={}, Tl={}, I={}, P=[], C=0)` | The container. `file`: the path of the csv. `step`, `step_line`: the values and the line number of the `-- step` header line, when the file has one. `hdr`: the values of the comment lines at the top of the csv. `T`: the T rows. `Tl`: the first and the last line number of the T rows of each interval. `I`: the I rows. `P`: the P rows. `C`: the number of C rows. |
| 313 | `def read_bwx(path):` | Starts the function `read_bwx`. It reads the csv of a runner, for example `a6456.csv` (part L and control I) or `cfwd.csv` and `crev.csv` (part C). |
| 314 | `    """Sections of a bwx csv. A file of rx.sh has one section. A file of run_bwx.sh (B7, C3, B5)` | Comment: the function returns the sections of a bwx csv. A file of `rx.sh` has one section. The sentence on a file of `run_bwx.sh` (steps B7, C3 and B5) goes on in line 315. |
| 315 | `    has one section per '-- step' line."""` | Comment: a file of `run_bwx.sh` has one section per `-- step` line. |
| 316 | `    secs, cur = [], None` | `secs`: the list of the sections. `cur`: the section whose rows are read now. It is `None` before the first line. |
| 317 | `    with _open(path) as f:` | Opens the csv through `_open` (line 39). |
| 318 | `        for ln, line in enumerate(f, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 319 | `            line = line.rstrip('\n')` | Removes the line end character from the line. |
| 320 | `            if line.startswith('-- step'):` | A `-- step` line starts a new section. A csv of the earlier script `run_bwx.sh` has one `-- step` line per process. |
| 321 | `                m = HDR_STEP.match(line)` | Takes the values of the line with the pattern `HDR_STEP` (line 260). |
| 322 | `                cur = _new_section(path, dict(step=m[1], tag=m[2], binary=m[3], load1=float(m[5]), load5=float(m[6]),` | Creates the new section (line 309). Its key `step` holds the values of the header line. This line: the step, the tag, the binary and the load averages over 1 and 5 minutes. |
| 323 | `                                              load15=float(m[7]), runnable=int(m[8]), logins=int(m[10]), utc=m[11],` | Continues the values of line 322: the load average over 15 minutes, the tasks that are runnable now, the number of logins and the time of day as text. |
| 324 | `                                              args=m[12]), ln)` | Ends the call of line 322: the arguments of the binary, and the line number of the header line as `step_line`. |
| 325 | `                secs.append(cur)` | Adds the section to the result. |
| 326 | `                continue` | Goes on with the next line of the file. |
| 327 | `            if cur is None:` | Tests whether no section is open yet. This is the case at the first line of a csv that `rx.sh` wrote. Such a file has no `-- step` line. |
| 328 | `                cur = _new_section(path)` | Creates a section without `step` values. |
| 329 | `                secs.append(cur)` | Adds it to the result. The whole file is then one section, and it holds one process. |
| 330 | `            if line.startswith('#'):` | Tests for a comment line of the csv. It starts with `#`. |
| 331 | `                if line.startswith('# bandwidth:') or line.startswith('# bwx:'):` | The runner prints two header lines first. They start with `# bandwidth:` and `# bwx:` and hold settings in the form `name=value`. |
| 332 | `                    for key in ('min_ms', 'thp', 'seq', 'rounds', 'stop', 'start', 'two_buffers', 'count'):` | Loop over the 8 settings that are stored. `seq` is the kernel sequence of the process, for example `oldread,asmread,read_nop96,read_nop256,read_1pl`. `stop` is the stop rule [Ref2]. With `common` the runner sets one start time and one deadline, `min_ms` milliseconds later, for all threads. Each thread stops after the chunk (2 MiB here) in which the deadline passes. With `pass` each thread stops after a whole pass over its buffer, `min_ms` milliseconds or more after its own start. |
| 333 | `                        m = re.search(r'\b%s=([^\s;]+)' % key, line)` | Searches the line for the name of the setting as a whole word, followed by `=`. Group 1 is the value: the characters up to the next space or `;`. |
| 334 | `                        if m and key not in cur['hdr']:` | The value is taken only when the section has no value for this setting yet. So the first value found is kept. |
| 335 | `                            cur['hdr'][key] = m[1]` | Stores the value as text in `hdr`. The value of `start` is not a time. It is the place in its buffer where a thread starts: `common` (the start of the buffer) or `offset` (a 2 MiB chunk that depends on the thread number) [Ref2]. All 9 bwx12 csv files of the rerun (parts L and C, control I) say `stop=common` and `start=common` in their header line `# bwx:`. |
| 336 | `                continue` | Every comment line ends here. So every other comment line is skipped, for example the column title lines and the `# page_read` lines. |
| 337 | `            p = line.split(',')` | `p`: the fields of a data row, split at the commas. Field 1 is the row kind: `T`, `I`, `P` or `C`. |
| 338 | `            if p[0] == 'T':` | T rows: one row per thread and interval. |
| 339 | `                if len(p) != 13:` | A T row must have 13 fields. |
| 340 | `                    sys.exit(f'{path}:{ln}: a T row with {len(p)} fields, 13 expected')` | If not, `sys.exit` prints the file, the line number and the field count, and ends the script with exit status 1. |
| 341 | `                # cpu, bytes, elapsed_s, flags, t_start_s, t_end_s (seconds since the process start)` | Comment: the 6 values kept per thread are the CPU, the bytes, `elapsed_s`, the flags, `t_start_s` and `t_end_s`. The two times count the seconds from the process start. They are the start and the end of the time `elapsed_s` of the thread. The flag is `late` when the thread started more than 100 microseconds after the common start time of the interval. In every other case it is `-` [Ref2]. |
| 342 | `                cur['T'].setdefault((int(p[1]), int(p[2]), p[3]), []).append(` | The key of an interval is the round, the position and the kernel name, from fields 2 to 4. `setdefault` creates the list of the interval at its first T row. The row is added to this list as the 6 values of line 343. |
| 343 | `                    (int(p[5]), int(p[6]), float(p[7]), p[-1], float(p[9]), float(p[10])))` | Continues the call of line 342: the 6 values, from the fields 6 (CPU), 7, 8, 13 (flag), 10 and 11 [Ref2]. Field 7, `bytes`: the bytes that the runner counted for this thread in the interval. For a read kernel it adds the size of every buffer range that it gave to the kernel. `oldread`, `read`, `asmread`, `read_nop96` and `read_nop256` read every byte of the range. `read_1pl` loads only 16 of every 64 bytes, and the runner still counts the full size. Field 8, `elapsed_s`: the time of this thread in seconds, with 6 decimals. It runs from the clock read directly before its first timed kernel call to the clock read after its last kernel call. The warm-up call comes before this time. |
| 344 | `                tl = cur['Tl'].setdefault((int(p[1]), int(p[2]), p[3]), [ln, ln])` | `Tl` keeps the first and the last line number of the T rows of each interval. The first T row of an interval creates the pair, with its own line number in both places. |
| 345 | `                tl[1] = ln` | Every T row then sets the second number to its own line number. Fields 5, 9 and 12 of a T row (`tid`, `t_sched_s`, `passes`) are not kept. |
| 346 | `            elif p[0] == 'I':` | I rows: one row per interval. |
| 347 | `                cur['I'][(int(p[1]), int(p[2]), p[3])] = dict(threads=int(p[5]), total_bytes=int(p[6]),` | Stores the row under the same key as the T rows. `threads`: field 6. `total_bytes`: field 7. |
| 348 | `                                                             max_elapsed_s=float(p[7]), agg=float(p[8]), line=ln)` | Ends the entry of line 347. `max_elapsed_s`: field 8. `agg`: field 9, `aggregate_GBps` as the runner printed it: total bytes / longest per-thread time, with 2 decimals [Ref2]. `line`: the line number of the row. This module does not use `agg` as the rate of the interval. For the 9 bwx12 csv files of the rerun, `build_facts.py` checks that it differs from the total of the T rows by less than 0.05 GB/s [Ref3]. It makes no such check for the bwx csv files of the earlier runs. |
| 349 | `            elif p[0] == 'P':` | P rows: each row holds the page state of one buffer of one thread. The runner prints one P row per thread before the first interval and after each interval [Ref2]. |
| 350 | `                cur['P'].append(tuple([int(p[1]), int(p[2]), int(p[3]), p[4]] + [int(x) for x in p[5:11]]))` | Stores the row as a tuple of 10 values: the round, the position, the thread, the buffer letter and the 6 numbers of fields 6 to 11. The first two numbers are `kB_total`, the size of the memory area of the buffer in kB, and `kB_huge`, the part of it on transparent huge pages in kB. The four other numbers are counters of Linux for the whole system [Ref2]. The buffer letter is `a` for the first buffer of a thread and `b` for its second buffer. The 9 bwx12 csv files of the rerun hold only `a` rows. |
| 351 | `            elif p[0] == 'C':` | C rows: one row per thread and interval, with counter values. |
| 352 | `                cur['C'] += 1` | C rows are only counted. A row of any other kind is ignored. |
| 353 | `    return secs` | Returns the list of sections. |

### Function `bwx_intervals`: one rate per interval from the T rows (lines 356 to 385)

| Line | Source | Explanation |
|---:|---|---|
| 356 | `def bwx_intervals(sec):` | Starts the function `bwx_intervals`. It takes one section of `read_bwx` and forms one rate per interval from the T rows. This is the second kind of rate of the module comment (line 12). |
| 357 | `    """One dict per interval (round, pos, kernel) of a section, in file order."""` | Comment: the function returns one dictionary per interval (round, position, kernel) of a section, in file order. |
| 358 | `    seq = sec['hdr'].get('seq', '').split(',')` | `seq`: the kernel sequence of the csv header, as a list of names. Without a `seq` value the list holds one empty name. |
| 359 | `    out = []` | `out`: the list of the intervals, empty at first. |
| 360 | `    for (rnd, pos, kernel), tl in sec['T'].items():` | Loop over the intervals, in the order of their first T row in the file. `tl` is the list of the T rows of the interval, one per thread. |
| 361 | `        rate = lambda t: t[1] / t[2] / 1e9` | `rate`: the rate of one thread in GB/s: its `bytes` / its `elapsed_s` / 1e9. So the bytes of each thread are divided by the time of that thread. |
| 362 | `        m0 = [rate(t) for t in tl if t[0] < 64]` | `m0`: the rates of the threads on the CPUs 0 to 63 (mesh 0). |
| 363 | `        m1 = [rate(t) for t in tl if t[0] >= 64]` | `m1`: the rates of the threads on the CPUs 64 and higher (mesh 1). The two lists together hold every T row of the interval. No T row is left out. A row with the flag `late` is used like every other row. The 9 bwx12 csv files of the rerun hold no row with this flag. |
| 364 | `        cpus = [t[0] for t in tl]` | `cpus`: the CPU of each T row. |
| 365 | `        i = sec['I'].get((rnd, pos, kernel))` | `i`: the I row of the same interval, or `None` when the file has none. |
| 366 | `        if pos > 0:` | Lines 366 to 371 find `before`, the kernel that was timed directly before this interval in the same process. Case 1: a position above 0. |
| 367 | `            before = seq[pos - 1]` | `before` is the kernel one position earlier in `seq`. |
| 368 | `        elif rnd > 0:` | Case 2: position 0 of a later round. |
| 369 | `            before = seq[-1]` | `before` is the last kernel of `seq`. |
| 370 | `        else:` | Case 3: the first interval of the process. |
| 371 | `            before = None` | `before` is `None`. The value comes from `seq`, not from a time in the file. Before each timed interval the runner also makes one warm-up pass with the kernel of that interval. This pass is not timed [Ref2]. |
| 372 | `        assert seq[pos] == kernel, (sec['file'], rnd, pos, kernel, seq)` | The `assert` stops the script with an error when the kernel name of the rows is not the name at this position of `seq`. The error shows the file, the round, the position, the name and the sequence. |
| 373 | `        out.append(dict(round=rnd, pos=pos, kernel=kernel, kernel_before=before, threads=len(tl),` | Adds the entry of the interval. `round`, `pos`, `kernel`: the key of the interval. `kernel_before`: the value of lines 366 to 371. `threads`: the number of T rows. |
| 374 | `                        total=sum(m0) + sum(m1), mesh0=sum(m0), mesh1=sum(m1), n0=len(m0), n1=len(m1),` | The bwx rate. `total`: the sum of `m0` plus the sum of `m1`. This is the sum of the per-thread rates of all threads of the interval, in GB/s. `build_facts.py` takes this value as the rate of a bwx12 interval [Ref3]. `mesh0`, `mesh1`: the same sum for each mesh. `n0`, `n1`: the thread counts per mesh. Nothing is rounded here. Example: T72L1, `a6456.csv`, round 0, position 0, `oldread`. The 120 T rows give 305.13 GB/s on mesh 0 and 157.17 GB/s on mesh 1. Their sum `total` is 462.30 GB/s. The I row says 462.29 GB/s [Ref8]. |
| 375 | `                        m0_min=min(m0) if m0 else None, m0_max=max(m0) if m0 else None,` | Continues the entry of line 373. `m0_min`, `m0_max`: the lowest and the highest per-thread rate on mesh 0 in GB/s. Both are `None` when no thread ran there. |
| 376 | `                        m1_min=min(m1) if m1 else None, m1_max=max(m1) if m1 else None,` | Continues the entry of line 373. `m1_min`, `m1_max`: the same two values for mesh 1. |
| 377 | `                        is_64_56=(len(m0) == 64 and len(m1) == 56 and max(cpus) <= 119 and len(set(cpus)) == 120),` | `is_64_56`: true when 64 threads ran on the CPUs 0 to 63 and 56 threads on the CPUs 64 to 119, on 120 different CPUs. This is the thread placement of the whole-chip runs. |
| 378 | `                        flagged=sum(t[3] != '-' for t in tl), flags=sorted(set(t[3] for t in tl)),` | `flagged`: the number of T rows whose flag is not `-`. `flags`: the different flag values of the interval, sorted. |
| 379 | `                        I_agg=i['agg'] if i else None, line=i['line'] if i else None,` | `I_agg`: the value `aggregate_GBps` of the I row. `line`: the line number of the I row. Both are `None` when the interval has no I row. |
| 380 | `                        max_elapsed_s=i['max_elapsed_s'] if i else None,` | `max_elapsed_s`: the longest per-thread time of the I row in seconds, or `None` when the interval has no I row. |
| 381 | `                        t_start=min(t[4] for t in tl), t_end=max(t[5] for t in tl),` | `t_start`: the earliest `t_start_s` of the T rows of the interval. `t_end`: the latest `t_end_s`. Both are in seconds from the process start. |
| 382 | `                        T_first=sec['Tl'][(rnd, pos, kernel)][0], T_last=sec['Tl'][(rnd, pos, kernel)][1]))` | Ends the entry of line 373. `T_first`, `T_last`: the first and the last line number of the T rows of the interval. |
| 383 | `    return out` | Returns the list of intervals. |

### The data sets of the rerun, the names of the binaries and function `find` (lines 386 to 404)

| Line | Source | Explanation |
|---:|---|---|
| 386 | `# ----------------------------------------------------------------------------- the data sets` | Comment: a divider line. The block below names the data sets. |
| 388 | `RERUN_A = [('T72A1', 1), ('T72A2', 2), ('T72A3', 3)]` | `RERUN_A`: the result folders of part A of the rerun, each as a tag and a session number (1 to 3). The tag is the name that `go.sh` gives to the run script. It is part of the folder name. |
| 389 | `RERUN_L = [('T72L1', 1), ('T72L2', 2), ('T72L3', 3)]` | `RERUN_L`: the result folders of part L, sessions 1 to 3. |
| 390 | `RERUN_C = [('T72C1', 1, 'cfwd'), ('T72C2', 2, 'crev'), ('T72C3', 3, 'cfwd'), ('T72C4', None, 'crev')]` | `RERUN_C`: the result folders of part C, with the name of the spec file as third value (`cfwd` or `crev`). `T72C4` has no session (`None`): it ran after session 3. In the log of `go.sh` the state line `after T72C4` follows the state line `after T72C3`. |
| 391 | `RERUN_I = [('T72I1', 1), ('T72I2', 2)]` | `RERUN_I`: the result folders of control I, the two processes that `go2.sh` starts. The number counts the control processes. It is not a session. |
| 393 | `SHA_NAMES = {  # short names of the binaries, by sha256 prefix, as the result files record them` | `SHA_NAMES`: starts a dictionary from the first 8 hexadecimal digits of a sha256 to the short name of a binary. The comment says that these are the checksums that the result files record. |
| 394 | `    'e8fc0205': 'bw_old', 'fd7c14df': 'bw_new', 'cd58e564': 'bwx12', 'f1215f9e': 'bwx11', '5b702073': 'bwx'}` | The five entries of line 393: `bw_old`, `bw_new`, `bwx12`, `bwx11` and `bwx`. `build_facts.py` uses the dictionary to name the binary of an earlier bwx csv from the checksum of its folder. |
| 397 | `def find(prefix):` | Starts the function `find`. It returns the one result folder of a tag. |
| 398 | `    """The one result folder whose name starts with prefix."""` | Comment: the one result folder whose name starts with `prefix`. |
| 399 | `    hits = sorted(glob.glob(os.path.join(R, prefix + '-2026*')))` | `hits`: the sorted list of the entries of `R` whose names start with the prefix followed by `-2026`. The `*` of the pattern stands for the rest of the name. Example: the prefix `k120-T72A1` gives the folder `k120-T72A1-20261117T221209Z` [Ref9]. |
| 400 | `    if len(hits) != 1:` | Tests whether the number of entries differs from 1. |
| 401 | `        sys.exit(f'expected one folder for {prefix}, found {hits}')` | Then `sys.exit` prints the prefix and the list of entries, and ends the script with exit status 1. So the script stops when a result folder is missing or exists twice. |
| 402 | `    return hits[0]` | Returns the path of the one folder. |

### Function `read_boot_table`: the boot history of the DIMM report (lines 405 to 420)

| Line | Source | Explanation |
|---:|---|---|
| 405 | `def read_boot_table():` | Starts the function `read_boot_table`. It reads two things from the tables of the report `DIMM-flaky-report.md` (line 30). `build_facts.py` uses them for the result folders of earlier runs [Ref3]. |
| 406 | `    """Boot history of the DIMM report (section 3): list of (boot number, Linux start, modules),` | Comment: the function returns the boot history of section 3 of the DIMM report as a list of boot number, Linux start time and module count. |
| 407 | `    and the time until which the memory speed setting was 8000 MT/s."""` | Comment: it also returns the time until which the memory speed setting was 8000 MT/s. |
| 408 | `    path = DIMM_REPORT` | `path`: the path of the report. |
| 409 | `    boots, until = [], None` | `boots`: the list of the boots, empty at first. `until`: the entry of the memory speed row, `None` until the row is found. |
| 410 | `    for ln, line in enumerate(_open(path), 1):` | Loop over the lines of the report, opened through `_open` (line 39). `ln` is the line number, counted from 1. |

Line 411 holds a backslash directly before a `|`. It stands outside the table:

```text
        m = re.match(r'\| (-?\d+) \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \| \**(\d+)\** \|', line)
```

Explanation of line 411: Tests for a row of the boot table. Its first three cells are a boot number, a start time and a module count. Group 1: the boot number, with an optional minus sign. Group 2: the start time in the form `YYYY-MM-DD HH:MM`. Group 3: the module count. The pattern allows `*` characters around the count. So a count that the report writes in bold fits too.

| Line | Source | Explanation |
|---:|---|---|
| 412 | `        if m:` | The line is a row of the boot table. |
| 413 | `            boots.append(dict(no=int(m[1]), start=dt.datetime.strptime(m[2], '%Y-%m-%d %H:%M'), modules=int(m[3]),` | Adds one boot. `no`: the boot number. `start`: the start time of Linux as a `datetime` value. `modules`: the number of memory modules. |
| 414 | `                              line=ln))` | Ends the entry of line 413. `line`: the line number of the table row. |

Line 415 holds a backslash directly before a `|`. It stands outside the table:

```text
        m = re.match(r'\| Memory speed until (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC \| (\d+) MT/s', line)
```

Explanation of line 415: Tests for the table row that starts with `Memory speed until`. Group 1: the date and time before the word `UTC`. Group 2: the speed in MT/s in the next cell.

| Line | Source | Explanation |
|---:|---|---|
| 416 | `        if m:` | The line is this row. |
| 417 | `            until = dict(utc=dt.datetime.strptime(m[1], '%Y-%m-%d %H:%M'), speed=int(m[2]), line=ln)` | `until`: the time until which the memory speed setting had this value (`utc`), the speed in MT/s (`speed`) and the line number (`line`). |
| 418 | `    return dict(path=path, boots=sorted(boots, key=lambda b: b['start']), until=until)` | Returns the path of the report, the boots in the order of their start time, and the entry `until`. |

### Function `base_record` and the two texts for `rate_kind` (lines 421 to 439)

| Line | Source | Explanation |
|---:|---|---|
| 421 | `def base_record(**kw):` | Starts the function `base_record`. It returns one interval record for `facts.json` with all 40 keys. `build_facts.py` creates one record per interval [Ref3]. `**kw` takes the values of the caller in the form `key=value`. |
| 422 | `    """One flat interval record of facts.json. Every record has every key."""` | Comment: one flat interval record of `facts.json`. Every record has every key. |
| 423 | `    rec = dict(dataset=None, part=None, role=None, speed_MTps=None, modules=None, boot=None,` | `rec`: the record with every key set to `None`. The keys of this line: the data set, the part of the test, the role of the data set, the memory speed in MT/s, the number of memory modules and the boot. |
| 424 | `               folder=None, file=None, line=None, tag=None, session=None, process=None, proc_key=None, round=None,` | Continues the record of line 423: the result folder, the csv file, the line number of the interval in the file, the tag, the session, the number of the process in the file, a text that is equal for all records of one process (`proc_key`) and the round. |
| 425 | `               pos=None, interval=None, kernel=None, kernel_before=None, binary=None, binary_sha256=None, GBps=None,` | Continues the record of line 423: the position, the number of the interval in the process, the kernel, the kernel that was timed before it, the binary, the sha256 of the binary and `GBps`. `GBps` holds the rate of the interval in GB/s. |
| 426 | `               rate_kind=None, mesh0_GBps=None, mesh1_GBps=None, passes=None, per_thread_min_GBps=None,` | Continues the record of line 423. `rate_kind` says how the rate was formed (lines 436 to 437). `mesh0_GBps`, `mesh1_GBps`: the rate per mesh, for bwx records. `passes`: the pass count, for part A records. `per_thread_min_GBps`: the lowest per-thread rate, for part A records. |
| 427 | `               per_thread_max_GBps=None, per_thread_avg_GBps=None, threads=None, is_64_56=None, flagged=None,` | Continues the record of line 423: the highest and the mean per-thread rate (part A records), the thread count, the result of the 64+56 test of line 377 and the number of flagged T rows (both for bwx records). |
| 428 | `               stop=None, start=None, min_ms=None, count=None, thp=None, load1_at_launch=None, launch_utc=None,` | Continues the record of line 423: the stop rule, the start place of the threads (`start`), the shortest length of one interval in ms (`min_ms`), the values `count` and `thp` of the csv header, the 1-minute load average at the launch of the process and the launch time in UTC. |
| 429 | `               gap_s=None, start_state=None)` | Ends the record of line 423. `gap_s`: the seconds from the end of the step before to this launch. `start_state`: a sentence on the state of the machine at the start. `build_facts.py` fills both for the records of the rerun. |
| 430 | `    unknown = set(kw) - set(rec)` | `unknown`: the keys of the caller that the record does not have. |
| 431 | `    assert not unknown, unknown` | The `assert` stops the script with an error when the caller passed such a key. So a typing error in a key name cannot add a new key to a record. |
| 432 | `    rec.update(kw)` | Puts the values of the caller into the record. |
| 433 | `    return rec` | Returns the record. |
| 436 | `KIND_A = 'aggregate_GBps column of the csv (sum of bytes / longest per-thread time)'` | `KIND_A`: the text for `rate_kind` of a part A record. It says that the rate is the csv column `aggregate_GBps`: the sum of the bytes / the longest per-thread time. |
| 437 | `KIND_X = 'sum over the T rows (threads) of bytes / elapsed_s / 1e9'` | `KIND_X`: the text for `rate_kind` of a record of a bwx runner. It says that the rate is the sum over the T rows (threads) of `bytes / elapsed_s / 1e9`. |

### Selection and statistics: functions `sel`, `rng`, `overlap`, `gap`, `width_pct` (lines 440 to 485)

| Line | Source | Explanation |
|---:|---|---|
| 440 | `# ----------------------------------------------------------------------------- selection and statistics` | Comment: a divider line. The block below holds the functions that select records and compute ranges. |
| 442 | `def sel(recs, **cond):` | Starts the function `sel`. It returns the records that pass every condition. A condition is written `key=value`. Example of a call in `facts_text.py`: `sel(recs, dataset='rerun-L', kernel='oldread')` returns the part L intervals of the old read kernel [Ref4]. |
| 443 | `    """Records that match every condition. A condition value may be a value, a set, or a function."""` | Comment: the function returns the records that match every condition. A condition value may be a value, a set or a function. |
| 444 | `    out = []` | `out`: the list of the records that pass, empty at first. |
| 445 | `    for r in recs:` | Loop over the records. |
| 446 | `        for k, v in cond.items():` | Loop over the conditions of the call. `k` is the key and `v` is the condition value. |
| 447 | `            x = r[k]` | `x`: the value of the record for this key. |
| 448 | `            if callable(v):` | Case 1: the condition value is a function. |
| 449 | `                ok = v(x)` | The function must return true for the value of the record. |
| 450 | `            elif isinstance(v, (set, frozenset, list, tuple)):` | Case 2: the condition value is a set, a list or a tuple. |
| 451 | `                ok = x in v` | It must contain the value of the record. |
| 452 | `            else:` | Case 3: a plain value. |
| 453 | `                ok = x == v` | It must be equal to the value of the record. |
| 454 | `            if not ok:` | Tests whether this condition failed. |
| 455 | `                break` | Then the loop over the conditions ends at once. The record is not taken. |
| 456 | `        else:` | This `else` belongs to the `for` of line 446. Python runs it only when the loop ended without `break`. Then every condition passed. |
| 457 | `            out.append(r)` | Adds the record to the result. |
| 458 | `    return out` | Returns the list. The order of the records is kept. |
| 461 | `def rng(rs, key='GBps'):` | Starts the function `rng`. It summarises a list of records, by default over the key `GBps`. The result for one kernel is a range, not a mean. |
| 462 | `    """min, max, median, number of intervals and number of processes of a list of records."""` | Comment: the function returns the minimum, the maximum, the median, the number of intervals and the number of processes of a list of records. |
| 463 | `    v = [r[key] for r in rs]` | `v`: the value of each record for the key. Each interval counts once. |
| 464 | `    if not v:` | Tests for an empty list. |
| 465 | `        return None` | An empty list gives `None`. |
| 466 | `    return dict(lo=min(v), hi=max(v), med=statistics.median(v), n=len(v), procs=len({r['proc_key'] for r in rs}),` | Returns the summary. `lo`, `hi`: the lowest and the highest value. `med`: the median. For an even number of values it is the mean of the two middle values. `n`: the number of records, which is the number of intervals. `procs`: the number of different processes (key `proc_key`). No value is left out and nothing is rounded. The function forms no mean over all values. The facts sheet prints a result as `lo` to `hi` with these counts [Ref4]. |
| 467 | `                sessions=len({r['session'] for r in rs if r['session'] is not None}),` | Continues the summary of line 466. `sessions`: the number of different values of the key `session`. A record without a value is not counted. In a control I record the key holds the number of the control process, and `rng` counts it like a session. |
| 468 | `                boots=len({r['boot'] for r in rs}))` | Ends the summary of line 466. `boots`: the number of different boots. |
| 471 | `def overlap(a, b):` | Starts the function `overlap`. It says whether two ranges of `rng` share at least one value. |
| 472 | `    return a['lo'] <= b['hi'] and b['lo'] <= a['hi']` | True when the lower end of each range is not above the upper end of the other range. Two ranges that only touch at one end count as overlapping. The values are compared without rounding. The function `compare` of `facts_text.py` sets the wording `no difference seen` when the 7200 MT/s range and the 8000 MT/s range overlap. It sets `differs between the 8000 MT/s boot and the 7200 MT/s boot` when they do not [Ref4]. |
| 475 | `def gap(a, b):` | Starts the function `gap`. It gives the distance between the nearest ends of two ranges in GB/s. |
| 476 | `    """Distance between the nearest ends of two ranges, GB/s. Positive: a is above b. Zero: they overlap."""` | Comment: the distance between the nearest ends of two ranges, in GB/s. Positive: `a` is above `b`. Zero: they overlap. |
| 477 | `    if a['lo'] > b['hi']:` | Case 1: the range `a` lies fully above the range `b`. |
| 478 | `        return a['lo'] - b['hi']` | Returns the lower end of `a` minus the upper end of `b`. The value is positive. |
| 479 | `    if a['hi'] < b['lo']:` | Case 2: the range `a` lies fully below the range `b`. |
| 480 | `        return a['hi'] - b['lo']` | Returns the upper end of `a` minus the lower end of `b`. The value is negative. |
| 481 | `    return 0.0` | In every other case the ranges overlap, and the distance is 0.0 GB/s. |
| 484 | `def width_pct(a):` | Starts the function `width_pct`. It gives the width of a range in percent of its lower end. |
| 485 | `    return (a['hi'] - a['lo']) / a['lo'] * 100` | Returns `(hi - lo) / lo * 100`. The function `compare` of `facts_text.py` calls it for the 8000 MT/s range [Ref4]. |

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
