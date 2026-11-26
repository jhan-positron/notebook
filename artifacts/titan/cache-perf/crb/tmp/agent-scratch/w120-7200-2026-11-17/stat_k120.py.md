# `stat_k120.py` explained

- Source file: `stat_k120.py` in this folder (Python script, 120 lines, 6042 bytes).
- sha256 of the source when this page was built: `aedf016b230fa5df989b05d3cd7b69dddee6cabada5c441c1afaf7f5466437b1`.
- Role in the whole-chip test: Quick statistics tool for part A: reads threads120.csv, reports rates per kernel and binary.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The script reads the file `threads120.csv` of one or more part A result folders. For each pair of kernel and binary it prints the number of timed intervals and the lowest, the median and the highest `aggregate_GBps`, which is the rate that the benchmark binary printed for an interval.

<details>
<summary>Words used here</summary>

- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **write, copy, asmwrite, asmcopy**: the four other kernels of bw_old and bw_new. `write` fills a buffer. `copy` copies one buffer to a second buffer. `asmwrite` and `asmcopy` are hand-written loops for the same two jobs. They are not read kernels.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Rerun**: the read test of 2026-11-17 with 120 threads, run after the memory speed was lowered to 7200 MT/s (million transfers per second). Part A is one of its parts.
- **GB, GB/s**: 1 GB is 1e9 bytes. Every rate is in GB/s.
- **threads120.csv**: the result file of part A. For each benchmark process, ra.sh appends one header line and then the output of the process.
- **ra.sh**: the script that runs part A. It starts one process per binary and kernel, in two rounds.
- **Header line**: a line that starts with `-- binary`. ra.sh writes it directly before it starts a process. It names the binary, the kernel, the thread count, the CPU list, the buffer size, the round, the load and the UTC time.
- **Interval line**: a csv line that the benchmark binary prints for one timed interval. Its 10 fields are: kernel, threads, bytes_per_thread, rep, total_bytes, elapsed_s, aggregate_GBps, per_thread_min_GBps, per_thread_max_GBps, per_thread_avg_GBps. The field elapsed_s holds the longest elapsed time of one thread [Ref1].
- **aggregate_GBps**: field 7 of an interval line: the bytes of all threads, divided by the longest elapsed time of one thread, divided by 1e9.
- **per_thread_min_GBps, per_thread_max_GBps, per_thread_avg_GBps**: fields 8, 9 and 10 of an interval line. Fields 8 and 9 are the lowest and the highest rate of one thread in the interval. Field 10 is the mean of the rates of all threads. The rate of a thread is its bytes divided by its own elapsed time, divided by 1e9 [Ref1].
- **Pass count**: `total_bytes` divided by `bytes_per_thread` of an interval line, rounded down. For the kernels `read`, `write`, `asmread` and `asmwrite` this is the number of buffer passes that all 120 threads together completed in the interval [Ref1]. For `copy` and `asmcopy` the binary counts read plus written bytes, as the `#` comment line of each process says. So the same division gives 2 x the number of buffer passes for these two kernels.
- **Load**: the 1-minute load average of Linux (the average number of tasks that are runnable or wait for disk input and output). ra.sh reads it directly before it starts a process and writes it into the header line.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Pool**: the intervals of several folders taken together as one group.
- **Median**: the middle value of a sorted list. For an even number of values Python takes the mean of the two middle values.
- **build_facts.py, facts_data.py, facts sheet**: the facts sheet is the file FACTS.md with its data file facts.json. It is the detailed record of the rerun. build_facts.py writes both from the raw result files and uses the parsers of facts_data.py.
- **Report page**: the file `whole-chip-rerun-7200.html`. The script make_report.py writes it from facts.json.
- **est.**: estimated, not measured directly.

</details>

## Main flow

1. Read the arguments: result folders, `--pool` with optional folders, and `--json` (lines 90-94).
2. Build the list of all folders (each one once) and the list of the folders to pool (lines 95-100).
3. `load` reads `threads120.csv` of each folder. It returns one record per process (one header line) with one entry per interval line: `aggregate_GBps`, the per-thread minimum and maximum, and the pass count (lines 24-44).
4. `rows_of` groups the processes by the pair (kernel, binary). For each group it computes `n`, `min`, `median` and `max` of `aggregate_GBps` over all intervals of the group. It runs once per folder and once more for the pool (lines 47-67).
5. Print the rows as text with `print_text`, or as one JSON list with `--json` (lines 107-113).
6. End with an error message and exit status 1 when a process has a header line and no interval line (lines 114-116).

