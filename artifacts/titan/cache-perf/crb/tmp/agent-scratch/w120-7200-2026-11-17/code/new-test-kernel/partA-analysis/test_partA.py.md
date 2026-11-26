# `test_partA.py` explained, line by line

- Source file: `new-test-kernel/partA-analysis/test_partA.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 435 lines, 29734 bytes).
- sha256 of the source when this page was built: `4f576fb79bada7e7f556eb8906659b0cfd3586903f3883983bda39c8f8e33eee`.

## Short version: purpose

`test_partA.py` tests the analysis script `analyze_partA.py` and the page generator `make_partA_html.py` without any measurement. It builds invented result folders in the format of the run script, runs both scripts on them, and checks the computed values and the text of the pages. The tests fix the choices of the analysis: which blocks are used, when the labels are used, and that missing data is reported as missing.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan and how to analyse Part A.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. B7 and B8 are steps of the later Part B, and Part C is the part with counters.
- **Run script**: the script `run_partA.sh`. It starts the processes of Part A on the test machine and writes the result folders.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Data set 1, data set 2**: the two sets of invented result folders of this file. Set 1 has clear patterns. Set 2 has patterns between the limits.
- **Summary, json file**: the result of the analysis script, one dictionary. It is stored as the file `partA-summary.json`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of the binary `bw_old`. `read_new` and `write_new` are the C kernels of the binary `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`.
- **Launch, tag**: a launch is one start of a process by the run script. The tag is the short name of the launch, for example `read_old-r1`.
- **Block**: the lines of one process in a csv file: the header line of the run script and the output of the benchmark.
- **Header line**: the line that the run script writes before the output of a process. It starts with `-- step`.
- **Data line**: an output line of the benchmark for one repetition, with 10 fields.
- **Thread line**: an output line of the benchmark for one thread and one repetition, printed with `--per-thread`.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither.
- **Fastest half**: the half of the threads of one repetition that has the highest rates.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that the analysis script had to fix where the plan and the handoff note give none.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **PMU**: performance monitoring unit, the counter hardware of a core. Linux shows it as a counter device with a type number.
- **SVE**: the scalable vector instruction set of Arm.
- **`assert`**: the Python statement of a test. It stops the program with an error when its condition is false.

## Main flow

1. Helpers for invented data (lines 27 to 144): CPU lists, rate functions for a split and for a uniform distribution, the class `Folder` that writes one result folder with its blocks, and `long_steps` that writes the steps A1 to A4.
2. `build_set1` builds data set 1 in three folders: a split and a uniform kernel, a killed launch that a later folder repeats, a skipped step A3, a level change in one A5 process, and a second A5 process that waited (lines 147 to 179).
3. `build_set2` builds data set 2 in one folder: distributions between the limits, step A3 present, a failed A5 process, no A6 and no A7 (lines 182 to 193).
4. `check_set1` tests the json values of set 1: missing steps, the choice of the blocks, passes, mesh values, q, fastest half, percentile, labels, brackets of A4, level changes of A5, A6 and the load (lines 200 to 275).
5. `check_set2` tests the json values of set 2: labels not used, the rows of A3 that are left out, no bracket, the passes of copy rows, and the failed process (lines 278 to 311).
6. `check_two_groups` and `check_units` test single functions on small inputs: the test of the two groups, the number format, the check of the level limits and the reading of the event codes (lines 314 to 348).
7. `check_set1_more` and `check_set2_more` test json values together with the text of the page (lines 351 to 389).
8. `check_page` tests rules that every page must meet: no forbidden word, no outside file, a short version of at most 3 sentences, and `Insufficient data` for every missing step (lines 392 to 403).
9. `main` runs all of this in order: the single functions, then set 1, then set 2, then one empty folder (lines 406 to 431).

## Behavior a reader must know

- The file needs no test machine and no result folder. Every rate in its data is invented, and each test page carries a banner that says so.
- The file is started as a program. `main` calls the check functions one after the other. The first failed `assert` ends the program with an error. The line `all tests passed` is printed only when none failed.
- Without `--keep` the data is written to a new temporary folder, which is deleted at the end, also after a failed test (lines 429 to 431).
- With `--keep DIR` the folder `DIR` is first deleted with all its content and then created new (line 410). The files of the test stay there.
- The summary is tested after it was written to a json file and read back (lines 414 to 415). So the tests see the values as the page generator sees them.
- The header text says that two pages stay with `--keep`. The code keeps three: the page of the empty folder is written too (line 427).
- The comment of line 302 speaks of 60 and 120 passes for the copy rows. The generator and the tests use 40 passes, and 80 without the division by 2.
- The text of line 183 gives rough q values for set 2. The tests do not depend on these numbers.
- The two scripts are loaded from the folder of this file (lines 18 to 21). The test writes no compiled copy of them (line 16).

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partA-analysis/test_partA.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (435 lines, 29734 bytes, sha256 `4f576fb79bada7e7f556eb8906659b0cfd3586903f3883983bda39c8f8e33eee`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, imports and fixed texts (lines 1 to 26)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_partA.py [--keep DIR]` | Starts the header text of the file (a docstring, a text that Python keeps but does not run). This line is the usage: the only option is `--keep` with a folder. |
| 4 | `Builds synthetic Part A result folders in the format of run_partA.sh and bandwidth.c --per-thread,` | Header text: the file builds invented result folders of Part A. They have the format that the run script `run_partA.sh` and the benchmark with `--per-thread` write. |
| 5 | `runs analyze_partA.py and make_partA_html.py on them, and checks the computed values.` | Header text: it runs the analysis `analyze_partA.py` and the page generator `make_partA_html.py` on these folders and checks the computed values. |
| 6 | `All rates in these folders are invented. They are test input, not measurements.` | Header text: all rates in these folders are invented. They are test input, not measurements. |
| 8 | `Two data sets:` | Header text: the file uses two data sets. |
| 9 | `  set 1 "clean":  split and uniform thread distributions, a killed block that a later folder repeats,` | Header text: set 1, named clean, has split and uniform thread distributions, and a killed block that a later folder repeats. The list goes on in line 10. |
| 10 | `                  a skipped A3, a level change inside one A5 process, a second A5 process that waited.` | Continues the list of set 1: a skipped step A3, a level change inside one A5 process, and a second A5 process that waited. |
| 11 | `  set 2 "mixed":  thread distributions between the two limits, so that q does not fall into two groups.` | Header text: set 2, named mixed, has thread distributions between the two limits. So q does not fall into two groups. |
| 12 | `                  A3 is present. A6 is missing.` | Continues set 2: step A3 is present, and step A6 is missing. |
| 13 | `With --keep DIR the folders, the two json files and the two pages stay in DIR.` | Header text: with `--keep DIR` the folders, the two json files and the two pages stay in the folder `DIR`. The code also keeps a third page there (line 427). |
| 14 | `"""` | Ends the header text. |
| 15 | `import os, sys, json, shutil, tempfile, re` | Loads six modules of the Python standard library: `os` (paths and folders), `sys` (arguments), `json`, `shutil` (copy and delete of folders), `tempfile` (temporary folders) and `re` (regular expressions). |
| 16 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled copy of the modules that it loads. So the test leaves no `__pycache__` folder beside the two scripts. |
| 17 | `BANNER = 'SYNTHETIC TEST DATA. Every rate on this page is invented by test_partA.py. It is not a measurement.'` | `BANNER`: the notice that every test page carries at its top. It says that the page holds invented test data and no measurement. |
| 18 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the full path of the folder that holds this file. |
| 19 | `sys.path.insert(0, HERE)` | Puts that folder first in the list of places where Python looks for modules. |
| 20 | `import analyze_partA as A` | Loads the analysis script as the module `A`. The tests call its functions directly. |
| 21 | `import make_partA_html as H` | Loads the page generator as the module `H`. |
| 23 | `MIB = 1 << 20` | `MIB`: 1048576 bytes, written as 1 shifted left by 20 bits. |
| 24 | `HEAD = 'kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps'` | `HEAD`: the line with the ten column names that the benchmark prints before its data lines. |

### Generators for CPU lists and invented thread rates (lines 27 to 46)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `def cpulist(a, b):` | Starts the function `cpulist`. It gives the CPU numbers for `a` threads on mesh 0 and `b` threads on mesh 1. |
| 28 | `    return list(range(a)) + list(range(64, 64 + b))` | Returns the list of the CPUs 0 to `a-1` followed by the CPUs 64 to `64+b-1`. This is the placement rule of the run script. |
| 31 | `def cpustr(a, b):` | Starts the function `cpustr`. It gives the same CPUs as the text of the option `--cpus`. |
| 32 | `    return ','.join(x for x in ([f'0-{a-1}'] if a else []) + ([f'64-{64+b-1}'] if b else []))` | Returns the range `0` to `a-1` when `a` is above 0, and the range `64` to `64+b-1` when `b` is above 0, joined with a comma. Example: `cpustr(64, 56)` gives `0-63,64-119`. |
| 35 | `def jit(i, amp):` | Starts the function `jit`. It gives a small fixed deviation for thread number `i`. With it the invented rates are not all equal. |
| 36 | `    return ((i * 37) % 11 - 5) * amp / 5.0` | Returns one of 11 values from `-amp` to `+amp`, in steps of one fifth of `amp`. The value depends only on `i`, so every run of the test builds the same data. |
| 39 | `def split(m0, m1, amp=0.0):` | Starts the function `split`. It builds a rate function for a split distribution of the threads. |
| 40 | `    return lambda i, cpu, rep: (m0 if cpu < 64 else m1) + jit(i + rep, amp)` | Returns a function of the thread index, the CPU and the repetition. It gives the rate `m0` to a thread on a CPU below 64 and the rate `m1` to every other thread, plus the deviation of `jit`. |
| 43 | `def flat(v, amp=0.0):` | Starts the function `flat`. It builds a rate function for a uniform distribution. |
| 44 | `    return lambda i, cpu, rep: v + jit(i + rep, amp)` | Returns a function that gives every thread the rate `v` plus the deviation of `jit`. |

