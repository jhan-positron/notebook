# Results of the reviews (line-by-line pages, 2026-11-25)

Kinds of defect (REVIEW.md, section 2): 1 false, 2 not grounded, 3 missing, 4 wrong pointer, 5 not understandable, 6 plain English.

| Review | Keys | Kind of review | Rows checked | Rows corrected | By kind |
|---|---|---|---:|---:|---|
| R1 | `kernels-2026-11-13`: bandwidth.orig.c, bandwidth.c, selftest.c, probe.c | full | 1206 | 14 | kind 1: 4 rows (2 of them the equal barrier row in both files), kind 3: 3, kind 5: 1, kind 6: 4 (+2 equal rows) |
| R3b | `bwx12-2026-11-15/bwx12.c` lines 1562 to 3126 | full | 1486 | 16 | kind 1: 10 (7 of them one wording, "every 8-byte word of the buffer"), kind 3: 2, kind 4: 1, kind 6: 3 |
| R2 | go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, manual-run/run.sh, 3 spec files, local.sha, go2.sha, stat_k120.py, stat_bwx.py, test_make_report.py | full | 622 | 17 | kind 1: 9 (5 of them one sentence on `HWDIR`), kind 3: 4, kind 5: 4. Plus 3 lines added to the page file of run.sh |
| R5 | `hwwatch-2026-11-24`: hw.sh, hwwatch.py, clock_from_counts.py, test_hwwatch.py (rows and 4 page files) | full | 1569 | 22 | kind 1: 10, kind 2: 3, kind 3: 8 (one row has kinds 1 and 3), kind 6: 2. Plus 1 part title and 17 lines of the page files |
| SR1 | `w120-7200-2026-11-17/facts_text.py` (300 of 1411 rows, seed 11), `facts_text4.py` (300 of 1585 rows, seed 12) | sample | 600 (and 125 more rows read) | 0 | none |
| SR2 | `w120-7200-2026-11-17/facts_data.py` (100 of 414 rows, seed 22), `build_facts.py` (200 of 1000, seed 21), `make_report.py` lines 1 to 1483 (300 of 1280, seed 23) | sample | 600 (and about 1260 more rows read) | 3 | kind 1: 2 (both in facts_data.py), kind 3: 1 (make_report.py) |
| SR3 | `w120-7200-2026-11-17/make_report.py` lines 1484 to 2834 (300 of 1222 rows, seed 24) | sample | 300 (all 1222 rows read once, less deep) | 2 (and 1 outside the sample) | kind 1: 3 |
| R3a | `bwx12-2026-11-15/bwx12.c` lines 1 to 1561 | full | 1508 | 28 | kind 1: 19 (8 of them the wording "whole buffer" for the first touch or the warm-up pass), kind 3: 2, kind 5: 3, kind 6: 4 |
| SR4 | `bench`: 13 keys (Makefile, latency.c, homelat.c, 5 run scripts, 5 Python files) and their 13 page files | sample | 592 of 2299 (all other rows read once, less strict) | 3 (and 5 outside the sample) | kind 1: 2, kind 3: 1. Outside the sample: kind 1: 3, kind 3: 2. Page files: 12 defects in 7 files |
| SR5 | `w120-2026-11-15`: 38 keys (5 run scripts, 14 spec files, 5 event lists, 8 analysis scripts, 6 robsize files) and their 38 page files | sample | 566 (the other rows read once) | 7 (and 2 outside the sample) | kind 1: 5 (3 of them one wording on `${WIN:-N}`), kind 6: 2. Outside the sample: kind 1: 1, kind 6: 1. Page files: 8 lines in 7 files, and the glossary wording of "GB, MiB" in 23 files |
| SR7 | `bwx11-2026-11-15`: test_runner11.py, test_schedule11.py, schedule11.py, schedule_zs.py, run_bwx11.sh, visit11.sh. `bwx10-2026-11-15/hostwatch.py`. `cread-2026-11-12`: cread.c, run_cread.sh, remote.sh, make_html.round2.py. And the 11 page files | sample | 686 (6 of the files read in full) | 8 (and 3 outside the sample) | kind 1: 7, kind 2: 1. Outside the sample: kind 1: 3. Page files: 7 places in 4 files |
| SR6 | `w120-2026-11-15/report_w120.py` (150 of 1135 rows), `robsize/robsize.c` (150 of 760), 13 keys of `asct-2026-11-16` (217 rows: 5 scripts, 5 input files, 3 Python files), and the 15 page files | sample | 517 | 8 (and 5 outside the sample) | kind 3: 7 (all in the five input files: the row did not say how the reading script uses a field), kind 6: 1. Outside the sample: kind 1: 2, kind 3: 1, kind 6: 2. Page files: 2 defects |
| R4 | `bwx12-2026-11-15`: build12.sh, bwx12_selftest.c, check_listing12.py, test_kernels12.py | full | 1445 | 11 | kind 1: 3, kind 3: 5, kind 5: 3 |
| SR8 | `new-test-kernel/partBC-analysis`: make_q1_html.py, test_q1.py, make_q2_html.py, test_q2.py, recount_results_md.py, render_q1.sh, gen_s1.sh, and the 7 page files | sample | 561 (about 850 more rows of the two page builders read once) | 8 (and 2 outside the sample) | kind 1: 8 (none on a formula, a column or a decision rule). Outside the sample: kind 1: 2. Page files: 24 lines in 6 files |
| SR9 | `asct-2026-11-16`: analyze.py, facts.py, svgchart.py, figs.py, report.py, dyn_notes.py, and the 6 page files | sample | 480 (the other 1441 rows read once) | 9 (and 5 outside the sample) | kind 1: 4, kind 2: 1, kind 3: 3, kind 5: 1. Outside the sample: kind 1: 2, kind 3: 3. Page files: 21 defects in 6 files |
| SR10 | `new-test-kernel`: run_partA.sh, visit.sh, session2.sh, fetch.sh, decide.py, partA-analysis (analyze_partA.py, make_partA_html.py, test_partA.py), and the 8 page files | sample | 501 (all 2620 rows read once) | 3 (and 2 outside the sample) | kind 1: 3. Outside the sample: kind 1: 1, kind 3: 1. Page files: 9 lines in 3 files |
| SR12 | `bwx-2026-11-13`: analyze_bwx.py, test_analyze_bwx.py, render.sh. `bwx8-2026-11-14`: check_accept8.py, test_h2.py. And the 5 page files | sample | 453 (the other rows read once) | 4 (and 1 outside the sample) | kind 1: 3, kind 6: 1. Outside the sample: kind 1: 1. Page files: 4 places in 3 files |
| SR11 | Versions 13 and 11 of the runner files (seeded from version 12): bwx13.c, bwx11.c, the two self-tests, the two listing checks, the two build scripts, and the 8 page files | sample | 531 (403 rows of the writers, 128 rows taken over) | 1 (and 4 outside the sample) | kind 2: 1. Outside the sample: kind 1: 3, kind 4: 1. Page files: 18 lines in 6 files |
| SR14 | `bwx10-2026-11-15`: run_bwx10.sh, visit10.sh, schedule10.py, test_schedule10.py, test_runner10.py. `bwx8-2026-11-14/test_runner8.py`. And the 6 page files | sample | 417 (334 rows of the writers, 83 rows taken over). Four of the files read in full | 2 (and 19 outside the sample) | kind 1: 1, kind 3: 1. Outside the sample: 15 rows of run_bwx10.sh (the wordings on `${X:-value}`, on "must be set", on `pcpu`, on `_PINNED`), 3 of test_schedule10.py, 1 of test_runner10.py. Page files: 8 places in 5 files |
| SR13 | `bwx10-2026-11-15/bwx10.c`, `bwx8-2026-11-14/bwx8.c`, `bwx-2026-11-13/bwx.c` (seeded from the next later version), and the 3 page files | every row of the writers, and a sample of the rows taken over | 517 (all 343 rows of the writers, 174 sampled rows taken over). 1468 more rows read beside the source | 0 (and 5 outside the sample) | Outside the sample: kind 3: 5 (two wordings on the equal lines of the three files). Page files: 20 lines in 3 files, and 1 new reference |
| SR15 | Versions 10, 8 and the first of the build script, the self-test and the listing check (9 keys: build10.sh, bwx10_selftest.c, check_listing10.py, build8.sh, bwx8_selftest.c, check_listing8.py, build.sh, bwx_selftest.c, check_listing.py), and the 9 page files | sample | 269 (194 rows of the writers, 75 rows taken over). All other rows read once | 4 (and 1 outside the sample) | kind 1: 2, kind 3: 2, all in rows of the writers. Outside the sample: kind 3: 1. Page files: 7 places in 3 files |
| SR16 | Round 2 scripts in `bwx8-2026-11-14`: run_bwx9.sh, visit9.sh, schedule9.py, test_schedule9.py, and the 4 page files | sample | 255 (233 rows of the writer, 22 rows taken over). All 1794 rows read once, run_bwx9.sh with full care | 2 (and 5 outside the sample) | kind 3: 1, kind 6: 1, both in rows of the writer. Outside the sample: kind 1: 4, kind 5: 1. Page files: 14 places in 4 files |
| SR17 | Round 1 scripts in `bwx8-2026-11-14`: run_bwx8.sh, visit8.sh, visit_h2.sh (every row), schedule8.py (sample), and the 4 page files | every row of the three shell files, and a sample of schedule8.py | 316 (all 230 rows of the three shell files, 86 sampled rows of schedule8.py). 274 more rows of schedule8.py read once | 10 (all in the three shell files, 0 in the sample of schedule8.py) | kind 1: 6, kind 3: 3, kind 5: 1. 8 of the 10 rows were taken over from round 2. Page files: 20 places in 4 files (5 of them came from the writer) |
| SR18 | `bwx8-2026-11-14/test_schedule8.py` and its page file | sample | 145 (141 rows of the writer, 4 rows taken over). All 886 rows read once | 4 (and 1 outside the sample) | kind 1: 2, kind 2: 1, kind 3: 1, all in rows of the writer. Outside the sample: kind 1: 1. Page file: 6 places, and 1 sentence added |
| SR19 | `bwx8-2026-11-14/run_h2.sh` and `bwx-2026-11-13/run_bwx.sh` (seeded from run_bwx8.sh), and the 2 page files | full | 453 (366 rows of the writer, 87 rows taken over) | 4 | kind 1: 3, kind 2: 1, all in rows of the writer. Page files: 10 places in 2 files |

