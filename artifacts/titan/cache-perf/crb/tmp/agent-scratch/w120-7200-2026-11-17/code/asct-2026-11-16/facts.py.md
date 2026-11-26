# `facts.py` explained, line by line

- Source file: `asct-2026-11-16/facts.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 255 lines, 14215 bytes).
- sha256 of the source when this page was built: `cd41109060abd01315613207e2e40dd850bfbbd3c5d004d220fa2ea6e1fe75a4`.

## Short version: purpose

`facts.py` turns the raw results of the ASCT cross-check (`asct.json`) and the older values of our own loops (`baseline.json`) into the numbers of the report. It reduces each cell to a median, a range and a count, computes ratios and a straight-line fit, and applies the predictions and rules of the decisions file as `True` or `False` verdicts. It writes one JSON file, which the project keeps as `facts.json` and which the text and page scripts read.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **P-A1, P-A4, P-A5, P-B1, P-B2, P-B3, R-A3, D-A2**: names of the decisions file. P is a prediction with a pass rule, R is a rule and D is an item that is only described.
- **Verdict**: the result of the test of one prediction or rule. `True` means that the prediction holds or that the rule finds a difference.
- **ASCT binary**: the benchmark program of ASCT, `loaded-latency-asct-sve.bin`. One start is one process.
- **ASCT loop**: the read loop of the ASCT binary. By the decisions file it loads 8 bytes from each 64-byte line.
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings, for example one CPU and one buffer size. By the decisions file a cell value is the median of its processes, and the range is the smallest to the largest value.
- **Median**: the middle value of a sorted list of values.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Line**: one cache line of 64 bytes.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase. `analyze.py` computes it.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Interval**: one timed measurement inside a process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Event set**: a named list of counter events that one process counts together.
- **Probe binary**: the ASCT binary built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT. The processes with counters use it.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB. The processes without counters use it.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Tag**: the name of one process of the mesh-counter runs.
- **Counting window**: one run of `perf stat -a` for the command `sleep` in the script `run_mesh.sh`.
- **DTC node**: by the Linux documentation the main controller of the counters of a mesh. It holds the global counters, and the cycle counter belongs to it [Ref3].
- **Vendor runs**: two complete ASCT runs that the chip vendor made on its own machines. Their console outputs and result archives lie in the welcome kit of Arm.
- **`launches.txt`**: a file that each run script writes into its result folder. It gets one `launch` line before each process and one `rc` line after it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Read `asct.json` from argument 1 and `baseline.json` from argument 2 (lines 39 to 42).
2. One core, for each of the CPUs 2 and 41 and each of the 16 sizes: reduce the ASCT processes of part U to a median, a range and a count. Put the older values of our three loops from `baseline.json` beside them. Take the median of each counter of part C (lines 45 to 65).
3. Per CPU: the ratio of the rate at 8 MiB to the rate at 1 MiB and the verdict of P-A1, the straight-line fit of cycles per line against L2 refills per line (the helper `linfit` fits by least squares), the clock rate that follows from the counters, the distance between counted and uncounted rates, and rule R-A3 for each prefetch counter (lines 66 to 96).
4. Injected NOPs on one core: the rates of part N with the verdict of P-A4, the counters of part NC with the verdict of P-A5, and the two lists of rule R-A3 over both CPUs (lines 97 to 136).
5. CPU 41 against CPU 2 per size, and the ratio of 8 MiB to 1 MiB of the vendor runs (lines 137 to 143).
6. Whole chip: merge all many-core folders. Reduce each cell to medians and ranges (helper `cell`). Compute the verdicts of P-B1, P-B2 and P-B3, the traffic types and the counters per mesh (lines 145 to 213).
7. Mesh counters: events per second and per line for each tag (lines 215 to 233).
8. Write the output file and print a short view to the console (lines 234 to 251).

## Behavior a reader must know

- Units: every rate is in GB/s with GB = 1e9 bytes. Every counter value of the cores is a count per 64-byte line. A mesh counter has two values, events per second and a count per line (lines 226 to 228). `ghz` is in GHz. The fields that end in `pct` are in percent.
- How values are combined: a cell is reduced by `stat` to the median, the smallest value, the largest value and the count of its processes. A counter of a one-core cell is the median over the processes that counted it. For a counted whole-chip case each process first gives the median over the threads of a mesh, and the value is the median of these thread medians over the event sets (lines 199 to 205).
- The verdict rules, as the code tests them:
  - P-A1 (line 70): the ASCT rate at 8 MiB divided by the rate at 1 MiB is below 0.90, per CPU.
  - R-A3 (lines 92 to 94, line 130): the value at 8 MiB lies outside the range of the values at 6 MiB and 12 MiB, after the range was widened at each end by 10 % of the mean of the two. A counter is different only when this holds on both CPUs.
  - P-A4 (lines 104 to 109): for each count of injected NOPs whose rate at 1 MiB is below 60 GB/s, the rate at 8 MiB is within 3 % of the rate at 1 MiB.
  - P-A5 (lines 124 to 128): `l2d_cache_lmiss_rd` per line at 8 MiB with 2 injected NOPs is below 0.8 times the value with 0 injected NOPs.
  - P-B1 (lines 185 to 186): the median total at 64+56 with 0 injected NOPs is below 334 GB/s. At 459 GB/s or more the prediction fails.
  - P-B2 (line 184, line 187): at least one count of injected NOPs from 1 to 40 has a median total of 459 GB/s or more.
  - P-B3 (lines 192 to 193): the median total is 330.6 to 368.55 GB/s for 64+0 and 302.1 to 337.785 GB/s for 0+56.
- The verdicts use the total that ASCT prints. The lower bound `floor` is computed beside it but takes part in no verdict.
- A verdict never stops the script. It is stored as `True`, `False` or `None`. `None` means that the data for the test is missing. For P-A4 it also means that no count of injected NOPs has a rate below 60 GB/s at 1 MiB (line 108). Two verdicts have no `None`: P-B2 is `False` without data (line 187), and P-A5 has no entry for a CPU without data (line 126).
- Which verdicts the report uses: the scripts `report.py` and `dyn_notes.py` read the verdicts of rule R-A3 (`different`, `RA3_different`, `RA3_counted`). No other script of this folder reads `PA1`, `PA4`, `PB1`, `PB1_fail_hard`, `PB2`, `PB3` or a field `holds`. This script prints the verdicts of P-A1, P-A4, P-B1, P-B2 and P-B3 to the console (lines 242 to 248). The headings of the report that say that a prediction holds are fixed text of `dyn_notes.py`.
- The description text says that the report generator only formats what this file computes (line 3). That is not exact: `dyn_notes.py` and `figs.py` compute further values from the output, such as percentages, factors and quotients.
- The ranges of our older loops are not ranges of processes. For the values from `final8.json` they are percentiles of rows. For 1 GiB on CPU 2 they are the smallest and the largest interval of the first run, and `n` counts intervals (line 55, line 60).
- Only the first one-core folder with part U is used, and the first folder with part NC. All many-core folders are merged (lines 45 to 46, lines 149 to 155).
- Several lines have no test for a missing value: lines 68 to 69, line 77, line 138, line 143. A missing value stops the script there with an error, and no output file is written.
- The scripts `notes.py` and `report.py` of the same folder read the output file. They pass its content to `dyn_notes.py` and `figs.py`.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/facts.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (255 lines, 14215 bytes, sha256 `cd41109060abd01315613207e2e40dd850bfbbd3c5d004d220fa2ea6e1fe75a4`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text, modules and constants (lines 1 to 17)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""facts.py ASCT.json BASELINE.json OUT.json: every derived number and every verdict of the report,` | Starts the description text of the file. Usage: three arguments, the output of `analyze.py`, the output of `baseline.py` and the output file. The text says that the script computes every derived number and every verdict of the report. That is not exact. The scripts `dyn_notes.py` and `figs.py` derive further values from the output, such as percentages, factors and quotients. |
| 3 | `computed by the rules of DECISIONS.md. The report generator only formats what this file computes."""` | Description, last line: the numbers follow the rules of the decisions file `DECISIONS.md`. The text says that the report generator only formats what this file computes. That is not exact either. The headings of the report that say that a prediction holds are fixed text of `dyn_notes.py`. No other script of this folder reads the verdicts `PA1`, `PA4`, `PB1`, `PB2` and `PB3` or a field `holds`. |
| 4 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 5 | `import statistics as st` | Loads the module `statistics` under the short name `st`. The script uses its function `median`. |
| 6 | `import sys` | Loads the module `sys`, which gives the arguments of the script. |
| 8 | `SIZES = [32768, 1048576, 1572864, 2097152, 2621440, 3145728, 4194304, 5242880, 6291456, 8388608, 12582912,` | `SIZES`: the 16 buffer sizes of the one-core runs in bytes. This line holds 32 KiB and 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8 and 12 MiB. |
| 9 | `         16777216, 25165824, 33554432, 268435456, 1073741824]` | Continues line 8: 16, 24 and 32 MiB, 256 MiB and 1 GiB. |
| 10 | `FIT_SIZES = [b for b in SIZES if 1048576 <= b <= 33554432]` | `FIT_SIZES`: the sizes from 1 MiB to 32 MiB, both ends included. These 13 sizes are used for the straight-line fit of lines 71 to 78. |
| 11 | `CPUS = [2, 41]` | `CPUS`: the two CPUs of the one-core runs, 2 and 41. |
| 12 | `NOPS = [0, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100, 180]` | `NOPS`: the 16 counts of injected NOPs of the many-core runs, from 0 to 180. |
| 13 | `PREFETCH = ['l1d_cache_hwprf', 'l2d_cache_hwprf', 'l2d_cache_l1hwprf', 'l2d_cache_refill_l1hwprf', 'l1d_cache_prfm',` | `PREFETCH`: the names of the 9 prefetch counters that rule R-A3 judges. By the text that `dyn_notes.py` writes into the report, the first two count the prefetches of the hardware prefetcher of L1 and of L2. The next two count the L2 accesses and the L2 refills that the L1 prefetcher caused. The last name of this line and the names of line 14 are the 5 events for prefetch instructions. |
| 14 | `            'l2d_cache_prfm', 'l1d_cache_refill_prfm', 'l2d_cache_refill_prfm', 'prf_spec']` | Continues line 13: four more counters for prefetch instructions. |
| 15 | `M1, M8 = 1048576, 8388608` | `M1`, `M8`: 1 MiB and 8 MiB in bytes. |

