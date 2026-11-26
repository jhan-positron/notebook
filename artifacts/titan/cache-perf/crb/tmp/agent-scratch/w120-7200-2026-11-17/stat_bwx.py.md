# `stat_bwx.py` explained

- Source file: `stat_bwx.py` in this folder (Python script, 166 lines, 7517 bytes).
- sha256 of the source when this page was built: `97eea37202ac31b25a285030e82c0fb669598bc3a8f9117053bf993edfea900d`.
- Role in the whole-chip test: Quick statistics tool for bwx12 csv files: per-interval totals, statistics per kernel.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The script reads the csv files that the runner bwx12 wrote into one or more result folders. It computes the rate of each timed interval as the sum of the per-thread rates, and it prints per kernel the number of intervals and the lowest, the median and the highest rate.

<details>
<summary>Words used here</summary>

- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Rerun**: the read test of 2026-11-17 with 120 threads, run after the memory speed was lowered to 7200 MT/s (million transfers per second). Its parts are part A, part L, part C and control I.
- **GB, GB/s**: 1 GB is 1e9 bytes. Every rate is in GB/s.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **bwx csv file**: the output of one bwx12 process. rx.sh (the script that starts bwx12) writes it into the result folder as `a6456.csv` (part L, control I), `cfwd.csv` or `crev.csv` (part C).
- **total**: the rate of an interval in this tool: the sum over the threads of bytes / elapsed_s / 1e9, in GB/s.
- **I_agg**: the field `aggregate_GBps` of the I row: the bytes of all threads divided by the longest elapsed time of one thread. bwx12 computes and prints it.
- **elapsed_s**: field 8 of a T row: the time from the clock read of the thread before its first timed kernel call to its clock read after the last one, in seconds [Ref2].
- **late**: the flag that bwx12 writes into a T row when the thread started more than 100 us after the common start time.
- **min_ms, stop, thp**: three values of the header lines of a bwx csv file. `min_ms` is the length of a timed interval in ms that the command line asked for (6000 in the rerun). `stop` is the stop rule (`common` in the rerun). `thp=madvise` means that bwx12 asked Linux for transparent huge pages (2 MiB pages) for the buffers.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Pool**: the intervals of several folders taken together as one group.
- **Median**: the middle value of a sorted list. For an even number of values Python takes the mean of the two middle values.
- **build_facts.py, facts_data.py, facts sheet**: the facts sheet is the file FACTS.md with its data file facts.json. It is the detailed record of the rerun. build_facts.py writes both from the raw result files and uses the parsers of facts_data.py.
- **Report page**: the file `whole-chip-rerun-7200.html`. The script make_report.py writes it from facts.json.

</details>

## Main flow

1. Split the arguments into flags (`--json`, `--pool`) and folders (lines 126-129).
2. For each folder, `interval_rows` reads every `*.csv` file in the order of the file names with `read_csv` (lines 61-65).
3. `read_csv` keeps per T row the CPU, the rate `bytes / elapsed_s / 1e9` and the flag. Per I row it keeps the printed `aggregate_GBps` (lines 38-58).
4. `interval_rows` builds one row per interval (round, position, kernel): `total` = the sum of the thread rates, the same sum per mesh, `I_agg`, and the test `is_64_56` (lines 66-80).
5. `summarize` groups the 64+56 rows by kernel and computes `n`, `min`, `median` and `max` of `total`. It runs once per folder, and once more over all folders with `--pool` (lines 84-99).
6. Print Part 1 (one line per interval) and Part 2 (one line per kernel) as text, or print everything as JSON with numbers rounded to 3 decimals (lines 141-162).

## Behavior a reader must know

