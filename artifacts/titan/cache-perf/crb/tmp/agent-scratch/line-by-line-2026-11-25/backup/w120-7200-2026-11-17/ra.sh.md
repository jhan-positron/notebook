# `ra.sh` explained

- Source file: `ra.sh` in this folder (Bash script, 50 lines, 3038 bytes).
- sha256 of the source when this page was built: `6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254`.
- Role in the whole-chip test: Part A runner: 24 processes of bw_old and bw_new with 120 threads.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

`ra.sh` repeats the 120-thread part of the test of 2026-11-13 with the binaries `bw_old` and `bw_new` of that day: 24 processes, one per binary, kernel and round, each with 120 threads on CPUs 0 to 119. It builds nothing, and it writes the rows that the binaries print to `threads120.csv` and the machine state to `probe.txt` in a new result folder.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Machine code, listing**: the instructions that the compiler produced for a function. The listing is their text form. run_kernels.sh wrote it to its own `probe.txt` on 2026-11-13 [Ref1].
- **Loop pass**: one execution of the body of a loop.
- **write, copy, asmwrite, asmcopy**: the four other kernels of bw_old and bw_new. `write` fills a buffer. `copy` copies one buffer to a second buffer. `asmwrite` and `asmcopy` are hand-written loops for the same two jobs. They are not read kernels.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **go.sh**: the driver script of the rerun of 2026-11-17. It calls ra.sh once per session.
- **run_kernels.sh**: the script of 2026-11-13. It built bw_old and bw_new and ran the test for the first time.
- **gcc**: the GNU C compiler. run_kernels.sh built bw_old and bw_new with it [Ref7].
- **Self-test**: the program `selftest`. run_kernels.sh builds it and runs it before its timed processes [Ref7]. It checks what the kernels of the new source do to memory [Ref10].
- **rx.sh**: the script that starts the bwx12 processes of part L and part C.
- **stat_k120.py**: an analysis script that reads threads120.csv.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test [Ref8]. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. The benchmark does it before any timing, so that a timed interval holds no page fault.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **GB, MiB**: GB = 1e9 bytes. MiB = 2^20 bytes. The argument `256M` means 256 MiB = 268435456 bytes.
- **Exit status**: the number that a program returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time. The scripts write every time in UTC.
- **taskset**: a Linux tool that starts a command with a limit on the CPUs that the command may use.

</details>

## Main flow

1. Set the shell options that stop the script at a failed command and at an unset variable. Then restart the script under `taskset -c 0-119`. The script and every process that it starts may then use CPUs 0 to 119 only (lines 8-9).
2. Read the argument `NAME` (`T72A1`, `T72A2` or `T72A3` in go.sh). Stop if the marker file exists (lines 10-13).
3. Compare the sha256 of `bw_old` and `bw_new` with the values of 2026-11-13. Stop on a difference (lines 14-20).
4. Create the result folder `k120-NAME-TIME` (`TIME` is the UTC time) (lines 21-23).
5. Wait until at most 2 tasks are runnable (at most 40 readings, 1 s apart), then 5 s more. Stop if more than 2 tasks stay runnable. After the wait, check the marker file again (lines 25-29).
6. Write host, time, load averages, boot id, `MemTotal`, Linux kernel release, the 5 processes with the highest %CPU and the checksums to `probe.txt` (lines 30-36).
7. Round 1, 12 processes: for each kernel in the order `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`, first `bw_old`, then `bw_new`. Each process appends its rows to `threads120.csv` (lines 37-48).
8. Round 2, 12 processes: the same processes in the exact reverse order. The last two are `bw_new` with `read`, then `bw_old` with `read` (lines 45-48).
9. Append the load averages after the last process to `probe.txt` and print the result folder (lines 49-50).

## Behavior a reader must know