### Helper functions `label`, `stat` and `linfit` (lines 18 to 38)

| Line | Source | Explanation |
|---:|---|---|
| 18 | `def label(b):` | Starts the function `label`. It turns a size in bytes into a short text such as `8 MiB`. |
| 19 | `    for unit, n in (('GiB', 1 << 30), ('MiB', 1 << 20), ('KiB', 1 << 10)):` | Starts a loop over three units from the largest to the smallest: GiB (2 to the power of 30 bytes), MiB (2 to the power of 20) and KiB (2 to the power of 10). `1 << 30` shifts the number 1 by 30 binary places. |
| 20 | `        if b >= n:` | Takes the first unit that is not larger than the size. |
| 21 | `            v = b / n` | `v`: the size in that unit. |
| 22 | `            return f'{v:g} {unit}'` | Returns the number and the unit. The format `g` prints the number without zeros at the end. So 1572864 bytes give `1.5 MiB` and 8388608 bytes give `8 MiB`. |
| 23 | `    return f'{b} B'` | A size below 1 KiB is returned in bytes with the letter `B`. |
| 26 | `def stat(v):` | Starts the function `stat`. It reduces a list of values to four numbers. |
| 27 | `    return {'median': st.median(v), 'lo': min(v), 'hi': max(v), 'n': len(v)} if v else None` | Returns the median, the smallest value (`lo`), the largest value (`hi`) and the count (`n`) of the list. For an empty list it returns `None`. |
| 30 | `def linfit(pts):` | Starts the function `linfit`. It fits a straight line y = a + b times x to a list of points (x, y) by least squares. |
| 31 | `    n = len(pts)` | `n`: the number of points. |
| 32 | `    mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n` | `mx`, `my`: the mean of the x values and the mean of the y values. |
| 33 | `    sxx = sum((p[0] - mx) ** 2 for p in pts)` | `sxx`: the sum of the squared distances of the x values from their mean. |
| 34 | `    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx` | `b`: the slope of the line. It is the sum of the products of the x distance and the y distance from the two means, divided by `sxx`. |
| 35 | `    a = my - b * mx` | `a`: the value of the line at x = 0. The line passes through the point of the two means. |
| 36 | `    return a, b, max(abs(p[1] - (a + b * p[0])) for p in pts)` | Returns `a`, `b` and the largest distance in y between a point and the line. |

### Function `main`: the two input files (lines 39 to 43)

| Line | Source | Explanation |
|---:|---|---|
| 39 | `def main():` | Starts the function `main`. |
| 40 | `    A = json.load(open(sys.argv[1]))` | `A`: the content of the file of argument 1, the output of `analyze.py` (`asct.json`). It holds the rates and the counts of the ASCT processes. |
| 41 | `    B = json.load(open(sys.argv[2]))` | `B`: the content of the file of argument 2, the output of `baseline.py` (`baseline.json`). It holds the older values of our own loops and the vendor runs. |
| 42 | `    F = {'sizes': SIZES, 'labels': {str(b): label(b) for b in SIZES}, 'cpus': CPUS}` | `F`: the dictionary that becomes the output file. It starts with the list of the sizes, a label text for each size and the list of the CPUs. |

