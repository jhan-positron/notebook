# `check_listing10.py` explained, line by line

- Source file: `bwx10-2026-11-15/check_listing10.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 336 lines, 17419 bytes).
- sha256 of the source when this page was built: `919341a4208a4bad6d700f4cdc21c4fd1950a63c7b52a07c01d0fb8c24b7ab13`.

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

1. When Python loads the file, it builds the table `NEW_LOOP`: the expected loop of each of the 5 new kernels (lines 71 to 87).
2. `main` reads the options and the two file arguments. Wrong arguments end the script with exit status 2 (lines 223 to 241).
3. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 (lines 242 to 247).
4. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, when the reference listing holds a kernel of round 3, or when the new listing has no block of the new binary (lines 248 to 258).
5. Part 1: for each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel (lines 261 to 297).
6. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW_LOOP` holds (lines 298 to 305).
7. With the option `--skip-new` it prints the summary line and ends here (lines 308 to 311).
8. Part 2: for each of the 5 new kernels the function `new_problems` applies the five rules. `main` prints one row per kernel (lines 312 to 329).
9. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed (lines 330 to 336).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its tables to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The code repo does not hold the folder `ref-bwx8`, the default place of the reference files. Without the options `--ref-listing` and `--ref-offsets` the script cannot read them there and ends with exit status 2 (lines 242 to 247). The reference files are the two files of the build record of bwx8 [Ref3].
- The repo holds no saved output of this script for the CRB build [Ref7]. A note of the project gives the result: all 21 kernels of `bwx8` were `same`, the 5 new loops had the expected instructions, and all loop offsets were as planned, 20 modulo 64 for the new kernels [Ref1]. The table `offsets.tsv` of the CRB build gives the value 20 for `asmread` and for the five new kernels [Ref5].
- What part 1 proves for a kernel with `same` and `ok`: every instruction of the function in `bwx10`, with every operand, equals the instruction at the same position in the accepted build of `bwx8`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that lines 23 to 38 define.
- What part 2 proves for a new kernel with `ok`: the loop is exactly the list of `NEW_LOOP` and a `b.cc` back to the loop start. For a `read_pf` kernel the list is the 8 `ldp` of `asmread`, four `prfm pldl1keep`, `add x0, x0, #0x100` and `cmp x0, x1`. For `read_1pl` it is four `ldr` of 16 B each and the same `add` and `cmp`. The function has no other branch or call. Before the loop stand only the end-pointer instruction and stores of d registers. After the loop stand only loads of d registers and `ret`. The loop start modulo 64 equals the loop start modulo 64 of `asmread` in the same listing.
- This script holds no fixed number for the loop position of a new kernel. Rule 5 compares with `asmread` of the same listing only (lines 213 to 216).
- In the table of part 2 the column `loop` can say `expected` in a row whose result is `FAIL:`. The column looks only at the problems about the loop instructions, the loop branch, another branch or call, and the number of backward branches (lines 326 to 327).
- Limit: for the 21 kernels of part 1 the script proves equality with `bwx8` only. It holds no expected instruction list for them.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.

## Source and explanation, line by line

- Text shown: the file `bwx10-2026-11-15/check_listing10.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (336 lines, 17419 bytes, sha256 `919341a4208a4bad6d700f4cdc21c4fd1950a63c7b52a07c01d0fb8c24b7ab13`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: what the script is, usage and reference (lines 1 to 13)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_listing10.py - acceptance test of a bwx10 build (design tackle-8mb.md,` | Starts the documentation text of the script (lines 2 to 62). Python does not execute it. `main` prints it when it finds too many arguments or an unknown option (line 238). This line: the script is the acceptance test of a build of the runner program `bwx10`. It accepts or rejects a build. Its input is the machine code of every kernel, as text. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 3 | `"Fixed setup": reject a build whose acceptance listing differs).` | Documentation text: the design note `tackle-8mb.md`, section "Fixed setup", gives the rule that a build is rejected when its acceptance listing differs. |
| 5 | `Runs on the development machine, on the listing.txt and offsets.tsv that` | Documentation text: the script runs on the development machine, not on CRB (the Arm reference server under test). It reads the files `listing.txt` and `offsets.tsv` that ... |
| 6 | `build10.sh wrote on CRB.` | Documentation text: ... the build script `build10.sh` wrote on CRB. |
| 7 | `Usage: check_listing10.py [listing.txt [offsets.tsv]]` | Documentation text: the usage. Both file arguments are optional. Line 240 and line 241 set the defaults. |
| 8 | `           [--ref-listing F] [--ref-offsets F] [--binary bwx10] [--ref-binary bwx8] [--skip-new]` | Documentation text: the five options. `--ref-listing` and `--ref-offsets` name other reference files. `--binary` and `--ref-binary` give the names of the two binaries as they stand in the title lines of the listings. The defaults are `bwx10` and `bwx8`. `--skip-new` leaves out part 2 (line 58). |
| 10 | `The reference is the accepted build of bwx8 (crb-build-1 of the folder` | Documentation text: the reference is the accepted build of bwx8, the runner version before. It is the folder `crb-build-1` in the folder ... |
| 11 | `bwx8-2026-11-14), saved in ref-bwx8/listing.txt and ref-bwx8/offsets.tsv` | Documentation text: ... `bwx8-2026-11-14`. Its two files are saved as `ref-bwx8/listing.txt` and `ref-bwx8/offsets.tsv` ... The code repo does not hold the folder `ref-bwx8`. The project folder of the script holds it. Its two files are equal, byte for byte, to the files in the build record of bwx8 [Ref3]. |
| 12 | `beside this script, binary "bwx8".` | Documentation text: ... beside this script. The name of the binary in these files is `bwx8`. |

