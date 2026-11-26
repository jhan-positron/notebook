# FACTS.md: how to read the facts sheet

## Short version

`FACTS.md` is the generated facts sheet (1118 lines, 33 tables) of the whole-chip read rerun of 2026-11-17: a memory read benchmark with 120 threads on CRB (an Arm reference server), run at a memory speed of 7200 MT/s (million transfers per second).
The script `build_facts.py` wrote every measured rate from the raw result files, and a new run of the script overwrites the file only when all 27 integrity checks pass.
The final old-against-new result stands in line 14 and in section 3.4: in part C, where one process times both kernels, the new read kernel (the newer version of the benchmark loop that reads memory) was 30.5 % to 31.2 % below the old read kernel when it ran directly after the old read kernel, and 29.7 % to 31.1 % below it when it ran directly after asmread (a hand-written loop with the same loads).

## What this file is

- **Explained file:** `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`.
- **Written by:** the function `main` of `build_facts.py`. It calls `render` of `facts_text.py`, writes the returned text to `FACTS.md.tmp`, and renames that file to `FACTS.md` [Ref1].
- **Which script writes which section:** `facts_text.py` writes the title lines and sections 0 to 3 and 7. `facts_text4.py` writes sections 4 to 6 [Ref2] [Ref6].
- **Step of the run:** analysis, after the benchmark runs. The scripts read the result files that were copied back from CRB.
- **No typed measured rates:** every measured rate is formatted from the collected data. So is every drop (how far the new rate lies below the old rate, in percent of the old rate). The text templates hold words, and they hold the fixed properties of the setup as the task and the run scripts give them: the CPU numbers of the two meshes, the loads per 256 B of each kernel, the two memory speeds, and the dates of earlier runs [Ref2]. Some templates also hold a typed count or a typed time difference. One example is the sentence "At every bwx12 launch 1 task was runnable". The script tests this count with `need(...)` before it writes the sentence. Another example is the text "ended 8 s before the first process of row A-2" in the file list of section 7 [Ref2].
- **Checked sentences:** for many sentences that depend on the pattern of the data, the script calls `need(...)` before it writes the sentence. This call stops the script when the data do not show the pattern that the sentence states [Ref2]. Not every typed value has a test of its exact value. For the typed text "ended 8 s before the first process of row A-2" the script tests only that the time difference is above 0 s and below 60 s [Ref2]. The script builds the whole text before it writes a file. So after such a stop neither `FACTS.md` nor `facts.json` is written [Ref1].
- **The first part of section 0 is built after sections 1 to 6:** the 3 result sentences and the 12 detail bullets quote numbers of section 4. The script builds them after sections 4 to 6 and inserts them under the heading of section 0. Only section 7 is written after that [Ref2].
- **Number format:** rates are shown to 0.01 GB/s and percent values to 0.1 %, both rounded half up. Two places have another format. The estimated values "120 x average" in the third table of section 4.3 (header in line 689) are shown to 0.1 GB/s. One percent value of section 4.2 (line 609) is shown to 0.01 % [Ref6]. GB = 1e9 bytes. A difference of two rates is computed before the rounding [Ref2].
- **Times:** all times are UTC. A time without a date is on 2026-11-17.
- **Folders:** `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`. `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`.
- **Data file of the sheet:** `S/facts.json` holds the same data as records. The companion `facts.json.md` explains it.
- **Size:** 1118 lines, 185615 bytes.
- **A new build stops since 2026-11-24:** line 20 of `S/go.sh` was edited on that day (the text of one message). Check 20 (line 232 of the sheet) compares the sha256 (a checksum) of 6 local files with the lists `S/local.sha` and `S/go2.sha`. The 6 files are go.sh, go2.sh, ra.sh and the three spec files. So check 20 fails for `go.sh` in a new build. `facts_text4.py` then stops the build before a file is written [Ref1] [Ref6]. A test of 2026-11-24 ran the build in a copy of the folder `S` [Ref10]. With the edited `go.sh` the build ended with status 1 and wrote no file. With the old line 20 put back the build passed. Its `FACTS.md` and its `facts.json` then equal the stored files after the folder path of the copy is replaced by the real path. The file list of the sheet names `S/go.sh` in line 962 and `S/local.sha` in line 968. `S/local.sha` holds the sha256 of the text that ran. It does not hold the sha256 of the present `go.sh`.

Reference numbers. The sheet has its own references, `[Ref1]` to `[Ref163]`, listed in its section 7. In this companion they appear only inside sample values. A reference in the running text of this companion, such as [Ref1], points to the list at the end of this companion.

How the sheet is made and used (top to bottom):

```
raw files under R (csv files, logs, env.txt, probe.txt)
  |
  v
build_facts.py: collect()      reads them through facts_data.py
build_facts.py: run_checks()   27 integrity checks
facts_text.py:  render()       title, sections 0 to 3 and 7
facts_text4.py: section4()     sections 4 to 6
  |
  +--> FACTS.md     (this sheet)
  +--> facts.json   (the same data as 793 interval records)
         |
         v
make_report.py reads both and writes whole-chip-rerun-7200.html
```

## Line kinds

| Kind of line | How to recognise it | Lines | What it holds |
|---|---|---|---|
| Heading | starts with `# `, `## ` or `### ` | 30 | 1 title, 8 section headings, 21 sub-section headings |
| Table header | starts with `\| ` and the next line starts with `\|---` | 33 | the column names of a table |
| Table separator | starts with `\|---` | 33 | no data |
| Table row | starts with `\| `, after a separator | 304 | one data row |
| Bullet | starts with `- ` (11 of them with 4 spaces before it) and is not a file-list line | 294 | one statement, one word of the word list, or one decision |
| File-list line | starts with `- [Ref` and a number | 163 | one raw file or script of section 7. 3 of the 163 lines name an external documentation page instead (lines 1095, 1096 and 1102) |
| Numbered line | starts with a number and `. ` | 62 | 27 integrity checks, 13 limits, 11 established results, 11 results that are not established |
| Paragraph | none of the other kinds | 42 | sentences that introduce a table or a list, the three result sentences (lines 14, 16, 18), the three verdict paragraphs (lines 432, 892, 894), the request of the user (line 93), the text that rule F1 point 5 requires (line 272), and the last line with the two output files |
| HTML tag | starts with `<` | 3 | start and end of the folded word list |
| Blank | empty | 154 | separator |

