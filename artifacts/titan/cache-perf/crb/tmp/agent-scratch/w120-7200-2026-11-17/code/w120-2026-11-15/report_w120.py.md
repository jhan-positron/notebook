# `report_w120.py` explained, line by line

- Source file: `w120-2026-11-15/report_w120.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1208 lines, 80545 bytes).
- sha256 of the source when this page was built: `e2657465f6b8604eeb0ce6b8676823f7e7cbb7a0b4b2a56522663157eaecc1c1`.

## Short version: purpose

`report_w120.py` builds the HTML report page of the 120-thread investigation of 2026-11-15, with the title "Why the whole-chip read rate fell with the new test kernel". It holds every number and every sentence of the page as fixed text or as fixed tables, and it draws four figures from these tables. It reads no result file when it runs, and it ends with exit status 1 when its check finds a label of a figure that overlaps another label or a mark, or that reaches outside the figure.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **120-thread investigation**: the tests of 2026-11-15 on why the read rate of 120 threads fell with the new read kernel.
- **Report page**: the HTML file that this script writes, `whole-chip-read-drop.html`.
- **Facts sheet of 2026-11-15**: the file `FINDINGS.md` in the folder of the script. It holds the numbers of the investigation in the sections "The question" and F1 to F5. On this page "the facts sheet" means this file.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Loop, loop variant**: the word of the report page for a read kernel. A variant is one of the 29 read kernels of the table `F2`.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`read_nop96`, `read_nop256`**: the `asmread` loop with 96 or 256 `nop` instructions after the 8 loads of each 256 B. A `nop` is an instruction that does nothing. The report page calls such a loop a padded loop.
- **`rand_nop0`, `rand_nop96`, `rand_nop256`**: loops that read the same bytes as `asmread` but visit the blocks of 256 B in a scrambled order, with 0, 96 or 256 `nop` instructions per block.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **`T` row**: the row that the runner prints for one thread in one interval. Its fields are: `T`, round, position, kernel, thread number, CPU, bytes, time in seconds, three clock times, passes, flags.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, each with its own buffer of 256 MiB. Other layouts are written in the same form.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the sum of the rates of all threads of a case.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **Window depth**: the number of 64-byte cache lines that the loads inside the out-of-order window of a core touch. The facts sheet gives it for each loop as a range, measured with one thread.
- **State**: the name that the facts sheet gives to the total of a loop at 64+56: `slow`, `between`, `fast` or `fastest`.
- **Latency probe**: a test loop on one CPU that times loads that miss the caches, while the other CPUs read. Its time per step is the probe time.
- **Lines in flight (`LIF`)**: an estimate of how many cache lines one core has requested and not yet received. It is the lines per second of a thread times the probe time.
- **Squeezed**: a squeezed mesh reads less than it would alone. The cause is the loop that the other mesh runs.
- **Scrambled order, sequential order**: a sequential loop reads its buffer from the lowest address to the highest. A scrambled loop reads the same bytes in an order that jumps between the blocks.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **SVG**: a text format for drawings. A browser shows it inside an HTML page.
- **Mark**: the small shape that stands for one value in a figure: a circle, a square or a triangle.
- **Citation mark**: the text `Ref` with a number in square brackets that the report page puts after a claim. The function `r` writes it. The numbers are those of the reference list of the report page (lines 1155 to 1189).
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. At load time the script sets the path of the page (lines 21 to 23), the colours (lines 26 to 32) and the data tables `F2`, `F3`, `F4`, `F5` and `FIG4` (lines 37 to 138).
2. The main part calls `build` (lines 1200 to 1201).
3. `build` first draws the four figures. Each figure function fills an object of the class `Svg`, which collects the drawing commands and a box for every label and mark (line 578).
4. `build` writes the head of the page, the title, the short version and the word list (lines 581 to 670).
5. `build` writes the sections 1 to 9 of the page: text, tables and the four figures (lines 673 to 1150).
6. `build` writes the reference list and closes the page (lines 1153 to 1194).
7. `build` collects the label overlaps of the four figures and returns them with the page text (lines 1196 to 1197).
8. The main part writes the page to the file, prints its size and every overlap, and ends with exit status 1 when there is an overlap (lines 1202 to 1208).

## Behavior a reader must know

- The script opens one file only, the page that it writes (line 1202). It does not read the facts sheet and no result file. Every number of the page is a fixed value in the source.
- The header text names four groups of numbers that were computed again from raw files. That work was done outside this script. Its results stand in the source as fixed numbers. Only the midpoints of group 3 are computed at run time (line 274).
- Group `LIF` (lines 90 to 96): for each mesh of a case, take the `T` rows of the file `CASE.m0.csv` or `CASE.m1.csv`. Divide the bytes of each row by its time. Take the mean of these rates. Divide by 64 bytes per cache line and multiply by the probe time in seconds, the column `median_ns` of the row `nop,0,` of `CASE.probe2.csv` or `CASE.probe66.csv`. A recomputation for this explanation page gives every `LIF` value and every probe time of the table `F4` [Ref10].
- Group `F5` (lines 105 to 117): for each file `GROUP.m0.csv` or `GROUP.m1.csv`, divide the bytes of each `T` row by its time. The sum of these rates is the mesh sum. The smallest and the largest are the per-thread range. A recomputation for this explanation page gives all values of the table `F5` [Ref20].
- Group `LOAD` (lines 1101 to 1108): the first value of the `/proc/loadavg` line in `env.txt` is the load at the start of a script. The first value after the word `load` in a `launch` line of `launches.txt` is the load at a launch. A recomputation for this explanation page over the 14 folders of 2026-11-15 gives the values that the page text holds: 0.00 to 71.24 at the start, 0.00 to 109.60 at the 101 launches, 1 runnable task and 0 logins at every launch [Ref17].
- The other numbers of the page are copies of the facts sheet, or rounded forms and outer ends of its ranges. The rows say where a line holds a number that is not in the facts sheet in this form.
- The page is written even when labels overlap. Only the exit status and the printed lines show the problem.
- The overlap check works with estimated text widths (0.58 times the font size per character). It can miss an overlap or report a false one.
- Figure 1 moves a mark sideways when it would cover another mark. The height of a mark is never changed, and the six labelled marks are never moved (lines 260 to 282).
- A total in the table of section 6 is the sum of the unrounded mesh sums. So it can differ by 0.1 GB/s from the sum of the two rounded values in the same row.
- The reference numbers of this explanation page are those of the report page for the same source: 1 for the facts sheet, 10 for the latency probe run, 17 for the files `env.txt` and `launches.txt`, 20 for the scrambled-order run.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/report_w120.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1208 lines, 80545 bytes, sha256 `e2657465f6b8604eeb0ce6b8676823f7e7cbb7a0b4b2a56522663157eaecc1c1`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, modules and the output path (lines 1 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""report_w120.py [OUT.html] - build the report "why the whole-chip read rate fell with the new read kernel".` | Starts the description text of the file. Usage: one optional argument, the path of the HTML page. The text names the report "why the whole-chip read rate fell with the new read kernel". The title that line 585 writes on the page ends with the words "new test kernel". |
| 4 | `Source of every number: FINDINGS.md in this folder (the facts sheet).` | Description: the source of every number is the file `FINDINGS.md` in the folder of the script, the facts sheet. |
| 5 | `Four groups of numbers are not copied from the facts sheet. They are recomputed from the raw files that it names:` | Description: four groups of numbers are not copied from the facts sheet. By this text they are computed again from the raw files that the facts sheet names. The script itself reads no raw file. It holds the results as fixed numbers (lines 89 to 97, lines 104 to 118, lines 1101 to 1108). Only the midpoints of line 9 are computed when the script runs (line 274). |
| 6 | `  - LIF: estimated lines in flight per case (results/w120-R4-20261115T200016Z, T rows of *.m0.csv / *.m1.csv` | Description, group `LIF`: the estimated lines in flight per case. The raw files lie in the result folder `w120-R4-20261115T200016Z`. The first kind is the `T` rows of the files `*.m0.csv` (threads on mesh 0) and `*.m1.csv` (threads on mesh 1). A `T` row holds the bytes of one thread in its seventh field (column `bytes`) and the time in its eighth field (column `elapsed_s`) [Ref10]. |
| 7 | `    and the "nop,0," row of *.probe2.csv / *.probe66.csv): mean per-thread bytes/s / 64 * probe time.` | Description, continued. The second kind is the row that starts with `nop,0,` in the files `*.probe2.csv` and `*.probe66.csv`, the latency probes on CPU 2 and CPU 66. Its fourth field (column `median_ns`) is the probe time. The value of a mesh is the mean over its `T` rows of bytes divided by time, then divided by 64 bytes per cache line, then multiplied by the probe time in seconds [Ref10]. |
| 8 | `  - LOAD: the 1-minute load average and the runnable-task count in env.txt and launches.txt of the w120-* folders.` | Description, group `LOAD`: the 1-minute load average and the number of runnable tasks. The file `env.txt` of a `w120-*` folder holds the content of `/proc/loadavg` at the start of a script. Each `launch` line of `launches.txt` holds it after the word `load`. The first value is the 1-minute load average. The number in front of the slash in the fourth value is the number of runnable tasks [Ref17]. |
| 9 | `  - the midpoints of the window ranges in Figure 1 (arithmetic on the facts-sheet ranges).` | Description, group 3: the midpoints of the window ranges in Figure 1. A midpoint is the mean of the two ends of a range of the facts sheet. Line 274 computes it. |
| 10 | `  - F5: the sums and per-thread ranges of the scrambled-order run (results/w120-R7-20261115T205946Z, T rows of` | Description, group `F5`: the sums and the per-thread ranges of the scrambled-order run. The raw files lie in the result folder `w120-R7-20261115T205946Z`. They are `T` rows again. |
| 11 | `    <group>.m0.csv / <group>.m1.csv, thread rate = bytes / elapsed_s). They agree with the facts sheet to 0.1 GB/s.` | Description, continued. The files are `GROUP.m0.csv` for mesh 0 and `GROUP.m1.csv` for mesh 1. The rate of a thread is its bytes divided by its time (columns `bytes` and `elapsed_s`). A sum adds the rates of all threads of one file. By this text the sums agree with the facts sheet within 0.1 GB/s [Ref20]. |
| 12 | `The recomputed values agree with the facts sheet (the sheet was corrected on 2026-11-15: 7.6 lines in flight, four` | Description: the recomputed values agree with the facts sheet. The facts sheet was corrected on 2026-11-15 at three places. The first two are the value of 7.6 lines in flight and the count of four variants. |
| 13 | `variants at 26-32 lines, the load sentence).` | Description, continued: these four variants are those at 26 to 32 lines. The third place is the sentence about the load. |
| 14 | `In Figure 1, marks that would cover each other are moved sideways (see place() in fig1); the page states the largest move.` | Description: in Figure 1, marks that would cover each other are moved sideways. The function `place` inside `fig1` does this. The page states the largest move. |
| 15 | `Python 3 standard library only. The page has no script, no external font and no external image.` | Description: the script needs only the standard library of Python 3. The page has no script, no font and no image from another place. |
| 16 | `The script prints every label overlap that it can compute, and exits with status 1 if there is one.` | Description: the script prints every overlap of labels that it can compute. It ends with exit status 1 when there is one. |
| 17 | `"""` | Ends the description text. |
| 18 | `import os` | Loads the module `os`, here for file paths. |
| 19 | `import sys` | Loads the module `sys`, which gives the arguments and the exit status. |
| 21 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script, as a full path. |
| 22 | `OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(` | `OUT`: the path of the page. It is argument 1 when the caller gives one. If not, it is the default of line 23. `os.path.normpath` removes the `..` parts from the path. |
| 23 | `    os.path.join(HERE, '..', '..', '..', 'new-test-kernel', 'whole-chip-read-drop.html'))` | Continues line 22: the default path. It goes three folders up from the folder of the script and then to `new-test-kernel/whole-chip-read-drop.html`. This fits the place of the script in the project folder on the agent server. In this repo the script lies in another folder, so the caller must give the path. |

### The colours (lines 25 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `# ---------------------------------------------------------------- palette (light theme only)` | Comment: the colours of the page. The page has a light theme only. |
| 26 | `C1 = '#2a78d6'   # blue` | `C1`: blue. The figures use it for the class `nop`, for mesh 0, for a fast mesh and for the sequential order. |
| 27 | `C2 = '#eb6834'   # orange` | `C2`: orange. The figures use it for the class `add`, for mesh 1, for a slow or squeezed mesh and for the scrambled order. |
| 28 | `C3 = '#1baf7a'   # aqua` | `C3`: a blue-green that the comment calls aqua. Figure 1 uses it for the class `load`. |
| 29 | `INK = '#0b0b0b'` | `INK`: the colour of the main text, almost black. |
| 30 | `INK2 = '#52514e'` | `INK2`: a grey for axes, tick labels and second-level text. |
| 31 | `GRID = '#e4e3df'` | `GRID`: a light grey for the grid lines. |
| 32 | `SURF = '#fcfcfb'` | `SURF`: the background colour of the figures, almost white. |

### Table `F2`: the loop variants at 64+56, and the three mark classes (lines 34 to 71)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `# ---------------------------------------------------------------- data from the facts sheet` | Comment: the tables that follow hold the data of the facts sheet. |
| 35 | `# F2 table: name, what the loop holds, window lo, hi (lines), total min, max (GB/s), n, state, class` | Comment: the fields of a row of `F2`. In this order: the name of the loop, what the loop holds, the low and the high end of its window depth in cache lines, the smallest and the largest total in GB/s, the number of intervals `n`, the state and the class. |
| 36 | `# class: 'nop' = loads plus nop, 'add' = loads plus vector adds, 'load' = loads only` | Comment: the three classes. `nop`: loads plus `nop` instructions. `add`: loads plus vector adds. `load`: loads only. The class sets the colour and the shape of the mark in Figure 1. |
| 37 | `F2 = [` | Starts the list `F2`, one row per loop variant that ran at 64+56. The 29 rows stand in the order of the table in section F2 of the facts sheet. A comparison for this page found the same window ranges, totals, counts and states there [Ref1]. |
| 38 | `    ('read_1pl', '4 ldr q, one per line (256 B)', 156, 164, 230.2, 235.0, 16, 'slow', 'load'),` | Row `read_1pl`: 4 single loads per 256 B, one per cache line. The window covers 156 to 164 lines. The total is 230.2 to 235.0 GB/s over 16 intervals. State `slow`, class `load`. Its window is far deeper than every other one, so Figure 1 draws it in a side panel. |
| 39 | `    ('read_sparse', '4 ldp + 9 nop (128 B)', 38, 42, 294.6, 301.5, 6, 'slow', 'nop'),` | Row `read_sparse`: 4 load-pair instructions and 9 `nop` per 128 B. State `slow`, class `nop`. The facts sheet writes the name as `read_sparse (sp9)`. |
| 40 | `    ('asmread (= new C read)', '8 ldp q (256 B)', 36, 40, 288.5, 309.8, 22, 'slow', 'load'),` | Row `asmread`, the new load-only loop: 8 load-pair instructions per 256 B. Window 36 to 40 lines, total 288.5 to 309.8 GB/s over 22 intervals, state `slow`. It is one of the six variants that Figure 1 labels. |
| 41 | `    ('read_pf2048', '8 ldp + 4 prfm 2048 B ahead', 36, 40, 290.5, 306.8, 11, 'slow', 'load'),` | Row `read_pf2048`: the load-only loop with 4 prefetch instructions that ask for the data 2048 B ahead. State `slow`. The line gives it the class `load`, whose legend text is "plain loads only". |
| 42 | `    ('read_nop32', '8 ldp + 32 nop', 36, 40, 284.8, 302.7, 4, 'slow', 'nop'),` | Row `read_nop32`: the load-only loop with 32 `nop` per 256 B. Window 36 to 40 lines, state `slow`. |
| 43 | `    ('read_nop48', '8 ldp + 48 nop', 32, 36, 305.4, 307.2, 2, 'slow', 'nop'),` | Row `read_nop48`: 48 `nop`. Window 32 to 36 lines, state `slow`. |
| 44 | `    ('read_dadd2', '8 ldp + 2 vector adds', 32, 36, 290.1, 296.4, 2, 'slow', 'add'),` | Row `read_dadd2`: the load-only loop with 2 vector adds. Window 32 to 36 lines, state `slow`, class `add`. |
| 45 | `    ('read_sp24', '4 ldp + 24 nop (128 B)', 32, 34, 280.9, 283.2, 2, 'slow', 'nop'),` | Row `read_sp24`: 4 load-pair instructions and 24 `nop` per 128 B. Window 32 to 34 lines, state `slow`. |
| 46 | `    ('read_nop56', '8 ldp + 56 nop', 28, 32, 308.6, 309.1, 2, 'slow', 'nop'),` | Row `read_nop56`: 56 `nop`. Window 28 to 32 lines, state `slow`. |
| 47 | `    ('read_dadd4', '8 ldp + 4 vector adds', 28, 32, 280.1, 283.2, 2, 'slow', 'add'),` | Row `read_dadd4`: 4 vector adds. Window 28 to 32 lines, state `slow`. |
| 48 | `    ('read_nop64', '8 ldp + 64 nop', 28, 32, 325.5, 333.9, 13, 'between', 'nop'),` | Row `read_nop64`: 64 `nop`. Window 28 to 32 lines, total 325.5 to 333.9 GB/s over 13 intervals. It is the first of the two rows with the state `between`. |
| 49 | `    ('read_sp32', '4 ldp + 32 nop (128 B)', 26, 30, 366.3, 366.6, 2, 'between', 'nop'),` | Row `read_sp32`: 4 load-pair instructions and 32 `nop` per 128 B. Window 26 to 30 lines. It is the second row with the state `between`. |
| 50 | `    ('read_nop72', '8 ldp + 72 nop', 24, 28, 459.0, 459.3, 2, 'fast', 'nop'),` | Row `read_nop72`: 72 `nop`. Window 24 to 28 lines, total 459.0 to 459.3 GB/s. It is the first row with the state `fast`, and Figure 1 labels it. |
| 51 | `    ('read_dadd8', '8 ldp + 8 vector adds', 24, 28, 462.4, 462.6, 2, 'fast', 'add'),` | Row `read_dadd8`: 8 vector adds. Window 24 to 28 lines, state `fast`. |
| 52 | `    ('read_1pl_nop96', '4 ldr q + 96 nop', 24, 28, 460.8, 460.9, 2, 'fast', 'nop'),` | Row `read_1pl_nop96`: the loop `read_1pl` with 96 `nop`. Window 24 to 28 lines, state `fast`. |
| 53 | `    ('read_nop80', '8 ldp + 80 nop', 24, 28, 459.7, 459.8, 2, 'fast', 'nop'),` | Row `read_nop80`: 80 `nop`. Window 24 to 28 lines, state `fast`. |
| 54 | `    ('read_sp40', '4 ldp + 40 nop (128 B)', 22, 24, 466.8, 466.9, 2, 'fast', 'nop'),` | Row `read_sp40`: 4 load-pair instructions and 40 `nop` per 128 B. Window 22 to 24 lines, state `fast`. |
| 55 | `    ('read_nop88', '', 20, 24, 462.8, 462.9, 2, 'fast', 'nop'),` | Row `read_nop88`. The second field is empty: the facts sheet does not say what this loop holds. Window 20 to 24 lines, state `fast`. |
| 56 | `    ('read_nop96', '', 20, 24, 465.5, 470.6, 16, 'fast', 'nop'),` | Row `read_nop96`. Window 20 to 24 lines, total 465.5 to 470.6 GB/s over 16 intervals, state `fast`. Line 131 takes this row for the second row of Figure 4. |
| 57 | `    ('read_sp48', '', 20, 22, 470.0, 470.1, 2, 'fast', 'nop'),` | Row `read_sp48`. The second field is empty. Window 20 to 22 lines, state `fast`. |
| 58 | `    ('oldread (old C read)', '4 ldp + 8 vector adds (128 B)', 18, 22, 465.5, 470.1, 22, 'fast', 'add'),` | Row `oldread`, the old read loop: 4 load-pair instructions and 8 vector adds per 128 B. Window 18 to 22 lines, total 465.5 to 470.1 GB/s over 22 intervals, state `fast`, class `add`. Figure 1 labels it. |
| 59 | `    ('read_sp56', '', 18, 20, 473.6, 473.7, 2, 'fast', 'nop'),` | Row `read_sp56`. The second field is empty. Window 18 to 20 lines, state `fast`. |
| 60 | `    ('read_dadd16', '8 ldp + 16 vector adds that use the loaded data', 16, 20, 466.7, 469.8, 5, 'fast', 'add'),` | Row `read_dadd16`: 16 vector adds that use the loaded data. Window 16 to 20 lines, state `fast`. |
| 61 | `    ('read_iadd16', '8 ldp + 16 vector adds that do not use the loaded data', 16, 20, 469.2, 469.7, 2, 'fast', 'add'),` | Row `read_iadd16`: 16 vector adds that do not use the loaded data. Window 16 to 20 lines, state `fast`. Figure 1 labels it. |
| 62 | `    ('read_nop112', '', 16, 20, 471.1, 471.2, 2, 'fast', 'nop'),` | Row `read_nop112`. The second field is empty. Window 16 to 20 lines, state `fast`. |
| 63 | `    ('read_nop128', '', 16, 20, 473.8, 476.4, 9, 'fast', 'nop'),` | Row `read_nop128`. The second field is empty. Window 16 to 20 lines, 9 intervals, state `fast`. |
| 64 | `    ('read_nop160', '', 12, 16, 477.9, 478.2, 2, 'fast', 'nop'),` | Row `read_nop160`. The second field is empty. Window 12 to 16 lines, state `fast`. |
| 65 | `    ('read_nop192', '', 12, 16, 479.6, 479.8, 2, 'fast', 'nop'),` | Row `read_nop192`. The second field is empty. Window 12 to 16 lines, state `fast`. |
| 66 | `    ('read_nop256', '8 ldp + 256 nop', 8, 12, 543.9, 549.0, 9, 'fastest', 'nop'),` | Row `read_nop256`: 256 `nop` per 256 B. Window 8 to 12 lines, total 543.9 to 549.0 GB/s over 9 intervals. It is the only row with the state `fastest`. Figure 1 labels it. |
| 67 | `]` | Ends the list `F2`. |
| 68 | `CLS = {'nop': (C1, 'circle', 'loads plus padding instructions (nop)'),` | `CLS`: maps each class to three things: the colour, the shape of the mark and the text of the legend. The class `nop` gets a blue circle. |
| 69 | `       'add': (C2, 'tri', 'loads plus vector adds'),` | The class `add` gets an orange triangle. |
| 70 | `       'load': (C3, 'square', 'plain loads only')}` | The class `load` gets a square in the colour `C3`. The closing brace ends the dictionary. |

### Table `F3`: the pairs of loops, one loop per mesh (lines 72 to 86)

| Line | Source | Explanation |
|---:|---|---|
| 72 | `# F3: mesh 0 loop, mesh 1 loop, mesh 0 sum, mesh 1 sum, total (GB/s). Order: by the mesh 1 loop.` | Comment: the fields of a row of `F3`. In this order: the loop on mesh 0, the loop on mesh 1, the sum of the thread rates on mesh 0, the sum on mesh 1, and the total, all in GB/s. The rows are ordered by the loop on mesh 1. |
| 73 | `SHORT = {'asmread': 'load-only', 'read_nop96': 'nop96', 'read_nop256': 'nop256'}` | `SHORT`: the short labels that Figure 2 prints under its bars for the three loops. |
| 74 | `F3 = [` | Starts the list `F3`: the nine pairs of the run with two processes at the same time, one per mesh. The values that the rows hold stand in section F3 of the facts sheet [Ref1]. |
| 75 | `    ('asmread', 'asmread', 175.7, 127.2, 302.9),` | Pair 1: `asmread` on both meshes. The total is the smallest of the nine. |
| 76 | `    ('read_nop96', 'asmread', 149.5, 154.3, 303.8),` | Pair 2: `read_nop96` on mesh 0, `asmread` on mesh 1. |
| 77 | `    ('read_nop256', 'asmread', 137.3, 251.3, 388.6),` | Pair 3: `read_nop256` on mesh 0, `asmread` on mesh 1. |
| 78 | `    ('asmread', 'read_nop96', 331.9, 116.2, 448.1),` | Pair 4: `asmread` on mesh 0, `read_nop96` on mesh 1. Figure 2 shades this group. |
| 79 | `    ('read_nop96', 'read_nop96', 318.9, 150.7, 469.5),` | Pair 5: `read_nop96` on both meshes. |
| 80 | `    ('read_nop256', 'read_nop96', 238.1, 254.2, 492.3),` | Pair 6: `read_nop256` on mesh 0, `read_nop96` on mesh 1. |
| 81 | `    ('asmread', 'read_nop256', 349.8, 108.2, 457.9),` | Pair 7: `asmread` on mesh 0, `read_nop256` on mesh 1. Figure 2 shades this group. |
| 82 | `    ('read_nop96', 'read_nop256', 347.8, 123.5, 471.3),` | Pair 8: `read_nop96` on mesh 0, `read_nop256` on mesh 1. |
| 83 | `    ('read_nop256', 'read_nop256', 327.4, 221.8, 549.1),` | Pair 9: `read_nop256` on both meshes. The total is the largest of the nine. |
| 84 | `]` | Ends the list `F3`. |
| 85 | `F3_REF = 348  # mesh 0 alone with asmread, GB/s` | `F3_REF`: 348 GB/s, the rate of mesh 0 alone with `asmread`. Figure 2 draws it as a dashed line. The value stands in section F3 of the facts sheet [Ref1]. |

