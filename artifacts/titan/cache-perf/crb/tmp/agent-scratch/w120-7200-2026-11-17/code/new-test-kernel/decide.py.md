# `decide.py` explained, line by line

- Source file: `new-test-kernel/decide.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 199 lines, 11899 bytes).
- sha256 of the source when this page was built: `98c551bc554ad28b70b2566863657af2ba72eda1f21d66777a532f093905989f`.

## Short version: purpose

`decide.py` holds the decision rules of section B.10 of the handoff note as Python functions. Each rule says when a difference between two kernels, or a change of such a difference, counts as resolved against the difference between two copies of one loop. Started as a program, the file only tests these rules on invented values and reads no measurement.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan. Its section B.10 gives the decision rules in words.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Step**: one named batch of processes of the plan. The steps B1, B2, B3 and B6 run one thread. The steps B7 and B10 run 120 threads.
- **Session of the plan**: one run of all steps of Parts B and C. The plan asks for 2 sessions some hours apart. This is not the session of the later rerun.
- **A/A pair**: one loop that stands in the binary twice, under two names, for example `asmread` and `asmread2`.
- **A/A difference**: the difference between the rates of the two copies of an A/A pair. It shows how much two equal loops differ.
- **A/A spread**: the largest absolute A/A difference of a group of processes. It is never negative.
- **Reference interval**: an interval of `asmread` that is timed directly before or after a compared interval, to show the level at that time.
- **Level: low, high, changing**: the label of a rate of `asmread` with one thread and a buffer of 8 MiB. Low is below 69 GB/s, high is above 70.5 GB/s, and changing is every rate from 69 to 70.5 GB/s. The two limits are provisional.
- **Stable process**: a process whose reference intervals all have the label low, or all have the label high.
- **Pair value**: the rate of one kernel minus the rate of the other in two neighbouring intervals, in GB/s.
- **Process value**: one number per process. `d` is the median of the pair values of the kernel comparison. `e` is the median of the pair values of the A/A comparison.
- **Decision group**: the processes of one session, one buffer size, one CPU and one label.
- **Resolved**: the word for a difference that is larger than the A/A spread and has one sign in all processes.
- **Not resolved**: the word for a difference that lies inside the A/A spread, or whose sign changes between the processes.
- **Not observed**: the word for a case with too few processes for a decision.
- **Setting**: one combination of the timing options of a step with 120 threads: the stop method, the interval length and the start method.
- **`D`, `E`**: the two process values of a step with 120 threads. `D` is the difference between two kernels. `E` is the A/A difference of the same process.
- **Control**: in step B10, the largest absolute A/A difference of one setting: one for the total rate and one for the rate of each mesh.
- **H11**: a hypothesis of the plan: in some intervals the threads of one mesh run faster, and this makes the write totals differ.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.

## Main flow

1. Set the two limits of the level and define `level`, which labels one rate (lines 11 to 14).
2. Define the rules for the steps with one thread (lines 16 to 78). `process_value` gives one label and the values `d` and `e` per process. `resolved` decides one decision group. `decide_one_thread` applies it per CPU and joins the CPUs. `decide_b6_state` compares the low and the high processes of one CPU.
3. Define the rules for the steps with 120 threads (lines 80 to 132). `decide_setting` decides one setting, and `decide_change` decides a change between two settings. `controls_from_aa` computes the controls of step B10, and `decide_h11` applies them to hypothesis H11.
4. Started as a program, the file runs `_tests`: seven groups of tests on invented values (lines 134 to 199).

## Behavior a reader must know

- The file reads no result file and writes no file. Started as a program it prints one line when all tests pass. A failed test ends the program with an error.
- The rules are used by the analysis of Parts B and C: the script `analyze_bwx.py` imports this file and calls its functions.
- Every rule compares with an A/A spread or a control. A difference counts only when it is strictly larger. An equal value is not resolved.
- A group with too few processes gives `not observed`: fewer than 3 in `decide_one_thread`, fewer than 2 of one label in `decide_b6_state`, fewer than 4 in `decide_setting` and `decide_change`, fewer than 2 counted processes in `decide_h11`. A caller can give another count.
- Values of different CPUs are never pooled in the rules for one thread. `decide_one_thread` needs at least 2 CPUs that are resolved with the same sign.
- A process gives one value, however many intervals it has. The value is a median of its pair values.
- At 8 MiB a process gives a value only when all its reference intervals are low or all are high. At the other sizes no level is tested.
- `decide_h11` does not return which mesh rose. It returns only the word.
- All rates in the tests are invented. No test result is a measurement.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/decide.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (199 lines, 11899 bytes, sha256 `98c551bc554ad28b70b2566863657af2ba72eda1f21d66777a532f093905989f`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, the two level limits and the function `level` (lines 1 to 15)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""decide.py - the decision rules of handoff.md section B.10, as code, with synthetic tests.` | Starts the header text of the file (a docstring, a text that Python keeps but does not run). It names the purpose: the decision rules of section B.10 of the handoff note `handoff.md`, written as code, with tests on invented values. |
| 4 | `Words: a "process value" is one number per process (never one per interval). d is the process value` | Header text: two terms. A process value is one number per process, never one number per interval. `d` is the process value of a difference between two kernels. The sentence ends in line 5. |
| 5 | `of a kernel difference, e is the process value of the A/A difference of the same process.` | Continues the header text: `e` is the process value of the A/A difference of the same process. An A/A difference is the difference between two copies of one loop that stand in the binary under two names. It shows how much two equal loops differ. |
| 6 | `Every one-thread decision is made per CPU. Processes of different CPUs are never pooled.` | Header text: every decision for a step with one thread is made for one CPU at a time. Values of processes on different CPUs are never put into one group. |
| 7 | `Run "python3 decide.py" to execute the synthetic tests.` | Header text: the command `python3 decide.py` runs the tests on invented values (lines 134 to 196). |
| 8 | `"""` | Ends the header text. |
| 9 | `from statistics import median` | Takes the function `median` from the Python standard library. For an even count of values it returns the mean of the two middle values. |
| 11 | `LOW_MAX, HIGH_MIN = 69.0, 70.5          # GB/s, provisional limits of the two levels at 8 MiB (plan, rule 5)` | `LOW_MAX` is 69.0 and `HIGH_MIN` is 70.5, both in GB/s. They are the limits of the two levels that a load-only read loop shows with one thread and a buffer of 8 MiB. By the comment the limits are provisional and come from rule 5 of the plan. |
| 13 | `def level(rate):` | Starts the function `level`. It gives the level label of one rate in GB/s. |
| 14 | `    return 'low' if rate < LOW_MAX else 'high' if rate > HIGH_MIN else 'changing'` | Returns `low` for a rate below 69.0 GB/s, `high` for a rate above 70.5 GB/s, and `changing` for every rate from 69.0 to 70.5 GB/s, the two limits included. |

