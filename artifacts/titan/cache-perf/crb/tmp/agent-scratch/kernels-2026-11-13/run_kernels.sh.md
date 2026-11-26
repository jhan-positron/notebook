# `run_kernels.sh` explained

- Source file: `run_kernels.sh` in this folder (Bash script, 80 lines, 4188 bytes).
- sha256 of the source when this page was built: `6a91bbbe799b9279f99c693f44ef5852d5daa437a7e2469bf61c914b40b81842`.
- Role in the whole-chip test: Script of 2026-11-13 that built bw_old and bw_new and ran the first test.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

`run_kernels.sh` compiles the old benchmark source `bandwidth.orig.c` into the binary `bw_old` and the new source `bandwidth.c` into `bw_new`, writes the machine code of every kernel to `probe.txt`, and runs a self-test. In mode `all` it then times every kernel of both binaries, first with 1 thread and then with 120 threads on CPUs 0 to 119.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **write, copy, asmwrite, asmcopy**: the four other kernels of bw_old and bw_new. `write` fills a buffer. `copy` copies one buffer to a second buffer. `asmwrite` and `asmcopy` are hand-written loops for the same two jobs. They are not read kernels.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **ra.sh**: the script of the rerun of 2026-11-17 that runs part A. It uses the binaries that run_kernels.sh built.
- **go.sh**: the driver script of the rerun of 2026-11-17. It calls ra.sh.
- **stat_k120.py**: an analysis script that reads threads120.csv.
- **gcc**: the GNU C compiler.
- **objdump**: a tool that prints the machine code of a binary as assembler text.
- **Machine code, listing**: the instructions that the compiler produced for a function. The listing is their text form in probe.txt.
- **Loop pass**: one execution of the body of a loop.
- **NEON**: the Arm vector instructions with 16-byte registers. The listing writes these registers as `q` or `v` with a number.
- **SVE**: the Scalable Vector Extension, another set of Arm vector instructions. The listing writes its registers as `z` or `p` with a number.
- **SVE2**: the Scalable Vector Extension 2, a further set of Arm vector instructions. The record of 2026-11-11 names four SVE2 extensions [Ref13]. The gcc manual says that each of them also turns on SVE2, and that SVE2 also turns on the SVE instructions [Ref12].
- **Stack check**: code that the compiler adds to a function. At entry the function copies a guard value to its stack frame. Before it returns it compares the copy with the guard value. On a difference it calls `__stack_chk_fail`.
- **Self-test**: the program `selftest`. It checks what the kernels do to memory. Exit status 0 means that every check passed.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test [Ref11]. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **GB, KiB, MiB, GiB**: GB = 1e9 bytes. KiB = 2^10 bytes, MiB = 2^20 bytes, GiB = 2^30 bytes. The size arguments `32K`, `1M`, `8M`, `256M` and `1G` use the binary units: `256M` means 256 MiB = 268435456 bytes.
- **Exit status**: the number that a program returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time. The scripts write every time in UTC.
- **taskset**: a Linux tool that starts a command with a limit on the CPUs that the command may use.

</details>

## Main flow

1. Set the shell options that stop the script at a failed command and at an unset variable. Then restart the script under `taskset -c 0-119`. The script and every process that it starts may then use CPUs 0 to 119 only (lines 8-9).
2. Read the mode (`probe` or `all`). Stop if the marker file exists (lines 10-14).
3. Find the script folder and create the result folder `kernels-TIME` (`TIME` is the UTC time) (lines 15-18).
4. Set the compiler flags. Write host, time, load averages, gcc version and flags to `probe.txt` (lines 19-27).
5. Build `bw_old`, `bw_new`, `selftest` and `probe.o` with the same flags. Stop if a build fails (lines 28-35).
6. Append the checksums of sources and binaries and the machine code of the six kernels of each binary to `probe.txt` (lines 36-53).
7. Run the self-test. Stop with status 4 if it fails (lines 54-55).
8. Mode `probe` ends here (line 56).
9. Mode `all`: run 192 processes with 1 thread each, on CPU 0 and on CPU 2, with four buffer sizes. Their rows go to `one-thread.csv` (lines 58-74).
10. Mode `all`: run 24 processes with 120 threads each. Their rows go to `threads120.csv`. This is the part that ra.sh repeats (lines 75-78).
11. Append the load averages after the last process to `probe.txt` and print the result folder (lines 79-80).

## Behavior a reader must know