### One core, per CPU: rates, prediction P-A1, the fit and rule R-A3 (lines 44 to 96)

| Line | Source | Explanation |
|---:|---|---|
| 44 | `    # ---------------- one core ----------------` | Comment: the block for one core starts here. |
| 45 | `    S = next((x for x in A['single'] if x['cells']), None)` | `S`: the first one-core folder of `asct.json` whose `cells` is not empty. That is a folder with runs of part U. It is `None` when no folder has such runs. The values of the parts U, N and C come from this one folder only. |
| 46 | `    NC = next((x for x in A['single'] if x.get('nops_counted')), None)     # part NC ran in its own folder` | `NC`: the first one-core folder whose `nops_counted` is not empty, or `None`. Comment: part NC ran in its own folder. |
| 47 | `    one = {}` | `one`: the results per CPU. It starts empty. |
| 48 | `    if S:` | The block of lines 49 to 136 runs only when a folder with part U exists. |
| 49 | `        for cpu in CPUS:` | Starts a loop over the CPUs 2 and 41. |
| 50 | `            c = {'asct': {}, 'old': {}, 'new': {}, 'newc': {}, 'cnt': {}}` | `c`: the values of this CPU. `asct`: the ASCT rates per size. `old`: the old read kernel. `new`: the new read kernel in its assembly form. `newc`: the new read kernel in its C form. `cnt`: the counters per size. |
| 51 | `            for b in SIZES:` | Starts a loop over the 16 sizes. |
| 52 | `                c['asct'][b] = stat(S['cells'].get(f'{cpu}.{b}', []))` | The ASCT rate of this CPU and size, in GB/s: the median, the smallest and the largest value and the count of the process totals of part U. The totals come from the entry `cells` of the folder `S` in `asct.json`, under the key CPU and size. Without a process the entry is `None`. |
| 53 | `                for key, name in (('old', 'oldread'), ('new', 'asmread'), ('newc', 'read')):` | Starts a loop over our three older loops and their names in `baseline.json`: `oldread`, `asmread` and `read`. |
| 54 | `                    v = B['single'].get(f'{name}.{cpu}.{b}')` | `v`: the entry of `baseline.json`, block `single`, under the key name, CPU and size. It is `None` when the block has no such entry. |
| 55 | `                    c[key][b] = {'median': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'n': v['processes'], 'src': 'final8'} if v else None` | Copies the entry: `median`, `lo` and `hi` as they are, the field `processes` as `n`, and the mark `final8` as `src`. By `baseline.py` these values come from the file `final8.json` of 2026-11-15. There `median` is the median of the row medians, `lo` the smallest `p5` and `hi` the largest `p95` of the rows. By their names these two fields are the 5th and the 95th percentile. So `lo` and `hi` are not the smallest and the largest process. |
| 56 | `                if b == 1 << 30 and cpu == 2:   # only the first run of 2026-11-13 has 1 GiB, and only CPUs 0 and 2` | A special case for the size 1 GiB (`1 << 30` bytes) on CPU 2. Comment: only the first run of 2026-11-13 has 1 GiB, and only for the CPUs 0 and 2. |
| 57 | `                    for key, name in (('old', 'bw_old'), ('newc', 'bw_new')):` | Starts a loop over the two binaries of that run: `bw_old` for the old read kernel and `bw_new` for the C form of the new read kernel. |
| 58 | `                        v = B['first'].get(f'{name}.read.{cpu}.{b}')` | `v`: the entry of `baseline.json`, block `first`, under the key binary, kernel `read`, CPU and size. |
| 59 | `                        if v:` | When the entry exists, |
| 60 | `                            c[key][b] = {'median': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'n': v['n'], 'src': 'first'}` | it replaces the entry of line 55. Here `lo` and `hi` are the smallest and the largest rate, and `n` is the number of rate values. By `baseline.py` each value is one timed interval of the first run, not one process. `src` is `first`. |
| 61 | `                cc = S['counted'].get(f'{cpu}.{b}')` | `cc`: the counted cell of part C for this CPU and size, from the entry `counted` of the folder `S`. |
| 62 | `                if cc:` | When the cell exists: |
| 63 | `                    c['cnt'][b] = {n: st.median(v) for n, v in cc['ev'].items()}` | `cnt` of this size gets one value per event: the median of the counts per line over the processes that counted the event. |
| 64 | `                    c['cnt'][b]['_rate'] = st.median(cc['rate'])` | `_rate`: the median of the totals of all counted processes of the cell, in GB/s. |
| 65 | `                    c['cnt'][b]['_rate_lo'], c['cnt'][b]['_rate_hi'] = min(cc['rate']), max(cc['rate'])` | `_rate_lo`, `_rate_hi`: the smallest and the largest of these totals. |
| 66 | `            a1, a8 = c['asct'][M1], c['asct'][M8]` | `a1`, `a8`: the ASCT entries of line 52 at 1 MiB and at 8 MiB. |
| 67 | `            c['ratio_asct'] = a8['median'] / a1['median'] if a1 and a8 else None` | `ratio_asct`: the median ASCT rate at 8 MiB divided by the median ASCT rate at 1 MiB. It is `None` when one of the two cells has no process. |
| 68 | `            c['ratio_new'] = c['new'][M8]['median'] / c['new'][M1]['median']` | `ratio_new`: the same ratio for the new read kernel (`asmread`), from the medians of `baseline.json`. The line has no test for a missing entry. A missing entry stops the script with an error. |
| 69 | `            c['ratio_old'] = c['old'][M8]['median'] / c['old'][M1]['median']` | `ratio_old`: the same ratio for the old read kernel (`oldread`). |
| 70 | `            c['PA1'] = None if c['ratio_asct'] is None else c['ratio_asct'] < 0.90` | `PA1`: the verdict of prediction P-A1 for this CPU. The prediction says that the ASCT rate at 8 MiB is below 0.90 of its rate at 1 MiB. The value is `True` when `ratio_asct` is below 0.90, `False` when it is 0.90 or more, and `None` without a ratio. |
| 71 | `            pts = [(c['cnt'][b]['l2d_cache_refill'], c['cnt'][b]['cpu_cycles']) for b in FIT_SIZES` | `pts`: the points for the fit of item D-A2 of the decisions file. Each point is one size from 1 to 32 MiB. Its x value is `l2d_cache_refill` per line, the L2 refills. Its y value is `cpu_cycles` per line. Both are medians of line 63. The line goes on in line 72. |
| 72 | `                   if b in c['cnt'] and 'l2d_cache_refill' in c['cnt'][b] and 'cpu_cycles' in c['cnt'][b]]` | Continues line 71: a size gives a point only when its cell was counted and holds both counters. |
| 73 | `            if len(pts) >= 3:` | The fit needs at least 3 points. |
| 74 | `                a, bb, res = linfit(pts)` | Fits the line with `linfit`. `a` is the cost in cycles per line without an L2 refill. `bb` is the added cost in cycles for one L2 refill per line. `res` is the largest distance of a point from the line, in cycles per line. |
| 75 | `                c['fit'] = {'a': a, 'b': bb, 'maxres': res, 'n': len(pts)}` | Stores the fit of the ASCT loop under `fit`: `a`, `b`, `maxres` and the number of points `n`. |
| 76 | `            zpts = [(B['zs'][f'asmread.{cpu}.{b}']['r'], B['zs'][f'asmread.{cpu}.{b}']['cyc']) for b in FIT_SIZES if f'asmread.{cpu}.{b}' in B['zs']]` | `zpts`: the same kind of points for the new read kernel (`asmread`). They come from `baseline.json`, block `zs`, fields `r` (L2 refills per line) and `cyc` (cycles per line). By `baseline.py` they are medians of the rows of the step `ZS` of 2026-11-15. |
| 77 | `            a, bb, res = linfit(zpts)` | Fits the line for the new read kernel. This line has no test for the number of points. |
| 78 | `            c['fit_new'] = {'a': a, 'b': bb, 'maxres': res, 'n': len(zpts)}` | Stores that fit under `fit_new`. |
| 79 | `            # clock implied by counted cycles and the rate of the same processes` | Comment: the next value is the clock rate that follows from the counted cycles and from the rate of the same processes. |
| 80 | `            ghz = [c['cnt'][b]['cpu_cycles'] * c['cnt'][b]['_rate'] / 64 for b in SIZES if b in c['cnt'] and 'cpu_cycles' in c['cnt'][b]]` | `ghz`: one value per counted size. It is the cycles per line times the rate `_rate` in GB/s, divided by 64 bytes per line. A rate in GB/s divided by 64 gives 1e9 lines per second. So the product is in 1e9 cycles per second, which is GHz. |
| 81 | `            c['ghz'] = [min(ghz), max(ghz)] if ghz else None` | `ghz` of this CPU: the smallest and the largest of these values, or `None` without a counted size. |
| 82 | `            # counted against uncounted rate` | Comment: the next value compares the rate of the counted processes with the rate of the processes without counters. |
| 83 | `            dev = [abs(c['cnt'][b]['_rate'] / c['asct'][b]['median'] - 1) * 100 for b in SIZES if b in c['cnt'] and c['asct'][b]]` | `dev`: one value per size that has both rates. It is the distance in percent between the median rate of the counted processes (`_rate`, part C, probe binary) and the median rate of part U (installed binary). |
| 84 | `            c['counted_vs_plain_maxpct'] = max(dev) if dev else None` | `counted_vs_plain_maxpct`: the largest of these distances, in percent. `None` without a value. |
| 85 | `            # rule R-A3` | Comment: rule R-A3 follows. |
| 86 | `            pf = {}` | `pf`: the result of the rule per counter. It starts empty. |
| 87 | `            for name in PREFETCH:` | Starts a loop over the 9 prefetch counters. |
| 88 | `                try:` | Starts a block that may fail. |
| 89 | `                    v6, v8, v12 = (c['cnt'][b][name] for b in (6291456, M8, 12582912))` | `v6`, `v8`, `v12`: the count per line of this counter at 6 MiB, 8 MiB and 12 MiB, from the medians of line 63. |
| 90 | `                except KeyError:` | When the counter is missing at one of the three sizes, |
| 91 | `                    continue` | the counter is skipped. |
| 92 | `                lo, hi = min(v6, v12), max(v6, v12)` | `lo`, `hi`: the smaller and the larger of the two neighbour values, which are the values at 6 MiB and at 12 MiB. |
| 93 | `                ext = 0.10 * (v6 + v12) / 2` | `ext`: 10 % of the mean of the two neighbour values. |
| 94 | `                pf[name] = {'v6': v6, 'v8': v8, 'v12': v12, 'different': not (lo - ext <= v8 <= hi + ext)}` | Stores the three values and the verdict `different`. It is `True` when the value at 8 MiB lies below `lo - ext` or above `hi + ext`. This is the test of rule R-A3 for one CPU. |
| 95 | `            c['prefetch'] = pf` | Stores the result of the rule for this CPU under `prefetch`. |
| 96 | `            one[cpu] = c` | Stores the values of this CPU in `one`. |

