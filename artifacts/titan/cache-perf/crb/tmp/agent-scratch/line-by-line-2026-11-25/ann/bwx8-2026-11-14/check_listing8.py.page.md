## Short version: purpose

`check_listing8.py` is the acceptance test of a build of the runner `bwx8`: it reads the machine code of every kernel (`listing.txt`) and the table of loop addresses (`offsets.tsv`) that the build script wrote. It accepts the build only when each of the 21 kernels of the first runner version, `bwx`, is unchanged apart from addresses and keeps its loop start modulo 64, and when the new listing holds no other kernel. The script of the next runner version, `check_listing10.py`, keeps this code as its part 1 and adds a part 2 with rules for five new kernels.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **`objdump`**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **`listing.txt`**: the `objdump` text of every kernel function of `bwx8`, written by the build script `build8.sh`. The block of one kernel starts with a line `=== bwx8 <kernel> ===`. The function of a kernel has the name `k_` plus the kernel name.
- **`offsets.tsv`**: a table with one row per kernel, written by `build8.sh`. Its columns are `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- **Reference, accepted build**: the reference is the `listing.txt` and the `offsets.tsv` of the accepted build of `bwx`, the first runner version. By the documentation text of the script they are saved in the folder `crb-build-2` of the folder `bwx-2026-11-13`. The accepted build of a runner version is the build that serves as the reference for the next version.
- **Build record, CRB build**: the build record is the folder `bwx8-crb-build-1` of the test data. It holds the files that one run of `build8.sh` wrote on 2026-11-15. This page calls that run the CRB build. A note of the project names this build as the build that was accepted on CRB [Ref1].
- **Development machine**: the machine on which this script runs, by its documentation text. It is not CRB.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range.
- **Loop start modulo 64 (`loop_mod64`, loop offset)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **`ldr`**: an instruction that loads one register from memory.
- **`bl`**: the instruction that calls a function.
- **Stub**: a short piece of code in the binary through which a call of a library function goes. `objdump` names it with the ending `@plt`.
- **`adrp`**: an instruction that puts the address of a 4096-byte page into a register.
- **Table of global addresses**: a table in the binary that holds addresses of global objects. Code reads an entry with `adrp` plus `ldr`. In the function `whole` the list of the used entries has the name `got`.
- **Stack guard**: a value that the compiler puts on the stack at function entry and compares before the return. When the value changed, the function calls `__stack_chk_fail`.
- **`tackle-8mb.md`**: the design note of the test of 2026-11-15 on the buffer size of 8 MiB [Ref4].
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` reads the four options and the two file arguments. Wrong arguments end the script with exit status 2 ({L118-133}).
2. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 ({L134-139}).
3. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, or when the new listing has no block of the new binary ({L140-147}).
4. For each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel ({L149-185}).
5. It checks the places of the table of global addresses over all kernels. It rejects a kernel that the reference does not hold ({L186-193}).
6. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed ({L194-199}).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its table to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The default place of the reference files is the folder `crb-build-2` of the folder `bwx-2026-11-13` ({L47}). The code repo holds no such folder. Without the options `--ref-listing` and `--ref-offsets` the script cannot read the reference there and ends with exit status 2 ({L134-139}). The repo keeps the two reference files in the build record `bwx-crb-build-2` [Ref3].
- The reference files hold four binaries: `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`. The script uses the binary `bwx` only ({L141}) [Ref3].
- The repo holds no saved output of this script for the CRB build [Ref6]. A note of the project gives the result: 21 of 21 kernels `same` with the reference offsets, and no note [Ref1]. The table `offsets.tsv` of the CRB build gives each of the 21 kernels the `loop_mod64` value that the reference table gives it for the binary `bwx` [Ref5].
- What the script proves for a kernel with `same` and `ok`: every instruction of the function in `bwx8`, with every operand, equals the instruction at the same position in the accepted build of `bwx`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that {L22-37} define.
- Limit: the script proves equality with `bwx` only. It holds no expected instruction list for any kernel.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel, and not the code of the trial mode that `bwx8` adds.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "CRB acceptance, 2026-11-15" names the build `crb-build-1` with gcc 14.2.0. It says that `check_listing8.py` gives 21 of 21 kernels "same" with the reference offsets, and no note.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/listing.txt`: the listing of the CRB build, with 21 blocks. The first block has the title line `=== bwx8 read ===` and the label line `0000000000004020 <k_read>:`. `k_read` holds `b.hi 4024 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x1e454>` and the offset 4072.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/`: the record of the second CRB build of `bwx`, with `listing.txt` (84 blocks: 21 kernels for each of the binaries `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`) and `offsets.tsv` (84 kernel rows). A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/`, the default reference folder of the copy of the script in the project folder. In the blocks of `bwx`, `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `1f000` and the offset 4072, and no other function holds an `adrp`. The folder `bwx-2026-11-13` of the code repo holds no folder `crb-build-2`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its title is "Design: explain the small read-bandwidth gain at 8 MiB". Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/offsets.tsv`: the table of the CRB build, with 21 kernel rows. Checked in this task with a script: the 21 kernel names and their `loop_mod64` values equal the 21 rows of the binary `bwx` in `offsets.tsv` of the record of [Ref3].
- [Ref6] Searched in this task with `grep -r` in the folders `tests` and `status` of the repo for the text `failed_rows=`, which the summary line of this script holds. The search found two files: `check_listing12.out` and `check_listing13.out`, the saved outputs of the listing checks of bwx12 and bwx13.
