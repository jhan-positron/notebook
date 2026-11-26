# `test_analyze_bwx.py` explained, line by line

- Source file: `bwx-2026-11-13/test_analyze_bwx.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 683 lines, 47073 bytes).
- sha256 of the source when this page was built: `5035ed0747e030a2b9af5c981763977e7332ce5583bfac8999497d971279684c`.

## Short version: purpose

`test_analyze_bwx.py` holds 28 tests of the analysis script `analyze_bwx.py`. Each test writes csv files with invented rates in the row format of the runner `bwx`, runs the analysis on them, and checks one decision rule or one part of the output. No test uses a measurement, so a passed test says something about the analysis and nothing about CRB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D [Ref2].
- **Handoff note**: the file `handoff.md`. It tells how to execute the plan. Its section B.3 gives the rows of the result files, and its section B.10 gives the decision rules in words [Ref1].
- **Deviations note**: the file `DEVIATIONS-scripts.md` in the folder of this file. Its points A1 to A33 say where the analysis adds to the handoff note or differs from it [Ref3].
- **Analysis**: the script `analyze_bwx.py`. This file imports it under the name `ab`.
- **Test**: one function of this file whose name starts with `test_`. It holds one or more checks.
- **Check**: one `assert` line. It stops the run with an error when its condition is false.
- **Block**: the text of one invented process: a header line and the rows of the runner after it. The function `block` builds it.
- **Step**: one named batch of processes of the plan, for example `B1` or `C3`. `SHORT` is a short trial run of every sequence.
- **Session, in Parts B and C**: one run of all steps. The plan asks for 2 sessions some hours apart. This is not the session of the later rerun.
- **Sequence, entry**: the sequence is the ordered list of kernels that one process times (option `--seq`). An entry is one element of it: a kernel name, or a kernel name with a size, as in `oldread@1M`.
- **Header line**: the line that the run script `run_bwx.sh` writes before each process. It starts with `-- step` and holds the step, the tag, the binary, the wait, the load record, the number of logins, the time and the arguments.
- **Tag**: the name that the run script gives to one process.
- **`I` row, `T` row, `P` row, `C` row**: the four kinds of data rows of the runner. `I`: one row per interval. `T`: one row per thread and interval, with the bytes and the times of the thread. `P`: the page state of one buffer. `C`: the counter values of one thread in one interval.
- **Elapsed time**: the column `elapsed_s` of a `T` row: the time between the clock reading of the thread before its first kernel call of the interval and its clock reading after the last.
- **`M_hist`**: a total rate of an interval: the bytes of all threads, divided by the longest elapsed time of a thread.
- **`M_sum`**: a total rate of an interval: the sum of the rates of the threads. Each thread is divided by its own elapsed time.
- **`q`**: the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one interval. A value near 1 means that all threads have nearly the same rate.
- **Pattern: split, uniform, mixed**: the label of an interval with many threads. Split is a `q` below 0.65, and uniform is a `q` above 0.85. A thread count is mixed unless all its intervals have the same one of these two labels.
- **A/A pair**: one loop that exists in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, and high is above 70.5 GB/s. The two limits are provisional.
- **Process value, `d`, `e`**: one number per process. In a step with one thread, `d` is the median of the differences between the compared kernel and its partner, and `e` is the median of the A/A differences of the same process.
- **`D`, `E`**: the two process values of a step with many threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Setting**: one combination of the timing options of a step with many threads: the stop method, the interval length in ms and the start method, written as in `pass/500/common`.
- **Reproduction condition**: the setting `pass/500/common` of step B7: whole passes, 0.5 s and the common start [Ref2].
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision, or for an event that did not occur.
- **Hypothesis, H1 to H11**: a possible explanation that the plan names, with a label such as H4. Each one makes a bounded prediction that one step tests [Ref2].
- **Flag of a session**: the result of one session for one hypothesis: `fail` (the prediction failed), `hold`, `not observed` or `not resolved`.
- **Late thread**: a thread whose `T` row has the flag `late`.
- **End skew**: the latest end time of a thread minus the earliest end time, inside one interval.
- **Irregular interval**: an interval with a late thread, or, with the common stop, with an end skew above 5 ms. It is listed and not used for a decision.
- **Coverage: full, none, partial**: the share of a buffer that lies on huge pages, read from a `P` row.
- **Bracket**: in step B8, the two counts of mesh-1 threads between which the pattern of a kernel changes from split to uniform.
- **Spread of a kernel**: in step B10, the highest minus the lowest `M_hist` of the intervals of one kernel in one process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the spread, one for the total rate and one for the rate of each mesh.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.
- **JSON**: a text format for nested lists and dictionaries.

## Main flow

1. The file imports the analysis and defines the sequences of the steps B1, B6, B7, B8, B5 and B10 as texts (lines 8 to 19).
2. The helpers follow. `block` builds the text of one process from a rate function, and `analyze` writes such texts to csv files in a temporary folder and runs the analysis on them (lines 22 to 102).
3. Tests of the steps with one thread: the parsing and the processes left out, four tests of step B1, one test each of the steps B6 and B3, and two tests of step B4 (lines 107 to 269).
4. Tests of the steps with 120 threads: four tests of step B7, then the brackets of B8, the answer of B5, the pattern of B9, the words without labels, and the spread and H11 of B10 (lines 274 to 509).
5. Tests of the counter rows, of the step SHORT, of the words over two sessions and of the command line with its output files (lines 514 to 567).
6. Six tests that were added after the review: the preconditions of H7 and H6, the disagreement of the two metrics in three places, and the counter tables (lines 571 to 668).
7. `main` runs every test in the alphabetical order of the test names, deletes the temporary folder and prints the result line (lines 671 to 683).

## Behavior a reader must know

- Every rate, time and counter value in the tests is invented. A rate function gives the rate of each thread, and `block` computes the bytes as rate times 1e9 times elapsed time (line 53).
- `block` writes the rows that the analysis reads. It does not model the runner in every detail: the planned start equals the real start with both stop methods (line 55), and the system counters of the `P` rows never change (line 43).
- A failed check ends the whole run with a Python error and exit status 1. The later tests do not run then. The temporary folder is deleted in every case (lines 673 to 678).
- The tests run in the alphabetical order of their names, not in the order of the file (line 672). No test reads a file of another test.
- Every call of `analyze` also turns the summary into JSON and builds the text table of each step (lines 94 to 97). So these two output paths are exercised by every test.
- The import of the analysis also imports `decide.py` (line 11). In the code repo that file lies in the folder `new-test-kernel` beside this folder, where the analysis does not look for it. So in the repo layout the tests start only when the environment variable `DECIDE_DIR` names that folder.
- In `test_b4_cases` the variable `other` is set and never used (line 247).
- The check of line 128 has two halves that are joined with `or`. With the input of the test only the second half is true.
- The deviations note records one trial of the first 20 tests: the analysis was changed in 16 ways, one at a time, and 15 of the changes made a test fail. The change that no test saw removed the check that two reference intervals are 3 positions apart [Ref3].

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/test_analyze_bwx.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (683 lines, 47073 bytes, sha256 `5035ed0747e030a2b9af5c981763977e7332ce5583bfac8999497d971279684c`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring, imports and the sequences of the steps (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_analyze_bwx.py - synthetic tests of analyze_bwx.py. Run: python3 test_analyze_bwx.py` | Starts the docstring of the file. It ends in line 7. The file holds tests of `analyze_bwx.py` on invented data, which the docstring calls synthetic tests. The command `python3 test_analyze_bwx.py` runs them. |
| 4 | `The tests write csv files in the format of handoff B.3 (header line of run_bwx.sh, then the I, T, P and C rows` | Docstring: the tests write csv files in the format of section B.3 of the handoff note: the header line of the run script `run_bwx.sh`, then the `I`, `T`, `P` and `C` rows. The sentence goes on in line 5. |
| 5 | `as bwx prints them), run the analysis on them, and assert the decisions. Each test says WHY the rule matters.` | Docstring: the rows have the form in which the runner `bwx` prints them. The tests run the analysis on these files and check its decisions. Each test says why its rule matters. |
| 6 | `No test uses measured data. All rates are invented.` | Docstring: no test uses measured data. All rates are invented. |
| 7 | `"""` | Ends the docstring. |
| 8 | `import json, os, shutil, sys, tempfile` | Loads five modules of the Python standard library. `json` writes and reads JSON. `os` builds paths and makes folders. `shutil` deletes a folder tree. `sys` gives the module search path and the standard output. `tempfile` makes a temporary folder. |
| 10 | `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` | Puts the folder of this file at the front of the module search path of Python. So line 11 finds the `analyze_bwx.py` that lies beside this file. |
| 11 | `import analyze_bwx as ab  # noqa: E402` | Imports the analysis script as the module `ab`. The import does not start its `main`. It does run the import of `decide.py` inside that script. The comment `noqa: E402` tells a style checker to accept an import that does not stand at the top of the file. |
| 13 | `B1SEQ = 'asmread,copy,asmcopy,asmread,asmcopy,copy,asmread,asmcopy,asmcopy2,asmread,asmcopy2,asmcopy,asmread'` | `B1SEQ`: the sequence of step B1, with 13 entries. `asmread` is the reference kernel at the positions 0, 3, 6, 9 and 12. Between the references stand the pairs `copy,asmcopy`, `asmcopy,copy`, `asmcopy,asmcopy2` and `asmcopy2,asmcopy`. So one round holds 2 pairs of the kernel comparison and 2 A/A pairs [Ref1]. |
| 14 | `B6SEQ = 'asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,oldread,oldread2,asmread,oldread2,oldread,asmread'` | `B6SEQ`: the sequence of step B6, built in the same way. The kernel pairs are `oldread` with `oldread@1M`: old read at the buffer size and at 1 MiB. The A/A pairs are `oldread` with `oldread2`. |
| 15 | `B7SEQ = 'oldread,read,asmread,asmread2,asmread2,asmread,read,oldread'` | `B7SEQ`: the sequence of step B7: `oldread`, `read`, `asmread`, `asmread2`, and then the same four in the reversed order. So each kernel has two intervals per round. |
| 16 | `B8SEQ = 'oldread,asmread,asmread2,asmread2,asmread,oldread'` | `B8SEQ`: the sequence of step B8: `oldread`, `asmread`, `asmread2`, and then the same three in the reversed order. |
| 17 | `B5SEQ = 'oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2'` | `B5SEQ`: the sequence of step B5: `oldread`, `read`, the variant `read_sparse`, four variants with `nop` instructions (`read_nop4` to `read_nop32`), `asmread` and `asmread2`. |
| 18 | `B10SEQ = 'oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite'` | `B10SEQ`: the sequence of step B10: the four write kernels `oldwrite`, `write`, `asmwrite` and `asmwrite2`, and then the same four in the reversed order. |
| 19 | `ALL = '--threads 120 --cpus 0-63,64-119 --bytes 256M'` | `ALL`: the options of a process with 120 threads: the CPUs 0 to 63 and 64 to 119, and a buffer of 256 MiB per thread. |

### Helpers `size` and `cpus_of` (lines 22 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `def size(s):` | Starts the function `size`. It turns a size text with a letter, such as `8M`, into a number of bytes. |
| 23 | `    return int(s[:-1]) << {'K': 10, 'M': 20, 'G': 30}[s[-1]]` | Takes the number before the last character and shifts it left by 10, 20 or 30 bits for the letter `K`, `M` or `G`. So `8M` gives 8388608. |
| 26 | `def cpus_of(s):` | Starts the function `cpus_of`. It turns a CPU list such as `0-63,64-119` into a list of CPU numbers. |
| 27 | `    out = []` | `out`: the list, empty at first. |
| 28 | `    for part in s.split(','):` | Loop over the parts between the commas. |
| 29 | `        a, _, b = part.partition('-')` | Splits a part at its first `-`. `a` is the text before it and `b` the text after it. `b` is empty for a single CPU. |
| 30 | `        out += range(int(a), int(b or a) + 1)` | Adds the CPUs from `a` to `b`, both included. For a single CPU it adds `a` alone. |
| 31 | `    return out` | Returns the list. |

