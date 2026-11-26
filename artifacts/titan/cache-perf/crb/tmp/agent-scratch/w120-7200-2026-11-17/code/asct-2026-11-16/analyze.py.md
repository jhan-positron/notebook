# `analyze.py` explained, line by line

- Source file: `asct-2026-11-16/analyze.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 306 lines, 14907 bytes).
- sha256 of the source when this page was built: `1ae210f3b28a323163f173003eaeffc5f9a529ab678f8a6ce200d6768457794f`.

## Short version: purpose

`analyze.py` reads the result folders of the ASCT cross-check and writes one JSON file, which the project keeps as `asct.json`. For each process it takes the rates that the ASCT binary printed and, when the process counted events, the counts per 64-byte line. It also checks the files and lists every failed check as a problem.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **ASCT binary**: the benchmark program of ASCT, `loaded-latency-asct-sve.bin`. The run scripts start it directly. One start is one process.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Process**: one start of a benchmark binary.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Repetition**: one pass of a thread over its buffer in the measured phase. The ASCT binary prints the number of repetitions and the time of each thread.
- **Line**: one cache line of 64 bytes.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Median**: the middle value of a sorted list of values.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter capture**: the counter code of ASCT inside the probe binary. It reads a list of raw codes from the environment variable `DIETPERF_PMUv3`. It writes its counter files to the folder that `DIETPERF_OUTDIR` names.
- **Probe binary**: the ASCT binary built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT.
- **Raw code**: the number that selects one counter event in the counter unit of the cores.
- **Event set**: a named list of counter events that one process counts together. The file `events.codes` holds one set per line.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Cell**: all processes with the same settings, for example one CPU and one buffer size.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Mesh unit**: the counter unit that Linux shows for one mesh. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **`perf stat`**: the Linux command that counts events while another command runs.
- **Counting window**: one run of `perf stat -a` for the command `sleep` in the script `run_mesh.sh`.
- **`launches.txt`**: a file that each run script writes into its result folder. It gets one `launch` line before each process and one `rc` line after it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` takes the output file from argument 1 and the result folders from the later arguments. It picks the function for each folder by the start of the folder name (lines 281 to 296).
2. A one-core folder goes to `do_single`. For each output file of the parts U, N, NC and C it reads the total of the process with `parse_out` and appends it to the list of its cell. For the parts NC and C it also reads the counter files with `parse_counters`, which gives counts per line and two checks (lines 121 to 166).
3. A many-core folder goes to `do_chip`. For each read process it keeps sums and ranges per mesh and a lower bound of the total (`mesh_split`). For the processes with counters it keeps the smallest, the median and the largest count per line over the threads of each mesh (lines 180 to 219).
4. A mesh-counter folder goes to `do_mesh`. It reads the settings and the times from `launches.txt`, checks that each counting window lies inside the measured phase, and reads the counts from the result files of `perf stat` (lines 222 to 278).
5. For a preparation folder the texts of `env.txt`, `sha.txt` and `resolve.txt` are stored unchanged (lines 291 to 294).
6. Each folder of the steps 2 to 4 also gets a summary of `launches.txt`: the load at the starts and the exit statuses (lines 103 to 118). A preparation folder gets none.
7. The script writes everything as JSON to the output file. Then it prints one line per folder and the first 8 problems of the folder (lines 297 to 302).

## Behavior a reader must know