### Documentation text: part 1, the kernels of the reference (lines 14 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 14 | `Part 1, the 21 kernels of the reference binary. The rules are the rules of` | Documentation text: part 1 covers the 21 kernels of the reference binary. These are the kernels that bwx8 already had. The rules are the rules of ... |
| 15 | `check_listing8.py, unchanged. For every kernel of the reference:` | Documentation text: ... `check_listing8.py`, the script of the same kind in the folder of bwx8, unchanged. Four rules follow. They hold for every kernel of the reference. A `diff` of this task found the code of part 1 equal in both scripts, apart from one line (line 302) [Ref6]. |
| 16 | ` 1. the new listing has the kernel, and the function has a loop;` | Documentation text: rule 1 for a kernel of the reference. The new listing has the kernel, and the function has a loop. Lines 266 to 270 implement it. |
| 17 | ` 2. the whole function text equals the reference text, apart from addresses;` | Documentation text: rule 2 for a kernel of the reference. The whole function text equals the reference text, apart from addresses. Lines 272 to 275 implement it. |
| 18 | ` 3. the loop start modulo 64 equals the reference value. Both are computed` | Documentation text: rule 3 for a kernel of the reference. The loop start modulo 64 equals the reference value (lines 284 to 285). The loop start modulo 64 is the remainder of the loop start address divided by 64. Both values are computed ... |
| 19 | `    from the listings;` | Documentation text: ... from the listings. |
| 20 | ` 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as` | Documentation text: rule 4 for a kernel of the reference. The row of the kernel in the new `offsets.tsv` gives the same `loop_mod64` as ... Lines 286 to 289 implement it. |
| 21 | `    the new listing and as the row of the reference offsets.tsv.` | Documentation text: ... the new listing and as the row of the reference `offsets.tsv`. |
| 23 | `What "apart from addresses" means here:` | Documentation text: lines 24 to 38 define how two functions at different addresses are compared. The function `whole` (line 137) implements it. |
| 24 | ` - an instruction address is not compared;` | Documentation text: an instruction address is not compared. |
| 25 | ` - a branch target inside the function is compared as its distance from the` | Documentation text: a branch target inside the function is compared as its distance from the ... |
| 26 | `   function start;` | Documentation text: ... function start. |
| 27 | ` - a target outside the function (the stub of bl, the page of a single adrp)` | Documentation text: a target outside the function ... The text names two cases: the stub that a `bl` calls, and the page of a single `adrp`. `bl` is the call instruction. The listing of the CRB build has 2 `bl` instructions, one in `oldread` and one in `oldread2`. Both call `__stack_chk_fail@plt`, the function for a failed stack guard [Ref2]. |
| 28 | `   is compared by its symbol name, not by its address;` | Documentation text: ... is compared by its symbol name, not by its address. The code keeps all that stands in the angle brackets (line 148). When the listing shows a symbol name plus an offset there, the offset is compared too. |
| 29 | ` - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from` | Documentation text: the pair `adrp xN, page` and `ldr xN, [xN, #offset]` loads a pointer from ... `adrp` puts the address of a 4096-byte page into a register. The `ldr` after it loads a pointer from that page. |
| 30 | `   the table of global addresses of the binary. In the reference only the` | Documentation text: ... the table of global addresses of the binary. This table holds addresses of global objects of the binary. In the reference only the ... |
| 31 | `   load of the stack-guard pointer has this form. Page and offset are the` | Documentation text: ... load of the stack-guard pointer has this form. The page and the offset are the ... |
| 32 | `   place of the pointer in that table. The linker sets them, so they are not` | Documentation text: ... place of the pointer in that table. The linker sets them. So they are not ... |
| 33 | `   compared with the reference. The pair is accepted only where the reference` | Documentation text: ... compared with the reference. The pair is accepted only where the reference ... |
| 34 | `   has it, because the rest of the text must be equal. The listing does not` | Documentation text: ... has it: the rest of the text must be equal. The listing does not ... |
| 35 | `   name the pointer. So this is checked: the new listing must not use more` | Documentation text: ... name the pointer. So one more check is made: the new listing must not use more ... |
| 36 | `   places of the table than the reference, per function and over all` | Documentation text: ... places of the table than the reference, per function (lines 279 to 281) and over all ... |
| 37 | `   kernels. The reference uses one place. A row whose offset differs from the` | Documentation text: ... kernels (lines 298 to 301). The reference uses one place. A row whose offset differs from the ... |
| 38 | `   reference prints "NOTE: got_offset_differs" in place of "ok": read it.` | Documentation text: ... reference prints `NOTE: got_offset_differs` in place of `ok` (lines 282 to 283). The text asks the reader to read such a row. |
| 39 | `The loop of a function is the range from the target of its first backward` | Documentation text: the definition of the loop. The loop of a function is the range from the target of its first backward ... A backward branch is a branch whose target address is lower than its own address. |
| 40 | `branch to that branch.` | Documentation text: ... branch to that branch. The function `loop_start` (line 127) finds the first address of the loop. |

### Documentation text: part 2 (the new kernels), `--skip-new` and the exit status (lines 42 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `Part 2, the 5 kernels of round 3 (read_pf256, read_pf512, read_pf1024,` | Documentation text: part 2 covers the 5 kernels of round 3. This line names `read_pf256`, `read_pf512` and `read_pf1024`. Round 3 is the set of additions that made bwx10 out of bwx8. It is not a round of a kernel sequence. The function `new_problems` (line 164) implements the five rules of part 2. |
| 43 | `read_pf2048, read_1pl). The reference does not have them. All 5 must be in` | Documentation text: ... and the other two kernels, `read_pf2048` and `read_1pl`. The reference does not have these five kernels. All 5 must be in ... |
| 44 | `the new listing. For each one:` | Documentation text: ... the new listing (lines 318 to 321). Five rules follow for each one. |
| 45 | ` 1. the function has exactly one backward branch, and no other branch or call;` | Documentation text: rule 1 of part 2. The function has exactly one backward branch, and no other branch or call. Lines 168 to 179 implement it. |
| 46 | ` 2. the instructions of the loop equal the expected list (NEW_LOOP below),` | Documentation text: rule 2 of part 2. The instructions of the loop equal the expected list, which is the entry of the kernel in the table `NEW_LOOP` (lines 77 to 87) ... Lines 180 to 188 implement the rule. |
| 47 | `    with every operand, and the loop ends with b.cc (the same instruction as` | Documentation text: ... with every operand. The loop ends with `b.cc` ... `b.cc` and `b.lo` are two names of one branch instruction. After `cmp x0, x1` it jumps when `x0` is below `x1` (unsigned compare). |
| 48 | `    b.lo) to the loop start;` | Documentation text: ... to the loop start (lines 187 to 188). |
| 49 | ` 3. every instruction before the loop is the computation of the end pointer` | Documentation text: rule 3 of part 2. Every instruction before the loop is the computation of the end pointer ... Lines 189 to 206 implement the rule. |
| 50 | `    or a store of d registers to the stack; every instruction after the loop` | Documentation text: ... or a store of d registers to the stack. Every instruction after the loop ... |
| 51 | `    is a load of d registers from the stack, and the last one is ret;` | Documentation text: ... is a load of d registers from the stack, and the last one is `ret`, the return to the caller. |
| 52 | ` 4. every register from v8 to v15 that the loop uses is stored before the` | Documentation text: rule 4 of part 2. Every register from v8 to v15 that the loop uses is stored before the ... Lines 207 to 212 implement it. |
| 53 | `    loop and loaded after it (d8-d15 are callee-saved);` | Documentation text: ... loop and loaded after it. The text gives the reason: d8 to d15 are callee-saved. A callee-saved register must hold the same value when the function returns as when it was called. So a kernel whose loop loads into q8 to q15 must store d8 to d15 before the loop and reload them after it. |
| 54 | ` 5. the loop start modulo 64 equals the loop start modulo 64 of asmread in` | Documentation text: rule 5 of part 2. The loop start modulo 64 equals the loop start modulo 64 of `asmread` in ... Lines 213 to 218 implement the rule. The script holds no fixed number for this position. |
| 55 | `    the same listing, and the row in offsets.tsv gives the same value.` | Documentation text: ... the same listing. And the row of the kernel in `offsets.tsv` gives the same value. |
| 56 | `Any other kernel that the reference lacks is a failure.` | Documentation text: any other kernel that the reference lacks is a failure. Lines 302 to 305 implement it. |
| 58 | `--skip-new leaves out part 2. It is only for a build on a machine that is not` | Documentation text: the option `--skip-new` leaves out part 2. It is only for a build on a machine that is not ... |
| 59 | `AArch64, where the new kernels are plain C stand-in loops. The last line then` | Documentation text: ... AArch64 (the 64-bit Arm instruction set). There the new kernels are plain C stand-in loops. The last line of the output then ... |
| 60 | `says that the new kernels were NOT CHECKED.` | Documentation text: ... says that the new kernels were `NOT CHECKED` (line 310). |
| 61 | `Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.` | Documentation text: the exit statuses. 0: all checks passed. 1: a check failed. 2: a file could not be used. The code also returns 2 for wrong arguments (line 234, line 239). The exit status is the return value of `main` (line 336). |
| 62 | `"""` | Ends the documentation text. |

