# `check_listing13.py` explained, line by line

- Source file: `bwx13-2026-11-15/check_listing13.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 351 lines, 17878 bytes).
- sha256 of the source when this page was built: `c014d135a04f227914c3d824d0c2f1c5c9ff85a1c2cbe1d39f0a711fd9413f3d`.

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

1. When Python loads the file, it defines the expected instruction lists of the `rand` kernels and the table `NEW` (lines 78 to 95).
2. `main` reads the options and the two file arguments. Wrong arguments end the script with exit status 2 (lines 238 to 256).
3. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 (lines 257 to 262).
4. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, when the reference listing holds a `rand` kernel, or when the new listing has no block of the new binary (lines 263 to 273).
5. Part 1: for each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel (lines 276 to 312).
6. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW` holds (lines 313 to 320).
7. With the option `--skip-new` it prints the summary line and ends here (lines 323 to 326).
8. Part 2: for each of the three `rand` kernels the function `new_problems` compares the whole function with the list of `expected_body`, checks the registers d8 to d15 and checks the loop offset. `main` prints one row per kernel (lines 327 to 344).
9. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed (lines 345 to 351).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its tables to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The code repo does not hold the folder `ref-bwx12`, the default place of the reference files. Without the options `--ref-listing` and `--ref-offsets` the script cannot read them there and ends with exit status 2 (lines 257 to 262). The reference files are the two files of the build record of bwx12 [Ref3].
- Result of the CRB build, from the saved output: all 55 rows of part 1 say `same` and `ok`. All 3 rows of part 2 say `expected` and `ok`. The summary line reports 0 failed rows in both parts [Ref1].
- What part 1 proves for a kernel with `same` and `ok`: every instruction of the function in `bwx13`, with every operand, equals the instruction at the same position in the accepted build of `bwx12`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that lines 27 to 42 define.
- What part 2 proves for a `rand` kernel with `expected` and `ok`: between the stores and the loads of d registers the function holds exactly the start code, loop 1, loop 2 and the four branches of lines 48 to 58, with every operand. Each loop holds the 8 `ldp` and N `nop`. The registers d8 to d15 are stored and loaded. The start of loop 1 lies at 20 modulo 64.
- Limit: for the 55 kernels of part 1 the script proves equality with `bwx12` only. It holds no expected instruction list for them.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.
- In part 2 the column `code` can say `expected` for a kernel that failed: the column looks for three texts in the problems only (lines 341 to 342). The column `result` holds every problem.
- The loop of a function is found through its first backward branch. A `rand` kernel has two loops, and the script checks that the first backward branch goes to loop 1 (line 224).

## Source and explanation, line by line

- Text shown: the file `bwx13-2026-11-15/check_listing13.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (351 lines, 17878 bytes, sha256 `c014d135a04f227914c3d824d0c2f1c5c9ff85a1c2cbe1d39f0a711fd9413f3d`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: what the script is, usage and reference (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_listing13.py - acceptance test of a bwx13 build (design tackle-8mb.md,` | Starts the documentation text of the script (lines 2 to 73). Python does not execute it. `main` prints it when it finds too many arguments or an unknown option (line 253). This line: the script is the acceptance test of a build of the runner program `bwx13`. It accepts or rejects a build. Its input is the machine code of every kernel, as text. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 3 | `"Fixed setup": reject a build whose acceptance listing differs).` | Documentation text: the design note `tackle-8mb.md`, section "Fixed setup", gives the rule that a build is rejected when its acceptance listing differs [Ref4]. |
| 5 | `It is check_listing12.py with another reference and other new kernels. The` | Documentation text: this script is `check_listing12.py` with another reference and other new kernels. `check_listing12.py` is the script of the same kind in the folder of bwx12, the runner version before `bwx13`. |
| 6 | `code of part 1 is unchanged.` | Documentation text: the code of part 1 is unchanged. |
| 8 | `Runs on the development machine, on the listing.txt and offsets.tsv that` | Documentation text: the script runs on the development machine, not on CRB (the Arm reference server under test). It reads the files `listing.txt` and `offsets.tsv` that ... |
| 9 | `build13.sh wrote on CRB.` | Documentation text: ... the build script `build13.sh` wrote on CRB. |
| 10 | `Usage: check_listing13.py [listing.txt [offsets.tsv]]` | Documentation text: the usage. Both file arguments are optional. Line 255 and line 256 set the defaults. |
| 11 | `           [--ref-listing F] [--ref-offsets F] [--binary bwx13] [--ref-binary bwx12] [--skip-new]` | Documentation text: the five options. `--ref-listing` and `--ref-offsets` name other reference files. `--binary` and `--ref-binary` give the names of the two binaries as they stand in the title lines of the listings. The defaults are `bwx13` and `bwx12`. `--skip-new` leaves out part 2 (line 69). |
| 13 | `The reference is the accepted build of bwx12 (crb-build-1 of the folder` | Documentation text: the reference is the accepted build of bwx12. It is the folder `crb-build-1` in the folder ... |
| 14 | `bwx12-2026-11-15), saved in ref-bwx12/listing.txt and ref-bwx12/offsets.tsv` | Documentation text: ... `bwx12-2026-11-15`. Its two files are saved as `ref-bwx12/listing.txt` and `ref-bwx12/offsets.tsv` ... The code repo does not hold the folder `ref-bwx12`. The project folder of `bwx13` on the agent server holds it. Its two files are equal, byte for byte, to the files in the build record of bwx12 [Ref3]. |
| 15 | `beside this script, binary "bwx12".` | Documentation text: ... beside this script. The name of the binary in these files is `bwx12`. |