The 10 counts add up to 1118 lines.

## Section map

| Section | Lines | Title | What it holds |
|---|---|---|---|
| (head) | 1-10 | Facts sheet: whole-chip read test at 7200 MT/s, rerun of 2026-11-17 | Title and 8 bullets: who wrote the sheet, units, the folders R and S, the rounding rule. |
| 0 | 12-96 | Short version | The 3 result sentences (lines 14, 16, 18), 12 detail bullets (lines 22 to 33), the folded word list with 52 terms (lines 35 to 91), the request of the user (line 93), and the questions Q1 and Q2 (lines 95 and 96). |
| 1 | 98-273 | Run record | What ran, when, and in which machine state. |
| 1.1 | 100-125 | Steps and times | One table row per step (12 rows): the 10 steps of the rerun and the 2 steps of control I, with start, launch and end times. |
| 1.2 | 127-175 | Machine state and its proof | One table row per state line (24 rows): 18 state lines of the two run logs and 6 lines of the three files `probe.txt` (the file that the part A script writes for each session). Below it the proof of the boot, of the 12 memory modules and of 7200 MT/s. |
| 1.3 | 177-209 | System load at every launch | The 1-minute load average before each process: one table for the 3 sessions of part A, one for the 9 bwx12 launches. |
| 1.4 | 211-241 | Integrity checks | 27 numbered checks of the result files. All 27 say "pass" in the stored sheet. A sheet with a failed check is not written: `facts_text4.py` stops the build when one check failed [Ref6]. Checks 19, 20 and 26 (lines 231, 232 and 238) read `S/go.sh` as it was at the build. Check 20 fails in a new build since 2026-11-24 (see "What this file is"). |
| 1.5 | 243-273 | Limits: differences between the procedure of 2026-11-13 and part A | 13 numbered points: the differences that were found between the earlier test and its repeat. Point 12 holds four Linux settings that were compared without a difference. Point 13 holds the saved facts on the firmware settings. |
| 2 | 275-301 | Decisions made by the agent for this run | 18 decisions, (a) to (r). The first 8 were made before or during the run. The other 10 were made after the numbers were seen. |
| 3 | 303-434 | Q1: old against new at 7200 MT/s | The old read kernel against the new read kernel in the rerun. |
| 3.1 | 305-357 | Part A: bw_old and bw_new, whole-pass stop, 0.5 s, 3 intervals per process | One row per process (24 rows), then one row per old-new pair (6 rows). |
| 3.2 | 359-383 | Parts L and I: bwx12, common stop, 6 s, oldread then asmread | One row per process and round (12 rows): part L, control I and the earlier process F72d12. |
| 3.3 | 385-414 | Part C: bwx12, common stop, 6 s, oldread, read and asmread in one process | One row per process and round (8 rows), then one row per group of intervals (6 rows). |
| 3.4 | 416-434 | Verdict for Q1 | One row per kind of pair (9 rows) with the smallest and the largest drop, and the verdict paragraph (line 432). |
| 4 | 436-894 | Q2: 7200 MT/s against 8000 MT/s | The rerun against the earlier runs at 8000 MT/s. |
| 4.1 | 438-539 | The rules and the rows | The comparison rules in short. One table row per earlier run (22 rows). Two tables on hardware error records (messages that the firmware passes to Linux when hardware reports an error) during the earlier runs (12 and 8 rows). |
| 4.2 | 541-650 | Old read kernel | Three blocks: part A, part L, part C. Each block has a range table and a comparison table. The part L block also has a view of the pool L-1 to L-4 (the 7 bwx12 processes of these four 8000 MT/s rows) split by start state (2 rows). |
| 4.3 | 652-702 | New read kernel in part A (rule V3) | Three tables with 6 rows each: the load-only kernels of session 1 against the 8000 MT/s processes of the same round. |
| 4.4 | 704-740 | Load-only loop in part L (asmread, position 1, directly after oldread) | A range table (12 rows) and a comparison table (9 rows). |
| 4.5 | 742-800 | Load-only kernels in part C | Kernel `read`: a range table (16 rows). Kernel `asmread`: a range table (8 rows) and a comparison table (6 rows). |
| 4.6 | 802-836 | What the rows of the same boot show, and what follows for Q2 | One row per visit (3 rows): the same argument line at three times in the 7200 MT/s boot. Then the conclusions for Q2. |
| 4.7 | 838-878 | Sums per mesh (looked at after the numbers were seen, not part of the fixed rules) | Two tables (7 and 11 rows): the rate of each half of the chip. |
| 4.8 | 880-888 | Record only: read_nop96, read_nop256, read_1pl | One row per test loop (3 rows). The sheet makes no statement from it. |
| 4.9 | 890-894 | Verdict for Q2 | Two paragraphs: old read kernel (line 892) and new read kernel (line 894). |
| 5 | 896-910 | Record only: write, copy, asmwrite, asmcopy of part A | One row per kernel and binary (8 rows). The sheet makes no statement from it. |
| 6 | 912-948 | What is established, what is not, and hypotheses | 11 established results, 11 results that are not established, 5 hypotheses (H1 to H5). |
| 7 | 950-1118 | Files | 163 file-list lines: 160 lines name a file that the sheet uses (a raw file, a script or a written record), and 3 lines name an external documentation page. The last line names the two output files. |

