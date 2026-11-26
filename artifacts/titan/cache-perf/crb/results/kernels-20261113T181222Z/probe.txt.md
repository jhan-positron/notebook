# `probe.txt` explained

- Source file: `probe.txt` in this folder (text file, 439 lines, 13796 bytes).
- sha256 of the source when this page was built: `53a4a9651dffff8c5477e68303f227aea619cea1c224adda7db3f782da7ea677`.
- Role in the whole-chip test: Build record and machine code of bw_old and bw_new, the part A binaries
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

run_kernels.sh wrote this file on CRB on 2026-11-13 when it built the binaries bw_old and bw_new: the machine state, the compiler flags, the sha256 values and the objdump text of every kernel function. Part A of the rerun of 2026-11-17 ran these two binaries. So this file shows the exact instructions of the old read kernel and of the new read kernel in part A.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Rerun**: the whole-chip read test of 2026-11-17 on CRB, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **run_kernels.sh**: the script of 2026-11-13 that built bw_old and bw_new on CRB, wrote this file and ran the timed runs of that day.
- **Self-test**: the program `selftest` that run_kernels.sh builds from selftest.c and runs after the build. It checks what the six kernels of the new source do to memory [Ref7].
- **probe.o**: an object file that run_kernels.sh compiled from probe.c. It holds three candidates for the copy kernel. run_kernels.sh did not link it and did not run it [Ref1] [Ref6].
- **ra.sh, go.sh**: ra.sh is the script that ran part A of the rerun. go.sh is the driver script of the rerun that started ra.sh.
- **objdump**: the GNU tool that prints the machine code of a binary as assembly text. Here it printed one function per call, without the raw instruction bytes.
- **sha256**: a checksum of 256 bits, printed as 64 hexadecimal digits. Equal values mean equal file content.
- **Loop pass**: one execution of the instructions of a loop, from the loop start to the branch that jumps back.
- **Call**: one execution of a kernel function. In part A one call goes once over the whole 256 MiB buffer of a thread.
- **Empty asm statement**: a statement of the new source, written `__asm__ volatile("" : : ...)`. Its instruction text is empty. It names the 16 loaded values as inputs in vector registers. gcc must have all 16 values in registers at that point. In `k_read` this keeps gcc from deleting the loads [Ref3].
- **Load instruction, store instruction**: a load instruction reads bytes from memory into a register. A store instruction writes bytes from a register to memory.
- **`ldp`, `stp`**: load pair and store pair: one instruction moves two registers. With two `q` registers it moves 32 bytes.
- **`x0` to `x30`, `sp`**: the 64-bit integer registers and the stack pointer. `w2` names the low 32 bits of `x2`.
- **`v`, `q`, `d` registers**: the 32 vector registers of 128 bits each. `q5` names all 16 bytes of register 5. `d5` names its low 8 bytes. `v5.2d` names the same register taken as two 64-bit numbers.
- **NEON**: the 128-bit vector instruction set of 64-bit Arm CPUs.
- **SVE**: Scalable Vector Extension, a second vector instruction set of Arm. Its registers are named `z0` to `z31`, and their size depends on the CPU. The registers `p0` to `p15` select the elements that an instruction uses.
- **Stack protector, guard value**: a check that the compiler adds to a function. At entry the function copies a guard value to the stack next to its local variables. Before it returns, it compares the copy with the guard value. When they differ, it calls `__stack_chk_fail`.
- **THP**: transparent huge pages: a Linux feature that backs memory with 2 MiB pages without a request of the program.
- **First touch**: the first write to a new buffer. Linux assigns the physical memory pages of the buffer at that moment.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg).
- **%CPU**: the column pcpu of the tool ps, shown in lines 6 to 11 of this file. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.

</details>

## How to read this file

1. Lines that start with `##` are notes of run_kernels.sh: the machine state, the compiler, the flags and the end of each step. They are lines 1 to 5, 12, 13 and 437 to 439.
2. The sha256 block (lines 13 to 22) names the sources and the binaries of the build. Lines 19 and 20 are the values that ra.sh checks before part A of the rerun.
3. A line of the form `=== bw_new k_read ===` starts the objdump text of one function. An instruction line holds the address in hexadecimal, the instruction name and the operands. Each instruction is 4 bytes long (lines 23-25).
4. To find a loop, look for a branch (`b.hi`, `b.cc`, `b.ne`, `b.gt`) whose target address is lower than its own address. The loop runs from the target to the branch (line 36).
5. The new read kernel is the section `bw_new k_read`: 8 loads per loop pass of 256 bytes, and no other use of the data (lines 23-37).
6. The old read kernel is the section `bw_old k_read`: 4 loads and 8 vector adds per loop pass of 128 bytes (lines 155-226).
7. The hand-written loop asmread is in both binaries with the same instructions: `bw_new k_asmread` at lines 81 to 103, and `bw_old k_asmread` at lines 257 to 279.
8. The sections `k_write`, `k_copy`, `k_asmwrite` and `k_asmcopy` of both binaries are the write and copy kernels (bw_new: lines 39 to 79 and 105 to 153, bw_old: lines 228 to 255 and 281 to 329). Part A timed them too, each in its own process.
9. The sections `probe.o` and `chase` show code that the whole-chip test does not run (lines 331-435).
10. The last three lines give the result of the self-test and the load after the timed runs of 2026-11-13 (lines 437-439).

## Behavior a reader must know

- This file is from the build of 2026-11-13, not from the rerun. The link to the rerun is a sha256 check: ra.sh started part A only after bw_old and bw_new matched lines 19 and 20 [Ref2]. The three part A records of the rerun show the same two values [Ref9].
- The part A result folders of the rerun hold their own file named `probe.txt`, written by ra.sh. That file holds no machine code [Ref9].
- The binary files bw_old and bw_new are not in the local folders of this project. So this listing cannot be checked against a local binary. Their sha256 values are known only from records, such as lines 19 and 20 of this file, ra.sh and the part A records of the rerun [Ref2] [Ref9].
- Per 256 bytes read, the new read kernel and asmread execute 8 loads and 3 other instructions in 1 loop pass. The old read kernel executes 8 loads and 24 other instructions in 2 loop passes: 16 vector adds, 4 integer adds, 2 compares and 2 branches.
- The new read kernel (lines 26 to 36) and asmread (lines 88 to 98) have the same loop: 8 `ldp` loads with the same offsets, one `add`, one `cmp` and one branch. They differ in four points: the register numbers, the operand order of `cmp` with the matching branch condition, the loop address, and the 8 stack instructions that asmread executes outside the loop once per call.
- Code outside a loop runs once per call. The benchmark reads the clock before the timed calls and after them [Ref3] [Ref4]. So this code is inside the timed interval. One warm-up call before each timed interval is not timed. In part A one call reads the 256 MiB buffer of a thread: 1,048,576 loop passes in `bw_new k_read` and in `k_asmread`, and 2,097,152 loop passes in `bw_old k_read` [Ref2].
- The listing holds only the six kernel functions of each binary. It does not show `pass` and `worker` (the functions that call them) or `main` [Ref1]. The statements of this page about the callers come from the source text [Ref3] [Ref4]. Both sources mark every kernel function `noinline`. This forbids the compiler to merge a kernel into its caller [Ref3] [Ref4].
- bw_old and bw_new fill their buffers with different write loops. Each thread does the first write (first touch) to its buffers with the `k_write` of its binary, before its first timed interval. This first write is not timed. In bw_old it is the SVE loop at lines 238 to 241 of this file. In bw_new it is the `stp` loop at lines 43 to 53 [Ref3] [Ref4].
- The copy of bandwidth.c in the project folder `tmp/agent-scratch/kernels-2026-11-13` is not the exact text of this build. Its sha256 starts with `f1985072`. Line 15 says `c1406e02`. run_kernels.sh ran again at 18:32:18 UTC of the same day, in the mode `probe` (build, machine code and self-test, no timed runs). The record of that run lists the `f1985072` text, the bw_new value of line 20, and machine code equal to lines 23 to 436 of this file [Ref5]. run_kernels.sh builds bw_new at every run [Ref1]. So both texts give the same bw_new.
- The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref12]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- The rerun also ran the runner program bwx12. This file holds no machine code of bwx12. In the bwx12 listing the functions `k_read`, `k_asmread` and `k_oldread` show the same instruction text as lines 25 to 37, 83 to 103 and 157 to 226 of this file, apart from addresses [Ref8].
- `bw_old k_read` holds a stack protector check (lines 159 to 160, 163 to 165, 211 to 212, 215 to 218, 221 and 226). It runs once per call. No flag in line 3 asks for it. Insufficient data: which default setting of this gcc adds it. The output of `gcc -Q --help=common` on CRB would resolve it.
- The self-test of line 437 covers the kernels of the new source only: selftest.c includes bandwidth.c, not bandwidth.orig.c [Ref7].

