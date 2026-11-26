## Short version: purpose

`build8.sh` builds the runner `bwx8` on CRB, runs its self-test, and writes the machine code of every kernel to `listing.txt`. It records the build in `build.txt`: host, load, compiler, flags, self-test result, branch targets of the timed function of the trial mode, and sha256 values. The build script of the next runner version, `build10.sh`, is this script with three additions: its branch-target check also covers a second timed function, it saves the machine code of both timed functions, and it records where five functions start modulo 64.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx8.c`. This script compiles it.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Self-test file**: the C file `bwx8_selftest.c`. The runner source includes it, and the option `--selftest` of the runner runs it.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Development machine**: the machine on which the check scripts run. It is not CRB. The header comment of the script uses this name.
- **Build record, CRB build**: the build record is the folder `bwx8-crb-build-1` of the test data. It holds the files that one run of this script wrote on 2026-11-15, and its printed output [Ref1] [Ref5]. This page calls that run the CRB build. A note of the project names this build as the build that was accepted on CRB [Ref10].
- **Accepted build**: the build of a runner version that serves as the reference for the next version.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of the runner source times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file, and the function `timed_sequence` runs the timed windows of a trial.
- **Branch target**: the address that a branch or call instruction goes to.
- **Loop start**: the address of the first instruction of the loop of a kernel. This script takes the target of the first backward branch of the function.
- **`objdump`, `taskset`**: two Linux tools. `objdump` prints the machine code of a binary as text. `taskset` starts a program that may run on a given list of CPUs only.
- **`PLACE`, pad**: `PLACE` is a macro of the runner source. It puts padding bytes (a pad) directly before a function. Then the function starts at a planned address modulo 64.
- **Page**: the unit in which Linux gives memory to a process. Its size is 4096 B in the self-test output of the CRB build [Ref4].
- **`tackle-8mb.md`, Stage 1**: `tackle-8mb.md` is the design note of the test of 2026-11-15 on the buffer size of 8 MiB. Stage 1 is the part of the note with the title "establish that the runner can measure the effect".

## Main flow

1. Stop when the marker file exists. Then start the script again under `taskset`, limited to the CPUs 0 to 119 ({L18-22}).
2. Set the folder of the script, the compiler, the ten compiler flags and the name of the binary ({L23-26}).
3. Write the first lines of `build.txt` and compile `bwx8.c`. Exit status 5 when the compiler fails ({L27-36}).
4. Check the marker file again and run `bwx8 --selftest`. Exit status 4 when the self-test fails ({L38-43}).
5. For each kernel name that `bwx8 --list` prints: append the machine code of the kernel function to `listing.txt`, and append one row with the function start and the loop start to `offsets.tsv` ({L47-63}).
6. Read the machine code of `timed_sequence` and write its branch targets to `build.txt`. Exit status 6 when a target is not allowed, or when the clock read or the kernel call is missing ({L70-79}).
7. Append the sha256 values, the load and the end time to `build.txt`. Print `build.txt` and `offsets.tsv` ({L81-88}).

## Behavior a reader must know

- The script times nothing and computes no rate. It reads the load averages at the start and at the end only for the record ({L29}, {L84}).
- Four checks stop the script, each with its own exit status: the marker file (status 3, checked at {L21}, {L38} and {L49}), the compiler (status 5), the self-test (status 4) and the branch targets of `timed_sequence` (status 6). With the rule `-e` of {L18} another failed command also ends the script. The row of {L18} names the exceptions.
- The script does not compare `listing.txt` with an accepted listing. The script `check_listing8.py` does that later, on the development machine ({L14}).
- A run that reaches its end replaces the binary, `build.txt`, `selftest-bwx8.txt`, `listing.txt` and `offsets.tsv` in the folder of the script. A run that stops earlier replaces only the files that it wrote before the stop. Files of an older run can then stay in the folder beside the new ones. Example: after a stop at the marker check of {L38} the folder holds the new `build.txt` and the new binary, beside the self-test output and the listing of an older run.
- The CPU limit of {L22} holds for every program that the script starts. The script pins no program to one CPU. Two environment variables change the limit. A `BWX_CPUS` that is set and not empty replaces the list `0-119`. A `_PINNED` that is already set and not empty at the start makes the script set no limit at all.
- The branch-target check has a limit. It skips a conditional branch whose `objdump` line ends with a comment ({L73}). The script saves no machine code of `timed_sequence`, so the build record cannot show which branches the check skipped.
- The loop start in `offsets.tsv` is the target of the first backward branch. In the CRB build each kernel function holds exactly one backward branch [Ref3].
- The header comment says that the accepted build of `bwx` used no extra compiler flag ({L6-7}). The record of that build shows no extra flag for the binary `bwx` and one extra flag, `-falign-loops=1`, for its binary `bwx_o52` [Ref9].
- Results of the CRB build: gcc 14.2.0, no compiler message, self-test with exit status 0 and `# failures=0`, and the four allowed branch targets of `timed_sequence` [Ref1]. `offsets.tsv` has 21 kernel rows, and no row holds `NA` [Ref2].
- No compiled `bwx8` is in a local folder. `build.txt` of the CRB build gives the sha256 of the binary. It begins with `f84be912` [Ref1].

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/build.txt`: the record that this script wrote in the CRB build, 15 lines. It holds the host `ubuntu`, the start time `2026-11-15T00:28:35Z`, the load averages `0.00 0.00 0.00`, `logins=0`, gcc 14.2.0, the ten flags, the two `compiler messages` lines with nothing between them, `## selftest bwx8 exit=0 # failures=0`, the line `## timed_sequence branch targets: (indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2`, six sha256 values, and the last line `## load_after=0.08 0.02 0.01 utc=2026-11-15T00:28:36Z`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/offsets.tsv`: the table of the CRB build: 1 header line and 21 kernel rows. The rows of `read`, `asmread` and `oldread` hold the values that the row of {L62} gives. No row holds `NA`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/listing.txt`: the machine code of the 21 kernels of the CRB build, 641 lines. The loop of `k_oldread` holds 4 `ldp` loads and 8 vector adds. The function `k_read` holds the branch target `4024 <k_read+0x4>`. The functions `k_oldwrite` and `k_oldcopy` each hold one loop with the instructions `whilelo` and `st1d`, and `k_oldwrite` holds the line `b.ne 3f40 <k_oldwrite+0x20>  // b.any`. Checked in this task with a script that applies the rule of {L55-61}: each of the 21 functions holds exactly one backward branch to an address inside the function. The only call instructions of the file are two calls of `__stack_chk_fail`, in `k_oldread` and `k_oldread2`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/selftest-bwx8.txt`: the self-test output of the CRB build, 319 lines. The first line holds `page_bytes=4096 kernels=21 (aarch64)`. The 319 lines are: 2 comment lines, 136 lines that begin with `call,`, and 181 rows that end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/build.out`: the saved standard output of the CRB build, 41 lines. Checked in this task with `cmp`: the first 15 lines equal `build.txt`, the next line is `## offsets.tsv:`, and the next 22 lines equal `offsets.tsv`. The last three lines are `build8 status 0`, a line that starts with `## pmu:` and a line that starts with `## paranoid=`. The script holds no command that prints these three lines.
- [Ref6] Help text of gcc 11.4.0 (x86-64) on the machine on which this page was written, read in this task (`gcc --help=optimizers`, `gcc --help=warnings`, `gcc --help=c`, `gcc -Q --help=optimizers -O3`). At `-O3` it lists `-finline-functions` and `-ftree-loop-vectorize` as enabled. It says "Enable most warning messages." for `-Wall`, "Print extra (possibly unwanted) warnings." for `-Wextra`, and "Conform to the ISO 2011 C standard with GNU extensions." for `-std=gnu11`. The help text of the compiler of the CRB build (gcc 14.2.0) was not read.
- [Ref7] external source: the gcc 14.2.0 manual on gcc.gnu.org, chapters "AArch64 Options", "Optimize Options" and "Link Options", read in this task through a web tool. By the entry `-march=name`, the value `native` makes the compiler pick the architecture of the host system, gcc uses the name to decide what kind of instructions it can emit, and without `-mtune` or `-mcpu` the code is tuned to perform well across a range of target processors of that architecture. By the entry `-ftree-loop-distribute-patterns`, gcc distributes loop patterns that can be generated as calls of a library, and the example is a loop that sets an array to zero and becomes a call of `memset`. By the entry `-fipa-icf`, gcc folds functions and read-only variables with identical code. By the entry `-fno-toplevel-reorder`, gcc does not reorder top-level functions, variables and `asm` statements and writes them in the order of the input file. By the entry `-falign-functions=n`, gcc aligns the start of functions to the next power of two that is at least n. By the entry `-pthread`, gcc links with the POSIX threads library.
- [Ref8] Computed in this task with `sha256sum` on the files `bwx8.c`, `bwx8_selftest.c` and `build8.sh` of the code folder, and on `listing.txt` and `offsets.tsv` of the build record. All five values equal the values in `build.txt` of the build record.
- [Ref9] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/build.txt`: the record of the second CRB build of `bwx`, of 2026-11-13. It holds the lines `## EXTRA=` and `## EXTRA_bwx=` with no value, and the line `## EXTRA_bwx_o52=-falign-loops=1`. Checked in this task with `cmp`: the file equals `build.txt` in the folder `crb-build-2` of the project folder `crb/tmp/agent-scratch/bwx-2026-11-13`.
- [Ref10] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "CRB acceptance, 2026-11-15" names the build `crb-build-1` with gcc 14.2.0 and a sha256 of `bwx8` that begins with `f84be912`, as in `build.txt`. It says that the self-test ends with `failures=0`.