### Table `F4`: the cases of the latency probe (group `LIF`) (lines 87 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 87 | `# F4: case label, mesh 0 loop, mesh 1 loop, lines in flight mesh 0, mesh 1 (est., LIF, recomputed), probe ns CPU 2, CPU 66` | Comment: the fields of a row of `F4`. The comment lists seven items and starts with a case label. A row of lines 90 to 96 has six fields and no separate case label. The six fields are, in this order: the label of the loop on mesh 0, the label of the loop on mesh 1, the estimated lines in flight per core on mesh 0 and on mesh 1 (est., group `LIF`), and the probe time in ns on CPU 2 and on CPU 66. |
| 88 | `# LIF values recomputed from results/w120-R4-20261115T200016Z (see the module text): mean over the streaming threads.` | Comment: the `LIF` values were computed again from the result folder `w120-R4-20261115T200016Z`, as the header text says. Each value is a mean over the streaming threads of one mesh. |
| 89 | `F4 = [` | Starts the list `F4`, one row per case of the latency probe. The file `CASE.m0.csv` of each case holds the `T` rows of 63 threads on mesh 0. Where mesh 1 has a loop, the file `CASE.m1.csv` holds those of 55 threads [Ref10]. |
| 90 | `    ('load-only (asmread)', 'load-only (asmread)', 8.380, 7.911, 203.1, 211.3),` | Case 1: `asmread` on both meshes. The values that the line holds are 8.380 and 7.911 lines in flight (est.) and 203.1 ns and 211.3 ns. A recomputation for this page from the files `asmread_asmread.*` gives the same values. For mesh 0: the mean thread rate is 2.641 GB/s. Divided by 64 bytes this is 41.27 million lines per second. Times the probe time of 203.075 ns this gives 8.380 lines [Ref10]. |
| 91 | `    ('read_1pl', 'read_1pl', 6.454, 7.061, 219.2, 219.4),` | Case 2: `read_1pl` on both meshes. The same computation on the files `read_1pl_read_1pl.*` gives the values of the line [Ref10]. |
| 92 | `    ('read_nop256', 'load-only (asmread)', 7.006, 16.621, 212.9, 223.5),` | Case 3: `read_nop256` on mesh 0, `asmread` on mesh 1. The same computation on the files `read_nop256_asmread.*` gives the values of the line [Ref10]. |
| 93 | `    ('load-only (asmread)', 'read_nop256', 25.323, 7.647, 297.1, 236.4),` | Case 4: `asmread` on mesh 0, `read_nop256` on mesh 1. The same computation on the files `asmread_read_nop256.*` gives the values of the line. The 7.647 of mesh 1 is the value that the header text gives as 7.6 [Ref10]. |
| 94 | `    ('read_nop96', 'read_nop96', 23.737, 9.190, 286.5, 238.1),` | Case 5: `read_nop96` on both meshes. The same computation on the files `read_nop96_read_nop96.*` gives the values of the line [Ref10]. |
| 95 | `    ('read_nop256', 'read_nop256', 19.197, 14.905, 238.0, 246.9),` | Case 6: `read_nop256` on both meshes. The same computation on the files `read_nop256_read_nop256.*` gives the values of the line [Ref10]. |
| 96 | `    ('load-only (asmread)', None, 23.374, None, 278.0, 165.5),` | Case 7: `asmread` on mesh 0 only. No thread streams on mesh 1, so its loop and its value are `None`. The probe on CPU 66 ran in this case too, and the line holds its time. The files are `asm_only_m0.*` [Ref10]. |
| 97 | `]` | Ends the list `F4`. |
| 98 | `SLOW_MAX = 9.2    # facts sheet: slow or squeezed meshes 6.5-9.2` | `SLOW_MAX`: 9.2 lines, the upper end of the range that the facts sheet gives for slow or squeezed meshes (6.5 to 9.2, est.) [Ref1]. Figure 3 colours a mark orange up to this value. |
| 99 | `FAST_MIN = 14.9   # facts sheet: fast meshes 14.9-25.3` | `FAST_MIN`: 14.9 lines, the lower end of the range that the facts sheet gives for fast meshes (14.9 to 25.3, est.) [Ref1]. The blue band of Figure 3 starts here. |

### Table `F5`: the scrambled-order run, and the function `f5tot` (lines 102 to 128)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `# F5: scrambled-order run R7, recomputed from the raw files. One 10 s interval per cell.` | Comment: the table `F5` holds the scrambled-order run R7, computed again from the raw files. Each cell is one interval of 10 s. |
| 103 | `# group: mesh 0 loop, mesh 1 loop, mesh 0 sum, mesh 1 sum (GB/s), per-thread min, max of mesh 0 and of mesh 1 (GB/s)` | Comment: the fields of a row of `F5`. In this order: the loop on mesh 0, the loop on mesh 1, the sum of the thread rates on mesh 0 and on mesh 1 in GB/s, then the smallest and the largest thread rate of mesh 0 and of mesh 1 in GB/s. |
| 104 | `F5 = [` | Starts the list `F5` with 13 groups. By the `launch` lines of the file `launches.txt` of that run, a group with two loops has two processes that start together: one with 64 threads on mesh 0 and one with 56 threads on mesh 1 [Ref20]. |
| 105 | `    ('rand_nop0', 'rand_nop0', 268.750, 220.835, 4.14854, 4.23725, 3.89397, 3.97673),` | Group 1: `rand_nop0` on both meshes. The mesh 0 sum of 268.750 GB/s is the sum over the 64 `T` rows of the file `rand_nop0_rand_nop0.m0.csv` of bytes divided by time. The mesh 1 sum of 220.835 GB/s is the same sum over the 56 `T` rows of the `.m1.csv` file. The four other values are the smallest and the largest thread rate of each file. A recomputation for this page gives the same six values [Ref20]. |
| 106 | `    ('rand_nop96', 'rand_nop96', 250.520, 222.941, 3.87058, 3.96486, 3.93126, 4.01952),` | Group 2: `rand_nop96` on both meshes. The same computation on the files `rand_nop96_rand_nop96.*` gives the values of the line [Ref20]. |
| 107 | `    ('rand_nop256', 'rand_nop256', 204.265, 178.257, 3.15792, 3.22448, 3.14721, 3.21170),` | Group 3: `rand_nop256` on both meshes. The same computation on the files `rand_nop256_rand_nop256.*` gives the values of the line [Ref20]. |
| 108 | `    ('rand_nop0', 'rand_nop256', 264.183, 158.116, 4.08435, 4.17789, 2.78908, 2.84760),` | Group 4: `rand_nop0` on mesh 0, `rand_nop256` on mesh 1. Files `rand_nop0_rand_nop256.*` [Ref20]. |
| 109 | `    ('rand_nop256', 'rand_nop0', 192.527, 230.039, 2.97477, 3.03843, 4.06382, 4.14166),` | Group 5: `rand_nop256` on mesh 0, `rand_nop0` on mesh 1. Files `rand_nop256_rand_nop0.*` [Ref20]. |
| 110 | `    ('rand_nop0', 'read_nop256', 182.803, 278.791, 2.82650, 2.87686, 4.90710, 5.06743),` | Group 6: the scrambled loop `rand_nop0` on mesh 0 against the sequential loop `read_nop256` on mesh 1. Files `rand_nop0_read_nop256.*` [Ref20]. |
| 111 | `    ('read_nop256', 'rand_nop0', 307.240, 158.375, 4.72086, 4.92151, 2.79339, 2.84202),` | Group 7: the reverse of group 6. Files `read_nop256_rand_nop0.*` [Ref20]. |
| 112 | `    ('asmread', 'rand_nop256', 282.896, 134.190, 4.33704, 4.45893, 2.36720, 2.41819),` | Group 8: the sequential loop `asmread` on mesh 0 against the scrambled loop `rand_nop256` on mesh 1. Files `asmread_rand_nop256.*` [Ref20]. |
| 113 | `    ('rand_nop256', 'asmread', 127.489, 266.454, 1.95465, 2.00917, 4.60922, 4.80490),` | Group 9: the reverse of group 8. Files `rand_nop256_asmread.*` [Ref20]. |
| 114 | `    ('asmread', 'asmread', 166.274, 131.543, 2.57884, 2.61169, 2.33390, 2.35632),` | Group 10, a control in sequential order: `asmread` on both meshes. Files `asmread_asmread.*` [Ref20]. |
| 115 | `    ('read_nop256', 'read_nop256', 328.531, 218.714, 5.03461, 5.21434, 3.85705, 3.92891),` | Group 11, the second control in sequential order: `read_nop256` on both meshes. Files `read_nop256_read_nop256.*` [Ref20]. |
| 116 | `    ('rand_nop0', None, 342.759, None, 5.29503, 5.40190, None, None),` | Group 12: `rand_nop0` on mesh 0 alone. The loop and the values of mesh 1 are `None`. File `solo_rand_nop0.m0.csv` [Ref20]. |
| 117 | `    ('rand_nop256', None, 223.251, None, 3.44565, 3.53066, None, None),` | Group 13: `rand_nop256` on mesh 0 alone. File `solo_rand_nop256.m0.csv` [Ref20]. |
| 118 | `]` | Ends the list `F5`. |
| 121 | `def f5tot(a, b):` | Starts the function `f5tot`. It gets the loop on mesh 0 and the loop on mesh 1 and returns the total of that group of `F5` in GB/s. |
| 122 | `    """Total of the group (mesh 0 loop a, mesh 1 loop b) in GB/s, unrounded."""` | The description text of `f5tot`: the total is not rounded. |
| 123 | `    for q in F5:` | Starts a loop over the rows of `F5`. |
| 124 | `        if q[0] == a and q[1] == b:` | Takes the row whose two loops are the two arguments. |
| 125 | `            return q[2] + (q[3] or 0.0)` | Returns the mesh 0 sum plus the mesh 1 sum. `(q[3] or 0.0)` gives 0.0 when the mesh 1 sum is `None`. |
| 126 | `    raise KeyError((a, b))` | When no row fits, raises a `KeyError` with the two names. This stops the script. |

### The rows of Figure 4 and the function `f1` (lines 129 to 145)

| Line | Source | Explanation |
|---:|---|---|
| 129 | `# Figure 4 rows: padding, window lo, hi (lines; the window of the sequential loop with the same loads and padding),` | Comment: the fields of a row of `FIG4`. First the padding, then the low and the high end of the window depth in cache lines. The window is that of the sequential loop with the same loads and the same padding. |
| 130 | `# sequential total lo, hi (GB/s), source of the sequential value, scrambled total (GB/s)` | Comment, continued: then the low and the high sequential total in GB/s, the source of the sequential value, and the scrambled total in GB/s. |
| 131 | `SEQ96 = [q for q in F2 if q[0] == 'read_nop96'][0]` | `SEQ96`: the row of `read_nop96` in `F2`. |
| 132 | `FIG4 = [` | Starts the list `FIG4` with three rows, one per padding. |
| 133 | `    ('no padding', 36, 40, f5tot('asmread', 'asmread'), f5tot('asmread', 'asmread'), 'same run',` | Row "no padding": window 36 to 40 lines. The sequential total is the total of the control group `asmread` on both meshes of `F5`. It is one interval, so the same value stands as low and as high end. The source text is "same run". |
| 134 | `     f5tot('rand_nop0', 'rand_nop0')),` | Continues the row of line 133: the scrambled total is the total of the group `rand_nop0` on both meshes. |
| 135 | `    ('96 nop', 20, 24, SEQ96[4], SEQ96[5], 'earlier runs, n = %d' % SEQ96[6], f5tot('rand_nop96', 'rand_nop96')),` | Row "96 nop": window 20 to 24 lines. The sequential total is the range of `read_nop96` in `F2`, 465.5 to 470.6 GB/s, with the source text "earlier runs" and its number of intervals. The scrambled total is the total of the group `rand_nop96` on both meshes. |
| 136 | `    ('256 nop', 8, 12, f5tot('read_nop256', 'read_nop256'), f5tot('read_nop256', 'read_nop256'), 'same run',` | Row "256 nop": window 8 to 12 lines. The sequential total is the total of the control group `read_nop256` on both meshes of `F5`, again as low and as high end. |
| 137 | `     f5tot('rand_nop256', 'rand_nop256')),` | Continues the row of line 136: the scrambled total is the total of the group `rand_nop256` on both meshes. |
| 138 | `]` | Ends the list `FIG4`. |
| 141 | `def f1(v):` | Starts the function `f1`. It writes a number with one decimal. |
| 142 | `    """One decimal, one rounding of the unrounded value (7.647 -> 7.6)."""` | The description text of `f1`: the unrounded value is rounded once. Its example: 7.647 becomes 7.6. |
| 143 | `    return '%.1f' % v` | Returns the text of the number with one decimal. |

### Class `Svg`: the text of one figure and a check of label overlaps (lines 146 to 209)

| Line | Source | Explanation |
|---:|---|---|
| 146 | `# ---------------------------------------------------------------- SVG helper with a label-overlap check` | Comment: the class that follows writes SVG and checks whether labels overlap. SVG is a text format for drawings that a browser shows inside an HTML page. |
| 147 | `class Svg:` | Starts the class `Svg`. One object collects the SVG text of one figure and a box for each label and each mark. |
| 148 | `    def __init__(self, name, w, h, label):` | Starts the set-up function. Its arguments are the name of the figure, the width and the height in pixels, and a label text for screen readers. |
| 149 | `        self.name, self.w, self.h = name, w, h` | Keeps the name, the width and the height. |
| 150 | `        self.out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '` | `self.out`: the list of SVG text pieces. The first piece is the opening tag with the width, the height and a view box of the same size. The line goes on in line 151. |
| 151 | `                    'role="img" aria-label="%s">' % (w, h, w, h, label),` | Continues line 150: `role="img"` and the label text tell a screen reader that the drawing is one picture, and what it shows. |
| 152 | `                    '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (w, h, SURF)]` | The second piece: a rectangle in the colour `SURF` that fills the whole figure, the background. |
| 153 | `        self.boxes = []   # (x0, y0, x1, y1, kind, text)` | `self.boxes`: the list for the overlap check. An entry holds the left, top, right and bottom edge of a box, its kind (`text` or `mark`) and a text. |
| 155 | `    def raw(self, s):` | Starts the method `raw`. It adds one ready piece of SVG text. |
| 156 | `        self.out.append(s)` | Appends the piece to `self.out`. |
| 158 | `    def line(self, x1, y1, x2, y2, col=INK2, w=1, dash=None, op=1):` | Starts the method `line`. It draws a straight line from the point `x1`, `y1` to the point `x2`, `y2`. The defaults are the colour `INK2`, a width of 1 pixel, no dashes and full opacity. |
| 159 | `        self.out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s%s/>' % (` | Appends the SVG element of the line: the four coordinates with one decimal, the colour and the width. The line goes on in lines 160 to 161. |
| 160 | `            x1, y1, x2, y2, col, w, ' stroke-dasharray="%s"' % dash if dash else '',` | Continues line 159: the dash pattern, only when `dash` is given. |
| 161 | `            ' stroke-opacity="%s"' % op if op != 1 else ''))` | Continues line 159: the opacity of the line, only when `op` is not 1. |
| 163 | `    def rect(self, x, y, w, h, fill, op=1, rx=0, title=None):` | Starts the method `rect`. It draws a rectangle with the left top corner `x`, `y`, the width `w`, the height `h` and a fill colour. |
| 164 | `        t = '<title>%s</title>' % title if title else ''` | `t`: a title element with the text `title`, or nothing. A browser shows such a text when the pointer rests on the shape. |
| 165 | `        self.out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"%s%s>%s</rect>' % (` | Appends the SVG element of the rectangle. The line goes on in line 166. |
| 166 | `            x, y, w, h, fill, ' fill-opacity="%s"' % op if op != 1 else '', ' rx="%s"' % rx if rx else '', t))` | Continues line 165: the fill opacity when `op` is not 1, the corner radius when `rx` is given, and the title element. |
| 168 | `    def text(self, x, y, s, size=12, anchor='start', col=INK, bold=False, halo=False, check=True):` | Starts the method `text`. It writes the text `s` at `x`, `y`. The options are the font size, the anchor (`start`, `middle` or `end`), the colour, bold, a halo, and whether the text takes part in the overlap check. |
| 169 | `        wd = 0.58 * size * len(s) * (1.06 if bold else 1.0)` | `wd`: the estimated width of the text in pixels: 0.58 times the font size times the number of characters, and 6 % more for bold text. The script cannot measure the real width, which depends on the font of the reader. |
| 170 | `        x0 = x if anchor == 'start' else (x - wd if anchor == 'end' else x - wd / 2)` | `x0`: the left edge of the text. It is `x` for the anchor `start`, `x` minus the width for `end`, and `x` minus half the width for `middle`. |
| 171 | `        if check:` | Only when `check` is true: |
| 172 | `            self.boxes.append((x0, y - 0.80 * size, x0 + wd, y + 0.22 * size, 'text', s))` | adds the box of the text to `self.boxes`. The box reaches from 0.80 font sizes above the base line `y` to 0.22 font sizes below it. |
| 173 | `        self.out.append('<text x="%.1f" y="%.1f" font-size="%s" text-anchor="%s" fill="%s"%s%s>%s</text>' % (` | Appends the SVG element of the text: position, font size, anchor and colour. The line goes on in lines 174 to 176. |
| 174 | `            x, y, size, anchor, col, ' font-weight="600"' if bold else '',` | Continues line 173: a font weight of 600 for bold text. |
| 175 | `            ' stroke="%s" stroke-width="3" paint-order="stroke" stroke-linejoin="round"' % SURF if halo else '',` | Continues line 173: the halo. It is an outline of 3 pixels in the background colour, drawn behind the letters. It keeps a label readable where it lies on a line or a mark. |
| 176 | `            s.replace('&', '&amp;')))` | Continues line 173: the text itself. Each `&` is written as `&amp;`, as HTML needs it. |
| 178 | `    def mark(self, x, y, shape, col, title=None, r=5, check=True, tag=''):` | Starts the method `mark`. It draws one data mark at `x`, `y`: a circle, a square or a triangle with the radius `r`. |
| 179 | `        t = '<title>%s</title>' % title if title else ''` | `t`: a title element with the text `title`, or nothing, as in line 164. |
| 180 | `        a = 'fill="%s" stroke="%s" stroke-width="1.5"' % (col, SURF)` | `a`: the shared look of a mark: the fill colour, and a border of 1.5 pixels in the background colour. |
| 181 | `        if shape == 'circle':` | For the shape `circle`: |
| 182 | `            self.out.append('<circle cx="%.1f" cy="%.1f" r="%s" %s>%s</circle>' % (x, y, r, a, t))` | appends a circle element with the centre and the radius. |
| 183 | `        elif shape == 'square':` | For the shape `square`: |
| 184 | `            self.out.append('<rect x="%.1f" y="%.1f" width="%s" height="%s" %s>%s</rect>' % (` | appends a rectangle element. The line goes on in line 185. |
| 185 | `                x - r, y - r, 2 * r, 2 * r, a, t))` | Continues line 184: the corner at `x - r`, `y - r` and a side of `2 * r`. |
| 186 | `        else:` | For any other shape, the triangle: |
| 187 | `            self.out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" %s>%s</polygon>' % (` | appends a polygon element with three points. The line goes on in line 188. |
| 188 | `                x, y - r - 1, x - r - 1, y + r, x + r + 1, y + r, a, t))` | Continues line 187: the tip above the centre, and the two lower corners to the left and to the right below the centre. |
| 189 | `        if check:` | Only when `check` is true: |
| 190 | `            self.boxes.append((x - r, y - r, x + r, y + r, 'mark', tag))` | adds the box of the mark to `self.boxes`: a square with the side `2 * r` around the centre, with the kind `mark` and the text `tag`. |
| 192 | `    def overlaps(self):` | Starts the method `overlaps`. It returns the list of overlap problems of the figure. |
| 193 | `        """Pairs (text, text) and (text, mark) whose boxes intersect."""` | The description text of `overlaps`: it reports the pairs of two texts, and of a text and a mark, whose boxes intersect. |
| 194 | `        res = []` | `res`: the result list, empty at first. |
| 195 | `        for i, a in enumerate(self.boxes):` | Starts a loop over all boxes. `i` is the position of the box `a` in the list. |
| 196 | `            for b in self.boxes[i + 1:]:` | Starts an inner loop over the boxes `b` that stand after `a`. So each pair is tested once. |
| 197 | `                if a[4] == 'mark' and b[4] == 'mark':` | When both boxes are marks: |
| 198 | `                    continue` | skips the pair. Two marks may overlap. |
| 199 | `                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:` | Tests whether the two boxes intersect: each one starts before the other one ends, in the x direction and in the y direction. |
| 200 | `                    res.append((self.name, a[4], a[5], b[4], b[5]))` | Adds a problem entry: the name of the figure, and the kind and the text of both boxes. |
| 201 | `        for b in self.boxes:` | Starts a second loop over all boxes. |
| 202 | `            if b[4] == 'text' and (b[0] < 0 or b[2] > self.w or b[1] < 0 or b[3] > self.h):` | Tests whether a text box reaches outside the figure: left of 0, right of the width, above 0 or below the height. |
| 203 | `                res.append((self.name, 'text outside the figure', b[5], '', ''))` | Adds a problem entry with the words `text outside the figure` and the text. |
| 204 | `        return res` | Returns the list of problems. |
| 206 | `    def done(self):` | Starts the method `done`. It returns the complete SVG text of the figure. |
| 207 | `        return '\n'.join(self.out) + '\n</svg>'` | Joins the pieces with line ends and adds the closing tag. |

### `fig1`: scales, switch band, grid and axes (lines 210 to 250)

| Line | Source | Explanation |
|---:|---|---|
| 210 | `# ---------------------------------------------------------------- Figure 1` | Comment: Figure 1 starts here. |
| 211 | `def fig1():` | Starts the function `fig1`. It draws Figure 1: the total at 64+56 of each loop variant against its window depth. |
| 212 | `    s = Svg('Figure 1', 920, 480, 'Total read rate at 64+56 against the measured window depth of each loop variant')` | `s`: a new figure of 920 by 480 pixels with the name `Figure 1` and a label text for screen readers. |
| 213 | `    X0, X1, YT, YB = 64, 694, 30, 390` | The plot area of the main panel in pixels: x from 64 to 694, y from 30 at the top to 390 at the bottom. |
| 214 | `    PX0, PX1 = 744, 884` | The x range of a second, small panel at the right: 744 to 884 pixels. It shows the window depths of 150 to 170 lines, where only `read_1pl` lies. |
| 216 | `    def xm(v):` | Defines `xm`: the x position of a window depth in the main panel. |
| 217 | `        return X0 + (X1 - X0) * v / 45.0` | The scale of `xm`: 0 to 45 cache lines over the width of the main panel. This is 14 pixels per cache line. |
| 219 | `    def xs(v):` | Defines `xs`: the x position of a window depth in the side panel. |
| 220 | `        return PX0 + (PX1 - PX0) * (v - 150) / 20.0` | The scale of `xs`: 150 to 170 cache lines over the width of the side panel. This is 7 pixels per cache line, half the scale of the main panel. |
| 222 | `    def yy(v):` | Defines `yy`: the y position of a total. |
| 223 | `        return YB - (YB - YT) * v / 600.0` | The scale of `yy`: 0 GB/s at the bottom and 600 GB/s at the top. This is 0.6 pixels per GB/s. The axis starts at 0. |
| 225 | `    # switch band` | Comment: the switch band. |
| 226 | `    s.rect(xm(28), YT, xm(32) - xm(28), YB - YT, '#8a8880', op=0.16)` | Draws a grey band over the full height from 28 to 32 cache lines, with an opacity of 0.16. It marks the window depths at which the total changes from fast to slow. |
| 227 | `    s.text(xm(30), 44, 'switch from fast to slow', 12, 'middle', INK, bold=True)` | Writes the bold label of the band, centred at 30 cache lines. |
| 228 | `    s.text(xm(30), 58, '28–32 lines', 11, 'middle', INK2)` | Writes the second label line of the band, its range in cache lines. |
| 229 | `    # grid and y axis` | Comment: the grid and the y axis. |
| 230 | `    for v in range(0, 601, 100):` | Starts a loop over the totals 0, 100 and so on up to 600 GB/s. |
| 231 | `        s.line(X0, yy(v), X1, yy(v), GRID)` | Draws a horizontal grid line across the main panel. |
| 232 | `        s.line(PX0, yy(v), PX1, yy(v), GRID)` | Draws the same grid line across the side panel. |
| 233 | `        s.text(X0 - 6, yy(v) + 4, str(v), 11, 'end', INK2)` | Writes the tick label left of the y axis, right-aligned. |
| 234 | `    s.line(X0, YB, X1, YB, INK2)` | Draws the x axis of the main panel at the bottom. |
| 235 | `    s.line(PX0, YB, PX1, YB, INK2)` | Draws the x axis of the side panel. |
| 236 | `    s.line(X0, YT, X0, YB, INK2)` | Draws the y axis at the left edge of the main panel. |
| 237 | `    s.text(X0 - 40, 16, 'total read rate at 64+56, GB/s (axis starts at 0)', 12, 'start', INK2)` | Writes the title of the y axis above the plot. The text names the unit GB/s and says that the axis starts at 0. |
| 238 | `    for v in range(0, 46, 5):` | Starts a loop over the window depths 0, 5 and so on up to 45 cache lines. |
| 239 | `        s.line(xm(v), YB, xm(v), YB + 4, INK2)` | Draws a tick of 4 pixels below the x axis. |
| 240 | `        s.text(xm(v), YB + 17, str(v), 11, 'middle', INK2)` | Writes the tick label, centred under the tick. |
| 241 | `    for v in (150, 160, 170):` | Starts a loop over the three ticks of the side panel: 150, 160 and 170 cache lines. |
| 242 | `        s.line(xs(v), YB, xs(v), YB + 4, INK2)` | Draws the tick of 4 pixels. |
| 243 | `        s.text(xs(v), YB + 17, str(v), 11, 'middle', INK2)` | Writes the tick label. |
| 244 | `    # axis break` | Comment: the axis break. |
| 245 | `    for dx in (0, 8):` | Starts a loop that runs twice, with a shift of 0 and of 8 pixels. |
| 246 | `        s.line(710 + dx, YB + 7, 718 + dx, YB - 7, INK2, 1.5)` | Draws a short slanted line across the x axis between the two panels. The two lines together are the sign for a break of the axis. |
| 247 | `    s.text(719, YB - 14, 'axis break', 10, 'middle', INK2)` | Writes the words `axis break` above that sign. |
| 248 | `    s.text((X0 + X1) / 2, YB + 38,` | Starts the title of the x axis, centred under the main panel. The call goes on in lines 249 to 250. |
| 249 | `           'measured window depth, cache lines (mark = middle of the measured range, thin bar = the range)',` | Continues line 248: the text. It names the unit, cache lines. It also says that a mark stands at the middle of the measured range and that the thin bar shows the range. |
| 250 | `           12, 'middle', INK2)` | Continues line 248: font size 12, centred, in the grey `INK2`. |

### `fig1`: the place and the bars of each mark (lines 251 to 293)

