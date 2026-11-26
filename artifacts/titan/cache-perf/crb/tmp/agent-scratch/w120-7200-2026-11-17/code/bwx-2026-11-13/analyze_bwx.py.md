# `analyze_bwx.py` explained, line by line

- Source file: `bwx-2026-11-13/analyze_bwx.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1104 lines, 67196 bytes).
- sha256 of the source when this page was built: `b09ba29ad63cb5e3134724287802f6eb46374d3a29a9dbc614d1ffbd63b894e3`.

## Short version: purpose

`analyze_bwx.py` reads the result files that the runner `bwx` wrote in Parts B and C of the test plan of 2026-11-13. For each step and each session it computes rates and differences from the rows of the threads, and it applies the decision rules of the handoff note, most of them through the functions of `decide.py`. It prints one text table per step and one word per hypothesis of the plan, and with `--out` it also writes these texts and a summary in JSON to a folder.

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
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D [Ref2].
- **Parts B and C**: two parts of the plan. Part B holds the deciding measurements with the runner `bwx`. Part C repeats some of them with counters. They are not the parts of the later rerun.
- **Handoff note**: the file `handoff.md`. It tells how to execute the plan. Its section B.3 gives the rows of the result files, and its section B.10 gives the decision rules in words [Ref1].
- **Deviations note**: the file `DEVIATIONS-scripts.md` in the folder of this script. Its points A1 to A33 say where the analysis adds to the handoff note or differs from it [Ref3].
- **`decide.py`**: the file that holds the decision rules of section B.10 as Python functions [Ref4].
- **Local rule**: a decision rule that is coded in this file, where `decide.py` has no function for it.
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
- **Pattern: split, uniform, between**: the label of an interval with many threads. Split is a `q` below 0.65, uniform is a `q` above 0.85, and between is the rest. The two limits are provisional.
- **A/A pair**: one loop that exists in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A difference**: the difference between the rates of the two copies of an A/A pair. It shows how much two equal loops differ.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high, changing**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, high is above 70.5 GB/s, and changing is every rate from 69 to 70.5 GB/s. The two limits are provisional.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair value**: the rate of one kernel minus the rate of the other in two neighbouring intervals, in GB/s.
- **Process value, `d`, `e`**: one number per process. In a step with one thread, `d` is the median of the pair values of the kernel comparison, and `e` is the median of the pair values of the A/A comparison.
- **`D`, `E`**: the two process values of a step with many threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Setting**: one combination of the timing options of a step with many threads: the stop method, the interval length in ms and the start method, written as in `pass/500/common`.
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision, or for an event that did not occur.
- **Hypothesis, H1 to H11**: a possible explanation that the plan names, with a label such as H4. Each one makes a bounded prediction that one step tests [Ref2]. The rows of the function `cross` give the prediction of each hypothesis that this script handles.
- **Flag of a session**: the result of one session for one hypothesis: `fail` (the prediction failed), `hold`, `not observed` or `not resolved`.
- **Copy difference**: what question Q1b of the plan asks about: with one thread and a buffer of 8 MiB, a lower rate of the new C copy kernel than of the assembly copy kernel [Ref2].
- **Read difference**: what question Q2a of the plan asks about: with 120 threads, a higher total rate of the old read kernel than of the new read kernel [Ref2].
- **Late thread**: a thread whose `T` row has the flag `late`. With the common stop it started more than 100 us after the planned common start.
- **End skew**: the latest end time of a thread minus the earliest end time, inside one interval.
- **Irregular interval**: an interval with a late thread, or, with the common stop, with an end skew above 5 ms. It is listed and not used for a decision.
- **Coverage: full, none, partial, unknown**: the share of a buffer that lies on huge pages, read from a `P` row.
- **Bracket**: in step B8, the two counts of mesh-1 threads between which the pattern of a kernel changes from split to uniform.
- **Spread of a kernel**: in step B10, the highest minus the lowest `M_hist` of the intervals of one kernel in one process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the spread, one for the total rate and one for the rate of each mesh.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.
- **JSON**: a text format for nested lists and dictionaries.

## Main flow

1. The script finds and imports `decide.py`, and it sets its constants: the CPUs of mesh 0, the limits for an irregular interval and for the pattern labels, and the regular expression for a header line (lines 22 to 40).
2. `main` reads the options: one or more `--session` with a name and paths, and `--out` (lines 1075 to 1083).
3. For each session `load_session` reads every csv file. `read_csv` makes one `Proc` per header line and passes every data row to it (lines 194 to 223, lines 95 to 167).
4. At the end of a file each `Proc` computes the values of its intervals from the `T` rows: the rate of each thread, `M_hist`, `M_sum`, the values per mesh, the end skew, `q` and the pattern. Then it decides whether the process is complete (lines 63 to 89, lines 169 to 185).
5. `analyze` takes the steps of a session in a fixed order and calls the analysis function of each step. Each function first lists the processes used and left out, the irregular intervals and the load (lines 1011 to 1030, lines 849 to 851, lines 237 to 252).
6. Steps with one thread: B1, B2 and B3 compare a copy kernel with `asmcopy` per CPU, B6 compares the old read kernel between levels and between sizes, and B4 counts intervals per level and coverage (lines 327 to 440).
7. Steps with many threads: B7 decides the difference `D` between old read and new read per setting and its change between settings, B10 does the same for the spread of the write kernels and tests H11, B8 builds brackets, and B5 and B9 compare patterns and totals (lines 445 to 784).
8. The steps C1 to C3 get a description of the counter rows, and the step SHORT gets one line per process. Neither gets a decision (lines 789 to 846).
9. `cross` joins the results of all sessions into one word per hypothesis (lines 856 to 1003, line 1031).
10. `main` builds the text tables, writes them and `summary.json` to the folder of `--out` when it is given, and prints all texts (lines 1085 to 1100).

## Behavior a reader must know

- Every rate comes from the `T` rows: the column `bytes` (field 7) divided by the column `elapsed_s` (field 8) and by 1e9, in GB/s. The values of the `I` rows are stored and never used (lines 137 to 138).
- The script reads no clock and times nothing. The time of a thread is the elapsed time that the runner printed.
- `M_hist` divides the bytes of all threads by the longest elapsed time of one thread. `M_sum` adds the rates of the threads. The two differ when the threads have different elapsed times, which the whole-pass stop allows.
- No value is the rate of the time in which all threads ran. The output says so in its list of limits (line 1014).
- A process gives values only when it is complete: no `-- killed` or `-- failed` line, no problem, and every expected interval with one `T` row per thread (line 181).
- An irregular interval is listed. A process gives no value for a quantity that needs such an interval (lines 458 to 460).
- With `--stop pass` an end skew never makes an interval irregular (line 86). The deviations note marks this as a point that needs a decision of the lead [Ref3].
- Where a decision rule uses process values, a process gives one value, however many intervals it has. This holds for the steps B1, B2, B3, B6, B7 and B10 and for the totals of B5 and B9. Step B4 counts single intervals (line 420), and the pattern labels of B8, B5 and B9 are given per interval. In the steps with one thread, values of different CPUs are never put into one group.
- The decision metric is `M_hist`. When `M_sum` gives another word or another sign for `D`, the result is `not resolved` (lines 480 to 486). For a change of `D` between two settings only the words are compared: those records hold no sign (line 543).
- The limits 69 and 70.5 GB/s (level), 0.65 and 0.85 (pattern), 100 us and 5 ms (irregular interval) are provisional. The output says so (line 1016).
- By a decision of the user the pattern labels are not used [Ref5]. The script still computes them. The entries for H8, H9a and the statement of step B5 hold a second word without labels (lines 1006 to 1008).
- The names of the five counts of a `C` row are assigned by position (line 789, line 813).
- The docstring of `a_copy` names step C2, but the table of lines 849 to 850 gives C2 to `a_count`.
- The script ends with a Python error when a header line does not fit the pattern, when a folder holds no csv file, or when `decide.py` is not found. A wrong command line gives exit status 2. A normal end gives exit status 0.
- In the code repo `decide.py` lies in the folder `new-test-kernel` beside the folder of this file. That is none of the three places of line 26 unless `DECIDE_DIR` names it. So in the repo layout the import needs `DECIDE_DIR`.

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/analyze_bwx.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1104 lines, 67196 bytes, sha256 `b09ba29ad63cb5e3134724287802f6eb46374d3a29a9dbc614d1ffbd63b894e3`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: usage, terms and the source of the rules (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""analyze_bwx.py - analysis of the bwx runs of Parts B and C (handoff.md, sections B.3 and B.10).` | Starts the docstring of the file. It ends in line 21. This line names the task: the analysis of the runs of the runner `bwx` in Parts B and C of the plan. It names two sections of the handoff note `handoff.md`: B.3 gives the format of the result rows, and B.10 gives the decision rules. |
| 4 | `Usage:` | Docstring: starts the usage text. |
| 5 | `  analyze_bwx.py --session NAME PATH [PATH...] [--session NAME PATH...] [--out DIR]` | Docstring: the form of the call. Each `--session` takes a name and one or more paths. The option may be given several times. `--out DIR` may be left out. |
| 6 | `    PATH is a result folder of run_bwx.sh (all its *.csv files are read) or one csv file.` | Docstring: a path is a result folder of the run script `run_bwx.sh` or one csv file. Of a folder the script reads every file whose name ends with `.csv`. |
| 7 | `    NAME names the session (one visit plan run once; the plan asks for 2 sessions some hours apart).` | Docstring: the name is the label of one session. A session is one run of the visit plan. The plan asks for 2 sessions some hours apart. |
| 8 | `    Without --out the text tables go to standard output. With --out DIR the script writes` | Docstring: without `--out` the text tables go to the standard output only. The sentence about `--out DIR` goes on in line 9. |
| 9 | `    DIR/summary.json and DIR/<step>.txt, and prints the tables too.` | Docstring: with `--out DIR` the script writes the file `summary.json` and one text file per step into the folder `DIR`. It still prints the tables. |
| 11 | `Words: a "process" is one start of bwx (one "-- step ..." header line in a csv file). An "interval" is one` | Docstring: two terms. A process is one start of `bwx`. In a csv file it begins at a header line that starts with `-- step`. The definition of an interval goes on in line 12. |
| 12 | `timed entry of the sequence. M_hist = (sum of the bytes of all threads) / (longest elapsed time of a thread).` | Docstring: an interval is one timed entry of the sequence. `M_hist` is the sum of the bytes of all threads, divided by the longest elapsed time of a thread. |
| 13 | `M_sum = sum over the threads of (bytes / elapsed time). Rates are in GB/s (1 GB = 1e9 bytes).` | Docstring: `M_sum` is the sum over the threads of the rate of each thread: its bytes divided by its own elapsed time. All rates are in GB/s, and 1 GB is 1e9 bytes. |
| 14 | `q = rate of the thread at the 10th percentile / rate of the thread at the 90th percentile.` | Docstring: `q` is the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile. The code sorts the threads of one interval by their rate for this (line 72, line 88). |
| 15 | `A/A spread = the largest absolute difference between two copies of one loop, over the processes of a group.` | Docstring: the A/A spread is the largest absolute difference between two copies of one loop, taken over the processes of a group. |
| 17 | `The decision rules are the functions of decide.py (new-test-kernel/decide.py). This file imports them.` | Docstring: the decision rules are the functions of the file `decide.py` in the folder `new-test-kernel`. This script imports them (line 30). |
| 18 | `Rules for which decide.py has no function are marked "local rule" below and listed in DEVIATIONS-scripts.md.` | Docstring: a rule that has no function in `decide.py` is coded in this file and marked "local rule". The deviations note `DEVIATIONS-scripts.md` lists these rules. The file marks two functions this way: `single_kernel` (line 561) and `a_b9` (line 751). The cases of step B4, the bracket of step B8 and the words over two sessions are also coded in this file without a function of `decide.py`, and they have no such mark. |
| 19 | `No rule is adapted to the data: where a definition does not fit, the result is "not observed" or` | Docstring: no rule is changed to fit the data. Where a definition does not fit, the result is the word "not observed" or the word of line 20. |
| 20 | `"not resolved", with the reason.` | Docstring: the word "not resolved", with the reason. |
| 21 | `"""` | Ends the docstring. |

### Imports, the search for `decide.py`, and the constants (lines 22 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `import argparse, glob, json, math, os, re, sys` | Loads seven modules of the Python standard library. `argparse` reads the command line. `glob` finds files by a name pattern. `json` writes JSON. `math` gives `ceil`, which rounds up. `os` builds paths and makes folders. `re` holds regular expressions. `sys` gives the module search path, the standard output and the exit of the script. |
| 23 | `from statistics import median, mean` | Takes `median` and `mean` from the module `statistics`. For an even count of values `median` returns the mean of the two middle values. |
| 25 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this file. |
| 26 | `for _d in (os.environ.get('DECIDE_DIR'), HERE, os.path.join(HERE, '..', '..', '..', 'new-test-kernel')):` | Loop over three folders in which `decide.py` may lie. The first is the folder that the environment variable `DECIDE_DIR` names. This value is `None` when the variable is not set. The second is the folder of this file. The third is the folder `new-test-kernel` inside the folder that lies three levels above the folder of this file. |
| 27 | `    if _d and os.path.exists(os.path.join(_d, 'decide.py')):` | Tests whether the folder is named and holds a file `decide.py`. |
| 28 | `        sys.path.insert(0, _d)` | Puts this folder at the front of the module search path of Python. |
| 29 | `        break` | Ends the loop of line 26 at the first folder that fits. |
| 30 | `import decide  # noqa: E402` | Imports `decide.py`. When none of the three folders held it, the search path is unchanged. This line then stops the script with an error, unless Python finds a `decide.py` in another folder of its path. The comment `noqa: E402` tells a style checker to accept an import that does not stand at the top of the file. |
| 32 | `MIB = 1 << 20` | `MIB`: 1048576, the number of bytes in 1 MiB. `1 << 20` shifts the number 1 left by 20 bits. |
| 33 | `MESH0_CPUS = range(0, 64)                 # mesh 0 = CPUs 0-63, mesh 1 = CPUs 64-119 (handoff, machine table)` | `MESH0_CPUS`: the CPU numbers 0 to 63, the CPUs of mesh 0. The code counts every other CPU as mesh 1 (line 74). The comment gives mesh 1 as the CPUs 64 to 119: mesh 1 holds the CPUs 64 to 127, and the runs use no CPU above 119. The comment names the machine table of the handoff note as its source. |
| 34 | `LATE_SKEW_S = 0.005                       # end skew above 5 ms makes an interval irregular (B.4, provisional)` | `LATE_SKEW_S`: 0.005 s (5 ms). An interval with the common stop whose threads end more than 5 ms apart is irregular (line 86). The comment names section B.4 of the handoff note and calls the limit provisional. |
| 35 | `Q_SPLIT, Q_UNIFORM = 0.65, 0.85           # pattern limits (handoff, Part A, rule 3, provisional)` | `Q_SPLIT` is 0.65 and `Q_UNIFORM` is 0.85: the two limits of the pattern label (line 89). They are ratios without a unit. The comment names rule 3 of Part A in the handoff note and calls the limits provisional. |
| 36 | `B4_MIN_INTERVALS = 10                     # B4: at least 10 low and 10 high intervals` | `B4_MIN_INTERVALS`: 10. In step B4 a case needs at least 10 low intervals and at least 10 high intervals (line 430). |
| 37 | `REF = 'asmread'                           # the reference kernel of the one-thread sequences` | `REF`: the name `asmread`. In the sequences with one thread the intervals of this kernel are the reference intervals. |
| 38 | `FLAG_OPTS = {'--no-thp', '--two-buffers', '--count'}` | `FLAG_OPTS`: the three options of the runner that take no value. `--no-thp` asks Linux to use no huge pages for the buffers. `--two-buffers` gives each thread a second buffer. `--count` reads counters around every interval [Ref1]. |
| 39 | `HEAD = re.compile(r'^-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\S+) '` | `HEAD`: a compiled pattern for the header line of a process. Its 11 groups hold, in order: the step, the tag, the binary, the wait in seconds (`waited_s`), the four fields of the load record, the number of logins, the UTC time and the arguments of the runner. The four load fields are the load averages over 1, 5 and 15 minutes, and a text such as `1/1083` with the runnable tasks and all tasks. `\S+` matches a run of characters without a space. The function `one` of `run_bwx.sh` writes this line directly before it starts the runner [Ref7]. |
| 40 | `                  r'logins (\S+) utc (\S+) args ?(.*)$')` | Continues the pattern of line 39: the groups 9 to 11. `args ?(.*)` takes the rest of the line as group 11. The space after `args` may be missing, so a header line without arguments fits too. |

### Functions `parse_size` and `size_name`: size texts (lines 43 to 53)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `def parse_size(s):` | Starts the function `parse_size`. It turns a size text such as `8M` into a number of bytes. |
| 44 | `    m = re.fullmatch(r'(\d+)([KMG]?)', s)` | Tests the whole text against a pattern: one or more digits (group 1), then at most one of the letters `K`, `M` and `G` (group 2, empty without a letter). |
| 45 | `    if not m:` | Tests whether the text did not fit. |
| 46 | `        raise ValueError('bad size ' + s)` | Then the function stops with the error `bad size` and the text. |
| 47 | `    return int(m.group(1)) << {'': 0, 'K': 10, 'M': 20, 'G': 30}[m.group(2)]` | Returns the digits as a number, shifted left by 0, 10, 20 or 30 bits. This multiplies by 1, by 1024, by 1048576 or by 1073741824. So `8M` gives 8388608 bytes (8 MiB). |
| 50 | `def size_name(n):` | Starts the function `size_name`. It turns a number of bytes into a short text for the labels of the tables. |
| 51 | `    return '%dM' % (n // MIB) if n % MIB == 0 else '%dK' % (n // 1024) if n % 1024 == 0 else str(n)` | A whole number of MiB gives a text such as `8M`. If not, a whole multiple of 1024 bytes gives a text such as `32K`. Every other number is printed as it is. |

### Class `Interval`: the rates and labels of one timed interval (lines 54 to 91)

| Line | Source | Explanation |
|---:|---|---|
| 54 | `# ---------------------------------------------------------------- parsing` | Comment: a divider. The part of the file that reads the result files starts here. |
| 56 | `class Interval:` | Starts the class `Interval`. One object holds one timed interval of one process. |
| 57 | `    """One timed interval of one process, from its T rows."""` | Docstring of the class: the values of an interval come from its `T` rows. A `T` row holds the bytes and the times of one thread in one interval. |
| 59 | `    def __init__(self, rnd, pos, entry):` | Starts the function that makes a new object. `rnd` is the round as the runner printed it. `pos` is the position in the sequence. `entry` is the entry of the sequence at this position. |
| 60 | `        self.round, self.pos, self.entry = rnd, pos, entry` | Stores the three values. |
| 61 | `        self.rows, self.irow, self.problem = [], None, None` | `rows`: the `T` rows of the interval, empty at first. `irow`: the values of its `I` row, or `None`. `problem`: the text of a defect, or `None`. |
| 63 | `    def finish(self, threads, stop):` | Starts the function `finish`. It computes the values of the interval after all rows of the process are read. `threads` is the thread count of the process. `stop` is its stop method, `pass` or `common`. |
| 64 | `        r = self.rows` | `r`: a short name for the list of the `T` rows. |
| 65 | `        if len(r) != threads:` | Tests whether the number of `T` rows differs from the number of threads. |
| 66 | `            self.problem = '%d T rows, %d threads expected' % (len(r), threads)` | Then `problem` says how many `T` rows were found and how many threads were expected. |
| 67 | `            return` | The function ends here. An interval with a problem gets no rate. |
| 68 | `        if any(x['elapsed'] <= 0 for x in r):` | Tests whether a thread has an elapsed time of 0 s or less. |
| 69 | `            self.problem = 'elapsed time not above 0'` | Then `problem` gets the text `elapsed time not above 0`. |
| 70 | `            return` | The function ends here, so no division by 0 follows. |
| 71 | `        longest = max(x['elapsed'] for x in r)` | `longest`: the longest elapsed time of a thread in this interval, in seconds. The elapsed time is the column `elapsed_s` of the `T` row (field 8). It is the time between two clock readings of the thread itself: directly before its first kernel call and directly after its last [Ref1]. |
| 72 | `        rates = sorted(x['bytes'] / x['elapsed'] / 1e9 for x in r)` | `rates`: the rate of each thread in GB/s, sorted from the lowest to the highest. A rate is the column `bytes` of the `T` row (field 7) divided by `elapsed_s` and by 1e9. For a copy kernel the runner counts the bytes read plus the bytes written [Ref6]. |
| 73 | `        m0 = [x for x in r if x['cpu'] in MESH0_CPUS]` | `m0`: the `T` rows of the threads on mesh 0. The CPU is the column `cpu` (field 6). It must lie in 0 to 63. |
| 74 | `        m1 = [x for x in r if x['cpu'] not in MESH0_CPUS]` | `m1`: the `T` rows of all other threads. The code takes them as mesh 1. |
| 75 | `        self.hist = sum(x['bytes'] for x in r) / longest / 1e9` | `hist`: the total rate `M_hist` in GB/s: the sum of `bytes` over all threads, divided by `longest` and by 1e9. One thread that runs longer than the others lowers this value for the whole interval. |
| 76 | `        self.msum = sum(rates)` | `msum`: the total rate `M_sum` in GB/s: the sum of the rates of the threads. Each thread is divided by its own elapsed time. |
| 77 | `        # per mesh: the same formulas over the threads of the mesh; M_hist keeps the longest time of ALL threads` | Comment: the values per mesh use the same two formulas over the threads of one mesh. For `M_hist` the divisor stays the longest elapsed time of all threads, not of the mesh. |
| 78 | `        self.mesh_hist = tuple(sum(x['bytes'] for x in m) / longest / 1e9 for m in (m0, m1))` | `mesh_hist`: the pair of the `M_hist` values of mesh 0 and of mesh 1, in GB/s. Each is the sum of `bytes` over the threads of that mesh, divided by `longest`. So the two values add up to `hist`. |
| 79 | `        self.mesh_sum = tuple(sum(x['bytes'] / x['elapsed'] / 1e9 for x in m) for m in (m0, m1))` | `mesh_sum`: the pair of the `M_sum` values of mesh 0 and of mesh 1, in GB/s: the sum of the thread rates of each mesh. |
| 80 | `        self.mesh_n = (len(m0), len(m1))` | `mesh_n`: the number of threads on mesh 0 and on mesh 1. |
| 81 | `        self.rate = self.hist                                   # one thread: bytes / elapsed` | `rate`: the same value as `hist`. The steps with one thread use this name. With one thread it is the bytes of the thread divided by its elapsed time, as the comment says. |
| 82 | `        self.skew = max(x['t_end'] for x in r) - min(x['t_end'] for x in r)` | `skew`: the end skew in seconds: the latest `t_end_s` of a thread minus the earliest. `t_end_s` is field 11 of the `T` row, the clock reading of the thread after its last kernel call, in seconds counted from the start of the process. |
| 83 | `        self.late = sum(1 for x in r if 'late' in x['flags'])` | `late`: the number of threads whose flag field (field 13) holds the word `late`. With the common stop the runner sets this flag when a thread starts more than 100 us after the planned common start. With the whole-pass stop it never sets the flag [Ref6]. |
| 84 | `        # Irregular (B.4): a late thread, or an end skew above 5 ms. The end skew is a rule of the common` | Comment: an interval is irregular when a thread is late or when the end skew is above 5 ms (section B.4 of the handoff note). The comment goes on in line 85. |
| 85 | `        # stop only: with --stop pass the threads end at pass borders, so their ends differ by design.` | Comment, continued: the end skew is a rule of the common stop only. With `--stop pass` the threads end at the borders of their passes, so their end times differ, and this is intended. |
| 86 | `        self.irregular = bool(self.late) or (stop == 'common' and self.skew > LATE_SKEW_S)` | `irregular`: true when at least one thread is late, or when the stop method is `common` and the end skew is above 0.005 s. With the whole-pass stop an end skew never makes an interval irregular. The deviations note lists this reading as point A5 and says that it needs a decision of the lead [Ref3]. |
| 87 | `        n = len(rates)                                          # nearest-rank percentiles` | `n`: the number of threads. The comment names the method of line 88: nearest-rank percentiles. |
| 88 | `        self.q = rates[max(0, math.ceil(0.10 * n) - 1)] / rates[max(0, math.ceil(0.90 * n) - 1)]` | `q`: the rate at the 10th percentile divided by the rate at the 90th percentile. The percentile `p` is the value at place `ceil(p x n)` of the sorted list, counted from 1. With 120 threads these are the 12th lowest and the 108th lowest rate. `max(0, ...)` keeps the index at 0 or above. |
| 89 | `        self.pattern = 'split' if self.q < Q_SPLIT else 'uniform' if self.q > Q_UNIFORM else 'between'` | `pattern`: the label of the interval from `q`: `split` below 0.65, `uniform` above 0.85, and `between` from 0.65 to 0.85. |

