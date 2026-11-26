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

1. The file starts with its description, the imports and the constants: the folders of the sources and of the reference builds, the names of the added kernels and `M` rows, and the compiler flags ({L1-71}).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed functions, and the order of pin and memory mapping ({L115-365}).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner ({L368-531}).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row ({L534-620}).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows ({L629-720}).
6. `test_sequence_code`: the source text and the machine code of the timed functions hold only the allowed calls, and both rules fail on a build with a defect ({L723-751}).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches ({L754-768}).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported ({L771-803}).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces ({L812-895}).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window ({L898-947}).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints ({L950-988}).
12. `test_source`: `bwx11.c` is the accepted source plus marked additions, the older kernels keep their start, size and order, and the code after the kernels keeps its placement ({L1019-1165}).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect ({L1168-1230}).
14. `test_listing_saved`: the listing check accepts a good listing and rejects each kind of changed kernel and each wrong new kernel ({L1293-1470}).
15. `test_build_scripts`: `build11.sh` stops on the marker file, writes its files, rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must ({L1473-1629}).
16. `test_new_kernels`: the five kernels of round 3 work in the plan parser, in the trial mode and in the interval mode ({L1683-1718}).
17. `test_rec_pad`: `--rec-pad` moves the window records by exactly its value and moves nothing else ({L1721-1818}).
18. `test_hot_copy`: `--hot-copy` prints the rows of a plain run, keeps every rule, and selects the second timed function ({L1845-1918}).
19. `test_nop_kernels`: the three kernels of round 4 work in the plan parser, in the trial mode and in the interval mode ({L1921-1952}).
20. `test_evict`: the evict step writes its memory, lies before the first trial and outside every timed sequence, and changes no other row and no address ({L2004-2212}).
21. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds four binaries, runs the 18 tests, deletes the temporary folder and prints the number of failed checks ({L2215-2263}).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them ({L2219-2221}), or when one of the four first builds fails ({L2232-2250}).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` ({L613}, {L922}, {L1601-1603}, {L1785}, {L2173}).
- A test that raises a Python error ends the script. The temporary folder is still deleted ({L2255-2259}), but the summary lines of {L2260-2262} are not printed.
- `main` does not run the tests in file order ({L2251-2253}). `test_source` and the two self-test tests run first.
  - `test_trace` sets `E.soft_counters`, which `test_counters` reads ({L824}, {L921}).
  - `test_source` sets `E.call8` and builds `E.bin10_placed`, which `test_build_scripts` needs ({L1116}, {L1155-1156}, {L1600-1602}).
- The tests write only into a new temporary folder ({L2225}). It is deleted at the end unless the variable `KEEP` is set.
- The tests read the folders `ref-bwx8` and `ref-bwx10` beside the test file ({L54-55}). The README of the repo says that the `ref-` folders were left out of the repo copy. So `test_source` cannot read its reference files from this copy.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text is no longer found in the source makes its checks fail ({L273-274}, {L468-469}).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the build script under `bash`, and `setarch`. A run that the helper `run` starts may last 120 s at most ({L510}).
- Two tests load the machine on purpose. `test_disturbed` runs an endless loop on the worker CPU during one trial ({L757}). `test_evict` runs an evict step of 256 MiB ({L2070}) and one of 4096 MiB, which writes 4 GiB of memory twice ({L2209}).
- At these places the text and the code do not match.
  - The comment of {L1195} names a build that counts one pass too many per clock read. The two defects that the code builds are others ({L1201-1202}).
  - The name of the check of {L2096-2097} says that the evict step is the last `mmap` before the trials. The condition of {L2098-2099} does not test that part.
  - The test `src is None` of {L273} has no effect, as {L272} already used `src`.
  - The name of the check of {L838} says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them ({L839}). The check of {L832-833} tests where they lie.
  - The name of the check of {L1931-1932} says that the plan uses every nop kernel as previous activity, prefix, predecessor and target. In the plan of {L1923-1926} `read_nop128` is never the previous activity, `read_nop64` never the prefix and `read_nop96` never the predecessor.
  - The names of the checks of {L1370}, {L1372}, {L1378-1379} and {L1391} say that a text stands in `k_oldread` and `k_oldread2`. Each condition only tests that the text stands 2 times in the whole listing.
