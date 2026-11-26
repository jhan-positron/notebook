# `check_listing12.py` explained

- Source file: `bwx12-2026-11-15/check_listing12.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 394 lines, 20994 bytes).
- sha256 of the source when this page was built: `cf8c3cd2cdb393f3a1a324c72dd3db78657dec3cd6ce635d0c46e236df41af9c`.
- Role in the whole-chip test: Acceptance check of the bwx12 kernel machine code, run after the build.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

The script reads the objdump text of the 55 kernels of `bwx12` (`listing.txt`) and the table of loop addresses (`offsets.tsv`). It accepts the build only when the 29 kernels of the earlier runner `bwx11` are unchanged and the 26 new kernels have exactly the planned instructions and loop position.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Whole-chip test**: the run of 2026-11-17 on the whole chip. Of `bwx12` it ran six kernels: `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`.
- **Kernel**: one loop function of the benchmark: a read, a write or a copy loop. Its function name in the binary is `k_` plus the kernel name. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the inner loop of the benchmark that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Interval mode, trial mode**: the two modes of `bwx12`. Interval mode (option `--seq`): every thread runs a sequence of kernels. In one timed interval a thread calls one kernel only, one or more times. The whole-chip test uses it. Trial mode (option `--trial`): one thread runs the trials of a plan file. The whole-chip test does not use it.
- **Development machine**: the machine on which this script ran. It is not CRB. The file `test_kernels12.py` in the same folder describes it as x86-64.
- **AArch64**: the 64-bit Arm instruction set. The listing of the CRB build is AArch64 code.
- **Dictionary**: the Python type `dict`: a table from keys to values.
- **objdump**: a tool that prints the machine code of a binary as text: one instruction per line, with its address.
- **listing.txt**: the objdump text of every kernel function of `bwx12`, written by `build12.sh` on CRB. The block of one kernel starts with a line `=== bwx12 <kernel> ===`.
- **offsets.tsv**: a table with one row per kernel, written by `build12.sh` on CRB. Its columns are `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`.
- **Reference**: the `listing.txt` and `offsets.tsv` of the accepted build of `bwx11`, saved in the folder `ref-bwx11`.
- **Accepted build**: a build of a runner whose listing passed its checker script. For `bwx12` it is the build whose files are saved in the folder `crb-build-1`.
- **Round 5**: the name in `bwx12.c` for the 26 kernels that `bwx12` adds to `bwx11`. It is not a round of a kernel sequence.
- **Backward branch**: a branch instruction whose target address is lower than its own address.
- **Loop, loop start**: the loop of a function is the range from the target of its first backward branch to that branch. The loop start is the address of the first instruction of this range.
- **Loop start modulo 64 (`loop_mod64`, loop offset)**: the remainder of the loop start address divided by 64. It gives the position of the loop start inside a 64-byte block of code. The value is a number of bytes from 0 to 63.
- **q, v and d registers**: three names for the 32 vector registers of AArch64. `qN` is the full 16-byte register N. `dN` is its low 8 bytes. `vN.2d` is the register as two 64-bit lanes. A lane is one element of a vector register.
- **ldp, stp, ldr**: `ldp` loads a pair of registers from memory. `stp` stores a pair. `ldr` loads one register.
- **nop**: an instruction that does nothing.
- **b.cc, b.lo**: two names of one conditional branch. After `cmp a, b` it jumps when a is below b as unsigned numbers.
- **bl, ret**: `bl` calls a function. `ret` returns to the caller.
- **adrp**: an instruction that puts the address of a 4096-byte page into a register.
- **movi, dup**: `movi` sets every lane of a vector register to a constant. `dup` copies a general register into every lane of a vector register.
- **Table of global addresses**: a table in the binary that holds addresses of global objects. Code reads an entry with `adrp` plus `ldr`. In the function `whole` the list of the used entries has the name `got`.
- **Stack guard**: a value that the compiler puts on the stack at function entry and compares before the return. When the value changed, the function calls `__stack_chk_fail`.
- **Callee-saved**: a register that must hold the same value when a function returns as when it was called. For v8 to v15 this holds for the low 8 bytes, the registers d8 to d15.
- **Stand-in loop**: a plain C loop that replaces an assembly kernel when the build machine is not AArch64.
- **sha256**: a digest: a value of 64 hexadecimal digits computed from the bytes of a file. Files with equal sha256 values are taken as equal.

</details>

## Main flow

1. When Python loads the file, it builds the table `NEW`: the expected loop of each of the 26 new kernels (lines 87-135).
2. `main` reads the arguments: the listing, the offsets table and the options (lines 278-296).
3. It reads the reference listing, the new listing and both offsets tables. It ends with exit status 2 when a file is unusable (lines 297-313).
4. Part 1: for each of the 29 kernels of the reference it compares the function text without addresses and the loop start modulo 64. It prints one row per kernel (lines 316-352).
5. It checks the places of the table of global addresses over all kernels. It rejects a kernel that neither the reference nor `NEW` holds (lines 353-360).
6. Part 2: for each of the 26 new kernels it applies the five rules of `new_problems`. It prints one row per kernel (lines 363-387).
7. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed (lines 388-390).

## Behavior a reader must know

- The scripts of the whole-chip test (`go.sh`, `go2.sh`, `ra.sh`, `rx.sh`) do not call this script. It ran after the build of `bwx12` on 2026-11-15, and the test of 2026-11-17 used the binary of that build [Ref4] [Ref5].
- The output for that build is saved in the file `check_listing12.out` in the build folder `crb-build-1` [Ref1]. All 29 rows of part 1 say `same` and `ok`. All 26 rows of part 2 say `expected` and `ok`. The summary line reports 0 failed rows in both parts.
- In this task (2026-11-21) the script was run again on the same `listing.txt` and `offsets.tsv`. It printed the same 58 lines as the saved output and ended with exit status 0. The saved output file has the modification time 2026-11-15 17:12:22 UTC on the development machine. The build on CRB ended at 17:12:14 UTC by the clock of CRB [Ref4]. Insufficient data: the command line that wrote the saved output file on 2026-11-15. A shell history or a session log of that day would resolve it.
- Part 1 passed for five kernels of the whole-chip test: `oldread` (the old read kernel), `read` (the new read kernel), `asmread`, `read_nop96` and `read_1pl` [Ref1]. This proves that every instruction of each function in `bwx12`, with every operand, equals the instruction at the same position in the accepted build of `bwx11`. Addresses are excluded from the comparison in the way that lines 27 to 42 define.
- Proved for the same five kernels: the loop start modulo 64 equals the value of `bwx11`. The values are 40 bytes for `oldread`, 36 bytes for `read`, and 20 bytes for `asmread`, `read_nop96` and `read_1pl` [Ref1].
- Part 2 passed for `read_nop256`. This proves that the loop is exactly the 8 `ldp` of `asmread` (256 bytes loaded per loop pass), then 256 `nop`, then `add x0, x0, #0x100`, `cmp x0, x1` and a `b.cc` back to the loop start. No instruction of the loop uses a loaded value. The function has no other branch or call. It stores d8 to d15 before the loop and reloads them after it. Its loop start modulo 64 is 20 bytes, the value of `asmread` in the same listing [Ref1].
- Limit: for the 29 kernels of part 1 the script proves equality with `bwx11` only. It holds no expected instruction list for them. The instructions of the old and the new read kernel are in the blocks `oldread` and `read` of `listing.txt` [Ref2].
- Limit: the script does not compare `bwx12` with `bw_old` or `bw_new`. It reads no listing of these two binaries.
- Limit: the script checks kernel functions only. It does not check the code that times a kernel. The whole-chip test uses the interval mode of `bwx12` [Ref11]. In this mode the function `worker` of `bwx12.c` reads the clock, and it calls each kernel through the function `call` [Ref10]. No file in the build folder `crb-build-1` holds the machine code of `worker` or `call`. The file `seq-listing.txt` lists `timed_sequence` and `timed_sequence_hot`. These two functions read the clock in the trial mode only, and the whole-chip test does not use the trial mode [Ref10]. `build12.sh` says that no script uses `seq-listing.txt` [Ref6].
- Limit: the script reads no digest. `build.txt` records the sha256 values of the binary `bwx12`, of `listing.txt` and of `offsets.tsv` from one build [Ref4]. The files `listing.txt` and `offsets.tsv` in the build folder have the recorded values (computed in this task). The binary `bwx12` is not in the local folders. So its sha256 value is known from the records only. `go.sh` stops unless the binary has the recorded value [Ref5].
- The script writes no file. It prints its tables to standard output. Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.

## Call sequence in the whole-chip test

