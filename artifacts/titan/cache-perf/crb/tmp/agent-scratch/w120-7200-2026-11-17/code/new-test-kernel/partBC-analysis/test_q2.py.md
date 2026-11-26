# `test_q2.py` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/test_q2.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 424 lines, 28238 bytes).
- sha256 of the source when this page was built: `da75d50f7065d56240fc22a6d0664ca972ebaacd2641edfb27d0cdfe079cb1bc`.

## Short version: purpose

`test_q2.py` tests the page builder `make_q2_html.py`. It writes invented result folders in the row format of the runner, builds pages from them, and checks the words of the hypotheses and the text of the pages. The rates are invented in a way that gives each decision rule a known result.

## Words used here

- **Page builder**: the file `make_q2_html.py`. It builds the HTML result page for question Q2 from result folders. The tests import it under the short name `Q`.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It names the questions, the hypotheses, eleven rules for the measurements, and the steps [Ref3].
- **Handoff**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the rows that the runner prints. Its sections B.4 and B.10 define the irregular interval and the decision rules [Ref2].
- **Q2**: the second question of the plan, about 64 threads on mesh 0 and 56 threads on mesh 1 with one 256 MiB buffer per thread: why the old read kernel has a higher total than the new one, and why the write kernels give several separate totals.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read, new read, asm read**: the names that the page builder prints for the kernels `oldread`, `read` and `asmread`. `asmread2` is a second copy of `asmread`. The write kernels are `oldwrite`, `write`, `asmwrite` and `asmwrite2`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC. The tests write folders of the same form on the machine on which they run.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Invented session**: the result folders that the function `session` writes for one session. No measurement stands behind them.
- **Session of Parts B and C**: one run of all steps of Parts B and C of the plan. Rule 10 of the plan asks for at least 2 sessions some hours apart. On this page "session" has this meaning.
- **Step**: one measurement of the plan with its own result folder. The steps of Q2 are B7 (read kernels in 8 settings), B10 (write kernels in 8 settings), B8 (read kernels with fewer threads on mesh 1), B5 (old read against loops with added `nop` instructions), B9 (one and two buffers per thread) and C3 (the sequences of B7 and B5 with counters).
- **Hypotheses H7a to H11**: H7a: the stop method and the short interval make a part of the difference. H7b: the common start makes a part of it. H8: a loop that only loads reaches the uniform state at a lower thread count than old read. H9a: the second buffer per thread changed the pattern of old read. H9b: old read differs between days or sessions for a reason other than the kernel. H10: the memory system fetches lines that the loop does not consume. H11: the higher write totals come from the threads of one mesh.
- **B5 statement**: the statement that step B5 of the plan tests: vector adds are needed for the split pattern of old read at 64+56 threads [Ref3]. The page builder words it as "vector adds are needed for the pattern and total of old read".
- **Header line**: the line that the run script writes into the csv file before each process. It starts with `-- step` and holds the step, the tag, the binary, the waited seconds, the load averages, the logins, the time and the arguments.
- **Tag**: the name of a process, for example `pass-500-common-p1`.
- **`env.txt`, `launches.txt`**: two files of a result folder. `env.txt` holds a reading of the machine state at the start and at the end of the step. `launches.txt` holds a load reading and a process list before each process.
- **T row, P row, C row**: rows of the csv file. A T row holds for one thread and one interval the CPU, the bytes, the elapsed time, three times of the thread, the passes and the flag `late`. A P row holds the page state of one buffer. A C row holds times and counter values of one thread and interval.
- **Setting**: one combination of stop method (`pass` or `common`), shortest interval length in ms and start (`common` or `offset`), written as in `pass/500/common`.
- **Reproduction condition**: the setting `pass/500/common`.
- **Total, `M_hist`**: the bytes of all threads of one interval divided by the longest elapsed time of a thread, in GB/s.
- **D**: the total of old read minus the total of new read, one value per process.
- **A/A spread**: the largest absolute difference between the two copies of one loop (`asmread2` minus `asmread`) over the processes of one setting.
- **Resolved**: D of a setting is resolved when its absolute median over the processes is above the A/A spread and every D has the same sign. A setting needs 4 processes with a value. If not, it is `not observed`.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval.
- **Pattern labels**: the labels `split` (q below 0.65) and `uniform` (q above 0.85) of the handoff. By decision 2 of the user of 2026-11-13 they are not used.
- **Label rule**: a rule of the analysis script that needs the pattern labels.
- **The five words**: the words that rule 11 of the plan allows for a result: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`.
- **Flag**: the result of one session for the prediction of a hypothesis: `fail` (it failed), `hold` (it held), `not observed` or `not resolved`.
- **Plan word**: `supported` or `contradicted`, the words of the plan for H8 and H11. For H11 the page builder prints one of them in brackets after its own word.
- **Page rules**: four rules of the page builder for the words of H8, H9a, H9b, H10, H11 and the B5 statement. They are not rules of the plan.
- **Open for the user**: the mark of the page builder for a judgment between two readings of a rule that the page does not make.
- **Late thread, irregular interval**: a T row with the flag `late` marks a thread that started late. An interval with such a thread is irregular and is not used.
- **2 % check**: rule 7 of the plan for whole passes: one pass may take at most 2 % of the interval, so each thread needs at least 50 passes.
- **Analysis script**: the file `analyze_bwx.py`. The page builder uses it to read the rows and to apply the decision rules.
- **Model**: the dictionary of computed values that the function `compute` of the page builder returns.
- **Unix time**: the seconds counted from 1970-01-01 00:00 UTC.
- **`assert`**: a Python statement that stops the program with an error when its condition is false.

## Main flow

1. The helpers are defined: the class `Folder` writes one invented result folder, and `session` writes the folders of one session with chosen effects (lines 26 to 147).
2. `check_page_rules` holds checks of the user's rules for a page: no outside resource, a Short version of at most three sentences, the place of the reference indexes, and text that stays inside each drawing (lines 170 to 216). The tests 1, 2, 5, 7 and 10 call it for one page each. The 7 other pages of the tests do not go through it.
3. Test 1 builds a page from one session and proves that it never says `rejected` (lines 231 to 251).
4. Test 2 adds a second equal session and proves that `rejected` then appears, with the other reading and the mark for the user (lines 253 to 275).
5. Test 3 gives the stop method a real effect and proves that only H7a changes its word (lines 277 to 287).
6. Test 4 proves that results of the label rule do not reach the words of the page (lines 289 to 309).
7. Tests 5 to 7 cover one late thread, the three cases of H11, and missing steps (lines 311 to 347).
8. Tests 8 and 9 cover the command line with a folder of another step, and the load section (lines 349 to 363).
9. Test 10 covers a busy process of another account, the times of the sessions, and a deviation of the setting (lines 365 to 393).
10. Test 11 covers the 2 % check, the sign of a rounded zero, the common axis of B8, and H11 over two sessions (lines 395 to 416).
11. The temporary folder is deleted, and the script prints that all tests passed (lines 418 to 420).

## Behavior a reader must know

- The tests run the real analysis script through the page builder. So they test both together. The import in line 12 needs the folders that `make_q2_html.py` looks in.
- No test reads a real result folder or contacts CRB. Every number in the folders is invented (lines 44 to 63).
- Every invented T row of an interval has the same elapsed time and the same end time. So the end skew is 0, and the total `M_hist` equals the sum of the thread rates (line 59).
- A failed `assert` stops the run at once with a Python error. The later tests do not run. The temporary folder is not deleted either: the delete stands at the end of `main` (lines 418 to 419).
- With `--keep DIR` the folder `DIR` is first deleted with all its content and then filled (line 223).
- Without `--keep` the invented folders lie in a new temporary folder whose name starts with `q2test-` (line 221).
- Test 6 checks for one session with two faster meshes only that the word is not `rejected`. It does not check the plan word of that page (line 330). By the code of the function `hypotheses` of the page builder, that page gets the word `not rejected` with the plan word `supported`. For two such sessions the test expects the plan word `contradicted` (line 332). So the plan word of the one-session page does not fit its data, and no test notices it.
- The check of the text boxes in the drawings uses an estimated text width. No browser measures the text (line 202).

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/test_q2.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (424 lines, 28238 bytes, sha256 `da75d50f7065d56240fc22a6d0664ca972ebaacd2641edfb27d0cdfe079cb1bc`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description, imports and constants (lines 1 to 25)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_q2.py [--keep DIR]: tests of make_q2_html.py on synthetic result folders in the row format of handoff.md B.3.` | Starts the description: the file tests `make_q2_html.py` on invented result folders. Their rows have the format of section B.3 of the handoff. With the option `--keep DIR` the invented folders and the pages that the tests wrote stay in the folder `DIR`. |
| 4 | `Each test states WHY its rule matters. The synthetic machine has 4 threads on mesh 0 (CPUs 0 to 3) and 4 on` | Continues the description: each test says why its rule matters. The invented machine has 4 threads on mesh 0, on the CPUs 0 to 3, and 4 threads on mesh 1. |
| 5 | `mesh 1 (CPUs 64 to 67). Rates are invented. They only steer the decision rules.` | Continues the description: the threads of mesh 1 run on the CPUs 64 to 67. The rates are invented. Their only purpose is to lead the decision rules to a known result. |
| 6 | `Run: python3 test_q2.py` | Continues the description: the command that runs the tests. |
| 7 | `"""` | Ends the description. |
| 8 | `import html, os, re, shutil, sys, tempfile, time` | Imports seven modules of the Python standard library: `html`, `os`, `re` (regular expressions), `shutil` (to delete a folder tree), `sys`, `tempfile` (to make a temporary folder) and `time`. |
| 10 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this file. |
| 11 | `sys.path.insert(0, HERE)` | Puts that folder at the front of the list of folders in which Python looks for a module. |
| 12 | `import make_q2_html as Q  # noqa: E402` | Imports the page builder `make_q2_html.py` under the short name `Q`. That file imports the analysis script and the generator of the Part A page, so both must be found too. |
| 14 | `MIB = 1 << 20` | `MIB`: 1048576, the number of bytes of 1 MiB. |
| 15 | `BOOT = 1790000000          # boot time of the synthetic machine, seconds since 1970` | `BOOT`: the time at which the invented machine was started, as Unix time (seconds counted from 1970-01-01 00:00 UTC). The uptime line of `env.txt` is computed from it. |
| 16 | `SETTINGS = [(st, ms, sa) for st in ('pass', 'common') for ms in (500, 6000) for sa in ('common', 'offset')]` | `SETTINGS`: the 8 settings of B7 as tuples of stop method, interval length in ms and start: `pass` or `common`, 500 or 6000, `common` or `offset`. |
| 17 | `B7SEQ = 'oldread,read,asmread,asmread2,asmread2,asmread,read,oldread'` | `B7SEQ`: the kernel sequence of step B7, the step that compares old read with new read at the full thread count in 8 timing settings. The sequence: old read, new read and the two copies of asm read, and then the same four in the reverse order. |
| 18 | `B10SEQ = 'oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite'` | `B10SEQ`: the kernel sequence of step B10, the step with the four write kernels in 8 timing settings. It has the same pattern as `B7SEQ`. |
| 19 | `B5SEQ = 'oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2'` | `B5SEQ`: the kernel sequence of step B5, the step that compares old read with load-only loops with added `nop` instructions. The sequence: old read, new read, `read_sparse`, the four `nop` variants and the two copies of asm read. |
| 22 | `def cpus(a, b):` | Starts the function `cpus`. It gives the CPU list of a process with `a` threads on mesh 0 and `b` threads on mesh 1. |
| 23 | `    return list(range(a)) + list(range(64, 64 + b))` | Returns the CPUs 0 to `a - 1` followed by the CPUs 64 to `64 + b - 1`. |

