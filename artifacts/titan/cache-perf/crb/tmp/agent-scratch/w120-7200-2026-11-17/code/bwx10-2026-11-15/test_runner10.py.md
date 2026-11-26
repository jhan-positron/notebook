# `test_runner10.py` explained, line by line

- Source file: `bwx10-2026-11-15/test_runner10.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1804 lines, 113828 bytes).
- sha256 of the source when this page was built: `d34eff54c9f46150481c2f9179b6650351163d7148be924ea0508d37828a1d22`.

## Short version: purpose

`test_runner10.py` holds the local tests of the runner `bwx10` and of its listing check `check_listing10.py`. The tests build the runner on the development machine and check its plan parser, its output rows, its timed sequence, its options and its build script. They prove that the harness counts bytes and times in the right way, and they measure no rate, as the kernels of a local build are stand-in loops.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Development machine**: the x86-64 machine on which these tests run. It is not CRB.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Design**: the plan of the investigation into the buffer size of 8 MiB, the file `tackle-8mb.md`. It says how the runner must measure.
- **Round 3**: the third set of experiments of that investigation. It added the runner `bwx10` with the prefetch kernels, `read_1pl`, `--rec-pad` and `--hot-copy`.
- **Accepted runner**: in this file the runner `bwx8` of rounds 1 and 2. The runner `bwx10` is compared with it.
- **First runner**: the runner `bwx`. Its folder `bwx-2026-11-13` holds `bwx.c`, `bwx_selftest.c` and `build.sh`.
- **`ref-bwx8`**: a folder beside the test file. It holds saved files of the accepted build of `bwx8`. The tests read two of them: the machine-code listing and the offsets table.
- **Marked block**: a part of a source file between a comment line `bwx10+` and a comment line `bwx10-`. Every addition of round 3 stands in such a block.
- **Stand-in kernel**: on a machine that is not AArch64 the runner builds each Arm kernel as a plain C loop that touches the same bytes. A rate of such a build means nothing.
- **AArch64, x86-64**: the 64-bit instruction sets of Arm processors and of the processors of the development machine.
- **Harness**: the code of the runner around the kernels. It reads the plan, pins the threads, allocates the buffer, reads the clock and prints the rows.
- **Trial mode**: the mode `--trial` of the runner. One pinned worker thread runs the trials of a plan file.
- **Interval mode**: the mode `--seq` of the runner, the mode of the first runner `bwx`. It times a sequence of kernels in intervals and prints `I`, `T` and `P` rows.
- **Worker, controlling thread**: the worker thread runs the kernels. The controlling thread starts the worker and waits for it. Each one is pinned to its own CPU.
- **Plan file**: a text file with three header lines and one line per trial. A trial line has 11 fields: trial number, condition label, repeat number, previous activity, prefix, predecessor, target, number of target windows, window duration in ms, count mode and bins switch.
- **Trial**: one line of a plan. The runner runs its windows one after the other with nothing but clock reads between them.
- **Window**: one timed period in which one kernel reads one range again and again.
- **Pass**: one complete read of the range of a window.
- **Previous activity, prefix, predecessor, target**: the four phases of a trial, in this order. The previous activity has 1 window. The prefix is the same preparation before each target and has 4 windows. The predecessor is the kernel that runs directly before the target, in 1 window. The target is the kernel whose rate is measured.
- **Timed sequence**: all windows of one trial, from the first clock read to the last. It may hold kernel calls and clock reads only, and with the count mode `read` the counter reads at the boundaries of the target windows.
- **Timed functions**: `timed_sequence` and `timed_sequence_hot`, the two C functions that run a timed sequence. The second one runs with `--hot-copy`.
- **Gap**: the time between the end clock read of a window and the start clock read of the next one. `gap_ns` is the gap before target window 0.
- **Bin**: a part of a target window with a requested width of 10 ms. It closes on a clock read that the window loop makes anyway.
- **Count mode**: `closed` (no counter group is open), `open` (the group is open and is not read) or `read` (the group is open and is read at the boundaries of the target windows). The count state of the `E` row can also be `fail`.
- **`M` row**: `M,key,value`, one setting of the run.
- **`K` row**: one kernel of the plan with the address of its function in hex and that address modulo 64.
- **`S` row**: the start of a trial: the 11 plan fields, then the label and the target of the trial before.
- **`P` row**: the page state of the buffer before (`pre`) or after (`post`) the timed sequence: size in kB, part on huge pages in kB and four page counters of the whole system.
- **`W` row**: one window: trial, phase, window number, kernel, bytes of one pass, bytes read, start time and end time in ns.
- **`B` row**: one bin: trial, window number, bin number, end time and bytes from the window start.
- **`C` row**: the counter values of one target window: enabled time, running time, thread CPU time and one count per event.
- **`E` row**: the end of a trial: wall time, CPU time, voluntary and involuntary context switches, `gap_ns`, the largest gap, `sink_ok` and the count state.
- **`X` row**: a reported failure, with a trial number or `-1`, a code and a text.
- **`TR` row**: one event of the trace: trial, event number, event name and time in ns.
- **Trace**: with `--trace` the runner logs each clock read, the first kernel call of each window, each counter read, page read and output, and prints them as `TR` rows. The rates of such a run are not used.
- **Sink, `sink_ok`**: the old read kernel returns the sum of the words that it read. The runner stores the sum in a variable, the sink. `sink_ok` is `1` when the last sum is the expected one.
- **Window record**: the 80 bytes in which the runner keeps the settings and the results of one window.
- **Record block**: the one block of memory that holds the trial records, the window records, the counter readings, the bins and the trace.
- **`--rec-pad`**: an option of the trial mode. It puts unused bytes before the window records, so they lie at another address.
- **`--hot-copy`**: an option of the trial mode. The window loop then works on local copies and does not touch the window record between the first and the last pass of a window.
- **Prefetch kernels**: `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`: the `asmread` loop with one software prefetch per 64-byte line.
- **`read_1pl`**: a kernel of round 3 that loads 16 bytes of every 64-byte line.
- **Rule**: a function of this file that returns a list of problems. An empty list means that the rows are right.
- **Defect**: an entry of the table `MUTANTS`: a copy of the runner source with one change that a check must find.
- **Loop offset**: the address of the first instruction of a loop modulo 64.
- **Pad**: zero bytes that the source puts before a function. They make the function start at a planned address modulo 64.
- **Placement**: the start addresses modulo 64 of the functions from `call` to the timed functions. `call` is the function that starts a kernel.
- **Listing check**: the script `check_listing10.py`. Part 1 compares the machine-code listing of a build with the accepted listing. Part 2 checks the loops of the new kernels.
- **Offsets table**: the file `offsets.tsv` of a build: one row per kernel with the start address, the loop start and the loop start modulo 64.
- **Build record**: the file `build.txt` that the build script writes: compiler, flags, compiler messages, self-test result, branch targets, placement and checksums.
- **Logging library**: the C text `SHIM`. A test loads it into the runner with `LD_PRELOAD`. It logs the calls `sched_setaffinity` and `mmap`, and it can let `madvise` fail.
- **PMU type**: the number by which Linux names a group of counters. In these tests type 1 means the software events of Linux.
- **Context switch**: Linux takes a thread off its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: happens when a thread uses a page that Linux has not yet assigned to it.
- **Address randomization**: Linux gives the stack and the mapped memory of each new process other addresses. `setarch -R` switches this off for one program.
- **Stack guard**: a value that the compiler puts on the stack of a function and tests before the function returns. `__stack_chk_fail` is called when it was overwritten.
- **FNV-1a**: a simple hash function. The runner prints the 64-bit FNV-1a hash of the bytes of its plan file.

## Main flow

1. The file starts with its description, the imports and the constants: the folders of the sources and of the reference build, the names of the added kernels and `M` rows, and the compiler flags (lines 1 to 57).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed functions, and the order of pin and memory mapping (lines 101 to 351).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner (lines 354 to 510).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row (lines 513 to 599).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows (lines 608 to 699).
6. `test_sequence_code`: the source text and the machine code of the timed functions hold only the allowed calls, and both rules fail on a build with a defect (lines 702 to 730).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches (lines 733 to 747).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported (lines 750 to 782).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces (lines 791 to 874).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window (lines 877 to 926).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints (lines 929 to 967).
12. `test_source`: `bwx10.c` is the accepted source plus marked additions, the older kernels keep their start, size and order, and the code after the kernels keeps its placement (lines 976 to 1072).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect (lines 1075 to 1129).
14. `test_listing_saved`: the listing check accepts a good listing and rejects each kind of changed kernel and each wrong new kernel (lines 1192 to 1336).
15. `test_build_scripts`: `build10.sh` stops on the marker file, writes its files, rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must (lines 1339 to 1478).
16. `test_new_kernels`: the five kernels of round 3 work in the plan parser, in the trial mode and in the interval mode (lines 1531 to 1565).
17. `test_rec_pad`: `--rec-pad` moves the window records by exactly its value and moves nothing else (lines 1568 to 1661).
18. `test_hot_copy`: `--hot-copy` prints the rows of a plain run, keeps every rule, and selects the second timed function (lines 1688 to 1761).
19. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds three binaries, runs the 16 tests, deletes the temporary folder and prints the number of failed checks (lines 1764 to 1800).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them (lines 1768 to 1770), or when one of the three first builds fails (lines 1778 to 1787).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` (line 592, line 901, line 1456, line 1632).
- A test that raises a Python error ends the script. The temporary folder is still deleted (lines 1792 to 1796), but the summary lines of lines 1797 to 1799 are not printed.
- `main` does not run the tests in file order (lines 1788 to 1790). `test_source` and the two self-test tests run first.
  - `test_trace` sets `E.soft_counters`, which `test_counters` reads (line 803, line 900).
  - `test_source` sets `E.call8`, which `test_build_scripts` needs (line 1052, line 1455).
- The tests write only into a new temporary folder (line 1774). It is deleted at the end unless the variable `KEEP` is set.
- The tests read three folders beside the folder of the test file or in it: the folder of the first runner (line 43), the folder of the runner `bwx8` (line 44) and `ref-bwx8` (line 45). The README of the repo says that the `ref-` folders were left out of the repo copy. So `test_source` (line 1066) and `test_listing_saved` (lines 1194 to 1196) cannot read their reference files from the repo copy in its present layout. The repo keeps the same two files, `listing.txt` and `offsets.tsv`, in the folder `build-records/bwx8-crb-build-1` of the test `2026-11-15-tackle-8mb`.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text is no longer found in the source makes its checks fail (lines 259 to 260, lines 447 to 448).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the listing check `check_listing10.py` under Python (line 1133), the two build scripts `build10.sh` and `build.sh` under `bash`, and `setarch`. A run that the helper `run` starts may last 120 s at most (line 489).
- One test loads the machine on purpose: `test_disturbed` runs an endless loop on the worker CPU during one trial (line 736).
- The check that the other addresses do not move with `--rec-pad` (lines 1640 to 1644) depends on the environment of the caller. A comment in the later test file `test_runner11.py` says so. By that comment `tw_addr` lies on the stack of the main thread, below the text of the arguments and of the environment. The pad values `0`, `80` and `4000` differ in length, and that can move `tw_addr`.
- At four places the text and the code do not match.
  - The comment of line 1094 names a build that counts one pass too many per clock read. The two defects that the code builds are others (lines 1100 to 1101).
  - The test `src is None` of line 259 has no effect, as line 258 already used `src`.
  - The name of the check of line 817 says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them (line 818). The check of lines 811 to 812 tests where they lie.
  - The description text of `seq_source_problems` names three C functions (line 283). The rule reads the five functions of the table `SEQ_SOURCE` (lines 240 to 244).

## Source and explanation, line by line

- Text shown: the file `bwx10-2026-11-15/test_runner10.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1804 lines, 113828 bytes, sha256 `d34eff54c9f46150481c2f9179b6650351163d7148be924ea0508d37828a1d22`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text of the file (lines 1 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_runner10.py - local tests of the runner bwx10 (round 3).` | Starts the description text of the file. It ends in line 31. This line: the file holds the local tests of the runner `bwx10`. Round 3 is the third set of experiments of the investigation into the buffer size of 8 MiB. |
| 4 | `It is test_runner8.py with the names of bwx10, plus the checks of round 3:` | Description text: this file is `test_runner8.py`, the test file of the runner `bwx8`, with the names of `bwx10`. The checks of round 3 are added. Lines 5 to 6 name them. |
| 5 | `the five new kernels, --rec-pad, --hot-copy, and check_listing10.py on` | Description text: the additions. The five new kernels are the four prefetch kernels and `read_1pl` (line 47). The option `--rec-pad` puts unused bytes before the window records of the runner. With the option `--hot-copy` the loop that runs a window works on local copies. It does not touch its window record between the first and the last pass of the window. The script `check_listing10.py` is the check of the machine-code listing of a build. The tests run it on ... |
| 6 | `synthetic listings. Every check of test_runner8.py is kept. Where bwx10` | Description text: ... synthetic listings, which this file builds itself. A new sentence: every check of `test_runner8.py` is kept. Another sentence starts: where `bwx10` ... |
| 7 | `differs from bwx8 by design, the check was changed and says so:` | Description text: ... differs from `bwx8` on purpose, the check was changed, and its name says so. Lines 8 to 12 list the three changes. |
| 8 | ` - "source": bwx10.c without its marked additions must be bwx8.c;` | Description text, change 1: the checks named `source`. In `bwx10.c` every addition stands between a comment line `bwx10+` and a comment line `bwx10-`. Without these blocks the file must be `bwx8.c`. |
| 9 | ` - a defect (MUTANTS) is placed inside one named function, because` | Description text, change 2: a defect of the table `MUTANTS` is put into one named function. The reason follows in line 10. |
| 10 | `   timed_sequence_hot() repeats lines of timed_sequence();` | Description text: `timed_sequence_hot()` repeats lines of `timed_sequence()`. These are the two C functions that run the windows of a trial. So a text to change can stand in both, and the function name selects one of them. |
| 11 | ` - the listing checks use the accepted listing of bwx8 (ref-bwx8) and add` | Description text, change 3: the listing checks use the accepted listing of `bwx8` as the reference. It lies in the folder `ref-bwx8`. They add ... |
| 12 | `   well-formed listings of the new kernels.` | Description text: ... well-formed listings of the new kernels. The reference has no listing of them. So this file writes these listings itself (line 1175). |
| 14 | `Runs on the development machine (x86-64). It builds bwx10.c with the flags of` | Description text: the tests run on the development machine, which has x86-64 processors and not Arm processors. They build `bwx10.c` with the compiler flags of the build script `build10.sh`. |
| 15 | `build10.sh into a temporary folder. The read kernels are then plain C stand-in` | Description text: the build goes into a temporary folder. On this machine the read kernels are plain C loops that replace the Arm code. |
| 16 | `loops, so rates mean nothing. The tests check the harness: the plan checks,` | Description text: so a rate of such a build means nothing. The tests check the harness, which is the code around the kernels. The list of the checked parts starts: the checks of the plan file. |
| 17 | `the rows, the timed sequence, the trace, the bins, the counter states, and` | Description text: the list goes on: the output rows, the timed sequence, the trace, the bins, the counter states. |
| 18 | `the two build scripts.` | Description text: the end of the list: the two build scripts. By the description of `test_build_scripts` (line 1340) these are `build10.sh` and `check_listing10.py`. |
| 20 | `Usage: test_runner10.py            (KEEP=1 keeps the temporary folder)` | Description text: the usage. The file takes no argument. When the environment variable `KEEP` is set, the temporary folder is kept at the end. |
| 21 | `Output: one line per check, "PASS name" or "FAIL name: detail".` | Description text: the output. Each check prints one line: `PASS` and its name, or `FAIL`, its name and a detail. |
| 22 | `Exit status: 0 only if every check passed.` | Description text: the exit status is 0 only when every check passed. |
| 24 | `A rule that the tests check on the output of bwx10 is a function that returns` | Description text: how a rule is tested. A rule that the tests apply to the output of `bwx10` is a function that returns ... |
| 25 | `a list of problems. Each such function is also run on changed rows, where it` | Description text: ... a list of problems. Each such function is also run on rows that the test changed on purpose ... |
| 26 | `must report a problem. So a rule that could not fail would be seen.` | Description text: ... and it must report a problem there. So a rule that can never fail would be found. |
| 28 | `Some rules cannot be shown to fail on changed rows, because the defect is in` | Description text: some rules cannot be shown to fail on changed rows. The reason: the defect would be in ... |
| 29 | `bwx10.c itself. For these the test builds a copy of bwx10.c with one defect` | Description text: ... `bwx10.c` itself. For these rules the test builds a copy of `bwx10.c` with one defect. |
| 30 | `(MUTANTS) and requires that the check fails on it.` | Description text: the table `MUTANTS` holds these defects. The check must fail on such a copy. |
| 31 | `"""` | Ends the description text. |

### Imports, folders, names of kernels and rows, compiler flags (lines 32 to 59)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `import os` | Loads `os`: paths, folders, the environment and the CPU list of the process. |
| 33 | `import re` | Loads `re`: regular expressions, which are patterns for text. |
| 34 | `import resource` | Loads `resource`: it limits the memory address space of a program that the tests start. |
| 35 | `import shutil` | Loads `shutil`: it copies files and deletes the temporary folder. |
| 36 | `import signal` | Loads `signal`: the numbers of the Linux signals. The tests use the signal `SIGKILL`, which ends a process immediately. |
| 37 | `import subprocess` | Loads `subprocess`: it starts other programs (the compiler, the runner, `objdump`, `nm`) and collects their output. |
| 38 | `import sys` | Loads `sys`: the path of the Python interpreter and the exit of the script. |
| 39 | `import tempfile` | Loads `tempfile`: it creates the temporary folder. |
| 40 | `import time` | Loads `time`: waits and time limits. |
| 42 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this test file. The sources under test are read from it. |
| 43 | `OLD = os.path.join(HERE, "..", "bwx-2026-11-13")` | `OLD`: the folder `bwx-2026-11-13` beside the folder of this file. It holds the first runner, `bwx`. The tests only read it. |
| 44 | `X8 = os.path.join(HERE, "..", "bwx8-2026-11-14")  # the accepted runner of rounds 1 and 2; only read` | `X8`: the folder of the runner `bwx8`. The comment calls it the accepted runner of rounds 1 and 2. The tests only read it. |
| 45 | `REF = os.path.join(HERE, "ref-bwx8")` | `REF`: the folder `ref-bwx8` beside this file. It holds the machine-code listing and the offsets table of the accepted build of `bwx8`. |
| 46 | `B8 = "bwx8"` | `B8`: the name of the accepted runner. The tests build file names from it. |
| 47 | `NEW_KERNELS = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]` | `NEW_KERNELS`: the five kernels that round 3 added. The four `read_pf` kernels are the `asmread` loop with one software prefetch per 64-byte line, 256 to 2048 bytes ahead. `read_1pl` loads 16 bytes of every 64-byte line. |
| 48 | `NEW_M = ["rec_pad", "hot_copy", "rec_addr", "win_addr", "win_size", "stack_addr", "buf_addr", "tw_addr"]` | `NEW_M`: the keys of the 8 `M` rows that round 3 added. An `M` row is one line of settings in the output of the runner, in the form `M,key,value`. |
| 49 | `ADDR_KEYS = ("rec_addr", "win_addr", "stack_addr", "buf_addr", "tw_addr")` | `ADDR_KEYS`: the keys of the five `M` rows that hold a memory address. An address can differ from process to process. So the comparisons of two runs leave these values out. |
| 50 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags, split into a list. `-O3` is the highest standard optimization level. `-march=native` allows the instructions of the build machine. `-fno-tree-loop-distribute-patterns` stops `gcc` from replacing a loop by a call of `memset` or `memcpy`. `-pthread` adds thread support. `-Wall -Wextra` switch the warnings on. `-std=gnu11` selects the C dialect. |
| 51 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues line 50. `-fno-ipa-icf`: `gcc` keeps two functions with equal code as two functions. `-fno-toplevel-reorder`: the functions stay in the order of the source, so each kernel keeps its place in the binary. `-falign-functions=4`: a function start is aligned to 4 bytes only, so the pad bytes in the source decide where a kernel starts. |
| 52 | `MIB8 = 8 << 20` | `MIB8`: 8 MiB in bytes (8388608). It is the buffer size of most tests. The runner also reads the clock after each 8 MiB of reads. |
| 53 | `HEAD1 = "# bwx8-plan v1"` | `HEAD1`: the first line that every plan file must have. It names the format of the plan. |
| 54 | `HEAD3 = "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `HEAD3`: the third line that every plan file must have. It names the 11 fields of a trial line. |
| 55 | `SUFFIX = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `SUFFIX`: the factor of each size letter. `K` is 1024, `M` is 1048576 (1 MiB) and `G` is 1073741824. |
| 57 | `failed = []` | `failed`: the list of the names of the checks that failed. It is empty at the start. |

### Helpers: `check`, `size_of`, `expected_windows`, `rows_of`, `of_trial` (lines 60 to 98)

| Line | Source | Explanation |
|---:|---|---|
| 60 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it with a name, a result (`ok`) and an optional detail. |
| 61 | `    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))` | Prints one line: `PASS` or `FAIL`, then the name. On a failure with a detail it adds a colon and the first 400 characters of the detail. |
| 62 | `    if not ok:` | Tests whether the check failed. |
| 63 | `        failed.append(name)` | Adds the name of the failed check to the list `failed`. The exit status of the file depends on this list. |
| 64 | `    return ok` | Returns `ok`. A caller can stop its test when a step that it needs has failed. |
| 67 | `def size_of(text):` | Starts the function `size_of`. It turns a size text of a plan, such as `8M` or `1000`, into a number of bytes. |
| 68 | `    return int(text[:-1]) * SUFFIX[text[-1]] if text[-1] in SUFFIX else int(text)` | Returns the number of bytes. When the last character is `K`, `M` or `G`, the number before it is multiplied by the factor of `SUFFIX`. If not, the whole text is the number. |
| 71 | `def expected_windows(f):` | Starts the function `expected_windows`. From the fields `f` of one trial line of a plan it builds the list of the windows that the runner must run for that trial. A window is one timed period in which one kernel reads one range again and again. |
| 72 | `    """[(phase, widx, kernel, pass_bytes, min_ns)] of one plan line, from its fields"""` | Description text: each entry of the result holds the phase, the window number inside the phase, the kernel, the bytes of one pass and the shortest duration in ns. |
| 73 | `    out = []` | `out`: the list of windows, empty at the start. |
| 74 | `    for phase, text, n in (("prev", f[3], 1), ("prefix", f[4], 4), ("pred", f[5], 1)):` | Loops over the three optional phases in the order in which they run. `prev` is the previous activity (field 3, 1 window). `prefix` is the same preparation before each target (field 4, 4 windows). `pred` is the predecessor, the kernel that runs directly before the target (field 5, 1 window). |
| 75 | `        if text == "-":` | A field that is `-` means that the trial has no such phase. |
| 76 | `            continue` | Continues with the next phase. |
| 77 | `        kernel, rest = text.split("@")` | Splits the field, for example `oldread@8M:40`, at the `@` into the kernel name and the rest. |
| 78 | `        size, ms = rest.split(":")` | Splits the rest at the colon into the size and the duration in ms. |
| 79 | `        out += [(phase, i, kernel, size_of(size), int(ms) // n * 1000000) for i in range(n)]` | Adds the `n` windows of this phase, numbered from 0. Each one has the kernel, the pass size in bytes and its share of the duration in ns: the ms value divided by `n` without a remainder, times 1000000. A prefix of 40 ms gives 4 windows of 10 ms. |
| 80 | `    kernel, size = f[6].split("@")` | Splits the target field (field 6), for example `oldread@8M`, into the kernel and the size. The target is the kernel whose rate is measured. Its field has no duration. |
| 81 | `    out += [("target", i, kernel, size_of(size), int(f[8]) * 1000000) for i in range(int(f[7]))]` | Adds the target windows. Field 7 (`nwin`) is their number. Field 8 (`win_ms`) is the requested duration of each one in ms. |
| 82 | `    return out` | Returns the list. |
| 85 | `def rows_of(out):` | Starts the function `rows_of`. It sorts the output text of the runner by row type. |
| 86 | `    """{row type: [fields]} of the output of bwx10"""` | Description text: the result is a dictionary. Its key is the row type. Its value is the list of the rows of that type in the output of `bwx10`, each row split into its fields. |
| 87 | `    r = {}` | `r`: the dictionary, empty at the start. |
| 88 | `    for line in out.splitlines():` | Loops over the lines of the output. |
| 89 | `        if line and not line.startswith("#"):` | Takes only a line that is not empty and that is no comment line. A comment line starts with `#`. |
| 90 | `            f = line.split(",")` | Splits the row at the commas into its fields. |
| 91 | `            r.setdefault(f[0], []).append(f)` | Appends the row to the list of its row type. The row type is the first field, for example `W` or `E`. |
| 92 | `    return r` | Returns the dictionary. |
| 95 | `def of_trial(rows, kind, trial):` | Starts the function `of_trial`. It picks the rows of one type that belong to one trial. |
| 96 | `    return [f for f in rows.get(kind, []) if f[1] == str(trial)]` | Returns the rows of the type `kind` whose second field is the trial number. A row type that the output does not hold gives an empty list. |

### Rule `window_problems`: the `W` rows of one trial against its plan line (lines 99 to 121)

| Line | Source | Explanation |
|---:|---|---|
| 99 | `# ---- rules ----` | Comment: the rules start here. A rule is a function that returns a list of problems. An empty list means that the rule holds. |
| 101 | `def window_problems(plan_fields, wrows):` | Starts the rule `window_problems`. It compares the `W` rows of one trial with the plan line of that trial. A `W` row is the record of one window: phase, window number, kernel, bytes of one pass, bytes read, start time and end time. |
| 102 | `    """W rows of one trial against its plan line"""` | Description text: the `W` rows of one trial are compared with its plan line. |
| 103 | `    exp, p, prev_end = expected_windows(plan_fields), [], None` | `exp`: the windows that the plan line asks for (line 71). `p`: the list of problems. `prev_end`: the end time of the window before, not set yet. |
| 104 | `    if len(wrows) != len(exp):` | Tests whether the number of `W` rows equals the number of planned windows. |
| 105 | `        return ["%d W rows, %d expected" % (len(wrows), len(exp))]` | If not, the rule returns this one problem. With a lost or an added window the pairs of the next loop would not match. |
| 106 | `    for w, e in zip(wrows, exp):` | Loops over the rows and the planned windows in pairs. |
| 107 | `        phase, widx, kernel, pb, by, t0, t1 = w[2], int(w[3]), w[4], int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the fields of the row: the phase, the window number, the kernel, the bytes of one pass (`pb`), the bytes read (`by`), the start time `t0` and the end time `t1`. Both times are in ns, counted from the start of the process. |
| 108 | `        if (phase, widx, kernel, pb) != e[:4]:` | Tests that the row names the planned phase, window number, kernel and pass size. This proves that the runner ran the kernel of the plan on the range of the plan. |
| 109 | `            p.append("window %s %d %s %d, expected %s" % (phase, widx, kernel, pb, e[:4]))` | Adds a problem that shows the row and the planned values. |
| 110 | `        if by <= 0 or by % pb:` | Tests the byte count: it must be above 0 and a whole number of passes. A rate is the bytes divided by the time. So a wrong byte count gives a wrong rate. |
| 111 | `            p.append("%s %d: %d bytes is not a whole number of passes above 0" % (phase, widx, by))` | Adds a problem with the phase, the window number and the byte count. |
| 112 | `        if MIB8 % pb == 0 and by % MIB8:` | The 8 MiB rule. The runner reads the clock after 8 MiB of reads. So when the pass size divides 8 MiB, the bytes of a window must be a multiple of 8 MiB. |
| 113 | `            p.append("%s %d: %d bytes is not a multiple of 8 MiB" % (phase, widx, by))` | Adds a problem with the byte count. |
| 114 | `        if t1 - t0 < e[4]:` | Tests the duration: the end time minus the start time must be at least the requested time. A window ends at the first clock read at or after its requested duration. So it can last longer, but never shorter. |
| 115 | `            p.append("%s %d: lasts %d ns, requested %d ns" % (phase, widx, t1 - t0, e[4]))` | Adds a problem with the measured and the requested duration in ns. |
| 116 | `        if not t0 < t1 or (prev_end is not None and t0 < prev_end):` | Tests the order of the times. The start must lie before the end. The window must not start before the window before it ended. |
| 117 | `            p.append("%s %d: timestamps go back" % (phase, widx))` | Adds a problem that says that the time stamps go back. |
| 118 | `        prev_end = t1` | Keeps the end time for the test of the next window. |
| 119 | `    return p` | Returns the list of problems. |

### Rule `e_problems`: the `E` row of one trial against its `W` rows (lines 122 to 138)

| Line | Source | Explanation |
|---:|---|---|
| 122 | `def e_problems(plan_fields, wrows, erow):` | Starts the rule `e_problems`. It computes three values of the `E` row again from the `W` rows. The `E` row is the summary row that ends a trial. |
| 123 | `    """E row of one trial against its W rows: wall time and the two gaps"""` | Description text: the rule covers the wall time and the two gap values of the `E` row. |
| 124 | `    p = []` | `p`: the list of problems. |
| 125 | `    g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. Field 7 of the plan line is the number of target windows. |
| 126 | `    t0 = [int(w[7]) for w in wrows]` | `t0`: the start times of all windows, in ns. |
| 127 | `    t1 = [int(w[8]) for w in wrows]` | `t1`: the end times of all windows, in ns. |
| 128 | `    if int(erow[2]) != t1[-1] - t0[0]:` | Tests `wall_ns` (field 2 of the `E` row): it must be the end of the last window minus the start of the first window. |
| 129 | `        p.append("wall_ns %s, W rows give %d" % (erow[2], t1[-1] - t0[0]))` | Adds a problem with both values. |
| 130 | `    gap = "NA" if g == 0 else str(t0[g] - t1[g - 1])` | Computes the expected `gap_ns`: the start of target window 0 minus the end of the window before it. In this gap no kernel runs. The gap is the time between the two clock reads at that boundary. A trial without a window before the target has no gap. Its value is `NA`. |
| 131 | `    if erow[6] != gap:` | Tests field 6 of the `E` row against this value, as text. |
| 132 | `        p.append("gap_ns %s, W rows give %s" % (erow[6], gap))` | Adds a problem with both values. |
| 133 | `    gaps = [t0[i] - t1[i - 1] for i in range(1, len(wrows))]` | `gaps`: the gap at every boundary between two windows of the trial, in ns. |
| 134 | `    if erow[7] != (str(max(gaps)) if gaps else "NA"):` | Tests `max_boundary_gap_ns` (field 7): it must be the largest of these gaps, or `NA` for a trial with one window. |
| 135 | `        p.append("max_boundary_gap_ns %s, W rows give %s" % (erow[7], max(gaps) if gaps else "NA"))` | Adds a problem with both values. |
| 136 | `    return p` | Returns the list of problems. |

### Rule `bin_problems`: the `B` rows of one trial (lines 139 to 169)