- Rate formula: `total` of an interval = the sum over its T rows of `bytes / elapsed_s / 1e9`, in GB/s (GB = 1e9 bytes). The bytes of each thread are divided by the elapsed time of that same thread. `elapsed_s` is the time from the clock read of the thread before its first timed kernel call to its last clock read of the interval. bwx12 prints it with 6 decimals [Ref1] [Ref2].
- This is not the formula of the I row. There bwx12 prints `aggregate_GBps` = the bytes of all threads divided by the longest elapsed time of one thread [Ref1]. The script shows that value as `I_agg` and does not use it in the statistics. In the 74 intervals of the 9 bwx12 folders of the rerun (parts L and C, control I), `total` is 0.00 to 0.02 GB/s above `I_agg` [Ref4].
- stat_k120.py, the tool for part A, reports the `aggregate_GBps` that bandwidth.c prints. That value follows the formula of the I row. So a rate of part A and a rate of part L or part C come from two different formulas.
- Rows used: T rows (thread rates), I rows (`I_agg` only) and `#` lines (`min_ms`, `stop` and `thp`, shown only). Of a T row the script reads the fields `round`, `pos`, `kernel`, `cpu`, `bytes`, `elapsed_s` and `flags`. It does not read `tid` (the number of the thread), `t_sched_s`, `t_start_s` and `t_end_s` (the common start time, the start time and the end time of the thread) or `passes` (the bytes of the thread divided by the bytes of one buffer pass). Of an I row it reads `round`, `pos`, `kernel` and `aggregate_GBps`. Rows not used: P rows and C rows.
- Part 2 leaves out every interval that is not 64+56. In the 9 bwx12 folders of the rerun all 74 intervals are 64+56, so none is left out [Ref4].
- A T row with the flag `late` stays in `total`. The script only counts it in the column `flg`. In the 9 bwx12 folders of the rerun no T row carries a flag [Ref4].
- Part 2 groups by the kernel name only. It does not keep rounds, positions or files apart. A pool over folders with different kernel orders (`cfwd.csv` and `crev.csv` of part C) therefore mixes intervals that ran after different kernels [Ref3].
- The old read kernel is the row `oldread`. The new read kernel is the row `read`. Of the three bwx12 parts of the rerun (part L, part C and control I), only part C runs the kernel `read` [Ref3]. The script does not compute a difference between kernels.
- The script identifies an interval by round, position and kernel inside one csv file. If a file held two processes with the same kernel sequence, their T rows would form one interval with twice the threads, and the 64+56 test would reject it. Each csv file of the rerun holds one process [Ref3]. Each bwx12 folder of the rerun holds one csv file. So a Part 2 row of one folder is computed from 2 intervals of one process: round 0 and round 1 of the kernel [Ref4].
- Rounding: all sums and statistics use the unrounded thread rates. The text report prints `total`, `I_agg`, the statistics and the rates of single threads with 2 decimals. It prints the sum per mesh with 1 decimal. The JSON output rounds every number to 3 decimals.
- Role in the final numbers: for the bwx runners the facts sheet and the report page use the same formula as `total` [Ref6]. build_facts.py computes it with the parser of facts_data.py. It compares the intervals of 26 csv files from 20 folders with the output of `interval_rows` [Ref5]. These are the 9 csv files of the 9 bwx12 folders of the rerun and 17 csv files from 11 earlier folders of the runners bwx12 and bwx11. The 11 earlier folders hold 52 csv files, and the check does not compare the other 35. The facts sheet records this check as passed for 297 intervals, among them the 74 bwx12 intervals of the rerun [Ref6]. The check does not cover the csv files of the runner bwx [Ref5]. build_facts.py calls no other function of this file.

## Call sequence in the whole-chip test

- `main` (line 125): command-line use: folders, optional `--pool` and `--json`
  - `interval_rows` (line 61): once per folder: one row per interval
    - `read_csv` (line 38): once per csv file: thread rates and I row rates
    - `half` (line 34): mesh of each thread, for the sums per mesh
  - `summarize` (line 84): once per folder, once more over all folders with `--pool`
  - `rounded` (line 102): only with `--json`
  - `fmt_half` (line 112): text output: the two mesh columns of each interval line
  - `print_summary` (line 118): text output: Part 2 table per folder and pooled
