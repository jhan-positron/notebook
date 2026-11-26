# `stderr.txt` explained: part L, session 1

## Short version

This file is the error output of `bwx12` of part L, session 1 of the whole-chip rerun at 7200 MT/s of 2026-11-17.
The file is empty (0 bytes).

## This file

- File: `stderr.txt` in this folder (`crb/results/w120-T72L1-20261117T221329Z`).
- Size: 0 lines, 0 bytes. sha256 when this page was built: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Written by: `rx.sh` (the runner script) sent the error output of `bwx12` to this file.
- Step of the run: part L, session 1, folder tag `T72L1`.

## The whole file

The file has no line.

The sections below explain the file type. The same text stands in the companion of every file of this type.

## The file type in short

`stderr.txt` collects what a launched benchmark process writes to its standard error: the error messages and warnings of taskset and bwx12. All nine files of the rerun are empty (0 bytes). An empty file means that the shell started the launch command and that the command wrote no error message and no warning.

Scope of this text:

- This text covers the file `stderr.txt` in each of the nine folders `R/w120-T72*` of the rerun of 2026-11-17 (parts L and C, control I).
- `R` is `/home/jhan/workspace/titan/cache-perf/crb/results`. The other folder letters are in "Words used here".

## What this file is

- **Writer.** The launched command writes the file. rx.sh (the runner script for the bwx12 benchmark processes) starts `taskset -c 0-119 <binary> <arguments>` and appends the standard error of this command to `stderr.txt` [Ref1].
- **Step of the run.** The shell opens the file when it starts the command. This is directly after rx.sh wrote the `launch` line of `launches.txt` [Ref1].
- **How often.** One file per result folder. rx.sh opens it in append mode. With several lines in the spec file, all processes of one call of rx.sh write into the same file. In the nine folders one call launched one process.
- **One line per what.** The content is free text: the messages of the command, in the order in which they were written. The file does not say which process wrote a message.
- **What is not in the file.** The messages of rx.sh itself (`RUNNING file present: stop`, `sha mismatch`, `marker: stop`, `marker: killed`, `done <folder>`) go to the standard output of rx.sh [Ref2]. rx.sh inherits its standard output and its error output from go.sh or go2.sh [Ref8]. In this run both outputs went into the run log [Ref12]. The result rows of bwx12 go to `<tag>.csv` [Ref1].

No sample line exists: the nine files hold no line.

## Line kinds

The nine files have 0 lines. So no line kind occurs in the data.

The table below lists eight kinds of message that the launched command can write. It is not a full list of the messages of bwx12. It comes from the source of bwx12 and from a local test of taskset. bwx12.c holds 31 lines with `fprintf(stderr` (one of them is a `vfprintf`) and 9 lines with `perror(` [Ref3].

| Kind of message | Example | Does the process go on? |
|---|---|---|
| A wrong argument | `bad --seq entry: <name>` | No. bwx12 ends with exit status 2 [Ref3]. |
| A thread cannot be pinned to its CPU | `sched_setaffinity: <error text>` | No. bwx12 ends with exit status 2 [Ref3]. |
| The buffer of a thread cannot be mapped | `mmap: <error text>` | No. bwx12 ends with exit status 2 [Ref3]. |
| A counter event that cannot be opened | `perf_event_open <event> (type <n> code 0x<code>): <error text> (printed as NA)` | Yes. Only the thread with index 0 prints this message. The csv file then holds `NA` for the event [Ref4]. |
| A failed `mprotect` or `madvise` call for the buffer of a thread | `mprotect of the guard ranges (continuing; page state will be NA): <error text>` or `madvise (continuing): <error text>` | Yes [Ref5]. |
| More threads than CPUs | `warning: <T> threads on <C> cpus: cpus are oversubscribed` | Yes [Ref3]. |
| taskset cannot start the binary | `taskset: failed to execute <path>: <error text>` | No. The exit status is 127 when the file does not exist. It is 126 when the file exists and cannot be executed (local test [Ref6]). |
| taskset cannot set the CPU list | `taskset: failed to set pid <n>'s affinity: <error text>` | No. The binary does not start. The exit status is 1 (local test [Ref6]). |

Four messages of bwx12.c let the process go on: the `perf_event_open` message, the two messages after a failed `mprotect` or `madvise` call, and the warning for more threads than CPUs. After every other message bwx12 ends with exit status 2 [Ref3].

The file can also hold a message of bash. When bash does not find the command that it must start, it writes `<name>: command not found` to the standard error of that command. The exit status is then 127 (local test with another command name [Ref6]). Here the command is `taskset`.

## Columns

This section does not apply: a message is free text without fields.

## What an empty file means

