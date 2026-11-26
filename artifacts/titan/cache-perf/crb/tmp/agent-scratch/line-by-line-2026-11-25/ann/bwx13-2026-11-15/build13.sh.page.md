## Short version: purpose

`build13.sh` builds the runner `bwx13` on CRB, runs its self-test, and writes the machine code of every kernel to `listing.txt`. It records the build in `build.txt`: host, load, compiler, flags, self-test result, branch targets of the two timed functions of the trial mode, placement of five functions, and sha256 values. It is `build12.sh`, the build script of the runner version before, with the names changed and one block added: the placement is also compared with the accepted `bwx12` binary.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`rand_nop0`, `rand_nop96`, `rand_nop256`**: the three kernels that `bwx13` adds to `bwx12`. By the header comment of `bwx13.c` they read the same 256 B blocks as `asmread`, in another order, with 0, 96 or 256 nop instructions after the loads of a block. A nop is an instruction that does nothing.
- **Self-test**: a program that checks what the kernels do to memory, without timing.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Development machine**: the machine on which the check scripts run. It is not CRB. The header comment of the script uses this name.
- **Build record, CRB build**: the build record is the folder `bwx13-crb-build-1` of the test data. It holds the files that one run of this script wrote on 2026-11-15, and its printed output [Ref1]. This page calls that run the CRB build. The folder name says that the run was on CRB.
- **Accepted binary**: the binary of an older runner version that serves as the reference for a new build. By default this script looks for it in the output folder of the build script of that version.
- **Interval mode, trial mode**: the two modes of the runner. In the interval mode (option `--seq`) each thread runs a sequence of kernels, and the function `worker` of `bwx13.c` times each kernel. In the trial mode (option `--trial`) one worker thread runs the trials of a plan file, and the functions `timed_sequence` and `timed_sequence_hot` run the timed windows of a trial.
- **Placement**: the start address modulo 64 of five functions of the binary: `call`, `read_smaps`, `tcount`, `timed_sequence` and `timed_sequence_hot`. The value is the offset of the function start inside a 64-byte block of code. The script calls this the placement of the timed path.
- **Branch target**: the address that a branch or call instruction goes to.
- **Loop start**: the address of the first instruction of the loop of a kernel. This script takes the target of the first backward branch of the function.
- **Symbol**: a name with an address in a binary, for example the name of a function.
- **`objdump`, `nm`, `taskset`**: three Linux tools. `objdump` prints the machine code of a binary as text. `nm` lists the symbols of a binary with their addresses. `taskset` starts a program that may run on a given list of CPUs only.
- **`PLACE`, pad**: `PLACE` is a macro of `bwx13.c`. It puts padding bytes (a pad) directly before a function. Then the function starts at a planned address modulo 64.
- **Page**: the unit in which Linux gives memory to a process. Its size is 4096 B in the self-test output of the CRB build [Ref5].
- **`tackle-8mb.md`, Stage 1**: `tackle-8mb.md` is the design note of the test of 2026-11-15 on the buffer size of 8 MiB. Stage 1 is the part of the note with the title "establish that the runner can measure the effect".

## Main flow

1. Stop when the marker file exists. Then start the script again under `taskset`, limited to the CPUs 0 to 119 ({L32-36}).
2. Set the folder of the script, the compiler, the ten compiler flags and the name of the binary ({L37-40}).
3. Write the first lines of `build.txt` and compile `bwx13.c`. Exit status 5 when the compiler fails ({L41-50}).
4. Check the marker file again and run `bwx13 --selftest`. Exit status 4 when the self-test fails ({L52-57}).
5. For each kernel name that `bwx13 --list` prints: append the machine code of the kernel function to `listing.txt`, and append one row with the function start and the loop start to `offsets.tsv` ({L61-77}).
6. For `timed_sequence` and `timed_sequence_hot`: save the machine code in `seq-listing.txt` and write the branch targets to `build.txt`. Exit status 6 when a target is not allowed, or when the clock read or the kernel call is missing ({L85-101}).
7. Write the placement of the new binary to `build.txt`. Compare it with the placement of the accepted binaries of bwx8, bwx10, bwx11 and bwx12, and write one line with `same` or `DIFFERS` per binary. A binary whose file is missing gets a line with `not compared`. The helper `placement` reads the five start addresses with `nm` ({L109-165}).
8. Append the sha256 values, the load and the end time to `build.txt`. Print `build.txt` and `offsets.tsv` ({L167-174}).

## Behavior a reader must know

