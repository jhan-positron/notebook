# `check_accept8.py` explained, line by line

- Source file: `bwx8-2026-11-14/check_accept8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 33 lines, 1982 bytes).
- sha256 of the source when this page was built: `2f2fe8085bc4f795d5583d3b2b5153916f3a319be23c15d2f91986aba5d772cf`.

## Short version: purpose

`check_accept8.py` checks the output of a trace run of the runner `bwx8` on CRB, as a part of the acceptance of that runner. For every trial of a plan file it applies three rules of `test_runner8.py` and three checks of its own, and it prints one line per trial with the rates of the target windows. Its exit status is 0 only when no check found a problem.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Design**: the file `tackle-8mb.md`, the design of the investigation into the buffer size of 8 MiB. Its Stage 1 lists the acceptance checks that the runner must pass before measurements [Ref1].
- **Decisions note**: the file `DECISIONS-bwx8.md` in the folder of this script. It fixes the plan file, the options and the output rows of `bwx8` [Ref2].
- **Trial mode, trial**: a mode of `bwx8` with one worker thread. A trial is one timed sequence of windows that one line of a plan file describes.
- **Plan file**: a text file that `bwx8` reads. Its first three lines are header lines. Every other line gives one trial in 11 fields that are divided by single spaces: `trial`, `cond`, `rep`, `prev`, `pfx`, `pred`, `tgt`, `nwin`, `win_ms`, `count` and `bins`.
- **Window**: one timed stretch of one kernel inside a trial. It runs whole passes over its range and ends at the first clock read at or after its requested duration.
- **Phase**: the role of a window in a trial: `prev` (previous activity), `prefix`, `pred` (predecessor) or `target`.
- **Target window**: a window of the phase `target`. Only the rates of target windows are printed here.
- **Timed sequence**: all windows of one trial, from the start of the first to the end of the last. No page reading, output or allocation lies inside it.
- **Gap**: the time between the clock read that ends one window and the clock read that starts the next.
- **Bin**: a record inside a target window: at a clock read about every 10 ms the worker stores the time and the bytes so far.
- **Counter mode**: the field `count` of a plan line: `closed`, `open` or `read`. With `read` the worker reads hardware counters at the borders of the target windows.
- **Trace run**: a run of `bwx8` with the option `--trace`. The runner then logs every event of its wrapper code in memory and prints the log as `TR` rows. The rates of a trace run are not used as results [Ref2].
- **`M`, `P`, `W`, `B`, `E`, `X`, `TR` rows**: the row kinds of the trial mode. `M`: one value that describes the process. `P`: the page state before or after a trial. `W`: one window with its bytes and its two times. `B`: one bin. `E`: the summary of a trial. `X`: a failure that the runner reports. `TR`: one event of the trace.
- **Worker thread, controlling thread**: the worker thread runs the kernels on its own CPU. The controlling thread starts it and waits on another CPU.
- **Minor page fault**: an access to a memory page that Linux first has to map, without reading from a disk.
- **Context switch**: Linux takes the CPU from a thread. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU from a thread that still wants to run.
- **`sink_ok`**: a field of the `E` row. It is 1 when the last old read of the trial left the sum of its range in the variable that takes the result, 0 when not, and `NA` when the trial ran no old read.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.

## Main flow

1. The script imports the rule functions of `test_runner8.py` (lines 6 to 7).
2. For each pair of a csv file and a plan file it reads the rows of the csv file by kind, the trials of the plan file, and the `minflt` lines, and it prints one heading (lines 10 to 15).
3. For each trial it applies the trace rule and the window rule, and the bin rule when the plan asks for bins (lines 16 to 21).
4. It adds its own checks: the `TR` rows are numbered in order, the timed sequence had 0 minor page faults, and the buffer lies fully on huge pages before and after the trial (lines 22 to 25).
5. It prints one line for the trial with the rates of the target windows, fields of the `E` row, the `X` rows and the problems (lines 26 to 31).
6. It prints the total number of problems and sets the exit status (lines 32 to 33).

## Behavior a reader must know

- The script reads files and measures nothing. The rates that it prints come from the `W` rows: bytes divided by the time between the two clock reads of the window (line 28).
- The rules themselves are in `test_runner8.py`. This script only applies them to files from CRB. In that test file each rule is also run on changed rows, where it must report a problem [Ref3].
- An `X` row is printed and not counted as a problem (line 26, line 30).
- The coverage check expects 8192 kB, so it fits a buffer of 8 MiB only (line 25).
- A csv file of a run without `--trace` has no `minflt` lines. Every trial of it gets a problem (line 23).
- Three cases end the script with a Python error and no result line: a file that cannot be read, a trial without an `E` row (line 18), and a trial that does not have exactly two `P` rows (line 24).
- Without arguments the script prints 0 problems and ends with exit status 0. A last csv file without a plan file is skipped (line 10).
- The decisions note records the use of this script on 2026-11-15: the trace runs of two result folders, 18 trials on the CPUs 2 and 41, 0 problems [Ref2].

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/check_accept8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (33 lines, 1982 bytes, sha256 `2f2fe8085bc4f795d5583d3b2b5153916f3a319be23c15d2f91986aba5d772cf`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_accept8.py - Stage 1 items 1 and 4 on the output of a --trace run of bwx8 on CRB.` | Starts the docstring of the file. It ends in line 5. The script covers the items 1 and 4 of Stage 1 on the output of a run of the runner `bwx8` with `--trace` on CRB. Stage 1 is the list of acceptance checks of the design. Item 1 is the check of the code and of the accounting. Item 4 is the check, with a trace, that no warm-up pass, page reading, output, counter read or barrier lies on the path from the predecessor window to the target windows of a trial that reads no counters [Ref1]. |
| 3 | `Usage: check_accept8.py <csv> <plan> [<csv> <plan> ...]` | Docstring: the usage. The arguments come in pairs: a csv file with the output of one `bwx8` process, and the plan file that this process ran. |
| 4 | `Applies the trace, window and bin rules of test_runner8.py to every trial, and prints the rates and gaps.` | Docstring: the script applies the trace rule, the window rule and the bin rule of `test_runner8.py` to every trial, and it prints the rates and the gaps. |
| 5 | `Exit status 0 only if no rule reports a problem."""` | Docstring: the exit status is 0 only if no rule reports a problem. The docstring ends here. |
| 6 | `import re, sys` | Loads two modules of the Python standard library: `re` for regular expressions, and `sys` for the arguments and the exit of the script. |
| 7 | `import test_runner8 as T` | Imports the test file `test_runner8.py` as the module `T`. The import defines the rule functions of that file and runs none of its tests. Python must find the file, for example in the folder of this script. |
| 9 | `bad = 0` | `bad`: the number of problems over all files, 0 at first. |
| 10 | `for csv, plan in zip(sys.argv[1::2], sys.argv[2::2]):` | Loop over the pairs of arguments. `csv` takes the arguments 1, 3, 5 and so on. `plan` takes the arguments 2, 4, 6 and so on. A last csv file without a plan file is skipped without a message. |
| 11 | `    out = open(csv).read()` | `out`: the whole text of the csv file. |
| 12 | `    rows, lines = T.rows_of(out), T.plan_lines(plan)` | `rows`: the rows of the file by kind. `T.rows_of` splits every line that is not empty and does not start with `#` at the commas, and stores it under its first field. `lines`: the trials of the plan file. `T.plan_lines` drops the first three lines of the file, which are header lines, and splits every other line at single spaces [Ref3]. |
| 13 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary from key to value. An `M` row has the form `M,key,value` and describes the process. |
| 14 | `    print("== %s cpu %s ctl %s madvise_ok %s kernels %s" % (csv.split("/")[-1], m.get("cpu"), m.get("ctl_cpu"), m.get("madvise_ok"), m.get("kernels")))` | Prints a heading for the file: its name without the folder, the CPU of the worker thread (`cpu`), the CPU of the controlling thread (`ctl_cpu`), `madvise_ok` (1 when the request for the page policy worked) and `kernels` (`aarch64`, or `STAND-IN` for a build whose read kernels are plain C loops) [Ref2]. |
| 15 | `    faults = dict(re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M))` | `faults`: per trial, the number of minor page faults of the worker thread in the timed sequence. The pattern finds the comment lines of the form `# minflt,0,0` that a trace run prints after each trial. Group 1 is the trial number. Group 2 is the count, which may have a minus sign. `re.M` lets the pattern match at every line of the text. |
| 16 | `    for i, f in enumerate(lines):` | Loop over the trials of the plan. `i` is the trial number, counted from 0. `f` holds the fields of its plan line. |
| 17 | `        ev, numbered = T.events_of(rows, i)` | `ev`: the events of the trace of this trial, as pairs of an event name and a time in ns. `T.events_of` reads them from the `TR` rows. `numbered`: true when the `TR` rows have the numbers 0, 1, 2 and so on without a gap. |
| 18 | `        w, e = T.of_trial(rows, "W", i), T.of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial, one per window. `e`: its `E` row, the summary row of the trial. A trial without an `E` row ends the script here with a Python error. |
| 19 | `        p = T.trace_problems(f, ev, w, e) + T.window_problems(f, w)` | `p`: the problems of the trial from two rules. `T.trace_problems` compares the trace with the plan line. Every planned window must start directly after a clock read and hold only its first kernel call and clock reads. It must end at the first clock read at or after its requested duration. Between two windows only the reads that the plan allows may lie. The times of the `W` rows and the gap of the `E` row must be clock reads of the trace. `T.window_problems` compares the `W` rows with the plan line: phase, number, kernel and pass size of each window, a byte count of whole passes, a duration of at least the requested time, and times that never go back [Ref3]. |
| 20 | `        if int(f[10]):` | Only when the plan line asks for bins: its field 11, `bins`, is not 0. |
| 21 | `            p += T.bin_problems(f, w, T.of_trial(rows, "B", i), {t for n, t in ev if n == "clock"})` | Adds the problems of the bin rule. `T.bin_problems` gets the `B` rows of the trial and the set of the times of all clock reads of the trace. It tests that the bins of each target window are numbered from 0, that their end times rise to the end of the window, that their bytes sum to the bytes of the window in whole passes, and that every bin end is a clock read of the trace [Ref3]. |
| 22 | `        if not numbered: p.append("TR rows not numbered")` | Adds a problem when the `TR` rows are not numbered in order. |
| 23 | `        if faults.get(str(i)) != "0": p.append("minflt %s" % faults.get(str(i)))` | Adds a problem unless the count of minor page faults of the trial is exactly 0. A missing `minflt` line gives a problem too. By a comment in the source of the runner, a count above 0 means that a page was first touched inside the timed sequence [Ref4]. |
| 24 | `        pre, post = [x for x in T.of_trial(rows, "P", i)]` | `pre` and `post`: the two `P` rows of the trial: the page state before the timed sequence and after it. Any other number of `P` rows ends the script with a Python error. |
| 25 | `        if pre[3:5] != ["8192", "8192"] or post[3:5] != ["8192", "8192"]: p.append("huge-page coverage %s %s" % (pre[3:5], post[3:5]))` | Adds a problem unless `kB_total` and `kB_huge` (the fields 4 and 5) are both 8192 in both rows. So the buffer of 8 MiB must lie fully on huge pages before and after the trial. This check fits a buffer of 8 MiB only. |
| 26 | `        x = T.of_trial(rows, "X", i)` | `x`: the `X` rows of the trial: failures that the runner reported itself. |
| 27 | `        tg = [r for r in w if r[2] == "target"]` | `tg`: the `W` rows of the target windows. |
| 28 | `        rates = ["%.2f" % (int(r[6]) / (int(r[8]) - int(r[7]))) for r in tg]` | `rates`: the rate of each target window in GB/s, with 2 decimals: the column `bytes` (field 7) divided by the time from `t_start_ns` (field 8) to `t_end_ns` (field 9). Bytes per ns are GB/s. The two times are clock reads of the worker thread at the start and at the end of the window [Ref2]. |
| 29 | `        print("trial %d %-28s count %-6s target GB/s %s \| wall %s cpu %s nvcsw %s nivcsw %s gap_ns %s max_gap %s sink %s state %s%s%s"` | Prints one line per trial: the trial number, the condition label, the counter mode, the rates of the target windows, and eight fields of the `E` row. This source line holds the text of the line. Its values follow in line 30. |
| 30 | `              % (i, f[1], f[9], " ".join(rates), e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9], " X=%s" % x if x else "", " PROBLEM %s" % p if p else ""))` | Continues line 29: the values. From the plan line: the condition (field 2) and the counter mode (field 10). From the `E` row: the wall time and the CPU time of the timed sequence in ns, the voluntary and the involuntary context switches, `gap_ns` (the gap before the first target window), the largest gap between two windows, `sink_ok` and the counter state. Then come the `X` rows when the trial has some, and the word `PROBLEM` with the list of the problems when there is one. |
| 31 | `        bad += len(p)` | Adds the number of problems of the trial to `bad`. |
| 32 | `print("# problems: %d" % bad)` | Prints the total number of problems. |
| 33 | `sys.exit(1 if bad else 0)` | Ends the script with exit status 1 when a problem was found, and with 0 when none was found. |

## References

- [Ref1] The design: the file `tests/2026-11-15-tackle-8mb/report/tackle-8mb.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`, section "Stage 1: establish that the runner can measure the effect", item 1 "Code and accounting" and item 4 "Transition fidelity", and section "One trial".
- [Ref2] The decisions note: the file `code/bwx8-2026-11-14/DECISIONS-bwx8.md` of the same repo. Section "Plan file": the fields of a plan line. Section "bwx8 command line": the option `--trace`, the rules of the timed sequence and the table of the output rows. Section "Changes after the review round": the line `# minflt`. Section "CRB acceptance, 2026-11-15": the trace runs that were checked with this script.
- [Ref3] The file `code/bwx8-2026-11-14/test_runner8.py` of the same repo: its header text, and the functions `rows_of`, `of_trial`, `plan_lines`, `events_of`, `expected_windows`, `window_problems`, `bin_problems` and `trace_problems`.
- [Ref4] The source of the runner: the file `code/bwx8-2026-11-14/bwx8.c` of the same repo. Its function `emit_trial` prints the rows of one trial and the line `# minflt`, with the comment on its meaning. The worker prints the comment lines with the column names of each row kind.
