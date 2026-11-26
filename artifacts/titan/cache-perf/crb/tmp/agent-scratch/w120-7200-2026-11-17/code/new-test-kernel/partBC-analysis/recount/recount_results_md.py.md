# `recount_results_md.py` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/recount/recount_results_md.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 202 lines, 10616 bytes).
- sha256 of the source when this page was built: `fc849a5deb5dbfa9a4e5272629696d95d033eef3e7e6318291460d7646e6d796`.

## Short version: purpose

`recount_results_md.py` counts again a set of numbers of the result handoff `results.md` of Parts B and C of the test plan of 2026-11-13. It reads the raw csv files of the two sessions and of the short run and prints the numbers as text lines. It decides nothing, and it applies none of the rules that leave a process or an interval out.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`copy`, `asmcopy`, `asmcopy2`**: the new C copy kernel, the asm copy kernel, and a second copy of the asm copy kernel under another name.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC. This script reads the copies on the agent server.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13, with its questions, hypotheses, rules and steps [Ref2].
- **Handoff**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the rows of the csv files, and its section B.10 the decision rules [Ref3].
- **`results.md`**: the result handoff of Parts A, B and C of the plan. It cites the output of this script for the numbers that the script counts [Ref1].
- **Session of Parts B and C**: one run of all steps of Parts B and C of the plan. Two sessions were run, named `s1` and `s2` [Ref1].
- **Step**: one measurement of the plan with its own result folder and csv file.
- **Steps with one thread**: B1 (`copy` against `asmcopy` at four buffer sizes), B2 (three asm variants of the copy loop against `asmcopy`), B3 (the sequence of B1 in three builds with other loop addresses), B4 (`asmread` alone at 8 MiB for 200 intervals), B6 (old read at 8 MiB and at 1 MiB), C1 (B4 with counters) and C2 (B1 at 8 MiB with counters).
- **Steps with 120 threads**: B7 (the four read kernels in 8 settings) and B10 (the four write kernels in 8 settings, in the two folders `B10a` and `B10b`).
- **Short run**: one run of every sequence with intervals of 0.1 s, made before the first session to test the scripts.
- **Header line**: the line that the run script writes into the csv file before each process. It starts with `-- step` and holds the tag, the binary and the arguments of the runner.
- **Tag**: the name of a process in the run script.
- **T row**: a row of the csv file for one thread and one interval. Its fields, counted from 0, are `T`, round, position, kernel, thread number, CPU, bytes (6), `elapsed_s` (7), `t_sched_s`, `t_start_s`, `t_end_s` (10), `passes` and the flag (12).
- **C row**: a row for one thread and one interval of a run with counters. Its fields are `C`, round, position, kernel, thread number, CPU, the enabled time (6), the running time (7) and the CPU time of the thread (8), all in ns, and then the counter values from field 9 on: cycles, instructions, L1 refills, L2 refills and last-level read misses.
- **Level limits**: for one thread with an 8 MiB buffer, the plan calls an interval low below 69 GB/s and high above 70.5 GB/s. It calls the two limits provisional.
- **Pair value, d, e**: a pair is two intervals of two kernels that follow each other. Its value is the rate of the first-named kernel minus the rate of the other. For one process, d is the median pair value of the kernel pair and e the median pair value of the A/A pair.
- **A/A pair, A/A spread**: an A/A pair is one loop that exists twice in the program under two names. The A/A spread of a CPU is the largest absolute e of its processes.
- **Total, `M_hist`**: the bytes of all threads of one interval divided by the longest elapsed time of a thread, in GB/s.
- **D**: the total of old read minus the total of new read. For one process it is the mean over its rounds.
- **Setting**: one combination of stop method (`pass` for whole passes, `common` for a common stop time), shortest interval length in ms and start (`common` or `offset`).
- **End skew**: the latest end time of a thread in an interval minus the earliest one.
- **Choice A2, choice A5**: two choices of the analysis script `analyze_bwx.py` from its notes. A2: a rate comes from the T rows, not from the rounded total that the runner prints. A5: with whole passes an end skew above 5 ms does not make an interval irregular [Ref4].
- **Line**: 64 B, the unit of a cache.

## Main flow

1. The paths on the agent server and the two level limits are set (lines 6 to 8).
2. For each of the two sessions the script reads the list of its result folders and prints a heading (lines 68 to 70).
3. B4: it counts the intervals of each process by level. C1: it prints the number of all intervals of the step, the highest rate and the number of high intervals (lines 71 to 77).
4. C2: it groups the asm read intervals with counters by level and prints medians per 64 B line (lines 78 to 93).
5. B1 at 8 MiB, B2 and B3: with the helpers `d_and_e` and `group` it prints d and the A/A spread per CPU, without level labels (lines 94 to 101).
6. B6: it prints old read at 8 MiB minus old read at 1 MiB for two positions of the sequence, and counts A/A pairs whose first interval is slower (lines 102 to 117).
7. B7: it prints the median D of each setting as a share of the median old read total (lines 118 to 141).
8. B10 and B7: it prints the largest end skew with whole passes, and counts the intervals with an end skew above 5 ms (lines 142 to 167).
9. Over all csv files of both sessions it counts C rows with a very large count and T rows with the flag `late`, and finds the longest page reading (lines 170 to 192).
10. From the short run it prints the instructions per 256 B of the process with a 32 KiB buffer (lines 193 to 202).