### Class `Folder`: writes one invented result folder (lines 26 to 69)

| Line | Source | Explanation |
|---:|---|---|
| 26 | `class Folder:` | Starts the class `Folder`. One object writes one result folder. |
| 27 | `    """One result folder: <step>.csv, env.txt, launches.txt, stderr.txt."""` | Description of `Folder`: the folder holds the csv file of the step, `env.txt`, `launches.txt` and `stderr.txt`, like a result folder of the run script. |
| 29 | `    def __init__(self, root, name, step, t0=None, busy=None):` | Starts the method that sets up a new folder. `root` and `name` give its place, `step` its step. |
| 30 | `        """t0: start of the folder in seconds since 1970 (it ends 590 s later). busy: one line of ps for the first launch."""` | Description: `t0` is the start time of the folder as Unix time, and the folder ends 590 s later. `busy` is one line of a `ps` list for the first launch. |
| 31 | `        self.dir = os.path.join(root, name); self.step = step; self.n = 0; self.busy = busy` | Keeps the path of the folder, the step, a counter `n` of the processes (0 at first) and the line `busy`. |
| 32 | `        os.makedirs(self.dir)` | Creates the folder. |
| 33 | `        self.csv = open(os.path.join(self.dir, step + '.csv'), 'w')` | Opens the csv file of the step, for example `B7.csv`, for writing. |
| 34 | `        self.la = open(os.path.join(self.dir, 'launches.txt'), 'w')` | Opens `launches.txt` for writing. |
| 35 | `        ts = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))` | `ts`: a small function that prints a Unix time in the form of the run script, such as `2026-11-14T02:43:52Z`. |
| 36 | `        a = ts(t0) if t0 is not None else '2026-01-01T00:00:00Z'; b = ts(t0 + 590) if t0 is not None else '2026-01-01T00:10:00Z'` | `a` and `b`: the start time and the end time of the folder as text. With `t0` given, the end is 590 s after the start. Without it, the two fixed times `2026-01-01T00:00:00Z` and `2026-01-01T00:10:00Z` are used. |
| 37 | `        with open(os.path.join(self.dir, 'env.txt'), 'w') as fh:` | Opens `env.txt` for writing. |
| 38 | `            fh.write(f'## host=test utc={a} loadavg=0.50 1.00 1.00 1/900 123 logins=0 step={step} steps={step}\n'` | Writes the start line: host `test`, the start time, a load average of the last minute of 0.50 with 1 runnable task of 900, 0 logins, and the step as the only step of the visit. |
| 39 | `                     + (f'## uptime={t0 - BOOT:.2f} MemFree: 1 kB\n' if t0 is not None else '')` | With `t0` given: also writes the uptime line. The uptime is `t0` minus `BOOT`, so every folder gives the same start time of the machine. |
| 40 | `                     + '## settings: STOP_AT=none BWX_STOP=common BWX_START=common BWX_MIN_MS=6000 BWX_EVENTS=cycles=0x11\n'` | Writes a settings line: no stop time, common stop, common start, 6000 ms and one event code. |
| 41 | `                     f'## end utc={b} loadavg=7.50 3.00 1.00 1/900 456\n')` | Writes the end line: the end time and a load average of the last minute of 7.50. |
| 42 | `        open(os.path.join(self.dir, 'stderr.txt'), 'w').close()` | Creates an empty file `stderr.txt`. |
| 44 | `    def proc(self, tag, cp, seq, rounds, stop, ms, start, rate, extra='', late=None, count=False):` | Starts the method `proc`. It writes one invented process: its block in `launches.txt`, its header line and its rows. `cp` is the CPU list, `seq` the sequence, and `stop`, `ms` and `start` the setting. `extra` is more option text. `count` adds counter rows. |
| 45 | `        """rate(kernel, cpu, round, pos) -> GB/s of one thread. late = (round, pos, tid) marks one late thread."""` | Description: `rate` is a function that gives the rate of one thread in GB/s for a kernel, a CPU, a round and a position. `late` names one round, position and thread that gets the flag `late`. |
| 46 | `        self.n += 1` | Counts the process. |
| 47 | `        load = '99.00 50.00 20.00' if self.n > 1 else '0.50 1.00 1.00'` | `load`: the three load averages of the readings: 0.50, 1.00 and 1.00 for the first process of the folder, and 99.00, 50.00 and 20.00 for every later one. The high values stand for the load directly after one of our own processes, which test 9 needs. |
| 48 | `        self.la.write(f'== {self.step}.csv {tag} utc 00:00:{self.n:02d} loadavg {load} 1/900 logins 0\n%CPU USER     COMMAND\n'` | Writes the block of the launch to `launches.txt`: the line that starts with `==`, with the csv name, the tag, a time, the load averages, 1 runnable task of 900 and 0 logins, and then the heading line of `ps`. |
| 49 | `                      + (self.busy + '\n' if self.busy and self.n == 1 else '') + ' 0.3 tester   bash\n 0.1 root     kworker/0:1-events\n')` | Continues the block: for the first process the line `busy` when one was given, then a `bash` process of the account `tester` at 0.3 % and a `kworker` process of `root` at 0.1 %. So the page builder takes `tester` as our own account. |
| 50 | `        args = f'--threads {len(cp)} --cpus x --bytes 256M --seq {seq} --rounds {rounds} --stop {stop} --min-ms {ms} --start {start}{extra}' + (' --count' if count else '')` | `args`: the arguments of the invented runner call: the thread count, a CPU list that is the letter `x`, 256 MiB per thread, the sequence, the rounds, the stop method, the interval length, the start, the text `extra`, and `--count` when counters are wanted. |
| 51 | `        w = self.csv.write` | `w`: a short name for the function that writes text to the csv file. |
| 52 | `        w(f'-- step {self.step} tag {tag} binary bwx waited_s 0 loadavg {load} 1/900 logins 0 utc 00:00:{self.n:02d} args {args}\n# bandwidth: synthetic\n')` | Writes the header line of the process, with a wait of 0 s and the same load values as the block of the launch, and one comment line. |
| 53 | `        el = ms / 1000.0` | `el`: the length of every interval in s, the interval length `ms` divided by 1000. |
| 54 | `        for r in range(rounds):` | Loop over the rounds. |
| 55 | `            for i, k in enumerate(seq.split(',')):` | Loop over the positions of the sequence. `k` is the kernel. |
| 56 | `                for tid, c in enumerate(cp):` | Loop over the threads. `tid` is the thread number and `c` its CPU. |
| 57 | `                    b = int(rate(k, c, r, i) * 1e9 * el)` | `b`: the bytes of this thread in this interval: its rate in GB/s times 1e9 times the interval length, as a whole number. |
| 58 | `                    flag = 'late' if late == (r, i, tid) else '-'` | `flag`: `late` for the one thread that `late` names, and `-` for every other thread. |
| 59 | `                    w(f'T,{r},{i},{k},{tid},{c},{b},{el:.6f},1.000000,1.000000,{1 + el:.6f},{b / (256 * MIB):.3f},{flag}\n')` | Writes the T row. The elapsed time is `el` for every thread. The scheduled start and the real start are 1 s and the end is `1 + el` s for every thread, so the end skew is 0. The passes are the bytes divided by 256 MiB. |
| 60 | `                    if count:` | The next two lines run only when counters are wanted. |
| 61 | `                        lines = b / 64` | `lines`: the bytes divided by 64. |
| 62 | `                        w(f'C,{r},{i},{k},{tid},{c},{int(el * 1e9)},{int(el * 1e9)},{int(el * 0.995e9)},{int(el * 2.8e9)},{int(lines * 3)},{int(lines * 0.95)},{int(lines)},{int(lines * 0.1)}\n')` | Writes the C row. The enabled time and the running time are the interval length in ns. The CPU time is 99.5 % of the interval length. The five counts are 2.8e9 cycles per second of the interval, 3 instructions per line, 0.95 L1 refills per line, 1 L2 refill per line and 0.1 last-level read misses per line. |
| 63 | `                    w(f'P,{r},{i},{tid},a,262144,262144,1,0,0,0\n')` | Writes a P row for the buffer `a` of the thread: 262144 kB in all and 262144 kB on 2 MiB pages, so full coverage. |
| 65 | `    def close(self):` | Starts the method `close`. |
| 66 | `        self.csv.close(); self.la.close()` | Closes the csv file and `launches.txt`. |
| 67 | `        return self.dir` | Returns the path of the folder. |

### `session`: writes the folders of one invented session (lines 70 to 149)