| Line | Source | Explanation |
|---:|---|---|
| 139 | `def bin_problems(plan_fields, wrows, brows, clock_times=None):` | Starts the rule `bin_problems`. It checks the `B` rows of one trial. A `B` row is one time bin inside a target window: the window number, the bin number, the end time of the bin and the bytes read from the window start to that time. |
| 140 | `    """B rows of one trial. clock_times: the times of the clock reads of the trace, if there is one."""` | Description text: `clock_times` holds the times of the clock reads of the trace, when the run has a trace. |
| 141 | `    p = []` | `p`: the list of problems. |
| 142 | `    targets = [w for w in wrows if w[2] == "target"]` | `targets`: the `W` rows of the target windows. Only a target window can have bins. |
| 143 | `    if plan_fields[10] == "0":` | Field 10 of the plan line is the bins switch. `0` means that the trial has no bins. |
| 144 | `        return ["B rows in a trial without bins"] if brows else []` | For such a trial the rule ends here. It returns one problem when any `B` row exists, and no problem if none exists. |
| 145 | `    for w in targets:` | Loops over the target windows. |
| 146 | `        pb, by, t0, t1 = int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the pass size, the bytes, the start time and the end time of the window from its `W` row. |
| 147 | `        bins = [b for b in brows if b[2] == w[3]]` | `bins`: the `B` rows of this window. Field 2 of a `B` row is the window number. |
| 148 | `        if not bins:` | Tests whether the window has no bin at all. |
| 149 | `            p.append("window %s has no bin" % w[3])` | Adds a problem that names the window. |
| 150 | `            continue` | Continues with the next window. |
| 151 | `        ends, cum = [int(b[4]) for b in bins], [int(b[5]) for b in bins]` | `ends`: the end times of the bins in ns. `cum`: the bytes from the window start to each bin end. |
| 152 | `        if [int(b[3]) for b in bins] != list(range(len(bins))):` | Tests that the bins are numbered 0, 1, 2 and so on, without a hole. |
| 153 | `            p.append("window %s: bin numbers are not 0, 1, 2, ..." % w[3])` | Adds a problem that names the window. |
| 154 | `        if ends != sorted(set(ends)) or ends[0] <= t0 or ends[-1] != t1:` | Tests the bin ends. They must rise strictly. The first one must lie after the window start. The last one must equal the window end. So the bins cover the whole window. |
| 155 | `            p.append("window %s: bin ends do not rise to the end of the window" % w[3])` | Adds a problem that names the window. |
| 156 | `        per_bin = [c - d for c, d in zip(cum, [0] + cum[:-1])]` | `per_bin`: the bytes of each bin alone. It is the difference of two neighbour values of `cum`. |
| 157 | `        if sum(per_bin) != by or min(per_bin) <= 0:` | Tests that the bins sum to the bytes of the window and that every bin holds more than 0 bytes. So no byte is lost or counted twice when a rate is computed per bin. |
| 158 | `            p.append("window %s: the bins sum to %d bytes, the window has %d" % (w[3], sum(per_bin), by))` | Adds a problem with the sum of the bins and the bytes of the window. |
| 159 | `        if any(b % pb for b in per_bin):` | Tests that every bin holds whole passes. |
| 160 | `            p.append("window %s: a bin does not hold whole passes" % w[3])` | Adds a problem that names the window. |
| 161 | `        if len(bins) > 1 and ends[0] - t0 < 10000000:` | When a window has more than one bin, bin 0 must last at least 10000000 ns. That is 10 ms, the requested width of a bin. |
| 162 | `            p.append("window %s: bin 0 is shorter than 10 ms" % w[3])` | Adds a problem that names the window. |
| 163 | `        if clock_times is not None and any(e not in clock_times for e in ends):` | Only with a trace: every bin end must be the time of a clock read of the trace. This proves that a bin closes on a clock read that the window loop makes anyway. The bins add no clock read to the timed loop. |
| 164 | `            p.append("window %s: a bin end is not a clock read of the trace" % w[3])` | Adds a problem that names the window. |
| 165 | `    if len(brows) != sum(1 for b in brows if b[2] in [w[3] for w in targets]):` | Counts the `B` rows whose window number is the number of a target window. Every `B` row of the trial must be one of them. |
| 166 | `        p.append("B rows of a window that is not a target window")` | Adds a problem: a `B` row belongs to a window that is no target window. |
| 167 | `    return p` | Returns the list of problems. |

### Rule `trace_problems`: the events of the trace of one trial (lines 170 to 236)

| Line | Source | Explanation |
|---:|---|---|
| 170 | `def trace_problems(plan_fields, events, wrows, erow):` | Starts the rule `trace_problems`. It checks the order of the events that a run with `--trace` logged for one trial. `events` is a list of pairs: the event name and its time in ns. |
| 171 | `    """TR events [(name, t)] of one trial. The timed sequence may hold clock` | Description text: the events come from the `TR` rows of one trial. The timed sequence may hold clock ... |
| 172 | `    reads and the first kernel call of each window. With count 'read' it also` | Description text: ... reads and the first kernel call of each window. The trace logs only the first call of a window. A new sentence starts: with the count mode `read` it also ... |
| 173 | `    holds a counter read and a CPU clock read between the end clock and the` | Description text: ... holds a counter read and a read of the thread CPU clock between the end clock read and the ... |
| 174 | `    start clock of each boundary of a target window. Nothing else."""` | Description text: ... start clock read at each boundary of a target window. No other event is allowed. |
| 175 | `    exp, reads, p = expected_windows(plan_fields), plan_fields[9] == "read", []` | `exp`: the planned windows. `reads`: true when the count field of the plan line (field 9) is `read`. `p`: the list of problems. |
| 176 | `    names = [e[0] for e in events]` | `names`: the event names in the order of the trace. |
| 177 | `    kf = [i for i, n in enumerate(names) if n.startswith("kernel_first")]` | `kf`: the positions of the events whose name starts with `kernel_first`. The runner logs one such event at the first kernel call of each window. |
| 178 | `    want = ["kernel_first:%s:%d" % (e[0], e[1]) for e in exp]` | `want`: the names that these events must have, one per planned window, for example `kernel_first:prefix:2`. |
| 179 | `    if [names[i] for i in kf] != want:` | Tests that the trace holds exactly these first calls, in the planned order. |
| 180 | `        return ["kernel calls %s, expected %s (a warm-up pass or a lost window)" % ([names[i] for i in kf], want)]` | If not, the rule returns this one problem. The cause can be a kernel call that belongs to no planned window, such as a warm-up pass, or a lost window. |
| 181 | `    start, end = kf[0] - 1, kf[-1] + 1` | `start`: the position directly before the first kernel call. `end`: the position directly after the last event `kernel_first`. |
| 182 | `    while end < len(names) and names[end] == "clock":` | Moves `end` forward over the clock reads that follow. These are the clock reads of the last window. |
| 183 | `        end += 1` | One step of this move. |
| 184 | `    end -= 1` | Steps one position back. `end` is now the last clock read of the last window. It ends the timed sequence. |
| 185 | `    if start < 0 or names[start] != "clock" or end == kf[-1]:` | Tests that a clock read stands directly before the first kernel call, and that at least one clock read follows the first call of the last window. |
| 186 | `        return ["no clock read around the first or the last window"]` | If not, the rule returns this one problem. |
| 187 | `    count_tail = [["count_read", "cpu_clock"], ["cpu_clock"]] if reads else [[]]` | `count_tail`: the event lists that may stand between the end clock read of a window and the start clock read of a target window. With the count mode `read`: a counter read and a CPU clock read, or the CPU clock read alone when the counter group did not open. In every other trial: nothing. |
| 188 | `    ends = []  # index of the end clock of each window` | `ends`: the position of the end clock read of each window, as the comment says. It is empty at the start. |
| 189 | `    for j, i in enumerate(kf):` | Loops over the windows. `j` is the number of the window in the trial. `i` is the position of its first kernel call. |
| 190 | `        if names[i - 1] != "clock":` | Tests that the event directly before the first kernel call is a clock read. So nothing runs between the start time of a window and its first pass. |
| 191 | `            p.append("window %d does not start directly after a clock read" % j)` | Adds a problem that names the window. |
| 192 | `        nxt = kf[j + 1] - 1 if j + 1 < len(kf) else end + 1  # the start clock of the next window` | `nxt`: the position of the start clock read of the next window. For the last window it is the position after the end of the timed sequence. The comment says the same. |
| 193 | `        body = names[i + 1:nxt]` | `body`: the events from the first kernel call of this window, not included, to the start clock read of the next window, not included. |
| 194 | `        tail = []` | `tail`: the events of the boundary after this window. It is empty at the start. |
| 195 | `        while body and body[-1] != "clock":` | As long as `body` does not end with a clock read: |
| 196 | `            tail.insert(0, body.pop())` | Moves the last event of `body` to the front of `tail`. At the end `body` ends with the end clock read of the window, and `tail` holds what the runner did between that read and the next start clock read. |
| 197 | `        if not body or any(n != "clock" for n in body):` | Tests the inside of the window: `body` must hold at least one clock read, and nothing but clock reads. A page read, an output or a counter event inside a window is a problem. |
| 198 | `            p.append("inside window %d: %s" % (j, sorted(set(body) - {"clock"}) or "no clock read"))` | Adds a problem that names the window and the foreign events, or the text `no clock read`. |
| 199 | `        ends.append(i + len(body))` | Stores the position of the end clock read of this window. |
| 200 | `        if j + 1 < len(kf):` | For every window but the last: |
| 201 | `            allowed = count_tail if exp[j + 1][0] == "target" else [[]]` | `allowed`: the lists that may stand between this window and the next one. The counter events are allowed only when the next window is a target window. |
| 202 | `            if tail not in allowed:` | Tests that `tail` is one of the allowed lists. This is the check of the gap. A page read, an output or a counter read that is not allowed between two windows would be found here. A kernel call cannot stand in `tail`. A kernel call that the trace logs outside the plan fails the test of line 179. |
| 203 | `                p.append("between window %d and window %d: %s, allowed %s" % (j, j + 1, tail, allowed))` | Adds a problem with the two window numbers, the events found and the allowed lists. |
| 204 | `        clocks, pb = len(body), exp[j][3]` | `clocks`: the number of clock reads of the window. `pb`: its pass size in bytes. |
| 205 | `        # the window ends at the first clock read at or after its requested duration` | Comment: a window ends at the first clock read at or after its requested duration. |
| 206 | `        if clocks > 1 and events[i + clocks - 1][1] - events[i - 1][1] >= exp[j][4]:` | Tests this stop rule on the times of the trace. The clock read before the last one must lie before the requested end, counted from the start clock read. When it lies at or after the requested end, the window continued after the clock read at which it had to stop. |
| 207 | `            p.append("window %d: runs on after the clock read that passed its requested duration" % j)` | Adds a problem that names the window. |
| 208 | `        if j < len(wrows) and clocks != int(wrows[j][6]) // (pb * max(1, MIB8 // pb)):` | Tests the number of clock reads against the bytes of the `W` row: the bytes divided by the bytes between two clock reads. That is one pass for a pass size of 8 MiB or more. For a smaller pass size it is the largest whole number of passes that fits into 8 MiB. So the runner reads the clock once per group of passes, not more and not less. |
| 209 | `            p.append("window %d: %d clock reads for %s bytes" % (j, clocks, wrows[j][6]))` | Adds a problem with the number of clock reads and the bytes. |
| 210 | `    before = names[:start]` | `before`: the events before the start clock read of the first window. |
| 211 | `    if reads and exp[0][0] == "target":` | With the count mode `read`, when the first window is a target window: |
| 212 | `        if before[-2:] not in (["count_read", "cpu_clock"], ["cpu_clock", "cpu_clock"]):` | The last two events before the timed sequence must be the first counter reading: a counter read and a CPU clock read. When the group did not open they are two CPU clock reads. |
| 213 | `            p.append("no counter read before the first target window")` | Adds a problem: no counter read before the first target window. |
| 214 | `        before = before[:-2] if before[-2:] == ["count_read", "cpu_clock"] else before[:-1]` | Removes that counter reading from `before`. |
| 215 | `    if [n for n in before if n not in ("count_open", "count_close")] != ["output", "page_read", "rusage", "cpu_clock"]:` | Tests the rest of `before`, without the events of a counter open or close. It must be exactly: an output (the `S` row that starts the trial), a page read, a read of the context-switch counts (`rusage`) and a CPU clock read, in this order. |
| 216 | `        p.append("before the timed sequence: %s" % before)` | Adds a problem with the events found. |
| 217 | `    after = names[end + 1:]` | `after`: the events after the end of the timed sequence. |
| 218 | `    if reads:` | With the count mode `read`: |
| 219 | `        if after[:2] not in (["count_read", "cpu_clock"],) and after[:1] != ["cpu_clock"]:` | The first events after the timed sequence must be the last counter reading: a counter read with a CPU clock read, or the CPU clock read alone. |
| 220 | `            p.append("no counter read after the last target window")` | Adds a problem: no counter read after the last target window. |
| 221 | `        after = after[2:] if after[:1] == ["count_read"] else after[1:]` | Removes that reading from `after`. |
| 222 | `    if after != ["cpu_clock", "rusage", "page_read", "output"]:` | Tests the rest: exactly a CPU clock read, a read of the context-switch counts, a page read and an output, in this order. So the page state is read and the rows are printed only after the last window. |
| 223 | `        p.append("after the timed sequence: %s" % after)` | Adds a problem with the events found. |
| 224 | `    if not reads and "count_read" in names:` | In a trial without the count mode `read` the trace must hold no counter read at all. |
| 225 | `        p.append("a counter read in a trial with count %s" % plan_fields[9])` | Adds a problem that names the count mode. |
| 226 | `    # the W rows are the clock reads of the trace, and the gap is the time between two of them` | Comment: the times of the `W` rows are clock reads of the trace, and the gap is the time between two of them. The next lines test this. |
| 227 | `    if len(wrows) == len(kf) and not p:` | Only when the trial has as many `W` rows as the trace has windows, and no problem was found so far: |
| 228 | `        for j, w in enumerate(wrows):` | Loops over the `W` rows. |
| 229 | `            if int(w[7]) != events[kf[j] - 1][1] or int(w[8]) != events[ends[j]][1]:` | The start time of the `W` row must be the time of the clock read before the first kernel call of the window. Its end time must be the time of the end clock read. So the printed times are the times that the timed loop read, and no other clock read. |
| 230 | `                p.append("window %d: the W row does not hold the clock reads of the trace" % j)` | Adds a problem that names the window. |
| 231 | `        g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. |
| 232 | `        if g and erow[6] != str(events[kf[g] - 1][1] - events[ends[g - 1]][1]):` | When such a window exists: `gap_ns` of the `E` row must be the start clock read of target window 0 minus the end clock read of the window before it. |
| 233 | `            p.append("gap_ns %s is not the time between the two clock reads of the trace" % erow[6])` | Adds a problem with the printed value. |
| 234 | `    return p` | Returns the list of problems. |

### Rules on the C source: `fn_span`, `hot_source_problems`, `seq_source_problems` (lines 237 to 300)

| Line | Source | Explanation |
|---:|---|---|
| 237 | `# The timed sequence, read from the source and from the machine code. The` | Comment: the next two rules read the timed sequence from the C source and from the machine code. |
| 238 | `# trace holds only what the wrappers log themselves. These two rules do not` | Comment: the trace holds only the events that the wrapper functions of the runner log themselves. A wrapper function here is a small function around the clock read or around the kernel call. |
| 239 | `# depend on that log.` | Comment: the two rules do not depend on that log. So they also find a call that the trace would not show. |
| 240 | `SEQ_SOURCE = {"timed_sequence": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall": 1},` | `SEQ_SOURCE`: for each C function of the timed path, the names that may stand directly before a `(` in its body, each with its count. This line: `timed_sequence`, the function that runs the windows of one trial. It may hold 2 `for`, 3 `if`, 2 `while`, 2 calls of `tcount` (the counter read), 2 calls of `tclock` (the clock read) and 1 call of `tcall` (the kernel call). |
| 241 | `              "timed_sequence_hot": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall_hot": 1},` | The entry of `timed_sequence_hot`, the function that runs the windows with the option `--hot-copy`: the same counts, with `tcall_hot` as its kernel call. |
| 242 | `              "tclock": {"now_ns": 1, "if": 1, "tev_add": 1},` | The entry of `tclock`, the clock read: 1 call of `now_ns` (it reads the clock of Linux), 1 `if` and 1 call of `tev_add` (it adds an event to the trace). |
| 243 | `              "tcall": {"if": 1, "tev_add": 1, "call": 1},` | The entry of `tcall`, the kernel call: 1 `if`, 1 call of `tev_add` and 1 call of `call`. `call` is the function of the runner that starts a kernel. |
| 244 | `              "tcall_hot": {"if": 1, "tev_add": 1, "call": 1}}` | The entry of `tcall_hot`: the same counts as `tcall`. The last brace ends the dictionary. |
| 245 | `SEQ_FUNCTIONS = ("timed_sequence", "timed_sequence_hot")` | `SEQ_FUNCTIONS`: the names of the two functions that run a timed sequence. The rules for the machine code are applied to both. |
| 246 | `FN_HEAD = r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n"` | `FN_HEAD`: a pattern for the first two lines of the definition of a C function. `%s` takes the function name. The first line may start with `__attribute__((noinline))`. Then come `static`, an optional `inline`, the return type, the name and the argument list in round brackets. The second line must hold only `{`. |
| 249 | `def fn_span(src, fn):` | Starts the function `fn_span`. It finds the body of the C function `fn` in the source text `src`. |
| 250 | `    """(start, end) of the body of the C function fn, or None"""` | Description text: the result is the pair of the start and the end position of the body, or `None`. |
| 251 | `    m = re.search(FN_HEAD % fn + r"(.*?)^\}\n", src, re.M \| re.S)` | Searches for the head of the function (`FN_HEAD`) and takes the shortest text after it that ends before a line holding only `}`. Group 1 is that text, the body. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. |
| 252 | `    return (m.start(1), m.end(1)) if m else None` | Returns the start and the end position of group 1, or `None` when the function was not found. |
| 255 | `def replace_in(src, fn, good, bad):` | Starts the function `replace_in`. It makes a changed copy of a source text. The tests use it to put one defect into the source of the runner. |
| 256 | `    """src with 'good' replaced by 'bad' inside function fn (the whole text if fn is None).` | Description text: the result is `src` with `good` replaced by `bad` inside the function `fn`, or in the whole text when `fn` is `None`. |
| 257 | `    None unless 'good' stands exactly once there."""` | Description text: the result is `None` unless `good` stands exactly once in that range. |
| 258 | `    span = (0, len(src)) if fn is None else fn_span(src, fn)` | `span`: the range to change. It is the whole text, or the body of `fn`. |
| 259 | `    if src is None or span is None or src[span[0]:span[1]].count(good) != 1:` | Tests that the range was found and that `good` stands exactly once in it. So a defect is never put in at two places, and a text that is no longer in the source is noticed. The test `src is None` has no effect at this place: line 258 already used `src`. |
| 260 | `        return None` | Returns `None` in that case. |
| 261 | `    return src[:span[0]] + src[span[0]:span[1]].replace(good, bad) + src[span[1]:]` | Returns the text before the range, then the range with `good` replaced by `bad`, then the text after the range. |
| 264 | `def hot_source_problems(src):` | Starts the rule `hot_source_problems`. It reads the source text of `timed_sequence_hot`, the function that runs the windows with the option `--hot-copy`. |
| 265 | `    """timed_sequence_hot() of bwx10.c: between the start clock read of a window and the store of its results,` | Description text: the rule is about `timed_sequence_hot()` of `bwx10.c`. Between the start clock read of a window and the store of its results ... |
| 266 | `    the text names no field of the window record (x->), no field of the trial record (r->) and no win[]."""` | Description text: ... the text must name no field of the window record (`x->`), no field of the trial record (`r->`) and no `win[]`. The window record is the place where the runner keeps the settings and the results of one window. |
| 267 | `    span = fn_span(src, "timed_sequence_hot")` | `span`: the body of `timed_sequence_hot` in the source text. |
| 268 | `    if span is None:` | Tests whether the function was not found. |
| 269 | `        return ["no function timed_sequence_hot"]` | Returns this one problem. |
| 270 | `    body = src[span[0]:span[1]]` | `body`: the text of the body. |
| 271 | `    a, b = body.find("        t0 = tclock(w);\n"), body.find("        x->bytes = bytes;\n")` | `a`: the position of the line with the start clock read of a window, `t0 = tclock(w);`. `b`: the position of the line with the first store of a result, `x->bytes = bytes;`. `find` gives -1 when the text is not there. |
| 272 | `    if a < 0 or b < a:` | Tests whether one of the two lines is missing, or the store stands before the clock read. |
| 273 | `        return ["the start clock read or the store of the results is not found"]` | Returns this one problem. |
| 274 | `    loop = re.sub(r"/\*.*?\*/", "", body[a:b], flags=re.S)` | `loop`: the text between the two positions, without C comments. This is the window loop: every pass and every clock read of one window. |
| 275 | `    p = ["the window loop of timed_sequence_hot names %s" % w for w in ("x->", "r->", "win") if w in loop]` | `p`: one problem for each of the texts `x->`, `r->` and `win` that `loop` holds. With `--hot-copy` the window loop must work on local copies. It must not read or write the window record between the first and the last pass. The rule proves this for the source text. |
| 276 | `    need = ("k = x->k", "phase = x->phase", "widx = x->widx", "bin_cap = x->bin_cap", "size = x->size", "passes = x->passes",` | `need`: the copies that must stand before the window loop: the kernel number, the phase, the window number, the room for bins, the pass size, the number of passes between two clock reads ... |
| 277 | `            "dur_ns = x->dur_ns", "bin = x->bin")` | Continues line 276: ... the requested duration in ns and the address of the bins. |
| 278 | `    return p + ["no copy '%s' before the window loop" % n for n in need if n not in body[:a]]` | Returns the problems of line 275, plus one problem for each copy that the text before the start clock read does not hold. |
| 279 | `SEQ_ALLOWED = {"clock_gettime", "(indirect)", "tcount", "__stack_chk_fail"}` | `SEQ_ALLOWED`: the only places outside itself to which the machine code of a timed function may branch. `clock_gettime` reads the clock. `(indirect)` means a call through a pointer, which is the kernel call. `tcount` is the counter read of the runner. `__stack_chk_fail` is the function that the compiler calls when the guard value on the stack was overwritten. |
| 282 | `def seq_source_problems(src):` | Starts the rule `seq_source_problems`. It counts the names before a `(` in the source text of the functions of the timed path. |
| 283 | `    """The words before a '(' in timed_sequence(), tclock() and tcall() of bwx10.c:` | Description text: the rule reads the words before a `(` in `timed_sequence()`, `tclock()` and `tcall()` of `bwx10.c`. The text names three functions. The table `SEQ_SOURCE` (lines 240 to 244), which the rule follows, also holds `timed_sequence_hot` and `tcall_hot`. |
| 284 | `    one clock read at each end of a window, one kernel call per pass, the` | Description text: allowed are one clock read at each end of a window, one kernel call per pass, ... |
| 285 | `    counter read at the two places of count 'read', and no other call."""` | Description text: ... the counter read at the two places of the count mode `read`, and no other call. |
| 286 | `    p = []` | `p`: the list of problems. |
| 287 | `    for fn, want in SEQ_SOURCE.items():` | Loops over the entries of `SEQ_SOURCE`: the function name `fn` and its expected counts `want`. |
| 288 | `        m = re.search(r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n(.*?)^\}\n" % fn, src,` | Searches for the function `fn` in the source. The pattern matches the head of its definition: an optional `__attribute__((noinline))`, then `static`, an optional `inline`, the return type, the name, the arguments, and a line with `{`. Group 1 is the body, up to the first line that holds only `}`. |
| 289 | `                      re.M \| re.S)` | Continues the call of line 288: the flags. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. |
| 290 | `        if not m:` | Tests whether the function was not found. |
| 291 | `            p.append("no function %s" % fn)` | Adds a problem that names the function. |
| 292 | `            continue` | Continues with the next function. |
| 293 | `        got = {}` | `got`: the counts found, empty at the start. |
| 294 | `        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)):` | Removes the C comments from the body. Then finds every name that stands before a `(`, with optional spaces between them. Such a name is a function call or a keyword such as `if`, `for` and `while`. |
| 295 | `            got[name] = got.get(name, 0) + 1` | Adds 1 to the count of that name. |
| 296 | `        if got != want:` | Tests that the counts found equal the expected counts exactly. An added call in the timed path, for example a second clock read, a page read or a warm-up kernel call, changes a count and is found. |
| 297 | `            p.append("%s holds %s, expected %s" % (fn, sorted(got.items()), sorted(want.items())))` | Adds a problem with the counts found and the expected counts. |
| 298 | `    return p` | Returns the list of problems. |

### Machine-code rule: `seq_targets` and `seq_code_problems` (lines 301 to 326)

| Line | Source | Explanation |
|---:|---|---|
| 301 | `def seq_targets(binary, fn="timed_sequence"):` | Starts the function `seq_targets`. It reads from the machine code of `binary` where the function `fn` branches to. |
| 302 | `    """{branch target outside function fn: count} from the machine code (x86-64 or AArch64 objdump text)"""` | Description text: the result is a dictionary from each branch target outside `fn` to the number of branches to it. The function reads the text that `objdump` prints for x86-64 or for AArch64, the 64-bit Arm instruction set. |
| 303 | `    out = subprocess.run(["objdump", "-d", "--no-show-raw-insn", "--disassemble=" + fn, binary],` | Runs the tool `objdump` on the binary. `-d` prints the machine code as instructions. `--no-show-raw-insn` leaves out the bytes of each instruction. `--disassemble=` limits the output to the function `fn`. |
| 304 | `                         stdout=subprocess.PIPE, universal_newlines=True).stdout` | Continues the call that runs `objdump`: its output is collected as text. |
| 305 | `    t = {}` | `t`: the dictionary of the targets, empty at the start. |
| 306 | `    for line in out.splitlines():` | Loops over the lines of the `objdump` output. |
| 307 | `        f = line.split()` | Splits the line at spaces and tabs into fields. |
| 308 | `        if len(f) < 3 or not re.fullmatch(r"[0-9a-f]+:", f[0]):` | Takes only an instruction line: at least 3 fields, and a first field that is a hex address with a colon. |
| 309 | `            continue` | Skips every other line. |
| 310 | `        if re.search(r"\s(call\|jmp)q?\s+\*", line) or f[1] in ("blr", "br"):` | Tests for a call or a jump through a pointer. On x86-64 the operand of such an instruction starts with `*`. On AArch64 the instructions are `blr` and `br`. |
| 311 | `            name = "(indirect)"` | Such a branch gets the name `(indirect)`. The kernel call is of this kind: the runner calls a kernel through a function pointer. |
| 312 | `        elif re.fullmatch(r"callq?\|jmpq?\|j[a-z]+\|bl\|b\|b\.[a-z]+\|cbn?z\|tbn?z", f[1]) and re.fullmatch(r"<.*>", f[-1]):` | If not: tests for a direct call, jump or branch whose last field is a symbol name in angle brackets. The pattern lists the instruction names of both machines: `call`, `jmp` and the conditional jumps of x86-64, and `bl`, `b`, `b.` with a condition, `cbz`, `cbnz`, `tbz` and `tbnz` of AArch64. |
| 313 | `            name = re.sub(r"\+0x[0-9a-f]+$\|@plt", "", f[-1][1:-1])` | `name`: the symbol name without the angle brackets, without an offset such as `+0x1c` at its end and without the mark `@plt`. That mark shows a call of a library function through the linker table. |
| 314 | `            if name == fn:` | Tests whether the target lies inside the function `fn` itself. |
| 315 | `                continue` | Skips such a branch: it does not leave the function. |
| 316 | `        else:` | Every other instruction line holds no branch with a named target. |
| 317 | `            continue` | Skips such a line. |
| 318 | `        t[name] = t.get(name, 0) + 1` | Adds 1 to the count of the target. |
| 319 | `    return t` | Returns the dictionary. |
| 322 | `def seq_code_problems(targets, fn="timed_sequence"):` | Starts the rule `seq_code_problems`. It judges the branch targets that `seq_targets` found for the function `fn`. |
| 323 | `    p = ["%s reaches %s" % (fn, n) for n in sorted(set(targets) - SEQ_ALLOWED)]` | `p`: one problem for each target that is not in `SEQ_ALLOWED`. A call of an output function or of a page read inside a timed function is found here, also when the trace does not log it. A helper that the compiler did not put inline shows here too, under its own name. |
| 324 | `    return p + ["%s has no call of %s" % (fn, n) for n in ("clock_gettime", "(indirect)") if n not in targets]` | Returns these problems, plus one problem for each of `clock_gettime` and `(indirect)` that is missing. Without the first the function reads no clock. Without the second it calls no kernel. |

### Rule `placement_problems`: the order of pin and memory mapping (lines 327 to 353)

| Line | Source | Explanation |
|---:|---|---|
| 327 | `def placement_problems(lines, cpu, ctl):` | Starts the rule `placement_problems`. It reads the log lines of the preloaded library (line 354) and checks in which order the two threads pin themselves and map memory. `cpu` is the CPU of the worker thread. `ctl` is the CPU of the controlling thread. |
| 328 | `    """Lines 'shim <call> pid=P tid=T <a> <b>' of the preloaded library, in time` | Description text: each log line has the form `shim <call> pid=P tid=T <a> <b>`. The lines stand in time ... |
| 329 | `    order. setaffinity: a = CPUs in the set, b = the first one. mmap: a = bytes.` | Description text: ... order. For `setaffinity`, `a` is the number of CPUs in the set and `b` is the first of them. For `mmap`, `a` is the number of bytes. |
| 330 | `    The controlling thread pins itself to ctl before the worker exists. The` | Description text: the controlling thread must pin itself to `ctl` before the worker thread exists. |
| 331 | `    worker pins itself to cpu before it maps the buffer."""` | Description text: the worker thread must pin itself to `cpu` before it maps the buffer. |
| 332 | `    ev = []` | `ev`: the list of the events, empty at the start. |
| 333 | `    for line in lines:` | Loops over the log lines. |
| 334 | `        f = line.split()` | Splits the line at the spaces into fields. |
| 335 | `        ev.append((f[1], f[3] == "tid=" + f[2][4:], f[3], int(f[4]), int(f[5])))` | Adds one event with five values: the call name, whether the caller is the main thread, the thread id text, and the two numbers. The caller is the main thread when its thread id equals the process id. In the trial mode the main thread is the controlling thread. |
| 336 | `    first_worker = next((i for i, e in enumerate(ev) if not e[1]), None)` | `first_worker`: the position of the first event of a thread that is not the main thread, or `None`. |
| 337 | `    if first_worker is None:` | Tests whether no such event exists. |
| 338 | `        return ["no call of the worker thread"]` | Returns this one problem. |
| 339 | `    p = []` | `p`: the list of problems. |
| 340 | `    if len({e[2] for e in ev}) != 2:` | Tests that exactly 2 threads made calls: the controlling thread and one worker. |
| 341 | `        p.append("%d threads, 2 expected" % len({e[2] for e in ev}))` | Adds a problem with the number of threads. |
| 342 | `    if ("setaffinity", True, 1, ctl) not in [(e[0], e[1], e[3], e[4]) for e in ev[:first_worker]]:` | Tests the controlling thread. Before the first event of the worker it must have made a `setaffinity` call with exactly 1 CPU in the set, the CPU `ctl`. So the controlling thread is pinned to its own CPU before the worker starts, and it cannot run on the CPU of the worker. |
| 343 | `        p.append("the controlling thread did not pin itself to CPU %d before the worker started" % ctl)` | Adds a problem that names the CPU `ctl`. |
| 344 | `    w = [e for e in ev if not e[1]]` | `w`: the events of the worker thread. |
| 345 | `    if (w[0][0], w[0][3], w[0][4]) != ("setaffinity", 1, cpu):` | Tests that the first logged call of the worker is its pin: `setaffinity` with 1 CPU, the CPU `cpu`. |
| 346 | `        p.append("the first call of the worker is %s %d %d, not its pin to CPU %d" % (w[0][0], w[0][3], w[0][4], cpu))` | Adds a problem with the call found. |
| 347 | `    if not any(e[0] == "mmap" and e[3] >= MIB8 for e in w[1:]):` | Tests that a later call of the worker is an `mmap` of at least 8 MiB. That is the buffer. So the worker is pinned before it maps the buffer. The first touch of the buffer then happens on the CPU that later reads it. |
| 348 | `        p.append("the worker did not map the buffer after its pin")` | Adds a problem: the worker did not map the buffer after its pin. |
| 349 | `    if any(e[0] == "mmap" and e[1] and e[3] >= MIB8 for e in ev):` | Tests that the main thread made no `mmap` of 8 MiB or more. The controlling thread must not own a buffer. |
| 350 | `        p.append("the controlling thread mapped a buffer")` | Adds a problem. |
| 351 | `    return p` | Returns the list of problems. |

### `SHIM`: the C source of the library that logs the calls (lines 354 to 393)

| Line | Source | Explanation |
|---:|---|---|
| 354 | `SHIM = r"""` | `SHIM`: the C source text of a small library, as a raw text that ends in line 392. A test builds it and loads it into the runner with the variable `LD_PRELOAD`. Its functions then replace the C library functions of the same name. Each one logs the call and passes it on to Linux. |
| 355 | `#define _GNU_SOURCE` | C text: `_GNU_SOURCE` switches on the Linux extensions of the header files, such as the macros for CPU sets. |
| 356 | `#include <errno.h>` | C text: includes `errno.h`, for the error number `errno` and the value `EINVAL`. |
| 357 | `#include <sched.h>` | C text: includes `sched.h`, for the type and the macros of a CPU set. |
| 358 | `#include <stdio.h>` | C text: includes `stdio.h`, for `snprintf`. |
| 359 | `#include <stdlib.h>` | C text: includes `stdlib.h`, for `getenv`. |
| 360 | `#include <sys/mman.h>` | C text: includes `sys/mman.h`, for the declarations of `mmap` and `madvise`. |
| 361 | `#include <sys/syscall.h>` | C text: includes `sys/syscall.h`, for the numbers of the system calls. |
| 362 | `#include <unistd.h>` | C text: includes `unistd.h`, for `write`, `getpid` and `syscall`. |
| 363 | `static void note(const char *what, long a, long b)` | C text: starts the function `note`. It writes one log line for the call named `what` with the two numbers `a` and `b`. |
| 364 | `{` | C text: opens the body of `note`. |
| 365 | `    char buf[128];` | C text: `buf`: room for one log line of up to 127 characters. |
| 366 | `    int n = snprintf(buf, sizeof buf, "shim %s pid=%d tid=%ld %ld %ld\n", what, (int)getpid(), syscall(SYS_gettid), a, b);` | C text: builds the line `shim <call> pid=<process id> tid=<thread id> <a> <b>`. `syscall(SYS_gettid)` asks Linux for the id of the calling thread. `n` is the length of the line. |
| 367 | `    if (write(2, buf, (size_t)n) < 0)` | C text: writes the line to the error output (file number 2) with one `write` call. |
| 368 | `        return;` | C text: returns when the `write` failed. The function ends directly after this line in both cases. |
| 369 | `}` | C text: ends the function `note`. |
| 370 | `int sched_setaffinity(pid_t pid, size_t len, const cpu_set_t *set)` | C text: starts the replacement of `sched_setaffinity`, the call that sets the CPUs on which a thread may run. The runner pins its threads with it. |
| 371 | `{` | C text: opens the body. |
| 372 | `    long first = -1;` | C text: `first`: the lowest CPU of the set. It is -1 as long as none is found. |
| 373 | `    for (long c = 0; c < 8 * (long)len && first < 0; c++)` | C text: loops over the CPU numbers that a set of `len` bytes can hold (8 per byte), until a CPU is found. |
| 374 | `        if (CPU_ISSET_S(c, len, set))` | C text: tests whether the CPU `c` is in the set. |
| 375 | `            first = c;` | C text: keeps it as `first`. |
| 376 | `    note("setaffinity", CPU_COUNT_S(len, set), first);` | C text: logs `setaffinity` with the number of CPUs in the set and the first CPU. |
| 377 | `    return (int)syscall(SYS_sched_setaffinity, pid, len, set);` | C text: passes the call on to Linux with the system call of the same name and returns its result. So the pin still happens. |
| 378 | `}` | C text: ends the replacement of `sched_setaffinity`. |
| 379 | `void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off)` | C text: starts the replacement of `mmap`, the call that asks Linux for a new range of memory. |
| 380 | `{` | C text: opens the body. |
| 381 | `    note("mmap", (long)len, 0);` | C text: logs `mmap` with the number of bytes. The second number is 0. |
| 382 | `    return (void *)syscall(SYS_mmap, addr, len, prot, flags, fd, off);` | C text: passes the call on to Linux and returns the address that Linux gave. |
| 383 | `}` | C text: ends the replacement of `mmap`. |
| 384 | `int madvise(void *addr, size_t len, int advice)` | C text: starts the replacement of `madvise`. The runner asks Linux for huge pages with this call. |
| 385 | `{` | C text: opens the body. |
| 386 | `    if (getenv("SHIM_MADVISE_FAIL")) {` | C text: tests whether the environment variable `SHIM_MADVISE_FAIL` is set. |
| 387 | `        errno = EINVAL;` | C text: sets the error number to `EINVAL`, the value for an invalid argument. |
| 388 | `        return -1;` | C text: returns -1. The runner sees a failed request. The test of line 777 uses this to check how the runner reports the failure. |
| 389 | `    }` | C text: ends the `if`. |
| 390 | `    return (int)syscall(SYS_madvise, addr, len, advice);` | C text: if the variable is not set, passes the call on to Linux and returns its result. |
| 391 | `}` | C text: ends the replacement of `madvise`. |
| 392 | `"""` | Ends the text `SHIM`. |

### `MUTANTS`: one defect each in a copy of the runner source (lines 394 to 440)

| Line | Source | Explanation |
|---:|---|---|
| 394 | `# One defect each in a copy of bwx10.c: [(function or None for the whole text, text of bwx10.c, changed text)].` | Comment: each entry of the table below is one defect in a copy of `bwx10.c`. A defect is a list of changes. Each change holds a function name (or `None` for the whole text), the text of `bwx10.c` to find and the changed text. |
| 395 | `WARM = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) call(&kernels[x->k], "` | `WARM`: one change, as a pair of the text to find and the changed text. The text to find is the line with the start clock read of a window, `t0 = tclock(w);`, and the first word of the line after it. The changed text starts here: before that clock read it adds one kernel call when the window is target window 0. |
| 396 | `        "&w->t, 0, x->size, 0, sink);\n        t0 = tclock(w);\n        next_bin")` | Continues the changed text: the arguments of the added kernel call, then the original text. The added call is a warm-up pass over the range of the window. It calls `call` directly and not `tcall`, so the trace does not log it. |
| 397 | `PAGE = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) { long long vmx[4]; "` | `PAGE`: a second change at the same place. Before the start clock read of target window 0 it adds a block with an array `vmx` ... |
| 398 | `        "read_vmstat(vmx); fflush(stdout); }\n        t0 = tclock(w);\n        next_bin")` | Continues the changed text: the block reads four counters of the file `/proc/vmstat` (`read_vmstat`) and flushes the output (`fflush(stdout)`). The design forbids a page read and an output between two windows. |
| 399 | `CLOCK = ("            t1 = tclock(w);\n", "            t1 = tclock(w);\n            if (x->bin) (void)now_ns();\n")` | `CLOCK`: a third change. After the clock read that follows a group of passes, `t1 = tclock(w);`, it adds a second clock read with `now_ns()` when the window has bins. That read does not go through `tclock`, so the trace does not log it. |
| 400 | `MUTANTS = {` | `MUTANTS`: the table of the defects. The key is the name of the defect. The names of the checks print it. The value is the list of the changes of that defect. |
| 401 | `    "a warm-up pass before the first target window": [("timed_sequence",) + WARM],` | Defect: a warm-up pass before the first target window. It is the change `WARM` in the function `timed_sequence`. |
| 402 | `    "a page read and an output flush before the first target window": [("timed_sequence",) + PAGE],` | Defect: a page read and an output flush before the first target window. It is the change `PAGE` in `timed_sequence`. |
| 403 | `    "an added clock read in a window with bins": [("timed_sequence",) + CLOCK],` | Defect: an added clock read in a window with bins. It is the change `CLOCK` in `timed_sequence`. |
| 404 | `    "the two context-switch counts exchanged in the E row":` | Defect: the `E` row prints the two context-switch counts in exchanged fields. |
| 405 | `        [(None, "r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]", "r->nivcsw[1] - r->nivcsw[0], r->nvcsw[1] - r->nvcsw[0]")],` | The change, in the whole text: the two arguments of the `printf` call are exchanged. `nvcsw` counts the voluntary context switches, in which the thread gave up the CPU. `nivcsw` counts the involuntary ones, in which Linux took the CPU away. |
| 406 | `    "wall time printed as cpu_ns":` | Defect: the field `cpu_ns` of the `E` row holds the wall time. |
| 407 | `        [(None, "(unsigned long long)(r->cpu[1] - r->cpu[0]));", "(unsigned long long)(r->win[r->nw - 1].t_end - r->win[0].t_start));")],` | The change: the difference of the two CPU clock reads is replaced by the end of the last window minus the start of the first window. |
| 408 | `    "the pre snapshot printed in the post P row":` | Defect: the `P` row `post` prints the page state that was read before the timed sequence. |
| 409 | `        [(None, 'print_p8(i, "post", &r->pg[1], r->vm[1]);', 'print_p8(i, "post", &r->pg[0], r->vm[0]);')],` | The change: the call that prints the row `post` gets the first snapshot (`pg[0]`, `vm[0]`) in place of the second one. |
| 410 | `    "C rows that hold the readings, not their differences":` | Defect: a `C` row holds the counter readings at the end of its window, and not their change over the window. |
| 411 | `        [(None, "(unsigned long long)(c1->enabled - c0->enabled)", "(unsigned long long)(c1->enabled)"),` | Change 1 of 3: the enabled time of the counter group is printed as the second reading alone, without the subtraction. |
| 412 | `         (None, "(unsigned long long)(c1->running - c0->running));\n        else", "(unsigned long long)(c1->running));\n        else"),` | Change 2 of 3: the same for the running time. The text to find also holds the line break and the `else` that follow. |
| 413 | `         (None, "(unsigned long long)(c1->val[at] - c0->val[at]));", "(unsigned long long)(c1->val[at]));")],` | Change 3 of 3: the same for the count of each event. The last bracket ends the list of this defect. |
| 414 | `    "no X row count_multiplexed":` | Defect: the row `X,<trial>,count_multiplexed` is never printed. An `X` row reports a failure. This one reports a counter that ran for less time than it was enabled. |
| 415 | `        [(None, "        if (m >= 0)\n", "        if (0 && m >= 0)\n")],` | The change: the condition `m >= 0` gets `0 &&` in front, so it is never true. |
| 416 | `    "no X row sink":` | Defect: the row `X,<trial>,sink` is never printed. It reports that the old read kernel did not leave the sum of its range in the result variable. |
| 417 | `        [(None, "    if (r->sink_ok == 0)\n        printf(\"X", "    if (0)\n        printf(\"X")],` | The change: the condition `r->sink_ok == 0` becomes `0`. |
| 418 | `    "no X row coverage_na":` | Defect: the row `X,<trial>,coverage_na` is never printed. It reports that the huge-page state of the buffer could not be read. |
| 419 | `        [(None, "    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)\n", "    if (0)\n")],` | The change: the condition on the two snapshots becomes `0`. |
| 420 | `    # gcc itself turns malloc + memset into calloc, which writes no page of a fresh block` | Comment: `gcc` itself turns the pair `malloc` and `memset` into `calloc`. `calloc` writes no page of a fresh block. So without a store of its own the runner would touch the pages of its records first during a trial. |
| 421 | `    "record storage without the store to every page before the first trial":` | Defect: the storage of the records is not written before the first trial. |
| 422 | `        [(None, "        ((volatile char *)mem)[at] = 0;\n", "        ;\n"), (None, "    ((volatile char *)mem)[recsz.bytes - 1] = 0;\n", "")],` | Two changes: the store of one byte to every page becomes an empty statement, and the store to the last byte is removed. |
| 423 | `    # round 3: the same three defects of the timed sequence in the function of --hot-copy` | Comment: round 3 added the next entries. The first three are the three defects of the timed sequence, now in the function that runs with `--hot-copy`. |
| 424 | `    "a warm-up pass before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + WARM],` | Defect: the change `WARM` in `timed_sequence_hot`. |
| 425 | `    "a page read and an output flush before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + PAGE],` | Defect: the change `PAGE` in `timed_sequence_hot`. |
| 426 | `    "an added clock read in a window with bins, in timed_sequence_hot": [("timed_sequence_hot",) + CLOCK],` | Defect: the change `CLOCK` in `timed_sequence_hot`. |
| 427 | `    "timed_sequence_hot reads the pass count from the window record after every pass":` | Defect: `timed_sequence_hot` reads the pass count from the window record after every pass. |
| 428 | `        [("timed_sequence_hot", "c < passes;", "c < passes && c < x->passes;")],` | The change: the loop condition `c < passes;` also tests `c < x->passes`. So the loop reads a field of the window record after each pass. With `--hot-copy` it must not do that. |
| 429 | `    "--hot-copy that still runs timed_sequence":` | Defect: with `--hot-copy` the runner still runs `timed_sequence`. |
| 430 | `        [("run_trial", "    if (plan.hot_copy)\n", "    if (0)\n")],` | The change, in `run_trial`: the test of the option becomes `if (0)`. So `timed_sequence_hot` is never chosen. |
| 431 | `    "--rec-pad that does not move the window records":` | Defect: `--rec-pad` does not move the window records. |
| 432 | `        [("alloc_records", "    win = (struct win *)((char *)win + plan.rec_pad);\n", "")],` | The change, in `alloc_records`: the line that adds the pad to the address of the window records is removed. |
| 433 | `}` | Ends the table `MUTANTS`. |
| 434 | `SEQ_MUTANTS = list(MUTANTS)[:3]` | `SEQ_MUTANTS`: the names of the first 3 entries of the table. A Python dictionary keeps the order in which its entries were written. These are the three defects of `timed_sequence`. |
| 435 | `ROW_MUTANTS = list(MUTANTS)[3:10]` | `ROW_MUTANTS`: the names of the entries 4 to 10, the 7 defects of the output rows. |
| 436 | `TOUCH_MUTANT = list(MUTANTS)[10]` | `TOUCH_MUTANT`: the name of entry 11, the record storage without the first store. |
| 437 | `HOT_SEQ_MUTANTS = list(MUTANTS)[11:14]` | `HOT_SEQ_MUTANTS`: the names of the entries 12 to 14, the three defects of `timed_sequence_hot`. |
| 438 | `HOT_READ_MUTANT, HOT_OFF_MUTANT, PAD_MUTANT = list(MUTANTS)[14:17]` | The names of the entries 15, 16 and 17: the read of the pass count from the window record, the `--hot-copy` that still runs `timed_sequence`, and the `--rec-pad` that moves nothing. |