## Behavior a reader must know

- Rate formula: this script computes no rate. It reads field 7 of an interval line, `aggregate_GBps`, as the benchmark binary printed it (2 decimals). bandwidth.c computes that value as the bytes of all threads, divided by the longest elapsed time of one thread, divided by 1e9 [Ref1]. Each thread measures its own elapsed time. It reads the clock once before its first timed pass and again after each pass over its 256 MiB buffer. The elapsed time runs from the first read to the last read [Ref1]. The old source bandwidth.orig.c does the same [Ref2].
- stat_bwx.py, the tool for the csv files of the runner bwx12, uses another formula: the sum over the threads of bytes / own elapsed time / 1e9. No thread has an elapsed time above the longest one. So for one interval that sum cannot be lower than `aggregate_GBps` (before rounding). Part A uses the whole-pass stop, and its threads have different elapsed times. In the 36 `read` intervals of the three part A folders of the rerun the sum is about 1 % to 4 % higher than `aggregate_GBps` (est.: 120 x the column `per_thread_avg_GBps`, which is rounded to 0.01 GB/s) [Ref4].
- Lines used: every header line (binary, kernel, round, load, UTC time) and every interval line (field 4, `rep`, is a number). Of an interval line the script reads fields 1, 3, 4, 5, 7, 8 and 9. It does not read field 2 (`threads`), field 6 (`elapsed_s`) or field 10 (`per_thread_avg_GBps`). Lines not used: the `#` comment line, the line of column names and the `best` line of each process.
- No interval is left out, and no kernel is treated specially. A part A file also holds processes of the kernels `write`, `copy`, `asmread`, `asmwrite` and `asmcopy` [Ref3]. Each pair of kernel and binary gets its own row.
- The old read kernel is the row with kernel `read` and binary `bw_old`. The new read kernel is the row with kernel `read` and binary `bw_new`. The script does not compute the difference between the two rows.
- In one part A folder each pair has 2 processes (round 1 and round 2) with 3 intervals each, so `n` is 6 [Ref3]. The statistics do not keep the rounds apart. The lines per process show each round.
- The script does not check the thread count, the CPU list or the buffer size. The pattern `HDR` reads these fields of the header line, and `load` does not keep them.
- Rounding: `min`, `max` and every interval value are the numbers of the file. `median` is rounded to 3 decimals in the row, and the text report prints it with 2 decimals. The median of an even number of values can have a 5 as its third decimal. The text report formats the binary floating-point number, and it can then print the lower 2-decimal value. Example: the 6 `asmread` intervals of `bw_new` in the first part A folder of the rerun have the median 328.455 GB/s, and the text report prints 328.45. The facts sheet rounds half up. So a median of the facts sheet can differ by 0.01 GB/s from the output of this tool [Ref6].
- Role in the final numbers: the facts sheet and the report page use the same rate for part A, the column `aggregate_GBps` [Ref6]. build_facts.py reads the files with the parser of facts_data.py and compares every interval with the output of `load` [Ref5]. The facts sheet records this check as passed for 333 interval lines, among them the 216 interval lines of the three part A folders of the rerun [Ref6].
- facts_data.py also uses the pattern `HDR` of this file [Ref5]. Neither build_facts.py nor facts_data.py calls `main`.

## Call sequence in the whole-chip test

- `main` (line 89): command-line use: folders, optional `--pool` and `--json`
  - `load` (line 24): once per folder: processes and intervals of `threads120.csv`
  - `rows_of` (line 47): once per folder and once for the pool: statistics per kernel and binary
  - `print_text` (line 70): once per group, when `--json` is not given
- `build_facts.py:run_checks`: second use: cross-check while the facts sheet is built
  - `load` (line 24): its intervals are compared with those of the facts_data.py parser