- The rerun of 2026-11-17 did not start this script. go.sh calls ra.sh, and ra.sh uses the binaries `bw_old` and `bw_new` that this script built on CRB on 2026-11-13 [Ref8].
- Every start of the script builds the binaries again. Three result folders of this script exist from 2026-11-13. Their starts were at 18:12:10 UTC (mode `probe`) [Ref4], at 18:12:22 UTC (mode `all`) [Ref1] and at 18:32:18 UTC (mode `probe`) [Ref5]. All three `probe.txt` files record the same sha256 for `bw_old` (e8fc0205...) and the same sha256 for `bw_new` (fd7c14df...) [Ref1] [Ref4] [Ref5]. ra.sh checks these two values [Ref8].
- The new source changed between the starts. `bandwidth.c` had the sha256 c1406e02... at 18:12:10 UTC and at 18:12:22 UTC, and f1985072... at 18:32:18 UTC [Ref4] [Ref1] [Ref5]. The sha256 of `bw_new` and the machine code of the kernels in `probe.txt` did not change [Ref1] [Ref5]. The local `bandwidth.c` has the sha256 f1985072... [Ref3]. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref14]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- Compiler result for the read kernels, from the listing [Ref1]: gcc turned the 16 sums of the old `k_read` into 8 vector registers with 2 sums each. One loop pass of the old `k_read` in `bw_old` has 4 `ldp q` loads (128 bytes) and 8 vector `add` instructions that add the loaded values to the sums. One loop pass of the new `k_read` in `bw_new` has 8 `ldp q` loads (256 bytes) and no instruction that uses the loaded values.
- Compiler result for the instruction sets, from the listing [Ref1]: the old `k_write` and `k_copy` in `bw_old` use SVE instructions (`whilelo`, `st1d`, `ld1d`). `-march=native` is the only flag of line 19 that sets the target architecture. The architecture decides which instructions gcc may use [Ref12]. A record from CRB of 2026-11-11 shows what the same gcc version picked for `native`: the architecture name `armv8-a` with 16 extensions (sets of extra instructions), among them four SVE2 extensions [Ref13]. The ten other kernel listings of the two binaries hold no SVE instruction.
- Compiler result for `-fno-tree-loop-distribute-patterns`, from the listing [Ref1]: no kernel calls `memset` or `memcpy`. The only call in the twelve kernel listings is the stack check of the old `k_read`.
- The old `k_read` in `bw_old` ends with a call to `__stack_chk_fail`, which belongs to a stack check. The instructions of the check sit before and after the loop, not inside it [Ref1]. No flag of line 19 asks for it. Insufficient data: the options that the gcc of CRB turns on without a flag. The output of `gcc -v` and of `gcc -Q --help=common -O3 -march=native` on CRB would resolve it.
- Source of the flag meanings on line 19: the help text of the local gcc 11.4.0 for x86-64 [Ref9]. The meaning of `-march=native` on an Arm machine comes from the public manual of gcc 14.2.0 [Ref12]. The value that gcc picked for `native` on CRB comes from a record of 2026-11-11, two days before the build [Ref13]. The `probe.txt` files of 2026-11-13 do not record this value. No manual page of gcc is installed on the local machine. CRB used gcc 14.2.0 [Ref1]. Insufficient data: the exact list of steps that `-O3` turns on in gcc 14.2.0 on CRB. The output of `gcc -Q --help=optimizers -O3` on CRB would resolve it.
- The self-test covers the new source only. `selftest.c` includes `bandwidth.c` [Ref6]. It does not check the kernels `read`, `write` and `copy` of the old source `bandwidth.orig.c`. The three hand-written kernels have the same source text in both files [Ref3].
- Order of the processes: one process holds one kernel of one binary. So no kernel is timed after another kernel in the same process. But the processes follow each other without a wait. On 2026-11-13 the 1-minute load average was 1.00 at the first 120-thread process and 85.38 at the last one [Ref2].
- What one 120-thread process does [Ref3]: each thread first pins itself to one CPU (thread number i to CPU i). Then it allocates its own buffer of 256 MiB, asks Linux for huge pages for it, and writes it once before any timing. It writes with `k_write`, the function of the kernel `write` of the same binary. For `copy` and `asmcopy` each thread has a second buffer of the same size. Before each of the 3 intervals every thread runs the kernel once over its buffer without timing. Then all threads start together. In each of the 3 intervals a thread reads the clock at its start and after each whole pass over its buffer. It stops when 0.5 s or more have passed.
- The rate [Ref3]: the binary prints one row per interval. Per pass over its buffer a thread counts the size of the buffer in bytes. For `copy` and `asmcopy` it counts twice that size: the bytes that it read plus the bytes that it wrote. The column `aggregate_GBps` is the sum of the bytes of all threads, divided by the longest elapsed time of any thread, in GB/s. Each process also prints a comment line, a title line and one `best` row with the highest of its 3 rates.
- The marker file is checked at the start, before the self-test and before each benchmark process. Nothing checks it while a process runs.
- The script can stop early. Status 2: unknown mode. Status 3: the marker file exists. Status 5: a build failed. Status 4: the self-test failed. A benchmark process that fails stops the script with its own status. Mode `probe` ends with status 0 after the self-test.
- The local file is the script that ran. Its sha256 (6a91bbbe...) equals the value that all three `probe.txt` files record [Ref1] [Ref4] [Ref5]. The local files `bandwidth.orig.c` (61228754...), `selftest.c` (90456a56...) and `probe.c` (81f96b39...) also have the sha256 values that all three files record [Ref1] [Ref4] [Ref5].
- The binaries `bw_old` and `bw_new` are not in the local folders. Their sha256 values are known only from records such as the three `probe.txt` files of this script [Ref1] [Ref4] [Ref5] and the two values that ra.sh checks [Ref8].

