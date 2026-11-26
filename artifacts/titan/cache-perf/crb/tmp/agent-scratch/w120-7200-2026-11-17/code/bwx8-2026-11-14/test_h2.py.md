# `test_h2.py` explained, line by line

- Source file: `bwx8-2026-11-14/test_h2.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 526 lines, 32550 bytes).
- sha256 of the source when this page was built: `b3c99cee30bb3061652fcfb6243ca245d03c45a665d1a056a069ddc211b5e41d`.

## Short version: purpose

`test_h2.py` tests the run script `run_h2.sh` and the analysis script `h2_analyze.py` on the agent server, without any contact to CRB. It runs `run_h2.sh` with two dummy binaries in a temporary folder and checks the order of the processes, every stop control and the files of a run, and it runs the analysis on that output and on invented files. It prints one line per check and ends with exit status 0 only when every check passed.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Process**: one start of a benchmark binary.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Original run**: the run of `bw_old` and `bw_new` with the script `run_kernels.sh` on 2026-11-13. Its file `one-thread.csv` holds the rates with one thread [Ref4].
- **Hypothesis H2**: a hypothesis of the investigation into the buffer size of 8 MiB: the gain of 0.94 % of the original run was measured while the new read kernel was at its low level [Ref1] [Ref4].
- **`run_h2.sh`**: the run script of the test of H2. It starts the two original binaries at 8 MiB many times, one process after the other [Ref1].
- **`visit_h2.sh`**: the script that logs in to CRB, checks the marker file and starts `run_h2.sh` there.
- **`h2_analyze.py`**: the analysis script for the files that `run_h2.sh` writes. It also prints the numbers of the original run [Ref5].
- **Dummy binary, dummy**: a small Bash script with the name `bw_old` or `bw_new`. It prints rows in the form of the benchmark with fixed rates and measures nothing.
- **Set-up**: one object of the class `Box`: a temporary folder with the two dummies, a results folder, and its own marker file and stop file.
- **Check**: one call of the function `check`. It has a name that says what it proves, and it prints `PASS` or `FAIL`.
- **Session, of `run_h2.sh`**: one pass of `run_h2.sh` through its 72 processes. Session 1 uses the CPU order 2, 0, 41. Session 2 uses 41, 0, 2 and may start 3 hours after the end of session 1 at the earliest. This is not the session of the later rerun.
- **Pair**: one process of `bw_old` and one process of `bw_new` that run directly one after the other on one CPU. Each CPU gets 12 pairs per session.
- **Place in the pair (`pos`)**: 1 for the process that runs first, 2 for the other.
- **`idx`**: the number of a process in the order of a session, from 0 to 71.
- **Tag**: the name that `run_h2.sh` gives to one process, for example `s1-c2-p01-old`: session 1, CPU 2, pair 1, binary `bw_old`.
- **Dry run**: a start of `run_h2.sh` with `--dry-run`. It prints the command line of every process and starts none.
- **Stop file**: the file `~/cache-perf/STOP`. `run_h2.sh` stops when it exists. A second login creates it to stop a run.
- **`STOP_AT`**: a required setting of `run_h2.sh`: a UTC time past which nothing may run, or the word `none`.
- **Margin**: the seconds that must be left before `STOP_AT` when a process starts: the nominal work of one process plus a reserve.
- **Nominal work**: the planned time of the timed repetitions: 3 times 0.5 s for one process.
- **`SESSION1_END`**: a setting that session 2 needs: the UTC time at which session 1 ended.
- **Settle rule**: before each process `run_h2.sh` waits until at most 2 tasks are runnable, for at most 20 s.
- **Header line**: the line that `run_h2.sh` writes into `H2.csv` before each process. It starts with `-- binary`.
- **Repetition**: one timed measurement of the original benchmark. One process makes 3.
- **Gain**: 100 times (rate of the new read kernel divided by rate of the old read kernel, minus 1), in percent.
- **Class: low, between, high**: the label that `h2_analyze.py` gives to one repetition rate. Low is at or below 69.5 GB/s, high is at or above 70.5 GB/s, and between is the rest.
- **Process group**: a set of processes that one signal can reach together.
- **Signal**: a message that Linux delivers to a process. TERM asks a process to end, INT is the interrupt signal, and HUP says that the connection was closed.
- **Docstring**: a text literal at the top of a Python file, class or function that describes it.

## Main flow

1. The file sets the paths of the scripts under test and imports `h2_analyze.py` (lines 31 to 38).
2. The helpers follow: the text of the dummy binary, the function `check`, the class `Box` for one set-up, the helpers that run `run_h2.sh`, and the rule function `order_problems` (lines 40 to 217).
3. `main` makes a temporary folder, calls `tests`, deletes the folder and sets the exit status (lines 220 to 230).
4. `tests` first checks the texts of the scripts: the syntax, no call of `sudo` or `ssh`, the pinning to the CPUs 0 to 119, and the two sha256 values (lines 234 to 251).
5. Dry run: 72 command lines per session, the original options, a balanced order, and session 2 as the reverse of session 1 (lines 253 to 279).
6. Wrong use and checksums: a missing setting, a wrong sha256 and a missing binary each give exit status 2, and nothing starts (lines 281 to 301).
7. Stop controls before the first process, and the rules for session 2 (lines 303 to 336).
8. Stops while a process runs: the marker file, three signals, the stop file, `STOP_AT`, and a benchmark that fails (lines 338 to 370).
9. A full run of session 1 with 72 dummy processes: the files of the result folder, the order, the header lines, and the analysis of that output (lines 372 to 423).
10. `analyzer_tests` checks `h2_analyze.py` alone: its two small functions, the numbers of the original run, invented files, and the errors that it must report (lines 428 to 522).

## Behavior a reader must know

- No check contacts CRB. The marker file, the stop file, the binaries and the results folder are replaced by paths inside the temporary folder (lines 101 to 103). So a passed check says something about the scripts and nothing about CRB.
- The rates of the dummies are fixed numbers (line 57). Nothing is timed.
- A failed check does not end the run: `check` notes it and the next check runs (lines 67 to 71). A Python error does end the run, for example the time limit of line 109.
- A complete run makes 84 checks, counted from the calls of `check` and their loops in this text. The decisions note records, in an entry of 2026-11-15 at 05:25 UTC, that this file passed 84 of 84 checks [Ref2].
- By the docstring the full run takes about 75 s on an idle machine and up to 26 min on a busy one (lines 14 to 18).
- The code repo does not hold `h2_analyze.py`. The path of line 34 names a folder that the repo does not have. The file lies in the project folder on the agent server [Ref5]. So this test does not start from the repo layout.
- The checks of lines 436 to 444 read a measured file: `one-thread.csv` of the original run, at the fixed path that `h2_analyze.py` holds. The expected numbers of these checks are the numbers of that file [Ref4].
- The check of lines 250 to 251 has the words "after the marker check" in its name. It tests only that both texts are in `visit_h2.sh`, not their order.
- The check of lines 247 to 248 reads `run_kernels.sh`. That script was changed on 2026-11-24, after all tests. Its text in the code repo still holds the option line and the size loop that the check looks for.
- The case of line 361 depends on timing. `STOP_AT` lies 60 s after the start of the case, and the script ends 1 to 2 s after `STOP_AT`. The helper waits 60 s for that end, counted from about 0.5 s after the dummy started to sleep (lines 142 to 145). So the check can fail when the dummy starts to sleep less than about 1.5 s after the start of the case, for example on an idle machine, where `run_h2.sh` does not wait before a process. This is reasoning from the code of this file and of `run_h2.sh` [Ref1]. It was not tested for this page.
- The test deletes its temporary folder at the end unless the environment variable `KEEP` is set (lines 224 to 228).

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/test_h2.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (526 lines, 32550 bytes, sha256 `b3c99cee30bb3061652fcfb6243ca245d03c45a665d1a056a069ddc211b5e41d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: what is tested, with what, and how long it takes (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_h2.py - local tests of run_h2.sh and of h2_analyze.py.` | Starts the docstring of the file. It ends in line 19. The file holds local tests of the run script `run_h2.sh` and of the analysis script `h2_analyze.py`. |
| 4 | `Runs on the development machine. It never contacts CRB. run_h2.sh is run` | Docstring: the tests run on the development machine, which is the agent server. They never contact CRB. `run_h2.sh` is run with two dummy binaries. The sentence goes on in line 5. |
| 5 | `with two dummy binaries (shell scripts named bw_old and bw_new in a temporary` | Docstring: the dummy binaries are shell scripts with the names `bw_old` and `bw_new` in a temporary folder. |
| 6 | `folder) through the test-only settings H2_DIR, H2_SHA256_OLD, H2_SHA256_NEW,` | Docstring: `run_h2.sh` finds them through settings that exist for tests only: `H2_DIR` (the folder of the binaries), and `H2_SHA256_OLD` and `H2_SHA256_NEW` (the expected checksums). The list goes on in line 7. |
| 7 | `BWX8_MARKER, BWX8_STOPFILE and BWX8_RESULTS. The dummy binaries print rows in` | Docstring: `BWX8_MARKER` (the path of the marker file), `BWX8_STOPFILE` (the path of the stop file) and `BWX8_RESULTS` (the folder for the result folders). The dummy binaries print rows. The sentence goes on in line 8. |
| 8 | `the csv form of the original program, so rates mean nothing.` | Docstring: the rows have the csv form of the original program, so the rates mean nothing. |
| 10 | `Usage: test_h2.py            (KEEP=1 keeps the temporary folder)` | Docstring: the usage. The file takes no argument. `KEEP=1` in the environment keeps the temporary folder. |
| 11 | `Output: one line per check, "PASS name" or "FAIL name: detail".` | Docstring: the output is one line per check: `PASS` with the name, or `FAIL` with the name and a detail. |
| 12 | `Exit status: 0 only if every check passed.` | Docstring: the exit status is 0 only if every check passed. |
| 14 | `The full run of 72 dummy processes takes about 75 s on an idle machine,` | Docstring: the full run of 72 dummy processes takes about 75 s on an idle machine. The reason follows in line 15. |
| 15 | `because run_h2.sh looks at the marker file once per second while a process` | Docstring: `run_h2.sh` looks at the marker file once per second while a process runs. |
| 16 | `runs. On a machine with more than 2 runnable tasks run_h2.sh also waits up to` | Docstring: on a machine with more than 2 runnable tasks `run_h2.sh` also waits up to 20 s before every process. The script calls this its settle rule. The sentence goes on in line 17. |
| 17 | `20 s before every process (its "settle" rule), so the full run can take up to` | Docstring: so the full run can take up to 26 min. |
| 18 | `26 min. The test allows 40 min for it.` | Docstring: the test allows 40 min for the full run (line 374). |
| 19 | `"""` | Ends the docstring. |

### Imports and the paths of the files under test (lines 20 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `import contextlib` | Imports `contextlib`. It gives `redirect_stdout` and `redirect_stderr`, which catch printed text (line 215). |
| 21 | `import hashlib` | Imports `hashlib`, which computes sha256 checksums (line 78). |
| 22 | `import io` | Imports `io`, which gives a text buffer in memory (line 214). |
| 23 | `import os` | Imports `os`: paths, files, folders, the environment and process groups. |
| 24 | `import re` | Imports `re`: regular expressions. |
| 25 | `import shutil` | Imports `shutil`, which deletes a folder tree (line 228). |
| 26 | `import subprocess` | Imports `subprocess`, which starts other programs and collects their output. |
| 27 | `import sys` | Imports `sys`: the module search path, the Python program in use and the exit of the script. |
| 28 | `import tempfile` | Imports `tempfile`, which makes the temporary folder (line 221). |
| 29 | `import time` | Imports `time`: the clock, pauses and the text form of a UTC time. |
| 31 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this file. |
| 32 | `RUN = os.path.join(HERE, "run_h2.sh")` | `RUN`: the path of `run_h2.sh` in that folder. It is the script under test. |
| 33 | `VISIT = os.path.join(HERE, "visit_h2.sh")` | `VISIT`: the path of `visit_h2.sh` in that folder. That script logs in to CRB and starts `run_h2.sh` there. The tests only read its text. |
| 34 | `A = os.path.normpath(os.path.join(HERE, "..", "..", "..", "new-test-kernel", "tackle-8mb-analysis"))` | `A`: the folder of the analysis scripts: `new-test-kernel/tackle-8mb-analysis` inside the folder that lies three levels above the folder of this file. `normpath` removes the `..` parts from the path. |
| 35 | `ORIG_RUN = os.path.join(HERE, "..", "kernels-2026-11-13", "run_kernels.sh")` | `ORIG_RUN`: the path of `run_kernels.sh` in the folder `kernels-2026-11-13` beside this folder. It is the run script of the original run of 2026-11-13. |
| 36 | `sys.path.insert(0, A)` | Puts the folder `A` at the front of the module search path of Python. |
| 37 | `sys.dont_write_bytecode = True` | Tells Python to write no compiled copies of the modules that it imports. So the import of line 38 leaves no folder `__pycache__`. |
| 38 | `import h2_analyze  # noqa: E402` | Imports the analysis script `h2_analyze.py` from the folder `A`. The comment `noqa: E402` tells a style checker to accept an import that does not stand at the top of the file. |
| 40 | `OPTIONS = "--threads 1 --cpus %s --bytes 8M --kernel read --reps 3 --min-ms 500"` | `OPTIONS`: the options with which every process must be started, with `%s` in the place of the CPU: 1 thread, a buffer of 8 MiB, the kernel `read`, and 3 repetitions of at least 500 ms each. The function `one` of `run_kernels.sh`, the script of the original run, gives a process the same options (line 248). |

### `DUMMY`: the text of the two dummy binaries (lines 42 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `# The dummy binary. It logs its name and arguments, counts its calls, and prints what the original` | Comment: the dummy binary logs its name and its arguments, counts its calls, and prints what the original program prints. |
| 43 | `# program prints. Rates: bw_old 67.00 to 67.02; bw_new on CPU 41 starts low and ends high.` | Comment: its rates. `bw_old` prints 67.00 to 67.02 GB/s. `bw_new` on CPU 41 starts low and ends high. |
| 44 | `# DUMMY_MARK_AT=n: the n-th call creates the marker file and then sleeps (the runner must kill it).` | Comment: `DUMMY_MARK_AT=n` makes the call number `n` create the marker file and then sleep. The comment calls `run_h2.sh` the runner here: it must kill the dummy. |
| 45 | `# DUMMY_FAIL_AT=n: the n-th call exits with status 7.` | Comment: `DUMMY_FAIL_AT=n` makes the call number `n` end with exit status 7. |
| 46 | `# DUMMY_SLEEP_AT=n: the n-th call sleeps for 300 s (the test stops the runner meanwhile).` | Comment: `DUMMY_SLEEP_AT=n` makes the call number `n` sleep for 300 s. The test stops `run_h2.sh` in that time. |
| 47 | `# A call that sleeps writes its process id to the file "pid" first. run_h2.sh starts the dummy with` | Comment: a call that sleeps first writes its process id to the file `pid`. The comment goes on in line 48. |
| 48 | `# setsid, so this id is also the id of its process group.` | Comment, continued: `run_h2.sh` starts the dummy with `setsid`, so this id is also the id of its process group. |
| 49 | `DUMMY = r"""#!/usr/bin/env bash` | `DUMMY`: starts a text that holds a Bash script. The text ends in line 62. The `r` before the quotes keeps every backslash as it is. This first line of the script tells Linux to run it with `bash`. |
| 50 | `me=$(basename "$0"); d=$(dirname "$0")` | Text of the dummy: `me` is the file name of the dummy, `bw_old` or `bw_new`. `d` is its folder. |
| 51 | `echo "$me $*" >> "$d/calls.log"` | Text of the dummy: adds one line with its name and all its arguments to the file `calls.log` in its folder. The sign `>>` appends to a file. |
| 52 | `n=$(wc -l < "$d/calls.log")` | Text of the dummy: `n` is the number of lines of `calls.log`. So `n` is the number of this call, counted over both dummies. |
| 53 | `cpu=$4` | Text of the dummy: `cpu` is the fourth argument. In the option line of `run_h2.sh` this is the value after `--cpus`. |
| 54 | `if [[ -n ${DUMMY_FAIL_AT:-} && $n == "$DUMMY_FAIL_AT" ]]; then echo "dummy failure" >&2; exit 7; fi` | Text of the dummy: when `DUMMY_FAIL_AT` is set and equals `n`, it prints `dummy failure` to the error output and ends with exit status 7. `${DUMMY_FAIL_AT:-}` gives an empty text when the variable is not set, and `-n` tests for a text that is not empty. |
| 55 | `echo "# bandwidth: GB = 1e9 bytes; dummy threads=1 bytes_per_thread=8388608 min_ms=500 thp=madvise"` | Text of the dummy: prints the comment line of the benchmark, with the word `dummy` in it. |
| 56 | `echo "kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps"` | Text of the dummy: prints the line with the column names of the benchmark. |
| 57 | `if [[ $me == bw_old ]]; then r=(67.00 67.01 67.02); elif [[ $cpu == 41 ]]; then r=(69.10 70.00 71.60); else r=(67.50 67.60 67.70); fi` | Text of the dummy: `r` holds the three rates in GB/s. `bw_old`: 67.00, 67.01 and 67.02. `bw_new` on CPU 41: 69.10, 70.00 and 71.60. `bw_new` on any other CPU: 67.50, 67.60 and 67.70. |
| 58 | `for i in 0 1 2; do echo "read,1,8388608,$i,33537654784,0.5001,${r[i]},${r[i]},${r[i]},${r[i]}"; done` | Text of the dummy: prints one row per repetition 0, 1 and 2: the kernel `read`, 1 thread, 8388608 bytes, the repetition, fixed values for the total bytes and the time, and the rate in the last four columns. |
| 59 | `if [[ -n ${DUMMY_MARK_AT:-} && $n == "$DUMMY_MARK_AT" ]]; then echo $$ > "$d/pid"; touch "$DUMMY_MARKER"; sleep 30; fi` | Text of the dummy: when `DUMMY_MARK_AT` equals `n`, it writes its process id (`$$`) to the file `pid`, creates the marker file whose path is in `DUMMY_MARKER`, and sleeps 30 s. |
| 60 | `if [[ -n ${DUMMY_SLEEP_AT:-} && $n == "$DUMMY_SLEEP_AT" ]]; then echo $$ > "$d/pid"; sleep 300; fi` | Text of the dummy: when `DUMMY_SLEEP_AT` equals `n`, it writes its process id to the file `pid` and sleeps 300 s. |
| 61 | `echo "read,1,8388608,best,,,${r[2]},,,"` | Text of the dummy: prints the `best` line with the third rate. A dummy that is killed in line 59 or line 60 never prints it. |
| 62 | `"""` | Ends the text. |

### The list of failed checks, and the helpers `check` and `sha` (lines 64 to 80)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `failed = []` | `failed`: the list of the names of the checks that failed, empty at first. |
| 67 | `def check(name, ok, detail=""):` | Starts the function `check`. `name` says what the check proves. `ok` is its result. `detail` is shown when it fails. |
| 68 | `    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))` | Prints `PASS` or `FAIL` and the name. After a failed check with a detail it adds a colon and the first 400 characters of the detail. |
| 69 | `    if not ok:` | After a failed check. |
| 70 | `        failed.append(name)` | Adds the name to `failed`. The run goes on with the next check. |
| 71 | `    return ok` | Returns the result. |
| 74 | `def sha(path):` | Starts the function `sha`. It gives the sha256 of a file as 64 hex digits. |
| 75 | `    if not os.path.exists(path):` | The file does not exist. |
| 76 | `        return "0" * 64` | Then it returns 64 zeros in place of a checksum. |
| 77 | `    with open(path, "rb") as f:` | Opens the file as bytes. |
| 78 | `        return hashlib.sha256(f.read()).hexdigest()` | Returns the sha256 of its content. |

### Class `Box`: one temporary set-up with dummy binaries (lines 81 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 81 | `class Box:` | Starts the class `Box`. One object is one set-up for a group of checks. |
| 82 | `    """one temporary set-up: dummy binaries, results folder, marker and stop file paths"""` | Docstring: a set-up is temporary. It holds the dummy binaries, a results folder, and the paths of the marker file and of the stop file. |
| 84 | `    def __init__(self, top, name):` | Starts the function that makes a set-up with the name `name` below the folder `top`. |
| 85 | `        self.dir = os.path.join(top, name)` | `dir`: the folder of the set-up. |
| 86 | `        self.bin = os.path.join(self.dir, "bin")` | `bin`: its sub-folder for the dummy binaries. |
| 87 | `        self.results = os.path.join(self.dir, "results")` | `results`: its sub-folder for the result folders. |
| 88 | `        os.makedirs(self.bin)` | Makes the folder `bin`. |
| 89 | `        os.makedirs(self.results)` | Makes the folder `results`. |
| 90 | `        for b in ("bw_old", "bw_new"):` | Loop over the two binary names. |
| 91 | `            p = os.path.join(self.bin, b)` | `p`: the path of the dummy. |
| 92 | `            with open(p, "w") as f:` | Opens it for writing. |
| 93 | `                f.write(DUMMY + "# %s\n" % b)` | Writes the text `DUMMY` and one comment line with the name. So the two files differ in content, and their sha256 values differ. |
| 94 | `            os.chmod(p, 0o755)` | Makes the file executable (mode 755). |
| 95 | `        self.marker = os.path.join(self.dir, "RUNNING")` | `marker`: the path of the marker file of this set-up: the file `RUNNING` in its folder. The real marker file on CRB is never touched. |
| 96 | `        self.stopfile = os.path.join(self.dir, "STOP")` | `stopfile`: the path of its stop file: the file `STOP` in its folder. |
| 98 | `    def env(self, **more):` | Starts the function `env`. It builds the environment for one start of `run_h2.sh`. |
| 99 | `        e = {k: v for k, v in os.environ.items()` | `e`: a copy of the environment of the test without the variables that steer `run_h2.sh`: `STOP_AT`, `SESSION`, `SESSION1_END`, `RESERVE` and `_PINNED`. The condition goes on in line 100. |
| 100 | `             if k not in ("STOP_AT", "SESSION", "SESSION1_END", "RESERVE", "_PINNED") and not k.startswith(("H2_", "BWX8_", "DUMMY_"))}` | Continues line 99: and without every variable whose name starts with `H2_`, `BWX8_` or `DUMMY_`. |
| 101 | `        e.update(H2_DIR=self.bin, BWX8_MARKER=self.marker, BWX8_STOPFILE=self.stopfile, BWX8_RESULTS=self.results,` | Sets the test settings: the folder of the dummies, the marker file, the stop file and the results folder of this set-up. The call goes on in lines 102 to 103. |
| 102 | `                 H2_SHA256_OLD=sha(os.path.join(self.bin, "bw_old")), H2_SHA256_NEW=sha(os.path.join(self.bin, "bw_new")),` | Continues the call: the sha256 values of the two dummies as the expected checksums. So the checksum test of `run_h2.sh` passes for the dummies. |
| 103 | `                 DUMMY_MARKER=self.marker, HOME=self.dir)` | Continues the call: `DUMMY_MARKER` for the dummy, and `HOME` as the folder of the set-up. So a file that the script wrote below the home folder would be inside the set-up. |
| 104 | `        e.update(more)` | Adds the settings of the caller, for example `SESSION` or `STOP_AT`. |
| 105 | `        return {k: v for k, v in e.items() if v is not None}` | Returns the environment without the variables whose value is `None`. So a caller removes a setting by giving `None`. |
| 107 | `    def run(self, *args, timeout=600, **more):` | Starts the function `run`. It runs `run_h2.sh` to its end. |
| 108 | `        return subprocess.run([RUN] + list(args), env=self.env(**more), stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Starts the script with the given arguments and the environment of line 98. Its output and its error output are collected as text. The call goes on in line 109. |
| 109 | `                              universal_newlines=True, timeout=timeout)` | Continues line 108: when the script runs longer than `timeout` seconds, Python stops it and the whole test ends with an error. The limit is 600 s unless the caller gives another. |
| 111 | `    def folders(self):` | Starts the function `folders`. |
| 112 | `        return sorted(os.listdir(self.results))` | Returns the names of the result folders of this set-up, sorted. |
| 114 | `    def calls(self):` | Starts the function `calls`. |
| 115 | `        p = os.path.join(self.bin, "calls.log")` | `p`: the path of the call log of the dummies. |
| 116 | `        return open(p).read().splitlines() if os.path.exists(p) else []` | Returns its lines, one per start of a dummy, or an empty list when the file does not exist. |

### Helpers `group_left`, `run_until_sleep`, `utc` and `dry_lines` (lines 119 to 161)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `def group_left(box):` | Starts the function `group_left`. |
| 120 | `    """True if a process of the group of the sleeping dummy still exists (or if the dummy wrote no id)"""` | Docstring: it is true if a process of the group of the sleeping dummy still exists, or if the dummy wrote no id. |
| 121 | `    try:` | Starts a block. Line 123 catches its errors. |
| 122 | `        pid = int(open(os.path.join(box.bin, "pid")).read())` | `pid`: the process id that the dummy wrote to the file `pid`. |
| 123 | `    except (OSError, ValueError):` | The file is missing or holds no number. |
| 124 | `        return True` | Then the function returns true. |
| 125 | `    try:` | Starts a second block. |
| 126 | `        os.killpg(pid, 0)` | Sends the signal 0 to the process group with this id. Signal 0 delivers nothing. The call only tests whether a process of the group exists. |
| 127 | `    except ProcessLookupError:` | No process of the group exists. |
| 128 | `        return False` | Then the function returns false. |
| 129 | `    except PermissionError:` | A process exists, and the test has no right to signal it. |
| 130 | `        pass` | Nothing is done in that case. |
| 131 | `    return True` | Returns true: a process of the group is left. |
| 134 | `def run_until_sleep(box, act, **more):` | Starts the function `run_until_sleep`. |
| 135 | `    """start run_h2.sh, wait until a dummy sleeps, call act(runner), return (status, H2.csv text)"""` | Docstring: it starts `run_h2.sh`, waits until a dummy sleeps, calls `act` with the running script, and returns the exit status and the text of `H2.csv`. |
| 136 | `    p = subprocess.Popen([RUN], env=box.env(**more), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)` | Starts `run_h2.sh` without waiting for it. Its output and its error output are dropped. |
| 137 | `    pidfile = os.path.join(box.bin, "pid")` | `pidfile`: the path of the file `pid` of the dummy. |
| 138 | `    end = time.time() + 300` | `end`: the time 300 s from now. |
| 139 | `    while time.time() < end and p.poll() is None and not (os.path.exists(pidfile) and os.path.getsize(pidfile)):` | Loop: runs while three things hold: the 300 s are not over, the script still runs, and the file `pid` is missing or empty. |
| 140 | `        time.sleep(0.1)` | Each turn is a pause of 0.1 s. |
| 141 | `    started = p.poll() is None and group_left(box)` | `started`: true when the script still runs and the process group of the dummy exists. |
| 142 | `    time.sleep(0.5)` | A pause of 0.5 s. |
| 143 | `    act(p)` | Calls `act` with the running script. `act` sends a signal, creates the stop file, or does nothing. |
| 144 | `    try:` | Starts a block. |
| 145 | `        rc = p.wait(timeout=60)` | `rc`: the exit status of the script. The test waits at most 60 s for its end. |
| 146 | `    except subprocess.TimeoutExpired:` | The script did not end within the 60 s. |
| 147 | `        p.kill()` | Then the test kills it. |
| 148 | `        rc = "timeout"` | And `rc` becomes the text `timeout`, which equals no expected status. |
| 149 | `    f = box.folders()` | `f`: the result folders. |
| 150 | `    csv = open(os.path.join(box.results, f[0], "H2.csv")).read() if f else ""` | `csv`: the text of `H2.csv` in the first result folder, or an empty text without a folder. |
| 151 | `    return (rc if started else "the dummy did not start"), csv` | Returns the status and the text. When the dummy did not start, the status is the text `the dummy did not start`. |
| 154 | `def utc(offset):` | Starts the function `utc`. |
| 155 | `    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset))` | Returns the UTC time that lies `offset` seconds from now, in the form `2026-11-15T03:00:00Z`. A negative `offset` gives a time in the past. |
| 158 | `def dry_lines(out):` | Starts the function `dry_lines`. |
| 159 | `    return [l for l in out.splitlines() if l.startswith("bw_")]` | Returns the lines of an output that start with `bw_`. These are the command lines that `run_h2.sh --dry-run` prints, one per process. |

### Helpers `order_problems` and `dry_order`: the rules of the process order (lines 162 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 162 | `def order_problems(rows, session):` | Starts the function `order_problems`. `rows` is an order of processes: one tuple of CPU, pair number, place in the pair and binary per process. `session` is 1 or 2. |
| 163 | `    """problems of an order [(cpu, pair, pos, binary)] against the rules of the head of run_h2.sh"""` | Docstring: it returns the problems of the order against the rules in the head of `run_h2.sh`. |
| 164 | `    p = []` | `p`: the list of the problems, empty at first. |
| 165 | `    cpus = ["2", "0", "41"] if session == 1 else ["41", "0", "2"]` | `cpus`: the CPU order that the rules give: 2, 0, 41 in session 1, and 41, 0, 2 in session 2. |
| 166 | `    if len(rows) != 72:` | Tests whether the order has another length than 72 processes. |
| 167 | `        return ["%d processes, 72 expected" % len(rows)]` | Then this is the only problem that is returned. |
| 168 | `    if list(dict.fromkeys(r[0] for r in rows)) != cpus:` | Tests the CPU order: the CPUs in the order of their first use must be `cpus`. |
| 169 | `        p.append("CPU order %s, expected %s" % (list(dict.fromkeys(r[0] for r in rows)), cpus))` | If not, it adds a problem with both orders. |
| 170 | `    for ci, cpu in enumerate(cpus):` | Loop over the three CPUs. |
| 171 | `        blk = rows[ci * 24:(ci + 1) * 24]` | `blk`: the 24 processes at the places of this CPU: the first 24, the next 24 or the last 24. |
| 172 | `        if any(r[0] != cpu for r in blk):` | Tests whether a process of another CPU is in the block. |
| 173 | `            p.append("CPU %s: its 24 processes are not in one run" % cpu)` | Then it adds the problem that the 24 processes of the CPU are not in one run. |
| 174 | `            continue` | And it goes on with the next CPU. |
| 175 | `        for b in ("bw_old", "bw_new"):` | Loop over the two binaries. |
| 176 | `            if sum(r[3] == b for r in blk) != 12:` | Tests whether the block holds another number than 12 processes of the binary. |
| 177 | `                p.append("CPU %s: %d processes of %s, 12 expected" % (cpu, sum(r[3] == b for r in blk), b))` | Then it adds a problem with the number found. |
| 178 | `            first = sum(r[3] == b and r[2] == "1" for r in blk)` | `first`: the number of pairs in which this binary is the first process. |
| 179 | `            if first != 6:` | Tests whether this number is not 6. |
| 180 | `                p.append("CPU %s: %s is first in %d pairs, 6 expected" % (cpu, b, first))` | Then it adds a problem. So each binary must run first in half of the pairs of a CPU. |
| 181 | `        for k in range(12):` | Loop over the 12 pairs. |
| 182 | `            x, y = blk[2 * k], blk[2 * k + 1]` | `x` and `y`: the two processes at the places of pair `k`. |
| 183 | `            if (x[1], y[1], x[2], y[2]) != (str(k + 1), str(k + 1), "1", "2") or {x[3], y[3]} != {"bw_old", "bw_new"}:` | Tests three things: both have the pair number `k + 1`, their places in the pair are 1 and 2, and they are one process of each binary. |
| 184 | `                p.append("CPU %s: places %d and %d are not pair %d with one process of each binary" % (cpu, 2 * k, 2 * k + 1, k + 1))` | If not, it adds a problem that names the two places and the pair. |
| 185 | `        # equal mean place of both binaries inside the block (no linear drift favours one binary)` | Comment: both binaries must have the same mean place inside the block. Then a steady drift along the block favours neither binary. |
| 186 | `        place = {b: sum(i for i, r in enumerate(blk) if r[3] == b) for b in ("bw_old", "bw_new")}` | `place`: for each binary the sum of the places (0 to 23) of its processes in the block. |
| 187 | `        if place["bw_old"] != place["bw_new"]:` | Tests whether the two sums differ. |
| 188 | `            p.append("CPU %s: sum of places differs between the binaries: %s" % (cpu, place))` | Then it adds a problem with both sums. |
| 189 | `    return p` | Returns the problems. |
| 192 | `def dry_order(out):` | Starts the function `dry_order`. It reads the order from the output of a dry run. |
| 193 | `    rows = []` | `rows`: the order, empty at first. |
| 194 | `    for l in dry_lines(out):` | Loop over the command lines (line 158). |
| 195 | `        m = re.match(r"(bw_\w+) --threads 1 --cpus (\d+) .*# idx (\d+), pair (\d+), pos (\d), tag (\S+)$", l)` | Tests the line against a pattern. Group 1 is the binary (`bw_` and word characters), group 2 the CPU after `--cpus`, group 3 the number `idx` of the process, group 4 the pair, group 5 the place in the pair (one digit) and group 6 the tag. The part `.*#` skips the other options up to the comment sign. |
| 196 | `        rows.append((m.group(2), m.group(4), m.group(5), m.group(1)) if m else ("?",) * 4)` | Adds the tuple of CPU, pair, place and binary. A line that does not fit gives four question marks. |
| 197 | `    return rows` | Returns the order. |