## Call sequence in the whole-chip test

- `go.sh`: driver of the rerun: starts ra.sh (part A) three times
  - `ra.sh`: checks the sha256 of lines 19 and 20, then starts 24 processes
    - `bandwidth.orig.c:main`: binary bw_old: 12 of the 24 processes, one per kernel and round
      - `bandwidth.orig.c:worker`: one of 120 threads: pins, allocates, first write, timed passes
        - `bw_old k_write` (line 228): first write to each buffer, and the timed kernel write
        - `bandwidth.orig.c:pass`: one call of the chosen kernel over the whole buffer
          - `bw_old k_read` (line 155): old read kernel: 4 loads and 8 vector adds per 128 B
          - `bw_old k_copy` (line 244): copy kernel of bw_old, SVE loop
          - `bw_old k_asmread` (line 257): hand-written loop: 8 loads per 256 B
          - `bw_old k_asmwrite` (line 281): hand-written write loop: 8 stores per 256 B
          - `bw_old k_asmcopy` (line 298): hand-written copy loop: 8 loads, then 8 stores
    - `bandwidth.c:main`: binary bw_new: the other 12 processes, one kernel per process
      - `bandwidth.c:worker`: one of 120 threads: pins, allocates, first write, timed passes
        - `bw_new k_write` (line 39): first write to each buffer, and the timed kernel write
        - `bandwidth.c:pass`: one call of the chosen kernel over the whole buffer
          - `bw_new k_read` (line 23): new read kernel: 8 loads per 256 B, data not used
          - `bw_new k_copy` (line 56): copy kernel of bw_new: 8 loads, then 8 stores
          - `bw_new k_asmread` (line 81): hand-written loop: 8 loads per 256 B
          - `bw_new k_asmwrite` (line 105): hand-written write loop: 8 stores per 256 B
          - `bw_new k_asmcopy` (line 122): hand-written copy loop: 8 loads, then 8 stores

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `bw_new k_read` | 23-37 | New read kernel as built: 8 `ldp` loads of 32 bytes per loop pass. No instruction uses the data. | - | yes |
| `bw_new k_write` | 39-54 | Write kernel of bw_new: 8 `stp` stores of 32 bytes per loop pass. It also does the first write to each buffer. | - | yes |
| `bw_new k_copy` | 56-79 | Copy kernel of bw_new: 8 loads, then 8 stores, 256 bytes per loop pass. | - | yes |
| `bw_new k_asmread` | 81-103 | Hand-written load-only loop: 8 `ldp` loads per loop pass. It saves `d8` to `d15` once per call. | - | yes |
| `bw_new k_asmwrite` | 105-120 | Hand-written write loop: 8 `stp` stores of 32 bytes per loop pass. | - | yes |
| `bw_new k_asmcopy` | 122-153 | Hand-written copy loop: 8 loads, then 8 stores, 256 bytes per loop pass. | - | yes |
| `bw_old k_read` | 155-226 | Old read kernel as built: 4 `ldp` loads and 8 vector adds per loop pass of 128 bytes. It returns the total. | `__stack_chk_fail` | yes |
| `bw_old k_write` | 228-242 | Write kernel of bw_old, an SVE loop. It also does the first write to each buffer. | - | yes |
| `bw_old k_copy` | 244-255 | Copy kernel of bw_old, an SVE loop: one load and one store per loop pass. | - | yes |
| `bw_old k_asmread` | 257-279 | The same instructions as `bw_new k_asmread`, at other addresses. | - | yes |
| `bw_old k_asmwrite` | 281-296 | The same instructions as `bw_new k_asmwrite`, at other addresses. | - | yes |
| `bw_old k_asmcopy` | 298-329 | The same instructions as `bw_new k_asmcopy`, at other addresses. | - | yes |
| `probe.o copy_barrier` | 331-354 | Copy candidate with the empty asm statement. Compiled only, never run. | - | no |
| `probe.o copy_plain` | 355-379 | Copy candidate without the empty asm statement. Compiled only, never run. | - | no |
| `probe.o copy_plain_norestrict` | 380-403 | Copy candidate without the statement and without `restrict`. Compiled only, never run. | - | no |
| `bench/latency chase` | 404-419 | Loop of 8 dependent 8-byte loads in another benchmark binary. The whole-chip test does not run it. | - | no |
| `bench/homelat chase` | 421-435 | The same kind of loop in a second benchmark binary. The whole-chip test does not run it. | - | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header: machine state before the build</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  ## host=ubuntu utc=2026-11-13T18:12:22Z load_before=0.03 0.02 0.00 logins=0 mode=all</pre></td><td valign="top">run_kernels.sh (the script of 2026-11-13 that built both binaries on CRB) wrote this line before the build [Ref1].<ul><li><code>host</code>: the host name that CRB reports.</li><li><code>utc</code>: the start time. The folder name <code>kernels-20261113T181222Z</code> holds the same time.</li><li><code>load_before</code>: the load average of the last 1, 5 and 15 minutes.</li><li><code>logins=0</code>: the tool <code>who</code> listed no login session.</li><li><code>mode=all</code>: the script ran the build, this listing, the self-test and then the timed runs of 2026-11-13.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  2  ## gcc=gcc (Ubuntu 14.2.0-4ubuntu2~24.04.1) 14.2.0
  3  ## CFLAGS=-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11</pre></td><td valign="top"><ul><li>Line 2: the first line of <code>gcc --version</code>. The compiler is gcc 14.2.0 of Ubuntu.</li><li>Line 3: the flags of all four builds of this run [Ref1].</li><li><code>-O3</code>: the highest numbered optimization level of gcc.</li><li><code>-march=native</code>: gcc may use every instruction set of the CPU that runs the compiler. On CRB this includes SVE [Ref11].</li><li><code>-fno-tree-loop-distribute-patterns</code>: gcc must not replace a loop by a call of a library function.</li><li>The other flags select thread support, more warnings and the C dialect.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  4  ## thp=[always] madvise never</pre></td><td valign="top">The content of the Linux file <code>/sys/kernel/mm/transparent_hugepage/enabled</code> [Ref1]. The brackets mark the active setting, <code>always</code>. With <code>always</code>, Linux may back a buffer with 2 MiB pages without a request of the program (THP, see Words used here).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  5  ## busiest processes (pcpu user comm):
  6  %CPU USER     COMMAND
  7   0.3 jhan     systemd
  8   0.0 root     rcu_preempt
  9   0.0 root     pr/ttyAMA-1
 10   0.0 root     kworker/u512:1-bnxt_pf_wq
 11   0.0 root     kworker/u528:3-flush-259:0</pre></td><td valign="top">Line 6 is the header line of the tool <code>ps</code>. Lines 7 to 11 are the 5 processes with the highest <code>%CPU</code>, here at most 0.3 % [Ref1]. <code>%CPU</code> is an average over the life of a process. It is not the use at the moment of the reading.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 12  ## build output bytes: 0</pre></td><td valign="top">The size of <code>build.txt</code>, the file that received the messages of gcc. 0 bytes means that gcc printed no warning and no error in the four builds: bw_old, bw_new, selftest and probe.o [Ref1].</td></tr>