### Class `Proc`: the header line and the options of one process (lines 92 to 131)

| Line | Source | Explanation |
|---:|---|---|
| 92 | `class Proc:` | Starts the class `Proc`. One object holds one process of the runner. |
| 93 | `    """One bwx process: its header line and its rows."""` | Docstring of the class: a process is its header line and its data rows. |
| 95 | `    def __init__(self, session, path, m):` | Starts the function that makes a new object. `session` is the name of the session. `path` is the path of the csv file. `m` is the match of the pattern `HEAD` (line 39) on the header line. |
| 96 | `        self.session, self.file = session, os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path)` | Stores the session. `file`: the name of the folder of the csv file, a slash and the file name, for example `B1-20261114T012315Z/B1.csv`. The reports name a process by this text and its tag. |
| 97 | `        self.step, self.tag, self.binary = m.group(1), m.group(2), m.group(3)` | `step`, `tag` and `binary`: the groups 1 to 3 of the header line. The step is a name such as `B1`. The tag names the process inside the step. |
| 98 | `        self.waited_s = float(m.group(4)) if re.fullmatch(r'[\d.]+', m.group(4)) else None` | `waited_s`: group 4 as a number: the seconds that the run script waited for a quiet system before the start. The value is `None` when the field holds anything other than digits and dots. |
| 99 | `        self.load1 = float(m.group(5)) if re.fullmatch(r'[\d.]+', m.group(5)) else None` | `load1`: group 5 as a number: the load average over 1 minute at the start of the process. It is `None` when the field is not a number. |
| 100 | `        self.runnable, self.logins, self.utc = m.group(8), m.group(9), m.group(10)` | `runnable`: group 8, the text with the runnable tasks and all tasks. `logins`: group 9, the number of logged-in users, kept as text. `utc`: group 10, the time of the start. The groups 6 and 7, the load averages over 5 and 15 minutes, are not kept. |
| 101 | `        self.args = m.group(11).split()` | `args`: group 11, the arguments of the runner, split at spaces into a list. |
| 102 | `        self.opts, self.problems, self.status = {}, [], 'ok'` | `opts`: an empty dictionary for the options. `problems`: an empty list for the defects of the process. `status`: the word `ok`, until a line says that the process was killed or failed (line 207). |
| 103 | `        t = self.args` | `t`: a short name for the list of arguments. |
| 104 | `        i = 0` | `i`: the index of the argument that is read next. |
| 105 | `        while i < len(t):` | Loop over the arguments. |
| 106 | `            if t[i] in FLAG_OPTS:` | Tests whether the argument is one of the three options without a value (line 38). |
| 107 | `                self.opts[t[i]] = True` | Stores the option with the value `True`. |
| 108 | `                i += 1` | Goes on with the next argument. |
| 109 | `            elif t[i].startswith('--') and i + 1 < len(t):` | Tests whether the argument starts with `--` and another argument follows it. |
| 110 | `                self.opts[t[i]] = t[i + 1]` | Stores the option with the next argument as its value. |
| 111 | `                i += 2` | Skips both arguments. |
| 112 | `            else:` | Every other argument. |
| 113 | `                self.problems.append('option not understood: ' + t[i])` | Adds the problem `option not understood` with the argument. A process with a problem is not used (line 181). |
| 114 | `                i += 1` | Goes on with the next argument. |
| 115 | `        o = self.opts` | `o`: a short name for the dictionary of the options. |
| 116 | `        self.bytes = parse_size(o.get('--bytes', '1M'))` | `bytes`: the buffer size of `--bytes`, in bytes. Without the option it is 1 MiB, which is also the default of the runner [Ref6]. |
| 117 | `        self.seq = [e for e in o.get('--seq', '').split(',') if e]` | `seq`: the sequence of `--seq`, split at the commas into a list of entries. Empty pieces are dropped. Without the option the list is empty. |
| 118 | `        self.rounds = int(o.get('--rounds', 1))` | `rounds`: the number of rounds of `--rounds`, 1 without the option. |
| 119 | `        self.threads = int(o.get('--threads', 1))` | `threads`: the number of threads of `--threads`, 1 without the option. |
| 120 | `        self.stop, self.start = o.get('--stop', 'pass'), o.get('--start', 'common')` | `stop`: the stop method of `--stop`. Without the option it is `pass`, the whole-pass stop. `start`: the start method of `--start`, `common` without the option. With `common` every thread starts at the start of its buffer. With `offset` each thread starts its first pass at its own offset inside its buffer [Ref1]. |
| 121 | `        self.min_ms = int(float(o.get('--min-ms', 0)))` | `min_ms`: the shortest length of an interval of `--min-ms`, in whole ms. Without the option the value is 0 here. The runner itself uses 500 ms in that case [Ref6]. |
| 122 | `        self.no_thp, self.two_buffers, self.count = (k in o for k in ('--no-thp', '--two-buffers', '--count'))` | `no_thp`, `two_buffers` and `count`: true when the header line holds the option of that name. |
| 123 | `        self.cpu = int(o['--cpus']) if self.threads == 1 and o.get('--cpus', '').isdigit() else None` | `cpu`: the CPU of a process with one thread: the value of `--cpus` as a number, when it holds digits only. For every other process it is `None`. |
| 124 | `        self.setting = '%s/%d/%s' % (self.stop, self.min_ms, self.start)` | `setting`: the stop method, the interval length in ms and the start method, joined with slashes, for example `pass/500/common`. The steps with many threads group their processes by this text. |
| 125 | `        self.raw = {}             # (round as printed, pos) -> Interval` | `raw`: an empty dictionary for the intervals. By the comment its key is the pair of the round as printed and the position. |
| 126 | `        self.P, self.C, self.n_I, self.other_lines = [], [], 0, 0` | `P`: the list of the `P` rows. `C`: the list of the `C` rows. `n_I`: the number of `I` rows. `other_lines`: the number of lines of no known kind. |
| 127 | `        self.iv, self.ordered, self.complete = {}, [], False` | `iv`: the intervals under the pair of the round counted from 0 and the position (line 176). `ordered`: the intervals in time order (line 177). `complete`: false until `finish` has tested the process (line 181). |
| 129 | `    def entry_size(self, entry):` | Starts the function `entry_size`. It gives the size in bytes that one entry of the sequence uses. |
| 130 | `        return parse_size(entry.split('@')[1]) if '@' in entry else self.bytes` | An entry with the character `@`, such as `oldread@1M`, uses the size after that character. Every other entry uses the size of `--bytes`. |

### `Proc.add` and `Proc._iv`: the data rows of the runner (lines 132 to 168)

| Line | Source | Explanation |
|---:|---|---|
| 132 | `    def add(self, line):` | Starts the function `add`. It reads one data line of the process. |
| 133 | `        f = line.split(',')` | `f`: the fields of the line, split at the commas. Python counts from 0, so `f[6]` is field 7. The rows below name the fields counted from 1. |
| 134 | `        try:` | Starts a block. Line 156 catches its errors. |
| 135 | `            if f[0] == 'I' and len(f) == 9:` | An `I` row: the first field is `I` and the row has 9 fields. The runner prints one `I` row per interval. |
| 136 | `                self.n_I += 1` | Counts the `I` row. |
| 137 | `                self._iv(int(f[1]), int(f[2]), f[3]).irow = dict(threads=int(f[5]), total_bytes=int(f[6]),` | Finds or makes the interval of this round (field 2) and position (field 3) with `_iv` (line 159). `_iv` also checks the kernel name (field 4). The record `irow` of the interval gets the thread count (field 6) and the total bytes (field 7). The call goes on in line 138. |
| 138 | `                                                                 max_elapsed=float(f[7]), aggregate=float(f[8]))` | Continues line 137: the longest elapsed time in seconds (field 8) and the rate that the runner printed (field 9, in GB/s with 2 decimals). No other line of the file reads `irow`. Every rate of the analysis comes from the `T` rows (line 72). The deviations note gives the reason in point A2: 2 decimals are too coarse for an A/A spread [Ref3]. |
| 139 | `            elif f[0] == 'T' and len(f) == 13:` | A `T` row: the first field is `T` and the row has 13 fields. The runner prints one `T` row per thread and interval. |
| 140 | `                self._iv(int(f[1]), int(f[2]), f[3]).rows.append(dict(` | Finds or makes the interval as in line 137 and adds one record to its `rows`. Lines 141 to 142 list the record. |
| 141 | `                    tid=int(f[4]), cpu=int(f[5]), bytes=int(f[6]), elapsed=float(f[7]), t_sched=float(f[8]),` | The record of the thread: `tid` (field 5, the number of the thread), `cpu` (field 6), `bytes` (field 7, the bytes that the thread handled in the interval), `elapsed` (field 8, `elapsed_s`) and `t_sched` (field 9, the planned common start in seconds). |
| 142 | `                    t_start=float(f[9]), t_end=float(f[10]), passes=float(f[11]), flags=f[12]))` | Continues the record: `t_start` (field 10) and `t_end` (field 11), the clock readings of the thread at its start and at its end, in seconds counted from the start of the process. `passes` (field 12): the bytes divided by the bytes of one pass. `flags` (field 13): `-` or `late`. |
| 143 | `            elif f[0] == 'P' and len(f) == 11:` | A `P` row: the first field is `P` and the row has 11 fields. It holds the page state of one buffer. |
| 144 | `                num = lambda x: None if x == 'NA' else int(x)` | `num`: a small function that turns a field into a whole number, or into `None` for the text `NA`. |
| 145 | `                self.P.append(dict(round=int(f[1]), pos=int(f[2]), tid=int(f[3]), buffer=f[4], kB_total=num(f[5]),` | Adds one record to the list `P`: the round (field 2), the position (field 3), the thread (field 4), the buffer letter (field 5, `a` or `b`) and `kB_total` (field 6). `kB_total` is the size in kB of the entry that Linux lists for the buffer in `/proc/self/smaps` [Ref1]. |
| 146 | `                                   kB_huge=num(f[6]), thp_fault_alloc=num(f[7]), thp_fault_fallback=num(f[8]),` | Continues the record: `kB_huge` (field 7), the kB of the buffer that lie on huge pages. Then two counters of the whole system from the file `/proc/vmstat`: `thp_fault_alloc` (field 8) and `thp_fault_fallback` (field 9). |
| 147 | `                                   thp_collapse_alloc=num(f[9]), pgmigrate_success=num(f[10])))` | Continues the record: two more counters of the whole system, `thp_collapse_alloc` (field 10) and `pgmigrate_success` (field 11). Step B4 uses these two as signs that Linux replaced or moved pages somewhere (lines 424 to 425). |
| 148 | `            elif f[0] == 'C' and len(f) >= 9:` | A `C` row: the first field is `C` and the row has at least 9 fields. It holds the counter values of one thread in one interval. |
| 149 | `                na = lambda x: None if x == 'NA' else int(x)      # NA: the group or the event did not open` | `na`: the same function as `num` of line 144. By the comment, `NA` means that the counter group or the event could not be opened. |
| 150 | `                self.C.append(dict(round=int(f[1]), pos=int(f[2]), kernel=f[3], tid=int(f[4]), cpu=int(f[5]),` | Adds one record to the list `C`: the round (field 2), the position (field 3), the kernel (field 4), the thread (field 5) and the CPU (field 6). The record goes on in line 151. |
| 151 | `                                   enabled=na(f[6]), running=na(f[7]), cputime=na(f[8]), counts=[na(x) for x in f[9:]]))` | Continues the record: `enabled` (field 7) and `running` (field 8), the ns of the interval for which the counter group was enabled and for which it counted. `cputime` (field 9): the CPU time of the thread in the interval, in ns. `counts`: all further fields, one count per event. |
| 152 | `            elif f[0] in ('I', 'T', 'P', 'C'):` | A row that starts with `I`, `T`, `P` or `C` and has another number of fields. |
| 153 | `                self.problems.append('row with a wrong number of fields: ' + line[:60])` | Adds the problem `row with a wrong number of fields` with the first 60 characters of the line. |
| 154 | `            else:` | Every other line. |
| 155 | `                self.other_lines += 1` | Counts it in `other_lines`. It is not a problem. |
| 156 | `        except (ValueError, IndexError):` | Catches the error of a field that is not a number, and the error of a missing field. |
| 157 | `            self.problems.append('row not understood: ' + line[:60])` | Adds the problem `row not understood` with the first 60 characters of the line. |
| 159 | `    def _iv(self, rnd, pos, kernel):` | Starts the function `_iv`. It returns the interval of a round and a position, and it makes the interval at its first row. `kernel` is the kernel name of the row. |
| 160 | `        if not 0 <= pos < len(self.seq):` | Tests whether the position lies outside the sequence of the header line. |
| 161 | `            self.problems.append('position %d is outside the sequence' % pos)` | Then it adds the problem that the position is outside the sequence. |
| 162 | `            pos_entry = kernel` | The entry of the interval is then the kernel name of the row. |
| 163 | `        else:` | The position lies inside the sequence. |
| 164 | `            pos_entry = self.seq[pos]` | `pos_entry`: the entry of the sequence at this position, for example `oldread@1M`. The runner prints the kernel name without the size. So the size of an interval comes from the header line (point A1 of the deviations note [Ref3]). |
| 165 | `            if kernel.split('@')[0] != pos_entry.split('@')[0]:` | Compares the kernel name of the row with the entry. Both are cut at the character `@` first. |
| 166 | `                self.problems.append('kernel %s at position %d, the sequence has %s' % (kernel, pos, pos_entry))` | When they differ, it adds a problem that names the kernel, the position and the entry. The process is then left out. |
| 167 | `        return self.raw.setdefault((rnd, pos), Interval(rnd, pos, pos_entry))` | Returns the interval that is stored under the pair of round and position. `setdefault` stores a new `Interval` when the pair is not there yet. |

### `Proc.finish` and `Proc.page_before`: complete or not, and the page row (lines 169 to 193)

| Line | Source | Explanation |
|---:|---|---|
| 169 | `    def finish(self):` | Starts the function `finish` of a process. `read_csv` calls it after the whole file is read (line 211). |
| 170 | `        rounds = sorted({k[0] for k in self.raw})                # rounds may be printed from 0 or from 1` | `rounds`: the round numbers that occur in the rows, sorted. By the comment a runner may print its rounds from 0 or from 1. |
| 171 | `        for (rnd, pos), iv in self.raw.items():` | Loop over the intervals. |
| 172 | `            iv.finish(self.threads, self.stop)` | Computes the values of the interval (line 63), with the thread count and the stop method of the process. |
| 173 | `            if iv.problem:` | Tests whether the interval has a problem. |
| 174 | `                self.problems.append('round %d pos %d: %s' % (rnd, pos, iv.problem))` | Then the problem goes into the list of the process, with the round and the position. |
| 175 | `            iv.r = rounds.index(rnd)` | `iv.r`: the place of the printed round number in the sorted list. So the first round is 0, whatever number the runner printed. |
| 176 | `            self.iv[(iv.r, pos)] = iv` | Stores the interval in `iv` under the pair of this round and the position. |
| 177 | `        self.ordered = [self.iv[k] for k in sorted(self.iv)]` | `ordered`: the intervals sorted by round and position. This is their order in time. |
| 178 | `        want = len(self.seq) * self.rounds` | `want`: the number of intervals that the header line asks for: the length of the sequence times the number of rounds. |
| 179 | `        if self.status == 'ok' and len(self.iv) != want:` | Tests whether a process without a `killed` or `failed` line has another number of intervals. |
| 180 | `            self.problems.append('%d intervals, %d expected' % (len(self.iv), want))` | Then it adds a problem that names the number found and the number expected. |
| 181 | `        self.complete = self.status == 'ok' and not self.problems and want > 0` | `complete`: true only when the status is `ok`, the list of problems is empty, and at least one interval was expected. Only a complete process gives values (point A3 of the deviations note [Ref3]). |
| 182 | `        self.rate_by_entry = {}` | `rate_by_entry`: an empty dictionary. It stays empty for a process that is not complete. |
| 183 | `        if self.complete:` | Only for a complete process. |
| 184 | `            for iv in self.ordered:` | Loop over the intervals in time order. |
| 185 | `                self.rate_by_entry.setdefault(iv.entry, []).append(iv)` | Groups the intervals by their entry. Each entry gets the list of its intervals in time order. The dictionary holds the interval objects, not rates, although its name says rate. |
| 187 | `    def page_before(self, iv):` | Starts the function `page_before`. It finds the `P` row that belongs to one interval. |
| 188 | `        """One-thread process: the P row read before the interval (same round and position), buffer a."""` | Docstring: in a process with one thread this is the `P` row of the same round and position, of buffer `a`. In such a process the worker reads the page state after the warm-up pass of the entry and before the timed interval [Ref1]. |
| 189 | `        rows = [p for p in self.P if p['round'] == iv.round and p['pos'] == iv.pos]` | `rows`: the `P` rows whose round and position are those of the interval. The round is compared as the runner printed it. |
| 190 | `        a = [p for p in rows if p['buffer'] in ('a', 'A', '0')]` | `a`: of these rows, those of the first buffer. The buffer field may be `a`, `A` or `0`. |
| 191 | `        return a[0] if len(a) == 1 else rows[0] if len(rows) == 1 else None` | Returns the row of buffer `a` when exactly one exists. If not, it returns the only row when exactly one row exists. In every other case it returns `None`. |

### `read_csv` and `load_session`: from the files to the processes (lines 194 to 225)

| Line | Source | Explanation |
|---:|---|---|
| 194 | `def read_csv(session, path):` | Starts the function `read_csv`. It reads one csv file and returns its processes. |
| 195 | `    procs, cur = [], None` | `procs`: the list of the processes found so far. `cur`: the process whose rows are read now. It is `None` before the first header line. |
| 196 | `    with open(path) as fh:` | Opens the file for reading. Python closes it when the block of this line ends. |
| 197 | `        for line in fh:` | Reads the file line by line. |
| 198 | `            line = line.rstrip('\n')` | Removes the line end. |
| 199 | `            if line.startswith('-- step '):` | A line that starts with `-- step` and a space is a header line. The run script writes one before each start of the runner. |
| 200 | `                m = HEAD.match(line)` | Tests the line against the pattern `HEAD` (line 39). |
| 201 | `                if not m:` | Tests whether the line did not fit. |
| 202 | `                    raise ValueError('%s: header line not understood: %s' % (path, line[:80]))` | Then the function stops with an error that names the file and the first 80 characters of the line. `main` does not catch this error, so the whole script ends. |
| 203 | `                cur = Proc(session, path, m)` | Makes a new `Proc` from the header line and takes it as the current process. |
| 204 | `                procs.append(cur)` | Adds it to the list. |
| 205 | `            elif line.startswith('-- killed') or line.startswith('-- failed'):` | A line that starts with `-- killed` or with `-- failed`. The run script writes `-- killed` when it stops the runner, and `-- failed` when the runner ends with an error [Ref7]. |
| 206 | `                if cur:` | Only when a process is open. |
| 207 | `                    cur.status = line.split()[1]` | The status of the current process becomes the second word of the line: `killed` or `failed`. |
| 208 | `            elif cur and line and not line.startswith('#'):` | Every other line that is not empty and does not start with `#`, when a process is open. The lines that start with `#` are the comment lines of the runner. |
| 209 | `                cur.add(line)` | Passes the line to the current process (line 132). |
| 210 | `    for p in procs:` | After the last line: loop over the processes of the file. |
| 211 | `        p.finish()` | Computes the values of each process (line 169). |
| 212 | `    return procs` | Returns the processes in file order. |
| 215 | `def load_session(name, paths):` | Starts the function `load_session`. It reads all files of one session. |
| 216 | `    procs = []` | `procs`: the processes of the session, empty at first. |
| 217 | `    for path in paths:` | Loop over the paths that the command line gave for this session. |
| 218 | `        files = sorted(glob.glob(os.path.join(path, '*.csv'))) if os.path.isdir(path) else [path]` | `files`: for a folder, all files in it whose names end with `.csv`, sorted by name. For any other path, the path itself. |
| 219 | `        if not files:` | Tests whether a folder held no csv file. |
| 220 | `            raise ValueError('no csv file in ' + path)` | Then the function stops with the error `no csv file in` and the path. |
| 221 | `        for f in files:` | Loop over the files. |
| 222 | `            procs += read_csv(name, f)` | Adds the processes of the file. Each one holds the session name. |
| 223 | `    return procs` | Returns all processes of the session. |

### Helpers: `med`, `row`, `integrity` and `pair_label` (lines 226 to 260)