| Line | Source | Explanation |
|---:|---|---|
| 70 | `def session(root, name, steps=('B7', 'B10', 'B8', 'B5', 'B9', 'C3'), stop_effect=0.0, late=False, sparse_equal=False, b10='flat', old_m0=5.0, b9_two_uniform=False,` | Starts the function `session`. It writes the result folders of one session below `root`. The options choose the steps and switch single effects on. |
| 71 | `            boost=None, later_start='common', clock0=None, c3_busy=None):` | Continues the list of options. |
| 72 | `    """Writes the folders of one session and returns their paths.` | Starts the description: the function writes the folders of one session and returns their paths. |
| 73 | `    stop_effect: GB/s per mesh-0 thread that old read loses with the common stop (a real effect of the stop method).` | `stop_effect`: the GB/s that old read loses per mesh-0 thread with the common stop. This is a real effect of the stop method in the invented data. |
| 74 | `    b10: 'flat' (no higher interval), 'mesh1' (one interval of old write has a faster mesh 1), 'both' (both meshes faster).` | `b10`: `flat` means that no interval has a higher total. `mesh1` means that one interval of old write has a faster mesh 1. `both` means that both meshes are faster in it. |
| 75 | `    boost: a B7 setting (stop, ms, start) in which old read gains 0.5 GB/s per mesh-0 thread, so that the handoff rule selects it.` | `boost`: a B7 setting in which old read gains 0.5 GB/s per mesh-0 thread. The handoff rule then selects that setting. |
| 76 | `    later_start: the start mode of B8, B5 and B9. clock0: start of the session in seconds since 1970 (one folder per 600 s).` | `later_start`: the start mode of B8, B5 and B9. `clock0`: the start of the session as Unix time. Each folder starts 600 s after the one before. |
| 77 | `    c3_busy: a ps line of another account at the first launch of C3."""` | `c3_busy`: a `ps` line of another account for the first launch of C3. The line ends the description. |
| 78 | `    out, pn, fn = [], [0], [0]` | `out`: the paths of the folders. `pn` and `fn`: two counters. Each is a list with one number. An inner function can change the number inside such a list. |
| 80 | `    def Fo(nm, step, busy=None):` | Starts the inner function `Fo`. It makes the next folder of the session. |
| 81 | `        fn[0] += 1` | Counts the folder. |
| 82 | `        return Folder(root, nm, step, t0=None if clock0 is None else clock0 + 600 * (fn[0] - 1), busy=busy)` | Returns a new `Folder`. With `clock0` given, its start time is `clock0` plus 600 s for each folder before it. |
| 84 | `    def eps():                                    # small deterministic A/A noise per process` | Starts the inner function `eps`. By the comment it gives a small A/A difference per process that is the same at every run of the tests. |
| 85 | `        pn[0] += 1` | Counts the process. |
| 86 | `        return ((pn[0] * 37) % 11 - 5) * 0.004` | Returns one of eleven values from -0.020 to +0.020 GB/s in steps of 0.004, chosen by the process number. |
| 88 | `    def reader(stop, ep, sparse=False):` | Starts the inner function `reader`. It returns the rate function of a process that runs read kernels. `ep` is the value of `eps` for the process. |
| 89 | `        def rate(k, c, r, i):` | Starts the rate function. |
| 90 | `            m0 = c < 64` | `m0`: true for a CPU below 64, so on mesh 0. |
| 91 | `            if k == 'oldread' or (sparse and k == 'read_sparse'):` | Tests whether the kernel is old read, or `read_sparse` when `sparse` asks that it behaves like old read. |
| 92 | `                return ((old_m0 - (stop_effect if stop == 'common' else 0)) if m0 else 2.8) + ep * 3 * (0.5 - (r + i) % 2)` | Then a mesh-0 thread gets `old_m0` GB/s (5.0 by default), minus `stop_effect` with the common stop, and a mesh-1 thread gets 2.8 GB/s. A small term of plus or minus 1.5 times `ep` follows, which changes its sign from one interval to the next. |
| 93 | `            return (2.6 if m0 else 2.4) + (ep if k == 'asmread2' else 0) + (0.002 * (i % 3) if k.startswith('read') else 0)` | Every other kernel gets 2.6 GB/s on mesh 0 and 2.4 GB/s on mesh 1. `asmread2` gets `ep` in addition, which makes the A/A difference. A kernel whose name starts with `read` gets up to 0.004 GB/s in addition, by its position. |
| 94 | `        return rate` | Returns the rate function. |
| 95 | `    C = cpus(4, 4)` | `C`: the CPU list of the full machine: 4 threads on each mesh. |
| 96 | `    if 'B7' in steps:` | The lines up to line 107 run only when B7 is wanted. |
| 97 | `        F = Fo(f'B7-{name}', 'B7')` | `F`: the folder of B7. |
| 98 | `        for p in range(1, 5):` | Loop over the process numbers 1 to 4. |
| 99 | `            for st, ms, sa in SETTINGS:` | Loop over the 8 settings. |
| 100 | `                lt = (0, 0, 2) if late and p == 1 and (st, ms, sa) == ('common', 500, 'common') else None` | `lt`: with the option `late`, process 1 of the setting `common/500/common` gets one late thread: thread 2 in round 0 at position 0. Every other process gets none. |
| 101 | `                rd = reader(st, eps())` | `rd`: the rate function of the process. |
| 102 | `                if boost == (st, ms, sa):` | Tests whether this is the setting that `boost` names. |
| 103 | `                    rd = (lambda base: lambda k, c, r, i: base(k, c, r, i) + (0.5 if k == 'oldread' and c < 64 else 0))(rd)` | Then the rate function is wrapped: old read gains 0.5 GB/s on every mesh-0 thread. |
| 104 | `                F.proc(f'{st}-{ms}-{sa}-p{p}', C, B7SEQ, 2, st, ms, sa, rd, late=lt)` | Writes the process: the B7 sequence, 2 rounds, the setting, and a tag of the form `pass-500-common-p1`. |
| 105 | `            for k in ('oldread', 'read', 'asmread', 'asmread2'):` | Loop over the four read kernels. |
| 106 | `                F.proc(f'single-{k}-p{p}', C, k, 3, 'pass', 500, 'common', reader('pass', eps()))` | Writes a process with this kernel alone: 3 rounds with the reproduction condition, and a tag that starts with `single`. |
| 107 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 108 | `    if 'B10' in steps:` | The lines up to line 119 run only when B10 is wanted. |
| 109 | `        F = Fo(f'B10a-{name}', 'B10')` | `F`: a folder named like `B10a` with the step B10. |
| 110 | `        for p in range(1, 5):` | Loop over the process numbers 1 to 4. |
| 111 | `            for st, ms, sa in SETTINGS:` | Loop over the 8 settings. |
| 112 | `                ep = eps()` | `ep`: the A/A value of the process. |
| 113 | `                def rate(k, c, r, i, ep=ep):` | Starts the rate function of the process. |
| 114 | `                    v = 1.0 + (ep if k == 'asmwrite2' else 0)` | `v`: 1.0 GB/s per thread, plus `ep` for `asmwrite2`. |
| 115 | `                    if k == 'oldwrite' and (r, i) == (1, 0) and b10 != 'flat' and (c >= 64 or b10 == 'both'):` | Tests whether this is the one higher interval: old write in round 1 at position 0, when `b10` is not `flat`. The test holds for the threads of mesh 1, and with `both` for all threads. |
| 116 | `                        v *= 1.5` | Then the rate is 1.5 times as high. |
| 117 | `                    return v` | Returns the rate. |
| 118 | `                F.proc(f'{st}-{15000 if ms == 6000 else 500}-{sa}-p{p}', C, B10SEQ, 2, st, 15000 if ms == 6000 else 500, sa, rate)` | Writes the process with the B10 sequence and 2 rounds. The long interval is 15000 ms in the place of 6000 ms. |
| 119 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 120 | `    if 'B8' in steps:` | The lines up to line 129 run only when B8 is wanted. B8 is the step with several thread counts on mesh 1. |
| 121 | `        F = Fo(f'B8-{name}', 'B8')` | `F`: the folder of B8. |
| 122 | `        for p in (1, 2):` | Loop over the process numbers 1 and 2. |
| 123 | `            for b in (2, 3, 4):` | Loop over three thread counts on mesh 1: 2, 3 and 4. |
| 124 | `                def rate(k, c, r, i, b=b):` | Starts the rate function of the process. |
| 125 | `                    if k == 'oldread':                       # by the label rule: split at 2 and 3, uniform at 4` | Tests whether the kernel is old read. By the comment the label rule gives it `split` at 2 and 3 threads and `uniform` at 4. |
| 126 | `                        return 2.6 if b == 4 else (5.0 if c < 64 else 2.8)` | Old read: every thread has 2.6 GB/s at 4 mesh-1 threads. Below that, mesh 0 has 5.0 and mesh 1 has 2.8 GB/s. |
| 127 | `                    return 2.6 if b >= 3 else (5.0 if c < 64 else 2.8)      # asm read: split at 2, uniform at 3 and 4` | Asm read and its copy: every thread has 2.6 GB/s from 3 mesh-1 threads on, and the two unequal rates at 2. So by the label rule asm read changes at a lower count than old read. |
| 128 | `                F.proc(f'4+{b}-p{p}', cpus(4, b), 'oldread,asmread,asmread2,asmread2,asmread,oldread', 1, 'common', 6000, later_start, rate)` | Writes the process: 4 threads on mesh 0 and `b` on mesh 1, the B8 sequence, 1 round, common stop, 6000 ms, and the start `later_start`. |
| 129 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 130 | `    if 'B5' in steps:` | The lines up to line 134 run only when B5 is wanted. |
| 131 | `        F = Fo(f'B5-{name}', 'B5')` | `F`: the folder of B5. |
| 132 | `        for p, seq in enumerate((B5SEQ, ','.join(reversed(B5SEQ.split(','))), B5SEQ, ','.join(reversed(B5SEQ.split(',')))), 1):` | Loop over 4 processes: the B5 sequence, the reversed sequence, and both once more. |
| 133 | `            F.proc(f'b5-{p}', C, seq, 1, 'common', 6000, later_start, reader('pass', eps(), sparse=sparse_equal))` | Writes the process: 1 round, common stop, 6000 ms and the start `later_start`. With `sparse_equal`, `read_sparse` gets the rates of old read. |
| 134 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 135 | `    if 'B9' in steps:` | The lines up to line 141 run only when B9 is wanted. B9 is the step with one buffer and with two buffers per thread. |
| 136 | `        F = Fo(f'B9-{name}', 'B9')` | `F`: the folder of B9. |
| 137 | `        for p in (1, 2, 3):` | Loop over the process numbers 1 to 3. |
| 138 | `            F.proc(f'onebuf-p{p}', C, 'oldread', 3, 'common', 6000, later_start, reader('pass', eps()))` | Writes a process with one buffer per thread: old read alone, 3 rounds. |
| 139 | `            two = (lambda k, c, r, i: 2.6) if b9_two_uniform else reader('pass', eps())` | `two`: the rate function of the process with two buffers. With `b9_two_uniform` every thread gets 2.6 GB/s. If not, it gets the same rates as with one buffer. |
| 140 | `            F.proc(f'twobuf-p{p}', C, 'oldread', 3, 'common', 6000, later_start, two, extra=' --two-buffers')` | Writes the process with the option `--two-buffers`. |
| 141 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 142 | `    if 'C3' in steps:` | The lines up to line 146 run only when C3 is wanted. C3 is the step that repeats sequences with core counters. |
| 143 | `        F = Fo(f'C3-{name}', 'C3', busy=c3_busy)` | `F`: the folder of C3, with the `ps` line `c3_busy` for its first launch. |
| 144 | `        for p in (1, 2):` | Loop over the process numbers 1 and 2. |
| 145 | `            F.proc(f'common-6000-common-p{p}', C, B7SEQ, 2, 'common', 6000, 'common', reader('pass', eps()), count=True)` | Writes a process with counter rows: the B7 sequence, 2 rounds, in the setting `common/6000/common`. |
| 146 | `        out.append(F.close())` | Closes the folder and keeps its path. |
| 147 | `    return out` | Returns the paths of the folders. |

