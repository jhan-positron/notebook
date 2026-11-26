# Briefing for the reviewers of the line-by-line pages

Read `BRIEF.md` and `GLOSSARY.md` of this folder first. They hold the rules that the writers had. This file says what a reviewer does.

## 1. The job

A writer has written one explanation per source line (a "row"). You check every row of your keys against the source, and you correct the rows that are wrong. You are a second, independent reader: do not trust a row because it sounds sure.

The user reads these pages to review the test code of a benchmark. A wrong row is worse than a missing row.

## 2. What counts as a defect, most important first

1. **False.** The row says something that the source line does not do, or that the file it names does not hold. Examples: a wrong byte count, a wrong unit, a wrong order of steps, a flag explained with the meaning of another flag, "ends the function" on a line that ends a loop.
2. **Not grounded.** A statement about a past run, a result, the machine code, the hardware or another file that you cannot confirm from the files that the row or the page names. A statement about what a past run did on a line that was written on 2026-11-24 (fact 1 of section 10 of the briefing).
3. **Missing.** The row leaves out a fact that section 4 of the briefing requires for this line ("Say these things exactly": what is timed, where the clock is read, which bytes are counted, how a rate is computed, pinning, buffers, order, stops, exit statuses, the source of a number).
4. **Wrong pointer.** A token `{L..}` that names the wrong line. A citation `[RefN]` whose reference does not prove the sentence.
5. **Not understandable.** A term that a newcomer cannot know, that the row does not explain, and that the list "Words used here" of the page does not hold.
6. **Plain English.** An idiom or a metaphor. A sentence that hides a condition in a side clause. A number without a unit.

Not a defect: a row that is correct and could be worded in another way. Do not rewrite for taste. Do not shorten or lengthen a correct row.

## 3. How to check

- Work in pieces of about 150 source lines: `python3 T2/lbl.py show KEY A B` prints each source line and under it the row (`=` a row of the writer, `~` a row taken over from another version of the file).
- For each piece: first read the source lines and decide for yourself what they do. Then read the rows.
- Open the other file when a row says something about it (a helper script, a result file, a machine-code listing). `python3 T2/lbl.py info KEY` lists the references of a page with their paths.
- Test a shell construct, a regular expression or a Python expression with a small experiment in your scratchpad folder when you are not sure. Never run a file of the code folder. Never use `ssh`.
- Rows marked `~` need the same care: the text was written for another file. Check that it is true here.
- For a page with `mode new`, also check the page file `T2/ann/KEY.page.md`: the short version, the list of words (a definition must be true and must be the one of `GLOSSARY.md` when the term is there), the main flow (order, line tokens), the behavior notes.

## 4. How to correct

- A row marked `=`: edit its line in the annotation file that holds it (`T2/ann/KEY.ann` or a file in `T2/ann/KEY.ann.d/`). Keep the form `N: text`.
- A row marked `~`: never edit a `.seed` file. Write the corrected row as `N: text` into the file `T2/ann/KEY.ann.d/zz-review.ann` (create it, or use `T2/ann/KEY.ann` when the key has no `.ann.d` folder). A row there replaces the seed.
- Follow sections 5 and 6 of the briefing in every row that you write.
- After your corrections `python3 T2/lbl.py check KEY` must print `OK`.
- Do not run `build`, `seed`, `manifest`. Change no source file and no page.

## 5. Your report

- Per key: rows checked, rows corrected.
- A list of the corrected rows: key, line, kind of defect (the number of section 2), and one sentence that says what was wrong.
- Rows that you doubt and could not decide, with the reason.
- Anything in the source that looks like a bug or that a comment states wrongly (the user wants to know). Do not change it.

## 6. Sampled review (only when your task says "sampled review")

For a sampled review you do not check every row. Your task gives, per key, a number of rows N and a seed.

- `python3 T2/lbl_main.py sample KEY N SEED` prints N rows of the key, chosen at random (with two more numbers A B: only from the lines A to B). The same command prints the same rows again.
- Read the source file first, at least the functions that hold the sampled lines, so that you can judge a row in its context. Then check each sampled row as section 2 and 3 say. Also read the rows directly before and after a sampled row when you need them to judge it.
- Correct each defect that you find (section 4). When you see a defect in a row that is not in the sample, correct it too and report it apart.
- Report per key: rows in the sample, rows of the sample with a defect, by kind (the numbers of section 2). The main session uses the share of defects of the kinds 1 to 4 to decide whether the key needs a full review. So be exact: count a row as a defect only when you corrected it.

## Rule of this server: the allowed CPUs

- Every shell command of an agent is pinned to CPUs 26 to 31 of this server. Never change the allowed CPUs of a process: no `taskset`, no `numactl`, no `os.sched_setaffinity`, also not for a short experiment.
- To learn what such a command does, read its manual page (`man taskset`, `taskset --help`).
- Keep the number of busy processes at 6 or fewer. Size a worker pool from `nproc`.