- Nothing in this script runs inside a timed interval. The script starts a binary and waits for it. The clock reads, the pinning of the threads and the buffers are in the binary [Ref2].
- What one process does with its arguments [Ref2]: each of the 120 threads first pins itself to one CPU (thread number i to CPU i). Then it allocates its own buffer of 256 MiB and asks Linux for huge pages for it (`madvise` with `MADV_HUGEPAGE`). Then it writes its whole buffer once before any timing (first touch). It writes with `k_write`, the function of the kernel `write` of the same binary. For `copy` and `asmcopy` each thread has a second buffer of the same size.
- Timing inside one process [Ref2]: before each of the 3 intervals every thread runs the kernel once over its buffer without timing. Then all threads start together. A thread reads the clock at its start and after each whole pass over its buffer. It stops when 0.5 s or more have passed. So the threads stop at different times (whole-pass stop).
- The rate [Ref2]: the binary prints one row per interval. For `read` and `asmread` a thread counts 268435456 bytes per pass over its buffer. It counts the same number for `write` and `asmwrite`. For `copy` and `asmcopy` it counts twice that number: the bytes that it read plus the bytes that it wrote. The column `aggregate_GBps` is the sum of the bytes of all threads, divided by the longest elapsed time of any thread, in GB/s. Each process also prints a comment line, a title line and one `best` row with the highest of its 3 rates.
- Machine code of the two read kernels, from the listing of 2026-11-13 [Ref1]: one loop pass of the old read kernel in `bw_old` has 4 `ldp q` loads (128 bytes) and 8 vector `add` instructions that add the loaded values to the running sums. One loop pass of the new read kernel in `bw_new` has 8 `ldp q` loads (256 bytes) and no instruction that uses the loaded values. The listing agrees with the comment on lines 4 and 5 of ra.sh: 8 vector registers hold the 16 running sums of the old read kernel, and the new read kernel has loads only.
- Order of the processes: one process holds one kernel of one binary. So no kernel is timed after another kernel in the same process. But the processes follow each other without a wait. In round 1 the old read kernel is process 1 and the new read kernel is process 2. In round 2 the new read kernel is process 23 and the old read kernel is process 24.
- The wait of lines 26 to 28 uses the number of tasks that are runnable at that moment. It does not use the load average. In sessions 2 and 3 the 1-minute load average after the wait was 98.64 and 102.96, and `probe.txt` records `runnable=2` [Ref3].
- The 1-minute load average is higher at the last process of a session than at the first process. The line that starts with `-- ` records it at the start of each process. It was 0.07 for process 1 and 77.06 for process 24 in session 1, 98.64 and 112.71 in session 2, and 102.96 and 111.98 in session 3 [Ref3]. It does not rise at every process. In session 3 it fell from 105.51 at process 5 to 98.02 at process 6 [Ref3].
- The marker file is checked before each process and not while a process runs. In the three sessions the start of a process came 2 s to 5 s after the start of the process before it [Ref3]. These start times have a resolution of 1 s. rx.sh checks the file every second while a process runs. When the file exists, rx.sh stops that process [Ref5].
- The script can stop early. Status 1: no `NAME`. Status 2: a binary is not the one of 2026-11-13, or cannot be read. Status 3: the marker file exists. Status 6: more than 2 tasks are runnable after 40 readings. A benchmark process that fails stops the script with its own status. go.sh stops the whole run when ra.sh ends with a status other than 0 [Ref4].
- The main differences between ra.sh and the 120-thread part of run_kernels.sh: ra.sh builds nothing and runs no self-test. It checks the checksums of the binaries. It waits before the first process, and it runs no one-thread process before the 120-thread processes. It records the boot id, `MemTotal`, the Linux kernel release and the runnable tasks. It does not record the gcc version and the compiler flags. The function `one`, the two kernel lists and the loop have the same text in both scripts [Ref7].
- The local file is the script that ran. Its sha256 (6d67715e...) equals the value that `probe.txt` records in all three sessions [Ref3].
- The records show two texts of the new source `bandwidth.c`. The local file has the sha256 f1985072... [Ref2]. The timed run of 2026-11-13 recorded the sha256 c1406e02... for `bandwidth.c` in its `probe.txt` [Ref1]. All three `probe.txt` files that run_kernels.sh wrote on that day record the same sha256 for `bw_new` (fd7c14df...) [Ref1] [Ref9]. ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref11]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- The binaries `bw_old` and `bw_new` are not in the local folders. Their sha256 values are known only from records such as lines 17 and 18 of ra.sh and the `probe.txt` files [Ref1] [Ref3] [Ref9].

## Call sequence in the whole-chip test

