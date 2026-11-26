# `offsets.tsv` explained

- Source file: `offsets.tsv` in this folder (text file, 56 lines, 2367 bytes).
- sha256 of the source when this page was built: `214a1f50299bdd1bb31db3754a58caba78ee1f237d25f25d0e1dc5fa6451035f`.
- Role in the whole-chip test: Address table of the 55 bwx12 kernels: function start, loop start, offset modulo 64.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

build12.sh wrote this table on CRB on 2026-11-15, in the same run that built the runner bwx12 and ran its self-test. Each row gives, for one kernel, the address of its function and of its loop in the binary, and the loop address modulo 64.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **build12.sh**: the script that builds bwx12 on CRB and writes this file. It stands in the folder above this one.
- **objdump**: a command that prints the machine code of a binary as assembler text, one instruction per line with its address.
- **listing.txt**: the file in the same folder that holds the objdump text of every kernel of bwx12.
- **build.txt**: the build record that build12.sh writes in the same folder: compiler, flags, self-test result and sha256 digests.
- **sha256 digest**: a checksum of 256 bits that the command `sha256sum` computes from the content of a file. It is printed as 64 hexadecimal digits.
- **Loop start**: the first instruction of the loop of a kernel. The backward branch at the end of the loop goes to it.
- **Modulo 64**: the remainder after a division by 64. For an address it is the position inside a 64-byte block, from 0 to 63. bwx12.c counts one cache line as 64 bytes.
- **Loop pass**: one run through the instructions of the loop, from the loop start to the backward branch.
- **Accepted build**: the word of build12.sh and check_listing12.py for the build of an earlier version (here bwx11) that serves as the reference for a new build.
- **Development machine**: the word of build12.sh and check_listing12.py for the machine on which check_listing12.py runs. It is not CRB.
- **Whole-chip test**: the run under review: the read test with 120 threads on CRB, run on 2026-11-17.
- **ldp, ldr, add, cmp, nop**: Arm instructions. `ldp` of two q registers loads 32 bytes. `ldr` of a q register loads 16 bytes. `add` adds. `cmp` compares two values for the branch that follows. `nop` does nothing.
- **d8 to d15**: the low halves of eight vector registers. A function that changes them must restore them before it returns. The kernel saves them on the stack before the loop and loads them back after it.
- **Stack guard**: a value that the compiled code stores on the stack at the start of a function and compares before the return.
- **First touch**: the first write of a thread to its new buffer.
- **Kernel sequence**: the list of kernel names after the option `--seq` of bwx12. The process times the kernels in this order.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.

</details>

## How to read this file

1. Line 1 is the header. One tab character separates the six columns (line 1).
2. Each later line is one kernel of bwx12. The 55 rows stand in the order of `bwx12 --list`, which is the order of the table `kernels[]` in bwx12.c [Ref4] (lines 2-56).
3. Read `start` and `loop_start` as hexadecimal addresses that `objdump` printed for the binary. Read `loop_mod64` as a decimal number.
4. The bwx12 processes of the whole-chip test (part L, part C and control I) time six of these kernels: `read` (line 2), `asmread` (line 5), `oldread` (line 8), `read_1pl` (line 27), `read_nop96` (line 29) and `read_nop256` (line 39) [Ref6]. They also run `write` (line 3) once per thread before the first interval, and they do not time that call [Ref4].
5. For the instructions of a kernel open listing.txt in the same folder and find the title line `=== bwx12 <kernel> ===` [Ref2].

## Behavior a reader must know

