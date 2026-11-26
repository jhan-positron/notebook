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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env python3
  2  """stat_bwx.py [--json] [--pool] FOLDER...
  3
  4  Reads the bwx csv files (*.csv) of each result folder.
  5
  6  Part 1, one row per interval (round, pos, kernel) of each csv file:
  7    thr      number of T rows (threads)
  8    total    sum over threads of bytes / elapsed_s / 1e9, in GB/s (GB = 1e9 bytes; the method of an.py)
  9    h0, h1   the same sum for the threads on CPUs 0-63 (h0) and on CPUs 64-127 (h1),
 10             with the thread count and the lowest and highest per-thread rate
 11    I_agg    aggregate_GBps of the I row with the same round, pos and kernel
 12             (the runner computes it as sum(bytes) / max(per-thread elapsed_s))
 13    64+56    "yes" when the interval has 64 threads on 64 different CPUs of 0-63
 14             and 56 threads on 56 different CPUs of 64-119, and no other thread
 15    flg      number of T rows whose flags field is not "-" (bwx writes "late" for a thread that
 16             started more than 100 us after the common start); these rows are counted, not removed
 17
 18  Part 2, per folder and kernel, over the "64+56" intervals only: n, min, median, max of total,
 19  and the totals in file order (csv files sorted by name, rows in the order of the file).
 20
 21  --pool  adds Part 2 once more over all folders together (folder name "POOLED").
 22  --json  prints {"intervals": [...], "summary": [...]} instead of text.
 23  A copy kernel counts read plus written bytes. No kernel is treated specially.
 24  """</pre></td><td valign="top">Usage text. The script prints it when the arguments are wrong (line 129).<ul><li><code>total</code> is the rate of an interval in this tool: the sum over the threads of bytes / elapsed_s / 1e9, in GB/s.</li><li><code>I_agg</code> is the rate that the runner printed for the same interval. It is shown for comparison.</li><li>Part 2 uses only the intervals marked <code>64+56</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 25  import collections
 26  import glob
 27  import json
 28  import os
 29  import re
 30  import statistics
 31  import sys
 32
 33</pre></td><td valign="top">Modules of the Python standard library. No other package is needed.</td></tr>
<tr><td colspan="2"><b>Function <code>half</code>: the mesh of a CPU</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 34  def half(cpu):
 35      return 0 if cpu &lt; 64 else 1
 36
 37</pre></td><td valign="top">Return 0 for a CPU number below 64 and 1 for every other CPU number. CPUs 0-63 sit on mesh 0, and CPUs 64-127 sit on mesh 1.</td></tr>
<tr><td colspan="2"><b>Function <code>read_csv</code>: read one bwx csv file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 38  def read_csv(path):
 39      """Return (header info, {(round, pos, kernel): [(cpu, GB/s, flags)]}, {(round, pos, kernel): aggregate_GBps})."""
 40      info = {}
 41      threads = collections.OrderedDict()
 42      agg = {}
 43      with open(path) as fh:
 44          for line in fh:
 45              if line.startswith('#'):
 46                  for key in ('min_ms', 'stop', 'thp'):
 47                      m = re.search(r'\b%s=(\S+)' % key, line)
 48                      if m and key not in info:
 49                          info[key] = m.group(1).rstrip(';')
 50                  continue</pre></td><td valign="top">Read the file line by line. A line that starts with <code>#</code> is a header or comment line of the runner. The script searches it for <code>min_ms=</code>, <code>stop=</code> and <code>thp=</code>, and it keeps the first value found for each of the three. These values are only shown in the report, and they change no rate.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 51              p = line.rstrip('\n').split(',')
 52              if p[0] == 'T':
 53                  # T,round,pos,kernel,tid,cpu,bytes,elapsed_s,t_sched_s,t_start_s,t_end_s,passes,flags
 54                  threads.setdefault((p[1], p[2], p[3]), []).append((int(p[5]), float(p[6]) / float(p[7]) / 1e9, p[-1]))</pre></td><td valign="top"><ul><li>Every other line is split at the commas into the list <code>p</code>. Python counts from 0, so <code>p[5]</code> is field 6.</li><li>A row with <code>T</code> in the first field holds one thread in one interval. The key of the interval is (<code>p[1]</code>, <code>p[2]</code>, <code>p[3]</code>): round, position and kernel, kept as text.</li><li><code>p[5]</code> is the CPU that the thread is pinned to. <code>p[6]</code> is <code>bytes</code>, the number of bytes that the thread read in the interval (a copy kernel counts read plus written bytes). <code>p[7]</code> is <code>elapsed_s</code> in seconds: the time from the clock read of the thread before its first timed kernel call to its last clock read of the interval [Ref2].</li><li>The rate of the thread is <code>bytes / elapsed_s / 1e9</code>, in GB/s.</li><li><code>p[-1]</code> is the last field, <code>flags</code>: <code>-</code> or <code>late</code>. The fields <code>tid</code>, <code>t_sched_s</code>, <code>t_start_s</code>, <code>t_end_s</code> and <code>passes</code> are not read.</li><li><code>threads</code> keeps the intervals in the order of their first T row, and each interval keeps its threads in file order.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 55              elif p[0] == 'I':
 56                  # I,round,pos,kernel,bytes_per_thread,threads,total_bytes,max_elapsed_s,aggregate_GBps
 57                  agg[(p[1], p[2], p[3])] = float(p[8])
 58      return info, threads, agg
 59
 60</pre></td><td valign="top">A row with <code>I</code> in the first field is the line that the runner prints once per interval. The script keeps only <code>p[8]</code>, the field <code>aggregate_GBps</code>: the bytes of all threads divided by the longest elapsed time of one thread [Ref1]. All other rows (P rows and C rows) are skipped. The function returns the header values, the thread lists and the I row rates.</td></tr>