### Function `process_value`: one label and two numbers per process (lines 16 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 16 | `def process_value(ref_rates, kernel_pairs, aa_pairs, labelled=True):` | Starts the function `process_value`. It turns the values of one process into one label and two numbers. `ref_rates`: the rates of all reference intervals of the process, in GB/s. A reference interval is an interval of the kernel `asmread` that is timed directly before or after a compared interval. It shows the level at that time. `kernel_pairs`: the pair values of the kernel comparison. `aa_pairs`: the pair values of the A/A comparison. A pair value is the rate of one kernel minus the rate of the other in two neighbouring intervals, in GB/s. |
| 17 | `    """One process -> (label, d, e), or None if the process gives no value.` | Text of the function: the result is the triple of the label, `d` and `e`, or `None` when the process gives no value. |
| 18 | `    ref_rates: rates of all reference intervals of the process. kernel_pairs, aa_pairs: pair values.` | Text of the function: the meaning of the three inputs, as line 16 gives it. |
| 19 | `    labelled=True (8 MiB): only a process whose references are all low or all high gives a value (plan, rule 4).` | Text of the function: with `labelled=True`, the case of 8 MiB, only a process whose reference intervals are all low or all high gives a value. This is rule 4 of the plan. |
| 20 | `    labelled=False (4, 16, 32 MiB): no level is defined; every process gives a value with the label 'none'."""` | Text of the function: with `labelled=False`, the cases of 4, 16 and 32 MiB, no level is defined. Every process then gives a value, with the label `none`. The text ends here. |
| 21 | `    if not kernel_pairs or not aa_pairs:` | Tests whether one of the two lists of pair values is empty. |
| 22 | `        return None` | A process without kernel pairs or without A/A pairs gives no value: the function returns `None`. |
| 23 | `    if labelled:` | The case with level labels (8 MiB). |
| 24 | `        labels = {level(r) for r in ref_rates}` | `labels`: the set of the level labels of all reference rates of the process (line 13). A set holds each label once. |
| 25 | `        if len(labels) != 1 or labels == {'changing'}:` | Tests whether the reference intervals have more than one label, or no label, or only the label `changing`. |
| 26 | `            return None` | Such a process is not stable at one level. It gives no value. |
| 27 | `        label = labels.pop()` | `label`: the one label that the set holds, `low` or `high`. |
| 28 | `    else:` | The case without level labels (4, 16 and 32 MiB). |
| 29 | `        label = 'none'` | The label is the word `none`. The reference rates are not used in this case. |
| 30 | `    return label, median(kernel_pairs), median(aa_pairs)` | Returns the label, `d` and `e`. `d` is the median of the kernel pair values of the process. `e` is the median of its A/A pair values. So a process gives one value of each kind, however many intervals it has. |

### Function `resolved`: the rule for one decision group (lines 32 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `def resolved(d, e, min_n):` | Starts the function `resolved`, the central rule. `d` and `e` are the lists of the process values of one decision group: the same session, buffer size, CPU and label. `min_n` is the smallest number of processes that a decision needs. |
| 33 | `    """d, e: process values of one group (same session, size, CPU, label).` | Text of the function: the meaning of `d` and `e`, as line 32 gives it. |
| 34 | `    -> ('not observed', None) with fewer than min_n processes; else ('resolved', sign) or ('not resolved', None).` | Text of the function: the result is a pair of a word and a sign. With fewer than `min_n` processes the word is `not observed`. If not, it is `resolved` with a sign, or `not resolved`. |
| 35 | `    Resolved: \|median d\| larger than the A/A spread (largest \|e\|), and all d have one sign."""` | Text of the function: the rule. A group is resolved when the absolute value of the median of `d` is larger than the A/A spread, and all `d` have one sign. The A/A spread is the largest absolute value of `e`. |
| 36 | `    if len(d) < min_n or len(e) < min_n:` | Tests whether the group has fewer than `min_n` values of `d` or of `e`. |
| 37 | `        return 'not observed', None` | Too few processes: the result is `not observed`, without a sign. |
| 38 | `    spread = max(abs(x) for x in e)` | `spread`: the A/A spread of the group, in GB/s: the largest absolute value among the `e` values. It is never negative. |
| 39 | `    m = median(d)` | `m`: the median of the `d` values of the group, in GB/s. It keeps its sign. |
| 40 | `    one_sign = all(x > 0 for x in d) or all(x < 0 for x in d)` | `one_sign`: true when every `d` is above 0, or every `d` is below 0. One `d` of exactly 0 makes it false. |
| 41 | `    if abs(m) > spread and one_sign:` | The test of the rule: the absolute value of the median is larger than the A/A spread, and all `d` have one sign. A median that is equal to the spread does not pass. |
| 42 | `        return 'resolved', (1 if m > 0 else -1)` | Returns the word `resolved` and the sign of the difference: 1 when the median is above 0, and -1 when it is below 0. |
| 43 | `    return 'not resolved', None` | Every other case: the difference lies inside the A/A spread, or its sign is not the same in all processes. The result is `not resolved`. |

