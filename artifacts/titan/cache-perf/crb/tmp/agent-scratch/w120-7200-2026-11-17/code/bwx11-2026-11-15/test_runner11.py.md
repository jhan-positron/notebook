# `test_runner11.py` explained, line by line

- Source file: `bwx11-2026-11-15/test_runner11.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 2267 lines, 151801 bytes).
- sha256 of the source when this page was built: `d424a7788d7c22527edb04f106f55df9cac02095d8a247a23d71ca9cffb63c71`.

## Short version: purpose

`test_runner11.py` holds the local tests of the runner `bwx11` and of its listing check `check_listing11.py`. The tests build the runner on the development machine and check its plan parser, its output rows, its timed sequence, its options and its build script. They prove that the harness counts bytes and times in the right way, and they measure no rate, as the kernels of a local build are stand-in loops.

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
- **Round 3, round 4**: two later sets of experiments of that investigation. Round 3 added the runner `bwx10` with the prefetch kernels, `read_1pl`, `--rec-pad` and `--hot-copy`. Round 4 added the runner `bwx11` with the nop kernels and `--evict-mb`.
- **Accepted runner**: in this file the runner `bwx8` of rounds 1 and 2. The later runners are compared with it.
- **`ref-bwx8`, `ref-bwx10`**: two folders beside the test file. They hold saved files of the accepted builds of `bwx8` and `bwx10`: the machine-code listing, the offsets table and the build record.
- **`bwx10` source**: the text of `bwx11.c` and of `bwx11_selftest.c` without their marked blocks. The tests build it as the binary `bwx10`.
- **Marked block**: a part of a source file between a comment line `bwx11+` and a comment line `bwx11-`, or between `bwx10+` and `bwx10-`. Every addition of a round stands in such a block.
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
- **`--evict-mb`, evict step**: an option of the trial mode. Before the first trial the worker maps that many MiB of other memory, writes it twice and unmaps it.
- **nop kernels**: `read_nop64`, `read_nop96` and `read_nop128`: the `asmread` loop with 64, 96 and 128 `nop` instructions per loop pass. A `nop` does nothing.
- **Prefetch kernels**: `read_pf256`, `read_pf512`, `read_pf1024` and `read_pf2048`: the `asmread` loop with one software prefetch per 64-byte line.
- **Rule**: a function of this file that returns a list of problems. An empty list means that the rows are right.
- **Defect**: an entry of the table `MUTANTS`: a copy of the runner source with one change that a check must find.
- **Loop offset**: the address of the first instruction of a loop modulo 64.
- **Pad**: zero bytes that the source puts before a function. They make the function start at a planned address modulo 64.
- **Placement**: the start addresses modulo 64 of the functions from `call` to the timed functions. `call` is the function that starts a kernel.
- **Listing check**: the script `check_listing11.py`. Part 1 compares the machine-code listing of a build with the accepted listing. Part 2 checks the loops of the new kernels.
- **Offsets table**: the file `offsets.tsv` of a build: one row per kernel with the start address, the loop start and the loop start modulo 64.
- **Build record**: the file `build.txt` that the build script writes: compiler, flags, compiler messages, self-test result, branch targets, placement and checksums.
- **Logging library**: the C text `SHIM`. A test loads it into the runner with `LD_PRELOAD`. It logs the calls `sched_setaffinity` and `mmap`, and it can let `madvise` fail.
- **PMU type**: the number by which Linux names a group of counters. In these tests type 1 means the software events of Linux.
- **Context switch**: Linux takes a thread off its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: happens when a thread uses a page that Linux has not yet assigned to it.
- **Resident set size**: the part of the memory of a process that lies in physical memory.
- **Address randomization**: Linux gives the stack and the mapped memory of each new process other addresses. `setarch -R` switches this off for one program.
- **Stack guard**: a value that the compiler puts on the stack of a function and tests before the function returns. `__stack_chk_fail` is called when it was overwritten.
- **FNV-1a**: a simple hash function. The runner prints the 64-bit FNV-1a hash of the bytes of its plan file.

## Main flow

1. The file starts with its description, the imports and the constants: the folders of the sources and of the reference builds, the names of the added kernels and `M` rows, and the compiler flags (lines 1 to 71).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed functions, and the order of pin and memory mapping (lines 115 to 365).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner (lines 368 to 531).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row (lines 534 to 620).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows (lines 629 to 720).
6. `test_sequence_code`: the source text and the machine code of the timed functions hold only the allowed calls, and both rules fail on a build with a defect (lines 723 to 751).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches (lines 754 to 768).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported (lines 771 to 803).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces (lines 812 to 895).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window (lines 898 to 947).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints (lines 950 to 988).
12. `test_source`: `bwx11.c` is the accepted source plus marked additions, the older kernels keep their start, size and order, and the code after the kernels keeps its placement (lines 1019 to 1165).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect (lines 1168 to 1230).
14. `test_listing_saved`: the listing check accepts a good listing and rejects each kind of changed kernel and each wrong new kernel (lines 1293 to 1470).
15. `test_build_scripts`: `build11.sh` stops on the marker file, writes its files, rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must (lines 1473 to 1629).
16. `test_new_kernels`: the five kernels of round 3 work in the plan parser, in the trial mode and in the interval mode (lines 1683 to 1718).
17. `test_rec_pad`: `--rec-pad` moves the window records by exactly its value and moves nothing else (lines 1721 to 1818).
18. `test_hot_copy`: `--hot-copy` prints the rows of a plain run, keeps every rule, and selects the second timed function (lines 1845 to 1918).
19. `test_nop_kernels`: the three kernels of round 4 work in the plan parser, in the trial mode and in the interval mode (lines 1921 to 1952).
20. `test_evict`: the evict step writes its memory, lies before the first trial and outside every timed sequence, and changes no other row and no address (lines 2004 to 2212).
21. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds four binaries, runs the 18 tests, deletes the temporary folder and prints the number of failed checks (lines 2215 to 2263).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them (lines 2219 to 2221), or when one of the four first builds fails (lines 2232 to 2250).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` (line 613, line 922, lines 1601 to 1603, line 1785, line 2173).
- A test that raises a Python error ends the script. The temporary folder is still deleted (lines 2255 to 2259), but the summary lines of lines 2260 to 2262 are not printed.
- `main` does not run the tests in file order (lines 2251 to 2253). `test_source` and the two self-test tests run first.
  - `test_trace` sets `E.soft_counters`, which `test_counters` reads (line 824, line 921).
  - `test_source` sets `E.call8` and builds `E.bin10_placed`, which `test_build_scripts` needs (line 1116, lines 1155 to 1156, lines 1600 to 1602).
- The tests write only into a new temporary folder (line 2225). It is deleted at the end unless the variable `KEEP` is set.
- The tests read the folders `ref-bwx8` and `ref-bwx10` beside the test file (lines 54 to 55). The README of the repo says that the `ref-` folders were left out of the repo copy. So `test_source` cannot read its reference files from this copy.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text is no longer found in the source makes its checks fail (lines 273 to 274, lines 468 to 469).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the build script under `bash`, and `setarch`. A run that the helper `run` starts may last 120 s at most (line 510).
- Two tests load the machine on purpose. `test_disturbed` runs an endless loop on the worker CPU during one trial (line 757). `test_evict` runs an evict step of 256 MiB (line 2070) and one of 4096 MiB, which writes 4 GiB of memory twice (line 2209).
- At these places the text and the code do not match.
  - The comment of line 1195 names a build that counts one pass too many per clock read. The two defects that the code builds are others (lines 1201 to 1202).
  - The name of the check of lines 2096 to 2097 says that the evict step is the last `mmap` before the trials. The condition of lines 2098 to 2099 does not test that part.
  - The test `src is None` of line 273 has no effect, as line 272 already used `src`.
  - The name of the check of line 838 says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them (line 839). The check of lines 832 to 833 tests where they lie.
  - The name of the check of lines 1931 to 1932 says that the plan uses every nop kernel as previous activity, prefix, predecessor and target. In the plan of lines 1923 to 1926 `read_nop128` is never the previous activity, `read_nop64` never the prefix and `read_nop96` never the predecessor.
  - The names of the checks of line 1370, line 1372, lines 1378 to 1379 and line 1391 say that a text stands in `k_oldread` and `k_oldread2`. Each condition only tests that the text stands 2 times in the whole listing.

## Source and explanation, line by line

- Text shown: the file `bwx11-2026-11-15/test_runner11.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (2267 lines, 151801 bytes, sha256 `d424a7788d7c22527edb04f106f55df9cac02095d8a247a23d71ca9cffb63c71`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text of the file (lines 1 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_runner11.py - local tests of the runner bwx11 (round 4).` | Starts the description text of the file. It ends in line 39. This line: the file holds the local tests of the runner `bwx11`. Round 4 is the fourth set of experiments of the investigation into the buffer size of 8 MiB. |
| 4 | `It is test_runner10.py with the names of bwx11, plus the checks of round 4:` | Description text: this file is `test_runner10.py`, the test file of the runner before this one, with the names of `bwx11`. The checks of round 4 are added. Lines 5 to 6 name them. |
| 5 | `the three kernels read_nop64, read_nop96, read_nop128, the option --evict-mb,` | Description text: the first two additions. The kernels `read_nop64`, `read_nop96` and `read_nop128` are the loop of `asmread` with 64, 96 and 128 `nop` instructions, which do nothing. With the option `--evict-mb` the worker thread writes other memory before the first trial. The purpose of that step is to move the benchmark buffer out of the caches. |
| 6 | `and check_listing11.py on synthetic listings. Every check of test_runner10.py` | Description text: the third addition. The script `check_listing11.py` is the check of the machine-code listing of a build. The tests run it on listings that this file builds itself. A new sentence starts: every check of `test_runner10.py` ... |
| 7 | `is kept. Where bwx11 differs from bwx10 by design, the check was changed and` | Description text: ... is kept. Where `bwx11` differs from `bwx10` on purpose, the check was changed ... |
| 8 | `says so:` | Description text: ... and its name says so. Lines 9 to 20 list the four changes. |
| 9 | ` - "source": bwx11.c without its blocks "bwx11+" to "bwx11-" must be the` | Description text, change 1: the checks named `source`. In `bwx11.c` every addition stands between a comment line `bwx11+` and a comment line `bwx11-`. Without these blocks the file must be ... |
| 10 | `   accepted bwx10.c (its sha256 stands in ref-bwx10/build.txt). That text` | Description text: ... the accepted `bwx10.c`. Its sha256 stands in `ref-bwx10/build.txt`, the build record of the accepted build of `bwx10`. A new sentence starts: that text ... |
| 11 | `   without its blocks "bwx10+" to "bwx10-" must be bwx8.c, as before;` | Description text: ... without its blocks `bwx10+` to `bwx10-` must be `bwx8.c`. The test file of `bwx10` had the same check. |
| 12 | ` - counts: 29 kernels (21 of bwx8, 5 of round 3, 3 of round 4), 33 trial` | Description text, change 2: the counts. `bwx11` has 29 kernels: 21 of `bwx8`, 5 of round 3 and 3 of round 4. The self-test has 33 ... |
| 13 | `   checks of the self-test, 2 more M rows (evict_mb, evict_ns);` | Description text: ... checks of the trial mode. The output has 2 more `M` rows, `evict_mb` and `evict_ns`. |
| 14 | ` - the listing checks use the accepted listing of bwx10 (ref-bwx10) and add` | Description text, change 3: the listing checks use the accepted listing of `bwx10` as the reference. It lies in the folder `ref-bwx10`. They add ... |
| 15 | `   well-formed listings of the three new kernels. The checks on the prefetch` | Description text: ... well-formed listings of the three new kernels. A new sentence starts: the checks on the prefetch ... |
| 16 | `   kernels of check_listing10.py part 2 became checks on the nop kernels,` | Description text: ... kernels, which were part 2 of `check_listing10.py`, became checks on the nop kernels. |
| 17 | `   because those prefetch kernels are now part of the reference;` | Description text: the reason. The prefetch kernels are now part of the reference. So part 1 of the listing check compares them. |
| 18 | ` - the comparison of a real local listing uses a local build of the bwx10` | Description text, change 4: the comparison of a real listing of the local machine uses a local build of the `bwx10` ... |
| 19 | `   source (bwx11.c without its marked blocks) as the reference, with 26` | Description text: ... source as the reference. That source is `bwx11.c` without its marked blocks. The reference has 26 kernels. |
| 20 | `   kernels, in place of the build of bwx.c with 21 kernels.` | Description text: before this change the reference was a build of `bwx.c`, the first runner, with 21 kernels. |
| 22 | `Runs on the development machine (x86-64). It builds bwx11.c with the flags of` | Description text: the tests run on the development machine, which has x86-64 processors and not Arm processors. They build `bwx11.c` with the compiler flags of the build script `build11.sh`. |
| 23 | `build11.sh into a temporary folder. The read kernels are then plain C stand-in` | Description text: the build goes into a temporary folder. On this machine the read kernels are plain C loops that replace the Arm code. |
| 24 | `loops, so rates mean nothing. The tests check the harness: the plan checks,` | Description text: so a rate of such a build means nothing. The tests check the harness, which is the code around the kernels. The list of the checked parts starts: the checks of the plan file. |
| 25 | `the rows, the timed sequence, the trace, the bins, the counter states, the` | Description text: the list goes on: the output rows, the timed sequence, the trace, the bins, the counter states. |
| 26 | `evict step, and the two build scripts.` | Description text: the end of the list: the evict step and the two build scripts. By the description of `test_build_scripts` (line 1474) these are `build11.sh` and `check_listing11.py`. |
| 28 | `Usage: test_runner11.py            (KEEP=1 keeps the temporary folder)` | Description text: the usage. The file takes no argument. When the environment variable `KEEP` is set, the temporary folder is kept at the end. |
| 29 | `Output: one line per check, "PASS name" or "FAIL name: detail".` | Description text: the output. Each check prints one line: `PASS` and its name, or `FAIL`, its name and a detail. |
| 30 | `Exit status: 0 only if every check passed.` | Description text: the exit status is 0 only when every check passed. |
| 32 | `A rule that the tests check on the output of bwx11 is a function that returns` | Description text: how a rule is tested. A rule that the tests apply to the output of `bwx11` is a function that returns ... |
| 33 | `a list of problems. Each such function is also run on changed rows, where it` | Description text: ... a list of problems. Each such function is also run on rows that the test changed on purpose ... |
| 34 | `must report a problem. So a rule that could not fail would be seen.` | Description text: ... and it must report a problem there. So a rule that can never fail would be found. |
| 36 | `Some rules cannot be shown to fail on changed rows, because the defect is in` | Description text: some rules cannot be shown to fail on changed rows. The reason: the defect would be in ... |
| 37 | `bwx11.c itself. For these the test builds a copy of bwx11.c with one defect` | Description text: ... `bwx11.c` itself. For these rules the test builds a copy of `bwx11.c` with one defect. |
| 38 | `(MUTANTS) and requires that the check fails on it.` | Description text: the table `MUTANTS` holds these defects. The check must fail on such a copy. |
| 39 | `"""` | Ends the description text. |

### Imports, folders, names of kernels and rows, compiler flags (lines 40 to 73)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `import hashlib` | Loads the Python module `hashlib`. The function `sha256` (line 1004) computes checksums with it. |
| 41 | `import os` | Loads `os`: paths, folders, the environment and the CPU list of the process. |
| 42 | `import re` | Loads `re`: regular expressions, which are patterns for text. |
| 43 | `import resource` | Loads `resource`: it limits the memory address space of a program that the tests start. |
| 44 | `import shutil` | Loads `shutil`: it copies files and deletes the temporary folder. |
| 45 | `import signal` | Loads `signal`: the numbers of the Linux signals. The tests use the signal `SIGKILL`, which ends a process immediately. |
| 46 | `import subprocess` | Loads `subprocess`: it starts other programs (the compiler, the runner, `objdump`, `nm`) and collects their output. |
| 47 | `import sys` | Loads `sys`: the path of the Python interpreter and the exit of the script. |
| 48 | `import tempfile` | Loads `tempfile`: it creates the temporary folder. |
| 49 | `import time` | Loads `time`: waits and time limits. |
| 51 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this test file. The sources under test are read from it. |
| 52 | `OLD = os.path.join(HERE, "..", "bwx-2026-11-13")` | `OLD`: the folder `bwx-2026-11-13` beside the folder of this file. It holds the first runner, `bwx`. The tests only read it. |
| 53 | `X8 = os.path.join(HERE, "..", "bwx8-2026-11-14")  # the accepted runner of rounds 1 and 2; only read` | `X8`: the folder of the runner `bwx8`. The comment calls it the accepted runner of rounds 1 and 2. The tests only read it. |
| 54 | `REF = os.path.join(HERE, "ref-bwx8")` | `REF`: the folder `ref-bwx8` beside this file. It holds the machine-code listing of the accepted build of `bwx8`. |
| 55 | `REF10 = os.path.join(HERE, "ref-bwx10")  # the accepted build of bwx10: listing.txt, offsets.tsv, build.txt` | `REF10`: the folder `ref-bwx10` beside this file. By the comment it holds three files of the accepted build of `bwx10`: `listing.txt` (the machine-code listing), `offsets.tsv` (the table of the loop addresses) and `build.txt` (the build record). |
| 56 | `B8 = "bwx8"` | `B8`: the name of the accepted runner. The tests build file names from it. |
| 57 | `B10 = "bwx10"` | `B10`: the name of the runner of round 3. The tests build file names from it. |
| 58 | `NEW_KERNELS = ["read_pf256", "read_pf512", "read_pf1024", "read_pf2048", "read_1pl"]  # round 3` | `NEW_KERNELS`: the five kernels that round 3 added. The four `read_pf` kernels are the `asmread` loop with one software prefetch per 64-byte line, 256 to 2048 bytes ahead. `read_1pl` loads 16 bytes of every 64-byte line. |
| 59 | `NOP_KERNELS = ["read_nop64", "read_nop96", "read_nop128"]  # round 4` | `NOP_KERNELS`: the three kernels that round 4 added. |
| 60 | `NOPS = {"read_nop64": 64, "read_nop96": 96, "read_nop128": 128}` | `NOPS`: the number of `nop` instructions that the loop of each of these kernels must hold. |
| 61 | `NEW_M = ["rec_pad", "hot_copy", "rec_addr", "win_addr", "win_size", "stack_addr", "buf_addr", "tw_addr"]  # round 3` | `NEW_M`: the keys of the 8 `M` rows that round 3 added. An `M` row is one line of settings in the output of the runner, in the form `M,key,value`. |
| 62 | `NEW_M11 = ["evict_mb", "evict_ns"]  # round 4` | `NEW_M11`: the keys of the 2 `M` rows that round 4 added. `evict_mb` holds the value of the option `--evict-mb`. `evict_ns` holds the duration of the evict step in ns. |
| 63 | `ADDR_KEYS = ("rec_addr", "win_addr", "stack_addr", "buf_addr", "tw_addr")` | `ADDR_KEYS`: the keys of the five `M` rows that hold a memory address. An address can differ from process to process. So the comparisons of two runs leave these values out. |
| 64 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags, split into a list. `-O3` is the highest standard optimization level. `-march=native` allows the instructions of the build machine. `-fno-tree-loop-distribute-patterns` stops `gcc` from replacing a loop by a call of `memset` or `memcpy`. `-pthread` adds thread support. `-Wall -Wextra` switch the warnings on. `-std=gnu11` selects the C dialect. |
| 65 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues line 64. `-fno-ipa-icf`: `gcc` keeps two functions with equal code as two functions. `-fno-toplevel-reorder`: the functions stay in the order of the source, so each kernel keeps its place in the binary. `-falign-functions=4`: a function start is aligned to 4 bytes only, so the pad bytes in the source decide where a kernel starts. |
| 66 | `MIB8 = 8 << 20` | `MIB8`: 8 MiB in bytes (8388608). It is the buffer size of most tests. The runner also reads the clock after each 8 MiB of reads. |
| 67 | `HEAD1 = "# bwx8-plan v1"` | `HEAD1`: the first line that every plan file must have. It names the format of the plan. |
| 68 | `HEAD3 = "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `HEAD3`: the third line that every plan file must have. It names the 11 fields of a trial line. |
| 69 | `SUFFIX = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `SUFFIX`: the factor of each size letter. `K` is 1024, `M` is 1048576 (1 MiB) and `G` is 1073741824. |
| 71 | `failed = []` | `failed`: the list of the names of the checks that failed. It is empty at the start. |

### Helpers: `check`, `size_of`, `expected_windows`, `rows_of`, `of_trial` (lines 74 to 112)

| Line | Source | Explanation |
|---:|---|---|
| 74 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it with a name, a result (`ok`) and an optional detail. |
| 75 | `    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))` | Prints one line: `PASS` or `FAIL`, then the name. On a failure with a detail it adds a colon and the first 400 characters of the detail. |
| 76 | `    if not ok:` | Tests whether the check failed. |
| 77 | `        failed.append(name)` | Adds the name of the failed check to the list `failed`. The exit status of the file depends on this list. |
| 78 | `    return ok` | Returns `ok`. A caller can stop its test when a step that it needs has failed. |
| 81 | `def size_of(text):` | Starts the function `size_of`. It turns a size text of a plan, such as `8M` or `1000`, into a number of bytes. |
| 82 | `    return int(text[:-1]) * SUFFIX[text[-1]] if text[-1] in SUFFIX else int(text)` | Returns the number of bytes. When the last character is `K`, `M` or `G`, the number before it is multiplied by the factor of `SUFFIX`. If not, the whole text is the number. |
| 85 | `def expected_windows(f):` | Starts the function `expected_windows`. From the fields `f` of one trial line of a plan it builds the list of the windows that the runner must run for that trial. A window is one timed period in which one kernel reads one range again and again. |
| 86 | `    """[(phase, widx, kernel, pass_bytes, min_ns)] of one plan line, from its fields"""` | Description text: each entry of the result holds the phase, the window number inside the phase, the kernel, the bytes of one pass and the shortest duration in ns. |
| 87 | `    out = []` | `out`: the list of windows, empty at the start. |
| 88 | `    for phase, text, n in (("prev", f[3], 1), ("prefix", f[4], 4), ("pred", f[5], 1)):` | Loops over the three optional phases in the order in which they run. `prev` is the previous activity (field 3, 1 window). `prefix` is the same preparation before each target (field 4, 4 windows). `pred` is the predecessor, the kernel that runs directly before the target (field 5, 1 window). |
| 89 | `        if text == "-":` | A field that is `-` means that the trial has no such phase. |
| 90 | `            continue` | Continues with the next phase. |
| 91 | `        kernel, rest = text.split("@")` | Splits the field, for example `oldread@8M:40`, at the `@` into the kernel name and the rest. |
| 92 | `        size, ms = rest.split(":")` | Splits the rest at the colon into the size and the duration in ms. |
| 93 | `        out += [(phase, i, kernel, size_of(size), int(ms) // n * 1000000) for i in range(n)]` | Adds the `n` windows of this phase, numbered from 0. Each one has the kernel, the pass size in bytes and its share of the duration in ns: the ms value divided by `n` without a remainder, times 1000000. A prefix of 40 ms gives 4 windows of 10 ms. |
| 94 | `    kernel, size = f[6].split("@")` | Splits the target field (field 6), for example `oldread@8M`, into the kernel and the size. The target is the kernel whose rate is measured. Its field has no duration. |
| 95 | `    out += [("target", i, kernel, size_of(size), int(f[8]) * 1000000) for i in range(int(f[7]))]` | Adds the target windows. Field 7 (`nwin`) is their number. Field 8 (`win_ms`) is the requested duration of each one in ms. |
| 96 | `    return out` | Returns the list. |
| 99 | `def rows_of(out):` | Starts the function `rows_of`. It sorts the output text of the runner by row type. |
| 100 | `    """{row type: [fields]} of the output of bwx11"""` | Description text: the result is a dictionary. Its key is the row type. Its value is the list of the rows of that type in the output of `bwx11`, each row split into its fields. |
| 101 | `    r = {}` | `r`: the dictionary, empty at the start. |
| 102 | `    for line in out.splitlines():` | Loops over the lines of the output. |
| 103 | `        if line and not line.startswith("#"):` | Takes only a line that is not empty and that is no comment line. A comment line starts with `#`. |
| 104 | `            f = line.split(",")` | Splits the row at the commas into its fields. |
| 105 | `            r.setdefault(f[0], []).append(f)` | Appends the row to the list of its row type. The row type is the first field, for example `W` or `E`. |
| 106 | `    return r` | Returns the dictionary. |
| 109 | `def of_trial(rows, kind, trial):` | Starts the function `of_trial`. It picks the rows of one type that belong to one trial. |
| 110 | `    return [f for f in rows.get(kind, []) if f[1] == str(trial)]` | Returns the rows of the type `kind` whose second field is the trial number. A row type that the output does not hold gives an empty list. |

### Rule `window_problems`: the `W` rows of one trial against its plan line (lines 113 to 135)

| Line | Source | Explanation |
|---:|---|---|
| 113 | `# ---- rules ----` | Comment: the rules start here. A rule is a function that returns a list of problems. An empty list means that the rule holds. |
| 115 | `def window_problems(plan_fields, wrows):` | Starts the rule `window_problems`. It compares the `W` rows of one trial with the plan line of that trial. A `W` row is the record of one window: phase, window number, kernel, bytes of one pass, bytes read, start time and end time. |
| 116 | `    """W rows of one trial against its plan line"""` | Description text: the `W` rows of one trial are compared with its plan line. |
| 117 | `    exp, p, prev_end = expected_windows(plan_fields), [], None` | `exp`: the windows that the plan line asks for (line 85). `p`: the list of problems. `prev_end`: the end time of the window before, not set yet. |
| 118 | `    if len(wrows) != len(exp):` | Tests whether the number of `W` rows equals the number of planned windows. |
| 119 | `        return ["%d W rows, %d expected" % (len(wrows), len(exp))]` | If not, the rule returns this one problem. With a lost or an added window the pairs of the next loop would not match. |
| 120 | `    for w, e in zip(wrows, exp):` | Loops over the rows and the planned windows in pairs. |
| 121 | `        phase, widx, kernel, pb, by, t0, t1 = w[2], int(w[3]), w[4], int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the fields of the row: the phase, the window number, the kernel, the bytes of one pass (`pb`), the bytes read (`by`), the start time `t0` and the end time `t1`. Both times are in ns, counted from the start of the process. |
| 122 | `        if (phase, widx, kernel, pb) != e[:4]:` | Tests that the row names the planned phase, window number, kernel and pass size. This proves that the runner ran the kernel of the plan on the range of the plan. |
| 123 | `            p.append("window %s %d %s %d, expected %s" % (phase, widx, kernel, pb, e[:4]))` | Adds a problem that shows the row and the planned values. |
| 124 | `        if by <= 0 or by % pb:` | Tests the byte count: it must be above 0 and a whole number of passes. A rate is the bytes divided by the time. So a wrong byte count gives a wrong rate. |
| 125 | `            p.append("%s %d: %d bytes is not a whole number of passes above 0" % (phase, widx, by))` | Adds a problem with the phase, the window number and the byte count. |
| 126 | `        if MIB8 % pb == 0 and by % MIB8:` | The 8 MiB rule. The runner reads the clock after 8 MiB of reads. So when the pass size divides 8 MiB, the bytes of a window must be a multiple of 8 MiB. |
| 127 | `            p.append("%s %d: %d bytes is not a multiple of 8 MiB" % (phase, widx, by))` | Adds a problem with the byte count. |
| 128 | `        if t1 - t0 < e[4]:` | Tests the duration: the end time minus the start time must be at least the requested time. A window ends at the first clock read at or after its requested duration. So it can last longer, but never shorter. |
| 129 | `            p.append("%s %d: lasts %d ns, requested %d ns" % (phase, widx, t1 - t0, e[4]))` | Adds a problem with the measured and the requested duration in ns. |
| 130 | `        if not t0 < t1 or (prev_end is not None and t0 < prev_end):` | Tests the order of the times. The start must lie before the end. The window must not start before the window before it ended. |
| 131 | `            p.append("%s %d: timestamps go back" % (phase, widx))` | Adds a problem that says that the time stamps go back. |
| 132 | `        prev_end = t1` | Keeps the end time for the test of the next window. |
| 133 | `    return p` | Returns the list of problems. |

### Rule `e_problems`: the `E` row of one trial against its `W` rows (lines 136 to 152)

| Line | Source | Explanation |
|---:|---|---|
| 136 | `def e_problems(plan_fields, wrows, erow):` | Starts the rule `e_problems`. It computes three values of the `E` row again from the `W` rows. The `E` row is the summary row that ends a trial. |
| 137 | `    """E row of one trial against its W rows: wall time and the two gaps"""` | Description text: the rule covers the wall time and the two gap values of the `E` row. |
| 138 | `    p = []` | `p`: the list of problems. |
| 139 | `    g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. Field 7 of the plan line is the number of target windows. |
| 140 | `    t0 = [int(w[7]) for w in wrows]` | `t0`: the start times of all windows, in ns. |
| 141 | `    t1 = [int(w[8]) for w in wrows]` | `t1`: the end times of all windows, in ns. |
| 142 | `    if int(erow[2]) != t1[-1] - t0[0]:` | Tests `wall_ns` (field 2 of the `E` row): it must be the end of the last window minus the start of the first window. |
| 143 | `        p.append("wall_ns %s, W rows give %d" % (erow[2], t1[-1] - t0[0]))` | Adds a problem with both values. |
| 144 | `    gap = "NA" if g == 0 else str(t0[g] - t1[g - 1])` | Computes the expected `gap_ns`: the start of target window 0 minus the end of the window before it. In this gap no kernel runs. The gap is the time between the two clock reads at that boundary. A trial without a window before the target has no gap. Its value is `NA`. |
| 145 | `    if erow[6] != gap:` | Tests field 6 of the `E` row against this value, as text. |
| 146 | `        p.append("gap_ns %s, W rows give %s" % (erow[6], gap))` | Adds a problem with both values. |
| 147 | `    gaps = [t0[i] - t1[i - 1] for i in range(1, len(wrows))]` | `gaps`: the gap at every boundary between two windows of the trial, in ns. |
| 148 | `    if erow[7] != (str(max(gaps)) if gaps else "NA"):` | Tests `max_boundary_gap_ns` (field 7): it must be the largest of these gaps, or `NA` for a trial with one window. |
| 149 | `        p.append("max_boundary_gap_ns %s, W rows give %s" % (erow[7], max(gaps) if gaps else "NA"))` | Adds a problem with both values. |
| 150 | `    return p` | Returns the list of problems. |

### Rule `bin_problems`: the `B` rows of one trial (lines 153 to 183)

| Line | Source | Explanation |
|---:|---|---|
| 153 | `def bin_problems(plan_fields, wrows, brows, clock_times=None):` | Starts the rule `bin_problems`. It checks the `B` rows of one trial. A `B` row is one time bin inside a target window: the window number, the bin number, the end time of the bin and the bytes read from the window start to that time. |
| 154 | `    """B rows of one trial. clock_times: the times of the clock reads of the trace, if there is one."""` | Description text: `clock_times` holds the times of the clock reads of the trace, when the run has a trace. |
| 155 | `    p = []` | `p`: the list of problems. |
| 156 | `    targets = [w for w in wrows if w[2] == "target"]` | `targets`: the `W` rows of the target windows. Only a target window can have bins. |
| 157 | `    if plan_fields[10] == "0":` | Field 10 of the plan line is the bins switch. `0` means that the trial has no bins. |
| 158 | `        return ["B rows in a trial without bins"] if brows else []` | For such a trial the rule ends here. It returns one problem when any `B` row exists, and no problem if none exists. |
| 159 | `    for w in targets:` | Loops over the target windows. |
| 160 | `        pb, by, t0, t1 = int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the pass size, the bytes, the start time and the end time of the window from its `W` row. |
| 161 | `        bins = [b for b in brows if b[2] == w[3]]` | `bins`: the `B` rows of this window. Field 2 of a `B` row is the window number. |
| 162 | `        if not bins:` | Tests whether the window has no bin at all. |
| 163 | `            p.append("window %s has no bin" % w[3])` | Adds a problem that names the window. |
| 164 | `            continue` | Continues with the next window. |
| 165 | `        ends, cum = [int(b[4]) for b in bins], [int(b[5]) for b in bins]` | `ends`: the end times of the bins in ns. `cum`: the bytes from the window start to each bin end. |
| 166 | `        if [int(b[3]) for b in bins] != list(range(len(bins))):` | Tests that the bins are numbered 0, 1, 2 and so on, without a hole. |
| 167 | `            p.append("window %s: bin numbers are not 0, 1, 2, ..." % w[3])` | Adds a problem that names the window. |
| 168 | `        if ends != sorted(set(ends)) or ends[0] <= t0 or ends[-1] != t1:` | Tests the bin ends. They must rise strictly. The first one must lie after the window start. The last one must equal the window end. So the bins cover the whole window. |
| 169 | `            p.append("window %s: bin ends do not rise to the end of the window" % w[3])` | Adds a problem that names the window. |
| 170 | `        per_bin = [c - d for c, d in zip(cum, [0] + cum[:-1])]` | `per_bin`: the bytes of each bin alone. It is the difference of two neighbour values of `cum`. |
| 171 | `        if sum(per_bin) != by or min(per_bin) <= 0:` | Tests that the bins sum to the bytes of the window and that every bin holds more than 0 bytes. So no byte is lost or counted twice when a rate is computed per bin. |
| 172 | `            p.append("window %s: the bins sum to %d bytes, the window has %d" % (w[3], sum(per_bin), by))` | Adds a problem with the sum of the bins and the bytes of the window. |
| 173 | `        if any(b % pb for b in per_bin):` | Tests that every bin holds whole passes. |
| 174 | `            p.append("window %s: a bin does not hold whole passes" % w[3])` | Adds a problem that names the window. |
| 175 | `        if len(bins) > 1 and ends[0] - t0 < 10000000:` | When a window has more than one bin, bin 0 must last at least 10000000 ns. That is 10 ms, the requested width of a bin. |
| 176 | `            p.append("window %s: bin 0 is shorter than 10 ms" % w[3])` | Adds a problem that names the window. |
| 177 | `        if clock_times is not None and any(e not in clock_times for e in ends):` | Only with a trace: every bin end must be the time of a clock read of the trace. This proves that a bin closes on a clock read that the window loop makes anyway. The bins add no clock read to the timed loop. |
| 178 | `            p.append("window %s: a bin end is not a clock read of the trace" % w[3])` | Adds a problem that names the window. |
| 179 | `    if len(brows) != sum(1 for b in brows if b[2] in [w[3] for w in targets]):` | Counts the `B` rows whose window number is the number of a target window. Every `B` row of the trial must be one of them. |
| 180 | `        p.append("B rows of a window that is not a target window")` | Adds a problem: a `B` row belongs to a window that is no target window. |
| 181 | `    return p` | Returns the list of problems. |

### Rule `trace_problems`: the events of the trace of one trial (lines 184 to 250)

| Line | Source | Explanation |
|---:|---|---|
| 184 | `def trace_problems(plan_fields, events, wrows, erow):` | Starts the rule `trace_problems`. It checks the order of the events that a run with `--trace` logged for one trial. `events` is a list of pairs: the event name and its time in ns. |
| 185 | `    """TR events [(name, t)] of one trial. The timed sequence may hold clock` | Description text: the events come from the `TR` rows of one trial. The timed sequence may hold clock ... |
| 186 | `    reads and the first kernel call of each window. With count 'read' it also` | Description text: ... reads and the first kernel call of each window. The trace logs only the first call of a window. A new sentence starts: with the count mode `read` it also ... |
| 187 | `    holds a counter read and a CPU clock read between the end clock and the` | Description text: ... holds a counter read and a read of the thread CPU clock between the end clock read and the ... |
| 188 | `    start clock of each boundary of a target window. Nothing else."""` | Description text: ... start clock read at each boundary of a target window. No other event is allowed. |
| 189 | `    exp, reads, p = expected_windows(plan_fields), plan_fields[9] == "read", []` | `exp`: the planned windows. `reads`: true when the count field of the plan line (field 9) is `read`. `p`: the list of problems. |
| 190 | `    names = [e[0] for e in events]` | `names`: the event names in the order of the trace. |
| 191 | `    kf = [i for i, n in enumerate(names) if n.startswith("kernel_first")]` | `kf`: the positions of the events whose name starts with `kernel_first`. The runner logs one such event at the first kernel call of each window. |
| 192 | `    want = ["kernel_first:%s:%d" % (e[0], e[1]) for e in exp]` | `want`: the names that these events must have, one per planned window, for example `kernel_first:prefix:2`. |
| 193 | `    if [names[i] for i in kf] != want:` | Tests that the trace holds exactly these first calls, in the planned order. |
| 194 | `        return ["kernel calls %s, expected %s (a warm-up pass or a lost window)" % ([names[i] for i in kf], want)]` | If not, the rule returns this one problem. The cause can be a kernel call that belongs to no planned window, such as a warm-up pass, or a lost window. |
| 195 | `    start, end = kf[0] - 1, kf[-1] + 1` | `start`: the position directly before the first kernel call. `end`: the position directly after the last event `kernel_first`. |
| 196 | `    while end < len(names) and names[end] == "clock":` | Moves `end` forward over the clock reads that follow. These are the clock reads of the last window. |
| 197 | `        end += 1` | One step of this move. |
| 198 | `    end -= 1` | Steps one position back. `end` is now the last clock read of the last window. It ends the timed sequence. |
| 199 | `    if start < 0 or names[start] != "clock" or end == kf[-1]:` | Tests that a clock read stands directly before the first kernel call, and that at least one clock read follows the first call of the last window. |
| 200 | `        return ["no clock read around the first or the last window"]` | If not, the rule returns this one problem. |
| 201 | `    count_tail = [["count_read", "cpu_clock"], ["cpu_clock"]] if reads else [[]]` | `count_tail`: the event lists that may stand between the end clock read of a window and the start clock read of a target window. With the count mode `read`: a counter read and a CPU clock read, or the CPU clock read alone when the counter group did not open. In every other trial: nothing. |
| 202 | `    ends = []  # index of the end clock of each window` | `ends`: the position of the end clock read of each window, as the comment says. It is empty at the start. |
| 203 | `    for j, i in enumerate(kf):` | Loops over the windows. `j` is the number of the window in the trial. `i` is the position of its first kernel call. |
| 204 | `        if names[i - 1] != "clock":` | Tests that the event directly before the first kernel call is a clock read. So nothing runs between the start time of a window and its first pass. |
| 205 | `            p.append("window %d does not start directly after a clock read" % j)` | Adds a problem that names the window. |
| 206 | `        nxt = kf[j + 1] - 1 if j + 1 < len(kf) else end + 1  # the start clock of the next window` | `nxt`: the position of the start clock read of the next window. For the last window it is the position after the end of the timed sequence. The comment says the same. |
| 207 | `        body = names[i + 1:nxt]` | `body`: the events from the first kernel call of this window, not included, to the start clock read of the next window, not included. |
| 208 | `        tail = []` | `tail`: the events of the boundary after this window. It is empty at the start. |
| 209 | `        while body and body[-1] != "clock":` | As long as `body` does not end with a clock read: |
| 210 | `            tail.insert(0, body.pop())` | Moves the last event of `body` to the front of `tail`. At the end `body` ends with the end clock read of the window, and `tail` holds what the runner did between that read and the next start clock read. |
| 211 | `        if not body or any(n != "clock" for n in body):` | Tests the inside of the window: `body` must hold at least one clock read, and nothing but clock reads. A page read, an output or a counter event inside a window is a problem. |
| 212 | `            p.append("inside window %d: %s" % (j, sorted(set(body) - {"clock"}) or "no clock read"))` | Adds a problem that names the window and the foreign events, or the text `no clock read`. |
| 213 | `        ends.append(i + len(body))` | Stores the position of the end clock read of this window. |
| 214 | `        if j + 1 < len(kf):` | For every window but the last: |
| 215 | `            allowed = count_tail if exp[j + 1][0] == "target" else [[]]` | `allowed`: the lists that may stand between this window and the next one. The counter events are allowed only when the next window is a target window. |
| 216 | `            if tail not in allowed:` | Tests that `tail` is one of the allowed lists. This is the check of the gap. A page read, an output or a counter read that is not allowed between two windows would be found here. A kernel call cannot stand in `tail`. A kernel call that the trace logs outside the plan fails the test of line 193. |
| 217 | `                p.append("between window %d and window %d: %s, allowed %s" % (j, j + 1, tail, allowed))` | Adds a problem with the two window numbers, the events found and the allowed lists. |
| 218 | `        clocks, pb = len(body), exp[j][3]` | `clocks`: the number of clock reads of the window. `pb`: its pass size in bytes. |
| 219 | `        # the window ends at the first clock read at or after its requested duration` | Comment: a window ends at the first clock read at or after its requested duration. |
| 220 | `        if clocks > 1 and events[i + clocks - 1][1] - events[i - 1][1] >= exp[j][4]:` | Tests this stop rule on the times of the trace. The clock read before the last one must lie before the requested end, counted from the start clock read. When it lies at or after the requested end, the window continued after the clock read at which it had to stop. |
| 221 | `            p.append("window %d: runs on after the clock read that passed its requested duration" % j)` | Adds a problem that names the window. |
| 222 | `        if j < len(wrows) and clocks != int(wrows[j][6]) // (pb * max(1, MIB8 // pb)):` | Tests the number of clock reads against the bytes of the `W` row: the bytes divided by the bytes between two clock reads. That is one pass for a pass size of 8 MiB or more. For a smaller pass size it is the largest whole number of passes that fits into 8 MiB. So the runner reads the clock once per group of passes, not more and not less. |
| 223 | `            p.append("window %d: %d clock reads for %s bytes" % (j, clocks, wrows[j][6]))` | Adds a problem with the number of clock reads and the bytes. |
| 224 | `    before = names[:start]` | `before`: the events before the start clock read of the first window. |
| 225 | `    if reads and exp[0][0] == "target":` | With the count mode `read`, when the first window is a target window: |
| 226 | `        if before[-2:] not in (["count_read", "cpu_clock"], ["cpu_clock", "cpu_clock"]):` | The last two events before the timed sequence must be the first counter reading: a counter read and a CPU clock read. When the group did not open they are two CPU clock reads. |
| 227 | `            p.append("no counter read before the first target window")` | Adds a problem: no counter read before the first target window. |
| 228 | `        before = before[:-2] if before[-2:] == ["count_read", "cpu_clock"] else before[:-1]` | Removes that counter reading from `before`. |
| 229 | `    if [n for n in before if n not in ("count_open", "count_close")] != ["output", "page_read", "rusage", "cpu_clock"]:` | Tests the rest of `before`, without the events of a counter open or close. It must be exactly: an output (the `S` row that starts the trial), a page read, a read of the context-switch counts (`rusage`) and a CPU clock read, in this order. |
| 230 | `        p.append("before the timed sequence: %s" % before)` | Adds a problem with the events found. |
| 231 | `    after = names[end + 1:]` | `after`: the events after the end of the timed sequence. |
| 232 | `    if reads:` | With the count mode `read`: |
| 233 | `        if after[:2] not in (["count_read", "cpu_clock"],) and after[:1] != ["cpu_clock"]:` | The first events after the timed sequence must be the last counter reading: a counter read with a CPU clock read, or the CPU clock read alone. |
| 234 | `            p.append("no counter read after the last target window")` | Adds a problem: no counter read after the last target window. |
| 235 | `        after = after[2:] if after[:1] == ["count_read"] else after[1:]` | Removes that reading from `after`. |
| 236 | `    if after != ["cpu_clock", "rusage", "page_read", "output"]:` | Tests the rest: exactly a CPU clock read, a read of the context-switch counts, a page read and an output, in this order. So the page state is read and the rows are printed only after the last window. |
| 237 | `        p.append("after the timed sequence: %s" % after)` | Adds a problem with the events found. |
| 238 | `    if not reads and "count_read" in names:` | In a trial without the count mode `read` the trace must hold no counter read at all. |
| 239 | `        p.append("a counter read in a trial with count %s" % plan_fields[9])` | Adds a problem that names the count mode. |
| 240 | `    # the W rows are the clock reads of the trace, and the gap is the time between two of them` | Comment: the times of the `W` rows are clock reads of the trace, and the gap is the time between two of them. The next lines test this. |
| 241 | `    if len(wrows) == len(kf) and not p:` | Only when the trial has as many `W` rows as the trace has windows, and no problem was found so far: |
| 242 | `        for j, w in enumerate(wrows):` | Loops over the `W` rows. |
| 243 | `            if int(w[7]) != events[kf[j] - 1][1] or int(w[8]) != events[ends[j]][1]:` | The start time of the `W` row must be the time of the clock read before the first kernel call of the window. Its end time must be the time of the end clock read. So the printed times are the times that the timed loop read, and no other clock read. |
| 244 | `                p.append("window %d: the W row does not hold the clock reads of the trace" % j)` | Adds a problem that names the window. |
| 245 | `        g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. |
| 246 | `        if g and erow[6] != str(events[kf[g] - 1][1] - events[ends[g - 1]][1]):` | When such a window exists: `gap_ns` of the `E` row must be the start clock read of target window 0 minus the end clock read of the window before it. |
| 247 | `            p.append("gap_ns %s is not the time between the two clock reads of the trace" % erow[6])` | Adds a problem with the printed value. |
| 248 | `    return p` | Returns the list of problems. |

### Rules on the C source: `fn_span`, `hot_source_problems`, `seq_source_problems` (lines 251 to 314)

| Line | Source | Explanation |
|---:|---|---|
| 251 | `# The timed sequence, read from the source and from the machine code. The` | Comment: the next two rules read the timed sequence from the C source and from the machine code. |
| 252 | `# trace holds only what the wrappers log themselves. These two rules do not` | Comment: the trace holds only the events that the wrapper functions of the runner log themselves. A wrapper function here is a small function around the clock read or around the kernel call. |
| 253 | `# depend on that log.` | Comment: the two rules do not depend on that log. So they also find a call that the trace would not show. |
| 254 | `SEQ_SOURCE = {"timed_sequence": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall": 1},` | `SEQ_SOURCE`: for each C function of the timed path, the names that may stand directly before a `(` in its body, each with its count. This line: `timed_sequence`, the function that runs the windows of one trial. It may hold 2 `for`, 3 `if`, 2 `while`, 2 calls of `tcount` (the counter read), 2 calls of `tclock` (the clock read) and 1 call of `tcall` (the kernel call). |
| 255 | `              "timed_sequence_hot": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall_hot": 1},` | The entry of `timed_sequence_hot`, the function that runs the windows with the option `--hot-copy`: the same counts, with `tcall_hot` as its kernel call. |
| 256 | `              "tclock": {"now_ns": 1, "if": 1, "tev_add": 1},` | The entry of `tclock`, the clock read: 1 call of `now_ns` (it reads the clock of Linux), 1 `if` and 1 call of `tev_add` (it adds an event to the trace). |
| 257 | `              "tcall": {"if": 1, "tev_add": 1, "call": 1},` | The entry of `tcall`, the kernel call: 1 `if`, 1 call of `tev_add` and 1 call of `call`. `call` is the function of the runner that starts a kernel. |
| 258 | `              "tcall_hot": {"if": 1, "tev_add": 1, "call": 1}}` | The entry of `tcall_hot`: the same counts as `tcall`. The last brace ends the dictionary. |
| 259 | `SEQ_FUNCTIONS = ("timed_sequence", "timed_sequence_hot")` | `SEQ_FUNCTIONS`: the names of the two functions that run a timed sequence. The rules for the machine code are applied to both. |
| 260 | `FN_HEAD = r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n"` | `FN_HEAD`: a pattern for the first two lines of the definition of a C function. `%s` takes the function name. The first line may start with `__attribute__((noinline))`. Then come `static`, an optional `inline`, the return type, the name and the argument list in round brackets. The second line must hold only `{`. |
| 263 | `def fn_span(src, fn):` | Starts the function `fn_span`. It finds the body of the C function `fn` in the source text `src`. |
| 264 | `    """(start, end) of the body of the C function fn, or None"""` | Description text: the result is the pair of the start and the end position of the body, or `None`. |
| 265 | `    m = re.search(FN_HEAD % fn + r"(.*?)^\}\n", src, re.M \| re.S)` | Searches for the head of the function (`FN_HEAD`) and takes the shortest text after it that ends before a line holding only `}`. Group 1 is that text, the body. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. |
| 266 | `    return (m.start(1), m.end(1)) if m else None` | Returns the start and the end position of group 1, or `None` when the function was not found. |
| 269 | `def replace_in(src, fn, good, bad):` | Starts the function `replace_in`. It makes a changed copy of a source text. The tests use it to put one defect into the source of the runner. |
| 270 | `    """src with 'good' replaced by 'bad' inside function fn (the whole text if fn is None).` | Description text: the result is `src` with `good` replaced by `bad` inside the function `fn`, or in the whole text when `fn` is `None`. |
| 271 | `    None unless 'good' stands exactly once there."""` | Description text: the result is `None` unless `good` stands exactly once in that range. |
| 272 | `    span = (0, len(src)) if fn is None else fn_span(src, fn)` | `span`: the range to change. It is the whole text, or the body of `fn`. |
| 273 | `    if src is None or span is None or src[span[0]:span[1]].count(good) != 1:` | Tests that the range was found and that `good` stands exactly once in it. So a defect is never put in at two places, and a text that is no longer in the source is noticed. The test `src is None` has no effect at this place: line 272 already used `src`. |
| 274 | `        return None` | Returns `None` in that case. |
| 275 | `    return src[:span[0]] + src[span[0]:span[1]].replace(good, bad) + src[span[1]:]` | Returns the text before the range, then the range with `good` replaced by `bad`, then the text after the range. |
| 278 | `def hot_source_problems(src):` | Starts the rule `hot_source_problems`. It reads the source text of `timed_sequence_hot`, the function that runs the windows with the option `--hot-copy`. |
| 279 | `    """timed_sequence_hot() of bwx11.c: between the start clock read of a window and the store of its results,` | Description text: the rule is about `timed_sequence_hot()` of `bwx11.c`. Between the start clock read of a window and the store of its results ... |
| 280 | `    the text names no field of the window record (x->), no field of the trial record (r->) and no win[]."""` | Description text: ... the text must name no field of the window record (`x->`), no field of the trial record (`r->`) and no `win[]`. The window record is the place where the runner keeps the settings and the results of one window. |
| 281 | `    span = fn_span(src, "timed_sequence_hot")` | `span`: the body of `timed_sequence_hot` in the source text. |
| 282 | `    if span is None:` | Tests whether the function was not found. |
| 283 | `        return ["no function timed_sequence_hot"]` | Returns this one problem. |
| 284 | `    body = src[span[0]:span[1]]` | `body`: the text of the body. |
| 285 | `    a, b = body.find("        t0 = tclock(w);\n"), body.find("        x->bytes = bytes;\n")` | `a`: the position of the line with the start clock read of a window, `t0 = tclock(w);`. `b`: the position of the line with the first store of a result, `x->bytes = bytes;`. `find` gives -1 when the text is not there. |
| 286 | `    if a < 0 or b < a:` | Tests whether one of the two lines is missing, or the store stands before the clock read. |
| 287 | `        return ["the start clock read or the store of the results is not found"]` | Returns this one problem. |
| 288 | `    loop = re.sub(r"/\*.*?\*/", "", body[a:b], flags=re.S)` | `loop`: the text between the two positions, without C comments. This is the window loop: every pass and every clock read of one window. |
| 289 | `    p = ["the window loop of timed_sequence_hot names %s" % w for w in ("x->", "r->", "win") if w in loop]` | `p`: one problem for each of the texts `x->`, `r->` and `win` that `loop` holds. With `--hot-copy` the window loop must work on local copies. It must not read or write the window record between the first and the last pass. The rule proves this for the source text. |
| 290 | `    need = ("k = x->k", "phase = x->phase", "widx = x->widx", "bin_cap = x->bin_cap", "size = x->size", "passes = x->passes",` | `need`: the copies that must stand before the window loop: the kernel number, the phase, the window number, the room for bins, the pass size, the number of passes between two clock reads ... |
| 291 | `            "dur_ns = x->dur_ns", "bin = x->bin")` | Continues line 290: ... the requested duration in ns and the address of the bins. |
| 292 | `    return p + ["no copy '%s' before the window loop" % n for n in need if n not in body[:a]]` | Returns the problems of line 289, plus one problem for each copy that the text before the start clock read does not hold. |
| 293 | `SEQ_ALLOWED = {"clock_gettime", "(indirect)", "tcount", "__stack_chk_fail"}` | `SEQ_ALLOWED`: the only places outside itself to which the machine code of a timed function may branch. `clock_gettime` reads the clock. `(indirect)` means a call through a pointer, which is the kernel call. `tcount` is the counter read of the runner. `__stack_chk_fail` is the function that the compiler calls when the guard value on the stack was overwritten. |
| 296 | `def seq_source_problems(src):` | Starts the rule `seq_source_problems`. It counts the names before a `(` in the source text of the functions of the timed path. |
| 297 | `    """The words before a '(' in timed_sequence(), tclock() and tcall() of bwx11.c:` | Description text: the rule reads the words before a `(` in `timed_sequence()`, `tclock()` and `tcall()` of `bwx11.c`. |
| 298 | `    one clock read at each end of a window, one kernel call per pass, the` | Description text: allowed are one clock read at each end of a window, one kernel call per pass, ... |
| 299 | `    counter read at the two places of count 'read', and no other call."""` | Description text: ... the counter read at the two places of the count mode `read`, and no other call. |
| 300 | `    p = []` | `p`: the list of problems. |
| 301 | `    for fn, want in SEQ_SOURCE.items():` | Loops over the entries of `SEQ_SOURCE`: the function name `fn` and its expected counts `want`. |
| 302 | `        m = re.search(r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n(.*?)^\}\n" % fn, src,` | Searches for the function `fn` in the source. The pattern matches the head of its definition: an optional `__attribute__((noinline))`, then `static`, an optional `inline`, the return type, the name, the arguments, and a line with `{`. Group 1 is the body, up to the first line that holds only `}`. |
| 303 | `                      re.M \| re.S)` | Continues the call of line 302: the flags. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. |
| 304 | `        if not m:` | Tests whether the function was not found. |
| 305 | `            p.append("no function %s" % fn)` | Adds a problem that names the function. |
| 306 | `            continue` | Continues with the next function. |
| 307 | `        got = {}` | `got`: the counts found, empty at the start. |
| 308 | `        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)):` | Removes the C comments from the body. Then finds every name that stands before a `(`, with optional spaces between them. Such a name is a function call or a keyword such as `if`, `for` and `while`. |
| 309 | `            got[name] = got.get(name, 0) + 1` | Adds 1 to the count of that name. |
| 310 | `        if got != want:` | Tests that the counts found equal the expected counts exactly. An added call in the timed path, for example a second clock read, a page read or a warm-up kernel call, changes a count and is found. |
| 311 | `            p.append("%s holds %s, expected %s" % (fn, sorted(got.items()), sorted(want.items())))` | Adds a problem with the counts found and the expected counts. |
| 312 | `    return p` | Returns the list of problems. |

### Machine-code rule: `seq_targets` and `seq_code_problems` (lines 315 to 340)

| Line | Source | Explanation |
|---:|---|---|
| 315 | `def seq_targets(binary, fn="timed_sequence"):` | Starts the function `seq_targets`. It reads from the machine code of `binary` where the function `fn` branches to. |
| 316 | `    """{branch target outside function fn: count} from the machine code (x86-64 or AArch64 objdump text)"""` | Description text: the result is a dictionary from each branch target outside `fn` to the number of branches to it. The function reads the text that `objdump` prints for x86-64 or for AArch64, the 64-bit Arm instruction set. |
| 317 | `    out = subprocess.run(["objdump", "-d", "--no-show-raw-insn", "--disassemble=" + fn, binary],` | Runs the tool `objdump` on the binary. `-d` prints the machine code as instructions. `--no-show-raw-insn` leaves out the bytes of each instruction. `--disassemble=` limits the output to the function `fn`. |
| 318 | `                         stdout=subprocess.PIPE, universal_newlines=True).stdout` | Continues the call that runs `objdump`: its output is collected as text. |
| 319 | `    t = {}` | `t`: the dictionary of the targets, empty at the start. |
| 320 | `    for line in out.splitlines():` | Loops over the lines of the `objdump` output. |
| 321 | `        f = line.split()` | Splits the line at spaces and tabs into fields. |
| 322 | `        if len(f) < 3 or not re.fullmatch(r"[0-9a-f]+:", f[0]):` | Takes only an instruction line: at least 3 fields, and a first field that is a hex address with a colon. |
| 323 | `            continue` | Skips every other line. |
| 324 | `        if re.search(r"\s(call\|jmp)q?\s+\*", line) or f[1] in ("blr", "br"):` | Tests for a call or a jump through a pointer. On x86-64 the operand of such an instruction starts with `*`. On AArch64 the instructions are `blr` and `br`. |
| 325 | `            name = "(indirect)"` | Such a branch gets the name `(indirect)`. The kernel call is of this kind: the runner calls a kernel through a function pointer. |
| 326 | `        elif re.fullmatch(r"callq?\|jmpq?\|j[a-z]+\|bl\|b\|b\.[a-z]+\|cbn?z\|tbn?z", f[1]) and re.fullmatch(r"<.*>", f[-1]):` | If not: tests for a direct call, jump or branch whose last field is a symbol name in angle brackets. The pattern lists the instruction names of both machines: `call`, `jmp` and the conditional jumps of x86-64, and `bl`, `b`, `b.` with a condition, `cbz`, `cbnz`, `tbz` and `tbnz` of AArch64. |
| 327 | `            name = re.sub(r"\+0x[0-9a-f]+$\|@plt", "", f[-1][1:-1])` | `name`: the symbol name without the angle brackets, without an offset such as `+0x1c` at its end and without the mark `@plt`. That mark shows a call of a library function through the linker table. |
| 328 | `            if name == fn:` | Tests whether the target lies inside the function `fn` itself. |
| 329 | `                continue` | Skips such a branch: it does not leave the function. |
| 330 | `        else:` | Every other instruction line holds no branch with a named target. |
| 331 | `            continue` | Skips such a line. |
| 332 | `        t[name] = t.get(name, 0) + 1` | Adds 1 to the count of the target. |
| 333 | `    return t` | Returns the dictionary. |
| 336 | `def seq_code_problems(targets, fn="timed_sequence"):` | Starts the rule `seq_code_problems`. It judges the branch targets that `seq_targets` found for the function `fn`. |
| 337 | `    p = ["%s reaches %s" % (fn, n) for n in sorted(set(targets) - SEQ_ALLOWED)]` | `p`: one problem for each target that is not in `SEQ_ALLOWED`. A call of an output function or of a page read inside a timed function is found here, also when the trace does not log it. A helper that the compiler did not put inline shows here too, under its own name. |
| 338 | `    return p + ["%s has no call of %s" % (fn, n) for n in ("clock_gettime", "(indirect)") if n not in targets]` | Returns these problems, plus one problem for each of `clock_gettime` and `(indirect)` that is missing. Without the first the function reads no clock. Without the second it calls no kernel. |

### Rule `placement_problems`: the order of pin and memory mapping (lines 341 to 367)

| Line | Source | Explanation |
|---:|---|---|
| 341 | `def placement_problems(lines, cpu, ctl):` | Starts the rule `placement_problems`. It reads the log lines of the preloaded library (line 368) and checks in which order the two threads pin themselves and map memory. `cpu` is the CPU of the worker thread. `ctl` is the CPU of the controlling thread. |
| 342 | `    """Lines 'shim <call> pid=P tid=T <a> <b>' of the preloaded library, in time` | Description text: each log line has the form `shim <call> pid=P tid=T <a> <b>`. The lines stand in time ... |
| 343 | `    order. setaffinity: a = CPUs in the set, b = the first one. mmap: a = bytes.` | Description text: ... order. For `setaffinity`, `a` is the number of CPUs in the set and `b` is the first of them. For `mmap`, `a` is the number of bytes. |
| 344 | `    The controlling thread pins itself to ctl before the worker exists. The` | Description text: the controlling thread must pin itself to `ctl` before the worker thread exists. |
| 345 | `    worker pins itself to cpu before it maps the buffer."""` | Description text: the worker thread must pin itself to `cpu` before it maps the buffer. |
| 346 | `    ev = []` | `ev`: the list of the events, empty at the start. |
| 347 | `    for line in lines:` | Loops over the log lines. |
| 348 | `        f = line.split()` | Splits the line at the spaces into fields. |
| 349 | `        ev.append((f[1], f[3] == "tid=" + f[2][4:], f[3], int(f[4]), int(f[5])))` | Adds one event with five values: the call name, whether the caller is the main thread, the thread id text, and the two numbers. The caller is the main thread when its thread id equals the process id. In the trial mode the main thread is the controlling thread. |
| 350 | `    first_worker = next((i for i, e in enumerate(ev) if not e[1]), None)` | `first_worker`: the position of the first event of a thread that is not the main thread, or `None`. |
| 351 | `    if first_worker is None:` | Tests whether no such event exists. |
| 352 | `        return ["no call of the worker thread"]` | Returns this one problem. |
| 353 | `    p = []` | `p`: the list of problems. |
| 354 | `    if len({e[2] for e in ev}) != 2:` | Tests that exactly 2 threads made calls: the controlling thread and one worker. |
| 355 | `        p.append("%d threads, 2 expected" % len({e[2] for e in ev}))` | Adds a problem with the number of threads. |
| 356 | `    if ("setaffinity", True, 1, ctl) not in [(e[0], e[1], e[3], e[4]) for e in ev[:first_worker]]:` | Tests the controlling thread. Before the first event of the worker it must have made a `setaffinity` call with exactly 1 CPU in the set, the CPU `ctl`. So the controlling thread is pinned to its own CPU before the worker starts, and it cannot run on the CPU of the worker. |
| 357 | `        p.append("the controlling thread did not pin itself to CPU %d before the worker started" % ctl)` | Adds a problem that names the CPU `ctl`. |
| 358 | `    w = [e for e in ev if not e[1]]` | `w`: the events of the worker thread. |
| 359 | `    if (w[0][0], w[0][3], w[0][4]) != ("setaffinity", 1, cpu):` | Tests that the first logged call of the worker is its pin: `setaffinity` with 1 CPU, the CPU `cpu`. |
| 360 | `        p.append("the first call of the worker is %s %d %d, not its pin to CPU %d" % (w[0][0], w[0][3], w[0][4], cpu))` | Adds a problem with the call found. |
| 361 | `    if not any(e[0] == "mmap" and e[3] >= MIB8 for e in w[1:]):` | Tests that a later call of the worker is an `mmap` of at least 8 MiB. That is the buffer. So the worker is pinned before it maps the buffer. The first touch of the buffer then happens on the CPU that later reads it. |
| 362 | `        p.append("the worker did not map the buffer after its pin")` | Adds a problem: the worker did not map the buffer after its pin. |
| 363 | `    if any(e[0] == "mmap" and e[1] and e[3] >= MIB8 for e in ev):` | Tests that the main thread made no `mmap` of 8 MiB or more. The controlling thread must not own a buffer. |
| 364 | `        p.append("the controlling thread mapped a buffer")` | Adds a problem. |
| 365 | `    return p` | Returns the list of problems. |

### `SHIM`: the C source of the library that logs the calls (lines 368 to 407)

| Line | Source | Explanation |
|---:|---|---|
| 368 | `SHIM = r"""` | `SHIM`: the C source text of a small library, as a raw text that ends in line 406. A test builds it and loads it into the runner with the variable `LD_PRELOAD`. Its functions then replace the C library functions of the same name. Each one logs the call and passes it on to Linux. |
| 369 | `#define _GNU_SOURCE` | C text: `_GNU_SOURCE` switches on the Linux extensions of the header files, such as the macros for CPU sets. |
| 370 | `#include <errno.h>` | C text: includes `errno.h`, for the error number `errno` and the value `EINVAL`. |
| 371 | `#include <sched.h>` | C text: includes `sched.h`, for the type and the macros of a CPU set. |
| 372 | `#include <stdio.h>` | C text: includes `stdio.h`, for `snprintf`. |
| 373 | `#include <stdlib.h>` | C text: includes `stdlib.h`, for `getenv`. |
| 374 | `#include <sys/mman.h>` | C text: includes `sys/mman.h`, for the declarations of `mmap` and `madvise`. |
| 375 | `#include <sys/syscall.h>` | C text: includes `sys/syscall.h`, for the numbers of the system calls. |
| 376 | `#include <unistd.h>` | C text: includes `unistd.h`, for `write`, `getpid` and `syscall`. |
| 377 | `static void note(const char *what, long a, long b)` | C text: starts the function `note`. It writes one log line for the call named `what` with the two numbers `a` and `b`. |
| 378 | `{` | C text: opens the body of `note`. |
| 379 | `    char buf[128];` | C text: `buf`: room for one log line of up to 127 characters. |
| 380 | `    int n = snprintf(buf, sizeof buf, "shim %s pid=%d tid=%ld %ld %ld\n", what, (int)getpid(), syscall(SYS_gettid), a, b);` | C text: builds the line `shim <call> pid=<process id> tid=<thread id> <a> <b>`. `syscall(SYS_gettid)` asks Linux for the id of the calling thread. `n` is the length of the line. |
| 381 | `    if (write(2, buf, (size_t)n) < 0)` | C text: writes the line to the error output (file number 2) with one `write` call. |
| 382 | `        return;` | C text: returns when the `write` failed. The function ends directly after this line in both cases. |
| 383 | `}` | C text: ends the function `note`. |
| 384 | `int sched_setaffinity(pid_t pid, size_t len, const cpu_set_t *set)` | C text: starts the replacement of `sched_setaffinity`, the call that sets the CPUs on which a thread may run. The runner pins its threads with it. |
| 385 | `{` | C text: opens the body. |
| 386 | `    long first = -1;` | C text: `first`: the lowest CPU of the set. It is -1 as long as none is found. |
| 387 | `    for (long c = 0; c < 8 * (long)len && first < 0; c++)` | C text: loops over the CPU numbers that a set of `len` bytes can hold (8 per byte), until a CPU is found. |
| 388 | `        if (CPU_ISSET_S(c, len, set))` | C text: tests whether the CPU `c` is in the set. |
| 389 | `            first = c;` | C text: keeps it as `first`. |
| 390 | `    note("setaffinity", CPU_COUNT_S(len, set), first);` | C text: logs `setaffinity` with the number of CPUs in the set and the first CPU. |
| 391 | `    return (int)syscall(SYS_sched_setaffinity, pid, len, set);` | C text: passes the call on to Linux with the system call of the same name and returns its result. So the pin still happens. |
| 392 | `}` | C text: ends the replacement of `sched_setaffinity`. |
| 393 | `void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off)` | C text: starts the replacement of `mmap`, the call that asks Linux for a new range of memory. |
| 394 | `{` | C text: opens the body. |
| 395 | `    note("mmap", (long)len, 0);` | C text: logs `mmap` with the number of bytes. The second number is 0. |
| 396 | `    return (void *)syscall(SYS_mmap, addr, len, prot, flags, fd, off);` | C text: passes the call on to Linux and returns the address that Linux gave. |
| 397 | `}` | C text: ends the replacement of `mmap`. |
| 398 | `int madvise(void *addr, size_t len, int advice)` | C text: starts the replacement of `madvise`. The runner asks Linux for huge pages with this call. |
| 399 | `{` | C text: opens the body. |
| 400 | `    if (getenv("SHIM_MADVISE_FAIL")) {` | C text: tests whether the environment variable `SHIM_MADVISE_FAIL` is set. |
| 401 | `        errno = EINVAL;` | C text: sets the error number to `EINVAL`, the value for an invalid argument. |
| 402 | `        return -1;` | C text: returns -1. The runner sees a failed request. The test of line 798 uses this to check how the runner reports the failure. |
| 403 | `    }` | C text: ends the `if`. |
| 404 | `    return (int)syscall(SYS_madvise, addr, len, advice);` | C text: if the variable is not set, passes the call on to Linux and returns its result. |
| 405 | `}` | C text: ends the replacement of `madvise`. |
| 406 | `"""` | Ends the text `SHIM`. |

### `MUTANTS`: one defect each in a copy of the runner source (lines 408 to 461)

| Line | Source | Explanation |
|---:|---|---|
| 408 | `# One defect each in a copy of bwx11.c: [(function or None for the whole text, text of bwx11.c, changed text)].` | Comment: each entry of the table below is one defect in a copy of `bwx11.c`. A defect is a list of changes. Each change holds a function name (or `None` for the whole text), the text of `bwx11.c` to find and the changed text. |
| 409 | `WARM = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) call(&kernels[x->k], "` | `WARM`: one change, as a pair of the text to find and the changed text. The text to find is the line with the start clock read of a window, `t0 = tclock(w);`, and the first word of the line after it. The changed text starts here: before that clock read it adds one kernel call when the window is target window 0. |
| 410 | `        "&w->t, 0, x->size, 0, sink);\n        t0 = tclock(w);\n        next_bin")` | Continues the changed text: the arguments of the added kernel call, then the original text. The added call is a warm-up pass over the range of the window. It calls `call` directly and not `tcall`, so the trace does not log it. |
| 411 | `PAGE = ("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) { long long vmx[4]; "` | `PAGE`: a second change at the same place. Before the start clock read of target window 0 it adds a block with an array `vmx` ... |
| 412 | `        "read_vmstat(vmx); fflush(stdout); }\n        t0 = tclock(w);\n        next_bin")` | Continues the changed text: the block reads four counters of the file `/proc/vmstat` (`read_vmstat`) and flushes the output (`fflush(stdout)`). The design forbids a page read and an output between two windows. |
| 413 | `CLOCK = ("            t1 = tclock(w);\n", "            t1 = tclock(w);\n            if (x->bin) (void)now_ns();\n")` | `CLOCK`: a third change. After the clock read that follows a group of passes, `t1 = tclock(w);`, it adds a second clock read with `now_ns()` when the window has bins. That read does not go through `tclock`, so the trace does not log it. |
| 414 | `MUTANTS = {` | `MUTANTS`: the table of the defects. The key is the name of the defect. The names of the checks print it. The value is the list of the changes of that defect. |
| 415 | `    "a warm-up pass before the first target window": [("timed_sequence",) + WARM],` | Defect: a warm-up pass before the first target window. It is the change `WARM` in the function `timed_sequence`. |
| 416 | `    "a page read and an output flush before the first target window": [("timed_sequence",) + PAGE],` | Defect: a page read and an output flush before the first target window. It is the change `PAGE` in `timed_sequence`. |
| 417 | `    "an added clock read in a window with bins": [("timed_sequence",) + CLOCK],` | Defect: an added clock read in a window with bins. It is the change `CLOCK` in `timed_sequence`. |
| 418 | `    "the two context-switch counts exchanged in the E row":` | Defect: the `E` row prints the two context-switch counts in exchanged fields. |
| 419 | `        [(None, "r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]", "r->nivcsw[1] - r->nivcsw[0], r->nvcsw[1] - r->nvcsw[0]")],` | The change, in the whole text: the two arguments of the `printf` call are exchanged. `nvcsw` counts the voluntary context switches, in which the thread gave up the CPU. `nivcsw` counts the involuntary ones, in which Linux took the CPU away. |
| 420 | `    "wall time printed as cpu_ns":` | Defect: the field `cpu_ns` of the `E` row holds the wall time. |
| 421 | `        [(None, "(unsigned long long)(r->cpu[1] - r->cpu[0]));", "(unsigned long long)(r->win[r->nw - 1].t_end - r->win[0].t_start));")],` | The change: the difference of the two CPU clock reads is replaced by the end of the last window minus the start of the first window. |
| 422 | `    "the pre snapshot printed in the post P row":` | Defect: the `P` row `post` prints the page state that was read before the timed sequence. |
| 423 | `        [(None, 'print_p8(i, "post", &r->pg[1], r->vm[1]);', 'print_p8(i, "post", &r->pg[0], r->vm[0]);')],` | The change: the call that prints the row `post` gets the first snapshot (`pg[0]`, `vm[0]`) in place of the second one. |
| 424 | `    "C rows that hold the readings, not their differences":` | Defect: a `C` row holds the counter readings at the end of its window, and not their change over the window. |
| 425 | `        [(None, "(unsigned long long)(c1->enabled - c0->enabled)", "(unsigned long long)(c1->enabled)"),` | Change 1 of 3: the enabled time of the counter group is printed as the second reading alone, without the subtraction. |
| 426 | `         (None, "(unsigned long long)(c1->running - c0->running));\n        else", "(unsigned long long)(c1->running));\n        else"),` | Change 2 of 3: the same for the running time. The text to find also holds the line break and the `else` that follow. |
| 427 | `         (None, "(unsigned long long)(c1->val[at] - c0->val[at]));", "(unsigned long long)(c1->val[at]));")],` | Change 3 of 3: the same for the count of each event. The last bracket ends the list of this defect. |
| 428 | `    "no X row count_multiplexed":` | Defect: the row `X,<trial>,count_multiplexed` is never printed. An `X` row reports a failure. This one reports a counter that ran for less time than it was enabled. |
| 429 | `        [(None, "        if (m >= 0)\n", "        if (0 && m >= 0)\n")],` | The change: the condition `m >= 0` gets `0 &&` in front, so it is never true. |
| 430 | `    "no X row sink":` | Defect: the row `X,<trial>,sink` is never printed. It reports that the old read kernel did not leave the sum of its range in the result variable. |
| 431 | `        [(None, "    if (r->sink_ok == 0)\n        printf(\"X", "    if (0)\n        printf(\"X")],` | The change: the condition `r->sink_ok == 0` becomes `0`. |
| 432 | `    "no X row coverage_na":` | Defect: the row `X,<trial>,coverage_na` is never printed. It reports that the huge-page state of the buffer could not be read. |
| 433 | `        [(None, "    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)\n", "    if (0)\n")],` | The change: the condition on the two snapshots becomes `0`. |
| 434 | `    # gcc itself turns malloc + memset into calloc, which writes no page of a fresh block` | Comment: `gcc` itself turns the pair `malloc` and `memset` into `calloc`. `calloc` writes no page of a fresh block. So without a store of its own the runner would touch the pages of its records first during a trial. |
| 435 | `    "record storage without the store to every page before the first trial":` | Defect: the storage of the records is not written before the first trial. |
| 436 | `        [(None, "        ((volatile char *)mem)[at] = 0;\n", "        ;\n"), (None, "    ((volatile char *)mem)[recsz.bytes - 1] = 0;\n", "")],` | Two changes: the store of one byte to every page becomes an empty statement, and the store to the last byte is removed. |
| 437 | `    # round 3: the same three defects of the timed sequence in the function of --hot-copy` | Comment: round 3 added the next entries. The first three are the three defects of the timed sequence, now in the function that runs with `--hot-copy`. |
| 438 | `    "a warm-up pass before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + WARM],` | Defect: the change `WARM` in `timed_sequence_hot`. |
| 439 | `    "a page read and an output flush before the first target window, in timed_sequence_hot": [("timed_sequence_hot",) + PAGE],` | Defect: the change `PAGE` in `timed_sequence_hot`. |
| 440 | `    "an added clock read in a window with bins, in timed_sequence_hot": [("timed_sequence_hot",) + CLOCK],` | Defect: the change `CLOCK` in `timed_sequence_hot`. |
| 441 | `    "timed_sequence_hot reads the pass count from the window record after every pass":` | Defect: `timed_sequence_hot` reads the pass count from the window record after every pass. |
| 442 | `        [("timed_sequence_hot", "c < passes;", "c < passes && c < x->passes;")],` | The change: the loop condition `c < passes;` also tests `c < x->passes`. So the loop reads a field of the window record after each pass. With `--hot-copy` it must not do that. |
| 443 | `    "--hot-copy that still runs timed_sequence":` | Defect: with `--hot-copy` the runner still runs `timed_sequence`. |
| 444 | `        [("run_trial", "    if (plan.hot_copy)\n", "    if (0)\n")],` | The change, in `run_trial`: the test of the option becomes `if (0)`. So `timed_sequence_hot` is never chosen. |
| 445 | `    "--rec-pad that does not move the window records":` | Defect: `--rec-pad` does not move the window records. |
| 446 | `        [("alloc_records", "    win = (struct win *)((char *)win + plan.rec_pad);\n", "")],` | The change, in `alloc_records`: the line that adds the pad to the address of the window records is removed. |
| 447 | `    # round 4` | Comment: the defects of round 4 follow. |
| 448 | `    "an evict step that maps and unmaps the range but stores nothing":` | Defect: the evict step maps and unmaps its memory range but stores nothing in it. |
| 449 | `        [("evict_step", "            m[i] = (uint64_t)i + (uint64_t)pass + 1;\n", "            ;\n")],` | The change, in `evict_step`: the store of one word per 64-byte line becomes an empty statement. Linux assigns a memory page only at the first write. So this copy maps the range and never fills it. |
| 450 | `    "an evict step that runs after trial 0":` | Defect: the evict step runs after trial 0, and not before the first trial. |
| 451 | `        [(None, "    if (evict_mb > 0 && evict_step() != 0) {\n", "    if (0) {\n"),` | Change 1 of 2, in the whole text: the call of the evict step before the first trial is replaced by `if (0)`. |
| 452 | `         (None, "        emit_trial(w, i);\n", "        emit_trial(w, i);\n        if (i == 0 && evict_mb > 0) evict_step();\n")],` | Change 2 of 2: directly after the rows of a trial are printed (`emit_trial`), the evict step runs when the trial is trial 0 and `evict_mb` is above 0. |
| 453 | `}` | Ends the table `MUTANTS`. |
| 454 | `SEQ_MUTANTS = list(MUTANTS)[:3]` | `SEQ_MUTANTS`: the names of the first 3 entries of the table. A Python dictionary keeps the order in which its entries were written. These are the three defects of `timed_sequence`. |
| 455 | `ROW_MUTANTS = list(MUTANTS)[3:10]` | `ROW_MUTANTS`: the names of the entries 4 to 10, the 7 defects of the output rows. |
| 456 | `TOUCH_MUTANT = list(MUTANTS)[10]` | `TOUCH_MUTANT`: the name of entry 11, the record storage without the first store. |
| 457 | `HOT_SEQ_MUTANTS = list(MUTANTS)[11:14]` | `HOT_SEQ_MUTANTS`: the names of the entries 12 to 14, the three defects of `timed_sequence_hot`. |
| 458 | `HOT_READ_MUTANT, HOT_OFF_MUTANT, PAD_MUTANT = list(MUTANTS)[14:17]` | The names of the entries 15, 16 and 17: the read of the pass count from the window record, the `--hot-copy` that still runs `timed_sequence`, and the `--rec-pad` that moves nothing. |
| 459 | `EVICT_NOSTORE_MUTANT, EVICT_LATE_MUTANT = list(MUTANTS)[17:19]` | The names of the entries 18 and 19: the two defects of the evict step. |

### `mutant_source` and `mutant_build`: a copy of the runner with one defect (lines 462 to 486)

| Line | Source | Explanation |
|---:|---|---|
| 462 | `def mutant_source(name):` | Starts the function `mutant_source`. It returns the source text of the runner with the defect `name`. |
| 463 | `    """bwx11.c with the defect 'name', or None if a text to change is not there exactly once"""` | Description text: the result is `bwx11.c` with the defect, or `None` when a text to change does not stand there exactly once. |
| 464 | `    with open(os.path.join(HERE, "bwx11.c")) as f:` | Opens `bwx11.c` in the folder of this file. |
| 465 | `        src = f.read()` | `src`: the whole source text. |
| 466 | `    for fn, good, bad in MUTANTS[name]:` | Loops over the changes of the defect. |
| 467 | `        src = replace_in(src, fn, good, bad)` | Applies one change with `replace_in` (line 269). |
| 468 | `        if src is None:` | Tests whether the change could not be applied. |
| 469 | `            return None` | Returns `None`. The checks that use the defect then fail. So a text of the table that the source no longer holds is noticed. |
| 470 | `    return src` | Returns the changed text. |
| 473 | `def mutant_build(name, tag):` | Starts the function `mutant_build`. It compiles the runner with the defect `name`. `tag` is a short word for the folder name. |
| 474 | `    """builds the mutant in its own folder; returns the path of the binary, or None"""` | Description text: the defect copy is built in its own folder. The result is the path of the binary, or `None`. |
| 475 | `    d = os.path.join(E.tmp, "mutant-" + tag)` | `d`: the folder `mutant-` plus `tag` in the temporary folder. |
| 476 | `    os.makedirs(d, exist_ok=True)` | Creates the folder. No error when it exists. |
| 477 | `    src = mutant_source(name)` | `src`: the source text with the defect. |
| 478 | `    if src is None:` | Tests whether the defect could not be put in. |
| 479 | `        return None` | Returns `None`. |
| 480 | `    with open(os.path.join(d, "bwx11.c"), "w") as f:` | Opens the file `bwx11.c` in that folder for writing. |
| 481 | `        f.write(src)` | Writes the changed source text. |
| 482 | `    shutil.copy(os.path.join(HERE, "bwx11_selftest.c"), d)` | Copies `bwx11_selftest.c` into the folder. `bwx11.c` includes that file, so the compiler needs it there. |
| 483 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx11"), os.path.join(d, "bwx11.c")])` | Compiles the copy with `gcc` and the flags `CFLAGS` into the binary `bwx11` of that folder. |
| 484 | `    return os.path.join(d, "bwx11") if r.returncode == 0 else None` | Returns the path of the binary when `gcc` ended with exit status 0, and `None` if not. |

### Running the runner: `write_plan`, `run`, `trial`, `fnv1a64`, `plan_lines`, `GOOD` (lines 487 to 533)

| Line | Source | Explanation |
|---:|---|---|
| 487 | `# ---- running bwx11 ----` | Comment: the helpers that start `bwx11` follow. |
| 489 | `class Env:` | Starts the class `Env`. It has no content of its own. It only carries values. |
| 490 | `    pass` | The empty body of the class. |
| 493 | `E = Env()` | `E`: the one object of that class. `main` stores in it the settings that all tests share, such as the temporary folder (`E.tmp`), the path of the binary (`E.bin`) and the worker CPU (`E.cpu`). |
| 496 | `def write_plan(name, lines, cpu=None, nbytes=MIB8, head1=HEAD1, head3=HEAD3, head2=None):` | Starts the function `write_plan`. It writes a plan file with the trial lines `lines` and returns its path. A plan file lists the trials that the runner must run. The other arguments replace single header values, for the tests of bad plans. |
| 497 | `    cpu = E.cpu if cpu is None else cpu` | `cpu`: the worker CPU of the tests, unless the caller gave another one. |
| 498 | `    if head2 is None:` | Tests whether the caller gave no second header line. |
| 499 | `        head2 = "# step=T session=1 cpu=%d bytes=%d proc=0 seed=1 test=1" % (cpu, nbytes)` | `head2`: the standard second header line. It holds pairs of the form `key=value`: the step name `T`, session 1, the worker CPU, the buffer size in bytes, process 0, seed 1 and `test=1`. The runner requires that `cpu` and `bytes` equal its options. |
| 500 | `    path = os.path.join(E.tmp, name + ".plan")` | `path`: the file `name` with the ending `.plan` in the temporary folder. |
| 501 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 502 | `        f.write("\n".join([head1, head2, head3] + lines) + "\n")` | Writes the three header lines and the trial lines, each ended by a line break. |
| 503 | `    return path` | Returns the path. |
| 506 | `def run(args, env_add=None, binary=None):` | Starts the function `run`. It starts a binary with the arguments `args` and waits for its end. `env_add` holds added environment variables. `binary` is the program to start, when it is not the runner under test. |
| 507 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment of the test without every variable whose name starts with `BWX_`. So a counter setting in the environment of the caller cannot change a test. |
| 508 | `    env.update(env_add or {})` | Adds the variables of `env_add`, if any. |
| 509 | `    r = subprocess.run([binary or E.bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,` | Starts the binary (`E.bin` unless `binary` is given) and collects its standard output and its error output apart. |
| 510 | `                       universal_newlines=True, timeout=120)` | Continues the call of line 509: the outputs are returned as text. `timeout=120`: when the program runs longer than 120 s, the call ends with an error. |
| 511 | `    return r.returncode, r.stdout, r.stderr` | Returns three values: the exit status, the standard output and the error output. |
| 514 | `def trial(plan, extra=None, cpu=None, nbytes="8M", env_add=None):` | Starts the function `trial`. It runs the runner in the trial mode on one plan file. |
| 515 | `    return run(["--trial", "--cpus", str(E.cpu if cpu is None else cpu), "--bytes", nbytes, "--plan", plan] + (extra or []),` | Returns the result of `run`, called with `--trial`, `--cpus` and one CPU (the worker CPU of the tests unless `cpu` is given), `--bytes` and the buffer size (`8M` means 8 MiB), `--plan` and the path, and the added arguments of `extra`. |
| 516 | `               env_add)` | Continues the call of line 515: the added environment variables. |
| 519 | `def fnv1a64(data):` | Starts the function `fnv1a64`. It computes the FNV-1a hash of 64 bits over a sequence of bytes. The runner prints the same hash of its plan file. |
| 520 | `    h = 14695981039346656037` | `h`: the start value of that hash. |
| 521 | `    for b in data:` | Loops over the bytes. |
| 522 | `        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF` | One step: `h` is combined with the byte by exclusive or, multiplied by the constant 1099511628211 and cut to the low 64 bits. |
| 523 | `    return "%016x" % h` | Returns the hash as 16 hex digits. |
| 526 | `def plan_lines(path):` | Starts the function `plan_lines`. It reads the trial lines of a plan file. |
| 527 | `    with open(path) as f:` | Opens the plan file. |
| 528 | `        return [line.split(" ") for line in f.read().splitlines()[3:]]` | Returns the lines after the three header lines, each one split at single spaces into its 11 fields. |
| 531 | `GOOD = "0 a 1 - oldread@8M:8 - oldread@8M 1 5 closed 0"` | `GOOD`: a valid trial line that many tests use. Its fields: trial 0, the condition label `a`, repeat 1, no previous activity, a prefix of the old read kernel on 8 MiB for 8 ms (4 windows of 2 ms), no predecessor, the target `oldread` on 8 MiB, 1 target window of 5 ms, the count mode `closed` (no counters) and no bins. |

### `test_bad_plans`, checks a: a plan with a defect is refused (lines 534 to 589)

| Line | Source | Explanation |
|---:|---|---|
| 534 | `def test_bad_plans():` | Starts the test `test_bad_plans`. The names of its checks start with `a:`. |
| 535 | `    """(a) every defect gives status 2, a message, and no row"""` | Description text: every defect must give exit status 2, a message and no row. |
| 536 | `    rc, out, _ = trial(write_plan("good", [GOOD]))` | Runs the control: a plan that holds only the line `GOOD`. `rc` is the exit status. `out` is the standard output. |
| 537 | `    check("a: the good control plan runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the good plan runs with status 0 and prints the `E` row of trial 0. Without this control the next checks could pass for a wrong reason, for example with a runner that refuses every plan. |
| 539 | `    def bad(name, line=None, **kw):` | Starts the inner function `bad`. It runs one plan with a defect and checks the result. `line` is a bad trial line. `kw` holds header values to replace. |
| 540 | `        plan = write_plan("bad", [GOOD] if line is None else [GOOD.replace("0 a", "0 first"), line], **kw)` | Writes the plan. With a bad trial line: the good line with the label `first`, then the bad line as trial 1. Without one: the good line alone, under the changed header. |
| 541 | `        rc, out, err = trial(plan)` | Runs the plan in the trial mode. |
| 542 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. The design asks that a malformed plan fails before any work starts. The empty output proves that the runner printed no row. So no half result of a bad plan can reach the analysis. |
| 544 | `    t = "1 b 1 - oldread@8M:8 - %s 1 5 closed 0"` | `t`: a pattern for trial 1 in which only the target field changes. |
| 545 | `    bad("unknown kernel", t % "newread@8M")` | Bad plan: a target kernel with a name that the runner does not know. |
| 546 | `    bad("write kernel as target", t % "write@8M")` | Bad plan: a write kernel as the target. The trial mode accepts read kernels only. |
| 547 | `    bad("copy kernel as target", t % "copy@8M")` | Bad plan: a copy kernel as the target. |
| 548 | `    bad("write kernel as prefix", "1 b 1 - oldwrite@8M:8 - read@8M 1 5 closed 0")` | Bad plan: a write kernel, `oldwrite`, as the prefix. |
| 549 | `    bad("copy kernel as predecessor", "1 b 1 - - asmcopy@8M:8 read@8M 1 5 closed 0")` | Bad plan: a copy kernel, `asmcopy`, as the predecessor. |
| 550 | `    bad("size above --bytes", t % "read@16M")` | Bad plan: a target size of 16 MiB. That is above the buffer size of 8 MiB that `--bytes` gives. |
| 551 | `    bad("size not a multiple of 256", t % "read@1000")` | Bad plan: a size of 1000 bytes, which is no multiple of 256. The read kernels handle 256 bytes per loop pass. |
| 552 | `    bad("size 0", t % "read@0")` | Bad plan: a size of 0. |
| 553 | `    bad("size with a fraction", t % "read@1.5M")` | Bad plan: a size with a fraction, `1.5M`. |
| 554 | `    bad("target with a duration", t % "read@8M:5")` | Bad plan: a target with a duration, `read@8M:5`. The duration of the target windows comes from the field `win_ms`. |
| 555 | `    bad("prefix without a duration", "1 b 1 - oldread@8M - read@8M 1 5 closed 0")` | Bad plan: a prefix without a duration. |
| 556 | `    bad("pfx ms not a multiple of 4", "1 b 1 - oldread@8M:42 - read@8M 1 5 closed 0")` | Bad plan: a prefix duration of 42 ms, which is no multiple of 4. The runner records the prefix as 4 windows of equal requested length. |
| 557 | `    bad("pred ms 0", "1 b 1 - - read@8M:0 read@8M 1 5 closed 0")` | Bad plan: a predecessor duration of 0 ms. |
| 558 | `    bad("bad count word", "1 b 1 - - - read@8M 1 5 maybe 0")` | Bad plan: the count word `maybe`. Allowed are `closed`, `open` and `read`. |
| 559 | `    bad("bins 2", "1 b 1 - - - read@8M 1 5 closed 2")` | Bad plan: the bins value 2. Allowed are 0 and 1. |
| 560 | `    bad("nwin 0", "1 b 1 - - - read@8M 0 5 closed 0")` | Bad plan: 0 target windows. |
| 561 | `    bad("nwin 4097", "1 b 1 - - - read@8M 4097 5 closed 0")` | Bad plan: 4097 target windows. The limit is 4096. |
| 562 | `    bad("win_ms 0", "1 b 1 - - - read@8M 1 0 closed 0")` | Bad plan: a window duration of 0 ms. |
| 563 | `    bad("rep 5", "1 b 5 - - - read@8M 1 5 closed 0")` | Bad plan: the repeat number 5. Allowed are 1 to 4. |
| 564 | `    bad("trial number out of order", "2 b 1 - - - read@8M 1 5 closed 0")` | Bad plan: trial number 2 directly after trial 0. The trial numbers must be 0, 1, 2 and so on. |
| 565 | `    bad("10 fields", "1 b 1 - - - read@8M 1 5 closed")` | Bad plan: a trial line with 10 fields. It needs 11. |
| 566 | `    bad("12 fields", "1 b 1 - - - read@8M 1 5 closed 0 0")` | Bad plan: a trial line with 12 fields. |
| 567 | `    bad("two spaces between fields", "1 b 1 -  - - read@8M 1 5 closed 0")` | Bad plan: two spaces between two fields. |
| 568 | `    bad("comma in cond", "1 b,c 1 - - - read@8M 1 5 closed 0")` | Bad plan: a comma in the condition label. The label goes into an output row with comma-separated fields. A comma in it would shift the fields. |
| 569 | `    bad("empty line in the plan", "")` | Bad plan: an empty line in the plan. |
| 570 | `    # Record storage above the bound (design: "Bound its size"). The plan below needs 23.6 GB of bins. The address` | Comment: the next case is record storage above its bound. The design says of the storage for the output records: "Bound its size". By the comment the plan below needs 23.6 GB of bins. |
| 571 | `    # space limit keeps a runner without the bound from writing that much memory on this machine.` | Comment: the test limits the address space of the process. So a runner without the bound cannot write that much memory on the machine of the test. |
| 572 | `    plan = write_plan("bad", [GOOD.replace("0 a", "0 first"), "1 b 1 - - - oldread@8M 4096 3600000 closed 1"])` | Writes the plan: the good line, then a trial 1 with 4096 target windows of 3600000 ms (1 hour) each, with bins. One bin per 10 ms of all these windows needs far more than the bound of 256 MiB. |
| 573 | `    r = subprocess.run([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=subprocess.PIPE,` | Starts the runner on this plan directly, without the helper `run`. The test needs this to set a limit for the new process. |
| 574 | `                       stderr=subprocess.PIPE, universal_newlines=True, timeout=120,` | Continues the call of line 573: the outputs are collected as text, and the run may last 120 s at most. |
| 575 | `                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30)))` | Continues the call: `preexec_fn` runs in the new process before the runner starts. It limits the address space of the process to 4 GiB (`RLIMIT_AS`, as soft and as hard limit). |
| 576 | `    check("a: status 2, no row and a plan message that names line 5: record storage above the bound of 256 MiB",` | Check: the runner refuses the plan with status 2 and no row. Its message must start with `bad plan` and name the fifth text line of the plan file, which is the bad trial line. |
| 577 | `          r.returncode == 2 and r.stdout == "" and r.stderr.startswith("bad plan") and "line 5:" in r.stderr,` | Continues the check: the condition on the exit status, the standard output and the two parts of the message. |
| 578 | `          "rc=%s out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:160]))` | Continues the check: the detail that a failure prints. |
| 579 | `    bad("wrong header line 1", head1="# bwx8-plan v2")` | Bad plan: a first header line with `v2` in place of `v1`. |
| 580 | `    bad("wrong header line 3", head3=HEAD3.replace("win_ms count", "count win_ms"))` | Bad plan: a third header line in which the column names `win_ms` and `count` are exchanged. |
| 581 | `    bad("plan bytes differ from --bytes", head2="# step=T cpu=%d bytes=%d" % (E.cpu, MIB8 // 2))` | Bad plan: the header gives 4 MiB as `bytes`, and the option `--bytes` gives 8 MiB. A plan that was made for another buffer size must not run. |
| 582 | `    bad("plan cpu differs from --cpus", head2="# step=T cpu=%d bytes=%d" % (E.cpu2, MIB8))` | Bad plan: the header names another CPU (`E.cpu2`) than the option `--cpus`. A plan that was made for another CPU must not run. |
| 583 | `    bad("plan without bytes=", head2="# step=T cpu=%d" % E.cpu)` | Bad plan: a header without the pair `bytes=`. |
| 584 | `    bad("header pair without =", head2="# step cpu=%d bytes=%d" % (E.cpu, MIB8))` | Bad plan: a header word without `=`, the word `step`. |
| 585 | `    with open(os.path.join(E.tmp, "empty.plan"), "w") as f:` | Opens the file `empty.plan` in the temporary folder for writing. |
| 586 | `        f.write("\n".join([HEAD1, "# cpu=%d bytes=%d" % (E.cpu, MIB8), HEAD3]) + "\n")` | Writes the three header lines and no trial line. |
| 587 | `    rc, out, err = trial(os.path.join(E.tmp, "empty.plan"))` | Runs this plan in the trial mode. |
| 588 | `    check("a: status 2 and no row: plan without a trial", rc == 2 and out == "" and err.strip() != "", rc)` | Check: a plan without a trial gives status 2, no row and a message. |

### `test_bad_plans`, checks a: bad options are refused (lines 590 to 622)

| Line | Source | Explanation |
|---:|---|---|
| 590 | `    good = write_plan("good", [GOOD])` | `good`: a plan file with the line `GOOD`, for the checks of the options. |
| 592 | `    def bad_opt(name, args, env_add=None):` | Starts the inner function `bad_opt`. It starts the runner with the arguments `args` and checks that the runner refuses them. |
| 593 | `        rc, out, err = run(args, env_add)` | Runs the runner. |
| 594 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. |
| 596 | `    base = ["--trial", "--bytes", "8M", "--plan", good]` | `base`: the arguments of a valid trial run without `--cpus`. |
| 597 | `    bad_opt("worker CPU equal to the control CPU", base + ["--cpus", str(E.cpu), "--ctl-cpu", str(E.cpu)])` | Bad options: the worker CPU is also the CPU of the controlling thread (`--ctl-cpu`). The two threads would share one CPU, and the controlling thread could take time from the worker. |
| 598 | `    bad_opt("worker CPU equal to the default control CPU 0", ["--trial", "--bytes", "8M", "--cpus", "0", "--plan",` | Bad options: the worker CPU is CPU 0. That is the CPU of the controlling thread when `--ctl-cpu` is not given. |
| 599 | `                                                               write_plan("cpu0", [GOOD], cpu=0)])` | Continues the call of line 598: the plan is written for CPU 0, so only the CPU clash can be the reason of the refusal. |
| 600 | `    bad_opt("CPU above 119", ["--trial", "--bytes", "8M", "--cpus", "120", "--plan", write_plan("cpu120", [GOOD], cpu=120)])` | Bad options: CPU 120 as the worker CPU. The runner accepts the CPUs 0 to 119 only. |
| 601 | `    bad_opt("control CPU above 119", base + ["--cpus", str(E.cpu), "--ctl-cpu", "120"])` | Bad options: CPU 120 as the CPU of the controlling thread. |
| 602 | `    bad_opt("two CPUs", base + ["--cpus", "%d,%d" % (E.cpu, E.cpu2)])` | Bad options: two CPUs in `--cpus`. The trial mode has exactly one worker. |
| 603 | `    bad_opt("no --cpus", base)` | Bad options: no `--cpus`. |
| 604 | `    bad_opt("no --bytes", ["--trial", "--cpus", str(E.cpu), "--plan", good])` | Bad options: no `--bytes`. |
| 605 | `    bad_opt("no --plan", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M"])` | Bad options: no `--plan`. |
| 606 | `    bad_opt("plan file that does not exist", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good + ".none"])` | Bad options: a plan file that does not exist. |
| 607 | `    bad_opt("unknown option", base + ["--cpus", str(E.cpu), "--warmup"])` | Bad options: the unknown option `--warmup`. |
| 608 | `    bad_opt("--seq together with --trial", base + ["--cpus", str(E.cpu), "--seq", "read"])` | Bad options: `--seq` together with `--trial`. `--seq` belongs to the interval mode, the other mode of the runner. |
| 609 | `    if E.absent is not None:` | Tests whether a CPU from 0 to 119 exists that the test process may not use (`E.absent`). |
| 610 | `        bad_opt("worker CPU outside the allowed set of the process",` | Bad options: that CPU as the worker CPU. The runner must refuse a CPU outside the allowed set of the process before it starts any work. |
| 611 | `                ["--trial", "--bytes", "8M", "--cpus", str(E.absent), "--plan", write_plan("absent", [GOOD], cpu=E.absent)])` | Continues the call of line 610: the arguments, with a plan written for that CPU. |
| 612 | `    else:` | If no such CPU exists: |
| 613 | `        check("a: worker CPU outside the allowed set (no such CPU from 0 to 119 on this machine: NOT RUN)", False)` | Records a failed check whose name holds `NOT RUN`. So a case that this machine cannot test counts as a failure of the test file, and the output shows it. |
| 614 | `    counted = write_plan("counted", [GOOD, "1 b 1 - - - read@8M 1 5 open 0"])` | `counted`: a plan with the good line and a trial 1 with the count mode `open`. |
| 615 | `    bad_opt("count open without counter settings", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted])` | Bad options: a plan with a counted trial and no counter settings. |
| 616 | `    bad_opt("count open with a PMU type and no event",` | Bad options: a counted trial with a PMU type and no event list. The PMU type is the number by which Linux names a group of counters. |
| 617 | `            ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted, "--pmu-type", "1"])` | Continues the call of line 616: the arguments, with `--pmu-type 1`. |
| 618 | `    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted],` | Runs the same plan with the counter settings in the environment. |
| 619 | `                     {"BWX_PMU_TYPE": "1", "BWX_EVENTS": "task_clock=1"})` | Continues the call of line 618: `BWX_PMU_TYPE=1` and `BWX_EVENTS=task_clock=1`. |
| 620 | `    check("a: the same plan runs with the counter settings in the environment", rc == 0 and "\nE,1," in out, rc)` | Check: the plan now runs with status 0 and prints the `E` row of trial 1. So the runner also takes the counter settings from the environment. The two refusals before are proven to come from the missing settings. |

### `ALL` and `test_rows`: the rows of a plan with all phases (lines 623 to 692)

| Line | Source | Explanation |
|---:|---|---|
| 623 | `ALL = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 4 20 closed 0",` | `ALL`: the four trial lines of a short plan that uses every phase. Trial 0, label `A`: previous activity `asmread` on 8 MiB for 24 ms, prefix `oldread` on 8 MiB for 40 ms, predecessor `read` on 1 MiB for 20 ms, target `oldread` on 8 MiB with 4 windows of 20 ms, counters closed, no bins. |
| 624 | `       "1 B 1 - read@1M:40 - read@1M 4 20 closed 0",` | Trial 1, label `B`: a prefix of `read` on 1 MiB for 40 ms, then the target `read` on 1 MiB with 4 windows of 20 ms. |
| 625 | `       "2 C 1 - - - asmread@32K 3 25 closed 1",` | Trial 2, label `C`: no phase before the target. The target is `asmread` on 32 KiB with 3 windows of 25 ms, with bins. |
| 626 | `       "3 A 2 - oldread@8M:40 oldread@1M:20 read@8M 2 20 closed 1"]` | Trial 3, label `A`, repeat 2: prefix `oldread` on 8 MiB for 40 ms, predecessor `oldread` on 1 MiB for 20 ms, target `read` on 8 MiB with 2 windows of 20 ms, with bins. |
| 629 | `def test_rows():` | Starts the test `test_rows`. |
| 630 | `    """(b) (d) (e) (h) and the M, K, S, P rows of a short plan with all phases"""` | Description text: the checks named b, d, e and h, and the `M`, `K`, `S` and `P` rows, on a short plan with all phases. |
| 631 | `    plan = write_plan("all", ALL)` | Writes the plan `ALL` to a file. |
| 632 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)])` | Runs it in the trial mode, with the CPU `E.ctl` for the controlling thread. |
| 633 | `    if not check("b: the plan with all phases runs with status 0", rc == 0, err):` | Check: the run ends with status 0. On a failure the error output is printed. |
| 634 | `        return` | Ends the test on a failure. Every later check needs the rows of this run. |
| 635 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the four plan lines. |
| 636 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary from key to value. An `M` row is one line of settings, `M,key,value`. |
| 637 | `    need = ["mode", "cpu", "ctl_cpu", "bytes", "thp", "madvise_ok", "check_bytes", "kernels", "plan_fnv1a64", "ntrials",` | `need`: the keys that the output must hold: the mode, the worker CPU, the control CPU, the buffer size, the huge-page policy, the result of the page policy request, the bytes between two clock reads, the kind of the kernels, the hash of the plan, the number of trials ... |
| 638 | `            "rec_windows", "rec_bins", "rec_bytes", "trace", "pmu_type", "events"]` | Continues line 637: ... the sizes of the record storage (windows, bins, bytes), the trace switch, the PMU type and the events. |
| 639 | `    check("b: every required M key is present", all(k in m for k in need), [k for k in need if k not in m])` | Check: every required key is present. The analysis needs these settings to know under which conditions a rate was measured. |
| 640 | `    with open(plan, "rb") as f:` | Opens the plan file as bytes. |
| 641 | `        digest = fnv1a64(f.read())` | `digest`: the FNV-1a hash of these bytes, computed by the test (line 519). |
| 642 | `    check("b: M values", (m.get("mode"), m.get("cpu"), m.get("ctl_cpu"), m.get("bytes"), m.get("check_bytes"), m.get("ntrials"),` | Check of ten `M` values. This line and line 643 read them from the output. |
| 643 | `                          m.get("trace"), m.get("plan_fnv1a64"), m.get("kernels"), m.get("thp")) ==` | Continues the check: the last four values that are read, and the start of the comparison. |
| 644 | `          ("trial", str(E.cpu), str(E.ctl), str(MIB8), str(MIB8), "4", "0", digest, "STAND-IN", "madvise"), m)` | Continues the check: the expected values. The mode is `trial`. The two CPUs are those of the options. `bytes` and `check_bytes` are 8388608. The plan has 4 trials. The trace is off. `plan_fnv1a64` equals the hash that the test computed, so a result names exactly the plan that ran. `kernels` is `STAND-IN`: the build marks itself as not usable for rates. `thp` is `madvise`: huge pages were requested. |
| 645 | `    check("b: the plan pairs are copied to M,plan.<key> rows",` | Check: every pair of the second header line of the plan is copied to a row `M,plan.<key>,<value>`. |
| 646 | `          {k: v for k, v in m.items() if k.startswith("plan.")} ==` | Continues the check: the rows of the output whose key starts with `plan.`. |
| 647 | `          {"plan.step": "T", "plan.session": "1", "plan.cpu": str(E.cpu), "plan.bytes": str(MIB8), "plan.proc": "0",` | Continues the check: the expected pairs, the values that `write_plan` wrote (line 499). |
| 648 | `           "plan.seed": "1", "plan.test": "1"})` | Continues the check: the last two pairs. |
| 649 | `    nwin = sum(len(expected_windows(f)) for f in lines)` | `nwin`: the number of windows of all four trials together. |
| 650 | `    check("b: record storage is sized from the plan and its size is printed",` | Check: the storage for the records is sized from the plan, and its size is printed. |
| 651 | `          m.get("rec_windows") == str(nwin) and m.get("rec_bins") == str(3 * 4 + 2 * 4) and int(m.get("rec_bytes", 0)) > 0, m)` | Continues the check: `rec_windows` equals `nwin`. `rec_bins` is 20: room for 4 bins in each of the 3 windows of trial 2 and of the 2 windows of trial 3. `rec_bytes` is above 0. The design asks that this storage is allocated and first written before the first trial. So no trial spends time on the first use of a page. |
| 652 | `    k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. A `K` row holds a kernel name, the address of its function in hex and that address modulo 64. |
| 653 | `    check("b: one K row per kernel of the plan, with the address modulo 64",` | Check: one `K` row per kernel of the plan, with the address modulo 64. |
| 654 | `          sorted(k) == ["asmread", "oldread", "read"] and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are `asmread`, `oldread` and `read`, and in each row the last field is the hex address modulo 64. That value is the place of the function inside a 64-byte block of code. So each result names the code placement of its run. |
| 655 | `    s = rows.get("S", [])` | `s`: the `S` rows. An `S` row starts a trial. The runner prints it before the trial runs. |
| 656 | `    check("b: S rows hold the plan fields and the previous trial",` | Check: the `S` rows hold the plan fields and the previous trial. |
| 657 | `          [f[1:12] for f in s] == lines and [f[12:] for f in s] ==` | Continues the check: the fields 1 to 11 of each `S` row are the 11 fields of its plan line, and the last two fields are compared with the next line. |
| 658 | `          [["none", "none"], ["A", "oldread@8M"], ["B", "read@1M"], ["C", "asmread@32K"]], s)` | Continues the check: the label and the target of the trial before, and `none` twice for trial 0. The analysis can test with them whether the trial before changes a result. |
| 659 | `    check("b: one E row per S row", [f[1] for f in rows.get("E", [])] == [f[1] for f in s])` | Check: one `E` row per `S` row, with the same trial numbers. An `S` row without its `E` row would mean a trial that was interrupted. |
| 660 | `    check("b: P rows pre and post for every trial",` | Check: each trial has a `P` row `pre` and a `P` row `post`, in this order. |
| 661 | `          [(f[1], f[2]) for f in rows.get("P", [])] == [(str(i), w) for i in range(4) for w in ("pre", "post")] and` | Continues the check: the trial number and the word of each `P` row, against the expected list for the trials 0 to 3. |
| 662 | `          all(len(f) == 9 for f in rows["P"]))` | Continues the check: every `P` row has 9 fields. A `P` row holds the page state of the buffer: its size in kB, its part on huge pages in kB and four page counters of the whole system. |
| 663 | `    last = 0` | `last`: the end time of the trial before, 0 at the start. |
| 664 | `    for i, f in enumerate(lines):` | Loops over the four trials. `f` holds the plan fields of trial `i`. |
| 665 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 666 | `        p = window_problems(f, w)` | Applies the rule `window_problems` (line 115) to the trial. |
| 667 | `        check("b: trial %d: W rows complete, whole passes, 8 MiB rule, durations, monotonic times" % i, not p, p)` | Check b: no problem. The windows are complete, hold whole passes, keep the 8 MiB rule, last at least their requested time and have rising times. |
| 668 | `        check("b: trial %d: starts after the trial before it" % i, int(w[0][7]) >= last)` | Check b: the trial starts at or after the end of the trial before it. So the timed sequences of two trials do not overlap. |
| 669 | `        last = int(w[-1][8])` | Keeps the end time of the last window for the next trial. |
| 670 | `        p = e_problems(f, w, e)` | Applies the rule `e_problems` (line 136). |
| 671 | `        check("d: trial %d: wall_ns, gap_ns and max_boundary_gap_ns equal the W-row differences" % i, not p, p)` | Check d: `wall_ns`, `gap_ns` and `max_boundary_gap_ns` of the `E` row equal the differences of the `W` times. So the gap that the analysis reads is the measured time between the two clock reads. |
| 672 | `        p = bin_problems(f, w, of_trial(rows, "B", i))` | Applies the rule `bin_problems` (line 153). |
| 673 | `        check("e: trial %d: bins rise to the window end and their bytes sum to the window bytes" % i, not p, p)` | Check e: the bins rise to the window end, and their bytes sum to the bytes of the window. |
| 674 | `        check("b: trial %d: E row has 10 fields and count_state closed" % i, len(e) == 10 and e[9] == "closed", e)` | Check b: the `E` row has 10 fields, and its last field, the count state, is `closed`. The plan asked for no counters, and the row confirms that no counter group was open. |
| 675 | `        wall, cpu = int(e[2]), int(e[3])` | `wall`, `cpu`: the wall time and the CPU time of the timed sequence in ns (fields 2 and 3 of the `E` row). |
| 676 | `        check("b: trial %d: cpu_ns is CPU time: not the wall time, at least half of it, at most 1 ms above it" % i,` | Check b: `cpu_ns` is a CPU time and no copy of the wall time. |
| 677 | `              cpu != wall and wall // 2 <= cpu <= wall + 1000000, e)` | Continues the check: it differs from the wall time, is at least half of it and at most 1 ms (1000000 ns) above it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. So the field must hold a separate measurement. |
| 678 | `        pre, post = of_trial(rows, "P", i)` | `pre`, `post`: the two `P` rows of the trial. |
| 679 | `        check("b: trial %d: both P rows hold 8192 kB for the 8 MiB buffer and a number in every field" % i,` | Check b: both `P` rows hold 8192 kB, the size of the 8 MiB buffer, and a number in every later field. |
| 680 | `              pre[3] == post[3] == "8192" and all(v.isdigit() for v in pre[3:] + post[3:]), (pre, post))` | Continues the check: the condition and the detail. A number in the huge-page field shows that the runner could read the page state of the buffer. |
| 681 | `    e = rows["E"]` | `e`: all `E` rows of the run. |
| 682 | `    check("h: sink_ok is 1 for the trials that ran old read", [f[8] for f in e] == ["1", "NA", "NA", "1"], [f[8] for f in e])` | Check h: `sink_ok` (field 8) is `1` for the trials 0 and 3, which ran the old read kernel, and `NA` for the two others. The old read kernel returns the sum of the words that it read. The runner compares the last sum with the expected value. A `1` shows that the result of the old read kernel was used and was right. |
| 683 | `    check("d: gap_ns is NA for the trial whose target has no window before it", e[2][6] == "NA", e[2])` | Check d: `gap_ns` is `NA` for trial 2, whose target has no window before it. A gap that does not exist is not printed as 0. |
| 684 | `    # One pass over 8 MiB takes more than 20 us with the stand-in kernels, so a warm-up pass in the gap fails here.` | Comment: with the stand-in kernels one pass over 8 MiB takes more than 20 us. So a warm-up pass inside the gap makes the next check fail. |
| 685 | `    check("d: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",` | Check d: the gap before an 8 MiB target is below 20 us in trial 0 or in trial 3. So no kernel pass lies inside the gap. |
| 686 | `          min(int(e[0][6]), int(e[3][6])) < 20000, (e[0][6], e[3][6]))` | Continues the check: the smaller of the two gaps must be below 20000 ns. One long gap alone does not fail the check. |
| 687 | `    check("b: the 1 MiB windows hold a multiple of 8 MiB",` | Check b: every window with a pass size of 1 MiB holds a multiple of 8 MiB. The runner reads the clock after 8 passes of 1 MiB. |
| 688 | `          all(int(w[6]) % MIB8 == 0 for w in rows["W"] if w[5] == str(1 << 20)) and` | Continues the check: the condition on all `W` rows with a pass size of 1048576 bytes. |
| 689 | `          any(w[5] == str(1 << 20) for w in rows["W"]))` | Continues the check: at least one such row must exist. If none existed, the condition before would hold without testing anything. |
| 690 | `    check("b: no X row, no C row and no TR row in this run", not rows.get("X") and not rows.get("C") and not rows.get("TR"),` | Check b: this run printed no `X` row (no reported failure), no `C` row (no counters) and no `TR` row (no trace). |
| 691 | `          rows.get("X"))` | Continues the check: the detail that a failure prints. |

### `test_rows`: each rule must fail on changed rows (lines 693 to 722)

| Line | Source | Explanation |
|---:|---|---|
| 693 | `    # every rule must report a problem on changed rows` | Comment: every rule must report a problem on rows that were changed. This proves that the rule can fail. |
| 694 | `    f0, w0, e0 = lines[0], of_trial(rows, "W", 0), of_trial(rows, "E", 0)[0]` | `f0`, `w0`, `e0`: the plan fields, the `W` rows and the `E` row of trial 0. Trial 0 has 10 windows: row 0 is the previous activity, rows 1 to 4 are the prefix, row 5 is the predecessor and rows 6 to 9 are the target. |
| 696 | `    def changed(row_index, field, value):` | Starts the inner function `changed`. It returns a copy of the `W` rows of trial 0 in which one field of one row has a new value. |
| 697 | `        w = [list(x) for x in w0]` | Copies the rows. |
| 698 | `        w[row_index][field] = str(value)` | Sets the field. |
| 699 | `        return w` | Returns the changed rows. |
| 701 | `    check("b: the rule fails on a lost W row", window_problems(f0, w0[:-1]))` | Check: `window_problems` reports a problem when the last `W` row is lost. In the checks of this part the list of problems is the result itself: a list that is not empty counts as passed. |
| 702 | `    check("b: the rule fails on a byte count that is not whole passes", window_problems(f0, changed(2, 6, int(w0[2][6]) + 64)))` | Check: the rule fails on a byte count that is no whole number of passes: prefix window 1 with 64 bytes added. |
| 703 | `    check("b: the rule fails on 0 bytes", window_problems(f0, changed(2, 6, 0)))` | Check: the rule fails on a window with 0 bytes. |
| 704 | `    check("b: the rule fails on a 1 MiB window with 9 MiB", window_problems(f0, changed(5, 6, 9 << 20)))` | Check: the rule fails on the 1 MiB predecessor window with 9 MiB. That is whole passes, but no multiple of 8 MiB. |
| 705 | `    check("b: the rule fails on a window shorter than requested", window_problems(f0, changed(6, 8, int(w0[6][7]) + 19999999)))` | Check: the rule fails on a target window that ends 19999999 ns after its start. That is 1 ns less than the requested 20 ms. |
| 706 | `    check("b: the rule fails on a start before the end of the window before", window_problems(f0, changed(6, 7, int(w0[5][8]) - 1)))` | Check: the rule fails on a target window that starts 1 ns before the end of the predecessor window. |
| 707 | `    check("b: the rule fails on a wrong kernel in a window", window_problems(f0, changed(5, 4, "asmread")))` | Check: the rule fails on a wrong kernel name in the predecessor window. |
| 708 | `    e_bad = list(e0)` | `e_bad`: a copy of the `E` row of trial 0. |
| 709 | `    e_bad[6] = str(int(e0[6]) + 1)` | Adds 1 ns to its `gap_ns`. |
| 710 | `    check("d: the rule fails on a gap_ns that differs from the W rows by 1 ns", e_problems(f0, w0, e_bad))` | Check: `e_problems` fails on a `gap_ns` that differs from the `W` rows by 1 ns. |
| 711 | `    e_bad = list(e0)` | `e_bad`: a fresh copy of the `E` row. |
| 712 | `    e_bad[6] = "0"` | Sets its `gap_ns` to 0. |
| 713 | `    check("d: the rule fails on a gap_ns of 0", int(e0[6]) > 0 and e_problems(f0, w0, e_bad), e0)` | Check: the real gap is above 0, and the rule fails on a gap of 0. So the runner measures the gap and does not assume that it is zero. |
| 714 | `    f2, w2, b2 = lines[2], of_trial(rows, "W", 2), of_trial(rows, "B", 2)` | `f2`, `w2`, `b2`: the plan fields, the `W` rows and the `B` rows of trial 2. That trial has bins and a pass size of 32 KiB. |
| 715 | `    b_bad = [list(x) for x in b2]` | `b_bad`: a copy of the `B` rows. |
| 716 | `    b_bad[-1][5] = str(int(b_bad[-1][5]) - (32 << 10))` | Takes 32 KiB, one pass, from the byte count of the last bin. |
| 717 | `    check("e: the rule fails when the bins do not sum to the window bytes", bin_problems(f2, w2, b_bad))` | Check: `bin_problems` fails when the bins do not sum to the bytes of the window. |
| 718 | `    check("e: the rule fails when the last bin is lost", bin_problems(f2, w2, b2[:-1]))` | Check: the rule fails when the last bin is lost. The bins then do not reach the window end. |
| 719 | `    check("e: the rule fails on B rows in a trial without bins", bin_problems(lines[1], of_trial(rows, "W", 1), b2))` | Check: the rule fails on `B` rows in trial 1, which has no bins. |
| 720 | `    check("e: a 25 ms window has 1 to 3 bins", all(1 <= len([b for b in b2 if b[2] == str(i)]) <= 3 for i in range(3)), b2)` | Check: each of the 3 windows of 25 ms has 1 to 3 bins. The requested bin width is 10 ms, so such a window can close 3 bins at most. |

### `test_sequence_code`, checks c: the timed sequence in source and machine code (lines 723 to 753)

| Line | Source | Explanation |
|---:|---|---|
| 723 | `def test_sequence_code():` | Starts the test `test_sequence_code`. |
| 724 | `    """(c) the timed sequence in the source and in the machine code, without the trace; both functions"""` | Description text: the checks named c. They read the timed sequence from the source and from the machine code, without the trace, for both timed functions. |
| 725 | `    with open(os.path.join(HERE, "bwx11.c")) as f:` | Opens `bwx11.c` in the folder of this file. |
| 726 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 727 | `    p = seq_source_problems(src)` | Applies the rule `seq_source_problems` to it. |
| 728 | `    check("c: source: timed_sequence() and timed_sequence_hot() hold 2 clock reads, 1 kernel call, 2 counter reads and "` | Check: in the source, `timed_sequence()` and `timed_sequence_hot()` hold 2 clock reads, 1 kernel call, 2 counter reads ... |
| 729 | `          "no other call", not p, p)` | Continues the check: ... and no other call. So the text of the timed loop holds nothing that could add time between two clock reads, such as an output or a page read. |
| 730 | `    for name in SEQ_MUTANTS + HOT_SEQ_MUTANTS:` | Loops over the six defects of the two timed functions. |
| 731 | `        m = mutant_source(name)` | `m`: the source text of the runner with the defect `name`. |
| 732 | `        check("c: the source rule fails on a build with " + name, m is not None and seq_source_problems(m))` | Check: the defect could be put in, and the source rule reports a problem on that text. So the rule is proven to find this defect. |
| 733 | `    p = hot_source_problems(src)` | Applies the rule `hot_source_problems` (line 278) to the source. |
| 734 | `    check("c: source: the window loop of timed_sequence_hot() names no field of the window record", not p, p)` | Check: the window loop of `timed_sequence_hot()` names no field of the window record. With `--hot-copy` the loop then cannot read or write that record between the first and the last pass of a window. |
| 735 | `    m = mutant_source(HOT_READ_MUTANT)` | `m`: the source in which the loop reads the pass count from the window record after every pass. |
| 736 | `    check("c: that rule fails on a source where " + HOT_READ_MUTANT, m is not None and hot_source_problems(m))` | Check: the rule fails on that source. |
| 737 | `    for fn in SEQ_FUNCTIONS:` | Loops over the two timed functions. |
| 738 | `        t = seq_targets(E.bin, fn)` | `t`: the branch targets of the function in the machine code of the binary under test. |
| 739 | `        p = seq_code_problems(t, fn)` | Applies the rule `seq_code_problems` to them. |
| 740 | `        check("c: machine code: %s reaches only clock_gettime, the kernels, tcount and the stack-guard failure" % fn,` | Check: in the machine code the function reaches only `clock_gettime`, the kernels, `tcount` and the function for a failed stack guard. This is the proof on the code that really runs: the compiler could have added or kept a call that the source does not show. |
| 741 | `              not p, (p, t))` | Continues the check: the result and the detail. |
| 742 | `        check("c: the machine-code rule fails on a call of fflush (%s)" % fn, seq_code_problems(dict(t, fflush=1), fn))` | Check: the rule fails when a call of `fflush` is added to the targets. `fflush` writes buffered output. |
| 743 | `        check("c: the machine-code rule fails on a helper that is not inlined (%s)" % fn, seq_code_problems(dict(t, tclock=2), fn))` | Check: the rule fails when `tclock` stands among the targets. That is the case when the compiler did not put the clock helper inline. |
| 744 | `        check("c: the machine-code rule fails when the function has no kernel call (%s)" % fn,` | Check: the rule fails when the function has no kernel call. |
| 745 | `              seq_code_problems({k: v for k, v in t.items() if k != "(indirect)"}, fn))` | Continues the check: the targets without the entry `(indirect)`. |
| 746 | `    for fn, name, tag in (("timed_sequence", SEQ_MUTANTS[1], "seq"), ("timed_sequence_hot", HOT_SEQ_MUTANTS[1], "seqhot")):` | Loops over two cases: `timed_sequence` with its page-read defect, and `timed_sequence_hot` with its page-read defect. `tag` names the build folder. |
| 747 | `        b = mutant_build(name, tag)` | `b`: the binary of the runner with that defect (line 473). |
| 748 | `        other = [f for f in SEQ_FUNCTIONS if f != fn][0]` | `other`: the timed function that has no defect in this build. |
| 749 | `        check("c: the machine-code rule fails for %s on a real build with %s, and passes for %s" % (fn, name, other),` | Check: on a real build with the defect the machine-code rule fails for the function with the defect and passes for the other one. |
| 750 | `              b is not None and any("read_vmstat" in x or "fflush" in x for x in seq_code_problems(seq_targets(b, fn), fn)) and` | Continues the check: the build worked, and a problem of the function names `read_vmstat` or `fflush`, the two calls that the defect added ... |
| 751 | `              not seq_code_problems(seq_targets(b, other), other), b and seq_targets(b, fn))` | Continues the check: ... and the other function has no problem. So the rule finds a real forbidden call in the compiled code, and it names the right function. |

### `test_disturbed`, checks i: the values that mark a disturbed trial (lines 754 to 770)

| Line | Source | Explanation |
|---:|---|---|
| 754 | `def test_disturbed():` | Starts the test `test_disturbed`. |
| 755 | `    """(i) the values that mark a disturbed trial, from a trial that shares its CPU with another process"""` | Description text: the checks named i. They read the values that mark a disturbed trial from a trial that shares its CPU with another process. |
| 756 | `    plan = write_plan("shared", ["0 a 1 - oldread@8M:200 - oldread@8M 2 100 closed 0"])` | Writes a plan with one trial: a prefix of `oldread` on 8 MiB for 200 ms and 2 target windows of 100 ms. |
| 757 | `    spin = subprocess.Popen([sys.executable, "-c", "import os\nos.sched_setaffinity(0, {%d})\nwhile True:\n    pass" % E.cpu])` | Starts a second Python process. It pins itself to the worker CPU and then runs an endless loop. So it competes with the worker for that CPU. |
| 758 | `    try:` | Starts a block whose end (line 761) always runs. |
| 759 | `        time.sleep(0.5)  # the other process now runs on the worker CPU` | Waits 0.5 s. By the comment the other process then runs on the worker CPU. |
| 760 | `        rc, out, err = trial(plan)` | Runs the trial. |
| 761 | `    finally:` | The next two lines run also when the trial raised an error. |
| 762 | `        spin.kill()` | Ends the other process with the kill signal. |
| 763 | `        spin.wait()` | Waits until it has ended. |
| 764 | `    e = rows_of(out).get("E", [[]])[0]` | `e`: the `E` row of the trial, or an empty list when the output has none. |
| 765 | `    if not check("i: the trial on a shared CPU ends with status 0 and an E row", rc == 0 and len(e) == 10, err):` | Check: the trial on the shared CPU still ends with status 0 and an `E` row of 10 fields. |
| 766 | `        return` | Ends the test when that check failed. |
| 767 | `    check("i: shared CPU: cpu_ns is below 0.9 x wall_ns", int(e[3]) < 0.9 * int(e[2]), e)` | Check: `cpu_ns` is below 0.9 times `wall_ns`. The worker got only a part of the CPU, and the row shows it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. |
| 768 | `    check("i: shared CPU: nivcsw (involuntary) is above 0 and nvcsw (voluntary) is 0", int(e[5]) > 0 and e[4] == "0", e)` | Check: `nivcsw`, the count of involuntary context switches (field 5), is above 0, and `nvcsw`, the count of voluntary ones (field 4), is 0. Linux took the CPU away from the worker, and the worker never gave it up by itself. A rise of the involuntary count is the second mark of a disturbed trial in the design. |

### `test_placement`, checks j: pin before allocation, and a failed `madvise` (lines 771 to 805)

| Line | Source | Explanation |
|---:|---|---|
| 771 | `def test_placement():` | Starts the test `test_placement`. |
| 772 | `    """(j) pin before allocation, the CPU of the controlling thread, and the X row of a failed madvise"""` | Description text: the checks named j. They cover the pin before the allocation, the CPU of the controlling thread, and the `X` row of a failed `madvise`. |
| 773 | `    d = os.path.join(E.tmp, "shim")` | `d`: the folder `shim` in the temporary folder. |
| 774 | `    os.makedirs(d)` | Creates the folder. |
| 775 | `    with open(os.path.join(d, "shim.c"), "w") as f:` | Opens the file `shim.c` in it for writing. |
| 776 | `        f.write(SHIM)` | Writes the C text `SHIM` (line 368). |
| 777 | `    so = os.path.join(d, "shim.so")` | `so`: the path of the library file `shim.so`. |
| 778 | `    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,` | Compiles the C text with `gcc` into a shared library. `-shared` makes a library that a program can load at its start. `-fPIC` makes code that works at any address. `-O1` is a low optimization level. |
| 779 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call of line 778: the messages of the compiler are collected as one text. |
| 780 | `    if not check("j: the library that logs sched_setaffinity and mmap builds", r.returncode == 0, r.stdout):` | Check j: the library builds. On a failure the compiler messages are printed. |
| 781 | `        return` | Ends the test when the library did not build. |
| 782 | `    plan = write_plan("place", [GOOD])` | Writes a plan with the line `GOOD`. |
| 783 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)], env_add={"LD_PRELOAD": so})` | Runs it with the control CPU `E.ctl` and with `LD_PRELOAD` set to the library. Linux then loads the library before the C library. So the runner calls the `sched_setaffinity`, `mmap` and `madvise` of the library, and each call is logged. |
| 784 | `    lines = [x for x in err.splitlines() if x.startswith("shim ")]` | `lines`: the log lines of the library in the error output. Each one starts with `shim`. |
| 785 | `    p = placement_problems(lines, E.cpu, E.ctl) if rc == 0 and lines else ["rc=%s, %d lines" % (rc, len(lines))]` | Applies the rule `placement_problems` (line 341) when the run ended with status 0 and logged lines. If not, the status and the number of lines are the problem. |
| 786 | `    check("j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself "` | Check j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself ... |
| 787 | `          "before it maps the buffer", not p, (p, lines))` | Continues the check: ... before it maps the buffer. Linux assigns the pages of a buffer at the first touch. A worker that maps and writes its buffer before the pin could do so while it runs on another CPU. |
| 788 | `    if not p:` | Only when the rule passed: the next three checks show that the rule can fail. |
| 789 | `        w = [i for i, x in enumerate(lines) if x.split()[3] != "tid=" + x.split()[2][4:]]` | `w`: the positions of the log lines of the worker thread. These are the lines whose thread id differs from the process id. |
| 790 | `        late = lines[:w[0]] + [lines[w[1]], lines[w[0]]] + lines[w[1] + 1:]` | `late`: the log with the first two logged calls of the worker exchanged. The worker then maps memory before its pin. |
| 791 | `        check("j: the rule fails when the worker maps the buffer before its pin", placement_problems(late, E.cpu, E.ctl))` | Check: the rule fails on that log. |
| 792 | `        no_ctl = [x for x in lines if not x.endswith(" 1 %d" % E.ctl)]` | `no_ctl`: the log without the lines that end with a set of 1 CPU whose first CPU is the control CPU. These are the pins to the control CPU. |
| 793 | `        check("j: the rule fails when the controlling thread does not pin itself", placement_problems(no_ctl, E.cpu, E.ctl))` | Check: the rule fails when the controlling thread does not pin itself. |
| 794 | `        check("j: the rule fails when the worker pins itself to another CPU", placement_problems(lines, E.ctl, E.ctl))` | Check: the rule fails when it is asked for another worker CPU (`E.ctl`) than the one in the log. So a worker on a wrong CPU would be found. |
| 795 | `    rows = rows_of(out)` | `rows`: the output of the first run, sorted by row type. |
| 796 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 797 | `    check("j: madvise that works: M,madvise_ok,1 and no X row", m.get("madvise_ok") == "1" and not rows.get("X"), rows.get("X"))` | Check j: with a working `madvise` the row `M,madvise_ok` holds `1`, and no `X` row is printed. |
| 798 | `    rc, out, err = trial(plan, env_add={"LD_PRELOAD": so, "SHIM_MADVISE_FAIL": "1"})` | Runs the plan again with the variable `SHIM_MADVISE_FAIL` set. The library then lets every `madvise` call of the runner fail (line 400). |
| 799 | `    rows = rows_of(out)` | `rows`: the output of this run, sorted by row type. |
| 800 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 801 | `    check("j: madvise that fails: status 0, M,madvise_ok,0, the row X,-1,madvise, and the trial still runs",` | Check j: a failed page policy request is reported, and the run continues. The exit status is 0, the row `M,madvise_ok` holds `0`, the only `X` row is `X,-1,madvise`, ... |
| 802 | `          rc == 0 and m.get("madvise_ok") == "0" and [f[1:3] for f in rows.get("X", [])] == [["-1", "madvise"]] and` | Continues the check: the three conditions on the exit status, the `M` row and the `X` rows. |
| 803 | `          len(rows.get("E", [])) == 1, (rc, m.get("madvise_ok"), rows.get("X")))` | Continues the check: ... and one `E` row exists, so the trial still ran. The design says that a failed page-policy request is a reported failure and not an assumed success. A result without the requested huge pages is then marked in its own output. |

### `events_of` and `test_trace`, checks c: the trace of closed, open and read trials (lines 806 to 859)

| Line | Source | Explanation |
|---:|---|---|
| 806 | `def events_of(rows, trial_no):` | Starts the function `events_of`. It reads the trace of one trial from the `TR` rows. A `TR` row holds the trial number, the event number, the event name and a time in ns. |
| 807 | `    tr = of_trial(rows, "TR", trial_no)` | `tr`: the `TR` rows of the trial. |
| 808 | `    ok = [int(f[2]) for f in tr] == list(range(len(tr)))` | `ok`: true when the event numbers (field 2) are 0, 1, 2 and so on. |
| 809 | `    return [(f[3], int(f[4])) for f in tr], ok` | Returns the list of pairs of event name and time, and `ok`. |
| 812 | `def test_trace():` | Starts the test `test_trace`. |
| 813 | `    """(c) the trace of closed, open and read trials, and the trace rule on broken traces"""` | Description text: the checks named c on the trace of trials with the count modes `closed`, `open` and `read`, and the trace rule on broken traces. |
| 814 | `    plan = write_plan("trace", ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",` | Writes a plan of 5 trials. Trial 0, label `A`: all phases, the target `oldread` on 8 MiB with 3 windows of 20 ms, counters closed, with bins. |
| 815 | `                                "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",` | Trial 1, label `B`: a prefix, a predecessor and 3 target windows of `read`, with the count mode `read`. In this mode the counter group is open, and the runner reads it at the boundaries of the target windows. |
| 816 | `                                "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",` | Trial 2, label `C`: a prefix and 2 target windows of `asmread`, with the count mode `open`. The counter group is open but is not read. |
| 817 | `                                "3 D 1 - - - read@8M 2 20 read 0",` | Trial 3, label `D`: only 2 target windows of `read`, with the count mode `read`. |
| 818 | `                                "4 E 1 - - - oldread@8M 2 20 closed 0"])` | Trial 4, label `E`: only 2 target windows of `oldread`, counters closed. |
| 819 | `    rc, out, err = trial(plan, ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with `--trace`, the PMU type 1 and the events `task_clock` (code 1) and `cpu_clock` (code 0). By the check of line 825, PMU type 1 means the software events of Linux. With `--trace` the runner logs the events of its wrapper functions and prints them as `TR` rows. The design calls this the non-measuring test: the rates of a trace run are not used. |
| 820 | `    if not check("c: the trace run ends with status 0", rc == 0, err):` | Check c: the trace run ends with status 0. |
| 821 | `        return` | Ends the test when the run failed. |
| 822 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the plan lines. |
| 823 | `    states = [f[9] for f in rows["E"]]` | `states`: the count state of each trial, the last field of its `E` row. |
| 824 | `    E.soft_counters = states == ["closed", "read", "open", "read", "closed"]` | `E.soft_counters`: true when the states are `closed`, `read`, `open`, `read`, `closed`, as the plan asks. The software events then opened on this machine. Later tests read this value. |
| 825 | `    check("c: the software events of Linux (PMU type 1) open on this machine", E.soft_counters, (states, rows.get("X")))` | Check c: the software events of Linux (PMU type 1) open on this machine. On a failure the states and the `X` rows are printed. |
| 826 | `    saved = None` | `saved`: will hold the data of trial 0, for the checks on broken traces. |
| 827 | `    for i, f in enumerate(lines):` | Loops over the trials. `f` holds the plan fields of trial `i`. |
| 828 | `        ev, numbered = events_of(rows, i)` | `ev`: the events of the trial. `numbered`: whether its `TR` rows are numbered without a hole. |
| 829 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 830 | `        p = trace_problems(f, ev, w, e)` | Applies the rule `trace_problems` (line 184). |
| 831 | `        check("c: trial %d (count %s): TR rows are numbered 0, 1, 2, ..." % (i, f[9]), numbered and len(ev) > 0)` | Check c: the `TR` rows of the trial are numbered 0, 1, 2 and so on, and at least one exists. A lost event row would show as a hole in the numbers. |
| 832 | `        check("c: trial %d (count %s): no forbidden event in the timed sequence, and the W rows and gap_ns "` | Check c: no forbidden event lies in the timed sequence, and the times of the `W` rows and `gap_ns` ... |
| 833 | `              "are clock reads of the trace" % (i, f[9]), not p, p)` | Continues the check: ... are clock reads of the trace. By the design a warm-up pass, a page read, an output flush or a counter read must not enter the path from the predecessor to the target, and the recorded gap must hold all the work of the runner between the two kernels. This check proves both on the real call path. |
| 834 | `        names = [n for n, _ in ev]` | `names`: the event names of the trial. |
| 835 | `        want_reads = int(f[7]) + 1 if f[9] == "read" and E.soft_counters else 0` | `want_reads`: the expected number of counter reads. In a trial with the count mode `read`, when the events opened, it is the number of target windows plus 1. In every other trial it is 0. |
| 836 | `        check("c: trial %d (count %s): %d counter reads" % (i, f[9], want_reads), names.count("count_read") == want_reads,` | Check c: the trace holds exactly that many counter reads. That is one reading at each boundary of a target window and none inside a window. |
| 837 | `              names.count("count_read"))` | Continues the check: the number found, as the detail. |
| 838 | `        check("c: trial %d: 2 page reads and 2 outputs, all outside the timed sequence" % i,` | Check c: each trial has 2 page reads and 2 outputs. |
| 839 | `              names.count("page_read") == 2 and names.count("output") == 2)` | Continues the check: the two counts. The trace rule of line 832 has shown that they lie outside the timed sequence. |
| 840 | `        if i == 0:` | For trial 0 only: |
| 841 | `            saved = (f, ev, w, e)` | Keeps the data of trial 0. |
| 842 | `            times = {t for n, t in ev if n == "clock"}` | `times`: the set of the times of all clock reads of the trace. |
| 843 | `            p = bin_problems(f, w, of_trial(rows, "B", 0), times)` | Applies `bin_problems` (line 153) with these times. |
| 844 | `            check("e: every bin end of the trace run is a clock read of the trace", not p, p)` | Check e: every bin end of this run is a clock read of the trace. So the bins add no clock read to the timed loop. |
| 845 | `            b_bad = [list(x) for x in of_trial(rows, "B", 0)]` | `b_bad`: a copy of the `B` rows of trial 0. |
| 846 | `            b_bad[0][4] = str(int(b_bad[0][4]) + 1)` | Adds 1 ns to the end time of its first bin. |
| 847 | `            check("e: the rule fails on a bin end that is no clock read", bin_problems(f, w, b_bad, times))` | Check e: the rule fails on a bin end that is no clock read. |
| 848 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)` | `faults`: the pairs of trial number and count from the comment lines `# minflt,<trial>,<count>` of the output. With `--trace` the runner prints there the minor page faults of the worker between its two reads of the thread statistics, before and after the timed sequence. A minor page fault happens when a thread uses a page that Linux has not yet assigned to it. The pattern matches a whole line: group 1 is the trial number, group 2 the count, which may be negative. |
| 849 | `    check("c: no minor page fault of the worker between the two rusage reads of any trial (records and buffer were "` | Check c: no minor page fault of the worker in the timed sequence of any trial. The records and the buffer were first touched before ... |
| 850 | `          "first touched before)", faults == [(str(i), "0") for i in range(5)], faults)` | Continues the check: the list must hold the trials 0 to 4, each with the count 0. So no window holds the time of the first use of a page. |
| 851 | `    b = mutant_build(TOUCH_MUTANT, "touch")` | `b`: a build of the runner whose record storage is not written before the first trial (line 435). |
| 852 | `    out_m = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--trace", "--pmu-type", "1", "--events",` | Runs the same trace plan with that build and takes its standard output. |
| 853 | `                 "task_clock=1,cpu_clock=0"], binary=b)[1] if b else ""` | Continues the call of line 852: the event list and the binary. Without a build the output is an empty text. |
| 854 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out_m, re.M)` | `faults`: the fault lines of that output. |
| 855 | `    check("c: that check fails on a build with " + TOUCH_MUTANT, len(faults) == 5 and any(int(n) > 0 for _, n in faults), faults)` | Check c: the fault check fails on that build: 5 lines, and at least one count above 0. So the check is proven to find a first touch inside a timed sequence. |
| 856 | `    opens = [[n for n, _ in events_of(rows, i)[0] if n in ("count_open", "count_close")] for i in range(5)]` | `opens`: for each of the 5 trials, its events `count_open` and `count_close` in order. |
| 857 | `    check("c: the group opens before the first counted trial and closes before the next closed trial",` | Check c: the counter group opens before the first counted trial and closes before the next closed trial. |
| 858 | `          opens == [[], ["count_open"], [], [], ["count_close"]], opens)` | Continues the check: trial 1 has one open, trial 4 has one close, the other trials have none. So the group stays open over the trials 1 to 3. A counted trial that follows a counted trial does not open the group again. |

### `test_trace`: the trace rule must fail on broken traces (lines 860 to 897)

| Line | Source | Explanation |
|---:|---|---|
| 860 | `    # the rule on broken traces of trial 0 (closed, all phases)` | Comment: the next checks apply the rule to broken copies of the trace of trial 0, the closed trial with all phases. |
| 861 | `    f, ev, w, e = saved` | `f`, `ev`, `w`, `e`: the saved data of trial 0. |
| 862 | `    names = [n for n, _ in ev]` | `names`: its event names. |
| 863 | `    tgt0 = names.index("kernel_first:target:0")` | `tgt0`: the position of the first kernel call of target window 0. |
| 864 | `    tgt1 = names.index("kernel_first:target:1")` | `tgt1`: the position of the first kernel call of target window 1. |
| 865 | `    pred = names.index("kernel_first:pred:0")` | `pred`: the position of the first kernel call of the predecessor window. |
| 867 | `    def broken(at, name):` | Starts the inner function `broken`. It returns a copy of the trace with one more event, `name`, before the position `at`. |
| 868 | `        return ev[:at] + [(name, ev[at - 1][1])] + ev[at:]` | Returns the events before `at`, then the new event with the time of the event before it, then the events from `at` on. |
| 870 | `    check("c: the rule passes on the unchanged trace", not trace_problems(f, ev, w, e))` | Check c: the rule passes on the unchanged trace. |
| 871 | `    check("c: the rule fails on a page read between predecessor and target", trace_problems(f, broken(tgt0 - 1, "page_read"), w, e))` | Check: the rule fails on a page read between the predecessor and the target. The event is put before the start clock read of target window 0. |
| 872 | `    check("c: the rule fails on a page read between the start clock read of the target and its first kernel call",` | Check: the rule fails on a page read between the start clock read of the target and its first kernel call. |
| 873 | `          trace_problems(f, broken(tgt0, "page_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 874 | `    check("c: the rule fails on an output between two target windows", trace_problems(f, broken(tgt1 - 1, "output"), w, e))` | Check: the rule fails on an output between two target windows. |
| 875 | `    check("c: the rule fails on a counter read between predecessor and target in a closed trial",` | Check: the rule fails on a counter read between the predecessor and the target in a closed trial. |
| 876 | `          trace_problems(f, broken(tgt0 - 1, "count_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 877 | `    check("c: the rule fails on a CPU clock read between predecessor and target in a closed trial",` | Check: the rule fails on a CPU clock read between the predecessor and the target in a closed trial. |
| 878 | `          trace_problems(f, broken(tgt0 - 1, "cpu_clock"), w, e))` | Continues the check: the broken trace and the rule. |
| 879 | `    check("c: the rule fails on a warm-up kernel call before the target", trace_problems(f, broken(tgt0 - 1, "kernel_first:warmup:0"), w, e))` | Check: the rule fails on a warm-up kernel call before the target. The added event has the name `kernel_first:warmup:0`. |
| 880 | `    check("c: the rule fails on a second first call of the target window", trace_problems(f, broken(tgt0 + 1, "kernel_first:target:0"), w, e))` | Check: the rule fails on a second first call of target window 0. |
| 881 | `    check("c: the rule fails on a page read inside the predecessor window", trace_problems(f, broken(pred + 2, "page_read"), w, e))` | Check: the rule fails on a page read inside the predecessor window. |
| 882 | `    check("c: the rule fails on a counter open inside the prefix", trace_problems(f, broken(names.index("kernel_first:prefix:2") + 2, "count_open"), w, e))` | Check: the rule fails on a counter open inside the prefix. |
| 883 | `    check("c: the rule fails on a lost clock read of a window", trace_problems(f, ev[:tgt0 + 1] + ev[tgt0 + 2:], w, e))` | Check: the rule fails on a lost clock read of a window. The event after the first kernel call of target window 0 is removed. |
| 884 | `    one_clock = ev[:tgt0 - 2] + ev[tgt0 - 1:]` | `one_clock`: the trace without the event two places before the first kernel call of target window 0. That event is the end clock read of the predecessor window. |
| 885 | `    check("c: the rule fails when one clock read serves as end and start of a boundary", trace_problems(f, one_clock, w, e))` | Check: the rule fails when one clock read serves as the end of a window and as the start of the next one. The runner must read the clock twice at a boundary. Only then the gap is a measured time. |
| 886 | `    e_bad = list(e)` | `e_bad`: a copy of the `E` row. |
| 887 | `    e_bad[6] = str(int(e[6]) + 5)` | Adds 5 ns to its `gap_ns`. |
| 888 | `    check("d: the rule fails when gap_ns is not the time between the two clock reads", trace_problems(f, ev, w, e_bad))` | Check d: the rule fails when `gap_ns` is not the time between the two clock reads of the trace. |
| 889 | `    # target window 0 (20 ms): the clock read before its last one already lies at the requested end` | Comment: the next case uses target window 0, which has 20 ms. Its clock read before the last one is moved to the requested end. |
| 890 | `    late = list(ev)` | `late`: a copy of the trace. |
| 891 | `    late[tgt1 - 3] = ("clock", ev[tgt0 - 1][1] + 20000000)` | Changes the event three places before the first kernel call of target window 1. That event is the clock read before the last one of target window 0. Its new time is the start of the window plus 20000000 ns, exactly the requested end. |
| 892 | `    p = trace_problems(f, late, w, e)` | Applies the rule to this trace. |
| 893 | `    check("c: the rule fails on a window that runs on after a clock read at its requested end",` | Check c: the rule fails on a window that continues after a clock read at its requested end. |
| 894 | `          names[tgt1 - 3] == "clock" and tgt1 - 3 > tgt0 and p == ["window 6: runs on after the clock read that passed "` | Continues the check: the changed event is a clock read inside target window 0, and the rule reports exactly one problem, for window 6. Window 6 is target window 0: six windows of the trial run before it. |
| 895 | `                                                                 "its requested duration"], p)` | Continues the check: the rest of the expected problem text, and the detail. |

### `test_counters`, checks f: a counter that does not open is reported (lines 898 to 949)

| Line | Source | Explanation |
|---:|---|---|
| 898 | `def test_counters():` | Starts the test `test_counters`. |
| 899 | `    """(f) a failed open is reported, and the timing rows stay"""` | Description text: the checks named f. A failed open is reported, and the timing rows stay. |
| 900 | `    lines = ["0 A 1 - oldread@8M:20 - oldread@8M 2 10 closed 0",` | `lines`: three trials, each with a prefix of 20 ms and 2 target windows of 10 ms of `oldread` on 8 MiB. Trial 0 has the count mode `closed`. |
| 901 | `             "1 B 1 - oldread@8M:20 - oldread@8M 2 10 read 0",` | Trial 1 has the count mode `read`. |
| 902 | `             "2 C 1 - oldread@8M:20 - oldread@8M 2 10 open 0"]` | Trial 2 has the count mode `open`. |
| 903 | `    plan = write_plan("count", lines)` | Writes the plan. |
| 904 | `    rc, out, err = trial(plan, ["--pmu-type", "999999", "--events", "cycles=0x11,instructions=0x08"])` | Runs it with the PMU type 999999 and two events named `cycles` and `instructions`. The check of line 906 says that this PMU type does not exist. So the events cannot open. |
| 905 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 906 | `    check("f: a PMU type that does not exist: status 0", rc == 0, err)` | Check f: the exit status is 0. A counter that does not open does not stop the run. |
| 907 | `    x = [(f[1], f[2]) for f in rows.get("X", [])]` | `x`: the trial number and the code of each `X` row. |
| 908 | `    check("f: an X row with code count_open for each counted trial, none for the closed trial",` | Check f: one `X` row with the code `count_open` for each counted trial, and none for the closed trial. So the result itself says which trials have no usable counts. |
| 909 | `          x == [("1", "count_open"), ("2", "count_open")], rows.get("X"))` | Continues the check: the expected list, the trials 1 and 2. |
| 910 | `    check("f: count_state is fail in the E rows of the counted trials", [f[9] for f in rows.get("E", [])] == ["closed", "fail", "fail"],` | Check f: the count state in the `E` rows is `closed`, `fail`, `fail`. So a trial whose counters did not open says so in its own summary row. |
| 911 | `          rows.get("E"))` | Continues the check: the `E` rows as the detail. |
| 912 | `    check("f: the timing rows of the failed trials are kept",` | Check f: the timing rows of the failed trials are kept. |
| 913 | `          all(not window_problems(f, of_trial(rows, "W", i)) for i, f in enumerate(plan_lines(plan))))` | Continues the check: the `W` rows of every trial pass `window_problems`. The design says to reject unsupported event counts for interpretation and to keep the timing rows. |
| 914 | `    c = rows.get("C", [])` | `c`: the `C` rows. A `C` row belongs to one target window of a trial with the count mode `read`. It holds the enabled time and the running time of the counter group, the thread CPU time, and one count per event. |
| 915 | `    check("f: the C rows of the failed read trial hold NA for the group and a number for the CPU time",` | Check f: the `C` rows of the failed read trial hold `NA` for the group and a number for the CPU time. |
| 916 | `          len(c) == 2 and all(f[1] == "1" and f[3:5] == ["NA", "NA"] and f[5].isdigit() and f[6:] == ["NA", "NA"] for f in c), c)` | Continues the check: 2 rows, both of trial 1. The enabled and the running time are `NA`, the CPU time is a number, and both event counts are `NA`. A count that was not measured is never printed as 0. |
| 917 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary. |
| 918 | `    check("f: M rows record the PMU type and the event codes", m.get("pmu_type") == "999999" and` | Check f: the `M` rows record the PMU type and the event codes. |
| 919 | `          m.get("events") == "cycles=0x11;instructions=0x8", m)` | Continues the check: `pmu_type` is `999999`, and `events` is `cycles=0x11;instructions=0x8`: each name with its code in hex. |
| 921 | `    if not getattr(E, "soft_counters", False):` | Tests whether the software events opened in `test_trace` (line 824). |
| 922 | `        check("f: counter rows with software events (NOT RUN: the events did not open in the trace test)", False)` | If not, the rest of this test cannot run. The line records a failed check with `NOT RUN` in its name. |
| 923 | `        return` | Ends the test in that case. |
| 924 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,bad=999"])` | Runs the plan with the PMU type 1 and two events: `task_clock`, and an event with the code 999, which the test expects not to open. |
| 925 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 926 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 927 | `    check("f: one event of two does not open: X rows count_open and count_state fail",` | Check f: when one event of two does not open, the runner prints `X` rows `count_open` and the count state `fail`. |
| 928 | `          rc == 0 and [(f[1], f[2]) for f in rows.get("X", [])] == [("1", "count_open"), ("2", "count_open")] and` | Continues the check: status 0, and `X` rows for the trials 1 and 2 ... |
| 929 | `          [f[9] for f in rows["E"]] == ["closed", "fail", "fail"] and "1 of 2" in rows["X"][0][3], rows.get("X"))` | Continues the check: ... the states `closed`, `fail`, `fail`, and the text `1 of 2` in the first `X` row. |
| 930 | `    check("f: the event that opened has numbers, the other has NA",` | Check f: the event that opened has numbers, and the other one has `NA`. |
| 931 | `          len(c) == 2 and all(f[3].isdigit() and f[6].isdigit() and f[7] == "NA" for f in c), c)` | Continues the check: in both `C` rows the enabled time and the first count are numbers, and the second count is `NA`. |
| 932 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with two events that open: `task_clock` and `cpu_clock`. |
| 933 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 934 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 935 | `    check("f: events that open: no X row, count_state closed, read, open",` | Check f: with events that open there is no `X` row, and the count states are `closed`, `read`, `open`. |
| 936 | `          rc == 0 and not rows.get("X") and [f[9] for f in rows["E"]] == ["closed", "read", "open"], rows.get("X"))` | Continues the check: the three conditions, and the `X` rows as the detail. |
| 937 | `    check("f: one C row per target window of the read trial only, with enabled, running, CPU time and 2 counts",` | Check f: one `C` row per target window of the read trial only, with the enabled time, the running time, the CPU time and 2 counts. |
| 938 | `          [(f[1], f[2]) for f in c] == [("1", "0"), ("1", "1")] and all(len(f) == 8 and all(v.isdigit() for v in f[3:]) for f in c), c)` | Continues the check: the rows are those of trial 1, windows 0 and 1. Each has 8 fields, and every value is a number. The trial with the count mode `open` prints no `C` row. |
| 939 | `    check("f: running time equals enabled time, and the CPU time is above 0",` | Check f: the running time equals the enabled time, and the CPU time is above 0. |
| 940 | `          all(f[3] == f[4] and int(f[5]) > 0 for f in c), c)` | Continues the check: the condition on both rows. Equal times mean that the counters counted during the whole window. The runner reports a running time below the enabled time as a multiplexed counter. |
| 941 | `    # A C row holds the change over its target window. The group was opened before the 20 ms prefix, so a row that` | Comment: a `C` row holds the change over its target window. The counter group was opened before the prefix of 20 ms. So a row that held the reading itself ... |
| 942 | `    # held the reading itself would be at least 3 times the 10 ms window.` | Comment: ... would be at least 3 times the window of 10 ms. |
| 943 | `    tw = [w for w in of_trial(rows, "W", 1) if w[2] == "target"]` | `tw`: the `W` rows of the target windows of trial 1. |
| 944 | `    span = [int(w[8]) - int(w[7]) for w in tw]` | `span`: the duration of each of these windows in ns. |
| 945 | `    check("f: enabled time, CPU time and both software clocks of a C row lie between half of the window time and "` | Check f: the enabled time, the CPU time and both software clocks of a `C` row lie between half of the window time and ... |
| 946 | `          "the window time plus 1 ms", len(c) == len(span) == 2 and` | Continues the check: ... the window time plus 1 ms. There must be 2 rows and 2 windows. |
| 947 | `          all(n // 2 <= int(v) <= n + 1000000 for f, n in zip(c, span) for v in f[3:]), (c, span))` | Continues the check: every value from field 3 on is compared with the duration of its window. This proves that a `C` row is the difference of two readings at the two ends of one target window, and not a total from the open on. |

### `test_kill_and_seq`, checks g: a killed trial, and the unchanged interval mode (lines 950 to 990)

| Line | Source | Explanation |
|---:|---|---|
| 950 | `def test_kill_and_seq():` | Starts the test `test_kill_and_seq`. |
| 951 | `    """(g) S row without E row after SIGKILL, and the unchanged --seq mode"""` | Description text: the checks named g. After the signal `SIGKILL` an `S` row stands without its `E` row. The mode `--seq` is unchanged. |
| 952 | `    plan = write_plan("kill", [GOOD, "1 long 1 - oldread@8M:400 - oldread@8M 4 5000 closed 0"])` | Writes a plan: the good line, then a long trial 1 with a prefix of 400 ms and 4 target windows of 5000 ms each. |
| 953 | `    path = os.path.join(E.tmp, "kill.csv")` | `path`: the file `kill.csv` in the temporary folder. It takes the output of the runner. |
| 954 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 955 | `        proc = subprocess.Popen([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=f,` | Starts the runner on the plan in the background, with its standard output in that file. |
| 956 | `                                stderr=subprocess.DEVNULL)` | Continues the call of line 955: the error output is discarded. |
| 957 | `    deadline = time.time() + 30` | `deadline`: 30 s from now. |
| 958 | `    while time.time() < deadline and proc.poll() is None:` | Waits as long as the deadline has not passed and the runner still runs: |
| 959 | `        with open(path) as f:` | Opens the output file for reading. |
| 960 | `            if "\nS,1," in f.read():` | Tests whether the file holds the `S` row of trial 1. |
| 961 | `                break` | Leaves the wait loop. |
| 962 | `        time.sleep(0.02)` | Sleeps 0.02 s before the next test of the file. |
| 963 | `    time.sleep(0.2)  # the worker is now inside the timed sequence of trial 1` | Waits 0.2 s more. By the comment the worker is then inside the timed sequence of trial 1. |
| 964 | `    alive = proc.poll() is None` | `alive`: true when the runner still runs. |
| 965 | `    proc.send_signal(signal.SIGKILL)` | Sends the signal `SIGKILL` to the runner. Linux ends the process immediately. The process cannot react to this signal. |
| 966 | `    rc = proc.wait()` | `rc`: the exit status. For a process that a signal ended, Python gives the negative number of the signal. |
| 967 | `    with open(path) as f:` | Opens the output file. |
| 968 | `        rows = rows_of(f.read())` | `rows`: its content sorted by row type. |
| 969 | `    check("g: the process was killed inside trial 1", alive and rc == -signal.SIGKILL, rc)` | Check g: the process was alive before the kill and was ended by `SIGKILL`. So the process was ended while a trial ran. |
| 970 | `    check("g: after SIGKILL the S row of trial 1 has no E row, and trial 0 has both",` | Check g: after the kill the `S` row of trial 1 has no `E` row, and trial 0 has both. |
| 971 | `          [f[1] for f in rows.get("S", [])] == ["0", "1"] and [f[1] for f in rows.get("E", [])] == ["0"], rows.get("E"))` | Continues the check: the `S` rows are those of the trials 0 and 1, and the only `E` row is that of trial 0. The runner prints the `S` row before a trial and all other rows after it. So the analysis can find an interrupted trial: a trial-start record without a trial-complete record, as the design asks. |
| 972 | `    check("g: no W row of the interrupted trial", not of_trial(rows, "W", 1))` | Check g: the output holds no `W` row of the interrupted trial. So no half measurement of it can be used. |
| 974 | `    args = ["--seq", "oldread,asmread@1M,oldread,read", "--bytes", "8M", "--rounds", "2", "--min-ms", "20", "--stop", "pass",` | `args`: a run in the interval mode. The sequence is `oldread`, `asmread` on 1 MiB, `oldread`, `read`. The buffer has 8 MiB. The sequence runs in 2 rounds. Each interval lasts at least 20 ms. With `--stop pass` a thread runs whole passes and stops at the first clock read at or after that minimum time. |
| 975 | `            "--cpus", str(E.cpu), "--threads", "1"]` | Continues line 974: the worker CPU and 1 thread. |
| 976 | `    rc, out, err = run(args)` | Runs these arguments with the runner under test. |
| 977 | `    rc0, out0, _ = run(args, binary=E.bin_old)` | Runs the same arguments with `E.bin_old`, the binary that was built from `bwx.c`, the first runner. |
| 978 | `    r = rows_of(out)` | `r`: the output of the runner under test, sorted by row type. |
| 979 | `    check("g: --seq mode prints 8 I rows, 8 T rows and 8 P rows", rc == 0 and` | Check g: the interval mode prints 8 `I` rows, 8 `T` rows and 8 `P` rows. |
| 980 | `          [len(r.get(k, [])) for k in "ITP"] == [8, 8, 8], (rc, err))` | Continues the check: the three counts. 8 is 4 kernels of the sequence times 2 rounds. An `I` row is one interval, a `T` row is one thread of an interval, and a `P` row is the page state of a buffer. |
| 982 | `    def shape(text):` | Starts the inner function `shape`. It reduces an output text to its form, without the measured values. |
| 983 | `        return [line if line.startswith("#") else (line.split(",")[0], len(line.split(",")), line.split(",")[1:4]) for line in text.splitlines()]` | Returns one item per line of the text. A comment line stays whole. A data row becomes the row type, the number of fields and the fields 1 to 3. For an `I` row and a `T` row these are the round, the position and the kernel. |
| 985 | `    check("g: --seq mode: comment lines byte for byte and row order as the binary built from bwx.c",` | Check g: in the interval mode the comment lines are equal byte for byte, and the rows have the same order, as in the output of the binary built from `bwx.c`. |
| 986 | `          rc0 == 0 and shape(out) == shape(out0))` | Continues the check: both shapes are equal. So the code of the trial mode did not change what the interval mode prints. The design uses the unchanged interval mode to repeat an earlier measurement. |
| 987 | `    check("g: that comparison can fail: another sequence gives another shape",` | Check g: that comparison can fail. |
| 988 | `          shape(out) != shape(run(args[:1] + ["oldread,read"] + args[2:])[1]))` | Continues the check: a run with the shorter sequence `oldread,read` has another shape. |

### Helpers for the source test: `strip_marked`, `ref10_digest`, `sha256`, `path_to_seq` (lines 991 to 1018)

| Line | Source | Explanation |
|---:|---|---|
| 991 | `def strip_marked(text, tag="bwx10"):` | Starts the function `strip_marked`. It removes the marked blocks from a source text. A marked block is an addition of one round. It starts with a comment line `<tag>+` and ends with a comment line `<tag>-`. |
| 992 | `    """(text without the blocks between a line '<tag>+' and a line '<tag>-', number of blocks, markers left)"""` | Description text: the result has three values: the text without the blocks, the number of blocks, and the number of markers that are left. |
| 993 | `    out, n = re.subn(r"^[ \t]*/\* %s\+ \*/\n.*?^[ \t]*/\* %s- \*/\n" % (tag, tag), "", text, flags=re.M \| re.S)` | Removes every block. The pattern matches a line that holds only the comment `/* <tag>+ */` after optional spaces or tabs, then the shortest text up to and with a line that holds only `/* <tag>- */`. `re.subn` returns the new text and the number of blocks removed. |
| 994 | `    return out, n, out.count(tag + "+") + out.count(tag + "-")` | Returns the text, the number of blocks, and the number of marker words `<tag>+` and `<tag>-` that the text still holds. A marker that is left shows a block that was not marked in the right form. |
| 997 | `def ref10_digest(name):` | Starts the function `ref10_digest`. It looks up the checksum of one file of the accepted build of `bwx10`. |
| 998 | `    """the sha256 of a file of the accepted bwx10 build, from ref-bwx10/build.txt"""` | Description text: the sha256 comes from the file `ref-bwx10/build.txt`. |
| 999 | `    with open(os.path.join(REF10, "build.txt")) as f:` | Opens `build.txt` in the folder `REF10`. |
| 1000 | `        m = re.search(r"^([0-9a-f]{64})  %s$" % re.escape(name), f.read(), re.M)` | Searches a line that holds 64 hex digits, two spaces and the file name `name`. Group 1 is the checksum. `re.escape` makes the dot of the file name match a dot only. |
| 1001 | `    return m.group(1) if m else None` | Returns the checksum, or `None` when no such line exists. |
| 1004 | `def sha256(text):` | Starts the function `sha256`. |
| 1005 | `    return hashlib.sha256(text.encode()).hexdigest()` | Returns the sha256 of the text as 64 hex digits. |
| 1008 | `def path_to_seq(binary, last="timed_sequence"):` | Starts the function `path_to_seq`. It reads from the binary where the functions from `call` to the function `last` lie. `call` is the function of the runner that starts a kernel. |
| 1009 | `    """(start of call modulo 64, [(function, distance from call, size)] from call to the function 'last')"""` | Description text: the result is the start of `call` modulo 64, and a list with the name, the distance from `call` and the size of each function from `call` to `last`. |
| 1010 | `    out = subprocess.run(["nm", "-n", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs the tool `nm` on the binary. It lists the symbols. `-n` sorts them by address. `-S` also prints the size of each symbol. |
| 1011 | `    s = [(p[3], int(p[0], 16), int(p[1], 16)) for p in (line.split() for line in out.splitlines()) if len(p) == 4 and p[2] in "tT"]` | `s`: one entry per function: the name, the address and the size. A line counts when it has 4 fields and the symbol type `t` or `T`, the two types of code. |
| 1012 | `    names = [x[0] for x in s]` | `names`: the function names in the order of their addresses. |
| 1013 | `    if "call" not in names or last not in names:` | Tests whether `call` or `last` is not among the names of the functions. |
| 1014 | `        return None, []` | Returns `None` and an empty list in that case. |
| 1015 | `    i, j = names.index("call"), names.index(last)` | `i`, `j`: the positions of `call` and of `last`. |
| 1016 | `    return s[i][1] % 64, [(x[0], x[1] - s[i][1], x[2]) for x in s[i:j + 1]]` | Returns the start address of `call` modulo 64 and, for every function from `call` to `last`, its name, its distance from `call` in bytes and its size in bytes. |

### `test_source`: the runner source is the accepted source plus marked additions (lines 1019 to 1065)

| Line | Source | Explanation |
|---:|---|---|
| 1019 | `def test_source():` | Starts the test `test_source`. The names of its checks start with `source:`. |
| 1020 | `    """bwx11.c is the accepted bwx10.c plus marked additions; bwx10.c is bwx8.c plus marked additions; bwx8.c` | Description text: `bwx11.c` is the accepted `bwx10.c` plus marked additions. `bwx10.c` is `bwx8.c` plus marked additions. `bwx8.c` ... |
| 1021 | `    holds the text of bwx.c"""` | Description text: ... holds the text of `bwx.c`. |
| 1022 | `    with open(os.path.join(OLD, "bwx.c")) as f:` | Opens `bwx.c`, the source of the first runner. |
| 1023 | `        old = f.read()` | `old`: its whole text. |
| 1024 | `    with open(os.path.join(HERE, "bwx11.c")) as f:` | Opens `bwx11.c`. |
| 1025 | `        new11 = f.read()` | `new11`: its whole text. |
| 1026 | `    with open(os.path.join(X8, B8 + ".c")) as f:` | Opens the source of the accepted runner in the folder `X8`. |
| 1027 | `        new8 = f.read()` | `new8`: its whole text. |
| 1028 | `    new10, blocks11, left11 = strip_marked(new11, "bwx11")` | `new10`: the text of `bwx11.c` without its blocks `bwx11+` to `bwx11-` (line 991). `blocks11`: the number of these blocks. `left11`: the number of markers that are left. |
| 1029 | `    want = ref10_digest("bwx10.c")` | `want`: the sha256 of the accepted `bwx10.c`, from the build record (line 997). |
| 1030 | `    check("source: bwx11.c without its %d blocks 'bwx11+' to 'bwx11-' is the accepted bwx10.c byte for byte (sha256 of "` | Check: `bwx11.c` without its marked blocks is the accepted `bwx10.c` byte for byte. The name of the check prints the number of blocks ... |
| 1031 | `          "ref-bwx10/build.txt)" % blocks11,` | Continues the name of the check: ... and says that the sha256 comes from `ref-bwx10/build.txt`. |
| 1032 | `          blocks11 >= 8 and left11 == 0 and want is not None and sha256(new10) == want, (blocks11, left11, want, sha256(new10)))` | Continues the check: at least 8 blocks were removed, no marker is left, the reference checksum was found, and the sha256 of the text equals it. So round 4 only added text. The 26 kernels of `bwx10`, the function `call`, both timed functions and the interval mode are the text that was accepted for `bwx10`. |
| 1033 | `    check("source: that comparison can fail: one changed character outside the marked blocks",` | Check: that comparison can fail on one changed character outside the marked blocks. |
| 1034 | `          sha256(strip_marked(new11.replace("x->bytes = bytes;", "x->bytes = bytes ;", 1), "bwx11")[0]) != want)` | Continues the check: in a copy of `bwx11.c` the first `x->bytes = bytes;` gets a space before its last character. The copy without its marked blocks must have another sha256 than the reference. |
| 1035 | `    check("source: the text of bwx11.c that the compiler sees includes bwx11_selftest.c once, and the old include line "` | Check: the text of `bwx11.c` that the compiler reads includes `bwx11_selftest.c` once, and the old include line ... |
| 1036 | `          "stands inside '#if 0'",` | Continues the name of the check: ... stands inside `#if 0`. |
| 1037 | `          new11.count('#if 0\n/* bwx11- */\n#include "bwx10_selftest.c"\n/* bwx11+ */\n#endif\n#include "bwx11_selftest.c"\n') == 1 and` | Continues the check: six lines must stand together exactly once: `#if 0`, the marker `bwx11-`, the include of `bwx10_selftest.c`, the marker `bwx11+`, `#endif`, and the include of `bwx11_selftest.c`. The compiler skips the text between `#if 0` and `#endif`. The old include line lies outside the marked blocks, so the text without the blocks is still `bwx10.c`. |
| 1038 | `          new11.count('#include "bwx11_selftest.c"') == 1 and new11.count('#include "bwx10_selftest.c"') == 1)` | Continues the check: each of the two include lines stands exactly once in the file. |
| 1039 | `    new, blocks, left = strip_marked(new10)` | `new`: the text `new10` without its blocks `bwx10+` to `bwx10-`. `blocks`: the number of these blocks. `left`: the number of markers that are left. |
| 1040 | `    inc = '#include "bwx10_selftest.c"\n'` | `inc`: the source line that includes the self-test file `bwx10_selftest.c`. |
| 1041 | `    check("source: bwx10.c (that text) without its %d marked blocks, and with the old name of the self-test file, is the "` | Check: the text of `bwx10.c` without its marked blocks, and with the old name of the self-test file, is the ... |
| 1042 | `          "file of the accepted runner bwx8 byte for byte" % blocks,` | Continues the name of the check: ... file of the accepted runner `bwx8` byte for byte. |
| 1043 | `          blocks >= 10 and left == 0 and new.count(inc) == 1 and new.replace(inc, inc.replace("bwx10", B8)) == new8,` | Continues the check: at least 10 blocks were removed, no marker is left, the include line stands once, and the text with the name of the accepted runner in that line equals the source of the accepted runner. |
| 1044 | `          (blocks, left, len(new), len(new8)))` | Continues the check: the detail, with the two counts and the lengths of the two texts. |
| 1045 | `    check("source: that comparison can fail: one changed character outside the marked blocks (bwx8 level)",` | Check: that comparison can fail too. One changed character outside the marked blocks is found at the level of `bwx8`. |
| 1046 | `          strip_marked(new10.replace("x->bytes = bytes;", "x->bytes = bytes ;", 1))[0].replace(inc, inc.replace("bwx10", B8)) != new8)` | Continues the check: the copy with a space put into `x->bytes = bytes;`, without its marked blocks and with the old include name, must differ from the source of the accepted runner. |
| 1047 | `    a8, a11 = fn_span(new8, "timed_sequence"), fn_span(new11, "timed_sequence")` | `a8`, `a11`: the place of the body of `timed_sequence` in `bwx8.c` and in `bwx11.c` (line 263). |
| 1048 | `    check("source: timed_sequence() of bwx11.c is the text of the accepted runner",` | Check: `timed_sequence()` of `bwx11.c` is the text of the accepted runner. |
| 1049 | `          a8 is not None and a11 is not None and new8[a8[0]:a8[1]] == new11[a11[0]:a11[1]])` | Continues the check: both bodies were found, and they are equal. So the loop that times the windows without `--hot-copy` is the loop of the accepted runner, character for character. |
| 1050 | `    h10, h11 = fn_span(new10, "timed_sequence_hot"), fn_span(new11, "timed_sequence_hot")` | `h10`, `h11`: the place of the body of `timed_sequence_hot` in the `bwx10` text and in `bwx11.c`. |
| 1051 | `    check("source: timed_sequence_hot() of bwx11.c is the text of bwx10.c",` | Check: `timed_sequence_hot()` of `bwx11.c` is the text of `bwx10.c`. |
| 1052 | `          h10 is not None and h11 is not None and new10[h10[0]:h10[1]] == new11[h11[0]:h11[1]])` | Continues the check: both bodies were found, and they are equal. |
| 1053 | `    a, b = old.index("#define _GNU_SOURCE"), old.index('#include "bwx_selftest.c"')` | `a`, `b`: two positions in `bwx.c`: the line `#define _GNU_SOURCE` and the line that includes the self-test file of `bwx`. The text between them holds the kernels, the function `call`, the buffer allocation and the code of the interval mode up to the function `parse_events`. |
| 1054 | `    check("source: bwx.c from '#define _GNU_SOURCE' to the end of parse_events() stands unchanged in bwx11.c without "` | Check: the text of `bwx.c` from `#define _GNU_SOURCE` to the end of `parse_events()` stands unchanged in `bwx11.c` without ... |
| 1055 | `          "its marked blocks", new.count(old[a:b]) == 1)` | Continues the check: ... its marked blocks. That old text must stand exactly once in the text without marked blocks. So the kernels and the function `call` of the first runner are unchanged. |
| 1056 | `    kernels_end = new.index(old[a:b]) + len(old[a:b])` | `kernels_end`: the position where that old text ends in the text without marked blocks. |
| 1057 | `    check("source: every line of the trial mode stands after that text",` | Check: every line of the trial mode stands after that text. |
| 1058 | `          min(new.index(s) for s in ("timed_sequence", "trial_main", "tclock", "struct trial")) > kernels_end)` | Continues the check: the first place of each of the names `timed_sequence`, `trial_main`, `tclock` and `struct trial` lies after `kernels_end`. The build keeps the order of the source. So code that is added after the kernels does not move them. |
| 1059 | `    hook = ('    for (int i = 1; i < argc; i++)\n        if (!strcmp(argv[i], "--trial"))\n'` | `hook`: the three source lines that start the trial mode. They loop over the arguments and compare each one with `--trial` ... |
| 1060 | `            '            return trial_main(argc, argv);\n')` | Continues line 1059: ... and call `trial_main` when one argument is `--trial`. |
| 1061 | `    check("source: main() of bwx11.c is main() of bwx.c plus the 3 lines that start the trial mode",` | Check: `main()` of `bwx11.c` is `main()` of `bwx.c` plus the 3 lines that start the trial mode. |
| 1062 | `          new11.count(hook) == 1 and new11[new11.index("int main("):].replace(hook, "") == old[old.index("int main("):])` | Continues the check: the hook stands once in `bwx11.c`. The text from `int main(` to the end of the file, without the hook, equals the same part of `bwx.c`. |
| 1063 | `    check("source: in bwx11.c the evict step and its variables stand after timed_sequence_hot() and before trial_worker()",` | Check: in `bwx11.c` the evict step and its variables stand after `timed_sequence_hot()` and before `trial_worker()`. |
| 1064 | `          0 < new11.find("static void timed_sequence_hot(struct tw") < new11.find("\nstatic long evict_mb;") <` | Continues the check: the positions of four texts must rise: the head of `timed_sequence_hot`, the variable `evict_mb`, ... |
| 1065 | `          new11.find("static int evict_step(void)") < new11.find("\nstatic void *trial_worker("))` | Continues the check: ... the head of `evict_step` and the head of `trial_worker`. By the comment in `bwx11.c`, code and variables that stand after the timed functions move nothing that stands before them. |

### `test_source`: the self-test file is the accepted one plus marked additions (lines 1066 to 1083)

| Line | Source | Explanation |
|---:|---|---|
| 1066 | `    with open(os.path.join(OLD, "bwx_selftest.c")) as f:` | Opens `bwx_selftest.c`, the self-test file of the first runner. |
| 1067 | `        old_st = f.read()` | `old_st`: its whole text. |
| 1068 | `    with open(os.path.join(HERE, "bwx11_selftest.c")) as f:` | Opens `bwx11_selftest.c`. |
| 1069 | `        new_st11 = f.read()` | `new_st11`: its whole text. |
| 1070 | `    with open(os.path.join(X8, B8 + "_selftest.c")) as f:` | Opens the self-test file of the accepted runner in the folder `X8`. |
| 1071 | `        new_st8 = f.read()` | `new_st8`: its whole text. |
| 1072 | `    new_st10, blocks11, left11 = strip_marked(new_st11, "bwx11")` | `new_st10`: the text of `bwx11_selftest.c` without its blocks `bwx11+` to `bwx11-`, with the two counts. |
| 1073 | `    want = ref10_digest("bwx10_selftest.c")` | `want`: the sha256 of the accepted `bwx10_selftest.c`, from the build record. |
| 1074 | `    check("source: bwx11_selftest.c without its %d blocks 'bwx11+' to 'bwx11-' is the accepted bwx10_selftest.c byte for byte "` | Check: `bwx11_selftest.c` without its marked blocks is the accepted `bwx10_selftest.c` byte for byte ... |
| 1075 | `          "(sha256 of ref-bwx10/build.txt)" % blocks11,` | Continues the name of the check: ... by the sha256 of `ref-bwx10/build.txt`. |
| 1076 | `          blocks11 >= 3 and left11 == 0 and want is not None and sha256(new_st10) == want, (blocks11, left11))` | Continues the check: at least 3 blocks were removed, no marker is left, the checksum was found and is equal. So every check of the accepted self-test is kept as it was. |
| 1077 | `    new_st, blocks, left = strip_marked(new_st10)` | `new_st`: that text without its blocks `bwx10+` to `bwx10-`, with the two counts. |
| 1078 | `    check("source: bwx10_selftest.c (that text) without its %d marked blocks is the self-test file of the accepted runner" % blocks,` | Check: the text of `bwx10_selftest.c` without its marked blocks is the self-test file of the accepted runner. |
| 1079 | `          blocks >= 3 and left == 0 and new_st == new_st8)` | Continues the check: at least 3 blocks were removed, no marker is left, and the text equals the self-test file of the accepted runner. |
| 1080 | `    a, b = old_st.index("static int failures;"), old_st.index("static int selftest(void)")` | `a`, `b`: two positions in the self-test file of the first runner: the line `static int failures;` and the head of the function `selftest`. The text between them holds the checks of the kernels. |
| 1081 | `    check("source: the kernel checks of bwx_selftest.c stand unchanged in bwx11_selftest.c without its marked blocks",` | Check: the kernel checks of `bwx_selftest.c` stand unchanged in `bwx11_selftest.c` without its marked blocks. |
| 1082 | `          new_st.count(old_st[a:b]) == 1)` | Continues the check: that old text stands exactly once in the text without marked blocks. |

### `test_source`: the kernels keep their start, size and order in the binary (lines 1084 to 1112)

| Line | Source | Explanation |
|---:|---|---|
| 1084 | `    def syms(binary):` | Starts the inner function `syms`. It reads the kernel symbols of a binary. |
| 1085 | `        out = subprocess.run(["nm", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs `nm -S` on the binary. It lists each symbol with its address and its size. |
| 1086 | `        return {p[3]: (int(p[0], 16) % 64, p[1]) for p in (line.split() for line in out.splitlines())` | Returns a dictionary. The key is a symbol name. The value is the address modulo 64 and the size as text. |
| 1087 | `                if len(p) == 4 and p[3].startswith("k_")}` | Continues line 1086: only lines with 4 fields whose name starts with `k_` are taken. These are the kernel functions. |
| 1089 | `    s_old, s_8, s_10, s_new = syms(E.bin_old), syms(E.bin8), syms(E.bin10), syms(E.bin)` | `s_old`, `s_8`, `s_10`, `s_new`: the kernel symbols of four local builds: `bwx`, `bwx8`, the `bwx10` source and `bwx11`. |
| 1090 | `    common = {k: v for k, v in s_new.items() if k in s_old}` | `common`: the symbols of the build under test whose kernels the first runner also has. |
| 1091 | `    check("source: the 21 old kernels have the same start modulo 64 and the same size in the local builds of bwx, of the "` | Check: the 21 old kernels have the same start modulo 64 and the same size in the local builds of `bwx`, of the ... |
| 1092 | `          "accepted runner and of bwx11", len(s_old) == 21 and s_old == s_8 == common,` | Continues the check: ... accepted runner and of `bwx11`. The first runner has 21 kernels, and the three dictionaries are equal. The start modulo 64 is the place of a function inside a 64-byte block of code. The design keeps this place and the loop bodies fixed. An equal size shows that the machine code of a kernel has the same length. |
| 1093 | `          {k: (s_old[k], s_new.get(k)) for k in s_old if s_old[k] != s_new.get(k)})` | Continues the check: the detail lists each old kernel whose values differ. |
| 1094 | `    check("source: the 26 kernels of bwx10 have the same start modulo 64 and the same size in the local builds of the bwx10 "` | Check: the 26 kernels of `bwx10` have the same start modulo 64 and the same size in the local builds of the `bwx10` ... |
| 1095 | `          "source and of bwx11", len(s_10) == 26 and s_10 == {k: v for k, v in s_new.items() if k in s_10},` | Continues the check: ... source and of `bwx11`. The `bwx10` build has 26 kernels, and each has the same two values in `bwx11`. |
| 1096 | `          {k: (s_10[k], s_new.get(k)) for k in s_10 if s_10[k] != s_new.get(k)})` | Continues the check: the detail lists each kernel whose values differ. |
| 1097 | `    check("source: bwx11 has 29 kernels: the 21 old ones, the 5 of round 3 and the 3 new ones",` | Check: `bwx11` has 29 kernels: the 21 old ones, the 5 of round 3 and the 3 new ones. |
| 1098 | `          sorted(set(s_new) - set(s_old)) == sorted("k_" + k for k in NEW_KERNELS + NOP_KERNELS) and` | Continues the check: the kernels that `bwx` does not have are exactly `NEW_KERNELS` plus `NOP_KERNELS` ... |
| 1099 | `          sorted(set(s_new) - set(s_10)) == sorted("k_" + k for k in NOP_KERNELS), sorted(set(s_new) - set(s_old)))` | Continues the check: ... and the kernels that the `bwx10` build does not have are exactly `NOP_KERNELS`. |
| 1100 | `    check("source: the three new kernels start where asmread starts, modulo 64 (the pad of asmread)",` | Check: the three new kernels start where `asmread` starts, modulo 64. The source gives them the pad of `asmread`. |
| 1101 | `          all(s_new.get("k_" + k, (None,))[0] == s_new["k_asmread"][0] for k in NOP_KERNELS), [s_new.get("k_" + k) for k in NOP_KERNELS])` | Continues the check: the start modulo 64 of each new kernel equals that of `k_asmread`. The new kernels are the `asmread` loop with added `nop` instructions. By the comment in `bwx11.c`, their loop then starts at the same offset modulo 64 as the loop of `asmread` in a build for AArch64. |
| 1103 | `    def order(binary):` | Starts the inner function `order`. It reads the order of the kernels in a binary. |
| 1104 | `        out = subprocess.run(["nm", "-n", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs `nm -n` on the binary. It lists the symbols sorted by address. |
| 1105 | `        return [line.split()[-1] for line in out.splitlines() if line.split()[-1].startswith("k_")]` | Returns the symbol names that start with `k_`, in that order. |
| 1107 | `    o = order(E.bin)` | `o`: the order of the kernels in the binary under test. |
| 1108 | `    check("source: in the binary the 5 kernels of round 3 stand after every old kernel, in the order of the table, and the "` | Check: in the binary the 5 kernels of round 3 stand after every old kernel, in the order of the kernel table, and the ... |
| 1109 | `          "3 new kernels stand after them",` | Continues the name of the check: ... 3 new kernels stand after them. |
| 1110 | `          o[21:26] == ["k_" + k for k in NEW_KERNELS] and o[:21] == order(E.bin8) and o[:26] == order(E.bin10) and` | Continues the check: the places 22 to 26 hold `NEW_KERNELS`, the first 21 places equal the order in the `bwx8` build, the first 26 equal the order in the `bwx10` build ... |
| 1111 | `          o[26:] == ["k_" + k for k in NOP_KERNELS], o[20:])` | Continues the check: ... and the last places hold `NOP_KERNELS`. A kernel that is added behind all others leaves the addresses of the others as they were. |

### `test_source`: the place of the code after the kernels, and the text of `evict_step` (lines 1113 to 1167)

| Line | Source | Explanation |
|---:|---|---|
| 1113 | `    # The pad after the new kernels. bwx11.c holds the value of the accepted AArch64 build (24) in` | Comment: the pad after the new kernels. `bwx11.c` holds the value of the accepted AArch64 build, 24, in ... |
| 1114 | `    # PAD_after_kernels, and PAD_after_kernels11 takes that value. A copy built with the value of the local build` | Comment: ... `PAD_after_kernels`, and `PAD_after_kernels11` takes that value. A copy built with the value of the local build ... |
| 1115 | `    # of the accepted runner must place every function from call() to timed_sequence() as that build does.` | Comment: ... of the accepted runner must place every function from `call()` to `timed_sequence()` as that build does. |
| 1116 | `    E.call8, path8 = path_to_seq(E.bin8)` | `E.call8`: the start of `call` modulo 64 in the local build of the accepted runner. `path8`: its functions from `call` to `timed_sequence`, as `path_to_seq` returns them. |
| 1117 | `    if not check("source: the local build of the accepted runner has call() and timed_sequence() as functions "` | Check: the local build of the accepted runner has `call()` and `timed_sequence()` as functions ... |
| 1118 | `                 "(needed for the placement checks)", E.call8 is not None and len(path8) >= 3, path8[:3]):` | Continues the check: ... and at least 3 functions on that path. The placement checks need them. |
| 1119 | `        return` | Ends the test when they are missing. |
| 1120 | `    E.bin_placed = os.path.join(E.tmp, "bwx11-placed")` | `E.bin_placed`: the path `bwx11-placed` in the temporary folder, for a second build of `bwx11.c`. |
| 1121 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % E.call8, "-o", E.bin_placed, os.path.join(HERE, "bwx11.c")])` | Compiles `bwx11.c` with `-DPAD_after_kernels=` and the value `E.call8`. The pad after the kernels then has the value that matches the local machine. |
| 1122 | `    call_p, path_p = path_to_seq(E.bin_placed) if r.returncode == 0 else (None, [])` | `call_p`, `path_p`: the placement of that build, or `None` and an empty list when the compiler failed. |
| 1123 | `    check("source: with the pad of the local build, the functions from call() to timed_sequence() (at least 10) have the "` | Check: with the pad of the local build, the functions from `call()` to `timed_sequence()` (at least 10) have the ... |
| 1124 | `          "start modulo 64, the distances and the sizes of the accepted runner",` | Continues the name of the check: ... start modulo 64, the distances and the sizes of the accepted runner. |
| 1125 | `          call_p == E.call8 and path_p == path8 and len(path8) >= 10, (call_p, E.call8, len(path8), [x for x in zip(path_p, path8) if x[0] != x[1]][:3]))` | Continues the check: the start of `call` and the whole list are equal in both builds, and the list has at least 10 functions. These functions are the code that runs around the kernel call inside a timed sequence. So the kernels that were added do not move this code, and they do not change its length. |
| 1126 | `    other = (E.call8 + 4) % 64` | `other`: a pad that is 4 bytes larger, modulo 64. |
| 1127 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % other, "-o", E.bin_placed + "-off", os.path.join(HERE, "bwx11.c")])` | Compiles `bwx11.c` with that other pad into `bwx11-placed-off`. |
| 1128 | `    check("source: that comparison can fail: a pad 4 bytes larger moves call() by 4 bytes",` | Check: that comparison can fail: a pad 4 bytes larger moves `call()` by 4 bytes. |
| 1129 | `          r.returncode == 0 and path_to_seq(E.bin_placed + "-off")[0] == other, (other, path_to_seq(E.bin_placed + "-off")[0]))` | Continues the check: the build worked, and its `call` starts at `other` modulo 64. |
| 1130 | `    with open(os.path.join(REF, "listing.txt")) as f:` | Opens `listing.txt` in the folder `REF`. It is the machine-code listing of the accepted build of `bwx8`. |
| 1131 | `        ref_text = f.read()` | `ref_text`: its whole text. |
| 1132 | `    last = max(int(x, 16) for x in re.findall(r"^\s+([0-9a-f]+):\t", ref_text, re.M))` | `last`: the highest instruction address of that listing. The pattern finds the hex address at the start of each instruction line, before a colon and a tab. |
| 1133 | `    m = re.search(r"^#define PAD_after_kernels (\d+)$", new11, re.M)` | `m`: the source line `#define PAD_after_kernels` with its number in `bwx11.c`. Group 1 is the number. |
| 1134 | `    check("source: the pad in bwx11.c (24) is the address after the last instruction of the last kernel in "` | Check: the pad in `bwx11.c` (24) is the address after the last instruction of the last kernel in ... |
| 1135 | `          "ref-bwx8/listing.txt (0x4a14, a ret), modulo 64",` | Continues the name of the check: ... `ref-bwx8/listing.txt`, modulo 64. The name gives that last instruction as a `ret` at 0x4a14. |
| 1136 | `          m is not None and int(m.group(1)) == (last + 4) % 64 == 24 and "    %x:\tret\n" % last in ref_text, (m and m.group(1), hex(last)))` | Continues the check: the number of the `#define` equals `last + 4` modulo 64 and equals 24, and the instruction at `last` is `ret`. An AArch64 instruction has 4 bytes. So `last + 4` is the first address after the kernels in the accepted build. |
| 1137 | `    # round 4: the same placement against the bwx10 source, up to timed_sequence_hot(). Both local builds use the` | Comment: round 4 makes the same placement check against the `bwx10` source, up to `timed_sequence_hot()`. Both local builds use the ... |
| 1138 | `    # pad 24 of the source, so call() starts at 24 modulo 64 in both.` | Comment: ... pad 24 of the source. So `call()` starts at 24 modulo 64 in both. |
| 1139 | `    call10, path10 = path_to_seq(E.bin10, "timed_sequence_hot")` | `call10`, `path10`: the placement of the local build of the `bwx10` source, from `call` to `timed_sequence_hot`. |
| 1140 | `    call11, path11 = path_to_seq(E.bin, "timed_sequence_hot")` | `call11`, `path11`: the same for the build of `bwx11` under test. |
| 1141 | `    check("source: the functions from call() to timed_sequence_hot() (at least 12) have the start modulo 64, the distances "` | Check: the functions from `call()` to `timed_sequence_hot()` (at least 12) have the start modulo 64, the distances ... |
| 1142 | `          "and the sizes of the local build of the bwx10 source",` | Continues the name of the check: ... and the sizes of the local build of the `bwx10` source. |
| 1143 | `          call10 is not None and call11 == call10 == 24 and path11 == path10 and len(path10) >= 12,` | Continues the check: `call` was found, it starts at 24 modulo 64 in both builds, the two lists are equal, and the list has at least 12 functions. So the three kernels of round 4 moved no function of the timed path. |
| 1144 | `          (call11, call10, len(path10), [x for x in zip(path11, path10) if x[0] != x[1]][:3]))` | Continues the check: the detail, with the first three functions that differ. |
| 1145 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels11=28", "-o", E.bin_placed + "-off11", os.path.join(HERE, "bwx11.c")])` | Compiles `bwx11.c` with `-DPAD_after_kernels11=28` into `bwx11-placed-off11`. |
| 1146 | `    check("source: that comparison can fail: with PAD_after_kernels11 set to 28, call() starts at 28 modulo 64",` | Check: that comparison can fail: with `PAD_after_kernels11` set to 28, `call()` starts at 28 modulo 64. |
| 1147 | `          r.returncode == 0 and path_to_seq(E.bin_placed + "-off11", "timed_sequence_hot")[0] == 28)` | Continues the check: the build worked, and `path_to_seq` gives 28 for it. |
| 1148 | `    check("source: PAD_after_kernels11 takes the value of PAD_after_kernels unless it is given",` | Check: `PAD_after_kernels11` takes the value of `PAD_after_kernels` unless it is given. |
| 1149 | `          "#ifndef PAD_after_kernels11\n#define PAD_after_kernels11 PAD_after_kernels\n#endif\nPLACE(after_kernels11);\n" in new11)` | Continues the check: the four source lines `#ifndef`, `#define`, `#endif` and `PLACE(after_kernels11);` stand together in `bwx11.c`. |
| 1150 | `    with open(os.path.join(REF10, "build.txt")) as f:` | Opens `build.txt` in the folder `REF10`. |
| 1151 | `        placed = re.search(r"^## placement bwx10 \(start modulo 64\): call=(\d+) ", f.read(), re.M)` | `placed`: the line `## placement bwx10 (start modulo 64): call=` with a number in that build record. Group 1 is the number. |
| 1152 | `    check("source: ref-bwx10/build.txt records call() of the accepted bwx10 at that pad (24) modulo 64",` | Check: `ref-bwx10/build.txt` records `call()` of the accepted `bwx10` at that pad (24) modulo 64. |
| 1153 | `          placed is not None and m is not None and placed.group(1) == m.group(1) == "24", placed and placed.group(0))` | Continues the check: the line was found, and its number and the number of the `#define` are both `24`. |
| 1154 | `    # the bwx10 source with the local pad: the reference binary of the placement record of build11.sh` | Comment: the `bwx10` source built with the local pad is the reference binary for the placement record of `build11.sh` (line 1612). |
| 1155 | `    E.bin10_placed = os.path.join(E.tmp, "bwx10-placed")` | `E.bin10_placed`: the path `bwx10-placed` in the temporary folder. |
| 1156 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-DPAD_after_kernels=%d" % E.call8, "-o", E.bin10_placed, os.path.join(E.src10, "bwx10.c")])` | Compiles the `bwx10` source with `-DPAD_after_kernels=` and the value `E.call8`. |
| 1157 | `    check("source: the bwx10 source builds with the local pad (needed for the placement record of build11.sh)", r.returncode == 0)` | Check: that build works. The placement record of `build11.sh` needs it. |
| 1158 | `    span = fn_span(new11, "evict_step")` | `span`: the place of the body of `evict_step` in `bwx11.c`. |
| 1159 | `    body = re.sub(r"/\*.*?\*/", "", new11[span[0]:span[1]], flags=re.S) if span else ""` | `body`: that body without C comments, or an empty text when the function was not found. |
| 1160 | `    check("source: evict_step() maps plain anonymous private memory, stores one word per 64 B line in ascending order in "` | Check: `evict_step()` maps plain anonymous private memory, stores one word per 64 B line in ascending order in ... |
| 1161 | `          "2 passes, unmaps, and calls no madvise",` | Continues the name of the check: ... 2 passes, unmaps, and calls no `madvise`. |
| 1162 | `          "mmap(NULL, len, PROT_READ \| PROT_WRITE, MAP_PRIVATE \| MAP_ANONYMOUS, -1, 0)" in body and` | Continues the check: the body holds the `mmap` call with exactly these arguments: readable and writable memory that belongs to the process alone and has no file behind it ... |
| 1163 | `          "    for (int pass = 0; pass < 2; pass++)\n        for (size_t i = 0; i < len / 8; i += 8)\n            m[i] = " in body and` | Continues the check: ... the two loops: 2 passes, and in each pass one store to every eighth 8-byte word, which is one store per 64 bytes ... |
| 1164 | `          "volatile uint64_t *m" in body and "munmap((void *)m, len)" in body and "madvise" not in body and` | Continues the check: ... a pointer of the kind `volatile`, which makes the compiler keep every store, the `munmap` call, no `madvise` ... |
| 1165 | `          "size_t len = (size_t)evict_mb << 20;" in body, body[:300])` | Continues the check: ... and the length `evict_mb` times 1 MiB. The option `--evict-mb` has its effect only when the step really writes that much other memory. This check fixes the text of the step. |

### `test_selftest`: the self-test of the runner, and builds that it must reject (lines 1168 to 1224)

| Line | Source | Explanation |
|---:|---|---|
| 1168 | `def test_selftest():` | Starts the test `test_selftest`. |
| 1169 | `    rc, out, err = run(["--selftest"])` | Runs the runner with `--selftest`. The self-test checks what the kernels do to memory and how the trial mode counts bytes and times. It measures no rate. |
| 1170 | `    trial_lines = [line for line in out.splitlines() if line.startswith("trial,")]` | `trial_lines`: the lines of its output that start with `trial,`. Each one is one check of the trial mode and ends with `pass` or `FAIL`. |
| 1171 | `    check("selftest: status 0, no FAIL line, 33 checks of the trial mode (19 of the accepted runner, 8 with --hot-copy, "` | Check: the self-test ends with status 0 and no `FAIL` line, and it has 33 checks of the trial mode (19 of the accepted runner, 8 with `--hot-copy`, ... |
| 1172 | `          "3 of the touch test, 3 of the evict step)",` | Continues the name of the check: ... 3 of the touch test and 3 of the evict step). |
| 1173 | `          rc == 0 and "FAIL" not in out and out.rstrip().endswith("# failures=0") and len(trial_lines) == 33 and` | Continues the check: status 0, the word `FAIL` nowhere, the last line `# failures=0`, and 33 lines that start with `trial,` ... |
| 1174 | `          all(line.endswith(",pass") for line in trial_lines) and` | Continues the check: ... every such line ends with `,pass` ... |
| 1175 | `          len([x for x in trial_lines if x.startswith("trial,hot copy: ")]) == 8 and` | Continues the check: ... 8 of them start with `trial,hot copy: ` ... |
| 1176 | `          len([x for x in trial_lines if x.startswith("trial,hot touch: ")]) == 3 and` | Continues the check: ... 3 start with `trial,hot touch: ` ... |
| 1177 | `          len([x for x in trial_lines if x.startswith("trial,evict: ")]) == 3, (rc, err, len(trial_lines)))` | Continues the check: ... and 3 start with `trial,evict: `. The fixed counts show that no check of the self-test was lost. On a failure the status, the error output and the count are printed. |
| 1178 | `    out10 = run(["--selftest"], binary=E.bin10)[1]` | `out10`: the self-test output of the local build of the `bwx10` source. |
| 1179 | `    drop = lambda text: [x for x in text.splitlines() if not x.startswith("#") and x.split(",")[0] not in NOP_KERNELS and` | `drop`: a function that reduces a self-test output to the lines that both versions must share. It leaves out the comment lines, the check lines of the three new kernels ... |
| 1180 | `                         not (x.startswith("call,") and x.split(",")[1] in NOP_KERNELS) and not x.startswith("trial,evict: ")]` | Continues line 1179: ... the `call,` lines of these kernels and the lines of the evict step. |
| 1181 | `    check("selftest: without the lines of the three new kernels and of the evict step, the output is the output of the "` | Check: without the lines of the three new kernels and of the evict step, the output is the output of the ... |
| 1182 | `          "self-test of the bwx10 source, line for line", len(drop(out10)) > 200 and drop(out) == drop(out10),` | Continues the check: ... self-test of the `bwx10` source, line for line. More than 200 lines are compared. So the additions of round 4 changed no result of an earlier check. |
| 1183 | `          (len(drop(out)), len(drop(out10))))` | Continues the check: the two line counts as the detail. |
| 1184 | `    out8 = run(["--selftest"], binary=E.bin8)[1]` | `out8`: the self-test output of the local build of the accepted runner. |
| 1186 | `    def kernel_checks(text, k):` | Starts the inner function `kernel_checks`. It returns the checks that a self-test output holds for the kernel `k`. |
| 1187 | `        return sorted(",".join(line.split(",")[1:]) for line in text.splitlines() if line.startswith(k + ","))` | Returns these checks as a sorted list. It takes the lines that start with the kernel name and a comma and removes the name. What is left of each line is the check, the byte count and the result. |
| 1189 | `    want = kernel_checks(out8, "asmread")` | `want`: the checks of `asmread` in the output of the accepted runner. |
| 1190 | `    check("selftest: asmread has 8 checks in the accepted runner (the reference for the next check)",` | Check: `asmread` has 8 checks in the accepted runner, and all pass. They are the reference for the next check. |
| 1191 | `          len(want) == 8 and all(x.endswith(",pass") for x in want), want)` | Continues the check: the count and the results. |
| 1192 | `    for k in NEW_KERNELS + NOP_KERNELS:` | Loops over the 5 kernels of round 3 and the 3 kernels of round 4. |
| 1193 | `        check("selftest: %s gets the 8 checks of a read kernel, all pass" % k, kernel_checks(out, k) == want, kernel_checks(out, k))` | Check: the kernel `k` gets the same 8 checks as `asmread`, and all pass. By the description in the self-test file, a read kernel must leave the buffer unchanged, must touch no page outside its range and must touch every page inside it. So each added kernel is proven to read the range for which the runner counts its bytes. |
| 1194 | `    check("selftest: that comparison can fail: a kernel that is not in the output has no check", kernel_checks(out, "read_nop63") != want)` | Check: that comparison can fail: `read_nop63`, a kernel that the output does not hold, has no check. |
| 1195 | `    # the self-test must fail on a broken wrapper: a build that counts one pass too many per clock read` | Comment: the self-test must fail on a broken wrapper, a build that counts one pass too many per clock read. A wrapper here is the code of the runner around the kernel call. |
| 1196 | `    with open(os.path.join(HERE, "bwx11.c")) as f:` | Opens `bwx11.c`. |
| 1197 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 1198 | `    good = "        x->bytes = bytes;\n"` | `good`: the source line that stores the byte total of a window, `x->bytes = bytes;`. |
| 1199 | `    n = 0` | `n`: a counter for the names of the build folders. |
| 1200 | `    for fn, own in (("timed_sequence", "trial,every window lasts"), ("timed_sequence_hot", "trial,hot copy: every window lasts")):` | Loops over the two timed functions. `own` is the start of the self-test lines of that function: `trial,every window lasts` for `timed_sequence` and `trial,hot copy: every window lasts` for `timed_sequence_hot`. |
| 1201 | `        for name, bad in (("a window that counts 256 bytes too many", "        x->bytes = bytes + 256;\n"),` | Loops over two defects. Defect 1: the stored byte total of a window is 256 bytes too high. The comment of line 1195 names another defect, one pass too many per clock read. The code does not build that one. |
| 1202 | `                          ("a window whose end is before its start", "        x->bytes = bytes; t1 = t0 - 1;\n")):` | Defect 2: the byte total is right, but the end time of the window is set to 1 ns before its start time. |
| 1203 | `            n += 1` | Counts the build. |
| 1204 | `            d = os.path.join(E.tmp, "broken%d" % n)` | `d`: the folder `broken` plus the number in the temporary folder. |
| 1205 | `            os.makedirs(d, exist_ok=True)` | Creates it. |
| 1206 | `            changed = replace_in(src, fn, good, bad)` | `changed`: the source with the defect in the function `fn`, or `None` when the line was not found exactly once. |
| 1207 | `            with open(os.path.join(d, "bwx11.c"), "w") as f:` | Opens `bwx11.c` in that folder for writing. |
| 1208 | `                f.write(changed or "")` | Writes the changed source, or an empty text when the defect could not be put in. |
| 1209 | `            shutil.copy(os.path.join(HERE, "bwx11_selftest.c"), d)` | Copies `bwx11_selftest.c` into the folder. |
| 1210 | `            ok = changed is not None and subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx11"), os.path.join(d, "bwx11.c")]).returncode == 0` | `ok`: true when the defect was put in and `gcc` built the copy with exit status 0. |
| 1211 | `            rc, out, _ = run(["--selftest"], binary=os.path.join(d, "bwx11"))` | Runs the self-test of that build. |
| 1212 | `            fails = [x for x in out.splitlines() if x.endswith(",FAIL")]` | `fails`: the lines of its output that end with `,FAIL`. |
| 1213 | `            check("selftest: status 1 for a build with %s in %s, and the failed checks are those of that function" % (name, fn),` | Check: the self-test ends with status 1 for a build with that defect in `fn`, and the failed checks are those of that function. |
| 1214 | `                  ok and rc == 1 and any(x.startswith(own) or x.startswith(own.replace("lasts", "holds")) for x in fails) and` | Continues the check: the build worked, the status is 1, and one failed line starts with `own`, or with `own` with the word `holds` in place of `lasts`. Defect 1 fails the check that every window holds whole passes. Defect 2 fails the check that every window lasts its requested time. |
| 1215 | `                  all(x.startswith("trial,hot ") if fn == "timed_sequence_hot" else not x.startswith("trial,hot copy: ") for x in fails),` | Continues the check: for `timed_sequence_hot` every failed line must start with `trial,hot `. For `timed_sequence` no failed line may start with `trial,hot copy: `. So the self-test shows which of the two functions counts wrongly. |
| 1216 | `                  (rc, fails))` | Continues the check: the status and the failed lines as the detail. |
| 1217 | `    b = mutant_build(HOT_READ_MUTANT, "hotread")` | `b`: a build in which `timed_sequence_hot` reads the pass count from the window record after every pass (line 441). |
| 1218 | `    rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1219 | `    fails = [x for x in out.splitlines() if x.endswith(",FAIL")]` | `fails`: the lines of that output that end with `,FAIL`. |
| 1220 | `    check("selftest: status 1 for a build where %s: the touch test sees it on the machine code" % HOT_READ_MUTANT,` | Check: the self-test ends with status 1 for that build. The touch test finds the defect in the machine code. |
| 1221 | `          rc == 1 and fails == ["trial,hot touch: timed_sequence_hot does not touch the window record between the first "` | Continues the check: the only failed line is the check that `timed_sequence_hot` does not touch the window record between the first ... |
| 1222 | `                                "and the last pass,0,FAIL"], (rc, fails))` | Continues the check: ... and the last pass. By the description in the self-test file, the touch test puts the window record into a memory page of its own, makes that page unusable for 20 ms while a window runs, and counts the faults. It runs the compiled code, so it also finds a read that the source text does not show. |

### `test_selftest_rows`, `run_listing` and `shift_block` (lines 1225 to 1251)

| Line | Source | Explanation |
|---:|---|---|
| 1225 | `def test_selftest_rows():` | Starts the test `test_selftest_rows`. |
| 1226 | `    """the row checks of the self-test fail on a build that prints a wrong value"""` | Description text: the row checks of the self-test must fail on a build that prints a wrong value. |
| 1227 | `    for n, name in enumerate(ROW_MUTANTS):` | Loops over the defects of the output rows, `ROW_MUTANTS` (line 455). |
| 1228 | `        b = mutant_build(name, "row%d" % n)` | `b`: a build of the runner with that defect. |
| 1229 | `        rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1230 | `        check("selftest: status 1 for a build with " + name, rc == 1 and ",FAIL" in out, rc)` | Check: the self-test ends with status 1 and prints a line with `,FAIL`. The self-test lets the runner print the rows of a record with known values and compares the text. So a runner that prints a wrong field, for example the wall time as CPU time, does not pass its own self-test. |
| 1233 | `def run_listing(args):` | Starts the function `run_listing`. It runs the listing check with the arguments `args`. |
| 1234 | `    r = subprocess.run([sys.executable, os.path.join(HERE, "check_listing11.py")] + args, stdout=subprocess.PIPE,` | Starts `check_listing11.py` with the Python interpreter that runs this test. |
| 1235 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that starts the listing check: the error output goes into the standard output, and the result is text. |
| 1236 | `    return r.returncode, r.stdout` | Returns the exit status and the output. |
| 1239 | `def shift_block(text, binary, kernel, by):` | Starts the function `shift_block`. It moves one kernel of a listing text to other addresses. |
| 1240 | `    """adds 'by' to every address of one '=== binary kernel ===' block of a listing"""` | Description text: it adds `by` to every address of one block of a listing. A block starts with a head line `=== binary kernel ===`. |
| 1241 | `    out, inside = [], False` | `out`: the new lines. `inside`: whether the current line belongs to the block to move. |
| 1242 | `    for line in text.split("\n"):` | Loops over the lines of the listing. |
| 1243 | `        if line.startswith("==="):` | A line that starts with `===` is the head line of a block. |
| 1244 | `            inside = line == "=== %s %s ===" % (binary, kernel)` | `inside` is true from the head line of the wanted binary and kernel on, and false from every other head line on. |
| 1245 | `        elif inside:` | For a line inside the wanted block: |
| 1246 | `            line = re.sub(r"^(\s*)([0-9a-f]+)(:\| <)", lambda m: "%s%0*x%s" % (m.group(1), len(m.group(2)), int(m.group(2), 16) + by, m.group(3)), line)` | Adds `by` to the address at the start of the line. The pattern matches optional spaces, a hex number and then a colon (an instruction line) or a space with `<` (the line with the function name). The new number gets the same number of digits. |
| 1247 | `            line = re.sub(r"\b([0-9a-f]+) <k_", lambda m: "%x <k_" % (int(m.group(1), 16) + by), line)` | Adds `by` to every branch target of the form hex number, space, `<k_`. So a branch inside the kernel still points to the same instruction. |
| 1248 | `        out.append(line)` | Adds the line to `out`. |
| 1249 | `    return "\n".join(out)` | Returns the lines as one text. |

### Synthetic listings of the new kernels: `synth`, `nop_body`, `synth_new` (lines 1252 to 1292)

| Line | Source | Explanation |
|---:|---|---|
| 1252 | `LDP8 = ["ldp\tq0, q1, [x0]", "ldp\tq2, q3, [x0, #32]", "ldp\tq4, q5, [x0, #64]", "ldp\tq6, q7, [x0, #96]",` | `LDP8`: the 8 load instructions of the `asmread` loop, written as `objdump` prints them, with a tab after the instruction name. Each `ldp` loads two 16-byte vector registers from the address in `x0` plus an offset. The first four cover the offsets 0 to 127. |
| 1253 | `        "ldp\tq8, q9, [x0, #128]", "ldp\tq10, q11, [x0, #160]", "ldp\tq12, q13, [x0, #192]", "ldp\tq14, q15, [x0, #224]"]` | Continues line 1252: the last four loads, for the offsets 128 to 255. Together the 8 instructions load 256 bytes. |
| 1254 | `SAVES = ["stp\td8, d9, [sp, #-64]!", "add\tx1, x0, x1, lsl #3", "stp\td10, d11, [sp, #16]", "stp\td12, d13, [sp, #32]",` | `SAVES`: the 5 instructions before the loop. Four `stp` instructions store the registers `d8` to `d15` on the stack. The second instruction, `add x1, x0, x1, lsl #3`, computes the end pointer: the start address plus 8 times the number of words. |
| 1255 | `         "stp\td14, d15, [sp, #48]"]` | Continues line 1254: the last of the four stores. |
| 1256 | `RESTORES = ["ldp\td10, d11, [sp, #16]", "ldp\td12, d13, [sp, #32]", "ldp\td14, d15, [sp, #48]", "ldp\td8, d9, [sp], #64"]` | `RESTORES`: the 4 `ldp` instructions after the loop. They load `d8` to `d15` back from the stack. |
| 1257 | `STEP = ["add\tx0, x0, #0x100", "cmp\tx0, x1"]` | `STEP`: the two instructions that end one loop pass before the branch. `add` moves the pointer `x0` forward by 0x100 bytes (256). `cmp` compares it with the end pointer `x1`. |
| 1260 | `def synth(kernel, start, head, body, tail=("ret",), binary="bwx11"):` | Starts the function `synth`. It writes the listing of one kernel as text, from lists of instructions. |
| 1261 | `    """(listing block, offsets row) of a kernel as build11.sh writes them on AArch64: head, loop body, the loop` | Description text: the result is the listing block and the offsets row of a kernel, in the form in which `build11.sh` writes them on AArch64. The parts are the head, the loop body, the loop ... |
| 1262 | `    branch, tail. The loop start is start + 4 * len(head)."""` | Description text: ... branch and the tail. The loop starts 4 bytes per head instruction after the start of the function. |
| 1263 | `    loop = start + 4 * len(head)` | `loop`: the address of the loop start. |
| 1264 | `    insns = list(head) + list(body) + ["b.cc\t%x <k_%s+0x%x>  // b.lo, b.ul, b.last" % (loop, kernel, loop - start)] + list(tail)` | `insns`: all instructions of the function: the head, the loop body, the loop branch and the tail. The loop branch is `b.cc` to the loop start, written as `objdump` writes it: the address, the function name with the offset in angle brackets, and a comment with other names of the same instruction. One of them is `b.lo`, the name that the source of the runner uses. |
| 1265 | `    text = "=== %s %s ===\n%016x <k_%s>:\n" % (binary, kernel, start, kernel)` | `text`: the block starts with the head line `=== binary kernel ===` and the line with the start address as 16 hex digits and the function name, `k_` plus the kernel name. |
| 1266 | `    text += "".join("    %x:\t%s\n" % (start + 4 * i, x) for i, x in enumerate(insns)) + "\n"` | Adds one line per instruction: 4 spaces, the address in hex, a colon, a tab and the instruction. The addresses rise by 4 bytes. An empty line ends the block. |
| 1267 | `    return text, "%s\t%s\tk_%s\t%x\t%x\t%d\n" % (binary, kernel, kernel, start, loop, loop % 64)` | Returns the block and the row for `offsets.tsv`: the binary, the kernel, the function name, the start address, the loop start and the loop start modulo 64, separated by tabs. |
| 1270 | `def nop_body(n):` | Starts the function `nop_body`. |
| 1271 | `    return LDP8 + ["nop"] * n + STEP` | Returns a loop body: the 8 loads, then `n` instructions `nop`, then the two instructions of `STEP`. |
| 1274 | `# Starts after the last kernel of the reference (read_1pl ends at 0x4df0), each at 0 modulo 64 as asmread.` | Comment: the three synthetic kernels start after the last kernel of the reference. The comment gives 0x4df0 as the end of `read_1pl` there. Each one starts at 0 modulo 64, as `asmread` does. |
| 1275 | `NOP_START = {"read_nop64": 0x4e00, "read_nop96": 0x4f80, "read_nop128": 0x5180}` | `NOP_START`: the start address of each synthetic kernel. All three are multiples of 64. With the 5 head instructions the loop starts 20 bytes later, at 20 modulo 64. |
| 1276 | `FULL = (SAVES, RESTORES + ["ret"])` | `FULL`: the complete head and the complete tail of a well-formed kernel: `SAVES` before the loop, and `RESTORES` plus `ret` after it. |
| 1279 | `def synth_new(change=None, by=0):` | Starts the function `synth_new`. It builds the listing text and the offsets rows of the three new kernels. |
| 1280 | `    """the 3 new kernels, well formed, at addresses after the last kernel of the reference. change: {kernel: (start,` | Description text: without arguments the three kernels are well formed and lie after the last kernel of the reference. `change` maps a kernel name to its own start ... |
| 1281 | `    head, body, tail)} replaces the parts of single kernels. by: added to every start. Returns (listing text,` | Description text: ... head, body and tail, and so replaces the parts of single kernels. `by` is added to every start address. The result is the listing text ... |
| 1282 | `    offsets rows)."""` | Description text: ... and the offsets rows. |
| 1283 | `    parts = {k: (NOP_START[k] + by, SAVES, nop_body(NOPS[k]), RESTORES + ["ret"]) for k in NOP_KERNELS}` | `parts`: for each new kernel: its start address plus `by`, the head `SAVES`, the loop body with the right number of `nop`, and the tail `RESTORES` plus `ret`. |
| 1284 | `    parts.update(change or {})` | Replaces the parts of single kernels by those of `change`, when it is given. |
| 1285 | `    text = offs = ""` | `text`, `offs`: the listing text and the offsets rows, both empty at the start. |
| 1286 | `    for k in NOP_KERNELS:` | Loops over the three new kernels. |
| 1287 | `        if parts[k] is not None:` | A kernel whose parts are `None` is left out. So a test can build a listing that lacks one kernel. |
| 1288 | `            t, o = synth(k, *parts[k])` | `t`, `o`: the block and the offsets row of the kernel, from `synth`. |
| 1289 | `            text, offs = text + t, offs + o` | Appends both to the results. |
| 1290 | `    return text, offs` | Returns the listing text and the offsets rows. |

### `test_listing_saved`: the listing check on a good listing (lines 1293 to 1324)

| Line | Source | Explanation |
|---:|---|---|
| 1293 | `def test_listing_saved():` | Starts the test `test_listing_saved`. The names of its checks start with `listing:`. |
| 1294 | `    """check_listing11.py on the accepted listing of bwx10 (ref-bwx10) plus synthetic new kernels, and on changed copies"""` | Description text: the test runs `check_listing11.py` on the accepted listing of `bwx10` (folder `ref-bwx10`) plus synthetic new kernels, and on changed copies. |
| 1295 | `    with open(os.path.join(REF10, "listing.txt")) as f:` | Opens `listing.txt` in the folder `REF10`. |
| 1296 | `        ref_listing = f.read()` | `ref_listing`: the machine-code listing of the accepted build of `bwx10`. |
| 1297 | `    with open(os.path.join(REF10, "offsets.tsv")) as f:` | Opens `offsets.tsv` in the folder `REF10`. |
| 1298 | `        ref_offs = f.read()` | `ref_offs`: the offsets table of that build. It has one row per kernel with the start address, the loop start and the loop start modulo 64. |
| 1299 | `    old_listing, old_offs = ref_listing.replace("=== %s " % B10, "=== bwx11 "), ref_offs.replace("\n%s\t" % B10, "\nbwx11\t")` | `old_listing`, `old_offs`: the same two texts with the binary name `bwx11` in place of `bwx10`. They represent a build of `bwx11` whose 26 older kernels are exactly the accepted ones. |
| 1300 | `    new_text, new_offs = synth_new()` | `new_text`, `new_offs`: the well-formed synthetic listing of the new kernels and its offsets rows, from `synth_new`. |
| 1301 | `    listing, offs = old_listing + new_text, old_offs + new_offs` | `listing`, `offs`: the complete good listing and the complete offsets table of this test. |
| 1302 | `    d = os.path.join(E.tmp, "listing")` | `d`: the folder `listing` in the temporary folder. |
| 1303 | `    os.makedirs(d, exist_ok=True)` | Creates it. No error when it exists. |
| 1305 | `    def case(name, want_rc, new_listing, new_offs=offs, want_text=None, extra=None):` | Starts the inner function `case`. It writes a listing and an offsets table to files, runs the listing check on them and checks the result. `want_rc` is the expected exit status. `want_text` is a text that the output must hold. `extra` holds added arguments. |
| 1306 | `        with open(os.path.join(d, "listing.txt"), "w") as f:` | Opens `listing.txt` in the folder `d` for writing. |
| 1307 | `            f.write(new_listing)` | Writes the listing of this case. |
| 1308 | `        with open(os.path.join(d, "offsets.tsv"), "w") as f:` | Opens `offsets.tsv` in the folder `d` for writing. |
| 1309 | `            f.write(new_offs)` | Writes the offsets table of this case. |
| 1310 | `        rc, out = run_listing([os.path.join(d, "listing.txt")] + (extra or []))` | Runs the listing check on the listing file. It finds the offsets table beside it. |
| 1311 | `        check("listing: " + name, rc == want_rc and (want_text is None or want_text in out), "rc=%d %s" % (rc, out[-400:]))` | Check: the exit status is the expected one, and the output holds the expected text when one is given. On a failure the status and the last 400 characters of the output are printed. |
| 1312 | `        return out` | Returns the output, for further checks. |
| 1314 | `    out = case("the accepted listing of bwx10 under the name bwx11 plus 3 well-formed new kernels passes (exit 0)", 0, listing)` | Case: the accepted listing of `bwx10` under the name `bwx11`, plus 3 well-formed new kernels, passes with exit status 0. This is the listing of a good build. |
| 1315 | `    check("listing: 26 kernels compared, 26 rows ok; 3 new kernels, 3 rows ok",` | Check: 26 kernels were compared and 26 rows are ok. 3 new kernels were checked and 3 rows are ok. |
| 1316 | `          out.count("\tsame\tok") == 26 and out.count("\texpected\tok") == 3 and` | Continues the check: 26 rows end with the columns `same` and `ok`. That is part 1 of the listing check: the text of a kernel equals the reference. 3 rows end with `expected` and `ok`. That is part 2: the loop of a new kernel is the expected one. |
| 1317 | `          "kernels=26 failed_rows=0 new_kernels=3 new_failed_rows=0" in out, out[-200:])` | Continues the check: the summary line holds `kernels=26 failed_rows=0 new_kernels=3 new_failed_rows=0`. |
| 1318 | `    check("listing: the synthetic new kernels have their loop at 20 modulo 64, as asmread",` | Check: the synthetic new kernels have their loop at 20 modulo 64, as `asmread` has. |
| 1319 | `          [r.split("\t")[5] for r in new_offs.splitlines()] == ["20"] * 3 and "bwx11\tasmread\tk_asmread\t42c0\t42d4\t20" in offs)` | Continues the check: the sixth column of each of the 3 synthetic offsets rows is `20`, and the offsets table holds the row of `asmread` with the start 42c0, the loop start 42d4 and the offset 20. |
| 1320 | `    check("listing: the synthetic new kernels hold 64, 96 and 128 nop",` | Check: the synthetic new kernels hold 64, 96 and 128 `nop`. |
| 1321 | `          [new_text.split("=== bwx11 %s ===" % k)[1].split("===")[0].count("\tnop\n") for k in NOP_KERNELS] == [64, 96, 128])` | Continues the check: it counts the `nop` lines in the block of each kernel. So the good input of the next cases really holds these numbers. |
| 1322 | `    out = case("the accepted listing of bwx10 under its own name, with --binary bwx10 and --skip-new, passes against itself", 0,` | Case: the accepted listing of `bwx10` under its own name, checked with `--binary bwx10` and `--skip-new`, passes against itself. |
| 1323 | `               ref_listing, ref_offs, want_text="kernels=26 failed_rows=0 new_kernels=NOT CHECKED", extra=["--binary", "bwx10", "--skip-new"])` | Continues the case: the listing and the offsets table of the reference, the expected text `kernels=26 failed_rows=0 new_kernels=NOT CHECKED`, and the two options. `--binary` names the binary whose blocks are checked. `--skip-new` leaves out part 2. |

### `test_listing_saved`: part 1 of the listing check must reject changed kernels (lines 1325 to 1397)

| Line | Source | Explanation |
|---:|---|---|
| 1325 | `    # ---- the checks of part 1 (check_listing8.py), on the 26 kernels of the reference ----` | Comment: the cases for part 1 of the listing check follow. They are the checks of `check_listing8.py`, now on the 26 kernels of the reference. |
| 1326 | `    one = "ldp\tq29, q28, [x0, #32]"` | `one`: one load instruction of the kernel `read`, as the listing prints it. A case below changes it. |
| 1327 | `    check("listing: the instruction to change stands once in k_read of bwx11",` | Check: the instruction to change stands once in `k_read` of `bwx11`. |
| 1328 | `          listing.split("=== bwx11 read ===")[1].split("===")[0].count(one) == 1)` | Continues the check: the count in the block of `read` is 1. So the change below changes exactly one place. |
| 1329 | `    head, rest = listing.split("=== bwx11 read ===")` | `head`, `rest`: the listing before and after the head line of the kernel `read`. |
| 1330 | `    case("one changed instruction in k_read fails (exit 1)", 1,` | Case: one changed instruction in the kernel `read` must fail with exit status 1. |
| 1331 | `         head + "=== bwx11 read ===" + rest.replace(one, "ldp\tq29, q28, [x0, #48]", 1), want_text="read\t41a0\t41a4\t36\t36\tDIFFERS\tFAIL")` | Continues the case: the offset of that load is 48 in place of 32. The output must hold the row of `read` with its loop offset 36 in both columns, the text column `DIFFERS` and the result `FAIL`. The place of the loop is unchanged. Only the comparison of the instructions finds this defect. |
| 1332 | `    check("listing: the loop start of k_asmread stands once", listing.count("    42d4:\tldp\tq0, q1, [x0]") == 1)` | Check: the first instruction of the loop of `k_asmread`, at the address 42d4, stands once in the listing. |
| 1333 | `    case("one added nop before the loop of k_asmread fails", 1,` | Case: one added `nop` before the loop of `k_asmread` must fail. |
| 1334 | `         listing.replace("    42d4:\tldp\tq0, q1, [x0]", "    42d0:\tnop\n    42d4:\tldp\tq0, q1, [x0]", 1), want_text="asmread")` | Continues the case: a line with a `nop` at the address 42d0 is put before the loop start. The output must name `asmread`. |
| 1335 | `    shifted = shift_block(listing, "bwx11", "asmread", 4)` | `shifted`: the listing with every address of `k_asmread` moved up by 4 bytes (line 1239). |
| 1336 | `    offs_shifted = offs.replace("bwx11\tasmread\tk_asmread\t42c0\t42d4\t20", "bwx11\tasmread\tk_asmread\t42c4\t42d8\t24")` | `offs_shifted`: the offsets table with the row of `asmread` moved in the same way: start 42c4, loop start 42d8, offset 24. |
| 1337 | `    check("listing: the shifted copy differs from the saved one", shifted != listing and offs_shifted != offs)` | Check: the shifted copy differs from the saved one. So the next cases test a changed input. |
| 1338 | `    out = case("k_asmread shifted by 4 bytes, same text, fails on the loop offset (exit 1)", 1, shifted, offs_shifted,` | Case: `k_asmread` shifted by 4 bytes, with the same text, must fail on the loop offset with exit status 1. |
| 1339 | `               want_text="asmread\t42c4\t42d8\t24\t20\tsame\tFAIL: loop offset modulo 64 is 24, reference 20")` | Continues the case: the expected row of `asmread`: start 42c4, loop start 42d8, loop offset 24 against 20 in the reference, the text column `same`, and the result `FAIL: loop offset modulo 64 is 24, reference 20`. The instructions are equal. Only the place of the loop inside a 64-byte block differs. The design asks to keep the loop offsets modulo 64. |
| 1340 | `    check("listing: with k_asmread shifted, every new kernel fails too: its loop offset is compared with asmread",` | Check: with `k_asmread` shifted, every new kernel fails too: its loop offset is compared with that of `asmread`. |
| 1341 | `          out.count("loop offset modulo 64 is 20, asmread has 24") == 3, out[-300:])` | Continues the check: the text `loop offset modulo 64 is 20, asmread has 24` stands 3 times in the output. |
| 1342 | `    case("the same shift with an offsets.tsv that still says 20 fails", 1, shifted, want_text="offsets.tsv gives 20")` | Case: the same shifted listing with an offsets table that still says 20 must fail. The output must hold `offsets.tsv gives 20`. So a table that was not updated cannot hide a moved loop. The check computes the loop offset from the listing. |
| 1343 | `    check("listing: the offsets row of k_oldread stands once", offs.count("bwx11\toldread\tk_oldread\t3e00\t3e68\t40") == 1)` | Check: the offsets row of `k_oldread` (start 3e00, loop start 3e68, offset 40) stands once in the table. |
| 1344 | `    case("an offsets.tsv row that differs from the listing fails", 1, listing,` | Case: an offsets row that differs from the listing must fail. |
| 1345 | `         offs.replace("bwx11\toldread\tk_oldread\t3e00\t3e68\t40", "bwx11\toldread\tk_oldread\t3e00\t3e68\t0"), want_text="offsets.tsv gives 0")` | Continues the case: the last column of the row of `oldread` is 0 in place of 40. The output must hold `offsets.tsv gives 0`. |
| 1346 | `    whole = listing` | `whole`: a copy of the listing, for the next case. |
| 1347 | `    for k in re.findall(r"=== bwx11 (\S+) ===", listing):` | Loops over the names of all kernels of `bwx11` in the listing. The pattern finds the kernel name in each head line. |
| 1348 | `        whole = shift_block(whole, "bwx11", k, 0x1040)` | Moves the block of the kernel up by 0x1040 bytes. That is 65 times 64. |
| 1349 | `    check("listing: the moved copy differs and holds 29 kernels", whole != listing and len(re.findall(r"=== bwx11 (\S+) ===", listing)) == 29)` | Check: the moved copy differs from the listing, and the listing holds 29 kernels. |
| 1350 | `    case("all kernels moved by a multiple of 64 bytes pass: addresses are not compared", 0, whole)` | Case: a listing in which all kernels are moved by a multiple of 64 bytes passes. The listing check does not compare addresses. It compares the instructions and the loop offset modulo 64, and such a move changes neither. |
| 1351 | `    block = listing.split("=== bwx11 read_sparse ===")[1].split("===")[0]` | `block`: the text of the block of the kernel `read_sparse`. |
| 1352 | `    case("a listing without k_read_sparse fails", 1, listing.replace("=== bwx11 read_sparse ===" + block, ""), want_text="no listing or no loop")` | Case: a listing without `k_read_sparse` must fail. The output must hold `no listing or no loop`. A build that lacks a kernel of the reference is not accepted. |
| 1353 | `    case("a listing with a kernel that the reference lacks and that is not a kernel of round 4 fails", 1,` | Case: a listing with a kernel that the reference does not have, and that is no kernel of round 4, must fail. |
| 1354 | `         listing + "\n=== bwx11 read_new ===\n" + block, want_text="read_new")` | Continues the case: a block with the kernel name `read_new` is added. The output must name `read_new`. |
| 1355 | `    # the kernels of round 3 are part of the reference now: part 1 compares them` | Comment: the kernels of round 3 are part of the reference now. So part 1 compares them. |
| 1356 | `    pf_block = listing.split("=== bwx11 read_pf512 ===")[1].split("===")[0]` | `pf_block`: the text of the block of `read_pf512`. |
| 1357 | `    case("a listing without k_read_pf512 (a kernel of round 3, now in the reference) fails", 1,` | Case: a listing without `k_read_pf512`, a kernel of round 3, must fail. |
| 1358 | `         listing.replace("=== bwx11 read_pf512 ===" + pf_block, ""), want_text="read_pf512\tNA\tNA\tNA\t20\t-\tFAIL: no listing or no loop")` | Continues the case: the expected row of `read_pf512` has `NA` in the three columns of the new listing, 20 as the loop offset of the reference, and the result `FAIL: no listing or no loop`. |
| 1359 | `    check("listing: the prfm to change stands once in k_read_pf512", pf_block.count("prfm\tpldl1keep, [x0, #576]") == 1)` | Check: the prefetch instruction to change, `prfm pldl1keep` with the offset 576, stands once in `k_read_pf512`. |
| 1360 | `    case("one changed prfm offset in k_read_pf512 fails", 1,` | Case: one changed prefetch offset in `k_read_pf512` must fail. |
| 1361 | `         listing.replace("=== bwx11 read_pf512 ===" + pf_block, "=== bwx11 read_pf512 ===" +` | Continues the case: the block of the kernel is replaced by a copy ... |
| 1362 | `                         pf_block.replace("prfm\tpldl1keep, [x0, #576]", "prfm\tpldl1keep, [x0, #584]")),` | Continues the case: ... in which the prefetch offset is 584 in place of 576. |
| 1363 | `         want_text="read_pf512\t4c40\t4c54\t20\t20\tDIFFERS\tFAIL")` | Continues the case: the expected row of `read_pf512`: loop offset 20 in both columns, the text column `DIFFERS` and the result `FAIL`. |
| 1364 | `    pl_block = listing.split("=== bwx11 read_1pl ===")[1].split("===")[0]` | `pl_block`: the text of the block of `read_1pl`. |
| 1365 | `    check("listing: the load to change stands once in k_read_1pl", pl_block.count("ldr\tq2, [x0, #128]") == 1)` | Check: the load to change, `ldr q2` with the offset 128, stands once in `k_read_1pl`. |
| 1366 | `    case("one changed load offset in k_read_1pl fails", 1,` | Case: one changed load offset in `k_read_1pl` must fail. |
| 1367 | `         listing.replace("=== bwx11 read_1pl ===" + pl_block, "=== bwx11 read_1pl ===" + pl_block.replace("ldr\tq2, [x0, #128]", "ldr\tq2, [x0, #136]")),` | Continues the case: the block is replaced by a copy in which the offset is 136 in place of 128. |
| 1368 | `         want_text="read_1pl\t4dd0\t4dd4\t20\t20\tDIFFERS\tFAIL")` | Continues the case: the expected row of `read_1pl`: the text column `DIFFERS` and the result `FAIL`. |
| 1369 | `    got = "ldr\tx3, [x3, #4072]"` | `got`: a load instruction of the old read kernel, as the listing prints it. With the `adrp` instruction before it, it loads a pointer from the table of global addresses of the binary, here at the offset 4072. The linker sets the place of a pointer in that table. |
| 1370 | `    check("listing: the pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got) == 2)` | Check: this pointer load stands exactly 2 times in the listing. The name of the check says that the two places are `k_oldread` and `k_oldread2`. The condition counts the whole listing and does not test the kernels. |
| 1371 | `    got0 = "ldr\tx0, [x0, #4072]"` | `got0`: the second pointer load of that kind, through the register `x0`. |
| 1372 | `    check("listing: the second pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got0) == 2)` | Check: it also stands 2 times in the listing. |
| 1373 | `    out = case("another place of the stack-guard pointer in the table of the linker, the same in all four loads, "` | Case: another place of the stack-guard pointer in the table of the linker, the same in all four loads, ... |
| 1374 | `               "passes with a note", 0, listing.replace(got, "ldr\tx3, [x3, #4064]").replace(got0, "ldr\tx0, [x0, #4064]"),` | Continues the case: ... passes with a note. All four loads get the offset 4064 in place of 4072. |
| 1375 | `               want_text="\tsame\tNOTE: got_offset_differs (4064,4064, reference 4072,4072)")` | Continues the case: the output must hold a row with the text column `same` and the result `NOTE: got_offset_differs (4064,4064, reference 4072,4072)`. The offset is set by the linker and is no part of the read loop. So the listing check accepts it, and it prints a note for a person to read. |
| 1376 | `    check("listing: the two rows with the note do not print a plain ok", out.count("\tsame\tok") == 24, out[-300:])` | Check: the two rows with the note do not print a plain `ok`. Only 24 rows end with `same` and `ok`. |
| 1377 | `    adrp, stub = "adrp\tx3, 2f000 <__FRAME_END__+0x1bbf8>", "bl\t2040 <__stack_chk_fail@plt>"` | `adrp`: the instruction that gives the page of the table. `stub`: the call of `__stack_chk_fail`, the function for a failed stack guard. |
| 1378 | `    check("listing: the adrp before that load and the call of the stack-guard failure stand in k_oldread and k_oldread2",` | Check: the `adrp` before that load and the call of the stack-guard failure stand in `k_oldread` and `k_oldread2`. |
| 1379 | `          listing.count(adrp) == 2 and listing.count(stub) == 2)` | Continues the check: each of the two texts stands 2 times in the listing. |
| 1380 | `    case("the first pointer load of k_oldread from another page of the table fails (exit 1)", 1,` | Case: the first pointer load of `k_oldread` from another page of the table must fail with exit status 1. |
| 1381 | `         listing.replace(adrp, "adrp\tx3, 2a000 <some_other_table>", 1), want_text="use 2 places of the table")` | Continues the case: the first `adrp` gets another page and another symbol name. The output must hold `use 2 places of the table`. A kernel that loads from a second place of the table loads another pointer than the reference does. |
| 1382 | `    case("the first pointer load of k_oldread from another offset fails", 1,` | Case: the first pointer load of `k_oldread` from another offset must fail. |
| 1383 | `         listing.replace(got, "ldr\tx3, [x3, #8]", 1), want_text="use 2 places of the table")` | Continues the case: the first load gets the offset 8. The output must hold `use 2 places of the table`. |
| 1384 | `    case("k_oldread2 with its two pointer loads from another place than k_oldread fails", 1,` | Case: `k_oldread2` with its two pointer loads from another place than `k_oldread` must fail. |
| 1385 | `         "=== bwx11 oldread2 ===".join([listing.split("=== bwx11 oldread2 ===")[0],` | Continues the case: the listing is cut at the head line of `oldread2` and joined again. The part before it stays as it is ... |
| 1386 | `                                        listing.split("=== bwx11 oldread2 ===")[1].replace("[x3, #4072]", "[x3, #16]", 1)` | Continues the case: ... and in the part after it the first load through `x3` gets the offset 16 ... |
| 1387 | `                                        .replace("[x0, #4072]", "[x0, #16]", 1)]),` | Continues the case: ... and the first load through `x0` gets the offset 16 too. |
| 1388 | `         want_text="over all kernels")` | Continues the case: the output must hold `over all kernels`. Each function alone uses one place of the table, but the two functions together use two. |
| 1389 | `    case("a call of another function in place of the stack-guard failure fails", 1,` | Case: a call of another function in place of the stack-guard failure must fail. |
| 1390 | `         listing.replace(stub, "bl\t9999 <abort@plt>", 1), want_text="DIFFERS")` | Continues the case: the first call of `__stack_chk_fail` becomes a call of `abort`. The output must hold `DIFFERS`. A target outside the function is compared by its symbol name. |
| 1391 | `    check("listing: the load from the stack to change stands in k_oldread and k_oldread2", listing.count("ldr\tx2, [sp, #136]") == 2)` | Check: the load from the stack to change, `ldr x2` with the offset 136, stands exactly 2 times in the listing. The name of the check says that the two places are `k_oldread` and `k_oldread2`. The condition counts the whole listing and does not test the kernels. |
| 1392 | `    case("another offset in a load from the stack fails", 1, listing.replace("ldr\tx2, [sp, #136]", "ldr\tx2, [sp, #128]", 1),` | Case: another offset in a load from the stack must fail. The first such load gets the offset 128. |
| 1393 | `         want_text="DIFFERS")` | Continues the case: the output must hold `DIFFERS`. |
| 1394 | `    case("a listing with no block of bwx11 cannot be used (exit 2)", 2, listing.replace("=== bwx11 ", "=== other "))` | Case: a listing with no block of `bwx11` cannot be used: exit status 2. Every head line gets the binary name `other`. |
| 1395 | `    case("a reference that holds a kernel of round 4 cannot be used (exit 2)", 2, listing, want_text="holds a kernel of round 4",` | Case: a reference that holds a kernel of round 4 cannot be used: exit status 2. The output must hold `holds a kernel of round 4`. |
| 1396 | `         extra=["--ref-listing", os.path.join(d, "listing.txt"), "--ref-offsets", os.path.join(d, "offsets.tsv"), "--ref-binary", "bwx11"])` | Continues the case: the test listing itself is given as the reference, with `--ref-listing`, `--ref-offsets` and `--ref-binary bwx11`. A listing with the new kernels is no listing of the reference binary, and the listing check says so. |

### `test_listing_saved`: part 2 of the listing check must reject a wrong new kernel (lines 1398 to 1472)

| Line | Source | Explanation |
|---:|---|---|
| 1398 | `    # ---- the 3 new kernels ----` | Comment: the cases for the 3 new kernels follow. They test part 2 of the listing check. |
| 1399 | `    def new_case(name, change, want_text, want_rc=1):` | Starts the inner function `new_case`. It runs one case on the accepted old kernels plus new kernels with a change. |
| 1400 | `        t, o = synth_new(change)` | `t`, `o`: the synthetic listing of the new kernels with the change, and its offsets rows. |
| 1401 | `        return case(name, want_rc, old_listing + t, old_offs + o, want_text=want_text)` | Runs the case and returns the output. The expected exit status is 1 unless the caller gives another one. |
| 1403 | `    a64, body64 = NOP_START["read_nop64"], nop_body(64)` | `a64`: the start address of the synthetic `read_nop64`. `body64`: its well-formed loop body with 64 `nop`. |
| 1404 | `    new_case("read_nop64 with 63 nop fails (exit 1)", {"read_nop64": (a64, FULL[0], nop_body(63), FULL[1])},` | Case: `read_nop64` with 63 `nop` must fail with exit status 1. |
| 1405 | `             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: the loop has 63 nop, expected 64")` | Continues the case: the expected row: start 4e00, loop start 4e14, loop offset 20 in both columns, the loop column `DIFFERS`, and the result `FAIL: the loop has 63 nop, expected 64`. The number of `nop` is what makes this kernel differ from `asmread`. A build with another number would be measured under a wrong name. |
| 1406 | `    new_case("read_nop64 with 65 nop fails", {"read_nop64": (a64, FULL[0], nop_body(65), FULL[1])},` | Case: `read_nop64` with 65 `nop` must fail. |
| 1407 | `             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: the loop has 65 nop, expected 64")` | Continues the case: the expected row, with the result `FAIL: the loop has 65 nop, expected 64`. |
| 1408 | `    new_case("read_nop96 with 97 nop fails", {"read_nop96": (NOP_START["read_nop96"], FULL[0], nop_body(97), FULL[1])},` | Case: `read_nop96` with 97 `nop` must fail. |
| 1409 | `             "read_nop96\t4f80\t4f94\t20\t20\tDIFFERS\tFAIL: the loop has 97 nop, expected 96")` | Continues the case: the expected row, with the result `FAIL: the loop has 97 nop, expected 96`. |
| 1410 | `    new_case("read_nop128 with the loop of read_nop96 fails", {"read_nop128": (NOP_START["read_nop128"], FULL[0], nop_body(96), FULL[1])},` | Case: `read_nop128` with the loop of `read_nop96` must fail. |
| 1411 | `             "read_nop128\t5180\t5194\t20\t20\tDIFFERS\tFAIL: the loop has 96 nop, expected 128")` | Continues the case: the expected row, with the result `FAIL: the loop has 96 nop, expected 128`. |
| 1412 | `    new_case("read_nop128 without any nop (the loop of asmread) fails", {"read_nop128": (NOP_START["read_nop128"], FULL[0], nop_body(0), FULL[1])},` | Case: `read_nop128` without any `nop`, which is the loop of `asmread`, must fail. |
| 1413 | `             "the loop has 0 nop, expected 128")` | Continues the case: the output must hold `the loop has 0 nop, expected 128`. |
| 1414 | `    new_case("read_nop64 with another instruction in place of one nop fails",` | Case: `read_nop64` with another instruction in place of one `nop` must fail. |
| 1415 | `             {"read_nop64": (a64, FULL[0], body64[:40] + ["mov\tx2, x2"] + body64[41:], FULL[1])},` | Continues the case: instruction 40 of the loop body is `mov x2, x2`. |
| 1416 | `             "loop instruction 40 is 'mov x2, x2', expected 'nop'")` | Continues the case: the output must hold `loop instruction 40 is 'mov x2, x2', expected 'nop'`. |
| 1417 | `    new_case("read_nop64 with one nop before the 8 ldp (64 nop in all) fails",` | Case: `read_nop64` with one `nop` before the 8 `ldp`, and 64 `nop` in all, must fail. |
| 1418 | `             {"read_nop64": (a64, FULL[0], ["nop"] + LDP8 + ["nop"] * 63 + STEP, FULL[1])},` | Continues the case: the body is one `nop`, the 8 loads, 63 `nop` and the two step instructions. |
| 1419 | `             "read_nop64\t4e00\t4e14\t20\t20\tDIFFERS\tFAIL: loop instruction 0 is 'nop', expected 'ldp q0, q1, [x0]'")` | Continues the case: the expected result says that loop instruction 0 is `nop` where the first `ldp` is expected. So the right count alone does not pass. The order of the instructions is checked too. |
| 1420 | `    new_case("read_nop64 with the nop after the add fails",` | Case: `read_nop64` with the `nop` after the `add` must fail. |
| 1421 | `             {"read_nop64": (a64, FULL[0], LDP8 + STEP[:1] + ["nop"] * 64 + STEP[1:], FULL[1])},` | Continues the case: the body is the 8 loads, the `add`, 64 `nop` and the `cmp`. |
| 1422 | `             "loop instruction 8 is 'add x0, x0, #0x100', expected 'nop'")` | Continues the case: the output must hold `loop instruction 8 is 'add x0, x0, #0x100', expected 'nop'`. |
| 1423 | `    new_case("read_nop64 with one wrong ldp offset (40 in place of 32) fails",` | Case: `read_nop64` with one wrong `ldp` offset, 40 in place of 32, must fail. |
| 1424 | `             {"read_nop64": (a64, FULL[0], [x.replace("[x0, #32]", "[x0, #40]") for x in body64], FULL[1])},` | Continues the case: the offset is replaced in the loop body. |
| 1425 | `             "loop instruction 1 is 'ldp q2, q3, [x0, #40]', expected 'ldp q2, q3, [x0, #32]'")` | Continues the case: the output must say that loop instruction 1 loads from the offset 40 where 32 is expected. A wrong offset means that the loop does not load each of its 256 bytes once. |
| 1426 | `    new_case("read_nop64 with 7 ldp fails", {"read_nop64": (a64 + 4, FULL[0], body64[:7] + body64[8:], FULL[1])},` | Case: `read_nop64` with 7 `ldp` must fail. The body lacks the eighth load, and the function starts 4 bytes later. |
| 1427 | `             "loop instruction 7 is 'nop', expected 'ldp q14, q15, [x0, #224]'")` | Continues the case: the output must say that loop instruction 7 is `nop` where the eighth `ldp` is expected. |
| 1428 | `    new_case("read_nop64 with a step of 128 bytes fails",` | Case: `read_nop64` with a step of 128 bytes must fail. |
| 1429 | `             {"read_nop64": (a64, FULL[0], [x.replace("#0x100", "#0x80") for x in body64], FULL[1])},` | Continues the case: the `add` of the loop body moves the pointer by 0x80 in place of 0x100. |
| 1430 | `             "loop instruction 72 is 'add x0, x0, #0x80', expected 'add x0, x0, #0x100'")` | Continues the case: the output must name loop instruction 72 with the step 0x80 where 0x100 is expected. The step must be the 256 bytes that one loop pass loads. |
| 1431 | `    new_case("read_nop64 with the loop moved by 4 bytes (offsets.tsv agrees with the listing) fails on the loop offset",` | Case: `read_nop64` with the loop moved by 4 bytes must fail on the loop offset. The offsets table agrees with the listing here. |
| 1432 | `             {"read_nop64": (a64 + 4, FULL[0], body64, FULL[1])},` | Continues the case: the kernel starts at `a64 + 4`, with its well-formed parts. |
| 1433 | `             "read_nop64\t4e04\t4e18\t24\t20\texpected\tFAIL: loop offset modulo 64 is 24, asmread has 20; loop offset modulo 64 is 24, planned 20")` | Continues the case: the expected row: start 4e04, loop start 4e18, loop offset 24 against 20 of `asmread`, the loop column `expected`, and a result with two problems: the offset differs from that of `asmread`, and it differs from the planned 20. The loop text is right. Only its place is wrong. |
| 1434 | `    new_case("read_nop96 that starts at 20 modulo 64 (loop at 40) fails on the loop offset",` | Case: `read_nop96` that starts at 20 modulo 64, with its loop at 40, must fail on the loop offset. |
| 1435 | `             {"read_nop96": (NOP_START["read_nop96"] + 20, FULL[0], nop_body(96), FULL[1])},` | Continues the case: the kernel starts 20 bytes after its planned start. |
| 1436 | `             "read_nop96\t4f94\t4fa8\t40\t20\texpected\tFAIL: loop offset modulo 64 is 40, asmread has 20")` | Continues the case: the expected row: start 4f94, loop start 4fa8, loop offset 40 against 20, and the result `FAIL: loop offset modulo 64 is 40, asmread has 20`. |
| 1437 | `    t, o = synth_new()` | `t`, `o`: the well-formed synthetic kernels and their offsets rows. |
| 1438 | `    case("a new kernel whose offsets.tsv row differs from the listing fails", 1, old_listing + t,` | Case: a new kernel whose offsets row differs from the listing must fail. |
| 1439 | `         old_offs + o.replace("bwx11\tread_nop128\tk_read_nop128\t5180\t5194\t20", "bwx11\tread_nop128\tk_read_nop128\t5180\t5194\t4"),` | Continues the case: the last column of the row of `read_nop128` is 4 in place of 20. |
| 1440 | `         want_text="read_nop128\t5180\t5194\t20\t20\texpected\tFAIL: offsets.tsv gives 4, the listing gives 20")` | Continues the case: the expected row ends with `FAIL: offsets.tsv gives 4, the listing gives 20`. |
| 1441 | `    # asmread and the new kernels all at 24: the new loops agree with asmread, and still miss the planned 20` | Comment: in the next case `asmread` and the new kernels all lie at 24. The new loops agree with `asmread`, and they still miss the planned 20. |
| 1442 | `    t, o = synth_new(by=4)` | `t`, `o`: the synthetic kernels with every start address 4 bytes higher. |
| 1443 | `    out = case("with k_asmread and the three new kernels all moved by 4 bytes, each new kernel fails on the planned offset 20", 1,` | Case: with `k_asmread` and the three new kernels all moved by 4 bytes, each new kernel must fail on the planned offset 20. |
| 1444 | `               shift_block(old_listing, "bwx11", "asmread", 4) + t,` | Continues the case: the listing with `k_asmread` moved by 4 bytes, plus the moved new kernels. |
| 1445 | `               old_offs.replace("bwx11\tasmread\tk_asmread\t42c0\t42d4\t20", "bwx11\tasmread\tk_asmread\t42c4\t42d8\t24") + o,` | Continues the case: the offsets table with the moved row of `asmread`, plus the rows of the moved new kernels. |
| 1446 | `               want_text="read_nop64\t4e04\t4e18\t24\t24\texpected\tFAIL: loop offset modulo 64 is 24, planned 20")` | Continues the case: the expected row of `read_nop64`: loop offset 24 in both columns, and the result `FAIL: loop offset modulo 64 is 24, planned 20`. |
| 1447 | `    check("listing: that run names the planned offset 3 times and never a difference from asmread",` | Check: that run names the planned offset 3 times and never a difference from `asmread`. |
| 1448 | `          out.count("loop offset modulo 64 is 24, planned 20") == 3 and "asmread has" not in out, out[-300:])` | Continues the check: the two conditions on the output. So the listing check compares the new loops with the fixed value 20, and not only with the place of `asmread` in the same build. |
| 1449 | `    new_case("read_nop64 without the store of d14 and d15 fails (the loop uses v14 and v15)",` | Case: `read_nop64` without the store of `d14` and `d15` must fail. The loop uses the vector registers `v14` and `v15`. |
| 1450 | `             {"read_nop64": (a64 + 4, SAVES[:4], body64, FULL[1])}, "not stored before the loop: [14, 15]")` | Continues the case: the head has only the first 4 instructions of `SAVES`. The output must hold `not stored before the loop: [14, 15]`. By the description of the listing check, a function must keep `d8` to `d15` for its caller. |
| 1451 | `    new_case("read_nop64 without the load of d8 and d9 after the loop fails",` | Case: `read_nop64` without the load of `d8` and `d9` after the loop must fail. |
| 1452 | `             {"read_nop64": (a64, FULL[0], body64, RESTORES[:3] + ["ret"])}, "not loaded after it: [8, 9]")` | Continues the case: the tail has only the first 3 instructions of `RESTORES`. The output must hold `not loaded after it: [8, 9]`. |
| 1453 | `    new_case("read_nop64 with a second backward branch fails",` | Case: `read_nop64` with a second backward branch must fail. |
| 1454 | `             {"read_nop64": (a64, FULL[0], body64, RESTORES + ["cbnz\tx2, 4e14 <k_read_nop64+0x14>", "ret"])},` | Continues the case: the tail gets a `cbnz` instruction that branches back to the loop start. |
| 1455 | `             "FAIL: 2 backward branches, 1 expected")` | Continues the case: the output must hold `FAIL: 2 backward branches, 1 expected`. |
| 1456 | `    new_case("read_nop64 with a call after the loop fails",` | Case: `read_nop64` with a call after the loop must fail. |
| 1457 | `             {"read_nop64": (a64, FULL[0], body64, RESTORES + ["bl\t2040 <abort@plt>", "ret"])}, "a branch or call beside the loop branch")` | Continues the case: the tail gets a call of `abort`. The output must hold `a branch or call beside the loop branch`. |
| 1458 | `    new_case("read_nop64 with another instruction before the loop fails",` | Case: `read_nop64` with another instruction before the loop must fail. |
| 1459 | `             {"read_nop64": (a64 - 4, SAVES + ["ldr\tq4, [x0, #4032]"], body64, FULL[1])},` | Continues the case: the head gets a load, `ldr q4`, as a sixth instruction, and the function starts 4 bytes earlier. |
| 1460 | `             "is not the end pointer and not a store of d registers")` | Continues the case: the output must hold `is not the end pointer and not a store of d registers`. |
| 1461 | `    new_case("read_nop64 that does not end with ret fails",` | Case: `read_nop64` that does not end with `ret` must fail. |
| 1462 | `             {"read_nop64": (a64, FULL[0], body64, RESTORES)}, "the function does not end with ret")` | Continues the case: the tail is `RESTORES` without `ret`. The output must hold `the function does not end with ret`. |
| 1463 | `    hi = old_listing + synth_new()[0].replace("b.cc\t4e14 <k_read_nop64+0x14>", "b.hi\t4e14 <k_read_nop64+0x14>")` | `hi`: the good listing in which the loop branch of `read_nop64` is `b.hi` in place of `b.cc`. |
| 1464 | `    check("listing: the loop branch to change stands once", synth_new()[0].count("b.cc\t4e14 <k_read_nop64+0x14>") == 1)` | Check: the loop branch to change stands once in the synthetic listing. |
| 1465 | `    case("read_nop64 with b.hi in place of b.cc as its loop branch fails", 1, hi, want_text="the loop branch is 'b.hi")` | Case: `read_nop64` with `b.hi` as its loop branch must fail. The output must hold `the loop branch is 'b.hi`. The source of the kernel asks for `b.lo`, another name of `b.cc`: the loop continues while the pointer is below the end pointer. |
| 1466 | `    new_case("a listing without read_nop96 fails", {"read_nop96": None}, "read_nop96\tNA\tNA\tNA\t20\t-\tFAIL: no listing")` | Case: a listing without `read_nop96` must fail. The expected row of `read_nop96` has `NA` in its three columns and the result `FAIL: no listing`. |
| 1467 | `    out = case("the accepted listing alone (no new kernel) fails: all 3 new kernels are required", 1, old_listing, old_offs)` | Case: the accepted listing alone, with no new kernel, must fail. All 3 new kernels are required. |
| 1468 | `    check("listing: that run names 3 failed new rows and no failed old row", "failed_rows=0 new_kernels=3 new_failed_rows=3" in out, out[-200:])` | Check: that run names 3 failed new rows and no failed old row. The summary line holds `failed_rows=0 new_kernels=3 new_failed_rows=3`. |
| 1469 | `    out = case("--skip-new: the same listing passes, and the last line says that the new kernels were not checked", 0,` | Case: with `--skip-new` the same listing passes, and the last line says that the new kernels were not checked. |
| 1470 | `               old_listing, old_offs, want_text="new_kernels=NOT CHECKED (--skip-new)", extra=["--skip-new"])` | Continues the case: the listing and the offsets table of the old kernels, the expected text `new_kernels=NOT CHECKED (--skip-new)` and the option. The summary line shows to a reader that part 2 did not run. |

### `test_build_scripts`: the build script stops when the marker file exists (lines 1473 to 1522)

| Line | Source | Explanation |
|---:|---|---|
| 1473 | `def test_build_scripts():` | Starts the test `test_build_scripts`. |
| 1474 | `    """build11.sh on this machine, and check_listing11.py on two real listings of one compiler"""` | Description text: the test runs `build11.sh` on this machine, and `check_listing11.py` on two real listings of one compiler. |
| 1475 | `    cpus = ",".join(str(c) for c in E.allowed)` | `cpus`: the CPUs that the test process may use, as a text with commas. The build script takes it as the CPU list of its own run. |
| 1476 | `    new, old = os.path.join(E.tmp, "new"), os.path.join(E.tmp, "old")` | `new`, `old`: two folders in the temporary folder. `new` is for a build of the runner under test. `old` is for the reference build. |
| 1477 | `    os.makedirs(new)` | Creates the folder `new`. |
| 1478 | `    os.makedirs(old)` | Creates the folder `old`. |
| 1479 | `    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):` | Loops over the three files that a build needs: the source, the self-test file and the build script. |
| 1480 | `        shutil.copy(os.path.join(HERE, name), new)` | Copies the file into the folder `new`. The build script writes only in its own folder. So the test runs a copy, and the folder of the sources stays unchanged. |
| 1481 | `    # The reference build of the listing comparison: build11.sh on the bwx10 source (bwx11.c without its marked` | Comment: the reference build of the listing comparison is `build11.sh` on the `bwx10` source. That source is `bwx11.c` without its marked ... |
| 1482 | `    # blocks), stored under the file name that the script compiles. Its listing has 26 kernels under the binary` | Comment: ... blocks. It is stored under the file name that the script compiles. Its listing has 26 kernels under the binary ... |
| 1483 | `    # name bwx11. The copy of bwx11_selftest.c is not compiled: the script only takes its digest.` | Comment: ... name `bwx11`. The copy of `bwx11_selftest.c` is not compiled. The script only takes its checksum. |
| 1484 | `    shutil.copy(os.path.join(E.src10, "bwx10.c"), os.path.join(old, "bwx11.c"))` | Copies the `bwx10` source into the folder `old` under the name `bwx11.c`. |
| 1485 | `    shutil.copy(os.path.join(E.src10, "bwx10_selftest.c"), old)` | Copies the self-test file of the `bwx10` source beside it. The source includes it. |
| 1486 | `    for name in ("bwx11_selftest.c", "build11.sh"):` | Loops over two more files: `bwx11_selftest.c` and `build11.sh`. |
| 1487 | `        shutil.copy(os.path.join(HERE, name), old)` | Copies the file into the folder `old`. |
| 1488 | `    marker = os.path.join(E.tmp, "marker")` | `marker`: the path of a test marker file in the temporary folder. |
| 1489 | `    open(marker, "w").close()` | Creates that file, empty. |
| 1490 | `    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=marker)` | `env`: the environment for the build script. `BWX_CPUS` holds the CPU list. `BWX_MARKER` holds the path of the test marker file. By the comment in the build script this variable exists only for a test of the marker check. |
| 1491 | `    env.pop("_PINNED", None)` | Removes the variable `_PINNED`, if it is set. The build script sets it when it starts itself again under `taskset`, the tool that sets the CPU list. Without the variable the script does that step. |
| 1492 | `    r = subprocess.run(["bash", os.path.join(new, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build11.sh` in the folder `new` while the test marker file exists. |
| 1493 | `    check("build11.sh: exit 3 and no file written while the marker file is present",` | Check: `build11.sh` ends with exit status 3 and writes no file while the marker file is present. |
| 1494 | `          r.returncode == 3 and sorted(os.listdir(new)) == ["build11.sh", "bwx11.c", "bwx11_selftest.c"], (r.returncode, os.listdir(new)))` | Continues the check: status 3, and the folder holds only the three copied files. On the test machine the marker file exists while another user runs a performance test. A build would use CPU time of the machine, so the script must stop before it compiles. |
| 1495 | `    # The marker file appears while the self-test runs. A script stands for the compiler. The "binary" that it` | Comment: in the next case the marker file appears while the self-test runs. A script replaces the compiler. The fake binary that ... |
| 1496 | `    # writes creates the marker file in its self-test and leaves a file if it is run in any other way.` | Comment: ... it writes creates the marker file in its self-test, and it leaves a file when it is run in any other way. |
| 1497 | `    late = os.path.join(E.tmp, "late")` | `late`: the folder `late` in the temporary folder. |
| 1498 | `    os.makedirs(late)` | Creates it. |
| 1499 | `    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):` | Loops over the three files of a build. |
| 1500 | `        shutil.copy(os.path.join(HERE, name), late)` | Copies the file into the folder `late`. |
| 1501 | `    late_marker, ran = os.path.join(E.tmp, "late-marker"), os.path.join(E.tmp, "late-ran")` | `late_marker`: the path of the marker file of this case. `ran`: the path of a file that shows that the fake binary ran again. |
| 1502 | `    cc = os.path.join(E.tmp, "fake-cc")` | `cc`: the path of the fake compiler, `fake-cc`. |
| 1503 | `    with open(cc, "w") as f:` | Opens it for writing. |
| 1504 | `        f.write('#!/bin/sh\n[ "$1" = --version ] && { echo fake; exit 0; }\n'` | Text of the fake compiler, a shell script. Its first line tells Linux to run it with `sh`. Its second line: when the first argument is `--version`, it prints `fake` and ends with exit status 0. |
| 1505 | `                'while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done\n'` | Text of the fake compiler: a loop over the arguments. When an argument is `-o`, the next one is kept in `out`. That is the path of the binary to write. |
| 1506 | `                'printf \'#!/bin/sh\\nif [ "$1" = --selftest ]; then : > "%s"; echo "# failures=0"; else : > "%s"; fi\\n\' > "$out"\n'` | Text of the fake compiler: it writes the fake binary to that path. The fake binary is a shell script too. Called with `--selftest`, it creates the marker file of this case and prints `# failures=0`, the last line of a passed self-test. Called in any other way, it creates the file `ran`. |
| 1507 | `                'chmod +x "$out"\n' % (late_marker, ran))` | Text of the fake compiler: it makes the fake binary executable. The end of the line puts the two paths into the text above. |
| 1508 | `    os.chmod(cc, 0o755)` | Makes the fake compiler executable (mode 755). |
| 1509 | `    r = subprocess.run(["bash", os.path.join(late, "build11.sh")], env=dict(env, BWX_MARKER=late_marker, CC=cc),` | Runs `build11.sh` in the folder `late`, with the marker path of this case and with the fake compiler in the variable `CC`. |
| 1510 | `                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Continues the call that runs the build script: both outputs are collected. |
| 1511 | `    check("build11.sh: exit 3 and no further run of the binary when the marker file appears during the self-test",` | Check: `build11.sh` ends with exit status 3 and does not run the binary again when the marker file appears during the self-test. |
| 1512 | `          r.returncode == 3 and os.path.exists(late_marker) and os.path.exists(os.path.join(late, "selftest-bwx11.txt")) and` | Continues the check: status 3, the marker file of this case exists, and the file `selftest-bwx11.txt` exists, so the self-test ran ... |
| 1513 | `          not os.path.exists(ran), (r.returncode, os.path.exists(late_marker), os.path.exists(ran), r.stderr[-200:]))` | Continues the check: ... and the file `ran` does not exist. So the script tested the marker file again after the self-test, and it did not start the binary again. Its next step would have run the binary to list the kernels. |
| 1514 | `    env["BWX_MARKER"] = marker + ".none"` | Sets `BWX_MARKER` to a path that does not exist. No marker file is present for the next runs. |
| 1515 | `    r = subprocess.run(["bash", os.path.join(new, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build11.sh` in the folder `new`. This is a full build on this machine. |
| 1516 | `                       universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1517 | `    made = sorted(os.listdir(new))` | `made`: the sorted names of the files in the folder `new` after the run. |
| 1518 | `    check("build11.sh: exit 0; writes bwx11, build.txt, listing.txt, offsets.tsv, selftest-bwx11.txt, seq-listing.txt",` | Check: `build11.sh` ends with exit status 0 and writes `bwx11`, `build.txt`, `listing.txt`, `offsets.tsv`, `selftest-bwx11.txt` and `seq-listing.txt`. |
| 1519 | `          r.returncode == 0 and made == sorted(["build11.sh", "bwx11.c", "bwx11_selftest.c", "bwx11", "build.txt", "listing.txt",` | Continues the check: status 0, and the folder holds exactly the three copied files plus the binary, the build record, the listing ... |
| 1520 | `                                                "offsets.tsv", "selftest-bwx11.txt", "seq-listing.txt"]), (r.returncode, made, r.stderr[-300:]))` | Continues the check: ... the offsets table, the self-test output and the listing of the timed functions. On a failure the status, the file names and the end of the error output are printed. |
| 1521 | `    if r.returncode != 0:` | Tests whether the build failed. |
| 1522 | `        return` | Ends the test in that case. The next checks read the files of the build. |

### `test_build_scripts`: the build record, and a build that the script must reject (lines 1523 to 1568)

| Line | Source | Explanation |
|---:|---|---|
| 1523 | `    with open(os.path.join(new, "build.txt")) as f:` | Opens `build.txt` in the folder `new`. |
| 1524 | `        build = f.read()` | `build`: the whole build record. |
| 1525 | `    with open(os.path.join(OLD, "build.sh")) as f:` | Opens `build.sh`, the build script of the first runner. |
| 1526 | `        old_flags = re.search(r'^CFLAGS="(.*)"$', f.read(), re.M).group(1)` | `old_flags`: the compiler flags of that script. The pattern takes the text between the double quotes of the line that starts with `CFLAGS=`. |
| 1527 | `    check("build11.sh: build.txt holds the CFLAGS of build.sh, no compiler message, the self-test result and 7 digests",` | Check: `build.txt` holds the `CFLAGS` of `build.sh`, no compiler message, the self-test result and 7 checksums. |
| 1528 | `          "## CFLAGS=%s\n" % old_flags in build and "## compiler messages:\n## compiler messages end\n" in build and` | Continues the check: the record holds a line `## CFLAGS=` with exactly these flags, and the line `## compiler messages:` is followed directly by the line `## compiler messages end`. So the build used the flags of the first runner, and the compiler gave no warning. |
| 1529 | `          "## selftest bwx11 exit=0 # failures=0" in build and len(re.findall(r"^[0-9a-f]{64}  ", build, re.M)) == 7, build[-600:])` | Continues the check: the record holds `## selftest bwx11 exit=0 # failures=0`, and 7 lines start with a sha256 (64 hex digits and two spaces). With these checksums a later result can name the exact sources, binary and listings. |
| 1530 | `    for fn in SEQ_FUNCTIONS:` | Loops over the two timed functions. |
| 1531 | `        t = seq_targets(os.path.join(new, "bwx11"), fn)` | `t`: the branch targets of the function in the binary that the script built (line 315). |
| 1532 | `        check("build11.sh: build.txt lists the branch targets of %s, as the machine-code rule reads them" % fn,` | Check: `build.txt` lists the branch targets of the function, as the machine-code rule reads them. |
| 1533 | `              "## %s branch targets: %s\n" % (fn, " ".join("%s=%d" % (k, t[k]) for k in sorted(t))) in build and` | Continues the check: the record holds a line with the function name, the words `branch targets:` and every target with its count in the form `name=count`, sorted by name ... |
| 1534 | `              not seq_code_problems(t, fn), re.findall(r"^## timed_sequence.*$", build, re.M))` | Continues the check: ... and these targets pass the machine-code rule. So the build script and the test read the same targets from the machine code. On a failure the lines of the record about the timed functions are printed. |
| 1535 | `    check("build11.sh: build.txt holds the placement of bwx11, and says that the accepted binary was not found beside it",` | Check: `build.txt` holds the placement of `bwx11`, and it says that the accepted binary was not found beside it. |
| 1536 | `          re.search(r"^## placement bwx11 \(start modulo 64\): call=\d+ read_smaps=\d+ tcount=\d+ timed_sequence=\d+ "` | Continues the check: a line `## placement bwx11 (start modulo 64):` with a number for each of `call`, `read_smaps`, `tcount`, `timed_sequence` ... |
| 1537 | `                    r"timed_sequence_hot=\d+$", build, re.M) and "## placement against bwx8: not compared (no file " in build,` | Continues the check: ... and `timed_sequence_hot`, and a line that holds `## placement against bwx8: not compared (no file`. The second line shows that a comparison that could not be made is written down. |
| 1538 | `          re.findall(r"^## placement.*$", build, re.M))` | Continues the check: the placement lines of the record as the detail. |
| 1539 | `    check("build11.sh: build.txt also says that the accepted binary of bwx10 was not found beside it",` | Check: `build.txt` also says that the accepted binary of `bwx10` was not found beside it. |
| 1540 | `          "## placement against bwx10: not compared (no file " in build and len(re.findall(r"^## placement.*$", build, re.M)) == 3,` | Continues the check: the record holds `## placement against bwx10: not compared (no file`, and it has exactly 3 placement lines. |
| 1541 | `          re.findall(r"^## placement.*$", build, re.M))` | Continues the check: the placement lines of the record as the detail. |
| 1542 | `    with open(os.path.join(new, "seq-listing.txt")) as f:` | Opens `seq-listing.txt` in the folder `new`. |
| 1543 | `        seq_text = f.read()` | `seq_text`: its whole text. |
| 1544 | `    check("build11.sh: seq-listing.txt holds the machine code of both timed functions",` | Check: `seq-listing.txt` holds the machine code of both timed functions. |
| 1545 | `          re.findall(r"^=== bwx11 (\S+) ===$", seq_text, re.M) == list(SEQ_FUNCTIONS) and` | Continues the check: the head lines `=== bwx11 <function> ===` name exactly the two timed functions, in order ... |
| 1546 | `          all("<%s>:" % fn in seq_text for fn in SEQ_FUNCTIONS) and len(seq_text.splitlines()) > 60, seq_text[:200])` | Continues the check: ... the label of each function is in the text, and the text has more than 60 lines. |
| 1547 | `    seq = os.path.join(E.tmp, "seq")` | `seq`: the folder `seq` in the temporary folder. |
| 1548 | `    os.makedirs(seq)` | Creates it. |
| 1549 | `    for name in ("bwx11_selftest.c", "build11.sh"):` | Loops over the self-test file and the build script. |
| 1550 | `        shutil.copy(os.path.join(HERE, name), seq)` | Copies the file into the folder `seq`. |
| 1551 | `    with open(os.path.join(seq, "bwx11.c"), "w") as f:` | Opens `bwx11.c` in that folder for writing. |
| 1552 | `        f.write(mutant_source(SEQ_MUTANTS[1]) or "")` | Writes the source with the second defect of `SEQ_MUTANTS`: a page read and an output flush before the first target window. Without that source the file is empty. |
| 1553 | `    r6 = subprocess.run(["bash", os.path.join(seq, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build11.sh` in the folder `seq`. |
| 1554 | `                        universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1555 | `    check("build11.sh: exit 6 for a build with " + SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and` | Check: `build11.sh` ends with exit status 6 for a build with that defect. The error output names `read_vmstat` ... |
| 1556 | `          "fflush" in r6.stderr and "timed_sequence of bwx11:" in r6.stderr and "timed_sequence_hot of" not in r6.stderr,` | Continues the check: ... and `fflush`, the two added calls. It holds `timed_sequence of bwx11:` and does not hold `timed_sequence_hot of`. Exit status 6 of the build script means that a timed sequence reaches a function that is not allowed there. So a build with such a call is rejected when it is built, before any measurement. |
| 1557 | `          (r6.returncode, r6.stderr[-300:]))` | Continues the check: the status and the end of the error output as the detail. |
| 1558 | `    seqh = os.path.join(E.tmp, "seqh")` | `seqh`: the folder `seqh` in the temporary folder. |
| 1559 | `    os.makedirs(seqh)` | Creates it. |
| 1560 | `    for name in ("bwx11_selftest.c", "build11.sh"):` | Loops over the self-test file and the build script. |
| 1561 | `        shutil.copy(os.path.join(HERE, name), seqh)` | Copies the file into the folder `seqh`. |
| 1562 | `    with open(os.path.join(seqh, "bwx11.c"), "w") as f:` | Opens `bwx11.c` in that folder for writing. |
| 1563 | `        f.write(mutant_source(HOT_SEQ_MUTANTS[1]) or "")` | Writes the source with the same defect in `timed_sequence_hot` (line 439). |
| 1564 | `    r6 = subprocess.run(["bash", os.path.join(seqh, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build11.sh` in the folder `seqh`. |
| 1565 | `                        universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1566 | `    check("build11.sh: exit 6 for a build with " + HOT_SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and` | Check: `build11.sh` ends with exit status 6 for that build too. The error output names `read_vmstat` ... |
| 1567 | `          "fflush" in r6.stderr and "timed_sequence_hot of bwx11:" in r6.stderr and "timed_sequence of" not in r6.stderr,` | Continues the check: ... and `fflush`. It holds `timed_sequence_hot of bwx11:` and does not hold `timed_sequence of`. So the script checks both timed functions and names the right one. |
| 1568 | `          (r6.returncode, r6.stderr[-300:]))` | Continues the check: the status and the end of the error output as the detail. |

### `test_build_scripts`: real listings, a moved kernel, and the placement record (lines 1569 to 1631)

| Line | Source | Explanation |
|---:|---|---|
| 1569 | `    with open(os.path.join(new, "offsets.tsv")) as f:` | Opens `offsets.tsv` of the full build in the folder `new`. |
| 1570 | `        rows = [line.split("\t") for line in f.read().splitlines()[1:]]` | `rows`: its rows without the header line, each split at the tabs. |
| 1571 | `    check("build11.sh: offsets.tsv has one row per kernel of binary bwx11, each with a loop",` | Check: `offsets.tsv` has one row per kernel of the binary `bwx11`, each with a loop. |
| 1572 | `          len(rows) == 29 and [r[1] for r in rows[21:26]] == NEW_KERNELS and [r[1] for r in rows[26:]] == NOP_KERNELS and` | Continues the check: 29 rows. The rows 22 to 26 are the kernels of `NEW_KERNELS`, and the last three are those of `NOP_KERNELS` ... |
| 1573 | `          all(r[0] == "bwx11" and r[5].isdigit() for r in rows), rows[:3])` | Continues the check: ... every row names the binary `bwx11`, and its loop offset is a number. A number shows that the script found a backward branch, and so a loop, in the function. |
| 1574 | `    r = subprocess.run(["bash", os.path.join(old, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build11.sh` in the folder `old`, on the `bwx10` source. |
| 1575 | `    with open(os.path.join(old, "offsets.tsv")) as f:` | Opens `offsets.tsv` of that build. |
| 1576 | `        ref_rows = [line.split("\t") for line in f.read().splitlines()[1:]]` | `ref_rows`: its rows without the header line. |
| 1577 | `    if not check("build11.sh on the bwx10 source runs in a temporary copy and lists 26 kernels (the reference for the next check)",` | Check: `build11.sh` on the `bwx10` source runs in a temporary copy and lists 26 kernels. This build is the reference for the next check. |
| 1578 | `                 r.returncode == 0 and len(ref_rows) == 26 and [x[1] for x in ref_rows] == [x[1] for x in rows[:26]], r.stderr[-300:]):` | Continues the check: status 0, 26 rows, and the same kernel names in the same order as the first 26 rows of the full build. |
| 1579 | `        return` | Ends the test when the check before it failed. |
| 1580 | `    ref = ["--ref-listing", os.path.join(old, "listing.txt"), "--ref-offsets", os.path.join(old, "offsets.tsv"),` | `ref`: the arguments that make the listing check use the build in the folder `old` as its reference: its listing, its offsets table ... |
| 1581 | `           "--ref-binary", "bwx11"]` | Continues line 1580: ... and `bwx11` as the binary name in that reference. |
| 1582 | `    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref + ["--skip-new"])` | Runs the listing check on the listing of the full build against that reference, with `--skip-new`. |
| 1583 | `    check("listing: on this machine the 26 kernels of bwx10 in bwx11 equal the kernels of a build of the bwx10 source, text and "` | Check: on this machine the 26 kernels of `bwx10` in `bwx11` equal the kernels of a build of the `bwx10` source, in text and ... |
| 1584 | `          "loop offset (--skip-new: the new kernels are stand-in loops here)",` | Continues the name of the check: ... in loop offset. It adds that `--skip-new` is used: the new kernels are stand-in loops on this machine. |
| 1585 | `          rc == 0 and out.count("\tsame\tok") == 26 and "new_kernels=NOT CHECKED" in out, out[-400:])` | Continues the check: exit status 0, 26 rows that end with `same` and `ok`, and the text `new_kernels=NOT CHECKED`. This runs the whole chain of build script, listing and listing check on real compiler output. It shows for the local compiler that the additions of round 4 change no instruction and no loop offset of an older kernel. |
| 1586 | `    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref)` | Runs the listing check on the listing of the full build against that reference. |
| 1587 | `    check("listing: without --skip-new the stand-in loops of the new kernels are rejected (exit 1), and the 26 old rows stay ok",` | Check: without `--skip-new` the stand-in loops of the new kernels are rejected with exit status 1, and the 26 old rows stay ok. |
| 1588 | `          rc == 1 and out.count("\tsame\tok") == 26 and "failed_rows=0 new_kernels=3 new_failed_rows=3" in out, out[-400:])` | Continues the check: status 1, 26 rows `same` and `ok`, and the summary `failed_rows=0 new_kernels=3 new_failed_rows=3`. A stand-in loop holds no `ldp` and no `nop` of the planned loop. So part 2 of the listing check is shown to reject real code that is not the planned loop. |
| 1589 | `    # a bwx11 build whose kernel was moved must be rejected` | Comment: a build of `bwx11` in which a kernel was moved must be rejected. |
| 1590 | `    moved = os.path.join(E.tmp, "moved")` | `moved`: the folder `moved` in the temporary folder. |
| 1591 | `    os.makedirs(moved)` | Creates it. |
| 1592 | `    for name in ("bwx11.c", "bwx11_selftest.c", "build11.sh"):` | Loops over the three files of a build. |
| 1593 | `        shutil.copy(os.path.join(HERE, name), moved)` | Copies the file into the folder `moved`. |
| 1594 | `    with open(os.path.join(moved, "bwx11.c")) as f:` | Opens `bwx11.c` in that folder. |
| 1595 | `        src = f.read()` | `src`: the source text of the runner. |
| 1596 | `    with open(os.path.join(moved, "bwx11.c"), "w") as f:` | Opens the same file for writing. |
| 1597 | `        f.write(src.replace("#define PAD_asmread 0\n", "#define PAD_asmread 16\n"))` | Writes the source with `PAD_asmread` set to 16 in place of 0. The pad before `k_asmread` then is 16 bytes longer. So the kernel and its loop start 16 bytes later. |
| 1598 | `    r = subprocess.run(["bash", os.path.join(moved, "build11.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build11.sh` in the folder `moved`. The check of this build follows in lines 1627 to 1629. |
| 1599 | `    # the placement record against the accepted binary: a copy with the local pad, and a copy with another pad` | Comment: the placement record against the accepted binary is tested with two copies: one with the local pad and one with another pad. |
| 1600 | `    if getattr(E, "call8", None) is None:` | Tests whether `E.call8` is missing. The test `test_source` sets it when its placement check works. |
| 1601 | `        check("build11.sh: placement record against the accepted binary (NOT RUN: the placement check of the source test failed)", False)` | Records a failed check with `NOT RUN` in its name: the placement record against the accepted binary cannot be tested. |
| 1602 | `    elif getattr(E, "bin10_placed", None) is None or not os.path.exists(E.bin10_placed):` | If not: tests whether the `bwx10` build with the local pad is missing. |
| 1603 | `        check("build11.sh: placement record against bwx10 (NOT RUN: the bwx10 source did not build with the local pad)", False)` | Records a failed check with `NOT RUN` in its name: the placement record against `bwx10` cannot be tested. |
| 1604 | `    else:` | In every other case the placement record is tested. |
| 1605 | `        for tag, pad in (("local", E.call8), ("other", (E.call8 + 4) % 64)):` | Loops over two cases: `local` with the pad of the local build of the accepted runner, and `other` with a pad 4 bytes larger. |
| 1606 | `            d = os.path.join(E.tmp, "placed-" + tag)` | `d`: the folder `placed-` plus the name of the case in the temporary folder. |
| 1607 | `            os.makedirs(d)` | Creates it. |
| 1608 | `            for name in ("bwx11_selftest.c", "build11.sh"):` | Loops over the self-test file and the build script. |
| 1609 | `                shutil.copy(os.path.join(HERE, name), d)` | Copies the file into that folder. |
| 1610 | `            with open(os.path.join(d, "bwx11.c"), "w") as f:` | Opens `bwx11.c` in that folder for writing. |
| 1611 | `                f.write(src.replace("#define PAD_after_kernels 24\n", "#define PAD_after_kernels %d\n" % pad))` | Writes the source with `PAD_after_kernels` set to the pad of this case in place of 24. |
| 1612 | `            rp = subprocess.run(["bash", os.path.join(d, "build11.sh")], env=dict(env, BWX8_BIN=E.bin8, BWX10_BIN=E.bin10_placed),` | Runs `build11.sh` in that folder. `BWX8_BIN` gives it the local build of the accepted runner. `BWX10_BIN` gives it the `bwx10` build with the local pad. By the comment in the build script it reads these two binaries with `nm` only and does not run them. |
| 1613 | `                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)` | Continues the call of line 1612: the outputs are collected as text. |
| 1614 | `            lines = []` | `lines`: the placement lines of the build record, empty at the start. |
| 1615 | `            if os.path.exists(os.path.join(d, "build.txt")):` | Tests whether the build wrote a build record. |
| 1616 | `                with open(os.path.join(d, "build.txt")) as f:` | Opens it. |
| 1617 | `                    lines = re.findall(r"^## placement.*$", f.read(), re.M)` | `lines`: the lines of the record that start with `## placement`. |
| 1618 | `            want = "same" if tag == "local" else "DIFFERS"` | `want`: the word that the record must hold: `same` for the local pad and `DIFFERS` for the other pad. |
| 1619 | `            check("build11.sh: with the accepted binary given and the %s pad, build.txt holds both placements and the word %s" % (tag, want),` | Check: with the accepted binary given and the pad of this case, `build.txt` holds both placements and the expected word. |
| 1620 | `                  rp.returncode == 0 and len(lines) == 5 and lines[0].startswith("## placement bwx11 (start modulo 64): call=%d " % pad) and` | Continues the check: status 0, 5 placement lines, and the first one gives `call` of `bwx11` at the pad of this case ... |
| 1621 | `                  lines[1].startswith("## placement bwx8 (start modulo 64): call=%d " % E.call8) and` | Continues the check: ... the second one gives `call` of `bwx8` at `E.call8` ... |
| 1622 | `                  lines[2] == "## placement up to timed_sequence against bwx8: " + want, (rp.returncode, lines))` | Continues the check: ... and the third one is `## placement up to timed_sequence against bwx8:` with the expected word. Both words are produced in the two cases. So the script is shown to detect a timed path that was moved by 4 bytes. |
| 1623 | `            check("build11.sh: with a bwx10 binary given and the %s pad, build.txt holds its placement and the word %s" % (tag, want),` | Check: with a `bwx10` binary given and the pad of this case, `build.txt` holds its placement and the expected word. |
| 1624 | `                  len(lines) == 5 and lines[3].startswith("## placement bwx10 (start modulo 64): call=%d " % E.call8) and` | Continues the check: 5 lines, and the fourth one gives `call` of `bwx10` at `E.call8` ... |
| 1625 | `                  "timed_sequence_hot=" in lines[3] and` | Continues the check: ... and names `timed_sequence_hot` ... |
| 1626 | `                  lines[4] == "## placement up to timed_sequence_hot against bwx10: " + want, lines)` | Continues the check: ... and the fifth one is `## placement up to timed_sequence_hot against bwx10:` with the expected word. |
| 1627 | `    rc, out = run_listing([os.path.join(moved, "listing.txt")] + ref + ["--skip-new"])` | Runs the listing check on the listing of the build with the moved kernel, against the reference, with `--skip-new`. |
| 1628 | `    check("listing: a real bwx11 build with k_asmread moved by 16 bytes is rejected (exit 1)",` | Check: a real build of `bwx11` with `k_asmread` moved by 16 bytes is rejected with exit status 1. |
| 1629 | `          r.returncode == 0 and rc == 1 and "loop offset modulo 64" in out, (r.returncode, rc, out[-300:]))` | Continues the check: the build itself worked with exit status 0, the listing check ended with exit status 1, and its output holds `loop offset modulo 64`. So a kernel that a build moved is rejected on real compiler output, also when its instructions are unchanged. |

### `structure`, `m_of` and `accounting_problems`: comparing two runs (lines 1632 to 1682)

| Line | Source | Explanation |
|---:|---|---|
| 1632 | `def structure(out, drop_m=()):` | Starts the function `structure`. It reduces the output of a run to the parts that must be equal in two runs of the same plan. `drop_m` names `M` keys to leave out. |
| 1633 | `    """The rows of a run without what differs between two runs of one plan: times, byte counts, counter values` | Description text: the result holds the rows without what differs between two runs of one plan: times, byte counts, counter values ... |
| 1634 | `    and addresses. Comment lines byte for byte. M rows with their values, apart from the addresses and an evict_ns` | Description text: ... and addresses. Comment lines are kept byte for byte. `M` rows keep their values, apart from the addresses and an `evict_ns` ... |
| 1635 | `    above 0. S rows whole.` | Description text: ... above 0. `S` rows are kept whole. |
| 1636 | `    W rows: trial, phase, widx, kernel, pass_bytes. P rows: trial, when, kB_total. E rows: trial, field count,` | Description text: of a `W` row the trial, the phase, the window number, the kernel and the pass bytes are kept. Of a `P` row the trial, the word `pre` or `post` and the size in kB. Of an `E` row the trial, the number of fields ... |
| 1637 | `    sink_ok, count_state. B rows: one entry per window that has bins. Other rows: type and field count."""` | Description text: ... `sink_ok` and the count state. The `B` rows give one entry per window that has bins. Of every other row the type and the number of fields are kept. |
| 1638 | `    s = []` | `s`: the list of the kept items, empty at the start. |
| 1639 | `    for line in out.splitlines():` | Loops over the lines of the output. |
| 1640 | `        f = line.split(",")` | Splits the line at the commas. |
| 1641 | `        if line.startswith("#"):` | A comment line, which starts with `#`: |
| 1642 | `            item = line` | is kept whole. |
| 1643 | `        elif f[0] == "M":` | An `M` row: |
| 1644 | `            if f[1] in drop_m:` | Tests whether its key is one of the keys to leave out. |
| 1645 | `                continue` | Skips the row in that case. |
| 1646 | `            item = ("M", f[1], None if f[1] in ADDR_KEYS or (f[1] == "evict_ns" and f[2] != "0") else ",".join(f[2:]))` | Keeps the key and the value. The value is replaced by `None` for the five address keys, and for `evict_ns` when it is not `0`. The duration of the evict step differs from run to run. |
| 1647 | `        elif f[0] == "S":` | An `S` row: |
| 1648 | `            item = tuple(f)` | is kept with all its fields. |
| 1649 | `        elif f[0] == "W":` | A `W` row: |
| 1650 | `            item = tuple(f[:6]) + (len(f),)` | Keeps its first 6 fields (the row type, the trial, the phase, the window number, the kernel and the pass bytes) and its number of fields. The bytes and the two times are left out. |
| 1651 | `        elif f[0] == "P":` | A `P` row: |
| 1652 | `            item = tuple(f[:4]) + (len(f),)` | Keeps its first 4 fields (the row type, the trial, `pre` or `post`, and the size in kB) and its number of fields. |
| 1653 | `        elif f[0] == "E":` | An `E` row: |
| 1654 | `            item = ("E", f[1], len(f), f[8], f[9])` | Keeps the trial, the number of fields, `sink_ok` (field 8) and the count state (field 9). |
| 1655 | `        elif f[0] == "B":` | A `B` row: |
| 1656 | `            item = ("B", f[1], f[2], len(f))` | Keeps the trial, the window number and the number of fields. |
| 1657 | `            if s and s[-1] == item:` | Tests whether the item before is the same item. That is the case for the second and every later bin of a window. |
| 1658 | `                continue` | Skips it. So each window with bins gives one item, however many bins the run made. |
| 1659 | `        elif f[0] == "K":` | A `K` row: |
| 1660 | `            item = ("K", f[1], len(f))` | Keeps the kernel name and the number of fields. The address is left out. |
| 1661 | `        else:` | Every other row: |
| 1662 | `            item = (f[0], len(f))` | Keeps the row type and the number of fields. |
| 1663 | `        s.append(item)` | Adds the item to the list. |
| 1664 | `    return s` | Returns the list. |
| 1667 | `def m_of(out):` | Starts the function `m_of`. |
| 1668 | `    return {f[1]: f[2] for f in rows_of(out).get("M", [])}` | Returns the `M` rows of an output as a dictionary from key to value. |
| 1671 | `def accounting_problems(plan, out):` | Starts the function `accounting_problems`. It applies the three row rules to every trial of a run. |
| 1672 | `    """the W, E and B rules of test_rows on every trial of a run"""` | Description text: the rules are the `W`, `E` and `B` rules of `test_rows`. |
| 1673 | `    rows, p = rows_of(out), []` | `rows`: the output sorted by row type. `p`: the list of problems. |
| 1674 | `    for i, f in enumerate(plan_lines(plan)):` | Loops over the trials of the plan. `f` holds the plan fields of trial `i`. |
| 1675 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)` | `w`: the `W` rows of the trial. `e`: its `E` rows. |
| 1676 | `        if len(e) != 1:` | Tests whether the trial does not have exactly one `E` row. |
| 1677 | `            p.append("trial %d: %d E rows" % (i, len(e)))` | Adds a problem with the number of `E` rows. |
| 1678 | `            continue` | Continues with the next trial. |
| 1679 | `        p += ["trial %d: %s" % (i, x) for x in window_problems(f, w) + e_problems(f, w, e[0]) + bin_problems(f, w, of_trial(rows, "B", i))]` | Adds every problem of `window_problems` (line 115), `e_problems` (line 136) and `bin_problems` (line 153), each with the trial number in front. Together they say that the bytes and the times of every window are right: whole passes, the 8 MiB rule, the durations, the order of the times, the gaps, and bins that sum to the bytes of their window. |
| 1680 | `    return p` | Returns the list of problems. |

### `test_new_kernels`, checks k: the kernels of round 3 in every mode (lines 1683 to 1720)

| Line | Source | Explanation |
|---:|---|---|
| 1683 | `def test_new_kernels():` | Starts the test `test_new_kernels`. |
| 1684 | `    """(k) the five kernels of round 3 in --list, in the plan parser, in the trial mode and in the interval mode"""` | Description text: the checks named k. They cover the five kernels of round 3 in the output of `--list`, in the plan parser, in the trial mode and in the interval mode. |
| 1685 | `    rc, out, _ = run(["--list"])` | Runs the runner with `--list`. It prints the names of its kernels, one per line. |
| 1686 | `    rc8, out8, _ = run(["--list"], binary=E.bin8)` | Runs the local build of the accepted runner with `--list`. |
| 1687 | `    names = out.split()` | `names`: the kernel names of the runner under test. |
| 1688 | `    check("k: --list prints 29 kernels: the 21 of the accepted runner in their order, then the 5 of round 3, then the 3 new ones",` | Check: `--list` prints 29 kernels: the 21 of the accepted runner in their order, then the 5 of round 3, then the 3 new ones. |
| 1689 | `          rc == 0 and rc8 == 0 and len(names) == 29 and names[:21] == out8.split() and names[21:26] == NEW_KERNELS and` | Continues the check: both runs end with status 0, 29 names, the first 21 equal the list of the accepted runner, the next 5 are `NEW_KERNELS` ... |
| 1690 | `          names[26:] == NOP_KERNELS and names[:26] == run(["--list"], binary=E.bin10)[1].split(), names[20:])` | Continues the check: ... the last 3 are `NOP_KERNELS`, and the first 26 equal the list of the build of the `bwx10` source. The build script takes the kernels for its listing from `--list`. So the order of this list is also the order of the listing. |
| 1691 | `    lines = ["0 A 1 read_pf256@8M:8 read_pf512@8M:40 read_pf1024@1M:8 read_pf2048@8M 2 10 closed 0",` | `lines`: a plan of four trials that uses every kernel of round 3. Trial 0: previous activity `read_pf256`, prefix `read_pf512`, predecessor `read_pf1024` on 1 MiB, target `read_pf2048` with 2 windows of 10 ms. |
| 1692 | `             "1 B 1 - read_1pl@8M:40 read_1pl@1M:8 read_1pl@8M 2 10 closed 1",` | Trial 1: `read_1pl` as prefix, as predecessor on 1 MiB and as target, with bins. |
| 1693 | `             "2 C 1 - oldread@8M:8 - read_pf256@32K 3 10 closed 0",` | Trial 2: a prefix of `oldread`, then the target `read_pf256` on 32 KiB with 3 windows of 10 ms. |
| 1694 | `             "3 D 1 read_1pl@8M:8 - - read_pf512@1M 2 10 closed 0"]` | Trial 3: previous activity `read_1pl`, then the target `read_pf512` on 1 MiB. |
| 1695 | `    plan = write_plan("newk", lines)` | Writes the plan. |
| 1696 | `    for extra in ([], ["--hot-copy"]):` | Loops over two runs: one without an added option and one with `--hot-copy`. |
| 1697 | `        rc, out, err = trial(plan, extra)` | Runs the plan in the trial mode. |
| 1698 | `        tag = "with --hot-copy" if extra else "plain"` | `tag`: a word for the names of the checks: `plain`, or `with --hot-copy`. |
| 1699 | `        if not check("k: a plan that uses every new kernel as previous activity, prefix, predecessor or target runs with "` | Check: a plan that uses every new kernel as previous activity, prefix, predecessor or target runs with ... |
| 1700 | `                     "status 0 (%s)" % tag, rc == 0, err):` | Continues the check: ... status 0. So the plan parser accepts each new kernel in each phase. |
| 1701 | `            continue` | Continues with the next run when this one failed. |
| 1702 | `        rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 1703 | `        k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. |
| 1704 | `        check("k: one K row per new kernel of the plan, with the address modulo 64 (%s)" % tag,` | Check: one `K` row per new kernel of the plan, with the address modulo 64. |
| 1705 | `              sorted(k) == sorted(NEW_KERNELS + ["oldread"]) and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are the five new kernels and `oldread`, and in each row the last field is the hex address modulo 64. |
| 1706 | `        p = accounting_problems(plan, out)` | Applies the three row rules to every trial (line 1671). |
| 1707 | `        check("k: W, E and B rows of the new kernels: whole passes, 8 MiB rule, durations, gaps, bins (%s)" % tag, not p, p)` | Check: the `W`, `E` and `B` rows of the new kernels keep the rules: whole passes, the 8 MiB rule, durations, gaps and bins. So the byte and time counts of the runner are also right for the added kernels. |
| 1708 | `        check("k: the W rows name the kernel of the plan in every window (%s)" % tag,` | Check: the `W` rows name the kernel of the plan in every window. |
| 1709 | `              [w[4] for w in rows["W"]] == [e[2] for f in plan_lines(plan) for e in expected_windows(f)])` | Continues the check: the kernel column of all `W` rows equals the kernels of the planned windows, in order. |
| 1710 | `        check("k: sink_ok is 1 only for the trial that ran old read, and no X row (%s)" % tag,` | Check: `sink_ok` is `1` only for the trial that ran the old read kernel, and no `X` row is printed. |
| 1711 | `              [f[8] for f in rows["E"]] == ["NA", "NA", "1", "NA"] and not rows.get("X"), rows.get("X"))` | Continues the check: the values are `NA`, `NA`, `1`, `NA`. A new kernel returns no sum, so it has no sink check. |
| 1712 | `    for bad_name in ("read_pf128", "read_pf", "read_1pl2", "READ_PF256"):` | Loops over four names that are close to a real kernel name but are none. |
| 1713 | `        rc, out, err = trial(write_plan("badk", ["0 a 1 - - - %s@8M 1 5 closed 0" % bad_name]))` | Runs a plan whose target is that name. |
| 1714 | `        check("k: status 2 and no row for the unknown kernel %s" % bad_name, rc == 2 and out == "" and "unknown kernel" in err, (rc, err[:100]))` | Check: status 2, no row, and the words `unknown kernel` in the error output. So a name with a typing error cannot run as another kernel. |
| 1715 | `    rc, out, err = run(["--seq", "read_pf512,read_1pl@1M,asmread", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])` | Runs the interval mode with the sequence `read_pf512`, `read_1pl` on 1 MiB and `asmread`, on a buffer of 8 MiB, with intervals of at least 10 ms and 1 thread on the worker CPU. |
| 1716 | `    r = rows_of(out)` | `r`: the output sorted by row type. |
| 1717 | `    check("k: the interval mode (--seq) runs the new kernels",` | Check: the interval mode (`--seq`) runs the new kernels. |
| 1718 | `          rc == 0 and [f[3] for f in r.get("I", [])] == ["read_pf512", "read_1pl", "asmread"], (rc, err[:200]))` | Continues the check: status 0, and the kernel column of the `I` rows is `read_pf512`, `read_1pl`, `asmread`. |

### `test_rec_pad`, checks l: `--rec-pad` moves the window records and nothing else (lines 1721 to 1764)

| Line | Source | Explanation |
|---:|---|---|
| 1721 | `def test_rec_pad():` | Starts the test `test_rec_pad`. |
| 1722 | `    """(l) --rec-pad: the layout with 0, the move of the window records, bad values"""` | Description text: the checks named l for the option `--rec-pad`: the layout with the value 0, the move of the window records, and bad values. The option puts unused bytes before the window records. Round 3 added it to test whether the address of these records changes a measured rate. |
| 1723 | `    plan = write_plan("pad", ALL)` | Writes the plan `ALL` (line 623). |
| 1724 | `    outs = {}` | `outs`: the outputs of the runs, by a key. It is empty at the start. |
| 1725 | `    for key, extra, binary in (("accepted", [], E.bin8), ("none", [], None), (0, ["--rec-pad", "0"], None),` | Loops over six runs. The key `accepted` is a run of the accepted runner. The key `none` is the runner under test without the option. The key 0 is `--rec-pad 0` ... |
| 1726 | `                               (80, ["--rec-pad", "80"], None), (4000, ["--rec-pad", "4000"], None),` | Continues line 1725: ... the keys 80 and 4000 are pads of 80 and 4000 bytes ... |
| 1727 | `                               (65536, ["--rec-pad", "65536"], None)):` | Continues line 1725: ... and the key 65536 is the largest pad that the option allows. |
| 1728 | `        rc, out, err = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + extra, binary=binary)` | Runs the plan in the trial mode with the binary and the option of this run. |
| 1729 | `        check("l: the plan with all phases runs with status 0 (%s)" % (key if binary or key == "none" else "--rec-pad %s" % key),` | Check: the plan with all phases runs with status 0. The name of the check holds the key or the option. |
| 1730 | `              rc == 0 and len(rows_of(out).get("E", [])) == 4, (rc, err[:200]))` | Continues the check: status 0 and 4 `E` rows, one per trial. |
| 1731 | `        outs[key] = out` | Keeps the output under its key. |
| 1732 | `    m = {k: m_of(v) for k, v in outs.items()}` | `m`: the `M` rows of each run as a dictionary. |
| 1733 | `    check("l: --rec-pad 0 prints the rows of a run without the option: comment lines, every M value but the addresses, "` | Check: `--rec-pad 0` prints the rows of a run without the option: the comment lines, every `M` value but the addresses ... |
| 1734 | `          "and the S, K, P, W, B, E structure", structure(outs[0]) == structure(outs["none"]),` | Continues the check: ... and the same structure of the `S`, `K`, `P`, `W`, `B` and `E` rows (line 1632). So the value 0 is the same as no option. |
| 1735 | `          [x for x in zip(structure(outs[0]), structure(outs["none"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1736 | `    check("l: that comparison can fail: --rec-pad 80 gives another structure", structure(outs[80]) != structure(outs["none"]))` | Check: that comparison can fail: `--rec-pad 80` gives another structure. |
| 1737 | `    check("l: bwx11 without the option prints the rows of the accepted runner plus the 8 M rows of round 3 and the 2 of "` | Check: `bwx11` without the option prints the rows of the accepted runner plus the 8 `M` rows of round 3 and the 2 of ... |
| 1738 | `          "round 4: comment lines, M values (rec_bytes among them), S, K, P, W, B, E structure",` | Continues the name of the check: ... round 4: the comment lines, the `M` values with `rec_bytes` among them, and the structure of the `S`, `K`, `P`, `W`, `B` and `E` rows. |
| 1739 | `          structure(outs["none"], drop_m=NEW_M + NEW_M11) == structure(outs["accepted"]) and "rec_bytes" in m["accepted"],` | Continues the check: without the 10 added `M` rows the structure equals that of the accepted runner, and the accepted runner prints `rec_bytes`. So the additions of rounds 3 and 4 changed no row that the analysis of the accepted runner reads. |
| 1740 | `          [x for x in zip(structure(outs["none"], drop_m=NEW_M + NEW_M11), structure(outs["accepted"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1741 | `    check("l: that comparison can fail: with --rec-pad 80 the M row rec_bytes differs from the accepted runner",` | Check: that comparison can fail: with `--rec-pad 80` the `M` row `rec_bytes` differs from the accepted runner. |
| 1742 | `          structure(outs[80], drop_m=NEW_M + NEW_M11) != structure(outs["accepted"]))` | Continues the check: the two structures differ. |
| 1743 | `    keys = [f[1] for f in rows_of(outs["none"])["M"]]` | `keys`: the keys of the `M` rows of the run without the option, in the order of the output. |
| 1744 | `    check("l: the 8 M rows of round 3 stand together, in the documented order, directly after M,trace",` | Check: the 8 `M` rows of round 3 stand together, in the documented order, directly after the row `M,trace`. |
| 1745 | `          keys[keys.index("trace") + 1:keys.index("trace") + 9] == NEW_M and all(keys.count(k) == 1 for k in NEW_M), keys)` | Continues the check: the 8 keys after `trace` are those of `NEW_M`, and each of these keys stands once. |
| 1746 | `    check("l: M,rec_pad holds the option value and is 0 without the option",` | Check: `M,rec_pad` holds the value of the option and is 0 without the option. |
| 1747 | `          [m[k].get("rec_pad") for k in ("none", 0, 80, 4000, 65536)] == ["0", "0", "80", "4000", "65536"])` | Continues the check: the values of the five runs are `0`, `0`, `80`, `4000` and `65536`. So each result names the pad under which it was measured. |
| 1748 | `    check("l: M,hot_copy is 0 and M,win_size is 80 (the size of one window record) in every run",` | Check: `M,hot_copy` is 0 and `M,win_size` is 80 in every run. 80 bytes is the size of one window record. With `win_addr` and this size the address of every window record can be computed. |
| 1749 | `          all(m[k].get("hot_copy") == "0" and m[k].get("win_size") == "80" for k in ("none", 0, 80, 4000, 65536)), m["none"])` | Continues the check: the two values in each of the five runs. |
| 1750 | `    hexa = re.compile(r"[0-9a-f]+")` | `hexa`: a pattern for a hex number without a prefix. |
| 1751 | `    check("l: the five address rows hold hex numbers above 0",` | Check: the five address rows hold hex numbers above 0. |
| 1752 | `          all(hexa.fullmatch(m[k].get(a, "")) and int(m[k][a], 16) > 0 for k in ("none", 0, 80, 4000, 65536) for a in ADDR_KEYS), m["none"])` | Continues the check: every key of `ADDR_KEYS` in each of the five runs. |
| 1753 | `    a = {k: {x: int(m[k][x], 16) for x in ADDR_KEYS} for k in ("none", 0, 80, 4000, 65536)}` | `a`: the five addresses of each of the five runs as numbers. |
| 1754 | `    check("l: buf_addr is a multiple of 2 MiB, and the five addresses differ from each other",` | Check: `buf_addr` is a multiple of 2 MiB, and the five addresses differ from each other. |
| 1755 | `          all(a[k]["buf_addr"] % (2 << 20) == 0 and len(set(a[k].values())) == 5 for k in a), a["none"])` | Continues the check: the condition on every run. The buffer starts at a 2 MiB boundary, so it can lie on huge pages from its first byte on. |
| 1756 | `    base = a[0]["win_addr"] - a[0]["rec_addr"]` | `base`: the distance from the start of the record block (`rec_addr`) to the first window record (`win_addr`) with `--rec-pad 0`, in bytes. |
| 1757 | `    check("l: without a pad win[0] stands after the 4 trial records of the plan: win_addr - rec_addr is a multiple of 4 above 0, "` | Check: without a pad the first window record stands after the 4 trial records of the plan. The distance is a multiple of 4 above 0 ... |
| 1758 | `          "the same without the option and with --rec-pad 0", base > 0 and base % 4 == 0 and a["none"]["win_addr"] - a["none"]["rec_addr"] == base, base)` | Continues the check: ... and it is the same without the option and with `--rec-pad 0`. |
| 1759 | `    for pad in (80, 4000, 65536):` | Loops over the three pads above 0. |
| 1760 | `        check("l: --rec-pad %d: win_addr - rec_addr grows by exactly %d bytes, and rec_bytes grows by exactly %d bytes" % (pad, pad, pad),` | Check: with this pad the distance from `rec_addr` to `win_addr` grows by exactly the pad, and `rec_bytes` grows by exactly the pad. |
| 1761 | `              a[pad]["win_addr"] - a[pad]["rec_addr"] - base == pad and int(m[pad]["rec_bytes"]) - int(m[0]["rec_bytes"]) == pad,` | Continues the check: both differences, measured against the run with `--rec-pad 0`. So the option moves the window records by the bytes that it names, inside a record block that is larger by the same bytes. |
| 1762 | `              (a[pad]["win_addr"] - a[pad]["rec_addr"] - base, m[pad]["rec_bytes"], m[0]["rec_bytes"]))` | Continues the check: the three values as the detail. |
| 1763 | `        p = accounting_problems(plan, outs[pad])` | Applies the three row rules to the run with this pad (line 1671). |
| 1764 | `        check("l: --rec-pad %d: W, E and B rows keep the rules (whole passes, durations, gaps, bins)" % pad, not p, p)` | Check: with this pad the `W`, `E` and `B` rows keep the rules: whole passes, durations, gaps and bins. The moved records still hold right counts. |

### `test_rec_pad`: the absolute address of the window records (lines 1765 to 1802)

| Line | Source | Explanation |
|---:|---|---|
| 1765 | `    # The absolute address. The record block is the first block that the worker thread takes from malloc. glibc` | Comment: the next checks look at the absolute address. The record block is the first block that the worker thread takes from `malloc`. The C library glibc ... |
| 1766 | `    # gives a thread its own heap, which starts at a multiple of 64 MiB. So the address of the block modulo 64 MiB` | Comment: ... gives a thread its own heap, which starts at a multiple of 64 MiB. So the address of the block modulo 64 MiB ... |
| 1767 | `    # is the same in every process (below the size from which malloc maps a block on its own, 128 KiB by default).` | Comment: ... is the same in every process. This holds below the size from which `malloc` maps a block on its own, 128 KiB by default. |
| 1768 | `    big = write_plan("padbig", ["0 a 1 - - - asmread@8M 120 2 closed 0"])` | `big`: a plan with one trial of 120 target windows of 2 ms of `asmread` on 8 MiB. |
| 1769 | `    abs_addr = {}` | `abs_addr`: the address of the first window record per pad, empty at the start. |
| 1770 | `    for pad in (0, 80, 4000):` | Loops over the pads 0, 80 and 4000. |
| 1771 | `        rc, out, err = trial(big, ["--rec-pad", str(pad)])` | Runs the plan with this pad. |
| 1772 | `        abs_addr[pad] = int(m_of(out).get("win_addr", "0"), 16) if rc == 0 else None` | Keeps `win_addr` as a number, or `None` when the run failed. |
| 1773 | `    low = {k: None if v is None else v % (64 << 20) for k, v in abs_addr.items()}` | `low`: each address modulo 64 MiB. |
| 1774 | `    for pad in (80, 4000):` | Loops over the pads 80 and 4000. |
| 1775 | `        check("l: a plan of 120 windows: win_addr modulo 64 MiB moves up by exactly %d bytes with --rec-pad %d (three processes "` | Check: for a plan of 120 windows, `win_addr` modulo 64 MiB moves up by exactly the pad. The name adds: three processes ... |
| 1776 | `              "with address randomization; this relies on the thread heap of glibc)" % (pad, pad),` | Continues the name of the check: ... with address randomization, and the check relies on the thread heap of glibc. |
| 1777 | `              None not in low.values() and low[pad] - low[0] == pad, low)` | Continues the check: no run failed, and the address with the pad minus the address without it equals the pad. So the option moves the records also in absolute terms, from process to process. A test that compares two pads then compares two known addresses. |
| 1778 | `    b = mutant_build(PAD_MUTANT, "pad")` | `b`: a build in which `--rec-pad` does not move the window records (line 445). |
| 1779 | `    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--rec-pad", "80"], binary=b) if b else (1, "", "")` | Runs the plan `ALL` with `--rec-pad 80` and that build. Without a build the status is 1. |
| 1780 | `    mm = m_of(out)` | `mm`: the `M` rows of that run. |
| 1781 | `    check("l: the move check fails on a build with " + PAD_MUTANT,` | Check: the move check fails on that build. |
| 1782 | `          rc == 0 and int(mm["win_addr"], 16) - int(mm["rec_addr"], 16) == base, (rc, mm.get("win_addr")))` | Continues the check: the run ends with status 0, and the distance from `rec_addr` to `win_addr` is still `base`. The check of line 1760 would find this build. |
| 1783 | `    r = subprocess.run(["setarch", os.uname().machine, "-R", "true"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `setarch` with the machine name and `-R` on the command `true`. `setarch -R` starts a program with address randomization switched off. This call only tests whether that works here. |
| 1784 | `    if r.returncode != 0:` | Tests whether it failed. |
| 1785 | `        check("l: absolute win_addr without address randomization (setarch -R does not work here: NOT RUN)", False, r.stderr)` | Records a failed check with `NOT RUN` in its name: the absolute address without address randomization cannot be tested. |
| 1786 | `    else:` | If it works: |
| 1787 | `        fixed = {}` | `fixed`: the five addresses per pad, empty at the start. |
| 1788 | `        for pad in (0, 80, 4000):` | Loops over the pads 0, 80 and 4000. |
| 1789 | `            # tw_addr lies on the stack of the main thread, below the argument and environment text. "0", "80" and` | Comment: `tw_addr` lies on the stack of the main thread, below the text of the arguments and of the environment. The pad values `0`, `80` and ... |
| 1790 | `            # "4000" differ in length, which can move it by 16 or more bytes. The variable TEST_FILL makes the` | Comment: ... `4000` differ in length. That can move `tw_addr` by 16 or more bytes. The variable `TEST_FILL` makes the ... |
| 1791 | `            # text of the three runs equally long. (test_runner10.py has no such fill: there the check depends` | Comment: ... text of the three runs equally long. The comment adds that `test_runner10.py` has no such fill, so there the check depends ... |
| 1792 | `            # on the size of the environment of the caller.)` | Comment: ... on the size of the environment of the caller. |
| 1793 | `            r = subprocess.run(["setarch", os.uname().machine, "-R", E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M",` | Runs the runner under `setarch -R` on the plan `big` in the trial mode ... |
| 1794 | `                                "--plan", big, "--rec-pad", str(pad)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Continues the call of line 1793: ... with the pad of this run. The outputs are collected. |
| 1795 | `                               universal_newlines=True, timeout=120, env=dict(os.environ, TEST_FILL="x" * (4 - len(str(pad)))))` | Continues the call: the outputs are text, the time limit is 120 s, and `TEST_FILL` holds as many `x` as the pad value has fewer than 4 characters. |
| 1796 | `            fixed[pad] = {k: int(v, 16) for k, v in m_of(r.stdout).items() if k in ADDR_KEYS}` | Keeps the five addresses of this run as numbers. |
| 1797 | `        check("l: without address randomization (setarch -R) the absolute win_addr moves by exactly 80 and 4000 bytes, and "` | Check: without address randomization the absolute `win_addr` moves by exactly 80 and 4000 bytes, and ... |
| 1798 | `              "rec_addr, buf_addr, stack_addr and tw_addr do not move",` | Continues the name of the check: ... `rec_addr`, `buf_addr`, `stack_addr` and `tw_addr` do not move. |
| 1799 | `              all(len(fixed[p]) == 5 for p in fixed) and` | Continues the check: every run printed five addresses ... |
| 1800 | `              all(fixed[p]["win_addr"] - fixed[0]["win_addr"] == p for p in (80, 4000)) and` | Continues the check: ... `win_addr` with a pad minus `win_addr` without one equals the pad ... |
| 1801 | `              all(fixed[p][k] == fixed[0][k] for p in (80, 4000) for k in ADDR_KEYS if k != "win_addr"), fixed)` | Continues the check: ... and each other address equals its value without a pad. So the option changes one thing only, the place of the window records. The buffer, the record block, the stack of the worker and the record of the worker stay where they are. |

### `test_rec_pad`: bad values of `--rec-pad`, and the options outside the trial mode (lines 1803 to 1820)

| Line | Source | Explanation |
|---:|---|---|
| 1803 | `    good = write_plan("good", [GOOD])` | `good`: a plan with the line `GOOD`. |
| 1804 | `    base_args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good]` | `base_args`: the arguments of a valid trial run. |
| 1805 | `    for name, value in (("a negative value", "-8"), ("a value above 65536", "65544"), ("65537", "65537"), ("a word", "abc"),` | Loops over nine bad values: a negative value, a value above 65536, the value 65537, a word ... |
| 1806 | `                        ("a number with a letter after it", "80x"), ("a fraction", "80.5"), ("an empty value", ""),` | Continues line 1805: ... a number with a letter after it, a fraction, an empty value ... |
| 1807 | `                        ("a value that is not a multiple of 8", "12"), ("a hex number", "0x50")):` | Continues line 1805: ... a value that is no multiple of 8, and a hex number. |
| 1808 | `        rc, out, err = run(base_args + ["--rec-pad", value])` | Runs the runner with `--rec-pad` and that value. |
| 1809 | `        check("l: status 2, no row and a message for --rec-pad with " + name, rc == 2 and out == "" and "--rec-pad" in err,` | Check: status 2, no row and a message that names `--rec-pad`. A malformed value must not run as 0 or as another pad. |
| 1810 | `              "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Continues the check: the status and the starts of both outputs as the detail. |
| 1811 | `    rc, out, err = run(base_args + ["--rec-pad"])` | Runs the runner with `--rec-pad` as the last argument, without a value. |
| 1812 | `    check("l: status 2 and no row for --rec-pad without a value", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. |
| 1813 | `    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--rec-pad", "80"])` | Runs the interval mode with `--rec-pad 80`. |
| 1814 | `    check("l: status 2 and no row for --rec-pad outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. The option belongs to the trial mode only. |
| 1815 | `    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--hot-copy"])` | Runs the interval mode with `--hot-copy`. |
| 1816 | `    check("l: status 2 and no row for --hot-copy outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. This option belongs to the trial mode only too. |
| 1817 | `    rc, out, err = run(base_args + ["--rec-pad", "0"])` | Runs the same command as the bad cases with `--rec-pad 0`. |
| 1818 | `    check("l: the control: the same command with --rec-pad 0 runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the control runs with status 0 and prints the `E` row of trial 0. So the refusals before came from the values. |

### `TRACE_PLAN` and `trace_run_problems`: the trace rules on a whole run (lines 1821 to 1844)

| Line | Source | Explanation |
|---:|---|---|
| 1821 | `TRACE_PLAN = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",` | `TRACE_PLAN`: the five trial lines of the trace test (line 814). Trial 0: all phases, counters closed, with bins. |
| 1822 | `              "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",` | Trial 1: a prefix, a predecessor and 3 target windows, with the count mode `read`. |
| 1823 | `              "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",` | Trial 2: a prefix and 2 target windows, with the count mode `open`. |
| 1824 | `              "3 D 1 - - - read@8M 2 20 read 0",` | Trial 3: only 2 target windows, with the count mode `read`. |
| 1825 | `              "4 E 1 - - - oldread@8M 2 20 closed 0"]` | Trial 4: only 2 target windows, counters closed. |
| 1828 | `def trace_run_problems(plan, out):` | Starts the function `trace_run_problems`. It applies the rules of a trace run to every trial of an output. |
| 1829 | `    """the trace rule, the bin rule on the clock reads of the trace, and the page-fault line, for every trial"""` | Description text: the rules are the trace rule, the bin rule on the clock reads of the trace, and the page-fault line. |
| 1830 | `    rows, p = rows_of(out), []` | `rows`: the output sorted by row type. `p`: the list of problems. |
| 1831 | `    for i, f in enumerate(plan_lines(plan)):` | Loops over the trials of the plan. |
| 1832 | `        ev, numbered = events_of(rows, i)` | `ev`: the events of the trial. `numbered`: whether its `TR` rows are numbered without a hole. |
| 1833 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)` | `w`: the `W` rows of the trial. `e`: its `E` rows. |
| 1834 | `        if not numbered or not ev or len(e) != 1:` | Tests whether the numbers have a hole, the trial has no event, or it does not have exactly one `E` row. |
| 1835 | `            p.append("trial %d: TR rows or E row missing" % i)` | Adds a problem for the trial. |
| 1836 | `            continue` | Continues with the next trial. |
| 1837 | `        p += ["trial %d: %s" % (i, x) for x in trace_problems(f, ev, w, e[0])]` | Adds the problems of `trace_problems` (line 184), each with the trial number in front. |
| 1838 | `        p += ["trial %d: %s" % (i, x) for x in bin_problems(f, w, of_trial(rows, "B", i), {t for n, t in ev if n == "clock"})]` | Adds the problems of `bin_problems` (line 153) with the times of the clock reads of the trace. |
| 1839 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)` | `faults`: the pairs of trial number and count from the comment lines `# minflt,<trial>,<count>`. They give the minor page faults of the worker during each timed sequence. |
| 1840 | `    if faults != [(str(i), "0") for i in range(len(plan_lines(plan)))]:` | Tests whether the list is not exactly one line per trial with the count 0. |
| 1841 | `        p.append("minor page faults in a timed sequence: %s" % faults)` | Adds a problem: minor page faults in a timed sequence. |
| 1842 | `    return p` | Returns the list of problems. |

### `test_hot_copy`, checks m: `--hot-copy` prints the rows of a plain run (lines 1845 to 1872)

| Line | Source | Explanation |
|---:|---|---|
| 1845 | `def test_hot_copy():` | Starts the test `test_hot_copy`. |
| 1846 | `    """(m) --hot-copy: the rows, the byte accounting, the trace rules"""` | Description text: the checks named m for the option `--hot-copy`: the rows, the byte accounting and the trace rules. With the option the function `timed_sequence_hot` runs the windows. Its window loop works on local copies and does not touch the window record between the first and the last pass of a window. |
| 1847 | `    plan = write_plan("hot", ALL)` | Writes the plan `ALL`. |
| 1848 | `    rc0, out0, _ = trial(plan)` | Runs it without the option. |
| 1849 | `    rc, out, err = trial(plan, ["--hot-copy"])` | Runs it with `--hot-copy`. |
| 1850 | `    if not check("m: the plan with all phases runs with status 0 with and without --hot-copy", rc == 0 and rc0 == 0, err):` | Check: the plan with all phases runs with status 0 with and without `--hot-copy`. |
| 1851 | `        return` | Ends the test when a run failed. |
| 1852 | `    check("m: M,hot_copy is 1 with the option and 0 without it", (m_of(out).get("hot_copy"), m_of(out0).get("hot_copy")) == ("1", "0"))` | Check: `M,hot_copy` is 1 with the option and 0 without it. So each result says which of the two timed functions measured it. |
| 1853 | `    check("m: --hot-copy prints the rows of a plain run: comment lines, every M value but hot_copy and the addresses, "` | Check: `--hot-copy` prints the rows of a plain run: the comment lines, every `M` value but `hot_copy` and the addresses ... |
| 1854 | `          "and the S, K, P, W, B, E structure",` | Continues the name of the check: ... and the structure of the `S`, `K`, `P`, `W`, `B` and `E` rows. |
| 1855 | `          structure(out, drop_m=["hot_copy"]) == structure(out0, drop_m=["hot_copy"]),` | Continues the check: the two structures without the row `hot_copy` are equal (line 1632). So the second timed function produces the same kinds of rows, and the analysis reads both in one way. |
| 1856 | `          [x for x in zip(structure(out), structure(out0)) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 1857 | `    check("m: that comparison can fail: another plan gives another structure",` | Check: that comparison can fail: another plan gives another structure. |
| 1858 | `          structure(out, drop_m=["hot_copy"]) != structure(trial(write_plan("hot2", ALL[:3]))[1], drop_m=["hot_copy"]))` | Continues the check: the structure of the run with `--hot-copy` differs from that of a run of the first three trials of `ALL`. |
| 1859 | `    p = accounting_problems(plan, out)` | Applies the three row rules to the run with `--hot-copy` (line 1671). |
| 1860 | `    check("m: --hot-copy: byte accounting of every window: whole passes, the 8 MiB rule, durations, monotonic times, "` | Check: with `--hot-copy` the byte accounting of every window holds: whole passes, the 8 MiB rule, durations, rising times ... |
| 1861 | `          "wall_ns and gaps from the W rows, bins that sum to the window bytes", not p, p)` | Continues the check: ... `wall_ns` and the gaps from the `W` rows, and bins that sum to the bytes of the window. `timed_sequence_hot` keeps its own count of bytes and times. This check proves that this second count follows the same rules. |
| 1862 | `    rows = rows_of(out)` | `rows`: the output of the run with `--hot-copy`, sorted by row type. |
| 1863 | `    check("m: --hot-copy: sink_ok is 1 for the trials that ran old read, and no X row",` | Check: with `--hot-copy`, `sink_ok` is `1` for the trials that ran the old read kernel, and no `X` row is printed. |
| 1864 | `          [f[8] for f in rows["E"]] == ["1", "NA", "NA", "1"] and not rows.get("X"), rows.get("X"))` | Continues the check: the values are `1`, `NA`, `NA`, `1`. |
| 1865 | `    check("m: --hot-copy: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",` | Check: with `--hot-copy` the gap before an 8 MiB target is below 20 us in trial 0 or in trial 3. So no kernel pass lies inside the gap. |
| 1866 | `          min(int(rows["E"][0][6]), int(rows["E"][3][6])) < 20000, (rows["E"][0][6], rows["E"][3][6]))` | Continues the check: the smaller of the two gaps is below 20000 ns. |
| 1867 | `    rc, out, err = trial(plan, ["--hot-copy", "--rec-pad", "4000"])` | Runs the plan with `--hot-copy` and `--rec-pad 4000` together. |
| 1868 | `    p = accounting_problems(plan, out) if rc == 0 else ["rc=%s" % rc]` | Applies the row rules, or keeps the exit status as the problem when the run failed. |
| 1869 | `    mm = m_of(out)` | `mm`: the `M` rows of that run. |
| 1870 | `    check("m: --hot-copy together with --rec-pad 4000 runs, both M rows are set, and the byte accounting holds",` | Check: `--hot-copy` together with `--rec-pad 4000` runs, both `M` rows are set, and the byte accounting holds. |
| 1871 | `          not p and (mm.get("hot_copy"), mm.get("rec_pad")) == ("1", "4000"), p)` | Continues the check: no problem, and the values `1` and `4000`. |

### `test_hot_copy`: the trace with `--hot-copy`, and builds with a defect (lines 1873 to 1920)

| Line | Source | Explanation |
|---:|---|---|
| 1873 | `    tplan = write_plan("hottrace", TRACE_PLAN)` | Writes the plan `TRACE_PLAN` to a file. |
| 1874 | `    counted = ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"]` | `counted`: the arguments of a trace run with the two software events: `--trace`, the PMU type 1 and the events `task_clock` and `cpu_clock`. |
| 1875 | `    rc, out, err = trial(tplan, counted + ["--hot-copy"])` | Runs the plan with these arguments and `--hot-copy`. |
| 1876 | `    if not check("m: the trace run with --hot-copy ends with status 0", rc == 0, err):` | Check: the trace run with `--hot-copy` ends with status 0. |
| 1877 | `        return` | Ends the test when it failed. |
| 1878 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 1879 | `    states = [f[9] for f in rows["E"]]` | `states`: the count state of each trial. |
| 1880 | `    check("m: trace with --hot-copy: the count states are closed, read, open, read, closed", states == ["closed", "read", "open", "read", "closed"], states)` | Check: in the trace run with `--hot-copy` the count states are `closed`, `read`, `open`, `read`, `closed`. |
| 1881 | `    p = trace_run_problems(tplan, out)` | Applies the rules of a trace run to every trial (line 1828). |
| 1882 | `    check("m: trace with --hot-copy: no forbidden event in any timed sequence, the W rows, gap_ns and the bin ends are clock "` | Check: in the trace with `--hot-copy` no forbidden event lies in any timed sequence, and the `W` rows, `gap_ns` and the bin ends are clock ... |
| 1883 | `          "reads of the trace, and no minor page fault", not p, p)` | Continues the check: ... reads of the trace, and no minor page fault happened. So `timed_sequence_hot` keeps every rule of the timed path that `timed_sequence` keeps. |
| 1884 | `    reads = [[n for n, _ in events_of(rows, i)[0]].count("count_read") for i in range(5)]` | `reads`: the number of counter reads in the trace of each trial. |
| 1885 | `    check("m: trace with --hot-copy: nwin + 1 counter reads in the trials with count read, none in the others",` | Check: in the trace with `--hot-copy` the trials with the count mode `read` have one more counter read than target windows, and the others have none. |
| 1886 | `          reads == [0, 4, 0, 3, 0], reads)` | Continues the check: the counts are 0, 4, 0, 3 and 0. Trial 1 has 3 target windows and trial 3 has 2. |
| 1887 | `    names = lambda o: [[n for n, _ in events_of(rows_of(o), i)[0]] for i in range(5)]` | `names`: a function that gives the event names of each of the 5 trials of an output. |
| 1888 | `    plain = trial(tplan, counted)[1]` | `plain`: the output of the same trace run without `--hot-copy`. |
| 1890 | `    def no_clock_runs(seqs):` | Starts the inner function `no_clock_runs`. |
| 1891 | `        # the number of clock reads inside a window depends on the speed of the run; the order of the other events does not` | Comment: the number of clock reads inside a window depends on the speed of the run. The order of the other events does not. |
| 1892 | `        return [[n for j, n in enumerate(s) if n != "clock" or j == 0 or s[j - 1] != "clock"] for s in seqs]` | Returns each event list with every run of clock reads cut to one clock read. |
| 1894 | `    check("m: trace with --hot-copy: the events of every trial stand in the order of the plain run (runs of clock reads "` | Check: in the trace with `--hot-copy` the events of every trial stand in the order of the plain run, with runs of clock ... |
| 1895 | `          "counted once)", no_clock_runs(names(out)) == no_clock_runs(names(plain)) and len(names(out)[0]) > 20)` | Continues the check: ... reads counted once. Trial 0 has more than 20 events, so the comparison is not empty. Both timed functions do the same steps in the same order. |
| 1896 | `    # --hot-copy must select timed_sequence_hot(): a defect in that function shows only with the option, and a` | Comment: `--hot-copy` must select `timed_sequence_hot()`. A defect in that function shows only with the option, and a ... |
| 1897 | `    # defect in timed_sequence() only without it. The defect is a warm-up pass before the first target window.` | Comment: ... defect in `timed_sequence()` shows only without it. The defect is a warm-up pass before the first target window. |
| 1898 | `    # The trace does not log it (it does not go through tcall), but the gap before the target then holds one` | Comment: the trace does not log it, as it does not go through `tcall`. But the gap before the target then holds one ... |
| 1899 | `    # pass over 8 MiB, which takes more than 20 us with the stand-in kernels.` | Comment: ... pass over 8 MiB, which takes more than 20 us with the stand-in kernels. |
| 1900 | `    def gap_ok(o):` | Starts the inner function `gap_ok`. It applies the gap rule of line 1865 to an output. |
| 1901 | `        e = rows_of(o).get("E", [])` | `e`: the `E` rows of the output. |
| 1902 | `        return len(e) == 4 and min(int(e[0][6]), int(e[3][6])) < 20000` | Returns true when there are 4 `E` rows and the smaller gap of the trials 0 and 3 is below 20000 ns. |
| 1904 | `    for name, tag, fails_with in ((HOT_SEQ_MUTANTS[0], "hotwarm", True), (SEQ_MUTANTS[0], "warm", False)):` | Loops over two builds: one with the warm-up pass in `timed_sequence_hot`, which must fail with the option, and one with the warm-up pass in `timed_sequence`, which must fail without it. |
| 1905 | `        b = mutant_build(name, tag)` | `b`: the build with that defect. |
| 1906 | `        got = {}` | `got`: the result of the gap rule without and with the option, empty at the start. |
| 1907 | `        for hot in (False, True):` | Loops over the two runs: without and with `--hot-copy`. |
| 1908 | `            o = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan] + (["--hot-copy"] if hot else []), binary=b) if b else (1, "", "")` | Runs the plan `ALL` with that build. Without a build the status is 1. |
| 1909 | `            got[hot] = o[0] == 0 and gap_ok(o[1])` | Keeps whether the run ended with status 0 and passed the gap rule. |
| 1910 | `        check("m: a build with %s: the gap rule fails %s --hot-copy and passes %s it" %` | Check: for a build with that defect the gap rule fails with `--hot-copy` and passes without it, or the reverse for the other build. |
| 1911 | `              (name, "with" if fails_with else "without", "without" if fails_with else "with"),` | Continues the name of the check: the words `with` and `without` in the right order for this build. |
| 1912 | `              b is not None and not got[fails_with] and got[not fails_with], got)` | Continues the check: the build worked, the rule failed in the run where it must fail and passed in the other one. So the option is proven to choose the function: each defect shows only in the runs that use its function. The gap rule is also proven to find a warm-up pass that the trace cannot show. |
| 1913 | `    b = mutant_build(HOT_OFF_MUTANT, "hotoff")` | `b`: a build in which `--hot-copy` still runs `timed_sequence` (line 443). |
| 1914 | `    o = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 1915 | `    check("m: a build with %s fails the self-test only in the touch check of timed_sequence_hot" % HOT_OFF_MUTANT,` | Check: that build fails the self-test only in the touch check of `timed_sequence_hot`. |
| 1916 | `          o[0] == 1 and [x for x in o[1].splitlines() if x.endswith(",FAIL")] ==` | Continues the check: the status is 1, and the list of the failed lines equals ... |
| 1917 | `          ["trial,hot touch: timed_sequence_hot does not touch the window record between the first and the last pass,0,FAIL"],` | Continues the check: ... the one line of the touch test: `timed_sequence_hot` does not touch the window record between the first and the last pass. The rows of such a build have the right form. Only the touch test shows that the wrong function ran. |
| 1918 | `          (o[0], [x for x in o[1].splitlines() if x.endswith(",FAIL")]))` | Continues the check: the status and the failed lines as the detail. |

### `test_nop_kernels`, checks n: the kernels of round 4 in every mode (lines 1921 to 1954)

| Line | Source | Explanation |
|---:|---|---|
| 1921 | `def test_nop_kernels():` | Starts the test `test_nop_kernels`. |
| 1922 | `    """(n) the three kernels of round 4 in the plan parser, in the trial mode and in the interval mode"""` | Description text: the checks named n. They cover the three kernels of round 4 in the plan parser, in the trial mode and in the interval mode. |
| 1923 | `    lines = ["0 A 1 read_nop64@8M:8 read_nop96@8M:40 read_nop128@1M:8 read_nop64@8M 2 10 closed 0",` | `lines`: a plan of four trials that uses every nop kernel. Trial 0: previous activity `read_nop64`, prefix `read_nop96`, predecessor `read_nop128` on 1 MiB, target `read_nop64` with 2 windows of 10 ms. |
| 1924 | `             "1 B 1 - read_nop128@8M:40 read_nop64@1M:8 read_nop96@8M 2 10 closed 1",` | Trial 1: prefix `read_nop128`, predecessor `read_nop64` on 1 MiB, target `read_nop96`, with bins. |
| 1925 | `             "2 C 1 - oldread@8M:8 - read_nop128@32K 3 10 closed 0",` | Trial 2: a prefix of `oldread`, then the target `read_nop128` on 32 KiB with 3 windows of 10 ms. |
| 1926 | `             "3 D 1 read_nop96@8M:8 - - read_nop128@1M 2 10 closed 0"]` | Trial 3: previous activity `read_nop96`, then the target `read_nop128` on 1 MiB. |
| 1927 | `    plan = write_plan("nopk", lines)` | Writes the plan. |
| 1928 | `    for extra in ([], ["--hot-copy"], ["--evict-mb", "8"]):` | Loops over three runs: without an added option, with `--hot-copy` and with `--evict-mb 8`. |
| 1929 | `        rc, out, err = trial(plan, extra)` | Runs the plan in the trial mode. |
| 1930 | `        tag = "with " + " ".join(extra) if extra else "plain"` | `tag`: a word for the names of the checks: `plain`, or `with` and the option. |
| 1931 | `        if not check("n: a plan that uses every nop kernel as previous activity, prefix, predecessor and target runs with "` | Check: a plan that uses every nop kernel as previous activity, prefix, predecessor and target runs with ... |
| 1932 | `                     "status 0 (%s)" % tag, rc == 0, err):` | Continues the check: ... status 0. The plan of lines 1923 to 1926 does not use each nop kernel in each phase: `read_nop128` is never the previous activity, `read_nop64` never the prefix and `read_nop96` never the predecessor. Each of the three is a target. So the name of the check says more than the plan tests. |
| 1933 | `            continue` | Continues with the next run when this one failed. |
| 1934 | `        rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 1935 | `        k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. |
| 1936 | `        check("n: one K row per nop kernel of the plan, with the address modulo 64 (%s)" % tag,` | Check: one `K` row per nop kernel of the plan, with the address modulo 64. |
| 1937 | `              sorted(k) == sorted(NOP_KERNELS + ["oldread"]) and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are the three nop kernels and `oldread`, and in each row the last field is the hex address modulo 64. |
| 1938 | `        p = accounting_problems(plan, out)` | Applies the three row rules to every trial (line 1671). |
| 1939 | `        check("n: W, E and B rows of the nop kernels: whole passes, 8 MiB rule, durations, gaps, bins (%s)" % tag, not p, p)` | Check: the `W`, `E` and `B` rows of the nop kernels keep the rules: whole passes, the 8 MiB rule, durations, gaps and bins. The planned test compares the rate of these slow kernels at several buffer sizes. So their bytes and times must be counted as for every other kernel. |
| 1940 | `        check("n: the W rows name the kernel of the plan in every window (%s)" % tag,` | Check: the `W` rows name the kernel of the plan in every window. |
| 1941 | `              [w[4] for w in rows["W"]] == [e[2] for f in plan_lines(plan) for e in expected_windows(f)])` | Continues the check: the kernel column of all `W` rows equals the kernels of the planned windows, in order. |
| 1942 | `        check("n: sink_ok is 1 only for the trial that ran old read, and no X row (%s)" % tag,` | Check: `sink_ok` is `1` only for the trial that ran the old read kernel, and no `X` row is printed. |
| 1943 | `              [f[8] for f in rows["E"]] == ["NA", "NA", "1", "NA"] and not rows.get("X"), rows.get("X"))` | Continues the check: the values are `NA`, `NA`, `1`, `NA`. |
| 1944 | `    for bad_name in ("read_nop63", "read_nop", "read_nop256", "READ_NOP64", "read_nop64x"):` | Loops over five names that are close to the name of a nop kernel but are none. `read_nop256` is among them. |
| 1945 | `        rc, out, err = trial(write_plan("badn", ["0 a 1 - - - %s@8M 1 5 closed 0" % bad_name]))` | Runs a plan whose target is that name. |
| 1946 | `        check("n: status 2 and no row for the unknown kernel %s" % bad_name, rc == 2 and out == "" and "unknown kernel" in err, (rc, err[:100]))` | Check: status 2, no row, and the words `unknown kernel` in the error output. |
| 1947 | `    rc, out, err = run(["--seq", "read_nop64,read_nop96@1M,read_nop128", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])` | Runs the interval mode with the sequence `read_nop64`, `read_nop96` on 1 MiB and `read_nop128`, on a buffer of 8 MiB, with intervals of at least 10 ms and 1 thread on the worker CPU. |
| 1948 | `    r = rows_of(out)` | `r`: the output sorted by row type. |
| 1949 | `    check("n: the interval mode (--seq) runs the nop kernels",` | Check: the interval mode (`--seq`) runs the nop kernels. |
| 1950 | `          rc == 0 and [f[3] for f in r.get("I", [])] == NOP_KERNELS, (rc, err[:200]))` | Continues the check: status 0, and the kernel column of the `I` rows holds the three nop kernels in order. |
| 1951 | `    rc, out, err = run(["--seq", "read_nop63", "--bytes", "8M", "--min-ms", "10", "--cpus", str(E.cpu), "--threads", "1"])` | Runs the interval mode with the sequence `read_nop63`. |
| 1952 | `    check("n: the interval mode gives status 2 for the unknown kernel read_nop63", rc == 2 and "I," not in out, (rc, err[:100]))` | Check: the interval mode gives status 2 for the unknown kernel `read_nop63` and prints no `I` row. |

### `evict_problems` and `run_maxrss`: helpers for the evict step (lines 1955 to 2003)

| Line | Source | Explanation |
|---:|---|---|
| 1955 | `def evict_problems(rows, want_mb, traced):` | Starts the rule `evict_problems`. It checks the rows of the evict step in the rows of one run. `want_mb` is the value of `--evict-mb` of that run. `traced` says whether the run had `--trace`. In the evict step the worker maps other memory, writes it twice and unmaps it, before the first trial. |
| 1956 | `    """The rows of the evict step. M,evict_mb holds the option value. M,evict_ns is 0 without a step and above 0` | Description text: the rows of the evict step. `M,evict_mb` holds the value of the option. `M,evict_ns` is 0 without a step and above 0 ... |
| 1957 | `    with one. With --trace and a step: the two rows TR,-1 hold its start and its end, their difference is` | Description text: ... with one. With `--trace` and a step, the two rows `TR,-1` hold its start and its end, and their difference is ... |
| 1958 | `    evict_ns, and the step lies outside every timed sequence: it ends before the first window of the first trial,` | Description text: ... `evict_ns`. The step lies outside every timed sequence: it ends before the first window of the first trial ... |
| 1959 | `    it overlaps no trial (first window start to last window end), and no clock read of a trial lies inside it."""` | Description text: ... it overlaps no trial, from the first window start to the last window end, and no clock read of a trial lies inside it. |
| 1960 | `    p = []` | `p`: the list of problems. |
| 1961 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary. |
| 1962 | `    if m.get("evict_mb") != str(want_mb):` | Tests whether `M,evict_mb` is not the expected value. |
| 1963 | `        p.append("M,evict_mb is %s, expected %d" % (m.get("evict_mb"), want_mb))` | Adds a problem with both values. |
| 1964 | `    ns = m.get("evict_ns", "")` | `ns`: the text of `M,evict_ns`, or an empty text when the row is missing. |
| 1965 | `    if not ns.isdigit():` | Tests whether it is no whole number. |
| 1966 | `        return p + ["M,evict_ns is '%s'" % ns]` | Returns the problems so far plus this one. |
| 1967 | `    if (int(ns) > 0) != (want_mb > 0):` | Tests whether `evict_ns` is above 0 in a run without a step, or 0 in a run with a step. |
| 1968 | `        p.append("M,evict_ns is %s with %d MiB" % (ns, want_mb))` | Adds a problem with the duration and the MiB value. |
| 1969 | `    tr = [f for f in rows.get("TR", []) if f[1] == "-1"]` | `tr`: the `TR` rows with the trial number `-1`. The runner uses that number for the evict step, which belongs to no trial. |
| 1970 | `    if not (traced and want_mb > 0):` | For a run without a trace or without a step: |
| 1971 | `        return p + (["TR rows of the evict step without --trace or without a step"] if tr else [])` | The rule ends here. Such a run must have no `TR` row of the evict step. One problem is added when it has one. |
| 1972 | `    if [f[2:4] for f in tr] != [["0", "evict_start"], ["1", "evict_end"]]:` | Tests that there are exactly two such rows: event 0 with the name `evict_start` and event 1 with the name `evict_end`. |
| 1973 | `        return p + ["the TR rows of the evict step are %s" % tr]` | Returns the problems plus this one if not. |
| 1974 | `    t0, t1 = int(tr[0][4]), int(tr[1][4])` | `t0`, `t1`: the start time and the end time of the step in ns. |
| 1975 | `    if t0 <= 0 or t1 <= t0 or t1 - t0 != int(ns):` | Tests the times: the start must be above 0, the end must lie after the start, and the end minus the start must equal `evict_ns`. |
| 1976 | `        p.append("evict_start %d, evict_end %d, evict_ns %s" % (t0, t1, ns))` | Adds a problem with the three values. |
| 1977 | `    w = rows.get("W", [])` | `w`: all `W` rows of the run. |
| 1978 | `    if not w:` | Tests whether the run has no `W` row. |
| 1979 | `        return p + ["no W row"]` | Returns the problems plus this one. |
| 1980 | `    if t1 > min(int(f[7]) for f in w):` | Tests whether the step ends after the earliest window start of the run. |
| 1981 | `        p.append("the evict step ends at %d ns, after the start of the first window (%d ns)" % (t1, min(int(f[7]) for f in w)))` | Adds a problem with both times. The step must be over before the first window is timed. |
| 1982 | `    for i in sorted({int(f[1]) for f in w}):` | Loops over the trial numbers of the `W` rows. |
| 1983 | `        a, b = min(int(f[7]) for f in w if f[1] == str(i)), max(int(f[8]) for f in w if f[1] == str(i))` | `a`, `b`: the start of the first window and the end of the last window of this trial. Between them lies its timed sequence. |
| 1984 | `        if t0 <= b and t1 >= a:` | Tests whether the time of the step and this range overlap. |
| 1985 | `            p.append("the evict step (%d to %d ns) overlaps the timed sequence of trial %d (%d to %d ns)" % (t0, t1, i, a, b))` | Adds a problem that names the trial and all four times. |
| 1986 | `    inside = [f for f in rows.get("TR", []) if f[1] != "-1" and f[3] == "clock" and t0 <= int(f[4]) <= t1]` | `inside`: the clock reads of the trials (`TR` rows with the event `clock` and another trial number than `-1`) whose time lies inside the step. |
| 1987 | `    if inside:` | Tests whether any exists. |
| 1988 | `        p.append("%d clock reads of a trial lie inside the evict step" % len(inside))` | Adds a problem with their number. |
| 1989 | `    return p` | Returns the list of problems. |
| 1992 | `def run_maxrss(args, binary=None):` | Starts the function `run_maxrss`. It runs a binary and measures how much memory the process held at most. |
| 1993 | `    """(exit status, stdout, peak resident set size in kB) of one run"""` | Description text: the result is the exit status, the standard output and the peak resident set size in kB of one run. The resident set size is the part of the memory of a process that lies in physical memory. |
| 1994 | `    path = os.path.join(E.tmp, "rss.out")` | `path`: the file `rss.out` in the temporary folder, for the output. |
| 1995 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment without the variables whose name starts with `BWX_`. |
| 1996 | `    with open(path, "w") as f:` | Opens the output file for writing. |
| 1997 | `        proc = subprocess.Popen([binary or E.bin] + args, stdout=f, stderr=subprocess.DEVNULL, env=env)` | Starts the binary (the runner under test unless `binary` is given) with its output in that file. The error output is discarded. |
| 1998 | `        _, status, ru = os.wait4(proc.pid, 0)` | Waits for the end of the process with `os.wait4`. It also returns `ru`, the resource usage that Linux recorded for the process. |
| 1999 | `    proc.returncode = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1` | Sets the exit status: the status of the process when it ended by itself, and -1 when a signal ended it. |
| 2000 | `    with open(path) as f:` | Opens the output file for reading. |
| 2001 | `        return proc.returncode, f.read(), ru.ru_maxrss` | Returns the exit status, the output and `ru.ru_maxrss`, the peak resident set size in kB. |

### `test_evict`, checks o: the rows with and without `--evict-mb` (lines 2004 to 2058)

| Line | Source | Explanation |
|---:|---|---|
| 2004 | `def test_evict():` | Starts the test `test_evict`. |
| 2005 | `    """(o) --evict-mb: the rows with 0, the step with a value above 0, the place of the step, bad values"""` | Description text: the checks named o for the option `--evict-mb`: the rows with the value 0, the step with a value above 0, the place of the step, and bad values. With `--evict-mb N` the worker writes N MiB of other memory twice before the first trial. The comment in `bwx11.c` gives the purpose: the lines of the benchmark buffer leave the caches, and the next read brings them back from memory. Round 4 added the option to test whether the rate changes then. |
| 2006 | `    plan = write_plan("evict", ALL)` | Writes the plan `ALL` (line 623). |
| 2007 | `    base_args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan]` | `base_args`: the arguments of a trial run of that plan. |
| 2008 | `    outs = {}` | `outs`: the outputs of the runs, by a key. It is empty at the start. |
| 2009 | `    for key, extra, binary in (("bwx10", [], E.bin10), ("none", [], None), (0, ["--evict-mb", "0"], None),` | Loops over five runs. The key `bwx10` is a run of the local build of the `bwx10` source. The key `none` is `bwx11` without the option. The key 0 is `--evict-mb 0` ... |
| 2010 | `                               (8, ["--evict-mb", "8"], None), (64, ["--evict-mb", "64"], None)):` | Continues line 2009: ... and the keys 8 and 64 are evict steps of 8 MiB and 64 MiB. |
| 2011 | `        rc, out, err = run(base_args + extra, binary=binary)` | Runs the plan with the binary and the option of this run. |
| 2012 | `        check("o: the plan with all phases runs with status 0 (%s)" % (key if binary or key == "none" else "--evict-mb %s" % key),` | Check: the plan with all phases runs with status 0. The name of the check holds the key or the option. |
| 2013 | `              rc == 0 and len(rows_of(out).get("E", [])) == 4, (rc, err[:200]))` | Continues the check: status 0 and 4 `E` rows, one per trial. |
| 2014 | `        outs[key] = out` | Keeps the output under its key. |
| 2015 | `    m = {k: m_of(v) for k, v in outs.items()}` | `m`: the `M` rows of each run as a dictionary. |
| 2016 | `    check("o: --evict-mb 0 prints the rows of a run without the option: comment lines, every M value but the addresses, "` | Check: `--evict-mb 0` prints the rows of a run without the option: the comment lines, every `M` value but the addresses ... |
| 2017 | `          "and the S, K, P, W, B, E structure", structure(outs[0]) == structure(outs["none"]),` | Continues the check: ... and the same structure of the `S`, `K`, `P`, `W`, `B` and `E` rows (line 1632). So the value 0 is the same as no option. |
| 2018 | `          [x for x in zip(structure(outs[0]), structure(outs["none"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 2019 | `    check("o: that comparison can fail: --evict-mb 8 gives another structure", structure(outs[8]) != structure(outs["none"]))` | Check: that comparison can fail: `--evict-mb 8` gives another structure. |
| 2020 | `    check("o: --evict-mb 8 differs from a run without the option only in the two M rows evict_mb and evict_ns",` | Check: `--evict-mb 8` differs from a run without the option only in the two `M` rows `evict_mb` and `evict_ns`. |
| 2021 | `          structure(outs[8], drop_m=NEW_M11) == structure(outs["none"], drop_m=NEW_M11),` | Continues the check: without these two rows the structures are equal. So the step adds no row and removes none. A run with the step and a run without it can be compared row by row. |
| 2022 | `          [x for x in zip(structure(outs[8], drop_m=NEW_M11), structure(outs["none"], drop_m=NEW_M11)) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 2023 | `    check("o: bwx11 without the option prints the rows of the bwx10 source plus the 2 new M rows: comment lines, M values, "` | Check: `bwx11` without the option prints the rows of the `bwx10` source plus the 2 new `M` rows: the comment lines, the `M` values ... |
| 2024 | `          "S, K, P, W, B, E structure",` | Continues the name of the check: ... and the structure of the `S`, `K`, `P`, `W`, `B` and `E` rows. |
| 2025 | `          structure(outs["none"], drop_m=NEW_M11) == structure(outs["bwx10"]) and "tw_addr" in m["bwx10"] and "evict_mb" not in m["bwx10"],` | Continues the check: without the 2 new rows the structures are equal. The `bwx10` build prints `tw_addr`, the last `M` row of round 3, and no `evict_mb`. So a result of `bwx11` without the option has the form of a result of `bwx10`. |
| 2026 | `          [x for x in zip(structure(outs["none"], drop_m=NEW_M11), structure(outs["bwx10"])) if x[0] != x[1]][:3])` | Continues the check: the first three items that differ, as the detail. |
| 2027 | `    check("o: that comparison can fail: without leaving out the 2 new M rows the structures differ",` | Check: that comparison can fail: when the 2 new `M` rows are not left out, the structures differ. |
| 2028 | `          structure(outs["none"]) != structure(outs["bwx10"]))` | Continues the check: the full structure of `bwx11` against that of the `bwx10` build. |
| 2029 | `    keys = [f[1] for f in rows_of(outs["none"])["M"]]` | `keys`: the keys of the `M` rows of the run without the option, in the order of the output. |
| 2030 | `    check("o: the 2 new M rows stand together, evict_mb first, directly after M,tw_addr (the last M row of round 3)",` | Check: the 2 new `M` rows stand together, `evict_mb` first, directly after `M,tw_addr`, the last `M` row of round 3. |
| 2031 | `          keys[keys.index("tw_addr") + 1:keys.index("tw_addr") + 3] == NEW_M11 and all(keys.count(k) == 1 for k in NEW_M11), keys)` | Continues the check: the 2 keys after `tw_addr` are those of `NEW_M11`, and each of them stands once. |
| 2032 | `    check("o: M,evict_mb holds the option value and is 0 without the option",` | Check: `M,evict_mb` holds the value of the option and is 0 without the option. |
| 2033 | `          [m[k].get("evict_mb") for k in ("none", 0, 8, 64)] == ["0", "0", "8", "64"], [m[k].get("evict_mb") for k in ("none", 0, 8, 64)])` | Continues the check: the values of the runs `none`, 0, 8 and 64 are `0`, `0`, `8` and `64`. So each result says whether an evict step ran before it, and with how much memory. |
| 2034 | `    check("o: M,evict_ns is 0 without the option and with --evict-mb 0",` | Check: `M,evict_ns` is 0 without the option and with `--evict-mb 0`. |
| 2035 | `          m["none"].get("evict_ns") == "0" and m[0].get("evict_ns") == "0", (m["none"].get("evict_ns"), m[0].get("evict_ns")))` | Continues the check: both values are `0`. No step ran, so no time was spent. |
| 2036 | `    check("o: M,evict_ns is a whole number above 0 with --evict-mb 8 and --evict-mb 64, and the larger step takes longer",` | Check: `M,evict_ns` is a whole number above 0 with `--evict-mb 8` and with `--evict-mb 64`, and the larger step takes longer. |
| 2037 | `          all(m[k].get("evict_ns", "").isdigit() for k in (8, 64)) and 0 < int(m[8]["evict_ns"]) < int(m[64]["evict_ns"]),` | Continues the check: both values are digits, and the 8 MiB value lies above 0 and below the 64 MiB value. `evict_ns` is the time from the clock read before the step to the clock read after it. |
| 2038 | `          (m[8].get("evict_ns"), m[64].get("evict_ns")))` | Continues the check: the two values as the detail. |
| 2039 | `    for key in ("none", 0, 8, 64):` | Loops over the four runs of `bwx11`. |
| 2040 | `        p = evict_problems(rows_of(outs[key]), 0 if key == "none" else key, False)` | Applies the rule `evict_problems` (line 1955) with the MiB value of the run and without a trace. |
| 2041 | `        check("o: the rule of the evict rows passes (%s)" % (key if key == "none" else "--evict-mb %s" % key), not p, p)` | Check: the rule of the evict rows passes for this run. |
| 2042 | `    for mb in (8, 64):` | Loops over the two runs with a step. |
| 2043 | `        p = accounting_problems(plan, outs[mb])` | Applies the three row rules to every trial (line 1671). |
| 2044 | `        check("o: --evict-mb %d: the windows still account bytes correctly: whole passes, the 8 MiB rule, durations, monotonic "` | Check: with this evict step the windows still account bytes correctly: whole passes, the 8 MiB rule, durations, rising ... |
| 2045 | `              "times, wall_ns and gaps from the W rows, bins that sum to the window bytes" % mb, not p, p)` | Continues the check: ... times, `wall_ns` and the gaps from the `W` rows, and bins that sum to the bytes of the window. |
| 2046 | `        rows = rows_of(outs[mb])` | `rows`: the output of this run, sorted by row type. |
| 2047 | `        check("o: --evict-mb %d: sink_ok is 1 for the trials that ran old read (the buffer still holds its values), no X row, "` | Check: with this evict step, `sink_ok` is `1` for the trials that ran the old read kernel, and the output has no `X` row and ... |
| 2048 | `              "no TR row" % mb, [f[8] for f in rows["E"]] == ["1", "NA", "NA", "1"] and not rows.get("X") and not rows.get("TR"), rows.get("X"))` | Continues the check: ... no `TR` row. A `sink_ok` of `1` means that the sum over the buffer is still the expected one. So the step did not change a value of the benchmark buffer. |
| 2049 | `        check("o: --evict-mb %d: both P rows of every trial hold 8192 kB for the buffer (the evict range is gone from the "` | Check: with this evict step, both `P` rows of every trial hold 8192 kB for the buffer. The name adds that the evict range is gone from the ... |
| 2050 | `              "page reads)" % mb, [f[3] for f in rows["P"]] == ["8192"] * 8, [f[3] for f in rows["P"]])` | Continues the check: ... page reads. All 8 `P` rows hold `8192`. The page state that the runner prints is that of the 8 MiB buffer alone. |
| 2051 | `    check("o: the accounting rule can fail on these rows: one changed byte count",` | Check: the accounting rule can fail on these rows after one changed byte count. |
| 2052 | `          accounting_problems(plan, outs[8].replace("\nW,0,target,0,oldread,8388608,", "\nW,0,target,0,oldread,8388608,1", 1)))` | Continues the check: in the output of the 8 MiB run a digit `1` is put in front of the byte count of target window 0 of trial 0. The rule must report a problem. |
| 2053 | `    rc, out, err = run(base_args + ["--evict-mb", "8", "--hot-copy", "--rec-pad", "80"])` | Runs the plan with `--evict-mb 8`, `--hot-copy` and `--rec-pad 80` together. |
| 2054 | `    mm = m_of(out)` | `mm`: the `M` rows of that run. |
| 2055 | `    p = accounting_problems(plan, out) + evict_problems(rows_of(out), 8, False) if rc == 0 else ["rc=%s" % rc]` | Applies the row rules and the evict rule, or keeps the exit status as the problem when the run failed. |
| 2056 | `    check("o: --evict-mb 8 together with --hot-copy and --rec-pad 80 runs, the three M rows are set, and the byte accounting holds",` | Check: `--evict-mb 8` together with `--hot-copy` and `--rec-pad 80` runs, the three `M` rows are set, and the byte accounting holds. |
| 2057 | `          not p and (mm.get("hot_copy"), mm.get("rec_pad"), mm.get("evict_mb")) == ("1", "80", "8"), p)` | Continues the check: no problem, and the values `1`, `80` and `8`. |

### `test_evict`: the evict rule on changed rows, and the proof that the step writes memory (lines 2059 to 2079)

| Line | Source | Explanation |
|---:|---|---|
| 2059 | `    # the rule on changed rows` | Comment: the next checks apply the evict rule to changed rows. |
| 2060 | `    r8 = rows_of(outs[8])` | `r8`: the rows of the run with `--evict-mb 8`. |
| 2061 | `    changed = lambda key, value: dict(r8, M=[[f[0], f[1], value] if f[1] == key else f for f in r8["M"]])` | `changed`: a function that returns these rows with the value of one `M` key replaced. |
| 2062 | `    check("o: the rule fails on evict_ns 0 with 8 MiB", evict_problems(changed("evict_ns", "0"), 8, False))` | Check: the rule fails on an `evict_ns` of 0 in a run with 8 MiB. |
| 2063 | `    check("o: the rule fails on another evict_mb", evict_problems(changed("evict_mb", "0"), 8, False))` | Check: the rule fails on an `evict_mb` that is not the value of the option. |
| 2064 | `    check("o: the rule fails on a missing M,evict_ns row", evict_problems(dict(r8, M=[f for f in r8["M"] if f[1] != "evict_ns"]), 8, False))` | Check: the rule fails when the row `M,evict_ns` is missing. |
| 2065 | `    check("o: the rule fails on an evict_ns above 0 without a step",` | Check: the rule fails on an `evict_ns` above 0 in a run without a step. |
| 2066 | `          evict_problems(dict(rows_of(outs[0]), M=[[f[0], f[1], "5"] if f[1] == "evict_ns" else f for f in rows_of(outs[0])["M"]]), 0, False))` | Continues the check: the rows of the run with `--evict-mb 0`, with `evict_ns` set to `5`. |
| 2068 | `    # the step is real: the process holds the range in memory, and a build that stores nothing does not` | Comment: the step is real. The process holds the range in memory, and a build that stores nothing does not. |
| 2069 | `    rss = {}` | `rss`: the peak resident set size per run in kB, empty at the start. |
| 2070 | `    for key, extra, binary in ((0, [], None), (256, ["--evict-mb", "256"], None)):` | Loops over two runs: without a step, and with `--evict-mb 256`. |
| 2071 | `        rc, out, kb = run_maxrss(base_args + extra, binary)` | Runs the plan and measures the peak resident set size (line 1992). |
| 2072 | `        rss[key] = kb if rc == 0 and len(rows_of(out).get("E", [])) == 4 else None` | Keeps the size, or `None` when the run did not end with status 0 and 4 `E` rows. |
| 2073 | `    check("o: --evict-mb 256: the peak resident set size of the process is at least 200 MiB above a run without the step "` | Check: with `--evict-mb 256` the peak resident set size of the process is at least 200 MiB above that of a run without the step. |
| 2074 | `          "(the range was written)", None not in rss.values() and rss[256] - rss[0] >= 200 << 10, rss)` | Continues the check: both runs worked, and the difference is at least 204800 kB. Linux assigns a memory page only when it is written. So this proves that the step wrote its range and did not only map it. |
| 2075 | `    b = mutant_build(EVICT_NOSTORE_MUTANT, "nostore")` | `b`: a build whose evict step maps and unmaps the range but stores nothing (line 448). |
| 2076 | `    rc, out, kb = run_maxrss(base_args + ["--evict-mb", "256"], b) if b else (None, "", 0)` | Runs the plan with `--evict-mb 256` and that build, and measures its peak resident set size. |
| 2077 | `    check("o: that check fails on a build with " + EVICT_NOSTORE_MUTANT,` | Check: the memory check fails on that build. |
| 2078 | `          rc == 0 and rss[0] is not None and kb - rss[0] < 100 << 10 and m_of(out).get("evict_mb") == "256", (rc, kb, rss))` | Continues the check: the run ends with status 0 and prints `M,evict_mb,256`, but its peak resident set size is less than 100 MiB (102400 kB) above the run without a step. The rows of such a build have the right form. Only the memory measurement shows that the step does nothing. |

### `test_evict`: the `mmap` calls of the step, and a step that cannot map its memory (lines 2080 to 2119)

| Line | Source | Explanation |
|---:|---|---|
| 2080 | `    # the calls of the step: one mmap of exactly N MiB by the worker, after the buffer and the record block` | Comment: the next checks look at the calls of the step. The worker makes one `mmap` of exactly N MiB, after the buffer and the record block. |
| 2081 | `    d = os.path.join(E.tmp, "shim11")` | `d`: the folder `shim11` in the temporary folder. |
| 2082 | `    os.makedirs(d)` | Creates it. |
| 2083 | `    with open(os.path.join(d, "shim.c"), "w") as f:` | Opens the file `shim.c` in it for writing. |
| 2084 | `        f.write(SHIM)` | Writes the C text `SHIM` (line 368). |
| 2085 | `    so = os.path.join(d, "shim.so")` | `so`: the path of the library file `shim.so`. |
| 2086 | `    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,` | Compiles the C text with `gcc` into a shared library, as in `test_placement` (line 778). |
| 2087 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call of line 2086: the compiler messages are collected as one text. |
| 2088 | `    if check("o: the library that logs mmap builds", r.returncode == 0, r.stdout):` | Check: the library that logs `mmap` builds. The next checks run only when it does. |
| 2089 | `        maps = {}` | `maps`: the sizes of the `mmap` calls of the worker per run, empty at the start. |
| 2090 | `        for mb in (0, 24):` | Loops over two runs: `--evict-mb 0` and `--evict-mb 24`. |
| 2091 | `            rc, out, err = run(base_args + ["--evict-mb", str(mb)], env_add={"LD_PRELOAD": so})` | Runs the plan with the option and with the library loaded through `LD_PRELOAD`. |
| 2092 | `            # worker lines only: the thread id differs from the process id` | Comment: only the lines of the worker are used. Its thread id differs from the process id. |
| 2093 | `            maps[mb] = [int(x.split()[4]) for x in err.splitlines()` | Keeps the byte counts of the log lines `shim mmap` ... |
| 2094 | `                        if x.startswith("shim mmap ") and x.split()[3] != "tid=" + x.split()[2][4:]] if rc == 0 else None` | Continues line 2093: ... whose thread id is not the process id. The value is `None` when the run failed. |
| 2095 | `        buf = 12 << 20  # the 8 MiB buffer is mapped with 4 MiB around it` | `buf`: 12 MiB. By the comment the 8 MiB buffer is mapped with 4 MiB around it. |
| 2096 | `        check("o: --evict-mb 24: the worker maps exactly 24 MiB once, after the buffer, and it is its last mmap before the trials "` | Check: with `--evict-mb 24` the worker maps exactly 24 MiB once, after the buffer. The name adds that this is its last `mmap` before the trials ... |
| 2097 | `              "apart from memory that stdio or malloc may take",` | Continues the name of the check: ... apart from memory that the output functions or `malloc` may take. |
| 2098 | `              maps[24] is not None and maps[24].count(24 << 20) == 1 and buf in maps[24] and` | Continues the check: the run worked, exactly one `mmap` of the worker has 24 MiB, an `mmap` of 12 MiB exists ... |
| 2099 | `              maps[24].index(24 << 20) > maps[24].index(buf), maps[24])` | Continues the check: ... and the 24 MiB call comes after the 12 MiB call. So the step maps the size that the option names, and it runs after the benchmark buffer exists. The condition does not test the last part of the name, that no other `mmap` follows before the trials. |
| 2100 | `        check("o: without a step the worker maps the same ranges apart from the 24 MiB",` | Check: without a step the worker maps the same ranges apart from the 24 MiB. |
| 2101 | `              maps[0] is not None and maps[24] is not None and (24 << 20) not in maps[0] and` | Continues the check: both runs worked, the run with the value 0 has no `mmap` of 24 MiB ... |
| 2102 | `              [x for x in maps[24] if x != 24 << 20] == maps[0], (maps[0], maps[24]))` | Continues the check: ... and the `mmap` sizes of the run with 24, without the 24 MiB call, equal those of the run with 0. So the step adds one mapping and changes no other allocation of the worker. |
| 2104 | `    # a failed mmap: the address space of the process is limited to 2 GiB` | Comment: the next case is an `mmap` that fails. The address space of the process is limited to 2 GiB. |
| 2105 | `    limit = lambda: resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))` | `limit`: a function that sets the limit of the address space (`RLIMIT_AS`) to 2 GiB, as soft and as hard limit. |
| 2106 | `    r = subprocess.run([E.bin] + base_args + ["--evict-mb", "4096"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs the plan with `--evict-mb 4096` in a process with that limit. A step of 4096 MiB cannot be mapped there. |
| 2107 | `                       universal_newlines=True, timeout=120, preexec_fn=limit)` | Continues the call of line 2106: the outputs are text, the time limit is 120 s, and `limit` runs in the new process before the runner starts. |
| 2108 | `    rows = rows_of(r.stdout)` | `rows`: the standard output sorted by row type. |
| 2109 | `    mm = m_of(r.stdout)` | `mm`: its `M` rows as a dictionary. |
| 2110 | `    check("o: an mmap that fails (4096 MiB under an address space limit of 2 GiB): status 2, the last row is X,-1,evict with "` | Check: an `mmap` that fails gives status 2, and the last row is `X,-1,evict` with a text. The row `M,evict_mb,4096` ... |
| 2111 | `          "a text, M,evict_mb,4096 is printed, and no M,evict_ns row, no S row and no trial row follow",` | Continues the name of the check: ... is printed, and no row `M,evict_ns`, no `S` row and no trial row follow. |
| 2112 | `          r.returncode == 2 and r.stdout.rstrip().splitlines()[-1].startswith("X,-1,evict,mmap of 4096 MiB failed: ") and` | Continues the check: the status is 2, and the last line starts with `X,-1,evict,mmap of 4096 MiB failed:` ... |
| 2113 | `          mm.get("evict_mb") == "4096" and "evict_ns" not in mm and not any(rows.get(k) for k in "SWEPBK") and` | Continues the check: ... `evict_mb` is `4096`, the key `evict_ns` is missing, and the output has no `S`, `W`, `E`, `P`, `B` or `K` row ... |
| 2114 | `          [f[1:3] for f in rows.get("X", [])] == [["-1", "evict"]], (r.returncode, r.stdout[-200:], r.stderr[-200:]))` | Continues the check: ... and the only `X` row is the evict row. So a step that could not run stops the process before any trial. No rate can be measured under a step that did not happen. |
| 2115 | `    r = subprocess.run([E.bin] + base_args + ["--evict-mb", "8"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs the plan with `--evict-mb 8` under the same limit. |
| 2116 | `                       universal_newlines=True, timeout=120, preexec_fn=limit)` | Continues the call of line 2115: the outputs, the time limit and the limit function. |
| 2117 | `    check("o: the control: under the same limit --evict-mb 8 runs with status 0 and 4 E rows",` | Check: the control: under the same limit `--evict-mb 8` runs with status 0 and 4 `E` rows. |
| 2118 | `          r.returncode == 0 and len(rows_of(r.stdout).get("E", [])) == 4, (r.returncode, r.stderr[-200:]))` | Continues the check: the condition and the detail. So the failure before came from the size of the step and not from the limit alone. |

### `test_evict`: with `--trace` the step lies outside every timed sequence (lines 2120 to 2169)

| Line | Source | Explanation |
|---:|---|---|
| 2120 | `    # --trace: the step lies outside every timed sequence` | Comment: the next checks use `--trace`. The step must lie outside every timed sequence. |
| 2121 | `    tplan = write_plan("evicttrace", TRACE_PLAN)` | Writes the plan `TRACE_PLAN` (line 1821) to a file. |
| 2122 | `    counted = ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"]` | `counted`: the arguments of a trace run with the two software events. |
| 2123 | `    for extra in ([], ["--hot-copy"]):` | Loops over two runs: without and with `--hot-copy`. |
| 2124 | `        tag = " with --hot-copy" if extra else ""` | `tag`: a word for the names of the checks. |
| 2125 | `        rc, out, err = trial(tplan, counted + ["--evict-mb", "8"] + extra)` | Runs the plan with the trace arguments, `--evict-mb 8` and the option of this run. |
| 2126 | `        if not check("o: the trace run with --evict-mb 8%s ends with status 0" % tag, rc == 0, err):` | Check: the trace run with `--evict-mb 8` ends with status 0. |
| 2127 | `            continue` | Continues with the next run when this one failed. |
| 2128 | `        rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 2129 | `        p = evict_problems(rows, 8, True)` | Applies the evict rule for a run with a trace (line 1955). |
| 2130 | `        check("o: trace with --evict-mb 8%s: the rows TR,-1,0,evict_start and TR,-1,1,evict_end hold the step, their "` | Check: in the trace with `--evict-mb 8` the rows `TR,-1,0,evict_start` and `TR,-1,1,evict_end` hold the step, their ... |
| 2131 | `              "difference is evict_ns, the step ends before the first window, overlaps no timed sequence, and holds no "` | Continues the name of the check: ... difference is `evict_ns`, the step ends before the first window, overlaps no timed sequence, and holds no ... |
| 2132 | `              "clock read of a trial" % tag, not p, p)` | Continues the check: ... clock read of a trial. So the time of the step is in no window and in no gap. It cannot change a measured duration. |
| 2133 | `        p = trace_run_problems(tplan, out)` | Applies the rules of a trace run to every trial (line 1828). |
| 2134 | `        check("o: trace with --evict-mb 8%s: no forbidden event in any timed sequence, the W rows, gap_ns and the bin ends are "` | Check: in the trace with `--evict-mb 8` no forbidden event lies in any timed sequence, and the `W` rows, `gap_ns` and the bin ends are ... |
| 2135 | `              "clock reads of the trace, and no minor page fault in a timed sequence" % tag, not p, p)` | Continues the check: ... clock reads of the trace, and no minor page fault happened in a timed sequence. The step maps and unmaps memory. This check shows that no page fault of the step happens inside a trial. |
| 2136 | `        check("o: trace with --evict-mb 8%s: the two rows of the step stand before the first S row" % tag,` | Check: in the trace with `--evict-mb 8` the two rows of the step stand before the first `S` row. |
| 2137 | `              out.index("\nTR,-1,1,evict_end,") < out.index("\nS,0,"))` | Continues the check: the position of the row `evict_end` in the output lies before the position of the `S` row of trial 0. |
| 2138 | `        if extra:` | For the run with `--hot-copy`: |
| 2139 | `            continue` | the rest of the loop body is skipped. The checks on changed rows run once, on the plain run. |
| 2140 | `        tr = [f for f in rows["TR"] if f[1] == "-1"]` | `tr`: the two `TR` rows of the step. |
| 2141 | `        w0 = of_trial(rows, "W", 0)` | `w0`: the `W` rows of trial 0. |
| 2142 | `        mid = (int(w0[0][7]) + int(w0[-1][8])) // 2` | `mid`: the middle of the timed sequence of trial 0 in ns. |
| 2143 | `        moved = lambda t0, t1: dict(rows, TR=[f for f in rows["TR"] if f[1] != "-1"] +` | `moved`: a function that returns the rows with the step moved to the times `t0` and `t1`. It removes the two `TR` rows of the step ... |
| 2144 | `                                    [tr[0][:4] + [str(t0)], tr[1][:4] + [str(t1)]],` | Continues line 2143: ... adds two rows with the new times ... |
| 2145 | `                                    M=[[f[0], f[1], str(t1 - t0)] if f[1] == "evict_ns" else f for f in rows["M"]])` | Continues line 2143: ... and sets `M,evict_ns` to the difference of the new times. |
| 2146 | `        check("o: the rule passes on rows rebuilt with the times of the run", not evict_problems(moved(int(tr[0][4]), int(tr[1][4])), 8, True))` | Check: the rule passes on rows rebuilt with the times of the run. So a failure below comes from the moved times and not from the rebuild. |
| 2147 | `        check("o: the rule fails on a step that ends inside the timed sequence of trial 0",` | Check: the rule fails on a step that ends inside the timed sequence of trial 0. |
| 2148 | `              evict_problems(moved(int(tr[0][4]), mid), 8, True))` | Continues the check: the step keeps its start and ends at `mid`. |
| 2149 | `        check("o: the rule fails on a step that lies wholly inside the timed sequence of trial 0",` | Check: the rule fails on a step that lies wholly inside the timed sequence of trial 0. |
| 2150 | `              any("overlaps the timed sequence of trial 0" in x for x in evict_problems(moved(mid, mid + 1000), 8, True)))` | Continues the check: a step of 1000 ns from `mid` on. A problem must say that the step overlaps the timed sequence of trial 0. |
| 2151 | `        w3 = of_trial(rows, "W", 3)` | `w3`: the `W` rows of trial 3. |
| 2152 | `        check("o: the rule fails on a step that lies inside a window of trial 3",` | Check: the rule fails on a step that lies inside a window of trial 3. |
| 2153 | `              any("overlaps the timed sequence of trial 3" in x for x in evict_problems(moved(int(w3[0][7]) + 10, int(w3[0][7]) + 20), 8, True)))` | Continues the check: a step from 10 ns to 20 ns after the start of the first window of trial 3. A problem must name trial 3. |
| 2154 | `        gap_a, gap_b = int(of_trial(rows, "W", 1)[-1][8]), int(of_trial(rows, "W", 2)[0][7])` | `gap_a`, `gap_b`: the end of the last window of trial 1 and the start of the first window of trial 2. |
| 2155 | `        check("o: the rule fails on a step between trial 1 and trial 2 (after the first window)",` | Check: the rule fails on a step between trial 1 and trial 2. Such a step overlaps no trial, but it lies after the first window. |
| 2156 | `              gap_b - gap_a > 4 and evict_problems(moved(gap_a + 1, gap_b - 1), 8, True))` | Continues the check: the time between the two trials is above 4 ns, and the step from 1 ns after trial 1 to 1 ns before trial 2 gives a problem. The step must run once, before the first trial. So a step at a later time is a defect, also when it touches no window. |
| 2157 | `        check("o: the rule fails when evict_ns is not the difference of the two rows",` | Check: the rule fails when `evict_ns` is not the difference of the two rows. |
| 2158 | `              evict_problems(dict(rows, M=[[f[0], f[1], str(int(f[2]) + 1)] if f[1] == "evict_ns" else f for f in rows["M"]]), 8, True))` | Continues the check: the rows with 1 ns added to `evict_ns`. |
| 2159 | `        check("o: the rule fails when the row evict_end is lost", evict_problems(dict(rows, TR=[f for f in rows["TR"] if f[3] != "evict_end"]), 8, True))` | Check: the rule fails when the row `evict_end` is lost. |
| 2160 | `        check("o: the rule fails on these rows if they are said to come from a run without --trace", evict_problems(rows, 8, False))` | Check: the rule fails on these rows when the caller says that the run had no `--trace`. A run without a trace must have no `TR` row of the step. |
| 2161 | `    rc, out, err = trial(tplan, counted + ["--evict-mb", "0"])` | Runs the trace plan with `--evict-mb 0`. |
| 2162 | `    check("o: trace with --evict-mb 0: no TR row of an evict step, and the trace rules hold",` | Check: in the trace with `--evict-mb 0` there is no `TR` row of an evict step, and the trace rules hold. |
| 2163 | `          rc == 0 and not evict_problems(rows_of(out), 0, True) and not [f for f in rows_of(out).get("TR", []) if f[1] == "-1"] and` | Continues the check: status 0, no problem of the evict rule for the value 0 with a trace, no `TR` row with the trial number `-1` ... |
| 2164 | `          not trace_run_problems(tplan, out), rc)` | Continues the check: ... and no problem of the rules of a trace run. |
| 2165 | `    b = mutant_build(EVICT_LATE_MUTANT, "late")` | `b`: a build whose evict step runs after trial 0 (line 450). |
| 2166 | `    rc, out, err = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", tplan] + counted + ["--evict-mb", "8"], binary=b) if b else (None, "", "")` | Runs the trace plan with `--evict-mb 8` and that build. Without a build the status is `None`. |
| 2167 | `    check("o: the rule fails on a build with " + EVICT_LATE_MUTANT, rc == 0 and evict_problems(rows_of(out), 8, True),` | Check: the rule fails on that build. |
| 2168 | `          (rc, [f for f in rows_of(out).get("M", []) if f[1] in NEW_M11]))` | Continues the check: the run ends with status 0, and the evict rule reports a problem. So the rule is proven to find a step that does not run before the first trial. |

### `test_evict`: the memory layout stays that of the runner before (lines 2170 to 2194)

| Line | Source | Explanation |
|---:|---|---|
| 2170 | `    # the layout: without address randomization the five addresses are those of the bwx10 source` | Comment: the next checks are about the layout. Without address randomization the five addresses are those of the `bwx10` source. |
| 2171 | `    r = subprocess.run(["setarch", os.uname().machine, "-R", "true"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `setarch` with the machine name and `-R` on the command `true`, to test whether address randomization can be switched off here. |
| 2172 | `    if r.returncode != 0:` | Tests whether it failed. |
| 2173 | `        check("o: addresses without address randomization (setarch -R does not work here: NOT RUN)", False, r.stderr)` | Records a failed check with `NOT RUN` in its name. |
| 2174 | `    else:` | If it works: |
| 2175 | `        fixed = {}` | `fixed`: the five addresses per run, empty at the start. |
| 2176 | `        for key, extra, binary in (("bwx10", [], E.bin10), ("none", [], E.bin), (0, ["--evict-mb", "0"], E.bin), (8, ["--evict-mb", "8"], E.bin)):` | Loops over four runs: the build of the `bwx10` source, `bwx11` without the option, with `--evict-mb 0` and with `--evict-mb 8`. |
| 2177 | `            r = subprocess.run(["setarch", os.uname().machine, "-R", binary] + base_args + extra, stdout=subprocess.PIPE,` | Runs the binary under `setarch -R` with the arguments of the run. |
| 2178 | `                               stderr=subprocess.PIPE, universal_newlines=True, timeout=120)` | Continues the call of line 2177: the outputs are text, and the time limit is 120 s. |
| 2179 | `            fixed[key] = {k: int(v, 16) for k, v in m_of(r.stdout).items() if k in ADDR_KEYS}` | Keeps the five addresses of this run as numbers. |
| 2180 | `        shown = {k: {a: hex(v) for a, v in fixed[k].items()} for k in fixed}` | `shown`: the addresses as hex text, for the detail of the checks. |
| 2181 | `        check("o: without address randomization (setarch -R), bwx11 without the option has the five addresses of the bwx10 "` | Check: without address randomization, `bwx11` without the option has the five addresses of the `bwx10` ... |
| 2182 | `              "source: buffer, record block, window records, worker stack variable, worker record (binaries with file "` | Continues the name of the check: ... source: the buffer, the record block, the window records, the stack variable of the worker and the record of the worker. The name adds: binaries with file ... |
| 2183 | `              "names of the same length, same arguments)",` | Continues the name of the check: ... names of the same length, and the same arguments. |
| 2184 | `              len(os.path.basename(E.bin)) == len(os.path.basename(E.bin10)) and os.path.dirname(E.bin) == os.path.dirname(E.bin10) and` | Continues the check: the two binary names have the same length and lie in the same folder ... |
| 2185 | `              len(fixed["bwx10"]) == 5 and fixed["none"] == fixed["bwx10"], shown)` | Continues the check: ... the `bwx10` build printed five addresses, and the five addresses of `bwx11` equal them. Round 3 tested whether the address of the window records changes a rate. So the additions of round 4 must not move the buffer or the records. |
| 2186 | `        # tw_addr lies on the stack of the main thread, below the arguments: two more arguments move it` | Comment: `tw_addr` lies on the stack of the main thread, below the arguments. Two more arguments move it. |
| 2187 | `        heap = [k for k in ADDR_KEYS if k != "tw_addr"]` | `heap`: the address keys without `tw_addr`. |
| 2188 | `        check("o: with --evict-mb 0 and with --evict-mb 8 the buffer, the record block, the window records and the worker "` | Check: with `--evict-mb 0` and with `--evict-mb 8` the buffer, the record block, the window records and the ... |
| 2189 | `              "stack variable stand at the addresses of a run without the option (the range is mapped after them, and "` | Continues the name of the check: ... stack variable of the worker stand at the addresses of a run without the option. The name adds that the range of the step is mapped after them and ... |
| 2190 | `              "unmapped again)",` | Continues the name of the check: ... unmapped again. |
| 2191 | `              all(len(fixed[k]) == 5 and [fixed[k][a] for a in heap] == [fixed["none"][a] for a in heap] for k in (0, 8)), shown)` | Continues the check: both runs printed five addresses, and their four addresses of `heap` equal those of the run without the option. So a run with the step and a run without it differ in the step only, not in where the buffer and the records lie. |
| 2192 | `        check("o: --evict-mb 8 has all five addresses of --evict-mb 0 (arguments of the same length)",` | Check: `--evict-mb 8` has all five addresses of `--evict-mb 0`. The two argument lists have the same length. |
| 2193 | `              len(fixed[8]) == 5 and fixed[8] == fixed[0], shown)` | Continues the check: the run with 8 printed five addresses, and they equal those of the run with 0. |

### `test_evict`: bad values of `--evict-mb`, and the largest value (lines 2195 to 2214)

| Line | Source | Explanation |
|---:|---|---|
| 2195 | `    good = write_plan("good", [GOOD])` | `good`: a plan with the line `GOOD`. |
| 2196 | `    args = ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good]` | `args`: the arguments of a valid trial run. |
| 2197 | `    for name, value in (("a negative value", "-1"), ("a value above 4096", "4097"), ("a word", "abc"),` | Loops over eight bad values: a negative value, a value above 4096, a word ... |
| 2198 | `                        ("a number with a letter after it", "8x"), ("a fraction", "1.5"), ("an empty value", ""),` | Continues line 2197: ... a number with a letter after it, a fraction, an empty value ... |
| 2199 | `                        ("a hex number", "0x8"), ("a number with a unit", "8M")):` | Continues line 2197: ... a hex number and a number with a unit letter. |
| 2200 | `        rc, out, err = run(args + ["--evict-mb", value])` | Runs the runner with `--evict-mb` and that value. |
| 2201 | `        check("o: status 2, no row and a message for --evict-mb with " + name, rc == 2 and out == "" and "--evict-mb" in err,` | Check: status 2, no row and a message that names `--evict-mb`. A malformed value must not run as 0, which would be a run without a step. |
| 2202 | `              "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Continues the check: the status and the starts of both outputs as the detail. |
| 2203 | `    rc, out, err = run(args + ["--evict-mb"])` | Runs the runner with `--evict-mb` as the last argument, without a value. |
| 2204 | `    check("o: status 2 and no row for --evict-mb without a value", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. |
| 2205 | `    rc, out, err = run(["--seq", "read", "--bytes", "8M", "--min-ms", "5", "--evict-mb", "8"])` | Runs the interval mode with `--evict-mb 8`. |
| 2206 | `    check("o: status 2 and no row for --evict-mb outside the trial mode", rc == 2 and out == "" and err.strip() != "", rc)` | Check: status 2, no row and a message. The option belongs to the trial mode only. |
| 2207 | `    rc, out, err = run(args + ["--evict-mb", "0"])` | Runs the same command as the bad cases with `--evict-mb 0`. |
| 2208 | `    check("o: the control: the same command with --evict-mb 0 runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the control runs with status 0 and prints the `E` row of trial 0. |
| 2209 | `    rc, out, err = run(args + ["--evict-mb", "4096"])` | Runs the same command with `--evict-mb 4096`, the largest value that the option allows. |
| 2210 | `    check("o: the largest value, --evict-mb 4096, runs with status 0 on this machine (4 GiB of memory are written twice)",` | Check: the largest value runs with status 0 on the machine of the test. The name adds that 4 GiB of memory are written twice. |
| 2211 | `          rc == 0 and "\nE,0," in out and m_of(out).get("evict_mb") == "4096" and int(m_of(out).get("evict_ns", "0")) > 0,` | Continues the check: status 0, the `E` row of trial 0, `evict_mb` is `4096`, and `evict_ns` is above 0. |
| 2212 | `          (rc, err[:200], out[-200:]))` | Continues the check: the status and the ends of both outputs as the detail. |

### `main`: settings, the builds, the order of the tests, the summary (lines 2215 to 2267)

| Line | Source | Explanation |
|---:|---|---|
| 2215 | `def main():` | Starts the function `main`. It prepares the settings and the builds and runs all tests. |
| 2216 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg`, the file in which Linux reports the load averages. |
| 2217 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints a comment line with the three load averages (1, 5 and 15 minutes) and the number of CPUs that the test process may use. |
| 2218 | `    E.allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `E.allowed`: the CPUs from 0 to 119 on which the test process may run, sorted. The runner accepts no CPU above 119. |
| 2219 | `    if len(E.allowed) < 3 or 0 not in E.allowed:` | Tests whether fewer than 3 such CPUs exist, or CPU 0 is not among them. The tests need CPU 0, the default CPU of the controlling thread, and two more CPUs. |
| 2220 | `        print("FAIL setup: CPU 0 and two more CPUs from 0 to 119 are needed in the allowed set: %s" % E.allowed)` | Prints a line that starts with `FAIL setup` and shows the allowed CPUs. |
| 2221 | `        return 1` | Returns 1. The script then ends with exit status 1, and no test has run. |
| 2222 | `    E.cpu, E.cpu2 = [c for c in E.allowed if c != 0][:2]  # worker CPU, and a second CPU` | `E.cpu`, `E.cpu2`: the first two allowed CPUs that are not CPU 0. `E.cpu` is the worker CPU of all tests. `E.cpu2` is a second CPU. |
| 2223 | `    E.ctl = E.cpu2                                         # a control CPU that is not the default` | `E.ctl`: that second CPU, as a CPU for the controlling thread that is not the default. |
| 2224 | `    E.absent = next((c for c in range(120) if c not in E.allowed), None)` | `E.absent`: the lowest CPU from 0 to 119 that the test process may not use, or `None` when every one is allowed. |
| 2225 | `    E.tmp = tempfile.mkdtemp(prefix="bwx11-test-")` | `E.tmp`: a new temporary folder whose name starts with `bwx11-test-`. All builds and all files of the tests go there. |
| 2226 | `    E.bin, E.bin_old, E.bin8 = os.path.join(E.tmp, "bwx11"), os.path.join(E.tmp, "bwx"), os.path.join(E.tmp, B8)` | `E.bin`, `E.bin_old`, `E.bin8`: the paths of three binaries in the temporary folder: `bwx11` (the runner under test), `bwx` (the first runner) and `bwx8` (the accepted runner). |
| 2227 | `    E.bin10, E.src10 = os.path.join(E.tmp, B10), os.path.join(E.tmp, "src10")  # the bwx10 source: bwx11.c without its marked blocks` | `E.bin10`: the path of the binary `bwx10`. `E.src10`: the folder `src10` for its source. By the comment the `bwx10` source is `bwx11.c` without its marked blocks. |
| 2228 | `    print("# worker CPU %d, control CPU 0 (default) or %d, temporary folder %s" % (E.cpu, E.ctl, E.tmp))` | Prints a comment line with the worker CPU, the two possible CPUs of the controlling thread (0 by default, or `E.ctl`) and the temporary folder. |
| 2229 | `    try:` | Starts a block whose end (line 2255) always runs, also after an error. |
| 2230 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin, os.path.join(HERE, "bwx11.c")], stdout=subprocess.PIPE,` | Compiles `bwx11.c` with `gcc` and the flags `CFLAGS` into `E.bin`. |
| 2231 | `                           stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that runs the compiler: its messages are collected as one text. |
| 2232 | `        if not check("build: bwx11.c compiles with the flags of build11.sh and no compiler message", r.returncode == 0 and r.stdout == "", r.stdout):` | Check: `bwx11.c` compiles with the flags of `build11.sh` and with no compiler message. A warning counts as a failure. |
| 2233 | `            return 1` | Returns 1 when the build failed. No test can run without the binary. |
| 2234 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin_old, os.path.join(OLD, "bwx.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)` | Compiles `bwx.c`, the first runner, into `E.bin_old`. |
| 2235 | `        if not check("build: bwx.c compiles (reference for the --seq mode)", r.returncode == 0):` | Check: `bwx.c` compiles. Its binary is the reference for the checks of the mode `--seq`. |
| 2236 | `            return 1` | Returns 1 when that build failed. |
| 2237 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin8, os.path.join(X8, B8 + ".c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)` | Compiles the source of the accepted runner into `E.bin8`. |
| 2238 | `        if not check("build: the source of the accepted runner compiles (reference for the layout and the kernel list)", r.returncode == 0):` | Check: the source of the accepted runner compiles. Its binary is the reference for the layout and for the list of kernels. |
| 2239 | `            return 1` | Returns 1 when that build failed. |
| 2240 | `        os.makedirs(E.src10)` | Creates the folder `E.src10`. |
| 2241 | `        for name in ("bwx11.c", "bwx11_selftest.c"):` | Loops over the two source files `bwx11.c` and `bwx11_selftest.c`. |
| 2242 | `            with open(os.path.join(HERE, name)) as f:` | Opens the file in the folder of this test file. |
| 2243 | `                text = strip_marked(f.read(), "bwx11")[0]` | `text`: its text without the blocks `bwx11+` to `bwx11-` (line 991). |
| 2244 | `            with open(os.path.join(E.src10, name.replace("bwx11", B10)), "w") as f:` | Opens a file in `E.src10` for writing. Its name has `bwx10` in place of `bwx11`. |
| 2245 | `                f.write(text)` | Writes the text. The folder now holds the `bwx10` source as the tests define it. |
| 2246 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin10, os.path.join(E.src10, B10 + ".c")], stdout=subprocess.PIPE,` | Compiles that source into `E.bin10`. |
| 2247 | `                           stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call of line 2246: the compiler messages are collected as one text. |
| 2248 | `        if not check("build: bwx11.c without its marked blocks (the bwx10 source) compiles with no compiler message (reference "` | Check: `bwx11.c` without its marked blocks, the `bwx10` source, compiles with no compiler message. The name adds that it is the reference ... |
| 2249 | `                     "for the layout, the rows and the kernel list of bwx10)", r.returncode == 0 and r.stdout == "", r.stdout):` | Continues the check: ... for the layout, the rows and the kernel list of `bwx10`. The condition is exit status 0 and an empty compiler output. |
| 2250 | `            return 1` | Returns 1 when that build failed. |
| 2251 | `        for test in (test_source, test_selftest, test_selftest_rows, test_bad_plans, test_rows, test_sequence_code,` | Loops over the test functions in the order in which they run. This line names the first six: the source, the self-test, the row checks of the self-test, the bad plans, the rows and the timed sequence in the code. |
| 2252 | `                     test_trace, test_counters, test_disturbed, test_placement, test_kill_and_seq, test_listing_saved,` | Continues the list of the tests: the trace, the counters, the disturbed trial, the placement, the killed trial with the interval mode, and the saved listing. |
| 2253 | `                     test_build_scripts, test_new_kernels, test_rec_pad, test_hot_copy, test_nop_kernels, test_evict):` | Continues the list of the tests: the build scripts, the kernels of round 3, `--rec-pad`, `--hot-copy`, the nop kernels and `--evict-mb`. |
| 2254 | `            test()` | Runs the test. A failed check does not stop the loop. An earlier test can store a value in `E` for a later one, as `test_trace` does for `test_counters`. |
| 2255 | `    finally:` | The next lines run in every case, also when a test raised an error or `main` returned early. |
| 2256 | `        if os.environ.get("KEEP"):` | Tests whether the environment variable `KEEP` is set to a text that is not empty. |
| 2257 | `            print("# kept: %s" % E.tmp)` | Prints the path of the temporary folder, which is kept. |
| 2258 | `        else:` | If `KEEP` is not set: |
| 2259 | `            shutil.rmtree(E.tmp, ignore_errors=True)` | Deletes the temporary folder with all its content. Errors of the delete are ignored. |
| 2260 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg` again. |
| 2261 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints a comment line with the three load averages at the end. |
| 2262 | `    print("# checks failed: %d%s" % (len(failed), "".join("\n#   " + n for n in failed)))` | Prints the number of failed checks, and under it one line per failed check with its name. |
| 2263 | `    return 1 if failed else 0` | Returns 1 when a check failed, and 0 when none failed. |
| 2266 | `if __name__ == "__main__":` | Tests whether the file runs as a script, and is not loaded as a module by another file. |
| 2267 | `    sys.exit(main())` | Calls `main` and ends the script with its result as the exit status. |
