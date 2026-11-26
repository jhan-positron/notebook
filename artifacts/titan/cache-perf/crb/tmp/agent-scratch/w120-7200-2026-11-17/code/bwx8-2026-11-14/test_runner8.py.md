# `test_runner8.py` explained, line by line

- Source file: `bwx8-2026-11-14/test_runner8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1181 lines, 69017 bytes).
- sha256 of the source when this page was built: `6cbd73bdd78fc036a0df756c087c1a78412aff098403aa0cf628672ed08af771`.

## Short version: purpose

`test_runner8.py` holds the local tests of the runner `bwx8` and of its listing check `check_listing8.py`. The tests build the runner on the development machine and check its plan parser, its output rows, its timed sequence, its counters and its build script. They prove that the harness counts bytes and times in the right way, and they measure no rate, as the kernels of a local build are stand-in loops.

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
- **First runner**: the runner `bwx`. Its folder `bwx-2026-11-13` holds `bwx.c`, `bwx_selftest.c` and `build.sh`. The runner `bwx8` is a copy of it with an added trial mode.
- **Accepted build of `bwx`**: the build of the first runner whose files were saved in the folder `crb-build-2`. Its machine-code listing is the reference of the listing check.
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
- **Timed function**: `timed_sequence`, the C function of `bwx8.c` that runs a timed sequence.
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
- **Rule**: a function of this file that returns a list of problems. An empty list means that the rows are right.
- **Defect**: an entry of the table `MUTANTS`: a copy of the runner source with one change that a check must find.
- **Loop offset**: the address of the first instruction of a loop modulo 64.
- **Pad**: zero bytes that the source puts before a function. They make the function start at a planned address modulo 64.
- **Listing check**: the script `check_listing8.py`. It compares the machine-code listing of a build with the listing of the accepted build of `bwx`.
- **Offsets table**: the file `offsets.tsv` of a build: one row per kernel with the start address, the loop start and the loop start modulo 64.
- **Build record**: the file `build.txt` that the build script writes: compiler, flags, compiler messages, self-test result, branch targets and checksums.
- **Logging library**: the C text `SHIM`. A test loads it into the runner with `LD_PRELOAD`. It logs the calls `sched_setaffinity` and `mmap`, and it can let `madvise` fail.
- **PMU type**: the number by which Linux names a group of counters. In these tests type 1 means the software events of Linux.
- **Context switch**: Linux takes a thread off its CPU. It is voluntary when the thread waits by itself, and involuntary when Linux takes the CPU away.
- **Minor page fault**: happens when a thread uses a page that Linux has not yet assigned to it.
- **Stack guard**: a value that the compiler puts on the stack of a function and tests before the function returns. `__stack_chk_fail` is called when it was overwritten.
- **FNV-1a**: a simple hash function. The runner prints the 64-bit FNV-1a hash of the bytes of its plan file.

## Main flow

1. The file starts with its description, the imports and the constants: the folder of the first runner, the compiler flags and the header lines of a plan (lines 1 to 41).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed function, and the order of pin and memory mapping (lines 85 to 299).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner (lines 302 to 446).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row (lines 449 to 535).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows (lines 544 to 635).
6. `test_sequence_code`: the source text and the machine code of the timed function hold only the allowed calls, and both rules fail on a build with a defect (lines 638 to 658).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches (lines 661 to 675).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported (lines 678 to 710).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces (lines 719 to 802).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window (lines 805 to 854).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints (lines 857 to 895).
12. `test_source`: `bwx8.c` holds the kernels and the interval mode of `bwx.c` unchanged, and the kernels keep their start and their size in the binary (lines 898 to 928).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect (lines 931 to 958).
14. `test_listing_saved`: the listing check accepts the saved listing of the accepted build and rejects each kind of changed kernel (lines 980 to 1049).
15. `test_build_scripts`: `build8.sh` stops on the marker file, writes its files and rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must (lines 1052 to 1141).
16. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds two binaries, runs the 13 tests, deletes the temporary folder and prints the number of failed checks (lines 1144 to 1177).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them (lines 1148 to 1150), or when one of the two first builds fails (lines 1158 to 1164).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` (line 528, line 829).
- A test that raises a Python error ends the script. The temporary folder is still deleted (lines 1169 to 1173), but the summary lines of lines 1174 to 1176 are not printed.
- `main` does not run the tests in file order (lines 1165 to 1167). `test_source` and the two self-test tests run first. `test_trace` sets `E.soft_counters`, which `test_counters` reads (line 731, line 828).
- The tests write only into a new temporary folder (line 1154). It is deleted at the end unless the variable `KEEP` is set.
- The tests read the folder of the first runner beside the folder of the test file (line 33), and in it the sub folder `crb-build-2` (line 982). The folder `bwx-2026-11-13` of the repo copy has no such sub folder. The repo keeps its two files `listing.txt` and `offsets.tsv` in the folder `build-records/bwx-crb-build-2` of the test `2026-11-13-new-read-kernel`. So `test_listing_saved` cannot read its reference from the repo copy in its present layout.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text does not stand exactly once in the source makes its checks fail (lines 382 to 383).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the listing check `check_listing8.py` under Python (line 962), and the two build scripts `build8.sh` and `build.sh` under `bash`. A run that the helper `run` starts may last 120 s at most (line 425).
- One test loads the machine on purpose: `test_disturbed` runs an endless loop on the worker CPU during one trial (line 664).
- At two places the text and the code do not match.
  - The comment of line 937 names a build that counts one pass too many per clock read. The two defects that the code builds are others (lines 941 to 942).
  - The name of the check of line 745 says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them (line 746). The check of lines 739 to 740 tests where they lie.