### Function `decide_one_thread`: one session and size, CPU by CPU (lines 45 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `def decide_one_thread(procs, min_n=3):` | Starts the function `decide_one_thread`: the decision for one session and one buffer size of a step with one thread. `procs` holds one entry per process. A group needs at least 3 processes unless the caller gives another `min_n`. |
| 46 | `    """procs: list of dicts {cpu, label, d, e}, one per process, for one session and size.` | Text of the function: each entry of `procs` is a dictionary with the CPU, the label and the process values `d` and `e` of one process. |
| 47 | `    -> {label: (word, sign, per_cpu)}. A label is 'resolved' only if at least 2 CPUs have enough processes,` | Text of the function: the result maps each label to a triple: the word of the decision, the sign, and the results of the single CPUs. The sentence about `resolved` ends in line 48. |
| 48 | `    every such CPU is resolved, and all have the same sign."""` | Continues the text: a label is `resolved` only when at least 2 CPUs have enough processes, every such CPU is resolved, and all of them have the same sign. |
| 49 | `    out = {}` | `out`: the result, empty at first. |
| 50 | `    for label in sorted({p['label'] for p in procs}):` | Loop over the labels that occur in `procs`, in sorted order. The set in braces holds each label once. |
| 51 | `        per_cpu = {}` | `per_cpu`: the result of each CPU for this label. |
| 52 | `        for cpu in sorted({p['cpu'] for p in procs}):` | Loop over the CPUs that occur in `procs`, in rising order. |
| 53 | `            g = [p for p in procs if p['cpu'] == cpu and p['label'] == label]` | `g`: the decision group: the processes of this CPU that have this label. A process of another CPU never enters the group. |
| 54 | `            per_cpu[cpu] = resolved([p['d'] for p in g], [p['e'] for p in g], min_n)` | Applies the rule `resolved` (line 32) to the `d` values and the `e` values of the group, and keeps the result for the CPU. |
| 55 | `        seen = [v for v in per_cpu.values() if v[0] != 'not observed']` | `seen`: the results of the CPUs that had enough processes. A CPU with the word `not observed` is left out. |
| 56 | `        if len(seen) < 2:` | Tests whether fewer than 2 CPUs had enough processes. |
| 57 | `            out[label] = ('not observed', None, per_cpu)` | The label is then `not observed`. The function does not pool the CPUs to reach the needed count. |
| 58 | `        elif all(v[0] == 'resolved' for v in seen) and len({v[1] for v in seen}) == 1:` | Tests whether every such CPU is resolved and all of them have the same sign: the set of their signs holds exactly one value. |
| 59 | `            out[label] = ('resolved', seen[0][1], per_cpu)` | The label is `resolved`, with that sign. |
| 60 | `        else:` | Every other case: at least one such CPU is not resolved, or the signs of the CPUs differ. |
| 61 | `            out[label] = ('not resolved', None, per_cpu)` | The label is `not resolved`. |
| 62 | `    return out` | Returns the result for all labels. |

### Function `decide_b6_state`: old read at the low and at the high level, per CPU (lines 64 to 79)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `def decide_b6_state(procs, min_n=2):` | Starts the function `decide_b6_state`: the first comparison of step B6. It compares the rate of the old read kernel at 8 MiB between the stable low processes and the stable high processes of one CPU. Each of the two labels needs at least 2 processes unless the caller gives another `min_n`. |
| 65 | `    """B6, first comparison: old read at 8 MiB in stable-low processes against stable-high processes ON THE SAME CPU.` | Text of the function: the comparison is made on one CPU at a time. A stable low process is a process whose reference intervals are all low. A stable high process has only high ones. |
| 66 | `    procs: list of dicts {cpu, label, rate (process median of oldread at 8 MiB), e (oldread2 - oldread)}.` | Text of the function: each entry of `procs` holds the CPU, the label, `rate` and `e`. `rate` is the median over the process of the rates of `oldread` at 8 MiB, in GB/s. `e` is the A/A value of the process: the rate of `oldread2` minus the rate of `oldread`. `oldread` is the name of the old read kernel in the runner, and `oldread2` is a second copy of it. |
| 67 | `    -> {cpu: (word, difference)}. A CPU without min_n processes of each label is 'not observed'."""` | Text of the function: the result maps each CPU to the word and the difference. A CPU with fewer than `min_n` processes of one of the two labels is `not observed`. |
| 68 | `    out = {}` | `out`: the result, empty at first. |
| 69 | `    for cpu in sorted({p['cpu'] for p in procs}):` | Loop over the CPUs that occur in `procs`, in rising order. |
| 70 | `        g = [p for p in procs if p['cpu'] == cpu]` | `g`: the processes of this CPU. |
| 71 | `        lo = [p['rate'] for p in g if p['label'] == 'low']; hi = [p['rate'] for p in g if p['label'] == 'high']` | `lo`: the rates of the low processes of this CPU. `hi`: the rates of its high processes. The semicolon puts two statements on one line. |
| 72 | `        if len(lo) < min_n or len(hi) < min_n:` | Tests whether one of the two labels has fewer than `min_n` processes on this CPU. |
| 73 | `            out[cpu] = ('not observed', None); continue` | The CPU is then `not observed`, without a difference. `continue` goes to the next CPU. |
| 74 | `        spread = max(abs(p['e']) for p in g)` | `spread`: the A/A spread of the CPU, in GB/s: the largest absolute `e` over all its processes, low and high together. |
| 75 | `        diff = median(lo) - median(hi)` | `diff`: the median rate of the low processes minus the median rate of the high processes, in GB/s. |
| 76 | `        separate = max(lo) < min(hi) or min(lo) > max(hi)` | `separate`: true when every low value lies on one side of every high value. Either the highest low rate is below the lowest high rate, or the lowest low rate is above the highest high rate. |
| 77 | `        out[cpu] = ('resolved' if abs(diff) > spread and separate else 'not resolved', diff)` | The CPU is `resolved` when the absolute difference is larger than the A/A spread and the two sets of values are separate. If not, it is `not resolved`. The difference is stored in both cases. |
| 78 | `    return out` | Returns the result for all CPUs. |

