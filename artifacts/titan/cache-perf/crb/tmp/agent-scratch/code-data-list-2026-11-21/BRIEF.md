# Briefing for every agent of this task

## 1. The task

The user wants to review the code and the data of one benchmark run, with a written explanation next to every file.

- The run: the whole-chip read test on CRB (an Arm reference server with 128 CPUs), run on 2026-11-17 after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- The result under review: at 7200 MT/s the new read kernel was still about 30 % slower than the old read kernel with 120 threads.
- "Kernel" here means the inner loop of the benchmark that reads memory. It never means the Linux kernel. Write "Linux kernel" for the operating system kernel.
- Our deliverable: for each code file a companion file `<file>.md` with the source at the left and the explanation at the right. For each data file a companion `<file>.md` that explains its rows and columns.
- A script builds the companion from the source file plus your explanations. You never copy source text. You write explanations with line numbers.

## 2. The test in short

Folders:

- `C` = `/home/jhan/workspace/titan/cache-perf/crb`
- `R` = `C/results` (result folders copied back from CRB)
- `S` = `C/tmp/agent-scratch/w120-7200-2026-11-17` (run scripts, analysis scripts, facts sheet of the rerun)
- `K13` = `C/tmp/agent-scratch/kernels-2026-11-13` (old and new benchmark source, script of 2026-11-13)
- `BWX12` = `C/tmp/agent-scratch/bwx12-2026-11-15` (runner program bwx12 and its build script)
- `W15` = `C/tmp/agent-scratch/w120-2026-11-15` (runner script rx.sh)
- `T` = `C/tmp/agent-scratch/code-data-list-2026-11-21` (this task: tool, manifest, your output)
- On CRB the same files lived under `~/cache-perf/` (`S` was `~/cache-perf/w120-7200-20261117`, `K13` was `~/cache-perf/scratch-kernels-20261113`, `BWX12` was `~/cache-perf/bwx12-20261115`, `W15` was `~/cache-perf/w120-20261115`, `R` was `~/cache-perf/results`).

Call sequence of the run (on CRB, no root, CPUs 0-119):

```
go.sh  (driver, 3 sessions, then one more part C process)
 |- ra.sh T72A<s>                      part A -> R/k120-T72A<s>-<time>/threads120.csv, probe.txt
 |    |- bw_old  (built from K13/bandwidth.orig.c by K13/run_kernels.sh on 2026-11-13)   old read kernel
 |    `- bw_new  (built from K13/bandwidth.c      by K13/run_kernels.sh on 2026-11-13)   new read kernel
 |- rx.sh T72L<s> bwx12 SHA < like.spec   part L -> R/w120-T72L<s>-<time>/a6456.csv, env.txt, launches.txt, stderr.txt
 |    `- bwx12   (built from BWX12/bwx12.c by BWX12/build12.sh on 2026-11-15)  kernels oldread, asmread, read_nop96, read_nop256, read_1pl
 `- rx.sh T72C<s> bwx12 SHA < cfwd.spec or crev.spec   part C -> R/w120-T72C<s>-<time>/cfwd.csv or crev.csv, ...
      `- bwx12   kernels oldread, read, asmread (cfwd) or asmread, read, oldread (crev)
go2.sh (control I, added later: the part L line twice, each time from an idle machine)
 `- rx.sh T72I<i> bwx12 SHA < like.spec   -> R/w120-T72I<i>-<time>/a6456.csv, ...
analysis: stat_k120.py, stat_bwx.py (quick statistics); facts_data.py + build_facts.py + facts_text.py + facts_text4.py -> S/FACTS.md, S/facts.json;
          make_report.py -> C/new-test-kernel/whole-chip-rerun-7200.html; test_make_report.py (tests of make_report.py)
