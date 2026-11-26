# `build.txt` explained

- Source file: `build.txt` in this folder (text file, 24 lines, 1748 bytes).
- sha256 of the source when this page was built: `3c9ed1c63a8b8451e0695b70ce0ac10a2d55fb6722acd5281a82f22a57e9a675`.
- Role in the whole-chip test: Build record of the runner bwx12: compiler, flags, self-test result, sha256 digests.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

build12.sh wrote this file on CRB on 2026-11-15, when it built the runner bwx12. The file records the machine load, the compiler and its flags, the result of the self-test, the calls inside the timed functions of the trial mode, the placement of five functions, and the sha256 digest of the bwx12 binary that the whole-chip test ran.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **bwx8, bwx10**: two more earlier versions of the runner program. build12.sh reads the symbol table of their accepted binaries.
- **Accepted binary**: the word of build12.sh for the binary of an earlier version (bwx8, bwx10, bwx11) that serves as the reference for a new build.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **build12.sh**: the script that builds bwx12 on CRB and writes this file. It stands in the folder above this one.
- **gcc**: the GNU C compiler.
- **Self-test**: the run `bwx12 --selftest`. It runs every kernel on test buffers and checks the trial mode. It prints one row with `pass` or `FAIL` per check.
- **Interval mode, trial mode**: the two modes of bwx12. Interval mode (option `--seq`): every thread runs a sequence of kernels, and each timed interval holds the calls of one kernel. The bwx12 processes of the whole-chip test use it. Trial mode (option `--trial`): one thread runs the trials of a plan file. The whole-chip test does not use it.
- **timed_sequence, timed_sequence_hot**: the two functions of the trial mode that run and time the kernels.
- **tcount**: a function of the trial mode. It reads the hardware counters and the CPU time of the thread.
- **call**: the function of bwx12.c that runs one kernel on a range of the buffer of a thread.
- **read_smaps**: the function of bwx12.c that reads from /proc/self/smaps the size of each buffer and the part of it that uses huge pages (pages of 2 MiB).
- **worker**: the thread function of the interval mode. It reads the clock before and after the kernel calls of an interval.
- **Branch target**: the address or the function that a branch or call instruction goes to.
- **blr, bl, b**: Arm branch instructions. `bl` calls a function at a fixed address. `blr` calls the function whose address a register holds. `b` jumps to a fixed address and keeps no return address.
- **Stack guard**: a value that the compiled code stores on the stack at the start of a function and compares before the return. If the value changed, the code calls `__stack_chk_fail`.
- **Modulo 64**: the remainder after a division by 64. For an address it is the position inside a 64-byte block, from 0 to 63. bwx12.c counts one cache line as 64 bytes.
- **Placement**: the start address of a function or a loop, modulo 64.
- **nm**: a command that lists the symbols of a binary: each function name with its address.
- **objdump**: a command that prints the machine code of a binary as assembler text, one instruction per line with its address.
- **sha256 digest**: a checksum of 256 bits that the command `sha256sum` computes from the content of a file. It is printed as 64 hexadecimal digits. The scripts use it to check that a file is the expected one.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg).
- **UTC**: Coordinated Universal Time, the time scale without a local time zone.
- **go.sh, go2.sh, rx.sh**: scripts of the whole-chip test. go.sh is the driver of the run. go2.sh is a second driver that was added later for two more bwx12 processes. rx.sh starts one bwx12 process per line of a spec file (a file that holds, per process, a tag and the arguments of bwx12).
- **env.txt**: the file that rx.sh writes first into each result folder. It holds the time, the Linux kernel version, the load, the logins, the busiest processes, and a line `binary` with the path and the sha256 digest of the binary.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Whole-chip test**: the run under review: the read test with 120 threads on CRB, run on 2026-11-17.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.

</details>

## How to read this file

1. A line that starts with `##` is written by build12.sh. Lines 17 to 23 are the direct output of `sha256sum`.
2. Read where and when the build ran, and with which compiler and flags (lines 1-3).
3. Read the compiler messages between the two marker lines. Here there is none (lines 4-5).
4. Read the result of the self-test of the new binary (line 6).
5. Read which functions the two timed functions of the trial mode call (lines 7-8).
6. Read where five functions start, modulo 64, in bwx12 and in three earlier binaries (bwx8 has four of the five) (lines 9-15).
7. Read the sha256 digests of the inputs, of the binary (line 20) and of three output files (lines 16-23).
8. Read the load and the time at the end of the build (line 24).

## Behavior a reader must know