### Functions `decide_setting` and `decide_change`: steps with 120 threads (lines 80 to 93)

| Line | Source | Explanation |
|---:|---|---|
| 80 | `def decide_setting(procs, min_n=4):` | Starts the function `decide_setting`: the decision for one setting of a step with 120 threads (B7 or B10). `procs` holds one entry per process. A decision needs at least 4 processes unless the caller gives another `min_n`. |
| 81 | `    """B7 or B10, one setting: procs = list of dicts {D, E}, ONE per process (the mean over the rounds of the process)."""` | Text of the function: each entry holds the two values `D` and `E` of one process. By the handoff note, `D` of step B7 is the mean over the rounds of the process of the total rate of `oldread` minus that of `read`, and `E` is the same for `asmread2` minus `asmread`. `read` is the new read kernel, and `asmread2` is a second copy of `asmread`. |
| 82 | `    return resolved([p['D'] for p in procs], [p['E'] for p in procs], min_n)` | Applies the rule `resolved` (line 32) to the `D` values and the `E` values. So `D` is resolved when the absolute value of its median is larger than the largest absolute `E`, and all `D` have one sign. |
| 84 | `def decide_change(procs_x, procs_y, min_n=4):` | Starts the function `decide_change`: the change of `D` between two settings that differ in one factor, for example in the stop method. `procs_x` and `procs_y` hold the processes of the two settings. |
| 85 | `    """Change of D between two settings that differ in one factor. -> (word, change)."""` | Text of the function: the result is the word of the decision and the change. |
| 86 | `    if len(procs_x) < min_n or len(procs_y) < min_n:` | Tests whether one of the two settings has fewer than `min_n` processes. |
| 87 | `        return 'not observed', None` | The result is then `not observed`, without a change. |
| 88 | `    dx = [p['D'] for p in procs_x]; dy = [p['D'] for p in procs_y]` | `dx` and `dy`: the `D` values of the first and of the second setting. |
| 89 | `    change = median(dx) - median(dy)` | `change`: the median `D` of the first setting minus the median `D` of the second, in GB/s. |
| 90 | `    spread = max(abs(p['E']) for p in procs_x) + max(abs(p['E']) for p in procs_y)` | `spread`: the sum of the two A/A spreads. Each is the largest absolute `E` of its setting. |
| 91 | `    separate = max(dx) < min(dy) or min(dx) > max(dy)` | `separate`: true when every `D` of one setting lies on one side of every `D` of the other. |
| 92 | `    return ('resolved' if abs(change) > spread and separate else 'not resolved'), change` | Returns the word and the change. The word is `resolved` when the absolute change is larger than the sum of the two A/A spreads and the two sets of `D` are separate. If not, it is `not resolved`. |

### Function `controls_from_aa`: the controls of step B10 (lines 94 to 102)

| Line | Source | Explanation |
|---:|---|---|
| 94 | `def controls_from_aa(aa_intervals):` | Starts the function `controls_from_aa`. It computes the controls of one setting of step B10 from its A/A pair, which is `asmwrite` and `asmwrite2` by the handoff note. A control is the largest difference that two copies of one loop showed. A change of a kernel counts only when it is larger than its control. |
| 95 | `    """Controls of one setting from its A/A intervals.` | Text of the function: the controls of one setting are computed from its A/A intervals. |
| 96 | `    aa_intervals: list of (a, a2) for neighbouring intervals of the A/A pair in one process;` | Text of the function: `aa_intervals` is a list of pairs `(a, a2)`. Each pair stands for two neighbouring intervals of the A/A pair in one process. |
| 97 | `    a and a2 are (rate of mesh 0, rate of mesh 1) of the original and of its copy.` | Text of the function: `a` holds the rate of mesh 0 and the rate of mesh 1 of the original loop. `a2` holds the same two rates of its copy. |
| 98 | `    -> (control of the total rate, (control of mesh 0, control of mesh 1)): largest absolute A/A differences."""` | Text of the function: the result is the control of the total rate and the pair of the controls of the two meshes. Each is a largest absolute A/A difference. |
| 99 | `    tot = max(abs(sum(a2) - sum(a)) for a, a2 in aa_intervals)` | `tot`: the control of the total rate, in GB/s. The total of an interval is the sum of its two mesh rates. `tot` is the largest absolute difference between the total of the copy and the total of the original, over all pairs. |
| 100 | `    mesh = tuple(max(abs(a2[m] - a[m]) for a, a2 in aa_intervals) for m in (0, 1))` | `mesh`: the two controls of the mesh rates. For mesh 0 and for mesh 1 it is the largest absolute difference between the rate of the copy and the rate of the original on that mesh, over all pairs. |
| 101 | `    return tot, mesh` | Returns the control of the total and the two controls of the meshes. |