### Class `Folder`: one invented result folder (lines 47 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 47 | `class Folder:` | Starts the class `Folder`. One object stands for one invented result folder on disk. |
| 48 | `    def __init__(self, root, name, steps, skipped_a3=False, a7=False):` | Starts the set-up of a folder. `root` is the folder above it, `name` its name and `steps` the step list for `env.txt`. `skipped_a3` adds the line of a skipped step A3. `a7` adds the files of step A7. |
| 49 | `        self.d = os.path.join(root, name); os.makedirs(self.d)` | `self.d`: the path of the folder. `os.makedirs` creates it. |
| 50 | `        self.n = 0` | `self.n`: the number of launches written so far. It gives each launch its own invented time. |
| 51 | `        with open(os.path.join(self.d, 'env.txt'), 'w') as f:` | Opens the new file `env.txt` for writing. |
| 52 | `            f.write(f'## host=ubuntu utc=2026-01-01T00:00:00Z loadavg=0.08 0.10 0.09 1/1400 5321 logins=1 steps={steps}\n'` | Writes the first line of `env.txt` in the format of the run script: host `ubuntu`, a fixed time, a quiet load, 1 login and the step list. |
| 53 | `                    '## thp=[always] madvise never defrag=always defer defer+madvise [madvise] never\n'` | Writes the line with the two settings for transparent huge pages. |
| 54 | `                    '## uptime=1000.00 MemFree: 500000000 kB MemAvailable: 510000000 kB \n'` | Writes the line with the uptime and the memory values. |
| 55 | `                    '## busiest processes (pcpu user comm):\n%CPU USER     COMMAND\n 0.3 root     kworker\n 0.1 jhan     sshd\n'` | Writes the title line and the list of the busiest processes, with two processes. The list holds no process `ps`. So the analysis cannot find the account of the run script in set 1. |
| 56 | `                    '## sha256:\naaaa  bw_old\nbbbb  bw_new\ncccc  run_partA.sh\n## vmstat thp:\nthp_fault_alloc 10\n')` | Writes the lines with invented checksums and the title line and one counter of the huge page counters. |
| 57 | `            if skipped_a3:` | Only for a folder with a skipped step A3. |
| 58 | `                f.write('A3 skipped: MemAvailable is 61 GiB, below 70 GiB\n')` | Writes the line that the run script writes when it skips step A3: 61 GiB available, below 70 GiB. |
| 59 | `            f.write('## end utc=2026-01-01T00:30:00Z loadavg=30.10 20.00 9.00 1/1400 9999\n')` | Writes the end line, with a load average over 1 minute of 30.10. |
| 60 | `        open(os.path.join(self.d, 'stderr.txt'), 'w').close()` | Creates an empty file `stderr.txt`. |
| 61 | `        if a7:` | Only for a folder with the files of step A7. |
| 62 | `            open(os.path.join(self.d, 'A7-sve.txt'), 'w').write('## sve_default_vector_length (bytes):\n16\n')` | Writes `A7-sve.txt` with the title line and the value 16. |
| 63 | `            open(os.path.join(self.d, 'A7-perf-list.txt'), 'w').write('  cycles\n  instructions\n')` | Writes `A7-perf-list.txt` with two event names. |
| 64 | `            open(os.path.join(self.d, 'A7-pmu-devices.txt'), 'w').write('armv8_pmuv3_0\n')` | Writes `A7-pmu-devices.txt` with one device name. |
| 65 | `            open(os.path.join(self.d, 'A7-core-events.txt'), 'w').write('== /sys/bus/event_source/devices/armv8_pmuv3_0 type=10\n/sys/x/events/l1d_cache_refill:event=0x03\n')` | Writes `A7-core-events.txt` with one PMU line of the type 10 and one event line, for `l1d_cache_refill` with the code `0x03`. So only one of the five events of the handoff note has a code. |
| 67 | `    def block(self, step, tag, binary, cpus, nbytes, min_ms, kernels, reps, fn, passes, args, waited=0, load='0.50 0.40 0.30 1/1400',` | Starts the method `block`. It appends one process block to the csv file of a step, and the matching entry to `launches.txt`. The arguments name the step, the tag, the binary, the CPUs, the buffer size in bytes, the interval length in ms, the kernels and the number of repetitions. `fn` gives the rate function of a kernel, and `passes` gives the passes per thread of a kernel and repetition. `args` is the options text. `waited` and `load` go into the header line. |
| 68 | `              thp='madvise', kill_after=None, fail=False, foreign=None):` | Continues the arguments: `thp` is the page setting that the block prints. `kill_after` cuts the block as a kill does. `fail` makes a failed block. `foreign` replaces the list of the busiest processes. |
| 69 | `        """kernels: list of kernel names. fn(kernel) -> f(i, cpu, rep) -> rate. passes(kernel, rep) -> passes per thread."""` | Text of the method: the meaning of `kernels`, `fn` and `passes`. |
| 70 | `        self.n += 1` | Counts the launch. |
| 71 | `        utc = f'00:{self.n // 60:02d}:{self.n % 60:02d}'` | `utc`: an invented time of the launch: one second per launch, from 00:00:01 on. |
| 72 | `        with open(os.path.join(self.d, 'launches.txt'), 'a') as f:` | Opens `launches.txt` of the folder for appending. |
| 73 | `            f.write(f'== {step}.csv {tag} utc {utc} loadavg {load} logins 1\n%CPU USER     COMMAND\n')` | Writes the first line of the launch in the format of the run script, and the title line of `ps`. |
| 74 | `            f.write(foreign or ' 0.3 root     kworker/3:1\n 0.2 root     systemd\n 0.1 jhan     sshd\n 0.0 root     rcu_sched\n 0.0 root     ksoftirqd\n')` | Writes five process lines: the list `foreign` when one is given, and five quiet system processes in every other case. |
| 75 | `        out = [f'-- step {step} tag {tag} binary {binary} waited_s {waited} loadavg {load} logins 1 utc {utc} args {args}',` | `out`: the lines of the block. The first is the header line in the format of the run script. |
| 76 | `               f'# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; '` | Continues `out`: the comment line of the benchmark, which starts with `# bandwidth:`. |
| 77 | `               f'threads={len(cpus)} bytes_per_thread={nbytes} min_ms={min_ms} thp={thp}', HEAD]` | Continues the comment line with the thread count, the buffer size, the interval length and the page setting. Then follows the line with the column names. |
| 78 | `        n = len(cpus)` | `n`: the number of threads. |
| 79 | `        for k in kernels:` | Loop over the kernels of the block. |
| 80 | `            f = fn(k); best = 0; lines = []` | `f`: the rate function of the kernel. `best`: the highest total so far. `lines`: the output lines of the kernel. |
| 81 | `            for rep in range(reps):` | Loop over the repetitions. |
| 82 | `                r = [round(f(i, c, rep), 2) for i, c in enumerate(cpus)]` | `r`: the invented thread rates of the repetition, rounded to 2 decimals as the benchmark prints them. |
| 83 | `                agg = round(sum(r) * (0.99 if n > 1 else 1), 2); best = max(best, agg)` | `agg`: the invented total. With more than one thread it is 99 % of the sum of the thread rates. With one thread it is the rate of the thread. |
| 84 | `                total = int(passes(k, rep) * n * nbytes * (2 if 'copy' in k else 1))` | `total`: the value for the column `total_bytes`: the wanted passes per thread times the threads times the buffer size, and twice that for a copy kernel. So the analysis must find exactly the wanted passes. |
| 85 | `                lines.append(f'{k},{n},{nbytes},{rep},{total},{min_ms/1000*1.1:.4f},{agg:.2f},{min(r):.2f},{max(r):.2f},{sum(r)/n:.2f}')` | Adds the data line: kernel, threads, buffer size, repetition, total bytes, an elapsed time of 1.1 times the interval length, the total, and the lowest, highest and mean thread rate. |
| 86 | `            lines.append(f'{k},{n},{nbytes},best,,,{best:.2f},,,')` | Adds the best line of the kernel. |
| 87 | `            if '--per-thread' in args:` | Only when the options hold `--per-thread`. |
| 88 | `                for i, c in enumerate(cpus):` | Loop over the threads. |
| 89 | `                    for rep in range(reps):` | Loop over the repetitions. |
| 90 | `                        lines.append(f'thread,{i},{c},{k},{rep},{f(i, c, rep):.2f}')` | Adds one thread line: the thread index, the CPU, the kernel, the repetition and the rate with 2 decimals. |
| 91 | `            out += lines` | Adds the lines of the kernel to the block. |
| 92 | `        if kill_after is not None:` | Only for a block that must look killed. |
| 93 | `            out = out[:kill_after] + [out[kill_after][:7], f'-- killed tag {tag} status 4 utc {utc}']      # one cut line, as after a kill` | Keeps the first `kill_after` lines of the block. Then it adds the first 7 characters of the next line, as a line that a kill cut short, and a `-- killed` line with the status 4. |
| 94 | `        if fail:` | Only for a block that must look failed. |
| 95 | `            out = out[:3] + [f'-- failed tag {tag} exit 1']` | Keeps the header line, the comment line and the column names, and adds a `-- failed` line with the exit status 1. |
| 96 | `        with open(os.path.join(self.d, f'{step}.csv'), 'a') as f:` | Opens the csv file of the step for appending. |
| 97 | `            f.write('\n'.join(out) + '\n')` | Writes the lines of the block. |

### Options text and kernel names (lines 100 to 110)

| Line | Source | Explanation |
|---:|---|---|
| 100 | `def all_args(a, b, kernel, reps, ms):` | Starts the function `all_args`. It gives the options text of a launch with `a+b` threads. |
| 101 | `    return f'--threads {a+b} --cpus {cpustr(a, b)} --bytes 256M --per-thread --kernel {kernel} --reps {reps} --min-ms {ms}'` | Returns the options in the form of the run script: the thread count, the CPU list, a buffer of 256 MiB, `--per-thread`, the kernel, the repetitions and the interval length. |
| 104 | `K6 = ['read_old', 'read_new', 'asmread', 'write_old', 'write_new', 'asmwrite']` | `K6`: the six kernel names of the tags, in the order of round 1. |
| 107 | `def ker(k): return {'read_old': 'read', 'read_new': 'read', 'write_old': 'write', 'write_new': 'write'}.get(k, k)` | Defines `ker`. It gives the kernel option for a kernel name: `read` or `write` for the four C kernels, and the name itself for the others. |
| 108 | `def binof(k): return 'bw_old' if k in ('read_old', 'write_old') else 'bw_new'` | Defines `binof`. It gives the binary: `bw_old` for `read_old` and `write_old`, and `bw_new` for the others. |

### Function `long_steps`: the steps A1, A2, A3 and A4 of one folder (lines 111 to 146)

