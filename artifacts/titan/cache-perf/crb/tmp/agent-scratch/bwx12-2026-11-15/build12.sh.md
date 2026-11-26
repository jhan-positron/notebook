# `build12.sh` explained

- Source file: `build12.sh` in this folder (Bash script, 160 lines, 8561 bytes).
- sha256 of the source when this page was built: `8601ca3a4daaffa48438c749d5fa6c3387358ba88bdab89a9e5eef4b0aabf185`.
- Role in the whole-chip test: Build script: compiled the runner bwx12 on CRB on 2026-11-15 and recorded the build.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The script compiles `bwx12.c` into the binary `bwx12` with ten fixed compiler flags, tests the binary, and records the build: compiler, flags, checks, the machine code of every kernel, and sha256 values. It ran on CRB on 2026-11-15, and the whole-chip test of 2026-11-17 used the binary that it built.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **CRB build**: the run of this script on CRB on 2026-11-15 that built the binary of the whole-chip test. The folder `crb-build-1` beside the script holds its records, without the binary [Ref1].
- **Whole-chip test**: the run under review: the read test of 2026-11-17 on CRB. "Whole chip" means: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Kernel**: one inner loop of the benchmark. In bwx12.c each kernel is a function with the name `k_<name>`. The CRB build of bwx12 has 55 kernels. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the inner loop of the benchmark that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **bwx8, bwx10**: two more older versions of the runner. bwx12.c is bwx11.c plus additions, bwx11.c is bwx10.c plus additions, and bwx10.c is bwx8.c plus additions [Ref8].
- **Accepted build, accepted binary**: the build on CRB of an older runner version. It serves as the reference for a new build. For bwx11 it is the build in the folder `crb-build-1` of bwx11 [Ref10].
- **Development machine**: the machine on which the check scripts run on the files that come back from CRB. It is not CRB [Ref10].
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **Self-test**: the mode `--selftest` of bwx12. It calls every kernel on small buffers and checks the memory afterwards. It prints one row per check and ends with the line `# failures=N` [Ref9].
- **Interval mode, trial mode**: the two modes of bwx12. Interval mode (option `--seq`): the threads run a sequence of kernels. Each kernel of the sequence gets one timed interval per round (a round is one repeat of the sequence). The whole-chip test uses it. Trial mode (option `--trial`): one pinned thread runs the trials of a plan file. A trial is a series of timed windows. The whole-chip test does not use it [Ref8].
- **Spec file**: a text file with one line per bwx12 process: a tag, the character `|`, and the arguments of the process. The whole-chip test has three, each with one line: `like.spec`, `cfwd.spec` and `crev.spec` [Ref13].
- **`go.sh`, `go2.sh`, `rx.sh`**: scripts of the whole-chip test. `go.sh` and `go2.sh` are the drivers. They call `rx.sh`, which starts one bwx12 process per line of a spec file [Ref11] [Ref12].
- **`worker`**: the function of bwx12.c that each benchmark thread runs in the interval mode. It reads the clock before and after the kernel calls of an interval [Ref8].
- **`timed_sequence`, `timed_sequence_hot`**: the two functions of bwx12.c that time the windows of one trial in the trial mode. `timed_sequence_hot` runs when the option `--hot-copy` is given [Ref8].
- **`tcount`**: a function of bwx12.c for the trial mode. It reads the event counters and the CPU time of the thread at the edge of a window [Ref8].
- **`call`**: the function of bwx12.c that runs one kernel on a byte range of the buffer of a thread [Ref8].
- **`read_smaps`**: the function of bwx12.c that reads the page state of a buffer from the file `/proc/self/smaps` [Ref8].
- **`PLACE`**: a macro of bwx12.c that stands before each kernel. It pads the code to a 64-byte boundary and then adds a set number of bytes. So the kernel starts at a planned address modulo 64 [Ref8].
- **Address modulo 64**: the remainder when the address is divided by 64. It is the offset inside a 64-byte block of code, from 0 to 63 bytes.
- **Loop start**: the address of the first instruction of the loop of a kernel. The script takes the target of the first backward branch of the function.
- **Branch target**: the address that a branch or call instruction goes to.
- **Listing**: machine code printed as assembler text, one instruction per line with its address.
- **objdump**: a tool that prints the machine code of a binary as a listing.
- **nm**: a tool that lists the symbols of a binary (the names of functions and variables) with their addresses.
- **taskset**: a Linux tool that starts a program limited to a list of CPUs.
- **sha256**: a checksum. Two files with the same sha256 have the same content. The value has 64 hexadecimal digits.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg).
- **SVE**: Scalable Vector Extension, a vector instruction set extension of Arm CPUs.
- **Stack-guard failure function**: `__stack_chk_fail`. Check code that the compiler adds to a function calls it when the guard value on the stack was overwritten.

</details>

## Main flow

1. Stop with status 3 if the marker file exists. The same check runs again before each run of the new binary (lines 31-33).
2. Restart the script under `taskset`, limited to CPUs 0 to 119 (line 34).
3. Set the compiler and the ten compiler flags (lines 35-37).
4. Start `build.txt` with host, time, load averages, logins, compiler version and flags (lines 38-45).
5. Compile `bwx12.c` into `bwx12`. Compiler messages go to `build.txt`. A failed compile ends the script with status 5 (lines 46-48).
6. Run `bwx12 --selftest` and save its output in `selftest-bwx12.txt`. A failed self-test ends the script with status 4 (lines 49-55).
7. For each kernel that `bwx12 --list` names: append its machine code to `listing.txt`, and write its start, its loop start and the loop start modulo 64 to `offsets.tsv` (lines 56-75).
8. Save the machine code of `timed_sequence` and `timed_sequence_hot` in `seq-listing.txt`, write their branch targets to `build.txt`, and end with status 6 if a target is not allowed (lines 76-99).
9. Write to `build.txt` where five functions start modulo 64, and whether the accepted binaries of bwx8, bwx10 and bwx11 have the same values (lines 100-151).
10. Append the sha256 values of seven files, the load averages and the end time to `build.txt` (lines 152-157).
11. Print `build.txt` and `offsets.tsv` to the standard output (lines 158-160).

## Behavior a reader must know