### Imports and constants (lines 63 to 70)

| Line | Source | Explanation |
|---:|---|---|
| 63 | `import os` | Loads the module `os`. The script uses it for file paths. |
| 64 | `import re` | Loads the module `re` for regular expressions. |
| 65 | `import sys` | Loads the module `sys` for the arguments and the exit status. |
| 67 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. |
| 68 | `REF_DIR = os.path.join(HERE, "ref-bwx8")` | `REF_DIR`: its subfolder `ref-bwx8`, the place of the reference files. The code repo does not hold this folder (see the row of line 11). |
| 69 | `TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")` | `TARGET`: a compiled pattern for a branch target at the end of an instruction: a hexadecimal address, a space and a name in angle brackets. Group 1 holds the address. The page operand of an `adrp` instruction has the same form. The pattern matches it too. Two examples from the listing of the CRB build (`listing.txt`): the branch target `41a4 <k_read+0x4>` and the page operand `2f000 <__FRAME_END__+0x1bbf8>` [Ref2]. |

### Expected loop of the new kernels, table `NEW_LOOP`, patterns `SAVE`, `RESTORE`, `BRANCH` (lines 71 to 93)

| Line | Source | Explanation |
|---:|---|---|
| 71 | `# The loop of each new kernel, as objdump prints it (one space between the` | Comment: the lists below hold the loop of each new kernel in the form in which `objdump` prints it, with one space between the ... `objdump` is the tool that prints the machine code of a binary as text. The function `sections` (line 94) brings the instruction text of a listing into the same form. |
| 72 | `# fields). x0 is the pointer and x1 is the end, as in every asm kernel of the` | Comment: ... fields. The register `x0` is the pointer and `x1` is the end address, as in every asm kernel of the ... |
| 73 | `# reference. The loop branch stands after these instructions.` | Comment: ... reference. The loop branch stands after these instructions. It is not in the lists. |
| 74 | `LDP8 = ["ldp q0, q1, [x0]", "ldp q2, q3, [x0, #32]", "ldp q4, q5, [x0, #64]", "ldp q6, q7, [x0, #96]",` | `LDP8`: the 8 `ldp` instructions of `asmread`. Each one loads two 16-byte registers. Together they load q0 to q15 from the 256 bytes at the pointer `x0`. This line holds the first four, for the offsets 0, 32, 64 and 96 bytes. |
| 75 | `        "ldp q8, q9, [x0, #128]", "ldp q10, q11, [x0, #160]", "ldp q12, q13, [x0, #192]", "ldp q14, q15, [x0, #224]"]` | Continues the list of line 74: the other four `ldp`, for the offsets 128, 160, 192 and 224 bytes. |
| 76 | `STEP = ["add x0, x0, #0x100", "cmp x0, x1"]` | `STEP`: add 256 bytes (`#0x100`) to `x0`, then compare `x0` with the end pointer `x1`. |
| 77 | `NEW_LOOP = {` | `NEW_LOOP`: the table of the new kernels. A key is a kernel name. Its value is the expected list of the loop instructions without the loop branch. Lines 78 to 86 hold the five entries. |
| 78 | `    "read_pf256": LDP8 + ["prfm pldl1keep, [x0, #256]", "prfm pldl1keep, [x0, #320]",` | `read_pf256`: the 8 `ldp` of `LDP8`, then four `prfm pldl1keep` instructions. `prfm` is a prefetch instruction: it asks for a cache line and loads no data. By a comment in the runner source, `pldl1keep` asks for the line in the first-level data cache, for a later load. This line holds the prefetches for the addresses 256 and 320 bytes after the pointer `x0` ... |
| 79 | `                          "prfm pldl1keep, [x0, #384]", "prfm pldl1keep, [x0, #448]"] + STEP,` | ... and for 384 and 448 bytes after `x0`. The four addresses are the four 64 B lines of the 256 bytes that the next loop pass loads. In the last pass of a kernel call they lie past the end of the range. `STEP` ends the list. |
| 80 | `    "read_pf512": LDP8 + ["prfm pldl1keep, [x0, #512]", "prfm pldl1keep, [x0, #576]",` | `read_pf512`: the same list with other prefetch addresses: 512 and 576 bytes after `x0` ... |
| 81 | `                          "prfm pldl1keep, [x0, #640]", "prfm pldl1keep, [x0, #704]"] + STEP,` | ... and 640 and 704 bytes. These are the four lines of the block that the loop loads 2 passes later. |
| 82 | `    "read_pf1024": LDP8 + ["prfm pldl1keep, [x0, #1024]", "prfm pldl1keep, [x0, #1088]",` | `read_pf1024`: the prefetch addresses are 1024 and 1088 bytes after `x0` ... |
| 83 | `                           "prfm pldl1keep, [x0, #1152]", "prfm pldl1keep, [x0, #1216]"] + STEP,` | ... and 1152 and 1216 bytes. These are the four lines of the block that the loop loads 4 passes later. |
| 84 | `    "read_pf2048": LDP8 + ["prfm pldl1keep, [x0, #2048]", "prfm pldl1keep, [x0, #2112]",` | `read_pf2048`: the prefetch addresses are 2048 and 2112 bytes after `x0` ... |
| 85 | `                           "prfm pldl1keep, [x0, #2176]", "prfm pldl1keep, [x0, #2240]"] + STEP,` | ... and 2176 and 2240 bytes. These are the four lines of the block that the loop loads 8 passes later. |
| 86 | `    "read_1pl": ["ldr q0, [x0]", "ldr q1, [x0, #64]", "ldr q2, [x0, #128]", "ldr q3, [x0, #192]"] + STEP,` | `read_1pl`: four `ldr` instructions, then `STEP`. Each `ldr` loads one 16-byte register (q0 to q3). The addresses are 0, 64, 128 and 192 bytes after `x0`. So one loop pass loads the first 16 B of each of four 64 B lines: 64 of the 256 bytes that it steps over. The list has no `ldp` and no prefetch. |
| 87 | `}` | Ends the table `NEW_LOOP`. |
| 88 | `END_POINTER = "add x1, x0, x1, lsl #3"` | `END_POINTER`: the instruction before the loop that computes the end address: pointer plus 8 times the second argument. By the runner source, the second argument of a kernel is a count of 8-byte words. `lsl #3` shifts it left by 3 bits. |
| 89 | `SAVE = re.compile(r"(?:stp d(\d+), d(\d+)\|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")` | `SAVE`: a compiled pattern for a store of one or two d registers to the stack: `stp` with two d registers or `str` with one, then `[sp]` with or without an offset, with or without `!`. Example: `stp d8, d9, [sp, #-64]!`. The groups hold the register numbers. |
| 90 | `RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)\|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")` | `RESTORE`: a compiled pattern for a load of one or two d registers from the stack: `ldp` with two d registers or `ldr` with one. Example: `ldp d8, d9, [sp], #64`. The groups hold the register numbers. |
| 91 | `BRANCH = re.compile(r"(b\|bl\|br\|blr\|b\.[a-z]+\|cbn?z\|tbn?z)\b")` | `BRANCH`: a compiled pattern for the name of a branch or call instruction at the start of the text: `b`, `bl`, `br`, `blr`, a conditional `b.` with letters, `cbz`, `cbnz`, `tbz`, `tbnz`. It does not match `ret`. |

