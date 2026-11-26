# `check_listing.py` explained, line by line

- Source file: `bwx-2026-11-13/check_listing.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 278 lines, 13093 bytes).
- sha256 of the source when this page was built: `c3a151d5372267aea7bd40e933bd3fe787f5e679b70c9963c233c4a6ef649a00`.

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

1. When Python loads the file, it builds the tables `KERNELS`, `AA` and `SAME` (lines 52 to 62) and the tables of check 5 (lines 138 to 142).
2. `main` reads the option `--binaries` and the two file arguments (lines 181 to 190).
3. It reads `probe.txt` and the listing with the helper `sections`. A file that cannot be read ends the script with exit status 2 (lines 191 to 195).
4. It takes the loop and the whole text of the nine reference functions from `probe.txt`, with the helpers `loop_of` and `whole`. Exit status 2 when one of them has no loop (lines 196 to 203).
5. Exit status 2 when the listing has no block. An expected binary that the listing lacks gets a failure row (lines 204 to 215).
6. For each binary and each of the 21 kernels it makes the checks 1 to 5 and prints one row. When a text differs, it prints both texts side by side (lines 216 to 268).
7. Kernels of a binary that the script does not know count as one failure (lines 269 to 272).
8. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed (lines 273 to 278).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its table to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used, `--binaries` has no value, a reference function has no loop, or the listing has no block.
- The script reads `listing.txt` and `probe.txt`. It does not read `offsets.tsv`, the second table that `build.sh` writes. It computes every loop start from the listing.
- The default path of `probe.txt` fits the project folder of the script and not the code repo (line 50). From the repo the file must be given as the second argument. The repo keeps it in the test folder of 2026-11-13 [Ref1].
- Saved outputs of this script for the two CRB builds lie in the project folder, not in the repo. Both show 83 rows with `ok` and one row with `FAIL`, and both end with `failed_rows=1` [Ref2]. So the script ended with exit status 1 for both builds. A note of the project says the same for the second build [Ref3].
- CRB build 1 fails at `copy` of `bwx_o52`: the loop offset is 0 and not the planned 52. CRB build 2 was built with one more compiler option for `bwx_o52`. It fails at `oldwrite` of `bwx_o52`: the loop body is the same, and the code outside the loop differs from `k_write` of `bw_old` [Ref2]. By the note of the project the first build was not used, and no sequence of step B3 uses `oldwrite` [Ref3].
- What the script proves for one of the 13 kernels of `WHOLE` with `ok`: the whole function, with every operand, equals the function of `bw_new` or `bw_old` in `probe.txt`, apart from addresses. A target outside the function is not compared at all (line 132).
- What it proves for one of the other eight kernels with `ok`: the loop body equals a list that the script builds from two reference loops (lines 158 to 177), the function has exactly one backward branch, and d8 to d15 are stored and loaded where the kernel is in `SAVE_D8_D15`. The rest of the code outside the loop of these kernels is not checked (lines 37 to 38).
- In check 2 only the target of the loop branch is made independent of the address (line 107). The documentation text describes a distance from the loop start (lines 40 to 41).
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel.

## Source and explanation, line by line

- Text shown: the file `bwx-2026-11-13/check_listing.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (278 lines, 13093 bytes, sha256 `c3a151d5372267aea7bd40e933bd3fe787f5e679b70c9963c233c4a6ef649a00`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: usage, the five checks and the exit status (lines 1 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_listing.py - acceptance test of a bwx build (handoff.md, B.7).` | Starts the documentation text of the script (lines 2 to 44). Python does not execute it, and no line of the script prints it. This line: the script is the acceptance test of a build of the runner program `bwx`. It accepts or rejects a build. Its input is the machine code of every kernel, as text. A kernel is one inner loop of the benchmark that reads, writes or copies memory. The test follows section B.7 of the note `handoff.md`. |
| 4 | `Runs on the development machine, on the listing.txt that build.sh wrote on CRB.` | Documentation text: the script runs on the development machine, not on CRB (the Arm reference server under test). It reads the file `listing.txt` that the build script `build.sh` wrote on CRB. |
| 5 | `Usage: check_listing.py [listing.txt] [probe.txt]` | Documentation text: the usage. Both file arguments are optional: the listing and the reference file `probe.txt`. Line 189 and line 190 set the defaults. |
| 7 | `Checks, for each of the four binaries bwx, bwx_o0, bwx_o36, bwx_o52 (a binary` | Documentation text: five checks follow. They are made for each of the four binaries `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`. A binary ... |
| 8 | `that listing.txt lacks is a failure; "--binaries a,b" names another list):` | Documentation text: ... that `listing.txt` lacks is a failure (lines 212 to 215). The option `--binaries a,b` names another list of binaries (lines 182 to 188). |
| 9 | ` 1. every kernel is present and has a loop;` | Documentation text: check 1. Every kernel is present and has a loop. Lines 225 to 228 implement it. |
| 10 | ` 2. the loop body equals the reference in probe.txt:` | Documentation text: check 2. The loop body equals the reference in `probe.txt` (lines 231 to 234). `probe.txt` holds the machine code of the kernels of the two older benchmark binaries `bw_new` and `bw_old`. Lines 11 to 20 say which reference each kernel has. |
| 11 | `    - read, write, copy, asmread, asmwrite, asmcopy and the A/A copies: the` | Documentation text: for `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy` and the A/A copies the reference is the ... An A/A copy is the same source under a second name: `asmread2`, `asmwrite2`, `asmcopy2` and `oldread2`. This line holds for the first three only. The reference of `oldread2` is in `bw_old` (line 13, line 60). |
| 12 | `      loop of the same kernel in "bw_new";` | Documentation text: ... loop of the same kernel in `bw_new`. |
| 13 | `    - oldread, oldread2, oldwrite, oldcopy: the loop of k_read, k_write,` | Documentation text: for `oldread`, `oldread2`, `oldwrite` and `oldcopy` the reference is the loop of `k_read`, `k_write` and ... |
| 14 | `      k_copy in "bw_old";` | Documentation text: ... `k_copy` in `bw_old`. |
| 15 | `    - asmcopy_c: the loop of "bw_new k_copy";` | Documentation text: for `asmcopy_c` the reference is the loop of `k_copy` in `bw_new`. By the handoff, `asmcopy_c` is an assembly kernel whose loop is the machine code of that C copy loop [Ref5]. |
| 16 | `    - asmcopy_c_reg: that loop with q31..q16 renamed to q0..q15;` | Documentation text: for `asmcopy_c_reg` it is that loop with the registers q31 down to q16 renamed to q0 up to q15 (lines 163 to 164). |
| 17 | `    - asmcopy_c_add: the 8 ldp of that loop, its 8 stp with the offsets 0 to` | Documentation text: for `asmcopy_c_add` it is the 8 `ldp` of that loop, then its 8 `stp` with the offsets 0 to ... |
| 18 | `      224, then its two add, cmp and branch;` | Documentation text: ... 224 bytes, then its two `add`, its `cmp` and its branch (lines 165 to 171). |
| 19 | `    - read_nopN: the loop of "bw_new k_asmread" with N nop before its add;` | Documentation text: for a kernel `read_nopN` it is the loop of `k_asmread` in `bw_new` with N `nop` instructions before its `add` (lines 172 to 174). N is 4, 8, 16 or 32. A `nop` is an instruction that does nothing. |
| 20 | `    - read_sparse: the first 4 ldp of that loop, 9 nop, add of 128, cmp, branch;` | Documentation text: for `read_sparse` it is the first 4 `ldp` of that loop, 9 `nop`, an `add` of 128 bytes, the `cmp` and the branch (lines 175 to 176). |
| 21 | ` 3. the planned loop offsets modulo 64: bwx has copy at 36 and asmcopy,` | Documentation text: check 3, the planned loop offsets modulo 64 (lines 235 to 237). A loop offset modulo 64 is the remainder of the loop start address divided by 64. In `bwx`, `copy` is planned at 36 and `asmcopy`, ... |
| 22 | `    asmcopy2, asmcopy_c, asmcopy_c_add, asmcopy_c_reg at 52; bwx_oN has copy,` | Documentation text: ... `asmcopy2`, `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg` at 52. In a binary `bwx_oN`, `copy`, ... |
| 23 | `    asmcopy and asmcopy2 at N;` | Documentation text: ... `asmcopy` and `asmcopy2` are planned at N. The function `planned` (line 65) holds these values. |
| 24 | ` 4. every A/A copy has its own start address and the loop offset modulo 64 of` | Documentation text: check 4. Every A/A copy has its own start address and the loop offset modulo 64 of ... |
| 25 | `    its original.` | Documentation text: ... its original (lines 238 to 244). |
| 26 | ` 5. code outside the loop:` | Documentation text: check 5, the code outside the loop. It has three parts. |
| 27 | `    - read, write, copy, asmread, asmwrite, asmcopy, the A/A copies and the` | Documentation text: first part. For `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`, the A/A copies and the ... |
| 28 | `      old kernels: the whole function equals the function in probe.txt` | Documentation text: ... old kernels, the whole function must equal the function in `probe.txt` ... |
| 29 | `      (prologue, end computation, epilogue, any second loop);` | Documentation text: ... with its prologue, its end computation, its epilogue and any second loop (lines 246 to 248). The prologue is the code before the loop. The epilogue is the code after it. |
| 30 | `    - asmcopy_c, asmcopy_c_add, asmcopy_c_reg, read_nopN, read_sparse (no` | Documentation text: second part. For `asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`, `read_nopN` and `read_sparse` ... The text in parentheses says that `probe.txt` holds no ... |
| 31 | `      listing of them exists in probe.txt): the function has exactly one` | Documentation text: ... listing of these kernels. For them the function must have exactly one ... |
| 32 | `      backward branch;` | Documentation text: ... backward branch (lines 249 to 251). |
| 33 | `    - every kernel that uses q8 to q15 (asmread, asmread2, read_nopN, asmcopy,` | Documentation text: third part. For every kernel that uses the registers q8 to q15 (`asmread`, `asmread2`, `read_nopN`, `asmcopy`, ... |
| 34 | `      asmcopy2, asmcopy_c_reg): "stp d8, d9", "stp d10, d11", "stp d12, d13",` | Documentation text: ... `asmcopy2`, `asmcopy_c_reg`), the four stores `stp d8, d9`, `stp d10, d11`, `stp d12, d13` and ... |
| 35 | `      "stp d14, d15" stand before the loop and the four matching ldp after it.` | Documentation text: ... `stp d14, d15` must stand before the loop, and the four matching `ldp` after it (lines 252 to 253). `stp` stores a pair of registers, and `ldp` loads a pair. The registers d8 to d15 are the low halves of v8 to v15. A function must give them back unchanged. |
| 36 | `    Check 5 is stricter than handoff B.7, which names the loop bodies only.` | Documentation text: check 5 is stricter than section B.7 of the handoff, which names the loop bodies only. |
| 37 | `    What it does not see: the code outside the loop of the five kernels` | Documentation text: what check 5 does not see: the code outside the loop of the five kernels ... |
| 38 | `    without a listing in probe.txt, apart from the two points above.` | Documentation text: ... without a listing in `probe.txt`, apart from the two points above. The text counts the four `read_nopN` kernels as one. The code has eight such kernels (line 250). |
| 39 | `The loop of a function is the range from the target of its first backward` | Documentation text: the definition of the loop. The loop of a function is the range from the target of its first backward ... A backward branch is a branch whose target address is lower than its own address. |
| 40 | `branch to that branch. Addresses are not compared: a branch target inside the` | Documentation text: ... branch to that branch. Addresses are not compared. A branch target inside the ... |
| 41 | `function is compared as a distance from the loop start (check 2) or from the` | Documentation text: ... function is compared as a distance from the loop start in check 2, or from the ... The code of check 2 does less: it writes the target of the loop branch as the word `LOOP` (line 107). A second branch inside a loop body would keep its address. None of the nine reference loops holds one [Ref1]. |
| 42 | `function start (check 5).` | Documentation text: ... function start in check 5 (line 128). |
| 43 | `Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.` | Documentation text: the exit statuses. 0: all checks passed. 1: a check failed. 2: a file could not be used. The code returns 2 in three more cases: `--binaries` has no value (line 186), `probe.txt` has no loop for a reference function (line 201), and the listing has no block (line 207). The exit status is the return value of `main` (line 278). |
| 44 | `"""` | Ends the documentation text. |

### Imports, the default path of `probe.txt`, and the tables `KERNELS`, `AA` and `SAME` (lines 45 to 64)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `import os` | Loads the module `os`. The script uses it for file paths. |
| 46 | `import re` | Loads the module `re` for regular expressions. |
| 47 | `import sys` | Loads the module `sys` for the arguments and the exit status. |
| 49 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. |
| 50 | `PROBE = os.path.join(HERE, "..", "..", "..", "results", "kernels-20261113T181222Z", "probe.txt")` | `PROBE`: the default path of the reference file `probe.txt`. It goes three folders up from the folder of the script and then into `results/kernels-20261113T181222Z`. This fits the place of the script in the project folder (`crb/tmp/agent-scratch/bwx-2026-11-13`). From the code repo the path names no file. The repo keeps the same `probe.txt` in the test folder `2026-11-13-new-read-kernel/kernels-20261113T181222Z` [Ref1]. |
| 52 | `KERNELS = ["read", "write", "copy", "asmread", "asmwrite", "asmcopy", "oldread", "oldwrite", "oldcopy",` | `KERNELS`: the names of the 21 kernels that every binary must hold, in the order of the output rows. This line: the three new C kernels, the three assembly kernels and the three old kernels. |
| 53 | `           "asmread2", "asmwrite2", "asmcopy2", "oldread2", "asmcopy_c", "asmcopy_c_add", "asmcopy_c_reg",` | Continues the list: the four A/A copies, and the three kernels `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. |
| 54 | `           "read_nop4", "read_nop8", "read_nop16", "read_nop32", "read_sparse"]` | Ends the list: the four `read_nop` kernels and `read_sparse`. |
| 55 | `AA = {"asmread2": "asmread", "asmwrite2": "asmwrite", "asmcopy2": "asmcopy", "oldread2": "oldread"}` | `AA`: a dictionary from each A/A copy to its original: `asmread2` to `asmread`, `asmwrite2` to `asmwrite`, `asmcopy2` to `asmcopy`, and `oldread2` to `oldread`. |
| 56 | `# kernel -> (reference binary, reference function) for an unchanged loop` | Comment: the next table gives, for a kernel with an unchanged loop, the reference binary and the reference function. |
| 57 | `SAME = {"read": ("bw_new", "k_read"), "write": ("bw_new", "k_write"), "copy": ("bw_new", "k_copy"),` | `SAME`: a dictionary from a kernel name to the pair (reference binary, reference function) in `probe.txt`. This line: `read`, `write` and `copy` have the functions `k_read`, `k_write` and `k_copy` of `bw_new`. |
| 58 | `        "asmread": ("bw_new", "k_asmread"), "asmwrite": ("bw_new", "k_asmwrite"), "asmcopy": ("bw_new", "k_asmcopy"),` | Continues: `asmread`, `asmwrite` and `asmcopy` have `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new`. |
| 59 | `        "asmread2": ("bw_new", "k_asmread"), "asmwrite2": ("bw_new", "k_asmwrite"), "asmcopy2": ("bw_new", "k_asmcopy"),` | Continues: the three A/A copies `asmread2`, `asmwrite2` and `asmcopy2` have the references of their originals. |
| 60 | `        "oldread": ("bw_old", "k_read"), "oldread2": ("bw_old", "k_read"),` | Continues: `oldread` and `oldread2` have `k_read` of `bw_old`. |
| 61 | `        "oldwrite": ("bw_old", "k_write"), "oldcopy": ("bw_old", "k_copy"),` | Continues: `oldwrite` and `oldcopy` have `k_write` and `k_copy` of `bw_old`. |
| 62 | `        "asmcopy_c": ("bw_new", "k_copy")}` | Ends the dictionary: `asmcopy_c` has `k_copy` of `bw_new`. Only its loop is compared with that function (line 140). |

### Functions `planned` and `sections` (lines 65 to 93)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `def planned(binary):` | Starts the function `planned`. It returns the planned loop offsets of one binary. |
| 66 | `    """kernel -> planned loop offset modulo 64, for the kernels that have one"""` | Documentation text of `planned`: it returns a dictionary from a kernel name to the planned loop offset modulo 64, for the kernels that have one. |
| 67 | `    if binary == "bwx":` | For the binary `bwx` ... |
| 68 | `        return {"copy": 36, "asmcopy": 52, "asmcopy2": 52, "asmcopy_c": 52, "asmcopy_c_add": 52, "asmcopy_c_reg": 52}` | ... the plan is 36 for `copy` and 52 for `asmcopy`, `asmcopy2`, `asmcopy_c`, `asmcopy_c_add` and `asmcopy_c_reg`. The unit is bytes inside a 64-byte block of code. |
| 69 | `    m = re.fullmatch(r"bwx_o(\d+)", binary)` | `m`: tests whether the whole name has the form `bwx_o` plus digits. Group 1 holds the digits. |
| 70 | `    if m:` | For such a binary ... |
| 71 | `        n = int(m.group(1))` | ... `n` is the number in the name: 0, 36 or 52 for the three B3 binaries ... |
| 72 | `        return {"copy": n, "asmcopy": n, "asmcopy2": n}` | ... and the plan is `n` for `copy`, `asmcopy` and `asmcopy2`. The three `asmcopy_c` kernels have no planned offset in these binaries. |
| 73 | `    return {}` | Any other binary name has no planned offset: the result is an empty dictionary. |
| 76 | `def sections(path):` | Starts the function `sections`. It reads a listing file. |
| 77 | `    """{(binary, name): [(address, text), ...]} from '=== binary name ===' blocks of objdump text"""` | Documentation text of `sections`: it returns a dictionary. A key is the pair (binary, name). Its value is the list of (address, instruction text) of that block, in file order. A block starts with a title line `=== binary name ===`. The script reads both `listing.txt` and `probe.txt` with this function. |
| 78 | `    out, cur = {}, None` | `out`: the dictionary. `cur`: the list of the block that is read now. It is `None` outside a block. |
| 79 | `    with open(path) as f:` | Opens the file. |
| 80 | `        for line in f:` | Loop over the lines of the file. |
| 81 | `            m = re.match(r"=== (\S+) (\S+) ===", line)` | Tests whether the line is a title line of the form `=== BINARY NAME ===`. Group 1 holds the name of the binary. Group 2 holds the second name. In `listing.txt` it is a kernel name such as `read`. In `probe.txt` it is a function name such as `k_read`. |
| 82 | `            if m:` | A title line starts a new block. |
| 83 | `                cur = out.setdefault((m.group(1), m.group(2)), [])` | `cur` becomes the list for this pair. `setdefault` creates an empty list when the pair is new. |
| 84 | `                continue` | Goes to the next line. |
| 85 | `            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)` | Tests whether the line is an instruction line: spaces, a hexadecimal address (group 1), a colon, spaces or tabs, and the instruction (group 2). The label line of a function has no colon directly after its address. So it does not match and is skipped. |
| 86 | `            if m and cur is not None:` | Only inside a block ... |
| 87 | `                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()` | ... the text is cleaned. The `objdump` comment after `//` is cut off. Each run of spaces and tabs becomes one space. |
| 88 | `                cur.append((int(m.group(1), 16), text))` | Appends the pair of the address as a number and the cleaned text to the block. |
| 89 | `            elif line.startswith("##"):` | A line that starts with `##` (`probe.txt` holds such lines before its first block and after its last block [Ref1]) ... |
| 90 | `                cur = None` | ... ends the block that is read now. |
| 91 | `    return out` | Returns the dictionary. |

### Functions `loop_of`, `backward_branches` and `whole` (lines 94 to 135)

| Line | Source | Explanation |
|---:|---|---|
| 94 | `def loop_of(insns):` | Starts the function `loop_of`. `insns` is the list of (address, text) of one function. The function finds the loop. |
| 95 | `    """(loop start address, normalized loop text) or None. The loop ends at the` | Documentation text of `loop_of`: it returns the pair of the loop start address and the loop text in a form without addresses, or `None`. The loop ends at the ... |
| 96 | `    first instruction that branches backward to an address inside the function."""` | Documentation text: ... first instruction that branches backward to an address inside the function. |
| 97 | `    if not insns:` | An empty list, which stands for a missing block ... |
| 98 | `        return None` | ... gives `None`. |
| 99 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 100 | `    for i, (addr, text) in enumerate(insns):` | Goes through the instructions in order. `i` is the position, `addr` the address and `text` the instruction text. |
| 101 | `        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)` | `m`: looks for a branch target at the end of the text: a hexadecimal address (group 1), a space and a name in angle brackets. Example from the listing of CRB build 2: `3a24 <k_read+0x4>` [Ref6]. |
| 102 | `        if not m:` | An instruction without such a target ... |
| 103 | `            continue` | ... is skipped. |
| 104 | `        tgt = int(m.group(1), 16)` | `tgt`: the target address as a number. |
| 105 | `        if first <= tgt < addr:` | The branch counts when its target lies inside the function and before the branch itself (`first <= tgt < addr`). The first such branch ends the loop. |
| 106 | `            body = [t for a, t in insns[:i + 1] if a >= tgt]` | `body`: the texts of the instructions from the loop start `tgt` up to this branch, both included. |
| 107 | `            body[-1] = text[:m.start()] + "LOOP"` | The last entry is the loop branch. Its target is replaced by the word `LOOP`. So `b.hi 3a24 <k_read+0x4>` becomes `b.hi LOOP`. In the nine reference loops no other entry holds an address [Ref1]. So two equal loops at different addresses give equal lists. |
| 108 | `            return tgt, body` | Returns the loop start address and the list. |
| 109 | `    return None` | Returns `None` when the function has no backward branch. |
| 112 | `def backward_branches(insns):` | Starts the function `backward_branches`. It counts the backward branches of one function. |
| 113 | `    """number of instructions that branch backward to an address inside the function"""` | Documentation text of `backward_branches`: the number of instructions that branch backward to an address inside the function. |
| 114 | `    first, n = insns[0][0], 0` | `first`: the address of the first instruction. `n`: the count, 0 at first. |
| 115 | `    for addr, text in insns:` | Loop over the instructions. |
| 116 | `        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)` | Looks for a branch target at the end of the text, with the pattern of line 101. |
| 117 | `        if m and first <= int(m.group(1), 16) < addr:` | A target inside the function and before the instruction itself ... |
| 118 | `            n += 1` | ... adds 1 to the count. |
| 119 | `    return n` | Returns the count. |
| 122 | `def whole(insns):` | Starts the function `whole`. It returns the text of a whole function in a form that does not depend on the addresses. |
| 123 | `    """the function text; a branch target inside the function becomes its distance from the function start"""` | Documentation text of `whole`: it returns the function text. A branch target inside the function becomes its distance from the function start. |
| 124 | `    first, last, out = insns[0][0], insns[-1][0], []` | `first` and `last`: the addresses of the first and the last instruction. `out`: the result list. |
| 125 | `    for _, text in insns:` | Loop over the instruction texts. |
| 126 | `        m = re.search(r"\b([0-9a-f]+) <[^>]+>$", text)` | Looks for a target at the end of the text. |
| 127 | `        if m and first <= int(m.group(1), 16) <= last:` | A target inside the function ... |
| 128 | `            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... becomes its distance from the function start, written as `+0x` and hexadecimal digits. Example with text of the listing of CRB build 2: in `k_read`, which starts at 3a20, `b.hi 3a24 <k_read+0x4>` becomes `b.hi +0x4` [Ref6]. |
| 129 | `        elif m:` | A target outside the function: |
| 130 | `            # an address outside the function (adrp of a data page, bl of a library stub) depends on` | Comment: an address outside the function is the data page of an `adrp` instruction or the library stub that a `bl` calls. `adrp` puts the address of a page into a register. `bl` is the call instruction. Such an address depends on ... |
| 131 | `            # where the linker put that target in this binary, not on the code of the kernel` | Comment: ... where the linker put that target in this binary, not on the code of the kernel. |
| 132 | `            text = text[:m.start()] + "(outside)"` | So the address and the name in angle brackets are replaced by the fixed text `(outside)`. The name of the target is not compared. So a call of another function at the same place would pass. A note of the project lists this rule as a change of the lead of the test: the script no longer compares addresses outside a function [Ref3]. |
| 133 | `        out.append(text)` | Appends the text to `out`. |
| 134 | `    return out` | Returns the list of the instruction texts. |

### Tables for check 5, and the function `save_problems` (lines 136 to 157)

| Line | Source | Explanation |
|---:|---|---|
| 137 | `# kernels that use q8 to q15, so d8 to d15 must be saved before the loop and restored after it` | Comment: the next set names the kernels that use the registers q8 to q15. For them d8 to d15 must be saved before the loop and restored after it. |
| 138 | `SAVE_D8_D15 = {"asmread", "asmread2", "read_nop4", "read_nop8", "read_nop16", "read_nop32", "asmcopy", "asmcopy2", "asmcopy_c_reg"}` | `SAVE_D8_D15`: the nine kernels of that kind: `asmread`, `asmread2`, the four `read_nop` kernels, `asmcopy`, `asmcopy2` and `asmcopy_c_reg`. |
| 139 | `# kernels whose whole function is in probe.txt (asmcopy_c has only its loop from there)` | Comment: the next table names the kernels whose whole function is in `probe.txt`. `asmcopy_c` has only its loop from there. |
| 140 | `WHOLE = {k: v for k, v in SAME.items() if k != "asmcopy_c"}` | `WHOLE`: the dictionary `SAME` without `asmcopy_c`. It holds 13 kernels. |
| 141 | `D_PAIRS = ["d8, d9", "d10, d11", "d12, d13", "d14, d15"]` | `D_PAIRS`: the four register pairs of d8 to d15, in the text form of the listing. |
| 142 | `BINARIES = ["bwx", "bwx_o0", "bwx_o36", "bwx_o52"]` | `BINARIES`: the four binaries that the script expects by default. |
| 145 | `def save_problems(insns, loop_start, loop_len):` | Starts the function `save_problems`. It checks the stores and loads of d8 to d15 of one function. `loop_start` is the address of the loop start. `loop_len` is the number of instructions of the loop. |
| 146 | `    """the pairs of d8 to d15 that are not saved before the loop or not restored after it"""` | Documentation text of `save_problems`: it returns the pairs of d8 to d15 that are not saved before the loop or not restored after it. |
| 147 | `    before = [t for a, t in insns if a < loop_start]` | `before`: the texts of the instructions that stand before the loop start. |
| 148 | `    after = [t for a, t in insns if a >= loop_start + 4 * loop_len]` | `after`: the texts of the instructions that stand after the loop. An instruction has 4 bytes. So the first address after the loop is `loop_start + 4 * loop_len`. |
| 149 | `    out = []` | `out`: the list of problem texts. |
| 150 | `    for pair in D_PAIRS:` | Loop over the four pairs. |
| 151 | `        if not any(re.match(r"stp %s, \[sp" % pair, t) for t in before):` | Looks in `before` for a text that starts with `stp`, the pair and `[sp`. That is a store of the pair to the stack. |
| 152 | `            out.append("no 'stp %s' before the loop" % pair)` | Without one, a problem says that the `stp` of this pair is missing before the loop. |
| 153 | `        if not any(re.match(r"ldp %s, \[sp" % pair, t) for t in after):` | Looks in `after` for a text that starts with `ldp`, the pair and `[sp`. That is a load of the pair from the stack. |
| 154 | `            out.append("no 'ldp %s' after the loop" % pair)` | Without one, a problem says that the `ldp` of this pair is missing after the loop. |
| 155 | `    return out` | Returns the list. An empty list says that all four pairs are stored and loaded. |

### Function `expected`: the loop text that a kernel must have (lines 158 to 179)

| Line | Source | Explanation |
|---:|---|---|
| 158 | `def expected(kernel, ref):` | Starts the function `expected`. It returns the loop text that a kernel must have. `ref` holds the reference loops of `probe.txt`, each in the form that `loop_of` gives. |
| 159 | `    """the loop text that the kernel must have, built from the reference loops"""` | Documentation text of `expected`: the loop text that the kernel must have, built from the reference loops. |
| 160 | `    if kernel in SAME:` | A kernel of the table `SAME` ... |
| 161 | `        return ref[SAME[kernel]]` | ... gets the loop of its reference function unchanged. |
| 162 | `    c, r = ref[("bw_new", "k_copy")], ref[("bw_new", "k_asmread")]` | `c`: the loop of `k_copy` of `bw_new`, the C copy loop. `r`: the loop of `k_asmread` of `bw_new`. The four cases below build their lists from these two. In `probe.txt` the first has 20 instructions and the second has 11 [Ref1]. |
| 163 | `    if kernel == "asmcopy_c_reg":` | Case `asmcopy_c_reg`: |
| 164 | `        return [re.sub(r"\bq(\d+)\b", lambda m: "q%d" % (31 - int(m.group(1))), t) for t in c]` | the list `c` with every register name `qN` replaced by `q` plus the number 31 minus N. So q31 becomes q0, and q16 becomes q15. The pattern takes the letter `q` with digits as a whole word. |
| 165 | `    if kernel == "asmcopy_c_add":` | Case `asmcopy_c_add`: |
| 166 | `        ldp = [t for t in c if t.startswith("ldp")]` | `ldp`: the 8 `ldp` instructions of `c`. |
| 167 | `        stp = [t for t in c if t.startswith("stp")]` | `stp`: its 8 `stp` instructions. |
| 168 | `        add = [t for t in c if t.startswith("add")]` | `add`: its two `add` instructions. |
| 169 | `        dst = re.search(r"\[(\w+)", stp[0]).group(1)` | `dst`: the register name inside the brackets of the first `stp`. It is the destination pointer, `x0` in `probe.txt` [Ref1]. |
| 170 | `        stp = [re.sub(r"\[.*\]", "[%s]" % dst if i == 0 else "[%s, #%d]" % (dst, 32 * i), t) for i, t in enumerate(stp)]` | Rewrites the address of each `stp`: `[x0]` for the first, and `[x0, #32]` up to `[x0, #224]` for the others, in steps of 32 bytes. In the C loop the last seven stores stand after an `add` and have the offsets -224 to -32 bytes [Ref1]. |
| 171 | `        return ldp + stp + add + c[-2:]` | The expected list: the 8 `ldp`, the 8 rewritten `stp`, the two `add`, and the last two entries of `c`, which are the `cmp` and the loop branch. |
| 172 | `    m = re.fullmatch(r"read_nop(\d+)", kernel)` | `m`: tests whether the name is `read_nop` plus digits. Group 1 holds the number of `nop`. |
| 173 | `    if m:` | For such a kernel ... |
| 174 | `        return r[:8] + ["nop"] * int(m.group(1)) + r[8:]` | ... the list is the first 8 entries of `r` (the 8 `ldp`), then that number of `nop`, then the rest of `r`: the `add`, the `cmp` and the loop branch. |
| 175 | `    if kernel == "read_sparse":` | Case `read_sparse`: |
| 176 | `        return r[:4] + ["nop"] * 9 + [r[8].replace("#0x100", "#0x80")] + r[9:]` | the first 4 `ldp` of `r`, then 9 `nop`, then the `add` of `r` with `#0x80` (128 bytes) in place of `#0x100` (256 bytes), then the `cmp` and the loop branch. These are 16 instructions per 128 B. |
| 177 | `    raise KeyError(kernel)` | Any other name raises `KeyError`. The loop of line 221 passes only the names of `KERNELS`, and each of them has a case above. |

### Function `main`: arguments, reference loops and the expected binaries (lines 180 to 215)

| Line | Source | Explanation |
|---:|---|---|
| 180 | `def main():` | Starts the function `main`. Its return value becomes the exit status (line 278). |
| 181 | `    args, want_bins = sys.argv[1:], BINARIES` | `args`: the arguments of the command line without the script name. `want_bins`: the binaries that the script expects, by default the four of `BINARIES`. |
| 182 | `    if "--binaries" in args:` | When the option `--binaries` is present ... |
| 183 | `        i = args.index("--binaries")` | ... it stands at position `i` ... |
| 184 | `        if i + 1 >= len(args):` | ... and needs one more argument after it. |
| 185 | `            print("--binaries needs a comma-separated list")` | Without it the script prints that `--binaries` needs a comma-separated list ... |
| 186 | `            return 2` | ... and ends with exit status 2. |
| 187 | `        want_bins = args[i + 1].split(",")` | `want_bins` becomes the list of the names, split at the commas. |
| 188 | `        del args[i:i + 2]` | The option and its value are removed from the arguments. |
| 189 | `    listing = args[0] if len(args) > 0 else os.path.join(HERE, "listing.txt")` | `listing`: the first remaining argument, or `listing.txt` in the folder of the script. |
| 190 | `    probe = args[1] if len(args) > 1 else PROBE` | `probe`: the second remaining argument, or the default path `PROBE` (line 50). |
| 191 | `    try:` | Starts the block in which a file error is caught. |
| 192 | `        ref_raw, got_raw = sections(probe), sections(listing)` | Reads `probe.txt` into `ref_raw` and the listing into `got_raw`, both with `sections`. |
| 193 | `    except OSError as e:` | A file that cannot be opened (`OSError`) ... |
| 194 | `        print("cannot read: %s" % e)` | ... prints `cannot read:` and the reason ... |
| 195 | `        return 2` | ... and the script ends with exit status 2. |
| 196 | `    ref, ref_whole = {}, {}` | `ref`: the reference loops. `ref_whole`: the reference function texts. Both get one entry per reference function. |
| 197 | `    for key in set(SAME.values()):` | Loop over the distinct pairs (binary, function) of the table `SAME`. These are nine functions: six of `bw_new` and three of `bw_old`. |
| 198 | `        lp = loop_of(ref_raw.get(key, []))` | `lp`: the loop of that function in `probe.txt`, from `loop_of`. A missing block gives an empty list and so `None`. |
| 199 | `        if lp is None:` | When the reference has no loop for the function ... |
| 200 | `            print("probe.txt has no loop for %s %s" % key)` | ... the script prints a message that names the binary and the function ... |
| 201 | `            return 2` | ... and ends with exit status 2. |
| 202 | `        ref[key] = lp[1]` | Stores the loop text of the function in `ref`. |
| 203 | `        ref_whole[key] = whole(ref_raw[key])` | Stores its whole function text in `ref_whole` (`whole`, line 122). |
| 204 | `    found = sorted({b for b, _ in got_raw})` | `found`: the sorted names of the binaries that the listing holds. |
| 205 | `    if not found:` | A listing without any block ... |
| 206 | `        print("no '=== binary kernel ===' block in %s" % listing)` | ... prints a message with the name of the listing file ... |
| 207 | `        return 2` | ... and ends the script with exit status 2. |
| 208 | `    # the expected binaries, then any other binary of the listing` | Comment: the order of the output is the expected binaries first, then any other binary of the listing. |
| 209 | `    binaries = want_bins + [b for b in found if b not in want_bins]` | `binaries`: the expected binaries, followed by the other binaries of the listing. |
| 211 | `    bad = 0` | `bad`: the count of failures. The summary line prints it as `failed_rows`. |
| 212 | `    for b in want_bins:` | Loop over the expected binaries. |
| 213 | `        if b not in found:` | An expected binary that the listing lacks ... |
| 214 | `            print("%s\t-\tNA\tNA\tNA\t-\t-\tFAIL: the listing has no block of this binary" % b)` | ... gets a row that ends with `FAIL: the listing has no block of this binary` ... |
| 215 | `            bad += 1` | ... and `bad` grows by 1. |

### Function `main`: one output row per binary and kernel, and the exit status (lines 216 to 278)

| Line | Source | Explanation |
|---:|---|---|
| 216 | `    print("binary\tkernel\tstart\tloop_start\tloop_mod64\tplanned\tloop_body\tresult")` | Prints the column names of the output table, with tabs between them: `binary`, `kernel`, `start`, `loop_start`, `loop_mod64`, `planned`, `loop_body`, `result`. A row for a missing binary (line 214) is printed before this line. |
| 217 | `    for b in binaries:` | Loop over the binaries. |
| 218 | `        if b not in found:` | A binary that the listing lacks ... |
| 219 | `            continue` | ... is skipped. Its failure row is already printed. |
| 220 | `        info = {}` | `info`: for each kernel of this binary that has a loop, its start address and its loop offset modulo 64. Check 4 reads it. |
| 221 | `        for k in KERNELS:` | Loop over the 21 kernel names of `KERNELS`. |
| 222 | `            insns = got_raw.get((b, k), [])` | `insns`: the instructions of the kernel in the listing, or an empty list when the listing has no block for it. |
| 223 | `            lp = loop_of(insns)` | `lp`: the loop of the function, or `None`. |
| 224 | `            problems = []` | `problems`: the problem texts of this kernel. |
| 225 | `            if lp is None:` | Check 1: no block or no backward branch ... |
| 226 | `                print("%s\t%s\tNA\tNA\tNA\t-\t-\tFAIL: no listing or no loop" % (b, k))` | ... prints a row that ends with `FAIL: no listing or no loop` ... |
| 227 | `                bad += 1` | ... `bad` grows by 1 ... |
| 228 | `                continue` | ... and the loop goes to the next kernel. |
| 229 | `            start, (loop, body) = insns[0][0], lp` | `start`: the address of the first instruction of the function. `loop`: the loop start. `body`: the loop text. |
| 230 | `            info[k] = (start, loop % 64)` | Stores the start address and the loop offset modulo 64 of this kernel in `info`. |
| 231 | `            want = expected(k, ref)` | Check 2. `want`: the expected loop text of the kernel (line 158). |
| 232 | `            same = body == want` | `same`: true when the two lists are equal: the same count, the same order, and every instruction text equal with every operand. |
| 233 | `            if not same:` | When they differ ... |
| 234 | `                problems.append("loop body differs from the reference")` | ... this is a problem: the loop body differs from the reference. |
| 235 | `            plan = planned(b).get(k)` | Check 3. `plan`: the planned loop offset of this kernel in this binary, or `None` (line 65). |
| 236 | `            if plan is not None and loop % 64 != plan:` | A planned offset that the loop start modulo 64 does not have ... |
| 237 | `                problems.append("loop offset is not the planned %d" % plan)` | ... is a problem that names the planned value. |
| 238 | `            if k in AA and AA[k] in info:` | Check 4, for an A/A copy whose original has a loop in this binary: |
| 239 | `                if info[AA[k]][0] == start:` | the same start address as the original ... |
| 240 | `                    problems.append("same start address as %s" % AA[k])` | ... is a problem. The handoff gives the reason for this check: without the flag `-fno-ipa-icf` gcc may merge two functions with equal bodies, and an A/A copy would then not exist [Ref5]. |
| 241 | `                if info[AA[k]][1] != loop % 64:` | A loop offset modulo 64 that differs from that of the original ... |
| 242 | `                    problems.append("loop offset differs from %s (%d)" % (AA[k], info[AA[k]][1]))` | ... is a problem that names the original and its offset. |
| 243 | `            elif k in AA:` | An A/A copy whose original has no loop in this binary ... |
| 244 | `                problems.append("original %s is missing" % AA[k])` | ... gets the problem that the original is missing. |
| 245 | `            # code outside the loop` | Comment: the checks of the code outside the loop follow. |
| 246 | `            outside = k in WHOLE and whole(insns) != ref_whole[WHOLE[k]]` | Check 5, first part. `outside` is true when the kernel is in `WHOLE` and its whole function text differs from the reference function text. |
| 247 | `            if outside and same:` | This becomes a problem of its own only when the loop body is equal ... |
| 248 | `                problems.append("code outside the loop differs from %s %s of probe.txt" % WHOLE[k])` | ... and the problem names the reference function. When the loop body differs, the row already has the problem of line 234. |
| 249 | `            nback = backward_branches(insns)` | `nback`: the number of backward branches of the function. |
| 250 | `            if k not in WHOLE and nback != 1:` | Check 5, second part, for the eight kernels that are not in `WHOLE`: the count must be 1. |
| 251 | `                problems.append("%d backward branches, 1 expected" % nback)` | If not, a problem gives the count. |
| 252 | `            if k in SAVE_D8_D15:` | Check 5, third part, for the nine kernels of `SAVE_D8_D15`: |
| 253 | `                problems += save_problems(insns, loop, len(body))` | `save_problems` (line 145) adds one problem for each missing store or load of a pair of d8 to d15. |
| 254 | `            print("%s\t%s\t%x\t%x\t%d\t%s\t%s\t%s" % (b, k, start, loop, loop % 64, "-" if plan is None else plan,` | Prints the row of the kernel: the binary, the kernel, the function start and the loop start (hexadecimal addresses), the loop start modulo 64, the planned offset or `-` ... |
| 255 | `                                                      "same" if same else "DIFFERS",` | ... `same` or `DIFFERS` for the loop body ... |
| 256 | `                                                      "FAIL: " + "; ".join(problems) if problems else "ok"))` | ... and the result: `FAIL:` with the problems, or `ok`. |
| 257 | `            if not same:` | When the loop body differs ... |
| 258 | `                for i in range(max(len(body), len(want))):` | ... a loop over the positions of the longer of the two lists ... |
| 259 | `                    g = body[i] if i < len(body) else "(none)"` | ... takes the instruction of the listing, or `(none)` past the end ... |
| 260 | `                    w = want[i] if i < len(want) else "(none)"` | ... and the expected instruction, or `(none)` past the end. |
| 261 | `                    print("    %s %-34s \| expected %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` and the word `expected` before the second. The mark `!=` stands before a line that differs. |
| 262 | `            elif outside:` | When the loop body is equal and the code outside the loop differs ... |
| 263 | `                g_all, w_all = whole(insns), ref_whole[WHOLE[k]]` | ... `g_all` is the whole function text of the listing, and `w_all` is that of the reference. |
| 264 | `                for i in range(max(len(g_all), len(w_all))):` | A loop over the positions of the longer text ... |
| 265 | `                    g = g_all[i] if i < len(g_all) else "(none)"` | ... takes the instruction of the listing, or `(none)` past the end ... |
| 266 | `                    w = w_all[i] if i < len(w_all) else "(none)"` | ... and the instruction of the reference, or `(none)` past the end. |
| 267 | `                    print("    %s %-34s \| probe.txt %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` and the word `probe.txt` before the second. A saved output of this script for CRB build 2 holds such a block for `oldwrite` of `bwx_o52`: 13 lines, 9 of them with the mark `!=` [Ref2]. |
| 268 | `            bad += bool(problems)` | `bad` grows by 1 when the kernel has a problem. |
| 269 | `        extra = sorted(k for bb, k in got_raw if bb == b and k not in KERNELS)` | `extra`: the kernels of this binary in the listing whose names are not in `KERNELS`. |
| 270 | `        if extra:` | When there is such a kernel ... |
| 271 | `            print("%s\t(kernels in the listing that this script does not know: %s)" % (b, ", ".join(extra)))` | ... one line names them as kernels that this script does not know ... |
| 272 | `            bad += 1` | ... and `bad` grows by 1. |
| 273 | `    print("# binaries=%d (expected: %s) kernels_per_binary=%d failed_rows=%d" % (len(found), ",".join(want_bins), len(KERNELS), bad))` | Prints the summary line: `# binaries=` with the number of binaries in the listing, the expected binaries in parentheses, `kernels_per_binary=` with the number of names in `KERNELS` (21), and `failed_rows=` with the value of `bad`. The saved outputs of this script for the two CRB builds both end with `failed_rows=1`. In CRB build 1 the failed row is `copy` of `bwx_o52`: its loop offset is 0 and not the planned 52. In CRB build 2 the failed row is `oldwrite` of `bwx_o52`: its code outside the loop differs from `k_write` of `bw_old` [Ref2]. |
| 274 | `    return 1 if bad else 0` | `main` returns 1 when a check failed, and 0 when none failed. |
| 277 | `if __name__ == "__main__":` | This test is true when the file runs as a script. |
| 278 | `    sys.exit(main())` | Calls `main` and makes its return value the exit status of the script. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/kernels-20261113T181222Z/probe.txt`: the reference file, 439 lines. The 22 rows of text before its first block and the 3 rows after its last block are not listing text. 10 of them start with `##`: 7 before the first block and 3 after the last block. It holds 17 blocks, among them `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy` of `bw_new` and of `bw_old`. Checked in this task with a script that follows the rule of lines 94 to 109: each of the nine reference functions has one backward branch, no reference loop holds a branch before its loop branch, the loop of `bw_new k_copy` has 20 instructions, and the loop of `bw_new k_asmread` has 11. In `bw_new k_copy` the first `stp` is `stp q31, q30, [x0]` and the seven others have the offsets -224 to -32. A `cmp` in this task found the file equal to `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`, the file that the default path of line 50 names from the project folder. From the folder `code/bwx-2026-11-13` of the repo the default path leads into a folder `results` beside the folder `arm-crb`. No such folder exists.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partBC-analysis/recount/check_listing-crb-build-2.txt` and the file `check_listing-crb-build-1.txt` beside it: saved outputs of this script, in the project folder. The file of build 2 has 99 lines: the header line, 84 kernel rows (83 end with `ok`), 13 lines of a side-by-side block (9 with `!=`) and the summary line `# binaries=4 (expected: bwx,bwx_o0,bwx_o36,bwx_o52) kernels_per_binary=21 failed_rows=1`. Its failed row is `bwx_o52 oldwrite`, with `same` in the column `loop_body` and the result `FAIL: code outside the loop differs from bw_old k_write of probe.txt`. The file of build 1 has 111 lines, 83 rows with `ok` and the same summary line. Its failed row is `bwx_o52 copy`, with `loop_mod64` 0, `planned` 52 and a result that starts with `FAIL: loop offset is not the planned 52`.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: a note of the project. Its section "Changes of the lead" says in item 1 that `bwx_o52` is built with `-falign-loops=1`, that the first build failed the acceptance test and was not used, that with the second build `check_listing.py` reports 83 of 84 rows ok and ends with status 1, that the failed row is `oldwrite` of `bwx_o52`, and that no B3 sequence uses it. Item 2 says that `check_listing.py` no longer compares addresses outside a function (`adrp`, `bl`).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: a note of the project. Its part "Smaller points of `build.sh` and `check_listing.py`" says that the script requires the four binaries, that it also checks code outside the loop, and that this is stricter than specification v1.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the note with "specification v1" of `bwx`. Section B.1 lists the kernels and says that `asmcopy_c` is an asm kernel whose loop is the machine code of the C copy loop. The text before B.1 says that without `-fno-ipa-icf` gcc may merge two functions with equal bodies, and that an A/A copy would then not exist. Section B.7 "Loop addresses" holds the item "Acceptance test, required".
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/listing.txt`: the listing of CRB build 2, with 84 blocks. The first block has the title line `=== bwx read ===` and the label line `0000000000003a20 <k_read>:`. `k_read` holds `b.hi 3a24 <k_read+0x4>`.