- The file holds addresses only. It holds no rate and no time. Whether a loop position changes a rate cannot be read from it.
- The old read kernel is the row `oldread` (line 8). The new read kernel is the row `read` (line 2).
- The table describes the binary bwx12 only. Part A of the whole-chip test runs the binaries bw_old and bw_new, not bwx12. It times their kernels `read`, `write`, `copy`, `asmread`, `asmwrite` and `asmcopy` [Ref8]. Those functions stand at other addresses [Ref3]. On this page a sentence about which part runs a kernel concerns the function of bwx12 in that row. The same holds for the sentence "The whole-chip test does not run these kernels".
- bwx12.c puts unused bytes before each kernel. They set the start of the function, and with it the loop start, to a planned position modulo 64 [Ref4]. For three kernels of the whole-chip test the loop positions of this table equal the loop positions in bw_new and bw_old: `read` 36 and `asmread` 20 as in bw_new, `oldread` 40 as `k_read` of bw_old [Ref3].
- Check made for this page on 2026-11-21 with a short Python script on listing.txt and on the saved machine code of bw_new and bw_old: `k_read` and `k_asmread` of bwx12 hold the same instructions as `k_read` and `k_asmread` of bw_new. `k_oldread` of bwx12 holds the same instructions as `k_read` of bw_old. Only the addresses differ [Ref2] [Ref3].
- The loops of `read` and `asmread` have the same length (11 instructions, 44 bytes) and different positions: 36 and 20. The `read` loop crosses a 64-byte boundary. The `asmread` loop does not.
- The rows are not in the order of the addresses. `oldread` (line 8) has the lowest start address, 0x4600.
- No program of the whole-chip test reads this file. check_listing12.py reads it on the development machine. It compares column 6 of each row with the loop start modulo 64 that it computes from listing.txt. For the 29 kernels that bwx11 also has, it compares column 6 with the table of the accepted bwx11 build too. Its saved output check_listing12.out ends with `failed_rows=0` and `new_failed_rows=0` [Ref5].
- Check made for this page on 2026-11-21 with a short Python script: in each of the 55 rows `function` is `k_` plus `kernel`, and `loop_mod64` equals `loop_start` modulo 64. The sha256 digest of this file equals the value that build.txt records for it [Ref7].

## Call sequence in the whole-chip test

- `build12.sh`: on CRB, 2026-11-15: writes the header, then one row per kernel
  - `bwx12 --list`: prints the 55 kernel names, which gives the row order
  - `objdump`: prints the machine code of one kernel function
  - `build12.sh (loop over the lines)`: finds the first backward branch, writes start, loop start and modulo 64
- `check_listing12.py`: development machine: compares column 6 with listing.txt and the bwx11 table
- `bwx12.c:worker`: whole-chip test: each thread runs the kernels below
  - `bwx12.c:k_write`: first touch of the buffer, not timed (row on line 3)
  - `bwx12.c:k_oldread`: old read kernel (row on line 8)
  - `bwx12.c:k_read`: new read kernel, part C only (row on line 2)
  - `bwx12.c:k_asmread`: hand-written load-only loop (row on line 5)
  - `bwx12.c:k_read_nop96`: part L and control I (row on line 29)
  - `bwx12.c:k_read_nop256`: part L and control I (row on line 39)
  - `bwx12.c:k_read_1pl`: part L and control I (row on line 27)

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Line 1: the six columns</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  binary	kernel	function	start	loop_start	loop_mod64</pre></td><td valign="top">The header line. Each later line describes one kernel of bwx12.<ul><li><code>binary</code>: the name of the binary. It is <code>bwx12</code> in every row.</li><li><code>kernel</code>: the kernel name, as <code>bwx12 --list</code> prints it and as the option <code>--seq</code> takes it.</li><li><code>function</code>: the C function of the kernel in bwx12.c: <code>k_</code> plus the kernel name.</li><li><code>start</code>: the address of the first instruction of the function, in bytes. Hexadecimal, without <code>0x</code>.</li><li><code>loop_start</code>: the address of the first instruction of the loop. Hexadecimal. build12.sh takes the target of the first branch that goes backward to an address inside the function [Ref1].</li><li><code>loop_mod64</code>: <code>loop_start</code> modulo 64, as a decimal number from 0 to 63. It is the position of the loop start inside a 64-byte block.</li></ul></td></tr>
<tr><td colspan="2"><b>Line 2: <code>read</code>, the new read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 2  bwx12	read	k_read	49a0	49a4	36</pre></td><td valign="top"><code>read</code> is the new read kernel. Part C runs it.<ul><li>The function <code>k_read</code> starts at 0x49a0. The loop starts at 0x49a4, 4 bytes (1 instruction) later. That instruction computes the end address of the range.</li><li>0x49a4 modulo 64 is 36. The loop of <code>k_read</code> in bw_new has the same value [Ref3].</li><li>listing.txt shows the loop: 8 <code>ldp</code> loads (256 bytes per loop pass), <code>add</code>, <code>cmp</code> and the backward branch at 0x49cc. That is 11 instructions, 44 bytes [Ref2]. No instruction uses the loaded values.</li><li>The loop starts at position 36 of its 64-byte block and is 44 bytes long. So it ends in the next block: it crosses the boundary at 0x49c0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 3  bwx12	write	k_write	4a00	4a08	8
 4  bwx12	copy	k_copy	4a60	4a64	36</pre></td><td valign="top">No kernel sequence of the whole-chip test names <code>write</code> or <code>copy</code>. But every thread of a bwx12 process calls <code>k_write</code> once before its first interval: it fills its new buffer (the first touch). This call is not timed [Ref4]. Part A times kernels named <code>write</code> and <code>copy</code>, but they are functions of bw_old and bw_new [Ref8].</td></tr>