### Function `decide_h11`: does one mesh alone make the higher write totals (lines 103 to 133)

| Line | Source | Explanation |
|---:|---|---|
| 103 | `def decide_h11(procs, ctrl_total, ctrl_mesh, min_n=2):` | Starts the function `decide_h11`: the rule for hypothesis H11 in step B10. H11 says that in some intervals the threads of one mesh run faster, and that this makes the write totals differ. `ctrl_total` and `ctrl_mesh` are the controls that lines 94 to 101 compute. At least 2 processes must count unless the caller gives another `min_n`. |
| 104 | `    """H11: in an interval with a higher total, one mesh is faster and the other is not.` | Text of the function: what H11 predicts. In an interval with a higher total, one mesh is faster and the other is not. |
| 105 | `    procs: one dict per process: {hi: (mesh0, mesh1), lo: (mesh0, mesh1)} = per-mesh rates of the interval with` | Text of the function: `procs` holds one dictionary per process, with the entries `hi` and `lo`. Each is the pair of the rate of mesh 0 and the rate of mesh 1 in one interval. The sentence ends in line 106. |
| 106 | `    the highest and with the lowest total of one kernel in that process.` | Continues the text: `hi` is the interval with the highest total and `lo` the interval with the lowest total of one kernel in that process. |
| 107 | `    A process counts only if its total differs by more than the control of the total rate.` | Text of the function: a process counts only when its two totals differ by more than the control of the total rate. |
| 108 | `    Each mesh is judged with the control of ITS OWN rate, never with a control of a total or of a range.` | Text of the function: each mesh is judged with the control of its own rate. A control of a total or of a range is never used for a mesh. |
| 109 | `    Supported: in every counted process exactly one mesh changed by more than its control, that change is` | Text of the function: when H11 is supported. In every counted process exactly one mesh changed by more than its control. The sentence ends in line 110. |
| 110 | `    positive (the mesh got faster), and it is the same mesh in all processes.` | Continues the text: that change is positive, so the mesh got faster, and it is the same mesh in all processes. |
| 111 | `    -> 'supported', 'contradicted', 'not resolved' or 'not observed'."""` | Text of the function: the result is one of four words: `supported`, `contradicted`, `not resolved` or `not observed`. The text ends here. |
| 112 | `    kinds = []` | `kinds`: one entry per counted process. It says what kind of change the process showed. |
| 113 | `    for p in procs:` | Loop over the processes. |
| 114 | `        if sum(p['hi']) - sum(p['lo']) <= ctrl_total:` | Computes the total of the high interval minus the total of the low interval. Each total is the sum of the two mesh rates. Tests whether this difference is not larger than the control of the total rate. |
| 115 | `            continue` | Such a process does not count: its higher total is not above what two equal loops showed. `continue` goes to the next process. |
| 116 | `        delta = [p['hi'][m] - p['lo'][m] for m in (0, 1)]` | `delta`: for each mesh, its rate in the high interval minus its rate in the low interval, in GB/s. |
| 117 | `        moved = [abs(delta[m]) > ctrl_mesh[m] for m in (0, 1)]` | `moved`: for each mesh, whether the absolute change is larger than the control of that mesh. |
| 118 | `        if moved[0] != moved[1]:` | The case that exactly one of the two meshes has changed. |
| 119 | `            m = 0 if moved[0] else 1` | `m`: the number of that mesh, 0 or 1. |
| 120 | `            # H11 says that one mesh runs FASTER: a mesh that only got slower is not support.` | Comment: H11 says that one mesh runs faster. A mesh that only got slower does not support it. |
| 121 | `            kinds.append(('one', m) if delta[m] > 0 else ('other', None))` | When the change of that mesh is above 0, the process gets the kind `one` with the mesh number. When the mesh got slower, the process gets the kind `other`. |
| 122 | `        elif moved[0] and moved[1] and (delta[0] > 0) == (delta[1] > 0):` | The case that both meshes have changed, and in the same direction: both changes are above 0, or neither is. |
| 123 | `            kinds.append(('both', None))` | The process gets the kind `both`. |
| 124 | `        else:` | Every other case: no mesh has changed by more than its control, or the two meshes have changed in opposite directions. |
| 125 | `            kinds.append(('other', None))` | The process gets the kind `other`. |
| 126 | `    if len(kinds) < min_n:` | Tests whether fewer than `min_n` processes counted. |
| 127 | `        return 'not observed'` | The result is then `not observed`. |
| 128 | `    if all(k[0] == 'one' for k in kinds) and len({k[1] for k in kinds}) == 1:` | Tests whether every counted process has the kind `one`, and the mesh is the same in all of them. |
| 129 | `        return 'supported'` | The result is `supported`. |
| 130 | `    if all(k[0] == 'both' for k in kinds):` | Tests whether every counted process has the kind `both`. |
| 131 | `        return 'contradicted'` | The result is `contradicted`: both meshes rose or fell together in every counted process. |
| 132 | `    return 'not resolved'` | Every other mix of kinds gives `not resolved`. |

### Tests 1 to 3: negative differences, CPUs kept apart, one value per process (lines 134 to 162)

