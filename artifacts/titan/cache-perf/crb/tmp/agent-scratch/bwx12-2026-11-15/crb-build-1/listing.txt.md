# `listing.txt` explained

- Source file: `listing.txt` in this folder (text file, 3921 lines, 78890 bytes).
- sha256 of the source when this page was built: `d796325cfbdeb05b259e79406e21489ec0c58ef69957fdb3a1643ceca4f9692f`.
- Role in the whole-chip test: Machine instructions of every bwx12 kernel, as text, written when bwx12 was built.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.
- The table shows only the parts of the file that the whole-chip test uses. A row says which lines are left out.

## Short version: purpose

This file holds the machine instructions of the 55 kernel functions of the binary bwx12, as text. The build script build12.sh wrote it on CRB on 2026-11-15 with the tool objdump, in the same run that compiled bwx12 [Ref1] [Ref10].

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **build12.sh**: the build script of bwx12. It ran on CRB. It compiled bwx12.c, ran the self-test and wrote this file, build.txt and offsets.tsv.
- **objdump**: the tool that prints the machine instructions of a binary file as text.
- **gcc**: the C compiler that built bwx12.
- **-O3, -march=native, -pthread, -Wall, -Wextra, -std=gnu11**: gcc flags. `-O3` is optimisation level 3. With `-march=native` gcc picks the instruction set of the machine that it runs on. `-pthread` links the thread library. `-Wall` and `-Wextra` enable warnings. `-std=gnu11` selects the C language of 2011 with GNU extensions [Ref18].
- **-fno-tree-loop-distribute-patterns**: a gcc flag. With it gcc does not replace a loop by a call of a library function such as `memset` [Ref18].
- **-fno-ipa-icf, -fno-toplevel-reorder, -falign-functions=4**: gcc flags. With `-fno-ipa-icf` gcc does not merge two functions that have the same code. With `-fno-toplevel-reorder` gcc keeps the functions in the order of the source file. With `-falign-functions=4` gcc aligns the start of a function to 4 bytes only [Ref18]. bwx12.c needs the last two flags to put each kernel at a chosen address modulo 64 [Ref15].
- **--seq**: the option of bwx12 that names the kernels to time, in their order.
- **Loop pass**: one run of the instructions of the loop, from the loop start to the branch that jumps back.
- **Loop start modulo 64**: the address of the first instruction of the loop, modulo 64. It is the place of the loop start inside a block of 64 bytes of code addresses.
- **B, MiB**: B is a byte. 1 MiB is 1048576 bytes.
- **64 B line**: a block of 64 bytes of memory that starts at an address that is a multiple of 64. The comments of bwx12.c use the word "line" for the block that a cache loads as one piece.
- **Warm-up call**: one call of the kernel over the whole buffer before the timed interval starts. Its time is not measured.
- **build.txt, offsets.tsv**: two more files that build12.sh wrote in the same run. build.txt holds the compiler, the flags and sha256 values. offsets.tsv holds the start address and the loop start of each kernel.
- **check_listing12.py**: the script that accepts or rejects a build of bwx12. It reads this file and offsets.tsv.
- **go.sh, go2.sh**: the driver scripts of the whole-chip test of 2026-11-17. go2.sh ran control I.
- **x0 to x30, sp**: the general registers of a 64-bit Arm CPU (64 bits each) and the stack pointer. `x0` and `x1` carry the first and the second argument of a function. `x0` carries the return value.
- **v0 to v31, qN, dN**: the 32 vector registers of a 64-bit Arm CPU (128 bits each). `qN` names all 16 bytes of register N. `dN` names its low 8 bytes. `vN.2d` names it as two elements of 64 bits.
- **ldp, ldr, stp, str**: Arm instructions. `ldp` loads two registers from memory, `ldr` loads one. `stp` stores two registers to memory, `str` stores one.
- **nop**: the instruction "no operation". It changes no register and no memory.
- **Unsigned compare**: a compare that treats both values as numbers without a sign, as addresses are.
- **AAPCS64**: the calling convention of 64-bit Arm: the rules that say which registers carry arguments and which registers must hold their old values when a function returns.
- **asm statement, macro**: an asm statement is assembler text inside C source. The compiler copies it into the machine code. A macro is a text pattern of the C preprocessor. `DEF_ASMREAD(name, nops)` expands to one kernel function.
- **Stack guard**: a value that compiled code copies to the stack at the start of a function and compares before the return. A changed copy means that the function wrote outside its stack variables.
- **Frame pointer, return address**: the registers `x29` and `x30`. `x29` points to the stack area of the current function. `x30` holds the address at which the caller continues.
- **First touch**: the first write to newly allocated memory. Linux assigns the physical pages at that moment.
- **sha256**: a checksum of 64 hexadecimal digits. Equal values mean equal file content.

</details>

## How to read this file

1. The file holds 55 blocks, one per kernel of bwx12, in the order in which the command `bwx12 --list` prints the kernel names [Ref1]. The table below shows the six kernels of bwx12 that the whole-chip test timed: `read`, `asmread`, `oldread`, `read_1pl`, `read_nop96` and `read_nop256`.
2. A block starts with the header `=== bwx12 <kernel> ===` (line 1).
3. The next line gives the start address of the function (16 hexadecimal digits) and its name `k_<kernel>` (line 2).
4. Each further line is one machine instruction: its address (hexadecimal), the name of the instruction, the operands. Every instruction is 4 bytes long. So the addresses rise by 4 (lines 3-15).
5. In the operands, a number after `#` is decimal unless it starts with `0x`. Example: `#224` is 224, and `#0x100` is 256 (lines 11-12).
6. A branch line shows the target address and, in angle brackets, the same target as function name plus offset. objdump adds the words after `//`: other names of the branch condition, or the decimal value of a constant (line 14).
7. To find the loop of a kernel, look for the branch whose target address is lower than its own address and lies inside the function. The loop is the lines from that target to the branch. Example: the branch at line 14 jumps to `49a4`. That address is line 4. So the loop of `read` is lines 4 to 14.
8. The instructions before the loop and after the loop run at most once per call of the kernel.
9. An empty line ends the block (line 16).

## Behavior a reader must know