## Columns

This part explains every table that holds final throughput numbers: what one row is, and what each column means. Each column table shows the values of one real row. The line number of that row is in the title of the value column.

Rules that hold for all these tables:

- A rate is in GB/s (1 GB = 1e9 bytes) and counts all 120 threads together. The exceptions say so in the column title: the columns "m0 + m1" and the mesh columns of section 4.7 count the threads of one mesh, and the thread columns of sections 3.1 and 4.3 hold the rate of one thread.
- A rate of part A is the column `aggregate_GBps` that the benchmark binary prints: the bytes of all threads divided by the longest per-thread time.
- A rate of the runner bwx12 (parts L, C and control I) is the sum over the 120 threads of bytes / elapsed time.
- These two formulas are different measures. For the same interval the part A formula gives a value equal to or lower than the bwx12 formula. The reason: it divides all bytes by the longest thread time. Every old-against-new pair of section 3 stays inside one formula. So does every range comparison of section 4 that `verdicts.q2_rows` of `facts.json` records (42 comparisons): part A against part A runs, bwx runners against bwx runners.
- A drop is (1 - new rate / old rate) x 100, in percent [Ref3].
- A column "Source" names a csv file by a reference of the sheet. In the tables of sections 3.1, 3.2 and 3.3 it also names the lines of that csv file.

### Section 3.1, first table (header in line 315, 24 rows)

One row is one process of part A: one start of `bw_old` or `bw_new` with one kernel, timed 3 times. The table lists the processes of the kernels `read` and `asmread` only. Each session and round has 4 of them [Ref4]. In round 1 the `bw_old read` process is the first process of the session, and the `bw_new read` process is launched directly after it. In round 2 these two are the last processes of the session, and `bw_new read` runs first. Column 5 shows the launch times. The field `kernel_before` of `facts.json` holds the process before each process.

| No. | Column | Unit | Meaning | Value in line 317 |
|---|---|---|---|---|
| 1 | Session | number | Session of go.sh, 1 to 3. | `1` |
| 2 | Start state of the session | text | What ran before the session started. | `started from an idle machine, 5 s after go.sh started (1-minute load average 0.07)` |
| 3 | Round | number | Round of the part A script, 1 or 2. Round 2 runs the processes in the reverse order. | `1` |
| 4 | Binary and kernel | text | Which binary and which kernel. The cell marks the old read kernel and the new read kernel in words. | `bw_old read (old read kernel)` |
| 5 | Launch | time, UTC | Launch time of the process. | `22:12:14` |
| 6 | Load at launch | load average | 1-minute load average of Linux directly before the launch. | `0.07` |
| 7 | Interval 1, GB/s (passes) | GB/s (count) | Rate of the first timed interval. In brackets the pass count: total bytes divided by the buffer size of one thread. | `467.83 (954)` |
| 8 | Interval 2 | GB/s (count) | The same for the second interval. | `467.92 (951)` |
| 9 | Interval 3 | GB/s (count) | The same for the third interval. | `465.38 (944)` |
| 10 | Median, GB/s | GB/s | Median of the three interval rates. | `467.83` |
| 11 | Slowest to fastest thread, GB/s | GB/s | Lowest `per_thread_min_GBps` and highest `per_thread_max_GBps` of the three csv rows. | `2.98 to 4.95` |
| 12 | Source | text | Reference of the sheet for the csv file, and the lines of the three interval rows. | `[Ref25], lines 4-6` |

The row of the new read kernel for the same session and round is line 318. Its three cells are `330.59 (664)`, `330.09 (664)` and `333.25 (664)`, and its median is `330.59`.

### Section 3.1, second table (header in line 344, 6 rows)

One row is one pair: the `bw_old read` process and the `bw_new read` process of the same session and round [Ref3] [Ref4].

| No. | Column | Unit | Meaning | Value in line 346 |
|---|---|---|---|---|
| 1 | Session | number | Session of go.sh. | `1` |
| 2 | Start state of the session | text | As in the first table. | `started from an idle machine, 5 s after go.sh started (1-minute load average 0.07)` |
| 3 | Round | number | Round of the part A script. | `1` |
| 4 | bw_old read, median GB/s | GB/s | Median of the 3 intervals of the old read kernel. | `467.83` |
| 5 | bw_new read, median GB/s | GB/s | Median of the 3 intervals of the new read kernel. | `330.59` |
| 6 | Ratio new/old | ratio | Column 5 divided by column 4. | `0.707` |
| 7 | New below old, % | % | (1 - ratio) x 100. This is the drop of part A. | `29.3` |
| 8 | Lowest to highest ratio of single intervals (lowest bw_new / highest bw_old to highest bw_new / lowest bw_old) | ratio | First value: the lowest `bw_new` interval divided by the highest `bw_old` interval. Second value: the highest `bw_new` interval divided by the lowest `bw_old` interval. | `0.705 to 0.716` |
| 9 | bw_old asmread / bw_old read | ratio | Median of the `bw_old asmread` process divided by column 4. | `0.689` |
| 10 | bw_new asmread / bw_old read | ratio | Median of the `bw_new asmread` process divided by column 4. | `0.688` |

### Section 3.2 (header in line 365, 12 rows)

One row is one round of one bwx12 process that ran the argument line of part L. 6 rows are part L, 4 rows are control I, and 2 rows are the earlier process F72d12. Each round times `oldread` first and `asmread` directly after it [Ref4]. The three test loops `read_nop96`, `read_nop256` and `read_1pl` follow in the same round. Section 4.8 holds their rates. So in a row of round 1, `oldread` was timed directly after `read_1pl` of round 0. The field `kernel_before` of `facts.json` holds this for every interval.