| Line | Source | Explanation |
|---:|---|---|
| 134 | `def _tests():` | Starts the function `_tests`. It holds seven groups of tests on invented values. Each `assert` stops the program with an error when its condition is false. |
| 135 | `    # 1. A negative difference can be resolved (rule 3 of the plan uses the absolute value).` | Comment: test group 1. A negative difference can be resolved. Rule 3 of the plan compares the absolute value of the median with the A/A spread. |
| 136 | `    assert resolved([-2.0, -2.2, -1.7], [0.3, -0.2, 0.1], 3) == ('resolved', -1)` | Three processes with `d` of -2.0, -2.2 and -1.7 GB/s, and `e` values with an A/A spread of 0.3 GB/s. The median is -2.0 GB/s. Its absolute value is above 0.3, and all signs are negative. The result must be `resolved` with the sign -1. This proves that the rule also finds a kernel that is slower. |
| 137 | `    assert resolved([-2.0, -2.2, +1.7], [0.3, -0.2, 0.1], 3)[0] == 'not resolved'      # signs differ` | The same values with one positive `d`. The median is still -2.0 GB/s, but the signs differ. The result must be `not resolved`. This proves that one process with the other sign blocks the decision. |
| 138 | `    assert resolved([-0.2, -0.25, -0.1], [0.3, -0.2, 0.1], 3)[0] == 'not resolved'     # inside the A/A spread` | All `d` are negative, but the absolute median, 0.2 GB/s, is below the A/A spread of 0.3 GB/s. The result must be `not resolved`. This proves that a difference inside the spread of two equal loops is not reported as a difference. |
| 139 | `    assert resolved([-2.0, -2.2], [0.3, -0.2], 3)[0] == 'not observed'                 # too few processes` | Only 2 processes where 3 are needed. The result must be `not observed`. This proves that a clear difference in too few processes gives no decision. |
| 141 | `    # 2. A difference between CPUs must not become a difference between levels.` | Comment: test group 2. A difference between two CPUs must not be reported as a difference between the two levels. |
| 142 | `    #    CPU 2 is always low with old read at 67.0; CPU 41 is always high with old read at 68.0.` | Comment: the invented case. CPU 2 is always at the low level, with the old read kernel at 67.0 GB/s. CPU 41 is always at the high level, with the old read kernel at 68.0 GB/s. |
| 143 | `    procs = [dict(cpu=2, label='low', rate=67.0 + i * 0.01, e=0.02) for i in range(4)] + \` | Builds 4 low processes on CPU 2 with the rates 67.00, 67.01, 67.02 and 67.03 GB/s and an A/A value of 0.02 GB/s each. The backslash continues the statement in line 144. |
| 144 | `            [dict(cpu=41, label='high', rate=68.0 + i * 0.01, e=0.02) for i in range(4)]` | Adds 4 high processes on CPU 41 with the rates 68.00 to 68.03 GB/s and the same A/A value. |
| 145 | `    r = decide_b6_state(procs)` | `r`: the result of `decide_b6_state` for these 8 processes. |
| 146 | `    assert r[2][0] == 'not observed' and r[41][0] == 'not observed', r` | Both CPUs must be `not observed`: each CPU has processes of one level only. The `r` after the comma is shown when the test fails. |
| 147 | `    #    Pooled over the CPUs the same data would look like a resolved level effect of -1.0 GB/s:` | Comment: pooled over the two CPUs, the same data would look like a resolved effect of the level of -1.0 GB/s. |
| 148 | `    pooled = median(p['rate'] for p in procs if p['label'] == 'low') - median(p['rate'] for p in procs if p['label'] == 'high')` | `pooled`: what a pooled analysis would compute: the median rate of all low processes minus the median rate of all high processes, without regard to the CPU. |
| 149 | `    assert abs(pooled + 1.0) < 0.02` | Checks that the pooled difference is -1.0 GB/s, within 0.02 GB/s. So the invented data would show a level effect of 1 GB/s when the CPUs are pooled, and the rule of line 64 reports none. Together with line 146 this proves that the rule keeps a difference between CPUs apart from a difference between levels. |
| 150 | `    #    With both levels on one CPU and equal rates, the result is 'not resolved'.` | Comment: with both levels on one CPU and equal rates, the result is `not resolved`. |
| 151 | `    procs = [dict(cpu=2, label=l, rate=67.0 + i * 0.01, e=0.05) for l in ('low', 'high') for i in range(3)]` | Builds 3 low and 3 high processes on CPU 2. Both sets have the same rates, 67.00 to 67.02 GB/s, and an A/A value of 0.05 GB/s. |
| 152 | `    assert decide_b6_state(procs)[2][0] == 'not resolved'` | The result for CPU 2 must be `not resolved`: the difference is 0 GB/s, and the two sets are not separate. This proves that a CPU with enough processes of both levels gets a decision, and that equal rates are not reported as a difference. |
| 154 | `    # 3. One process with many intervals counts once.` | Comment: test group 3. One process with many intervals counts once. |
| 155 | `    small = [process_value([67.5] * 5, [0.1] * 4, [0.02] * 4) for _ in range(3)]` | `small`: the values of 3 short processes. Each has 5 reference intervals at 67.5 GB/s, which is low, 4 kernel pair values of +0.1 GB/s and 4 A/A pair values of 0.02 GB/s. So each gives the label `low`, `d` of 0.1 and `e` of 0.02. |
| 156 | `    big = process_value([67.5] * 101, [-5.0] * 100, [0.02] * 100)` | `big`: the value of one long process with 101 reference intervals and 100 kernel pair values of -5.0 GB/s. It gives the label `low` and `d` of -5.0. |
| 157 | `    procs = [dict(cpu=2, label=v[0], d=v[1], e=v[2]) for v in small + [big]] + \` | Puts the 4 processes on CPU 2, one dictionary per process. The backslash continues the statement in line 158. |
| 158 | `            [dict(cpu=41, label=v[0], d=v[1], e=v[2]) for v in small + [big]]` | Puts the same 4 processes on CPU 41. So 2 CPUs have enough processes. |
| 159 | `    assert decide_one_thread(procs)['low'][0] == 'not resolved'       # 3 processes say +0.1, one says -5` | The label `low` must be `not resolved`. On each CPU three processes give +0.1 and one gives -5.0. The median of the four is +0.1, and the signs differ. This proves that the long process counts as one process, not as 100 values. |
| 160 | `    all_pairs = [0.1] * 12 + [-5.0] * 100` | `all_pairs`: all kernel pair values of one CPU in one list: 12 values of +0.1 and 100 values of -5.0. A pooled analysis over the intervals would use this list. |
| 161 | `    assert median(all_pairs) == -5.0                                  # pooling the intervals would say -5` | Checks that the median of the pooled list is -5.0 GB/s. So a pooled analysis would report the value of the one long process. Together with line 159 this shows why the rule takes one value per process. |

