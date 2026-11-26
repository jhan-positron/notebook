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

1. The file sets the paths of the scripts under test and imports `h2_analyze.py` ({L31-38}).
2. The helpers follow: the text of the dummy binary, the function `check`, the class `Box` for one set-up, the helpers that run `run_h2.sh`, and the rule function `order_problems` ({L40-217}).
3. `main` makes a temporary folder, calls `tests`, deletes the folder and sets the exit status ({L220-230}).
4. `tests` first checks the texts of the scripts: the syntax, no call of `sudo` or `ssh`, the pinning to the CPUs 0 to 119, and the two sha256 values ({L234-251}).
5. Dry run: 72 command lines per session, the original options, a balanced order, and session 2 as the reverse of session 1 ({L253-279}).
6. Wrong use and checksums: a missing setting, a wrong sha256 and a missing binary each give exit status 2, and nothing starts ({L281-301}).
7. Stop controls before the first process, and the rules for session 2 ({L303-336}).
8. Stops while a process runs: the marker file, three signals, the stop file, `STOP_AT`, and a benchmark that fails ({L338-370}).
9. A full run of session 1 with 72 dummy processes: the files of the result folder, the order, the header lines, and the analysis of that output ({L372-423}).
10. `analyzer_tests` checks `h2_analyze.py` alone: its two small functions, the numbers of the original run, invented files, and the errors that it must report ({L428-522}).

## Behavior a reader must know

- No check contacts CRB. The marker file, the stop file, the binaries and the results folder are replaced by paths inside the temporary folder ({L101-103}). So a passed check says something about the scripts and nothing about CRB.
- The rates of the dummies are fixed numbers ({L57}). Nothing is timed.
- A failed check does not end the run: `check` notes it and the next check runs ({L67-71}). A Python error does end the run, for example the time limit of {L109}.
- A complete run makes 84 checks, counted from the calls of `check` and their loops in this text. The decisions note records, in an entry of 2026-11-15 at 05:25 UTC, that this file passed 84 of 84 checks [Ref2].
- By the docstring the full run takes about 75 s on an idle machine and up to 26 min on a busy one ({L14-18}).
- The code repo does not hold `h2_analyze.py`. The path of {L34} names a folder that the repo does not have. The file lies in the project folder on the agent server [Ref5]. So this test does not start from the repo layout.
- The checks of {L436-444} read a measured file: `one-thread.csv` of the original run, at the fixed path that `h2_analyze.py` holds. The expected numbers of these checks are the numbers of that file [Ref4].
- The check of {L250-251} has the words "after the marker check" in its name. It tests only that both texts are in `visit_h2.sh`, not their order.
- The check of {L247-248} reads `run_kernels.sh`. That script was changed on 2026-11-24, after all tests. Its text in the code repo still holds the option line and the size loop that the check looks for.
- The case of {L361} depends on timing. `STOP_AT` lies 60 s after the start of the case, and the script ends 1 to 2 s after `STOP_AT`. The helper waits 60 s for that end, counted from about 0.5 s after the dummy started to sleep ({L142-145}). So the check can fail when the dummy starts to sleep less than about 1.5 s after the start of the case, for example on an idle machine, where `run_h2.sh` does not wait before a process. This is reasoning from the code of this file and of `run_h2.sh` [Ref1]. It was not tested for this page.
- The test deletes its temporary folder at the end unless the environment variable `KEEP` is set ({L224-228}).

## References

- [Ref1] The run script: the file `code/bwx8-2026-11-14/run_h2.sh` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its head comment gives hypothesis H2, the order of the processes, the settings and the exit statuses. The functions `why_stop`, `stop_child`, `settle` and `one` hold the stop controls. The line that sets `MARGIN` gives the 92 s.
- [Ref2] The decisions note: the file `code/bwx8-2026-11-14/DECISIONS-bwx8.md` of the same repo, section "Round 2, added 05:25 UTC": the sentence that `test_h2.py` passed 84 of 84 checks, and the rule of step `H2`.
- [Ref3] The handoff note of 2026-11-13: the file `tests/2026-11-13-new-read-kernel/report/handoff.md` of the same repo, section "Files": the expected sha256 values of `bw_old` and `bw_new`.
- [Ref4] The file `tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/one-thread.csv` of the same repo: the rows of the kernel `read` at 8 MiB for `bw_old` and `bw_new` on the CPUs 0 and 2, rounds 1 and 2. Its sha256 was equal to that of the file that `h2_analyze.py` reads when this page was written on 2026-11-25.
- [Ref5] The analysis script: the file `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis/h2_analyze.py` on the agent server. It is not in the code repo. Its constant `ORIGINAL` names the file `one-thread.csv` of the original run, and its functions `gain`, `classify`, `parse`, `report_group` and `main` produce the texts that the checks compare.
