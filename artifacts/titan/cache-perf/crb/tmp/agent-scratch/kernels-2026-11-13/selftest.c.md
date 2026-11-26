# `selftest.c` explained

- Source file: `selftest.c` in this folder (C source, 163 lines, 6076 bytes).
- sha256 of the source when this page was built: `90456a5661e61d14fa20f6c75c13976fe0904b58e83bcba4182f8456a4d64c28`.
- Role in the whole-chip test: Self-test of the six kernels of bandwidth.c. Not run in the 2026-11-17 rerun.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

selftest.c calls the six kernels of bandwidth.c (the new benchmark source) on small buffers (at most 1 MiB) and checks the memory afterwards. run_kernels.sh (the script of 2026-11-13) built it and ran it before its own timed runs, and it does not run during the rerun of 2026-11-17.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: an inner loop of the benchmark that reads, writes or copies memory. It never means the Linux kernel. The operating system kernel is always written "Linux kernel".
- **C kernels, asm kernels**: the C kernels are `k_read`, `k_write` and `k_copy`, written with NEON intrinsics. The asm kernels are `k_asmread`, `k_asmwrite` and `k_asmcopy`, written as inline assembly. All six are functions of bandwidth.c.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Word**: one unsigned 64-bit integer (8 bytes). The kernels take the buffer length as a count of words.
- **Loop pass**: one run of the loop body of a kernel. Each kernel of bandwidth.c moves 256 B (32 words) per loop pass.
- **Page**: the unit in which the Linux kernel manages memory. One page had 4096 bytes on CRB in this test.
- **Guard page**: a page with the protection `PROT_NONE` (no access allowed), placed directly before or directly after a test buffer. A read or a write of it ends the process with the signal `SIGSEGV`.
- **Salt**: the second argument of `pattern`. The four fill loops of selftest.c use the numbers 1 to 4, so no two fills give a word the same value.
- **ldp**: here "ldp q", the Arm instruction that loads two 16-byte vector registers (32 B).
- **run_kernels.sh**: the script of 2026-11-13. It built bw_old, bw_new and the self-test, compiled probe.c, printed the machine code of the kernels and ran the self-test. In its mode `all` it then timed the kernels.
- **probe.txt**: a text file that run_kernels.sh wrote into its result folder. It holds the compiler, the flags, the sha256 values, the machine code of the kernels and the exit status of the self-test. During the rerun ra.sh writes another file with the same name into its own result folder. That file holds no machine code.
- **objdump**: the tool that prints the machine code of a binary as text.
- **sha256**: a checksum of a file. Two files with the same sha256 value have the same content.
- **Rerun of 2026-11-17**: the test under review: the 120-thread read test on CRB after the memory speed was lowered. Its scripts are go.sh, go2.sh, ra.sh and rx.sh.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.

</details>

## Main flow

1. The compiler copies the text of bandwidth.c into this file. So the test calls the kernels of the benchmark source, not copies of them (lines 15-17).
2. The program takes no arguments and reads no environment variable. `main` makes the output line-buffered, reads the page size and prints the header line (lines 140-148).
3. For 3 buffer sizes (1 page, 3 pages, 1 MiB) `test_size` checks the C kernels, then the asm kernels, each over a whole buffer between two guard pages (lines 149-154).
4. For 2 block positions (page start, page end) `test_block` checks one 256 B loop pass of the C kernels, then of the asm kernels (lines 155-160).
5. `main` prints the number of failed checks and returns exit status 0 (every check passed) or 1 (lines 161-162).

## Behavior a reader must know