| Line | Source | Explanation |
|---:|---|---|
| 251 | `    # points` | Comment: the points. |
| 252 | `    named = {}` | `named`: a dictionary from the short name of a variant to the position of its mark. |
| 253 | `    LAB = ('oldread', 'asmread', 'read_nop72', 'read_nop256', 'read_iadd16', 'read_1pl')` | `LAB`: the six variants that get a text label in the figure. |
| 254 | `    # Several variants have the same window range and nearly the same total. Their marks would cover each other.` | Comment: several variants have the same window range and nearly the same total. Their marks would cover each other. |
| 255 | `    # place(): a mark keeps its y. It moves sideways by the smallest step that leaves SEP px to every placed mark.` | Comment: the rule of `place`. A mark keeps its height. It moves sideways by the smallest step that leaves `SEP` pixels to every mark that is already placed. |
| 256 | `    # The six labelled variants are placed first, so they stay at their true x.` | Comment: the six labelled variants are placed first. So they stay at their true x position. |
| 257 | `    SEP, STEP = 6.0, 3.0` | `SEP`: 6 pixels, the smallest distance between two marks. `STEP`: 3 pixels, the size of one sideways step. |
| 258 | `    placed = []` | `placed`: the positions of the marks that are already placed. |
| 260 | `    def place(mx, my):` | Starts the inner function `place`. It gets the true position of a mark and returns the sideways shift in pixels. |
| 261 | `        for k in range(0, 13):` | Starts a loop over the size `k` of the shift, from 0 to 12 steps. |
| 262 | `            for dx in ((0,) if k == 0 else (-k * STEP, k * STEP)):` | For `k` equal to 0 it tries no shift. For a larger `k` it tries first the shift to the left and then the same shift to the right. |
| 263 | `                if all(abs(mx + dx - px) >= SEP or abs(my - py) >= SEP for px, py in placed):` | A position is free when every placed mark is at least `SEP` pixels away in x, or at least `SEP` pixels away in y. |
| 264 | `                    placed.append((mx + dx, my))` | Records the free position in `placed`. |
| 265 | `                    return dx` | Returns the shift of that position. |
| 266 | `        raise SystemExit('Figure 1: no free place for a mark')` | When no position is free up to 12 steps (36 pixels): ends the script with the message `Figure 1: no free place for a mark`. |
| 268 | `    s.maxdx = 0.0` | `s.maxdx`: the largest shift so far, in pixels. The caption of the figure states it (lines 734 to 736). |
| 269 | `    s.moved = 0` | `s.moved`: the number of marks that were shifted. |
| 270 | `    for name, holds, lo, hi, rmin, rmax, n, state, cls in sorted(` | Starts the loop over the rows of `F2` in a sorted order. The call goes on in line 271. |
| 271 | `            F2, key=lambda q: (q[0].split(' ')[0] not in LAB, q[2] + q[3], q[4])):` | Continues line 270: the sort key. The six labelled variants come first. Then the order follows the sum of the two ends of the window range, then the smallest total. |
| 272 | `        col, shape, _ = CLS[cls]` | Takes the colour and the shape of the class of the row. This loop uses the colour only. |
| 273 | `        fx = xs if lo > 100 else xm` | `fx`: the x scale of the row. It is `xs`, the side panel, when the window is above 100 cache lines, and `xm` if not. |
| 274 | `        mx, my = fx((lo + hi) / 2.0), yy((rmin + rmax) / 2.0)` | `mx`, `my`: the true position of the mark. The x value is the middle of the window range, `(lo + hi) / 2.0`. The y value is the middle of the range of the total, `(rmin + rmax) / 2.0`. These midpoints are group 3 of the header text. |
| 275 | `        dx = place(mx, my)` | `dx`: the sideways shift that `place` gives for this position. |
| 276 | `        key = name.split(' ')[0]` | `key`: the first word of the name, such as `asmread` for the row `asmread (= new C read)`. |
| 277 | `        assert key not in LAB or dx == 0` | Checks that a labelled variant was not shifted. If one was, the script stops with an error. |
| 278 | `        s.maxdx = max(s.maxdx, abs(dx))` | Updates the largest shift. |
| 279 | `        s.moved += 1 if dx else 0` | Counts the mark when its shift is not 0. |
| 280 | `        s.line(fx(lo), my, fx(hi), my, col, 1.2, op=0.55)` | Draws the thin horizontal bar of the mark, from the low to the high end of the window range, at the height of the mark. It is not shifted, so it shows the true range. |
| 281 | `        s.line(mx + dx, yy(rmin), mx + dx, yy(rmax), col, 2.5)` | Draws the vertical bar at the shifted x position, from the smallest to the largest total. |
| 282 | `        named[key] = (mx + dx, my)` | Stores the shifted position of the mark under its short name. |
| 283 | `    s.px_per_line = (X1 - X0) / 45.0` | `s.px_per_line`: 14 pixels per cache line, the scale of the main panel. The caption uses it to give the largest shift in cache lines. |
| 284 | `    # the six labelled variants are drawn last, so that no other mark hides them` | Comment: the six labelled variants are drawn last. So no other mark hides them. |
| 285 | `    for name, holds, lo, hi, rmin, rmax, n, state, cls in sorted(F2, key=lambda q: q[0].split(' ')[0] in LAB):` | Starts a second loop over the rows of `F2`, sorted with the labelled variants last. |
| 286 | `        col, shape, _ = CLS[cls]` | Takes the colour and the shape of the class. |
| 287 | `        mx, my = named[name.split(' ')[0]]` | Takes the stored position of the mark. |
| 288 | `        key = name.split(' ')[0]` | `key`: the first word of the name. |
| 289 | `        lab = key in LAB` | `lab`: true for a labelled variant. No later line uses it. |
| 290 | `        s.mark(mx, my, shape, col, r=4.5, check=True, tag=key,` | Draws the mark with a radius of 4.5 pixels, in the colour and the shape of its class. The call goes on in lines 291 to 292. |
| 291 | `               title='%s: window %d to %d lines, total %.1f to %.1f GB/s, n = %d intervals, %s' % (` | Continues line 290: the text that the browser shows when the pointer rests on the mark. It holds the name, the window range in cache lines, the range of the total in GB/s, the number of intervals and the state. |
| 292 | `                   name, lo, hi, rmin, rmax, n, state))` | Continues line 290: the values of the row for that text. |

### `fig1`: labels, notes and legend (lines 294 to 331)

| Line | Source | Explanation |
|---:|---|---|
| 294 | `    def leader(x1, y1, key):` | Starts the inner function `leader`. It draws a thin line from a point near a label to the mark of a variant. |
| 295 | `        x2, y2 = named[key]` | Takes the position of the mark. |
| 296 | `        s.line(x1, y1, x2, y2, INK2, 0.8)` | Draws the line in grey with a width of 0.8 pixels. |
| 298 | `    # direct labels (six named variants)` | Comment: the labels of the six named variants, written next to the marks. |
| 299 | `    x, y = named['read_nop256']` | Takes the position of the mark of `read_nop256`. |
| 300 | `    s.text(x + 12, y + 4, 'read_nop256: 543.9–549.0 GB/s', 12, 'start', INK, halo=True)` | Writes its label right of the mark: the name and the range of its total. The range is fixed text. It repeats the values of the row in `F2`. |
| 301 | `    leader(258, 84, 'read_iadd16')` | Draws a leader line to the mark of `read_iadd16`. |
| 302 | `    s.text(70, 84, 'read_iadd16: 469.2–469.7 GB/s', 12, 'start', INK, halo=True)` | Writes the label of `read_iadd16` at the left of the plot, with its range as fixed text. |
| 303 | `    leader(250, 142, 'oldread')` | Draws a leader line to the mark of `oldread`. |
| 304 | `    s.text(70, 150, 'old read loop (oldread):', 12, 'start', INK, bold=True, halo=True)` | Writes the first label line of the old read loop, in bold. |
| 305 | `    s.text(70, 165, '465.5–470.1 GB/s', 12, 'start', INK, halo=True)` | Writes its second label line, the range of the total as fixed text. |
| 306 | `    leader(516, 130, 'read_nop72')` | Draws a leader line to the mark of `read_nop72`. |
| 307 | `    s.text(519, 134, 'read_nop72: 459.0–459.3', 12, 'start', INK, halo=True)` | Writes the label of `read_nop72`, with its range as fixed text. |
| 308 | `    x, y = named['asmread']` | Takes the position of the mark of `asmread`. |
| 309 | `    s.line(x, 247, x, y + 6, INK2, 0.8)` | Draws a vertical line from a point 6 pixels below that mark down to a point above the label of line 310. |
| 310 | `    s.text(500, 260, 'new load-only loop (asmread):', 12, 'start', INK, bold=True, halo=True)` | Writes the first label line of the new load-only loop, in bold. |
| 311 | `    s.text(500, 275, '288.5–309.8 GB/s', 12, 'start', INK, halo=True)` | Writes its second label line, the range of the total as fixed text. |
| 312 | `    x, y = named['read_1pl']` | Takes the position of the mark of `read_1pl`. |
| 313 | `    s.text(x, y + 22, 'read_1pl', 12, 'middle', INK, halo=True)` | Writes its name under the mark, centred. |
| 314 | `    s.text(x, y + 37, '230.2–235.0 GB/s', 12, 'middle', INK, halo=True)` | Writes the range of its total under the name, as fixed text. |
| 315 | `    # plain-language annotation` | Comment: the notes in plain language. |
| 316 | `    s.text(70, 318, 'Measured range at or below 24–28 lines:', 12, 'start', INK2)` | Writes the first line of the note at the left. It names the variants whose measured range is at or below 24 to 28 cache lines. |
| 317 | `    s.text(70, 334, 'fast, 459 GB/s or more', 12, 'start', INK, bold=True)` | Writes the second line in bold: these variants are fast. It gives the lower limit of their total. |
| 318 | `    s.text(530, 318, 'Window of 32 lines or more:', 12, 'start', INK2)` | Writes the first line of the note at the right. It names the variants with a window of 32 cache lines or more. |
| 319 | `    s.text(530, 334, 'slow, 280–310 GB/s', 12, 'start', INK, bold=True)` | Writes the second line in bold: these variants are slow. It gives the range of their total. |
| 320 | `    s.text(530, 350, '(read_1pl: 230–235 GB/s)', 12, 'start', INK2)` | Writes the third line: the lower range of `read_1pl`. |
| 321 | `    # legend` | Comment: the legend. |
| 322 | `    lx = 64` | `lx`: the x position of the next legend entry. It starts at 64 pixels. |
| 323 | `    for cls in ('nop', 'add', 'load'):` | Starts a loop over the three classes. |
| 324 | `        col, shape, txt = CLS[cls]` | Takes the colour, the shape and the legend text of the class. |
| 325 | `        s.mark(lx + 5, 456, shape, col, r=4.5, check=False)` | Draws a sample mark. It does not take part in the overlap check. |
| 326 | `        s.text(lx + 16, 460, txt, 12, 'start', INK2)` | Writes the legend text right of the sample mark. |
| 327 | `        lx += 16 + 0.58 * 12 * len(txt) + 22` | Moves `lx` to the right by the space of the mark, the estimated width of the text and a gap of 22 pixels. |
| 328 | `    s.text(lx, 460, 'vertical bar = min to max', 12, 'start', INK2)` | Writes the last legend entry: the vertical bar shows the smallest and the largest total. |
| 329 | `    return s` | Returns the figure object. |

### `fig2`: two bars per pair of loops (lines 332 to 375)

| Line | Source | Explanation |
|---:|---|---|
| 332 | `# ---------------------------------------------------------------- Figure 2` | Comment: Figure 2 starts here. |
| 333 | `def fig2():` | Starts the function `fig2`. It draws Figure 2. For each of the nine pairs of `F3` it draws one bar for the sum of mesh 0 and one bar for the sum of mesh 1. |
| 334 | `    s = Svg('Figure 2', 920, 440, 'Read rate of each mesh for nine pairs of loops')` | `s`: a new figure of 920 by 440 pixels with the name `Figure 2` and a label text for screen readers. |
| 335 | `    X0, X1, YT, YB = 96, 900, 46, 336` | The plot area in pixels: x from 96 to 900, y from 46 at the top to 336 at the bottom. |
| 336 | `    gw = (X1 - X0) / 9.0` | `gw`: the width of one group of two bars, one ninth of the plot width. This is about 89 pixels. |
| 338 | `    def yy(v):` | Defines `yy`: the y position of a rate. |
| 339 | `        return YB - (YB - YT) * v / 450.0` | The scale of `yy`: 0 GB/s at the bottom and 450 GB/s at the top. The axis starts at 0. |
| 341 | `    for i, (a, b, m0, m1, tot) in enumerate(F3):` | Starts a loop over the pairs of `F3`. `i` is the position of the pair, from 0. |
| 342 | `        if a == 'asmread' and b != 'asmread':` | For a pair in which mesh 0 runs `asmread` and mesh 1 runs another loop: |
| 343 | `            s.rect(X0 + i * gw + 3, YT, gw - 6, YB - YT + 46, '#8a8880', op=0.13)` | draws a grey shade behind the group, with an opacity of 0.13. It reaches 46 pixels below the axis, so it also lies behind the two loop names of the group. |
| 344 | `    for v in range(0, 451, 100):` | Starts a loop over the rates 0, 100 and so on up to 400 GB/s. |
| 345 | `        s.line(X0, yy(v), X1, yy(v), GRID)` | Draws a horizontal grid line. |
| 346 | `        s.text(X0 - 6, yy(v) + 4, str(v), 11, 'end', INK2)` | Writes the tick label left of the y axis. |
| 347 | `    s.text(X0 - 80, 16, 'sum of the read rate of one mesh, GB/s (axis starts at 0)', 12, 'start', INK2)` | Writes the title of the y axis above the plot. It names the value: the sum of the read rate of one mesh in GB/s. |
| 348 | `    s.line(X0, yy(F3_REF), X1, yy(F3_REF), INK, 1.2, dash='6 4')` | Draws a dashed line at the height of `F3_REF`, 348 GB/s. This is the rate of mesh 0 alone with the load-only loop. |
| 349 | `    s.text(X0 + 4, 36, 'dashed line: mesh 0 alone with the load-only loop = %d GB/s' % F3_REF, 12, 'start', INK)` | Writes the label of the dashed line above the plot. It puts in the value of `F3_REF`. |
| 350 | `    s.line(X0 + 30, 40, X0 + 30, yy(F3_REF), INK2, 0.8)` | Draws a short vertical line from that label down to the dashed line. |
| 351 | `    s.text(X0 - 6, YB + 20, 'mesh 0 loop', 11, 'end', INK2)` | Writes the row title `mesh 0 loop` left of the first line of loop names. |
| 352 | `    s.text(X0 - 6, YB + 36, 'mesh 1 loop', 11, 'end', INK2)` | Writes the row title `mesh 1 loop` left of the second line of loop names. |
| 353 | `    for i, (a, b, m0, m1, tot) in enumerate(F3):` | Starts the loop that draws the nine groups. |
| 354 | `        cx = X0 + (i + 0.5) * gw` | `cx`: the x position of the middle of the group. |
| 355 | `        for k, (v, col, nm) in enumerate(((m0, C1, 'mesh 0'), (m1, C2, 'mesh 1'))):` | Starts a loop over the two bars of the group: the mesh 0 sum in blue and the mesh 1 sum in orange. |
| 356 | `            bx = cx - 33 + k * 34` | `bx`: the left edge of the bar. The mesh 0 bar starts 33 pixels left of the middle. The mesh 1 bar starts 1 pixel right of it. |
| 357 | `            s.rect(bx, yy(v), 32, YB - yy(v), col, rx=3,` | Draws the bar: 32 pixels wide, from the value down to the axis, with round corners of 3 pixels. The call goes on in lines 358 to 359. |
| 358 | `                   title='%s runs %s, %s runs %s: %s sum %.1f GB/s, total %.1f GB/s' % (` | Continues line 357: the text that the browser shows when the pointer rests on the bar. It names both loops, the mesh, its sum and the total of the pair. |
| 359 | `                       'mesh 0', a, 'mesh 1', b, nm, v, tot))` | Continues line 357: the values for that text. |
| 360 | `            s.rect(bx, YB - 4, 32, 4, col)` | Draws a strip of 4 pixels at the foot of the bar in the same colour. It makes the lower corners of the bar square. |
| 361 | `            s.text(bx + 16, yy(v) - 4, '%.1f' % v, 10.5, 'middle', INK, halo=True)` | Writes the value above the bar, with one decimal. |
| 362 | `        s.text(cx, 66, 'total %.1f' % tot, 11, 'middle', INK, bold=True, halo=True)` | Writes the total of the pair in bold near the top of the plot. |
| 363 | `        s.text(cx, YB + 20, SHORT[a], 11, 'middle', INK)` | Writes the short name of the mesh 0 loop under the axis (line 73). |
| 364 | `        s.text(cx, YB + 36, SHORT[b], 11, 'middle', INK)` | Writes the short name of the mesh 1 loop one text line lower. |
| 365 | `    s.line(X0, YB, X1, YB, INK2)` | Draws the x axis. |
| 366 | `    # legend and annotation` | Comment: the legend and the note. |
| 367 | `    s.rect(X0, 395, 12, 12, C1, rx=2)` | Draws the blue sample square of the legend. |
| 368 | `    s.text(X0 + 18, 406, 'mesh 0 sum (64 threads)', 12, 'start', INK2)` | Writes its text: the mesh 0 sum, with its number of threads, 64. |
| 369 | `    s.rect(X0 + 190, 395, 12, 12, C2, rx=2)` | Draws the orange sample square of the legend. |
| 370 | `    s.text(X0 + 208, 406, 'mesh 1 sum (56 threads)', 12, 'start', INK2)` | Writes its text: the mesh 1 sum, with its number of threads, 56. |
| 371 | `    s.text(X0, 428, 'Shaded groups: the load-only loop on mesh 0 reads as if it were alone. '` | Starts the note in bold under the legend. The call goes on in line 372. The text explains the shaded groups: there mesh 0 reads as if it were alone. |
| 372 | `           'Mesh 1 is squeezed to 108–116 GB/s.', 12, 'start', INK, bold=True)` | Continues line 371: the second sentence of the note. It gives the range to which the sum of mesh 1 falls, as fixed text. |
| 373 | `    return s` | Returns the figure object. |

### `fig3`: the estimated lines in flight of each case (lines 376 to 442)

| Line | Source | Explanation |
|---:|---|---|
| 376 | `# ---------------------------------------------------------------- Figure 3` | Comment: Figure 3 starts here. |
| 377 | `def fig3():` | Starts the function `fig3`. It draws Figure 3: one row per case of `F4`, with the estimated lines in flight of mesh 0 and of mesh 1 on a common scale. |
| 378 | `    rows = len(F4)` | `rows`: the number of cases, 7. |
| 379 | `    RH, Y0 = 48, 78` | `RH`: the height of one row, 48 pixels. `Y0`: the top of the first row, 78 pixels. |
| 380 | `    H = Y0 + rows * RH + 128` | `H`: the height of the figure. It is the top margin plus the rows plus 128 pixels for the axis, the legend and the notes. |
| 381 | `    s = Svg('Figure 3', 920, H, 'Estimated lines in flight per core for each case of the latency probe')` | `s`: a new figure with a width of 920 pixels and the height `H`, with the name `Figure 3`. |
| 382 | `    X0, X1 = 330, 700` | The x range of the scale in pixels: 330 to 700. |
| 384 | `    def xx(v):` | Defines `xx`: the x position of a number of lines in flight. |
| 385 | `        return X0 + (X1 - X0) * v / 30.0` | The scale of `xx`: 0 to 30 lines in flight over these 370 pixels. |
| 387 | `    yb = Y0 + rows * RH` | `yb`: the y position of the bottom of the last row. |
| 388 | `    s.rect(xx(6.5), Y0 - 8, xx(SLOW_MAX) - xx(6.5), yb - Y0 + 8, C2, op=0.13)` | Draws an orange band from 6.5 to `SLOW_MAX` lines in flight over all rows, with an opacity of 0.13. It is the range of slow or squeezed meshes. |
| 389 | `    s.rect(xx(FAST_MIN), Y0 - 8, xx(25.3) - xx(FAST_MIN), yb - Y0 + 8, C1, op=0.11)` | Draws a blue band from `FAST_MIN` to 25.3 lines in flight, with an opacity of 0.11. It is the range of fast meshes. |
| 390 | `    s.text(xx(7.85), Y0 - 30, 'slow or squeezed meshes', 12, 'middle', INK, bold=True)` | Writes the bold title of the orange band, centred at 7.85, the middle of the band. |
| 391 | `    s.text(xx(7.85), Y0 - 15, '6.5–9.2 lines (est.)', 11, 'middle', INK2)` | Writes the range of the orange band under its title, as fixed text with the mark of an estimate. |
| 392 | `    s.text(xx(20.1), Y0 - 30, 'fast meshes', 12, 'middle', INK, bold=True)` | Writes the bold title of the blue band, centred at 20.1, the middle of the band. |
| 393 | `    s.text(xx(20.1), Y0 - 15, '14.9–25.3 lines (est.)', 11, 'middle', INK2)` | Writes the range of the blue band under its title, as fixed text with the mark of an estimate. |
| 394 | `    s.text(16, Y0 - 30, 'case', 12, 'start', INK, bold=True)` | Writes the title of the left column, the case. |
| 395 | `    s.text(16, Y0 - 15, 'loop on mesh 0 \| loop on mesh 1', 11, 'start', INK2)` | Writes its second line: the column gives the loop on mesh 0 and the loop on mesh 1. |
| 396 | `    s.text(716, Y0 - 30, 'time of one DRAM read', 12, 'start', INK, bold=True)` | Writes the title of the right column, the time of one read from memory. |
| 397 | `    s.text(716, Y0 - 15, 'by the probe, CPU 2 \| CPU 66', 11, 'start', INK2)` | Writes its second line: the probe measured this time, on CPU 2 and on CPU 66. |
| 398 | `    for v in range(0, 31, 5):` | Starts a loop over the scale values 0, 5 and so on up to 30. |
| 399 | `        s.line(xx(v), Y0 - 8, xx(v), yb, GRID)` | Draws a vertical grid line over all rows. |
| 400 | `        s.text(xx(v), yb + 16, str(v), 11, 'middle', INK2)` | Writes the tick label under the rows. |
| 401 | `    s.line(X0, yb, X1, yb, INK2)` | Draws the x axis under the rows. |
| 402 | `    s.text((X0 + X1) / 2, yb + 34, 'estimated lines in flight per streaming core (est.)', 12, 'middle', INK2)` | Writes the title of the x axis. It names the value as an estimate. |
| 403 | `    for i, (a, b, l0, l1, p2, p66) in enumerate(F4):` | Starts the loop over the cases of `F4`. `i` is the number of the row, from 0. |
| 404 | `        yc = Y0 + i * RH + RH / 2 - 4` | `yc`: the y position of the middle of the row, moved up by 4 pixels. |
| 405 | `        if i:` | For every row but the first: |
| 406 | `            s.line(16, Y0 + i * RH - 6, 904, Y0 + i * RH - 6, GRID)` | draws a thin line above the row, over the whole width of the figure. |
| 407 | `        s.text(16, yc - 3, 'mesh 0: ' + a, 12, 'start', INK)` | Writes the loop of mesh 0 at the left. |
| 408 | `        s.text(16, yc + 13, 'mesh 1: ' + (b if b else 'idle (no stream)'), 12, 'start', INK)` | Writes the loop of mesh 1 under it, or the words for an idle mesh when the loop is `None`. |
| 409 | `        s.text(716, yc + 5, '%.1f \| %.1f ns' % (p2, p66), 12, 'start', INK)` | Writes the two probe times in ns at the right, with one decimal each. |
| 410 | `        pts = [(l0, yc - 8, 'circle', 'mesh 0', a)]` | `pts`: the list of the points of the row. It starts with the point of mesh 0: its value, a y position 8 pixels above the middle, and a circle. |
| 411 | `        if l1 is not None:` | When mesh 1 has a value: |
| 412 | `            pts.append((l1, yc + 8, 'square', 'mesh 1', b))` | adds the point of mesh 1: its value, a y position 8 pixels below the middle, and a square. |
| 413 | `            s.line(xx(l0), yc - 8, xx(l1), yc + 8, INK2, 1.5, op=0.6)` | Draws a line between the two marks. Its length shows how far the two meshes of one case lie apart. |
| 414 | `        for v, y, shape, nm, loop in pts:` | Starts a loop over the points of the row. |
| 415 | `            col = C2 if v <= SLOW_MAX + 0.05 else C1` | Chooses the colour of the mark: orange when the value is at most `SLOW_MAX` plus 0.05, blue if not. |
| 416 | `            s.mark(xx(v), y, shape, col, r=5, tag='%s row %d' % (nm, i),` | Draws the mark with a radius of 5 pixels. The call goes on in line 417. |
| 417 | `                   title='%s runs %s: %s lines in flight per core (est.)' % (nm, loop, f1(v)))` | Continues line 416: the text for the pointer. It names the mesh, the loop and the value, which `f1` rounds to one decimal. |
| 418 | `            # the label goes to the side that the connecting line does not cross` | Comment: the label goes to the side that the connecting line does not cross. |
| 419 | `            other = [q[0] for q in pts if q[0] != v]` | `other`: the values of the row that differ from this value. |
| 420 | `            if other and other[0] > v + 3:` | When the other value is more than 3 above this value: |
| 421 | `                s.text(xx(v) - 9, y + 4, f1(v), 11, 'end', INK, halo=True)` | writes the value left of the mark, with one decimal. |
| 422 | `            else:` | In every other case: |
| 423 | `                s.text(xx(v) + 9, y + 4, f1(v), 11, 'start', INK, halo=True)` | writes the value right of the mark, with one decimal. |
| 424 | `    # legend and annotation` | Comment: the legend and the notes. |
| 425 | `    ly = yb + 58` | `ly`: the y position of the legend, 58 pixels below the rows. |
| 426 | `    s.mark(22, ly - 4, 'circle', INK2, r=5, check=False)` | Draws a grey sample circle. |
| 427 | `    s.text(33, ly, 'mesh 0', 12, 'start', INK2)` | Writes its text: a circle stands for mesh 0. |
| 428 | `    s.mark(98, ly - 4, 'square', INK2, r=5, check=False)` | Draws a grey sample square. |
| 429 | `    s.text(109, ly, 'mesh 1', 12, 'start', INK2)` | Writes its text: a square stands for mesh 1. |
| 430 | `    s.mark(178, ly - 4, 'circle', C2, r=5, check=False)` | Draws an orange sample circle. |
| 431 | `    s.text(189, ly, 'slow or squeezed', 12, 'start', INK2)` | Writes its text: orange stands for a slow or squeezed mesh. |
| 432 | `    s.mark(308, ly - 4, 'circle', C1, r=5, check=False)` | Draws a blue sample circle. |
| 433 | `    s.text(319, ly, 'fast', 12, 'start', INK2)` | Writes its text: blue stands for a fast mesh. |
| 434 | `    s.text(16, ly + 24, 'A request is not slower in the slow state: 203–211 ns against 238–297 ns.',` | Starts the main note in bold. The call goes on in line 435. The text says that a request is not slower in the slow state. It gives two ranges of the probe time in ns as fixed text. They are rounded forms of the probe times in `F4`. |
| 435 | `           12.5, 'start', INK, bold=True)` | Continues line 434: font size 12.5, left-aligned, bold. |
| 436 | `    s.text(16, ly + 42, '203–211 ns: load-only loop on all cores (row 1). 238–297 ns: padded loops on all cores '` | Starts the second note line. It says which rows give the two ranges. The call goes on in line 437. |
| 437 | `           '(rows 5 and 6),', 11.5, 'start', INK2)` | Continues line 436: the end of the text, and the font size 11.5 in grey. |
| 438 | `    s.text(16, ly + 58, 'and mesh 0 with the load-only loop against read_nop256 (row 4). '` | Starts the third note line. It names the mixed case of row 4 and points to the column at the right. The call goes on in line 439. |
| 439 | `           'The other values are in the column at the right.', 11.5, 'start', INK2)` | Continues line 438: the end of the text, and the font size 11.5 in grey. |
| 440 | `    return s` | Returns the figure object. |

### `sgn` and `fig4`: sequential order against scrambled order (lines 443 to 514)

