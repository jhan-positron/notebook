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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env python3
  2  """stat_k120.py - statistics of threads120.csv, the 120-thread file of run_kernels.sh and ra.sh.
  3
  4  Usage: stat_k120.py [--json] [FOLDER ...] [--pool [FOLDER ...]]
  5
  6  Each FOLDER holds one threads120.csv. In that file one process is one "-- binary ..." header
  7  line, then one csv line per timed interval (rep 0, 1, 2), then one "best" line (not used here).
  8
  9  Output, per folder and per (kernel, binary):
 10    n, min, median and max of aggregate_GBps over the intervals (GB = 1e9 bytes),
 11    every interval in file order with its round and its per-thread min and max (GB/s),
 12    and the load value of the header lines (min and max per folder).
 13  --pool F1 F2 ..  also prints the same statistics over the intervals of F1, F2, .. taken together.
 14                   Each of these folders is still printed alone first.
 15  --pool           (no folder after it) pools all folders of the command line.
 16  --json           prints the rows as a JSON list instead of text.
 17  The parser follows summarize.py of results/kernels-20261113T181222Z.
 18  """</pre></td><td valign="top">Usage text of the tool. <code>main</code> shows it as the help text (line 90).<ul><li>One process in the file is one header line that starts with <code>-- binary</code>, then the output of the benchmark binary: one comment line, one line of column names, one line per timed interval and one <code>best</code> line.</li><li>The tool reports the column <code>aggregate_GBps</code> per pair of kernel and binary. GB means 1e9 bytes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 19  import argparse, json, os, re, statistics, sys
 20
 21  HDR = re.compile(r'-- binary (\S+) kernel (\S+) threads (\d+) cpus (\S+) bytes (\S+) round (\d+) load (\S+)(?: utc (\S+))?')
 22
 23</pre></td><td valign="top"><code>HDR</code> is the pattern of a header line. ra.sh (the script of part A) writes one header line directly before it starts a benchmark process. The eight groups are, in this order: binary, kernel, thread count, CPU list, buffer size, round, load and UTC time. A header line without the <code>utc</code> part also fits.</td></tr>