| No. | Column | Unit | Meaning | Value in line 367 |
|---|---|---|---|---|
| 1 | Folder tag or row | text | Tag of the result folder, or `F72d12`. | `T72L1` |
| 2 | What | text | Which part the process belongs to. | `part L, session 1. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B)` |
| 3 | Round | number | Round of the kernel sequence inside the process, 0 or 1. | `0` |
| 4 | Load at launch | load average | 1-minute load average directly before the launch of the process. | `74.05` |
| 5 | oldread, GB/s | GB/s | Rate of the old read kernel in this round. | `462.30` |
| 6 | oldread m0 + m1 | GB/s + GB/s | The same rate in two parts: the threads on mesh 0 (CPUs 0-63) plus the threads on mesh 1 (CPUs 64-119). | `305.13 + 157.17` |
| 7 | asmread, GB/s | GB/s | Rate of asmread in this round. | `321.76` |
| 8 | asmread m0 + m1 | GB/s + GB/s | The same rate in two parts. | `178.60 + 143.16` |
| 9 | asmread below oldread, % | % | (1 - column 7 / column 5) x 100, inside the same process and round. | `30.4` |
| 10 | Source | text | Reference of the sheet for the csv file, and the lines of the two I rows (the summary rows of the two intervals). | `[Ref31], I rows in lines 128 and 490` |

### Section 3.3, first table (header in line 392, 8 rows)

One row is one round of one part C process. 4 processes ran, with 2 rounds each. Every round times all three kernels in one process [Ref4].

| No. | Column | Unit | Meaning | Value in line 394 |
|---|---|---|---|---|
| 1 | Folder tag | text | Tag of the result folder, `T72C1` to `T72C4`. | `T72C1` |
| 2 | Order | text | `cfwd` = sequence oldread, read, asmread. `crev` = sequence asmread, read, oldread. | `cfwd` |
| 3 | Round | number | Round of the sequence, 0 or 1. | `0` |
| 4 | Load at launch | load average | 1-minute load average directly before the launch. | `94.97` |
| 5 | oldread, GB/s | GB/s | Rate of the old read kernel. In brackets its position in the sequence and the kernel that ran directly before. | `466.01 (position 0, after nothing: first interval)` |
| 6 | oldread m0 + m1 | GB/s + GB/s | The same rate in two parts: mesh 0 plus mesh 1. | `308.39 + 157.63` |
| 7 | read, GB/s | GB/s | Rate of the new read kernel, with position and kernel before. | `320.90 (position 1, after oldread)` |
| 8 | read m0 + m1 | GB/s + GB/s | The same rate in two parts. | `178.20 + 142.70` |
| 9 | asmread, GB/s | GB/s | Rate of asmread, with position and kernel before. | `320.86 (position 2, after read)` |
| 10 | asmread m0 + m1 | GB/s + GB/s | The same rate in two parts. | `177.73 + 143.13` |
| 11 | read below oldread, % | % | (1 - column 7 / column 5) x 100. This is the drop of the new read kernel. | `31.1` |
| 12 | asmread below oldread, % | % | (1 - column 9 / column 5) x 100. | `31.1` |
| 13 | Source | text | Reference of the sheet for the csv file, and the lines of the I rows of oldread, read and asmread, in this order. | `[Ref43], I rows in lines 128, 490, 852` |

### Section 3.3, second table (header in line 405, 6 rows)

One row is one group of part C intervals: one kernel, and the kernel that ran directly before it (or none, for the first interval of a process). The last row holds all oldread intervals [Ref4].

| No. | Column | Unit | Meaning | Value in line 407 |
|---|---|---|---|---|
| 1 | Group | text | Kernel and the kernel directly before it. | `read after oldread` |
| 2 | Where | text | The order and the rounds in which this case occurs. In the oldread row: the order and the position. | `cfwd, rounds 0 and 1` |
| 3 | Folder tags | text | The processes that hold the intervals. | `T72C1, T72C3` |
| 4 | n | counts | Number of intervals and number of processes. | `4 intervals / 2 processes` |
| 5 | Min to max, GB/s | GB/s | Lowest and highest interval rate of the group. | `320.89 to 324.98` |
| 6 | Below oldread of the same process and round, % | % | Smallest and largest drop of the group. `-` in the oldread row. | `30.5 to 31.2` |

### Section 3.4 (header in line 418, 9 rows)

One row is one kind of pair: a new or load-only interval against the oldread interval that it is compared with. In the row of part A a pair is two processes: the medians of their 3 intervals are compared. This table holds the final old-against-new numbers [Ref4].

| No. | Column | Unit | Meaning | Value in line 420 |
|---|---|---|---|---|
| 1 | Part | text | `C`, `L`, `A`, the control I, or F72d12. | `C` |
| 2 | Pair | text | Which two intervals form a pair. In the row of part A: which two processes. | bwx12 `read` (new read kernel) directly after `oldread` (cfwd), against `oldread` of the same process and round |
| 3 | Smallest drop, % | % | Smallest drop over the pairs of the row. | `30.5` |
| 4 | Largest drop, % | % | Largest drop over the pairs of the row. | `31.2` |
| 5 | n | counts | Number of pairs, intervals per kernel, processes, sessions and boots. | `4 pairs: 4 intervals per kernel / 2 processes (T72C1, T72C3) / sessions 1 and 3 / 1 boot` |

### Section 4: the range table (7 columns, 6 places)

The same table form stands at the header lines 545, 566 and 623 (section 4.2), 709 (section 4.4), 750 and 776 (section 4.5).

One row is one set of intervals of one kernel: a part of the rerun, control I, one earlier run, or a pool (several earlier runs taken together) [Ref5].