### Helpers for invented files, `analyze`, and the function `main` (lines 200 to 232)

| Line | Source | Explanation |
|---:|---|---|
| 200 | `def synth_header(binary, cpu, session, idx, pair, pos):` | Starts the function `synth_header`. It builds one header line of an invented `H2.csv`. |
| 201 | `    return ("-- binary %s kernel read threads 1 cpus %s bytes 8M round %d load 0.10 utc 01:02:03 session %d idx %d pair %d pos %d "` | The line has the form that `run_h2.sh` writes: the binary, the kernel `read`, 1 thread, the CPU, 8 MiB, the session in the place of the round, a load of 0.10, a time, and then the fields `session`, `idx`, `pair` and `pos`. The text goes on in line 202. |
| 202 | `            "tag t waited_s 0 loadavg 0.10 0.10 0.10 1/900 logins 1" % (binary, cpu, session, session, idx, pair, pos))` | Continues line 201: the tag `t`, a wait of 0 s, the load record and 1 login. The values of the line follow. |
| 205 | `def synth_rows(rates):` | Starts the function `synth_rows`. It builds the rows of one invented process from a list of rates. |
| 206 | `    out = ["# bandwidth: synthetic", "kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,x,y,z"]` | `out`: a comment line and a line of column names, as the benchmark prints them. |
| 207 | `    out += ["read,1,8388608,%d,1,0.5,%.2f,%.2f,%.2f,%.2f" % (i, r, r, r, r) for i, r in enumerate(rates)]` | Adds one row per rate: the kernel `read`, 1 thread, 8388608 bytes, the repetition number, and the rate with 2 decimals in the columns 7 to 10. |
| 208 | `    if rates:` | Only when the list has a rate. |
| 209 | `        out.append("read,1,8388608,best,,,%.2f,,," % max(rates))` | Adds the `best` line with the highest rate. |
| 210 | `    return out` | Returns the lines. |
| 213 | `def analyze(*argv):` | Starts the function `analyze`. It runs `h2_analyze.py` inside this process. |
| 214 | `    buf, err = io.StringIO(), io.StringIO()` | `buf` and `err`: two text buffers in memory. |
| 215 | `    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):` | For the block of this line, everything that is printed goes into `buf`, and everything for the error output goes into `err`. |
| 216 | `        rc = h2_analyze.main(list(argv))` | `rc`: the return value of `main` of `h2_analyze.py`, called with the given arguments. It is the exit status that the script would give. |
| 217 | `    return rc, buf.getvalue(), err.getvalue()` | Returns the status, the output text and the error text. |
| 220 | `def main():` | Starts the function `main`. |
| 221 | `    top = tempfile.mkdtemp(prefix="test_h2_")` | `top`: a new temporary folder whose name starts with `test_h2_`. |
| 222 | `    try:` | Starts a block. |
| 223 | `        tests(top)` | Runs all checks (line 233). |
| 224 | `    finally:` | In every case, also after an error. |
| 225 | `        if os.environ.get("KEEP"):` | Tests whether the environment variable `KEEP` is set and not empty. |
| 226 | `            print("kept: %s" % top)` | Then it prints the path of the folder and keeps it. |
| 227 | `        else:` | If not. |
| 228 | `            shutil.rmtree(top, ignore_errors=True)` | It deletes the folder with all its content. |
| 229 | `    print("%d checks failed" % len(failed) if failed else "all checks passed")` | Prints the number of failed checks, or `all checks passed`. |
| 230 | `    return 1 if failed else 0` | Returns 1 when a check failed and 0 when none failed. |