| Line | Source | Explanation |
|---:|---|---|
| 226 | `# ---------------------------------------------------------------- helpers` | Comment: a divider. The small helper functions start here. |
| 228 | `def med(v):` | Starts the function `med`: a median that also accepts an empty list. |
| 229 | `    return median(v) if v else None` | Returns the median of the list, or `None` for an empty list. |
| 232 | `def row(what, word, n, spread, value, note=''):` | Starts the function `row`. It builds one line of the text table of a step. |
| 233 | `    """One line of the text table of a step: every decision with its number of processes and its A/A spread."""` | Docstring: every decision is printed with its number of processes and its A/A spread. |
| 234 | `    return dict(what=what, decision=word, n_processes=n, aa_spread=spread, value=value, note=note)` | Returns a dictionary with six fields: `what` (the label of the line), `decision` (the word), `n_processes`, `aa_spread` (in GB/s), `value` (in GB/s) and `note`. |
| 237 | `def integrity(procs):` | Starts the function `integrity`. Every analysis function of a step calls it first. |
| 238 | `    """What every step reports first: the processes used, the processes left out, the irregular intervals, the load."""` | Docstring: it gives what every step reports first: the processes used, the processes left out, the irregular intervals and the load. |
| 239 | `    used = [p for p in procs if p.complete]` | `used`: the complete processes (line 181). |
| 240 | `    load = [p.load1 for p in procs if p.load1 is not None]` | `load`: the load average over 1 minute of every process whose header line has one. |
| 241 | `    waits = [p.waited_s for p in procs if p.waited_s is not None]` | `waits`: the wait in seconds of every process whose header line has one. |
| 242 | `    out = dict(` | Starts the report dictionary `out`. It ends in line 251. |
| 243 | `        n_processes=len(procs), n_used=len(used),` | `n_processes`: all processes of the step in the files. `n_used`: the complete ones. |
| 244 | `        left_out=[dict(file=p.file, tag=p.tag, reason=(p.status if p.status != 'ok' else '; '.join(p.problems[:3]) or 'no interval'))` | `left_out`: one record per process that is not complete, with file, tag and reason. The reason is the status word (`killed` or `failed`) when the process has one. If not, it is the first three problems, joined with the character `;` and a space. A process without any problem gets the text `no interval`. |
| 245 | `                  for p in procs if not p.complete],` | Continues line 244: the list takes only the processes that are not complete. |
| 246 | `        irregular_intervals=[dict(file=p.file, tag=p.tag, round=iv.round, pos=iv.pos, entry=iv.entry, late_threads=iv.late,` | `irregular_intervals`: one record per irregular interval of a used process: file, tag, round, position, entry and the number of late threads. The record goes on in line 247. |
| 247 | `                                  end_skew_ms=round(iv.skew * 1e3, 3)) for p in used for iv in p.ordered if iv.irregular],` | Continues line 246: the end skew in ms, rounded to 3 decimals (1 us). The two loops of the list follow: over the used processes and over their intervals. |
| 248 | `        load=dict(loadavg_1min_min=min(load) if load else None, loadavg_1min_max=max(load) if load else None,` | `load`: the lowest and the highest load average over 1 minute over the starts of the processes, or `None` without a value. The dictionary goes on in line 249. |
| 249 | `                  waited_s_max=max(waits) if waits else None, logins=sorted({p.logins for p in procs})),` | Continues line 248: the longest wait in seconds, and the sorted set of the login counts of the header lines. |
| 250 | `        page_rows_NA=sum(1 for p in procs for x in p.P if x['kB_total'] is None or x['kB_huge'] is None),` | `page_rows_NA`: the number of `P` rows in which `kB_total` or `kB_huge` is `NA`. The runner prints `NA` when it finds no entry in `/proc/self/smaps` that is exactly the buffer [Ref1]. |
| 251 | `        page_rows=sum(len(p.P) for p in procs))` | `page_rows`: the number of all `P` rows. The line ends the dictionary of line 242. |
| 252 | `    return used, out` | Returns the complete processes and the report. |
| 255 | `def pair_label(refs):` | Starts the function `pair_label`. It gives the level label of one pair from the rates of its two reference intervals. |
| 256 | `    """Rule 5 of the plan: low if both neighbouring references are low, high if both are high, else changing."""` | Docstring: rule 5 of the plan. A pair is low when both neighbouring reference intervals are low, high when both are high, and changing in every other case. |
| 257 | `    levels = {decide.level(r) for r in refs}` | `levels`: the set of the level labels of the two reference rates. `decide.level` gives `low` below 69.0 GB/s, `high` above 70.5 GB/s and `changing` for the rest [Ref4]. |
| 258 | `    return levels.pop() if len(levels) == 1 and levels != {'changing'} else 'changing'` | Returns the one label when both rates have the same label and that label is not `changing`. In every other case it returns `changing`. |

### Function `pair_values`: pairs between two reference intervals (lines 261 to 275)

| Line | Source | Explanation |
|---:|---|---|
| 261 | `def pair_values(p, first, second):` | Starts the function `pair_values`. `p` is a process, and `first` and `second` are two entries of its sequence. |
| 262 | `    """Pairs of the entries first and second that stand between the same two reference intervals.` | Docstring: it finds the pairs of the two entries that stand between the same two reference intervals. The docstring goes on in line 263. |
| 263 | `    Value = rate of first minus rate of second (GB/s)."""` | Docstring: the value of a pair is the rate of `first` minus the rate of `second`, in GB/s. |
| 264 | `    out = []` | `out`: the list of the pairs, empty at first. |
| 265 | `    refpos = [i for i, e in enumerate(p.seq) if e == REF]` | `refpos`: the positions of the sequence whose entry is exactly `asmread`, the reference kernel. |
| 266 | `    for r in range(p.rounds):` | Loop over the rounds of the process. |
| 267 | `        for a, b in zip(refpos, refpos[1:]):` | Loop over each two reference positions that follow each other in the sequence. |
| 268 | `            if b - a != 3 or {p.seq[a + 1], p.seq[a + 2]} != {first, second} or first == second:` | A pair exists only when the two reference positions are 3 apart. Then exactly two intervals lie between them. The entries of these two intervals must be `first` and `second`, in any order. The line also skips the case that `first` and `second` are the same name. |
| 269 | `                continue` | Every other case is skipped. |
| 270 | `            rate = {p.seq[i]: p.iv[(r, i)].rate for i in (a + 1, a + 2)}` | `rate`: the rates of the two intervals between the references, by entry. The rate of an interval with one thread is its bytes divided by its elapsed time (line 81). |
| 271 | `            refs = (p.iv[(r, a)].rate, p.iv[(r, b)].rate)` | `refs`: the rates of the reference interval before the pair and of the reference interval after it. |
| 272 | `            out.append(dict(round=r, pos=a + 1, value=rate[first] - rate[second], label=pair_label(refs)))` | Adds the pair: its round, the position of its first interval, its value (the rate of `first` minus the rate of `second`, in GB/s) and its level label (line 255). |
| 273 | `    return out` | Returns the pairs of the process. |

### Function `one_thread_group`: one comparison, decided per label and per CPU (lines 276 to 310)

| Line | Source | Explanation |
|---:|---|---|
| 276 | `def one_thread_group(procs, first, second, aa_first, aa_second, labelled):` | Starts the function `one_thread_group`. It decides one comparison for one group of processes with one thread. `first` and `second` name the kernel pair. `aa_first` and `aa_second` name the A/A pair. `labelled` says whether the level labels are used. |
| 277 | `    """One size (or variant, or build) of a one-thread step. Process values with decide.process_value,` | Docstring: the group is one size, one variant or one build of a step with one thread. `decide.process_value` gives the process values. The docstring goes on in line 278. |
| 278 | `    decision per label and per CPU with decide.decide_one_thread. CPUs are never pooled."""` | Docstring: `decide.decide_one_thread` gives the decision per label and per CPU. Processes of different CPUs are never put together. |
| 279 | `    plist, detail = [], []` | `plist`: the process values of the processes that give one. `detail`: one record per process for the JSON file. |
| 280 | `    for p in procs:` | Loop over the processes of the group. |
| 281 | `        kp, ap = pair_values(p, first, second), pair_values(p, aa_first, aa_second)` | `kp`: the pairs of the kernel comparison. `ap`: the pairs of the A/A comparison (line 261). |
| 282 | `        refs = [iv.rate for iv in p.ordered if iv.entry == REF]` | `refs`: the rates of all reference intervals of the process, in time order. |
| 283 | `        pv = decide.process_value(refs, [x['value'] for x in kp], [x['value'] for x in ap], labelled=labelled)` | `pv`: the triple of label, `d` and `e`, or `None`. `d` is the median of the kernel pair values of the process. `e` is the median of its A/A pair values. With `labelled` a process gives values only when all its reference intervals are low or all are high. Without it every process with pairs gives values, under the label `none` [Ref4]. |
| 284 | `        rec = dict(file=p.file, tag=p.tag, cpu=p.cpu, reference_min=min(refs) if refs else None,` | Starts the record of the process: file, tag, CPU and the lowest reference rate. |
| 285 | `                   reference_median=med(refs), reference_max=max(refs) if refs else None,` | Continues the record: the median and the highest reference rate, in GB/s. |
| 286 | `                   n_kernel_pairs=len(kp), n_aa_pairs=len(ap))` | Continues the record: the number of kernel pairs and the number of A/A pairs. |
| 287 | `        if pv is None:` | The process gave no value. |
| 288 | `            rec.update(used=False, reason='no pair found' if not kp or not ap else 'the reference intervals are not all at one level',` | The record gets `used` false and the reason. The reason is `no pair found` when one of the two pair lists is empty. If not, it says that the reference intervals are not all at one level. The call goes on in line 289. |
| 289 | `                       pairs=[dict(label=x['label'], value=round(x['value'], 3)) for x in kp])` | Continues line 288: the record keeps every kernel pair with its label and its value, rounded to 0.001 GB/s. So the report lists the pairs of a process that is not used. |
| 290 | `        else:` | The process gave a value. |
| 291 | `            rec.update(used=True, label=pv[0], d=pv[1], e=pv[2])` | The record gets `used` true, the label, `d` and `e`. |
| 292 | `            plist.append(dict(cpu=p.cpu, label=pv[0], d=pv[1], e=pv[2]))` | Adds the CPU, the label, `d` and `e` to `plist`. |
| 293 | `        detail.append(rec)` | Adds the record to `detail`. |
| 294 | `    dec = decide.decide_one_thread(plist) if plist else {}` | `dec`: the decision for each label that occurs. `decide.decide_one_thread` first decides each CPU alone. A CPU needs at least 3 processes with the label. It is resolved when the absolute median of `d` is above the largest absolute `e` and all `d` have one sign. A label is resolved when at least 2 CPUs have enough processes, each of them is resolved, and all have the same sign [Ref4]. |
| 295 | `    out = {}` | `out`: the result per label, empty at first. |
| 296 | `    for lab in (('low', 'high') if labelled else ('none',)):` | Loop over the labels: `low` and `high` with level labels, and `none` without them. |
| 297 | `        word, sign, per = dec.get(lab, ('not observed', None, {}))` | The word, the sign and the results per CPU of this label. A label that no process has gets `not observed`. |
| 298 | `        cpus = {}` | `cpus`: the result per CPU, empty at first. |
| 299 | `        for cpu in sorted({p.cpu for p in procs}):` | Loop over the CPUs of all processes of the group, in rising order. |
| 300 | `            g = [x for x in plist if x['cpu'] == cpu and x['label'] == lab]` | `g`: the process values of this CPU with this label. |
| 301 | `            w = per.get(cpu, ('not observed', None))` | `w`: the word and the sign of this CPU. It is `not observed` when the decision has no entry for the CPU. |
| 302 | `            cpus[cpu] = dict(decision=w[0], sign=w[1], n_processes=len(g), d=[x['d'] for x in g],` | Stores for the CPU: the word, the sign, the number of processes and the list of their `d` values. The record goes on in line 303. |
| 303 | `                             median_d=med([x['d'] for x in g]), aa_spread=max((abs(x['e']) for x in g), default=None))` | Continues line 302: the median of `d` in GB/s, and the A/A spread: the largest absolute `e` of these processes, or `None` without a process. |
| 304 | `        out[lab] = dict(decision=word, sign=sign, per_cpu=cpus,` | Stores for the label: the word, the sign and the results per CPU. The record goes on in lines 305 to 307. |
| 305 | `                        n_processes=sum(c['n_processes'] for c in cpus.values()),` | Continues the record: the number of processes with this label over all CPUs. This number is only reported. No decision puts the CPUs together. |
| 306 | `                        note='' if word != 'not observed' else 'Insufficient data: fewer than 2 CPUs have 3 processes with this label; '` | Continues the record: the note. It is empty unless the word is `not observed`. Then it starts with `Insufficient data` and says that fewer than 2 CPUs have 3 processes with this label. |
| 307 | `                        'processes per CPU: ' + ', '.join('CPU %s: %d' % (c, v['n_processes']) for c, v in cpus.items()))` | Continues the note: the number of processes with this label for each CPU. |
| 308 | `    return out, detail, plist` | Returns the result per label, the records per process and the process values. |

### Functions `group_rows` and `sign_txt`: lines of the text table (lines 311 to 324)

| Line | Source | Explanation |
|---:|---|---|
| 311 | `def group_rows(name, res):` | Starts the function `group_rows`. It turns the result of line 276 into lines of the text table. `name` is the label of the group. |
| 312 | `    rows = []` | `rows`: the lines, empty at first. |
| 313 | `    for lab, r in res.items():` | Loop over the labels of the result. |
| 314 | `        rows.append(row('%s label %s, all CPUs' % (name, lab), r['decision'] + sign_txt(r['sign']), r['n_processes'], None, None, r['note']))` | One line for the label over all CPUs: the word with its sign, and the number of processes. This line has no A/A spread and no value. Its note is the note of line 306. |
| 315 | `        for cpu, c in r['per_cpu'].items():` | Loop over the CPUs. |
| 316 | `            rows.append(row('%s label %s CPU %s' % (name, lab, cpu), c['decision'] + sign_txt(c['sign']), c['n_processes'],` | One line per CPU: the word with its sign, the number of processes of this CPU, the A/A spread and the median of `d`. The call goes on in line 317. |
| 317 | `                            c['aa_spread'], c['median_d'], 'value = median d'))` | Continues line 316: the note says that the value column holds the median of `d`. |
| 318 | `    return rows` | Returns the lines. |
| 321 | `def sign_txt(s):` | Starts the function `sign_txt`. It gives the text that shows a sign in a table. |
| 322 | `    return '' if s is None else ' (+)' if s > 0 else ' (-)'` | Returns an empty text without a sign. For a positive sign it returns a space and `(+)`, and for a negative sign a space and `(-)`. |

### Function `a_copy`: steps B1, B2 and B3, a copy kernel against `asmcopy` (lines 325 to 366)

| Line | Source | Explanation |
|---:|---|---|
| 325 | `# ---------------------------------------------------------------- one-thread steps` | Comment: a divider. The analysis functions of the steps with one thread start here. |
| 327 | `def a_copy(procs, ctx, step):` | Starts the function `a_copy`, the analysis of the steps B1, B2 and B3. `procs` holds the processes of one step in one session. `ctx` is a dictionary that passes values from one step to a later step of the same session. `step` is the step name. |
| 328 | `    """B1 (per size), B2 (per variant), B3 (per build), C2: kernel pair against asmcopy, A/A pair asmcopy2 - asmcopy."""` | Docstring: B1 is decided per size, B2 per variant and B3 per build. The kernel pair is the compared copy kernel against `asmcopy`, and the A/A pair is `asmcopy2` minus `asmcopy`. The docstring also names C2. That does not fit the code: the table of lines 849 to 850 gives C2 to the function `a_count`. |
| 329 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report with `integrity` (line 237). |
| 330 | `    groups = {}` | `groups`: the processes by group, empty at first. |
| 331 | `    for p in used:` | Loop over the complete processes. |
| 332 | `        other = [e for e in p.seq if e not in (REF, 'asmcopy', 'asmcopy2')]` | `other`: the entries of the sequence that are not `asmread`, `asmcopy` or `asmcopy2`. In the sequence of step B1 this is `copy`, the new C copy kernel. In step B2 it is one of the three variants of the copy loop in assembly [Ref1]. |
| 333 | `        first = other[0] if other else None` | `first`: the first such entry, the kernel that is compared with `asmcopy`. It is `None` when the sequence has none. |
| 334 | `        key = p.binary if step == 'B3' else first if step == 'B2' else size_name(p.bytes)` | `key`: the name of the group. For B3 it is the name of the binary: B3 uses one binary per loop offset. For B2 it is the compared kernel. For every other step it is the size name of `--bytes`, for example `8M`. |
| 335 | `        groups.setdefault((key, first, p.bytes), []).append(p)` | Puts the process into the group of its key, its compared kernel and its size. |
| 336 | `    out['groups'], rows, plists = {}, [], {}` | `out['groups']`: the results per group. `rows`: the table lines. `plists`: the process values per group. All three are empty at first. |
| 337 | `    for (key, first, size), g in sorted(groups.items(), key=lambda kv: str(kv[0])):` | Loop over the groups, sorted by the text of their key. |
| 338 | `        res, detail, plist = one_thread_group(g, first, 'asmcopy', 'asmcopy2', 'asmcopy', labelled=(size == 8 * MIB))` | Decides the group with `one_thread_group` (line 276). The kernel pair is `first` minus `asmcopy`, and the A/A pair is `asmcopy2` minus `asmcopy`. The level labels are used only when the size is exactly 8 MiB. At every other size all processes count, with the label `none`. |
| 339 | `        out['groups'][key] = dict(kernel_pair='%s - asmcopy' % first, aa_pair='asmcopy2 - asmcopy', size=size_name(size),` | Stores the result of the group: the names of the two pairs and the size. The record goes on in line 340. |
| 340 | `                                  labels=res, processes=detail)` | Continues line 339: the results per label and the records per process. |
| 341 | `        plists[key] = plist` | Keeps the process values of the group. |
| 342 | `        rows += group_rows('%s %s (%s - asmcopy)' % (step, key, first), res)` | Adds the table lines of the group (line 311). Their label names the step, the group and the kernel pair. |
| 343 | `    ctx[step] = plists` | Stores the process values of this step in `ctx`. Step B3 reads those of step B1 from there (line 346). |
| 344 | `    if step == 'B3':` | The lines from here to line 362 run for step B3 only. |
| 345 | `        out['change_against_B1'] = {}` | `change_against_B1`: the changes per build, empty at first. |
| 346 | `        base = ctx.get('B1', {}).get('8M')` | `base`: the process values of step B1 at 8 MiB in the same session, or `None` when the session has none. `analyze` handles B1 before B3 (line 851). |
| 347 | `        for key, plist in plists.items():` | Loop over the builds of B3. |
| 348 | `            ch = {}` | `ch`: the changes of this build, empty at first. |
| 349 | `            for lab in ('low', 'high'):` | Loop over the two level labels. |
| 350 | `                for cpu in sorted({x['cpu'] for x in plist}):` | Loop over the CPUs for which the build has process values. |
| 351 | `                    y = [dict(D=x['d'], E=x['e']) for x in plist if x['cpu'] == cpu and x['label'] == lab]` | `y`: the process values of the build on this CPU with this label, as records with `D` (the `d` of the process) and `E` (its `e`). |
| 352 | `                    x_ = [dict(D=x['d'], E=x['e']) for x in (base or []) if x['cpu'] == cpu and x['label'] == lab]` | `x_`: the same for step B1. |
| 353 | `                    if base is None:` | Step B1 at 8 MiB is missing in this session. |
| 354 | `                        word, change, note = 'not observed', None, 'B1 at 8 MiB of the same session is missing'` | Then the word is `not observed`, with the note that B1 is missing. |
| 355 | `                    else:` | Step B1 is there. |
| 356 | `                        word, change = decide.decide_change(x_, y, min_n=3)` | `decide.decide_change` with a smallest count of 3 processes. The change is the median `d` of B1 minus the median `d` of the build, in GB/s. It is resolved when its absolute value is above the sum of the two A/A spreads and every `d` of B1 lies on one side of every `d` of the build. With fewer than 3 processes in B1 or in the build the word is `not observed` and the change is `None` [Ref4]. |
| 357 | `                        note = 'change = median d of B1 minus median d of the build' if change is not None else \` | `note`: when a change exists, the note says how it is computed. The other case follows in line 358. |
| 358 | `                            'fewer than 3 processes with this label on this CPU in B1 (%d) or in the build (%d)' % (len(x_), len(y))` | Continues line 357: without a change, the note says that fewer than 3 processes have this label on this CPU, and gives the count of B1 and the count of the build. |
| 359 | `                    spread = None if change is None else max(abs(v['E']) for v in x_) + max(abs(v['E']) for v in y)` | `spread`: the sum of the two A/A spreads in GB/s: the largest absolute `e` of B1 plus the largest absolute `e` of the build. It is `None` without a change. |
| 360 | `                    ch['%s/cpu%s' % (lab, cpu)] = dict(decision=word, change=change, n_B1=len(x_), n_build=len(y), sum_of_aa_spreads=spread, note=note)` | Stores the result under a key such as `low/cpu0`: the word, the change, the two process counts, the sum of the A/A spreads and the note. |
| 361 | `                    rows.append(row('B3 %s change against B1, label %s CPU %s' % (key, lab, cpu), word, '%d and %d' % (len(x_), len(y)), spread, change, note))` | Adds one table line: the build, the label and the CPU, the word, the two counts, the sum of the A/A spreads and the change. |
| 362 | `            out['change_against_B1'][key] = ch` | Stores the changes of the build. |
| 363 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 364 | `    return out` | Returns the report of the step. |

### Functions `a_b6` and `coverage`: step B6, and the coverage word of a `P` row (lines 367 to 407)

| Line | Source | Explanation |
|---:|---|---|
| 367 | `def a_b6(procs, ctx, step):` | Starts the function `a_b6`, the analysis of step B6. The step runs the old read kernel at 8 MiB and at 1 MiB in one process with one thread, between reference intervals of `asmread` [Ref1]. |
| 368 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 369 | `    # first comparison: old read at 8 MiB in stable-low against stable-high processes on the same CPU` | Comment: the first comparison is old read at 8 MiB in the processes that stay low against the processes that stay high, on the same CPU. |
| 370 | `    state, detail = [], []` | `state`: one record per process for this comparison. `detail`: one record per process for the JSON file. |
| 371 | `    for p in used:` | Loop over the complete processes. |
| 372 | `        aa = [x['value'] for x in pair_values(p, 'oldread2', 'oldread')]` | `aa`: the values of the A/A pairs of the process: the rate of `oldread2` minus the rate of `oldread`, in GB/s (line 261). |
| 373 | `        refs = [iv.rate for iv in p.ordered if iv.entry == REF]` | `refs`: the rates of all reference intervals of the process. |
| 374 | `        pv = decide.process_value(refs, aa, aa, labelled=True)        # gives the label of the process, or None` | `pv`: used here only for the label of the process. It is `None` when the reference intervals are not all low or all high. |
| 375 | `        old = [iv.rate for iv in p.rate_by_entry.get('oldread', [])]` | `old`: the rates of all intervals of the entry `oldread`. This is the old read kernel at the size of `--bytes`, which is 8 MiB in this step. The intervals of `oldread@1M` are another entry and are not in this list. |
| 376 | `        if not aa or not old:` | Tests whether the process has no A/A pair or no interval of `oldread`. |
| 377 | `            detail.append(dict(file=p.file, tag=p.tag, used=False, reason='no old read interval or no A/A pair'))` | Then the process is recorded as not used, with the reason. |
| 378 | `            continue` | Goes on with the next process. |
| 379 | `        rec = dict(cpu=p.cpu, label=pv[0] if pv else 'changing', rate=median(old), e=median(aa))` | The record of the process: the CPU, the label (`low`, `high`, or `changing` for a process that is not stable), `rate` (the median of its `oldread` rates, in GB/s) and `e` (the median of its A/A values). |
| 380 | `        state.append(rec)` | Adds it to `state`. |
| 381 | `        detail.append(dict(file=p.file, tag=p.tag, used=True, **rec))` | Adds the same values with file and tag to `detail`. |
| 382 | `    st = decide.decide_b6_state(state) if state else {}` | `st`: the decision per CPU. `decide.decide_b6_state` needs at least 2 stable low and 2 stable high processes on one CPU. The difference is the median `rate` of the low processes minus that of the high processes. The A/A spread is the largest absolute `e` over all processes of the CPU. The difference is resolved when its absolute value is above the spread and every low value lies on one side of every high value [Ref4]. |
| 383 | `    out['state'] = {}` | `out['state']`: the results per CPU, empty at first. |
| 384 | `    rows = []` | `rows`: the table lines, empty at first. |
| 385 | `    for cpu, (word, diff) in st.items():` | Loop over the CPUs of the decision. |
| 386 | `        g = [x for x in state if x['cpu'] == cpu]` | `g`: the records of this CPU. |
| 387 | `        n = dict((lab, sum(1 for x in g if x['label'] == lab)) for lab in ('low', 'high', 'changing'))` | `n`: the number of its processes with the label `low`, `high` and `changing`. |
| 388 | `        spread = max(abs(x['e']) for x in g)` | `spread`: the A/A spread of the CPU in GB/s: the largest absolute `e` of all its processes. The processes that change level are included (point A15 of the deviations note [Ref3]). |
| 389 | `        note = 'value = median old read of the low processes minus that of the high processes'` | `note`: says what the value is: the median old read rate of the low processes minus that of the high processes. |
| 390 | `        if word == 'not observed':` | The CPU could not be decided. |
| 391 | `            note = 'Insufficient data: a CPU needs 2 stable low and 2 stable high processes; this CPU has %d low, %d high, %d changing' % (n['low'], n['high'], n['changing'])` | Then the note starts with `Insufficient data`, gives the rule of 2 stable low and 2 stable high processes, and gives the three counts of this CPU. |
| 392 | `        out['state'][cpu] = dict(decision=word, difference=diff, n_low=n['low'], n_high=n['high'], n_changing=n['changing'], aa_spread=spread, note=note)` | Stores the result of the CPU: the word, the difference, the three counts, the A/A spread and the note. |
| 393 | `        rows.append(row('B6 old read at 8 MiB, low against high, CPU %s' % cpu, word, '%d low, %d high' % (n['low'], n['high']), spread, diff, note))` | Adds one table line for the CPU. |
| 394 | `    out['state_processes'] = detail` | Stores the records per process. |
| 395 | `    # second comparison: old read at 8 MiB minus old read at 1 MiB, decided as B1 with the label "none"` | Comment: the second comparison is old read at 8 MiB minus old read at 1 MiB. It is decided as B1, with the label `none`. |
| 396 | `    res, detail2, _ = one_thread_group(used, 'oldread', 'oldread@1M', 'oldread2', 'oldread', labelled=False)` | Decides it with `one_thread_group` (line 276). The kernel pair is `oldread` minus `oldread@1M`. The A/A pair is `oldread2` minus `oldread`. No level label is used, so every complete process counts. |
| 397 | `    out['size'] = dict(kernel_pair='oldread - oldread@1M', aa_pair='oldread2 - oldread', labels=res, processes=detail2)` | Stores the result of the second comparison under `size`. |
| 398 | `    out['rows'] = rows + group_rows('B6 (oldread - oldread@1M)', res)` | The table lines of the step: those of the first comparison, then those of the second. |
| 399 | `    return out` | Returns the report of the step. |
| 402 | `def coverage(p_row):` | Starts the function `coverage`. It turns one `P` row into a word for the share of the buffer that lies on huge pages. |
| 403 | `    if p_row is None or p_row['kB_total'] is None or p_row['kB_huge'] is None:` | Tests whether the row is missing, or one of its two sizes is `NA`. |
| 404 | `        return 'unknown'` | Then the coverage is `unknown`. |
| 405 | `    return 'full' if p_row['kB_huge'] == p_row['kB_total'] else 'none' if p_row['kB_huge'] == 0 else 'partial'` | `full` when `kB_huge` equals `kB_total`, `none` when `kB_huge` is 0, and `partial` for every value between. |