### Functions `sections` and `offsets`: read the two kinds of input file (lines 94 to 126)

| Line | Source | Explanation |
|---:|---|---|
| 94 | `def sections(path):` | Starts the function `sections`. It reads a listing file. |
| 95 | `    """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""` | Documentation text of `sections`: it returns a dictionary. A key is the pair (binary, kernel). Its value is the list of (address, instruction text) of that kernel function, in file order. Example: in the listing of the CRB build (`listing.txt`) the first block starts with the title line `=== bwx10 read ===`. The label line `00000000000041a0 <k_read>:` follows it. It is no instruction line and is skipped (line 103) [Ref2]. |
| 96 | `    out, cur = {}, None` | `out`: the dictionary. `cur`: the list of the block that is read now. It is `None` outside a block. |
| 97 | `    with open(path) as f:` | Opens the file. |
| 98 | `        for line in f:` | Loop over the lines of the file. |
| 99 | `            m = re.match(r"=== (\S+) (\S+) ===", line)` | Tests whether the line is a title line of the form `=== BINARY KERNEL ===`. Group 1 holds the name of the binary, group 2 the name of the kernel. |
| 100 | `            if m:` | A title line starts the block of one kernel. |
| 101 | `                cur = out.setdefault((m.group(1), m.group(2)), [])` | `cur` becomes the list for this pair. `setdefault` creates an empty list when the pair is new. |
| 102 | `                continue` | Goes to the next line. |
| 103 | `            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)` | Tests whether the line is an instruction line: spaces, a hexadecimal address (group 1), a colon, spaces or tabs, and the instruction (group 2). The label line of a function has no colon directly after its address. So it does not match and is skipped. |
| 104 | `            if m and cur is not None:` | Only inside a block ... |
| 105 | `                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()` | ... the text is cleaned. The `objdump` comment after `//` is cut off. Each run of spaces and tabs becomes one space. |
| 106 | `                cur.append((int(m.group(1), 16), text))` | Appends the pair of the address as a number and the cleaned text to the block. |
| 107 | `            elif line.startswith("##"):` | A line that starts with `##` ... |
| 108 | `                cur = None` | ... ends the block that is read now. |
| 109 | `    return out` | Returns the dictionary. |
| 112 | `def offsets(path):` | Starts the function `offsets`. It reads a file `offsets.tsv`. |
| 113 | `    """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""` | Documentation text of `offsets`: it returns a dictionary from (binary, kernel) to the text of the column `loop_mod64`. |
| 114 | `    out = {}` | `out`: the dictionary. |
| 115 | `    with open(path) as f:` | Opens the file. |
| 116 | `        head = f.readline().rstrip("\n").split("\t")` | `head`: the fields of the first line, split at the tab characters. |
| 117 | `        if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:` | The first line must hold exactly the 6 column names. |
| 118 | `            raise ValueError("%s: unexpected header line" % path)` | If not, the function raises `ValueError` with the text `unexpected header line`. `main` then ends with exit status 2 (lines 245 to 247). |
| 119 | `        for line in f:` | Loop over the other lines. |
| 120 | `            p = line.rstrip("\n").split("\t")` | `p`: the fields of the line. |
| 121 | `            if len(p) != 6:` | Every row must have 6 fields. |
| 122 | `                raise ValueError("%s: a row with %d fields" % (path, len(p)))` | If not, the function raises `ValueError`. |
| 123 | `            out[(p[0], p[1])] = p[5]` | Stores column 6 under the pair of column 1 and column 2. The script uses columns 1, 2 and 6 only. It ignores the columns `function`, `start` and `loop_start`. |
| 124 | `    return out` | Returns the dictionary. |

### Functions `loop_start`, `whole` and `numbers` (lines 127 to 163)