- Part L, part C and control I of the whole-chip test ran the binary that this listing describes. build.txt records the sha256 value of the binary bwx12 and of this file from the same build [Ref10]. go.sh and go2.sh stop unless bwx12 has that sha256 value [Ref11]. The binary bwx12 is not in the local folders. Its sha256 value is known only from records such as build.txt, go.sh and go2.sh. On 2026-11-21 the copy of this file in this folder had the sha256 value that build.txt records (checked with `sha256sum`). On the same day the copy of bwx12.c in the parent folder had the sha256 value that build.txt records for the source.
- Part A did not run bwx12. It ran the binaries bw_old and bw_new [Ref16]. In each of the two it timed six kernels: `read`, `write`, `copy`, `asmread`, `asmwrite` and `asmcopy` [Ref16]. Notes below compare their read loops with this listing. The function list below describes the functions of bwx12 only. There, "Not run in the whole-chip test" means that no part of the test ran that function of bwx12.
- Instructions per 256 B of buffer: `read` 11, `asmread` 11, `oldread` 32 (two loop passes of 16), `read_1pl` 7, `read_nop96` 107, `read_nop256` 267.
- The old read kernel and the load-only loops use the same load instruction in the same number: 8 `ldp` of 32 B per 256 B. The old read kernel adds every loaded value to a running sum (16 vector adds per 256 B). The load-only loops use no loaded value.
- `read_1pl` loads 64 B per 256 B. bwx12 counts the whole length of the range that a call covers. So the rate of `read_1pl` counts 256 B per loop pass [Ref8].
- The whole-chip test runs bwx12 with `--bytes 256M` (a buffer of 256 MiB per thread) and `--stop common` [Ref9]. With `--stop common` all threads of an interval have one common deadline. One timed call of a kernel covers 2 MiB, and the thread reads the clock after each call [Ref8]. A thread ends its interval at the first clock read at or after the deadline. A call over 2 MiB runs 8192 passes of a 256 B loop, or 16384 passes of the `oldread` loop. So the instructions before and after a loop run at most once per 2 MiB.
- Before each interval a thread runs one warm-up call of the kernel over its whole 256 MiB buffer. This call is not timed [Ref8].
- Each thread fills its buffer once with `k_write` (lines 17 to 32, not shown below) before the first interval. This first touch is not timed [Ref8].
- The machine instructions of `read`, `asmread` and `oldread` equal those of `k_read` and `k_asmread` of bw_new and of `k_read` of bw_old in the listing of 2026-11-13 [Ref14]. Only addresses and the function name `k_oldread` differ. Each of the three loops starts at the same address modulo 64 as in that listing (36, 20 and 40). A script of this task compared the texts on 2026-11-21. Method: drop the address column, replace each branch target by its distance from the function start, drop the words after `//`, then compare line by line. With this method every line of `read` and of `asmread` is equal. Three lines of `oldread` still differ: the two `adrp` lines (lines 137 and 189) and the `bl` line (line 204). They hold addresses outside the function.
- Part A timed `asmread` in bw_old too [Ref16]. With the same method, every line of `k_asmread` of bw_old in the listing of 2026-11-13 equals the same line of `asmread` in this file [Ref14]. The loop of `k_asmread` of bw_old starts at address 28 modulo 64. The loops of `asmread` in bwx12 and in bw_new start at 20.
- The binaries bw_old and bw_new are not in the local folders. So the comparisons above use the listing of 2026-11-13, not the binaries. The sha256 values of the two binaries are known only from records. The file of that listing holds the two values [Ref14]. ra.sh, the script of part A, stops unless bw_old and bw_new have these values [Ref16].
- bwx12.c pads the code before each kernel. The pad makes the kernel start at a chosen address modulo 64 [Ref15]. offsets.tsv lists the function start, the loop start and the loop start modulo 64 of every kernel [Ref12]. Its values for the six kernels equal the addresses in the table below.
- check_listing12.py compares this file with the accepted listing of bwx11 and with the expected loop of each new kernel. The saved output of this check says `ok` for all 55 kernels and counts 0 failed rows [Ref13].
- The compiler was gcc 14.2.0 with the flags `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4` [Ref10].

## Call sequence in the whole-chip test

