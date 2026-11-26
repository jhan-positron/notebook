# `probe.c` explained

- Source file: `probe.c` in this folder (C source, 36 lines, 2081 bytes).
- sha256 of the source when this page was built: `81f96b39747fad6e8876a70c764ec0420011f7e02f8ff20faffa5a0e0b82913f`.
- Role in the whole-chip test: Three compile-only candidates for the copy kernel. Not used in the 2026-11-17 rerun.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

probe.c holds three candidate forms of the copy kernel `k_copy` of bandwidth.c, written only to compare their machine code. run_kernels.sh (the script of 2026-11-13) compiled the file without running it, and the rerun of 2026-11-17 does not use it.

<details>
<summary>Words used here</summary>

- **Kernel**: an inner loop of the benchmark that reads, writes or copies memory. It never means the Linux kernel. The operating system kernel is always written "Linux kernel".
- **Copy kernel**: `k_copy` of bandwidth.c: the loop that loads 256 B from a source buffer and stores them to a destination buffer in each loop pass.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Candidate**: one of the three forms of the copy loop in this file.
- **NEON intrinsics**: C functions that map to Arm vector instructions. Here: `vld1q_u64` (load 16 B) and `vst1q_u64` (store 16 B).
- **Barrier**: the empty inline-assembly statement of the macro `BARRIER`.
- **restrict**: a C keyword on a pointer. With it the programmer promises that no other pointer of the function reaches the same memory.
- **ldp, stp, stur**: Arm instructions as they appear in the listing. `ldp` loads two 16-byte vector registers (32 B). `stp` stores two of them (32 B). `stur` stores one (16 B).
- **Word**: one unsigned 64-bit integer (8 bytes). The kernels take the buffer length as a count of words.
- **Loop pass**: one run of the loop body of a kernel. Each kernel of bandwidth.c moves 256 B (32 words) per loop pass.
- **Object file**: the output of the compiler for one source file, before linking. It cannot be run by itself.
- **run_kernels.sh**: the script of 2026-11-13. It built bw_old, bw_new and the self-test, compiled probe.c, printed the machine code of the kernels and ran the self-test. In its mode `all` it then timed the kernels.
- **probe.txt**: a text file that run_kernels.sh wrote into its result folder. It holds the compiler, the flags, the sha256 values, the machine code of the kernels and the exit status of the self-test. During the rerun ra.sh writes another file with the same name into its own result folder. That file holds no machine code.
- **objdump**: the tool that prints the machine code of a binary as text.
- **sha256**: a checksum of a file. Two files with the same sha256 value have the same content.
- **Rerun of 2026-11-17**: the test under review: the 120-thread read test on CRB after the memory speed was lowered. Its scripts are go.sh, go2.sh, ra.sh and rx.sh.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.

</details>

## Main flow

1. Nothing executes this file. It has no `main`, and run_kernels.sh compiles it to the object file probe.o without linking [Ref1].
2. Three macros define the parts of one loop pass: `LOADS` (16 loads, 256 B), `BARRIER` (the empty asm statement) and `STORES` (16 stores, 256 B) (lines 5-17).
3. Three functions build the copy loop from the macros: with the barrier, without it, and without both the barrier and `restrict` (lines 19-36).
4. run_kernels.sh prints the machine code of each function into probe.txt. The reader compares the order of the loads and the stores there [Ref2].

## Behavior a reader must know

- No function of this file runs in any test, and nothing here is timed. Among the scripts and the C sources of the project, only run_kernels.sh names the file: it compiles it and prints the machine code [Ref1].
- The rerun of 2026-11-17 does not use this file. That rerun builds nothing. ra.sh uses the binaries bw_old and bw_new of 2026-11-13. None of the four scripts of the rerun (go.sh, go2.sh, ra.sh, rx.sh) names this file [Ref4].
- The file is about the copy kernel. It holds no read kernel. Its link to the read test is the macro `BARRIER`: the new read kernel `k_read` has the same empty asm statement after its 16 loads [Ref3].
- Result of 2026-11-13 (gcc 14.2.0, flags `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11`), per loop pass of 256 B: in candidate 1 all 8 `ldp` come before the 8 `stp`. Candidate 2 has 8 `ldp`, 7 `stp` and 2 `stur`, and loads and stores alternate. In candidate 3 all 8 `ldp` come before the 8 `stp` [Ref2].
- The instruction sequence of candidate 1 equals that of `k_copy` in bw_new [Ref2].
- Candidates 1 and 2 agree with the comment in bandwidth.c: with the empty asm statement the loads come first, without it loads and stores alternate [Ref3].
- The results folder holds three runs of run_kernels.sh from 2026-11-13. Their three probe.txt files hold the same listing of these three functions [Ref2].
- The probe.c in this folder has the sha256 value that probe.txt records for it (it starts with 81f96b39) [Ref2].
- The bandwidth.c in this folder has the sha256 value that the run of 2026-11-13 18:32:18 UTC recorded for bandwidth.c (it starts with f1985072). The runs of 18:12:10 and 18:12:22 UTC recorded another sha256 value for bandwidth.c (c1406e02) [Ref2]. So the comment and the line numbers of bandwidth.c that this page cites are those of the later text. The binary bw_new had the same sha256 value in the three runs (it starts with fd7c14df), and the three probe.txt files hold the same listing of `k_copy` [Ref2]. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref5]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.