- The script does not run during the whole-chip test. The saved record is of one run on CRB on 2026-11-15, from 17:12:11 to 17:12:14 UTC [Ref1]. The folder `crb-build-1` beside the script holds the files of that build. The script times nothing and computes no rate.
- `set -euo pipefail` (line 30) holds for the whole script. The script ends when a command fails, when it uses a variable that was never set, or when one command of a pipeline fails. A command that `if` tests, or that `||` follows, does not end it. Other failures also do not stop the build. Two examples: a failed `bwx12 --list` in the `for` list of line 62, and a failed `nm` inside `placement` (line 109). The row of line 30 gives the rule.
- Records of one build: the binary `bwx12`, `build.txt`, `selftest-bwx12.txt`, `listing.txt`, `offsets.tsv`, `seq-listing.txt`, and the text on the standard output. The rows of lines 38 to 160 explain each record at the line that writes it. The entry [Ref1] says what each of the 24 lines of the CRB `build.txt` holds.
- Link from the test to this build: `build.txt` records the sha256 value `cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a` for the binary [Ref1]. `go.sh` and `go2.sh` hold this value and pass it to `rx.sh`. All three scripts stop when the `bwx12` file has another value [Ref11] [Ref12]. All 9 `env.txt` files of the bwx12 runs of the test record this value [Ref14].
- Link from the build to the local source: the local copies of `bwx12.c`, `bwx12_selftest.c` and `build12.sh` have the sha256 values that `build.txt` records [Ref20]. The binary itself is not under the local folder `crb`.
- Compiler and flags against the binaries of 2026-11-13: the same gcc 14.2.0 built bw_old and bw_new with the first seven flags of line 37. bwx12 has three more flags: `-fno-ipa-icf`, `-fno-toplevel-reorder` and `-falign-functions=4` [Ref15] [Ref16].
- The branch-target check of lines 76 to 99 covers the trial mode only. The whole-chip test ran the interval mode (`--seq` in the spec files). In that mode the function `worker` of bwx12.c reads the clock and calls the kernels [Ref8] [Ref13]. The build record holds the machine code of the kernels, not of `worker`. Insufficient data: whether gcc inlined the function `call` into `worker`. The output of `objdump -d --disassemble=worker` on the binary would resolve it. The symbol `call` in the placement line of `build.txt` does not resolve it [Ref21].
- This script does not compare the kernel code with an accepted build. `check_listing12.py` does that afterwards on the development machine [Ref10]. Its saved output for the CRB build reports 0 failed rows for the 29 kernels of bwx11 and 0 failed rows for the 26 new kernels. Of the six kernels of the whole-chip test, `oldread`, `read`, `asmread`, `read_nop96` and `read_1pl` have the same function text as in the accepted bwx11 build, apart from addresses. `read_nop256` is a new kernel, and its loop has the expected instructions [Ref7].
- `build.txt` is written in steps. The sha256 block (lines 154 and 155) and the `load_after` line (line 156) come last. A `build.txt` of this script without the `## sha256:` block belongs to a build that stopped early.
- Six environment variables change a run: `BWX_MARKER` (path of the marker file), `BWX_CPUS` (CPU list), `CC` (compiler), and `BWX8_BIN`, `BWX10_BIN`, `BWX11_BIN` (paths of the older binaries). The script also reads `_PINNED` (line 34). It sets this variable itself for the restart under `taskset`. If the variable is already set and not empty at the start, the script does not restart, and it sets no CPU limit.

## Call sequence in the whole-chip test

- `build12.sh` (line 30): ran on CRB on 2026-11-15, not during the whole-chip test
  - `check_marker` (line 32): called on lines 33, 50 and 61: status 3 if the marker file exists
  - `taskset` (line 34): restarts this script limited to CPUs 0 to 119
  - `gcc` (line 47): compiles bwx12.c, which includes bwx12_selftest.c, into the binary bwx12
  - `bwx12 --selftest` (line 51): first run of the new binary, output to selftest-bwx12.txt
    - `bwx12.c:main`: finds the option and calls the self-test
      - `bwx12_selftest.c:selftest`: calls all 55 kernels on small buffers and checks the memory
        - `bwx12.c:call`: runs one kernel, the same function as in the benchmark
          - `bwx12.c:k_oldread, k_read, k_asmread, k_read_nop96, k_read_nop256, k_read_1pl`: the six kernels of the whole-chip test, among the 55
  - `bwx12 --list` (line 62): prints the 55 kernel names for the loop
  - `objdump` (line 64): once per kernel: machine code of the kernel function for listing.txt
  - `objdump` (line 86): machine code of the two timed functions of the trial mode
  - `placement` (line 107): called on lines 114, 117, 130 and 142, each with one binary
    - `nm` (line 109): lists the symbols and addresses of that binary
  - `sha256sum` (line 155): checksums of seven files for build.txt

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 32-32 | Ends the script with status 3 when the marker file exists. | - | - |
| `placement` | 107-112 | Prints `name=value` pairs: the start address modulo 64 of five functions of the given binary, read with `nm`. | `nm`, `awk`, `sort` | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header comment: what the script does</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  1  #!/usr/bin/env bash
  2  # build12.sh - on CRB: build bwx12, run its self-test, print the digests, and
  3  # save the machine code of every kernel (design tackle-8mb.md, "Fixed setup":
  4  # a build whose listing differs from the accepted one is rejected).
  5  # It is build11.sh for bwx12.c, with the same checks, and one addition:
  6  # build.txt also holds the placement of the timed path in the accepted bwx11
  7  # and says whether bwx12 has the same placement.
  8  # (build11.sh is build10.sh with the same addition for the accepted bwx10.)
  9  # (build10.sh is build8.sh with three additions: the branch-target check
 10  # covers timed_sequence_hot() too, the machine code of both timed functions is
 11  # saved in seq-listing.txt, and build.txt holds the placement of the timed
 12  # path in the new binary and in the accepted bwx8.)</pre></td><td valign="top"><ul><li>Line 1 makes <code>bash</code> the interpreter.</li><li>The script runs on CRB (the Arm reference server under test). It builds the binary <code>bwx12</code>, runs the self-test of the binary, prints checksums, and saves the machine code of every kernel. A kernel is one inner loop of the benchmark.</li><li>The comment names three earlier versions of this script: <code>build8.sh</code>, <code>build10.sh</code> and <code>build11.sh</code>. Each version keeps the checks of the version before and adds to them.</li><li>This script does not apply the rule of line 4 (a build whose listing differs from the accepted one is rejected). The script that line 22 names applies it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 13  # Usage: build12.sh
 14  # The compiler flags are the flags of build8.sh. There is no EXTRA.
 15  # Output, all in the folder of this script (on CRB: ~/cache-perf/bwx12-20261115/):
 16  #   bwx12                the binary
 17  #   build.txt            host, load, compiler, flags, compiler messages, sha256
 18  #   selftest-bwx12.txt   output of "bwx12 --selftest"
 19  #   listing.txt          "=== bwx12 &lt;kernel&gt; ===" and the objdump text of function k_&lt;kernel&gt;
 20  #   offsets.tsv          binary, kernel, function, start, loop_start, loop_mod64 (addresses in hex)
 21  #   seq-listing.txt      the objdump text of timed_sequence and timed_sequence_hot (for reading; no script uses it)
 22  # Then, on the development machine: check_listing12.py listing.txt offsets.tsv</pre></td><td valign="top"><ul><li>The script takes no argument. Lines 16 to 21 list the six files that it writes into its own folder. The rows below explain each file at the line that writes it.</li><li><code>EXTRA</code> (line 14) was a variable for more compiler flags in the build script of the older runner version bwx [Ref19]. This script has no such variable, so the flags of line 37 are the only flags.</li><li>Line 22 names the step after the build. On the development machine, <code>check_listing12.py</code> compares <code>listing.txt</code> and <code>offsets.tsv</code> with the accepted build of bwx11 (the runner version before bwx12) [Ref10].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 23  # Exit status: 0 done; 3 marker file present; 4 the self-test failed; 5 the build failed;
 24  #   6 a timed sequence of the trial mode reaches a function that is not allowed there.
 25  # Writes only in its own folder. No sudo. Runs on CPUs 0-119 only (BWX_CPUS changes the list).</pre></td><td valign="top">Each exit status belongs to one check: 3 to <code>check_marker</code> (line 32), 5 to the compiler call (line 47), 4 to the self-test (line 54), 6 to the branch-target check (line 99). Status 0 means that every step ran.<br>Another failed command can also end the script (rule <code>-e</code> of line 30, with the exceptions named there). The exit status is then the status of that command.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 26  # It reads three files outside its folder, if they exist: the accepted binaries
 27  # of bwx8 (BWX8_BIN, default ../bwx8-20261114/bwx8), of bwx10 (BWX10_BIN,
 28  # default ../bwx10-20261115/bwx10) and of bwx11 (BWX11_BIN, default
 29  # ../bwx11-20261115/bwx11), with nm only. It does not run them.</pre></td><td valign="top">The script reads three binaries of older runner versions (bwx8, bwx10, bwx11) with the tool <code>nm</code>, and does not run them. <code>nm</code> lists the symbols of a binary with their addresses. Three environment variables replace the default paths. A missing file does not stop the script (lines 125 to 127, 137 to 139 and 149 to 151).</td></tr>