## Call sequence in the whole-chip test

- `run_kernels.sh all` (line 1): ran on CRB on 2026-11-13, not during the rerun of 2026-11-17
  - `taskset -c 0-119 run_kernels.sh all` (line 9): restart of the script, limited to CPUs 0 to 119
  - `check_marker` (line 13): stop with status 3 if the marker file exists
  - `load` (line 20): print the three load averages for probe.txt
  - `build` (line 29): gcc with the flags of line 19, four calls
    - `gcc bandwidth.orig.c` (line 31): builds bw_old, the binary with the old read kernel
    - `gcc bandwidth.c` (line 32): builds bw_new, the binary with the new read kernel
    - `gcc selftest.c` (line 33): builds the self-test of the new source
    - `gcc -c probe.c` (line 34): compiles three copy candidates, never run
  - `objdump` (line 42): machine code of the six kernels of both binaries to probe.txt
  - `selftest` (line 55): checks the kernels of the new source, must end with status 0
  - `one` (line 60): mode all: 192 one-thread processes, then 24 processes with 120 threads
    - `check_marker` (line 13): before every process
    - `bandwidth.orig.c:main`: binary bw_old: half of the processes, one kernel each
      - `bandwidth.orig.c:worker`: one thread: pins, allocates, times the kernel
        - `bandwidth.orig.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.orig.c:alloc_buf`: buffer of the thread, with a request for huge pages
        - `bandwidth.orig.c:k_write`: writes the whole buffer once, before any timing
        - `bandwidth.orig.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.orig.c:k_read`: old read kernel (kernel name read)
          - `bandwidth.orig.c:k_asmread`: hand-written load-only loop (kernel name asmread)
          - `bandwidth.orig.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels
    - `bandwidth.c:main`: binary bw_new: half of the processes, one kernel each
      - `bandwidth.c:worker`: one thread: pins, allocates, times the kernel
        - `bandwidth.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.c:alloc_buf`: buffer of the thread, with a request for huge pages
        - `bandwidth.c:k_write`: writes the whole buffer once, before any timing
        - `bandwidth.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.c:k_read`: new read kernel (kernel name read)
          - `bandwidth.c:k_asmread`: same hand-written loop as in bw_old (kernel name asmread)
          - `bandwidth.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 13-13 | Ends the script with status 3 when the marker file exists. | - | no |
| `load` | 20-20 | Prints the load averages of the last 1, 5 and 15 minutes. | - | no |
| `build` | 29-29 | Runs gcc with the flags of line 19. Appends the compiler messages to build.txt. Ends the script with status 5 when gcc fails. | `gcc` | no |
| `one` | 60-64 | Writes the `-- ` line, starts one benchmark binary with one kernel and waits for it. The timed intervals run inside that binary. | `check_marker`, `bw_old or bw_new` | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header comment: the two modes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  #!/usr/bin/env bash
 2  # run_kernels.sh - on CRB: build the old and the new bandwidth.c, print the
 3  # machine code of the kernels, run the self-test, then time old and new.
 4  # Usage: run_kernels.sh probe | all
 5  #   probe: build, machine code and self-test only (no timing)
 6  #   all:   probe, then the timed runs
 7  # Writes only under $HOME/cache-perf. Uses CPUs 0-119 only. No sudo.</pre></td><td valign="top">The comment gives the two modes. <code>probe</code> builds the binaries, prints the machine code of the kernels and runs the self-test. <code>all</code> does the same and then runs the timed processes. The timed run of 2026-11-13 used <code>all</code> [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  set -euo pipefail</pre></td><td valign="top"><ul><li><code>-e</code>: the script stops at the first command that fails (exit status not 0). A failing command inside an <code>if</code> test or in front of <code>||</code> does not stop it.</li><li><code>-u</code>: the script stops when it uses a variable that was never set.</li><li><code>-o pipefail</code>: a pipeline (commands joined with <code>|</code>) counts as failed when any command of it fails, not only the last one.</li></ul></td></tr>
