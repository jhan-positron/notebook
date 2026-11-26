## Short version: purpose

`bandwidth_cread.c` is the benchmark program of the cread test: a copy of the old benchmark source with one more read kernel, `k_cread`. `k_cread` is written in C with NEON intrinsics, and it only loads the buffer: 256 B per loop pass, with no arithmetic. Each thread runs the selected kernels in whole passes over its own buffer for a minimum time, and `main` prints one rate in GB/s per timed interval.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB. It ran on 2026-11-13 [Ref1].
- **`k_read`, kernel `read`**: in this file the read kernel of the old benchmark source: portable C code with 16 running sums. Each load is followed by an add.
- **`k_cread`, kernel `cread`**: the read kernel that this file adds: NEON intrinsics, loads only. The new read kernel `k_read` of the later file `bandwidth.c` has the same loop text.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Asm kernels**: the three kernels `k_asmread`, `k_asmwrite` and `k_asmcopy`. Their loops are assembly text inside a C function.
- **NEON intrinsics**: C functions that map to Arm vector instructions. NEON is the set of 128-bit vector instructions of Arm.
- **`ldp q`, `stp q`**: `ldp q` is the Arm instruction that loads two 16-byte vector registers (32 B). `stp q` is the Arm instruction that stores two 16-byte vector registers (32 B).
- **64-bit Arm (AArch64)**: the instruction set of CRB.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process. The code calls it a repetition (`rep`).
- **Pass, loop pass**: a pass is one call of a kernel. It goes once over the whole buffer of a thread. A loop pass is one run of the loop body inside a kernel: 128 B in `k_read`, 256 B in `k_cread` and in the asm kernels.
- **Warm-up pass**: one pass that a thread runs before each timed interval. It is not timed.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Barrier**: an object of the POSIX thread library. A thread that calls `pthread_barrier_wait` waits until a set number of threads have called it. Then all of them continue together.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`run_cread.sh`**: the script of the cread test. It builds this file on CRB, prints the machine-code listing of `k_cread`, `k_asmread` and `k_read`, and starts the timed processes.
- **Test binary**: the binary `bandwidth_cread` that `run_cread.sh` built from this file on 2026-11-13 [Ref1].
- **Old benchmark source**: the benchmark source before the change of 2026-11-13. The code repo holds it as the file `bandwidth.orig.c` in the folder `kernels-2026-11-13`.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` sets the defaults: a buffer of 1 MiB per thread and the kernels `read`, `write` and `copy` ({L378-382}).
2. `main` reads the arguments ({L384-430}). `run_cread.sh` passes `--threads 1`, `--cpus` with CPU 0 or CPU 2, `--bytes` with `32K`, `1M`, `8M` or `1G`, `--kernel readcmp`, `--reps 3` and `--min-ms 500`.
3. `main` checks the arguments. The buffer size must be a multiple of 256 B ({L431-442}).
4. `main` creates the barrier for all worker threads plus itself and starts the worker threads ({L444-456}).
5. Each worker pins itself to its CPU, reserves its buffer and writes every element once, which is the first touch. None of this is timed ({L338-345}).
6. For each selected kernel and each repetition, each worker runs one warm-up pass and then waits at the barrier ({L347-352}). With `readcmp` the kernels run in the order `read`, `asmread`, `cread`.
7. The barrier releases all threads together. Each worker reads the clock, runs whole passes of the kernel and reads the clock again after each group of passes. It stops when the minimum time has passed ({L353-362}).
8. `main` waits until all workers have stopped. It divides the bytes of all threads by the longest thread time and prints one row with this rate ({L467-489}).
9. After the last repetition of a kernel `main` prints the `best` row ({L491-501}).
10. After the last kernel `main` waits for the end of the threads and exits ({L503-505}).

## Behavior a reader must know

- What is timed: the passes of the kernel and the clock reads between them ({L353-359}). Pinning, buffer allocation, first touch, the warm-up pass and the waits at the barrier are not timed.
- Order in a `readcmp` process: `read`, then `asmread`, then `cread`, each with its own warm-up passes and timed intervals. So `cread` is always timed after the two other kernels in the same process. The comment of {L423} names the kernels in another order.
- Stop rule: a thread tests the time only after `passes_per_check` whole passes ({L334-336}). With the sizes that `run_cread.sh` passes, these are 256 passes for `32K`, 8 passes for `1M`, and 1 pass for `8M` and for `1G`.
- Rate: `aggregate_GBps` is the bytes of all threads, divided by the longest thread time, divided by 1e9 ({L484}). With 1 thread it equals the rate of that thread.
- `k_cread` in the test binary: one loop pass is 11 instructions for 256 B: 8 `ldp q` loads, 1 `add`, 1 `cmp` and 1 branch. It holds no add of data. `k_read` in the same binary has 4 `ldp q` loads and 8 vector adds per 128 B [Ref1].
- The compiler chooses the machine code of `k_cread`. So each new build needs a check of the machine-code listing. `run_cread.sh` writes the listing into its build record.
- The usage text does not list the kernel names `cread` and `readcmp` ({L372}).
- Exit status: 0 after a normal end. 2 after a bad argument or after a failed step of the setup (`calloc`, the barrier, `pthread_create`, `mmap` or `sched_setaffinity`).
- 2 MiB pages: the program asks for them with `madvise` and never checks the result ({L133}).
- What this file adds to the old benchmark source: the include of `arm_neon.h` ({L19-21}), the seventh kernel in the kernel list ({L28-29}), `k_cread` with its comment ({L257-288}), its case in `pass` ({L318-320}), the names `cread` and `readcmp` ({L421-424}) and the test for `cread` in {L437}. Every other line equals the old benchmark source [Ref2].

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/cread-20261113T060510Z/probe.txt`: the build record that `run_cread.sh` wrote on CRB on 2026-11-13. It holds the compiler (gcc 14.2.0), the compiler flags and three sha256 values. The sha256 of `bandwidth_cread.c` in it equals the sha256 of the file that this page explains. Under the headings `=== k_cread ===`, `=== k_asmread ===` and `=== k_read ===` it holds the machine-code listing of these three functions of the test binary.
- [Ref2] Check made for this page on 2026-11-25: the command `diff` on the files `kernels-2026-11-13/bandwidth.orig.c` and `cread-2026-11-12/bandwidth_cread.c` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code`. It prints 6 places: the include of `arm_neon.h`, the two lines of the kernel list, the function `k_cread` with its comment, the case `K_CREAD` in `pass`, the names `cread` and `readcmp`, and the test for a build without the asm kernels.
