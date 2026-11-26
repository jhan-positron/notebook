# `check_listing12.py` explained

- Source file: `check_listing12.py` in this folder (Python script, 394 lines, 20994 bytes).
- sha256 of the source when this page was built: `cf8c3cd2cdb393f3a1a324c72dd3db78657dec3cd6ce635d0c46e236df41af9c`.
- Role in the whole-chip test: Acceptance check of the bwx12 kernel machine code, run after the build.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Documentation text: what the script is</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env python3
  2  """check_listing12.py - acceptance test of a bwx12 build (design tackle-8mb.md,
  3  "Fixed setup": reject a build whose acceptance listing differs).
  4
  5  It is check_listing11.py with another reference and other new kernels. The
  6  code of part 1 is unchanged.
  7</pre></td><td valign="top"><ul><li>Lines 2 to 78 are the documentation text of the script. Python does not execute it. <code>main</code> prints it when it finds too many arguments or an unknown option (line 293).</li><li>The script accepts or rejects a build of the runner program <code>bwx12</code>. Its input is the machine code of every kernel, as text.</li><li>Line 3 cites the design rule that a build is rejected when its acceptance listing differs [Ref8].</li><li><code>check_listing11.py</code> is the script of the same kind in the folder of <code>bwx11</code>, the runner version before <code>bwx12</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  8  Runs on the development machine, on the listing.txt and offsets.tsv that
  9  build12.sh wrote on CRB.
 10  Usage: check_listing12.py [listing.txt [offsets.tsv]]
 11             [--ref-listing F] [--ref-offsets F] [--binary bwx12] [--ref-binary bwx11] [--skip-new]
 12
 13  The reference is the accepted build of bwx11 (crb-build-1 of the folder
 14  bwx11-2026-11-15), saved in ref-bwx11/listing.txt and ref-bwx11/offsets.tsv
 15  beside this script, binary "bwx11".
 16</pre></td><td valign="top"><ul><li>The script runs on the development machine, not on CRB.</li><li>It reads <code>listing.txt</code> and <code>offsets.tsv</code>. The script <code>build12.sh</code> wrote both files on CRB [Ref6].</li><li>Both file arguments are optional. Lines 295 and 296 set the defaults.</li><li>The reference is a saved copy of the same two files from the accepted build of <code>bwx11</code>. The copies are equal, byte for byte, to the files in the build folder of <code>bwx11</code> [Ref3].</li></ul></td></tr>
<tr><td colspan="2"><b>Documentation text: part 1, the 29 kernels of the reference</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 17  Part 1, the 29 kernels of the reference binary. The rules are the rules of
 18  check_listing11.py part 1 (which are the rules of check_listing8.py),
 19  unchanged. For every kernel of the reference:
 20   1. the new listing has the kernel, and the function has a loop;
 21   2. the whole function text equals the reference text, apart from addresses;
 22   3. the loop start modulo 64 equals the reference value. Both are computed
 23      from the listings;
 24   4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as
 25      the new listing and as the row of the reference offsets.tsv.
 26</pre></td><td valign="top">Part 1 covers the kernels that <code>bwx11</code> already had. Five of the six kernels of the whole-chip test are among them: <code>oldread</code>, <code>read</code>, <code>asmread</code>, <code>read_nop96</code> and <code>read_1pl</code>.<ul><li>Rule 1: lines 321 to 325.</li><li>Rule 2: lines 327 to 330.</li><li>Rule 3: lines 339 and 340.</li><li>Rule 4: lines 341 to 344.</li></ul>"Loop start modulo 64" is the remainder of the loop start address divided by 64.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 27  What "apart from addresses" means here:
 28   - an instruction address is not compared;
 29   - a branch target inside the function is compared as its distance from the
 30     function start;
 31   - a target outside the function (the stub of bl, the page of a single adrp)
 32     is compared by its symbol name, not by its address;
 33   - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from
 34     the table of global addresses of the binary. In the reference only the
 35     load of the stack-guard pointer has this form. Page and offset are the
 36     place of the pointer in that table. The linker sets them, so they are not
 37     compared with the reference. The pair is accepted only where the reference
 38     has it, because the rest of the text must be equal. The listing does not
 39     name the pointer. So this is checked: the new listing must not use more
 40     places of the table than the reference, per function and over all
 41     kernels. The reference uses one place. A row whose offset differs from the
 42     reference prints "NOTE: got_offset_differs" in place of "ok": read it.
 43  The loop of a function is the range from the target of its first backward
 44  branch to that branch.
 45</pre></td><td valign="top">These lines define how two functions at different addresses are compared. The function <code>whole</code> (line 181) implements it.<ul><li><code>bl</code> is the call instruction. The listing has 2 <code>bl</code> instructions, one in <code>oldread</code> and one in <code>oldread2</code>. Both call <code>__stack_chk_fail@plt</code>, the function for a failed stack guard [Ref2].</li><li><code>adrp</code> puts the address of a 4096-byte page into a register. The <code>ldr</code> after it loads a pointer from that page.</li><li>The "table of global addresses" holds addresses of global objects of the binary. The linker sets the page and the offset of an entry. So the script does not compare them with the reference.</li><li>Lines 43 and 44 define the loop. The function <code>loop_start</code> (line 171) finds its first address.</li></ul></td></tr>
<tr><td colspan="2"><b>Documentation text: part 2, the 26 new kernels</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 46  Part 2, the 26 kernels of round 5 (the keys of NEW below). The reference does
 47  not have them. All 26 must be in the new listing. For each one:
 48   1. the function has exactly one backward branch, and no other branch or call;
 49   2. the instructions of the loop equal the expected list (the field "loop" of
 50      NEW), with every operand. The loop ends with b.cc (the same instruction
 51      as b.lo) to the loop start. The expected lists:
 52        read_nopN       the 8 ldp of asmread, N nop, add #256, cmp
 53        read_daddK      the 8 ldp, K "add vA.2d, vA.2d, vL.2d" with vL a
 54                        register that the 8 ldp loaded, add #256, cmp
 55        read_iadd16     the 8 ldp, 16 "add vA.2d, vA.2d, vB.2d" with vB one of
 56                        v24-v31, add #256, cmp
 57        read_spN        the 4 ldp of read_sparse, N nop, add #128, cmp
 58        read_1pl_nop96  the 4 ldr of read_1pl, 96 nop, add #256, cmp
 59        write_nopN      the 8 stp of asmwrite, N nop, add #256, cmp
 60        copy_nopN       the 8 ldp and 8 stp of asmcopy, N nop, the two add, cmp</pre></td><td valign="top">Part 2 covers the kernels that <code>bwx12</code> adds to <code>bwx11</code>. The whole-chip test runs one of them: <code>read_nop256</code>. The function <code>new_problems</code> (line 208) implements the five rules.<ul><li>"Round 5" is the name in <code>bwx12.c</code> for these 26 additions [Ref7]. It is not a round of a kernel sequence.</li><li>Rule 1: lines 214 to 225.</li><li>Rule 2: lines 226 to 238. Lines 91 to 131 build the expected lists.</li><li><code>ldp</code> loads a pair of registers. <code>stp</code> stores a pair. <code>nop</code> does nothing.</li><li><code>b.cc</code> and <code>b.lo</code> are two names of one branch instruction. After <code>cmp x0, x1</code> it jumps when <code>x0</code> is below <code>x1</code> (unsigned compare).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 61   3. the instructions before the loop are: the computation of the end pointer
 62      (once), stores of d registers to the stack, and the instructions of the
 63      field "init" in their order (the movi of the add kernels, the dup of the
 64      write kernels), and nothing else. Every instruction after the loop is a
 65      load of d registers from the stack, and the last one is ret;
 66   4. every register from v8 to v15 that the loop uses is stored before the
 67      loop and loaded after it (d8-d15 are callee-saved);
 68   5. the loop start modulo 64 equals the planned value (20 for a read kernel,
 69      40 for a write kernel, 52 for a copy kernel), it equals the loop start
 70      modulo 64 of the original in the same listing (asmread, asmwrite or
 71      asmcopy), and the row in offsets.tsv gives the same value.
 72  Any other kernel that the reference lacks is a failure.
 73</pre></td><td valign="top"><ul><li>Rule 3: lines 239 to 259.</li><li>Rule 4: lines 260 to 265. A callee-saved register must hold the same value when the function returns as when it was called. A kernel whose loop loads into q8 to q15 must store d8 to d15 before the loop and reload them after it.</li><li>Rule 5: lines 266 to 273.</li><li>Line 72 is implemented in lines 357 to 360.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 74  --skip-new leaves out part 2. It is only for a build on a machine that is not
 75  AArch64, where the new kernels are plain C stand-in loops. The last line then
 76  says that the new kernels were NOT CHECKED.
 77  Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.
 78  """</pre></td><td valign="top"><ul><li><code>--skip-new</code> was not used for the accepted build of <code>bwx12</code>. The summary line of the saved output says <code>new_kernels=26</code>, not <code>NOT CHECKED</code> [Ref1].</li><li>The exit status is the return value of <code>main</code> (line 394).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 79  import os
 80  import re
 81  import sys
 82
 83  HERE = os.path.dirname(os.path.abspath(__file__))
 84  REF_DIR = os.path.join(HERE, "ref-bwx11")
 85  TARGET = re.compile(r"\b([0-9a-f]+) &lt;[^&gt;]+&gt;$")
 86</pre></td><td valign="top"><ul><li><code>HERE</code> is the folder of this script. <code>REF_DIR</code> is its subfolder <code>ref-bwx11</code>.</li><li><code>TARGET</code> is a text pattern for a branch target at the end of an instruction: a hexadecimal address, a space and a name in angle brackets. Example: <code>49a4 &lt;k_read+0x4&gt;</code>. The pattern captures the address. The page operand of an <code>adrp</code> instruction has the same form. The pattern matches it too. Example: <code>2f000 &lt;__FRAME_END__+0x16a34&gt;</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Expected instruction lists of the new kernels</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 87  # The loop of each new kernel, as objdump prints it (one space between the
 88  # fields). x0 is the pointer and x1 is the end, as in every asm read and write
 89  # kernel of the reference. A copy kernel has the destination in x0, the source
 90  # in x1 and the end in x2. The loop branch stands after these instructions.
 91  LDP8 = ["ldp q0, q1, [x0]", "ldp q2, q3, [x0, #32]", "ldp q4, q5, [x0, #64]", "ldp q6, q7, [x0, #96]",
 92          "ldp q8, q9, [x0, #128]", "ldp q10, q11, [x0, #160]", "ldp q12, q13, [x0, #192]", "ldp q14, q15, [x0, #224]"]
 93  STEP = ["add x0, x0, #0x100", "cmp x0, x1"]
 94  STEP128 = ["add x0, x0, #0x80", "cmp x0, x1"]
 95  LDR4 = ["ldr q0, [x0]", "ldr q1, [x0, #64]", "ldr q2, [x0, #128]", "ldr q3, [x0, #192]"]</pre></td><td valign="top">The lists hold instruction text in the form that the function <code>sections</code> (line 138) produces: one space between the fields.<ul><li><code>LDP8</code>: the 8 <code>ldp</code> instructions of <code>asmread</code>. Each one loads two 16-byte registers. Together they load q0 to q15 from the 256 bytes at the pointer <code>x0</code>.</li><li><code>STEP</code>: add 256 bytes (<code>#0x100</code>) to <code>x0</code>, then compare <code>x0</code> with the end pointer <code>x1</code>. <code>STEP128</code> adds 128 bytes (<code>#0x80</code>).</li><li><code>LDR4</code>: 4 <code>ldr</code> instructions. Each one loads 16 bytes. The offsets from <code>x0</code> are 0, 64, 128 and 192 bytes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 96  STP8 = ["stp q0, q0, [x0%s]" % ("" if o == 0 else ", #%d" % o) for o in range(0, 256, 32)]
 97  COPY_LDP8 = [t.replace("[x0", "[x1") for t in LDP8]
 98  COPY_STP8 = [t.replace("ldp", "stp") for t in LDP8]
 99  COPY_STEP = ["add x1, x1, #0x100", "add x0, x0, #0x100", "cmp x1, x2"]
100  END_POINTER = "add x1, x0, x1, lsl #3"
101  COPY_END_POINTER = "add x2, x1, x2, lsl #3"
102  ACC_ZERO = ["movi v%d.4s, #0x0" % r for r in range(16, 24)]
103  CONST_ONE = ["movi v%d.4s, #0x1" % r for r in range(24, 32)]
104
105</pre></td><td valign="top"><ul><li><code>STP8</code>: 8 <code>stp</code> instructions. Each one stores q0 twice (32 bytes). The offsets from <code>x0</code> are 0, 32 and so on up to 224 bytes.</li><li><code>COPY_LDP8</code>: <code>LDP8</code> with the source pointer <code>x1</code>. <code>COPY_STP8</code>: 8 <code>stp</code> that store q0 to q15 at the destination pointer <code>x0</code>.</li><li><code>COPY_STEP</code>: add 256 bytes to both pointers, then compare the source pointer with the end pointer <code>x2</code>.</li><li><code>END_POINTER</code>: the instruction before the loop that computes the end address: pointer plus 8 times the second argument. The second argument of a kernel is a count of 8-byte words [Ref9]. <code>lsl #3</code> shifts it left by 3 bits.</li><li><code>COPY_END_POINTER</code>: the same instruction with the registers of a copy kernel.</li><li><code>ACC_ZERO</code>: 8 <code>movi</code> that set v16 to v23 to zero. <code>CONST_ONE</code>: 8 <code>movi</code> that set each 32-bit lane of v24 to v31 to 1.</li></ul></td></tr>
<tr><td colspan="2"><b>Functions <code>vadd</code> and <code>spec</code>: build one expectation</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">106  def vadd(pairs):
107      return ["add v%d.2d, v%d.2d, v%d.2d" % (a, a, b) for a, b in pairs]
108
109
110  def spec(loop, mod, like, init=(), end=END_POINTER):
111      """loop: the instructions of the loop before its branch; mod: the planned loop start modulo 64; like: the
112      kernel of the reference whose loop offset this kernel must have; init: the instructions before the loop
113      beside the end pointer and the stores of d registers; end: the computation of the end pointer"""
114      return {"loop": loop, "mod": mod, "like": like, "init": list(init), "end": end}
115
116</pre></td><td valign="top"><ul><li><code>vadd</code> turns pairs of register numbers (a, b) into the instruction texts <code>add va.2d, va.2d, vb.2d</code>. This instruction adds the two 64-bit lanes of register b to register a.</li><li><code>spec</code> returns the expectation of one new kernel as a dictionary with 5 fields.</li><li><code>loop</code>: the loop instructions without the loop branch. <code>mod</code>: the planned loop start modulo 64.</li><li><code>like</code>: the older kernel that must have the same loop start modulo 64 in the same listing.</li><li><code>init</code>: the extra instructions before the loop. <code>end</code>: the end-pointer instruction.</li></ul></td></tr>
<tr><td colspan="2"><b>Table <code>NEW</code>: the 26 new kernels and their expected loops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">117  NEW = {}
118  for _n in (48, 56, 72, 80, 88, 112, 160, 192, 256):
119      NEW["read_nop%d" % _n] = spec(LDP8 + ["nop"] * _n + STEP, 20, "asmread")
120  NEW["read_dadd2"] = spec(LDP8 + vadd([(16, 0), (17, 8)]) + STEP, 20, "asmread", ACC_ZERO)
121  NEW["read_dadd4"] = spec(LDP8 + vadd([(16, 0), (17, 4), (18, 8), (19, 12)]) + STEP, 20, "asmread", ACC_ZERO)
122  NEW["read_dadd8"] = spec(LDP8 + vadd([(16 + i, 2 * i) for i in range(8)]) + STEP, 20, "asmread", ACC_ZERO)
123  NEW["read_dadd16"] = spec(LDP8 + vadd([(16 + i % 8, i) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO)
124  NEW["read_iadd16"] = spec(LDP8 + vadd([(16 + i % 8, 24 + i % 8) for i in range(16)]) + STEP, 20, "asmread", ACC_ZERO + CONST_ONE)
125  for _n in (24, 32, 40, 48, 56):
126      NEW["read_sp%d" % _n] = spec(LDP8[:4] + ["nop"] * _n + STEP128, 20, "asmread")
127  NEW["read_1pl_nop96"] = spec(LDR4 + ["nop"] * 96 + STEP, 20, "asmread")
128  for _n in (32, 96, 128, 256):
129      NEW["write_nop%d" % _n] = spec(STP8 + ["nop"] * _n + STEP, 40, "asmwrite", ["dup v0.2d, x2"])
130  for _n in (96, 192):
131      NEW["copy_nop%d" % _n] = spec(COPY_LDP8 + COPY_STP8 + ["nop"] * _n + COPY_STEP, 52, "asmcopy", end=COPY_END_POINTER)
132  NEW_LOOP = NEW  # the name that the code of part 1 uses for "is a new kernel"</pre></td><td valign="top"><ul><li>Lines 118 and 119: 9 kernels <code>read_nopN</code>. The loop is <code>LDP8</code>, N <code>nop</code>, <code>STEP</code>. The whole-chip test runs <code>read_nop256</code> (N = 256).</li><li>Lines 120 to 123: <code>read_dadd2</code> to <code>read_dadd16</code>. After the loads come 2 to 16 vector adds. Each add takes a register that the loads of the same loop pass filled.</li><li>Line 124: <code>read_iadd16</code>. Its 16 adds take the constant registers v24 to v31, not a loaded register.</li><li>Lines 125 to 127: 5 kernels <code>read_spN</code> (4 <code>ldp</code>, 128 bytes per loop pass, N <code>nop</code>) and <code>read_1pl_nop96</code> (<code>LDR4</code>, 96 <code>nop</code>).</li><li>Lines 128 to 131: 4 write kernels (planned loop start modulo 64: 40 bytes, original <code>asmwrite</code>) and 2 copy kernels (planned 52 bytes, original <code>asmcopy</code>). Every read kernel has the planned value 20 bytes and the original <code>asmread</code>.</li><li>Line 132: <code>NEW_LOOP</code> is a second name for the same table.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">133  SAVE = re.compile(r"(?:stp d(\d+), d(\d+)|str d(\d+)), \[sp(?:, #-?\d+)?\]!?")
134  RESTORE = re.compile(r"(?:ldp d(\d+), d(\d+)|ldr d(\d+)), \[sp(?:, #\d+)?\](?:, #\d+)?")
135  BRANCH = re.compile(r"(b|bl|br|blr|b\.[a-z]+|cbn?z|tbn?z)\b")
136
137</pre></td><td valign="top"><ul><li><code>SAVE</code> matches a store of one or two d registers to the stack, for example <code>stp d8, d9, [sp, #-64]!</code>. It captures the register numbers.</li><li><code>RESTORE</code> matches a load of one or two d registers from the stack, for example <code>ldp d8, d9, [sp], #64</code>.</li><li><code>BRANCH</code> matches the name of a branch or call instruction at the start of the text: <code>b</code>, <code>bl</code>, <code>br</code>, <code>blr</code>, a conditional <code>b.xx</code>, <code>cbz</code>, <code>cbnz</code>, <code>tbz</code>, <code>tbnz</code>. It does not match <code>ret</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>sections</code>: read a listing file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">138  def sections(path):
139      """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""
140      out, cur = {}, None
141      with open(path) as f:
142          for line in f:
143              m = re.match(r"=== (\S+) (\S+) ===", line)
144              if m:
145                  cur = out.setdefault((m.group(1), m.group(2)), [])
146                  continue
147              m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)
148              if m and cur is not None:
149                  text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()
150                  cur.append((int(m.group(1), 16), text))
151              elif line.startswith("##"):
152                  cur = None
153      return out
154
155</pre></td><td valign="top">Returns a dictionary. The key is the pair (binary, kernel). The value is the list of (address, instruction text) of that kernel function, in file order.<ul><li>Lines 143 to 146: a line such as <code>=== bwx12 read ===</code> starts the block of one kernel.</li><li>Line 147: an instruction line holds a hexadecimal address, a colon and the instruction. The function header <code>00000000000049a0 &lt;k_read&gt;:</code> does not match and is skipped.</li><li>Line 149: the objdump comment after <code>//</code> is cut off. Each run of spaces and tabs becomes one space.</li><li>Lines 151 and 152: a line that starts with <code>##</code> ends the current block.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>offsets</code>: read offsets.tsv</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">156  def offsets(path):
157      """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""
158      out = {}
159      with open(path) as f:
160          head = f.readline().rstrip("\n").split("\t")
161          if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:
162              raise ValueError("%s: unexpected header line" % path)
163          for line in f:
164              p = line.rstrip("\n").split("\t")
165              if len(p) != 6:
166                  raise ValueError("%s: a row with %d fields" % (path, len(p)))
167              out[(p[0], p[1])] = p[5]
168      return out
169
170</pre></td><td valign="top">Returns a dictionary from (binary, kernel) to the text of column 6, <code>loop_mod64</code>.<ul><li>Lines 160 to 162: the first line must hold exactly the 6 column names, separated by tab characters.</li><li>Lines 163 to 166: every other line must have 6 fields.</li><li>A wrong header or row raises <code>ValueError</code>. <code>main</code> then ends with exit status 2 (lines 300 to 302).</li><li>The script uses columns 1, 2 and 6 only. It ignores the columns <code>function</code>, <code>start</code> and <code>loop_start</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>loop_start</code>: first address of the loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">171  def loop_start(insns):
172      """address of the loop start: the target of the first backward branch into the function, or None"""
173      first = insns[0][0]
174      for addr, text in insns:
175          m = TARGET.search(text)
176          if m and first &lt;= int(m.group(1), 16) &lt; addr:
177              return int(m.group(1), 16)
178      return None
179
180</pre></td><td valign="top"><ul><li>Goes through the instructions in order. It returns the target of the first branch whose target lies inside the function and before the branch itself (<code>first &lt;= target &lt; addr</code>). This address is the loop start.</li><li>It returns <code>None</code> when the function has no such branch.</li><li><code>main</code> computes every loop start modulo 64 of part 1 as <code>loop_start(...) % 64</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>whole</code>: function text without addresses</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">181  def whole(insns):
182      """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""
183      first, last, out, got = insns[0][0], insns[-1][0], [], []
184      adrp_reg = adrp_page = None
185      for _, text in insns:
186          m = TARGET.search(text)
187          page = None
188          if m and first &lt;= int(m.group(1), 16) &lt;= last:
189              text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)
190          elif m:
191              page = m.group(1)
192              text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]</pre></td><td valign="top">Returns two lists: the instruction texts without addresses (<code>out</code>), and the places of the pointer loads from the table of global addresses (<code>got</code>).<ul><li>Lines 188 and 189: a branch target inside the function becomes its distance from the function start. Example: <code>b.hi 49a4 &lt;k_read+0x4&gt;</code> becomes <code>b.hi +0x4</code>.</li><li>Lines 190 to 192: a target outside the function becomes <code>(outside &lt;name&gt;)</code>. The name is kept. The address is removed. Example: <code>bl (outside &lt;__stack_chk_fail@plt&gt;)</code>. <code>page</code> keeps the address text for line 199.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">193          load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)
194          if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:
195              got.append((adrp_page, load.group(3)))
196              out[-1] = "adrp %s, (table page)" % adrp_reg
197              text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)
198          m = re.match(r"adrp (x\d+), ", text)
199          adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)
200          out.append(text)
201      return out, got
202
203</pre></td><td valign="top">These lines handle the pair <code>adrp xN, page</code> and <code>ldr xN, [xN, #offset]</code> with one register xN.<ul><li>Line 195 records the place (page, offset) in <code>got</code>.</li><li>Lines 196 and 197 replace both texts by fixed texts: <code>adrp xN, (table page)</code> and <code>ldr xN, [xN, #(table)]</code>. So page and offset are not part of the text comparison.</li><li>Lines 198 and 199 remember the register and the page of an <code>adrp</code> for the next instruction only.</li></ul>In both listings only <code>oldread</code> and <code>oldread2</code> have this pair. Each has it twice, with the page address <code>2f000</code> (hexadecimal) and the offset 4072 bytes [Ref2] [Ref3].</td></tr>
<tr><td colspan="2"><b>Function <code>numbers</code>: register numbers of one match</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">204  def numbers(match):
205      return {int(g) for g in match.groups() if g is not None}
206
207</pre></td><td valign="top">Returns the set of register numbers that one <code>SAVE</code> or <code>RESTORE</code> match captured.</td></tr>
<tr><td colspan="2"><b>Function <code>new_problems</code>: the five rules of part 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">208  def new_problems(kernel, insns, want_mod, off_row):
209      """Part 2 for one new kernel. want_mod: the loop start modulo 64 of the original (the field "like") in the
210      same listing, or None."""
211      p = []
212      sp = NEW[kernel]
213      first = insns[0][0]
214      back = [i for i, (addr, text) in enumerate(insns)
215              if TARGET.search(text) and first &lt;= int(TARGET.search(text).group(1), 16) &lt;= addr]
216      if len(back) != 1:
217          return ["%d backward branches, 1 expected" % len(back)]
218      end = back[0]
219      loop = int(TARGET.search(insns[end][1]).group(1), 16)
220      begin = next((i for i, (addr, _) in enumerate(insns) if addr == loop), None)
221      if begin is None:
222          return ["the loop branch goes to %x, which is not the address of an instruction" % loop]
223      others = [text for i, (_, text) in enumerate(insns) if i != end and BRANCH.match(text)]
224      if others:
225          p.append("a branch or call beside the loop branch: %s" % "; ".join(others))</pre></td><td valign="top">Returns a list of problem texts for one new kernel. An empty list says that the kernel passed.<ul><li>Lines 214 to 217: <code>back</code> lists every instruction that has a branch target inside the function, at or before its own address. Exactly 1 is required. If not, the function returns immediately with this one problem.</li><li>Lines 218 to 222: <code>end</code> is the index of that branch. <code>loop</code> is its target address. <code>begin</code> is the index of the instruction at that address. If no instruction has that address, the function returns with one problem.</li><li>Lines 223 to 225 (rule 1): any other instruction that <code>BRANCH</code> matches is a problem. The <code>ret</code> at the end is not a problem.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">226      body, want = [text for _, text in insns[begin:end]], sp["loop"]
227      if body != want:
228          # the count of nop first: one line says what is wrong with a loop of the wrong length
229          if body.count("nop") != want.count("nop"):
230              p.append("the loop has %d nop, expected %d" % (body.count("nop"), want.count("nop")))
231          diff = [i for i in range(max(len(body), len(want))) if (body[i] if i &lt; len(body) else "(none)") != (want[i] if i &lt; len(want) else "(none)")]
232          for i in diff[:3]:
233              p.append("loop instruction %d is '%s', expected '%s'" % (i, body[i] if i &lt; len(body) else "(none)",
234                                                                     want[i] if i &lt; len(want) else "(none)"))
235          if len(diff) &gt; 3:
236              p.append("%d more loop instructions differ" % (len(diff) - 3))
237      if not re.fullmatch(r"b\.(cc|lo) %x &lt;k_%s\+0x%x&gt;" % (loop, re.escape(kernel), loop - first), insns[end][1]):
238          p.append("the loop branch is '%s', expected b.cc (b.lo) to the loop start" % insns[end][1])</pre></td><td valign="top">Rule 2.<ul><li>Line 226: <code>body</code> is the instruction text from the loop start to the instruction before the loop branch. <code>want</code> is the expected list from <code>NEW</code>.</li><li>Line 227: the two lists must be equal. So the count, the order, and every register and offset of the loop instructions are compared.</li><li>Lines 228 to 236 only write the messages: the <code>nop</code> count if it differs, the first 3 differing instructions, and the number of further ones.</li><li>Lines 237 and 238: the loop branch must be <code>b.cc</code> or <code>b.lo</code>. The name after its target address must be <code>k_</code> plus the kernel name, plus the distance of the loop start from the function start.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">239      head, tail = [text for _, text in insns[:begin]], [text for _, text in insns[end + 1:]]
240      saved, restored, init = set(), set(), []
241      for text in head:
242          m = SAVE.fullmatch(text)
243          if m:
244              saved |= numbers(m)
245          elif text != sp["end"]:
246              init.append(text)
247      if head.count(sp["end"]) != 1:
248          p.append("before the loop: '%s' stands %d times, 1 expected" % (sp["end"], head.count(sp["end"])))
249      if init != sp["init"]:
250          p.append("before the loop, beside the end pointer and the stores of d registers: '%s', expected '%s'" %
251                   ("; ".join(init) or "nothing", "; ".join(sp["init"]) or "nothing"))</pre></td><td valign="top">Rule 3, before the loop. <code>head</code> holds the instructions before the loop start. <code>tail</code> holds the instructions after the loop branch.<ul><li>Lines 241 to 246: an instruction that <code>SAVE</code> matches adds its register numbers to <code>saved</code>. Every other instruction, apart from the end-pointer instruction, is added to the list <code>init</code>.</li><li>Lines 247 and 248: the end-pointer instruction must occur exactly 1 time.</li><li>Lines 249 to 251: <code>init</code> must equal the field <code>init</code> of the expectation, in the same order. For <code>read_nop256</code> this field is empty. So only stores of d registers and the end-pointer instruction may stand before its loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">252      if not tail or tail[-1] != "ret":
253          p.append("the function does not end with ret")
254      for text in tail[:-1]:
255          m = RESTORE.fullmatch(text)
256          if m:
257              restored |= numbers(m)
258          else:
259              p.append("after the loop: '%s' is not a load of d registers from the stack" % text)
260      used = {int(n) for text in body for n in re.findall(r"\b[qvd](\d+)\b", text) if 8 &lt;= int(n) &lt;= 15}
261      if used - saved or used - restored:
262          p.append("the loop uses v%s; not stored before the loop: %s; not loaded after it: %s" %
263                   (",".join(str(n) for n in sorted(used)), sorted(used - saved) or "none", sorted(used - restored) or "none"))
264      if saved != restored:
265          p.append("d registers stored %s, loaded %s" % (sorted(saved), sorted(restored)))</pre></td><td valign="top">Rule 3, after the loop, and rule 4.<ul><li>Lines 252 to 259: the last instruction must be <code>ret</code>. Every instruction between the loop branch and <code>ret</code> must be a load that <code>RESTORE</code> matches.</li><li>Line 260: <code>used</code> holds the register numbers 8 to 15 that the loop names as a q, v or d register.</li><li>Lines 261 to 263: every register in <code>used</code> must be in <code>saved</code> and in <code>restored</code>.</li><li>Lines 264 and 265: the stored set and the reloaded set must be equal.</li><li>The script compares register numbers only. It does not compare the stack offset of a store with the stack offset of its reload.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">266      if want_mod is None:
267          p.append("%s has no loop in this listing, so the loop offset cannot be compared" % sp["like"])
268      elif loop % 64 != want_mod:
269          p.append("loop offset modulo 64 is %d, %s has %d" % (loop % 64, sp["like"], want_mod))
270      if loop % 64 != sp["mod"]:
271          p.append("loop offset modulo 64 is %d, planned %d" % (loop % 64, sp["mod"]))
272      if off_row != str(loop % 64):
273          p.append("offsets.tsv gives %s, the listing gives %d" % (off_row if off_row is not None else "no row", loop % 64))
274      return p
275
276</pre></td><td valign="top">Rule 5, the place of the loop. <code>loop % 64</code> is the loop start modulo 64 of this kernel.<ul><li>Lines 266 to 269: it must equal <code>want_mod</code>, the value of the original kernel (field <code>like</code>) in the same listing. <code>main</code> computes <code>want_mod</code> in lines 367 to 371 and line 375. When the original kernel has no loop in the listing, <code>want_mod</code> is <code>None</code>. This is also a problem.</li><li>Lines 270 and 271: it must equal the planned value of <code>NEW</code>.</li><li>Lines 272 and 273: the row of the kernel in <code>offsets.tsv</code> must hold the same number.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: arguments</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">277  def main():
278      args = sys.argv[1:]
279      opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),
280             "--binary": "bwx12", "--ref-binary": "bwx11"}
281      skip_new = "--skip-new" in args
282      if skip_new:
283          args.remove("--skip-new")
284      for name in opt:
285          if name in args:
286              i = args.index(name)
287              if i + 1 &gt;= len(args):
288                  print("%s needs a value" % name)
289                  return 2
290              opt[name] = args[i + 1]
291              del args[i:i + 2]
292      if len(args) &gt; 2 or any(a.startswith("--") for a in args):
293          print(__doc__)
294          return 2</pre></td><td valign="top"><ul><li>Lines 279 and 280: the defaults of the 4 options. The reference files are in <code>ref-bwx11</code>. The binary name is <code>bwx12</code>. The reference binary name is <code>bwx11</code>.</li><li>Lines 281 to 283: <code>--skip-new</code> is a flag without a value.</li><li>Lines 284 to 291: an option that is present takes the next argument as its value. Both are removed from the list. An option without a value ends the script with exit status 2.</li><li>Lines 292 to 294: more than 2 remaining arguments, or a remaining argument that starts with <code>--</code>, print the documentation text. The script then ends with exit status 2.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: read the files, refuse unusable input</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">295      listing = args[0] if args else os.path.join(HERE, "listing.txt")
296      offs = args[1] if len(args) &gt; 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")
297      try:
298          ref, got = sections(opt["--ref-listing"]), sections(listing)
299          ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)
300      except (OSError, ValueError) as e:
301          print("cannot use: %s" % e)
302          return 2
303      b, rb = opt["--binary"], opt["--ref-binary"]
304      kernels = [k for (bb, k) in ref if bb == rb]
305      if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):
306          print("the reference listing has no usable block of binary %s" % rb)
307          return 2
308      if any(k in NEW_LOOP for k in kernels):
309          print("the reference listing holds a kernel of round 5: it is not a listing of %s" % rb)
310          return 2
311      if not any(bb == b for bb, _ in got):
312          print("no '=== %s kernel ===' block in %s" % (b, listing))
313          return 2
314</pre></td><td valign="top"><ul><li>Lines 295 and 296: the listing is the first argument, or <code>listing.txt</code> in the folder of the script. The offsets table is the second argument, or <code>offsets.tsv</code> in the folder of the listing.</li><li>Lines 297 to 302: read the reference listing (<code>ref</code>), the new listing (<code>got</code>) and the two offsets tables. A file that cannot be opened, or an offsets table with a wrong form, ends the script with exit status 2.</li><li>Line 304: <code>kernels</code> lists the kernel names of the reference binary, in the order of the reference listing.</li><li>Lines 305 to 313: three more cases end with exit status 2. Case 1: the reference listing has no kernel of the reference binary, or a reference kernel has no instructions or no loop. Case 2: the reference holds a kernel of <code>NEW</code>. Case 3: the new listing has no block of the binary <code>bwx12</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Part 1: one output row per kernel of the reference</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">315      # Part 1: the kernels of the reference (the code of check_listing8.py)
316      bad, r_places, g_places = 0, set(), set()
317      print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")
318      for k in kernels:
319          r_insns, insns = ref[(rb, k)], got.get((b, k), [])
320          r_mod = loop_start(r_insns) % 64
321          loop = loop_start(insns) if insns else None
322          if loop is None:
323              print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))
324              bad += 1
325              continue</pre></td><td valign="top"><ul><li>Line 317 prints the column names of the first output table.</li><li>Line 320: <code>r_mod</code> is the loop start modulo 64 of the kernel in the reference listing.</li><li>Lines 321 to 325 (rule 1): the new listing must have a block for the kernel, and the function must have a backward branch. If not, the row says <code>FAIL: no listing or no loop</code>.</li><li><code>bad</code> counts the failures of part 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">326          problems, notes = [], []
327          (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)
328          same = text == r_text
329          if not same:
330              problems.append("function text differs from the reference")
331          else:
332              r_places.update(r_got)
333              g_places.update(g_got)
334              if len(set(g_got)) &gt; len(set(r_got)):
335                  problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %
336                                  (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))
337              elif [o for _, o in g_got] != [o for _, o in r_got]:
338                  notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))</pre></td><td valign="top">Rule 2, the function text.<ul><li>Lines 327 and 328: <code>whole</code> (line 181) gives the text without addresses of the reference function and of the new function. <code>same</code> is true when the two lists are equal: the same number of instructions, and each instruction text equal with every operand.</li><li>Lines 329 and 330: unequal text is a problem.</li><li>Lines 332 to 336: <code>r_got</code> and <code>g_got</code> are the places of the pointer loads from the table of global addresses. More distinct places in the new function than in the reference function is a problem.</li><li>Lines 337 and 338: a new function with no more places than the reference, but with other offsets, gets a note and not a failure. When the row has no failure, its result column then starts with <code>NOTE: got_offset_differs</code> in place of <code>ok</code>. No row of the accepted build of <code>bwx12</code> has this note [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">339          if loop % 64 != r_mod:
340              problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))
341          if ref_off.get((rb, k)) != str(r_mod):
342              problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))
343          if got_off.get((b, k)) != str(loop % 64):
344              problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))
345          print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",
346                                               "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))
347          if not same:
348              for i in range(max(len(text), len(r_text))):
349                  g = text[i] if i &lt; len(text) else "(none)"
350                  w = r_text[i] if i &lt; len(r_text) else "(none)"
351                  print("    %s %-40s | reference %s" % ("  " if g == w else "!=", g, w))
352          bad += bool(problems)</pre></td><td valign="top">Rules 3 and 4, then the output row.<ul><li>Lines 339 and 340: the loop start modulo 64 of the new listing must equal the reference value.</li><li>Lines 341 and 342: the reference <code>offsets.tsv</code> must hold the reference value.</li><li>Lines 343 and 344: the new <code>offsets.tsv</code> must hold the value of the new listing.</li><li>Lines 345 and 346 print the row: kernel, function start and loop start (hexadecimal addresses), loop start modulo 64, reference value, <code>same</code> or <code>DIFFERS</code>, and the result <code>ok</code>, <code>NOTE: ...</code> or <code>FAIL: ...</code>.</li><li>Lines 347 to 351: when the text differs, both texts are printed side by side. <code>!=</code> marks a line that differs.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">353      if len(g_places) &gt; len(r_places):
354          print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %
355                (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))
356          bad += 1
357      extra = sorted(k for bb, k in got if bb == b and k not in kernels and k not in NEW_LOOP)
358      if extra:
359          print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))
360          bad += 1
361</pre></td><td valign="top">Two checks over all kernels of part 1. Each failure adds 1 to <code>bad</code>.<ul><li>Lines 353 to 356: the places are collected over all kernels with equal text. The new listing may not use more distinct places of the table of global addresses than the reference.</li><li>Lines 357 to 360: a kernel of <code>bwx12</code> in the new listing is a failure when it is not in the reference and not in <code>NEW</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Part 2: one output row per new kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">362      # Part 2: the kernels of round 5
363      new_bad = 0
364      if skip_new:
365          print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=NOT CHECKED (--skip-new)" % (b, rb, len(kernels), bad))
366          return 1 if bad else 0
367      like_mod = {}
368      for name in sorted({sp["like"] for sp in NEW.values()}):
369          orig = got.get((b, name), [])
370          orig_loop = loop_start(orig) if orig else None
371          like_mod[name] = None if orig_loop is None else orig_loop % 64</pre></td><td valign="top"><ul><li>Lines 364 to 366: with <code>--skip-new</code> the script prints the summary line here and returns. The new kernels are then not checked.</li><li>Lines 367 to 371: <code>like_mod</code> holds the loop start modulo 64 of <code>asmcopy</code>, <code>asmread</code> and <code>asmwrite</code> in the new listing. These are the three originals that <code>NEW</code> names. A value is <code>None</code> when the kernel is missing or has no loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">372      print("new_kernel\tstart\tloop_start\tloop_mod64\toriginal_loop_mod64\tloop\tresult")
373      for k in NEW_LOOP:
374          insns = got.get((b, k), [])
375          want_mod = like_mod[NEW[k]["like"]]
376          if not insns:
377              print("%s\tNA\tNA\tNA\t%s\t-\tFAIL: no listing" % (k, "NA" if want_mod is None else want_mod))
378              new_bad += 1
379              continue
380          problems = new_problems(k, insns, want_mod, got_off.get((b, k)))
381          loop = loop_start(insns)
382          print("%s\t%x\t%s\t%s\t%s\t%s\t%s" % (k, insns[0][0], "NA" if loop is None else "%x" % loop,
383                                                 "NA" if loop is None else loop % 64, "NA" if want_mod is None else want_mod,
384                                                 "DIFFERS" if any("loop instruction" in x or "loop branch" in x or "backward" in x or "nop, expected" in x
385                                                                  for x in problems) else "expected",
386                                                 "FAIL: " + "; ".join(problems) if problems else "ok"))
387          new_bad += bool(problems)</pre></td><td valign="top"><ul><li>Line 372 prints the column names of the second output table.</li><li>Lines 373 to 379: every kernel of <code>NEW</code> must have a block in the new listing. If not, the row says <code>FAIL: no listing</code>.</li><li>Line 380: <code>new_problems</code> (line 208) applies the five rules.</li><li>Lines 382 to 386 print the row: kernel, function start, loop start, loop start modulo 64, the value of the original kernel, <code>expected</code> or <code>DIFFERS</code>, and the result <code>ok</code> or <code>FAIL: ...</code>.</li><li>The sixth column says <code>DIFFERS</code> when a problem text is about the loop instructions, the <code>nop</code> count, the loop branch, another branch or call, or the number of backward branches. Any other problem shows only in the result column.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">388      print("# binary=%s reference=%s kernels=%d failed_rows=%d new_kernels=%d new_failed_rows=%d" %
389            (b, rb, len(kernels), bad, len(NEW_LOOP), new_bad))
390      return 1 if bad or new_bad else 0
391
392
393  if __name__ == "__main__":
394      sys.exit(main())</pre></td><td valign="top"><ul><li>Lines 388 and 389 print the summary line. For the accepted build of <code>bwx12</code> it is <code># binary=bwx12 reference=bwx11 kernels=29 failed_rows=0 new_kernels=26 new_failed_rows=0</code> [Ref1].</li><li>Line 390: <code>main</code> returns 1 when a check of part 1 or part 2 failed, and 0 when none failed.</li><li>Line 394 makes this value the exit status of the script.</li></ul></td></tr>
</table>

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