### One core: injected NOPs, predictions P-A4 and P-A5, CPU 41 against CPU 2 (lines 97 to 144)

| Line | Source | Explanation |
|---:|---|---|
| 97 | `        # part N and prediction P-A4` | Comment: part N and prediction P-A4 follow. |
| 98 | `        pad = {}` | `pad`: the rates of the ASCT loop with injected NOPs. It starts empty. |
| 99 | `        for cpu in CPUS:` | Starts a loop over the two CPUs. |
| 100 | `            for nn in (1, 2, 4, 8):` | Starts a loop over the counts 1, 2, 4 and 8 of injected NOPs. |
| 101 | `                row = {b: stat(S.get('nops', {}).get(f'{nn}.{cpu}.{b}', [])) for b in (32768, M1, M8)}` | `row`: for each of the sizes 32 KiB, 1 MiB and 8 MiB the median, the smallest and the largest value and the count of the process totals of part N, in GB/s. The totals come from the entry `nops` of the folder `S`, under the key NOPs, CPU and size. |
| 102 | `                if row[M1] and row[M8]:` | The row is used only when the sizes 1 MiB and 8 MiB both have a process. |
| 103 | `                    row['ratio'] = row[M8]['median'] / row[M1]['median']` | `ratio`: the median rate at 8 MiB divided by the median rate at 1 MiB. |
| 104 | `                    row['applies'] = row[M1]['median'] < 60` | `applies`: `True` when the median rate at 1 MiB is below 60 GB/s. Prediction P-A4 speaks only about such counts of injected NOPs. The decisions file takes them as loops that their own instructions limit. |
| 105 | `                    row['holds'] = abs(row['ratio'] - 1) <= 0.03 if row['applies'] else None` | `holds`: for a row to which the prediction applies, `True` when the ratio lies between 0.97 and 1.03. So the rate at 8 MiB is within 3 % of the rate at 1 MiB. A gain of more than 3 % fails the test in the same way as a loss. For the other rows the value is `None`. |
| 106 | `                    pad[f'{cpu}.{nn}'] = row` | Stores the row under the key CPU and NOPs, as in `2.4`. |
| 107 | `        F['pad'] = pad` | Stores all rows under `pad`. |
| 108 | `        F['PA4'] = {str(cpu): (None if not any(v['applies'] for k, v in pad.items() if k.startswith(f'{cpu}.')) else` | `PA4`: the verdict of prediction P-A4 per CPU. It is `None` when the prediction applies to no row of the CPU. The line goes on in line 109. |
| 109 | `                               all(v['holds'] for k, v in pad.items() if k.startswith(f'{cpu}.') and v['applies'])) for cpu in CPUS}` | Continues line 108: otherwise it is `True` when `holds` is `True` for every row of the CPU to which the prediction applies. |
| 110 | `        # part NC: the padded loop with counters, and prediction P-A5` | Comment: part NC follows, the loop with injected NOPs and counters, and prediction P-A5. |
| 111 | `        padcnt = {}` | `padcnt`: the counters of the loop with injected NOPs. It starts empty. |
| 112 | `        for cpu in CPUS:` | Starts a loop over the two CPUs. |
| 113 | `            for nn in (1, 2, 4):` | Starts a loop over the counts 1, 2 and 4 of injected NOPs. |
| 114 | `                for b in (M1, M8):` | Starts a loop over the sizes 1 MiB and 8 MiB. |
| 115 | `                    cc = (NC or S).get('nops_counted', {}).get(f'{nn}.{cpu}.{b}')` | `cc`: the counted cell of part NC under the key NOPs, CPU and size. It comes from the entry `nops_counted` of the folder `NC`. Without such a folder the code looks in the folder `S`. |
| 116 | `                    if cc:` | When the cell exists: |
| 117 | `                        d = {n: st.median(v) for n, v in cc['ev'].items()}` | `d`: one value per event, the median of the counts per line over the processes that counted the event. |
| 118 | `                        d['_rate'] = st.median(cc['rate'])` | `_rate`: the median of the totals of all processes of the cell, in GB/s. |
| 119 | `                        d['_rate_lo'], d['_rate_hi'], d['_n'] = min(cc['rate']), max(cc['rate']), len(cc['rate'])` | `_rate_lo`, `_rate_hi`: the smallest and the largest of these totals. `_n`: the number of processes. |
| 120 | `                        padcnt[f'{cpu}.{nn}.{b}'] = d` | Stores `d` under the key CPU, NOPs and size. |
| 121 | `        F['padcnt'] = padcnt` | Stores all cells under `padcnt`. |
| 122 | `        pa5 = {}` | `pa5`: the verdict of prediction P-A5 per CPU. It starts empty. |
| 123 | `        for cpu in CPUS:` | Starts a loop over the two CPUs. |
| 124 | `            k = padcnt.get(f'{cpu}.2.{M8}')` | `k`: the cell with 2 injected NOPs at 8 MiB. |
| 125 | `            base = one[cpu]['cnt'].get(M8, {}).get('l2d_cache_lmiss_rd')` | `base`: the count of `l2d_cache_lmiss_rd` per line at 8 MiB with 0 injected NOPs. It is the median of part C from line 63. By the text of the report this counter counts the L2 read misses with a long latency. |
| 126 | `            if k and 'l2d_cache_lmiss_rd' in k and base:` | The verdict is computed only when the cell exists, the cell holds the counter, and the base value is not 0. |
| 127 | `                pa5[str(cpu)] = {'n0': base, 'n2': k['l2d_cache_lmiss_rd'], 'ratio': k['l2d_cache_lmiss_rd'] / base,` | Stores `n0` (the value with 0 injected NOPs), `n2` (the value with 2) and the ratio of `n2` to `n0`. The dictionary goes on in line 128. |
| 128 | `                                 'holds': k['l2d_cache_lmiss_rd'] < 0.8 * base}` | Continues line 127. `holds`: `True` when the value with 2 injected NOPs is below 0.8 times the value with 0. This is the test of prediction P-A5 for one CPU. |
| 129 | `        F['PA5'] = pa5` | Stores the verdicts under `PA5`. |
| 130 | `        F['RA3_different'] = sorted(n for n in PREFETCH if all(n in one[c]['prefetch'] and one[c]['prefetch'][n]['different'] for c in CPUS))` | `RA3_different`: the sorted names of the prefetch counters whose verdict `different` of line 94 is `True` on both CPUs. Rule R-A3 calls a counter different at 8 MiB only then. |
| 131 | `        F['RA3_counted'] = sorted(n for n in PREFETCH if all(n in one[c]['prefetch'] for c in CPUS))` | `RA3_counted`: the sorted names of the prefetch counters that the rule could judge on both CPUs. |
| 132 | `        F['single_launch'] = S['launches']` | Copies the summary of `launches.txt` of the folder `S` to `single_launch`. |
| 133 | `        F['single_problems'] = S['problems']` | Copies the list of the problems of the folder `S` to `single_problems`. |
| 134 | `        F['single_folder'] = S['folder']` | Copies the name of the folder `S` to `single_folder`. |
| 135 | `        if NC:` | When a folder with part NC exists, |
| 136 | `            F['nc_launch'], F['nc_problems'], F['nc_folder'] = NC['launches'], NC['problems'], NC['folder']` | its summary of `launches.txt`, its problems and its name go to `nc_launch`, `nc_problems` and `nc_folder`. |
| 137 | `    if S:` | Only when a folder with part U exists: |
| 138 | `        F['cpu41_over_cpu2_pct'] = {b: (one[41]['asct'][b]['median'] / one[2]['asct'][b]['median'] - 1) * 100 for b in SIZES}` | `cpu41_over_cpu2_pct`: one value per size. It is the median ASCT rate of CPU 41 divided by that of CPU 2, minus 1, in percent. A positive value means that CPU 41 is faster. A size without a process on one of the CPUs stops the script with an error here. |
| 139 | `    F['one'] = {str(k): v for k, v in one.items()}` | Stores the values per CPU under `one`. The CPU numbers become text keys. |
| 140 | `    F['vendor_ratio'] = {}` | `vendor_ratio`: the ratio of 8 MiB to 1 MiB for the vendor runs. It starts empty. |
| 141 | `    for name, v in B['vendor'].items():` | Starts a loop over the vendor runs of `baseline.json`, block `vendor`. |
| 142 | `        d = dict(v['sweep'])` | `d`: the one-core sweep of the run as a dictionary from the buffer size in bytes to the rate in GB/s. |
| 143 | `        F['vendor_ratio'][name] = {'m1': d[M1], 'm8': d[M8], 'ratio': d[M8] / d[M1]}` | Stores the rate at 1 MiB (`m1`), the rate at 8 MiB (`m8`) and the ratio of the second to the first. A sweep without one of the two sizes stops the script with an error. |