- `ra.sh NAME` (line 1): go.sh calls it once per session with NAME T72A1, T72A2 or T72A3
  - `taskset -c 0-119 ra.sh NAME` (line 9): restart of the script, limited to CPUs 0 to 119
  - `check_marker` (line 12): stop with status 3 if the marker file exists
  - `sha256sum -c` (line 16): compare bw_old and bw_new with the checksums of 2026-11-13
  - `load` (line 24): print the three load averages for probe.txt
  - `one` (line 39): 24 calls: bw_old and bw_new in turn per kernel. Round 2: reverse order
    - `check_marker` (line 12): before every process
    - `bandwidth.orig.c:main`: binary bw_old: 12 of the 24 processes, one kernel each
      - `bandwidth.orig.c:worker`: one of 120 threads: pins, allocates, times the kernel
        - `bandwidth.orig.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.orig.c:alloc_buf`: 256 MiB buffer of the thread, with a request for huge pages
        - `bandwidth.orig.c:k_write`: first touch: writes the whole buffer once, before any timing
        - `bandwidth.orig.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.orig.c:k_read`: old read kernel (kernel name read)
          - `bandwidth.orig.c:k_asmread`: hand-written load-only loop (kernel name asmread)
          - `bandwidth.orig.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels, one process each per round
    - `bandwidth.c:main`: binary bw_new: 12 of the 24 processes, one kernel each
      - `bandwidth.c:worker`: one of 120 threads: pins, allocates, times the kernel
        - `bandwidth.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.c:alloc_buf`: 256 MiB buffer of the thread, with a request for huge pages
        - `bandwidth.c:k_write`: first touch: writes the whole buffer once, before any timing
        - `bandwidth.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.c:k_read`: new read kernel (kernel name read)
          - `bandwidth.c:k_asmread`: same hand-written loop as in bw_old (kernel name asmread)
          - `bandwidth.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels, one process each per round

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 12-12 | Ends the script with status 3 when the marker file exists. | - | no |
| `load` | 24-24 | Prints the load averages of the last 1, 5 and 15 minutes. | - | no |
| `one` | 39-43 | Writes the `-- ` line, starts one benchmark binary with one kernel and waits for it. The timed intervals run inside that binary. | `check_marker`, `bw_old or bw_new` | no |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header comment: what the script does</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  #!/usr/bin/env bash
 2  # ra.sh NAME - rerun of the 120-thread part of run_kernels.sh (2026-11-13).
 3  # It uses the SAME two binaries as that run (sha256 checked) and builds nothing.
 4  # bw_old = bandwidth.orig.c (read kernel: portable C, 16 running sums, load + add).
 5  # bw_new = bandwidth.c      (read kernel: NEON intrinsics, loads only).
 6  # Process arguments, kernel order and round order are those of run_kernels.sh.
 7  # Writes only under $HOME/cache-perf/results. Uses CPUs 0-119 only. No sudo.</pre></td><td valign="top">The comment states what the script does. It repeats the 120-thread part of <code>run_kernels.sh</code> with the two binaries of 2026-11-13 and builds nothing. <code>bw_old</code> holds the old read kernel. <code>bw_new</code> holds the new read kernel.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  set -euo pipefail</pre></td><td valign="top"><ul><li><code>-e</code>: the script stops at the first command that fails (exit status not 0). A failing command inside an <code>if</code> test or in front of <code>||</code> does not stop it.</li><li><code>-u</code>: the script stops when it uses a variable that was never set.</li><li><code>-o pipefail</code>: a pipeline (commands joined with <code>|</code>) counts as failed when any command of it fails, not only the last one.</li></ul></td></tr>