| Line | Source | Explanation |
|---:|---|---|
| 443 | `# ---------------------------------------------------------------- Figure 4` | Comment: Figure 4 starts here. |
| 444 | `def sgn(v):` | Starts the function `sgn`. It writes a number with its sign. |
| 445 | `    """Signed value with one decimal and a real minus sign."""` | The description text of `sgn`: one decimal, and a real minus sign. |
| 446 | `    return ('+' if v >= 0 else '−') + '%.1f' % abs(v)` | Returns `+` for a value of 0 or more, and the minus sign of typography for a negative value. After the sign stands the size of the value with one decimal. |
| 449 | `def fig4():` | Starts the function `fig4`. It draws Figure 4: for each of three paddings, the total at 64+56 in sequential order and in scrambled order. |
| 450 | `    RH, Y0 = 62, 84` | `RH`: the height of one row, 62 pixels. `Y0`: the top of the first row, 84 pixels. |
| 451 | `    rows = len(FIG4)` | `rows`: the number of rows of `FIG4`, 3. |
| 452 | `    yb = Y0 + rows * RH` | `yb`: the y position of the bottom of the last row. |
| 453 | `    s = Svg('Figure 4', 920, yb + 138,` | `s`: a new figure with a width of 920 pixels and the name `Figure 4`. Its height is `yb` plus 138 pixels. The call goes on in line 454. |
| 454 | `            'Total read rate at 64+56 in sequential order and in scrambled order for three paddings')` | Continues line 453: the label text for screen readers. |
| 455 | `    X0, X1 = 232, 692` | The x range of the scale in pixels: 232 to 692. |
| 457 | `    def xx(v):` | Defines `xx`: the x position of a total. |
| 458 | `        return X0 + (X1 - X0) * v / 600.0` | The scale of `xx`: 0 to 600 GB/s over these 460 pixels. |
| 460 | `    s.text(16, Y0 - 34, 'loop', 12, 'start', INK, bold=True)` | Writes the title of the left column, the loop. |
| 461 | `    s.text(16, Y0 - 19, 'padding per 256 B \| window depth', 11, 'start', INK2)` | Writes its second line: the column gives the padding per 256 B and the window depth. |
| 462 | `    s.text(716, Y0 - 34, 'scrambled minus sequential', 12, 'start', INK, bold=True)` | Writes the title of the right column: the scrambled total minus the sequential total. |
| 463 | `    s.text(716, Y0 - 19, 'total, GB/s', 11, 'start', INK2)` | Writes its second line, the unit GB/s. |
| 464 | `    for v in range(0, 601, 100):` | Starts a loop over the totals 0, 100 and so on up to 600 GB/s. |
| 465 | `        s.line(xx(v), Y0 - 8, xx(v), yb, GRID)` | Draws a vertical grid line over all rows. |
| 466 | `        s.text(xx(v), yb + 16, str(v), 11, 'middle', INK2)` | Writes the tick label under the rows. |
| 467 | `    s.line(X0, yb, X1, yb, INK2)` | Draws the x axis under the rows. |
| 468 | `    s.text((X0 + X1) / 2, yb + 34, 'total read rate at 64+56, GB/s (axis starts at 0)', 12, 'middle', INK2)` | Writes the title of the x axis: the total read rate at 64+56 in GB/s. The text says that the axis starts at 0. |
| 469 | `    seq, scr = [], []` | `seq` and `scr`: two lists of points, one for the sequential order and one for the scrambled order. |
| 470 | `    for i, (pad, lo, hi, s0, s1, src, rnd) in enumerate(FIG4):` | Starts a first loop over the rows of `FIG4`. It only computes the positions of the marks. |
| 471 | `        yc = Y0 + i * RH + RH / 2 - 4` | `yc`: the y position of the middle of the row, moved up by 4 pixels. |
| 472 | `        seq.append((xx((s0 + s1) / 2.0), yc + 9))` | Adds the sequential point of the row. Its x position is that of the middle of the low and the high sequential total. It lies 9 pixels below the middle of the row. |
| 473 | `        scr.append((xx(rnd), yc - 9))` | Adds the scrambled point of the row. Its x position is that of the scrambled total. It lies 9 pixels above the middle of the row. |
| 474 | `    # the two curves: one line per order, through the three rows` | Comment: the two curves. Each order gets one line through the three rows. |
| 475 | `    for pts, col in ((seq, C1), (scr, C2)):` | Starts a loop over the two point lists: the sequential one in blue and the scrambled one in orange. |
| 476 | `        s.raw('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-opacity="0.55" '` | Adds a line through the three points of the list, 2 pixels wide with an opacity of 0.55. The call goes on in line 477. |
| 477 | `              'stroke-linejoin="round"/>' % (' '.join('%.1f,%.1f' % q for q in pts), col))` | Continues line 476: the points as text with one decimal, and the colour. |
| 478 | `    for i, (pad, lo, hi, s0, s1, src, rnd) in enumerate(FIG4):` | Starts the second loop over the rows of `FIG4`. It writes the texts and draws the marks. |
| 479 | `        yc = Y0 + i * RH + RH / 2 - 4` | `yc`: the y position of the middle of the row, as in line 471. |
| 480 | `        if i:` | For every row but the first: |
| 481 | `            s.line(16, Y0 + i * RH - 6, 904, Y0 + i * RH - 6, GRID)` | draws a thin line above the row, over the whole width of the figure. |
| 482 | `        s.text(16, yc - 3, pad, 12, 'start', INK, bold=True)` | Writes the padding of the row in bold at the left. |
| 483 | `        s.text(16, yc + 13, 'window %d–%d lines' % (lo, hi), 12, 'start', INK2)` | Writes the window range of the row in cache lines under it. |
| 484 | `        one = '%.1f' % s0 == '%.1f' % s1` | `one`: true when the low and the high sequential total are equal after rounding to one decimal. |
| 485 | `        slab = '%.1f' % s0 if one else rng(s0, s1)` | `slab`: the label of the sequential value. It is one number when `one` is true. If not, it is the range that `rng` writes. |
| 486 | `        (qx, qy), (rx, ry) = seq[i], scr[i]` | Takes the positions of the two marks of the row. |
| 487 | `        s.mark(qx, qy, 'circle', C1, r=5, tag='sequential row %d' % i,` | Draws a blue circle for the sequential value. The call goes on in line 488. |
| 488 | `               title='%s, sequential order: %s GB/s (%s)' % (pad, slab, src))` | Continues line 487: the text for the pointer, with the padding, the value and its source. |
| 489 | `        s.mark(rx, ry, 'square', C2, r=5, tag='scrambled row %d' % i,` | Draws an orange square for the scrambled value. The call goes on in line 490. |
| 490 | `               title='%s, scrambled order: %.1f GB/s (one 10 s interval)' % (pad, rnd))` | Continues line 489: the text for the pointer. It says that the value is one interval of 10 s. |
| 491 | `        # labels go to the outer side of each mark. In a row where the marks are close, both go to the right.` | Comment: a label goes to the outer side of its mark. In a row where the two marks are close, both labels go to the right. |
| 492 | `        near = abs(qx - rx) < 60` | `near`: true when the two marks are less than 60 pixels apart. |
| 493 | `        if near or qx > rx:` | When the marks are near, or the sequential mark is the right one of the two: |
| 494 | `            s.text(qx + 9, qy + 4, slab, 11, 'start', INK, halo=True)` | writes the sequential label right of its mark. |
| 495 | `        else:` | If not: |
| 496 | `            s.text(qx - 9, qy + 4, slab, 11, 'end', INK, halo=True)` | writes the sequential label left of its mark. |
| 497 | `        if near or rx > qx:` | When the marks are near, or the scrambled mark is the right one of the two: |
| 498 | `            s.text(rx + 9, ry + 4, '%.1f' % rnd, 11, 'start', INK, halo=True)` | writes the scrambled value right of its mark, with one decimal. |
| 499 | `        else:` | If not: |
| 500 | `            s.text(rx - 9, ry + 4, '%.1f' % rnd, 11, 'end', INK, halo=True)` | writes the scrambled value left of its mark. |
| 501 | `        s.text(716, yc + 5, sgn(rnd - s0) if one else '%s to %s' % (sgn(rnd - s1), sgn(rnd - s0)), 12, 'start', INK)` | Writes the right column: the scrambled total minus the sequential total, with a sign (`sgn`). When the sequential value is a range, the text gives two differences, the one to the high end first and the one to the low end second. |
| 502 | `    ly = yb + 60` | `ly`: the y position of the legend, 60 pixels below the rows. |
| 503 | `    s.mark(22, ly - 4, 'circle', C1, r=5, check=False)` | Draws a blue sample circle. |
| 504 | `    s.text(33, ly, 'sequential order (asmread, read_nop96, read_nop256)', 12, 'start', INK2)` | Writes its text: the sequential order, with the names of its three loops. |
| 505 | `    s.mark(420, ly - 4, 'square', C2, r=5, check=False)` | Draws an orange sample square. |
| 506 | `    s.text(431, ly, 'scrambled order (rand_nop0, rand_nop96, rand_nop256)', 12, 'start', INK2)` | Writes its text: the scrambled order, with the names of its three loops. |
| 507 | `    s.text(16, ly + 24, 'Less padding lowers the total in sequential order and raises it in scrambled order.', 12.5, 'start', INK, bold=True)` | Writes the main note in bold: less padding lowers the total in sequential order and raises it in scrambled order. |
| 508 | `    s.text(16, ly + 42, 'Sequential order: the total rises from %.1f to %.1f GB/s when the window gets less deep.'` | Starts the second note line. It says that the sequential total rises when the window gets less deep. The call goes on in line 509. |
| 509 | `           % (FIG4[0][3], FIG4[2][3]), 11.5, 'start', INK2)` | Continues line 508: puts in the sequential totals of the first row (no padding) and of the third row (256 `nop`), with one decimal. |
| 510 | `    s.text(16, ly + 58, 'Scrambled order: the total falls from %.1f to %.1f GB/s.' % (FIG4[0][6], FIG4[2][6]),` | Starts the third note line. It says that the scrambled total falls, and puts in the scrambled totals of the first and of the third row. The call goes on in line 511. |
| 511 | `           11.5, 'start', INK2)` | Continues line 510: font size 11.5 in grey. |
| 512 | `    return s` | Returns the figure object. |

### The style sheet of the page (lines 515 to 556)

