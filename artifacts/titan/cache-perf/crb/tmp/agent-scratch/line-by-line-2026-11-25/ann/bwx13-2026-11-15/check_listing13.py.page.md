## Short version: purpose

`check_listing13.py` is the acceptance test of a build of the runner `bwx13`: it reads the machine code of every kernel (`listing.txt`) and the table of loop addresses (`offsets.tsv`) that the build script wrote. It accepts the build only when the 55 kernels of the runner version before, `bwx12`, are unchanged, and when the three new `rand` kernels hold exactly the expected instructions at the planned loop position. It is `check_listing12.py` with another reference and other new kernels: the code of part 1 is unchanged, and the code of part 2 is new.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`rand_nop0`, `rand_nop96`, `rand_nop256`**: the three kernels that `bwx13` adds to `bwx12`. They read 256 B blocks of their range with the 8 `ldp` of `asmread`, with 0, 96 or 256 `nop` instructions after the loads of a block. This page calls them the `rand` kernels.
- **Block, loop 1, loop 2**: a block is 256 B of the range of a `rand` kernel. Loop 1 of such a kernel reads the blocks in a computed order: step `i` reads block `i * (2 * i + 1)` modulo the number of blocks. Loop 2 reads the blocks in address order. The kernel runs loop 2 when the number of blocks is not a power of two.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`objdump`**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **`listing.txt`**: the `objdump` text of every kernel function of `bwx13`, written by the build script `build13.sh`. The block of one kernel starts with a line `=== bwx13 <kernel> ===`. The function of a kernel has the name `k_` plus the kernel name.
- **`offsets.tsv`**: a table with one row per kernel, written by `build13.sh`. Its columns are `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- **Reference, accepted build**: the reference is the `listing.txt` and the `offsets.tsv` of the accepted build of `bwx12`. By the documentation text of the script they are saved in a folder `ref-bwx12` beside the script. The accepted build of a runner version is the build that serves as the reference for the next version.
- **Build record, CRB build**: the build record is the folder `bwx13-crb-build-1` of the test data. It holds the files that one run of `build13.sh` wrote, and the saved output of this script for them [Ref1]. This page calls that run the CRB build. The folder name says that the run was on CRB.
- **Development machine**: the machine on which this script runs, by its documentation text. It is not CRB.
- **AArch64**: the 64-bit Arm instruction set.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range.
- **Loop start modulo 64 (`loop_mod64`, loop offset)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **q and d registers**: two names for the 32 vector registers of AArch64. `qN` is the full 16-byte register N. `dN` is its low 8 bytes.
- **`ldp`, `stp`, `ldr`, `str`**: `ldp` loads a pair of registers from memory. `stp` stores a pair. `ldr` loads one register. `str` stores one.
- **`nop`**: an instruction that does nothing.
- **`b.cc`, `b.lo`, `b.ne`, `b`**: branch instructions. `b.cc` and `b.lo` are two names of one conditional branch: after `cmp a, b` it jumps when a is below b as unsigned numbers. `b.ne` jumps when the result of the instruction before was not 0. `b` always jumps.
- **`bl`, `ret`**: `bl` calls a function. `ret` returns to the caller.
- **Stub**: a short piece of code in the binary through which a call of a library function goes. `objdump` names it with the ending `@plt`.
- **`adrp`**: an instruction that puts the address of a 4096-byte page into a register.
- **Table of global addresses**: a table in the binary that holds addresses of global objects. Code reads an entry with `adrp` plus `ldr`. In the function `whole` the list of the used entries has the name `got`.
- **Stack guard**: a value that the compiler puts on the stack at function entry and compares before the return. When the value changed, the function calls `__stack_chk_fail`.
- **Stand-in loop**: a plain C loop that takes the place of an assembly kernel when the build machine is not AArch64.
- **`tackle-8mb.md`**: the design note of the test of 2026-11-15 on the buffer size of 8 MiB.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. When Python loads the file, it defines the expected instruction lists of the `rand` kernels and the table `NEW` ({L78-95}).
2. `main` reads the options and the two file arguments. Wrong arguments end the script with exit status 2 ({L238-256}).
3. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 ({L257-262}).
4. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, when the reference listing holds a `rand` kernel, or when the new listing has no block of the new binary ({L263-273}).
5. Part 1: for each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel ({L276-312}).
6. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW` holds ({L313-320}).
7. With the option `--skip-new` it prints the summary line and ends here ({L323-326}).
8. Part 2: for each of the three `rand` kernels the function `new_problems` compares the whole function with the list of `expected_body`, checks the registers d8 to d15 and checks the loop offset. `main` prints one row per kernel ({L327-344}).
9. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed ({L345-351}).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its tables to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The code repo does not hold the folder `ref-bwx12`, the default place of the reference files. Without the options `--ref-listing` and `--ref-offsets` the script cannot read them there and ends with exit status 2 ({L257-262}). The reference files are the two files of the build record of bwx12 [Ref3].
- Result of the CRB build, from the saved output: all 55 rows of part 1 say `same` and `ok`. All 3 rows of part 2 say `expected` and `ok`. The summary line reports 0 failed rows in both parts [Ref1].
- What part 1 proves for a kernel with `same` and `ok`: every instruction of the function in `bwx13`, with every operand, equals the instruction at the same position in the accepted build of `bwx12`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that {L27-42} define.
- What part 2 proves for a `rand` kernel with `expected` and `ok`: between the stores and the loads of d registers the function holds exactly the start code, loop 1, loop 2 and the four branches of {L48-58}, with every operand. Each loop holds the 8 `ldp` and N `nop`. The registers d8 to d15 are stored and loaded. The start of loop 1 lies at 20 modulo 64.
- Limit: for the 55 kernels of part 1 the script proves equality with `bwx12` only. It holds no expected instruction list for them.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.
- In part 2 the column `code` can say `expected` for a kernel that failed: the column looks for three texts in the problems only ({L341-342}). The column `result` holds every problem.
- The loop of a function is found through its first backward branch. A `rand` kernel has two loops, and the script checks that the first backward branch goes to loop 1 ({L224}).

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/check_listing13.out`: the saved output of this script for the CRB build, 61 lines. They are the header line of part 1, 55 rows that all hold `same` and `ok`, the header line of part 2, 3 rows that all hold `expected` and `ok`, and the summary line `# binary=bwx13 reference=bwx12 kernels=55 failed_rows=0 new_kernels=3 new_failed_rows=0`. No row holds the word `NOTE`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/listing.txt`: the checked listing, with 58 blocks. The first block has the title line `=== bwx13 read ===` and the label line `0000000000004aa0 <k_read>:`. `k_read` holds `b.hi 4aa4 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x14bb8>` and the offset 4072. `k_rand_nop0` has 4 stores of d registers and the branches `b.ne` to `<k_rand_nop0+0x68>`, `b.cc` to `<k_rand_nop0+0x24>` and `b` to `<k_rand_nop0+0x98>`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-17-whole-chip-7200/build-records/bwx12-crb-build-1/`: the build record of bwx12, with `listing.txt` (55 blocks) and `offsets.tsv`. A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx13-2026-11-15/ref-bwx12/`, the reference folder beside the copy of the script in the project folder. In this listing `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `2f000` and the offset 4072. The folder `bwx13-2026-11-15` of the code repo holds four files and no folder `ref-bwx12`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