- This file times nothing. It reads no clock and prints no rate.
- It does not run during the rerun of 2026-11-17. That rerun builds nothing. ra.sh uses the binaries bw_old and bw_new of 2026-11-13. None of the four scripts of the rerun (go.sh, go2.sh, ra.sh, rx.sh) names this file [Ref5].
- It tests bandwidth.c only. That is the source of bw_new, which holds the new read kernel. It does not test bandwidth.orig.c (the source of bw_old). The old read kernel is therefore not covered [Ref1].
- The runner bwx12 has its own self-test in another file, bwx12_selftest.c [Ref7].
- Limits, from the file header: the test sees memory contents and faults only. A read kernel that loads nothing would pass. The machine code listing in probe.txt is the evidence that `k_read` and `k_asmread` of bw_new load 256 B per loop pass, with 8 `ldp` instructions of 32 B each [Ref3].
- Insufficient data: whether the kernels inside the selftest binary have the same machine code as the kernels inside bw_new. An objdump listing of the selftest binary would resolve it. The selftest binary is not in the local folders. Both binaries are built from the same bandwidth.c with the same flags. They are separate compilations. probe.txt holds listings of the kernels of bw_new and bw_old. It holds no listing of the selftest binary [Ref1] [Ref3].
- Exit status: 0 = every check passed. 1 = at least one check failed. 2 = setup failed (`mmap`, `mprotect`, or a page size that is not a multiple of 256 B).
- A kernel that reads or writes a guard page ends the process with `SIGSEGV`. Then the output has no `# failures=` line, and its last `call,` line names the kernel. The shell reports exit status 139 (128 plus the signal number 11).
- run_kernels.sh ends with exit status 4 when the self-test does not return 0. So it timed no kernel on 2026-11-13 before the self-test had passed [Ref1].
- Result of 2026-11-13: page size 4096 bytes, 30 `call` lines, 36 result lines, all `pass`, last line `# failures=0`. The results folder holds three runs of run_kernels.sh from that day (18:12:10, 18:12:22 and 18:32:18 UTC). The three selftest.txt files (the saved output of the self-test, one file per run) have the same sha256 value [Ref2]. Only the run of 18:12:22 had the mode `all` (the mode with timed runs). The other two had the mode `probe` (build, machine code and self-test, no timed runs) [Ref4].
- The selftest binary had the same sha256 value in the three builds of 2026-11-13 that the results folder records (it starts with 80714eb8). The sha256 value of bandwidth.c differs between the second build (c1406e02) and the third build (f1985072). So that change of bandwidth.c did not change the selftest binary. The bandwidth.c in this folder is the text of the third build. The selftest.c in this folder is the text of these three builds (90456a56) [Ref4].
- The first build also recorded c1406e02 for bandwidth.c. The second build (18:12:22 UTC) is the one with the timed runs. So the self-test that ran before the timed runs was built from a text of bandwidth.c that is not the text in this folder. The binary bw_new also had the same sha256 value in the three builds (it starts with fd7c14df) [Ref4]. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref8]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.

## Call sequence in the whole-chip test