### Helper `block`: the text of one invented process (lines 34 to 77)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `def block(step, tag, args, rate, binary='bwx', elapsed=None, flag=None, page=None, counts=None, tail=None, drop=0, load='0.52 0.40 0.30 1/913'):` | Starts the function `block`. It builds the text of one process: the header line and all rows. `rate` is a function that gives the rate of a thread in GB/s. The other arguments are optional: `binary` (the name in the header line), `elapsed`, `flag`, `page` and `counts` (functions that set single values), `tail` (a line to add at the end), `drop` (a number of lines to cut at the end) and `load` (the four fields of the load record). |
| 35 | `    """One process as run_bwx.sh and bwx write it. rate(r, pos, entry, tid, cpu) -> GB/s of the thread."""` | Docstring: the text is one process as `run_bwx.sh` and `bwx` write it. `rate` is called with the round, the position, the entry, the thread number and the CPU, and it gives the rate of the thread in GB/s. |
| 36 | `    a = args.split()` | `a`: the arguments of the runner, split at spaces. |
| 37 | `    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d` | `opt`: a small function that gives the value after the option `k`, or `d` when the option is missing. |
| 38 | `    seq, rounds, cpus = opt('--seq').split(','), int(opt('--rounds', '1')), cpus_of(opt('--cpus'))` | `seq`: the entries of `--seq`. `rounds`: the value of `--rounds`, 1 when it is missing. `cpus`: the CPU list of `--cpus` as numbers. |
| 39 | `    nbytes, ms, stop = size(opt('--bytes', '1M')), int(opt('--min-ms')), opt('--stop', 'pass')` | `nbytes`: the buffer size in bytes, 1 MiB when `--bytes` is missing. `ms`: the value of `--min-ms`. `stop`: the stop method, `pass` when it is missing. |
| 40 | `    L = ['-- step %s tag %s binary %s waited_s 0 loadavg %s logins 1 utc 12:00:00 args %s' % (step, tag, binary, load, args),` | `L`: the lines of the text. The first line is the header line: the step, the tag, the binary, a wait of 0 s, the load record, 1 login, the time `12:00:00` and the arguments. The list goes on in line 41. |
| 41 | `         '# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); synthetic']` | Continues line 40: the second line is a comment line of the kind that the runner prints first. It is marked with the word `synthetic`. |
| 42 | `    multi, t, kb = len(cpus) > 1, 1.0, nbytes // 1024` | `multi`: true for more than one thread. `t`: a running time stamp in seconds, 1.0 at first. `kb`: the buffer size in kB. |
| 43 | `    vm = '1000,5,7,90'` | `vm`: the four system counters of a `P` row as one fixed text: `thp_fault_alloc` 1000, `thp_fault_fallback` 5, `thp_collapse_alloc` 7 and `pgmigrate_success` 90. They never change. So in step B4 the two counters that the analysis compares at a level change are always equal. Such a change then counts as one with no sign of a page change, unless the coverage is unknown or differs between the two intervals. |
| 44 | `    if multi:` | Only for more than one thread. |
| 45 | `        L += ['P,0,-1,%d,a,%d,%d,%s' % (tid, kb, kb, vm) for tid in range(len(cpus))]` | Adds one `P` row per thread with the position -1 and full coverage. A runner with many threads prints such rows for the page state before the first interval [Ref1]. |
| 46 | `    for r in range(rounds):` | Loop over the rounds. |
| 47 | `        for pos, entry in enumerate(seq):` | Loop over the positions and entries of the sequence. |
| 48 | `            name = entry.split('@')[0]` | `name`: the kernel name: the entry without its size. |
| 49 | `            esize = size(entry.split('@')[1]) if '@' in entry else nbytes` | `esize`: the size of the entry in bytes: the size after the character `@`, or the buffer size. |
| 50 | `            rows = []` | `rows`: the values of the threads for this interval, empty at first. |
| 51 | `            for tid, cpu in enumerate(cpus):` | Loop over the threads. The thread number counts from 0, and each thread gets the next CPU of the list. |
| 52 | `                el = (elapsed(r, pos, entry, tid) if elapsed else None) or ms / 1000.0` | `el`: the elapsed time of the thread in seconds. It is the value that the function `elapsed` gives. When no such function is given, or when it gives `None`, it is the value of `--min-ms` in seconds. |
| 53 | `                b = int(round(rate(r, pos, entry, tid, cpu) * 1e9 * el))` | `b`: the bytes of the thread: the wanted rate times 1e9 times the elapsed time, rounded to a whole number. So the analysis computes the wanted rate again when it divides the bytes by the elapsed time. |
| 54 | `                ts = t + 0.002` | `ts`: the start time of the thread, 2 ms after `t`. |
| 55 | `                rows.append((tid, cpu, b, el, t + 0.002 if stop == 'common' else ts, ts, ts + el, flag(r, pos, tid) if flag else '-'))` | Adds the values of the thread: its number, its CPU, the bytes, the elapsed time, the planned start, the start, the end (the start plus the elapsed time) and the flag. The flag is `-` unless the function `flag` gives another text. Both branches of the test on `stop` give the same planned start, so the stop method changes nothing in this line. |
| 56 | `            pg = page(r, pos) if page else (kb, kb)` | `pg`: the pair of `kB_total` and `kB_huge` for the `P` row: the value of the function `page`, or full coverage without it. |
| 57 | `            if not multi:` | Only for one thread. |
| 58 | `                L.append('P,%d,%d,0,a,%s,%s,%s' % (r, pos, pg[0], pg[1], vm))` | Adds the `P` row of buffer `a` before the other rows of the interval, as a runner with one thread prints it. |
| 59 | `            total, longest = sum(x[2] for x in rows), max(x[3] for x in rows)` | `total`: the sum of the bytes of all threads. `longest`: the longest elapsed time of a thread. |
| 60 | `            L.append('I,%d,%d,%s,%d,%d,%d,%.6f,%.2f' % (r, pos, name, esize, len(cpus), total, longest, total / longest / 1e9))` | Adds the `I` row: the round, the position, the kernel, the entry size, the number of threads, the total bytes, the longest elapsed time, and the rate `total / longest / 1e9` with 2 decimals. |
| 61 | `            for x in rows:` | Loop over the threads. |
| 62 | `                L.append('T,%d,%d,%s,%d,%d,%d,%.6f,%.6f,%.6f,%.6f,%.3f,%s' % (r, pos, name, x[0], x[1], x[2], x[3], x[4], x[5], x[6],` | Adds the `T` row of the thread with its 13 fields. The times have 6 decimals (1 us). The call goes on in line 63. |
| 63 | `                                                                         x[2] / esize / (2 if 'copy' in name else 1), x[7]))` | Continues line 62: the passes are the bytes divided by the entry size, and by 2 more for a kernel with `copy` in its name. The flag is the last field. |
| 64 | `            if counts:` | Only when the caller gave a function `counts`. |
| 65 | `                for x in rows:` | Loop over the threads. |
| 66 | `                    L.append('C,%d,%d,%s,%d,%d,%s' % (r, pos, name, x[0], x[1], counts(r, pos, entry, x[0], x[2])))` | Adds one `C` row per thread. The function `counts` gives the text of all fields after the CPU: the enabled time, the running time, the CPU time and the counts. |
| 67 | `            if multi:` | Only for more than one thread. |
| 68 | `                L += ['P,%d,%d,%d,a,%d,%d,%s' % (r, pos, tid, kb, kb, vm) for tid in range(len(cpus))]` | Adds one `P` row per thread after the interval, with full coverage, as a runner with many threads prints them. |
| 69 | `                L.append('# page_read,%d,%d,3.210 ms' % (r, pos))` | Adds the comment line `# page_read` with a fixed time of 3.210 ms. The runner prints such a line after each page reading of a process with many threads. |
| 70 | `            t += longest + 0.01` | Moves `t` forward by the longest elapsed time plus 10 ms. So the intervals follow each other in time. |
| 71 | `    if drop:` | Only when `drop` is not 0. |
| 72 | `        L = L[:-drop]` | Cuts the last `drop` lines. |
| 73 | `    if tail:` | Only when `tail` is given. |
| 74 | `        L.append(tail)` | Adds the line `tail`, for example a `-- killed` line. |
| 75 | `    return '\n'.join(L) + '\n'` | Returns the lines as one text. |

### The temporary folder, and the helpers `analyze` and `near` (lines 78 to 104)

| Line | Source | Explanation |
|---:|---|---|
| 78 | `TMP = tempfile.mkdtemp(prefix='bwx-test-')` | `TMP`: a new temporary folder whose name starts with `bwx-test-`. All files of the tests go there. |
| 79 | `N = [0]` | `N`: a counter of the calls of `analyze`. It is kept in a list, so the function can change it. |
| 82 | `def analyze(sessions):` | Starts the function `analyze` of this test file. It writes invented csv files and runs the analysis on them. |
| 83 | `    """sessions: {session name: {csv name: [block text, ...]}} -> summary."""` | Docstring: `sessions` maps a session name to its files, and each file name to a list of block texts. The result is the summary of the analysis. |
| 84 | `    N[0] += 1` | Counts the call. |
| 85 | `    loaded = {}` | `loaded`: the processes per session, empty at first. |
| 86 | `    for s, files in sessions.items():` | Loop over the sessions. |
| 87 | `        d = os.path.join(TMP, 'case%d' % N[0], s)` | `d`: the folder of this session for this call, for example `case3/s1` below `TMP`. |
| 88 | `        os.makedirs(d)` | Makes the folder. |
| 89 | `        for name, blocks in files.items():` | Loop over the files of the session. |
| 90 | `            with open(os.path.join(d, name), 'w') as fh:` | Opens the file for writing. |
| 91 | `                fh.write(''.join(blocks))` | Writes the blocks one after the other. |
| 92 | `        loaded[s] = ab.load_session(s, [d])` | Reads the folder with `load_session` of the analysis, as its `main` does for a result folder. |
| 93 | `    out = ab.analyze(loaded)` | `out`: the summary that the function `analyze` of the analysis computes. |
| 94 | `    json.dumps(out, default=str)                 # the summary must be writable as json` | Turns the summary into JSON text and drops the text. By the comment the summary must be writable as JSON. So an error here fails the test that called. |
| 95 | `    for s, res in out['sessions'].items():` | Loop over the sessions of the summary. |
| 96 | `        for step, r in res.items():` | Loop over the steps. |
| 97 | `            ab.text_step(s, step, r)             # and as text` | Builds the text table of the step and drops it. So every test also proves that the tables of its steps can be built. |
| 98 | `    return out` | Returns the summary. |
| 101 | `def near(a, b, tol=0.05):` | Starts the function `near`. It tests whether two numbers are equal within a tolerance. The tolerance is 0.05 unless the caller gives another. |
| 102 | `    return abs(a - b) <= tol` | True when the absolute difference is at most `tol`. |

### Helpers `copy_rate` and `b1`: one process of step B1 (lines 105 to 119)

| Line | Source | Explanation |
|---:|---|---|
| 105 | `# ------------------------------------------------------------ one thread` | Comment: a divider. The tests of the steps with one thread start here. |
| 107 | `def copy_rate(ref=67.5, copy=56.0, asm=58.0, asm2=58.1, ref_by_round=None):` | Starts the function `copy_rate`. It returns a rate function for the sequence of step B1. The defaults are 67.5 GB/s for the reference kernel (a low level), 56.0 for `copy`, 58.0 for `asmcopy` and 58.1 for `asmcopy2`. So by default `d` is -2.0 GB/s and `e` is +0.1 GB/s. |
| 108 | `    def f(r, pos, entry, tid, cpu):` | Starts the inner function `f`, the rate function. |
| 109 | `        if entry == 'asmread':` | For the reference kernel `asmread`. |
| 110 | `            return ref_by_round[r] if ref_by_round else ref` | Returns the rate of this round from the list `ref_by_round` when it is given. If not, it returns `ref`. |
| 111 | `        return {'copy': copy, 'asmcopy': asm, 'asmcopy2': asm2}.get(entry, copy)` | Returns the rate of the entry: `copy`, `asmcopy` or `asmcopy2`. Any other entry, such as a variant of step B2, gets the rate of `copy`. |
| 112 | `    return f` | Returns the rate function. |
| 115 | `def b1(cpu, i, rate, bytes_='8M', rounds=4, step='B1', seq=B1SEQ, binary='bwx', **kw):` | Starts the function `b1`. It builds one process of step B1 with one thread on the CPU `cpu`. `i` is the number of the process on that CPU. The defaults are a buffer of 8 MiB, 4 rounds, the step name `B1`, the sequence `B1SEQ` and the binary `bwx`. |
| 116 | `    return block(step, '%s-cpu%d-p%d' % (bytes_, cpu, i), '--threads 1 --cpus %d --bytes %s --seq %s --rounds %d --min-ms 300 --stop pass' % (cpu, bytes_, seq, rounds),` | Calls `block` with a tag of the form `8M-cpu2-p1` and the options of step B1: 1 thread, intervals of at least 300 ms and the whole-pass stop. The call goes on in line 117. |
| 117 | `                 rate, binary=binary, **kw)` | Continues line 116: the rate function, the binary and every further argument go to `block`. |

### Test: a killed or cut process gives no value (lines 120 to 134)

| Line | Source | Explanation |
|---:|---|---|
| 120 | `def test_parse_and_left_out():` | Starts the test `test_parse_and_left_out`. |
| 121 | `    """WHY: a killed or cut process must not give a value, and the report must name it."""` | Docstring, the reason of the test: a killed or cut process must not give a value, and the report must name it. |
| 122 | `    good = b1(2, 1, copy_rate())` | `good`: one complete process on CPU 2. |
| 123 | `    killed = b1(2, 2, copy_rate(), tail='-- killed tag 8M-cpu2-p2 status 3 utc 12:00:09')` | `killed`: the same process with a `-- killed` line at its end, as the run script writes one when it stops the runner. |
| 124 | `    cut = b1(2, 3, copy_rate(), drop=1)            # the last T row is missing` | `cut`: the same process without its last line. By the comment this is the last `T` row. |
| 125 | `    s = analyze({'s1': {'B1.csv': [good, killed, cut]}})['sessions']['s1']['B1']` | Runs the analysis on one file with the three processes and takes the result of step B1. |
| 126 | `    assert s['n_processes'] == 3 and s['n_used'] == 1, s['n_used']` | Proves that all 3 processes are counted and only 1 is used. A killed or cut process that gave values would put a part of a run into a decision. |
| 127 | `    assert {x['tag']: x['reason'] for x in s['left_out']}['8M-cpu2-p2'] == 'killed'` | Proves that the report names the killed process with the reason `killed`. |
| 128 | `    assert 'intervals' in {x['tag']: x['reason'] for x in s['left_out']}['8M-cpu2-p3'] or 'T rows' in str(s['left_out'])` | Proves that the cut process is listed with a reason. The check passes when the reason of the cut process holds the word `intervals`, or when the text of the whole list holds `T rows`. With this input the second half holds: the last interval has its `I` row and no `T` row. |
| 129 | `    assert s['load']['loadavg_1min_max'] == 0.52                     # the load of the launches is reported` | Proves that the report holds the load of the starts: the highest load average over 1 minute is the 0.52 of the invented header lines. The handoff note asks for the system load in every result [Ref1]. |
| 130 | `    p = ab.load_session('x', [os.path.join(TMP, 'case%d' % N[0], 's1')])[0]` | Reads the same folder once more and takes its first process, the complete one. |
| 131 | `    assert len(p.iv) == 52 and len(p.P) == 52 and p.cpu == 2 and p.bytes == 8 << 20 and p.stop == 'pass'` | Proves the parsing of the header line and of the rows: 52 intervals (13 entries times 4 rounds), 52 `P` rows, the CPU 2, 8388608 bytes and the stop method `pass`. |
| 132 | `    assert near(p.iv[(0, 1)].rate, 56.0, 0.001) and p.iv[(0, 1)].entry == 'copy'` | Proves the rate of one interval: round 0 at position 1 has 56.0 GB/s within 0.001 GB/s, the rate that the test set for `copy`, and its entry is `copy`. The `I` row of this interval holds the same rate, 56.00 GB/s. So this check does not show whether the rate comes from the `T` row or from the `I` row. |

### Tests of step B1: resolved per CPU, and CPUs are not pooled (lines 135 to 160)

| Line | Source | Explanation |
|---:|---|---|
| 135 | `def test_b1_resolved_per_cpu():` | Starts the test `test_b1_resolved_per_cpu`. |
| 136 | `    """WHY: a difference is resolved only per CPU, with the sign kept, against the A/A spread of the same processes."""` | Docstring, the reason: a difference is resolved only per CPU, with its sign kept, against the A/A spread of the same processes. |
| 137 | `    blocks = [b1(c, i, copy_rate(asm2=58.0 + 0.02 * i)) for c in (0, 2, 41, 94) for i in range(1, 5)]` | 16 processes at 8 MiB: 4 on each of the CPUs 0, 2, 41 and 94. `copy` is 2.0 GB/s below `asmcopy`. `asmcopy2` lies 0.02 GB/s times the process number above `asmcopy`, so `e` is 0.02 to 0.08 GB/s. |
| 138 | `    blocks += [b1(c, i, copy_rate(ref=30.0), bytes_='16M') for c in (0, 2) for i in range(1, 5)]` | 8 more processes at 16 MiB on the CPUs 0 and 2, with a reference rate of 30.0 GB/s. |
| 139 | `    g = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']` | Runs the analysis and takes the groups of step B1. |
| 140 | `    low = g['8M']['labels']['low']` | `low`: the result of the 8 MiB group for the label `low`. |
| 141 | `    assert low['decision'] == 'resolved' and low['sign'] == -1 and low['n_processes'] == 16` | Proves that the label is resolved with a negative sign and counts 16 processes. All four CPUs are resolved with the same sign. |
| 142 | `    c = low['per_cpu'][41]` | `c`: the result of CPU 41. |
| 143 | `    assert c['n_processes'] == 4 and near(c['median_d'], -2.0, 0.01) and near(c['aa_spread'], 0.08, 0.011)` | Proves the numbers of one CPU: 4 processes, a median `d` of -2.0 GB/s, and an A/A spread of 0.08 GB/s, the largest `e` of its four processes. |
| 144 | `    # no process was at the high level: "high" is "not observed", with the reason, and is not filled from "low"` | Comment: no process was at the high level. So the label `high` must be `not observed` with the reason, and it must not be filled from `low`. |
| 145 | `    assert g['8M']['labels']['high']['decision'] == 'not observed' and 'Insufficient data' in g['8M']['labels']['high']['note']` | Proves that: the label `high` is `not observed`, and its note holds `Insufficient data`. |
| 146 | `    # at 16 MiB no level is defined: the label is "none" and every process gives a value` | Comment: at 16 MiB no level is defined. The label is `none`, and every process gives a value. |
| 147 | `    assert list(g['16M']['labels']) == ['none'] and g['16M']['labels']['none']['decision'] == 'resolved'` | Proves that the 16 MiB group has the label `none` alone and that it is resolved. The reference rate is not used in that group. |
| 150 | `def test_cpus_are_not_pooled():` | Starts the test `test_cpus_are_not_pooled`. |
| 151 | `    """WHY: 6 processes that all say -2 GB/s are enough only if 2 CPUs have 3 each. A pooled count would pass."""` | Docstring, the reason: 6 processes that all say -2 GB/s are enough only if 2 CPUs have 3 each. A count over both CPUs together would pass. |
| 152 | `    blocks = [b1(0, i, copy_rate()) for i in range(1, 5)] + [b1(2, i, copy_rate()) for i in range(1, 3)]` | 4 processes on CPU 0 and 2 processes on CPU 2, all with a `d` of -2.0 GB/s. |
| 153 | `    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']` | Runs the analysis and takes the label `low` of the 8 MiB group. |
| 154 | `    assert low['decision'] == 'not observed' and low['per_cpu'][0]['decision'] == 'resolved' and low['per_cpu'][2]['decision'] == 'not observed'` | Proves that the label is `not observed`: CPU 0 alone is resolved, and CPU 2 with its 2 processes is `not observed`. A decision over the 6 processes together would have passed the limit of 3. |
| 155 | `    # opposite signs on two CPUs do not cancel and do not add: the label is not resolved` | Comment: opposite signs on two CPUs do not cancel and do not add. The label is not resolved. |
| 156 | `    blocks = [b1(0, i, copy_rate()) for i in range(1, 5)] + [b1(2, i, copy_rate(copy=60.0)) for i in range(1, 5)]` | 4 processes on CPU 0 with a `d` of -2.0 GB/s, and 4 on CPU 2 with `copy` at 60.0 GB/s. There `d` is +2.0 GB/s. |
| 157 | `    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']` | Runs the analysis again. |
| 158 | `    assert low['decision'] == 'not resolved' and low['per_cpu'][0]['sign'] == -1 and low['per_cpu'][2]['sign'] == 1` | Proves that the label is `not resolved`, with the sign -1 on CPU 0 and the sign 1 on CPU 2. So a difference that changes its sign between CPUs never counts as resolved. |