- `facts_data.py:read_k120`: uses the pattern `HDR` (line 21) to find header lines

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `load` | 24-44 | Reads `threads120.csv` of a folder. Returns one record per process with `aggregate_GBps`, per-thread minimum and maximum, and pass count of every interval. | - | - |
| `rows_of` | 47-67 | Groups processes by (kernel, binary). Computes n, min, median and max of `aggregate_GBps` over all intervals of each group. | - | - |
| `print_text` | 70-86 | Prints one group as text: a statistics line per kernel and binary, then one line per process with every interval. | - | - |
| `main` | 89-116 | Parses the arguments, loads every folder, builds the rows per folder and for the pool, prints text or JSON. | `load`, `rows_of`, `print_text` | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/stat_k120.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (120 lines, 6042 bytes, sha256 `aedf016b230fa5df989b05d3cd7b69dddee6cabada5c441c1afaf7f5466437b1`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Usage text, imports and the pattern `HDR` (lines 1 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""stat_k120.py - statistics of threads120.csv, the 120-thread file of run_kernels.sh and ra.sh.` | Starts the usage text of the tool (a Python docstring). `main` shows it as the help text (line 90). This line names the task: statistics of `threads120.csv`, the file of the 120-thread processes that `run_kernels.sh` and `ra.sh` write. |
| 4 | `Usage: stat_k120.py [--json] [FOLDER ...] [--pool [FOLDER ...]]` | Usage text: the form of the call. It takes any number of folders, the option `--pool` with any number of folders after it, and the option `--json`. |
| 6 | `Each FOLDER holds one threads120.csv. In that file one process is one "-- binary ..." header` | Usage text: each folder holds one `threads120.csv`. In that file one process is one header line that starts with `-- binary`. The sentence goes on in line 7. |
| 7 | `line, then one csv line per timed interval (rep 0, 1, 2), then one "best" line (not used here).` | Usage text, continued: then one csv line per timed interval (`rep` 0, 1 and 2), then one `best` line, which this tool does not use. The benchmark binary also prints one comment line and one line of column names before the interval lines. |
| 9 | `Output, per folder and per (kernel, binary):` | Usage text: the output is given per folder and per pair of kernel and binary. |
| 10 | `  n, min, median and max of aggregate_GBps over the intervals (GB = 1e9 bytes),` | Usage text: `n` (the number of intervals), the minimum, the median and the maximum of the column `aggregate_GBps` over the intervals. GB means 1e9 bytes. |
| 11 | `  every interval in file order with its round and its per-thread min and max (GB/s),` | Usage text: every interval in file order, with its round and with the lowest and the highest rate of one thread, in GB/s. |
| 12 | `  and the load value of the header lines (min and max per folder).` | Usage text: the load value of the header lines, as the minimum and the maximum per folder. |
| 13 | `--pool F1 F2 ..  also prints the same statistics over the intervals of F1, F2, .. taken together.` | Usage text: `--pool` with folders also prints the same statistics over the intervals of these folders taken together. |
| 14 | `                 Each of these folders is still printed alone first.` | Usage text, continued: each of these folders is still printed alone first. |
| 15 | `--pool           (no folder after it) pools all folders of the command line.` | Usage text: `--pool` without a folder after it pools all folders of the command line. |
| 16 | `--json           prints the rows as a JSON list instead of text.` | Usage text: `--json` prints the rows as one JSON list in place of the text report. |
| 17 | `The parser follows summarize.py of results/kernels-20261113T181222Z.` | Usage text: by this line the parser follows the script `summarize.py` of the result folder `kernels-20261113T181222Z`. |
| 18 | `"""` | Ends the usage text. |
| 19 | `import argparse, json, os, re, statistics, sys` | Loads six modules of the Python standard library. `argparse` reads the command line. `json` writes JSON. `os` builds file paths. `re` holds regular expressions. `statistics` computes the median. `sys` gives the standard output and ends the script. |
| 21 | `HDR = re.compile(r'-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d+) load (\S+)(?: utc (\S+))?')` | `HDR`: a compiled pattern for the header line that starts each process in `threads120.csv`. Its 8 groups hold the binary, the kernel, the thread count, the CPU list, the buffer size, the round, the load value and, when the line has one, the UTC time. `\S+` stands for a run of characters without a space, and `\d+` for a run of digits. The part with `utc` is optional, so a header line without it also fits. `ra.sh` (the script of part A) writes one header line directly before it starts a benchmark process [Ref3]. |

### Function `load`: read the processes of one folder (lines 24 to 46)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `def load(folder):` | Starts the function `load`. It reads the file `threads120.csv` of one folder. |
| 25 | `    """Return the processes of folder/threads120.csv in file order, each with its intervals."""` | Description of the function: it returns the processes of the file in file order, each with its intervals. |
| 26 | `    fn = os.path.join(folder, 'threads120.csv')` | `fn`: the path of the file `threads120.csv` in the folder. |
| 27 | `    procs, cur = [], None` | `procs`: the list of the processes found so far. `cur`: the process whose interval lines are read now. It is `None` before the first header line. |
| 28 | `    with open(fn) as f:` | Opens the file for reading. Python closes it when the block of this line ends. |
| 29 | `        for ln, l in enumerate(f, 1):` | Reads the file line by line. `ln` is the line number, counted from 1. `l` is the text of the line. |
| 30 | `            l = l.strip()` | `strip` removes spaces and the line end from both ends of the line. |
| 31 | `            m = HDR.match(l)` | Tests the line against the pattern `HDR` (line 21), from the start of the line. `m` is `None` when the line does not fit. |
| 32 | `            if m:` | A line that fits `HDR` starts a new process record. |
| 33 | `                cur = dict(folder=folder, binary=m[1], kernel=m[2], round=int(m[6]), load=float(m[7]), utc=m[8], iv=[])` | The record keeps the folder, the binary (group 1), the kernel (group 2), the round as a whole number (group 6), the load as a number (group 7), the UTC time (group 8) and an empty list `iv` for the intervals. The thread count, the CPU list and the buffer size of the header line (groups 3 to 5) are not kept. |
| 34 | `                procs.append(cur)` | Adds the record to `procs`. |
| 35 | `                continue` | Goes on with the next line of the file. |
| 36 | `            p = l.split(',')` | Every other line is split at the commas into the list `p`. Python counts from 0, so `p[3]` is field 4, `rep`. |
| 37 | `            if len(p) > 8 and p[3].isdigit():` | The line is an interval line when it has more than 8 fields and field 4 holds digits only. This test drops the `#` comment line (it has no comma), the line of column names (field 4 is the word `rep`) and the `best` line (field 4 is `best`). |
| 38 | `                if cur is None or p[0] != cur['kernel']:` | An interval line must come after a header line, and its first field must be the kernel of that header line. |
| 39 | `                    sys.exit(f'{fn}:{ln}: interval line does not belong to the header line before it')` | If not, the script stops and names the file and the line. `sys.exit` with a text prints the text to the error output and ends the script with exit status 1. |
| 40 | `                # aggregate_GBps, per_thread_min_GBps, per_thread_max_GBps` | Comment: the names of the first three values that line 41 keeps. The comment does not name the fourth value, the pass count. |
| 41 | `                cur['iv'].append((float(p[6]), float(p[7]), float(p[8]), int(p[4]) // int(p[2])))` | Kept per interval: `p[6]` = `aggregate_GBps`, `p[7]` = `per_thread_min_GBps`, `p[8]` = `per_thread_max_GBps`. The last two are the lowest and the highest rate of one thread in the interval. The rate of a thread is its bytes divided by its own elapsed time [Ref1]. Also kept: the pass count `p[4] // p[2]`. It is `total_bytes` divided by `bytes_per_thread`, rounded down. Not read: `p[1]` (`threads`), `p[5]` (`elapsed_s`) and `p[9]` (`per_thread_avg_GBps`). No rate is computed here. `aggregate_GBps` is the number that the binary printed: the bytes of all threads, divided by the longest elapsed time of one thread, divided by 1e9 [Ref1]. |
| 42 | `    if not procs:` | Tests whether the file held no header line. |
| 43 | `        sys.exit(f'{fn}: no "-- binary" header line')` | In that case the script stops with a message that names the file. |
| 44 | `    return procs` | Otherwise `load` returns the processes in file order. |

### Function `rows_of`: statistics per kernel and binary (lines 47 to 69)

| Line | Source | Explanation |
|---:|---|---|
| 47 | `def rows_of(label, procs, folders=None):` | Starts the function `rows_of`. It computes the statistics of a list of processes, per pair of kernel and binary. `label` becomes the folder name in each row. `folders` is given only for a pooled group. |
| 48 | `    """One row per (kernel, binary), in the order of first appearance in procs."""` | Description of the function: one row per pair of kernel and binary, in the order in which each pair first appears in `procs`. |
| 49 | `    loads = [p['load'] for p in procs]` | `loads` holds the load of every process that was passed in. |
| 50 | `    cells = {}` | `cells`: an empty dictionary for the groups of processes. |
| 51 | `    for p in procs:` | Loop over the processes. |
| 52 | `        cells.setdefault((p['kernel'], p['binary']), []).append(p)` | Groups the processes by the pair (kernel, binary). `setdefault` creates the list of a pair at its first use. So the pairs keep the order in which they first appear. The old read kernel is the group (`read`, `bw_old`), and the new read kernel is the group (`read`, `bw_new`). |
| 53 | `    rows = []` | `rows`: the list of the result rows, empty at first. |
| 54 | `    for (kernel, binary), ps in cells.items():` | Loop over the groups. `ps` holds the processes of one pair. |
| 55 | `        iv = [(p['round'], a, lo, hi, n) for p in ps for a, lo, hi, n in p['iv']]` | `iv` lists every interval of the group: the intervals of its first process, then those of the next process. Each entry holds the round, `aggregate_GBps`, the per-thread minimum, the per-thread maximum and the pass count. No interval is left out. |
| 56 | `        v = [x[1] for x in iv]` | `v` holds the `aggregate_GBps` values of these intervals. |
| 57 | `        row = dict(folder=label, kernel=kernel, binary=binary, n=len(v),` | Starts one result row for the group, computed over `v`. It holds the label, the kernel and the binary. `n`: the number of intervals. |
| 58 | `                   min=min(v) if v else None, median=round(statistics.median(v), 3) if v else None,` | `min`: the lowest `aggregate_GBps`. `median`: the middle value. For an even `n` it is the mean of the two middle values. It is rounded to 3 decimals (0.001 GB/s). Both are `None` when the group has no interval. |
| 59 | `                   max=max(v) if v else None, values=v, rounds=[x[0] for x in iv],` | `max`: the highest `aggregate_GBps`, or `None` without an interval. `values` and `rounds`: one entry per interval, in file order. |
| 60 | `                   per_thread_min=[x[2] for x in iv], per_thread_max=[x[3] for x in iv], passes=[x[4] for x in iv],` | `per_thread_min`, `per_thread_max` and `passes`: also one entry per interval, in file order. |
| 61 | `                   processes=len(ps), loads=[p['load'] for p in ps],` | `processes` and `loads`: the number of processes of the group and their load values. |
| 62 | `                   folder_load_min=min(loads), folder_load_max=max(loads))` | `folder_load_min` and `folder_load_max`: the lowest and the highest load over all processes that were passed in, not only those of this group. The line ends the `dict` call of line 57. |
| 63 | `        if folders:` | Tests whether a list of folders was passed in. This is the case for a pooled group. |
| 64 | `            row['folders'] = folders` | A pooled row also names its folders. |
| 65 | `        row['_procs'] = ps  # for the text output only; removed before the JSON output` | `_procs` keeps the process records for the text report. `main` removes this field before the JSON output (line 108). |
| 66 | `        rows.append(row)` | Adds the row to `rows`. |
| 67 | `    return rows` | Returns the rows. |

### Function `print_text`: text report of one group (lines 70 to 88)

| Line | Source | Explanation |
|---:|---|---|
| 70 | `def print_text(title, rows, show_folder):` | Starts the function `print_text`. It prints the text report of one group of rows. |
| 71 | `    nproc = sum(r['processes'] for r in rows)` | `nproc`: the number of processes of all rows together. |
| 72 | `    per = sorted({len(p['iv']) for r in rows for p in r['_procs']})` | `per`: the different interval counts per process, as a sorted list. When every process has 3 intervals, the list holds the one value 3. |
| 73 | `    print(f'== {title}')` | Prints the title line. It starts with `==`. |
| 74 | `    print(f'   {nproc} processes, intervals per process: {per}, '` | Starts the summary line: the number of processes and the different interval counts per process. |
| 75 | `          f'load in the "-- binary" lines: min {rows[0]["folder_load_min"]:.2f} max {rows[0]["folder_load_max"]:.2f}')` | Continues the summary line of line 74: the lowest and the highest load, with 2 decimals. The load values are taken from the first row, and they are the same in every row of the group. |
| 76 | `    print('   aggregate_GBps per (kernel, binary); under it one line per process: aggregate (per-thread min-max), GB/s')` | Prints one line that describes the layout of the report. |
| 77 | `    for r in rows:` | Loop over the rows, one per pair of kernel and binary. |
| 78 | `        if r['n']:` | Tests whether the pair has at least one interval. |
| 79 | `            print(f'{r["kernel"]:9} {r["binary"]:7} n={r["n"]:<3} min {r["min"]:7.2f}  median {r["median"]:7.2f}  max {r["max"]:7.2f}')` | Prints one line for the pair: the kernel (padded to 9 characters), the binary (padded to 7 characters), `n`, then `min`, `median` and `max` with 2 decimals (0.01 GB/s). |
| 80 | `        else:` | The other case: the pair has no interval. |
| 81 | `            print(f'{r["kernel"]:9} {r["binary"]:7} n=0   NO INTERVAL')` | A pair without an interval prints `n=0` and `NO INTERVAL`. |
| 82 | `        for p in r['_procs']:` | Under it, one line per process of the pair. |
| 83 | `            where = os.path.basename(p['folder']) + ' ' if show_folder else ''` | `where`: in a pooled report the line starts with the folder name (the last part of the folder path). In the report of one folder it is empty. |
| 84 | `            ivs = ' \| '.join(f'{a:.2f} ({lo:.2f}-{hi:.2f}, {n} passes)' for a, lo, hi, n in p['iv']) or 'NO INTERVAL'` | `ivs`: for each interval the rate, then in parentheses the per-thread minimum, the per-thread maximum and the pass count. Rates have 2 decimals. A `\|` with a space on each side separates two intervals. A process without an interval gives `NO INTERVAL`. |
| 85 | `            print(f'    {where}round {p["round"]} load {p["load"]:6.2f} utc {p["utc"]} \| {ivs}')` | Prints the line of the process: the folder name in a pooled report, the round, the load with 2 decimals, the UTC time, then the intervals. |
| 86 | `    print()` | Prints an empty line after the group. |

### Function `main`: arguments, statistics, output (lines 89 to 120)

| Line | Source | Explanation |
|---:|---|---|
| 89 | `def main():` | Starts the function `main`. It reads the arguments, computes the statistics and prints them. |
| 90 | `    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)` | Creates the reader of the command line. The usage text of lines 2 to 18 is its help text. `RawDescriptionHelpFormatter` keeps the line breaks of that text. |
| 91 | `    ap.add_argument('folders', nargs='*', help='result folders, each with a threads120.csv')` | Argument `folders`: any number of folders (`nargs='*'`). |
| 92 | `    ap.add_argument('--pool', nargs='*', metavar='FOLDER', help='folders to pool (none named: all folders)')` | Option `--pool` with any number of folders after it. Without the option the value is `None`. With the option and no folder it is an empty list. |
| 93 | `    ap.add_argument('--json', action='store_true', help='print the rows as JSON')` | Option `--json`: a switch without a value. |
| 94 | `    a = ap.parse_args()` | Reads the arguments of the command line into `a`. |
| 95 | `    norm = lambda d: d.rstrip('/') or '/'` | `norm` removes `/` characters from the end of a folder name. A name that holds only `/` characters becomes `/`. |
| 96 | `    singles = list(dict.fromkeys(norm(d) for d in a.folders + (a.pool or [])))` | `singles` is the list of all folders named anywhere on the command line, each one once. The folders outside `--pool` come first, then the folders after `--pool`. `dict.fromkeys` drops repeats and keeps the order. |
| 97 | `    if not singles:` | Tests whether no folder was given. |
| 98 | `        ap.error('no folder given')` | Without a folder the script ends with a usage error. `ap.error` prints the usage line and the message, and it ends the script with exit status 2. |
| 99 | `    pool = [norm(d) for d in a.pool] or singles if a.pool is not None else []` | `pool` is the list of the folders to pool: the folders after `--pool`, or all folders when none follows `--pool`. Without `--pool` the list is empty. |
| 100 | `    pool = list(dict.fromkeys(pool))` | Drops repeated folders from `pool` and keeps the order. |
| 101 | `    procs = {d: load(d) for d in singles}` | Reads every folder once with `load` (line 24). `procs` maps each folder to its list of processes. |
| 102 | `    groups = [(d, rows_of(d, procs[d]), False) for d in singles]` | Builds one group of rows per folder with `rows_of` (line 47). A group holds the title (the folder), the rows and the flag `show_folder`, here `False`. |
| 103 | `    if pool:` | Tests whether a pool was asked for. |
| 104 | `        allp = [p for d in pool for p in procs[d]]` | `allp` joins the processes of the pool folders, in the order of the folders. |
| 105 | `        groups.append((f'pool of {len(pool)} folders: ' + ', '.join(os.path.basename(d) for d in pool),` | Adds one more group for the pool. Its title gives the number of the pooled folders and their names. |
| 106 | `                       rows_of('pool', allp, pool), True))` | Continues line 105: the rows of the pool, built with `rows_of` from the joined processes. These rows carry the folder label `pool`. The flag `True` makes the report print the folder name of each process. |
| 107 | `    if a.json:` | Tests whether `--json` was given. |
| 108 | `        out = [{k: v for k, v in r.items() if k != '_procs'} for _, rows, _ in groups for r in rows]` | With `--json`: `out` holds the rows of all groups as one list, each row without the field `_procs`. |
| 109 | `        json.dump(out, sys.stdout, indent=1)` | Prints the list as JSON on the standard output, indented by 1 space per level. |
| 110 | `        print()` | Ends the JSON text with a line end. |
| 111 | `    else:` | The other case: no `--json`. |
| 112 | `        for title, rows, show_folder in groups:` | Loop over the groups. |
| 113 | `            print_text(title, rows, show_folder)` | Prints each group with `print_text` (line 70). |
| 114 | `    empty = [(p['folder'], p['kernel'], p['binary'], p['round']) for d in singles for p in procs[d] if not p['iv']]` | After the output: `empty` lists every process that has a header line and no interval line. Each entry holds the folder, the kernel, the binary and the round. |
| 115 | `    if empty:` | Tests whether the list is not empty. |
| 116 | `        sys.exit(f'process without any interval line (folder, kernel, binary, round): {empty}')` | In that case the script prints the list as an error message and ends with exit status 1. |
| 119 | `if __name__ == '__main__':` | Runs `main` when the file is started as a script. When another script imports the file, `main` does not run. |
| 120 | `    main()` | The call of `main`. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: source of bw_new. Lines 471 to 479: the clock reads of a thread (`t0` before the first timed pass, `t1` after each check step) and its elapsed time `t1 - t0`. Lines 24 and 452 to 454: a check step is 1 pass when the buffer is larger than 8 MiB. Lines 418 to 444: the bytes that one pass counts (1 x the buffer size, and 2 x for `copy` and `asmcopy`). Lines 584 to 603: `aggregate_GBps` = total bytes / longest elapsed time / 1e9, printed with 2 decimals, and the per-thread minimum, maximum and average. The records of 2026-11-13 show two texts of `bandwidth.c`. This local text has the sha256 (a checksum) `f1985072...`. The script run_kernels.sh of the test of 2026-11-13 wrote a record file `probe.txt` at each start. The `probe.txt` of the start of 18:32:18 UTC holds this value in line 15 (folder `kernels-20261113T183218Z` of `/home/jhan/workspace/titan/cache-perf/crb/results`). That start built the binaries and timed nothing. The `probe.txt` of the timed run of 18:12:22 UTC holds another sha256 for `bandwidth.c` in line 15: `c1406e02...` (folder `kernels-20261113T181222Z`). All three `probe.txt` records of that day hold the same sha256 for the binary bw_new (`fd7c14df...`). ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`: source of bw_old. Lines 314 to 322 and 427 to 446: the same clock reads and the same formula.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: lines 39 to 48: the format of the header line, `--reps 3`, the 6 kernels, the 2 binaries and the 2 rounds.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: and the same file of the folders `k120-T72A2-20261117T221518Z` and `k120-T72A3-20261117T221827Z`: the 36 interval lines of kernel `read`, fields 7 and 10. Example: line 4 of the first file holds 467.83 GB/s and 3.99 GB/s. 120 x 3.99 = 478.8 GB/s (est.).
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 798 to 815: the cross-check. Line 806 calls `stat_k120.load`. `facts_data.py` of the same folder uses `stat_k120.HDR` in line 271.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: line 9: rates are rounded half up, and a median of an even number of values can differ by 0.01 GB/s from the output of stat_k120.py. Line 292, decision (i): the rate per interval of part A is the column aggregate_GBps. Line 235, check 23: the cross-check with stat_k120.py passed for 333 interval rows (the 3 part A folders of the rerun and 3 earlier part A runs). In `make_report.py` of the same folder the function `val` (lines 176 to 189) returns the same rate for a part A record.