| No. | Column | Unit | Meaning | Value in line 547 |
|---|---|---|---|---|
| 1 | Row | text | Label of the set. | `part A, sessions 1 to 3` |
| 2 | What it is | text | Kind of the set: rerun, baseline, supporting row, row of another binary. | `rerun (one row per process is in section 3.1)` |
| 3 | Memory speed, modules | MT/s, count | Memory speed and number of memory modules of the boot. | `7200 MT/s, 12 modules` |
| 4 | n | counts | Number of intervals and number of processes in the set. | `18 intervals / 6 processes` |
| 5 | Min to max, GB/s | GB/s | Lowest and highest interval rate of the set. This is the range of the set. | `459.90 to 474.15` |
| 6 | Median, GB/s | GB/s | Median of the interval rates. | `467.54` |
| 7 | Source | text | References of the sheet for the csv files. | `[Ref25] [Ref27] [Ref29]` |

### Section 4: the comparison table (8 columns, 5 places)

The same table form stands at the header lines 553, 581 and 636 (section 4.2), 724 (section 4.4) and 787 (section 4.5).

One row is one comparison of a 7200 MT/s range with an 8000 MT/s range (rule V1 point 2 of the rules file) [Ref5].

| No. | Column | Unit | Meaning | Value in line 558 | Value in line 583 |
|---|---|---|---|---|---|
| 1 | 7200 MT/s row | text | Label of the 7200 MT/s set. | `part A, sessions 1 to 3` | `part L` |
| 2 | Its range, GB/s | GB/s | Lowest and highest interval rate of that set. | `459.90 to 474.15` | `461.61 to 464.29` |
| 3 | 8000 MT/s range used | text | Label of the 8000 MT/s set. | `pool A-1 to A-3` | `L-1 alone` |
| 4 | That range, GB/s | GB/s | Lowest and highest interval rate of that set. | `463.58 to 469.03` | `467.35 to 468.06` |
| 5 | Overlap | yes or no | `yes` when the two ranges share at least one value. | `yes` | `no` |
| 6 | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | GB/s | `0` when the ranges overlap. With `+`: lowest 7200 MT/s value minus highest 8000 MT/s value. With `-`: highest 7200 MT/s value minus lowest 8000 MT/s value. | `0` | `-3.06` |
| 7 | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | % | (highest - lowest) / lowest x 100 of the 8000 MT/s range. When the ranges overlap, the test cannot exclude a difference of this size. | `1.2` | `0.2` |
| 8 | Wording by rule V1 point 2 | text | The result text, only in the row that decides: "no difference seen" when the ranges overlap, "differs between the 8000 MT/s boot and the 7200 MT/s boot" when not. `-` in every other row. | `"no difference seen"` | `-` |

### Section 4.1, rows of earlier runs (header in line 454, 22 rows)

One row is one earlier run that section 4 uses. The row names of this table (A-1, L-1, B7a and so on) are the labels in all later tables [Ref6].

| No. | Column | Unit | Meaning | Value in line 459 |
|---|---|---|---|---|
| 1 | Row | text | Label of the earlier run. It is the value of the field `dataset` in `facts.json`. | `L-1` |
| 2 | What it is | text | Role of the run in the comparison. | `baseline: identical argument line` |
| 3 | Folder and files | path | Result folder and csv files. | `R/w120-R8-20261117T020549Z: a6456.csv` |
| 4 | Binary (sha256, first 8 characters) | text | Binary and the start of its checksum. | `bwx12 (cd58e564)` |
| 5 | Stop rule, interval length | text, s | How a timed interval ends, and the length setting of the interval. With the whole-pass stop rule the timed length of a thread is at least this value. | `common stop, 6 s` |
| 6 | Memory speed, modules, boot | MT/s, count, text | Machine state of the run. | `8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)` |
| 7 | Load at launch (lowest to highest process) | load average | 1-minute load average at the launch of the processes of the run. | `0.00` |
| 8 | Interval records in facts.json / processes | counts | How many records of `facts.json` belong to the run, and from how many processes. | `10 / 1` |
| 9 | Source | text | References of the sheet for the rates, the load and the checksum. | `rates [Ref73], load [Ref75], sha256 [Ref74]` |

### Section 4.3, first table (header in line 658, 6 rows)

One row is one load-only kernel of part A in one round: `bw_new read` (the new read kernel), `bw_new asmread` or `bw_old asmread`. The row compares session 1 of the rerun with the 8000 MT/s processes of the same round (rule V3) [Ref6].

| No. | Column | Unit | Meaning | Value in line 660 |
|---|---|---|---|---|
| 1 | Binary and kernel | text | Which binary and kernel. | `bw_new read` |
| 2 | Round | number | Round of the part A script. | `1` |
| 3 | 7200 MT/s, session 1 | GB/s (count) | The three interval rates of session 1, each with its pass count in brackets. | `330.59 (664), 330.09 (664), 333.25 (664)` |
| 4 | 8000 MT/s, A-1, same round | GB/s (count) | The same for the earlier run A-1. | `285.06 (600), 279.66 (600), 280.27 (600)` |
| 5 | 8000 MT/s, A-2, same round | GB/s (count) | The same for the earlier run A-2. | `288.94 (600), 293.39 (600), 297.34 (600)` |
| 6 | 8000 MT/s range of the round, GB/s | GB/s | Lowest and highest of the intervals of columns 4 and 5. | `279.66 to 297.34` |
| 7 | Wording by rule V3 | text | Whether the three intervals of session 1 lie inside or outside that range. | `outside (above)` |
| 8 | Distance to the nearer end of the range, GB/s | GB/s | For intervals above the range: interval rate minus the upper end. Smallest and largest of the three. | `32.75 to 35.91` |

The sheet gives no percent in this table (rules V3 and V1 point 3). It also states that part A cannot give the size of a change. The pass counts differ between the two speeds (664 against 600 in this row), and with the whole-pass stop rule the rate moves together with the pass count.

### Section 4.6, the three visits (header in line 806, 3 rows)

One row is one visit: one time at which the argument line of part L ran in the 7200 MT/s boot [Ref6].