### Tests of step B1: one process counts once, and a changing process gives no value (lines 161 to 183)

| Line | Source | Explanation |
|---:|---|---|
| 161 | `def test_one_process_counts_once():` | Starts the test `test_one_process_counts_once`. |
| 162 | `    """WHY: a process with 10 times more intervals must not outvote three processes (plan, rule 4)."""` | Docstring, the reason: a process with 10 times more intervals must count as one process, and not as more than three other processes together (rule 4 of the plan). |
| 163 | `    blocks = []` | `blocks`: empty at first. |
| 164 | `    for c in (0, 2):` | Loop over the CPUs 0 and 2. |
| 165 | `        blocks += [b1(c, i, copy_rate(copy=58.5)) for i in range(1, 4)]           # d = +0.5 in 3 processes, 8 pairs each` | 3 processes with `copy` at 58.5 GB/s. By the comment `d` is +0.5 GB/s in each, from 8 pairs. |
| 166 | `        blocks += [b1(c, 4, copy_rate(copy=53.0), rounds=40)]                     # d = -5 in 1 process, 80 pairs` | 1 process with `copy` at 53.0 GB/s and 40 rounds. By the comment `d` is -5 GB/s, from 80 pairs. |
| 167 | `    low = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']['labels']['low']` | Runs the analysis and takes the label `low` of the 8 MiB group. |
| 168 | `    assert low['per_cpu'][0]['n_processes'] == 4 and low['decision'] == 'not resolved'       # the signs differ` | Proves that CPU 0 counts 4 processes and that the label is `not resolved`. By the comment the signs of the four `d` values differ. |
| 169 | `    assert near(low['per_cpu'][0]['median_d'], 0.5, 0.01)        # median over 4 processes; over the 104 pairs it would be -5` | Proves that the median `d` of CPU 0 is +0.5 GB/s: the median over the 4 process values. By the comment the median over all 104 pairs would be -5 GB/s. So one long process counts as one value. |
| 172 | `def test_changing_process_gives_no_value():` | Starts the test `test_changing_process_gives_no_value`. |
| 173 | `    """WHY: a process whose references change level gives no process value at 8 MiB (plan, rules 4 and 5)."""` | Docstring, the reason: a process whose reference intervals change level gives no process value at 8 MiB (rules 4 and 5 of the plan). |
| 174 | `    blocks = []` | `blocks`: empty at first. |
| 175 | `    for c in (0, 2):` | Loop over the CPUs 0 and 2. |
| 176 | `        blocks += [b1(c, i, copy_rate()) for i in range(1, 4)]` | 3 processes with the default rates: `d` is -2.0 GB/s at the low level. |
| 177 | `        blocks += [b1(c, 4, copy_rate(copy=67.0, ref_by_round=[67.5, 67.5, 71.2, 71.2]))]      # d = +9, but the level changes` | 1 process with `copy` at 67.0 GB/s, so `d` is +9 GB/s. Its reference rate is 67.5 GB/s in the first two rounds and 71.2 GB/s in the last two. So the level changes from low to high. |
| 178 | `    g = analyze({'s1': {'B1.csv': blocks}})['sessions']['s1']['B1']['groups']['8M']` | Runs the analysis and takes the 8 MiB group. |
| 179 | `    assert g['labels']['low']['decision'] == 'resolved' and g['labels']['low']['sign'] == -1 and g['labels']['low']['per_cpu'][0]['n_processes'] == 3` | Proves that the label `low` is resolved with a negative sign from 3 processes on CPU 0. The fourth process, with its +9 GB/s, is not used for the decision. |
| 180 | `    odd = [p for p in g['processes'] if not p['used']]` | `odd`: the records of the processes that are not used. |
| 181 | `    assert len(odd) == 2 and 'not all at one level' in odd[0]['reason'] and {x['label'] for x in odd[0]['pairs']} == {'low', 'high'}` | Proves that 2 processes are not used, one per CPU. The reason says that the reference intervals are not all at one level, and the pairs are listed with the labels `low` and `high`. |

### Helpers `b6_rate` and `b6`, and the test of step B6 (lines 184 to 211)

| Line | Source | Explanation |
|---:|---|---|
| 184 | `def b6_rate(ref, old8, old1=None, old2=None):` | Starts the function `b6_rate`. It returns a rate function for the sequence of step B6. `ref` is the rate of the reference kernel, and `old8` is the rate of old read at 8 MiB. |
| 185 | `    def f(r, pos, entry, tid, cpu):` | Starts the inner function `f`, the rate function. |
| 186 | `        return {'asmread': ref, 'oldread': old8, 'oldread@1M': old1 if old1 else old8 + 0.01, 'oldread2': old2 if old2 else old8 + 0.02}[entry]` | Returns the rate of the entry. `oldread@1M` gets `old1`, or `old8` plus 0.01 GB/s without it. `oldread2` gets `old2`, or `old8` plus 0.02 GB/s without it. |
| 187 | `    return f` | Returns the rate function. |
| 190 | `def b6(cpu, i, rate):` | Starts the function `b6`. It builds one process of step B6. |
| 191 | `    return block('B6', 'cpu%d-p%d' % (cpu, i), '--threads 1 --cpus %d --seq %s --bytes 8M --rounds 4 --min-ms 300 --stop pass' % (cpu, B6SEQ), rate)` | Calls `block` with a tag of the form `cpu2-p1` and the options of step B6: 1 thread, 8 MiB, 4 rounds, 300 ms and the whole-pass stop. |
| 194 | `def test_b6_cpu_difference_is_not_a_level_difference():` | Starts the test `test_b6_cpu_difference_is_not_a_level_difference`. |
| 195 | `    """WHY: CPU 2 always low at 67.0 and CPU 41 always high at 68.0 says nothing about the level (handoff B.10)."""` | Docstring, the reason: a CPU 2 that is always low at 67.0 GB/s and a CPU 41 that is always high at 68.0 GB/s say nothing about the level (section B.10 of the handoff note). |
| 196 | `    blocks = [b6(2, i, b6_rate(67.5, 67.0)) for i in range(1, 5)] + [b6(41, i, b6_rate(71.2, 68.0)) for i in range(1, 5)]` | 4 processes on CPU 2 with a low reference rate (67.5 GB/s) and old read at 67.0 GB/s, and 4 on CPU 41 with a high reference rate (71.2 GB/s) and old read at 68.0 GB/s. |
| 197 | `    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']` | Runs the analysis and takes step B6. |
| 198 | `    assert r['state'][2]['decision'] == 'not observed' and r['state'][41]['decision'] == 'not observed'` | Proves that both CPUs are `not observed` in the comparison of low against high: no CPU has processes of both levels. A comparison across the two CPUs would have shown their 1.0 GB/s as an effect of the level. |
| 199 | `    assert 'Insufficient data' in r['state'][2]['note']` | Proves that the note of CPU 2 holds `Insufficient data`. |
| 200 | `    # the second comparison (8 MiB against 1 MiB) uses all processes, label "none": 0.01 GB/s against an A/A of 0.02 is not resolved` | Comment: the second comparison, 8 MiB against 1 MiB, uses all processes with the label `none`. A difference of 0.01 GB/s against an A/A value of 0.02 GB/s is not resolved. |
| 201 | `    assert r['size']['labels']['none']['decision'] == 'not resolved'` | Proves that: the size comparison is `not resolved`. |
| 202 | `    # both levels on ONE CPU with separate old read rates: resolved on that CPU` | Comment: both levels on one CPU, with separate old read rates, give a resolved result on that CPU. |
| 203 | `    blocks = [b6(2, i, b6_rate(67.5, 67.0)) for i in (1, 2)] + [b6(2, i, b6_rate(71.2, 69.0)) for i in (3, 4)]` | 2 low processes with old read at 67.0 GB/s and 2 high processes with old read at 69.0 GB/s, all on CPU 2. |
| 204 | `    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']` | Runs the analysis. |
| 205 | `    assert r['state'][2]['decision'] == 'resolved' and near(r['state'][2]['difference'], -2.0, 0.01)` | Proves that CPU 2 is resolved, with a difference of -2.0 GB/s: low minus high. |
| 206 | `    # a resolved difference between 8 MiB and 1 MiB needs 2 CPUs, as in B1` | Comment: a resolved difference between 8 MiB and 1 MiB needs 2 CPUs, as in B1. |
| 207 | `    blocks = [b6(c, i, b6_rate(67.5, 67.0, old1=60.0)) for c in (2, 41) for i in range(1, 4)]` | 3 processes on each of the CPUs 2 and 41, with old read at 67.0 GB/s at 8 MiB and at 60.0 GB/s at 1 MiB. |
| 208 | `    r = analyze({'s1': {'B6.csv': blocks}})['sessions']['s1']['B6']` | Runs the analysis. |
| 209 | `    assert r['size']['labels']['none']['decision'] == 'resolved' and r['size']['labels']['none']['sign'] == 1` | Proves that the size comparison is resolved with a positive sign. |

### Test of step B3: the change of the difference against B1 (lines 212 to 228)

| Line | Source | Explanation |
|---:|---|---|
| 212 | `def test_b3_change_against_b1():` | Starts the test `test_b3_change_against_b1`. |
| 213 | `    """WHY: H6 is about the CHANGE of the difference when the offset changes, per CPU, against both A/A spreads."""` | Docstring, the reason: hypothesis H6 is about the change of the difference when the offset changes, per CPU, against both A/A spreads. |
| 214 | `    base = [b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)]                                         # d = -2` | `base`: step B1 with 4 processes on each of the CPUs 0 and 2. By the comment `d` is -2 GB/s. |
| 215 | `    gone = [b1(c, i, copy_rate(copy=57.9), step='B3', binary='bwx_o52') for c in (0, 2) for i in range(1, 5)]   # d = -0.1` | `gone`: step B3 with the binary `bwx_o52` and `copy` at 57.9 GB/s. By the comment `d` is -0.1 GB/s: the difference is nearly 0. |
| 216 | `    same = [b1(c, i, copy_rate(copy=55.95), step='B3', binary='bwx_o36') for c in (0, 2) for i in range(1, 5)]  # d = -2.05` | `same`: step B3 with the binary `bwx_o36` and `copy` at 55.95 GB/s. By the comment `d` is -2.05 GB/s: nearly the same as in B1. |
| 217 | `    few = [b1(0, i, copy_rate(copy=57.9), step='B3', binary='bwx_o0') for i in range(1, 3)]` | `few`: step B3 with the binary `bwx_o0`: only 2 processes, on CPU 0. |
| 218 | `    out = analyze({'s1': {'B1.csv': base, 'B3.csv': gone + same + few}})` | Runs the analysis on one session with both steps. |
| 219 | `    ch = out['sessions']['s1']['B3']['change_against_B1']` | `ch`: the changes against B1 per build. |
| 220 | `    assert ch['bwx_o52']['low/cpu0']['decision'] == 'resolved' and near(ch['bwx_o52']['low/cpu0']['change'], -1.9, 0.01)` | Proves that the change of `bwx_o52` on CPU 0 is resolved and is -1.9 GB/s: the median `d` of B1 (-2.0) minus that of the build (-0.1). |
| 221 | `    assert ch['bwx_o36']['low/cpu2']['decision'] == 'not resolved'      # 0.05 GB/s is inside 0.1 + 0.1` | Proves that the change of `bwx_o36` on CPU 2 is `not resolved`. By the comment 0.05 GB/s lies inside the sum of the two A/A spreads, 0.1 plus 0.1 GB/s. |
| 222 | `    assert ch['bwx_o0']['low/cpu0']['decision'] == 'not observed'       # 2 processes are not enough` | Proves that `bwx_o0` on CPU 0 is `not observed`. By the comment 2 processes are not enough. |
| 223 | `    assert out['hypotheses']['H6 (B3)']['per_session'] == {'s1': 'not observed'}    # bwx_o0 has no CPU with 3 processes` | Proves that the flag of the session for H6 is `not observed`. By the comment the build `bwx_o0` has no CPU with 3 processes. So a build with too few processes cannot count as a failure of H6. |
| 224 | `    # without B1 of the same session there is nothing to compare with` | Comment: without B1 of the same session there is nothing to compare with. |
| 225 | `    ch = analyze({'s1': {'B3.csv': gone}})['sessions']['s1']['B3']['change_against_B1']` | Runs the analysis on a session with step B3 alone. |
| 226 | `    assert ch['bwx_o52']['low/cpu0']['decision'] == 'not observed' and 'B1' in ch['bwx_o52']['low/cpu0']['note']` | Proves that the change is then `not observed`, with a note that names B1. |

### Helper `b4` and the test of the two cases of step B4 (lines 229 to 251)

| Line | Source | Explanation |
|---:|---|---|
| 229 | `def b4(cpu, tag, n_low, n_high, cov, nothp=False):` | Starts the function `b4`. It builds one process of step B4. `n_low` and `n_high` are numbers of rounds. `cov` names the coverage. `nothp` adds the option `--no-thp`. |
| 230 | `    kb = 8192` | `kb`: 8192, the size of the buffer in kB (8 MiB). |
| 231 | `    pg = {'full': (kb, kb), 'none': (kb, 0), 'NA': ('NA', 'NA'), 'partial': (kb, 2048)}[cov]` | `pg`: the pair of `kB_total` and `kB_huge` for the coverage word: full (8192 of 8192 kB), none (0 of 8192 kB), `NA` in both fields, or partial (2048 of 8192 kB). |
| 232 | `    return block('B4', '%s-cpu%d' % (tag, cpu), '--threads 1 --cpus %d --bytes 8M --seq asmread --rounds %d --min-ms 300 --stop pass%s' % (cpu, n_low + n_high, ' --no-thp' if nothp else ''),` | Calls `block` with the options of step B4: 1 thread, 8 MiB, the sequence `asmread` alone, 300 ms and the whole-pass stop. The number of rounds is `n_low + n_high`. The call goes on in line 233. |
| 233 | `                 lambda r, pos, e, tid, c: 67.5 if r < n_low else 71.2, page=lambda r, pos: pg)` | Continues line 232: the rate is 67.5 GB/s (low) in the first `n_low` rounds and 71.2 GB/s (high) after them. Every `P` row has the coverage `pg`. |
| 236 | `def test_b4_cases():` | Starts the test `test_b4_cases`. |
| 237 | `    """WHY: H3a is contradicted only by 10 low AND 10 high intervals with the SAME known coverage on one CPU."""` | Docstring, the reason: H3a is contradicted only by 10 low and 10 high intervals with the same known coverage on one CPU. |
| 238 | `    s = analyze({'s1': {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full'), b4(2, 'nothp-p1', 30, 0, 'none', True),` | Runs the analysis on six processes. CPU 2: 15 low and 15 high intervals with full coverage, and 30 low intervals with coverage none. The list goes on in lines 239 to 240. |
| 239 | `                                   b4(41, 'thp-p1', 25, 5, 'full'), b4(41, 'nothp-p1', 12, 18, 'none', True),` | Continues line 238. CPU 41: 25 low and 5 high intervals with full coverage, and 12 low and 18 high intervals with coverage none. |
| 240 | `                                   b4(94, 'thp-p1', 15, 15, 'NA'), b4(94, 'thp-p2', 15, 15, 'partial')]}})['sessions']['s1']['B4']['per_cpu']` | Continues line 238. CPU 94: 15 low and 15 high intervals with `NA`, and 15 low and 15 high intervals with partial coverage. The result per CPU is taken. |
| 241 | `    assert s[2]['cases'] == ['a'] and s[2]['intervals']['low']['none'] == 30` | Proves case `a` alone on CPU 2, and 30 low intervals with coverage none in its table. Case `b` does not hold there: it also needs high intervals with coverage none. |
| 242 | `    assert s[41]['cases'] == ['b'] and s[41]['intervals']['high']['full'] == 5       # 5 high intervals are fewer than 10` | Proves case `b` alone on CPU 41. By the comment 5 high intervals with full coverage are fewer than 10, so case `a` does not hold. |
| 243 | `    assert s[94]['decision'] == 'not observed' and s[94]['intervals']['low']['unknown'] == 15   # NA coverage proves nothing` | Proves that CPU 94 is `not observed`, with 15 low intervals under `unknown`. By the comment a coverage of `NA` proves nothing. The intervals with partial coverage count for no case either. |
| 244 | `    assert s[2]['level_changes_low_high'] == 1 and s[2]['level_changes_with_no_sign_of_a_page_change'] == 1` | Proves the count of level changes on CPU 2: one change from low to high, and it shows no sign of a page change. The coverage and the system counters are the same before both intervals. |
| 245 | `    # "rejected" needs the same CPU in two sessions` | Comment: the word `rejected` needs the same CPU in two sessions. |
| 246 | `    one = {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full')]}` | `one`: a session with a case on CPU 2. |
| 247 | `    other = {'B4.csv': [b4(41, 'thp-p1', 15, 15, 'full')]}` | `other`: a session with a case on CPU 41. This test never uses it. |
| 248 | `    assert analyze({'s1': one, 's2': one})['hypotheses']['H3a (B4)']['word'] == 'rejected'` | Proves that two sessions with a case on the same CPU give the word `rejected` for H3a. |
| 249 | `    assert 'one session only' in analyze({'s1': one})['hypotheses']['H3a (B4)']['word']` | Proves that one session alone never rejects: its word holds `one session only`. |

