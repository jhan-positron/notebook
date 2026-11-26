# `check_listing8.py` explained, line by line

- Source file: `bwx8-2026-11-14/check_listing8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 199 lines, 9441 bytes).
- sha256 of the source when this page was built: `9dd2ae1b45bd2d0334a71b51d661995f7300e92a53c8eaa39c537fd90c65ded7`.

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

1. `main` reads the four options and the two file arguments. Wrong arguments end the script with exit status 2 (lines 118 to 133).
2. It reads the reference listing, the new listing and both `offsets.tsv` tables with the helpers `sections` and `offsets`. A file that cannot be used ends the script with exit status 2 (lines 134 to 139).
3. It ends with exit status 2 when the reference listing has no usable kernel of the reference binary, or when the new listing has no block of the new binary (lines 140 to 147).
4. For each kernel of the reference it compares the function text without addresses and the loop start modulo 64, and it checks both `offsets.tsv` rows. It prints one row per kernel (lines 149 to 185).
5. It checks the places of the table of global addresses over all kernels. It rejects a kernel that the reference does not hold (lines 186 to 193).
6. It prints the summary line. It returns 0 when no check failed, and 1 when a check failed (lines 194 to 199).

## Behavior a reader must know

- The script runs no binary and reads no clock. It compares text files. It writes no file and prints its table to the standard output.
- Exit status: 0 all checks passed, 1 a check failed, 2 a file could not be used or the arguments are wrong.
- The default place of the reference files is the folder `crb-build-2` of the folder `bwx-2026-11-13` (line 47). The code repo holds no such folder. Without the options `--ref-listing` and `--ref-offsets` the script cannot read the reference there and ends with exit status 2 (lines 134 to 139). The repo keeps the two reference files in the build record `bwx-crb-build-2` [Ref3].
- The reference files hold four binaries: `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`. The script uses the binary `bwx` only (line 141) [Ref3].
- The repo holds no saved output of this script for the CRB build [Ref6]. A note of the project gives the result: 21 of 21 kernels `same` with the reference offsets, and no note [Ref1]. The table `offsets.tsv` of the CRB build gives each of the 21 kernels the `loop_mod64` value that the reference table gives it for the binary `bwx` [Ref5].
- What the script proves for a kernel with `same` and `ok`: every instruction of the function in `bwx8`, with every operand, equals the instruction at the same position in the accepted build of `bwx`, and the loop start modulo 64 is equal. Addresses are left out of the comparison in the way that lines 22 to 37 define.
- Limit: the script proves equality with `bwx` only. It holds no expected instruction list for any kernel.
- Limit: the script checks kernel functions only. `listing.txt` holds no other function. So the script does not check the code that calls and times a kernel, and not the code of the trial mode that `bwx8` adds.

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/check_listing8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (199 lines, 9441 bytes, sha256 `9dd2ae1b45bd2d0334a71b51d661995f7300e92a53c8eaa39c537fd90c65ded7`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Documentation text: what the script is, usage and reference (lines 1 to 12)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""check_listing8.py - acceptance test of a bwx8 build (design tackle-8mb.md,` | Starts the documentation text of the script (lines 2 to 41). Python does not execute it. `main` prints it when it finds too many arguments or an unknown option (line 130). This line: the script is the acceptance test of a build of the runner program `bwx8`. It accepts or rejects a build. Its input is the machine code of every kernel, as text. A kernel is one inner loop of the benchmark that reads, writes or copies memory. |
| 3 | `"Fixed setup": reject a build whose acceptance listing differs).` | Documentation text: the design note `tackle-8mb.md`, section "Fixed setup", gives the rule that a build is rejected when its acceptance listing differs. |
| 5 | `Runs on the development machine, on the listing.txt and offsets.tsv that` | Documentation text: the script runs on the development machine, not on CRB (the Arm reference server under test). It reads the files `listing.txt` and `offsets.tsv` that ... |
| 6 | `build8.sh wrote on CRB.` | Documentation text: ... the build script `build8.sh` wrote on CRB. |
| 7 | `Usage: check_listing8.py [listing.txt [offsets.tsv]]` | Documentation text: the usage. Both file arguments are optional. Line 132 and line 133 set the defaults. |
| 8 | `           [--ref-listing F] [--ref-offsets F] [--binary bwx8] [--ref-binary bwx]` | Documentation text: the four options. `--ref-listing` and `--ref-offsets` name other reference files. `--binary` and `--ref-binary` give the names of the two binaries as they stand in the title lines of the listings. The defaults are `bwx8` and `bwx`. |
| 10 | `The reference is the saved accepted build of bwx: crb-build-2/listing.txt and` | Documentation text: the reference is the saved accepted build of `bwx`, the first runner version. Its files are `listing.txt` in the folder `crb-build-2` and ... |
| 11 | `offsets.tsv in the folder bwx-2026-11-13, binary "bwx".` | Documentation text: ... `offsets.tsv` in the same folder. That folder lies in the folder `bwx-2026-11-13`. The name of the binary in these files is `bwx`. The code repo holds no folder `crb-build-2`. It keeps the two files in the build record `bwx-crb-build-2` of the test data [Ref3]. The two files hold four binaries. The script uses the blocks and the rows of the binary `bwx` only (line 141). |