<tr><td colspan="2"><b>Restart on CPUs 0 to 119</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 9  if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi</pre></td><td valign="top"><ul><li>The script starts itself again under <code>taskset -c 0-119</code>. This tool limits a command to CPUs 0 to 119.</li><li><code>exec</code> replaces the running shell with that command. No extra process is created.</li><li><code>_PINNED=1</code> is set for the new start. The test <code>-z ${_PINNED:-}</code> (is the variable empty or not set?) is then false. So the restart happens only once.</li><li>Every process that the script starts later inherits the CPU limit. The benchmark binaries are among them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">10  NAME=${1:?usage: ra.sh NAME}</pre></td><td valign="top"><code>NAME</code> is the first argument. If it is missing or empty, bash prints <code>usage: ra.sh NAME</code> and the script ends with status 1. <code>NAME</code> becomes part of the name of the result folder (line 22). go.sh passes <code>T72A1</code>, <code>T72A2</code> and <code>T72A3</code>, one per session [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>check_marker</code>: stop when another test runs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">11  MARKER=/tmp/positron-perf.RUNNING
12  check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" &gt;&amp;2; exit 3; fi; }
13  check_marker</pre></td><td valign="top"><code>check_marker</code> tests whether the marker file <code>/tmp/positron-perf.RUNNING</code> exists (<code>-e</code>). If it exists, the function prints a message to the error output (stderr, <code>&gt;&amp;2</code>) and ends the script with status 3. Line 13 is the first call.</td></tr>
<tr><td colspan="2"><b>Check that the binaries are those of 2026-11-13</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">14  SRC=$HOME/cache-perf/scratch-kernels-20261113
15  # sha256 of the binaries as recorded in results/kernels-20261113T181222Z/probe.txt
16  (cd "$SRC" &amp;&amp; sha256sum -c - &gt; /dev/null &lt;&lt;'SUMS'
17  e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
18  fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
19  SUMS
20  ) || { echo "sha mismatch: bw_old or bw_new is not the binary of 2026-11-13" &gt;&amp;2; exit 2; }</pre></td><td valign="top"><ul><li><code>SRC</code> is the folder on CRB that holds <code>bw_old</code> and <code>bw_new</code>.</li><li><code>sha256sum -c -</code> reads the two lines between <code>&lt;&lt;'SUMS'</code> and <code>SUMS</code>. Each line holds a checksum and a file name. The tool computes the sha256 of each file and compares it with the given value.</li><li><code>&gt; /dev/null</code> drops the report of the tool. Only its exit status is used.</li><li>The parentheses run <code>cd</code> and the check in a subshell (a child copy of the shell). The working folder of the script itself does not change.</li><li>If a file differs or cannot be read, the part after <code>||</code> runs: the script prints <code>sha mismatch ...</code> and ends with status 2.</li><li>The two checksums equal the values that <code>run_kernels.sh</code> recorded for the binaries on 2026-11-13 [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">21  TS=$(date -u +%Y%m%dT%H%M%SZ)
22  OUT=$HOME/cache-perf/results/k120-$NAME-$TS
23  mkdir -p "$OUT"</pre></td><td valign="top"><ul><li><code>TS</code> is the UTC time of this moment, written as date, <code>T</code>, time, <code>Z</code>. In session 1 it was <code>20261117T221209Z</code> [Ref3].</li><li><code>OUT</code> is the result folder: <code>k120-</code>, then <code>NAME</code>, then <code>TS</code>, under <code>$HOME/cache-perf/results</code>. <code>mkdir -p</code> creates it.</li><li>The time is read before the wait of lines 26 to 28. So the first process starts at least 5 s after the time in the folder name.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>load</code>: the three load averages</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">24  load() { cut -d' ' -f1-3 /proc/loadavg; }</pre></td><td valign="top">Function <code>load</code> prints the first three fields of <code>/proc/loadavg</code> (<code>cut -d' ' -f1-3</code>: split the line at spaces and keep fields 1 to 3). They are the load averages over the last 1, 5 and 15 minutes.</td></tr>
<tr><td colspan="2"><b>Wait until at most 2 tasks are runnable</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">25  # Before the first process: wait until at most 2 tasks are runnable, then 5 s (rule of rx.sh).
26  for _ in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); if [[ $r -le 2 ]]; then break; fi; sleep 1; done
27  if [[ $r -gt 2 ]]; then echo "not quiet: $r tasks runnable after 40 s: stop" &gt;&amp;2; exit 6; fi
28  sleep 5
29  check_marker</pre></td><td valign="top"><ul><li>Line 26: the loop runs at most 40 times. Each time it reads the fourth field of <code>/proc/loadavg</code>, which holds two numbers with a slash between them. The second <code>cut</code> keeps the number before the slash. This is <code>r</code>, the number of tasks that are runnable now.</li><li>If <code>r</code> is 2 or less, <code>break</code> leaves the loop. If not, the script sleeps 1 s and reads again.</li><li>Line 27: if <code>r</code> is still above 2 after the 40 readings, the script ends with status 6.</li><li>Line 28: the script then always waits 5 s more.</li><li>Line 29: the marker file is checked again after the wait.</li><li>This wait runs once, before the first of the 24 processes. rx.sh has the same loop and the same 5 s wait before every process, but not the stop of line 27 [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Write the machine state to <code>probe.txt</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">30  {
31    echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who | wc -l) name=$NAME"
32    echo "## boot_id=$(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo | tr -s ' ') runnable=$r"
33    echo "## kernel=$(uname -r) thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
34    echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu | head -6
35    echo "## sha256:"; (cd "$SRC" &amp;&amp; sha256sum bw_old bw_new); sha256sum "$0"
36  } &gt; "$OUT/probe.txt"</pre></td><td valign="top"><ul><li>The braces group lines 31 to 35. <code>&gt; "$OUT/probe.txt"</code> writes the output of all of them to the new file <code>probe.txt</code>.</li><li>Line 31: host name, UTC time, load averages, number of login sessions (<code>who</code> prints one line per login session, <code>wc -l</code> counts the lines) and <code>NAME</code>.</li><li>Line 32: the boot id, the <code>MemTotal</code> line of <code>/proc/meminfo</code> (<code>tr -s ' '</code> turns each run of spaces into one space) and the last value of <code>r</code>. The script read this value in the loop of line 26, before the 5 s wait.</li><li>Line 33: the release of the Linux kernel (<code>uname -r</code>) and the setting for transparent huge pages. The value in square brackets is the active one.</li><li>Line 34: <code>ps -eo pcpu,user,comm --sort=-pcpu</code> lists all processes with their %CPU, user and command name, highest %CPU first. <code>head -6</code> keeps the title line and 5 processes.</li><li>Line 35: the sha256 of <code>bw_old</code>, of <code>bw_new</code> and of this script (<code>$0</code>).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>one</code>: start one benchmark process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">37  # One process per (binary, kernel): no kernel is timed after another kernel
38  # in the same process. Round 2 reverses the order of binaries and kernels.
39  one() { # csv binary kernel threads cpus bytes round
40    check_marker
41    echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" &gt;&gt; "$1"
42    "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 &gt;&gt; "$1"
43  }</pre></td><td valign="top"><ul><li>Arguments in this order: csv file, binary, kernel, threads, CPU list, bytes, round.</li><li>Line 40: check the marker file before every process. Nothing checks it while a process runs.</li><li>Line 41: append one line that starts with <code>-- </code> to the csv file. It holds the arguments, the 1-minute load average at this moment and the UTC time. stat_k120.py reads this line to know which rows belong to which process [Ref6].</li><li>Line 42: start the binary with one kernel (<code>--kernel</code>) and wait until it ends. <code>&gt;&gt;</code> appends the rows that the binary prints to the csv file.</li><li><code>--reps 3</code>: the process times 3 intervals. <code>--min-ms 500</code>: each interval lasts at least 500 ms [Ref2].</li><li>If the binary ends with a status other than 0, <code>set -e</code> ends the script with that status.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">44  K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"</pre></td><td valign="top"><code>K1</code> is the kernel order of round 1. <code>K2</code> holds the same six names in the reverse order, for round 2. <code>read</code> and <code>asmread</code> are the read kernels, and the other four names are the write and copy kernels. A <code>for</code> loop over such a list takes the names one by one.</td></tr>
<tr><td colspan="2"><b>The 24 processes: round 1, then round 2 in reverse order</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">45  for round in 1 2; do
46    if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi
47    for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done
48  done</pre></td><td valign="top"><ul><li>Round 1 (<code>BINS</code> holds old, then new, and <code>KS</code> is <code>K1</code>): for each kernel first <code>bw_old</code>, then <code>bw_new</code>. Order: old <code>read</code>, new <code>read</code>, old <code>write</code>, new <code>write</code>, old <code>copy</code>, new <code>copy</code>, old <code>asmread</code>, new <code>asmread</code>, old <code>asmwrite</code>, new <code>asmwrite</code>, old <code>asmcopy</code>, new <code>asmcopy</code>.</li><li>Round 2 (<code>BINS</code> holds new, then old, and <code>KS</code> is <code>K2</code>): the exact reverse of round 1. Order: new <code>asmcopy</code>, old <code>asmcopy</code>, new <code>asmwrite</code>, old <code>asmwrite</code>, new <code>asmread</code>, old <code>asmread</code>, new <code>copy</code>, old <code>copy</code>, new <code>write</code>, old <code>write</code>, new <code>read</code>, old <code>read</code>.</li><li>Every process gets the same arguments: 120 threads and the CPU list <code>0-119</code>. The binary pins thread number i to CPU i. <code>256M</code> gives each thread its own buffer of 256 MiB. Each process times 3 intervals of at least 500 ms each [Ref2].</li><li>All 24 processes append to one file, <code>threads120.csv</code>.</li><li>No wait separates two processes. Only the first process (old <code>read</code>, round 1) starts directly after the wait of lines 26 to 28.</li><li>The new read kernel starts directly after the old read kernel in round 1. In round 2 it starts directly after <code>bw_old</code> with <code>write</code>, and the old read kernel is the last process.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">49  echo "## load_after=$(load) utc=$(date -u +%FT%TZ) $(grep MemTotal /proc/meminfo | tr -s ' ')" &gt;&gt; "$OUT/probe.txt"
50  echo "done $OUT"</pre></td><td valign="top">Line 49 appends a last line to <code>probe.txt</code>: the load averages, the UTC time and the <code>MemTotal</code> line after the last process. Line 50 prints <code>done</code> and the result folder.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Written by run_kernels.sh on 2026-11-13 at 18:12:22 UTC. Line 15 holds the sha256 of bandwidth.c: c1406e02.... Lines 19 and 20 hold the sha256 of bw_old and bw_new. They equal the values on lines 17 and 18 of ra.sh. From line 23 the file holds the machine code of the kernels of bw_new, and from line 155 the machine code of the kernels of bw_old.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c, /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: Sources of bw_old and bw_new. The functions `main`, `worker`, `pin_cpu`, `alloc_buf` and `pass` are the source for the statements on arguments, pinning, buffers, timing and the rate. The local bandwidth.orig.c has the sha256 on line 14 of Ref1. The local bandwidth.c has the sha256 f1985072.... The probe.txt in /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z records this sha256 (line 15) together with a bw_new that has the sha256 that ra.sh checks (line 20).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z, /home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A2-20261117T221518Z, /home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A3-20261117T221827Z`: Result folders of sessions 1, 2 and 3. In each `threads120.csv` the 24 lines that start with `-- ` give the process order, the load and the start time. In each `probe.txt` line 1 holds the load averages read after the wait (`load_before`), line 2 holds `runnable=2`, and line 14 holds the sha256 of ra.sh.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: Line 41 calls ra.sh once per session and stops the whole run when ra.sh ends with a status other than 0.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: Lines 14 and 15 hold the same wait loop and the 5 s wait, before every process and without a stop. Line 19 checks the marker file every second while a process runs.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Line 21 holds the pattern that reads the lines that start with `-- `.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: Line 29 runs gcc. Lines 31 to 33 build bw_old, bw_new and the program selftest with it. Line 55 runs selftest. Lines 58 to 65 and 75 to 78 have the same text as lines 37 to 48 of ra.sh (compared with diff).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The facts sheet of the rerun of 2026-11-17. Line 77 (list "Words used here") says that another user creates the marker file during a performance test. The script itself does not say who creates the file.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181210Z/probe.txt, /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: The two other records that run_kernels.sh wrote on 2026-11-13, at 18:12:10 UTC and at 18:32:18 UTC. Both starts built the binaries and timed nothing. Line 15 holds the sha256 of bandwidth.c: c1406e02... in the first file and f1985072... in the second file. Lines 19 and 20 hold the sha256 of bw_old and bw_new. Both files give the same two values as Ref1.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c`: Source of the program selftest. Line 2 says that the program checks what the six kernels of bandwidth.c do to memory. Line 16 includes bandwidth.c, the new source.
- [Ref11] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