### Small helpers: `page`, `hyp`, `visible` and `e_in` (lines 150 to 169)

| Line | Source | Explanation |
|---:|---|---|
| 150 | `def page(sessions):` | Starts the function `page`. `sessions` gives the folders per session name. |
| 151 | `    m = Q.compute(sessions, offsets=Q.OFFSETS)` | `m`: the model that the page builder computes from the folders, with its default offsets file. |
| 152 | `    return m, Q.build(m)` | Returns the model and the HTML page that the page builder writes from it. |
| 155 | `def hyp(m):` | Starts the function `hyp`. |
| 156 | `    return {h['label']: h for h in m['hyp']}` | Returns the rows of the hypothesis table of a model as a dictionary by their label. |
| 159 | `def visible(h):` | Starts the function `visible`. It gives the text that a reader sees on the page. |
| 160 | `    h = re.sub(r'<style>.*?</style>', ' ', h, flags=re.S)` | Removes the style block. The pattern fits the opening `style` tag, any text up to the next closing `style` tag, and that tag. `re.S` lets the dot also fit a line break. |
| 161 | `    h = re.sub(r'<title>.*?</title>', ' ', h, flags=re.S)        # tooltips of chart markers and the page title` | Removes every `title` element in the same way. By the comment these are the tooltips of the chart markers and the page title. |
| 162 | `    return html.unescape(re.sub(r'<[^>]+>', ' ', h))` | Replaces every remaining tag, an opening angle bracket up to the next closing one, by a space. Then `html.unescape` turns the HTML codes of special characters back into the characters. |
| 165 | `def e_in(text, h):` | Starts the function `e_in`. |
| 166 | `    """True if the text stands on the page (escaped as the page escapes it)."""` | Description: true if the text stands on the page, escaped as the page escapes it. |
| 167 | `    return html.escape(text) in h` | Returns whether the escaped text occurs in the HTML text `h`. |

### `check_page_rules`: the rules of the user for every result page (lines 170 to 218)

| Line | Source | Explanation |
|---:|---|---|
| 170 | `def check_page_rules(h, m):` | Starts the function `check_page_rules`. `h` is the HTML page and `m` its model. The tests call it for five of their pages: one page each in the tests 1, 2, 5, 7 and 10 (line 243, line 273, line 321, line 347, line 391). The 7 other pages that the tests build do not go through these checks. |
| 171 | `    """The standing rules of the user for a result page."""` | Description: the standing rules of the user for a result page. |
| 172 | `    t = visible(h)` | `t`: the visible text of the page. |
| 173 | `    # WHY: the page must be readable with no network and must not follow a dark OS theme.` | Comment: why the next two checks matter: the page must be readable without a network, and it must not follow a dark theme of the operating system. |
| 174 | `    assert 'http' not in h and '<script' not in h and '<link' not in h and '<img' not in h, 'external resource or script'` | Proves that the page loads nothing from outside: it holds no `http` address and no `script`, `link` or `img` tag. If this fails, the message is `external resource or script`. |
| 175 | `    assert 'color-scheme:light' in h and 'background:#ffffff' in h and 'prefers-color-scheme' not in h` | Proves the light theme: the style sets `color-scheme:light` and a white background, and it has no rule for `prefers-color-scheme`. |
| 176 | `    # WHY: a newcomer reads only the Short version. More than three sentences is a defect by the user's rule.` | Comment: why: a newcomer reads only the Short version, and by the rule of the user more than three sentences are a defect. |
| 177 | `    sv = visible(re.search(r'<b>Short version\.</b>(.*?)</p>', h, re.S).group(1))` | `sv`: the visible text of the Short version. The pattern takes the text between the bold words `Short version.` and the end of that paragraph. Group 1 holds it. |
| 178 | `    assert len(re.findall(r'[.!?]["\')]?(?:\s\|$)', sv.strip())) <= 3, sv` | Proves that the Short version has at most three sentences. The pattern counts each sentence end: a full stop, exclamation mark or question mark, an optional closing quote or bracket, and then a space or the end of the text. |
| 179 | `    # WHY: a newcomer has not met the hypothesis labels yet. The Short version must do without them.` | Comment: why: a newcomer has not met the hypothesis labels yet, so the Short version must do without them. |
| 180 | `    assert not re.search(r'\bH\d', sv) and 'resolved' not in sv, sv` | Proves that the Short version holds no hypothesis label (the letter H directly before a digit) and not the word `resolved`. |
| 181 | `    # WHY (user's rule 5): a reference index stands at the end of the sentence, before its full stop, never after it.` | Comment: why, by rule 5 of the user: a reference index stands at the end of the sentence, before its full stop, never after it. |
| 182 | `    bad = re.search(r'[.!?]\s*\[Ref\d+\]', t.split('References')[0])` | `bad`: the first place in the visible text before the word `References` where a reference index follows a sentence end. The pattern fits a full stop, exclamation mark or question mark, optional spaces, and an index in square brackets. |
| 183 | `    assert not bad, t[max(0, bad.start() - 80):bad.end() + 20]` | Proves that there is no such place. On failure the message shows the text around it. This tests the function `tidy_refs` of the page builder. |
| 184 | `    assert not re.search(r'(\[Ref\d+\])\1', h), 'a reference is repeated in one group'` | Proves that no reference index stands twice directly one after the other. The pattern fits an index followed by the same index. |
| 185 | `    # WHY: every row of the hypothesis table must show what the analysis rule gives as it stands, next to the word of the page.` | Comment: why: every row of the hypothesis table must show the unchanged output of the analysis rule, next to the word of the page. |
| 186 | `    for x in m['hyp']:` | Loop over the rows of the hypothesis table. |
| 187 | `        assert x['strict'] and x['meaning'] and x['short'], x['label']` | Proves that the row has the output of the analysis rule, a meaning in plain words and a short text. |
| 188 | `        assert x['open'] == '' or 'Open for the user' in h, x['label']` | Proves that a row with an open question appears on a page that holds the words `Open for the user`. |
| 189 | `    # WHY: semicolons join two claims in one sentence. The user's rule forbids them in prose.` | Comment: why: a semicolon joins two claims in one sentence, and the rule of the user forbids that in prose. |
| 190 | `    assert ';' not in t, t[max(0, t.index(';') - 80):t.index(';') + 40]` | Proves that the visible text holds no semicolon. On failure the message shows the text around the first one. |
| 191 | `    # WHY: a claim with a reference number that is not in the list cannot be checked by the reader.` | Comment: why: a reader cannot check a claim whose reference number is not in the list. |
| 192 | `    used = {int(x) for x in re.findall(r'\[Ref(\d+)\]', h.split('<h2 id="refs">')[0])}` | `used`: the reference numbers that occur before the reference section. The pattern fits `Ref` and digits in square brackets, and group 1 holds the digits. |
| 193 | `    listed = {int(x) for x in re.findall(r'<li>\[Ref(\d+)\]', h.split('<h2 id="refs">')[1])}` | `listed`: the reference numbers of the list items of the reference section. |
| 194 | `    assert used <= listed, used - listed` | Proves that every cited number is listed. |
| 195 | `    assert listed <= used, ('listed and never cited', listed - used)` | Proves that every listed number is cited. So the list holds no reference that the page never uses. |
| 196 | `    # WHY: a label that runs out of the drawing is cut off in the browser and the reader loses a number.` | Comment: why: a label that extends beyond the drawing is cut off in the browser, and the reader loses a number. |
| 197 | `    for mm in re.finditer(r'<svg viewBox="0 0 (\d+) (\d+)"(.*?)</svg>', h, re.S):` | Loop over the drawings of the page. The pattern fits an `svg` element. Groups 1 and 2 hold the width and the height from its `viewBox`. Group 3 holds its content. |
| 198 | `        W, H = int(mm.group(1)), int(mm.group(2))` | `W` and `H`: the width and the height as numbers. |
| 199 | `        for tx in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"([^>]*)>(.*?)</text>', mm.group(3), re.S):` | Loop over the text elements of the drawing. Groups 1 and 2 hold the position `x` and `y`. Group 3 holds the other attributes, and group 4 the text. |
| 200 | `            x, y, attr, s = float(tx.group(1)), float(tx.group(2)), tx.group(3), html.unescape(tx.group(4))` | Reads the four groups: the position as numbers, the attributes, and the text with its HTML codes turned back into characters. |
| 201 | `            size = 10 if 'font-size:10px' in attr else 12 if 'class="lab"' in attr else 11` | `size`: the font size of the text in px: 10 when the style says so, 12 for the class `lab`, and 11 in every other case. |
| 202 | `            w = len(s) * size * (0.60 if 'font-weight' in attr else 0.56)` | `w`: an estimate of the width of the text: the number of characters times the font size times 0.56, or times 0.60 for bold text. No browser measures it. |
| 203 | `            x0 = x - w if 'text-anchor="end"' in attr else x - w / 2 if 'text-anchor="middle"' in attr else x` | `x0`: the left end of the text. It depends on the anchor: the text ends at `x`, is centered at `x`, or starts at `x`. |
| 204 | `            assert x0 >= -6 and x0 + w <= W + 6, ('text outside the drawing', W, round(x0), round(x0 + w), s)` | Proves that the estimated text box lies inside the width of the drawing, with 6 units of tolerance at each side. |
| 205 | `            assert 0 < y <= H, ('text above or below the drawing', s)` | Proves that the text lies inside the height of the drawing. |
| 206 | `    # WHY: every step and every hypothesis label that the page uses must be defined in "Words used here".` | Comment: why: every step and every hypothesis label that the page uses must be defined in the list `Words used here`. |
| 207 | `    words = h.split('<h2 id="words">')[1].split('<h2')[0]` | `words`: the HTML text of that section, from its heading to the next heading of level 2. |
| 208 | `    for term in ('B7', 'B10', 'B8', 'B5', 'B9', 'C3', 'H7a', 'H7b', 'H8', 'H9a', 'H9b', 'H10', 'H11', 'M_hist', 'M_sum', 'A/A', 'CRB', '<b>q</b>', '<b>D</b>',` | Loop over terms that must be in the list: the six steps, the seven hypotheses, the two metrics, the A/A terms, CRB, q and D. |
| 209 | `                 '<b>Pattern</b>', 'Bounded prediction', 'Cell (B10)', 'Group (C3)', '<b>Visit</b>', 'Short run', 'Open for the user', 'Limit, band', 'UTC', '<code>ps</code>'):` | Continues the list of terms: among them the pattern, the bounded prediction, the cell of B10, the group of C3, the visit, the short run, UTC and `ps`. |
| 210 | `        assert term in words, term` | Proves that the section holds the term. |
| 211 | `    # WHY: "L1" and "L2" are cache levels on this page. A rule of the page must not carry the same name.` | Comment: why: L1 and L2 are cache levels on this page, so a rule of the page must not have the same name. |
| 212 | `    assert not re.search(r'\brule L\d', t) and 'est.' not in words` | Proves that the visible text never says `rule L` with a digit, and that the word list does not hold the abbreviation `est.`. |
| 213 | `    # WHY: the user asks for the load of every step.` | Comment: why: the user asks for the load of every step. |
| 214 | `    for s in m['sessions']:` | Loop over the sessions. |
| 215 | `        for st in m['S'][s]['steps']:` | Loop over the steps of the session that have a result. |
| 216 | `            assert st in m['S'][s]['load'], st` | Proves that the model has load readings for the step. |

