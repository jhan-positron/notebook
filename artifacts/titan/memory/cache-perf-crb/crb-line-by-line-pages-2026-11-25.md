---
name: crb-line-by-line-pages-2026-11-25
description: "Line-by-line explanation pages of all code of ai-proj/arm-crb/code, built into the rerun scratch folder S: tool folder, layout, rebuild rules, and what the older companion tool must no longer do"
metadata:
  node_type: memory
  type: project
  originSessionId: e8814cab-99b1-4798-9af9-6536ce08ea6e
  modified: 2026-11-26T02:18:45.310Z
---

User request of 2026-11-25: replace the detailed section of the `.md` pages under `crb/tmp/agent-scratch/w120-7200-2026-11-17/` (S) with a line-by-line explanation in valid Markdown, from the newer source texts of `~/workspace/ai-proj/arm-crb/code` (REPO), leave the other sections intact, and explain all code of REPO at S (C kernels and Python too).

Puzzle that the user raised: no C page in S. Answer: the request of 2026-11-22 said "these companion files are in the same folder as their target files". So the C pages were written beside the C sources, in `crb/tmp/agent-scratch/kernels-2026-11-13/` and `.../bwx12-2026-11-15/`. S never held C code.

Tool folder: `crb/tmp/agent-scratch/line-by-line-2026-11-25/` (T2).

- `lbl.py`: `manifest`, `info`, `show`, `old`, `seed`, `check`, `build`, `build-all`, `status`. `lbl_main.py`: `index`, `sample`, `units`, `pages-check`.
- Input per file: `T2/ann/<path below REPO>.ann` or `.ann.d/*.ann` (one line `N: text` per source line that is not blank, `@part A-B title` lines), plus `.page.md` for a new page. `.seed` files are written by `lbl.py seed` (explanations taken over from another version of the file).
- `BRIEF.md` and `GLOSSARY.md`: the rules that the writer agents got.
- Never edit a built page by hand. Edit the annotation and run `python3 T2/lbl.py build KEY`. The build reads every table back with its own reader and with pandoc (reader gfm) and stops when a source cell differs from the source line.

Layout decisions (mine, the user was not asked, see [[minor-design-readings-decide-not-ask]]):

- Files of the repo folder `w120-7200-2026-11-17`: the page stays at the top of S (`S/go.sh.md`). Only the section "Source and explanation ..." is replaced. Its heading is now "Source and explanation, line by line" in every page. The page before the change is kept in `T2/backup/`.
- Every other repo folder X: `S/code/X/<file>.md`. When an older companion existed beside the scratch source (11 files), the new page is a copy of it with a new head and the new table section.
- Index: `S/code-pages.md`.
- Scope: C, Python, Bash, the Makefile, and the `.spec` and `.txt` input files, plus `local.sha` and `go2.sha` of S. Not the 6 JSON data files and not the 8 Markdown notes of REPO.
- Table form: `| Line | Source | Explanation |`, one row per line, blank lines without a row, each `|` of the source written `\|`. A source line with a backslash directly before `|` stands in a code block between two tables, because Markdown readers do not agree on that pair in a table cell (pandoc 2.9 reads `\\|` as backslash plus pipe, newer readers end the cell there).
- For `go.sh`, `go2.sh`, `ra.sh`, `rx.sh`, `run_kernels.sh` the repo text is newer than the scratch text. The other sections of these pages still describe the scratch text. The table section holds a map of the line numbers.

Consequences for the older tools (see [[crb-whole-chip-code-data-list-2026-11-21]]):

- The 16 pages of S that have a table section are no longer output of `companion_tool.py` or `make_go_sh_md.py`. `companion_tool.py build` or `build-all` and `make_go_sh_md.py` would write the older page again. After such a run, run `python3 T2/lbl.py build-all`.
- `companion_tool.py verify` stops at these keys (it searches for `<table style=`).
- The list `crb/new-test-kernel/whole-chip-test-code-data-list.md` was not changed.

More files of T2 (added while the job ran):

- `lbl_main.py` also has `reseed-all [PREFIX]` (takes the rows of another version over again, in chain order) and `glossary-check`. `check_markdown_it.py` is a second read-back with the package markdown-it-py (not installed on the agent server: make a venv first).
- `REVIEW.md` (rules for reviewer agents), `REVIEW-RESULTS.md` (one table row and one note per review, R1 to R5 and SR1 to SR19), `review-lists/` (the sample commands).
- `SOURCE-NOTES.md`: the points about the source code that writers and reviewers reported (measurement points, comments that do not fit the code, files that the repo copy lacks). Nothing in the code was changed. Look here first when the user asks what the review of the test code found.
- `make_summary.py` and `summary_facts.py` write the summary page `S/code-pages-summary.html` (chart of the review results, limits, findings). `scan_commands.py` scans the session records of the job for starts of code-folder scripts, `ssh` and `taskset` (see [[agentsrv-cpu-rule-in-agent-briefs]]).
- `patch_rows.py`, `backport.py`, `scan_default.py`, `mklist.py`: small helpers of the main session.

After a change of a source file in REPO: `python3 lbl.py manifest`, write the rows of the changed lines, `python3 lbl.py build KEY`, then `python3 lbl_main.py pages-check` and `python3 lbl_main.py index`. `pages-check` reports every page whose source changed after the manifest was written.

Open points that I told the user on 2026-11-25:

- Row 1558 of the page of `make_report.py` lacks four sums with 6 decimals of the process T72C1. The permission system denied the command of the writer agent. Do not work around it. The older text is in `T2/backup/`.
- `arm-crb/manual-run.sh` (written by another session on 2026-11-25, outside `code/`) has no page. The 6 JSON files and the 8 Markdown notes of REPO have none either.
- Sampled reviews do not prove the rows outside the samples. The summary page gives the estimate.
