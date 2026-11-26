# Briefing for the writers of the line-by-line pages

Read this file to the end before you write anything. Then read `GLOSSARY.md` in the same folder.

## 1. The task

The user reviews the test code of a hardware benchmark project. For every code file the user wants one Markdown page that explains the file **line by line**: one table row per source line, the source at the left and the explanation at the right.

- You write the explanations. A script (`lbl.py`) copies the source lines and builds the page. You never copy source text into a file.
- You get a unit: a list of file keys. A key is the path of a file below the code folder, for example `kernels-2026-11-13/bandwidth.c`.
- Every line of every file of your unit that is not blank gets its own explanation.

## 2. Folders and tools

- `CODE` = `/home/jhan/workspace/ai-proj/arm-crb/code` (the source files. Read only.)
- `T2` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/line-by-line-2026-11-25` (this folder: tool, manifest, your output under `T2/ann/`)
- `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17` (the pages are built there by the main session, not by you)
- Notes of the project, to understand what a file is for: `/home/jhan/workspace/ai-proj/arm-crb/README.md` (one table of the tests, one table of the code folders), and the `.md` files inside the code folders (`README.md`, `DECISIONS*.md`, `DEVIATIONS*.md`, `FINDINGS.md`). Test data: `/home/jhan/workspace/ai-proj/arm-crb/tests/`.

Commands (always with the full path of the tool):

```
python3 T2/lbl.py info KEY          paths, kind of page, references that you may cite
python3 T2/lbl.py show KEY [A [B]]  source lines A to B, each with the explanation it has now
python3 T2/lbl.py old KEY           explanations of an older page of this file, when one exists
python3 T2/lbl.py seed KEY          take over explanations from an earlier or later version of the file (section 8)
python3 T2/lbl.py check KEY         test your files. It must print "OK" at the end before you finish
```

## 3. Hard rules

- Do not use `ssh`. Do not contact any other machine. The test machine is shared with other users.
- Do not run any file of `CODE`: no run script, no build script, no test, no benchmark. Reading them is the job.
- You may run read-only commands (`grep`, `sed -n`, `wc`, `python3 -c`, `bash -n`) and small harmless experiments in your scratchpad folder, to test what a shell construct, a regular expression or a Python expression does. Never start more than 2 processes at once.
- Write only your annotation files under `T2/ann/` (and scratch files in your scratchpad folder). The scratchpad folder is shared by all writers: make a sub-folder with the name of your first key and work only there. Change no other file. Do not run `lbl.py build`, `build-all`, `manifest` or `index`. No git command that changes anything.
- The `cd` command of this shell prints a folder listing. Use absolute paths.
- Do not start other agents.
- Every statement must follow from text that you read in this task: the source line, the rest of the file, a file that it reads or calls, or a note of the project. When you cannot ground a statement, leave it out. Do not guess what a past run did or measured.
- When you are not sure what a command flag, a C library call, a Python function or an Arm instruction does, look it up before you write the sentence (`--help`, the Python `help()`, a public documentation page if you have a web tool). Never put a path, a name or data of this project into a web request.

## 4. What an explanation must do

Reader: an engineer who knows C and performance work in general. The reader does not know shell syntax in detail, has never seen this project, and is not a native English speaker.

The rules of the user's skill "explain-bash" apply to every language here. Read "command" as "statement" for C and Python:

- Turn each command into a plain sentence, not jargon. Example: `find . -name "foo"` becomes "find all the files and folders under the current folder tree whose names are `foo`".
- Fold the meaning of a flag into the sentence. Example: `sort -u` becomes "sort the lines and drop duplicates".
- Be brief. One or two short sentences for a normal line. A long line that holds several commands gets one short sentence per command, in the order of the line.
- Say **what the line does and why it is there**. Do not only repeat its words. "Calls `foo`" is not an explanation. "Pins the thread to its CPU (`pin_cpu`)" is one.
- Every line that is not blank gets a row, also a line that is simple:
  - A comment line: start with `Comment:` and give its message in plain words. Define a term of the comment that a newcomer cannot know. When the code does not do what the comment says, say so.
  - A line that only closes something (`}`, `fi`, `done`, `)`): name what it closes: "Ends the function `worker`." or "Ends the loop of {L40}."
  - A line that continues a statement from the line before: say what this line adds: "Continues the call of {L60}: the output file and the error file."
  - A line of a long text literal (HTML, CSS, a help text, a table of values): say what this line of text is for: "Text of the page: the heading of section 3." or "CSS: table cells get a border of 1 px."
  - A blank line gets no explanation. The tool skips it.
- A helper function is explained in the row of its definition, in one or two sentences. A row that calls it names it and says what the call is for at this place.
- Give the meaning of a number: its unit and what it stands for. Example: "`--min-ms 500`: each timed interval lasts at least 500 ms."
- For a line of a test: say what the test proves and why that matters, not only what it compares.

Say these things exactly. They are the reason for the review:

- What is timed and what is not. Where the clock is read. What ends a timed interval.
- How a rate is computed: which bytes are counted, which time divides them, the unit (GB = 1e9 bytes).
- For a read, write or copy loop: how many bytes one loop pass handles, how many load or store instructions, what happens to a loaded value (added to a sum, or dropped), how the loop is unrolled.
- Thread placement: which CPU a thread is pinned to, how a buffer is allocated (size, huge pages, first write).
- Order effects: which step runs after which, waits, checks that can stop the run, exit statuses.
- For an analysis script: which file and which column a number comes from, and how it is combined (minimum, median, sum, ratio).

Language notes:

- C: for a preprocessor line say what it defines or includes and what that is used for. For a struct field say what it holds and its unit. For a NEON intrinsic or an assembly line say what the instruction does to which register or memory (for example "`vld1q_u8(p)` loads 16 bytes from the address `p` into a vector register"). For a `printf` say what the printed line means, column by column when it is a data row.
- Bash: explain every pipeline stage, redirection (`2>&1`, `< /dev/null`), parameter expansion (`${X:-default}`), test (`-e`, `-s`, `-x`) and `set` option at its first use in the file. Later uses can be shorter.
- Python: for a regular expression say what text it matches and what each group holds. For a format string say what it prints. For a comprehension say what list or dictionary it builds.

## 5. Plain English

These rules are checked by a reviewer. Most are also checked by the tool.

- No idioms, no metaphors, no wordplay, no uncommon words. Use the literal verb. Bad: "bails out", "kicks off", "under the hood", "boilerplate", "sanity check", "on the fly", "via". Good: "stops", "starts", "through".
- One claim per sentence. Short sentences. No semicolon. When a sentence holds "because", "since", "which means" or "so that", try to split it: first the fact, then "So ...".
- Every number has a unit and, when the reader cannot judge it alone, a clause that says what it means. Mark an estimate with "est.".
- Define a term at its first use: a name from another file, an abbreviation, a metric. A name that is visible in the source line of the same row needs no definition. Terms that the page uses many times go into the list "Words used here" (section 7.2). Take the definitions of `GLOSSARY.md` word for word.
- "Kernel" means the inner loop of a benchmark that reads, writes or copies memory. Write "Linux kernel" for the operating system kernel.
- Do not write "simply", "just", "basically", "obviously", "of course".
- Do not cite `file:line` of another file inside a sentence. Name the other file in plain words ("the file `hw.sh` defines `hw_init`").

## 6. Markdown rules of an explanation (the checker enforces them)

An explanation is one line of plain text with code spans. The tool puts it into a table cell.

- Put every piece of code, file name, variable, command, option and literal value in backticks: `` `sort -u` ``, `` `$HOME` ``, `` `threads120.csv` ``.
- A code span that holds a backtick needs two backticks at each end and spaces inside: ``` `` echo `date` `` ```.
- Outside a code span the text must not hold any of these characters: `|` `<` `>` `*` `_` `~` `$` `\` `^` `&` `;` `@` `[` `]` `{` `}`, and no character that is not plain ASCII. The two exceptions are the line reference `{L12}` and the citation `[Ref3]`. So: no bold, no italics, no links, no HTML, no arrows. Write "above 2" and not a comparison sign.
- A line of the **same file** is named with a token: `{L12}` for one line, `{L12-15}` for a range. The tool prints "line 12" and "lines 12 to 15". The first and the last line of a token must not be blank lines. Never write a line number of this file as plain text ("line 12" is an error).
- Never give a line number of another file. Name the file and the function or variable.
- A citation `[RefN]` is allowed only when `lbl.py info KEY` lists that reference (pages that keep their older sections), or when your own page file lists it (new pages, section 7.2).
- Inside a code span, a backslash directly before `|` cannot be shown in a table. The checker tells you. Describe that piece in words. (A source line that holds this pair is handled by the tool. Only for such a line the explanation may hold it too.)
- At most about 700 characters per explanation. Most rows need 60 to 250.

## 7. Files that you write

### 7.1 The explanations: `T2/ann/KEY.ann`

Plain text, one explanation per line, in this form (line number, colon, one space, text):

```
@part 1-9 Header comment and settings
1: Tells Linux to run this file with `bash`.
2: Comment: the usage. The script takes one argument, the name of the run.
9: `set -u`: the script stops when it uses a variable that was never set.
@part 10-34 Function `worker`: one benchmark thread
10: Starts the function `worker`. Each thread of the benchmark runs it once.
```

- A `@part A-B title` line starts a part. The page shows one table per part, under the title. Parts must cover the file from line 1 to the last line, in order, without a gap: a blank line between two functions belongs to one of the two parts. A file of more than 80 lines needs parts. A part has at most 200 lines. Use one part per function or per logical block. Give a long function several parts ("`main`: reading the arguments", "`main`: the timed loop"). A title has at most 90 characters and follows the rules of section 6.
- For a large file write several files in place of one: `T2/ann/KEY.ann.d/01.ann`, `02.ann`, and so on, each with about 200 to 400 source lines. The tool reads them in name order. Write the next one only after `check` shows no error other than "lines have no explanation".
- Blank lines of the annotation file are ignored. Everything else must be a `@part` line or an `N: text` line.

### 7.2 The page sections: `T2/ann/KEY.page.md`

Only for a file whose `info` says `mode new`. (For `mode section` and `mode copy` the page keeps the sections of an older page. Write no page file for them.)

Use exactly these headings, in this order. The first three are required.

```
## Short version: purpose

