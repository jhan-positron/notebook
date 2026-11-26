## Short version: purpose

`build10.sh` builds the runner `bwx10` on CRB, runs its self-test, and writes the machine code of every kernel to `listing.txt`. It records the build in `build.txt`: host, load, compiler, flags, self-test result, branch targets of the two timed functions of the trial mode, placement of five functions, and sha256 values. The build script of the next runner version, `build11.sh`, is this script with the names changed and one block added: it also compares the placement with the accepted `bwx10` binary.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx10.c`. This script compiles it.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Self-test file**: the C file `bwx10_selftest.c`. The runner source includes it, and the option `--selftest` of the runner runs it.
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
- **Build record, CRB build**: the build record is the folder `bwx10-crb-build-1` of the test data. It holds five files that one run of this script wrote on 2026-11-15 [Ref1]. This page calls that run the CRB build. A note of the project says that this build ran on CRB [Ref10].
- **Accepted binary**: the binary of an older runner version that serves as the reference for a new build. By default this script looks for it in the output folder of the build script of that version.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of the runner source times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file, and the functions `timed_sequence` and `timed_sequence_hot` run the timed windows of a trial.
- **Placement**: the start address modulo 64 of five functions of the binary: `call`, `read_smaps`, `tcount`, `timed_sequence` and `timed_sequence_hot`. The value is the offset of the function start inside a 64-byte block of code. The script calls this the placement of the timed path.
- **Branch target**: the address that a branch or call instruction goes to.
- **Loop start**: the address of the first instruction of the loop of a kernel. This script takes the target of the first backward branch of the function.
- **Symbol**: a name with an address in a binary, for example the name of a function.
- **`objdump`, `nm`, `taskset`**: three Linux tools. `objdump` prints the machine code of a binary as text. `nm` lists the symbols of a binary with their addresses. `taskset` starts a program that may run on a given list of CPUs only.
- **`PLACE`, pad**: `PLACE` is a macro of the runner source. It puts padding bytes (a pad) directly before a function. Then the function starts at a planned address modulo 64.
- **Page**: the unit in which Linux gives memory to a process. Its size is 4096 B in the self-test output of the CRB build [Ref5].
- **`tackle-8mb.md`, Stage 1**: `tackle-8mb.md` is the design note of the test of 2026-11-15 on the buffer size of 8 MiB. Stage 1 is the part of the note with the title "establish that the runner can measure the effect".

## Main flow

1. Stop when the marker file exists. Then start the script again under `taskset`, limited to the CPUs 0 to 119 ({L24-28}).
2. Set the folder of the script, the compiler, the ten compiler flags and the name of the binary ({L29-32}).
3. Write the first lines of `build.txt` and compile `bwx10.c`. Exit status 5 when the compiler fails ({L33-42}).
4. Check the marker file again and run `bwx10 --selftest`. Exit status 4 when the self-test fails ({L44-49}).
5. For each kernel name that `bwx10 --list` prints: append the machine code of the kernel function to `listing.txt`, and append one row with the function start and the loop start to `offsets.tsv` ({L53-69}).
6. For `timed_sequence` and `timed_sequence_hot`: save the machine code in `seq-listing.txt` and write the branch targets to `build.txt`. Exit status 6 when a target is not allowed, or when the clock read or the kernel call is missing ({L77-93}).
7. Write the placement of the new binary to `build.txt`. Compare it with the placement of the accepted binary of bwx8, and write one line with `same` or `DIFFERS`. The helper `placement` reads the five start addresses with `nm` ({L101-121}).
8. Append the sha256 values, the load and the end time to `build.txt`. Print `build.txt` and `offsets.tsv` ({L123-130}).

## Behavior a reader must know

- The script times nothing and computes no rate. It reads the load averages at the start and at the end only for the record ({L35}, {L126}).
- Four checks stop the script, each with its own exit status: the marker file (status 3, checked at {L27}, {L44} and {L55}), the compiler (status 5), the self-test (status 4) and the branch targets of the two timed functions (status 6). With the rule `-e` of {L24} another failed command also ends the script. The row of {L24} names the exceptions.
- The placement comparison never stops the script. A difference only gives a line with `DIFFERS` in `build.txt`.
- The script does not compare `listing.txt` with an accepted listing. The script `check_listing10.py` does that later, on the development machine ({L18}).
- A run that reaches its end replaces the binary, `build.txt`, `selftest-bwx10.txt`, `listing.txt`, `offsets.tsv` and `seq-listing.txt` in the folder of the script. A run that stops earlier replaces only the files that it wrote before the stop. Files of an older run can then stay in the folder beside the new ones. Example: after a stop at the marker check of {L44} the folder holds the new `build.txt` and the new binary, beside the self-test output and the listing of an older run.
- The CPU limit of {L28} holds for every program that the script starts. The script pins no program to one CPU. Two environment variables change the limit. A `BWX_CPUS` that is set and not empty replaces the list `0-119`. A `_PINNED` that is already set and not empty at the start makes the script set no limit at all.
- The branch-target check has a limit. It skips a conditional branch whose `objdump` line ends with a comment ({L85}). In the CRB build each of these branches stays inside its own function [Ref4].
- The loop start in `offsets.tsv` is the target of the first backward branch. In the CRB build each kernel function holds exactly one backward branch [Ref3].
- The header comment says that no script uses `seq-listing.txt` ({L17}). The test script `test_runner10.py` reads the `seq-listing.txt` of its own test build.
- By the header comment, this script is `build8.sh` with three additions ({L5-8}): the branch-target check also covers `timed_sequence_hot`, the machine code of both timed functions goes to `seq-listing.txt`, and `build.txt` holds the placement lines. One more difference is not in that list: `build8.sh` ends with exit status 6 directly after its one check, and this script first handles both functions ({L93}).
- Results of the CRB build: gcc 14.2.0, no compiler message, self-test with exit status 0 and `# failures=0`, the same four allowed branch targets in both timed functions, and the same placement as bwx8 up to `timed_sequence` [Ref1]. `offsets.tsv` has 26 kernel rows, and no row holds `NA` [Ref2].
- No compiled `bwx10` is in a local folder. `build.txt` of the CRB build gives the sha256 of the binary. It begins with `22cbb1ee` [Ref1].

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/build.txt`: the record that this script wrote in the CRB build, 20 lines. It holds the host `ubuntu`, the start time `2026-11-15T07:02:47Z`, the load averages `0.00 0.00 0.16`, `logins=0`, gcc 14.2.0, the ten flags, the two `compiler messages` lines with nothing between them, `## selftest bwx10 exit=0 # failures=0`, the branch targets of the two timed functions, the placement lines of `bwx10` and bwx8 with one line that ends with `same`, seven sha256 values, and the end time `2026-11-15T07:02:49Z`. The folder holds four more files ([Ref2] to [Ref5]) and no copy of the printed output.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/offsets.tsv`: the table of the CRB build: 1 header line and 26 kernel rows. The rows of `read`, `asmread` and `oldread` hold the values that the row of {L68} gives. No row holds `NA`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/listing.txt`: the machine code of the 26 kernels of the CRB build, 765 lines. The loop of `k_oldread` holds 4 `ldp` loads and 8 vector adds. The function `k_read` holds the branch target `41a4 <k_read+0x4>`. The functions `k_oldwrite` and `k_oldcopy` each hold one loop with the store instruction `st1d`. Checked in this task with a script that applies the rule of {L61-67}: each of the 26 functions holds exactly one backward branch to an address inside the function. The only call instructions of the file are two calls of `__stack_chk_fail`, in `k_oldread` and `k_oldread2`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/seq-listing.txt`: the machine code of `timed_sequence` and `timed_sequence_hot` of the CRB build, 753 lines. Both functions hold the SVE instruction `cntb`. The file holds the line `b.le 6bdc <timed_sequence+0x2c0>`. Checked in this task with a script: 48 branch lines have a last field that is not a name (20 in `timed_sequence`, 28 in `timed_sequence_hot`). Each of them ends with a comment of `objdump` and has a target inside its own function.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/selftest-bwx10.txt`: the self-test output of the CRB build, 413 lines. The first line holds `page_bytes=4096 kernels=26 (aarch64)`. The 413 lines are: 2 comment lines, 179 lines that begin with `call,`, and 232 rows that end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref6] Help text of gcc 11.4.0 (x86-64) on the machine on which this page was written, read in this task (`gcc --help=optimizers`, `gcc --help=warnings`, `gcc --help=c`, `gcc -Q --help=optimizers -O3`). At `-O3` it lists `-finline-functions` and `-ftree-loop-vectorize` as enabled. It says "Enable most warning messages." for `-Wall`, "Print extra (possibly unwanted) warnings." for `-Wextra`, and "Conform to the ISO 2011 C standard with GNU extensions." for `-std=gnu11`. The help text of the compiler of the CRB build (gcc 14.2.0) was not read.
- [Ref7] external source: the gcc 14.2.0 manual on gcc.gnu.org, chapters "AArch64 Options", "Optimize Options" and "Link Options", read in this task through a web tool. By the entry `-march=name`, the value `native` makes the compiler pick the architecture of the host system, gcc uses the name to decide what kind of instructions it can emit, and without `-mtune` or `-mcpu` the code is tuned to perform well across a range of target processors of that architecture. By the entry `-ftree-loop-distribute-patterns`, gcc distributes loop patterns that can be generated as calls of a library, and the example is a loop that sets an array to zero and becomes a call of `memset`. By the entry `-fipa-icf`, gcc folds functions and read-only variables with identical code. By the entry `-fno-toplevel-reorder`, gcc does not reorder top-level functions, variables and `asm` statements and writes them in the order of the input file. By the entry `-falign-functions=n`, gcc aligns the start of functions to the next power of two that is at least n. By the entry `-pthread`, gcc links with the POSIX threads library.
- [Ref8] Test in this task with gcc 11.4.0 (x86-64) on the machine on which this page was written. The C file has 16 lines. Its `static` function `call` has one call, through a `static inline` function, from a function `worker`. Built with `-O3`: `nm` shows no symbol `call`. Built with `-O3 -fno-toplevel-reorder`, and with the ten flags of {L31}: `nm` shows the symbol `call`, and the `objdump` text of the binary holds no call of it and no jump to it. The compiler of the CRB build (gcc 14.2.0, AArch64) was not tested.
- [Ref9] Computed in this task with `sha256sum` on the files `bwx10.c`, `bwx10_selftest.c` and `build10.sh` of the code folder, and on `listing.txt`, `offsets.tsv` and `seq-listing.txt` of the build record. All six values equal the values in `build.txt` of the build record.
- [Ref10] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "`bwx10` acceptance on CRB, 2026-11-15 07:03 UTC" names the build at 07:02 UTC in `~/cache-perf/bwx10-20261115/`, with gcc 14.2.0 and a sha256 of `bwx10` that begins with `22cbb1ee`, as in `build.txt`.