### Documentation text: part 1, the kernels of the reference (lines 17 to 43)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `Part 1, the 55 kernels of the reference binary. The rules are the rules of` | Documentation text: part 1 covers the 55 kernels of the reference binary. These are the kernels that bwx12 already had. The rules are the rules of ... |
| 18 | `check_listing12.py part 1 (which are the rules of check_listing8.py),` | Documentation text: ... part 1 of `check_listing12.py`, which are the rules of `check_listing8.py`, ... |
| 19 | `unchanged. For every kernel of the reference:` | Documentation text: ... unchanged. Four rules follow. They hold for every kernel of the reference. |
| 20 | ` 1. the new listing has the kernel, and the function has a loop;` | Documentation text: rule 1 for a kernel of the reference. The new listing has the kernel, and the function has a loop. Lines 281 to 285 implement it. |
| 21 | ` 2. the whole function text equals the reference text, apart from addresses;` | Documentation text: rule 2 for a kernel of the reference. The whole function text equals the reference text, apart from addresses. Lines 287 to 290 implement it. |
| 22 | ` 3. the loop start modulo 64 equals the reference value. Both are computed` | Documentation text: rule 3 for a kernel of the reference. The loop start modulo 64 equals the reference value (lines 299 to 300). The loop start modulo 64 is the remainder of the loop start address divided by 64. Both values are computed ... |
| 23 | `    from the listings;` | Documentation text: ... from the listings. |
| 24 | ` 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as` | Documentation text: rule 4 for a kernel of the reference. The row of the kernel in the new `offsets.tsv` gives the same `loop_mod64` as ... Lines 301 to 304 implement it. |
| 25 | `    the new listing and as the row of the reference offsets.tsv.` | Documentation text: ... the new listing and as the row of the reference `offsets.tsv`. |
| 27 | `What "apart from addresses" means here:` | Documentation text: lines 28 to 40 define how two functions at different addresses are compared. The function `whole` (line 141) implements it. |
| 28 | ` - an instruction address is not compared;` | Documentation text: an instruction address is not compared. |
| 29 | ` - a branch target inside the function is compared as its distance from the` | Documentation text: a branch target inside the function is compared as its distance from the ... |
| 30 | `   function start;` | Documentation text: ... function start. |
| 31 | ` - a target outside the function (the stub of bl, the page of a single adrp)` | Documentation text: a target outside the function ... The text names two cases: the stub that a `bl` calls, and the page of a single `adrp`. `bl` is the call instruction. The listing of the CRB build has 2 `bl` instructions, one in `oldread` and one in `oldread2`. Both call `__stack_chk_fail@plt`, the function for a failed stack guard [Ref2]. |
| 32 | `   is compared by its symbol name, not by its address;` | Documentation text: ... is compared by its symbol name, not by its address. The code keeps all that stands in the angle brackets (line 152). When the listing shows a symbol name plus an offset there, the offset is compared too. |
| 33 | ` - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from` | Documentation text: the pair `adrp xN, page` and `ldr xN, [xN, #offset]` loads a pointer from ... `adrp` puts the address of a 4096-byte page into a register. The `ldr` after it loads a pointer from that page. |
| 34 | `   the table of global addresses of the binary. In the reference only the` | Documentation text: ... the table of global addresses of the binary. This table holds addresses of global objects of the binary. In the reference only the ... |
| 35 | `   load of the stack-guard pointer has this form. Page and offset are the` | Documentation text: ... load of the stack-guard pointer has this form. The page and the offset are the ... |
| 36 | `   place of the pointer in the table, so they are not compared. The check` | Documentation text: ... place of the pointer in the table. So they are not compared. The check ... |
| 37 | `   fails if the new binary loads pointers from more` | Documentation text: ... fails if the new binary loads pointers from more ... |
| 38 | `   places of the table than the reference, per function and over all` | Documentation text: ... places of the table than the reference, per function (lines 294 to 296) and over all ... |
| 39 | `   kernels. The reference uses one place. A row whose offset differs from the` | Documentation text: ... kernels (lines 313 to 316). The reference uses one place. A row whose offset differs from the ... |
| 40 | `   reference prints "NOTE: got_offset_differs" in place of "ok": read it.` | Documentation text: ... reference prints `NOTE: got_offset_differs` in place of `ok` (lines 297 to 298). The text asks the reader to read such a row. |
| 41 | `The loop of a function is the range from the target of its first backward` | Documentation text: the definition of the loop. The loop of a function is the range from the target of its first backward ... A backward branch is a branch whose target address is lower than its own address. |
| 42 | `branch to that branch.` | Documentation text: ... branch to that branch. The function `loop_start` (line 131) finds the first address of the loop. |

### Documentation text: part 2 (the new kernels), `--skip-new` and the exit status (lines 44 to 73)

| Line | Source | Explanation |
|---:|---|---|
| 44 | `Part 2, the 3 kernels rand_nop0, rand_nop96 and rand_nop256 (the keys of NEW` | Documentation text: part 2 covers the 3 kernels `rand_nop0`, `rand_nop96` and `rand_nop256`, the keys of the table `NEW` ... (line 92). They are the kernels that `bwx13` adds to `bwx12`. The function `new_problems` (line 180) implements the rules. |
| 45 | `below). The reference does not have them. All 3 must be in the new listing.` | Documentation text: ... below. The reference does not have these kernels. All 3 must be in the new listing (lines 333 to 336). |
| 46 | `For rand_nopN the function must be, instruction for instruction and with` | Documentation text: for a kernel `rand_nopN` the function must be the list of lines 48 to 58, instruction for instruction and with ... N is the number of `nop` instructions per block: 0, 96 or 256. A `nop` does nothing. A block is 256 B of the range of the kernel. |
| 47 | `every operand:` | Documentation text: ... every operand. Line 203 compares the function with the expected list. |
| 48 | ` 1. stores of d registers to the stack (any number of instructions);` | Documentation text: item 1. Stores of d registers to the stack, any number of instructions (lines 192 to 194). A d register is the low half of an Arm vector register. |
| 49 | ` 2. lsr x10, x1, #5; sub x12, x10, #1; tst x10, x12; mov x9, #0; b.ne to` | Documentation text: item 2, the start code. `lsr x10, x1, #5` divides the number of words in `x1` by 32. The result in `x10` is the number of blocks. `sub x12, x10, #1` puts that number minus 1 into `x12`. `tst x10, x12` computes the AND of the two values. It is 0 when the number of blocks is a power of two, and not 0 for every other number above 0. `mov x9, #0` sets the step counter `x9` to 0. `b.ne` branches to ... |
| 50 | `    loop 2;` | Documentation text: ... loop 2 when the AND is not 0. So loop 2 runs when the number of blocks is not a power of two. |
| 51 | ` 3. loop 1 (the random order): add x11, x9, x9; add x11, x11, #1;` | Documentation text: item 3, loop 1. The text calls its block order the random order. `add x11, x9, x9` and `add x11, x11, #1` compute 2 times the step plus 1 ... |
| 52 | `    mul x11, x11, x9; and x11, x11, x12; add x13, x0, x11, lsl #8; the 8 ldp` | Documentation text: ... `mul x11, x11, x9` multiplies this by the step. `and x11, x11, x12` keeps the low bits, which is the value modulo the number of blocks. So `x11` is the number of the block to read. `add x13, x0, x11, lsl #8` computes the address of the block: the pointer `x0` plus 256 times the block number. Then come the 8 `ldp` ... |
| 53 | `    of asmread with x13 as the base; N nop; add x9, x9, #1; cmp x9, x10;` | Documentation text: ... of `asmread`, with `x13` as the base register. `ldp` loads a pair of registers. The 8 `ldp` load the 256 B of the block. Then come N `nop`. `add x9, x9, #1` counts the step, and `cmp x9, x10` compares it with the number of blocks. |
| 54 | `    b.cc (the same instruction as b.lo) to the start of loop 1;` | Documentation text: ... `b.cc` branches back to the start of loop 1 while the step is below the number of blocks (unsigned compare). `b.cc` and `b.lo` are two names of one branch instruction. |
| 55 | ` 4. b to the first instruction after loop 2;` | Documentation text: item 4. After loop 1 an unconditional branch `b` jumps over loop 2, to the first instruction after it. |
| 56 | ` 5. loop 2 (the order of asmread): add x13, x0, x9, lsl #8; the 8 ldp; N nop;` | Documentation text: item 5, loop 2. It reads the blocks in address order, as `asmread` does. `add x13, x0, x9, lsl #8` computes the address of the block with the number of the step. Then come the 8 `ldp` and N `nop` ... |
| 57 | `    add x9, x9, #1; cmp x9, x10; b.cc to the start of loop 2;` | Documentation text: ... the same two instructions for the step, and `b.cc` back to the start of loop 2. |
| 58 | ` 6. loads of d registers from the stack, and ret.` | Documentation text: item 6. Loads of d registers from the stack (lines 198 to 200), and `ret`, the return to the caller (line 195). |
| 59 | `So the function has 8 ldp and N nop in each loop, 5 instructions of index` | Documentation text: the sum of the six items. The function has 8 `ldp` and N `nop` in each loop, 5 instructions of index ... |
| 60 | `arithmetic in loop 1 and 1 in loop 2, and no branch beside the four named.` | Documentation text: ... arithmetic in loop 1 and 1 in loop 2, and no branch beside the four named: the `b.ne`, the two `b.cc` and the `b`. |
| 61 | `Also:` | Documentation text: two more rules follow. |
| 62 | ` 7. d8 to d15 are all stored before item 2 and loaded after item 5;` | Documentation text: rule 7. The registers d8 to d15 must all be stored before item 2 and loaded after item 5 (lines 215 to 217). The Arm calling convention requires that a function gives them back unchanged, and the 8 `ldp` of the kernel overwrite them. |
| 63 | ` 8. the start of loop 1 modulo 64 equals the planned value (20, the offset of` | Documentation text: rule 8. The start of loop 1 modulo 64 must equal the planned value, 20. This is the offset of ... |
| 64 | `    asmread in the same listing), and the row in offsets.tsv gives the same` | Documentation text: ... the loop of `asmread` in the same listing (lines 226 to 231). And the row of the kernel in `offsets.tsv` must give the same ... |
| 65 | `    value. The offset is not important for these kernels: it is checked so` | Documentation text: ... value (lines 232 to 233). The text adds that the offset is not important for these kernels. It is checked so ... |
| 66 | `    that the record in offsets.tsv is right.` | Documentation text: ... that the record in `offsets.tsv` is right. |
| 67 | `Any other kernel that the reference lacks is a failure.` | Documentation text: any other kernel that the reference lacks is a failure. Lines 317 to 320 implement it. |
| 69 | `--skip-new leaves out part 2. It is only for a build on a machine that is not` | Documentation text: the option `--skip-new` leaves out part 2. It is only for a build on a machine that is not ... |
| 70 | `AArch64, where the new kernels are plain C stand-in loops. The last line then` | Documentation text: ... AArch64 (the 64-bit Arm instruction set). There the new kernels are plain C stand-in loops. The last line of the output then ... |
| 71 | `says that the new kernels were NOT CHECKED.` | Documentation text: ... says that the new kernels were `NOT CHECKED`. `--skip-new` was not used for the saved output of the CRB build. Its summary line says `new_kernels=3`, not `NOT CHECKED` [Ref1]. |
| 72 | `Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.` | Documentation text: the exit statuses. 0: all checks passed. 1: a check failed. 2: a file could not be used. The code also returns 2 for wrong arguments (line 249, line 254). The exit status is the return value of `main` (line 351). |
| 73 | `"""` | Ends the documentation text. |