```

Words. The project word list is in `S/FACTS.md`, lines 38 to 89 ("Words used here"). Read it. Reuse its definitions word for word when you define one of these terms: CRB, mesh 0 / mesh 1, whole chip, MT/s, read kernel, old read kernel, new read kernel, asmread, load-only loop, bw_old, bw_new, bwx12, process, interval, round, position, session, part A, part L, part C, control I.

Machine code of the kernels, for cross-checks:

- `R/kernels-20261113T181222Z/probe.txt`: objdump text of `k_read` and the other kernels of bw_new (from line 23) and bw_old (from line 155), plus the compiler flags.
- `BWX12/crb-build-1/listing.txt`: objdump text of every kernel of bwx12. `BWX12/crb-build-1/build.txt` holds the flags and the sha256 values.

## 3. Hard rules

- Do not use ssh. Do not contact CRB or any other machine.
- Do not run `go.sh`, `go2.sh`, `ra.sh`, `rx.sh`, `run_kernels.sh`, `build12.sh`, or any benchmark binary. Reading them is the job.
- You may run read-only commands (`grep`, `sed -n`, `wc`, `python3 -c`, `man`, `bash -n`) and small harmless experiments in your scratchpad folder to test what a shell construct, a regular expression or a Python expression does. Use `nproc` if you need a worker count. Never start more than 2 processes at once.
- Write only the output files that your task names (under `T/ann/` or `T/types/`, or the companion files named in your task). Change no other file. No git commands that change anything.
- The `cd` command of this shell prints a directory listing. Use absolute paths, or `cd X >/dev/null`.
- Every statement you write must follow from source text or data that you read in this task. If you cannot ground a statement, write `Insufficient data: <what is unknown>. <the file or measurement that would resolve it>.` Do not guess.
- When you are not sure what a command flag, a C library call or an Arm instruction does, look it up (`man`, `--help`, the listing files) before you write the sentence.

## 4. How to write an explanation

Reader: an engineer who knows C and performance work, but does not know shell syntax in detail, has never seen this project, and is not a native English speaker.

From the explain-bash skill (it applies to every language here, with "command" read as "statement" for C and Python):

- Turn each command into a plain sentence, not jargon. Example: `find . -name "foo"` becomes "find all the files and directories under the current folder tree whose names are `foo`".
- Fold flag meanings into the sentence. Example: `sort -u` becomes "sort the lines and drop duplicates".
- Be brief: one sentence per significant command or pipeline stage. Skip lines that need no explanation (comments that already say it, progress `echo`s, simple variable assignments).
- Mention a detail outside the main flow only when it changes behavior the reader must know, for example `set -e` (the script stops at the first failed command) or a destructive step.

Plain-English rules (the plain-english skill in your instructions applies in full). The ones that fail most often:

- No idioms, no metaphors. Use the literal verb.
- One claim per sentence. Short sentences. No semicolons.
- Every number has a unit and, where the reader cannot judge it, a clause that says what it means. Example: "`--min-ms 500` (each timed interval lasts at least 500 ms)".
- Define a term at first use: a name from the code, an abbreviation, a metric. A name that is visible in the source lines of the same row needs no definition.
- Do not cite `file:line` of another file inside a sentence. Name the other file in plain words. If a citation is needed, give it an entry in the `refs` list of the overview and write `[Ref1]` at the end of the sentence.
- A reference to a line of the same source file is allowed: "the function `state` (line 17)".

What to say for code that matters to the measurement (say it exactly, it is the reason for the review):

- What is timed and what is not. Where the clock is read. What stops a timed interval.
- How a rate is computed: which bytes are counted, which time divides them, the unit (GB = 1e9 bytes).
- For a read kernel: how many bytes one loop pass reads, how many load instructions, what happens to the loaded value (added to a sum or dropped), how the loop is unrolled, what the compiler may do with it. Check your statement against the objdump text named in section 2.
- Thread placement: which CPU a thread is pinned to, how buffers are allocated (size, huge pages, first touch).
- Order effects: which kernel runs after which, waits, checks that can stop the run.

## 5. Output format A: annotation files for a side-by-side companion

One companion needs one overview file and one annotation file per chunk. The chunk ranges are fixed in `T/manifest.json` (`chunks` of your key).

Annotation file `T/ann/<key>.c<NN>.json` (NN = chunk number, 01 for the first):

```json
{"file": "<absolute path of the source>", "start": 1, "end": 48,
 "segments": [
  {"start": 1, "end": 8, "heading": "optional title row", "text": "Explanation of lines 1 to 8."},
  {"start": 9, "end": 9, "text": "`set -u`: the script stops when it uses a variable that was never set."}
 ]}
