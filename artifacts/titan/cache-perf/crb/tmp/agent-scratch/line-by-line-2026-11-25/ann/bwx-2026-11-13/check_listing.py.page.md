## Short version: purpose

`check_listing.py` is the acceptance test of a build of the first runner `bwx`: it reads the machine code of every kernel of the four binaries (`listing.txt`) and compares it with saved listings of the two older benchmark binaries `bw_new` and `bw_old` (`probe.txt`). It accepts a build only when every kernel has the expected loop body, the planned loop offsets modulo 64 hold, every A/A copy is a function of its own, and the code outside the loops passes three more checks. The script of the next runner version, `check_listing8.py`, is of another kind: it compares the whole function text of each kernel with the accepted build of `bwx`.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **The 21 kernels of `bwx`**: `read`, `write`, `copy` (the new C kernels of `bw_new`), `asmread`, `asmwrite`, `asmcopy` (the assembly kernels of `bw_new`), `oldread`, `oldwrite`, `oldcopy` (the kernels of `bw_old`), four A/A copies, three variants of the copy loop (`asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`), four `read_nop` kernels and `read_sparse` [Ref5].
- **A/A copy**: the same source under a second name: `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`.
- **Four binaries, B3 binaries**: `build.sh` builds `bwx` and the three binaries `bwx_o0`, `bwx_o36` and `bwx_o52` of step B3 of the test plan. In a B3 binary the loops of `copy`, `asmcopy` and `asmcopy2` are planned at 0, 36 or 52 modulo 64.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`objdump`**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **`listing.txt`**: the `objdump` text of every kernel function of the four binaries, written by the build script `build.sh`. The block of one kernel starts with a line `=== <binary> <kernel> ===`. The function of a kernel has the name `k_` plus the kernel name.
- **`probe.txt`**: a result file of the test of the kernels of 2026-11-13. It holds the `objdump` text of the kernel functions of `bw_new` and `bw_old`, in blocks that start with a line such as `=== bw_new k_read ===` [Ref1].
- **Reference**: the loop or the whole function in `probe.txt` with which a kernel is compared.
- **`handoff.md`, B.7**: `handoff.md` is the note that specifies the runner `bwx`. Its section B.7 "Loop addresses" requires this acceptance test [Ref5].
- **Build records, CRB build 1, CRB build 2**: the folders `bwx-crb-build-1` and `bwx-crb-build-2` of the test data hold the files of two runs of `build.sh` on 2026-11-13. This page calls the runs CRB build 1 and CRB build 2.
- **Development machine**: the machine on which this script runs, by its documentation text. It is not CRB.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start, loop body**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range. The loop body is the list of the instructions of the range.
- **Loop offset modulo 64 (`loop_mod64`)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **q, v and d registers**: three names for the 32 vector registers of AArch64, the 64-bit Arm instruction set. `qN` is the full 16-byte register N. `dN` is its low 8 bytes. `vN` is the same register seen as a vector of elements.
- **`ldp`, `stp`, `add`, `cmp`, `nop`**: `ldp` loads a pair of registers from memory. `stp` stores a pair. `add` adds. `cmp` compares two values for the branch after it. `nop` does nothing.
- **`bl`, `adrp`**: `bl` calls a function. `adrp` puts the address of a 4096-byte page into a register.
- **Stub**: a short piece of code in the binary through which a call of a library function goes.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. When Python loads the file, it builds the tables `KERNELS`, `AA` and `SAME` ({L52-62}) and the tables of check 5 ({L138-142}).
2. `main` reads the option `--binaries` and the two file arguments ({L181-190}).
3. It reads `probe.txt` and the listing with the helper `sections`. A file that cannot be read ends the script with exit status 2 ({L191-195}).
4. It takes the loop and the whole text of the nine reference functions from `probe.txt`, with the helpers `loop_of` and `whole`. Exit status 2 when one of them has no loop ({L196-203}).
5. Exit status 2 when the listing has no block. An expected binary that the listing lacks gets a failure row ({L204-215}).
6. For each binary and each of the 21 kernels it makes the checks 1 to 5 and prints one row. When a text differs, it prints both texts side by side ({L216-268}).
7. Kernels of a binary that the script does not know count as one failure ({L269-272}).
8. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed ({L273-278}).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its table to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used, `--binaries` has no value, a reference function has no loop, or the listing has no block.
- The script reads `listing.txt` and `probe.txt`. It does not read `offsets.tsv`, the second table that `build.sh` writes. It computes every loop start from the listing.
- The default path of `probe.txt` fits the project folder of the script and not the code repo ({L50}). From the repo the file must be given as the second argument. The repo keeps it in the test folder of 2026-11-13 [Ref1].
- Saved outputs of this script for the two CRB builds lie in the project folder, not in the repo. Both show 83 rows with `ok` and one row with `FAIL`, and both end with `failed_rows=1` [Ref2]. So the script ended with exit status 1 for both builds. A note of the project says the same for the second build [Ref3].
- CRB build 1 fails at `copy` of `bwx_o52`: the loop offset is 0 and not the planned 52. CRB build 2 was built with one more compiler option for `bwx_o52`. It fails at `oldwrite` of `bwx_o52`: the loop body is the same, and the code outside the loop differs from `k_write` of `bw_old` [Ref2]. By the note of the project the first build was not used, and no sequence of step B3 uses `oldwrite` [Ref3].
- What the script proves for one of the 13 kernels of `WHOLE` with `ok`: the whole function, with every operand, equals the function of `bw_new` or `bw_old` in `probe.txt`, apart from addresses. A target outside the function is not compared at all ({L132}).
- What it proves for one of the other eight kernels with `ok`: the loop body equals a list that the script builds from two reference loops ({L158-177}), the function has exactly one backward branch, and d8 to d15 are stored and loaded where the kernel is in `SAVE_D8_D15`. The rest of the code outside the loop of these kernels is not checked ({L37-38}).
- In check 2 only the target of the loop branch is made independent of the address ({L107}). The documentation text describes a distance from the loop start ({L40-41}).
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: the reference file, 439 lines. The 22 rows of text before its first block and the 3 rows after its last block are not listing text. 10 of them start with `##`: 7 before the first block and 3 after the last block. It holds 17 blocks, among them `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` and of `bw_old`. Checked in this task with a script that follows the rule of {L94-109}: each of the nine reference functions has one backward branch, no reference loop holds a branch before its loop branch, the loop of `bw_new k_copy` has 20 instructions, and the loop of `bw_new k_asmread` has 11. In `bw_new k_copy` the first `stp` is `stp q31, q30, [x0]` and the seven others have the offsets -224 to -32. A `cmp` in this task found the file equal to `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`, the file that the default path of {L50} names from the project folder. From the folder `code/bwx-2026-11-13` of the repo the default path leads into a folder `results` beside the folder `arm-crb`. No such folder exists.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/recount/check_listing-crb-build-2.txt` and the file `check_listing-crb-build-1.txt` beside it: saved outputs of this script, in the project folder. The file of build 2 has 99 lines: the header line, 84 kernel rows (83 end with `ok`), 13 lines of a side-by-side block (9 with `!=`) and the summary line `# binaries=4 (expected: bwx,bwx_o0,bwx_o36,bwx_o52) kernels_per_binary=21 failed_rows=1`. Its failed row is `bwx_o52 oldwrite`, with `same` in the column `loop_body` and the result `FAIL: code outside the loop differs from bw_old k_write of probe.txt`. The file of build 1 has 111 lines, 83 rows with `ok` and the same summary line. Its failed row is `bwx_o52 copy`, with `loop_mod64` 0, `planned` 52 and a result that starts with `FAIL: loop offset is not the planned 52`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: a note of the project. Its section "Changes of the lead" says in item 1 that `bwx_o52` is built with `-falign-loops=1`, that the first build failed the acceptance test and was not used, that with the second build `check_listing.py` reports 83 of 84 rows ok and ends with status 1, that the failed row is `oldwrite` of `bwx_o52`, and that no B3 sequence uses it. Item 2 says that `check_listing.py` no longer compares addresses outside a function (`adrp`, `bl`).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: a note of the project. Its part "Smaller points of `build.sh` and `check_listing.py`" says that the script requires the four binaries, that it also checks code outside the loop, and that this is stricter than specification v1.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the note with "specification v1" of `bwx`. Section B.1 lists the kernels and says that `asmcopy_c` is an asm kernel whose loop is the machine code of the C copy loop. The text before B.1 says that without `-fno-ipa-icf` gcc may merge two functions with equal bodies, and that an A/A copy would then not exist. Section B.7 "Loop addresses" holds the item "Acceptance test, required".
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/listing.txt`: the listing of CRB build 2, with 84 blocks. The first block has the title line `=== bwx read ===` and the label line `0000000000003a20 <k_read>:`. `k_read` holds `b.hi 3a24 <k_read+0x4>`.