| Line | Source | Explanation |
|---:|---|---|
| 111 | `def long_steps(F, rates, a2_kill=True, a3=None, a4=None, load2='31.20 12.00 5.00 2/1500'):` | Starts the function `long_steps`. It writes the blocks of the steps A1, A2 and A4, and of A3 when `a3` is given, into the folder `F`. `load2` is the load text of most launches: a load average over 1 minute of 31.20 with 2 runnable tasks. |
| 112 | `    """rates: kernel name -> rate function. Writes A1, A2, optionally A3, and A4 into folder F."""` | Text of the function: `rates` maps each kernel name to its rate function. |
| 113 | `    cp = cpulist(64, 56)` | `cp`: the CPUs of 64 threads on mesh 0 and 56 on mesh 1. |
| 114 | `    for rnd in (1, 2):` | Loop over the rounds 1 and 2 of step A1. |
| 115 | `        for k in (K6 if rnd == 1 else K6[::-1]):` | Loop over the six kernels, in the reversed order in round 2. |
| 116 | `            F.block('A1', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, 500, [ker(k)], 3, lambda _k, k=k: rates[k], lambda _k, rep: 5,` | Writes one block of step A1: 120 threads, 256 MiB, 500 ms, 3 repetitions, the rate function of the kernel, and 5 passes per thread in every repetition. So every repetition of A1 is below 50 passes. |
| 117 | `                    all_args(64, 56, ker(k), 3, 500), load='0.50 0.40 0.30 1/1400' if (rnd, k) == (1, 'read_old') else load2,` | Continues the call: the options text. The first launch of the step gets a quiet load. Every other launch gets `load2`. |
| 118 | `                    waited=0 if (rnd, k) == (1, 'read_old') else 4,` | Continues the call: the first launch waited 0 s, and every other launch waited 4 s. |
| 119 | `                    foreign=' 99.0 other    busy_job\n 0.3 root     kworker/3:1\n 0.2 root     systemd\n 0.1 jhan     sshd\n 0.0 root     rcu_sched\n' if (rnd, k) == (2, 'asmread') else None)` | Continues the call: the launch of `asmread` in round 2 gets a list of busiest processes with the process `busy_job` of the user `other` at 99.0 % of a CPU. |
| 120 | `    for rnd in (1, 2):` | Loop over the rounds 1 and 2 of step A2. |
| 121 | `        for k in (K6 if rnd == 1 else K6[::-1]):` | Loop over the six kernels, in the reversed order in round 2. |
| 122 | `            ms = 6000 if 'read' in k else 15000` | `ms`: 6000 for a kernel name that holds `read`, and 15000 for the others, as in the run script. |
| 123 | `            # round 2 runs in the reversed order, so read_old-r2 is the last launch of A2: it is the killed one` | Comment: round 2 runs in the reversed order. So `read_old-r2` is the last launch of A2, and it is the one that is killed. |
| 124 | `            if a2_kill and (rnd, k) == (2, 'read_old'):` | Only for that launch, and only when `a2_kill` is true. |
| 125 | `                F.block('A2', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, ms, [ker(k)], 3, lambda _k, k=k: rates[k], lambda _k, rep: 60,` | Writes its block with 60 passes per thread. The call goes on in line 126. |
| 126 | `                        all_args(64, 56, ker(k), 3, ms), load=load2, kill_after=5)` | Continues the call: `kill_after=5` cuts the block after 5 lines. So it holds 2 data lines, a cut line and the `-- killed` line. |
| 127 | `                continue` | Goes to the next kernel. The killed launch gets no second block here. |
| 128 | `            # read_new round 1 repetition 2 gets 48 passes: it must be marked` | Comment: repetition 2 of the new read kernel in round 1 gets 48 passes. The analysis must mark it. |
| 129 | `            F.block('A2', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, ms, [ker(k)], 3, lambda _k, k=k: rates[k],` | Writes the block of every other launch of A2. The call goes on in line 130. |
| 130 | `                    lambda _k, rep, k=k, rnd=rnd: 48 if (k, rnd, rep) == ('read_new', 1, 2) else 60, all_args(64, 56, ker(k), 3, ms), load=load2)` | Continues the call: 60 passes per thread, and 48 passes for the one repetition that the comment names. |
| 131 | `    if a3:` | Only when values for step A3 are given. |
| 132 | `        for ms in (500, 6000):` | Loop over the two interval lengths of A3. |
| 133 | `            for i in (1, 2, 3):` | Loop over the process numbers 1 to 3. |
| 134 | `                F.block('A3', f'onebuf-ms{ms}-{i}', 'bw_old', cp, 256 * MIB, ms, ['read'], 3, lambda _k: a3['one'], lambda _k, rep: 60,` | Writes a block with one buffer: the kernel `read` only, 3 repetitions, the rate function `a3['one']` and 60 passes per thread. |
| 135 | `                        all_args(64, 56, 'read', 3, ms), load=load2)` | Continues the call: the options text with `--kernel read`. |
| 136 | `                F.block('A3', f'twobuf-ms{ms}-{i}', 'bw_old', cp, 256 * MIB, ms, ['read', 'write', 'copy'], 3,` | Writes a block with two buffers: the kernels `read`, `write` and `copy`, 3 repetitions each. |
| 137 | `                        lambda k: a3['two'] if k == 'read' else flat(1.2, 0.02), lambda k, rep: 40 if k == 'copy' else 60, all_args(64, 56, 'all', 3, ms), load=load2)` | Continues the call: the read kernel gets the rate function `a3['two']`, and write and copy get a flat rate of 1.2 GB/s. Copy gets 40 passes per thread and the others 60. The options text holds `--kernel all`. |
| 138 | `    for a, b in ((64, 0), (64, 16), (64, 32), (64, 40), (64, 48), (64, 52), (64, 56), (32, 32), (40, 40), (48, 48), (56, 56)):` | Loop over the 11 thread counts of step A4. |
| 139 | `        for k in ('read_old', 'asmread'):` | Loop over the two kernels of A4. |
| 140 | `            F.block('A4', f'{k}-{a}+{b}', binof(k), cpulist(a, b), 256 * MIB, 6000, [ker(k)], 2, lambda _k, k=k, a=a, b=b: a4(k, a, b),` | Writes one block of step A4: the CPUs of the count, 6000 ms, 2 repetitions, and the rate function that `a4` gives for the kernel and the count. |
| 141 | `                    lambda _k, rep: 70, f'--threads {a+b} --cpus {cpustr(a, b)} --bytes 256M --per-thread --kernel {ker(k)} --reps 2 --min-ms 6000', load=load2)` | Continues the call: 70 passes per thread, and the options text of the launch. |
| 144 | `def a5_args(cpu): return f'--threads 1 --cpus {cpu} --bytes 8M --kernel asmread --reps 30 --min-ms 300'` | Defines `a5_args`. It gives the options text of an A5 launch: one thread on the given CPU, 8 MiB, `asmread`, 30 repetitions of at least 300 ms. |

### Function `build_set1`: data set 1, clean (lines 147 to 181)

| Line | Source | Explanation |
|---:|---|---|
| 147 | `def build_set1(root):` | Starts the function `build_set1`. It builds the three folders of data set 1 below `root`. |
| 148 | `    # folder 1: A7 A5 A6` | Comment: folder 1 holds the steps A7, A5 and A6. |
| 149 | `    F = Folder(root, 'partA-20260101T000000Z', 'A7 A5 A6', a7=True)` | `F`: folder 1, with the files of step A7. |
| 150 | `    one = lambda v: (lambda _k: (lambda i, cpu, rep: v(rep)))` | `one`: a helper that turns a function of the repetition number into a rate function for one thread. |
| 151 | `    F.block('A5', 'cpu2-proc1', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5 + 0.1 * (r % 3)), lambda k, r: 2500, a5_args(2))` | A5, process 1 on CPU 2: the rates run through 67.5, 67.6 and 67.7 GB/s. All 30 intervals are low. 2500 passes per thread. |
| 152 | `    F.block('A5', 'cpu2-proc2', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.6 + 0.1 * (r % 2)), lambda k, r: 2500, a5_args(2), waited=2)` | A5, process 2 on CPU 2: the rates are 67.6 and 67.7 GB/s in turn, all low. Its header line says that it waited 2 s. |
| 153 | `    # CPU 41: low for intervals 0-11, 69.8 (changing) at interval 12, high from interval 13` | Comment: on CPU 41 the first process is low in the intervals 0 to 11, has 69.8 GB/s (changing) in interval 12, and is high from interval 13 on. |
| 154 | `    F.block('A5', 'cpu41-proc1', 'bw_new', [41], 8 * MIB, 300, ['asmread'], 30,` | A5, process 1 on CPU 41. The call goes on in line 155. |
| 155 | `            one(lambda r: 67.9 if r < 12 else 69.8 if r == 12 else 71.2), lambda k, r: 2500, a5_args(41))` | Continues the call: 67.9 GB/s up to interval 11, 69.8 GB/s in interval 12, and 71.2 GB/s after it. |
| 156 | `    F.block('A5', 'cpu41-proc2', 'bw_new', [41], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 71.0 + 0.1 * (r % 2)), lambda k, r: 2500, a5_args(41))` | A5, process 2 on CPU 41: the rates are 71.0 and 71.1 GB/s in turn, all high. |
| 157 | `    for i in range(1, 9):` | Loop over the 8 pairs of step A6. |
| 158 | `        a = '--threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500'` | `a`: the options text of an A6 launch. |
| 159 | `        F.block('A6', f'thp-{i}', 'bw_new', [2], 8 * MIB, 500, ['asmread'], 3, one(lambda r, i=i: 67.0 + 0.1 * i + 0.05 * r), lambda k, r: 4000, a)` | A6 with huge pages allowed, pair `i`: the three rates are 67.0 plus 0.1 times `i`, then 0.05 and 0.10 GB/s more. So the process medians run from 67.15 to 67.85 GB/s. |
| 160 | `        F.block('A6', f'nothp-{i}', 'bw_new', [2], 8 * MIB, 500, ['asmread'], 3, one(lambda r, i=i: 52.0 + 0.1 * i + 0.05 * r), lambda k, r: 3000,` | A6 with `--no-thp`, pair `i`: the same pattern around 52 GB/s. The process medians run from 52.15 to 52.85 GB/s. |
| 161 | `                a + ' --no-thp', thp='nohugepage')` | Continues the call: the options text with `--no-thp`, and the printed page setting `nohugepage`. |
| 162 | `    # folder 2: A1 A2 A3 A4. A3 is skipped. The last A2 launch (read_old-r2) is killed.` | Comment: folder 2 holds the steps A1 to A4. Step A3 is skipped, and the last launch of A2 is killed. |
| 163 | `    rates = dict(read_old=split(5.0, 2.5), read_new=flat(2.4), asmread=flat(2.3, 0.05),` | `rates`: the rate functions of set 1. The old read kernel is split: 5.0 GB/s on mesh 0 and 2.5 GB/s on mesh 1, with no deviation. The new read kernel is flat at 2.4 GB/s. `asmread` is flat near 2.3 GB/s. |
| 164 | `                 write_old=split(1.5, 0.9, 0.02), write_new=flat(1.05, 0.02), asmwrite=split(1.5, 0.9, 0.02))` | Continues `rates`: the old write kernel and `asmwrite` are split, near 1.5 GB/s on mesh 0 and 0.9 GB/s on mesh 1. The new write kernel is flat near 1.05 GB/s. |
| 165 | `    def a4(k, a, b):` | Starts the inner function `a4`. It gives the rate function of step A4 for a kernel and a thread count. |
| 166 | `        if a != 64: return flat(3.4, 0.05)                    # a+a counts: uniform` | A count with fewer than 64 threads on mesh 0, that is a count of the series `a+a`, is flat near 3.4 GB/s. By the comment these counts are uniform. |
| 167 | `        lim = 48 if k == 'read_old' else 32                    # split up to this count of mesh-1 threads` | `lim`: the highest number of mesh 1 threads at which the kernel is still split: 48 for the old read kernel and 32 for `asmread`. |
| 168 | `        return split(5.2, 2.6, 0.05) if 0 < b <= lim else flat(5.3 if b == 0 else 2.5, 0.05)` | A count with 1 to `lim` threads on mesh 1 is split, near 5.2 and 2.6 GB/s. Every other count is flat: near 5.3 GB/s for 64+0 and near 2.5 GB/s above `lim`. |
| 169 | `    F = Folder(root, 'partA-20260101T001000Z', 'A1 A2 A3 A4', skipped_a3=True)` | `F`: folder 2, with the line of a skipped step A3 in its `env.txt`. |
| 170 | `    long_steps(F, rates, a4=a4)` | Writes the steps A1, A2 and A4 into folder 2. No values for A3 are given, so A3 has no csv file. |
| 171 | `    # the kill ended the script, so A4 of this folder would not exist: remove it, and write it in folder 3` | Comment: the kill ended the script. So step A4 would not exist in this folder. It is removed here and written into folder 3. |
| 172 | `    os.remove(os.path.join(F.d, 'A4.csv'))` | Deletes `A4.csv` of folder 2. |
| 173 | `    # folder 3: the repeated A2 launch, and A4` | Comment: folder 3 holds the repeated launch of A2, and step A4. |
| 174 | `    F3 = Folder(root, 'partA-20260101T020000Z', 'A2 A4')` | `F3`: folder 3. Its name has a later time than folder 2. |
| 175 | `    F3.block('A2', 'read_old-r2', 'bw_old', cpulist(64, 56), 256 * MIB, 6000, ['read'], 3, lambda _k: rates['read_old'], lambda k, r: 60,` | Writes the repeated launch `read_old-r2` of step A2 into folder 3, as a complete block. The call goes on in line 176. |
| 176 | `             all_args(64, 56, 'read', 3, 6000))` | Continues the call: the options text. |
| 177 | `    tmp = Folder(root, 'tmp-a4', 'A4'); long_steps(tmp, rates, a2_kill=False, a4=a4)` | Builds a temporary folder `tmp-a4` and writes all long steps into it, without a kill. |
| 178 | `    shutil.copy(os.path.join(tmp.d, 'A4.csv'), os.path.join(F3.d, 'A4.csv')); shutil.rmtree(tmp.d)` | Copies only its `A4.csv` into folder 3 and deletes the temporary folder. So the A4 blocks of folder 3 have no entries in `launches.txt`. |
| 179 | `    return [os.path.join(root, n) for n in ('partA-20260101T000000Z', 'partA-20260101T001000Z', 'partA-20260101T020000Z')]` | Returns the paths of the three folders. |