### `tests`: checks on the texts of the scripts (lines 233 to 252)

| Line | Source | Explanation |
|---:|---|---|
| 233 | `def tests(top):` | Starts the function `tests`. It holds all checks of `run_h2.sh`. Its last line calls the checks of the analysis (line 425). |
| 234 | `    # ---- the files ----` | Comment: the first group reads the files. |
| 235 | `    for f in (RUN, VISIT):` | Loop over `run_h2.sh` and `visit_h2.sh`. |
| 236 | `        r = subprocess.run(["bash", "-n", f], stderr=subprocess.PIPE, universal_newlines=True)` | Runs `bash -n` on the file. With `-n` Bash reads the script and tests its syntax without running a command of it. |
| 237 | `        check("syntax %s" % os.path.basename(f), r.returncode == 0, r.stderr)` | Check: the syntax is right, which `bash -n` shows with exit status 0. |
| 238 | `    text = open(RUN).read()` | `text`: the whole text of `run_h2.sh`. |
| 239 | `    check("run_h2.sh never calls sudo, ssh, scp, gcc or make",` | Check: `run_h2.sh` never calls `sudo`, `ssh`, `scp`, `gcc` or `make`. The condition is in line 240. |
| 240 | `          not re.search(r"^[^#\n]*\b(sudo\|ssh\|scp\|gcc\|make)\b", text, re.M))` | Continues line 239: no line holds one of the five words as a whole word before its first `#`. In the pattern `[^#\n]*` matches the part of a line before a comment sign, and `\b` matches a word border. `re.M` lets the pattern start at every line. So the code part of the script names none of the five commands: `sudo` for root rights, `ssh` and `scp` for a login or a copy to another machine, `gcc` and `make` for a build. The check looks for these five names only. |
| 241 | `    check("run_h2.sh pins itself to CPUs 0-119", "exec taskset -c 0-119" in text)` | Check: the text holds `exec taskset -c 0-119`. With that line `run_h2.sh` starts itself again under `taskset`. So the script and its processes may run on the CPUs 0 to 119 only. |
| 242 | `    check("run_h2.sh holds the two digests of handoff.md",` | Check: the text holds the two sha256 values that the handoff note of 2026-11-13 gives for `bw_old` and `bw_new` [Ref3]. The condition is in lines 243 to 244. |
| 243 | `          "e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa" in text` | Continues line 242: the value for `bw_old`. |
| 244 | `          and "fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6" in text)` | Continues line 242: the value for `bw_new`. |
| 245 | `    # the option spelling of the original "one" function` | Comment: the next check looks at the spelling of the options in the function `one` of the original script. |
| 246 | `    orig = open(ORIG_RUN).read()` | `orig`: the text of `run_kernels.sh`. |
| 247 | `    check("original run_kernels.sh has the option line this test expects",` | Check: the original script holds the option line that this test expects. The condition is in line 248. |
| 248 | `          '--threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500' in orig and "for bytes in 32K 1M 8M 1G" in orig)` | Continues line 247: the text of `run_kernels.sh` must hold the option line of its function `one`, which ends with `--reps 3 --min-ms 500`, and the loop over the sizes `32K 1M 8M 1G`. The check compares these two fixed texts with the original script. It does not use `OPTIONS` (line 40). So it shows that the original script still has this option line. That `OPTIONS` holds the same options is seen only by reading both texts. |
| 249 | `    vt = open(VISIT).read()` | `vt`: the text of `visit_h2.sh`. |
| 250 | `    check("visit_h2.sh calls ./run_h2.sh after the marker check", "./run_h2.sh $*" in vt and "/tmp/positron-perf.RUNNING" in vt` | Check. Its name says that `visit_h2.sh` calls `run_h2.sh` after the marker check. The text must hold the call of `run_h2.sh` and the path of the marker file. The check does not test the order of the two. The condition goes on in line 251. |
| 251 | `          and "run_bwx8.sh" not in vt.replace("# ", ""))` | Continues line 250: and the text must not hold the name `run_bwx8.sh`. The call of `replace` removes every `#` that a space follows. It removes no comment, so the name is also searched in the comments. |