## Notes per review

### R1

- No row held a wrong instruction count, byte count, clock position or rate formula. The reviewer counted the instructions of every kernel in the build record.
- The two corrections that matter: the barrier row called the release "the common start of the timed interval" (each thread starts at its own clock read, and the start times are not stored). A self-test row said that the self-test tests the code that the benchmark runs (true for the source text only: the self-test is a separate compile).
- After R1 the main session ran `seed` again for `kernels-2026-11-13/bandwidth.c` and `cread-2026-11-12/bandwidth_cread.c`, corrected three equal own rows of `bandwidth_cread.c` (139, 145, 352), and rebuilt the six pages.
- Rows that the reviewer doubts and left: `bandwidth.orig.c` L5 and `bandwidth.c` L5 (the comment's claim that a timed interval holds no page fault: no cited file holds a page-fault count. A `perf stat -e page-faults` record of one process would decide it).

### R3b

- No row was wrong about the clock reads, the limits of the timed interval, the stop rules, the counted bytes, the rate, the pinning or the row columns. The reviewer recomputed every number that the rows cite from the 9 csv files of the rerun: all match.
- Corrections that matter: `cpu_ns` and `read_group` are called before and after an interval only with `--count` (rows 1609, 1617). The first touch writes `cfg.bytes / 8` words, so for a `--bytes` value that is not a multiple of 2 MiB a rest of the rounded-up buffer stays unwritten (rows 1646 and five equal wordings). With `--start offset` the kernel calls start at `off` (row 1699).
- Rows 1804, 1852 and 1919 now hold tokens to lines that `bwx8.c` does not have: after the next `seed` these three lines of `bwx8.c` need own rows.
- Design properties that the rows state (for the user): with `--stop common` the deadline counts from the common start and `t0` is later, so the elapsed time can be shorter than `--min-ms` (5.999979 s for 6000 ms in the rerun). The main thread is not pinned. The counters also count the two `cpu_ns` calls and the clock read `t0`.

### R2

- Every statement about the functions of `hw.sh` was compared with `hw.sh`. No row of a line of 2026-11-24 says that a past run did it. Each of the 21 arguments of the spec rows was compared with the parser of `bwx12.c`. All stated checksums were computed again.
- Corrections that matter: `${HWDIR:-...}` also replaces an empty value (5 rows). `go.sh` L3: 0.5 s is the minimum length of one timed interval, not a run time. `go.sh` L26: `fail` also stops the run when the lock file cannot be opened. `ra.sh` L54 and `run_kernels.sh` L85: the copy kernels get a second buffer per thread. `rx.sh` L14: the sampler and `atx` are pinned to CPU 119. `stat_bwx.py` L54: the field `bytes` is the size of the buffer part of each kernel call, also for `read_1pl`, which loads 16 of every 64 bytes.
- After R2 the main session ran `seed` again for `go2.sh` and rebuilt the 14 pages.
- Rows that the reviewer doubts and left: `go.sh` L42 calls `scaling_cur_freq` "the current frequency that Linux reports". By the docstring of `hwwatch.py` this file holds the rate that Linux requested, not a measured rate on this machine.

### R5

- No correction touches the clock-rate arithmetic of `clock_from_counts.py` (0 rows corrected there. The reviewer recomputed one real row: 16747251676 cycles / 5996669068 ns = 2.7928 GHz).
- Most corrections add what a read can disturb, on which CPU the reading program runs, or the exact condition of a failure. The six public references of the `hwwatch.py` page were opened and hold what the rows say.
- Limit that the reviewer names: the docstring statements of `hwwatch.py` about Linux (a read of `feedback_ctrs` interrupts the core, a read of `cpuinfo_avg_freq` does not) fit the kernel source of the vendor kit (release 7.1.3-v0.9.0). CRB ran firmware release 0.7.2 on 2026-11-17, by the design note. That kernel was not read.
- After R5 the main session rebuilt the 4 pages.

### SR1

- 0 defects in 600 sampled rows. The reviewer checked every data fact of the sample in its file (`FACTS.md`, `facts.json`, csv files, the listing), all 150 line tokens and all 51 citations of the sample.
- Notes on the source: `facts_text.py` lines 191 and 192 hold the typed counts `12 state lines` and `6 state lines` with no guard. Line 255 holds the typed value `8 s`, and its guard tests only that the gap lies between 0 s and 60 s. The facts scripts can run only in the scratch folder of the rerun (paths are derived from the place of the file).

### SR2

- 3 defects in 600 sampled rows (0.5 %). No sampled row states a wrong formula, column, file or regular expression. The reviewer opened the file for every data fact of the sample (about 40): all hold.
- Corrected: `facts_data.py` row 348 (the check `I-agg` covers only the 9 bwx12 csv files of the rerun), row 30 (a path wording), `make_report.py` row 1011 (a second stop condition).
- Notes on the source: `build_facts.py` lines 1044 to 1052 (the list of failed checks and `sys.exit(1)`) cannot run with a failed check, because `facts_text.render` stops first. Two rules for the severity of a hardware error record (`facts_data.py` lines 187 to 189 against `make_report.py` lines 929 and 930): with the present data both give the same result.

### SR3

- 2 defects in 300 sampled rows (0.7 %), both false statements of small weight: row 2517 (the boot record holds one line with the count 12, not 12 lines), row 1942 (the bold part of a figure caption is two sentences). All 398 line tokens and all 59 citations of the range were checked.
- Not done by the reviewer: no browser rendering. Rows on CSS widths were checked against the rules only.
- Notes on the source: the tooltip check of `make_report.py` line 2801 passes from 181 tooltips up, while the built page holds 333. It would still pass when two of the three layouts of figure 1 had no tooltip. The sentence counter of the Short version (line 2791) removes a full stop directly after `MT/s`. Several typed statements of the page have no assertion (process tags in two labels of Table 1, "position 1" in Table 2, two sentences of the caption of Table 4, "in every row" in the caption of figure 1 for the 5 rows at 8000 MT/s). All are true with the current data.

### R3a

- The rows of the six kernels of the whole-chip test were right in every byte count, instruction count and address. The reviewer counted by address arithmetic in the listing: `k_oldread` 16, `k_read` 11, `k_asmread` 11, `k_read_nop96` 107, `k_read_nop256` 267, `k_read_1pl` 7 instructions per loop pass. 16 more kernels were counted in the same way: all rows agree. All 55 start addresses equal the default pad.
- Corrections that matter: with `--stop common` each worker waits for the common start time and then starts at its own clock read `t0` (rows 132, 294, 324, 325). No thread stops at a common stop time: each ends at its first clock read at or after the deadline (row 325). `cfg.bytes` is not the buffer size: the buffer is `--bytes` rounded up to 2 MiB (row 268). The warm-up pass covers the range of the `--seq` entry, not the whole buffer (rows 463, 502, 1494). Thread i is pinned to entry `i % ncpus` of the CPU list (row 410).
- After R3a the main session corrected one more row of the other half (1662: the start offsets of the threads) and rebuilt the page.
- Open at this point: run `seed` again for the chain that takes rows from `bwx12.c` (done in the final pass).

### SR4

- 3 defects in 592 sampled rows (0.5 %). All 105 line tokens of the sample and all 196 "Ends the ..." rows of the 13 keys were tested by script.
- Corrected: `latency.c` rows 23 and 192 (how many loads lie between two clock reads: one whole cycle for a buffer of 1048576 lines or more, between 524288 and 1048576 loads below that), `run_crb.sh` rows 116, 119, 130 (CPU 3 only in the full plan), `analyze_writepath.py` row 58 (the idle background is also subtracted from the cycle counter), `homelat.c` row 1075, `run_sudo.sh` row 15.
- All "comment does not fit the code" reports of the writer for this folder were confirmed.
- After SR4 the main session rebuilt the 13 pages.

### SR5

- 7 defects in 566 sampled rows (1.2 %), 5 of the kinds 1 to 4 (0.9 %). The 102 rows of the 14 spec files (every row checked) and the 66 rows of the event lists had no defect: a script compared every code span of these rows with its source line (1106 spans).
- Every cited result folder was opened: all facts about past runs hold.
- Corrected: `r0.sh` row 16 (a background command of a script gets the empty input `/dev/null`, tested), the wording on `${WIN:-N}` in `rc.sh`, `rc2.sh`, `rgc.sh` (an empty value gets the default too), `an.py` row 24.
- Follow-up of the main session: the same wording on `${X:-default}` stands in 29 rows of 11 other shell pages ("when X is not set" without "or empty"). To correct in the final pass.

### SR7

- 8 defects in 686 sampled rows (1.2 %). No defect in `schedule11.py`, `hostwatch.py`, `visit11.sh` and the four cread files.
- Corrected: `run_bwx11.sh` rows 86 and 94 (the stop rule is `now + MARGIN >= STOP_EPOCH`, so a process starts only when the deadline is more than `MARGIN` seconds away), `test_schedule11.py` rows 540, 542 (36 combinations, not 108) and 1509, `test_runner11.py` rows 216, 1013, 1370, 1391, 1932, `schedule_zs.py` row 41.
- The rule "no name with 11 in a row of a line that version 10 shares" has 0 breaches in a scan of all rows on shared lines.
- After SR7 the main session ran `seed` again for `test_runner10.py` and `test_runner8.py` and rebuilt the pages.

### SR6

- `report_w120.py`: 0 defects in 150 sampled rows. The reviewer computed the number groups of the script again from the raw files (13 lines-in-flight values and 14 probe times, all values of the 13 groups of F5, the load values of 14 folders, all 29 rows of table F2): all equal the values in the source.
- `robsize.c`: 0 defects in 150 sampled rows. The template rows agree with the saved listing `tmpl.lst`.
- ASCT keys: the 8 defects lie in the five input files (50 rows, every row checked). The 8 scripts and Python files (167 sampled rows) have none.
- Confirmed by experiment: `exit 2` inside `cpuflags` does not stop `run_chip.sh` and `run_mesh.sh`.

### R4

- No row was wrong about a compiler flag, a recorded value, a checksum, a byte count or a rule of the listing check. The reviewer wrote the rules of the listing check again from the rows: this reproduces the 29 rows of part 1 of the saved check output. All 210 line tokens and all 109 citations were opened.
- Corrected: `build12.sh` rows 24, 25, 34 (a second cause of exit status 6. No CPU limit when `_PINNED` is already set. The restart under `taskset` needs a `$0` that can be executed), `bwx12_selftest.c` rows 290 and 627, `check_listing12.py` rows 32, 192, 316.
- After R4 the main session ran `seed` again for the six files of the versions 13 and 11 and rebuilt the 10 pages.

### SR8

- The two page builders had 0 defects in 300 sampled rows. The 8 defects lie in the two test files (5) and in `render_q1.sh` (3, small).
- The reported behavior of `make_q2_html.py` for hypothesis H11 holds (the reviewer copied the functions into a test of its own). It has one more case than the writers reported: on a page with two sessions, a cell that has a result in one session only gets the same word. The delivered two-session page is not affected: all 32 cells have a result in both sessions.
- The glossary text of "Common stop" ("all threads stop at the same time") is not exact: each thread ends at its own first clock read at or after the common deadline. To correct in `GLOSSARY.md` and in the page files in the final pass.

### SR9

- 8 defects of the kinds 1 to 4 in 480 sampled rows (1.7 %). `figs.py` had none in 80 rows. All verdict rules on the `facts.py` page agree with the code and with `DECISIONS.md`.
- The page files of this unit held the most defects (21): mostly claims that were too wide ("holds every number of the report", "only formats"). All corrected.
- The three places that the writer reported are confirmed: the six headings "Prediction ... holds" of `dyn_notes.py` are fixed text, the bar of `figs.py` line 200 ends at the middle between the smallest and the largest total, and the caption of `report.py` line 85 says "Median of the processes" where other medians are shown.

### SR10

- 3 defects in 501 sampled rows (0.6 %), all of small weight. `analyze_partA.py` had none in 150 rows. Every cited file was opened: all facts about past runs hold.
- Corrected: `session2.sh` row 6 (with `BWX_STOP=common` the time of one thread can be a little shorter than `BWX_MIN_MS`: 2 of 9072 thread rows of one B8 file have `elapsed_s` 5.999999), `decide.py` rows 174 and 177 (what the test proves and what it does not), `make_partA_html.py` row 886, `test_partA.py` row 325.
- Both reports of the writer on `run_partA.sh` are confirmed: the comment lacks exit status 1, and the script starts one `date` and one `sleep` process per second while a benchmark runs.

### SR12

- `analyze_bwx.py` had 0 defects in 150 sampled rows. The 4 defects lie in the two test files.
- The writer's claim on `analyze_bwx.py` line 543 holds (the reviewer copied the functions into a test of its own): for a change of `D` between two settings only the word is compared, not the sign. A change of +140 GB/s with one metric and of -140 GB/s with the other, both resolved, gave the joined word `resolved`. This differs from point A7 of the deviations note, which says that word and sign are compared.

### SR11

- 1 defect in 531 sampled rows (0.2 %). None of the 128 sampled rows that were taken over from version 12 had a defect.
- All 32 addresses in the rows of `bwx13.c` and all 23 in `bwx11.c` are in the build record of their own version, and all instruction counts per loop pass agree (parsed by script). No row and no page of the 8 keys states a fact of the whole-chip test.
- The writer's report on `bwx13.c` line 23 is confirmed: the comment calls the block order of the three new kernels random, but `rand_index` returns the fixed value `(i * (2 * i + 1)) & (nb - 1)`, and no option selects the order.
- Corrected outside the sample: `build11.sh` rows 20 and 85 ("no script uses `seq-listing.txt`" is false in version 11, because `test_runner11.py` reads it).

### SR14

- 2 defects in 417 sampled rows (0.5 %). None of the 83 sampled rows that were taken over had a defect.
- The reviewer read `run_bwx10.sh` in full and corrected 15 more rows. 14 of them were rows taken over from `run_bwx11.sh`. The main session copied the corrected texts back to the equal lines of `run_bwx11.sh` (14 rows) and of `test_schedule11.py` (3 rows) with `backport.py`, ported four page corrections to the round 4 pages, ran `seed` again for the chain and rebuilt 16 pages.
- The process counts and the order rules of the `schedule10.py` page agree with the source and with the 9 schedule copies in the result folders.

### SR13

- 0 defects in 517 checked rows: all 343 rows of the writers (115, 111 and 117) and 174 sampled rows taken over (58 per key).
- A script of the reviewer parsed the five machine-code listings. All 26 kernels shift by 0xc0 from version 11 to 10, all 21 by 0x180 from 10 to 8, and all 21 by 0x600 from 8 to the first runner. Every address and every instruction count in the rows agrees with the listing of its own version.
- All 5572 rows taken over equal the row of the next later version, and every line token points to the same source text there (script of the reviewer).
- Corrected outside the sample: the warm-up row (`bwx10.c` 1188, `bwx8.c` 1016, `bwx.c` 1011) did not name the page-state reading that a process with one thread makes between the warm-up pass and the timed interval. The header comment row (`bwx10.c` 35, `bwx8.c` 10) repeated "nothing but clock reads between the windows" without the counter reading before a target window.
- After SR13 the main session put both facts into the equal rows of `bwx11.c` (61, 1253), `bwx12.c` (94, 1669) and `bwx13.c` (125, 1825), ported three page sentences to the pages of `bwx11.c` and `bwx13.c`, added the sentence on `--trace` to the pages of versions 11, 10 and 8, ran `seed` again for the chain and rebuilt the six runner source pages.
- Rows that the reviewer doubts and left: `bwx10.c` 404, 443, 580 ("one call gets one chunk of 2 MiB": for a `--seq` entry below 2 MiB the chunk is the whole entry, and the word list says so). `bwx10.c` 1151 and `bwx8.c` 979 ("the start function of every worker thread": the worker of the trial mode starts in `trial_worker`). `bwx10.c` 1484 and 1510 (the rows report a comment that names the scripts of version 8).

### SR15

- 4 defects in 269 sampled rows (1.5 %). None of the 75 sampled rows that were taken over had a defect.
- The reviewer wrote the rules of the three listing checks again from the rows. For the first runner the output equals both saved check outputs byte for byte. For the versions 8 and 10 it gives the results of the project note. `offsets.tsv` rebuilt from the listings with the rule of the rows equals the saved table in all 4 build records.
- Confirmed: both CRB builds of the first runner ended `check_listing.py` with `failed_rows=1`.
- Corrected: `build10.sh` row 28, `build8.sh` row 22 and `build.sh` row 23 (the restart under `taskset` needs a `$0` that can be executed), `build.sh` row 47 (the marker file is checked before each self-test only, not before the four runs with `--list`), `check_listing.py` row 11 (the reference of `oldread2` is in `bw_old`).
- After SR15 the main session put the same facts into the rows of `build11.sh` (32), `build12.sh` (34) and `build13.sh` (36) and into two bullets of the pages of `build11.sh` and `build13.sh`, and rebuilt the 12 pages.
- Rows that the reviewer doubts and left: `bwx8_selftest.c` 380 and `bwx10_selftest.c` 572 ("`main` calls `selftest` for the argument `--selftest`": with `--trial` on the same command line `main` calls `trial_main` first).

### SR16

- 2 defects in 255 sampled rows (0.8 %), 1 of the kinds 1 to 4 (0.4 %). None of the 22 sampled rows that were taken over had a defect.
- Step `XW`: the code gives 864 s of nominal work per session (the loops of `schedule9.py`, the table of the test, and `planned_nominal_ms=864000` in `env.txt` of both `XW` result folders). The 852 s of `DECISIONS-bwx8.md` is wrong.
- The process order that the reviewer computed from the seed rule equals all 13 `schedule.tsv` copies in the result folders. All 13 `env.txt` files record the sha256 of `run_bwx9.sh`.
- Corrected: `run_bwx9.sh` rows 41, 70 and 207, `test_schedule9.py` rows 35, 437, 630 and 977. In the page of `run_bwx9.sh` the list of things that stop the run was given as complete: with `set -e` a failed command such as `mkdir` or `cp` also ends the script, without a message.
- After SR16 the main session corrected the equal rows of `run_bwx11.sh` (49, 102, 241) and of `run_partA.sh` (6, 30), added the seventh stop cause to the pages of `run_bwx10.sh` and `run_bwx11.sh`, corrected the short versions of the pages of `test_schedule10.py` and `test_schedule11.py`, defined the word "Design" on four pages, and put the meaning of the `ps` column `pcpu` into 9 rows and 3 pages of other folders.
- Rows that the reviewer doubts and left: `test_schedule9.py` 1151, 1174, 1182, 1189 (the rows leave out the condition that the process had started), 709 and 753 (`max_sample_us` is called a count, it is a time), `run_bwx9.sh` 156.

### SR17

- 10 rows corrected in the 230 rows of `run_bwx8.sh`, `visit8.sh` and `visit_h2.sh` (4.3 %). 0 defects in the 86 sampled rows of `schedule8.py`.
- 8 of the 10 rows were rows taken over from round 2. 4 of them held a wording that the review of round 2 corrected at the same time (the `pcpu` wording twice, the `_PINNED` exception, "before anything runs").
- The reviewer ran a copy of `schedule8.py` in its scratchpad folder. The schedules for `B6W`, `S2` and `S4` of both sessions are byte-equal to the 6 `schedule.tsv` copies in the result folders. Counts, work times and the four plan seeds equal the page.
- All 6 `env.txt` files record the sha256 of `run_bwx8.sh`. The 4 visit logs end with the status lines that the pages quote.
- After SR17 the main session corrected the equal rows in the rounds 2 to 4 (the loop that checks the steps, the `setsid` row, the usage row of the three visit scripts) and four page sentences, and rebuilt the pages.
- One read-only shell command of the reviewer was denied by the permission system (a search in a note). The reviewer read the note with the file tool.
- Rows that the reviewer doubts and left: `run_bwx8.sh` 14 and 20 (the rows give the message of the comment, and the code differs in a small case), 21 to 23 (no row names the exit under `set -e`, the page does), 123. `schedule8.py` 291, 106 and 258.

### SR18

- 4 defects in 145 sampled rows (2.8 %), all in rows of the writer. None of the 332 rows taken over names a step, a binary, a kernel, an option, a check or a count of round 2 (script of the reviewer).
- The counts of the rows and of the page agree with a copy of the generator and of the test functions that the reviewer ran in its scratchpad folder (671 files, 1440 trials of `S2`, 192 command lines, 11 damaged plans, 5 variants of `S2`, 9 bad values of `SESSION1_END`).
- Corrected: rows 8, 28, 174, 196 and 413. The page said that most rules are also applied to a damaged input. By count, 24 of the 176 checks of `schedule_checks` are such second tests.
- After SR18 the main session made the same statement exact in the test pages of rounds 3 and 4 (the validator, the rule for the CPU order and the rule functions of the steps have a second test), and added the note on the divisor check to the test pages of rounds 2 to 4.
- Rows that the reviewer doubts and left: 30, 671, 691, 697, 801, 943 and 974 (a "So" sentence goes from the tested cases to a general rule).

### SR19

- 4 rows corrected in 453 (0.9 %). None of the 87 rows taken over needed a correction. No row was wrong about what a step runs, its arguments, the process counts, the planned times, the stop rules, the waits, the records or the exit statuses.
- `run_bwx.sh`: a model of the step functions that the reviewer wrote equals all 684 header lines of the 29 result folders (tag, binary, options), and `planned_processes`, `planned_timed_s` and `MARGIN` of all 29 `env.txt` files. The six kernel sequences equal the table of section B.9 of the handoff note.
- `run_h2.sh`: the reviewer's model of the pair order equals `order.tsv` of both sessions (72 rows each) and the 72 header lines of each `H2.csv`. In the 144 recorded header lines the wait before a launch (`waited_s`) is 0.
- All six readings of the writer on comments that do not fit the code are confirmed (`run_h2.sh` lines 7, 13 and 39, `run_bwx.sh` lines 23, 35 and 126).
- Corrected: `run_h2.sh` rows 36 and 38, `run_bwx.sh` rows 22 and 104.
- After SR19 the main session corrected the same `_PINNED` wording in `run_bwx10.sh` (row 51), `run_bwx11.sh` (row 53) and in two page lines, and the `MARGIN` wording of `run_partA.sh` (rows 12 and 17, one page line).
- Rows that the reviewer doubts and left: rows that say "intervals of at least N ms" for a process with the common stop (the page states the limit). `run_bwx.sh` 169. `run_h2.sh` 56, 107, 110, 111. The rows on the signal HUP (see the hypothesis in SOURCE-NOTES.md).