- The scripts of the whole-chip test do not build bwx12. They run a binary with the digest of this build: go.sh and go2.sh stop unless the sha256 digest of the binary equals the value of line 20 [Ref3]. The env.txt files of the nine bwx12 result folders of the whole-chip test hold the same digest [Ref8].
- This file records the build of bwx12 only. Part A of the whole-chip test runs the binaries bw_old and bw_new, not bwx12. The script run_kernels.sh built them on 2026-11-13 with the first seven flags of line 3 [Ref2]. Its three records of that day hold the same two sha256 digests for them [Ref2]. ra.sh, the script of part A, holds the same two digests. It stops if a binary has another digest [Ref9].
- build12.sh stops with a non-zero exit status before it writes line 16 when the compile fails (status 5), when the self-test fails (status 4), or when the branch targets of a timed function of the trial mode fail the check behind lines 7 and 8 (status 6). So a file that has lines 16 to 24 passed these three checks [Ref1].
- The comparisons of lines 11, 13 and 15 are a record only. `DIFFERS` would not stop the build [Ref1].
- Lines 7 to 15 concern mostly the trial mode of bwx12. The bwx12 processes of the whole-chip test use the interval mode, in which the function `worker` times the kernels [Ref4]. No line of this file describes `worker`.
- Insufficient data: whether `worker` reaches the kernels through the copy of `call` whose start address modulo 64 line 9 gives, or through a copy that gcc put inside `worker`. The machine code of `worker` in the binary would resolve it. No saved listing holds it.
- Check made for this page on 2026-11-21 with `sha256sum`: the local copies of bwx12.c, bwx12_selftest.c, build12.sh, listing.txt, offsets.tsv and seq-listing.txt have the digests of lines 17 to 19 and 21 to 23. The binary is not in the folder of bwx12.c or in this folder, so line 20 was not computed again.

## Call sequence in the whole-chip test

- `build12.sh`: on CRB, 2026-11-15: writes this file from top to bottom
  - `gcc`: compiles bwx12.c (lines 2 to 5: version, flags, messages)
  - `bwx12 --selftest`: self-test of the new binary (line 6)
  - `objdump`: machine code of the two timed functions (lines 7 and 8)
  - `build12.sh:placement`: start addresses modulo 64, read with nm (lines 9 to 15)
  - `sha256sum`: digests of seven files (lines 17 to 23)
- `go.sh`: 2026-11-17: holds the digest of line 20, checks the binary
  - `rx.sh`: checks the digest again, writes it to env.txt, starts bwx12
- `go2.sh`: added later: the same digest check, then rx.sh

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Lines 1 to 5: machine, compiler, flags, compiler messages</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  ## host=ubuntu utc=2026-11-15T17:12:11Z load_before=1.18 28.51 31.03 logins=0</pre></td><td valign="top">build12.sh writes this line before it compiles.<ul><li><code>host=ubuntu</code>: the host name that the build machine (CRB) reports.</li><li><code>utc=</code>: the start time, 2026-11-15 at 17:12:11 UTC.</li><li><code>load_before=</code>: the load average of the last 1, 5 and 15 minutes: 1.18, 28.51 and 31.03 tasks.</li><li><code>logins=0</code>: the command <code>who</code> listed no logged-in user.</li></ul>The 5-minute and 15-minute values are far above the 1-minute value. So other work had loaded the machine some minutes before the build.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 2  ## cc=gcc (Ubuntu 14.2.0-4ubuntu2~24.04.1) 14.2.0</pre></td><td valign="top"><code>cc=</code>: the first line that <code>gcc --version</code> printed. The compiler is gcc 14.2.0. The build of bw_old and bw_new on 2026-11-13 recorded the same version line [Ref2].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 3  ## CFLAGS=-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4</pre></td><td valign="top">The flags of the compile command. The first seven are the flags of the bw_old and bw_new build [Ref2]. That build does not have the last three. The build scripts of the runner programs bwx, bwx8, bwx10, bwx11 and bwx12 hold the same ten flags [Ref1].<ul><li><code>-O3</code>: optimisation level 3 of gcc.</li><li><code>-march=native</code>: gcc may use every instruction of the CPU that it runs on (here a CPU of CRB).</li><li><code>-fno-tree-loop-distribute-patterns</code>: gcc does not replace a loop by a call of a library function such as <code>memset</code>.</li><li><code>-pthread -Wall -Wextra -std=gnu11</code>: thread support, the usual and the extra warnings, the C language of 2011 with GNU extensions.</li><li><code>-fno-ipa-icf</code>: gcc does not merge two functions that have the same code. bwx12.c holds some kernels twice under two names [Ref4].</li><li><code>-fno-toplevel-reorder -falign-functions=4</code>: gcc keeps the functions in the order of the source file and aligns a function start to 4 bytes only. bwx12.c needs both to put each kernel at a chosen address modulo 64 [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 4  ## compiler messages:
 5  ## compiler messages end</pre></td><td valign="top">build12.sh appends every message of gcc (warnings and errors) between these two lines. Nothing stands between them: gcc printed no message.</td></tr>