### Documentation text: the checks, the meaning of "apart from addresses", and the exit status (lines 13 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 13 | `Checks, for every kernel of the reference binary:` | Documentation text: four checks follow. They hold for every kernel of the reference binary. |
| 14 | ` 1. the new listing has the kernel, and the function has a loop;` | Documentation text: rule 1 for a kernel of the reference. The new listing has the kernel, and the function has a loop. Lines 154 to 158 implement it. |
| 15 | ` 2. the whole function text equals the reference text, apart from addresses;` | Documentation text: rule 2 for a kernel of the reference. The whole function text equals the reference text, apart from addresses. Lines 160 to 163 implement it. |
| 16 | ` 3. the loop start modulo 64 equals the reference value. Both are computed` | Documentation text: rule 3 for a kernel of the reference. The loop start modulo 64 equals the reference value (lines 172 to 173). The loop start modulo 64 is the remainder of the loop start address divided by 64. Both values are computed ... |
| 17 | `    from the listings;` | Documentation text: ... from the listings. |
| 18 | ` 4. the row of the kernel in the new offsets.tsv gives the same loop_mod64 as` | Documentation text: rule 4 for a kernel of the reference. The row of the kernel in the new `offsets.tsv` gives the same `loop_mod64` as ... Lines 174 to 177 implement it. |
| 19 | `    the new listing and as the row of the reference offsets.tsv.` | Documentation text: ... the new listing and as the row of the reference `offsets.tsv`. |
| 20 | `A kernel of the new listing that the reference lacks is a failure.` | Documentation text: one more check. A kernel of the new listing that the reference lacks is a failure. Lines 190 to 193 implement it. |
| 22 | `What "apart from addresses" means here:` | Documentation text: lines 23 to 37 define how two functions at different addresses are compared. The function `whole` (line 94) implements it. |
| 23 | ` - an instruction address is not compared;` | Documentation text: an instruction address is not compared. |
| 24 | ` - a branch target inside the function is compared as its distance from the` | Documentation text: a branch target inside the function is compared as its distance from the ... |
| 25 | `   function start;` | Documentation text: ... function start. |
| 26 | ` - a target outside the function (the stub of bl, the page of a single adrp)` | Documentation text: a target outside the function ... The text names two cases: the stub that a `bl` calls, and the page of a single `adrp`. `bl` is the call instruction. The listing of the CRB build has 2 `bl` instructions, one in `oldread` and one in `oldread2`. Both call `__stack_chk_fail@plt`, the function for a failed stack guard [Ref2]. |
| 27 | `   is compared by its symbol name, not by its address;` | Documentation text: ... is compared by its symbol name, not by its address. The code keeps all that stands in the angle brackets (line 105). When the listing shows a symbol name plus an offset there, the offset is compared too. |
| 28 | ` - the pair "adrp xN, page" + "ldr xN, [xN, #offset]" loads a pointer from` | Documentation text: the pair `adrp xN, page` and `ldr xN, [xN, #offset]` loads a pointer from ... `adrp` puts the address of a 4096-byte page into a register. The `ldr` after it loads a pointer from that page. |
| 29 | `   the table of global addresses of the binary. In the reference only the` | Documentation text: ... the table of global addresses of the binary. This table holds addresses of global objects of the binary. In the reference only the ... |
| 30 | `   load of the stack-guard pointer has this form. Page and offset are the` | Documentation text: ... load of the stack-guard pointer has this form. The page and the offset are the ... |
| 31 | `   place of the pointer in that table. The linker sets them, so they are not` | Documentation text: ... place of the pointer in that table. The linker sets them. So they are not ... |
| 32 | `   compared with the reference. The pair is accepted only where the reference` | Documentation text: ... compared with the reference. The pair is accepted only where the reference ... |
| 33 | `   has it, because the rest of the text must be equal. The listing does not` | Documentation text: ... has it: the rest of the text must be equal. The listing does not ... |
| 34 | `   name the pointer. So this is checked: the new listing must not use more` | Documentation text: ... name the pointer. So one more check is made: the new listing must not use more ... |
| 35 | `   places of the table than the reference, per function and over all` | Documentation text: ... places of the table than the reference, per function (lines 167 to 169) and over all ... |
| 36 | `   kernels. The reference uses one place. A row whose offset differs from the` | Documentation text: ... kernels (lines 186 to 189). The reference uses one place. A row whose offset differs from the ... |
| 37 | `   reference prints "NOTE: got_offset_differs" in place of "ok": read it.` | Documentation text: ... reference prints `NOTE: got_offset_differs` in place of `ok` (lines 170 to 171). The text asks the reader to read such a row. |
| 38 | `The loop of a function is the range from the target of its first backward` | Documentation text: the definition of the loop. The loop of a function is the range from the target of its first backward ... A backward branch is a branch whose target address is lower than its own address. |
| 39 | `branch to that branch.` | Documentation text: ... branch to that branch. The function `loop_start` (line 84) finds the first address of the loop. |
| 40 | `Exit status: 0 all checks passed; 1 a check failed; 2 a file could not be used.` | Documentation text: the exit statuses. 0: all checks passed. 1: a check failed. 2: a file could not be used. The code also returns 2 for wrong arguments (line 126, line 131). The exit status is the return value of `main` (line 199). |
| 41 | `"""` | Ends the documentation text. |