### `mutant_source` and `mutant_build`: a copy of the runner with one defect (lines 441 to 465)

| Line | Source | Explanation |
|---:|---|---|
| 441 | `def mutant_source(name):` | Starts the function `mutant_source`. It returns the source text of the runner with the defect `name`. |
| 442 | `    """bwx10.c with the defect 'name', or None if a text to change is not there exactly once"""` | Description text: the result is `bwx10.c` with the defect, or `None` when a text to change does not stand there exactly once. |
| 443 | `    with open(os.path.join(HERE, "bwx10.c")) as f:` | Opens `bwx10.c` in the folder of this file. |
| 444 | `        src = f.read()` | `src`: the whole source text. |
| 445 | `    for fn, good, bad in MUTANTS[name]:` | Loops over the changes of the defect. |
| 446 | `        src = replace_in(src, fn, good, bad)` | Applies one change with `replace_in` (line 255). |
| 447 | `        if src is None:` | Tests whether the change could not be applied. |
| 448 | `            return None` | Returns `None`. The checks that use the defect then fail. So a text of the table that the source no longer holds is noticed. |
| 449 | `    return src` | Returns the changed text. |
| 452 | `def mutant_build(name, tag):` | Starts the function `mutant_build`. It compiles the runner with the defect `name`. `tag` is a short word for the folder name. |
| 453 | `    """builds the mutant in its own folder; returns the path of the binary, or None"""` | Description text: the defect copy is built in its own folder. The result is the path of the binary, or `None`. |
| 454 | `    d = os.path.join(E.tmp, "mutant-" + tag)` | `d`: the folder `mutant-` plus `tag` in the temporary folder. |
| 455 | `    os.makedirs(d, exist_ok=True)` | Creates the folder. No error when it exists. |
| 456 | `    src = mutant_source(name)` | `src`: the source text with the defect. |
| 457 | `    if src is None:` | Tests whether the defect could not be put in. |
| 458 | `        return None` | Returns `None`. |
| 459 | `    with open(os.path.join(d, "bwx10.c"), "w") as f:` | Opens the file `bwx10.c` in that folder for writing. |
| 460 | `        f.write(src)` | Writes the changed source text. |
| 461 | `    shutil.copy(os.path.join(HERE, "bwx10_selftest.c"), d)` | Copies `bwx10_selftest.c` into the folder. `bwx10.c` includes that file, so the compiler needs it there. |
| 462 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx10"), os.path.join(d, "bwx10.c")])` | Compiles the copy with `gcc` and the flags `CFLAGS` into the binary `bwx10` of that folder. |
| 463 | `    return os.path.join(d, "bwx10") if r.returncode == 0 else None` | Returns the path of the binary when `gcc` ended with exit status 0, and `None` if not. |

### Running the runner: `write_plan`, `run`, `trial`, `fnv1a64`, `plan_lines`, `GOOD` (lines 466 to 512)

| Line | Source | Explanation |
|---:|---|---|
| 466 | `# ---- running bwx10 ----` | Comment: the helpers that start `bwx10` follow. |
| 468 | `class Env:` | Starts the class `Env`. It has no content of its own. It only carries values. |
| 469 | `    pass` | The empty body of the class. |
| 472 | `E = Env()` | `E`: the one object of that class. `main` stores in it the settings that all tests share, such as the temporary folder (`E.tmp`), the path of the binary (`E.bin`) and the worker CPU (`E.cpu`). |
| 475 | `def write_plan(name, lines, cpu=None, nbytes=MIB8, head1=HEAD1, head3=HEAD3, head2=None):` | Starts the function `write_plan`. It writes a plan file with the trial lines `lines` and returns its path. A plan file lists the trials that the runner must run. The other arguments replace single header values, for the tests of bad plans. |
| 476 | `    cpu = E.cpu if cpu is None else cpu` | `cpu`: the worker CPU of the tests, unless the caller gave another one. |
| 477 | `    if head2 is None:` | Tests whether the caller gave no second header line. |
| 478 | `        head2 = "# step=T session=1 cpu=%d bytes=%d proc=0 seed=1 test=1" % (cpu, nbytes)` | `head2`: the standard second header line. It holds pairs of the form `key=value`: the step name `T`, session 1, the worker CPU, the buffer size in bytes, process 0, seed 1 and `test=1`. The runner requires that `cpu` and `bytes` equal its options. |
| 479 | `    path = os.path.join(E.tmp, name + ".plan")` | `path`: the file `name` with the ending `.plan` in the temporary folder. |
| 480 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 481 | `        f.write("\n".join([head1, head2, head3] + lines) + "\n")` | Writes the three header lines and the trial lines, each ended by a line break. |
| 482 | `    return path` | Returns the path. |
| 485 | `def run(args, env_add=None, binary=None):` | Starts the function `run`. It starts a binary with the arguments `args` and waits for its end. `env_add` holds added environment variables. `binary` is the program to start, when it is not the runner under test. |
| 486 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment of the test without every variable whose name starts with `BWX_`. So a counter setting in the environment of the caller cannot change a test. |
| 487 | `    env.update(env_add or {})` | Adds the variables of `env_add`, if any. |
| 488 | `    r = subprocess.run([binary or E.bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,` | Starts the binary (`E.bin` unless `binary` is given) and collects its standard output and its error output apart. |
| 489 | `                       universal_newlines=True, timeout=120)` | Continues the call of line 488: the outputs are returned as text. `timeout=120`: when the program runs longer than 120 s, the call ends with an error. |
| 490 | `    return r.returncode, r.stdout, r.stderr` | Returns three values: the exit status, the standard output and the error output. |
| 493 | `def trial(plan, extra=None, cpu=None, nbytes="8M", env_add=None):` | Starts the function `trial`. It runs the runner in the trial mode on one plan file. |
| 494 | `    return run(["--trial", "--cpus", str(E.cpu if cpu is None else cpu), "--bytes", nbytes, "--plan", plan] + (extra or []),` | Returns the result of `run`, called with `--trial`, `--cpus` and one CPU (the worker CPU of the tests unless `cpu` is given), `--bytes` and the buffer size (`8M` means 8 MiB), `--plan` and the path, and the added arguments of `extra`. |
| 495 | `               env_add)` | Continues the call of line 494: the added environment variables. |
| 498 | `def fnv1a64(data):` | Starts the function `fnv1a64`. It computes the FNV-1a hash of 64 bits over a sequence of bytes. The runner prints the same hash of its plan file. |
| 499 | `    h = 14695981039346656037` | `h`: the start value of that hash. |
| 500 | `    for b in data:` | Loops over the bytes. |
| 501 | `        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF` | One step: `h` is combined with the byte by exclusive or, multiplied by the constant 1099511628211 and cut to the low 64 bits. |
| 502 | `    return "%016x" % h` | Returns the hash as 16 hex digits. |
| 505 | `def plan_lines(path):` | Starts the function `plan_lines`. It reads the trial lines of a plan file. |
| 506 | `    with open(path) as f:` | Opens the plan file. |
| 507 | `        return [line.split(" ") for line in f.read().splitlines()[3:]]` | Returns the lines after the three header lines, each one split at single spaces into its 11 fields. |
| 510 | `GOOD = "0 a 1 - oldread@8M:8 - oldread@8M 1 5 closed 0"` | `GOOD`: a valid trial line that many tests use. Its fields: trial 0, the condition label `a`, repeat 1, no previous activity, a prefix of the old read kernel on 8 MiB for 8 ms (4 windows of 2 ms), no predecessor, the target `oldread` on 8 MiB, 1 target window of 5 ms, the count mode `closed` (no counters) and no bins. |

### `test_bad_plans`, checks a: a plan with a defect is refused (lines 513 to 568)

| Line | Source | Explanation |
|---:|---|---|
| 513 | `def test_bad_plans():` | Starts the test `test_bad_plans`. The names of its checks start with `a:`. |
| 514 | `    """(a) every defect gives status 2, a message, and no row"""` | Description text: every defect must give exit status 2, a message and no row. |
| 515 | `    rc, out, _ = trial(write_plan("good", [GOOD]))` | Runs the control: a plan that holds only the line `GOOD`. `rc` is the exit status. `out` is the standard output. |
| 516 | `    check("a: the good control plan runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the good plan runs with status 0 and prints the `E` row of trial 0. Without this control the next checks could pass for a wrong reason, for example with a runner that refuses every plan. |
| 518 | `    def bad(name, line=None, **kw):` | Starts the inner function `bad`. It runs one plan with a defect and checks the result. `line` is a bad trial line. `kw` holds header values to replace. |
| 519 | `        plan = write_plan("bad", [GOOD] if line is None else [GOOD.replace("0 a", "0 first"), line], **kw)` | Writes the plan. With a bad trial line: the good line with the label `first`, then the bad line as trial 1. Without one: the good line alone, under the changed header. |
| 520 | `        rc, out, err = trial(plan)` | Runs the plan in the trial mode. |
| 521 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. The design asks that a malformed plan fails before any work starts. The empty output proves that the runner printed no row. So no half result of a bad plan can reach the analysis. |
| 523 | `    t = "1 b 1 - oldread@8M:8 - %s 1 5 closed 0"` | `t`: a pattern for trial 1 in which only the target field changes. |
| 524 | `    bad("unknown kernel", t % "newread@8M")` | Bad plan: a target kernel with a name that the runner does not know. |
| 525 | `    bad("write kernel as target", t % "write@8M")` | Bad plan: a write kernel as the target. The trial mode accepts read kernels only. |
| 526 | `    bad("copy kernel as target", t % "copy@8M")` | Bad plan: a copy kernel as the target. |
| 527 | `    bad("write kernel as prefix", "1 b 1 - oldwrite@8M:8 - read@8M 1 5 closed 0")` | Bad plan: a write kernel, `oldwrite`, as the prefix. |
| 528 | `    bad("copy kernel as predecessor", "1 b 1 - - asmcopy@8M:8 read@8M 1 5 closed 0")` | Bad plan: a copy kernel, `asmcopy`, as the predecessor. |
| 529 | `    bad("size above --bytes", t % "read@16M")` | Bad plan: a target size of 16 MiB. That is above the buffer size of 8 MiB that `--bytes` gives. |
| 530 | `    bad("size not a multiple of 256", t % "read@1000")` | Bad plan: a size of 1000 bytes, which is no multiple of 256. The read kernels handle 256 bytes per loop pass. |
| 531 | `    bad("size 0", t % "read@0")` | Bad plan: a size of 0. |
| 532 | `    bad("size with a fraction", t % "read@1.5M")` | Bad plan: a size with a fraction, `1.5M`. |
| 533 | `    bad("target with a duration", t % "read@8M:5")` | Bad plan: a target with a duration, `read@8M:5`. The duration of the target windows comes from the field `win_ms`. |
| 534 | `    bad("prefix without a duration", "1 b 1 - oldread@8M - read@8M 1 5 closed 0")` | Bad plan: a prefix without a duration. |
| 535 | `    bad("pfx ms not a multiple of 4", "1 b 1 - oldread@8M:42 - read@8M 1 5 closed 0")` | Bad plan: a prefix duration of 42 ms, which is no multiple of 4. The runner records the prefix as 4 windows of equal requested length. |
| 536 | `    bad("pred ms 0", "1 b 1 - - read@8M:0 read@8M 1 5 closed 0")` | Bad plan: a predecessor duration of 0 ms. |
| 537 | `    bad("bad count word", "1 b 1 - - - read@8M 1 5 maybe 0")` | Bad plan: the count word `maybe`. Allowed are `closed`, `open` and `read`. |
| 538 | `    bad("bins 2", "1 b 1 - - - read@8M 1 5 closed 2")` | Bad plan: the bins value 2. Allowed are 0 and 1. |
| 539 | `    bad("nwin 0", "1 b 1 - - - read@8M 0 5 closed 0")` | Bad plan: 0 target windows. |
| 540 | `    bad("nwin 4097", "1 b 1 - - - read@8M 4097 5 closed 0")` | Bad plan: 4097 target windows. The limit is 4096. |
| 541 | `    bad("win_ms 0", "1 b 1 - - - read@8M 1 0 closed 0")` | Bad plan: a window duration of 0 ms. |
| 542 | `    bad("rep 5", "1 b 5 - - - read@8M 1 5 closed 0")` | Bad plan: the repeat number 5. Allowed are 1 to 4. |
| 543 | `    bad("trial number out of order", "2 b 1 - - - read@8M 1 5 closed 0")` | Bad plan: trial number 2 directly after trial 0. The trial numbers must be 0, 1, 2 and so on. |
| 544 | `    bad("10 fields", "1 b 1 - - - read@8M 1 5 closed")` | Bad plan: a trial line with 10 fields. It needs 11. |
| 545 | `    bad("12 fields", "1 b 1 - - - read@8M 1 5 closed 0 0")` | Bad plan: a trial line with 12 fields. |
| 546 | `    bad("two spaces between fields", "1 b 1 -  - - read@8M 1 5 closed 0")` | Bad plan: two spaces between two fields. |
| 547 | `    bad("comma in cond", "1 b,c 1 - - - read@8M 1 5 closed 0")` | Bad plan: a comma in the condition label. The label goes into an output row with comma-separated fields. A comma in it would shift the fields. |
| 548 | `    bad("empty line in the plan", "")` | Bad plan: an empty line in the plan. |
| 549 | `    # Record storage above the bound (design: "Bound its size"). The plan below needs 23.6 GB of bins. The address` | Comment: the next case is record storage above its bound. The design says of the storage for the output records: "Bound its size". By the comment the plan below needs 23.6 GB of bins. |
| 550 | `    # space limit keeps a runner without the bound from writing that much memory on this machine.` | Comment: the test limits the address space of the process. So a runner without the bound cannot write that much memory on the machine of the test. |
| 551 | `    plan = write_plan("bad", [GOOD.replace("0 a", "0 first"), "1 b 1 - - - oldread@8M 4096 3600000 closed 1"])` | Writes the plan: the good line, then a trial 1 with 4096 target windows of 3600000 ms (1 hour) each, with bins. One bin per 10 ms of all these windows needs far more than the bound of 256 MiB. |
| 552 | `    r = subprocess.run([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=subprocess.PIPE,` | Starts the runner on this plan directly, without the helper `run`. The test needs this to set a limit for the new process. |
| 553 | `                       stderr=subprocess.PIPE, universal_newlines=True, timeout=120,` | Continues the call of line 552: the outputs are collected as text, and the run may last 120 s at most. |
| 554 | `                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30)))` | Continues the call: `preexec_fn` runs in the new process before the runner starts. It limits the address space of the process to 4 GiB (`RLIMIT_AS`, as soft and as hard limit). |
| 555 | `    check("a: status 2, no row and a plan message that names line 5: record storage above the bound of 256 MiB",` | Check: the runner refuses the plan with status 2 and no row. Its message must start with `bad plan` and name the fifth text line of the plan file, which is the bad trial line. |
| 556 | `          r.returncode == 2 and r.stdout == "" and r.stderr.startswith("bad plan") and "line 5:" in r.stderr,` | Continues the check: the condition on the exit status, the standard output and the two parts of the message. |
| 557 | `          "rc=%s out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:160]))` | Continues the check: the detail that a failure prints. |
| 558 | `    bad("wrong header line 1", head1="# bwx8-plan v2")` | Bad plan: a first header line with `v2` in place of `v1`. |
| 559 | `    bad("wrong header line 3", head3=HEAD3.replace("win_ms count", "count win_ms"))` | Bad plan: a third header line in which the column names `win_ms` and `count` are exchanged. |
| 560 | `    bad("plan bytes differ from --bytes", head2="# step=T cpu=%d bytes=%d" % (E.cpu, MIB8 // 2))` | Bad plan: the header gives 4 MiB as `bytes`, and the option `--bytes` gives 8 MiB. A plan that was made for another buffer size must not run. |
| 561 | `    bad("plan cpu differs from --cpus", head2="# step=T cpu=%d bytes=%d" % (E.cpu2, MIB8))` | Bad plan: the header names another CPU (`E.cpu2`) than the option `--cpus`. A plan that was made for another CPU must not run. |
| 562 | `    bad("plan without bytes=", head2="# step=T cpu=%d" % E.cpu)` | Bad plan: a header without the pair `bytes=`. |
| 563 | `    bad("header pair without =", head2="# step cpu=%d bytes=%d" % (E.cpu, MIB8))` | Bad plan: a header word without `=`, the word `step`. |
| 564 | `    with open(os.path.join(E.tmp, "empty.plan"), "w") as f:` | Opens the file `empty.plan` in the temporary folder for writing. |
| 565 | `        f.write("\n".join([HEAD1, "# cpu=%d bytes=%d" % (E.cpu, MIB8), HEAD3]) + "\n")` | Writes the three header lines and no trial line. |
| 566 | `    rc, out, err = trial(os.path.join(E.tmp, "empty.plan"))` | Runs this plan in the trial mode. |
| 567 | `    check("a: status 2 and no row: plan without a trial", rc == 2 and out == "" and err.strip() != "", rc)` | Check: a plan without a trial gives status 2, no row and a message. |

### `test_bad_plans`, checks a: bad options are refused (lines 569 to 601)

| Line | Source | Explanation |
|---:|---|---|
| 569 | `    good = write_plan("good", [GOOD])` | `good`: a plan file with the line `GOOD`, for the checks of the options. |
| 571 | `    def bad_opt(name, args, env_add=None):` | Starts the inner function `bad_opt`. It starts the runner with the arguments `args` and checks that the runner refuses them. |
| 572 | `        rc, out, err = run(args, env_add)` | Runs the runner. |
| 573 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. |
| 575 | `    base = ["--trial", "--bytes", "8M", "--plan", good]` | `base`: the arguments of a valid trial run without `--cpus`. |
| 576 | `    bad_opt("worker CPU equal to the control CPU", base + ["--cpus", str(E.cpu), "--ctl-cpu", str(E.cpu)])` | Bad options: the worker CPU is also the CPU of the controlling thread (`--ctl-cpu`). The two threads would share one CPU, and the controlling thread could take time from the worker. |
| 577 | `    bad_opt("worker CPU equal to the default control CPU 0", ["--trial", "--bytes", "8M", "--cpus", "0", "--plan",` | Bad options: the worker CPU is CPU 0. That is the CPU of the controlling thread when `--ctl-cpu` is not given. |
| 578 | `                                                               write_plan("cpu0", [GOOD], cpu=0)])` | Continues the call of line 577: the plan is written for CPU 0, so only the CPU clash can be the reason of the refusal. |
| 579 | `    bad_opt("CPU above 119", ["--trial", "--bytes", "8M", "--cpus", "120", "--plan", write_plan("cpu120", [GOOD], cpu=120)])` | Bad options: CPU 120 as the worker CPU. The runner accepts the CPUs 0 to 119 only. |
| 580 | `    bad_opt("control CPU above 119", base + ["--cpus", str(E.cpu), "--ctl-cpu", "120"])` | Bad options: CPU 120 as the CPU of the controlling thread. |
| 581 | `    bad_opt("two CPUs", base + ["--cpus", "%d,%d" % (E.cpu, E.cpu2)])` | Bad options: two CPUs in `--cpus`. The trial mode has exactly one worker. |
| 582 | `    bad_opt("no --cpus", base)` | Bad options: no `--cpus`. |
| 583 | `    bad_opt("no --bytes", ["--trial", "--cpus", str(E.cpu), "--plan", good])` | Bad options: no `--bytes`. |
| 584 | `    bad_opt("no --plan", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M"])` | Bad options: no `--plan`. |
| 585 | `    bad_opt("plan file that does not exist", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good + ".none"])` | Bad options: a plan file that does not exist. |
| 586 | `    bad_opt("unknown option", base + ["--cpus", str(E.cpu), "--warmup"])` | Bad options: the unknown option `--warmup`. |
| 587 | `    bad_opt("--seq together with --trial", base + ["--cpus", str(E.cpu), "--seq", "read"])` | Bad options: `--seq` together with `--trial`. `--seq` belongs to the interval mode, the other mode of the runner. |
| 588 | `    if E.absent is not None:` | Tests whether a CPU from 0 to 119 exists that the test process may not use (`E.absent`). |
| 589 | `        bad_opt("worker CPU outside the allowed set of the process",` | Bad options: that CPU as the worker CPU. The runner must refuse a CPU outside the allowed set of the process before it starts any work. |
| 590 | `                ["--trial", "--bytes", "8M", "--cpus", str(E.absent), "--plan", write_plan("absent", [GOOD], cpu=E.absent)])` | Continues the call of line 589: the arguments, with a plan written for that CPU. |
| 591 | `    else:` | If no such CPU exists: |
| 592 | `        check("a: worker CPU outside the allowed set (no such CPU from 0 to 119 on this machine: NOT RUN)", False)` | Records a failed check whose name holds `NOT RUN`. So a case that this machine cannot test counts as a failure of the test file, and the output shows it. |
| 593 | `    counted = write_plan("counted", [GOOD, "1 b 1 - - - read@8M 1 5 open 0"])` | `counted`: a plan with the good line and a trial 1 with the count mode `open`. |
| 594 | `    bad_opt("count open without counter settings", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted])` | Bad options: a plan with a counted trial and no counter settings. |
| 595 | `    bad_opt("count open with a PMU type and no event",` | Bad options: a counted trial with a PMU type and no event list. The PMU type is the number by which Linux names a group of counters. |
| 596 | `            ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted, "--pmu-type", "1"])` | Continues the call of line 595: the arguments, with `--pmu-type 1`. |
| 597 | `    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted],` | Runs the same plan with the counter settings in the environment. |
| 598 | `                     {"BWX_PMU_TYPE": "1", "BWX_EVENTS": "task_clock=1"})` | Continues the call of line 597: `BWX_PMU_TYPE=1` and `BWX_EVENTS=task_clock=1`. |
| 599 | `    check("a: the same plan runs with the counter settings in the environment", rc == 0 and "\nE,1," in out, rc)` | Check: the plan now runs with status 0 and prints the `E` row of trial 1. So the runner also takes the counter settings from the environment. The two refusals before are proven to come from the missing settings. |

### `ALL` and `test_rows`: the rows of a plan with all phases (lines 602 to 671)