### `tests`: the dry run and the order of the processes (lines 253 to 280)

| Line | Source | Explanation |
|---:|---|---|
| 253 | `    # ---- dry run ----` | Comment: the next group is the dry run. |
| 254 | `    b = Box(top, "dry")` | `b`: a new set-up with the name `dry`. |
| 255 | `    for s in (1, 2):` | Loop over the sessions 1 and 2. |
| 256 | `        r = b.run("--dry-run", SESSION=str(s))` | Runs `run_h2.sh --dry-run` with `SESSION` set to the session. A dry run prints the command lines and starts no process. |
| 257 | `        lines = dry_lines(r.stdout)` | `lines`: the command lines of the output (line 158). |
| 258 | `        check("dry run session %d: status 0 and 72 command lines" % s, r.returncode == 0 and len(lines) == 72` | Check: exit status 0 and 72 command lines. The condition goes on in line 259. |
| 259 | `              and "count: 72 command lines" in r.stdout, (r.returncode, len(lines), r.stderr))` | Continues line 258: and the output holds `count: 72 command lines`. The values at the end of the line are shown when the check fails. |
| 260 | `        check("dry run session %d: prints process count and nominal work first" % s,` | Check: the first output line gives the process count, and the output gives the nominal work. The condition is in line 261. |
| 261 | `              r.stdout.startswith("H2 session %d: 72 processes" % s) and "nominal kernel work 108.000 s" in r.stdout, r.stdout[:200])` | Continues line 260: the output starts with `H2 session`, the session number and `72 processes`, and it holds `nominal kernel work 108.000 s`. 108 s is 72 processes times 3 repetitions of 0.5 s. |
| 262 | `        bad = [l for l in lines if not re.match(r"bw_(old\|new) " + re.escape(OPTIONS).replace("%s", r"(2\|0\|41)") + r"  # ", l)]` | `bad`: the command lines that do not have the expected form: `bw_old` or `bw_new`, the options of `OPTIONS` with the CPU 2, 0 or 41, two spaces, `#` and a space. `re.escape` makes the option text a literal pattern. |
| 263 | `        check("dry run session %d: every line has the original options" % s, not bad, bad[:2])` | Check: no such line exists. So every process would start with the original options. |
| 264 | `        check("dry run session %d: the order is balanced" % s, not order_problems(dry_order(r.stdout), s), order_problems(dry_order(r.stdout), s)[:3])` | Check: the order of the dry run has no problem under `order_problems` (line 162). |
| 265 | `        check("dry run session %d: warns about each test setting" % s,` | Check: the dry run warns about each of the six test settings. The condition is in line 266. |
| 266 | `              all("warning: %s is set" % v in r.stderr for v in ("H2_DIR", "H2_SHA256_OLD", "H2_SHA256_NEW", "BWX8_MARKER", "BWX8_STOPFILE", "BWX8_RESULTS")))` | Continues line 265: the error output holds `warning: NAME is set` for all six names. So a run with a test setting left in the environment would show a warning. |
| 267 | `    check("dry run: no result folder, no process started", b.folders() == [] and b.calls() == [])` | Check: the dry runs made no result folder and started no dummy. |
| 268 | `    r1, r2 = dry_order(b.run("--dry-run", SESSION="1").stdout), dry_order(b.run("--dry-run", SESSION="2").stdout)` | `r1` and `r2`: the orders of a dry run of session 1 and of a dry run of session 2. |
| 269 | `    check("session 2 reverses the CPU order and the first binary of every pair",` | Check: session 2 reverses the CPU order and the first binary of every pair. The condition is in lines 270 to 271. |
| 270 | `          [x[0] for x in r2[::24]] == [x[0] for x in r1[::24]][::-1]` | Continues line 269: the CPUs of the three blocks of session 2 are those of session 1 in the reversed order. `[::24]` takes every 24th process, the first of each block. |
| 271 | `          and all(dict(((x[0], x[1], x[2]), x[3]) for x in r1)[(y[0], y[1], y[2])] != y[3] for y in r2))` | Continues line 269: and for every CPU, pair and place, session 2 has the other binary than session 1. |
| 272 | `    # the order rule can fail: a changed order must be reported` | Comment: the order rule can fail. A changed order must be reported. |
| 273 | `    sw = list(r1)` | `sw`: a copy of the order of session 1. |
| 274 | `    sw[2], sw[3] = (sw[2][0], sw[2][1], "1", sw[3][3]), (sw[3][0], sw[3][1], "2", sw[2][3])` | Swaps the binaries of the processes 2 and 3 of the copy. These are the two processes of pair 2 on the first CPU. Then one binary is first in 7 pairs. |
| 275 | `    check("order rule reports an unbalanced order", order_problems(sw, 1) and order_problems(r1, 2) and order_problems(r1[:70], 1))` | Check: `order_problems` reports a problem for three wrong orders: the swapped copy, the order of session 1 judged as session 2, and an order with only 70 processes. This shows that the rule of line 264 can fail. |
| 276 | `    r = b.run("--dry-run", "--from", "70", SESSION="1")` | Runs a dry run with `--from 70`. |
| 277 | `    check("dry run --from 70: 2 command lines", r.returncode == 0 and len(dry_lines(r.stdout)) == 2 and "count: 2 command lines" in r.stdout)` | Check: exit status 0 and 2 command lines, for the processes 70 and 71. |
| 278 | `    r = b.run("--dry-run", "--from", "72", SESSION="1")` | Runs a dry run with `--from 72`. |
| 279 | `    check("dry run --from 72: status 2", r.returncode == 2, r.returncode)` | Check: exit status 2. No process has the number 72. |

### `tests`: wrong use, and the checksums of the binaries (lines 281 to 302)