- `main` (line 140): Started by run_kernels.sh on 2026-11-13. Not part of the 2026-11-17 rerun.
  - `test_size` (line 56): 6 calls: 3 buffer sizes, C kernels then asm kernels
    - `guarded` (line 24): 2 calls: buffers a and b between guard pages
    - `pattern` (line 35): fill values and expected values
    - `calling` (line 40): prints the call line before each kernel
    - `bandwidth.c:k_read (or k_asmread)`: reads the whole buffer once
    - `check` (line 45): prints pass or FAIL, counts failures
    - `bandwidth.c:k_write (or k_asmwrite)`: stores v to the whole buffer once
    - `bandwidth.c:k_copy (or k_asmcopy)`: copies buffer a to buffer b once
  - `test_block` (line 104): 4 calls: 2 offsets, C kernels then asm kernels
    - `guarded` (line 24): 2 calls: one page each for a and b
    - `bandwidth.c:k_read (or k_asmread)`: reads 256 B at the offset
    - `bandwidth.c:k_copy (or k_asmcopy)`: copies 256 B at the offset
    - `bandwidth.c:k_write (or k_asmwrite)`: stores v to 256 B at the offset

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `guarded` | 24-33 | Maps a buffer of n words with one no-access page before it and one after it. Exits with status 2 on failure. | - | no |
| `pattern` | 35-38 | Returns the test value of word i for one salt. Different indexes give different values. | - | no |
| `calling` | 40-43 | Prints the line "call,kernel,bytes" before a kernel call. | - | no |
| `check` | 45-50 | Prints one result line with pass or FAIL. Counts a failed check in failures. | - | no |
| `test_size` | 56-100 | Checks one read, one write and one copy kernel over a whole guarded buffer of n words. | `guarded`, `pattern`, `calling`, `check`, `rd = k_read or k_asmread`, `wr = k_write or k_asmwrite`, `cp = k_copy or k_asmcopy` | no |
| `test_block` | 104-138 | Checks one 256 B loop pass of each kernel at a word offset inside one guarded page. | `guarded`, `pattern`, `calling`, `check`, `rd = k_read or k_asmread`, `cp = k_copy or k_asmcopy`, `wr = k_write or k_asmwrite` | no |
| `main` | 140-163 | Sets line buffering, reads the page size, runs test_size for 3 sizes and test_block for 2 offsets. Returns 0 when every check passed. | `test_size`, `test_block` | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File header: what the self-test checks, and its limits</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  /*
  2   * selftest.c - checks what the six kernels of bandwidth.c do to memory.
  3   * It includes bandwidth.c itself, so it tests the code that the benchmark runs.
  4   * Every buffer ends at a page that cannot be read or written (PROT_NONE) and
  5   * starts after one. A kernel that touches a byte within one page before the
  6   * buffer or within one page after it dies with SIGSEGV. The line "call,..."
  7   * printed before each kernel call names the kernel that died.
  8   * Exit status 0 means every check passed.
  9   *
 10   * Limits. The test sees only memory contents and faults. It cannot see
 11   * whether a read kernel loads every byte, or in which order a copy kernel
 12   * loads and stores: the objdump listing is the evidence for those. It does
 13   * not check that a kernel preserves the callee-saved registers d8-d15.
 14   */</pre></td><td valign="top"><ul><li>The comment states the method. Each kernel runs on a buffer that lies between two pages with no access rights (guard pages). The program compares the memory afterwards.</li><li><code>PROT_NONE</code> is the protection value that forbids every access to a page. <code>SIGSEGV</code> is the signal that the Linux kernel sends to a process on a forbidden memory access. It ends the process.</li><li>The limits matter for the review. The test cannot show that a read kernel loads all the bytes of its buffer. The machine code listing is the evidence for that [Ref3].</li><li>Callee-saved registers are registers that a function must restore before it returns. The test does not check them.</li></ul></td></tr>
<tr><td colspan="2"><b>Include the benchmark source itself</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 15  #define main bandwidth_main
 16  #include "bandwidth.c"
 17  #undef main
 18</pre></td><td valign="top"><ul><li><code>#include "bandwidth.c"</code> copies the whole text of bandwidth.c into this file. The compiler looks for it in the folder of selftest.c first. That file is the new benchmark source, the one that bw_new is built from [Ref1].</li><li>The six kernels are <code>static</code> functions of bandwidth.c. The include makes them callable from this file.</li><li>The <code>#define</code> renames the <code>main</code> function of bandwidth.c to <code>bandwidth_main</code> while the include is read. <code>#undef</code> ends the renaming. Nothing calls <code>bandwidth_main</code>.</li><li>bandwidth.c also includes the system headers that this file needs.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 19  static long page;
 20  static int failures;
 21</pre></td><td valign="top"><code>page</code> holds the page size in bytes. <code>main</code> sets it (line 143). <code>failures</code> counts the checks that failed.</td></tr>