| No. | Column | Unit | Meaning | Value in line 809 |
|---|---|---|---|---|
| 1 | Visit | text | F72d12, part L, or control I. | `part L` |
| 2 | Launch times | time, UTC | Launch of the first and of the last process of the visit. | `22:13:34 to 22:19:52` |
| 3 | Start state | text | What ran before, and the load at launch. | `5 s after part A (load 74.05 to 104.52)` |
| 4 | Time since the first kernel log line of the boot | h, min, s | Launch time minus the time of the first line of the Linux kernel log of the boot. | `2 h 11 min 18 s to 2 h 17 min 36 s` |
| 5 | asmread, GB/s | GB/s | Lowest and highest rate of asmread at position 1. | `321.65 to 327.93` |
| 6 | oldread, GB/s | GB/s | Lowest and highest rate of oldread at position 0. | `461.61 to 464.29` |
| 7 | n per kernel | counts | Number of intervals and processes per kernel. | `6 intervals / 3 processes` |

### The other tables with rates

| Header line | Section | One row is | Cells hold |
|---|---|---|---|
| 521 | 4.1 | one interval of an earlier bwx12 or bwx11 run to which hardware error records can be assigned (8 intervals, all kernels and positions) | the rate in GB/s, the rate of the same kernel at the same position in the other round of the process, and the difference. The sheet says that this view was added after the numbers were seen and is not part of the fixed rules |
| 602 | 4.2 | one group of bwx12 processes of the pool L-1 to L-4 (8000 MT/s) with the same kind of start state | lowest and highest rate of oldread and of asmread, in GB/s |
| 674 | 4.3 | one load-only kernel of part A in one round, only the intervals with 663 or 664 passes | the ranges at both speeds in GB/s, with the number of intervals, and their distance |
| 689 | 4.3 | one load-only kernel of part A in one round | the average rate per thread in GB/s, 120 x that average as an estimate of the sum, and the distance of the nearest ends by two methods |
| 847 | 4.7 | one set of oldread intervals | lowest and highest sum of the thread rates on mesh 0 and on mesh 1, in GB/s |
| 859 | 4.7 | one set of intervals of a load-only kernel. The last row holds the kernels `read` and `asmread` of the runner bwx together | the same two sums |
| 884 | 4.8 | one test loop of bwx12 (`read_nop96`, `read_nop256`, `read_1pl`) | lowest and highest rate in GB/s per run, with the number of intervals |
| 901 | 5 | one kernel of part A (`write`, `copy`, `asmwrite`, `asmcopy`) in one binary | number of intervals, then lowest / median / highest rate in GB/s |

The table with the header line 494 (section 4.1) holds hardware error records and no rates. The tables of sections 1.1 to 1.3 hold times, machine state and load.

## Old read kernel and new read kernel in this file

Both kernels were measured in the same run. So the sheet has no separate part for "old kernel testing" and "new kernel testing". The reader finds each kernel by its name in a row or a column.

| Kernel | Name in part A | Name in the bwx12 parts (L, C, control I) |
|---|---|---|
| Old read kernel | `bw_old read` | `oldread` |
| New read kernel | `bw_new read` | `read` (timed in part C only) |
| asmread, the hand-written loop with the same loads | `bw_old asmread`, `bw_new asmread` | `asmread` (used in place of the new read kernel in part L and control I) |

Where the rows and columns of each kernel are:

| Place | Old read kernel | New read kernel |
|---|---|---|
| Section 3.1, first table | the 6 rows with `bw_old read (old read kernel)` in column 4 | the 6 rows with `bw_new read (new read kernel)` in column 4 |
| Section 3.1, second table | column 4 | column 5. The drop is column 7 |
| Section 3.2 | column 5 (`oldread`) | none. Column 7 holds asmread in its place. The drop is column 9 |
| Section 3.3, first table | column 5 (`oldread`) | column 7 (`read`). The drop is column 11 |
| Section 3.4 | the old read kernel is the base of every drop | rows 1 and 2 (lines 420 and 421) for bwx12 `read`, row 7 (line 426) for `bw_new read` |
| Section 4 | section 4.2 | section 4.3 (part A), section 4.5 (kernel `read` of part C). Section 4.4 holds asmread of part L |

## Where the final old-against-new result is

1. **Line 14**, the first sentence of section 0. It gives the result in one sentence.
2. **Section 3.4**, the table in lines 418 to 428 and the verdict paragraph in line 432. The table is copied here without its last column:

| Line | Part | Pair | Smallest drop, % | Largest drop, % |
|---|---|---|---|---|
| 420 | C | bwx12 `read` (new read kernel) directly after `oldread` (cfwd), against `oldread` of the same process and round | 30.5 | 31.2 |
| 421 | C | bwx12 `read` (new read kernel) directly after `asmread` (crev), against `oldread` of the same process and round | 29.7 | 31.1 |
| 422 | C | bwx12 `asmread` directly after `read` (cfwd), against `oldread` of the same process and round | 30.8 | 31.2 |
| 423 | C | bwx12 `asmread` as first interval of the process (crev, round 0), against `oldread` of the same process and round | 30.1 | 31.7 |
| 424 | C | bwx12 `asmread` directly after `oldread` (crev, round 1), against `oldread` of the same process and round | 29.7 | 30.6 |
| 425 | L | bwx12 `asmread` (used in place of the new read kernel) against `oldread`, same process and round | 29.2 | 30.5 |
| 426 | A | bw_new `read` against bw_old `read`, medians of 3 intervals, same session and round | 28.5 | 31.8 |
| 427 | I (control, added after the first numbers were seen) | bwx12 `asmread` against `oldread`, same process and round | 31.9 | 32.8 |
| 428 | F72d12 (earlier visit, not part of the rerun) | bwx12 `asmread` against `oldread`, same process and round | 35.4 | 35.4 |