At most three sentences. What the whole file does, and what it is for in the tests. A newcomer must follow them.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **`bw_old`**: ...

## Main flow

1. One sentence per major step, in the order it runs ({L10-14}).
2. ...

## Behavior a reader must know

- Only what changes behavior that the reader must know: what stops the run, what is deleted, what is timed, exit statuses.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
```

- "Words used here": every project name, abbreviation and metric that the page uses and that a newcomer cannot know. One line per term, in the form `- **Term**: definition`. Take the definition from `GLOSSARY.md` word for word when the term is there.
- "Main flow": walk the top-level execution path in order: arguments and environment first, then each major step. For a C file start at `main`. For a file of tests: the groups of tests in file order. For an input file (a `.spec` or `.txt` file): how to read the file. Give the lines of each step with a token.
- Do not give a helper function its own step. Say what a helper does in one clause at the step that calls it.
- "Behavior a reader must know" and "References" may be left out when you have nothing to say.
- The rules of section 5 and 6 apply to every line. Each list item is one line. `**` is allowed only around the term of a "Words used here" line.

## 8. How to work

For each key of your unit, in the order that your task gives:

1. `python3 T2/lbl.py info KEY`. If it says "equal to another file", skip the key.
2. Read the whole source file first (the Read tool shows line numbers). Read the files that it calls or reads when you need them to explain a line. Read the notes of its folder.
3. If `info` shows `old_page`: run `python3 T2/lbl.py old KEY`. It prints the explanations of the older page, in groups of lines. A reviewer has checked them. Use every fact of them that fits: your row for a line must not say less about the measurement than the older text said. Rewrite them as one row per line, in one line of text each (a table cell cannot hold a list). When `old` prints "CAUTION: older text", the file was changed later: the older line numbers differ (the map is printed), and the new lines need new explanations.
4. If `info` shows `seed_from` and that file is finished: run `python3 T2/lbl.py seed KEY`. It writes `T2/ann/KEY.seed` (do not edit that file). Every line that is equal in both files gets the explanation of the other file, with the line tokens moved. `show` marks such a line with `~`. Lines marked `?` need your explanation. Under some `?` lines `show` prints a text with the mark `!`: the row of the other file, which the tool did not take over (it names the other version, or it holds a citation). Its line tokens are already moved to the lines of this file. `{L?}` stands for a line that this file does not have: write that part again. Adapt such a text to this file. Do not copy it blindly. A line in your own `.ann` file replaces the seed of that line. Read every seeded explanation that lies within 10 lines of a `?` line, and the first and last row of every function. Replace a seeded text that is not true in this file. `seed` also writes `T2/ann/KEY.parts-proposal`: copy its `@part` lines into your `.ann` file and correct them.
5. Write the annotation (section 7.1), and the page file when the mode is `new` (section 7.2).
6. `python3 T2/lbl.py check KEY` until it prints `OK`. Fix every error. Read the warnings and shorten or split where it is easy.
7. Second pass. Read again, beside the source, every row that touches a point of the list "Say these things exactly" in section 4, every row of a line with a regular expression, and every row that you were not sure about. Use `show KEY A B`. Correct what is wrong.

Keep your own notes short. Do not print large parts of the files into your answer.

8. Rows that other versions take over. The runners and their scripts exist in several versions (`bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12`, `bwx13`, and the same for `build*.sh`, `run_bwx*.sh`, `schedule*.py`, `check_listing*.py`, the tests). When your file is one of them, the tool gives your row to every equal line of the other versions. So write each row in a way that stays true there: say "the runner" or "this program" in place of the version name, and name the version (`bwx12`) only for a fact of that version alone, such as its machine code, its build record or its results. Do not say how many kernels or options the whole program has in the row of a line that does not show it.

## 9. Background

The tests ran on CRB, an Arm reference server with 128 CPUs, from 2026-10-30 to 2026-11-17. They measure how fast the cores read, write and copy memory, and where the limits are. The table "Tests" of the repo README names each test and its code folder. In short:

- `bench`: the first benchmarks (`latency.c`: load latency per cache level. `bandwidth.c`: streaming throughput. `homelat.c`: latency of a line that another core holds) and their run scripts.
- `cread-2026-11-12`, `kernels-2026-11-13`: a rewrite of the read, write and copy loops of `bandwidth.c`. `bandwidth.orig.c` holds the old read kernel, `bandwidth.c` the new one. `run_kernels.sh` builds both (`bw_old`, `bw_new`) and runs them.
- `new-test-kernel`: scripts and analysis of the test plan of 2026-11-13 (parts A, B and C).
- `bwx-2026-11-13` to `bwx13-2026-11-15`: the runner programs `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12`, `bwx13`. Each is a later version of the one before. A runner times a sequence of kernels in one process and prints one row per thread. Each folder holds the source, a self-test, a build script, run scripts, schedule generators and their tests, and a check of the machine-code listing.
- `w120-2026-11-15`: the 120-thread investigation: `rx.sh` starts a runner once per line of a spec file. `r*.spec` and `rc*.spec` are spec files. `sets*.txt` are lists of counter events. `an*.py` are small analysis scripts. `robsize` measures the size of the out-of-order window of a core.
- `asct-2026-11-16`: a cross-check with ASCT, a measurement tool from Arm.
- `w120-7200-2026-11-17`: the whole-chip rerun at a memory speed of 7200 MT/s. `go.sh` is the driver, `ra.sh` runs part A, `go2.sh` is a control run. The Python files build the facts sheet (`FACTS.md`) and the report page.
- `manual-run`: one command that starts the whole-chip test.
- `hwwatch-2026-11-24`: the hardware record (clock rate of the cores, throttle flags, power) that the run scripts call since 2026-11-24.

The call sequence of the whole-chip test (on CRB, no root, CPUs 0 to 119):

```
go.sh  (driver, 3 sessions, then one more part C process)
 |- ra.sh T72A<s>                         part A: threads120.csv, probe.txt
 |    |- bw_old  (from kernels-2026-11-13/bandwidth.orig.c)   old read kernel
 |    `- bw_new  (from kernels-2026-11-13/bandwidth.c)        new read kernel
 |- rx.sh T72L<s> bwx12 SHA < like.spec   part L: a6456.csv, env.txt, launches.txt, stderr.txt
 |    `- bwx12   (from bwx12-2026-11-15/bwx12.c, built by build12.sh)
 `- rx.sh T72C<s> bwx12 SHA < cfwd.spec or crev.spec   part C
go2.sh (control run: the part L line twice, each time from an idle machine)
ra.sh, rx.sh and run_kernels.sh call the functions of hwwatch-2026-11-24/hw.sh (hw_init, hw_begin, hw_end, hw_done)
```