- The script times nothing. Every time and every repetition count comes from the output of the ASCT binary. How that binary times a thread is not visible in this repo, which does not hold the ASCT source. Its output gives one repetition count and one time per thread [Ref1]. The report text in `dyn_notes.py` says that every thread runs the same number of passes and measures its own time.
- Rate of a thread: repetitions times buffer bytes, divided by the time of that thread and by 1e9, in GB/s (line 50). Total of a process: the number of the line `Total Bandwidth (MB/sec)` divided by 1000, in GB/s (line 40).
- Every pass counts all bytes of the buffer. By the decisions file ASCT counts 64 bytes for each line, although its read loop loads 8 bytes of the line [Ref3].
- The total that ASCT prints is a sum of thread rates, and each thread has its own time. The value `floor` of line 176 divides all bytes of the process by the longest time of a thread. The decisions file added it as a lower bound after the many-core data was seen [Ref3].
- Count per line: the count of a counter file divided by the lines of the measured phase of the same thread, which is repetitions times buffer bytes divided by 64 (line 51, line 77).
- A failed check does not stop the script. It adds a text to the list `problems` of the folder, and the console report prints the first 8 of them. A value that fails a check stays in the output. Three things are left out, each with a problem text: an output file without a result (lines 45 to 46), a counter file that fits no thread of its output file (lines 62 to 64) and a mesh event that `perf stat` printed without a count (lines 268 to 271).
- The exit status of a process is counted in `rc_nonzero` but not tested. A process with another status than 0 is used when its output holds a total.
- These things stop the script, among others: a folder name of an unknown kind (exit status 1, line 296), a missing file that the code opens without a test (line 225, lines 292 to 294), a result line of a thread without a settings line (line 49), a file name that does not have the expected form (line 60, line 184), and a field of a counter file that is not a number (line 70).
- A counter folder that does not exist gives no counts and no problem text (line 59).
- The list of a counted cell mixes the processes of all event sets. Its `rate` list holds every process. An event list holds only the processes that counted the event (lines 151 to 153, lines 163 to 165).
- In `asct.json` of this folder the list `mesh` is empty [Ref6]. So `do_mesh` has no result in the data of the report.
- The script `facts.py` of the same folder reads the output file.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/analyze.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (306 lines, 14907 bytes, sha256 `1ae210f3b28a323163f173003eaeffc5f9a529ab678f8a6ce200d6768457794f`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text, modules and constants (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""analyze.py OUT.json FOLDER...: read ASCT result folders (asct-single-*, asct-chip-*, asct-mesh-*, asct-prep-*)` | Starts the description text of the file. Usage: argument 1 is the output file, and each later argument is one result folder. The script reads result folders of the ASCT cross-check. Their names start with `asct-single-`, `asct-chip-`, `asct-mesh-` or `asct-prep-`. |
| 3 | `and write every number the report uses. GB = 1e9 bytes. A line = 64 bytes.` | Description, continued: the text says that the script writes every number that the report uses. That is not exact: the report also uses values of `baseline.json`, values that `facts.py` and `dyn_notes.py` derive, and fixed numbers. GB means 1e9 bytes. A line is one cache line of 64 bytes. |
| 5 | `Rates come from the lines the ASCT binary prints for its measured phase:` | Description, continued: the rates come from the lines that the ASCT binary prints for its measured phase. |
| 6 | `  'tid = T, repetitions = R, tickdiff = D, time = S'  ->  thread rate = R * buflen / S` | Description, continued: the result line of one thread. `T` is the thread id, `R` the repetitions, `D` a count of timer ticks and `S` the time in seconds. The rate of the thread is `R` times the buffer length in bytes, divided by `S`. So one repetition is one pass of the thread over its buffer. |
| 7 | `  'Total Bandwidth (MB/sec) = X'                       ->  process total (sum of the thread rates)` | Description, continued: the line `Total Bandwidth (MB/sec) = X` gives the total of the process. The ASCT binary builds it as the sum of the rates of the threads. |
| 8 | `Counter files are written by ASCT's capture code (dietperf): one file <cpu>_<tid> per thread, one line per` | Description, continued: the counter files come from the counter capture of ASCT, which has the name dietperf. One file belongs to one thread. Its name is the CPU number, an underscore and the thread id. |
| 9 | `event: code,count,time_enabled_ns,time_running_ns. Counts are divided by the lines of the measured phase.` | Description, last text line: a counter file has one line per event with four fields. They are the raw code, the count, the time that the counter was enabled and the time that it ran, both in ns. The script divides each count by the number of lines of the measured phase. |
| 10 | `"""` | Ends the description text. |
| 11 | `import glob` | Loads the module `glob`, which lists the files that fit a name pattern. |
| 12 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 13 | `import os` | Loads the module `os`. The script uses its path functions. |
| 14 | `import re` | Loads the module `re` for regular expressions. |
| 15 | `import statistics as st` | Loads the module `statistics` under the short name `st`. The script uses its function `median`. |
| 16 | `import sys` | Loads the module `sys`, which gives the arguments of the script. |
| 18 | `LINE = 64` | `LINE`: 64, the number of bytes of one cache line. |
| 19 | `MESH0 = range(0, 64)` | `MESH0`: the CPU numbers 0 to 63. These CPUs sit on mesh 0. The code counts every other CPU as mesh 1. |

### Function `parse_out`: the rates of one process (lines 22 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `def parse_out(path):` | Starts the function `parse_out`. It reads the output file `path` of one start of the ASCT binary and returns the rates of that process. |
| 23 | `    """One process output -> dict or None when the process printed no total."""` | Description of the function: it returns a dictionary, or `None` when the process printed no total. |
| 24 | `    tid_cpu, buflen, nops = {}, None, None` | `tid_cpu`: a dictionary from the thread id to the CPU number. `buflen`: the buffer length of one thread in bytes. `nops`: the count of injected NOPs that the binary reports. `buflen` and `nops` are `None` until a settings line gives them. |
| 25 | `    threads = {}` | `threads`: a dictionary from the thread id to the repetitions and the time of that thread. |
| 26 | `    total = reps = None` | `total`: the total rate that the binary prints. `reps`: the repetition count that the binary prints for the process. Both start as `None`. |
| 27 | `    for line in open(path, errors='replace'):` | Starts a loop over the lines of the file. `errors='replace'`: a byte that is not valid text becomes a substitute character. So such a byte does not stop the script. |
| 28 | `        m = re.match(r'CPU(\d+) BWTHREAD(\d+): buflen = (\d+), .*inner_nops = (\d+), .*tid = (\d+)', line)` | Pattern for the settings line that the binary prints for each thread before the run [Ref1]. `re.match` tests a pattern at the start of the line. This one matches `CPU`, a number, one space, `BWTHREAD`, a number, `: buflen = `, a number, then any text up to `inner_nops = `, a number, then any text up to `tid = ` and a number. The five groups hold the CPU number, the number of the thread inside the process, the buffer length in bytes, the count of injected NOPs and the thread id. |
| 29 | `        if m:` | When the line is a settings line: |
| 30 | `            tid_cpu[int(m.group(5))] = int(m.group(1))` | stores the CPU number (group 1) under the thread id (group 5), |
| 31 | `            buflen, nops = int(m.group(3)), int(m.group(4))` | keeps the buffer length (group 3) and the count of injected NOPs (group 4). Each settings line overwrites the values of the line before it. So the code assumes that all threads of one process have the same two values. |
| 32 | `            continue` | and goes to the next line of the file. |
| 33 | `        m = re.match(r'tid = (\d+), repetitions = (\d+), tickdiff = (\d+), time = ([0-9.]+)', line)` | Pattern for the result line of one thread [Ref1]. It matches `tid = `, a number, `, repetitions = `, a number, `, tickdiff = `, a number, `, time = ` and a number that may hold a dot. The four groups hold the thread id, the repetitions, the tick count and the time of the measured phase of this thread in seconds. The script does not use the tick count. |
| 34 | `        if m:` | When the line is the result line of a thread: |
| 35 | `            tid, r, sec = int(m.group(1)), int(m.group(2)), float(m.group(4))` | `tid`: the thread id. `r`: the repetitions, which is the number of passes of the thread over its buffer in the measured phase. `sec`: the time of the measured phase of this thread in seconds. The ASCT binary measured this time. This script reads no clock. |
| 36 | `            threads[tid] = {'reps': r, 'sec': sec}` | stores the repetitions and the time under the thread id, |
| 37 | `            continue` | and goes to the next line of the file. |
| 38 | `        m = re.match(r'Total Bandwidth \(MB/sec\) = ([0-9.]+)', line)` | Pattern for the total of the process. It matches the text `Total Bandwidth (MB/sec) = ` and a number, which group 1 holds. The two backslashes of the pattern make the parentheses plain characters. The line `Total Bandwidth (B/cycle)` of the same output does not match. |
| 39 | `        if m:` | When the line is the total line: |
| 40 | `            total = float(m.group(1)) / 1e3` | `total`: the printed number divided by 1e3. The binary prints MB/s with 1 MB = 1e6 bytes [Ref1]. So `total` is in GB/s with GB = 1e9 bytes. |
| 41 | `            continue` | and goes to the next line of the file. |
| 42 | `        m = re.match(r'Bandwidth Repetitions = (\d+)', line)` | Pattern for the line `Bandwidth Repetitions = ` and a number, which group 1 holds. |
| 43 | `        if m:` | When the line fits: |
| 44 | `            reps = int(m.group(1))` | `reps`: the repetition count that the binary prints once for the whole process. |
| 45 | `    if total is None or not threads or buflen is None:` | Tests whether the file gave a result. There is no result when the total line is missing, when no thread printed a result line, or when no settings line gave a buffer length. |
| 46 | `        return None` | In that case the function returns `None`. |
| 47 | `    per = {}` | `per`: a dictionary from the CPU number to the values of the thread on that CPU. |
| 48 | `    for tid, t in threads.items():` | Starts a loop over the threads that printed a result line. |
| 49 | `        cpu = tid_cpu[tid]` | `cpu`: the CPU of the thread, from its settings line. A result line whose thread id has no settings line stops the script with an error here. |
| 50 | `        per[cpu] = {'tid': tid, 'reps': t['reps'], 'sec': t['sec'], 'gbps': t['reps'] * buflen / t['sec'] / 1e9,` | Stores the values of the thread under its CPU: the thread id, the repetitions, the time and the rate `gbps`. The rate is the repetitions times the buffer length in bytes, divided by the time of this thread in seconds and by 1e9. So it is in GB/s, and each pass counts every byte of the buffer. The dictionary goes on in line 51. |
| 51 | `                    'lines': t['reps'] * buflen / LINE}` | Continues line 50. `lines`: the number of 64-byte lines that the thread passed in the measured phase. It is the repetitions times the buffer length, divided by `LINE`. |
| 52 | `    return {'total': total, 'reps': reps, 'buflen': buflen, 'nops': nops, 'threads': per,` | Returns the result of the process: `total` (the printed total in GB/s), `reps`, `buflen`, `nops` and `threads` (the dictionary `per`). The dictionary goes on in line 53. |
| 53 | `            'sum_threads': sum(t['gbps'] for t in per.values())}` | Continues line 52. `sum_threads`: the sum of the thread rates of line 50, in GB/s. No other script of this folder reads this value. |

### Function `parse_counters`: counts per line and two checks (lines 56 to 81)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `def parse_counters(folder, proc, names):` | Starts the function `parse_counters`. It reads the counter files of one process from the folder `folder`. `proc` is the result of `parse_out` for the same process. `names` gives the event name of each raw code. |
| 57 | `    """Counter folder of one process -> {cpu: {name: per-line count}}, plus the checks."""` | Description of the function: it returns for each CPU a dictionary from the event name to the count per line, and the list of the failed checks. |
| 58 | `    out, bad = {}, []` | `out`: the counts per CPU. `bad`: the texts of the failed checks. Both start empty. |
| 59 | `    for f in glob.glob(os.path.join(folder, '*')):` | Starts a loop over all files of the counter folder. When the folder does not exist, the loop has nothing to do. The function then returns no counts and no failed check. |
| 60 | `        cpu, tid = (int(x) for x in os.path.basename(f).split('_'))` | Splits the file name at the underscore. `cpu` is the first number and `tid` the second. A file name of another form stops the script with an error. |
| 61 | `        th = proc['threads'].get(cpu)` | `th`: the thread that `parse_out` found on this CPU, or `None`. |
| 62 | `        if th is None or th['tid'] != tid:` | Tests whether the output file has no thread on this CPU, or a thread with another thread id. |
| 63 | `            bad.append(f'no thread for {os.path.basename(f)}')` | Then the counter file belongs to no known thread. The text `no thread for` with the file name goes to `bad`, |
| 64 | `            continue` | and the loop goes to the next file. |
| 65 | `        row = {}` | `row`: the counts of this thread by event name. It starts empty. |
| 66 | `        for line in open(f):` | Starts a loop over the lines of the counter file. |
| 67 | `            p = line.strip().split(',')` | `p`: the fields of the line, split at the commas. |
| 68 | `            if len(p) != 4:` | A line that does not have exactly 4 fields |
| 69 | `                continue` | is skipped. |
| 70 | `            code, cnt, en, run = int(p[0], 16), int(p[1]), int(p[2]), int(p[3])` | `code`: the raw code, read as a hexadecimal number. `cnt`: the count. `en`: the time that the counter was enabled, in ns. `run`: the time that the counter ran, in ns. |
| 71 | `            name = names.get(code, hex(code))` | `name`: the event name of the code. For a code that `names` does not hold it is the code as hexadecimal text. |
| 72 | `            if run != en:` | Check 1: the counter ran for the whole time that it was enabled. Linux lets events take turns on a hardware counter when a thread asks for more events than the core has counters. Then the running time is shorter than the enabled time [Ref4]. By the decisions file a set has at most 7 events, and with this size no event shares a counter [Ref3]. |
| 73 | `                bad.append(f'{name} cpu {cpu}: running {run} of enabled {en} ns')` | When the two times differ, a text with the event, the CPU and both times goes to `bad`. |
| 74 | `            ratio = en / 1e9 / th['sec'] if th['sec'] else 0` | `ratio`: the enabled time in seconds (`en / 1e9`) divided by the measured time `sec` of the thread. It is 0 when `sec` is 0. |
| 75 | `            if not 0.98 <= ratio <= 1.02:` | Check 2: the ratio lies between 0.98 and 1.02. So the time that the counter was enabled equals the measured phase of the thread within 2 %. |
| 76 | `                bad.append(f'{name} cpu {cpu}: enabled time is {ratio:.3f} of the measured time')` | When it does not, a text with the event, the CPU and the ratio goes to `bad`. |
| 77 | `            row[name] = cnt / th['lines']` | Stores the count per line: the count divided by the lines of the measured phase of this thread (`lines` of `parse_out`). The value is stored also when a check failed. |
| 78 | `        out[cpu] = row` | Stores the row of the thread under its CPU. |
| 79 | `    return out, bad` | Returns the counts and the list of the failed checks. |

### Functions `med` and `load_codes`: the median, and the event names (lines 82 to 102)

| Line | Source | Explanation |
|---:|---|---|
| 82 | `def med(v):` | Starts the function `med`: the median of a list that may be empty. |
| 83 | `    return st.median(v) if v else None` | Returns the median of `v`. For an empty list it returns `None`, where `st.median` would stop with an error. |
| 86 | `def load_codes(folder):` | Starts the function `load_codes`. It reads the file `events.codes` of a result folder. The scripts `run_single.sh` and `run_chip.sh` copy this file into each result folder. |
| 87 | `    names, sets = {}, {}` | `names`: a dictionary from the raw code to the event name. `sets`: a dictionary from the name of an event set to the list of its event names. |
| 88 | `    p = os.path.join(folder, 'events.codes')` | `p`: the path of `events.codes` in the folder. |
| 89 | `    if os.path.exists(p):` | Reads the file only when it exists. Without the file both dictionaries stay empty. |
| 90 | `        for line in open(p):` | Starts a loop over the lines of the file. |
| 91 | `            if '\|' not in line:` | A line without the character `\|` |
| 92 | `                continue` | is skipped. |
| 93 | `            s, evs = line.strip().split('\|')` | Splits the line at `\|`. `s` is the name of the set. `evs` is the text with its events. |
| 94 | `            sets[s] = []` | Starts an empty list for the set. |
| 95 | `            for e in evs.split(','):` | Starts a loop over the events of the set. Commas separate them. |
| 96 | `                if '=' in e:` | Takes only an entry of the form `name=code`. |
| 97 | `                    n, c = e.split('=')` | `n`: the event name. `c`: the raw code as hexadecimal text. |
| 98 | `                    names[int(c, 16)] = n` | Stores the name under the code as a number. |
| 99 | `                    sets[s].append(n)` | Appends the name to the list of the set. |
| 100 | `    return names, sets` | Returns both dictionaries. The callers in this file use `names` only. |

### Function `launches`: load and exit statuses from `launches.txt` (lines 103 to 120)

| Line | Source | Explanation |
|---:|---|---|
| 103 | `def launches(folder):` | Starts the function `launches`. It reads the file `launches.txt` of a result folder. It returns a summary of the machine load at the starts of the processes and of their exit statuses. |
| 104 | `    loads, rcs = [], []` | `loads`: one pair per started process, the 1-minute load average and the number of runnable tasks. `rcs`: the exit statuses. Both start empty. |
| 105 | `    p = os.path.join(folder, 'launches.txt')` | `p`: the path of `launches.txt` in the folder. |
| 106 | `    if not os.path.exists(p):` | When the file does not exist, |
| 107 | `        return {'n': 0}` | the function returns a summary with `n` = 0 and no other field. |
| 108 | `    for line in open(p):` | Starts a loop over the lines of the file. |
| 109 | `        m = re.match(r'launch (\S+) epoch ([0-9.]+) load ([0-9.]+) [0-9.]+ [0-9.]+ (\d+)/', line)` | Pattern for a `launch` line. The run script writes it directly before it starts a process, with the content of `/proc/loadavg` [Ref2]. The pattern matches `launch `, the tag, ` epoch `, a time, ` load `, three numbers and the digits before the slash of the next field. Group 1 holds the tag. Group 2 holds the time in seconds, counted from the start of the year 1970. Group 3 holds the 1-minute load average. Group 4 holds the number of tasks that were runnable at that moment. The function uses the groups 3 and 4 only. |
| 110 | `        if m:` | When the line is a `launch` line: |
| 111 | `            loads.append((float(m.group(3)), int(m.group(4))))` | appends the 1-minute load average and the number of runnable tasks to `loads`. |
| 112 | `        m = re.match(r'rc (-?\d+) (\S+)', line)` | Pattern for an `rc` line. The run script writes it after a process has ended. It matches `rc `, a number that may be negative, a space and the tag. Group 1 holds the exit status of the process, group 2 the tag. |
| 113 | `        if m:` | When the line is an `rc` line: |
| 114 | `            rcs.append(int(m.group(1)))` | appends the exit status to `rcs`. |
| 115 | `    return {'n': len(loads), 'load1_min': min(l[0] for l in loads) if loads else None,` | Returns the summary. `n`: the number of `launch` lines. `load1_min`: the smallest 1-minute load average at a start, or `None` without a `launch` line. The dictionary goes on in lines 116 to 118. |
| 116 | `            'load1_max': max(l[0] for l in loads) if loads else None,` | Continues line 115. `load1_max`: the largest 1-minute load average at a start. |
| 117 | `            'runnable_max': max(l[1] for l in loads) if loads else None,` | Continues line 115. `runnable_max`: the largest number of runnable tasks at a start. |
| 118 | `            'rc_nonzero': sum(1 for r in rcs if r != 0), 'rc_count': len(rcs)}` | Ends the summary. `rc_nonzero`: the number of processes with an exit status other than 0. `rc_count`: the number of `rc` lines. |

### Function `do_single`: one result folder of the one-core runs (lines 121 to 168)

| Line | Source | Explanation |
|---:|---|---|
| 121 | `def do_single(folder):` | Starts the function `do_single`. It reads one result folder of the script `run_single.sh`, which holds the one-core runs. |
| 122 | `    names, sets = load_codes(folder)` | Reads the event names of the folder with `load_codes`. |
| 123 | `    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'cells': {}, 'counted': {}, 'nops': {}, 'nops_counted': {}, 'problems': []}` | `res`: the result for this folder. `folder`: the last part of the folder path, which is empty when the argument ends with a slash. `launches`: the summary of `launches.txt`. `cells`: the rates of part U. `counted`: part C. `nops`: part N. `nops_counted`: part NC. `problems`: the texts of all failed checks. |
| 124 | `    for f in sorted(glob.glob(os.path.join(folder, 'u.*.out'))):` | Part U, the runs without counters: starts a loop over the files whose names fit `u.*.out`, in sorted order. |
| 125 | `        _, cpu, size, rep = os.path.basename(f)[:-4].split('.')` | Cuts the ending `.out` from the file name and splits the rest at the dots. The four pieces are the letter `u`, the CPU, the buffer size in bytes and the number of the process. |
| 126 | `        p = parse_out(f)` | `p`: the rates of the process, from `parse_out`. |
| 127 | `        if p is None:` | When the file holds no result, |
| 128 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 129 | `            continue` | and the loop goes to the next file. |
| 130 | `        res['cells'].setdefault(f'{cpu}.{size}', []).append(p['total'])` | Appends the total rate of the process, in GB/s, to the list of its cell. The key of a cell is the CPU and the buffer size, as in `2.8388608`. The script `run_single.sh` gives each process one CPU. So the total is the rate of one thread. |
| 131 | `    for f in sorted(glob.glob(os.path.join(folder, 'n.*.out'))):      # part N: injected NOPs` | Part N: starts a loop over the files that fit `n.*.out`. Comment: part N is the part with injected NOPs. |
| 132 | `        _, nn, cpu, size, rep = os.path.basename(f)[:-4].split('.')` | Splits the file name as in line 125. The five pieces are the letter `n`, the count of injected NOPs, the CPU, the buffer size and the number of the process. |
| 133 | `        p = parse_out(f)` | `p`: the rates of the process. |
| 134 | `        if p is None:` | When the file holds no result, |
| 135 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 136 | `            continue` | and the loop goes to the next file. |
| 137 | `        if p['nops'] != int(nn):` | Check: the count of injected NOPs that the binary reports equals the count in the file name. |
| 138 | `            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')` | When they differ, a text with the file name and the reported count goes to the problems. The rate is kept. |
| 139 | `        res['nops'].setdefault(f'{nn}.{cpu}.{size}', []).append(p['total'])` | Appends the total rate to the list of its cell. The key is the count of injected NOPs, the CPU and the buffer size. |
| 140 | `    for f in sorted(glob.glob(os.path.join(folder, 'nc.*.out'))):     # part NC: injected NOPs with counters` | Part NC: starts a loop over the files that fit `nc.*.out`. Comment: part NC is the part with injected NOPs and counters. |
| 141 | `        _, s, nn, cpu, size, rep = os.path.basename(f)[:-4].split('.')` | Splits the file name. The six pieces are the letters `nc`, the name of the event set, the count of injected NOPs, the CPU, the buffer size and the number of the process. |
| 142 | `        p = parse_out(f)` | `p`: the rates of the process. |
| 143 | `        if p is None:` | When the file holds no result, |
| 144 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 145 | `            continue` | and the loop goes to the next file. |
| 146 | `        if p['nops'] != int(nn):` | Check: the count of injected NOPs that the binary reports equals the count in the file name. |
| 147 | `            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')` | When they differ, a text goes to the problems. |
| 148 | `        cnt, bad = parse_counters(f[:-4] + '.d', p, names)` | Reads the counter files of the process with `parse_counters`. The counter folder has the name of the output file with `.d` in place of `.out`. `cnt` holds the counts per line and `bad` the failed checks. |
| 149 | `        res['problems'] += [f'{os.path.basename(f)}: {b}' for b in bad]` | Adds each failed check to the problems, with the file name before it. |
| 150 | `        cell = res['nops_counted'].setdefault(f'{nn}.{cpu}.{size}', {'rate': [], 'ev': {}})` | `cell`: the entry of this cell in `nops_counted`. The key is the count of injected NOPs, the CPU and the buffer size. A new cell starts with an empty list `rate` and an empty dictionary `ev`. |
| 151 | `        cell['rate'].append(p['total'])` | Appends the total rate of the process to `rate`. So `rate` holds the processes of all event sets of the cell. |
| 152 | `        for name, v in cnt.get(int(cpu), {}).items():` | Starts a loop over the counts per line of the thread on the CPU of the file name. |
| 153 | `            cell['ev'].setdefault(name, []).append(v)` | Appends each value to the list of its event in `ev`. An event gets one value from each process that counted it. The cell does not keep the name of the event set. |
| 154 | `    for f in sorted(glob.glob(os.path.join(folder, 'c.*.out'))):` | Part C, the runs with counters and without injected NOPs: starts a loop over the files that fit `c.*.out`. |
| 155 | `        _, s, cpu, size, rep = os.path.basename(f)[:-4].split('.')` | Splits the file name. The five pieces are the letter `c`, the name of the event set, the CPU, the buffer size and the number of the process. |
| 156 | `        p = parse_out(f)` | `p`: the rates of the process. |
| 157 | `        if p is None:` | When the file holds no result, |
| 158 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 159 | `            continue` | and the loop goes to the next file. |
| 160 | `        cnt, bad = parse_counters(f[:-4] + '.d', p, names)` | Reads the counter files of the process with `parse_counters`, as in line 148. |
| 161 | `        res['problems'] += [f'{os.path.basename(f)}: {b}' for b in bad]` | Adds each failed check to the problems, with the file name before it. |
| 162 | `        cell = res['counted'].setdefault(f'{cpu}.{size}', {'rate': [], 'ev': {}})` | `cell`: the entry of this cell in `counted`. The key is the CPU and the buffer size. |
| 163 | `        cell['rate'].append(p['total'])` | Appends the total rate of the process to `rate`. |
| 164 | `        for name, v in cnt.get(int(cpu), {}).items():` | Starts a loop over the counts per line of the thread on the CPU of the file name. |
| 165 | `            cell['ev'].setdefault(name, []).append(v)` | Appends each value to the list of its event. By the file `events.txt` of the folder `crb`, every event set holds `cpu_cycles`. So this event gets a value from every process of the cell. Each other event gets values from the processes of its own set only. |
| 166 | `    return res` | Returns the result of the folder. |

### Function `mesh_split`: sums and ranges per mesh for one process (lines 169 to 179)

| Line | Source | Explanation |
|---:|---|---|
| 169 | `def mesh_split(proc):` | Starts the function `mesh_split`. It turns the result of one many-core process into sums and ranges per mesh. |
| 170 | `    m0 = [t['gbps'] for c, t in proc['threads'].items() if c in MESH0]` | `m0`: the rates in GB/s of the threads on the CPUs 0 to 63, which is mesh 0. |
| 171 | `    m1 = [t['gbps'] for c, t in proc['threads'].items() if c not in MESH0]` | `m1`: the rates of the threads on all other CPUs, which is mesh 1. |
| 172 | `    return {'total': proc['total'], 'mesh0': sum(m0), 'mesh1': sum(m1), 'n0': len(m0), 'n1': len(m1),` | Returns the summary. `total`: the total that the binary printed, in GB/s. `mesh0`, `mesh1`: the sum of the thread rates of each mesh. `n0`, `n1`: the number of threads of each mesh. The dictionary goes on in lines 173 to 177. |
| 173 | `            'thr0': [min(m0), med(m0), max(m0)] if m0 else None, 'thr1': [min(m1), med(m1), max(m1)] if m1 else None,` | Continues line 172. `thr0`, `thr1`: the smallest, the median and the largest thread rate of each mesh, or `None` for a mesh without a thread. |
| 174 | `            'sec': [min(t['sec'] for t in proc['threads'].values()), max(t['sec'] for t in proc['threads'].values())],` | Continues line 172. `sec`: the shortest and the longest measured time of a thread of the process, in seconds. |
| 175 | `            # lower bound of the simultaneous rate: all bytes of the process over the time of its slowest thread` | Comment: the next value is a lower bound of the rate that all threads reach at the same time. It is all bytes of the process divided by the time of its slowest thread. |
| 176 | `            'floor': sum(t['lines'] for t in proc['threads'].values()) * LINE / max(t['sec'] for t in proc['threads'].values()) / 1e9,` | Continues line 172. `floor`: the lines of all threads times 64 bytes, divided by the longest measured time of a thread and by 1e9. So it is in GB/s. It divides the bytes of all threads by one common time. The total of ASCT adds rates, and each of them divides the bytes of one thread by the time of that thread. |
| 177 | `            'reps': proc['reps']}` | Ends the summary. `reps`: the repetition count that the binary printed for the process. |

### Function `do_chip`: one result folder of the many-core runs (lines 180 to 221)

| Line | Source | Explanation |
|---:|---|---|
| 180 | `def do_chip(folder):` | Starts the function `do_chip`. It reads one result folder of the script `run_chip.sh`, which holds the many-core runs. |
| 181 | `    names, sets = load_codes(folder)` | Reads the event names of the folder with `load_codes`. |
| 182 | `    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'runs': {}, 'counted': {}, 'mix': {}, 'problems': []}` | `res`: the result for this folder. `runs`: the read processes without counters, per cell. `counted`: the processes with counters. `mix`: the processes that mix reads and writes. `problems`: the texts of all failed checks. |
| 183 | `    for f in sorted(glob.glob(os.path.join(folder, 'w.*.out'))):` | Starts a loop over the files that fit `w.*.out`, the read processes without counters. |
| 184 | `        m = re.match(r'w\.(\d+)\.n(\d+)\.d([0-9.]+)\.(\d+)\.out', os.path.basename(f))` | Pattern for the file name: `w.`, the layout, `.n`, the count of injected NOPs, `.d`, the length of the measured phase in seconds, a dot, the number of the process and `.out`. The four groups hold the layout (as in `6456`), the count of injected NOPs, the length (digits and dots, as in `0.25`) and the number of the process. A file name that does not fit stops the script with an error in line 189. |
| 185 | `        p = parse_out(f)` | `p`: the rates of the process, from `parse_out`. |
| 186 | `        if p is None:` | When the file holds no result, |
| 187 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 188 | `            continue` | and the loop goes to the next file. |
| 189 | `        if p['nops'] != int(m.group(2)):` | Check: the count of injected NOPs that the binary reports equals the count in the file name. |
| 190 | `            res['problems'].append(f'{os.path.basename(f)}: the binary reports {p["nops"]} NOPs')` | When they differ, a text goes to the problems. |
| 191 | `        if len(p['threads']) != {'6456': 120, '6400': 64, '0056': 56, '5656': 112}.get(m.group(1), len(p['threads'])):` | Check: the number of threads with a result line fits the layout. The expected numbers are 120 for `6456`, 64 for `6400`, 56 for `0056` and 112 for `5656`. For any other layout the expected number is the number found, so the check passes. |
| 192 | `            res['problems'].append(f'{os.path.basename(f)}: {len(p["threads"])} threads reported')` | When the numbers differ, a text with the file name and the number of threads goes to the problems. The process is kept. |
| 193 | `        res['runs'].setdefault(f'{m.group(1)}.n{m.group(2)}.d{m.group(3)}', []).append(mesh_split(p))` | Appends the summary of the process (`mesh_split`) to the list of its cell. The key is the layout, the count of injected NOPs and the length, as in `6456.n0.d2`. |
| 194 | `    for f in sorted(glob.glob(os.path.join(folder, 'x.*.out'))):      # step MIX: read-write traffic types` | Starts a loop over the files that fit `x.*.out`. Comment: they belong to the step MIX, the traffic types that mix reads and writes. |
| 195 | `        m = re.match(r'x\.(\d+)\.t(\d)\.d([0-9.]+)\.(\d+)\.out', os.path.basename(f))` | Pattern for the file name: `x.`, the layout, `.t`, one digit, `.d`, the length of the measured phase, a dot, the number of the process and `.out`. Group 2 holds the digit, which is the traffic type. |
| 196 | `        p = parse_out(f)` | `p`: the rates of the process. |
| 197 | `        if p is None:` | When the file holds no result, |
| 198 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 199 | `            continue` | and the loop goes to the next file. |
| 200 | `        res['mix'].setdefault(m.group(2), []).append(p['total'])` | Appends the total of the process, in GB/s, to the list of its traffic type. The layout and the length are not part of the key. |
| 201 | `    for f in sorted(glob.glob(os.path.join(folder, 'c.*.out'))):` | Starts a loop over the files that fit `c.*.out`, the processes with counters. |
| 202 | `        m = re.match(r'c\.(\w+)\.(\d+)\.n(\d+)\.out', os.path.basename(f))` | Pattern for the file name: `c.`, the name of the event set, a dot, the layout, `.n`, the count of injected NOPs and `.out`. The three groups hold the set, the layout and the count of injected NOPs. |
| 203 | `        p = parse_out(f)` | `p`: the rates of the process. |
| 204 | `        if p is None:` | When the file holds no result, |
| 205 | `            res['problems'].append(f'no result in {os.path.basename(f)}')` | the text `no result in` with the file name goes to the problems, |
| 206 | `            continue` | and the loop goes to the next file. |
| 207 | `        cnt, bad = parse_counters(f[:-4] + '.d', p, names)` | Reads the counter files of the process with `parse_counters`. The folder has the name of the output file with `.d` in place of `.out`. |
| 208 | `        if bad:` | When a check of a counter row failed, |
| 209 | `            res['problems'].append(f'{os.path.basename(f)}: {len(bad)} counter rows fail a check, first: {bad[0]}')` | one text goes to the problems: the file name, the number of entries of `bad` and the first entry. The text calls this number `counter rows`. It is a number of failed checks: a counter row that fails both checks counts twice, and a counter file that fits no thread counts once. |
| 210 | `        cell = res['counted'].setdefault(f'{m.group(2)}.n{m.group(3)}', {'sets': {}, 'ev': {}})` | `cell`: the entry of this case in `counted`. The key is the layout and the count of injected NOPs, as in `6456.n0`. A new cell starts with two empty dictionaries, `sets` and `ev`. |
| 211 | `        cell['sets'][m.group(1)] = mesh_split(p)` | Stores the rate summary of this process (`mesh_split`) under the name of its event set. |
| 212 | `        evnames = sorted({n for row in cnt.values() for n in row})` | `evnames`: the sorted names of all events that a thread of this process counted. |
| 213 | `        for name in evnames:` | Starts a loop over these events. |
| 214 | `            v0 = [row[name] for c, row in cnt.items() if c in MESH0 and name in row]` | `v0`: the counts per line of the event for the threads on mesh 0. |
| 215 | `            v1 = [row[name] for c, row in cnt.items() if c not in MESH0 and name in row]` | `v1`: the same for the threads on mesh 1. |
| 216 | `            cell['ev'].setdefault(name, {})[m.group(1)] = {` | Stores the result for this event under the name of the event set. The dictionary goes on in lines 217 to 218. |
| 217 | `                'mesh0': [min(v0), med(v0), max(v0)] if v0 else None,` | `mesh0`: the smallest, the median and the largest count per line over the threads of mesh 0, or `None` when no thread of mesh 0 has a value. |
| 218 | `                'mesh1': [min(v1), med(v1), max(v1)] if v1 else None, 'threads': len(v0) + len(v1)}` | `mesh1`: the same for mesh 1. `threads`: the number of threads that have a value. |
| 219 | `    return res` | Returns the result of the folder. |

### Function `do_mesh`: one result folder of the mesh-counter runs (lines 222 to 280)

| Line | Source | Explanation |
|---:|---|---|
| 222 | `def do_mesh(folder):` | Starts the function `do_mesh`. It reads one result folder of the script `run_mesh.sh`, the runs with mesh counters. By the decisions file these runs did not happen [Ref3]. |
| 223 | `    res = {'folder': os.path.basename(folder), 'launches': launches(folder), 'tags': {}, 'problems': [], 'order': []}` | `res`: the result for this folder. `tags`: the values per tag. `problems`: the texts of all failed checks. `order`: the tags in the order of `launches.txt`. |
| 224 | `    spec = {}` | `spec`: the settings of each tag. It starts empty. |
| 225 | `    for line in open(os.path.join(folder, 'launches.txt')):` | First pass over `launches.txt`. The file must exist here. A missing file stops the script with an error. |
| 226 | `        m = re.match(r'launch (\S+) .* layout (\S+) bytes (\d+) nops (\d+) duration (\S+)', line)` | Pattern for a `launch` line of `run_mesh.sh`. It matches `launch `, the tag, any text, ` layout `, a word, ` bytes `, a number, ` nops `, a number, ` duration ` and a word. The five groups hold the tag, the layout, the buffer size in bytes, the count of injected NOPs and the length of the measured phase in seconds. |
| 227 | `        if m:` | When the line fits: |
| 228 | `            spec[m.group(1)] = {'layout': m.group(2), 'bytes': int(m.group(3)), 'nops': int(m.group(4)), 'duration': m.group(5)}` | stores the four settings under the tag. The length stays text. |
| 229 | `            res['order'].append(m.group(1))` | Appends the tag to `order`. |
| 230 | `    # every counting window must lie inside the measured phase of its process: the phase ends at the 'rc' line` | Comment: every counting window must lie inside the measured phase of its process. The code takes the time of the `rc` line as the end of the phase. |
| 231 | `    # and lasts as long as the slowest thread reports` | Comment, continued: the phase lasts as long as the slowest thread reports. |
| 232 | `    t_launch, t_rc, wins = {}, {}, {}` | `t_launch`: the start time of each tag. `t_rc`: the time of its `rc` line. `wins`: the start and the end of each counting window, per tag and event set. All three start empty. |
| 233 | `    for line in open(os.path.join(folder, 'launches.txt')):` | Second pass over `launches.txt`. |
| 234 | `        m = re.match(r'launch (\S+) epoch ([0-9.]+)', line)` | Pattern: `launch `, the tag, ` epoch ` and a time in seconds, counted from the start of the year 1970. The two groups hold the tag and the time. |
| 235 | `        if m:` | When the line fits: |
| 236 | `            t_launch[m.group(1)] = float(m.group(2))` | stores the start time under the tag. |
| 237 | `        m = re.match(r'rc -?\d+ (\S+) epoch ([0-9.]+)', line)` | Pattern: `rc `, an exit status, a space, the tag, ` epoch ` and a time. The two groups hold the tag and the time. The script `run_mesh.sh` reads this time after the process has ended. |
| 238 | `        if m:` | When the line fits: |
| 239 | `            t_rc[m.group(1)] = float(m.group(2))` | stores the time under the tag. |
| 240 | `        m = re.match(r'win (\S+) (\S+) (start\|end) ([0-9.]+)', line)` | Pattern for a window line: `win `, the tag, the name of the event set, the word `start` or `end`, and a time. The four groups hold these four values. |
| 241 | `        if m:` | When the line fits: |
| 242 | `            wins.setdefault(m.group(1), {}).setdefault(m.group(2), {})[m.group(3)] = float(m.group(4))` | stores the time under the tag, the set and the word. |
| 243 | `    for tag, sp in spec.items():` | Starts a loop over the tags and their settings. |
| 244 | `        rate = None` | `rate`: the total rate of the process of this tag. It stays `None` for the layout `idle`. |
| 245 | `        phase = None` | `phase`: the measured phase of the process. It starts as `None`. |
| 246 | `        if sp['layout'] != 'idle':` | For every layout other than `idle`. An `idle` tag has no process. |
| 247 | `            p = parse_out(os.path.join(folder, tag + '.out')) if os.path.exists(os.path.join(folder, tag + '.out')) else None` | `p`: the rates of the process, read by `parse_out` from the file with the name of the tag and the ending `.out`. It is `None` when the file does not exist. |
| 248 | `            if p is None:` | When there is no result, |
| 249 | `                res['problems'].append(f'no result for {tag}')` | the text `no result for` with the tag goes to the problems, |
| 250 | `                continue` | and the loop goes to the next tag. This tag gets no entry in `tags`. |
| 251 | `            rate = p['total']` | `rate`: the total that the binary printed, in GB/s. |
| 252 | `            if tag in t_rc:` | Only when the tag has an `rc` line with a time: |
| 253 | `                longest = max(t['sec'] for t in p['threads'].values())` | `longest`: the longest measured time of a thread, in seconds. |
| 254 | `                phase = {'start': t_rc[tag] - longest, 'end': t_rc[tag], 'startup': t_rc[tag] - longest - t_launch[tag]}` | `phase`: the measured phase as the code places it in time. `end`: the time of the `rc` line. `start`: the end minus `longest`. `startup`: the seconds from the `launch` line to that start. The process ended before the script read the time of the `rc` line. So the true phase ended a little earlier than `end`. |
| 255 | `                for sn, w in wins.get(tag, {}).items():` | Starts a loop over the counting windows of the tag. |
| 256 | `                    if 'end' not in w or w['start'] < phase['start'] or w['end'] > phase['end']:` | A window fails the check when it has no end time, when it starts before the phase, or when it ends after the phase. |
| 257 | `                        res['problems'].append(f'{tag} {sn}: window {w.get("start", 0) - phase["start"]:.1f} to '` | Then a text goes to the problems. It gives the tag, the set and the start of the window in seconds after the start of the phase. For a missing time the code uses 0. The text goes on in line 258. |
| 258 | `                                               f'{w.get("end", 0) - phase["start"]:.1f} s is not inside the measured phase of {longest:.1f} s')` | Continues line 257: the end of the window in seconds after the start of the phase, the words `is not inside the measured phase of` and the length of the phase in seconds. |
| 259 | `        res.setdefault('phase', {})[tag] = phase` | Stores the phase of the tag in `res` under the key `phase`. The value is `None` for an `idle` tag and for a tag without an `rc` time. |
| 260 | `        ev = {}` | `ev`: the counts of the tag by event name. It starts empty. |
| 261 | `        for f in sorted(glob.glob(os.path.join(folder, f'{tag}.*.perf'))):` | Starts a loop over the result files of `perf stat` for this tag. Their names are the tag, the name of the event set and the ending `.perf`. |
| 262 | `            sn = os.path.basename(f).split('.')[-2]` | `sn`: the name of the event set, which is the piece before the ending of the file name. |
| 263 | `            for line in open(f):` | Starts a loop over the lines of the file. |
| 264 | `                p = line.strip().split(',')` | `p`: the fields of the line, split at the commas. By the manual of `perf stat` the first five fields are the count, the unit, the event name, the time that the counter ran and the share of the measurement time in percent for which it ran [Ref5]. |
| 265 | `                if len(p) < 5 or line.startswith('#'):` | A line with fewer than 5 fields, and a line that starts with `#`, |
| 266 | `                    continue` | is skipped. |
| 267 | `                m = re.match(r'arm_cmn_(\d)/(.*)/', p[2])` | Pattern for the event name in field 3: `arm_cmn_`, one digit, a slash, a name and a slash. Group 1 holds the number of the mesh unit and group 2 the event name. |
| 268 | `                if not m or p[0].startswith('<'):` | Tests whether field 3 is no mesh event, or whether field 1 starts with the character `<`. The code treats a first field of that form as a text in place of a count. |
| 269 | `                    if m:` | When the line is a mesh event without a count, |
| 270 | `                        res['problems'].append(f'{tag} {sn} {p[2]}: {p[0]}')` | a text with the tag, the set, the event and the first field goes to the problems. |
| 271 | `                    continue` | In both cases the loop goes to the next line. |
| 272 | `                mesh, name = int(m.group(1)), m.group(2)` | `mesh`: the number of the mesh unit, 0 or 1. `name`: the event name. |
| 273 | `                cnt, sec, pct = float(p[0]), float(p[3]) / 1e9, float(p[4])` | `cnt`: the count. `sec`: the time that the counter ran, divided by 1e9. So the code reads this field as ns and keeps seconds. `pct`: the share of the measurement time in percent for which the counter ran. |
| 274 | `                if pct < 99.9:` | Check: the counter ran for at least 99.9 % of the window. |
| 275 | `                    res['problems'].append(f'{tag} {sn} {name} mesh {mesh}: counted {pct} % of the window')` | When it did not, a text goes to the problems. The value is kept. |
| 276 | `                ev.setdefault(name, {})[f'mesh{mesh}'] = {'count': cnt, 'sec': sec, 'per_s': cnt / sec, 'set': sn}` | Stores the event under its name and its mesh: the count, the seconds, the count per second and the name of the set. |
| 277 | `        res['tags'][tag] = {'spec': sp, 'rate': rate, 'ev': ev}` | Stores the settings, the rate and the events of the tag in `tags`. |
| 278 | `    return res` | Returns the result of the folder. |

### Function `main`: all folders, the output file and the console report (lines 281 to 306)

| Line | Source | Explanation |
|---:|---|---|
| 281 | `def main():` | Starts the function `main`. |
| 282 | `    out = {'single': [], 'chip': [], 'mesh': [], 'prep': []}` | `out`: the content of the output file. It has one list for each kind of folder. |
| 283 | `    for folder in sys.argv[2:]:` | Starts a loop over the folders, which are argument 2 and all later arguments. |
| 284 | `        b = os.path.basename(folder.rstrip('/'))` | `b`: the last part of the folder path. A slash at the end of the path is removed first. |
| 285 | `        if b.startswith('asct-single-'):` | A folder whose name starts with `asct-single-` |
| 286 | `            out['single'].append(do_single(folder))` | is read by `do_single`. The result goes to the list `single`. |
| 287 | `        elif b.startswith('asct-chip-'):` | A folder whose name starts with `asct-chip-` |
| 288 | `            out['chip'].append(do_chip(folder))` | is read by `do_chip`. The result goes to the list `chip`. |
| 289 | `        elif b.startswith('asct-mesh-'):` | A folder whose name starts with `asct-mesh-` |
| 290 | `            out['mesh'].append(do_mesh(folder))` | is read by `do_mesh`. The result goes to the list `mesh`. |
| 291 | `        elif b.startswith('asct-prep-'):` | A folder whose name starts with `asct-prep-` is the folder of the preparation script `prep.sh`. |
| 292 | `            out['prep'].append({'folder': b, 'env': open(os.path.join(folder, 'env.txt')).read(),` | For it the list `prep` gets the folder name and the whole text of `env.txt`, the machine record. |
| 293 | `                                'sha': open(os.path.join(folder, 'sha.txt')).read(),` | Continues line 292: the whole text of `sha.txt`, the list of the checksums. |
| 294 | `                                'resolve': open(os.path.join(folder, 'resolve.txt')).read()})` | Continues line 292: the whole text of `resolve.txt`, the list of the events with their raw codes. The script computes no number from these three files. |
| 295 | `        else:` | Any other folder name |
| 296 | `            sys.exit(f'unknown folder kind: {b}')` | ends the script with the message `unknown folder kind` and the name. `sys.exit` with a text prints the text to the error output and gives exit status 1. No output file is written in this case. |
| 297 | `    json.dump(out, open(sys.argv[1], 'w'), indent=1)` | Writes `out` as JSON to the file of argument 1. `indent=1` puts each value on its own line, with 1 space per level. |
| 298 | `    for kind in ('single', 'chip', 'mesh'):` | Starts the console report: a loop over the three kinds of run folders. |
| 299 | `        for r in out[kind]:` | Starts a loop over the folders of one kind. |
| 300 | `            print(kind, r['folder'], 'launches', r['launches'], 'problems', len(r['problems']))` | Prints one line per folder: the kind, the folder name, the summary of `launches.txt` and the number of problems. |
| 301 | `            for p in r['problems'][:8]:` | Starts a loop over the first 8 problems of the folder. |
| 302 | `                print('   ', p)` | Prints each of them after 4 spaces. |
| 305 | `if __name__ == '__main__':` | Runs the next line only when the file is started as a script, not when another file loads it. |
| 306 | `    main()` | Calls `main`. |

## References

- [Ref1] The output file `u.2.8388608.1.out` in the result folder `asct-single-20261116T231240Z` of the test folder `2026-11-16-asct-cross-check`: the settings line of the thread with `buflen`, `inner_nops` and `tid`, the result line with `repetitions`, `tickdiff` and `time`, and the lines `Total Bandwidth (MB/sec)` and `Bandwidth Repetitions`. In this file 1702 repetitions of a buffer of 8388608 bytes in 0.249577 s give 57.2 GB/s, and the printed total is 57206.53 MB/sec.
- [Ref2] `launches.txt` in the result folders `asct-single-20261116T231240Z` and `asct-chip-20261116T231956Z` of the same test folder: the `launch` lines and the `rc` lines.
- [Ref3] `DECISIONS.md` in the folder `asct-2026-11-16`: the sections "How ASCT is used, and why not through `asct run`" (at most 6 events plus `cpu_cycles` per set), "Readings fixed now", "Added 2026-11-16 23:37 UTC" (the lower bound of a total) and "Record of 2026-11-16 23:50 UTC" (the mesh-counter runs did not happen).
- [Ref4] external source: Linux manual page `perf_event_open(2)`, the fields `time_enabled` and `time_running` and the text on multiplexing.
- [Ref5] external source: Linux manual page perf-stat(1), section "CSV FORMAT".
- [Ref6] `asct.json` in the folder `asct-2026-11-16`: the lists `single` (2 folders), `chip` (2 folders), `prep` (1 folder) and `mesh` (no entry).