<tr><td colspan="2"><b>Line 5: <code>asmread</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 5  bwx12	asmread	k_asmread	4ac0	4ad4	20</pre></td><td valign="top"><code>asmread</code> is the hand-written load-only loop. Part L, part C and control I run it.<ul><li><code>k_asmread</code> starts at 0x4ac0. The loop starts at 0x4ad4, 20 bytes (5 instructions) later. Four of them save the registers d8 to d15 on the stack. One computes the end address.</li><li>0x4ad4 modulo 64 is 20. The loop of <code>k_asmread</code> in bw_new has the same value [Ref3].</li><li>The loop has the form of the <code>read</code> loop: 8 <code>ldp</code> loads (256 bytes per loop pass), <code>add</code>, <code>cmp</code> and the backward branch (at 0x4afc). That is 11 instructions, 44 bytes [Ref2].</li><li>The loop starts at position 20 and is 44 bytes long. So it lies inside one 64-byte block: the next block starts at 0x4b00, directly after the branch.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 6  bwx12	asmwrite	k_asmwrite	4f20	4f28	40
 7  bwx12	asmcopy	k_asmcopy	5020	5034	52</pre></td><td valign="top">No bwx12 process of the whole-chip test runs these kernels. Part A times kernels named <code>asmwrite</code> and <code>asmcopy</code>, but they are functions of bw_old and bw_new [Ref8]. The columns have the same meaning.</td></tr>