### Whole chip: merged folders, cell values, predictions P-B1 to P-B3, counters (lines 145 to 214)

| Line | Source | Explanation |
|---:|---|---|
| 145 | `    # ---------------- whole chip ----------------` | Comment: the block for the whole chip starts here. |
| 146 | `    Cc = None` | `Cc`: the merged many-core folders. It stays `None` when there is none. |
| 147 | `    if A['chip']:        # several whole-chip folders: every surviving process of every folder counts` | When `asct.json` holds at least one many-core folder. Comment: with several folders, every process of every folder counts that still has its result file. By the decisions file 8 result files of the first folder were overwritten, and two steps ran again in a second folder [Ref1]. |
| 148 | `        Cc = {'runs': {}, 'mix': {}, 'counted': {}, 'problems': [], 'folder': [c['folder'] for c in A['chip']], 'launches': {}}` | Starts the merged dictionary: empty `runs`, `mix`, `counted` and `problems`, the list of the folder names, and an empty `launches`. |
| 149 | `        for c in A['chip']:` | Starts a loop over the many-core folders. |
| 150 | `            for k, v in c['runs'].items():` | Starts a loop over the cells of the read processes of the folder. |
| 151 | `                Cc['runs'].setdefault(k, []).extend(v)` | Appends the processes of the cell to the cell with the same key in `Cc`. So a cell holds the processes of all folders. |
| 152 | `            for k, v in c.get('mix', {}).items():` | Starts a loop over the traffic types of the folder. |
| 153 | `                Cc['mix'].setdefault(k, []).extend(v)` | Appends its totals to the list of the same traffic type in `Cc`. |
| 154 | `            Cc['counted'].update(c['counted'])` | Copies the counted cases of the folder. A case with the same key in a later folder replaces the earlier one. |
| 155 | `            Cc['problems'] += [f'{c["folder"]}: {x}' for x in c['problems']]` | Adds the problems of the folder, each with the folder name before it. |
| 156 | `        ls = [c['launches'] for c in A['chip']]` | `ls`: the summaries of `launches.txt` of all many-core folders. |
| 157 | `        Cc['launches'] = {'n': sum(x['n'] for x in ls), 'load1_min': min(x['load1_min'] for x in ls), 'load1_max': max(x['load1_max'] for x in ls),` | The merged summary. `n`: the sum of the started processes. `load1_min`, `load1_max`: the smallest and the largest 1-minute load average at a start, over all folders. The dictionary goes on in lines 158 to 159. |
| 158 | `                          'runnable_max': max(x['runnable_max'] for x in ls), 'rc_nonzero': sum(x['rc_nonzero'] for x in ls),` | Continues line 157. `runnable_max`: the largest number of runnable tasks at a start. `rc_nonzero`: the sum of the processes with an exit status other than 0. |
| 159 | `                          'rc_count': sum(x['rc_count'] for x in ls), 'per_folder': {c['folder']: c['launches'] for c in A['chip']}}` | Ends the summary. `rc_count`: the sum of the `rc` lines. `per_folder`: the summary of each folder under its name. |
| 160 | `    chip = {}` | `chip`: the results for the whole chip. It starts empty. |
| 161 | `    if Cc:` | The block of lines 162 to 212 runs only when a many-core folder exists. |
| 162 | `        def cell(key):` | Starts the helper function `cell`. It reduces the processes of one cell to one entry. |
| 163 | `            runs = Cc['runs'].get(key)` | `runs`: the processes of the cell with this key. |
| 164 | `            if not runs:` | Without a process |
| 165 | `                return None` | the function returns `None`. |
| 166 | `            d = stat([r['total'] for r in runs])` | `d`: the median, the smallest and the largest value and the count of the totals that ASCT printed, in GB/s. |
| 167 | `            d['mesh0'] = st.median(r['mesh0'] for r in runs)` | `mesh0`: the median over the processes of the sum of the thread rates of mesh 0. |
| 168 | `            d['mesh1'] = st.median(r['mesh1'] for r in runs)` | `mesh1`: the same for mesh 1. |
| 169 | `            for m in ('thr0', 'thr1'):` | Starts a loop over the two thread ranges, `thr0` for mesh 0 and `thr1` for mesh 1. |
| 170 | `                v = [r[m] for r in runs if r[m]]` | `v`: the ranges of the processes that have threads on this mesh. Each range is the smallest, the median and the largest thread rate of one process. |
| 171 | `                d[m] = [min(x[0] for x in v), st.median(x[1] for x in v), max(x[2] for x in v)] if v else None` | The range of the cell: the smallest thread rate of any process, the median of the process medians and the largest thread rate of any process. It is `None` when no process has threads on this mesh. |
| 172 | `            d['sec'] = [min(r['sec'][0] for r in runs), max(r['sec'][1] for r in runs)]` | `sec`: the shortest and the longest measured time of a thread over all processes of the cell, in seconds. |
| 173 | `            d['floor'] = st.median(r['floor'] for r in runs)` | `floor`: the median over the processes of the lower bound that `analyze.py` computes. That bound is all bytes of a process divided by the time of its slowest thread, in GB/s. |
| 174 | `            return d` | Returns the entry. |
| 175 | `        dur = None` | `dur`: the length of the measured phase of the main runs, as the text of the file names. It starts as `None`. |
| 176 | `        for k in Cc['runs']:` | Starts a loop over the keys of the cells. |
| 177 | `            if k.startswith('6456.n0.d') and not k.endswith('d0.25'):` | Looks for a cell at 64+56 with 0 injected NOPs whose length is not `0.25`. |
| 178 | `                dur = k.split('.d', 1)[1]` | Takes the text after `.d` of such a key as `dur`. With several such lengths the last one is kept. |
| 179 | `        chip['dur'] = dur` | Stores `dur`. |
| 180 | `        chip['base'] = cell(f'6456.n0.d{dur}')` | `base`: the cell at 64+56 with 0 injected NOPs and the length `dur`. |
| 181 | `        chip['default'] = cell('6456.n0.d0.25')` | `default`: the cell at 64+56 with 0 injected NOPs and a measured phase of 0.25 s, which is the default of ASCT. |
| 182 | `        chip['nops'] = {n: cell(f'6456.n{n}.d{dur}') for n in NOPS if cell(f'6456.n{n}.d{dur}')}` | `nops`: one entry per count of injected NOPs that has a process at 64+56 with the length `dur`. The entry of the count 0 equals `base`. |
| 183 | `        chip['layouts'] = {lay: {n: cell(f'{lay}.n{n}.d{dur}') for n in (0, 20)} for lay in ('6400', '0056', '5656')}` | `layouts`: for each of the layouts `6400`, `0056` and `5656` the cells with 0 and with 20 injected NOPs. A cell without a process is `None`. |
| 184 | `        fast = [n for n in NOPS if 1 <= n <= 40 and n in chip['nops'] and chip['nops'][n]['median'] >= 459]` | `fast`: the counts of injected NOPs from 1 to 40 whose median total is 459 GB/s or more. |
| 185 | `        chip['PB1'] = None if not chip['base'] else chip['base']['median'] < 334` | `PB1`: the verdict of prediction P-B1. The prediction says that the median ASCT total at 64+56 with 0 injected NOPs is below 334 GB/s. The value is `True` when the median of `base` is below 334, and `None` without the cell. |
| 186 | `        chip['PB1_fail_hard'] = bool(chip['base'] and chip['base']['median'] >= 459)` | `PB1_fail_hard`: `True` when that median is 459 GB/s or more. By the decisions file the prediction fails in this case. A median from 334 to below 459 GB/s gives `False` in both fields. |
| 187 | `        chip['PB2'] = bool(fast)` | `PB2`: the verdict of prediction P-B2. It is `True` when at least one count from 1 to 40 is in `fast`. |
| 188 | `        chip['fastN'] = fast` | `fastN`: the list `fast`. |
| 189 | `        best = max(chip['nops'], key=lambda n: chip['nops'][n]['median']) if chip['nops'] else None` | `best`: the count of injected NOPs with the highest median total. The count 0 takes part. `None` when `nops` is empty. |
| 190 | `        chip['bestN'] = best` | Stores it as `bestN`. |
| 191 | `        l64, l56 = chip['layouts']['6400'][0], chip['layouts']['0056'][0]` | `l64`, `l56`: the cells with 0 injected NOPs of the layouts 64+0 and 0+56. |
| 192 | `        chip['PB3'] = {'6400': None if not l64 else 348.0 * 0.95 <= l64['median'] <= 351.0 * 1.05,` | `PB3`: the verdict of prediction P-B3 for the two layouts. For 64+0 it is `True` when the median total lies between 348.0 times 0.95 and 351.0 times 1.05, which is 330.6 to 368.55 GB/s. It is `None` without the cell. The dictionary goes on in line 193. |
| 193 | `                       '0056': None if not l56 else 318.0 * 0.95 <= l56['median'] <= 321.7 * 1.05}` | Continues line 192. For 0+56 it is `True` when the median total lies between 318.0 times 0.95 and 321.7 times 1.05, which is 302.1 to 337.785 GB/s. The four numbers 348.0, 351.0, 318.0 and 321.7 are the values of 2026-11-15 that the decisions file names. |
| 194 | `        chip['mix'] = {t: stat(v) for t, v in Cc.get('mix', {}).items()}` | `mix`: for each traffic type the median, the smallest and the largest value and the count of the totals, in GB/s. |
| 195 | `        cnt = {}` | `cnt`: the counters of the counted many-core cases. It starts empty. |
| 196 | `        for key, cc in Cc['counted'].items():` | Starts a loop over the counted cases, such as `6456.n0`. |
| 197 | `            ev = {}` | `ev`: the values of this case by event name. It starts empty. |
| 198 | `            for name, per_set in cc['ev'].items():` | Starts a loop over the events. `per_set` holds one entry for each event set that counted the event. |
| 199 | `                m0 = [v['mesh0'][1] for v in per_set.values() if v['mesh0']]` | `m0`: the median over the threads of mesh 0, one value per set. |
| 200 | `                m1 = [v['mesh1'][1] for v in per_set.values() if v['mesh1']]` | `m1`: the same for mesh 1. |
| 201 | `                lo0 = [v['mesh0'][0] for v in per_set.values() if v['mesh0']]` | `lo0`: the smallest value of a thread of mesh 0, one per set. |
| 202 | `                hi0 = [v['mesh0'][2] for v in per_set.values() if v['mesh0']]` | `hi0`: the largest value of a thread of mesh 0, one per set. |
| 203 | `                lo1 = [v['mesh1'][0] for v in per_set.values() if v['mesh1']]` | `lo1`: the smallest value of a thread of mesh 1, one per set. |
| 204 | `                hi1 = [v['mesh1'][2] for v in per_set.values() if v['mesh1']]` | `hi1`: the largest value of a thread of mesh 1, one per set. |
| 205 | `                ev[name] = {'mesh0': st.median(m0) if m0 else None, 'mesh1': st.median(m1) if m1 else None,` | Stores the event. `mesh0`, `mesh1`: the median over the sets of the thread medians of each mesh, as a count per line. For an event that one set counted, this is the thread median of one process. The dictionary goes on in line 206. |
| 206 | `                            'r0': [min(lo0), max(hi0)] if m0 else None, 'r1': [min(lo1), max(hi1)] if m1 else None}` | Continues line 205. `r0`, `r1`: the smallest and the largest value of any thread of mesh 0 and of mesh 1, over all sets. `None` for a mesh without a value. |
| 207 | `            cnt[key] = {'ev': ev, 'totals': {s: v['total'] for s, v in cc['sets'].items()},` | Stores the case: the events, and `totals`, the total in GB/s that ASCT printed for the process of each set. The dictionary goes on in line 208. |
| 208 | `                        'mesh0': {s: v['mesh0'] for s, v in cc['sets'].items()}, 'mesh1': {s: v['mesh1'] for s, v in cc['sets'].items()}}` | Continues line 207. `mesh0`, `mesh1`: the sum of the thread rates of each mesh for the process of each set. |
| 209 | `        chip['cnt'] = cnt` | Stores the counted cases under `cnt`. |
| 210 | `        F['chip_launch'] = Cc['launches']` | Copies the merged summary of `launches.txt` to `chip_launch`. |
| 211 | `        F['chip_problems'] = Cc['problems']` | Copies the merged problems to `chip_problems`. |
| 212 | `        F['chip_folder'] = Cc['folder']` | Copies the list of the folder names to `chip_folder`. |
| 213 | `    F['chip'] = chip` | Stores the results for the whole chip under `chip`. Without a many-core folder it is an empty dictionary. |