- **The launch happened.** The shell creates the file when it starts the command, also when the command writes nothing (local test [Ref6]). A folder without `stderr.txt` would mean that rx.sh launched no process.
- **No message was written.** Neither bash, nor taskset, nor bwx12 wrote to the standard error of the command.
- **Counters.** Every `launch` line of the nine folders holds `--count` and six events in `--events`. With `--count` each thread opens the events for itself. The thread with index 0 prints a message for each event that does not open [Ref4]. So in each of the nine processes the thread with index 0 opened all six events. The file cannot show a failure of another thread. The csv file shows such a failure as `NA`. The csv files of the nine folders hold no `NA` (`grep -c NA` gives 0 for each file).
- **Buffers.** Each thread calls `mprotect` and `madvise` when it allocates its buffer. A failed call prints a message and the thread goes on [Ref5]. So no such call failed in the nine processes.
- **Limit.** An empty file does not show that the process ended with the exit status 0. bwx12.c holds no call of `signal` or `sigaction`. The file bwx12_selftest.c, which bwx12.c includes, calls `sigaction` in two of its test functions. These functions run only with the option `--selftest` [Ref3]. The nine `launch` lines hold no `--selftest`. So bwx12 prints nothing when a signal ends it. The exit status is in the `rc` line of `launches.txt`. Read both: the `rc` line must hold the status 0, and `stderr.txt` must have 0 bytes.

### Size of the nine files

The rows are in the order of time. A script made the table with the file sizes.

| Folder (under `R`) | Size of `stderr.txt` | Lines |
|---|---|---|
| `w120-T72L1-20261117T221329Z` | 0 bytes | 0 |
| `w120-T72C1-20261117T221436Z` | 0 bytes | 0 |
| `w120-T72L2-20261117T221638Z` | 0 bytes | 0 |
| `w120-T72C2-20261117T221745Z` | 0 bytes | 0 |
| `w120-T72L3-20261117T221947Z` | 0 bytes | 0 |
| `w120-T72C3-20261117T222054Z` | 0 bytes | 0 |
| `w120-T72C4-20261117T222136Z` | 0 bytes | 0 |
| `w120-T72I1-20261117T222700Z` | 0 bytes | 0 |
| `w120-T72I2-20261117T223227Z` | 0 bytes | 0 |

- All nine files have 0 bytes.
- The `rc` line of `launches.txt` holds the exit status 0 in all nine folders.

## Old read kernel and new read kernel in this file

This section does not apply: the nine files are empty.

- A message would belong to the whole process.
- One process ran every kernel of its sequence, one after the other. The sequence holds the old read kernel and one or two load-only loops. In part L and control I it also holds three test loops (`read_nop96`, `read_nop256`, `read_1pl`).
- The file has no field for the kernel and no field for the time of a message.

## Which code reads this file

No rate comes from this file.

| Reader | What it takes from `stderr.txt` | What it does with it |
|---|---|---|
| rx.sh, its last line [Ref2] | The size in bytes (`wc -c`). The first 600 bytes (`head -c 600`). | It prints both to its standard output. In the two run logs the line `0` stands after each of the 9 `done` lines of an rx.sh folder, directly after the line `2` [Ref7]. This `0` is the size of `stderr.txt`. |
| go.sh and go2.sh [Ref8] | Nothing. They do not read the file. | They name the file in the message `FAILED: bwx12 <name>: exit status not 0 (launches.txt, stderr.txt)`. The message tells the reader where to look. Neither log holds this message [Ref7]. |
| build_facts.py [Ref9] | The size in bytes. It does not open the file. | Check 10 passes when the size is 0 bytes in each of the nine folders. |
| facts_text.py [Ref10] | Nothing from the content. | It lists the path in the file list of FACTS.md with the words "error output of bwx12". |

- Check 10 passed in the facts sheet FACTS.md [Ref11].
- make_report.py (the script that builds the HTML report), stat_bwx.py and stat_k120.py (the two scripts for quick statistics) do not read this file.
- The exit status of rx.sh is the status of its last command. This command is the `head` that prints the first 600 bytes of `stderr.txt` [Ref2]. So rx.sh ends with status 0 when the file can be read, also when bwx12 failed. For this reason go.sh tests the `rc` line of `launches.txt` [Ref8].

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process**: one start of a benchmark binary.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **rx.sh**: the runner script of parts L and C and of control I. It reads a spec file, launches one bwx12 process per line and writes `env.txt`, `launches.txt`, `stderr.txt` and one csv file per process.
- **go.sh, go2.sh**: the two driver scripts of the rerun. go.sh runs the three sessions of parts A, L and C. go2.sh runs control I. Both call rx.sh.
- **Run log**: the file that holds the standard output and the error output of go.sh or of go2.sh [Ref12]. The two run logs are `go-T72-20261117T221209Z.log` and `go2-T72-20261117T222335Z.log` in the folder `R` [Ref7].
- **Result folder**: the folder that one call of rx.sh creates. Its name is `w120-<name>-<UTC time>`.
- **Spec file**: the input of rx.sh. Each line holds a tag, the character `|` and the arguments of one bwx12 process.
- **Tag**: the name of one process inside a result folder: `a6456`, `cfwd` or `crev` in the nine folders. The csv file of the process is `<tag>.csv`.
- **Csv file**: the file `<tag>.csv` of a result folder. It holds the result rows that bwx12 prints.
- **build_facts.py, facts_text.py**: two of the scripts that read the raw files of the rerun and write the facts sheet. The facts sheet is `facts.json` (data) and `FACTS.md` (text) in the folder `S`.
- **Standard output, standard error**: the two output streams of a process. bwx12 prints its result rows to the standard output and its messages to the standard error.
- **Exit status**: the number that a process returns to the shell when it ends. 0 means success.
- **taskset**: the Linux tool that starts a command on a given list of CPUs. Here the list is CPUs 0 to 119.
- **Counter event**: a hardware event that the processor counts for a thread, for example bus accesses. bwx12 opens the events with the Linux system call perf_event_open.
- **mprotect, madvise**: two Linux system calls. bwx12 uses mprotect to block the memory before and after a buffer. It uses madvise to ask for huge pages for the buffer, or to refuse them.
- **NA**: "not available". bwx12 prints it in place of a value that it could not read.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. rx.sh stops when this file exists.
- **Folder letters**: `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`. `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`. `W15` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15`. `BWX12` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15`. On CRB the folder `R` was `~/cache-perf/results`.