### Imports and constants (lines 74 to 81)

| Line | Source | Explanation |
|---:|---|---|
| 74 | `import os` | Loads the module `os`. The script uses it for file paths. |
| 75 | `import re` | Loads the module `re` for regular expressions. |
| 76 | `import sys` | Loads the module `sys` for the arguments and the exit status. |
| 78 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. |
| 79 | `REF_DIR = os.path.join(HERE, "ref-bwx12")` | `REF_DIR`: its subfolder `ref-bwx12`, the place of the reference files. The code repo does not hold this folder (see the row of line 14). |
| 80 | `TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")` | `TARGET`: a compiled pattern for a branch target at the end of an instruction: a hexadecimal address, a space and a name in angle brackets. Group 1 holds the address. The page operand of an `adrp` instruction has the same form. The pattern matches it too. Two examples from the listing of the CRB build (`listing.txt`): the branch target `4aa4 <k_read+0x4>` and the page operand `2f000 <__FRAME_END__+0x14bb8>` [Ref2]. |

### Expected instructions of the new kernels, table `NEW`, patterns `SAVE` and `RESTORE` (lines 82 to 97)

| Line | Source | Explanation |
|---:|---|---|
| 82 | `# The new kernels, as objdump prints them (one space between the fields). x0` | Comment: the lists below hold the instructions of the new kernels in the form in which `objdump` prints them, with one space between the fields. `objdump` is the tool that prints the machine code of a binary as text. The function `sections` (line 98) brings the instruction text of a listing into the same form. The register `x0` ... |
| 83 | `# is the pointer and x1 is the number of words. x9 is the step, x10 the number` | Comment: ... is the pointer to the range, and `x1` is the number of 8-byte words. `x9` is the step, `x10` the number ... |
| 84 | `# of blocks, x11 the block index, x12 the mask, x13 the address of the block.` | Comment: ... of blocks, `x11` the block index, `x12` the mask (the number of blocks minus 1), and `x13` the address of the block. |
| 85 | `RAND_LDP8 = ["ldp q0, q1, [x13]", "ldp q2, q3, [x13, #32]", "ldp q4, q5, [x13, #64]", "ldp q6, q7, [x13, #96]",` | `RAND_LDP8`: the 8 `ldp` instructions of a `rand` kernel. Each one loads two 16-byte registers. Together they load q0 to q15 from the 256 bytes at the block address `x13`. This line holds the first four, for the offsets 0, 32, 64 and 96 bytes. |
| 86 | `             "ldp q8, q9, [x13, #128]", "ldp q10, q11, [x13, #160]", "ldp q12, q13, [x13, #192]", "ldp q14, q15, [x13, #224]"]` | Continues the list of line 85: the other four `ldp`, for the offsets 128, 160, 192 and 224 bytes. |
| 87 | `RAND_INIT = ["lsr x10, x1, #5", "sub x12, x10, #0x1", "tst x10, x12", "mov x9, #0x0"]` | `RAND_INIT`: the four instructions of the start code (line 49). The constants stand in the form that `objdump` prints: `#0x1` and `#0x0`. |
| 88 | `RAND_INDEX = ["add x11, x9, x9", "add x11, x11, #0x1", "mul x11, x11, x9", "and x11, x11, x12", "add x13, x0, x11, lsl #8"]` | `RAND_INDEX`: the five instructions of loop 1 that compute the block number and the block address (lines 51 to 52). |
| 89 | `SEQ_INDEX = ["add x13, x0, x9, lsl #8"]` | `SEQ_INDEX`: the one instruction of loop 2 that computes the block address from the step (line 56). |
| 90 | `RAND_STEP = ["add x9, x9, #0x1", "cmp x9, x10"]` | `RAND_STEP`: the two instructions at the end of each loop: add 1 to the step `x9`, then compare it with the number of blocks `x10`. |
| 91 | `RAND_MOD = 20  # the planned start of loop 1 modulo 64` | `RAND_MOD`: 20. Comment: the planned start of loop 1 modulo 64. The unit is bytes. |
| 92 | `NEW = {"rand_nop0": 0, "rand_nop96": 96, "rand_nop256": 256}  # kernel: number of nop per block` | `NEW`: the table of the new kernels. A key is a kernel name. Its value is the number of `nop` instructions per block: 0, 96 or 256. |
| 93 | `NEW_LOOP = NEW  # the name that the code of part 1 uses for "is a new kernel"` | `NEW_LOOP`: a second name for the same table. Comment: the code of part 1 uses this name to ask whether a kernel is a new kernel. |
| 94 | `SAVE = re.compile(r"(?:stp d(\d+), d(\d+)\|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")` | `SAVE`: a compiled pattern for a store of one or two d registers to the stack: `stp` with two d registers or `str` with one, then `[sp]` with or without an offset, with or without `!`. Example: `stp d8, d9, [sp, #-64]!`. The groups hold the register numbers. |
| 95 | `RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)\|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")` | `RESTORE`: a compiled pattern for a load of one or two d registers from the stack: `ldp` with two d registers or `ldr` with one. Example: `ldp d8, d9, [sp], #64`. The groups hold the register numbers. |