### Tests 4 to 6: unstable processes, two CPUs, settings and changes (lines 163 to 178)

| Line | Source | Explanation |
|---:|---|---|
| 163 | `    # 4. A process whose references change level gives no value at 8 MiB, and gives one at an unlabelled size.` | Comment: test group 4. A process whose reference intervals change level gives no value at 8 MiB. At a size without labels it gives one. |
| 164 | `    assert process_value([67.5, 71.0, 67.6], [0.1] * 4, [0.0] * 4) is None` | Reference rates of 67.5, 71.0 and 67.6 GB/s: low, high, low. The process is not stable, so the result must be `None`. |
| 165 | `    assert process_value([67.5, 69.8, 67.6], [0.1] * 4, [0.0] * 4) is None` | Reference rates of 67.5, 69.8 and 67.6 GB/s: low, changing, low. One reference interval between the two limits is enough: the result must be `None`. |
| 166 | `    assert process_value([55.0, 58.0, 61.0], [0.1] * 4, [0.0] * 4, labelled=False)[0] == 'none'` | With `labelled=False` the reference rates are not tested. The process must give a value with the label `none`. The three tests prove that only the 8 MiB case drops a process for its level. This matters: a pair value from a process that changed level would mix two levels. |
| 168 | `    # 5. One-thread decision needs the same sign on at least 2 CPUs with enough processes.` | Comment: test group 5. A decision for a step with one thread needs the same sign on at least 2 CPUs that have enough processes. |
| 169 | `    mk = lambda cpu, d: [dict(cpu=cpu, label='low', d=d + i * 0.01, e=0.1) for i in range(4)]` | `mk`: a helper that builds 4 low processes on one CPU. Their `d` values are the given value plus 0, 0.01, 0.02 and 0.03 GB/s, and each `e` is 0.1 GB/s. |
| 170 | `    assert decide_one_thread(mk(0, -2.0) + mk(2, -2.1))['low'][:2] == ('resolved', -1)` | CPU 0 with `d` near -2.0 GB/s and CPU 2 with `d` near -2.1 GB/s. Both CPUs are resolved with a negative sign. The first two parts of the result for `low` must be `resolved` and -1. This proves the positive case: two CPUs that agree give a decision. |
| 171 | `    assert decide_one_thread(mk(0, -2.0) + mk(2, +2.1))['low'][0] == 'not resolved'` | CPU 0 negative and CPU 2 positive. Each CPU alone is resolved, but the signs differ. The label must be `not resolved`. This proves that two CPUs that disagree give no decision. |
| 172 | `    assert decide_one_thread(mk(0, -2.0))['low'][0] == 'not observed'` | Only one CPU has processes. The label must be `not observed`. This proves that one CPU alone never decides. |
| 174 | `    # 6. Settings: one value per process; a change needs separate ranges.` | Comment: test group 6. A setting gets one value per process, and a change between two settings needs separate ranges. The tests of the group do not prove the second point. The ranges of `D` are separate in both calls of `decide_change` (lines 176 to 177). No test has ranges that overlap. |
| 175 | `    x = [dict(D=160 + i, E=5) for i in range(4)]; y = [dict(D=20 + i, E=6) for i in range(4)]` | `x`: a setting with 4 processes, `D` of 160, 161, 162 and 163 GB/s and `E` of 5 GB/s. `y`: a setting with `D` of 20 to 23 GB/s and `E` of 6 GB/s. |
| 176 | `    assert decide_setting(x) == ('resolved', 1) and decide_change(x, y)[0] == 'resolved'` | `D` of the setting `x` must be resolved with a positive sign: its median, 161.5 GB/s, is above the A/A spread of 5 GB/s. The change from `x` to `y` must be resolved too. It is 140 GB/s, the sum of the two spreads is 11 GB/s, and the two ranges of `D` do not overlap. |
| 177 | `    assert decide_change(x, [dict(D=155 + i, E=6) for i in range(4)])[0] == 'not resolved'` | A second setting with `D` of 155 to 158 GB/s. Its range of `D` lies wholly below the range of `x`. So the two ranges are separate. The change is 5 GB/s, below the sum of the two spreads, 11 GB/s. The result must be `not resolved`. This proves that separate ranges alone do not give a resolved change: the change must also be larger than the A/A spread. The test does not prove that the two spreads are added. With the spread of `x` alone, 5 GB/s, the result would be the same: a change of 5 GB/s is not larger than 5 GB/s. |
| 178 | `    assert decide_setting(x[:3])[0] == 'not observed'` | Only 3 of the 4 processes of `x`: the result must be `not observed`. A setting needs 4 processes. This proves that a setting with too few processes gives no decision. |