- `check_listing12.py listing.txt offsets.tsv`: ran after the build of 2026-11-15. The test scripts do not call it.
  - `spec` (line 110): at load time, 26 calls: one expectation per new kernel
  - `vadd` (line 106): at load time: the add instructions of `read_dadd2` to `read_iadd16`
  - `main` (line 277): entry point, called from line 394
    - `sections` (line 138): reads the reference listing, then the new listing
    - `offsets` (line 156): reads the reference `offsets.tsv`, then the new `offsets.tsv`
    - `loop_start` (line 171): part 1: loop start of each kernel in both listings
    - `whole` (line 181): part 1: text without addresses of both functions
    - `loop_start` (line 171): part 2: loop start of `asmcopy`, `asmread`, `asmwrite` and each new kernel
    - `new_problems` (line 208): part 2: the five rules for one new kernel
      - `numbers` (line 204): register numbers of a matched store or load

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `vadd` | 106-107 | Builds the text of vector add instructions from pairs of register numbers. | - | - |
| `spec` | 110-114 | Returns the expectation of one new kernel: loop instructions, planned loop start modulo 64, original kernel, instructions before the loop, end-pointer instruction. | - | - |
| `sections` | 138-153 | Reads a listing file into a dictionary from (binary, kernel) to the list of (address, instruction text). | - | - |
| `offsets` | 156-168 | Reads `offsets.tsv` into a dictionary from (binary, kernel) to the text of column `loop_mod64`. Raises `ValueError` on a wrong header or row. | - | - |
| `loop_start` | 171-178 | Returns the target address of the first backward branch inside the function, or `None`. | - | - |
| `whole` | 181-201 | Returns the function text with addresses removed, and the places of the pointer loads from the table of global addresses. | - | - |
| `numbers` | 204-205 | Returns the register numbers that one `SAVE` or `RESTORE` match captured. | - | - |
| `new_problems` | 208-274 | Applies the five rules of part 2 to one new kernel and returns the list of problems. | `numbers` | - |
| `main` | 277-390 | Parses the arguments, reads the files, runs part 1 and part 2, prints one row per kernel, returns the exit status. | `sections`, `offsets`, `loop_start`, `whole`, `new_problems` | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bwx12-2026-11-15/check_listing12.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (394 lines, 20994 bytes, sha256 `cf8c3cd2cdb393f3a1a324c72dd3db78657dec3cd6ce635d0c46e236df41af9c`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: what the script is, usage and reference (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_listing12.py - acceptance test of a bwx12 build (design tackle-8mb.md,` | Starts the documentation text of the script (lines 2 to 78). Python does not execute it. `main` prints it when it finds too many arguments or an unknown option (line 293). This line: the script is the acceptance test of a build of the runner program `bwx12`. It accepts or rejects a build. Its input is the machine code of every kernel, as text. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 3 | `"Fixed setup": reject a build whose acceptance listing differs).` | Documentation text: the design note `tackle-8mb.md`, section "Fixed setup", gives the rule that a build is rejected when its acceptance listing differs [Ref8]. |
| 5 | `It is check_listing11.py with another reference and other new kernels. The` | Documentation text: this script is `check_listing11.py` with another reference and other new kernels. `check_listing11.py` is the script of the same kind in the folder of bwx11, the runner version before bwx12. |
| 6 | `code of part 1 is unchanged.` | Documentation text: the code of part 1 is unchanged. |
| 8 | `Runs on the development machine, on the listing.txt and offsets.tsv that` | Documentation text: the script runs on the development machine, not on CRB (the Arm reference server under test). It reads the files `listing.txt` and `offsets.tsv` that ... |
| 9 | `build12.sh wrote on CRB.` | Documentation text: ... the build script `build12.sh` wrote on CRB [Ref6]. |
| 10 | `Usage: check_listing12.py [listing.txt [offsets.tsv]]` | Documentation text: the usage. Both file arguments are optional. Line 295 and line 296 set the defaults. |
| 11 | `           [--ref-listing F] [--ref-offsets F] [--binary bwx12] [--ref-binary bwx11] [--skip-new]` | Documentation text: the five options. `--ref-listing` and `--ref-offsets` name other reference files. `--binary` and `--ref-binary` give the names of the two binaries as they stand in the title lines of the listings. The defaults are `bwx12` and `bwx11`. `--skip-new` leaves out part 2 (line 74). |
| 13 | `The reference is the accepted build of bwx11 (crb-build-1 of the folder` | Documentation text: the reference is the accepted build of bwx11. It is the folder `crb-build-1` in the folder ... |
| 14 | `bwx11-2026-11-15), saved in ref-bwx11/listing.txt and ref-bwx11/offsets.tsv` | Documentation text: ... `bwx11-2026-11-15`. Its two files are saved as `ref-bwx11/listing.txt` and `ref-bwx11/offsets.tsv` ... The copies are equal, byte for byte, to the files in the build folder of bwx11 [Ref3]. |
| 15 | `beside this script, binary "bwx11".` | Documentation text: ... beside this script. The name of the binary in these files is `bwx11`. |

### Documentation text: part 1, the kernels of the reference (lines 17 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `Part 1, the 29 kernels of the reference binary. The rules are the rules of` | Documentation text: part 1 covers the 29 kernels of the reference binary. These are the kernels that bwx11 already had. Five of the six kernels of the whole-chip test are among them: `oldread`, `read`, `asmread`, `read_nop96` and `read_1pl` [Ref11]. The rules are the rules of ... |
| 18 | `check_listing11.py part 1 (which are the rules of check_listing8.py),` | Documentation text: ... part 1 of `check_listing11.py`, which are the rules of `check_listing8.py`, ... |
| 19 | `unchanged. For every kernel of the reference:` | Documentation text: ... unchanged. Four rules follow. They hold for every kernel of the reference. |
| 20 | ` 1. the new listing has the kernel, and the function has a loop;` | Documentation text: rule 1 for a kernel of the reference. The new listing has the kernel, and the function has a loop. Lines 321 to 325 implement it. |
| 21 | ` 2. the whole function text equals the reference text, apart from addresses;` | Documentation text: rule 2 for a kernel of the reference. The whole function text equals the reference text, apart from addresses. Lines 327 to 330 implement it. |
| 22 | ` 3. the loop start modulo 64 equals the reference value. Both are computed` | Documentation text: rule 3 for a kernel of the reference. The loop start modulo 64 equals the reference value (lines 339 to 340). The loop start modulo 64 is the remainder of the loop start address divided by 64. Both values are computed ... |
| 23 | `    from the listings;` | Documentation text: ... from the listings. |
| 24 | ` 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as` | Documentation text: rule 4 for a kernel of the reference. The row of the kernel in the new `offsets.tsv` gives the same `loop_mod64` as ... Lines 341 to 344 implement it. |
| 25 | `    the new listing and as the row of the reference offsets.tsv.` | Documentation text: ... the new listing and as the row of the reference `offsets.tsv`. |
| 27 | `What "apart from addresses" means here:` | Documentation text: lines 28 to 42 define how two functions at different addresses are compared. The function `whole` (line 181) implements it. |
| 28 | ` - an instruction address is not compared;` | Documentation text: an instruction address is not compared. |
| 29 | ` - a branch target inside the function is compared as its distance from the` | Documentation text: a branch target inside the function is compared as its distance from the ... |
| 30 | `   function start;` | Documentation text: ... function start. |
| 31 | ` - a target outside the function (the stub of bl, the page of a single adrp)` | Documentation text: a target outside the function ... The text names two cases: the stub that a `bl` calls, and the page of a single `adrp`. `bl` is the call instruction. A stub is a short piece of code in the binary through which a call reaches a function of a shared library. The listing has 2 `bl` instructions, one in `oldread` and one in `oldread2`. Both call the stub `__stack_chk_fail@plt` of the function for a failed stack guard [Ref2]. |
| 32 | `   is compared by its symbol name, not by its address;` | Documentation text: ... is compared by its symbol name, not by its address. The code keeps all that stands in the angle brackets (line 192). When the listing shows a symbol name plus an offset there, the offset is compared too. |
| 33 | ` - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from` | Documentation text: the pair `adrp xN, page` and `ldr xN, [xN, #offset]` loads a pointer from ... `adrp` puts the address of a 4096-byte page into a register. The `ldr` after it loads a pointer from that page. |
| 34 | `   the table of global addresses of the binary. In the reference only the` | Documentation text: ... the table of global addresses of the binary. This table holds addresses of global objects of the binary. In the reference only the ... |
| 35 | `   load of the stack-guard pointer has this form. Page and offset are the` | Documentation text: ... load of the stack-guard pointer has this form. The page and the offset are the ... |
| 36 | `   place of the pointer in that table. The linker sets them, so they are not` | Documentation text: ... place of the pointer in that table. The linker sets them. So they are not ... |
| 37 | `   compared with the reference. The pair is accepted only where the reference` | Documentation text: ... compared with the reference. The pair is accepted only where the reference ... |
| 38 | `   has it, because the rest of the text must be equal. The listing does not` | Documentation text: ... has it: the rest of the text must be equal. The listing does not ... |
| 39 | `   name the pointer. So this is checked: the new listing must not use more` | Documentation text: ... name the pointer. So one more check is made: the new listing must not use more ... |
| 40 | `   places of the table than the reference, per function and over all` | Documentation text: ... places of the table than the reference, per function (lines 334 to 336) and over all ... |
| 41 | `   kernels. The reference uses one place. A row whose offset differs from the` | Documentation text: ... kernels (lines 353 to 356). The reference uses one place. A row whose offset differs from the ... |
| 42 | `   reference prints "NOTE: got_offset_differs" in place of "ok": read it.` | Documentation text: ... reference prints `NOTE: got_offset_differs` in place of `ok` (lines 337 to 338). The text asks the reader to read such a row. |
| 43 | `The loop of a function is the range from the target of its first backward` | Documentation text: the definition of the loop. The loop of a function is the range from the target of its first backward ... A backward branch is a branch whose target address is lower than its own address. |
| 44 | `branch to that branch.` | Documentation text: ... branch to that branch. The function `loop_start` (line 171) finds the first address of the loop. |

### Documentation text: part 2 (the new kernels), the option `--skip-new` and the exit status (lines 46 to 78)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `Part 2, the 26 kernels of round 5 (the keys of NEW below). The reference does` | Documentation text: part 2 covers the 26 kernels of round 5, the keys of the table `NEW` (lines 117 to 131). "Round 5" is the name in `bwx12.c` for these 26 additions [Ref7]. It is not a round of a kernel sequence. The whole-chip test runs one of them: `read_nop256` [Ref11]. The function `new_problems` (line 208) implements the five rules. |
| 47 | `not have them. All 26 must be in the new listing. For each one:` | Documentation text: the reference does not have these kernels. All 26 must be in the new listing. Five rules follow for each one. |
| 48 | ` 1. the function has exactly one backward branch, and no other branch or call;` | Documentation text: rule 1 of part 2. The function has exactly one backward branch, and no other branch or call. Lines 214 to 225 implement it. |
| 49 | ` 2. the instructions of the loop equal the expected list (the field "loop" of` | Documentation text: rule 2 of part 2. The instructions of the loop equal the expected list, which is the field `loop` of ... Lines 226 to 238 implement the rule. Lines 91 to 131 build the expected lists. |
| 50 | `    NEW), with every operand. The loop ends with b.cc (the same instruction` | Documentation text: ... `NEW`, with every operand. The loop ends with `b.cc` ... `b.cc` and `b.lo` are two names of one branch instruction. After `cmp x0, x1` it jumps when `x0` is below `x1` (unsigned compare). |
| 51 | `    as b.lo) to the loop start. The expected lists:` | Documentation text: ... to the loop start. The expected lists follow, one per family of kernels. |
| 52 | `      read_nopN       the 8 ldp of asmread, N nop, add #256, cmp` | Documentation text: `read_nopN`: the 8 `ldp` of `asmread`, N `nop`, an add of 256 and a compare. `ldp` loads a pair of registers. `nop` does nothing. |
| 53 | `      read_daddK      the 8 ldp, K "add vA.2d, vA.2d, vL.2d" with vL a` | Documentation text: `read_daddK`: the 8 `ldp`, then K adds of the form `add vA.2d, vA.2d, vL.2d`, where vL is a ... |
| 54 | `                      register that the 8 ldp loaded, add #256, cmp` | Documentation text: ... register that the 8 `ldp` loaded, then the add of 256 and the compare. |
| 55 | `      read_iadd16     the 8 ldp, 16 "add vA.2d, vA.2d, vB.2d" with vB one of` | Documentation text: `read_iadd16`: the 8 `ldp`, then 16 adds of the form `add vA.2d, vA.2d, vB.2d`, where vB is one of ... |
| 56 | `                      v24-v31, add #256, cmp` | Documentation text: ... v24 to v31, then the add of 256 and the compare. |
| 57 | `      read_spN        the 4 ldp of read_sparse, N nop, add #128, cmp` | Documentation text: `read_spN`: the 4 `ldp` of `read_sparse`, N `nop`, an add of 128 and a compare. |
| 58 | `      read_1pl_nop96  the 4 ldr of read_1pl, 96 nop, add #256, cmp` | Documentation text: `read_1pl_nop96`: the 4 `ldr` of `read_1pl`, 96 `nop`, the add of 256 and the compare. `ldr` loads one register. |
| 59 | `      write_nopN      the 8 stp of asmwrite, N nop, add #256, cmp` | Documentation text: `write_nopN`: the 8 `stp` of `asmwrite`, N `nop`, the add of 256 and the compare. `stp` stores a pair of registers. |
| 60 | `      copy_nopN       the 8 ldp and 8 stp of asmcopy, N nop, the two add, cmp` | Documentation text: `copy_nopN`: the 8 `ldp` and the 8 `stp` of `asmcopy`, N `nop`, the two adds and the compare. |
| 61 | ` 3. the instructions before the loop are: the computation of the end pointer` | Documentation text: rule 3 of part 2. The instructions before the loop are: the computation of the end pointer ... Lines 239 to 259 implement the rule. |
| 62 | `    (once), stores of d registers to the stack, and the instructions of the` | Documentation text: ... (once), stores of d registers to the stack, and the instructions of the ... |
| 63 | `    field "init" in their order (the movi of the add kernels, the dup of the` | Documentation text: ... field `init` in their order. These are the `movi` of the add kernels and the `dup` of the ... |
| 64 | `    write kernels), and nothing else. Every instruction after the loop is a` | Documentation text: ... write kernels. Nothing else may stand there. Every instruction after the loop is a ... |
| 65 | `    load of d registers from the stack, and the last one is ret;` | Documentation text: ... load of d registers from the stack, and the last one is `ret`, the return to the caller. |
| 66 | ` 4. every register from v8 to v15 that the loop uses is stored before the` | Documentation text: rule 4 of part 2. Every register from v8 to v15 that the loop uses is stored before the ... Lines 260 to 265 implement it. |
| 67 | `    loop and loaded after it (d8-d15 are callee-saved);` | Documentation text: ... loop and loaded after it. The text gives the reason: d8 to d15 are callee-saved. A callee-saved register must hold the same value when the function returns as when it was called. So a kernel whose loop loads into q8 to q15 must store d8 to d15 before the loop and reload them after it. |
| 68 | ` 5. the loop start modulo 64 equals the planned value (20 for a read kernel,` | Documentation text: rule 5 of part 2. The loop start modulo 64 equals the planned value: 20 for a read kernel, ... Lines 266 to 273 implement the rule. |
| 69 | `    40 for a write kernel, 52 for a copy kernel), it equals the loop start` | Documentation text: ... 40 for a write kernel, 52 for a copy kernel. It also equals the loop start ... |
| 70 | `    modulo 64 of the original in the same listing (asmread, asmwrite or` | Documentation text: ... modulo 64 of the original in the same listing. The original is `asmread`, `asmwrite` or ... |
| 71 | `    asmcopy), and the row in offsets.tsv gives the same value.` | Documentation text: ... `asmcopy`. And the row in `offsets.tsv` gives the same value. |
| 72 | `Any other kernel that the reference lacks is a failure.` | Documentation text: any other kernel that the reference lacks is a failure. Lines 357 to 360 implement it. |
| 74 | `--skip-new leaves out part 2. It is only for a build on a machine that is not` | Documentation text: the option `--skip-new` leaves out part 2. It is only for a build on a machine that is not ... |
| 75 | `AArch64, where the new kernels are plain C stand-in loops. The last line then` | Documentation text: ... AArch64 (the 64-bit Arm instruction set). There the new kernels are plain C stand-in loops. The last line of the output then ... |
| 76 | `says that the new kernels were NOT CHECKED.` | Documentation text: ... says that the new kernels were `NOT CHECKED`. `--skip-new` was not used for the accepted build of bwx12. The summary line of the saved output says `new_kernels=26`, not `NOT CHECKED` [Ref1]. |
| 77 | `Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.` | Documentation text: the exit statuses. 0: all checks passed. 1: a check failed. 2: a file could not be used. The code also returns 2 for wrong arguments (line 289, line 294). The exit status is the return value of `main` (line 394). |
| 78 | `"""` | Ends the documentation text. |

### Imports, constants and the expected instruction lists (lines 79 to 104)

| Line | Source | Explanation |
|---:|---|---|
| 79 | `import os` | Loads the module `os`. The script uses it for file paths. |
| 80 | `import re` | Loads the module `re` for regular expressions. |
| 81 | `import sys` | Loads the module `sys` for the arguments and the exit status. |
| 83 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. |
| 84 | `REF_DIR = os.path.join(HERE, "ref-bwx11")` | `REF_DIR`: its subfolder `ref-bwx11`, the place of the reference files. |
| 85 | `TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")` | `TARGET`: a compiled pattern for a branch target at the end of an instruction: a hexadecimal address, a space and a name in angle brackets. Group 1 holds the address. The page operand of an `adrp` instruction has the same form. The pattern matches it too. Two examples from the listing of the CRB build (`listing.txt`): the branch target `49a4 <k_read+0x4>` and the page operand `2f000 <__FRAME_END__+0x16a34>` [Ref2]. |
| 87 | `# The loop of each new kernel, as objdump prints it (one space between the` | Comment: the lists below hold the loop of each new kernel in the form in which `objdump` prints it, with one space between the ... `objdump` is the tool that prints the machine code of a binary as text. The function `sections` (line 138) brings the instruction text of a listing into the same form. |
| 88 | `# fields). x0 is the pointer and x1 is the end, as in every asm read and write` | Comment: ... fields. The register `x0` is the pointer and `x1` is the end address, as in every asm read and write ... |
| 89 | `# kernel of the reference. A copy kernel has the destination in x0, the source` | Comment: ... kernel of the reference. A copy kernel has the destination in `x0`, the source ... |
| 90 | `# in x1 and the end in x2. The loop branch stands after these instructions.` | Comment: ... in `x1` and the end address in `x2`. The loop branch stands after these instructions. It is not in the lists. |
| 91 | `LDP8 = ["ldp q0, q1, [x0]", "ldp q2, q3, [x0, #32]", "ldp q4, q5, [x0, #64]", "ldp q6, q7, [x0, #96]",` | `LDP8`: the 8 `ldp` instructions of `asmread`. Each one loads two 16-byte registers. Together they load q0 to q15 from the 256 bytes at the pointer `x0`. This line holds the first four, for the offsets 0, 32, 64 and 96 bytes. |
| 92 | `        "ldp q8, q9, [x0, #128]", "ldp q10, q11, [x0, #160]", "ldp q12, q13, [x0, #192]", "ldp q14, q15, [x0, #224]"]` | Continues the list of line 91: the other four `ldp`, for the offsets 128, 160, 192 and 224 bytes. |
| 93 | `STEP = ["add x0, x0, #0x100", "cmp x0, x1"]` | `STEP`: add 256 bytes (`#0x100`) to `x0`, then compare `x0` with the end pointer `x1`. |
| 94 | `STEP128 = ["add x0, x0, #0x80", "cmp x0, x1"]` | `STEP128`: the same two instructions with an add of 128 bytes (`#0x80`). |
| 95 | `LDR4 = ["ldr q0, [x0]", "ldr q1, [x0, #64]", "ldr q2, [x0, #128]", "ldr q3, [x0, #192]"]` | `LDR4`: 4 `ldr` instructions. Each one loads 16 bytes. The offsets from `x0` are 0, 64, 128 and 192 bytes. |
| 96 | `STP8 = ["stp q0, q0, [x0%s]" % ("" if o == 0 else ", #%d" % o) for o in range(0, 256, 32)]` | `STP8`: 8 `stp` instructions, built by a list comprehension over the offsets 0, 32 and so on up to 224 bytes. Each one stores q0 twice (32 bytes). The first text has no offset. The others end with the offset, for example `, #32]`. |
| 97 | `COPY_LDP8 = [t.replace("[x0", "[x1") for t in LDP8]` | `COPY_LDP8`: the texts of `LDP8` with the source pointer `x1` in place of `x0`. |
| 98 | `COPY_STP8 = [t.replace("ldp", "stp") for t in LDP8]` | `COPY_STP8`: the texts of `LDP8` with `stp` in place of `ldp`. These are 8 `stp` that store q0 to q15 at the destination pointer `x0`. |
| 99 | `COPY_STEP = ["add x1, x1, #0x100", "add x0, x0, #0x100", "cmp x1, x2"]` | `COPY_STEP`: add 256 bytes to both pointers, then compare the source pointer `x1` with the end pointer `x2`. |
| 100 | `END_POINTER = "add x1, x0, x1, lsl #3"` | `END_POINTER`: the instruction before the loop that computes the end address: pointer plus 8 times the second argument. The second argument of a kernel is a count of 8-byte words [Ref9]. `lsl #3` shifts it left by 3 bits. |
| 101 | `COPY_END_POINTER = "add x2, x1, x2, lsl #3"` | `COPY_END_POINTER`: the same instruction with the registers of a copy kernel. The end address is the source pointer `x1` plus 8 times `x2`. |
| 102 | `ACC_ZERO = ["movi v%d.4s, #0x0" % r for r in range(16, 24)]` | `ACC_ZERO`: 8 `movi` instructions that set v16 to v23 to zero. `movi` sets every lane of a vector register to a constant. A lane is one element of a vector register. |
| 103 | `CONST_ONE = ["movi v%d.4s, #0x1" % r for r in range(24, 32)]` | `CONST_ONE`: 8 `movi` instructions that set each 32-bit lane of v24 to v31 to 1. |

### Functions `vadd` and `spec`: build one expectation (lines 105 to 116)

| Line | Source | Explanation |
|---:|---|---|
| 106 | `def vadd(pairs):` | Starts the function `vadd`. It turns pairs of register numbers (a, b) into the texts of vector add instructions. |
| 107 | `    return ["add v%d.2d, v%d.2d, v%d.2d" % (a, a, b) for a, b in pairs]` | Returns one text `add va.2d, va.2d, vb.2d` per pair. This instruction adds the two 64-bit lanes of register b to register a. |
| 110 | `def spec(loop, mod, like, init=(), end=END_POINTER):` | Starts the function `spec`. It returns the expectation of one new kernel as a dictionary with 5 fields. `init` is empty and `end` is `END_POINTER` when the caller does not give them. |
| 111 | `    """loop: the instructions of the loop before its branch; mod: the planned loop start modulo 64; like: the` | Documentation text of `spec`. `loop`: the instructions of the loop without the loop branch. `mod`: the planned loop start modulo 64. `like`: the ... |
| 112 | `    kernel of the reference whose loop offset this kernel must have; init: the instructions before the loop` | Documentation text: ... kernel of the reference that must have the same loop start modulo 64 in the same listing. `init`: the extra instructions before the loop ... |
| 113 | `    beside the end pointer and the stores of d registers; end: the computation of the end pointer"""` | Documentation text: ... beside the end-pointer instruction and the stores of d registers. `end`: the end-pointer instruction. |
| 114 | `    return {"loop": loop, "mod": mod, "like": like, "init": list(init), "end": end}` | Returns the dictionary with the 5 fields. `list(init)` turns the `init` argument into a list. |

### Table `NEW` of the new kernels, and the patterns `SAVE`, `RESTORE` and `BRANCH` (lines 117 to 137)

| Line | Source | Explanation |
|---:|---|---|
| 117 | `NEW = {}` | `NEW`: the table of the new kernels, empty at first. A key is a kernel name. Its value is the expectation of that kernel. |
| 118 | `for _n in (48, 56, 72, 80, 88, 112, 160, 192, 256):` | Loop over the nine nop counts of the family `read_nopN`. |
| 119 | `    NEW["read_nop%d" % _n] = spec(LDP8 + ["nop"] * _n + STEP, 20, "asmread")` | The expected loop of `read_nopN`: `LDP8`, N `nop`, `STEP`. The planned loop start modulo 64 is 20 bytes, and the original is `asmread`. Both hold for every read kernel of the table. The whole-chip test runs `read_nop256` (N = 256) [Ref11]. |
| 120 | `NEW["read_dadd2"] = spec(LDP8 + vadd([(16, 0), (17, 8)]) + STEP, 20, "asmread", ACC_ZERO)` | `read_dadd2`: after the loads come 2 vector adds. They add v0 to v16 and v8 to v17. Each add takes a register that the loads of the same loop pass filled. Before the loop the 8 `movi` of `ACC_ZERO` must stand. |
| 121 | `NEW["read_dadd4"] = spec(LDP8 + vadd([(16, 0), (17, 4), (18, 8), (19, 12)]) + STEP, 20, "asmread", ACC_ZERO)` | `read_dadd4`: 4 vector adds. They add v0, v4, v8 and v12 to v16, v17, v18 and v19. |
| 122 | `NEW["read_dadd8"] = spec(LDP8 + vadd([(16 + i, 2 * i) for i in range(8)]) + STEP, 20, "asmread", ACC_ZERO)` | `read_dadd8`: 8 vector adds. Add number i adds the loaded register with the number 2 times i to register 16 plus i. So v0, v2 and so on up to v14 go to v16 to v23. |
| 123 | `NEW["read_dadd16"] = spec(LDP8 + vadd([(16 + i % 8, i) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO)` | `read_dadd16`: 16 vector adds. They add all 16 loaded registers v0 to v15. Each of v16 to v23 gets two of them. |
| 124 | `NEW["read_iadd16"] = spec(LDP8 + vadd([(16 + i % 8, 24 + i % 8) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO + CONST_ONE)` | `read_iadd16`: 16 vector adds that take the constant registers v24 to v31, not a loaded register. Each of v16 to v23 gets two adds. Before the loop the 8 `movi` of `ACC_ZERO` and the 8 `movi` of `CONST_ONE` must stand. |
| 125 | `for _n in (24, 32, 40, 48, 56):` | Loop over the five nop counts of the family `read_spN`. |
| 126 | `    NEW["read_sp%d" % _n] = spec(LDP8[:4] + ["nop"] * _n + STEP128, 20, "asmread")` | `read_spN`: the first 4 `ldp` of `LDP8` (128 bytes per loop pass), N `nop`, `STEP128`. |
| 127 | `NEW["read_1pl_nop96"] = spec(LDR4 + ["nop"] * 96 + STEP, 20, "asmread")` | `read_1pl_nop96`: the 4 loads of `LDR4`, 96 `nop`, `STEP`. |
| 128 | `for _n in (32, 96, 128, 256):` | Loop over the four nop counts of the write kernels. |
| 129 | `    NEW["write_nop%d" % _n] = spec(STP8 + ["nop"] * _n + STEP, 40, "asmwrite", ["dup v0.2d, x2"])` | `write_nopN`: `STP8`, N `nop`, `STEP`. The planned loop start modulo 64 is 40 bytes, and the original is `asmwrite`. Before the loop `dup v0.2d, x2` must stand. `dup` copies the general register `x2` into both 64-bit lanes of v0. |
| 130 | `for _n in (96, 192):` | Loop over the two nop counts of the copy kernels. |
| 131 | `    NEW["copy_nop%d" % _n] = spec(COPY_LDP8 + COPY_STP8 + ["nop"] * _n + COPY_STEP, 52, "asmcopy", end=COPY_END_POINTER)` | `copy_nopN`: `COPY_LDP8`, `COPY_STP8`, N `nop`, `COPY_STEP`. The planned loop start modulo 64 is 52 bytes, the original is `asmcopy`, and the end-pointer instruction is `COPY_END_POINTER`. |
| 132 | `NEW_LOOP = NEW  # the name that the code of part 1 uses for "is a new kernel"` | `NEW_LOOP`: a second name for the same table. Comment: the code of part 1 uses this name to ask whether a kernel is a new kernel. |
| 133 | `SAVE = re.compile(r"(?:stp d(\d+), d(\d+)\|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")` | `SAVE`: a compiled pattern for a store of one or two d registers to the stack: `stp` with two d registers or `str` with one, then `[sp]` with or without an offset, with or without `!`. Example: `stp d8, d9, [sp, #-64]!`. The groups hold the register numbers. |
| 134 | `RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)\|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")` | `RESTORE`: a compiled pattern for a load of one or two d registers from the stack: `ldp` with two d registers or `ldr` with one. Example: `ldp d8, d9, [sp], #64`. The groups hold the register numbers. |
| 135 | `BRANCH = re.compile(r"(b\|bl\|br\|blr\|b\.[a-z]+\|cbn?z\|tbn?z)\b")` | `BRANCH`: a compiled pattern for the name of a branch or call instruction at the start of the text: `b`, `bl`, `br`, `blr`, a conditional `b.` with letters, `cbz`, `cbnz`, `tbz`, `tbnz`. It does not match `ret`. |

### Functions `sections` and `offsets`: read the two kinds of input file (lines 138 to 170)

| Line | Source | Explanation |
|---:|---|---|
| 138 | `def sections(path):` | Starts the function `sections`. It reads a listing file. |
| 139 | `    """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""` | Documentation text of `sections`: it returns a dictionary. A key is the pair (binary, kernel). Its value is the list of (address, instruction text) of that kernel function, in file order. Example: in the listing of the CRB build (`listing.txt`) the first block starts with the title line `=== bwx12 read ===`. The label line `00000000000049a0 <k_read>:` follows it. It is no instruction line and is skipped (line 147) [Ref2]. |
| 140 | `    out, cur = {}, None` | `out`: the dictionary. `cur`: the list of the block that is read now. It is `None` outside a block. |
| 141 | `    with open(path) as f:` | Opens the file. |
| 142 | `        for line in f:` | Loop over the lines of the file. |
| 143 | `            m = re.match(r"=== (\S+) (\S+) ===", line)` | Tests whether the line is a title line of the form `=== BINARY KERNEL ===`. Group 1 holds the name of the binary, group 2 the name of the kernel. |
| 144 | `            if m:` | A title line starts the block of one kernel. |
| 145 | `                cur = out.setdefault((m.group(1), m.group(2)), [])` | `cur` becomes the list for this pair. `setdefault` creates an empty list when the pair is new. |
| 146 | `                continue` | Goes to the next line. |
| 147 | `            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)` | Tests whether the line is an instruction line: spaces, a hexadecimal address (group 1), a colon, spaces or tabs, and the instruction (group 2). The label line of a function has no colon directly after its address. So it does not match and is skipped. |
| 148 | `            if m and cur is not None:` | Only inside a block ... |
| 149 | `                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()` | ... the text is cleaned. The `objdump` comment after `//` is cut off. Each run of spaces and tabs becomes one space. |
| 150 | `                cur.append((int(m.group(1), 16), text))` | Appends the pair of the address as a number and the cleaned text to the block. |
| 151 | `            elif line.startswith("##"):` | A line that starts with `##` ... |
| 152 | `                cur = None` | ... ends the block that is read now. |
| 153 | `    return out` | Returns the dictionary. |
| 156 | `def offsets(path):` | Starts the function `offsets`. It reads a file `offsets.tsv`. |
| 157 | `    """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""` | Documentation text of `offsets`: it returns a dictionary from (binary, kernel) to the text of the column `loop_mod64`. |
| 158 | `    out = {}` | `out`: the dictionary. |
| 159 | `    with open(path) as f:` | Opens the file. |
| 160 | `        head = f.readline().rstrip("\n").split("\t")` | `head`: the fields of the first line, split at the tab characters. |
| 161 | `        if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:` | The first line must hold exactly the 6 column names. |
| 162 | `            raise ValueError("%s: unexpected header line" % path)` | If not, the function raises `ValueError` with the text `unexpected header line`. `main` then ends with exit status 2 (lines 300 to 302). |
| 163 | `        for line in f:` | Loop over the other lines. |
| 164 | `            p = line.rstrip("\n").split("\t")` | `p`: the fields of the line. |
| 165 | `            if len(p) != 6:` | Every row must have 6 fields. |
| 166 | `                raise ValueError("%s: a row with %d fields" % (path, len(p)))` | If not, the function raises `ValueError`. |
| 167 | `            out[(p[0], p[1])] = p[5]` | Stores column 6 under the pair of column 1 and column 2. The script uses columns 1, 2 and 6 only. It ignores the columns `function`, `start` and `loop_start`. |
| 168 | `    return out` | Returns the dictionary. |

### Functions `loop_start`, `whole` and `numbers` (lines 171 to 207)

| Line | Source | Explanation |
|---:|---|---|
| 171 | `def loop_start(insns):` | Starts the function `loop_start`. `insns` is the list of (address, text) of one function. |
| 172 | `    """address of the loop start: the target of the first backward branch into the function, or None"""` | Documentation text of `loop_start`: it returns the address of the loop start. That is the target of the first backward branch into the function. Without such a branch the result is `None`. |
| 173 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 174 | `    for addr, text in insns:` | Goes through the instructions in order. |
| 175 | `        m = TARGET.search(text)` | Looks for a branch target at the end of the instruction text. |
| 176 | `        if m and first <= int(m.group(1), 16) < addr:` | The branch counts when its target lies inside the function and before the branch itself (`first <= target < addr`). |
| 177 | `            return int(m.group(1), 16)` | Returns that target. This address is the loop start. `main` computes a loop start modulo 64 as `loop_start(...) % 64`. |
| 178 | `    return None` | Returns `None` when the function has no such branch. |
| 181 | `def whole(insns):` | Starts the function `whole`. It returns the text of a function in a form that does not depend on the addresses. |
| 182 | `    """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""` | Documentation text of `whole`: it returns two lists. The first is the function text without addresses (`out`). The second holds the places (page, offset) of the pointer loads from the table of global addresses (`got`). Two examples with text of the listing of the CRB build (`listing.txt`): `b.hi 49a4 <k_read+0x4>` becomes `b.hi +0x4` (line 189), and the call of `__stack_chk_fail@plt` becomes `bl (outside <__stack_chk_fail@plt>)` (line 192) [Ref2]. |
| 183 | `    first, last, out, got = insns[0][0], insns[-1][0], [], []` | `first` and `last`: the addresses of the first and the last instruction. `out` and `got`: the two result lists. |
| 184 | `    adrp_reg = adrp_page = None` | `adrp_reg` and `adrp_page`: the register and the page of an `adrp` instruction, kept for the next instruction only. |
| 185 | `    for _, text in insns:` | Loop over the instruction texts. |
| 186 | `        m = TARGET.search(text)` | Looks for a target at the end of the text. |
| 187 | `        page = None` | `page`: the address text of a target outside the function. `None` at first. |
| 188 | `        if m and first <= int(m.group(1), 16) <= last:` | A target inside the function ... |
| 189 | `            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... becomes its distance from the function start, written as `+0x` and hexadecimal digits. |
| 190 | `        elif m:` | A target outside the function: |
| 191 | `            page = m.group(1)` | `page` keeps the address text for line 199. |
| 192 | `            text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]` | The text becomes `(outside NAME)`. NAME is all that stands in the angle brackets, with the brackets: a symbol name, or a symbol name plus an offset. It is kept, and the address before it is removed. |
| 193 | `        load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)` | `load`: tests whether the whole text is a load of the form `ldr xA, [xB, #N]`. The groups hold the two registers and the offset. |
| 194 | `        if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:` | The pair counts when the instruction before was an `adrp` with a page, and both registers of the load are the register of that `adrp`. |
| 195 | `            got.append((adrp_page, load.group(3)))` | Records the place (page, offset) in `got`. |
| 196 | `            out[-1] = "adrp %s, (table page)" % adrp_reg` | Replaces the text of the `adrp` before by the fixed text `adrp xN, (table page)`. |
| 197 | `            text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)` | Replaces the text of the load by the fixed text `ldr xN, [xN, #(table)]`. So the page and the offset are not part of the text comparison. In both listings only `oldread` and `oldread2` have this pair. Each has it twice, with the page address `2f000` (hexadecimal) and the offset 4072 bytes [Ref2] [Ref3]. |
| 198 | `        m = re.match(r"adrp (x\d+), ", text)` | Tests whether this instruction is an `adrp`. Group 1 holds its register. |
| 199 | `        adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)` | Remembers the register and the page of an `adrp` with a page outside the function. Every other instruction clears both values. |
| 200 | `        out.append(text)` | Appends the text to `out`. |
| 201 | `    return out, got` | Returns the two lists. |
| 204 | `def numbers(match):` | Starts the function `numbers`. `match` is one match of `SAVE` or of `RESTORE`. |
| 205 | `    return {int(g) for g in match.groups() if g is not None}` | Returns the set of the register numbers that the match captured. A group without a value is left out. |

### Function `new_problems`: the rules of part 2 for one new kernel (lines 208 to 276)

| Line | Source | Explanation |
|---:|---|---|
| 208 | `def new_problems(kernel, insns, want_mod, off_row):` | Starts the function `new_problems`. It applies the rules of part 2 to one new kernel and returns a list of problem texts. An empty list says that the kernel passed. `insns` is the list of (address, text) of the kernel function. `off_row` is the value of the kernel in `offsets.tsv`, or `None`. |
| 209 | `    """Part 2 for one new kernel. want_mod: the loop start modulo 64 of the original (the field "like") in the` | Documentation text of `new_problems`: it is part 2 for one new kernel. `want_mod` is the loop start modulo 64 of the original, the kernel that the field `like` names, in the ... `main` computes it (lines 367 to 371, line 375). |
| 210 | `    same listing, or None."""` | Documentation text: ... same listing, or `None`. |
| 211 | `    p = []` | `p`: the list of problem texts, empty at first. |
| 212 | `    sp = NEW[kernel]` | `sp`: the expectation of this kernel from the table `NEW`. |
| 213 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 214 | `    back = [i for i, (addr, text) in enumerate(insns)` | `back`: the positions of every instruction that has a branch target ... |
| 215 | `            if TARGET.search(text) and first <= int(TARGET.search(text).group(1), 16) <= addr]` | ... inside the function, at or before its own address. These are the backward branches. |
| 216 | `    if len(back) != 1:` | Exactly 1 backward branch is required. |
| 217 | `        return ["%d backward branches, 1 expected" % len(back)]` | If not, the function returns immediately with this one problem. |
| 218 | `    end = back[0]` | `end`: the position of that branch, the loop branch. |
| 219 | `    loop = int(TARGET.search(insns[end][1]).group(1), 16)` | `loop`: its target address, the loop start. |
| 220 | `    begin = next((i for i, (addr, _) in enumerate(insns) if addr == loop), None)` | `begin`: the position of the instruction at that address. `None` when no instruction has that address. |
| 221 | `    if begin is None:` | If no instruction has that address ... |
| 222 | `        return ["the loop branch goes to %x, which is not the address of an instruction" % loop]` | ... the function returns with one problem. |
| 223 | `    others = [text for i, (_, text) in enumerate(insns) if i != end and BRANCH.match(text)]` | Rule 1: `others` lists every other instruction that `BRANCH` matches. The `ret` at the end is not matched. |
| 224 | `    if others:` | If there is one ... |
| 225 | `        p.append("a branch or call beside the loop branch: %s" % "; ".join(others))` | ... it is a problem: a branch or call beside the loop branch. |
| 226 | `    body, want = [text for _, text in insns[begin:end]], sp["loop"]` | Rule 2. `body`: the instruction texts from the loop start to the instruction before the loop branch. `want`: the expected list from `NEW`. |
| 227 | `    if body != want:` | The two lists `body` and `want` must be equal: the same count, the same order, and every instruction text equal with every operand. The next lines only write the messages for the case that they differ. |
| 228 | `        # the count of nop first: one line says what is wrong with a loop of the wrong length` | Comment: the count of `nop` comes first. Then one line says what is wrong with a loop of the wrong length. |
| 229 | `        if body.count("nop") != want.count("nop"):` | When the two lists hold different numbers of `nop` ... |
| 230 | `            p.append("the loop has %d nop, expected %d" % (body.count("nop"), want.count("nop")))` | ... a problem names both counts. |
| 231 | `        diff = [i for i in range(max(len(body), len(want))) if (body[i] if i < len(body) else "(none)") != (want[i] if i < len(want) else "(none)")]` | `diff`: the positions at which the two lists differ. Where one list is shorter, its entry counts as `(none)`. |
| 232 | `        for i in diff[:3]:` | For the first 3 of these positions ... |
| 233 | `            p.append("loop instruction %d is '%s', expected '%s'" % (i, body[i] if i < len(body) else "(none)",` | ... a problem names the position, the instruction found ... |
| 234 | `                                                                   want[i] if i < len(want) else "(none)"))` | ... and the instruction expected. |
| 235 | `        if len(diff) > 3:` | When more than 3 positions differ ... |
| 236 | `            p.append("%d more loop instructions differ" % (len(diff) - 3))` | ... one more problem gives the number of the others. |
| 237 | `    if not re.fullmatch(r"b\.(cc\|lo) %x <k_%s\+0x%x>" % (loop, re.escape(kernel), loop - first), insns[end][1]):` | The loop branch must be `b.cc` or `b.lo` to the loop start. The whole text must be the name, the loop address, and in angle brackets `k_` plus the kernel name plus the distance of the loop start from the function start. `re.escape` makes the kernel name plain text for the pattern. |
| 238 | `        p.append("the loop branch is '%s', expected b.cc (b.lo) to the loop start" % insns[end][1])` | If not, a problem shows the text of the loop branch. |
| 239 | `    head, tail = [text for _, text in insns[:begin]], [text for _, text in insns[end + 1:]]` | Rule 3. `head`: the instructions before the loop start. `tail`: the instructions after the loop branch. |
| 240 | `    saved, restored, init = set(), set(), []` | `saved` and `restored`: two sets of register numbers. `init`: the list of the other instructions before the loop. |
| 241 | `    for text in head:` | Loop over the instructions before the loop. |
| 242 | `        m = SAVE.fullmatch(text)` | Tests whether the whole text is a store of d registers to the stack (`SAVE`). |
| 243 | `        if m:` | If it is ... |
| 244 | `            saved \|= numbers(m)` | ... its register numbers are added to `saved`. |
| 245 | `        elif text != sp["end"]:` | Every other instruction, apart from the end-pointer instruction ... |
| 246 | `            init.append(text)` | ... is added to the list `init`. |
| 247 | `    if head.count(sp["end"]) != 1:` | The end-pointer instruction must occur exactly 1 time before the loop. |
| 248 | `        p.append("before the loop: '%s' stands %d times, 1 expected" % (sp["end"], head.count(sp["end"])))` | If not, a problem gives the count. |
| 249 | `    if init != sp["init"]:` | `init` must equal the field `init` of the expectation, in the same order. For `read_nop256` this field is empty. So only stores of d registers and the end-pointer instruction may stand before its loop. |
| 250 | `        p.append("before the loop, beside the end pointer and the stores of d registers: '%s', expected '%s'" %` | If not, a problem shows the instructions found ... |
| 251 | `                 ("; ".join(init) or "nothing", "; ".join(sp["init"]) or "nothing"))` | ... and the instructions expected. An empty list is written as `nothing`. |
| 252 | `    if not tail or tail[-1] != "ret":` | After the loop: the last instruction must be `ret`. |
| 253 | `        p.append("the function does not end with ret")` | If not, a problem says that the function does not end with `ret`. |
| 254 | `    for text in tail[:-1]:` | Loop over the instructions between the loop branch and the last instruction. |
| 255 | `        m = RESTORE.fullmatch(text)` | Tests whether the whole text is a load of d registers from the stack (`RESTORE`). |
| 256 | `        if m:` | If it is ... |
| 257 | `            restored \|= numbers(m)` | ... its register numbers are added to `restored`. |
| 258 | `        else:` | Every other instruction ... |
| 259 | `            p.append("after the loop: '%s' is not a load of d registers from the stack" % text)` | ... is a problem. |
| 260 | `    used = {int(n) for text in body for n in re.findall(r"\b[qvd](\d+)\b", text) if 8 <= int(n) <= 15}` | Rule 4. `used`: the register numbers from 8 to 15 that the loop names as a q, v or d register. The pattern takes the number after one of the letters `q`, `v` or `d`. |
| 261 | `    if used - saved or used - restored:` | Every register in `used` must be in `saved` and in `restored`. |
| 262 | `        p.append("the loop uses v%s; not stored before the loop: %s; not loaded after it: %s" %` | If not, a problem lists the used registers ... |
| 263 | `                 (",".join(str(n) for n in sorted(used)), sorted(used - saved) or "none", sorted(used - restored) or "none"))` | ... those that are not stored before the loop, and those that are not loaded after it. |
| 264 | `    if saved != restored:` | The stored set and the reloaded set must be equal. |
| 265 | `        p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))` | If not, a problem shows both sets. The script compares register numbers only. It does not compare the stack offset of a store with the stack offset of its reload. |
| 266 | `    if want_mod is None:` | The place of the loop. `loop % 64` is the loop start modulo 64 of this kernel. `want_mod` is the value of the kernel to compare with in the same listing. It is `None` when that kernel has no loop in the listing. |
| 267 | `        p.append("%s has no loop in this listing, so the loop offset cannot be compared" % sp["like"])` | This is also a problem: the loop offset cannot be compared. The message names the original. Lines 266 to 273 implement rule 5 of part 2. |
| 268 | `    elif loop % 64 != want_mod:` | `loop % 64` must equal `want_mod`. |
| 269 | `        p.append("loop offset modulo 64 is %d, %s has %d" % (loop % 64, sp["like"], want_mod))` | If not, a problem gives both values. |
| 270 | `    if loop % 64 != sp["mod"]:` | `loop % 64` must also equal the planned value of `NEW`, the field `mod`. |
| 271 | `        p.append("loop offset modulo 64 is %d, planned %d" % (loop % 64, sp["mod"]))` | If not, a problem gives both values. |
| 272 | `    if off_row != str(loop % 64):` | The row of the kernel in `offsets.tsv` must hold the same number as text. |
| 273 | `        p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))` | If not, a problem gives both values. A missing row is written as `no row`. |
| 274 | `    return p` | Returns the list of problems. |

### Function `main`: arguments and input files (lines 277 to 314)

| Line | Source | Explanation |
|---:|---|---|
| 277 | `def main():` | Starts the function `main`. Its return value becomes the exit status (line 394). |
| 278 | `    args = sys.argv[1:]` | `args`: the arguments of the command line without the script name. |
| 279 | `    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),` | `opt`: the defaults of the 4 options that take a value. The reference files are `listing.txt` and `offsets.tsv` in the folder `REF_DIR`. |
| 280 | `           "--binary": "bwx12", "--ref-binary": "bwx11"}` | Continues the dictionary of line 279: the binary name is `bwx12`. The reference binary name is `bwx11`. |
| 281 | `    skip_new = "--skip-new" in args` | `skip_new`: true when the arguments hold `--skip-new`. This option is a flag without a value. |
| 282 | `    if skip_new:` | When the flag is present ... |
| 283 | `        args.remove("--skip-new")` | ... it is removed from the list. |
| 284 | `    for name in opt:` | Loop over the 4 option names. |
| 285 | `        if name in args:` | An option that is present ... |
| 286 | `            i = args.index(name)` | ... stands at position `i` ... |
| 287 | `            if i + 1 >= len(args):` | ... and needs one more argument after it. |
| 288 | `                print("%s needs a value" % name)` | Without it the script prints that the option needs a value ... |
| 289 | `                return 2` | ... and ends with exit status 2. |
| 290 | `            opt[name] = args[i + 1]` | The next argument becomes the value of the option. |
| 291 | `            del args[i:i + 2]` | Both are removed from the list. |
| 292 | `    if len(args) > 2 or any(a.startswith("--") for a in args):` | More than 2 remaining arguments, or a remaining argument that starts with `--` ... |
| 293 | `        print(__doc__)` | ... print the documentation text ... |
| 294 | `        return 2` | ... and the script ends with exit status 2. |
| 295 | `    listing = args[0] if args else os.path.join(HERE, "listing.txt")` | `listing`: the first remaining argument, or `listing.txt` in the folder of the script. |
| 296 | `    offs = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")` | `offs`: the second remaining argument, or `offsets.tsv` in the folder of the listing. |
| 297 | `    try:` | Starts the block in which a file error is caught. |
| 298 | `        ref, got = sections(opt["--ref-listing"]), sections(listing)` | Reads the reference listing into `ref` and the new listing into `got`. |
| 299 | `        ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)` | Reads the reference `offsets.tsv` into `ref_off` and the new `offsets.tsv` into `got_off`. |
| 300 | `    except (OSError, ValueError) as e:` | A file that cannot be opened (`OSError`), or an offsets table with a wrong form (`ValueError`) ... |
| 301 | `        print("cannot use: %s" % e)` | ... prints `cannot use:` and the reason ... |
| 302 | `        return 2` | ... and ends the script with exit status 2. |
| 303 | `    b, rb = opt["--binary"], opt["--ref-binary"]` | `b`: the name of the new binary. `rb`: the name of the reference binary. |
| 304 | `    kernels = [k for (bb, k) in ref if bb == rb]` | `kernels`: the list of the kernel names of the reference binary, in the order of the reference listing. |
| 305 | `    if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):` | One more case that ends with exit status 2: the reference listing has no kernel of the reference binary, or a reference kernel has no instructions or no loop. |
| 306 | `        print("the reference listing has no usable block of binary %s" % rb)` | Prints a message that names the reference binary ... |
| 307 | `        return 2` | ... and ends with exit status 2. |
| 308 | `    if any(k in NEW_LOOP for k in kernels):` | One more case: the reference listing holds a new kernel, which is a key of `NEW_LOOP`. |
| 309 | `        print("the reference listing holds a kernel of round 5: it is not a listing of %s" % rb)` | Prints a message: the reference holds a kernel of round 5, so it is not a listing of the reference binary. |
| 310 | `        return 2` | Ends with exit status 2. |
| 311 | `    if not any(bb == b for bb, _ in got):` | One more case: the new listing has no block of the new binary. |
| 312 | `        print("no '=== %s kernel ===' block in %s" % (b, listing))` | Prints a message that names the new binary and the listing file ... |
| 313 | `        return 2` | ... and ends with exit status 2. |

### Function `main`: part 1, one output row per kernel of the reference (lines 315 to 361)

| Line | Source | Explanation |
|---:|---|---|
| 315 | `    # Part 1: the kernels of the reference (the code of check_listing8.py)` | Comment: part 1, the kernels of the reference. It is the code of `check_listing8.py`. |
| 316 | `    bad, r_places, g_places = 0, set(), set()` | `bad`: the count of failures that the summary line prints as `failed_rows`. It counts each kernel of the reference whose row fails, and 1 for each of the two checks over the whole listing that fails (lines 353 to 360). `r_places` and `g_places`: the places of the table of global addresses that the reference listing and the new listing use, over all kernels. |
| 317 | `    print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")` | Prints the column names of the output table of the reference kernels, with tabs between them: `kernel`, `start`, `loop_start`, `loop_mod64`, `ref_loop_mod64`, `text`, `result`. |
| 318 | `    for k in kernels:` | Loop over the kernels of the reference. |
| 319 | `        r_insns, insns = ref[(rb, k)], got.get((b, k), [])` | `r_insns`: the instructions of the kernel in the reference listing. `insns`: its instructions in the new listing, or an empty list when the new listing has no block for it. |
| 320 | `        r_mod = loop_start(r_insns) % 64` | `r_mod`: the loop start modulo 64 of the kernel in the reference listing. |
| 321 | `        loop = loop_start(insns) if insns else None` | Rule 1: `loop` is the loop start in the new listing. It is `None` when the block is missing or the function has no backward branch. |
| 322 | `        if loop is None:` | In that case ... |
| 323 | `            print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))` | ... the row says `FAIL: no listing or no loop`, with `NA` in the three columns of the new listing ... |
| 324 | `            bad += 1` | ... `bad` grows by 1 ... |
| 325 | `            continue` | ... and the loop goes to the next kernel. |
| 326 | `        problems, notes = [], []` | `problems` and `notes`: the texts for the result column of this kernel. |
| 327 | `        (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)` | Rule 2, the function text. `whole` (line 181) gives the text without addresses and the table places of the reference function (`r_text`, `r_got`) and of the new function (`text`, `g_got`). |
| 328 | `        same = text == r_text` | `same`: true when the two text lists are equal. They then hold the same number of instructions, and each instruction text is equal with every operand. |
| 329 | `        if not same:` | When the text is not equal ... |
| 330 | `            problems.append("function text differs from the reference")` | ... this is a problem. |
| 331 | `        else:` | When the text is equal: |
| 332 | `            r_places.update(r_got)` | The places of the reference function are added to `r_places` ... |
| 333 | `            g_places.update(g_got)` | ... and the places of the new function to `g_places`. |
| 334 | `            if len(set(g_got)) > len(set(r_got)):` | More distinct places in the new function than in the reference function ... |
| 335 | `                problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %` | ... is a problem. Its text gives the number of places of the new function ... |
| 336 | `                                (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))` | ... each place with its page and offset, and the number of the reference. |
| 337 | `            elif [o for _, o in g_got] != [o for _, o in r_got]:` | A new function with no more places than the reference, but with other offsets ... |
| 338 | `                notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))` | ... gets a note and not a failure. When the row has no failure, its result column then starts with `NOTE: got_offset_differs` in place of `ok`. No row of the accepted build of `bwx12` has this note [Ref1]. |
| 339 | `        if loop % 64 != r_mod:` | Rule 3: the loop start modulo 64 of the new listing must equal the reference value. |
| 340 | `            problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))` | If not, a problem gives both values. |
| 341 | `        if ref_off.get((rb, k)) != str(r_mod):` | Rule 4: the reference `offsets.tsv` must hold the reference value for this kernel. |
| 342 | `            problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))` | If not, a problem gives the value of the table, or `no row`. |
| 343 | `        if got_off.get((b, k)) != str(loop % 64):` | The new `offsets.tsv` must hold the value of the new listing. |
| 344 | `            problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))` | If not, a problem gives both values. |
| 345 | `        print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",` | Prints the row of the kernel: the kernel name, the function start and the loop start (hexadecimal addresses), the loop start modulo 64, the reference value, `same` or `DIFFERS` ... |
| 346 | `                                             "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))` | ... and the result: `FAIL:` with the problems, or `NOTE:` with the notes, or `ok`. |
| 347 | `        if not same:` | When the text differs ... |
| 348 | `            for i in range(max(len(text), len(r_text))):` | ... a loop over the positions of the longer text ... |
| 349 | `                g = text[i] if i < len(text) else "(none)"` | ... takes the new instruction text, or `(none)` past the end ... |
| 350 | `                w = r_text[i] if i < len(r_text) else "(none)"` | ... and the reference instruction text, or `(none)` past the end. |
| 351 | `                print("    %s %-40s \| reference %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` between them. The mark `!=` stands before a line that differs. |
| 352 | `        bad += bool(problems)` | `bad` grows by 1 when the kernel has a problem. |
| 353 | `    if len(g_places) > len(r_places):` | After the loop, a check over all kernels with equal text: the new listing may not use more distinct places of the table of global addresses than the reference. |
| 354 | `        print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %` | If it does, a line that starts with `FAIL:` gives the number of places of the new listing ... |
| 355 | `              (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))` | ... the places, and the number of the reference. |
| 356 | `        bad += 1` | `bad` grows by 1. |
| 357 | `    extra = sorted(k for bb, k in got if bb == b and k not in kernels and k not in NEW_LOOP)` | `extra`: the kernels of the new binary in the new listing that are not in the reference and not new kernels (keys of `NEW_LOOP`). |
| 358 | `    if extra:` | When there is such a kernel ... |
| 359 | `        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))` | ... a line that starts with `FAIL:` names them ... |
| 360 | `        bad += 1` | ... and `bad` grows by 1. |

### Function `main`: part 2, one output row per new kernel, and the exit status (lines 362 to 394)

| Line | Source | Explanation |
|---:|---|---|
| 362 | `    # Part 2: the kernels of round 5` | Comment: part 2, the kernels of round 5. |
| 363 | `    new_bad = 0` | `new_bad`: the count of the failures of part 2. |
| 364 | `    if skip_new:` | With the option `--skip-new` ... |
| 365 | `        print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))` | ... the script prints the summary line here, with the words `new_kernels=NOT CHECKED (--skip-new)` ... |
| 366 | `        return 1 if bad else 0` | ... and returns 1 when part 1 has a failure, else 0. The new kernels are then not checked. |
| 367 | `    like_mod = {}` | `like_mod`: a dictionary from the name of an original kernel to its loop start modulo 64 in the new listing. |
| 368 | `    for name in sorted({sp["like"] for sp in NEW.values()}):` | Loop over the originals that `NEW` names in the field `like`, each one once, in sorted order. These are `asmcopy`, `asmread` and `asmwrite`. |
| 369 | `        orig = got.get((b, name), [])` | `orig`: the instructions of the original in the new listing, or an empty list. |
| 370 | `        orig_loop = loop_start(orig) if orig else None` | `orig_loop`: its loop start, or `None` when the kernel is missing or has no loop. |
| 371 | `        like_mod[name] = None if orig_loop is None else orig_loop % 64` | Stores the loop start modulo 64, or `None`. |
| 372 | `    print("new_kernel\tstart\tloop_start\tloop_mod64\toriginal_loop_mod64\tloop\tresult")` | Prints the column names of the second output table: `new_kernel`, `start`, `loop_start`, `loop_mod64`, `original_loop_mod64`, `loop`, `result`. |
| 373 | `    for k in NEW_LOOP:` | Loop over the new kernels. |
| 374 | `        insns = got.get((b, k), [])` | `insns`: the instructions of the kernel in the new listing, or an empty list. |
| 375 | `        want_mod = like_mod[NEW[k]["like"]]` | `want_mod`: the loop start modulo 64 of the original of this kernel. |
| 376 | `        if not insns:` | Every new kernel must have a block in the new listing. If it has none ... |
| 377 | `            print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))` | ... the row says `FAIL: no listing` ... |
| 378 | `            new_bad += 1` | ... `new_bad` grows by 1 ... |
| 379 | `            continue` | ... and the loop goes to the next kernel. |
| 380 | `        problems = new_problems(k, insns, want_mod, got_off.get((b, k)))` | `new_problems` (line 208) applies the rules of part 2 and returns the problems of this kernel. |
| 381 | `        loop = loop_start(insns)` | `loop`: the loop start of the kernel, for the row. |
| 382 | `        print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,` | Prints the row of the kernel. The call goes on to line 386. This line: the kernel name, the function start and the loop start (hexadecimal addresses, `NA` without a loop) ... |
| 383 | `                                               "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,` | ... the loop start modulo 64, and the value of the kernel to compare with (`NA` when it has none) ... |
| 384 | `                                               "DIFFERS" if any("loop instruction" in x or "loop branch" in x or "backward" in x or "nop, expected" in x` | ... and the sixth column. It says `DIFFERS` when a problem text holds one of four phrases. These phrases stand in the problems about the loop instructions, the `nop` count, the loop branch, another branch or call, and the number of backward branches. |
| 385 | `                                                                for x in problems) else "expected",` | Continues the test of line 384 over all problems of the kernel. Without such a problem the column says `expected`. Any other problem shows only in the result column. |
| 386 | `                                               "FAIL: " + "; ".join(problems) if problems else "ok"))` | Ends the call: the result column is `FAIL:` with the problems, or `ok`. |
| 387 | `        new_bad += bool(problems)` | `new_bad` grows by 1 when the kernel has a problem. |
| 388 | `    print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %` | Prints the summary line. For the accepted build of `bwx12` it is `# binary=bwx12 reference=bwx11 kernels=29 failed_rows=0 new_kernels=26 new_failed_rows=0` [Ref1]. |
| 389 | `          (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))` | Continues the call of line 388: the values of the line. They are the two binary names, the number of reference kernels, the failures of part 1, the number of new kernels and the failures of part 2. |
| 390 | `    return 1 if bad or new_bad else 0` | `main` returns 1 when a check of part 1 or of part 2 failed, and 0 when none failed. |
| 393 | `if __name__ == "__main__":` | This test is true when the file runs as a script. |
| 394 | `    sys.exit(main())` | Calls `main` and makes its return value the exit status of the script. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/check_listing12.out`: the saved output of this script for the build in `crb-build-1`. Lines 2 to 30 are the 29 rows of part 1. Lines 32 to 57 are the 26 rows of part 2. Line 58 is the summary line.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: the checked listing. The blocks of the six kernels of the whole-chip test start at these lines: `read` 1, `asmread` 59, `oldread` 133, `read_1pl` 754, `read_nop96` 854, `read_nop256` 2126. The `adrp` and `bl` instructions are at lines 137, 189, 204, 313, 365 and 380.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/ref-bwx11/`: the reference files `listing.txt` and `offsets.tsv`. A `cmp` in this task found them equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx11-2026-11-15/crb-build-1/`. The `adrp` instructions of the reference listing are at lines 137, 189, 313 and 365.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: lines 20 to 22 hold the sha256 values of `bwx12`, `listing.txt` and `offsets.tsv`. Line 24 holds the end time of the build, 2026-11-15T17:12:14Z.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: line 13 holds the sha256 value of `bwx12` that line 20 of `build.txt` records. Line 23 stops the driver when the binary has another value. `go2.sh` in the same folder holds the same value in line 10 and makes the same check in line 19.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 57 to 75 write `listing.txt` and `offsets.tsv`. Line 21 says that no script uses `seq-listing.txt`. Line 22 names this script as the next step.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 3 to 11 and line 1080: `bwx12.c` is `bwx11.c` plus the additions of round 5. The additions are 26 kernels.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md`: line 141, section "Fixed setup": the design rule that a build is rejected when its acceptance listing differs. Lines 2 and 3 of the script cite it.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 605 to 641, macro `DEF_ASMREAD`: a kernel takes a pointer and a count of 8-byte words. The list of changed registers makes gcc save d8 to d15 outside the loop.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 90 to 94 name the two modes: `--seq` for the interval mode, `--trial` for the trial mode. Lines 2913 and 2914 send a command line with `--trial` to `trial_main`. Function `worker` (from line 1632) is the thread of the interval mode: with the option `--stop common` of the whole-chip test it reads the start time of an interval in line 1688. It calls the kernel through `call` in line 1695 and reads the clock after each call in line 1700. The last of these clock reads is the end time of the interval. Line 1491 defines `call`. Lines 1995 and 2056 define `timed_sequence` and `timed_sequence_hot`. Their only calls are in lines 2206 and 2209, in the function `run_trial` of the trial mode.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/`: the files `like.spec`, `cfwd.spec` and `crev.spec` hold the arguments of the `bwx12` processes of the whole-chip test. Each one has `--seq` and no `--trial`. Together the three `--seq` lists name the six kernels `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`.