<tr><td colspan="2"><b>Function <code>guarded</code>: a buffer between two guard pages</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 22  /* n words whose first byte follows a PROT_NONE page and whose last byte
 23   * precedes one. n * 8 must be a multiple of the page size. */
 24  static uint64_t *guarded(size_t n)
 25  {
 26      size_t len = n * 8;
 27      uint8_t *raw = mmap(NULL, len + 2 * (size_t)page, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
 28      if (raw == MAP_FAILED || mprotect(raw + page, len, PROT_READ | PROT_WRITE) != 0) {
 29          perror("guarded");
 30          exit(2);
 31      }
 32      return (uint64_t *)(raw + page);
 33  }
 34</pre></td><td valign="top"><ul><li><code>mmap</code> reserves <code>len</code> bytes plus two pages. <code>PROT_NONE</code> forbids every access to all of it. <code>MAP_PRIVATE | MAP_ANONYMOUS</code> means memory of this process only. It is not the content of a file.</li><li><code>mprotect</code> then allows reads and writes for the <code>len</code> bytes that start one page after the start of the mapping. The page before them and the page after them stay forbidden. These are the two guard pages.</li><li>The function returns the address of the first byte after the front guard page.</li><li>If <code>mmap</code> or <code>mprotect</code> fails, the program prints the error and ends with exit status 2.</li><li><code>n * 8</code> must be a multiple of the page size. Then the last byte of the buffer is the last byte before the rear guard page.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pattern</code>: the test value of word <code>i</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 35  static uint64_t pattern(size_t i, uint64_t salt)
 36  {
 37      return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;
 38  }
 39</pre></td><td valign="top"><ul><li>Returns <code>(i + 1)</code> times a fixed 64-bit constant, then XOR (bitwise exclusive or, <code>^</code>) with <code>salt</code>.</li><li>The constant is odd. Two different indexes therefore never give the same value for the same <code>salt</code>.</li><li>The file has four fill loops (lines 63, 84, 111 and 120). They pass the salts 1 to 4. So no two fills give a word the same value.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>calling</code>: the line printed before a kernel call</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 40  static void calling(const char *kernel, size_t n)
 41  {
 42      printf("call,%s,%zu\n", kernel, n * 8);
 43  }
 44</pre></td><td valign="top">Prints <code>call,&lt;kernel name&gt;,&lt;bytes&gt;</code>. <code>n</code> is a count of 8-byte words. <code>n * 8</code> is the byte count. If the kernel call then ends the process with <code>SIGSEGV</code>, this is the last line of the output, and it names the kernel.</td></tr>
<tr><td colspan="2"><b>Function <code>check</code>: one result line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 45  static void check(int ok, const char *kernel, const char *what, size_t n)
 46  {
 47      printf("%s,%s,%zu,%s\n", kernel, what, n * 8, ok ? "pass" : "FAIL");
 48      if (!ok)
 49          failures++;
 50  }
 51</pre></td><td valign="top">Prints one result line: kernel name, name of the check, byte count, then <code>pass</code> or <code>FAIL</code>. A failed check adds 1 to <code>failures</code>. The program continues after a failed check.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 52  typedef void (*read_fn)(const uint64_t *, size_t);
 53  typedef void (*write_fn)(uint64_t *, size_t, uint64_t);
 54  typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);
 55</pre></td><td valign="top">Three types of pointer to a kernel function, one per kind of kernel. A read kernel takes a buffer and a word count. A write kernel also takes the value to store. A copy kernel takes the destination, the source and the word count.</td></tr>