- `bwx12.c:main`: reads the arguments and starts 120 threads
  - `bwx12.c:worker`: one thread: pins itself, allocates its buffer, times each kernel
    - `k_write` (line 18): fills the buffer once (first touch), not timed, not shown below
    - `bwx12.c:call`: calls one kernel: one warm-up call, then one call per 2 MiB
      - `k_oldread` (line 134): old read kernel of bwx12, timed in part L, part C and control I
      - `k_asmread` (line 60): hand-written load-only loop of bwx12, timed in part L, part C and control I
      - `k_read_nop96` (line 855): asmread loop plus 96 nop, timed in part L and control I
      - `k_read_nop256` (line 2127): asmread loop plus 256 nop, timed in part L and control I
      - `k_read_1pl` (line 755): one 16 B load per 64 B, timed in part L and control I
      - `k_read` (line 2): new read kernel of bwx12, timed in part C only

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `k_read` | 2-15 | New read kernel, compiled from C with NEON intrinsics. Loop: 8 ldp, add, cmp, branch per 256 B. Uses no loaded value. | - | yes |
| `k_write` | 18-32 | Write loop from C: 8 stp per 256 B. In this test each thread calls it once to fill its buffer (first touch). Not timed. | - | no |
| `k_copy` | 35-57 | Not run in the whole-chip test. Copy loop from C: 8 ldp and 8 stp per 256 B. | - | no |
| `k_asmread` | 60-81 | Hand-written load-only loop: 8 ldp, add, cmp, branch per 256 B. Uses no loaded value. Saves d8 to d15 around the loop. | - | yes |
| `k_asmwrite` | 84-98 | Not run in the whole-chip test. Hand-written write loop: 8 stp per 256 B. | - | no |
| `k_asmcopy` | 101-131 | Not run in the whole-chip test. Hand-written copy loop: 8 ldp and 8 stp per 256 B. | - | no |
| `k_oldread` | 134-204 | Old read kernel, compiled from plain C. Loop: 4 ldp, 8 vector adds, 2 scalar adds, cmp, branch per 128 B. Returns the sum. | `__stack_chk_fail` | yes |
| `k_oldwrite` | 207-220 | Not run in the whole-chip test. Old write loop, compiled from plain C. | - | no |
| `k_oldcopy` | 223-233 | Not run in the whole-chip test. Old copy loop, compiled from plain C. | - | no |
| `k_asmread2` | 236-257 | Not run in the whole-chip test. The source of asmread under a second name. | - | no |
| `k_asmwrite2` | 260-274 | Not run in the whole-chip test. The source of asmwrite under a second name. | - | no |
| `k_asmcopy2` | 277-307 | Not run in the whole-chip test. The source of asmcopy under a second name. | - | no |
| `k_oldread2` | 310-380 | Not run in the whole-chip test. The source of oldread under a second name. | `__stack_chk_fail` | no |
| `k_asmcopy_c` | 383-405 | Not run in the whole-chip test. Hand-written copy loop in the instruction order of the C copy loop: 8 ldp, 8 stp per 256 B. | - | no |
| `k_asmcopy_c_add` | 408-430 | Not run in the whole-chip test. As asmcopy_c, but the two pointer adds stand after the 8 stp. | - | no |
| `k_asmcopy_c_reg` | 433-463 | Not run in the whole-chip test. As asmcopy_c, but with the registers q0 to q15. | - | no |
| `k_read_nop4` | 466-491 | Not run in the whole-chip test. The asmread loop with 4 nop instructions per 256 B. | - | no |
| `k_read_nop8` | 494-523 | Not run in the whole-chip test. The asmread loop with 8 nop instructions per 256 B. | - | no |
| `k_read_nop16` | 526-563 | Not run in the whole-chip test. The asmread loop with 16 nop instructions per 256 B. | - | no |
| `k_read_nop32` | 566-619 | Not run in the whole-chip test. The asmread loop with 32 nop instructions per 256 B. | - | no |
| `k_read_sparse` | 622-640 | Not run in the whole-chip test. Read loop with 4 ldp and 9 nop per 128 B. | - | no |
| `k_read_pf256` | 643-668 | Not run in the whole-chip test. The asmread loop plus 4 prefetch instructions (prfm) per 256 B, 256 B ahead. | - | no |
| `k_read_pf512` | 671-696 | Not run in the whole-chip test. The asmread loop plus 4 prefetch instructions (prfm) per 256 B, 512 B ahead. | - | no |
| `k_read_pf1024` | 699-724 | Not run in the whole-chip test. The asmread loop plus 4 prefetch instructions (prfm) per 256 B, 1024 B ahead. | - | no |
| `k_read_pf2048` | 727-752 | Not run in the whole-chip test. The asmread loop plus 4 prefetch instructions (prfm) per 256 B, 2048 B ahead. | - | no |
| `k_read_1pl` | 755-764 | Test loop with one 16 B load per 64 B: 4 ldr, add, cmp, branch per 256 B. Uses no loaded value. | - | yes |
| `k_read_nop64` | 767-852 | Not run in the whole-chip test. The asmread loop with 64 nop instructions per 256 B. | - | no |
| `k_read_nop96` | 855-972 | The asmread loop with 96 nop instructions per 256 B: 8 ldp, 96 nop, add, cmp, branch. | - | yes |
| `k_read_nop128` | 975-1124 | Not run in the whole-chip test. The asmread loop with 128 nop instructions per 256 B. | - | no |
| `k_read_nop48` | 1127-1196 | Not run in the whole-chip test. The asmread loop with 48 nop instructions per 256 B. | - | no |
| `k_read_nop56` | 1199-1276 | Not run in the whole-chip test. The asmread loop with 56 nop instructions per 256 B. | - | no |
| `k_read_nop72` | 1279-1372 | Not run in the whole-chip test. The asmread loop with 72 nop instructions per 256 B. | - | no |
| `k_read_nop80` | 1375-1476 | Not run in the whole-chip test. The asmread loop with 80 nop instructions per 256 B. | - | no |
| `k_read_nop88` | 1479-1588 | Not run in the whole-chip test. The asmread loop with 88 nop instructions per 256 B. | - | no |
| `k_read_nop112` | 1591-1724 | Not run in the whole-chip test. The asmread loop with 112 nop instructions per 256 B. | - | no |
| `k_read_nop160` | 1727-1908 | Not run in the whole-chip test. The asmread loop with 160 nop instructions per 256 B. | - | no |
| `k_read_nop192` | 1911-2124 | Not run in the whole-chip test. The asmread loop with 192 nop instructions per 256 B. | - | no |
| `k_read_nop256` | 2127-2404 | The asmread loop with 256 nop instructions per 256 B: 8 ldp, 256 nop, add, cmp, branch. | - | yes |
| `k_read_dadd2` | 2407-2438 | Not run in the whole-chip test. The asmread loop plus 2 vector adds of loaded values per 256 B. | - | no |
| `k_read_dadd4` | 2441-2474 | Not run in the whole-chip test. The asmread loop plus 4 vector adds of loaded values per 256 B. | - | no |
| `k_read_dadd8` | 2477-2514 | Not run in the whole-chip test. The asmread loop plus 8 vector adds of loaded values per 256 B. | - | no |
| `k_read_dadd16` | 2517-2562 | Not run in the whole-chip test. The asmread loop plus 16 vector adds of loaded values per 256 B. | - | no |
| `k_read_iadd16` | 2565-2618 | Not run in the whole-chip test. The asmread loop plus 16 vector adds per 256 B. The adds use no loaded value. | - | no |
| `k_read_sp24` | 2621-2654 | Not run in the whole-chip test. Read loop with 4 ldp and 24 nop per 128 B. | - | no |
| `k_read_sp32` | 2657-2698 | Not run in the whole-chip test. Read loop with 4 ldp and 32 nop per 128 B. | - | no |
| `k_read_sp40` | 2701-2750 | Not run in the whole-chip test. Read loop with 4 ldp and 40 nop per 128 B. | - | no |
| `k_read_sp48` | 2753-2810 | Not run in the whole-chip test. Read loop with 4 ldp and 48 nop per 128 B. | - | no |
| `k_read_sp56` | 2813-2878 | Not run in the whole-chip test. Read loop with 4 ldp and 56 nop per 128 B. | - | no |
| `k_read_1pl_nop96` | 2881-2986 | Not run in the whole-chip test. The read_1pl loop with 96 nop instructions per 256 B. | - | no |
| `k_write_nop32` | 2989-3035 | Not run in the whole-chip test. Write loop with 8 stp and 32 nop per 256 B. | - | no |
| `k_write_nop96` | 3038-3148 | Not run in the whole-chip test. Write loop with 8 stp and 96 nop per 256 B. | - | no |
| `k_write_nop128` | 3151-3293 | Not run in the whole-chip test. Write loop with 8 stp and 128 nop per 256 B. | - | no |
| `k_write_nop256` | 3296-3566 | Not run in the whole-chip test. Write loop with 8 stp and 256 nop per 256 B. | - | no |
| `k_copy_nop96` | 3569-3695 | Not run in the whole-chip test. Copy loop with 8 ldp, 8 stp and 96 nop per 256 B. | - | no |
| `k_copy_nop192` | 3698-3920 | Not run in the whole-chip test. Copy loop with 8 ldp, 8 stp and 192 nop per 256 B. | - | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Kernel <code>read</code>: the new read kernel, function <code>k_read</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  === bwx12 read ===</pre></td><td valign="top"><code>=== bwx12 read ===</code> is the header that build12.sh writes before the text of each kernel [Ref1]. <code>read</code> is the name of the kernel in the option <code>--seq</code> of bwx12. It is the new read kernel.<ul><li>The whole-chip test times this function in part C only [Ref9].</li><li>Part A times the new read kernel in another binary, bw_new [Ref16].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   2  00000000000049a0 &lt;k_read&gt;:</pre></td><td valign="top">Start address <code>49a0</code> (hexadecimal) and name of the function. <b>The loop is lines 4 to 14.</b><ul><li>Address range: <code>49a4</code> to <code>49cc</code>. That is 11 instructions, 44 bytes of code. Loop start modulo 64: 36.</li><li>Bytes read per loop pass: 256 B.</li><li>Load instructions per loop pass: 8 (<code>ldp</code>, 32 B each).</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.hi</code>).</li><li>The loaded values are not used.</li><li>Source: the <code>do ... while</code> loop of the C function <code>k_read</code> in bwx12.c [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   3      49a0:	add	x1, x0, x1, lsl #3</pre></td><td valign="top">This instruction runs once per call, before the loop.<ul><li>On entry <code>x0</code> holds <code>a</code>, the address of the first byte to read. <code>x1</code> holds <code>n</code>, the number of 8-byte words to read.</li><li>The instruction computes the end address <code>x1 = x0 + 8 * n</code> (<code>lsl #3</code> multiplies by 8). Source: <code>end = a + n</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   4      49a4:	ldp	q31, q30, [x0]
   5      49a8:	ldp	q29, q28, [x0, #32]
   6      49ac:	ldp	q27, q26, [x0, #64]
   7      49b0:	ldp	q25, q24, [x0, #96]
   8      49b4:	ldp	q23, q22, [x0, #128]
   9      49b8:	ldp	q21, q20, [x0, #160]
  10      49bc:	ldp	q19, q18, [x0, #192]
  11      49c0:	ldp	q17, q16, [x0, #224]</pre></td><td valign="top">The loop starts at line 4. Each <code>ldp</code> (load pair) reads 32 B from memory into two vector registers of 16 B. The 8 instructions read the 256 B that start at <code>x0</code> (offsets 0 to 224 B). No instruction uses the loaded values.<ul><li>Source: 16 calls of <code>vld1q_u64</code> (the C function that loads one vector of 16 B). The compiler joined the 16 loads in pairs: each <code>ldp</code> does two of them.</li><li>An empty <code>asm</code> statement in the source takes the 16 loaded values as inputs. The comment in bandwidth.c says that this keeps gcc from deleting the loads, and that it adds no instruction [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  12      49c4:	add	x0, x0, #0x100</pre></td><td valign="top"><code>add x0, x0, #0x100</code> moves the pointer forward by 256 B (<code>0x100</code> = 256). Source: <code>p += 32</code> (32 words of 8 B). So one pass of this loop is one pass of the <code>do ... while</code> loop of the source.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  13      49c8:	cmp	x1, x0
  14      49cc:	b.hi	49a4 &lt;k_read+0x4&gt;  // b.pmore</pre></td><td valign="top"><code>cmp x1, x0</code> compares the end address with the pointer. <code>b.hi 49a4</code> jumps back to line 4 while the end address is higher (unsigned compare). Source: <code>while (p &lt; end)</code>. objdump adds the words after <code>//</code>: another name of the same branch condition.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  15      49d0:	ret
  16</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value. Line 16 is the empty line that ends the block.</td></tr>
<tr><td colspan="2"><i>Lines 17 to 58 of the file are not shown here.</i></td></tr>
<tr><td colspan="2"><b>Kernel <code>asmread</code>: the hand-written load-only loop, function <code>k_asmread</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  59  === bwx12 asmread ===</pre></td><td valign="top">Header of the kernel <code>asmread</code>, the hand-written load-only loop. The whole-chip test times this function in part L, in part C and in control I [Ref9]. Part A times <code>asmread</code> in other binaries, bw_old and bw_new [Ref16].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  60  0000000000004ac0 &lt;k_asmread&gt;:</pre></td><td valign="top">Start address <code>4ac0</code> (hexadecimal) and name of the function. <b>The loop is lines 66 to 76.</b><ul><li>Address range: <code>4ad4</code> to <code>4afc</code>. That is 11 instructions, 44 bytes of code. Loop start modulo 64: 20.</li><li>Bytes read per loop pass: 256 B.</li><li>Load instructions per loop pass: 8 (<code>ldp</code>, 32 B each).</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>The loaded values are not used.</li><li>Source: the asm text of the macro <code>DEF_ASMREAD</code> in bwx12.c, used as <code>DEF_ASMREAD(asmread, 0)</code> [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  61      4ac0:	stp	d8, d9, [sp, #-64]!
  62      4ac4:	add	x1, x0, x1, lsl #3
  63      4ac8:	stp	d10, d11, [sp, #16]
  64      4acc:	stp	d12, d13, [sp, #32]
  65      4ad0:	stp	d14, d15, [sp, #48]</pre></td><td valign="top">These 5 instructions run once per call, before the loop. The compiler wrote them.<ul><li><code>stp d8, d9, [sp, #-64]!</code> lowers the stack pointer by 64 B and stores <code>d8</code> and <code>d9</code> there. Lines 63 to 65 store <code>d10</code> to <code>d15</code> in the same 64 B.</li><li>Reason: the loop overwrites <code>q8</code> to <code>q15</code>. The calling convention AAPCS64 requires that <code>d8</code> to <code>d15</code> hold their old values when a function returns [Ref4].</li><li><code>add x1, x0, x1, lsl #3</code> (line 62) computes the end address <code>x1 = x0 + 8 * n</code>. Source: <code>end = a + n</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  66      4ad4:	ldp	q0, q1, [x0]
  67      4ad8:	ldp	q2, q3, [x0, #32]
  68      4adc:	ldp	q4, q5, [x0, #64]
  69      4ae0:	ldp	q6, q7, [x0, #96]
  70      4ae4:	ldp	q8, q9, [x0, #128]
  71      4ae8:	ldp	q10, q11, [x0, #160]
  72      4aec:	ldp	q12, q13, [x0, #192]
  73      4af0:	ldp	q14, q15, [x0, #224]</pre></td><td valign="top">The loop starts at line 66 (the label <code>1:</code> of the source). The 8 <code>ldp</code> instructions read the 256 B that start at <code>x0</code> into <code>q0</code> to <code>q15</code>, 32 B per instruction. No instruction uses the loaded values. These are the 8 loads of <code>k_read</code> (lines 4 to 11) with other register numbers.<ul><li>Lines 66 to 76 are the 11 instructions of the asm text of the source, in the same order. The compiler chose only the registers: <code>x0</code> for the pointer and <code>x1</code> for the end address.</li><li>The comment in bandwidth.c says that the compiler cannot add arithmetic, reorder or drop anything inside such an asm block [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  74      4af4:	add	x0, x0, #0x100</pre></td><td valign="top">Moves the pointer forward by 256 B (<code>0x100</code> = 256). Source: <code>add %[p], %[p], #256</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  75      4af8:	cmp	x0, x1
  76      4afc:	b.cc	4ad4 &lt;k_asmread+0x14&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp x0, x1</code> compares the pointer with the end address. <code>b.cc 4ad4</code> jumps back to line 66 while the pointer is lower (unsigned compare). The source writes <code>b.lo</code>, another name of <code>b.cc</code>. <code>k_read</code> tests the same condition with swapped operands (<code>cmp x1, x0</code>, then <code>b.hi</code>).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  77      4b00:	ldp	d10, d11, [sp, #16]
  78      4b04:	ldp	d12, d13, [sp, #32]
  79      4b08:	ldp	d14, d15, [sp, #48]
  80      4b0c:	ldp	d8, d9, [sp], #64</pre></td><td valign="top">These 4 instructions run once per call, after the loop. They load <code>d8</code> to <code>d15</code> back from the stack. <code>ldp d8, d9, [sp], #64</code> also raises the stack pointer by 64 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  81      4b10:	ret
  82</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><i>Lines 83 to 132 of the file are not shown here.</i></td></tr>
<tr><td colspan="2"><b>Kernel <code>oldread</code>: the old read kernel, function <code>k_oldread</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 133  === bwx12 oldread ===</pre></td><td valign="top">Header of the kernel <code>oldread</code>, the old read kernel. The whole-chip test times this function in part L, in part C and in control I [Ref9]. Part A times the old read kernel in another binary, bw_old [Ref16].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 134  0000000000004600 &lt;k_oldread&gt;:</pre></td><td valign="top">Start address <code>4600</code> (hexadecimal) and name of the function. <b>The loop is lines 161 to 176.</b><ul><li>Address range: <code>4668</code> to <code>46a4</code>. That is 16 instructions, 64 bytes of code. Loop start modulo 64: 40.</li><li>Bytes read per loop pass: 128 B. So 256 B take 2 passes (32 instructions).</li><li>Load instructions per loop pass: 4 (<code>ldp</code>, 32 B each).</li><li>Other instructions per loop pass: 12 (8 vector <code>add</code>, 2 scalar <code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>Every loaded value is added to a running sum.</li><li>Source: the two nested <code>for</code> loops of the macro <code>DEF_OLDREAD</code> in bwx12.c, used as <code>DEF_OLDREAD(oldread)</code> [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 135      4600:	movi	v31.4s, #0x0
 136      4604:	sub	sp, sp, #0xa0</pre></td><td valign="top">Lines 135 to 160 (26 instructions) run at most once per call, before the loop. <code>movi v31.4s, #0x0</code> sets the vector register <code>v31</code> to zero. <code>sub sp, sp, #0xa0</code> reserves 160 B on the stack (<code>0xa0</code> = 160).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 137      4608:	adrp	x3, 2f000 &lt;__FRAME_END__+0x16a34&gt;
 138      460c:	ldr	x3, [x3, #4072]
 139      4610:	stp	x29, x30, [sp, #144]
 140      4614:	add	x29, sp, #0x90
 141      4618:	ldr	x4, [x3]
 142      461c:	str	x4, [sp, #136]
 143      4620:	mov	x4, #0x0                   	// #0</pre></td><td valign="top">Stack guard and frame. The C source has no such code. The compiler added it.<ul><li><code>adrp</code> and <code>ldr</code> (lines 137 and 138) load the address of the stack guard value into <code>x3</code>.</li><li><code>stp x29, x30, [sp, #144]</code> saves the frame pointer and the return address. <code>add x29, sp, #0x90</code> sets the frame pointer of this function.</li><li><code>ldr x4, [x3]</code> reads the guard value. <code>str x4, [sp, #136]</code> stores a copy on the stack, above the array <code>s</code>. <code>mov x4, #0x0</code> clears <code>x4</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 144      4624:	stp	q31, q31, [sp]
 145      4628:	stp	q31, q31, [sp, #32]
 146      462c:	stp	q31, q31, [sp, #64]
 147      4630:	stp	q31, q31, [sp, #96]</pre></td><td valign="top">The 4 <code>stp</code> instructions write zero to the 128 B from <code>sp</code> to <code>sp + 127</code>. This is the array <code>s</code> of the source: <code>uint64_t s[16] = { 0 }</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 148      4634:	cbz	x1, 46b8 &lt;k_oldread+0xb8&gt;</pre></td><td valign="top"><code>cbz x1, 46b8</code>: when <code>n</code> is 0, the function does not run the loop. It continues at line 181.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 149      4638:	movi	v31.4s, #0x0
 150      463c:	sub	x2, x1, #0x1
 151      4640:	mov	x1, #0x0                   	// #0
 152      4644:	lsr	x2, x2, #4
 153      4648:	add	x2, x2, #0x1</pre></td><td valign="top">Number of loop passes: <code>x2 = (n - 1) / 16 + 1</code> (lines 150, 152 and 153).<ul><li><code>lsr x2, x2, #4</code> divides by 16.</li><li><code>x1</code> becomes the pass counter and starts at 0 (line 151).</li><li>Line 149 sets <code>v31</code> to zero again.</li><li>In the whole-chip test one timed call covers 2 MiB (<code>n</code> = 262144 words). So the loop runs 16384 passes per call [Ref8] [Ref9].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 154      464c:	mov	v30.16b, v31.16b
 155      4650:	mov	v29.16b, v31.16b
 156      4654:	mov	v28.16b, v31.16b
 157      4658:	mov	v27.16b, v31.16b
 158      465c:	mov	v26.16b, v31.16b
 159      4660:	mov	v25.16b, v31.16b
 160      4664:	mov	v24.16b, v31.16b</pre></td><td valign="top">The 7 <code>mov</code> instructions copy the zero of <code>v31</code> into <code>v24</code> to <code>v30</code>. <code>v24</code> to <code>v31</code> are the 8 sum registers of the loop. Each one holds two sums of 64 bits. Together they hold the 16 sums <code>s[0]</code> to <code>s[15]</code> of the source.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 161      4668:	ldp	q6, q5, [x0]
 162      466c:	add	x1, x1, #0x1
 163      4670:	ldp	q4, q3, [x0, #32]
 164      4674:	ldp	q2, q1, [x0, #64]
 165      4678:	ldp	q0, q23, [x0, #96]
 166      467c:	add	x0, x0, #0x80</pre></td><td valign="top">The loop starts at line 161. One loop pass is one pass of the outer <code>for</code> loop of the source (16 words). The compiler turned the inner <code>for</code> loop of 16 steps into the 4 loads here and the 8 vector adds below.<ul><li>The 4 <code>ldp</code> instructions (lines 161, 163, 164 and 165) read the 128 B that start at <code>x0</code> into 8 registers, 32 B per instruction. Source: the 16 words <code>a[i]</code> to <code>a[i + 15]</code>.</li><li><code>add x1, x1, #0x1</code> (line 162) adds 1 to the pass counter.</li><li><code>add x0, x0, #0x80</code> (line 166) moves the pointer forward by 128 B (<code>0x80</code> = 128). Source: <code>i += 16</code> (16 words of 8 B).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 167      4680:	add	v24.2d, v24.2d, v6.2d
 168      4684:	add	v25.2d, v25.2d, v5.2d
 169      4688:	add	v26.2d, v26.2d, v4.2d
 170      468c:	add	v27.2d, v27.2d, v3.2d
 171      4690:	add	v28.2d, v28.2d, v2.2d
 172      4694:	add	v29.2d, v29.2d, v1.2d
 173      4698:	add	v30.2d, v30.2d, v0.2d
 174      469c:	add	v31.2d, v31.2d, v23.2d</pre></td><td valign="top">8 vector adds. Each one adds the two 64-bit words of one loaded register to the two 64-bit sums of one sum register (<code>.2d</code> means two elements of 64 bits). Source: <code>s[j] += a[i + j]</code> for <code>j</code> from 0 to 15.<ul><li>Each add takes a loaded register as input. So it cannot run before the data of that load arrives.</li><li>The 8 sum registers form 8 separate chains. Each add needs the sum that the same register held after the pass before.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 175      46a0:	cmp	x1, x2
 176      46a4:	b.cc	4668 &lt;k_oldread+0x68&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp x1, x2</code> compares the pass counter with the number of passes. <code>b.cc 4668</code> jumps back to line 161 while the counter is lower. Source: the test <code>i &lt; n</code> of the outer loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 177      46a8:	stp	q24, q25, [sp]
 178      46ac:	stp	q26, q27, [sp, #32]
 179      46b0:	stp	q28, q29, [sp, #64]
 180      46b4:	stp	q30, q31, [sp, #96]</pre></td><td valign="top">Lines 177 to 203 (27 instructions) run at most once per call, after the loop. These 4 <code>stp</code> instructions store the 8 sum registers into the array <code>s</code> on the stack.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 181      46b8:	ldp	q28, q31, [sp]
 182      46bc:	ldp	q30, q29, [sp, #32]
 183      46c0:	ldp	q26, q27, [sp, #64]
 184      46c4:	add	v31.2d, v31.2d, v28.2d
 185      46c8:	add	v30.2d, v30.2d, v29.2d
 186      46cc:	ldp	q28, q29, [sp, #96]
 187      46d0:	add	v31.2d, v31.2d, v26.2d
 188      46d4:	add	v30.2d, v30.2d, v27.2d
 189      46d8:	adrp	x0, 2f000 &lt;__FRAME_END__+0x16a34&gt;
 190      46dc:	ldr	x0, [x0, #4072]
 191      46e0:	add	v31.2d, v31.2d, v28.2d
 192      46e4:	add	v30.2d, v30.2d, v29.2d
 193      46e8:	ldr	x2, [sp, #136]
 194      46ec:	ldr	x1, [x0]
 195      46f0:	subs	x2, x2, x1
 196      46f4:	mov	x1, #0x0                   	// #0
 197      46f8:	add	v31.2d, v31.2d, v30.2d
 198      46fc:	addp	d31, v31.2d</pre></td><td valign="top">Final sum and stack guard check.<ul><li>Lines 181 to 188, 191, 192 and 197 load the 16 sums from the stack and add them into <code>v31</code>.</li><li><code>addp d31, v31.2d</code> (line 198) adds the two 64-bit halves of <code>v31</code>. The result is the sum of all words that the call read. Source: the loop <code>sum += s[j]</code>.</li><li>Lines 189 and 190 load the address of the stack guard value again. Lines 193 to 195 load the copy from <code>sp + 136</code> and the guard value, and <code>subs</code> subtracts one from the other. Line 196 clears <code>x1</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 199      4700:	b.ne	4714 &lt;k_oldread+0x114&gt;  // b.any</pre></td><td valign="top"><code>b.ne 4714</code>: when the copy differs from the guard value, the function continues at line 204.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 200      4704:	ldp	x29, x30, [sp, #144]
 201      4708:	fmov	x0, d31
 202      470c:	add	sp, sp, #0xa0
 203      4710:	ret</pre></td><td valign="top">Return path.<ul><li><code>ldp x29, x30, [sp, #144]</code> restores the frame pointer and the return address.</li><li><code>fmov x0, d31</code> copies the sum into <code>x0</code>, the register of the return value. Source: <code>return sum</code>.</li><li><code>add sp, sp, #0xa0</code> frees the 160 B of stack. <code>ret</code> returns to the caller.</li><li>The function <code>call</code> of bwx12.c stores the returned sum in the variable <code>sink</code> on the stack of the thread [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 204      4714:	bl	2870 &lt;__stack_chk_fail@plt&gt;
 205</pre></td><td valign="top">This line runs only when the stack guard check fails. <code>bl</code> calls <code>__stack_chk_fail</code>, the C library function for a failed stack guard check. It ends the program.</td></tr>
<tr><td colspan="2"><i>Lines 206 to 753 of the file are not shown here.</i></td></tr>
<tr><td colspan="2"><b>Kernel <code>read_1pl</code>: one 16 B load per 64 B, function <code>k_read_1pl</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 754  === bwx12 read_1pl ===</pre></td><td valign="top">Header of the kernel <code>read_1pl</code>. The name means one load per 64 B line. The whole-chip test times it in part L and in control I, as the last kernel of the sequence [Ref9].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 755  00000000000055d0 &lt;k_read_1pl&gt;:</pre></td><td valign="top">Start address <code>55d0</code> (hexadecimal) and name of the function. <b>The loop is lines 757 to 763.</b><ul><li>Address range: <code>55d4</code> to <code>55ec</code>. That is 7 instructions, 28 bytes of code. Loop start modulo 64: 20.</li><li>Bytes read per loop pass: 64 B. The pointer moves 256 B per pass.</li><li>Load instructions per loop pass: 4 (<code>ldr</code>, 16 B each).</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>The loaded values are not used.</li><li>Source: the asm text of the function <code>k_read_1pl</code> in bwx12.c [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 756      55d0:	add	x1, x0, x1, lsl #3</pre></td><td valign="top">This instruction runs once per call, before the loop. It computes the end address <code>x1 = x0 + 8 * n</code>. The compiler wrote it.<ul><li>The function stores no register on the stack.</li><li>Reason: the loop names <code>q0</code> to <code>q3</code> only. The source comment says that gcc saves nothing for them [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 757      55d4:	ldr	q0, [x0]
 758      55d8:	ldr	q1, [x0, #64]
 759      55dc:	ldr	q2, [x0, #128]
 760      55e0:	ldr	q3, [x0, #192]</pre></td><td valign="top">The loop starts at line 757. Each <code>ldr</code> loads 16 B into one vector register. The offsets are 0, 64, 128 and 192 B from <code>x0</code>.<ul><li>So one pass reads bytes 0 to 15 of each of four 64 B lines, and no other byte [Ref6].</li><li>bwx12 counts the whole length of the range that a call covers. So the rate of this kernel counts 256 B per loop pass, and the loop loads 64 B of them [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 761      55e4:	add	x0, x0, #0x100</pre></td><td valign="top">Moves the pointer forward by 256 B (<code>0x100</code> = 256).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 762      55e8:	cmp	x0, x1
 763      55ec:	b.cc	55d4 &lt;k_read_1pl+0x4&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp x0, x1</code> compares the pointer with the end address. <code>b.cc 55d4</code> jumps back to line 757 while the pointer is lower (unsigned compare).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 764      55f0:	ret
 765</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><i>Lines 766 to 853 of the file are not shown here.</i></td></tr>
<tr><td colspan="2"><b>Kernel <code>read_nop96</code>: the asmread loop plus 96 <code>nop</code>, function <code>k_read_nop96</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 854  === bwx12 read_nop96 ===</pre></td><td valign="top">Header of the kernel <code>read_nop96</code>: the loop of <code>asmread</code> with 96 <code>nop</code> instructions in each loop pass. The whole-chip test times it in part L and in control I, directly after <code>asmread</code> [Ref9].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 855  00000000000057c0 &lt;k_read_nop96&gt;:</pre></td><td valign="top">Start address <code>57c0</code> (hexadecimal) and name of the function. <b>The loop is lines 861 to 967.</b><ul><li>Address range: <code>57d4</code> to <code>597c</code>. That is 107 instructions, 428 bytes of code. Loop start modulo 64: 20.</li><li>Bytes read per loop pass: 256 B.</li><li>Load instructions per loop pass: 8 (<code>ldp</code>, 32 B each).</li><li>Other instructions per loop pass: 99 (96 <code>nop</code>, <code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>The loaded values are not used.</li><li>Source: the macro <code>DEF_ASMREAD</code> in bwx12.c, used as <code>DEF_ASMREAD(read_nop96, 96)</code> [Ref4] [Ref7].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 856      57c0:	stp	d8, d9, [sp, #-64]!
 857      57c4:	add	x1, x0, x1, lsl #3
 858      57c8:	stp	d10, d11, [sp, #16]
 859      57cc:	stp	d12, d13, [sp, #32]
 860      57d0:	stp	d14, d15, [sp, #48]</pre></td><td valign="top">These 5 instructions run once per call, before the loop. They are the 5 instructions of <code>k_asmread</code> (lines 61 to 65): they store <code>d8</code> to <code>d15</code> on the stack and compute the end address <code>x1 = x0 + 8 * n</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 861      57d4:	ldp	q0, q1, [x0]
 862      57d8:	ldp	q2, q3, [x0, #32]
 863      57dc:	ldp	q4, q5, [x0, #64]
 864      57e0:	ldp	q6, q7, [x0, #96]
 865      57e4:	ldp	q8, q9, [x0, #128]
 866      57e8:	ldp	q10, q11, [x0, #160]
 867      57ec:	ldp	q12, q13, [x0, #192]
 868      57f0:	ldp	q14, q15, [x0, #224]</pre></td><td valign="top">The loop starts at line 861. The 8 <code>ldp</code> instructions are the loads of <code>k_asmread</code> (lines 66 to 73): they read the 256 B that start at <code>x0</code> into <code>q0</code> to <code>q15</code>. No instruction uses the loaded values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 869      57f4:	nop
 870      57f8:	nop
 871      57fc:	nop
 872      5800:	nop
 873      5804:	nop
 874      5808:	nop
 875      580c:	nop
 876      5810:	nop
 877      5814:	nop
 878      5818:	nop
 879      581c:	nop
 880      5820:	nop
 881      5824:	nop
 882      5828:	nop
 883      582c:	nop
 884      5830:	nop
 885      5834:	nop
 886      5838:	nop
 887      583c:	nop
 888      5840:	nop
 889      5844:	nop
 890      5848:	nop
 891      584c:	nop
 892      5850:	nop
 893      5854:	nop
 894      5858:	nop
 895      585c:	nop
 896      5860:	nop
 897      5864:	nop
 898      5868:	nop
 899      586c:	nop
 900      5870:	nop
 901      5874:	nop
 902      5878:	nop
 903      587c:	nop
 904      5880:	nop
 905      5884:	nop
 906      5888:	nop
 907      588c:	nop
 908      5890:	nop
 909      5894:	nop
 910      5898:	nop
 911      589c:	nop
 912      58a0:	nop
 913      58a4:	nop
 914      58a8:	nop
 915      58ac:	nop
 916      58b0:	nop
 917      58b4:	nop
 918      58b8:	nop
 919      58bc:	nop
 920      58c0:	nop
 921      58c4:	nop
 922      58c8:	nop
 923      58cc:	nop
 924      58d0:	nop
 925      58d4:	nop
 926      58d8:	nop
 927      58dc:	nop
 928      58e0:	nop
 929      58e4:	nop
 930      58e8:	nop
 931      58ec:	nop
 932      58f0:	nop
 933      58f4:	nop
 934      58f8:	nop
 935      58fc:	nop
 936      5900:	nop
 937      5904:	nop
 938      5908:	nop
 939      590c:	nop
 940      5910:	nop
 941      5914:	nop
 942      5918:	nop
 943      591c:	nop
 944      5920:	nop
 945      5924:	nop
 946      5928:	nop
 947      592c:	nop
 948      5930:	nop
 949      5934:	nop
 950      5938:	nop
 951      593c:	nop
 952      5940:	nop
 953      5944:	nop
 954      5948:	nop
 955      594c:	nop
 956      5950:	nop
 957      5954:	nop
 958      5958:	nop
 959      595c:	nop
 960      5960:	nop
 961      5964:	nop
 962      5968:	nop
 963      596c:	nop
 964      5970:	nop</pre></td><td valign="top">96 <code>nop</code> instructions: lines 869 to 964, addresses <code>57f4</code> to <code>5970</code>.<ul><li>A <code>nop</code> (no operation) changes no register and no memory.</li><li>Source: the line <code>.rept 96</code>, <code>nop</code>, <code>.endr</code> of the macro. It tells the assembler to repeat <code>nop</code> 96 times [Ref7].</li><li>They stand after the 8 loads and before the <code>add</code> of the pointer.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 965      5974:	add	x0, x0, #0x100</pre></td><td valign="top">Moves the pointer forward by 256 B (<code>0x100</code> = 256).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 966      5978:	cmp	x0, x1
 967      597c:	b.cc	57d4 &lt;k_read_nop96+0x14&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp x0, x1</code> compares the pointer with the end address. <code>b.cc 57d4</code> jumps back to line 861 while the pointer is lower (unsigned compare).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 968      5980:	ldp	d10, d11, [sp, #16]
 969      5984:	ldp	d12, d13, [sp, #32]
 970      5988:	ldp	d14, d15, [sp, #48]
 971      598c:	ldp	d8, d9, [sp], #64</pre></td><td valign="top">These 4 instructions run once per call, after the loop. They load <code>d8</code> to <code>d15</code> back from the stack and raise the stack pointer by 64 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 972      5990:	ret
 973</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><i>Lines 974 to 2125 of the file are not shown here.</i></td></tr>
<tr><td colspan="2"><b>Kernel <code>read_nop256</code>: the asmread loop plus 256 <code>nop</code>, function <code>k_read_nop256</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2126  === bwx12 read_nop256 ===</pre></td><td valign="top">Header of the kernel <code>read_nop256</code>: the loop of <code>asmread</code> with 256 <code>nop</code> instructions in each loop pass. The whole-chip test times it in part L and in control I, directly after <code>read_nop96</code> [Ref9].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2127  0000000000006cc0 &lt;k_read_nop256&gt;:</pre></td><td valign="top">Start address <code>6cc0</code> (hexadecimal) and name of the function. <b>The loop is lines 2133 to 2399.</b><ul><li>Address range: <code>6cd4</code> to <code>70fc</code>. That is 267 instructions, 1068 bytes of code. Loop start modulo 64: 20.</li><li>Bytes read per loop pass: 256 B.</li><li>Load instructions per loop pass: 8 (<code>ldp</code>, 32 B each).</li><li>Other instructions per loop pass: 259 (256 <code>nop</code>, <code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>The loaded values are not used.</li><li>Source: the macro <code>DEF_ASMREAD</code> in bwx12.c, used as <code>DEF_ASMREAD(read_nop256, 256)</code> [Ref4] [Ref7].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2128      6cc0:	stp	d8, d9, [sp, #-64]!
2129      6cc4:	add	x1, x0, x1, lsl #3
2130      6cc8:	stp	d10, d11, [sp, #16]
2131      6ccc:	stp	d12, d13, [sp, #32]
2132      6cd0:	stp	d14, d15, [sp, #48]</pre></td><td valign="top">These 5 instructions run once per call, before the loop. They are the 5 instructions of <code>k_asmread</code> (lines 61 to 65): they store <code>d8</code> to <code>d15</code> on the stack and compute the end address <code>x1 = x0 + 8 * n</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2133      6cd4:	ldp	q0, q1, [x0]
2134      6cd8:	ldp	q2, q3, [x0, #32]
2135      6cdc:	ldp	q4, q5, [x0, #64]
2136      6ce0:	ldp	q6, q7, [x0, #96]
2137      6ce4:	ldp	q8, q9, [x0, #128]
2138      6ce8:	ldp	q10, q11, [x0, #160]
2139      6cec:	ldp	q12, q13, [x0, #192]
2140      6cf0:	ldp	q14, q15, [x0, #224]</pre></td><td valign="top">The loop starts at line 2133. The 8 <code>ldp</code> instructions are the loads of <code>k_asmread</code> (lines 66 to 73): they read the 256 B that start at <code>x0</code> into <code>q0</code> to <code>q15</code>. No instruction uses the loaded values.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2141      6cf4:	nop
2142      6cf8:	nop
2143      6cfc:	nop
2144      6d00:	nop
2145      6d04:	nop
2146      6d08:	nop
2147      6d0c:	nop
2148      6d10:	nop
2149      6d14:	nop
2150      6d18:	nop
2151      6d1c:	nop
2152      6d20:	nop
2153      6d24:	nop
2154      6d28:	nop
2155      6d2c:	nop
2156      6d30:	nop
2157      6d34:	nop
2158      6d38:	nop
2159      6d3c:	nop
2160      6d40:	nop
2161      6d44:	nop
2162      6d48:	nop
2163      6d4c:	nop
2164      6d50:	nop
2165      6d54:	nop
2166      6d58:	nop
2167      6d5c:	nop
2168      6d60:	nop
2169      6d64:	nop
2170      6d68:	nop
2171      6d6c:	nop
2172      6d70:	nop
2173      6d74:	nop
2174      6d78:	nop
2175      6d7c:	nop
2176      6d80:	nop
2177      6d84:	nop
2178      6d88:	nop
2179      6d8c:	nop
2180      6d90:	nop
2181      6d94:	nop
2182      6d98:	nop
2183      6d9c:	nop
2184      6da0:	nop
2185      6da4:	nop
2186      6da8:	nop
2187      6dac:	nop
2188      6db0:	nop
2189      6db4:	nop
2190      6db8:	nop
2191      6dbc:	nop
2192      6dc0:	nop
2193      6dc4:	nop
2194      6dc8:	nop
2195      6dcc:	nop
2196      6dd0:	nop
2197      6dd4:	nop
2198      6dd8:	nop
2199      6ddc:	nop
2200      6de0:	nop
2201      6de4:	nop
2202      6de8:	nop
2203      6dec:	nop
2204      6df0:	nop
2205      6df4:	nop
2206      6df8:	nop
2207      6dfc:	nop
2208      6e00:	nop
2209      6e04:	nop
2210      6e08:	nop
2211      6e0c:	nop
2212      6e10:	nop
2213      6e14:	nop
2214      6e18:	nop
2215      6e1c:	nop
2216      6e20:	nop
2217      6e24:	nop
2218      6e28:	nop
2219      6e2c:	nop
2220      6e30:	nop
2221      6e34:	nop
2222      6e38:	nop
2223      6e3c:	nop
2224      6e40:	nop
2225      6e44:	nop
2226      6e48:	nop
2227      6e4c:	nop
2228      6e50:	nop
2229      6e54:	nop
2230      6e58:	nop
2231      6e5c:	nop
2232      6e60:	nop
2233      6e64:	nop
2234      6e68:	nop
2235      6e6c:	nop
2236      6e70:	nop
2237      6e74:	nop
2238      6e78:	nop
2239      6e7c:	nop
2240      6e80:	nop
2241      6e84:	nop
2242      6e88:	nop
2243      6e8c:	nop
2244      6e90:	nop
2245      6e94:	nop
2246      6e98:	nop
2247      6e9c:	nop
2248      6ea0:	nop
2249      6ea4:	nop
2250      6ea8:	nop
2251      6eac:	nop
2252      6eb0:	nop
2253      6eb4:	nop
2254      6eb8:	nop
2255      6ebc:	nop
2256      6ec0:	nop
2257      6ec4:	nop
2258      6ec8:	nop
2259      6ecc:	nop
2260      6ed0:	nop
2261      6ed4:	nop
2262      6ed8:	nop
2263      6edc:	nop
2264      6ee0:	nop
2265      6ee4:	nop
2266      6ee8:	nop
2267      6eec:	nop
2268      6ef0:	nop
2269      6ef4:	nop
2270      6ef8:	nop
2271      6efc:	nop
2272      6f00:	nop
2273      6f04:	nop
2274      6f08:	nop
2275      6f0c:	nop
2276      6f10:	nop
2277      6f14:	nop
2278      6f18:	nop
2279      6f1c:	nop
2280      6f20:	nop
2281      6f24:	nop
2282      6f28:	nop
2283      6f2c:	nop
2284      6f30:	nop
2285      6f34:	nop
2286      6f38:	nop
2287      6f3c:	nop
2288      6f40:	nop
2289      6f44:	nop
2290      6f48:	nop
2291      6f4c:	nop
2292      6f50:	nop
2293      6f54:	nop
2294      6f58:	nop
2295      6f5c:	nop
2296      6f60:	nop
2297      6f64:	nop
2298      6f68:	nop
2299      6f6c:	nop
2300      6f70:	nop
2301      6f74:	nop
2302      6f78:	nop
2303      6f7c:	nop
2304      6f80:	nop
2305      6f84:	nop
2306      6f88:	nop
2307      6f8c:	nop
2308      6f90:	nop
2309      6f94:	nop
2310      6f98:	nop
2311      6f9c:	nop
2312      6fa0:	nop
2313      6fa4:	nop
2314      6fa8:	nop
2315      6fac:	nop
2316      6fb0:	nop
2317      6fb4:	nop
2318      6fb8:	nop
2319      6fbc:	nop
2320      6fc0:	nop
2321      6fc4:	nop
2322      6fc8:	nop
2323      6fcc:	nop
2324      6fd0:	nop
2325      6fd4:	nop
2326      6fd8:	nop
2327      6fdc:	nop
2328      6fe0:	nop
2329      6fe4:	nop
2330      6fe8:	nop
2331      6fec:	nop
2332      6ff0:	nop
2333      6ff4:	nop
2334      6ff8:	nop
2335      6ffc:	nop
2336      7000:	nop
2337      7004:	nop
2338      7008:	nop
2339      700c:	nop
2340      7010:	nop
2341      7014:	nop
2342      7018:	nop
2343      701c:	nop
2344      7020:	nop
2345      7024:	nop
2346      7028:	nop
2347      702c:	nop
2348      7030:	nop
2349      7034:	nop
2350      7038:	nop
2351      703c:	nop
2352      7040:	nop
2353      7044:	nop
2354      7048:	nop
2355      704c:	nop
2356      7050:	nop
2357      7054:	nop
2358      7058:	nop
2359      705c:	nop
2360      7060:	nop
2361      7064:	nop
2362      7068:	nop
2363      706c:	nop
2364      7070:	nop
2365      7074:	nop
2366      7078:	nop
2367      707c:	nop
2368      7080:	nop
2369      7084:	nop
2370      7088:	nop
2371      708c:	nop
2372      7090:	nop
2373      7094:	nop
2374      7098:	nop
2375      709c:	nop
2376      70a0:	nop
2377      70a4:	nop
2378      70a8:	nop
2379      70ac:	nop
2380      70b0:	nop
2381      70b4:	nop
2382      70b8:	nop
2383      70bc:	nop
2384      70c0:	nop
2385      70c4:	nop
2386      70c8:	nop
2387      70cc:	nop
2388      70d0:	nop
2389      70d4:	nop
2390      70d8:	nop
2391      70dc:	nop
2392      70e0:	nop
2393      70e4:	nop
2394      70e8:	nop
2395      70ec:	nop
2396      70f0:	nop</pre></td><td valign="top">256 <code>nop</code> instructions: lines 2141 to 2396, addresses <code>6cf4</code> to <code>70f0</code>.<ul><li>A <code>nop</code> (no operation) changes no register and no memory.</li><li>Source: the line <code>.rept 256</code>, <code>nop</code>, <code>.endr</code> of the macro. It tells the assembler to repeat <code>nop</code> 256 times [Ref7].</li><li>They stand after the 8 loads and before the <code>add</code> of the pointer.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2397      70f4:	add	x0, x0, #0x100</pre></td><td valign="top">Moves the pointer forward by 256 B (<code>0x100</code> = 256).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2398      70f8:	cmp	x0, x1
2399      70fc:	b.cc	6cd4 &lt;k_read_nop256+0x14&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp x0, x1</code> compares the pointer with the end address. <code>b.cc 6cd4</code> jumps back to line 2133 while the pointer is lower (unsigned compare).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2400      7100:	ldp	d10, d11, [sp, #16]
2401      7104:	ldp	d12, d13, [sp, #32]
2402      7108:	ldp	d14, d15, [sp, #48]
2403      710c:	ldp	d8, d9, [sp], #64</pre></td><td valign="top">These 4 instructions run once per call, after the loop. They load <code>d8</code> to <code>d15</code> back from the stack and raise the stack pointer by 64 B.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2404      7110:	ret
2405</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><i>Lines 2406 to 3921 of the file are not shown here.</i></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 57 to 65: the loop that wrote this file. For each name that `bwx12 --list` prints it writes the header line and the output of `objdump -d --no-show-raw-insn --disassemble=k_<name>`. With these options objdump prints the instructions of one function, `k_<name>`, without the bytes of each instruction. A filter (the text tool `sed`) keeps only the lines from the function line to the next empty line.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 493 to 528: the C source of `k_read`. The loop is lines 505 to 527 (16 loads, the empty asm statement, `p += 32`, the loop test).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: lines 168 to 183: the comment on the C kernels. It says that the empty asm statement keeps gcc from deleting the loads of `k_read` and adds no instruction. Lines 286 to 293: the comment on the asm kernels. It says that the compiler cannot add arithmetic, reorder or drop anything in the asm block of the loop. The comment of `k_read` in bwx12.c (lines 493 to 499) points to it under the name bench/bandwidth.c. On 2026-11-21 the file bench/bandwidth.c of the repository and this file had the same sha256 value. That value starts with f1985072. The file of Ref14 records another sha256 value for bandwidth.c in its run. That other value starts with c1406e02. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs. None exists under /home/jhan/workspace/titan/cache-perf. A later run of 2026-11-13 built the binaries again. Its record holds the value that starts with f1985072 for bandwidth.c [Ref17]. It holds the same sha256 value for the binary bw_new as the file of Ref14. So both texts compiled to the same binary bw_new.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 605 to 642: the macro `DEF_ASMREAD` and its use `DEF_ASMREAD(asmread, 0)` (line 642). The asm text of the loop is lines 623 to 635. Lines 609 to 611: the comment that gcc saves d8 to d15 once per call, outside the loop.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 453 to 474: the macro `DEF_OLDREAD` and its use `DEF_OLDREAD(oldread)` (line 474). The two nested `for` loops are lines 466 to 468. The final sum is lines 469 to 472.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 984 to 1004: the source of `k_read_1pl` (asm text of the loop: lines 993 to 1000) and its comment (bytes 0 to 15 of every 64 B line). Lines 907 to 909: the comment that gcc saves nothing for v0 to v3.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 1063: `DEF_ASMREAD(read_nop96, 96)`. Line 1199: `DEF_ASMREAD(read_nop256, 256)`. Line 632 of the macro: the `.rept` line that repeats `nop`.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 1487 to 1509 (function `call`) and 1632 to 1735 (function `worker`): the first touch with `k_write` (line 1646), the warm-up call (line 1669), the timed loop with one call per 2 MiB chunk, its byte count and its clock read (lines 1690 to 1701), and the variable `sink` (lines 1500 and 1635).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`: the files like.spec, cfwd.spec and crev.spec: the arguments of bwx12 in part L, part C and control I (`--threads 120`, `--bytes 256M`, `--stop common`, and the kernel sequence after `--seq`).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: line 1: the host name and the UTC time at the start of the build run (2026-11-15, 17:12:11). Lines 2 and 3: compiler and flags. Line 17: sha256 of the source bwx12.c. Line 20: sha256 of the binary bwx12. Line 21: sha256 of listing.txt.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`: go.sh (lines 13 and 23) and go2.sh (lines 10 and 19): the sha256 value that bwx12 must have, and the check that stops the script otherwise.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/offsets.tsv`: one row per kernel: function start, loop start and loop start modulo 64, written by build12.sh in the same run.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/check_listing12.out`: the output of check_listing12.py for this file: 29 rows against the listing of bwx11 and 26 rows of new kernels, all `ok`. Line 58 counts 0 failed rows.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: the objdump text of bw_new and bw_old of 2026-11-13: `k_read` of bw_new (lines 23 to 37), `k_asmread` of bw_new (lines 81 to 103), `k_read` of bw_old (lines 155 to 226), `k_asmread` of bw_old (lines 257 to 279). Line 15: the sha256 value of bandwidth.c in that run. Lines 19 and 20: the sha256 values of the binaries bw_old and bw_new.
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 142 to 164: the comment on loop placement and the macro `PLACE`, which pads the code before a kernel.
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: the script of part A. Lines 14 to 20: the folder of the binaries bw_old and bw_new and the check of their sha256 values. Line 42: the command that starts one of the two binaries with one kernel. Lines 44 to 47: the kernel names (`read`, `asmread` and four more) and the loop over both binaries.
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: the record of a run of the script run_kernels.sh (in the folder of Ref3) at 18:32:18 UTC on 2026-11-13. This script builds bw_old and bw_new in every run. Line 1 says `mode=probe`: in this mode the script times nothing. Line 15: the sha256 value of bandwidth.c in that run. Line 20: the sha256 value of the binary bw_new, equal to line 20 of the file of Ref14.
- [Ref18] external source: the gcc 14.2.0 manual on gcc.gnu.org (onlinedocs/gcc-14.2.0/gcc), read on 2026-11-21. Page Optimize-Options: the entries `-O3`, `-fno-toplevel-reorder`, `-falign-functions=n`, `-fipa-icf` and `-ftree-loop-distribute-patterns`. Page AArch64-Options: the value `native` of `-march`. Pages Link-Options, C-Dialect-Options and Warning-Options: `-pthread`, `-std=gnu11`, `-Wall` and `-Wextra`.