### Test: the flag of a session for H3a comes from that session alone (lines 252 to 271)

| Line | Source | Explanation |
|---:|---|---|
| 252 | `def test_b4_session_flag_does_not_depend_on_the_other_session():` | Starts the test `test_b4_session_flag_does_not_depend_on_the_other_session`. |
| 253 | `    """WHY: a per-session result must be the result of that session (plan, rule 10), and "not observed" means that the` | Docstring, the reason: a result per session must be the result of that session (rule 10 of the plan), and `not observed` means that the event did not occur (rule 11). The docstring goes on in lines 254 to 255. |
| 254 | `    event did not occur (rule 11). A case on CPU 2 in one session and on CPU 41 in the other is a failed prediction in` | Docstring: a case on CPU 2 in one session and on CPU 41 in the other is a failed prediction in each session. |
| 255 | `    each session. Before A32 both sessions got the flag "not observed" and the word was "not observed"."""` | Docstring: before point A32 of the deviations note both sessions got the flag `not observed`, and the word was `not observed`. |
| 256 | `    one = {'B4.csv': [b4(2, 'thp-p1', 15, 15, 'full')]}` | `one`: a session with a case on CPU 2. |
| 257 | `    other = {'B4.csv': [b4(41, 'thp-p1', 15, 15, 'full')]}` | `other`: a session with a case on CPU 41. |
| 258 | `    none = {'B4.csv': [b4(2, 'thp-p1', 30, 0, 'full')]}` | `none`: a session with 30 low intervals and no high interval on CPU 2. It has no case. |
| 259 | `    h = analyze({'s1': one, 's2': other})['hypotheses']['H3a (B4)']` | Runs the analysis on `one` and `other` and takes the entry for H3a. |
| 260 | `    assert h['per_session'] == {'s1': 'fail', 's2': 'fail'}` | Proves that both sessions have the flag `fail`. |
| 261 | `    assert h['word'] == 'not rejected'                                  # no CPU has a case in both sessions (A13)` | Proves that the word is `not rejected`. By the comment no CPU has a case in both sessions (point A13). |
| 262 | `    assert h['word_without_the_same_cpu_condition'] == 'rejected'       # the other reading is kept next to it, not chosen` | Proves that the word without the condition of the same CPU is `rejected`. By the comment this other reading is kept beside the word and is not chosen. |
| 263 | `    assert h['cpus_with_a_case'] == {'s1': [2], 's2': [41]} and h['cpus_with_a_case_in_every_session'] == []` | Proves the lists: CPU 2 in the first session, CPU 41 in the second, and no CPU in both. |
| 264 | `    h = analyze({'s1': one, 's2': one})['hypotheses']['H3a (B4)']` | Runs the analysis on two sessions with the case on CPU 2. |
| 265 | `    assert h['word'] == 'rejected' and h['cpus_with_a_case_in_every_session'] == [2]` | Proves that the word is then `rejected`, with CPU 2 as the CPU with a case in every session. |
| 266 | `    h = analyze({'s1': one, 's2': none})['hypotheses']['H3a (B4)']` | Runs the analysis on `one` and `none`. |
| 267 | `    assert h['per_session'] == {'s1': 'fail', 's2': 'not observed'} and h['word'] == 'not rejected'` | Proves the flags `fail` and `not observed`, and the word `not rejected`. |
| 268 | `    h = analyze({'s1': none, 's2': none})['hypotheses']['H3a (B4)']` | Runs the analysis on two sessions without a case. |
| 269 | `    assert h['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and h['word'] == 'not observed'` | Proves that both flags are `not observed` and that the word is `not observed`. So a session keeps its own flag, whatever the other session shows. |

### Helpers `split`, `read_rate` and `b7`, and the test of `D` and of the meshes (lines 272 to 306)

| Line | Source | Explanation |
|---:|---|---|
| 272 | `# ------------------------------------------------------------ 120 threads` | Comment: a divider. The tests of the steps with 120 threads start here. |
| 274 | `def split(total_fast=5.0, slow=2.7):` | Starts the function `split`. It returns a rate function of the CPU for a split pattern. |
| 275 | `    return lambda cpu: total_fast if cpu < 64 else slow` | A thread on the CPUs 0 to 63 gets 5.0 GB/s and every other thread gets 2.7 GB/s, unless the caller gives other rates. So mesh 0 is the fast mesh. |
| 278 | `def read_rate(old=split(), read=2.5, asm=2.5, asm2=2.52):` | Starts the function `read_rate`. It returns a rate function for the read sequences. By default old read is split, and `read`, `asmread` and `asmread2` are uniform at 2.5, 2.5 and 2.52 GB/s per thread. |
| 279 | `    """Old read split (mesh 0 fast), the other kernels uniform. Totals: old 471.2, read 300, asmread2 - asmread +2.4 GB/s."""` | Docstring: old read is split with mesh 0 fast, and the other kernels are uniform. With the defaults the totals are 471.2 GB/s for old read (64 times 5.0 plus 56 times 2.7) and 300 GB/s for `read`. `asmread2` minus `asmread` is +2.4 GB/s (120 times 0.02). |
| 280 | `    def f(r, pos, entry, tid, cpu):` | Starts the inner function `f`, the rate function. |
| 281 | `        return old(cpu) if entry == 'oldread' else {'read': read, 'asmread': asm, 'asmread2': asm2}.get(entry, read)` | Old read gets the rate of its CPU from `old`. `read`, `asmread` and `asmread2` get their fixed rates. Any other entry gets the rate of `read`. |
| 282 | `    return f` | Returns the rate function. |
| 285 | `def b7(setting, i, rate, seq=B7SEQ, rounds=2, step='B7', **kw):` | Starts the function `b7`. It builds one process with 120 threads. `setting` has the form `pass/500/common`. The defaults are the sequence `B7SEQ`, 2 rounds and the step name `B7`. |
| 286 | `    stop, ms, start = setting.split('/')` | Splits the setting into the stop method, the interval length in ms and the start method. |
| 287 | `    return block(step, '%s-p%d' % (setting.replace('/', '-'), i), '%s --seq %s --rounds %d --stop %s --min-ms %s --start %s' % (ALL, seq, rounds, stop, ms, start), rate, **kw)` | Calls `block` with a tag of the form `pass-500-common-p1`, and with the options `ALL` (line 19), the sequence, the rounds and the three parts of the setting. |
| 290 | `def test_b7_setting_and_meshes():` | Starts the test `test_b7_setting_and_meshes`. |
| 291 | `    """WHY: D is one value per process, decided against the A/A spread; mesh 0 is CPUs 0-63 and mesh 1 is CPUs 64-119."""` | Docstring, the reason: `D` is one value per process, decided against the A/A spread. Mesh 0 is the CPUs 0 to 63, and mesh 1 is the CPUs 64 to 119. |
| 292 | `    S = 'pass/500/common'` | `S`: the setting `pass/500/common`, the reproduction condition of step B7. |
| 293 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(asm2=2.5 + 0.005 * i)) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis on 4 processes of this setting. `asmread2` lies 0.005 GB/s per thread times the process number above `asmread`. So `E` is 0.6, 1.2, 1.8 and 2.4 GB/s. |
| 294 | `    d = r['settings'][S]` | `d`: the decision of the setting. |
| 295 | `    assert d['decision'] == 'resolved' and d['sign'] == 1 and r['reproduction_in_one_process'] == 'reproduced'` | Proves that `D` is resolved with a positive sign, and that the reproduction in one process is `reproduced`. |
| 296 | `    m = d['metrics']` | `m`: the decisions per metric. |
| 297 | `    assert m['M_hist']['n_processes'] == 4 and near(m['M_hist']['median_D'], 171.2) and near(m['M_hist']['aa_spread'], 2.4)` | Proves the numbers with `M_hist`: 4 processes, a median `D` of 171.2 GB/s (471.2 minus 300) and an A/A spread of 2.4 GB/s, the largest `E`. |
| 298 | `    assert near(m['M_hist_mesh0']['median_D'], 64 * 2.5) and near(m['M_hist_mesh1']['median_D'], 56 * 0.2)      # CPU 63 is mesh 0, CPU 64 is mesh 1` | Proves the values per mesh: `D` of mesh 0 is 64 times 2.5 = 160 GB/s, and `D` of mesh 1 is 56 times 0.2 = 11.2 GB/s. By the comment CPU 63 belongs to mesh 0 and CPU 64 to mesh 1. A border that is off by one CPU would change both numbers. |
| 299 | `    # 3 processes hold 12 intervals of each kernel, but they are 3 values: not observed` | Comment: 3 processes hold 12 intervals of each kernel, but they are 3 values. So the result is `not observed`. |
| 300 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate()) for i in range(1, 4)]}})['sessions']['s1']['B7']` | Runs the analysis on 3 processes. |
| 301 | `    assert r['settings'][S]['decision'] == 'not observed' and '3 processes' in r['settings'][S]['note']` | Proves that the decision is `not observed` and that the note names the 3 processes. So intervals are not counted as processes. |
| 302 | `    # a difference inside the A/A spread is not resolved` | Comment: a difference inside the A/A spread is not resolved. |
| 303 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(old=lambda c: 2.51)) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis on 4 processes in which old read is uniform at 2.51 GB/s per thread. Then `D` is 1.2 GB/s against an A/A spread of 2.4 GB/s. |
| 304 | `    assert r['settings'][S]['decision'] == 'not resolved' and r['reproduction_in_one_process'].startswith('not reproduced')` | Proves that `D` is `not resolved` and that the reproduction text starts with `not reproduced`. |

### Tests of step B7: irregular intervals, and `M_hist` against `M_sum` (lines 307 to 340)

| Line | Source | Explanation |
|---:|---|---|
| 307 | `def test_b7_irregular_intervals():` | Starts the test `test_b7_irregular_intervals`. |
| 308 | `    """WHY: with the common stop, an interval with a late thread or an end skew above 5 ms is listed and not used."""` | Docstring, the reason: with the common stop an interval with a late thread or with an end skew above 5 ms is listed and not used. |
| 309 | `    S = 'common/6000/common'` | `S`: the setting `common/6000/common`. |
| 310 | `    late = lambda r, pos, tid: 'late' if (r, pos, tid) == (1, 0, 17) else '-'` | `late`: a flag function. It gives `late` for thread 17 in round 1 at position 0, and `-` for every other thread and interval. |
| 311 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), flag=late if i == 2 else None) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis on 4 processes. Only process 2 gets the flag function. |
| 312 | `    assert r['settings'][S]['decision'] == 'not observed'             # the process with the late thread gives no D: 3 values` | Proves that the setting is `not observed`. By the comment the process with the late thread gives no `D`, so 3 values are left. |
| 313 | `    assert [(x['tag'], x['round'], x['pos'], x['late_threads']) for x in r['irregular_intervals']] == [('common-6000-common-p2', 1, 0, 1)]` | Proves that the report lists exactly one irregular interval: process 2, round 1, position 0, with 1 late thread. |
| 314 | `    assert 'irregular' in r['settings'][S]['processes_without_value'][0]['reason']` | Proves that the reason of the process without a value holds the word `irregular`. |
| 315 | `    # the same data without the flag is resolved: the flag alone made the difference` | Comment: the same data without the flag is resolved. So the flag alone made the difference. |
| 316 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate()) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis on the same 4 processes without the flag. |
| 317 | `    assert r['settings'][S]['decision'] == 'resolved' and r['irregular_intervals'] == []` | Proves that the setting is then resolved and that no interval is irregular. |
| 318 | `    # end skew: one thread ends 8 ms after the others` | Comment: the next case is the end skew. One thread ends 8 ms after the others. |
| 319 | `    slow = lambda r, pos, e, tid: 6.008 if (r, pos, tid) == (0, 1, 5) else None` | `slow`: an elapsed-time function. Thread 5 gets 6.008 s in round 0 at position 1. Every other thread keeps the 6.000 s of `--min-ms`. |
| 320 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), elapsed=slow if i == 1 else None) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis with this function in process 1 only. |
| 321 | `    assert r['settings'][S]['decision'] == 'not observed' and r['irregular_intervals'][0]['end_skew_ms'] == 8.0` | Proves that the setting is `not observed` and that the first irregular interval has an end skew of 8.0 ms. That is above the limit of 5 ms. |
| 322 | `    # with --stop pass the threads end at pass borders: an end skew of 80 ms is the method, not a defect` | Comment: with `--stop pass` the threads end at the borders of their passes. An end skew of 80 ms is the method, not a defect. |
| 323 | `    S = 'pass/500/common'` | `S`: the setting `pass/500/common`. |
| 324 | `    slow = lambda r, pos, e, tid: 0.58 if tid % 2 else None` | `slow`: every thread with an odd number gets an elapsed time of 0.58 s. The others keep 0.5 s. So the ends differ by 80 ms. |
| 325 | `    r = analyze({'s1': {'B7.csv': [b7(S, i, read_rate(), elapsed=slow) for i in range(1, 5)]}})['sessions']['s1']['B7']` | Runs the analysis with this function in all 4 processes. |
| 326 | `    assert r['irregular_intervals'] == [] and r['settings'][S]['decision'] == 'resolved'` | Proves that no interval is irregular and that `D` is resolved. With the other reading every interval of the whole-pass stop could be dropped, and the reproduction condition would give no value. |
| 329 | `def test_b7_m_hist_against_m_sum():` | Starts the test `test_b7_m_hist_against_m_sum`. |
| 330 | `    """WHY: if the two metrics lead to different results for D, the result is "not resolved" and both are reported."""` | Docstring, the reason: when the two metrics lead to different results for `D`, the result is `not resolved`, and both are reported. |
| 331 | `    S = 'pass/500/common'` | `S`: the setting `pass/500/common`. |
| 332 | `    # read: 3.5 GB/s per thread, but thread 0 needs 1.0 s for its last pass. M_sum = 420, M_hist = 211.75. Old read: 360 by both.` | Comment: the invented case. `read` runs at 3.5 GB/s per thread, but thread 0 needs 1.0 s for its last pass. Then `M_sum` of `read` is 420 GB/s and `M_hist` is 211.75 GB/s. Old read is 360 GB/s by both metrics. |
| 333 | `    slow = lambda r, pos, e, tid: 1.0 if e == 'read' and tid == 0 else None` | `slow`: thread 0 gets an elapsed time of 1.0 s in the `read` intervals. |
| 334 | `    rate = read_rate(old=lambda c: 3.0, read=3.5)` | `rate`: old read uniform at 3.0 GB/s per thread, and `read` at 3.5 GB/s per thread. |
| 335 | `    d = analyze({'s1': {'B7.csv': [b7(S, i, rate, elapsed=slow) for i in range(1, 5)]}})['sessions']['s1']['B7']['settings'][S]` | Runs the analysis on 4 such processes and takes the decision of the setting. |
| 336 | `    assert (d['metrics']['M_hist']['decision'], d['metrics']['M_hist']['sign']) == ('resolved', 1) and near(d['metrics']['M_hist']['median_D'], 148.25)` | Proves that `M_hist` resolves `D` with a positive sign, at 148.25 GB/s (360 minus 211.75). |
| 337 | `    assert (d['metrics']['M_sum']['decision'], d['metrics']['M_sum']['sign']) == ('resolved', -1) and near(d['metrics']['M_sum']['median_D'], -60.0)` | Proves that `M_sum` resolves `D` with a negative sign, at -60.0 GB/s (360 minus 420). |
| 338 | `    assert d['decision'] == 'not resolved' and 'M_sum' in d['note']` | Proves that the decision is `not resolved` and that its note names `M_sum`. So one thread with a long last pass cannot set the sign of `D` alone. |