### Function `build_set2`: data set 2, mixed, and the helper `near` (lines 182 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 182 | `def build_set2(root):` | Starts the function `build_set2`. It builds the one folder of data set 2. |
| 183 | `    """Thread distributions between the limits: q of the write kernels is about 0.72 to 0.80, read_old 0.60."""` | Text of the function: the thread distributions lie between the limits. By the text q of the write kernels is about 0.72 to 0.80 and q of the old read kernel is 0.60. A recomputation from the formulas of lines 184 to 185 gives 0.66 to 0.82 for the three write kernels and 0.59 for the old read kernel. So the numbers of the text are rough. |
| 184 | `    rates = dict(read_old=split(4.0, 2.4, 0.03), read_new=split(2.6, 2.0, 0.03), asmread=flat(2.3, 0.05),` | `rates`: the rate functions of set 2. Every C kernel is split with a smaller distance between the meshes than in set 1: 4.0 and 2.4 GB/s for the old read kernel, 2.6 and 2.0 GB/s for the new one. `asmread` is flat near 2.3 GB/s. |
| 185 | `                 write_old=split(1.4, 1.0, 0.03), write_new=split(1.3, 1.1, 0.03), asmwrite=split(1.4, 0.95, 0.03))` | Continues `rates`: the three write kernels are split with ratios of the two mesh rates between the two limits of q. |
| 186 | `    def a4(k, a, b):` | Starts the inner function `a4`. |
| 187 | `        return split(4.0, 4.0 - 0.02 * b, 0.03)` | Every count of A4 is split with 4.0 GB/s on mesh 0 and a rate on mesh 1 that falls by 0.02 GB/s per thread on mesh 1. So q falls slowly with the count, without a step. |
| 188 | `    F = Folder(root, 'partA-20260102T000000Z', 'A1 A2 A3 A4 A5')` | `F`: the folder of set 2, with the steps A1 to A5 in its step list. It has no files of step A7. |
| 189 | `    long_steps(F, rates, a2_kill=False, a3=dict(one=split(5.0, 2.5), two=flat(3.0, 0.2)), a4=a4)` | Writes the long steps without a kill and with step A3. With one buffer the old read kernel is split at 5.0 and 2.5 GB/s. With two buffers it is flat near 3.0 GB/s. |
| 190 | `    one = lambda v: (lambda _k: (lambda i, cpu, rep: v(rep)))` | `one`: the same helper as in line 150. |
| 191 | `    F.block('A5', 'cpu2-proc1', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5), lambda k, r: 2500, a5_args(2))` | A5, process 1 on CPU 2: a constant rate of 67.5 GB/s. |
| 192 | `    F.block('A5', 'cpu2-proc2', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5), lambda k, r: 2500, a5_args(2), fail=True)` | A5, process 2 on CPU 2, written as a failed block. |
| 193 | `    return [F.d]` | Returns the path of the one folder. Step A6 has no file in this set. |
| 196 | `def near(a, b, tol=1e-9):` | Starts the function `near`. It compares two numbers with a tolerance. |
| 197 | `    return abs(a - b) <= tol` | Returns true when the two numbers differ by at most `tol`, which is 1e-9 unless the caller gives another value. |

### Function `check_set1`: the json values of data set 1 (lines 200 to 277)