### `main`: set-up and test 1 (one session) (lines 219 to 252)

| Line | Source | Explanation |
|---:|---|---|
| 219 | `def main():` | Starts the function `main`. It holds the 11 tests. A failed `assert` stops the run with an error at the first test that fails. |
| 220 | `    keep = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None` | `keep`: the folder named after `--keep` on the command line, or `None`. |
| 221 | `    root = keep or tempfile.mkdtemp(prefix='q2test-')` | `root`: the folder for the invented data: `keep`, or a new temporary folder whose name starts with `q2test-`. |
| 222 | `    if keep:` | The next line runs only with `--keep`. |
| 223 | `        shutil.rmtree(keep, ignore_errors=True); os.makedirs(keep)` | Deletes that folder with all its content when it exists, and creates it empty. |
| 224 | `    n = [0]` | `n`: a counter of the invented sessions, as a list with one number. |
| 226 | `    def mk(**kw):` | Starts the inner function `mk`. It makes one invented session. Its options go to `session`. |
| 227 | `        n[0] += 1` | Counts the session. |
| 228 | `        d = os.path.join(root, f'set{n[0]}'); os.makedirs(d)` | `d`: a new folder `setN` below `root`, with the number of the session. |
| 229 | `        return session(d, f's{n[0]}', **kw)` | Returns the paths of the result folders of the session. The session name is `sN` with the same number. |
| 231 | `    # ---- 1. One session, no factor changes D.` | Comment: test 1, one session in which no timing factor changes D. |
| 232 | `    # WHY: rule 11 of the plan gives "rejected" only for a prediction that failed in BOTH sessions. A page built from` | Comment: why: rule 11 of the plan gives `rejected` only for a prediction that failed in both sessions. |
| 233 | `    # one session must never print that word as a result, whatever the data show.` | Comment: so a page built from one session must never print that word as a result, whatever the data show. |
| 234 | `    a1 = mk()` | `a1`: the folders of an invented session with the default options. |
| 235 | `    m, h = page({'s1': a1})` | `m` and `h`: the model and the page built from this one session, named `s1`. |
| 236 | `    H = hyp(m)` | `H`: the rows of the hypothesis table by their label. |
| 237 | `    assert m['summary']['hypotheses']['H7a (B7, read)']['per_session'] == {'s1': 'fail'}` | Proves the starting point of the test: the analysis script gives the flag `fail` for H7a for read in the session. H7a says that the stop method and the short interval make a part of the read difference. So its prediction did fail in the invented data. |
| 238 | `    assert all(x['word'] != 'rejected' for x in m['hyp']), [(x['label'], x['word']) for x in m['hyp']]` | Proves that no row of the page has the word `rejected`. On failure the message lists the labels and words. |
| 239 | `    assert H['H7a, read']['word'] == 'not rejected' and H['H7a, read']['one_session'] and H['H7b, read']['one_session']` | Proves that H7a for read has the word `not rejected` together with the mark `one_session`, and that H7b for read has that mark too. H7b says that the common start makes a part of the read difference. The mark tells the reader that the prediction failed in this session. |
| 240 | `    assert 'Every "rejected" is impossible with one session' in h and 'prediction failed in this session' in h` | Proves that the page prints the sentence that every `rejected` is impossible with one session, and the note that the prediction failed in this session. |
| 241 | `    assert '<b>rejected</b>' not in h` | Proves that the word `rejected` never stands in bold on the page, the form of a result in the hypothesis table. |
| 242 | `    assert H['H9b']['word'] == 'not tested' and H['H10']['word'] == 'not tested'` | Proves that H9b and H10 are `not tested`. H9b says that old read differs between days or sessions for a reason other than the kernel, and it needs two sessions. H10 says that the memory system fetches lines that the loop does not consume, and it has no test in these steps. |
| 243 | `    check_page_rules(h, m)` | Runs the checks of `check_page_rules` on this page. |
| 244 | `    if keep:` | The next line runs only with `--keep`. |
| 245 | `        open(os.path.join(root, 'one-session.html'), 'w').write(h)` | Writes the page to the file `one-session.html` in the kept folder. |
| 246 | `    # WHY: text that interprets data must come from the data. The median D of the synthetic input is known:` | Comment: why: text that interprets data must come from the data. The median D of the invented input is known. |
| 247 | `    # 4 threads x (5.0 - 2.6) + 4 threads x (2.8 - 2.4) = 11.2 GB/s (new read carries up to +0.004 GB/s per thread).` | Comment: the expected value: 4 threads times (5.0 - 2.6) plus 4 threads times (2.8 - 2.4) is 11.2 GB/s. New read has up to 0.004 GB/s more per thread. |
| 248 | `    md = m['S']['s1']['B7']['res']['settings']['pass/500/common']['metrics']['M_hist']['median_D']` | `md`: the median D of the reproduction condition with `M_hist`, from the analysis result in the model. |
| 249 | `    assert abs(md - 11.2) < 0.05, md` | Proves that it is within 0.05 GB/s of 11.2 GB/s. So the value that the page builder works with follows from the bytes and times of the invented T rows. |
| 250 | `    assert Q.fx(md) in h` | Proves that the page prints this value in the number format of the page builder. |
| 251 | `    assert m['S']['s1']['B7']['res']['reproduced_in_either_way'] and 'is reproduced in the changed benchmark' in h` | Proves that the analysis found the difference reproduced, and that the page says that it is reproduced in the changed benchmark. |

### `main`: tests 2 to 4 (two sessions, a real effect, the pattern labels) (lines 253 to 310)

