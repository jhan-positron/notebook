# How to read `whole-chip-rerun-7200.html`

## Short version

`whole-chip-rerun-7200.html` is the report page of the whole-chip read rerun of 2026-11-17: a memory read benchmark with 120 threads on CRB (an Arm reference server), run at a memory speed of 7200 MT/s (million transfers per second, the unit of memory speed).
The script `make_report.py` built it from `facts.json` (the data file with one record per timed measurement), and the header of the script states the rule that no measured number is typed by hand.
It holds 2 figures and 6 numbered tables, and every rate on it is in GB/s (1 GB = 1e9 bytes).

## What this file is

Explained file: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html`

Short forms of folders in this text:

- `C` = `/home/jhan/workspace/titan/cache-perf/crb`
- `R` = `C/results` (the result folders that were copied back from the test machine)
- `S` = `C/tmp/agent-scratch/w120-7200-2026-11-17` (the run scripts and the analysis scripts of the rerun)

Terms such as part A, pool, drop or n are defined in the folded list "Words used here" near the end.

- It is the last output of the analysis. The chain is:

```
raw csv files in R
  |  build_facts.py and its three helper scripts
  v
facts.json (793 interval records) and FACTS.md
  |  make_report.py
  v
whole-chip-rerun-7200.html (this page)
```

- `S/build_facts.py` wrote `facts.json` and `FACTS.md` from the raw files [Ref17].
- Writer of the page: `S/make_report.py` [Ref1]. The script runs from top to bottom and takes no options.
- The script writes the page only when every one of its self-checks passes. If one check fails, it prints "NOT WRITTEN" and ends with exit status 1 [Ref12]. A failed count or raw-file check stops the script even earlier, with a line that starts with "make_report.py: STOP:" [Ref3].
- Size: 425796 bytes in 1146 lines. File time: 2026-11-18 04:55:01 UTC.
- The page is one self-contained file. It has one light theme, no script and no external file [Ref12].
- Do not edit the page by hand. The header of the script says: "Edit this file, never the HTML" [Ref1].
- A line of the HTML file is not a data record. So this text explains the page by its parts, its figures and its tables.

The three sentences of the Short version of the page (line 110) are the result of the rerun:

- The new read kernel read 29.7 % to 31.2 % less than the old read kernel in 8 pairs of 6 s measurements.
- For the old read kernel, no difference from the 8000 MT/s runs was seen in parts A and C. In part L it was lower by 0.3 % (nearest ends of the two ranges, in percent of the lower end of the 8000 MT/s range) and by 1.3 % (medians, in percent of the 8000 MT/s median).
- The load-only loop gave higher rates than the 8000 MT/s runs in all 4 comparisons of the rerun. The data do not show that the memory speed caused either difference.

## Parts of the page, in order

The page names two questions (line 116):

- Q1: is the whole-chip read rate of the new read kernel still below that of the old read kernel at 7200 MT/s, and by how much.
- Q2: did the rate of either kernel differ from the earlier runs at 8000 MT/s.

| Part | Lines of the HTML file | What it holds |
|---|---|---|
| Title and subtitle | 105 to 106 | Date, machine, 120 threads on CPUs 0-119, 256 MiB per thread, 12 memory modules at 7200 MT/s |
| Short version | 108 to 113 | 3 sentences (the answers to Q1 and Q2) and 5 bullets with more detail |
| Words used here | 115 to 117 | A folded list of 58 entries. One entry can define several terms |
| Section 1, "Is the new read kernel still below the old one? (Q1)" | 119 to 703 | 4 bullets, Figure 1, Table 1, 2 bullets, and the folded "Table view of Figure 1: every row" |
| Section 2, "Did a rate differ from the 8000 MT/s runs? (Q2)" | 705 to 1128 | 4 bullets, Figure 2, Table 2 with 6 notes, a sub-section with 3 bullets, Table 3, Table 4, and the folded "Table view of Figure 2: every interval" |
| Section 3, "What the data do not show" | 1130 to 1131 | 6 bullets. Each starts with "Insufficient data:" and names the measurement that would resolve it |
| Section 4, "Machine state and system load" | 1133 to 1138 | Table 5 (machine state) and Table 6 (system load) |
| References | 1140 to 1143 | 76 entries, numbered Ref1 to Ref76 in the list of the page. Each entry is a file path and a note on what the file holds. Ref2 of the page names `S/go.sh`. Line 20 of that file was edited on 2026-11-24, after the page was built. The edit changed the text of one message. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit |

## How a number on this page is computed

All formulas are in `make_report.py`.

| Value | Formula | Reference |
|---|---|---|
| Rate of one interval, part A (binaries bw_old and bw_new) | The column `aggregate_GBps` of the interval row of the csv file. The csv header defines it as sum(bytes) / max(per-thread elapsed_s), with GB = 1e9 bytes | [Ref2] [Ref16] |
| Rate of one interval, runner bwx12 (and the older runner bwx) | For each of the 120 thread rows of the interval: the bytes of the thread / the elapsed_s of the same thread / 1e9. The 120 results are added. It is not the rate that the interval row prints. The csv header defines that rate as sum(bytes) / max(per-thread elapsed_s) | [Ref2] [Ref15] |
| Median | The middle value of the sorted list. For an even number of values it is the mean of the two middle values | [Ref3] |
| Drop, % | (1 - load-only rate / old-kernel rate) x 100 | [Ref6] |
| Range | The lowest and the highest interval of a list of intervals | [Ref4] |
| Overlap of two ranges | "yes" when the ranges share at least one value: low1 <= high2 and low2 <= high1 | [Ref4] |
| Distance of the nearest ends, GB/s | 0 when the ranges overlap. Otherwise the lowest value of the higher range minus the highest value of the lower range. The sign is + when the 7200 MT/s range is the higher one | [Ref4] |
| Distance of the farthest ends, GB/s | The larger of (high1 - low2) and (high2 - low1) | [Ref4] |
| Width of a range, % | (high - low) / low x 100. The page calls it the size that the test cannot exclude | [Ref7] |
| Percent of a distance (old read kernel, part L against the pool L-1 to L-4) | Nearest ends: the distance without its sign / the lowest value of the 8000 MT/s range x 100. Medians: (8000 MT/s median - 7200 MT/s median) / 8000 MT/s median x 100. These are the 0.3 % and the 1.3 % of the Short version of the page | [Ref7] |
| Rounding | Rates to 0.01 GB/s and percent values to 0.1 %, rounded half up. A distance is computed from the rates before rounding | [Ref3] [Ref4] |

The two kinds of rate use different divisions:

- The part A rate divides the bytes of all threads by the longest thread time.
- The bwx12 rate adds 120 thread rates. Each thread rate uses the elapsed time of its own thread.

Why the bwx12 rate is a sum of thread rows:

- `facts.json` defines the rate of a bwx12 record as this sum of thread rates (its field `meta.rate_kinds`) [Ref14].
- `facts.json` holds each bwx12 rate rounded to 0.001 GB/s. Rounding such a value again to 0.01 GB/s can change the last digit (page line 1143, entry Ref75 of the reference list of the page).
- So the script sums the 120 thread rows of the csv file and rounds the sum once [Ref2].
- The script stops when the 120 lines after the interval row are not the thread rows of this interval. It also stops when the sum, rounded to 0.001 GB/s, is not the value of the record in `facts.json` [Ref2].
- The page states that this sum differs from the rate printed in the interval row by at most 0.02 GB/s (line 696). The script stops when one difference is above 0.02 GB/s [Ref2].
- Example: line 128 of `R/w120-T72L1-20261117T221329Z/a6456.csv` is `I,0,0,oldread,268435456,120,2773875687424,6.000276,462.29`. The sum of the 120 thread rows after it is 462.30 GB/s (my recomputation). The page shows 462.30 [Ref15].

What the page does not decide:

- The page does not time anything. The benchmark programs wrote the bytes and the elapsed times into the csv files.
- This text therefore says nothing about what a timed interval includes. The source of the benchmark programs answers that.

## Figure 1 (lines 121 to 697): old read kernel against load-only loop, per process

Kind of chart: a dumbbell chart. One row holds two dots that a line joins.

The page holds this chart three times: 940 px, 726 px and 386 px wide (lines 123, 304 and 490).
The style block shows one of the three, by the width of the window (lines 73 to 75):

- 1000 px or wider: the 940 px drawing.
- 780 px to 999 px: the 726 px drawing.
- Below 780 px: the 386 px drawing. There the row name stands above its two dots.

All three drawings show the same 21 rows and the same 42 dots.

### What one row is

One row is one bwx12 process (first block), or one round of the two part A binaries (second block).

| Block (grey title bar) | Group | Rows | Kernel of the orange dot |
|---|---|---|---|
| "6 s measurements, runner bwx12, all threads stop together" | 8000 MT/s, hollow markers | 1 row: L-1 | asmread |
| same block | 7200 MT/s, filled markers | 10 rows: F72d12. Part L, sessions 1 to 3 (T72L1 to T72L3). Part C, T72C1 to T72C4. Control I, T72I1 and T72I2 | asmread for F72d12, part L and control I. Kernel `read` of bwx12 (the new read kernel) for part C |
| "0.5 s measurements, the two binaries of 2026-11-13, each thread finishes its pass" | 8000 MT/s, hollow markers | 4 rows: A-1 round 1, A-1 round 2, A-2 round 1, A-2 round 2 | `read` of bw_new (the new read kernel) |
| same block | 7200 MT/s, filled markers | 6 rows: part A, sessions 1 to 3, rounds 1 and 2 | `read` of bw_new (the new read kernel) |

- A bwx12 row has 2 intervals per kernel: rounds 0 and 1 of one process.
- A part A row has 3 intervals per kernel: the 3 intervals of one bw_old process and the 3 intervals of one bw_new process [Ref6].
- So the orange dot is the new read kernel itself in 14 rows, and asmread in its place in 7 rows.

### Axis

- X axis: whole-chip read rate in GB/s, from 0 to 500. One grid line per 100 GB/s. The axis starts at 0.
- There is no Y axis. The rows stand one under the other in the order of the table above.

### What one mark is

| Mark | Meaning | Unit |
|---|---|---|
| Blue dot | Median of the old-read-kernel intervals of the row | GB/s, read on the x axis |
| Orange dot | Median of the load-only intervals of the row | GB/s, read on the x axis |
| Number beside a dot | The same median with 2 decimals | GB/s |
| Hollow dot | The row ran at 8000 MT/s | - |
| Filled dot | The row ran at 7200 MT/s | - |
| Black bar with two end ticks through a dot | Lowest to highest interval of that kernel in the row, drawn to scale. It is often narrower than the dot | GB/s |
| Grey line between the two dots, with a percent above it | Drop of the load-only loop below the old read kernel | % |
| Tooltip of a dot (the text that appears when the pointer rests on the mark) | Row name, kernel, median, every interval, n, the csv file and the line numbers of the source rows | - |
| Tooltip of the grey line | Row name, the drop, how the drop was computed, the number of pairs, the csv file and the line numbers of the source rows | - |

How the percent is computed [Ref6] [Ref9]:

- bwx12 row: a pair is one load-only interval and the old-kernel interval of the same process and round. The row has 2 pairs. The text gives the lowest and the highest drop of the 2 pairs, for example "30.3 % to 30.4 %". It gives one value when both drops round to the same 0.1 %.
- Part A row: the row has one drop. It is computed between the median of the bw_new process and the median of the bw_old process.
- So in a bwx12 row the percent is not computed from the two dots. The dots are medians, and the percent comes from the pairs.

Sample tooltip (line 188 of the page, blue dot of row "Part C, T72C1 (cfwd)"):

```
Part C, T72C1 (cfwd), kernel read = the new read kernel, after oldread: oldread (old read kernel). Median 465.78 GB/s. Intervals: 466.01, 465.54 GB/s. n = 2 intervals / 1 process. Source: R/w120-T72C1-20261117T221436Z/cfwd.csv, interval rows in lines 128, 1214. Each rate is the sum of the 120 thread rows after its interval row.
```

Under the chart:

- Line 695 is the caption. It says that in the 6 rows of the part L argument line at 7200 MT/s the blue dot stays at nearly the same place and the orange dot moves.
- Line 696 holds three reading notes. One of them says that the data of both figures come from `facts.json`.

## Figure 2 (lines 707 to 1117): every interval against the 8000 MT/s range

Kind of chart: two strip plots (panels). A strip plot draws every value of a row as one dot on a common axis. The two panels stand side by side when the window is wide enough.

- First panel "Old read kernel" (from line 711): 70 blue dots. 32 are hollow (8000 MT/s) and 38 are filled (7200 MT/s).
- Second panel "Load-only loop" (from line 891): 69 orange dots. 23 are hollow and 46 are filled.
- One dot is one interval. The figure shows 139 intervals (line 891).

### Axes

| Panel | X axis | Labelled ticks | Thin grid lines |
|---|---|---|---|
| Old read kernel | Whole-chip read rate, GB/s, from 458 to 476 | 460, 464, 468, 472, 476 | Every 2 GB/s |
| Load-only loop | Whole-chip read rate, GB/s, from 276 to 340 | 280, 300, 320, 340 | Every 10 GB/s |

- Neither axis starts at 0. A break mark at the left end of each axis line shows this.
- The two panels have different scales. The first panel shows 18 GB/s over its width. The second panel shows 64 GB/s over the same width. So the same distance on the screen is 3.6 times as many GB/s in the second panel (line 709).
- There is no Y axis. The height of a dot inside its row carries no value. The script moves a dot up or down only so that it does not cover another dot [Ref10].

### What one row is

One row holds all intervals of one named group: one 8000 MT/s row of the list, F72d12, one part of the rerun, control I, one group of part C, or one session of part A. In the two 0.5 s blocks of the second panel a row holds the intervals of one round only. The number in brackets is the number of dots of the row.

Panel "Old read kernel":

| Block | Grey band | 8000 MT/s rows (hollow) | 7200 MT/s rows (filled) |
|---|---|---|---|
| "6 s measurements, bwx12 oldread" | Rows L-1 to L-4, oldread at position 0: 465.53 to 470.05 GB/s, 11 intervals | L-1 (2), L-2 (4), L-3 (2), L-4 (3) | F72d12 (2), part L (6), part C (8), control I (4) |
| "0.5 s measurements, bw_old read" | Rows A-1 to A-3: 463.58 to 469.03 GB/s, 21 intervals | A-1 (6), A-2 (6), A-3 (9) | Part A session 1 (6), session 2 (6), session 3 (6) |

Panel "Load-only loop":

| Block | Grey band | 8000 MT/s rows (hollow) | 7200 MT/s rows (filled) |
|---|---|---|---|
| "6 s measurements, bwx12" | Rows L-1 to L-4, asmread at position 1: 288.54 to 309.17 GB/s, 11 intervals | L-1 (2), L-2 (4), L-3 (2), L-4 (3) | Compared with the band: F72d12 (2), part L (6), part C "asmread after oldread" (2), control I (4). Not compared, no band: part C `read` after oldread (4), `read` after asmread (4), asmread after `read` (4), asmread as first interval of the process (2) |
| "0.5 s measurements, bw_new read, round 1" | Rows A-1 and A-2 of round 1: 279.66 to 297.34 GB/s, 6 intervals | A-1 (3), A-2 (3) | Part A session 1 (3, compared), session 2 (3), session 3 (3) |
| "0.5 s measurements, bw_new read, round 2" | Rows A-1 and A-2 of round 2: 294.02 to 316.31 GB/s, 6 intervals | A-1 (3), A-2 (3) | Part A session 1 (3, compared), session 2 (3), session 3 (3) |

- The first panel has 14 rows and 2 grey bands. The second panel has 22 rows and 3 grey bands.
- Rows L-2 to L-4 are 4 s measurements. Their row names say "(4 s)". All other bwx12 rows are 6 s measurements.

### What one mark is

| Mark | Meaning | Unit |
|---|---|---|
| Blue dot (first panel) | One interval of the old read kernel: `read` of bw_old, or `oldread` of bwx12 | GB/s, read on the x axis |
| Orange dot (second panel) | One interval of the load-only loop: `read` of bw_new, `read` of bwx12, or asmread | GB/s, read on the x axis |
| Hollow dot, filled dot | 8000 MT/s, 7200 MT/s | - |
| Grey band | Lowest to highest interval of the 8000 MT/s rows of the block | GB/s |
| Text under a row name | "lowest to highest, GB/s (n intervals)" of the row | GB/s |
| Bold text under a 7200 MT/s row name | The place of the row relative to the band: "inside the band", "overlaps the band", "x GB/s lower (left of the band)" or "x GB/s higher (right of the band)". The number is the distance of the nearest ends | GB/s |
| Tooltip of a dot | bwx12 dot: row, kernel, process, round, position, the kernel that ran directly before, the rate, the range and n of the row, the csv file and the line of the source row. Part A dot: the tooltip names the process by its number in the csv file, and it gives the round and the number of the interval. It gives no position and no kernel before. A dot of row A-3 gives the tag of the process and no round | - |
| Tooltip of a band | The range of the band, its n, and the csv files of its rows | - |

- A 7200 MT/s row without bold text is not compared with a band (line 891).
- The row "Part L" of the first panel has one more bold line. It gives the distance of the medians: "medians: 6.27 GB/s lower".
- In the two 0.5 s blocks of the second panel only session 1 is compared, each round against the same round. Sessions 2 and 3 carry the text "used for Q1 only (rule V3)" [Ref8].

Sample tooltip (line 975 of the page, an orange dot of row "Part L"):

```
Part L, 12.48 GB/s higher (right of the band): asmread (in place of the new read kernel), process T72L1, round 0, position 1, directly after oldread: 321.76 GB/s. Row: 321.65 to 327.93 GB/s, n = 6 intervals / 3 processes. Source: R/w120-T72L1-20261117T221329Z/a6456.csv, interval row in line 490. The rate is the sum of the 120 thread rows after it.
```

Near the chart:

- Line 891 holds four reading notes. They stand under the first panel.
- Line 1116 is the caption. It says that in the panel "Old read kernel" every 7200 MT/s row overlaps the grey band of its block, except part L.
- The caption also says that in the panel "Load-only loop" every 7200 MT/s row that is compared with a band lies to the right of it (higher), except F72d12.

## Tables

The form of n:

- 7200 MT/s rows: intervals / processes / sessions / boots. Example: "6 intervals / 3 processes / 3 sessions / 1 boot".
- "No session" marks a row that is not part of a session of go.sh (control I and F72d12).
- "1 extra process" is T72C4, the part C process that go.sh ran after session 3.
- 8000 MT/s rows: intervals / processes / boots.

### Table 1 (line 699): the drop per part

One row is one group of pairs. A pair is one load-only value and one old-kernel value that belong together.
The table has 8 data rows in 3 groups, and one note.

| Group | Rows |
|---|---|
| "7200 MT/s, the planned rerun" | Part C, `read` directly after oldread. Part C, `read` directly after asmread. Part L, asmread. Part A, bw_new read against bw_old read |
| "7200 MT/s, same boot, not part of the planned rerun" | Control I. F72d12 |
| "8000 MT/s, for context only (same computation)" | L-1. A-1 and A-2 |

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Part and pair | - | The part, the load-only kernel, its position, the kernel that ran directly before it, and the processes |
| 2 | Lowest drop, % | % | The smallest drop of the pairs of the row |
| 3 | Highest drop, % | % | The largest drop of the pairs of the row |
| 4 | Old read kernel, GB/s | GB/s | Lowest to highest old-kernel interval of the pairs. In the two part A rows: lowest to highest median of the bw_old processes |
| 5 | Load-only loop, GB/s | GB/s | Lowest to highest load-only interval of the pairs. In the two part A rows: lowest to highest median of the bw_new processes, given per round |
| 6 | n | - | Pairs / processes / sessions / boots |

- In the bwx12 rows a pair is two intervals of the same process and round.
- In the 7200 MT/s part A row a pair is the median of one bw_new process and the median of the bw_old process of the same session and round. In the row "A-1, A-2" it is the two medians of the same 8000 MT/s row (A-1 or A-2) and round [Ref6] [Ref11].
- First data row, copied from line 699: 30.5 | 31.2 | 465.54 to 467.83 | 320.89 to 324.98 | 4 pairs / 2 processes / sessions 1 and 3 / 1 boot.

### Table view of Figure 1 (line 702, folded)

One row is one row of Figure 1. The table has 21 data rows under 4 group lines.

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Row | - | The row name of Figure 1 with its notes |
| 2 | Old read kernel: median, GB/s | GB/s | The value of the blue dot |
| 3 | Its intervals, GB/s | GB/s | Every old-kernel interval of the row, in the order of launch time and interval number [Ref4] |
| 4 | Load-only loop: median, GB/s | GB/s | The value of the orange dot |
| 5 | Its intervals, GB/s | GB/s | Every load-only interval of the row, in the same order |
| 6 | Drop | % | The percent text of the row in Figure 1 |

### Table 2 (line 1119): 7200 MT/s against 8000 MT/s

One row is one comparison: one 7200 MT/s row against 8000 MT/s rows of the list in the rules file.
The table has 12 data rows in 2 blocks, and 6 notes.

| Block | Rows |
|---|---|
| "Old read kernel" (5 rows) | Part A (bw_old read). Part C (oldread). Part L (oldread at position 0). F72d12 (oldread). Control I (oldread) |
| "Load-only loop" (7 rows) | Part L (asmread at position 1). Part A session 1 round 1 (bw_new read). Part A session 1 round 2 (bw_new read). Part C kernel `read`. Part C asmread directly after oldread. F72d12 (asmread). Control I (asmread) |

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | 7200 MT/s row | - | The part, the kernel and the position of the 7200 MT/s intervals |
| 2 | Range at 7200 MT/s, GB/s, and n | GB/s | Lowest to highest interval of the 7200 MT/s row, and its n |
| 3 | 8000 MT/s rows: range, GB/s, and n | GB/s | Which 8000 MT/s rows are used, their lowest to highest interval, and their n. The cell says "no bwx12 run" for kernel `read` of part C |
| 4 | Overlap | yes or no | "yes" when the two ranges share at least one value. "-" in the row of kernel `read` of part C |
| 5 | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | GB/s | 0 when the ranges overlap. Otherwise the gap between the two ranges, with its sign. "-" in the row of kernel `read` of part C |
| 6 | Wording by the rules fixed before the run | - | The fixed wording of the result, and remarks |

The wording in column 6 [Ref7] [Ref8] [Ref18]:

- Overlap: "no difference seen". The cell adds the width of the 8000 MT/s range as the size that the test cannot exclude.
- No overlap: "differs between the 8000 MT/s boot and the 7200 MT/s boot".
- The two part A rows of the new read kernel use the wording of rule V3: "outside (above) the 8000 MT/s range of the same round". These cells also give the pass counts.
- Kernel `read` of part C: "Insufficient data: no 8000 MT/s run of kernel read with bwx12".

Where a row has an 8000 MT/s side, it is one of three sets:

- "pool A-1 to A-3": 21 intervals of bw_old read from 7 processes.
- "pool L-1 to L-4": 11 intervals from 7 processes, oldread at position 0 or asmread at position 1.
- "A-1 and A-2, round 1" or "round 2": 6 intervals of bw_new read from 2 processes.

The 6 notes under the table cover: the pool against row L-1 alone, a contradiction in the rules file about part C, row X2d12, rows of the older runner bwx, three boots with 10 memory modules, and rounding.

Rows that are not comparisons of the rerun: F72d12 and control I (caption in line 1118).

### Table 3 (line 1123): the three visits of the part L line in the 7200 MT/s boot

One row is one visit: one time at which the argument line of part L was run. The table has 3 rows: F72d12, part L, control I.

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Visit | - | Name of the visit |
| 2 | Launch, UTC | time of day | Launch time of the process, or the first and the last launch time when the visit has several processes |
| 3 | Start state | - | What ran before the launch, the 1-minute load average at launch, and the highest %CPU in the process list that was saved before the launch |
| 4 | asmread, GB/s | GB/s | Lowest to highest asmread interval of the visit (position 1) |
| 5 | oldread, GB/s | GB/s | Lowest to highest oldread interval of the visit (position 0) |
| 6 | n per kernel | - | Intervals / processes / sessions / boots |

### Table 4 (line 1125): three kinds of distance for asmread

One row is one kind of distance. The table has 3 rows and 2 value columns.

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Kind of distance | - | "Nearest ends of the two ranges", "Medians" or "Farthest ends of the two ranges" |
| 2 | Part L above the 8000 MT/s pool L-1 to L-4, GB/s | GB/s | The distance between the asmread range of part L and the asmread range of the pool |
| 3 | Part L above F72d12 (same 7200 MT/s boot, earlier run, not part of the rerun), GB/s | GB/s | The same distance between part L and F72d12 |

- Nearest ends: lowest part L value minus the highest value of the other range.
- Medians: median of part L minus the median of the other range.
- Farthest ends: highest part L value minus the lowest value of the other range [Ref4] [Ref7].

### Table view of Figure 2 (line 1127, folded)

One row is one row of Figure 2. The table has 36 data rows under 11 group lines.

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Row | - | The row name of Figure 2 with its notes |
| 2 | n intervals | count | Number of intervals of the row. It is the number of dots of the row |
| 3 | Intervals, GB/s, sorted | GB/s | Every interval of the row, from the lowest to the highest |

### Table 5 (line 1135): machine state

One row is one fact about the machine or the run. The table has 11 rows.

| No. | Column | Meaning |
|---|---|---|
| 1 | Fact | The statement, for example "12 memory modules during the rerun" |
| 2 | Proof | The raw files and the values in them that show the fact |
| 3 | Limit | What the proof does not cover. "-" when the page names no limit |

The 11 facts, in order:

1. 12 memory modules during the rerun.
2. Memory speed 7200 MT/s during the rerun.
3. The rerun is complete.
4. Logins and accounts with processes during go.sh.
5. Control I ran afterwards.
6. F72d12 belongs to boot 3bfc57a1.
7. Work before the first 120-thread process of part A.
8. Firmware settings other than the memory speed.
9. The 8000 MT/s rows: one boot, 12 modules.
10. Corrected hardware error records in the 8000 MT/s rows.
11. The lowest asmread value of the 8000 MT/s pool comes from an interval with corrected hardware error records.

### Table 6 (line 1138): system load

The table has 24 data rows in 2 groups.

- Group 1 (12 rows): one row per step. A step is one part of one session of go.sh, the extra part C process, or one process of control I. The row gives the first launch of the step.
- Group 2 (12 rows): one row per earlier row that the page shows: F72d12, A-1, A-2, A-3, L-1, L-2, L-3, L-4, two rows of the older runner bwx, X2d12, and the boots with 10 modules. The row covers the processes of that earlier row that the page uses. For A-1 and A-2 these are the 4 processes of kernel `read` of each row (2 of bw_old and 2 of bw_new). The csv file of A-1 holds 24 processes, and the csv file of A-2 holds 12 (my count of the process header lines) [Ref11]. The row gives one value per process, or the lowest and the highest value.

| No. | Column | Unit | Meaning |
|---|---|---|---|
| 1 | Step or row | - | The folder tag of the step (T72A1 to T72I2), or the name of the earlier row |
| 2 | What | - | The part and the session, or the memory speed and the number of processes |
| 3 | Launch | UTC time | Launch time. The rows of the rerun, of control I and of F72d12 give the time of day on 2026-11-17. The other rows give the date too |
| 4 | 1-minute load average at launch | number of tasks | The 1-minute load average of Linux, read directly before the launch. A part A row also lists the value of each of its 4 read processes |
| 5 | Time since the end of the previous 120-thread process of go.sh or go2.sh, s (given for their steps only) | s | Given for the steps of go.sh and go2.sh only. "-" in all other rows and in the row of the first step |

- The first launch of the rerun (T72A1) was at a load average of 0.07.
- The other 9 steps of go.sh started at a load average of 74.05 to 105.24, each 5 s after a 120-thread process of the rerun had ended (caption in line 1137).
- The page marks the cause of these high values as a hypothesis that was not tested.

## Old read kernel and new read kernel in this file

| Kernel | Name in the data | Colour | Where it is on the page |
|---|---|---|---|
| Old read kernel | `read` of the binary bw_old (part A, rows A-1 to A-3). `oldread` of bwx12 (parts L and C, control I, F72d12, rows L-1 to L-4) | Blue | Blue dots of both figures. Column 4 of Table 1. Block "Old read kernel" of Table 2. Column 5 of Table 3 |
| New read kernel | `read` of the binary bw_new (part A, rows A-1 and A-2). `read` of bwx12 (part C only) | Orange | Orange dots of the part A rows and of the part C rows named "read". Data rows 1, 2, 4 and 8 of Table 1. The part A rows and the row "Part C, kernel read" of the block "Load-only loop" of Table 2 |
| asmread, used in place of the new read kernel | `asmread` of bwx12 (parts L and C, control I, F72d12, rows L-1 to L-4) | Orange | Orange dots of the rows that say "asmread". Data rows 3, 5, 6 and 7 of Table 1 (part L, control I, F72d12, L-1). The other 4 rows of the block "Load-only loop" of Table 2. Tables 3 and 4 |

- The page uses "load-only loop" for the new read kernel or asmread.
- Kernel `read` of bwx12 has no run at 8000 MT/s. So the new read kernel itself is compared between the two memory speeds in part A only (Table 2).
- Part L never runs the new read kernel itself. It runs asmread at position 1, directly after oldread.
- In both figures a row label, a group label or a block title says which load-only kernel a row holds.

## Which code writes this file, and which code reads it

- `S/make_report.py` writes the page [Ref1] [Ref12].
- It reads `S/facts.json` for the interval records, the launch data and the fixed wordings. The two figures use 139 of the 793 interval records [Ref5] [Ref14].
- It reads `S/FACTS.md` to compare its own values with the facts sheet. A mismatch stops the page from being written [Ref1].
- It reads the raw csv files in `R` to sum the thread rows of each bwx12 interval, and to check that each record names its source row [Ref2].
- It checks the facts of Table 5 in the raw files (logs, saved logs of the Linux kernel, settings lists) before it writes them [Ref1].
- `S/test_make_report.py` runs copies of the generator on damaged copies of `facts.json`. The copies write to a temporary folder. The test does not read or change this page [Ref13].
- No script of the analysis chain reads this page. A search of the 8 Python scripts and the 3 shell scripts at the top level of `S` for the file name found it in `make_report.py` and `test_make_report.py` only.
- The same search over the sub-folders of `S` found the file name in more scripts:
  - Four sub-folders with names that start with `bak-before-` each hold a copy of `make_report.py`.
  - The sub-folders `render`, `final-check`, `review-scratch`, `r3fix-work` and `verify-vfix-r3` hold scripts that name the page. I opened two of them, and both are tools of the review of the page. `render/final_render.sh` takes screenshots of the page. `final-check/numbers/tables.py` reads the table cells of the page.
  - Insufficient data: what each of the other scripts in these five sub-folders does. Reading these scripts would resolve it.

How a final rate on the page comes from the raw columns:

- Part A: csv row `read,120,268435456,0,256087425024,0.5474,467.83,2.98,4.93,3.99` (line 4 of `R/k120-T72A1-20261117T221209Z/threads120.csv`). Its 7th field, 467.83, is the rate of the interval. The page shows it as the first interval of row "Part A, session 1, round 1" [Ref16].
- bwx12: the 120 thread rows after an interval row. For each thread row, field 7 (bytes) is divided by field 8 (elapsed_s) and by 1e9. The 120 results are added [Ref2] [Ref15].
- A dot of Figure 1 is the median of 2 or 3 such rates. A dot of Figure 2 is one such rate.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **MT/s**: million transfers per second, the unit of memory speed.
- **GB/s**: gigabytes per second. 1 GB is 1e9 bytes.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **go.sh, go2.sh**: the driver scripts. go.sh ran the planned rerun. go2.sh ran control I.
- **Rerun**: the 10 steps that go.sh ran at 7200 MT/s on 2026-11-17 from 22:12:09 to 22:22:18 UTC: 3 sessions of parts A, L and C, and one more part C process.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **F72d12**: one process of the part L line. It ran at 20:02 UTC on 2026-11-17 for another test, in the same boot as the rerun and before it. It is not part of the rerun.
- **T72A1 to T72I2**: the names (tags) of the result folders of the rerun and of control I: T72, then the letter of the part (A, L, C or I), then a number.
- **A-1, A-2, A-3**: the 8000 MT/s rows for part A, all of 2026-11-13, with the same two binaries. A-1 is the original test. A-2 is a second run with another process order. A-3 is three more processes of bw_old read.
- **L-1, L-2, L-3, L-4**: the 8000 MT/s rows for parts L and C, all with bwx12. L-1 used the argument line of part L unchanged. L-2 to L-4 used 4 s measurements.
- **Pool**: the intervals of several rows taken together as one range.
- **Pair, drop**: a pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A the two kernels run in two processes. There the drop uses the medians of the two processes of one session and round.
- **n**: the number of measurements that a range comes from, written as intervals / processes / sessions / boots.
- **Boot, boot 3bfc57a1**: a boot is one run of the machine from a start to the next restart. The rerun ran in boot 3bfc57a1. This name is the first 8 characters of the boot id, a random identifier that Linux creates at each start.
- **Hardware error record, corrected record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the log of the Linux kernel with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues).
- **Argument line, spec file**: the arguments of one bwx12 process. A spec file is a text file with one argument line.
- **Visit**: one time at which the same argument line was run.
- **Interval row, thread row**: two kinds of row in a csv file of bwx12. An interval row starts with the letter I and holds one interval. A thread row starts with the letter T and holds one thread of one interval. The 120 thread rows of an interval follow its interval row.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Pass count**: part A only: the number of buffer passes that all 120 threads completed in one interval. It is the column total_bytes divided by the column bytes_per_thread of the csv row. So it is the sum over the threads. Example: 600 passes are 5 passes per thread on average.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes.
- **%CPU, process list**: a process list is the output of the tool ps that a run script saves before a launch. %CPU is the column pcpu of this output. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **Facts sheet**: the file FACTS.md with its data file facts.json. It is the detailed record of the rerun. The script build_facts.py built it from the raw result files.
- **Rules file**: `S/baselines-and-rules.txt`. It holds the list of 8000 MT/s rows and the comparison rules V1 to V4, F1 and F2. It was written before the run.
- **X2d12**: one process of the part L line at 8000 MT/s with 12 modules, in another boot of 2026-11-17. The page shows it and does not use it.
- **Dumbbell chart, strip plot**: two kinds of chart. A dumbbell chart joins two dots of one row by a line. A strip plot draws every value of a row as one dot.
- **Tooltip**: the text that a browser shows when the pointer rests on a mark of a figure.
- **px**: pixel, the unit of length of a web page.
- **est.**: estimated, not measured directly.

</details>

## References

- [Ref1] `S/make_report.py`, lines 1 to 19 and 29 to 32: header of the script. It names the output file, the input, the rule "No measured number is typed", and "Edit this file, never the HTML".
- [Ref2] `S/make_report.py`, lines 124 to 139 and 176 to 189: functions `t_rows` and `val`. The rate of a part A record is the csv value. The rate of a bwx12 record is the sum of its 120 thread rows. Lines 339 to 345: the check of this sum against the rate that the interval row prints.
- [Ref3] `S/make_report.py`, lines 42 to 49 (`stop` and `need`: a failed hard check ends the script) and lines 86 to 105 (rounding half up with `q`, `f2`, `f1`, and `median`).
- [Ref4] `S/make_report.py`, lines 192 to 217: class `Rg` with the range, the order of the intervals, `overlaps`, `nearest` and `farthest`.
- [Ref5] `S/make_report.py`, lines 268 to 319: which records each row of the page uses, with the expected number of intervals and processes.
- [Ref6] `S/make_report.py`, lines 407 to 460: pairs, `drop`, and the part A pair of process medians (`a_pair`).
- [Ref7] `S/make_report.py`, lines 470 to 507: the two fixed wordings, `width_pct`, `wording`, the two percent values of the part L distances of the old read kernel (lines 489 to 492), and the three kinds of distance of Table 4.
- [Ref8] `S/make_report.py`, lines 508 to 517 and 1905 to 1915: part A, session 1 against the 8000 MT/s processes of the same round (rule V3).
- [Ref9] `S/make_report.py`, lines 1555 to 1678: the rows and the drawing of Figure 1 (`bwx_row`, `F1_BLOCKS`, `fig1`).
- [Ref10] `S/make_report.py`, lines 1682 to 1708 and 1756 to 1862: `beeswarm` (vertical offsets), `p_row` and `panel` of Figure 2. Lines 1886 to 1935: the blocks and rows of the two panels.
- [Ref11] `S/make_report.py`, lines 2003 to 2045 (`q1_table`), 2079 to 2181 (`q2_table`), 2184 to 2216 (`visits_table`, `dist_table`), 2219 to 2252 (`load_table`), 2255 to 2275 (the two table views), 2503 to 2570 (`state_table`).
- [Ref12] `S/make_report.py`, lines 2677 to 2781 (`build`: the order of the parts of the page) and 2784 to 2831 (checks of the built page, "NOT WRITTEN", the write of the file).
- [Ref13] `S/test_make_report.py`, lines 1 to 7 and 21 to 35: what the test does and where its copies write.
- [Ref14] `S/facts.json`: 793 interval records (field `meta.counts.intervals`). The field `meta.rate_kinds` defines the two kinds of rate: the csv column `aggregate_GBps` for part A, and the sum over the thread rows of bytes / elapsed_s / 1e9 for the bwx runners.
- [Ref15] `R/w120-T72L1-20261117T221329Z/a6456.csv`, line 1 (the csv header with the definition of `aggregate_GBps`), line 128 (interval row) and lines 129 to 248 (its 120 thread rows): the sample of the bwx12 rate.
- [Ref16] `R/k120-T72A1-20261117T221209Z/threads120.csv`, lines 2 to 6: the csv header with the definition of `aggregate_GBps`, the column names, and the 3 intervals of the first bw_old read process.
- [Ref17] `S/build_facts.py`: the script that builds `facts.json` and `FACTS.md` from the raw files.
- [Ref18] `S/baselines-and-rules.txt`: the list of 8000 MT/s rows and the comparison rules. Its explanation is `S/baselines-and-rules.txt.md`.