### Test of step B7: changes between settings, and one kernel per process (lines 341 to 363)

| Line | Source | Explanation |
|---:|---|---|
| 341 | `def test_b7_changes_and_single_kernel():` | Starts the test `test_b7_changes_and_single_kernel`. |
| 342 | `    """WHY: a factor "contributes" only if D changes by more than both A/A spreads and the two sets of D do not overlap."""` | Docstring, the reason: a factor "contributes" only if `D` changes by more than both A/A spreads and the two sets of `D` do not overlap. |
| 343 | `    big, small = read_rate(), read_rate(old=lambda c: 2.7)                 # D = 171.2 and D = 24` | `big`: the default rates. `small`: old read uniform at 2.7 GB/s per thread. By the comment `D` is 171.2 GB/s with `big` and 24 GB/s with `small` (120 times 0.2). |
| 344 | `    blocks = [b7('pass/500/common', i, big) for i in range(1, 5)] + [b7('common/500/common', i, small) for i in range(1, 5)] + \` | 4 processes each of two settings: `pass/500/common` with `big` and `common/500/common` with `small`. The list goes on in line 345. |
| 345 | `             [b7('pass/500/offset', i, big) for i in range(1, 5)] + [b7('common/6000/offset', i, small) for i in range(1, 5)]` | Continues line 344: 4 processes each of `pass/500/offset` with `big` and of `common/6000/offset` with `small`. |
| 346 | `    for k in ('oldread', 'read', 'asmread', 'asmread2'):` | Loop over the four kernels of the runs with one kernel per process. |
| 347 | `        blocks += [b7('pass/500/common', i, read_rate(), seq=k, rounds=3).replace('tag pass-500-common', 'tag single-%s' % k) for i in range(1, 5 if k != 'read' else 4)]` | Adds processes with one kernel and 3 rounds. Their tag is changed to the form `single-oldread-p1`. Each kernel gets 4 processes, but `read` gets only 3. |
| 348 | `    out = analyze({'s1': {'B7.csv': blocks}})` | Runs the analysis. |
| 349 | `    r = out['sessions']['s1']['B7']` | `r`: the result of step B7. |
| 350 | `    ch = r['changes']` | `ch`: the changes of `D` between settings. |
| 351 | `    assert sorted(ch) == ['start: pass/500/common -> pass/500/offset', 'stop: pass/500/common -> common/500/common']    # only pairs that differ in ONE factor` | Proves that exactly two changes are computed: one for the start and one for the stop method, both from `pass/500/common`. By the comment only pairs that differ in one factor count. The setting `common/6000/offset` differs from each of the others in two or three factors. |
| 352 | `    c = ch['stop: pass/500/common -> common/500/common']` | `c`: the change for the stop method. |
| 353 | `    assert c['decision'] == 'resolved' and near(c['metrics']['M_hist']['change'], 147.2) and near(c['metrics']['M_hist']['sum_of_aa_spreads'], 4.8)` | Proves that it is resolved, with a change of 147.2 GB/s (171.2 minus 24) and a sum of the A/A spreads of 4.8 GB/s (2.4 plus 2.4). |
| 354 | `    assert ch['start: pass/500/common -> pass/500/offset']['decision'] == 'not resolved'` | Proves that the change for the start is `not resolved`: `D` is the same with both start methods. |
| 355 | `    assert out['hypotheses']['H7a (B7, read)']['per_session'] == {'s1': 'hold'} and out['hypotheses']['H7b (B7, read)']['per_session'] == {'s1': 'fail'}` | Proves the flags of the session: `hold` for H7a, for the change with the stop method is resolved, and `fail` for H7b, for no change with the start is resolved. |
| 356 | `    assert 'one session only' in out['hypotheses']['H7b (B7, read)']['word']          # one session never rejects` | Proves that the word for H7b holds `one session only`. By the comment one session never rejects. |
| 357 | `    # one kernel per process: 3 processes of read are not 4` | Comment: with one kernel per process, 3 processes of `read` are not 4. |
| 358 | `    assert r['single_kernel']['decision'] == 'not observed' and r['single_kernel']['n_processes']['read'] == 3` | Proves that the decision with one kernel per process is `not observed` and that it counts 3 processes of `read`. |
| 359 | `    blocks.append(b7('pass/500/common', 4, read_rate(), seq='read', rounds=3).replace('tag pass-500-common', 'tag single-read'))` | Adds the fourth process of `read`. |
| 360 | `    sk = analyze({'s1': {'B7.csv': blocks}})['sessions']['s1']['B7']['single_kernel']` | Runs the analysis again and takes that decision. |
| 361 | `    assert sk['decision'] == 'resolved' and sk['sign'] == 1 and near(sk['D'], 171.2) and near(sk['aa_value'], 2.4)` | Proves that it is now resolved with a positive sign, with a `D` of 171.2 GB/s and an A/A value of 2.4 GB/s. |

### Helper `b8` and the test of the brackets of step B8 (lines 364 to 393)

| Line | Source | Explanation |
|---:|---|---|
| 364 | `def b8(b, i, old_split, asm_split):` | Starts the function `b8`. It builds one process of step B8 with 64 threads on mesh 0 and `b` threads on mesh 1. `old_split` and `asm_split` say whether old read and the two copies of `asmread` are split. |
| 365 | `    def rate(r, pos, entry, tid, cpu):` | Starts the inner rate function. |
| 366 | `        s = old_split if entry == 'oldread' else asm_split` | `s`: the choice for this entry: `old_split` for `oldread`, and `asm_split` for every other entry. |
| 367 | `        return (5.0 if cpu < 64 else 2.6) if s else 3.0` | A split kernel gets 5.0 GB/s on the CPUs 0 to 63 and 2.6 GB/s on the others. Then `q` is 0.52, which is below 0.65. A uniform kernel gets 3.0 GB/s on every thread, so `q` is 1. |
| 368 | `    return block('B8', '64+%d-p%d' % (b, i), '--threads %d --cpus 0-63,64-%d --bytes 256M --seq %s --rounds 1 --stop common --min-ms 6000 --start common' % (64 + b, 63 + b, B8SEQ), rate)` | Calls `block` with a tag of the form `64+36-p1`, the CPUs 0 to 63 and 64 to `63 + b`, 256 MiB, the sequence `B8SEQ`, 1 round, the common stop and 6000 ms. |
| 371 | `def test_b8_brackets():` | Starts the test `test_b8_brackets`. |
| 372 | `    """WHY: a bracket needs ordered counts. It is never built from the highest split count alone (handoff B.10)."""` | Docstring, the reason: a bracket needs ordered counts. It is never built from the highest split count alone (section B.10 of the handoff note). |
| 373 | `    assert ab.bracket({36: 'split', 40: 'mixed', 44: 'uniform'}) == (36, 44)` | Proves the plain case of the function `bracket`: split at 36, mixed at 40 and uniform at 44 give the bracket 36 to 44. |
| 374 | `    assert ab.bracket({36: 'split', 40: 'untested', 44: 'uniform', 48: 'uniform'}) == (36, 44)` | Proves that an untested count between the two ends is skipped, and that the bracket ends at the lowest uniform count: 36 to 44. |
| 375 | `    assert ab.bracket({36: 'split', 40: 'uniform', 44: 'split', 48: 'uniform'}) is None       # a split count above a uniform count` | Proves that a split count above a uniform count gives no bracket, as the comment says. |
| 376 | `    assert ab.bracket({36: 'uniform', 40: 'uniform'}) is None and ab.bracket({36: 'split', 40: 'split'}) is None and ab.bracket({36: 'mixed'}) is None` | Proves three more cases without a bracket: only uniform counts, only split counts, and one mixed count alone. |
| 377 | `    plan = {36: (True, True), 40: (True, False), 44: (False, False)}       # old read changes between 40 and 44, asm read between 36 and 40` | `plan`: per count of mesh-1 threads, whether old read and `asmread` are split. By the comment old read changes between 40 and 44, and `asmread` between 36 and 40. |
| 378 | `    r = analyze({'s1': {'B8.csv': [b8(b, i, *plan[b]) for i in (1, 2) for b in plan]}})['sessions']['s1']['B8']` | Runs the analysis on 2 processes per count. |
| 379 | `    assert r['kernels']['oldread']['bracket'] == (40, 44) and r['kernels']['asmread']['bracket'] == (36, 40) and r['H8'] == 'supported'` | Proves the brackets from whole files: 40 to 44 for old read and 36 to 40 for `asmread`. The `asmread` bracket ends where the old read bracket starts, so H8 is `supported`. |
| 380 | `    assert r['kernels']['oldread']['counts'][36]['label'] == 'split' and near(r['kernels']['oldread']['counts'][36]['q'][0], 0.52, 0.001)` | Proves that the count 36 of old read has the label `split`, and that its first `q` is 0.52. |
| 381 | `    plan = {36: (True, True), 40: (False, True), 44: (False, False)}` | `plan`: the opposite order. Old read changes between 36 and 40, and `asmread` between 40 and 44. |
| 382 | `    two = {'B8.csv': [b8(b, i, *plan[b]) for i in (1, 2) for b in plan]}` | `two`: the file of one session with this plan. |
| 383 | `    out = analyze({'s1': two, 's2': two})` | Runs the analysis on two equal sessions. |
| 384 | `    assert out['sessions']['s1']['B8']['H8'] == 'contradicted' and out['hypotheses']['H8 (B8)']['word'] == 'rejected (contradicted)'` | Proves that H8 is `contradicted` in a session, and that the word over the two sessions is `rejected (contradicted)`. |
| 385 | `    # one process split and one uniform at a count: the count is "mixed", and equal brackets are not resolved` | Comment: one split and one uniform process at a count make the count mixed. Equal brackets are not resolved. |
| 386 | `    blocks = [b8(36, i, True, True) for i in (1, 2)] + [b8(40, 1, True, True), b8(40, 2, False, False)] + [b8(44, i, False, False) for i in (1, 2)]` | Both kernels are split at 36 and uniform at 44. At 40 one process is split and the other is uniform. |
| 387 | `    r = analyze({'s1': {'B8.csv': blocks}})['sessions']['s1']['B8']` | Runs the analysis. |
| 388 | `    assert r['kernels']['oldread']['counts'][40]['label'] == 'mixed' and r['kernels']['oldread']['bracket'] == (36, 44) and r['H8'] == 'not resolved at this grid'` | Proves that the count 40 is `mixed`, that the bracket of old read is 36 to 44, and that H8 is `not resolved at this grid`: both kernels have the same bracket. |
| 389 | `    # old read never uniform: no bracket and no decision` | Comment: when old read is never uniform, there is no bracket and no decision. |
| 390 | `    r = analyze({'s1': {'B8.csv': [b8(b, i, True, b < 44) for i in (1, 2) for b in (36, 40, 44)]}})['sessions']['s1']['B8']` | Runs the analysis on files in which old read is split at all three counts and `asmread` is split below 44. |
| 391 | `    assert r['kernels']['oldread']['bracket'] is None and r['H8'] == 'not resolved'` | Proves that old read has no bracket and that H8 is `not resolved`. |

### Helper `b5` and the test of step B5 (lines 394 to 422)

| Line | Source | Explanation |
|---:|---|---|
| 394 | `def b5(i, sparse_split, sparse_rate=None):` | Starts the function `b5`. It builds one process of step B5. `sparse_split` says whether the variant `read_sparse` is split. `sparse_rate` may give its rate on mesh 0. |
| 395 | `    def rate(r, pos, entry, tid, cpu):` | Starts the inner rate function. |
| 396 | `        if entry == 'oldread':` | For old read. |
| 397 | `            return 5.0 if cpu < 64 else 2.7` | 5.0 GB/s on the CPUs 0 to 63 and 2.7 GB/s on the others: a split pattern with a total of 471.2 GB/s. |
| 398 | `        if entry == 'read_sparse':` | For `read_sparse`. |
| 399 | `            return (sparse_rate or 4.97 if cpu < 64 else 2.7) if sparse_split else 2.5` | When it is split: `sparse_rate` on the CPUs 0 to 63, or 4.97 GB/s without that argument, and 2.7 GB/s on the others. When it is not split: 2.5 GB/s on every thread. |
| 400 | `        return 2.525 if entry == 'asmread2' else 2.5` | Every other entry gets 2.5 GB/s, and `asmread2` gets 2.525 GB/s. So `E` is 3.0 GB/s (120 times 0.025). |
| 401 | `    seq = B5SEQ if i % 2 else ','.join(reversed(B5SEQ.split(',')))` | `seq`: the sequence `B5SEQ` for an odd process number, and the same entries in the reversed order for an even one. |
| 402 | `    return block('B5', 'b5-%s-p%d' % ('fwd' if i % 2 else 'rev', i), '%s --seq %s --rounds 1 --stop common --min-ms 6000 --start offset' % (ALL, seq), rate)` | Calls `block` with a tag of the form `b5-fwd-p1` or `b5-rev-p2`, 120 threads, 1 round, the common stop, 6000 ms and the offset start. |
| 405 | `def test_b5():` | Starts the test `test_b5`. |
| 406 | `    """WHY: a variant "shows the pattern and total of old read" only if BOTH hold: same pattern label in the same` | Docstring, the reason: a variant "shows the pattern and total of old read" only if both hold. The first is the same pattern label in the same process. The docstring goes on in line 407. |
| 407 | `    process, and a total difference that is not resolved against the A/A spread."""` | Docstring: the second is a total difference that is not resolved against the A/A spread. |
| 408 | `    yes = {'B5.csv': [b5(i, True) for i in range(1, 5)]}` | `yes`: a session with 4 processes in which `read_sparse` is split like old read. |
| 409 | `    out = analyze({'s1': yes, 's2': yes})` | Runs the analysis on two such sessions. |
| 410 | `    v = out['sessions']['s1']['B5']['variants']` | `v`: the results per variant of the first session. |
| 411 | `    assert v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'yes'            # split, and 1.92 GB/s below old read against an A/A of 3` | Proves the answer `yes` for `read_sparse`. By the comment it is split, and its total lies 1.92 GB/s below old read (64 times 0.03) against an A/A spread of 3 GB/s. |
| 412 | `    assert v['read_nop4']['shows_pattern_and_total_of_oldread'] == 'no' and v['read_nop4']['same_pattern'] is False` | Proves the answer `no` for `read_nop4`, with `same_pattern` false: it is uniform while old read is split. |
| 413 | `    assert out['hypotheses']['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'rejected'` | Proves that the statement of step B5 is then `rejected` over the two sessions. |
| 414 | `    # same pattern but a resolved lower total: not "the pattern and total of old read"` | Comment: the same pattern with a resolved lower total is not "the pattern and total of old read". |
| 415 | `    v = analyze({'s1': {'B5.csv': [b5(i, True, sparse_rate=4.5) for i in range(1, 5)]}})['sessions']['s1']['B5']['variants']` | Runs the analysis with `read_sparse` at 4.5 GB/s on mesh 0. It is still split (`q` is 0.6), and its total lies 32 GB/s below old read. |
| 416 | `    assert v['read_sparse']['same_pattern'] is True and v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'no'` | Proves that the pattern is the same and that the answer is still `no`. So the pattern alone is not enough. |
| 417 | `    out = analyze({'s1': {'B5.csv': [b5(i, False) for i in range(1, 5)]}, 's2': yes})` | Runs the analysis on two sessions: one in which `read_sparse` is uniform, and the session `yes`. |
| 418 | `    assert out['hypotheses']['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'not rejected'` | Proves that the statement is `not rejected` when its prediction fails in only one of the two sessions. |
| 419 | `    v = analyze({'s1': {'B5.csv': [b5(i, True) for i in range(1, 4)]}})['sessions']['s1']['B5']['variants']` | Runs the analysis on 3 processes. |
| 420 | `    assert v['read_sparse']['shows_pattern_and_total_of_oldread'] == 'not observed'     # 3 processes` | Proves that the answer is then `not observed`. By the comment the reason is the 3 processes. |