### Function `a_b4`: step B4, intervals per level and coverage (lines 408 to 442)

| Line | Source | Explanation |
|---:|---|---|
| 408 | `def a_b4(procs, ctx, step):` | Starts the function `a_b4`, the analysis of step B4. The step runs `asmread` alone at 8 MiB for 200 rounds with one thread. Half of its processes run with `--no-thp` [Ref1]. |
| 409 | `    """B4: every interval has the label of its own rate. Counts of intervals per CPU, label and coverage."""` | Docstring: every interval has the label of its own rate. The function counts the intervals per CPU, per label and per coverage. |
| 410 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 411 | `    out['per_cpu'], rows = {}, []` | `out['per_cpu']`: the results per CPU. `rows`: the table lines. Both are empty at first. |
| 412 | `    for cpu in sorted({p.cpu for p in used}):` | Loop over the CPUs of the complete processes, in rising order. |
| 413 | `        counts, changes, no_sign = {}, 0, 0` | `counts`: the number of intervals per pair of label and coverage. `changes`: the number of level changes. `no_sign`: the number of level changes without a sign of a page change. All start empty or at 0. |
| 414 | `        g = [p for p in used if p.cpu == cpu]` | `g`: the complete processes of this CPU, with and without `--no-thp`. |
| 415 | `        for p in g:` | Loop over these processes. |
| 416 | `            prev = None` | `prev`: the last interval of this process that was low or high. It is `None` at the start of each process. So no change is counted from one process to the next. |
| 417 | `            for iv in p.ordered:` | Loop over the intervals of the process in time order. |
| 418 | `                pr = p.page_before(iv)` | `pr`: the `P` row that the runner read before this interval (line 187). |
| 419 | `                cur = (decide.level(iv.rate), coverage(pr), pr)` | `cur`: the level of the rate of this interval (line 257), the coverage of its `P` row (line 402) and the row itself. |
| 420 | `                counts[(cur[0], cur[1])] = counts.get((cur[0], cur[1]), 0) + 1` | Counts the interval under its pair of level and coverage. |
| 421 | `                if prev and {prev[0], cur[0]} == {'low', 'high'}:` | Tests for a level change: the last low or high interval and this interval have the two different labels `low` and `high`. |
| 422 | `                    changes += 1` | Counts the level change. |
| 423 | `                    a, b = prev[2], cur[2]` | `a` and `b`: the `P` row before the earlier interval and the `P` row before this one. |
| 424 | `                    if a and b and prev[1] == cur[1] != 'unknown' and a['thp_collapse_alloc'] == b['thp_collapse_alloc'] \` | Tests for "no sign of a page change": both rows exist, both intervals have the same coverage and it is not `unknown`, and the counter `thp_collapse_alloc` has the same value in both rows. The condition goes on in line 425. |
| 425 | `                            and a['pgmigrate_success'] == b['pgmigrate_success'] and a['thp_collapse_alloc'] is not None:` | Continues line 424: the counter `pgmigrate_success` also has the same value in both rows, and `thp_collapse_alloc` is not `NA`. Both counters count for the whole system, not for this buffer [Ref1]. |
| 426 | `                        no_sign += 1` | Counts the change as one without a sign of a page change. By the plan this is a description. It is no proof that the physical pages stayed the same [Ref2]. |
| 427 | `                if cur[0] != 'changing':` | Only a low or a high interval. |
| 428 | `                    prev = cur` | It becomes the earlier interval for the next test. A changing interval is skipped. |
| 429 | `        n = lambda lab, cov: counts.get((lab, cov), 0)` | `n`: a small function that gives the count for a label and a coverage, or 0 when there is none. |
| 430 | `        cases = [c for c, cov in (('a', 'full'), ('b', 'none')) if n('low', cov) >= B4_MIN_INTERVALS and n('high', cov) >= B4_MIN_INTERVALS]` | `cases`: the cases that contradict hypothesis H3a on this CPU. H3a predicts that low intervals have less than full coverage and high intervals have full coverage [Ref1]. Case `a`: at least 10 low and at least 10 high intervals with full coverage. Case `b`: at least 10 low and at least 10 high intervals with coverage none. The counts run over all complete processes of the CPU in this session (point A12 of the deviations note, which asks for a check by the lead [Ref3]). |
| 431 | `        word = 'contradicts H3a (case %s)' % ' and '.join(cases) if cases else 'not observed'` | `word`: `contradicts H3a` with the cases found, or `not observed` without a case. |
| 432 | `        table = {lab: {cov: n(lab, cov) for cov in ('full', 'partial', 'none', 'unknown')} for lab in ('low', 'changing', 'high')}` | `table`: the counts for each of the three labels and each of the four coverage words. |
| 433 | `        note = 'intervals low/high with full coverage %d/%d, with coverage none %d/%d; a case needs 10 and 10' % (` | `note`: the four counts that decide the cases, and the rule that a case needs 10 and 10. The text goes on in line 434. |
| 434 | `            n('low', 'full'), n('high', 'full'), n('low', 'none'), n('high', 'none'))` | Continues line 433: the values of the note: the low count and the high count with full coverage, then the two with coverage none. |
| 435 | `        out['per_cpu'][cpu] = dict(decision=word, cases=cases, intervals=table, n_processes=len(g),` | Stores the result of the CPU: the word, the cases, the table and the number of processes. The record goes on in lines 436 to 437. |
| 436 | `                                   n_processes_no_thp=sum(1 for p in g if p.no_thp),` | Continues the record: the number of processes with `--no-thp`. |
| 437 | `                                   level_changes_low_high=changes, level_changes_with_no_sign_of_a_page_change=no_sign, note=note)` | Continues the record: the number of level changes between low and high, the number of them without a sign of a page change, and the note. |
| 438 | `        rows.append(row('B4 CPU %s, H3a' % cpu, word, len(g), None, None, note + '; B4 has no A/A pair'))` | Adds one table line for the CPU. It has no A/A spread and no value. The note adds that B4 has no A/A pair. |
| 439 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 440 | `    return out` | Returns the report of the step. |

### `METRICS`, `diff_value` and `setting_values`: `D` and `E` of one process (lines 443 to 479)

| Line | Source | Explanation |
|---:|---|---|
| 443 | `# ---------------------------------------------------------------- steps with many threads` | Comment: a divider. The analysis of the steps with many threads starts here. |
| 445 | `METRICS = (('M_hist', lambda iv: iv.hist), ('M_sum', lambda iv: iv.msum),` | `METRICS`: four named values of an interval, each with a small function that reads it from an interval: `M_hist` (line 75) and `M_sum` (line 76). The list goes on in line 446. |
| 446 | `           ('M_hist_mesh0', lambda iv: iv.mesh_hist[0]), ('M_hist_mesh1', lambda iv: iv.mesh_hist[1]))` | Continues line 445: `M_hist_mesh0` and `M_hist_mesh1`, the `M_hist` values of the threads of mesh 0 and of mesh 1 (line 78). |
| 449 | `def diff_value(p, a, b, key):` | Starts the function `diff_value`. It gives one difference per process. `a` and `b` are two entries of the sequence. `key` is the function that reads one value of an interval. |
| 450 | `    """One process: the mean over its rounds of (mean of the intervals of entry a minus mean of those of b).` | Docstring: the value is the mean over the rounds of the process. In each round it is the mean over the intervals of entry `a` minus the mean over the intervals of entry `b`. |
| 451 | `    No value if an interval that it needs is irregular."""` | Docstring: the process gives no value when an interval that the value needs is irregular. |
| 452 | `    vals = []` | `vals`: one difference per round, empty at first. |
| 453 | `    for r in range(p.rounds):` | Loop over the rounds of the process. |
| 454 | `        ia = [p.iv[(r, i)] for i, e in enumerate(p.seq) if e == a]` | `ia`: the intervals of this round whose entry is `a`. |
| 455 | `        ib = [p.iv[(r, i)] for i, e in enumerate(p.seq) if e == b]` | `ib`: the intervals of this round whose entry is `b`. |
| 456 | `        if not ia or not ib:` | Tests whether the sequence holds none of one of them. |
| 457 | `            return None, 'the sequence has no %s or no %s' % (a, b)` | Then the function returns no value, and the reason. |
| 458 | `        bad = [iv for iv in ia + ib if iv.irregular]` | `bad`: the irregular intervals among them. |
| 459 | `        if bad:` | Tests whether there is one. |
| 460 | `            return None, 'irregular interval (round %d pos %d)' % (bad[0].round, bad[0].pos)` | Then the function returns no value, and the reason names the first irregular interval. So one irregular interval removes the value of the whole process (point A6 of the deviations note, which needs a decision of the lead [Ref3]). |
| 461 | `        vals.append(mean(key(iv) for iv in ia) - mean(key(iv) for iv in ib))` | Adds the difference of this round: the mean of `key` over `ia` minus the mean of `key` over `ib`. In the sequence of step B7 each kernel stands twice per round, so each mean is over 2 intervals. |
| 462 | `    return mean(vals), None` | Returns the mean of the differences of all rounds, and no reason. |
| 465 | `def setting_values(procs, a, b, aa2, aa):` | Starts the function `setting_values`. It computes `D` and `E` of every process of one setting, for each of the four metrics. `a` and `b` name the kernel pair. `aa2` and `aa` name the A/A pair. |
| 466 | `    """-> {metric: [dict(D, E, tag)]} and the processes without a value."""` | Docstring: the first result maps each metric to a list of records with `D`, `E` and the tag. The second result lists the processes without a value. |
| 467 | `    vals, missing = {m: [] for m, _ in METRICS}, []` | `vals`: an empty list per metric. `missing`: the processes without a value, empty at first. |
| 468 | `    for p in procs:` | Loop over the processes. |
| 469 | `        for m, key in METRICS:` | Loop over the four metrics of line 445. |
| 470 | `            D, why = diff_value(p, a, b, key)` | `D`: the difference `a` minus `b` of the process in this metric (line 449), in GB/s. `why` is the reason when there is no value. |
| 471 | `            E, why2 = diff_value(p, aa2, aa, key)` | `E`: the A/A difference `aa2` minus `aa` of the same process in the same metric. |
| 472 | `            if D is None or E is None:` | Tests whether one of the two is missing. |
| 473 | `                if m == 'M_hist':` | The process is listed as missing once, at the metric `M_hist`. The other metrics miss the same processes: the tests of line 456 and line 458 do not depend on the metric. |
| 474 | `                    missing.append(dict(file=p.file, tag=p.tag, reason=why or why2))` | The record names the file, the tag and the reason. |
| 475 | `                continue` | Goes on with the next metric. The process gets no value in this metric. |
| 476 | `            vals[m].append(dict(D=D, E=E, tag=p.tag))` | Adds the pair of `D` and `E`, with the tag of the process. |
| 477 | `    return vals, missing` | Returns the values per metric and the list of the missing processes. |

### `both_metrics`, `decide_d` and `factor_pairs`: the decision for one setting (lines 480 to 517)

| Line | Source | Explanation |
|---:|---|---|
| 480 | `def both_metrics(by_metric):` | Starts the function `both_metrics`. It joins the decisions that the two metrics `M_hist` and `M_sum` gave for one quantity. |
| 481 | `    """The decision metric is M_hist. If M_sum gives another word or another sign, the result is 'not resolved'."""` | Docstring: the decision metric is `M_hist`. When `M_sum` gives another word or another sign, the result is `not resolved`. |
| 482 | `    h, s = by_metric['M_hist'], by_metric['M_sum']` | `h`: the decision with `M_hist`. `s`: the decision with `M_sum`. |
| 483 | `    if (h['decision'], h.get('sign')) == (s['decision'], s.get('sign')):` | Tests whether the word and the sign are equal in both. A decision that has no field `sign` counts as a sign of `None`. |
| 484 | `        return h['decision'], h.get('sign'), ''` | Then the result is the word and the sign of `M_hist`, with an empty note. |
| 485 | `    return 'not resolved', None, 'M_hist gives "%s%s" and M_sum gives "%s%s": reported as not resolved' % (` | If not, the result is `not resolved` without a sign. The note quotes the two decisions and says that the result is reported as not resolved. The text goes on in line 486. |
| 486 | `        h['decision'], sign_txt(h.get('sign')), s['decision'], sign_txt(s.get('sign')))` | Continues line 485: the values of the note: the two words with their signs. |
| 489 | `def decide_d(vals, missing, min_n=4):` | Starts the function `decide_d`. It decides `D` of one setting from the values of line 465. A decision needs at least 4 processes unless the caller gives another `min_n`. |
| 490 | `    by = {}` | `by`: the decision per metric, empty at first. |
| 491 | `    for m, pl in vals.items():` | Loop over the four metrics. `pl` is the list of the records of one metric. |
| 492 | `        word, sign = decide.decide_setting(pl, min_n)` | `decide.decide_setting`: with fewer than 4 processes the word is `not observed`. `D` is resolved when the absolute median of the `D` values is above the A/A spread and all `D` have one sign. The A/A spread is the largest absolute `E`. The sign is 1 for a positive median and -1 for a negative one [Ref4]. |
| 493 | `        by[m] = dict(decision=word, sign=sign, n_processes=len(pl), median_D=med([x['D'] for x in pl]),` | Stores for the metric: the word, the sign, the number of processes and the median of `D` in GB/s. The record goes on in line 494. |
| 494 | `                     aa_spread=max((abs(x['E']) for x in pl), default=None), D=[x['D'] for x in pl], E=[x['E'] for x in pl])` | Continues line 493: the A/A spread (the largest absolute `E`, or `None` without a process) and the lists of all `D` and all `E`. |
| 495 | `    word, sign, note = both_metrics(by)` | Joins the decisions of `M_hist` and `M_sum` (line 480). The two mesh metrics are not used for the decision. They are reported as a description (line 532). |
| 496 | `    disagree = bool(note)                                       # M_hist and M_sum give another word or sign` | `disagree`: true when line 495 gave a note. By the comment this means that `M_hist` and `M_sum` gave another word or another sign. |
| 497 | `    if word == 'not observed':` | The setting has too few processes with a value. |
| 498 | `        note = '%d processes with a value, %d needed' % (by['M_hist']['n_processes'], min_n) + \` | Then the note gives the number of processes with a value and the number needed. The text goes on in line 499. |
| 499 | `               (''.join('; %s has no value: %s' % (x['tag'], x['reason']) for x in missing))` | Continues line 498: for every missing process, its tag and the reason (line 474). |
| 500 | `    return dict(decision=word, sign=sign, note=note, metrics=by, metrics_disagree=disagree, processes_without_value=missing)` | Returns the decision: the word, the sign, the note, the decisions per metric, `metrics_disagree` and the list of the missing processes. |
| 503 | `def factor_pairs(settings):` | Starts the function `factor_pairs`. `settings` is a list of setting names such as `pass/500/common`. |
| 504 | `    """Pairs of settings (stop/min_ms/start) that differ in exactly one factor. The first of a pair is the one with` | Docstring: it gives the pairs of settings that differ in exactly one of the three factors. The docstring goes on in line 505. |
| 505 | `    pass, the shorter interval, or the common start."""` | Docstring: the first setting of a pair is the one with `pass`, with the shorter interval, or with the common start. |
| 506 | `    names = ('stop', 'interval', 'start')` | `names`: the names of the three factors in the order of the setting text: `stop`, `interval` and `start`. |
| 507 | `    order = lambda i, v: int(v) if i == 1 else int(v != ('pass', None, 'common')[i])` | `order`: a small function that gives a rank to a value of factor `i`. For the interval (factor 1) the rank is the number of ms. For the stop method the rank is 0 for `pass` and 1 for any other word. For the start the rank is 0 for `common` and 1 for any other word. |
| 508 | `    out = []` | `out`: the pairs, empty at first. |
| 509 | `    for x in settings:` | Loop over the settings as the first setting `x`. |
| 510 | `        for y in settings:` | Loop over the settings as the second setting `y`. |
| 511 | `            fx, fy = x.split('/'), y.split('/')` | `fx` and `fy`: the three parts of each setting. |
| 512 | `            d = [i for i in range(3) if fx[i] != fy[i]]` | `d`: the numbers of the factors in which the two settings differ. |
| 513 | `            if len(d) == 1 and order(d[0], fx[d[0]]) < order(d[0], fy[d[0]]):` | A pair counts when exactly one factor differs and `x` has the lower rank in it. So each two settings give at most one pair, in a fixed order. |
| 514 | `                out.append((names[d[0]], x, y))` | Adds the name of the factor, the first setting and the second setting. |
| 515 | `    return sorted(out)` | Returns the pairs, sorted by factor name and then by the setting names. |

### Function `a_b7`: step B7, the read difference `D` per setting (lines 518 to 559)

| Line | Source | Explanation |
|---:|---|---|
| 518 | `def a_b7(procs, ctx, step):` | Starts the function `a_b7`, the analysis of step B7. The step runs the old read kernel, the new read kernel and the A/A pair `asmread` and `asmread2` with 120 threads, in the 8 combinations of stop method, interval length and start method [Ref1]. |
| 519 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 520 | `    main = [p for p in used if len(p.seq) > 1]` | `main`: the processes whose sequence has more than one entry. In them the kernels alternate inside one process. |
| 521 | `    single = [p for p in used if len(p.seq) == 1]` | `single`: the processes with one entry. Each of them runs one kernel alone. |
| 522 | `    out['settings'], rows, vals = {}, [], {}` | `out['settings']`: the results per setting. `rows`: the table lines. `vals`: the values per setting. All are empty at first. |
| 523 | `    for s in sorted({p.setting for p in main}):` | Loop over the settings of the `main` processes, sorted by name. |
| 524 | `        g = [p for p in main if p.setting == s]` | `g`: the processes of this setting. |
| 525 | `        vals[s], missing = setting_values(g, 'oldread', 'read', 'asmread2', 'asmread')` | Computes `D` and `E` for each process (line 465). `D` is `oldread` minus `read`, the old read kernel minus the new one. `E` is `asmread2` minus `asmread`. Both are differences of total rates in GB/s. |
| 526 | `        d = decide_d(vals[s], missing)` | Decides `D` of the setting (line 489). |
| 527 | `        h = d['metrics']['M_hist']` | `h`: the decision with the metric `M_hist`. |
| 528 | `        out['settings'][s] = d` | Stores the decision of the setting. |
| 529 | `        rows.append(row('B7 %s: D = oldread - read (M_hist)' % s, d['decision'] + sign_txt(d['sign']), h['n_processes'], h['aa_spread'], h['median_D'], d['note']))` | Adds the main table line of the setting: the word with its sign, the number of processes, the A/A spread and the median of `D`, all with `M_hist`. |
| 530 | `        for m in ('M_sum', 'M_hist_mesh0', 'M_hist_mesh1'):` | Loop over the three other metrics. |
| 531 | `            x = d['metrics'][m]` | `x`: the decision with this metric. |
| 532 | `            rows.append(row('B7 %s: D with %s (description)' % (s, m), x['decision'] + sign_txt(x['sign']), x['n_processes'], x['aa_spread'], x['median_D']))` | Adds one table line that is marked as a description: the same columns with `M_sum`, with the `M_hist` of mesh 0 and with the `M_hist` of mesh 1. |
| 533 | `    rep = out['settings'].get('pass/500/common')` | `rep`: the decision of the setting `pass/500/common`, or `None`. The plan calls this setting the reproduction condition: whole passes, 0.5 s and the common start, which is the timing method of the benchmark `bandwidth.c` [Ref2]. |
| 534 | `    out['reproduction_in_one_process'] = 'not observed' if not rep else \` | `reproduction_in_one_process`: `not observed` when no process has this setting. The other cases follow in line 535. |
| 535 | `        'reproduced' if rep['decision'] == 'resolved' and rep['sign'] == 1 else 'not reproduced (D is %s%s)' % (rep['decision'], sign_txt(rep['sign']))` | Continues line 534: `reproduced` when `D` is resolved there with a positive sign. A positive sign means old read above new read. Every other case is `not reproduced`, with the word and the sign that were found. |
| 536 | `    out['changes'] = {}` | `out['changes']`: the changes of `D` between settings, empty at first. |
| 537 | `    for factor, x, y in factor_pairs(list(vals)):` | Loop over the pairs of settings that differ in exactly one factor (line 503). |
| 538 | `        by = {}` | `by`: the decision per metric, empty at first. |
| 539 | `        for m in ('M_hist', 'M_sum'):` | Loop over `M_hist` and `M_sum`. |
| 540 | `            word, change = decide.decide_change(vals[x][m], vals[y][m])` | `decide.decide_change` with at least 4 processes per setting. The change is the median `D` of the first setting minus the median `D` of the second, in GB/s. It is resolved when its absolute value is above the sum of the two A/A spreads and every `D` of one setting lies on one side of every `D` of the other [Ref4]. |
| 541 | `            spread = None if change is None else max(abs(v['E']) for v in vals[x][m]) + max(abs(v['E']) for v in vals[y][m])` | `spread`: the sum of the two A/A spreads in GB/s: the largest absolute `E` of each setting. It is `None` when no change was computed. |
| 542 | `            by[m] = dict(decision=word, change=change, sum_of_aa_spreads=spread, n_first=len(vals[x][m]), n_second=len(vals[y][m]))` | Stores for the metric: the word, the change, the sum of the A/A spreads and the two process counts. |
| 543 | `        word, _, note = both_metrics(by)` | Joins the two metrics (line 480). These records hold no field `sign`. So only the words are compared here: two resolved changes of opposite direction would count as agreement. |
| 544 | `        disagree = bool(note)` | `disagree`: true when line 543 gave a note. |
| 545 | `        if word == 'not observed':` | A setting of the pair has too few processes. |
| 546 | `            note = 'a setting has fewer than 4 processes with a value'` | Then the note says that a setting has fewer than 4 processes with a value. |
| 547 | `        h = by['M_hist']` | `h`: the values with `M_hist`. |
| 548 | `        out['changes']['%s: %s -> %s' % (factor, x, y)] = dict(factor=factor, first=x, second=y, decision=word, note=note, metrics=by,` | Stores the change under a key that names the factor and the two settings. The record holds the factor, the settings, the word, the note and the values per metric. It goes on in line 549. |
| 549 | `                                                              metrics_disagree=disagree)` | Continues line 548: `metrics_disagree`. |
| 550 | `        rows.append(row('B7 change of D, %s: %s minus %s' % (factor, x, y), word, '%d and %d' % (h['n_first'], h['n_second']),` | Adds one table line for the change: the factor and the two settings, the word and the two process counts. The call goes on in line 551. |
| 551 | `                        h['sum_of_aa_spreads'], h['change'], note or 'A/A value = sum of the two A/A spreads'))` | Continues line 550: the sum of the A/A spreads and the change with `M_hist`, then the note. Without a note the line says that the A/A value is the sum of the two A/A spreads. |
| 552 | `    out['single_kernel'] = sk = single_kernel(single, rows)` | `single_kernel`: the decision for the processes with one kernel each (line 560). The function also adds its table line to `rows`. |
| 553 | `    # Plan, step B7: without a resolved D of the sign of 2026-11-13 in either way of running, no cause is assigned.` | Comment: by step B7 of the plan no cause is assigned unless `D` is resolved with the sign of 2026-11-13 in one of the two ways of running. |
| 554 | `    out['reproduced_in_either_way'] = bool((rep and rep['decision'] == 'resolved' and rep['sign'] == 1) or` | `reproduced_in_either_way`: true when `D` is resolved with a positive sign in the setting `pass/500/common` with the kernels in one process. The second case follows in line 555. |
| 555 | `                                           (sk['decision'] == 'resolved' and sk.get('sign') == 1))` | Continues line 554: or when the decision with one kernel per process is resolved with a positive sign. `cross` uses this value for the hypotheses H7a and H7b (line 942). |
| 556 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 557 | `    return out` | Returns the report of the step. |