| Line | Source | Explanation |
|---:|---|---|
| 200 | `def check_set1(s):` | Starts the function `check_set1`. `s` is the summary of data set 1, read back from its json file. Each `assert` stops the test with an error when its condition is false. |
| 201 | `    c = s['counts']` | `c`: the counts of the blocks. |
| 202 | `    assert s['steps_missing'] == ['A3'], s['steps_missing']` | Step A3 must be the only missing step. This proves that a step without a csv file is reported and not passed over. The value after the comma is shown when the test fails. |
| 203 | `    assert s['env'][1]['skipped'] == ['A3 skipped: MemAvailable is 61 GiB, below 70 GiB']` | The `env.txt` entry of folder 2 must hold the line of the skipped step A3, word for word. The page quotes this line to say why A3 has no data. |
| 204 | `    # killed and repeated` | Comment: the tests of the killed and repeated launch follow. |
| 205 | `    assert c['killed'] == 1 and c['failed'] == 0 and c['repeated_tags'] == 1, c` | Exactly 1 block has a `killed` line, none has a `failed` line, and 1 tag occurs more than once. So the analysis sees the kill and the repeat in the invented folders. |
| 206 | `    assert c['blocks_found'] == 4 + 16 + 12 + 12 + 1 + 22 and c['blocks_not_used'] == 1, c` | 67 blocks must be found: 4 of A5, 16 of A6, 12 of A1, 12 of A2 in folder 2, 1 more of A2 in folder 3, and 22 of A4. Exactly 1 of them must be left unused. This proves that no block is lost and that only the killed one is dropped. |
| 207 | `    nu = s['not_used'][0]` | `nu`: the one entry of the list `not_used`. |
| 208 | `    assert (nu['step'], nu['tag'], nu['folder'], nu['replaced']) == ('A2', 'read_old-r2', 'partA-20260101T001000Z', True), nu` | The unused block must be the launch `read_old-r2` of step A2 in folder 2, and `replaced` must be true: a complete block of the same launch is used. |
| 209 | `    assert 'killed' in nu['reason']` | Its reason must hold the word `killed`. |
| 210 | `    used = [b for b in s['blocks'] if (b['step'], b['tag']) == ('A2', 'read_old-r2')]` | `used`: the used blocks with that step and tag. |
| 211 | `    assert len(used) == 1 and used[0]['folder'] == 'partA-20260101T020000Z'` | Exactly one such block is used, and it comes from folder 3. Together with line 208 this proves choice C4: the last complete block of a repeated launch counts. This matters: a killed block has too few repetitions and thread lines, and its values must not enter the results. |
| 212 | `    # passes: A1 has 5 per thread (all marked), A2 has 60, one repetition has 48` | Comment: the passes. A1 has 5 passes per thread, so all its repetitions are marked. A2 has 60, and one repetition has 48. |
| 213 | `    a1 = s['A1']['read_old']` | `a1`: the summary of the old read kernel in step A1. |
| 214 | `    assert all(near(r['passes_per_thread'], 5) and r['below_50_passes'] for r in a1['reps'])` | Every repetition of it must have 5 passes per thread and the mark for fewer than 50 passes. This proves the formula of the passes: total bytes divided by threads times bytes per thread. |
| 215 | `    low_a2 = [x for x in s['passes']['below_50'] if x['step'] == 'A2']` | `low_a2`: the repetitions of step A2 below 50 passes. |
| 216 | `    assert [(x['tag'], x['rep']) for x in low_a2] == [('read_new-r1', 2)] and near(low_a2[0]['passes_per_thread'], 48), low_a2` | It must hold exactly one entry: repetition 2 of the launch `read_new-r1`, with 48 passes. This proves that the 2 % check finds a single short repetition among long ones, and marks no other. |
| 217 | `    assert s['passes']['n_below_50'] == 36 + 1` | 37 repetitions must be below 50 passes in all: the 36 of step A1 and that one of A2. |
| 218 | `    # split distribution without jitter: 64 threads at 5.00 GB/s on mesh 0, 56 threads at 2.50 GB/s on mesh 1` | Comment: the split distribution without deviation: 64 threads at 5.00 GB/s on mesh 0 and 56 threads at 2.50 GB/s on mesh 1. |
| 219 | `    r = a1['reps'][0]` | `r`: the first repetition of the old read kernel in A1. |
| 220 | `    assert r['mesh0'] == dict(n=64, sum=320.0, median=5.0) and r['mesh1'] == dict(n=56, sum=140.0, median=2.5), (r['mesh0'], r['mesh1'])` | Mesh 0 must have 64 threads, a sum of 320.0 GB/s and a median of 5.0 GB/s. Mesh 1 must have 56 threads, a sum of 140.0 GB/s and a median of 2.5 GB/s. This proves that a thread goes to the right mesh by its CPU, and that sum and median are computed per mesh. |
| 221 | `    assert near(r['q'], 0.5) and r['label_rule'] == 'split' and r['label'] == 'split'` | q must be 0.5, and both the label of the rule and the used label must be `split`. With 120 threads the 12th rate is 2.5 and the 108th is 5.0 GB/s. |
| 222 | `    fh = r['fastest_half']` | `fh`: the fastest half of that repetition. |
| 223 | `    assert fh['n_half'] == 60 and fh['mesh0'] == [60, 60] and fh['mesh1'] == [0, 0], fh` | The half must have 60 threads, all 60 on mesh 0 and none on mesh 1. The 64 threads of mesh 0 are tied at the limit, and they alone fill the half. So the count is exact also with tied rates. |
| 224 | `    # uniform distribution without jitter: every thread at 2.40 GB/s. The fastest half is then not defined by the rates.` | Comment: the uniform distribution without deviation: every thread at 2.40 GB/s. The rates then do not define the fastest half. |
| 225 | `    r = s['A1']['read_new']['reps'][0]` | `r`: the first repetition of the new read kernel in A1. |
| 226 | `    assert near(r['q'], 1.0) and r['label'] == 'uniform'` | q must be 1.0, and the label must be `uniform`. This proves the other end of the rule: equal rates give q of 1 and the label `uniform`. |
| 227 | `    assert r['fastest_half']['mesh0'] == [4, 60] and r['fastest_half']['mesh1'] == [0, 56] and r['fastest_half']['tied_at_cut'] == 120` | The count of mesh 0 in the fastest half must be the range 4 to 60, the count of mesh 1 the range 0 to 56, and all 120 threads must be tied. This proves choice C3: when equal rates leave the half open, the analysis gives the lowest and highest possible count and no single invented number. |
| 228 | `    assert near(r['mesh0']['sum'], 153.6) and near(r['mesh1']['sum'], 134.4)` | The sums of the thread rates must be 153.6 GB/s on mesh 0 (64 times 2.4) and 134.4 GB/s on mesh 1 (56 times 2.4). |
| 229 | `    # percentile, nearest rank: 10 values 1..10 -> value number 1 and number 9` | Comment: the nearest-rank percentile. Of the 10 values 1 to 10, the 10th percentile is value number 1 and the 90th is value number 9. |
| 230 | `    assert A.pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10) == 1 and A.pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9` | Tests exactly that on the list 1 to 10. |
| 231 | `    assert A.pct(list(range(1, 121)), 10) == 12 and A.pct(list(range(1, 121)), 90) == 108` | Tests the case of 120 threads: of the values 1 to 120, the 10th percentile is the 12th value and the 90th is the 108th. These two tests fix choice C1. q depends on which two threads are taken, so the rank must not shift by one. |
| 232 | `    # q falls into two groups, labels are used` | Comment: q falls into two groups, and the labels are used. |
| 233 | `    d = s['q']['decision']` | `d`: the decision of the test of the two groups. |
| 234 | `    assert d['two_groups'] and d['limits_fit'] and d['labels_usable'], d` | All three answers must be true: two groups, the limits fit, the labels are usable. |
| 235 | `    assert d['n_between'] == 0 and d['lower_max'] < 0.65 and d['upper_min'] > 0.85` | No q may lie between the limits, the lower group must end below 0.65, and the upper group must start above 0.85. The tests of lines 234 to 235 prove that clear data turn the labels on. Every label of the page depends on this one decision. |
| 236 | `    assert d['n'] == 36 + 36 + 44, d['n']` | 116 q values must take part: 36 of A1, 36 of A2 and 44 of A4. The killed block adds none, and the one-thread steps have no q. |
| 237 | `    # A1 against A2 for the write kernel with a split: mesh 0 is the fast mesh` | Comment: two groups of tests follow. The first is for a write kernel with a split, where mesh 0 is the fast mesh. The second is the comparison of A1 with A2. |
| 238 | `    w = s['A1']['write_old']` | `w`: the summary of the old write kernel in A1. |
| 239 | `    assert w['mesh0_median']['median'] > w['mesh1_median']['median'] and w['labels'] == ['split']` | Its median thread rate must be higher on mesh 0 than on mesh 1, and its only label must be `split`. This proves that the summary of a kernel keeps the two meshes apart and carries the label of its repetitions. |
| 240 | `    assert set(s['A1_A2']['kernels']) == set(K6)` | The comparison of A1 with A2 must hold all six kernels. |
| 241 | `    assert near(s['A1_A2']['kernels']['read_new']['change_GBps'], 0.0) and s['A1_A2']['kernels']['read_new']['ranges_overlap']` | For the new read kernel the change of the median total must be 0 GB/s and the two ranges must overlap. The invented rates do not depend on the interval length. So this proves that the comparison reports no change where there is none. |
| 242 | `    # A4: old read changes between 64+48 and 64+52, asm read between 64+32 and 64+40; a+a never changes` | Comment: step A4. The old read kernel changes between 64+48 and 64+52, `asmread` between 64+32 and 64+40, and the series `a+a` never changes. |
| 243 | `    k = s['A4']['kernels']` | `k`: the kernels of step A4. |
| 244 | `    assert k['read_old']['series']['64+b']['bracket'] == ['64+48', '64+52'], k['read_old']['series']['64+b']` | The bracket of the old read kernel in the series `64+b` must be 64+48 and 64+52. That is where the generator ends the split (line 167). |
| 245 | `    assert k['asmread']['series']['64+b']['bracket'] == ['64+32', '64+40']` | The bracket of `asmread` must be 64+32 and 64+40. |
| 246 | `    assert len(k['read_old']['series']['64+b']['changes']) == 2      # 64+0 is uniform: that change is listed, and is not the bracket` | The old read kernel must have 2 changes in the series `64+b`. By the comment the count 64+0 is uniform. That change is listed and is not the bracket. This proves choice C7: the count with threads on one mesh only does not hide the real change. |
| 247 | `    assert k['read_old']['series']['a+a']['bracket'] is None and 'no change' in k['read_old']['series']['a+a']['note']` | In the series `a+a` the old read kernel must have no bracket, and the note must hold the words `no change`. |
| 248 | `    assert s['A4']['bracket_compare']['64+b'] == 'different'` | The comparison of the two brackets in the series `64+b` must be `different`. So the analysis tells two kernels with different brackets apart. The plan asks for this comparison of the old read kernel with `asmread`. |
| 249 | `    assert k['read_old']['counts']['64+48']['label'] == 'split' and k['read_old']['counts']['64+52']['label'] == 'uniform'` | The count 64+48 of the old read kernel must have the label `split` and the count 64+52 the label `uniform`. |
| 250 | `    # A5` | Comment: the tests of step A5 follow. |
| 251 | `    p = {x['tag']: x for x in s['A5']['processes']}` | `p`: the processes of A5 under their tags. |
| 252 | `    assert p['cpu41-proc1']['changes'] == [dict(at_interval=13, from_level='low', to_level='high')], p['cpu41-proc1']['changes']` | Process 1 on CPU 41 must have exactly one level change: from low to high at interval 13. The interval 12 is changing and is left out. This proves choice C6: the position of a change is the first interval with the new label. |
| 253 | `    assert (p['cpu41-proc1']['n_low'], p['cpu41-proc1']['n_changing'], p['cpu41-proc1']['n_high']) == (12, 1, 17)` | The same process must have 12 low intervals, 1 changing and 17 high. This proves that every interval is counted under its own label, also the one between the two limits. |
| 254 | `    assert p['cpu2-proc1']['changes'] == [] and p['cpu2-proc1']['n_low'] == 30` | Process 1 on CPU 2 must have no change and 30 low intervals. This proves that a process without a change gets an empty list of changes, and not a false one. |
| 255 | `    assert p['cpu41-proc2']['first_level'] == 'high'` | The first interval of process 2 on CPU 41 must be high. The page uses this label to compare the end of a first process with the start of the second one. |
| 256 | `    pr = {x['cpu']: x for x in s['A5']['pairs']}` | `pr`: the pairs of A5 under their CPU. |
| 257 | `    assert pr[2]['second_not_at_once'] and pr[2]['second_waited_s'] == 2 and not pr[41]['second_not_at_once']` | The pair on CPU 2 must be marked as not at once, with a wait of 2 s. The pair on CPU 41 must not be marked. The handoff note asks to report a second process that waited. This proves that the wait of the header line reaches the result. |
| 258 | `    # A6: process medians 67.15 .. 67.85 with pages of 2 MiB allowed, 52.15 .. 52.85 without` | Comment: step A6. The process medians run from 67.15 to 67.85 GB/s with pages of 2 MiB allowed, and from 52.15 to 52.85 GB/s without. |
| 259 | `    a6 = s['A6']` | `a6`: the summary of step A6. |
| 260 | `    assert a6['thp']['process_medians']['n'] == 8 and a6['nothp']['process_medians']['n'] == 8` | Each kind must have 8 process medians. |
| 261 | `    assert near(a6['thp']['process_medians']['median'], 67.5, 1e-6) and near(a6['nothp']['process_medians']['median'], 52.5, 1e-6)` | The median of the process medians must be 67.5 GB/s with huge pages allowed and 52.5 GB/s with `--no-thp`, within 0.000001 GB/s. |
| 262 | `    assert near(a6['nothp_minus_thp_GBps'], -15.0, 1e-6) and not a6['process_ranges_overlap']` | The difference must be -15.0 GB/s, and the two ranges of process medians must not overlap. The tests of lines 260 to 262 prove that the two kinds of A6 are summarised apart, by the median of their process medians. |
| 263 | `    assert all(x['thp_line_ok'] for x in a6['processes'])` | Every A6 block must show the page setting that its launch asked for. This proves that the analysis compares the printed setting with the kind of the launch. A block with another setting would mean that a process ran with other pages than its tag says. |
| 264 | `    # load` | Comment: the tests of the load readings follow. |
| 265 | `    L = s['load']` | `L`: the load readings per step. |
| 266 | `    assert L['A1']['launches'] == 12 and L['A1']['load1']['min'] == 0.5 and L['A1']['load1']['max'] == 31.2` | Step A1 must have 12 launches, and its load average over 1 minute must run from 0.5 to 31.2 tasks. |
| 267 | `    assert L['A1']['n_waited'] == 11 and L['A1']['waited_s']['max'] == 4` | 11 launches of A1 must have waited, and the longest wait must be 4 s. The tests of lines 266 to 267 prove that the load readings of the header lines reach the summary. By the handoff note the user asks for the system load in every result. |
| 268 | `    assert L['A1']['busiest'][0] == dict(user='other', comm='busy_job', max_pcpu=99.0), L['A1']['busiest'][0]` | The busiest process of step A1 must be `busy_job` of the user `other` at 99.0 %. This proves that a busy process of another account in `launches.txt` reaches the summary. |
| 269 | `    assert s['env'][0]['a7']['A7-sve.txt']['sve_vector_length_bytes'] == '16'` | The SVE vector length of folder 1 must be the text `16`. This proves that the value of the file `A7-sve.txt` is read. |
| 272 | `def check_set1_a4_first_count(s):` | Starts the function `check_set1_a4_first_count`. |
| 273 | `    # with 64+0 uniform the 64+b series would have two changes. The generator gives 64+0 a flat rate, so check what was computed.` | Comment: with a uniform count 64+0 the series `64+b` has two changes. The generator gives 64+0 a flat rate, so the test checks what was computed. |
| 274 | `    k = s['A4']['kernels']['read_old']` | `k`: the old read kernel of step A4. |
| 275 | `    assert k['counts']['64+0']['label'] == 'uniform'` | The count 64+0 must have the label `uniform`. This is the base of the test of line 246. |