<tr><td colspan="2"><b>sha256 values of the sources and the binaries</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 13  ## sha256:
 14  61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b  bandwidth.orig.c
 15  c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2  bandwidth.c
 16  90456a5661e61d14fa20f6c75c13976fe0904b58e83bcba4182f8456a4d64c28  selftest.c
 17  81f96b39747fad6e8876a70c764ec0420011f7e02f8ff20faffa5a0e0b82913f  probe.c
 18  6a91bbbe799b9279f99c693f44ef5852d5daa437a7e2469bf61c914b40b81842  run_kernels.sh
 19  e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
 20  fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
 21  80714eb8a73bd5b62e1a6ed8b9de286929f52ef28e342ede20dc19e58c19f58b  selftest
 22  61228754162c504e37faab3da7f423630ab66e32064ba5911455999347c2fe1b  /home/jhan/cache-perf/bench/bandwidth.c</pre></td><td valign="top"><ul><li>Lines 14 to 18: the four C sources and the script run_kernels.sh in the build folder. <code>bandwidth.orig.c</code> is the old source. <code>bandwidth.c</code> is the new source.</li><li>Lines 19 and 20: the binaries bw_old and bw_new. ra.sh (the part A script of the rerun) compares both binaries with these two values before it starts a process. It stops when a value differs [Ref2].</li><li>Line 21: the binary of the self-test.</li><li>Line 22: the benchmark source in the folder <code>~/cache-perf/bench</code> of CRB. Its value equals line 14. So that file was the old source at the time of the build.</li><li>The copy of <code>bandwidth.c</code> in the folder <code>tmp/agent-scratch/kernels-2026-11-13</code> of this project has another value than line 15. A later record shows that it gives the bw_new of line 20 [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b><code>bw_new k_read</code>: the new read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 23  === bw_new k_read ===
 24  0000000000001c60 &lt;k_read&gt;:</pre></td><td valign="top">objdump text of the function <code>k_read</code> of bw_new. Line 24 gives its start address. Each line below holds an address (hexadecimal), an instruction name and the operands. Each instruction is 4 bytes long.<ul><li>Loop: addresses <code>1c64</code> to <code>1c8c</code> (lines 26 to 36), 11 instructions, 44 bytes of code.</li><li>Bytes read per loop pass: 256.</li><li>Load instructions per loop pass: 8.</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.hi</code>).</li><li>Loaded values: no instruction uses them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 25      1c60:	add	x1, x0, x1, lsl #3</pre></td><td valign="top"><code>x0</code> holds the address of the buffer and <code>x1</code> its length in 8-byte words: the two arguments of <code>k_read</code> [Ref3]. The instruction computes <code>x1 = x0 + x1 * 8</code>, the address of the first byte after the buffer. It runs once per call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 26      1c64:	ldp	q31, q30, [x0]</pre></td><td valign="top">Loop start. <code>ldp</code> (load pair) reads 32 bytes of the buffer at the address in <code>x0</code> into two 16-byte vector registers, <code>q31</code> and <code>q30</code>. The source writes 16 loads of 16 bytes each. gcc joined them in pairs into the 8 <code>ldp</code> of lines 26 to 33 [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 27      1c68:	ldp	q29, q28, [x0, #32]
 28      1c6c:	ldp	q27, q26, [x0, #64]
 29      1c70:	ldp	q25, q24, [x0, #96]
 30      1c74:	ldp	q23, q22, [x0, #128]
 31      1c78:	ldp	q21, q20, [x0, #160]
 32      1c7c:	ldp	q19, q18, [x0, #192]
 33      1c80:	ldp	q17, q16, [x0, #224]</pre></td><td valign="top">7 more <code>ldp</code> loads of 32 bytes each, at the offsets 32 to 224 bytes from <code>x0</code>. With line 26 this gives 8 loads that read bytes 0 to 255, each byte once. The data go to the 16 registers <code>q16</code> to <code>q31</code>. No instruction of the function reads these registers, and the next loop pass overwrites them.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 34      1c84:	add	x0, x0, #0x100</pre></td><td valign="top"><code>x0 = x0 + 256</code> (<code>0x100</code>). The pointer moves to the next 256 bytes.<ul><li>In the source an empty asm statement (see Words used here) stands between the 16 loads and this pointer change. The statement names the 16 loaded values as inputs. This keeps gcc from deleting the loads [Ref3].</li><li>No instruction stands between the last load and this <code>add</code>. So the statement produced no instruction.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 35      1c88:	cmp	x1, x0
 36      1c8c:	b.hi	1c64 &lt;k_read+0x4&gt;  // b.pmore</pre></td><td valign="top"><ul><li><code>cmp</code> compares the end address <code>x1</code> with the pointer <code>x0</code>.</li><li><code>b.hi</code> jumps back to <code>1c64</code> (line 26) while the end address is higher (unsigned compare).</li><li>No check stands before the first pass. So the loop runs at least once.</li><li>The text after <code>//</code> is another name of the same branch condition, printed by objdump.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 37      1c90:	ret
 38</pre></td><td valign="top"><code>ret</code> returns to the caller. The function saves no register, uses no stack and returns no value.</td></tr>
<tr><td colspan="2"><b><code>bw_new k_write</code> and <code>bw_new k_copy</code>: write and copy kernels of bw_new</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 39  === bw_new k_write ===
 40  0000000000001b00 &lt;k_write&gt;:
 41      1b00:	dup	v31.2d, x2
 42      1b04:	add	x1, x0, x1, lsl #3
 43      1b08:	add	x0, x0, #0x100
 44      1b0c:	stp	q31, q31, [x0, #-256]
 45      1b10:	stp	q31, q31, [x0, #-224]
 46      1b14:	stp	q31, q31, [x0, #-192]
 47      1b18:	stp	q31, q31, [x0, #-160]
 48      1b1c:	stp	q31, q31, [x0, #-128]
 49      1b20:	stp	q31, q31, [x0, #-96]
 50      1b24:	stp	q31, q31, [x0, #-64]
 51      1b28:	stp	q31, q31, [x0, #-32]
 52      1b2c:	cmp	x1, x0
 53      1b30:	b.hi	1b08 &lt;k_write+0x8&gt;  // b.pmore
 54      1b34:	ret
 55</pre></td><td valign="top">The write kernel of bw_new.<ul><li><code>dup</code> copies the 64-bit value in <code>x2</code> into both halves of <code>v31</code>.</li><li>The loop (<code>1b08</code> to <code>1b30</code>) writes 256 bytes per pass with 8 <code>stp</code> (store pair) instructions of 32 bytes each.</li><li>Each thread of bw_new also calls this function for the first write to each of its buffers. This first write is not timed [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 56  === bw_new k_copy ===
 57  0000000000001ca0 &lt;k_copy&gt;:
 58      1ca0:	add	x2, x1, x2, lsl #3
 59      1ca4:	ldp	q31, q30, [x1]
 60      1ca8:	ldp	q29, q28, [x1, #32]
 61      1cac:	ldp	q27, q26, [x1, #64]
 62      1cb0:	ldp	q25, q24, [x1, #96]
 63      1cb4:	ldp	q23, q22, [x1, #128]
 64      1cb8:	ldp	q21, q20, [x1, #160]
 65      1cbc:	ldp	q19, q18, [x1, #192]
 66      1cc0:	ldp	q17, q16, [x1, #224]
 67      1cc4:	add	x1, x1, #0x100
 68      1cc8:	stp	q31, q30, [x0]
 69      1ccc:	add	x0, x0, #0x100
 70      1cd0:	stp	q29, q28, [x0, #-224]
 71      1cd4:	stp	q27, q26, [x0, #-192]
 72      1cd8:	stp	q25, q24, [x0, #-160]
 73      1cdc:	stp	q23, q22, [x0, #-128]
 74      1ce0:	stp	q21, q20, [x0, #-96]
 75      1ce4:	stp	q19, q18, [x0, #-64]
 76      1ce8:	stp	q17, q16, [x0, #-32]
 77      1cec:	cmp	x2, x1
 78      1cf0:	b.hi	1ca4 &lt;k_copy+0x4&gt;  // b.pmore
 79      1cf4:	ret
 80</pre></td><td valign="top">The copy kernel of bw_new. Per loop pass (<code>1ca4</code> to <code>1cf0</code>) 8 <code>ldp</code> read 256 bytes from the source at <code>x1</code>, and 8 <code>stp</code> write them to the destination at <code>x0</code>. The 8 loads stand before the 8 stores.</td></tr>
<tr><td colspan="2"><b><code>bw_new k_asmread</code>: the hand-written load-only loop (asmread)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 81  === bw_new k_asmread ===
 82  0000000000001b40 &lt;k_asmread&gt;:</pre></td><td valign="top">objdump text of <code>k_asmread</code> of bw_new. The loop is the text of an inline assembly block in the source. gcc added the instructions around it [Ref3].<ul><li>Loop: addresses <code>1b54</code> to <code>1b7c</code> (lines 88 to 98), 11 instructions, 44 bytes of code.</li><li>Bytes read per loop pass: 256.</li><li>Load instructions per loop pass: 8.</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>Loaded values: no instruction uses them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 83      1b40:	stp	d8, d9, [sp, #-64]!</pre></td><td valign="top"><code>stp</code> (store pair) with <code>[sp, #-64]!</code>: first lower the stack pointer <code>sp</code> by 64 bytes, then store <code>d8</code> and <code>d9</code> there. <code>d8</code> is the low 8 bytes of vector register 8. This writes 16 bytes to the stack, not to the buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 84      1b44:	add	x1, x0, x1, lsl #3</pre></td><td valign="top"><code>x1 = x0 + x1 * 8</code>: the address of the first byte after the buffer, as in line 25.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 85      1b48:	stp	d10, d11, [sp, #16]
 86      1b4c:	stp	d12, d13, [sp, #32]
 87      1b50:	stp	d14, d15, [sp, #48]</pre></td><td valign="top">Store <code>d10</code> to <code>d15</code> to the stack, once per call. The loop overwrites the vector registers 8 to 15. AAPCS64 (the calling rules of 64-bit Arm) requires that a function leaves their low 8 bytes unchanged for its caller. So gcc saves them in lines 83 to 87 and restores them in lines 99 to 102 [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 88      1b54:	ldp	q0, q1, [x0]</pre></td><td valign="top">Loop start. <code>ldp</code> reads 32 bytes of the buffer at the address in <code>x0</code> into the 16-byte registers <code>q0</code> and <code>q1</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 89      1b58:	ldp	q2, q3, [x0, #32]
 90      1b5c:	ldp	q4, q5, [x0, #64]
 91      1b60:	ldp	q6, q7, [x0, #96]
 92      1b64:	ldp	q8, q9, [x0, #128]
 93      1b68:	ldp	q10, q11, [x0, #160]
 94      1b6c:	ldp	q12, q13, [x0, #192]
 95      1b70:	ldp	q14, q15, [x0, #224]</pre></td><td valign="top">7 more <code>ldp</code> loads of 32 bytes each, at the offsets 32 to 224 bytes from <code>x0</code>. With line 88 this gives 8 loads that read bytes 0 to 255, each byte once. The data go to the registers <code>q0</code> to <code>q15</code>. No instruction of the function reads these registers, and the next loop pass overwrites them.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 96      1b74:	add	x0, x0, #0x100</pre></td><td valign="top"><code>x0 = x0 + 256</code> (<code>0x100</code>). The pointer moves to the next 256 bytes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 97      1b78:	cmp	x0, x1
 98      1b7c:	b.cc	1b54 &lt;k_asmread+0x14&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp</code> compares the pointer <code>x0</code> with the end address <code>x1</code>. <code>b.cc</code> jumps back to <code>1b54</code> (line 88) while the pointer is lower (unsigned compare). This is the loop condition of lines 35 and 36 with the two operands exchanged. The loop runs at least once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 99      1b80:	ldp	d10, d11, [sp, #16]
100      1b84:	ldp	d12, d13, [sp, #32]
101      1b88:	ldp	d14, d15, [sp, #48]
102      1b8c:	ldp	d8, d9, [sp], #64</pre></td><td valign="top">After the loop: load <code>d10</code> to <code>d15</code>, then <code>d8</code> and <code>d9</code>, back from the stack. Line 102 also raises <code>sp</code> by 64 bytes. These 4 <code>ldp</code> read 16 bytes each from the stack, not from the buffer. They run once per call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">103      1b90:	ret
104</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><b><code>bw_new k_asmwrite</code> and <code>bw_new k_asmcopy</code>: hand-written write and copy loops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">105  === bw_new k_asmwrite ===
106  0000000000001ba0 &lt;k_asmwrite&gt;:
107      1ba0:	add	x1, x0, x1, lsl #3
108      1ba4:	dup	v0.2d, x2
109      1ba8:	stp	q0, q0, [x0]
110      1bac:	stp	q0, q0, [x0, #32]
111      1bb0:	stp	q0, q0, [x0, #64]
112      1bb4:	stp	q0, q0, [x0, #96]
113      1bb8:	stp	q0, q0, [x0, #128]
114      1bbc:	stp	q0, q0, [x0, #160]
115      1bc0:	stp	q0, q0, [x0, #192]
116      1bc4:	stp	q0, q0, [x0, #224]
117      1bc8:	add	x0, x0, #0x100
118      1bcc:	cmp	x0, x1
119      1bd0:	b.cc	1ba8 &lt;k_asmwrite+0x8&gt;  // b.lo, b.ul, b.last
120      1bd4:	ret
121</pre></td><td valign="top">The hand-written write loop of bw_new. <code>dup</code> copies the 64-bit value in <code>x2</code> into both halves of <code>v0</code>. The loop (<code>1ba8</code> to <code>1bd0</code>) writes 256 bytes per pass with 8 <code>stp</code> of 32 bytes each.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">122  === bw_new k_asmcopy ===
123  0000000000001be0 &lt;k_asmcopy&gt;:
124      1be0:	stp	d8, d9, [sp, #-64]!
125      1be4:	add	x2, x1, x2, lsl #3
126      1be8:	stp	d10, d11, [sp, #16]
127      1bec:	stp	d12, d13, [sp, #32]
128      1bf0:	stp	d14, d15, [sp, #48]
129      1bf4:	ldp	q0, q1, [x1]
130      1bf8:	ldp	q2, q3, [x1, #32]
131      1bfc:	ldp	q4, q5, [x1, #64]
132      1c00:	ldp	q6, q7, [x1, #96]
133      1c04:	ldp	q8, q9, [x1, #128]
134      1c08:	ldp	q10, q11, [x1, #160]
135      1c0c:	ldp	q12, q13, [x1, #192]
136      1c10:	ldp	q14, q15, [x1, #224]
137      1c14:	stp	q0, q1, [x0]
138      1c18:	stp	q2, q3, [x0, #32]
139      1c1c:	stp	q4, q5, [x0, #64]
140      1c20:	stp	q6, q7, [x0, #96]
141      1c24:	stp	q8, q9, [x0, #128]
142      1c28:	stp	q10, q11, [x0, #160]
143      1c2c:	stp	q12, q13, [x0, #192]
144      1c30:	stp	q14, q15, [x0, #224]
145      1c34:	add	x1, x1, #0x100
146      1c38:	add	x0, x0, #0x100
147      1c3c:	cmp	x1, x2
148      1c40:	b.cc	1bf4 &lt;k_asmcopy+0x14&gt;  // b.lo, b.ul, b.last
149      1c44:	ldp	d10, d11, [sp, #16]
150      1c48:	ldp	d12, d13, [sp, #32]
151      1c4c:	ldp	d14, d15, [sp, #48]
152      1c50:	ldp	d8, d9, [sp], #64
153      1c54:	ret
154</pre></td><td valign="top">The hand-written copy loop of bw_new. Per loop pass (<code>1bf4</code> to <code>1c40</code>) 8 <code>ldp</code> read 256 bytes from the source at <code>x1</code>, then 8 <code>stp</code> write them to the destination at <code>x0</code>. The function saves and restores <code>d8</code> to <code>d15</code> outside the loop, as <code>k_asmread</code> does.</td></tr>
<tr><td colspan="2"><b><code>bw_old k_read</code>: the old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">155  === bw_old k_read ===
156  0000000000001b00 &lt;k_read&gt;:</pre></td><td valign="top">objdump text of <code>k_read</code> of bw_old. gcc built it from a plain C loop that adds each 8-byte word of the buffer to one of 16 sums [Ref4].<ul><li>Loop: addresses <code>1b68</code> to <code>1ba4</code> (lines 183 to 198), 16 instructions, 64 bytes of code.</li><li>Bytes read per loop pass: 128.</li><li>Load instructions per loop pass: 4.</li><li>Other instructions per loop pass: 12 (8 vector <code>add</code>, 2 integer <code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>Per 256 bytes: 2 loop passes with 8 loads and 24 other instructions.</li><li>Loaded values: each one is added to a running sum.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">157      1b00:	movi	v31.4s, #0x0
158      1b04:	sub	sp, sp, #0xa0</pre></td><td valign="top"><code>movi</code> sets all 128 bits of the vector register <code>v31</code> to zero. <code>sub</code> lowers the stack pointer <code>sp</code> by 160 bytes (<code>0xa0</code>). The function uses this space for the 16 sums (128 bytes), a copy of the guard value of the stack protector and two saved registers.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">159      1b08:	adrp	x3, 1f000 &lt;__FRAME_END__+0x1c390&gt;
160      1b0c:	ldr	x3, [x3, #4072]</pre></td><td valign="top">Get the address of the guard value of the stack protector (see Words used here). <code>adrp</code> puts the page address <code>1f000</code> into <code>x3</code>. <code>ldr</code> loads the 8-byte pointer that lies 4072 bytes after this address.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">161      1b10:	stp	x29, x30, [sp, #144]
162      1b14:	add	x29, sp, #0x90</pre></td><td valign="top">Store <code>x29</code> (frame pointer) and <code>x30</code> (return address) on the stack at <code>sp + 144</code>. Then set <code>x29</code> to <code>sp + 144</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">163      1b18:	ldr	x4, [x3]
164      1b1c:	str	x4, [sp, #136]
165      1b20:	mov	x4, #0x0                   	// #0</pre></td><td valign="top">Load the guard value (8 bytes) into <code>x4</code> and store a copy on the stack at <code>sp + 136</code>. Then set <code>x4</code> to zero.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">166      1b24:	stp	q31, q31, [sp]
167      1b28:	stp	q31, q31, [sp, #32]
168      1b2c:	stp	q31, q31, [sp, #64]
169      1b30:	stp	q31, q31, [sp, #96]</pre></td><td valign="top">4 <code>stp</code> write 4 x 32 = 128 zero bytes to the stack at <code>sp</code>. This is the array <code>s</code> of the source: the 16 sums, set to zero [Ref4]. These are stores to the stack, not to the buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">170      1b34:	cbz	x1, 1bb8 &lt;k_read+0xb8&gt;</pre></td><td valign="top"><code>cbz</code>: when <code>x1</code> (the buffer length in 8-byte words) is zero, jump to <code>1bb8</code> (line 203). This skips the loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">171      1b38:	movi	v31.4s, #0x0
172      1b3c:	sub	x2, x1, #0x1
173      1b40:	mov	x1, #0x0                   	// #0
174      1b44:	lsr	x2, x2, #4
175      1b48:	add	x2, x2, #0x1</pre></td><td valign="top">Loop setup. <code>x2 = ((x1 - 1) &gt;&gt; 4) + 1</code> is the number of loop passes: one pass per 16 words (128 bytes), rounded up. <code>x1 = 0</code> is the pass counter. <code>movi</code> sets <code>v31</code> to zero again.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">176      1b4c:	mov	v30.16b, v31.16b
177      1b50:	mov	v29.16b, v31.16b
178      1b54:	mov	v28.16b, v31.16b
179      1b58:	mov	v27.16b, v31.16b
180      1b5c:	mov	v26.16b, v31.16b
181      1b60:	mov	v25.16b, v31.16b
182      1b64:	mov	v24.16b, v31.16b</pre></td><td valign="top"><ul><li>Copy the zero of <code>v31</code> into <code>v30</code> to <code>v24</code>.</li><li>The 8 registers <code>v24</code> to <code>v31</code> are the sum registers. Each one holds two 64-bit sums. Together they hold the 16 running sums.</li><li>Lines 157 to 182 run once per call.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">183      1b68:	ldp	q6, q5, [x0]</pre></td><td valign="top">Loop start. <code>ldp</code> reads 32 bytes of the buffer at the address in <code>x0</code> into the 16-byte registers <code>q6</code> and <code>q5</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">184      1b6c:	add	x1, x1, #0x1</pre></td><td valign="top">Pass counter: <code>x1 = x1 + 1</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">185      1b70:	ldp	q4, q3, [x0, #32]
186      1b74:	ldp	q2, q1, [x0, #64]
187      1b78:	ldp	q0, q23, [x0, #96]</pre></td><td valign="top">3 more <code>ldp</code> loads of 32 bytes each, at the offsets 32, 64 and 96 bytes from <code>x0</code>. With line 183 this gives 4 loads that read bytes 0 to 127, each byte once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">188      1b7c:	add	x0, x0, #0x80</pre></td><td valign="top"><code>x0 = x0 + 128</code> (<code>0x80</code>). The pointer moves to the next 128 bytes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">189      1b80:	add	v24.2d, v24.2d, v6.2d
190      1b84:	add	v25.2d, v25.2d, v5.2d
191      1b88:	add	v26.2d, v26.2d, v4.2d
192      1b8c:	add	v27.2d, v27.2d, v3.2d
193      1b90:	add	v28.2d, v28.2d, v2.2d
194      1b94:	add	v29.2d, v29.2d, v1.2d
195      1b98:	add	v30.2d, v30.2d, v0.2d
196      1b9c:	add	v31.2d, v31.2d, v23.2d</pre></td><td valign="top">8 vector adds, one per loaded register.<ul><li><code>add v24.2d, v24.2d, v6.2d</code> takes each register as two 64-bit numbers and adds <code>v6</code> to the sum register <code>v24</code>.</li><li>Every loaded register goes into its own sum register. So the 8 adds of one loop pass do not depend on each other.</li><li>Each add needs the value of its sum register from the loop pass before.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">197      1ba0:	cmp	x1, x2
198      1ba4:	b.cc	1b68 &lt;k_read+0x68&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp</code> compares the pass counter <code>x1</code> with the number of passes <code>x2</code>. <code>b.cc</code> jumps back to <code>1b68</code> (line 183) while the counter is lower (unsigned compare).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">199      1ba8:	stp	q24, q25, [sp]
200      1bac:	stp	q26, q27, [sp, #32]
201      1bb0:	stp	q28, q29, [sp, #64]
202      1bb4:	stp	q30, q31, [sp, #96]</pre></td><td valign="top">After the loop: 4 <code>stp</code> store the 8 sum registers into the 128 bytes at <code>sp</code> (the array <code>s</code>). These are stores to the stack. They run once per call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">203      1bb8:	ldp	q28, q31, [sp]
204      1bbc:	ldp	q30, q29, [sp, #32]
205      1bc0:	ldp	q26, q27, [sp, #64]
206      1bc4:	add	v31.2d, v31.2d, v28.2d
207      1bc8:	add	v30.2d, v30.2d, v29.2d
208      1bcc:	ldp	q28, q29, [sp, #96]
209      1bd0:	add	v31.2d, v31.2d, v26.2d
210      1bd4:	add	v30.2d, v30.2d, v27.2d</pre></td><td valign="top">4 <code>ldp</code> load the 16 sums back from the stack, 32 bytes each, and 4 <code>add</code> start to add them up in <code>v31</code> and <code>v30</code>. Line 203 is also the target of the jump of line 170. These <code>ldp</code> read the stack, not the buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">211      1bd8:	adrp	x0, 1f000 &lt;__FRAME_END__+0x1c390&gt;
212      1bdc:	ldr	x0, [x0, #4072]</pre></td><td valign="top">Get the address of the guard value again, as in lines 159 and 160. Line 212 is a load of 8 bytes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">213      1be0:	add	v31.2d, v31.2d, v28.2d
214      1be4:	add	v30.2d, v30.2d, v29.2d</pre></td><td valign="top">Two more adds of the sums into <code>v31</code> and <code>v30</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">215      1be8:	ldr	x2, [sp, #136]
216      1bec:	ldr	x1, [x0]
217      1bf0:	subs	x2, x2, x1
218      1bf4:	mov	x1, #0x0                   	// #0</pre></td><td valign="top"><ul><li><code>x2</code> = the copy of the guard value from <code>sp + 136</code>. <code>x1</code> = the guard value now. Each of these two loads reads 8 bytes.</li><li><code>subs</code> subtracts <code>x1</code> from <code>x2</code> and sets the condition flags for line 221.</li><li><code>mov</code> sets <code>x1</code> to zero.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">219      1bf8:	add	v31.2d, v31.2d, v30.2d
220      1bfc:	addp	d31, v31.2d</pre></td><td valign="top"><code>add</code> adds <code>v30</code> to <code>v31</code>. <code>addp</code> adds the two 64-bit halves of <code>v31</code> into <code>d31</code>. <code>d31</code> now holds the total of the 16 sums.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">221      1c00:	b.ne	1c14 &lt;k_read+0x114&gt;  // b.any</pre></td><td valign="top"><code>b.ne</code>: when the two guard values of lines 215 and 216 differ, jump to <code>1c14</code> (line 226).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">222      1c04:	ldp	x29, x30, [sp, #144]
223      1c08:	fmov	x0, d31
224      1c0c:	add	sp, sp, #0xa0
225      1c10:	ret</pre></td><td valign="top">Restore <code>x29</code> and <code>x30</code> with one 16-byte load from the stack. <code>fmov</code> copies the total into <code>x0</code>, the register that carries the return value. <code>add</code> raises <code>sp</code> by 160 bytes, and <code>ret</code> returns. The caller stores the returned total into a <code>volatile</code> variable of the thread [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">226      1c14:	bl	d50 &lt;__stack_chk_fail@plt&gt;
227</pre></td><td valign="top">This line is reached only when the copy on the stack differs from the guard value (the compare of line 217). It calls the C library function <code>__stack_chk_fail</code>. That function ends the program.</td></tr>
<tr><td colspan="2"><b><code>bw_old k_write</code> and <code>bw_old k_copy</code>: write and copy kernels of bw_old</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">228  === bw_old k_write ===
229  0000000000001c20 &lt;k_write&gt;:
230      1c20:	cbz	x1, 1c50 &lt;k_write+0x30&gt;
231      1c24:	mov	x3, #0x0                   	// #0
232      1c28:	cntd	x4
233      1c2c:	mov	z31.d, x2
234      1c30:	whilelo	p7.d, xzr, x1
235      1c34:	nop
236      1c38:	nop
237      1c3c:	nop
238      1c40:	st1d	{z31.d}, p7, [x0, x3, lsl #3]
239      1c44:	add	x3, x3, x4
240      1c48:	whilelo	p7.d, x3, x1
241      1c4c:	b.ne	1c40 &lt;k_write+0x20&gt;  // b.any
242      1c50:	ret
243</pre></td><td valign="top">The write kernel of bw_old. gcc built it from a plain C loop and used SVE instructions [Ref4].<ul><li>Before the loop: <code>cntd</code> puts the number of 8-byte elements of one SVE register into <code>x4</code>. <code>mov z31.d, x2</code> copies the value to write into every element of <code>z31</code>. The 3 <code>nop</code> instructions do nothing.</li><li>Loop (<code>1c40</code> to <code>1c4c</code>): <code>st1d</code> stores the register <code>z31</code> to the buffer, <code>add</code> moves the index <code>x3</code>, <code>whilelo</code> marks the elements that are left, and <code>b.ne</code> repeats while one is left.</li><li>A record of the same day gives 16 bytes as the default SVE register size of a process on CRB [Ref10]. With this size one loop pass writes 16 bytes.</li><li>Each thread of bw_old also calls this function for the first write to each of its buffers. This first write is not timed [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">244  === bw_old k_copy ===
245  0000000000001c60 &lt;k_copy&gt;:
246      1c60:	cbz	x2, 1c84 &lt;k_copy+0x24&gt;
247      1c64:	mov	x3, #0x0                   	// #0
248      1c68:	cntd	x4
249      1c6c:	whilelo	p7.d, xzr, x2
250      1c70:	ld1d	{z31.d}, p7/z, [x1, x3, lsl #3]
251      1c74:	st1d	{z31.d}, p7, [x0, x3, lsl #3]
252      1c78:	add	x3, x3, x4
253      1c7c:	whilelo	p7.d, x3, x2
254      1c80:	b.ne	1c70 &lt;k_copy+0x10&gt;  // b.any
255      1c84:	ret
256</pre></td><td valign="top">The copy kernel of bw_old, also built with SVE instructions. Per loop pass (<code>1c70</code> to <code>1c80</code>) one <code>ld1d</code> loads one SVE register from the source at <code>x1</code>, and one <code>st1d</code> stores it to the destination at <code>x0</code>. With the 16-byte register size of the row above, one loop pass copies 16 bytes.</td></tr>
<tr><td colspan="2"><b><code>bw_old k_asmread</code>: the same hand-written loop in bw_old</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">257  === bw_old k_asmread ===
258  0000000000001c88 &lt;k_asmread&gt;:</pre></td><td valign="top">objdump text of <code>k_asmread</code> of bw_old. Its instructions are the same as in <code>bw_new k_asmread</code> (lines 83 to 103). Only the addresses differ.<ul><li>Loop: addresses <code>1c9c</code> to <code>1cc4</code> (lines 264 to 274), 11 instructions, 44 bytes of code.</li><li>Bytes read per loop pass: 256.</li><li>Load instructions per loop pass: 8.</li><li>Other instructions per loop pass: 3 (<code>add</code>, <code>cmp</code>, <code>b.cc</code>).</li><li>Loaded values: no instruction uses them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">259      1c88:	stp	d8, d9, [sp, #-64]!</pre></td><td valign="top">First lower the stack pointer <code>sp</code> by 64 bytes, then store <code>d8</code> and <code>d9</code> there (the low 8 bytes of the vector registers 8 and 9). This writes to the stack, not to the buffer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">260      1c8c:	add	x1, x0, x1, lsl #3</pre></td><td valign="top"><code>x1 = x0 + x1 * 8</code>: the address of the first byte after the buffer. <code>x0</code> is the buffer address and <code>x1</code> its length in 8-byte words.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">261      1c90:	stp	d10, d11, [sp, #16]
262      1c94:	stp	d12, d13, [sp, #32]
263      1c98:	stp	d14, d15, [sp, #48]</pre></td><td valign="top">Store <code>d10</code> to <code>d15</code> to the stack. Lines 259 to 263 run once per call, before the loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">264      1c9c:	ldp	q0, q1, [x0]</pre></td><td valign="top">Loop start. <code>ldp</code> reads 32 bytes of the buffer at the address in <code>x0</code> into the 16-byte registers <code>q0</code> and <code>q1</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">265      1ca0:	ldp	q2, q3, [x0, #32]
266      1ca4:	ldp	q4, q5, [x0, #64]
267      1ca8:	ldp	q6, q7, [x0, #96]
268      1cac:	ldp	q8, q9, [x0, #128]
269      1cb0:	ldp	q10, q11, [x0, #160]
270      1cb4:	ldp	q12, q13, [x0, #192]
271      1cb8:	ldp	q14, q15, [x0, #224]</pre></td><td valign="top">7 more <code>ldp</code> loads of 32 bytes each, at the offsets 32 to 224 bytes from <code>x0</code>. With line 264 this gives 8 loads that read bytes 0 to 255, each byte once. No instruction of the function reads the registers <code>q0</code> to <code>q15</code>, and the next loop pass overwrites them.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">272      1cbc:	add	x0, x0, #0x100</pre></td><td valign="top"><code>x0 = x0 + 256</code> (<code>0x100</code>). The pointer moves to the next 256 bytes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">273      1cc0:	cmp	x0, x1
274      1cc4:	b.cc	1c9c &lt;k_asmread+0x14&gt;  // b.lo, b.ul, b.last</pre></td><td valign="top"><code>cmp</code> compares the pointer <code>x0</code> with the end address <code>x1</code>. <code>b.cc</code> jumps back to <code>1c9c</code> (line 264) while the pointer is lower (unsigned compare). The loop runs at least once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">275      1cc8:	ldp	d10, d11, [sp, #16]
276      1ccc:	ldp	d12, d13, [sp, #32]
277      1cd0:	ldp	d14, d15, [sp, #48]
278      1cd4:	ldp	d8, d9, [sp], #64</pre></td><td valign="top">After the loop: load <code>d8</code> to <code>d15</code> back from the stack. Line 278 also raises <code>sp</code> by 64 bytes. These 4 <code>ldp</code> read 16 bytes each from the stack, not from the buffer. They run once per call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">279      1cd8:	ret
280</pre></td><td valign="top"><code>ret</code> returns to the caller. The function returns no value.</td></tr>
<tr><td colspan="2"><b><code>bw_old k_asmwrite</code> and <code>bw_old k_asmcopy</code>: hand-written write and copy loops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">281  === bw_old k_asmwrite ===
282  0000000000001ce0 &lt;k_asmwrite&gt;:
283      1ce0:	add	x1, x0, x1, lsl #3
284      1ce4:	dup	v0.2d, x2
285      1ce8:	stp	q0, q0, [x0]
286      1cec:	stp	q0, q0, [x0, #32]
287      1cf0:	stp	q0, q0, [x0, #64]
288      1cf4:	stp	q0, q0, [x0, #96]
289      1cf8:	stp	q0, q0, [x0, #128]
290      1cfc:	stp	q0, q0, [x0, #160]
291      1d00:	stp	q0, q0, [x0, #192]
292      1d04:	stp	q0, q0, [x0, #224]
293      1d08:	add	x0, x0, #0x100
294      1d0c:	cmp	x0, x1
295      1d10:	b.cc	1ce8 &lt;k_asmwrite+0x8&gt;  // b.lo, b.ul, b.last
296      1d14:	ret
297</pre></td><td valign="top">The hand-written write loop of bw_old. Its instructions are the same as in <code>bw_new k_asmwrite</code> (lines 107 to 120). Only the addresses differ. The loop (<code>1ce8</code> to <code>1d10</code>) writes 256 bytes per pass with 8 <code>stp</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">298  === bw_old k_asmcopy ===
299  0000000000001d20 &lt;k_asmcopy&gt;:
300      1d20:	stp	d8, d9, [sp, #-64]!
301      1d24:	add	x2, x1, x2, lsl #3
302      1d28:	stp	d10, d11, [sp, #16]
303      1d2c:	stp	d12, d13, [sp, #32]
304      1d30:	stp	d14, d15, [sp, #48]
305      1d34:	ldp	q0, q1, [x1]
306      1d38:	ldp	q2, q3, [x1, #32]
307      1d3c:	ldp	q4, q5, [x1, #64]
308      1d40:	ldp	q6, q7, [x1, #96]
309      1d44:	ldp	q8, q9, [x1, #128]
310      1d48:	ldp	q10, q11, [x1, #160]
311      1d4c:	ldp	q12, q13, [x1, #192]
312      1d50:	ldp	q14, q15, [x1, #224]
313      1d54:	stp	q0, q1, [x0]
314      1d58:	stp	q2, q3, [x0, #32]
315      1d5c:	stp	q4, q5, [x0, #64]
316      1d60:	stp	q6, q7, [x0, #96]
317      1d64:	stp	q8, q9, [x0, #128]
318      1d68:	stp	q10, q11, [x0, #160]
319      1d6c:	stp	q12, q13, [x0, #192]
320      1d70:	stp	q14, q15, [x0, #224]
321      1d74:	add	x1, x1, #0x100
322      1d78:	add	x0, x0, #0x100
323      1d7c:	cmp	x1, x2
324      1d80:	b.cc	1d34 &lt;k_asmcopy+0x14&gt;  // b.lo, b.ul, b.last
325      1d84:	ldp	d10, d11, [sp, #16]
326      1d88:	ldp	d12, d13, [sp, #32]
327      1d8c:	ldp	d14, d15, [sp, #48]
328      1d90:	ldp	d8, d9, [sp], #64
329      1d94:	ret
330</pre></td><td valign="top">The hand-written copy loop of bw_old. Its instructions are the same as in <code>bw_new k_asmcopy</code> (lines 124 to 153). Only the addresses differ. The loop (<code>1d34</code> to <code>1d80</code>) reads 256 bytes with 8 <code>ldp</code> and writes them with 8 <code>stp</code>.</td></tr>
<tr><td colspan="2"><b><code>probe.o</code>: three candidates for the copy kernel, compiled only</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">331  === probe.o copy_barrier ===
332  0000000000000000 &lt;copy_barrier&gt;:
333     0:	add	x2, x1, x2, lsl #3
334     4:	ldp	q31, q30, [x1]
335     8:	ldp	q29, q28, [x1, #32]
336     c:	ldp	q27, q26, [x1, #64]
337    10:	ldp	q25, q24, [x1, #96]
338    14:	ldp	q23, q22, [x1, #128]
339    18:	ldp	q21, q20, [x1, #160]
340    1c:	ldp	q19, q18, [x1, #192]
341    20:	ldp	q17, q16, [x1, #224]
342    24:	add	x1, x1, #0x100
343    28:	stp	q31, q30, [x0]
344    2c:	add	x0, x0, #0x100
345    30:	stp	q29, q28, [x0, #-224]
346    34:	stp	q27, q26, [x0, #-192]
347    38:	stp	q25, q24, [x0, #-160]
348    3c:	stp	q23, q22, [x0, #-128]
349    40:	stp	q21, q20, [x0, #-96]
350    44:	stp	q19, q18, [x0, #-64]
351    48:	stp	q17, q16, [x0, #-32]
352    4c:	cmp	x2, x1
353    50:	b.hi	4 &lt;copy_barrier+0x4&gt;  // b.pmore
354    54:	ret</pre></td><td valign="top">The function <code>copy_barrier</code> of probe.o, which run_kernels.sh compiled from probe.c but never linked or ran [Ref1]. So its addresses start at 0. This candidate has the empty asm statement between the loads and the stores [Ref6]. Its instructions are the same as in <code>bw_new k_copy</code> (lines 58 to 79): 8 <code>ldp</code>, then 8 <code>stp</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">355  === probe.o copy_plain ===
356  0000000000000060 &lt;copy_plain&gt;:
357    60:	add	x2, x1, x2, lsl #3
358    64:	ldp	q31, q30, [x1]
359    68:	add	x0, x0, #0x100
360    6c:	stur	q31, [x0, #-256]
361    70:	ldp	q29, q31, [x1, #32]
362    74:	stp	q30, q29, [x0, #-240]
363    78:	ldp	q29, q30, [x1, #64]
364    7c:	stp	q31, q29, [x0, #-208]
365    80:	ldp	q29, q31, [x1, #96]
366    84:	stp	q30, q29, [x0, #-176]
367    88:	ldp	q29, q30, [x1, #128]
368    8c:	stp	q31, q29, [x0, #-144]
369    90:	ldp	q29, q31, [x1, #160]
370    94:	stp	q30, q29, [x0, #-112]
371    98:	ldp	q29, q30, [x1, #192]
372    9c:	stp	q31, q29, [x0, #-80]
373    a0:	ldp	q29, q31, [x1, #224]
374    a4:	add	x1, x1, #0x100
375    a8:	stp	q30, q29, [x0, #-48]
376    ac:	stur	q31, [x0, #-16]
377    b0:	cmp	x2, x1
378    b4:	b.hi	64 &lt;copy_plain+0x4&gt;  // b.pmore
379    b8:	ret</pre></td><td valign="top">The candidate without the empty asm statement [Ref6]. Loads and stores alternate here. The whole-chip test does not run this code.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">380  === probe.o copy_plain_norestrict ===
381  00000000000000c0 &lt;copy_plain_norestrict&gt;:
382    c0:	add	x2, x1, x2, lsl #3
383    c4:	ldp	q17, q16, [x1]
384    c8:	add	x0, x0, #0x100
385    cc:	ldp	q19, q18, [x1, #32]
386    d0:	ldp	q21, q20, [x1, #64]
387    d4:	ldp	q23, q22, [x1, #96]
388    d8:	ldp	q25, q24, [x1, #128]
389    dc:	ldp	q27, q26, [x1, #160]
390    e0:	ldp	q29, q28, [x1, #192]
391    e4:	ldp	q31, q30, [x1, #224]
392    e8:	add	x1, x1, #0x100
393    ec:	stp	q17, q16, [x0, #-256]
394    f0:	stp	q19, q18, [x0, #-224]
395    f4:	stp	q21, q20, [x0, #-192]
396    f8:	stp	q23, q22, [x0, #-160]
397    fc:	stp	q25, q24, [x0, #-128]
398   100:	stp	q27, q26, [x0, #-96]
399   104:	stp	q29, q28, [x0, #-64]
400   108:	stp	q31, q30, [x0, #-32]
401   10c:	cmp	x2, x1
402   110:	b.hi	c4 &lt;copy_plain_norestrict+0x4&gt;  // b.pmore
403   114:	ret</pre></td><td valign="top">The candidate without the empty asm statement and without the keyword <code>restrict</code> [Ref6]. Here the 8 <code>ldp</code> stand before the 8 <code>stp</code> again. The whole-chip test does not run this code.</td></tr>
<tr><td colspan="2"><b><code>chase</code>: a function of two other benchmark binaries</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">404  === bench/latency chase ===
405  0000000000001b40 &lt;chase&gt;:
406      1b40:	cbz	x1, 1b74 &lt;chase+0x34&gt;
407      1b44:	mov	x2, #0x0                   	// #0
408      1b48:	ldr	x0, [x0]
409      1b4c:	add	x2, x2, #0x8
410      1b50:	ldr	x0, [x0]
411      1b54:	ldr	x0, [x0]
412      1b58:	ldr	x0, [x0]
413      1b5c:	ldr	x0, [x0]
414      1b60:	ldr	x0, [x0]
415      1b64:	ldr	x0, [x0]
416      1b68:	ldr	x0, [x0]
417      1b6c:	cmp	x1, x2
418      1b70:	b.hi	1b48 &lt;chase+0x8&gt;  // b.pmore
419      1b74:	ret
420</pre></td><td valign="top">The function <code>chase</code> of the binary <code>latency</code> in the folder <code>~/cache-perf/bench</code> of CRB, which run_kernels.sh did not build [Ref1].<ul><li>The loop (<code>1b48</code> to <code>1b70</code>) holds 8 <code>ldr x0, [x0]</code>. Each one loads 8 bytes from the address in <code>x0</code> into <code>x0</code>. So each load gives the address for the next load.</li><li>The whole-chip test does not run this code.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">421  === bench/homelat chase ===
422  00000000000049a0 &lt;chase&gt;:
423      49a0:	mov	w2, #0x0                   	// #0
424      49a4:	ldr	x0, [x0]
425      49a8:	add	w2, w2, #0x8
426      49ac:	ldr	x0, [x0]
427      49b0:	ldr	x0, [x0]
428      49b4:	ldr	x0, [x0]
429      49b8:	ldr	x0, [x0]
430      49bc:	ldr	x0, [x0]
431      49c0:	ldr	x0, [x0]
432      49c4:	ldr	x0, [x0]
433      49c8:	cmp	w1, w2
434      49cc:	b.gt	49a4 &lt;chase+0x4&gt;
435      49d0:	ret
436</pre></td><td valign="top">The function <code>chase</code> of the binary <code>homelat</code> in the same folder. Its loop (<code>49a4</code> to <code>49cc</code>) holds the same 8 <code>ldr x0, [x0]</code> loads. The whole-chip test does not run this code.</td></tr>
<tr><td colspan="2"><b>Footer: self-test result and load after the timed runs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">437  ## selftest exit=0</pre></td><td valign="top"><code>selftest</code> is the self-test program. It includes the new source bandwidth.c and checks what its six kernels do to memory. Exit status 0 means that every check passed [Ref7]. Its output is in the file <code>selftest.txt</code> of the same folder.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">438  ## one-thread done load=1.00 0.65 0.29 utc=2026-11-13T18:17:21Z</pre></td><td valign="top">Written after the one-thread timed runs of 2026-11-13, whose results are in <code>one-thread.csv</code> [Ref1]. <code>load</code> is the load average of the last 1, 5 and 15 minutes at the time <code>utc</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">439  ## load_after=85.38 27.01 9.53 utc=2026-11-13T18:18:37Z</pre></td><td valign="top">Written after the 120-thread timed runs of 2026-11-13, whose results are in <code>threads120.csv</code> [Ref1]. It is the last line that run_kernels.sh wrote to this file. The 1-minute load average was 85.38 tasks directly after these runs.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: the script that wrote this file (its sha256 equals line 18). Lines 21 to 27: the header and the process list. Lines 29 to 35: the four builds and the line `build output bytes`. Lines 36 to 53: the sha256 block and the objdump calls. Line 40: the six kernel functions that are listed for each binary. Line 55: the self-test. Lines 74 and 79: the last two lines.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: the part A script of the rerun. Lines 14 to 20: the sha256 check of bw_old and bw_new. Lines 17 and 18 hold the two expected values. They equal lines 19 and 20 of this file. Lines 44 to 47: the 24 processes, each with `--bytes 256M`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: the new source (local copy, see the note on its sha256). Lines 184 to 211: `k_read` with 16 loads of 16 bytes and the empty asm statement. Lines 168 to 183 and 286 to 293: the comments on that statement and on the saved registers d8 to d15. Lines 297 to 319: `k_asmread`. Line 459: the first write with `k_write`. Line 469: the warm-up call before the first clock read. Lines 471 to 477: the two clock reads around the calls. Line 70: `M` means 2^20 bytes. Lines 184, 213, 239, 297, 321 and 344: the first lines of the six kernel functions, each marked `noinline`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`: the old source (its sha256 equals line 14). Lines 135 to 148: `k_read` with the array `s` of 16 sums. Lines 150 to 160: `k_write` and `k_copy` as plain C loops. Line 264: the caller stores the result of `k_read` into a volatile variable. Line 302: the first write with `k_write`. Line 312: the warm-up call before the first clock read. Lines 314 to 320: the two clock reads around the calls. Line 69: `M` means 2^20 bytes. Lines 138, 150, 156, 173, 197 and 220: the first lines of the six kernel functions, each marked `noinline`.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: the record of a later run of run_kernels.sh, of 2026-11-13 18:32:18 UTC. Line 1: `mode=probe` (no timed runs). Line 15: bandwidth.c with the sha256 `f1985072...`, the value of the local copy. Line 20: bw_new with the same sha256 as line 20 of this file. Lines 23 to 436: equal to lines 23 to 436 of this file (compared with the tool cmp).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/probe.c`: the source of probe.o (its sha256 equals line 17). Lines 19 to 36: the three copy candidates and their comments.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c`: the self-test (its sha256 equals line 16). Lines 1 to 17: what it checks, and that it includes bandwidth.c. Lines 161 and 162: the exit status.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: objdump text of bwx12. Lines 2 to 15 (`k_read`), 60 to 81 (`k_asmread`) and 134 to 204 (`k_oldread`) were compared with this file by a script: the instruction text is equal when the addresses are left out.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/probe.txt`: the record that ra.sh wrote in part A of the rerun, first of three. Lines 12 and 13 show the sha256 values of bw_old and bw_new. The files of `k120-T72A2-20261117T221518Z` and `k120-T72A3-20261117T221827Z` show the same values.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/results/partA-20261113T204939Z/A7-sve.txt`: line 2: the Linux file `/proc/sys/abi/sve_default_vector_length` on CRB held 16 (bytes) on 2026-11-13 at 20:49 UTC.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt`: a record from CRB of 2026-11-11. Line 5: what `-march=native` means for the same gcc version. The list holds SVE2 extensions. Line 3: SVE register size 16 bytes.
- [Ref12] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