### Functions `sections` and `offsets`: read the two kinds of input file (lines 98 to 130)

| Line | Source | Explanation |
|---:|---|---|
| 98 | `def sections(path):` | Starts the function `sections`. It reads a listing file. |
| 99 | `    """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""` | Documentation text of `sections`: it returns a dictionary. A key is the pair (binary, kernel). Its value is the list of (address, instruction text) of that kernel function, in file order. Example: in the listing of the CRB build (`listing.txt`) the first block starts with the title line `=== bwx13 read ===`. The label line `0000000000004aa0 <k_read>:` follows it. It is no instruction line and is skipped (line 107) [Ref2]. |
| 100 | `    out, cur = {}, None` | `out`: the dictionary. `cur`: the list of the block that is read now. It is `None` outside a block. |
| 101 | `    with open(path) as f:` | Opens the file. |
| 102 | `        for line in f:` | Loop over the lines of the file. |
| 103 | `            m = re.match(r"=== (\S+) (\S+) ===", line)` | Tests whether the line is a title line of the form `=== BINARY KERNEL ===`. Group 1 holds the name of the binary, group 2 the name of the kernel. |
| 104 | `            if m:` | A title line starts the block of one kernel. |
| 105 | `                cur = out.setdefault((m.group(1), m.group(2)), [])` | `cur` becomes the list for this pair. `setdefault` creates an empty list when the pair is new. |
| 106 | `                continue` | Goes to the next line. |
| 107 | `            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)` | Tests whether the line is an instruction line: spaces, a hexadecimal address (group 1), a colon, spaces or tabs, and the instruction (group 2). The label line of a function has no colon directly after its address. So it does not match and is skipped. |
| 108 | `            if m and cur is not None:` | Only inside a block ... |
| 109 | `                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()` | ... the text is cleaned. The `objdump` comment after `//` is cut off. Each run of spaces and tabs becomes one space. |
| 110 | `                cur.append((int(m.group(1), 16), text))` | Appends the pair of the address as a number and the cleaned text to the block. |
| 111 | `            elif line.startswith("##"):` | A line that starts with `##` ... |
| 112 | `                cur = None` | ... ends the block that is read now. |
| 113 | `    return out` | Returns the dictionary. |
| 116 | `def offsets(path):` | Starts the function `offsets`. It reads a file `offsets.tsv`. |
| 117 | `    """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""` | Documentation text of `offsets`: it returns a dictionary from (binary, kernel) to the text of the column `loop_mod64`. |
| 118 | `    out = {}` | `out`: the dictionary. |
| 119 | `    with open(path) as f:` | Opens the file. |
| 120 | `        head = f.readline().rstrip("\n").split("\t")` | `head`: the fields of the first line, split at the tab characters. |
| 121 | `        if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:` | The first line must hold exactly the 6 column names. |
| 122 | `            raise ValueError("%s: unexpected header line" % path)` | If not, the function raises `ValueError` with the text `unexpected header line`. `main` then ends with exit status 2 (lines 260 to 262). |
| 123 | `        for line in f:` | Loop over the other lines. |
| 124 | `            p = line.rstrip("\n").split("\t")` | `p`: the fields of the line. |
| 125 | `            if len(p) != 6:` | Every row must have 6 fields. |
| 126 | `                raise ValueError("%s: a row with %d fields" % (path, len(p)))` | If not, the function raises `ValueError`. |
| 127 | `            out[(p[0], p[1])] = p[5]` | Stores column 6 under the pair of column 1 and column 2. The script uses columns 1, 2 and 6 only. It ignores the columns `function`, `start` and `loop_start`. |
| 128 | `    return out` | Returns the dictionary. |

### Functions `loop_start`, `whole` and `numbers` (lines 131 to 167)

