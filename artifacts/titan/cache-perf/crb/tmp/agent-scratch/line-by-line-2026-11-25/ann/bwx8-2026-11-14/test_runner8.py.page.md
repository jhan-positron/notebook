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

1. The file starts with its description, the imports and the constants: the folder of the first runner, the compiler flags and the header lines of a plan ({L1-41}).
2. The rules are defined. They check the `W`, `E`, `B` and `TR` rows of one trial, the source text and the machine code of the timed function, and the order of pin and memory mapping ({L85-299}).
3. The inputs of the tests are defined: the C text of the logging library, the table of defects, and the helpers that build a runner with a defect, write a plan file and start the runner ({L302-446}).
4. `test_bad_plans`: every plan or option with a defect must give exit status 2, a message and no row ({L449-535}).
5. `test_rows`: a plan with all phases runs, and its `M`, `K`, `S`, `P`, `W`, `B` and `E` rows are checked. Then each rule must fail on changed rows ({L544-635}).
6. `test_sequence_code`: the source text and the machine code of the timed function hold only the allowed calls, and both rules fail on a build with a defect ({L638-658}).
7. `test_disturbed`: a trial that shares its CPU with another process shows a low CPU time and involuntary context switches ({L661-675}).
8. `test_placement`: the logging library shows that each thread pins itself before the buffer is mapped, and a failed `madvise` is reported ({L678-710}).
9. `test_trace`: a run with `--trace` shows that no forbidden event lies in a timed sequence. Then the trace rule must fail on broken traces ({L719-802}).
10. `test_counters`: a counter that does not open is reported, the timing rows stay, and a `C` row holds the change over one target window ({L805-854}).
11. `test_kill_and_seq`: a killed trial leaves an `S` row without an `E` row, and the interval mode prints what the first runner prints ({L857-895}).
12. `test_source`: `bwx8.c` holds the kernels and the interval mode of `bwx.c` unchanged, and the kernels keep their start and their size in the binary ({L898-928}).
13. `test_selftest` and `test_selftest_rows`: the self-test passes with its fixed number of checks, and it fails on builds with a defect ({L931-958}).
14. `test_listing_saved`: the listing check accepts the saved listing of the accepted build and rejects each kind of changed kernel ({L980-1049}).
15. `test_build_scripts`: `build8.sh` stops on the marker file, writes its files and rejects a build with a forbidden call, and its real listings pass or fail the listing check as they must ({L1052-1141}).
16. `main` runs last in the file and first in time. It prints the load, chooses the CPUs, builds two binaries, runs the 13 tests, deletes the temporary folder and prints the number of failed checks ({L1144-1177}).

## Behavior a reader must know

- The tests run on the development machine only. They start no program on CRB and read no result of CRB.
- No rate of these tests is a result. A local build prints `M,kernels,STAND-IN`, and the tests use its times only to check the rules of the rows.
- The exit status is 0 only when every check passed. It is 1 when a check failed, when fewer than 3 CPUs from 0 to 119 are allowed or CPU 0 is not among them ({L1148-1150}), or when one of the two first builds fails ({L1158-1164}).
- A check that cannot run on the machine counts as failed. Its name holds `NOT RUN` ({L528}, {L829}).
- A test that raises a Python error ends the script. The temporary folder is still deleted ({L1169-1173}), but the summary lines of {L1174-1176} are not printed.
- `main` does not run the tests in file order ({L1165-1167}). `test_source` and the two self-test tests run first. `test_trace` sets `E.soft_counters`, which `test_counters` reads ({L731}, {L828}).
- The tests write only into a new temporary folder ({L1154}). It is deleted at the end unless the variable `KEEP` is set.
- The tests read the folder of the first runner beside the folder of the test file ({L33}), and in it the sub folder `crb-build-2` ({L982}). The folder `bwx-2026-11-13` of the repo copy has no such sub folder. The repo keeps its two files `listing.txt` and `offsets.tsv` in the folder `build-records/bwx-crb-build-2` of the test `2026-11-13-new-read-kernel`. So `test_listing_saved` cannot read its reference from the repo copy in its present layout.
- Every rule is tested in two ways: it must pass on the output of the runner, and it must report a problem on changed rows or on a build with a defect. A defect whose text does not stand exactly once in the source makes its checks fail ({L382-383}).
- What the tests start: `gcc` many times (each defect is a full build of the runner), the runner, `objdump`, `nm`, the listing check `check_listing8.py` under Python ({L962}), and the two build scripts `build8.sh` and `build.sh` under `bash`. A run that the helper `run` starts may last 120 s at most ({L425}).
- One test loads the machine on purpose: `test_disturbed` runs an endless loop on the worker CPU during one trial ({L664}).
- At two places the text and the code do not match.
  - The comment of {L937} names a build that counts one pass too many per clock read. The two defects that the code builds are others ({L941-942}).
  - The name of the check of {L745} says that the page reads and the outputs lie outside the timed sequence. Its condition only counts them ({L746}). The check of {L739-740} tests where they lie.
- The check of {L950} tests the texts `trial,` and `,FAIL` separately. So it does not prove that the failed line of the self-test is a check of the trial mode.