| Line | Source | Explanation |
|---:|---|---|
| 127 | `def loop_start(insns):` | Starts the function `loop_start`. `insns` is the list of (address, text) of one function. |
| 128 | `    """address of the loop start: the target of the first backward branch into the function, or None"""` | Documentation text of `loop_start`: it returns the address of the loop start. That is the target of the first backward branch into the function. Without such a branch the result is `None`. |
| 129 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 130 | `    for addr, text in insns:` | Goes through the instructions in order. |
| 131 | `        m = TARGET.search(text)` | Looks for a branch target at the end of the instruction text. |
| 132 | `        if m and first <= int(m.group(1), 16) < addr:` | The branch counts when its target lies inside the function and before the branch itself (`first <= target < addr`). |
| 133 | `            return int(m.group(1), 16)` | Returns that target. This address is the loop start. `main` computes a loop start modulo 64 as `loop_start(...) % 64`. |
| 134 | `    return None` | Returns `None` when the function has no such branch. |
| 137 | `def whole(insns):` | Starts the function `whole`. It returns the text of a function in a form that does not depend on the addresses. |
| 138 | `    """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""` | Documentation text of `whole`: it returns two lists. The first is the function text without addresses (`out`). The second holds the places (page, offset) of the pointer loads from the table of global addresses (`got`). Two examples with text of the listing of the CRB build (`listing.txt`): `b.hi 41a4 <k_read+0x4>` becomes `b.hi +0x4` (line 145), and the call of `__stack_chk_fail@plt` becomes `bl (outside <__stack_chk_fail@plt>)` (line 148) [Ref2]. |
| 139 | `    first, last, out, got = insns[0][0], insns[-1][0], [], []` | `first` and `last`: the addresses of the first and the last instruction. `out` and `got`: the two result lists. |
| 140 | `    adrp_reg = adrp_page = None` | `adrp_reg` and `adrp_page`: the register and the page of an `adrp` instruction, kept for the next instruction only. |
| 141 | `    for _, text in insns:` | Loop over the instruction texts. |
| 142 | `        m = TARGET.search(text)` | Looks for a target at the end of the text. |
| 143 | `        page = None` | `page`: the address text of a target outside the function. `None` at first. |
| 144 | `        if m and first <= int(m.group(1), 16) <= last:` | A target inside the function ... |
| 145 | `            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... becomes its distance from the function start, written as `+0x` and hexadecimal digits. |
| 146 | `        elif m:` | A target outside the function: |
| 147 | `            page = m.group(1)` | `page` keeps the address text for line 155. |
| 148 | `            text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]` | The text becomes `(outside NAME)`. NAME is all that stands in the angle brackets, with the brackets: a symbol name, or a symbol name plus an offset. It is kept, and the address before it is removed. |
| 149 | `        load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)` | `load`: tests whether the whole text is a load of the form `ldr xA, [xB, #N]`. The groups hold the two registers and the offset. |
| 150 | `        if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:` | The pair counts when the instruction before was an `adrp` with a page, and both registers of the load are the register of that `adrp`. |
| 151 | `            got.append((adrp_page, load.group(3)))` | Records the place (page, offset) in `got`. |
| 152 | `            out[-1] = "adrp %s, (table page)" % adrp_reg` | Replaces the text of the `adrp` before by the fixed text `adrp xN, (table page)`. |
| 153 | `            text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)` | Replaces the text of the load by the fixed text `ldr xN, [xN, #(table)]`. So the page and the offset are not part of the text comparison. In the listing of the CRB build and in the reference listing only `oldread` and `oldread2` have this pair. Each has it twice, with the page address `2f000` (hexadecimal) and the offset 4072 bytes [Ref2] [Ref3]. |
| 154 | `        m = re.match(r"adrp (x\d+), ", text)` | Tests whether this instruction is an `adrp`. Group 1 holds its register. |
| 155 | `        adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)` | Remembers the register and the page of an `adrp` with a page outside the function. Every other instruction clears both values. |
| 156 | `        out.append(text)` | Appends the text to `out`. |
| 157 | `    return out, got` | Returns the two lists. |
| 160 | `def numbers(match):` | Starts the function `numbers`. `match` is one match of `SAVE` or of `RESTORE`. |
| 161 | `    return {int(g) for g in match.groups() if g is not None}` | Returns the set of the register numbers that the match captured. A group without a value is left out. |

### Function `new_problems`: the rules of part 2 for one new kernel (lines 164 to 221)

| Line | Source | Explanation |
|---:|---|---|
| 164 | `def new_problems(kernel, insns, want_mod, off_row):` | Starts the function `new_problems`. It applies the rules of part 2 to one new kernel and returns a list of problem texts. An empty list says that the kernel passed. `insns` is the list of (address, text) of the kernel function. `off_row` is the value of the kernel in `offsets.tsv`, or `None`. |
| 165 | `    """Part 2 for one new kernel. want_mod: the loop start modulo 64 of asmread in the same listing, or None."""` | Documentation text of `new_problems`: part 2 for one new kernel. `want_mod` is the loop start modulo 64 of `asmread` in the same listing, or `None`. |
| 166 | `    p = []` | `p`: the list of problem texts, empty at first. |
| 167 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 168 | `    back = [i for i, (addr, text) in enumerate(insns)` | `back`: the positions of every instruction that has a branch target ... |
| 169 | `            if TARGET.search(text) and first <= int(TARGET.search(text).group(1), 16) <= addr]` | ... inside the function, at or before its own address. These are the backward branches. |
| 170 | `    if len(back) != 1:` | Exactly 1 backward branch is required. |
| 171 | `        return ["%d backward branches, 1 expected" % len(back)]` | If not, the function returns immediately with this one problem. |
| 172 | `    end = back[0]` | `end`: the position of that branch, the loop branch. |
| 173 | `    loop = int(TARGET.search(insns[end][1]).group(1), 16)` | `loop`: its target address, the loop start. |
| 174 | `    begin = next((i for i, (addr, _) in enumerate(insns) if addr == loop), None)` | `begin`: the position of the instruction at that address. `None` when no instruction has that address. |
| 175 | `    if begin is None:` | If no instruction has that address ... |
| 176 | `        return ["the loop branch goes to %x, which is not the address of an instruction" % loop]` | ... the function returns with one problem. |
| 177 | `    others = [text for i, (_, text) in enumerate(insns) if i != end and BRANCH.match(text)]` | Rule 1: `others` lists every other instruction that `BRANCH` matches. The `ret` at the end is not matched. |
| 178 | `    if others:` | If there is one ... |
| 179 | `        p.append("a branch or call beside the loop branch: %s" % "; ".join(others))` | ... it is a problem: a branch or call beside the loop branch. |
| 180 | `    body, want = [text for _, text in insns[begin:end]], NEW_LOOP[kernel]` | Rule 2. `body`: the instructions of the loop, from the loop start to the instruction before the loop branch. `want`: the expected list of this kernel from the table `NEW_LOOP`. |
| 181 | `    if body != want:` | The two lists `body` and `want` must be equal: the same count, the same order, and every instruction text equal with every operand. The next lines only write the messages for the case that they differ. |
| 182 | `        for i in range(max(len(body), len(want))):` | For the messages, a loop over the positions of the longer of the two lists ... |
| 183 | `            g = body[i] if i < len(body) else "(none)"` | ... takes the instruction of the listing at this position (`g`), or `(none)` past the end of `body` ... |
| 184 | `            w = want[i] if i < len(want) else "(none)"` | ... and the expected instruction (`w`), or `(none)` past the end of `want`. |
| 185 | `            if g != w:` | When the two texts differ ... |
| 186 | `                p.append("loop instruction %d is '%s', expected '%s'" % (i, g, w))` | ... a problem gives the position (counted from 0), the instruction found and the instruction expected. Every position that differs adds one problem. |
| 187 | `    if not re.fullmatch(r"b\.(cc\|lo) %x <k_%s\+0x%x>" % (loop, re.escape(kernel), loop - first), insns[end][1]):` | The loop branch must be `b.cc` or `b.lo` to the loop start. The whole text must be the name, the loop address, and in angle brackets `k_` plus the kernel name plus the distance of the loop start from the function start. `re.escape` makes the kernel name plain text for the pattern. |
| 188 | `        p.append("the loop branch is '%s', expected b.cc (b.lo) to the loop start" % insns[end][1])` | If not, a problem shows the text of the loop branch. |
| 189 | `    head, tail = [text for _, text in insns[:begin]], [text for _, text in insns[end + 1:]]` | Rule 3. `head`: the instructions before the loop start. `tail`: the instructions after the loop branch. |
| 190 | `    saved, restored = set(), set()` | `saved` and `restored`: the sets of the numbers of the d registers that the function stores before the loop and loads after it. Both are empty at first. |
| 191 | `    for text in head:` | Loop over the instructions before the loop. |
| 192 | `        m = SAVE.fullmatch(text)` | Tests whether the whole text is a store of d registers to the stack (`SAVE`). |
| 193 | `        if m:` | If it is ... |
| 194 | `            saved \|= numbers(m)` | ... its register numbers are added to `saved`. |
| 195 | `        elif text != END_POINTER:` | Every other instruction before the loop must be the end-pointer instruction (`END_POINTER`). |
| 196 | `            p.append("before the loop: '%s' is not the end pointer and not a store of d registers to the stack" % text)` | If it is not, a problem shows the instruction and says that it is not the end pointer and not a store of d registers to the stack. |
| 197 | `    if head.count(END_POINTER) != 1:` | The end-pointer instruction must stand exactly once before the loop. |
| 198 | `        p.append("before the loop: '%s' stands %d times, 1 expected" % (END_POINTER, head.count(END_POINTER)))` | If not, a problem gives the instruction and the number of times that it stands there. |
| 199 | `    if not tail or tail[-1] != "ret":` | After the loop: the last instruction must be `ret`. |
| 200 | `        p.append("the function does not end with ret")` | If not, a problem says that the function does not end with `ret`. |
| 201 | `    for text in tail[:-1]:` | Loop over the instructions between the loop branch and the last instruction. |
| 202 | `        m = RESTORE.fullmatch(text)` | Tests whether the whole text is a load of d registers from the stack (`RESTORE`). |
| 203 | `        if m:` | If it is ... |
| 204 | `            restored \|= numbers(m)` | ... its register numbers are added to `restored`. |
| 205 | `        else:` | Every other instruction ... |
| 206 | `            p.append("after the loop: '%s' is not a load of d registers from the stack" % text)` | ... is a problem. |
| 207 | `    used = {int(n) for text in body for n in re.findall(r"\b[qvd](\d+)\b", text) if 8 <= int(n) <= 15}` | Rule 4. `used`: the register numbers from 8 to 15 that the loop names as a q, v or d register. The pattern takes the number after one of the letters `q`, `v` or `d`. |
| 208 | `    if used - saved or used - restored:` | Every register in `used` must be in `saved` and in `restored`. |
| 209 | `        p.append("the loop uses v%s; not stored before the loop: %s; not loaded after it: %s" %` | If not, a problem lists the used registers ... |
| 210 | `                 (",".join(str(n) for n in sorted(used)), sorted(used - saved) or "none", sorted(used - restored) or "none"))` | ... those that are not stored before the loop, and those that are not loaded after it. |
| 211 | `    if saved != restored:` | The stored set and the reloaded set must be equal. |
| 212 | `        p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))` | If not, a problem shows both sets. The script compares register numbers only. It does not compare the stack offset of a store with the stack offset of its reload. |
| 213 | `    if want_mod is None:` | Rule 5, the place of the loop. `loop % 64` is the loop start modulo 64 of this kernel. `want_mod` is the loop start modulo 64 of `asmread` in the same listing. It is `None` when the listing has no block of `asmread`, or when that function has no loop. |
| 214 | `        p.append("asmread has no loop in this listing, so the loop offset cannot be compared")` | Then a problem says that `asmread` has no loop in this listing, and that the loop offset cannot be compared. |
| 215 | `    elif loop % 64 != want_mod:` | `loop % 64` must equal `want_mod`. |
| 216 | `        p.append("loop offset modulo 64 is %d, asmread has %d" % (loop % 64, want_mod))` | If not, a problem gives the value of this kernel and the value of `asmread`. |
| 217 | `    if off_row != str(loop % 64):` | The row of the kernel in `offsets.tsv` must hold the same number as text. |
| 218 | `        p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))` | If not, a problem gives both values. A missing row is written as `no row`. |
| 219 | `    return p` | Returns the list of problems. |

### Function `main`: arguments and input files (lines 222 to 259)

| Line | Source | Explanation |
|---:|---|---|
| 222 | `def main():` | Starts the function `main`. Its return value becomes the exit status (line 336). |
| 223 | `    args = sys.argv[1:]` | `args`: the arguments of the command line without the script name. |
| 224 | `    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),` | `opt`: the defaults of the 4 options that take a value. The reference files are `listing.txt` and `offsets.tsv` in the folder `REF_DIR`. |
| 225 | `           "--binary": "bwx10", "--ref-binary": "bwx8"}` | Continues the dictionary of line 224: the default names of the two binaries, `bwx10` for the new binary and `bwx8` for the reference. |
| 226 | `    skip_new = "--skip-new" in args` | `skip_new`: true when the arguments hold `--skip-new`. This option is a flag without a value. |
| 227 | `    if skip_new:` | When the flag is present ... |
| 228 | `        args.remove("--skip-new")` | ... it is removed from the list. |
| 229 | `    for name in opt:` | Loop over the 4 option names. |
| 230 | `        if name in args:` | An option that is present ... |
| 231 | `            i = args.index(name)` | ... stands at position `i` ... |
| 232 | `            if i + 1 >= len(args):` | ... and needs one more argument after it. |
| 233 | `                print("%s needs a value" % name)` | Without it the script prints that the option needs a value ... |
| 234 | `                return 2` | ... and ends with exit status 2. |
| 235 | `            opt[name] = args[i + 1]` | The next argument becomes the value of the option. |
| 236 | `            del args[i:i + 2]` | Both are removed from the list. |
| 237 | `    if len(args) > 2 or any(a.startswith("--") for a in args):` | More than 2 remaining arguments, or a remaining argument that starts with `--` ... |
| 238 | `        print(__doc__)` | ... print the documentation text ... |
| 239 | `        return 2` | ... and the script ends with exit status 2. |
| 240 | `    listing = args[0] if args else os.path.join(HERE, "listing.txt")` | `listing`: the first remaining argument, or `listing.txt` in the folder of the script. |
| 241 | `    offs = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")` | `offs`: the second remaining argument, or `offsets.tsv` in the folder of the listing. |
| 242 | `    try:` | Starts the block in which a file error is caught. |
| 243 | `        ref, got = sections(opt["--ref-listing"]), sections(listing)` | Reads the reference listing into `ref` and the new listing into `got`. |
| 244 | `        ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)` | Reads the reference `offsets.tsv` into `ref_off` and the new `offsets.tsv` into `got_off`. |
| 245 | `    except (OSError, ValueError) as e:` | A file that cannot be opened (`OSError`), or an offsets table with a wrong form (`ValueError`) ... |
| 246 | `        print("cannot use: %s" % e)` | ... prints `cannot use:` and the reason ... |
| 247 | `        return 2` | ... and ends the script with exit status 2. |
| 248 | `    b, rb = opt["--binary"], opt["--ref-binary"]` | `b`: the name of the new binary. `rb`: the name of the reference binary. |
| 249 | `    kernels = [k for (bb, k) in ref if bb == rb]` | `kernels`: the list of the kernel names of the reference binary, in the order of the reference listing. |
| 250 | `    if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):` | One more case that ends with exit status 2: the reference listing has no kernel of the reference binary, or a reference kernel has no instructions or no loop. |
| 251 | `        print("the reference listing has no usable block of binary %s" % rb)` | Prints a message that names the reference binary ... |
| 252 | `        return 2` | ... and ends with exit status 2. |
| 253 | `    if any(k in NEW_LOOP for k in kernels):` | One more case: the reference listing holds a new kernel, which is a key of `NEW_LOOP`. |
| 254 | `        print("the reference listing holds a kernel of round 3: it is not a listing of %s" % rb)` | Prints the message that the reference listing holds a kernel of round 3 and is therefore not a listing of the reference binary. |
| 255 | `        return 2` | Ends with exit status 2. |
| 256 | `    if not any(bb == b for bb, _ in got):` | One more case: the new listing has no block of the new binary. |
| 257 | `        print("no '=== %s kernel ===' block in %s" % (b, listing))` | Prints a message that names the new binary and the listing file ... |
| 258 | `        return 2` | ... and ends with exit status 2. |

### Function `main`: part 1, one output row per kernel of the reference (lines 260 to 306)

| Line | Source | Explanation |
|---:|---|---|
| 260 | `    # Part 1: the kernels of the reference (the code of check_listing8.py)` | Comment: part 1, the kernels of the reference. It is the code of `check_listing8.py`. |
| 261 | `    bad, r_places, g_places = 0, set(), set()` | `bad`: the count of failures that the summary line prints as `failed_rows`. It counts each kernel of the reference whose row fails, and 1 for each of the two checks over the whole listing that fails (lines 298 to 305). `r_places` and `g_places`: the places of the table of global addresses that the reference listing and the new listing use, over all kernels. |
| 262 | `    print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")` | Prints the column names of the output table of the reference kernels, with tabs between them: `kernel`, `start`, `loop_start`, `loop_mod64`, `ref_loop_mod64`, `text`, `result`. |
| 263 | `    for k in kernels:` | Loop over the kernels of the reference. |
| 264 | `        r_insns, insns = ref[(rb, k)], got.get((b, k), [])` | `r_insns`: the instructions of the kernel in the reference listing. `insns`: its instructions in the new listing, or an empty list when the new listing has no block for it. |
| 265 | `        r_mod = loop_start(r_insns) % 64` | `r_mod`: the loop start modulo 64 of the kernel in the reference listing. |
| 266 | `        loop = loop_start(insns) if insns else None` | Rule 1: `loop` is the loop start in the new listing. It is `None` when the block is missing or the function has no backward branch. |
| 267 | `        if loop is None:` | In that case ... |
| 268 | `            print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))` | ... the row says `FAIL: no listing or no loop`, with `NA` in the three columns of the new listing ... |
| 269 | `            bad += 1` | ... `bad` grows by 1 ... |
| 270 | `            continue` | ... and the loop goes to the next kernel. |
| 271 | `        problems, notes = [], []` | `problems` and `notes`: the texts for the result column of this kernel. |
| 272 | `        (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)` | Rule 2, the function text. `whole` (line 137) gives the text without addresses and the table places of the reference function (`r_text`, `r_got`) and of the new function (`text`, `g_got`). |
| 273 | `        same = text == r_text` | `same`: true when the two text lists are equal. They then hold the same number of instructions, and each instruction text is equal with every operand. |
| 274 | `        if not same:` | When the text is not equal ... |
| 275 | `            problems.append("function text differs from the reference")` | ... this is a problem. |
| 276 | `        else:` | When the text is equal: |
| 277 | `            r_places.update(r_got)` | The places of the reference function are added to `r_places` ... |
| 278 | `            g_places.update(g_got)` | ... and the places of the new function to `g_places`. |
| 279 | `            if len(set(g_got)) > len(set(r_got)):` | More distinct places in the new function than in the reference function ... |
| 280 | `                problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %` | ... is a problem. Its text gives the number of places of the new function ... |
| 281 | `                                (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))` | ... each place with its page and offset, and the number of the reference. |
| 282 | `            elif [o for _, o in g_got] != [o for _, o in r_got]:` | A new function with no more places than the reference, but with other offsets ... |
| 283 | `                notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))` | ... gets a note and not a failure. When the row has no failure, its result column then starts with `NOTE: got_offset_differs` in place of `ok`. |
| 284 | `        if loop % 64 != r_mod:` | Rule 3: the loop start modulo 64 of the new listing must equal the reference value. |
| 285 | `            problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))` | If not, a problem gives both values. |
| 286 | `        if ref_off.get((rb, k)) != str(r_mod):` | Rule 4: the reference `offsets.tsv` must hold the reference value for this kernel. |
| 287 | `            problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))` | If not, a problem gives the value of the table, or `no row`. |
| 288 | `        if got_off.get((b, k)) != str(loop % 64):` | The new `offsets.tsv` must hold the value of the new listing. |
| 289 | `            problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))` | If not, a problem gives both values. |
| 290 | `        print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",` | Prints the row of the kernel: the kernel name, the function start and the loop start (hexadecimal addresses), the loop start modulo 64, the reference value, `same` or `DIFFERS` ... |
| 291 | `                                             "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))` | ... and the result: `FAIL:` with the problems, or `NOTE:` with the notes, or `ok`. |
| 292 | `        if not same:` | When the text differs ... |
| 293 | `            for i in range(max(len(text), len(r_text))):` | ... a loop over the positions of the longer text ... |
| 294 | `                g = text[i] if i < len(text) else "(none)"` | ... takes the new instruction text, or `(none)` past the end ... |
| 295 | `                w = r_text[i] if i < len(r_text) else "(none)"` | ... and the reference instruction text, or `(none)` past the end. |
| 296 | `                print("    %s %-40s \| reference %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` between them. The mark `!=` stands before a line that differs. |
| 297 | `        bad += bool(problems)` | `bad` grows by 1 when the kernel has a problem. |
| 298 | `    if len(g_places) > len(r_places):` | After the loop, a check over all kernels with equal text: the new listing may not use more distinct places of the table of global addresses than the reference. |
| 299 | `        print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %` | If it does, a line that starts with `FAIL:` gives the number of places of the new listing ... |
| 300 | `              (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))` | ... the places, and the number of the reference. |
| 301 | `        bad += 1` | `bad` grows by 1. |
| 302 | `    extra = sorted(k for bb, k in got if bb == b and k not in kernels and k not in NEW_LOOP)` | `extra`: the kernels of the new binary in the new listing that are not in the reference and not new kernels (keys of `NEW_LOOP`). |
| 303 | `    if extra:` | When there is such a kernel ... |
| 304 | `        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))` | ... a line that starts with `FAIL:` names them ... |
| 305 | `        bad += 1` | ... and `bad` grows by 1. |

### Function `main`: part 2, one output row per new kernel, and the exit status (lines 307 to 336)

| Line | Source | Explanation |
|---:|---|---|
| 307 | `    # Part 2: the kernels of round 3` | Comment: part 2, the kernels of round 3. |
| 308 | `    new_bad = 0` | `new_bad`: the count of the failures of part 2. |
| 309 | `    if skip_new:` | With the option `--skip-new` ... |
| 310 | `        print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))` | ... the script prints the summary line here, with the words `new_kernels=NOT CHECKED (--skip-new)` ... |
| 311 | `        return 1 if bad else 0` | ... and returns 1 when part 1 has a failure, else 0. The new kernels are then not checked. |
| 312 | `    asm = got.get((b, "asmread"), [])` | `asm`: the instructions of `asmread` in the new listing, or an empty list. |
| 313 | `    asm_loop = loop_start(asm) if asm else None` | `asm_loop`: its loop start, or `None` when `asmread` is missing or has no loop. |
| 314 | `    want_mod = None if asm_loop is None else asm_loop % 64` | `want_mod`: the loop start modulo 64 of `asmread`, or `None`. |
| 315 | `    print("new_kernel\tstart\tloop_start\tloop_mod64\tasmread_loop_mod64\tloop\tresult")` | Prints the column names of the second output table: `new_kernel`, `start`, `loop_start`, `loop_mod64`, `asmread_loop_mod64`, `loop`, `result`. |
| 316 | `    for k in NEW_LOOP:` | Loop over the new kernels. |
| 317 | `        insns = got.get((b, k), [])` | `insns`: the instructions of the kernel in the new listing, or an empty list. |
| 318 | `        if not insns:` | Every new kernel must have a block in the new listing. If it has none ... |
| 319 | `            print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))` | ... the row says `FAIL: no listing` ... |
| 320 | `            new_bad += 1` | ... `new_bad` grows by 1 ... |
| 321 | `            continue` | ... and the loop goes to the next kernel. |
| 322 | `        problems = new_problems(k, insns, want_mod, got_off.get((b, k)))` | `new_problems` (line 164) applies the rules of part 2 and returns the problems of this kernel. |
| 323 | `        loop = loop_start(insns)` | `loop`: the loop start of the kernel, for the row. |
| 324 | `        print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,` | Prints the row of the kernel. The call goes on to line 328. This line: the kernel name, the function start and the loop start (hexadecimal addresses, `NA` without a loop) ... |
| 325 | `                                               "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,` | ... the loop start modulo 64 of the kernel, and the loop start modulo 64 of `asmread` (`NA` when `asmread` has none) ... |
| 326 | `                                               "DIFFERS" if any("loop instruction" in x or "loop branch" in x or "backward" in x` | ... and the sixth column, `loop`. It says `DIFFERS` when a problem text holds one of three phrases: `loop instruction`, `loop branch` or `backward`. These phrases stand in the problems about the loop instructions, the loop branch, another branch or call, and the number of backward branches. |
| 327 | `                                                                for x in problems) else "expected",` | Continues the test of line 326 over all problems of the kernel. Without such a problem the column says `expected`. Any other problem shows only in the result column. So a row can hold `expected` in this column and `FAIL:` in the result column, for example when the function does not end with `ret`. |
| 328 | `                                               "FAIL: " + "; ".join(problems) if problems else "ok"))` | Ends the call: the result column is `FAIL:` with the problems, or `ok`. |
| 329 | `        new_bad += bool(problems)` | `new_bad` grows by 1 when the kernel has a problem. |
| 330 | `    print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %` | Prints the summary line. It starts with `# binary=` and the name of the new binary, then `reference=` and the name of the reference binary, then the four counts that line 331 gives. The repo holds no saved output of this script for the CRB build [Ref7]. By a note of the project, the script found all 21 kernels of the reference `same` and the 5 new loops with the expected instructions for that build [Ref1]. |
| 331 | `          (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))` | Continues the call of line 330: the values of the line. They are the two binary names, the number of reference kernels, the failures of part 1, the number of new kernels and the failures of part 2. |
| 332 | `    return 1 if bad or new_bad else 0` | `main` returns 1 when a check of part 1 or of part 2 failed, and 0 when none failed. |
| 335 | `if __name__ == "__main__":` | This test is true when the file runs as a script. |
| 336 | `    sys.exit(main())` | Calls `main` and makes its return value the exit status of the script. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "`bwx10` acceptance on CRB, 2026-11-15 07:03 UTC" names the build at 07:02 UTC in `~/cache-perf/bwx10-20261115/` and its record `crb-build-1`. It says that `check_listing10.py` found 21 of 21 old kernels "same" against the `bwx8` build, that the 5 new loops have the expected instructions, and that all loop offsets are as planned, 20 modulo 64 for the new kernels.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/listing.txt`: the listing of the CRB build, with 26 blocks. The first block has the title line `=== bwx10 read ===` and the label line `00000000000041a0 <k_read>:`. `k_read` holds `b.hi 41a4 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x1bbf8>` and the offset 4072.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/`: the build record of bwx8, with `listing.txt` (21 blocks) and `offsets.tsv`. A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx10-2026-11-15/ref-bwx8/`, the reference folder beside the copy of the script in the project folder. In this listing `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `2f000` and the offset 4072. The folder `bwx10-2026-11-15` of the code repo holds no folder `ref-bwx8`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its title is "Design: explain the small read-bandwidth gain at 8 MiB". Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx10-crb-build-1/offsets.tsv`: the table of the CRB build, with 26 kernel rows. The rows of `asmread`, `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` and `read_1pl` hold 20 in the column `loop_mod64`.
- [Ref6] A `diff` in this task of `check_listing10.py` against `check_listing8.py`, both of the code repo. The functions `sections`, `offsets`, `loop_start` and `whole` are equal in both files. In the code of part 1 of `main` (lines 261 to 305) one line differs: the line that builds `extra` (line 302) has the added condition `k not in NEW_LOOP`.
- [Ref7] Searched in this task with `grep -r` in the folders `tests` and `status` of the repo for the text `failed_rows=`, which the summary line of this script holds. The search found two files: `check_listing12.out` and `check_listing13.out`, the saved outputs of the listing checks of bwx12 and bwx13.