```

- Add `"kind": "text"` at the top level when the source is a text or listing file (not code).
- The segments must cover every line from `start` to `end` exactly once, in order, with no gap and no overlap.
- One segment = the lines that do one thing. Usual size 1 to 15 lines. Above 40 lines the tool warns. Above 80 lines of code the tool refuses (400 for a text or listing file).
- A segment may have an empty `text` when its lines need no explanation (blank lines, a closing brace, a comment that says it all). Keep such segments short, or join the lines to a neighbour segment.
- `text` markup: `` `code` ``, `**bold**`, and lines that start with `- ` for a bullet list. Nothing else. No tables, no links, no HTML.
- `text` length: 1 to 4 short sentences, or up to 6 bullets. A long one-line shell command that holds several commands gets one bullet per command.
- `heading`: put one on the first segment of every top-level function (and of every large section), for example ``Function `worker`: one benchmark thread``. At most 12 words.
- A helper function is explained once, in the row of its definition, in one or two sentences. Rows that call it name it and say what the call is for.

Overview file `T/ann/<key>.overview.json`:

```json
{"file": "<absolute path>",
 "role": "at most 14 words: what this file is in the whole-chip test",
 "purpose": "One or two sentences: what the whole file does.",
 "main_flow": [{"step": "One sentence per major step, in the order it runs.", "lines": "40-45"}],
 "behavior_notes": ["Only what changes behavior the reader must know."],
 "words": [{"term": "CRB", "def": "the Arm reference server under test. It has 128 CPUs."}],
 "call_sequence": [{"depth": 0, "name": "main", "line": 496, "note": "at most 14 words"},
                   {"depth": 1, "name": "worker", "line": 446, "note": "one thread: pins, allocates, times the kernel"}],
 "functions": [{"name": "worker", "line": 446, "end": 485, "what": "at most 25 words", "calls": ["pin_cpu", "pass"], "timed_path": true}],
 "refs": [{"id": "Ref1", "path": "<path>", "what": "what this reference proves"}]}
```

- `main_flow`: walk the top-level execution path in order: arguments and environment first, then each major step. For a text or listing file this list is "how to read this file".
- `call_sequence`: the calls that happen when the file is used in the whole-chip test of section 2, in call order, as an outline (`depth` 0 = entry point). Give the function line. For a function of another file, write the name as `otherfile:function` and leave `line` out. Include the kernel functions that the test runs.
- `functions`: every function that the file defines (for a file with more than 60 functions: every function that `call_sequence` or `main_flow` names, plus the ones a reviewer of the measurement needs). `line` is the line of the definition and must show the name. `timed_path`: true when the function runs between the two clock reads of a timed interval, false when not, null when the question does not apply (analysis scripts).
- `words`: every term that the explanations of this companion use and that needs a definition.

Checks you must run before you finish (both must print OK):

```
python3 T/companion_tool.py check-ann T/ann/<key>.c<NN>.json
python3 T/companion_tool.py check-overview T/ann/<key>.overview.json
```

Do not run `build`. The main session builds the companions.

## 6. Output format B: a data explanation in Markdown

Used for data files. Your task names the output path. Write Markdown (tables allowed). Structure:

1. `## What this file is`: which program wrote it, at which step of the run, one row or line per what.
2. `## Line kinds`: a table of every kind of line in the file: how to recognise it, what it holds.
3. `## Columns`: one table per kind of row: column number, name, unit, meaning. Ground each meaning in the source line that prints the column.
4. `## Old read kernel and new read kernel in this file`: how a reader finds the rows of each kernel.
5. `## Which code reads this file`: the analysis scripts and the columns they use, and how the final rate comes from the columns.
6. `<details><summary>Words used here</summary> ... </details>`
7. `## References`: `[Ref1]` entries with path and line numbers for the source lines that you used.

A type-level explanation (one text for several files of the same format) must be true for every file of the type. Check at least the first and the last instance. An example value must name the file and the line it comes from.

## 7. Facts that earlier agents of this task established (the main session checked each one)

Use them. Every companion that touches one of these points must say the same thing.

1. How the run was started. No script of `S` holds the command. The record of the Claude Code session of 2026-11-17 holds it: `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`, line 313 (go.sh) and line 365 (go2.sh). The command was sent from the agent server with ssh, as user jhan, with no `taskset`:
   `if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi; L=~/cache-perf/results/go-T72-$(date -u +%Y%m%dT%H%M%SZ).log; nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null & pid=$!; echo "log $L pid $pid"; wait $pid; echo "go.sh exit status $?"; cat $L`
   The go2.sh command is the same with `go2-T72-` and `go2.sh`. So: the log holds standard output and error output (`2>&1`); `setsid` gave the script a session and a process group of its own; standard input was `/dev/null`. This record lies outside the project folder: say so when you cite it.