### Imports and constants (lines 42 to 50)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `import os` | Loads the module `os`. The script uses it for file paths. |
| 43 | `import re` | Loads the module `re` for regular expressions. |
| 44 | `import sys` | Loads the module `sys` for the arguments and the exit status. |
| 46 | `HERE = os.path.dirname(os.path.abspath(__file__))` | `HERE`: the folder of this script. |
| 47 | `REF_DIR = os.path.join(HERE, "..", "bwx-2026-11-13", "crb-build-2")` | `REF_DIR`: the place of the reference files. It is the folder `crb-build-2` in the folder `bwx-2026-11-13`, which stands beside the folder of this script (`..` is the folder above). The code repo holds no such folder (see the row of line 11). |
| 48 | `TARGET = re.compile(r"\b([0-9a-f]+) <[^>]+>$")` | `TARGET`: a compiled pattern for a branch target at the end of an instruction: a hexadecimal address, a space and a name in angle brackets. Group 1 holds the address. The page operand of an `adrp` instruction has the same form. The pattern matches it too. Two examples from the listing of the CRB build (`listing.txt`): the branch target `4024 <k_read+0x4>` and the page operand `2f000 <__FRAME_END__+0x1e454>` [Ref2]. |

### Functions `sections` and `offsets`: read the two kinds of input file (lines 51 to 83)