### Test 7 (H11 with one control per mesh) and the start of the tests (lines 179 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 179 | `    # 7. H11 uses a control per mesh. A/A intervals with equal totals and opposite mesh rates:` | Comment: test group 7. H11 uses one control per mesh. The invented A/A intervals have equal totals and opposite mesh rates. |
| 180 | `    aa = [((50.0, 50.0), (55.0, 45.0)), ((55.0, 45.0), (50.0, 50.0))]` | `aa`: two invented A/A pairs. In the first the original has 50 and 50 GB/s on the two meshes, and the copy has 55 and 45 GB/s. The second pair is the reverse. The total is 100 GB/s in every interval. |
| 181 | `    ctrl_total, ctrl_mesh = controls_from_aa(aa)` | Computes the controls from these pairs (line 94). |
| 182 | `    assert ctrl_total == 0.0 and ctrl_mesh == (5.0, 5.0)` | The control of the total must be 0 GB/s, and the control of each mesh must be 5 GB/s. This proves that the mesh controls come from the mesh rates and not from the totals. |
| 183 | `    #    A change of (0.1, 0) GB/s is far inside the per-mesh control: it must not support H11.` | Comment: a change of 0.1 GB/s on mesh 0 and of 0 GB/s on mesh 1 lies far inside the control of each mesh. It must not support H11. |
| 184 | `    tiny = [dict(hi=(50.1, 50.0), lo=(50.0, 50.0)) for _ in range(3)]` | `tiny`: 3 processes whose high interval has 0.1 GB/s more on mesh 0 and the same rate on mesh 1. |
| 185 | `    assert decide_h11(tiny, ctrl_total, ctrl_mesh) == 'not resolved'` | The total rises by 0.1 GB/s. That is above the control of 0 GB/s, so the processes count. No mesh changes by more than its control of 5 GB/s. The result must be `not resolved`. If the code judged a mesh with the control of the total, the result would be `supported`. The test proves that the rule does not make that error. |
| 186 | `    #    Constant totals with opposing mesh changes: no interval has a higher total, so nothing is observed.` | Comment: constant totals with opposite mesh changes. No interval has a higher total, so nothing is observed. |
| 187 | `    opposing = [dict(hi=(55.0, 45.0), lo=(50.0, 50.0)) for _ in range(3)]` | `opposing`: 3 processes whose high interval has 5 GB/s more on mesh 0 and 5 GB/s less on mesh 1. The total stays at 100 GB/s. |
| 188 | `    assert decide_h11(opposing, ctrl_total, ctrl_mesh) == 'not observed'` | The total does not rise above the control, so no process counts. The result must be `not observed`. This proves that a process counts only when its total rose by more than the control of the total. |
| 189 | `    #    One mesh rises by more than its control, the other does not: supported. Both rise: contradicted.` | Comment: one mesh rises by more than its control and the other does not: supported. Both rise: contradicted. |
| 190 | `    assert decide_h11([dict(hi=(50.0, 80.0), lo=(50.0, 50.0))] * 2, 1.0, (5.0, 5.0)) == 'supported'` | Two processes in which mesh 1 rises by 30 GB/s and mesh 0 does not change. The control of the total is 1 GB/s, and the control of each mesh is 5 GB/s. The result must be `supported`. This proves the main case of the rule. |
| 191 | `    assert decide_h11([dict(hi=(70.0, 80.0), lo=(50.0, 50.0))] * 2, 1.0, (5.0, 5.0)) == 'contradicted'` | Two processes in which both meshes rise, by 20 and by 30 GB/s. The result must be `contradicted`. This proves the opposite case: a rise on both meshes speaks against H11. |
| 192 | `    assert decide_h11([dict(hi=(50.0, 80.0), lo=(50.0, 50.0)), dict(hi=(80.0, 50.0), lo=(50.0, 50.0))], 1.0, (5.0, 5.0)) == 'not resolved'` | Mesh 1 rises in the first process and mesh 0 in the second. One mesh changes in each process, but not the same mesh. The result must be `not resolved`. This proves that the rising mesh must be the same in all counted processes. |
| 193 | `    #    The only mesh above its control got SLOWER (50 -> 48) while the total rose: not support for H11.` | Comment: the only mesh above its control got slower, from 50 to 48 GB/s, while the total rose. That is no support for H11. |
| 194 | `    slower = [dict(hi=(48.0, 53.0), lo=(50.0, 50.0)) for _ in range(2)]` | `slower`: 2 processes whose high interval has 2 GB/s less on mesh 0 and 3 GB/s more on mesh 1. The total rises by 1 GB/s. |
| 195 | `    assert decide_h11(slower, 0.0, (1.0, 10.0)) == 'not resolved'` | The controls are 0 GB/s for the total, 1 GB/s for mesh 0 and 10 GB/s for mesh 1. Only mesh 0 has changed by more than its control, and it got slower. The result must be `not resolved`. This proves that a mesh that only got slower does not count as support for H11. |
| 196 | `    print('decide.py: all synthetic tests passed')` | All tests passed: prints the line `decide.py: all synthetic tests passed`. |
| 198 | `if __name__ == '__main__':` | This test is true when the file is started as a program. It is false when another file imports it. |
| 199 | `    _tests()` | Runs the tests. So a start of the file as a program does nothing other than test its own rules. |