<tr><td colspan="2"><b>Shell options</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 30  set -euo pipefail</pre></td><td valign="top"><code>set -euo pipefail</code> sets three rules for the whole script:<ul><li><code>-e</code>: the script ends when a command fails. A command that <code>if</code> tests, or that <code>||</code> follows, does not end it. The form <code>$( )</code> runs commands and inserts their output. A failed command inside <code>$( )</code> ends the script only when the <code>$( )</code> is the whole right side of an assignment (line 64). It does not end the script when the <code>$( )</code> stands inside an <code>echo</code> text (line 41) or a <code>for</code> list (line 62). Bash also turns <code>-e</code> off inside <code>$( )</code>, and every call of <code>placement</code> stands inside <code>$( )</code>. So a failed <code>nm</code> (line 109) does not end the script.</li><li><code>-u</code>: the script ends when it uses a variable that was never set.</li><li><code>-o pipefail</code>: a pipeline counts as failed when any of its commands fails, not only the last one.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>check_marker</code>: stop when the marker file exists</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 31  MARKER=${BWX_MARKER:-/tmp/positron-perf.RUNNING}   # BWX_MARKER: only for a test of this check
 32  check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" &gt;&amp;2; exit 3; fi; }
 33  check_marker</pre></td><td valign="top"><ul><li><code>MARKER</code> is the path of the marker file, by default <code>/tmp/positron-perf.RUNNING</code>. Another user creates this file during a performance test [Ref18]. The environment variable <code>BWX_MARKER</code> replaces the path (for a test of this check).</li><li><code>check_marker</code> tests whether the file exists (<code>-e</code>). If it exists, the function prints a message to the error output (<code>&gt;&amp;2</code>) and ends the script with status 3.</li><li>Line 33 is the first call. Line 50 and line 61 call it again, each time before the script runs the new binary.</li></ul></td></tr>
<tr><td colspan="2"><b>CPU limit: the script restarts itself under <code>taskset</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 34  if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c "${BWX_CPUS:-0-119}" "$0" "$@"; fi</pre></td><td valign="top"><ul><li>On the first pass the variable <code>_PINNED</code> is empty, so the <code>if</code> branch runs.</li><li><code>exec</code> replaces the shell with <code>taskset</code>, and <code>taskset</code> starts this script again (<code>$0</code>) with the same arguments (<code>$@</code>).</li><li><code>taskset -c 0-119</code> limits a program to CPUs 0 to 119. bwx12.c names this range as the rule of the test machine [Ref8].</li><li><code>_PINNED=1</code> goes into the environment of the new run. So the second pass skips the <code>if</code> branch and continues with line 35.</li><li>Every program that the script starts later inherits the limit: the compiler, the new binary, <code>objdump</code> and <code>nm</code>.</li><li>The environment variable <code>BWX_CPUS</code> replaces the list <code>0-119</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 35  SRC=$(cd "$(dirname "$0")" &amp;&amp; pwd)
 36  CC=${CC:-gcc}</pre></td><td valign="top"><code>SRC</code> is the absolute path of the folder that holds this script: <code>cd</code> goes to the folder of <code>$0</code>, and <code>pwd</code> prints it. <code>CC</code> is the compiler: the environment variable <code>CC</code> if it is set and not empty, otherwise <code>gcc</code>. The CRB build used gcc 14.2.0 [Ref1].</td></tr>
