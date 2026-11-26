## Short version: purpose

`check_listing11.py` is the acceptance test of a build of the runner `bwx11`: it reads the machine code of every kernel (`listing.txt`) and the table of loop addresses (`offsets.tsv`) that the build script wrote. It accepts the build only when the 26 kernels of the runner version before, `bwx10`, are unchanged, and when the three new kernels `read_nop64`, `read_nop96` and `read_nop128` hold exactly the expected loop at the planned loop position. It is `check_listing10.py` with another reference and other new kernels, and the code of part 1 is unchanged.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Runner source**: the C file of the runner, here `bwx11.c`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Round 4, `read_nop64`, `read_nop96`, `read_nop128`**: round 4 is the set of additions that made bwx11 out of bwx10. Its three new kernels are the `asmread` loop with 64, 96 or 128 `nop` instructions after the 8 loads. "Round" does not mean a repeat of a kernel sequence here.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`objdump`**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **`listing.txt`**: the `objdump` text of every kernel function of `bwx11`, written by the build script `build11.sh`. The block of one kernel starts with a line `=== bwx11 <kernel> ===`. The function of a kernel has the name `k_` plus the kernel name.
- **`offsets.tsv`**: a table with one row per kernel, written by `build11.sh`. Its columns are `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- **Reference, accepted build**: the reference is the `listing.txt` and the `offsets.tsv` of the accepted build of `bwx10`. By the documentation text of the script they are saved in a folder `ref-bwx10` beside the script. The accepted build of a runner version is the build that serves as the reference for the next version.
- **Build record, CRB build**: the build record is the folder `bwx11-crb-build-1` of the test data. It holds the files that one run of `build11.sh` wrote on 2026-11-15. This page calls that run the CRB build. A note of the project says that this build ran on CRB [Ref1].
- **Development machine**: the machine on which this script runs, by its documentation text. It is not CRB.
- **AArch64**: the 64-bit Arm instruction set.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range.
- **Loop start modulo 64 (`loop_mod64`, loop offset)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **q, v and d registers**: three names for the 32 vector registers of AArch64. `qN` is the full 16-byte register N. `dN` is its low 8 bytes. `vN` is the same register seen as a vector of elements.
- **`ldp`, `stp`, `ldr`, `str`**: `ldp` loads a pair of registers from memory. `stp` stores a pair. `ldr` loads one register. `str` stores one.
- **`nop`**: an instruction that does nothing.
- **`b.cc`, `b.lo`**: two names of one conditional branch. After `cmp a, b` it jumps when a is below b as unsigned numbers.
- **`bl`, `ret`**: `bl` calls a function. `ret` returns to the caller.
- **Stub**: a short piece of code in the binary through which a call of a library function goes. `objdump` names it with the ending `@plt`.
- **`adrp`**: an instruction that puts the address of a 4096-byte page into a register.
- **Table of global addresses**: a table in the binary that holds addresses of global objects. Code reads an entry with `adrp` plus `ldr`. In the function `whole` the list of the used entries has the name `got`.
- **Stack guard**: a value that the compiler puts on the stack at function entry and compares before the return. When the value changed, the function calls `__stack_chk_fail`.
- **Callee-saved**: a register that must hold the same value when a function returns as when it was called. For v8 to v15 this holds for the low 8 bytes, the registers d8 to d15.
- **Stand-in loop**: a plain C loop that takes the place of an assembly kernel when the build machine is not AArch64.
- **`tackle-8mb.md`**: the design note of the test of 2026-11-15 on the buffer size of 8 MiB.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. When Python loads the file, it builds the table `NEW_LOOP`: the expected loop of each of the 3 new kernels ({L76-89}).
2. `main` reads the options and the two file arguments. Wrong arguments end the script with exit status 2 ({L227-245}).
3. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 ({L246-251}).
4. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, when the reference listing holds a kernel of round 4, or when the new listing has no block of the new binary ({L252-262}).
5. Part 1: for each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel ({L265-301}).
6. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW_LOOP` holds ({L302-309}).
7. With the option `--skip-new` it prints the summary line and ends here ({L312-315}).
8. Part 2: for each of the 3 new kernels the function `new_problems` applies the five rules. `main` prints one row per kernel ({L316-333}).
9. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed ({L334-340}).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its tables to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The code repo does not hold the folder `ref-bwx10`, the default place of the reference files. Without the options `--ref-listing` and `--ref-offsets` the script cannot read them there and ends with exit status 2 ({L246-251}). The reference files are the two files of the build record of bwx10 [Ref3].
- The repo holds no saved output of this script for the CRB build. A note of the project gives the result: all 26 kernels of `bwx10` were `same`, and the 3 new loops were as expected, with the loop offset 20 modulo 64 [Ref1]. The table `offsets.tsv` of the CRB build gives the value 20 for `asmread` and for the three new kernels [Ref5].
- What part 1 proves for a kernel with `same` and `ok`: every instruction of the function in `bwx11`, with every operand, equals the instruction at the same position in the accepted build of `bwx10`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that {L27-44} define.
- What part 2 proves for a new kernel with `ok`: the loop is exactly the 8 `ldp` of `asmread`, then N `nop`, then `add x0, x0, #0x100`, `cmp x0, x1` and a `b.cc` back to the loop start. The function has no other branch or call. Before the loop stand only the end-pointer instruction and stores of d registers. After the loop stand only loads of d registers and `ret`. The loop start lies at 20 modulo 64, as the loop start of `asmread` in the same listing.
- Limit: for the 26 kernels of part 1 the script proves equality with `bwx10` only. It holds no expected instruction list for them.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "`bwx11` acceptance on CRB, 2026-11-15 08:41 UTC" names the build in `~/cache-perf/bwx11-20261115/` and its record `crb-build-1`. It says that `check_listing11.py` found 26 of 26 kernels of `bwx10` "same" and the 3 new loops as expected, with the loop offset 20 modulo 64.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/listing.txt`: the listing of the CRB build, with 29 blocks. The first block has the title line `=== bwx11 read ===` and the label line `0000000000004260 <k_read>:`. `k_read` holds `b.hi 4264 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x1ab40>` and the offset 4072.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/`: the build record of bwx10, with `listing.txt` (26 blocks) and `offsets.tsv`. A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx11-2026-11-15/ref-bwx10/`, the reference folder beside the copy of the script in the project folder. In this listing `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `2f000` and the offset 4072. The folder `bwx11-2026-11-15` of the code repo holds no folder `ref-bwx10`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx11-crb-build-1/offsets.tsv`: the table of the CRB build, with 29 kernel rows. The rows of `asmread`, `read_nop64`, `read_nop96` and `read_nop128` hold 20 in the column `loop_mod64`.
