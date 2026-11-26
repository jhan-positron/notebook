# `test_q1.py` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/test_q1.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 431 lines, 29036 bytes).
- sha256 of the source when this page was built: `34d347edd236bc957d1bd4ebb21ca38d2633ca3c92212141ae29872bbdcef6bb`.

## Short version: purpose

`test_q1.py` holds the 14 tests of the page builder `make_q1_html.py`. Twelve tests write result folders with invented rates in the format of the run script `run_bwx.sh` and of the runner `bwx`, build the page from them, and compare values and sentences of the page with what the invented rates must give. Two more tests run only when the real result folders lie in the working tree, and compare the page with a saved output of the analysis script and with values typed into the test.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Page builder**: the script `make_q1_html.py`. This file imports it under the short name `M` [Ref3].
- **Generated page**: the HTML page that the page builder writes: the result page for question Q1 of the plan.
- **Plan**: the test plan of 2026-11-13, the file `plan.md`. Its rule 10 asks for a result per session. Its rule 11 allows five result words [Ref1].
- **Handoff note**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the result rows and its section B.10 the numeric decision rules [Ref2].
- **Q1**: the first question of the plan: why one thread with a buffer of 8 MiB behaves differently from the other buffer sizes [Ref1].
- **Parts B, C and D of the plan**: Part B uses the runner `bwx`. Part C repeats steps of Part B with core counters. Part D needs root rights.
- **Step**: one measurement of the plan with a name such as B1. The run script writes one result folder per step.
- **B1**: step: the kernels `copy` and `asmcopy` are compared inside one process, with the A/A pair `asmcopy2` and `asmcopy` [Ref1].
- **B4**: step: one process times `asmread` many times on one buffer of 8 MiB, and the page state is read before every interval [Ref1].
- **B6**: step: `oldread` at 8 MiB and at 1 MiB in one process, with the A/A pair `oldread2` and `oldread` [Ref1].
- **B9**: a step of the second question of the plan that runs 120 threads. The page builder uses only its header lines and its `env.txt`, for the system load.
- **C1**: step: the schedule of B4, run with the option `--count`, which makes the runner read core counters [Ref2].
- **Level, low, high**: a level is the word of the plan for one of two rates of a loop that only loads, at 8 MiB with one thread. An `asmread` interval at 8 MiB has the label low for a rate below 69.0 GB/s and the label high for a rate above 70.5 GB/s. The plan calls the two limits provisional [Ref1].
- **H1**: hypothesis: the old read kernel is limited inside the core at every cache size, and its rate at 8 MiB does not depend on the level [Ref1].
- **H2**: hypothesis: the low level can change to the high level while the loop runs, and the high level can stay for the next process [Ref1].
- **H3a**: hypothesis: huge-page coverage decides the level. The low level is a buffer that is not fully on pages of 2 MiB [Ref1].
- **H3b**: hypothesis: the physical address of the pages decides the level [Ref1].
- **H4, H5, H6**: three hypotheses of the plan on the copy difference, the difference between the rates of the C copy kernel and of the assembly copy kernel at 8 MiB with one thread. H4: it comes from something that differs between processes, and not from the kernel code. H5: it comes from the instruction order of the C loop. H6: it comes from the address of the loop [Ref1].
- **Bounded prediction**: the one statement of a hypothesis that a step tests, as the plan words it.
- **The five words**: the result words of rule 11 of the plan: "rejected" (the bounded prediction failed in both sessions), "not rejected", "not observed", "not resolved" and "not tested" [Ref1].
- **Session (of the plan)**: one run of all steps on CRB. The plan asks for at least 2 sessions some hours apart. The tests name their sessions `s1` and `s2`.
- **Strong session**: the word of this file for an invented session in which every bounded prediction that can fail does fail (lines 69 to 74).
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`oldread`, `oldread2`, `oldread@1M`**: the old read kernel in the runner, a second copy of the same source, and the entry that runs `oldread` on the first 1 MiB of the buffer.
- **`copy`, `asmcopy`, `asmcopy2`**: three copy kernels of the runner: the C copy kernel, the copy kernel written in assembly, and a second copy of the source of `asmcopy`.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Invented folder**: a folder that the function `folder` of this file writes in the form of a result folder. Its rates are invented and are no measurement.
- **Block**: the text of one process in the csv file of a step: the header line and the rows that the runner prints. The function `block` of `test_analyze_bwx.py` writes it from a rate function [Ref4].
- **Rate function**: a small function that gives the invented rate in GB/s for a round, a position, an entry, a thread and a CPU.
- **Header line**: the line that the run script writes before the output of each process. It starts with `-- step` and holds the step, the tag, the load values and the arguments of the runner.
- **Tag**: the name that the run script gives a process, for example `8M-cpu2-p1`.
- **`P` row**: a row with the page state of one buffer, read before an interval. Counted from 1 with the row letter as field 1, field 6 is `kB_total`, field 7 is `kB_huge`, and fields 10 and 11 are the system counters `thp_collapse_alloc` and `pgmigrate_success` [Ref2].
- **`C` row**: a row with the counter values of one thread and interval: the enabled time, the running time and the CPU time in ns, and one count per event [Ref2].
- **`env.txt`, `launches.txt`, `stderr.txt`**: three more files of a result folder: the state of the machine at the start and the end of the step, one block of load readings per launch, and the error output of the runner.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Reference interval**: an interval of `asmread` at the buffer size of the process, timed before and behind every compared pair.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair, pair value**: a pair is two neighbouring intervals of two compared entries between the same two reference intervals. The pair value is the rate of the first-named entry minus the rate of the second, in GB/s.
- **A/A pair, A/A spread**: an A/A pair is a pair of the two copies of one loop. The A/A spread of a CPU is the largest absolute `e` of its processes.
- **`d`, `e`**: the two values of one process. `d` is the median of its pair values of the two compared entries. `e` is the median of its A/A pair values.
- **Resolved**: the word of the plan for a difference whose absolute median is larger than the A/A spread and that has one sign in all processes [Ref1].
- **Rule, description**: the rule is the decision rule of the analysis script. At 8 MiB it uses only stable processes. The description is what the page builder computes for all complete processes. It never changes a word of the rule.
- **Flag of a session**: the result of one session for one hypothesis in the analysis script, for example `fail` when the bounded prediction failed.
- **Open item**: a text of the box "Open for the user" of the generated page. It gives two readings of a result and leaves the choice to the user.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Huge-page coverage**: `kB_huge` of `kB_total` of a `P` row. It is full when the two are equal.
- **Case (a)**: a result of step B4 that contradicts H3a: one CPU has at least 10 low and at least 10 high intervals with full coverage [Ref2].
- **Position effect**: the rate of a loop depends on the loop that ran directly before it in the sequence.
- **Analysis script**: the file `analyze_bwx.py`. The page builder imports its parser and its decision rules [Ref5].
- **`D`**: the dictionary with all computed values of a page. The function `make` of the page builder returns it with the page text.
- **`T`**: the short name under which this file imports `test_analyze_bwx.py`.
- **Visible text**: the page text without its style sheet, its tooltips and its tags (lines 56 to 60).
- **Tooltip**: a text that a browser shows when the mouse pointer is over an element.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **UTC**: Coordinated Universal Time.

## Main flow

1. The first lines import the page builder and the row writer of `test_analyze_bwx.py`, and set the banner text, the option `--keep` and the folder for the test files (lines 10 to 21).
2. Five helpers follow: `folder` writes one invented folder, `page` builds a page from such folders, `word` finds one row of the hypothesis table, `visible` gives the visible text, and `near` compares two numbers (lines 24 to 64).
3. `strong_session` writes the three folders of a session in which the predictions of H1, H3a and H4 fail (lines 69 to 74).
4. Two tests cover the words over the sessions: one session never gives "rejected" (lines 77 to 95), and the two readings of H3a stand side by side (lines 98 to 116).
5. Three tests cover the level limits: a case near a limit is marked (lines 119 to 135), a process that is not stable is described and not decided (lines 138 to 162), and a size without a level uses every process (lines 165 to 171).
6. One test covers the position effect of step B6 (lines 174 to 212).
7. Three tests cover the page state, the counters and missing data: the counter increases and level changes of B4 (lines 215 to 243), the observation on the two refill counts (lines 246 to 270), and missing steps with Part D (lines 273 to 284).
8. Two tests cover the section on the system load (lines 287 to 314) and the columns and markers of tables and charts (lines 317 to 328).
9. `check_page_rules` holds the page rules that a script can check. One test applies them to three kinds of input, and then tests that the command line writes a page that holds the banner (lines 331 to 361).
10. Two tests run on the real result folders when they exist: session 1 alone (lines 364 to 388) and both sessions (lines 391 to 418).
11. The start of the script runs every function whose name starts with `test_`, in the order of the names, removes the temporary folders and prints the counts (lines 421 to 431).

## Behavior a reader must know