| Line | Source | Explanation |
|---:|---|---|
| 281 | `    # ---- usage ----` | Comment: the next group is the usage. |
| 282 | `    r = b.run("--dry-run", SESSION=None)` | Runs a dry run without `SESSION`. |
| 283 | `    check("no SESSION: status 2", r.returncode == 2 and "set SESSION" in r.stderr)` | Check: exit status 2, and the error output holds `set SESSION`. |
| 284 | `    r = b.run("--dry-run", "S2", SESSION="1")` | Runs a dry run with the unknown argument `S2`. |
| 285 | `    check("unknown argument: status 2", r.returncode == 2)` | Check: exit status 2. |
| 286 | `    r = b.run(SESSION="1")` | Runs the script without `--dry-run`, with `SESSION` and without `STOP_AT`. |
| 287 | `    check("no STOP_AT: status 2, nothing started", r.returncode == 2 and "set STOP_AT" in r.stderr and b.calls() == [] and b.folders() == [])` | Check: exit status 2, the message `set STOP_AT`, no dummy started and no result folder. So a real run needs a stop time or the word `none`. |
| 289 | `    # ---- digest ----` | Comment: the next group is the checksums, which the comment calls digests. |
| 290 | `    b = Box(top, "digest")` | `b`: a new set-up with the name `digest`. |
| 291 | `    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_NEW="0" * 64)` | Runs the script with a wrong expected sha256 for `bw_new`: 64 zeros. |
| 292 | `    check("digest of bw_new differs: status 2, nothing started", r.returncode == 2 and "bw_new does not have the expected sha256" in r.stderr` | Check: exit status 2, and the error output says that `bw_new` does not have the expected sha256. The condition goes on in line 293. |
| 293 | `          and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))` | Continues line 292: and no dummy was started and no result folder exists. The values at the end are shown when the check fails. |
| 294 | `    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_OLD="0" * 64)` | The same run with a wrong expected sha256 for `bw_old`. |
| 295 | `    check("digest of bw_old differs: status 2, nothing started", r.returncode == 2 and "bw_old does not have the expected sha256" in r.stderr` | Check: exit status 2, and the error output says that `bw_old` does not have the expected sha256. The condition goes on in line 296. |
| 296 | `          and b.calls() == [] and b.folders() == [])` | Continues line 295: and no dummy was started and no result folder exists. |
| 297 | `    r = b.run(SESSION="1", STOP_AT="none", H2_SHA256_OLD=None, H2_SHA256_NEW=None)` | Runs the script without the two test settings for the checksums. Then `run_h2.sh` uses its built-in values, the checksums of the real binaries. |
| 298 | `    check("dummy binaries against the real digests: status 2, nothing started", r.returncode == 2 and b.calls() == [] and b.folders() == [])` | Check: exit status 2 and nothing started. So a file that is not the original binary cannot run under its name. |
| 299 | `    os.remove(os.path.join(b.bin, "bw_new"))` | Deletes the dummy `bw_new`. |
| 300 | `    r = b.run(SESSION="1", STOP_AT="none")` | Runs the script. |
| 301 | `    check("missing bw_new: status 2, no rebuild", r.returncode == 2 and "missing" in r.stderr and not os.path.exists(os.path.join(b.bin, "bw_new")))` | Check: exit status 2, a message with the word `missing`, and the file still does not exist. So the script does not build a missing binary. |

### `tests`: the stop controls before the first process, and session 2 (lines 303 to 337)

| Line | Source | Explanation |
|---:|---|---|
| 303 | `    # ---- stop controls before the first process ----` | Comment: the next group is the stop controls before the first process. |
| 304 | `    b = Box(top, "stops")` | `b`: a new set-up with the name `stops`. |
| 305 | `    open(b.marker, "w").close()` | Creates the marker file of the set-up as an empty file. |
| 306 | `    r = b.run(SESSION="1", STOP_AT="none")` | Runs the script. |
| 307 | `    check("marker file present: status 3, nothing started", r.returncode == 3 and "RUNNING file present" in r.stderr and b.calls() == [] and b.folders() == [],` | Check: exit status 3, the message `RUNNING file present`, no dummy started and no result folder. The line goes on in line 308. |
| 308 | `          (r.returncode, r.stderr[-200:]))` | Continues line 307: the values that are shown when the check fails. |
| 309 | `    os.remove(b.marker)` | Deletes the marker file. |
| 310 | `    open(b.stopfile, "w").close()` | Creates the stop file. |
| 311 | `    r = b.run(SESSION="1", STOP_AT="none")` | Runs the script. |
| 312 | `    check("stop file present: status 5, nothing started", r.returncode == 5 and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))` | Check: exit status 5 and nothing started. |
| 313 | `    os.remove(b.stopfile)` | Deletes the stop file. |
| 314 | `    r = b.run(SESSION="1", STOP_AT=utc(-60))` | Runs the script with a `STOP_AT` that lies 60 s in the past. |
| 315 | `    check("STOP_AT in the past: status 4, nothing started", r.returncode == 4 and b.calls() == [] and b.folders() == [], (r.returncode, r.stderr[-200:]))` | Check: exit status 4 and nothing started. |
| 316 | `    r = b.run(SESSION="1", STOP_AT=utc(60))` | Runs the script with a `STOP_AT` that lies 60 s ahead. |
| 317 | `    check("STOP_AT 60 s away (MARGIN 92 s): status 4, nothing started", r.returncode == 4 and "less than 92 s away" in r.stderr and b.calls() == [],` | Check: exit status 4, the message `less than 92 s away`, and no dummy started. The margin of `run_h2.sh` is 92 s: 2 s for the nominal work of one process, rounded up from 1.5 s, plus a reserve of 90 s. So no process starts that could run past `STOP_AT`. The line goes on in line 318. |
| 318 | `          (r.returncode, r.stderr[-200:]))` | Continues line 317: the values that are shown when the check fails. |
| 319 | `    r = b.run(SESSION="1", STOP_AT="not-a-time")` | Runs the script with a `STOP_AT` that is no time. |
| 320 | `    check("bad STOP_AT: status 2", r.returncode == 2 and b.calls() == [])` | Check: exit status 2 and no dummy started. |
| 322 | `    # ---- session 2 ----` | Comment: the next group is session 2. |
| 323 | `    r = b.run(SESSION="2", STOP_AT="none")` | Runs session 2 without `SESSION1_END`. |
| 324 | `    check("session 2 without SESSION1_END: status 2", r.returncode == 2 and "needs SESSION1_END" in r.stderr and b.calls() == [])` | Check: exit status 2 and the message `needs SESSION1_END`. |
| 325 | `    r = b.run(SESSION="2", STOP_AT="none", SESSION1_END=utc(-10800 + 120))` | Runs session 2 with a `SESSION1_END` of 2 h 58 min ago: 10800 s minus 120 s. |
| 326 | `    check("session 2 two minutes too early: status 2, nothing started", r.returncode == 2 and "3 hours after" in r.stderr and b.calls() == [] and b.folders() == [],` | Check: exit status 2, the message `3 hours after`, and nothing started. So session 2 cannot start earlier than 3 hours after the end of session 1. The line goes on in line 327. |
| 327 | `          (r.returncode, r.stderr[-200:]))` | Continues line 326: the values that are shown when the check fails. |
| 328 | `    r = b.run(SESSION="2", STOP_AT="none", SESSION1_END="yesterday")` | Runs session 2 with the word `yesterday` as `SESSION1_END`. |
| 329 | `    check("session 2 with a SESSION1_END that is not a full UTC time: status 2", r.returncode == 2 and "bad SESSION1_END" in r.stderr and b.calls() == [])` | Check: exit status 2 and the message `bad SESSION1_END`. By a comment of `run_h2.sh` the program `date` also accepts relative words, so the script tests the form of the time itself. |
| 330 | `    r = b.run("--from", "70", SESSION="2", STOP_AT="none", SESSION1_END=utc(-10800 - 120))` | Runs session 2 from process 70 on, with a `SESSION1_END` of 3 h 2 min ago. |
| 331 | `    f = b.folders()` | `f`: the result folders. |
| 332 | `    check("session 2 three hours and two minutes after session 1: runs (--from 70: 2 processes)",` | Check: the run works. The condition is in line 333. |
| 333 | `          r.returncode == 0 and len(b.calls()) == 2 and len(f) == 1 and re.match(r"h2-s2-\d{8}T\d{6}Z$", f[0]), (r.returncode, r.stderr[-300:], f))` | Continues line 332: exit status 0, 2 dummies started, one result folder, and its name has the form `h2-s2-`, a date of 8 digits, `T`, a time of 6 digits and `Z`. |
| 334 | `    if f:` | Only when a result folder exists. |
| 335 | `        env = open(os.path.join(b.results, f[0], "env.txt")).read()` | `env`: the text of the file `env.txt` in it. |
| 336 | `        check("--from is recorded in env.txt", " from=70 " in env and "to_run_processes=2" in env)` | Check: `env.txt` holds `from=70` and `to_run_processes=2`. So a continued session is visible in the record of the run. |

### `tests`: stops while a process runs (lines 338 to 371)