<tr><td colspan="2"><b>Function <code>interval_rows</code>: one row per interval of a folder</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 61  def interval_rows(folder):
 62      rows = []
 63      name = os.path.basename(os.path.normpath(folder))
 64      for path in sorted(glob.glob(os.path.join(folder, '*.csv'))):
 65          info, threads, agg = read_csv(path)
 66          for (rnd, pos, kernel), tl in threads.items():
 67              row = {'folder': name, 'file': os.path.basename(path), 'round': int(rnd), 'pos': int(pos),
 68                     'kernel': kernel, 'threads': len(tl), 'total': sum(t[1] for t in tl),
 69                     'I_agg': agg.get((rnd, pos, kernel)), 'flagged': sum(t[2] != '-' for t in tl),
 70                     'min_ms': info.get('min_ms'), 'stop': info.get('stop'), 'thp': info.get('thp')}</pre></td><td valign="top">The csv files of the folder are read with <code>read_csv</code> in the order of their names. For each interval the row holds:<ul><li><code>folder</code>, <code>file</code>, <code>round</code>, <code>pos</code>, <code>kernel</code>: where the interval comes from. <code>folder</code> is the last part of the folder path.</li><li><code>threads</code>: the number of T rows of the interval.</li><li><code>total</code>: the sum of the rates of all these T rows. This is the rate of the interval, in GB/s.</li><li><code>I_agg</code>: the <code>aggregate_GBps</code> of the I row with the same key, or no value when the file has no such row.</li><li><code>flagged</code>: the number of T rows whose flag is not <code>-</code>. These rows stay in <code>total</code>.</li><li><code>min_ms</code>, <code>stop</code>, <code>thp</code>: the header values of the file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 71              for h in (0, 1):
 72                  rates = [t[1] for t in tl if half(t[0]) == h]
 73                  row['h%d_n' % h] = len(rates)
 74                  row['h%d_sum' % h] = sum(rates)
 75                  row['h%d_min' % h] = min(rates) if rates else None
 76                  row['h%d_max' % h] = max(rates) if rates else None</pre></td><td valign="top">The same per mesh. <code>half</code> gives the mesh of each thread. For <code>h</code> = 0 (CPUs below 64) and <code>h</code> = 1 (CPUs from 64 up) the row gets the number of threads, the sum of their rates, and the lowest and the highest rate of one thread.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 77              cpus = [t[0] for t in tl]
 78              row['is_64_56'] = (row['h0_n'] == 64 and row['h1_n'] == 56 and max(cpus) &lt;= 119
 79                                 and len(set(cpus)) == 120)
 80              rows.append(row)
 81      return rows
 82
 83</pre></td><td valign="top"><code>is_64_56</code> is true when four tests hold: 64 threads on CPUs below 64, 56 threads on CPUs from 64 up, no CPU number above 119, and 120 different CPU numbers. This is the whole-chip layout of the test: one thread on each of the CPUs 0-119. <code>summarize</code> uses only the intervals that pass.</td></tr>
<tr><td colspan="2"><b>Function <code>summarize</code>: statistics per kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 84  def summarize(rows, folder_name):
 85      """Per kernel over the 64+56 intervals of rows: n, min, median, max and the totals in file order."""
 86      by_kernel = collections.OrderedDict()
 87      for r in rows:
 88          if r['is_64_56']:
 89              by_kernel.setdefault(r['kernel'], []).append(r)</pre></td><td valign="top">Keep only the rows with <code>is_64_56</code> true. Group them by the kernel name alone, in the order in which each kernel first appears. Round, position and file are not part of the group. So all intervals of one kernel in <code>rows</code> form one group, whichever kernel ran before them.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 90      out = []
 91      for kernel, rs in by_kernel.items():
 92          v = [r['total'] for r in rs]
 93          out.append({'folder': folder_name, 'kernel': kernel, 'n': len(v), 'min': min(v),
 94                      'median': statistics.median(v), 'max': max(v), 'values': v,
 95                      'files': sorted(set(r['file'] for r in rs)), 'flagged': sum(r['flagged'] for r in rs),
 96                      'min_ms': sorted(set(str(r['min_ms']) for r in rs)),
 97                      'stop': sorted(set(str(r['stop']) for r in rs)),
 98                      'thp': sorted(set(str(r['thp']) for r in rs))})
 99      return out
