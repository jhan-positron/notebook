# Work queue of the main session (line-by-line pages, 2026-11-25)

The limit of the harness is 20 subagents at once.

## Units and their state

| Unit | Keys | State |
|---|---|---|
| main | `w120-2026-11-15/rx.sh`, `manual-run/run.sh` | written by the main session, built |
| A5 | rerun scripts: go.sh, go2.sh, ra.sh, 3 spec, 2 sha, stat_k120.py, stat_bwx.py, test_make_report.py, `kernels-2026-11-13/run_kernels.sh` | done, built |
| A6 | `kernels-2026-11-13`: bandwidth.orig.c, bandwidth.c, selftest.c, probe.c. `cread-2026-11-12`: all 5 | done, built (also `bench/bandwidth.c`, equal file) |
| A9 | `hwwatch-2026-11-24`: hw.sh, hwwatch.py, clock_from_counts.py, test_hwwatch.py | done, built |
| A1a, A1b | `w120-7200-2026-11-17/make_report.py` lines 1-1483 and 1484-2834 | done, built (row 1558: four 6-decimal sums of T72C1 left out: the writer had a command denied by the permission system. Do not work around it. Tell the user) |
| A2 | `w120-7200-2026-11-17/facts_text.py` | done, built |
| A3 | `w120-7200-2026-11-17/facts_text4.py` | done, built |
| A4 | `w120-7200-2026-11-17/facts_data.py`, `build_facts.py` | done, built |
| A7a, A7b | `bwx12-2026-11-15/bwx12.c` lines 1-1561 and 1562-3126 | done, built |
| A8 | `bwx12-2026-11-15`: build12.sh, bwx12_selftest.c, check_listing12.py, test_kernels12.py | done, built |
| A10 | `w120-2026-11-15` without rx.sh and report_w120.py (39 keys) | done, built |
| A11 | `asct-2026-11-16`: crb/*.sh, visit.sh, 5 txt, resolve_events.py, baseline.py, notes.py. `w120-2026-11-15/report_w120.py` | done, built |
| A12 | `asct-2026-11-16`: analyze.py, facts.py, svgchart.py, figs.py, report.py, dyn_notes.py | done, built |
| A13 | `bench` without bandwidth.c | done, built |
| A14 | `new-test-kernel/partBC-analysis`: make_q1_html.py, test_q1.py | done, built |
| A15 | `new-test-kernel/partBC-analysis`: make_q2_html.py, test_q2.py, recount/recount_results_md.py, render_q1.sh, gen_s1.sh | done, built |
| A16 | `new-test-kernel`: run_partA.sh, visit.sh, session2.sh, fetch.sh, decide.py, partA-analysis (3 files) | done, built |
| A17 | `bwx11-2026-11-15/test_runner11.py` | done, built |
| A18 | `bwx11-2026-11-15`: run_bwx11.sh, visit11.sh, schedule11.py, schedule_zs.py, test_schedule11.py. `bwx10-2026-11-15/hostwatch.py` | done, built |
| A19 | `bwx-2026-11-13`: analyze_bwx.py, test_analyze_bwx.py, render.sh. `bwx8-2026-11-14`: check_accept8.py, test_h2.py | done, built |
| B1 | seeded from the bwx12 files: `bwx13-2026-11-15` (4 files), `bwx11-2026-11-15`: bwx11.c, bwx11_selftest.c, check_listing11.py, build11.sh | B1a and B1b done, built (bwx13 and bwx11 folders complete) |
| C1 | seeded: `bwx10-2026-11-15` all except hostwatch.py | all done and built: C1c (test_runner10.py, test_runner8.py), C2 (bwx10 scripts), C1a (bwx10.c, bwx8.c, bwx.c), CDE-b (build, selftest, check_listing of the versions 10, 8 and the first) |
| D1 | seeded: `bwx8-2026-11-14` all except hostwatch.py, check_accept8.py, test_h2.py | D2a done, built (run_bwx9.sh, visit9.sh, schedule9.py, test_schedule9.py). D2b: run_bwx8.sh, visit8.sh, visit_h2.sh, schedule8.py done and built. D2b RUNNING on test_schedule8.py (its last key: the main session took keys 6 and 7 away at 01:40 UTC of 2026-11-26). D2c RUNNING (agent name `D2c`): run_h2.sh and bwx-2026-11-13/run_bwx.sh, both seeded from run_bwx8.sh |
| E1 | seeded: `bwx-2026-11-13`: bwx.c, bwx_selftest.c, check_listing.py, build.sh, run_bwx.sh | covered by C1a (bwx.c), CDE-b (build.sh, bwx_selftest.c, check_listing.py) and D2b (run_bwx.sh) |

## Reviews

| Review | Keys | State |
|---|---|---|
| R1 | kernels-2026-11-13: bandwidth.orig.c, bandwidth.c, selftest.c, probe.c | done, corrections applied, pages rebuilt (see REVIEW-RESULTS.md) |
| R2 | go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, manual-run/run.sh, 3 spec, 2 sha, stat_k120.py, stat_bwx.py, test_make_report.py | done, corrections applied, pages rebuilt (see REVIEW-RESULTS.md) |
| R3 | bwx12.c (two reviewers, halves) | R3a and R3b done, page rebuilt. The chain that takes rows from bwx12.c needs seed again (final pass: lbl_main.py reseed-all) |
| R4 | build12.sh, bwx12_selftest.c, check_listing12.py, test_kernels12.py | done, pages rebuilt |
| R5 | hw.sh, hwwatch.py, clock_from_counts.py, test_hwwatch.py | done, corrections applied, pages rebuilt (see REVIEW-RESULTS.md) |
| R6.. | the five Python pages of S (make_report.py, facts_text.py, facts_text4.py, build_facts.py, facts_data.py) | SR1, SR2, SR3 done (5 defects in 1500 sampled rows), pages rebuilt |
| sample | the other units: a random sample per key (REVIEW.md section 6): files above 400 rows 120 to 200 rows, smaller files 25 %, at least 20 rows | done: SR4 to SR12 (see REVIEW-RESULTS.md). SR13 and SR14 done, recorded, pages rebuilt, corrections ported to the later versions. Running: SR15 (9 keys of CDE-b), SR16 (4 keys of D2a), SR17 (agent name `SR17`: run_bwx8.sh, visit8.sh, visit_h2.sh in full, schedule8.py sampled). Still to start: SR18 for test_schedule8.py (after D2b) and for run_h2.sh and bwx-2026-11-13/run_bwx.sh (after D2c) |

## After a review changed rows of a file that seeds another file

Run `python3 lbl.py seed CHILD` again in the order of the chain (the list `SEED` in `lbl.py`), then `check` every child, then `build-all`.
After the review of the kernels: seed `kernels-2026-11-13/bandwidth.c`, then `cread-2026-11-12/bandwidth_cread.c`, then build both and `bench/bandwidth.c`.
After the review of the run scripts: seed `w120-7200-2026-11-17/go2.sh`.

## At the end (final pass of the main session)

1. `python3 lbl_main.py reseed-all`, then `check` every seeded key, write the rows that lost their seed.
2. The wording on `${X:-default}`: scan all Bash rows again (a row that says "not set" without "empty") and correct them.
3. `python3 lbl_main.py glossary-check`: put the glossary wording of "GB, MiB" into the page files that still hold `2^20`.
3b. DONE on 2026-11-26 01:30 UTC (26 page files, 3 rows; the pages are not rebuilt yet). The glossary entry "Common stop" is not exact ("all threads stop at the same time"). New text: "a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline." Change `GLOSSARY.md` and every page file that holds the old text.
4. Row 1558 of `make_report.py`: leave as it is, tell the user (a command of the writer was denied by the permission system).
5. Then:

`python3 lbl.py build-all`, `python3 lbl_main.py pages-check`, `python3 lbl_main.py index`, update the memory file `crb-line-by-line-pages-2026-11-25.md`.

## Notes of 2026-11-26 01:40 UTC

- A second reader exists: `check_markdown_it.py` (needs the package markdown-it-py, installed in the scratchpad folder `mdit/venv` of this session). It read 171 built pages back equal to their source.
- Another session of the user works in the repo `ai-proj` at the same time (a manual run of the whole-chip test, started 2026-11-26 01:09:58 UTC). So run `pages-check` at the very end: it fails when a source file changed after the manifest was written.
- `code/hwwatch-2026-11-24/__pycache__/` in the repo was written at 2026-11-26 01:02:49 UTC. No command of this session or of its agents names that folder at that time. The index skips `__pycache__`.

## State at 2026-11-26 02:25 UTC

- Done and recorded in REVIEW-RESULTS.md: SR13, SR14, SR15, SR16, SR17. Their corrections are ported to the equal rows and page sentences of the other versions, and the pages are rebuilt.
- D2b done (keys 1 to 5 of its unit). 176 of 178 pages are built and pass `pages-check` and `check_markdown_it.py`.
- Running: writer `D2c` (run_h2.sh, bwx-2026-11-13/run_bwx.sh: all rows written, `check` OK, report not yet in), reviewer `SR18` (test_schedule8.py).
- To start after the report of D2c: review `SR19`, a full read of run_h2.sh and bwx-2026-11-13/run_bwx.sh. Points to give it: the seventh stop cause (`set -e`), the `pcpu` wording, "MARGIN seconds away or less", "before the first process of the step starts", `RESERVE` "not set or is empty" in the page files, and two points of SR17 (row of run_bwx.sh line 280: line 281 can end with status 6. Row of run_h2.sh "before the first step": run_h2.sh has no steps).
- Final pass, in this order: `lbl_main.py reseed-all`, `scan_default.py`, `lbl_main.py glossary-check`, `lbl.py build-all`, `lbl_main.py pages-check` (178), `check_markdown_it.py` (178), `lbl_main.py index`, `scan_commands.py`, `make_summary.py` (after the TAKEN_OVER list and REVIEW_LABEL in the scripts are complete), render check of the summary page, memory file, final answer.
- Summary page: `make_summary.py` and `summary_facts.py` write `S/code-pages-summary.html`. It needs the final numbers of SR18 and SR19.
- Facts to tell the user (also on the summary page): three `taskset` experiments outside the CPUs 26 to 31 (list: `scan_commands.py`), row 1558 of make_report.py, one denied read-only command of SR17, the file `report_w120.py.page.md` written through the shell, another session works in the repo (new `arm-crb/manual-run.sh`, `__pycache__` in hwwatch-2026-11-24 at 01:02:49 UTC).

## Final state, 2026-11-26 03:00 UTC

- All 178 pages are built. `pages-check` and `check_markdown_it.py` read all of them back equal to their source (63132 rows). The index and the summary page are written.
- All writers and reviews are done and recorded (R1 to R5, SR1 to SR19). `reseed-all`, `scan_default.py` and `glossary-check` ran after the last review.
- Nothing is open in this queue.