### Helper `b9` and the test of step B9 (lines 423 to 439)

| Line | Source | Explanation |
|---:|---|---|
| 423 | `def b9(i, two, is_split):` | Starts the function `b9`. It builds one process of step B9. `two` adds the option `--two-buffers`. `is_split` chooses the pattern. |
| 424 | `    return block('B9', '%s-p%d' % ('twobuf' if two else 'onebuf', i), '%s --seq oldread --rounds 3 --stop common --min-ms 6000 --start common%s' % (ALL, ' --two-buffers' if two else ''),` | Calls `block` with a tag of the form `onebuf-p1` or `twobuf-p1`, 120 threads, the sequence `oldread` alone, 3 rounds, the common stop and 6000 ms. The call goes on in line 425. |
| 425 | `                 lambda r, pos, e, tid, cpu: ((5.0 if cpu < 64 else 2.7) if is_split else 3.0) + 0.001 * i)` | Continues line 424: the rate is split (5.0 and 2.7 GB/s) or uniform (3.0 GB/s), plus 0.001 GB/s times the process number on every thread. So the totals of two processes of one kind differ by 0.12 GB/s per step of the process number. |
| 428 | `def test_b9():` | Starts the test `test_b9`. |
| 429 | `    """WHY: H9a is rejected only if the pattern is the same with one and with two buffers, in both sessions."""` | Docstring, the reason: H9a is rejected only if the pattern is the same with one buffer and with two, in both sessions. |
| 430 | `    pred = {'B9.csv': [b9(i, two, not two) for i in (1, 2, 3) for two in (False, True)]}` | `pred`: 3 processes of each kind: split with one buffer and uniform with two. This is what H9a predicts. |
| 431 | `    same = {'B9.csv': [b9(i, two, True) for i in (1, 2, 3) for two in (False, True)]}` | `same`: 3 processes of each kind, all split. |
| 432 | `    r = analyze({'s1': pred})['sessions']['s1']['B9']` | Runs the analysis on `pred`. |
| 433 | `    assert r['pattern_result'] == 'pattern as H9a predicts' and r['total']['decision'] == 'resolved' and near(r['total']['aa_value'], 0.24, 0.01)` | Proves the pattern result `pattern as H9a predicts`, a resolved total, and an A/A value of 0.24 GB/s. That is the difference between the totals of the processes 1 and 3 of one kind (120 times 0.002). |
| 434 | `    out = analyze({'s1': same, 's2': same})` | Runs the analysis on two sessions `same`. |
| 435 | `    assert out['sessions']['s1']['B9']['pattern_result'] == 'same pattern' and out['sessions']['s1']['B9']['total']['decision'] == 'not resolved'` | Proves the pattern result `same pattern` and a total that is `not resolved`. |
| 436 | `    assert out['hypotheses']['H9a (B9)']['word'] == 'rejected'` | Proves that H9a is `rejected` over the two sessions. |
| 437 | `    assert analyze({'s1': same, 's2': pred})['hypotheses']['H9a (B9)']['word'] == 'not rejected'` | Proves that H9a is `not rejected` when only one of the two sessions shows the same pattern. |

### Test: the entries that use a label also hold the word without labels (lines 440 to 465)

| Line | Source | Explanation |
|---:|---|---|
| 440 | `def test_label_entries_carry_the_word_without_labels():` | Starts the test `test_label_entries_carry_the_word_without_labels`. |
| 441 | `    """WHY: the user decided on 2026-11-13 that the labels split and uniform are not used, and that a rule which needs a` | Docstring, the reason: the user decided on 2026-11-13 that the labels split and uniform are not used, and that a rule which needs a label gives `not resolved`. The docstring goes on in lines 442 to 444. |
| 442 | `    label gives "not resolved" (decisions.md, item 2). The label rule of B.10 is still computed. So every entry that rests` | Docstring: this is item 2 of the file `decisions.md`. The label rule of section B.10 is still computed. So every entry that uses a label must also hold the word without labels. |
| 443 | `    on a label must carry the word without labels next to it, and the text output must say so at the entry. Without` | Docstring: and the text output must say so at the entry. |
| 444 | `    this, hypotheses.txt presents "H9a: rejected" as a decision (A33)."""` | Docstring: without this the file `hypotheses.txt` presents "H9a: rejected" as a decision (point A33 of the deviations note). |
| 445 | `    same = {'B9.csv': [b9(i, two, True) for i in (1, 2, 3) for two in (False, True)],` | `same`: one session with three files. Step B9: all processes are split. The dictionary goes on in lines 446 to 447. |
| 446 | `            'B8.csv': [b8(b, i, b < 40, b < 24) for b in (16, 24, 32, 40, 48, 56) for i in (1, 2)],` | Continues line 445. Step B8: 2 processes at each of 6 counts of mesh-1 threads. Old read is split below 40, and `asmread` below 24. |
| 447 | `            'B5.csv': [b5(i, True) for i in range(1, 5)]}` | Continues line 445. Step B5: 4 processes in which `read_sparse` is split like old read. |
| 448 | `    out = analyze({'s1': same, 's2': same})` | Runs the analysis on two such sessions. |
| 449 | `    h = out['hypotheses']` | `h`: the entries of the hypotheses. |
| 450 | `    assert h['H9a (B9)']['word'] == 'rejected' and h['H9a (B9)']['word_without_labels'] == 'not resolved'` | Proves that H9a has the word `rejected` from the label rule, and the word `not resolved` without labels. |
| 451 | `    assert h['H8 (B8)']['word_without_labels'] == 'not resolved'` | Proves that the entry for H8 has the word `not resolved` without labels. |
| 452 | `    name = 'B5 statement "vector adds are needed for the split pattern of old read"'` | `name`: the name of the entry for the statement of step B5. |
| 453 | `    # read_sparse equal to old read in pattern and total: the label rule rejects, and without labels nothing decides.` | Comment: `read_sparse` equals old read in pattern and total. The label rule rejects, and without labels nothing decides. |
| 454 | `    assert h[name]['word'] == 'rejected' and h[name]['word_without_labels'] == 'not resolved'` | Proves that: the word is `rejected`, and the word without labels is `not resolved`. |
| 455 | `    # A resolved lower total of read_sparse decides without any label.` | Comment: a resolved lower total of `read_sparse` decides without any label. |
| 456 | `    low = {'B5.csv': [b5(i, False) for i in range(1, 5)]}` | `low`: a session in which `read_sparse` is uniform at 2.5 GB/s per thread. Its total lies 171.2 GB/s below old read. |
| 457 | `    h2 = analyze({'s1': low, 's2': low})['hypotheses'][name]` | Runs the analysis on two such sessions and takes the entry. |
| 458 | `    assert h2['word_without_labels'] == 'not rejected' and h2['per_session_without_labels'] == {'s1': 'hold', 's2': 'hold'}` | Proves that the word without labels is then `not rejected`, with the flag `hold` in both sessions. |
| 459 | `    # An entry that uses no label carries no such word.` | Comment: an entry that uses no label has no such word. |
| 460 | `    assert all('word_without_labels' not in v for k, v in h.items() if not k.startswith(('H8', 'H9a', 'B5 statement')))` | Proves that no entry other than H8, H9a and the statement of B5 has a word without labels. |
| 461 | `    t = ab.text_hypotheses(out)` | `t`: the text of the hypothesis entries. |
| 462 | `    assert t.count('LABELS NOT USED') == 3 and 'Without labels the word is "not resolved"' in t` | Proves that the text holds `LABELS NOT USED` exactly 3 times, and the sentence that gives the word `not resolved` without labels. |
| 463 | `    assert 'NOT USED' in ab.text_step('s1', 'B9', out['sessions']['s1']['B9']) and any('NOT USED' in x for x in out['limits'])` | Proves that the table text of step B9 holds `NOT USED`, and that one of the limits of the summary holds it too. |

### Helper `b10` and the test of step B10 (lines 466 to 511)

| Line | Source | Explanation |
|---:|---|---|
| 466 | `def b10(setting, i, kind):` | Starts the function `b10`. It builds one process of step B10. `kind` chooses the invented behaviour of the write kernels. |
| 467 | `    """kind 'levels': write has one interval (round 1, pos 6) in which mesh 1 is faster; old write has one in which` | Docstring: with the kind `levels` the kernel `write` has one interval (round 1, position 6) in which mesh 1 is faster. Old write has one interval in which both meshes are faster. The docstring goes on in line 468. |
| 468 | `    both meshes are faster. kind 'flat': every interval is the same. kind 'aa-mesh': the A/A copies differ per mesh."""` | Docstring: with the kind `flat` every interval is the same. With the kind `aa-mesh` the two A/A copies differ per mesh. |
| 469 | `    def rate(r, pos, entry, tid, cpu):` | Starts the inner rate function. |
| 470 | `        hi = kind != 'flat' and r == 1 and pos in (6, 7)` | `hi`: true in round 1 at the positions 6 and 7, unless the kind is `flat`. Position 6 is the second `write` interval of the round, and position 7 is the second `oldwrite` interval. |
| 471 | `        if entry == 'write':` | For the kernel `write`. |
| 472 | `            return 1.5 if hi and cpu >= 64 and kind == 'levels' else 1.01 if hi and cpu >= 64 else 1.0` | In the high interval the threads on the CPUs from 64 on get 1.5 GB/s with the kind `levels`, and 1.01 GB/s with the kind `aa-mesh`. Every other thread and interval gets 1.0 GB/s. |
| 473 | `        if entry == 'oldwrite':` | For the kernel `oldwrite`. |
| 474 | `            return 1.3 if hi and kind == 'levels' else 1.0` | In the high interval every thread gets 1.3 GB/s with the kind `levels`. If not, it gets 1.0 GB/s. |
| 475 | `        if kind == 'aa-mesh' and entry == 'asmwrite2':` | For `asmwrite2` with the kind `aa-mesh`. |
| 476 | `            return 1.05 if cpu < 64 else 0.942857142857                 # mesh 0 +3.2 GB/s, mesh 1 -3.2 GB/s, total equal` | 1.05 GB/s on the CPUs 0 to 63 and 0.942857 GB/s on the others. By the comment mesh 0 is then 3.2 GB/s higher and mesh 1 is 3.2 GB/s lower than `asmwrite`, and the two totals are equal. |
| 477 | `        return 1.0 + (0.002 if entry == 'asmwrite2' and r == 1 else 0.0)` | Every other case: 1.0 GB/s. `asmwrite2` gets 0.002 GB/s more per thread in round 1, which is 0.24 GB/s in the total of 120 threads. |
| 478 | `    return b7(setting, i, rate, seq=B10SEQ, step='B10')` | Builds the process with `b7` (line 285), with the sequence `B10SEQ` and the step name `B10`. |
| 481 | `def test_b10():` | Starts the test `test_b10`. |
| 482 | `    """WHY: the spread is one value per process; H11 judges each mesh with the control of ITS OWN rate."""` | Docstring, the reason: the spread is one value per process. H11 judges each mesh with the control of its own rate. |
| 483 | `    A, B = 'pass/500/common', 'common/15000/common'` | `A`: the setting `pass/500/common`. `B`: the setting `common/15000/common`. |
| 484 | `    files = {'B10a-x.csv': [b10(A, i, 'levels') for i in (1, 2)] + [b10(B, i, 'flat') for i in (1, 2)],` | `files`: two csv files, as the two halves of step B10 in one session. The first file holds the processes 1 and 2 of `A` with the kind `levels` and of `B` with the kind `flat`. The dictionary goes on in line 485. |
| 485 | `             'B10b-x.csv': [b10(A, i, 'levels') for i in (3, 4)] + [b10(B, i, 'flat') for i in (3, 4)]}       # the two halves of one session` | Continues line 484: the second file holds the processes 3 and 4 of both settings. By the comment these are the two halves of one session, so the analysis must join them. |
| 486 | `    out = analyze({'s1': files, 's2': files})` | Runs the analysis on two such sessions. |
| 487 | `    r = out['sessions']['s1']['B10']` | `r`: the result of step B10 of the first session. |
| 488 | `    a = r['settings'][A]` | `a`: the result of the setting `A`. |
| 489 | `    assert a['n_processes'] == 4 and near(a['control_total'], 0.24, 0.01) and near(a['control_spread'], 0.24, 0.01)` | Proves that the 4 processes of the two files are joined into one setting, and that the control of the total and the control of the spread are both 0.24 GB/s. |
| 490 | `    assert near(a['kernels']['write']['median_spread'], 28.0) and a['kernels']['write']['H11'] == 'supported'           # only mesh 1 rose` | Proves a median spread of 28.0 GB/s for `write` (56 threads times 0.5 GB/s) and the word `supported` for H11. By the comment only mesh 1 rose. |
| 491 | `    assert near(a['kernels']['write']['high_minus_low'][0]['mesh1'], 28.0) and near(a['kernels']['write']['high_minus_low'][0]['mesh0'], 0.0)` | Proves the numbers of this result: in the first process mesh 1 is 28.0 GB/s higher in the interval with the highest total, and mesh 0 is unchanged. |
| 492 | `    assert a['kernels']['oldwrite']['H11'] == 'contradicted'                                                            # both meshes rose` | Proves that H11 is `contradicted` for `oldwrite`. By the comment both meshes rose. |
| 493 | `    assert r['settings'][B]['kernels']['write']['H11'] == 'not observed'                                                # no interval with a higher total` | Proves that H11 is `not observed` for `write` in the setting `B`. By the comment it has no interval with a higher total. |
| 494 | `    assert r['spread_changes'] == {}                         # A and B differ in two factors: no change is computed between them` | Proves that no change of the spread is computed. By the comment `A` and `B` differ in two factors. |
| 495 | `    assert out['hypotheses']['H11 (B10, %s, write)' % A]['word'] == 'not rejected (supported)'` | Proves the word `not rejected (supported)` for H11 with `write` over the two sessions. |
| 496 | `    assert out['hypotheses']['H11 (B10, %s, oldwrite)' % A]['word'] == 'rejected (contradicted)'` | Proves the word `rejected (contradicted)` for H11 with `oldwrite` over the two sessions. |
| 497 | `    # settings that differ in one factor: the spread of write changes from 28 to 0 GB/s` | Comment: the next case has settings that differ in one factor. The spread of `write` changes from 28 to 0 GB/s. |
| 498 | `    C = 'common/500/common'` | `C`: the setting `common/500/common`. |
| 499 | `    r = analyze({'s1': {'B10.csv': [b10(A, i, 'levels') for i in range(1, 5)] + [b10(C, i, 'flat') for i in range(1, 5)]}})['sessions']['s1']['B10']` | Runs the analysis on 4 processes of `A` with the kind `levels` and 4 processes of `C` with the kind `flat`. |
| 500 | `    c = r['spread_changes']['write stop: %s -> %s' % (A, C)]` | `c`: the change of the spread of `write` for the stop method. |
| 501 | `    assert c['decision'] == 'resolved' and near(c['change_of_spread'], 28.0) and c['n_first'] == 4` | Proves that it is resolved, with a change of 28.0 GB/s and 4 processes in the first setting. |
| 502 | `    assert r['spread_changes']['asmwrite stop: %s -> %s' % (A, C)]['decision'] == 'not resolved'` | Proves that the change for `asmwrite` is `not resolved`: its spread is 0 GB/s in both settings. |
| 503 | `    # A/A copies with equal totals and opposite mesh rates: the control of each mesh is 3.2 GB/s. A rise of 0.56 GB/s on mesh 1 is not support.` | Comment: A/A copies with equal totals and opposite mesh rates give a control of 3.2 GB/s for each mesh. A rise of 0.56 GB/s on mesh 1 is not support. |
| 504 | `    r = analyze({'s1': {'B10.csv': [b10(A, i, 'aa-mesh') for i in range(1, 5)]}})['sessions']['s1']['B10']['settings'][A]` | Runs the analysis on 4 processes of the kind `aa-mesh` and takes the setting `A`. |
| 505 | `    assert r['control_total'] < 0.01 and near(r['control_mesh0'], 3.2) and near(r['control_mesh1'], 3.2)` | Proves the controls: below 0.01 GB/s for the total, and 3.2 GB/s for each mesh. |
| 506 | `    assert r['kernels']['write']['H11'] == 'not resolved'` | Proves that H11 is `not resolved` for `write`. The rise of 0.56 GB/s on mesh 1 (56 threads times 0.01 GB/s) lies inside the control of mesh 1. With the control of the total in its place the rise would have counted as support. |
| 507 | `    # 3 processes: no change of the spread can be decided` | Comment: with 3 processes no change of the spread can be decided. |
| 508 | `    r = analyze({'s1': {'B10.csv': [b10(A, i, 'levels') for i in range(1, 4)] + [b10(C, i, 'flat') for i in range(1, 5)]}})['sessions']['s1']['B10']` | Runs the analysis on 3 processes of `A` and 4 processes of `C`. |
| 509 | `    assert r['spread_changes']['write stop: %s -> %s' % (A, C)]['decision'] == 'not observed'` | Proves that the change of the spread is then `not observed`. |