<tr><td colspan="2"><b>Restart on CPUs 0 to 119</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 9  if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi</pre></td><td valign="top"><ul><li>The script starts itself again under <code>taskset -c 0-119</code>. This tool limits a command to CPUs 0 to 119.</li><li><code>exec</code> replaces the running shell with that command. No extra process is created.</li><li><code>_PINNED=1</code> is set for the new start. The test <code>-z ${_PINNED:-}</code> (is the variable empty or not set?) is then false. So the restart happens only once.</li><li>Every process that the script starts later inherits the CPU limit. The compiler, the self-test and the benchmark binaries are among them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">10  MODE=${1:-probe}
11  MARKER=/tmp/positron-perf.RUNNING
12  case $MODE in probe|all) ;; *) echo "usage: $0 probe|all" &gt;&amp;2; exit 2;; esac</pre></td><td valign="top"><ul><li>Line 10: <code>MODE</code> is the first argument. Without an argument it is <code>probe</code>.</li><li>Line 11: <code>MARKER</code> is the path of the marker file.</li><li>Line 12: the <code>case</code> accepts <code>probe</code> and <code>all</code>. Any other word prints the usage text and ends the script with status 2.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>check_marker</code>: stop when another test runs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">13  check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" &gt;&amp;2; exit 3; fi; }
14  check_marker</pre></td><td valign="top"><code>check_marker</code> tests whether the marker file <code>/tmp/positron-perf.RUNNING</code> exists (<code>-e</code>). If it exists, the function prints a message to the error output (stderr, <code>&gt;&amp;2</code>) and ends the script with status 3. Line 14 is the first call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">15  SRC=$(cd "$(dirname "$0")" &amp;&amp; pwd)
16  TS=$(date -u +%Y%m%dT%H%M%SZ)
17  OUT=$HOME/cache-perf/results/kernels-$TS
18  mkdir -p "$OUT"</pre></td><td valign="top"><ul><li>Line 15: <code>SRC</code> is the absolute path of the folder that holds this script. <code>dirname "$0"</code> gives the folder part of the script path. <code>cd</code> and <code>pwd</code> turn it into an absolute path.</li><li>The sources are read from <code>SRC</code> and the binaries are written to <code>SRC</code>.</li><li>Lines 16 to 18: <code>OUT</code> is a new result folder, <code>kernels-</code> plus the UTC time, under <code>$HOME/cache-perf/results</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Compiler flags, one by one</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">19  CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"</pre></td><td valign="top"><ul><li><code>-O3</code>: optimization level 3, the highest numbered level of gcc. At this level gcc may turn a scalar loop into a vector loop.</li><li><code>-march=native</code>: the target architecture is that of the machine that compiles, here CRB. The architecture decides which instructions gcc may use [Ref12]. A record from CRB of 2026-11-11 shows what the same gcc version picked for <code>native</code>: the architecture name <code>armv8-a</code> with 16 extensions (sets of extra instructions), among them four SVE2 extensions [Ref13]. The listing shows one case: two kernels of <code>bw_old</code> use SVE instructions [Ref1]. Line 19 has no <code>-mtune</code> and no <code>-mcpu</code> flag. For this case the gcc manual says that the code is tuned for a range of processors that implement the architecture [Ref12].</li><li><code>-fno-tree-loop-distribute-patterns</code>: turns off one step that <code>-O3</code> would run. That step replaces a loop pattern with a call to a library function, for example a copy loop with <code>memcpy</code>. With the flag, gcc does not replace a kernel loop with such a call.</li><li><code>-pthread</code>: compile and link with support for POSIX threads (the standard thread interface of Unix systems). The benchmark creates its threads with <code>pthread_create</code>.</li><li><code>-Wall</code>: turn on most warning messages. <code>-Wextra</code>: turn on some extra warnings. A warning does not change the machine code.</li><li><code>-std=gnu11</code>: the language is C of the 2011 standard with the GNU extensions.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>load</code>: the three load averages</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">20  load() { cut -d' ' -f1-3 /proc/loadavg; }</pre></td><td valign="top">Function <code>load</code> prints the first three fields of <code>/proc/loadavg</code> (<code>cut -d' ' -f1-3</code>: split the line at spaces and keep fields 1 to 3). They are the load averages over the last 1, 5 and 15 minutes.</td></tr>
<tr><td colspan="2"><b>Start <code>probe.txt</code> with the build environment</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">21  {
22    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who | wc -l) mode=$MODE"
23    echo "## gcc=$(gcc --version | head -1)"
24    echo "## CFLAGS=$CFLAGS"
25    echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
26    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
27  } &gt; "$OUT/probe.txt"</pre></td><td valign="top"><ul><li>The braces group lines 22 to 26. <code>&gt; "$OUT/probe.txt"</code> writes the output of all of them to the new file <code>probe.txt</code>.</li><li>Line 22: host name, UTC time, load averages, number of login sessions (<code>who</code> prints one line per login session, <code>wc -l</code> counts the lines) and the mode.</li><li>Line 23: the first line of <code>gcc --version</code>. It names the compiler version.</li><li>Line 24: the flags of line 19.</li><li>Line 25: the setting for transparent huge pages. The value in square brackets is the active one.</li><li>Line 26: <code>ps -eo pcpu,user,comm --sort=-pcpu</code> lists all processes with their %CPU, user and command name, highest %CPU first. <code>head -6</code> keeps the title line and 5 processes.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>build</code>: one gcc call</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">28  # old = the source before the change; new = the changed source
29  build() { gcc $CFLAGS "$@" 2&gt;&gt; "$OUT/build.txt" || { echo "build failed: $OUT/build.txt" &gt;&amp;2; cat "$OUT/build.txt" &gt;&amp;2; exit 5; }; }
30  : &gt; "$OUT/build.txt"</pre></td><td valign="top"><ul><li><code>build</code> runs <code>gcc</code> with the flags of line 19, followed by the arguments of the call (<code>"$@"</code>). <code>$CFLAGS</code> has no quotes. So the shell splits it into the seven flags.</li><li><code>2&gt;&gt;</code> appends the messages of gcc (its error output) to <code>build.txt</code>.</li><li>If gcc fails, the script prints <code>build.txt</code> to the error output and ends with status 5.</li><li>Line 30 creates <code>build.txt</code> as an empty file before the first build. <code>:</code> is a command that does nothing, and <code>&gt;</code> empties the file.</li></ul></td></tr>
<tr><td colspan="2"><b>Build the two benchmark binaries, the self-test and <code>probe.o</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">31  build -o "$SRC/bw_old" "$SRC/bandwidth.orig.c"
32  build -o "$SRC/bw_new" "$SRC/bandwidth.c"
33  build -o "$SRC/selftest" "$SRC/selftest.c"
34  build -c -o "$SRC/probe.o" "$SRC/probe.c"</pre></td><td valign="top"><ul><li>Line 31: <code>bandwidth.orig.c</code> (the old source) becomes the binary <code>bw_old</code>. It holds the old read kernel.</li><li>Line 32: <code>bandwidth.c</code> (the new source) becomes the binary <code>bw_new</code>. It holds the new read kernel.</li><li>Line 33: <code>selftest.c</code> becomes the binary <code>selftest</code>. This source includes <code>bandwidth.c</code>. So the self-test checks the kernels of the new source [Ref6].</li><li>Line 34: <code>probe.c</code> becomes the object file <code>probe.o</code>. <code>-c</code> means compile only, with no linking. The file holds three candidate copy loops [Ref7].</li><li>All four builds use the same flags. <code>-o</code> names the output file. All four output files are written to the script folder.</li><li>Both modes run these lines. So every start of the script builds <code>bw_old</code> and <code>bw_new</code> again and replaces the files.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">35  echo "## build output bytes: $(wc -c &lt; "$OUT/build.txt")" &gt;&gt; "$OUT/probe.txt"</pre></td><td valign="top">Append the size of <code>build.txt</code> in bytes to <code>probe.txt</code> (<code>wc -c</code> counts bytes). 0 bytes means that gcc printed no warning. On 2026-11-13 the size was 0 bytes [Ref1].</td></tr>
<tr><td colspan="2"><b>Append checksums and machine code to <code>probe.txt</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">36  {
37    echo "## sha256:"; (cd "$SRC" &amp;&amp; sha256sum bandwidth.orig.c bandwidth.c selftest.c probe.c run_kernels.sh bw_old bw_new selftest)
38    sha256sum "$HOME/cache-perf/bench/bandwidth.c"</pre></td><td valign="top"><ul><li>The braces that open on line 36 close on line 53. <code>&gt;&gt; "$OUT/probe.txt"</code> there appends the output of lines 37 to 52 to <code>probe.txt</code>.</li><li>Line 37: the sha256 of the four sources, of this script and of the three binaries. The parentheses run <code>cd</code> and <code>sha256sum</code> in a subshell (a child copy of the shell) inside <code>SRC</code>. So the output shows the file names without a folder.</li><li>Line 38: the sha256 of the copy of the benchmark source in the folder <code>bench</code>. On 2026-11-13 it was equal to the sha256 of <code>bandwidth.orig.c</code> [Ref1].</li><li>ra.sh later compares <code>bw_old</code> and <code>bw_new</code> with the two values that line 37 wrote [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">39    for b in bw_new bw_old; do
40      for f in k_read k_write k_copy k_asmread k_asmwrite k_asmcopy; do
41        echo "=== $b $f ==="
42        objdump -d --no-show-raw-insn --disassemble=$f "$SRC/$b" | sed -n '/&gt;:$/,/^$/p'
43      done
44    done</pre></td><td valign="top"><ul><li>For <code>bw_new</code>, then <code>bw_old</code>, and for each of the six kernel functions: print a title line <code>=== binary function ===</code>, then the machine code of that function.</li><li><code>objdump -d --disassemble=$f</code> prints the instructions of the function <code>$f</code> only. <code>--no-show-raw-insn</code> leaves out the bytes of each instruction.</li><li><code>sed -n '/&gt;:$/,/^$/p'</code> prints only the lines from the function label (a line that ends with <code>&gt;:</code>) to the next empty line. The title lines of objdump are dropped.</li><li>This listing is the record of what each kernel does in one loop pass. The C source alone does not decide that. The compiler chooses the instructions.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">45    for f in copy_barrier copy_plain copy_plain_norestrict; do
46      echo "=== probe.o $f ==="
47      objdump -d --no-show-raw-insn --disassemble=$f "$SRC/probe.o" | sed -n '/&gt;:$/,/^$/p'
48    done</pre></td><td valign="top">The same listing for the three functions of <code>probe.o</code>. These loops are only compiled. No part of the script runs them.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">49    for b in latency homelat; do
50      echo "=== bench/$b chase ==="
51      objdump -d --no-show-raw-insn --disassemble=chase "$HOME/cache-perf/bench/$b" | sed -n '/&gt;:$/,/^$/p' || echo "(not available)"
52    done
53  } &gt;&gt; "$OUT/probe.txt"</pre></td><td valign="top"><ul><li>The same listing for the function <code>chase</code> of two other programs in the folder <code>bench</code>: <code>latency</code> and <code>homelat</code>.</li><li><code>objdump</code> fails when the binary is missing. <code>pipefail</code> then makes the pipeline fail. The part after <code>||</code> prints the line <code>(not available)</code>, and the script continues.</li><li>The script only prints the machine code of these two programs. It does not run them.</li><li>Line 53 closes the braces of line 36.</li></ul></td></tr>
<tr><td colspan="2"><b>Run the self-test</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">54  check_marker
55  "$SRC/selftest" &gt; "$OUT/selftest.txt" 2&gt;&amp;1 &amp;&amp; echo "## selftest exit=0" &gt;&gt; "$OUT/probe.txt" || { echo "## selftest exit=$?" &gt;&gt; "$OUT/probe.txt"; echo "selftest failed" &gt;&amp;2; echo "$OUT"; exit 4; }</pre></td><td valign="top"><ul><li>Line 54: check the marker file again.</li><li>Line 55: run <code>selftest</code>. <code>&gt; ... 2&gt;&amp;1</code> writes its output and its error output to <code>selftest.txt</code>.</li><li>On success (<code>&amp;&amp;</code>) the script appends <code>## selftest exit=0</code> to <code>probe.txt</code>.</li><li>On failure (<code>||</code>) it appends the exit status to <code>probe.txt</code>, prints <code>selftest failed</code> and the result folder, and ends with status 4.</li><li>So the timed processes below start only after the self-test has passed.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">56  if [[ $MODE != all ]]; then echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" &gt;&gt; "$OUT/probe.txt"; echo "$OUT"; exit 0; fi</pre></td><td valign="top">In mode <code>probe</code> the script ends here with status 0. Before that it appends the load averages and the UTC time to <code>probe.txt</code> and prints the result folder. Only mode <code>all</code> continues to the timed processes.</td></tr>
<tr><td colspan="2"><b>Function <code>one</code>: start one benchmark process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">57
58  # One process per (binary, kernel): no kernel is timed after another kernel
59  # in the same process. Round 2 reverses the order of binaries and kernels.
60  one() { # csv binary kernel threads cpus bytes round
61    check_marker
62    echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" &gt;&gt; "$1"
63    "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 &gt;&gt; "$1"
64  }</pre></td><td valign="top"><ul><li>Arguments in this order: csv file, binary, kernel, threads, CPU list, bytes, round.</li><li>Line 61: check the marker file before every process. Nothing checks it while a process runs.</li><li>Line 62: append one line that starts with <code>-- </code> to the csv file. It holds the arguments, the 1-minute load average at this moment and the UTC time. stat_k120.py reads this line to know which rows belong to which process [Ref10].</li><li>Line 63: start the binary with one kernel (<code>--kernel</code>) and wait until it ends. <code>&gt;&gt;</code> appends the rows that the binary prints to the csv file.</li><li><code>--reps 3</code>: the process times 3 intervals. <code>--min-ms 500</code>: each interval lasts at least 500 ms [Ref3].</li><li>If the binary ends with a status other than 0, <code>set -e</code> ends the script with that status.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">65  K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"</pre></td><td valign="top"><code>K1</code> is the kernel order of round 1. <code>K2</code> holds the same six names in the reverse order, for round 2. <code>read</code> and <code>asmread</code> are the read kernels, and the other four names are the write and copy kernels. A <code>for</code> loop over such a list takes the names one by one.</td></tr>
<tr><td colspan="2"><b>One-thread processes (the rerun of 2026-11-17 does not repeat them)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">66  for round in 1 2; do
67    if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
68    for cpu in 0 2; do
69      for bytes in 32K 1M 8M 1G; do
70        for k in $KS; do for b in $BINS; do one "$OUT/one-thread.csv" $b $k 1 $cpu $bytes $round; done; done
71      done
72    done
73  done
74  echo "## one-thread done load=$(load) utc=$(date -u +%FT%TZ)" &gt;&gt; "$OUT/probe.txt"</pre></td><td valign="top"><ul><li>Two rounds. In each round: CPU 0, then CPU 2. For each CPU the buffer sizes <code>32K</code>, <code>1M</code>, <code>8M</code> and <code>1G</code> (32 KiB, 1 MiB, 8 MiB, 1 GiB). For each size all six kernels with both binaries.</li><li>Each process has 1 thread, pinned to that one CPU. Its rows are appended to <code>one-thread.csv</code>.</li><li>That gives 2 x 2 x 4 x 6 x 2 = 192 processes.</li><li>Round 2 reverses the order of the kernels and of the binaries, as in the 120-thread part. It does not reverse the order of the CPUs and of the sizes.</li><li>Line 74 appends the load averages and the UTC time after this part to <code>probe.txt</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>The 120-thread part: the test that ra.sh repeats</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">75  for round in 1 2; do
76    if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
77    for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done
78  done</pre></td><td valign="top"><ul><li>Round 1: for each kernel first <code>bw_old</code>, then <code>bw_new</code>. Order: old <code>read</code>, new <code>read</code>, old <code>write</code>, new <code>write</code>, old <code>copy</code>, new <code>copy</code>, old <code>asmread</code>, new <code>asmread</code>, old <code>asmwrite</code>, new <code>asmwrite</code>, old <code>asmcopy</code>, new <code>asmcopy</code>.</li><li>Round 2: the exact reverse of round 1. Order: new <code>asmcopy</code>, old <code>asmcopy</code>, new <code>asmwrite</code>, old <code>asmwrite</code>, new <code>asmread</code>, old <code>asmread</code>, new <code>copy</code>, old <code>copy</code>, new <code>write</code>, old <code>write</code>, new <code>read</code>, old <code>read</code>.</li><li>Every process gets the same arguments: 120 threads and the CPU list <code>0-119</code>. The binary pins thread number i to CPU i. <code>256M</code> gives each thread its own buffer of 256 MiB. Each process times 3 intervals of at least 500 ms each [Ref3].</li><li>All 24 processes append to one file, <code>threads120.csv</code>.</li><li>No wait comes before this part or between two processes. On 2026-11-13 the last one-thread process started at 18:17:20 UTC and the first of the 24 processes at 18:17:21 UTC [Ref2].</li><li>ra.sh holds these four lines and the function <code>one</code> with the same text [Ref8].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">79  echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" &gt;&gt; "$OUT/probe.txt"
80  echo "$OUT"</pre></td><td valign="top">Line 79 appends the load averages and the UTC time after the last process to <code>probe.txt</code>. Line 80 prints the result folder.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Written by this script at 18:12:22 UTC on 2026-11-13. Line 1: mode `all`. Line 2: gcc 14.2.0. Line 3: the flags. Line 12: build output of 0 bytes. Lines 14 to 22: checksums. Lines 23 to 330: machine code of the six kernels of bw_new (from line 23) and of bw_old (from line 155). Line 437: self-test exit status 0.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/one-thread.csv, /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/threads120.csv`: The 192 and the 24 lines that start with `-- ` give the order, the load and the start time of each process on 2026-11-13.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c, /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: The old and the new benchmark source. The functions `main`, `worker`, `pin_cpu`, `alloc_buf` and `pass` are the source for the statements on arguments, pinning, buffers, timing and the rate. Lines 162 to 255 of the old source and lines 286 to 379 of the new source (the hand-written kernels) have the same text (compared with diff). The local bandwidth.orig.c has the sha256 61228754... and the local bandwidth.c has the sha256 f1985072... (computed with sha256sum on 2026-11-21).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181210Z/probe.txt`: Written by the start of 18:12:10 UTC, mode `probe`. Lines 14 to 22 hold the same checksums as in Ref1.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: Written by the start of 18:32:18 UTC, mode `probe`. Line 15: bandwidth.c with the sha256 f1985072.... Lines 19 and 20: bw_old and bw_new with the same sha256 as in Ref1. Lines 23 to 436 (the machine code) equal the same lines of Ref1 (compared with diff).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c`: Lines 15 to 17 include bandwidth.c under another name for `main`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/probe.c`: Line 1 calls the file "compile-only candidates for k_copy". It defines copy_barrier, copy_plain and copy_plain_norestrict.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: Lines 17 and 18 hold the sha256 values that it checks. Lines 37 to 48 have the same text as lines 58 to 65 and 75 to 78 of run_kernels.sh (compared with diff). The driver go.sh in the same folder calls ra.sh and does not call run_kernels.sh.
- [Ref9] Help text of the local gcc 11.4.0 for x86-64, read on 2026-11-21: `gcc --help=optimizers`, `gcc --help=common`, `gcc --help=warnings`, `gcc --help=c`, `gcc --help=target`, `gcc -Q --help=optimizers` with `-O2`, `-O3` and `-O4`, and `gcc -dumpspecs` for `-pthread`. In this gcc, `-O3` and `-O4` turn on the same options, `-O3` turns on loop vectorization, and `-fno-tree-loop-distribute-patterns` turns off exactly one option that `-O3` has on.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Line 21 holds the pattern that reads the lines that start with `-- `.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The facts sheet of the rerun of 2026-11-17. Line 77 (list "Words used here") says that another user creates the marker file during a performance test. The script itself does not say who creates the file.
- [Ref12] external source: manual of gcc 14.2.0, page "AArch64 Options", entry `-march=name`, read on 2026-11-21. The entry says that the value `native` "causes the compiler to pick the architecture of the host system". It says that gcc uses the architecture name to decide which instructions it can emit. It also says that with `-march` and without `-mtune` or `-mcpu` the code is tuned for a range of processors that implement the architecture. The sub-section "-march and -mcpu Feature Modifiers" of the same page says that each of `sve2-aes`, `sve2-bitperm`, `sve2-sha3` and `sve2-sm4` also enables SVE2 instructions, and that `sve2` also enables SVE instructions.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt`: A record from CRB of 2026-11-11 at 21:00:17 UTC. Line 4 holds the same gcc version text as line 2 of Ref1. Line 5 holds what `gcc -march=native -Q --help=target` printed for the options `-march=`, `-mcpu=` and `-mtune=`. The value of `-march=` is `armv8-a` with 16 extensions. Four of them are SVE2 extensions: `sve2-aes`, `sve2-bitperm`, `sve2-sha3` and `sve2-sm4`. The values of `-mcpu=` and `-mtune=` are empty. The file probe-20261111T210017Z.cmd.txt in the same folder holds the commands that wrote the record.
- [Ref14] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