3. **The single measurements of each row:** section 3.3 for part C (8 rows, one per process and round), section 3.2 for part L, control I and F72d12 (12 rows), section 3.1 for part A (24 rows and 6 pairs).
4. **The same result as data:** `verdicts.q1` and `verdicts.q1_parts` of `S/facts.json`. Line 432 is the words "**Verdict.**" followed by the text of `verdicts.q1`. The 9 records of `verdicts.q1_parts` are the 9 rows of the table.
5. **The result against 8000 MT/s (Q2):** lines 16 and 18 of section 0, and the two paragraphs of section 4.9 (lines 892 and 894).

How to read one row of part C: the old and the new read kernel run in the same process, one directly after the other, for 6 s each. Line 394 shows 466.01 GB/s for oldread and 320.90 GB/s for read. The drop is 31.1 %.

What "directly after" means: the next timed interval of the same process. The time between two intervals is not timed. In the csv file of the row of line 394 the thread rows of oldread end at 6.414 s after the process start, and the thread rows of read start at 6.523 s. So 0.109 s lie between the two timed intervals. In this time the main thread of bwx12 prints the rows of the first interval and reads the page state of the buffers (how many kB of each buffer lie on 2 MiB pages). Then each thread runs one warm-up pass of the next kernel over its buffer [Ref9].

Limits that the sheet states for this result:

- All values come from 1 boot at 7200 MT/s.
- The percent values of part A are less exact than those of parts L and C. With the whole-pass stop rule the pass count moves in steps, and the rate moves with it.
- Part C has one row per group. The sheet gives no range over all read intervals of part C.
- Part C, order of the kernels: the reverse order (crev) comes from 2 processes, T72C2 in session 2 and T72C4 after session 3. With 2 processes per order, the effect of the order and the effect of the session are not fully separated.

## Which code reads this file

| Script | What it reads | What it does with it |
|---|---|---|
| `make_report.py` (the generator of the report page `whole-chip-rerun-7200.html`) | the whole text | It accepts the text only when it holds the heading "## 7. Files" and the words "Output files of this sheet". If not, it waits 1.5 s and reads the file again. After 10 failed reads it stops. So it does not use a file that is only partly written. It splits the text into sections by the number in each heading [Ref7]. |
| the same | tables of sections 3.1 to 3.4 and 4.2 to 4.5 | It finds a table row by the texts of its cells and a cell by the text of its column title. It compares the value of each cell that it reads with the value that it computed itself. It computes a part A value from the records of `facts.json`. For a rate of a bwx runner it sums the thread rows (T rows) of the csv file that the record names. It reads only a part of the cells. In section 3.4 it reads the two drops of 6 of the 9 rows. In section 3.1 it reads only the second table. It does not read the first table of section 3.3 (one row per process and round of part C). It also searches the text of sections 0, 1.5, 3.4, 4.2, 4.5, 4.6 and 4.9 for some of its computed values. On a mismatch it does not write the report page [Ref7]. |
| the same | the word list (lines 35 to 91) | It reuses definitions of the list in the report page [Ref7]. |

- `test_make_report.py` runs copies of `make_report.py`. These copies read the same `FACTS.md`.
- No other script at the top level of the folder `S` reads `FACTS.md`. `build_facts.py` only writes it.
- The subfolders `final-check`, `review-scratch`, `verify-r3fix` and `verify-vfix-r3` of `S` hold check scripts of earlier reviews. Some of them read `FACTS.md`, for example `final-check/facts/refs.py` and `verify-vfix-r3/check_text.py`. `build_facts.py`, `make_report.py` and `test_make_report.py` do not call them.
- The column titles are keys for `make_report.py`. Examples: "Smallest drop", "Min to max, GB/s", "New below old, %". After a change of such a title in `facts_text.py` or `facts_text4.py`, `make_report.py` no longer finds the row or the cell, and it stops.
- `make_report.py` tests that the sections 0, 3.1, 3.2, 3.3, 3.4, 4.2, 4.3, 4.4, 4.5, 4.6 and 4.9 exist. It stops when one of them is missing [Ref7].
- It also uses two sections that this test does not name. It searches the text of section 1.5 for one computed range. It tests that section 2 lists the decisions (k) and (r) under the decisions made after the numbers were seen, and it stops when they are not there [Ref7].

How a final rate reaches a cell of the sheet:

1. The benchmark writes one csv row per interval (part A) or one row per thread and interval (bwx12).
2. `facts_data.py` reads the rows. For part A it takes the printed `aggregate_GBps`. For bwx12 it sums bytes / elapsed time over the 120 thread rows.
3. `build_facts.py` makes one record per interval.
4. `facts_text.py` and `facts_text4.py` select records, take the lowest value, the highest value, the median or a drop, and round the result to 0.01 GB/s or 0.1 %.

<details>
<summary>Words used here</summary>

The sheet has its own word list with 52 terms (lines 35 to 91). The entries of the first list below are copied from it word for word [Ref8]. One entry has a change: the entry "Read kernel" says "On this page" where the sheet says "In this sheet".

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Idle start**: a launch at a 1-minute load average below 1.0.
- **Visit**: one time at which the same line was run. A later visit is the same line run again at a later time.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **Baseline, like-for-like**: an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.
- **Supporting row, other-binary row**: earlier 8000 MT/s runs that differ in interval length or counter setup (supporting), or that used another runner binary (other binary).
- **Ranges overlap**: two min-to-max ranges share at least one value.
- **n**: the number of measurements that a range comes from. It is written as intervals / processes / sessions / boots (rule V1 point 1). "No session" marks a row that is not part of a session of go.sh.
- **Pool**: the intervals of several rows taken together as one range.
- **Distance of the nearest ends**: for two ranges that do not overlap: the lowest value of the higher range minus the highest value of the lower range.
- **Rules V1 to V4, F1, F2**: the comparison rules in `baselines-and-rules.txt`.
- **est.**: estimated, not measured directly.