### Mesh counters and the output file (lines 215 to 236)

| Line | Source | Explanation |
|---:|---|---|
| 215 | `    # ---------------- mesh counters (root) ----------------` | Comment: the block for the mesh counters starts here. Reading them needs root. |
| 216 | `    mesh = {}` | `mesh`: the values per tag. It starts empty. |
| 217 | `    for Mm in A['mesh']:` | Starts a loop over the mesh-counter folders of `asct.json`. In the `asct.json` of this folder the list is empty, and `facts.json` holds an empty `mesh` [Ref2]. |
| 218 | `        for tag, t in Mm['tags'].items():` | Starts a loop over the tags of the folder. |
| 219 | `            per = {}` | `per`: the values of the tag by event name. |
| 220 | `            for name, d in t['ev'].items():` | Starts a loop over the events of the tag. |
| 221 | `                if name == 'dtc_cycles':` | The event `dtc_cycles` |
| 222 | `                    continue` | is skipped, so it gets no value per line. The script `run_mesh.sh` counts this event of both mesh units in every counting window, before the events of the set. The Linux documentation of the mesh counters names a cycle counter that belongs to the DTC node of a mesh [Ref3]. |
| 223 | `                row = {}` | `row`: the values of this event. |
| 224 | `                for m in ('mesh0', 'mesh1'):` | Starts a loop over the two meshes. |
| 225 | `                    if m in d:` | When the event has a count for this mesh: |
| 226 | `                        row[m + '_per_s'] = d[m]['count'] / d[m]['sec']` | `mesh0_per_s` or `mesh1_per_s`: the count divided by the seconds that the counter ran. So it is in events per second. |
| 227 | `                        if t['rate']:` | Only when the tag has a rate. A tag has a rate when a process ran for it. |
| 228 | `                            row[m] = d[m]['count'] / (t['rate'] * 1e9 / 64 * d[m]['sec'])` | `mesh0` or `mesh1`: the count per line. The divisor is the number of lines of the window. It is the total rate of the process in bytes per second (`rate` times 1e9), divided by 64 bytes per line, times the seconds that the counter ran. So the lines of the window are an estimate from the total that the process printed for its measured phase. |
| 229 | `                per[name] = row` | Stores the row under the event name. |
| 230 | `            mesh[tag] = {'spec': t['spec'], 'rate': t['rate'], 'ev': per, 'folder': Mm['folder']}` | Stores the tag: its settings, its rate, its events and the name of its folder. |
| 231 | `        F.setdefault('mesh_problems', []).extend(f'{Mm["folder"]}: {p}' for p in Mm['problems'])` | Adds the problems of the folder to `mesh_problems`, each with the folder name before it. |
| 232 | `        F.setdefault('mesh_launch', {})[Mm['folder']] = Mm['launches']` | Stores the summary of `launches.txt` of the folder in `mesh_launch` under the folder name. |
| 233 | `    F['mesh'] = mesh` | Stores the values per tag under `mesh`. |
| 234 | `    F['prep'] = A['prep'][0] if A['prep'] else None` | `prep`: the entry of the first folder of the preparation script `prep.sh` in `asct.json`, or `None` when it holds no such folder. The entry holds the folder name and the whole texts of the files `env.txt`, `sha.txt` and `resolve.txt` of that folder. |
| 235 | `    json.dump(F, open(sys.argv[3], 'w'), indent=1)` | Writes `F` as JSON to the file of argument 3. JSON has text keys only. So every number that is a key in this file, such as a size, a CPU or a count of injected NOPs, is a text key in the output file. |