| Line | Source | Explanation |
|---:|---|---|
| 131 | `def loop_start(insns):` | Starts the function `loop_start`. `insns` is the list of (address, text) of one function. |
| 132 | `    """address of the loop start: the target of the first backward branch into the function, or None"""` | Documentation text of `loop_start`: it returns the address of the loop start. That is the target of the first backward branch into the function. Without such a branch the result is `None`. |
| 133 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 134 | `    for addr, text in insns:` | Goes through the instructions in order. |
| 135 | `        m = TARGET.search(text)` | Looks for a branch target at the end of the instruction text. |
| 136 | `        if m and first <= int(m.group(1), 16) < addr:` | The branch counts when its target lies inside the function and before the branch itself (`first <= target < addr`). |
| 137 | `            return int(m.group(1), 16)` | Returns that target. This address is the loop start. `main` computes a loop start modulo 64 as `loop_start(...) % 64`. |
| 138 | `    return None` | Returns `None` when the function has no such branch. |
| 141 | `def whole(insns):` | Starts the function `whole`. It returns the text of a function in a form that does not depend on the addresses. |
| 142 | `    """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""` | Documentation text of `whole`: it returns two lists. The first is the function text without addresses (`out`). The second holds the places (page, offset) of the pointer loads from the table of global addresses (`got`). Two examples with text of the listing of the CRB build (`listing.txt`): `b.hi 4aa4 <k_read+0x4>` becomes `b.hi +0x4` (line 149), and the call of `__stack_chk_fail@plt` becomes `bl (outside <__stack_chk_fail@plt>)` (line 152) [Ref2]. |
| 143 | `    first, last, out, got = insns[0][0], insns[-1][0], [], []` | `first` and `last`: the addresses of the first and the last instruction. `out` and `got`: the two result lists. |
| 144 | `    adrp_reg = adrp_page = None` | `adrp_reg` and `adrp_page`: the register and the page of an `adrp` instruction, kept for the next instruction only. |
| 145 | `    for _, text in insns:` | Loop over the instruction texts. |
| 146 | `        m = TARGET.search(text)` | Looks for a target at the end of the text. |
| 147 | `        page = None` | `page`: the address text of a target outside the function. `None` at first. |
| 148 | `        if m and first <= int(m.group(1), 16) <= last:` | A target inside the function ... |
| 149 | `            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... becomes its distance from the function start, written as `+0x` and hexadecimal digits. |
| 150 | `        elif m:` | A target outside the function: |
| 151 | `            page = m.group(1)` | `page` keeps the address text for line 159. |
| 152 | `            text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]` | The text becomes `(outside NAME)`. NAME is all that stands in the angle brackets, with the brackets: a symbol name, or a symbol name plus an offset. It is kept, and the address before it is removed. |
| 153 | `        load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)` | `load`: tests whether the whole text is a load of the form `ldr xA, [xB, #N]`. The groups hold the two registers and the offset. |
| 154 | `        if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:` | The pair counts when the instruction before was an `adrp` with a page, and both registers of the load are the register of that `adrp`. |
| 155 | `            got.append((adrp_page, load.group(3)))` | Records the place (page, offset) in `got`. |
| 156 | `            out[-1] = "adrp %s, (table page)" % adrp_reg` | Replaces the text of the `adrp` before by the fixed text `adrp xN, (table page)`. |
| 157 | `            text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)` | Replaces the text of the load by the fixed text `ldr xN, [xN, #(table)]`. So the page and the offset are not part of the text comparison. In the listing of the CRB build and in the reference listing only `oldread` and `oldread2` have this pair. Each has it twice, with the page address `2f000` (hexadecimal) and the offset 4072 bytes [Ref2] [Ref3]. |
| 158 | `        m = re.match(r"adrp (x\d+), ", text)` | Tests whether this instruction is an `adrp`. Group 1 holds its register. |
| 159 | `        adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)` | Remembers the register and the page of an `adrp` with a page outside the function. Every other instruction clears both values. |
| 160 | `        out.append(text)` | Appends the text to `out`. |
| 161 | `    return out, got` | Returns the two lists. |
| 164 | `def numbers(match):` | Starts the function `numbers`. `match` is one match of `SAVE` or of `RESTORE`. |
| 165 | `    return {int(g) for g in match.groups() if g is not None}` | Returns the set of the register numbers that the match captured. A group without a value is left out. |

### Function `expected_body`: the expected instructions of one new kernel (lines 168 to 179)

| Line | Source | Explanation |
|---:|---|---|
| 168 | `def expected_body(nops, at):` | Starts the function `expected_body`. It builds the list of the instructions that a kernel `rand_nopN` must have between its stores and its loads of d registers. `nops` is N. `at` is the distance of the first of these instructions from the function start, in bytes. |
| 169 | `    """The instructions of rand_nopN between the stores and the loads of d registers. at: the distance of the` | Documentation text of `expected_body`: the function returns the instructions of `rand_nopN` between the stores and the loads of d registers. `at` is the distance of the ... |
| 170 | `    first of them from the function start, in bytes. A branch is written with its target as that distance.` | Documentation text: ... first of them from the function start, in bytes. A branch is written with its target as that distance, for example `b.ne +0x68`. |
| 171 | `    Returns (list, distance of the start of loop 1)."""` | Documentation text: the function returns a pair: the list, and the distance of the start of loop 1. |
| 172 | `    loop1 = RAND_INDEX + RAND_LDP8 + ["nop"] * nops + RAND_STEP` | `loop1`: the instructions of loop 1 without its branch: the 5 of `RAND_INDEX`, the 8 `ldp`, `nops` times `nop`, and the 2 of `RAND_STEP`. |
| 173 | `    loop2 = SEQ_INDEX + RAND_LDP8 + ["nop"] * nops + RAND_STEP` | `loop2`: the instructions of loop 2 without its branch: the 1 of `SEQ_INDEX`, the 8 `ldp`, `nops` times `nop`, and the 2 of `RAND_STEP`. |
| 174 | `    l1 = at + 4 * (len(RAND_INIT) + 1)` | `l1`: the distance of the start of loop 1 from the function start, in bytes. Each AArch64 instruction has 4 bytes. Before loop 1 stand the 4 instructions of `RAND_INIT` and the `b.ne`. With 4 stores of d registers `at` is 16 bytes, and `l1` is 36 bytes (`0x24`). |
| 175 | `    l2 = l1 + 4 * (len(loop1) + 2)` | `l2`: the distance of the start of loop 2. Between the two starts stand the instructions of loop 1, its `b.cc`, and the `b` of item 4. For N = 0 and `l1` = 36 this gives 104 bytes (`0x68`). |
| 176 | `    l3 = l2 + 4 * (len(loop2) + 1)` | `l3`: the distance of the first instruction after loop 2. The instructions of loop 2 and its `b.cc` stand before it. For N = 0 this gives 152 bytes (`0x98`). |
| 177 | `    return (RAND_INIT + ["b.ne +0x%x" % l2] + loop1 + ["b.cc +0x%x" % l1, "b +0x%x" % l3] + loop2 + ["b.cc +0x%x" % l2]), l1` | Returns the pair. The list is: `RAND_INIT`, `b.ne` to loop 2, `loop1`, `b.cc` to the start of loop 1, `b` to the place after loop 2, `loop2`, and `b.cc` to the start of loop 2. The format `+0x%x` writes a distance as hexadecimal digits. The second value of the pair is `l1`. In the listing of the CRB build the function `k_rand_nop0` holds the three distances `+0x24`, `+0x68` and `+0x98` [Ref2]. |

### Function `new_problems`: the rules of part 2 for one new kernel (lines 180 to 236)

| Line | Source | Explanation |
|---:|---|---|
| 180 | `def new_problems(kernel, insns, want_mod, off_row):` | Starts the function `new_problems`. It applies the rules of part 2 to one new kernel and returns a list of problem texts. An empty list says that the kernel passed. `insns` is the list of (address, text) of the kernel function. `off_row` is the value of the kernel in `offsets.tsv`, or `None`. |
| 181 | `    """Part 2 for one new kernel. want_mod: the loop start modulo 64 of asmread in the same listing, or None."""` | Documentation text of `new_problems`: part 2 for one new kernel. `want_mod` is the loop start modulo 64 of `asmread` in the same listing, or `None`. |
| 182 | `    p = []` | `p`: the list of problem texts, empty at first. |
| 183 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 184 | `    text = []` | `text`: the instruction texts of the function in the form of the expected list. It is empty at first. |
| 185 | `    for _, t in insns:  # a branch target inside the function becomes its distance from the function start` | Loop over the instructions of the function. Comment: a branch target inside the function becomes its distance from the function start. |
| 186 | `        m = TARGET.search(t)` | Looks for a target at the end of the instruction text. |
| 187 | `        if m:` | When the text has a target ... |
| 188 | `            t = t[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... the address and the name are replaced by `+0x` and the distance from the function start in hexadecimal digits. The line does not test whether the target lies inside the function. A target outside gives a text that the expected list does not hold. Then the comparison of line 203 fails. |
| 189 | `        text.append(re.sub(r"^b\.lo ", "b.cc ", t))` | Appends the text to the list. `re.sub` first replaces the name `b.lo` at the start of a text by `b.cc`. Both names stand for one instruction, and the expected list uses `b.cc`. |
| 190 | `    head = 0` | `head`: the number of instructions at the start of the function that store d registers. It is 0 at first. |
| 191 | `    saved, restored = set(), set()` | `saved` and `restored`: the sets of the numbers of the d registers that the function stores and loads. Both are empty at first. |
| 192 | `    while head < len(text) and SAVE.fullmatch(text[head]):` | Goes forward over the instructions at the start that match `SAVE` as a whole (`fullmatch`). These are the stores of d registers to the stack. The loop stops at the first instruction that is no such store. |
| 193 | `        saved \|= numbers(SAVE.fullmatch(text[head]))` | Adds the register numbers of the store to `saved` (function `numbers`, line 164). |
| 194 | `        head += 1` | Counts the store. |
| 195 | `    if not text or text[-1] != "ret":` | The last instruction of the function must be `ret`. The part `not text` covers an empty list. `main` never passes one (line 333). |
| 196 | `        p.append("the function does not end with ret")` | If not, a problem says that the function does not end with `ret`. |
| 197 | `    tail = len(text) - 1` | `tail`: the index of the last instruction. The loop below moves it back over the loads of d registers. |
| 198 | `    while tail > head and RESTORE.fullmatch(text[tail - 1]):` | Goes backward from the instruction before the last one, as long as the instruction matches `RESTORE` as a whole. These are the loads of d registers from the stack. `tail > head` keeps the loop out of the stores at the start. |
| 199 | `        restored \|= numbers(RESTORE.fullmatch(text[tail - 1]))` | Adds the register numbers of the load to `restored`. |
| 200 | `        tail -= 1` | Moves `tail` one instruction back. |
| 201 | `    body = text[head:tail]` | `body`: the instructions between the stores at the start and the loads at the end. By the rules they are the start code, the two loops and their branches. |
| 202 | `    want, l1 = expected_body(NEW[kernel], 4 * head)` | `want`: the expected list for this kernel. `expected_body` (line 168) builds it from the nop count of `NEW` and from the distance `4 * head` bytes (4 bytes per store instruction). `l1`: the expected distance of the start of loop 1. |
| 203 | `    if body != want:` | The two lists `body` and `want` must be equal: the same count, the same order, and every instruction text equal with every operand. The next lines only write the messages for the case that they differ. |
| 204 | `        for name in ("nop", "ldp"):` | Loop over the two instruction names `nop` and `ldp`. |
| 205 | `            n_got = sum(t.split(" ")[0] == name for t in body)` | `n_got`: how many instructions of `body` have this name. The name is the first word of the text. |
| 206 | `            n_want = sum(t.split(" ")[0] == name for t in want)` | `n_want`: the same count in the expected list. |
| 207 | `            if n_got != n_want:` | When the two counts differ ... |
| 208 | `                p.append("the function has %d %s between the stores and the loads of d registers, expected %d" % (n_got, name, n_want))` | ... a problem gives both counts. Its text is `the function has`, the count, the name, `between the stores and the loads of d registers, expected` and the expected count. So one message tells the reader that the number of loads or of `nop` is wrong. |
| 209 | `        diff = [i for i in range(max(len(body), len(want))) if (body[i] if i < len(body) else "(none)") != (want[i] if i < len(want) else "(none)")]` | `diff`: the positions at which the two lists differ. Where one list is shorter, its entry counts as `(none)`. |
| 210 | `        for i in diff[:3]:` | For the first 3 of these positions ... |
| 211 | `            p.append("instruction %d after the stores is '%s', expected '%s'" % (i, body[i] if i < len(body) else "(none)",` | ... a problem gives the position, the instruction that the function has there, and the expected instruction. The position counts from 0 at the first instruction after the stores. The call goes on in line 212. |
| 212 | `                                                                                  want[i] if i < len(want) else "(none)"))` | Continues the call of line 211: the expected instruction, or `(none)` past the end of the expected list. |
| 213 | `        if len(diff) > 3:` | When more than 3 positions differ ... |
| 214 | `            p.append("%d more instructions differ" % (len(diff) - 3))` | ... a problem gives the number of the other positions that differ. |
| 215 | `    need = set(range(8, 16))` | `need`: the set of the numbers 8 to 15, for the registers d8 to d15. |
| 216 | `    if need - saved or need - restored:` | Rule 7: each of them must be stored at the start and loaded at the end. `need - saved` is the set of the registers that are not stored. `need - restored` is the set of those that are not loaded. |
| 217 | `        p.append("d8-d15: not stored before the code: %s; not loaded after it: %s" % (sorted(need - saved) or "none", sorted(need - restored) or "none"))` | If one is missing, a problem lists the registers that are not stored and those that are not loaded. An empty list is written as `none`. |
| 218 | `    if saved != restored:` | The stored set and the reloaded set must be equal. |
| 219 | `        p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))` | If not, a problem shows both sets. The script compares register numbers only. It does not compare the stack offset of a store with the stack offset of its reload. |
| 220 | `    loop = loop_start(insns)` | `loop`: the loop start of the function. `loop_start` (line 131) gives the target of the first backward branch. |
| 221 | `    if loop is None:` | A function without a backward branch ... |
| 222 | `        p.append("no backward branch")` | ... gets the problem `no backward branch` ... |
| 223 | `        return p` | ... and the function returns here. The checks below need a loop start. |
| 224 | `    if loop - first != l1:` | The first backward branch must go to the expected start of loop 1: the distance of `loop` from the function start must be `l1`. |
| 225 | `        p.append("the first backward branch goes to +0x%x, loop 1 is expected at +0x%x" % (loop - first, l1))` | If not, a problem gives both distances as hexadecimal numbers. |
| 226 | `    if want_mod is None:` | Rule 8, the place of the loop. `want_mod` is the loop start modulo 64 of `asmread` in the same listing (lines 327 to 329). It is `None` when the listing has no block of `asmread`, or when that function has no loop. |
| 227 | `        p.append("asmread has no loop in this listing, so the loop offset cannot be compared")` | Then a problem says that the loop offset cannot be compared. |
| 228 | `    elif want_mod != RAND_MOD:` | When `asmread` has a loop, its loop start modulo 64 must be the planned value `RAND_MOD` (20). |
| 229 | `        p.append("asmread has its loop at %d modulo 64, the plan says %d" % (want_mod, RAND_MOD))` | If not, a problem gives the value of `asmread` and the planned value. |
| 230 | `    if loop % 64 != RAND_MOD:` | The loop start of this kernel modulo 64 must also be the planned value. `loop % 64` is the offset of the loop start inside a 64-byte block of code. |
| 231 | `        p.append("loop offset modulo 64 is %d, planned %d" % (loop % 64, RAND_MOD))` | If not, a problem gives both values. |
| 232 | `    if off_row != str(loop % 64):` | The row of the kernel in `offsets.tsv` must hold the same number as text. |
| 233 | `        p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))` | If not, a problem gives both values. A missing row is written as `no row`. |
| 234 | `    return p` | Returns the list of problems. |

### Function `main`: arguments and input files (lines 237 to 274)

| Line | Source | Explanation |
|---:|---|---|
| 237 | `def main():` | Starts the function `main`. Its return value becomes the exit status (line 351). |
| 238 | `    args = sys.argv[1:]` | `args`: the arguments of the command line without the script name. |
| 239 | `    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),` | `opt`: the defaults of the 4 options that take a value. The reference files are `listing.txt` and `offsets.tsv` in the folder `REF_DIR`. |
| 240 | `           "--binary": "bwx13", "--ref-binary": "bwx12"}` | Continues the dictionary of line 239: the default names of the two binaries, `bwx13` for the new binary and `bwx12` for the reference. |
| 241 | `    skip_new = "--skip-new" in args` | `skip_new`: true when the arguments hold `--skip-new`. This option is a flag without a value. |
| 242 | `    if skip_new:` | When the flag is present ... |
| 243 | `        args.remove("--skip-new")` | ... it is removed from the list. |
| 244 | `    for name in opt:` | Loop over the 4 option names. |
| 245 | `        if name in args:` | An option that is present ... |
| 246 | `            i = args.index(name)` | ... stands at position `i` ... |
| 247 | `            if i + 1 >= len(args):` | ... and needs one more argument after it. |
| 248 | `                print("%s needs a value" % name)` | Without it the script prints that the option needs a value ... |
| 249 | `                return 2` | ... and ends with exit status 2. |
| 250 | `            opt[name] = args[i + 1]` | The next argument becomes the value of the option. |
| 251 | `            del args[i:i + 2]` | Both are removed from the list. |
| 252 | `    if len(args) > 2 or any(a.startswith("--") for a in args):` | More than 2 remaining arguments, or a remaining argument that starts with `--` ... |
| 253 | `        print(__doc__)` | ... print the documentation text ... |
| 254 | `        return 2` | ... and the script ends with exit status 2. |
| 255 | `    listing = args[0] if args else os.path.join(HERE, "listing.txt")` | `listing`: the first remaining argument, or `listing.txt` in the folder of the script. |
| 256 | `    offs = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")` | `offs`: the second remaining argument, or `offsets.tsv` in the folder of the listing. |
| 257 | `    try:` | Starts the block in which a file error is caught. |
| 258 | `        ref, got = sections(opt["--ref-listing"]), sections(listing)` | Reads the reference listing into `ref` and the new listing into `got`. |
| 259 | `        ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)` | Reads the reference `offsets.tsv` into `ref_off` and the new `offsets.tsv` into `got_off`. |
| 260 | `    except (OSError, ValueError) as e:` | A file that cannot be opened (`OSError`), or an offsets table with a wrong form (`ValueError`) ... |
| 261 | `        print("cannot use: %s" % e)` | ... prints `cannot use:` and the reason ... |
| 262 | `        return 2` | ... and ends the script with exit status 2. |
| 263 | `    b, rb = opt["--binary"], opt["--ref-binary"]` | `b`: the name of the new binary. `rb`: the name of the reference binary. |
| 264 | `    kernels = [k for (bb, k) in ref if bb == rb]` | `kernels`: the list of the kernel names of the reference binary, in the order of the reference listing. |
| 265 | `    if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):` | One more case that ends with exit status 2: the reference listing has no kernel of the reference binary, or a reference kernel has no instructions or no loop. |
| 266 | `        print("the reference listing has no usable block of binary %s" % rb)` | Prints a message that names the reference binary ... |
| 267 | `        return 2` | ... and ends with exit status 2. |
| 268 | `    if any(k in NEW_LOOP for k in kernels):` | One more case: the reference listing holds a new kernel, which is a key of `NEW_LOOP`. |
| 269 | `        print("the reference listing holds a rand_nop kernel: it is not a listing of %s" % rb)` | Prints the message that the reference listing holds a `rand_nop` kernel and is therefore not a listing of the reference binary. |
| 270 | `        return 2` | Ends with exit status 2. |
| 271 | `    if not any(bb == b for bb, _ in got):` | One more case: the new listing has no block of the new binary. |
| 272 | `        print("no '=== %s kernel ===' block in %s" % (b, listing))` | Prints a message that names the new binary and the listing file ... |
| 273 | `        return 2` | ... and ends with exit status 2. |