- The script times nothing and computes no rate. It reads the load averages at the start and at the end only for the record ({L43}, {L170}).
- Four checks stop the script, each with its own exit status: the marker file (status 3, checked at {L35}, {L52} and {L63}), the compiler (status 5), the self-test (status 4) and the branch targets of the two timed functions (status 6). With the rule `-e` of {L32} another failed command also ends the script. The row of {L32} names the exceptions.
- The placement comparison never stops the script. A difference only gives a line with `DIFFERS` in `build.txt`.
- The script does not compare `listing.txt` with an accepted listing. The script `check_listing13.py` does that later, on the development machine ({L23}).
- A run that reaches its end replaces the binary, `build.txt`, `selftest-bwx13.txt`, `listing.txt`, `offsets.tsv` and `seq-listing.txt` in the folder of the script. A run that stops earlier replaces only the files that it wrote before the stop. Files of an older run can then stay in the folder beside the new ones. Example: after a stop at the marker check of {L52} the folder holds the new `build.txt` and the new binary, beside the self-test output and the listing of an older run.
- The CPU limit of {L36} holds for every program that the script starts. The script pins no program to one CPU. Two environment variables change the limit. A `BWX_CPUS` that is set and not empty replaces the list `0-119`. A `_PINNED` that is already set and not empty at the start makes the script set no limit at all.
- The branch-target check has a limit. It skips a conditional branch whose `objdump` line ends with a comment ({L93}). In the CRB build each of these branches stays inside its own function [Ref4].
- The loop start in `offsets.tsv` is the target of the first backward branch. In the CRB build the three `rand` kernels hold two loops each, and the table records the first one [Ref3].
- Results of the CRB build: gcc 14.2.0, no compiler message, self-test with exit status 0 and `# failures=0`, the same four allowed branch targets in both timed functions, and the same placement as bwx8, bwx10, bwx11 and bwx12 [Ref1]. `offsets.tsv` has 58 kernel rows, and no row holds `NA` [Ref2].
- No compiled `bwx13` is in a local folder. `build.txt` of the CRB build gives the sha256 of the binary. It begins with `a2858df5` [Ref1].

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/build.txt`: the record that this script wrote in the CRB build, 26 lines. It holds the host `ubuntu`, the start time `2026-11-15T20:57:30Z`, the load averages `0.00 1.34 20.62`, `logins=0`, gcc 14.2.0, the ten flags, the two `compiler messages` lines with nothing between them, `## selftest bwx13 exit=0 # failures=0`, the branch targets of the two timed functions, the placement lines of `bwx13`, bwx8, bwx10, bwx11 and bwx12 with four lines that end with `same`, seven sha256 values, and the end time `2026-11-15T20:57:33Z`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/offsets.tsv`: the table of the CRB build: 1 header line and 58 kernel rows. The rows of `read`, `asmread` and `oldread` hold the values that the row of {L76} gives. No row holds `NA`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/listing.txt`: the machine code of the 58 kernels of the CRB build, 4763 lines. The loop of `k_oldread` holds 4 `ldp` loads and 8 vector adds. The function `k_read` holds the branch target `4aa4 <k_read+0x4>`. Checked in this task with a script that applies the rule of {L69-75}: 55 functions hold exactly one backward branch to an address inside the function, and `k_rand_nop0`, `k_rand_nop96` and `k_rand_nop256` hold two. The only call instructions of the file are two calls of `__stack_chk_fail`, in `k_oldread` and `k_oldread2`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/seq-listing.txt`: the machine code of `timed_sequence` and `timed_sequence_hot` of the CRB build, 753 lines. Both functions hold the SVE instruction `cntb`. Checked in this task with a script: 48 branch lines have a last field that is not a name (20 in `timed_sequence`, 28 in `timed_sequence_hot`), and each of them has a target inside its own function.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/selftest-bwx13.txt`: the self-test output of the CRB build, 966 lines. The first line holds `page_bytes=4096 kernels=58 (aarch64)`. The 966 lines are: 2 comment lines, 444 lines that begin with `call,`, and 520 rows that end with `pass`. No line holds `FAIL`. The last line is `# failures=0`.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/build.out`: the standard output of the CRB build, 86 lines. Checked in this task with `diff`: the first 26 lines equal `build.txt`, the next line is `## offsets.tsv:`, and the last 59 lines equal `offsets.tsv`.
- [Ref7] Help text of gcc 11.4.0 on the agent server, read in this task (`gcc --help=optimizers`, `gcc --help=warnings`, `gcc --help=c`, `gcc -Q --help=optimizers -O3`). At `-O3` it lists `-finline-functions` and `-ftree-loop-vectorize` as enabled. It says "Enable most warning messages." for `-Wall`, "Print extra (possibly unwanted) warnings." for `-Wextra`, and "Conform to the ISO 2011 C standard with GNU extensions." for `-std=gnu11`. The help text of the compiler of the CRB build (gcc 14.2.0) was not read.
- [Ref8] external source: the gcc 14.2.0 manual on gcc.gnu.org, chapters "AArch64 Options" and "Optimize Options", read in this task through a web tool. By the entry `-march=name`, the value `native` makes the compiler pick the architecture of the host system, the architecture decides what kind of instructions gcc can emit, and without `-mtune` or `-mcpu` the code is tuned to perform well across a range of processors of that architecture. By the entry `-ftree-loop-distribute-patterns`, gcc turns loop patterns into calls of a library, and the example is a loop that sets an array to zero and becomes a call of `memset`. By the entry `-fipa-icf`, gcc folds functions with identical code. By the entry `-fno-toplevel-reorder`, gcc writes top-level functions, variables and `asm` statements in the order of the input file. By the entry `-falign-functions=n`, gcc aligns the start of functions to the next power of two that is at least n.
- [Ref9] Test in this task on the agent server with gcc 11.4.0 (x86-64). The C file has 16 lines. Its `static` function `call` has one call, through a `static inline` function, from a function `worker`. Built with `-O3`: `nm` shows no symbol `call`. Built with `-O3 -fno-toplevel-reorder`, and with `-O3 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`: `nm` shows the symbol `call`, and the `objdump` text of the binary holds no call of it. The compiler of the CRB build (gcc 14.2.0, AArch64) was not tested.
- [Ref10] Computed in this task with `sha256sum` on the files `bwx13.c`, `bwx13_selftest.c` and `build13.sh` of the code folder, and on `listing.txt`, `offsets.tsv` and `seq-listing.txt` of the build record. All six values equal the values in `build.txt` of the build record.