### Function `check_set2`: the json values of data set 2 (lines 278 to 313)

| Line | Source | Explanation |
|---:|---|---|
| 278 | `def check_set2(s):` | Starts the function `check_set2`. `s` is the summary of data set 2. |
| 279 | `    d = s['q']['decision']` | `d`: the decision of the test of the two groups. |
| 280 | `    assert not d['labels_usable'], d` | The labels must not be usable. Set 2 has q values between the limits. |
| 281 | `    assert d['reason']` | The decision must give a reason. |
| 282 | `    # WHY: the handoff compares only the read rows of A3. The 36 write and copy repetitions of the 6 processes with` | Comment, why this test exists: the handoff note compares only the read rows of step A3. The sentence ends in line 283. |
| 283 | `    # --kernel all must not take part in the test that switches the labels on or off for all of Part A.` | Continues the comment: the 36 write and copy repetitions of the 6 processes with `--kernel all` must not take part in the test that turns the labels on or off for all of Part A. |
| 284 | `    # 36 (A1) + 36 (A2) + 44 (A4) + 18 (A3 one buffer, read) + 18 (A3 two buffers, read) = 152; before this rule 188.` | Continues the comment: the count is 36 of A1, 36 of A2, 44 of A4, and 18 read repetitions of A3 for each number of buffers. That gives 152. Before this rule the count was 188. |
| 285 | `    assert d['n'] == 152 and len(s['q']['rows']) == 152, d['n']` | Exactly 152 q values must take part, and the list of the rows must have the same length. |
| 286 | `    assert len(s['q']['rows_left_out']) == 36 and {x['kernel'] for x in s['q']['rows_left_out']} == {'write', 'copy'}` | 36 rows must be left out, and their kernels must be `write` and `copy` only. |
| 287 | `    assert all(x['step'] != 'A3' or x['kernel'] == 'read' for x in s['q']['rows'])` | No row of step A3 with another kernel than `read` may be among the rows of the test. The three tests prove choice C8. |
| 288 | `    # no label is set anywhere, the rule labels stay available` | Comment: no label is set anywhere, and the labels of the rule stay available. |
| 289 | `    assert all(r['label'] is None for k in s['A1'].values() for r in k['reps'])` | Every repetition of step A1 must have an empty `label`. |
| 290 | `    assert any(r['label_rule'] == 'between' for k in s['A1'].values() for r in k['reps'])` | At least one repetition of A1 must have the rule label `between`. So the rule is still computed, and only its use is turned off. |
| 291 | `    assert s['A1']['read_old']['labels'] is None` | The summary of the old read kernel in A1 must have no labels. |
| 292 | `    for k in s['A4']['kernels'].values():` | Loop over the kernels of step A4. |
| 293 | `        for ser in k['series'].values():` | Loop over the two series of each kernel. |
| 294 | `            assert ser['bracket'] is None and ser['note'] == 'labels not available'` | Every series must have no bracket and the note `labels not available`. This proves that the analysis builds no bracket from labels that it may not use. |
| 295 | `    # A3 is present: 4 groups of 3 processes, read rows only (3 repetitions per process, not 9)` | Comment: step A3 is present, with 4 groups of 3 processes. Only the read rows count: 3 repetitions per process, not 9. |
| 296 | `    g = s['A3']['groups']` | `g`: the groups of step A3. |
| 297 | `    assert sorted(g) == ['onebuf-ms500', 'onebuf-ms6000', 'twobuf-ms500', 'twobuf-ms6000']` | The four groups must be one buffer and two buffers, each at 500 ms and at 6000 ms. |
| 298 | `    assert all(len(x['processes']) == 3 and all(len(p['reps']) == 3 for p in x['processes']) for x in g.values())` | Each group must have 3 processes with 3 repetitions each. A process with two buffers has 9 repetitions in its block, so this proves that write and copy are left out. |
| 299 | `    assert g['twobuf-ms6000']['processes'][0]['other_kernels'] == ['copy', 'write']` | The first process with two buffers at 6000 ms must name `copy` and `write` as its other kernels. |
| 300 | `    assert near(g['onebuf-ms6000']['q']['median'], 0.5) and g['twobuf-ms6000']['q']['median'] > 0.8` | The median q must be 0.5 with one buffer at 6000 ms and above 0.8 with two buffers. |
| 301 | `    assert not s['A3']['compare']['6000']['q_ranges_overlap'] and s['A3']['compare']['6000']['same_label'] is None` | At 6000 ms the two ranges of q must not overlap, and `same_label` must be empty: the labels are not used. |
| 302 | `    # copy rows of --kernel all: 60 passes, not 120` | Comment: the copy rows of `--kernel all` have 60 passes, not 120. The numbers of this line do not fit the code: the generator gives the copy rows 40 passes (line 137), and line 304 and line 307 name 40 and 80. |
| 303 | `    # 36 repetitions of A1 (5 passes), 1 of A2 (48 passes), and the 18 copy repetitions of A3 (40 passes).` | Comment: the count below 50 passes is made of 36 repetitions of A1 with 5 passes, 1 of A2 with 48 passes, and the 18 copy repetitions of A3 with 40 passes. |
| 304 | `    # A copy repetition counts read plus written bytes: without the division by 2 it would show 80 passes and not be marked.` | Comment, why this matters: a copy repetition counts the bytes read plus the bytes written. Without the division by 2 it would show 80 passes and would not be marked. |
| 305 | `    assert s['passes']['n_below_50'] == 36 + 1 + 18, s['passes']['n_below_50']` | 55 repetitions must be below 50 passes: 36, 1 and 18. |
| 306 | `    cp = [x for x in s['passes']['below_50'] if x['kernel'] == 'copy']` | `cp`: the copy repetitions among them. |
| 307 | `    assert len(cp) == 18 and all(near(x['passes_per_thread'], 40) for x in cp)` | There must be 18, each with 40 passes per thread. This proves that the analysis halves the passes of a copy kernel. |
| 308 | `    # the failed A5 process is not used and listed` | Comment: the failed A5 process is not used and is listed. |
| 309 | `    assert s['counts']['failed'] == 1 and [x['tag'] for x in s['not_used']] == ['cpu2-proc2']` | 1 block must have a `failed` line, and the list of unused blocks must hold exactly the launch `cpu2-proc2`. |
| 310 | `    assert s['A5']['pairs'][0]['have_both'] is False` | The A5 pair on CPU 2 must be marked as not complete. So the page cannot compare a first process with a second one that failed. |
| 311 | `    assert s['steps_missing'] == ['A6', 'A7'], s['steps_missing']` | The missing steps must be A6 and A7. Set 2 has no file for either. |

### Functions `check_two_groups` and `check_units`: single functions on small inputs (lines 314 to 350)