| Line | Source | Explanation |
|---:|---|---|
| 253 | `    # ---- 2. Two sessions with the same failed prediction.` | Comment: test 2, two sessions with the same failed prediction. |
| 254 | `    # WHY: without this case test 1 could pass with a generator that can never say "rejected" at all.` | Comment: why: without this case test 1 could pass with a page builder that can never say `rejected` at all. |
| 255 | `    a2 = mk()` | `a2`: the folders of a second invented session with the same options. |
| 256 | `    m2, h2 = page({'s1': a1, 's2': a2})` | `m2` and `h2`: the model and the page built from both sessions. |
| 257 | `    H2 = hyp(m2)` | `H2`: the rows of the hypothesis table. |
| 258 | `    assert H2['H7a, read']['word'] == 'rejected' and H2['H7b, read']['word'] == 'rejected', (H2['H7a, read'], H2['H7b, read'])` | Proves that H7a and H7b for read are `rejected` when the prediction failed in both sessions. |
| 259 | `    assert not H2['H7a, read']['one_session'] and 'Every "rejected" is impossible' not in h2` | Proves that the mark `one_session` is gone, and that the page no longer says that `rejected` is impossible. |
| 260 | `    # WHY (L3): H9b compares sessions. Equal synthetic sessions give overlapping ranges of q, so no difference was seen.` | Comment: why: H9b compares sessions. Two equal invented sessions give overlapping ranges of q, so no difference was seen. |
| 261 | `    assert H2['H9b']['word'] == 'not observed', H2['H9b']` | Proves that H9b is `not observed` in that case (page rule 3). |
| 262 | `    # WHY: the overlap test of H9b is a rule of this page, not of the plan, and user decision 2 gives "not resolved" for a` | Comment: why: the overlap test of H9b is a rule of the page and not of the plan, and user decision 2 gives `not resolved` for a rule that needs a label. |
| 263 | `    # rule that needs a label. The page must print both readings and leave the choice to the user.` | Comment: so the page must print both readings and leave the choice to the user. |
| 264 | `    assert H2['H9b']['open'] and 'not resolved' in H2['H9b']['other'] and 'not approved' in H2['H9b']['other']` | Proves that the row of H9b has an open question, and that its other reading names `not resolved` and says that the rule is not approved. |
| 265 | `    # WHY: "rejected" for H7b rests on changes that all lie inside their limit, which rule 11 also calls "not resolved".` | Comment: why: `rejected` for H7b is based on changes that all lie inside their limit, and rule 11 also calls that `not resolved`. |
| 266 | `    # The word of the analysis rule is printed, with the limits, the other reading, and the mark "open for the user".` | Comment: so the word of the analysis rule is printed with the limits, the other reading and the mark `open for the user`. |
| 267 | `    b = H2['H7b, read']` | `b`: the row of H7b for read. |
| 268 | `    assert '"rejected" (s1: fail, s2: fail)' in b['strict'] and b['open'] == '"rejected" or "not resolved"' and 'no resolved contribution' in b['other']` | Proves three things for that row: the output of the analysis rule holds `rejected` with the flag `fail` of both sessions, the open question names `rejected` or `not resolved`, and the other reading quotes the wording of the plan, `no resolved contribution`. |
| 269 | `    assert '8 of 8 lie inside the limit' in b['basis'] and 'could not show a contribution below its limit' in b['basis'], b['basis']` | Proves that the basis gives the numbers behind the word: all 8 changes that are not resolved lie inside their limit, and the test could not show a contribution below its limit. |
| 270 | `    assert h2.count('<b>open for the user</b>') == sum(1 for x in m2['hyp'] if x['open'])` | Proves that the page marks exactly as many rows in bold as `open for the user` as the model has rows with an open question. |
| 271 | `    # WHY: a "not rejected" word must not carry the mark of an open judgment.` | Comment: why: a `not rejected` word must not have the mark of an open judgment. |
| 272 | `    assert not H2['H10']['open'] and not H2['B5 statement']['open']` | Proves that the rows of H10 and of the B5 statement have no open question. |
| 273 | `    check_page_rules(h2, m2)` | Runs the checks of `check_page_rules` on the page with two sessions. |
| 274 | `    if keep:` | The next line runs only with `--keep`. |
| 275 | `        open(os.path.join(root, 'two-sessions.html'), 'w').write(h2)` | Writes the page to the file `two-sessions.html` in the kept folder. |
| 277 | `    # ---- 3. A real effect of the stop method in both sessions.` | Comment: test 3, a real effect of the stop method in both sessions. |
| 278 | `    # WHY: a factor that changes D by more than the control must keep H7a from being rejected, and must leave H7b alone.` | Comment: why: a factor that changes D by more than the control must keep H7a from being rejected, and must leave H7b alone. |
| 279 | `    b1, b2 = mk(stop_effect=2.0), mk(stop_effect=2.0)` | `b1` and `b2`: two invented sessions in which old read loses 2.0 GB/s per mesh-0 thread with the common stop. |
| 280 | `    m3, h3 = page({'s1': b1, 's2': b2})` | `m3` and `h3`: the model and the page built from both. |
| 281 | `    H3 = hyp(m3)` | `H3`: the rows of the hypothesis table. |
| 282 | `    assert H3['H7a, read']['word'] == 'not rejected' and H3['H7b, read']['word'] == 'rejected', (H3['H7a, read']['flags'], H3['H7b, read']['flags'])` | Proves that H7a for read is `not rejected`: the stop method changes D. H7b for read is still `rejected`: the start changes nothing. So the page treats the two hypotheses separately, each by its own factors. |
| 283 | `    assert Q.fx(8.0) in h3 or Q.fx(-8.0) in h3 or '-8.0' in h3            # the change of D (4 threads x 2.0 GB/s) is printed` | Proves that the page prints the change of D: 4 threads times 2.0 GB/s is 8.0 GB/s, with either sign. |
| 284 | `    # WHY: "not rejected" must not read as "the timing method explains the difference". The basis gives the direction and` | Comment: why: `not rejected` must not read as if the timing method explained the difference. The basis gives the direction and the size of the resolved changes. |
| 285 | `    # the size of the resolved changes: here D is larger with whole passes (old read loses 2 GB/s per thread with the common stop).` | Comment: here D is larger with whole passes. The reason is that old read loses 2 GB/s per thread with the common stop. |
| 286 | `    assert 'D is larger with whole passes' in H3['H7a, read']['basis'] and '% of the median D' in H3['H7a, read']['basis'], H3['H7a, read']['basis']` | Proves that the basis of H7a names the direction, D is larger with whole passes, and gives the size as a share of the median D. |
| 287 | `    assert not H3['H7a, read']['open'] and 'no timing setting removes it' in H3['H7a, read']['basis']` | Proves that the row has no open question, and that the basis says that no timing setting removes D. |
| 289 | `    # ---- 4. The pattern labels are not used (user decision of 2026-11-13).` | Comment: test 4, the pattern labels are not used, by the decision of the user of 2026-11-13. |
| 290 | `    # WHY: q did not fall into two groups in Part A. A result that rests on the labels would be an artefact of two` | Comment: why: q did not fall into two groups in Part A, so a result that depends on the labels would follow from two provisional limits and not from the data. |
| 291 | `    # provisional limits. The synthetic B8 gives a clean bracket by the label rule, B9 gives equal labels, and B5 gives a` | Comment: the invented B8 gives a clear bracket by the label rule, B9 gives equal labels, and B5 gives a sparse loop equal to old read. |
| 292 | `    # sparse loop equal to old read. The analysis script calls these "supported" and "rejected". The page must not.` | Comment: the analysis script calls these results `supported` and `rejected`. The page must not. |
| 293 | `    c1, c2 = mk(sparse_equal=True), mk(sparse_equal=True)` | `c1` and `c2`: two invented sessions in which `read_sparse` has the rates of old read. |
| 294 | `    m4, h4 = page({'s1': c1, 's2': c2})` | `m4` and `h4`: the model and the page built from both. |
| 295 | `    H4, an = hyp(m4), m4['summary']['hypotheses']` | `H4`: the rows of the page. `an`: the entries of the analysis script per hypothesis. |
| 296 | `    assert an['H8 (B8)']['word'].startswith('not rejected (supported)'), an['H8 (B8)']` | Proves the starting point: the label rule of the analysis gives H8 the word `not rejected (supported)`. H8 says that a loop that only loads reaches the uniform state at a lower thread count than old read. |
| 297 | `    assert an['H9a (B9)']['word'] == 'rejected', an['H9a (B9)']` | Proves the starting point: the label rule gives H9a the word `rejected`. H9a says that the second buffer per thread changed the pattern of old read. |
| 298 | `    assert an['B5 statement "vector adds are needed for the split pattern of old read"']['word'] == 'rejected'` | Proves the starting point: the label rule gives the B5 statement the word `rejected`. The statement says that vector adds are needed for the pattern and total of old read. |
| 299 | `    assert H4['H8']['word'] == 'not resolved' and H4['H9a']['word'] == 'not resolved' and H4['B5 statement']['word'] == 'not resolved'` | Proves that the page gives all three the word `not resolved`. So page rule 1 applies also when the label rule gives a clear result. |
| 300 | `    # WHY: the conflict between the label rule and the user decision is shown side by side, not hidden and not overridden silently.` | Comment: why: the conflict between the label rule and the user decision is shown, with both words next to each other. It is not hidden, and the page does not replace one by the other without a word. |
| 301 | `    assert H4['H9a']['strict'].startswith('"rejected" (s1: fail, s2: fail)') and 'It is not used: user decision 2' in H4['H9a']['other']` | Proves that the row of H9a shows the output of the label rule, `rejected` with the flag `fail` of both sessions, and that its other reading says that this word is not used by user decision 2. |
| 302 | `    assert H4['H8']['strict'].startswith('"not rejected (supported)"') and H4['H8']['other']` | Proves the same for H8: the row shows the word of the label rule and has a text for the other reading. |
| 303 | `    assert e_in(H4['H9a']['other'], h4) and e_in(H4['H9a']['strict'], h4)` | Proves that both texts of H9a stand on the page, escaped as the page escapes text. |
| 304 | `    assert not H4['H9a']['open']                                                       # decided by the user, so it is not open` | Proves that H9a has no open question. By the comment the user has decided this point, so it is not open. |
| 305 | `    assert not hyp(m2)['B5 statement']['other']                                        # no conflict where the total alone decides` | Proves, with the page of test 2, that the B5 statement has no other reading where the total alone decides. |
| 306 | `    b8 = h4.split('<h2 id="b8">')[1].split('<h2')[0]` | `b8`: the HTML text of the B8 section of the page. |
| 307 | `    assert not re.search(r'\b(split\|uniform)\b', visible(b8).replace('labels split and uniform', '')), 'a label is printed in the B8 section'` | Proves that the visible text of the B8 section never uses `split` or `uniform` as a word of its own, apart from the phrase that names the two labels. So no label is printed as a result. |
| 308 | `    # WHY: where the totals alone decide the B5 rule, no label is needed and the result must not be weakened.` | Comment: why: where the totals alone decide the B5 rule, no label is needed, and the result must not be made weaker. |
| 309 | `    assert hyp(m2)['B5 statement']['word'] == 'not rejected' and hyp(m2)['B5 statement']['flags'] == {'s1': 'hold', 's2': 'hold'}` | Proves, with the page of test 2, that the B5 statement is `not rejected` with the flag `hold` in both sessions. There the total of `read_sparse` differs from old read by a resolved amount. |

### `main`: tests 5 to 9 (irregular interval, H11, missing steps, command line, load) (lines 311 to 364)