| Line | Source | Explanation |
|---:|---|---|
| 51 | `def sections(path):` | Starts the function `sections`. It reads a listing file. |
| 52 | `    """{(binary, kernel): [(address, text), ...]} from the '=== binary kernel ===' blocks of objdump text"""` | Documentation text of `sections`: it returns a dictionary. A key is the pair (binary, kernel). Its value is the list of (address, instruction text) of that kernel function, in file order. Example: in the listing of the CRB build (`listing.txt`) the first block starts with the title line `=== bwx8 read ===`. The label line `0000000000004020 <k_read>:` follows it. It is no instruction line and is skipped (line 60) [Ref2]. |
| 53 | `    out, cur = {}, None` | `out`: the dictionary. `cur`: the list of the block that is read now. It is `None` outside a block. |
| 54 | `    with open(path) as f:` | Opens the file. |
| 55 | `        for line in f:` | Loop over the lines of the file. |
| 56 | `            m = re.match(r"=== (\S+) (\S+) ===", line)` | Tests whether the line is a title line of the form `=== BINARY KERNEL ===`. Group 1 holds the name of the binary, group 2 the name of the kernel. |
| 57 | `            if m:` | A title line starts the block of one kernel. |
| 58 | `                cur = out.setdefault((m.group(1), m.group(2)), [])` | `cur` becomes the list for this pair. `setdefault` creates an empty list when the pair is new. |
| 59 | `                continue` | Goes to the next line. |
| 60 | `            m = re.match(r"\s*([0-9a-f]+):\s+(.*)", line)` | Tests whether the line is an instruction line: spaces, a hexadecimal address (group 1), a colon, spaces or tabs, and the instruction (group 2). The label line of a function has no colon directly after its address. So it does not match and is skipped. |
| 61 | `            if m and cur is not None:` | Only inside a block ... |
| 62 | `                text = re.sub(r"\s+", " ", m.group(2).split("//")[0]).strip()` | ... the text is cleaned. The `objdump` comment after `//` is cut off. Each run of spaces and tabs becomes one space. |
| 63 | `                cur.append((int(m.group(1), 16), text))` | Appends the pair of the address as a number and the cleaned text to the block. |
| 64 | `            elif line.startswith("##"):` | A line that starts with `##` ... |
| 65 | `                cur = None` | ... ends the block that is read now. |
| 66 | `    return out` | Returns the dictionary. |
| 69 | `def offsets(path):` | Starts the function `offsets`. It reads a file `offsets.tsv`. |
| 70 | `    """{(binary, kernel): loop_mod64 as text} from offsets.tsv"""` | Documentation text of `offsets`: it returns a dictionary from (binary, kernel) to the text of the column `loop_mod64`. |
| 71 | `    out = {}` | `out`: the dictionary. |
| 72 | `    with open(path) as f:` | Opens the file. |
| 73 | `        head = f.readline().rstrip("\n").split("\t")` | `head`: the fields of the first line, split at the tab characters. |
| 74 | `        if head != ["binary", "kernel", "function", "start", "loop_start", "loop_mod64"]:` | The first line must hold exactly the 6 column names. |
| 75 | `            raise ValueError("%s: unexpected header line" % path)` | If not, the function raises `ValueError` with the text `unexpected header line`. `main` then ends with exit status 2 (lines 137 to 139). |
| 76 | `        for line in f:` | Loop over the other lines. |
| 77 | `            p = line.rstrip("\n").split("\t")` | `p`: the fields of the line. |
| 78 | `            if len(p) != 6:` | Every row must have 6 fields. |
| 79 | `                raise ValueError("%s: a row with %d fields" % (path, len(p)))` | If not, the function raises `ValueError`. |
| 80 | `            out[(p[0], p[1])] = p[5]` | Stores column 6 under the pair of column 1 and column 2. The script uses columns 1, 2 and 6 only. It ignores the columns `function`, `start` and `loop_start`. |
| 81 | `    return out` | Returns the dictionary. |

### Functions `loop_start` and `whole` (lines 84 to 116)