| Line | Source | Explanation |
|---:|---|---|
| 338 | `    # ---- marker appears while a process runs ----` | Comment: the next group: the marker file appears while a process runs. |
| 339 | `    b = Box(top, "midmark")` | `b`: a new set-up with the name `midmark`. |
| 340 | `    r = b.run(SESSION="1", STOP_AT="none", DUMMY_MARK_AT="3")` | Runs the script with `DUMMY_MARK_AT` set to 3. So the third dummy creates the marker file and sleeps 30 s. |
| 341 | `    f = b.folders()` | `f`: the result folders. |
| 342 | `    csv = open(os.path.join(b.results, f[0], "H2.csv")).read() if f else ""` | `csv`: the text of `H2.csv`, or an empty text. |
| 343 | `    check("marker appears during process 3: status 3, the process is killed, no later process starts",` | Check: exit status 3, the process is killed, and no later process starts. The condition is in lines 344 to 345. |
| 344 | `          r.returncode == 3 and len(b.calls()) == 3 and csv.count("-- binary") == 3 and csv.count("read,1,8388608,best") == 2` | Continues line 343: 3 dummies were started, the csv file has 3 header lines, and it has only 2 `best` lines. The third dummy was stopped before its last line. |
| 345 | `          and re.search(r"^-- killed tag s1-c2-p02-new status 3 ", csv, re.M), (r.returncode, len(b.calls()), r.stderr[-200:]))` | Continues line 343: and the csv file holds the line `-- killed tag s1-c2-p02-new status 3`. This tag is the third process of session 1: CPU 2, pair 2, `bw_new` first. |
| 346 | `    check("marker appears during process 3: no process of its group is left", not group_left(b))` | Check: no process of the group of that dummy is left (line 119). So no benchmark process stays on the machine after a stop. |
| 347 | `    # ---- interruption and stop file while a process runs: the process group must be gone afterwards ----` | Comment: the next group: a signal or the stop file while a process runs. Afterwards the process group must be gone. |
| 348 | `    for sig, name in ((15, "TERM"), (2, "INT"), (1, "HUP")):` | Loop over three signals: 15 (TERM), 2 (INT) and 1 (HUP). |
| 349 | `        b = Box(top, "sig" + name)` | `b`: a new set-up per signal. |
| 350 | `        rc, csv = run_until_sleep(b, lambda p, sig=sig: p.send_signal(sig), SESSION="1", STOP_AT="none", DUMMY_SLEEP_AT="2")` | Starts the script with `DUMMY_SLEEP_AT` set to 2, and sends it the signal when the second dummy sleeps (line 134). |
| 351 | `        check("signal %s during process 2: status 130, a 'killed' line, no later process, no process of its group is left" % name,` | Check: exit status 130, a `killed` line, no later process, and no process of the group left. The condition is in line 352. |
| 352 | `              rc == 130 and len(b.calls()) == 2 and re.search(r"^-- killed tag s1-c2-p01-new status 130 ", csv, re.M) and not group_left(b),` | Continues line 351: 2 dummies were started, the csv file holds the line `-- killed tag s1-c2-p01-new status 130`, and no process of the group is left. |
| 353 | `              (rc, len(b.calls()), group_left(b)))` | Continues line 351: the values that are shown when the check fails. |
| 354 | `    b = Box(top, "midstop")` | `b`: a new set-up with the name `midstop`. |
| 355 | `    rc, csv = run_until_sleep(b, lambda p: open(b.stopfile, "w").close(), SESSION="1", STOP_AT="none", DUMMY_SLEEP_AT="1")` | Starts the script with `DUMMY_SLEEP_AT` set to 1, and creates the stop file when the first dummy sleeps. |
| 356 | `    check("stop file appears during process 1: status 5, a 'killed' line, no later process, no process of its group is left",` | Check: exit status 5, a `killed` line, no later process, and no process of the group left. The condition is in line 357. |
| 357 | `          rc == 5 and len(b.calls()) == 1 and re.search(r"^-- killed tag s1-c2-p01-old status 5 ", csv, re.M) and not group_left(b),` | Continues line 356: 1 dummy was started, and the csv file holds the line `-- killed tag s1-c2-p01-old status 5`. |
| 358 | `          (rc, len(b.calls()), group_left(b)))` | Continues line 356: the values that are shown when the check fails. |
| 359 | `    b = Box(top, "midstopat")` | `b`: a new set-up with the name `midstopat`. |
| 360 | `    t0 = time.time()` | `t0`: the time before the start. |
| 361 | `    rc, csv = run_until_sleep(b, lambda p: None, SESSION="1", STOP_AT=utc(60), RESERVE="5", DUMMY_SLEEP_AT="1")` | Starts the script with a `STOP_AT` that lies 60 s ahead, a reserve of 5 s and `DUMMY_SLEEP_AT` set to 1. With this reserve the margin is 7 s, so the first process may start. `act` does nothing: `STOP_AT` is reached while the dummy sleeps. By its code `run_h2.sh` then needs 1 to 2 s to end: it looks at the time once per second and waits 1 s after its first kill signal. The helper waits 60 s for that end, counted from about 0.5 s after the dummy started to sleep (lines 142 to 145). So the 60 s can be over before the script ends, when the dummy starts to sleep less than about 1.5 s after this line computed `STOP_AT`. This follows from the code and was not tested for this page. |
| 362 | `    check("STOP_AT is reached during process 1: status 4, a 'killed' line, no process of its group is left",` | Check: exit status 4, a `killed` line, and no process of the group left. The condition is in line 363. |
| 363 | `          rc == 4 and len(b.calls()) == 1 and re.search(r"^-- killed tag s1-c2-p01-old status 4 ", csv, re.M) and not group_left(b),` | Continues line 362: 1 dummy was started, and the csv file holds the line `-- killed tag s1-c2-p01-old status 4`. |
| 364 | `          (rc, len(b.calls()), group_left(b), time.time() - t0))` | Continues line 362: the values that are shown when the check fails, with the time that the case took. |
| 365 | `    b = Box(top, "fail")` | `b`: a new set-up with the name `fail`. |
| 366 | `    r = b.run(SESSION="1", STOP_AT="none", DUMMY_FAIL_AT="2")` | Runs the script with `DUMMY_FAIL_AT` set to 2. So the second dummy ends with exit status 7. |
| 367 | `    f = b.folders()` | `f`: the result folders. |
| 368 | `    csv = open(os.path.join(b.results, f[0], "H2.csv")).read() if f else ""` | `csv`: the text of `H2.csv`, or an empty text. |
| 369 | `    check("a benchmark fails: status 1, a 'failed' line, no later process", r.returncode == 1 and len(b.calls()) == 2 and "-- failed tag s1-c2-p01-new exit 7" in csv,` | Check: exit status 1, 2 dummies started, and the line `-- failed tag s1-c2-p01-new exit 7` in the csv file. So a failed benchmark stops the session. The line goes on in line 370. |
| 370 | `          (r.returncode, len(b.calls())))` | Continues line 369: the values that are shown when the check fails. |

### `tests`: a full run of session 1 with 72 dummy processes (lines 372 to 427)

| Line | Source | Explanation |
|---:|---|---|
| 372 | `    # ---- a full run of session 1 ----` | Comment: the next group is a full run of session 1. |
| 373 | `    b = Box(top, "full")` | `b`: a new set-up with the name `full`. |
| 374 | `    r = b.run(SESSION="1", STOP_AT=utc(7200), timeout=2400)` | Runs the whole session 1 with a `STOP_AT` that lies 2 hours ahead. The test allows the run 2400 s (40 min). |
| 375 | `    f = b.folders()` | `f`: the result folders. |
| 376 | `    check("full run: status 0, one folder h2-s1-<UTC>", r.returncode == 0 and len(f) == 1 and re.match(r"h2-s1-\d{8}T\d{6}Z$", f[0] if f else ""),` | Check: exit status 0 and one result folder with a name of the form `h2-s1-` and a UTC time. The line goes on in line 377. |
| 377 | `          (r.returncode, r.stderr[-300:], f))` | Continues line 376: the values that are shown when the check fails. |
| 378 | `    out = os.path.join(b.results, f[0]) if f else ""` | `out`: the path of the result folder, or an empty text. |
| 379 | `    if f:` | The checks from here to line 423 run only when a result folder exists. |
| 380 | `        check("full run: the folder holds exactly H2.csv env.txt launches.txt order.tsv stderr.txt",` | Check: the folder holds exactly five files. The condition is in line 381. |
| 381 | `              sorted(os.listdir(out)) == ["H2.csv", "env.txt", "launches.txt", "order.tsv", "stderr.txt"], sorted(os.listdir(out)))` | Continues line 380: `H2.csv`, `env.txt`, `launches.txt`, `order.tsv` and `stderr.txt`. |
| 382 | `        check("full run: nothing written outside the result folder and the dummy call log",` | Check: nothing was written outside the result folder and the call log of the dummies. The condition is in line 383. |
| 383 | `              sorted(os.listdir(b.dir)) == ["bin", "results"] and sorted(os.listdir(b.bin)) == ["bw_new", "bw_old", "calls.log"])` | Continues line 382: the set-up folder holds only `bin` and `results`, and `bin` holds only the two dummies and `calls.log`. The home folder of the run is the set-up folder (line 103), so a file below the home folder would show here. |
| 384 | `        check("full run: prints process count and nominal work before the start", r.stdout.startswith("H2 session 1: 72 processes") and` | Check: the script prints the process count and the nominal work before the start. The output must start with `H2 session 1: 72 processes`. The condition goes on in line 385. |
| 385 | `              r.stdout.index("H2 session 1") < r.stdout.index("result folder:"))` | Continues line 384: and this text must stand before the line `result folder:`, which the script prints when it has made the folder. |
| 386 | `        order = [l.split("\t") for l in open(os.path.join(out, "order.tsv")).read().splitlines()]` | `order`: the lines of `order.tsv`, each split at the tabs. |
| 387 | `        saved = [(x[1], x[2], x[3], x[4]) for x in order[1:]]` | `saved`: the order without its heading: CPU, pair, place and binary per process. |
| 388 | `        check("full run: order.tsv is saved, balanced, and numbered 0 to 71",` | Check: `order.tsv` is saved, balanced, and numbered 0 to 71. The condition is in lines 389 to 390. |
| 389 | `              order[0] == ["idx", "cpu", "pair", "pos", "binary"] and [x[0] for x in order[1:]] == [str(i) for i in range(72)]` | Continues line 388: the heading is `idx`, `cpu`, `pair`, `pos`, `binary`, and the first column counts from 0 to 71. |
| 390 | `              and not order_problems(saved, 1), order_problems(saved, 1)[:3])` | Continues line 388: and the saved order has no problem under `order_problems`. |
| 391 | `        check("full run: order.tsv equals the dry run", saved == r1)` | Check: the saved order equals the order of the dry run of session 1 (line 268). So a dry run shows the order that a real run uses. |
| 392 | `        calls = b.calls()` | `calls`: the call log of the dummies. |
| 393 | `        check("full run: 72 processes started, in the saved order, each with the original options",` | Check: 72 processes were started, in the saved order, each with the original options. The condition is in line 394. |
| 394 | `              calls == ["%s %s" % (x[3], OPTIONS % x[0]) for x in saved], calls[:2])` | Continues line 393: the log equals the list of binary and `OPTIONS` with the CPU, built from the saved order. |
| 395 | `        csv = open(os.path.join(out, "H2.csv")).read().splitlines()` | `csv`: the lines of `H2.csv`. |
| 396 | `        heads = [l for l in csv if l.startswith("-- ")]` | `heads`: the lines that start with `--` and a space: the header lines. |
| 397 | `        want = [r"-- binary %s kernel read threads 1 cpus %s bytes 8M round 1 load \S+ utc \d\d:\d\d:\d\d session 1 idx %d pair %s pos %s tag \S+ waited_s \d+ "` | `want`: one pattern per process for its header line: the binary, the kernel `read`, 1 thread, the CPU, 8 MiB, round 1, a load value, a time, session 1, and the `idx`, the pair and the place of the saved order. The text goes on in line 398. |
| 398 | `                % (x[3], x[0], i, x[1], x[2]) for i, x in enumerate(saved)]` | Continues line 397: the values of each pattern, and the loop over the saved order. |
| 399 | `        check("full run: H2.csv has one header line per process, in the saved order",` | Check: `H2.csv` has one header line per process, in the saved order. The condition is in line 400. |
| 400 | `              len(heads) == 72 and all(re.match(w, h) for w, h in zip(want, heads)), heads[:1])` | Continues line 399: 72 header lines, and each one fits its pattern. |
| 401 | `        check("full run: every header is followed by 3 repetition rows",` | Check: every header line is followed by 3 repetition rows. The condition is in line 402. |
| 402 | `              len([l for l in csv if re.match(r"read,1,8388608,[012],", l)]) == 216 and all(csv[i + 3].startswith("read,1,8388608,0,") for i, l in enumerate(csv) if l.startswith("-- ")))` | Continues line 401: the file has 216 rows of the repetitions 0, 1 and 2 (72 times 3), and the third line after each header line is the row of repetition 0. The two lines between are the comment line and the column names. |
| 403 | `        sys.path.insert(0, os.path.dirname(h2_analyze.ORIGINAL))` | Puts the folder of the original `one-thread.csv` at the front of the module search path. That result folder also holds the script `summarize.py` of the original run. |
| 404 | `        try:` | Starts a block. |
| 405 | `            import summarize` | Imports that `summarize.py`. |
| 406 | `            d, loads = summarize.load(os.path.join(out, "H2.csv"))` | Reads `H2.csv` with its function `load`. `d` maps size, kernel and binary to the list of the rates. `loads` holds one load value per header line. |
| 407 | `            check("full run: the original summarize.py reads H2.csv (36 repetitions per binary and CPU... 108 per binary)",` | Check: the original `summarize.py` reads `H2.csv`. The condition is in line 408. |
| 408 | `                  len(loads) == 72 and len(d["8M", "read", "bw_old"]) == 108 and len(d["8M", "read", "bw_new"]) == 108)` | Continues line 407: 72 load values, and 108 rates each for `bw_old` and for `bw_new` at 8 MiB (36 processes times 3). So the header line of `run_h2.sh` still fits the tool of the original run. |
| 409 | `        except Exception as e:  # noqa: BLE001` | Any error in the block. |
| 410 | `            check("full run: the original summarize.py reads H2.csv", False, e)` | Then the check counts as failed, with the error as its detail. |
| 411 | `        launches = open(os.path.join(out, "launches.txt")).read()` | `launches`: the text of `launches.txt`. |
| 412 | `        check("full run: launches.txt has one load record per launch", len(re.findall(r"^== H2.csv idx \d+ \S+ utc \S+ loadavg ", launches, re.M)) == 72)` | Check: `launches.txt` has one load record per start: 72 lines that begin with `== H2.csv idx`, a number, a tag, `utc`, a time and `loadavg`. |
| 413 | `        env = open(os.path.join(out, "env.txt")).read()` | `env`: the text of `env.txt`. |
| 414 | `        check("full run: env.txt has the settings, the digests and the end line",` | Check: `env.txt` has the settings, the checksums and the end line. The condition is in lines 415 to 416. |
| 415 | `              "session=1 from=0 " in env and "cpu_order=2 0 41" in env and "planned_processes=72" in env and sha(os.path.join(b.bin, "bw_old")) in env` | Continues line 414: `session=1 from=0`, the CPU order `2 0 41`, 72 planned processes, and the sha256 of the dummy `bw_old`. |
| 416 | `              and sha(os.path.join(b.bin, "bw_new")) in env and re.search(r"^## end utc=", env, re.M) and "DIR=%s" % b.bin in env)` | Continues line 414: the sha256 of the dummy `bw_new`, a line that starts with `## end utc=`, and the folder of the dummies as `DIR`. |
| 417 | `        rc, text, err = analyze("--results", b.results)` | Runs `h2_analyze.py` on the results folder of the set-up (line 213). |
| 418 | `        check("h2_analyze.py on the full dummy run: status 0, 12 pairs per CPU",` | Check: status 0 and 12 pairs per CPU. The condition is in line 419. |
| 419 | `              rc == 0 and len(re.findall(r"^  pair summary: 12 pairs", text, re.M)) == 3 and "H2 runs: 1 file(s)" in text, (rc, err))` | Continues line 418: three lines with `pair summary: 12 pairs`, one per CPU, and the text `H2 runs: 1 file(s)`. |
| 420 | `        check("h2_analyze.py on the full dummy run: CPU 41 repetitions are low, between, high",` | Check: the repetitions of the dummy `bw_new` on CPU 41 are classed low, between and high. The condition is in lines 421 to 423. |
| 421 | `              "  session 1 CPU  41: 12 pairs \| gain of medians: median   4.46 % \| new repetitions: low 12, between 12, high 12" in text` | Continues line 420: the summary line of CPU 41: 12 pairs, a median gain of 4.46 %, and 12 repetitions in each class. The dummy rates 69.10, 70.00 and 71.60 GB/s fall into the three classes. The gain is 70.00 against 67.01 GB/s, the medians of the two dummies. |
| 422 | `              and "  session 1 CPU   2: 12 pairs \| gain of medians: median   0.88 % \| new repetitions: low 36, between 0, high 0" in text,` | Continues line 420: the summary line of CPU 2: 12 pairs, a median gain of 0.88 % (67.60 against 67.01 GB/s), and all 36 repetitions low. |
| 423 | `              [l for l in text.splitlines() if l.startswith("  session")])` | Continues line 420: the summary lines are shown when the check fails. |
| 425 | `    analyzer_tests(top)` | Runs the checks of the analysis script (line 428). |