2. Two texts of bandwidth.c. The local `K13/bandwidth.c` (and the identical `cache-perf/bench/bandwidth.c`) has sha256 `f1985072...`. That is the value in `R/kernels-20261113T183218Z/probe.txt` (a build-only run of 18:32:18 UTC on 2026-11-13). The timed run of 18:12:22 UTC (`R/kernels-20261113T181222Z/probe.txt`, line 15) recorded sha256 `c1406e02...` for bandwidth.c. All three records of that day give the same sha256 for the binary bw_new (`fd7c14df...`), which is the value that ra.sh checks. So the machine code is not in doubt. The two texts differ in comment lines only (established on 2026-11-21, checked by the main session). The record of the Claude Code session of 2026-11-13, `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000 (time 2026-11-13T18:32:07Z), holds the edit: it replaced the 2 comment lines " * In k_copy it keeps all 16 loads ahead of the 16 stores. The statement adds" / " * no instruction." above `k_read` with the 5 comment lines 178 to 182 of the local text. With this edit reversed, the local text has the sha256 value `c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2`, which is the value of the runs of 18:12:10 and 18:12:22 UTC. No code line differs. So do NOT write "Insufficient data: which source lines differ": state this fact and cite the session record. `K13/bandwidth.orig.c` has the recorded value `61228754...`.
3. The FACTS.md definition of "Read kernel" says "In this sheet". In a companion write "On this page" instead. Every other reused definition stays word for word.
4. No manual pages and no Linux kernel documentation are installed on this server. You may read public documentation pages on the web (for example man7.org, gcc.gnu.org, docs.kernel.org, developer.arm.com). Never put project data, paths or names into a web request. Name the page as an external source in the references.
5. The scratchpad folder is shared by all agents. Work only in a sub-folder of it that carries the name of your unit.
6. The binary files bw_old, bw_new and bwx12 are not in the local folders. Their sha256 values are known only from the records (probe.txt, build.txt, env.txt, go.sh, ra.sh).
7. Copy to CRB and copy back. The same session record (point 1) holds these commands, all sent from the agent server. The main session read each one.
   - Line 309: `sha256sum go.sh ra.sh like.spec cfwd.spec crev.spec > local.sha` in the local folder `S`, then `tar cf - go.sh ra.sh like.spec cfwd.spec crev.spec local.sha | ssh ... 'D=~/cache-perf/w120-7200-20261117; mkdir -p $D && cd $D && tar xf - && chmod +x go.sh ra.sh && sha256sum -c local.sha ...'`. So local.sha was written on the agent server, and `sha256sum -c local.sha` then ran on CRB on the copied files.
   - Line 313: the start of go.sh (point 1).
   - Line 339: `ssh ... 'cd ~/cache-perf/results && tar cf - go-T72-20261117T221209Z.log k120-T72A?-2026* w120-T72[LC]?-2026*' | tar xf - --no-same-owner -C R/`: the copy of the log and of the result folders of parts A, L and C back to `R`.
   - Line 353: go2.sh was written, then `sha256sum go2.sh > go2.sha; tar cf - go2.sh go2.sha | ssh ... 'cd ~/cache-perf/w120-7200-20261117 && tar xf - && sha256sum -c go2.sha ...'`.
   - Line 365: the start of go2.sh. Line 377: the copy of `go2-T72-2026*.log` and `w120-T72I?-2026*` back to `R`.
8. Two texts of go.sh. Line 20 of the local `S/go.sh` was edited on 2026-11-24, after the rerun, on the instruction of the user. `fail "RUNNING file present"` became `fail "RUNNING file present, Jeremy or someone else is using CRB"`. Jeremy is another user of CRB: `/home/jhan/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md`, lines 12 and 13. No other line changed. The file still has 48 lines. The rerun ran the older text. Its sha256 is `75bc50b0...`. This value is the go.sh entry of `S/local.sha`. It is also the sha256 of the script text in line 295 of the session record of point 1. That line holds the last command that wrote go.sh before the copy to CRB. The local text has the sha256 `d68cf6c0...`. With the old line 20 put back, the local text has `75bc50b0...` again. `S/local.sha` was not changed. So `sha256sum -c local.sha` in `S` prints `go.sh: FAILED`. A new run of `build_facts.py` fails check 20 (key `sha-local`: the sha256 of the local run files against `local.sha` and `go2.sha`). It then stops at line 1461 of `facts_text4.py`, before it writes a file. Do not write `S/local.sha` or `S/go2.sha` again. They are the records of the two launches. FACTS.md prints the file time of `local.sha` in decision (h). `S/go2.sh` was not edited. It keeps the older message in lines 16 and 25. The edit was made in the local file only. The tests of the edit and a copy of the older go.sh are in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24`. The record of the Claude Code session of the edit holds the instruction (line 2153, 2026-11-24 20:27:54 UTC) and the edit (line 2245): `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl`. That session began on 2026-11-22 (UTC). The record lies outside the project folder.