### Function `single_kernel`: step B7 with one kernel per process (lines 560 to 598)

| Line | Source | Explanation |
|---:|---|---|
| 560 | `def single_kernel(single, rows):` | Starts the function `single_kernel`. `single` holds the processes of step B7 that run one kernel each. `rows` is the list of the table lines of the step. |
| 561 | `    """B7 with one kernel per process (local rule, B.10): process value = median of its intervals.` | Docstring: a local rule, taken from section B.10 of the handoff note. The process value is the median of the intervals of the process. |
| 562 | `    D = median of the process values of oldread minus that of read. A/A value = \|median asmread2 - median asmread\|.` | Docstring: `D` is the median of the process values of `oldread` minus the median of those of `read`. The A/A value is the absolute difference between the median of `asmread2` and the median of `asmread`. |
| 563 | `    Resolved if \|D\| is above the A/A value and every value of one kernel lies on one side of every value of the other.` | Docstring: `D` is resolved when its absolute value is above the A/A value and every value of one kernel lies on one side of every value of the other. |
| 564 | `    The decision metric is M_hist. The same rule is applied with M_sum, and another word or sign gives "not resolved"."""` | Docstring: the decision metric is `M_hist`. The same rule is applied with `M_sum`. Another word or another sign there gives `not resolved`. |
| 565 | `    keys = dict(M_hist=lambda iv: iv.hist, M_sum=lambda iv: iv.msum)` | `keys`: the two metrics, each with the function that reads it from an interval. |
| 566 | `    pv, left = {m: {} for m in keys}, []` | `pv`: per metric, the process values by kernel, empty at first. `left`: the processes without a value. |
| 567 | `    for p in single:` | Loop over the processes with one kernel. The function does not test their setting. |
| 568 | `        if any(iv.irregular for iv in p.ordered):` | Tests whether the process has an irregular interval. |
| 569 | `            left.append(dict(file=p.file, tag=p.tag, reason='irregular interval'))` | Then it is listed as left out, with the reason. |
| 570 | `            continue` | Goes on with the next process. |
| 571 | `        for m, key in keys.items():` | Loop over the two metrics. |
| 572 | `            pv[m].setdefault(p.seq[0], []).append(median(key(iv) for iv in p.ordered))` | Adds the process value to the list of the kernel of the process: the median of the metric over all intervals of the process. The kernel is the one entry of its sequence. |
| 573 | `    n = {k: len(pv['M_hist'].get(k, [])) for k in ('oldread', 'read', 'asmread', 'asmread2')}` | `n`: the number of processes with a value for each of the four kernels `oldread`, `read`, `asmread` and `asmread2`. |
| 574 | `    res = dict(process_values=pv['M_hist'], process_values_M_sum=pv['M_sum'], n_processes=n, processes_without_value=left)` | Starts the result: the process values with `M_hist`, those with `M_sum`, the four counts and the processes left out. |
| 575 | `    if not single:` | The input has no process with one kernel. |
| 576 | `        return dict(decision='not observed', note='no process with one kernel in the input')` | Then the result is `not observed` with a note. No table line is added. |
| 577 | `    if min(n.values()) < 4:` | At least one of the four kernels has fewer than 4 processes with a value. |
| 578 | `        res.update(decision='not observed', sign=None, D=None, aa_value=None,` | Then the word is `not observed`, without `D` and without an A/A value. The call goes on in line 579. |
| 579 | `                   note='4 processes of each kernel are needed; found ' + ', '.join('%s: %d' % kv for kv in n.items()))` | Continues line 578: the note says that 4 processes of each kernel are needed, and gives the count found per kernel. |
| 580 | `    else:` | Every kernel has at least 4 processes. |
| 581 | `        by = {}` | `by`: the decision per metric, empty at first. |
| 582 | `        for m, v in pv.items():` | Loop over the two metrics. `v` holds the process values by kernel. |
| 583 | `            o, r = v['oldread'], v['read']` | `o`: the process values of `oldread`. `r`: those of `read`. |
| 584 | `            D = median(o) - median(r)` | `D`: the median of `o` minus the median of `r`, in GB/s. |
| 585 | `            aa = abs(median(v['asmread2']) - median(v['asmread']))` | `aa`: the A/A value in GB/s: the absolute difference between the median process value of `asmread2` and that of `asmread`. |
| 586 | `            sep = max(o) < min(r) or min(o) > max(r)` | `sep`: true when the two sets do not overlap: every value of `oldread` is below every value of `read`, or every one is above. |
| 587 | `            ok = abs(D) > aa and sep` | `ok`: true when the absolute `D` is above the A/A value and the two sets do not overlap. |
| 588 | `            by[m] = dict(decision='resolved' if ok else 'not resolved', sign=(1 if D > 0 else -1) if ok else None, D=D, aa_value=aa)` | Stores for the metric: `resolved` or `not resolved`, the sign of `D` when it is resolved (1 for old read above new read, -1 for below), `D` and the A/A value. |
| 589 | `        word, sign, note = both_metrics(by)` | Joins the two metrics (line 480). These records hold a sign, so the word and the sign are compared. |
| 590 | `        if note:` | The two metrics disagree. |
| 591 | `            note += '; M_sum: D %s GB/s, A/A value %s GB/s' % (fmt(by['M_sum']['D']), fmt(by['M_sum']['aa_value']))` | Then the note also gives `D` and the A/A value with `M_sum`, in GB/s. |
| 592 | `        res.update(decision=word, sign=sign, D=by['M_hist']['D'], aa_value=by['M_hist']['aa_value'], note=note, metrics=by,` | Stores the word and the sign, and `D` and the A/A value with `M_hist`. The call goes on in line 593. |
| 593 | `                   metrics_disagree=bool(note))` | Continues line 592: the decisions per metric, and `metrics_disagree`. |
| 594 | `    rows.append(row('B7 pass/500/common, one kernel per process: D (M_hist)', res['decision'] + sign_txt(res['sign']),` | Adds the table line of this way of running. Its label names the setting `pass/500/common`. The call goes on in line 595. |
| 595 | `                    'per kernel: ' + '/'.join(str(v) for v in n.values()), res['aa_value'], res['D'], res['note']))` | Continues line 594: the process counts of the four kernels, the A/A value, `D` and the note. |
| 596 | `    return res` | Returns the result. |

### `a_b10`: step B10, the spread of each write kernel and the controls (lines 599 to 630)

| Line | Source | Explanation |
|---:|---|---|
| 599 | `def a_b10(procs, ctx, step):` | Starts the function `a_b10`, the analysis of step B10. The step runs four write kernels with 120 threads: `oldwrite`, `write` and the A/A pair `asmwrite` and `asmwrite2`. It uses the 8 combinations of stop method, interval length and start method [Ref1]. |
| 600 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 601 | `    kernels = ('oldwrite', 'write', 'asmwrite', 'asmwrite2')` | `kernels`: the four kernel names of the step. |
| 602 | `    out['settings'], rows, spreads = {}, [], {}` | `out['settings']`: the results per setting. `rows`: the table lines. `spreads`: the spread values per setting. All are empty at first. |
| 603 | `    for s in sorted({p.setting for p in used}):` | Loop over the settings, sorted by name. |
| 604 | `        g = [p for p in used if p.setting == s]` | `g`: the processes of this setting. |
| 605 | `        per_proc, aa_iv, missing = [], [], []` | `per_proc`: one record per process. `aa_iv`: the pairs of neighbouring A/A intervals. `missing`: the kernels of a process that give no value. |
| 606 | `        for p in g:` | Loop over the processes. |
| 607 | `            rec = dict(tag=p.tag)` | `rec`: the record of the process, with its tag. |
| 608 | `            for k in kernels:` | Loop over the four kernels. |
| 609 | `                ivs = p.rate_by_entry.get(k, [])` | `ivs`: the intervals of this kernel in the process, in time order. |
| 610 | `                if not ivs or any(iv.irregular for iv in ivs):` | Tests whether the process has no interval of the kernel, or an irregular one. |
| 611 | `                    missing.append(dict(file=p.file, tag=p.tag, kernel=k, reason='irregular interval' if ivs else 'kernel not in the sequence'))` | Then the kernel is listed as missing for this process, with the reason. |
| 612 | `                    continue` | Goes on with the next kernel. |
| 613 | `                hi, lo = max(ivs, key=lambda iv: iv.hist), min(ivs, key=lambda iv: iv.hist)` | `hi`: the interval with the highest `M_hist` among them. `lo`: the interval with the lowest. |
| 614 | `                rec[k] = dict(spread=hi.hist - lo.hist, median_total=median(iv.hist for iv in ivs), median_total_M_sum=median(iv.msum for iv in ivs),` | Stores for the kernel: `spread`, the highest minus the lowest `M_hist` in GB/s. This is the process value of the kernel. Then the median of `M_hist` and the median of `M_sum` over its intervals. The record goes on in line 615. |
| 615 | `                              hi=hi.mesh_hist, lo=lo.mesh_hist)` | Continues line 614: the `M_hist` values per mesh of the interval with the highest total and of the interval with the lowest total. |
| 616 | `            per_proc.append(rec)` | Adds the record of the process. |
| 617 | `            for r in range(p.rounds):                          # neighbouring intervals of the A/A pair` | Loop over the rounds. By the comment the next lines look for neighbouring intervals of the A/A pair. |
| 618 | `                for i in range(len(p.seq) - 1):` | Loop over each two positions of the sequence that follow each other. |
| 619 | `                    if {p.seq[i], p.seq[i + 1]} == {'asmwrite', 'asmwrite2'}:` | Tests whether the two entries are `asmwrite` and `asmwrite2`, in any order. |
| 620 | `                        x, y = p.iv[(r, i)], p.iv[(r, i + 1)]` | `x` and `y`: the two intervals. |
| 621 | `                        if not (x.irregular or y.irregular):` | Only when neither of them is irregular. |
| 622 | `                            a, a2 = (x, y) if x.entry == 'asmwrite' else (y, x)` | `a`: the interval of `asmwrite`. `a2`: the interval of `asmwrite2`. |
| 623 | `                            aa_iv.append((a.mesh_hist, a2.mesh_hist))` | Adds the pair of their `M_hist` values per mesh. |
| 624 | `        both = [r for r in per_proc if 'asmwrite' in r and 'asmwrite2' in r]` | `both`: the processes that have a spread for `asmwrite` and for `asmwrite2`. |
| 625 | `        for r in both:` | Loop over them. |
| 626 | `            r['E'] = r['asmwrite2']['spread'] - r['asmwrite']['spread']` | `E`: the A/A value of the spread for this process: the spread of `asmwrite2` minus the spread of `asmwrite`, in GB/s. |
| 627 | `        ctrl_spread = max((abs(r['E']) for r in both), default=None)` | `ctrl_spread`: the control of the spread: the largest absolute `E` of the setting, or `None` without such a process. |
| 628 | `        ctrl_total, ctrl_mesh = decide.controls_from_aa(aa_iv) if aa_iv else (None, (None, None))` | `ctrl_total` and `ctrl_mesh`: the control of the total rate and the controls of the rate of each mesh. `decide.controls_from_aa` takes the largest absolute difference between the two copies over the pairs of line 623: once for the sum of the two meshes, once for mesh 0 and once for mesh 1 [Ref4]. Without a pair all three are `None`. |
| 629 | `        res = dict(n_processes=len(g), control_spread=ctrl_spread, control_total=ctrl_total, control_mesh0=ctrl_mesh[0], control_mesh1=ctrl_mesh[1],` | Starts the result of the setting: the number of processes and the four controls. The record goes on in line 630. |
| 630 | `                   n_aa_interval_pairs=len(aa_iv), values_missing=missing, kernels={})` | Continues line 629: the number of A/A interval pairs, the list of the missing values and an empty dictionary for the kernels. |

### `a_b10`: hypothesis H11 per kernel, and the change of the spread (lines 631 to 664)