### `analyzer_tests`: the two small functions, and the numbers of the original run (lines 428 to 445)

| Line | Source | Explanation |
|---:|---|---|
| 428 | `def analyzer_tests(top):` | Starts the function `analyzer_tests`. It holds the checks of `h2_analyze.py`. |
| 429 | `    # ---- the functions ----` | Comment: the first group is the functions. |
| 430 | `    c = h2_analyze.classify` | `c`: a short name for the function `classify` of the analysis. It gives the class of one rate for a low limit and a high limit. |
| 431 | `    check("classify: borders", (c(69.5, 69.5, 70.5), c(69.51, 69.5, 70.5), c(70.49, 69.5, 70.5), c(70.5, 69.5, 70.5), c(67.7, 69.5, 70.5), c(71.6, 69.5, 70.5))` | Check: the borders of the classes, with a low limit of 69.5 GB/s and a high limit of 70.5 GB/s. The line goes on in line 432. |
| 432 | `          == ("low", "between", "between", "high", "low", "high"))` | Continues line 431: 69.5 is low, 69.51 and 70.49 are between, 70.5 is high, 67.7 is low and 71.6 is high. So a rate that equals a limit belongs to the class of that limit. |
| 433 | `    check("gain: 100 x (new / old - 1)", abs(h2_analyze.gain(67.71, 67.08) - 0.9392) < 1e-3 and h2_analyze.gain(60.0, 80.0) == -25.0)` | Check: `gain` is 100 times (new divided by old, minus 1), in percent. 67.71 against 67.08 gives 0.9392 within 0.001, and 60.0 against 80.0 gives -25.0. |
| 435 | `    # ---- the original run ----` | Comment: the next group is the original run. |
| 436 | `    rc, text, err = analyze("--results", os.path.join(top, "none"))` | Runs the analysis with a results folder that does not exist. The analysis still reads the file `one-thread.csv` of the original run of 2026-11-13 from its fixed path. |
| 437 | `    check("original numbers: status 0 and the note that no H2 file exists", rc == 0 and "no H2.csv found" in text, (rc, err))` | Check: status 0, and the output holds the note `no H2.csv found`. |
| 438 | `    check("original numbers: best rates 67.08 and 67.71 GB/s, gain 0.94 %, class low",` | Check: the numbers of the original run. The condition is in line 439. |
| 439 | `          "original, all CPUs: old best  67.08 \| new best  67.71 \| gain of the best repetitions   0.94 % \| class of the new best: low" in text)` | Continues line 438: the output holds the line with the best rate of old read (67.08 GB/s), the best rate of new read (67.71 GB/s), the gain of 0.94 % between them, and the class `low` of the new best rate. The csv file of the original run holds these two rates [Ref4]. |
| 440 | `    gm = re.findall(r"^  pair  \d \((?:old\|new) first\): .* gain of medians +(\S+) %", text, re.M)` | `gm`: the gains of the medians from all pair lines of the output. The pattern finds the lines that start with two spaces, `pair`, two spaces and one digit, then `(old first)` or `(new first)`. Its group holds the number before the percent sign that follows `gain of medians`. |
| 441 | `    check("original numbers: the four pair gains of the design (0.51, 0.69, 0.94, 0.51 %)", gm == ["0.51", "0.69", "0.94", "0.51"], gm)` | Check: the four pair gains are 0.51, 0.69, 0.94 and 0.51 %. The check name calls them the pair gains of the design. They follow from the csv file of the original run: CPU 0 and then CPU 2, each with round 1 and round 2 [Ref4]. |
| 442 | `    check("original numbers: round 1 ran old first, round 2 new first",` | Check: round 1 ran old first, and round 2 ran new first. The condition is in line 443. |
| 443 | `          len(re.findall(r"^  pair  1 \(old first\)", text, re.M)) == 2 and len(re.findall(r"^  pair  2 \(new first\)", text, re.M)) == 2)` | Continues line 442: the output holds two lines with pair 1 and `(old first)`, and two lines with pair 2 and `(new first)`: one each for the CPUs 0 and 2. |
| 444 | `    check("original numbers: the three repetitions of the new read on CPU 2, round 1", "  new round 1:  67.71  67.66  67.65 \| median  67.66 \| max  67.71" in text)` | Check: the output holds a line of the new read in round 1 with the three repetitions 67.71, 67.66 and 67.65 GB/s, the median 67.66 and the maximum 67.71. By the check name this is the line of CPU 2. The csv file of the original run holds these three rates for `bw_new` on CPU 2 in round 1 [Ref4]. |

### `analyzer_tests`: an invented `H2.csv` with two sessions (lines 446 to 499)