| Line | Source | Explanation |
|---:|---|---|
| 602 | `ALL = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 4 20 closed 0",` | `ALL`: the four trial lines of a short plan that uses every phase. Trial 0, label `A`: previous activity `asmread` on 8 MiB for 24 ms, prefix `oldread` on 8 MiB for 40 ms, predecessor `read` on 1 MiB for 20 ms, target `oldread` on 8 MiB with 4 windows of 20 ms, counters closed, no bins. |
| 603 | `       "1 B 1 - read@1M:40 - read@1M 4 20 closed 0",` | Trial 1, label `B`: a prefix of `read` on 1 MiB for 40 ms, then the target `read` on 1 MiB with 4 windows of 20 ms. |
| 604 | `       "2 C 1 - - - asmread@32K 3 25 closed 1",` | Trial 2, label `C`: no phase before the target. The target is `asmread` on 32 KiB with 3 windows of 25 ms, with bins. |
| 605 | `       "3 A 2 - oldread@8M:40 oldread@1M:20 read@8M 2 20 closed 1"]` | Trial 3, label `A`, repeat 2: prefix `oldread` on 8 MiB for 40 ms, predecessor `oldread` on 1 MiB for 20 ms, target `read` on 8 MiB with 2 windows of 20 ms, with bins. |
| 608 | `def test_rows():` | Starts the test `test_rows`. |
| 609 | `    """(b) (d) (e) (h) and the M, K, S, P rows of a short plan with all phases"""` | Description text: the checks named b, d, e and h, and the `M`, `K`, `S` and `P` rows, on a short plan with all phases. |
| 610 | `    plan = write_plan("all", ALL)` | Writes the plan `ALL` to a file. |
| 611 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)])` | Runs it in the trial mode, with the CPU `E.ctl` for the controlling thread. |
| 612 | `    if not check("b: the plan with all phases runs with status 0", rc == 0, err):` | Check: the run ends with status 0. On a failure the error output is printed. |
| 613 | `        return` | Ends the test on a failure. Every later check needs the rows of this run. |
| 614 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the four plan lines. |
| 615 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary from key to value. An `M` row is one line of settings, `M,key,value`. |
| 616 | `    need = ["mode", "cpu", "ctl_cpu", "bytes", "thp", "madvise_ok", "check_bytes", "kernels", "plan_fnv1a64", "ntrials",` | `need`: the keys that the output must hold: the mode, the worker CPU, the control CPU, the buffer size, the huge-page policy, the result of the page policy request, the bytes between two clock reads, the kind of the kernels, the hash of the plan, the number of trials ... |
| 617 | `            "rec_windows", "rec_bins", "rec_bytes", "trace", "pmu_type", "events"]` | Continues line 616: ... the sizes of the record storage (windows, bins, bytes), the trace switch, the PMU type and the events. |
| 618 | `    check("b: every required M key is present", all(k in m for k in need), [k for k in need if k not in m])` | Check: every required key is present. The analysis needs these settings to know under which conditions a rate was measured. |
| 619 | `    with open(plan, "rb") as f:` | Opens the plan file as bytes. |
| 620 | `        digest = fnv1a64(f.read())` | `digest`: the FNV-1a hash of these bytes, computed by the test (line 498). |
| 621 | `    check("b: M values", (m.get("mode"), m.get("cpu"), m.get("ctl_cpu"), m.get("bytes"), m.get("check_bytes"), m.get("ntrials"),` | Check of ten `M` values. This line and line 622 read them from the output. |
| 622 | `                          m.get("trace"), m.get("plan_fnv1a64"), m.get("kernels"), m.get("thp")) ==` | Continues the check: the last four values that are read, and the start of the comparison. |
| 623 | `          ("trial", str(E.cpu), str(E.ctl), str(MIB8), str(MIB8), "4", "0", digest, "STAND-IN", "madvise"), m)` | Continues the check: the expected values. The mode is `trial`. The two CPUs are those of the options. `bytes` and `check_bytes` are 8388608. The plan has 4 trials. The trace is off. `plan_fnv1a64` equals the hash that the test computed, so a result names exactly the plan that ran. `kernels` is `STAND-IN`: the build marks itself as not usable for rates. `thp` is `madvise`: huge pages were requested. |
| 624 | `    check("b: the plan pairs are copied to M,plan.<key> rows",` | Check: every pair of the second header line of the plan is copied to a row `M,plan.<key>,<value>`. |
| 625 | `          {k: v for k, v in m.items() if k.startswith("plan.")} ==` | Continues the check: the rows of the output whose key starts with `plan.`. |
| 626 | `          {"plan.step": "T", "plan.session": "1", "plan.cpu": str(E.cpu), "plan.bytes": str(MIB8), "plan.proc": "0",` | Continues the check: the expected pairs, the values that `write_plan` wrote (line 478). |
| 627 | `           "plan.seed": "1", "plan.test": "1"})` | Continues the check: the last two pairs. |
| 628 | `    nwin = sum(len(expected_windows(f)) for f in lines)` | `nwin`: the number of windows of all four trials together. |
| 629 | `    check("b: record storage is sized from the plan and its size is printed",` | Check: the storage for the records is sized from the plan, and its size is printed. |
| 630 | `          m.get("rec_windows") == str(nwin) and m.get("rec_bins") == str(3 * 4 + 2 * 4) and int(m.get("rec_bytes", 0)) > 0, m)` | Continues the check: `rec_windows` equals `nwin`. `rec_bins` is 20: room for 4 bins in each of the 3 windows of trial 2 and of the 2 windows of trial 3. `rec_bytes` is above 0. The design asks that this storage is allocated and first written before the first trial. So no trial spends time on the first use of a page. |
| 631 | `    k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. A `K` row holds a kernel name, the address of its function in hex and that address modulo 64. |
| 632 | `    check("b: one K row per kernel of the plan, with the address modulo 64",` | Check: one `K` row per kernel of the plan, with the address modulo 64. |
| 633 | `          sorted(k) == ["asmread", "oldread", "read"] and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are `asmread`, `oldread` and `read`, and in each row the last field is the hex address modulo 64. That value is the place of the function inside a 64-byte block of code. So each result names the code placement of its run. |
| 634 | `    s = rows.get("S", [])` | `s`: the `S` rows. An `S` row starts a trial. The runner prints it before the trial runs. |
| 635 | `    check("b: S rows hold the plan fields and the previous trial",` | Check: the `S` rows hold the plan fields and the previous trial. |
| 636 | `          [f[1:12] for f in s] == lines and [f[12:] for f in s] ==` | Continues the check: the fields 1 to 11 of each `S` row are the 11 fields of its plan line, and the last two fields are compared with the next line. |
| 637 | `          [["none", "none"], ["A", "oldread@8M"], ["B", "read@1M"], ["C", "asmread@32K"]], s)` | Continues the check: the label and the target of the trial before, and `none` twice for trial 0. The analysis can test with them whether the trial before changes a result. |
| 638 | `    check("b: one E row per S row", [f[1] for f in rows.get("E", [])] == [f[1] for f in s])` | Check: one `E` row per `S` row, with the same trial numbers. An `S` row without its `E` row would mean a trial that was interrupted. |
| 639 | `    check("b: P rows pre and post for every trial",` | Check: each trial has a `P` row `pre` and a `P` row `post`, in this order. |
| 640 | `          [(f[1], f[2]) for f in rows.get("P", [])] == [(str(i), w) for i in range(4) for w in ("pre", "post")] and` | Continues the check: the trial number and the word of each `P` row, against the expected list for the trials 0 to 3. |
| 641 | `          all(len(f) == 9 for f in rows["P"]))` | Continues the check: every `P` row has 9 fields. A `P` row holds the page state of the buffer: its size in kB, its part on huge pages in kB and four page counters of the whole system. |
| 642 | `    last = 0` | `last`: the end time of the trial before, 0 at the start. |
| 643 | `    for i, f in enumerate(lines):` | Loops over the four trials. `f` holds the plan fields of trial `i`. |
| 644 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 645 | `        p = window_problems(f, w)` | Applies the rule `window_problems` (line 101) to the trial. |
| 646 | `        check("b: trial %d: W rows complete, whole passes, 8 MiB rule, durations, monotonic times" % i, not p, p)` | Check b: no problem. The windows are complete, hold whole passes, keep the 8 MiB rule, last at least their requested time and have rising times. |
| 647 | `        check("b: trial %d: starts after the trial before it" % i, int(w[0][7]) >= last)` | Check b: the trial starts at or after the end of the trial before it. So the timed sequences of two trials do not overlap. |
| 648 | `        last = int(w[-1][8])` | Keeps the end time of the last window for the next trial. |
| 649 | `        p = e_problems(f, w, e)` | Applies the rule `e_problems` (line 122). |
| 650 | `        check("d: trial %d: wall_ns, gap_ns and max_boundary_gap_ns equal the W-row differences" % i, not p, p)` | Check d: `wall_ns`, `gap_ns` and `max_boundary_gap_ns` of the `E` row equal the differences of the `W` times. So the gap that the analysis reads is the measured time between the two clock reads. |
| 651 | `        p = bin_problems(f, w, of_trial(rows, "B", i))` | Applies the rule `bin_problems` (line 139). |
| 652 | `        check("e: trial %d: bins rise to the window end and their bytes sum to the window bytes" % i, not p, p)` | Check e: the bins rise to the window end, and their bytes sum to the bytes of the window. |
| 653 | `        check("b: trial %d: E row has 10 fields and count_state closed" % i, len(e) == 10 and e[9] == "closed", e)` | Check b: the `E` row has 10 fields, and its last field, the count state, is `closed`. The plan asked for no counters, and the row confirms that no counter group was open. |
| 654 | `        wall, cpu = int(e[2]), int(e[3])` | `wall`, `cpu`: the wall time and the CPU time of the timed sequence in ns (fields 2 and 3 of the `E` row). |
| 655 | `        check("b: trial %d: cpu_ns is CPU time: not the wall time, at least half of it, at most 1 ms above it" % i,` | Check b: `cpu_ns` is a CPU time and no copy of the wall time. |
| 656 | `              cpu != wall and wall // 2 <= cpu <= wall + 1000000, e)` | Continues the check: it differs from the wall time, is at least half of it and at most 1 ms (1000000 ns) above it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. So the field must hold a separate measurement. |
| 657 | `        pre, post = of_trial(rows, "P", i)` | `pre`, `post`: the two `P` rows of the trial. |
| 658 | `        check("b: trial %d: both P rows hold 8192 kB for the 8 MiB buffer and a number in every field" % i,` | Check b: both `P` rows hold 8192 kB, the size of the 8 MiB buffer, and a number in every later field. |
| 659 | `              pre[3] == post[3] == "8192" and all(v.isdigit() for v in pre[3:] + post[3:]), (pre, post))` | Continues the check: the condition and the detail. A number in the huge-page field shows that the runner could read the page state of the buffer. |
| 660 | `    e = rows["E"]` | `e`: all `E` rows of the run. |
| 661 | `    check("h: sink_ok is 1 for the trials that ran old read", [f[8] for f in e] == ["1", "NA", "NA", "1"], [f[8] for f in e])` | Check h: `sink_ok` (field 8) is `1` for the trials 0 and 3, which ran the old read kernel, and `NA` for the two others. The old read kernel returns the sum of the words that it read. The runner compares the last sum with the expected value. A `1` shows that the result of the old read kernel was used and was right. |
| 662 | `    check("d: gap_ns is NA for the trial whose target has no window before it", e[2][6] == "NA", e[2])` | Check d: `gap_ns` is `NA` for trial 2, whose target has no window before it. A gap that does not exist is not printed as 0. |
| 663 | `    # One pass over 8 MiB takes more than 20 us with the stand-in kernels, so a warm-up pass in the gap fails here.` | Comment: with the stand-in kernels one pass over 8 MiB takes more than 20 us. So a warm-up pass inside the gap makes the next check fail. |
| 664 | `    check("d: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",` | Check d: the gap before an 8 MiB target is below 20 us in trial 0 or in trial 3. So no kernel pass lies inside the gap. |
| 665 | `          min(int(e[0][6]), int(e[3][6])) < 20000, (e[0][6], e[3][6]))` | Continues the check: the smaller of the two gaps must be below 20000 ns. One long gap alone does not fail the check. |
| 666 | `    check("b: the 1 MiB windows hold a multiple of 8 MiB",` | Check b: every window with a pass size of 1 MiB holds a multiple of 8 MiB. The runner reads the clock after 8 passes of 1 MiB. |
| 667 | `          all(int(w[6]) % MIB8 == 0 for w in rows["W"] if w[5] == str(1 << 20)) and` | Continues the check: the condition on all `W` rows with a pass size of 1048576 bytes. |
| 668 | `          any(w[5] == str(1 << 20) for w in rows["W"]))` | Continues the check: at least one such row must exist. If none existed, the condition before would hold without testing anything. |
| 669 | `    check("b: no X row, no C row and no TR row in this run", not rows.get("X") and not rows.get("C") and not rows.get("TR"),` | Check b: this run printed no `X` row (no reported failure), no `C` row (no counters) and no `TR` row (no trace). |
| 670 | `          rows.get("X"))` | Continues the check: the detail that a failure prints. |

### `test_rows`: each rule must fail on changed rows (lines 672 to 701)

| Line | Source | Explanation |
|---:|---|---|
| 672 | `    # every rule must report a problem on changed rows` | Comment: every rule must report a problem on rows that were changed. This proves that the rule can fail. |
| 673 | `    f0, w0, e0 = lines[0], of_trial(rows, "W", 0), of_trial(rows, "E", 0)[0]` | `f0`, `w0`, `e0`: the plan fields, the `W` rows and the `E` row of trial 0. Trial 0 has 10 windows: row 0 is the previous activity, rows 1 to 4 are the prefix, row 5 is the predecessor and rows 6 to 9 are the target. |
| 675 | `    def changed(row_index, field, value):` | Starts the inner function `changed`. It returns a copy of the `W` rows of trial 0 in which one field of one row has a new value. |
| 676 | `        w = [list(x) for x in w0]` | Copies the rows. |
| 677 | `        w[row_index][field] = str(value)` | Sets the field. |
| 678 | `        return w` | Returns the changed rows. |
| 680 | `    check("b: the rule fails on a lost W row", window_problems(f0, w0[:-1]))` | Check: `window_problems` reports a problem when the last `W` row is lost. In the checks of this part the list of problems is the result itself: a list that is not empty counts as passed. |
| 681 | `    check("b: the rule fails on a byte count that is not whole passes", window_problems(f0, changed(2, 6, int(w0[2][6]) + 64)))` | Check: the rule fails on a byte count that is no whole number of passes: prefix window 1 with 64 bytes added. |
| 682 | `    check("b: the rule fails on 0 bytes", window_problems(f0, changed(2, 6, 0)))` | Check: the rule fails on a window with 0 bytes. |
| 683 | `    check("b: the rule fails on a 1 MiB window with 9 MiB", window_problems(f0, changed(5, 6, 9 << 20)))` | Check: the rule fails on the 1 MiB predecessor window with 9 MiB. That is whole passes, but no multiple of 8 MiB. |
| 684 | `    check("b: the rule fails on a window shorter than requested", window_problems(f0, changed(6, 8, int(w0[6][7]) + 19999999)))` | Check: the rule fails on a target window that ends 19999999 ns after its start. That is 1 ns less than the requested 20 ms. |
| 685 | `    check("b: the rule fails on a start before the end of the window before", window_problems(f0, changed(6, 7, int(w0[5][8]) - 1)))` | Check: the rule fails on a target window that starts 1 ns before the end of the predecessor window. |
| 686 | `    check("b: the rule fails on a wrong kernel in a window", window_problems(f0, changed(5, 4, "asmread")))` | Check: the rule fails on a wrong kernel name in the predecessor window. |
| 687 | `    e_bad = list(e0)` | `e_bad`: a copy of the `E` row of trial 0. |
| 688 | `    e_bad[6] = str(int(e0[6]) + 1)` | Adds 1 ns to its `gap_ns`. |
| 689 | `    check("d: the rule fails on a gap_ns that differs from the W rows by 1 ns", e_problems(f0, w0, e_bad))` | Check: `e_problems` fails on a `gap_ns` that differs from the `W` rows by 1 ns. |
| 690 | `    e_bad = list(e0)` | `e_bad`: a fresh copy of the `E` row. |
| 691 | `    e_bad[6] = "0"` | Sets its `gap_ns` to 0. |
| 692 | `    check("d: the rule fails on a gap_ns of 0", int(e0[6]) > 0 and e_problems(f0, w0, e_bad), e0)` | Check: the real gap is above 0, and the rule fails on a gap of 0. So the runner measures the gap and does not assume that it is zero. |
| 693 | `    f2, w2, b2 = lines[2], of_trial(rows, "W", 2), of_trial(rows, "B", 2)` | `f2`, `w2`, `b2`: the plan fields, the `W` rows and the `B` rows of trial 2. That trial has bins and a pass size of 32 KiB. |
| 694 | `    b_bad = [list(x) for x in b2]` | `b_bad`: a copy of the `B` rows. |
| 695 | `    b_bad[-1][5] = str(int(b_bad[-1][5]) - (32 << 10))` | Takes 32 KiB, one pass, from the byte count of the last bin. |
| 696 | `    check("e: the rule fails when the bins do not sum to the window bytes", bin_problems(f2, w2, b_bad))` | Check: `bin_problems` fails when the bins do not sum to the bytes of the window. |
| 697 | `    check("e: the rule fails when the last bin is lost", bin_problems(f2, w2, b2[:-1]))` | Check: the rule fails when the last bin is lost. The bins then do not reach the window end. |
| 698 | `    check("e: the rule fails on B rows in a trial without bins", bin_problems(lines[1], of_trial(rows, "W", 1), b2))` | Check: the rule fails on `B` rows in trial 1, which has no bins. |
| 699 | `    check("e: a 25 ms window has 1 to 3 bins", all(1 <= len([b for b in b2 if b[2] == str(i)]) <= 3 for i in range(3)), b2)` | Check: each of the 3 windows of 25 ms has 1 to 3 bins. The requested bin width is 10 ms, so such a window can close 3 bins at most. |

### `test_sequence_code`, checks c: the timed sequence in source and machine code (lines 702 to 732)

| Line | Source | Explanation |
|---:|---|---|
| 702 | `def test_sequence_code():` | Starts the test `test_sequence_code`. |
| 703 | `    """(c) the timed sequence in the source and in the machine code, without the trace; both functions"""` | Description text: the checks named c. They read the timed sequence from the source and from the machine code, without the trace, for both timed functions. |
| 704 | `    with open(os.path.join(HERE, "bwx10.c")) as f:` | Opens `bwx10.c` in the folder of this file. |
| 705 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 706 | `    p = seq_source_problems(src)` | Applies the rule `seq_source_problems` to it. |
| 707 | `    check("c: source: timed_sequence() and timed_sequence_hot() hold 2 clock reads, 1 kernel call, 2 counter reads and "` | Check: in the source, `timed_sequence()` and `timed_sequence_hot()` hold 2 clock reads, 1 kernel call, 2 counter reads ... |
| 708 | `          "no other call", not p, p)` | Continues the check: ... and no other call. So the text of the timed loop holds nothing that could add time between two clock reads, such as an output or a page read. |
| 709 | `    for name in SEQ_MUTANTS + HOT_SEQ_MUTANTS:` | Loops over the six defects of the two timed functions. |
| 710 | `        m = mutant_source(name)` | `m`: the source text of the runner with the defect `name`. |
| 711 | `        check("c: the source rule fails on a build with " + name, m is not None and seq_source_problems(m))` | Check: the defect could be put in, and the source rule reports a problem on that text. So the rule is proven to find this defect. |
| 712 | `    p = hot_source_problems(src)` | Applies the rule `hot_source_problems` (line 264) to the source. |
| 713 | `    check("c: source: the window loop of timed_sequence_hot() names no field of the window record", not p, p)` | Check: the window loop of `timed_sequence_hot()` names no field of the window record. With `--hot-copy` the loop then cannot read or write that record between the first and the last pass of a window. |
| 714 | `    m = mutant_source(HOT_READ_MUTANT)` | `m`: the source in which the loop reads the pass count from the window record after every pass. |
| 715 | `    check("c: that rule fails on a source where " + HOT_READ_MUTANT, m is not None and hot_source_problems(m))` | Check: the rule fails on that source. |
| 716 | `    for fn in SEQ_FUNCTIONS:` | Loops over the two timed functions. |
| 717 | `        t = seq_targets(E.bin, fn)` | `t`: the branch targets of the function in the machine code of the binary under test. |
| 718 | `        p = seq_code_problems(t, fn)` | Applies the rule `seq_code_problems` to them. |
| 719 | `        check("c: machine code: %s reaches only clock_gettime, the kernels, tcount and the stack-guard failure" % fn,` | Check: in the machine code the function reaches only `clock_gettime`, the kernels, `tcount` and the function for a failed stack guard. This is the proof on the code that really runs: the compiler could have added or kept a call that the source does not show. |
| 720 | `              not p, (p, t))` | Continues the check: the result and the detail. |
| 721 | `        check("c: the machine-code rule fails on a call of fflush (%s)" % fn, seq_code_problems(dict(t, fflush=1), fn))` | Check: the rule fails when a call of `fflush` is added to the targets. `fflush` writes buffered output. |
| 722 | `        check("c: the machine-code rule fails on a helper that is not inlined (%s)" % fn, seq_code_problems(dict(t, tclock=2), fn))` | Check: the rule fails when `tclock` stands among the targets. That is the case when the compiler did not put the clock helper inline. |
| 723 | `        check("c: the machine-code rule fails when the function has no kernel call (%s)" % fn,` | Check: the rule fails when the function has no kernel call. |
| 724 | `              seq_code_problems({k: v for k, v in t.items() if k != "(indirect)"}, fn))` | Continues the check: the targets without the entry `(indirect)`. |
| 725 | `    for fn, name, tag in (("timed_sequence", SEQ_MUTANTS[1], "seq"), ("timed_sequence_hot", HOT_SEQ_MUTANTS[1], "seqhot")):` | Loops over two cases: `timed_sequence` with its page-read defect, and `timed_sequence_hot` with its page-read defect. `tag` names the build folder. |
| 726 | `        b = mutant_build(name, tag)` | `b`: the binary of the runner with that defect (line 452). |
| 727 | `        other = [f for f in SEQ_FUNCTIONS if f != fn][0]` | `other`: the timed function that has no defect in this build. |
| 728 | `        check("c: the machine-code rule fails for %s on a real build with %s, and passes for %s" % (fn, name, other),` | Check: on a real build with the defect the machine-code rule fails for the function with the defect and passes for the other one. |
| 729 | `              b is not None and any("read_vmstat" in x or "fflush" in x for x in seq_code_problems(seq_targets(b, fn), fn)) and` | Continues the check: the build worked, and a problem of the function names `read_vmstat` or `fflush`, the two calls that the defect added ... |
| 730 | `              not seq_code_problems(seq_targets(b, other), other), b and seq_targets(b, fn))` | Continues the check: ... and the other function has no problem. So the rule finds a real forbidden call in the compiled code, and it names the right function. |

### `test_disturbed`, checks i: the values that mark a disturbed trial (lines 733 to 749)

| Line | Source | Explanation |
|---:|---|---|
| 733 | `def test_disturbed():` | Starts the test `test_disturbed`. |
| 734 | `    """(i) the values that mark a disturbed trial, from a trial that shares its CPU with another process"""` | Description text: the checks named i. They read the values that mark a disturbed trial from a trial that shares its CPU with another process. |
| 735 | `    plan = write_plan("shared", ["0 a 1 - oldread@8M:200 - oldread@8M 2 100 closed 0"])` | Writes a plan with one trial: a prefix of `oldread` on 8 MiB for 200 ms and 2 target windows of 100 ms. |
| 736 | `    spin = subprocess.Popen([sys.executable, "-c", "import os\nos.sched_setaffinity(0, {%d})\nwhile True:\n    pass" % E.cpu])` | Starts a second Python process. It pins itself to the worker CPU and then runs an endless loop. So it competes with the worker for that CPU. |
| 737 | `    try:` | Starts a block whose end (line 740) always runs. |
| 738 | `        time.sleep(0.5)  # the other process now runs on the worker CPU` | Waits 0.5 s. By the comment the other process then runs on the worker CPU. |
| 739 | `        rc, out, err = trial(plan)` | Runs the trial. |
| 740 | `    finally:` | The next two lines run also when the trial raised an error. |
| 741 | `        spin.kill()` | Ends the other process with the kill signal. |
| 742 | `        spin.wait()` | Waits until it has ended. |
| 743 | `    e = rows_of(out).get("E", [[]])[0]` | `e`: the `E` row of the trial, or an empty list when the output has none. |
| 744 | `    if not check("i: the trial on a shared CPU ends with status 0 and an E row", rc == 0 and len(e) == 10, err):` | Check: the trial on the shared CPU still ends with status 0 and an `E` row of 10 fields. |
| 745 | `        return` | Ends the test when that check failed. |
| 746 | `    check("i: shared CPU: cpu_ns is below 0.9 x wall_ns", int(e[3]) < 0.9 * int(e[2]), e)` | Check: `cpu_ns` is below 0.9 times `wall_ns`. The worker got only a part of the CPU, and the row shows it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. |
| 747 | `    check("i: shared CPU: nivcsw (involuntary) is above 0 and nvcsw (voluntary) is 0", int(e[5]) > 0 and e[4] == "0", e)` | Check: `nivcsw`, the count of involuntary context switches (field 5), is above 0, and `nvcsw`, the count of voluntary ones (field 4), is 0. Linux took the CPU away from the worker, and the worker never gave it up by itself. A rise of the involuntary count is the second mark of a disturbed trial in the design. |

### `test_placement`, checks j: pin before allocation, and a failed `madvise` (lines 750 to 784)

| Line | Source | Explanation |
|---:|---|---|
| 750 | `def test_placement():` | Starts the test `test_placement`. |
| 751 | `    """(j) pin before allocation, the CPU of the controlling thread, and the X row of a failed madvise"""` | Description text: the checks named j. They cover the pin before the allocation, the CPU of the controlling thread, and the `X` row of a failed `madvise`. |
| 752 | `    d = os.path.join(E.tmp, "shim")` | `d`: the folder `shim` in the temporary folder. |
| 753 | `    os.makedirs(d)` | Creates the folder. |
| 754 | `    with open(os.path.join(d, "shim.c"), "w") as f:` | Opens the file `shim.c` in it for writing. |
| 755 | `        f.write(SHIM)` | Writes the C text `SHIM` (line 354). |
| 756 | `    so = os.path.join(d, "shim.so")` | `so`: the path of the library file `shim.so`. |
| 757 | `    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,` | Compiles the C text with `gcc` into a shared library. `-shared` makes a library that a program can load at its start. `-fPIC` makes code that works at any address. `-O1` is a low optimization level. |
| 758 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call of line 757: the messages of the compiler are collected as one text. |
| 759 | `    if not check("j: the library that logs sched_setaffinity and mmap builds", r.returncode == 0, r.stdout):` | Check j: the library builds. On a failure the compiler messages are printed. |
| 760 | `        return` | Ends the test when the library did not build. |
| 761 | `    plan = write_plan("place", [GOOD])` | Writes a plan with the line `GOOD`. |
| 762 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)], env_add={"LD_PRELOAD": so})` | Runs it with the control CPU `E.ctl` and with `LD_PRELOAD` set to the library. Linux then loads the library before the C library. So the runner calls the `sched_setaffinity`, `mmap` and `madvise` of the library, and each call is logged. |
| 763 | `    lines = [x for x in err.splitlines() if x.startswith("shim ")]` | `lines`: the log lines of the library in the error output. Each one starts with `shim`. |
| 764 | `    p = placement_problems(lines, E.cpu, E.ctl) if rc == 0 and lines else ["rc=%s, %d lines" % (rc, len(lines))]` | Applies the rule `placement_problems` (line 327) when the run ended with status 0 and logged lines. If not, the status and the number of lines are the problem. |
| 765 | `    check("j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself "` | Check j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself ... |
| 766 | `          "before it maps the buffer", not p, (p, lines))` | Continues the check: ... before it maps the buffer. Linux assigns the pages of a buffer at the first touch. A worker that maps and writes its buffer before the pin could do so while it runs on another CPU. |
| 767 | `    if not p:` | Only when the rule passed: the next three checks show that the rule can fail. |
| 768 | `        w = [i for i, x in enumerate(lines) if x.split()[3] != "tid=" + x.split()[2][4:]]` | `w`: the positions of the log lines of the worker thread. These are the lines whose thread id differs from the process id. |
| 769 | `        late = lines[:w[0]] + [lines[w[1]], lines[w[0]]] + lines[w[1] + 1:]` | `late`: the log with the first two logged calls of the worker exchanged. The worker then maps memory before its pin. |
| 770 | `        check("j: the rule fails when the worker maps the buffer before its pin", placement_problems(late, E.cpu, E.ctl))` | Check: the rule fails on that log. |
| 771 | `        no_ctl = [x for x in lines if not x.endswith(" 1 %d" % E.ctl)]` | `no_ctl`: the log without the lines that end with a set of 1 CPU whose first CPU is the control CPU. These are the pins to the control CPU. |
| 772 | `        check("j: the rule fails when the controlling thread does not pin itself", placement_problems(no_ctl, E.cpu, E.ctl))` | Check: the rule fails when the controlling thread does not pin itself. |
| 773 | `        check("j: the rule fails when the worker pins itself to another CPU", placement_problems(lines, E.ctl, E.ctl))` | Check: the rule fails when it is asked for another worker CPU (`E.ctl`) than the one in the log. So a worker on a wrong CPU would be found. |
| 774 | `    rows = rows_of(out)` | `rows`: the output of the first run, sorted by row type. |
| 775 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 776 | `    check("j: madvise that works: M,madvise_ok,1 and no X row", m.get("madvise_ok") == "1" and not rows.get("X"), rows.get("X"))` | Check j: with a working `madvise` the row `M,madvise_ok` holds `1`, and no `X` row is printed. |
| 777 | `    rc, out, err = trial(plan, env_add={"LD_PRELOAD": so, "SHIM_MADVISE_FAIL": "1"})` | Runs the plan again with the variable `SHIM_MADVISE_FAIL` set. The library then lets every `madvise` call of the runner fail (line 386). |
| 778 | `    rows = rows_of(out)` | `rows`: the output of this run, sorted by row type. |
| 779 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 780 | `    check("j: madvise that fails: status 0, M,madvise_ok,0, the row X,-1,madvise, and the trial still runs",` | Check j: a failed page policy request is reported, and the run continues. The exit status is 0, the row `M,madvise_ok` holds `0`, the only `X` row is `X,-1,madvise`, ... |
| 781 | `          rc == 0 and m.get("madvise_ok") == "0" and [f[1:3] for f in rows.get("X", [])] == [["-1", "madvise"]] and` | Continues the check: the three conditions on the exit status, the `M` row and the `X` rows. |
| 782 | `          len(rows.get("E", [])) == 1, (rc, m.get("madvise_ok"), rows.get("X")))` | Continues the check: ... and one `E` row exists, so the trial still ran. The design says that a failed page-policy request is a reported failure and not an assumed success. A result without the requested huge pages is then marked in its own output. |

### `events_of` and `test_trace`, checks c: the trace of closed, open and read trials (lines 785 to 838)

| Line | Source | Explanation |
|---:|---|---|
| 785 | `def events_of(rows, trial_no):` | Starts the function `events_of`. It reads the trace of one trial from the `TR` rows. A `TR` row holds the trial number, the event number, the event name and a time in ns. |
| 786 | `    tr = of_trial(rows, "TR", trial_no)` | `tr`: the `TR` rows of the trial. |
| 787 | `    ok = [int(f[2]) for f in tr] == list(range(len(tr)))` | `ok`: true when the event numbers (field 2) are 0, 1, 2 and so on. |
| 788 | `    return [(f[3], int(f[4])) for f in tr], ok` | Returns the list of pairs of event name and time, and `ok`. |
| 791 | `def test_trace():` | Starts the test `test_trace`. |
| 792 | `    """(c) the trace of closed, open and read trials, and the trace rule on broken traces"""` | Description text: the checks named c on the trace of trials with the count modes `closed`, `open` and `read`, and the trace rule on broken traces. |
| 793 | `    plan = write_plan("trace", ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",` | Writes a plan of 5 trials. Trial 0, label `A`: all phases, the target `oldread` on 8 MiB with 3 windows of 20 ms, counters closed, with bins. |
| 794 | `                                "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",` | Trial 1, label `B`: a prefix, a predecessor and 3 target windows of `read`, with the count mode `read`. In this mode the counter group is open, and the runner reads it at the boundaries of the target windows. |
| 795 | `                                "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",` | Trial 2, label `C`: a prefix and 2 target windows of `asmread`, with the count mode `open`. The counter group is open but is not read. |
| 796 | `                                "3 D 1 - - - read@8M 2 20 read 0",` | Trial 3, label `D`: only 2 target windows of `read`, with the count mode `read`. |
| 797 | `                                "4 E 1 - - - oldread@8M 2 20 closed 0"])` | Trial 4, label `E`: only 2 target windows of `oldread`, counters closed. |
| 798 | `    rc, out, err = trial(plan, ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with `--trace`, the PMU type 1 and the events `task_clock` (code 1) and `cpu_clock` (code 0). By the check of line 804, PMU type 1 means the software events of Linux. With `--trace` the runner logs the events of its wrapper functions and prints them as `TR` rows. The design calls this the non-measuring test: the rates of a trace run are not used. |
| 799 | `    if not check("c: the trace run ends with status 0", rc == 0, err):` | Check c: the trace run ends with status 0. |
| 800 | `        return` | Ends the test when the run failed. |
| 801 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the plan lines. |
| 802 | `    states = [f[9] for f in rows["E"]]` | `states`: the count state of each trial, the last field of its `E` row. |
| 803 | `    E.soft_counters = states == ["closed", "read", "open", "read", "closed"]` | `E.soft_counters`: true when the states are `closed`, `read`, `open`, `read`, `closed`, as the plan asks. The software events then opened on this machine. Later tests read this value. |
| 804 | `    check("c: the software events of Linux (PMU type 1) open on this machine", E.soft_counters, (states, rows.get("X")))` | Check c: the software events of Linux (PMU type 1) open on this machine. On a failure the states and the `X` rows are printed. |
| 805 | `    saved = None` | `saved`: will hold the data of trial 0, for the checks on broken traces. |
| 806 | `    for i, f in enumerate(lines):` | Loops over the trials. `f` holds the plan fields of trial `i`. |
| 807 | `        ev, numbered = events_of(rows, i)` | `ev`: the events of the trial. `numbered`: whether its `TR` rows are numbered without a hole. |
| 808 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 809 | `        p = trace_problems(f, ev, w, e)` | Applies the rule `trace_problems` (line 170). |
| 810 | `        check("c: trial %d (count %s): TR rows are numbered 0, 1, 2, ..." % (i, f[9]), numbered and len(ev) > 0)` | Check c: the `TR` rows of the trial are numbered 0, 1, 2 and so on, and at least one exists. A lost event row would show as a hole in the numbers. |
| 811 | `        check("c: trial %d (count %s): no forbidden event in the timed sequence, and the W rows and gap_ns "` | Check c: no forbidden event lies in the timed sequence, and the times of the `W` rows and `gap_ns` ... |
| 812 | `              "are clock reads of the trace" % (i, f[9]), not p, p)` | Continues the check: ... are clock reads of the trace. By the design a warm-up pass, a page read, an output flush or a counter read must not enter the path from the predecessor to the target, and the recorded gap must hold all the work of the runner between the two kernels. This check proves both on the real call path. |
| 813 | `        names = [n for n, _ in ev]` | `names`: the event names of the trial. |
| 814 | `        want_reads = int(f[7]) + 1 if f[9] == "read" and E.soft_counters else 0` | `want_reads`: the expected number of counter reads. In a trial with the count mode `read`, when the events opened, it is the number of target windows plus 1. In every other trial it is 0. |
| 815 | `        check("c: trial %d (count %s): %d counter reads" % (i, f[9], want_reads), names.count("count_read") == want_reads,` | Check c: the trace holds exactly that many counter reads. That is one reading at each boundary of a target window and none inside a window. |
| 816 | `              names.count("count_read"))` | Continues the check: the number found, as the detail. |
| 817 | `        check("c: trial %d: 2 page reads and 2 outputs, all outside the timed sequence" % i,` | Check c: each trial has 2 page reads and 2 outputs. |
| 818 | `              names.count("page_read") == 2 and names.count("output") == 2)` | Continues the check: the two counts. The trace rule of line 811 has shown that they lie outside the timed sequence. |
| 819 | `        if i == 0:` | For trial 0 only: |
| 820 | `            saved = (f, ev, w, e)` | Keeps the data of trial 0. |
| 821 | `            times = {t for n, t in ev if n == "clock"}` | `times`: the set of the times of all clock reads of the trace. |
| 822 | `            p = bin_problems(f, w, of_trial(rows, "B", 0), times)` | Applies `bin_problems` (line 139) with these times. |
| 823 | `            check("e: every bin end of the trace run is a clock read of the trace", not p, p)` | Check e: every bin end of this run is a clock read of the trace. So the bins add no clock read to the timed loop. |
| 824 | `            b_bad = [list(x) for x in of_trial(rows, "B", 0)]` | `b_bad`: a copy of the `B` rows of trial 0. |
| 825 | `            b_bad[0][4] = str(int(b_bad[0][4]) + 1)` | Adds 1 ns to the end time of its first bin. |
| 826 | `            check("e: the rule fails on a bin end that is no clock read", bin_problems(f, w, b_bad, times))` | Check e: the rule fails on a bin end that is no clock read. |
| 827 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)` | `faults`: the pairs of trial number and count from the comment lines `# minflt,<trial>,<count>` of the output. With `--trace` the runner prints there the minor page faults of the worker between its two reads of the thread statistics, before and after the timed sequence. A minor page fault happens when a thread uses a page that Linux has not yet assigned to it. The pattern matches a whole line: group 1 is the trial number, group 2 the count, which may be negative. |
| 828 | `    check("c: no minor page fault of the worker between the two rusage reads of any trial (records and buffer were "` | Check c: no minor page fault of the worker in the timed sequence of any trial. The records and the buffer were first touched before ... |
| 829 | `          "first touched before)", faults == [(str(i), "0") for i in range(5)], faults)` | Continues the check: the list must hold the trials 0 to 4, each with the count 0. So no window holds the time of the first use of a page. |
| 830 | `    b = mutant_build(TOUCH_MUTANT, "touch")` | `b`: a build of the runner whose record storage is not written before the first trial (line 421). |
| 831 | `    out_m = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--trace", "--pmu-type", "1", "--events",` | Runs the same trace plan with that build and takes its standard output. |
| 832 | `                 "task_clock=1,cpu_clock=0"], binary=b)[1] if b else ""` | Continues the call of line 831: the event list and the binary. Without a build the output is an empty text. |
| 833 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out_m, re.M)` | `faults`: the fault lines of that output. |
| 834 | `    check("c: that check fails on a build with " + TOUCH_MUTANT, len(faults) == 5 and any(int(n) > 0 for _, n in faults), faults)` | Check c: the fault check fails on that build: 5 lines, and at least one count above 0. So the check is proven to find a first touch inside a timed sequence. |
| 835 | `    opens = [[n for n, _ in events_of(rows, i)[0] if n in ("count_open", "count_close")] for i in range(5)]` | `opens`: for each of the 5 trials, its events `count_open` and `count_close` in order. |
| 836 | `    check("c: the group opens before the first counted trial and closes before the next closed trial",` | Check c: the counter group opens before the first counted trial and closes before the next closed trial. |
| 837 | `          opens == [[], ["count_open"], [], [], ["count_close"]], opens)` | Continues the check: trial 1 has one open, trial 4 has one close, the other trials have none. So the group stays open over the trials 1 to 3. A counted trial that follows a counted trial does not open the group again. |

### `test_trace`: the trace rule must fail on broken traces (lines 839 to 876)

| Line | Source | Explanation |
|---:|---|---|
| 839 | `    # the rule on broken traces of trial 0 (closed, all phases)` | Comment: the next checks apply the rule to broken copies of the trace of trial 0, the closed trial with all phases. |
| 840 | `    f, ev, w, e = saved` | `f`, `ev`, `w`, `e`: the saved data of trial 0. |
| 841 | `    names = [n for n, _ in ev]` | `names`: its event names. |
| 842 | `    tgt0 = names.index("kernel_first:target:0")` | `tgt0`: the position of the first kernel call of target window 0. |
| 843 | `    tgt1 = names.index("kernel_first:target:1")` | `tgt1`: the position of the first kernel call of target window 1. |
| 844 | `    pred = names.index("kernel_first:pred:0")` | `pred`: the position of the first kernel call of the predecessor window. |
| 846 | `    def broken(at, name):` | Starts the inner function `broken`. It returns a copy of the trace with one more event, `name`, before the position `at`. |
| 847 | `        return ev[:at] + [(name, ev[at - 1][1])] + ev[at:]` | Returns the events before `at`, then the new event with the time of the event before it, then the events from `at` on. |
| 849 | `    check("c: the rule passes on the unchanged trace", not trace_problems(f, ev, w, e))` | Check c: the rule passes on the unchanged trace. |
| 850 | `    check("c: the rule fails on a page read between predecessor and target", trace_problems(f, broken(tgt0 - 1, "page_read"), w, e))` | Check: the rule fails on a page read between the predecessor and the target. The event is put before the start clock read of target window 0. |
| 851 | `    check("c: the rule fails on a page read between the start clock read of the target and its first kernel call",` | Check: the rule fails on a page read between the start clock read of the target and its first kernel call. |
| 852 | `          trace_problems(f, broken(tgt0, "page_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 853 | `    check("c: the rule fails on an output between two target windows", trace_problems(f, broken(tgt1 - 1, "output"), w, e))` | Check: the rule fails on an output between two target windows. |
| 854 | `    check("c: the rule fails on a counter read between predecessor and target in a closed trial",` | Check: the rule fails on a counter read between the predecessor and the target in a closed trial. |
| 855 | `          trace_problems(f, broken(tgt0 - 1, "count_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 856 | `    check("c: the rule fails on a CPU clock read between predecessor and target in a closed trial",` | Check: the rule fails on a CPU clock read between the predecessor and the target in a closed trial. |
| 857 | `          trace_problems(f, broken(tgt0 - 1, "cpu_clock"), w, e))` | Continues the check: the broken trace and the rule. |
| 858 | `    check("c: the rule fails on a warm-up kernel call before the target", trace_problems(f, broken(tgt0 - 1, "kernel_first:warmup:0"), w, e))` | Check: the rule fails on a warm-up kernel call before the target. The added event has the name `kernel_first:warmup:0`. |
| 859 | `    check("c: the rule fails on a second first call of the target window", trace_problems(f, broken(tgt0 + 1, "kernel_first:target:0"), w, e))` | Check: the rule fails on a second first call of target window 0. |
| 860 | `    check("c: the rule fails on a page read inside the predecessor window", trace_problems(f, broken(pred + 2, "page_read"), w, e))` | Check: the rule fails on a page read inside the predecessor window. |
| 861 | `    check("c: the rule fails on a counter open inside the prefix", trace_problems(f, broken(names.index("kernel_first:prefix:2") + 2, "count_open"), w, e))` | Check: the rule fails on a counter open inside the prefix. |
| 862 | `    check("c: the rule fails on a lost clock read of a window", trace_problems(f, ev[:tgt0 + 1] + ev[tgt0 + 2:], w, e))` | Check: the rule fails on a lost clock read of a window. The event after the first kernel call of target window 0 is removed. |
| 863 | `    one_clock = ev[:tgt0 - 2] + ev[tgt0 - 1:]` | `one_clock`: the trace without the event two places before the first kernel call of target window 0. That event is the end clock read of the predecessor window. |
| 864 | `    check("c: the rule fails when one clock read serves as end and start of a boundary", trace_problems(f, one_clock, w, e))` | Check: the rule fails when one clock read serves as the end of a window and as the start of the next one. The runner must read the clock twice at a boundary. Only then the gap is a measured time. |
| 865 | `    e_bad = list(e)` | `e_bad`: a copy of the `E` row. |
| 866 | `    e_bad[6] = str(int(e[6]) + 5)` | Adds 5 ns to its `gap_ns`. |
| 867 | `    check("d: the rule fails when gap_ns is not the time between the two clock reads", trace_problems(f, ev, w, e_bad))` | Check d: the rule fails when `gap_ns` is not the time between the two clock reads of the trace. |
| 868 | `    # target window 0 (20 ms): the clock read before its last one already lies at the requested end` | Comment: the next case uses target window 0, which has 20 ms. Its clock read before the last one is moved to the requested end. |
| 869 | `    late = list(ev)` | `late`: a copy of the trace. |
| 870 | `    late[tgt1 - 3] = ("clock", ev[tgt0 - 1][1] + 20000000)` | Changes the event three places before the first kernel call of target window 1. That event is the clock read before the last one of target window 0. Its new time is the start of the window plus 20000000 ns, exactly the requested end. |
| 871 | `    p = trace_problems(f, late, w, e)` | Applies the rule to this trace. |
| 872 | `    check("c: the rule fails on a window that runs on after a clock read at its requested end",` | Check c: the rule fails on a window that continues after a clock read at its requested end. |
| 873 | `          names[tgt1 - 3] == "clock" and tgt1 - 3 > tgt0 and p == ["window 6: runs on after the clock read that passed "` | Continues the check: the changed event is a clock read inside target window 0, and the rule reports exactly one problem, for window 6. Window 6 is target window 0: six windows of the trial run before it. |
| 874 | `                                                                 "its requested duration"], p)` | Continues the check: the rest of the expected problem text, and the detail. |

### `test_counters`, checks f: a counter that does not open is reported (lines 877 to 928)

| Line | Source | Explanation |
|---:|---|---|
| 877 | `def test_counters():` | Starts the test `test_counters`. |
| 878 | `    """(f) a failed open is reported, and the timing rows stay"""` | Description text: the checks named f. A failed open is reported, and the timing rows stay. |
| 879 | `    lines = ["0 A 1 - oldread@8M:20 - oldread@8M 2 10 closed 0",` | `lines`: three trials, each with a prefix of 20 ms and 2 target windows of 10 ms of `oldread` on 8 MiB. Trial 0 has the count mode `closed`. |
| 880 | `             "1 B 1 - oldread@8M:20 - oldread@8M 2 10 read 0",` | Trial 1 has the count mode `read`. |
| 881 | `             "2 C 1 - oldread@8M:20 - oldread@8M 2 10 open 0"]` | Trial 2 has the count mode `open`. |
| 882 | `    plan = write_plan("count", lines)` | Writes the plan. |
| 883 | `    rc, out, err = trial(plan, ["--pmu-type", "999999", "--events", "cycles=0x11,instructions=0x08"])` | Runs it with the PMU type 999999 and two events named `cycles` and `instructions`. The check of line 885 says that this PMU type does not exist. So the events cannot open. |
| 884 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 885 | `    check("f: a PMU type that does not exist: status 0", rc == 0, err)` | Check f: the exit status is 0. A counter that does not open does not stop the run. |
| 886 | `    x = [(f[1], f[2]) for f in rows.get("X", [])]` | `x`: the trial number and the code of each `X` row. |
| 887 | `    check("f: an X row with code count_open for each counted trial, none for the closed trial",` | Check f: one `X` row with the code `count_open` for each counted trial, and none for the closed trial. So the result itself says which trials have no usable counts. |
| 888 | `          x == [("1", "count_open"), ("2", "count_open")], rows.get("X"))` | Continues the check: the expected list, the trials 1 and 2. |
| 889 | `    check("f: count_state is fail in the E rows of the counted trials", [f[9] for f in rows.get("E", [])] == ["closed", "fail", "fail"],` | Check f: the count state in the `E` rows is `closed`, `fail`, `fail`. So a trial whose counters did not open says so in its own summary row. |
| 890 | `          rows.get("E"))` | Continues the check: the `E` rows as the detail. |
| 891 | `    check("f: the timing rows of the failed trials are kept",` | Check f: the timing rows of the failed trials are kept. |
| 892 | `          all(not window_problems(f, of_trial(rows, "W", i)) for i, f in enumerate(plan_lines(plan))))` | Continues the check: the `W` rows of every trial pass `window_problems`. The design says to reject unsupported event counts for interpretation and to keep the timing rows. |
| 893 | `    c = rows.get("C", [])` | `c`: the `C` rows. A `C` row belongs to one target window of a trial with the count mode `read`. It holds the enabled time and the running time of the counter group, the thread CPU time, and one count per event. |
| 894 | `    check("f: the C rows of the failed read trial hold NA for the group and a number for the CPU time",` | Check f: the `C` rows of the failed read trial hold `NA` for the group and a number for the CPU time. |
| 895 | `          len(c) == 2 and all(f[1] == "1" and f[3:5] == ["NA", "NA"] and f[5].isdigit() and f[6:] == ["NA", "NA"] for f in c), c)` | Continues the check: 2 rows, both of trial 1. The enabled and the running time are `NA`, the CPU time is a number, and both event counts are `NA`. A count that was not measured is never printed as 0. |
| 896 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary. |
| 897 | `    check("f: M rows record the PMU type and the event codes", m.get("pmu_type") == "999999" and` | Check f: the `M` rows record the PMU type and the event codes. |
| 898 | `          m.get("events") == "cycles=0x11;instructions=0x8", m)` | Continues the check: `pmu_type` is `999999`, and `events` is `cycles=0x11;instructions=0x8`: each name with its code in hex. |
| 900 | `    if not getattr(E, "soft_counters", False):` | Tests whether the software events opened in `test_trace` (line 803). |
| 901 | `        check("f: counter rows with software events (NOT RUN: the events did not open in the trace test)", False)` | If not, the rest of this test cannot run. The line records a failed check with `NOT RUN` in its name. |
| 902 | `        return` | Ends the test in that case. |
| 903 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,bad=999"])` | Runs the plan with the PMU type 1 and two events: `task_clock`, and an event with the code 999, which the test expects not to open. |
| 904 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 905 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 906 | `    check("f: one event of two does not open: X rows count_open and count_state fail",` | Check f: when one event of two does not open, the runner prints `X` rows `count_open` and the count state `fail`. |
| 907 | `          rc == 0 and [(f[1], f[2]) for f in rows.get("X", [])] == [("1", "count_open"), ("2", "count_open")] and` | Continues the check: status 0, and `X` rows for the trials 1 and 2 ... |
| 908 | `          [f[9] for f in rows["E"]] == ["closed", "fail", "fail"] and "1 of 2" in rows["X"][0][3], rows.get("X"))` | Continues the check: ... the states `closed`, `fail`, `fail`, and the text `1 of 2` in the first `X` row. |
| 909 | `    check("f: the event that opened has numbers, the other has NA",` | Check f: the event that opened has numbers, and the other one has `NA`. |
| 910 | `          len(c) == 2 and all(f[3].isdigit() and f[6].isdigit() and f[7] == "NA" for f in c), c)` | Continues the check: in both `C` rows the enabled time and the first count are numbers, and the second count is `NA`. |
| 911 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with two events that open: `task_clock` and `cpu_clock`. |
| 912 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 913 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 914 | `    check("f: events that open: no X row, count_state closed, read, open",` | Check f: with events that open there is no `X` row, and the count states are `closed`, `read`, `open`. |
| 915 | `          rc == 0 and not rows.get("X") and [f[9] for f in rows["E"]] == ["closed", "read", "open"], rows.get("X"))` | Continues the check: the three conditions, and the `X` rows as the detail. |
| 916 | `    check("f: one C row per target window of the read trial only, with enabled, running, CPU time and 2 counts",` | Check f: one `C` row per target window of the read trial only, with the enabled time, the running time, the CPU time and 2 counts. |
| 917 | `          [(f[1], f[2]) for f in c] == [("1", "0"), ("1", "1")] and all(len(f) == 8 and all(v.isdigit() for v in f[3:]) for f in c), c)` | Continues the check: the rows are those of trial 1, windows 0 and 1. Each has 8 fields, and every value is a number. The trial with the count mode `open` prints no `C` row. |
| 918 | `    check("f: running time equals enabled time, and the CPU time is above 0",` | Check f: the running time equals the enabled time, and the CPU time is above 0. |
| 919 | `          all(f[3] == f[4] and int(f[5]) > 0 for f in c), c)` | Continues the check: the condition on both rows. Equal times mean that the counters counted during the whole window. The runner reports a running time below the enabled time as a multiplexed counter. |
| 920 | `    # A C row holds the change over its target window. The group was opened before the 20 ms prefix, so a row that` | Comment: a `C` row holds the change over its target window. The counter group was opened before the prefix of 20 ms. So a row that held the reading itself ... |
| 921 | `    # held the reading itself would be at least 3 times the 10 ms window.` | Comment: ... would be at least 3 times the window of 10 ms. |
| 922 | `    tw = [w for w in of_trial(rows, "W", 1) if w[2] == "target"]` | `tw`: the `W` rows of the target windows of trial 1. |
| 923 | `    span = [int(w[8]) - int(w[7]) for w in tw]` | `span`: the duration of each of these windows in ns. |
| 924 | `    check("f: enabled time, CPU time and both software clocks of a C row lie between half of the window time and "` | Check f: the enabled time, the CPU time and both software clocks of a `C` row lie between half of the window time and ... |
| 925 | `          "the window time plus 1 ms", len(c) == len(span) == 2 and` | Continues the check: ... the window time plus 1 ms. There must be 2 rows and 2 windows. |
| 926 | `          all(n // 2 <= int(v) <= n + 1000000 for f, n in zip(c, span) for v in f[3:]), (c, span))` | Continues the check: every value from field 3 on is compared with the duration of its window. This proves that a `C` row is the difference of two readings at the two ends of one target window, and not a total from the open on. |

### `test_kill_and_seq`, checks g: a killed trial, and the unchanged interval mode (lines 929 to 969)

| Line | Source | Explanation |
|---:|---|---|
| 929 | `def test_kill_and_seq():` | Starts the test `test_kill_and_seq`. |
| 930 | `    """(g) S row without E row after SIGKILL, and the unchanged --seq mode"""` | Description text: the checks named g. After the signal `SIGKILL` an `S` row stands without its `E` row. The mode `--seq` is unchanged. |
| 931 | `    plan = write_plan("kill", [GOOD, "1 long 1 - oldread@8M:400 - oldread@8M 4 5000 closed 0"])` | Writes a plan: the good line, then a long trial 1 with a prefix of 400 ms and 4 target windows of 5000 ms each. |
| 932 | `    path = os.path.join(E.tmp, "kill.csv")` | `path`: the file `kill.csv` in the temporary folder. It takes the output of the runner. |
| 933 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 934 | `        proc = subprocess.Popen([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=f,` | Starts the runner on the plan in the background, with its standard output in that file. |
| 935 | `                                stderr=subprocess.DEVNULL)` | Continues the call of line 934: the error output is discarded. |
| 936 | `    deadline = time.time() + 30` | `deadline`: 30 s from now. |
| 937 | `    while time.time() < deadline and proc.poll() is None:` | Waits as long as the deadline has not passed and the runner still runs: |
| 938 | `        with open(path) as f:` | Opens the output file for reading. |
| 939 | `            if "\nS,1," in f.read():` | Tests whether the file holds the `S` row of trial 1. |
| 940 | `                break` | Leaves the wait loop. |
| 941 | `        time.sleep(0.02)` | Sleeps 0.02 s before the next test of the file. |
| 942 | `    time.sleep(0.2)  # the worker is now inside the timed sequence of trial 1` | Waits 0.2 s more. By the comment the worker is then inside the timed sequence of trial 1. |
| 943 | `    alive = proc.poll() is None` | `alive`: true when the runner still runs. |
| 944 | `    proc.send_signal(signal.SIGKILL)` | Sends the signal `SIGKILL` to the runner. Linux ends the process immediately. The process cannot react to this signal. |
| 945 | `    rc = proc.wait()` | `rc`: the exit status. For a process that a signal ended, Python gives the negative number of the signal. |
| 946 | `    with open(path) as f:` | Opens the output file. |
| 947 | `        rows = rows_of(f.read())` | `rows`: its content sorted by row type. |
| 948 | `    check("g: the process was killed inside trial 1", alive and rc == -signal.SIGKILL, rc)` | Check g: the process was alive before the kill and was ended by `SIGKILL`. So the process was ended while a trial ran. |
| 949 | `    check("g: after SIGKILL the S row of trial 1 has no E row, and trial 0 has both",` | Check g: after the kill the `S` row of trial 1 has no `E` row, and trial 0 has both. |
| 950 | `          [f[1] for f in rows.get("S", [])] == ["0", "1"] and [f[1] for f in rows.get("E", [])] == ["0"], rows.get("E"))` | Continues the check: the `S` rows are those of the trials 0 and 1, and the only `E` row is that of trial 0. The runner prints the `S` row before a trial and all other rows after it. So the analysis can find an interrupted trial: a trial-start record without a trial-complete record, as the design asks. |
| 951 | `    check("g: no W row of the interrupted trial", not of_trial(rows, "W", 1))` | Check g: the output holds no `W` row of the interrupted trial. So no half measurement of it can be used. |
| 953 | `    args = ["--seq", "oldread,asmread@1M,oldread,read", "--bytes", "8M", "--rounds", "2", "--min-ms", "20", "--stop", "pass",` | `args`: a run in the interval mode. The sequence is `oldread`, `asmread` on 1 MiB, `oldread`, `read`. The buffer has 8 MiB. The sequence runs in 2 rounds. Each interval lasts at least 20 ms. With `--stop pass` a thread runs whole passes and stops at the first clock read at or after that minimum time. |
| 954 | `            "--cpus", str(E.cpu), "--threads", "1"]` | Continues line 953: the worker CPU and 1 thread. |
| 955 | `    rc, out, err = run(args)` | Runs these arguments with the runner under test. |
| 956 | `    rc0, out0, _ = run(args, binary=E.bin_old)` | Runs the same arguments with `E.bin_old`, the binary that was built from `bwx.c`, the first runner. |
| 957 | `    r = rows_of(out)` | `r`: the output of the runner under test, sorted by row type. |
| 958 | `    check("g: --seq mode prints 8 I rows, 8 T rows and 8 P rows", rc == 0 and` | Check g: the interval mode prints 8 `I` rows, 8 `T` rows and 8 `P` rows. |
| 959 | `          [len(r.get(k, [])) for k in "ITP"] == [8, 8, 8], (rc, err))` | Continues the check: the three counts. 8 is 4 kernels of the sequence times 2 rounds. An `I` row is one interval, a `T` row is one thread of an interval, and a `P` row is the page state of a buffer. |
| 961 | `    def shape(text):` | Starts the inner function `shape`. It reduces an output text to its form, without the measured values. |
| 962 | `        return [line if line.startswith("#") else (line.split(",")[0], len(line.split(",")), line.split(",")[1:4]) for line in text.splitlines()]` | Returns one item per line of the text. A comment line stays whole. A data row becomes the row type, the number of fields and the fields 1 to 3. For an `I` row and a `T` row these are the round, the position and the kernel. |
| 964 | `    check("g: --seq mode: comment lines byte for byte and row order as the binary built from bwx.c",` | Check g: in the interval mode the comment lines are equal byte for byte, and the rows have the same order, as in the output of the binary built from `bwx.c`. |
| 965 | `          rc0 == 0 and shape(out) == shape(out0))` | Continues the check: both shapes are equal. So the code of the trial mode did not change what the interval mode prints. The design uses the unchanged interval mode to repeat an earlier measurement. |
| 966 | `    check("g: that comparison can fail: another sequence gives another shape",` | Check g: that comparison can fail. |
| 967 | `          shape(out) != shape(run(args[:1] + ["oldread,read"] + args[2:])[1]))` | Continues the check: a run with the shorter sequence `oldread,read` has another shape. |

### `strip_marked`: a source text without its marked blocks (lines 970 to 975)

| Line | Source | Explanation |
|---:|---|---|
| 970 | `def strip_marked(text):` | Starts the function `strip_marked`. It removes the marked blocks from a source text. A marked block is an addition of round 3. It starts with a comment line `bwx10+` and ends with a comment line `bwx10-`. |
| 971 | `    """(text without the blocks between a line 'bwx10+' and a line 'bwx10-', number of blocks, markers left)"""` | Description text: the result has three values: the text without the blocks, the number of blocks, and the number of markers that are left. |
| 972 | `    out, n = re.subn(r"^[ \t]*/\* bwx10\+ \*/\n.*?^[ \t]*/\* bwx10- \*/\n", "", text, flags=re.M \| re.S)` | Removes every block. The pattern matches a line that holds only the comment `/* bwx10+ */` after optional spaces or tabs, then the shortest text up to and with a line that holds only `/* bwx10- */`. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. `re.subn` returns the new text and the number of blocks removed. |
| 973 | `    return out, n, out.count("bwx10+") + out.count("bwx10-")` | Returns the text, the number of blocks, and the number of marker words `bwx10+` and `bwx10-` that the text still holds. A marker that is left shows a block that was not marked in the right form. |

### `test_source`: the runner source is the accepted source plus marked additions (lines 976 to 1004)

| Line | Source | Explanation |
|---:|---|---|
| 976 | `def test_source():` | Starts the test `test_source`. The names of its checks start with `source:`. |
| 977 | `    """bwx10.c is bwx8.c plus marked additions, and bwx8.c holds the text of bwx.c"""` | Description text: `bwx10.c` is `bwx8.c` plus marked additions, and `bwx8.c` holds the text of `bwx.c`, the source of the first runner. |
| 978 | `    with open(os.path.join(OLD, "bwx.c")) as f:` | Opens `bwx.c`, the source of the first runner. |
| 979 | `        old = f.read()` | `old`: its whole text. |
| 980 | `    with open(os.path.join(HERE, "bwx10.c")) as f:` | Opens `bwx10.c`. |
| 981 | `        new10 = f.read()` | `new10`: its whole text. |
| 982 | `    with open(os.path.join(X8, B8 + ".c")) as f:` | Opens the source of the accepted runner in the folder `X8`. |
| 983 | `        new8 = f.read()` | `new8`: its whole text. |
| 984 | `    new, blocks, left = strip_marked(new10)` | `new`: the text `new10` without its blocks `bwx10+` to `bwx10-`. `blocks`: the number of these blocks. `left`: the number of markers that are left. |
| 985 | `    inc = '#include "bwx10_selftest.c"\n'` | `inc`: the source line that includes the self-test file `bwx10_selftest.c`. |
| 986 | `    check("source: bwx10.c without its %d marked blocks, and with the old name of the self-test file, is the file of "` | Check: `bwx10.c` without its marked blocks, and with the old name of the self-test file, is the file of ... |
| 987 | `          "the accepted runner byte for byte" % blocks,` | Continues the name of the check: ... the accepted runner byte for byte. The name prints the number of blocks. When the check passes, round 3 only added text. The 21 kernels of the accepted runner, the function `call`, `timed_sequence()` and the interval mode are then the accepted text. |
| 988 | `          blocks >= 10 and left == 0 and new.count(inc) == 1 and new.replace(inc, inc.replace("bwx10", B8)) == new8,` | Continues the check: at least 10 blocks were removed, no marker is left, the include line stands once, and the text with the name of the accepted runner in that line equals the source of the accepted runner. |
| 989 | `          (blocks, left, len(new), len(new8)))` | Continues the check: the detail, with the two counts and the lengths of the two texts. |
| 990 | `    check("source: that comparison can fail: one changed character outside the marked blocks",` | Check: that comparison can fail on one changed character outside the marked blocks. |
| 991 | `          strip_marked(new10.replace("x->bytes = bytes;", "x->bytes = bytes ;", 1))[0].replace(inc, inc.replace("bwx10", B8)) != new8)` | Continues the check: the copy with a space put into `x->bytes = bytes;`, without its marked blocks and with the old include name, must differ from the source of the accepted runner. |
| 992 | `    a8, a10 = fn_span(new8, "timed_sequence"), fn_span(new10, "timed_sequence")` | `a8`, `a10`: the place of the body of `timed_sequence` in `bwx8.c` and in `bwx10.c` (line 249). |
| 993 | `    check("source: timed_sequence() of bwx10.c is the text of the accepted runner",` | Check: `timed_sequence()` of `bwx10.c` is the text of the accepted runner. |
| 994 | `          a8 is not None and a10 is not None and new8[a8[0]:a8[1]] == new10[a10[0]:a10[1]])` | Continues the check: both bodies were found, and they are equal. So the loop that times the windows without `--hot-copy` is the loop of the accepted runner, character for character. A run without the option times its windows with the same code as the accepted runner. |
| 995 | `    a, b = old.index("#define _GNU_SOURCE"), old.index('#include "bwx_selftest.c"')` | `a`, `b`: two positions in `bwx.c`: the line `#define _GNU_SOURCE` and the line that includes the self-test file of `bwx`. The text between them holds the kernels, the function `call`, the buffer allocation and the code of the interval mode up to the function `parse_events`. |
| 996 | `    check("source: bwx.c from '#define _GNU_SOURCE' to the end of parse_events() stands unchanged in bwx10.c without "` | Check: the text of `bwx.c` from `#define _GNU_SOURCE` to the end of `parse_events()` stands unchanged in `bwx10.c` without ... |
| 997 | `          "its marked blocks", new.count(old[a:b]) == 1)` | Continues the check: ... its marked blocks. That old text must stand exactly once in the text without marked blocks. So the kernels and the function `call` of the first runner are unchanged. |
| 998 | `    kernels_end = new.index(old[a:b]) + len(old[a:b])` | `kernels_end`: the position where that old text ends in the text without marked blocks. |
| 999 | `    check("source: every line of the trial mode stands after that text",` | Check: every line of the trial mode stands after that text. |
| 1000 | `          min(new.index(s) for s in ("timed_sequence", "trial_main", "tclock", "struct trial")) > kernels_end)` | Continues the check: the first place of each of the names `timed_sequence`, `trial_main`, `tclock` and `struct trial` lies after `kernels_end`. The build keeps the order of the source. So code that is added after the kernels does not move them. |
| 1001 | `    hook = ('    for (int i = 1; i < argc; i++)\n        if (!strcmp(argv[i], "--trial"))\n'` | `hook`: the three source lines that start the trial mode. They loop over the arguments and compare each one with `--trial` ... |
| 1002 | `            '            return trial_main(argc, argv);\n')` | Continues line 1001: ... and call `trial_main` when one argument is `--trial`. |
| 1003 | `    check("source: main() of bwx10.c is main() of bwx.c plus the 3 lines that start the trial mode",` | Check: `main()` of `bwx10.c` is `main()` of `bwx.c` plus the 3 lines that start the trial mode. |
| 1004 | `          new10.count(hook) == 1 and new10[new10.index("int main("):].replace(hook, "") == old[old.index("int main("):])` | Continues the check: the hook stands once in `bwx10.c`. The text from `int main(` to the end of the file, without the hook, equals the same part of `bwx.c`. So apart from the hook, `main()` is the code of the first runner. |

### `test_source`: the self-test file is the accepted one plus marked additions (lines 1005 to 1017)

| Line | Source | Explanation |
|---:|---|---|
| 1005 | `    with open(os.path.join(OLD, "bwx_selftest.c")) as f:` | Opens `bwx_selftest.c`, the self-test file of the first runner. |
| 1006 | `        old_st = f.read()` | `old_st`: its whole text. |
| 1007 | `    with open(os.path.join(HERE, "bwx10_selftest.c")) as f:` | Opens `bwx10_selftest.c`. |
| 1008 | `        new_st10 = f.read()` | `new_st10`: its whole text. |
| 1009 | `    with open(os.path.join(X8, B8 + "_selftest.c")) as f:` | Opens the self-test file of the accepted runner in the folder `X8`. |
| 1010 | `        new_st8 = f.read()` | `new_st8`: its whole text. |
| 1011 | `    new_st, blocks, left = strip_marked(new_st10)` | `new_st`: the text `new_st10` without its blocks `bwx10+` to `bwx10-`. `blocks` and `left`: the number of these blocks and the number of markers that are left. |
| 1012 | `    check("source: bwx10_selftest.c without its %d marked blocks is the self-test file of the accepted runner" % blocks,` | Check: `bwx10_selftest.c` without its marked blocks is the self-test file of the accepted runner. The name prints the number of blocks. When the check passes, every check of the accepted self-test is kept as it was. |
| 1013 | `          blocks >= 3 and left == 0 and new_st == new_st8)` | Continues the check: at least 3 blocks were removed, no marker is left, and the text equals the self-test file of the accepted runner. |
| 1014 | `    a, b = old_st.index("static int failures;"), old_st.index("static int selftest(void)")` | `a`, `b`: two positions in the self-test file of the first runner: the line `static int failures;` and the head of the function `selftest`. The text between them holds the checks of the kernels. |
| 1015 | `    check("source: the kernel checks of bwx_selftest.c stand unchanged in bwx10_selftest.c without its marked blocks",` | Check: the kernel checks of `bwx_selftest.c` stand unchanged in `bwx10_selftest.c` without its marked blocks. |
| 1016 | `          new_st.count(old_st[a:b]) == 1)` | Continues the check: that old text stands exactly once in the text without marked blocks. |

### `test_source`: the kernels keep their start, size and order in the binary (lines 1018 to 1038)

| Line | Source | Explanation |
|---:|---|---|
| 1018 | `    def syms(binary):` | Starts the inner function `syms`. It reads the kernel symbols of a binary. |
| 1019 | `        out = subprocess.run(["nm", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs `nm -S` on the binary. It lists each symbol with its address and its size. |
| 1020 | `        return {p[3]: (int(p[0], 16) % 64, p[1]) for p in (line.split() for line in out.splitlines())` | Returns a dictionary. The key is a symbol name. The value is the address modulo 64 and the size as text. |
| 1021 | `                if len(p) == 4 and p[3].startswith("k_")}` | Continues line 1020: only lines with 4 fields whose name starts with `k_` are taken. These are the kernel functions. |
| 1023 | `    s_old, s_8, s_new = syms(E.bin_old), syms(E.bin8), syms(E.bin)` | `s_old`, `s_8`, `s_new`: the kernel symbols of three local builds: `bwx`, the accepted runner `bwx8`, and `bwx10`, the runner under test. |
| 1024 | `    common = {k: v for k, v in s_new.items() if k in s_old}` | `common`: the symbols of the build under test whose kernels the first runner also has. |
| 1025 | `    check("source: the 21 old kernels have the same start modulo 64 and the same size in the local builds of bwx, of the "` | Check: the 21 old kernels have the same start modulo 64 and the same size in the local builds of `bwx`, of the ... |
| 1026 | `          "accepted runner and of bwx10", len(s_old) == 21 and s_old == s_8 == common,` | Continues the check: ... accepted runner and of `bwx10`. The first runner has 21 kernels, and the three dictionaries are equal. The start modulo 64 is the place of a function inside a 64-byte block of code. The design keeps this place and the loop bodies fixed. An equal size shows that the machine code of a kernel has the same length. |
| 1027 | `          {k: (s_old[k], s_new.get(k)) for k in s_old if s_old[k] != s_new.get(k)})` | Continues the check: the detail lists each old kernel whose values differ. |
| 1028 | `    check("source: bwx10 has 26 kernels: the 21 old ones and the 5 new ones",` | Check: `bwx10` has 26 kernels: the 21 old ones and the 5 new ones. |
| 1029 | `          sorted(set(s_new) - set(s_old)) == sorted("k_" + k for k in NEW_KERNELS), sorted(set(s_new) - set(s_old)))` | Continues the check: the kernels of `bwx10` that `bwx` does not have are exactly those of `NEW_KERNELS`. The condition tests these 5 names only. The 21 old kernels are tested by the check of lines 1025 to 1027. The detail shows the names found. |
| 1031 | `    def order(binary):` | Starts the inner function `order`. It reads the order of the kernels in a binary. |
| 1032 | `        out = subprocess.run(["nm", "-n", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs `nm -n` on the binary. It lists the symbols sorted by address. |
| 1033 | `        return [line.split()[-1] for line in out.splitlines() if line.split()[-1].startswith("k_")]` | Returns the symbol names that start with `k_`, in that order. |
| 1035 | `    o = order(E.bin)` | `o`: the order of the kernels in the binary under test. |
| 1036 | `    check("source: in the binary the 5 new kernels stand after every old kernel, in the order of the table",` | Check: in the binary the 5 new kernels stand after every old kernel, in the order of the kernel table. |
| 1037 | `          o[-5:] == ["k_" + k for k in NEW_KERNELS] and o[:21] == order(E.bin8), o[-6:])` | Continues the check: the last 5 places hold `NEW_KERNELS`, and the first 21 places equal the order in the build of the accepted runner. A kernel that is added behind all others leaves the addresses of the others as they were. |

### `test_source`: `path_to_seq` and the place of the code after the kernels (lines 1039 to 1074)

| Line | Source | Explanation |
|---:|---|---|
| 1039 | `    # The pad after the new kernels. bwx10.c holds the value of the accepted AArch64 build (24). A copy built with` | Comment: the pad after the new kernels. `bwx10.c` holds the value of the accepted AArch64 build, 24. A copy built with ... |
| 1040 | `    # the value of the local build of the accepted runner must place every function from call() to` | Comment: ... the value of the local build of the accepted runner must place every function from `call()` to ... |
| 1041 | `    # timed_sequence() as that build does.` | Comment: ... `timed_sequence()` as that build does. |
| 1042 | `    def path_to_seq(binary):` | Starts the inner function `path_to_seq`. It reads from a binary where the functions from `call` to `timed_sequence` lie. `call` is the function of the runner that starts a kernel. |
| 1043 | `        """(start of call modulo 64, [(function, distance from call, size)] from call to timed_sequence)"""` | Description text: the result is the start of `call` modulo 64, and a list with the name, the distance from `call` and the size of each function from `call` to `timed_sequence`. |
| 1044 | `        out = subprocess.run(["nm", "-n", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs the tool `nm` on the binary. It lists the symbols. `-n` sorts them by address. `-S` also prints the size of each symbol. |
| 1045 | `        s = [(p[3], int(p[0], 16), int(p[1], 16)) for p in (line.split() for line in out.splitlines()) if len(p) == 4 and p[2] in "tT"]` | `s`: one entry per function: the name, the address and the size. A line counts when it has 4 fields and the symbol type `t` or `T`, the two types of a symbol in the code section. |
| 1046 | `        names = [x[0] for x in s]` | `names`: the function names in the order of their addresses. |
| 1047 | `        if "call" not in names or "timed_sequence" not in names:` | Tests whether `call` or `timed_sequence` is not among them. A function has no symbol when the compiler wrote no copy of its own for it. A compiler can leave that copy out when it put the function inline at every call. |
| 1048 | `            return None, []` | Returns `None` and an empty list in that case. |
| 1049 | `        i, j = names.index("call"), names.index("timed_sequence")` | `i`, `j`: the positions of `call` and of `timed_sequence`. |
| 1050 | `        return s[i][1] % 64, [(x[0], x[1] - s[i][1], x[2]) for x in s[i:j + 1]]` | Returns the start address of `call` modulo 64 and, for every function from `call` to `timed_sequence`, its name, its distance from `call` in bytes and its size in bytes. |
| 1052 | `    E.call8, path8 = path_to_seq(E.bin8)` | `E.call8`: the start of `call` modulo 64 in the local build of the accepted runner. `path8`: its functions from `call` to `timed_sequence`, as `path_to_seq` returns them. |
| 1053 | `    if not check("source: the local build of the accepted runner has call() and timed_sequence() as functions "` | Check: the local build of the accepted runner has `call()` and `timed_sequence()` as functions ... |
| 1054 | `                 "(needed for the placement checks)", E.call8 is not None and len(path8) >= 3, path8[:3]):` | Continues the check: ... and at least 3 functions on that path. The placement checks need them. |
| 1055 | `        return` | Ends the test when they are missing. |
| 1056 | `    E.bin_placed = os.path.join(E.tmp, "bwx10-placed")` | `E.bin_placed`: the path `bwx10-placed` in the temporary folder, for a second build of `bwx10.c`. |
| 1057 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % E.call8, "-o", E.bin_placed, os.path.join(HERE, "bwx10.c")])` | Compiles `bwx10.c` with `-DPAD_after_kernels=` and the value `E.call8`. `-D` sets a C macro from the command line. The pad after the kernels then has the value that matches the local machine: the code after the kernels starts at `E.call8` modulo 64, as in the local build of the accepted runner. |
| 1058 | `    call_p, path_p = path_to_seq(E.bin_placed) if r.returncode == 0 else (None, [])` | `call_p`, `path_p`: the placement of that build, or `None` and an empty list when the compiler failed. |
| 1059 | `    check("source: with the pad of the local build, the functions from call() to timed_sequence() (at least 10) have the "` | Check: with the pad of the local build, the functions from `call()` to `timed_sequence()` (at least 10) have the ... |
| 1060 | `          "start modulo 64, the distances and the sizes of the accepted runner",` | Continues the name of the check: ... start modulo 64, the distances and the sizes of the accepted runner. |
| 1061 | `          call_p == E.call8 and path_p == path8 and len(path8) >= 10, (call_p, E.call8, len(path8), [x for x in zip(path_p, path8) if x[0] != x[1]][:3]))` | Continues the check: the start of `call` and the whole list are equal in both builds, and the list has at least 10 functions. These functions are the code that runs around the kernel call inside a timed sequence. So the kernels that were added do not move this code, and they do not change its length. |
| 1062 | `    other = (E.call8 + 4) % 64` | `other`: a pad that is 4 bytes larger, modulo 64. |
| 1063 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % other, "-o", E.bin_placed + "-off", os.path.join(HERE, "bwx10.c")])` | Compiles `bwx10.c` with that other pad into `bwx10-placed-off`. |
| 1064 | `    check("source: that comparison can fail: a pad 4 bytes larger moves call() by 4 bytes",` | Check: that comparison can fail: a pad 4 bytes larger moves `call()` by 4 bytes. |
| 1065 | `          r.returncode == 0 and path_to_seq(E.bin_placed + "-off")[0] == other, (other, path_to_seq(E.bin_placed + "-off")[0]))` | Continues the check: the build worked, and its `call` starts at `other` modulo 64. |
| 1066 | `    with open(os.path.join(REF, "listing.txt")) as f:` | Opens `listing.txt` in the folder `REF`. It is the machine-code listing of the accepted build of `bwx8`. |
| 1067 | `        ref_text = f.read()` | `ref_text`: its whole text. |
| 1068 | `    last = max(int(x, 16) for x in re.findall(r"^\s+([0-9a-f]+):\t", ref_text, re.M))` | `last`: the highest instruction address of that listing. The pattern finds the hex address at the start of each instruction line, before a colon and a tab. |
| 1069 | `    m = re.search(r"^#define PAD_after_kernels (\d+)$", new10, re.M)` | `m`: the source line `#define PAD_after_kernels` with its number in `bwx10.c`. Group 1 is the number. |
| 1070 | `    check("source: the pad in bwx10.c (24) is the address after the last instruction of the last kernel in "` | Check: the pad in `bwx10.c` (24) is the address after the last instruction of the last kernel in ... |
| 1071 | `          "ref-bwx8/listing.txt (0x4a14, a ret), modulo 64",` | Continues the name of the check: ... `ref-bwx8/listing.txt`, modulo 64. The name gives that last instruction as a `ret` at 0x4a14. |
| 1072 | `          m is not None and int(m.group(1)) == (last + 4) % 64 == 24 and "    %x:\tret\n" % last in ref_text, (m and m.group(1), hex(last)))` | Continues the check: the number of the `#define` equals `last + 4` modulo 64 and equals 24, and the instruction at `last` is `ret`. An AArch64 instruction has 4 bytes. So `last + 4` is the first address after the kernels in the accepted build. |

### `test_selftest`: the self-test of the runner, and builds that it must reject (lines 1075 to 1123)

| Line | Source | Explanation |
|---:|---|---|
| 1075 | `def test_selftest():` | Starts the test `test_selftest`. |
| 1076 | `    rc, out, err = run(["--selftest"])` | Runs the runner with `--selftest`. The self-test checks what the kernels do to memory and how the trial mode counts bytes and times. It measures no rate. |
| 1077 | `    trial_lines = [line for line in out.splitlines() if line.startswith("trial,")]` | `trial_lines`: the lines of its output that start with `trial,`. Each one is one check of the trial mode and ends with `pass` or `FAIL`. |
| 1078 | `    check("selftest: status 0, no FAIL line, 30 checks of the trial mode (19 of the accepted runner, 8 with --hot-copy, "` | Check: the self-test ends with status 0 and no `FAIL` line, and it has 30 checks of the trial mode (19 of the accepted runner, 8 with `--hot-copy`, ... |
| 1079 | `          "3 of the touch test)",` | Continues the name of the check: ... and 3 of the touch test). |
| 1080 | `          rc == 0 and "FAIL" not in out and out.rstrip().endswith("# failures=0") and len(trial_lines) == 30 and` | Continues the check: status 0, the word `FAIL` nowhere, the last line `# failures=0`, and 30 lines that start with `trial,` ... |
| 1081 | `          all(line.endswith(",pass") for line in trial_lines) and` | Continues the check: ... every such line ends with `,pass` ... |
| 1082 | `          len([x for x in trial_lines if x.startswith("trial,hot copy: ")]) == 8 and` | Continues the check: ... 8 of them start with `trial,hot copy: ` ... |
| 1083 | `          len([x for x in trial_lines if x.startswith("trial,hot touch: ")]) == 3, (rc, err, len(trial_lines)))` | Continues the check: ... and 3 start with `trial,hot touch: `. The fixed counts show that no check of the self-test was lost. On a failure the status, the error output and the count are printed. |
| 1084 | `    out8 = run(["--selftest"], binary=E.bin8)[1]` | `out8`: the self-test output of the local build of the accepted runner. |
| 1086 | `    def kernel_checks(text, k):` | Starts the inner function `kernel_checks`. It returns the checks that a self-test output holds for the kernel `k`. |
| 1087 | `        return sorted(",".join(line.split(",")[1:]) for line in text.splitlines() if line.startswith(k + ","))` | Returns these checks as a sorted list. It takes the lines that start with the kernel name and a comma and removes the name. What is left of each line is the check, the byte count and the result. |
| 1089 | `    want = kernel_checks(out8, "asmread")` | `want`: the checks of `asmread` in the output of the accepted runner. |
| 1090 | `    check("selftest: asmread has 8 checks in the accepted runner (the reference for the next check)",` | Check: `asmread` has 8 checks in the accepted runner, and all pass. They are the reference for the next check. |
| 1091 | `          len(want) == 8 and all(x.endswith(",pass") for x in want), want)` | Continues the check: the count and the results. |
| 1092 | `    for k in NEW_KERNELS:` | Loops over the 5 kernels of round 3. |
| 1093 | `        check("selftest: %s gets the 8 checks of a read kernel, all pass" % k, kernel_checks(out, k) == want, kernel_checks(out, k))` | Check: the kernel `k` gets the same 8 checks as `asmread`, and all pass. By the description in the self-test file, a read kernel must leave the buffer unchanged, must touch no page outside its range and must touch every page inside it. So each added kernel is proven to read the range for which the runner counts its bytes. |
| 1094 | `    # the self-test must fail on a broken wrapper: a build that counts one pass too many per clock read` | Comment: the self-test must fail on a broken wrapper, a build that counts one pass too many per clock read. A wrapper here is the code of the runner around the kernel call. |
| 1095 | `    with open(os.path.join(HERE, "bwx10.c")) as f:` | Opens `bwx10.c`. |
| 1096 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 1097 | `    good = "        x->bytes = bytes;\n"` | `good`: the source line that stores the byte total of a window, `x->bytes = bytes;`. |
| 1098 | `    n = 0` | `n`: a counter for the names of the build folders. |
| 1099 | `    for fn, own in (("timed_sequence", "trial,every window lasts"), ("timed_sequence_hot", "trial,hot copy: every window lasts")):` | Loops over the two timed functions. `own` is the start of the self-test lines of that function: `trial,every window lasts` for `timed_sequence` and `trial,hot copy: every window lasts` for `timed_sequence_hot`. |
| 1100 | `        for name, bad in (("a window that counts 256 bytes too many", "        x->bytes = bytes + 256;\n"),` | Loops over two defects. Defect 1: the stored byte total of a window is 256 bytes too high. The comment of line 1094 names another defect, one pass too many per clock read. The code does not build that one. |
| 1101 | `                          ("a window whose end is before its start", "        x->bytes = bytes; t1 = t0 - 1;\n")):` | Defect 2: the byte total is right, but the end time of the window is set to 1 ns before its start time. |
| 1102 | `            n += 1` | Counts the build. |
| 1103 | `            d = os.path.join(E.tmp, "broken%d" % n)` | `d`: the folder `broken` plus the number in the temporary folder. |
| 1104 | `            os.makedirs(d, exist_ok=True)` | Creates it. |
| 1105 | `            changed = replace_in(src, fn, good, bad)` | `changed`: the source with the defect in the function `fn`, or `None` when the line was not found exactly once. |
| 1106 | `            with open(os.path.join(d, "bwx10.c"), "w") as f:` | Opens `bwx10.c` in that folder for writing. |
| 1107 | `                f.write(changed or "")` | Writes the changed source, or an empty text when the defect could not be put in. |
| 1108 | `            shutil.copy(os.path.join(HERE, "bwx10_selftest.c"), d)` | Copies `bwx10_selftest.c` into the folder. |
| 1109 | `            ok = changed is not None and subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx10"), os.path.join(d, "bwx10.c")]).returncode == 0` | `ok`: true when the defect was put in and `gcc` built the copy with exit status 0. |
| 1110 | `            rc, out, _ = run(["--selftest"], binary=os.path.join(d, "bwx10"))` | Runs the self-test of that build. When the build failed, the binary does not exist, and this call raises a Python error. |
| 1111 | `            fails = [x for x in out.splitlines() if x.endswith(",FAIL")]` | `fails`: the lines of its output that end with `,FAIL`. |
| 1112 | `            check("selftest: status 1 for a build with %s in %s, and the failed checks are those of that function" % (name, fn),` | Check: the self-test ends with status 1 for a build with that defect in `fn`, and the failed checks are those of that function. |
| 1113 | `                  ok and rc == 1 and any(x.startswith(own) or x.startswith(own.replace("lasts", "holds")) for x in fails) and` | Continues the check: the build worked, the status is 1, and one failed line starts with `own`, or with `own` with the word `holds` in place of `lasts`. Defect 1 fails the check that every window holds whole passes. Defect 2 fails the check that every window lasts its requested time. |
| 1114 | `                  all(x.startswith("trial,hot ") if fn == "timed_sequence_hot" else not x.startswith("trial,hot copy: ") for x in fails),` | Continues the check: for `timed_sequence_hot` every failed line must start with `trial,hot `. For `timed_sequence` no failed line may start with `trial,hot copy: `. So the self-test shows which of the two functions counts wrongly. |
| 1115 | `                  (rc, fails))` | Continues the check: the status and the failed lines as the detail. |
| 1116 | `    b = mutant_build(HOT_READ_MUTANT, "hotread")` | `b`: a build in which `timed_sequence_hot` reads the pass count from the window record after every pass (line 427). |
| 1117 | `    rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1118 | `    fails = [x for x in out.splitlines() if x.endswith(",FAIL")]` | `fails`: the lines of that output that end with `,FAIL`. |
| 1119 | `    check("selftest: status 1 for a build where %s: the touch test sees it on the machine code" % HOT_READ_MUTANT,` | Check: the self-test ends with status 1 for that build. The touch test finds the defect in the machine code. |
| 1120 | `          rc == 1 and fails == ["trial,hot touch: timed_sequence_hot does not touch the window record between the first "` | Continues the check: the only failed line is the check that `timed_sequence_hot` does not touch the window record between the first ... |
| 1121 | `                                "and the last pass,0,FAIL"], (rc, fails))` | Continues the check: ... and the last pass. By the description in the self-test file, the touch test puts the window record into a memory page of its own, makes that page unusable for 20 ms while a window runs, and counts the faults. It runs the compiled code, so it also finds a read that the source text does not show. |

### `test_selftest_rows`, `run_listing` and `shift_block` (lines 1124 to 1150)

| Line | Source | Explanation |
|---:|---|---|
| 1124 | `def test_selftest_rows():` | Starts the test `test_selftest_rows`. |
| 1125 | `    """the row checks of the self-test fail on a build that prints a wrong value"""` | Description text: the row checks of the self-test must fail on a build that prints a wrong value. |
| 1126 | `    for n, name in enumerate(ROW_MUTANTS):` | Loops over the defects of the output rows, `ROW_MUTANTS` (line 435). |
| 1127 | `        b = mutant_build(name, "row%d" % n)` | `b`: a build of the runner with that defect. |
| 1128 | `        rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1129 | `        check("selftest: status 1 for a build with " + name, rc == 1 and ",FAIL" in out, rc)` | Check: the self-test ends with status 1 and prints a line with `,FAIL`. The self-test lets the runner print the rows of a record with known values and compares the text. So a runner that prints a wrong field, for example the wall time as CPU time, does not pass its own self-test. |
| 1132 | `def run_listing(args):` | Starts the function `run_listing`. It runs the listing check with the arguments `args`. |
| 1133 | `    r = subprocess.run([sys.executable, os.path.join(HERE, "check_listing10.py")] + args, stdout=subprocess.PIPE,` | Starts `check_listing10.py` with the Python interpreter that runs this test. |
| 1134 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that starts the listing check: the error output goes into the standard output, and the result is text. |
| 1135 | `    return r.returncode, r.stdout` | Returns the exit status and the output. |
| 1138 | `def shift_block(text, binary, kernel, by):` | Starts the function `shift_block`. It moves one kernel of a listing text to other addresses. |
| 1139 | `    """adds 'by' to every address of one '=== binary kernel ===' block of a listing"""` | Description text: it adds `by` to every address of one block of a listing. A block starts with a head line `=== binary kernel ===`. |
| 1140 | `    out, inside = [], False` | `out`: the new lines. `inside`: whether the current line belongs to the block to move. |
| 1141 | `    for line in text.split("\n"):` | Loops over the lines of the listing. |
| 1142 | `        if line.startswith("==="):` | A line that starts with `===` is the head line of a block. |
| 1143 | `            inside = line == "=== %s %s ===" % (binary, kernel)` | `inside` is true from the head line of the wanted binary and kernel on, and false from every other head line on. |
| 1144 | `        elif inside:` | For a line inside the wanted block: |
| 1145 | `            line = re.sub(r"^(\s*)([0-9a-f]+)(:\| <)", lambda m: "%s%0*x%s" % (m.group(1), len(m.group(2)), int(m.group(2), 16) + by, m.group(3)), line)` | Adds `by` to the address at the start of the line. The pattern matches optional spaces, a hex number and then a colon (an instruction line) or a space with `<` (the line with the function name). The new number gets the same number of digits. |
| 1146 | `            line = re.sub(r"\b([0-9a-f]+) <k_", lambda m: "%x <k_" % (int(m.group(1), 16) + by), line)` | Adds `by` to every branch target of the form hex number, space, `<k_`. So a branch inside the kernel still points to the same instruction. |
| 1147 | `        out.append(line)` | Adds the line to `out`. |
| 1148 | `    return "\n".join(out)` | Returns the lines as one text. |

### Synthetic listings of the new kernels: `synth`, `pf_body`, `synth_new` (lines 1151 to 1191)

| Line | Source | Explanation |
|---:|---|---|
| 1151 | `LDP8 = ["ldp\tq0, q1, [x0]", "ldp\tq2, q3, [x0, #32]", "ldp\tq4, q5, [x0, #64]", "ldp\tq6, q7, [x0, #96]",` | `LDP8`: the 8 load instructions of the `asmread` loop, written as `objdump` prints them, with a tab after the instruction name. Each `ldp` loads two 16-byte vector registers from the address in `x0` plus an offset. The first four cover the offsets 0 to 127. |
| 1152 | `        "ldp\tq8, q9, [x0, #128]", "ldp\tq10, q11, [x0, #160]", "ldp\tq12, q13, [x0, #192]", "ldp\tq14, q15, [x0, #224]"]` | Continues line 1151: the last four loads, for the offsets 128 to 255. Together the 8 instructions load 256 bytes. |
| 1153 | `SAVES = ["stp\td8, d9, [sp, #-64]!", "add\tx1, x0, x1, lsl #3", "stp\td10, d11, [sp, #16]", "stp\td12, d13, [sp, #32]",` | `SAVES`: the 5 instructions before the loop. Four `stp` instructions store the registers `d8` to `d15` on the stack. The second instruction, `add x1, x0, x1, lsl #3`, computes the end pointer: the start address plus 8 times the number of words. |
| 1154 | `         "stp\td14, d15, [sp, #48]"]` | Continues line 1153: the last of the four stores. |
| 1155 | `RESTORES = ["ldp\td10, d11, [sp, #16]", "ldp\td12, d13, [sp, #32]", "ldp\td14, d15, [sp, #48]", "ldp\td8, d9, [sp], #64"]` | `RESTORES`: the 4 `ldp` instructions after the loop. They load `d8` to `d15` back from the stack. |
| 1158 | `def synth(kernel, start, head, body, tail=("ret",), binary="bwx10"):` | Starts the function `synth`. It writes the listing of one kernel as text, from lists of instructions. |
| 1159 | `    """(listing block, offsets row) of a kernel as build10.sh writes them on AArch64: head, loop body, the loop` | Description text: the result is the listing block and the offsets row of a kernel, in the form in which `build10.sh` writes them on AArch64. The parts are the head, the loop body, the loop ... |
| 1160 | `    branch, tail. The loop start is start + 4 * len(head)."""` | Description text: ... branch and the tail. The loop starts 4 bytes per head instruction after the start of the function. |
| 1161 | `    loop = start + 4 * len(head)` | `loop`: the address of the loop start. |
| 1162 | `    insns = list(head) + list(body) + ["b.cc\t%x <k_%s+0x%x>  // b.lo, b.ul, b.last" % (loop, kernel, loop - start)] + list(tail)` | `insns`: all instructions of the function: the head, the loop body, the loop branch and the tail. The loop branch is `b.cc` to the loop start, written as `objdump` writes it: the address, the function name with the offset in angle brackets, and a comment with other names of the same instruction. One of them is `b.lo`, the name that the source of the runner uses. |
| 1163 | `    text = "=== %s %s ===\n%016x <k_%s>:\n" % (binary, kernel, start, kernel)` | `text`: the block starts with the head line `=== binary kernel ===` and the line with the start address as 16 hex digits and the function name, `k_` plus the kernel name. |
| 1164 | `    text += "".join("    %x:\t%s\n" % (start + 4 * i, x) for i, x in enumerate(insns)) + "\n"` | Adds one line per instruction: 4 spaces, the address in hex, a colon, a tab and the instruction. The addresses rise by 4 bytes. An empty line ends the block. |
| 1165 | `    return text, "%s\t%s\tk_%s\t%x\t%x\t%d\n" % (binary, kernel, kernel, start, loop, loop % 64)` | Returns the block and the row for `offsets.tsv`: the binary, the kernel, the function name, the start address, the loop start and the loop start modulo 64, separated by tabs. |
| 1168 | `def pf_body(d, step=64):` | Starts the function `pf_body`. It builds the loop body of a prefetch kernel. `d` is the prefetch distance in bytes. `step` is the distance between two prefetch addresses, 64 bytes by default. |
| 1169 | `    return LDP8 + ["prfm\tpldl1keep, [x0, #%d]" % (d + step * i) for i in range(4)] + ["add\tx0, x0, #0x100", "cmp\tx0, x1"]` | Returns the body: the 8 loads of `LDP8`, then 4 instructions `prfm pldl1keep` at the offsets `d`, `d + 64`, `d + 128` and `d + 192` from `x0`, then `add`, which moves the pointer `x0` forward by 0x100 bytes (256), and `cmp`, which compares it with the end pointer `x1`. `prfm pldl1keep` is a software prefetch: it asks the processor to bring a line into the first-level data cache, and it loads no data. So one loop pass loads 256 bytes and prefetches the 4 lines of 64 bytes that start `d` bytes ahead. |
| 1172 | `PL_BODY = ["ldr\tq0, [x0]", "ldr\tq1, [x0, #64]", "ldr\tq2, [x0, #128]", "ldr\tq3, [x0, #192]", "add\tx0, x0, #0x100", "cmp\tx0, x1"]` | `PL_BODY`: the loop body of `read_1pl`. Four `ldr` instructions each load one 16-byte vector register, from the offsets 0, 64, 128 and 192. So the loop loads the first 16 bytes of each of the 4 lines of 64 bytes. Then `add` moves the pointer `x0` forward by 256 bytes, and `cmp` compares it with the end pointer `x1`. |
| 1175 | `def synth_new(change=None):` | Starts the function `synth_new`. It builds the listing text and the offsets rows of the five new kernels. |
| 1176 | `    """the 5 new kernels, well formed, at addresses after the last kernel of the reference. change: {kernel: (start,` | Description text: without an argument the five kernels are well formed and lie at addresses after the last kernel of the reference. `change` maps a kernel name to its own start ... |
| 1177 | `    head, body, tail)} replaces the parts of single kernels. Returns (listing text, offsets rows)."""` | Description text: ... head, body and tail, and so replaces the parts of single kernels. The result is the listing text and the offsets rows. |
| 1178 | `    parts = {"read_pf256": (0x4a80, SAVES, pf_body(256), RESTORES + ["ret"]),` | `parts`: for each new kernel its start address, its head, its loop body and its tail. `read_pf256` starts at 0x4a80, a multiple of 64. Its head is `SAVES`, its body prefetches 256 bytes ahead, and its tail is `RESTORES` plus `ret`. With the 5 head instructions the loop starts 20 bytes later, at 20 modulo 64. |
| 1179 | `             "read_pf512": (0x4b00, SAVES, pf_body(512), RESTORES + ["ret"]),` | `read_pf512`: the start 0x4b00, a multiple of 64, and the body that prefetches 512 bytes ahead. |
| 1180 | `             "read_pf1024": (0x4b80, SAVES, pf_body(1024), RESTORES + ["ret"]),` | `read_pf1024`: the start 0x4b80, a multiple of 64, and the body that prefetches 1024 bytes ahead. |
| 1181 | `             "read_pf2048": (0x4c00, SAVES, pf_body(2048), RESTORES + ["ret"]),` | `read_pf2048`: the start 0x4c00, a multiple of 64, and the body that prefetches 2048 bytes ahead. |
| 1182 | `             "read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], PL_BODY, ["ret"])}` | `read_1pl`: the start 0x4c90, which is 16 modulo 64. Its head is the one instruction that computes the end pointer. So the loop starts 4 bytes later, at 20 modulo 64. Its body is `PL_BODY`, and its tail is `ret` alone. The loop uses the registers `q0` to `q3` only, so the function has no register to store before the loop and to load after it. |
| 1183 | `    parts.update(change or {})` | Replaces the parts of single kernels by those of `change`, when it is given. |
| 1184 | `    text = offs = ""` | `text`, `offs`: the listing text and the offsets rows, both empty at the start. |
| 1185 | `    for k in NEW_KERNELS:` | Loops over the five new kernels. |
| 1186 | `        if parts[k] is not None:` | A kernel whose parts are `None` is left out. So a test can build a listing that lacks one kernel. |
| 1187 | `            t, o = synth(k, *parts[k])` | `t`, `o`: the block and the offsets row of the kernel, from `synth`. |
| 1188 | `            text, offs = text + t, offs + o` | Appends both to the results. |
| 1189 | `    return text, offs` | Returns the listing text and the offsets rows. |

### `test_listing_saved`: the listing check on a good listing (lines 1192 to 1218)

| Line | Source | Explanation |
|---:|---|---|
| 1192 | `def test_listing_saved():` | Starts the test `test_listing_saved`. The names of its checks start with `listing:`. |
| 1193 | `    """check_listing10.py on the accepted listing of bwx8 (ref-bwx8) plus synthetic new kernels, and on changed copies"""` | Description text: the test runs `check_listing10.py` on the accepted listing of `bwx8` (folder `ref-bwx8`) plus synthetic new kernels, and on changed copies. |
| 1194 | `    with open(os.path.join(REF, "listing.txt")) as f:` | Opens `listing.txt` in the folder `REF`. It is the machine-code listing of the accepted build of `bwx8`. |
| 1195 | `        old_listing = f.read().replace("=== %s " % B8, "=== bwx10 ")` | `old_listing`: that listing with the binary name `bwx10` in place of `bwx8` in every head line. It represents a build of `bwx10` whose 21 older kernels are exactly the accepted ones. |
| 1196 | `    with open(os.path.join(REF, "offsets.tsv")) as f:` | Opens `offsets.tsv` in the folder `REF`. It is the offsets table of that build. It has one row per kernel with the start address, the loop start and the loop start modulo 64. |
| 1197 | `        old_offs = f.read().replace("\n%s\t" % B8, "\nbwx10\t")` | `old_offs`: that table with the binary name `bwx10` in place of `bwx8` at the start of every row. |
| 1198 | `    new_text, new_offs = synth_new()` | `new_text`, `new_offs`: the well-formed synthetic listing of the new kernels and its offsets rows, from `synth_new`. |
| 1199 | `    listing, offs = old_listing + new_text, old_offs + new_offs` | `listing`, `offs`: the complete good listing and the complete offsets table of this test. |
| 1200 | `    d = os.path.join(E.tmp, "listing")` | `d`: the folder `listing` in the temporary folder. |
| 1201 | `    os.makedirs(d, exist_ok=True)` | Creates it. No error when it exists. |
| 1203 | `    def case(name, want_rc, new_listing, new_offs=offs, want_text=None, extra=None):` | Starts the inner function `case`. It writes a listing and an offsets table to files, runs the listing check on them and checks the result. `want_rc` is the expected exit status. `want_text` is a text that the output must hold. `extra` holds added arguments. |
| 1204 | `        with open(os.path.join(d, "listing.txt"), "w") as f:` | Opens `listing.txt` in the folder `d` for writing. |
| 1205 | `            f.write(new_listing)` | Writes the listing of this case. |
| 1206 | `        with open(os.path.join(d, "offsets.tsv"), "w") as f:` | Opens `offsets.tsv` in the folder `d` for writing. |
| 1207 | `            f.write(new_offs)` | Writes the offsets table of this case. |
| 1208 | `        rc, out = run_listing([os.path.join(d, "listing.txt")] + (extra or []))` | Runs the listing check on the listing file. It finds the offsets table beside it. |
| 1209 | `        check("listing: " + name, rc == want_rc and (want_text is None or want_text in out), "rc=%d %s" % (rc, out[-400:]))` | Check: the exit status is the expected one, and the output holds the expected text when one is given. On a failure the status and the last 400 characters of the output are printed. |
| 1210 | `        return out` | Returns the output, for further checks. |
| 1212 | `    out = case("the accepted listing under the name bwx10 plus 5 well-formed new kernels passes (exit 0)", 0, listing)` | Case: the accepted listing under the name `bwx10`, plus 5 well-formed new kernels, passes with exit status 0. This is the listing of a good build. |
| 1213 | `    check("listing: 21 kernels compared, 21 rows ok; 5 new kernels, 5 rows ok",` | Check: 21 kernels were compared and 21 rows are ok. 5 new kernels were checked and 5 rows are ok. |
| 1214 | `          out.count("\tsame\tok") == 21 and out.count("\texpected\tok") == 5 and` | Continues the check: 21 rows end with the columns `same` and `ok`. That is part 1 of the listing check: the text of a kernel equals the reference. 5 rows end with `expected` and `ok`. That is part 2: the loop of a new kernel is the expected one. |
| 1215 | `          "kernels=21 failed_rows=0 new_kernels=5 new_failed_rows=0" in out, out[-200:])` | Continues the check: the summary line holds `kernels=21 failed_rows=0 new_kernels=5 new_failed_rows=0`. |
| 1216 | `    check("listing: the synthetic new kernels have their loop at 20 modulo 64, as asmread",` | Check: the synthetic new kernels have their loop at 20 modulo 64, as `asmread` has. |
| 1217 | `          [r.split("\t")[5] for r in new_offs.splitlines()] == ["20"] * 5 and "bwx10\tasmread\tk_asmread\t4140\t4154\t20" in offs)` | Continues the check: the sixth column of each of the 5 synthetic offsets rows is `20`, and the offsets table holds the row of `asmread` with the start 4140, the loop start 4154 and the offset 20. |

### `test_listing_saved`: part 1 of the listing check must reject changed kernels (lines 1219 to 1275)

| Line | Source | Explanation |
|---:|---|---|
| 1219 | `    # ---- the checks of check_listing8.py, on the 21 kernels of the reference ----` | Comment: the cases for part 1 of the listing check follow. They are the checks of `check_listing8.py`, the listing check of the accepted runner, on the 21 kernels of the reference. |
| 1220 | `    one = "ldp\tq29, q28, [x0, #32]"` | `one`: one load instruction of the kernel `read`, as the listing prints it. A case below changes it. |
| 1221 | `    check("listing: the instruction to change stands once in k_read of bwx10",` | Check: the instruction to change stands once in `k_read` of `bwx10`. |
| 1222 | `          listing.split("=== bwx10 read ===")[1].split("===")[0].count(one) == 1)` | Continues the check: the count in the block of `read` is 1. So the change below changes exactly one place. |
| 1223 | `    head, rest = listing.split("=== bwx10 read ===")` | `head`, `rest`: the listing before and after the head line of the kernel `read`. |
| 1224 | `    case("one changed instruction in k_read fails (exit 1)", 1,` | Case: one changed instruction in the kernel `read` must fail with exit status 1. |
| 1225 | `         head + "=== bwx10 read ===" + rest.replace(one, "ldp\tq29, q28, [x0, #48]", 1), want_text="read\t4020\t4024\t36\t36\tDIFFERS\tFAIL")` | Continues the case: the offset of that load is 48 in place of 32. The output must hold the row of `read` with the start 4020, the loop start 4024, the loop offset 36 in both columns, the text column `DIFFERS` and the result `FAIL`. The place of the loop is unchanged. Only the comparison of the instructions finds this defect. |
| 1226 | `    check("listing: the loop start of k_asmread stands once", listing.count("    4154:\tldp\tq0, q1, [x0]") == 1)` | Check: the first instruction of the loop of `k_asmread`, at the address 4154, stands once in the listing. So the next case changes exactly one place. |
| 1227 | `    case("one added nop before the loop of k_asmread fails", 1,` | Case: one added `nop` before the loop of `k_asmread` must fail. |
| 1228 | `         listing.replace("    4154:\tldp\tq0, q1, [x0]", "    4150:\tnop\n    4154:\tldp\tq0, q1, [x0]", 1), want_text="asmread")` | Continues the case: a line with a `nop` at the address 4150 is put before the loop start. The function text then has one instruction more than the reference. The output must name `asmread`. |
| 1229 | `    shifted = shift_block(listing, "bwx10", "asmread", 4)` | `shifted`: the listing with every address of `k_asmread` moved up by 4 bytes (line 1138). |
| 1230 | `    offs_shifted = offs.replace("bwx10\tasmread\tk_asmread\t4140\t4154\t20", "bwx10\tasmread\tk_asmread\t4144\t4158\t24")` | `offs_shifted`: the offsets table with the row of `asmread` moved in the same way: start 4144, loop start 4158, offset 24. |
| 1231 | `    check("listing: the shifted copy differs from the saved one", shifted != listing and offs_shifted != offs)` | Check: the shifted copy differs from the saved one. So the next cases test a changed input. |
| 1232 | `    out = case("k_asmread shifted by 4 bytes, same text, fails on the loop offset (exit 1)", 1, shifted, offs_shifted,` | Case: `k_asmread` shifted by 4 bytes, with the same text, must fail on the loop offset with exit status 1. |
| 1233 | `               want_text="asmread\t4144\t4158\t24\t20\tsame\tFAIL: loop offset modulo 64 is 24, reference 20")` | Continues the case: the expected row of `asmread`: start 4144, loop start 4158, loop offset 24 against 20 in the reference, the text column `same`, and the result `FAIL: loop offset modulo 64 is 24, reference 20`. The instructions are equal. Only the place of the loop inside a 64-byte block differs. The design asks to keep the loop offsets modulo 64. |
| 1234 | `    check("listing: with k_asmread shifted, every new kernel fails too: its loop offset is compared with asmread",` | Check: with `k_asmread` shifted, every new kernel fails too: its loop offset is compared with that of `asmread`. |
| 1235 | `          out.count("loop offset modulo 64 is 20, asmread has 24") == 5, out[-300:])` | Continues the check: the text `loop offset modulo 64 is 20, asmread has 24` stands 5 times in the output, once per new kernel. |
| 1236 | `    case("the same shift with an offsets.tsv that still says 20 fails", 1, shifted, want_text="offsets.tsv gives 20")` | Case: the same shifted listing with an offsets table that still says 20 must fail. The output must hold `offsets.tsv gives 20`. So a table that was not updated cannot hide a moved loop. The check computes the loop offset from the listing. |
| 1237 | `    check("listing: the offsets row of k_oldread stands once", offs.count("bwx10\toldread\tk_oldread\t3c80\t3ce8\t40") == 1)` | Check: the offsets row of `k_oldread` (start 3c80, loop start 3ce8, offset 40) stands once in the table. So the next case changes exactly one row. |
| 1238 | `    case("an offsets.tsv row that differs from the listing fails", 1, listing,` | Case: an offsets row that differs from the listing must fail. |
| 1239 | `         offs.replace("bwx10\toldread\tk_oldread\t3c80\t3ce8\t40", "bwx10\toldread\tk_oldread\t3c80\t3ce8\t0"), want_text="offsets.tsv gives 0")` | Continues the case: the last column of the row of `oldread` is 0 in place of 40. The output must hold `offsets.tsv gives 0`. |
| 1240 | `    whole = listing` | `whole`: a copy of the listing, for the next case. |
| 1241 | `    for k in re.findall(r"=== bwx10 (\S+) ===", listing):` | Loops over the names of all kernels of `bwx10` in the listing. The pattern finds the kernel name in each head line. |
| 1242 | `        whole = shift_block(whole, "bwx10", k, 0x1040)` | Moves the block of the kernel up by 0x1040 bytes. That is 65 times 64. |
| 1243 | `    check("listing: the moved copy differs and holds 26 kernels", whole != listing and len(re.findall(r"=== bwx10 (\S+) ===", listing)) == 26)` | Check: the moved copy differs from the listing, and the listing holds 26 kernels. So the next case tests a changed input that holds every kernel. |
| 1244 | `    case("all kernels moved by a multiple of 64 bytes pass: addresses are not compared", 0, whole)` | Case: a listing in which all kernels are moved by a multiple of 64 bytes passes. The listing check does not compare addresses. It compares the instructions and the loop offset modulo 64, and such a move changes neither. |
| 1245 | `    block = listing.split("=== bwx10 read_sparse ===")[1].split("===")[0]` | `block`: the text of the block of the kernel `read_sparse`. |
| 1246 | `    case("a listing without k_read_sparse fails", 1, listing.replace("=== bwx10 read_sparse ===" + block, ""), want_text="no listing or no loop")` | Case: a listing without `k_read_sparse` must fail. The output must hold `no listing or no loop`. A build that lacks a kernel of the reference is not accepted. |
| 1247 | `    case("a listing with a kernel that the reference lacks and that is not a kernel of round 3 fails", 1,` | Case: a listing with a kernel that the reference does not have, and that is no kernel of round 3, must fail. |
| 1248 | `         listing + "\n=== bwx10 read_new ===\n" + block, want_text="read_new")` | Continues the case: a block with the kernel name `read_new` is added. The output must name `read_new`. |
| 1249 | `    got = "ldr\tx3, [x3, #4072]"` | `got`: a load instruction of the old read kernel, as the listing prints it. With the `adrp` instruction before it, it loads a pointer from the table of global addresses of the binary, here at the offset 4072. The linker sets the place of a pointer in that table. |
| 1250 | `    check("listing: the pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got) == 2)` | Check: this pointer load stands exactly 2 times in the listing. The name of the check says that the two places are `k_oldread` and `k_oldread2`. The condition counts the whole listing and does not test the kernels. |
| 1251 | `    got0 = "ldr\tx0, [x0, #4072]"` | `got0`: the second pointer load of that kind, through the register `x0`. |
| 1252 | `    check("listing: the second pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got0) == 2)` | Check: it also stands 2 times in the listing. |
| 1253 | `    out = case("another place of the stack-guard pointer in the table of the linker, the same in all four loads, "` | Case: another place of the stack-guard pointer in the table of the linker, the same in all four loads, ... |
| 1254 | `               "passes with a note", 0, listing.replace(got, "ldr\tx3, [x3, #4064]").replace(got0, "ldr\tx0, [x0, #4064]"),` | Continues the case: ... passes with a note. All four loads get the offset 4064 in place of 4072. |
| 1255 | `               want_text="\tsame\tNOTE: got_offset_differs (4064,4064, reference 4072,4072)")` | Continues the case: the output must hold a row with the text column `same` and the result `NOTE: got_offset_differs (4064,4064, reference 4072,4072)`. The offset is set by the linker and is no part of the read loop. So the listing check accepts it, and it prints a note for a person to read. |
| 1256 | `    check("listing: the two rows with the note do not print a plain ok", out.count("\tsame\tok") == 19, out[-300:])` | Check: the two rows with the note do not print a plain `ok`. Only 19 rows end with `same` and `ok`: the 21 kernels of the reference without these two. |
| 1257 | `    adrp, stub = "adrp\tx3, 2f000 <__FRAME_END__+0x1e454>", "bl\t1ed0 <__stack_chk_fail@plt>"` | `adrp`: the instruction that gives the page of the table. `stub`: the call of `__stack_chk_fail`, the function for a failed stack guard. |
| 1258 | `    check("listing: the adrp before that load and the call of the stack-guard failure stand in k_oldread and k_oldread2",` | Check: the `adrp` before that load and the call of the stack-guard failure stand in `k_oldread` and `k_oldread2`. |
| 1259 | `          listing.count(adrp) == 2 and listing.count(stub) == 2)` | Continues the check: each of the two texts stands 2 times in the listing. |
| 1260 | `    case("the first pointer load of k_oldread from another page of the table fails (exit 1)", 1,` | Case: the first pointer load of `k_oldread` from another page of the table must fail with exit status 1. |
| 1261 | `         listing.replace(adrp, "adrp\tx3, 2a000 <some_other_table>", 1), want_text="use 2 places of the table")` | Continues the case: the first `adrp` gets another page and another symbol name. The output must hold `use 2 places of the table`. A kernel that loads from a second place of the table loads another pointer than the reference does. |
| 1262 | `    case("the first pointer load of k_oldread from another offset fails", 1,` | Case: the first pointer load of `k_oldread` from another offset must fail. |
| 1263 | `         listing.replace(got, "ldr\tx3, [x3, #8]", 1), want_text="use 2 places of the table")` | Continues the case: the first load gets the offset 8. The output must hold `use 2 places of the table`. |
| 1264 | `    case("k_oldread2 with its two pointer loads from another place than k_oldread fails", 1,` | Case: `k_oldread2` with its two pointer loads from another place than `k_oldread` must fail. |
| 1265 | `         "=== bwx10 oldread2 ===".join([listing.split("=== bwx10 oldread2 ===")[0],` | Continues the case: the listing is cut at the head line of `oldread2` and joined again. The part before it stays as it is ... |
| 1266 | `                                        listing.split("=== bwx10 oldread2 ===")[1].replace("[x3, #4072]", "[x3, #16]", 1)` | Continues the case: ... and in the part after it the first load through `x3` gets the offset 16 ... |
| 1267 | `                                        .replace("[x0, #4072]", "[x0, #16]", 1)]),` | Continues the case: ... and the first load through `x0` gets the offset 16 too. |
| 1268 | `         want_text="over all kernels")` | Continues the case: the output must hold `over all kernels`. Each function alone uses one place of the table, but the two functions together use two. |
| 1269 | `    case("a call of another function in place of the stack-guard failure fails", 1,` | Case: a call of another function in place of the stack-guard failure must fail. |
| 1270 | `         listing.replace(stub, "bl\t9999 <abort@plt>", 1), want_text="DIFFERS")` | Continues the case: the first call of `__stack_chk_fail` becomes a call of `abort`. The output must hold `DIFFERS`. A target outside the function is compared by its symbol name. |
| 1271 | `    check("listing: the load from the stack to change stands in k_oldread and k_oldread2", listing.count("ldr\tx2, [sp, #136]") == 2)` | Check: the load from the stack to change, `ldr x2` with the offset 136, stands exactly 2 times in the listing. The name of the check says that the two places are `k_oldread` and `k_oldread2`. The condition counts the whole listing and does not test the kernels. |
| 1272 | `    case("another offset in a load from the stack fails", 1, listing.replace("ldr\tx2, [sp, #136]", "ldr\tx2, [sp, #128]", 1),` | Case: another offset in a load from the stack must fail. The first such load gets the offset 128. |
| 1273 | `         want_text="DIFFERS")` | Continues the case: the output must hold `DIFFERS`. |
| 1274 | `    case("a listing with no block of bwx10 cannot be used (exit 2)", 2, listing.replace("=== bwx10 ", "=== other "))` | Case: a listing with no block of `bwx10` cannot be used: exit status 2. Every head line gets the binary name `other`. By the description of the listing check, exit status 2 means that a file could not be used. It is not the status of a failed check, which is 1. |

### `test_listing_saved`: part 2 of the listing check must reject a wrong new kernel (lines 1276 to 1338)

| Line | Source | Explanation |
|---:|---|---|
| 1276 | `    # ---- the 5 new kernels ----` | Comment: the cases for the 5 new kernels follow. They test part 2 of the listing check. |
| 1277 | `    def new_case(name, change, want_text, want_rc=1):` | Starts the inner function `new_case`. It runs one case on the accepted old kernels plus new kernels with a change. |
| 1278 | `        t, o = synth_new(change)` | `t`, `o`: the synthetic listing of the new kernels with the change, and its offsets rows. |
| 1279 | `        return case(name, want_rc, old_listing + t, old_offs + o, want_text=want_text)` | Runs the case and returns the output. The expected exit status is 1 unless the caller gives another one. |
| 1281 | `    full = (SAVES, RESTORES + ["ret"])` | `full`: the complete head and the complete tail of a well-formed prefetch kernel: `SAVES` before the loop, and `RESTORES` plus `ret` after it. |
| 1282 | `    body = pf_body(512)` | `body`: the well-formed loop body of `read_pf512`. |
| 1283 | `    wrong = list(body)` | `wrong`: a copy of that body. |
| 1284 | `    wrong[9] = "prfm\tpldl1keep, [x0, #584]"` | Changes instruction 9 of the copy, the second prefetch. Its offset is 584 in place of 576. |
| 1285 | `    new_case("read_pf512 with one wrong prfm offset (584 in place of 576) fails (exit 1)",` | Case: `read_pf512` with one wrong prefetch offset, 584 in place of 576, must fail with exit status 1. |
| 1286 | `             {"read_pf512": (0x4b00, full[0], wrong, full[1])},` | Continues the case: the kernel has the changed body, at its planned start. |
| 1287 | `             "read_pf512\t4b00\t4b14\t20\t20\tDIFFERS\tFAIL: loop instruction 9 is 'prfm pldl1keep, [x0, #584]', expected "` | Continues the case: the expected row: start 4b00, loop start 4b14, loop offset 20 in both columns, the loop column `DIFFERS`, and a result that says that loop instruction 9 prefetches at the offset 584 ... |
| 1288 | `             "'prfm pldl1keep, [x0, #576]'")` | Continues the case: ... where the offset 576 is expected. Part 2 of the listing check compares every operand of the loop. So a build whose prefetch is not the planned one is rejected. |
| 1289 | `    new_case("read_pf256 with the offsets of read_pf512 fails", {"read_pf256": (0x4a80, full[0], pf_body(512), full[1])},` | Case: `read_pf256` with the prefetch offsets of `read_pf512` must fail. The kernel gets the body with the distance 512. |
| 1290 | `             "read_pf256\t4a80\t4a94\t20\t20\tDIFFERS\tFAIL: loop instruction 8 is 'prfm pldl1keep, [x0, #512]'")` | Continues the case: the expected row: start 4a80, loop start 4a94, loop offset 20 in both columns, the loop column `DIFFERS`, and a result that starts with loop instruction 8, a prefetch at the offset 512. The prefetch distance is what makes one prefetch kernel differ from another. A build with another distance would be measured under a wrong name. |
| 1291 | `    new_case("read_pf1024 with a missing prfm (3 in place of 4) fails",` | Case: `read_pf1024` with 3 prefetch instructions in place of 4 must fail. |
| 1292 | `             {"read_pf1024": (0x4b80, full[0], pf_body(1024)[:11] + pf_body(1024)[12:], full[1])},` | Continues the case: the body lacks instruction 11, the fourth prefetch. |
| 1293 | `             "read_pf1024\t4b80\t4b94\t20\t20\tDIFFERS\tFAIL: loop instruction 11 is 'add x0, x0, #0x100', expected "` | Continues the case: the expected row: start 4b80, loop start 4b94, loop offset 20 in both columns, the loop column `DIFFERS`, and a result that says that loop instruction 11 is the `add` ... |
| 1294 | `             "'prfm pldl1keep, [x0, #1216]'")` | Continues the case: ... where the prefetch at the offset 1216 is expected. With 3 prefetch instructions one of the 4 lines of 64 bytes gets no prefetch. |
| 1295 | `    new_case("read_pf2048 with pldl2keep in place of pldl1keep fails",` | Case: `read_pf2048` with `pldl2keep` in place of `pldl1keep` must fail. `pldl2keep` asks for the line in the second cache level and not in the first one. |
| 1296 | `             {"read_pf2048": (0x4c00, full[0], [x.replace("pldl1keep, [x0, #2112]", "pldl2keep, [x0, #2112]") for x in pf_body(2048)], full[1])},` | Continues the case: in the body the prefetch at the offset 2112 gets the word `pldl2keep`. |
| 1297 | `             "expected 'prfm pldl1keep, [x0, #2112]'")` | Continues the case: the output must say that `prfm pldl1keep` at the offset 2112 is expected. |
| 1298 | `    new_case("read_pf2048 with the prfm before the 8 ldp fails",` | Case: `read_pf2048` with the 4 prefetch instructions before the 8 `ldp` must fail. |
| 1299 | `             {"read_pf2048": (0x4c00, full[0], pf_body(2048)[8:12] + LDP8 + pf_body(2048)[12:], full[1])}, "read_pf2048\t4c00\t4c14\t20\t20\tDIFFERS")` | Continues the case: the body is the 4 prefetch instructions, the 8 loads, `add` and `cmp`. The expected row of `read_pf2048` has the loop offset 20 in both columns and the loop column `DIFFERS`. So the right set of instructions alone does not pass. Their order is checked too. |
| 1300 | `    new_case("read_pf256 with the loop moved by 4 bytes (offsets.tsv agrees with the listing) fails on the loop offset",` | Case: `read_pf256` with the loop moved by 4 bytes must fail on the loop offset. The offsets table agrees with the listing here. |
| 1301 | `             {"read_pf256": (0x4a84, full[0], pf_body(256), full[1])},` | Continues the case: the kernel starts at 0x4a84, 4 bytes after its planned start, with its well-formed parts. |
| 1302 | `             "read_pf256\t4a84\t4a98\t24\t20\texpected\tFAIL: loop offset modulo 64 is 24, asmread has 20")` | Continues the case: the expected row: start 4a84, loop start 4a98, loop offset 24 against 20 of `asmread`, the loop column `expected`, and the result `FAIL: loop offset modulo 64 is 24, asmread has 20`. The loop text is right. Only its place is wrong. |
| 1303 | `    new_case("read_1pl that starts at 0 modulo 64 (loop at 4, as read_sparse) fails on the loop offset",` | Case: `read_1pl` that starts at 0 modulo 64 must fail on the loop offset. Its loop then lies at 4. The name adds that `read_sparse` has its loop there. |
| 1304 | `             {"read_1pl": (0x4c80, ["add\tx1, x0, x1, lsl #3"], PL_BODY, ["ret"])},` | Continues the case: the kernel starts at 0x4c80, a multiple of 64, with its well-formed parts. |
| 1305 | `             "read_1pl\t4c80\t4c84\t4\t20\texpected\tFAIL: loop offset modulo 64 is 4, asmread has 20")` | Continues the case: the expected row: start 4c80, loop start 4c84, loop offset 4 against 20 of `asmread`, and the result `FAIL: loop offset modulo 64 is 4, asmread has 20`. By the comment in `bwx10.c`, the loop of every new kernel is planned at 20 modulo 64, the loop offset of `asmread` in the accepted build. |
| 1306 | `    t, o = synth_new()` | `t`, `o`: the well-formed synthetic kernels and their offsets rows. |
| 1307 | `    case("a new kernel whose offsets.tsv row differs from the listing fails", 1, old_listing + t,` | Case: a new kernel whose offsets row differs from the listing must fail. |
| 1308 | `         old_offs + o.replace("bwx10\tread_1pl\tk_read_1pl\t4c90\t4c94\t20", "bwx10\tread_1pl\tk_read_1pl\t4c90\t4c94\t4"),` | Continues the case: the last column of the row of `read_1pl` is 4 in place of 20. |
| 1309 | `         want_text="read_1pl\t4c90\t4c94\t20\t20\texpected\tFAIL: offsets.tsv gives 4, the listing gives 20")` | Continues the case: the expected row ends with `FAIL: offsets.tsv gives 4, the listing gives 20`. |
| 1310 | `    new_case("read_pf512 without the store of d14 and d15 fails (the loop uses v14 and v15)",` | Case: `read_pf512` without the store of `d14` and `d15` must fail. The loop uses the vector registers `v14` and `v15`. |
| 1311 | `             {"read_pf512": (0x4b04, SAVES[:4], body, full[1])}, "not stored before the loop: [14, 15]")` | Continues the case: the head has only the first 4 instructions of `SAVES`. The function starts 4 bytes later, so the loop start stays at 4b14. The output must hold `not stored before the loop: [14, 15]`. By the description of the listing check, a function must keep `d8` to `d15` for its caller. |
| 1312 | `    new_case("read_pf512 without the load of d8 and d9 after the loop fails",` | Case: `read_pf512` without the load of `d8` and `d9` after the loop must fail. |
| 1313 | `             {"read_pf512": (0x4b00, full[0], body, RESTORES[:3] + ["ret"])}, "not loaded after it: [8, 9]")` | Continues the case: the tail has only the first 3 instructions of `RESTORES`. The output must hold `not loaded after it: [8, 9]`. |
| 1314 | `    new_case("read_1pl with a load at offset 136 in place of 128 fails",` | Case: `read_1pl` with a load at the offset 136 in place of 128 must fail. |
| 1315 | `             {"read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], PL_BODY[:2] + ["ldr\tq2, [x0, #136]"] + PL_BODY[3:], ["ret"])},` | Continues the case: instruction 2 of the loop body is `ldr q2` with the offset 136. |
| 1316 | `             "loop instruction 2 is 'ldr q2, [x0, #136]', expected 'ldr q2, [x0, #128]'")` | Continues the case: the output must say that loop instruction 2 loads from the offset 136 where 128 is expected. With that offset the loop does not load the first 16 bytes of the third line. |
| 1317 | `    new_case("read_1pl with ldp (32 B per line) in place of ldr fails",` | Case: `read_1pl` with `ldp` in place of `ldr` must fail. `ldp` loads two registers. That is 32 bytes of the line and not 16, as the name of the case says. |
| 1318 | `             {"read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], ["ldp\tq0, q1, [x0]"] + PL_BODY[1:], ["ret"])},` | Continues the case: instruction 0 of the loop body is an `ldp` of `q0` and `q1`. |
| 1319 | `             "loop instruction 0 is 'ldp q0, q1, [x0]', expected 'ldr q0, [x0]'")` | Continues the case: the output must say that loop instruction 0 is that `ldp` where the `ldr` of `q0` is expected. The number of bytes that the loop loads per line is what defines this kernel. |
| 1320 | `    new_case("read_1pl with a second backward branch fails",` | Case: `read_1pl` with a second backward branch must fail. |
| 1321 | `             {"read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], PL_BODY, ["cbnz\tx2, 4c94 <k_read_1pl+0x4>", "ret"])},` | Continues the case: the tail gets a `cbnz` instruction that branches back to the loop start. |
| 1322 | `             "FAIL: 2 backward branches, 1 expected")` | Continues the case: the output must hold `FAIL: 2 backward branches, 1 expected`. |
| 1323 | `    new_case("read_1pl with a call after the loop fails",` | Case: `read_1pl` with a call after the loop must fail. |
| 1324 | `             {"read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], PL_BODY, ["bl\t1ed0 <abort@plt>", "ret"])}, "a branch or call beside the loop branch")` | Continues the case: the tail gets a call of `abort`. The output must hold `a branch or call beside the loop branch`. |
| 1325 | `    new_case("read_1pl with another instruction before the loop fails",` | Case: `read_1pl` with another instruction before the loop must fail. |
| 1326 | `             {"read_1pl": (0x4c8c, ["add\tx1, x0, x1, lsl #3", "ldr\tq4, [x0, #4032]"], PL_BODY, ["ret"])},` | Continues the case: the head gets a load, `ldr q4`, as a second instruction. The function starts 4 bytes earlier, so the loop start stays at 4c94. |
| 1327 | `             "is not the end pointer and not a store of d registers")` | Continues the case: the output must hold `is not the end pointer and not a store of d registers`. |
| 1328 | `    new_case("read_1pl that does not end with ret fails",` | Case: `read_1pl` that does not end with `ret` must fail. |
| 1329 | `             {"read_1pl": (0x4c90, ["add\tx1, x0, x1, lsl #3"], PL_BODY, [])}, "the function does not end with ret")` | Continues the case: the tail is empty, so the loop branch is the last instruction. The output must hold `the function does not end with ret`. |
| 1330 | `    hi = old_listing + synth_new()[0].replace("b.cc\t4c94 <k_read_1pl+0x4>", "b.hi\t4c94 <k_read_1pl+0x4>")` | `hi`: the good listing in which the loop branch of `read_1pl` is `b.hi` in place of `b.cc`. |
| 1331 | `    case("read_1pl with b.hi in place of b.cc as its loop branch fails", 1, hi, want_text="the loop branch is 'b.hi")` | Case: `read_1pl` with `b.hi` as its loop branch must fail. The output must hold `the loop branch is 'b.hi`. The source of the kernel asks for `b.lo`, another name of `b.cc`: the loop continues while the pointer is below the end pointer. |
| 1332 | `    new_case("a listing without read_1pl fails", {"read_1pl": None}, "read_1pl\tNA\tNA\tNA\t20\t-\tFAIL: no listing")` | Case: a listing without `read_1pl` must fail. The expected row of `read_1pl` has `NA` in its three columns, 20 as the loop offset of `asmread`, and the result `FAIL: no listing`. |
| 1333 | `    out = case("the accepted listing alone (no new kernel) fails: all 5 new kernels are required", 1, old_listing, old_offs)` | Case: the accepted listing alone, with no new kernel, must fail. All 5 new kernels are required. |
| 1334 | `    check("listing: that run names 5 failed new rows and no failed old row", "failed_rows=0 new_kernels=5 new_failed_rows=5" in out, out[-200:])` | Check: that run names 5 failed new rows and no failed old row. The summary line holds `failed_rows=0 new_kernels=5 new_failed_rows=5`. |
| 1335 | `    out = case("--skip-new: the same listing passes, and the last line says that the new kernels were not checked", 0,` | Case: with `--skip-new` the same listing passes, and the last line says that the new kernels were not checked. |
| 1336 | `               old_listing, old_offs, want_text="new_kernels=NOT CHECKED (--skip-new)", extra=["--skip-new"])` | Continues the case: the listing and the offsets table of the old kernels, the expected text `new_kernels=NOT CHECKED (--skip-new)` and the option. The summary line shows to a reader that part 2 did not run. |

### `test_build_scripts`: the build script stops when the marker file exists (lines 1339 to 1383)

| Line | Source | Explanation |
|---:|---|---|
| 1339 | `def test_build_scripts():` | Starts the test `test_build_scripts`. |
| 1340 | `    """build10.sh on this machine, and check_listing10.py on two real listings of one compiler"""` | Description text: the test runs `build10.sh` on this machine, and `check_listing10.py` on two real listings of one compiler. |
| 1341 | `    cpus = ",".join(str(c) for c in E.allowed)` | `cpus`: the CPUs that the test process may use, as a text with commas. The build script takes it as the CPU list of its own run. |
| 1342 | `    new, old = os.path.join(E.tmp, "new"), os.path.join(E.tmp, "old")` | `new`, `old`: two folders in the temporary folder. `new` is for a build of the runner under test. `old` is for the reference build. |
| 1343 | `    os.makedirs(new)` | Creates the folder `new`. |
| 1344 | `    os.makedirs(old)` | Creates the folder `old`. |
| 1345 | `    for name in ("bwx10.c", "bwx10_selftest.c", "build10.sh"):` | Loops over the three files that a build needs: the source, the self-test file and the build script. |
| 1346 | `        shutil.copy(os.path.join(HERE, name), new)` | Copies the file into the folder `new`. The build script writes only in its own folder. So the test runs a copy, and the folder of the sources stays unchanged. |
| 1347 | `    for name in ("bwx.c", "bwx_selftest.c", "build.sh"):` | Loops over the three files of the first runner: its source, its self-test file and its build script. |
| 1348 | `        shutil.copy(os.path.join(OLD, name), old)` | Copies the file from the folder `OLD` into the folder `old`. The build of line 1432 runs in this copy. Its listing is the reference of the listing comparison. |
| 1349 | `    marker = os.path.join(E.tmp, "marker")` | `marker`: the path of a test marker file in the temporary folder. |
| 1350 | `    open(marker, "w").close()` | Creates that file, empty. |
| 1351 | `    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=marker)` | `env`: the environment for the build script. `BWX_CPUS` holds the CPU list. `BWX_MARKER` holds the path of the test marker file. By the comment in the build script this variable exists only for a test of the marker check. |
| 1352 | `    env.pop("_PINNED", None)` | Removes the variable `_PINNED`, if it is set. The build script sets it when it starts itself again under `taskset`, the tool that sets the CPU list. Without the variable the script does that step. |
| 1353 | `    r = subprocess.run(["bash", os.path.join(new, "build10.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build10.sh` in the folder `new` while the test marker file exists. |
| 1354 | `    check("build10.sh: exit 3 and no file written while the marker file is present",` | Check: `build10.sh` ends with exit status 3 and writes no file while the marker file is present. |
| 1355 | `          r.returncode == 3 and sorted(os.listdir(new)) == ["build10.sh", "bwx10.c", "bwx10_selftest.c"], (r.returncode, os.listdir(new)))` | Continues the check: status 3, and the folder holds only the three copied files. On CRB the marker file exists while another user runs a performance test. A build would use CPU time of that machine. So the script must stop before it compiles. |
| 1356 | `    # The marker file appears while the self-test runs. A script stands for the compiler. The "binary" that it` | Comment: in the next case the marker file appears while the self-test runs. A script replaces the compiler. The fake binary that ... |
| 1357 | `    # writes creates the marker file in its self-test and leaves a file if it is run in any other way.` | Comment: ... it writes creates the marker file in its self-test, and it leaves a file when it is run in any other way. |
| 1358 | `    late = os.path.join(E.tmp, "late")` | `late`: the folder `late` in the temporary folder. |
| 1359 | `    os.makedirs(late)` | Creates it. |
| 1360 | `    for name in ("bwx10.c", "bwx10_selftest.c", "build10.sh"):` | Loops over the three files of a build. |
| 1361 | `        shutil.copy(os.path.join(HERE, name), late)` | Copies the file into the folder `late`. |
| 1362 | `    late_marker, ran = os.path.join(E.tmp, "late-marker"), os.path.join(E.tmp, "late-ran")` | `late_marker`: the path of the marker file of this case. `ran`: the path of a file that shows that the fake binary ran again. |
| 1363 | `    cc = os.path.join(E.tmp, "fake-cc")` | `cc`: the path of the fake compiler, `fake-cc`. |
| 1364 | `    with open(cc, "w") as f:` | Opens it for writing. |
| 1365 | `        f.write('#!/bin/sh\n[ "$1" = --version ] && { echo fake; exit 0; }\n'` | Text of the fake compiler, a shell script. Its first line tells Linux to run it with `sh`. Its second line: when the first argument is `--version`, it prints `fake` and ends with exit status 0. |
| 1366 | `                'while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done\n'` | Text of the fake compiler: a loop over the arguments. When an argument is `-o`, the next one is kept in `out`. That is the path of the binary to write. |
| 1367 | `                'printf \'#!/bin/sh\\nif [ "$1" = --selftest ]; then : > "%s"; echo "# failures=0"; else : > "%s"; fi\\n\' > "$out"\n'` | Text of the fake compiler: it writes the fake binary to that path. The fake binary is a shell script too. Called with `--selftest`, it creates the marker file of this case and prints `# failures=0`, the last line of a passed self-test. Called in any other way, it creates the file `ran`. |
| 1368 | `                'chmod +x "$out"\n' % (late_marker, ran))` | Text of the fake compiler: it makes the fake binary executable. The end of the line puts the two paths into the text above. |
| 1369 | `    os.chmod(cc, 0o755)` | Makes the fake compiler executable (mode 755). |
| 1370 | `    r = subprocess.run(["bash", os.path.join(late, "build10.sh")], env=dict(env, BWX_MARKER=late_marker, CC=cc),` | Runs `build10.sh` in the folder `late`, with the marker path of this case and with the fake compiler in the variable `CC`. |
| 1371 | `                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Continues the call that runs the build script: both outputs are collected. |
| 1372 | `    check("build10.sh: exit 3 and no further run of the binary when the marker file appears during the self-test",` | Check: `build10.sh` ends with exit status 3 and does not run the binary again when the marker file appears during the self-test. |
| 1373 | `          r.returncode == 3 and os.path.exists(late_marker) and os.path.exists(os.path.join(late, "selftest-bwx10.txt")) and` | Continues the check: status 3, the marker file of this case exists, and the file `selftest-bwx10.txt` exists, so the self-test ran ... |
| 1374 | `          not os.path.exists(ran), (r.returncode, os.path.exists(late_marker), os.path.exists(ran), r.stderr[-200:]))` | Continues the check: ... and the file `ran` does not exist. So the script tested the marker file again after the self-test, and it did not start the binary again. Its next step would have run the binary to list the kernels. |
| 1375 | `    env["BWX_MARKER"] = marker + ".none"` | Sets `BWX_MARKER` to a path that does not exist. No marker file is present for the next runs. |
| 1376 | `    r = subprocess.run(["bash", os.path.join(new, "build10.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build10.sh` in the folder `new`. This is a full build on this machine. |
| 1377 | `                       universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1378 | `    made = sorted(os.listdir(new))` | `made`: the sorted names of the files in the folder `new` after the run. |
| 1379 | `    check("build10.sh: exit 0; writes bwx10, build.txt, listing.txt, offsets.tsv, selftest-bwx10.txt, seq-listing.txt",` | Check: `build10.sh` ends with exit status 0 and writes `bwx10`, `build.txt`, `listing.txt`, `offsets.tsv`, `selftest-bwx10.txt` and `seq-listing.txt`. |
| 1380 | `          r.returncode == 0 and made == sorted(["build10.sh", "bwx10.c", "bwx10_selftest.c", "bwx10", "build.txt", "listing.txt",` | Continues the check: status 0, and the folder holds exactly the three copied files plus the binary, the build record, the listing ... |
| 1381 | `                                                "offsets.tsv", "selftest-bwx10.txt", "seq-listing.txt"]), (r.returncode, made, r.stderr[-300:]))` | Continues the check: ... the offsets table, the self-test output and the listing of the timed functions. On a failure the status, the file names and the end of the error output are printed. |
| 1382 | `    if r.returncode != 0:` | Tests whether the build failed. |
| 1383 | `        return` | Ends the test in that case. The next checks read the files of the build. |

### `test_build_scripts`: the build record, and a build that the script must reject (lines 1384 to 1426)

| Line | Source | Explanation |
|---:|---|---|
| 1384 | `    with open(os.path.join(new, "build.txt")) as f:` | Opens `build.txt` in the folder `new`. |
| 1385 | `        build = f.read()` | `build`: the whole build record. |
| 1386 | `    with open(os.path.join(OLD, "build.sh")) as f:` | Opens `build.sh`, the build script of the first runner. |
| 1387 | `        old_flags = re.search(r'^CFLAGS="(.*)"$', f.read(), re.M).group(1)` | `old_flags`: the compiler flags of that script. The pattern takes the text between the double quotes of the line that starts with `CFLAGS=`. |
| 1388 | `    check("build10.sh: build.txt holds the CFLAGS of build.sh, no compiler message, the self-test result and 7 digests",` | Check: `build.txt` holds the `CFLAGS` of `build.sh`, no compiler message, the self-test result and 7 checksums. |
| 1389 | `          "## CFLAGS=%s\n" % old_flags in build and "## compiler messages:\n## compiler messages end\n" in build and` | Continues the check: the record holds a line `## CFLAGS=` with exactly these flags, and the line `## compiler messages:` is followed directly by the line `## compiler messages end`. So the build used the flags of the first runner, and the compiler gave no warning. |
| 1390 | `          "## selftest bwx10 exit=0 # failures=0" in build and len(re.findall(r"^[0-9a-f]{64}  ", build, re.M)) == 7, build[-600:])` | Continues the check: the record holds `## selftest bwx10 exit=0 # failures=0`, and 7 lines start with a sha256 (64 hex digits and two spaces). With these checksums a later result can name the exact sources, binary and listings. |
| 1391 | `    for fn in SEQ_FUNCTIONS:` | Loops over the two timed functions. |
| 1392 | `        t = seq_targets(os.path.join(new, "bwx10"), fn)` | `t`: the branch targets of the function in the binary that the script built (line 301). |
| 1393 | `        check("build10.sh: build.txt lists the branch targets of %s, as the machine-code rule reads them" % fn,` | Check: `build.txt` lists the branch targets of the function, as the machine-code rule reads them. |
| 1394 | `              "## %s branch targets: %s\n" % (fn, " ".join("%s=%d" % (k, t[k]) for k in sorted(t))) in build and` | Continues the check: the record holds a line with the function name, the words `branch targets:` and every target with its count in the form `name=count`, sorted by name ... |
| 1395 | `              not seq_code_problems(t, fn), re.findall(r"^## timed_sequence.*$", build, re.M))` | Continues the check: ... and these targets pass the machine-code rule. So the build script and the test read the same targets from the machine code. On a failure the lines of the record about the timed functions are printed. |
| 1396 | `    check("build10.sh: build.txt holds the placement of bwx10, and says that the accepted binary was not found beside it",` | Check: `build.txt` holds the placement of `bwx10`, and it says that the accepted binary was not found beside it. |
| 1397 | `          re.search(r"^## placement bwx10 \(start modulo 64\): call=\d+ read_smaps=\d+ tcount=\d+ timed_sequence=\d+ "` | Continues the check: a line `## placement bwx10 (start modulo 64):` with a number for each of `call`, `read_smaps`, `tcount`, `timed_sequence` ... |
| 1398 | `                    r"timed_sequence_hot=\d+$", build, re.M) and "## placement against bwx8: not compared (no file " in build,` | Continues the check: ... and `timed_sequence_hot`, and a line that holds `## placement against bwx8: not compared (no file`. The second line shows that a comparison that could not be made is written down. |
| 1399 | `          re.findall(r"^## placement.*$", build, re.M))` | Continues the check: the placement lines of the record as the detail. |
| 1400 | `    with open(os.path.join(new, "seq-listing.txt")) as f:` | Opens `seq-listing.txt` in the folder `new`. |
| 1401 | `        seq_text = f.read()` | `seq_text`: its whole text. |
| 1402 | `    check("build10.sh: seq-listing.txt holds the machine code of both timed functions",` | Check: `seq-listing.txt` holds the machine code of both timed functions. The comment in the build script says that this file is for a person to read and that no script uses it. This test reads the file of its own test build (lines 1400 to 1401). |
| 1403 | `          re.findall(r"^=== bwx10 (\S+) ===$", seq_text, re.M) == list(SEQ_FUNCTIONS) and` | Continues the check: the head lines `=== bwx10 <function> ===` name exactly the two timed functions, in order ... |
| 1404 | `          all("<%s>:" % fn in seq_text for fn in SEQ_FUNCTIONS) and len(seq_text.splitlines()) > 60, seq_text[:200])` | Continues the check: ... the label of each function is in the text, and the text has more than 60 lines. |
| 1405 | `    seq = os.path.join(E.tmp, "seq")` | `seq`: the folder `seq` in the temporary folder. |
| 1406 | `    os.makedirs(seq)` | Creates it. |
| 1407 | `    for name in ("bwx10_selftest.c", "build10.sh"):` | Loops over the self-test file and the build script. |
| 1408 | `        shutil.copy(os.path.join(HERE, name), seq)` | Copies the file into the folder `seq`. |
| 1409 | `    with open(os.path.join(seq, "bwx10.c"), "w") as f:` | Opens `bwx10.c` in that folder for writing. |
| 1410 | `        f.write(mutant_source(SEQ_MUTANTS[1]) or "")` | Writes the source with the second defect of `SEQ_MUTANTS`: a page read and an output flush before the first target window. Without that source the file is empty. |
| 1411 | `    r6 = subprocess.run(["bash", os.path.join(seq, "build10.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build10.sh` in the folder `seq`. |
| 1412 | `                        universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1413 | `    check("build10.sh: exit 6 for a build with " + SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and` | Check: `build10.sh` ends with exit status 6 for a build with that defect. The error output names `read_vmstat` ... |
| 1414 | `          "fflush" in r6.stderr and "timed_sequence of bwx10:" in r6.stderr and "timed_sequence_hot of" not in r6.stderr,` | Continues the check: ... and `fflush`, the two added calls. It holds `timed_sequence of bwx10:` and does not hold `timed_sequence_hot of`. Exit status 6 of the build script means that a timed sequence reaches a function that is not allowed there. So a build with such a call is rejected when it is built, before any measurement. |
| 1415 | `          (r6.returncode, r6.stderr[-300:]))` | Continues the check: the status and the end of the error output as the detail. |
| 1416 | `    seqh = os.path.join(E.tmp, "seqh")` | `seqh`: the folder `seqh` in the temporary folder. |
| 1417 | `    os.makedirs(seqh)` | Creates it. |
| 1418 | `    for name in ("bwx10_selftest.c", "build10.sh"):` | Loops over the self-test file and the build script. |
| 1419 | `        shutil.copy(os.path.join(HERE, name), seqh)` | Copies the file into the folder `seqh`. |
| 1420 | `    with open(os.path.join(seqh, "bwx10.c"), "w") as f:` | Opens `bwx10.c` in that folder for writing. |
| 1421 | `        f.write(mutant_source(HOT_SEQ_MUTANTS[1]) or "")` | Writes the source with the same defect in `timed_sequence_hot` (line 425). |
| 1422 | `    r6 = subprocess.run(["bash", os.path.join(seqh, "build10.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build10.sh` in the folder `seqh`. |
| 1423 | `                        universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1424 | `    check("build10.sh: exit 6 for a build with " + HOT_SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and` | Check: `build10.sh` ends with exit status 6 for that build too. The error output names `read_vmstat` ... |
| 1425 | `          "fflush" in r6.stderr and "timed_sequence_hot of bwx10:" in r6.stderr and "timed_sequence of" not in r6.stderr,` | Continues the check: ... and `fflush`. It holds `timed_sequence_hot of bwx10:` and does not hold `timed_sequence of`. So the script checks both timed functions and names the right one. |
| 1426 | `          (r6.returncode, r6.stderr[-300:]))` | Continues the check: the status and the end of the error output as the detail. |

### `test_build_scripts`: real listings, a moved kernel, and the placement record (lines 1427 to 1480)

| Line | Source | Explanation |
|---:|---|---|
| 1427 | `    with open(os.path.join(new, "offsets.tsv")) as f:` | Opens `offsets.tsv` of the full build in the folder `new`. |
| 1428 | `        rows = [line.split("\t") for line in f.read().splitlines()[1:]]` | `rows`: its rows without the header line, each split at the tabs. |
| 1429 | `    check("build10.sh: offsets.tsv has one row per kernel of binary bwx10, each with a loop",` | Check: `offsets.tsv` has one row per kernel of the binary `bwx10`, each with a loop. |
| 1430 | `          len(rows) == 26 and [r[1] for r in rows[21:]] == NEW_KERNELS and` | Continues the check: 26 rows, and the rows 22 to 26 are the kernels of `NEW_KERNELS` ... |
| 1431 | `          all(r[0] == "bwx10" and r[5].isdigit() for r in rows), rows[:3])` | Continues the check: ... every row names the binary `bwx10`, and its loop offset is a number. A number shows that the script found a backward branch, and so a loop, in the function. |
| 1432 | `    r = subprocess.run(["bash", os.path.join(old, "build.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build.sh`, the build script of the first runner, in the folder `old`. Both outputs are collected. |
| 1433 | `    if not check("build.sh of bwx runs in a temporary copy (the reference for the next check)", r.returncode == 0, r.stderr[-300:]):` | Check: `build.sh` of `bwx` runs in a temporary copy with exit status 0. Its listing is the reference for the next check. On a failure the end of the error output is printed. |
| 1434 | `        return` | Ends the test when the check before it failed. |
| 1435 | `    ref = ["--ref-listing", os.path.join(old, "listing.txt"), "--ref-offsets", os.path.join(old, "offsets.tsv"),` | `ref`: the arguments that make the listing check use the build in the folder `old` as its reference: its listing, its offsets table ... |
| 1436 | `           "--ref-binary", "bwx"]` | Continues line 1435: ... and `bwx` as the binary name in that reference. |
| 1437 | `    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref + ["--skip-new"])` | Runs the listing check on the listing of the full build against that reference, with `--skip-new`. |
| 1438 | `    check("listing: on this machine the 21 old kernels of bwx10 equal the kernels of bwx, text and loop offset "` | Check: on this machine the 21 old kernels of `bwx10` equal the kernels of `bwx`, in text and in loop offset. |
| 1439 | `          "(--skip-new: the new kernels are stand-in loops here)",` | Continues the name of the check: it adds that `--skip-new` is used, as the new kernels are stand-in loops on this machine. |
| 1440 | `          rc == 0 and out.count("\tsame\tok") == 21 and "new_kernels=NOT CHECKED" in out, out[-400:])` | Continues the check: exit status 0, 21 rows that end with `same` and `ok`, and the text `new_kernels=NOT CHECKED`. This runs the whole chain of build script, listing and listing check on real compiler output. It shows for the local compiler that the additions of round 3 change no instruction and no loop offset of an older kernel. |
| 1441 | `    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref)` | Runs the listing check on the listing of the full build against that reference. |
| 1442 | `    check("listing: without --skip-new the stand-in loops of the new kernels are rejected (exit 1), and the 21 old rows stay ok",` | Check: without `--skip-new` the stand-in loops of the new kernels are rejected with exit status 1, and the 21 old rows stay ok. |
| 1443 | `          rc == 1 and out.count("\tsame\tok") == 21 and "failed_rows=0 new_kernels=5 new_failed_rows=5" in out, out[-400:])` | Continues the check: status 1, 21 rows `same` and `ok`, and the summary `failed_rows=0 new_kernels=5 new_failed_rows=5`. A stand-in loop of this machine is x86-64 code and holds none of the planned Arm instructions. So part 2 of the listing check is shown to reject real code that is not the planned loop. |
| 1444 | `    # a bwx10 build whose kernel was moved must be rejected` | Comment: a build of `bwx10` in which a kernel was moved must be rejected. |
| 1445 | `    moved = os.path.join(E.tmp, "moved")` | `moved`: the folder `moved` in the temporary folder. |
| 1446 | `    os.makedirs(moved)` | Creates it. |
| 1447 | `    for name in ("bwx10.c", "bwx10_selftest.c", "build10.sh"):` | Loops over the three files of a build. |
| 1448 | `        shutil.copy(os.path.join(HERE, name), moved)` | Copies the file into the folder `moved`. |
| 1449 | `    with open(os.path.join(moved, "bwx10.c")) as f:` | Opens `bwx10.c` in that folder. |
| 1450 | `        src = f.read()` | `src`: the source text of the runner. |
| 1451 | `    with open(os.path.join(moved, "bwx10.c"), "w") as f:` | Opens the same file for writing. |
| 1452 | `        f.write(src.replace("#define PAD_asmread 0\n", "#define PAD_asmread 16\n"))` | Writes the source with `PAD_asmread` set to 16 in place of 0. The pad before `k_asmread` then is 16 bytes longer. So the kernel and its loop start 16 bytes later. |
| 1453 | `    r = subprocess.run(["bash", os.path.join(moved, "build10.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build10.sh` in the folder `moved`. The check of this build follows in lines 1476 to 1478. |
| 1454 | `    # the placement record against the accepted binary: a copy with the local pad, and a copy with another pad` | Comment: the placement record against the accepted binary is tested with two copies: one with the local pad and one with another pad. |
| 1455 | `    if getattr(E, "call8", None) is None:` | Tests whether `E.call8` is missing. The test `test_source` sets it when its placement check works. |
| 1456 | `        check("build10.sh: placement record against the accepted binary (NOT RUN: the placement check of the source test failed)", False)` | Records a failed check with `NOT RUN` in its name: the placement record against the accepted binary cannot be tested. |
| 1457 | `    else:` | In every other case the placement record is tested. |
| 1458 | `        for tag, pad in (("local", E.call8), ("other", (E.call8 + 4) % 64)):` | Loops over two cases: `local` with the pad of the local build of the accepted runner, and `other` with a pad 4 bytes larger. |
| 1459 | `            d = os.path.join(E.tmp, "placed-" + tag)` | `d`: the folder `placed-` plus the name of the case in the temporary folder. |
| 1460 | `            os.makedirs(d)` | Creates it. |
| 1461 | `            for name in ("bwx10_selftest.c", "build10.sh"):` | Loops over the self-test file and the build script. |
| 1462 | `                shutil.copy(os.path.join(HERE, name), d)` | Copies the file into that folder. |
| 1463 | `            with open(os.path.join(d, "bwx10.c"), "w") as f:` | Opens `bwx10.c` in that folder for writing. |
| 1464 | `                f.write(src.replace("#define PAD_after_kernels 24\n", "#define PAD_after_kernels %d\n" % pad))` | Writes the source with `PAD_after_kernels` set to the pad of this case in place of 24. |
| 1465 | `            rp = subprocess.run(["bash", os.path.join(d, "build10.sh")], env=dict(env, BWX8_BIN=E.bin8), stdout=subprocess.PIPE,` | Runs `build10.sh` in that folder. `BWX8_BIN` gives it the local build of the accepted runner. By the comment in the build script it reads this binary with `nm` only and does not run it. |
| 1466 | `                                stderr=subprocess.PIPE, universal_newlines=True)` | Continues the call of line 1465: the outputs are collected as text. |
| 1467 | `            lines = []` | `lines`: the placement lines of the build record, empty at the start. |
| 1468 | `            if os.path.exists(os.path.join(d, "build.txt")):` | Tests whether the build wrote a build record. |
| 1469 | `                with open(os.path.join(d, "build.txt")) as f:` | Opens it. |
| 1470 | `                    lines = re.findall(r"^## placement.*$", f.read(), re.M)` | `lines`: the lines of the record that start with `## placement`. |
| 1471 | `            want = "same" if tag == "local" else "DIFFERS"` | `want`: the word that the record must hold: `same` for the local pad and `DIFFERS` for the other pad. |
| 1472 | `            check("build10.sh: with the accepted binary given and the %s pad, build.txt holds both placements and the word %s" % (tag, want),` | Check: with the accepted binary given and the pad of this case, `build.txt` holds both placements and the expected word. |
| 1473 | `                  rp.returncode == 0 and len(lines) == 3 and lines[0].startswith("## placement bwx10 (start modulo 64): call=%d " % pad) and` | Continues the check: status 0, 3 placement lines, and the first one gives `call` of `bwx10` at the pad of this case ... |
| 1474 | `                  lines[1].startswith("## placement bwx8 (start modulo 64): call=%d " % E.call8) and` | Continues the check: ... the second one gives `call` of `bwx8` at `E.call8` ... |
| 1475 | `                  lines[2] == "## placement up to timed_sequence against bwx8: " + want, (rp.returncode, lines))` | Continues the check: ... and the third one is `## placement up to timed_sequence against bwx8:` with the expected word. Both words are produced in the two cases. So the script is shown to detect a timed path that was moved by 4 bytes. |
| 1476 | `    rc, out = run_listing([os.path.join(moved, "listing.txt")] + ref + ["--skip-new"])` | Runs the listing check on the listing of the build with the moved kernel, against the reference, with `--skip-new`. |
| 1477 | `    check("listing: a real bwx10 build with k_asmread moved by 16 bytes is rejected (exit 1)",` | Check: a real build of `bwx10` with `k_asmread` moved by 16 bytes is rejected with exit status 1. |
| 1478 | `          r.returncode == 0 and rc == 1 and "loop offset modulo 64" in out, (r.returncode, rc, out[-300:]))` | Continues the check: the build itself worked with exit status 0, the listing check ended with exit status 1, and its output holds `loop offset modulo 64`. So a kernel that a build moved is rejected on real compiler output, also when its instructions are unchanged. |

### `structure`, `m_of` and `accounting_problems`: comparing two runs (lines 1481 to 1530)

| Line | Source | Explanation |
|---:|---|---|
| 1481 | `def structure(out, drop_m=()):` | Starts the function `structure`. It reduces the output of a run to the parts that must be equal in two runs of the same plan. `drop_m` names `M` keys to leave out. |
| 1482 | `    """The rows of a run without what differs between two runs of one plan: times, byte counts, counter values` | Description text: the result holds the rows without what differs between two runs of one plan: times, byte counts, counter values ... |
| 1483 | `    and addresses. Comment lines byte for byte. M rows with their values, apart from the addresses. S rows whole.` | Description text: ... and addresses. Comment lines are kept byte for byte. `M` rows keep their values, apart from the addresses. `S` rows are kept whole. |
| 1484 | `    W rows: trial, phase, widx, kernel, pass_bytes. P rows: trial, when, kB_total. E rows: trial, field count,` | Description text: of a `W` row the trial, the phase, the window number, the kernel and the pass bytes are kept. Of a `P` row the trial, the word `pre` or `post` and the size in kB. Of an `E` row the trial, the number of fields ... |
| 1485 | `    sink_ok, count_state. B rows: one entry per window that has bins. Other rows: type and field count."""` | Description text: ... `sink_ok` and the count state. The `B` rows give one entry per window that has bins. Of every other row the type and the number of fields are kept. |
| 1486 | `    s = []` | `s`: the list of the kept items, empty at the start. |
| 1487 | `    for line in out.splitlines():` | Loops over the lines of the output. |
| 1488 | `        f = line.split(",")` | Splits the line at the commas. |
| 1489 | `        if line.startswith("#"):` | A comment line, which starts with `#`: |
| 1490 | `            item = line` | is kept whole. |
| 1491 | `        elif f[0] == "M":` | An `M` row: |
| 1492 | `            if f[1] in drop_m:` | Tests whether its key is one of the keys to leave out. |
| 1493 | `                continue` | Skips the row in that case. |
| 1494 | `            item = ("M", f[1], None if f[1] in ADDR_KEYS else ",".join(f[2:]))` | Keeps the key and the value. The value is replaced by `None` for the five address keys. |
| 1495 | `        elif f[0] == "S":` | An `S` row: |
| 1496 | `            item = tuple(f)` | is kept with all its fields. |
| 1497 | `        elif f[0] == "W":` | A `W` row: |
| 1498 | `            item = tuple(f[:6]) + (len(f),)` | Keeps its first 6 fields (the row type, the trial, the phase, the window number, the kernel and the pass bytes) and its number of fields. The bytes and the two times are left out. |
| 1499 | `        elif f[0] == "P":` | A `P` row: |
| 1500 | `            item = tuple(f[:4]) + (len(f),)` | Keeps its first 4 fields (the row type, the trial, `pre` or `post`, and the size in kB) and its number of fields. |
| 1501 | `        elif f[0] == "E":` | An `E` row: |
| 1502 | `            item = ("E", f[1], len(f), f[8], f[9])` | Keeps the trial, the number of fields, `sink_ok` (field 8) and the count state (field 9). |
| 1503 | `        elif f[0] == "B":` | A `B` row: |
| 1504 | `            item = ("B", f[1], f[2], len(f))` | Keeps the trial, the window number and the number of fields. |
| 1505 | `            if s and s[-1] == item:` | Tests whether the item before is the same item. That is the case for the second and every later bin of a window. |
| 1506 | `                continue` | Skips it. So each window with bins gives one item, however many bins the run made. |
| 1507 | `        elif f[0] == "K":` | A `K` row: |
| 1508 | `            item = ("K", f[1], len(f))` | Keeps the kernel name and the number of fields. The address is left out. |
| 1509 | `        else:` | Every other row: |
| 1510 | `            item = (f[0], len(f))` | Keeps the row type and the number of fields. |
| 1511 | `        s.append(item)` | Adds the item to the list. |
| 1512 | `    return s` | Returns the list. |
| 1515 | `def m_of(out):` | Starts the function `m_of`. |
| 1516 | `    return {f[1]: f[2] for f in rows_of(out).get("M", [])}` | Returns the `M` rows of an output as a dictionary from key to value. |
| 1519 | `def accounting_problems(plan, out):` | Starts the function `accounting_problems`. It applies the three row rules to every trial of a run. |
| 1520 | `    """the W, E and B rules of test_rows on every trial of a run"""` | Description text: the rules are the `W`, `E` and `B` rules of `test_rows`. |
| 1521 | `    rows, p = rows_of(out), []` | `rows`: the output sorted by row type. `p`: the list of problems. |
| 1522 | `    for i, f in enumerate(plan_lines(plan)):` | Loops over the trials of the plan. `f` holds the plan fields of trial `i`. |
| 1523 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)` | `w`: the `W` rows of the trial. `e`: its `E` rows. |
| 1524 | `        if len(e) != 1:` | Tests whether the trial does not have exactly one `E` row. |
| 1525 | `            p.append("trial %d: %d E rows" % (i, len(e)))` | Adds a problem with the number of `E` rows. |
| 1526 | `            continue` | Continues with the next trial. |
| 1527 | `        p += ["trial %d: %s" % (i, x) for x in window_problems(f, w) + e_problems(f, w, e[0]) + bin_problems(f, w, of_trial(rows, "B", i))]` | Adds every problem of `window_problems` (line 101), `e_problems` (line 122) and `bin_problems` (line 139), each with the trial number in front. Together they say that the bytes and the times of every window are right: whole passes, the 8 MiB rule, the durations, the order of the times, the gaps, and bins that sum to the bytes of their window. |
| 1528 | `    return p` | Returns the list of problems. |

### `test_new_kernels`, checks k: the kernels of round 3 in every mode (lines 1531 to 1567)

| Line | Source | Explanation |
|---:|---|---|
| 1531 | `def test_new_kernels():` | Starts the test `test_new_kernels`. |
| 1532 | `    """(k) the five kernels of round 3 in --list, in the plan parser, in the trial mode and in the interval mode"""` | Description text: the checks named k. They cover the five kernels of round 3 in the output of `--list`, in the plan parser, in the trial mode and in the interval mode. |
| 1533 | `    rc, out, _ = run(["--list"])` | Runs the runner with `--list`. It prints the names of its kernels, one per line. |
| 1534 | `    rc8, out8, _ = run(["--list"], binary=E.bin8)` | Runs the local build of the accepted runner with `--list`. |
| 1535 | `    names = out.split()` | `names`: the kernel names of the runner under test. |
| 1536 | `    check("k: --list prints 26 kernels: the 21 of the accepted runner in their order, then the 5 new ones",` | Check: `--list` prints 26 kernels: the 21 of the accepted runner in their order, then the 5 new ones. |
| 1537 | `          rc == 0 and rc8 == 0 and len(names) == 26 and names[:21] == out8.split() and names[21:] == NEW_KERNELS, names[20:])` | Continues the check: both runs end with status 0, the list has 26 names, the first 21 equal the list of the accepted runner, and the last 5 are `NEW_KERNELS`. The build script takes the kernels for its listing from `--list`. So the order of this list is also the order of the listing. |
| 1538 | `    lines = ["0 A 1 read_pf256@8M:8 read_pf512@8M:40 read_pf1024@1M:8 read_pf2048@8M 2 10 closed 0",` | `lines`: a plan of four trials that uses every kernel of round 3. Trial 0: previous activity `read_pf256`, prefix `read_pf512`, predecessor `read_pf1024` on 1 MiB, target `read_pf2048` with 2 windows of 10 ms. |
| 1539 | `             "1 B 1 - read_1pl@8M:40 read_1pl@1M:8 read_1pl@8M 2 10 closed 1",` | Trial 1: `read_1pl` as prefix, as predecessor on 1 MiB and as target, with bins. |
| 1540 | `             "2 C 1 - oldread@8M:8 - read_pf256@32K 3 10 closed 0",` | Trial 2: a prefix of `oldread`, then the target `read_pf256` on 32 KiB with 3 windows of 10 ms. |
| 1541 | `             "3 D 1 read_1pl@8M:8 - - read_pf512@1M 2 10 closed 0"]` | Trial 3: previous activity `read_1pl`, then the target `read_pf512` on 1 MiB. |
| 1542 | `    plan = write_plan("newk", lines)` | Writes the plan. |
| 1543 | `    for extra in ([], ["--hot-copy"]):` | Loops over two runs: one without an added option and one with `--hot-copy`. |
| 1544 | `        rc, out, err = trial(plan, extra)` | Runs the plan in the trial mode. |
| 1545 | `        tag = "with --hot-copy" if extra else "plain"` | `tag`: a word for the names of the checks: `plain`, or `with --hot-copy`. |
| 1546 | `        if not check("k: a plan that uses every new kernel as previous activity, prefix, predecessor or target runs with "` | Check: a plan that uses every new kernel as previous activity, prefix, predecessor or target runs with ... |
| 1547 | `                     "status 0 (%s)" % tag, rc == 0, err):` | Continues the check: ... status 0. So the plan parser accepts each new kernel in each phase. |
| 1548 | `            continue` | Continues with the next run when this one failed. |
| 1549 | `        rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 1550 | `        k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. |
| 1551 | `        check("k: one K row per new kernel of the plan, with the address modulo 64 (%s)" % tag,` | Check: one `K` row per new kernel of the plan, with the address modulo 64. |
| 1552 | `              sorted(k) == sorted(NEW_KERNELS + ["oldread"]) and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are the five new kernels and `oldread`, and in each row the last field is the hex address modulo 64. |
| 1553 | `        p = accounting_problems(plan, out)` | Applies the three row rules to every trial (line 1519). |
| 1554 | `        check("k: W, E and B rows of the new kernels: whole passes, 8 MiB rule, durations, gaps, bins (%s)" % tag, not p, p)` | Check: the `W`, `E` and `B` rows of the new kernels keep the rules: whole passes, the 8 MiB rule, durations, gaps and bins. So the byte and time counts of the runner are also right for the added kernels. |
| 1555 | `        check("k: the W rows name the kernel of the plan in every window (%s)" % tag,` | Check: the `W` rows name the kernel of the plan in every window. |
| 1556 | `              [w[4] for w in rows["W"]] == [e[2] for f in plan_lines(plan) for e in expected_windows(f)])` | Continues the check: the kernel column of all `W` rows equals the kernels of the planned windows, in order. |
| 1557 | `        check("k: sink_ok is 1 only for the trial that ran old read, and no X row (%s)" % tag,` | Check: `sink_ok` is `1` only for the trial that ran the old read kernel, and no `X` row is printed. |
| 1558 | `              [f[8] for f in rows["E"]] == ["NA", "NA", "1", "NA"] and not rows.get("X"), rows.get("X"))` | Continues the check: the values are `NA`, `NA`, `1`, `NA`. A new kernel returns no sum, so it has no sink check. |
| 1559 | `    for bad_name in ("read_pf128", "read_pf", "read_1pl2", "READ_PF256"):` | Loops over four names that are close to a real kernel name but are none. |
| 1560 | `        rc, out, err = trial(write_plan("badk", ["0 a 1 - - - %s@8M 1 5 closed 0" % bad_name]))` | Runs a plan whose target is that name. |
| 1561 | `        check("k: status 2 and no row for the unknown kernel %s" % bad_name, rc == 2 and out == "" and "unknown kernel" in err, (rc, err[:100]))` | Check: status 2, no row, and the words `unknown kernel` in the error output. So a name with a typing error cannot run as another kernel. |
| 1562 | `    rc, out, err = run(["--seq", "read_pf512,read_1pl@1M,asmread", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])` | Runs the interval mode with the sequence `read_pf512`, `read_1pl` on 1 MiB and `asmread`, on a buffer of 8 MiB, with intervals of at least 10 ms and 1 thread on the worker CPU. |
| 1563 | `    r = rows_of(out)` | `r`: the output sorted by row type. |
| 1564 | `    check("k: the interval mode (--seq) runs the new kernels",` | Check: the interval mode (`--seq`) runs the new kernels. |
| 1565 | `          rc == 0 and [f[3] for f in r.get("I", [])] == ["read_pf512", "read_1pl", "asmread"], (rc, err[:200]))` | Continues the check: status 0, and the kernel column of the `I` rows is `read_pf512`, `read_1pl`, `asmread`. |

### `test_rec_pad`, checks l: `--rec-pad` moves the window records and nothing else (lines 1568 to 1611)

| Line | Source | Explanation |
|---:|---|---|
| 1568 | `def test_rec_pad():` | Starts the test `test_rec_pad`. |
| 1569 | `    """(l) --rec-pad: the layout with 0, the move of the window records, bad values"""` | Description text: the checks named l for the option `--rec-pad`: the layout with the value 0, the move of the window records, and bad values. The option puts unused bytes before the window records. Round 3 added it to test whether the address of these records changes a measured rate. |
| 1570 | `    plan = write_plan("pad", ALL)` | Writes the plan `ALL` (line 602). |
| 1571 | `    outs = {}` | `outs`: the outputs of the runs, by a key. It is empty at the start. |
| 1572 | `    for key, extra, binary in (("accepted", [], E.bin8), ("none", [], None), (0, ["--rec-pad", "0"], None),` | Loops over six runs. The key `accepted` is a run of the accepted runner. The key `none` is the runner under test without the option. The key 0 is `--rec-pad 0` ... |
| 1573 | `                               (80, ["--rec-pad", "80"], None), (4000, ["--rec-pad", "4000"], None),` | Continues line 1572: ... the keys 80 and 4000 are pads of 80 and 4000 bytes ... |
| 1574 | `                               (65536, ["--rec-pad", "65536"], None)):` | Continues line 1572: ... and the key 65536 is the largest pad that the option allows. |
| 1575 | `        rc, out, err = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + extra, binary=binary)` | Runs the plan in the trial mode with the binary and the option of this run. |
| 1576 | `        check("l: the plan with all phases runs with status 0 (%s)" % (key if binary or key == "none" else "--rec-pad %s" % key),` | Check: the plan with all phases runs with status 0. The name of the check holds the key or the option. |
| 1577 | `              rc == 0 and len(rows_of(out).get("E", [])) == 4, (rc, err[:200]))` | Continues the check: status 0 and 4 `E` rows, one per trial. |
| 1578 | `        outs[key] = out` | Keeps the output under its key. |
| 1579 | `    m = {k: m_of(v) for k, v in outs.items()}` | `m`: the `M` rows of each run as a dictionary. |
| 1580 | `    check("l: --rec-pad 0 prints the rows of a run without the option: comment lines, every M value but the addresses, "` | Check: `--rec-pad 0` prints the rows of a run without the option: the comment lines, every `M` value but the addresses ... |
| 1581 | `          "and the S, K, P, W, B, E structure", structure(outs[0]) == structure(outs["none"]),` | Continues the check: ... and the same structure of the `S`, `K`, `P`, `W`, `B` and `E` rows (line 1481). So the value 0 is the same as no option. |
| 1582 | `          [x for x in zip(structure(outs[0]), structure(outs["none"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1583 | `    check("l: that comparison can fail: --rec-pad 80 gives another structure", structure(outs[80]) != structure(outs["none"]))` | Check: that comparison can fail: `--rec-pad 80` gives another structure. |
| 1584 | `    check("l: bwx10 without the option prints the rows of the accepted runner plus the 8 new M rows: comment lines, "` | Check: `bwx10` without the option prints the rows of the accepted runner plus the 8 new `M` rows: the comment lines, ... |
| 1585 | `          "M values (rec_bytes among them), S, K, P, W, B, E structure",` | Continues the name of the check: ... the `M` values with `rec_bytes` among them, and the structure of the `S`, `K`, `P`, `W`, `B` and `E` rows. |
| 1586 | `          structure(outs["none"], drop_m=NEW_M) == structure(outs["accepted"]) and "rec_bytes" in m["accepted"],` | Continues the check: without the 8 added `M` rows the structure equals that of the accepted runner, and the accepted runner prints `rec_bytes`. So the additions of round 3 changed no row that the analysis of the accepted runner reads. |
| 1587 | `          [x for x in zip(structure(outs["none"], drop_m=NEW_M), structure(outs["accepted"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1588 | `    check("l: that comparison can fail: with --rec-pad 80 the M row rec_bytes differs from the accepted runner",` | Check: that comparison can fail: with `--rec-pad 80` the `M` row `rec_bytes` differs from the accepted runner. |
| 1589 | `          structure(outs[80], drop_m=NEW_M) != structure(outs["accepted"]))` | Continues the check: the two structures differ. |
| 1590 | `    keys = [f[1] for f in rows_of(outs["none"])["M"]]` | `keys`: the keys of the `M` rows of the run without the option, in the order of the output. |
| 1591 | `    check("l: the 8 new M rows stand together, in the documented order, directly after M,trace",` | Check: the 8 new `M` rows stand together, in the documented order, directly after the row `M,trace`. |
| 1592 | `          keys[keys.index("trace") + 1:keys.index("trace") + 9] == NEW_M and all(keys.count(k) == 1 for k in NEW_M), keys)` | Continues the check: the 8 keys after `trace` are those of `NEW_M`, and each of these keys stands once. |
| 1593 | `    check("l: M,rec_pad holds the option value and is 0 without the option",` | Check: `M,rec_pad` holds the value of the option and is 0 without the option. |
| 1594 | `          [m[k].get("rec_pad") for k in ("none", 0, 80, 4000, 65536)] == ["0", "0", "80", "4000", "65536"])` | Continues the check: the values of the five runs are `0`, `0`, `80`, `4000` and `65536`. So each result names the pad under which it was measured. |
| 1595 | `    check("l: M,hot_copy is 0 and M,win_size is 80 (the size of one window record) in every run",` | Check: `M,hot_copy` is 0 and `M,win_size` is 80 in every run. 80 bytes is the size of one window record. With `win_addr` and this size the address of every window record can be computed. |
| 1596 | `          all(m[k].get("hot_copy") == "0" and m[k].get("win_size") == "80" for k in ("none", 0, 80, 4000, 65536)), m["none"])` | Continues the check: the two values in each of the five runs. |
| 1597 | `    hexa = re.compile(r"[0-9a-f]+")` | `hexa`: a pattern for a hex number without a prefix. |
| 1598 | `    check("l: the five address rows hold hex numbers above 0",` | Check: the five address rows hold hex numbers above 0. |
| 1599 | `          all(hexa.fullmatch(m[k].get(a, "")) and int(m[k][a], 16) > 0 for k in ("none", 0, 80, 4000, 65536) for a in ADDR_KEYS), m["none"])` | Continues the check: every key of `ADDR_KEYS` in each of the five runs. |
| 1600 | `    a = {k: {x: int(m[k][x], 16) for x in ADDR_KEYS} for k in ("none", 0, 80, 4000, 65536)}` | `a`: the five addresses of each of the five runs as numbers. |
| 1601 | `    check("l: buf_addr is a multiple of 2 MiB, and the five addresses differ from each other",` | Check: `buf_addr` is a multiple of 2 MiB, and the five addresses differ from each other. |
| 1602 | `          all(a[k]["buf_addr"] % (2 << 20) == 0 and len(set(a[k].values())) == 5 for k in a), a["none"])` | Continues the check: the condition on every run. The buffer starts at a 2 MiB boundary, so it can lie on huge pages from its first byte on. |
| 1603 | `    base = a[0]["win_addr"] - a[0]["rec_addr"]` | `base`: the distance from the start of the record block (`rec_addr`) to the first window record (`win_addr`) with `--rec-pad 0`, in bytes. |
| 1604 | `    check("l: without a pad win[0] stands after the 4 trial records of the plan: win_addr - rec_addr is a multiple of 4 above 0, "` | Check: without a pad the first window record stands after the 4 trial records of the plan. The distance is a multiple of 4 above 0 ... |
| 1605 | `          "the same without the option and with --rec-pad 0", base > 0 and base % 4 == 0 and a["none"]["win_addr"] - a["none"]["rec_addr"] == base, base)` | Continues the check: ... and it is the same without the option and with `--rec-pad 0`. |
| 1606 | `    for pad in (80, 4000, 65536):` | Loops over the three pads above 0. |
| 1607 | `        check("l: --rec-pad %d: win_addr - rec_addr grows by exactly %d bytes, and rec_bytes grows by exactly %d bytes" % (pad, pad, pad),` | Check: with this pad the distance from `rec_addr` to `win_addr` grows by exactly the pad, and `rec_bytes` grows by exactly the pad. |
| 1608 | `              a[pad]["win_addr"] - a[pad]["rec_addr"] - base == pad and int(m[pad]["rec_bytes"]) - int(m[0]["rec_bytes"]) == pad,` | Continues the check: both differences, measured against the run with `--rec-pad 0`. So the option moves the window records by the bytes that it names, inside a record block that is larger by the same bytes. |
| 1609 | `              (a[pad]["win_addr"] - a[pad]["rec_addr"] - base, m[pad]["rec_bytes"], m[0]["rec_bytes"]))` | Continues the check: the three values as the detail. |
| 1610 | `        p = accounting_problems(plan, outs[pad])` | Applies the three row rules to the run with this pad (line 1519). |
| 1611 | `        check("l: --rec-pad %d: W, E and B rows keep the rules (whole passes, durations, gaps, bins)" % pad, not p, p)` | Check: with this pad the `W`, `E` and `B` rows keep the rules: whole passes, durations, gaps and bins. The moved records still hold right counts. |

### `test_rec_pad`: the absolute address of the window records (lines 1612 to 1645)

| Line | Source | Explanation |
|---:|---|---|
| 1612 | `    # The absolute address. The record block is the first block that the worker thread takes from malloc. glibc` | Comment: the next checks look at the absolute address. The record block is the first block that the worker thread takes from `malloc`. The C library glibc ... |
| 1613 | `    # gives a thread its own heap, which starts at a multiple of 64 MiB. So the address of the block modulo 64 MiB` | Comment: ... gives a thread its own heap, which starts at a multiple of 64 MiB. So the address of the block modulo 64 MiB ... |
| 1614 | `    # is the same in every process (below the size from which malloc maps a block on its own, 128 KiB by default).` | Comment: ... is the same in every process. This holds below the size from which `malloc` maps a block on its own, 128 KiB by default. |
| 1615 | `    big = write_plan("padbig", ["0 a 1 - - - asmread@8M 120 2 closed 0"])` | `big`: a plan with one trial of 120 target windows of 2 ms of `asmread` on 8 MiB. |
| 1616 | `    abs_addr = {}` | `abs_addr`: the address of the first window record per pad, empty at the start. |
| 1617 | `    for pad in (0, 80, 4000):` | Loops over the pads 0, 80 and 4000. |
| 1618 | `        rc, out, err = trial(big, ["--rec-pad", str(pad)])` | Runs the plan with this pad. |
| 1619 | `        abs_addr[pad] = int(m_of(out).get("win_addr", "0"), 16) if rc == 0 else None` | Keeps `win_addr` as a number, or `None` when the run failed. |
| 1620 | `    low = {k: None if v is None else v % (64 << 20) for k, v in abs_addr.items()}` | `low`: each address modulo 64 MiB. |
| 1621 | `    for pad in (80, 4000):` | Loops over the pads 80 and 4000. |
| 1622 | `        check("l: a plan of 120 windows: win_addr modulo 64 MiB moves up by exactly %d bytes with --rec-pad %d (three processes "` | Check: for a plan of 120 windows, `win_addr` modulo 64 MiB moves up by exactly the pad. The name adds: three processes ... |
| 1623 | `              "with address randomization; this relies on the thread heap of glibc)" % (pad, pad),` | Continues the name of the check: ... with address randomization, and the check relies on the thread heap of glibc. |
| 1624 | `              None not in low.values() and low[pad] - low[0] == pad, low)` | Continues the check: no run failed, and the address with the pad minus the address without it equals the pad. So the option moves the records also in absolute terms, from process to process. A test that compares two pads then compares two known addresses. |
| 1625 | `    b = mutant_build(PAD_MUTANT, "pad")` | `b`: a build in which `--rec-pad` does not move the window records (line 431). |
| 1626 | `    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--rec-pad", "80"], binary=b) if b else (1, "", "")` | Runs the plan `ALL` with `--rec-pad 80` and that build. Without a build the status is 1. |
| 1627 | `    mm = m_of(out)` | `mm`: the `M` rows of that run. |
| 1628 | `    check("l: the move check fails on a build with " + PAD_MUTANT,` | Check: the move check fails on that build. |
| 1629 | `          rc == 0 and int(mm["win_addr"], 16) - int(mm["rec_addr"], 16) == base, (rc, mm.get("win_addr")))` | Continues the check: the run ends with status 0, and the distance from `rec_addr` to `win_addr` is still `base`. The check of line 1607 would find this build. |
| 1630 | `    r = subprocess.run(["setarch", os.uname().machine, "-R", "true"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `setarch` with the machine name and `-R` on the command `true`. `setarch -R` starts a program with address randomization switched off. This call only tests whether that works here. |
| 1631 | `    if r.returncode != 0:` | Tests whether it failed. |
| 1632 | `        check("l: absolute win_addr without address randomization (setarch -R does not work here: NOT RUN)", False, r.stderr)` | Records a failed check with `NOT RUN` in its name: the absolute address without address randomization cannot be tested. |
| 1633 | `    else:` | If it works: |
| 1634 | `        fixed = {}` | `fixed`: the five addresses per pad, empty at the start. |
| 1635 | `        for pad in (0, 80, 4000):` | Loops over the pads 0, 80 and 4000. |
| 1636 | `            r = subprocess.run(["setarch", os.uname().machine, "-R", E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M",` | Runs the runner under `setarch -R` on the plan `big` in the trial mode ... |
| 1637 | `                                "--plan", big, "--rec-pad", str(pad)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Continues the call of line 1636: ... with the pad of this run. The outputs are collected. |
| 1638 | `                               universal_newlines=True, timeout=120)` | Continues the call: the outputs are text, and the time limit is 120 s. The three runs get the environment of the test process unchanged. A comment in the later test file `test_runner11.py` says that the check of lines 1640 to 1644 then depends on the size of that environment. By that comment `tw_addr` lies on the stack of the main thread, below the text of the arguments and of the environment. The pad values `0`, `80` and `4000` differ in length, and that can move `tw_addr`. |
| 1639 | `            fixed[pad] = {k: int(v, 16) for k, v in m_of(r.stdout).items() if k in ADDR_KEYS}` | Keeps the five addresses of this run as numbers. |
| 1640 | `        check("l: without address randomization (setarch -R) the absolute win_addr moves by exactly 80 and 4000 bytes, and "` | Check: without address randomization the absolute `win_addr` moves by exactly 80 and 4000 bytes, and ... |
| 1641 | `              "rec_addr, buf_addr, stack_addr and tw_addr do not move",` | Continues the name of the check: ... `rec_addr`, `buf_addr`, `stack_addr` and `tw_addr` do not move. |
| 1642 | `              all(len(fixed[p]) == 5 for p in fixed) and` | Continues the check: every run printed five addresses ... |
| 1643 | `              all(fixed[p]["win_addr"] - fixed[0]["win_addr"] == p for p in (80, 4000)) and` | Continues the check: ... `win_addr` with a pad minus `win_addr` without one equals the pad ... |
| 1644 | `              all(fixed[p][k] == fixed[0][k] for p in (80, 4000) for k in ADDR_KEYS if k != "win_addr"), fixed)` | Continues the check: ... and each other address equals its value without a pad. So the option changes one thing only, the place of the window records. The buffer, the record block, the stack of the worker and the record of the worker stay where they are. |

### `test_rec_pad`: bad values of `--rec-pad`, and the options outside the trial mode (lines 1646 to 1663)

| Line | Source | Explanation |
|---:|---|---|
| 1646 | `    good = write_plan("good", [GOOD])` | `good`: a plan with the line `GOOD`. |
| 1647 | `    base_args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good]` | `base_args`: the arguments of a valid trial run. |
| 1648 | `    for name, value in (("a negative value", "-8"), ("a value above 65536", "65544"), ("65537", "65537"), ("a word", "abc"),` | Loops over nine bad values: a negative value, a value above 65536, the value 65537, a word ... |
| 1649 | `                        ("a number with a letter after it", "80x"), ("a fraction", "80.5"), ("an empty value", ""),` | Continues line 1648: ... a number with a letter after it, a fraction, an empty value ... |
| 1650 | `                        ("a value that is not a multiple of 8", "12"), ("a hex number", "0x50")):` | Continues line 1648: ... a value that is no multiple of 8, and a hex number. |
| 1651 | `        rc, out, err = run(base_args + ["--rec-pad", value])` | Runs the runner with `--rec-pad` and that value. |
| 1652 | `        check("l: status 2, no row and a message for --rec-pad with " + name, rc == 2 and out == "" and "--rec-pad" in err,` | Check: status 2, no row and a message that names `--rec-pad`. A malformed value must not run as 0 or as another pad. |
| 1653 | `              "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Continues the check: the status and the starts of both outputs as the detail. |
| 1654 | `    rc, out, err = run(base_args + ["--rec-pad"])` | Runs the runner with `--rec-pad` as the last argument, without a value. |
| 1655 | `    check("l: status 2 and no row for --rec-pad without a value", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. |
| 1656 | `    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--rec-pad", "80"])` | Runs the interval mode with `--rec-pad 80`. |
| 1657 | `    check("l: status 2 and no row for --rec-pad outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. The option belongs to the trial mode only. |
| 1658 | `    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--hot-copy"])` | Runs the interval mode with `--hot-copy`. |
| 1659 | `    check("l: status 2 and no row for --hot-copy outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. This option belongs to the trial mode only too. |
| 1660 | `    rc, out, err = run(base_args + ["--rec-pad", "0"])` | Runs the same command as the bad cases with `--rec-pad 0`. |
| 1661 | `    check("l: the control: the same command with --rec-pad 0 runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the control runs with status 0 and prints the `E` row of trial 0. So the refusals before came from the values. |

### `TRACE_PLAN` and `trace_run_problems`: the trace rules on a whole run (lines 1664 to 1687)

| Line | Source | Explanation |
|---:|---|---|
| 1664 | `TRACE_PLAN = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",` | `TRACE_PLAN`: the five trial lines of the trace test (line 793). Trial 0: all phases, counters closed, with bins. |
| 1665 | `              "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",` | Trial 1: a prefix, a predecessor and 3 target windows, with the count mode `read`. |
| 1666 | `              "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",` | Trial 2: a prefix and 2 target windows, with the count mode `open`. |
| 1667 | `              "3 D 1 - - - read@8M 2 20 read 0",` | Trial 3: only 2 target windows, with the count mode `read`. |
| 1668 | `              "4 E 1 - - - oldread@8M 2 20 closed 0"]` | Trial 4: only 2 target windows, counters closed. |
| 1671 | `def trace_run_problems(plan, out):` | Starts the function `trace_run_problems`. It applies the rules of a trace run to every trial of an output. |
| 1672 | `    """the trace rule, the bin rule on the clock reads of the trace, and the page-fault line, for every trial"""` | Description text: the rules are the trace rule, the bin rule on the clock reads of the trace, and the page-fault line. |
| 1673 | `    rows, p = rows_of(out), []` | `rows`: the output sorted by row type. `p`: the list of problems. |
| 1674 | `    for i, f in enumerate(plan_lines(plan)):` | Loops over the trials of the plan. |
| 1675 | `        ev, numbered = events_of(rows, i)` | `ev`: the events of the trial. `numbered`: whether its `TR` rows are numbered without a hole. |
| 1676 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)` | `w`: the `W` rows of the trial. `e`: its `E` rows. |
| 1677 | `        if not numbered or not ev or len(e) != 1:` | Tests whether the numbers have a hole, the trial has no event, or it does not have exactly one `E` row. |
| 1678 | `            p.append("trial %d: TR rows or E row missing" % i)` | Adds a problem for the trial. |
| 1679 | `            continue` | Continues with the next trial. |
| 1680 | `        p += ["trial %d: %s" % (i, x) for x in trace_problems(f, ev, w, e[0])]` | Adds the problems of `trace_problems` (line 170), each with the trial number in front. |
| 1681 | `        p += ["trial %d: %s" % (i, x) for x in bin_problems(f, w, of_trial(rows, "B", i), {t for n, t in ev if n == "clock"})]` | Adds the problems of `bin_problems` (line 139) with the times of the clock reads of the trace. |
| 1682 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)` | `faults`: the pairs of trial number and count from the comment lines `# minflt,<trial>,<count>`. They give the minor page faults of the worker during each timed sequence. |
| 1683 | `    if faults != [(str(i), "0") for i in range(len(plan_lines(plan)))]:` | Tests whether the list is not exactly one line per trial with the count 0. |
| 1684 | `        p.append("minor page faults in a timed sequence: %s" % faults)` | Adds a problem: minor page faults in a timed sequence. |
| 1685 | `    return p` | Returns the list of problems. |

### `test_hot_copy`, checks m: `--hot-copy` prints the rows of a plain run (lines 1688 to 1715)

| Line | Source | Explanation |
|---:|---|---|
| 1688 | `def test_hot_copy():` | Starts the test `test_hot_copy`. |
| 1689 | `    """(m) --hot-copy: the rows, the byte accounting, the trace rules"""` | Description text: the checks named m for the option `--hot-copy`: the rows, the byte accounting and the trace rules. With the option the function `timed_sequence_hot` runs the windows. Its window loop works on local copies and does not touch the window record between the first and the last pass of a window. |
| 1690 | `    plan = write_plan("hot", ALL)` | Writes the plan `ALL`. |
| 1691 | `    rc0, out0, _ = trial(plan)` | Runs it without the option. |
| 1692 | `    rc, out, err = trial(plan, ["--hot-copy"])` | Runs it with `--hot-copy`. |
| 1693 | `    if not check("m: the plan with all phases runs with status 0 with and without --hot-copy", rc == 0 and rc0 == 0, err):` | Check: the plan with all phases runs with status 0 with and without `--hot-copy`. |
| 1694 | `        return` | Ends the test when a run failed. |
| 1695 | `    check("m: M,hot_copy is 1 with the option and 0 without it", (m_of(out).get("hot_copy"), m_of(out0).get("hot_copy")) == ("1", "0"))` | Check: `M,hot_copy` is 1 with the option and 0 without it. So each result says which of the two timed functions measured it. |
| 1696 | `    check("m: --hot-copy prints the rows of a plain run: comment lines, every M value but hot_copy and the addresses, "` | Check: `--hot-copy` prints the rows of a plain run: the comment lines, every `M` value but `hot_copy` and the addresses ... |
| 1697 | `          "and the S, K, P, W, B, E structure",` | Continues the name of the check: ... and the structure of the `S`, `K`, `P`, `W`, `B` and `E` rows. |
| 1698 | `          structure(out, drop_m=["hot_copy"]) == structure(out0, drop_m=["hot_copy"]),` | Continues the check: the two structures without the row `hot_copy` are equal (line 1481). So the second timed function produces the same kinds of rows, and the analysis reads both in one way. |
| 1699 | `          [x for x in zip(structure(out), structure(out0)) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1700 | `    check("m: that comparison can fail: another plan gives another structure",` | Check: that comparison can fail: another plan gives another structure. |
| 1701 | `          structure(out, drop_m=["hot_copy"]) != structure(trial(write_plan("hot2", ALL[:3]))[1], drop_m=["hot_copy"]))` | Continues the check: the structure of the run with `--hot-copy` differs from that of a run of the first three trials of `ALL`. |
| 1702 | `    p = accounting_problems(plan, out)` | Applies the three row rules to the run with `--hot-copy` (line 1519). |
| 1703 | `    check("m: --hot-copy: byte accounting of every window: whole passes, the 8 MiB rule, durations, monotonic times, "` | Check: with `--hot-copy` the byte accounting of every window holds: whole passes, the 8 MiB rule, durations, rising times ... |
| 1704 | `          "wall_ns and gaps from the W rows, bins that sum to the window bytes", not p, p)` | Continues the check: ... `wall_ns` and the gaps from the `W` rows, and bins that sum to the bytes of the window. `timed_sequence_hot` keeps its own count of bytes and times. This check proves that this second count follows the same rules. |
| 1705 | `    rows = rows_of(out)` | `rows`: the output of the run with `--hot-copy`, sorted by row type. |
| 1706 | `    check("m: --hot-copy: sink_ok is 1 for the trials that ran old read, and no X row",` | Check: with `--hot-copy`, `sink_ok` is `1` for the trials that ran the old read kernel, and no `X` row is printed. |
| 1707 | `          [f[8] for f in rows["E"]] == ["1", "NA", "NA", "1"] and not rows.get("X"), rows.get("X"))` | Continues the check: the values are `1`, `NA`, `NA`, `1`. |
| 1708 | `    check("m: --hot-copy: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",` | Check: with `--hot-copy` the gap before an 8 MiB target is below 20 us in trial 0 or in trial 3. So no kernel pass lies inside the gap. |
| 1709 | `          min(int(rows["E"][0][6]), int(rows["E"][3][6])) < 20000, (rows["E"][0][6], rows["E"][3][6]))` | Continues the check: the smaller of the two gaps is below 20000 ns. |
| 1710 | `    rc, out, err = trial(plan, ["--hot-copy", "--rec-pad", "4000"])` | Runs the plan with `--hot-copy` and `--rec-pad 4000` together. |
| 1711 | `    p = accounting_problems(plan, out) if rc == 0 else ["rc=%s" % rc]` | Applies the row rules, or keeps the exit status as the problem when the run failed. |
| 1712 | `    mm = m_of(out)` | `mm`: the `M` rows of that run. |
| 1713 | `    check("m: --hot-copy together with --rec-pad 4000 runs, both M rows are set, and the byte accounting holds",` | Check: `--hot-copy` together with `--rec-pad 4000` runs, both `M` rows are set, and the byte accounting holds. |
| 1714 | `          not p and (mm.get("hot_copy"), mm.get("rec_pad")) == ("1", "4000"), p)` | Continues the check: no problem, and the values `1` and `4000`. |

### `test_hot_copy`: the trace with `--hot-copy`, and builds with a defect (lines 1716 to 1763)

| Line | Source | Explanation |
|---:|---|---|
| 1716 | `    tplan = write_plan("hottrace", TRACE_PLAN)` | Writes the plan `TRACE_PLAN` to a file. |
| 1717 | `    counted = ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"]` | `counted`: the arguments of a trace run with the two software events: `--trace`, the PMU type 1 and the events `task_clock` and `cpu_clock`. |
| 1718 | `    rc, out, err = trial(tplan, counted + ["--hot-copy"])` | Runs the plan with these arguments and `--hot-copy`. |
| 1719 | `    if not check("m: the trace run with --hot-copy ends with status 0", rc == 0, err):` | Check: the trace run with `--hot-copy` ends with status 0. |
| 1720 | `        return` | Ends the test when it failed. |
| 1721 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 1722 | `    states = [f[9] for f in rows["E"]]` | `states`: the count state of each trial. |
| 1723 | `    check("m: trace with --hot-copy: the count states are closed, read, open, read, closed", states == ["closed", "read", "open", "read", "closed"], states)` | Check: in the trace run with `--hot-copy` the count states are `closed`, `read`, `open`, `read`, `closed`. |
| 1724 | `    p = trace_run_problems(tplan, out)` | Applies the rules of a trace run to every trial (line 1671). |
| 1725 | `    check("m: trace with --hot-copy: no forbidden event in any timed sequence, the W rows, gap_ns and the bin ends are clock "` | Check: in the trace with `--hot-copy` no forbidden event lies in any timed sequence, and the `W` rows, `gap_ns` and the bin ends are clock ... |
| 1726 | `          "reads of the trace, and no minor page fault", not p, p)` | Continues the check: ... reads of the trace, and no minor page fault happened. So `timed_sequence_hot` keeps every rule of the timed path that `timed_sequence` keeps. |
| 1727 | `    reads = [[n for n, _ in events_of(rows, i)[0]].count("count_read") for i in range(5)]` | `reads`: the number of counter reads in the trace of each trial. |
| 1728 | `    check("m: trace with --hot-copy: nwin + 1 counter reads in the trials with count read, none in the others",` | Check: in the trace with `--hot-copy` the trials with the count mode `read` have one more counter read than target windows, and the others have none. |
| 1729 | `          reads == [0, 4, 0, 3, 0], reads)` | Continues the check: the counts are 0, 4, 0, 3 and 0. Trial 1 has 3 target windows and trial 3 has 2. |
| 1730 | `    names = lambda o: [[n for n, _ in events_of(rows_of(o), i)[0]] for i in range(5)]` | `names`: a function that gives the event names of each of the 5 trials of an output. |
| 1731 | `    plain = trial(tplan, counted)[1]` | `plain`: the output of the same trace run without `--hot-copy`. |
| 1733 | `    def no_clock_runs(seqs):` | Starts the inner function `no_clock_runs`. |
| 1734 | `        # the number of clock reads inside a window depends on the speed of the run; the order of the other events does not` | Comment: the number of clock reads inside a window depends on the speed of the run. The order of the other events does not. |
| 1735 | `        return [[n for j, n in enumerate(s) if n != "clock" or j == 0 or s[j - 1] != "clock"] for s in seqs]` | Returns each event list with every run of clock reads cut to one clock read. |
| 1737 | `    check("m: trace with --hot-copy: the events of every trial stand in the order of the plain run (runs of clock reads "` | Check: in the trace with `--hot-copy` the events of every trial stand in the order of the plain run, with runs of clock ... |
| 1738 | `          "counted once)", no_clock_runs(names(out)) == no_clock_runs(names(plain)) and len(names(out)[0]) > 20)` | Continues the check: ... reads counted once. Trial 0 has more than 20 events, so the comparison is not empty. Both timed functions do the same steps in the same order. |
| 1739 | `    # --hot-copy must select timed_sequence_hot(): a defect in that function shows only with the option, and a` | Comment: `--hot-copy` must select `timed_sequence_hot()`. A defect in that function shows only with the option, and a ... |
| 1740 | `    # defect in timed_sequence() only without it. The defect is a warm-up pass before the first target window.` | Comment: ... defect in `timed_sequence()` shows only without it. The defect is a warm-up pass before the first target window. |
| 1741 | `    # The trace does not log it (it does not go through tcall), but the gap before the target then holds one` | Comment: the trace does not log it, as it does not go through `tcall`. But the gap before the target then holds one ... |
| 1742 | `    # pass over 8 MiB, which takes more than 20 us with the stand-in kernels.` | Comment: ... pass over 8 MiB, which takes more than 20 us with the stand-in kernels. |
| 1743 | `    def gap_ok(o):` | Starts the inner function `gap_ok`. It applies the gap rule of line 1708 to an output. |
| 1744 | `        e = rows_of(o).get("E", [])` | `e`: the `E` rows of the output. |
| 1745 | `        return len(e) == 4 and min(int(e[0][6]), int(e[3][6])) < 20000` | Returns true when there are 4 `E` rows and the smaller gap of the trials 0 and 3 is below 20000 ns. |
| 1747 | `    for name, tag, fails_with in ((HOT_SEQ_MUTANTS[0], "hotwarm", True), (SEQ_MUTANTS[0], "warm", False)):` | Loops over two builds: one with the warm-up pass in `timed_sequence_hot`, which must fail with the option, and one with the warm-up pass in `timed_sequence`, which must fail without it. |
| 1748 | `        b = mutant_build(name, tag)` | `b`: the build with that defect. |
| 1749 | `        got = {}` | `got`: the result of the gap rule without and with the option, empty at the start. |
| 1750 | `        for hot in (False, True):` | Loops over the two runs: without and with `--hot-copy`. |
| 1751 | `            o = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + (["--hot-copy"] if hot else []), binary=b) if b else (1, "", "")` | Runs the plan `ALL` with that build. Without a build the status is 1. |
| 1752 | `            got[hot] = o[0] == 0 and gap_ok(o[1])` | Keeps whether the run ended with status 0 and passed the gap rule. |
| 1753 | `        check("m: a build with %s: the gap rule fails %s --hot-copy and passes %s it" %` | Check: for a build with that defect the gap rule fails with `--hot-copy` and passes without it, or the reverse for the other build. |
| 1754 | `              (name, "with" if fails_with else "without", "without" if fails_with else "with"),` | Continues the name of the check: the words `with` and `without` in the right order for this build. |
| 1755 | `              b is not None and not got[fails_with] and got[not fails_with], got)` | Continues the check: the build worked, the rule failed in the run where it must fail and passed in the other one. So the option is proven to choose the function: each defect shows only in the runs that use its function. The gap rule is also proven to find a warm-up pass that the trace cannot show. |
| 1756 | `    b = mutant_build(HOT_OFF_MUTANT, "hotoff")` | `b`: a build in which `--hot-copy` still runs `timed_sequence` (line 429). |
| 1757 | `    o = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1758 | `    check("m: a build with %s fails the self-test only in the touch check of timed_sequence_hot" % HOT_OFF_MUTANT,` | Check: that build fails the self-test only in the touch check of `timed_sequence_hot`. |
| 1759 | `          o[0] == 1 and [x for x in o[1].splitlines() if x.endswith(",FAIL")] ==` | Continues the check: the status is 1, and the list of the failed lines equals ... |
| 1760 | `          ["trial,hot touch: timed_sequence_hot does not touch the window record between the first and the last pass,0,FAIL"],` | Continues the check: ... the one line of the touch test: `timed_sequence_hot` does not touch the window record between the first and the last pass. The rows of such a build have the right form. Only the touch test shows that the wrong function ran. |
| 1761 | `          (o[0], [x for x in o[1].splitlines() if x.endswith(",FAIL")]))` | Continues the check: the status and the failed lines as the detail. |

### `main`: settings, the builds, the order of the tests, the summary (lines 1764 to 1804)

| Line | Source | Explanation |
|---:|---|---|
| 1764 | `def main():` | Starts the function `main`. It prepares the settings and the builds and runs all tests. |
| 1765 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg`, the file in which Linux reports the load averages. |
| 1766 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints a comment line with the three load averages (1, 5 and 15 minutes) and the number of CPUs that the test process may use. |
| 1767 | `    E.allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `E.allowed`: the CPUs from 0 to 119 on which the test process may run, sorted. The runner accepts no CPU above 119. |
| 1768 | `    if len(E.allowed) < 3 or 0 not in E.allowed:` | Tests whether fewer than 3 such CPUs exist, or CPU 0 is not among them. The tests need CPU 0, the default CPU of the controlling thread, and two more CPUs. |
| 1769 | `        print("FAIL setup: CPU 0 and two more CPUs from 0 to 119 are needed in the allowed set: %s" % E.allowed)` | Prints a line that starts with `FAIL setup` and shows the allowed CPUs. |
| 1770 | `        return 1` | Returns 1. The script then ends with exit status 1, and no test has run. |
| 1771 | `    E.cpu, E.cpu2 = [c for c in E.allowed if c != 0][:2]  # worker CPU, and a second CPU` | `E.cpu`, `E.cpu2`: the first two allowed CPUs that are not CPU 0. `E.cpu` is the worker CPU of all tests. `E.cpu2` is a second CPU. |
| 1772 | `    E.ctl = E.cpu2                                         # a control CPU that is not the default` | `E.ctl`: that second CPU, as a CPU for the controlling thread that is not the default. |
| 1773 | `    E.absent = next((c for c in range(120) if c not in E.allowed), None)` | `E.absent`: the lowest CPU from 0 to 119 that the test process may not use, or `None` when every one is allowed. |
| 1774 | `    E.tmp = tempfile.mkdtemp(prefix="bwx10-test-")` | `E.tmp`: a new temporary folder whose name starts with `bwx10-test-`. All builds and all files of the tests go there. |
| 1775 | `    E.bin, E.bin_old, E.bin8 = os.path.join(E.tmp, "bwx10"), os.path.join(E.tmp, "bwx"), os.path.join(E.tmp, B8)` | `E.bin`, `E.bin_old`, `E.bin8`: the paths of three binaries in the temporary folder: `bwx10` (the runner under test), `bwx` (the first runner) and `bwx8` (the accepted runner). |
| 1776 | `    print("# worker CPU %d, control CPU 0 (default) or %d, temporary folder %s" % (E.cpu, E.ctl, E.tmp))` | Prints a comment line with the worker CPU, the two possible CPUs of the controlling thread (0 by default, or `E.ctl`) and the temporary folder. |
| 1777 | `    try:` | Starts a block whose end (line 1792) always runs, also after an error. |
| 1778 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin, os.path.join(HERE, "bwx10.c")], stdout=subprocess.PIPE,` | Compiles `bwx10.c` with `gcc` and the flags `CFLAGS` into `E.bin`. |
| 1779 | `                           stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that runs the compiler: its messages are collected as one text. |
| 1780 | `        if not check("build: bwx10.c compiles with the flags of build10.sh and no compiler message", r.returncode == 0 and r.stdout == "", r.stdout):` | Check: `bwx10.c` compiles with the flags of `build10.sh` and with no compiler message. A warning counts as a failure. |
| 1781 | `            return 1` | Returns 1 when the build failed. No test can run without the binary. |
| 1782 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin_old, os.path.join(OLD, "bwx.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)` | Compiles `bwx.c`, the first runner, into `E.bin_old`. |
| 1783 | `        if not check("build: bwx.c compiles (reference for the --seq mode)", r.returncode == 0):` | Check: `bwx.c` compiles. Its binary is the reference for the checks of the mode `--seq`. |
| 1784 | `            return 1` | Returns 1 when that build failed. |
| 1785 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin8, os.path.join(X8, B8 + ".c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)` | Compiles the source of the accepted runner into `E.bin8`. |
| 1786 | `        if not check("build: the source of the accepted runner compiles (reference for the layout and the kernel list)", r.returncode == 0):` | Check: the source of the accepted runner compiles. Its binary is the reference for the layout and for the list of kernels. |
| 1787 | `            return 1` | Returns 1 when that build failed. |
| 1788 | `        for test in (test_source, test_selftest, test_selftest_rows, test_bad_plans, test_rows, test_sequence_code,` | Loops over the test functions in the order in which they run. This line names the first six: the source, the self-test, the row checks of the self-test, the bad plans, the rows and the timed sequence in the code. |
| 1789 | `                     test_trace, test_counters, test_disturbed, test_placement, test_kill_and_seq, test_listing_saved,` | Continues the list of the tests: the trace, the counters, the disturbed trial, the placement, the killed trial with the interval mode, and the saved listing. |
| 1790 | `                     test_build_scripts, test_new_kernels, test_rec_pad, test_hot_copy):` | Continues the list of the tests: the build scripts, the kernels of round 3, `--rec-pad` and `--hot-copy`. |
| 1791 | `            test()` | Runs the test. A failed check does not stop the loop. An earlier test can store a value in `E` for a later one, as `test_trace` does for `test_counters`. |
| 1792 | `    finally:` | The next lines run in every case, also when a test raised an error or `main` returned early. |
| 1793 | `        if os.environ.get("KEEP"):` | Tests whether the environment variable `KEEP` is set to a text that is not empty. |
| 1794 | `            print("# kept: %s" % E.tmp)` | Prints the path of the temporary folder, which is kept. |
| 1795 | `        else:` | If `KEEP` is not set: |
| 1796 | `            shutil.rmtree(E.tmp, ignore_errors=True)` | Deletes the temporary folder with all its content. Errors of the delete are ignored. |
| 1797 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg` again. |
| 1798 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints a comment line with the three load averages at the end. |
| 1799 | `    print("# checks failed: %d%s" % (len(failed), "".join("\n#   " + n for n in failed)))` | Prints the number of failed checks, and under it one line per failed check with its name. |
| 1800 | `    return 1 if failed else 0` | Returns 1 when a check failed, and 0 when none failed. |
| 1803 | `if __name__ == "__main__":` | Tests whether the file runs as a script, and is not loaded as a module by another file. |
| 1804 | `    sys.exit(main())` | Calls `main` and ends the script with its result as the exit status. |