| Line | Source | Explanation |
|---:|---|---|
| 631 | `        spreads[s] = {}` | `spreads[s]`: the spread values of this setting per kernel, empty at first. |
| 632 | `        for k in kernels:` | Loop over the four kernels. |
| 633 | `            pk = [r for r in per_proc if k in r]` | `pk`: the processes that have a value for this kernel. |
| 634 | `            spreads[s][k] = [dict(D=r[k]['spread'], E=r['E']) for r in pk if 'E' in r]` | The values for the change of the spread: per process, `D` is the spread of the kernel and `E` is the A/A value of line 626. A process without `E` is left out. |
| 635 | `            h11p = [dict(hi=r[k]['hi'], lo=r[k]['lo']) for r in pk]` | `h11p`: per process, the `M_hist` values per mesh of its interval with the highest total (`hi`) and of its interval with the lowest total (`lo`). |
| 636 | `            if ctrl_total is None:` | The setting has no control. |
| 637 | `                h11, note = 'not observed', 'no regular neighbouring A/A intervals, so no control'` | Then the word for H11 is `not observed`, with the note that no regular neighbouring A/A intervals exist. |
| 638 | `            else:` | The setting has controls. |
| 639 | `                h11, note = decide.decide_h11(h11p, ctrl_total, ctrl_mesh), ''` | `decide.decide_h11` gives the word for hypothesis H11: in an interval with a higher total one mesh is faster and the other is not. A process counts only when its highest total is above its lowest total by more than the control of the total. A mesh has changed when its rate differs between the two intervals by more than the control of that mesh. `supported`: in every counted process exactly one mesh changed, it got faster, and it is the same mesh in all. `contradicted`: in every counted process both meshes changed in the same direction. Fewer than 2 counted processes give `not observed`. The rest is `not resolved` [Ref4]. |
| 640 | `            res['kernels'][k] = dict(` | Stores the result of the kernel. The record starts in this line and goes on to line 644. |
| 641 | `                n_processes=len(pk), spreads=[r[k]['spread'] for r in pk], median_spread=med([r[k]['spread'] for r in pk]),` | Continues the record: the number of processes, the list of their spreads and the median spread in GB/s. |
| 642 | `                median_total=med([r[k]['median_total'] for r in pk]), median_total_M_sum=med([r[k]['median_total_M_sum'] for r in pk]),` | Continues the record: the median over the processes of their median `M_hist`, and the same for `M_sum`. |
| 643 | `                H11=h11, H11_note=note,` | Continues the record: the word for H11 and its note. |
| 644 | `                high_minus_low=[dict(total=sum(r[k]['hi']) - sum(r[k]['lo']), mesh0=r[k]['hi'][0] - r[k]['lo'][0], mesh1=r[k]['hi'][1] - r[k]['lo'][1]) for r in pk])` | Continues the record: `high_minus_low`. Per process it holds the highest total minus the lowest total, and the same difference for mesh 0 and for mesh 1, in GB/s. |
| 645 | `            rows.append(row('B10 %s %s: H11' % (s, k), h11, len(pk), ctrl_total, med([r[k]['spread'] for r in pk]),` | Adds one table line for the setting and the kernel: the word for H11, the number of processes, the control of the total in the A/A column and the median spread in the value column. The call goes on in line 646. |
| 646 | `                            'A/A value = control of the total; controls of mesh 0 and mesh 1: %s and %s; value = median spread. %s' % (fmt(ctrl_mesh[0]), fmt(ctrl_mesh[1]), note)))` | Continues line 645: the note names what the two columns hold and gives the controls of mesh 0 and of mesh 1. |
| 647 | `        out['settings'][s] = res` | Stores the result of the setting. |
| 648 | `    out['spread_changes'] = {}` | `spread_changes`: the changes of the spread between settings, empty at first. |
| 649 | `    for factor, x, y in factor_pairs(list(spreads)):` | Loop over the pairs of settings that differ in exactly one factor (line 503). |
| 650 | `        for k in kernels:` | Loop over the four kernels. |
| 651 | `            word, change = decide.decide_change(spreads[x][k], spreads[y][k])` | `decide.decide_change` on the spread values of the two settings (line 634), with at least 4 processes per setting. The change is the median spread of the first setting minus that of the second. It is resolved when its absolute value is above the sum of the two controls of the spread and the spreads of the two settings do not overlap [Ref4]. Only `M_hist` is used for the spread. |
| 652 | `            cs = None if change is None else max(abs(v['E']) for v in spreads[x][k]) + max(abs(v['E']) for v in spreads[y][k])` | `cs`: the sum of the two controls of the spread in GB/s, or `None` without a change. |
| 653 | `            tx, ty = out['settings'][x]['kernels'][k]['median_total'], out['settings'][y]['kernels'][k]['median_total']` | `tx` and `ty`: the median total of the kernel in the first setting and in the second. |
| 654 | `            note = 'a setting has fewer than 4 processes with a spread and a control' if word == 'not observed' else \` | `note`: for the word `not observed` it says that a setting has fewer than 4 processes with a spread and a control. The other case follows in line 655. |
| 655 | `                'change of the median total (description, no rule): %s GB/s' % fmt(None if tx is None or ty is None else tx - ty)` | Continues line 654: if not, it gives the change of the median total in GB/s. The text marks this number as a description without a rule. |
| 656 | `            out['spread_changes']['%s %s: %s -> %s' % (k, factor, x, y)] = dict(` | Stores the change under a key that names the kernel, the factor and the two settings. The record goes on in lines 657 to 658. |
| 657 | `                kernel=k, factor=factor, first=x, second=y, decision=word, change_of_spread=change, sum_of_controls=cs,` | Continues the record: the kernel, the factor, the settings, the word, the change of the spread and the sum of the controls. |
| 658 | `                change_of_median_total=None if tx is None or ty is None else tx - ty, n_first=len(spreads[x][k]), n_second=len(spreads[y][k]), note=note)` | Continues the record: the change of the median total, the two process counts and the note. |
| 659 | `            rows.append(row('B10 %s change of spread, %s: %s minus %s' % (k, factor, x, y), word,` | Adds one table line for the change of the spread. The call goes on in line 660. |
| 660 | `                            '%d and %d' % (len(spreads[x][k]), len(spreads[y][k])), cs, change, note))` | Continues line 659: the two process counts, the sum of the controls, the change and the note. |
| 661 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 662 | `    return out` | Returns the report of the step. |

### Functions `count_label` and `bracket`: the pattern of a thread count (lines 665 to 684)

| Line | Source | Explanation |
|---:|---|---|
| 665 | `def count_label(labels):` | Starts the function `count_label`. It joins the pattern labels of several intervals into one label. |
| 666 | `    return 'untested' if not labels else labels[0] if len(set(labels)) == 1 and labels[0] in ('split', 'uniform') else 'mixed'` | Without any label the result is `untested`. When all labels are equal and are `split` or `uniform`, the result is that label. Every other case is `mixed`, also when all intervals have the label `between`. |
| 669 | `def bracket(count_labels):` | Starts the function `bracket`, a rule of step B8. `count_labels` maps a count of mesh-1 threads to its label. |
| 670 | `    """B8: count_labels = {mesh-1 threads: split \| uniform \| mixed \| untested}. -> (x, y) or None.` | Docstring: the labels are `split`, `uniform`, `mixed` or `untested`. The result is a pair of two counts, or `None`. |
| 671 | `    A bracket exists only if every tested count up to x is split, every tested count from y on is uniform,` | Docstring: a bracket exists only if every tested count up to the first number of the pair is split, and every tested count from the second number on is uniform. The sentence ends in line 672. |
| 672 | `    and the tested counts between them are mixed."""` | Docstring: and the tested counts between the two are mixed. |
| 673 | `    t = [(b, l) for b, l in sorted(count_labels.items()) if l != 'untested']` | `t`: the tested counts with their labels, in rising order of the count. Counts with the label `untested` are dropped. |
| 674 | `    i = 0` | `i`: starts at 0. |
| 675 | `    while i < len(t) and t[i][1] == 'split':` | Loop: runs while the label at place `i` is `split`. |
| 676 | `        i += 1` | Moves `i` one place forward. After the loop `i` is the number of split counts at the low end of the list. |
| 677 | `    j = len(t)` | `j`: starts at the length of the list. |
| 678 | `    while j > 0 and t[j - 1][1] == 'uniform':` | Loop: runs while the label before place `j` is `uniform`. |
| 679 | `        j -= 1` | Moves `j` one place back. After the loop `j` is the place of the first of the uniform counts at the high end. |
| 680 | `    if i == 0 or j == len(t) or any(l != 'mixed' for _, l in t[i:j]):` | Three cases give no bracket: the lowest tested count is not split, the highest tested count is not uniform, or a count between the two runs has a label other than `mixed`. A split count above a uniform count belongs to the third case. |
| 681 | `        return None` | Then the result is `None`. |
| 682 | `    return t[i - 1][0], t[j][0]` | Returns the bracket: the highest count of the split run and the lowest count of the uniform run. |

### Function `a_b8`: step B8, the bracket of each kernel and hypothesis H8 (lines 685 to 716)

| Line | Source | Explanation |
|---:|---|---|
| 685 | `def a_b8(procs, ctx, step):` | Starts the function `a_b8`, the analysis of step B8. The step runs `oldread` and the A/A pair `asmread` and `asmread2` in one process, with threads on mesh 0 and a varied number of threads on mesh 1 [Ref1]. |
| 686 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 687 | `    rows, out['kernels'] = [], {}` | `rows`: the table lines. `out['kernels']`: the results per kernel. Both are empty at first. |
| 688 | `    a_counts = sorted({p.threads_mesh0 for p in used}) if used else []` | `a_counts`: the different numbers of mesh-0 threads among the processes, sorted. `analyze` sets `threads_mesh0` and `threads_mesh1` of each process before this call (lines 1024 to 1028). |
| 689 | `    out['mesh0_threads'] = a_counts` | Stores this list in the report. |
| 690 | `    for k in ('oldread', 'asmread', 'asmread2'):` | Loop over the three kernels. |
| 691 | `        counts = {}` | `counts`: the record per count of mesh-1 threads, empty at first. |
| 692 | `        for p in used:` | Loop over the complete processes. |
| 693 | `            c = counts.setdefault(p.threads_mesh1, dict(labels=[], q=[], n_processes=0, left_out_irregular=0))` | `c`: the record of the count of mesh-1 threads of this process. A new record has two empty lists, `labels` and `q`, and two numbers at 0. |
| 694 | `            c['n_processes'] += 1` | Counts the process. |
| 695 | `            for iv in p.rate_by_entry.get(k, []):` | Loop over the intervals of this kernel in the process. |
| 696 | `                if iv.irregular:` | An irregular interval. |
| 697 | `                    c['left_out_irregular'] += 1` | It is counted as left out and gives no label. |
| 698 | `                else:` | A regular interval. |
| 699 | `                    c['labels'].append(iv.pattern)` | Adds its pattern label (line 89). |
| 700 | `                    c['q'].append(round(iv.q, 4))` | Adds its `q`, rounded to 4 decimals. |
| 701 | `        for c in counts.values():` | Loop over the records. |
| 702 | `            c['label'] = count_label(c['labels'])` | `label`: the one label of the count, from all regular intervals of the kernel in all processes with this count (line 665). |
| 703 | `        br = bracket({b: c['label'] for b, c in counts.items()}) if len(a_counts) == 1 else None` | `br`: the bracket of this kernel (line 669). It is built only when all processes have the same number of mesh-0 threads. If not, it is `None`. |
| 704 | `        note = 'counts of mesh-1 threads and their labels: ' + ', '.join('%d %s' % (b, counts[b]['label']) for b in sorted(counts))` | `note`: lists every count of mesh-1 threads with its label. |
| 705 | `        if len(a_counts) > 1:` | The input has more than one number of mesh-0 threads. |
| 706 | `            note = 'the input has more than one count of mesh-0 threads (%s): no bracket is built. ' % a_counts + note` | Then the note starts with the sentence that no bracket is built, and with the numbers found. |
| 707 | `        out['kernels'][k] = dict(counts={b: counts[b] for b in sorted(counts)}, bracket=br, decision='bracket' if br else 'not resolved', note=note)` | Stores the result of the kernel: the records per count in rising order, the bracket, the word `bracket` or `not resolved`, and the note. |
| 708 | `        rows.append(row('B8 %s: bracket of mesh-1 threads' % k, ('%d to %d' % br) if br else 'not resolved',` | Adds one table line for the kernel: the bracket in the form `36 to 44`, or `not resolved`. The call goes on in line 709. |
| 709 | `                        sum(c['n_processes'] for c in counts.values()), None, None, note + '; pattern labels need no A/A spread'))` | Continues line 708: the number of processes, no A/A spread and no value. The note adds that pattern labels need no A/A spread. |
| 710 | `    o, a = out['kernels']['oldread']['bracket'], out['kernels']['asmread']['bracket']` | `o`: the bracket of `oldread`. `a`: the bracket of `asmread`. The bracket of `asmread2` is reported and not compared. |
| 711 | `    out['H8'] = 'not resolved' if not o or not a else 'supported' if a[1] <= o[0] else 'contradicted' if o[1] <= a[0] else 'not resolved at this grid'` | `H8`: the word for hypothesis H8. H8 predicts that `asmread` changes to the uniform pattern at a lower count of mesh-1 threads than old read [Ref2]. `not resolved` when a bracket is missing. `supported` when the upper end of the `asmread` bracket is at or below the lower end of the old read bracket. `contradicted` when the upper end of the old read bracket is at or below the lower end of the `asmread` bracket. Every other case is `not resolved at this grid`. |
| 712 | `    rows.append(row('B8 H8: asm read changes at a lower count than old read', out['H8'], len(used), None, None, 'old read %s, asm read %s' % (o, a)))` | Adds the table line for H8, with the two brackets in the note. |
| 713 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 714 | `    return out` | Returns the report of the step. |

### Function `a_b5`: step B5, does a variant show the pattern and total of old read (lines 717 to 749)

| Line | Source | Explanation |
|---:|---|---|
| 717 | `def a_b5(procs, ctx, step):` | Starts the function `a_b5`, the analysis of step B5. The step runs old read, new read, load-only loops with added `nop` instructions, and the A/A pair `asmread` and `asmread2`. Each kernel has one interval per process, and every second process runs the sequence in the reversed order [Ref1]. |
| 718 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 719 | `    variants = [e for e in dict.fromkeys(e for p in used for e in p.seq) if e not in ('oldread', 'asmread2')]` | `variants`: every entry that occurs in a sequence of the step, once, in the order of its first use, without `oldread` and `asmread2`. So `read` and `asmread` are handled as variants too. |
| 720 | `    rows, out['variants'] = [], {}` | `rows`: the table lines. `out['variants']`: the results per variant. Both are empty at first. |
| 721 | `    one = lambda p, e: p.rate_by_entry[e][0] if len(p.rate_by_entry.get(e, [])) == 1 else None` | `one`: a small function that gives the only interval of entry `e` in process `p`. It gives `None` when the process has no interval of the entry, or more than one. |
| 722 | `    old = {p.tag: one(p, 'oldread') for p in used}` | `old`: the `oldread` interval of each process, by tag. |
| 723 | `    out['oldread_patterns'] = {t: (iv.pattern if iv and not iv.irregular else None) for t, iv in old.items()}` | `oldread_patterns`: the pattern label of that interval per tag, or `None` when the interval is missing or irregular. |
| 724 | `    out['oldread_q'] = {t: (round(iv.q, 4) if iv else None) for t, iv in old.items()}` | `oldread_q`: its `q` per tag, rounded to 4 decimals, or `None` when the interval is missing. |
| 725 | `    for v in variants:` | Loop over the variants. |
| 726 | `        vals, missing = setting_values(used, 'oldread', v, 'asmread2', 'asmread')` | Computes `D` and `E` per process (line 465). `D` is `oldread` minus the variant. `E` is `asmread2` minus `asmread`. Both are differences of total rates in GB/s. |
| 727 | `        d = decide_d(vals, missing)` | Decides `D` (line 489): at least 4 processes, `M_hist` as the decision metric and `M_sum` as the check. |
| 728 | `        pats = {}` | `pats`: the pattern labels per process, empty at first. |
| 729 | `        for p in used:` | Loop over the complete processes. |
| 730 | `            iv, o = one(p, v), old[p.tag]` | `iv`: the interval of the variant in this process. `o`: its `oldread` interval. |
| 731 | `            pats[p.tag] = None if not iv or not o or iv.irregular or o.irregular else (iv.pattern, o.pattern)` | Stores the pair of the pattern label of the variant and the pattern label of old read. The value is `None` when one of the two intervals is missing or irregular. |
| 732 | `        same = None if not pats or any(x is None for x in pats.values()) else all(x[0] == x[1] for x in pats.values())` | `same`: true when the two labels are equal in every process. False when they differ in at least one process. `None` when a process has no pair of labels. |
| 733 | `        if d['decision'] == 'not observed' or same is None:` | Tests whether `D` is `not observed`, or the patterns are not known in every process. |
| 734 | `            shows, note = 'not observed', d['note'] or 'an interval of the variant or of old read is irregular or missing'` | Then the answer is `not observed`. The note is the note of `D`. When that note is empty, the note says that an interval of the variant or of old read is irregular or missing. |
| 735 | `        else:` | Both parts are known. |
| 736 | `            # "yes" needs M_hist AND M_sum "not resolved". If the two metrics give another word or sign, the total` | Comment: the answer `yes` needs the word `not resolved` with `M_hist` and with `M_sum`. The comment goes on in line 737. |
| 737 | `            # difference is neither shown nor excluded: the variant gets "not resolved", never "yes".` | Comment, continued: when the two metrics give another word or sign, the total difference is neither shown nor excluded. The variant then gets `not resolved`, never `yes`. |
| 738 | `            shows = 'no' if not same else 'not resolved' if d['metrics_disagree'] else 'yes' if d['decision'] == 'not resolved' else 'no'` | `shows`: the answer to the question whether the variant shows the pattern and the total of old read. `no` when the patterns differ. With equal patterns: `not resolved` when the two metrics disagree, `yes` when the total difference `D` is not resolved, and `no` when `D` is resolved. The deviations note lists the case of a disagreement as point A28, which needs a decision of the lead [Ref3]. |
| 739 | `            note = 'pattern equal to old read in every process: %s; total difference old read minus variant: %s%s' % (` | `note`: says whether the pattern equals that of old read in every process, and gives the word and the sign of the total difference. The text goes on in line 740. |
| 740 | `                'yes' if same else 'no', d['decision'], sign_txt(d['sign'])) + ('; ' + d['note'] if d['metrics_disagree'] else '')` | Continues line 739: the values of the note. When the two metrics disagree, the note of line 485 is added. |
| 741 | `        h = d['metrics']['M_hist']` | `h`: the decision of `D` with `M_hist`. |
| 742 | `        out['variants'][v] = dict(shows_pattern_and_total_of_oldread=shows, same_pattern=same, total_difference=d,` | Stores the result of the variant: the answer, `same_pattern` and the decision of the total difference. The record goes on in line 743. |
| 743 | `                                  patterns={t: (x[0] if x else None) for t, x in pats.items()}, note=note)` | Continues line 742: the pattern label of the variant per process, and the note. |
| 744 | `        rows.append(row('B5 %s shows the pattern and total of old read' % v, shows, h['n_processes'], h['aa_spread'], h['median_D'],` | Adds one table line for the variant: the answer, the number of processes, the A/A spread and the median `D` with `M_hist`. The call goes on in line 745. |
| 745 | `                        note + '; value = median of old read minus variant'))` | Continues line 744: the note, with the remark that the value is the median of old read minus the variant. |
| 746 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 747 | `    return out` | Returns the report of the step. |

### Function `a_b9`: step B9, old read with one buffer and with two (lines 750 to 786)

| Line | Source | Explanation |
|---:|---|---|
| 750 | `def a_b9(procs, ctx, step):` | Starts the function `a_b9`, the analysis of step B9. The step runs `oldread` alone with 120 threads, in processes with one buffer per thread and in processes with two buffers (`--two-buffers`) [Ref1]. |
| 751 | `    """B9 (local rule): pattern of old read with one and with two buffers. The A/A value of the total is the` | Docstring: a local rule. It compares the pattern of old read with one buffer and with two. The docstring goes on in line 752. |
| 752 | `    largest difference between two processes of one kind."""` | Docstring: the A/A value of the total is the largest difference between two processes of one kind. |
| 753 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 754 | `    kinds, rows = {}, []` | `kinds`: the result per kind. `rows`: the table lines. Both are empty at first. |
| 755 | `    for name, flag in (('one_buffer', False), ('two_buffers', True)):` | Loop over the two kinds: `one_buffer` for the processes without `--two-buffers`, and `two_buffers` for the processes with it. |
| 756 | `        g = [p for p in used if p.two_buffers == flag]` | `g`: the complete processes of this kind. |
| 757 | `        ivs = [iv for p in g for iv in p.ordered if not iv.irregular]` | `ivs`: all regular intervals of these processes. |
| 758 | `        pv = [median(iv.hist for iv in p.ordered) for p in g if not any(iv.irregular for iv in p.ordered)]` | `pv`: the process values: per process the median `M_hist` of its intervals, in GB/s. A process with an irregular interval gives no value. |
| 759 | `        kinds[name] = dict(n_processes=len(g), pattern=count_label([iv.pattern for iv in ivs]), q=[round(iv.q, 4) for iv in ivs],` | Stores for the kind: the number of processes, the pattern label of the kind from all its regular intervals (line 665), and the `q` of each of these intervals. The record goes on in line 760. |
| 760 | `                           process_values=pv, aa_value=(max(pv) - min(pv)) if len(pv) >= 2 else None)` | Continues line 759: the process values, and the A/A value: the highest minus the lowest process value. It is `None` with fewer than 2 process values. |
| 761 | `    o, t = kinds['one_buffer'], kinds['two_buffers']` | `o`: the result with one buffer. `t`: the result with two. |
| 762 | `    pats = (o['pattern'], t['pattern'])` | `pats`: the two pattern labels. |
| 763 | `    if 'untested' in pats:` | One kind has no regular interval. |
| 764 | `        word = 'not observed'` | Then the pattern result is `not observed`. |
| 765 | `    elif pats[0] == pats[1] and pats[0] in ('split', 'uniform'):` | Both kinds have the same label, and it is `split` or `uniform`. |
| 766 | `        word = 'same pattern'` | Then the pattern result is `same pattern`. Hypothesis H9a predicts the opposite: old read is split with one buffer and uniform with two [Ref2]. |
| 767 | `    elif pats == ('split', 'uniform'):` | One buffer is split and two buffers are uniform. |
| 768 | `        word = 'pattern as H9a predicts'` | Then the pattern result is `pattern as H9a predicts`. |
| 769 | `    else:` | Every other case, for example a kind with the label `mixed`. |
| 770 | `        word = 'not resolved'` | Then the pattern result is `not resolved`. |
| 771 | `    out.update(kinds=kinds, pattern_result=word)` | Stores the two kinds and the pattern result. |
| 772 | `    rows.append(row('B9 pattern with one buffer and with two', word, '%d and %d' % (o['n_processes'], t['n_processes']), None, None,` | Adds the table line of the pattern: the word and the two process counts. The call goes on in line 773. |
| 773 | `                    'one buffer: %s, two buffers: %s; pattern labels need no A/A spread' % pats))` | Continues line 772: no A/A spread and no value. The note gives the two labels and says that pattern labels need no A/A spread. |
| 774 | `    if o['aa_value'] is None or t['aa_value'] is None:` | Tests whether a kind has fewer than 2 process values. |
| 775 | `        tot = dict(decision='not observed', difference=None, aa_value=None, note='2 processes of each kind are needed')` | Then the total is `not observed`, with the note that 2 processes of each kind are needed. |
| 776 | `    else:` | Both kinds have an A/A value. |
| 777 | `        diff, aa = median(o['process_values']) - median(t['process_values']), max(o['aa_value'], t['aa_value'])` | `diff`: the median process value with one buffer minus the median with two, in GB/s. `aa`: the larger of the two A/A values. |
| 778 | `        sep = max(o['process_values']) < min(t['process_values']) or min(o['process_values']) > max(t['process_values'])` | `sep`: true when the process values of the two kinds do not overlap. |
| 779 | `        tot = dict(decision='resolved' if abs(diff) > aa and sep else 'not resolved', difference=diff, aa_value=aa, note='total with one buffer minus total with two (M_hist)')` | The total is `resolved` when the absolute difference is above the A/A value and the two sets do not overlap. If not, it is `not resolved`. Only `M_hist` is used here. |
| 780 | `    out['total'] = tot` | Stores the result for the total. |
| 781 | `    rows.append(row('B9 total rate, one buffer minus two', tot['decision'], '%d and %d' % (len(o['process_values']), len(t['process_values'])),` | Adds the table line of the total rate: the word and the numbers of process values of the two kinds. The call goes on in line 782. |
| 782 | `                    tot['aa_value'], tot['difference'], tot['note']))` | Continues line 781: the A/A value, the difference and the note. |
| 783 | `    out['rows'] = rows` | Stores the table lines in the report. |
| 784 | `    return out` | Returns the report of the step. |

### `EVENTS` and `a_count`: steps C1 to C3, counts per 64 B line (lines 787 to 833)

| Line | Source | Explanation |
|---:|---|---|
| 787 | `# ---------------------------------------------------------------- Part C and SHORT (description only)` | Comment: a divider. Part C and the step SHORT follow. The comment says that they give a description only. |
| 789 | `EVENTS = ('cycles', 'instructions', 'l1d_refill', 'l2d_refill', 'll_read_miss')` | `EVENTS`: the names that the script gives to the first five count columns of a `C` row, in order: cycles, instructions, `l1d_refill` and `l2d_refill` (refills of the data caches of level 1 and level 2) and `ll_read_miss` (read misses of the last cache level). The names are assigned by position. The script does not read the event names that the runner prints in its comment line. |
| 792 | `def a_count(procs, ctx, step):` | Starts the function `a_count`, the analysis of the steps C1, C2 and C3. These steps repeat sequences of Part B with the option `--count` [Ref1]. |
| 793 | `    """C1, C2, C3: counts per interval, kernel and thread. A row whose running time is below its enabled time is not used."""` | Docstring: the counts are taken per interval, kernel and thread. A `C` row whose running time is below its enabled time is not used. |
| 794 | `    used, out = integrity(procs)` | Takes the complete processes and starts the report (line 237). |
| 795 | `    groups, unused, total = {}, 0, 0` | `groups`: the values per group, empty at first. `unused`: the number of `C` rows that are not used. `total`: the number of all `C` rows. |
| 796 | `    for p in used:` | Loop over the complete processes. |
| 797 | `        for c in p.C:` | Loop over the `C` rows of the process. |
| 798 | `            total += 1` | Counts the row. |
| 799 | `            iv = p.raw.get((c['round'], c['pos']))` | `iv`: the interval of the row, found by the round as printed and the position. |
| 800 | `            t = next((x for x in iv.rows if x['tid'] == c['tid']), None) if iv else None` | `t`: the `T` row of the same thread in that interval, or `None`. |
| 801 | `            if t is None or None in (c['running'], c['enabled'], c['cputime']) or c['running'] < c['enabled'] or c['enabled'] <= 0 or c['cputime'] <= 0:` | The row is not used in five cases: no `T` row fits, one of the three times is `NA`, the running time is below the enabled time, the enabled time is not above 0, or the CPU time is not above 0. A running time below the enabled time means that the counters did not count for the whole interval [Ref2]. |
| 802 | `                unused += 1` | Counts the row as not used. |
| 803 | `                continue` | Goes on with the next row. |
| 804 | `            level = decide.level(iv.rate) if p.threads == 1 and p.entry_size(iv.entry) == 8 * MIB and iv.entry == REF else '-'` | `level`: the level label of the rate of the interval (line 257). Only an interval of `asmread` at 8 MiB in a process with one thread gets one. Every other interval gets `-`. |
| 805 | `            mesh = '-' if p.threads == 1 else 'mesh0' if c['cpu'] in MESH0_CPUS else 'mesh1'` | `mesh`: `-` for a process with one thread. If not, `mesh0` for a thread on the CPUs 0 to 63 and `mesh1` for every other thread. |
| 806 | `            group = p.setting if p.threads > 1 else 'cpu%s' % p.cpu` | `group`: the setting for a process with many threads, and the CPU in the form `cpu2` for a process with one thread. |
| 807 | `            if step == 'C3':                                    # C3 runs the B7 sequence and the B5 sequence: keep them apart` | Only for step C3. By the comment C3 runs the sequence of B7 and the sequence of B5, and the two must stay in separate groups. |
| 808 | `                group += ' B5 sequence' if 'read_sparse' in p.seq else ' B7 sequence'` | Adds a space and the words `B5 sequence` to the group name when the sequence holds `read_sparse`. If not, it adds a space and `B7 sequence`. |
| 809 | `            key = (group, iv.entry, level, mesh)` | `key`: the group name, the entry, the level and the mesh. |
| 810 | `            g = groups.setdefault(key, dict({e: [] for e in EVENTS + ('clock_GHz', 'GBps')}, procs=set()))` | `g`: the lists of the group, made at its first row: one list per event name, one for `clock_GHz`, one for `GBps`, and a set `procs`. |
| 811 | `            g['procs'].add(id(p))` | Notes the process of the row in the set. So the group knows the number of its processes. |
| 812 | `            lines = t['bytes'] / 64.0` | `lines`: the bytes of the `T` row divided by 64. A line is 64 B, the size of one cache line. |
| 813 | `            cnt = dict(zip(EVENTS, c['counts'] + [None] * 5))` | `cnt`: the counts of the row by event name. A row with fewer than 5 counts gets `None` for the rest. |
| 814 | `            if cnt['cycles'] is not None:` | Only when the cycle count exists. |
| 815 | `                g['clock_GHz'].append(cnt['cycles'] / c['cputime'])` | Adds the clock rate of the core in GHz: the cycles divided by the CPU time of the thread in ns. |
| 816 | `            g['GBps'].append(t['bytes'] / t['elapsed'] / 1e9)` | Adds the rate of the thread in GB/s: `bytes` divided by `elapsed_s` and by 1e9, both from the `T` row. |
| 817 | `            for e in EVENTS:` | Loop over the five event names. |
| 818 | `                if cnt[e] is not None:` | Only when the row has a count for the event. |
| 819 | `                    g[e].append(cnt[e] / lines)` | Adds the count per line: the count divided by `lines`. |
| 820 | `    out['rows_C'], out['rows_C_not_used'] = total, unused` | Stores the number of all `C` rows and the number of rows that are not used. |
| 821 | `    out['groups'] = [dict(group=k[0], entry=k[1], level=k[2], mesh=k[3], n_rows=len(g['GBps']), n_processes=len(g['procs']), median_thread_GBps=med(g['GBps']),` | `out['groups']`: one record per group, sorted by key: the group name, the entry, the level, the mesh, the number of rows, the number of processes and the median rate of a thread in GB/s. The record goes on in lines 822 to 823. |
| 822 | `                          median_clock_GHz=med(g['clock_GHz']), **{'median_%s_per_line' % e: med(g[e]) for e in EVENTS},` | Continues the record: the median clock rate in GHz, and for each event the median count per line. |
| 823 | `                          not_supported=[e for e in EVENTS if not g[e]]) for k, g in sorted(groups.items())]` | Continues the record: `not_supported`, the events for which the group has no count at all. The loop over the groups follows. |
| 824 | `    out['note'] = 'Description only, no decision. A line is 64 B of the bytes that the T row counts (a copy counts the bytes read plus the bytes written). ' \` | `note`: the step is a description without a decision. A line is 64 B of the bytes that the `T` row counts. For a copy kernel these are the bytes read plus the bytes written. The text goes on in line 825. |
| 825 | `                  'instructions per byte = median_instructions_per_line / 64.'` | Continues line 824: the instructions per byte are the median instructions per line divided by 64. |
| 826 | `    out['rows'] = [row('%s %s %s level %s %s' % (step, g['group'], g['entry'], g['level'], g['mesh']), 'description', g['n_processes'], None, g['median_thread_GBps'],` | `out['rows']`: one table line per group. Its label names the step, the group, the entry, the level and the mesh. The word is `description`, the process column holds the number of processes, and the value is the median rate of a thread. The call goes on in lines 827 to 830. |
| 827 | `                       '%d C rows (one per thread and interval); value = median rate of a thread; ' % g['n_rows'] +` | Continues the line: the note starts with the number of `C` rows of the group and says that the value is the median rate of a thread. |
| 828 | `                       'clock %s GHz; per line: instr %s, L1D refill %s, L2D refill %s, LL read miss %s' % tuple(` | Continues the note: the clock rate in GHz, and per line the instructions, the refills of the two cache levels and the read misses of the last level. |
| 829 | `                           fmt(g[x], 4) for x in ('median_clock_GHz', 'median_instructions_per_line', 'median_l1d_refill_per_line',` | Continues the note: the first three of the five values that it prints, each with 4 decimals (line 1037). |
| 830 | `                                                 'median_l2d_refill_per_line', 'median_ll_read_miss_per_line'))) for g in out['groups']]` | Continues the note: the last two values, and the loop over the groups. |
| 831 | `    return out` | Returns the report of the step. |

### `a_short`, and the tables `ANALYZERS` and `ORDER` (lines 834 to 853)

| Line | Source | Explanation |
|---:|---|---|
| 834 | `def a_short(procs, ctx, step):` | Starts the function `a_short`. It handles the step SHORT and every step name that the table of line 849 does not hold. |
| 835 | `    """SHORT and unknown steps: no decision. One line per process, to check the output of bwx."""` | Docstring: these steps get no decision. The function gives one line per process, to check the output of the runner. |
| 836 | `    used, out = integrity(procs)` | Starts the report (line 237). The list of the complete processes is not used here. |
| 837 | `    out['processes'] = [dict(file=p.file, tag=p.tag, status=p.status, complete=p.complete, intervals=len(p.iv), expected=len(p.seq) * p.rounds,` | `out['processes']`: one record per process, complete or not: file, tag, status, `complete`, the number of intervals found and the number expected. The record goes on in lines 838 to 841. |
| 838 | `                             I_rows=p.n_I, P_rows=len(p.P), P_rows_NA=sum(1 for x in p.P if x['kB_total'] is None), C_rows=len(p.C),` | Continues the record: the number of `I` rows, the number of `P` rows, the number of `P` rows whose `kB_total` is `NA`, and the number of `C` rows. |
| 839 | `                             late_intervals=sum(1 for iv in p.iv.values() if not iv.problem and iv.late),` | Continues the record: the number of intervals with at least one late thread. Intervals with a problem are skipped. |
| 840 | `                             max_end_skew_ms=max((round(iv.skew * 1e3, 3) for iv in p.iv.values() if not iv.problem), default=None),` | Continues the record: the largest end skew of an interval in ms, rounded to 3 decimals, or `None` without a usable interval. |
| 841 | `                             other_lines=p.other_lines, problems=p.problems[:5]) for p in procs]` | Continues the record: the number of lines of no known kind, and the first 5 problems. The loop over all processes of the step follows. |
| 842 | `    out['rows'] = [row('%s %s' % (step, x['tag']), 'complete' if x['complete'] else 'NOT complete', 1, None, None,` | `out['rows']`: one table line per process. The word is `complete` or `NOT complete`, and the process column holds 1. The call goes on in lines 843 to 845. |
| 843 | `                       '%d of %d intervals, P rows %d (NA %d), C rows %d, late intervals %d, largest end skew %s ms %s' % (` | Continues the line: the text of the note. It gives the intervals found and expected, the `P` rows and those with `NA`, the `C` rows, the late intervals and the largest end skew in ms. |
| 844 | `                           x['intervals'], x['expected'], x['P_rows'], x['P_rows_NA'], x['C_rows'], x['late_intervals'], x['max_end_skew_ms'],` | Continues the line: the values of the note. |
| 845 | `                           '; '.join(x['problems']))) for x in out['processes']]` | Continues the line: the problems, joined with the character `;` and a space. The loop over the records follows. |
| 846 | `    return out` | Returns the report. |
| 849 | `ANALYZERS = dict(B1=a_copy, B2=a_copy, B3=a_copy, B4=a_b4, B6=a_b6, B7=a_b7, B10=a_b10, B8=a_b8, B5=a_b5, B9=a_b9,` | `ANALYZERS`: the table from a step name to its analysis function. B1, B2 and B3 use `a_copy`. B4, B6, B7, B10, B8, B5 and B9 each have their own function. The table goes on in line 850. |
| 850 | `                 C1=a_count, C2=a_count, C3=a_count)` | Continues line 849: C1, C2 and C3 use `a_count`. |
| 851 | `ORDER = ['SHORT', 'B1', 'B2', 'B3', 'B4', 'B6', 'B7', 'B10', 'B8', 'B5', 'B9', 'C1', 'C2', 'C3']` | `ORDER`: the order in which the steps of a session are analysed and printed. B1 stands before B3, which needs the values of B1 (line 346). |

### Function `two_sessions`: from the flags of the sessions to one word (lines 854 to 867)

| Line | Source | Explanation |
|---:|---|---|
| 854 | `# ---------------------------------------------------------------- the two sessions together` | Comment: a divider. The functions that join the sessions start here. |
| 856 | `def two_sessions(flags):` | Starts the function `two_sessions`. `flags` maps each session to its flag for one hypothesis. |
| 857 | `    """flags: one per session: 'fail' (the bounded prediction failed), 'hold', 'not observed', 'not resolved'.` | Docstring: a flag is `fail` (the bounded prediction of the hypothesis failed in that session), `hold`, `not observed` or `not resolved`. |
| 858 | `    'not resolved' is never a failure: with it the word is 'not rejected'.` | Docstring: `not resolved` is never a failure. With it the word is `not rejected`. |
| 859 | `    -> one of the words of rule 11 of the plan. 'rejected' needs the failure in at least 2 sessions and in all of them."""` | Docstring: the result is one of the words of rule 11 of the plan. The word `rejected` needs the failure in every session and in at least 2 sessions. |
| 860 | `    f = list(flags.values())` | `f`: the flags as a list. |
| 861 | `    if f and all(x == 'not observed' for x in f):` | Tests whether there is at least one session and every flag is `not observed`. |
| 862 | `        return 'not observed'` | Then the word is `not observed`. |
| 863 | `    if len(f) < 2:` | Fewer than 2 sessions. |
| 864 | `        return 'not rejected (one session only: "rejected" needs 2 sessions)' if f else 'not tested'` | With one session the word is `not rejected`, with the remark that `rejected` needs 2 sessions. Without a session it is `not tested`. |
| 865 | `    return 'rejected' if all(x == 'fail' for x in f) else 'not rejected'` | With 2 or more sessions: `rejected` when every flag is `fail`. If not, `not rejected`. |