100
101</pre></td><td valign="top">One result row per kernel, computed over the <code>total</code> values <code>v</code> of its group:<ul><li><code>n</code>: the number of intervals. <code>min</code> and <code>max</code>: the lowest and the highest total.</li><li><code>median</code>: the middle value. For an even <code>n</code> it is the mean of the two middle values. It is not rounded here.</li><li><code>values</code>: the totals in file order.</li><li><code>flagged</code>: the sum of the flagged T rows of these intervals.</li><li><code>files</code>, <code>min_ms</code>, <code>stop</code>, <code>thp</code>: the different file names and header values of these intervals, each list sorted.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>rounded</code>: 3 decimals for the JSON output</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">102  def rounded(obj):
103      if isinstance(obj, float):
104          return round(obj, 3)
105      if isinstance(obj, dict):
106          return {k: rounded(v) for k, v in obj.items()}
107      if isinstance(obj, list):
108          return [rounded(v) for v in obj]
109      return obj
110
111</pre></td><td valign="top">Return a value with every floating-point number in it rounded to 3 decimals (0.001 GB/s for a rate). Lists and dictionaries are handled element by element. Only the JSON output uses this function (line 142).</td></tr>
<tr><td colspan="2"><b>Function <code>fmt_half</code>: text of one mesh column</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">112  def fmt_half(row, h):
113      if not row['h%d_n' % h]:
114          return '%32s' % '-'
115      return '%7.1f n=%3d (%5.2f-%5.2f)' % (row['h%d_sum' % h], row['h%d_n' % h], row['h%d_min' % h], row['h%d_max' % h]) + ' ' * 4
116
117</pre></td><td valign="top">Text of one mesh in a Part 1 line: the sum of the rates, the thread count, and the lowest and the highest rate of one thread. A mesh without a thread prints <code>-</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>print_summary</code>: the Part 2 table</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">118  def print_summary(summary):
119      print('   %-16s %3s %8s %8s %8s  %-12s %3s %s' % ('kernel', 'n', 'min', 'median', 'max', 'min_ms', 'flg', 'totals in file order (GB/s)'))
120      for s in summary:
121          print('   %-16s %3d %8.2f %8.2f %8.2f  %-12s %3d %s' % (s['kernel'], s['n'], s['min'], s['median'], s['max'],
122                '/'.join(s['min_ms']), s['flagged'], ' '.join('%.2f' % x for x in s['values'])))
123
124</pre></td><td valign="top">Print a line of column names, then one line per kernel: <code>n</code>, then <code>min</code>, <code>median</code> and <code>max</code> with 2 decimals (GB/s), the <code>min_ms</code> values, the number of flagged T rows, and every total in file order.</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: arguments, statistics, output</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">125  def main(argv):
126      flags = [a for a in argv if a.startswith('--')]
127      folders = [a for a in argv if not a.startswith('--')]
128      if not folders or set(flags) - {'--json', '--pool'}:
129          sys.exit(__doc__)</pre></td><td valign="top">Arguments that start with <code>--</code> are flags. All other arguments are folders. Without a folder, or with a flag other than <code>--json</code> and <code>--pool</code>, the script prints the usage text and ends with exit status 1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">130      all_rows, all_summary = [], []
131      per_folder = []
132      for folder in folders:
133          rows = interval_rows(folder)
134          if not rows:
135              sys.exit('no T rows in the csv files of ' + folder)
136          summary = summarize(rows, rows[0]['folder'])
137          per_folder.append((rows, summary))
138          all_rows += rows
139          all_summary += summary
140      pooled = summarize(all_rows, 'POOLED') if '--pool' in flags else []</pre></td><td valign="top">For each folder, build the interval rows with <code>interval_rows</code>. The script stops when the csv files of a folder hold no T row. <code>summarize</code> then builds the statistics of that folder. With <code>--pool</code>, <code>summarize</code> runs once more over the rows of all folders together, under the folder name <code>POOLED</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">141      if '--json' in flags:
142          json.dump(rounded({'intervals': all_rows, 'summary': all_summary + pooled}), sys.stdout, indent=1)
143          print()
144          return</pre></td><td valign="top">With <code>--json</code>, print one JSON object and return. <code>intervals</code> holds every interval row of every folder, also the rows that are not 64+56. <code>summary</code> holds the statistics per folder, then the pooled ones. <code>rounded</code> rounds every number to 3 decimals first.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">145      for rows, summary in per_folder:
146          print('== ' + rows[0]['folder'])
147          last_file = None
148          for r in rows:
149              if r['file'] != last_file:
150                  last_file = r['file']
151                  print('-- %s  (header: stop=%s min_ms=%s thp=%s)' % (r['file'], r['stop'], r['min_ms'], r['thp']))
152                  print('   %2s %3s %-16s %4s %8s  %-32s %-32s %8s %-5s %s' % ('rd', 'pos', 'kernel', 'thr', 'total',
153                        'h0: CPUs 0-63, GB/s n (min-max)', 'h1: CPUs 64-127', 'I_agg', '64+56', 'flg'))
154              print('   %2d %3d %-16s %4d %8.2f  %s %s %8s %-5s %d' % (r['round'], r['pos'], r['kernel'], r['threads'], r['total'],
155                    fmt_half(r, 0), fmt_half(r, 1), '-' if r['I_agg'] is None else '%.2f' % r['I_agg'],
156                    'yes' if r['is_64_56'] else 'no', r['flagged']))
157          print('-- 64+56 intervals of %s, total GB/s per kernel' % rows[0]['folder'])
158          print_summary(summary)
159          print()</pre></td><td valign="top">Text output, per folder, under a title line with the folder name:<ul><li>Part 1: a line with the file name and its header values, a line of column names, then one line per interval. The line shows round, position, kernel, thread count, <code>total</code> with 2 decimals, the two mesh columns from <code>fmt_half</code>, <code>I_agg</code>, <code>yes</code> or <code>no</code> for 64+56, and the flagged count.</li><li>Part 2: the table of <code>print_summary</code> for this folder.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">160      if pooled:
161          print('== POOLED over %d folders, 64+56 intervals, total GB/s per kernel' % len(folders))
162          print_summary(pooled)
163
164</pre></td><td valign="top">With <code>--pool</code>, print the pooled table with <code>print_summary</code> after the last folder.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">165  if __name__ == '__main__':
166      main(sys.argv[1:])</pre></td><td valign="top">Run <code>main</code> with the command-line arguments when the file is started as a script. When another script imports the file, <code>main</code> does not run.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 3025 and 3026: the field names of the I row and the T row. Lines 3066 to 3071: total bytes and longest elapsed time of an interval. Lines 3077 to 3084: the I row (`aggregate_GBps` = total bytes / longest elapsed time) and the T row (`elapsed_s` = end minus start of the thread, 6 decimals. Flag `late` or `-`).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 1688: the clock read before the first timed kernel call. Lines 1690 to 1701: with the common stop the thread reads the clock after each chunk of 2 MiB and stops at the first read that is not before the common deadline. Lines 1722 to 1725: start time, end time and the `late` flag (line 133: more than 100000 ns after the common start).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: lines 11 to 17: rx.sh reads its spec file (the input file of rx.sh: each line holds a tag and the arguments of one bwx12 process). It writes the output of each process to the csv file with the name of the tag. The spec files `like.spec`, `cfwd.spec` and `crev.spec` in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17` hold one line each, with the kernel sequences of part L and part C.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: and the csv files of the 8 other folders `w120-T72L*`, `w120-T72C*` and `w120-T72I*` of the same results folder. Output of `stat_bwx.py --json` on these 9 folders, run on 2026-11-21 for this explanation: 74 intervals, `is_64_56` true in all, `flagged` 0 in all, `total` minus `I_agg` from 0.000 to 0.018 GB/s. Example: the first `oldread` interval of this file has `total` 462.30 GB/s, and its I row in line 128 holds 462.29 GB/s.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 816 to 834: the cross-check. Line 820 calls `stat_bwx.interval_rows`. Lines 817 and 818: the check covers the 9 bwx12 folders of the rerun and the 11 folders of the list `rx_sets` (lines 207 to 221), which are earlier runs of the runners bwx12 and bwx11. Lines 821 to 823: of a folder of `rx_sets` the check takes only the csv files that the list names (17 files in total). The folders of the runner bwx (list `step_sets`, lines 258 to 267) are not in the check.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: line 292, decision (i): the rate per interval of the bwx runners is the sum over the threads of bytes / elapsed time. Line 236, check 24: the cross-check with stat_bwx.py passed for 297 intervals of 20 folders, among them the 9 folders of parts L, C and I with 74 intervals. In `make_report.py` of the same folder the function `val` (lines 176 to 189) computes the same sum for a record of a bwx runner.