## Call sequence in the whole-chip test

- `run_kernels.sh:build`: Compiles probe.c to probe.o on 2026-11-13. No program calls its functions.

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `copy_barrier` | 20-24 | Candidate 1: per 256 B loop pass 16 loads, the empty asm statement, 16 stores. Same statements as k_copy. Compiled only. | - | no |
| `copy_plain` | 26-30 | Candidate 2: the same loop without the empty asm statement. Compiled only. | - | no |
| `copy_plain_norestrict` | 32-36 | Candidate 3: the same loop without the empty asm statement and without restrict. Compiled only. | - | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header and includes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  /* probe.c - compile-only candidates for k_copy. */
 2  #include &lt;arm_neon.h&gt;
 3  #include &lt;stddef.h&gt;
 4  #include &lt;stdint.h&gt;</pre></td><td valign="top"><ul><li>The file holds three candidate forms of the copy kernel <code>k_copy</code> of bandwidth.c.</li><li>The file is only compiled: run_kernels.sh compiled it to an object file and printed the machine code [Ref1]. The file has no <code>main</code>, and no program calls its functions.</li><li><code>arm_neon.h</code> gives the vector type <code>uint64x2_t</code> and the NEON intrinsics <code>vld1q_u64</code> and <code>vst1q_u64</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>LOADS</code>: 16 vector loads (256 B)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 5  #define LOADS(P) \
 6      uint64x2_t v0 = vld1q_u64(P + 0), v1 = vld1q_u64(P + 2), v2 = vld1q_u64(P + 4), v3 = vld1q_u64(P + 6), \
 7                 v4 = vld1q_u64(P + 8), v5 = vld1q_u64(P + 10), v6 = vld1q_u64(P + 12), v7 = vld1q_u64(P + 14), \
 8                 v8 = vld1q_u64(P + 16), v9 = vld1q_u64(P + 18), v10 = vld1q_u64(P + 20), v11 = vld1q_u64(P + 22), \
 9                 v12 = vld1q_u64(P + 24), v13 = vld1q_u64(P + 26), v14 = vld1q_u64(P + 28), v15 = vld1q_u64(P + 30)</pre></td><td valign="top"><ul><li>Declares 16 variables <code>v0</code> to <code>v15</code>. Each is one <code>uint64x2_t</code>: two 64-bit integers, 16 B.</li><li><code>vld1q_u64(P + k)</code> loads 16 B from the address of word <code>k</code> after <code>P</code>.</li><li>The offsets 0, 2, ..., 30 cover 32 words (256 B) with no gap.</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>BARRIER</code>: an empty asm statement with 16 inputs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">10  #define BARRIER \
11      __asm__ volatile("" : : "w"(v0), "w"(v1), "w"(v2), "w"(v3), "w"(v4), "w"(v5), "w"(v6), "w"(v7), \
12                       "w"(v8), "w"(v9), "w"(v10), "w"(v11), "w"(v12), "w"(v13), "w"(v14), "w"(v15))</pre></td><td valign="top"><ul><li>An inline-assembly statement with an empty instruction text (<code>""</code>). It adds no instruction to the machine code.</li><li>It names <code>v0</code> to <code>v15</code> as inputs. The constraint <code>"w"</code> asks for each value in a vector register.</li><li>So the compiler must have all 16 loaded values in registers at this point [Ref3].</li><li>The statement does not fix the order of the loads and the stores. The comment in bandwidth.c says that gcc may move code across it [Ref3].</li><li><code>volatile</code> tells the compiler that it must not delete the statement.</li><li>The new read kernel <code>k_read</code> of bandwidth.c has the same statement. There it keeps the compiler from deleting the 16 loads [Ref3].</li></ul></td></tr>
<tr><td colspan="2"><b>Macro <code>STORES</code>: 16 vector stores (256 B)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">13  #define STORES(P) \
14      vst1q_u64(P + 0, v0); vst1q_u64(P + 2, v1); vst1q_u64(P + 4, v2); vst1q_u64(P + 6, v3); \
15      vst1q_u64(P + 8, v4); vst1q_u64(P + 10, v5); vst1q_u64(P + 12, v6); vst1q_u64(P + 14, v7); \
16      vst1q_u64(P + 16, v8); vst1q_u64(P + 18, v9); vst1q_u64(P + 20, v10); vst1q_u64(P + 22, v11); \
17      vst1q_u64(P + 24, v12); vst1q_u64(P + 26, v13); vst1q_u64(P + 28, v14); vst1q_u64(P + 30, v15)
18</pre></td><td valign="top"><code>vst1q_u64(P + k, v)</code> stores the 16 B of <code>v</code> at word <code>k</code> after <code>P</code>. The 16 stores write <code>v0</code> to <code>v15</code> to the same offsets that <code>LOADS</code> read from.</td></tr>
<tr><td colspan="2"><b>Candidate 1 <code>copy_barrier</code>: loads, barrier, stores</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">19  /* candidate 1: copy with the barrier between the loads and the stores */
20  void copy_barrier(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
21  {
22      uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
23      do { LOADS(sp); BARRIER; STORES(dp); sp += 32; dp += 32; } while (sp &lt; end);
24  }</pre></td><td valign="top"><ul><li><code>d</code> is the destination, <code>s</code> the source, <code>n</code> the count of 64-bit words. <code>restrict</code> is the promise that the two buffers do not overlap.</li><li>The source text of one loop pass has the 16 loads from <code>sp</code> (256 B), then <code>BARRIER</code>, then the 16 stores to <code>dp</code> (256 B). Then both pointers move by 32 words.</li><li>The loop is <code>do ... while</code>: the body runs before the first test. <code>n</code> must be a multiple of 32 and not zero.</li><li>These are the statements of <code>k_copy</code> in bandwidth.c [Ref3].</li><li>Machine code of 2026-11-13: per loop pass all 8 <code>ldp</code> come before the 8 <code>stp</code>. It is the same instruction sequence as <code>k_copy</code> in bw_new [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Candidate 2 <code>copy_plain</code>: no barrier</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">25  /* candidate 2: copy without the barrier */
26  void copy_plain(uint64_t *restrict d, const uint64_t *restrict s, size_t n)
27  {
28      uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
29      do { LOADS(sp); STORES(dp); sp += 32; dp += 32; } while (sp &lt; end);
30  }</pre></td><td valign="top"><ul><li>The same loop without <code>BARRIER</code>.</li><li>Machine code of 2026-11-13: loads and stores alternate. One loop pass has 8 <code>ldp</code>, 7 <code>stp</code> and 2 <code>stur</code> [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Candidate 3 <code>copy_plain_norestrict</code>: no barrier, no <code>restrict</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">31  /* candidate 3: copy without the barrier and without restrict */
32  void copy_plain_norestrict(uint64_t *d, const uint64_t *s, size_t n)
33  {
34      uint64_t *dp = d; const uint64_t *sp = s; const uint64_t *end = s + n;
35      do { LOADS(sp); STORES(dp); sp += 32; dp += 32; } while (sp &lt; end);
36  }</pre></td><td valign="top"><ul><li>The same loop as candidate 2, but the pointers are not <code>restrict</code>.</li><li>The compiler must then assume that a store to <code>d</code> can change bytes that a later load from <code>s</code> reads. So it cannot move a store to a place before a load.</li><li>Machine code of 2026-11-13: per loop pass all 8 <code>ldp</code> come before the 8 <code>stp</code>, the same order as candidate 1 [Ref2].</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: line 19: the compiler flags. Line 29: the function `build`. Line 34: `build -c` compiles probe.c to probe.o (`-c` = compile, do not link). Lines 45 to 48: objdump prints the machine code of the three functions into probe.txt. No other line names probe.o.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: lines 2 and 3: compiler and flags. Line 15: sha256 value of bandwidth.c (c1406e02). Line 17: sha256 value of probe.c. Line 20: sha256 value of bw_new (fd7c14df). Lines 56 to 79: machine code of `k_copy` in bw_new. Lines 331 to 403: machine code of the three functions of probe.o. The files probe.txt in the folders kernels-20261113T181210Z and kernels-20261113T183218Z hold the same lines for probe.o, the same lines 56 to 79 and the same line 20. Line 15 of the file in kernels-20261113T183218Z holds another value (f1985072).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: lines 175 to 182: the comment on the empty asm statement and on the order of loads and stores that was observed with and without it. Lines 184 to 211: `k_read` with the same statement. Lines 239 to 284: `k_copy`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: lines 3 and 14 to 20 of ra.sh: the rerun builds nothing and checks the sha256 values of bw_old and bw_new. go.sh (same folder) starts ra.sh and rx.sh. go2.sh (same folder) starts rx.sh. rx.sh (in /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15) starts the bwx12 binary. None of the four scripts names selftest or probe.c. Lines 30 to 36 and line 49 of ra.sh: it writes its own file probe.txt (the machine state and three sha256 values, no machine code).
- [Ref5] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