| Line | Source | Explanation |
|---:|---|---|
| 515 | `# ---------------------------------------------------------------- HTML` | Comment: the HTML part starts here. |
| 516 | `CSS = """` | Starts the text `CSS`, the style sheet of the page. Each of the lines lines 517 to 553 is one rule. |
| 517 | `:root{color-scheme:light}` | CSS: the page uses the light colour scheme only. |
| 518 | `*{box-sizing:border-box}` | CSS: for every element the width includes its inner margin and its border. |
| 519 | `body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: the body has no outer margin, the background colour of the figures and an almost black text colour. The font is a system font without serifs, 16 pixels, with a line height of 1.55. |
| 520 | `main{max-width:980px;margin:0 auto;padding:28px 16px 64px}` | CSS: the main block is at most 980 pixels wide and centred. Its inner margin is 28 pixels at the top, 16 pixels at the sides and 64 pixels at the bottom. |
| 521 | `h1{font-size:28px;line-height:1.25;margin:0 0 6px}` | CSS: the main title has 28 pixels and a small margin below. |
| 522 | `h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}` | CSS: a section title has 21 pixels, a margin of 40 pixels above and a thin line above it. |
| 523 | `h3{font-size:16px;margin:22px 0 6px}` | CSS: the title of a sub-section has 16 pixels. |
| 524 | `p{margin:8px 0}` | CSS: a paragraph gets 8 pixels above and below. |
| 525 | `ul{margin:6px 0 10px;padding-left:22px}` | CSS: a list gets small margins and an indent of 22 pixels. |
| 526 | `li{margin:4px 0}` | CSS: a list item gets 4 pixels above and below. |
| 527 | `.sub{color:#52514e;font-size:14px;margin:0 0 18px}` | CSS: the class `sub`, the subtitle: grey, 14 pixels. |
| 528 | `.short{background:#f1f0ec;border-left:4px solid #2a78d6;padding:12px 16px;margin:14px 0}` | CSS: the class `short`, the box of the short version: a light grey background and a blue bar of 4 pixels at its left edge. |
| 529 | `.short p{margin:4px 0}` | CSS: a paragraph inside that box gets 4 pixels above and below. |
| 530 | `dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}` | CSS: the word list: a grid with two columns, in 15 pixels. The first column, for the term, is 120 to 210 pixels wide. The second column holds the definition. |
| 531 | `dl.words dt{font-weight:600}` | CSS: a term of the word list is half bold. |
| 532 | `dl.words dd{margin:0}` | CSS: a definition of the word list has no margin. |
| 533 | `@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}` | CSS: on a screen of at most 600 pixels width the word list has one column, and each definition gets 8 pixels below. |
| 534 | `code{font-family:ui-monospace,"DejaVu Sans Mono",Menlo,Consolas,monospace;font-size:0.9em;background:#f1f0ec;padding:0 3px;border-radius:3px}` | CSS: code text: a font with letters of equal width at 0.9 of the text size, a light grey background and round corners. |
| 535 | `.tw{overflow-x:auto;margin:10px 0}` | CSS: the class `tw`, the wrapper of a table. It scrolls sideways when the table is wider than the page. |
| 536 | `table{border-collapse:collapse;font-size:13.5px;line-height:1.35}` | CSS: a table: neighbour cells share one border, the text has 13.5 pixels. |
| 537 | `th,td{border-bottom:1px solid #e4e3df;padding:3px 9px;text-align:left;vertical-align:top}` | CSS: head cells and data cells: a thin line below, an inner margin of 3 by 9 pixels, the text at the left and at the top. |
| 538 | `th{background:#f1f0ec;font-weight:600}` | CSS: head cells get a light grey background and are half bold. |
| 539 | `td:first-child{min-width:150px}` | CSS: the first cell of a row is at least 150 pixels wide. |
| 540 | `td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}` | CSS: the class `n`, the cells with numbers: right-aligned, digits of equal width, no line break. |
| 541 | `caption{caption-side:top;text-align:left;font-weight:600;padding:4px 0;font-size:14px}` | CSS: the caption of a table: above the table, left-aligned, half bold, 14 pixels. |
| 542 | `figure{margin:16px 0}` | CSS: a figure gets 16 pixels above and below. |
| 543 | `.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}` | CSS: the class `fig`, the frame of a figure: sideways scroll when needed, a thin border with round corners, and the background colour. |
| 544 | `.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: the drawing inside the frame is shown as a block. Its texts use the system font without serifs. |
| 545 | `figcaption{font-size:14.5px;margin-top:6px}` | CSS: the caption of a figure: 14.5 pixels, 6 pixels above. |
| 546 | `figcaption b{font-weight:600}` | CSS: bold text in the caption of a figure is half bold. |
| 547 | `.take{font-weight:600}` | CSS: the class `take`, the takeaway sentence of a caption: half bold. |
| 548 | `.ref{color:#52514e;font-size:0.85em;white-space:nowrap}` | CSS: the class `ref`, the citation marks: grey, smaller, no line break. |
| 549 | `.note{color:#52514e;font-size:14px}` | CSS: the class `note`: grey, 14 pixels. |
| 550 | `ol.refs{font-size:14px;padding-left:0;list-style:none}` | CSS: the reference list: 14 pixels, no indent and no numbers. |
| 551 | `ol.refs li{margin:5px 0;overflow-wrap:anywhere}` | CSS: an item of the reference list gets 5 pixels above and below. A long path may break at any place. |
| 552 | `details{margin:8px 0}` | CSS: a fold-out block gets 8 pixels above and below. |
| 553 | `summary{cursor:pointer;font-weight:600}` | CSS: the title line of a fold-out block shows the pointer of a link and is half bold. |
| 554 | `"""` | Ends the text `CSS`. |

### The helpers `r`, `table` and `rng` (lines 557 to 576)

| Line | Source | Explanation |
|---:|---|---|
| 557 | `def r(*n):` | Starts the function `r`. It gets one or more reference numbers and returns their citation marks for the page. |
| 558 | `    return ' <span class="ref">' + ''.join('[Ref%d]' % i for i in n) + '</span>'` | Returns a `span` element of the class `ref`, with a space in front. Inside it each number is written as `Ref` and the number in square brackets. |
| 561 | `def table(caption, head, rows, num_from=1):` | Starts the function `table`. It builds one HTML table from a caption, the column titles and the rows. `num_from` is the position of the first column with numbers, counted from 0. Its default is 1. |
| 562 | `    h = ['<div class="tw"><table><caption>%s</caption><thead><tr>' % caption]` | `h`: the list of the pieces of the table. It starts with the wrapper of the class `tw`, the table, the caption and the opening of the head row. |
| 563 | `    for i, c in enumerate(head):` | Starts a loop over the column titles. |
| 564 | `        h.append('<th%s>%s</th>' % (' class="n"' if i >= num_from else '', c))` | Adds one head cell. From the column `num_from` on it gets the class `n`, which aligns it to the right. |
| 565 | `    h.append('</tr></thead><tbody>')` | Closes the head and opens the body of the table. |
| 566 | `    for row in rows:` | Starts a loop over the rows. |
| 567 | `        h.append('<tr>' + ''.join('<td%s>%s</td>' % (' class="n"' if i >= num_from else '', c)` | Adds one table row with one cell per value. The call goes on in line 568. |
| 568 | `                                  for i, c in enumerate(row)) + '</tr>')` | Continues line 567: the loop over the values of the row. From the column `num_from` on a cell gets the class `n`. |
| 569 | `    h.append('</tbody></table></div>')` | Closes the body, the table and the wrapper. |
| 570 | `    return ''.join(h)` | Returns all pieces as one text. |
| 573 | `def rng(a, b):` | Starts the function `rng`. It writes a range. |
| 574 | `    return '%.1f–%.1f' % (a, b)` | Returns the two values with one decimal each and an en dash between them. |

### `build`: head of the page, title and short version (lines 577 to 599)

| Line | Source | Explanation |
|---:|---|---|
| 577 | `def build():` | Starts the function `build`. It returns the whole page as one text, and the list of the label overlaps. |
| 578 | `    g1, g2, g3, g4 = fig1(), fig2(), fig3(), fig4()` | Draws the four figures first. `g1` to `g4` are the figure objects. |
| 579 | `    P = []` | `P`: the list of the pieces of the page, empty at first. |
| 580 | `    w = P.append` | `w`: a short name for `P.append`. Each call of `w` adds one piece to the page. |
| 581 | `    w('<!DOCTYPE html>\n<html lang="en" data-theme="light">\n<head>\n<meta charset="utf-8">\n'` | Starts the head of the HTML page: the document type, the language `en`, a mark for the light theme, and the character set UTF-8. The call goes on in lines 582 to 584. |
| 582 | `      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'` | Continues line 581: the setting that gives the page the width of the screen on a phone. |
| 583 | `      '<meta name="color-scheme" content="light">\n'` | Continues line 581: the page declares the light colour scheme only. |
| 584 | `      '<title>Whole-chip read drop</title>\n<style>%s</style>\n</head>\n<body>\n<main>\n' % CSS)` | Continues line 581: the title for the browser tab, the style sheet `CSS`, the end of the head, and the opening of the body and of the main block. |
| 585 | `    w('<h1>Why the whole-chip read rate fell with the new test kernel</h1>')` | Writes the main title of the page. |
| 586 | `    w('<p class="sub">CRB, 120 threads, DRAM-sized buffers. Measured on 2026-11-15, 16:56 to 21:03 UTC. '` | Starts the subtitle: the machine, the 120 threads, the size class of the buffers, and the date and the time span of the measurements as fixed text. The call goes on in line 587. |
| 587 | `      'A generator script builds this page' + r(19) + '. Its numbers come from the facts sheet' + r(1) + '.</p>')` | Continues line 586: a sentence that a generator script builds the page, with the citation mark of reference 19. Then a sentence that the numbers come from the facts sheet, with the citation mark of reference 1. |
| 589 | `    # ------------------------------------------------ short version` | Comment: the short version. |
| 590 | `    w('<h2 id="short">Short version</h2><div class="short">')` | Writes the section title of the short version and opens its box. The numbers of the three paragraphs that follow stand in the section "What is established" of the facts sheet [Ref1]. |
| 591 | `    w('<p>With 120 threads only read really dropped (about 300 GB/s against about 468 GB/s, -36 %): copy did not '` | Starts paragraph 1 of the short version: with 120 threads only read dropped. It gives the two rounded totals and the drop in percent as fixed text. The call goes on in line 592. |
| 592 | `      'drop, and most of the write drop comes from the stop rule of the benchmark.</p>')` | Continues line 591: copy did not drop, and most of the write drop comes from the stop rule of the benchmark. |
| 593 | `    w('<p>The new read loop holds loads only, and the out-of-order window of a core (the instructions that it can '` | Starts paragraph 2: the new read loop holds loads only. The text explains the out-of-order window of a core in a few words. The call goes on in lines 594 to 595. |
| 594 | `      'start ahead) then covers 36 to 40 cache lines (64 B each) instead of 18 to 22 (one-thread test), and the '` | Continues line 593: the window depth of the new loop and of the old loop in cache lines, as fixed text, from a test with one thread. |
| 595 | `      '120-thread total falls when the window covers more than about 30 lines.</p>')` | Continues line 593: the 120-thread total falls when the window covers more than about 30 cache lines. |
| 596 | `    w('<p>Adding 72 or more do-nothing instructions per 256 B of data read restores 459 to 480 GB/s, and the drop '` | Starts paragraph 3: the remedy. Instructions that do nothing, 72 or more per 256 B, bring the total back. The numbers are fixed text. The call goes on in lines 597 to 598. |
| 597 | `      'did not appear when the same loads read the memory in one scrambled order instead of address order, and '` | Continues line 596: the drop did not appear when the same loads read the memory in one scrambled order. |
| 598 | `      'the exact rule inside the core is not established.</p></div>')` | Continues line 596: the exact rule inside the core is not established. The piece also closes the box of the short version. |

### `build`: the word list of the page (lines 600 to 671)

| Line | Source | Explanation |
|---:|---|---|
| 600 | `    # ------------------------------------------------ words` | Comment: the word list. |
| 601 | `    w('<h2 id="words">Words used here</h2><dl class="words">')` | Writes the section title of the word list and opens the list. |
| 602 | `    words = [` | `words`: starts the list of pairs. Each pair is a term and its definition. |
| 603 | `        ('CRB', 'The Arm server under test. It has 128 cores of type Neoverse V3AE. The tests use CPUs 0 to 119. The core clock is 2.8 GHz.'),` | Word list of the page: the entry for CRB. The numbers in it (cores, CPUs of the tests, core clock) are fixed text. |
| 604 | `        ('kernel', 'One timed loop of the benchmark. It is not the Linux kernel. This page mostly says "loop".'),` | Word list: the entry for the word kernel. It says that the page mostly writes "loop". |
| 605 | `        ('old read (<code>oldread</code>)', 'The read loop of the old benchmark, written in C. '` | Word list: the entry for the old read loop, `oldread`. The definition goes on in line 606. |
| 606 | `         'Per 128 B it holds 4 load-pair instructions and 8 vector adds.'),` | Continues the entry of line 605: what the old loop holds per 128 B. |
| 607 | `        ('new read, asm read (<code>asmread</code>)', 'The read loops of the new benchmark. One is written in C '` | Word list: the entry for the two new read loops, with the name `asmread`. The definition goes on in lines 608 to 609. |
| 608 | `         'and one in assembly. Both hold 8 load-pair instructions per 256 B and nothing else. '` | Continues the entry of line 607: what both loops hold per 256 B. |
| 609 | `         'This page calls them the load-only loop.'),` | Continues the entry of line 607: the page calls them the load-only loop. |
| 610 | `        ('nop', 'An instruction that does nothing. It still uses one place in the window.'),` | Word list: the entry for `nop`, an instruction that does nothing but takes one place in the window. |
| 611 | `        ('padded loop', 'The load-only loop with nop instructions added. <code>read_nop96</code> has 96 nop per '` | Word list: the entry for a padded loop, with `read_nop96` as the first example. The definition goes on in line 612. |
| 612 | `         '256 B. <code>read_nop256</code> has 256 nop per 256 B.'),` | Continues the entry of line 611: the second example, `read_nop256`. |
| 613 | `        ('ldp, ldr, prfm', 'Arm instructions: load a pair of registers, load one register, prefetch.'),` | Word list: the entry for the three Arm instructions that the page names: load a pair, load one register, prefetch. |
| 614 | `        ('<code>read_1pl</code>', 'A loop with 4 single loads (ldr) per 256 B, one load per 64 B line, and nothing '` | Word list: the entry for the loop `read_1pl`. The definition goes on in line 615. |
| 615 | `         'else. <code>read_1pl_nop96</code> is the same loop plus 96 nop.'),` | Continues the entry of line 614: the loop `read_1pl_nop96`. |
| 616 | `        ('<code>read_daddN</code>, <code>read_iadd16</code>', 'The load-only loop plus N vector adds per 256 B. '` | Word list: the entry for the loops with vector adds, `read_daddN` and `read_iadd16`. The definition goes on in lines 617 to 618. |
| 617 | `         'In <code>read_dadd16</code> the adds use the loaded data. '` | Continues the entry of line 616: in `read_dadd16` the adds use the loaded data. |
| 618 | `         'In <code>read_iadd16</code> the 16 adds do not use the loaded data.'),` | Continues the entry of line 616: in `read_iadd16` the adds do not use the loaded data. |
| 619 | `        ('<code>read_spN</code>, <code>read_sparse</code>', 'Loops with 4 load-pair instructions and N nop per 128 B. '` | Word list: the entry for the loops `read_spN` and `read_sparse`, which have 4 load-pair instructions per 128 B. The definition goes on in line 620. |
| 620 | `         '<code>read_sparse</code> has 9 nop.'),` | Continues the entry of line 619: the number of `nop` in `read_sparse`. |
| 621 | `        ('<code>read_pfN</code>', 'The load-only loop plus software prefetch instructions (prfm) that ask for the '` | Word list: the entry for the loops `read_pfN`, the load-only loop with prefetch instructions. The definition goes on in line 622. |
| 622 | `         'data N bytes ahead.'),` | Continues the entry of line 621: N is the distance of the prefetch in bytes. |
| 623 | `        ('sequential order, sequential stream', 'The loop reads its buffer from the lowest address to the highest. '` | Word list: the entry for the sequential order. The definition goes on in line 624. |
| 624 | `         'All loops of sections 1 to 5 do this.'),` | Continues the entry of line 623: all loops of the sections 1 to 5 of the page read in this order. |
| 625 | `        ('scrambled order', 'The loop reads the same bytes, but it does not follow the addresses. '` | Word list: the entry for the scrambled order. The definition goes on in lines 626 to 627. |
| 626 | `         'Each buffer is cut into chunks of 2 MiB. One chunk has 8192 blocks of 256 B. '` | Continues the entry of line 625: the buffer is cut into chunks of 2 MiB, and a chunk has 8192 blocks of 256 B. |
| 627 | `         'The loop visits every block of a chunk once, in an order that jumps between the blocks.'),` | Continues the entry of line 625: the loop visits every block of a chunk once. |
| 628 | `        ('<code>rand_nop0</code>, <code>rand_nop96</code>, <code>rand_nop256</code>', 'The scrambled-order loops. '` | Word list: the entry for the three scrambled-order loops. The definition goes on in lines 629 to 630. |
| 629 | `         'They hold 8 load-pair instructions per 256 B and 0, 96 or 256 nop. These are the loads and the padding of '` | Continues the entry of line 628: their loads per 256 B and their numbers of `nop`. |
| 630 | `         '<code>asmread</code>, <code>read_nop96</code> and <code>read_nop256</code>.'),` | Continues the entry of line 628: the three sequential loops with the same loads and padding. |
| 631 | `        ('request limit', 'The largest number of memory requests that a core keeps outstanding at one time.'),` | Word list: the entry for the request limit of a core. |
| 632 | `        ('DRAM', 'The main memory of the machine. It lies outside the caches of the chip.'),` | Word list: the entry for DRAM, the main memory. |
| 633 | `        ('prefetcher', 'The part of a core that requests data before the loop asks for it. '` | Word list: the entry for the prefetcher. The definition goes on in lines 634 to 635. |
| 634 | `         'The hardware prefetcher does this without any instruction. '` | Continues the entry of line 633: the hardware prefetcher. |
| 635 | `         'A software prefetch is an instruction in the loop.'),` | Continues the entry of line 633: a software prefetch. |
| 636 | `        ('streaming core', 'A core that runs a read loop over its buffer.'),` | Word list: the entry for a streaming core. |
| 637 | `        ('latency probe, pointer chase', 'A test loop on one core. Each load gives the address of the next load, '` | Word list: the entry for the latency probe, a pointer chase. The definition goes on in line 638. |
| 638 | `         'and each load misses the cache. The time of one step is about the time of one DRAM read.'),` | Continues the entry of line 637: what the time of one step stands for. |
| 639 | `        ('huge page', 'A memory page of 2 MiB. The normal page is 4 KiB.'),` | Word list: the entry for a huge page, with the two page sizes. |
| 640 | `        ('line', 'One cache line. It is 64 B.'),` | Word list: the entry for a cache line of 64 B. |
| 641 | `        ('window (out-of-order window)', 'The instructions that a core holds between fetch and retirement. '` | Word list: the entry for the out-of-order window. The definition goes on in line 642. |
| 642 | `         'The core can start the loads of all instructions in the window before the first one finishes.'),` | Continues the entry of line 641: the core can start the loads of all instructions in the window. |
| 643 | `        ('window depth in lines', 'The number of 64 B lines that the loads inside one full window touch. '` | Word list: the entry for the window depth in cache lines. The definition goes on in line 644. |
| 644 | `         'It was measured for each loop with one thread on CPU 2. The result is a range, for example 36 to 40 lines.'),` | Continues the entry of line 643: how it was measured, and that the result is a range. |
| 645 | `        ('lines in flight', 'The lines that one core has requested from memory and has not yet received.'),` | Word list: the entry for the lines in flight. |
| 646 | `        ('mesh 0, mesh 1', 'The chip has two meshes (grids of links that connect cores, cache and memory ports). '` | Word list: the entry for mesh 0 and mesh 1. The definition goes on in line 647. |
| 647 | `         'CPUs 0 to 63 are on mesh 0. CPUs 64 to 119 are on mesh 1.'),` | Continues the entry of line 646: the CPUs of each mesh that the tests use. |
| 648 | `        ('64+56', '64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119. Each thread has its own 256 MiB '` | Word list: the entry for the layout 64+56. The definition goes on in line 649. |
| 649 | `         'buffer. The data comes from DRAM. Other layouts use the same form, for example 64+0.'),` | Continues the entry of line 648: the buffer size per thread, and the form of other layout names. |
| 650 | `        ('gateway', 'The link that carries requests and data from one mesh to the other mesh.'),` | Word list: the entry for the gateway between the two meshes. |
| 651 | `        ('memory port', 'A port of the mesh that leads to a DRAM controller. The counters cover 24 ports.'),` | Word list: the entry for a memory port, with the number of ports that the counters cover. |
| 652 | `        ('home node', 'A node of the mesh that receives the memory requests of the cores and passes them on.'),` | Word list: the entry for a home node. |
| 653 | `        ('busy level', 'A value from 0 to 3 that a response message carries. A higher value says that the sender '` | Word list: the entry for the busy level. The definition goes on in line 654. |
| 654 | `         'is more busy.'),` | Continues the entry of line 653. |
| 655 | `        ('flit', 'One unit of transfer on a mesh link. Two data flits carry one line.'),` | Word list: the entry for a flit. Two data flits carry one cache line. |
| 656 | `        ('whole-pass stop', 'The stop rule of <code>bandwidth.c</code> (the benchmark). A thread stops only at the '` | Word list: the entry for the whole-pass stop of `bandwidth.c`. The definition goes on in line 657. |
| 657 | `         'end of a whole pass over its buffer. The threads stop at different times.'),` | Continues the entry of line 656: the threads stop at different times. |
| 658 | `        ('common stop', 'All threads stop at the same time.'),` | Word list: the entry for the common stop. |
| 659 | `        ('slow, between, fast, fastest', 'Names for the 120-thread read total. Slow is 280 to 310 GB/s '` | Word list: the entry for the four state names, with the range of the total of each state as fixed text. The definition goes on in lines 660 to 661. |
| 660 | `         '(230 to 235 GB/s for <code>read_1pl</code>). Between is 325 to 367 GB/s. Fast is 459 to 480 GB/s. '` | Continues the entry of line 659. The range for the state between, 325 to 367 GB/s, is not in the facts sheet in this form. It spans the two rows of `F2` with that state (lines 48 to 49). |
| 661 | `         'Fastest is 544 to 549 GB/s (<code>read_nop256</code>).'),` | Continues the entry of line 659: the range of the state fastest. |
| 662 | `        ('squeezed', 'A mesh is squeezed when its threads read less because the other mesh runs a different loop.'),` | Word list: the entry for a squeezed mesh. |
| 663 | `        ('total', 'The sum of the rates of all threads.'),` | Word list: the entry for the total. |
| 664 | `        ('n', 'The number of timed intervals behind a value.'),` | Word list: the entry for `n`, the number of intervals behind a value. |
| 665 | `        ('GB', '1e9 bytes. MiB and KiB are powers of 2.'),` | Word list: the entry for the units GB, MiB and KiB. |
| 666 | `        ('est.', 'Estimate. The value is computed with an assumption. It is not measured directly.'),` | Word list: the entry for the mark of an estimate. |
| 667 | `    ]` | Ends the list `words`. |
| 668 | `    for t, d in words:` | Starts a loop over the pairs. |
| 669 | `        w('<dt>%s</dt><dd>%s</dd>' % (t, d))` | Writes the term and the definition of one pair as an entry of the list. |
| 670 | `    w('</dl>')` | Closes the list. |

### `build`: section 1 of the page, only read really dropped (lines 672 to 715)

| Line | Source | Explanation |
|---:|---|---|
| 672 | `    # ------------------------------------------------ (a)` | Comment: the block for section 1 of the page. The comment calls it (a). |
| 673 | `    w('<h2 id="a">1. Only read really dropped</h2>')` | Writes the title of section 1. The numbers of this section are fixed text. They stand in the sections "The question" and F1 of the facts sheet [Ref1]. |
| 674 | `    w('<ul>')` | Opens the first list of the section. |
| 675 | `    w('<li>The original run used the whole-pass stop and 0.5 s per interval' + r(2) + '. '` | List item 1: the stop rule and the interval length of the original run, with the citation mark of reference 2. The item goes on in line 676. |
| 676 | `      'Read fell there by more than one third. Write fell by a smaller amount. Copy did not fall.</li>')` | Continues line 675: how read, write and copy changed in that run, in words. |
| 677 | `    w('<li>Copy was measured again at 64+56 with a common stop and 6 s. All five copy loops gave 152.4 to '` | List item 2: copy was measured again at 64+56 with a common stop. The range of the five copy loops is fixed text. It spans the five ranges of the facts sheet. The item goes on in line 678. |
| 678 | `      '153.6 GB/s' + r(3) + '.</li>')` | Continues line 677: the upper end of the range and the citation mark of reference 3. |
| 679 | `    w('<li>Write was measured again at 64+56 with a common stop and 8 s. The old loop gave 126.1 to 126.8 GB/s. '` | List item 3: write was measured again at 64+56 with a common stop. It gives the range of the old loop. The item goes on in line 680. |
| 680 | `      'The new loops gave 120.2 to 129.3 GB/s' + r(3) + '. Padding does not change write.</li>')` | Continues line 679: the range of the new loops, with the citation mark of reference 3. That range spans the three ranges of the new and the padded write loops in the facts sheet. A last sentence says that padding does not change write. |
| 681 | `    w('<li>The write drop depends on the stop rule. Earlier controlled runs compared old write and new C write under '` | List item 4: the write drop depends on the stop rule. Earlier runs compared the old and the new write loop. The item goes on in lines 682 to 683. |
| 682 | `      'four timing rules' + r(4) + '. The old loop is 21.5 % higher with the whole-pass stop and 0.5 s. '` | Continues line 681: four timing rules, with the citation mark of reference 4, and the gain of the old loop with the whole-pass stop and 0.5 s. |
| 683 | `      'It is 3.1 % to 3.7 % higher with a common stop.</li>')` | Continues line 681: the gain of the old loop with a common stop. |
| 684 | `    w('<li>So most of the write drop in the original run comes from the whole-pass stop rule. '` | List item 5: the reading. Most of the write drop of the original run comes from the whole-pass stop rule. The item goes on in line 685. |
| 685 | `      '3 to 4 % remains with a common stop.</li>')` | Continues line 684: the part of the drop that stays with a common stop. |
| 686 | `    w('<li>The original file supports this. At equal pass count (296 passes) old write is 144.2 to 145.6 GB/s. '` | List item 6: the original file supports this. At an equal number of passes the old write range is given. The item goes on in line 687. |
| 687 | `      'New write is 143.6 GB/s and 147.8 GB/s' + r(2) + '.</li>')` | Continues line 686: the two values of the new write loop, with the citation mark of reference 2. |
| 688 | `    w('<li>Read is different. The drop stays with a common stop: 288.5 to 309.8 GB/s against 465.5 to 470.1 GB/s '` | List item 7: read is different. The drop stays with a common stop. The two ranges are those of `asmread` and `oldread` in `F2`, as fixed text. The item goes on in line 689. |
| 689 | `      '(section 2)' + r(6) + '.</li>')` | Continues line 688: a pointer to section 2 and the citation mark of reference 6. |
| 690 | `    w('</ul>')` | Closes the list. |
| 691 | `    w(table('Original run: total in GB/s, 120 threads, whole-pass stop, 0.5 s (n = 6 per loop)' + r(2),` | Starts the first table of the section: the original run with 120 threads, the whole-pass stop and 0.5 s. This line is the caption, with the citation mark of reference 2. The call goes on in lines 692 to 696. |
| 692 | `            ['test', 'old C loop', 'new C loop', 'asm loop', 'result'],` | Continues line 691: the five column titles. |
| 693 | `            [['read', '464.4–466.7', '279.7–304.1', '271.1–305.9', 'drop'],` | Continues line 691: the row for read, with the ranges of the old C loop, the new C loop and the assembly loop. |
| 694 | `             ['write', '140.9–186.9 (median 144.6)', '123.5–147.8 (median 131.9)', 'not in the facts sheet',` | Continues line 691: the row for write. The cell of the assembly loop says that the facts sheet has no value. The row goes on in line 695. |
| 695 | `              'smaller drop'],` | Continues line 694: the last cell of the write row. |
| 696 | `             ['copy (read + written bytes)', '155.0–158.6', '153.9–162.4', 'not in the facts sheet', 'no drop']]))` | Continues line 691: the row for copy. The closing brackets end the table. |
| 697 | `    w(table('Controlled runs at 64+56 with a common stop: total in GB/s (n = 2 intervals per loop)' + r(3),` | Starts the second table: the runs at 64+56 with a common stop. This line is the caption, with the citation mark of reference 3. The call goes on in lines 698 to 702. |
| 698 | `            ['test', 'interval', 'old loop', 'asm loop', 'new C loop', 'padded loops'],` | Continues line 697: the six column titles. |
| 699 | `            [['copy', '6 s', '152.7–153.0', '152.4–152.6', '152.7–153.4',` | Continues line 697: the row for copy with an interval of 6 s. The row goes on in line 700. |
| 700 | `              'copy_nop96 153.2–153.6, copy_nop192 153.3–153.4'],` | Continues line 699: the cell with the two padded copy loops. |
| 701 | `             ['write', '8 s', '126.1–126.8', '121.3–121.8', '121.4–129.3',` | Continues line 697: the row for write with an interval of 8 s. The row goes on in line 702. |
| 702 | `              'write_nop32, 96, 128, 256: 120.2–122.9']]))` | Continues line 701: the cell with the padded write loops. The closing brackets end the table. |
| 703 | `    w(table('Old write against new C write under four timing rules: median total in GB/s '` | Starts the third table: the old write loop against the new C write loop under four timing rules. The caption goes on in line 704. |
| 704 | `            '(64 processes, 64 intervals per cell)' + r(4),` | Continues line 703: the sample size of each cell and the citation mark of reference 4. |
| 705 | `            ['stop rule', 'interval', 'old write', 'new C write', 'old above new'],` | Continues line 703: the five column titles. |
| 706 | `            [['whole-pass stop', '0.5 s', '144.1', '118.6', '+21.5 %'],` | Continues line 703: the row for the whole-pass stop with 0.5 s. |
| 707 | `             ['whole-pass stop', '15 s', '131.3', '117.4', '+11.9 %'],` | Continues line 703: the row for the whole-pass stop with 15 s. |
| 708 | `             ['common stop', '0.5 s', '126.4', '122.0', '+3.7 %'],` | Continues line 703: the row for the common stop with 0.5 s. |
| 709 | `             ['common stop', '15 s', '126.6', '122.8', '+3.1 %']]))` | Continues line 703: the row for the common stop with 15 s. The closing brackets end the table. |
| 710 | `    w('<ul><li>Writers on one mesh only (64+0) reach 455 GB/s with <code>oldwrite</code>, <code>asmwrite</code>, '` | Starts a second list. Item 1: writers on one mesh only, with their rate. The piece goes on in lines 711 to 714. |
| 711 | `      '<code>write_nop128</code> and <code>write_nop256</code>' + r(3) + '.</li>'` | Continues line 710: the names of two more write loops and the citation mark of reference 3. |
| 712 | `      '<li>Writers at 32+32 reach 204 to 209 GB/s' + r(3) + '.</li>'` | Continues line 710: item 2, the rate of writers at 32+32, with the citation mark of reference 3. |
| 713 | `      '<li>So the write total falls from 455 GB/s (64+0) to 120 to 129 GB/s (64+56) when writers run on both '` | Continues line 710: item 3, the fall of the write total from one mesh to both meshes. The range at 64+56 is a rounded form of the range in line 680. |
| 714 | `      'meshes. The fall is the same for old and new loops. It is not explained here.</li></ul>')` | Continues line 710: the fall is the same for the old and the new loops, and the page does not explain it. The piece closes the list. |

### `build`: section 2 of the page, the read rate follows the window depth (lines 716 to 775)

| Line | Source | Explanation |
|---:|---|---|
| 716 | `    # ------------------------------------------------ (b)` | Comment: the block for section 2 of the page. |
| 717 | `    w('<h2 id="b">2. The read rate follows the window depth</h2>')` | Writes the title of section 2. The numbers of this section are fixed text or come from the table `F2`. They stand in section F2 of the facts sheet [Ref1]. |
| 718 | `    w('<ul>')` | Opens the first list of the section. |
| 719 | `    w('<li>A window test with one thread on CPU 2 measured how much one core holds in its window' + r(5) + '. '` | List item 1: the window test with one thread on CPU 2, with the citation mark of reference 5. The item goes on in line 720. |
| 720 | `      'The window holds 684 nop, or 159 vector-register writes, or 191 integer adds.</li>')` | Continues line 719: the three capacities of the window as fixed text: `nop` instructions, writes to vector registers, and integer adds. |
| 721 | `    w('<li>The same test measured the window depth of each loop in lines. One loop body was the unit. '` | List item 2: the same test measured the window depth of each loop in cache lines. The item goes on in line 722. |
| 722 | `      'The result is a range: the last count that fits, to the first count that does not fit' + r(5) + '.</li>')` | Continues line 721: why the result is a range, with the citation mark of reference 5. |
| 723 | `    w('<li>29 loop variants were then run at 64+56. Figure 1 shows the total of each variant against its window '` | List item 3: the number of loop variants that ran at 64+56, and what Figure 1 shows. The number 29 is fixed text. It equals the number of rows of `F2`. The item goes on in line 724. |
| 724 | `      'depth' + r(6) + '.</li>')` | Continues line 723: the citation mark of reference 6. |
| 725 | `    w('<li>Every variant with a window of 32 lines or more is slow: 280 to 310 GB/s. '` | List item 4: every variant with a window of 32 cache lines or more is slow, with the range of the total. The item goes on in line 726. |
| 726 | `      '<code>read_1pl</code> covers about 160 lines and gives 230 to 235 GB/s.</li>')` | Continues line 725: the case of `read_1pl`. |
| 727 | `    w('<li>Every variant whose measured range is at or below 24 to 28 lines is fast: 459 to 480 GB/s. '` | List item 5: every variant whose measured range is at or below 24 to 28 cache lines is fast, with the range of the total. The item goes on in line 728. |
| 728 | `      '<code>read_nop256</code> covers 8 to 12 lines and gives 543.9 to 549.0 GB/s.</li>')` | Continues line 727: the case of `read_nop256`. |
| 729 | `    w('<li>The four variants whose measured range lies inside 26 to 32 lines are slow or between '` | List item 6: the four variants whose range lies inside 26 to 32 cache lines are slow or between. The item goes on in line 730. |
| 730 | `      '(<code>read_nop56</code>, <code>read_dadd4</code>, <code>read_nop64</code>, <code>read_sp32</code>).</li>')` | Continues line 729: the names of the four variants. |
| 731 | `    w('</ul>')` | Closes the list. |
| 732 | `    w('<figure><div class="fig">' + g1.done() + '</div><figcaption><b>Figure 1.</b> Total read rate at 64+56 '` | Opens the figure block and puts in the SVG text of Figure 1 (`g1.done()`). Then the caption starts. The piece goes on in lines 733 to 738. |
| 733 | `      'against the measured window depth, one mark per loop variant (29 marks). The window depth comes from a '` | Continues line 732: one mark per loop variant, and the source of the window depth. |
| 734 | `      'test with one thread on CPU 2. %d marks would cover other marks. They are moved sideways by at most %.1f px '` | Continues line 732: the sentence about the shifted marks. It has three places for numbers: how many marks were shifted, and the largest shift in pixels. |
| 735 | `      '(%.2f lines). The thin horizontal bar and the table below give the exact range. '` | Continues line 732: the third number, the largest shift in cache lines. The text adds that the thin bar and the table give the exact range. |
| 736 | `      'Hover over a mark for its values. ' % (g1.moved, g1.maxdx, g1.maxdx / g1.px_per_line) +` | Continues line 732: the three values for these places: `g1.moved`, `g1.maxdx` and `g1.maxdx` divided by the 14 pixels per cache line. `fig1` computed them (lines 268 to 283). |
| 737 | `      '<span class="take">Takeaway: variants below the switch band give 459 GB/s or more, and variants above it give '` | Continues line 732: the takeaway sentence starts, in the class `take`. Variants below the switch band are fast. |
| 738 | `      '310 GB/s or less, for every kind of loop.</span></figcaption></figure>')` | Continues line 732: the end of the takeaway sentence. Variants above the band are slow, for every kind of loop. The piece closes the caption and the figure block. |
| 739 | `    w('<ul>')` | Opens the second list of the section. |
| 740 | `    w('<li>The old read loop is fast because its 8 vector adds per 128 B occupy vector registers. '` | List item: why the old read loop is fast. Its vector adds occupy vector registers. The item goes on in line 741. |
| 741 | `      'The window holds 159 vector-register writes' + r(1, 5) + '.</li>')` | Continues line 740: the capacity of the window in writes to vector registers, with the citation marks of the references 1 and 5. |
| 742 | `    w('<li>The adds do not need to wait for data. <code>read_iadd16</code> has adds that do not use the loaded data. '` | List item: the adds do not need to wait for data. It compares `read_iadd16` with `read_dadd16`. The item goes on in lines 743 to 744. |
| 743 | `      '<code>read_dadd16</code> has adds that use it. The two totals overlap (469.2 to 469.7 GB/s and 466.7 to '` | Continues line 742: the two ranges of the total overlap. The numbers are those of the two rows in `F2`, as fixed text. |
| 744 | `      '469.8 GB/s)' + r(6) + '.</li>')` | Continues line 742: the end of the second range and the citation mark of reference 6. |
| 745 | `    w('<li>Software prefetch does not restore the rate. <code>read_pf256</code> gives 289.1 to 300.1 GB/s (n = 4). '` | List item: software prefetch does not bring the rate back. It gives the range of `read_pf256`. The item goes on in lines 746 to 747. |
| 746 | `      '<code>read_pf512</code> gives 302.3 to 303.9 GB/s (n = 2). <code>read_pf1024</code> gives 311.8 to '` | Continues line 745: the ranges of `read_pf512` and `read_pf1024`. These three variants are not in `F2`. |
| 747 | `      '315.8 GB/s (n = 2)' + r(6) + '.</li>')` | Continues line 745: the end of the last range and the citation mark of reference 6. |
| 748 | `    w('<li>The page size does not matter. With 4 KiB pages instead of 2 MiB pages (huge pages) the results are the same. '` | List item: the page size does not matter. It compares pages of 4 KiB with pages of 2 MiB. The item goes on in line 749. |
| 749 | `      'The differences to the process with huge pages are -2.4 % to +0.2 % (one process per page size)' + r(7) + '.</li>')` | Continues line 748: the range of the differences in percent, with the citation mark of reference 7. |
| 750 | `    w('</ul>')` | Closes the list. |
| 751 | `    w(table('Per-thread read rate in GB/s' + r(6),` | Starts a table of the read rate of one thread in GB/s, with the citation mark of reference 6. The call goes on in lines 752 to 755. |
| 752 | `            ['state', 'mesh 0 threads', 'mesh 1 threads'],` | Continues line 751: the three column titles: the state, the threads of mesh 0 and the threads of mesh 1. |
| 753 | `            [['slow', '2.5–2.75', '2.25–2.45'],` | Continues line 751: the row for the slow state. |
| 754 | `             ['fast (the 459–480 GB/s group)', '4.27–5.45', '2.51–2.78'],` | Continues line 751: the row for the fast state. |
| 755 | `             ['read_nop256', '4.99–5.22', '3.84–3.97']]))` | Continues line 751: the row for `read_nop256`. The closing brackets end the table. |
| 756 | `    w('<details><summary>Exact numbers of Figure 1 (29 variants)</summary>')` | Opens a fold-out block with the exact numbers of Figure 1. |
| 757 | `    rows = []` | `rows`: the list of the table rows, empty at first. |
| 758 | `    for name, holds, lo, hi, rmin, rmax, n, state, cls in F2:` | Starts a loop over the rows of `F2`. |
| 759 | `        rows.append(['<code>%s</code>' % name.split(' ')[0] + (' ' + name.split(' ', 1)[1] if ' ' in name else ''),` | Adds one table row. Its first cell is the first word of the name as code text, then the rest of the name. The call goes on in line 760. |
| 760 | `                     holds if holds else '–', CLS[cls][2], '%d–%d' % (lo, hi), rng(rmin, rmax), str(n), state])` | Continues line 759: what the loop holds, or a dash for an empty text. Then the legend text of the class, the window range, the range of the total written by `rng`, the number of intervals and the state. |
| 761 | `    w(table('Total at 64+56 in GB/s (min–max over all intervals) and window depth in lines (one-thread test). '` | Starts the table of the fold-out block. The caption says what the two value columns are. The call goes on in lines 762 to 766. |
| 762 | `            '12 processes. 169 intervals in this table, 177 with the three variants <code>read_pf256</code>, '` | Continues line 761: the number of processes and two interval counts as fixed text. 169 is the sum of the field `n` over the rows of `F2`. 177 is the total that the facts sheet gives [Ref1]. |
| 763 | `            '<code>read_pf512</code> and <code>read_pf1024</code>. The ranges and n include the process with '` | Continues line 761: the three variants that make the difference of 8 intervals. |
| 764 | `            '4 KiB pages (2 intervals for each of its 7 loops)' + r(5, 6, 7),` | Continues line 761: a remark on the process with pages of 4 KiB, and the citation marks of the references 5, 6 and 7. |
| 765 | `            ['loop', 'what the loop holds per iteration', 'colour class in Figure 1', 'window depth, lines',` | Continues line 761: the first four column titles. |
| 766 | `             'total, GB/s', 'n', 'state'], rows, num_from=3))` | Continues line 761: the last three column titles and the rows. `num_from=3` right-aligns the columns from the window depth on. |
| 767 | `    w('<p class="note">A dash means that the facts sheet does not list the content of that loop. '` | Starts a note paragraph: a dash means that the facts sheet does not list the content of the loop. The piece goes on in line 768. |
| 768 | `      'The colour class is assigned in this report from the content of the loop.</p>')` | Continues line 767: the colour class is assigned in this report, not in the facts sheet. |
| 769 | `    w(table('4 KiB pages: total at 64+56 in GB/s' + r(7),` | Starts a table of the totals with pages of 4 KiB, with the citation mark of reference 7. The call goes on in lines 770 to 773. |
| 770 | `            ['loop', 'total, GB/s'],` | Continues line 769: the two column titles. |
| 771 | `            [['oldread', '466.0–468.5'], ['asmread', '298.0–300.3'], ['read_nop64', '325.9–326.1'],` | Continues line 769: the rows of three loops. |
| 772 | `             ['read_nop96', '467.7–467.8'], ['read_nop256', '543.9–545.0'], ['read_1pl', '234.8–235.0'],` | Continues line 769: the rows of three more loops. |
| 773 | `             ['read_pf2048', '297.6–302.5']]))` | Continues line 769: the row of `read_pf2048`. The closing brackets end the table. |
| 774 | `    w('</details>')` | Closes the fold-out block. |

### `build`: section 3 of the page, other thread layouts (lines 776 to 796)

| Line | Source | Explanation |
|---:|---|---|
| 776 | `    # ------------------------------------------------ (c)` | Comment: the block for section 3 of the page. |
| 777 | `    w('<h2 id="c">3. The padded loop follows the old loop in every thread layout</h2>')` | Writes the title of section 3. The numbers of this section are fixed text. They stand in section F2 of the facts sheet, under "Other layouts" [Ref1]. |
| 778 | `    w('<ul>')` | Opens the list of the section. |
| 779 | `    w('<li>Four loops were run in seven more thread layouts' + r(8) + '.</li>')` | List item 1: four loops were run in seven more thread layouts, with the citation mark of reference 8. |
| 780 | `    w('<li>The padded loops follow the old read loop in every layout, within 2.3 %.</li>')` | List item 2: the padded loops follow the old read loop in every layout, with the largest difference in percent. |
| 781 | `    w('<li>This includes 64+32. There the load-only loop is 8 % faster than the old loop, and the padded loops are '` | List item 3: the layout 64+32, where the load-only loop is faster than the old loop. The item goes on in line 782. |
| 782 | `      'not.</li>')` | Continues line 781: the padded loops are not faster there. |
| 783 | `    w('<li>The drop exists only with many threads on both meshes. With one mesh only (64+0, 0+56) and at 32+32 '` | List item 4: the drop exists only with many threads on both meshes. The item goes on in line 784. |
| 784 | `      'all four loops agree within 1.6 %.</li>')` | Continues line 783: with one mesh only and at 32+32 all four loops agree. The 1.6 % is not in the facts sheet. It follows from the last three rows of the table in lines 793 to 795. |
| 785 | `    w('</ul>')` | Closes the list. |
| 786 | `    w(table('Total read rate in GB/s by thread layout (threads on mesh 0 + threads on mesh 1; '` | Starts the table of the totals by thread layout. The caption goes on in line 787. |
| 787 | `            'one interval per cell)' + r(8),` | Continues line 786: one interval per cell, and the citation mark of reference 8. |
| 788 | `            ['layout', 'oldread', 'asmread (load-only)', 'read_nop96', 'read_nop128'],` | Continues line 786: the five column titles: the layout and the four loops. |
| 789 | `            [['56+56', '534.8', '300.1', '538.1', '547.1'],` | Continues line 786: the row for 56+56. |
| 790 | `             ['48+48', '412.1', '349.9', '414.4', '417.2'],` | Continues line 786: the row for 48+48. |
| 791 | `             ['64+44', '432.9', '356.3', '437.2', '435.0'],` | Continues line 786: the row for 64+44. |
| 792 | `             ['64+32', '412.2', '445.0', '417.8', '413.4'],` | Continues line 786: the row for 64+32. |
| 793 | `             ['64+0', '348.0', '348.4', '349.0', '351.0'],` | Continues line 786: the row for 64+0, mesh 0 only. |
| 794 | `             ['0+56', '318.0', '318.1', '319.2', '321.7'],` | Continues line 786: the row for 0+56, mesh 1 only. |
| 795 | `             ['32+32', '336.9', '336.5', '339.9', '341.9']]))` | Continues line 786: the row for 32+32. The closing brackets end the table. |

### `build`: section 4 of the page, mixed loops (lines 797 to 826)

| Line | Source | Explanation |
|---:|---|---|
| 797 | `    # ------------------------------------------------ (d)` | Comment: the block for section 4 of the page. |
| 798 | `    w('<h2 id="d">4. With mixed loops, the deeper window takes the larger share</h2>')` | Writes the title of section 4. The numbers of this section are fixed text or come from the table `F3`. They stand in section F3 of the facts sheet [Ref1]. |
| 799 | `    w('<ul>')` | Opens the first list of the section. |
| 800 | `    w('<li>Two processes ran at the same time, one per mesh, for 12 s. Each process ran one loop. '` | List item 1: two processes ran at the same time, one per mesh, each with one loop. The item goes on in line 801. |
| 801 | `      'The two intervals overlapped by 98.8 % to 99.97 %' + r(9) + '.</li>')` | Continues line 800: how much the two intervals overlapped, with the citation mark of reference 9. |
| 802 | `    w('<li>The rate of a thread depends on the loop of the other threads.</li>')` | List item 2: the rate of a thread depends on the loop of the other threads. |
| 803 | `    w('<li>Mesh 0 alone with the load-only loop reads 348 GB/s. With the load-only loop on mesh 0 and a padded loop '` | List item 3: the rate of mesh 0 alone, and the case of the load-only loop on mesh 0 with a padded loop on mesh 1. The item goes on in line 804. |
| 804 | `      'on mesh 1, mesh 0 reads 331.9 to 349.8 GB/s. Mesh 1 is squeezed to 108 to 116 GB/s.</li>')` | Continues line 803: the range of mesh 0 in that case and the range to which mesh 1 falls. The numbers are those of the pairs 4 and 7 of `F3`, as fixed text. |
| 805 | `    w('<li>The reverse case also holds. With <code>read_nop256</code> on mesh 0 and the load-only loop on mesh 1, '` | List item 4: the reverse case, with `read_nop256` on mesh 0 and the load-only loop on mesh 1. The item goes on in line 806. |
| 806 | `      'mesh 0 reads 137.3 GB/s and mesh 1 reads 251.3 GB/s.</li>')` | Continues line 805: the two sums of pair 3 of `F3`, as fixed text. |
| 807 | `    w('</ul>')` | Closes the list. |
| 808 | `    w('<figure><div class="fig">' + g2.done() + '</div><figcaption><b>Figure 2.</b> Sum of the read rate of each '` | Opens the figure block and puts in the SVG text of Figure 2 (`g2.done()`). Then the caption starts. The piece goes on in lines 809 to 812. |
| 809 | `      'mesh for nine pairs of loops. "load-only" is <code>asmread</code>, "nop96" is <code>read_nop96</code>, '` | Continues line 808: the caption explains the three short loop names of the figure. |
| 810 | `      '"nop256" is <code>read_nop256</code>. <span class="take">Takeaway for the question: the read rate of a mesh '` | Continues line 808: the takeaway sentence starts, in the class `take`. |
| 811 | `      'depends on the loop of the other mesh. The mesh with the deeper window takes the larger share, and the other '` | Continues line 808: the mesh with the deeper window takes the larger share. |
| 812 | `      'mesh loses rate.</span></figcaption></figure>')` | Continues line 808: the other mesh loses rate. The piece closes the caption and the figure block. |
| 813 | `    w(table('Exact numbers of Figure 2: sum in GB/s' + r(9),` | Starts the table with the exact numbers of Figure 2, with the citation mark of reference 9. The call goes on in lines 814 to 815. |
| 814 | `            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0 sum', 'mesh 1 sum', 'total'],` | Continues line 813: the five column titles. |
| 815 | `            [[a, b, '%.1f' % m0, '%.1f' % m1, '%.1f' % t] for a, b, m0, m1, t in F3], num_from=2))` | Continues line 813: one row per pair of `F3`: the two loops, then the two sums and the total with one decimal. `num_from=2` right-aligns the three number columns. |
| 816 | `    w('<ul>')` | Opens the second list of the section. |
| 817 | `    w('<li>The loops were also mixed inside both meshes: even CPUs ran the load-only loop and odd CPUs ran a '` | List item: the loops were also mixed inside both meshes. Even CPUs ran the load-only loop. The item goes on in line 818. |
| 818 | `      'padded loop' + r(9) + '.</li>')` | Continues line 817: odd CPUs ran a padded loop. The citation mark of reference 9 follows. |
| 819 | `    w('<li>With <code>read_nop256</code> on the odd CPUs, the load-only threads read 3.04 to 3.36 GB/s each. '` | List item: the case with `read_nop256` on the odd CPUs, with the rate per thread of the load-only threads. The item goes on in line 820. |
| 820 | `      'The <code>read_nop256</code> threads read 1.99 to 2.20 GB/s each. The total is 318.2 GB/s.</li>')` | Continues line 819: the rate per thread of the `read_nop256` threads and the total. |
| 821 | `    w('<li>With <code>read_nop96</code> on the odd CPUs, the values are 2.63 to 3.08 GB/s against 2.06 to '` | List item: the case with `read_nop96` on the odd CPUs, with the two ranges per thread. The item goes on in line 822. |
| 822 | `      '2.40 GB/s. The total is 306.3 GB/s.</li>')` | Continues line 821: the total of that case. |
| 823 | `    w('<li>In the same split, all <code>read_nop256</code> gives 548.3 GB/s and all <code>asmread</code> gives '` | List item: the two controls in the same split, all threads with `read_nop256` or all with `asmread`. The item goes on in line 824. |
| 824 | `      '300.3 GB/s.</li>')` | Continues line 823: the total of the second control. |
| 825 | `    w('</ul>')` | Closes the list. |

### `build`: section 5 of the page, latency probe and lines in flight (lines 827 to 862)

| Line | Source | Explanation |
|---:|---|---|
| 827 | `    # ------------------------------------------------ (e)` | Comment: the block for section 5 of the page. |
| 828 | `    w('<h2 id="e">5. The slow state is not congestion</h2>')` | Writes the title of section 5. The numbers of this section are fixed text or come from the table `F4`. They stand in section F4 of the facts sheet [Ref1]. |
| 829 | `    w('<h3>Latency probe and lines in flight</h3><ul>')` | Writes the title of the first sub-section and opens its list. |
| 830 | `    w('<li>One core per mesh (CPU 2 and CPU 66) ran a latency probe (a pointer chase). Each step issues two '` | List item 1: one core per mesh, CPU 2 and CPU 66, ran a latency probe. The item goes on in lines 831 to 832. |
| 831 | `      'independent loads that miss the cache at the same time. So the step time is about the time of one DRAM read. '` | Continues line 830: each step of the probe has two loads that miss the cache at the same time. So the time of one step is about the time of one read from memory. |
| 832 | `      'The other 118 cores ran a read loop' + r(10) + '.</li>')` | Continues line 830: the other 118 cores ran a read loop. The citation mark of reference 10 follows. |
| 833 | `    w('<li>On the idle machine one step takes 146.9 ns on both CPUs' + r(10) + '.</li>')` | List item 2: the time of one step on the idle machine, the same on both CPUs, with the citation mark of reference 10. |
| 834 | `    w('<li>With the load-only loop on all cores (total 298 GB/s) one step takes 203.1 ns and 211.3 ns. '` | List item 3: the two step times with the load-only loop on all cores. They are the probe times of case 1 of `F4`. The item goes on in line 835. |
| 835 | `      'With the padded loops on all cores one step takes 238.0 to 286.5 ns' + r(10) + '.</li>')` | Continues line 834: the range of the step time with the padded loops on all cores, with the citation mark of reference 10. |
| 836 | `    w('<li>With the load-only loop on mesh 0 against <code>read_nop256</code> on mesh 1, one step takes 297.1 ns '` | List item 4: the mixed case with the load-only loop on mesh 0 against `read_nop256` on mesh 1. The item goes on in lines 837 to 838. |
| 837 | `      'on mesh 0 (fast) and 236.4 ns on mesh 1 (squeezed). In the reverse case one step takes 212.9 ns on mesh 0 '` | Continues line 836: the two step times of that case, and the first step time of the reverse case. |
| 838 | `      '(squeezed) and 223.5 ns on mesh 1 (fast)' + r(10) + '.</li>')` | Continues line 836: the second step time of the reverse case, with the citation mark of reference 10. |
| 839 | `    w('<li>So one memory request takes less time in the slow state than in the fast states: 203 to 211 ns against '` | List item 5: the reading. One memory request takes less time in the slow state than in the fast states. The two ranges are rounded forms of the probe times. The item goes on in line 840. |
| 840 | `      '238 to 297 ns. The 297 ns is the fast mesh 0 of the mixed case.</li>')` | Continues line 839: the upper range, and which case gives its largest value. |
| 841 | `    w('<li>Lines in flight per streaming core (est.) = lines per second per thread x probe time. '` | List item 6: the formula of the lines in flight per streaming core: lines per second per thread times the probe time. The item goes on in line 842. |
| 842 | `      'The estimate assumes that a request of a streaming core takes as long as a request of the probe.</li>')` | Continues line 841: the assumption behind the estimate. A request of a streaming core takes as long as a request of the probe. |
| 843 | `    w('<li>Slow or squeezed meshes have 6.5 to 9.2 lines in flight per core (est.). '` | List item 7: the range of the lines in flight for slow or squeezed meshes, marked as an estimate. The item goes on in line 844. |
| 844 | `      'Fast meshes have 14.9 to 25.3 (est.).</li>')` | Continues line 843: the range for fast meshes, marked as an estimate. |
| 845 | `    w('</ul>')` | Closes the list. |
| 846 | `    w('<figure><div class="fig">' + g3.done() + '</div><figcaption><b>Figure 3.</b> Estimated lines in flight per '` | Opens the figure block and puts in the SVG text of Figure 3 (`g3.done()`). Then the caption starts. The piece goes on in lines 847 to 851. |
| 847 | `      'streaming core (est.), one row per case of the latency probe. A streaming core is a core that runs a read loop. '` | Continues line 846: one row per case of the latency probe, and what a streaming core is. |
| 848 | `      'The column at the right is the time of one DRAM read by a test core, in ns. '` | Continues line 846: what the column at the right of the figure shows. |
| 849 | `      '<span class="take">Takeaway for the question: the drop is not congestion. A slow or squeezed mesh keeps about '` | Continues line 846: the takeaway sentence starts, in the class `take`. The drop is not congestion. |
| 850 | `      '8 lines (est.) in flight per core instead of about 20 (est.), although each request is served faster.'` | Continues line 846: a slow or squeezed mesh keeps fewer lines in flight per core, though each request is served faster. Both numbers are marked as estimates. |
| 851 | `      '</span></figcaption></figure>')` | Continues line 846: the piece closes the takeaway, the caption and the figure block. |
| 852 | `    rows = [['idle machine', '–', '–', '–', '146.9', '146.9']]` | `rows`: the rows of the next table. The first row is the idle machine. It has dashes for the loops and for the lines in flight, and the probe time of both CPUs as fixed text. |
| 853 | `    for a, b, l0, l1, p2, p66 in F4:` | Starts a loop over the cases of `F4`. |
| 854 | `        rows.append([a, b if b else 'idle (no stream)', f1(l0), f1(l1) if l1 is not None else '–',` | Adds one row: the two loops, with the words for an idle mesh in place of `None`. Then the lines in flight of mesh 0 and of mesh 1, each rounded once to one decimal by `f1`, or a dash for `None`. The call goes on in line 855. |
| 855 | `                     '%.1f' % p2, '%.1f' % p66])` | Continues line 854: the two probe times with one decimal. |
| 856 | `    w(table('Exact numbers of Figure 3: lines in flight per streaming core (est.) and probe time per step' + r(10),` | Starts the table with the exact numbers of Figure 3, with the citation mark of reference 10. The call goes on in lines 857 to 858. |
| 857 | `            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0, lines (est.)', 'mesh 1, lines (est.)',` | Continues line 856: the first four column titles. The two titles of the lines in flight carry the mark of an estimate. |
| 858 | `             'CPU 2, ns', 'CPU 66, ns'], rows, num_from=2))` | Continues line 856: the two titles of the probe times in ns, and the rows. `num_from=2` right-aligns the four number columns. |
| 859 | `    w('<p class="note">The lines in flight per case were recomputed for this report from the raw files of the probe '` | Starts a note paragraph: the lines in flight per case were computed again for this report from the raw files of the probe run. The piece goes on in lines 860 to 861. |
| 860 | `      'run' + r(10) + '. Each value is the mean over the streaming threads of one mesh. '` | Continues line 859: the citation mark of reference 10. Each value is the mean over the streaming threads of one mesh. |
| 861 | `      'They agree with the ranges in the facts sheet' + r(1) + '.</p>')` | Continues line 859: the values agree with the ranges of the facts sheet. The citation mark of reference 1 follows. |

### `build`: section 5 of the page, mesh counters, memory ports and data path (lines 863 to 917)

| Line | Source | Explanation |
|---:|---|---|
| 863 | `    w('<h3>Mesh counters</h3><ul>')` | Writes the title of the sub-section on the mesh counters and opens its list. |
| 864 | `    w('<li>Root counters of the mesh were read during 64+56 runs. No row was multiplexed '` | List item 1: the counters of the mesh were read as root during runs at 64+56. No row was multiplexed. The item goes on in line 865. |
| 865 | `      '(every counter ran for the whole interval)' + r(11) + '.</li>')` | Continues line 864: what that means. Every counter ran for the whole interval. The citation mark of reference 11 follows. |
| 866 | `    w('<li>Per line read, the slow state has fewer retries, a lower queue occupancy and fewer stalls than the fast '` | List item 2: per cache line read, the slow state has fewer retries, a lower queue occupancy and fewer stalls than the fast states. The item goes on in line 867. |
| 867 | `      'states. The exception is the north and south data links' + r(11) + '.</li>')` | Continues line 866: the exception, the data links to the north and to the south, with the citation mark of reference 11. |
| 868 | `    w('<li>Each value in the table is a counter total divided by the number of 64 B lines read. '` | List item 3: how a value of the table is formed: a counter total divided by the number of 64 B lines read. The item goes on in line 869. |
| 869 | `      'A lower value means fewer retries or less waiting per line.</li>')` | Continues line 868: a lower value means fewer retries or less waiting per line. |
| 870 | `    w('<li><b>Insufficient data:</b> what one count of the queue-occupancy counter and of the busy-level counter '` | List item 4: a gap that the page names. It is not known what one count of the queue-occupancy counter and of the busy-level counter stands for. The item goes on in lines 871 to 872. |
| 871 | `      'stands for. The facts sheet does not say it. The counter description in the manual of the mesh would resolve '` | Continues line 870: the facts sheet does not say it, and the manual of the mesh would answer it. |
| 872 | `      'it. The comparison between the states does not need it.</li>')` | Continues line 870: the comparison between the states does not need the answer. |
| 873 | `    w('</ul>')` | Closes the list. |
| 874 | `    w(table('Mesh counters at 64+56: counter events per 64 B line read' + r(11),` | Starts the table of the mesh counters at 64+56, in events per 64 B line read, with the citation mark of reference 11. The call goes on in lines 875 to 884. |
| 875 | `            ['counter', 'slow: asmread, 299 GB/s', 'fast: read_nop96, 470 GB/s', 'fast: oldread, 468 GB/s'],` | Continues line 874: the four column titles: the counter, the slow case with `asmread`, and the two fast cases with `read_nop96` and with `oldread`, each with its total in GB/s. |
| 876 | `            [['home-node request retries (<code>hns_pocq_retry_all</code>)', '0.047', '0.072', '0.069'],` | Continues line 874: the row for the request retries of the home nodes. |
| 877 | `             ['home-node queue occupancy (<code>hns_qos_pocq_occupancy_all</code>)', '0.087', '0.121', '0.118'],` | Continues line 874: the row for the queue occupancy of the home nodes. |
| 878 | `             ['memory-controller retries (<code>hns_mc_retries_local_all</code>)', '0.0046', '0.043', '0.039'],` | Continues line 874: the row for the retries at the memory controllers. |
| 879 | `             ['gateway data stalls (<code>ccra_chidat_stalls</code>)', '0.21', '0.73', '0.73'],` | Continues line 874: the row for the data stalls of the gateway. |
| 880 | `             ['home-node busy level 3 (<code>hns_cbusy11_all</code>)', '0.21', '1.49', '1.53'],` | Continues line 874: the row for busy level 3 at the home nodes. |
| 881 | `             ['request-link stalls east (<code>mxp_e_req_txflit_stall</code>)', '0.013', '0.167', '0.163'],` | Continues line 874: the row for the stalls of the request link to the east. |
| 882 | `             ['data-link stalls east', '0.162', '0.344', '0.351'],` | Continues line 874: the row for the stalls of the data link to the east. |
| 883 | `             ['data-link stalls north (exception)', '0.119', '0.069', '0.073'],` | Continues line 874: the row for the stalls of the data link to the north, marked as an exception. |
| 884 | `             ['data-link stalls south (exception)', '0.027', '0.020', '0.025']]))` | Continues line 874: the row for the stalls of the data link to the south, marked as an exception. The closing brackets end the table. |
| 885 | `    w('<h3>Memory ports</h3><ul>')` | Writes the title of the sub-section on the memory ports and opens its list. |
| 886 | `    w('<li>The 24 memory ports get one read request per line in the slow state and in the fast states' + r(12) + '.</li>')` | List item 1: the 24 memory ports get one read request per line in the slow state and in the fast states, with the citation mark of reference 12. |
| 887 | `    w('<li>They get almost no write data (0.0003 to 0.0004 per line). So DRAM does one read per line in both '` | List item 2: the ports get almost no write data. So the memory does one read per line in both states. The item goes on in line 888. |
| 888 | `      'states. DRAM does no extra reads' + r(12) + '.</li>')` | Continues line 887: the memory does no extra reads. The citation mark of reference 12 follows. |
| 889 | `    w('</ul>')` | Closes the list. |
| 890 | `    w(table('Memory-port counts per line read, 24 ports' + r(12),` | Starts the table of the counts at the memory ports per line read, with the citation mark of reference 12. The call goes on in lines 891 to 896. |
| 891 | `            ['count', 'asmread 64+56 (307 GB/s)', 'read_nop96 (468 GB/s)', 'read_nop256 (550 GB/s)',` | Continues line 890: the first four column titles: the count and three cases at 64+56, each with its total in GB/s. |
| 892 | `             'asmread 64+0 (349 GB/s)'],` | Continues line 890: the fifth column title, `asmread` at 64+0. |
| 893 | `            [['read requests into the ports', '1.004', '1.002', '1.076', '0.997'],` | Continues line 890: the row for the read requests into the ports. |
| 894 | `             ['request stalls', '0.0005', '0.018', '0.030', '0.000'],` | Continues line 890: the row for the request stalls. |
| 895 | `             ['write data into the ports', '0.0004', '0.0003', '0.0003', '0.0003'],` | Continues line 890: the row for the write data into the ports. |
| 896 | `             ['data flits out (2 flits = 1 line)', '1.992', '1.996', '1.995', '1.995']]))` | Continues line 890: the row for the data flits out of the ports. The closing brackets end the table. |
| 897 | `    w('<h3>Data path, busy level and core counters</h3><ul>')` | Writes the title of the sub-section on the data path, the busy level and the core counters, and opens its list. |
| 898 | `    w('<li>Per line, a core gets 0.50 + 0.50 flits from the two memory-port columns of its own mesh and 1.00 flit '` | List item 1: per line, how many flits a core gets from the two columns of memory ports of its own mesh and from the gateway row. The item goes on in line 899. |
| 899 | `      'from the gateway row. This holds in every state: slow, fast, squeezed and alone' + r(13) + '.</li>')` | Continues line 898: this holds in every state. The citation mark of reference 13 follows. |
| 900 | `    w('<li>So half of the lines arrive directly from the memory ports of the own mesh. '` | List item 2: the reading. Half of the lines arrive from the memory ports of the own mesh. The item goes on in line 901. |
| 901 | `      'The other half arrive through the gateway from the other mesh.</li>')` | Continues line 900: the other half arrive through the gateway from the other mesh. |
| 902 | `    w('<li>Response messages with busy level 0 are 82 to 93 % on slow or squeezed meshes. '` | List item 3: the share of response messages with busy level 0 on slow or squeezed meshes. The item goes on in line 903. |
| 903 | `      'They are 4 to 26 % on fast meshes' + r(14) + '.</li>')` | Continues line 902: the same share on fast meshes, with the citation mark of reference 14. |
| 904 | `    w('<li>Three cases are in between. Mesh 1 under <code>read_nop96</code> or <code>oldread</code> at 64+56 has '` | List item 4: three cases lie between. The first is mesh 1 under `read_nop96` or `oldread` at 64+56. The item goes on in lines 905 to 906. |
| 905 | `      '73 to 74 %. Mesh 1 with <code>asmread</code> against <code>read_nop256</code> on mesh 0 has 44 to 46 %'` | Continues line 904: the second is mesh 1 with `asmread` against `read_nop256` on mesh 0. |
| 906 | `      + r(14) + '.</li>')` | Continues line 904: the citation mark of reference 14. |
| 907 | `    w('<li>So the squeezed cores do not receive a higher busy level than the fast cores.</li>')` | List item 5: the reading. The squeezed cores do not receive a higher busy level than the fast cores. |
| 908 | `    w('<li>Data that arrives through the gateway carries busy level 3 in 89 to 100 % of the flits. '` | List item 6: the share of the flits through the gateway that carry busy level 3. The item goes on in line 909. |
| 909 | `      'This holds in every state, also with the other mesh idle' + r(14) + '.</li>')` | Continues line 908: this holds in every state, also with the other mesh idle. The citation mark of reference 14 follows. |
| 910 | `    w('<li>The core counters per line are the same in the slow and fast states. They are 2.08 bus accesses '` | List item 7: the counters of a core per line are the same in the slow and the fast states. It gives the bus accesses per line. The item goes on in lines 911 to 913. |
| 911 | `      '(transfers between the core and the mesh), 1.000 L2 refills (lines that arrive in the L2 cache, the second '` | Continues line 910: a short explanation of a bus access, and the L2 refills per line. |
| 912 | `      'cache level of the core) and 1.000 L2 hardware-prefetch events (as counted by the core for its hardware '` | Continues line 910: a short explanation of an L2 refill, and the hardware-prefetch events of L2 per line. |
| 913 | `      'prefetcher). The instruction counts are as coded' + r(1) + '.</li>')` | Continues line 910: the instruction counts are as coded. The citation mark of reference 1 follows. |
| 914 | `    w('<li>Only the cycles per line differ: 66 to 77 in the slow state against 35 to 37 in the fast state on '` | List item 8: only the cycles per line differ between the slow state and the fast state on mesh 0. The item goes on in line 915. |
| 915 | `      'mesh 0. The core clock is 2.8 GHz in all runs' + r(1) + '.</li>')` | Continues line 914: the core clock in all runs, with the citation mark of reference 1. |
| 916 | `    w('</ul>')` | Closes the list. |

### `build`: section 6 of the page, the scrambled-order loops and their runs (lines 918 to 986)

| Line | Source | Explanation |
|---:|---|---|
| 918 | `    # ------------------------------------------------ (r) scrambled order` | Comment: the block for section 6 of the page, the scrambled order. |
| 919 | `    w('<h2 id="r">6. The drop needs a sequential stream</h2>')` | Writes the title of section 6. The numbers of this section are fixed text or come from the tables `F5` and `FIG4`. They stand in section F5 of the facts sheet [Ref1]. |
| 920 | `    w('<h3>The scrambled-order loops</h3><ul>')` | Writes the title of the first sub-section and opens its list. |
| 921 | `    w('<li>Three more loops were added to the benchmark program (<code>bwx13</code>, the runner): <code>rand_nop0</code>, <code>rand_nop96</code> and '` | List item 1: three more loops were added to the runner `bwx13`. The item goes on in line 922. |
| 922 | `      '<code>rand_nop256</code>' + r(21) + '.</li>')` | Continues line 921: the name of the third loop and the citation mark of reference 21. |
| 923 | `    w('<li>They read the same bytes as the load-only loop: 8 load-pair instructions per 256 B block, and every '` | List item 2: these loops read the same bytes as the load-only loop, every block of 256 B once. The item goes on in line 924. |
| 924 | `      'block once. They add 0, 96 or 256 nop per block.</li>')` | Continues line 923: the number of `nop` instructions that they add per block. |
| 925 | `    w('<li>So their loads and padding are those of the load-only loop (<code>asmread</code>), of '` | List item 3: so their loads and padding are those of three sequential loops. The item goes on in line 926. |
| 926 | `      '<code>read_nop96</code> and of <code>read_nop256</code>.</li>')` | Continues line 925: the names of the second and the third of these loops. |
| 927 | `    w('<li>The difference is the order. The 8192 blocks of each 2 MiB chunk are visited in a scrambled order. '` | List item 4: the difference is the order in which the 8192 blocks of each chunk of 2 MiB are visited. The item goes on in line 928. |
| 928 | `      'Visit number i reads block (i x (2i + 1)) mod 8192' + r(1) + '.</li>')` | Continues line 927: the formula of the order. Visit number i reads the block with the number i times (2i + 1), modulo 8192. The citation mark of reference 1 follows. |
| 929 | `    w('<li>The intent was that the hardware prefetcher cannot follow the order from block to block. '` | List item 5: the intent. The hardware prefetcher should not be able to follow the order from block to block. The item goes on in line 930. |
| 930 | `      'The one-thread counters below do not confirm an idle prefetcher.</li>')` | Continues line 929: the one-thread counters of the next sub-section do not confirm an idle prefetcher. |
| 931 | `    w('<li>The window depth in lines is taken from the sequential loop with the same loads and padding: '` | List item 6: the window depth is taken from the sequential loop with the same loads and padding. The item goes on in lines 932 to 934. |
| 932 | `      '36 to 40 lines, 20 to 24 lines and 8 to 12 lines. '` | Continues line 931: the three window ranges in cache lines, as fixed text. |
| 933 | `      'The scrambled loops have 5 more integer instructions per block' + r(1) + '. '` | Continues line 931: the scrambled loops have 5 more integer instructions per block. The citation mark of reference 1 follows. |
| 934 | `      'Their window depth was not measured separately.</li>')` | Continues line 931: their window depth was not measured separately. |
| 935 | `    w('</ul>')` | Closes the list. |
| 936 | `    w('<h3>One thread</h3><ul>')` | Writes the title of the sub-section on one thread and opens its list. |
| 937 | `    w('<li>One thread on CPU 2 read a 256 MiB buffer. This section uses two runs of 0.5 s per loop, both with '` | List item 1: one thread on CPU 2 read a buffer of 256 MiB. Two runs of 0.5 s per loop are used, both with the common stop. The item goes on in line 938. |
| 938 | `      'the common stop: one for the rate, and one with the core counters switched on' + r(21) + '.</li>')` | Continues line 937: one run gives the rate, the other one has the core counters switched on. The citation mark of reference 21 follows. |
| 939 | `    w('<li>The load-only loop in sequential order read 35.7 GB/s. In scrambled order the loops read 10.8 GB/s '` | List item 2: the rate of the load-only loop in sequential order and the first of the three rates in scrambled order. The item goes on in line 940. |
| 940 | `      '(no padding), 8.4 GB/s (96 nop) and 4.8 GB/s (256 nop).</li>')` | Continues line 939: the rates of the scrambled loops with 96 and with 256 `nop`. |
| 941 | `    w('<li>The core counters differ per line. The scrambled loops have 1.63 to 1.64 L2 refills per line against '` | List item 3: the core counters differ per line. It gives the L2 refills per line of the scrambled loops. The item goes on in lines 942 to 943. |
| 942 | `      '1.00 in sequential order. They have 0.41 to 0.42 loads per line that miss all caches against 0.00 to 0.06 '` | Continues line 941: the value in sequential order, and the loads per line that miss all caches, for both orders. |
| 943 | `      '(<code>read_nop256</code> has 0.00)' + r(1, 21) + '.</li>')` | Continues line 941: the value of `read_nop256`, with the citation marks of the references 1 and 21. |
| 944 | `    w('<li>The scrambled loops show 1.84 to 1.91 L2 hardware-prefetch events per line against 1.00 in sequential '` | List item 4: the hardware-prefetch events of L2 per line of the scrambled loops, against the value in sequential order. The item goes on in line 945. |
| 945 | `      'order' + r(1, 21) + '. So the hardware prefetcher is not idle in scrambled order.</li>')` | Continues line 944: the citation marks of the references 1 and 21, and the reading that the hardware prefetcher is not idle in scrambled order. |
| 946 | `    w('<li>A second counter run of the same test used the whole-pass stop. Its scrambled loops show 1.44 to 1.51 '` | List item 5: a second counter run of the same test used the whole-pass stop. The item goes on in lines 947 to 948. |
| 947 | `      'L2 hardware-prefetch events per line and 0.58 to 0.60 loads per line that miss all caches'` | Continues line 946: its two counter values per line for the scrambled loops. |
| 948 | `      + r(1, 21) + '.</li>')` | Continues line 946: the citation marks of the references 1 and 21. |
| 949 | `    w('<li>So with one thread the scrambled order is the slower one, and the loop has more cache '` | List item 6: the reading. With one thread the scrambled order is the slower one. The item goes on in line 950. |
| 950 | `      'misses.</li>')` | Continues line 949: and the loop has more cache misses. |
| 951 | `    w('</ul>')` | Closes the list. |
| 952 | `    w('<h3>120 threads at 64+56</h3><ul>')` | Writes the title of the sub-section on 120 threads at 64+56 and opens its list. |
| 953 | `    w('<li>Two processes ran at the same time, one per mesh, for 10 s. There is one interval per cell' + r(20) + '.</li>')` | List item 1: two processes ran at the same time, one per mesh, for 10 s, with one interval per cell. The citation mark of reference 20 follows. |
| 954 | `    w('<li>With the scrambled loops on both meshes the total is %s GB/s (no padding), %s GB/s (96 nop) and '` | List item 2: the totals with the scrambled loops on both meshes. The text has three places for numbers. The item goes on in lines 955 to 956. |
| 955 | `      '%s GB/s (256 nop).</li>' % (f1(f5tot('rand_nop0', 'rand_nop0')), f1(f5tot('rand_nop96', 'rand_nop96')),` | Continues line 954: the first two values. `f5tot` adds the two mesh sums of the group in `F5`, and `f1` rounds the total once to one decimal. The groups are `rand_nop0` and `rand_nop96` on both meshes. |
| 956 | `                                   f1(f5tot('rand_nop256', 'rand_nop256'))))` | Continues line 954: the third value, the total of the group `rand_nop256` on both meshes. |
| 957 | `    w('<li>Two sequential controls ran in the same run. The load-only loop gave %s GB/s. '` | List item 3: two controls in sequential order ran in the same run. The text has two places for numbers. The item goes on in lines 958 to 959. |
| 958 | `      '<code>read_nop256</code> gave %s GB/s. Both lie inside the ranges of section 2.</li>' % (` | Continues line 957: a sentence that both values lie inside the ranges of section 2. |
| 959 | `          f1(f5tot('asmread', 'asmread')), f1(f5tot('read_nop256', 'read_nop256'))))` | Continues line 957: the two values: the totals of the groups `asmread` and `read_nop256` on both meshes of `F5`, rounded by `f1`. |
| 960 | `    w('<li><code>read_nop96</code> in sequential order was not repeated in this run. '` | List item 4: `read_nop96` in sequential order was not repeated in this run. The item goes on in line 961. |
| 961 | `      'Figure 4 uses its range from section 2: 465.5 to 470.6 GB/s (n = 16)' + r(6) + '.</li>')` | Continues line 960: Figure 4 uses its range from section 2. The range and its number of intervals are fixed text, equal to the row of `F2` (line 56). The citation mark of reference 6 follows. |
| 962 | `    w('</ul>')` | Closes the list. |
| 963 | `    w('<figure><div class="fig">' + g4.done() + '</div><figcaption><b>Figure 4.</b> Total read rate at 64+56 in '` | Opens the figure block and puts in the SVG text of Figure 4 (`g4.done()`). Then the caption starts. The piece goes on in lines 964 to 973. |
| 964 | `      'sequential order and in scrambled order, for the same loads and the same padding. One row per padding. '` | Continues line 963: the figure compares the two orders for the same loads and the same padding, one row per padding. |
| 965 | `      'The window depth is that of the sequential loop. Each scrambled value and the sequential values of rows 1 '` | Continues line 963: the window depth is that of the sequential loop. The scrambled values and the sequential values of the rows 1 and 3 belong together. The sentence goes on in line 966. |
| 966 | `      'and 3 are one 10 s interval of the same run. The sequential value of row 2 is the range of 16 intervals of '` | Continues line 963: they are one interval of 10 s each, from the same run. The sequential value of row 2 is a range of 16 intervals. The sentence goes on in line 967. |
| 967 | `      'earlier runs of the same evening, and its mark is the middle of that range. '` | Continues line 963: that range comes from earlier runs of the same evening, and its mark stands at the middle of the range. |
| 968 | `      '<span class="take">Takeaway: with the deepest window the scrambled order reads %s GB/s and the sequential '` | Continues line 963: the takeaway sentence starts, in the class `take`. It has two places for numbers: the scrambled total with the deepest window, and the sequential total. The sentence goes on in line 969. |
| 969 | `      'order reads %s GB/s, so the deep window alone does not lower the total.</span> Hypothesis, not tested: part of the fall of the '` | Continues line 963: the deep window alone does not lower the total. Then a hypothesis starts, marked as not tested. |
| 970 | `      'scrambled values to %s GB/s is the limit of one core with 256 nop (4.8 GB/s with one thread).'` | Continues line 963: the hypothesis has a third place for a number. Part of the fall of the scrambled values to that number is the limit of one core with 256 `nop`. |
| 971 | `      '</figcaption></figure>' % (` | Continues line 963: the piece closes the caption and the figure block. The values for the three places follow in lines 972 to 973. |
| 972 | `          f1(f5tot('rand_nop0', 'rand_nop0')), f1(f5tot('asmread', 'asmread')),` | Continues line 963: the totals of the groups `rand_nop0` on both meshes and `asmread` on both meshes, each rounded by `f1`. |
| 973 | `          f1(f5tot('rand_nop256', 'rand_nop256'))))` | Continues line 963: the total of the group `rand_nop256` on both meshes, rounded by `f1`. |
| 974 | `    rows = []` | `rows`: the rows of the next table, empty at first. |
| 975 | `    for a, b, m0, m1, a0, a1, b0, b1 in F5:` | Starts a loop over the groups of `F5`. |
| 976 | `        rows.append(['<code>%s</code>' % a, '<code>%s</code>' % b if b else 'idle (no stream)', f1(m0),` | Adds one row: the two loops as code text, with the words for an idle mesh in place of `None`. Then the mesh 0 sum, rounded by `f1`. The call goes on in lines 977 to 978. |
| 977 | `                     f1(m1) if b else '–', f1(m0 + (m1 or 0.0)), '%.2f–%.2f' % (a0, a1),` | Continues line 976: the mesh 1 sum or a dash. Then the total: the two unrounded sums are added first and `f1` rounds the result once. Then the per-thread range of mesh 0, with two decimals. |
| 978 | `                     '%.2f–%.2f' % (b0, b1) if b else '–'])` | Continues line 976: the per-thread range of mesh 1 with two decimals, or a dash. |
| 979 | `    w(table('Scrambled-order run: sum in GB/s per mesh and per-thread range in GB/s. 13 groups, 24 processes, '` | Starts the table of the scrambled-order run. The caption names the two kinds of values and the size of the run: 13 groups and 24 processes. The call goes on in lines 980 to 982. |
| 980 | `            'one 10 s interval per cell. 64 threads on mesh 0, 56 threads on mesh 1' + r(20),` | Continues line 979: one interval of 10 s per cell, the threads per mesh, and the citation mark of reference 20. |
| 981 | `            ['mesh 0 loop', 'mesh 1 loop', 'mesh 0 sum', 'mesh 1 sum', 'total', 'mesh 0, per thread',` | Continues line 979: the first six column titles. |
| 982 | `             'mesh 1, per thread'], rows, num_from=2))` | Continues line 979: the seventh column title and the rows. `num_from=2` right-aligns the five number columns. |
| 983 | `    w('<p class="note">The values of this table were recomputed for this report from the raw files of the run'` | Starts a note paragraph: the values of this table were computed again for this report from the raw files of the run. The piece goes on in lines 984 to 986. |
| 984 | `      + r(20) + '. They agree with the facts sheet to 0.1 GB/s' + r(1) + '. '` | Continues line 983: the citation mark of reference 20. The values agree with the facts sheet within 0.1 GB/s. The citation mark of reference 1 follows. |
| 985 | `      'A total is the sum of the unrounded mesh sums. So it can differ by 0.1 GB/s from the sum of the two rounded '` | Continues line 983: a total is the sum of the unrounded mesh sums. So it can differ by 0.1 GB/s from the sum of the two rounded values. |
| 986 | `      'values.</p>')` | Continues line 983: the end of the sentence and of the paragraph. |

### `build`: section 6 of the page, mixed pairs, reading and limits (lines 987 to 1019)

| Line | Source | Explanation |
|---:|---|---|
| 987 | `    w('<h3>Mixed pairs</h3><ul>')` | Writes the title of the sub-section on the mixed pairs and opens its list. |
| 988 | `    w('<li>In the four pairs of a sequential loop against a scrambled loop, the mesh with the sequential loop reads '` | List item 1: in the four pairs of a sequential loop against a scrambled loop, the mesh with the sequential loop reads more. The item goes on in line 989. |
| 989 | `      'more (rows 6 to 9 of the table).</li>')` | Continues line 988: these are the rows 6 to 9 of the table. |
| 990 | `    w('<li>With <code>read_nop256</code> on the other mesh, <code>rand_nop0</code> reads %s GB/s on mesh 0 and '` | List item 2: the rate of `rand_nop0` with `read_nop256` on the other mesh, and with `rand_nop0` on both meshes. The text has four places for numbers. The item goes on in lines 991 to 992. |
| 991 | `      '%s GB/s on mesh 1. With <code>rand_nop0</code> on both meshes it reads %s GB/s and %s GB/s.</li>' % (` | Continues line 990: the second half of the sentence, with the third and the fourth place. |
| 992 | `          f1(F5[5][2]), f1(F5[6][3]), f1(F5[0][2]), f1(F5[0][3])))` | Continues line 990: the four values, each rounded by `f1`. They are the mesh 0 sum of group 6, the mesh 1 sum of group 7, and the two sums of group 1 of `F5`. |
| 993 | `    w('<li>Mesh 0 alone reads %s GB/s with <code>rand_nop0</code> and %s GB/s with <code>rand_nop256</code>.</li>' % (` | List item 3: the rate of mesh 0 alone with `rand_nop0` and with `rand_nop256`. The text has two places for numbers. The item goes on in line 994. |
| 994 | `        f1(F5[11][2]), f1(F5[12][2])))` | Continues line 993: the two values, the mesh 0 sums of the groups 12 and 13 of `F5`, rounded by `f1`. |
| 995 | `    w('</ul>')` | Closes the list. |
| 996 | `    w('<h3>Reading</h3><ul>')` | Writes the title of the sub-section with the reading and opens its list. |
| 997 | `    w('<li>In scrambled order the deep window is the faster one: %s GB/s (no padding) is above %s GB/s (96 nop), '` | List item 1: in scrambled order the deep window is the faster one. The text has three places for the scrambled totals. The item goes on in lines 998 to 1000. |
| 998 | `      'and that is above %s GB/s (256 nop). In sequential order it is the reverse: %s GB/s is below 465.5 to '` | Continues line 997: in sequential order it is the reverse. A fourth place holds the sequential total without padding. The range of `read_nop96` is fixed text. |
| 999 | `      '470.6 GB/s, and that is below %s GB/s.</li>' % (` | Continues line 997: a fifth place holds the sequential total with 256 `nop`. |
| 1000 | `          f1(FIG4[0][6]), f1(FIG4[1][6]), f1(FIG4[2][6]), f1(FIG4[0][3]), f1(FIG4[2][3])))` | Continues line 997: the five values, each rounded by `f1`: the scrambled totals of the three rows of `FIG4`, then the sequential totals of its first and of its third row. |
| 1001 | `    w('<li>Hypothesis: part of the fall to %s GB/s is the limit of one core with 256 nop. ' % f1(FIG4[2][6]) +` | List item 2: a hypothesis. Part of the fall to the scrambled total with 256 `nop` is the limit of one core with 256 `nop`. The number comes from the third row of `FIG4`. The item goes on in lines 1002 to 1004. |
| 1002 | `      '<code>rand_nop256</code> reads 4.8 GB/s with one thread' + r(21) + '. It reads 3.15 to 3.22 GB/s per thread '` | Continues line 1001: the rate of `rand_nop256` with one thread, with the citation mark of reference 21. Then its range per thread with 120 threads, as fixed text. It is a rounded form of the per-thread values of group 3 of `F5`. |
| 1003 | `      'with 120 threads' + r(20) + '. A run of <code>rand_nop256</code> with fewer threads per mesh would test '` | Continues line 1001: the citation mark of reference 20, and a run that would test the hypothesis. |
| 1004 | `      'this. That run was not done.</li>')` | Continues line 1001: that run was not done. |
| 1005 | `    w('<li>The same loads and padding (window depth assumed equal, not measured) read %s GB/s in scrambled order '` | List item 3: the same loads and padding read more in scrambled order than in sequential order. The text has two places for numbers, and it says that the window depth is assumed equal. The item goes on in lines 1006 to 1008. |
| 1006 | `      'and %s GB/s in sequential order. So the deep window alone does not lower the total. In this run the drop '` | Continues line 1005: so the deep window alone does not lower the total. In this run the drop appeared in sequential order. |
| 1007 | `      'appeared in sequential order. It did not appear in the one scrambled order tested.</li>' % (` | Continues line 1005: it did not appear in the one scrambled order that was tested. |
| 1008 | `          f1(FIG4[0][6]), f1(FIG4[0][3])))` | Continues line 1005: the two values, the scrambled total and the sequential total of the first row of `FIG4`, rounded by `f1`. |
| 1009 | `    w('<li>So the drop depends on how the cores handle a sequential stream. The facts sheet reads this as: the rule is in the cores, not in the mesh, the gateways or '` | List item 4: the drop depends on how the cores handle a sequential stream. The text gives the reading of the facts sheet: the rule is in the cores. The item goes on in lines 1010 to 1011. |
| 1010 | `      'DRAM' + r(1) + '. This narrows the open item of section 7. The exact rule inside the core is still not '` | Continues line 1009: not in the mesh, the gateways or the memory. The citation mark of reference 1 follows. This narrows the open item of section 7. |
| 1011 | `      'established.</li>')` | Continues line 1009: the exact rule inside the core is still not established. |
| 1012 | `    w('</ul>')` | Closes the list. |
| 1013 | `    w('<p class="note">Limits of this section: every cell is one interval of 10 s from one evening. No cell was '` | Starts a note paragraph with the limits of this section: every cell is one interval of 10 s from one evening. The piece goes on in lines 1014 to 1018. |
| 1014 | `      'repeated. Only one scrambled pattern was tested. The hardware prefetcher was not switched off. Its settings were not '` | Continues line 1013: no cell was repeated, only one scrambled pattern was tested, and the hardware prefetcher was not switched off. |
| 1015 | `      'read. The one-thread counters show hardware-prefetch events in scrambled order too (1.84 to 1.91 per line), '` | Continues line 1013: its settings were not read. The one-thread counters show hardware-prefetch events in scrambled order too. |
| 1016 | `      'so the scrambled loops do not show the cores without prefetch. The window depth of the scrambled loops was '` | Continues line 1013: so the scrambled loops do not show the cores without prefetch. The window depth of the scrambled loops is the next point. |
| 1017 | `      'not measured. The latency probe did not run with the '` | Continues line 1013: it was not measured. The latency probe did not run with the scrambled loops. |
| 1018 | `      'scrambled loops, so their lines in flight are not known.</p>')` | Continues line 1013: so their lines in flight are not known. The piece closes the paragraph. |

### `build`: section 7 of the page, what is established and what is not (lines 1020 to 1080)

| Line | Source | Explanation |
|---:|---|---|
| 1020 | `    # ------------------------------------------------ (f)` | Comment: the block for section 7 of the page. |
| 1021 | `    w('<h2 id="f">7. What is established and what is not</h2>')` | Writes the title of section 7. Its text follows the sections "What is established" and "What is not established" of the facts sheet [Ref1]. |
| 1022 | `    w('<h3>Established</h3><ul>')` | Writes the title of the sub-section on what is established and opens its list. |
| 1023 | `    w('<li>Read is the only real drop. Its size at 64+56 is about 300 GB/s against about 468 GB/s (-36 %) '` | List item 1: read is the only real drop, with the two rounded totals at 64+56 and the drop in percent as fixed text. The item goes on in line 1024. |
| 1024 | `      '(sections 1 and 2)' + r(1) + '.</li>')` | Continues line 1023: a pointer to the sections 1 and 2 and the citation mark of reference 1. |
| 1025 | `    w('<li>Cause in the benchmark (section 2)' + r(1) + ':<ul>'` | List item 2: the cause in the benchmark, with the citation mark of reference 1. A list of four points starts. The item goes on in lines 1026 to 1029. |
| 1026 | `      '<li>The load-only loop lets the window of a core cover 36 to 40 lines.</li>'` | Continues line 1025: point 1, the window depth of the load-only loop. |
| 1027 | `      '<li>The old loop covered 18 to 22 lines.</li>'` | Continues line 1025: point 2, the window depth of the old loop. |
| 1028 | `      '<li>Above about 30 lines the 120-thread total falls.</li>'` | Continues line 1025: point 3, the depth above which the 120-thread total falls. |
| 1029 | `      '<li>Vector adds are not needed.</li></ul></li>')` | Continues line 1025: point 4, vector adds are not needed. The piece closes the inner list and the item. |
| 1030 | `    w('<li>Mechanism as far as measured (sections 4 and 5)' + r(1) + ':<ul>'` | List item 3: the mechanism as far as it was measured, with the citation mark of reference 1. A list of five points starts. The item goes on in lines 1031 to 1035. |
| 1031 | `      '<li>Cores (or their prefetchers) whose loop covers more lines take a larger share.</li>'` | Continues line 1030: point 1, cores whose loop covers more lines take a larger share. |
| 1032 | `      '<li>A whole mesh then runs with about 8 lines (est.) in flight per core instead of about 20 (est.).</li>'` | Continues line 1030: point 2, the lines in flight per core of a whole mesh in that case, as two estimates. |
| 1033 | `      '<li>Each request is served faster in that state.</li>'` | Continues line 1030: point 3, each request is served faster in that state. |
| 1034 | `      '<li>Nothing is congested.</li>'` | Continues line 1030: point 4, nothing is congested. |
| 1035 | `      '<li>DRAM does one read per line.</li></ul></li>')` | Continues line 1030: point 5, the memory does one read per line. The piece closes the inner list and the item. |
| 1036 | `    w('<li>Narrowing (section 6)' + r(1, 20) + ':<ul>'` | List item 4: the narrowing by section 6, with the citation marks of the references 1 and 20. A list of four points starts. The item goes on in lines 1037 to 1041. |
| 1037 | `      '<li>A loop with the same loads and padding (window depth assumed equal, not measured) reads 489.6 GB/s '` | Continues line 1036: point 1 starts. A loop with the same loads and padding is compared in both orders. The scrambled total is fixed text here. Lines 954 to 956 compute the same value from `F5`. |
| 1038 | `      'in scrambled order and 297.8 GB/s in sequential order.</li>'` | Continues line 1036: the sequential total, also as fixed text. |
| 1039 | `      '<li>So the deep window alone does not lower the total.</li>'` | Continues line 1036: point 2, the deep window alone does not lower the total. |
| 1040 | `      '<li>The drop depends on how the cores handle a sequential stream.</li>'` | Continues line 1036: point 3, the drop depends on how the cores handle a sequential stream. |
| 1041 | `      '<li>This rests on one scrambled pattern and on one interval of 10 s per cell from one evening.</li></ul></li>')` | Continues line 1036: point 4, the result rests on one scrambled pattern and on one interval of 10 s per cell. The piece closes the inner list and the item. |
| 1042 | `    w('<li>Fix verified (section 2)' + r(1) + ': 72 nop or more per 256 B in the load-only loop restores 459 to '` | List item 5: the fix that was verified, with the citation mark of reference 1: the number of `nop` per 256 B that brings the total back. The item goes on in line 1043. |
| 1043 | `      '480 GB/s. 256 nop gives 544 to 549 GB/s. That is 17 % above the old loop.</li>')` | Continues line 1042: the total with 256 `nop`, and how far it lies above the old loop in percent. |
| 1044 | `    w('</ul>')` | Closes the list. |
| 1045 | `    w('<h3>Not established</h3><ul>')` | Writes the title of the sub-section on what is not established and opens its list. |
| 1046 | `    w('<li><b>Insufficient data:</b> which rule inside the core lowers the lines in flight for a sequential stream '` | List item 1, marked as a gap in the data: which rule inside the core lowers the lines in flight for a sequential stream. The item goes on in lines 1047 to 1062. |
| 1047 | `      'in the slow state. Section 6 shows that the drop depends on the sequential stream. It does not identify the rule. '` | Continues line 1046: section 6 shows that the drop depends on the sequential stream. It does not identify the rule. |
| 1048 | `      'The prefetch controls of the V3AE core cannot be read from a normal Linux program. '` | Continues line 1046: the prefetch controls of the core type cannot be read from a normal Linux program. |
| 1049 | `      'Two hypotheses exist. Neither is confirmed. H-a and H-b are only labels for them' + r(1) + '.'` | Continues line 1046: two hypotheses exist, and neither is confirmed. The citation mark of reference 1 follows. |
| 1050 | `      '<ul><li>Hypothesis H-a: the cores set their request limit or their prefetch strength dynamically. '` | Continues line 1046: an inner list starts. Hypothesis H-a: the cores set their request limit or their prefetch strength dynamically. |
| 1051 | `      'The manual of the Neoverse V2 core documents a dynamic limit of outstanding requests that the busy level '` | Continues line 1046: the manual of another core type, Neoverse V2, documents a dynamic limit of outstanding requests. |
| 1052 | `      'drives (<code>IMP_CPUECTLR2_EL1 TXREQ_LIMIT_DYNAMIC</code>) and adaptive prefetch modes '` | Continues line 1046: the busy level drives that limit. The line names the register and the field of that limit as code text. |
| 1053 | `      '(<code>PF_MODE</code>). It is not known whether the V3AE core has this limit. '` | Continues line 1046: the name of the field of the prefetch modes. It is not known whether the core of CRB has this limit. |
| 1054 | `      'It is not known how the firmware set it. '` | Continues line 1046: it is not known how the firmware set it. |
| 1055 | `      'One finding contradicts a simple form of H-a: the squeezed cores receive lower busy levels.</li>'` | Continues line 1046: one finding contradicts a simple form of H-a. The squeezed cores receive lower busy levels. |
| 1056 | `      '<li>Hypothesis H-b: a prefetcher adapts its distance to how early the data arrives. '` | Continues line 1046: hypothesis H-b. A prefetcher adapts its distance to how early the data arrives. |
| 1057 | `      'This combines with the need to receive both halves of the lines in order (the half from the own mesh and '` | Continues line 1046: this combines with the need to receive both halves of the lines in order. |
| 1058 | `      'the half from the other mesh).</li>'` | Continues line 1046: the two halves are the one from the own mesh and the one from the other mesh. |
| 1059 | `      '<li>Measurement that would resolve it: read the registers <code>IMP_CPUECTLR_EL1</code> and '` | Continues line 1046: the measurement that would resolve the gap: read two control registers of the core on CRB. |
| 1060 | `      '<code>IMP_CPUECTLR2_EL1</code> on CRB (this needs a Linux kernel module or firmware access). '` | Continues line 1046: the name of the second register. Reading them needs a Linux kernel module or access to the firmware. |
| 1061 | `      'Other sources: the prefetch section of the V3AE manual, or a question to Arm support with the data of '` | Continues line 1046: two other sources: the prefetch section of the manual of the core, or a question to the support of Arm. |
| 1062 | `      'sections 4, 5 and 6.</li></ul></li>')` | Continues line 1046: the question would use the data of the sections 4, 5 and 6. The piece closes the inner list and the item. |
| 1063 | `    w('<li><b>Insufficient data:</b> why the write total falls with writers on both meshes. '` | List item 2, marked as a gap in the data: why the write total falls with writers on both meshes. The item goes on in lines 1064 to 1065. |
| 1064 | `      'The fall is the same for old and new loops. The facts sheet names no measurement for it. '` | Continues line 1063: the fall is the same for old and new loops, and the facts sheet names no measurement for it. |
| 1065 | `      'A first step would be the mesh counters of section 5 during write runs at 64+0 and at 64+56.</li>')` | Continues line 1063: a first step that the report proposes: the mesh counters during write runs at 64+0 and at 64+56. |
| 1066 | `    w('<li><b>Insufficient data:</b> why old write stays 3 to 4 % above new write under a common stop. '` | List item 3, marked as a gap in the data: why the old write loop stays a few percent above the new one under a common stop. The item goes on in lines 1067 to 1068. |
| 1067 | `      'The facts sheet names no measurement for it. A first step would be the core counters per line for both '` | Continues line 1066: the facts sheet names no measurement for it. A first step would be the core counters per line. |
| 1068 | `      'write loops.</li>')` | Continues line 1066: for both write loops. |
| 1069 | `    w('</ul>')` | Closes the list. |
| 1070 | `    w('<h3>Limits of this work</h3><ul>')` | Writes the title of the sub-section on the limits of this work and opens its list. |
| 1071 | `    w('<li>All runs come from one evening (2026-11-15, 16:56 to 21:03 UTC) and one machine.</li>')` | List item 1: all runs come from one evening and one machine. The date and the time span are fixed text. |
| 1072 | `    w('<li>Many cells have n = 2 intervals from one process. The layout table has one interval per cell. '` | List item 2: many cells have only 2 intervals from one process, and the layout table has one interval per cell. The item goes on in line 1073. |
| 1073 | `      'The sample count of each value is in the tables.</li>')` | Continues line 1072: the tables give the sample count of each value. |
| 1074 | `    w('<li>The window depth of each loop is a measured range from a test with one thread. '` | List item 3: the window depth of each loop is a measured range from a test with one thread. The item goes on in line 1075. |
| 1075 | `      'It was not measured during the 120-thread runs.</li>')` | Continues line 1074: it was not measured during the 120-thread runs. |
| 1076 | `    w('<li>The lines in flight are estimates (est.). They depend on the assumption named in section 5.</li>')` | List item 4: the lines in flight are estimates. They depend on the assumption that section 5 names. |
| 1077 | `    w('<li>The scrambled-order results of section 6 have one interval of 10 s per cell. No cell was repeated.</li>')` | List item 5: the scrambled-order results have one interval of 10 s per cell, and no cell was repeated. |
| 1078 | `    w('<li>The two "first step" proposals above come from this report. They are not in the facts sheet.</li>')` | List item 6: the two proposals of a first step come from this report. They are not in the facts sheet. |
| 1079 | `    w('</ul>')` | Closes the list. |

### `build`: section 8 of the page, recommendation for the benchmark (lines 1081 to 1094)

| Line | Source | Explanation |
|---:|---|---|
| 1081 | `    # ------------------------------------------------ (g)` | Comment: the block for section 8 of the page. |
| 1082 | `    w('<h2 id="g">8. Recommendation for the benchmark</h2><ul>')` | Writes the title of section 8 and opens its list. The text follows the section "Recommendation for the benchmark" of the facts sheet [Ref1]. |
| 1083 | `    w('<li>Keep the new load-only loops for one-thread and cache-size measurements. '` | List item 1: keep the new load-only loops for measurements with one thread and for cache sizes. The item goes on in line 1084. |
| 1084 | `      'They measure the load path without extra work.</li>')` | Continues line 1083: the reason. They measure the load path without extra work. |
| 1085 | `    w('<li>For whole-chip DRAM read numbers, state the loop. Report the load-only loop and a window-limited loop. '` | List item 2: for whole-chip read numbers, state the loop, and report two loops. The item goes on in lines 1086 to 1087. |
| 1086 | `      'One example is <code>read_nop256</code>: 544 to 549 GB/s at 64+56. '` | Continues line 1085: the example `read_nop256` with its total at 64+56, as fixed text. |
| 1087 | `      'With one thread and a 32 KiB buffer it reaches 23 GB/s, and the core limits it there' + r(1) + '.</li>')` | Continues line 1085: its rate with one thread and a buffer of 32 KiB, where the core limits it. The citation mark of reference 1 follows. |
| 1088 | `    w('<li>The 465 to 470 GB/s of the old read loop is one value among several. The value depends on the loop. '` | List item 3: the total of the old read loop is one value among several, and it depends on the loop. The item goes on in line 1089. |
| 1089 | `      'It is not a constant of the chip' + r(1) + '.</li>')` | Continues line 1088: it is not a constant of the chip. The citation mark of reference 1 follows. |
| 1090 | `    w('<li>For write totals use a common stop time or a long interval. '` | List item 4: for write totals use a common stop time or a long interval. The item goes on in line 1091. |
| 1091 | `      'The whole-pass rule with 0.5 s raises old write by 14 % (144 GB/s against 126 GB/s, median)' + r(1, 4) + '.</li>')` | Continues line 1090: how much the whole-pass rule with 0.5 s raises the old write total, with the two medians as fixed text. The citation marks of the references 1 and 4 follow. |
| 1092 | `    w('<li>The source of the benchmark was not changed' + r(1) + '.</li>')` | List item 5: the source of the benchmark was not changed, with the citation mark of reference 1. |
| 1093 | `    w('</ul>')` | Closes the list. |

### `build`: section 9 of the page, how it was measured (lines 1095 to 1151)

| Line | Source | Explanation |
|---:|---|---|
| 1095 | `    # ------------------------------------------------ (h)` | Comment: the block for section 9 of the page. |
| 1096 | `    w('<h2 id="h">9. How it was measured</h2><ul>')` | Writes the title of section 9 and opens its list. Most of its facts stand in the first paragraphs of the facts sheet [Ref1]. |
| 1097 | `    w('<li>Machine: CRB. All runs: 2026-11-15, 16:56 to 21:03 UTC, a Sunday.</li>')` | List item 1: the machine, and the date, the time span and the day of the week of all runs, as fixed text. |
| 1098 | `    w('<li>Machine state: nobody had reserved the machine in the Slack channel #phoenix-crb. The marker file '` | List item 2: the machine state. Nobody had reserved the machine in the Slack channel. The item goes on in lines 1099 to 1100. |
| 1099 | `      '(a file whose presence says that another performance run is active) was absent. '` | Continues line 1098: the marker file was absent. The text explains the marker file in a few words. |
| 1100 | `      'No other user was logged in' + r(1) + '.</li>')` | Continues line 1098: no other user was logged in. The citation mark of reference 1 follows. |
| 1101 | `    w('<li>Load: this report read the load lines in the 14 result folders of 16:56 to 21:03 UTC again. '` | List item 3: the load. This is the group `LOAD` of the header text. The item says that the report read the load lines of the 14 result folders again. It goes on in lines 1102 to 1111. |
| 1102 | `      'They agree with the facts sheet' + r(1, 17) + '.<ul>'` | Continues line 1101: the values agree with the facts sheet. The citation marks of the references 1 and 17 follow. An inner list starts. |
| 1103 | `      '<li>The 1-minute load average at the start of a script was 0.00 to 71.24.</li>'` | Continues line 1101: the range of the 1-minute load average at the start of a script. It is fixed text. A recomputation for this page from the `env.txt` files gives the same range [Ref17]. |
| 1104 | `      '<li>At the launch of a process it was 0.00 to 109.60.</li>'` | Continues line 1101: the range at the launch of a process, as fixed text. A recomputation for this page from the `launch` lines gives the same range [Ref17]. |
| 1105 | `      '<li>At every one of the 101 launches 1 task was runnable and 0 users were logged in.</li>'` | Continues line 1101: at each of the 101 launches 1 task was runnable and 0 users were logged in. A recomputation for this page gives the same three numbers [Ref17]. |
| 1106 | `      '<li>The scripts wait until at most 2 tasks are runnable.</li>'` | Continues line 1101: the scripts wait until at most 2 tasks are runnable. |
| 1107 | `      '<li>For the scrambled-order run (section 6) the load average was 0.18 at the start of the script and 0.17 to '` | Continues line 1101: the load of the scrambled-order run at the start of its script, and the lower end of the range at its launches, as fixed text. |
| 1108 | `      '68.54 at the 13 launches' + r(20) + '.</li>'` | Continues line 1101: the upper end of that range and the number of launches, 13, with the citation mark of reference 20. A recomputation for this page gives the same values [Ref20]. |
| 1109 | `      '<li>Hypothesis: the high values are the load average that still falls after the earlier 120-thread '` | Continues line 1101: a hypothesis. The high values are the load average that still falls after the earlier 120-thread processes. |
| 1110 | `      'processes of the same script and of this same session. The check: each high value follows the end of such '` | Continues line 1101: the check that would test it: each high value follows the end of such a process by a few minutes at most. |
| 1111 | `      'a process by a few minutes at most (times in <code>launches.txt</code>). This check was not done.</li></ul></li>')` | Continues line 1101: the times for that check stand in `launches.txt`. The check was not done. The piece closes the inner list and the item. |
| 1112 | `    w('<li>Runner: <code>bwx12.c</code> (the earlier runner program <code>bwx11</code> plus 26 loops). The binary on CRB has the '` | List item 4: the runner `bwx12.c`, which is the runner `bwx11` plus 26 loops. The item goes on in line 1113. |
| 1113 | `      'SHA-256 checksum <code>cd58e564...546a</code>' + r(15) + '.</li>')` | Continues line 1112: the first and the last characters of the sha256 of the binary on CRB, with the citation mark of reference 15. |
| 1114 | `    w('<li>Runner of section 6: <code>bwx13</code> (<code>bwx12</code> plus the three scrambled-order loops). '` | List item 5: the runner of section 6, `bwx13`, which is `bwx12` plus the three scrambled-order loops. The item goes on in line 1115. |
| 1115 | `      'The binary on CRB has the SHA-256 checksum <code>a2858df5...8dad</code>' + r(21) + '.</li>')` | Continues line 1114: the first and the last characters of the sha256 of that binary, with the citation mark of reference 21. |
| 1116 | `    w('<li>Run scripts: plain runs, simultaneous processes, and runs with root counters' + r(16) + '.</li>')` | List item 6: the three kinds of run scripts, with the citation mark of reference 16. |
| 1117 | `    w('<li>Root use: the user approved <code>sudo perf stat</code> (the Linux counter tool, run as root for the '` | List item 7: the use of root. The user approved `sudo perf stat`, and the text explains that command in a few words. The item goes on in line 1118. |
| 1118 | `      'whole system). The user also approved temporary changes of settings. No setting was changed' + r(1) + '.</li>')` | Continues line 1117: the user also approved temporary changes of settings, and no setting was changed. The citation mark of reference 1 follows. |
| 1119 | `    w('<li>Window test: one thread on CPU 2. Two independent loads that miss the cache are separated by N filler '` | List item 8: the method of the window test with one thread on CPU 2. The item goes on in lines 1120 to 1121. |
| 1120 | `      'units. The capacity is the N where the time per iteration rises from the time of about one cache miss to '` | Continues line 1119: two loads that miss the cache are separated by N filler units. The capacity is the N at which the time per pass rises. |
| 1121 | `      'about two' + r(5) + '.</li>')` | Continues line 1119: the rise is from about one miss time to about two. The citation mark of reference 5 follows. |
| 1122 | `    w('<li>Latency probe: the probe cores were CPU 2 and CPU 66. The streaming processes used the other 118 cores'` | List item 9: the CPUs of the latency probe, and the 118 cores of the streaming processes. The item goes on in line 1123. |
| 1123 | `      + r(10) + '.</li>')` | Continues line 1122: the citation mark of reference 10. |
| 1124 | `    w('<li>Analysis scripts: six Python scripts compute the totals, the per-mesh rates and the counters per line'` | List item 10: six Python scripts compute the totals, the rates per mesh and the counters per line. The item goes on in line 1125. |
| 1125 | `      + r(18) + '.</li>')` | Continues line 1124: the citation mark of reference 18. |
| 1126 | `    w('<li>Check: an independent checker (a second automated agent, workflow id wf_9d39bfdd-935) recomputed every '` | List item 11: the check. A second automated agent computed every number of the facts sheet again from the raw files. The item goes on in line 1127. |
| 1127 | `      'number of the facts sheet from the raw files. The facts sheet holds the corrected values' + r(1) + '.</li>')` | Continues line 1126: the facts sheet holds the corrected values. The citation mark of reference 1 follows. |
| 1128 | `    w('<li>The scrambled-order section of the facts sheet was added after that check. '` | List item 12: the scrambled-order section of the facts sheet was added after that check. The item goes on in line 1129. |
| 1129 | `      'This report recomputed its 64+56 sums from the raw files (section 6)' + r(20) + '.</li>')` | Continues line 1128: this report computed its sums at 64+56 again from the raw files. The citation mark of reference 20 follows. |
| 1130 | `    w('</ul>')` | Closes the list. |
| 1131 | `    w(table('Sample counts' + r(1, 10, 11, 20, 21),` | Starts the table of the sample counts, with the citation marks of the references 1, 10, 11, 20 and 21. The call goes on in lines 1132 to 1150. |
| 1132 | `            ['measurement', 'samples'],` | Continues line 1131: the two column titles. |
| 1133 | `            [['original run (section 1)', 'n = 6 per read loop, 0.5 s intervals'],` | Continues line 1131: the row for the original run. |
| 1134 | `             ['copy and write at 64+56 (section 1)', 'n = 2 intervals per loop, 6 s and 8 s'],` | Continues line 1131: the row for copy and write at 64+56. |
| 1135 | `             ['write under four timing rules (section 1)', '64 processes, 64 intervals per cell'],` | Continues line 1131: the row for write under four timing rules. |
| 1136 | `             ['window test (section 2)', 'one thread on CPU 2; the number of repetitions is not in the facts sheet'],` | Continues line 1131: the row for the window test. The facts sheet does not give its number of repetitions. |
| 1137 | `             ['read against window depth (section 2)', '12 processes, 177 intervals in total: 169 in the table of '` | Continues line 1131: the row for read against window depth: the processes and the intervals, as in line 762. The row goes on in line 1138. |
| 1138 | `              'Figure 1 (n per loop 2 to 22) and 8 for the three variants read_pf256, read_pf512, read_pf1024'],` | Continues line 1137: the range of `n` per loop and the 8 intervals of the three prefetch variants. |
| 1139 | `             ['4 KiB pages (section 2)', 'one process per page size'],` | Continues line 1131: the row for the pages of 4 KiB. |
| 1140 | `             ['thread layouts (section 3)', 'one interval per cell; a second process for 56+56'],` | Continues line 1131: the row for the thread layouts. |
| 1141 | `             ['mixed loops (section 4)', 'two processes at the same time, 12 s'],` | Continues line 1131: the row for the mixed loops. |
| 1142 | `             ['scrambled-order loops at 64+56 (section 6)', 'run R7: 13 groups, 24 processes, one 10 s interval '` | Continues line 1131: the row for the scrambled-order loops at 64+56: the run R7 with 13 groups and 24 processes. The row goes on in line 1143. |
| 1143 | `              'each (11 groups of two processes at the same time, 2 groups with mesh 0 alone)'],` | Continues line 1142: 11 groups have two processes at the same time, and 2 groups have mesh 0 alone. This fits the table `F5` (lines 105 to 117). |
| 1144 | `             ['scrambled-order loops with one thread (section 6)', 'two runs of 0.5 s per loop on CPU 2: one for the rate, one with counters'],` | Continues line 1131: the row for the scrambled-order loops with one thread. |
| 1145 | `             ['latency probe (section 5)', 'one run per case; per probe core 9 repetitions of 1,000,000 '` | Continues line 1131: the row for the latency probe: one run per case, and 9 repetitions of 1,000,000 passes per probe core. The header line of the raw probe files holds these two numbers [Ref10]. The row goes on in line 1146. |
| 1146 | `              'iterations (header of the raw probe files)'],` | Continues line 1145: the source of the two numbers, in words. |
| 1147 | `             ['mesh counters (section 5)', 'one run per state; 22 counter windows per run (raw folder); '` | Continues line 1131: the row for the mesh counters: one run per state and 22 counting windows per run. The row goes on in line 1148. |
| 1148 | `              'no multiplexed row'],` | Continues line 1147: no row was multiplexed. |
| 1149 | `             ['memory-port counters, data path, busy level, core counters (section 5)',` | Continues line 1131: the row for the counters of the memory ports, the data path, the busy level and the core counters. The row goes on in line 1150. |
| 1150 | `              'not in the facts sheet']], num_from=9))` | Continues line 1149: the facts sheet gives no sample count for them. `num_from=9` is larger than the number of columns, so no column of this table is right-aligned. |

### `build`: the reference list and the end of the page (lines 1152 to 1199)

| Line | Source | Explanation |
|---:|---|---|
| 1152 | `    # ------------------------------------------------ references` | Comment: the block for the reference list of the page. |
| 1153 | `    R = '/home/jhan/workspace/titan/cache-perf/crb/results'` | `R`: the fixed path of the folder with the result folders in the project folder on the agent server. In this repo the result folders lie in the test folders below `tests`. |
| 1154 | `    W = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15'` | `W`: the fixed path of the folder of this investigation in the project folder on the agent server. In this repo it is the folder `w120-2026-11-15`. |
| 1155 | `    refs = [` | `refs`: starts the list of the 21 entries of the reference list. The position in the list gives the number of an entry. |
| 1156 | `        'Facts sheet: <code>%s/FINDINGS.md</code>' % W,` | Entry 1: the facts sheet `FINDINGS.md` in the folder `W`. |
| 1157 | `        'Original run: <code>%s/kernels-20261113T181222Z/threads120.csv</code> (benchmark <code>bandwidth.c</code>)' % R,` | Entry 2: the file `threads120.csv` of the original run of 2026-11-13, made with the benchmark `bandwidth.c`. |
| 1158 | `        'Copy, write and 56+56 runs: <code>%s/w120-R1-20261115T185140Z/</code> (files <code>p4copy.csv</code>, '` | Entry 3: the result folder of the run R1, with the copy runs, the write runs and the 56+56 run. The entry goes on in line 1159. |
| 1159 | `        '<code>p3write.csv</code>, <code>p6w6400.csv</code>, <code>p7w3232.csv</code>, <code>p5r5656.csv</code>)' % R,` | Continues line 1158: the names of four of its five files. |
| 1160 | `        'Write under four timing rules: <code>%s/B10a-*</code> and <code>%s/B10b-*</code>' % (R, R),` | Entry 4: the result folders of the write test under four timing rules. Their names start with `B10a-` and `B10b-`. |
| 1161 | `        'Window test: <code>%s/robsize/</code> (program <code>robsize.c</code>, results '` | Entry 5: the folder `robsize` of the window test, with its program. The entry goes on in line 1162. |
| 1162 | `        '<code>results/rob-k1-*.csv</code>, <code>rob-k2-*.csv</code>, <code>rob-k3-*.csv</code>)' % W,` | Continues line 1161: the three groups of result files of the window test. |
| 1163 | `        'Read runs at 64+56: <code>%s/w120-R0-20261115T165608Z/</code>, <code>w120-R0b-20261115T170342Z/</code>, '` | Entry 6: the result folders of the read runs at 64+56. This line names the runs R0 and R0b. The entry goes on in lines 1164 to 1165. |
| 1164 | `        '<code>w120-R1-20261115T185140Z/</code>, <code>w120-R5-20261115T203152Z/</code>, '` | Continues line 1163: the runs R1 and R5. |
| 1165 | `        '<code>w120-R6-20261115T203438Z/</code>' % R,` | Continues line 1163: the run R6. |
| 1166 | `        '4 KiB pages: <code>%s/w120-R5-20261115T203152Z/nothp.csv</code>' % R,` | Entry 7: the file `nothp.csv` of the run R5, the process with pages of 4 KiB. |
| 1167 | `        'Thread layouts: <code>%s/w120-R0b-20261115T170342Z/</code> and <code>p5r5656.csv</code> of [Ref3]' % R,` | Entry 8: the result folder of the run R0b with the thread layouts. For the second 56+56 process it points to a file of entry 3. |
| 1168 | `        'Mixed loops: <code>%s/w120-R3-20261115T193922Z/</code>' % R,` | Entry 9: the result folder of the run R3 with the mixed loops. |
| 1169 | `        'Latency probe: <code>%s/w120-R4-20261115T200016Z/</code>' % R,` | Entry 10: the result folder of the run R4 with the latency probe. The `LIF` values of `F4` come from it. |
| 1170 | `        'Mesh counters: <code>%s/w120-RC1-20261115T190208Z/</code>' % R,` | Entry 11: the result folder of the run RC1 with the mesh counters. |
| 1171 | `        'Memory-port counters: <code>%s/w120-RC2-20261115T192222Z/</code>' % R,` | Entry 12: the result folder of the run RC2 with the counters of the memory ports. |
| 1172 | `        'Data path to the cores: <code>%s/w120-RC5-20261115T201920Z/</code>' % R,` | Entry 13: the result folder of the run RC5 with the data path to the cores. |
| 1173 | `        'Busy level on responses: <code>%s/w120-RC4-20261115T201114Z/</code> and '` | Entry 14: the result folder of the run RC4 with the busy level on responses. The entry goes on in line 1174. |
| 1174 | `        '<code>w120-RC6-20261115T202517Z/</code>' % R,` | Continues line 1173: the result folder of the run RC6. |
| 1175 | `        'Runner: <code>%s/bwx12-2026-11-15/bwx12.c</code>. Binary on CRB: '` | Entry 15: the source `bwx12.c` of the runner, in a folder beside `W`. The entry goes on in line 1176. |
| 1176 | `        '<code>~/cache-perf/bwx12-20261115/bwx12</code>' % os.path.dirname(W),` | Continues line 1175: the path of the binary on CRB. `os.path.dirname(W)` gives the folder above `W`. |
| 1177 | `        'Run scripts in <code>%s/</code>: <code>r0.sh</code>, <code>rx.sh</code> (plain runs), <code>rg.sh</code> '` | Entry 16: the run scripts in `W`: two for plain runs and one for processes at the same time. The entry goes on in line 1178. |
| 1178 | `        '(simultaneous processes), <code>rc.sh</code>, <code>rc2.sh</code>, <code>rgc.sh</code> (root counters)' % W,` | Continues line 1177: three scripts for runs with root counters. |
| 1179 | `        'All result folders of this session: <code>%s/w120-*</code> (files <code>env.txt</code> and '` | Entry 17: all result folders of this session, whose names start with `w120-`. The entry goes on in line 1180. The group `LOAD` comes from them. |
| 1180 | `        '<code>launches.txt</code>)' % R,` | Continues line 1179: the two files that hold the load, `env.txt` and `launches.txt`. |
| 1181 | `        'Analysis scripts in <code>%s/</code>: <code>an.py</code>, <code>anc.py</code>, <code>anc2.py</code>, '` | Entry 18: the six analysis scripts in `W`. The entry goes on in line 1182. |
| 1182 | `        '<code>anc3.py</code>, <code>anc4.py</code>, <code>ang.py</code>' % W,` | Continues line 1181: the names of the last three scripts. |
| 1183 | `        'Generator of this page: <code>%s/report_w120.py</code>' % W,` | Entry 19: this script, as the generator of the page. |
| 1184 | `        'Scrambled-order run R7: <code>%s/w120-R7-20261115T205946Z/</code> (per group <code>&lt;group&gt;.m0.csv</code> '` | Entry 20: the result folder of the scrambled-order run R7. The values of `F5` come from it. The entry goes on in line 1185. |
| 1185 | `        'and <code>&lt;group&gt;.m1.csv</code>, <code>launches.txt</code>, <code>env.txt</code>)' % R,` | Continues line 1184: its files: one for mesh 0 and one for mesh 1 per group, `launches.txt` and `env.txt`. The text writes the angle brackets around the word group as `&lt;` and `&gt;`, as HTML needs it. |
| 1186 | `        'Runner with the scrambled-order loops: <code>%s/bwx13-2026-11-15/</code> (source <code>bwx13.c</code>, '` | Entry 21: the folder of the runner `bwx13` with the scrambled-order loops, and its source. The entry goes on in lines 1187 to 1188. |
| 1187 | `        'one-thread test <code>crb-build-1/smoke13.txt</code>). Binary on CRB: '` | Continues line 1186: the file of the one-thread test, `smoke13.txt`, and the words in front of the path of the binary. |
| 1188 | `        '<code>~/cache-perf/bwx13-20261115/bwx13</code>' % os.path.dirname(W),` | Continues line 1186: the path of the binary on CRB. |
| 1189 | `    ]` | Ends the list `refs`. |
| 1190 | `    w('<h2 id="refs">References</h2><ol class="refs">')` | Writes the title of the reference list and opens the list. |
| 1191 | `    for i, t in enumerate(refs):` | Starts a loop over the entries. `i` counts from 0. |
| 1192 | `        w('<li>[Ref%d] %s</li>' % (i + 1, t))` | Writes one list item: the citation mark with the number `i + 1`, then the text of the entry. |
| 1193 | `    w('</ol>')` | Closes the list. |
| 1194 | `    w('</main>\n</body>\n</html>\n')` | Closes the main block, the body and the HTML page. |
| 1196 | `    bad = g1.overlaps() + g2.overlaps() + g3.overlaps() + g4.overlaps()` | `bad`: the label overlaps of the four figures, joined into one list. Each figure object gives its own list (`overlaps`). |
| 1197 | `    return '\n'.join(P), bad` | Returns two things: all pieces of the page joined with line ends, and the list of overlaps. |

### The main part: write the page and report label overlaps (lines 1200 to 1208)

| Line | Source | Explanation |
|---:|---|---|
| 1200 | `if __name__ == '__main__':` | The lines lines 1201 to 1208 run only when the file is started as a script, not when another file loads it as a module. |
| 1201 | `    html, bad = build()` | Calls `build`. `html` is the text of the page. `bad` is the list of label overlaps. |
| 1202 | `    with open(OUT, 'w', encoding='utf-8') as f:` | Opens the output file `OUT` for writing, in the character set UTF-8. An older file of that name is replaced. |
| 1203 | `        f.write(html)` | Writes the page. The page is written also when `bad` is not empty. |
| 1204 | `    print('wrote %s (%d bytes)' % (OUT, len(html.encode('utf-8'))))` | Prints the path of the page and its size in bytes. |
| 1205 | `    for b in bad:` | Starts a loop over the overlaps. |
| 1206 | `        print('LABEL OVERLAP:', b)` | Prints one line per overlap: the words `LABEL OVERLAP:` and the entry, which holds the name of the figure and the two boxes. |
| 1207 | `    print('label overlaps: %d' % len(bad))` | Prints the number of overlaps. |
| 1208 | `    sys.exit(1 if bad else 0)` | Ends the script with exit status 1 when there is an overlap, and with 0 if not. |

## References

- [Ref1] `FINDINGS.md` in the folder `w120-2026-11-15`: the facts sheet of 2026-11-15.
- [Ref10] The result folder `w120-R4-20261115T200016Z` in the test folder `2026-11-15-whole-chip-read-drop`: the files `CASE.m0.csv` and `CASE.m1.csv` with the `T` rows (columns `bytes` and `elapsed_s`), and the files `CASE.probe2.csv` and `CASE.probe66.csv` with the row `nop,0,` (column `median_ns`).
- [Ref17] The files `env.txt` and `launches.txt` of the 14 result folders `w120-*` of 2026-11-15 in the test folder `2026-11-15-whole-chip-read-drop`.
- [Ref20] The result folder `w120-R7-20261115T205946Z` in the same test folder: the files `GROUP.m0.csv` and `GROUP.m1.csv` with the `T` rows, and the files `env.txt` and `launches.txt`.