| Line | Source | Explanation |
|---:|---|---|
| 84 | `def loop_start(insns):` | Starts the function `loop_start`. `insns` is the list of (address, text) of one function. |
| 85 | `    """address of the loop start: the target of the first backward branch into the function, or None"""` | Documentation text of `loop_start`: it returns the address of the loop start. That is the target of the first backward branch into the function. Without such a branch the result is `None`. |
| 86 | `    first = insns[0][0]` | `first`: the address of the first instruction of the function. |
| 87 | `    for addr, text in insns:` | Goes through the instructions in order. |
| 88 | `        m = TARGET.search(text)` | Looks for a branch target at the end of the instruction text. |
| 89 | `        if m and first <= int(m.group(1), 16) < addr:` | The branch counts when its target lies inside the function and before the branch itself (`first <= target < addr`). |
| 90 | `            return int(m.group(1), 16)` | Returns that target. This address is the loop start. `main` computes a loop start modulo 64 as `loop_start(...) % 64`. |
| 91 | `    return None` | Returns `None` when the function has no such branch. |
| 94 | `def whole(insns):` | Starts the function `whole`. It returns the text of a function in a form that does not depend on the addresses. |
| 95 | `    """(function text without addresses, the places (page, offset) of the pointer loads from the table)"""` | Documentation text of `whole`: it returns two lists. The first is the function text without addresses (`out`). The second holds the places (page, offset) of the pointer loads from the table of global addresses (`got`). Two examples with text of the listing of the CRB build (`listing.txt`): `b.hi 4024 <k_read+0x4>` becomes `b.hi +0x4` (line 102), and the call of `__stack_chk_fail@plt` becomes `bl (outside <__stack_chk_fail@plt>)` (line 105) [Ref2]. |
| 96 | `    first, last, out, got = insns[0][0], insns[-1][0], [], []` | `first` and `last`: the addresses of the first and the last instruction. `out` and `got`: the two result lists. |
| 97 | `    adrp_reg = adrp_page = None` | `adrp_reg` and `adrp_page`: the register and the page of an `adrp` instruction, kept for the next instruction only. |
| 98 | `    for _, text in insns:` | Loop over the instruction texts. |
| 99 | `        m = TARGET.search(text)` | Looks for a target at the end of the text. |
| 100 | `        page = None` | `page`: the address text of a target outside the function. `None` at first. |
| 101 | `        if m and first <= int(m.group(1), 16) <= last:` | A target inside the function ... |
| 102 | `            text = text[:m.start()] + "+0x%x" % (int(m.group(1), 16) - first)` | ... becomes its distance from the function start, written as `+0x` and hexadecimal digits. |
| 103 | `        elif m:` | A target outside the function: |
| 104 | `            page = m.group(1)` | `page` keeps the address text for line 112. |
| 105 | `            text = text[:m.start()] + "(outside %s)" % text[m.start():].split(" ", 1)[1]` | The text becomes `(outside NAME)`. NAME is all that stands in the angle brackets, with the brackets: a symbol name, or a symbol name plus an offset. It is kept, and the address before it is removed. |
| 106 | `        load = re.fullmatch(r"ldr (x\d+), \[(x\d+), #(\d+)\]", text)` | `load`: tests whether the whole text is a load of the form `ldr xA, [xB, #N]`. The groups hold the two registers and the offset. |
| 107 | `        if load and adrp_reg and load.group(1) == adrp_reg and load.group(2) == adrp_reg:` | The pair counts when the instruction before was an `adrp` with a page, and both registers of the load are the register of that `adrp`. |
| 108 | `            got.append((adrp_page, load.group(3)))` | Records the place (page, offset) in `got`. |
| 109 | `            out[-1] = "adrp %s, (table page)" % adrp_reg` | Replaces the text of the `adrp` before by the fixed text `adrp xN, (table page)`. |
| 110 | `            text = "ldr %s, [%s, #(table)]" % (adrp_reg, adrp_reg)` | Replaces the text of the load by the fixed text `ldr xN, [xN, #(table)]`. So the page and the offset are not part of the text comparison. In the listing of the CRB build and in the blocks of `bwx` in the reference listing only `oldread` and `oldread2` have this pair. Each has it twice. The page address is `2f000` in the CRB build and `1f000` in the reference (both hexadecimal). The offset is 4072 bytes in both [Ref2] [Ref3]. |
| 111 | `        m = re.match(r"adrp (x\d+), ", text)` | Tests whether this instruction is an `adrp`. Group 1 holds its register. |
| 112 | `        adrp_reg, adrp_page = (m.group(1), page) if m and page else (None, None)` | Remembers the register and the page of an `adrp` with a page outside the function. Every other instruction clears both values. |
| 113 | `        out.append(text)` | Appends the text to `out`. |
| 114 | `    return out, got` | Returns the two lists. |

### Function `main`: arguments and input files (lines 117 to 148)