### Tests of the counter rows and of the step SHORT (lines 512 to 534)

| Line | Source | Explanation |
|---:|---|---|
| 512 | `# ------------------------------------------------------------ counters, SHORT, sessions, files` | Comment: a divider. The tests of the counters, of the step SHORT, of the sessions and of the output files start here. |
| 514 | `def test_counters():` | Starts the test `test_counters`. |
| 515 | `    """WHY: a C row whose running time is below its enabled time was multiplexed and is not used (handoff B.8)."""` | Docstring, the reason: a `C` row whose running time is below its enabled time was multiplexed and is not used (section B.8 of the handoff note). |
| 516 | `    def counts(r, pos, entry, tid, nbytes):` | Starts the inner function `counts`. It gives the fields of a `C` row after the CPU. |
| 517 | `        run = 290000000 if r == 1 else 300000000` | `run`: the running time in ns: 290000000 in round 1, and 300000000 in every other round. |
| 518 | `        return '300000000,%d,299000000,%d,%d,%d,NA,%d' % (run, 897000000, nbytes * 11 // 256, nbytes // 64, nbytes // 640)` | The fields: an enabled time of 300000000 ns, the running time, a CPU time of 299000000 ns, 897000000 cycles, 11 instructions per 256 B, one refill of the level 1 cache per 64 B, `NA` for the fourth event, and one read miss of the last level per 640 B. |
| 519 | `    blk = block('C1', 'cpu2-p1', '--threads 1 --cpus 2 --bytes 8M --seq asmread --rounds 4 --min-ms 300 --stop pass --count', lambda *a: 67.5, counts=counts)` | `blk`: one process of step C1 on CPU 2: 8 MiB, `asmread` alone, 4 rounds, the option `--count`, and 67.5 GB/s in every interval. |
| 520 | `    r = analyze({'s1': {'C1.csv': [blk]}})['sessions']['s1']['C1']` | Runs the analysis and takes step C1. |
| 521 | `    assert r['rows_C'] == 4 and r['rows_C_not_used'] == 1` | Proves that 4 `C` rows are read and that 1 is not used: the row of round 1, whose running time of 290 ms is below its enabled time of 300 ms. |
| 522 | `    g = r['groups'][0]` | `g`: the first group of the result. |
| 523 | `    assert g['level'] == 'low' and g['n_rows'] == 3 and near(g['median_instructions_per_line'], 2.75, 0.001) and near(g['median_clock_GHz'], 3.0, 0.001)` | Proves the group: the level `low`, 3 rows, 2.75 instructions per 64 B line (11 per 256 B), and a clock rate of 3.0 GHz (897000000 cycles in 299000000 ns). |
| 524 | `    assert g['not_supported'] == ['l2d_refill'] and near(g['median_ll_read_miss_per_line'], 0.1, 0.001)` | Proves that the event without a count is listed as not supported (`l2d_refill`), and that the read misses are 0.1 per line. |
| 527 | `def test_short_step_gives_no_decision():` | Starts the test `test_short_step_gives_no_decision`. |
| 528 | `    """WHY: the short run checks the output of bwx; nothing in it may look like a result."""` | Docstring, the reason: the short run checks the output of the runner. Nothing in it may look like a result. |
| 529 | `    blk = block('SHORT', 'b4-nothp', '--threads 1 --cpus 2 --min-ms 100 --stop pass --bytes 8M --seq asmread --rounds 5 --no-thp', lambda *a: 67.5, page=lambda r, pos: ('NA', 'NA'))` | `blk`: one process of the step SHORT with 5 rounds and `NA` in every `P` row. |
| 530 | `    out = analyze({'s1': {'SHORT.csv': [blk]}})` | Runs the analysis. |
| 531 | `    r = out['sessions']['s1']['SHORT']` | `r`: the result of the step SHORT. |
| 532 | `    assert r['processes'][0]['complete'] and r['processes'][0]['P_rows_NA'] == 5 and r['page_rows_NA'] == 5 and out['hypotheses'] == {}` | Proves that the process is listed as complete, that the 5 `P` rows with `NA` are counted for the process and for the step, and that no hypothesis gets an entry. |

### Tests of the words over two sessions and of the command line (lines 535 to 568)

| Line | Source | Explanation |
|---:|---|---|
| 535 | `def test_two_sessions_words():` | Starts the test `test_two_sessions_words`. |
| 536 | `    """WHY: "rejected" needs the failed prediction in both sessions (plan, rule 11)."""` | Docstring, the reason: the word `rejected` needs the failed prediction in both sessions (rule 11 of the plan). |
| 537 | `    assert ab.two_sessions({'s1': 'fail', 's2': 'fail'}) == 'rejected'` | Proves that two flags `fail` give `rejected`. |
| 538 | `    assert ab.two_sessions({'s1': 'fail', 's2': 'hold'}) == 'not rejected'` | Proves that `fail` and `hold` give `not rejected`. |
| 539 | `    assert ab.two_sessions({'s1': 'fail', 's2': 'not observed'}) == 'not rejected'` | Proves that `fail` and `not observed` give `not rejected`. |
| 540 | `    assert ab.two_sessions({'s1': 'not observed', 's2': 'not observed'}) == 'not observed'` | Proves that two flags `not observed` give `not observed`. |
| 541 | `    assert 'one session only' in ab.two_sessions({'s1': 'fail'})` | Proves that one session with the flag `fail` gives a word that holds `one session only`. |
| 542 | `    # H4: resolved with the same sign in both sessions is the failure of its prediction; opposite signs are not` | Comment: for H4 a difference that is resolved with the same sign in both sessions is the failure of its prediction. Opposite signs are not. |
| 543 | `    neg = {'B1.csv': [b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)]}` | `neg`: a session of step B1 with a `d` of -2.0 GB/s on the CPUs 0 and 2. |
| 544 | `    pos = {'B1.csv': [b1(c, i, copy_rate(copy=60.0)) for c in (0, 2) for i in range(1, 5)]}` | `pos`: the same with `copy` at 60.0 GB/s, so `d` is +2.0 GB/s. |
| 545 | `    assert analyze({'s1': neg, 's2': neg})['hypotheses']['H4 (B1, 8 MiB, label low)']['word'] == 'rejected'` | Proves that two sessions `neg` give the word `rejected` for H4 with the label `low`. |
| 546 | `    assert analyze({'s1': neg, 's2': pos})['hypotheses']['H4 (B1, 8 MiB, label low)']['word'] == 'not rejected'` | Proves that `neg` and `pos` give `not rejected`: both sessions are resolved, with opposite signs. |
| 547 | `    assert analyze({'s1': neg, 's2': neg})['hypotheses']['H4 (B1, 8 MiB, label high)']['word'] == 'not observed'` | Proves that H4 with the label `high` is `not observed` when no process is at the high level. |
| 550 | `def test_command_line_writes_json_and_tables():` | Starts the test `test_command_line_writes_json_and_tables`. |
| 551 | `    """WHY: the lead needs a json summary and a text table per step, each decision with its processes and A/A spread."""` | Docstring, the reason: the lead needs a JSON summary and a text table per step, each decision with its processes and its A/A spread. |
| 552 | `    d = os.path.join(TMP, 'cli', 'B1-20261114T000000Z')` | `d`: a folder with a name in the form of a result folder, `B1-20261114T000000Z`, below `TMP`. |
| 553 | `    os.makedirs(d)` | Makes the folder. |
| 554 | `    with open(os.path.join(d, 'B1.csv'), 'w') as fh:` | Opens the file `B1.csv` in it for writing. |
| 555 | `        fh.write(''.join(b1(c, i, copy_rate()) for c in (0, 2) for i in range(1, 5)))` | Writes 8 processes of step B1: 4 on each of the CPUs 0 and 2. |
| 556 | `    out = os.path.join(TMP, 'cli-out')` | `out`: the path of the output folder. |
| 557 | `    stdout, sys.stdout = sys.stdout, open(os.devnull, 'w')` | Keeps the standard output and puts the null device in its place. So the tables that `main` prints do not show. |
| 558 | `    try:` | Starts a block. Line 560 runs after it in every case. |
| 559 | `        assert ab.main(['--session', 's1', d, '--out', out]) == 0` | Proves that `main` of the analysis returns 0 when it is called with one session, the folder and `--out`. |
| 560 | `    finally:` | In every case, also after a failed check. |
| 561 | `        sys.stdout.close()` | Closes the null device. |
| 562 | `        sys.stdout = stdout` | Puts the standard output back. |
| 563 | `    s = json.load(open(os.path.join(out, 'summary.json')))` | `s`: the content of the file `summary.json` that `main` wrote. |
| 564 | `    assert s['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'resolved'` | Proves that the summary in the file holds the decision: resolved for the label `low` at 8 MiB. |
| 565 | `    t = open(os.path.join(out, 'B1.txt')).read()` | `t`: the text of the file `B1.txt`. |
| 566 | `    assert 'A/A spread GB/s' in t and 'processes' in t and 'system load' in t and 'resolved (-)' in t` | Proves that the table holds the column name `A/A spread GB/s`, the word `processes`, the line of the system load, and the decision `resolved (-)` with its sign. |
| 567 | `    assert 'H4' in open(os.path.join(out, 'hypotheses.txt')).read()` | Proves that the file `hypotheses.txt` holds an entry for H4. |

### Tests added after the review: H7 needs the reproduction, and a disagreement of the metrics (lines 569 to 605)

| Line | Source | Explanation |
|---:|---|---|
| 569 | `# ------------------------------------------------------------ preconditions and metric disagreements (review of 2026-11-13)` | Comment: a divider. The tests of the preconditions and of the disagreements of the two metrics follow. The comment names the review of 2026-11-13. |
| 571 | `H7A, H7B, H6, B5STMT = 'H7a (B7, read)', 'H7b (B7, read)', 'H6 (B3)', 'B5 statement "vector adds are needed for the split pattern of old read"'` | Four short names for the entries of H7a, H7b, H6 and the statement of step B5. |
| 574 | `def test_h7_needs_the_reproduction():` | Starts the test `test_h7_needs_the_reproduction`. |
| 575 | `    """WHY: the plan assigns no cause when B7 reproduces no difference. "No factor changed D" must then not be` | Docstring, the reason: the plan assigns no cause when step B7 reproduces no difference. The docstring goes on in line 576. |
| 576 | `    the word "rejected" for H7a and H7b: there was no D that a factor could change."""` | Docstring: "no factor changed `D`" must then not become the word `rejected` for H7a and H7b: there was no `D` that a factor could change. |
| 577 | `    flat = lambda i: (lambda r, pos, e, tid, cpu: 3.0 + (0.0005 * i if e == 'asmread2' else 0))` | `flat`: a function that gives a rate function for a process number. Every kernel runs at 3.0 GB/s per thread. `asmread2` gets 0.0005 GB/s more per thread times the process number, so `E` is small and not 0. |
| 578 | `    sets = ['%s/%s/%s' % (a, b, c) for a in ('pass', 'common') for b in ('500', '6000') for c in ('common', 'offset')]` | `sets`: the names of all 8 settings: 2 stop methods times 2 interval lengths times 2 start methods. |
| 579 | `    files = {'B7.csv': [b7(s, i, flat(i)) for i in range(1, 5) for s in sets]}` | `files`: 4 processes of each setting with the flat rates. |
| 580 | `    out = analyze({'s1': files, 's2': files})` | Runs the analysis on two such sessions. |
| 581 | `    r = out['sessions']['s1']['B7']` | `r`: the result of step B7 of the first session. |
| 582 | `    assert r['reproduced_in_either_way'] is False and all(c['decision'] == 'not resolved' for c in r['changes'].values())` | Proves that `D` was not reproduced in either way, and that every change between settings is `not resolved`. |
| 583 | `    for h in (H7A, H7B):` | Loop over H7a and H7b. |
| 584 | `        assert out['hypotheses'][h]['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and out['hypotheses'][h]['word'] == 'not observed'` | Proves that both sessions have the flag `not observed` and that the word is `not observed`. By point A26 of the deviations note such sessions gave `fail` before, and two of them gave the word `rejected` [Ref3]. |
| 585 | `    # with the reproduction, the same "no resolved change" in two sessions IS the failure of the prediction` | Comment: with the reproduction, the same "no resolved change" in two sessions is the failure of the prediction. |
| 586 | `    files = {'B7.csv': [b7(s, i, read_rate()) for i in range(1, 5) for s in sets]}` | `files`: 4 processes of each setting with the default rates. `D` is 171.2 GB/s in every setting. |
| 587 | `    out = analyze({'s1': files, 's2': files})` | Runs the analysis on two such sessions. |
| 588 | `    assert out['sessions']['s1']['B7']['reproduced_in_either_way'] is True` | Proves that `D` counts as reproduced. |
| 589 | `    assert out['hypotheses'][H7A]['word'] == 'rejected' and out['hypotheses'][H7B]['word'] == 'rejected'` | Proves that H7a and H7b are then `rejected`: `D` exists, and no factor changes it. |
| 592 | `def test_h7_metric_disagreement_is_not_a_failure():` | Starts the test `test_h7_metric_disagreement_is_not_a_failure`. |
| 593 | `    """WHY: a change of D that M_hist resolves and M_sum does not is "not resolved" (handoff B.10). It is not` | Docstring, the reason: a change of `D` that `M_hist` resolves and `M_sum` does not is `not resolved` (section B.10 of the handoff note). The docstring goes on in line 594. |
| 594 | `    evidence that the factor has no effect, so it must not count as the failed prediction of H7b."""` | Docstring: it is no evidence that the factor has no effect. So it must not count as the failed prediction of H7b. |
| 595 | `    # offset start: in the read intervals thread 0 needs 1.0 s for its last pass. M_sum of read is unchanged, M_hist halves.` | Comment: with the offset start, thread 0 needs 1.0 s for its last pass in the `read` intervals. `M_sum` of `read` is unchanged, and `M_hist` halves. |
| 596 | `    slow = lambda r, pos, e, tid: 1.0 if e == 'read' and tid == 0 else None` | `slow`: thread 0 gets an elapsed time of 1.0 s in the `read` intervals. |
| 597 | `    files = {'B7.csv': [b7('pass/500/common', i, read_rate()) for i in range(1, 5)] +` | `files`: 4 processes of `pass/500/common` with the default rates. The list goes on in line 598. |
| 598 | `                       [b7('pass/500/offset', i, read_rate(), elapsed=slow) for i in range(1, 5)]}` | Continues line 597: 4 processes of `pass/500/offset` with the same rates and the function `slow`. |
| 599 | `    out = analyze({'s1': files, 's2': files})` | Runs the analysis on two such sessions. |
| 600 | `    c = out['sessions']['s1']['B7']['changes']['start: pass/500/common -> pass/500/offset']` | `c`: the change of `D` for the start. |
| 601 | `    assert c['metrics']['M_hist']['decision'] == 'resolved' and c['metrics']['M_sum']['decision'] == 'not resolved'` | Proves that `M_hist` resolves the change and `M_sum` does not. |
| 602 | `    assert c['decision'] == 'not resolved' and c['metrics_disagree'] is True and 'M_sum' in c['note']` | Proves that the change is `not resolved`, that `metrics_disagree` is true, and that the note names `M_sum`. |
| 603 | `    assert out['hypotheses'][H7B]['per_session'] == {'s1': 'not resolved', 's2': 'not resolved'} and out['hypotheses'][H7B]['word'] == 'not rejected'` | Proves that the flag of H7b is `not resolved` in both sessions and that the word is `not rejected`. Without the rule the word would be `rejected`. |