- `build_facts.py:run_checks`: second use: cross-check while the facts sheet is built
  - `interval_rows` (line 61): totals, mesh sums, 64+56 test and flagged counts are compared

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `half` | 34-35 | Returns 0 for a CPU number below 64 (mesh 0) and 1 for every other CPU number (mesh 1). | - | - |
| `read_csv` | 38-58 | Parses one bwx csv file: header values, per-thread rate `bytes / elapsed_s / 1e9`, and the printed `aggregate_GBps` of each I row. | - | - |
| `interval_rows` | 61-81 | Builds one row per interval of a folder: `total` (sum of thread rates), sums per mesh, `I_agg`, flagged count, and the 64+56 test. | `read_csv`, `half` | - |
| `summarize` | 84-99 | Per kernel over the 64+56 intervals: n, min, median and max of `total`, and the totals in file order. | - | - |
| `rounded` | 102-109 | Rounds every floating-point number inside a value to 3 decimals, for the JSON output. | `rounded` | - |
| `fmt_half` | 112-115 | Formats one mesh column of a Part 1 line. | - | - |
| `print_summary` | 118-122 | Prints the Part 2 table: one line per kernel. | - | - |
| `main` | 125-162 | Parses flags and folders, builds rows and statistics per folder and pooled, prints text or JSON. | `interval_rows`, `summarize`, `rounded`, `fmt_half`, `print_summary` | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/stat_bwx.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (166 lines, 7517 bytes, sha256 `97eea37202ac31b25a285030e82c0fb669598bc3a8f9117053bf993edfea900d`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Usage text and imports (lines 1 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""stat_bwx.py [--json] [--pool] FOLDER...` | Starts the usage text (a Python docstring). The script prints it when the arguments are wrong (line 129). This line gives the form of the call: the options `--json` and `--pool`, then one or more folders. |
| 4 | `Reads the bwx csv files (*.csv) of each result folder.` | Usage text: the script reads the csv files of the bwx runners. These are all files of a result folder whose names end with `.csv`. |
| 6 | `Part 1, one row per interval (round, pos, kernel) of each csv file:` | Usage text: Part 1 of the output has one row per interval of each csv file. Round, position and kernel name an interval. |
| 7 | `  thr      number of T rows (threads)` | Usage text, column `thr`: the number of T rows of the interval. A T row holds one thread in one interval, so this is the number of threads. |
| 8 | `  total    sum over threads of bytes / elapsed_s / 1e9, in GB/s (GB = 1e9 bytes; the method of an.py)` | Usage text, column `total`: the rate of an interval in this tool. It is the sum over the threads of `bytes / elapsed_s / 1e9`, in GB/s. GB means 1e9 bytes. The line calls this the method of `an.py`. The script `an.py` of the folder `w120-2026-11-15` computes the same sum. |
| 9 | `  h0, h1   the same sum for the threads on CPUs 0-63 (h0) and on CPUs 64-127 (h1),` | Usage text, columns `h0` and `h1`: the same sum for the threads on the CPUs 0 to 63 (`h0`, mesh 0) and on the CPUs 64 to 127 (`h1`, mesh 1). |
| 10 | `           with the thread count and the lowest and highest per-thread rate` | Usage text, continued: each of the two columns also shows the thread count and the lowest and the highest rate of one thread. |
| 11 | `  I_agg    aggregate_GBps of the I row with the same round, pos and kernel` | Usage text, column `I_agg`: the value `aggregate_GBps` of the I row with the same round, position and kernel. It is the rate that the runner printed for the same interval. It is shown for comparison. |
| 12 | `           (the runner computes it as sum(bytes) / max(per-thread elapsed_s))` | Usage text, continued: the runner computes that value as the bytes of all threads divided by the longest elapsed time of one thread. |
| 13 | `  64+56    "yes" when the interval has 64 threads on 64 different CPUs of 0-63` | Usage text, column `64+56`: `yes` when the interval has 64 threads on 64 different CPUs of 0 to 63. The condition goes on in line 14. |
| 14 | `           and 56 threads on 56 different CPUs of 64-119, and no other thread` | Usage text, continued: and 56 threads on 56 different CPUs of 64 to 119, and no other thread. |
| 15 | `  flg      number of T rows whose flags field is not "-" (bwx writes "late" for a thread that` | Usage text, column `flg`: the number of T rows whose field `flags` is not `-`. The runner writes `late` for a thread that started late. The sentence goes on in line 16. |
| 16 | `           started more than 100 us after the common start); these rows are counted, not removed` | Usage text, continued: late means more than 100 us (microseconds) after the common start. These rows are counted, not removed. |
| 18 | `Part 2, per folder and kernel, over the "64+56" intervals only: n, min, median, max of total,` | Usage text: Part 2 gives `n`, the minimum, the median and the maximum of `total`, per folder and kernel. It uses only the intervals marked `64+56`. |
| 19 | `and the totals in file order (csv files sorted by name, rows in the order of the file).` | Usage text, continued: Part 2 also gives the totals in file order. The csv files are sorted by name, and the rows keep the order of the file. |
| 21 | `--pool  adds Part 2 once more over all folders together (folder name "POOLED").` | Usage text: `--pool` adds Part 2 once more over all folders together, under the folder name `POOLED`. |
| 22 | `--json  prints {"intervals": [...], "summary": [...]} instead of text.` | Usage text: `--json` prints one JSON object with the two lists `intervals` and `summary` in place of the text. |
| 23 | `A copy kernel counts read plus written bytes. No kernel is treated specially.` | Usage text: a copy kernel counts the bytes that it read plus the bytes that it wrote. The tool treats no kernel in a special way. |
| 24 | `"""` | Ends the usage text. |
| 25 | `import collections` | Loads the module `collections`. The script uses its `OrderedDict`, a dictionary that keeps the order in which its keys were added. |
| 26 | `import glob` | Loads the module `glob`, which finds files by a name pattern (line 64). |
| 27 | `import json` | Loads the module `json`, which writes the JSON output (line 142). |
| 28 | `import os` | Loads the module `os`, which works on file paths. |
| 29 | `import re` | Loads the module `re`, the regular expressions (line 47). |
| 30 | `import statistics` | Loads the module `statistics`, which computes the median (line 94). |
| 31 | `import sys` | Loads the module `sys`: the arguments of the command line, the standard output and the end of the script. All seven modules belong to the Python standard library. No other package is needed. |

### Function `half`: the mesh of a CPU (lines 34 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `def half(cpu):` | Starts the function `half`. It gives the mesh of a CPU. |
| 35 | `    return 0 if cpu < 64 else 1` | Returns 0 for a CPU number below 64 and 1 for every other CPU number. CPUs 0 to 63 sit on mesh 0, and CPUs 64 to 127 sit on mesh 1. |

### Function `read_csv`: read one bwx csv file (lines 38 to 60)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `def read_csv(path):` | Starts the function `read_csv`. It reads one csv file of a bwx runner. |
| 39 | `    """Return (header info, {(round, pos, kernel): [(cpu, GB/s, flags)]}, {(round, pos, kernel): aggregate_GBps})."""` | Description of the function: it returns three values. The first holds the header values. The second holds, per interval (round, position, kernel), the list of its threads: CPU, rate in GB/s and flags. The third holds, per interval, the value `aggregate_GBps` of the I row. |
| 40 | `    info = {}` | `info`: the header values, empty at first. |
| 41 | `    threads = collections.OrderedDict()` | `threads`: per interval the list of its threads. The `OrderedDict` keeps the intervals in the order of their first T row. |
| 42 | `    agg = {}` | `agg`: per interval the rate of the I row. |
| 43 | `    with open(path) as fh:` | Opens the file for reading. Python closes it when the block of this line ends. |
| 44 | `        for line in fh:` | Reads the file line by line. |
| 45 | `            if line.startswith('#'):` | A line that starts with `#` is a header or comment line of the runner. |
| 46 | `                for key in ('min_ms', 'stop', 'thp'):` | The script searches such a line for three names: `min_ms`, `stop` and `thp`. |
| 47 | `                    m = re.search(r'\b%s=(\S+)' % key, line)` | The pattern is the name at the start of a word (`\b`), then `=`, then a run of characters without a space (`\S+`). Its group holds that run, which is the value. |
| 48 | `                    if m and key not in info:` | The value is kept only when the pattern was found and no value of this name was kept before. So the script keeps the first value found for each of the three. |
| 49 | `                        info[key] = m.group(1).rstrip(';')` | Stores the value without a `;` at its end. These values are only shown in the report, and they change no rate. |
| 50 | `                continue` | Goes on with the next line of the file. |
| 51 | `            p = line.rstrip('\n').split(',')` | Every other line loses its line end and is split at the commas into the list `p`. Python counts from 0, so `p[5]` is field 6. |
| 52 | `            if p[0] == 'T':` | A row with `T` in the first field holds one thread in one interval. |
| 53 | `                # T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags` | Comment: the names of the fields of a T row, in their order. |
| 54 | `                threads.setdefault((p[1], p[2], p[3]), []).append((int(p[5]), float(p[6]) / float(p[7]) / 1e9, p[-1]))` | The key of the interval is (`p[1]`, `p[2]`, `p[3]`): round, position and kernel, kept as text. `p[5]` is the CPU that the thread is pinned to. `p[6]` is `bytes`, the number of bytes that the runner counted for the thread in the interval. For every kernel call the runner adds the size of the buffer part that the call covers. A copy kernel adds twice that size (read plus written bytes). A kernel that loads only some bytes of that part, such as `read_1pl` of `bwx12`, still adds the whole size. `p[7]` is `elapsed_s` in seconds: the time from the clock read of the thread before its first timed kernel call to its last clock read of the interval [Ref2]. The rate of the thread is `bytes / elapsed_s / 1e9`, in GB/s. `p[-1]` is the last field, `flags`: `-` or `late`. The fields `tid`, `t_sched_s`, `t_start_s`, `t_end_s` and `passes` are not read. `threads` keeps the intervals in the order of their first T row, and each interval keeps its threads in file order. |
| 55 | `            elif p[0] == 'I':` | A row with `I` in the first field is the line that the runner prints once per interval. |
| 56 | `                # I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps` | Comment: the names of the fields of an I row, in their order. |
| 57 | `                agg[(p[1], p[2], p[3])] = float(p[8])` | The script keeps only `p[8]`, the field `aggregate_GBps`: the bytes of all threads divided by the longest elapsed time of one thread [Ref1]. All other rows (P rows and C rows) are skipped. |
| 58 | `    return info, threads, agg` | The function returns the header values, the thread lists and the I row rates. |

### Function `interval_rows`: one row per interval of a folder (lines 61 to 83)

| Line | Source | Explanation |
|---:|---|---|
| 61 | `def interval_rows(folder):` | Starts the function `interval_rows`. It builds one row per interval of a folder. |
| 62 | `    rows = []` | `rows`: the result list, empty at first. |
| 63 | `    name = os.path.basename(os.path.normpath(folder))` | `name`: the last part of the folder path. `normpath` first removes a `/` at the end of the path. |
| 64 | `    for path in sorted(glob.glob(os.path.join(folder, '*.csv'))):` | The csv files of the folder are read in the order of their names. `glob` finds every file of the folder whose name ends with `.csv`, and `sorted` puts the paths in order. |
| 65 | `        info, threads, agg = read_csv(path)` | Reads one file with `read_csv` (line 38). |
| 66 | `        for (rnd, pos, kernel), tl in threads.items():` | Loop over the intervals of the file. `tl` is the list of the threads of one interval. |
| 67 | `            row = {'folder': name, 'file': os.path.basename(path), 'round': int(rnd), 'pos': int(pos),` | Starts the row of the interval. `folder`, `file`, `round` and `pos`, with `kernel` in line 68, say where the interval comes from. `folder` is the last part of the folder path. Round and position become whole numbers. |
| 68 | `                   'kernel': kernel, 'threads': len(tl), 'total': sum(t[1] for t in tl),` | `threads`: the number of T rows of the interval. `total`: the sum of the rates of all these T rows. This is the rate of the interval, in GB/s. |
| 69 | `                   'I_agg': agg.get((rnd, pos, kernel)), 'flagged': sum(t[2] != '-' for t in tl),` | `I_agg`: the `aggregate_GBps` of the I row with the same key, or no value (`None`) when the file has no such row. `flagged`: the number of T rows whose flag is not `-`. These rows stay in `total`. |
| 70 | `                   'min_ms': info.get('min_ms'), 'stop': info.get('stop'), 'thp': info.get('thp')}` | `min_ms`, `stop`, `thp`: the header values of the file, each `None` when the file does not hold it. The line ends the row that line 67 starts. |
| 71 | `            for h in (0, 1):` | The same per mesh: `h` is 0 for the CPUs below 64, then 1 for the CPUs from 64 up. |
| 72 | `                rates = [t[1] for t in tl if half(t[0]) == h]` | `rates`: the rates of the threads on this mesh. `half` (line 34) gives the mesh of each thread. |
| 73 | `                row['h%d_n' % h] = len(rates)` | `h0_n` or `h1_n`: the number of threads on the mesh. |
| 74 | `                row['h%d_sum' % h] = sum(rates)` | `h0_sum` or `h1_sum`: the sum of their rates, in GB/s. |
| 75 | `                row['h%d_min' % h] = min(rates) if rates else None` | `h0_min` or `h1_min`: the lowest rate of one thread. It is `None` for a mesh without a thread. |
| 76 | `                row['h%d_max' % h] = max(rates) if rates else None` | `h0_max` or `h1_max`: the highest rate of one thread. It is `None` for a mesh without a thread. |
| 77 | `            cpus = [t[0] for t in tl]` | `cpus`: the CPU numbers of all threads of the interval. |
| 78 | `            row['is_64_56'] = (row['h0_n'] == 64 and row['h1_n'] == 56 and max(cpus) <= 119` | `is_64_56` is true when four tests hold. This line holds three of them: 64 threads on CPUs below 64, 56 threads on CPUs from 64 up, and no CPU number above 119. |
| 79 | `                               and len(set(cpus)) == 120)` | Continues line 78: the fourth test, 120 different CPU numbers. Together the tests describe the whole-chip layout of the test: one thread on each of the CPUs 0 to 119. `summarize` uses only the intervals that pass. |
| 80 | `            rows.append(row)` | Adds the row to `rows`. |
| 81 | `    return rows` | Returns the rows of all csv files of the folder. |

### Function `summarize`: statistics per kernel (lines 84 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 84 | `def summarize(rows, folder_name):` | Starts the function `summarize`. It computes the statistics per kernel. `folder_name` becomes the folder name in each result row. |
| 85 | `    """Per kernel over the 64+56 intervals of rows: n, min, median, max and the totals in file order."""` | Description of the function: per kernel, over the 64+56 intervals of `rows`, it gives `n`, the minimum, the median, the maximum and the totals in file order. |
| 86 | `    by_kernel = collections.OrderedDict()` | `by_kernel`: the groups of interval rows. The `OrderedDict` keeps the kernels in the order in which each first appears. |
| 87 | `    for r in rows:` | Loop over the interval rows. |
| 88 | `        if r['is_64_56']:` | Keeps only the rows with `is_64_56` true. |
| 89 | `            by_kernel.setdefault(r['kernel'], []).append(r)` | Groups them by the kernel name alone. Round, position and file are not part of the group. So all intervals of one kernel in `rows` form one group. It does not matter which kernel ran before them. |
| 90 | `    out = []` | `out`: the result list, empty at first. |
| 91 | `    for kernel, rs in by_kernel.items():` | Loop over the kernels. `rs` holds the interval rows of one kernel. |
| 92 | `        v = [r['total'] for r in rs]` | `v`: the `total` values of the group, in file order. |
| 93 | `        out.append({'folder': folder_name, 'kernel': kernel, 'n': len(v), 'min': min(v),` | Starts one result row per kernel, computed over `v`. `n`: the number of intervals. `min`: the lowest total. |
| 94 | `                    'median': statistics.median(v), 'max': max(v), 'values': v,` | `median`: the middle value. For an even `n` it is the mean of the two middle values. It is not rounded here. `max`: the highest total. `values`: the totals in file order. |
| 95 | `                    'files': sorted(set(r['file'] for r in rs)), 'flagged': sum(r['flagged'] for r in rs),` | `files`: the different file names of these intervals, sorted. `flagged`: the sum of the flagged T rows of these intervals. |
| 96 | `                    'min_ms': sorted(set(str(r['min_ms']) for r in rs)),` | `min_ms`: the different `min_ms` header values of these intervals, as a sorted list of texts. |
| 97 | `                    'stop': sorted(set(str(r['stop']) for r in rs)),` | `stop`: the different `stop` header values, in the same form. |
| 98 | `                    'thp': sorted(set(str(r['thp']) for r in rs))})` | `thp`: the different `thp` header values, in the same form. The line ends the row that line 93 starts. |
| 99 | `    return out` | Returns the result rows. |

### Function `rounded`: 3 decimals for the JSON output (lines 102 to 111)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `def rounded(obj):` | Starts the function `rounded`. It returns a value with every floating-point number in it rounded to 3 decimals (0.001 GB/s for a rate). Only the JSON output uses this function (line 142). |
| 103 | `    if isinstance(obj, float):` | Case 1: the value is a floating-point number. |
| 104 | `        return round(obj, 3)` | It is rounded to 3 decimals. |
| 105 | `    if isinstance(obj, dict):` | Case 2: the value is a dictionary. |
| 106 | `        return {k: rounded(v) for k, v in obj.items()}` | The result is a new dictionary with the same keys. Each value goes through `rounded`. |
| 107 | `    if isinstance(obj, list):` | Case 3: the value is a list. |
| 108 | `        return [rounded(v) for v in obj]` | The result is a new list. Each element goes through `rounded`. |
| 109 | `    return obj` | Every other value is returned unchanged, for example a text, a whole number or `None`. |

### Function `fmt_half`: text of one mesh column (lines 112 to 117)

| Line | Source | Explanation |
|---:|---|---|
| 112 | `def fmt_half(row, h):` | Starts the function `fmt_half`. It builds the text of one mesh in a Part 1 line. |
| 113 | `    if not row['h%d_n' % h]:` | Tests whether the mesh has no thread. |
| 114 | `        return '%32s' % '-'` | A mesh without a thread prints `-`, at the right end of a field of 32 characters. |
| 115 | `    return '%7.1f n=%3d (%5.2f-%5.2f)' % (row['h%d_sum' % h], row['h%d_n' % h], row['h%d_min' % h], row['h%d_max' % h]) + ' ' * 4` | In the other case the text holds the sum of the rates with 1 decimal, the thread count, and in parentheses the lowest and the highest rate of one thread with 2 decimals. 4 spaces follow. |

### Function `print_summary`: the Part 2 table (lines 118 to 124)

| Line | Source | Explanation |
|---:|---|---|
| 118 | `def print_summary(summary):` | Starts the function `print_summary`. It prints the Part 2 table. |
| 119 | `    print('   %-16s %3s %8s %8s %8s  %-12s %3s %s' % ('kernel', 'n', 'min', 'median', 'max', 'min_ms', 'flg', 'totals in file order (GB/s)'))` | Prints the line of column names: `kernel`, `n`, `min`, `median`, `max`, `min_ms`, `flg` and `totals in file order (GB/s)`. |
| 120 | `    for s in summary:` | Loop over the result rows, one per kernel. |
| 121 | `        print('   %-16s %3d %8.2f %8.2f %8.2f  %-12s %3d %s' % (s['kernel'], s['n'], s['min'], s['median'], s['max'],` | Prints one line per kernel: the kernel name, `n`, then `min`, `median` and `max` with 2 decimals (GB/s). |
| 122 | `              '/'.join(s['min_ms']), s['flagged'], ' '.join('%.2f' % x for x in s['values'])))` | Continues line 121: the `min_ms` values joined with `/`, the number of flagged T rows, and every total in file order with 2 decimals. |

### Function `main`: arguments, statistics, output (lines 125 to 166)

| Line | Source | Explanation |
|---:|---|---|
| 125 | `def main(argv):` | Starts the function `main`. It reads the arguments, computes the statistics and prints them. `argv` holds the arguments of the command line. |
| 126 | `    flags = [a for a in argv if a.startswith('--')]` | Arguments that start with `--` are flags. |
| 127 | `    folders = [a for a in argv if not a.startswith('--')]` | All other arguments are folders. |
| 128 | `    if not folders or set(flags) - {'--json', '--pool'}:` | Tests for wrong arguments: no folder, or a flag other than `--json` and `--pool`. |
| 129 | `        sys.exit(__doc__)` | In that case the script prints the usage text (lines 2 to 24) to the error output and ends with exit status 1. |
| 130 | `    all_rows, all_summary = [], []` | `all_rows` and `all_summary`: the interval rows and the statistics of all folders together, empty at first. |
| 131 | `    per_folder = []` | `per_folder`: one pair of interval rows and statistics per folder, for the text output. |
| 132 | `    for folder in folders:` | Loop over the folders, in the order of the command line. |
| 133 | `        rows = interval_rows(folder)` | Builds the interval rows of the folder with `interval_rows` (line 61). |
| 134 | `        if not rows:` | Tests whether the folder gave no interval row. |
| 135 | `            sys.exit('no T rows in the csv files of ' + folder)` | The script stops with a message when the csv files of a folder hold no T row. The exit status is 1. |
| 136 | `        summary = summarize(rows, rows[0]['folder'])` | `summarize` (line 84) then builds the statistics of that folder. The folder name is taken from the first row. |
| 137 | `        per_folder.append((rows, summary))` | Keeps the rows and the statistics of the folder for the text output. |
| 138 | `        all_rows += rows` | Adds the rows of the folder to `all_rows`. |
| 139 | `        all_summary += summary` | Adds the statistics of the folder to `all_summary`. |
| 140 | `    pooled = summarize(all_rows, 'POOLED') if '--pool' in flags else []` | With `--pool`, `summarize` runs once more over the rows of all folders together, under the folder name `POOLED`. Without `--pool` the list `pooled` is empty. |
| 141 | `    if '--json' in flags:` | Tests whether `--json` was given. |
| 142 | `        json.dump(rounded({'intervals': all_rows, 'summary': all_summary + pooled}), sys.stdout, indent=1)` | With `--json`, prints one JSON object. `intervals` holds every interval row of every folder, also the rows that are not 64+56. `summary` holds the statistics per folder, then the pooled ones. `rounded` (line 102) rounds every number to 3 decimals first. |
| 143 | `        print()` | Ends the JSON text with a line end. |
| 144 | `        return` | Returns. The text output of lines 145 to 162 does not run in this case. |
| 145 | `    for rows, summary in per_folder:` | Text output: loop over the folders. |
| 146 | `        print('== ' + rows[0]['folder'])` | Prints a title line: `==` and the folder name. |
| 147 | `        last_file = None` | `last_file`: the csv file of the interval line printed before. It is `None` at the start. |
| 148 | `        for r in rows:` | Part 1: loop over the interval rows of the folder. |
| 149 | `            if r['file'] != last_file:` | Tests whether this row belongs to another csv file than the row before. |
| 150 | `                last_file = r['file']` | Remembers the new file. |
| 151 | `                print('-- %s  (header: stop=%s min_ms=%s thp=%s)' % (r['file'], r['stop'], r['min_ms'], r['thp']))` | Prints a line with the file name and its header values `stop`, `min_ms` and `thp`. |
| 152 | `                print('   %2s %3s %-16s %4s %8s  %-32s %-32s %8s %-5s %s' % ('rd', 'pos', 'kernel', 'thr', 'total',` | Prints the line of column names for the file. This line holds the first five: `rd` (round), `pos`, `kernel`, `thr` and `total`. |
| 153 | `                      'h0: CPUs 0-63, GB/s n (min-max)', 'h1: CPUs 64-127', 'I_agg', '64+56', 'flg'))` | Continues line 152: the names of the two mesh columns, then `I_agg`, `64+56` and `flg`. |
| 154 | `            print('   %2d %3d %-16s %4d %8.2f  %s %s %8s %-5s %d' % (r['round'], r['pos'], r['kernel'], r['threads'], r['total'],` | Prints one line per interval: round, position, kernel, thread count, and `total` with 2 decimals. |
| 155 | `                  fmt_half(r, 0), fmt_half(r, 1), '-' if r['I_agg'] is None else '%.2f' % r['I_agg'],` | Continues line 154: the two mesh columns from `fmt_half` (line 112), then `I_agg` with 2 decimals. `I_agg` is printed as `-` when the file has no I row for the interval. |
| 156 | `                  'yes' if r['is_64_56'] else 'no', r['flagged']))` | Continues line 154: `yes` or `no` for 64+56, and the flagged count. |
| 157 | `        print('-- 64+56 intervals of %s, total GB/s per kernel' % rows[0]['folder'])` | Part 2: prints its title line, with the folder name. |
| 158 | `        print_summary(summary)` | Prints the table of `print_summary` (line 118) for this folder. |
| 159 | `        print()` | Prints an empty line after the folder. |
| 160 | `    if pooled:` | Tests whether pooled statistics exist. The list `pooled` is empty without `--pool`. |
| 161 | `        print('== POOLED over %d folders, 64+56 intervals, total GB/s per kernel' % len(folders))` | Prints the title of the pooled table, with the number of folders. |
| 162 | `        print_summary(pooled)` | Prints the pooled table with `print_summary`, after the last folder. |
| 165 | `if __name__ == '__main__':` | Runs `main` with the command-line arguments when the file is started as a script. When another script imports the file, `main` does not run. |
| 166 | `    main(sys.argv[1:])` | The call of `main`. `sys.argv[1:]` holds the arguments without the name of the script. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 3025 and 3026: the field names of the I row and the T row. Lines 3066 to 3071: total bytes and longest elapsed time of an interval. Lines 3077 to 3084: the I row (`aggregate_GBps` = total bytes / longest elapsed time) and the T row (`elapsed_s` = end minus start of the thread, 6 decimals. Flag `late` or `-`).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 1688: the clock read before the first timed kernel call. Lines 1690 to 1701: with the common stop the thread reads the clock after each chunk of 2 MiB and stops at the first read that is not before the common deadline. Lines 1722 to 1725: start time, end time and the `late` flag (line 133: more than 100000 ns after the common start).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: lines 11 to 17: rx.sh reads its spec file (the input file of rx.sh: each line holds a tag and the arguments of one bwx12 process). It writes the output of each process to the csv file with the name of the tag. The spec files `like.spec`, `cfwd.spec` and `crev.spec` in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17` hold one line each, with the kernel sequences of part L and part C.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: and the csv files of the 8 other folders `w120-T72L*`, `w120-T72C*` and `w120-T72I*` of the same results folder. Output of `stat_bwx.py --json` on these 9 folders, run on 2026-11-21 for this explanation: 74 intervals, `is_64_56` true in all, `flagged` 0 in all, `total` minus `I_agg` from 0.000 to 0.018 GB/s. Example: the first `oldread` interval of this file has `total` 462.30 GB/s, and its I row in line 128 holds 462.29 GB/s.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 816 to 834: the cross-check. Line 820 calls `stat_bwx.interval_rows`. Lines 817 and 818: the check covers the 9 bwx12 folders of the rerun and the 11 folders of the list `rx_sets` (lines 207 to 221), which are earlier runs of the runners bwx12 and bwx11. Lines 821 to 823: of a folder of `rx_sets` the check takes only the csv files that the list names (17 files in total). The folders of the runner bwx (list `step_sets`, lines 258 to 267) are not in the check.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: line 292, decision (i): the rate per interval of the bwx runners is the sum over the threads of bytes / elapsed time. Line 236, check 24: the cross-check with stat_bwx.py passed for 297 intervals of 20 folders, among them the 9 folders of parts L, C and I with 74 intervals. In `make_report.py` of the same folder the function `val` (lines 176 to 189) computes the same sum for a record of a bwx runner.