| Line | Source | Explanation |
|---:|---|---|
| 311 | `    # ---- 5. An irregular interval.` | Comment: test 5, an irregular interval. |
| 312 | `    # WHY: handoff B.4: an interval with a late thread is not used for a decision. Its process then has no D, the` | Comment: why, from section B.4 of the handoff: an interval with a late thread is not used for a decision. Its process then has no D. |
| 313 | `    # setting has 3 processes, and 3 are too few (B.10 asks for 4). The page must list the interval and say "not observed".` | Comment: the setting then has 3 processes, and section B.10 asks for 4. So the page must list the interval and say `not observed`. |
| 314 | `    d1 = mk(late=True)` | `d1`: an invented session with one late thread in process 1 of the setting `common/500/common`. |
| 315 | `    m5, h5 = page({'s1': d1})` | `m5` and `h5`: the model and the page built from it. |
| 316 | `    st = m5['S']['s1']['B7']['res']['settings']` | `st`: the results of the analysis for the settings of B7. |
| 317 | `    assert st['common/500/common']['decision'] == 'not observed' and st['pass/500/common']['decision'] == 'resolved'` | Proves that the setting with the late thread is `not observed`, and that the reproduction condition is still `resolved`. So one bad interval removes its own setting only. |
| 318 | `    irr = h5.split('<h3>Irregular intervals</h3>')[1].split('<p>')[0]` | `irr`: the HTML text between the heading `Irregular intervals` and the next paragraph, which is the table of the irregular intervals. |
| 319 | `    assert 'common-500-common-p1' in irr and 'old read' in irr` | Proves that the table lists the process `common-500-common-p1` and the kernel old read. |
| 320 | `    assert 'D is resolved with old read above new read in 7 of 8 settings' in h5` | Proves that the note of the chart counts D as resolved in 7 of 8 settings. |
| 321 | `    check_page_rules(h5, m5)` | Runs the checks of `check_page_rules` on this page. |
| 323 | `    # ---- 6. H11.` | Comment: test 6, H11. |
| 324 | `    # WHY: H11 says ONE mesh makes the higher totals. A higher interval in which only mesh 1 is faster supports it.` | Comment: why: H11 says that one mesh makes the higher totals. A higher interval in which only mesh 1 is faster supports it. |
| 325 | `    # A higher interval in which both meshes are faster contradicts it, and only two such sessions reject it.` | Comment: a higher interval in which both meshes are faster contradicts it, and only two such sessions reject it. |
| 326 | `    e1 = mk(b10='mesh1')` | `e1`: an invented session in which one interval of old write has a faster mesh 1. |
| 327 | `    m6, h6 = page({'s1': e1})` | `m6` and `h6`: the model and the page built from it. |
| 328 | `    assert hyp(m6)['H11']['word'] == 'not rejected' and hyp(m6)['H11']['plan_word'] == 'supported', hyp(m6)['H11']` | Proves that H11 is then `not rejected` with the plan word `supported`. |
| 329 | `    f1, f2 = mk(b10='both'), mk(b10='both')` | `f1` and `f2`: two invented sessions in which both meshes are faster in that interval. |
| 330 | `    assert hyp(page({'s1': f1})[0])['H11']['word'] != 'rejected'` | Proves that one such session alone does not give `rejected`. The test does not look at the plan word of that page. |
| 331 | `    m7, h7 = page({'s1': f1, 's2': f2})` | `m7` and `h7`: the model and the page built from both. |
| 332 | `    assert hyp(m7)['H11']['word'] == 'rejected' and hyp(m7)['H11']['plan_word'] == 'contradicted', hyp(m7)['H11']` | Proves that two such sessions give `rejected` with the plan word `contradicted`. |
| 333 | `    assert '<b>rejected</b> (contradicted)' in h7` | Proves that the page prints the word in bold with the plan word in brackets. |
| 334 | `    # WHY: with no higher interval in any setting the plan says "not observed", not "rejected".` | Comment: why: with no higher interval in any setting the plan says `not observed` and not `rejected`. |
| 335 | `    assert hyp(m)['H11']['word'] == 'not observed', hyp(m)['H11']` | Proves, with the model of test 1, that H11 is `not observed` when no interval has a higher total. |
| 337 | `    # ---- 7. Missing steps.` | Comment: test 7, missing steps. |
| 338 | `    # WHY: a step without data must show "Insufficient data" and the word "not tested". It must not be skipped silently.` | Comment: why: a step without data must show `Insufficient data` and the word `not tested`. The page must not leave it out without a word. |
| 339 | `    g1 = mk(steps=('B7', 'B10'))` | `g1`: an invented session with the steps B7 and B10 only. |
| 340 | `    m8, h8 = page({'s1': g1})` | `m8` and `h8`: the model and the page built from it. |
| 341 | `    H8 = hyp(m8)` | `H8`: the rows of the hypothesis table. |
| 342 | `    assert H8['H8']['word'] == 'not tested' and H8['H9a']['word'] == 'not tested' and H8['B5 statement']['word'] == 'not tested'` | Proves that H8, H9a and the B5 statement are `not tested` when their steps are missing. |
| 343 | `    for stp in ('B8', 'B5', 'B9', 'C3'):` | Loop over the four missing steps. |
| 344 | `        sec = h8.split(f'<h2 id="{stp.lower()}">')[1].split('<h2')[0]` | `sec`: the HTML text of the section of the step, from its heading to the next heading of level 2. |
| 345 | `        assert 'Insufficient data' in sec and f'no process of step {stp}' in sec, stp` | Proves that the section still exists and says `Insufficient data` and that the session has no process of the step. |
| 346 | `    assert 'Missing: B8 in session s1' in h8` | Proves that the input paragraph of the page lists the missing steps, starting with B8 in session `s1`. |
| 347 | `    check_page_rules(h8, m8)` | Runs the checks of `check_page_rules` on this page. |
| 349 | `    # ---- 8. The command line, with folders of other steps in the input.` | Comment: test 8, the command line, with folders of other steps in the input. |
| 350 | `    # WHY: the lead calls the script with all folders of a session. Processes of the Q1 steps must not reach this page.` | Comment: why: the lead calls the script with all folders of a session, and processes of the Q1 steps must not appear on this page. |
| 351 | `    other = Folder(os.path.join(root, 'set1'), 'B4-x', 'B4')` | `other`: an extra invented folder `B4-x` of step B4, placed beside the folders of test 1. |
| 352 | `    other.proc('cpu2-p1', [2], 'asmread', 2, 'pass', 300, 'common', lambda k, c, r, i: 68.0)` | Writes one process into it: one thread on CPU 2 with asm read at 68.0 GB/s. |
| 353 | `    out = os.path.join(root, 'cli.html')` | `out`: the path of the page that the command line will write. |
| 354 | `    assert Q.main(['--session', 's1'] + a1 + [other.close(), '-o', out]) == 0` | Proves that `main` of the page builder returns 0 for a call with the session `s1`, the folders of test 1, the extra folder and the output path. |
| 355 | `    hc = open(out).read()` | `hc`: the text of the page that the call wrote. |
| 356 | `    assert 'B4-x' not in hc and 'Session s1 has 6 result folders for 6 steps' in hc` | Proves that the folder of the other step does not appear on the page, and that the page counts 6 result folders for 6 steps. |
| 358 | `    # ---- 9. The load statement.` | Comment: test 9, the load statement. |
| 359 | `    # WHY: the 1-minute load is high after our own process. The page must name the readings that show an idle host.` | Comment: why: the load average of the last minute is high after our own process, so the page must name the readings that show an idle machine. |
| 360 | `    ld = h.split('<h2 id="load">')[1].split('<h2')[0]` | `ld`: the HTML text of the load section of the page of test 1. |
| 361 | `    assert 'Our own benchmark process' in ld and 'Runnable tasks: 1 at each of the' in ld and '0 of ' in ld and 'Logged-in users: 0 at each of the' in ld` | Proves that the section explains the high load by our own benchmark process, and that it holds the texts of three readings: 1 runnable task at each launch, the text `'0 of '`, and 0 logged-in users at each launch. The text `'0 of '` stands for 0 launches that waited. This part of the condition is weak: a count that ends in 0, such as 10 launches that waited, would meet it too. |
| 362 | `    assert 'above 10 % of one CPU at 0 launches' in visible(ld) and 'Another account' not in ld` | Proves that the section counts 0 launches with a process of another account above 10 % of one CPU, and has no paragraph on another account. |
| 363 | `    assert m['S']['s1']['load']['B7']['load_max'] == 99.0 and m['S']['s1']['load']['B7']['first_load'] == 0.5` | Proves that the model read the invented load values of B7 from the header lines: 99.0 as the highest and 0.5 at the first launch. |

### `main`: test 10 (another account, the times of the sessions, a deviation of the setting) (lines 365 to 394)