<tr><td colspan="2"><b>Compiler flags, one by one</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 37  CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4"</pre></td><td valign="top">The same gcc 14.2.0 built bw_old and bw_new (the two binaries of the benchmark of 2026-11-13) with the first seven flags. The last three flags were not used for bw_old and bw_new [Ref15] [Ref16].<ul><li><code>-O3</code>: the highest numbered optimization level of gcc. The compiler may inline functions and vectorize loops [Ref17]. In the CRB build the 16 sums of the old read kernel are 8 vector adds per loop pass of <code>k_oldread</code> [Ref3].</li><li><code>-march=native</code>: gcc picks the architecture of the machine on which the build runs. The architecture decides which instructions the compiler may use [Ref22]. The build ran on CRB. Example: the machine code of <code>timed_sequence</code> holds SVE instructions (SVE is a vector extension of Arm) [Ref4]. The flag names no processor to tune for, and line 37 holds no <code>-mtune</code> and no <code>-mcpu</code>. For that case the gcc manual says that the code is tuned to perform well on a range of processors of that architecture [Ref22].</li><li><code>-fno-tree-loop-distribute-patterns</code>: gcc does not turn a loop pattern into a call of a library function [Ref17]. A store loop that becomes a call of <code>memset</code> is such a pattern. In the CRB build <code>k_oldwrite</code> and <code>k_oldcopy</code> are loops, and no kernel calls a library function for its work [Ref3].</li><li><code>-pthread</code>: compile and link with support for POSIX threads. bwx12 runs its benchmark threads as POSIX threads [Ref8].</li><li><code>-Wall -Wextra</code>: turn on most warnings of the compiler, and some more [Ref17]. A warning does not stop the build. It is written into <code>build.txt</code> (line 47). The CRB build has none [Ref1].</li><li><code>-std=gnu11</code>: the source is compiled as C of the 2011 standard with the GNU extensions [Ref17].</li><li><code>-fno-ipa-icf</code>: gcc does not merge two functions that have identical code [Ref17]. bwx12.c holds kernels that are one source under two names, for example <code>oldread</code> and <code>oldread2</code>. With this flag gcc keeps both [Ref8].</li><li><code>-fno-toplevel-reorder</code>: gcc writes the functions and the top-level <code>asm</code> statements into the binary in the order of the source file [Ref17]. bwx12.c needs this for its macro <code>PLACE</code>, which puts padding bytes directly before a kernel [Ref8].</li><li><code>-falign-functions=4</code>: gcc aligns the start of a function to 4 bytes only. Then a kernel starts directly after the pad of <code>PLACE</code>, at the planned address modulo 64 [Ref8].</li></ul></td></tr>
<tr><td colspan="2"><b>Record <code>build.txt</code>: the first four lines</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 38  b=bwx12
 39  B="$SRC/build.txt"
 40  {
 41    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who | wc -l)"
 42    echo "## cc=$($CC --version | head -1)"
 43    echo "## CFLAGS=$CFLAGS"
 44    echo "## compiler messages:"
 45  } &gt; "$B"</pre></td><td valign="top"><code>b</code> is the name of the binary. <code>B</code> is the path of <code>build.txt</code>. The block writes four lines and replaces an older <code>build.txt</code> (<code>&gt;</code>):<ul><li><code>## host=... utc=... load_before=... logins=...</code>: the host name, the UTC time at the start, the load averages of the last 1, 5 and 15 minutes (fields 1 to 3 of <code>/proc/loadavg</code>), and the number of lines that <code>who</code> prints (one line per login session).</li><li><code>## cc=...</code>: the first line of the version text of the compiler.</li><li><code>## CFLAGS=...</code>: the flags of line 37.</li><li><code>## compiler messages:</code>: a title for the text that the compiler prints next.</li><li>CRB build: host <code>ubuntu</code>, start at 17:12:11 UTC on 2026-11-15, load averages 1.18, 28.51 and 31.03 tasks (1, 5 and 15 minutes), 0 logins [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Compile <code>bwx12.c</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 46  # shellcheck disable=SC2086
 47  $CC $CFLAGS -o "$SRC/$b" "$SRC/bwx12.c" &gt;&gt; "$B" 2&gt;&amp;1 || { echo "build of $b failed: $B" &gt;&amp;2; cat "$B" &gt;&amp;2; exit 5; }
 48  echo "## compiler messages end" &gt;&gt; "$B"</pre></td><td valign="top"><ul><li>The compiler builds <code>bwx12.c</code> into the binary <code>bwx12</code> in the folder of the script. <code>bwx12.c</code> includes <code>bwx12_selftest.c</code> with <code>#include</code>, so one compiler call is enough [Ref8].</li><li><code>$CFLAGS</code> has no quotes on purpose: the shell must split it into single flags. Line 46 tells the checking tool shellcheck not to warn about that.</li><li><code>&gt;&gt; "$B" 2&gt;&amp;1</code> appends every message of the compiler to <code>build.txt</code>.</li><li>If the compiler fails, the part after <code>||</code> prints <code>build.txt</code> to the error output and ends the script with status 5.</li><li>Line 48 appends the line <code>## compiler messages end</code>.</li><li>CRB build: nothing stands between the two <code>compiler messages</code> lines, so the compiler printed no warning [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Self-test of the new binary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 49
 50  check_marker
 51  if "$SRC/$b" --selftest &gt; "$SRC/selftest-$b.txt" 2&gt;&amp;1; then
 52    echo "## selftest $b exit=0 $(tail -1 "$SRC/selftest-$b.txt")" &gt;&gt; "$B"
 53  else
 54    echo "## selftest $b exit=$?" &gt;&gt; "$B"; echo "selftest of $b failed: $SRC/selftest-$b.txt" &gt;&amp;2; tail -3 "$SRC/selftest-$b.txt" &gt;&amp;2; exit 4
 55  fi</pre></td><td valign="top"><ul><li>Line 50 checks the marker file again. Line 51 is the first run of the new binary.</li><li><code>bwx12 --selftest</code> runs the self-test. Its whole output goes to <code>selftest-bwx12.txt</code> (<code>2&gt;&amp;1</code> adds the error output).</li><li>The self-test calls each of the 55 kernels on buffers of 1 page, 3 pages and 1 MiB, and on single blocks of 256 B. Before each of these calls it prints a line that begins with <code>call,</code>. After each call it checks the memory. Then it tests the trial mode. Each check prints one row that ends with <code>pass</code> or <code>FAIL</code> [Ref9].</li><li>Limit: for a read kernel that returns nothing, the self-test shows that the buffer is unchanged and that the kernel touches every page of a 3-page range. It does not show that the kernel reads every byte [Ref9]. In the CRB build the rows of <code>read</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code> and <code>read_1pl</code> hold these two kinds of check only. The rows of <code>oldread</code> also hold the check that the returned sum equals the sum of all words [Ref5].</li><li>Exit status 0: the script appends <code>## selftest bwx12 exit=0</code> plus the last line of the self-test output to <code>build.txt</code>. CRB build: <code># failures=0</code>, and 457 rows end with <code>pass</code> [Ref1] [Ref5].</li><li>Any other status: the script appends <code>## selftest bwx12 exit=N</code> (N is the status), prints the last 3 lines of the output to the error output, and ends with status 4.</li></ul></td></tr>