### Function `main`: part 1, one output row per kernel of the reference (lines 275 to 321)

| Line | Source | Explanation |
|---:|---|---|
| 275 | `    # Part 1: the kernels of the reference (the code of check_listing8.py)` | Comment: part 1, the kernels of the reference. It is the code of `check_listing8.py`. |
| 276 | `    bad, r_places, g_places = 0, set(), set()` | `bad`: the count of failures that the summary line prints as `failed_rows`. It counts each kernel of the reference whose row fails, and 1 for each of the two checks over the whole listing that fails (lines 313 to 320). `r_places` and `g_places`: the places of the table of global addresses that the reference listing and the new listing use, over all kernels. |
| 277 | `    print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")` | Prints the column names of the output table of the reference kernels, with tabs between them: `kernel`, `start`, `loop_start`, `loop_mod64`, `ref_loop_mod64`, `text`, `result`. |
| 278 | `    for k in kernels:` | Loop over the kernels of the reference. |
| 279 | `        r_insns, insns = ref[(rb, k)], got.get((b, k), [])` | `r_insns`: the instructions of the kernel in the reference listing. `insns`: its instructions in the new listing, or an empty list when the new listing has no block for it. |
| 280 | `        r_mod = loop_start(r_insns) % 64` | `r_mod`: the loop start modulo 64 of the kernel in the reference listing. |
| 281 | `        loop = loop_start(insns) if insns else None` | Rule 1: `loop` is the loop start in the new listing. It is `None` when the block is missing or the function has no backward branch. |
| 282 | `        if loop is None:` | In that case ... |
| 283 | `            print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))` | ... the row says `FAIL: no listing or no loop`, with `NA` in the three columns of the new listing ... |
| 284 | `            bad += 1` | ... `bad` grows by 1 ... |
| 285 | `            continue` | ... and the loop goes to the next kernel. |
| 286 | `        problems, notes = [], []` | `problems` and `notes`: the texts for the result column of this kernel. |
| 287 | `        (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)` | Rule 2, the function text. `whole` (line 141) gives the text without addresses and the table places of the reference function (`r_text`, `r_got`) and of the new function (`text`, `g_got`). |
| 288 | `        same = text == r_text` | `same`: true when the two text lists are equal. They then hold the same number of instructions, and each instruction text is equal with every operand. |
| 289 | `        if not same:` | When the text is not equal ... |
| 290 | `            problems.append("function text differs from the reference")` | ... this is a problem. |
| 291 | `        else:` | When the text is equal: |
| 292 | `            r_places.update(r_got)` | The places of the reference function are added to `r_places` ... |
| 293 | `            g_places.update(g_got)` | ... and the places of the new function to `g_places`. |
| 294 | `            if len(set(g_got)) > len(set(r_got)):` | More distinct places in the new function than in the reference function ... |
| 295 | `                problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %` | ... is a problem. Its text gives the number of places of the new function ... |
| 296 | `                                (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))` | ... each place with its page and offset, and the number of the reference. |
| 297 | `            elif [o for _, o in g_got] != [o for _, o in r_got]:` | A new function with no more places than the reference, but with other offsets ... |
| 298 | `                notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))` | ... gets a note and not a failure. When the row has no failure, its result column then starts with `NOTE: got_offset_differs` in place of `ok`. No row of the saved output of the CRB build has this note [Ref1]. |
| 299 | `        if loop % 64 != r_mod:` | Rule 3: the loop start modulo 64 of the new listing must equal the reference value. |
| 300 | `            problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))` | If not, a problem gives both values. |
| 301 | `        if ref_off.get((rb, k)) != str(r_mod):` | Rule 4: the reference `offsets.tsv` must hold the reference value for this kernel. |
| 302 | `            problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))` | If not, a problem gives the value of the table, or `no row`. |
| 303 | `        if got_off.get((b, k)) != str(loop % 64):` | The new `offsets.tsv` must hold the value of the new listing. |
| 304 | `            problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))` | If not, a problem gives both values. |
| 305 | `        print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",` | Prints the row of the kernel: the kernel name, the function start and the loop start (hexadecimal addresses), the loop start modulo 64, the reference value, `same` or `DIFFERS` ... |
| 306 | `                                             "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))` | ... and the result: `FAIL:` with the problems, or `NOTE:` with the notes, or `ok`. |
| 307 | `        if not same:` | When the text differs ... |
| 308 | `            for i in range(max(len(text), len(r_text))):` | ... a loop over the positions of the longer text ... |
| 309 | `                g = text[i] if i < len(text) else "(none)"` | ... takes the new instruction text, or `(none)` past the end ... |
| 310 | `                w = r_text[i] if i < len(r_text) else "(none)"` | ... and the reference instruction text, or `(none)` past the end. |
| 311 | `                print("    %s %-40s \| reference %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` between them. The mark `!=` stands before a line that differs. |
| 312 | `        bad += bool(problems)` | `bad` grows by 1 when the kernel has a problem. |
| 313 | `    if len(g_places) > len(r_places):` | After the loop, a check over all kernels with equal text: the new listing may not use more distinct places of the table of global addresses than the reference. |
| 314 | `        print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %` | If it does, a line that starts with `FAIL:` gives the number of places of the new listing ... |
| 315 | `              (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))` | ... the places, and the number of the reference. |
| 316 | `        bad += 1` | `bad` grows by 1. |
| 317 | `    extra = sorted(k for bb, k in got if bb == b and k not in kernels and k not in NEW_LOOP)` | `extra`: the kernels of the new binary in the new listing that are not in the reference and not new kernels (keys of `NEW_LOOP`). |
| 318 | `    if extra:` | When there is such a kernel ... |
| 319 | `        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))` | ... a line that starts with `FAIL:` names them ... |
| 320 | `        bad += 1` | ... and `bad` grows by 1. |