| Line | Source | Explanation |
|---:|---|---|
| 117 | `def main():` | Starts the function `main`. Its return value becomes the exit status (line 199). |
| 118 | `    args = sys.argv[1:]` | `args`: the arguments of the command line without the script name. |
| 119 | `    opt = {"--ref-listing": os.path.join(REF_DIR, "listing.txt"), "--ref-offsets": os.path.join(REF_DIR, "offsets.tsv"),` | `opt`: the defaults of the 4 options that take a value. The reference files are `listing.txt` and `offsets.tsv` in the folder `REF_DIR`. |
| 120 | `           "--binary": "bwx8", "--ref-binary": "bwx"}` | Continues the dictionary of line 119: the default names of the two binaries, `bwx8` for the new binary and `bwx` for the reference. |
| 121 | `    for name in opt:` | Loop over the 4 option names. |
| 122 | `        if name in args:` | An option that is present ... |
| 123 | `            i = args.index(name)` | ... stands at position `i` ... |
| 124 | `            if i + 1 >= len(args):` | ... and needs one more argument after it. |
| 125 | `                print("%s needs a value" % name)` | Without it the script prints that the option needs a value ... |
| 126 | `                return 2` | ... and ends with exit status 2. |
| 127 | `            opt[name] = args[i + 1]` | The next argument becomes the value of the option. |
| 128 | `            del args[i:i + 2]` | Both are removed from the list. |
| 129 | `    if len(args) > 2 or any(a.startswith("--") for a in args):` | More than 2 remaining arguments, or a remaining argument that starts with `--` ... |
| 130 | `        print(__doc__)` | ... print the documentation text ... |
| 131 | `        return 2` | ... and the script ends with exit status 2. |
| 132 | `    listing = args[0] if args else os.path.join(HERE, "listing.txt")` | `listing`: the first remaining argument, or `listing.txt` in the folder of the script. |
| 133 | `    offs = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.abspath(listing)), "offsets.tsv")` | `offs`: the second remaining argument, or `offsets.tsv` in the folder of the listing. |
| 134 | `    try:` | Starts the block in which a file error is caught. |
| 135 | `        ref, got = sections(opt["--ref-listing"]), sections(listing)` | Reads the reference listing into `ref` and the new listing into `got`. |
| 136 | `        ref_off, got_off = offsets(opt["--ref-offsets"]), offsets(offs)` | Reads the reference `offsets.tsv` into `ref_off` and the new `offsets.tsv` into `got_off`. |
| 137 | `    except (OSError, ValueError) as e:` | A file that cannot be opened (`OSError`), or an offsets table with a wrong form (`ValueError`) ... |
| 138 | `        print("cannot use: %s" % e)` | ... prints `cannot use:` and the reason ... |
| 139 | `        return 2` | ... and ends the script with exit status 2. |
| 140 | `    b, rb = opt["--binary"], opt["--ref-binary"]` | `b`: the name of the new binary. `rb`: the name of the reference binary. |
| 141 | `    kernels = [k for (bb, k) in ref if bb == rb]` | `kernels`: the list of the kernel names of the reference binary, in the order of the reference listing. |
| 142 | `    if not kernels or any(not ref[(rb, k)] or loop_start(ref[(rb, k)]) is None for k in kernels):` | One more case that ends with exit status 2: the reference listing has no kernel of the reference binary, or a reference kernel has no instructions or no loop. |
| 143 | `        print("the reference listing has no usable block of binary %s" % rb)` | Prints a message that names the reference binary ... |
| 144 | `        return 2` | ... and ends with exit status 2. |
| 145 | `    if not any(bb == b for bb, _ in got):` | One more case: the new listing has no block of the new binary. |
| 146 | `        print("no '=== %s kernel ===' block in %s" % (b, listing))` | Prints a message that names the new binary and the listing file ... |
| 147 | `        return 2` | ... and ends with exit status 2. |

### Function `main`: one output row per kernel of the reference, and the exit status (lines 149 to 199)