<tr><td colspan="2"><b>Function <code>test_size</code>: read, write and copy over a whole buffer</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 56  static void test_size(size_t n, const char *rn, read_fn rd, const char *wn, write_fn wr, const char *cn, copy_fn cp)
 57  {
 58      uint64_t *a = guarded(n), *b = guarded(n);
 59      int ok;
 60</pre></td><td valign="top"><ul><li><code>n</code> is the buffer size in 8-byte words.</li><li><code>rn</code>, <code>wn</code> and <code>cn</code> are the names that the output shows for the read, write and copy kernel. <code>rd</code>, <code>wr</code> and <code>cp</code> are the kernel functions.</li><li>Line 58 gets two guarded buffers <code>a</code> and <code>b</code> of <code>n</code> words each.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 61      /* read: must leave every word as it was (and must not fault) */
 62      for (size_t i = 0; i &lt; n; i++)
 63          a[i] = pattern(i, 1);
 64      calling(rn, n);
 65      rd(a, n);
 66      ok = 1;
 67      for (size_t i = 0; i &lt; n; i++)
 68          ok &amp;= a[i] == pattern(i, 1);
 69      check(ok, rn, "buffer unchanged", n);
 70</pre></td><td valign="top"><ul><li>Fill <code>a</code> with the pattern of salt 1.</li><li>Print the <code>call</code> line. Then run the read kernel once over the whole buffer.</li><li>Compare every word with the pattern. <code>ok</code> stays 1 only when all <code>n</code> words equal the pattern.</li><li>The buffer fills the space between the two guard pages exactly. A load up to one page before its first byte, or up to one page after its last byte, ends the process.</li><li>The check passes also when the kernel loads nothing. It cannot show that every byte was loaded.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 71      /* write: every word must hold v afterwards; no word may keep the old pattern */
 72      uint64_t v = 0xA5A5F00D12345678ULL + n;
 73      calling(wn, n);
 74      wr(a, n, v);
 75      ok = 1;
 76      for (size_t i = 0; i &lt; n; i++)
 77          ok &amp;= a[i] == v;
 78      check(ok, wn, "every word equals v", n);
 79</pre></td><td valign="top"><ul><li><code>v</code> is the value to store. It depends on <code>n</code>, so each buffer size uses another value.</li><li>Run the write kernel once over the whole buffer <code>a</code>.</li><li>Every word must equal <code>v</code> afterwards. A word that the kernel did not write keeps its old value from the read test, and the check fails.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 80      /* copy: destination must equal source word for word; source unchanged.
 81       * Every word of the source is different, so a store of the wrong vector
 82       * or to the wrong offset is seen. */
 83      for (size_t i = 0; i &lt; n; i++) {
 84          a[i] = pattern(i, 2);
 85          b[i] = 0;
 86      }
 87      calling(cn, n);
 88      cp(b, a, n);
 89      ok = 1;
 90      for (size_t i = 0; i &lt; n; i++)
 91          ok &amp;= b[i] == pattern(i, 2);
 92      check(ok, cn, "destination equals source", n);
 93      ok = 1;
 94      for (size_t i = 0; i &lt; n; i++)
 95          ok &amp;= a[i] == pattern(i, 2);
 96      check(ok, cn, "source unchanged", n);
 97</pre></td><td valign="top"><ul><li>Fill the source <code>a</code> with the pattern of salt 2. Fill the destination <code>b</code> with zeros.</li><li>Run the copy kernel once: <code>cp(b, a, n)</code> copies <code>n</code> words from <code>a</code> to <code>b</code>.</li><li>First check: every word of <code>b</code> equals the pattern. No two words of the source hold the same value. A store of the wrong value or to the wrong offset therefore fails the check.</li><li>Second check: <code>a</code> still holds the pattern.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 98      munmap((uint8_t *)a - page, n * 8 + 2 * (size_t)page);
 99      munmap((uint8_t *)b - page, n * 8 + 2 * (size_t)page);
100  }
101</pre></td><td valign="top">Release both buffers together with their guard pages. Each mapping starts one page before the buffer and is two pages longer than the buffer.</td></tr>
<tr><td colspan="2"><b>Function <code>test_block</code>: one 256 B loop pass inside one page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">102  /* One iteration (256 B = 32 words) at word offset off inside one guarded
103   * page. Words of the page outside the 256 B must keep their old value. */
104  static void test_block(size_t off, const char *rn, read_fn rd, const char *wn, write_fn wr, const char *cn, copy_fn cp)
105  {
106      size_t n = (size_t)page / 8, m = 32;
107      uint64_t *a = guarded(n), *b = guarded(n);
108      int ok;
109</pre></td><td valign="top"><ul><li><code>a</code> and <code>b</code> are guarded buffers of one page each (<code>n</code> words). <code>m</code> is 32 words (256 B). That is the amount that one loop pass of each kernel moves [Ref6].</li><li><code>off</code> is the word offset of the 256 B block inside the page. <code>main</code> passes 0 (block at the page start, directly after the front guard page) and <code>page / 8 - 32</code> (block at the page end, directly before the rear guard page).</li><li>Each kernel is called for exactly these 32 words. A correct kernel runs one loop pass and returns.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">110      for (size_t i = 0; i &lt; n; i++)
111          a[i] = pattern(i, 3);
112      calling(rn, m);
113      rd(a + off, m);
114      ok = 1;
115      for (size_t i = 0; i &lt; n; i++)
116          ok &amp;= a[i] == pattern(i, 3);
117      check(ok, rn, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);
118</pre></td><td valign="top"><ul><li>Fill the page <code>a</code> with the pattern of salt 3.</li><li>Run the read kernel on the 32 words at <code>a + off</code>.</li><li>The whole page must be unchanged.</li><li>Block at the page start: a load before the block reads the front guard page, and the process ends.</li><li>Block at the page end: a load after the block (a second loop pass, for example) reads the rear guard page, and the process ends.</li><li>The text of the check says <code>page start</code> when <code>off</code> is 0, and <code>page end</code> otherwise.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">119      for (size_t i = 0; i &lt; n; i++)
120          b[i] = pattern(i, 4);
121      calling(cn, m);
122      cp(b + off, a + off, m);
123      ok = 1;
124      for (size_t i = 0; i &lt; n; i++)
125          ok &amp;= b[i] == (i &gt;= off &amp;&amp; i &lt; off + m ? pattern(i, 3) : pattern(i, 4));
126      check(ok, cn, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);
127</pre></td><td valign="top"><ul><li>Fill the page <code>b</code> with the pattern of salt 4.</li><li>Run the copy kernel: 32 words from <code>a + off</code> to <code>b + off</code>.</li><li>Expected in <code>b</code>: the 32 words of the block hold the values of <code>a</code> (salt 3). All other words still hold the pattern of salt 4.</li><li>A store next to the block changes one of those other words, or it writes to a guard page.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">128      uint64_t v = 0x0123456789ABCDEFULL;
129      calling(wn, m);
130      wr(a + off, m, v);
131      ok = 1;
132      for (size_t i = 0; i &lt; n; i++)
133          ok &amp;= a[i] == (i &gt;= off &amp;&amp; i &lt; off + m ? v : pattern(i, 3));
134      check(ok, wn, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);
135</pre></td><td valign="top"><ul><li>Run the write kernel: store <code>v</code> to the 32 words at <code>a + off</code>.</li><li>Expected in <code>a</code>: the 32 words of the block equal <code>v</code>. All other words still hold the pattern of salt 3.</li><li>The order in this function is read, copy, write. The copy check (line 125) expects that the source <code>a</code> still holds the pattern of salt 3. The write test changes <code>a</code>, so it runs last.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">136      munmap((uint8_t *)a - page, n * 8 + 2 * (size_t)page);
137      munmap((uint8_t *)b - page, n * 8 + 2 * (size_t)page);
138  }
139</pre></td><td valign="top">Release both pages together with their guard pages.</td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: run all checks and report</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">140  int main(void)
141  {
142      setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */
143      page = sysconf(_SC_PAGESIZE);
144      printf("# selftest: page_bytes=%ld; columns: kernel,check,bytes,result\n", page);
145      if (page % 256 != 0) {
146          fprintf(stderr, "page size is not a multiple of 256\n");
147          return 2;
148      }</pre></td><td valign="top"><ul><li>The program takes no arguments.</li><li><code>setvbuf</code> with <code>_IOLBF</code> makes the standard output line-buffered: each line is written out as soon as it is complete. run_kernels.sh sends the output to a file [Ref1]. Without this call the lines would stay in a memory buffer of the process, and they would be lost when a <code>SIGSEGV</code> ends the process.</li><li><code>sysconf(_SC_PAGESIZE)</code> returns the page size in bytes. It was 4096 bytes on CRB [Ref2].</li><li>Line 144 prints the header line: the page size and the column names of the result lines.</li><li>The kernels move 256 B per loop pass. If the page size is not a multiple of 256 B, the program ends with exit status 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">149      /* whole buffers of 1 page, 3 pages and 1 MiB */
150      size_t words[] = { (size_t)page / 8, 3 * (size_t)page / 8, (1UL &lt;&lt; 20) / 8 };
151      for (size_t i = 0; i &lt; sizeof words / sizeof words[0]; i++) {
152          test_size(words[i], "read", k_read, "write", k_write, "copy", k_copy);
153          test_size(words[i], "asmread", k_asmread, "asmwrite", k_asmwrite, "asmcopy", k_asmcopy);
154      }</pre></td><td valign="top"><ul><li>Three buffer sizes in words: 1 page, 3 pages and 1 MiB. With 4096-byte pages these are 512, 1536 and 131072 words.</li><li>For each size <code>test_size</code> runs twice. The first run tests the C kernels <code>k_read</code>, <code>k_write</code> and <code>k_copy</code>. The second run tests the asm kernels <code>k_asmread</code>, <code>k_asmwrite</code> and <code>k_asmcopy</code>.</li><li>The strings are the names in the output. <code>read</code> is <code>k_read</code>, the new read kernel.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">155      /* one iteration: at the start of a page (guard before it) and at the end (guard after it) */
156      size_t offs[] = { 0, (size_t)page / 8 - 32 };
157      for (size_t i = 0; i &lt; 2; i++) {
158          test_block(offs[i], "read", k_read, "write", k_write, "copy", k_copy);
159          test_block(offs[i], "asmread", k_asmread, "asmwrite", k_asmwrite, "asmcopy", k_asmcopy);
160      }</pre></td><td valign="top"><ul><li>Two word offsets: 0 (page start) and <code>page / 8 - 32</code> (the last 32 words of the page, word 480 with 4096-byte pages).</li><li>For each offset <code>test_block</code> runs twice: C kernels first, then asm kernels.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">161      printf("# failures=%d\n", failures);
162      return failures ? 1 : 0;
163  }</pre></td><td valign="top">Print the number of failed checks. Exit status 0 means that every check passed. Exit status 1 means that at least one check failed. run_kernels.sh stops before its timed runs when the status is not 0 [Ref1].</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: line 19: the compiler flags. Line 29: the function `build` (one gcc call with these flags). Lines 31 to 33: bw_old is built from bandwidth.orig.c, bw_new from bandwidth.c, and the self-test from selftest.c. All three sources lie in the folder of the script. Line 55: the self-test runs with its output sent to selftest.txt, and the script exits with status 4 when it fails. Lines 58 to 79: the timed runs come after it.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/selftest.txt`: output of the self-test of 2026-11-13 18:12:22 UTC, 68 lines. Line 1: `page_bytes=4096`. Line 68: `# failures=0`. The files selftest.txt in the folders kernels-20261113T181210Z and kernels-20261113T183218Z have the same sha256 value.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: line 437: `## selftest exit=0`. Lines 23 to 329: machine code of the six kernels of bw_new and of bw_old. It holds no listing of the selftest binary.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T18*/probe.txt`: line 1 of the three files: the mode (`probe`, `all`, `probe`). Lines 13 to 21 of the three files (181210Z, 181222Z, 183218Z): sha256 values of bandwidth.c, selftest.c, bw_new and the selftest binary at each build.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: lines 3 and 14 to 20 of ra.sh: the rerun builds nothing and checks the sha256 values of bw_old and bw_new. go.sh (same folder) starts ra.sh and rx.sh. go2.sh (same folder) starts rx.sh. rx.sh (in /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15) starts the bwx12 binary. None of the four scripts names selftest or probe.c. Lines 30 to 36 and line 49 of ra.sh: it writes its own file probe.txt (the machine state and three sha256 values, no machine code).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: lines 168 to 173 and 286 to 291: each kernel moves 256 B per loop pass, and the caller must pass a word count `n` for which `n * 8` bytes is a multiple of 256 and not zero. Lines 184 to 376: the six kernels.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`: lines 51 and 155: bwx12 has its own self-test (`bwx12 --selftest`, source bwx12_selftest.c).
- [Ref8] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
