## Short version: purpose

This file is the self-test of the runner `bwx8`: it checks what each of the 21 kernels does to memory, and the records and output rows of the trial mode. It runs only when `bwx8` is started with `--selftest`, which the build script `build8.sh` does once after the build. The self-test of the next runner version, `bwx10_selftest.c`, is this file plus two checks of the option `--hot-copy`, which `bwx8` does not have.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx8.c`. It includes this file with `#include`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Kind**: the type of a kernel in the table `kernels[]` of the runner source: `T_READ` (a read kernel that returns nothing), `T_OLDREAD` (a read kernel that returns a sum), `T_WRITE` or `T_COPY`.
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Objdump listing**: the name that the comments of this file use for the machine-code listing.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of the runner source times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file.
- **Plan**: the list of trials that the trial mode reads from a file. One line of the plan is one `struct trial`. The tests of this file write such a structure directly, without a file.
- **Worker record**: the `struct tw` of the runner source. It holds the state of the thread that runs the trials: the buffer, the counter group and the trace. In the self-test the main thread runs the trials.
- **Trial, window, target window**: a trial is a list of timed windows that run one directly after the other: 1 window of previous activity, 4 prefix windows, 1 predecessor window, then the target windows. One window runs one kernel on one range for a requested time.
- **Window record**: the `struct win` of one window. Its plan fields (kernel, range size, passes between two clock reads, duration, bin storage) are set before the trial. Its result fields (bytes, start time, end time, number of bins) are written by the timed sequence.
- **Bin**: a record inside a target window: one clock read and the bytes counted from the start of the window to that clock read. The requested width of a bin is 10 ms.
- **`timed_sequence`**: the function of the runner source that runs the windows of a trial.
- **Sink, sink check**: the sink is the variable that receives the sum that an old read kernel returns. After a trial, the sink check compares it with the expected sum: 1 = equal, 0 = not equal, -1 = the trial ran no old read.
- **Trace**: a list of the events of a trial that the trial mode can keep (option `--trace`).
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter group, multiplexed**: the counter group holds the counters that the runner opens for a thread. Linux reports how long the group was enabled and how long it ran. "Multiplexed" means here: in a target window the running time is below the enabled time.
- **Counter state**: what a trial does with the counter group. The plan sets it in the field `count`, and the last field of the E row prints it. `closed`: no counter group is open. `open`: the group is open, and the timed sequence does not read it. `read`: the timed sequence reads the group at the borders of the target windows. `fail`: the plan asked for `open` or `read`, and an event did not open.
- **Rows of the trial mode**: `emit_trial` of the runner source prints them. The first field is the kind of the row. P is a page snapshot before (`pre`) or after (`post`) the trial. W is one window. B is one bin. C holds the counter differences of one target window. E holds the totals of the trial. X is a defect that the runner found.
- **Page snapshot**: the page state of the buffer that the trial mode reads before and after a trial: the size in kB and the kB in huge pages from `/proc/self/smaps`, and four counters from `/proc/vmstat`. A value that is not available is -1 and is printed as `NA`.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Word**: 8 bytes, one `uint64_t`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Page, `page_bytes`**: the unit of memory protection. `page_bytes` holds its size in bytes. It was 4096 B in the self-test of the CRB build [Ref1].
- **`PROT_NONE` page**: a page that the process may neither read nor write. A load from it or a store to it is a fault.
- **Fault, `SIGSEGV`**: a fault is a forbidden memory access. Linux answers it with the signal `SIGSEGV`. Without a handler the signal ends the process.
- **Guarded buffer, guard page**: a guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. These two pages are the guard pages.
- **Stand-in kernels**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. The header line of the self-test output says which build ran.
- **Nop, vector add**: a nop is an instruction that does nothing. A vector add adds two vector registers. Neither of the two changes memory.
- **d8 to d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged.
- **Build record, CRB build**: the build record is the folder `bwx8-crb-build-1` of the test data. It holds the files that one run of the build script `build8.sh` wrote [Ref2]. This page calls that run the CRB build. A note of the project names this build as the build that was accepted on CRB [Ref4].
- **`build8.sh`**: the build script of `bwx8`. It compiles `bwx8.c`, runs `bwx8 --selftest`, and writes the machine-code listing.
- **Rate**: bytes divided by time, in GB/s.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `bwx8.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs ({L380}).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B ({L382-388}).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) ({L389-392}).
4. For each of the 21 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` ({L393-400}).
5. Two checks of the trial mode follow: `test_trial` and `test_emit` ({L401-402}).
6. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status ({L403-404}).
7. `build8.sh` stores the output in the file `selftest-bwx8.txt`. It stops the build with exit status 4 when the exit status of the self-test is not 0.

## Behavior a reader must know

- The self-test runs only with `bwx8 --selftest`. `build8.sh` starts it once after the build. A timed run starts the runner with `--seq` or `--trial`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate. Only the checks of the trial mode read the clock.
- Result of the CRB build: the self-test output has 319 lines, 181 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. Its header line says `page_bytes=4096 kernels=21 (aarch64)` [Ref1]. `build.txt` of the same build holds the line `## selftest bwx8 exit=0 # failures=0`, and its sha256 value of `bwx8_selftest.c` is the value of the file explained here [Ref2].
- What the kernel checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the kernel checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the bytes that a read kernel loads ({L22-26}).
- By the file comment, the kernel checks are the text of `bwx_selftest.c`, the self-test of the first runner version, and `test_trial` is new ({L5-6}). A `diff` of this task shows four blocks that `bwx_selftest.c` does not have in this form: the first lines of the file comment ({L2-6}), its two paragraphs on the trial mode ({L27-41}), the six functions from `trial_check` to `test_emit` ({L207-378}), and the two calls of {L401-402}. All other lines are equal in both files [Ref3].
- No check runs the interval mode. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size` and `test_block` no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread and starts no other thread. It pins no thread to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/selftest-bwx8.txt`: the self-test output of the CRB build, 319 lines. The first line is `# selftest: page_bytes=4096 kernels=21 (aarch64); columns: kernel,check,bytes,result`. 136 lines begin with `call,`. 181 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/build.txt`: the record of the CRB build. It holds the line `## selftest bwx8 exit=0 # failures=0`. Its sha256 value of `bwx8_selftest.c` begins with `a94d917e`. Computed in this task with `sha256sum`: the file `bwx8_selftest.c` of the code folder has the same value.
- [Ref3] A `diff` in this task of `bwx8_selftest.c` against `bwx_selftest.c`, both of the code repo. It prints four blocks: {L2-6} are changed, and {L27-41}, {L207-378} with the blank line after them, and {L401-402} stand in `bwx8_selftest.c` only.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "CRB acceptance, 2026-11-15" names the build `crb-build-1` with a sha256 of `bwx8` that begins with `f84be912`, and says that the self-test ends with `failures=0`. `build.txt` of the build record holds the same sha256 of `bwx8`.