| Line | Source | Explanation |
|---:|---|---|
| 314 | `def check_two_groups():` | Starts the function `check_two_groups`. It tests the function `two_groups` of the analysis on six short lists. |
| 315 | `    f = A.two_groups` | `f`: a short name for that function. |
| 316 | `    assert f([0.5, 0.52, 0.55, 0.9, 0.95, 0.97])['labels_usable']` | Three values near 0.5 and three near 0.95: the labels must be usable. This is the clear case of two groups on the two sides of the limits. |
| 317 | `    assert not f([0.9, 0.92, 0.95, 0.97, 0.99])['two_groups']                  # one group` | Five values from 0.9 to 0.99: not two groups. By the comment this is one group. The largest distance is 0.03, below 0.10. |
| 318 | `    assert not f([0.5, 0.6, 0.7, 0.8, 0.9, 0.95])['two_groups']                # spread evenly` | Six values from 0.5 to 0.95 in steps of about 0.1: not two groups. By the comment they are spread evenly. The distance is not larger than the width of a group. |
| 319 | `    r = f([0.30, 0.32, 0.5, 0.52, 0.55])                                        # two groups, both below 0.65` | `r`: the result for two values near 0.3 and three near 0.5. By the comment there are two groups, both below 0.65. |
| 320 | `    assert r['two_groups'] and not r['limits_fit'] and not r['labels_usable']` | The result must say two groups, limits that do not fit, and labels that are not usable. This proves that two clear groups alone do not turn the labels on: the groups must also lie on the two sides of the limits. |
| 321 | `    assert not f([0.5, 0.9, 0.95, 0.97])['two_groups']                         # one value alone is not a group` | One value at 0.5 and three near 0.95: not two groups. By the comment one value alone is not a group. |
| 322 | `    assert not f([0.5, 0.9])['labels_usable']` | Two values only: the labels must not be usable. The function needs at least 4 values. |
| 325 | `def check_units():` | Starts the function `check_units`. It tests five single functions of the two scripts on small inputs: `fx` and `fs` of the page generator, and `limit_check`, `level_check` and `parse_core_events` of the analysis. |
| 326 | `    # WHY: a median of 6 rates printed with 2 decimals can lie in the middle of two printed values (0.995). Printed as 0.99 next to` | Comment, why the first tests exist: a median of 6 rates that are printed with 2 decimals can lie exactly in the middle of two printed values, as 0.995 does. The sentence ends in line 327. |
| 327 | `    # 0.98 and a difference of 0.02 the three numbers of one sentence do not agree. Such a value keeps its third decimal.` | Continues the comment: printed as 0.99 beside 0.98 and a difference of 0.02, the three numbers of one sentence do not agree. Such a value keeps its third decimal. |
| 328 | `    assert H.fx(0.995) == '0.995' and H.fx(0.015) == '0.015' and H.fx(0.98) == '0.98' and H.fx(2.6149999999) == '2.615'` | The function `fx` of the page generator must print 0.995 as `0.995`, 0.015 as `0.015`, 0.98 as `0.98`, and 2.6149999999 as `2.615`. The last value shows that a small error of floating-point numbers does not hide the special case. |
| 329 | `    assert H.fx(0.6053) == '0.61' and H.fs(-8.335) == '-8.335' and H.fs(4.85) == '+4.85' and H.fx(-0.001) == '0.00'` | `fx` must print 0.6053 as `0.61`. The function `fs` must print -8.335 as `-8.335` and 4.85 as `+4.85`. `fx` must print -0.001 as `0.00`, without a minus sign. |
| 330 | `    # WHY (plan rule 5): a level limit that lies inside a dense run of rates must not be used to label them.` | Comment, why the next test exists (rule 5 of the plan): a level limit that lies inside a dense run of rates must not be used to label them. |
| 331 | `    # 30 rates that rise without a step from 68.5 to 69.5 GB/s: the limit 69 has rates 0.03 GB/s apart on its two sides.` | Continues the comment: the test uses 30 rates that rise without a step from 68.5 to 69.5 GB/s. The limit 69 then has rates about 0.03 GB/s apart on its two sides. |
| 332 | `    c = A.limit_check([68.5 + i * 1.0 / 29 for i in range(30)])` | `c`: the result of the function `limit_check` for these 30 rates. |
| 333 | `    assert not c['labels_usable'] and not c['limits'][0]['separates'] and c['limits'][1]['separates'] and c['limits'][1]['empty_range'] is None` | The labels must not be usable. The limit 69 must not separate the rates. The limit 70.5 must separate them, with no empty range: all rates lie below it. |
| 334 | `    # two levels with an empty range of 1.9 GB/s around 69 and of 1.4 GB/s around 70.5: both limits separate` | Comment: two levels with an empty range of 1.9 GB/s around 69 and of 1.4 GB/s around 70.5. Both limits separate. |
| 335 | `    c = A.limit_check([67.3, 67.4, 67.5, 69.4, 70.8, 70.9, 71.0])` | `c`: the result for three rates near 67.4, one at 69.4 and three near 70.9 GB/s. |
| 336 | `    assert c['labels_usable'] and c['limits'][0]['n_below'] == 3 and near(c['limits'][0]['empty_range'], 1.9, 1e-9)` | The labels must be usable, 3 rates must lie below the limit 69, and the empty range around it must be 1.9 GB/s. The two tests prove choice C9 in both directions. |
| 337 | `    # a CPU whose labels are not usable gets no level change, even if its labels go from low to changing` | Comment: a CPU whose labels are not usable gets no level change, also when its labels go from low to changing. |
| 338 | `    a5 = dict(processes=[dict(cpu=41, rates_GBps=[68.9, 68.95, 69.0, 69.05, 69.1], changes=[dict(at_interval=2, from_level='low', to_level='high')])])` | `a5`: one invented A5 process on CPU 41 with five rates from 68.9 to 69.1 GB/s and one level change that is already filled in. |
| 339 | `    lv = A.level_check(a5, dict(processes=[]))` | `lv`: the result of the function `level_check` for this process and no A6 process. |
| 340 | `    assert a5['processes'][0]['labels_usable'] is False and a5['processes'][0]['changes'] == [] and a5['processes'][0]['n_below_low_limit'] == 2` | The process must be marked as not usable, its list of changes must be empty, and 2 of its rates must lie below the lower limit. This proves that the check removes a change that rests on a limit inside the rates. |
| 341 | `    assert not lv['cpus']['41']['labels_usable']` | The check of CPU 41 must say that the labels are not usable. |
| 342 | `    # WHY (handoff B.8): Part C takes the PMU type and the event codes from A7-core-events.txt. A missing event must stay empty, not be guessed.` | Comment, why the next test exists (section B.8 of the handoff note): Part C takes the PMU type and the event codes from `A7-core-events.txt`. A missing event must stay empty and must not be guessed. |
| 343 | `    pm = A.parse_core_events(['== /sys/bus/event_source/devices/armv8_pmuv3_0 type=11', '/sys/d/armv8_pmuv3_0/events/cpu_cycles:event=0x0011',` | `pm`: the result of the function `parse_core_events` for four invented lines: one PMU line with the type 11 and the event line of `cpu_cycles`. |
| 344 | `                              '/sys/d/armv8_pmuv3_0/events/ll_cache_miss_rd:event=0x0037', '/sys/d/armv8_pmuv3_0/events/l3d_cache_refill:event=0x002a'])` | Continues the list with two more event lines: `ll_cache_miss_rd` and `l3d_cache_refill`. |
| 345 | `    assert len(pm) == 1 and pm[0]['name'] == 'armv8_pmuv3_0' and pm[0]['type'] == '11' and pm[0]['n_events'] == 3` | One PMU must be found, with the name `armv8_pmuv3_0`, the type `11` and 3 events. |
| 346 | `    b8 = {x['event']: x for x in pm[0]['b8']}` | `b8`: its five events under the words of the handoff note. |
| 347 | `    assert b8['cycles']['code'] == '0x0011' and b8['cycles']['line'] == 2 and b8['instructions']['code'] is None and b8['last-level read misses']['code'] == '0x0037'` | The cycles must have the code `0x0011` from the second line. The instructions must have no code: the invented lines hold no `inst_retired`. The last-level read misses must have the code `0x0037`. |
| 348 | `    assert [x['name'] for x in pm[0]['b8_other']] == ['l3d_cache_refill']` | The second candidate `l3d_cache_refill` must be listed as the only other event. |

### Functions `check_set1_more` and `check_set2_more`: json values and page text together (lines 351 to 391)

| Line | Source | Explanation |
|---:|---|---|
| 351 | `def check_set1_more(s, h):` | Starts the function `check_set1_more`. `s` is the summary of set 1, and `h` is the text of its page. |
| 352 | `    # the A7 file of set 1 lists one PMU of type 10 with one of the five events` | Comment: the A7 file of set 1 lists one PMU of the type 10 with one of the five events. |
| 353 | `    pm = s['env'][0]['a7']['A7-core-events.txt']['pmu_list'][0]` | `pm`: the first PMU entry of folder 1. |
| 354 | `    assert pm['type'] == '10' and [x['code'] for x in pm['b8']] == [None, None, '0x03', None, None]` | Its type must be `10`, and only the third of the five events, the L1 data refills, must have a code. |
| 355 | `    assert 'Consequence for Part C' in h and 'type number for <code>perf_event_open</code> is 10' in h and h.count('the file has no event of this name') == 4` | The page must hold the heading of the part on Part C and the sentence with the type number 10. It must say four times that the file has no event of this name. This proves that the page shows each missing code as missing. |
| 356 | `    # A1 against A2: the rates of set 1 do not depend on the interval, so no long total lies outside the short range,` | Comment: the rates of set 1 do not depend on the interval. So no long total lies outside the short range. The sentence ends in line 357. |
| 357 | `    # and the reading for the order of B7 and B8 is "the totals stayed" (choice C11)` | Continues the comment: the reading for the order of the steps B7 and B8 is then that the totals stayed (choice C11). |
| 358 | `    k = s['A1_A2']['kernels']['read_new']` | `k`: the comparison of A1 with A2 for the new read kernel. |
| 359 | `    assert k['n_long'] == 6 and k['n_long_outside_short'] == 0` | It must have 6 long totals, none of them outside the short range. |
| 360 | `    assert s['A1_A2']['order_reading'] == dict(changed=False, difference_smaller_with_long=False)` | The reading must say `changed` false and `difference_smaller_with_long` false. |
| 361 | `    assert 'Consequence for the order of B7 and B8' in h and 'the totals stayed' in h` | The page must hold the heading of the part on the order of B7 and B8 and the words `the totals stayed`. This proves that the reading of the json file reaches the page. |
| 362 | `    # WHY: "no other load" may be said only if no reading speaks against it. Set 1 has 1 logged-in user, launches that waited,` | Comment, why the next tests exist: the page may say that no other load was seen only when no reading speaks against it. The sentence ends in line 363. |
| 363 | `    # and a process of another user at 99 % of a CPU.` | Continues the comment: set 1 has 1 logged-in user, launches that waited, and a process of another user at 99 % of a CPU. |
| 364 | `    lc = s['load_check']` | `lc`: the readings for load from other users. |
| 365 | `    assert lc['no_other_load_seen'] is False and lc['logins_max'] == 1 and lc['n_waited'] > 0 and lc['own_user'] is None` | `no_other_load_seen` must be false, the highest number of logins must be 1, at least one launch must have waited, and the own account must be unknown. |
| 366 | `    assert lc['busiest_other'][0] == dict(pcpu=99.0, user='other', comm='busy_job')` | The busiest process of another account must be `busy_job` of the user `other` at 99.0 %. |
| 367 | `    assert 'No reading of this run shows load from another user' not in h` | The page must not hold the sentence that no reading shows load from another user. This matters: a rate that was measured beside a busy process of another user must not be presented as measured on a quiet machine. |
| 368 | `    # the header line and launches.txt hold one reading each of the runnable tasks; the generator writes the same value into both.` | Comment: the header line and `launches.txt` each hold one reading of the runnable tasks, and the generator writes the same value into both. |
| 369 | `    # The 22 A4 blocks of folder 3 were copied in without their launches.txt entries, so they have no second reading.` | Continues the comment: the 22 A4 blocks of folder 3 were copied in without their entries in `launches.txt`. So they have no second reading. |
| 370 | `    assert lc['n_runnable_differ'] == 0 and lc['n_with_launches_txt'] == lc['n_launches'] - 22` | No launch may show two different readings, and the number of launches with a second reading must be the number of all launches minus 22. |
| 371 | `    # the level limits separate the rates of both CPUs of set 1, so the level change of CPU 41 is given` | Comment: the level limits separate the rates of both CPUs of set 1. So the level change of CPU 41 is given. |
| 372 | `    assert all(c['labels_usable'] for c in s['level_check']['cpus'].values()) and sorted(s['level_check']['cpus']) == ['2', '41']` | The labels of every CPU must be usable, and the CPUs of the check must be 2 and 41. |
| 373 | `    assert 'first high interval was number 13' in h` | The page must hold the words that the first high interval was number 13. |
| 374 | `    # labels usable: the brackets of A4 are the thread counts for B8` | Comment: with usable labels, the brackets of step A4 are the thread counts for step B8. |
| 375 | `    assert 'Consequence for B8' in h and 'the pattern changed between 64+48 and 64+52 threads. B8 refines' in h` | The page must hold the heading of the part on B8 and the sentence that the pattern changed between 64+48 and 64+52 threads. |
| 378 | `def check_set2_more(s, h):` | Starts the function `check_set2_more`. `s` is the summary of set 2, and `h` is the text of its page. |
| 379 | `    # WHY (handoff B.9, row B8): without labels A4 gives no pair of counts. The page must say so as "Insufficient data", not stay silent.` | Comment, why the next test exists (row B8 of section B.9 of the handoff note): without labels, A4 gives no pair of counts. The page must say so with the words `Insufficient data` and must not stay silent. |
| 380 | `    assert 'Part A gives no thread counts for B8' in h and re.search(r'Insufficient data\.</b> Part A gives no thread counts for B8', h)` | The page must hold the sentence that Part A gives no thread counts for B8, directly after the bold words `Insufficient data.`. The pattern in `re.search` matches these words, the end tag of the bold text and the sentence. |
| 381 | `    g = s['q']['groups']` | `g`: the description of where the q values lie. |
| 382 | `    # old read at 64+56 threads: 12 repetitions of A1 and A2, 18 + 18 read repetitions of A3, 2 of A4` | Comment: the old read kernel at 64+56 threads has 12 repetitions in A1 and A2, 18 and 18 read repetitions in A3, and 2 in A4. |
| 383 | `    assert g['read_old']['n'] == 6 + 6 + 36 + 2 and g['load_only_read']['n'] == 12 + 12 + 2, (g['read_old']['n'], g['load_only_read']['n'])` | So its summary must count 50 repetitions, and the summary of the new read kernel and `asmread` must count 26: 12, 12 and 2. This proves that the summary collects the full thread count from all steps. |
| 384 | `    assert sum(x['n'] for x in g['below_split']) == s['q']['decision']['n_split']` | The counts of the q values below 0.65 per kernel must add up to the number of split values of the decision. |
| 385 | `    assert sum(x['n'] for x in g['between']) == s['q']['decision']['n_between']` | The counts of the q values between the limits must add up to the number of between values of the decision. The two tests prove that the two descriptions of the page count the same values. |
| 386 | `    # the count of the fastest half is given for each repetition, not as one merged range` | Comment: the count of the fastest half is given for each repetition, not as one merged range. |
| 387 | `    assert 'per repetition' in h and h.count(' of 60</td>') > 0` | The page must hold the words `per repetition`, and at least one table cell must end with the words `of 60`. |
| 388 | `    # A7 is missing in set 2: no codes for Part C` | Comment: step A7 is missing in set 2, so there are no codes for Part C. |
| 389 | `    assert 'insufficient data for the counter codes of Part C (A7)' in h` | The page must say `insufficient data` for the counter codes of Part C, in its short version. |