### Function `main`: part 2, one output row per new kernel, and the exit status (lines 322 to 351)

| Line | Source | Explanation |
|---:|---|---|
| 322 | `    # Part 2: the rand_nop kernels` | Comment: part 2, the `rand_nop` kernels. |
| 323 | `    new_bad = 0` | `new_bad`: the count of the failures of part 2. |
| 324 | `    if skip_new:` | With the option `--skip-new` ... |
| 325 | `        print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))` | ... the script prints the summary line here, with the words `new_kernels=NOT CHECKED (--skip-new)` ... |
| 326 | `        return 1 if bad else 0` | ... and returns 1 when part 1 has a failure, else 0. The new kernels are then not checked. |
| 327 | `    orig = got.get((b, "asmread"), [])` | `orig`: the instructions of `asmread` in the new listing, or an empty list. |
| 328 | `    orig_loop = loop_start(orig) if orig else None` | `orig_loop`: its loop start, or `None` when `asmread` is missing or has no loop. |
| 329 | `    want_mod = None if orig_loop is None else orig_loop % 64` | `want_mod`: the loop start modulo 64 of `asmread`, or `None`. |
| 330 | `    print("new_kernel\tstart\tloop_start\tloop_mod64\tasmread_loop_mod64\tcode\tresult")` | Prints the column names of the second output table: `new_kernel`, `start`, `loop_start`, `loop_mod64`, `asmread_loop_mod64`, `code`, `result`. |
| 331 | `    for k in NEW_LOOP:` | Loop over the new kernels. |
| 332 | `        insns = got.get((b, k), [])` | `insns`: the instructions of the kernel in the new listing, or an empty list. |
| 333 | `        if not insns:` | Every new kernel must have a block in the new listing. If it has none ... |
| 334 | `            print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))` | ... the row says `FAIL: no listing` ... |
| 335 | `            new_bad += 1` | ... `new_bad` grows by 1 ... |
| 336 | `            continue` | ... and the loop goes to the next kernel. |
| 337 | `        problems = new_problems(k, insns, want_mod, got_off.get((b, k)))` | `new_problems` (line 180) applies the rules of part 2 and returns the problems of this kernel. |
| 338 | `        loop = loop_start(insns)` | `loop`: the loop start of the kernel, for the row. |
| 339 | `        print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,` | Prints the row of the kernel. The call goes on to line 343. This line: the kernel name, the function start and the loop start (hexadecimal addresses, `NA` without a loop) ... |
| 340 | `                                               "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,` | ... the loop start modulo 64 of the kernel, and the loop start modulo 64 of `asmread` (`NA` when `asmread` has none) ... |
| 341 | `                                               "DIFFERS" if any("instruction" in x or "backward" in x or ", expected" in x` | ... and the sixth column, `code`. It says `DIFFERS` when a problem text holds the word `instruction`, the word `backward`, or the text `, expected`. These stand in the problems about a wrong instruction, about the backward branch, and about the count of `nop` or `ldp`. |
| 342 | `                                                                for x in problems) else "expected",` | Continues the test of line 341 over all problems of the kernel. Without such a problem the column says `expected`. Any other problem shows only in the result column. Examples: a function that does not end with `ret`, and a register of d8 to d15 that is not stored. |
| 343 | `                                               "FAIL: " + "; ".join(problems) if problems else "ok"))` | Ends the call: the result column is `FAIL:` with the problems, or `ok`. |
| 344 | `        new_bad += bool(problems)` | `new_bad` grows by 1 when the kernel has a problem. |
| 345 | `    print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %` | Prints the summary line. In the saved output of the CRB build it is `# binary=bwx13 reference=bwx12 kernels=55 failed_rows=0 new_kernels=3 new_failed_rows=0` [Ref1]. |
| 346 | `          (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))` | Continues the call of line 345: the values of the line. They are the two binary names, the number of reference kernels, the failures of part 1, the number of new kernels and the failures of part 2. |
| 347 | `    return 1 if bad or new_bad else 0` | `main` returns 1 when a check of part 1 or of part 2 failed, and 0 when none failed. |
| 350 | `if __name__ == "__main__":` | This test is true when the file runs as a script. |
| 351 | `    sys.exit(main())` | Calls `main` and makes its return value the exit status of the script. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/check_listing13.out`: the saved output of this script for the CRB build, 61 lines. They are the header line of part 1, 55 rows that all hold `same` and `ok`, the header line of part 2, 3 rows that all hold `expected` and `ok`, and the summary line `# binary=bwx13 reference=bwx12 kernels=55 failed_rows=0 new_kernels=3 new_failed_rows=0`. No row holds the word `NOTE`.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-whole-chip-read-drop/build-records/bwx13-crb-build-1/listing.txt`: the checked listing, with 58 blocks. The first block has the title line `=== bwx13 read ===` and the label line `0000000000004aa0 <k_read>:`. `k_read` holds `b.hi 4aa4 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x14bb8>` and the offset 4072. `k_rand_nop0` has 4 stores of d registers and the branches `b.ne` to `<k_rand_nop0+0x68>`, `b.cc` to `<k_rand_nop0+0x24>` and `b` to `<k_rand_nop0+0x98>`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-17-whole-chip-7200/build-records/bwx12-crb-build-1/`: the build record of bwx12, with `listing.txt` (55 blocks) and `offsets.tsv`. A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx13-2026-11-15/ref-bwx12/`, the reference folder beside the copy of the script in the project folder. In this listing `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `2f000` and the offset 4072. The folder `bwx13-2026-11-15` of the code repo holds four files and no folder `ref-bwx12`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