</details>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`, line 16 (the `launch` line) and line 17: `taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &`.
- [Ref2] The same file, lines 7, 8, 13 and 19 (the messages of rx.sh, written with `echo` to its standard output) and line 22 (the last line: `done <folder>`, the number of lines of `launches.txt`, the `rc` lines with a status other than 0, `wc -c < $out/stderr.txt`, `head -c 600 $out/stderr.txt`).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 1759 to 1762 (`bad --seq entry`, then `exit(2)`), lines 415 to 424 (function `pin_cpu`: `perror("sched_setaffinity")`, then `exit(2)`), lines 438 to 441 (`perror("mmap")`, then `exit(2)`), lines 2999 and 3000 (the warning for more threads than CPUs). The counts 31 and 9 come from `grep -c` on this file. A `grep` for `sigaction` and `signal(` finds no line in this file. Each of the other 36 lines with a message is followed by `exit(2)`, by `return 2` in `main` or in `trial_main` (whose value `main` returns), or by a call of `usage` or `trial_usage` (both end with `exit(2)`). Line 2900 of bwx12.c includes `bwx12_selftest.c` of the same folder. In that file, lines 245 and 498 call `sigaction` for the signal SIGSEGV in the functions `test_touch` and `hot_touch_run`. Only the function `selftest` reaches these two functions (lines 698 and 703 of that file), and `main` calls `selftest` only for the option `--selftest` (line 2920 of bwx12.c).
- [Ref4] The same file, lines 1580 to 1601 (function `open_counters`: an event that does not open is printed as NA, and the message is printed only when the index of the thread is 0) and lines 1643 and 1644 (each thread calls `open_counters` when `--count` is set).
- [Ref5] The same file, lines 434 to 451 (function `alloc_buf`: `perror` after a failed `mprotect` or `madvise`, with no exit) and line 1645 (each thread calls `alloc_buf`).
- [Ref6] Local test on the server of this task (GNU bash 5.1.16, taskset of util-linux 2.37.2), in the scratch folder of this task: the command `true 2>> e.txt` created a file of 0 bytes. The command `taskset -c 0 ./no-such-binary 2>> e.txt` wrote the line `taskset: failed to execute ./no-such-binary: No such file or directory` into the file and ended with status 127. The command `taskset -c 0 ./notexec` (a file without execute permission) wrote `taskset: failed to execute ./notexec: Permission denied` and ended with status 126. The command `taskset -c 99999 true` (a CPU that does not exist) wrote `taskset: failed to set pid <n>'s affinity: Invalid argument` and ended with status 1. A command name that does not exist, started in the background with `2>> e.txt`, wrote the line `/bin/bash: line <n>: <name>: command not found` into the file, and `wait` gave status 127. The command `true > /no-such-folder/x.csv 2>> e.txt` ended with status 1 and did not create `e.txt`. The versions of bash and taskset on CRB were not checked (no ssh in this task).
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log` (7 `done` lines of rx.sh folders, each followed by the lines `2` and `0`, no line that starts with `FAILED`). `/home/jhan/workspace/titan/cache-perf/crb/results/go2-T72-20261117T222335Z.log` (2 such `done` lines, the same pattern).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`, lines 28 to 32 (the comment, the function `rxok` and the failure message in the function `runx`). `go2.sh` in the same folder, lines 23 and 31. The call of rx.sh (line 31 of go.sh, line 30 of go2.sh) redirects the standard input only.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`, lines 82 to 86 (the size with `os.path.getsize`) and lines 716 and 717 (the check of 0 bytes).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`, line 202.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`, line 222: "10. pass: stderr.txt, bytes per folder (expected 0)" with the value 0 for each of the nine folders.
- [Ref12] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the record of the Claude Code session of 2026-11-17. This file lies outside the project folder. No script of the folder `S` holds the command that started the run. Line 313 of the record holds the command for go.sh, and line 365 holds the command for go2.sh. Each command was sent with ssh (the remote login tool) as user jhan. Its start part is `nohup setsid <script> > <log file> 2>&1 < /dev/null &`. The part `> <log file> 2>&1` sends the standard output and the error output of the script to the log file.