### `cross`: the entries for H4, H5 and H6 (steps B1, B2 and B3) (lines 868 to 909)

| Line | Source | Explanation |
|---:|---|---|
| 868 | `def cross(sessions):` | Starts the function `cross`. `sessions` maps each session name to its results per step. |
| 869 | `    """Words for the hypotheses over all sessions. Each entry keeps the flag of every session."""` | Docstring: it gives the words for the hypotheses over all sessions. Each entry keeps the flag of every session. |
| 870 | `    out = {}` | `out`: the entries, empty at first. |
| 872 | `    def put(name, flags, basis):` | Starts the inner function `put`. It stores one entry. |
| 873 | `        if flags:` | Only when at least one session has a flag. |
| 874 | `            out[name] = dict(word=two_sessions(flags), per_session=flags, basis=basis)` | The entry holds the word of line 856, the flag per session, and `basis`: a text that says what the flags mean. |
| 876 | `    def per(step):` | Starts the inner function `per`. |
| 877 | `        return {s: r[step] for s, r in sessions.items() if step in r}` | It returns the result of one step for every session that ran the step. |
| 879 | `    b1 = per('B1')` | `b1`: the results of step B1 per session. |
| 880 | `    b1_low = {}` | `b1_low`: the B1 results for the label `low`. Line 888 fills it. |
| 881 | `    for lab in ('low', 'high'):` | Loop over the labels `low` and `high`. |
| 882 | `        res = {s: r['groups'].get('8M', {}).get('labels', {}).get(lab) for s, r in b1.items()}` | `res`: per session, the result of B1 at 8 MiB for this label (line 304), or `None` when the session has none. |
| 883 | `        res = {s: v for s, v in res.items() if v}` | Drops the sessions without a result. |
| 884 | `        signs = {v['sign'] for v in res.values()}` | `signs`: the set of the signs of these results over all sessions. A result that is not resolved has the sign `None`. |
| 885 | `        flags = {s: 'fail' if v['decision'] == 'resolved' and len(signs) == 1 else 'not observed' if v['decision'] == 'not observed' else 'hold' for s, v in res.items()}` | The flag of a session for hypothesis H4. `fail`: the difference is resolved in this session, and all sessions have the same sign. `not observed`: the word of the session is `not observed`. Every other case is `hold`. |
| 886 | `        put('H4 (B1, 8 MiB, label %s)' % lab, flags, 'H4 predicts no resolved difference copy - asmcopy inside one process; fail = resolved with one sign in all sessions')` | Stores the entry `H4 (B1, 8 MiB, label ...)`. H4 says that the copy difference does not come from the kernel code [Ref2]. By the text of the entry it predicts no resolved difference between `copy` and `asmcopy` inside one process. So a difference that is resolved with one sign in all sessions is the failure. |
| 887 | `        if lab == 'low':` | Only for the label `low`. |
| 888 | `            b1_low = res` | Keeps the results for line 895. |
| 889 | `    for s_name, v in (('asmcopy_c', 'H5 (B2, asmcopy_c, label low)'),):` | A loop over one pair: the variant `asmcopy_c` of step B2 and the entry name `H5 (B2, asmcopy_c, label low)`. Only this variant is mapped to H5 (point A20 of the deviations note [Ref3]). |
| 890 | `        res = {s: r['groups'].get(s_name, {}).get('labels', {}).get('low') for s, r in per('B2').items()}` | `res`: per session, the result of B2 for this variant and the label `low`. |
| 891 | `        flags = {}` | `flags`: empty at first. |
| 892 | `        for s, x in res.items():` | Loop over the sessions. |
| 893 | `            if not x:` | A session without this result. |
| 894 | `                continue` | It is skipped. |
| 895 | `            ref = b1_low.get(s)` | `ref`: the B1 result of the same session for the label `low`. |
| 896 | `            flags[s] = 'not observed' if x['decision'] == 'not observed' or not ref or ref['sign'] is None else \` | The flag is `not observed` when the B2 result is `not observed`, when B1 is missing, or when B1 has no resolved sign. The other cases follow in line 897. |
| 897 | `                'hold' if x['decision'] == 'resolved' and x['sign'] == ref['sign'] else 'fail'` | Continues line 896: `hold` when the B2 difference is resolved with the sign of B1. Every other case is `fail`, also a resolved difference with the opposite sign. |
| 898 | `        put(v, flags, 'H5 predicts a resolved difference asmcopy_c - asmcopy of the sign of B1; "not observed" also when B1 of the session has no resolved sign')` | Stores the entry. H5 says that the copy difference comes from the instruction order of the C loop [Ref2]. By the text of the entry it predicts a resolved difference between `asmcopy_c` and `asmcopy` with the sign of B1. |
| 899 | `    flags = {}` | `flags`: starts empty again, now for H6. |
| 900 | `    for s, r in per('B3').items():` | Loop over the sessions that ran step B3. |
| 901 | `        ch = [c for b in r['change_against_B1'].values() for c in b.values()]` | `ch`: all change entries of the session: one per build, label and CPU (line 360). |
| 902 | `        seen_all = r['change_against_B1'] and all(any(c['decision'] != 'not observed' for c in b.values()) for b in r['change_against_B1'].values())` | `seen_all`: true when the session has at least one build and every build has at least one entry whose word is not `not observed`. |
| 903 | `        # Plan, step B3: "only after a resolved difference in B1". Without it there is no difference that an offset could change.` | Comment: the plan runs step B3 only after a resolved difference in B1. Without it there is no difference that an offset could change. |
| 904 | `        b1_labels = b1.get(s, {}).get('groups', {}).get('8M', {}).get('labels', {})` | `b1_labels`: the B1 results at 8 MiB of the same session, per label. |
| 905 | `        b1_resolved = any(v['decision'] == 'resolved' for v in b1_labels.values())` | `b1_resolved`: true when at least one label of B1 is resolved. |
| 906 | `        flags[s] = 'not observed' if not b1_resolved or not seen_all or len(r['change_against_B1']) < 3 else \` | The flag is `not observed` when B1 is not resolved, when `seen_all` is false, or when the session has fewer than 3 builds. The other cases follow in line 907. |
| 907 | `            'hold' if any(c['decision'] == 'resolved' for c in ch) else 'fail'` | Continues line 906: `hold` when at least one change is resolved. If not, `fail`. |
| 908 | `    put('H6 (B3)', flags, 'H6 predicts a resolved change of d at one offset; fail = resolved on no CPU for all three builds; '` | Stores the entry `H6 (B3)`. H6 says that the copy difference comes from the address of the loop [Ref2]. By the text of the entry it predicts a resolved change of `d` at one offset, and `fail` means that the change is resolved on no CPU for all three builds. The text goes on in line 909. |
| 909 | `        'not observed = B1 at 8 MiB of the session has no resolved difference, or a build is missing or has no CPU with 3 processes of one label in B1 and in the build')` | Continues the text of line 908: the cases of `not observed`: B1 at 8 MiB of the session has no resolved difference, a build is missing, or a build has no CPU with 3 processes of one label in B1 and in the build. |

### `cross`: the entries for H3a (B4), H1 (B6) and H7 for read (B7) (lines 910 to 948)

| Line | Source | Explanation |
|---:|---|---|
| 910 | `    b4 = per('B4')` | `b4`: the results of step B4 per session. |
| 911 | `    # The flag of a session comes from that session alone (plan, rule 10): a case on any CPU is a failed prediction there.` | Comment: the flag of a session comes from that session alone (rule 10 of the plan). A case on any CPU is a failed prediction in that session. |
| 912 | `    # The word "rejected" also needs one CPU with a case in every session (handoff B.10, DEVIATIONS-scripts.md A13 and A32).` | Comment: the word `rejected` also needs one CPU with a case in every session. The comment names section B.10 of the handoff note and the points A13 and A32 of the deviations note. |
| 913 | `    with_case = {s: {c for c, v in r['per_cpu'].items() if v['cases']} for s, r in b4.items()}` | `with_case`: per session, the set of the CPUs with a case `a` or `b` (line 430). |
| 914 | `    common = set.intersection(*with_case.values()) if with_case else set()` | `common`: the CPUs that have a case in every session. |
| 915 | `    flags = {s: 'fail' if c else 'not observed' for s, c in with_case.items()}` | The flag of a session for H3a: `fail` when at least one CPU has a case, and `not observed` when none has. |
| 916 | `    if flags:` | Only when a session ran B4. |
| 917 | `        any_cpu = two_sessions(flags)` | `any_cpu`: the word of line 856 from these flags, without the condition of the same CPU. |
| 918 | `        out['H3a (B4)'] = dict(` | Stores the entry `H3a (B4)`. The record starts in this line and goes on to line 924. |
| 919 | `            word='not rejected' if any_cpu == 'rejected' and not common else any_cpu, per_session=flags,` | Continues the record: the word. When `any_cpu` is `rejected` and no CPU has a case in every session, the word is `not rejected`. In every other case it is `any_cpu`. The flags per session follow. |
| 920 | `            cpus_with_a_case={s: sorted(c) for s, c in with_case.items()}, cpus_with_a_case_in_every_session=sorted(common),` | Continues the record: the CPUs with a case per session, and the CPUs with a case in every session. |
| 921 | `            word_without_the_same_cpu_condition=any_cpu,` | Continues the record: `word_without_the_same_cpu_condition`, the word `any_cpu`. It is kept beside the chosen word. The deviations note says that the condition of the same CPU is an open decision for the user [Ref3]. |
| 922 | `            basis='fail = case (a) or (b) on a CPU of that session; "rejected" needs one CPU with a case in every session (such CPUs: %s; CPUs with a case: %s). '` | Continues the record: `basis`, the text that explains the flag `fail` and the condition of the same CPU. It goes on in lines 923 to 924. |
| 923 | `                  'Without the same-CPU condition (plan, step B4) the word would be "%s"' % (` | Continues the text: without the condition of the same CPU the word would be `any_cpu`. The text names step B4 of the plan for that reading. |
| 924 | `                      sorted(common), ', '.join('%s=%s' % (s, sorted(c)) for s, c in with_case.items()), any_cpu))` | Continues the text: its three values: the CPUs with a case in every session, the CPUs with a case per session, and `any_cpu`. |
| 925 | `    b6 = per('B6')` | `b6`: the results of step B6 per session. |
| 926 | `    res6 = {s: {('state', c, 1 if v['difference'] > 0 else -1) for c, v in r['state'].items() if v['decision'] == 'resolved'} \|` | `res6`: per session, the set of its resolved results. For each CPU with a resolved difference between low and high it holds the word `state`, the CPU and the sign of the difference. The line goes on in line 927. |
| 927 | `            ({('size', r['size']['labels']['none']['sign'])} if r['size']['labels']['none']['decision'] == 'resolved' else set()) for s, r in b6.items()}` | Continues line 926: the set also holds the word `size` with its sign when the comparison of 8 MiB with 1 MiB is resolved. The loop over the sessions follows. |
| 928 | `    common6 = set.intersection(*res6.values()) if res6 else set()` | `common6`: the resolved results that occur in every session, with the same CPU and the same sign. |
| 929 | `    flags = {}` | `flags`: empty at first. |
| 930 | `    for s, r in b6.items():` | Loop over the sessions. |
| 931 | `        nothing = all(v['decision'] == 'not observed' for v in r['state'].values()) and r['size']['labels']['none']['decision'] == 'not observed'` | `nothing`: true when every CPU of the first comparison is `not observed` and the second comparison is `not observed` too. |
| 932 | `        flags[s] = 'not observed' if nothing else 'fail' if (common6 if len(b6) > 1 else res6[s]) else 'hold'` | The flag for H1. `not observed` when `nothing` is true. If not, `fail` when a resolved result counts: with more than one session it must be in `common6`, and with one session any resolved result of that session counts. Every other case is `hold`. |
| 933 | `    put('H1 (B6)', flags, 'fail = a resolved difference (low against high on one CPU, or 8 MiB against 1 MiB); with 2 sessions the same result in both: %s. '` | Stores the entry `H1 (B6)`. H1 predicts that the rate of old read at 8 MiB differs by no resolved amount between low and high intervals, and by none from its rate at 1 MiB [Ref2]. So a resolved difference is the failure. With 2 sessions it must be the same result in both. The text goes on in line 934. |
| 934 | `        'The two parts are reported apart in the tables of the step' % sorted(common6))` | Continues the text: the two parts are reported apart in the tables of the step. The value of the text is the list `common6`. |
| 935 | `    b7 = per('B7')` | `b7`: the results of step B7 per session. |
| 936 | `    for hyp, factors in (('H7a (B7, read)', ('stop', 'interval')), ('H7b (B7, read)', ('start',))):` | Loop over two hypotheses for the read kernels. H7a is tested with the factors `stop` and `interval`: it says that a part of the read difference is made by the stop method and the short interval. H7b is tested with the factor `start`: it says that a part is made by the common start [Ref2]. |
| 937 | `        flags = {}` | `flags`: empty at first. |
| 938 | `        for s, r in b7.items():` | Loop over the sessions. |
| 939 | `            ch = [c for c in r['changes'].values() if c['factor'] in factors]` | `ch`: the changes of `D` of the session whose factor belongs to the hypothesis (line 548). |
| 940 | `            seen = [c for c in ch if c['decision'] != 'not observed']` | `seen`: those of them whose word is not `not observed`. |
| 941 | `            # Plan, step B7: if the reproduction condition gives no resolved D in either way of running, no cause is assigned.` | Comment: by step B7 of the plan no cause is assigned when the reproduction condition gives no resolved `D` in either way of running. |
| 942 | `            flags[s] = 'not observed' if not seen or not r.get('reproduced_in_either_way') else \` | The flag is `not observed` when no change could be decided, or when `D` was not reproduced in either way (line 554). The other cases follow in lines 943 to 944. |
| 943 | `                'hold' if any(c['decision'] == 'resolved' for c in seen) else \` | Continues line 942: `hold` when at least one change is resolved. |
| 944 | `                'not resolved' if any(c.get('metrics_disagree') for c in seen) else 'fail'` | Continues line 942: `not resolved` when no change is resolved and the two metrics disagree for at least one pair of settings. Every other case is `fail`. |
| 945 | `        put(hyp, flags, 'predicts a resolved change of D when %s changes; fail = no resolved change in any pair of settings, with M_hist and M_sum in agreement. '` | Stores the entry. By its text the hypothesis predicts a resolved change of `D` when its factor changes. `fail` means no resolved change in any pair of settings, with `M_hist` and `M_sum` in agreement. The text goes on in lines 946 to 948. |
| 946 | `            'not observed also when the reproduction condition (pass/500/common) gives no resolved D of the sign of 2026-11-13, '` | Continues the text: the flag is also `not observed` when the reproduction condition `pass/500/common` gives no resolved `D` of the sign of 2026-11-13. |
| 947 | `            'neither with the kernels in one process nor with one kernel per process; '` | Continues the text: neither with the kernels in one process nor with one kernel per process. |
| 948 | `            'not resolved = no resolved change, and M_hist and M_sum give another word or sign for a pair' % ' or '.join(factors))` | Continues the text: `not resolved` means no resolved change, and another word or sign of the two metrics for a pair. The end of the line puts the factor names into the text. |

### `cross`: the entries for B10, H11, H8, the statement of B5 and H9a (lines 949 to 1005)

| Line | Source | Explanation |
|---:|---|---|
| 949 | `    b10 = per('B10')` | `b10`: the results of step B10 per session. |
| 950 | `    for hyp, factors in (('H7a (B10, write)', ('stop', 'interval')), ('H7b (B10, write)', ('start',))):` | Loop over the same two hypotheses for the write kernels, with the same factors. |
| 951 | `        flags = {}` | `flags`: empty at first. |
| 952 | `        for s, r in b10.items():` | Loop over the sessions. |
| 953 | `            seen = [c for c in r['spread_changes'].values() if c['factor'] in factors and c['decision'] != 'not observed']` | `seen`: the changes of the spread of the session whose factor belongs to the hypothesis and whose word is not `not observed` (line 656). |
| 954 | `            flags[s] = 'not observed' if not seen else 'hold' if any(c['decision'] == 'resolved' for c in seen) else 'fail'` | The flag: `not observed` without such a change, `hold` when at least one is resolved, and `fail` in every other case. |
| 955 | `        put(hyp, flags, 'predicts a resolved change of the spread of a kernel when %s changes; fail = no resolved change for any kernel and pair of settings' % ' or '.join(factors))` | Stores the entry. By its text the hypothesis predicts a resolved change of the spread of a kernel when its factor changes. `fail` means no resolved change for any kernel and pair of settings. |
| 956 | `    keys = sorted({(st, k) for r in b10.values() for st, v in r['settings'].items() for k in v['kernels']})` | `keys`: every pair of a setting and a kernel that occurs in a session, sorted. |
| 957 | `    for st, k in keys:` | Loop over these pairs. |
| 958 | `        w = {s: r['settings'][st]['kernels'][k]['H11'] for s, r in b10.items() if st in r['settings'] and k in r['settings'][st]['kernels']}` | `w`: the word for H11 of this setting and kernel (line 639), per session that has it. |
| 959 | `        flags = {s: {'supported': 'hold', 'contradicted': 'fail', 'not observed': 'not observed'}.get(x, 'not resolved') for s, x in w.items()}` | The flag per session: `supported` gives `hold`, `contradicted` gives `fail`, `not observed` stays, and every other word gives `not resolved`. |
| 960 | `        word = two_sessions(flags)` | `word`: the word of line 856 from these flags. |
| 961 | `        if len(w) > 1 and all(x == 'supported' for x in w.values()):` | With more than one session, and all of them `supported`. |
| 962 | `            word = 'not rejected (supported)'` | The word becomes `not rejected (supported)`. |
| 963 | `        elif word == 'rejected':` | The word is `rejected`. This needs at least 2 sessions that are all `contradicted`. |
| 964 | `            word = 'rejected (contradicted)'` | It becomes `rejected (contradicted)`. |
| 965 | `        elif len(w) > 1 and word == 'not rejected':` | With more than one session and the word `not rejected`, in a case other than line 961. |
| 966 | `            word = 'not resolved'` | The word becomes `not resolved`. |
| 967 | `        out['H11 (B10, %s, %s)' % (st, k)] = dict(word=word, per_session=w, basis='decide.decide_h11 per session; the mesh that rose is not compared between sessions by this script')` | Stores the entry for H11 with the setting and the kernel in its name, and with the words per session. Its text says that this script does not compare which mesh rose between the sessions. |
| 968 | `    b8 = per('B8')` | `b8`: the results of step B8 per session. |
| 969 | `    if b8:` | Only when a session ran B8. |
| 970 | `        w = {s: r['H8'] for s, r in b8.items()}` | `w`: the word for H8 per session (line 711). |
| 971 | `        word = 'not rejected (supported)' if len(w) > 1 and all(x == 'supported' for x in w.values()) else \` | `word`: with more than one session, `not rejected (supported)` when every session is `supported`. The other cases follow in lines 972 to 973. |
| 972 | `            'rejected (contradicted)' if len(w) > 1 and all(x == 'contradicted' for x in w.values()) else \` | Continues line 971: `rejected (contradicted)` when there is more than one session and every session is `contradicted`. |
| 973 | `            'not resolved' if len(w) > 1 else 'one session only: %s' % list(w.values())[0]` | Continues line 971: `not resolved` for every other case with more than one session. With one session the word is the text `one session only:` and the word of that session. |
| 974 | `        out['H8 (B8)'] = dict(word=word, per_session=w, basis='the bracket of asm read lies wholly below (supported) or wholly above (contradicted) the bracket of old read, in both sessions',` | Stores the entry `H8 (B8)` with the words per session and the text of its basis. The record goes on in line 975. |
| 975 | `                              word_without_labels='not resolved', without_labels_basis='a bracket is built from the labels split and uniform')` | Continues line 974: `word_without_labels` is `not resolved`. The reason given: a bracket is built from the labels split and uniform, and these labels are not used (line 1006). |
| 976 | `    flags = {}` | `flags`: empty at first, now for the statement of step B5. |
| 977 | `    for s, r in per('B5').items():` | Loop over the sessions that ran B5. |
| 978 | `        v = r['variants'].get('read_sparse')` | `v`: the result of the variant `read_sparse`, or `None`. |
| 979 | `        olds = set(r['oldread_patterns'].values())` | `olds`: the set of the pattern labels of old read over the processes of the session (line 723). |
| 980 | `        flags[s] = 'not observed' if not v or v['shows_pattern_and_total_of_oldread'] == 'not observed' or olds != {'split'} else \` | The flag is `not observed` when the variant is missing, when its answer is `not observed`, or when old read is not split in every process. The other cases follow in lines 981 to 982. |
| 981 | `            'fail' if v['shows_pattern_and_total_of_oldread'] == 'yes' else \` | Continues line 980: `fail` when the answer is `yes`: `read_sparse` shows the pattern and the total of old read. |
| 982 | `            'not resolved' if v['shows_pattern_and_total_of_oldread'] == 'not resolved' else 'hold'` | Continues line 980: `not resolved` when the answer is `not resolved`. Every other case is `hold`. |
| 983 | `    put('B5 statement "vector adds are needed for the split pattern of old read"', flags,` | Stores the entry for the statement of step B5: vector adds are needed for the split pattern of old read. `read_sparse` is a load-only loop with 16 instructions per 128 B, as the old read loop has, and without a vector add [Ref1]. The call goes on in lines 984 to 985. |
| 984 | `        'fail = read_sparse shows the pattern and total of old read (total difference not resolved with M_hist and with M_sum); '` | Continues the call: the text. `fail` means that `read_sparse` shows the pattern and the total of old read, with a total difference that is not resolved with `M_hist` and with `M_sum`. |
| 985 | `        'not observed also when old read is not split in every process; not resolved = same pattern, and M_hist and M_sum give another word or sign for the total')` | Continues the text: the flag is also `not observed` when old read is not split in every process. `not resolved` means the same pattern, and another word or sign of the two metrics for the total. |
| 986 | `    b5_name = 'B5 statement "vector adds are needed for the split pattern of old read"'` | `b5_name`: the name of this entry. |
| 987 | `    if b5_name in out:` | Only when the entry exists. |
| 988 | `        # Without labels (A33) only the total can decide: a resolved difference old read - read_sparse under both metrics` | Comment: without labels (point A33 of the deviations note) only the total can decide. The comment goes on in line 989. |
| 989 | `        # means that read_sparse does not show the total of old read, whatever its pattern.` | Comment, continued: a difference between old read and `read_sparse` that is resolved under both metrics means that `read_sparse` does not show the total of old read, whatever its pattern. |
| 990 | `        nolab = {}` | `nolab`: the flag per session without labels, empty at first. |
| 991 | `        for s, r in per('B5').items():` | Loop over the sessions that ran B5. |
| 992 | `            d = (r['variants'].get('read_sparse') or {}).get('total_difference')` | `d`: the decision of the total difference for `read_sparse` (line 742), or `None`. |
| 993 | `            nolab[s] = 'not observed' if not d or d['decision'] == 'not observed' else \` | The flag is `not observed` when the decision is missing or is `not observed`. The other cases follow in line 994. |
| 994 | `                'hold' if d['decision'] == 'resolved' and not d.get('metrics_disagree') else 'not resolved'` | Continues line 993: `hold` when the difference is resolved and the two metrics agree. Every other case is `not resolved`. |
| 995 | `        out[b5_name].update(` | Adds three fields to the entry. Lines 996 to 998 list them. |
| 996 | `            word_without_labels='not observed' if all(x == 'not observed' for x in nolab.values()) else` | `word_without_labels`: `not observed` when every session is `not observed`. The other cases follow in line 997. |
| 997 | `            'not rejected' if all(x == 'hold' for x in nolab.values()) else 'not resolved', per_session_without_labels=nolab,` | Continues line 996: `not rejected` when every session is `hold`, and `not resolved` in every other case. Then `per_session_without_labels`, the flags of line 990. |
| 998 | `            without_labels_basis='hold = old read - read_sparse is resolved with M_hist and with M_sum, so the total alone decides; otherwise the rule needs the label')` | `without_labels_basis`: the text that explains these flags. `hold` means that old read minus `read_sparse` is resolved with both metrics, so the total alone decides. |
| 999 | `    flags = {s: {'same pattern': 'fail', 'pattern as H9a predicts': 'hold', 'not observed': 'not observed'}.get(r['pattern_result'], 'not resolved') for s, r in per('B9').items()}` | The flag per session for H9a, from the pattern result of step B9 (line 771): `same pattern` gives `fail`, `pattern as H9a predicts` gives `hold`, `not observed` stays, and every other result gives `not resolved`. |
| 1000 | `    put('H9a (B9)', flags, 'fail = the same pattern with one buffer and with two')` | Stores the entry `H9a (B9)`. `fail` means the same pattern with one buffer and with two. |
| 1001 | `    if 'H9a (B9)' in out:` | Only when the entry exists. |
| 1002 | `        out['H9a (B9)'].update(word_without_labels='not resolved', without_labels_basis='the prediction is worded with the labels split and uniform')` | Adds `word_without_labels`: `not resolved`. The reason given: the prediction is worded with the labels split and uniform. |
| 1003 | `    return out` | Returns all entries. |

### `LABEL_NOTE` and the function `analyze`: all steps of all sessions (lines 1006 to 1034)

| Line | Source | Explanation |
|---:|---|---|
| 1006 | `LABEL_NOTE = ('The pattern labels split, mixed and uniform are NOT USED (user decision of 2026-11-13, decisions.md item 2: "Report q, no labels. '` | `LABEL_NOTE`: a text for the output. It says that the pattern labels split, mixed and uniform are not used, by a decision of the user of 2026-11-13. It names item 2 of the file `decisions.md` and quotes it: report `q`, no labels [Ref5]. The text goes on in lines 1007 to 1008. |
| 1007 | `              'Where a rule needs a label that the data do not give, the word is not resolved"). The tables of B8, B5 and B9 and the entries '` | Continues the text: the end of the quote. Where a rule needs a label that the data do not give, the word is not resolved. Then the next sentence starts: the tables of B8, B5 and B9 and three entries still print what the limits give. |
| 1008 | `              'H8, H9a and the B5 statement still print what the provisional limits 0.65 and 0.85 give. Each such entry also carries its word without labels.')` | Continues the text: these entries are H8, H9a and the statement of B5, and the limits are the provisional 0.65 and 0.85. Each such entry also holds its word without labels. |
| 1011 | `def analyze(sessions):` | Starts the function `analyze`. `sessions` maps each session name to its list of processes. |
| 1012 | `    """sessions: {name: [Proc]} -> the summary (a dict that json can write)."""` | Docstring: the result is the summary, a dictionary that the module `json` can write. |
| 1013 | `    summary = dict(sessions={}, limits=[` | Starts the summary: an empty dictionary for the sessions, and the list `limits`. The list holds five texts that the output prints as the limits of the analysis. |
| 1014 | `        'No value here is the traffic of the time in which all threads ran: a thread records only its total (handoff B.10). Rule 6 of the plan is met only in part.',` | Limit 1: no value here is the traffic of the time in which all threads ran. The reason given: a thread records only its total. Rule 6 of the plan is met only in part. |
| 1015 | `        'Page state of a process with more than one thread: the reading for an interval is the reading after the interval before it; the warm-up pass lies between (handoff B.6).',` | Limit 2: in a process with more than one thread, the page state for an interval is the reading after the interval before it. The warm-up pass lies between that reading and the interval. |
| 1016 | `        'The limits 0.65 and 0.85 (pattern), 69 and 70.5 GB/s (level), 100 us and 5 ms (irregular interval) are provisional. Check the distributions (q and reference rates are in the json) before the labels are used.',` | Limit 3: the limits 0.65 and 0.85 (pattern), 69 and 70.5 GB/s (level), 100 us and 5 ms (irregular interval) are provisional. The text asks to check the distributions before the labels are used. |
| 1017 | `        'With --stop pass the end skew is reported and does not make an interval irregular (see DEVIATIONS-scripts.md).',` | Limit 4: with `--stop pass` the end skew is reported and does not make an interval irregular. |
| 1018 | `        LABEL_NOTE])` | Limit 5: the text of line 1006. The line ends the list and the summary. |
| 1019 | `    for name, procs in sessions.items():` | Loop over the sessions. |
| 1020 | `        res, ctx = {}, {}` | `res`: the results per step. `ctx`: the dictionary that passes values between the steps of this session (line 343). Both are empty at first. |
| 1021 | `        steps = {p.step for p in procs}` | `steps`: the step names that occur in the header lines of the session. |
| 1022 | `        for step in [s for s in ORDER if s in steps] + sorted(steps - set(ORDER)):` | Loop over the steps: first the known ones in the order of `ORDER` (line 851), then every other name in sorted order. |
| 1023 | `            g = [p for p in procs if p.step == step]` | `g`: the processes of this step. |
| 1024 | `            if step == 'B8':` | Only for step B8. |
| 1025 | `                for p in g:` | Loop over its processes. |
| 1026 | `                    cp = [x['cpu'] for iv in p.ordered[:1] for x in iv.rows]` | `cp`: the CPUs of the threads, read from the `T` rows of the first interval of the process. |
| 1027 | `                    p.threads_mesh0 = sum(1 for c in cp if c in MESH0_CPUS)` | `threads_mesh0`: the number of these CPUs that lie in 0 to 63. |
| 1028 | `                    p.threads_mesh1 = len(cp) - p.threads_mesh0` | `threads_mesh1`: the number of the other threads. |
| 1029 | `            res[step] = ANALYZERS.get(step, a_short)(g, ctx, step)` | Calls the analysis function of the step from the table of line 849, or `a_short` for a name that the table does not hold. The result is stored under the step name. |
| 1030 | `        summary['sessions'][name] = res` | Stores the results of the session. |
| 1031 | `    summary['hypotheses'] = cross(summary['sessions'])` | `hypotheses`: the words over all sessions (line 868). |
| 1032 | `    return summary` | Returns the summary. |

### Text output: `fmt`, `text_step` and `text_hypotheses` (lines 1035 to 1074)

| Line | Source | Explanation |
|---:|---|---|
| 1035 | `# ---------------------------------------------------------------- text output` | Comment: a divider. The functions that build the text output start here. |
| 1037 | `def fmt(x, nd=2):` | Starts the function `fmt`. It turns a value into text for a table. `nd` is the number of decimals, 2 unless the caller gives another. |
| 1038 | `    return '-' if x is None else ('%.*f' % (nd, x)) if isinstance(x, float) else str(x)` | `None` gives `-`. A floating-point number is printed with `nd` decimals. Every other value is printed as it is. |
| 1041 | `def text_step(session, step, res):` | Starts the function `text_step`. It builds the text table of one step in one session. |
| 1042 | `    L = ['%s, session %s' % (step, session)]` | `L`: the lines of the text. The first line names the step and the session. |
| 1043 | `    ld = res['load']` | `ld`: the load values of the report (line 248). |
| 1044 | `    L.append('system load: 1-minute load average %s to %s over the launches; longest wait for a quiet system %s s; logins %s' % (` | Adds the line of the system load: the lowest and the highest load average over 1 minute at the starts of the processes, the longest wait for a quiet system in seconds, and the login counts. The call goes on in line 1045. |
| 1045 | `        fmt(ld['loadavg_1min_min']), fmt(ld['loadavg_1min_max']), fmt(ld['waited_s_max']), ','.join(ld['logins'])))` | Continues line 1044: the four values. |
| 1046 | `    L.append('processes: %d in the files, %d used; P rows %d, of them with NA %d' % (res['n_processes'], res['n_used'], res['page_rows'], res['page_rows_NA']))` | Adds the line of the processes: how many are in the files and how many are used, and the number of `P` rows and of those with `NA`. |
| 1047 | `    for x in res['left_out']:` | Loop over the processes that were left out. |
| 1048 | `        L.append('  left out: %s %s: %s' % (x['file'], x['tag'], x['reason']))` | Adds one line per process: file, tag and reason. |
| 1049 | `    for x in res['irregular_intervals']:` | Loop over the irregular intervals. |
| 1050 | `        L.append('  irregular interval, not used: %s %s round %d pos %d %s, late threads %d, end skew %s ms' % (` | Adds one line per irregular interval. It says that the interval is not used, and gives file, tag, round, position, entry, late threads and end skew in ms. The call goes on in line 1051. |
| 1051 | `            x['file'], x['tag'], x['round'], x['pos'], x['entry'], x['late_threads'], x['end_skew_ms']))` | Continues line 1050: the values. |
| 1052 | `    head = ('what', 'decision', 'processes', 'A/A spread GB/s', 'value GB/s', 'note')` | `head`: the six column names of the table: `what`, `decision`, `processes`, `A/A spread GB/s`, `value GB/s` and `note`. |
| 1053 | `    rows = [(r['what'], r['decision'], str(r['n_processes']), fmt(r['aa_spread']), fmt(r['value']), r['note']) for r in res.get('rows', [])]` | `rows`: the table lines of the step as texts. The A/A spread and the value are printed with 2 decimals, or as `-` when there is none (line 1037). |
| 1054 | `    w = [max(len(x[i]) for x in [head] + rows) for i in range(5)]` | `w`: the width of each of the first five columns: the longest text in the column, the column name included. |
| 1055 | `    for x in [head] + rows:` | Loop over the column names and the table lines. |
| 1056 | `        L.append('  '.join(x[i].ljust(w[i]) for i in range(5)) + '  ' + x[5])` | Adds one line: the first five fields, each padded with spaces to its column width and joined with two spaces, then the note. |
| 1057 | `    for k in ('reproduction_in_one_process', 'H8', 'pattern_result', 'note'):` | Loop over four keys of the report of a step. |
| 1058 | `        if k in res:` | Only when the report has the key. |
| 1059 | `            L.append('%s: %s' % (k, res[k]))` | Adds a line with the key and its value. These are the reproduction result of B7, the word for H8, the pattern result of B9 and the note of the counter steps. |
| 1060 | `    if step in ('B8', 'B5', 'B9'):` | Only for the steps B8, B5 and B9. |
| 1061 | `        L.append('labels: ' + LABEL_NOTE)` | Adds the line that says that the labels are not used (line 1006). |
| 1062 | `    return '\n'.join(L) + '\n'` | Returns the lines as one text. Each line ends with a line end. |
| 1065 | `def text_hypotheses(summary):` | Starts the function `text_hypotheses`. It builds the text of the hypothesis entries. |
| 1066 | `    L = ['Hypotheses over all sessions (words of rule 11 of the plan; "rejected" needs 2 sessions)']` | `L`: the lines. The first line is the heading. It says that the words are those of rule 11 of the plan and that `rejected` needs 2 sessions. |
| 1067 | `    for name, h in summary['hypotheses'].items():` | Loop over the entries. |
| 1068 | `        L.append('  %s: %s \| per session: %s \| %s' % (name, h['word'], ', '.join('%s=%s' % kv for kv in h['per_session'].items()), h['basis']))` | Adds one line per entry: its name, its word, the flag of each session in the form `session=flag`, and the text of its basis. The character `\|` divides the last three parts. |
| 1069 | `        if 'word_without_labels' in h:` | Only for an entry that has a word without labels. |
| 1070 | `            L.append('      LABELS NOT USED (user decision of 2026-11-13): the word above is the output of the label rule. Without labels the word is "%s" (%s)' % (` | Adds a second line that starts with `LABELS NOT USED`. It says that the word above is the output of the label rule, and it gives the word without labels with its reason. The call goes on in line 1071. |
| 1071 | `                h['word_without_labels'], h['without_labels_basis']))` | Continues line 1070: the two values. |
| 1072 | `    return '\n'.join(L) + '\n'` | Returns the lines as one text. |