<tr><td colspan="2"><b>Line 6: self-test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 6  ## selftest bwx12 exit=0 # failures=0</pre></td><td valign="top">build12.sh ran <code>bwx12 --selftest</code> and saved the output in selftest-bwx12.txt.<ul><li><code>exit=0</code>: the exit status of that run. The self-test returns 0 when no check failed [Ref7].</li><li><code># failures=0</code>: the last line of the saved output, copied here.</li></ul>The saved output holds 457 check rows, and each one ends with <code>pass</code> [Ref6]. 422 of them check what a kernel reads, writes or returns. The other 35 check the trial mode and the table of kernels in bwx12.c. No check concerns a rate.</td></tr>
<tr><td colspan="2"><b>Lines 7 and 8: calls inside the timed functions (trial mode)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 7  ## timed_sequence branch targets: (indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2</pre></td><td valign="top">build12.sh disassembles the function <code>timed_sequence</code>. It counts the branch and call instructions whose target lies outside the function, per target [Ref5].<ul><li><code>(indirect)=4</code>: 4 calls through a register. They are the kernel calls: a kernel is called through a function pointer, and the code has one such call per kernel type (read, old read, write, copy) [Ref4].</li><li><code>clock_gettime=2</code>: 2 calls of the clock read.</li><li><code>tcount=2</code>: 2 instructions that go to <code>tcount</code>, the function that reads the hardware counters.</li><li><code>__stack_chk_fail=1</code>: 1 call of the function that the compiled code calls when its stack guard check fails.</li></ul>Any other target stops the build with exit status 6. The build also stops with status 6 when <code>clock_gettime</code> or the indirect call is missing. <code>timed_sequence</code> belongs to the trial mode. The whole-chip test does not run it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  ## timed_sequence_hot branch targets: (indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2</pre></td><td valign="top">The same count for <code>timed_sequence_hot</code>, the variant of <code>timed_sequence</code> for the option <code>--hot-copy</code> of the trial mode. The targets and the counts equal line 7. The whole-chip test does not run this function.</td></tr>
<tr><td colspan="2"><b>Lines 9 to 15: placement of five functions, modulo 64</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 9  ## placement bwx12 (start modulo 64): call=24 read_smaps=52 tcount=52 timed_sequence=28 timed_sequence_hot=32</pre></td><td valign="top">build12.sh reads the symbol table of the new binary with <code>nm</code>. For five functions it prints the start address modulo 64.<ul><li><code>call=24</code>: the function through which a thread calls a kernel.</li><li><code>read_smaps=52</code>: the function that reads the page state of the buffers from /proc/self/smaps.</li><li><code>tcount=52</code>, <code>timed_sequence=28</code>, <code>timed_sequence_hot=32</code>: functions of the trial mode.</li></ul>In the source of the interval mode, <code>worker</code> calls <code>call</code> inside a timed interval, and <code>main</code> calls <code>read_smaps</code> between two intervals [Ref4].<br>bwx12.c adds unused bytes after its kernels so that these functions start at the same address modulo 64 as in bwx8, bwx10 and bwx11 [Ref4].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">10  ## placement bwx8 (start modulo 64): call=24 read_smaps=52 tcount=52 timed_sequence=28
11  ## placement up to timed_sequence against bwx8: same</pre></td><td valign="top">Line 10: the same values for the accepted binary of bwx8. build12.sh reads that binary with <code>nm</code> and does not run it. bwx8 has no <code>timed_sequence_hot</code>. Line 11: <code>same</code> means that the four values of bwx8 equal the first four values of line 9. A difference would print <code>DIFFERS</code>. It would not stop the build.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">12  ## placement bwx10 (start modulo 64): call=24 read_smaps=52 tcount=52 timed_sequence=28 timed_sequence_hot=32
13  ## placement up to timed_sequence_hot against bwx10: same</pre></td><td valign="top">The same for the accepted binary of bwx10. <code>same</code>: all five values equal line 9.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">14  ## placement bwx11 (start modulo 64): call=24 read_smaps=52 tcount=52 timed_sequence=28 timed_sequence_hot=32
15  ## placement up to timed_sequence_hot against bwx11: same</pre></td><td valign="top">The same for the accepted binary of bwx11. <code>same</code>: all five values equal line 9.</td></tr>
<tr><td colspan="2"><b>Lines 16 to 23: sha256 digests</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">16  ## sha256:</pre></td><td valign="top">The title of the next seven lines. They are the output of <code>sha256sum</code>: the sha256 digest (64 hexadecimal digits), two blanks, the file name.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">17  e3d4442b83d0aabdb8bf68ec62dfeb43d489df1d7c36de82e64e5482a1089127  bwx12.c
18  d27ca7aa8e706ec1e79c10258539e8c48fb8249159c38a15069af755fed8b72e  bwx12_selftest.c
19  8601ca3a4daaffa48438c749d5fa6c3387358ba88bdab89a9e5eef4b0aabf185  build12.sh</pre></td><td valign="top">The three inputs of the build: the C source of bwx12, the self-test source that bwx12.c includes, and the build script.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">20  cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a  bwx12</pre></td><td valign="top">The digest of the binary <code>bwx12</code>. The whole-chip test of 2026-11-17 ran a binary with this digest. go.sh and go2.sh hold the digest and stop before the first run if the binary has another one. rx.sh checks it again when it starts and writes it to env.txt [Ref3].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">21  d796325cfbdeb05b259e79406e21489ec0c58ef69957fdb3a1643ceca4f9692f  listing.txt
22  214a1f50299bdd1bb31db3754a58caba78ee1f237d25f25d0e1dc5fa6451035f  offsets.tsv
23  d350badee260725cfbae1e2eefb610860b5e84351d18d039b7594a14953e9082  seq-listing.txt</pre></td><td valign="top">Three outputs of the build: listing.txt (the machine code of every kernel as text), offsets.tsv (the loop start of every kernel) and seq-listing.txt (the machine code of <code>timed_sequence</code> and <code>timed_sequence_hot</code>).</td></tr>
<tr><td colspan="2"><b>Line 24: end of the build</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">24  ## load_after=1.17 28.05 30.86 utc=2026-11-15T17:12:14Z</pre></td><td valign="top"><code>load_after=</code>: the load average at the end, in the form of line 1. <code>utc=</code>: the end time, 17:12:14 UTC. That is 3 seconds after the time of line 1.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: the script that wrote this file. Line 37 sets the flags. The build scripts of bwx, bwx8, bwx10 and bwx11 (build.sh, build8.sh, build10.sh and build11.sh in the folders bwx-2026-11-13, bwx8-2026-11-14, bwx10-2026-11-15 and bwx11-2026-11-15) hold the same flags line. Lines 39-48 write lines 1 to 5, lines 50-55 write line 6, lines 83-99 write lines 7 and 8 and hold the exit with status 6, lines 107-151 write lines 9 to 15 (the comment on lines 101-106 says that a difference does not stop the build), lines 153-157 write lines 16 to 24.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: lines 2 and 3 hold the compiler version and the flags of the bw_old and bw_new build. Lines 19 and 20 hold the sha256 digests of bw_old and bw_new. Line 19 of run_kernels.sh (folder kernels-2026-11-13) sets these flags, and lines 31-32 of that script build the two binaries. The script wrote two more records on that day: the probe.txt files of the folders kernels-20261113T181210Z and kernels-20261113T183218Z. Their lines 3, 19 and 20 hold the same flags and the same two digests.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: line 13 holds the digest and line 23 checks the binary. go2.sh in the same folder does the same on its lines 10 and 19. rx.sh (folder w120-2026-11-15) checks the digest on line 8 and writes it to env.txt on line 10.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: lines 143-147: the placement of a kernel needs the two flags. Line 253: the four kernel types. Line 459: the flag -fno-ipa-icf keeps both copies of a kernel. Lines 1440-1449: the unused bytes after the kernels, which keep the start of `call` and of the code after it at the same address modulo 64 as in bwx11, bwx10 and bwx8. Lines 1491-1509: `call` holds one kernel call per kernel type. Lines 1632-1735: `worker` calls `call` between the clock read that starts an interval (line 1688) and the clock read that ends it (line 1700 or line 1714). Lines 1967-2093: `tcount`, `timed_sequence`, `timed_sequence_hot`. Lines 2912-2914: only the option --trial starts the trial mode. Line 3111: `main` calls `read_smaps` between two intervals.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/seq-listing.txt`: the machine code that build12.sh counted for lines 7 and 8. Each of the two functions holds 4 `blr` instructions, 2 `bl` to clock_gettime, one `bl` and one `b` to tcount, and one `bl` to __stack_chk_fail.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/selftest-bwx12.txt`: the saved output of the self-test: 852 lines, of which 457 are check rows that end with `pass`: 422 rows that start with a kernel name and 35 rows that start with `trial`. The last line is `# failures=0`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`: lines 709-710 print the failure count and return 1 if it is above 0, else 0.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/results`: the files env.txt of the nine folders w120-T72L1 to L3, w120-T72C1 to C4, w120-T72I1 and I2: the line `binary` holds the digest of line 20.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: the script of part A. Lines 16-20 check the sha256 digests of bw_old and bw_new and end the script with exit status 2 if one differs. Lines 17 and 18 hold the two values. Line 42 runs a binary.