### Function `check_page`: rules that every test page must meet (lines 392 to 405)

| Line | Source | Explanation |
|---:|---|---|
| 392 | `def check_page(html, s):` | Starts the function `check_page`. It tests rules that hold for every page. `html` is the text of the page and `s` its summary. |
| 393 | `    low = html.lower()` | `low`: the text of the page in lower case. |
| 394 | `    for w in ('rejected', 'confirmed'):` | Loop over the two words `rejected` and `confirmed`. |
| 395 | `        assert w not in low, f'the page must not use the word "{w}"'` | Neither word may occur on the page. Part A is screening, and the handoff note forbids these two words for its results. The text after the comma is the message of a failed test. |
| 396 | `    assert '<script' not in low and 'http://' not in low.replace('http://www.w3.org', '') and 'https://' not in low, 'external reference or script in the page'` | The page may hold no script and no web address. An address of `www.w3.org` is allowed. This proves that the page is one file that loads nothing from another place. |
| 397 | `    assert 'Short version' in html and 'Words used here' in html and 'References' in html and 'observed in screening' in low` | The page must hold the short version, the list of words, the references and the words `observed in screening`. |
| 398 | `    assert 'prefers-color-scheme' not in low` | The page must not hold the text `prefers-color-scheme`. That text would make the colours follow the dark mode of the system. The handoff note lists a light background among the standing rules of the user for a result page. |
| 399 | `    for step in s['steps_missing']:` | Loop over the steps that the summary lists as missing. |
| 400 | `        assert re.search(r'Insufficient data[^<]*' + step, html), f'no "Insufficient data" for {step}'` | For each missing step the page must hold the words `Insufficient data`, followed in the same piece of text by the name of the step. The pattern `[^<]*` matches any characters other than the start of an HTML tag. This proves that no missing step is passed over in silence. |
| 401 | `    sv = re.search(r'<b>Short version\.</b>(.*?)</p>', html, re.S).group(1)` | `sv`: the text of the short version: the part of the page from the bold words `Short version.` to the end of that paragraph. `re.S` lets the pattern run over line ends. |
| 402 | `    n = len(re.findall(r'[.!?](?:\s\|$)', re.sub(r'<[^>]+>', '', sv).strip()))` | `n`: the number of sentences of the short version. The inner `re.sub` removes the HTML tags. `re.findall` then counts each full stop, exclamation mark or question mark that is followed by white space or stands at the end. |
| 403 | `    assert n <= 3, f'Short version has {n} sentences'` | The short version may have at most 3 sentences. The handoff note lists this among the standing rules of the user for a result page. |

### Function `main`: the order of the tests (lines 406 to 435)

| Line | Source | Explanation |
|---:|---|---|
| 406 | `def main():` | Starts the function `main`. |
| 407 | `    keep = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None` | `keep`: the folder that follows the option `--keep`, or `None` when the option is not given. |
| 408 | `    root = keep or tempfile.mkdtemp(prefix='partA-test-')` | `root`: the folder for the test data. It is the kept folder, or a new temporary folder whose name starts with `partA-test-`. |
| 409 | `    if keep:` | Only with `--keep`. |
| 410 | `        shutil.rmtree(root, ignore_errors=True); os.makedirs(root)` | Deletes the kept folder with all its content, when it exists, and creates it new. So a folder that is named with `--keep` loses what it held before. |
| 411 | `    try:` | Starts a block whose end, lines 429 to 431, runs also after a failed test. |
| 412 | `        check_two_groups(); check_units()` | First the tests that need no folder: the two groups (line 314) and the single functions (line 325). |
| 413 | `        f1 = build_set1(os.path.join(root, 'set1')); s1 = A.analyse(f1)` | Builds data set 1 in the folder `set1` and runs the analysis on its three folders. |
| 414 | `        json.dump(s1, open(os.path.join(root, 'set1', 'partA-summary.json'), 'w'), indent=1)` | Writes the summary of set 1 to `partA-summary.json` in `set1`. |
| 415 | `        s1 = json.load(open(os.path.join(root, 'set1', 'partA-summary.json')))     # the page reads the json, so test that path` | Reads the summary back from the json file. By the comment the page generator reads the json file, so the test uses that path too. |
| 416 | `        check_set1(s1); check_set1_a4_first_count(s1)` | Runs the tests of the json values of set 1 (line 200, line 272). |
| 417 | `        h1 = H.build(s1, BANNER); open(os.path.join(root, 'set1', 'partA-result.html'), 'w').write(h1); check_page(h1, s1); check_set1_more(s1, h1)` | Builds the page of set 1 with the banner, writes it to `partA-result.html`, and runs the page rules (line 392) and the tests of line 351. |
| 418 | `        f2 = build_set2(os.path.join(root, 'set2')); s2 = A.analyse(f2)` | Builds data set 2 in the folder `set2` and runs the analysis on it. |
| 419 | `        json.dump(s2, open(os.path.join(root, 'set2', 'partA-summary.json'), 'w'), indent=1)` | Writes the summary of set 2 to its json file. |
| 420 | `        s2 = json.load(open(os.path.join(root, 'set2', 'partA-summary.json')))` | Reads it back from the json file. |
| 421 | `        check_set2(s2)` | Runs the tests of the json values of set 2 (line 278). |
| 422 | `        h2 = H.build(s2, BANNER); open(os.path.join(root, 'set2', 'partA-result.html'), 'w').write(h2); check_page(h2, s2); check_set2_more(s2, h2)` | Builds the page of set 2, writes it, and runs the page rules and the tests of line 378. |
| 423 | `        assert 'do not fall into two groups' in h2 or 'does not fall into two groups' in h2` | The page of set 2 must say that the q values do not fall into two groups, in one of two forms of that sentence. |
| 424 | `        # an empty folder must give a page that says what is missing, not an error` | Comment: an empty folder must give a page that says what is missing, and not an error. |
| 425 | `        e = os.path.join(root, 'set3', 'partA-20260103T000000Z'); os.makedirs(e)` | `e`: a new empty result folder in the folder `set3`. |
| 426 | `        s3 = json.loads(json.dumps(A.analyse([e]))); h3 = H.build(s3, BANNER); check_page(h3, s3)` | Runs the analysis on the empty folder, passes the summary through json text, builds the page and runs the page rules. This proves that both scripts work without any data, and that the page then names every step as missing. |
| 427 | `        open(os.path.join(root, 'set3', 'partA-result.html'), 'w').write(h3)` | Writes the page of the empty folder to `partA-result.html` in `set3`. |
| 428 | `        print('all tests passed' + (f'; files kept in {root}' if keep else ''))` | All tests passed: prints `all tests passed`, and with `--keep` also the folder that holds the files. |
| 429 | `    finally:` | The part that runs in every case, also after an error. |
| 430 | `        if not keep:` | Only without `--keep`. |
| 431 | `            shutil.rmtree(root, ignore_errors=True)` | Deletes the temporary folder with all the test data. |
| 434 | `if __name__ == '__main__':` | This test is true when the file is started as a program. |
| 435 | `    main()` | Runs `main`. A failed `assert` ends the program with an error message and an exit status other than 0. |