- The check of line 950 tests the texts `trial,` and `,FAIL` separately. So it does not prove that the failed line of the self-test is a check of the trial mode.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/test_runner8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1181 lines, 69017 bytes, sha256 `6cbd73bdd78fc036a0df756c087c1a78412aff098403aa0cf628672ed08af771`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text of the file (lines 1 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""test_runner8.py - local tests of the runner part of bwx8.` | Starts the description text of the file. It ends in line 21. This line: the file holds the local tests of the runner part of `bwx8`. By the note `DECISIONS-bwx8.md` the runner part is the runner source, its self-test file, the build script `build8.sh`, the listing check `check_listing8.py` and this test file. |
| 4 | `Runs on the development machine (x86-64). It builds bwx8.c with the flags of` | Description text: the tests run on the development machine, which has x86-64 processors and not Arm processors. They build `bwx8.c` with the compiler flags of the build script `build8.sh`. |
| 5 | `build8.sh into a temporary folder. The read kernels are then plain C stand-in` | Description text: the build goes into a temporary folder. On this machine the read kernels are plain C loops that replace the Arm code. |
| 6 | `loops, so rates mean nothing. The tests check the harness: the plan checks,` | Description text: so a rate of such a build means nothing. The tests check the harness, which is the code around the kernels. The list of the checked parts starts: the checks of the plan file. |
| 7 | `the rows, the timed sequence, the trace, the bins, the counter states, and` | Description text: the list goes on: the output rows, the timed sequence, the trace, the bins, the counter states. |
| 8 | `the two build scripts.` | Description text: the end of the list: the two build scripts. By the description of `test_build_scripts` (line 1053) these are `build8.sh` and `check_listing8.py`. |
| 10 | `Usage: test_runner8.py            (KEEP=1 keeps the temporary folder)` | Description text: the usage. The file takes no argument. When the environment variable `KEEP` is set, the temporary folder is kept at the end. |
| 11 | `Output: one line per check, "PASS name" or "FAIL name: detail".` | Description text: the output. Each check prints one line: `PASS` and its name, or `FAIL`, its name and a detail. |
| 12 | `Exit status: 0 only if every check passed.` | Description text: the exit status is 0 only when every check passed. |
| 14 | `A rule that the tests check on the output of bwx8 is a function that returns` | Description text: how a rule is tested. A rule that the tests apply to the output of `bwx8` is a function that returns ... |
| 15 | `a list of problems. Each such function is also run on changed rows, where it` | Description text: ... a list of problems. Each such function is also run on rows that the test changed on purpose ... |
| 16 | `must report a problem. So a rule that could not fail would be seen.` | Description text: ... and it must report a problem there. So a rule that can never fail would be found. |
| 18 | `Some rules cannot be shown to fail on changed rows, because the defect is in` | Description text: some rules cannot be shown to fail on changed rows. The reason: the defect would be in ... |
| 19 | `bwx8.c itself. For these the test builds a copy of bwx8.c with one defect` | Description text: ... `bwx8.c` itself. For these rules the test builds a copy of `bwx8.c` with one defect. |
| 20 | `(MUTANTS) and requires that the check fails on it.` | Description text: the table `MUTANTS` holds these defects. The check must fail on such a copy. |
| 21 | `"""` | Ends the description text. |

### Imports, folders, compiler flags, header lines of a plan (lines 22 to 43)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `import os` | Loads `os`: paths, folders, the environment and the CPU list of the process. |
| 23 | `import re` | Loads `re`: regular expressions, which are patterns for text. |
| 24 | `import resource` | Loads `resource`: it limits the memory address space of a program that the tests start. |
| 25 | `import shutil` | Loads `shutil`: it copies files and deletes the temporary folder. |
| 26 | `import signal` | Loads `signal`: the numbers of the Linux signals. The tests use the signal `SIGKILL`, which ends a process immediately. |
| 27 | `import subprocess` | Loads `subprocess`: it starts other programs (the compiler, the runner, `objdump`, `nm`) and collects their output. |
| 28 | `import sys` | Loads `sys`: the path of the Python interpreter and the exit of the script. |
| 29 | `import tempfile` | Loads `tempfile`: it creates the temporary folder. |
| 30 | `import time` | Loads `time`: waits and time limits. |
| 32 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder that holds this test file. The sources under test are read from it. |
| 33 | `OLD = os.path.join(HERE, "..", "bwx-2026-11-13")` | `OLD`: the folder `bwx-2026-11-13` beside the folder of this file. It holds the first runner, `bwx`. The tests only read it. They also read the saved listing of the accepted build of `bwx` from its sub folder `crb-build-2` (line 982). |
| 34 | `CFLAGS = ("-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 "` | `CFLAGS`: the compiler flags, split into a list. `-O3` is the highest standard optimization level. `-march=native` allows the instructions of the build machine. `-fno-tree-loop-distribute-patterns` stops `gcc` from replacing a loop by a call of `memset` or `memcpy`. `-pthread` adds thread support. `-Wall -Wextra` switch the warnings on. `-std=gnu11` selects the C dialect. |
| 35 | `          "-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4").split()` | Continues line 34. `-fno-ipa-icf`: `gcc` keeps two functions with equal code as two functions. `-fno-toplevel-reorder`: the functions stay in the order of the source, so each kernel keeps its place in the binary. `-falign-functions=4`: a function start is aligned to 4 bytes only, so the pad bytes in the source decide where a kernel starts. |
| 36 | `MIB8 = 8 << 20` | `MIB8`: 8 MiB in bytes (8388608). It is the buffer size of most tests. The runner also reads the clock after each 8 MiB of reads. |
| 37 | `HEAD1 = "# bwx8-plan v1"` | `HEAD1`: the first line that every plan file must have. It names the format of the plan. |
| 38 | `HEAD3 = "# trial cond rep prev pfx pred tgt nwin win_ms count bins"` | `HEAD3`: the third line that every plan file must have. It names the 11 fields of a trial line. |
| 39 | `SUFFIX = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `SUFFIX`: the factor of each size letter. `K` is 1024, `M` is 1048576 (1 MiB) and `G` is 1073741824. |
| 41 | `failed = []` | `failed`: the list of the names of the checks that failed. It is empty at the start. |

### Helpers: `check`, `size_of`, `expected_windows`, `rows_of`, `of_trial` (lines 44 to 82)

| Line | Source | Explanation |
|---:|---|---|
| 44 | `def check(name, ok, detail=""):` | Starts the function `check`. Every check of this file calls it with a name, a result (`ok`) and an optional detail. |
| 45 | `    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else ": " + str(detail)[:400]))` | Prints one line: `PASS` or `FAIL`, then the name. On a failure with a detail it adds a colon and the first 400 characters of the detail. |
| 46 | `    if not ok:` | Tests whether the check failed. |
| 47 | `        failed.append(name)` | Adds the name of the failed check to the list `failed`. The exit status of the file depends on this list. |
| 48 | `    return ok` | Returns `ok`. A caller can stop its test when a step that it needs has failed. |
| 51 | `def size_of(text):` | Starts the function `size_of`. It turns a size text of a plan, such as `8M` or `1000`, into a number of bytes. |
| 52 | `    return int(text[:-1]) * SUFFIX[text[-1]] if text[-1] in SUFFIX else int(text)` | Returns the number of bytes. When the last character is `K`, `M` or `G`, the number before it is multiplied by the factor of `SUFFIX`. If not, the whole text is the number. |
| 55 | `def expected_windows(f):` | Starts the function `expected_windows`. From the fields `f` of one trial line of a plan it builds the list of the windows that the runner must run for that trial. A window is one timed period in which one kernel reads one range again and again. |
| 56 | `    """[(phase, widx, kernel, pass_bytes, min_ns)] of one plan line, from its fields"""` | Description text: each entry of the result holds the phase, the window number inside the phase, the kernel, the bytes of one pass and the shortest duration in ns. |
| 57 | `    out = []` | `out`: the list of windows, empty at the start. |
| 58 | `    for phase, text, n in (("prev", f[3], 1), ("prefix", f[4], 4), ("pred", f[5], 1)):` | Loops over the three optional phases in the order in which they run. `prev` is the previous activity (field 3, 1 window). `prefix` is the same preparation before each target (field 4, 4 windows). `pred` is the predecessor, the kernel that runs directly before the target (field 5, 1 window). |
| 59 | `        if text == "-":` | A field that is `-` means that the trial has no such phase. |
| 60 | `            continue` | Continues with the next phase. |
| 61 | `        kernel, rest = text.split("@")` | Splits the field, for example `oldread@8M:40`, at the `@` into the kernel name and the rest. |
| 62 | `        size, ms = rest.split(":")` | Splits the rest at the colon into the size and the duration in ms. |
| 63 | `        out += [(phase, i, kernel, size_of(size), int(ms) // n * 1000000) for i in range(n)]` | Adds the `n` windows of this phase, numbered from 0. Each one has the kernel, the pass size in bytes and its share of the duration in ns: the ms value divided by `n` without a remainder, times 1000000. A prefix of 40 ms gives 4 windows of 10 ms. |
| 64 | `    kernel, size = f[6].split("@")` | Splits the target field (field 6), for example `oldread@8M`, into the kernel and the size. The target is the kernel whose rate is measured. Its field has no duration. |
| 65 | `    out += [("target", i, kernel, size_of(size), int(f[8]) * 1000000) for i in range(int(f[7]))]` | Adds the target windows. Field 7 (`nwin`) is their number. Field 8 (`win_ms`) is the requested duration of each one in ms. |
| 66 | `    return out` | Returns the list. |
| 69 | `def rows_of(out):` | Starts the function `rows_of`. It sorts the output text of the runner by row type. |
| 70 | `    """{row type: [fields]} of the output of bwx8"""` | Description text: the result is a dictionary. Its key is the row type. Its value is the list of the rows of that type in the output of `bwx8`, each row split into its fields. |
| 71 | `    r = {}` | `r`: the dictionary, empty at the start. |
| 72 | `    for line in out.splitlines():` | Loops over the lines of the output. |
| 73 | `        if line and not line.startswith("#"):` | Takes only a line that is not empty and that is no comment line. A comment line starts with `#`. |
| 74 | `            f = line.split(",")` | Splits the row at the commas into its fields. |
| 75 | `            r.setdefault(f[0], []).append(f)` | Appends the row to the list of its row type. The row type is the first field, for example `W` or `E`. |
| 76 | `    return r` | Returns the dictionary. |
| 79 | `def of_trial(rows, kind, trial):` | Starts the function `of_trial`. It picks the rows of one type that belong to one trial. |
| 80 | `    return [f for f in rows.get(kind, []) if f[1] == str(trial)]` | Returns the rows of the type `kind` whose second field is the trial number. A row type that the output does not hold gives an empty list. |

### Rule `window_problems`: the `W` rows of one trial against its plan line (lines 83 to 105)

| Line | Source | Explanation |
|---:|---|---|
| 83 | `# ---- rules ----` | Comment: the rules start here. A rule is a function that returns a list of problems. An empty list means that the rule holds. |
| 85 | `def window_problems(plan_fields, wrows):` | Starts the rule `window_problems`. It compares the `W` rows of one trial with the plan line of that trial. A `W` row is the record of one window: phase, window number, kernel, bytes of one pass, bytes read, start time and end time. |
| 86 | `    """W rows of one trial against its plan line"""` | Description text: the `W` rows of one trial are compared with its plan line. |
| 87 | `    exp, p, prev_end = expected_windows(plan_fields), [], None` | `exp`: the windows that the plan line asks for (line 55). `p`: the list of problems. `prev_end`: the end time of the window before, not set yet. |
| 88 | `    if len(wrows) != len(exp):` | Tests whether the number of `W` rows equals the number of planned windows. |
| 89 | `        return ["%d W rows, %d expected" % (len(wrows), len(exp))]` | If not, the rule returns this one problem. With a lost or an added window the pairs of the next loop would not match. |
| 90 | `    for w, e in zip(wrows, exp):` | Loops over the rows and the planned windows in pairs. |
| 91 | `        phase, widx, kernel, pb, by, t0, t1 = w[2], int(w[3]), w[4], int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the fields of the row: the phase, the window number, the kernel, the bytes of one pass (`pb`), the bytes read (`by`), the start time `t0` and the end time `t1`. Both times are in ns, counted from the start of the process. |
| 92 | `        if (phase, widx, kernel, pb) != e[:4]:` | Tests that the row names the planned phase, window number, kernel and pass size. This proves that the runner ran the kernel of the plan on the range of the plan. |
| 93 | `            p.append("window %s %d %s %d, expected %s" % (phase, widx, kernel, pb, e[:4]))` | Adds a problem that shows the row and the planned values. |
| 94 | `        if by <= 0 or by % pb:` | Tests the byte count: it must be above 0 and a whole number of passes. A rate is the bytes divided by the time. So a wrong byte count gives a wrong rate. |
| 95 | `            p.append("%s %d: %d bytes is not a whole number of passes above 0" % (phase, widx, by))` | Adds a problem with the phase, the window number and the byte count. |
| 96 | `        if MIB8 % pb == 0 and by % MIB8:` | The 8 MiB rule. The runner reads the clock after 8 MiB of reads. So when the pass size divides 8 MiB, the bytes of a window must be a multiple of 8 MiB. |
| 97 | `            p.append("%s %d: %d bytes is not a multiple of 8 MiB" % (phase, widx, by))` | Adds a problem with the byte count. |
| 98 | `        if t1 - t0 < e[4]:` | Tests the duration: the end time minus the start time must be at least the requested time. A window ends at the first clock read at or after its requested duration. So it can last longer, but never shorter. |
| 99 | `            p.append("%s %d: lasts %d ns, requested %d ns" % (phase, widx, t1 - t0, e[4]))` | Adds a problem with the measured and the requested duration in ns. |
| 100 | `        if not t0 < t1 or (prev_end is not None and t0 < prev_end):` | Tests the order of the times. The start must lie before the end. The window must not start before the window before it ended. |
| 101 | `            p.append("%s %d: timestamps go back" % (phase, widx))` | Adds a problem that says that the time stamps go back. |
| 102 | `        prev_end = t1` | Keeps the end time for the test of the next window. |
| 103 | `    return p` | Returns the list of problems. |

### Rule `e_problems`: the `E` row of one trial against its `W` rows (lines 106 to 122)

| Line | Source | Explanation |
|---:|---|---|
| 106 | `def e_problems(plan_fields, wrows, erow):` | Starts the rule `e_problems`. It computes three values of the `E` row again from the `W` rows. The `E` row is the summary row that ends a trial. |
| 107 | `    """E row of one trial against its W rows: wall time and the two gaps"""` | Description text: the rule covers the wall time and the two gap values of the `E` row. |
| 108 | `    p = []` | `p`: the list of problems. |
| 109 | `    g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. Field 7 of the plan line is the number of target windows. |
| 110 | `    t0 = [int(w[7]) for w in wrows]` | `t0`: the start times of all windows, in ns. |
| 111 | `    t1 = [int(w[8]) for w in wrows]` | `t1`: the end times of all windows, in ns. |
| 112 | `    if int(erow[2]) != t1[-1] - t0[0]:` | Tests `wall_ns` (field 2 of the `E` row): it must be the end of the last window minus the start of the first window. |
| 113 | `        p.append("wall_ns %s, W rows give %d" % (erow[2], t1[-1] - t0[0]))` | Adds a problem with both values. |
| 114 | `    gap = "NA" if g == 0 else str(t0[g] - t1[g - 1])` | Computes the expected `gap_ns`: the start of target window 0 minus the end of the window before it. In this gap no kernel runs. The gap is the time between the two clock reads at that boundary. A trial without a window before the target has no gap. Its value is `NA`. |
| 115 | `    if erow[6] != gap:` | Tests field 6 of the `E` row against this value, as text. |
| 116 | `        p.append("gap_ns %s, W rows give %s" % (erow[6], gap))` | Adds a problem with both values. |
| 117 | `    gaps = [t0[i] - t1[i - 1] for i in range(1, len(wrows))]` | `gaps`: the gap at every boundary between two windows of the trial, in ns. |
| 118 | `    if erow[7] != (str(max(gaps)) if gaps else "NA"):` | Tests `max_boundary_gap_ns` (field 7): it must be the largest of these gaps, or `NA` for a trial with one window. |
| 119 | `        p.append("max_boundary_gap_ns %s, W rows give %s" % (erow[7], max(gaps) if gaps else "NA"))` | Adds a problem with both values. |
| 120 | `    return p` | Returns the list of problems. |

### Rule `bin_problems`: the `B` rows of one trial (lines 123 to 153)

| Line | Source | Explanation |
|---:|---|---|
| 123 | `def bin_problems(plan_fields, wrows, brows, clock_times=None):` | Starts the rule `bin_problems`. It checks the `B` rows of one trial. A `B` row is one time bin inside a target window: the window number, the bin number, the end time of the bin and the bytes read from the window start to that time. |
| 124 | `    """B rows of one trial. clock_times: the times of the clock reads of the trace, if there is one."""` | Description text: `clock_times` holds the times of the clock reads of the trace, when the run has a trace. |
| 125 | `    p = []` | `p`: the list of problems. |
| 126 | `    targets = [w for w in wrows if w[2] == "target"]` | `targets`: the `W` rows of the target windows. Only a target window can have bins. |
| 127 | `    if plan_fields[10] == "0":` | Field 10 of the plan line is the bins switch. `0` means that the trial has no bins. |
| 128 | `        return ["B rows in a trial without bins"] if brows else []` | For such a trial the rule ends here. It returns one problem when any `B` row exists, and no problem if none exists. |
| 129 | `    for w in targets:` | Loops over the target windows. |
| 130 | `        pb, by, t0, t1 = int(w[5]), int(w[6]), int(w[7]), int(w[8])` | Reads the pass size, the bytes, the start time and the end time of the window from its `W` row. |
| 131 | `        bins = [b for b in brows if b[2] == w[3]]` | `bins`: the `B` rows of this window. Field 2 of a `B` row is the window number. |
| 132 | `        if not bins:` | Tests whether the window has no bin at all. |
| 133 | `            p.append("window %s has no bin" % w[3])` | Adds a problem that names the window. |
| 134 | `            continue` | Continues with the next window. |
| 135 | `        ends, cum = [int(b[4]) for b in bins], [int(b[5]) for b in bins]` | `ends`: the end times of the bins in ns. `cum`: the bytes from the window start to each bin end. |
| 136 | `        if [int(b[3]) for b in bins] != list(range(len(bins))):` | Tests that the bins are numbered 0, 1, 2 and so on, without a hole. |
| 137 | `            p.append("window %s: bin numbers are not 0, 1, 2, ..." % w[3])` | Adds a problem that names the window. |
| 138 | `        if ends != sorted(set(ends)) or ends[0] <= t0 or ends[-1] != t1:` | Tests the bin ends. They must rise strictly. The first one must lie after the window start. The last one must equal the window end. So the bins cover the whole window. |
| 139 | `            p.append("window %s: bin ends do not rise to the end of the window" % w[3])` | Adds a problem that names the window. |
| 140 | `        per_bin = [c - d for c, d in zip(cum, [0] + cum[:-1])]` | `per_bin`: the bytes of each bin alone. It is the difference of two neighbour values of `cum`. |
| 141 | `        if sum(per_bin) != by or min(per_bin) <= 0:` | Tests that the bins sum to the bytes of the window and that every bin holds more than 0 bytes. So no byte is lost or counted twice when a rate is computed per bin. |
| 142 | `            p.append("window %s: the bins sum to %d bytes, the window has %d" % (w[3], sum(per_bin), by))` | Adds a problem with the sum of the bins and the bytes of the window. |
| 143 | `        if any(b % pb for b in per_bin):` | Tests that every bin holds whole passes. |
| 144 | `            p.append("window %s: a bin does not hold whole passes" % w[3])` | Adds a problem that names the window. |
| 145 | `        if len(bins) > 1 and ends[0] - t0 < 10000000:` | When a window has more than one bin, bin 0 must last at least 10000000 ns. That is 10 ms, the requested width of a bin. |
| 146 | `            p.append("window %s: bin 0 is shorter than 10 ms" % w[3])` | Adds a problem that names the window. |
| 147 | `        if clock_times is not None and any(e not in clock_times for e in ends):` | Only with a trace: every bin end must be the time of a clock read of the trace. This proves that a bin closes on a clock read that the window loop makes anyway. The bins add no clock read to the timed loop. |
| 148 | `            p.append("window %s: a bin end is not a clock read of the trace" % w[3])` | Adds a problem that names the window. |
| 149 | `    if len(brows) != sum(1 for b in brows if b[2] in [w[3] for w in targets]):` | Counts the `B` rows whose window number is the number of a target window. Every `B` row of the trial must be one of them. |
| 150 | `        p.append("B rows of a window that is not a target window")` | Adds a problem: a `B` row belongs to a window that is no target window. |
| 151 | `    return p` | Returns the list of problems. |

### Rule `trace_problems`: the events of the trace of one trial (lines 154 to 220)

| Line | Source | Explanation |
|---:|---|---|
| 154 | `def trace_problems(plan_fields, events, wrows, erow):` | Starts the rule `trace_problems`. It checks the order of the events that a run with `--trace` logged for one trial. `events` is a list of pairs: the event name and its time in ns. |
| 155 | `    """TR events [(name, t)] of one trial. The timed sequence may hold clock` | Description text: the events come from the `TR` rows of one trial. The timed sequence may hold clock ... |
| 156 | `    reads and the first kernel call of each window. With count 'read' it also` | Description text: ... reads and the first kernel call of each window. The trace logs only the first call of a window. A new sentence starts: with the count mode `read` it also ... |
| 157 | `    holds a counter read and a CPU clock read between the end clock and the` | Description text: ... holds a counter read and a read of the thread CPU clock between the end clock read and the ... |
| 158 | `    start clock of each boundary of a target window. Nothing else."""` | Description text: ... start clock read at each boundary of a target window. No other event is allowed. |
| 159 | `    exp, reads, p = expected_windows(plan_fields), plan_fields[9] == "read", []` | `exp`: the planned windows. `reads`: true when the count field of the plan line (field 9) is `read`. `p`: the list of problems. |
| 160 | `    names = [e[0] for e in events]` | `names`: the event names in the order of the trace. |
| 161 | `    kf = [i for i, n in enumerate(names) if n.startswith("kernel_first")]` | `kf`: the positions of the events whose name starts with `kernel_first`. The runner logs one such event at the first kernel call of each window. |
| 162 | `    want = ["kernel_first:%s:%d" % (e[0], e[1]) for e in exp]` | `want`: the names that these events must have, one per planned window, for example `kernel_first:prefix:2`. |
| 163 | `    if [names[i] for i in kf] != want:` | Tests that the trace holds exactly these first calls, in the planned order. |
| 164 | `        return ["kernel calls %s, expected %s (a warm-up pass or a lost window)" % ([names[i] for i in kf], want)]` | If not, the rule returns this one problem. The cause can be a kernel call that belongs to no planned window, such as a warm-up pass, or a lost window. |
| 165 | `    start, end = kf[0] - 1, kf[-1] + 1` | `start`: the position directly before the first kernel call. `end`: the position directly after the last event `kernel_first`. |
| 166 | `    while end < len(names) and names[end] == "clock":` | Moves `end` forward over the clock reads that follow. These are the clock reads of the last window. |
| 167 | `        end += 1` | One step of this move. |
| 168 | `    end -= 1` | Steps one position back. `end` is now the last clock read of the last window. It ends the timed sequence. |
| 169 | `    if start < 0 or names[start] != "clock" or end == kf[-1]:` | Tests that a clock read stands directly before the first kernel call, and that at least one clock read follows the first call of the last window. |
| 170 | `        return ["no clock read around the first or the last window"]` | If not, the rule returns this one problem. |
| 171 | `    count_tail = [["count_read", "cpu_clock"], ["cpu_clock"]] if reads else [[]]` | `count_tail`: the event lists that may stand between the end clock read of a window and the start clock read of a target window. With the count mode `read`: a counter read and a CPU clock read, or the CPU clock read alone when the counter group did not open. In every other trial: nothing. |
| 172 | `    ends = []  # index of the end clock of each window` | `ends`: the position of the end clock read of each window, as the comment says. It is empty at the start. |
| 173 | `    for j, i in enumerate(kf):` | Loops over the windows. `j` is the number of the window in the trial. `i` is the position of its first kernel call. |
| 174 | `        if names[i - 1] != "clock":` | Tests that the event directly before the first kernel call is a clock read. So nothing runs between the start time of a window and its first pass. |
| 175 | `            p.append("window %d does not start directly after a clock read" % j)` | Adds a problem that names the window. |
| 176 | `        nxt = kf[j + 1] - 1 if j + 1 < len(kf) else end + 1  # the start clock of the next window` | `nxt`: the position of the start clock read of the next window. For the last window it is the position after the end of the timed sequence. The comment says the same. |
| 177 | `        body = names[i + 1:nxt]` | `body`: the events from the first kernel call of this window, not included, to the start clock read of the next window, not included. |
| 178 | `        tail = []` | `tail`: the events of the boundary after this window. It is empty at the start. |
| 179 | `        while body and body[-1] != "clock":` | As long as `body` does not end with a clock read: |
| 180 | `            tail.insert(0, body.pop())` | Moves the last event of `body` to the front of `tail`. At the end `body` ends with the end clock read of the window, and `tail` holds what the runner did between that read and the next start clock read. |
| 181 | `        if not body or any(n != "clock" for n in body):` | Tests the inside of the window: `body` must hold at least one clock read, and nothing but clock reads. A page read, an output or a counter event inside a window is a problem. |
| 182 | `            p.append("inside window %d: %s" % (j, sorted(set(body) - {"clock"}) or "no clock read"))` | Adds a problem that names the window and the foreign events, or the text `no clock read`. |
| 183 | `        ends.append(i + len(body))` | Stores the position of the end clock read of this window. |
| 184 | `        if j + 1 < len(kf):` | For every window but the last: |
| 185 | `            allowed = count_tail if exp[j + 1][0] == "target" else [[]]` | `allowed`: the lists that may stand between this window and the next one. The counter events are allowed only when the next window is a target window. |
| 186 | `            if tail not in allowed:` | Tests that `tail` is one of the allowed lists. This is the check of the gap. A page read, an output or a counter read that is not allowed between two windows would be found here. A kernel call cannot stand in `tail`. A kernel call that the trace logs outside the plan fails the test of line 163. |
| 187 | `                p.append("between window %d and window %d: %s, allowed %s" % (j, j + 1, tail, allowed))` | Adds a problem with the two window numbers, the events found and the allowed lists. |
| 188 | `        clocks, pb = len(body), exp[j][3]` | `clocks`: the number of clock reads of the window. `pb`: its pass size in bytes. |
| 189 | `        # the window ends at the first clock read at or after its requested duration` | Comment: a window ends at the first clock read at or after its requested duration. |
| 190 | `        if clocks > 1 and events[i + clocks - 1][1] - events[i - 1][1] >= exp[j][4]:` | Tests this stop rule on the times of the trace. The clock read before the last one must lie before the requested end, counted from the start clock read. When it lies at or after the requested end, the window continued after the clock read at which it had to stop. |
| 191 | `            p.append("window %d: runs on after the clock read that passed its requested duration" % j)` | Adds a problem that names the window. |
| 192 | `        if j < len(wrows) and clocks != int(wrows[j][6]) // (pb * max(1, MIB8 // pb)):` | Tests the number of clock reads against the bytes of the `W` row: the bytes divided by the bytes between two clock reads. That is one pass for a pass size of 8 MiB or more. For a smaller pass size it is the largest whole number of passes that fits into 8 MiB. So the runner reads the clock once per group of passes, not more and not less. |
| 193 | `            p.append("window %d: %d clock reads for %s bytes" % (j, clocks, wrows[j][6]))` | Adds a problem with the number of clock reads and the bytes. |
| 194 | `    before = names[:start]` | `before`: the events before the start clock read of the first window. |
| 195 | `    if reads and exp[0][0] == "target":` | With the count mode `read`, when the first window is a target window: |
| 196 | `        if before[-2:] not in (["count_read", "cpu_clock"], ["cpu_clock", "cpu_clock"]):` | The last two events before the timed sequence must be the first counter reading: a counter read and a CPU clock read. When the group did not open they are two CPU clock reads. |
| 197 | `            p.append("no counter read before the first target window")` | Adds a problem: no counter read before the first target window. |
| 198 | `        before = before[:-2] if before[-2:] == ["count_read", "cpu_clock"] else before[:-1]` | Removes that counter reading from `before`. |
| 199 | `    if [n for n in before if n not in ("count_open", "count_close")] != ["output", "page_read", "rusage", "cpu_clock"]:` | Tests the rest of `before`, without the events of a counter open or close. It must be exactly: an output (the `S` row that starts the trial), a page read, a read of the context-switch counts (`rusage`) and a CPU clock read, in this order. |
| 200 | `        p.append("before the timed sequence: %s" % before)` | Adds a problem with the events found. |
| 201 | `    after = names[end + 1:]` | `after`: the events after the end of the timed sequence. |
| 202 | `    if reads:` | With the count mode `read`: |
| 203 | `        if after[:2] not in (["count_read", "cpu_clock"],) and after[:1] != ["cpu_clock"]:` | The first events after the timed sequence must be the last counter reading: a counter read with a CPU clock read, or the CPU clock read alone. |
| 204 | `            p.append("no counter read after the last target window")` | Adds a problem: no counter read after the last target window. |
| 205 | `        after = after[2:] if after[:1] == ["count_read"] else after[1:]` | Removes that reading from `after`. |
| 206 | `    if after != ["cpu_clock", "rusage", "page_read", "output"]:` | Tests the rest: exactly a CPU clock read, a read of the context-switch counts, a page read and an output, in this order. So the page state is read and the rows are printed only after the last window. |
| 207 | `        p.append("after the timed sequence: %s" % after)` | Adds a problem with the events found. |
| 208 | `    if not reads and "count_read" in names:` | In a trial without the count mode `read` the trace must hold no counter read at all. |
| 209 | `        p.append("a counter read in a trial with count %s" % plan_fields[9])` | Adds a problem that names the count mode. |
| 210 | `    # the W rows are the clock reads of the trace, and the gap is the time between two of them` | Comment: the times of the `W` rows are clock reads of the trace, and the gap is the time between two of them. The next lines test this. |
| 211 | `    if len(wrows) == len(kf) and not p:` | Only when the trial has as many `W` rows as the trace has windows, and no problem was found so far: |
| 212 | `        for j, w in enumerate(wrows):` | Loops over the `W` rows. |
| 213 | `            if int(w[7]) != events[kf[j] - 1][1] or int(w[8]) != events[ends[j]][1]:` | The start time of the `W` row must be the time of the clock read before the first kernel call of the window. Its end time must be the time of the end clock read. So the printed times are the times that the timed loop read, and no other clock read. |
| 214 | `                p.append("window %d: the W row does not hold the clock reads of the trace" % j)` | Adds a problem that names the window. |
| 215 | `        g = len(wrows) - int(plan_fields[7])` | `g`: the number of windows before the first target window. |
| 216 | `        if g and erow[6] != str(events[kf[g] - 1][1] - events[ends[g - 1]][1]):` | When such a window exists: `gap_ns` of the `E` row must be the start clock read of target window 0 minus the end clock read of the window before it. |
| 217 | `            p.append("gap_ns %s is not the time between the two clock reads of the trace" % erow[6])` | Adds a problem with the printed value. |
| 218 | `    return p` | Returns the list of problems. |

### Rule on the C source: `SEQ_SOURCE` and `seq_source_problems` (lines 221 to 248)

| Line | Source | Explanation |
|---:|---|---|
| 221 | `# The timed sequence, read from the source and from the machine code. The` | Comment: the next two rules read the timed sequence from the C source and from the machine code. |
| 222 | `# trace holds only what the wrappers log themselves. These two rules do not` | Comment: the trace holds only the events that the wrapper functions of the runner log themselves. A wrapper function here is a small function around the clock read or around the kernel call. |
| 223 | `# depend on that log.` | Comment: the two rules do not depend on that log. So they also find a call that the trace would not show. |
| 224 | `SEQ_SOURCE = {"timed_sequence": {"for": 2, "if": 3, "while": 2, "tcount": 2, "tclock": 2, "tcall": 1},` | `SEQ_SOURCE`: for each C function of the timed path, the names that may stand directly before a `(` in its body, each with its count. This line: `timed_sequence`, the function that runs the windows of one trial. It may hold 2 `for`, 3 `if`, 2 `while`, 2 calls of `tcount` (the counter read), 2 calls of `tclock` (the clock read) and 1 call of `tcall` (the kernel call). |
| 225 | `              "tclock": {"now_ns": 1, "if": 1, "tev_add": 1},` | The entry of `tclock`, the clock read: 1 call of `now_ns` (it reads the clock of Linux), 1 `if` and 1 call of `tev_add` (it adds an event to the trace). |
| 226 | `              "tcall": {"if": 1, "tev_add": 1, "call": 1}}` | The entry of `tcall`, the kernel call: 1 `if`, 1 call of `tev_add` and 1 call of `call`. `call` is the function of the runner that starts a kernel. The last brace ends the dictionary. |
| 227 | `SEQ_ALLOWED = {"clock_gettime", "(indirect)", "tcount", "__stack_chk_fail"}` | `SEQ_ALLOWED`: the only places outside itself to which the machine code of a timed function may branch. `clock_gettime` reads the clock. `(indirect)` means a call through a pointer, which is the kernel call. `tcount` is the counter read of the runner. `__stack_chk_fail` is the function that the compiler calls when the guard value on the stack was overwritten. |
| 230 | `def seq_source_problems(src):` | Starts the rule `seq_source_problems`. It counts the names before a `(` in the source text of the functions of the timed path. |
| 231 | `    """The words before a '(' in timed_sequence(), tclock() and tcall() of bwx8.c:` | Description text: the rule reads the words before a `(` in `timed_sequence()`, `tclock()` and `tcall()` of `bwx8.c`. These are the three entries of `SEQ_SOURCE` (lines 224 to 226). |
| 232 | `    one clock read at each end of a window, one kernel call per pass, the` | Description text: allowed are one clock read at each end of a window, one kernel call per pass, ... |
| 233 | `    counter read at the two places of count 'read', and no other call."""` | Description text: ... the counter read at the two places of the count mode `read`, and no other call. |
| 234 | `    p = []` | `p`: the list of problems. |
| 235 | `    for fn, want in SEQ_SOURCE.items():` | Loops over the entries of `SEQ_SOURCE`: the function name `fn` and its expected counts `want`. |
| 236 | `        m = re.search(r"^(?:__attribute__\(\(noinline\)\) )?static (?:inline )?\w+ %s\([^)]*\)\n\{\n(.*?)^\}\n" % fn, src,` | Searches for the function `fn` in the source. The pattern matches the head of its definition: an optional `__attribute__((noinline))`, then `static`, an optional `inline`, the return type, the name, the arguments, and a line with `{`. Group 1 is the body, up to the first line that holds only `}`. |
| 237 | `                      re.M \| re.S)` | Continues the call of line 236: the flags. With `re.M` the mark `^` matches at each line start. With `re.S` the dot also matches a line break. |
| 238 | `        if not m:` | Tests whether the function was not found. |
| 239 | `            p.append("no function %s" % fn)` | Adds a problem that names the function. |
| 240 | `            continue` | Continues with the next function. |
| 241 | `        got = {}` | `got`: the counts found, empty at the start. |
| 242 | `        for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)):` | Removes the C comments from the body. Then finds every name that stands before a `(`, with optional spaces between them. Such a name is a function call or a keyword such as `if`, `for` and `while`. |
| 243 | `            got[name] = got.get(name, 0) + 1` | Adds 1 to the count of that name. |
| 244 | `        if got != want:` | Tests that the counts found equal the expected counts exactly. An added call in the timed path, for example a second clock read, a page read or a warm-up kernel call, changes a count and is found. |
| 245 | `            p.append("%s holds %s, expected %s" % (fn, sorted(got.items()), sorted(want.items())))` | Adds a problem with the counts found and the expected counts. |
| 246 | `    return p` | Returns the list of problems. |

### Machine-code rule: `seq_targets` and `seq_code_problems` (lines 249 to 274)

| Line | Source | Explanation |
|---:|---|---|
| 249 | `def seq_targets(binary):` | Starts the function `seq_targets`. It reads from the machine code of `binary` where the function `timed_sequence` branches to. |
| 250 | `    """{branch target outside timed_sequence: count} from the machine code (x86-64 or AArch64 objdump text)"""` | Description text: the result is a dictionary from each branch target outside `timed_sequence` to the number of branches to it. The function reads the text that `objdump` prints for x86-64 or for AArch64, the 64-bit Arm instruction set. |
| 251 | `    out = subprocess.run(["objdump", "-d", "--no-show-raw-insn", "--disassemble=timed_sequence", binary],` | Runs the tool `objdump` on the binary. `-d` prints the machine code as instructions. `--no-show-raw-insn` leaves out the bytes of each instruction. `--disassemble=timed_sequence` limits the output to the function `timed_sequence`. |
| 252 | `                         stdout=subprocess.PIPE, universal_newlines=True).stdout` | Continues the call that runs `objdump`: its output is collected as text. |
| 253 | `    t = {}` | `t`: the dictionary of the targets, empty at the start. |
| 254 | `    for line in out.splitlines():` | Loops over the lines of the `objdump` output. |
| 255 | `        f = line.split()` | Splits the line at spaces and tabs into fields. |
| 256 | `        if len(f) < 3 or not re.fullmatch(r"[0-9a-f]+:", f[0]):` | Takes only an instruction line: at least 3 fields, and a first field that is a hex address with a colon. |
| 257 | `            continue` | Skips every other line. |
| 258 | `        if re.search(r"\s(call\|jmp)q?\s+\*", line) or f[1] in ("blr", "br"):` | Tests for a call or a jump through a pointer. On x86-64 the operand of such an instruction starts with `*`. On AArch64 the instructions are `blr` and `br`. |
| 259 | `            name = "(indirect)"` | Such a branch gets the name `(indirect)`. The kernel call is of this kind: the runner calls a kernel through a function pointer. |
| 260 | `        elif re.fullmatch(r"callq?\|jmpq?\|j[a-z]+\|bl\|b\|b\.[a-z]+\|cbn?z\|tbn?z", f[1]) and re.fullmatch(r"<.*>", f[-1]):` | If not: tests for a direct call, jump or branch whose last field is a symbol name in angle brackets. The pattern lists the instruction names of both machines: `call`, `jmp` and the conditional jumps of x86-64, and `bl`, `b`, `b.` with a condition, `cbz`, `cbnz`, `tbz` and `tbnz` of AArch64. |
| 261 | `            name = re.sub(r"\+0x[0-9a-f]+$\|@plt", "", f[-1][1:-1])` | `name`: the symbol name without the angle brackets, without an offset such as `+0x1c` at its end and without the mark `@plt`. That mark shows a call of a library function through the linker table. |
| 262 | `            if name == "timed_sequence":` | Tests whether the target lies inside `timed_sequence` itself. |
| 263 | `                continue` | Skips such a branch: it does not leave the function. |
| 264 | `        else:` | Every other instruction line holds no branch with a named target. |
| 265 | `            continue` | Skips such a line. |
| 266 | `        t[name] = t.get(name, 0) + 1` | Adds 1 to the count of the target. |
| 267 | `    return t` | Returns the dictionary. |
| 270 | `def seq_code_problems(targets):` | Starts the rule `seq_code_problems`. It judges the branch targets that `seq_targets` found for `timed_sequence`. |
| 271 | `    p = ["timed_sequence reaches %s" % n for n in sorted(set(targets) - SEQ_ALLOWED)]` | `p`: one problem for each target that is not in `SEQ_ALLOWED`. A call of an output function or of a page read inside `timed_sequence` is found here, also when the trace does not log it. A helper that the compiler did not put inline shows here too, under its own name. |
| 272 | `    return p + ["timed_sequence has no call of %s" % n for n in ("clock_gettime", "(indirect)") if n not in targets]` | Returns these problems, plus one problem for each of `clock_gettime` and `(indirect)` that is missing. Without the first the function reads no clock. Without the second it calls no kernel. |

### Rule `placement_problems`: the order of pin and memory mapping (lines 275 to 301)

| Line | Source | Explanation |
|---:|---|---|
| 275 | `def placement_problems(lines, cpu, ctl):` | Starts the rule `placement_problems`. It reads the log lines of the preloaded library (line 302) and checks in which order the two threads pin themselves and map memory. `cpu` is the CPU of the worker thread. `ctl` is the CPU of the controlling thread. |
| 276 | `    """Lines 'shim <call> pid=P tid=T <a> <b>' of the preloaded library, in time` | Description text: each log line has the form `shim <call> pid=P tid=T <a> <b>`. The lines stand in time ... |
| 277 | `    order. setaffinity: a = CPUs in the set, b = the first one. mmap: a = bytes.` | Description text: ... order. For `setaffinity`, `a` is the number of CPUs in the set and `b` is the first of them. For `mmap`, `a` is the number of bytes. |
| 278 | `    The controlling thread pins itself to ctl before the worker exists. The` | Description text: the controlling thread must pin itself to `ctl` before the worker thread exists. |
| 279 | `    worker pins itself to cpu before it maps the buffer."""` | Description text: the worker thread must pin itself to `cpu` before it maps the buffer. |
| 280 | `    ev = []` | `ev`: the list of the events, empty at the start. |
| 281 | `    for line in lines:` | Loops over the log lines. |
| 282 | `        f = line.split()` | Splits the line at the spaces into fields. |
| 283 | `        ev.append((f[1], f[3] == "tid=" + f[2][4:], f[3], int(f[4]), int(f[5])))` | Adds one event with five values: the call name, whether the caller is the main thread, the thread id text, and the two numbers. The caller is the main thread when its thread id equals the process id. In the trial mode the main thread is the controlling thread. |
| 284 | `    first_worker = next((i for i, e in enumerate(ev) if not e[1]), None)` | `first_worker`: the position of the first event of a thread that is not the main thread, or `None`. |
| 285 | `    if first_worker is None:` | Tests whether no such event exists. |
| 286 | `        return ["no call of the worker thread"]` | Returns this one problem. |
| 287 | `    p = []` | `p`: the list of problems. |
| 288 | `    if len({e[2] for e in ev}) != 2:` | Tests that exactly 2 threads made calls: the controlling thread and one worker. |
| 289 | `        p.append("%d threads, 2 expected" % len({e[2] for e in ev}))` | Adds a problem with the number of threads. |
| 290 | `    if ("setaffinity", True, 1, ctl) not in [(e[0], e[1], e[3], e[4]) for e in ev[:first_worker]]:` | Tests the controlling thread. Before the first event of the worker it must have made a `setaffinity` call with exactly 1 CPU in the set, the CPU `ctl`. So the controlling thread is pinned to its own CPU before the worker starts, and it cannot run on the CPU of the worker. |
| 291 | `        p.append("the controlling thread did not pin itself to CPU %d before the worker started" % ctl)` | Adds a problem that names the CPU `ctl`. |
| 292 | `    w = [e for e in ev if not e[1]]` | `w`: the events of the worker thread. |
| 293 | `    if (w[0][0], w[0][3], w[0][4]) != ("setaffinity", 1, cpu):` | Tests that the first logged call of the worker is its pin: `setaffinity` with 1 CPU, the CPU `cpu`. |
| 294 | `        p.append("the first call of the worker is %s %d %d, not its pin to CPU %d" % (w[0][0], w[0][3], w[0][4], cpu))` | Adds a problem with the call found. |
| 295 | `    if not any(e[0] == "mmap" and e[3] >= MIB8 for e in w[1:]):` | Tests that a later call of the worker is an `mmap` of at least 8 MiB. That is the buffer. So the worker is pinned before it maps the buffer. The first touch of the buffer then happens on the CPU that later reads it. |
| 296 | `        p.append("the worker did not map the buffer after its pin")` | Adds a problem: the worker did not map the buffer after its pin. |
| 297 | `    if any(e[0] == "mmap" and e[1] and e[3] >= MIB8 for e in ev):` | Tests that the main thread made no `mmap` of 8 MiB or more. The controlling thread must not own a buffer. |
| 298 | `        p.append("the controlling thread mapped a buffer")` | Adds a problem. |
| 299 | `    return p` | Returns the list of problems. |

### `SHIM`: the C source of the library that logs the calls (lines 302 to 341)

| Line | Source | Explanation |
|---:|---|---|
| 302 | `SHIM = r"""` | `SHIM`: the C source text of a small library, as a raw text that ends in line 340. A test builds it and loads it into the runner with the variable `LD_PRELOAD`. Its functions then replace the C library functions of the same name. Each one logs the call and passes it on to Linux. |
| 303 | `#define _GNU_SOURCE` | C text: `_GNU_SOURCE` switches on the Linux extensions of the header files, such as the macros for CPU sets. |
| 304 | `#include <errno.h>` | C text: includes `errno.h`, for the error number `errno` and the value `EINVAL`. |
| 305 | `#include <sched.h>` | C text: includes `sched.h`, for the type and the macros of a CPU set. |
| 306 | `#include <stdio.h>` | C text: includes `stdio.h`, for `snprintf`. |
| 307 | `#include <stdlib.h>` | C text: includes `stdlib.h`, for `getenv`. |
| 308 | `#include <sys/mman.h>` | C text: includes `sys/mman.h`, for the declarations of `mmap` and `madvise`. |
| 309 | `#include <sys/syscall.h>` | C text: includes `sys/syscall.h`, for the numbers of the system calls. |
| 310 | `#include <unistd.h>` | C text: includes `unistd.h`, for `write`, `getpid` and `syscall`. |
| 311 | `static void note(const char *what, long a, long b)` | C text: starts the function `note`. It writes one log line for the call named `what` with the two numbers `a` and `b`. |
| 312 | `{` | C text: opens the body of `note`. |
| 313 | `    char buf[128];` | C text: `buf`: room for one log line of up to 127 characters. |
| 314 | `    int n = snprintf(buf, sizeof buf, "shim %s pid=%d tid=%ld %ld %ld\n", what, (int)getpid(), syscall(SYS_gettid), a, b);` | C text: builds the line `shim <call> pid=<process id> tid=<thread id> <a> <b>`. `syscall(SYS_gettid)` asks Linux for the id of the calling thread. `n` is the length of the line. |
| 315 | `    if (write(2, buf, (size_t)n) < 0)` | C text: writes the line to the error output (file number 2) with one `write` call. |
| 316 | `        return;` | C text: returns when the `write` failed. The function ends directly after this line in both cases. |
| 317 | `}` | C text: ends the function `note`. |
| 318 | `int sched_setaffinity(pid_t pid, size_t len, const cpu_set_t *set)` | C text: starts the replacement of `sched_setaffinity`, the call that sets the CPUs on which a thread may run. The runner pins its threads with it. |
| 319 | `{` | C text: opens the body. |
| 320 | `    long first = -1;` | C text: `first`: the lowest CPU of the set. It is -1 as long as none is found. |
| 321 | `    for (long c = 0; c < 8 * (long)len && first < 0; c++)` | C text: loops over the CPU numbers that a set of `len` bytes can hold (8 per byte), until a CPU is found. |
| 322 | `        if (CPU_ISSET_S(c, len, set))` | C text: tests whether the CPU `c` is in the set. |
| 323 | `            first = c;` | C text: keeps it as `first`. |
| 324 | `    note("setaffinity", CPU_COUNT_S(len, set), first);` | C text: logs `setaffinity` with the number of CPUs in the set and the first CPU. |
| 325 | `    return (int)syscall(SYS_sched_setaffinity, pid, len, set);` | C text: passes the call on to Linux with the system call of the same name and returns its result. So the pin still happens. |
| 326 | `}` | C text: ends the replacement of `sched_setaffinity`. |
| 327 | `void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off)` | C text: starts the replacement of `mmap`, the call that asks Linux for a new range of memory. |
| 328 | `{` | C text: opens the body. |
| 329 | `    note("mmap", (long)len, 0);` | C text: logs `mmap` with the number of bytes. The second number is 0. |
| 330 | `    return (void *)syscall(SYS_mmap, addr, len, prot, flags, fd, off);` | C text: passes the call on to Linux and returns the address that Linux gave. |
| 331 | `}` | C text: ends the replacement of `mmap`. |
| 332 | `int madvise(void *addr, size_t len, int advice)` | C text: starts the replacement of `madvise`. The runner asks Linux for huge pages with this call. |
| 333 | `{` | C text: opens the body. |
| 334 | `    if (getenv("SHIM_MADVISE_FAIL")) {` | C text: tests whether the environment variable `SHIM_MADVISE_FAIL` is set. |
| 335 | `        errno = EINVAL;` | C text: sets the error number to `EINVAL`, the value for an invalid argument. |
| 336 | `        return -1;` | C text: returns -1. The runner sees a failed request. The test of line 705 uses this to check how the runner reports the failure. |
| 337 | `    }` | C text: ends the `if`. |
| 338 | `    return (int)syscall(SYS_madvise, addr, len, advice);` | C text: if the variable is not set, passes the call on to Linux and returns its result. |
| 339 | `}` | C text: ends the replacement of `madvise`. |
| 340 | `"""` | Ends the text `SHIM`. |

### `MUTANTS`: one defect each in a copy of the runner source (lines 342 to 376)

| Line | Source | Explanation |
|---:|---|---|
| 342 | `# One defect each in a copy of bwx8.c: [(text of bwx8.c, changed text)].` | Comment: each entry of the table below is one defect in a copy of `bwx8.c`. A defect is a list of changes. Each change is a pair: the text of `bwx8.c` to find, and the changed text. |
| 343 | `MUTANTS = {` | `MUTANTS`: the table of the defects. The key is the name of the defect. The names of the checks print it. The value is the list of the changes of that defect. |
| 344 | `    "a warm-up pass before the first target window":` | Defect: a warm-up pass before the first target window. |
| 345 | `        [("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) call(&kernels[x->k], "` | The change, as a pair. The text to find is the line with the start clock read of a window, `t0 = tclock(w);`, and the first word of the line after it. The changed text starts here: before that clock read it adds one kernel call when the window is target window 0. |
| 346 | `          "&w->t, 0, x->size, 0, sink);\n        t0 = tclock(w);\n        next_bin")],` | Continues the changed text: the arguments of the added kernel call, then the original text. The added call is a warm-up pass over the range of the window. It calls `call` directly and not `tcall`, so the trace does not log it. |
| 347 | `    "a page read and an output flush before the first target window":` | Defect: a page read and an output flush before the first target window. |
| 348 | `        [("        t0 = tclock(w);\n        next_bin", "        if (x->phase == PH_TARGET && x->widx == 0) { long long vmx[4]; "` | The change, at the same place: before the start clock read of target window 0 it adds a block with an array `vmx` ... |
| 349 | `          "read_vmstat(vmx); fflush(stdout); }\n        t0 = tclock(w);\n        next_bin")],` | Continues the changed text: the block reads four counters of the file `/proc/vmstat` (`read_vmstat`) and flushes the output (`fflush(stdout)`). The design forbids a page read and an output between two windows. |
| 350 | `    "an added clock read in a window with bins":` | Defect: an added clock read in a window with bins. |
| 351 | `        [("            t1 = tclock(w);\n", "            t1 = tclock(w);\n            if (x->bin) (void)now_ns();\n")],` | The change: after the clock read that follows a group of passes, `t1 = tclock(w);`, it adds a second clock read with `now_ns()` when the window has bins. That read does not go through `tclock`, so the trace does not log it. |
| 352 | `    "the two context-switch counts exchanged in the E row":` | Defect: the `E` row prints the two context-switch counts in exchanged fields. |
| 353 | `        [("r->nvcsw[1] - r->nvcsw[0], r->nivcsw[1] - r->nivcsw[0]", "r->nivcsw[1] - r->nivcsw[0], r->nvcsw[1] - r->nvcsw[0]")],` | The change: the two arguments of the `printf` call are exchanged. `nvcsw` counts the voluntary context switches, in which the thread gave up the CPU. `nivcsw` counts the involuntary ones, in which Linux took the CPU away. |
| 354 | `    "wall time printed as cpu_ns":` | Defect: the field `cpu_ns` of the `E` row holds the wall time. |
| 355 | `        [("(unsigned long long)(r->cpu[1] - r->cpu[0]));", "(unsigned long long)(r->win[r->nw - 1].t_end - r->win[0].t_start));")],` | The change: the difference of the two CPU clock reads is replaced by the end of the last window minus the start of the first window. |
| 356 | `    "the pre snapshot printed in the post P row":` | Defect: the `P` row `post` prints the page state that was read before the timed sequence. |
| 357 | `        [('print_p8(i, "post", &r->pg[1], r->vm[1]);', 'print_p8(i, "post", &r->pg[0], r->vm[0]);')],` | The change: the call that prints the row `post` gets the first snapshot (`pg[0]`, `vm[0]`) in place of the second one. |
| 358 | `    "C rows that hold the readings, not their differences":` | Defect: a `C` row holds the counter readings at the end of its window, and not their change over the window. |
| 359 | `        [("(unsigned long long)(c1->enabled - c0->enabled)", "(unsigned long long)(c1->enabled)"),` | Change 1 of 3: the enabled time of the counter group is printed as the second reading alone, without the subtraction. |
| 360 | `         ("(unsigned long long)(c1->running - c0->running));\n        else", "(unsigned long long)(c1->running));\n        else"),` | Change 2 of 3: the same for the running time. The text to find also holds the line break and the `else` that follow. |
| 361 | `         ("(unsigned long long)(c1->val[at] - c0->val[at]));", "(unsigned long long)(c1->val[at]));")],` | Change 3 of 3: the same for the count of each event. The last bracket ends the list of this defect. |
| 362 | `    "no X row count_multiplexed":` | Defect: the row `X,<trial>,count_multiplexed` is never printed. An `X` row reports a failure. This one reports a counter that ran for less time than it was enabled. |
| 363 | `        [("        if (m >= 0)\n", "        if (0 && m >= 0)\n")],` | The change: the condition `m >= 0` gets `0 &&` in front, so it is never true. |
| 364 | `    "no X row sink":` | Defect: the row `X,<trial>,sink` is never printed. It reports that the old read kernel did not leave the sum of its range in the result variable. |
| 365 | `        [("    if (r->sink_ok == 0)\n        printf(\"X", "    if (0)\n        printf(\"X")],` | The change: the condition `r->sink_ok == 0` becomes `0`. |
| 366 | `    "no X row coverage_na":` | Defect: the row `X,<trial>,coverage_na` is never printed. It reports that the huge-page state of the buffer could not be read. |
| 367 | `        [("    if (r->pg[0].kb_huge < 0 \|\| r->pg[1].kb_huge < 0)\n", "    if (0)\n")],` | The change: the condition on the two snapshots becomes `0`. |
| 368 | `    # gcc itself turns malloc + memset into calloc, which writes no page of a fresh block` | Comment: `gcc` itself turns the pair `malloc` and `memset` into `calloc`. `calloc` writes no page of a fresh block. So without a store of its own the runner would touch the pages of its records first during a trial. |
| 369 | `    "record storage without the store to every page before the first trial":` | Defect: the storage of the records is not written before the first trial. |
| 370 | `        [("        ((volatile char *)mem)[at] = 0;\n", "        ;\n"), ("    ((volatile char *)mem)[recsz.bytes - 1] = 0;\n", "")],` | Two changes: the store of one byte to every page becomes an empty statement, and the store to the last byte is removed. |
| 371 | `}` | Ends the table `MUTANTS`. |
| 372 | `SEQ_MUTANTS = list(MUTANTS)[:3]` | `SEQ_MUTANTS`: the names of the first 3 entries of the table. A Python dictionary keeps the order in which its entries were written. These are the three defects of `timed_sequence`. |
| 373 | `ROW_MUTANTS = list(MUTANTS)[3:10]` | `ROW_MUTANTS`: the names of the entries 4 to 10, the 7 defects of the output rows. |
| 374 | `TOUCH_MUTANT = list(MUTANTS)[10]` | `TOUCH_MUTANT`: the name of entry 11, the record storage without the first store. |

### `mutant_source` and `mutant_build`: a copy of the runner with one defect (lines 377 to 401)

| Line | Source | Explanation |
|---:|---|---|
| 377 | `def mutant_source(name):` | Starts the function `mutant_source`. It returns the source text of the runner with the defect `name`. |
| 378 | `    """bwx8.c with the defect 'name', or None if a text to change is not there exactly once"""` | Description text: the result is `bwx8.c` with the defect, or `None` when a text to change does not stand there exactly once. |
| 379 | `    with open(os.path.join(HERE, "bwx8.c")) as f:` | Opens `bwx8.c` in the folder of this file. |
| 380 | `        src = f.read()` | `src`: the whole source text. |
| 381 | `    for good, bad in MUTANTS[name]:` | Loops over the changes of the defect. `good` is the text to find, and `bad` is the changed text. |
| 382 | `        if src.count(good) != 1:` | Tests whether the text to find does not stand exactly once in the whole source. So a defect is never put in at two places. |
| 383 | `            return None` | Returns `None`. The checks that use the defect then fail. So a text of the table that the source no longer holds is noticed. |
| 384 | `        src = src.replace(good, bad)` | Replaces the text by the changed text. |
| 385 | `    return src` | Returns the changed text. |
| 388 | `def mutant_build(name, tag):` | Starts the function `mutant_build`. It compiles the runner with the defect `name`. `tag` is a short word for the folder name. |
| 389 | `    """builds the mutant in its own folder; returns the path of the binary, or None"""` | Description text: the defect copy is built in its own folder. The result is the path of the binary, or `None`. |
| 390 | `    d = os.path.join(E.tmp, "mutant-" + tag)` | `d`: the folder `mutant-` plus `tag` in the temporary folder. |
| 391 | `    os.makedirs(d, exist_ok=True)` | Creates the folder. No error when it exists. |
| 392 | `    src = mutant_source(name)` | `src`: the source text with the defect. |
| 393 | `    if src is None:` | Tests whether the defect could not be put in. |
| 394 | `        return None` | Returns `None`. |
| 395 | `    with open(os.path.join(d, "bwx8.c"), "w") as f:` | Opens the file `bwx8.c` in that folder for writing. |
| 396 | `        f.write(src)` | Writes the changed source text. |
| 397 | `    shutil.copy(os.path.join(HERE, "bwx8_selftest.c"), d)` | Copies `bwx8_selftest.c` into the folder. `bwx8.c` includes that file, so the compiler needs it there. |
| 398 | `    r = subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx8"), os.path.join(d, "bwx8.c")])` | Compiles the copy with `gcc` and the flags `CFLAGS` into the binary `bwx8` of that folder. |
| 399 | `    return os.path.join(d, "bwx8") if r.returncode == 0 else None` | Returns the path of the binary when `gcc` ended with exit status 0, and `None` if not. |

### Running the runner: `write_plan`, `run`, `trial`, `fnv1a64`, `plan_lines`, `GOOD` (lines 402 to 448)

| Line | Source | Explanation |
|---:|---|---|
| 402 | `# ---- running bwx8 ----` | Comment: the helpers that start `bwx8` follow. |
| 404 | `class Env:` | Starts the class `Env`. It has no content of its own. It only carries values. |
| 405 | `    pass` | The empty body of the class. |
| 408 | `E = Env()` | `E`: the one object of that class. `main` stores in it the settings that all tests share, such as the temporary folder (`E.tmp`), the path of the binary (`E.bin`) and the worker CPU (`E.cpu`). |
| 411 | `def write_plan(name, lines, cpu=None, nbytes=MIB8, head1=HEAD1, head3=HEAD3, head2=None):` | Starts the function `write_plan`. It writes a plan file with the trial lines `lines` and returns its path. A plan file lists the trials that the runner must run. The other arguments replace single header values, for the tests of bad plans. |
| 412 | `    cpu = E.cpu if cpu is None else cpu` | `cpu`: the worker CPU of the tests, unless the caller gave another one. |
| 413 | `    if head2 is None:` | Tests whether the caller gave no second header line. |
| 414 | `        head2 = "# step=T session=1 cpu=%d bytes=%d proc=0 seed=1 test=1" % (cpu, nbytes)` | `head2`: the standard second header line. It holds pairs of the form `key=value`: the step name `T`, session 1, the worker CPU, the buffer size in bytes, process 0, seed 1 and `test=1`. The runner requires that `cpu` and `bytes` equal its options. |
| 415 | `    path = os.path.join(E.tmp, name + ".plan")` | `path`: the file `name` with the ending `.plan` in the temporary folder. |
| 416 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 417 | `        f.write("\n".join([head1, head2, head3] + lines) + "\n")` | Writes the three header lines and the trial lines, each ended by a line break. |
| 418 | `    return path` | Returns the path. |
| 421 | `def run(args, env_add=None, binary=None):` | Starts the function `run`. It starts a binary with the arguments `args` and waits for its end. `env_add` holds added environment variables. `binary` is the program to start, when it is not the runner under test. |
| 422 | `    env = {k: v for k, v in os.environ.items() if not k.startswith("BWX_")}` | `env`: the environment of the test without every variable whose name starts with `BWX_`. So a counter setting in the environment of the caller cannot change a test. |
| 423 | `    env.update(env_add or {})` | Adds the variables of `env_add`, if any. |
| 424 | `    r = subprocess.run([binary or E.bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,` | Starts the binary (`E.bin` unless `binary` is given) and collects its standard output and its error output apart. |
| 425 | `                       universal_newlines=True, timeout=120)` | Continues the call of line 424: the outputs are returned as text. `timeout=120`: when the program runs longer than 120 s, the call ends with an error. |
| 426 | `    return r.returncode, r.stdout, r.stderr` | Returns three values: the exit status, the standard output and the error output. |
| 429 | `def trial(plan, extra=None, cpu=None, nbytes="8M", env_add=None):` | Starts the function `trial`. It runs the runner in the trial mode on one plan file. |
| 430 | `    return run(["--trial", "--cpus", str(E.cpu if cpu is None else cpu), "--bytes", nbytes, "--plan", plan] + (extra or []),` | Returns the result of `run`, called with `--trial`, `--cpus` and one CPU (the worker CPU of the tests unless `cpu` is given), `--bytes` and the buffer size (`8M` means 8 MiB), `--plan` and the path, and the added arguments of `extra`. |
| 431 | `               env_add)` | Continues the call of line 430: the added environment variables. |
| 434 | `def fnv1a64(data):` | Starts the function `fnv1a64`. It computes the FNV-1a hash of 64 bits over a sequence of bytes. The runner prints the same hash of its plan file. |
| 435 | `    h = 14695981039346656037` | `h`: the start value of that hash. |
| 436 | `    for b in data:` | Loops over the bytes. |
| 437 | `        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF` | One step: `h` is combined with the byte by exclusive or, multiplied by the constant 1099511628211 and cut to the low 64 bits. |
| 438 | `    return "%016x" % h` | Returns the hash as 16 hex digits. |
| 441 | `def plan_lines(path):` | Starts the function `plan_lines`. It reads the trial lines of a plan file. |
| 442 | `    with open(path) as f:` | Opens the plan file. |
| 443 | `        return [line.split(" ") for line in f.read().splitlines()[3:]]` | Returns the lines after the three header lines, each one split at single spaces into its 11 fields. |
| 446 | `GOOD = "0 a 1 - oldread@8M:8 - oldread@8M 1 5 closed 0"` | `GOOD`: a valid trial line that many tests use. Its fields: trial 0, the condition label `a`, repeat 1, no previous activity, a prefix of the old read kernel on 8 MiB for 8 ms (4 windows of 2 ms), no predecessor, the target `oldread` on 8 MiB, 1 target window of 5 ms, the count mode `closed` (no counters) and no bins. |

### `test_bad_plans`, checks a: a plan with a defect is refused (lines 449 to 504)

| Line | Source | Explanation |
|---:|---|---|
| 449 | `def test_bad_plans():` | Starts the test `test_bad_plans`. The names of its checks start with `a:`. |
| 450 | `    """(a) every defect gives status 2, a message, and no row"""` | Description text: every defect must give exit status 2, a message and no row. |
| 451 | `    rc, out, _ = trial(write_plan("good", [GOOD]))` | Runs the control: a plan that holds only the line `GOOD`. `rc` is the exit status. `out` is the standard output. |
| 452 | `    check("a: the good control plan runs with status 0", rc == 0 and "\nE,0," in out, rc)` | Check: the good plan runs with status 0 and prints the `E` row of trial 0. Without this control the next checks could pass for a wrong reason, for example with a runner that refuses every plan. |
| 454 | `    def bad(name, line=None, **kw):` | Starts the inner function `bad`. It runs one plan with a defect and checks the result. `line` is a bad trial line. `kw` holds header values to replace. |
| 455 | `        plan = write_plan("bad", [GOOD] if line is None else [GOOD.replace("0 a", "0 first"), line], **kw)` | Writes the plan. With a bad trial line: the good line with the label `first`, then the bad line as trial 1. Without one: the good line alone, under the changed header. |
| 456 | `        rc, out, err = trial(plan)` | Runs the plan in the trial mode. |
| 457 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. The design asks that a malformed plan fails before any work starts. The empty output proves that the runner printed no row. So no half result of a bad plan can reach the analysis. |
| 459 | `    t = "1 b 1 - oldread@8M:8 - %s 1 5 closed 0"` | `t`: a pattern for trial 1 in which only the target field changes. |
| 460 | `    bad("unknown kernel", t % "newread@8M")` | Bad plan: a target kernel with a name that the runner does not know. |
| 461 | `    bad("write kernel as target", t % "write@8M")` | Bad plan: a write kernel as the target. The trial mode accepts read kernels only. |
| 462 | `    bad("copy kernel as target", t % "copy@8M")` | Bad plan: a copy kernel as the target. |
| 463 | `    bad("write kernel as prefix", "1 b 1 - oldwrite@8M:8 - read@8M 1 5 closed 0")` | Bad plan: a write kernel, `oldwrite`, as the prefix. |
| 464 | `    bad("copy kernel as predecessor", "1 b 1 - - asmcopy@8M:8 read@8M 1 5 closed 0")` | Bad plan: a copy kernel, `asmcopy`, as the predecessor. |
| 465 | `    bad("size above --bytes", t % "read@16M")` | Bad plan: a target size of 16 MiB. That is above the buffer size of 8 MiB that `--bytes` gives. |
| 466 | `    bad("size not a multiple of 256", t % "read@1000")` | Bad plan: a size of 1000 bytes, which is no multiple of 256. The read kernels handle 256 bytes per loop pass. |
| 467 | `    bad("size 0", t % "read@0")` | Bad plan: a size of 0. |
| 468 | `    bad("size with a fraction", t % "read@1.5M")` | Bad plan: a size with a fraction, `1.5M`. |
| 469 | `    bad("target with a duration", t % "read@8M:5")` | Bad plan: a target with a duration, `read@8M:5`. The duration of the target windows comes from the field `win_ms`. |
| 470 | `    bad("prefix without a duration", "1 b 1 - oldread@8M - read@8M 1 5 closed 0")` | Bad plan: a prefix without a duration. |
| 471 | `    bad("pfx ms not a multiple of 4", "1 b 1 - oldread@8M:42 - read@8M 1 5 closed 0")` | Bad plan: a prefix duration of 42 ms, which is no multiple of 4. The runner records the prefix as 4 windows of equal requested length. |
| 472 | `    bad("pred ms 0", "1 b 1 - - read@8M:0 read@8M 1 5 closed 0")` | Bad plan: a predecessor duration of 0 ms. |
| 473 | `    bad("bad count word", "1 b 1 - - - read@8M 1 5 maybe 0")` | Bad plan: the count word `maybe`. Allowed are `closed`, `open` and `read`. |
| 474 | `    bad("bins 2", "1 b 1 - - - read@8M 1 5 closed 2")` | Bad plan: the bins value 2. Allowed are 0 and 1. |
| 475 | `    bad("nwin 0", "1 b 1 - - - read@8M 0 5 closed 0")` | Bad plan: 0 target windows. |
| 476 | `    bad("nwin 4097", "1 b 1 - - - read@8M 4097 5 closed 0")` | Bad plan: 4097 target windows. The limit is 4096. |
| 477 | `    bad("win_ms 0", "1 b 1 - - - read@8M 1 0 closed 0")` | Bad plan: a window duration of 0 ms. |
| 478 | `    bad("rep 5", "1 b 5 - - - read@8M 1 5 closed 0")` | Bad plan: the repeat number 5. Allowed are 1 to 4. |
| 479 | `    bad("trial number out of order", "2 b 1 - - - read@8M 1 5 closed 0")` | Bad plan: trial number 2 directly after trial 0. The trial numbers must be 0, 1, 2 and so on. |
| 480 | `    bad("10 fields", "1 b 1 - - - read@8M 1 5 closed")` | Bad plan: a trial line with 10 fields. It needs 11. |
| 481 | `    bad("12 fields", "1 b 1 - - - read@8M 1 5 closed 0 0")` | Bad plan: a trial line with 12 fields. |
| 482 | `    bad("two spaces between fields", "1 b 1 -  - - read@8M 1 5 closed 0")` | Bad plan: two spaces between two fields. |
| 483 | `    bad("comma in cond", "1 b,c 1 - - - read@8M 1 5 closed 0")` | Bad plan: a comma in the condition label. The label goes into an output row with comma-separated fields. A comma in it would shift the fields. |
| 484 | `    bad("empty line in the plan", "")` | Bad plan: an empty line in the plan. |
| 485 | `    # Record storage above the bound (design: "Bound its size"). The plan below needs 23.6 GB of bins. The address` | Comment: the next case is record storage above its bound. The design says of the storage for the output records: "Bound its size". By the comment the plan below needs 23.6 GB of bins. |
| 486 | `    # space limit keeps a runner without the bound from writing that much memory on this machine.` | Comment: the test limits the address space of the process. So a runner without the bound cannot write that much memory on the machine of the test. |
| 487 | `    plan = write_plan("bad", [GOOD.replace("0 a", "0 first"), "1 b 1 - - - oldread@8M 4096 3600000 closed 1"])` | Writes the plan: the good line, then a trial 1 with 4096 target windows of 3600000 ms (1 hour) each, with bins. One bin per 10 ms of all these windows needs far more than the bound of 256 MiB. |
| 488 | `    r = subprocess.run([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=subprocess.PIPE,` | Starts the runner on this plan directly, without the helper `run`. The test needs this to set a limit for the new process. |
| 489 | `                       stderr=subprocess.PIPE, universal_newlines=True, timeout=120,` | Continues the call of line 488: the outputs are collected as text, and the run may last 120 s at most. |
| 490 | `                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30)))` | Continues the call: `preexec_fn` runs in the new process before the runner starts. It limits the address space of the process to 4 GiB (`RLIMIT_AS`, as soft and as hard limit). |
| 491 | `    check("a: status 2, no row and a plan message that names line 5: record storage above the bound of 256 MiB",` | Check: the runner refuses the plan with status 2 and no row. Its message must start with `bad plan` and name the fifth text line of the plan file, which is the bad trial line. |
| 492 | `          r.returncode == 2 and r.stdout == "" and r.stderr.startswith("bad plan") and "line 5:" in r.stderr,` | Continues the check: the condition on the exit status, the standard output and the two parts of the message. |
| 493 | `          "rc=%s out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:160]))` | Continues the check: the detail that a failure prints. |
| 494 | `    bad("wrong header line 1", head1="# bwx8-plan v2")` | Bad plan: a first header line with `v2` in place of `v1`. |
| 495 | `    bad("wrong header line 3", head3=HEAD3.replace("win_ms count", "count win_ms"))` | Bad plan: a third header line in which the column names `win_ms` and `count` are exchanged. |
| 496 | `    bad("plan bytes differ from --bytes", head2="# step=T cpu=%d bytes=%d" % (E.cpu, MIB8 // 2))` | Bad plan: the header gives 4 MiB as `bytes`, and the option `--bytes` gives 8 MiB. A plan that was made for another buffer size must not run. |
| 497 | `    bad("plan cpu differs from --cpus", head2="# step=T cpu=%d bytes=%d" % (E.cpu2, MIB8))` | Bad plan: the header names another CPU (`E.cpu2`) than the option `--cpus`. A plan that was made for another CPU must not run. |
| 498 | `    bad("plan without bytes=", head2="# step=T cpu=%d" % E.cpu)` | Bad plan: a header without the pair `bytes=`. |
| 499 | `    bad("header pair without =", head2="# step cpu=%d bytes=%d" % (E.cpu, MIB8))` | Bad plan: a header word without `=`, the word `step`. |
| 500 | `    with open(os.path.join(E.tmp, "empty.plan"), "w") as f:` | Opens the file `empty.plan` in the temporary folder for writing. |
| 501 | `        f.write("\n".join([HEAD1, "# cpu=%d bytes=%d" % (E.cpu, MIB8), HEAD3]) + "\n")` | Writes the three header lines and no trial line. |
| 502 | `    rc, out, err = trial(os.path.join(E.tmp, "empty.plan"))` | Runs this plan in the trial mode. |
| 503 | `    check("a: status 2 and no row: plan without a trial", rc == 2 and out == "" and err.strip() != "", rc)` | Check: a plan without a trial gives status 2, no row and a message. |

### `test_bad_plans`, checks a: bad options are refused (lines 505 to 537)

| Line | Source | Explanation |
|---:|---|---|
| 505 | `    good = write_plan("good", [GOOD])` | `good`: a plan file with the line `GOOD`, for the checks of the options. |
| 507 | `    def bad_opt(name, args, env_add=None):` | Starts the inner function `bad_opt`. It starts the runner with the arguments `args` and checks that the runner refuses them. |
| 508 | `        rc, out, err = run(args, env_add)` | Runs the runner. |
| 509 | `        check("a: status 2 and no row: " + name, rc == 2 and out == "" and err.strip() != "", "rc=%s out=%r err=%r" % (rc, out[:80], err[:120]))` | Check: the exit status is 2, the standard output is empty and the error output holds a message. |
| 511 | `    base = ["--trial", "--bytes", "8M", "--plan", good]` | `base`: the arguments of a valid trial run without `--cpus`. |
| 512 | `    bad_opt("worker CPU equal to the control CPU", base + ["--cpus", str(E.cpu), "--ctl-cpu", str(E.cpu)])` | Bad options: the worker CPU is also the CPU of the controlling thread (`--ctl-cpu`). The two threads would share one CPU, and the controlling thread could take time from the worker. |
| 513 | `    bad_opt("worker CPU equal to the default control CPU 0", ["--trial", "--bytes", "8M", "--cpus", "0", "--plan",` | Bad options: the worker CPU is CPU 0. That is the CPU of the controlling thread when `--ctl-cpu` is not given. |
| 514 | `                                                               write_plan("cpu0", [GOOD], cpu=0)])` | Continues the call of line 513: the plan is written for CPU 0, so only the CPU clash can be the reason of the refusal. |
| 515 | `    bad_opt("CPU above 119", ["--trial", "--bytes", "8M", "--cpus", "120", "--plan", write_plan("cpu120", [GOOD], cpu=120)])` | Bad options: CPU 120 as the worker CPU. The runner accepts the CPUs 0 to 119 only. |
| 516 | `    bad_opt("control CPU above 119", base + ["--cpus", str(E.cpu), "--ctl-cpu", "120"])` | Bad options: CPU 120 as the CPU of the controlling thread. |
| 517 | `    bad_opt("two CPUs", base + ["--cpus", "%d,%d" % (E.cpu, E.cpu2)])` | Bad options: two CPUs in `--cpus`. The trial mode has exactly one worker. |
| 518 | `    bad_opt("no --cpus", base)` | Bad options: no `--cpus`. |
| 519 | `    bad_opt("no --bytes", ["--trial", "--cpus", str(E.cpu), "--plan", good])` | Bad options: no `--bytes`. |
| 520 | `    bad_opt("no --plan", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M"])` | Bad options: no `--plan`. |
| 521 | `    bad_opt("plan file that does not exist", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", good + ".none"])` | Bad options: a plan file that does not exist. |
| 522 | `    bad_opt("unknown option", base + ["--cpus", str(E.cpu), "--warmup"])` | Bad options: the unknown option `--warmup`. |
| 523 | `    bad_opt("--seq together with --trial", base + ["--cpus", str(E.cpu), "--seq", "read"])` | Bad options: `--seq` together with `--trial`. `--seq` belongs to the interval mode, the other mode of the runner. |
| 524 | `    if E.absent is not None:` | Tests whether a CPU from 0 to 119 exists that the test process may not use (`E.absent`). |
| 525 | `        bad_opt("worker CPU outside the allowed set of the process",` | Bad options: that CPU as the worker CPU. The runner must refuse a CPU outside the allowed set of the process before it starts any work. |
| 526 | `                ["--trial", "--bytes", "8M", "--cpus", str(E.absent), "--plan", write_plan("absent", [GOOD], cpu=E.absent)])` | Continues the call of line 525: the arguments, with a plan written for that CPU. |
| 527 | `    else:` | If no such CPU exists: |
| 528 | `        check("a: worker CPU outside the allowed set (no such CPU from 0 to 119 on this machine: NOT RUN)", False)` | Records a failed check whose name holds `NOT RUN`. So a case that this machine cannot test counts as a failure of the test file, and the output shows it. |
| 529 | `    counted = write_plan("counted", [GOOD, "1 b 1 - - - read@8M 1 5 open 0"])` | `counted`: a plan with the good line and a trial 1 with the count mode `open`. |
| 530 | `    bad_opt("count open without counter settings", ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted])` | Bad options: a plan with a counted trial and no counter settings. |
| 531 | `    bad_opt("count open with a PMU type and no event",` | Bad options: a counted trial with a PMU type and no event list. The PMU type is the number by which Linux names a group of counters. |
| 532 | `            ["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted, "--pmu-type", "1"])` | Continues the call of line 531: the arguments, with `--pmu-type 1`. |
| 533 | `    rc, out, _ = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", counted],` | Runs the same plan with the counter settings in the environment. |
| 534 | `                     {"BWX_PMU_TYPE": "1", "BWX_EVENTS": "task_clock=1"})` | Continues the call of line 533: `BWX_PMU_TYPE=1` and `BWX_EVENTS=task_clock=1`. |
| 535 | `    check("a: the same plan runs with the counter settings in the environment", rc == 0 and "\nE,1," in out, rc)` | Check: the plan now runs with status 0 and prints the `E` row of trial 1. So the runner also takes the counter settings from the environment. The two refusals before are proven to come from the missing settings. |

### `ALL` and `test_rows`: the rows of a plan with all phases (lines 538 to 607)

| Line | Source | Explanation |
|---:|---|---|
| 538 | `ALL = ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 4 20 closed 0",` | `ALL`: the four trial lines of a short plan that uses every phase. Trial 0, label `A`: previous activity `asmread` on 8 MiB for 24 ms, prefix `oldread` on 8 MiB for 40 ms, predecessor `read` on 1 MiB for 20 ms, target `oldread` on 8 MiB with 4 windows of 20 ms, counters closed, no bins. |
| 539 | `       "1 B 1 - read@1M:40 - read@1M 4 20 closed 0",` | Trial 1, label `B`: a prefix of `read` on 1 MiB for 40 ms, then the target `read` on 1 MiB with 4 windows of 20 ms. |
| 540 | `       "2 C 1 - - - asmread@32K 3 25 closed 1",` | Trial 2, label `C`: no phase before the target. The target is `asmread` on 32 KiB with 3 windows of 25 ms, with bins. |
| 541 | `       "3 A 2 - oldread@8M:40 oldread@1M:20 read@8M 2 20 closed 1"]` | Trial 3, label `A`, repeat 2: prefix `oldread` on 8 MiB for 40 ms, predecessor `oldread` on 1 MiB for 20 ms, target `read` on 8 MiB with 2 windows of 20 ms, with bins. |
| 544 | `def test_rows():` | Starts the test `test_rows`. |
| 545 | `    """(b) (d) (e) (h) and the M, K, S, P rows of a short plan with all phases"""` | Description text: the checks named b, d, e and h, and the `M`, `K`, `S` and `P` rows, on a short plan with all phases. |
| 546 | `    plan = write_plan("all", ALL)` | Writes the plan `ALL` to a file. |
| 547 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)])` | Runs it in the trial mode, with the CPU `E.ctl` for the controlling thread. |
| 548 | `    if not check("b: the plan with all phases runs with status 0", rc == 0, err):` | Check: the run ends with status 0. On a failure the error output is printed. |
| 549 | `        return` | Ends the test on a failure. Every later check needs the rows of this run. |
| 550 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the four plan lines. |
| 551 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary from key to value. An `M` row is one line of settings, `M,key,value`. |
| 552 | `    need = ["mode", "cpu", "ctl_cpu", "bytes", "thp", "madvise_ok", "check_bytes", "kernels", "plan_fnv1a64", "ntrials",` | `need`: the keys that the output must hold: the mode, the worker CPU, the control CPU, the buffer size, the huge-page policy, the result of the page policy request, the bytes between two clock reads, the kind of the kernels, the hash of the plan, the number of trials ... |
| 553 | `            "rec_windows", "rec_bins", "rec_bytes", "trace", "pmu_type", "events"]` | Continues line 552: ... the sizes of the record storage (windows, bins, bytes), the trace switch, the PMU type and the events. |
| 554 | `    check("b: every required M key is present", all(k in m for k in need), [k for k in need if k not in m])` | Check: every required key is present. The analysis needs these settings to know under which conditions a rate was measured. |
| 555 | `    with open(plan, "rb") as f:` | Opens the plan file as bytes. |
| 556 | `        digest = fnv1a64(f.read())` | `digest`: the FNV-1a hash of these bytes, computed by the test (line 434). |
| 557 | `    check("b: M values", (m.get("mode"), m.get("cpu"), m.get("ctl_cpu"), m.get("bytes"), m.get("check_bytes"), m.get("ntrials"),` | Check of ten `M` values. This line and line 558 read them from the output. |
| 558 | `                          m.get("trace"), m.get("plan_fnv1a64"), m.get("kernels"), m.get("thp")) ==` | Continues the check: the last four values that are read, and the start of the comparison. |
| 559 | `          ("trial", str(E.cpu), str(E.ctl), str(MIB8), str(MIB8), "4", "0", digest, "STAND-IN", "madvise"), m)` | Continues the check: the expected values. The mode is `trial`. The two CPUs are those of the options. `bytes` and `check_bytes` are 8388608. The plan has 4 trials. The trace is off. `plan_fnv1a64` equals the hash that the test computed, so a result names exactly the plan that ran. `kernels` is `STAND-IN`: the build marks itself as not usable for rates. `thp` is `madvise`: huge pages were requested. |
| 560 | `    check("b: the plan pairs are copied to M,plan.<key> rows",` | Check: every pair of the second header line of the plan is copied to a row `M,plan.<key>,<value>`. |
| 561 | `          {k: v for k, v in m.items() if k.startswith("plan.")} ==` | Continues the check: the rows of the output whose key starts with `plan.`. |
| 562 | `          {"plan.step": "T", "plan.session": "1", "plan.cpu": str(E.cpu), "plan.bytes": str(MIB8), "plan.proc": "0",` | Continues the check: the expected pairs, the values that `write_plan` wrote (line 414). |
| 563 | `           "plan.seed": "1", "plan.test": "1"})` | Continues the check: the last two pairs. |
| 564 | `    nwin = sum(len(expected_windows(f)) for f in lines)` | `nwin`: the number of windows of all four trials together. |
| 565 | `    check("b: record storage is sized from the plan and its size is printed",` | Check: the storage for the records is sized from the plan, and its size is printed. |
| 566 | `          m.get("rec_windows") == str(nwin) and m.get("rec_bins") == str(3 * 4 + 2 * 4) and int(m.get("rec_bytes", 0)) > 0, m)` | Continues the check: `rec_windows` equals `nwin`. `rec_bins` is 20: room for 4 bins in each of the 3 windows of trial 2 and of the 2 windows of trial 3. `rec_bytes` is above 0. The design asks that this storage is allocated and first written before the first trial. So no trial spends time on the first use of a page. |
| 567 | `    k = {f[1]: f for f in rows.get("K", [])}` | `k`: the `K` rows by kernel name. A `K` row holds a kernel name, the address of its function in hex and that address modulo 64. |
| 568 | `    check("b: one K row per kernel of the plan, with the address modulo 64",` | Check: one `K` row per kernel of the plan, with the address modulo 64. |
| 569 | `          sorted(k) == ["asmread", "oldread", "read"] and all(int(f[2], 16) % 64 == int(f[3]) for f in k.values()), k)` | Continues the check: the names are `asmread`, `oldread` and `read`, and in each row the last field is the hex address modulo 64. That value is the place of the function inside a 64-byte block of code. So each result names the code placement of its run. |
| 570 | `    s = rows.get("S", [])` | `s`: the `S` rows. An `S` row starts a trial. The runner prints it before the trial runs. |
| 571 | `    check("b: S rows hold the plan fields and the previous trial",` | Check: the `S` rows hold the plan fields and the previous trial. |
| 572 | `          [f[1:12] for f in s] == lines and [f[12:] for f in s] ==` | Continues the check: the fields 1 to 11 of each `S` row are the 11 fields of its plan line, and the last two fields are compared with the next line. |
| 573 | `          [["none", "none"], ["A", "oldread@8M"], ["B", "read@1M"], ["C", "asmread@32K"]], s)` | Continues the check: the label and the target of the trial before, and `none` twice for trial 0. The analysis can test with them whether the trial before changes a result. |
| 574 | `    check("b: one E row per S row", [f[1] for f in rows.get("E", [])] == [f[1] for f in s])` | Check: one `E` row per `S` row, with the same trial numbers. An `S` row without its `E` row would mean a trial that was interrupted. |
| 575 | `    check("b: P rows pre and post for every trial",` | Check: each trial has a `P` row `pre` and a `P` row `post`, in this order. |
| 576 | `          [(f[1], f[2]) for f in rows.get("P", [])] == [(str(i), w) for i in range(4) for w in ("pre", "post")] and` | Continues the check: the trial number and the word of each `P` row, against the expected list for the trials 0 to 3. |
| 577 | `          all(len(f) == 9 for f in rows["P"]))` | Continues the check: every `P` row has 9 fields. A `P` row holds the page state of the buffer: its size in kB, its part on huge pages in kB and four page counters of the whole system. |
| 578 | `    last = 0` | `last`: the end time of the trial before, 0 at the start. |
| 579 | `    for i, f in enumerate(lines):` | Loops over the four trials. `f` holds the plan fields of trial `i`. |
| 580 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 581 | `        p = window_problems(f, w)` | Applies the rule `window_problems` (line 85) to the trial. |
| 582 | `        check("b: trial %d: W rows complete, whole passes, 8 MiB rule, durations, monotonic times" % i, not p, p)` | Check b: no problem. The windows are complete, hold whole passes, keep the 8 MiB rule, last at least their requested time and have rising times. |
| 583 | `        check("b: trial %d: starts after the trial before it" % i, int(w[0][7]) >= last)` | Check b: the trial starts at or after the end of the trial before it. So the timed sequences of two trials do not overlap. |
| 584 | `        last = int(w[-1][8])` | Keeps the end time of the last window for the next trial. |
| 585 | `        p = e_problems(f, w, e)` | Applies the rule `e_problems` (line 106). |
| 586 | `        check("d: trial %d: wall_ns, gap_ns and max_boundary_gap_ns equal the W-row differences" % i, not p, p)` | Check d: `wall_ns`, `gap_ns` and `max_boundary_gap_ns` of the `E` row equal the differences of the `W` times. So the gap that the analysis reads is the measured time between the two clock reads. |
| 587 | `        p = bin_problems(f, w, of_trial(rows, "B", i))` | Applies the rule `bin_problems` (line 123). |
| 588 | `        check("e: trial %d: bins rise to the window end and their bytes sum to the window bytes" % i, not p, p)` | Check e: the bins rise to the window end, and their bytes sum to the bytes of the window. |
| 589 | `        check("b: trial %d: E row has 10 fields and count_state closed" % i, len(e) == 10 and e[9] == "closed", e)` | Check b: the `E` row has 10 fields, and its last field, the count state, is `closed`. The plan asked for no counters, and the row confirms that no counter group was open. |
| 590 | `        wall, cpu = int(e[2]), int(e[3])` | `wall`, `cpu`: the wall time and the CPU time of the timed sequence in ns (fields 2 and 3 of the `E` row). |
| 591 | `        check("b: trial %d: cpu_ns is CPU time: not the wall time, at least half of it, at most 1 ms above it" % i,` | Check b: `cpu_ns` is a CPU time and no copy of the wall time. |
| 592 | `              cpu != wall and wall // 2 <= cpu <= wall + 1000000, e)` | Continues the check: it differs from the wall time, is at least half of it and at most 1 ms (1000000 ns) above it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. So the field must hold a separate measurement. |
| 593 | `        pre, post = of_trial(rows, "P", i)` | `pre`, `post`: the two `P` rows of the trial. |
| 594 | `        check("b: trial %d: both P rows hold 8192 kB for the 8 MiB buffer and a number in every field" % i,` | Check b: both `P` rows hold 8192 kB, the size of the 8 MiB buffer, and a number in every later field. |
| 595 | `              pre[3] == post[3] == "8192" and all(v.isdigit() for v in pre[3:] + post[3:]), (pre, post))` | Continues the check: the condition and the detail. A number in the huge-page field shows that the runner could read the page state of the buffer. |
| 596 | `    e = rows["E"]` | `e`: all `E` rows of the run. |
| 597 | `    check("h: sink_ok is 1 for the trials that ran old read", [f[8] for f in e] == ["1", "NA", "NA", "1"], [f[8] for f in e])` | Check h: `sink_ok` (field 8) is `1` for the trials 0 and 3, which ran the old read kernel, and `NA` for the two others. The old read kernel returns the sum of the words that it read. The runner compares the last sum with the expected value. A `1` shows that the result of the old read kernel was used and was right. |
| 598 | `    check("d: gap_ns is NA for the trial whose target has no window before it", e[2][6] == "NA", e[2])` | Check d: `gap_ns` is `NA` for trial 2, whose target has no window before it. A gap that does not exist is not printed as 0. |
| 599 | `    # One pass over 8 MiB takes more than 20 us with the stand-in kernels, so a warm-up pass in the gap fails here.` | Comment: with the stand-in kernels one pass over 8 MiB takes more than 20 us. So a warm-up pass inside the gap makes the next check fail. |
| 600 | `    check("d: gap_ns before an 8 MiB target is below 20 us in trial 0 or trial 3 (no kernel pass inside the gap)",` | Check d: the gap before an 8 MiB target is below 20 us in trial 0 or in trial 3. So no kernel pass lies inside the gap. |
| 601 | `          min(int(e[0][6]), int(e[3][6])) < 20000, (e[0][6], e[3][6]))` | Continues the check: the smaller of the two gaps must be below 20000 ns. One long gap alone does not fail the check. |
| 602 | `    check("b: the 1 MiB windows hold a multiple of 8 MiB",` | Check b: every window with a pass size of 1 MiB holds a multiple of 8 MiB. The runner reads the clock after 8 passes of 1 MiB. |
| 603 | `          all(int(w[6]) % MIB8 == 0 for w in rows["W"] if w[5] == str(1 << 20)) and` | Continues the check: the condition on all `W` rows with a pass size of 1048576 bytes. |
| 604 | `          any(w[5] == str(1 << 20) for w in rows["W"]))` | Continues the check: at least one such row must exist. If none existed, the condition before would hold without testing anything. |
| 605 | `    check("b: no X row, no C row and no TR row in this run", not rows.get("X") and not rows.get("C") and not rows.get("TR"),` | Check b: this run printed no `X` row (no reported failure), no `C` row (no counters) and no `TR` row (no trace). |
| 606 | `          rows.get("X"))` | Continues the check: the detail that a failure prints. |

### `test_rows`: each rule must fail on changed rows (lines 608 to 637)

| Line | Source | Explanation |
|---:|---|---|
| 608 | `    # every rule must report a problem on changed rows` | Comment: every rule must report a problem on rows that were changed. This proves that the rule can fail. |
| 609 | `    f0, w0, e0 = lines[0], of_trial(rows, "W", 0), of_trial(rows, "E", 0)[0]` | `f0`, `w0`, `e0`: the plan fields, the `W` rows and the `E` row of trial 0. Trial 0 has 10 windows: row 0 is the previous activity, rows 1 to 4 are the prefix, row 5 is the predecessor and rows 6 to 9 are the target. |
| 611 | `    def changed(row_index, field, value):` | Starts the inner function `changed`. It returns a copy of the `W` rows of trial 0 in which one field of one row has a new value. |
| 612 | `        w = [list(x) for x in w0]` | Copies the rows. |
| 613 | `        w[row_index][field] = str(value)` | Sets the field. |
| 614 | `        return w` | Returns the changed rows. |
| 616 | `    check("b: the rule fails on a lost W row", window_problems(f0, w0[:-1]))` | Check: `window_problems` reports a problem when the last `W` row is lost. In the checks of this part the list of problems is the result itself: a list that is not empty counts as passed. |
| 617 | `    check("b: the rule fails on a byte count that is not whole passes", window_problems(f0, changed(2, 6, int(w0[2][6]) + 64)))` | Check: the rule fails on a byte count that is no whole number of passes: prefix window 1 with 64 bytes added. |
| 618 | `    check("b: the rule fails on 0 bytes", window_problems(f0, changed(2, 6, 0)))` | Check: the rule fails on a window with 0 bytes. |
| 619 | `    check("b: the rule fails on a 1 MiB window with 9 MiB", window_problems(f0, changed(5, 6, 9 << 20)))` | Check: the rule fails on the 1 MiB predecessor window with 9 MiB. That is whole passes, but no multiple of 8 MiB. |
| 620 | `    check("b: the rule fails on a window shorter than requested", window_problems(f0, changed(6, 8, int(w0[6][7]) + 19999999)))` | Check: the rule fails on a target window that ends 19999999 ns after its start. That is 1 ns less than the requested 20 ms. |
| 621 | `    check("b: the rule fails on a start before the end of the window before", window_problems(f0, changed(6, 7, int(w0[5][8]) - 1)))` | Check: the rule fails on a target window that starts 1 ns before the end of the predecessor window. |
| 622 | `    check("b: the rule fails on a wrong kernel in a window", window_problems(f0, changed(5, 4, "asmread")))` | Check: the rule fails on a wrong kernel name in the predecessor window. |
| 623 | `    e_bad = list(e0)` | `e_bad`: a copy of the `E` row of trial 0. |
| 624 | `    e_bad[6] = str(int(e0[6]) + 1)` | Adds 1 ns to its `gap_ns`. |
| 625 | `    check("d: the rule fails on a gap_ns that differs from the W rows by 1 ns", e_problems(f0, w0, e_bad))` | Check: `e_problems` fails on a `gap_ns` that differs from the `W` rows by 1 ns. |
| 626 | `    e_bad = list(e0)` | `e_bad`: a fresh copy of the `E` row. |
| 627 | `    e_bad[6] = "0"` | Sets its `gap_ns` to 0. |
| 628 | `    check("d: the rule fails on a gap_ns of 0", int(e0[6]) > 0 and e_problems(f0, w0, e_bad), e0)` | Check: the real gap is above 0, and the rule fails on a gap of 0. So the runner measures the gap and does not assume that it is zero. |
| 629 | `    f2, w2, b2 = lines[2], of_trial(rows, "W", 2), of_trial(rows, "B", 2)` | `f2`, `w2`, `b2`: the plan fields, the `W` rows and the `B` rows of trial 2. That trial has bins and a pass size of 32 KiB. |
| 630 | `    b_bad = [list(x) for x in b2]` | `b_bad`: a copy of the `B` rows. |
| 631 | `    b_bad[-1][5] = str(int(b_bad[-1][5]) - (32 << 10))` | Takes 32 KiB, one pass, from the byte count of the last bin. |
| 632 | `    check("e: the rule fails when the bins do not sum to the window bytes", bin_problems(f2, w2, b_bad))` | Check: `bin_problems` fails when the bins do not sum to the bytes of the window. |
| 633 | `    check("e: the rule fails when the last bin is lost", bin_problems(f2, w2, b2[:-1]))` | Check: the rule fails when the last bin is lost. The bins then do not reach the window end. |
| 634 | `    check("e: the rule fails on B rows in a trial without bins", bin_problems(lines[1], of_trial(rows, "W", 1), b2))` | Check: the rule fails on `B` rows in trial 1, which has no bins. |
| 635 | `    check("e: a 25 ms window has 1 to 3 bins", all(1 <= len([b for b in b2 if b[2] == str(i)]) <= 3 for i in range(3)), b2)` | Check: each of the 3 windows of 25 ms has 1 to 3 bins. The requested bin width is 10 ms, so such a window can close 3 bins at most. |

### `test_sequence_code`, checks c: the timed sequence in source and machine code (lines 638 to 660)

| Line | Source | Explanation |
|---:|---|---|
| 638 | `def test_sequence_code():` | Starts the test `test_sequence_code`. |
| 639 | `    """(c) the timed sequence in the source and in the machine code, without the trace"""` | Description text: the checks named c. They read the timed sequence from the source and from the machine code, without the trace. |
| 640 | `    with open(os.path.join(HERE, "bwx8.c")) as f:` | Opens `bwx8.c` in the folder of this file. |
| 641 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 642 | `    p = seq_source_problems(src)` | Applies the rule `seq_source_problems` to it. |
| 643 | `    check("c: source: timed_sequence() holds 2 clock reads, 1 kernel call, 2 counter reads and no other call", not p, p)` | Check: in the source, `timed_sequence()` holds 2 clock reads, 1 kernel call, 2 counter reads and no other call. So the text of the timed loop holds nothing that could add time between two clock reads, such as an output or a page read. |
| 644 | `    t = seq_targets(E.bin)` | `t`: the branch targets of `timed_sequence` in the machine code of the binary under test. |
| 645 | `    p = seq_code_problems(t)` | Applies the rule `seq_code_problems` to them. |
| 646 | `    check("c: machine code: timed_sequence reaches only clock_gettime, the kernels, tcount and the stack-guard failure",` | Check: in the machine code `timed_sequence` reaches only `clock_gettime`, the kernels, `tcount` and the function for a failed stack guard. This is the proof on the code that really runs: the compiler could have added or kept a call that the source does not show. |
| 647 | `          not p, (p, t))` | Continues the check: the result and the detail. |
| 648 | `    for name in SEQ_MUTANTS:` | Loops over the three defects of `timed_sequence`. |
| 649 | `        m = mutant_source(name)` | `m`: the source text of the runner with the defect `name`. |
| 650 | `        check("c: the source rule fails on a build with " + name, m is not None and seq_source_problems(m))` | Check: the defect could be put in, and the source rule reports a problem on that text. So the rule is proven to find this defect. |
| 651 | `    check("c: the machine-code rule fails on a call of fflush", seq_code_problems(dict(t, fflush=1)))` | Check: the rule fails when a call of `fflush` is added to the targets. `fflush` writes buffered output. This check and the next two show that the rule can fail. |
| 652 | `    check("c: the machine-code rule fails on a helper that is not inlined", seq_code_problems(dict(t, tclock=2)))` | Check: the rule fails when `tclock` stands among the targets. That is the case when the compiler did not put the clock helper inline. |
| 653 | `    check("c: the machine-code rule fails when the function has no kernel call",` | Check: the rule fails when the function has no kernel call. |
| 654 | `          seq_code_problems({k: v for k, v in t.items() if k != "(indirect)"}))` | Continues the check: the targets without the entry `(indirect)`. |
| 655 | `    b = mutant_build(SEQ_MUTANTS[1], "seq")` | `b`: the binary of the runner with the second defect of `SEQ_MUTANTS`, a page read and an output flush before the first target window (line 388). |
| 656 | `    check("c: the machine-code rule fails on a real build with " + SEQ_MUTANTS[1],` | Check: the machine-code rule fails on a real build with that defect. |
| 657 | `          b is not None and any("read_vmstat" in x or "fflush" in x for x in seq_code_problems(seq_targets(b))),` | Continues the check: the build worked, and a problem names `read_vmstat` or `fflush`, the two calls that the defect added. So the rule finds a real forbidden call in the compiled code. |
| 658 | `          b and seq_targets(b))` | Continues the check: the targets of that build as the detail. |

### `test_disturbed`, checks i: the values that mark a disturbed trial (lines 661 to 677)

| Line | Source | Explanation |
|---:|---|---|
| 661 | `def test_disturbed():` | Starts the test `test_disturbed`. |
| 662 | `    """(i) the values that mark a disturbed trial, from a trial that shares its CPU with another process"""` | Description text: the checks named i. They read the values that mark a disturbed trial from a trial that shares its CPU with another process. |
| 663 | `    plan = write_plan("shared", ["0 a 1 - oldread@8M:200 - oldread@8M 2 100 closed 0"])` | Writes a plan with one trial: a prefix of `oldread` on 8 MiB for 200 ms and 2 target windows of 100 ms. |
| 664 | `    spin = subprocess.Popen([sys.executable, "-c", "import os\nos.sched_setaffinity(0, {%d})\nwhile True:\n    pass" % E.cpu])` | Starts a second Python process. It pins itself to the worker CPU and then runs an endless loop. So it competes with the worker for that CPU. |
| 665 | `    try:` | Starts a block whose end (line 668) always runs. |
| 666 | `        time.sleep(0.5)  # the other process now runs on the worker CPU` | Waits 0.5 s. By the comment the other process then runs on the worker CPU. |
| 667 | `        rc, out, err = trial(plan)` | Runs the trial. |
| 668 | `    finally:` | The next two lines run also when the trial raised an error. |
| 669 | `        spin.kill()` | Ends the other process with the kill signal. |
| 670 | `        spin.wait()` | Waits until it has ended. |
| 671 | `    e = rows_of(out).get("E", [[]])[0]` | `e`: the `E` row of the trial, or an empty list when the output has none. |
| 672 | `    if not check("i: the trial on a shared CPU ends with status 0 and an E row", rc == 0 and len(e) == 10, err):` | Check: the trial on the shared CPU still ends with status 0 and an `E` row of 10 fields. |
| 673 | `        return` | Ends the test when that check failed. |
| 674 | `    check("i: shared CPU: cpu_ns is below 0.9 x wall_ns", int(e[3]) < 0.9 * int(e[2]), e)` | Check: `cpu_ns` is below 0.9 times `wall_ns`. The worker got only a part of the CPU, and the row shows it. The design marks a trial as disturbed when its CPU time is below 99 % of its wall time. |
| 675 | `    check("i: shared CPU: nivcsw (involuntary) is above 0 and nvcsw (voluntary) is 0", int(e[5]) > 0 and e[4] == "0", e)` | Check: `nivcsw`, the count of involuntary context switches (field 5), is above 0, and `nvcsw`, the count of voluntary ones (field 4), is 0. Linux took the CPU away from the worker, and the worker never gave it up by itself. A rise of the involuntary count is the second mark of a disturbed trial in the design. |

### `test_placement`, checks j: pin before allocation, and a failed `madvise` (lines 678 to 712)

| Line | Source | Explanation |
|---:|---|---|
| 678 | `def test_placement():` | Starts the test `test_placement`. |
| 679 | `    """(j) pin before allocation, the CPU of the controlling thread, and the X row of a failed madvise"""` | Description text: the checks named j. They cover the pin before the allocation, the CPU of the controlling thread, and the `X` row of a failed `madvise`. |
| 680 | `    d = os.path.join(E.tmp, "shim")` | `d`: the folder `shim` in the temporary folder. |
| 681 | `    os.makedirs(d)` | Creates the folder. |
| 682 | `    with open(os.path.join(d, "shim.c"), "w") as f:` | Opens the file `shim.c` in it for writing. |
| 683 | `        f.write(SHIM)` | Writes the C text `SHIM` (line 302). |
| 684 | `    so = os.path.join(d, "shim.so")` | `so`: the path of the library file `shim.so`. |
| 685 | `    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O1", "-o", so, os.path.join(d, "shim.c")], stdout=subprocess.PIPE,` | Compiles the C text with `gcc` into a shared library. `-shared` makes a library that a program can load at its start. `-fPIC` makes code that works at any address. `-O1` is a low optimization level. |
| 686 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call of line 685: the messages of the compiler are collected as one text. |
| 687 | `    if not check("j: the library that logs sched_setaffinity and mmap builds", r.returncode == 0, r.stdout):` | Check j: the library builds. On a failure the compiler messages are printed. |
| 688 | `        return` | Ends the test when the library did not build. |
| 689 | `    plan = write_plan("place", [GOOD])` | Writes a plan with the line `GOOD`. |
| 690 | `    rc, out, err = trial(plan, ["--ctl-cpu", str(E.ctl)], env_add={"LD_PRELOAD": so})` | Runs it with the control CPU `E.ctl` and with `LD_PRELOAD` set to the library. Linux then loads the library before the C library. So the runner calls the `sched_setaffinity`, `mmap` and `madvise` of the library, and each call is logged. |
| 691 | `    lines = [x for x in err.splitlines() if x.startswith("shim ")]` | `lines`: the log lines of the library in the error output. Each one starts with `shim`. |
| 692 | `    p = placement_problems(lines, E.cpu, E.ctl) if rc == 0 and lines else ["rc=%s, %d lines" % (rc, len(lines))]` | Applies the rule `placement_problems` (line 275) when the run ended with status 0 and logged lines. If not, the status and the number of lines are the problem. |
| 693 | `    check("j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself "` | Check j: the controlling thread pins itself to its CPU before the worker starts, and the worker pins itself ... |
| 694 | `          "before it maps the buffer", not p, (p, lines))` | Continues the check: ... before it maps the buffer. Linux assigns the pages of a buffer at the first touch. A worker that maps and writes its buffer before the pin could do so while it runs on another CPU. |
| 695 | `    if not p:` | Only when the rule passed: the next three checks show that the rule can fail. |
| 696 | `        w = [i for i, x in enumerate(lines) if x.split()[3] != "tid=" + x.split()[2][4:]]` | `w`: the positions of the log lines of the worker thread. These are the lines whose thread id differs from the process id. |
| 697 | `        late = lines[:w[0]] + [lines[w[1]], lines[w[0]]] + lines[w[1] + 1:]` | `late`: the log with the first two logged calls of the worker exchanged. The worker then maps memory before its pin. |
| 698 | `        check("j: the rule fails when the worker maps the buffer before its pin", placement_problems(late, E.cpu, E.ctl))` | Check: the rule fails on that log. |
| 699 | `        no_ctl = [x for x in lines if not x.endswith(" 1 %d" % E.ctl)]` | `no_ctl`: the log without the lines that end with a set of 1 CPU whose first CPU is the control CPU. These are the pins to the control CPU. |
| 700 | `        check("j: the rule fails when the controlling thread does not pin itself", placement_problems(no_ctl, E.cpu, E.ctl))` | Check: the rule fails when the controlling thread does not pin itself. |
| 701 | `        check("j: the rule fails when the worker pins itself to another CPU", placement_problems(lines, E.ctl, E.ctl))` | Check: the rule fails when it is asked for another worker CPU (`E.ctl`) than the one in the log. So a worker on a wrong CPU would be found. |
| 702 | `    rows = rows_of(out)` | `rows`: the output of the first run, sorted by row type. |
| 703 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 704 | `    check("j: madvise that works: M,madvise_ok,1 and no X row", m.get("madvise_ok") == "1" and not rows.get("X"), rows.get("X"))` | Check j: with a working `madvise` the row `M,madvise_ok` holds `1`, and no `X` row is printed. |
| 705 | `    rc, out, err = trial(plan, env_add={"LD_PRELOAD": so, "SHIM_MADVISE_FAIL": "1"})` | Runs the plan again with the variable `SHIM_MADVISE_FAIL` set. The library then lets every `madvise` call of the runner fail (line 334). |
| 706 | `    rows = rows_of(out)` | `rows`: the output of this run, sorted by row type. |
| 707 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: its `M` rows as a dictionary. |
| 708 | `    check("j: madvise that fails: status 0, M,madvise_ok,0, the row X,-1,madvise, and the trial still runs",` | Check j: a failed page policy request is reported, and the run continues. The exit status is 0, the row `M,madvise_ok` holds `0`, the only `X` row is `X,-1,madvise`, ... |
| 709 | `          rc == 0 and m.get("madvise_ok") == "0" and [f[1:3] for f in rows.get("X", [])] == [["-1", "madvise"]] and` | Continues the check: the three conditions on the exit status, the `M` row and the `X` rows. |
| 710 | `          len(rows.get("E", [])) == 1, (rc, m.get("madvise_ok"), rows.get("X")))` | Continues the check: ... and one `E` row exists, so the trial still ran. The design says that a failed page-policy request is a reported failure and not an assumed success. A result without the requested huge pages is then marked in its own output. |

### `events_of` and `test_trace`, checks c: the trace of closed, open and read trials (lines 713 to 766)

| Line | Source | Explanation |
|---:|---|---|
| 713 | `def events_of(rows, trial_no):` | Starts the function `events_of`. It reads the trace of one trial from the `TR` rows. A `TR` row holds the trial number, the event number, the event name and a time in ns. |
| 714 | `    tr = of_trial(rows, "TR", trial_no)` | `tr`: the `TR` rows of the trial. |
| 715 | `    ok = [int(f[2]) for f in tr] == list(range(len(tr)))` | `ok`: true when the event numbers (field 2) are 0, 1, 2 and so on. |
| 716 | `    return [(f[3], int(f[4])) for f in tr], ok` | Returns the list of pairs of event name and time, and `ok`. |
| 719 | `def test_trace():` | Starts the test `test_trace`. |
| 720 | `    """(c) the trace of closed, open and read trials, and the trace rule on broken traces"""` | Description text: the checks named c on the trace of trials with the count modes `closed`, `open` and `read`, and the trace rule on broken traces. |
| 721 | `    plan = write_plan("trace", ["0 A 1 asmread@8M:24 oldread@8M:40 read@1M:20 oldread@8M 3 20 closed 1",` | Writes a plan of 5 trials. Trial 0, label `A`: all phases, the target `oldread` on 8 MiB with 3 windows of 20 ms, counters closed, with bins. |
| 722 | `                                "1 B 1 - oldread@8M:40 read@8M:20 read@8M 3 20 read 0",` | Trial 1, label `B`: a prefix, a predecessor and 3 target windows of `read`, with the count mode `read`. In this mode the counter group is open, and the runner reads it at the boundaries of the target windows. |
| 723 | `                                "2 C 1 - oldread@8M:40 - asmread@8M 2 20 open 0",` | Trial 2, label `C`: a prefix and 2 target windows of `asmread`, with the count mode `open`. The counter group is open but is not read. |
| 724 | `                                "3 D 1 - - - read@8M 2 20 read 0",` | Trial 3, label `D`: only 2 target windows of `read`, with the count mode `read`. |
| 725 | `                                "4 E 1 - - - oldread@8M 2 20 closed 0"])` | Trial 4, label `E`: only 2 target windows of `oldread`, counters closed. |
| 726 | `    rc, out, err = trial(plan, ["--trace", "--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with `--trace`, the PMU type 1 and the events `task_clock` (code 1) and `cpu_clock` (code 0). By the check of line 732, PMU type 1 means the software events of Linux. With `--trace` the runner logs the events of its wrapper functions and prints them as `TR` rows. The design calls this the non-measuring test: the rates of a trace run are not used. |
| 727 | `    if not check("c: the trace run ends with status 0", rc == 0, err):` | Check c: the trace run ends with status 0. |
| 728 | `        return` | Ends the test when the run failed. |
| 729 | `    rows, lines = rows_of(out), plan_lines(plan)` | `rows`: the output sorted by row type. `lines`: the fields of the plan lines. |
| 730 | `    states = [f[9] for f in rows["E"]]` | `states`: the count state of each trial, the last field of its `E` row. |
| 731 | `    E.soft_counters = states == ["closed", "read", "open", "read", "closed"]` | `E.soft_counters`: true when the states are `closed`, `read`, `open`, `read`, `closed`, as the plan asks. The software events then opened on this machine. Later tests read this value. |
| 732 | `    check("c: the software events of Linux (PMU type 1) open on this machine", E.soft_counters, (states, rows.get("X")))` | Check c: the software events of Linux (PMU type 1) open on this machine. On a failure the states and the `X` rows are printed. |
| 733 | `    saved = None` | `saved`: will hold the data of trial 0, for the checks on broken traces. |
| 734 | `    for i, f in enumerate(lines):` | Loops over the trials. `f` holds the plan fields of trial `i`. |
| 735 | `        ev, numbered = events_of(rows, i)` | `ev`: the events of the trial. `numbered`: whether its `TR` rows are numbered without a hole. |
| 736 | `        w, e = of_trial(rows, "W", i), of_trial(rows, "E", i)[0]` | `w`: the `W` rows of the trial. `e`: its `E` row. |
| 737 | `        p = trace_problems(f, ev, w, e)` | Applies the rule `trace_problems` (line 154). |
| 738 | `        check("c: trial %d (count %s): TR rows are numbered 0, 1, 2, ..." % (i, f[9]), numbered and len(ev) > 0)` | Check c: the `TR` rows of the trial are numbered 0, 1, 2 and so on, and at least one exists. A lost event row would show as a hole in the numbers. |
| 739 | `        check("c: trial %d (count %s): no forbidden event in the timed sequence, and the W rows and gap_ns "` | Check c: no forbidden event lies in the timed sequence, and the times of the `W` rows and `gap_ns` ... |
| 740 | `              "are clock reads of the trace" % (i, f[9]), not p, p)` | Continues the check: ... are clock reads of the trace. By the design a warm-up pass, a page read, an output flush or a counter read must not enter the path from the predecessor to the target, and the recorded gap must hold all the work of the runner between the two kernels. This check proves both on the real call path. |
| 741 | `        names = [n for n, _ in ev]` | `names`: the event names of the trial. |
| 742 | `        want_reads = int(f[7]) + 1 if f[9] == "read" and E.soft_counters else 0` | `want_reads`: the expected number of counter reads. In a trial with the count mode `read`, when the events opened, it is the number of target windows plus 1. In every other trial it is 0. |
| 743 | `        check("c: trial %d (count %s): %d counter reads" % (i, f[9], want_reads), names.count("count_read") == want_reads,` | Check c: the trace holds exactly that many counter reads. That is one reading at each boundary of a target window and none inside a window. |
| 744 | `              names.count("count_read"))` | Continues the check: the number found, as the detail. |
| 745 | `        check("c: trial %d: 2 page reads and 2 outputs, all outside the timed sequence" % i,` | Check c: each trial has 2 page reads and 2 outputs. |
| 746 | `              names.count("page_read") == 2 and names.count("output") == 2)` | Continues the check: the two counts. The trace rule of line 739 has shown that they lie outside the timed sequence. |
| 747 | `        if i == 0:` | For trial 0 only: |
| 748 | `            saved = (f, ev, w, e)` | Keeps the data of trial 0. |
| 749 | `            times = {t for n, t in ev if n == "clock"}` | `times`: the set of the times of all clock reads of the trace. |
| 750 | `            p = bin_problems(f, w, of_trial(rows, "B", 0), times)` | Applies `bin_problems` (line 123) with these times. |
| 751 | `            check("e: every bin end of the trace run is a clock read of the trace", not p, p)` | Check e: every bin end of this run is a clock read of the trace. So the bins add no clock read to the timed loop. |
| 752 | `            b_bad = [list(x) for x in of_trial(rows, "B", 0)]` | `b_bad`: a copy of the `B` rows of trial 0. |
| 753 | `            b_bad[0][4] = str(int(b_bad[0][4]) + 1)` | Adds 1 ns to the end time of its first bin. |
| 754 | `            check("e: the rule fails on a bin end that is no clock read", bin_problems(f, w, b_bad, times))` | Check e: the rule fails on a bin end that is no clock read. |
| 755 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out, re.M)` | `faults`: the pairs of trial number and count from the comment lines `# minflt,<trial>,<count>` of the output. With `--trace` the runner prints there the minor page faults of the worker between its two reads of the thread statistics, before and after the timed sequence. A minor page fault happens when a thread uses a page that Linux has not yet assigned to it. The pattern matches a whole line: group 1 is the trial number, group 2 the count, which may be negative. |
| 756 | `    check("c: no minor page fault of the worker between the two rusage reads of any trial (records and buffer were "` | Check c: no minor page fault of the worker in the timed sequence of any trial. The records and the buffer were first touched before ... |
| 757 | `          "first touched before)", faults == [(str(i), "0") for i in range(5)], faults)` | Continues the check: the list must hold the trials 0 to 4, each with the count 0. So no window holds the time of the first use of a page. |
| 758 | `    b = mutant_build(TOUCH_MUTANT, "touch")` | `b`: a build of the runner whose record storage is not written before the first trial (line 369). |
| 759 | `    out_m = run(["--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan, "--trace", "--pmu-type", "1", "--events",` | Runs the same trace plan with that build and takes its standard output. |
| 760 | `                 "task_clock=1,cpu_clock=0"], binary=b)[1] if b else ""` | Continues the call of line 759: the event list and the binary. Without a build the output is an empty text. |
| 761 | `    faults = re.findall(r"^# minflt,(\d+),(-?\d+)$", out_m, re.M)` | `faults`: the fault lines of that output. |
| 762 | `    check("c: that check fails on a build with " + TOUCH_MUTANT, len(faults) == 5 and any(int(n) > 0 for _, n in faults), faults)` | Check c: the fault check fails on that build: 5 lines, and at least one count above 0. So the check is proven to find a first touch inside a timed sequence. |
| 763 | `    opens = [[n for n, _ in events_of(rows, i)[0] if n in ("count_open", "count_close")] for i in range(5)]` | `opens`: for each of the 5 trials, its events `count_open` and `count_close` in order. |
| 764 | `    check("c: the group opens before the first counted trial and closes before the next closed trial",` | Check c: the counter group opens before the first counted trial and closes before the next closed trial. |
| 765 | `          opens == [[], ["count_open"], [], [], ["count_close"]], opens)` | Continues the check: trial 1 has one open, trial 4 has one close, the other trials have none. So the group stays open over the trials 1 to 3. A counted trial that follows a counted trial does not open the group again. |

### `test_trace`: the trace rule must fail on broken traces (lines 767 to 804)

| Line | Source | Explanation |
|---:|---|---|
| 767 | `    # the rule on broken traces of trial 0 (closed, all phases)` | Comment: the next checks apply the rule to broken copies of the trace of trial 0, the closed trial with all phases. |
| 768 | `    f, ev, w, e = saved` | `f`, `ev`, `w`, `e`: the saved data of trial 0. |
| 769 | `    names = [n for n, _ in ev]` | `names`: its event names. |
| 770 | `    tgt0 = names.index("kernel_first:target:0")` | `tgt0`: the position of the first kernel call of target window 0. |
| 771 | `    tgt1 = names.index("kernel_first:target:1")` | `tgt1`: the position of the first kernel call of target window 1. |
| 772 | `    pred = names.index("kernel_first:pred:0")` | `pred`: the position of the first kernel call of the predecessor window. |
| 774 | `    def broken(at, name):` | Starts the inner function `broken`. It returns a copy of the trace with one more event, `name`, before the position `at`. |
| 775 | `        return ev[:at] + [(name, ev[at - 1][1])] + ev[at:]` | Returns the events before `at`, then the new event with the time of the event before it, then the events from `at` on. |
| 777 | `    check("c: the rule passes on the unchanged trace", not trace_problems(f, ev, w, e))` | Check c: the rule passes on the unchanged trace. |
| 778 | `    check("c: the rule fails on a page read between predecessor and target", trace_problems(f, broken(tgt0 - 1, "page_read"), w, e))` | Check: the rule fails on a page read between the predecessor and the target. The event is put before the start clock read of target window 0. |
| 779 | `    check("c: the rule fails on a page read between the start clock read of the target and its first kernel call",` | Check: the rule fails on a page read between the start clock read of the target and its first kernel call. |
| 780 | `          trace_problems(f, broken(tgt0, "page_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 781 | `    check("c: the rule fails on an output between two target windows", trace_problems(f, broken(tgt1 - 1, "output"), w, e))` | Check: the rule fails on an output between two target windows. |
| 782 | `    check("c: the rule fails on a counter read between predecessor and target in a closed trial",` | Check: the rule fails on a counter read between the predecessor and the target in a closed trial. |
| 783 | `          trace_problems(f, broken(tgt0 - 1, "count_read"), w, e))` | Continues the check: the broken trace and the rule. |
| 784 | `    check("c: the rule fails on a CPU clock read between predecessor and target in a closed trial",` | Check: the rule fails on a CPU clock read between the predecessor and the target in a closed trial. |
| 785 | `          trace_problems(f, broken(tgt0 - 1, "cpu_clock"), w, e))` | Continues the check: the broken trace and the rule. |
| 786 | `    check("c: the rule fails on a warm-up kernel call before the target", trace_problems(f, broken(tgt0 - 1, "kernel_first:warmup:0"), w, e))` | Check: the rule fails on a warm-up kernel call before the target. The added event has the name `kernel_first:warmup:0`. |
| 787 | `    check("c: the rule fails on a second first call of the target window", trace_problems(f, broken(tgt0 + 1, "kernel_first:target:0"), w, e))` | Check: the rule fails on a second first call of target window 0. |
| 788 | `    check("c: the rule fails on a page read inside the predecessor window", trace_problems(f, broken(pred + 2, "page_read"), w, e))` | Check: the rule fails on a page read inside the predecessor window. |
| 789 | `    check("c: the rule fails on a counter open inside the prefix", trace_problems(f, broken(names.index("kernel_first:prefix:2") + 2, "count_open"), w, e))` | Check: the rule fails on a counter open inside the prefix. |
| 790 | `    check("c: the rule fails on a lost clock read of a window", trace_problems(f, ev[:tgt0 + 1] + ev[tgt0 + 2:], w, e))` | Check: the rule fails on a lost clock read of a window. The event after the first kernel call of target window 0 is removed. |
| 791 | `    one_clock = ev[:tgt0 - 2] + ev[tgt0 - 1:]` | `one_clock`: the trace without the event two places before the first kernel call of target window 0. That event is the end clock read of the predecessor window. |
| 792 | `    check("c: the rule fails when one clock read serves as end and start of a boundary", trace_problems(f, one_clock, w, e))` | Check: the rule fails when one clock read serves as the end of a window and as the start of the next one. The runner must read the clock twice at a boundary. Only then the gap is a measured time. |
| 793 | `    e_bad = list(e)` | `e_bad`: a copy of the `E` row. |
| 794 | `    e_bad[6] = str(int(e[6]) + 5)` | Adds 5 ns to its `gap_ns`. |
| 795 | `    check("d: the rule fails when gap_ns is not the time between the two clock reads", trace_problems(f, ev, w, e_bad))` | Check d: the rule fails when `gap_ns` is not the time between the two clock reads of the trace. |
| 796 | `    # target window 0 (20 ms): the clock read before its last one already lies at the requested end` | Comment: the next case uses target window 0, which has 20 ms. Its clock read before the last one is moved to the requested end. |
| 797 | `    late = list(ev)` | `late`: a copy of the trace. |
| 798 | `    late[tgt1 - 3] = ("clock", ev[tgt0 - 1][1] + 20000000)` | Changes the event three places before the first kernel call of target window 1. That event is the clock read before the last one of target window 0. Its new time is the start of the window plus 20000000 ns, exactly the requested end. |
| 799 | `    p = trace_problems(f, late, w, e)` | Applies the rule to this trace. |
| 800 | `    check("c: the rule fails on a window that runs on after a clock read at its requested end",` | Check c: the rule fails on a window that continues after a clock read at its requested end. |
| 801 | `          names[tgt1 - 3] == "clock" and tgt1 - 3 > tgt0 and p == ["window 6: runs on after the clock read that passed "` | Continues the check: the changed event is a clock read inside target window 0, and the rule reports exactly one problem, for window 6. Window 6 is target window 0: six windows of the trial run before it. |
| 802 | `                                                                 "its requested duration"], p)` | Continues the check: the rest of the expected problem text, and the detail. |

### `test_counters`, checks f: a counter that does not open is reported (lines 805 to 856)

| Line | Source | Explanation |
|---:|---|---|
| 805 | `def test_counters():` | Starts the test `test_counters`. |
| 806 | `    """(f) a failed open is reported, and the timing rows stay"""` | Description text: the checks named f. A failed open is reported, and the timing rows stay. |
| 807 | `    lines = ["0 A 1 - oldread@8M:20 - oldread@8M 2 10 closed 0",` | `lines`: three trials, each with a prefix of 20 ms and 2 target windows of 10 ms of `oldread` on 8 MiB. Trial 0 has the count mode `closed`. |
| 808 | `             "1 B 1 - oldread@8M:20 - oldread@8M 2 10 read 0",` | Trial 1 has the count mode `read`. |
| 809 | `             "2 C 1 - oldread@8M:20 - oldread@8M 2 10 open 0"]` | Trial 2 has the count mode `open`. |
| 810 | `    plan = write_plan("count", lines)` | Writes the plan. |
| 811 | `    rc, out, err = trial(plan, ["--pmu-type", "999999", "--events", "cycles=0x11,instructions=0x08"])` | Runs it with the PMU type 999999 and two events named `cycles` and `instructions`. The check of line 813 says that this PMU type does not exist. So the events cannot open. |
| 812 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 813 | `    check("f: a PMU type that does not exist: status 0", rc == 0, err)` | Check f: the exit status is 0. A counter that does not open does not stop the run. |
| 814 | `    x = [(f[1], f[2]) for f in rows.get("X", [])]` | `x`: the trial number and the code of each `X` row. |
| 815 | `    check("f: an X row with code count_open for each counted trial, none for the closed trial",` | Check f: one `X` row with the code `count_open` for each counted trial, and none for the closed trial. So the result itself says which trials have no usable counts. |
| 816 | `          x == [("1", "count_open"), ("2", "count_open")], rows.get("X"))` | Continues the check: the expected list, the trials 1 and 2. |
| 817 | `    check("f: count_state is fail in the E rows of the counted trials", [f[9] for f in rows.get("E", [])] == ["closed", "fail", "fail"],` | Check f: the count state in the `E` rows is `closed`, `fail`, `fail`. So a trial whose counters did not open says so in its own summary row. |
| 818 | `          rows.get("E"))` | Continues the check: the `E` rows as the detail. |
| 819 | `    check("f: the timing rows of the failed trials are kept",` | Check f: the timing rows of the failed trials are kept. |
| 820 | `          all(not window_problems(f, of_trial(rows, "W", i)) for i, f in enumerate(plan_lines(plan))))` | Continues the check: the `W` rows of every trial pass `window_problems`. The design says to reject unsupported event counts for interpretation and to keep the timing rows. |
| 821 | `    c = rows.get("C", [])` | `c`: the `C` rows. A `C` row belongs to one target window of a trial with the count mode `read`. It holds the enabled time and the running time of the counter group, the thread CPU time, and one count per event. |
| 822 | `    check("f: the C rows of the failed read trial hold NA for the group and a number for the CPU time",` | Check f: the `C` rows of the failed read trial hold `NA` for the group and a number for the CPU time. |
| 823 | `          len(c) == 2 and all(f[1] == "1" and f[3:5] == ["NA", "NA"] and f[5].isdigit() and f[6:] == ["NA", "NA"] for f in c), c)` | Continues the check: 2 rows, both of trial 1. The enabled and the running time are `NA`, the CPU time is a number, and both event counts are `NA`. A count that was not measured is never printed as 0. |
| 824 | `    m = {f[1]: f[2] for f in rows.get("M", [])}` | `m`: the `M` rows as a dictionary. |
| 825 | `    check("f: M rows record the PMU type and the event codes", m.get("pmu_type") == "999999" and` | Check f: the `M` rows record the PMU type and the event codes. |
| 826 | `          m.get("events") == "cycles=0x11;instructions=0x8", m)` | Continues the check: `pmu_type` is `999999`, and `events` is `cycles=0x11;instructions=0x8`: each name with its code in hex. |
| 828 | `    if not getattr(E, "soft_counters", False):` | Tests whether the software events opened in `test_trace` (line 731). |
| 829 | `        check("f: counter rows with software events (NOT RUN: the events did not open in the trace test)", False)` | If not, the rest of this test cannot run. The line records a failed check with `NOT RUN` in its name. |
| 830 | `        return` | Ends the test in that case. |
| 831 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,bad=999"])` | Runs the plan with the PMU type 1 and two events: `task_clock`, and an event with the code 999, which the test expects not to open. |
| 832 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 833 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 834 | `    check("f: one event of two does not open: X rows count_open and count_state fail",` | Check f: when one event of two does not open, the runner prints `X` rows `count_open` and the count state `fail`. |
| 835 | `          rc == 0 and [(f[1], f[2]) for f in rows.get("X", [])] == [("1", "count_open"), ("2", "count_open")] and` | Continues the check: status 0, and `X` rows for the trials 1 and 2 ... |
| 836 | `          [f[9] for f in rows["E"]] == ["closed", "fail", "fail"] and "1 of 2" in rows["X"][0][3], rows.get("X"))` | Continues the check: ... the states `closed`, `fail`, `fail`, and the text `1 of 2` in the first `X` row. |
| 837 | `    check("f: the event that opened has numbers, the other has NA",` | Check f: the event that opened has numbers, and the other one has `NA`. |
| 838 | `          len(c) == 2 and all(f[3].isdigit() and f[6].isdigit() and f[7] == "NA" for f in c), c)` | Continues the check: in both `C` rows the enabled time and the first count are numbers, and the second count is `NA`. |
| 839 | `    rc, out, err = trial(plan, ["--pmu-type", "1", "--events", "task_clock=1,cpu_clock=0"])` | Runs the plan with two events that open: `task_clock` and `cpu_clock`. |
| 840 | `    rows = rows_of(out)` | `rows`: the output sorted by row type. |
| 841 | `    c = rows.get("C", [])` | `c`: the `C` rows. |
| 842 | `    check("f: events that open: no X row, count_state closed, read, open",` | Check f: with events that open there is no `X` row, and the count states are `closed`, `read`, `open`. |
| 843 | `          rc == 0 and not rows.get("X") and [f[9] for f in rows["E"]] == ["closed", "read", "open"], rows.get("X"))` | Continues the check: the three conditions, and the `X` rows as the detail. |
| 844 | `    check("f: one C row per target window of the read trial only, with enabled, running, CPU time and 2 counts",` | Check f: one `C` row per target window of the read trial only, with the enabled time, the running time, the CPU time and 2 counts. |
| 845 | `          [(f[1], f[2]) for f in c] == [("1", "0"), ("1", "1")] and all(len(f) == 8 and all(v.isdigit() for v in f[3:]) for f in c), c)` | Continues the check: the rows are those of trial 1, windows 0 and 1. Each has 8 fields, and every value is a number. The trial with the count mode `open` prints no `C` row. |
| 846 | `    check("f: running time equals enabled time, and the CPU time is above 0",` | Check f: the running time equals the enabled time, and the CPU time is above 0. |
| 847 | `          all(f[3] == f[4] and int(f[5]) > 0 for f in c), c)` | Continues the check: the condition on both rows. Equal times mean that the counters counted during the whole window. The runner reports a running time below the enabled time as a multiplexed counter. |
| 848 | `    # A C row holds the change over its target window. The group was opened before the 20 ms prefix, so a row that` | Comment: a `C` row holds the change over its target window. The counter group was opened before the prefix of 20 ms. So a row that held the reading itself ... |
| 849 | `    # held the reading itself would be at least 3 times the 10 ms window.` | Comment: ... would be at least 3 times the window of 10 ms. |
| 850 | `    tw = [w for w in of_trial(rows, "W", 1) if w[2] == "target"]` | `tw`: the `W` rows of the target windows of trial 1. |
| 851 | `    span = [int(w[8]) - int(w[7]) for w in tw]` | `span`: the duration of each of these windows in ns. |
| 852 | `    check("f: enabled time, CPU time and both software clocks of a C row lie between half of the window time and "` | Check f: the enabled time, the CPU time and both software clocks of a `C` row lie between half of the window time and ... |
| 853 | `          "the window time plus 1 ms", len(c) == len(span) == 2 and` | Continues the check: ... the window time plus 1 ms. There must be 2 rows and 2 windows. |
| 854 | `          all(n // 2 <= int(v) <= n + 1000000 for f, n in zip(c, span) for v in f[3:]), (c, span))` | Continues the check: every value from field 3 on is compared with the duration of its window. This proves that a `C` row is the difference of two readings at the two ends of one target window, and not a total from the open on. |

### `test_kill_and_seq`, checks g: a killed trial, and the unchanged interval mode (lines 857 to 897)

| Line | Source | Explanation |
|---:|---|---|
| 857 | `def test_kill_and_seq():` | Starts the test `test_kill_and_seq`. |
| 858 | `    """(g) S row without E row after SIGKILL, and the unchanged --seq mode"""` | Description text: the checks named g. After the signal `SIGKILL` an `S` row stands without its `E` row. The mode `--seq` is unchanged. |
| 859 | `    plan = write_plan("kill", [GOOD, "1 long 1 - oldread@8M:400 - oldread@8M 4 5000 closed 0"])` | Writes a plan: the good line, then a long trial 1 with a prefix of 400 ms and 4 target windows of 5000 ms each. |
| 860 | `    path = os.path.join(E.tmp, "kill.csv")` | `path`: the file `kill.csv` in the temporary folder. It takes the output of the runner. |
| 861 | `    with open(path, "w") as f:` | Opens the file for writing. |
| 862 | `        proc = subprocess.Popen([E.bin, "--trial", "--cpus", str(E.cpu), "--bytes", "8M", "--plan", plan], stdout=f,` | Starts the runner on the plan in the background, with its standard output in that file. |
| 863 | `                                stderr=subprocess.DEVNULL)` | Continues the call of line 862: the error output is discarded. |
| 864 | `    deadline = time.time() + 30` | `deadline`: 30 s from now. |
| 865 | `    while time.time() < deadline and proc.poll() is None:` | Waits as long as the deadline has not passed and the runner still runs: |
| 866 | `        with open(path) as f:` | Opens the output file for reading. |
| 867 | `            if "\nS,1," in f.read():` | Tests whether the file holds the `S` row of trial 1. |
| 868 | `                break` | Leaves the wait loop. |
| 869 | `        time.sleep(0.02)` | Sleeps 0.02 s before the next test of the file. |
| 870 | `    time.sleep(0.2)  # the worker is now inside the timed sequence of trial 1` | Waits 0.2 s more. By the comment the worker is then inside the timed sequence of trial 1. |
| 871 | `    alive = proc.poll() is None` | `alive`: true when the runner still runs. |
| 872 | `    proc.send_signal(signal.SIGKILL)` | Sends the signal `SIGKILL` to the runner. Linux ends the process immediately. The process cannot react to this signal. |
| 873 | `    rc = proc.wait()` | `rc`: the exit status. For a process that a signal ended, Python gives the negative number of the signal. |
| 874 | `    with open(path) as f:` | Opens the output file. |
| 875 | `        rows = rows_of(f.read())` | `rows`: its content sorted by row type. |
| 876 | `    check("g: the process was killed inside trial 1", alive and rc == -signal.SIGKILL, rc)` | Check g: the process was alive before the kill and was ended by `SIGKILL`. So the process was ended while a trial ran. |
| 877 | `    check("g: after SIGKILL the S row of trial 1 has no E row, and trial 0 has both",` | Check g: after the kill the `S` row of trial 1 has no `E` row, and trial 0 has both. |
| 878 | `          [f[1] for f in rows.get("S", [])] == ["0", "1"] and [f[1] for f in rows.get("E", [])] == ["0"], rows.get("E"))` | Continues the check: the `S` rows are those of the trials 0 and 1, and the only `E` row is that of trial 0. The runner prints the `S` row before a trial and all other rows after it. So the analysis can find an interrupted trial: a trial-start record without a trial-complete record, as the design asks. |
| 879 | `    check("g: no W row of the interrupted trial", not of_trial(rows, "W", 1))` | Check g: the output holds no `W` row of the interrupted trial. So no half measurement of it can be used. |
| 881 | `    args = ["--seq", "oldread,asmread@1M,oldread,read", "--bytes", "8M", "--rounds", "2", "--min-ms", "20", "--stop", "pass",` | `args`: a run in the interval mode. The sequence is `oldread`, `asmread` on 1 MiB, `oldread`, `read`. The buffer has 8 MiB. The sequence runs in 2 rounds. Each interval lasts at least 20 ms. With `--stop pass` a thread runs whole passes and stops at the first clock read at or after that minimum time. |
| 882 | `            "--cpus", str(E.cpu), "--threads", "1"]` | Continues line 881: the worker CPU and 1 thread. |
| 883 | `    rc, out, err = run(args)` | Runs these arguments with the runner under test. |
| 884 | `    rc0, out0, _ = run(args, binary=E.bin_old)` | Runs the same arguments with `E.bin_old`, the binary that was built from `bwx.c`, the first runner. |
| 885 | `    r = rows_of(out)` | `r`: the output of the runner under test, sorted by row type. |
| 886 | `    check("g: --seq mode prints 8 I rows, 8 T rows and 8 P rows", rc == 0 and` | Check g: the interval mode prints 8 `I` rows, 8 `T` rows and 8 `P` rows. |
| 887 | `          [len(r.get(k, [])) for k in "ITP"] == [8, 8, 8], (rc, err))` | Continues the check: the three counts. 8 is 4 kernels of the sequence times 2 rounds. An `I` row is one interval, a `T` row is one thread of an interval, and a `P` row is the page state of a buffer. |
| 889 | `    def shape(text):` | Starts the inner function `shape`. It reduces an output text to its form, without the measured values. |
| 890 | `        return [line if line.startswith("#") else (line.split(",")[0], len(line.split(",")), line.split(",")[1:4]) for line in text.splitlines()]` | Returns one item per line of the text. A comment line stays whole. A data row becomes the row type, the number of fields and the fields 1 to 3. For an `I` row and a `T` row these are the round, the position and the kernel. |
| 892 | `    check("g: --seq mode: comment lines byte for byte and row order as the binary built from bwx.c",` | Check g: in the interval mode the comment lines are equal byte for byte, and the rows have the same order, as in the output of the binary built from `bwx.c`. |
| 893 | `          rc0 == 0 and shape(out) == shape(out0))` | Continues the check: both shapes are equal. So the code of the trial mode did not change what the interval mode prints. The design uses the unchanged interval mode to repeat an earlier measurement. |
| 894 | `    check("g: that comparison can fail: another sequence gives another shape",` | Check g: that comparison can fail. |
| 895 | `          shape(out) != shape(run(args[:1] + ["oldread,read"] + args[2:])[1]))` | Continues the check: a run with the shorter sequence `oldread,read` has another shape. |

### `test_source`: the runner source holds the text of the first runner (lines 898 to 930)

| Line | Source | Explanation |
|---:|---|---|
| 898 | `def test_source():` | Starts the test `test_source`. The names of its checks start with `source:`. |
| 899 | `    """bwx8.c holds the text of bwx.c"""` | Description text: `bwx8.c` holds the text of `bwx.c`, the source of the first runner. |
| 900 | `    with open(os.path.join(OLD, "bwx.c")) as f:` | Opens `bwx.c`, the source of the first runner. |
| 901 | `        old = f.read()` | `old`: its whole text. |
| 902 | `    with open(os.path.join(HERE, "bwx8.c")) as f:` | Opens `bwx8.c`. |
| 903 | `        new = f.read()` | `new`: its whole text. |
| 904 | `    a, b = old.index("#define _GNU_SOURCE"), old.index('#include "bwx_selftest.c"')` | `a`, `b`: two positions in `bwx.c`: the line `#define _GNU_SOURCE` and the line that includes the self-test file of `bwx`. The text between them holds the kernels, the function `call`, the buffer allocation and the code of the interval mode up to the function `parse_events`. |
| 905 | `    check("source: bwx.c from '#define _GNU_SOURCE' to the end of parse_events() stands unchanged in bwx8.c",` | Check: the text of `bwx.c` from `#define _GNU_SOURCE` to the end of `parse_events()` stands unchanged in `bwx8.c`. |
| 906 | `          new.count(old[a:b]) == 1)` | Continues the check: that old text must stand exactly once in `bwx8.c`. So the kernels and the function `call` of the first runner are unchanged. The design asks to keep the bodies of the read loops and the way in which they are called. |
| 907 | `    kernels_end = new.index(old[a:b]) + len(old[a:b])` | `kernels_end`: the position where that old text ends in `bwx8.c`. |
| 908 | `    check("source: every line of the trial mode stands after that text",` | Check: every line of the trial mode stands after that text. |
| 909 | `          min(new.index(s) for s in ("timed_sequence", "trial_main", "tclock", "struct trial")) > kernels_end)` | Continues the check: the first place of each of the names `timed_sequence`, `trial_main`, `tclock` and `struct trial` lies after `kernels_end`. The build keeps the order of the source. So code that is added after the kernels does not move them. |
| 910 | `    hook = ('    for (int i = 1; i < argc; i++)\n        if (!strcmp(argv[i], "--trial"))\n'` | `hook`: the three source lines that start the trial mode. They loop over the arguments and compare each one with `--trial` ... |
| 911 | `            '            return trial_main(argc, argv);\n')` | Continues line 910: ... and call `trial_main` when one argument is `--trial`. |
| 912 | `    check("source: main() of bwx8.c is main() of bwx.c plus the 3 lines that start the trial mode",` | Check: `main()` of `bwx8.c` is `main()` of `bwx.c` plus the 3 lines that start the trial mode. |
| 913 | `          new.count(hook) == 1 and new[new.index("int main("):].replace(hook, "") == old[old.index("int main("):])` | Continues the check: the hook stands once in `bwx8.c`. The text from `int main(` to the end of the file, without the hook, equals the same part of `bwx.c`. So apart from the hook, `main()` is the code of the first runner. |
| 914 | `    with open(os.path.join(OLD, "bwx_selftest.c")) as f:` | Opens `bwx_selftest.c`, the self-test file of the first runner. |
| 915 | `        old_st = f.read()` | `old_st`: its whole text. |
| 916 | `    with open(os.path.join(HERE, "bwx8_selftest.c")) as f:` | Opens `bwx8_selftest.c`. |
| 917 | `        new_st = f.read()` | `new_st`: its whole text. |
| 918 | `    a, b = old_st.index("static int failures;"), old_st.index("static int selftest(void)")` | `a`, `b`: two positions in the self-test file of the first runner: the line `static int failures;` and the head of the function `selftest`. The text between them holds the checks of the kernels. |
| 919 | `    check("source: the kernel checks of bwx_selftest.c stand unchanged in bwx8_selftest.c", new_st.count(old_st[a:b]) == 1)` | Check: the kernel checks of `bwx_selftest.c` stand unchanged in `bwx8_selftest.c`. The old text between `a` and `b` must stand exactly once in the new file. So the self-test still checks every kernel in the way of the first runner. |
| 921 | `    def syms(binary):` | Starts the inner function `syms`. It reads the kernel symbols of a binary. |
| 922 | `        out = subprocess.run(["nm", "-S", binary], stdout=subprocess.PIPE, universal_newlines=True).stdout` | Runs `nm -S` on the binary. It lists each symbol with its address and its size. |
| 923 | `        return {p[3]: (int(p[0], 16) % 64, p[1]) for p in (line.split() for line in out.splitlines())` | Returns a dictionary. The key is a symbol name. The value is the address modulo 64 and the size as text. |
| 924 | `                if len(p) == 4 and p[3].startswith("k_")}` | Continues line 923: only lines with 4 fields whose name starts with `k_` are taken. These are the kernel functions. |
| 926 | `    s_old, s_new = syms(E.bin_old), syms(E.bin)` | `s_old`, `s_new`: the kernel symbols of two local builds: `bwx`, the first runner, and `bwx8`, the runner under test. |
| 927 | `    check("source: the 21 kernels have the same start modulo 64 and the same size in the local builds of bwx and bwx8",` | Check: the 21 kernels have the same start modulo 64 and the same size in the local builds of `bwx` and `bwx8`. |
| 928 | `          len(s_old) == 21 and s_old == s_new, {k: (s_old[k], s_new.get(k)) for k in s_old if s_old[k] != s_new.get(k)})` | Continues the check: the first runner has 21 kernels, and the two dictionaries are equal. The start modulo 64 is the place of a function inside a 64-byte block of code. The design keeps this place and the loop bodies fixed. An equal size shows that the machine code of a kernel has the same length. The detail lists each kernel whose values differ. |

### `test_selftest`: the self-test of the runner, and builds that it must reject (lines 931 to 952)

| Line | Source | Explanation |
|---:|---|---|
| 931 | `def test_selftest():` | Starts the test `test_selftest`. |
| 932 | `    rc, out, err = run(["--selftest"])` | Runs the runner with `--selftest`. The self-test checks what the kernels do to memory and how the trial mode counts bytes and times. It measures no rate. |
| 933 | `    trial_lines = [line for line in out.splitlines() if line.startswith("trial,")]` | `trial_lines`: the lines of its output that start with `trial,`. Each one is one check of the trial mode and ends with `pass` or `FAIL`. |
| 934 | `    check("selftest: status 0, no FAIL line, 19 checks of the trial mode",` | Check: the self-test ends with status 0 and no `FAIL` line, and it has 19 checks of the trial mode. |
| 935 | `          rc == 0 and "FAIL" not in out and out.rstrip().endswith("# failures=0") and len(trial_lines) == 19 and` | Continues the check: status 0, the word `FAIL` nowhere, the last line `# failures=0`, and 19 lines that start with `trial,` ... |
| 936 | `          all(line.endswith(",pass") for line in trial_lines), (rc, err, len(trial_lines)))` | Continues the check: ... and every such line ends with `,pass`. The fixed count shows that no check of the self-test was lost. On a failure the status, the error output and the count are printed. |
| 937 | `    # the self-test must fail on a broken wrapper: a build that counts one pass too many per clock read` | Comment: the self-test must fail on a broken wrapper, a build that counts one pass too many per clock read. A wrapper here is the code of the runner around the kernel call. |
| 938 | `    with open(os.path.join(HERE, "bwx8.c")) as f:` | Opens `bwx8.c`. |
| 939 | `        src = f.read()` | `src`: the whole source text of the runner. |
| 940 | `    good = "        x->bytes = bytes;\n"` | `good`: the source line that stores the byte total of a window, `x->bytes = bytes;`. |
| 941 | `    for name, bad in (("a window that counts 256 bytes too many", "        x->bytes = bytes + 256;\n"),` | Loops over two defects. Defect 1: the stored byte total of a window is 256 bytes too high. The comment of line 937 names another defect, one pass too many per clock read. The code does not build that one. |
| 942 | `                      ("a window whose end is before its start", "        x->bytes = bytes; t1 = t0 - 1;\n")):` | Defect 2: the byte total is right, but the end time of the window is set to 1 ns before its start time. |
| 943 | `        d = os.path.join(E.tmp, "broken")` | `d`: the folder `broken` in the temporary folder. Both defects are built in this one folder, one after the other. |
| 944 | `        os.makedirs(d, exist_ok=True)` | Creates it. No error when it exists. |
| 945 | `        with open(os.path.join(d, "bwx8.c"), "w") as f:` | Opens `bwx8.c` in that folder for writing. |
| 946 | `            f.write(src.replace(good, bad))` | Writes the source in which every place of the line `good` holds the line of the defect. |
| 947 | `        shutil.copy(os.path.join(HERE, "bwx8_selftest.c"), d)` | Copies `bwx8_selftest.c` into the folder. |
| 948 | `        ok = src.count(good) == 1 and subprocess.run(["gcc"] + CFLAGS + ["-o", os.path.join(d, "bwx8"), os.path.join(d, "bwx8.c")]).returncode == 0` | `ok`: true when the line `good` stands exactly once in the source and `gcc` built the copy with exit status 0. When the line does not stand exactly once, `gcc` is not started. |
| 949 | `        rc, out, _ = run(["--selftest"], binary=os.path.join(d, "bwx8"))` | Runs the self-test of the binary in that folder. When no binary exists there, this call raises a Python error. |
| 950 | `        check("selftest: status 1 for a build with " + name, ok and rc == 1 and "trial," in out and ",FAIL" in out, rc)` | Check: the self-test ends with status 1 for a build with that defect. The build worked, the status is 1, and the output holds the texts `trial,` and `,FAIL`. So the self-test is shown to fail on a window with a wrong byte count or with wrong times. A runner with such a defect would report wrong rates. The two texts are tested separately. So the condition does not prove that the failed line is a check of the trial mode. |

### `test_selftest_rows`, `run_listing` and `shift_block` (lines 953 to 979)

| Line | Source | Explanation |
|---:|---|---|
| 953 | `def test_selftest_rows():` | Starts the test `test_selftest_rows`. |
| 954 | `    """the row checks of the self-test fail on a build that prints a wrong value"""` | Description text: the row checks of the self-test must fail on a build that prints a wrong value. |
| 955 | `    for n, name in enumerate(ROW_MUTANTS):` | Loops over the defects of the output rows, `ROW_MUTANTS` (line 373). |
| 956 | `        b = mutant_build(name, "row%d" % n)` | `b`: a build of the runner with that defect. |
| 957 | `        rc, out, _ = run(["--selftest"], binary=b) if b else (None, "", "")` | Runs its self-test. Without a build the status is `None`. |
| 958 | `        check("selftest: status 1 for a build with " + name, rc == 1 and ",FAIL" in out, rc)` | Check: the self-test ends with status 1 and prints a line with `,FAIL`. The self-test lets the runner print the rows of a record with known values and compares the text. So a runner that prints a wrong field, for example the wall time as CPU time, does not pass its own self-test. |
| 961 | `def run_listing(args):` | Starts the function `run_listing`. It runs the listing check with the arguments `args`. |
| 962 | `    r = subprocess.run([sys.executable, os.path.join(HERE, "check_listing8.py")] + args, stdout=subprocess.PIPE,` | Starts `check_listing8.py` with the Python interpreter that runs this test. |
| 963 | `                       stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that starts the listing check: the error output goes into the standard output, and the result is text. |
| 964 | `    return r.returncode, r.stdout` | Returns the exit status and the output. |
| 967 | `def shift_block(text, binary, kernel, by):` | Starts the function `shift_block`. It moves one kernel of a listing text to other addresses. |
| 968 | `    """adds 'by' to every address of one '=== binary kernel ===' block of a listing"""` | Description text: it adds `by` to every address of one block of a listing. A block starts with a head line `=== binary kernel ===`. |
| 969 | `    out, inside = [], False` | `out`: the new lines. `inside`: whether the current line belongs to the block to move. |
| 970 | `    for line in text.split("\n"):` | Loops over the lines of the listing. |
| 971 | `        if line.startswith("==="):` | A line that starts with `===` is the head line of a block. |
| 972 | `            inside = line == "=== %s %s ===" % (binary, kernel)` | `inside` is true from the head line of the wanted binary and kernel on, and false from every other head line on. |
| 973 | `        elif inside:` | For a line inside the wanted block: |
| 974 | `            line = re.sub(r"^(\s*)([0-9a-f]+)(:\| <)", lambda m: "%s%0*x%s" % (m.group(1), len(m.group(2)), int(m.group(2), 16) + by, m.group(3)), line)` | Adds `by` to the address at the start of the line. The pattern matches optional spaces, a hex number and then a colon (an instruction line) or a space with `<` (the line with the function name). The new number gets the same number of digits. |
| 975 | `            line = re.sub(r"\b([0-9a-f]+) <k_", lambda m: "%x <k_" % (int(m.group(1), 16) + by), line)` | Adds `by` to every branch target of the form hex number, space, `<k_`. So a branch inside the kernel still points to the same instruction. |
| 976 | `        out.append(line)` | Adds the line to `out`. |
| 977 | `    return "\n".join(out)` | Returns the lines as one text. |

### `test_listing_saved`: the listing check on the saved listing (lines 980 to 1000)

| Line | Source | Explanation |
|---:|---|---|
| 980 | `def test_listing_saved():` | Starts the test `test_listing_saved`. The names of its checks start with `listing:`. |
| 981 | `    """check_listing8.py on the saved accepted listing of bwx and on changed copies"""` | Description text: the test runs `check_listing8.py` on the saved accepted listing of `bwx` and on changed copies. |
| 982 | `    ref = os.path.join(OLD, "crb-build-2")` | `ref`: the folder `crb-build-2` in the folder of the first runner. By the description of the listing check it holds the saved accepted build of `bwx`. |
| 983 | `    with open(os.path.join(ref, "listing.txt")) as f:` | Opens `listing.txt` of that folder, the machine-code listing of the saved build. |
| 984 | `        listing = f.read().split("=== bwx_o0 ")[0].replace("=== bwx ", "=== bwx8 ")  # the blocks of binary bwx only` | `listing`: the part of that file before the first head line of the binary `bwx_o0`, with the binary name `bwx8` in place of `bwx` in every head line. By the comment these are the blocks of the binary `bwx` only. The file also holds blocks of other binaries after them. The result represents a build of `bwx8` whose 21 kernels are exactly the accepted ones. |
| 985 | `    with open(os.path.join(ref, "offsets.tsv")) as f:` | Opens `offsets.tsv` of that folder. It is the offsets table of the saved build. It has one row per kernel with the start address, the loop start and the loop start modulo 64. |
| 986 | `        offs = f.read().replace("\nbwx\t", "\nbwx8\t")` | `offs`: that table with the binary name `bwx8` in place of `bwx` at the start of each row of the binary `bwx`. The rows of the other binaries stay as they are. |
| 987 | `    d = os.path.join(E.tmp, "listing")` | `d`: the folder `listing` in the temporary folder. |
| 988 | `    os.makedirs(d, exist_ok=True)` | Creates it. No error when it exists. |
| 990 | `    def case(name, want_rc, new_listing, new_offs=offs, want_text=None):` | Starts the inner function `case`. It writes a listing and an offsets table to files, runs the listing check on them and checks the result. `want_rc` is the expected exit status. `want_text` is a text that the output must hold. Without `new_offs` the case uses the good table `offs`. |
| 991 | `        with open(os.path.join(d, "listing.txt"), "w") as f:` | Opens `listing.txt` in the folder `d` for writing. |
| 992 | `            f.write(new_listing)` | Writes the listing of this case. |
| 993 | `        with open(os.path.join(d, "offsets.tsv"), "w") as f:` | Opens `offsets.tsv` in the folder `d` for writing. |
| 994 | `            f.write(new_offs)` | Writes the offsets table of this case. |
| 995 | `        rc, out = run_listing([os.path.join(d, "listing.txt")])` | Runs the listing check on the listing file. It finds the offsets table beside it. Its reference is the saved build in the folder `crb-build-2`, the default of the script. |
| 996 | `        check("listing: " + name, rc == want_rc and (want_text is None or want_text in out), "rc=%d %s" % (rc, out[-300:]))` | Check: the exit status is the expected one, and the output holds the expected text when one is given. On a failure the status and the last 300 characters of the output are printed. |
| 997 | `        return out` | Returns the output, for further checks. |
| 999 | `    out = case("the saved listing of bwx under the name bwx8 passes (exit 0)", 0, listing)` | Case: the saved listing of `bwx` under the name `bwx8` passes with exit status 0. This is the listing of a good build. |
| 1000 | `    check("listing: 21 kernels compared, 21 rows ok", out.count("\tsame\tok") == 21 and "kernels=21 failed_rows=0" in out, out[-200:])` | Check: 21 kernels were compared and 21 rows are ok. 21 rows end with the columns `same` and `ok`. The column `same` says that the text of the kernel equals the reference. The result `ok` says that no check of the row failed. The summary line holds `kernels=21 failed_rows=0`. |

### `test_listing_saved`: the listing check must reject changed kernels (lines 1001 to 1051)

| Line | Source | Explanation |
|---:|---|---|
| 1001 | `    one = "ldp\tq29, q28, [x0, #32]"` | `one`: one load instruction of the kernel `read`, as the listing prints it. A case below changes it. |
| 1002 | `    check("listing: the instruction to change stands once in k_read of bwx8",` | Check: the instruction to change stands once in `k_read` of `bwx8`. |
| 1003 | `          listing.split("=== bwx8 read ===")[1].split("===")[0].count(one) == 1)` | Continues the check: the count in the block of `read` is 1. So the change below changes exactly one place. |
| 1004 | `    head, rest = listing.split("=== bwx8 read ===")` | `head`, `rest`: the listing before and after the head line of the kernel `read`. |
| 1005 | `    case("one changed instruction in k_read fails (exit 1)", 1,` | Case: one changed instruction in the kernel `read` must fail with exit status 1. |
| 1006 | `         head + "=== bwx8 read ===" + rest.replace(one, "ldp\tq29, q28, [x0, #48]", 1), want_text="read\t3a20\t3a24\t36\t36\tDIFFERS\tFAIL")` | Continues the case: the offset of that load is 48 in place of 32. The output must hold the row of `read` with the start 3a20, the loop start 3a24, the loop offset 36 in both columns, the text column `DIFFERS` and the result `FAIL`. The place of the loop is unchanged. Only the comparison of the instructions finds this defect. |
| 1007 | `    case("one added nop before the loop of k_asmread fails", 1,` | Case: one added `nop` before the loop of `k_asmread` must fail. |
| 1008 | `         listing.replace("    3b54:\tldp\tq0, q1, [x0]", "    3b50:\tnop\n    3b54:\tldp\tq0, q1, [x0]", 1), want_text="asmread")` | Continues the case: a line with a `nop` at the address 3b50 is put before the loop start of `k_asmread`, the load at the address 3b54. The function text then has one instruction more than the reference. The output must name `asmread`. |
| 1009 | `    shifted = shift_block(listing, "bwx8", "asmread", 4)` | `shifted`: the listing with every address of `k_asmread` moved up by 4 bytes (line 967). |
| 1010 | `    offs_shifted = offs.replace("bwx8\tasmread\tk_asmread\t3b40\t3b54\t20", "bwx8\tasmread\tk_asmread\t3b44\t3b58\t24")` | `offs_shifted`: the offsets table with the row of `asmread` moved in the same way: start 3b44, loop start 3b58, offset 24. |
| 1011 | `    check("listing: the shifted copy differs from the saved one", shifted != listing and offs_shifted != offs)` | Check: the shifted copy differs from the saved one. So the next cases test a changed input. |
| 1012 | `    case("k_asmread shifted by 4 bytes, same text, fails on the loop offset (exit 1)", 1, shifted, offs_shifted,` | Case: `k_asmread` shifted by 4 bytes, with the same text, must fail on the loop offset with exit status 1. |
| 1013 | `         want_text="asmread\t3b44\t3b58\t24\t20\tsame\tFAIL: loop offset modulo 64 is 24, reference 20")` | Continues the case: the expected row of `asmread`: start 3b44, loop start 3b58, loop offset 24 against 20 in the reference, the text column `same`, and the result `FAIL: loop offset modulo 64 is 24, reference 20`. The instructions are equal. Only the place of the loop inside a 64-byte block differs. The design asks to keep the loop offsets modulo 64. |
| 1014 | `    case("the same shift with an offsets.tsv that still says 20 fails", 1, shifted, want_text="offsets.tsv gives 20")` | Case: the same shifted listing with an offsets table that still says 20 must fail. The output must hold `offsets.tsv gives 20`. So a table that was not updated cannot hide a moved loop. The check computes the loop offset from the listing. |
| 1015 | `    case("an offsets.tsv row that differs from the listing fails", 1, listing,` | Case: an offsets row that differs from the listing must fail. |
| 1016 | `         offs.replace("bwx8\toldread\tk_oldread\t3680\t36e8\t40", "bwx8\toldread\tk_oldread\t3680\t36e8\t0"), want_text="offsets.tsv gives 0")` | Continues the case: the last column of the row of `oldread` (start 3680, loop start 36e8) is 0 in place of 40. The output must hold `offsets.tsv gives 0`. |
| 1017 | `    whole = listing` | `whole`: a copy of the listing, for the next case. |
| 1018 | `    for k in re.findall(r"=== bwx8 (\S+) ===", listing):` | Loops over the names of all kernels of `bwx8` in the listing. The pattern finds the kernel name in each head line. |
| 1019 | `        whole = shift_block(whole, "bwx8", k, 0x1040)` | Moves the block of the kernel up by 0x1040 bytes. That is 65 times 64. |
| 1020 | `    case("all kernels moved by a multiple of 64 bytes pass: addresses are not compared", 0, whole)` | Case: a listing in which all kernels are moved by a multiple of 64 bytes passes. The listing check does not compare addresses. It compares the instructions and the loop offset modulo 64, and such a move changes neither. |
| 1021 | `    block = listing.split("=== bwx8 read_sparse ===")[1].split("===")[0]` | `block`: the text of the block of the kernel `read_sparse`. |
| 1022 | `    case("a listing without k_read_sparse fails", 1, listing.replace("=== bwx8 read_sparse ===" + block, ""), want_text="no listing or no loop")` | Case: a listing without `k_read_sparse` must fail. The output must hold `no listing or no loop`. A build that lacks a kernel of the reference is not accepted. |
| 1023 | `    case("a listing with a kernel that the reference lacks fails", 1,` | Case: a listing with a kernel that the reference does not have must fail. |
| 1024 | `         listing + "\n=== bwx8 read_new ===\n" + block, want_text="read_new")` | Continues the case: a block with the kernel name `read_new` is added. The output must name `read_new`. The design says to add no new variant of a read loop before its stage 5. |
| 1025 | `    got = "ldr\tx3, [x3, #4072]"` | `got`: a load instruction of the old read kernel, as the listing prints it. With the `adrp` instruction before it, it loads a pointer from the table of global addresses of the binary, here at the offset 4072. The linker sets the place of a pointer in that table. |
| 1026 | `    check("listing: the pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got) == 2)` | Check: this pointer load stands exactly 2 times in the listing. The name of the check says that the two places are `k_oldread` and `k_oldread2`. The condition counts the whole listing and does not test the kernels. |
| 1027 | `    got0 = "ldr\tx0, [x0, #4072]"` | `got0`: the second pointer load of that kind, through the register `x0`. |
| 1028 | `    check("listing: the second pointer load after adrp stands in k_oldread and k_oldread2", listing.count(got0) == 2)` | Check: it also stands 2 times in the listing. |
| 1029 | `    out = case("another place of the stack-guard pointer in the table of the linker, the same in all four loads, "` | Case: another place of the stack-guard pointer in the table of the linker, the same in all four loads, ... |
| 1030 | `               "passes with a note", 0, listing.replace(got, "ldr\tx3, [x3, #4064]").replace(got0, "ldr\tx0, [x0, #4064]"),` | Continues the case: ... passes with a note. All four loads get the offset 4064 in place of 4072. |
| 1031 | `               want_text="\tsame\tNOTE: got_offset_differs (4064,4064, reference 4072,4072)")` | Continues the case: the output must hold a row with the text column `same` and the result `NOTE: got_offset_differs (4064,4064, reference 4072,4072)`. The offset is set by the linker and is no part of the read loop. So the listing check accepts it, and it prints a note for a person to read. |
| 1032 | `    check("listing: the two rows with the note do not print a plain ok", out.count("\tsame\tok") == 19, out[-300:])` | Check: the two rows with the note do not print a plain `ok`. Only 19 rows end with `same` and `ok`: the 21 kernels of the reference without these two. |
| 1033 | `    adrp, stub = "adrp\tx3, 1f000 <__FRAME_END__+0x1613c>", "bl\t1940 <__stack_chk_fail@plt>"` | `adrp`: the instruction that gives the page of the table. `stub`: the call of `__stack_chk_fail`, the function for a failed stack guard. |
| 1034 | `    check("listing: the adrp before that load and the call of the stack-guard failure stand in k_oldread and k_oldread2",` | Check: the `adrp` before that load and the call of the stack-guard failure stand in `k_oldread` and `k_oldread2`. |
| 1035 | `          listing.count(adrp) == 2 and listing.count(stub) == 2)` | Continues the check: each of the two texts stands 2 times in the listing. |
| 1036 | `    case("the first pointer load of k_oldread from another page of the table fails (exit 1)", 1,` | Case: the first pointer load of `k_oldread` from another page of the table must fail with exit status 1. |
| 1037 | `         listing.replace(adrp, "adrp\tx3, 2a000 <some_other_table>", 1), want_text="use 2 places of the table")` | Continues the case: the first `adrp` gets another page and another symbol name. The output must hold `use 2 places of the table`. A kernel that loads from a second place of the table loads another pointer than the reference does. |
| 1038 | `    case("the first pointer load of k_oldread from another offset fails", 1,` | Case: the first pointer load of `k_oldread` from another offset must fail. |
| 1039 | `         listing.replace(got, "ldr\tx3, [x3, #8]", 1), want_text="use 2 places of the table")` | Continues the case: the first load gets the offset 8. The output must hold `use 2 places of the table`. |
| 1040 | `    case("k_oldread2 with its two pointer loads from another place than k_oldread fails", 1,` | Case: `k_oldread2` with its two pointer loads from another place than `k_oldread` must fail. |
| 1041 | `         "=== bwx8 oldread2 ===".join([listing.split("=== bwx8 oldread2 ===")[0],` | Continues the case: the listing is cut at the head line of `oldread2` and joined again. The part before it stays as it is ... |
| 1042 | `                                       listing.split("=== bwx8 oldread2 ===")[1].replace("[x3, #4072]", "[x3, #16]", 1)` | Continues the case: ... and in the part after it the first load through `x3` gets the offset 16 ... |
| 1043 | `                                       .replace("[x0, #4072]", "[x0, #16]", 1)]),` | Continues the case: ... and the first load through `x0` gets the offset 16 too. |
| 1044 | `         want_text="over all kernels")` | Continues the case: the output must hold `over all kernels`. Each function alone uses one place of the table, but the two functions together use two. |
| 1045 | `    case("a call of another function in place of the stack-guard failure fails", 1,` | Case: a call of another function in place of the stack-guard failure must fail. |
| 1046 | `         listing.replace(stub, "bl\t9999 <abort@plt>", 1), want_text="DIFFERS")` | Continues the case: the first call of `__stack_chk_fail` becomes a call of `abort`. The output must hold `DIFFERS`. A target outside the function is compared by its symbol name. |
| 1047 | `    case("another offset in a load from the stack fails", 1, listing.replace("ldr\tx2, [sp, #136]", "ldr\tx2, [sp, #128]", 1),` | Case: another offset in a load from the stack must fail. The first such load gets the offset 128. |
| 1048 | `         want_text="DIFFERS")` | Continues the case: the output must hold `DIFFERS`. |
| 1049 | `    case("a listing with no block of bwx8 cannot be used (exit 2)", 2, listing.replace("=== bwx8 ", "=== other "))` | Case: a listing with no block of `bwx8` cannot be used: exit status 2. Every head line gets the binary name `other`. By the description of the listing check, exit status 2 means that a file could not be used. It is not the status of a failed check, which is 1. |

### `test_build_scripts`: the build script stops when the marker file exists (lines 1052 to 1096)

| Line | Source | Explanation |
|---:|---|---|
| 1052 | `def test_build_scripts():` | Starts the test `test_build_scripts`. |
| 1053 | `    """build8.sh on this machine, and check_listing8.py on two real listings of one compiler"""` | Description text: the test runs `build8.sh` on this machine, and `check_listing8.py` on two real listings of one compiler. |
| 1054 | `    cpus = ",".join(str(c) for c in E.allowed)` | `cpus`: the CPUs that the test process may use, as a text with commas. The build script takes it as the CPU list of its own run. |
| 1055 | `    new, old = os.path.join(E.tmp, "new"), os.path.join(E.tmp, "old")` | `new`, `old`: two folders in the temporary folder. `new` is for a build of the runner under test. `old` is for the reference build. |
| 1056 | `    os.makedirs(new)` | Creates the folder `new`. |
| 1057 | `    os.makedirs(old)` | Creates the folder `old`. |
| 1058 | `    for name in ("bwx8.c", "bwx8_selftest.c", "build8.sh"):` | Loops over the three files that a build needs: the source, the self-test file and the build script. |
| 1059 | `        shutil.copy(os.path.join(HERE, name), new)` | Copies the file into the folder `new`. The build script writes only in its own folder. So the test runs a copy, and the folder of the sources stays unchanged. |
| 1060 | `    for name in ("bwx.c", "bwx_selftest.c", "build.sh"):` | Loops over the three files of the first runner: its source, its self-test file and its build script. |
| 1061 | `        shutil.copy(os.path.join(OLD, name), old)` | Copies the file from the folder `OLD` into the folder `old`. The build of line 1122 runs in this copy. Its listing is the reference of the listing comparison. |
| 1062 | `    marker = os.path.join(E.tmp, "marker")` | `marker`: the path of a test marker file in the temporary folder. |
| 1063 | `    open(marker, "w").close()` | Creates that file, empty. |
| 1064 | `    env = dict(os.environ, BWX_CPUS=cpus, BWX_MARKER=marker)` | `env`: the environment for the build script. `BWX_CPUS` holds the CPU list. `BWX_MARKER` holds the path of the test marker file. By the comment in the build script this variable exists only for a test of the marker check. |
| 1065 | `    env.pop("_PINNED", None)` | Removes the variable `_PINNED`, if it is set. The build script sets it when it starts itself again under `taskset`, the tool that sets the CPU list. Without the variable the script does that step. |
| 1066 | `    r = subprocess.run(["bash", os.path.join(new, "build8.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build8.sh` in the folder `new` while the test marker file exists. |
| 1067 | `    check("build8.sh: exit 3 and no file written while the marker file is present",` | Check: `build8.sh` ends with exit status 3 and writes no file while the marker file is present. |
| 1068 | `          r.returncode == 3 and sorted(os.listdir(new)) == ["build8.sh", "bwx8.c", "bwx8_selftest.c"], (r.returncode, os.listdir(new)))` | Continues the check: status 3, and the folder holds only the three copied files. On CRB the marker file exists while another user runs a performance test. A build would use CPU time of that machine. So the script must stop before it compiles. |
| 1069 | `    # The marker file appears while the self-test runs. A script stands for the compiler. The "binary" that it` | Comment: in the next case the marker file appears while the self-test runs. A script replaces the compiler. The fake binary that ... |
| 1070 | `    # writes creates the marker file in its self-test and leaves a file if it is run in any other way.` | Comment: ... it writes creates the marker file in its self-test, and it leaves a file when it is run in any other way. |
| 1071 | `    late = os.path.join(E.tmp, "late")` | `late`: the folder `late` in the temporary folder. |
| 1072 | `    os.makedirs(late)` | Creates it. |
| 1073 | `    for name in ("bwx8.c", "bwx8_selftest.c", "build8.sh"):` | Loops over the three files of a build. |
| 1074 | `        shutil.copy(os.path.join(HERE, name), late)` | Copies the file into the folder `late`. |
| 1075 | `    late_marker, ran = os.path.join(E.tmp, "late-marker"), os.path.join(E.tmp, "late-ran")` | `late_marker`: the path of the marker file of this case. `ran`: the path of a file that shows that the fake binary ran again. |
| 1076 | `    cc = os.path.join(E.tmp, "fake-cc")` | `cc`: the path of the fake compiler, `fake-cc`. |
| 1077 | `    with open(cc, "w") as f:` | Opens it for writing. |
| 1078 | `        f.write('#!/bin/sh\n[ "$1" = --version ] && { echo fake; exit 0; }\n'` | Text of the fake compiler, a shell script. Its first line tells Linux to run it with `sh`. Its second line: when the first argument is `--version`, it prints `fake` and ends with exit status 0. |
| 1079 | `                'while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done\n'` | Text of the fake compiler: a loop over the arguments. When an argument is `-o`, the next one is kept in `out`. That is the path of the binary to write. |
| 1080 | `                'printf \'#!/bin/sh\\nif [ "$1" = --selftest ]; then : > "%s"; echo "# failures=0"; else : > "%s"; fi\\n\' > "$out"\n'` | Text of the fake compiler: it writes the fake binary to that path. The fake binary is a shell script too. Called with `--selftest`, it creates the marker file of this case and prints `# failures=0`, the last line of a passed self-test. Called in any other way, it creates the file `ran`. |
| 1081 | `                'chmod +x "$out"\n' % (late_marker, ran))` | Text of the fake compiler: it makes the fake binary executable. The end of the line puts the two paths into the text above. |
| 1082 | `    os.chmod(cc, 0o755)` | Makes the fake compiler executable (mode 755). |
| 1083 | `    r = subprocess.run(["bash", os.path.join(late, "build8.sh")], env=dict(env, BWX_MARKER=late_marker, CC=cc),` | Runs `build8.sh` in the folder `late`, with the marker path of this case and with the fake compiler in the variable `CC`. |
| 1084 | `                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Continues the call that runs the build script: both outputs are collected. |
| 1085 | `    check("build8.sh: exit 3 and no further run of the binary when the marker file appears during the self-test",` | Check: `build8.sh` ends with exit status 3 and does not run the binary again when the marker file appears during the self-test. |
| 1086 | `          r.returncode == 3 and os.path.exists(late_marker) and os.path.exists(os.path.join(late, "selftest-bwx8.txt")) and` | Continues the check: status 3, the marker file of this case exists, and the file `selftest-bwx8.txt` exists, so the self-test ran ... |
| 1087 | `          not os.path.exists(ran), (r.returncode, os.path.exists(late_marker), os.path.exists(ran), r.stderr[-200:]))` | Continues the check: ... and the file `ran` does not exist. So the script tested the marker file again after the self-test, and it did not start the binary again. Its next step would have run the binary to list the kernels. |
| 1088 | `    env["BWX_MARKER"] = marker + ".none"` | Sets `BWX_MARKER` to a path that does not exist. No marker file is present for the next runs. |
| 1089 | `    r = subprocess.run(["bash", os.path.join(new, "build8.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build8.sh` in the folder `new`. This is a full build on this machine. |
| 1090 | `                       universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1091 | `    made = sorted(os.listdir(new))` | `made`: the sorted names of the files in the folder `new` after the run. |
| 1092 | `    check("build8.sh: exit 0; writes bwx8, build.txt, listing.txt, offsets.tsv, selftest-bwx8.txt",` | Check: `build8.sh` ends with exit status 0 and writes `bwx8`, `build.txt`, `listing.txt`, `offsets.tsv` and `selftest-bwx8.txt`. |
| 1093 | `          r.returncode == 0 and made == sorted(["build8.sh", "bwx8.c", "bwx8_selftest.c", "bwx8", "build.txt", "listing.txt",` | Continues the check: status 0, and the folder holds exactly the three copied files plus the binary, the build record, the listing ... |
| 1094 | `                                                "offsets.tsv", "selftest-bwx8.txt"]), (r.returncode, made, r.stderr[-300:]))` | Continues the check: ... the offsets table and the self-test output. On a failure the status, the file names and the end of the error output are printed. |
| 1095 | `    if r.returncode != 0:` | Tests whether the build failed. |
| 1096 | `        return` | Ends the test in that case. The next checks read the files of the build. |

### `test_build_scripts`: the build record, and a build that the script must reject (lines 1097 to 1117)

| Line | Source | Explanation |
|---:|---|---|
| 1097 | `    with open(os.path.join(new, "build.txt")) as f:` | Opens `build.txt` in the folder `new`. |
| 1098 | `        build = f.read()` | `build`: the whole build record. |
| 1099 | `    with open(os.path.join(OLD, "build.sh")) as f:` | Opens `build.sh`, the build script of the first runner. |
| 1100 | `        old_flags = re.search(r'^CFLAGS="(.*)"$', f.read(), re.M).group(1)` | `old_flags`: the compiler flags of that script. The pattern takes the text between the double quotes of the line that starts with `CFLAGS=`. |
| 1101 | `    check("build8.sh: build.txt holds the CFLAGS of build.sh, no compiler message, the self-test result and 6 digests",` | Check: `build.txt` holds the `CFLAGS` of `build.sh`, no compiler message, the self-test result and 6 checksums. |
| 1102 | `          "## CFLAGS=%s\n" % old_flags in build and "## compiler messages:\n## compiler messages end\n" in build and` | Continues the check: the record holds a line `## CFLAGS=` with exactly these flags, and the line `## compiler messages:` is followed directly by the line `## compiler messages end`. So the build used the flags of the first runner, and the compiler gave no warning. |
| 1103 | `          "## selftest bwx8 exit=0 # failures=0" in build and len(re.findall(r"^[0-9a-f]{64}  ", build, re.M)) == 6, build[-600:])` | Continues the check: the record holds `## selftest bwx8 exit=0 # failures=0`, and 6 lines start with a sha256 (64 hex digits and two spaces). With these checksums a later result can name the exact sources, binary and listing. |
| 1104 | `    t = seq_targets(os.path.join(new, "bwx8"))` | `t`: the branch targets of `timed_sequence` in the binary that the script built (line 249). |
| 1105 | `    check("build8.sh: build.txt lists the branch targets of timed_sequence, as the machine-code rule reads them",` | Check: `build.txt` lists the branch targets of `timed_sequence`, as the machine-code rule reads them. |
| 1106 | `          "## timed_sequence branch targets: %s\n" % " ".join("%s=%d" % (k, t[k]) for k in sorted(t)) in build and` | Continues the check: the record holds a line `## timed_sequence branch targets:` with every target and its count in the form `name=count`, sorted by name ... |
| 1107 | `          not seq_code_problems(t), re.findall(r"^## timed_sequence.*$", build, re.M))` | Continues the check: ... and these targets pass the machine-code rule. So the build script and the test read the same targets from the machine code. On a failure the lines of the record about `timed_sequence` are printed. |
| 1108 | `    seq = os.path.join(E.tmp, "seq")` | `seq`: the folder `seq` in the temporary folder. |
| 1109 | `    os.makedirs(seq)` | Creates it. |
| 1110 | `    for name in ("bwx8_selftest.c", "build8.sh"):` | Loops over the self-test file and the build script. |
| 1111 | `        shutil.copy(os.path.join(HERE, name), seq)` | Copies the file into the folder `seq`. |
| 1112 | `    with open(os.path.join(seq, "bwx8.c"), "w") as f:` | Opens `bwx8.c` in that folder for writing. |
| 1113 | `        f.write(mutant_source(SEQ_MUTANTS[1]) or "")` | Writes the source with the second defect of `SEQ_MUTANTS`: a page read and an output flush before the first target window. Without that source the file is empty. |
| 1114 | `    r6 = subprocess.run(["bash", os.path.join(seq, "build8.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,` | Runs `build8.sh` in the folder `seq`. |
| 1115 | `                        universal_newlines=True)` | Continues the call that runs the build script: the outputs are collected as text. |
| 1116 | `    check("build8.sh: exit 6 for a build with " + SEQ_MUTANTS[1], r6.returncode == 6 and "read_vmstat" in r6.stderr and` | Check: `build8.sh` ends with exit status 6 for a build with that defect. The error output names `read_vmstat` ... |
| 1117 | `          "fflush" in r6.stderr, (r6.returncode, r6.stderr[-300:]))` | Continues the check: ... and `fflush`, the two added calls. Exit status 6 of the build script means that the timed sequence reaches a function that is not allowed there. So a build with such a call is rejected when it is built, before any measurement. The detail is the status and the end of the error output. |

### `test_build_scripts`: real listings and a moved kernel (lines 1118 to 1143)

| Line | Source | Explanation |
|---:|---|---|
| 1118 | `    with open(os.path.join(new, "offsets.tsv")) as f:` | Opens `offsets.tsv` of the full build in the folder `new`. |
| 1119 | `        rows = [line.split("\t") for line in f.read().splitlines()[1:]]` | `rows`: its rows without the header line, each split at the tabs. |
| 1120 | `    check("build8.sh: offsets.tsv has one row per kernel of binary bwx8, each with a loop",` | Check: `offsets.tsv` has one row per kernel of the binary `bwx8`, each with a loop. |
| 1121 | `          len(rows) == 21 and all(r[0] == "bwx8" and r[5].isdigit() for r in rows), rows[:3])` | Continues the check: 21 rows, every row names the binary `bwx8`, and its loop offset is a number. A number shows that the script found a backward branch, and so a loop, in the function. |
| 1122 | `    r = subprocess.run(["bash", os.path.join(old, "build.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build.sh`, the build script of the first runner, in the folder `old`. Both outputs are collected. |
| 1123 | `    if not check("build.sh of bwx runs in a temporary copy (the reference for the next check)", r.returncode == 0, r.stderr[-300:]):` | Check: `build.sh` of `bwx` runs in a temporary copy with exit status 0. Its listing is the reference for the next check. On a failure the end of the error output is printed. |
| 1124 | `        return` | Ends the test when the check before it failed. |
| 1125 | `    ref = ["--ref-listing", os.path.join(old, "listing.txt"), "--ref-offsets", os.path.join(old, "offsets.tsv")]` | `ref`: the arguments that make the listing check use the build in the folder `old` as its reference: its listing and its offsets table. The binary name of the reference stays `bwx`, the default of the script. |
| 1126 | `    rc, out = run_listing([os.path.join(new, "listing.txt")] + ref)` | Runs the listing check on the listing of the full build against that reference. |
| 1127 | `    check("listing: on this machine the 21 kernels of bwx8 equal the kernels of bwx, text and loop offset",` | Check: on this machine the 21 kernels of `bwx8` equal the kernels of `bwx`, in text and in loop offset. |
| 1128 | `          rc == 0 and out.count("\tsame\tok") == 21, out[-400:])` | Continues the check: exit status 0 and 21 rows that end with `same` and `ok`. This runs the whole chain of build script, listing and listing check on real compiler output. It shows for the local compiler that the added trial mode changes no instruction and no loop offset of a kernel. |
| 1129 | `    # a bwx8 build whose kernel was moved must be rejected` | Comment: a build of `bwx8` in which a kernel was moved must be rejected. |
| 1130 | `    moved = os.path.join(E.tmp, "moved")` | `moved`: the folder `moved` in the temporary folder. |
| 1131 | `    os.makedirs(moved)` | Creates it. |
| 1132 | `    for name in ("bwx8.c", "bwx8_selftest.c", "build8.sh"):` | Loops over the three files of a build. |
| 1133 | `        shutil.copy(os.path.join(HERE, name), moved)` | Copies the file into the folder `moved`. |
| 1134 | `    with open(os.path.join(moved, "bwx8.c")) as f:` | Opens `bwx8.c` in that folder. |
| 1135 | `        src = f.read()` | `src`: the source text of the runner. |
| 1136 | `    with open(os.path.join(moved, "bwx8.c"), "w") as f:` | Opens the same file for writing. |
| 1137 | `        f.write(src.replace("#define PAD_asmread 0\n", "#define PAD_asmread 16\n"))` | Writes the source with `PAD_asmread` set to 16 in place of 0. The pad before `k_asmread` then is 16 bytes longer. So the kernel and its loop start 16 bytes later. |
| 1138 | `    r = subprocess.run(["bash", os.path.join(moved, "build8.sh")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` | Runs `build8.sh` in the folder `moved`. The check of this build follows in lines 1140 to 1141. |
| 1139 | `    rc, out = run_listing([os.path.join(moved, "listing.txt")] + ref)` | Runs the listing check on the listing of the build with the moved kernel, against the reference. |
| 1140 | `    check("listing: a real bwx8 build with k_asmread moved by 16 bytes is rejected (exit 1)",` | Check: a real build of `bwx8` with `k_asmread` moved by 16 bytes is rejected with exit status 1. |
| 1141 | `          r.returncode == 0 and rc == 1 and "loop offset modulo 64" in out, (r.returncode, rc, out[-300:]))` | Continues the check: the build itself worked with exit status 0, the listing check ended with exit status 1, and its output holds `loop offset modulo 64`. So a kernel that a build moved is rejected on real compiler output, also when its instructions are unchanged. |

### `main`: settings, the builds, the order of the tests, the summary (lines 1144 to 1181)

| Line | Source | Explanation |
|---:|---|---|
| 1144 | `def main():` | Starts the function `main`. It prepares the settings and the builds and runs all tests. |
| 1145 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg`, the file in which Linux reports the load averages. |
| 1146 | `        print("# system load (1, 5, 15 min): %s; CPUs allowed: %d" % (" ".join(f.read().split()[:3]), len(os.sched_getaffinity(0))))` | Prints a comment line with the three load averages (1, 5 and 15 minutes) and the number of CPUs that the test process may use. |
| 1147 | `    E.allowed = sorted(c for c in os.sched_getaffinity(0) if c <= 119)` | `E.allowed`: the CPUs from 0 to 119 on which the test process may run, sorted. The runner accepts no CPU above 119. |
| 1148 | `    if len(E.allowed) < 3 or 0 not in E.allowed:` | Tests whether fewer than 3 such CPUs exist, or CPU 0 is not among them. The tests need CPU 0, the default CPU of the controlling thread, and two more CPUs. |
| 1149 | `        print("FAIL setup: CPU 0 and two more CPUs from 0 to 119 are needed in the allowed set: %s" % E.allowed)` | Prints a line that starts with `FAIL setup` and shows the allowed CPUs. |
| 1150 | `        return 1` | Returns 1. The script then ends with exit status 1, and no test has run. |
| 1151 | `    E.cpu, E.cpu2 = [c for c in E.allowed if c != 0][:2]  # worker CPU, and a second CPU` | `E.cpu`, `E.cpu2`: the first two allowed CPUs that are not CPU 0. `E.cpu` is the worker CPU of all tests. `E.cpu2` is a second CPU. |
| 1152 | `    E.ctl = E.cpu2                                         # a control CPU that is not the default` | `E.ctl`: that second CPU, as a CPU for the controlling thread that is not the default. |
| 1153 | `    E.absent = next((c for c in range(120) if c not in E.allowed), None)` | `E.absent`: the lowest CPU from 0 to 119 that the test process may not use, or `None` when every one is allowed. |
| 1154 | `    E.tmp = tempfile.mkdtemp(prefix="bwx8-test-")` | `E.tmp`: a new temporary folder whose name starts with `bwx8-test-`. All builds and all files of the tests go there. |
| 1155 | `    E.bin, E.bin_old = os.path.join(E.tmp, "bwx8"), os.path.join(E.tmp, "bwx")` | `E.bin`, `E.bin_old`: the paths of two binaries in the temporary folder: `bwx8` (the runner under test) and `bwx` (the first runner). |
| 1156 | `    print("# worker CPU %d, control CPU 0 (default) or %d, temporary folder %s" % (E.cpu, E.ctl, E.tmp))` | Prints a comment line with the worker CPU, the two possible CPUs of the controlling thread (0 by default, or `E.ctl`) and the temporary folder. |
| 1157 | `    try:` | Starts a block whose end (line 1169) always runs, also after an error. |
| 1158 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin, os.path.join(HERE, "bwx8.c")], stdout=subprocess.PIPE,` | Compiles `bwx8.c` with `gcc` and the flags `CFLAGS` into `E.bin`. |
| 1159 | `                           stderr=subprocess.STDOUT, universal_newlines=True)` | Continues the call that runs the compiler: its messages are collected as one text. |
| 1160 | `        if not check("build: bwx8.c compiles with the flags of build8.sh and no compiler message", r.returncode == 0 and r.stdout == "", r.stdout):` | Check: `bwx8.c` compiles with the flags of `build8.sh` and with no compiler message. A warning counts as a failure. |
| 1161 | `            return 1` | Returns 1 when the build failed. No test can run without the binary. |
| 1162 | `        r = subprocess.run(["gcc"] + CFLAGS + ["-o", E.bin_old, os.path.join(OLD, "bwx.c")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)` | Compiles `bwx.c`, the first runner, into `E.bin_old`. |
| 1163 | `        if not check("build: bwx.c compiles (reference for the --seq mode)", r.returncode == 0):` | Check: `bwx.c` compiles. Its binary is the reference for the checks of the mode `--seq`. |
| 1164 | `            return 1` | Returns 1 when that build failed. |
| 1165 | `        for test in (test_source, test_selftest, test_selftest_rows, test_bad_plans, test_rows, test_sequence_code,` | Loops over the test functions in the order in which they run. This line names the first six: the source, the self-test, the row checks of the self-test, the bad plans, the rows and the timed sequence in the code. |
| 1166 | `                     test_trace, test_counters, test_disturbed, test_placement, test_kill_and_seq, test_listing_saved,` | Continues the list of the tests: the trace, the counters, the disturbed trial, the placement, the killed trial with the interval mode, and the saved listing. |
| 1167 | `                     test_build_scripts):` | Continues the list of the tests: the build scripts. |
| 1168 | `            test()` | Runs the test. A failed check does not stop the loop. An earlier test can store a value in `E` for a later one, as `test_trace` does for `test_counters`. |
| 1169 | `    finally:` | The next lines run in every case, also when a test raised an error or `main` returned early. |
| 1170 | `        if os.environ.get("KEEP"):` | Tests whether the environment variable `KEEP` is set to a text that is not empty. |
| 1171 | `            print("# kept: %s" % E.tmp)` | Prints the path of the temporary folder, which is kept. |
| 1172 | `        else:` | If `KEEP` is not set: |
| 1173 | `            shutil.rmtree(E.tmp, ignore_errors=True)` | Deletes the temporary folder with all its content. Errors of the delete are ignored. |
| 1174 | `    with open("/proc/loadavg") as f:` | Opens `/proc/loadavg` again. |
| 1175 | `        print("# system load at the end: %s" % " ".join(f.read().split()[:3]))` | Prints a comment line with the three load averages at the end. |
| 1176 | `    print("# checks failed: %d%s" % (len(failed), "".join("\n#   " + n for n in failed)))` | Prints the number of failed checks, and under it one line per failed check with its name. |
| 1177 | `    return 1 if failed else 0` | Returns 1 when a check failed, and 0 when none failed. |
| 1180 | `if __name__ == "__main__":` | Tests whether the file runs as a script, and is not loaded as a module by another file. |
| 1181 | `    sys.exit(main())` | Calls `main` and ends the script with its result as the exit status. |