## 10. Facts that every page must state the same way

1. The files in `CODE` are the latest texts. Five scripts were changed on 2026-11-24, after all tests: `go.sh`, `go2.sh` and `ra.sh` in `w120-7200-2026-11-17`, `w120-2026-11-15/rx.sh` and `kernels-2026-11-13/run_kernels.sh`. They now call `hw.sh`, and the check of a fixed boot id was removed from `go.sh` and `go2.sh`. No test has run these texts. The files of `hwwatch-2026-11-24` were also written on 2026-11-24. So never write that a past run did what one of these new lines does.
2. A fact about a past run (a value, a time, a count of result files) may stand in an explanation only when it comes from the older explanation of the same line and one of two things holds. Either a citation `[RefN]` that `info` lists proves it. Or you open the file that holds the fact now, you see the fact yourself, and the sentence names that file in plain words (for example "In the file `facts.json` the field `kernel_before` is `read` for every record of `bx7`."). Do not drop an older sentence that you can prove in this way. Add no fact that the older explanation did not have. A fact that you cannot find in a file stays out: list it in your report.
3. The compiled programs (`bw_old`, `bw_new`, `bwx12` and the others) are not in any local folder. Their checksums are known only from records.
4. GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20). `256M` as a buffer size means 256 MiB = 268435456 bytes.
5. The marker file is `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
6. Our runs use the CPUs 0 to 119 only. CPUs 0 to 63 sit on mesh 0, CPUs 64 to 127 on mesh 1 (the two halves of the chip).

## 11. Examples

Two finished files of the main session. Read them before you write:

- `T2/ann/w120-2026-11-15/rx.sh.ann` (Bash, `mode copy`: no page file).
- `T2/ann/manual-run/run.sh.ann` and `T2/ann/manual-run/run.sh.page.md` (Bash, `mode new`).

C, lines 107 to 123 of `kernels-2026-11-13/bandwidth.orig.c` (the source is shown here only for the example):

```
107 static void pin_cpu(int cpu)
108 {
109     cpu_set_t set;
110     CPU_ZERO(&set);
111     CPU_SET(cpu, &set);
112     if (sched_setaffinity(0, sizeof set, &set) != 0) {
113         perror("sched_setaffinity");
114         exit(2);
115     }
116 }
117
118 static uint64_t *alloc_buf(uint64_t bytes)
119 {
120     size_t len = (bytes + HUGE_BYTES - 1) & ~(HUGE_BYTES - 1);
121     uint8_t *raw = mmap(NULL, len + HUGE_BYTES, PROT_READ | PROT_WRITE,
122                         MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
123     if (raw == MAP_FAILED) {
```

```
@part 107-117 Function `pin_cpu`: limit the calling thread to one CPU
107: Starts the function `pin_cpu`. It limits the calling thread to the CPU with the number `cpu`.
108: Opens the body of `pin_cpu`.
109: `set`: a CPU set, the Linux type for a list of CPUs.
110: Empties the set.
111: Adds the CPU `cpu` to the set. The set now holds this one CPU.
112: `sched_setaffinity` with the first argument 0 applies the set to the calling thread. After the call Linux runs the thread on this CPU only. A return value other than 0 means that the call failed.
113: On failure: `perror` prints the word `sched_setaffinity` and the reason that Linux gave.
114: On failure: the whole program ends with exit status 2.
115: Ends the `if` of {L112}.
116: Ends the function `pin_cpu`.
@part 118-134 Function `alloc_buf`: one buffer, aligned for huge pages
118: Starts the function `alloc_buf`. It reserves a buffer of at least `bytes` bytes and returns its address.
119: Opens the body of `alloc_buf`.
120: `len`: `bytes` rounded up to the next multiple of `HUGE_BYTES`. The expression adds `HUGE_BYTES - 1` and then clears the low bits. This gives the right value when `HUGE_BYTES` is a power of two.
121: `mmap` asks Linux for `len + HUGE_BYTES` bytes of new memory. The extra `HUGE_BYTES` bytes make it possible to move the start to an aligned address later. `PROT_READ | PROT_WRITE`: the program may read and write the memory.
122: Continues the call of {L121}. `MAP_PRIVATE | MAP_ANONYMOUS`: the memory belongs to this process and has no file behind it. `-1` and `0` are the two file arguments, which are not used here.
123: Tests whether `mmap` failed.
```

Python, three lines of `w120-7200-2026-11-17/stat_k120.py`:

```
21: `HDR`: a compiled pattern for the header line that starts each process in `threads120.csv`. Its 8 groups hold the binary, the kernel, the thread count, the CPU list, the buffer size, the round, the load value and, when the line has one, the UTC time.
24: Starts the function `load`. It reads the file `threads120.csv` of one folder.
27: `procs`: the list of the processes found so far. `cur`: the process whose interval lines are read now. It is `None` before the first header line.
```

## 12. Your report

End with a short report, no file contents:

- For each key: the number of lines explained and the last line of `check` (it must say `OK`).
- Rows that you could not ground and how you wrote them.
- Places where a comment of the source does not fit the code.
- For a seeded file: how many seeded rows you replaced, and why.
- Anything that the main session must know (a tool problem, a source file that looks damaged).

## Rule of this server: the allowed CPUs

- Every shell command of an agent is pinned to CPUs 26 to 31 of this server. Never change the allowed CPUs of a process: no `taskset`, no `numactl`, no `os.sched_setaffinity`, also not for a short experiment.
- To learn what such a command does, read its manual page (`man taskset`, `taskset --help`).
- Keep the number of busy processes at 6 or fewer. Size a worker pool from `nproc`.