| Line | Source | Explanation |
|---:|---|---|
| 149 | `    bad, r_places, g_places = 0, set(), set()` | `bad`: the count of failures that the summary line prints as `failed_rows`. It counts each kernel of the reference whose row fails, and 1 for each of the two checks over the whole listing that fails (lines 186 to 193). `r_places` and `g_places`: the places of the table of global addresses that the reference listing and the new listing use, over all kernels. |
| 150 | `    print("kernel\tstart\tloop_start\tloop_mod64\tref_loop_mod64\ttext\tresult")` | Prints the column names of the output table of the reference kernels, with tabs between them: `kernel`, `start`, `loop_start`, `loop_mod64`, `ref_loop_mod64`, `text`, `result`. |
| 151 | `    for k in kernels:` | Loop over the kernels of the reference. |
| 152 | `        r_insns, insns = ref[(rb, k)], got.get((b, k), [])` | `r_insns`: the instructions of the kernel in the reference listing. `insns`: its instructions in the new listing, or an empty list when the new listing has no block for it. |
| 153 | `        r_mod = loop_start(r_insns) % 64` | `r_mod`: the loop start modulo 64 of the kernel in the reference listing. |
| 154 | `        loop = loop_start(insns) if insns else None` | Rule 1: `loop` is the loop start in the new listing. It is `None` when the block is missing or the function has no backward branch. |
| 155 | `        if loop is None:` | In that case ... |
| 156 | `            print("%s\tNA\tNA\tNA\t%d\t-\tFAIL: no listing or no loop" % (k, r_mod))` | ... the row says `FAIL: no listing or no loop`, with `NA` in the three columns of the new listing ... |
| 157 | `            bad += 1` | ... `bad` grows by 1 ... |
| 158 | `            continue` | ... and the loop goes to the next kernel. |
| 159 | `        problems, notes = [], []` | `problems` and `notes`: the texts for the result column of this kernel. |
| 160 | `        (r_text, r_got), (text, g_got) = whole(r_insns), whole(insns)` | Rule 2, the function text. `whole` (line 94) gives the text without addresses and the table places of the reference function (`r_text`, `r_got`) and of the new function (`text`, `g_got`). |
| 161 | `        same = text == r_text` | `same`: true when the two text lists are equal. They then hold the same number of instructions, and each instruction text is equal with every operand. |
| 162 | `        if not same:` | When the text is not equal ... |
| 163 | `            problems.append("function text differs from the reference")` | ... this is a problem. |
| 164 | `        else:` | When the text is equal: |
| 165 | `            r_places.update(r_got)` | The places of the reference function are added to `r_places` ... |
| 166 | `            g_places.update(g_got)` | ... and the places of the new function to `g_places`. |
| 167 | `            if len(set(g_got)) > len(set(r_got)):` | More distinct places in the new function than in the reference function ... |
| 168 | `                problems.append("the pointer loads after adrp use %d places of the table (%s), the reference uses %d" %` | ... is a problem. Its text gives the number of places of the new function ... |
| 169 | `                                (len(set(g_got)), ", ".join("page %s offset %s" % g for g in g_got), len(set(r_got))))` | ... each place with its page and offset, and the number of the reference. |
| 170 | `            elif [o for _, o in g_got] != [o for _, o in r_got]:` | A new function with no more places than the reference, but with other offsets ... |
| 171 | `                notes.append("got_offset_differs (%s, reference %s)" % (",".join(o for _, o in g_got), ",".join(o for _, o in r_got)))` | ... gets a note and not a failure. When the row has no failure, its result column then starts with `NOTE: got_offset_differs` in place of `ok`. |
| 172 | `        if loop % 64 != r_mod:` | Rule 3: the loop start modulo 64 of the new listing must equal the reference value. |
| 173 | `            problems.append("loop offset modulo 64 is %d, reference %d" % (loop % 64, r_mod))` | If not, a problem gives both values. |
| 174 | `        if ref_off.get((rb, k)) != str(r_mod):` | Rule 4: the reference `offsets.tsv` must hold the reference value for this kernel. |
| 175 | `            problems.append("reference offsets.tsv gives %s" % ref_off.get((rb, k), "no row"))` | If not, a problem gives the value of the table, or `no row`. |
| 176 | `        if got_off.get((b, k)) != str(loop % 64):` | The new `offsets.tsv` must hold the value of the new listing. |
| 177 | `            problems.append("offsets.tsv gives %s, the listing gives %d" % (got_off.get((b, k), "no row"), loop % 64))` | If not, a problem gives both values. |
| 178 | `        print("%s\t%x\t%x\t%d\t%d\t%s\t%s" % (k, insns[0][0], loop, loop % 64, r_mod, "same" if same else "DIFFERS",` | Prints the row of the kernel: the kernel name, the function start and the loop start (hexadecimal addresses), the loop start modulo 64, the reference value, `same` or `DIFFERS` ... |
| 179 | `                                             "FAIL: " + "; ".join(problems) if problems else "NOTE: " + "; ".join(notes) if notes else "ok"))` | ... and the result: `FAIL:` with the problems, or `NOTE:` with the notes, or `ok`. |
| 180 | `        if not same:` | When the text differs ... |
| 181 | `            for i in range(max(len(text), len(r_text))):` | ... a loop over the positions of the longer text ... |
| 182 | `                g = text[i] if i < len(text) else "(none)"` | ... takes the new instruction text, or `(none)` past the end ... |
| 183 | `                w = r_text[i] if i < len(r_text) else "(none)"` | ... and the reference instruction text, or `(none)` past the end. |
| 184 | `                print("    %s %-40s \| reference %s" % ("  " if g == w else "!=", g, w))` | Prints both texts side by side, with a `\|` between them. The mark `!=` stands before a line that differs. |
| 185 | `        bad += bool(problems)` | `bad` grows by 1 when the kernel has a problem. |
| 186 | `    if len(g_places) > len(r_places):` | After the loop, a check over all kernels with equal text: the new listing may not use more distinct places of the table of global addresses than the reference. |
| 187 | `        print("FAIL: the pointer loads after adrp use %d places of the table over all kernels (%s), the reference uses %d" %` | If it does, a line that starts with `FAIL:` gives the number of places of the new listing ... |
| 188 | `              (len(g_places), ", ".join("page %s offset %s" % g for g in sorted(g_places)), len(r_places)))` | ... the places, and the number of the reference. |
| 189 | `        bad += 1` | `bad` grows by 1. |
| 190 | `    extra = sorted(k for bb, k in got if bb == b and k not in kernels)` | `extra`: the kernels of the new binary in the new listing that are not in the reference. |
| 191 | `    if extra:` | When there is such a kernel ... |
| 192 | `        print("FAIL: kernels in the listing that the reference lacks: %s" % ", ".join(extra))` | ... a line that starts with `FAIL:` names them ... |
| 193 | `        bad += 1` | ... and `bad` grows by 1. |
| 194 | `    print("# binary=%s reference=%s kernels=%d failed_rows=%d" % (b, rb, len(kernels), bad))` | Prints the summary line. It starts with `# binary=` and the name of the new binary, then `reference=` and the name of the reference binary, then `kernels=` with the number of reference kernels and `failed_rows=` with the value of `bad`. The repo holds no saved output of this script for the CRB build [Ref6]. By a note of the project, the script found 21 of 21 kernels `same` with the reference offsets for that build, and it printed no note [Ref1]. |
| 195 | `    return 1 if bad else 0` | `main` returns 1 when a check failed, and 0 when none failed. |
| 198 | `if __name__ == "__main__":` | This test is true when the file runs as a script. |
| 199 | `    sys.exit(main())` | Calls `main` and makes its return value the exit status of the script. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx8-2026-11-14/DECISIONS-bwx8.md`: a note of the project. Its section "CRB acceptance, 2026-11-15" names the build `crb-build-1` with gcc 14.2.0. It says that `check_listing8.py` gives 21 of 21 kernels "same" with the reference offsets, and no note.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/listing.txt`: the listing of the CRB build, with 21 blocks. The first block has the title line `=== bwx8 read ===` and the label line `0000000000004020 <k_read>:`. `k_read` holds `b.hi 4024 <k_read+0x4>`. The only `bl` instructions of the file are two calls of `__stack_chk_fail@plt`, in `k_oldread` and `k_oldread2`. The only `adrp` instructions are in the same two functions: two pairs of `adrp` and `ldr` each, with the page operand `2f000 <__FRAME_END__+0x1e454>` and the offset 4072.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/`: the record of the second CRB build of `bwx`, with `listing.txt` (84 blocks: 21 kernels for each of the binaries `bwx`, `bwx_o0`, `bwx_o36` and `bwx_o52`) and `offsets.tsv` (84 kernel rows). A `cmp` in this task found these two files equal to the two files in `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/crb-build-2/`, the default reference folder of the copy of the script in the project folder. In the blocks of `bwx`, `k_oldread` and `k_oldread2` hold two pairs of `adrp` and `ldr` each, with the page address `1f000` and the offset 4072, and no other function holds an `adrp`. The folder `bwx-2026-11-13` of the code repo holds no folder `crb-build-2`.
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/report/tackle-8mb.md`: the design note. Its title is "Design: explain the small read-bandwidth gain at 8 MiB". Its section "Fixed setup" holds the sentence "Reject a build whose acceptance listing differs."
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-15-tackle-8mb/build-records/bwx8-crb-build-1/offsets.tsv`: the table of the CRB build, with 21 kernel rows. Checked in this task with a script: the 21 kernel names and their `loop_mod64` values equal the 21 rows of the binary `bwx` in `offsets.tsv` of the record of [Ref3].
- [Ref6] Searched in this task with `grep -r` in the folders `tests` and `status` of the repo for the text `failed_rows=`, which the summary line of this script holds. The search found two files: `check_listing12.out` and `check_listing13.out`, the saved outputs of the listing checks of bwx12 and bwx13.
