## Short version: purpose

`check_listing10.py` is the acceptance test of a build of the runner `bwx10`: it reads the machine code of every kernel (`listing.txt`) and the table of loop addresses (`offsets.tsv`) that the build script wrote. It accepts the build only when the 21 kernels of the runner version before, `bwx8`, are unchanged, and when the five new kernels `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` and `read_1pl` hold exactly the expected loop at the loop position of `asmread`. The script of the next runner version, `check_listing11.py`, is this script with another reference, other new kernels and one more rule: a fixed loop position of 20 modulo 64.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx10.c`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Round 3, `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048`, `read_1pl`**: round 3 is the set of additions that made bwx10 out of bwx8. Four of its five new kernels are the `asmread` loop with four prefetch instructions after the 8 loads. The number in the name is the distance of the first prefetch from the loaded block, in bytes. The fifth kernel, `read_1pl`, loads 16 B of every 64 B line. "Round" does not mean a repeat of a kernel sequence here.
- **`prfm pldl1keep`**: a prefetch instruction. By a comment in the runner source it asks for a line in the first-level data cache for a later load, it reads no data, and it never faults.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`objdump`**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **`listing.txt`**: the `objdump` text of every kernel function of `bwx10`, written by the build script `build10.sh`. The block of one kernel starts with a line `=== bwx10 <kernel> ===`. The function of a kernel has the name `k_` plus the kernel name.
- **`offsets.tsv`**: a table with one row per kernel, written by `build10.sh`. Its columns are `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- **Reference, accepted build**: the reference is the `listing.txt` and the `offsets.tsv` of the accepted build of `bwx8`. By the documentation text of the script they are saved in a folder `ref-bwx8` beside the script. The accepted build of a runner version is the build that serves as the reference for the next version.
- **Build record, CRB build**: the build record is the folder `bwx10-crb-build-1` of the test data. It holds the files that one run of `build10.sh` wrote on 2026-11-15. This page calls that run the CRB build. A note of the project says that this build ran on CRB [Ref1].
- **Development machine**: the machine on which this script runs, by its documentation text. It is not CRB.
- **AArch64**: the 64-bit Arm instruction set.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range.
- **Loop start modulo 64 (`loop_mod64`, loop offset)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **q, v and d registers**: three names for the 32 vector registers of AArch64. `qN` is the full 16-byte register N. `dN` is its low 8 bytes. `vN` is the same register seen as a vector of elements.
- **`ldp`, `stp`, `ldr`, `str`**: `ldp` loads a pair of registers from memory. `stp` stores a pair. `ldr` loads one register. `str` stores one.
- **`b.cc`, `b.lo`**: two names of one conditional branch. After `cmp a, b` it jumps when a is below b as unsigned numbers.
- **`bl`, `ret`**: `bl` calls a function. `ret` returns to the caller.
- **Stub**: a short piece of code in the binary through which a call of a library function goes. `objdump` names it with the ending `@plt`.
- **`adrp`**: an instruction that puts the address of a 4096-byte page into a register.
- **Table of global addresses**: a table in the binary that holds addresses of global objects. Code reads an entry with `adrp` plus `ldr`. In the function `whole` the list of the used entries has the name `got`.
- **Stack guard**: a value that the compiler puts on the stack at function entry and compares before the return. When the value changed, the function calls `__stack_chk_fail`.
- **Callee-saved**: a register that must hold the same value when a function returns as when it was called. For v8 to v15 this holds for the low 8 bytes, the registers d8 to d15.
- **Stand-in loop**: a plain C loop that takes the place of an assembly kernel when the build machine is not AArch64.
- **`tackle-8mb.md`**: the design note of the test of 2026-11-15 on the buffer size of 8 MiB [Ref4].
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. When Python loads the file, it builds the table `NEW_LOOP`: the expected loop of each of the 5 new kernels ({L71-87}).
2. `main` reads the options and the two file arguments. Wrong arguments end the script with exit status 2 ({L223-241}).
3. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 ({L242-247}).
4. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, when the reference listing holds a kernel of round 3, or when the new listing has no block of the new binary ({L248-258}).
5. Part 1: for each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel ({L261-297}).
6. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW_LOOP` holds ({L298-305}).
7. With the option `--skip-new` it prints the summary line and ends here ({L308-311}).
8. Part 2: for each of the 5 new kernels the function `new_problems` applies the five rules. `main` prints one row per kernel ({L312-329}).
9. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed ({L330-336}).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its tables to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The code repo does not hold the folder `ref-bwx8`, the default place of the reference files. Without the options `--ref-listing` and `--ref-offsets` the script cannot read them there and ends with exit status 2 ({L242-247}). The reference files are the two files of the build record of bwx8 [Ref3].
- The repo holds no saved output of this script for the CRB build [Ref7]. A note of the project gives the result: all 21 kernels of `bwx8` were `same`, the 5 new loops had the expected instructions, and all loop offsets were as planned, 20 modulo 64 for the new kernels [Ref1]. The table `offsets.tsv` of the CRB build gives the value 20 for `asmread` and for the five new kernels [Ref5].
- What part 1 proves for a kernel with `same` and `ok`: every instruction of the function in `bwx10`, with every operand, equals the instruction at the same position in the accepted build of `bwx8`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that {L23-38} define.
- What part 2 proves for a new kernel with `ok`: the loop is exactly the list of `NEW_LOOP` and a `b.cc` back to the loop start. For a `read_pf` kernel the list is the 8 `ldp` of `asmread`, four `prfm pldl1keep`, `add x0, x0, #0x100` and `cmp x0, x1`. For `read_1pl` it is four `ldr` of 16 B each and the same `add` and `cmp`. The function has no other branch or call. Before the loop stand only the end-pointer instruction and stores of d registers. After the loop stand only loads of d registers and `ret`. The loop start modulo 64 equals the loop start modulo 64 of `asmread` in the same listing.
- This script holds no fixed number for the loop position of a new kernel. Rule 5 compares with `asmread` of the same listing only ({L213-216}).
- In the table of part 2 the column `loop` can say `expected` in a row whose result is `FAIL:`. The column looks only at the problems about the loop instructions, the loop branch, another branch or call, and the number of backward branches ({L326-327}).
- Limit: for the 21 kernels of part 1 the script proves equality with `bwx8` only. It holds no expected instruction list for them.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "`bwx10` acceptance on CRB, 2026-11-15 07:03 UTC" names the build at 07:02 UTC in `~/cache-perf/bwx10-20261115/` and its record `crb-build-1`. It says that `check_listing10.py` found 21 of 21 old kernels "same" against the `bwx8` build, that the 5 new loops have the expected instructions, and that all loop offsets are as planned, 20 modulo 64 for the new kernels.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/listing.txt`: the listing of the CRB build, with 26 blocks. The first block has the title line `=== bwx10 read ===` and the label line `00000000000041a0 <k_read>:`. `k_read` holds `b.hi 41a4 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x1bbf8>` and the offset 4072.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/`: the build record of bwx8, with `listing.txt` (21 blocks) and `offsets.tsv`. A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx10-2026-11-15/ref-bwx8/`, the reference folder beside the copy of the script in the project folder. In this listing `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `2f000` and the offset 4072. The folder `bwx10-2026-11-15` of the code repo holds no folder `ref-bwx8`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its title is "Design: explain the small read-bandwidth gain at 8 MiB". Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/offsets.tsv`: the table of the CRB build, with 26 kernel rows. The rows of `asmread`, `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` and `read_1pl` hold 20 in the column `loop_mod64`.
- [Ref6] A `diff` in this task of `check_listing10.py` against `check_listing8.py`, both of the code repo. The functions `sections`, `offsets`, `loop_start` and `whole` are equal in both files. In the code of part 1 of `main` ({L261-305}) one line differs: the line that builds `extra` ({L302}) has the added condition `k not in NEW_LOOP`.
- [Ref7] Searched in this task with `grep -r` in the folders `tests` and `status` of the repo for the text `failed_rows=`, which the summary line of this script holds. The search found two files: `check_listing12.out` and `check_listing13.out`, the saved outputs of the listing checks of bwx12 and bwx13.