| Line | Source | Explanation |
|---:|---|---|
| 365 | `    # ---- 10. A process of another account, the times of the sessions, and a deviation of the setting.` | Comment: test 10 covers a process of another account, the times of the sessions, and a deviation of the setting. |
| 366 | `    # WHY: the user asks for the load of every step. A busy process of another account must be named with its launch, and` | Comment: why: the user asks for the load of every step. A busy process of another account must be named with its launch. |
| 367 | `    # must not disappear behind a general sentence on an idle host.` | Comment: it must not be hidden by a general sentence on an idle machine. |
| 368 | `    t0 = 1794600000` | `t0`: the start of the first invented session, as Unix time. |
| 369 | `    i1 = mk(boost=('common', 6000, 'common'), clock0=t0)` | `i1`: a session that starts at `t0`. In B7 the setting `common/6000/common` gets the boost, so the handoff rule selects it. |
| 370 | `    i2 = mk(boost=('common', 6000, 'offset'), clock0=t0 + 6 * 600 - 10 + 14, c3_busy='90.9 root     check-new-relea')` | `i2`: a session in which the setting `common/6000/offset` gets the boost. It starts 3604 s after `i1`, which is 14 s after the end of the last folder of `i1`. The first launch of its C3 lists a process `check-new-relea` of `root` at 90.9 %. |
| 371 | `    m10, h10 = page({'s1': i1, 's2': i2})` | `m10` and `h10`: the model and the page built from both. |
| 372 | `    ld = visible(h10.split('<h2 id="load">')[1].split('<h2')[0])` | `ld`: the visible text of the load section. |
| 373 | `    assert 'above 10 % of one CPU at 1 launch of' in ld and 'Another account, session s2, step C3' in ld and 'check-new-release' in ld and '90.9 %' in ld, ld[:900]` | Proves that the section counts 1 launch with a busy process of another account, names the session and the step of that launch, gives the full program name `check-new-release`, and gives the share of 90.9 %. |
| 374 | `    assert 'at 1 of 2 launches of that step' in ld` | Proves that the section says at how many launches of the step the process was seen: 1 of 2. |
| 375 | `    # WHY: rule 10 of the plan asks for sessions some hours apart. The page must give the real times, so that a reader` | Comment: why: rule 10 of the plan asks for sessions some hours apart, so the page must give the real times. |
| 376 | `    # sees that the two sessions are one continuous run (session 2 starts 14 s after session 1 ends).` | Comment: a reader then sees that the two sessions are one continuous run. Session 2 starts 14 s after session 1 ends. |
| 377 | `    v10 = visible(h10)` | `v10`: the visible text of the whole page. |
| 378 | `    assert 'Session s2 started 14 s after session s1 ended' in v10 and 'one continuous run' in v10, v10[v10.index('When the sessions ran'):][:700]` | Proves that the page says that session `s2` started 14 s after session `s1` ended, and calls this one continuous run. So the gap comes from the times of `env.txt`. |
| 379 | `    assert 'each step of session s2 started 1 h 0 min after the same step of session s1' in v10` | Proves that the page gives the distance between the same steps of the two sessions, 3604 s, in the words `1 h 0 min`. |
| 380 | `    assert 'so the machine was not restarted between the sessions' in v10` | Proves that the page concludes from the uptime lines that the machine was not restarted between the sessions. |
| 381 | `    assert 'Insufficient data: whether the machine was restarted' in visible(h2)       # no uptime reading in those folders` | Proves, with the page of test 2, that the page says `Insufficient data` on a restart when the folders have no uptime line. |
| 382 | `    # WHY: B8, B5 and B9 must run in the setting that the handoff rule selects from B7 of the same session. Where they` | Comment: why: B8, B5 and B9 must run in the setting that the handoff rule selects from B7 of the same session. |
| 383 | `    # did not, the page must call it a deviation, name both settings and say that the user did not decide it.` | Comment: where they did not, the page must call it a deviation, name both settings, and say that the user did not decide it. |
| 384 | `    assert m10['S']['s1']['B7']['chosen'] == 'common/6000/common' and m10['S']['s2']['B7']['chosen'] == 'common/6000/offset'` | Proves the starting point: the handoff rule selects `common/6000/common` in `s1` and `common/6000/offset` in `s2`. |
| 385 | `    fa = visible(h10.split('<h2 id="facts">')[1].split('<h2')[0])` | `fa`: the visible text of the section on the decisions and settings. |
| 386 | `    assert fa.count('Deviation, session') == 1 and 'Deviation, session s2' in fa and 'The user did not decide this' in fa, fa[:1500]` | Proves that the section reports exactly one deviation, for session `s2`, and says that the user did not decide it. The later steps of `s2` ran with the common start. |
| 387 | `    assert 'The handoff rule selects "common stop, 6 s, offset start"' in fa and 'It is the setting that the rule selects in session s1' in fa` | Proves that the item names the setting that the rule selects in `s2`, and says that the used setting is the one that the rule selects in `s1`. |
| 388 | `    assert 'Deviation, session' not in h2 or m2['S']['s1']['B7']['chosen'] != 'common/6000/common' or m2['S']['s2']['B7']['chosen'] != 'common/6000/common'` | Proves, with the page of test 2, that no deviation is reported there, unless the rule did not select `common/6000/common` in one of its sessions. |
| 389 | `    # WHY: the pair of intervals in the per-thread chart must come from the setting that the later steps really used.` | Comment: why: the pair of intervals in the chart with one marker per thread must come from the setting that the later steps really used. |
| 390 | `    assert m10['S']['s2']['B7']['rep']['setting'] == 'common/6000/common' and m10['S']['s2']['B7']['rep']['why'] == 'used'` | Proves that the example pair of `s2` comes from the setting `common/6000/common`, with the reason `used`. |
| 391 | `    check_page_rules(h10, m10)` | Runs the checks of `check_page_rules` on this page. |
| 392 | `    if keep:` | The next line runs only with `--keep`. |
| 393 | `        open(os.path.join(root, 'deviation.html'), 'w').write(h10)` | Writes the page to the file `deviation.html` in the kept folder. |

### `main`: test 11 (2 % check, rounded zero, shared axis, H11 over two sessions) and the end (lines 395 to 424)

| Line | Source | Explanation |
|---:|---|---|
| 395 | `    # ---- 11. The 2 % check of rule 7, a rounded zero, the shared axis of B8, and H11 over two sessions.` | Comment: test 11 covers the 2 % check of rule 7, a rounded zero, the shared axis of B8, and H11 over two sessions. |
| 396 | `    # WHY: rule 7 of the plan applies to every run with whole passes. The synthetic threads make 9 passes or fewer in` | Comment: why: rule 7 of the plan applies to every run with whole passes. The invented threads make 9 passes or fewer in 0.5 s. By the invented rates the largest value in a T row is about 9.4 passes: 5.03 GB/s for 0.5 s on a 256 MiB buffer. That is far below the 50 passes of the check. |
| 397 | `    # 0.5 s, so every such interval fails, also with one kernel per process and in B10.` | Comment: so every such interval fails, also with one kernel per process and in B10. |
| 398 | `    b7 = m['S']['s1']['B7']` | `b7`: the model of B7 of test 1. |
| 399 | `    assert b7['fail2_single'][0] == b7['fail2_single'][1] == 48 and '<td>48 of 48</td>' in h` | Proves that all 48 intervals of the processes with one kernel fail the check, and that the table prints `48 of 48`. These are 16 processes with 3 intervals each. |
| 400 | `    f10 = m['S']['s1']['B10']['fail2']` | `f10`: the values of the 2 % check of B10 of test 1. |
| 401 | `    assert set(f10) == {'pass/500/common', 'pass/500/offset', 'pass/15000/common', 'pass/15000/offset'} and f10['pass/500/common'][:2] == (64, 64)` | Proves that the check exists for exactly the four settings with whole passes, and that all 64 intervals of `pass/500/common` fail. |
| 402 | `    assert f10['pass/15000/common'][0] == 0                                           # 15 s at 1 GB/s: 55 passes` | Proves that no interval of `pass/15000/common` fails. By the comment 15 s at 1 GB/s are 55 passes, which is above the limit of 50. |
| 403 | `    b10h = h.split('<h2 id="b10">')[1].split('<h2')[0]` | `b10h`: the HTML text of the B10 section of the page of test 1. |
| 404 | `    assert '<td>64 of 64</td>' in b10h and '<td>0 of 64</td>' in b10h and 'Fewest passes of a thread' in b10h` | Proves that the table of the section prints `64 of 64` and `0 of 64`, and has the column with the fewest passes of a thread. |
| 405 | `    # WHY: "-0.00" and "+0.00" are the same number. A sign on a rounded zero looks like a direction.` | Comment: why: `-0.00` and `+0.00` are the same number, and a sign on a rounded zero looks like a direction. |
| 406 | `    assert Q.fs(-0.001) == '0.00' and Q.fs(0.004) == '0.00' and Q.fs(-0.006) == '-0.01' and Q.fs(1.5) == '+1.50'` | Proves four cases of the function `fs` of the page builder: -0.001 and 0.004 print as `0.00` without a sign, -0.006 prints as `-0.01`, and 1.5 prints as `+1.50`. |
| 407 | `    # WHY: two sessions with the same thread rates must not look different because the charts chose different axes.` | Comment: why: two sessions with the same thread rates must not look different only for the reason that the charts chose different axes. |
| 408 | `    assert m2['b8_ymax'] == 6.0 and h2.count('>6</text>') >= 6` | Proves that the common upper end of the y axis of the B8 panels is 6.0 GB/s, and that the tick label 6 occurs at least 6 times on the page of test 2. Two sessions have 3 panels each. |
| 409 | `    # WHY: H11 needs the same result in both sessions. A cell that is supported in one session only is "not resolved".` | Comment: why: H11 needs the same result in both sessions. A cell that is supported in one session only is `not resolved`. |
| 410 | `    m11, h11 = page({'s1': e1, 's2': a2})` | `m11` and `h11`: the model and the page built from the session with a faster mesh 1 (`e1`) and a session without a higher interval (`a2`). |
| 411 | `    H11 = hyp(m11)['H11']` | `H11`: the row of H11. |
| 412 | `    assert H11['word'] == 'not resolved' and '0 of 32 cells are supported in every session' in H11['basis'], H11['basis']` | Proves that the word is `not resolved`, and that the basis says that 0 of the 32 cells are supported in every session. |
| 413 | `    assert 'Mesh 1 rose by' in H11['basis'] and 'Supported in s1: old write' in H11['basis']` | Proves that the basis still names the supported cell of `s1`: old write, with the rise of mesh 1. |
| 414 | `    # WHY: question Q2b must get a plain statement. With no rule for "separate levels" that statement is "Insufficient data".` | Comment: why: question Q2b must get a plain statement. With no rule for separate levels that statement is `Insufficient data`. |
| 415 | `    b10s = visible(h.split('<h2 id="b10">')[1].split('<h2')[0])` | `b10s`: the visible text of the B10 section of the page of test 1. |
| 416 | `    assert 'Question Q2b, description and no decision' in b10s and 'set no rule for when two totals are separate levels' in b10s` | Proves that the section holds the paragraph on Q2b as a description without a decision, and its sentence that no rule says when two totals are separate levels. |
| 418 | `    if not keep:` | The next line runs only without `--keep`. |
| 419 | `        shutil.rmtree(root)` | Deletes the temporary folder with all invented data. |
| 420 | `    print('test_q2: all tests passed' + (f' (pages kept in {root})' if keep else ''))` | Prints `test_q2: all tests passed`. With `--keep` it adds the folder in which the pages were kept. |
| 423 | `if __name__ == '__main__':` | Tests whether the file was started as a script. |
| 424 | `    main()` | Runs `main`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q2_html.py`: the page builder under test.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff: section B.3 (output rows), B.4 (late thread, irregular interval) and B.10 (decision procedure).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the plan: the hypotheses, the rules 7, 10 and 11, and the tested statement of step B5 in the table of the steps.