<tr><td colspan="2"><b>Records <code>listing.txt</code> and <code>offsets.tsv</code>: machine code of every kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 56
 57  # Machine code of every kernel. The loop start is the target of the first
 58  # branch of the function that goes backward to an address inside it.
 59  : &gt; "$SRC/listing.txt"
 60  printf 'binary\tkernel\tfunction\tstart\tloop_start\tloop_mod64\n' &gt; "$SRC/offsets.tsv"
 61  check_marker   # the next line runs the binary again</pre></td><td valign="top">Line 59 empties <code>listing.txt</code>: the command <code>:</code> does nothing, and <code>&gt;</code> creates the file or makes it empty (0 bytes). Line 60 writes the header line of <code>offsets.tsv</code>: six column names with tabs between them. Line 62 runs the binary once more. So line 61 checks the marker file again before it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 62  for k in $("$SRC/$b" --list); do
 63    fn=k_$k
 64    text=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b" | sed -n '/&gt;:$/,/^$/p')
 65    { echo "=== $b $k ==="; echo "$text"; echo; } &gt;&gt; "$SRC/listing.txt"</pre></td><td valign="top"><ul><li><code>bwx12 --list</code> prints the names of all kernels, one per line (55 in the CRB build [Ref2]). The loop runs once per name <code>k</code>. <code>fn</code> is the function of the kernel: <code>k_</code> plus the name.</li><li>A failed <code>--list</code> run does not end the script (see the row of line 30). The loop then runs over the names that the binary printed before it failed. In the CRB build the loop got every name. The first line of the self-test output gives <code>kernels=55</code>. <code>offsets.tsv</code> has 55 kernel rows [Ref2] [Ref5].</li><li><code>objdump -d --disassemble=$fn</code> prints the machine code of this one function as assembler text. It stops at the end of the function. <code>--no-show-raw-insn</code> leaves out the bytes of each instruction.</li><li><code>sed -n '/&gt;:$/,/^$/p'</code> keeps the lines from the label line of the function (it ends with <code>&gt;:</code>) to the next empty line. This drops the header that <code>objdump</code> prints first.</li><li>Line 65 appends three things to <code>listing.txt</code>: the title line <code>=== bwx12 &lt;kernel&gt; ===</code>, the text of the function, and an empty line.</li><li>The listing holds the six kernels of the whole-chip test: <code>oldread</code>, <code>read</code>, <code>asmread</code>, <code>read_nop96</code>, <code>read_nop256</code> and <code>read_1pl</code> [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 66    start=$(sed -n '1s/^0*\([0-9a-f]\+\) .*/\1/p' &lt;&lt;&lt; "$text"); loop=NA; mod=NA
 67    while read -r addr rest; do
 68      addr=${addr%:}
 69      if [[ $rest =~ ([0-9a-f]+)\ \&lt;$fn(\+0x[0-9a-f]+)?\&gt; ]]; then
 70        tgt=${BASH_REMATCH[1]}
 71        if (( 16#$tgt &lt; 16#$addr &amp;&amp; 16#$tgt &gt;= 16#$start )); then loop=$tgt; mod=$(( 16#$tgt % 64 )); break; fi
 72      fi
 73    done &lt; &lt;(tail -n +2 &lt;&lt;&lt; "$text" | grep -E '^ *[0-9a-f]+:')</pre></td><td valign="top">These lines find the start of the function and the start of its loop.<ul><li>Line 66: <code>start</code> is the address on the label line (line 1 of the text), without leading zeros. <code>loop</code> and <code>mod</code> begin as <code>NA</code>.</li><li>Line 73 gives the instruction lines to the <code>while</code> loop as input: every line after the first that begins with a hexadecimal address and a colon. <code>read</code> puts the address into <code>addr</code> and the rest of the line into <code>rest</code>. Line 68 removes the colon.</li><li>Line 69 looks for a branch to a place inside the same function. <code>objdump</code> prints such a target as an address and a name, for example <code>49a4 &lt;k_read+0x4&gt;</code>. <code>tgt</code> is that address.</li><li>Line 71 compares the addresses as hexadecimal numbers (<code>16#</code>). The branch goes backward when the target is lower than the address of the branch instruction and not lower than <code>start</code>. Then <code>loop</code> is the target, <code>mod</code> is the target modulo 64 as a decimal number, and <code>break</code> ends the search.</li><li>So the loop start is the target of the first backward branch. If a function had two loops, only the first would be recorded. In the CRB build each of the 55 kernel functions holds exactly one backward branch to an address inside the function [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 74    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$b" "$k" "$fn" "$start" "$loop" "$mod" &gt;&gt; "$SRC/offsets.tsv"
 75  done</pre></td><td valign="top">Line 74 appends one row per kernel to <code>offsets.tsv</code>, with tabs between the six fields:<ul><li><code>binary</code>: always <code>bwx12</code>. <code>kernel</code>: the kernel name. <code>function</code>: <code>k_</code> plus that name.</li><li><code>start</code>: the address of the first instruction of the function, hexadecimal.</li><li><code>loop_start</code>: the address of the first instruction of the loop, hexadecimal. It is <code>NA</code> when the function has no backward branch.</li><li><code>loop_mod64</code>: <code>loop_start</code> modulo 64, a decimal number of bytes from 0 to 63. It is the offset of the loop start inside a 64-byte block of code.</li><li>CRB build: <code>oldread</code> has <code>start</code> 4600, <code>loop_start</code> 4668 (both hexadecimal) and <code>loop_mod64</code> 40 bytes. <code>read</code> has 49a0, 49a4 and 36 bytes. <code>asmread</code> has 4ac0, 4ad4 and 20 bytes. No row holds <code>NA</code> [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Check with exit status 6: branch targets of the trial-mode timed functions</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 76
 77  # Branch targets of timed_sequence() and of timed_sequence_hot() that lie
 78  # outside the function (design, Stage 1 item 4: no warm-up, page read, output
 79  # or barrier can enter the timed path). Allowed: clock_gettime, the kernels
 80  # (an indirect call), tcount (the counter read of count "read") and the
 81  # stack-guard failure. A helper that is not inlined shows as its own name and
 82  # is rejected. Both functions are listed before the script decides.
 83  : &gt; "$SRC/seq-listing.txt"
 84  seq_fail=0</pre></td><td valign="top"><ul><li>The comment gives the rule. <code>timed_sequence</code> and <code>timed_sequence_hot</code> may branch only to four places: <code>clock_gettime</code> (the clock read), a kernel (through a function pointer), <code>tcount</code> (a function of bwx12.c that reads the event counters), and the stack-guard failure function.</li><li>Both functions belong to the trial mode of bwx12 (option <code>--trial</code>). They time the windows of a trial [Ref8].</li><li>The whole-chip test does not use the trial mode. Its spec files start bwx12 with <code>--seq</code>. Then the function <code>worker</code> of bwx12.c times each interval [Ref8] [Ref13].</li><li>So this check does not cover the timed path of the whole-chip test. This script does not save the machine code of <code>worker</code>.</li><li>Line 83 empties <code>seq-listing.txt</code>. <code>seq_fail=0</code> means that no function has failed yet.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 85  for fn in timed_sequence timed_sequence_hot; do
 86    code=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b")
 87    { echo "=== $b $fn ==="; sed -n '/&gt;:$/,/^$/p' &lt;&lt;&lt; "$code"; echo; } &gt;&gt; "$SRC/seq-listing.txt"</pre></td><td valign="top">The loop runs once for each of the two functions. Line 86 stores the whole <code>objdump</code> output for the function in <code>code</code>. Line 87 appends to <code>seq-listing.txt</code> the title line <code>=== bwx12 &lt;function&gt; ===</code>, the text of the function (label line to the next empty line) and an empty line. Apart from the checksum of line 155, no script reads <code>seq-listing.txt</code> (line 21): it is for a person to read.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 88    seq_calls=$(awk -v self="$fn" '
 89      $1 !~ /^[0-9a-f]+:$/ { next }
 90      /[ \t](call|jmp)q?[ \t]+\*/ || $2 == "blr" || $2 == "br" { print "(indirect)"; next }
 91      $2 ~ /^(callq?|jmpq?|j[a-z]+|bl|b|b\.[a-z]+|cbn?z|tbn?z)$/ &amp;&amp; $NF ~ /^&lt;.*&gt;$/ {
 92        t = $NF; gsub(/^&lt;|&gt;$|\+0x[0-9a-f]+&gt;$|@plt/, "", t); if (t != self) print t }' &lt;&lt;&lt; "$code" | LC_ALL=C sort | uniq -c | awk '{ printf "%s%s=%s", (NR &gt; 1 ? " " : ""), $2, $1 }')</pre></td><td valign="top">The pipeline lists the places outside the function that the function calls or branches to, each with a count.<ul><li>First <code>awk</code> rule (line 89): skip every line that does not begin with an address and a colon.</li><li>Second rule (line 90): an indirect call or jump prints <code>(indirect)</code>. On Arm these are the instructions <code>blr</code> and <code>br</code> (branch to the address in a register). The <code>call</code> and <code>jmp</code> patterns are x86 mnemonics.</li><li>Third rule (lines 91 and 92): it handles a call or branch instruction whose last field is a name in angle brackets. It prints the name without the brackets, without an offset such as <code>+0x2c0</code>, and without <code>@plt</code>. It does not print the name of the function itself, so a branch inside the function does not count.</li><li><code>LC_ALL=C sort | uniq -c</code> sorts the names and counts each name. <code>LC_ALL=C</code> makes <code>sort</code> compare plain byte values.</li><li>The last <code>awk</code> joins the names into one line of <code>name=count</code> pairs with one space between them.</li><li><code>objdump</code> adds a comment such as <code>// b.any</code> after some conditional branches. Then the last field is not a name, and the third rule skips the line. In the saved listing every such branch stays inside its own function [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 93    echo "## $fn branch targets: ${seq_calls:-none}" &gt;&gt; "$B"
 94    seq_bad=$(tr ' ' '\n' &lt;&lt;&lt; "$seq_calls" | sed 's/=[0-9]*$//' | grep -vxE 'clock_gettime|\(indirect\)|tcount|__stack_chk_fail' || true)</pre></td><td valign="top"><ul><li>Line 93 appends the list to <code>build.txt</code> as <code>## &lt;function&gt; branch targets: ...</code>. An empty list is written as <code>none</code>.</li><li>CRB build, the same for both functions: <code>(indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2</code>. Each number counts the instructions that go to that target [Ref1].</li><li>Line 94 collects the names that are not allowed in <code>seq_bad</code>. <code>tr</code> puts each <code>name=count</code> pair on its own line, and <code>sed</code> removes <code>=count</code>. <code>grep -vxE</code> keeps the lines that are not exactly one of the four allowed names.</li><li><code>|| true</code> stops the rule <code>-e</code> from ending the script when <code>grep</code> keeps no line (<code>grep</code> then returns status 1).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 95    if [[ -n $seq_bad || $seq_calls != *"clock_gettime="* || $seq_calls != *"(indirect)="* ]]; then
 96      echo "$fn of $b: branch targets '${seq_calls:-none}'; not allowed or missing: ${seq_bad:-clock_gettime or the kernel call}" &gt;&amp;2; seq_fail=1
 97    fi
 98  done
 99  if (( seq_fail )); then exit 6; fi</pre></td><td valign="top"><ul><li>A function fails in three cases: <code>seq_bad</code> holds a name, the list has no <code>clock_gettime=</code> entry, or the list has no <code>(indirect)=</code> entry. In the last two cases the function would not read the clock or would not call a kernel.</li><li>On failure, line 96 prints the list to the error output and sets <code>seq_fail=1</code>. The loop still handles the second function, so <code>seq-listing.txt</code> and <code>build.txt</code> hold both.</li><li>Line 99 then ends the script with status 6 if a function failed. In that case <code>build.txt</code> gets no placement lines and no sha256 lines.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>placement</code>: where five functions start, modulo 64</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">100
101  # Placement of the timed path: the start modulo 64 of call(), read_smaps(),
102  # tcount() and the two timed functions (a function that gcc inlined everywhere
103  # has no symbol and is left out). bwx12.c pads after its new kernels so that
104  # the functions from call() to timed_sequence_hot() start where they start in
105  # bwx11 and bwx10, modulo 64 (and up to timed_sequence() as in bwx8). This is a record,
106  # not a gate: a difference does not stop the build.
107  placement() {
108    local out
109    out=$(nm "$1" 2&gt;/dev/null | awk '$3 ~ /^(call|read_smaps|tcount|timed_sequence|timed_sequence_hot)$/ { print $3, $1 }' | LC_ALL=C sort |
110      while read -r name addr; do printf '%s=%d ' "$name" $(( 16#$addr % 64 )); done)
111    echo "${out% }"
112  }</pre></td><td valign="top"><code>placement FILE</code> prints one line of <code>name=value</code> pairs for a binary.<ul><li><code>nm</code> lists the symbols of the binary with their addresses. <code>2&gt;/dev/null</code> hides its error messages.</li><li><code>awk</code> keeps the symbols with the names <code>call</code>, <code>read_smaps</code>, <code>tcount</code>, <code>timed_sequence</code> and <code>timed_sequence_hot</code>, and prints name and address.</li><li><code>LC_ALL=C sort</code> sorts the lines by name. <code>LC_ALL=C</code> makes <code>sort</code> compare plain byte values.</li><li>The <code>while</code> loop prints each name with its address modulo 64, in decimal. This is the offset of the function start inside a 64-byte block, in bytes.</li><li>Line 111 prints the result without the space at its end.</li><li>Purpose (comment): bwx12.c adds padding after its new kernels. The goal is that these functions start at the same offset as in the older binaries [Ref8]. The result is a record: a difference does not stop the build.</li></ul></td></tr>
<tr><td colspan="2"><b>Placement record and comparison with three older binaries</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">113  BWX8_BIN=${BWX8_BIN:-$SRC/../bwx8-20261114/bwx8}
114  p12=$(placement "$SRC/$b")
115  echo "## placement $b (start modulo 64): ${p12:-none}" &gt;&gt; "$B"</pre></td><td valign="top"><ul><li><code>BWX8_BIN</code> is the path of the accepted binary of bwx8. The default is the file <code>bwx8</code> in the folder <code>bwx8-20261114</code>, which stands beside the folder of this script.</li><li><code>p12</code> is the placement line of the new binary. Line 115 appends it to <code>build.txt</code> (<code>none</code> if it is empty).</li><li>CRB build: <code>call=24 read_smaps=52 tcount=52 timed_sequence=28 timed_sequence_hot=32</code> [Ref1]. For example, <code>call</code> starts 24 bytes after a 64-byte boundary.</li><li>A name in this line shows that the binary holds a symbol for the function. It does not show that any code calls it. In a test of this task, gcc 11.4.0 with <code>-O3 -fno-toplevel-reorder</code> kept the symbol of a <code>static</code> function that it had inlined at its only call [Ref21]. So with that compiler the rule of the comment of lines 102 and 103 does not hold for every function. The CRB compiler (gcc 14.2.0) was not tested.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">116  if [[ -f $BWX8_BIN ]]; then
117    p8=$(placement "$BWX8_BIN")
118    echo "## placement bwx8 (start modulo 64): ${p8:-none}" &gt;&gt; "$B"
119    # timed_sequence_hot does not exist in bwx8; it sorts last
120    if [[ -n $p8 &amp;&amp; $(sed 's/ timed_sequence_hot=[0-9]*$//' &lt;&lt;&lt; "$p12") == "$p8" ]]; then
121      echo "## placement up to timed_sequence against bwx8: same" &gt;&gt; "$B"
122    else
123      echo "## placement up to timed_sequence against bwx8: DIFFERS" &gt;&gt; "$B"
124    fi
125  else
126    echo "## placement against bwx8: not compared (no file $BWX8_BIN)" &gt;&gt; "$B"
127  fi</pre></td><td valign="top"><ul><li>If the bwx8 binary exists (<code>-f</code>), the script appends its placement line and then one line with the result of the comparison.</li><li>bwx8 has no <code>timed_sequence_hot</code>, and this name is the last one in the sorted line. So line 120 removes the last pair from the bwx12 line with <code>sed</code> and compares the rest with the bwx8 line as text.</li><li>The result line ends with <code>same</code> or <code>DIFFERS</code>. An empty bwx8 line gives <code>DIFFERS</code>.</li><li>If the file is missing, line 126 appends <code>not compared</code> with the path.</li><li>CRB build: <code>same</code> [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">128  BWX10_BIN=${BWX10_BIN:-$SRC/../bwx10-20261115/bwx10}
129  if [[ -f $BWX10_BIN ]]; then
130    p10=$(placement "$BWX10_BIN")
131    echo "## placement bwx10 (start modulo 64): ${p10:-none}" &gt;&gt; "$B"
132    if [[ -n $p10 &amp;&amp; $p12 == "$p10" ]]; then
133      echo "## placement up to timed_sequence_hot against bwx10: same" &gt;&gt; "$B"
134    else
135      echo "## placement up to timed_sequence_hot against bwx10: DIFFERS" &gt;&gt; "$B"
136    fi
137  else
138    echo "## placement against bwx10: not compared (no file $BWX10_BIN)" &gt;&gt; "$B"
139  fi</pre></td><td valign="top">The same steps for the accepted binary of bwx10 (default: the file <code>bwx10</code> in the folder <code>bwx10-20261115</code>). The bwx10 line of the CRB build has all five functions, and line 132 compares the two whole lines. CRB build: <code>same</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">140  BWX11_BIN=${BWX11_BIN:-$SRC/../bwx11-20261115/bwx11}
141  if [[ -f $BWX11_BIN ]]; then
142    p11=$(placement "$BWX11_BIN")
143    echo "## placement bwx11 (start modulo 64): ${p11:-none}" &gt;&gt; "$B"
144    if [[ -n $p11 &amp;&amp; $p12 == "$p11" ]]; then
145      echo "## placement up to timed_sequence_hot against bwx11: same" &gt;&gt; "$B"
146    else
147      echo "## placement up to timed_sequence_hot against bwx11: DIFFERS" &gt;&gt; "$B"
148    fi
149  else
150    echo "## placement against bwx11: not compared (no file $BWX11_BIN)" &gt;&gt; "$B"
151  fi</pre></td><td valign="top">The same steps for the accepted binary of bwx11 (default: the file <code>bwx11</code> in the folder <code>bwx11-20261115</code>). CRB build: <code>same</code> [Ref1]. So in the CRB build the five functions of bwx12 start at the same offsets as in bwx10 and bwx11, and the first four at the same offsets as in bwx8.</td></tr>
<tr><td colspan="2"><b>Last records: sha256 values, load and end time</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">152
153  {
154    echo "## sha256:"
155    (cd "$SRC" &amp;&amp; sha256sum bwx12.c bwx12_selftest.c build12.sh $b listing.txt offsets.tsv seq-listing.txt)
156    echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)"
157  } &gt;&gt; "$B"</pre></td><td valign="top">The block appends the end of <code>build.txt</code>:<ul><li><code>## sha256:</code>, then one line per file from <code>sha256sum</code>: the sha256 value (a checksum of 64 hexadecimal digits) and the file name. <code>cd</code> goes to the folder of the script first, so the names carry no path. The parentheses limit this <code>cd</code> to the one command line.</li><li>The seven files are <code>bwx12.c</code>, <code>bwx12_selftest.c</code>, this script, the binary, <code>listing.txt</code>, <code>offsets.tsv</code> and <code>seq-listing.txt</code>. <code>build.txt</code> and <code>selftest-bwx12.txt</code> get no line.</li><li><code>## load_after=... utc=...</code>: the three load averages and the UTC time at the end.</li><li>CRB build: the value of the binary begins with <code>cd58e564</code>. <code>go.sh</code> of the whole-chip test holds the full value and passes it to <code>rx.sh</code>. Both scripts check it and do not start a <code>bwx12</code> file with another value [Ref11] [Ref12].</li><li>CRB build: end at 17:12:14 UTC, 3 s after the start, with load averages 1.17, 28.05 and 30.86 tasks [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">158  cat "$B"
159  echo "## offsets.tsv:"
160  cat "$SRC/offsets.tsv"</pre></td><td valign="top">The script prints <code>build.txt</code>, then the line <code>## offsets.tsv:</code>, then <code>offsets.tsv</code> to the standard output. For the CRB build the file <code>build.out</code> in the folder <code>crb-build-1</code> holds this text: the 24 lines of <code>build.txt</code>, the title line, and the 56 lines of <code>offsets.tsv</code> [Ref6].</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: The record that this script wrote on CRB on 2026-11-15, 24 lines. Line 1: host, start time, load, logins. Line 2: gcc 14.2.0. Line 3: flags. Lines 4 and 5: no compiler message between them. Line 6: self-test result. Lines 7 and 8: branch targets. Lines 9 to 15: placement lines and comparisons. Lines 16 to 23: sha256 values. Line 24: load and end time.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/offsets.tsv`: The table of the CRB build: 1 header line and 55 kernel rows. Line 2 `read`, line 5 `asmread`, line 8 `oldread`. No row holds `NA`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: The machine code of the 55 kernels of the CRB build. The six kernels of the whole-chip test begin at line 1 (`read`), 59 (`asmread`), 133 (`oldread`), 754 (`read_1pl`), 854 (`read_nop96`) and 2126 (`read_nop256`). Lines 161 to 176: the loop of `k_oldread` with 4 `ldp` loads and 8 vector adds. Lines 206 to 234: `k_oldwrite` and `k_oldcopy` with a backward branch each. The only call of a library function in the file is `__stack_chk_fail`, in `k_oldread` and `k_oldread2`. Checked in this task with a script that applies the rule of lines 69 to 71 of `build12.sh`: each of the 55 functions holds exactly one backward branch to an address inside the function.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/seq-listing.txt`: The machine code of `timed_sequence` (from line 1) and `timed_sequence_hot` (from line 310) of the CRB build. Line 21 holds the SVE instruction `cntb`. Checked in this task: the 48 branch lines with a trailing comment all have a target inside their own function.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/selftest-bwx12.txt`: The self-test output of the CRB build, 852 lines. Line 1 holds `kernels=55`. The 852 lines are: 2 comment lines, 393 lines that begin with `call,`, and 457 rows that end with `pass`. The last line is `# failures=0`. The kernels `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` have 8 rows each: 3 rows with the check `buffer unchanged`, 2 rows with a check that ends with `page unchanged`, and 3 rows with a check that begins with `faults in page`. `oldread` has these 8 rows and 3 rows with the check `returned sum equals the sum of all words`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.out`: The standard output of the CRB build, 81 lines. Checked in this task with `diff`: lines 1 to 24 equal `build.txt`, line 25 is `## offsets.tsv:`, lines 26 to 81 equal `offsets.tsv`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/check_listing12.out`: The saved output of `check_listing12.py` for the CRB build. Line 58: `kernels=29 failed_rows=0 new_kernels=26 new_failed_rows=0`. Lines 2, 5, 8, 27 and 29: `read`, `asmread`, `oldread`, `read_1pl` and `read_nop96` with text `same`. Line 40: `read_nop256` with loop `expected`.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: The source of the runner. Lines 3 to 7, 36 to 42 and 62 to 68: each version is the version before plus additions. Lines 90 to 94: interval mode (`--seq`) and trial mode (`--trial`). Lines 134 to 140: CPUs 0 to 119 are the rule of the test machine. Lines 142 to 163: `PLACE` needs `-fno-toplevel-reorder` and `-falign-functions=4`. Lines 454 to 459: `-fno-ipa-icf` keeps a kernel and its copy under a second name. Lines 1440 to 1449: the pad after the new kernels. Line 1491: `call`. Line 1515: `read_smaps`. Line 112: `#include <pthread.h>`. Line 3012: `pthread_create` starts each `worker` thread. Lines 1632 to 1735: `worker`. Lines 1688 to 1701: the timed loop for the stop rule `--stop common` of the spec files. Line 1688 reads the clock at the start. Line 1695 calls the kernel through `call`. Line 1700 reads the clock after each call. Line 1967: `tcount`. Lines 1995 and 2056: the two timed functions of the trial mode. Line 2900: the `#include` of the self-test file. Lines 2913 to 2924: `main` handles `--trial`, `--selftest` and `--list`.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`: Lines 60 to 100: what the self-test checks. Lines 67 to 70: the line `call,...` before each kernel call names the kernel if the call crashes. Lines 76 to 83: the checks for a read kernel and their limit. Lines 134 to 139: a row ends with `pass` or `FAIL`. Lines 147 to 188: one kernel is called through `call` and the memory is checked. Lines 676 to 711: the function `selftest` with the buffer sizes and the last line `# failures=N`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`: Lines 1 to 25: the script runs on the development machine on `listing.txt` and `offsets.tsv`. The reference is the accepted build of bwx11. For every kernel of the reference it compares the function text and the loop start modulo 64.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: The driver of the whole-chip test. Line 13 holds the sha256 value of the binary. Line 23 stops the run when the `bwx12` file has another value. Line 31 calls `rx.sh` and passes the value to it. The file `go2.sh` in the same folder holds the same value on line 10, checks it on line 19 and passes it on line 30.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: The runner script of the bwx12 parts of the test. Line 3: a spec line is a tag, the character `|`, and the arguments of the binary. Line 8 checks the sha256 value of the binary and ends with status 2 when it differs. Lines 11 to 21: one process per spec line.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`: Line 1: the arguments of bwx12 in the whole-chip test, with `--seq` and without `--trial`. The files `cfwd.spec` and `crev.spec` in the same folder have the same form.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/env.txt`: The line that begins with `binary` holds the path and the sha256 value of the binary. Checked in this task: the 9 folders `w120-T72*` under `results` all hold the same line.
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: Line 19: the seven flags of the build of bw_old and bw_new. Line 29: the compiler call. Lines 31 and 32: the builds of bw_old and bw_new.
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Lines 1 to 3 of the record of 2026-11-13: host `ubuntu`, gcc 14.2.0, and the seven flags.
- [Ref17] Help text of gcc 11.4.0 on the development machine, read in this task (`gcc --help=optimizers`, `gcc --help=c`, `gcc -Q --help=optimizers -O3`, `gcc -dumpspecs`). It gives one line per flag, for example "Enable loop distribution for patterns transformed into a library call" for `-ftree-loop-distribute-patterns` and "Perform Identical Code Folding for functions and read-only variables" for `-fipa-icf`. At `-O3` it lists `-finline-functions` and `-ftree-loop-vectorize` as enabled. The help text of the CRB compiler (gcc 14.2.0) was not read.
- [Ref18] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: Lines 38 to 89: the word list of the project. Line 77 defines the marker file. Line 80 defines sha256.
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/build.sh`: Lines 5 to 7, 27 and 42: `EXTRA` holds more compiler flags and goes into the compiler call of the older runner version bwx.
- [Ref20] Computed in this task with `sha256sum` on the local files `bwx12.c`, `bwx12_selftest.c` and `build12.sh`, and on `listing.txt`, `offsets.tsv` and `seq-listing.txt` in `crb-build-1`. All six values equal the values on lines 17 to 19 and 21 to 23 of `build.txt`. `find` shows no file with the name `bwx12` under the local folder `crb`.
- [Ref21] Test in this task on the development machine with gcc 11.4.0 (x86-64). The C file has 16 lines. Its `static` function `call` has one call, through a `static inline` function, from a function `worker`. Built with `-O3`: `nm` shows no symbol `call`. Built with `-O3 -fno-toplevel-reorder`, and with `-O3 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`: `nm` shows the symbol `call`, and the `objdump` text of the binary holds no call of it. The `static inline` function has no symbol in any of the three builds. The CRB compiler (gcc 14.2.0, AArch64) was not tested.
- [Ref22] external source: the gcc 14.2.0 manual, chapter "AArch64 Options", entry `-march=name`, read in this task on gcc.gnu.org. The value `native` "causes the compiler to pick the architecture of the host system". GCC uses the architecture name "to determine what kind of instructions it can emit". If `-march` is given without `-mtune` or `-mcpu`, "the code is tuned to perform well across a range of target processors implementing the target architecture".