<tr><td colspan="2"><b>Function <code>load</code>: read the processes of one folder</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 24  def load(folder):
 25      """Return the processes of folder/threads120.csv in file order, each with its intervals."""
 26      fn = os.path.join(folder, 'threads120.csv')
 27      procs, cur = [], None
 28      with open(fn) as f:
 29          for ln, l in enumerate(f, 1):
 30              l = l.strip()</pre></td><td valign="top">Open <code>threads120.csv</code> of the folder and read it line by line. <code>ln</code> is the line number, counted from 1. <code>strip</code> removes spaces and the line end from both ends of the line. <code>procs</code> collects one record per process, and <code>cur</code> is the process that the next interval lines belong to.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 31              m = HDR.match(l)
 32              if m:
 33                  cur = dict(folder=folder, binary=m[1], kernel=m[2], round=int(m[6]), load=float(m[7]), utc=m[8], iv=[])
 34                  procs.append(cur)
 35                  continue</pre></td><td valign="top">A line that fits <code>HDR</code> starts a new process record. The record keeps the folder, the binary, the kernel, the round, the load, the UTC time and an empty list <code>iv</code> for the intervals. The thread count, the CPU list and the buffer size of the header line are not kept.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 36              p = l.split(',')
 37              if len(p) &gt; 8 and p[3].isdigit():</pre></td><td valign="top">Every other line is split at the commas into the list <code>p</code>. Python counts from 0, so <code>p[3]</code> is field 4, <code>rep</code>. The line is an interval line when it has more than 8 fields and field 4 holds digits only. This test drops the <code>#</code> comment line (it has no comma), the line of column names (field 4 is the word <code>rep</code>) and the <code>best</code> line (field 4 is <code>best</code>).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 38                  if cur is None or p[0] != cur['kernel']:
 39                      sys.exit(f'{fn}:{ln}: interval line does not belong to the header line before it')
 40                  # aggregate_GBps, per_thread_min_GBps, per_thread_max_GBps
 41                  cur['iv'].append((float(p[6]), float(p[7]), float(p[8]), int(p[4]) // int(p[2])))</pre></td><td valign="top"><ul><li>An interval line must come after a header line, and its first field must be the kernel of that header line. If not, the script stops and names the file and the line.</li><li>Kept per interval: <code>p[6]</code> = <code>aggregate_GBps</code>, <code>p[7]</code> = <code>per_thread_min_GBps</code>, <code>p[8]</code> = <code>per_thread_max_GBps</code>. The last two are the lowest and the highest rate of one thread in the interval. The rate of a thread is its bytes divided by its own elapsed time [Ref1].</li><li>Also kept: the pass count <code>p[4] // p[2]</code>. It is <code>total_bytes</code> divided by <code>bytes_per_thread</code>, rounded down.</li><li>Not read: <code>p[1]</code> (<code>threads</code>), <code>p[5]</code> (<code>elapsed_s</code>) and <code>p[9]</code> (<code>per_thread_avg_GBps</code>).</li><li>No rate is computed here. <code>aggregate_GBps</code> is the number that the binary printed: the bytes of all threads, divided by the longest elapsed time of one thread, divided by 1e9 [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 42      if not procs:
 43          sys.exit(f'{fn}: no "-- binary" header line')
 44      return procs
 45
 46</pre></td><td valign="top">The script stops when the file holds no header line. Otherwise <code>load</code> returns the processes in file order.</td></tr>
<tr><td colspan="2"><b>Function <code>rows_of</code>: statistics per kernel and binary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 47  def rows_of(label, procs, folders=None):
 48      """One row per (kernel, binary), in the order of first appearance in procs."""
 49      loads = [p['load'] for p in procs]
 50      cells = {}
 51      for p in procs:
 52          cells.setdefault((p['kernel'], p['binary']), []).append(p)</pre></td><td valign="top"><code>loads</code> holds the load of every process that was passed in. <code>cells</code> groups the processes by the pair (kernel, binary), in the order in which each pair first appears. So the old read kernel is the group (<code>read</code>, <code>bw_old</code>), and the new read kernel is the group (<code>read</code>, <code>bw_new</code>).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 53      rows = []
 54      for (kernel, binary), ps in cells.items():
 55          iv = [(p['round'], a, lo, hi, n) for p in ps for a, lo, hi, n in p['iv']]
 56          v = [x[1] for x in iv]</pre></td><td valign="top"><code>iv</code> lists every interval of the group: the intervals of its first process, then those of the next process. No interval is left out. <code>v</code> holds the <code>aggregate_GBps</code> values of these intervals.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 57          row = dict(folder=label, kernel=kernel, binary=binary, n=len(v),
 58                     min=min(v) if v else None, median=round(statistics.median(v), 3) if v else None,
 59                     max=max(v) if v else None, values=v, rounds=[x[0] for x in iv],
 60                     per_thread_min=[x[2] for x in iv], per_thread_max=[x[3] for x in iv], passes=[x[4] for x in iv],
 61                     processes=len(ps), loads=[p['load'] for p in ps],
 62                     folder_load_min=min(loads), folder_load_max=max(loads))</pre></td><td valign="top">One result row per group, computed over <code>v</code>:<ul><li><code>n</code>: the number of intervals. <code>min</code> and <code>max</code>: the lowest and the highest <code>aggregate_GBps</code>.</li><li><code>median</code>: the middle value. For an even <code>n</code> it is the mean of the two middle values. It is rounded to 3 decimals (0.001 GB/s).</li><li><code>values</code>, <code>rounds</code>, <code>per_thread_min</code>, <code>per_thread_max</code>, <code>passes</code>: one entry per interval, in file order.</li><li><code>processes</code> and <code>loads</code>: the number of processes of the group and their load values.</li><li><code>folder_load_min</code> and <code>folder_load_max</code>: the lowest and the highest load over all processes that were passed in, not only those of this group.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 63          if folders:
 64              row['folders'] = folders
 65          row['_procs'] = ps  # for the text output only; removed before the JSON output
 66          rows.append(row)
 67      return rows
 68
 69</pre></td><td valign="top">A pooled row also names its folders. <code>_procs</code> keeps the process records for the text report. <code>main</code> removes this field before the JSON output (line 108).</td></tr>
<tr><td colspan="2"><b>Function <code>print_text</code>: text report of one group</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 70  def print_text(title, rows, show_folder):
 71      nproc = sum(r['processes'] for r in rows)
 72      per = sorted({len(p['iv']) for r in rows for p in r['_procs']})
 73      print(f'== {title}')
 74      print(f'   {nproc} processes, intervals per process: {per}, '
 75            f'load in the "-- binary" lines: min {rows[0]["folder_load_min"]:.2f} max {rows[0]["folder_load_max"]:.2f}')
 76      print('   aggregate_GBps per (kernel, binary); under it one line per process: aggregate (per-thread min-max), GB/s')</pre></td><td valign="top">Print the title, one summary line and one line that describes the layout of the report. The summary line holds the number of processes, the different interval counts per process, and the lowest and the highest load. The load values are taken from the first row, and they are the same in every row of the group.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 77      for r in rows:
 78          if r['n']:
 79              print(f'{r["kernel"]:9} {r["binary"]:7} n={r["n"]:&lt;3} min {r["min"]:7.2f}  median {r["median"]:7.2f}  max {r["max"]:7.2f}')
 80          else:
 81              print(f'{r["kernel"]:9} {r["binary"]:7} n=0   NO INTERVAL')
 82          for p in r['_procs']:
 83              where = os.path.basename(p['folder']) + ' ' if show_folder else ''
 84              ivs = ' | '.join(f'{a:.2f} ({lo:.2f}-{hi:.2f}, {n} passes)' for a, lo, hi, n in p['iv']) or 'NO INTERVAL'
 85              print(f'    {where}round {p["round"]} load {p["load"]:6.2f} utc {p["utc"]} | {ivs}')
 86      print()
 87
 88</pre></td><td valign="top">Print one line per pair of kernel and binary: <code>n</code>, then <code>min</code>, <code>median</code> and <code>max</code> with 2 decimals (0.01 GB/s). A pair without an interval prints <code>NO INTERVAL</code>. Under it, print one line per process: round, load, UTC time, and for each interval the rate, the per-thread minimum and maximum and the pass count. In a pooled report the line starts with the folder name.</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: arguments, statistics, output</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 89  def main():
 90      ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
 91      ap.add_argument('folders', nargs='*', help='result folders, each with a threads120.csv')
 92      ap.add_argument('--pool', nargs='*', metavar='FOLDER', help='folders to pool (none named: all folders)')
 93      ap.add_argument('--json', action='store_true', help='print the rows as JSON')
 94      a = ap.parse_args()</pre></td><td valign="top">Read the arguments: any number of folders, <code>--pool</code> with any number of folders after it, and <code>--json</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 95      norm = lambda d: d.rstrip('/') or '/'
 96      singles = list(dict.fromkeys(norm(d) for d in a.folders + (a.pool or [])))
 97      if not singles:
 98          ap.error('no folder given')
 99      pool = [norm(d) for d in a.pool] or singles if a.pool is not None else []
100      pool = list(dict.fromkeys(pool))</pre></td><td valign="top"><ul><li><code>norm</code> removes <code>/</code> characters from the end of a folder name.</li><li><code>singles</code> is the list of all folders named anywhere on the command line, each one once. The folders outside <code>--pool</code> come first, then the folders after <code>--pool</code>. Without a folder the script ends with a usage error.</li><li><code>pool</code> is the list of the folders to pool: the folders after <code>--pool</code>, or all folders when none follows <code>--pool</code>. Without <code>--pool</code> the list is empty.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">101      procs = {d: load(d) for d in singles}
102      groups = [(d, rows_of(d, procs[d]), False) for d in singles]
103      if pool:
104          allp = [p for d in pool for p in procs[d]]
105          groups.append((f'pool of {len(pool)} folders: ' + ', '.join(os.path.basename(d) for d in pool),
106                         rows_of('pool', allp, pool), True))</pre></td><td valign="top">Read every folder once with <code>load</code>. Build one group of rows per folder with <code>rows_of</code>. With a pool, join the processes of the pool folders and build one more group from them. Its rows carry the folder label <code>pool</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">107      if a.json:
108          out = [{k: v for k, v in r.items() if k != '_procs'} for _, rows, _ in groups for r in rows]
109          json.dump(out, sys.stdout, indent=1)
110          print()
111      else:
112          for title, rows, show_folder in groups:
113              print_text(title, rows, show_folder)</pre></td><td valign="top">With <code>--json</code>, print the rows of all groups as one JSON list, without the field <code>_procs</code>. Without it, print each group with <code>print_text</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">114      empty = [(p['folder'], p['kernel'], p['binary'], p['round']) for d in singles for p in procs[d] if not p['iv']]
115      if empty:
116          sys.exit(f'process without any interval line (folder, kernel, binary, round): {empty}')
117
118</pre></td><td valign="top">After the output, list every process that has a header line and no interval line. If the list is not empty, the script prints it as an error message and ends with exit status 1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">119  if __name__ == '__main__':
120      main()</pre></td><td valign="top">Run <code>main</code> when the file is started as a script. When another script imports the file, <code>main</code> does not run.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: source of bw_new. Lines 471 to 479: the clock reads of a thread (`t0` before the first timed pass, `t1` after each check step) and its elapsed time `t1 - t0`. Lines 24 and 452 to 454: a check step is 1 pass when the buffer is larger than 8 MiB. Lines 418 to 444: the bytes that one pass counts (1 x the buffer size, and 2 x for `copy` and `asmcopy`). Lines 584 to 603: `aggregate_GBps` = total bytes / longest elapsed time / 1e9, printed with 2 decimals, and the per-thread minimum, maximum and average. The records of 2026-11-13 show two texts of `bandwidth.c`. This local text has the sha256 (a checksum) `f1985072...`. The script run_kernels.sh of the test of 2026-11-13 wrote a record file `probe.txt` at each start. The `probe.txt` of the start of 18:32:18 UTC holds this value in line 15 (folder `kernels-20261113T183218Z` of `/home/jhan/workspace/titan/cache-perf/crb/results`). That start built the binaries and timed nothing. The `probe.txt` of the timed run of 18:12:22 UTC holds another sha256 for `bandwidth.c` in line 15: `c1406e02...` (folder `kernels-20261113T181222Z`). All three `probe.txt` records of that day hold the same sha256 for the binary bw_new (`fd7c14df...`). ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`: source of bw_old. Lines 314 to 322 and 427 to 446: the same clock reads and the same formula.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: lines 39 to 48: the format of the header line, `--reps 3`, the 6 kernels, the 2 binaries and the 2 rounds.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: and the same file of the folders `k120-T72A2-20261117T221518Z` and `k120-T72A3-20261117T221827Z`: the 36 interval lines of kernel `read`, fields 7 and 10. Example: line 4 of the first file holds 467.83 GB/s and 3.99 GB/s. 120 x 3.99 = 478.8 GB/s (est.).
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 798 to 815: the cross-check. Line 806 calls `stat_k120.load`. `facts_data.py` of the same folder uses `stat_k120.HDR` in line 271.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: line 9: rates are rounded half up, and a median of an even number of values can differ by 0.01 GB/s from the output of stat_k120.py. Line 292, decision (i): the rate per interval of part A is the column aggregate_GBps. Line 235, check 23: the cross-check with stat_k120.py passed for 333 interval rows (the 3 part A folders of the rerun and 3 earlier part A runs). In `make_report.py` of the same folder the function `val` (lines 176 to 189) returns the same rate for a part A record.
