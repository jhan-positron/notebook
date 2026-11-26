## Short version: purpose

This file is the self-test of the first runner `bwx`: it checks what each of the 21 kernels does to memory. It runs only when a binary of `bwx` is started with `--selftest`, which the build script `build.sh` does once for each of its four binaries. The self-test of the next runner version, `bwx8_selftest.c`, keeps these kernel checks unchanged and adds checks of the trial mode, which `bwx` does not have.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx.c`. It includes this file with `#include`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Kind**: the type of a kernel in the table `kernels[]` of the runner source: `T_READ` (a read kernel that returns nothing), `T_OLDREAD` (a read kernel that returns a sum), `T_WRITE` or `T_COPY`.
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Objdump listing**: the name that the comments of this file use for the machine-code listing.
- **Word**: 8 bytes, one `uint64_t`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Page, `page_bytes`**: the unit of memory protection. `page_bytes` holds its size in bytes. It was 4096 B in the self-tests of CRB build 1 [Ref1].
- **`PROT_NONE` page**: a page that the process may neither read nor write. A load from it or a store to it is a fault.
- **Fault, `SIGSEGV`**: a fault is a forbidden memory access. Linux answers it with the signal `SIGSEGV`. Without a handler the signal ends the process.
- **Guarded buffer, guard page**: a guarded buffer is a test buffer with one `PROT_NONE` page directly before it and one directly after it. These two pages are the guard pages.
- **Stand-in kernels**: on a machine that is not AArch64 (the 64-bit Arm instruction set), plain C loops take the place of the NEON and asm kernels. The header line of the self-test output says which build ran.
- **Nop, vector add**: a nop is an instruction that does nothing. A vector add adds two vector registers. Neither of the two changes memory.
- **d8 to d15**: the low halves of the Arm vector registers v8 to v15. The Arm calling convention requires that a function gives them back unchanged.
- **Build records, CRB build 1, CRB build 2**: the build records are the folders `bwx-crb-build-1` and `bwx-crb-build-2` of the test data. Each holds files that one run of the build script `build.sh` wrote on 2026-11-13 [Ref2]. This page calls the two runs CRB build 1 and CRB build 2. Only the record of CRB build 1 holds self-test outputs.
- **`build.sh`**: the build script of `bwx`. It compiles `bwx.c` into the four binaries `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`, runs each with `--selftest`, and writes the machine-code listing.
- **Rate**: bytes divided by time, in GB/s.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `bwx.c` includes this file directly before its `main`. `main` reads the page size into `page_bytes`, removes the CPUs above 119 from the allowed set of the process, and calls `selftest` when an argument is `--selftest`. In every other case no function of this file runs ({L191}).
2. `selftest` makes the output line-buffered, prints the header line, and stops with the value 2 if the page size is not a multiple of 256 B ({L193-199}).
3. It sets the three buffer sizes (1 page, 3 pages, 1 MiB) and the two block offsets (first and last 256 B of a page) ({L200-203}).
4. For each of the 21 kernels: `test_size` on the three sizes, `test_block` at the two offsets, and for a read kernel `test_touch` ({L204-211}).
5. `selftest` prints `# failures=N` and returns 1 if a check failed, else 0. `main` returns this value as the exit status ({L212-213}).
6. `build.sh` stores the output of each binary in a file `selftest-<binary>.txt`. It stops the build with exit status 4 when the exit status of a self-test is not 0.

## Behavior a reader must know

- The self-test runs only with the option `--selftest`. `build.sh` starts it once per binary after the build. A timed run starts the runner with `--seq`. So no function of this file runs between two clock reads of a timed run.
- The self-test computes no rate, and no function of this file reads the clock.
- Result of CRB build 1: each of the four self-test outputs has 299 lines, 162 rows that end with `pass`, no `FAIL` line, and the last line `# failures=0`. The header line says `page_bytes=4096 kernels=21 (aarch64)` [Ref1]. `build.txt` of both CRB builds holds four lines with `exit=0 # failures=0`, and its sha256 value of `bwx_selftest.c` is the value of the file explained here [Ref2].
- What the checks prove for a read kernel: the buffer is unchanged, no byte within one page outside the test buffer is loaded or stored, and at least one byte of each page of a range of 3 pages is accessed. For `oldread` and `oldread2` in addition: the returned sum equals the sum of all words.
- What the checks cannot prove. They see three things only: the content of memory after the call, a fault, and the sum that an old read kernel returns. They cannot see which bytes inside a page a read kernel without return value loads, a nop, the order of loads and stores, the speed, or the saving of the registers d8 to d15. By the file comment the objdump listing is the evidence for the bytes that a read kernel loads ({L21-25}).
- By a note of the project, two checks go beyond the model `selftest.c`: the fault check of `test_touch` for every read kernel, and the sum check for `oldread` and `oldread2` [Ref3].
- No check runs the timing code of the runner. The byte count, the clock reads and the stop rule of the function `worker` of the runner source are not tested by this file.
- In `test_size` and `test_block` no `SIGSEGV` handler is installed. A kernel that loads from or stores to a `PROT_NONE` page there ends the process. No result line follows, and the last `call` line of the output names the kernel.
- A failed check does not stop the self-test. It adds 1 to `failures`, and the exit status becomes 1.
- The self-test runs in the main thread and starts no other thread. It pins no thread to one CPU. The test buffers come from `guarded`: plain `mmap` memory, with no request for huge pages.
- On a machine that is not AArch64 the self-test checks the stand-in kernels, not the real ones. The header line of the output says which kernels ran.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/selftest-bwx.txt` and the three files `selftest-bwx_o0.txt`, `selftest-bwx_o36.txt` and `selftest-bwx_o52.txt` beside it: the self-test outputs of CRB build 1. The four files are equal (checked with `cmp`). Each has 299 lines. The first line is `# selftest: page_bytes=4096 kernels=21 (aarch64); columns: kernel,check,bytes,result`. 135 lines begin with `call,`. 162 rows end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-1/build.txt` and the file `build.txt` of the folder `bwx-crb-build-2`: the records of the two CRB builds. Each holds four lines of the form `## selftest <binary> exit=0 # failures=0`, for `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`. In both, the sha256 value of `bwx_selftest.c` begins with `1c25fc53`. Computed in this task with `sha256sum`: the file `bwx_selftest.c` of the code folder has the same value. The folder `bwx-crb-build-2` holds no self-test output file.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: a note of the project. Its item 20 says that the self-test is a mode of `bwx`, and it names two checks beyond `selftest.c`: each read kernel must fault when one page of a 3-page range is made `PROT_NONE`, and `oldread` and `oldread2` must return the sum of all words.
