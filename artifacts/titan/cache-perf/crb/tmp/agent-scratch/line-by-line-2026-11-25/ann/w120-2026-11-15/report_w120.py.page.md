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
- **Citation mark**: the text `Ref` with a number in square brackets that the report page puts after a claim. The function `r` writes it. The numbers are those of the reference list of the report page ({L1155-1189}).
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. At load time the script sets the path of the page ({L21-23}), the colours ({L26-32}) and the data tables `F2`, `F3`, `F4`, `F5` and `FIG4` ({L37-138}).
2. The main part calls `build` ({L1200-1201}).
3. `build` first draws the four figures. Each figure function fills an object of the class `Svg`, which collects the drawing commands and a box for every label and mark ({L578}).
4. `build` writes the head of the page, the title, the short version and the word list ({L581-670}).
5. `build` writes the sections 1 to 9 of the page: text, tables and the four figures ({L673-1150}).
6. `build` writes the reference list and closes the page ({L1153-1194}).
7. `build` collects the label overlaps of the four figures and returns them with the page text ({L1196-1197}).
8. The main part writes the page to the file, prints its size and every overlap, and ends with exit status 1 when there is an overlap ({L1202-1208}).

## Behavior a reader must know

- The script opens one file only, the page that it writes ({L1202}). It does not read the facts sheet and no result file. Every number of the page is a fixed value in the source.
- The header text names four groups of numbers that were computed again from raw files. That work was done outside this script. Its results stand in the source as fixed numbers. Only the midpoints of group 3 are computed at run time ({L274}).
- Group `LIF` ({L90-96}): for each mesh of a case, take the `T` rows of the file `CASE.m0.csv` or `CASE.m1.csv`. Divide the bytes of each row by its time. Take the mean of these rates. Divide by 64 bytes per cache line and multiply by the probe time in seconds, the column `median_ns` of the row `nop,0,` of `CASE.probe2.csv` or `CASE.probe66.csv`. A recomputation for this explanation page gives every `LIF` value and every probe time of the table `F4` [Ref10].
- Group `F5` ({L105-117}): for each file `GROUP.m0.csv` or `GROUP.m1.csv`, divide the bytes of each `T` row by its time. The sum of these rates is the mesh sum. The smallest and the largest are the per-thread range. A recomputation for this explanation page gives all values of the table `F5` [Ref20].
- Group `LOAD` ({L1101-1108}): the first value of the `/proc/loadavg` line in `env.txt` is the load at the start of a script. The first value after the word `load` in a `launch` line of `launches.txt` is the load at a launch. A recomputation for this explanation page over the 14 folders of 2026-11-15 gives the values that the page text holds: 0.00 to 71.24 at the start, 0.00 to 109.60 at the 101 launches, 1 runnable task and 0 logins at every launch [Ref17].
- The other numbers of the page are copies of the facts sheet, or rounded forms and outer ends of its ranges. The rows say where a line holds a number that is not in the facts sheet in this form.
- The page is written even when labels overlap. Only the exit status and the printed lines show the problem.
- The overlap check works with estimated text widths (0.58 times the font size per character). It can miss an overlap or report a false one.
- Figure 1 moves a mark sideways when it would cover another mark. The height of a mark is never changed, and the six labelled marks are never moved ({L260-282}).
- A total in the table of section 6 is the sum of the unrounded mesh sums. So it can differ by 0.1 GB/s from the sum of the two rounded values in the same row.
- The reference numbers of this explanation page are those of the report page for the same source: 1 for the facts sheet, 10 for the latency probe run, 17 for the files `env.txt` and `launches.txt`, 20 for the scrambled-order run.

## References

- [Ref1] `FINDINGS.md` in the folder `w120-2026-11-15`: the facts sheet of 2026-11-15.
- [Ref10] The result folder `w120-R4-20261115T200016Z` in the test folder `2026-11-15-whole-chip-read-drop`: the files `CASE.m0.csv` and `CASE.m1.csv` with the `T` rows (columns `bytes` and `elapsed_s`), and the files `CASE.probe2.csv` and `CASE.probe66.csv` with the row `nop,0,` (column `median_ns`).
- [Ref17] The files `env.txt` and `launches.txt` of the 14 result folders `w120-*` of 2026-11-15 in the test folder `2026-11-15-whole-chip-read-drop`.
- [Ref20] The result folder `w120-R7-20261115T205946Z` in the same test folder: the files `GROUP.m0.csv` and `GROUP.m1.csv` with the `T` rows, and the files `env.txt` and `launches.txt`.