| Line | Source | Explanation |
|---:|---|---|
| 446 | `    # ---- a synthetic H2.csv ----` | Comment: the next group is an invented `H2.csv`. The comment calls it synthetic. |
| 447 | `    res = os.path.join(top, "synth")` | `res`: a results folder with the name `synth` below the temporary folder. |
| 448 | `    d1 = os.path.join(res, "h2-s1-20261115T000000Z")` | `d1`: a result folder of session 1 in it. |
| 449 | `    d2 = os.path.join(res, "h2-s2-20261115T040000Z")` | `d2`: a result folder of session 2 in it. |
| 450 | `    os.makedirs(d1)` | Makes `d1`. |
| 451 | `    os.makedirs(d2)` | Makes `d2`. |
| 452 | `    lines = []` | `lines`: the lines of the first file, empty at first. |
| 453 | `    # session 1, CPU 2: pair 1 old first, pair 2 new first, pair 3 with a killed new process` | Comment: session 1 on CPU 2 has pair 1 with old first, pair 2 with new first, and pair 3 with a killed new process. |
| 454 | `    lines += [synth_header("bw_old", "2", 1, 0, 1, 1)] + synth_rows([67.00, 67.10, 67.20])` | Pair 1, old: 67.00, 67.10 and 67.20 GB/s. |
| 455 | `    lines += [synth_header("bw_new", "2", 1, 1, 1, 2)] + synth_rows([67.50, 69.50, 71.00])       # low low high, median 69.50` | Pair 1, new: 67.50, 69.50 and 71.00 GB/s. By the comment the classes are low, low, high, and the median is 69.50 GB/s. |
| 456 | `    lines += [synth_header("bw_new", "2", 1, 2, 2, 1)] + synth_rows([70.00, 70.50, 71.60])       # between high high` | Pair 2, new first: 70.00, 70.50 and 71.60 GB/s. By the comment the classes are between, high, high. |
| 457 | `    lines += [synth_header("bw_old", "2", 1, 3, 2, 2)] + synth_rows([80.00, 80.00, 80.00])` | Pair 2, old: three times 80.00 GB/s. |
| 458 | `    lines += [synth_header("bw_old", "2", 1, 4, 3, 1)] + synth_rows([67.00, 67.00, 67.00])` | Pair 3, old: three times 67.00 GB/s. |
| 459 | `    lines += [synth_header("bw_new", "2", 1, 5, 3, 2)] + synth_rows([67.50]) + ["-- killed tag t status 3 utc 01:02:03"]` | Pair 3, new: one repetition of 67.50 GB/s, and then a `-- killed` line. |
| 460 | `    # session 1, CPU 41: one pair` | Comment: session 1 on CPU 41 has one pair. |
| 461 | `    lines += [synth_header("bw_new", "41", 1, 48, 1, 1)] + synth_rows([71.60, 71.60, 71.60])` | New first: three times 71.60 GB/s. |
| 462 | `    lines += [synth_header("bw_old", "41", 1, 49, 1, 2)] + synth_rows([71.60, 71.60, 35.80])` | Old: 71.60, 71.60 and 35.80 GB/s. |
| 463 | `    with open(os.path.join(d1, "H2.csv"), "w") as f:` | Opens `H2.csv` in `d1` for writing. |
| 464 | `        f.write("\n".join(lines) + "\n")` | Writes the lines. |
| 465 | `    lines = [synth_header("bw_new", "41", 2, 0, 1, 1)] + synth_rows([69.10, 69.10, 69.10])` | `lines`: now the file of session 2. On CPU 41: new with three times 69.10 GB/s. |
| 466 | `    lines += [synth_header("bw_old", "41", 2, 1, 1, 2)] + synth_rows([69.10, 69.10, 69.10])` | And old with three times 69.10 GB/s. |
| 467 | `    with open(os.path.join(d2, "H2.csv"), "w") as f:` | Opens `H2.csv` in `d2` for writing. |
| 468 | `        f.write("\n".join(lines) + "\n")` | Writes the lines. |
| 469 | `    rc, text, err = analyze("--results", res)` | Runs the analysis on the folder `res`. |
| 470 | `    check("synthetic: status 0, two files, sessions and CPUs in run order",` | Check: status 0, two files, and the sessions and CPUs in run order. The condition is in lines 471 to 472. |
| 471 | `          rc == 0 and "H2 runs: 2 file(s)" in text` | Continues line 470: status 0 and the text `H2 runs: 2 file(s)`. |
| 472 | `          and re.findall(r"^== (session \d, CPU \d+) ==", text, re.M) == ["session 1, CPU 2", "session 1, CPU 41", "session 2, CPU 41"], (rc, err))` | Continues line 470: the headings are `session 1, CPU 2`, `session 1, CPU 41` and `session 2, CPU 41`, in this order. The pattern takes the text between the two `==` marks of the heading lines that name a session and a CPU. |
| 473 | `    check("synthetic: a process line has the three rates, the median and the maximum",` | Check: a process line has the three rates, the median and the maximum. The condition is in lines 474 to 475. |
| 474 | `          "  new idx  1 pair  1 pos 2:  67.50  69.50  71.00 \| median  69.50 \| max  71.00" in text` | Continues line 473: the line of the new process of pair 1, with the median 69.50 and the maximum 71.00 GB/s. |
| 475 | `          and "  old idx  0 pair  1 pos 1:  67.00  67.10  67.20 \| median  67.10 \| max  67.20" in text)` | Continues line 473: the line of the old process of pair 1, with the median 67.10 and the maximum 67.20 GB/s. |
| 476 | `    check("synthetic: pair 1 gain of medians 3.58 %, of maxima 5.65 %, old first",` | Check: pair 1 has a gain of the medians of 3.58 % and a gain of the maxima of 5.65 %, with old first. The condition is in line 477. |
| 477 | `          "  pair  1 (old first): old median  67.10 max  67.20 \| new median  69.50 max  71.00 \| gain of medians   3.58 % \| gain of maxima   5.65 %" in text)` | Continues line 476: the exact pair line. 3.58 % is 69.50 against 67.10 GB/s, and 5.65 % is 71.00 against 67.20 GB/s. |
| 478 | `    check("synthetic: pair 2 gain -11.88 % and -10.50 %, new first",` | Check: pair 2 has gains of -11.88 % and -10.50 %, with new first. The condition is in line 479. |
| 479 | `          "  pair  2 (new first): old median  80.00 max  80.00 \| new median  70.50 max  71.60 \| gain of medians -11.88 % \| gain of maxima -10.50 %" in text)` | Continues line 478: the exact pair line: 70.50 against 80.00 GB/s for the medians, and 71.60 against 80.00 GB/s for the maxima. |
| 480 | `    check("synthetic: the killed process is shown as not complete, and pair 3 is left out",` | Check: the killed process is shown as not complete, and pair 3 is left out. The condition is in lines 481 to 482. |
| 481 | `          "  new idx  5 pair  3 pos 2:  67.50 \| NOT COMPLETE (status killed, 1 of 3 repetitions): left out below" in text` | Continues line 480: the line of the killed process says `NOT COMPLETE`, with the status `killed` and 1 of 3 repetitions. |
| 482 | `          and "  pair summary: 2 pairs \| gain of medians: median  -4.15 %, lowest -11.88 %, highest   3.58 %" in text and "pair  3 (" not in text)` | Continues line 480: the pair summary counts 2 pairs with a median gain of -4.15 %, and the output has no line of pair 3. So a process that was cut cannot enter a gain. |
| 483 | `    check("synthetic: classes per repetition of the new read (CPU 2, session 1)",` | Check: the classes per repetition of the new read on CPU 2 in session 1. The condition is in lines 484 to 485. |
| 484 | `          "  new repetition 0: low 1, between 1, high 0" in text and "  new repetition 1: low 1, between 0, high 1" in text` | Continues line 483: repetition 0 has 1 low and 1 between. Repetition 1 has 1 low and 1 high. |
| 485 | `          and "  new repetition 2: low 0, between 0, high 2" in text and "  new all repetitions (6): low 2, between 1, high 3" in text)` | Continues line 483: repetition 2 has 2 high. All 6 repetitions together have 2 low, 1 between and 3 high. The killed process is not counted. |
| 486 | `    check("synthetic: a process that changes class is listed", "  new idx 1 changes class inside the process: low low high (67.50  69.50  71.00)" in text` | Check: a process that changes its class is listed. The condition goes on in line 487. |
| 487 | `          and "  new idx 2 changes class inside the process: between high high" in text)` | Continues line 486: the process 1 with `low low high`, and the process 2 with `between high high`. |
| 488 | `    check("synthetic: summary lines of both sessions",` | Check: the summary lines of both sessions. The condition is in lines 489 to 491. |
| 489 | `          "  session 1 CPU   2:  2 pairs \| gain of medians: median  -4.15 % \| new repetitions: low 2, between 1, high 3" in text` | Continues line 488: session 1, CPU 2: 2 pairs, a median gain of -4.15 %, and 2 low, 1 between and 3 high repetitions of the new read. |
| 490 | `          and "  session 1 CPU  41:  1 pairs \| gain of medians: median   0.00 % \| new repetitions: low 0, between 0, high 3" in text` | Continues line 488: session 1, CPU 41: 1 pair, a gain of 0.00 % and 3 high repetitions. The gain uses the medians, so the one old repetition of 35.80 GB/s does not change it. |
| 491 | `          and "  session 2 CPU  41:  1 pairs \| gain of medians: median   0.00 % \| new repetitions: low 3, between 0, high 0" in text,` | Continues line 488: session 2, CPU 41: 1 pair, a gain of 0.00 % and 3 low repetitions. |
| 492 | `          [l for l in text.splitlines() if l.startswith("  session")])` | Continues line 488: the summary lines are shown when the check fails. |
| 493 | `    rc, text2, err = analyze("--results", res, "--low-max", "70.0", "--high-min", "71.5")` | Runs the analysis again with the limits `--low-max 70.0` and `--high-min 71.5`. |
| 494 | `    check("synthetic: the levels of the command line change the classes",` | Check: the limits of the command line change the classes. The condition is in line 495. |
| 495 | `          rc == 0 and "  new all repetitions (6): low 3, between 2, high 1" in text2, [l for l in text2.splitlines() if "new all" in l])` | Continues line 494: status 0, and the 6 repetitions are now 3 low, 2 between and 1 high. |
| 496 | `    rc, _, err = analyze("--results", res, "--low-max", "71", "--high-min", "70")` | Runs the analysis with a low limit above the high limit. |
| 497 | `    check("levels in the wrong order: status 2", rc == 2)` | Check: status 2. |
| 498 | `    rc, text3, err = analyze(os.path.join(d2, "H2.csv"))` | Runs the analysis with the file of session 2 as its only argument. |
| 499 | `    check("a file named on the command line is the only one read", rc == 0 and "H2 runs: 1 file(s)" in text3 and "session 1, CPU" not in text3)` | Check: a file that is named on the command line is the only one read: the output counts 1 file and has no heading of session 1. |

### `analyzer_tests`: a continued session, reported defects, and the start as a program (lines 500 to 526)

| Line | Source | Explanation |
|---:|---|---|
| 500 | `    # a continued session: idx 5 complete in a second folder replaces the killed one` | Comment: a continued session. The process with the number 5 is complete in a second folder and replaces the killed one. |
| 501 | `    d3 = os.path.join(res, "h2-s1-20261115T000500Z")` | `d3`: a second result folder of session 1, with a later time in its name. |
| 502 | `    os.makedirs(d3)` | Makes it. |
| 503 | `    with open(os.path.join(d3, "H2.csv"), "w") as f:` | Opens `H2.csv` in it for writing. |
| 504 | `        f.write("\n".join([synth_header("bw_new", "2", 1, 5, 3, 2)] + synth_rows([67.67, 67.67, 67.67])) + "\n")` | Writes one process: the new process of pair 3 with the number 5, and three times 67.67 GB/s. |
| 505 | `    rc, text4, err = analyze("--results", res)` | Runs the analysis on the folder `res`. |
| 506 | `    check("a continued session (second folder, --from): the complete process replaces the killed one",` | Check: the complete process replaces the killed one. The condition is in lines 507 to 508. |
| 507 | `          rc == 0 and "  pair  3 (old first): old median  67.00 max  67.00 \| new median  67.67 max  67.67 \| gain of medians   1.00 %" in text4` | Continues line 506: status 0, and pair 3 now has a line, with a gain of the medians of 1.00 % (67.67 against 67.00 GB/s). |
| 508 | `          and "NOT COMPLETE" not in text4, (rc, err))` | Continues line 506: and the text `NOT COMPLETE` is gone. So a session that was stopped and then continued with `--from` is analysed as one session. |
| 509 | `    # defects that must be reported` | Comment: the last group is defects that must be reported. |
| 510 | `    bad = os.path.join(top, "bad.csv")` | `bad`: the path of a csv file for these cases. |
| 511 | `    with open(bad, "w") as f:` | Opens it for writing. |
| 512 | `        f.write("\n".join(synth_rows([67.0, 67.0, 67.0])) + "\n")` | Writes rows without a header line before them. |
| 513 | `    rc, _, err = analyze(bad)` | Runs the analysis on this file. |
| 514 | `    check("rows without a header line: status 2", rc == 2 and "does not belong" in err, (rc, err))` | Check: status 2, and the error text says that a row does not belong to a header line. |
| 515 | `    with open(bad, "w") as f:` | Opens the file again. |
| 516 | `        f.write("-- binary bw_old kernel read threads 1 cpus 2 bytes 8M round 1 load 0.10 utc 18:12:59\n" + "\n".join(synth_rows([67.0, 67.0, 67.0])) + "\n")` | Writes a header line in the form of `run_kernels.sh`, without the fields `session`, `idx` and `pair`, and three rows. |
| 517 | `    rc, _, err = analyze(bad)` | Runs the analysis. |
| 518 | `    check("a file with headers of run_kernels.sh given as H2.csv: status 2", rc == 2 and "not a file of run_h2.sh" in err, (rc, err))` | Check: status 2, and the error text says that the file is not a file of `run_h2.sh`. So a file of the original run cannot be taken for an H2 file. |
| 519 | `    rc, _, err = analyze(os.path.join(top, "missing.csv"))` | Runs the analysis on a file that does not exist. |
| 520 | `    check("a file that does not exist: status 2", rc == 2)` | Check: status 2. |
| 521 | `    r = subprocess.run([sys.executable, os.path.join(A, "h2_analyze.py"), "--results", res], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)` | Starts `h2_analyze.py` as a program with the same Python, on the folder `res`, and collects its output. |
| 522 | `    check("h2_analyze.py as a program: status 0 and the same text as the function", r.returncode == 0 and r.stdout == text4, r.stderr)` | Check: exit status 0, and the output equals the text that the call of line 505 gave. So the script behaves the same as a program and as a function. |
| 525 | `if __name__ == "__main__":` | True only when the file is started as a program. |
| 526 | `    sys.exit(main())` | Runs `main` and ends the script with its return value as the exit status. |

## References

- [Ref1] The run script: the file `code/bwx8-2026-11-14/run_h2.sh` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its head comment gives hypothesis H2, the order of the processes, the settings and the exit statuses. The functions `why_stop`, `stop_child`, `settle` and `one` hold the stop controls. The line that sets `MARGIN` gives the 92 s.
- [Ref2] The decisions note: the file `code/bwx8-2026-11-14/DECISIONS-bwx8.md` of the same repo, section "Round 2, added 05:25 UTC": the sentence that `test_h2.py` passed 84 of 84 checks, and the rule of step `H2`.
- [Ref3] The handoff note of 2026-11-13: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the same repo, section "Files": the expected sha256 values of `bw_old` and `bw_new`.
- [Ref4] The file `tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/one-thread.csv` of the same repo: the rows of the kernel `read` at 8 MiB for `bw_old` and `bw_new` on the CPUs 0 and 2, rounds 1 and 2. Its sha256 was equal to that of the file that `h2_analyze.py` reads when this page was written on 2026-11-25.
- [Ref5] The analysis script: the file `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis/h2_analyze.py` on the agent server. It is not in the code repo. Its constant `ORIGINAL` names the file `one-thread.csv` of the original run, and its functions `gain`, `classify`, `parse`, `report_group` and `main` produce the texts that the checks compare.