Added for this companion. The entries "Pass count" and "Load average" are short forms of the entries of the sheet:

- **Rerun**: the whole-chip read test that go.sh ran on CRB on 2026-11-17 (parts A, L and C), after the memory speed was lowered from 8000 MT/s to 7200 MT/s. Control I followed it on the same day.
- **Facts sheet, the sheet**: the file `FACTS.md`.
- **go.sh, go2.sh**: the driver script of the rerun, and the script of control I.
- **Q1, Q2**: the two questions of the sheet. Q1: is the new read kernel still below the old read kernel at 7200 MT/s, and by how much. Q2: did either kernel's rate differ from the earlier runs at 8000 MT/s.
- **Drop**: how far the new rate lies below the old rate, in percent of the old rate.
- **Pair**: one interval of a new or load-only kernel together with the oldread interval that it is compared with. In part A a pair is the `bw_new read` process and the `bw_old read` process of the same session and round.
- **Pass count**: total bytes of an interval divided by the buffer size of one thread. For a read kernel it is the number of buffer passes that all threads completed.
- **F72d12**: one bwx12 process with the argument line of part L. It ran at 20:02 UTC in the boot of the rerun, 2 h 9 min before go.sh started.
- **cfwd, crev**: the two kernel orders of part C, named after their spec files `cfwd.spec` and `crev.spec`.
- **m0 + m1**: the rate of the threads on mesh 0 plus the rate of the threads on mesh 1.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes.
- **DIMM report**: the file `/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md`. It holds the boot history of CRB with the module count of each boot.
- **Step**: one start of a run script by go.sh or go2.sh. It has one result folder with a tag such as `T72A1`.

</details>

## References

- [Ref1] `S/build_facts.py`, lines 1033 to 1052: function `main` (order of the steps: the text is built in line 1037, before `facts.json` is written in line 1038 and `FACTS.md.tmp` is written and renamed in lines 1039 to 1041).
- [Ref2] `S/facts_text.py`, lines 1 to 8 (what the script does, and its statement that the templates hold words only), lines 255 to 256 (the typed text "ended 8 s before the first process of row A-2" of the file list), lines 886 to 887 (the `need` test of the count and the sentence "At every bwx12 launch 1 task was runnable"), lines 1011 to 1016 (the `need` test of the time difference before row A-2: above 0 s and below 60 s), lines 36 to 38 (`need`), lines 41 to 55 (rounding half up to 0.01 and 0.1), lines 132 to 137 (`table`), lines 442 to 456 (title lines), lines 472 to 475 and 1467 (the result sentences and the detail bullets of section 0, built after sections 4 to 6 and inserted), lines 565 to 566 (start of the word list of section 0, written in its place), lines 1470 to 1483 (section 7).
- [Ref3] `S/facts_text.py`, lines 283 to 301 (pairs of part A: medians, ratio, drop) and lines 304 to 321 (pairs of bwx12 inside the same process and round, drop).
- [Ref4] `S/facts_text.py`, lines 1250 to 1304 (section 3.1), lines 1307 to 1351 (section 3.2), lines 1354 to 1394 (section 3.3), lines 1397 to 1455 (section 3.4).
- [Ref5] `S/facts_text4.py`, lines 48 to 55 (`ranges`: the range table) and lines 71 to 90 (`cmps`: the comparison table). `S/facts_text.py`, lines 333 to 336 (`compare`). `S/facts_data.py`, lines 461 to 485 (`rng`, `overlap`, `gap`, `width_pct`).
- [Ref6] `S/facts_text4.py`, lines 1 to 5 (sections 4, 5 and 6), lines 164 to 190 (rows of earlier runs), line 627 (the percent value with 2 decimals in section 4.2), lines 721 to 747 (first table of section 4.3), lines 832 to 833 (the values "120 x average" with 1 decimal), lines 1054 to 1069 (the three visits), lines 1220 to 1246 (sums per mesh), lines 1286 to 1298 (section 4.8), lines 1436 to 1453 (section 5), line 1461 (the build stops when an integrity check failed).
- [Ref7] `S/make_report.py`, lines 176 to 189 (function `val`: the rate of a record), lines 230 to 235 (read of the sheet), lines 556 to 588 (sections, tables, the sections that must exist), lines 591 to 607 (a row by its cells, a cell by its column title), lines 64 to 77 (the repeated read), lines 646 to 681 (comparison of the values of sections 3.1 to 3.4), lines 683 to 742 (comparison of the values of sections 4.2 to 4.5, and the search in the text of sections 4.6 and 4.9), lines 744 to 765, 1378 and 2062 (more searches in the text: sections 3.4, 0, 4.5, 4.6, 1.5 and 4.2), lines 1346 to 1348 (the test of the decisions (k) and (r) of section 2), lines 2279 to 2289 (word list).
- [Ref8] `S/FACTS.md`, lines 35 to 91: the word list of the sheet.
- [Ref9] `R/w120-T72C1-20261117T221436Z/cfwd.csv`, lines 129 to 248 and 491 to 610: the thread rows (T rows) of the first two intervals with the columns `t_start_s` and `t_end_s`. `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`, line 1669 (warm-up pass before each timed interval), lines 1688 to 1701 (clock reads at the start and at the end of a timed interval), lines 3077 to 3114 (the main thread prints the rows of an interval and then reads the page state, while the threads wait). The local `bwx12.c` has the sha256 `e3d4442b...`. The build record `crb-build-1/build.txt` of the same folder holds this value (line 17) beside the sha256 of the binary `bwx12` (`cd58e564...`, line 20).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24/check_facts_build.py` and its output `check_facts_build.out` in the same folder: the test of 2026-11-24 that ran `build_facts.py` in a copy of `S`. With the edited `go.sh` the build ended with status 1 and wrote no file. With the old line 20 put back it ended with status 0 and printed `checks: 27, failed: 0`.