- Every rate of the first twelve tests is invented. Their pages carry a banner that says so (line 18). These tests prove what the page builder does with given rows. They prove nothing about CRB.
- A test fails through an `assert`. The first failed `assert` stops the script with a Python error. Then the later tests do not run, the temporary folders stay, and the result line of line 431 is not printed.
- The tests run in the order of their names, not in the order of the file (line 422).
- The two tests on real folders look for a folder `results` two levels above the folder of the page builder, and the second also for two text files in the folder `new-test-kernel` there (line 367, lines 394 to 397). In this repo that place is the folder `code`, which has no folder `results`. So both tests take the path that prints the skip line here (lines 371 to 373, lines 400 to 402). A skipped test is counted apart and not as passed.
- The expected values of the two tests on real folders are typed into this file (lines 381 to 387, lines 405 to 417). This page reports them as what the test expects, not as results.
- The import of line 15 needs the page builder, and the page builder needs `analyze_bwx.py` at a path of the working tree. In this repo that path does not exist, so the import works only when the folder of `analyze_bwx.py` is on the module search path of Python in another way.
- Some comparisons cannot fail. Both texts of line 153, the first text of line 112 and the first text of line 162 stand on every page. The first text of line 268 stands on no page, and the test asks that it is absent.
- No invented folder holds a process of the steps B2, B3 or C2. So the sections of B2 and B3 with data, a word of the rule for H5 and H6, and the comparison of the two copy loops in step C2 run only in the two tests on real folders.
- `page` calls `M.make` with the default path of the file of loop offsets. No test looks at the table of loop offsets.
- Without `--keep` the test writes only below a new temporary folder and removes it at the end (line 20, lines 428 to 429). With `--keep DIR` the invented folders and all pages stay in `DIR`.
- The file does not set an exit status itself. Python ends with status 0 after the last line, and with a status other than 0 after an error.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/test_q1.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (431 lines, 29036 bytes, sha256 `34d347edd236bc957d1bd4ebb21ca38d2633ca3c92212141ae29872bbdcef6bb`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: what the tests do (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_q1.py [--keep DIR] - tests of make_q1_html.py. Run: python3 test_q1.py` | Starts the docstring of the file. It ends in line 9. This line gives the usage, with the optional `--keep DIR`, and says what the file is: the tests of the page builder `make_q1_html.py`. It is run as `python3 test_q1.py`. |
| 4 | `The tests write result folders in the format of run_bwx.sh and bwx (handoff B.3) with INVENTED rates, build the` | Docstring: the tests write result folders in the format of the run script `run_bwx.sh` and of the runner `bwx` (section B.3 of the handoff note), with invented rates. The sentence goes on in line 5. |
| 5 | `page from them and assert the computed values and the words. Each test says WHY its rule matters.` | Docstring: the tests build the generated page from these folders and test the computed values and the words. Each test says why its rule matters. |
| 6 | `The row writer is the one of test_analyze_bwx.py (function block), so the format is the format that the tests of` | Docstring: the rows are written by the function `block` of `test_analyze_bwx.py`. So the format is the one that the tests of the analysis script already use. |
| 7 | `the analysis already use. The last test runs on the real session 1 folders if they exist on this machine.` | Docstring: by its words the last test runs on the real folders of session 1, if they exist on this machine. The file has two tests on real folders: `test_real_session_1` (line 364) and `test_real_two_sessions` (line 391). The tests run in the order of their names (line 422), so these two are not the last to run. |
| 8 | `With --keep DIR the synthetic folders and pages stay in DIR.` | Docstring: with `--keep DIR` the invented folders and the pages stay in the folder `DIR`. |
| 9 | `"""` | Ends the docstring. |

### Imports and settings (lines 10 to 22)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `import html, json, os, re, shutil, sys, tempfile` | Imports seven modules of the Python standard library: `html` (decodes HTML entities), `json` (reads a JSON file), `os` (paths and files), `re` (regular expressions, which are patterns for text), `shutil` (removes folder trees), `sys` and `tempfile` (creates temporary folders). |
| 12 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled copies of the modules that it imports from here on. So the imports leave no folder `__pycache__` in the code folders. |
| 13 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the full path of the folder that holds this file. |
| 14 | `sys.path.insert(0, HERE)` | Puts that folder at the front of the module search path of Python. So line 15 finds `make_q1_html.py`. |
| 15 | `import make_q1_html as M                 # noqa: E402  (puts the folder of analyze_bwx.py on the path)` | Imports the page builder under the short name `M`. Comment: this import puts the folder of `analyze_bwx.py` on the search path. `test_analyze_bwx.py` lies in the same folder. `noqa: E402` tells a style checker not to report an import that does not stand at the top of the file. |
| 16 | `import test_analyze_bwx as T             # noqa: E402  block(), b1(), b4(), b6(), copy_rate(), b6_rate()` | Imports `test_analyze_bwx.py` under the short name `T`. Comment: the names that this file takes from it: `block`, `b1`, `b4`, `b6`, `copy_rate` and `b6_rate`. The import runs none of its tests. It creates the temporary folder `T.TMP`, which line 430 removes. |
| 18 | `BANNER = 'SYNTHETIC TEST DATA. Every rate on this page is invented by test_q1.py. It is not a measurement.'` | `BANNER`: the text of the banner on every page that the tests build from invented folders. It says that the page holds synthetic test data, that every rate on it is invented by `test_q1.py`, and that it is not a measurement. The pages of the two tests on real folders get no banner (line 374, line 403). |
| 19 | `KEEP = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None` | `KEEP`: the argument behind `--keep` on the command line, or `None` without that option. An option `--keep` without a folder name behind it stops the script here with an error. |
| 20 | `ROOT = KEEP or tempfile.mkdtemp(prefix='q1-test-')` | `ROOT`: the folder for the invented result folders and the pages. It is `KEEP` when that is given. If not, it is a new temporary folder whose name starts with `q1-test-`. |
| 21 | `N = [0]` | `N`: a list with one number, a counter that starts at 0. A function can change the number inside the list without a `global` statement. |

### Helpers `folder`, `page`, `word`, `visible` and `near` (lines 23 to 66)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `def folder(session, step, blocks, load='0.52 0.40 0.30 1/913', end='2026-01-01T00:10:00Z', start='2026-01-01T00:00:00Z', busy=''):` | Starts the function `folder`. It writes one invented result folder of one step and returns its path. `blocks` holds the texts of the processes. `load` is the text of four load values: load averages of 0.52, 0.40 and 0.30 tasks, and 1 runnable task of 913 tasks. `start` and `end` are the UTC times of the step. `busy` is an extra process line for `launches.txt`. |
| 25 | `    """One result folder of one step: <step>.csv, env.txt, launches.txt, stderr.txt."""` | Docstring: one result folder of one step with its four files: the csv file of the step, `env.txt`, `launches.txt` and `stderr.txt`. |
| 26 | `    N[0] += 1` | Adds 1 to the counter. |
| 27 | `    d = os.path.join(ROOT, 'case%03d' % N[0], session, '%s-20260101T0000%02dZ' % (step, N[0] % 60))` | `d`: the path of the folder: `ROOT`, a folder `case` with the counter in 3 digits, the session name, and a name in the form of a real result folder. That name holds the step, a hyphen and a time text whose last two digits come from the counter. |
| 28 | `    os.makedirs(d)` | Creates the folder and all folders above it. |
| 29 | `    with open(os.path.join(d, step + '.csv'), 'w') as fh:` | Opens the csv file of the step for writing. |
| 30 | `        fh.write(''.join(blocks))` | Writes all blocks, one behind the other. |
| 31 | `    with open(os.path.join(d, 'env.txt'), 'w') as fh:` | Opens the file `env.txt` for writing. |
| 32 | `        fh.write('## host=test utc=%s loadavg=%s 123 logins=0 step=%s steps=%s\n## end utc=%s loadavg=0.40 0.40 0.30 1/913 456\n' % (start, load, step, step, end))` | Writes two lines in the form of the run script. The first holds the host name `test`, the UTC time `start`, the load values with a fifth field, 0 logins and the step. The second starts with `## end` and holds the UTC time `end` and fixed load values. |
| 33 | `    with open(os.path.join(d, 'launches.txt'), 'w') as fh:` | Opens the file `launches.txt` for writing. |
| 34 | `        for b in blocks:` | Loop over the blocks. |
| 35 | `            tag = b.split()[4]` | `tag`: the fifth word of the block. It is the tag in the header line of the process. |
| 36 | `            fh.write('== %s.csv %s utc 12:00:00 loadavg %s logins 1\n%%CPU USER     COMMAND\n 100 tester   ps\n%s 0.3 root     kworker/1\n' % (step, tag, load, busy))` | Writes the block of one launch: the launch line with the csv name, the tag, a fixed time, the load values and 1 login, then the title line of `ps`, then a line for `ps` itself with 100 % under the account `tester`, then the text `busy`, then a line for the Linux kernel thread `kworker/1` with 0.3 % under the account `root`. The text `%%` in the format gives one percent sign. |
| 37 | `    open(os.path.join(d, 'stderr.txt'), 'w').close()` | Creates an empty file `stderr.txt`. |
| 38 | `    return d` | Returns the path of the folder. |
| 41 | `def page(spec):` | Starts the function `page`. It builds one page from invented folders. |
| 42 | `    """spec: {session: [folders]} -> (D, html text)."""` | Docstring: `spec` maps a session name to its folders. The result holds the values `D` and the HTML text. |
| 43 | `    D, text = M.make([(s, f) for s, f in spec.items()], BANNER)` | Calls `M.make` with the sessions as a list of pairs and with the banner text. `D` holds every computed value of the page. `text` is the page. |
| 44 | `    N[0] += 1` | Adds 1 to the counter. |
| 45 | `    with open(os.path.join(ROOT, 'page%03d.html' % N[0]), 'w') as fh:` | Opens a file `page` with the counter in 3 digits and the ending `.html` in `ROOT`. |
| 46 | `        fh.write(text)` | Writes the page into it. With `--keep` the file stays and can be viewed. |
| 47 | `    return D, text` | Returns `D` and the page text. |
| 50 | `def word(D, h):` | Starts the function `word`. It finds the row of one hypothesis in the hypothesis table of `D`. |
| 51 | `    rows = [r for r in D['hyp'] if r['h'] == h]` | `rows`: the rows whose name equals `h`. |
| 52 | `    assert len(rows) == 1, (h, [r['h'] for r in D['hyp']])` | Stops the test with an error unless exactly one row has this name. The error message shows `h` and the names of all rows. |
| 53 | `    return rows[0]` | Returns that row. |
| 56 | `def visible(text):` | Starts the function `visible`. It turns the HTML text of a page into the text that a reader sees. |
| 57 | `    """The text a reader sees: no style block, no tags, entities decoded."""` | Docstring: the text a reader sees: no style block, no tags, and the HTML entities decoded. |
| 58 | `    t = re.sub(r'<style>.*?</style>', ' ', text, flags=re.S)` | `t`: the page without its style sheet. The pattern fits the text from `<style>` to the nearest `</style>`. The flag `re.S` lets the dot fit a line break too. A space takes the place of the match. |
| 59 | `    t = re.sub(r'<title>.*?</title>', ' ', t, flags=re.S)       # svg tooltips and the page title` | Removes every `title` element with its text in the same way. Comment: these are the tooltips of the drawings and the title of the page. |
| 60 | `    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))` | Returns the result of three more steps. Every tag, from `<` to the next `>`, becomes a space. `html.unescape` turns entities such as `&quot;` back into their characters. Every run of white space becomes one space. |
| 63 | `def near(a, b, tol=0.02):` | Starts the function `near`. |
| 64 | `    return abs(a - b) <= tol` | Returns true when `a` and `b` differ by at most `tol`, which is 0.02 unless given. |

### `strong_session`: an invented session in which every tested prediction fails (lines 67 to 76)

| Line | Source | Explanation |
|---:|---|---|
| 67 | `# ------------------------------------------------------------ synthetic sessions` | Comment: a divider. The invented sessions follow. |
| 69 | `def strong_session(name):` | Starts the function `strong_session`. It writes three result folders of one invented session, for the steps B1, B4 and B6, and returns their paths. |
| 70 | `    """A session in which every bounded prediction that can fail does fail, with stable low references."""` | Docstring: a session in which every bounded prediction that can fail does fail, with stable low references. |
| 71 | `    b1 = [T.b1(c, i, T.copy_rate()) for c in (0, 2) for i in range(1, 5)]                       # d = -2, e = +0.1, references 67.5 (low)` | `b1`: the blocks of 8 processes of step B1 at 8 MiB, 4 on CPU 0 and 4 on CPU 2. `T.copy_rate()` gives 67.5 GB/s for `asmread`, 56.0 for `copy`, 58.0 for `asmcopy` and 58.1 for `asmcopy2` [Ref4]. Comment: so `d` is -2 GB/s, `e` is +0.1 GB/s, and the references are at 67.5 GB/s, which is low. |
| 72 | `    b4 = [T.b4(2, 'thp-p1', 15, 15, 'full')]                                                    # case (a) on CPU 2` | `b4`: the block of one process of step B4 on CPU 2: 15 intervals at 67.5 GB/s, then 15 intervals at 71.2 GB/s, all with full huge-page coverage. Comment: this is case (a) on CPU 2. |
| 73 | `    b6 = [T.b6(c, i, T.b6_rate(67.5, 67.0, old1=60.0)) for c in (2, 41) for i in range(1, 4)]   # 8 MiB minus 1 MiB = +7` | `b6`: the blocks of 6 processes of step B6, 3 on CPU 2 and 3 on CPU 41: `asmread` at 67.5 GB/s, `oldread` at 67.0 GB/s and `oldread@1M` at 60.0 GB/s. Comment: 8 MiB minus 1 MiB gives +7 GB/s. |
| 74 | `    return [folder(name, 'B1', b1), folder(name, 'B4', b4), folder(name, 'B6', b6)]` | Writes one folder per step and returns the three paths. |

### Test: a page of one session never says "rejected" (lines 77 to 97)

| Line | Source | Explanation |
|---:|---|---|
| 77 | `def test_one_session_never_gives_rejected():` | Starts the test `test_one_session_never_gives_rejected`. It proves that a page from one session never prints the word "rejected", also for data in which every tested prediction fails, and that the same data in two sessions do give the word. This matters: by rule 11 of the plan, the strongest word needs two sessions. |
| 78 | `    """WHY: rule 11 of the plan defines "rejected" as a prediction that failed in BOTH sessions. A page built from one` | Docstring: the reason for the test. Rule 11 of the plan defines "rejected" as a prediction that failed in both sessions. The sentence goes on in line 79. |
| 79 | `    session must not use the word for any hypothesis, however clear the data are, and must say why."""` | Docstring: a page built from one session must not use the word for any hypothesis, however clear the data are, and must say why. |
| 80 | `    D, text = page({'s1': strong_session('s1')})` | Builds a page from one strong session with the name `s1`. |
| 81 | `    assert all(r['word'] != 'rejected' for r in D['hyp'])` | Tests that no row of the hypothesis table has the word `rejected`. |
| 82 | `    assert word(D, 'H3a')['word'] == 'not rejected' and 'The bounded prediction failed' in word(D, 'H3a')['per']['s1']['result']` | Tests the row of H3a: the word is `not rejected`, and the result of the session still says that the bounded prediction failed. So the page reports the failure, and only the word waits for a second session. |
| 83 | `    assert word(D, 'H4, low intervals')['word'] == 'not rejected' and word(D, 'H1')['word'] == 'not rejected'` | Tests the same word for the row of H4 at the label low and for the row of H1. |
| 84 | `    assert 'no row of this table can say "rejected"' in visible(text)` | Tests that the visible text says that no row of the table can say "rejected". This is the "must say why" of the docstring. |
| 85 | `    assert 'one session cannot give "rejected"' in M.short_version(D)` | Tests that the Short version says that one session cannot give "rejected". |
| 86 | `    assert '<b>rejected</b>' not in text` | Tests that no cell of the page prints the word `rejected` in bold. The hypothesis table prints its word column in bold. |
| 87 | `    # the same data in two sessions: now the word is allowed, and the one-session sentence is gone` | Comment: the same data in two sessions follow. Now the word is allowed, and the sentence for one session is gone. |
| 88 | `    D2, text2 = page({'s1': strong_session('s1'), 's2': strong_session('s2')})` | Builds a page from two strong sessions, `s1` and `s2`. |
| 89 | `    assert word(D2, 'H3a')['word'] == 'rejected' and word(D2, 'H4, low intervals')['word'] == 'rejected' and word(D2, 'H1')['word'] == 'rejected'` | Tests that H3a, H4 at the label low and H1 now have the word `rejected`. This shows that the invented data do fail the predictions. In the first half the word was missing only for the lack of a second session. |
| 90 | `    assert 'no row of this table can say "rejected"' not in visible(text2)` | Tests that the sentence for one session is not in the visible text. |
| 91 | `    assert 'Session s2' in text2 and D2['names'] == ['s1', 's2']` | Tests that the page names session `s2`, and that `D2` holds the two session names in the order given. |
| 92 | `    # one failing session and one that does not fail: not rejected` | Comment: one failing session and one session that does not fail give "not rejected". |
| 93 | `    weak = [folder('s2', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]` | `weak`: one B4 folder for session `s2` with 30 low intervals and no high interval. It holds no case. |
| 94 | `    D3, _ = page({'s1': strong_session('s1'), 's2': weak})` | Builds a page from the strong session `s1` and this `s2`. |
| 95 | `    assert word(D3, 'H3a')['word'] != 'rejected'` | Tests that the word of H3a is not `rejected`. So a failure in one of two sessions is not enough. |

### Test: the two readings of H3a stand side by side (lines 98 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 98 | `def test_h3a_two_readings_are_printed_side_by_side():` | Starts the test `test_h3a_two_readings_are_printed_side_by_side`. It proves that the page prints the strict word of the analysis script and the second reading of the plan together, and leaves the choice to the user. This matters when the two sessions show their case on different CPUs: the handoff note and the plan then give different words. |
| 99 | `    """WHY: case (a) on CPU 2 in one session and on CPU 41 in the other is a failed prediction in each session. The` | Docstring: the reason for the test. Case (a) on CPU 2 in one session and on CPU 41 in the other is a failed prediction in each session. The text goes on in line 100. |
| 100 | `    handoff gives "rejected" only for one CPU in both sessions, the plan has no such condition. The page must give the` | Docstring: the handoff note gives "rejected" only for one CPU in both sessions, and the plan has no such condition. The sentence on what the page must give starts here and goes on in line 101. |
| 101 | `    result of each session as it is, the strict word of the script, the other reading with its reason, and must leave` | Docstring: the page must give the result of each session as it is, the strict word of the script, and the other reading with its reason. The sentence ends in line 102. |
| 102 | `    the choice to the user. "not observed" is wrong under every reading, because the event occurred."""` | Docstring: and the page must leave the choice to the user. The word "not observed" is wrong under every reading, for the reason that the event occurred. |
| 103 | `    s2 = [folder('s2', 'B4', [T.b4(41, 'thp-p1', 15, 15, 'full'), T.b4(2, 'thp-p1', 30, 0, 'full')])]` | `s2`: one B4 folder with two processes. The first runs on CPU 41 with 15 low and 15 high intervals with full coverage: case (a) on CPU 41. The second runs on CPU 2 with 30 low intervals with full coverage. |
| 104 | `    D, text = page({'s1': strong_session('s1'), 's2': s2})` | Builds a page from a strong session `s1`, which has case (a) on CPU 2, and this `s2`. |
| 105 | `    r = word(D, 'H3a')` | `r`: the row of H3a. |
| 106 | `    assert r['word'] == 'not rejected'` | Tests that the word is the strict word `not rejected`: no CPU has a case in both sessions. |
| 107 | `    assert 'The bounded prediction failed' in r['per']['s1']['result'] and 'CPU 2: case (a)' in r['per']['s1']['result']` | Tests that the result of `s1` says that the bounded prediction failed and names case (a) on CPU 2. |
| 108 | `    assert 'The bounded prediction failed' in r['per']['s2']['result'] and 'CPU 41: case (a)' in r['per']['s2']['result']` | Tests the same for `s2` with CPU 41. So neither session is turned into "not observed". |
| 109 | `    assert len(r['open']) == 1 and 'Strict output of the analysis script: "not rejected"' in r['open'][0]` | Tests that the row has exactly one open item, and that the item gives `not rejected` as the strict output of the analysis script. |
| 110 | `    assert 'Second reading: "rejected"' in r['open'][0] and 'word without the same-CPU condition' in r['open'][0] and 'judgment' in r['open'][0]` | Tests that the item also gives the second reading `rejected`, names it as the word without the same-CPU condition, and calls the choice a judgment. |
| 111 | `    v = visible(text)` | `v`: the visible text of the page. |
| 112 | `    assert 'Open for the user' in v and 'session s1: CPU 2, session s2: CPU 41' in v` | Tests that the visible text holds the heading of the box "Open for the user" and the list of the CPUs with a case per session. The heading stands on every page. Only the second text can fail. |
| 113 | `    assert 'CPU 2 has low intervals with full coverage in every session (s1: 15, s2: 30)' in v` | Tests the note on CPU 2: it has low intervals with full coverage in every session, 15 in `s1` and 30 in `s2`. |
| 114 | `    # the same CPU in both sessions: one word under both readings, nothing open` | Comment: the same CPU in both sessions gives one word under both readings, and nothing is open. |
| 115 | `    D2, _ = page({'s1': strong_session('s1'), 's2': strong_session('s2')})` | Builds a page from two strong sessions. Both have case (a) on CPU 2. |
| 116 | `    assert word(D2, 'H3a')['word'] == 'rejected' and not word(D2, 'H3a')['open']` | Tests that the word of H3a is `rejected` and that the row has no open item. |

### Test: a case of B4 that lies near a level limit is marked (lines 119 to 137)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `def test_b4_case_near_a_limit_is_marked():` | Starts the test `test_b4_case_near_a_limit_is_marked`. It proves that the page marks a case (a) whose low intervals lie less than 0.2 GB/s below the low limit, and does not call the prediction failed for it. This matters for the reason that the two level limits are provisional. |
| 120 | `    """WHY: the level limits are provisional. A case (a) whose low intervals lie just below 69 GB/s exists only because` | Docstring: the reason for the test. The level limits are provisional. A case (a) whose low intervals lie directly below 69 GB/s exists only by that limit. The text goes on in line 121. |
| 121 | `    of that limit. The page must mark it, give the description without labels, and must not state that the prediction` | Docstring: the page must mark such a case and give the description without labels. The sentence ends in line 122. |
| 122 | `    failed on that CPU. A case far from the limits is stated as failed."""` | Docstring: and the page must not state that the prediction failed on that CPU. A case far from the limits is stated as failed. |
| 123 | `    args = '--threads 1 --cpus 41 --bytes 8M --seq asmread --rounds 40 --min-ms 300 --stop pass'` | `args`: the arguments of one invented process: 1 thread on CPU 41, a buffer of 8 MiB, the sequence `asmread`, 40 rounds, intervals of at least 300 ms, and the whole-pass stop. |
| 124 | `    near = T.block('B4', 'thp-p1-cpu41', args, lambda r, pos, e, tid, c: 71.5 if r < 17 else 68.9, page=lambda r, pos: (8192, 8192))` | `near`: the block of that process for step B4. Its rate is 71.5 GB/s in the rounds 0 to 16 and 68.9 GB/s in the rounds 17 to 39. Its page state is 8192 of 8192 kB before every interval: full coverage. Inside this test the name `near` means this block and not the function `near` of line 63. |
| 125 | `    D, text = page({'s1': [folder('s1', 'B4', [near])]})` | Builds a page from one folder with this process. |
| 126 | `    f = D['sessions']['s1']['b4_cases'][41]` | `f`: the facts of `b4_case_facts` for CPU 41. |
| 127 | `    assert f['label_dependent'] and f['near_lo'] == 23 and f['n_low'] == 23 and f['near_hi'] == 0` | Tests four values: the case depends on the limits, 23 of the 23 low intervals lie near the low limit (68.9 GB/s is 0.1 GB/s below 69), and no high interval lies near the high limit. |
| 128 | `    b4 = visible(M.sec_b4(D, M.Refs()))` | `b4`: the visible text of the section of B4 alone. `M.sec_b4` gets an empty reference list, so the text holds no citation. |
| 129 | `    assert 'This case depends on the provisional limits. 23 of the 23 low intervals lie less than 0.2 GB/s below the limit of 69 GB/s' in b4` | Tests the sentence of the section that the case depends on the provisional limits, with the 23 of 23 low intervals less than 0.2 GB/s below the limit of 69 GB/s. |
| 130 | `    assert 'went from a median of 71.50 GB/s (intervals 0 to 16) to a median of 68.90 GB/s (intervals 17 to 39)' in b4` | Tests the description without labels: the rate went from a median of 71.50 GB/s in the intervals 0 to 16 to a median of 68.90 GB/s in the intervals 17 to 39. |
| 131 | `    assert 'So the bounded prediction of H3a failed' not in b4` | Tests that the section does not say that the bounded prediction of H3a failed. |
| 132 | `    assert 'The rule finds a case, and the case depends on the provisional limits' in word(D, 'H3a')['per']['s1']['result']` | Tests that the row of H3a says that the rule finds a case and that the case depends on the provisional limits. |
| 133 | `    D, _ = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 15, 15, 'full')])]})` | Builds a second page: one B4 process on CPU 2 with 15 intervals at 67.5 GB/s and 15 at 71.2 GB/s. Both rates lie far from the limits. |
| 134 | `    assert not D['sessions']['s1']['b4_cases'][2]['label_dependent']` | Tests that this case does not depend on the limits. |
| 135 | `    assert 'So the bounded prediction of H3a failed in this session on this CPU' in visible(M.sec_b4(D, M.Refs()))` | Tests that the section now says that the bounded prediction of H3a failed in this session on this CPU. So the mark of the first half is not printed for every case. |

### Test: a process that is not stable is described and not decided (lines 138 to 164)

| Line | Source | Explanation |
|---:|---|---|
| 138 | `def test_unstable_process_is_described_and_not_decided():` | Starts the test `test_unstable_process_is_described_and_not_decided`. It proves that a process whose reference intervals change level stays out of the rule and stays in the description. This matters for two reasons: the rule must not use it, and the user must still see it to judge the level limits. |
| 139 | `    """WHY: at 8 MiB only a process whose references are all at one level may enter a decision (plan, rules 4 and 5).` | Docstring: the reason for the test. At 8 MiB only a process whose references are all at one level may enter a decision (plan, rules 4 and 5). |
| 140 | `    The other processes must still be visible, as a description, so that the user can judge the level limits."""` | Docstring: the other processes must still be visible, as a description, so the user can judge the level limits. |
| 141 | `    blocks = []` | `blocks`: the blocks of the processes, empty at the start. |
| 142 | `    for c in (0, 2):` | Loop over the CPUs 0 and 2. |
| 143 | `        blocks += [T.b1(c, i, T.copy_rate()) for i in range(1, 4)]` | Adds three processes with the standard rates: `d` is -2 GB/s and the references are low. |
| 144 | `        blocks += [T.b1(c, 4, T.copy_rate(copy=67.0, ref_by_round=[67.5, 67.5, 71.2, 71.2]))]       # d = +9, the level changes` | Adds a fourth process. Its `copy` runs at 67.0 GB/s. Its references are at 67.5 GB/s in the rounds 0 and 1 and at 71.2 GB/s in the rounds 2 and 3. Comment: `d` is +9 GB/s, and the level changes. |
| 145 | `    D, text = page({'s1': [folder('s1', 'B1', blocks)]})` | Builds a page from one B1 folder with these 8 processes. |
| 146 | `    x = D['sessions']['s1']` | `x`: the values of the session. |
| 147 | `    g = x['pairs']['B1']['8M']` | `g`: the description of the group of B1 at 8 MiB. |
| 148 | `    rule = x['res']['B1']['groups']['8M']['labels']['low']` | `rule`: the result of the rule for that group at the label low. |
| 149 | `    assert g['per_cpu'][0]['n'] == 4 and rule['per_cpu'][0]['n_processes'] == 3         # 4 described, 3 decided` | Tests that the description has 4 processes on CPU 0 and the rule has 3. Comment: 4 described, 3 decided. |
| 150 | `    assert g['per_cpu'][0]['n_not_stable'] == 1 and near(max(g['per_cpu'][0]['d']), 9.0)` | Tests that the description counts 1 process of CPU 0 as not stable, and that the highest `d` on CPU 0 is near 9.0 GB/s. |
| 151 | `    assert rule['decision'] == 'resolved' and rule['sign'] == -1                         # the odd process did not enter the rule` | Tests that the rule gives `resolved` with a negative sign. Comment: the process that differs did not enter the rule. With it the values of `d` would not have one sign. |
| 152 | `    assert not g['per_cpu'][0]['one_sign']                                               # and the description shows that it differs` | Tests that the description says that the `d` of CPU 0 do not have one sign. Comment: so the description shows that one process differs. |
| 153 | `    assert 'description, no decision' in text and 'Description, no decision' in text` | Tests that the page holds the description mark in two forms, with a small and with a capital first letter. Both texts stand in typed text of every page (the list `WORDS` and the last paragraph of the function `sec_refs`). So this line cannot fail. |
| 154 | `    # all references between the two limits: the rule has no process at all, the description has all of them` | Comment: in the next case all references lie between the two limits. The rule has no process at all, and the description has all of them. |
| 155 | `    mid = [T.b1(c, i, T.copy_rate(ref=69.8)) for c in (0, 2) for i in range(1, 5)]` | `mid`: the blocks of 8 processes of B1 at 8 MiB with every reference at 69.8 GB/s, which lies between 69 and 70.5. |
| 156 | `    D, text = page({'s1': [folder('s1', 'B1', mid)]})` | Builds a page from one folder with them. |
| 157 | `    g = D['sessions']['s1']['pairs']['B1']['8M']` | `g`: the description of the group at 8 MiB. |
| 158 | `    assert word(D, 'H4, low intervals')['word'] == 'not observed' and word(D, 'H4, high intervals')['word'] == 'not observed'` | Tests that both rows of H4, for the label low and for the label high, have the word `not observed`. |
| 159 | `    assert word(D, 'H4, low intervals')['n'] == 0` | Tests that the row for the label low counts 0 processes that the rule used. |
| 160 | `    assert all(v['n'] == 4 and v['above'] and v['one_sign'] and near(v['median_d'], -2.0) for v in g['per_cpu'].values())` | Tests the description of every CPU: 4 processes, an absolute median `d` above the A/A spread, one sign, and a median `d` near -2.0 GB/s. So the description holds the whole difference of all 8 processes, although the rule uses none of them and gives the word `not observed`. |
| 161 | `    assert 'd is below 0 in 8 of 8 processes' in word(D, 'H4, low intervals')['basis']   # the description is next to the word, and is not the word` | Tests that the notes of the row say that `d` is below 0 in 8 of 8 processes. Comment: the description stands next to the word, and it is not the word. |
| 162 | `    assert 'Open decision for the user' in text and '0 of the 8 processes with reference intervals are stable' in visible(text)` | Tests two texts. The heading "Open decision for the user" stands on every page. That half cannot fail. The second text is computed: 0 of the 8 processes with reference intervals are stable. |

### Test: sizes without a level use every process (lines 165 to 173)

| Line | Source | Explanation |
|---:|---|---|
| 165 | `def test_sizes_without_a_level_are_decided_for_all_processes():` | Starts the test `test_sizes_without_a_level_are_decided_for_all_processes`. It proves that the level limits remove no process at a buffer size other than 8 MiB. This matters: at those sizes no level is defined, so the limits for 8 MiB must not decide which process counts. |
| 166 | `    """WHY: at 4, 16 and 32 MiB no level is defined (handoff B.10), so the level limits must not remove a process there."""` | Docstring: the reason for the test. At 4, 16 and 32 MiB no level is defined (section B.10 of the handoff note), so the level limits must not remove a process there. |
| 167 | `    blocks = [T.b1(c, i, T.copy_rate(ref=69.8), bytes_='16M') for c in (0, 2) for i in range(1, 5)]` | `blocks`: 8 processes of B1 with a buffer of 16 MiB, 4 on CPU 0 and 4 on CPU 2, with every reference at 69.8 GB/s. At 8 MiB such references would make every process not stable. |
| 168 | `    D, text = page({'s1': [folder('s1', 'B1', blocks)]})` | Builds a page from one folder with them. |
| 169 | `    r = D['sessions']['s1']['res']['B1']['groups']['16M']['labels']['none']` | `r`: the result of the rule for the group `16M` under the label `none`. |
| 170 | `    assert r['decision'] == 'resolved' and r['per_cpu'][0]['n_processes'] == 4` | Tests that the result is `resolved` and that the rule used all 4 processes of CPU 0. |
| 171 | `    assert '16 MiB (the chart is a description' not in text and '<h4>16 MiB</h4>' in text` | Tests the heading of the 16 MiB block: it carries no description mark, and it is a heading of level 4. At these sizes the chart shows what the rule decides. |

### Test: the position effect of step B6 is shown (lines 174 to 214)

| Line | Source | Explanation |
|---:|---|---|
| 174 | `def test_b6_position_effect_is_shown():` | Starts the test `test_b6_position_effect_is_shown`. It proves that the page shows when the rate of old read depends on the loop that ran before, and that it then does not report a size effect without that limit. This matters: without it a reader reads a position effect as an effect of the buffer size. |
| 175 | `    """WHY: in the B6 sequence one loop of a pair follows asm read and the other follows old read. If the loop before` | Docstring: the reason for the test. In the B6 sequence one loop of a pair follows asm read and the other follows old read. The text goes on in line 176. |
| 176 | `    changes the rate, the median over both orders hides it and the A/A spread looks small. The page must show the` | Docstring: if the loop before changes the rate, the median over both orders does not show it, and the A/A spread looks small. The text goes on in line 177. |
| 177 | `    rates by the loop before, and the largest single A/A pair, or the reader takes a position effect for a kernel effect."""` | Docstring: the page must show the rates by the loop before, and the largest single A/A pair. If not, the reader reads a position effect as a kernel effect. |
| 178 | `    seq = T.B6SEQ.split(',')` | `seq`: the entries of the B6 sequence as a list. |
| 180 | `    def rate(r, pos, entry, tid, cpu):` | Starts the inner function `rate`. It gives the invented rate of one interval from its round, position, entry, thread and CPU. |
| 181 | `        if entry == 'asmread':` | Tests whether the entry is the reference kernel. |
| 182 | `            return 67.5` | `asmread` always runs at 67.5 GB/s. |
| 183 | `        if entry == 'oldread@1M':` | Tests whether the entry is old read at 1 MiB. |
| 184 | `            return 67.1` | It always runs at 67.1 GB/s. |
| 185 | `        if seq[pos - 1] == 'asmread':` | Tests whether the entry before this one in the sequence is `asmread`. |
| 186 | `            return 63.0                                                       # old read after asm read is 4 GB/s slower` | Then old read at 8 MiB, or its second copy, runs at 63.0 GB/s. Comment: old read after asm read is 4 GB/s slower. |
| 187 | `        return 67.3 if entry == 'oldread2' else 67.0` | In every other place `oldread2` runs at 67.3 GB/s and `oldread` at 67.0 GB/s. |
| 188 | `    f = [folder('s1', 'B6', [T.b6(c, i, rate) for c in (2, 41) for i in range(1, 5)])]` | `f`: one B6 folder of session `s1` with 8 processes, 4 on CPU 2 and 4 on CPU 41, all with these rates. |
| 189 | `    D, text = page({'s1': f})` | Builds a page from it. |
| 190 | `    x = D['sessions']['s1']` | `x`: the values of the session. |
| 191 | `    pc = x['b6']['per_cpu'][2]` | `pc`: the values of the description of B6 for CPU 2. |
| 192 | `    assert near(pc['aa_spread'], 0.15) and near(pc['aa_single_max'], 4.3)      # the spread of the rule is small, a single pair differs by 4.3` | Tests two values. The A/A spread is near 0.15 GB/s: the two A/A pairs of a round give +4.3 and -4.0 GB/s, and their median is 0.15. The largest single A/A pair is near 4.3 GB/s. Comment: the spread of the rule is small, and a single pair differs by 4.3. |
| 193 | `    assert near(pc['d_first'], 63.0 - 67.1) and near(pc['d_second'], 67.0 - 67.1)` | Tests the pair value by order: near -4.1 GB/s with `oldread` at 8 MiB timed first, directly after `asmread`, and near -0.1 GB/s with it timed second. |
| 194 | `    assert pc['aa_pos_n'] == 32 and pc['aa_pos_neg'] == 32                     # the copy timed first is slower in every A/A pair` | Tests that CPU 2 has 32 A/A pairs and that the copy timed first is slower in all 32. Comment: the copy timed first is slower in every A/A pair. |
| 195 | `    bp = x['b6_prev'][2]` | `bp`: the rates of CPU 2 by the loop that ran before. |
| 196 | `    assert near(M.median(bp[('oldread', 'asm read')]), 63.0) and near(M.median(bp[('oldread', 'an old read entry')]), 67.0)` | Tests the median rate of `oldread`: near 63.0 GB/s after asm read and near 67.0 GB/s after an old read entry. `M.median` is the function `median` that the page builder imported. |
| 197 | `    v = visible(text)` | `v`: the visible text of the page. |
| 198 | `    assert 'In 64 of 64 such pairs the first interval is slower than the second' in v` | Tests the sentence with the count over both CPUs: in 64 of 64 A/A pairs the first interval is slower than the second. |
| 199 | `    assert 'So these data do not show that the rate of old read depends on the buffer size' in v` | Tests the conclusion: the data do not show that the rate of old read depends on the buffer size. |
| 200 | `    assert 'Its cause is a hypothesis: the loop that ran before leaves a state' in v` | Tests the sentence that calls the cause a hypothesis: the loop that ran before leaves a state. |
| 201 | `    assert 'Its absolute value is 4.10 GB/s in one order of the two loops and 0.10 GB/s in the other' in v      # the line under the Short version` | Tests the line under the Short version: the absolute difference is 4.10 GB/s in one order of the two loops and 0.10 GB/s in the other. Comment: this is the line under the Short version. |
| 202 | `    assert 'Old read at 1 MiB after asm read minus old read at 1 MiB after old read is 0.00 GB/s' in v` | Tests the sentence on old read at 1 MiB: after asm read minus after old read gives 0.00 GB/s. In the invented data its rate does not depend on the loop before. |
| 203 | `    assert not word(D, 'H1')['open']                                           # one session: the word is not "rejected", nothing to choose` | Tests that the row of H1 has no open item. Comment: with one session the word is not "rejected", so there is nothing to choose. |
| 204 | `    # two sessions: the strict word is "rejected". It stays, with the limit next to it and the choice left to the user.` | Comment: with two sessions the strict word is "rejected". It stays, with the limit next to it, and the choice is left to the user. |
| 205 | `    D, text = page({'s1': f, 's2': [folder('s2', 'B6', [T.b6(c, i, rate) for c in (2, 41) for i in range(1, 5)])]})` | Builds a page from the folder `f` as `s1` and a second folder with the same rates as `s2`. |
| 206 | `    r = word(D, 'H1')` | `r`: the row of H1. |
| 207 | `    assert r['word'] == 'rejected' and len(r['open']) == 1 and 'judgment' in r['open'][0] and '"not resolved"' in r['open'][0]` | Tests that the word is `rejected`, and that the row has exactly one open item that calls the choice a judgment and names the other word, `not resolved`. So the page does not change the word of the rule by itself. |
| 208 | `    assert 'The result comes from part 2 only' in r['basis']` | Tests that the notes of the row say that the result comes from part 2 only. |
| 209 | `    # no position effect: no such sentence, nothing open` | Comment: without a position effect there is no such sentence, and nothing is open. |
| 210 | `    flat = lambda r, pos, entry, tid, cpu: 67.5 if entry == 'asmread' else 67.1 if entry == 'oldread@1M' else 60.0 if entry == 'oldread' else 60.1` | `flat`: a rate function without a position effect: `asmread` at 67.5 GB/s, old read at 1 MiB at 67.1, `oldread` at 60.0 and `oldread2` at 60.1 GB/s, at every position. |
| 211 | `    D, text = page({s: [folder(s, 'B6', [T.b6(c, i, flat) for c in (2, 41) for i in range(1, 5)])] for s in ('s1', 's2')})` | Builds a page from two sessions, each with one B6 folder of 8 processes with these rates. |
| 212 | `    assert word(D, 'H1')['word'] == 'rejected' and not word(D, 'H1')['open'] and 'So these data do not show' not in text` | Tests that the word of H1 is `rejected`, that the row has no open item, and that the page does not hold the conclusion of line 199. So the limit is printed only when the data show the effect. |

### Test: counter increases and level changes of step B4 are found and described (lines 215 to 245)

| Line | Source | Explanation |
|---:|---|---|
| 215 | `def test_b4_marks_counter_increases_and_level_changes():` | Starts the test `test_b4_marks_counter_increases_and_level_changes`. It proves that the page finds an increase of a system counter at the right interval, and that it describes a level change inside a process with its direction while the word of H2 stays "not tested". This matters: these two descriptions are all that the steps B4 and C1 can give for H2 and H3b. |
| 216 | `    """WHY: H3b cannot be tested without root. What B4 can show is whether a level change comes with a change of` | Docstring: the reason for the test. H3b cannot be tested without root. What step B4 can show is whether a level change occurs together with a change of coverage. The list goes on in line 217. |
| 217 | `    coverage or with an increase of thp_collapse_alloc or pgmigrate_success. So an increase must be found at the` | Docstring: or with an increase of `thp_collapse_alloc` or `pgmigrate_success`. So an increase must be found at the right interval. |
| 218 | `    right interval. The plan gives H2 no bounded prediction in Parts B and C, so its word is "not tested" whatever the` | Docstring: the plan gives H2 no bounded prediction in Parts B and C, so its word is "not tested" for all data. The sentence ends in line 219. |
| 219 | `    data show, and a change of level inside a process is described with its direction."""` | Docstring: and a change of level inside a process is described with its direction. |
| 220 | `    blk = T.b4(2, 'thp-p1', 30, 30, 'full')` | `blk`: the block of one B4 process on CPU 2 with 30 intervals at 67.5 GB/s and then 30 intervals at 71.2 GB/s, all with full coverage. |
| 221 | `    out = []` | `out`: the changed lines of the block, empty at the start. |
| 222 | `    for line in blk.splitlines():` | Loop over the lines of the block. |
| 223 | `        f = line.split(',')` | `f`: the fields of the line. |
| 224 | `        if f[0] == 'P' and int(f[1]) >= 30:` | Tests whether the line is a `P` row of round 30 or later. In this sequence a round holds one interval, so the round is the interval number. |
| 225 | `            f[9] = '8'                                    # thp_collapse_alloc 7 -> 8 before interval 30` | Then field 10 of the row, `thp_collapse_alloc`, is set to 8. The row writer gives the value 7. Comment: the counter goes from 7 to 8 before interval 30. |
| 226 | `        if f[0] == 'P' and int(f[1]) >= 45:` | Tests whether the line is a `P` row of round 45 or later. |
| 227 | `            f[10] = '95'                                  # pgmigrate_success 90 -> 95 before interval 45` | Then field 11 of the row, `pgmigrate_success`, is set to 95. The row writer gives the value 90. Comment: the counter goes from 90 to 95 before interval 45. |
| 228 | `        out.append(','.join(f))` | Appends the line, changed or not. |
| 229 | `    D, text = page({'s1': [folder('s1', 'B4', ['\n'.join(out) + '\n'])]})` | Builds a page from one B4 folder with the changed block. |
| 230 | `    p = D['sessions']['s1']['b4'][0]` | `p`: the record of the process in `D`. |
| 231 | `    assert p['events'] == {'thp_collapse_alloc': [30], 'pgmigrate_success': [45]}` | Tests that the page builder found exactly one increase of each counter: before interval 30 and before interval 45. |
| 232 | `    assert p['changes'] == [(29, 30)] and p['step_at'] == 30 and near(p['step_size'], 71.2 - 67.5)` | Tests three more values: one level change, from interval 29 to interval 30. The largest step leads into interval 30. Its size is near 3.7 GB/s, which is 71.2 minus 67.5. |
| 233 | `    r = word(D, 'H2')` | `r`: the row of H2. |
| 234 | `    assert r['word'] == 'not tested' and r['per']['s1']['result'].startswith('Description, no decision. 1 change between low and high')` | Tests that the word is `not tested`, and that the result of the session starts with the description mark and with 1 change between low and high. |
| 235 | `    assert 'goes from low (67.50 GB/s, interval 29) to high (71.20 GB/s, interval 30).' in r['per']['s1']['result']` | Tests the sentence on the change, with its direction: from low at 67.50 GB/s in interval 29 to high at 71.20 GB/s in interval 30. |
| 236 | `    assert 'no bounded prediction in Parts B and C' in r['basis']` | Tests that the notes of the row say that the plan gives no bounded prediction in Parts B and C. |
| 237 | `    assert 'thp_collapse_alloc rose before interval 30' in text` | Tests that the page holds the tooltip of the vertical line in the chart: `thp_collapse_alloc` rose before interval 30. |
| 238 | `    # no change of level inside a process: the event could have been shown and was not` | Comment: the next case has no change of level inside a process. The event could have been shown and was not. |
| 239 | `    D, _ = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 60, 0, 'full'), T.b4(2, 'thp-p2', 0, 60, 'full')])]})` | Builds a page from one B4 folder with two processes on CPU 2: one with 60 low intervals and one with 60 high intervals. |
| 240 | `    r = word(D, 'H2')` | `r`: the row of H2. |
| 241 | `    assert r['word'] == 'not tested' and '0 changes between low and high' in r['per']['s1']['result'] and '1 process was high in all intervals' in r['per']['s1']['result']` | Tests that the word stays `not tested`, and that the result counts 0 changes between low and high and 1 process that was high in all intervals. |
| 242 | `    assert D['sessions']['s1']['res']['B4']['per_cpu'][2]['cases'] == ['a']        # low and high in two processes is still case (a)` | Tests that the analysis finds case (a) on CPU 2. Comment: low and high in two processes is still case (a). |
| 243 | `    assert 'No process has both' in M.sec_b4(D, M.Refs())` | Tests that the section of B4 says that no process has both levels. So the reader learns that the level differs between processes and not inside one. |

### Helper `counters`, and the test of the counter observation (lines 246 to 272)

| Line | Source | Explanation |
|---:|---|---|
| 246 | `def counters(l1_per_line, l2_per_line):` | Starts the helper `counters`. It returns a function that writes the count fields of a `C` row. `l1_per_line` and `l2_per_line` are the invented L1D and L2D refills per line of 64 B. |
| 247 | `    def f(r, pos, entry, tid, nbytes):` | Starts the inner function `f`. The row writer calls it with the round, the position, the entry, the thread and the bytes of the interval. |
| 248 | `        lines = nbytes // 64` | `lines`: the bytes of the interval divided by 64, without the remainder. |
| 249 | `        return '300000000,300000000,299000000,%d,%d,%d,%d,%d' % (840000000, nbytes * 11 // 256, int(lines * l1_per_line), int(lines * l2_per_line), 0)` | Returns the fields as text: an enabled time and a running time of 300000000 ns each, a CPU time of 299000000 ns, 840000000 cycles, 11 instructions per 256 B, the L1D refills, the L2D refills, and 0 read misses of the last cache level. |
| 250 | `    return f` | Returns the function `f`. |
| 253 | `def test_counter_observation_is_printed_only_when_computed():` | Starts the test `test_counter_observation_is_printed_only_when_computed`. It proves that the sentence on the two refill counts comes from the counter rows of the input, and that a counter run with one level names the missing measurement. This matters: a typed sentence would report an observation that the input does not hold. |
| 254 | `    """WHY: "l1d_refill is lower than l2d_refill" is an observation of some runs. The sentence must come from the` | Docstring: the reason for the test. That `l1d_refill` is lower than `l2d_refill` is an observation of some runs. The sentence goes on in line 255. |
| 255 | `    rows of the run on the page, not from the run in which it was first seen."""` | Docstring: the sentence must come from the rows of the run on the page, not from the run in which it was first seen. |
| 256 | `    args = '--threads 1 --cpus 2 --bytes 8M --seq asmread --rounds 4 --min-ms 300 --stop pass --count'` | `args`: the arguments of one invented process: 1 thread on CPU 2, a buffer of 8 MiB, the sequence `asmread`, 4 rounds, intervals of at least 300 ms, the whole-pass stop, and `--count`. |
| 257 | `    lower = T.block('C1', 'cpu2-p1', args, lambda *a: 67.5, counts=counters(0.37, 0.82))` | `lower`: the block of that process for step C1, at 67.5 GB/s in every interval, with 0.37 L1D refills and 0.82 L2D refills per line. |
| 258 | `    D, text = page({'s1': [folder('s1', 'C1', [lower])]})` | Builds a page from one C1 folder with it. |
| 259 | `    assert D['sessions']['s1']['cfacts']['C1']['l1_lt_l2'] == 4` | Tests that the page builder counts 4 `asmread` rows with fewer L1D refills than L2D refills. |
| 260 | `    v = visible(text)` | `v`: the visible text of the page. |
| 261 | `    assert 'Observation: the count of l1d_refill is lower than the count of l2d_refill in 4 of the 4 asm read intervals of C1' in v and 'Hypothesis: for this loop the two event names' in v` | Tests two sentences: the observation with its count, 4 of the 4 asm read intervals of C1, and the start of the hypothesis on the two event names. |
| 262 | `    # the plan asks C1 for both levels. A run with one level must say which measurement is missing.` | Comment: the plan asks step C1 for both levels. A run with one level must say which measurement is missing. |
| 263 | `    assert 'Insufficient data. Counters at the high level in a long run. No interval of C1 was above 70.5 GB/s. The level groups that were seen are: low.' in v` | Tests the block "Insufficient data" on counters at the high level: no interval of C1 was above 70.5 GB/s, and the only level group that was seen is low. |
| 264 | `    # 299000000 ns of CPU time in 0.3 s is 99.666 %: the lowest value is rounded down, never up` | Comment: 299000000 ns of CPU time in 0.3 s is 99.666 %. The lowest value is rounded down, never up. |
| 265 | `    assert 'The lowest CPU time of a thread was 99.66 % of the elapsed time of its interval (rounded down)' in v` | Tests that the page prints 99.66 % as the lowest CPU time of a thread, with the words "rounded down". A value rounded up would say more than was measured. |
| 266 | `    higher = T.block('C1', 'cpu2-p1', args, lambda *a: 67.5, counts=counters(1.0, 0.82))` | `higher`: the same process with 1.0 L1D refills and 0.82 L2D refills per line. Now the L1D count is the higher one. |
| 267 | `    D, text = page({'s1': [folder('s1', 'C1', [higher])]})` | Builds a page from one C1 folder with it. |
| 268 | `    assert 'Observation: in' not in text and 'In none of the 4 asm read intervals' in text` | Tests two texts. The first, `Observation: in`, is on no page: the paragraph of the page builder starts with `Observation: the count`. That half cannot fail. The second half can fail: the page says that in none of the 4 asm read intervals the L1D count is the lower one. |
| 269 | `    g = D['sessions']['s1']['res']['C1']['groups'][0]` | `g`: the first counter group in the result of the analysis. |
| 270 | `    assert near(g['median_instructions_per_line'], 2.75, 0.001) and near(g['median_clock_GHz'], 840 / 299, 0.001)` | Tests two computed values of the group. The instructions per line are near 2.75: 11 instructions per 256 B give 2.75 per 64 B. The clock is near 840 divided by 299, about 2.81 GHz: 840000000 cycles in 299000000 ns of CPU time. |

### Test: missing steps and Part D (lines 273 to 286)

| Line | Source | Explanation |
|---:|---|---|
| 273 | `def test_missing_steps_and_part_d():` | Starts the test `test_missing_steps_and_part_d`. It proves that a step without data is reported as missing with the measurement that would give it, and that H3b stays "not tested". This matters: a missing step must not look like a step without a result. |
| 274 | `    """WHY: a step that is not in the input must read "Insufficient data" with the measurement that would give it,` | Docstring: the reason for the test. A step that is not in the input must read "Insufficient data" with the measurement that would give it. The sentence goes on in line 275. |
| 275 | `    and H3b is "not tested" whatever the input, because Part D was not run."""` | Docstring: and H3b is "not tested" for every input, for the reason that Part D was not run. |
| 276 | `    D, text = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]})` | Builds a page from one B4 folder with one process of 30 low intervals. No other step is in the input. |
| 277 | `    assert word(D, 'H3b')['word'] == 'not tested'` | Tests that the word of H3b is `not tested`. |
| 278 | `    for h in ('H1', 'H4', 'H5', 'H6'):` | Loop over the four hypotheses whose steps are missing: H1, H4, H5 and H6. |
| 279 | `        assert word(D, h)['word'] == 'not tested', h` | Tests that each has the word `not tested`. The error message names the hypothesis. |
| 280 | `    assert D['sessions']['s1']['missing'] == ['B1', 'B2', 'B3', 'B6', 'C1', 'C2']` | Tests the list of missing steps: B1, B2, B3, B6, C1 and C2. |
| 281 | `    v = visible(text)` | `v`: the visible text of the page. |
| 282 | `    assert 'Insufficient data. Step B1: no process is in the input' in v and 'A run of step B1 would give it' in v` | Tests the block for step B1: `Insufficient data`, no process is in the input, and a run of step B1 would give it. |
| 283 | `    assert 'Insufficient data. Step C2: no counter row' in v` | Tests the block for step C2: `Insufficient data`, no counter row. |
| 284 | `    assert word(D, 'H3a')['word'] == 'not observed'               # one level only: neither case` | Tests that the word of H3a is `not observed`. Comment: the input has one level only, so neither case occurred. |

### Test: the section on the system load (lines 287 to 316)

| Line | Source | Explanation |
|---:|---|---|
| 287 | `def test_load_section():` | Starts the test `test_load_section`. It proves that the page does not take a high load average, or a busy process of our own account, as a sign of another user. This matters: the load is reported with every result, and a wrong reading would make an undisturbed run look disturbed. |
| 288 | `    """WHY: the 1-minute load average stays high for a while after our own process with 120 threads. The page must` | Docstring: the reason for the test. The 1-minute load average stays high for a while after our own process with 120 threads. The sentence goes on in line 289. |
| 289 | `    not read that as another user: it names the step before, and gives the runnable tasks, waits and logins."""` | Docstring: the page must not read that as another user. It names the step before, and gives the runnable tasks, the waits and the logins. |
| 290 | `    b1 = [T.block('B1', '8M-cpu%d-p%d' % (c, i), '--threads 1 --cpus %d --bytes 8M --seq %s --rounds 4 --min-ms 300 --stop pass' % (c, T.B1SEQ),` | Starts `b1`: the blocks of 6 processes of step B1 at 8 MiB, 3 on CPU 0 and 3 on CPU 2, each with 4 rounds of the B1 sequence. |
| 291 | `                  T.copy_rate(), load='%s 80.00 90.00 1/913' % ('88.50' if (c, i) == (0, 1) else '1.10')) for c in (0, 2) for i in (1, 2, 3)]` | Ends `b1`: the standard rates, and the load values of the header line. The first process (CPU 0, process 1) gets a 1-minute load average of 88.50 tasks. The others get 1.10. All get 1 runnable task. |
| 292 | `    f1 = folder('s1', 'B1', b1, start='2026-01-01T01:23:15Z', end='2026-01-01T01:40:00Z')` | `f1`: the B1 folder. Its `env.txt` gives the start 01:23:15 and the end 01:40:00 UTC on 2026-01-01. |
| 293 | `    big = [T.block('B9', 'one-p1', '--threads 120 --cpus 0-63,64-119 --bytes 256M --seq oldread --rounds 1 --min-ms 500 --stop common', lambda *a: 3.0)]` | `big`: the block of one process of step B9 with 120 threads on the CPUs 0 to 119, a buffer of 256 MiB per thread, the sequence `oldread` and the common stop. Every thread runs at 3.0 GB/s. |
| 294 | `    f0 = folder('s1', 'B9', big, start='2026-01-01T01:21:00Z', end='2026-01-01T01:23:01Z')` | `f0`: the B9 folder. Its step starts at 01:21:00 and ends at 01:23:01 UTC, 14 s before the start of B1. |
| 295 | `    D, text = page({'s1': [f0, f1]})` | Builds a page from both folders in one session. |
| 296 | `    L = D['sessions']['s1']['load']['B1']` | `L`: the load facts of step B1. |
| 297 | `    assert L['n'] == 6 and near(L['load_max'], 88.5) and near(L['load_first'], 88.5) and near(L['load_last'], 1.1) and L['runnable_max'] == 1` | Tests five values: 6 launches, a highest 1-minute load average near 88.5, the value 88.5 at the first launch and 1.1 at the last, and a highest count of 1 runnable task. |
| 298 | `    assert L['top'] == (0.3, 'root', 'kworker/1')                 # ps of the script itself is left out` | Tests the busiest other process: `kworker/1` of `root` with 0.3 %. Comment: the `ps` of the script itself, with 100 %, is left out. |
| 299 | `    v = visible(text)` | `v`: the visible text of the page. |
| 300 | `    assert 'ran 120 threads of our own benchmark and ended at 2026-01-01T01:23:01Z' in v` | Tests the sentence that the step before ran 120 threads of our own benchmark and ended at 01:23:01 UTC. So the page finds the B9 folder as the cause. |
| 301 | `    assert 'It is therefore no evidence of another user' in v` | Tests the sentence that the load average is no evidence of another user. |
| 302 | `    assert D['sessions']['s1']['other'][0]['steps'] == ['B9'] and D['sessions']['s1']['steps'] == ['B1']` | Tests that the B9 folder stands in the list `other`, and that B1 is the only step with processes. So B9 gives the page its end time and no process. |
| 303 | `    # without the folder of the step before, the cause is a labelled hypothesis` | Comment: without the folder of the step before, the cause is a labelled hypothesis. |
| 304 | `    _, text = page({'s1': [f1]})` | Builds a page from the B1 folder alone. |
| 305 | `    assert 'Hypothesis: the high values are left from a process with 120 threads' in visible(text)` | Tests that the page then states the cause as a sentence that starts with the word `Hypothesis`. |
| 306 | `    # no high value: the sentence is not printed` | Comment: without a high value the sentence is not printed. |
| 307 | `    _, text = page({'s1': [folder('s1', 'B4', [T.b4(2, 'thp-p1', 30, 0, 'full')])]})` | Builds a page from one B4 folder with the standard load of 0.52. |
| 308 | `    assert 'no evidence of another user' not in text and 'No launch on this page had a 1-minute load average above 2 tasks' in text` | Tests that the text on another user is absent, and that the page says that no launch had a 1-minute load average above 2 tasks. |
| 309 | `    # a busy process of the account that runs the script is not another user. One of another account is not explained by guessing.` | Comment: a busy process of the account that runs the script is not another user. A busy process of another account is not explained by a guess. |
| 310 | `    blk = [T.b4(2, 'thp-p1', 30, 0, 'full')]` | `blk`: the block of one B4 process with 30 low intervals. |
| 311 | `    _, text = page({'s1': [folder('s1', 'B4', blk, busy='17.8 tester   systemd\n')]})` | Builds a page whose `launches.txt` holds one more process line: `systemd` of the account `tester` with 17.8 %. `tester` is also the account of the `ps` line. |
| 312 | `    assert 'with 17.8 % of one CPU at one launch' in visible(text) and 'The run script runs under the same account, so this is not another user' in visible(text)` | Tests two sentences: the busy process with 17.8 % of one CPU at one launch, and that the run script runs under the same account, so this is not another user. |
| 313 | `    _, text = page({'s1': [folder('s1', 'B4', blk, busy='17.8 guest    python3\n')]})` | Builds the same page with the line `python3` of the account `guest` with 17.8 %. |
| 314 | `    assert 'Insufficient data: what this process did' in visible(text) and 'same account' not in text` | Tests that the page prints `Insufficient data` for what this process did, and that the text on the same account is absent. |

### Test: tables and charts keep sessions and series apart (lines 317 to 330)

| Line | Source | Explanation |
|---:|---|---|
| 317 | `def test_tables_and_charts_keep_sessions_and_series_apart():` | Starts the test `test_tables_and_charts_keep_sessions_and_series_apart`. It proves that each session has its own column, and that a reader can tell `d` from `e` in a chart row. This matters: rule 10 of the plan asks for a result per session, and a number that is read as the wrong value gives a wrong difference. |
| 318 | `    """WHY: a reader must see the result of each session in its own column (plan, rule 10), and must know which number` | Docstring: the reason for the test. A reader must see the result of each session in its own column (plan, rule 10). The sentence goes on in line 319. |
| 319 | `    of a chart row is d and which is e, also when the two markers are close."""` | Docstring: and the reader must know which number of a chart row is `d` and which is `e`, also when the two markers are close. |
| 320 | `    D, text = page({'s1': strong_session('s1'), 's2': strong_session('s2')})` | Builds a page from two strong sessions. |
| 321 | `    assert '<th>Session s1: result</th><th>Session s2: result</th>' in text` | Tests that the header row of the hypothesis table has one result column per session, `s1` and then `s2`. |
| 322 | `    r = word(D, 'H4, low intervals')` | `r`: the row of H4 at the label low. |
| 323 | `    assert set(r['per']) == {'s1', 's2'} and r['per']['s1']['used'] == '8 of 8'` | Tests that the row has values for exactly the two sessions, and that the rule used 8 of 8 processes in `s1`. |
| 324 | `    assert 'over the 4 stable low processes' in r['per']['s1']['spread'] and 'over all 4 processes' in r['per']['s1']['spread']` | Tests that the A/A spread text of `s1` names both spreads: over the 4 stable low processes of a CPU, and over all 4 processes of that CPU. |
| 325 | `    svg = M.dumbbell([(s, D['sessions'][s]['pairs']['B1']['8M']) for s in ('s1', 's2')], 'test')` | `svg`: the drawing of `M.dumbbell` for the group of B1 at 8 MiB of both sessions. |
| 326 | `    assert svg.count('style="fill:%s">-2.00<' % M.TD) == 16 and svg.count('style="fill:%s">+0.10<' % M.TE) == 16     # d blue at the left, e orange at the right` | Tests the number columns of the drawing: the value -2.00 stands 16 times in the color `TD` of `d`, and the value +0.10 stands 16 times in the color `TE` of `e`. 16 is 8 processes in each of 2 sessions. Comment: `d` is blue at the left, `e` is orange at the right. |
| 327 | `    assert svg.index('e +0.100 GB/s') < svg.index('d -2.000 GB/s')              # the dot of d is drawn after the diamond of e, so it is on top` | Tests the order of the two markers of the first row: the tooltip of `e` comes before the tooltip of `d` in the text. Comment: the dot of `d` is drawn after the diamond of `e`, so it is drawn over the diamond. |
| 328 | `    assert 'How to read the charts and tables' in text and text.count('All columns before the column "Rule"') == 1` | Tests that the page holds the box "How to read the charts and tables", and that its sentence on the columns before the column "Rule" stands on the page exactly once. |

### Helper `check_page_rules`: the page rules that a script can check (lines 331 to 350)

| Line | Source | Explanation |
|---:|---|---|
| 331 | `def check_page_rules(D, text):` | Starts the helper `check_page_rules`. Its name does not start with `test_`, so the loop of line 422 does not run it as a test. Three tests call it. |
| 332 | `    """The standing page rules that a script can check."""` | Docstring: the standing page rules that a script can check. |
| 333 | `    v = visible(text)` | `v`: the visible text of the page. |
| 334 | `    assert ';' not in v, v[max(0, v.index(';') - 80):v.index(';') + 40]` | Tests that the visible text holds no semicolon. On a failure the error message shows the text around the first semicolon. |
| 335 | `    assert 'background:#ffffff' in text and 'prefers-color-scheme' not in text` | Tests that the style sheet sets a white background, and that the page has no rule for a dark color scheme of the system. |
| 336 | `    assert not re.search(r'(src\|href)\s*=', text) and 'http://' not in text and 'https://' not in text and '@import' not in text` | Tests that the page loads nothing from another place: no attribute `src` or `href`, no web address and no `@import`. |
| 337 | `    body, refs = text.split('<h2 id="refs">')` | Splits the page at the heading of the references into `body` and `refs`. |
| 338 | `    used = set(re.findall(r'\[Ref(\d+)\]', body))` | `used`: the numbers of all citations in the body, each once. The pattern fits the text `[Ref`, digits and `]`. Its group holds the number. |
| 339 | `    listed = re.findall(r'<li>\[Ref(\d+)\]', refs)` | `listed`: the numbers of the items of the reference list, in the order of the list. |
| 340 | `    assert used == set(listed) and listed == [str(i + 1) for i in range(len(listed))], (sorted(used, key=int), listed)` | Tests two things: every cited number is listed and every listed number is cited, and the list is numbered 1, 2, 3 and so on without a gap. |
| 341 | `    sv = M.short_version(D)` | `sv`: the text of the Short version. |
| 342 | `    assert len(re.findall(r'[.!?](?:\s\|$)', sv)) <= 3, sv` | Tests that it has at most 3 sentence ends. The pattern counts each `.`, `!` or `?` that is followed by white space or by the end of the text. |
| 343 | `    assert text.index('Short version') < text.index('Words used here') < text.index('id="hyp"')` | Tests the order of three parts of the page: the Short version, then "Words used here", then the hypothesis table. |
| 344 | `    for w in re.findall(r'<td><b>([^<]+)</b></td>', text):` | Loop over the texts of all table cells that hold only one bold text. These are the word cells of the hypothesis table. |
| 345 | `        assert w in M.WORDS5, w` | Tests that each is one of the five words of `M.WORDS5`. |
| 346 | `    assert text.count('<svg') == text.count('</svg>')` | Tests that the page opens and closes the same number of drawings. |
| 347 | `    for term in ('H1', 'H2', 'H3a', 'H3b', 'H4', 'H5', 'H6', 'B1', 'B2', 'B3', 'B4', 'B6', 'C1, C2', 'A/A control, A/A spread', 'est.'):` | Loop over 15 terms: the seven hypotheses (H1, H2, H3a, H3b, H4, H5, H6), the steps B1, B2, B3, B4 and B6, the entry for C1 and C2, the entry for the A/A control and the A/A spread, and the entry for `est.` (an estimate). |
| 348 | `        assert '<li><b>%s</b>' % term in text, term` | Tests that the list "Words used here" has an item for each term. |

### Test: the page rules hold for every input, and the command line works (lines 351 to 363)

| Line | Source | Explanation |
|---:|---|---|
| 351 | `def test_page_rules_and_command_line():` | Starts the test `test_page_rules_and_command_line`. It proves that the page rules of the user hold for three kinds of input, and that the command line writes a page. This matters: the rules must hold for every input, and the page builder is used through its command line. |
| 352 | `    """WHY: the user's rules for a page (light background, no external resource, no semicolon, every reference listed,` | Docstring: the reason for the test. The rules of the user for a page are a light background, no external resource, no semicolon, every reference listed, and a Short version of at most three sentences. The list ends in line 353. |
| 353 | `    Short version of at most three sentences) hold for every input, also for an empty session."""` | Docstring: these rules hold for every input, also for an empty session. |
| 354 | `    f = strong_session('s1')` | `f`: the folders of a strong session `s1`. |
| 355 | `    for spec in ({'s1': f}, {'s1': f, 's2': strong_session('s2')}, {'s1': [folder('s1', 'B9', [])]}):` | Loop over three inputs: one session, two sessions, and a session with one B9 folder that holds no process. |
| 356 | `        D, text = page(spec)` | Builds the page of the input. |
| 357 | `        check_page_rules(D, text)` | Checks the page with `check_page_rules`. |
| 358 | `    out = os.path.join(ROOT, 'cli.html')` | `out`: the path of a page file `cli.html` in `ROOT`. |
| 359 | `    argv = ['--session', 's1'] + f + ['--session', 's2'] + strong_session('s2') + ['-o', out, '--banner', BANNER]` | `argv`: a command line with two uses of `--session` (`s1` with the folders `f`, `s2` with a new strong session), the output file and the banner text. |
| 360 | `    assert M.main(argv) == 0 and os.path.getsize(out) > 20000` | Tests that `M.main` returns 0 for this command line and that the written file is larger than 20000 bytes. |
| 361 | `    assert BANNER in open(out).read()` | Tests that the file holds the banner text. |

### Test on real folders: session 1 (lines 364 to 390)

| Line | Source | Explanation |
|---:|---|---|
| 364 | `def test_real_session_1():` | Starts the test `test_real_session_1`. It runs only when the result folders of session 1 lie below the folder `results` of the working tree. It compares the page builder with a saved output of the analysis script and with values typed into this test. This matters: the page must not give other words than the analysis output that existed before. |
| 365 | `    """WHY: the page must give the same words as the analysis output of session 1 that the lead already has, and the` | Docstring: the reason for the test. The page must give the same words as the analysis output of session 1 that the lead already has. The lead is the agent that executed the handoff note [Ref6]. The sentence goes on in line 366. |
| 366 | `    numbers of the task that were known before the page was written."""` | Docstring: and the numbers of the task that were known before the page was written. |
| 367 | `    R = os.path.join(M.CRB, 'results')` | `R`: the folder `results` below `M.CRB`, the folder two levels above the folder of the page builder. Inside this test `R` is a path. |
| 368 | `    names = ['B9-20261114T012105Z', 'B1-20261114T012315Z', 'B4-20261114T014024Z', 'B6-20261114T014825Z', 'B2-20261114T015517Z',` | Starts `names`: the names of eight result folders of session 1. This line holds those of the steps B9, B1, B4, B6 and B2. |
| 369 | `             'B3-20261114T020808Z', 'C1-20261114T022058Z', 'C2-20261114T022500Z']` | Ends `names` with those of the steps B3, C1 and C2. |
| 370 | `    ref = os.path.join(R, 'partB-s1-analysis', 'summary.json')` | `ref`: the file `summary.json` in the folder `partB-s1-analysis` below `R`. By the docstring it is the analysis output of session 1. |
| 371 | `    if not all(os.path.isdir(os.path.join(R, n)) for n in names) or not os.path.exists(ref):` | Tests whether one of the eight folders or the file is missing. |
| 372 | `        print('  skipped: the session 1 folders are not on this machine')` | Then one line is printed: the test is skipped, as the folders of session 1 are not on this machine. |
| 373 | `        return False` | Returns `False`. The loop of line 426 counts the test as skipped. |
| 374 | `    D, text = M.make([('s1', [os.path.join(R, n) for n in names])])` | Builds the page with `M.make` for one session `s1` with these folders, without a banner. |
| 375 | `    check_page_rules(D, text)` | Checks the page with `check_page_rules`. |
| 376 | `    lead = json.load(open(ref))['hypotheses']` | `lead`: the hypothesis entries of the saved file. |
| 377 | `    mine = D['summary']['hypotheses']` | `mine`: the hypothesis entries of the analysis that the page builder ran now. |
| 378 | `    for k in ('H4 (B1, 8 MiB, label low)', 'H4 (B1, 8 MiB, label high)', 'H5 (B2, asmcopy_c, label low)', 'H6 (B3)', 'H3a (B4)', 'H1 (B6)'):` | Loop over six keys: H4 at the labels low and high, H5, H6, H3a and H1. |
| 379 | `        assert mine[k]['word'] == lead[k]['word'] and mine[k]['per_session'] == lead[k]['per_session'], k` | Tests that the word and the flag of the session are equal in both. The error message names the key. |
| 380 | `    x = D['sessions']['s1']` | `x`: the values of the session. |
| 381 | `    assert x['n_procs'] == 204 and x['n_used'] == 204 and not x['missing']` | Tests three values that the test expects: 204 processes of the steps of Q1, all 204 used, and no missing step. |
| 382 | `    assert all(r['word'] != 'rejected' for r in D['hyp'])` | Tests that no row has the word `rejected`. |
| 383 | `    assert word(D, 'H3a')['word'] == 'not rejected' and 'The bounded prediction failed' in word(D, 'H3a')['per']['s1']['result']` | Tests that the word of H3a is `not rejected` and that the result of the session says that the bounded prediction failed. |
| 384 | `    assert sum(1 for r in x['pairs']['B1']['8M']['recs'] if r['d'] < 0) == 16` | Tests that `d` is below 0 in 16 processes of B1 at 8 MiB. The number 16 is typed into the test. |
| 385 | `    assert [(c, v['cases']) for c, v in x['res']['B4']['per_cpu'].items()] == [(2, ['a']), (41, [])]` | Tests the cases of B4 that the test expects: case (a) on CPU 2 and no case on CPU 41. |
| 386 | `    assert 'B9-20261114T012105Z' in visible(text) and near(x['load']['B1']['load_max'], 90.41)` | Tests that the visible text names the B9 folder, and that the highest 1-minute load average of step B1 is near 90.41 tasks. Both expected values are typed into the test. |
| 387 | `    assert sum(len(p['events'][k]) for p in x['b4'] for k in p['events']) == 0` | Tests that no interval of B4 follows an increase of the two counters. |
| 388 | `    return True` | Returns `True`: the test ran. |

### Test on real folders: both sessions (lines 391 to 420)

| Line | Source | Explanation |
|---:|---|---|
| 391 | `def test_real_two_sessions():` | Starts the test `test_real_two_sessions`. It runs only when the folders of both sessions lie in the working tree. It compares the words and the main numbers of the page with values typed into this test. This matters: these are the words and numbers of the page that was delivered. |
| 392 | `    """WHY: the words and the main numbers of the delivered page, checked against values that were recomputed from the` | Docstring: the reason for the test. It checks the words and the main numbers of the delivered page. The sentence goes on in line 393. |
| 393 | `    raw csv files by independent scripts during the review of 2026-11-14."""` | Docstring: against values that were recomputed from the raw csv files by independent scripts during the review of 2026-11-14. |
| 394 | `    N = os.path.join(M.CRB, 'new-test-kernel')` | `N`: the folder `new-test-kernel` below `M.CRB`. Inside this test the name `N` means this folder and not the counter of line 21. |
| 395 | `    R = os.path.join(M.CRB, 'results')` | `R`: the folder `results` below `M.CRB`. |
| 396 | `    try:` | Starts a block. Line 398 catches its file errors. |
| 397 | `        spec = [(s, [os.path.join(R, n) for n in open(os.path.join(N, f)).read().split()]) for s, f in (('s1', 'session1-folders.txt'), ('s2', 'session2-folders.txt'))]` | `spec`: the two sessions `s1` and `s2`. The folder names of each come from a text file in `N`: `session1-folders.txt` and `session2-folders.txt`. Each name is joined to `R`. |
| 398 | `    except OSError:` | Catches the error of a file that cannot be read. |
| 399 | `        spec = []` | Then `spec` is an empty list. |
| 400 | `    if not spec or not all(os.path.isdir(p) for _, ps in spec for p in ps):` | Tests whether `spec` is empty or one of the named folders is missing. |
| 401 | `        print('  skipped: the folders of the two sessions are not on this machine')` | Then one line is printed: the test is skipped, as the folders of the two sessions are not on this machine. |
| 402 | `        return False` | Returns `False`. The test counts as skipped. |
| 403 | `    D, text = M.make(spec)` | Builds the page with `M.make`, without a banner. |
| 404 | `    check_page_rules(D, text)` | Checks the page with `check_page_rules`. |
| 405 | `    words = {r['h']: r['word'] for r in D['hyp']}` | `words`: the word of every row of the hypothesis table, by the name of the row. |
| 406 | `    assert words == {'H1': 'rejected', 'H2': 'not tested', 'H3a': 'not rejected', 'H3b': 'not tested', 'H4, low intervals': 'not observed',` | Starts the test of all eight words against typed values: `rejected` for H1, `not tested` for H2 and H3b, `not rejected` for H3a, and `not observed` for H4 at the label low. |
| 407 | `                     'H4, high intervals': 'not observed', 'H5': 'not observed', 'H6': 'not observed'}, words` | Ends that test: `not observed` for H4 at the label high, for H5 and for H6. The error message shows the words that the page gave. |
| 408 | `    assert D['summary']['hypotheses']['H3a (B4)']['per_session'] == {'s1': 'fail', 's2': 'fail'}` | Tests that the flag of H3a is `fail` in both sessions. |
| 409 | `    assert len(word(D, 'H3a')['open']) == 2 and len(word(D, 'H1')['open']) == 1` | Tests that the row of H3a has 2 open items and the row of H1 has 1. |
| 410 | `    assert D['sessions']['s2']['b4_cases'][41]['label_dependent'] and not D['sessions']['s1']['b4_cases'][2]['label_dependent']` | Tests that the case of CPU 41 in `s2` depends on the limits, and that the case of CPU 2 in `s1` does not. |
| 411 | `    v = visible(text)` | `v`: the visible text of the page. |
| 412 | `    assert 'in 31 of 32 program runs over 2 test sessions (median per CPU: 1.18 to 2.61 GB/s slower' in v` | Tests a part of the Short version against a typed text with the count of program runs and the range of the median difference per CPU. |
| 413 | `    assert 'could use only 5 of these 32 runs' in v and 'In 384 of 384 such pairs the first interval is slower' in v` | Tests two more typed texts: the count of runs that the rule could use, and the count of A/A pairs of B6 in which the first interval is slower. |
| 414 | `    for wrong in ('at least 99.94', 'at least 99.90'):` | Loop over two texts that the page must not hold: `at least 99.94` and `at least 99.90`. |
| 415 | `        assert wrong not in v` | Tests that the text is absent. |
| 416 | `    assert v.count('99.93 % of the elapsed time') == 2 and '99.89 % of the elapsed time' in v and '99.91 % of the elapsed time' in v     # 99.9199 % is below 99.92 %` | Tests the percent values of the lowest CPU time against typed texts: one text must stand exactly twice, and two other texts must stand on the page, each at least once. Comment: 99.9199 % is below 99.92 %. So the test also checks the rule that this value is cut and never rounded up. |
| 417 | `    assert 'Over the 19 rows of B1, B2, B3, B6, C2' in v and '3 h 14 min apart' in v` | Tests two more typed texts: the count of rows of the steps with reference intervals, and the time between the two sessions in hours and minutes. |
| 418 | `    return True` | Returns `True`: the test ran. |

### The start of the script: run every test (lines 421 to 431)

| Line | Source | Explanation |
|---:|---|---|
| 421 | `if __name__ == '__main__':` | Tests whether the file runs as a program. |
| 422 | `    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]` | `tests`: every function of this file whose name starts with `test_`, in the order of the names. So the tests do not run in the order of the file. |
| 423 | `    skipped = 0` | `skipped`: the count of skipped tests, 0 at the start. |
| 424 | `    for t in tests:` | Loop over the tests. |
| 425 | `        print(t.__name__)` | Prints the name of the test before it runs. |
| 426 | `        if t() is False:` | Runs the test. A return value of `False` means that the test was skipped. |
| 427 | `            skipped += 1` | Counts the skipped test. |
| 428 | `    if not KEEP:` | Tests whether `--keep` was not given. |
| 429 | `        shutil.rmtree(ROOT, ignore_errors=True)` | Then the folder `ROOT` with all invented folders and pages is removed. An error of the removal is ignored. |
| 430 | `    shutil.rmtree(T.TMP, ignore_errors=True)` | Removes the temporary folder that the import of `test_analyze_bwx.py` created (line 16). |
| 431 | `    print('%d tests passed, %d skipped%s' % (len(tests) - skipped, skipped, '' if not KEEP else ', files kept in ' + KEEP))` | Prints one line: the count of tests that passed, the count of skipped tests, and with `--keep` the folder that holds the files. A failed test never reaches this line: its `assert` stops the script with a Python error. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the test plan of 2026-11-13: the question Q1, the table of the hypotheses, the rules 3, 4, 5, 10 and 11, and the table of the steps B1 to B6.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff note: section B.3 (the rows `I`, `T`, `P` and `C`), section B.9 (the sequences of the steps) and section B.10 (the numeric decision rules, with the cases of step B4).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q1_html.py`: the page builder under test. The tests call its functions `make`, `main`, `short_version`, `sec_b4` and `dumbbell`, its class `Refs`, and read its values `TD`, `TE`, `WORDS5` and `CRB`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/test_analyze_bwx.py`: the row writer `block`, the block builders `b1`, `b4` and `b6`, the rate functions `copy_rate` and `b6_rate`, and the sequences `B1SEQ` and `B6SEQ`.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/analyze_bwx.py`: the analysis script: the parser and the decision rules whose words the page prints.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: the result note of the test. Its list "Words used here" defines the lead as the agent that executed the handoff.