## Behavior a reader must know

- Where the numbers come from: a rate is field 6 of a T row divided by field 7, in GB/s (line 36). For 120 threads the total of an interval is the sum of field 6 over its T rows divided by the largest field 7 (lines 126 to 128). The end skew uses field 10 (line 150). Counter values come from the fields 6 to 13 of the C rows (line 87, line 182).
- No filter: the script uses every T row that it finds. It does not test whether a process is complete or an interval is irregular, as the analysis script does. It also does not look at the level of the reference intervals, so the lines for B1, B2 and B3 are a description without labels (line 53).
- The paths are fixed to the working folders on the agent server (lines 6 to 7). The code repo keeps the same result folders and the two folder lists in another place [Ref6].
- The script prints to the standard output only. The usage line sends that output to `recount_results_md.txt` (line 3).
- The script stops with a Python error when a file is missing, when a C row of C2 holds `NA` in a field that it reads, when a counter group of C2 did not run for its whole enabled time (line 88), or when one of the three levels of C2 has no interval (line 93).
- Fixed values in the code: the level limits 69.0 and 70.5 GB/s (line 8), the end skew of 0.005 s (line 166), the count of 1e13 (line 182), and the name of the folder of the short run (line 194).
- For a process with 120 threads the entry `cpu` holds only the first number of its CPU list (line 22). The script uses `cpu` only for the steps with one thread.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/recount/recount_results_md.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (202 lines, 10616 bytes, sha256 `fc849a5deb5dbfa9a4e5272629696d95d033eef3e7e6318291460d7646e6d796`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description, imports and constants (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""Recount of the numbers that results.md gives and that no page or analysis file holds in that form.` | Starts the description: the script counts again the numbers that the result handoff `results.md` gives and that no page or analysis file holds in that form. |
| 3 | `Reads only the raw csv files of the two sessions. Usage: python3 recount_results_md.py > recount_results_md.txt` | Continues the description: it reads only the raw csv files of the two sessions. The usage line sends the output to the file `recount_results_md.txt`. The code also reads the two lists of result folders (line 12) and the csv file of the short run (line 194). |
| 4 | `Rates come from the T rows (bytes / elapsed time), as in analyze_bwx.py (choice A2)."""` | Continues the description: every rate comes from the T rows, as bytes divided by elapsed time. The analysis script `analyze_bwx.py` does the same, which its notes list as choice A2. The line ends the description. |
| 5 | `import statistics as st, collections, re` | Imports three modules of the Python standard library: `statistics` under the short name `st` (median and mean), `collections` (dictionaries with a start value) and `re` (regular expressions). |
| 6 | `R = '/home/jhan/workspace/titan/cache-perf/crb/results/'` | `R`: the folder on the agent server that holds the result folders. |
| 7 | `N = '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/'` | `N`: the folder on the agent server that holds the two lists of result folders, one per session. |
| 8 | `LOW, HIGH = 69.0, 70.5` | `LOW` and `HIGH`: the two level limits for one thread with an 8 MiB buffer, 69.0 and 70.5 GB/s. An interval is called low below 69.0 GB/s and high above 70.5 GB/s. The plan calls these limits provisional. |

### Reading helpers: `folders`, `procs`, `rate` and `one_thread_rates` (lines 11 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `def folders(s):` | Starts the function `folders`. It gives the result folders of session `s`, which is 1 or 2. |
| 12 | `    return {f.split('-')[0]: f for f in open(N + 'session%d-folders.txt' % s).read().split()}` | Reads the file `session1-folders.txt` or `session2-folders.txt`. The file holds the names of the result folders with spaces between them. The function returns a dictionary from the step part of each name, the text before the first `-` such as `B10a`, to the whole folder name. |
| 15 | `def procs(path):` | Starts the function `procs`. It reads one csv file and returns its processes. |
| 16 | `    out, cur = [], None` | `out`: the list of the processes. `cur`: the process whose rows are read now, `None` at first. |
| 17 | `    for l in open(path):` | Loop over the lines of the file. |
| 18 | `        l = l.rstrip('\n')` | Removes the line end. |
| 19 | `        if l.startswith('-- step'):` | Tests whether the line is a header line. The run script writes one before each process, and it starts with `-- step`. |
| 20 | `            p, a = l.split(), l.split(' args ')[1]` | `p`: the words of the header line. `a`: the text after the word `args`, which holds the arguments of the runner. |
| 21 | `            cur = dict(tag=p[p.index('tag') + 1], bin=p[p.index('binary') + 1], args=a, T=[], C=[])` | `cur`: a new process. `tag` is the word after `tag` in the header line, and `bin` the word after `binary`. `T` and `C` are empty lists for its T rows and C rows. |
| 22 | `            for k, rx in (('cpu', r'--cpus (\d+)'), ('seq', r'--seq (\S+)'), ('bytes', r'--bytes (\S+)'), ('stop', r'--stop (\S+)'),` | Loop over six options of the runner, each with a pattern. This line: `cpu` takes the digits after `--cpus`, `seq` the text after `--seq`, `bytes` the text after `--bytes`, and `stop` the text after `--stop`. Each pattern has one group, which holds that value up to the next space. For a CPU list such as `0-63,64-119` the pattern of `cpu` takes only the first number. |
| 23 | `                          ('ms', r'--min-ms (\S+)'), ('start', r'--start (\S+)')):` | Continues the list: `ms` takes the text after `--min-ms`, and `start` the text after `--start`. |
| 24 | `                m = re.search(rx, a)` | Searches the arguments for the pattern. |
| 25 | `                cur[k] = m.group(1) if m else None` | Stores the value of the group under the name, or `None` when the option is not in the arguments. |
| 26 | `            cur['seq'] = cur['seq'].split(',')` | Splits the sequence at the commas into the list of its entries. An entry with a size, such as `oldread@1M`, keeps the size. |
| 27 | `            out.append(cur)` | Adds the process to `out`. |
| 28 | `        elif l.startswith('T,'):` | Tests whether the line is a T row: one thread in one interval. |
| 29 | `            cur['T'].append(l.split(','))` | Adds its fields, split at the commas, to the T rows of the process. The fields are text. Field 0 is the letter `T`. |
| 30 | `        elif l.startswith('C,'):` | Tests whether the line is a C row: the counter values of one thread in one interval. |
| 31 | `            cur['C'].append(l.split(','))` | Adds its fields to the C rows of the process. |
| 32 | `    return out` | Returns the processes. Every other line of the file, such as an I row, a P row or a comment line, is ignored. |
| 35 | `def rate(t):` | Starts the function `rate`. `t` is a T row. |
| 36 | `    return float(t[6]) / float(t[7]) / 1e9` | Returns the rate of the row in GB/s: field 6 (the bytes of the thread) divided by field 7 (its elapsed time in s) and by 1e9. |
| 39 | `def one_thread_rates(p):` | Starts the function `one_thread_rates`. It is made for a process with one thread, which has one T row per interval. |
| 40 | `    return {(int(t[1]), int(t[2])): rate(t) for t in p['T']}` | Returns a dictionary from the pair of round and position (fields 1 and 2 as numbers) to the rate of that interval. |

### `d_and_e` and `group`: pair values of the copy steps without level labels (lines 43 to 67)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `def d_and_e(p, X, Y, A='asmcopy2', B='asmcopy'):` | Starts the function `d_and_e`. For one process it gives the value d of the kernel pair `X` and `Y`, and the value e of the A/A pair `A` and `B`. Without other names the A/A pair is `asmcopy2` and `asmcopy`, two copies of the asm copy loop. |
| 44 | `    """d = median pair value X - Y, e = median pair value A - B (handoff B.10)."""` | Description: d is the median pair value `X` minus `Y`, and e is the median pair value `A` minus `B`, as section B.10 of the handoff defines them. |
| 45 | `    seq, r = p['seq'], one_thread_rates(p)` | `seq`: the sequence of the process. `r`: its rate per round and position. |
| 46 | `    dv, ev = [], []` | `dv` and `ev`: the pair values of the kernel pair and of the A/A pair, empty at first. |
| 47 | `    for rd in sorted({k[0] for k in r}):` | Loop over the rounds of the process. |
| 48 | `        for i in range(len(seq) - 1):` | Loop over each two positions of the sequence that follow each other. |
| 49 | `            if {seq[i], seq[i + 1]} == {X, Y}:` | Tests whether the two positions hold `X` and `Y`, in either order. |
| 50 | `                dv.append(r[(rd, seq.index(X, i, i + 2))] - r[(rd, seq.index(Y, i, i + 2))])` | Adds the pair value: the rate of `X` minus the rate of `Y` in these two intervals. `seq.index` with the two limits finds which of the two positions holds the kernel. |
| 51 | `            if {seq[i], seq[i + 1]} == {A, B}:` | Tests whether the two positions hold `A` and `B`, in either order. |
| 52 | `                ev.append(r[(rd, seq.index(A, i, i + 2))] - r[(rd, seq.index(B, i, i + 2))])` | Adds the A/A pair value: the rate of `A` minus the rate of `B`. |
| 53 | `    return st.median(dv), st.median(ev)` | Returns d and e: the median of the pair values of each kind over all rounds of the process. The function does not look at the level of the reference intervals, so every process gives a value. |
| 56 | `def group(ps, X, Y, label):` | Starts the function `group`. It prints one line for a group of processes `ps`. `label` is the text at the start of the line. |
| 57 | `    by = collections.defaultdict(list)` | `by`: a dictionary from a CPU to a list, empty at first. |
| 58 | `    for p in ps:` | Loop over the processes. |
| 59 | `        by[int(p['cpu'])].append(d_and_e(p, X, Y))` | Adds the pair of d and e of the process to the list of its CPU. The CPU comes from the option `--cpus`. |
| 60 | `    med = {c: st.median(x[0] for x in v) for c, v in by.items()}` | `med`: per CPU, the median of d over its processes. |
| 61 | `    aa = {c: max(abs(x[1]) for x in v) for c, v in by.items()}` | `aa`: per CPU, the A/A spread: the largest absolute e of its processes. |
| 62 | `    n = sum(len(v) for v in by.values())` | `n`: the number of processes. |
| 63 | `    print('%s: %d processes (%s per CPU), d below 0 in %d, median d per CPU %.2f to %.2f GB/s, A/A spread per CPU %.2f to %.2f GB/s' % (` | Prints the line. Its format: the label, the number of processes with the count per CPU, the number of processes with d below 0, the lowest and the highest median d of a CPU in GB/s, and the lowest and the highest A/A spread of a CPU in GB/s, each with 2 decimals. |
| 64 | `        label, n, '/'.join(str(len(v)) for v in by.values()), sum(x[0] < 0 for v in by.values() for x in v),` | Continues the statement: the label, the count, the counts per CPU with slashes between them, and the number of processes whose d is below 0. |
| 65 | `        min(med.values()), max(med.values()), min(aa.values()), max(aa.values())))` | Continues the statement: the lowest and the highest value of `med` and of `aa`. |

### Per session: levels in B4 and C1, counters in C2, pair values of B1, B2 and B3 (lines 68 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 68 | `for s in (1, 2):` | Loop over the two sessions. The lines up to line 167 run once for each. |
| 69 | `    F = folders(s)` | `F`: the result folders of the session by their step part. |
| 70 | `    print('== session s%d' % s)` | Prints a heading line with the session name, `s1` or `s2`. |
| 71 | `    print('-- B4: intervals per process by level (low below 69, high above 70.5 GB/s)')` | Prints the heading for B4: the intervals per process by level. B4 is the step with one thread, an 8 MiB buffer and asm read alone for 200 intervals of 0.3 s. Half of its processes run with the option `--no-thp`. |
| 72 | `    for p in procs(R + F['B4'] + '/B4.csv'):` | Loop over the processes of the file `B4.csv` in the B4 folder of the session. |
| 73 | `        r = [rate(t) for t in p['T']]` | `r`: the rate of every T row of the process. With one thread this is one rate per interval. |
| 74 | `        lo, hi = sum(x < LOW for x in r), sum(x > HIGH for x in r)` | `lo`: the number of intervals below 69.0 GB/s. `hi`: the number above 70.5 GB/s. |
| 75 | `        print('   %-15s intervals %d low %d high %d between %d lowest %.2f highest %.2f first %.2f' % (p['tag'], len(r), lo, hi, len(r) - lo - hi, min(r), max(r), r[0]))` | Prints one line per process: its tag, the number of intervals, the low ones, the high ones, the ones between the two limits, the lowest and the highest rate, and the rate of the first interval. |
| 76 | `    r = [rate(t) for p in procs(R + F['C1'] + '/C1.csv') for t in p['T']]` | `r`: the rate of every T row of every process of step C1. C1 repeats B4 with counters. |
| 77 | `    print('-- C1: %d intervals, highest %.2f GB/s, above 70.5 GB/s: %d' % (len(r), max(r), sum(x > HIGH for x in r)))` | Prints one line for C1: the number of intervals, the highest rate in GB/s, and the number of intervals above 70.5 GB/s. |
| 78 | `    print('-- C2: asm read reference intervals with counters, by their own rate; medians per 64 B line')` | Prints the heading for C2: the reference intervals of asm read with counters, grouped by their own rate, with medians per 64 B line. C2 repeats the sequence of B1 at 8 MiB with counters. In that sequence asm read is timed before and after each compared pair. |
| 79 | `    g = collections.defaultdict(list)` | `g`: a dictionary from a level to a list of values, empty at first. |
| 80 | `    for p in procs(R + F['C2'] + '/C2.csv'):` | Loop over the processes of the file `C2.csv`. |
| 81 | `        tm = {(t[1], t[2]): t for t in p['T']}` | `tm`: the T row of each interval of the process, by its round and position as text. |
| 82 | `        for c in p['C']:` | Loop over the C rows of the process. |
| 83 | `            if c[3] != 'asmread':` | Tests whether the kernel of the row, field 3, is not `asmread`. |
| 84 | `                continue` | Such a row is left out. |
| 85 | `            t = tm[(c[1], c[2])]` | `t`: the T row of the same round and position. |
| 86 | `            x, lines = rate(t), float(t[6]) / 64` | `x`: the rate of that interval in GB/s. `lines`: its bytes divided by 64, the number of 64 B lines. |
| 87 | `            en, ru, cpu, cy, ins, l1, l2 = [float(v) for v in c[6:13]]` | Reads seven fields of the C row as numbers: the enabled time and the running time of the counter group and the CPU time of the thread, all in ns, then the cycles, the instructions, the L1 refills and the L2 refills. A field with the text `NA` stops the script with an error here. |
| 88 | `            assert en == ru` | Stops the script with an error unless the running time equals the enabled time. So only rows whose counter group ran the whole time go on. |
| 89 | `            g['high' if x > HIGH else 'low' if x < LOW else 'between'].append((x, ins / lines, l1 / lines, l2 / lines, cy / cpu))` | Adds five values to the list of the level of the interval: its rate, the instructions per line, the L1 refills per line, the L2 refills per line, and the cycles divided by the CPU time in ns, which is the clock in GHz. The level is `high` above 70.5 GB/s, `low` below 69.0 GB/s, and `between` in the other cases. |
| 90 | `    for k in ('low', 'between', 'high'):` | Loop over the three levels. |
| 91 | `        v = g[k]` | `v`: the values of the level. |
| 92 | `        print('   %-7s %3d intervals, %.3f to %.3f GB/s, instructions %.4f, L1 refills %.4f, L2 refills %.4f, clock %.4f GHz' % (` | Prints one line per level: the number of intervals, the lowest and the highest rate, and the medians of the instructions, the L1 refills and the L2 refills per line and of the clock in GHz. |
| 93 | `            k, len(v), min(x[0] for x in v), max(x[0] for x in v), *[st.median(x[i] for x in v) for i in (1, 2, 3, 4)]))` | Continues the statement: the values for that line. A level without an interval stops the script with an error: an empty list has no lowest value. |
| 94 | `    print('-- B1 at 8 MiB, B2, B3: d and A/A spread over all processes of a CPU (description without labels)')` | Prints the heading for B1 at 8 MiB, B2 and B3: d and the A/A spread over all processes of a CPU, as a description without labels. |
| 95 | `    group([p for p in procs(R + F['B1'] + '/B1.csv') if p['bytes'] == '8M'], 'copy', 'asmcopy', '   B1 8 MiB copy - asmcopy')` | Prints the line for B1: the processes of `B1.csv` with 8 MiB buffers, with the pair `copy` minus `asmcopy`. B1 compares the new C copy kernel with the asm copy kernel in one process. |
| 96 | `    b2 = procs(R + F['B2'] + '/B2.csv')` | `b2`: the processes of the file `B2.csv`. B2 replaces the C copy kernel by one of three asm kernels. By the handoff the first holds the machine code of the C copy loop, the second has its two `add` instructions moved, and the third uses other registers. |
| 97 | `    for v in ('asmcopy_c', 'asmcopy_c_add', 'asmcopy_c_reg'):` | Loop over the three variants of B2: `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 98 | `        group([p for p in b2 if v in p['seq']], v, 'asmcopy', '   B2 %s - asmcopy' % v)` | Prints the line for the processes whose sequence holds this variant, with the pair variant minus `asmcopy`. |
| 99 | `    b3 = procs(R + F['B3'] + '/B3.csv')` | `b3`: the processes of the file `B3.csv`. B3 runs the sequence of B1 with three builds of the runner, in which both copy loops start at 0, 36 or 52 modulo 64. |
| 100 | `    for b in ('bwx_o0', 'bwx_o36', 'bwx_o52'):` | Loop over the three binaries of B3: `bwx_o0`, `bwx_o36` and `bwx_o52`. |
| 101 | `        group([p for p in b3 if p['bin'] == b], 'copy', 'asmcopy', '   B3 %s copy - asmcopy' % b)` | Prints the line for the processes of this binary, with the pair `copy` minus `asmcopy`. |

### Per session: old read by position in B6, and D as a share of the old read total in B7 (lines 102 to 141)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `    print('-- B6: old read at 8 MiB by position (sequence positions count from 0)')` | Prints the heading for B6: old read at 8 MiB by its position in the sequence. B6 times old read at 8 MiB, old read at 1 MiB (`oldread@1M`) and a second copy of old read (`oldread2`), with asm read intervals between them. |
| 103 | `    first, second, aa_first_slower, aa_n = collections.defaultdict(list), collections.defaultdict(list), 0, 0` | Four start values: two dictionaries from a CPU to a list (`first` and `second`), and two counters for the A/A pairs. |
| 104 | `    b6 = procs(R + F['B6'] + '/B6.csv')` | `b6`: the processes of the file `B6.csv`. |
| 105 | `    for p in b6:                                                      # per CPU: median over the processes of the process median` | Loop over them. The comment says how the values are combined: per CPU, the median over the processes of the median of each process. |
| 106 | `        r = one_thread_rates(p)` | `r`: the rate per round and position. |
| 107 | `        rounds = sorted({k[0] for k in r})` | `rounds`: the rounds of the process, sorted. |
| 108 | `        first[int(p['cpu'])].append(st.median(r[(rd, 1)] - r[(rd, 2)] for rd in rounds))      # oldread directly after asmread, minus oldread@1M` | Adds to `first` of the CPU: the median over the rounds of the rate at position 1 minus the rate at position 2. Position 1 is old read at 8 MiB directly after an asm read interval. Position 2 is old read at 1 MiB. |
| 109 | `        second[int(p['cpu'])].append(st.median(r[(rd, 5)] - r[(rd, 4)] for rd in rounds))     # oldread after oldread@1M, minus oldread@1M` | Adds to `second` of the CPU: the median over the rounds of the rate at position 5 minus the rate at position 4. Position 5 is old read at 8 MiB after an interval of old read at 1 MiB, which stands at position 4. |
| 110 | `        for rd in rounds:` | Loop over the rounds. |
| 111 | `            for a, b in ((7, 8), (10, 11)):                           # two old read intervals at 8 MiB after an asm read interval` | Loop over two pairs of positions, 7 with 8 and 10 with 11. Each pair holds the two copies of old read at 8 MiB, and its first interval follows an asm read interval. |
| 112 | `                aa_n += 1` | Counts the pair. |
| 113 | `                aa_first_slower += r[(rd, a)] < r[(rd, b)]` | Counts the pair when its first interval has a lower rate than its second. |
| 114 | `    print('   %d processes (%s per CPU); pair value per CPU, old read timed first: %.2f to %.2f GB/s; timed second: %.2f to %.2f GB/s; A/A pairs with the first interval slower: %d of %d' % (` | Prints one line for B6. Its format: the number of processes with the count per CPU, the range over the CPUs of the pair value with old read timed first, the same range with old read timed second, both in GB/s, and the number of A/A pairs with the first interval slower. |
| 115 | `        len(b6), '/'.join(str(sum(int(p['cpu']) == c for p in b6)) for c in sorted(first)),` | Continues the statement: the number of processes and the count per CPU. |
| 116 | `        min(st.median(v) for v in first.values()), max(st.median(v) for v in first.values()),` | Continues the statement: the lowest and the highest value over the CPUs of the median of `first`. |
| 117 | `        min(st.median(v) for v in second.values()), max(st.median(v) for v in second.values()), aa_first_slower, aa_n))` | Continues the statement: the same for `second`, and the two counters. |
| 118 | `    print('-- B7: median D of a setting as a share of the median old read total of the same processes (M_hist)')` | Prints the heading for B7: the median D of a setting as a share of the median old read total of the same processes, with `M_hist`. B7 runs the four read kernels with 120 threads in 8 timing settings. D is the total of old read minus the total of new read. |
| 119 | `    res = collections.defaultdict(list)` | `res`: a dictionary from a setting to a list of process values, empty at first. |
| 120 | `    for p in procs(R + F['B7'] + '/B7.csv'):` | Loop over the processes of the file `B7.csv`. |
| 121 | `        if len(p['seq']) != 8:` | Tests whether the sequence does not have 8 entries. |
| 122 | `            continue` | Such a process is left out. These are the processes with one kernel per process. |
| 123 | `        iv = collections.defaultdict(lambda: [0.0, 0.0])` | `iv`: per interval a pair of two numbers that start at 0: the sum of the bytes, and the longest elapsed time. |
| 124 | `        for t in p['T']:` | Loop over the T rows of the process, one per thread and interval. |
| 125 | `            k = (int(t[1]), int(t[2]))` | `k`: the round and the position of the row. |
| 126 | `            iv[k][0] += float(t[6])` | Adds the bytes of the thread (field 6) to the sum of the interval. |
| 127 | `            iv[k][1] = max(iv[k][1], float(t[7]))` | Keeps the longest elapsed time (field 7) of the interval. |
| 128 | `        m = {k: v[0] / v[1] / 1e9 for k, v in iv.items()}` | `m`: the total `M_hist` of each interval in GB/s: the bytes of all threads divided by the longest elapsed time of a thread and by 1e9. |
| 129 | `        ds, olds = [], []` | `ds` and `olds`: one value per round, empty at first. |
| 130 | `        for rd in sorted({k[0] for k in m}):` | Loop over the rounds. |
| 131 | `            o = [m[(rd, i)] for i, k in enumerate(p['seq']) if k == 'oldread']` | `o`: the totals of the intervals of this round whose entry is `oldread`. |
| 132 | `            n = [m[(rd, i)] for i, k in enumerate(p['seq']) if k == 'read']` | `n`: the totals of the intervals of this round whose entry is `read`, the new read kernel. |
| 133 | `            ds.append(st.mean(o) - st.mean(n))` | Adds the D of the round: the mean of `o` minus the mean of `n`. |
| 134 | `            olds.append(st.mean(o))` | Adds the mean old read total of the round. |
| 135 | `        res[(p['stop'], p['ms'], p['start'])].append((st.mean(ds), st.mean(olds)))` | Adds the process values to the list of its setting: the mean of D over the rounds, and the mean old read total over the rounds. The setting is the stop method, the interval length and the start of the header line. |
| 136 | `    pct = []` | `pct`: the share of each setting, empty at first. |
| 137 | `    for k, v in sorted(res.items()):` | Loop over the settings in sorted order. |
| 138 | `        D, O = st.median(x[0] for x in v), st.median(x[1] for x in v)` | `D`: the median over the processes of their D. `O`: the median over the processes of their old read total. |
| 139 | `        pct.append(100 * D / O)` | Adds the share: 100 times `D` divided by `O`, in %. |
| 140 | `        print('   %-22s %d processes, median D %.2f GB/s, median old read total %.2f GB/s, share %.1f %%' % ('/'.join(k), len(v), D, O, 100 * D / O))` | Prints one line per setting: the setting, the number of processes, the median D and the median old read total in GB/s with 2 decimals, and the share in % with 1 decimal. |
| 141 | `    print('   share over the 8 settings: %.1f to %.1f %%' % (min(pct), max(pct)))` | Prints the lowest and the highest share over the settings. The text of the line says `8 settings`. The script does not count them. |

### Per session: the end skew with whole passes in B10 and B7 (lines 142 to 169)

| Line | Source | Explanation |
|---:|---|---|
| 142 | `    print('-- B10: largest end skew with whole passes')` | Prints the heading for B10: the largest end skew with whole passes. B10 runs the four write kernels with 120 threads in 8 timing settings. The end skew of an interval is the latest end time of a thread minus the earliest one. |
| 143 | `    best = (0, None)` | `best`: the largest end skew so far and the place where it occurs, 0 and `None` at first. |
| 144 | `    for h in ('B10a', 'B10b'):` | Loop over the two result folders of B10, `B10a` and `B10b`. |
| 145 | `        for p in procs(R + F[h] + '/B10.csv'):` | Loop over the processes of the file `B10.csv` in that folder. |
| 146 | `            if p['stop'] != 'pass':` | Tests whether the process does not use the stop method `pass`. |
| 147 | `                continue` | Such a process is left out. |
| 148 | `            ends = collections.defaultdict(list)` | `ends`: per interval the list of the end times of its threads, empty at first. |
| 149 | `            for t in p['T']:` | Loop over the T rows of the process. |
| 150 | `                ends[(t[1], t[2])].append(float(t[10]))` | Adds the end time of the thread, field 10 (`t_end_s`, in s), to the list of its interval. |
| 151 | `            for k, v in ends.items():` | Loop over the intervals. |
| 152 | `                if max(v) - min(v) > best[0]:` | Tests whether the end skew of the interval is larger than the largest so far. |
| 153 | `                    best = (max(v) - min(v), '%s %s interval %s/%s, --min-ms %s' % (h, p['tag'], k[0], k[1], p['ms']))` | Then `best` becomes this end skew, with a text that names the folder, the tag of the process, the round and position of the interval, and the interval length of the process. |
| 154 | `    print('   %.1f ms in %s' % (best[0] * 1000, best[1]))` | Prints the largest end skew in ms with 1 decimal, and its place. |
| 155 | `    print('-- B7, B10: intervals with whole passes and an end skew above 5 ms (choice A5)')` | Prints the heading for the next count: the intervals of B7 and B10 with whole passes whose end skew is above 5 ms. The heading names choice A5 of the analysis: with whole passes an end skew above 5 ms does not make an interval irregular. |
| 156 | `    for step, hs in (('B7', ('B7',)), ('B10', ('B10a', 'B10b'))):` | Loop over the two steps, each with its result folders: B7 with one folder, B10 with two. |
| 157 | `        n = over = 0` | `n` and `over`: two counters that start at 0. |
| 158 | `        for h in hs:` | Loop over the folders of the step. |
| 159 | `            for p in procs(R + F[h] + '/%s.csv' % step):` | Loop over the processes of the csv file of the step in that folder. |
| 160 | `                if p['stop'] != 'pass':` | Tests whether the process does not use the stop method `pass`. |
| 161 | `                    continue` | Such a process is left out. |
| 162 | `                ends = collections.defaultdict(list)` | `ends`: per interval the list of the end times of its threads. |
| 163 | `                for t in p['T']:` | Loop over the T rows of the process. |
| 164 | `                    ends[(t[1], t[2])].append(float(t[10]))` | Adds the end time of the thread to the list of its interval. |
| 165 | `                n += len(ends)` | Adds the number of intervals of the process to `n`. |
| 166 | `                over += sum(max(v) - min(v) > 0.005 for v in ends.values())` | Adds to `over` the number of intervals whose end skew is above 0.005 s. |
| 167 | `        print('   %s: %d of %d intervals' % (step, over, n))` | Prints one line per step: how many of its intervals with whole passes have an end skew above 5 ms. This is the last line of the loop over the sessions. |

### Checks over both sessions and the short run (lines 170 to 202)

| Line | Source | Explanation |
|---:|---|---|
| 170 | `print('== checks that only a build on CRB could make (DEVIATIONS-bwx.md), from the raw files of both sessions and of the short run')` | Prints the heading of the last block: checks that only a build on CRB could make, from the raw files of both sessions and of the short run. The notes on the runner (`DEVIATIONS-bwx.md`) list these open points: the counters without root, the time of the page reading, and the flags `late`. |
| 171 | `big = rows = 0` | `big` and `rows`: two counters for the C rows, 0 at first. |
| 172 | `worst_read = (0.0, None)` | `worst_read`: the longest page reading so far and its place. |
| 173 | `late = trows = 0` | `late` and `trows`: two counters for the T rows, 0 at first. |
| 174 | `for s in (1, 2):` | Loop over the two sessions. |
| 175 | `    F = folders(s)` | `F`: the result folders of the session. |
| 176 | `    for h, f in F.items():` | Loop over the folders. `h` is the step part and `f` the folder name. |
| 177 | `        step = 'B10' if h.startswith('B10') else h` | `step`: the name of the csv file without its ending. The two folders of B10 both hold `B10.csv`. |
| 178 | `        for l in open(R + f + '/%s.csv' % step):` | Loop over the lines of the csv file of the folder. This loop reads the files of all steps, also of the steps with one thread. |
| 179 | `            if l.startswith('C,'):` | Tests whether the line is a C row. |
| 180 | `                c = l.rstrip().split(',')` | `c`: its fields. |
| 181 | `                rows += 1` | Counts the C row. |
| 182 | `                big += any(v != 'NA' and float(v) > 1e13 for v in c[9:14])` | Counts the row in `big` when one of its counter values, the fields 9 to 13, is not `NA` and is above 1e13. |
| 183 | `            elif l.startswith('T,'):` | Tests whether the line is a T row. |
| 184 | `                trows += 1` | Counts the T row. |
| 185 | `                late += 'late' in l.rstrip().split(',')[12]` | Counts the row in `late` when its flag, field 12, holds the word `late`. With the common stop the runner sets this flag when a thread starts more than 100 microseconds after the common start time. |
| 186 | `            elif l.startswith('# page_read'):` | Tests whether the line is a `# page_read` line. The runner prints such a line after its main thread has read the page state of all buffers between two intervals. The line gives the time of that reading in ms. |
| 187 | `                ms = float(l.split(',')[3].split()[0])` | `ms`: that time as a number: the first word of the fourth field of the line. |
| 188 | `                if ms > worst_read[0]:` | Tests whether it is the longest so far. |
| 189 | `                    worst_read = (ms, 's%d %s' % (s, h))` | Then `worst_read` becomes this time, with the session and the step part of the folder. |
| 190 | `print('   C rows: %d, of them with a count above 1e13 (a value near 2^47 is 1.4e14): %d' % (rows, big))` | Prints the number of C rows, and how many of them have a count above 1e13. The text in brackets gives the size of the value that the check looks for: a value near 2 to the power of 47 is 1.4e14. |
| 191 | `print('   T rows: %d, of them with the flag late: %d' % (trows, late))` | Prints the number of T rows, and how many of them have the flag `late`. |
| 192 | `print('   longest page reading of the main thread: %.2f ms (%s)' % worst_read)` | Prints the longest page reading of the main thread in ms with 2 decimals, and its place. |
| 193 | `cur = None` | `cur`: the arguments of the process that is read now, `None` at first. |
| 194 | `for l in open(R + 'SHORT-20261113T214338Z/SHORT.csv'):` | Loop over the lines of the csv file of the short run, in the folder `SHORT-20261113T214338Z`. The short run is one run of every sequence with intervals of 0.1 s. |
| 195 | `    if l.startswith('-- step'):` | Tests whether the line is a header line. |
| 196 | `        cur = l.split(' args ')[1].strip()` | `cur`: the arguments of that process. |
| 197 | `    elif l.startswith('T,') and '32K' in cur:` | Tests whether the line is a T row of a process whose arguments hold `32K`. That is the process with one thread and a 32 KiB buffer, made to count the instructions of the asm read loop. |
| 198 | `        t = l.split(',')` | `t`: the fields of the row. |
| 199 | `        tb = float(t[6])` | `tb`: the bytes of the thread in that interval. |
| 200 | `    elif l.startswith('C,') and '32K' in cur:` | Tests whether the line is a C row of such a process. The runner prints the C row of an interval after its T row. |
| 201 | `        c = l.rstrip().split(',')` | `c`: the fields of the row. |
| 202 | `        print('   short run, %s interval %s/%s (%s): %.4f instructions per 256 B' % (c[3], c[1], c[2], cur[:60], float(c[10]) / (tb / 256)))` | Prints one line per interval: the kernel, the round and the position, the first 60 characters of the arguments, and the instructions per 256 B with 4 decimals. The value is field 10 of the C row, the instruction count, divided by the bytes of the T row over 256. The handoff expects 11 instructions per 256 B for the asm read loop and accepts a value within 3 %. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: the result handoff. Its reference 21 names this script and its output, and its section "What was run" lists the two sessions.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the plan: rule 5 (the level limits) and the tables of the steps.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff: section B.3 (output rows), B.8 (the test of 11 instructions per 256 B), B.9 (the sequences of the steps) and B.10 (pair values, d and e).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-scripts.md`: the choices A2 and A5 of the analysis script.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: the added line `# page_read`, and the list of the points that only a build on CRB can verify.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/logs/session1-folders.txt` and `session2-folders.txt` in the same folder: the two folder lists. The result folders lie in `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/`.
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/run_bwx.sh`: the run script, with the sequences of B1 and B6 and the process of the short run with a 32 KiB buffer.