### Function `main`: the command line and the output files (lines 1075 to 1104)

| Line | Source | Explanation |
|---:|---|---|
| 1075 | `def main(argv=None):` | Starts the function `main`. `argv` is the list of arguments. With `None` the arguments of the command line are used. |
| 1076 | `    ap = argparse.ArgumentParser(description='analysis of the bwx runs (handoff.md B.10)')` | `ap`: the reader of the command line, with a short description for the help text. |
| 1077 | `    ap.add_argument('--session', nargs='+', action='append', required=True, metavar=('NAME', 'PATH'))` | The option `--session`: it takes one or more values, it is required, and it may be given several times. Each use adds one list of its values. |
| 1078 | `    ap.add_argument('--out')` | The option `--out`: the folder for the output files. It may be left out. |
| 1079 | `    a = ap.parse_args(argv)` | `a`: the values that the command line gave. A missing `--session` ends the script here with a usage message and exit status 2. |
| 1080 | `    sessions = {}` | `sessions`: the processes per session name, empty at first. |
| 1081 | `    for s in a.session:` | Loop over the uses of `--session`. |
| 1082 | `        if len(s) < 2:` | Tests whether the option has only one value. |
| 1083 | `            ap.error('--session needs a name and at least one path')` | Then the script prints the usage and the message that a name and at least one path are needed, and it ends with exit status 2. |
| 1084 | `        sessions.setdefault(s[0], []).extend(load_session(s[0], s[1:]))` | Loads the files of the paths (line 215) and adds their processes to the session of this name. So two uses of `--session` with the same name fill one session. |
| 1085 | `    summary = analyze(sessions)` | `summary`: the analysis of all sessions (line 1011). |
| 1086 | `    texts = {}` | `texts`: the output texts by name, empty at first. |
| 1087 | `    for name, res in summary['sessions'].items():` | Loop over the sessions. |
| 1088 | `        for step, r in res.items():` | Loop over the steps of the session. |
| 1089 | `            texts[step] = texts.get(step, '') + text_step(name, step, r) + '\n'` | Adds the table of the step (line 1041) to the text of this step name. So one text holds the tables of all sessions for one step. |
| 1090 | `    texts['hypotheses'] = text_hypotheses(summary) + '\nLimits:\n' + '\n'.join('  - ' + x for x in summary['limits']) + '\n'` | `texts['hypotheses']`: the hypothesis entries (line 1065), then the heading `Limits:` and the five limits of line 1013, each as one list item. |
| 1091 | `    if a.out:` | Only with `--out`. |
| 1092 | `        os.makedirs(a.out, exist_ok=True)` | Makes the folder. It is no error when the folder exists. |
| 1093 | `        with open(os.path.join(a.out, 'summary.json'), 'w') as fh:` | Opens the file `summary.json` in the folder for writing. |
| 1094 | `            json.dump(summary, fh, indent=1, default=str)` | Writes the summary as JSON with an indent of 1 space. `default=str` writes a value that JSON cannot hold as its text. |
| 1095 | `        for step, t in texts.items():` | Loop over the texts. |
| 1096 | `            with open(os.path.join(a.out, step + '.txt'), 'w') as fh:` | Opens a file with the name of the step and the ending `.txt`. The hypotheses go to `hypotheses.txt`. |
| 1097 | `                fh.write(t)` | Writes the text. |
| 1098 | `    for t in texts.values():` | Loop over the texts again. |
| 1099 | `        sys.stdout.write(t + '\n')` | Prints each text to the standard output, followed by an empty line. This happens with and without `--out`. |
| 1100 | `    return 0` | Returns 0, the exit status for success. |
| 1103 | `if __name__ == '__main__':` | True only when the file is started as a program, not when another file imports it. |
| 1104 | `    sys.exit(main())` | Runs `main` and ends the script with its return value as the exit status. |

## References

- [Ref1] The handoff note: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Section B.1: the kernels of the runner. Section B.2: the options of the runner. Section B.3: the fields of the `I`, `T`, `P` and `C` rows. Section B.4: the two stop methods, the flag `late` and the irregular interval. Section B.5: the start offsets. Section B.6: the page state and when it is read. Section B.8: the counters. Section B.9: the sequence and the options of each step. Section B.10: the decision rules.
- [Ref2] The plan: the file `tests/2026-11-13-new-read-kernel/report/plan.md` of the same repo. The section "The two questions" with the questions Q1b and Q2a, the table of the hypotheses H1 to H11, the rules 3, 4, 5, 6, 8, 10 and 11 for the deciding measurements, and the tables of the steps of Part B and Part C with the prediction that each step tests. The protocol of Part C: a row whose running time is below its enabled time is not used.
- [Ref3] The deviations note: the file `code/bwx-2026-11-13/DEVIATIONS-scripts.md` of the same repo, table "Analysis", points A1 to A33.
- [Ref4] The file `code/new-test-kernel/decide.py` of the same repo: the functions `level`, `process_value`, `resolved`, `decide_one_thread`, `decide_b6_state`, `decide_setting`, `decide_change`, `controls_from_aa` and `decide_h11`.
- [Ref5] The file `tests/2026-11-13-new-read-kernel/report/decisions.md` of the same repo, item 2: the answer "Report q, no labels".
- [Ref6] The source of the runner: the file `code/bwx-2026-11-13/bwx.c` of the same repo. The output loop of `main` prints the rows and the comment lines with the column names. The first comment line says that a copy counts the bytes read plus the bytes written. The constant `LATE_NS` is 100000 ns, and the worker sets the flag `late` only with the common stop. The defaults of the options are in the initial values of `cfg` and in `main` before the option loop.
- [Ref7] The run script: the file `code/bwx-2026-11-13/run_bwx.sh` of the same repo. Its function `one` writes the header line, the line `-- killed` and the line `-- failed`.