### The short console view (lines 237 to 255)

| Line | Source | Explanation |
|---:|---|---|
| 237 | `    # short console view` | Comment: a short view for the console follows. |
| 238 | `    for cpu in CPUS:` | Starts a loop over the two CPUs. |
| 239 | `        c = one.get(cpu)` | `c`: the values of the CPU. |
| 240 | `        if not c:` | A CPU without values |
| 241 | `            continue` | is skipped. |
| 242 | `        print(f'CPU {cpu}: ASCT 1 MiB {c["asct"][M1]["median"]:.2f} 8 MiB {c["asct"][M8]["median"]:.2f} ratio {c["ratio_asct"]:.3f} '` | Prints one line for the CPU: the median ASCT rate at 1 MiB and at 8 MiB with 2 decimals, and their ratio with 3 decimals. The text goes on in line 243. |
| 243 | `              f'P-A1 {c["PA1"]}; new ratio {c["ratio_new"]:.3f}; old ratio {c["ratio_old"]:.3f}; fit {c.get("fit")}; new fit {c["fit_new"]}')` | Continues line 242: the verdict of P-A1, the ratio of the new and of the old read kernel, the fit of the ASCT loop and the fit of the new read kernel. |
| 244 | `        print('   GHz', c['ghz'], 'counted vs plain max %', c['counted_vs_plain_maxpct'])` | Prints the range of the clock rate in GHz and the largest distance in percent between the counted and the uncounted rate. |
| 245 | `    print('R-A3 different at 8 MiB:', F.get('RA3_different'), 'of', F.get('RA3_counted'))` | Prints the prefetch counters that rule R-A3 calls different at 8 MiB, and the counters that it judged. |
| 246 | `    print('P-A4', F.get('PA4'), {k: (round(v[M1]['median'], 1), round(v[M8]['median'], 1), round(v['ratio'], 3)) for k, v in F.get('pad', {}).items()})` | Prints the verdict of P-A4. For each row of `pad` it prints the median rate at 1 MiB and at 8 MiB with 1 decimal and the ratio with 3 decimals. |
| 247 | `    if chip:` | When results for the whole chip exist: |
| 248 | `        print('chip base', chip['base'], 'P-B1', chip['PB1'], 'P-B2', chip['PB2'], chip['fastN'], 'best N', chip['bestN'], 'P-B3', chip['PB3'])` | prints the cell `base`, the verdicts of P-B1 and P-B2, the list `fastN`, the best count of injected NOPs and the verdict of P-B3, |
| 249 | `        print('nops', {n: round(v['median'], 1) for n, v in chip['nops'].items()})` | prints the median total for each count of injected NOPs, with 1 decimal, |
| 250 | `        print('mix', {t: round(v['median'], 1) for t, v in chip['mix'].items()})` | and prints the median total for each traffic type, with 1 decimal. |
| 251 | `    print('mesh tags', list(mesh))` | Prints the list of the tags with mesh counters. |
| 254 | `if __name__ == '__main__':` | Runs the next line only when the file is started as a script, not when another file loads it. |
| 255 | `    main()` | Calls `main`. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`: the sections "Predictions and rules (fixed now)", "Readings fixed now", "Added 2026-11-16 20:45 UTC" (P-A4), "Added 2026-11-16 23:23 UTC" (P-A5) and "Record of 2026-11-16 23:50 UTC" (the defect of `run_chip.sh` and the second many-core folder).
- [Ref2] `asct.json` and `facts.json` in the folder `asct-2026-11-16`: the list `mesh` of the first file has no entry, and the dictionary `mesh` of the second file is empty.
- [Ref3] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": the cycle counter of the DTC node.