<tr><td colspan="2"><b>Line 8: <code>oldread</code>, the old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  bwx12	oldread	k_oldread	4600	4668	40</pre></td><td valign="top"><code>oldread</code> is the old read kernel. Part L, part C and control I run it.<ul><li><code>k_oldread</code> starts at 0x4600. The loop starts at 0x4668, 104 bytes (26 instructions) later. These instructions make the stack frame, store the stack guard value, set the 16 sums to zero and compute the number of loop passes.</li><li>0x4668 modulo 64 is 40. The loop of <code>k_read</code> in bw_old has the same value [Ref3].</li><li>listing.txt shows the loop: 4 <code>ldp</code> loads (128 bytes per loop pass), 8 vector adds (one per loaded register), 2 scalar <code>add</code> (pass counter and address), <code>cmp</code> and the backward branch at 0x46a4. That is 16 instructions, 64 bytes [Ref2].</li><li>The loop starts at position 40 and is 64 bytes long. So it crosses the boundary at 0x4680.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 9  bwx12	oldwrite	k_oldwrite	48a0	48c0	0
10  bwx12	oldcopy	k_oldcopy	4920	4930	48
11  bwx12	asmread2	k_asmread2	4b40	4b54	20
12  bwx12	asmwrite2	k_asmwrite2	4fa0	4fa8	40
13  bwx12	asmcopy2	k_asmcopy2	50e0	50f4	52
14  bwx12	oldread2	k_oldread2	4740	47a8	40
15  bwx12	asmcopy_c	k_asmcopy_c	51b0	51b4	52
16  bwx12	asmcopy_c_add	k_asmcopy_c_add	5270	5274	52
17  bwx12	asmcopy_c_reg	k_asmcopy_c_reg	5320	5334	52
18  bwx12	read_nop4	k_read_nop4	4bc0	4bd4	20
19  bwx12	read_nop8	k_read_nop8	4c40	4c54	20
20  bwx12	read_nop16	k_read_nop16	4cc0	4cd4	20
21  bwx12	read_nop32	k_read_nop32	4d80	4d94	20
22  bwx12	read_sparse	k_read_sparse	4e80	4e84	4
23  bwx12	read_pf256	k_read_pf256	53c0	53d4	20
24  bwx12	read_pf512	k_read_pf512	5440	5454	20
25  bwx12	read_pf1024	k_read_pf1024	54c0	54d4	20
26  bwx12	read_pf2048	k_read_pf2048	5540	5554	20</pre></td><td valign="top">The whole-chip test does not run these kernels. The columns have the same meaning. <code>asmread2</code>, <code>asmwrite2</code>, <code>asmcopy2</code> and <code>oldread2</code> are second copies: the same source under a second name. Each has the <code>loop_mod64</code> of its original: 20, 40, 52 and 40.</td></tr>
<tr><td colspan="2"><b>Line 27: <code>read_1pl</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">27  bwx12	read_1pl	k_read_1pl	55d0	55d4	20</pre></td><td valign="top"><code>read_1pl</code> is the test loop with one load per 64-byte line. Part L and control I run it.<ul><li><code>k_read_1pl</code> starts at 0x55d0. The loop starts at 0x55d4, 4 bytes (1 instruction) later.</li><li>0x55d4 modulo 64 is 20, the value of <code>asmread</code>.</li><li>listing.txt shows the loop: 4 <code>ldr</code> loads of 16 bytes each, at the offsets 0, 64, 128 and 192 of a 256-byte block, then <code>add</code>, <code>cmp</code> and the backward branch at 0x55ec. That is 7 instructions, 28 bytes [Ref2]. So one loop pass loads 64 bytes and moves the address forward by 256 bytes.</li><li>bwx12 counts the length of the range that a kernel call covers, not the loaded bytes. So it counts 256 bytes per loop pass of <code>read_1pl</code> [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">28  bwx12	read_nop64	k_read_nop64	5640	5654	20</pre></td><td valign="top">The whole-chip test does not run this kernel.</td></tr>
<tr><td colspan="2"><b>Line 29: <code>read_nop96</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">29  bwx12	read_nop96	k_read_nop96	57c0	57d4	20</pre></td><td valign="top"><code>read_nop96</code> is the <code>asmread</code> loop with 96 <code>nop</code> instructions per loop pass. Part L and control I run it.<ul><li><code>k_read_nop96</code> starts at 0x57c0. The loop starts at 0x57d4, 20 bytes later, after the same 5 instructions as in <code>k_asmread</code>.</li><li>0x57d4 modulo 64 is 20, the value of <code>asmread</code>.</li><li>listing.txt shows the loop: 8 <code>ldp</code> loads (256 bytes per loop pass), 96 <code>nop</code>, <code>add</code>, <code>cmp</code> and the backward branch at 0x597c. That is 107 instructions, 428 bytes [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">30  bwx12	read_nop128	k_read_nop128	59c0	59d4	20
31  bwx12	read_nop48	k_read_nop48	5c80	5c94	20
32  bwx12	read_nop56	k_read_nop56	5dc0	5dd4	20
33  bwx12	read_nop72	k_read_nop72	5f00	5f14	20
34  bwx12	read_nop80	k_read_nop80	6080	6094	20
35  bwx12	read_nop88	k_read_nop88	6240	6254	20
36  bwx12	read_nop112	k_read_nop112	6400	6414	20
37  bwx12	read_nop160	k_read_nop160	6640	6654	20
38  bwx12	read_nop192	k_read_nop192	6940	6954	20</pre></td><td valign="top">The whole-chip test does not run these kernels. They are the <code>asmread</code> loop with other numbers of <code>nop</code> instructions. Each loop starts at 20 modulo 64.</td></tr>
<tr><td colspan="2"><b>Line 39: <code>read_nop256</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">39  bwx12	read_nop256	k_read_nop256	6cc0	6cd4	20</pre></td><td valign="top"><code>read_nop256</code> is the <code>asmread</code> loop with 256 <code>nop</code> instructions per loop pass. Part L and control I run it.<ul><li><code>k_read_nop256</code> starts at 0x6cc0. The loop starts at 0x6cd4, 20 bytes later, after the same 5 instructions as in <code>k_asmread</code>.</li><li>0x6cd4 modulo 64 is 20, the value of <code>asmread</code>.</li><li>listing.txt shows the loop: 8 <code>ldp</code> loads (256 bytes per loop pass), 256 <code>nop</code>, <code>add</code>, <code>cmp</code> and the backward branch at 0x70fc. That is 267 instructions, 1068 bytes [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">40  bwx12	read_dadd2	k_read_dadd2	7160	7194	20
41  bwx12	read_dadd4	k_read_dadd4	7220	7254	20
42  bwx12	read_dadd8	k_read_dadd8	72e0	7314	20
43  bwx12	read_dadd16	k_read_dadd16	73a0	73d4	20
44  bwx12	read_iadd16	k_read_iadd16	7480	74d4	20
45  bwx12	read_sp24	k_read_sp24	7590	7594	20
46  bwx12	read_sp32	k_read_sp32	7650	7654	20
47  bwx12	read_sp40	k_read_sp40	7710	7714	20
48  bwx12	read_sp48	k_read_sp48	7810	7814	20
49  bwx12	read_sp56	k_read_sp56	7910	7914	20
50  bwx12	read_1pl_nop96	k_read_1pl_nop96	7a50	7a54	20
51  bwx12	write_nop32	k_write_nop32	7c20	7c28	40
52  bwx12	write_nop96	k_write_nop96	7d20	7d28	40
53  bwx12	write_nop128	k_write_nop128	7f20	7f28	40
54  bwx12	write_nop256	k_write_nop256	81a0	81a8	40
55  bwx12	copy_nop96	k_copy_nop96	8620	8634	52
56  bwx12	copy_nop192	k_copy_nop192	8860	8874	52</pre></td><td valign="top">The whole-chip test does not run these kernels. They are read loops with vector adds (<code>read_dadd</code>, <code>read_iadd16</code>), read loops of 128 bytes per loop pass (<code>read_sp</code>), <code>read_1pl_nop96</code>, and write and copy loops with <code>nop</code> instructions. The read loops start at 20 modulo 64, the write loops at 40 and the copy loops at 52.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 59-75 write this file. Line 60 prints the header. Line 66 takes `start` from the first line of the objdump text. Lines 67-73 find the first backward branch. Line 74 prints the row.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: the machine code of the kernels: `read` from line 1, `asmread` from line 59, `oldread` from line 133, `read_1pl` from line 754, `read_nop96` from line 854, `read_nop256` from line 2126.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: the machine code of bw_new and bw_old. bw_new `k_read`: the loop starts at 0x1c64 (lines 24-36), 36 modulo 64. bw_new `k_asmread`: 0x1b54 (lines 82-98), 20 modulo 64. bw_old `k_read`: 0x1b68 (lines 156-198), 40 modulo 64.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 143-163: the padding before each kernel. Lines 1454-1484: the table `kernels[]`. Line 1646: `worker` calls `k_write` before the first interval. Lines 1663 and 1693-1696: `worker` adds the length of the range of each kernel call to the byte count of the interval (twice the length for a copy kernel). Lines 2921-2924: the option --list.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`: lines 156-168 read this file and keep column 6. The saved output is check_listing12.out in the same folder as this file.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`: the kernel sequence of part L and of control I: oldread, asmread, read_nop96, read_nop256, read_1pl. cfwd.spec and crev.spec in the same folder hold the sequences of part C: oldread, read, asmread and asmread, read, oldread.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: line 22 holds the sha256 digest of offsets.tsv.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: the script of part A. Line 44 names its kernels: read, write, copy, asmread, asmwrite, asmcopy. Lines 39-43 and 45-48 start one process of bw_old and one process of bw_new per kernel and round.
