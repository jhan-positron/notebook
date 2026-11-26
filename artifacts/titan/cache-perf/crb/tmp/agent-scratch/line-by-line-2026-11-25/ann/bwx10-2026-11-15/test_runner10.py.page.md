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

1. The file starts with its description, the imports and the constants: the folders of the sources and of the reference build, the names of the added kernels and `M` rows, and the compiler flags ({L1-57}).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed functions, and the order of pin and memory mapping ({L101-351}).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner ({L354-510}).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row ({L513-599}).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows ({L608-699}).
6. `test_sequence_code`: the source text and the machine code of the timed functions hold only the allowed calls, and both rules fail on a build with a defect ({L702-730}).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches ({L733-747}).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported ({L750-782}).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces ({L791-874}).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window ({L877-926}).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints ({L929-967}).
12. `test_source`: `bwx10.c` is the accepted source plus marked additions, the older kernels keep their start, size and order, and the code after the kernels keeps its placement ({L976-1072}).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect ({L1075-1129}).
14. `test_listing_saved`: the listing check accepts a good listing and rejects each kind of changed kernel and each wrong new kernel ({L1192-1336}).
15. `test_build_scripts`: `build10.sh` stops on the marker file, writes its files, rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must ({L1339-1478}).
16. `test_new_kernels`: the five kernels of round 3 work in the plan parser, in the trial mode and in the interval mode ({L1531-1565}).
17. `test_rec_pad`: `--rec-pad` moves the window records by exactly its value and moves nothing else ({L1568-1661}).
18. `test_hot_copy`: `--hot-copy` prints the rows of a plain run, keeps every rule, and selects the second timed function ({L1688-1761}).
19. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds three binaries, runs the 16 tests, deletes the temporary folder and prints the number of failed checks ({L1764-1800}).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them ({L1768-1770}), or when one of the three first builds fails ({L1778-1787}).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` ({L592}, {L901}, {L1456}, {L1632}).
- A test that raises a Python error ends the script. The temporary folder is still deleted ({L1792-1796}), but the summary lines of {L1797-1799} are not printed.
- `main` does not run the tests in file order ({L1788-1790}). `test_source` and the two self-test tests run first.
  - `test_trace` sets `E.soft_counters`, which `test_counters` reads ({L803}, {L900}).
  - `test_source` sets `E.call8`, which `test_build_scripts` needs ({L1052}, {L1455}).
- The tests write only into a new temporary folder ({L1774}). It is deleted at the end unless the variable `KEEP` is set.
- The tests read three folders beside the folder of the test file or in it: the folder of the first runner ({L43}), the folder of the runner `bwx8` ({L44}) and `ref-bwx8` ({L45}). The README of the repo says that the `ref-` folders were left out of the repo copy. So `test_source` ({L1066}) and `test_listing_saved` ({L1194-1196}) cannot read their reference files from the repo copy in its present layout. The repo keeps the same two files, `listing.txt` and `offsets.tsv`, in the folder `build-records/bwx8-crb-build-1` of the test `2026-11-15-tackle-8mb`.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text is no longer found in the source makes its checks fail ({L259-260}, {L447-448}).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the listing check `check_listing10.py` under Python ({L1133}), the two build scripts `build10.sh` and `build.sh` under `bash`, and `setarch`. A run that the helper `run` starts may last 120 s at most ({L489}).
- One test loads the machine on purpose: `test_disturbed` runs an endless loop on the worker CPU during one trial ({L736}).
- The check that the other addresses do not move with `--rec-pad` ({L1640-1644}) depends on the environment of the caller. A comment in the later test file `test_runner11.py` says so. By that comment `tw_addr` lies on the stack of the main thread, below the text of the arguments and of the environment. The pad values `0`, `80` and `4000` differ in length, and that can move `tw_addr`.
- At four places the text and the code do not match.
  - The comment of {L1094} names a build that counts one pass too many per clock read. The two defects that the code builds are others ({L1100-1101}).
  - The test `src is None` of {L259} has no effect, as {L258} already used `src`.
  - The name of the check of {L817} says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them ({L818}). The check of {L811-812} tests where they lie.
  - The description text of `seq_source_problems` names three C functions ({L283}). The rule reads the five functions of the table `SEQ_SOURCE` ({L240-244}).