### Tests added after the review: H6 needs a resolved B1, and B5 with a disagreement (lines 606 to 638)

| Line | Source | Explanation |
|---:|---|---|
| 606 | `def test_h6_needs_a_resolved_b1():` | Starts the test `test_h6_needs_a_resolved_b1`. |
| 607 | `    """WHY: the plan runs B3 only after a resolved difference in B1. With copy = asmcopy in B1 and in all builds,` | Docstring, the reason: the plan runs step B3 only after a resolved difference in B1. The docstring goes on in line 608. |
| 608 | `    "the offset changed nothing" must not reject H6 (H5 has the same guard)."""` | Docstring: with `copy` equal to `asmcopy` in B1 and in all builds, "the offset changed nothing" must not reject H6. H5 has the same guard. |
| 609 | `    def sess(copy):` | Starts the inner function `sess`. It builds one session for a given rate of `copy`. |
| 610 | `        cr = lambda: copy_rate(copy=copy)` | `cr`: a function that gives the rate function with this rate of `copy`. |
| 611 | `        return {'B1.csv': [b1(c, i, cr()) for c in (0, 2, 41, 94) for i in range(1, 5)],` | The session holds step B1 with 4 processes on each of the CPUs 0, 2, 41 and 94. The dictionary goes on in line 612. |
| 612 | `                'B3.csv': [b1(c, i, cr(), step='B3', binary=b) for b in ('bwx_o0', 'bwx_o36', 'bwx_o52') for c in (0, 2, 41, 94) for i in range(1, 5)]}` | Continues line 611: and step B3 with the three builds `bwx_o0`, `bwx_o36` and `bwx_o52`, each with the same 16 processes. |
| 613 | `    out = analyze({'s1': sess(58.0), 's2': sess(58.0)})` | Runs the analysis on two sessions with `copy` at 58.0 GB/s, the rate of `asmcopy`. So `d` is 0. |
| 614 | `    assert out['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'not resolved'` | Proves that B1 is `not resolved` for the label `low`. |
| 615 | `    assert out['hypotheses'][H6]['per_session'] == {'s1': 'not observed', 's2': 'not observed'} and out['hypotheses'][H6]['word'] == 'not observed'` | Proves that H6 is `not observed` in both sessions and over them. |
| 616 | `    # with a resolved difference in B1 that no build changes, the prediction of H6 fails in both sessions` | Comment: with a resolved difference in B1 that no build changes, the prediction of H6 fails in both sessions. |
| 617 | `    out = analyze({'s1': sess(56.0), 's2': sess(56.0)})` | Runs the analysis on two sessions with `copy` at 56.0 GB/s. So `d` is -2.0 GB/s in B1 and in every build. |
| 618 | `    assert out['sessions']['s1']['B1']['groups']['8M']['labels']['low']['decision'] == 'resolved'` | Proves that B1 is resolved. |
| 619 | `    assert out['hypotheses'][H6]['word'] == 'rejected'` | Proves that H6 is then `rejected`. |
| 622 | `def test_b5_metric_disagreement_is_not_yes():` | Starts the test `test_b5_metric_disagreement_is_not_yes`. |
| 623 | `    """WHY: "shows the pattern and total of old read" rejects the B5 statement. If M_hist resolves a total` | Docstring, the reason: the answer "shows the pattern and total of old read" rejects the statement of step B5. The docstring goes on in line 624. |
| 624 | `    difference and M_sum does not, the total of old read is not shown: the variant must not get "yes"."""` | Docstring: when `M_hist` resolves a total difference and `M_sum` does not, the total of old read is not shown. So the variant must not get `yes`. |
| 625 | `    def blk(i):` | Starts the inner function `blk`. It builds one process. |
| 626 | `        seq = B5SEQ if i % 2 else ','.join(reversed(B5SEQ.split(',')))` | `seq`: `B5SEQ` for an odd process number, and the reversed order for an even one. |
| 627 | `        rate = lambda r, pos, e, tid, cpu: (5.0 if cpu < 64 else 2.7) + (0.004 * i if e == 'asmread2' else 0)` | `rate`: every kernel has the split rates of old read, 5.0 and 2.7 GB/s. `asmread2` gets 0.004 GB/s more per thread times the process number. |
| 628 | `        late_pass = lambda r, pos, e, tid: 0.75 if e == 'oldread' and tid == 0 else None      # whole passes: one thread ends 0.25 s later` | `late_pass`: thread 0 gets an elapsed time of 0.75 s in the `oldread` interval. By the comment this imitates whole passes in which one thread ends 0.25 s later. |
| 629 | `        return block('B5', 'b5-p%d' % i, '%s --seq %s --rounds 1 --stop pass --min-ms 500 --start common' % (ALL, seq), rate, elapsed=late_pass)` | Calls `block` with the whole-pass stop, 500 ms and the common start. |
| 630 | `    files = {'B5.csv': [blk(i) for i in range(1, 5)]}` | `files`: 4 such processes. |
| 631 | `    out = analyze({'s1': files, 's2': files})` | Runs the analysis on two such sessions. |
| 632 | `    v = out['sessions']['s1']['B5']['variants']['read_sparse']` | `v`: the result of the variant `read_sparse`. |
| 633 | `    m = v['total_difference']['metrics']` | `m`: the decisions of its total difference per metric. |
| 634 | `    assert m['M_hist']['decision'] == 'resolved' and m['M_sum']['decision'] == 'not resolved' and v['same_pattern'] is True` | Proves the invented case: `M_hist` resolves the difference, `M_sum` does not, and the pattern is the same. |
| 635 | `    assert v['shows_pattern_and_total_of_oldread'] == 'not resolved' and 'M_hist gives' in v['note']` | Proves that the answer is `not resolved` and that the note quotes the disagreement. |
| 636 | `    assert out['hypotheses'][B5STMT]['per_session'] == {'s1': 'not resolved', 's2': 'not resolved'} and out['hypotheses'][B5STMT]['word'] == 'not rejected'` | Proves that the flag of the statement is `not resolved` in both sessions and that the word is `not rejected`. |

### Tests added after the review: one kernel per process, and the counter tables (lines 639 to 670)

| Line | Source | Explanation |
|---:|---|---|
| 639 | `def test_b7_single_kernel_uses_both_metrics():` | Starts the test `test_b7_single_kernel_uses_both_metrics`. |
| 640 | `    """WHY: handoff B.10 makes M_hist the decision metric "for the reproduction condition" too, and a different` | Docstring, the reason: section B.10 of the handoff note makes `M_hist` the decision metric for the reproduction condition too. The docstring goes on in line 641. |
| 641 | `    word under M_sum gives "not resolved". With whole passes one late thread changes M_hist and not M_sum."""` | Docstring: another word under `M_sum` gives `not resolved`. With whole passes one late thread changes `M_hist` and not `M_sum`. |
| 642 | `    blocks = []` | `blocks`: empty at first. |
| 643 | `    for k in ('oldread', 'read', 'asmread', 'asmread2'):` | Loop over the four kernels. |
| 644 | `        for i in range(1, 5):` | Loop over 4 processes per kernel. |
| 645 | `            rate = lambda r, pos, e, tid, cpu, i=i: 3.0 + 0.0001 * i` | `rate`: every thread runs at 3.0 GB/s plus 0.0001 GB/s times the process number. |
| 646 | `            el = (lambda r, pos, e, tid: 0.75 if tid == 0 else None) if k == 'read' else None` | `el`: only for the kernel `read`: thread 0 gets an elapsed time of 0.75 s. |
| 647 | `            blocks.append(block('B7', 'single-%s-p%d' % (k, i), '%s --seq %s --rounds 3 --stop pass --min-ms 500 --start common' % (ALL, k), rate, elapsed=el))` | Adds one process with one kernel, 3 rounds and the setting `pass/500/common`. |
| 648 | `    r = analyze({'s1': {'B7.csv': blocks}})['sessions']['s1']['B7']` | Runs the analysis and takes step B7. |
| 649 | `    sk = r['single_kernel']` | `sk`: the decision with one kernel per process. |
| 650 | `    assert sk['metrics']['M_hist']['decision'] == 'resolved' and sk['metrics']['M_sum']['decision'] == 'not resolved'` | Proves that `M_hist` resolves `D` and `M_sum` does not. |
| 651 | `    assert sk['decision'] == 'not resolved' and sk['sign'] is None and 'M_sum' in sk['note'] and near(sk['D'], 119.0, 0.1)` | Proves that the decision is `not resolved` without a sign, that the note names `M_sum`, and that `D` with `M_hist` is 119.0 GB/s (360 minus 241). |
| 652 | `    assert r['reproduced_in_either_way'] is False` | Proves that `D` then does not count as reproduced. |
| 655 | `def test_counter_tables_count_processes_and_keep_sequences_apart():` | Starts the test `test_counter_tables_count_processes_and_keep_sequences_apart`. |
| 656 | `    """WHY: the column "processes" of every table is the number of processes (plan, rule 4: one value per process),` | Docstring, the reason: the column `processes` of every table is the number of processes (rule 4 of the plan: one value per process). The docstring goes on in line 657. |
| 657 | `    and the rows of the B7 sequence and of the B5 sequence of C3 are different experiments."""` | Docstring: and the rows of the B7 sequence and of the B5 sequence of step C3 are different experiments. |
| 658 | `    counts = lambda r, pos, entry, tid, nbytes: '300000000,300000000,299000000,%d,%d,%d,%d,%d' % (897000000, nbytes * 11 // 256, nbytes // 64, 0, nbytes // 640)` | `counts`: the fields of a `C` row: an enabled time and a running time of 300000000 ns each, a CPU time of 299000000 ns, and five counts. The fourth count is 0. |
| 659 | `    one = [block('C1', 'cpu2-p%d' % i, '--threads 1 --cpus 2 --bytes 32K --seq asmread --rounds 3 --min-ms 100 --stop pass --count', lambda *a: 60.0, counts=counts) for i in (1, 2)]` | `one`: 2 processes of step C1 on CPU 2, with 32 KiB, 3 rounds and `--count`. |
| 660 | `    r = analyze({'s1': {'C1.csv': one}})['sessions']['s1']['C1']` | Runs the analysis and takes step C1. |
| 661 | `    assert len(r['groups']) == 1 and r['groups'][0]['n_rows'] == 6 and r['groups'][0]['n_processes'] == 2` | Proves one group with 6 `C` rows from 2 processes. |
| 662 | `    assert r['rows'][0]['n_processes'] == 2 and '6 C rows' in r['rows'][0]['note']` | Proves that the table line holds 2 as its number of processes and names the 6 `C` rows in its note. |
| 663 | `    opts = '--rounds 1 --stop common --min-ms 6000 --start common --count'` | `opts`: the options of the two processes of step C3: 1 round, the setting `common/6000/common` and `--count`. |
| 664 | `    c3 = [block('C3', 'common-6000-common-p1', '%s --seq %s %s' % (ALL, B7SEQ, opts), lambda *a: 2.5, counts=counts),` | `c3`: one process with the sequence of B7. The list goes on in line 665. |
| 665 | `          block('C3', 'b5-fwd-p1', '%s --seq %s %s' % (ALL, B5SEQ, opts), lambda *a: 2.5, counts=counts)]` | Continues line 664: and one process with the sequence of B5, in the same setting. |
| 666 | `    g = analyze({'s1': {'C3.csv': c3}})['sessions']['s1']['C3']['groups']` | Runs the analysis and takes the groups of step C3. |
| 667 | `    old = {x['group']: (x['n_rows'], x['n_processes']) for x in g if x['entry'] == 'oldread' and x['mesh'] == 'mesh0'}` | `old`: the number of rows and the number of processes of the groups of `oldread` on mesh 0, by group name. |
| 668 | `    assert old == {'common/6000/common B7 sequence': (128, 1), 'common/6000/common B5 sequence': (64, 1)}, old` | Proves two separate groups: the B7 sequence with 128 rows (64 threads times 2 intervals of `oldread`) and the B5 sequence with 64 rows, each from 1 process. |

### Function `main`: all tests, in the order of their names (lines 671 to 683)

| Line | Source | Explanation |
|---:|---|---|
| 671 | `def main():` | Starts the function `main` of the test file. |
| 672 | `    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]` | `tests`: all objects of this file whose names start with `test_`, in the alphabetical order of their names. This is not the order of the file. |
| 673 | `    try:` | Starts a block. Line 677 runs after it in every case. |
| 674 | `        for t in tests:` | Loop over the tests. |
| 675 | `            t()` | Runs the test. A check that fails stops the test, and the run, with an error. |
| 676 | `            print('ok   %s' % t.__name__)` | Prints `ok` and the name of the test. |
| 677 | `    finally:` | In every case, also after a failed check. |
| 678 | `        shutil.rmtree(TMP, ignore_errors=True)` | Deletes the temporary folder with all its files. |
| 679 | `    print('test_analyze_bwx.py: all %d tests passed' % len(tests))` | Prints that all tests passed, with their number. This line is reached only when no check failed. |
| 682 | `if __name__ == '__main__':` | True only when the file is started as a program. |
| 683 | `    main()` | Runs `main`. |

## References

- [Ref1] The handoff note: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Rule 4 of the rules for the machine: the system load is reported in every result. Section B.3: the fields of the `I`, `T`, `P` and `C` rows. Section B.6: the first page reading of a process with many threads has the position -1. Section B.9: the sequence and the options of each step. Section B.10: the decision rules.
- [Ref2] The plan: the file `tests/2026-11-13-new-read-kernel/report/plan.md` of the same repo. The table of the hypotheses, the rules 4, 5, 10 and 11, and step B7 with its reproduction condition.
- [Ref3] The deviations note: the file `code/bwx-2026-11-13/DEVIATIONS-scripts.md` of the same repo. Table "Analysis": the points A1 to A33. Section "What the tests cover": the number of tests, and the trial with 16 changed copies of the analysis.
