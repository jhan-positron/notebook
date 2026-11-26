# `like.spec` explained

- Source file: `like.spec` in this folder (text file, 1 lines, 274 bytes).
- sha256 of the source when this page was built: `9b331df92ae5494f81d3ec4473de3d750802581201f008f09f15e6b394c788be`.
- Role in the whole-chip test: Argument line of part L and control I: one bwx12 process, five kernels.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The file holds one line: a tag and the argument list of one bwx12 process, which the runner script rx.sh starts. The process pins 120 threads to CPUs 0 to 119 and times 5 read loops for 6 s each, in 2 rounds (10 timed intervals).

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Idle machine**: the start state of control I. Before each process go2.sh waits until the 1-minute load average of Linux is below 1.0 [Ref4]. The load average is the number of tasks that are runnable or wait for disk input and output, averaged here over the last minute. It was 0.87 and 0.91 at the two launches of control I [Ref7].
- **Baseline**: an earlier 8000 MT/s run with 12 memory modules that used the same binary and method as a part of the rerun. The list of baselines was fixed before the run. Row L-1 of the facts sheet is the baseline of part L. It ran the same argument line.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **2 MiB pages**: transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.
- **MT/s**: million transfers per second, the unit of memory speed.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Spec file**: a text file for rx.sh. Each line has the form `tag|arguments` and starts one process. The three spec files of the rerun hold one line each.
- **Tag**: the text before the `|` of a spec line. rx.sh uses it as the name of the csv file.
- **rx.sh**: the runner script of the bwx12 processes (parts L, C, I). It reads a spec file, starts one process per line on CPUs 0-119, and writes env.txt, launches.txt, stderr.txt and one csv file per line.
- **launches.txt**: a file that rx.sh writes on CRB. It holds one launch line before each process (tag, time, load, logins, arguments) and one `rc` line after it (exit status, tag, time).
- **go.sh, go2.sh**: go.sh is the driver script of the rerun: three sessions of parts A, L, C and a fourth part C process. go2.sh is the script of control I.
- **T72L1, T72C1, T72I1 and similar names**: the first argument that go.sh or go2.sh gives to rx.sh. rx.sh puts it into the name of the result folder, for example `w120-T72L1-20261117T221329Z`. The letter names the part: L, C, or I for control I. The last digit is the session of go.sh (1 to 3), 4 for the extra part C process, or the pass of go2.sh (1 or 2).
- **Rerun**: the whole-chip read test of 2026-11-17 at 7200 MT/s.
- **Facts sheet**: the file FACTS.md of the rerun. The script build_facts.py wrote it from the raw files. It is the source of the report.
- **Check 12, check 13, check 14, check 15, check 16**: numbered integrity checks in section 1.4 of the facts sheet. build_facts.py runs them and writes one line per check.
- **MiB**: 2^20 bytes (1048576 bytes). 256 MiB are 268435456 bytes.
- **GB**: 1e9 bytes.
- **Chunk**: 2 MiB of the buffer. With `--stop common` bwx12 calls the kernel on one chunk at a time and reads the clock after each chunk. After the last chunk of the buffer it goes on at byte 0.
- **Warm-up pass**: one call of the kernel on the whole buffer directly before its timed interval. It is not timed.
- **Counter unit (PMU)**: PMU means performance monitoring unit: the hardware event counters of a CPU core. Linux lists the unit of the CRB cores as the device `armv8_pmuv3_0` and gives it a type number [Ref6].
- **perf_event_attr**: the structure that a program hands to the Linux system call `perf_event_open` to open one counter. bwx12 fills the field `type` from `--pmu-type` and the field `config` from the CODE of `--events` [Ref1].
- **Busy level (CBusy)**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. The core counts the answers of each level. This is the definition of the ASCT cross-check report of this project [Ref12]. ASCT is the Arm System Characterization Tool, a tool of Arm for memory latency and bandwidth tests.
- **cbusy0, cbusy1, cbusy2, cbusy3**: column names that this line gives to the core events with the codes 0x198, 0x199, 0x19a and 0x19b. The tool `perf list` on CRB names them `l2_chi_cbusy0` to `l2_chi_cbusy3`. Its text for the first one is "Number of RXDAT or RXRSP response received with CBusy of 0". The other three texts end with 1, 2 and 3 [Ref5].
- **cbusy_mt**: column name for the core event with the code 0x19c. `perf list` on CRB names it `l2_chi_cbusy_mt` with the text "Number of RXDAT or RXRSP response received with CBusy Multi-threaded set" [Ref5]. Insufficient data: what the flag "Multi-threaded" means. The Arm documentation of this core event would resolve it.
- **bus_access**: column name for the core event with the code 0x19. `perf list` on CRB gives the text "Attributable Bus access" [Ref5].
- **RXDAT, RXRSP**: names in the event texts of `perf list`. By these texts they are the two kinds of response that carry the CBusy value [Ref5]. Insufficient data: their exact definition. The Arm documentation of these core events would resolve it.

</details>

## How to read this file

1. The line has two fields. The character `|` stands between them. rx.sh splits the line at the first `|` [Ref2] (line 1).
2. Field 1 is the tag `a6456`. rx.sh uses it as the name of the csv file (`a6456.csv`) and writes it into the two lines of launches.txt [Ref2]. The digits match the thread counts of the line: 64 on CPUs 0-63 and 56 on CPUs 64-119. Insufficient data: the naming rule of the tag. A note of the author of r8.spec would resolve it [Ref8] (line 1).
3. Field 2 is the argument list of bwx12. rx.sh passes it without quotes. So the shell splits it at the spaces into 21 arguments [Ref2] (line 1).
4. The function `main` of bwx12.c reads the arguments from left to right. The table row of line 1 explains each one. When `main` does not know an option, it prints the usage text and ends the process with status 2 [Ref1].
5. go.sh starts rx.sh with this file as its input once per session: folders T72L1, T72L2 and T72L3 (part L) [Ref3]. go2.sh does the same 2 times: folders T72I1 and T72I2 (control I) [Ref4].
6. bwx12 repeats the options in the first two lines of the csv file: `threads=120 bytes_per_thread=268435456 min_ms=6000` in line 1 and `seq=oldread,asmread,read_nop96,read_nop256,read_1pl rounds=2 stop=common start=common` in line 2. The header line of the `C` rows repeats the six event names, the type 11 and the six codes [Ref9].

## Behavior a reader must know

- **What is timed.** Each thread reads the clock when an interval starts and after every 2 MiB chunk. The last clock value ends the interval. Not timed: the first write of the buffer, one warm-up pass of each kernel over the whole buffer directly before its interval, the two counter readings, and the reading of the page state between two intervals [Ref1].
- **Start time.** With `--stop common` the main thread sets the common start time 2 ms after it released the workers. Each worker waits for that time in a loop that reads the clock. Then it reads the counters and reads the clock again. This clock value is the start of its interval. When it is more than 0.1 ms after the common start time, the `T` row of the thread gets the flag `late` [Ref1]. In the 9 bwx12 csv files of the rerun no `T` row has this flag (check 12 of the facts sheet) [Ref7].
- **Rate.** bwx12 counts 2 MiB for each chunk, for every kernel of this line. For `read_1pl` the 2 MiB are the size of the address range that the loop covers. The loop loads only 16 bytes of every 64 bytes. The `I` row of an interval holds the bytes of all threads divided by the longest thread time. The facts sheet uses the sum over the threads of bytes / elapsed time. In the 9 bwx12 csv files of the rerun the largest difference of the two values is 0.018 GB/s, rounded to 3 decimal places (check 14 of the facts sheet). GB = 1e9 bytes [Ref1] [Ref7].
- **Order.** `asmread` runs directly after `oldread` in both rounds. In round 1 `oldread` runs directly after `read_1pl` of round 0. Between two intervals bwx12 prints the rows of the finished interval, reads the page state of all buffers, and runs one warm-up pass of the next kernel [Ref1].
- **No new read kernel in this line.** The kernel `read` is not in `--seq`. The facts sheet uses `asmread` in its place for part L and control I. `asmread` has the same 8 `ldp q` loads per 256 B. The facts sheet makes its statements from `oldread` and `asmread`. It lists the rates of `read_nop96`, `read_nop256` and `read_1pl` and makes no statement from them [Ref7].
- **Result that comes from this line.** Part L (3 processes, each started 5 s after the last 120-thread process of part A of its session): `oldread` gave 461.61 to 464.29 GB/s in 6 intervals. `asmread` gave 321.65 to 327.93 GB/s in 6 intervals. That is 29.2 % to 30.5 % below `oldread` of the same process and round. Control I (2 processes, each started from an idle machine): `oldread` gave 466.30 to 469.20 GB/s in 4 intervals. `asmread` gave 313.78 to 317.60 GB/s in 4 intervals. That is 31.9 % to 32.8 % below `oldread` of the same process and round [Ref7].
- **Same line in earlier runs.** The line is identical to line 1 of r8.spec [Ref8]. The 8000 MT/s baseline of part L in the facts sheet (row L-1) ran this line with the same bwx12 binary [Ref7]. The facts sheet lists 5 more earlier processes of this line: rows F72d12, X2d12, X1d10, X1d10b and BASEd10. Their launch lines hold the same argument line (compared for this page). Only row F72d12 ran in the boot of the rerun, at 7200 MT/s. It was launched at 20:02 UTC, about 2 h 10 min before go.sh started. It is not part of the rerun. There `asmread` gave 301.90 to 302.78 GB/s in 2 intervals. That is 35.4 % below `oldread` of the same round in both rounds [Ref7].
- **Buffers.** The line has no `--no-thp`. So bwx12 asks Linux for 2 MiB pages for every buffer. In the 9 bwx12 csv files of the rerun every `P` row shows the whole buffer (262144 kB) on 2 MiB pages (check 13 of the facts sheet) [Ref1] [Ref7].
- **Counters.** Each thread opens the six events for itself as one group, for user mode only [Ref1]. In the 5 csv files that this file produced, all 6000 `C` rows hold six event counts and no `NA` (counted for this page) [Ref9]. bwx12 prints `NA` for an event that Linux did not open [Ref1]. The analysis scripts of the rerun do not use the values. facts_data.py only counts the `C` rows, and stat_bwx.py does not read them [Ref11]. The facts sheet of the rerun does not describe the six events. No line of FACTS.md holds the text `cbusy` or `bus_access`. The meanings on this page come from the saved output of `perf list` on CRB [Ref5].
- **Type number 11.** Insufficient data: the type number of the counter unit in the boot of the rerun. The file `/sys/bus/event_source/devices/armv8_pmuv3_0/type`, read in that boot, would resolve it. The value 11 was read on 2026-11-13, in an earlier boot [Ref6] [Ref7]. A cross-check with the data was computed for this page. For each interval, the sum of the column `bus_access` over the 120 threads was divided by the number of 64 B lines (counted bytes / 64). The result is 2.07 to 2.12 counts per 64 B line in the 50 intervals that this file produced. It is 2.07 to 2.12 in all 74 bwx12 intervals of the rerun [Ref9]. The facts sheet of 2026-11-15 gives 2.08 for its runs [Ref10]. By the boot times in the facts sheet of the rerun, those runs were in the same earlier boot [Ref7]. The values are close. This is consistent with the assumption that type 11 selected the same counter unit in both boots. It is not a proof.
- **Checks that use this file.** go.sh and go2.sh stop before the first measurement when the file is missing or empty [Ref3] [Ref4]. After each step of rx.sh both scripts read launches.txt of the step. They stop unless it holds exactly one `rc` line and that line reads `rc 0` (exit status 0). So the file must start exactly one process [Ref3] [Ref4]. The facts sheet compares the tag and the arguments of every launch line with this file. They are equal in the 5 folders T72L1, T72L2, T72L3, T72I1 and T72I2 (check 15) [Ref7]. The file local.sha in the same folder holds the sha256 of this file.
- **More scripts that read this file after the run.** facts_text4.py and make_report.py read this file too. Each of them stops when one of its tests fails. facts_text4.py writes sections 4 to 6 of the facts sheet. It tests that the argument lines of the three spec files differ in the value of `--seq` only. It also tests that the launch line of row L-1 holds the arguments of this file [Ref13]. make_report.py builds the report of the rerun (the page whole-chip-rerun-7200.html). It tests that this file holds exactly one line, and it makes the same test of the three argument lines. It takes the tag `a6456` from this file to find the launch lines and the csv files of this line. It tests that the launch lines of 11 folders hold the arguments of this file: row L-1, the 3 folders of part L, the 2 folders of control I, and the rows F72d12, X2d12, X1d10, X1d10b and BASEd10 [Ref14]. On 2026-11-21 all of these tests hold (repeated with shell commands for this page).

## Call sequence in the whole-chip test

- `go.sh:runx`: sessions 1 to 3: starts rx.sh with like.spec as input (T72L1 to T72L3)
- `go2.sh:top level`: control I: starts rx.sh with like.spec as input, 2 times
  - `rx.sh:top level`: splits tag and arguments, starts bwx12, writes a6456.csv
    - `bwx12.c:main`: reads the 21 arguments, starts 120 workers, prints the csv rows
      - `bwx12.c:parse_long`: checks the numbers of --threads, --rounds and --pmu-type
      - `bwx12.c:parse_cpus`: builds the CPU list 0 to 119
      - `bwx12.c:parse_bytes`: turns 256M into 268435456 bytes
      - `bwx12.c:parse_seq`: looks up the 5 kernel names and keeps their order
      - `bwx12.c:parse_events`: stores the six event names and codes
      - `bwx12.c:worker`: one thread: pins, opens counters, allocates, times each kernel
        - `bwx12.c:pin_cpu`: pins the thread to its CPU of the list
        - `bwx12.c:open_counters`: opens the six events as one group of the thread
        - `bwx12.c:alloc_buf`: maps the 256 MiB buffer and asks for 2 MiB pages
        - `bwx12.c:k_write`: first write of the buffer by its own thread, not timed
        - `bwx12.c:call`: runs one kernel on a range of the buffer
          - `bwx12.c:k_oldread`: position 0: old read kernel, 16 running sums
          - `bwx12.c:k_asmread`: position 1: load-only loop, 8 ldp q per 256 B
          - `bwx12.c:k_read_nop96`: position 2: asmread loop with 96 nop per 256 B
          - `bwx12.c:k_read_nop256`: position 3: asmread loop with 256 nop per 256 B
          - `bwx12.c:k_read_1pl`: position 4: one 16 B load per 64 B line
- `build_facts.py:main`: after the run: builds the facts sheet
  - `build_facts.py:run_checks`: checks 15 and 16: launch lines against the spec files
  - `facts_text.py:render`: writes the text of the facts sheet
    - `facts_text4.py:section4`: tests the three argument lines and the launch line of row L-1
- `make_report.py:top level`: after the run: builds the report, tests launch lines against this file
  - `make_report.py:spec_line`: reads the one line: tag, arguments, kernel sequence
  - `make_report.py:launch_args`: reads the arguments of one launch line of launches.txt

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>The one line: a tag, then the arguments of bwx12</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1  a6456|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --seq oldread,asmread,read_nop96,read_nop256,read_1pl --count --pmu-type 11 --events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19</pre></td><td valign="top">One line for the runner script <code>rx.sh</code>: a tag, the character <code>|</code>, and the argument list of one bwx12 process. <code>rx.sh</code> passes the argument list without quotes. So the shell splits it at the spaces into 21 arguments [Ref2]. Each bullet below is one field or option, as the function <code>main</code> of <code>bwx12.c</code> reads it [Ref1].<ul><li><code>a6456</code>: the tag. <code>rx.sh</code> writes the standard output of the process to the file <code>a6456.csv</code>, and it writes the tag into <code>launches.txt</code>. bwx12 does not receive the tag.</li><li><code>--threads 120</code>: start 120 worker threads.</li><li><code>--cpus 0-63,64-119</code>: the CPU list 0 to 119. Thread number i is pinned to entry i of the list. So 64 threads run on mesh 0 (CPUs 0-63) and 56 threads run on mesh 1 (CPUs 64-119).</li><li><code>--bytes 256M</code>: the buffer size per thread, 256 MiB (268435456 bytes). Each thread allocates its own buffer and writes it once before the first interval. Every kernel of <code>--seq</code> works on this whole size.</li><li><code>--stop common</code>: all threads start an interval at one common start time and stop at one common deadline. A thread reads the clock after each chunk of 2 MiB. It stops at the first clock value that is not before the deadline.</li><li><code>--start common</code>: each thread starts every interval at byte 0 of its own buffer. The option sets the start position in the buffer, not the start time. It is also the default.</li><li><code>--min-ms 6000</code>: the length of a timed interval. The deadline is 6000 ms (6 s) after the common start time.</li><li><code>--rounds 2</code>: run the whole kernel sequence 2 times in the same process (round 0 and round 1).</li><li><code>--seq oldread,asmread,read_nop96,read_nop256,read_1pl</code>: the kernels to time, one interval each, in this order (positions 0 to 4). 5 kernels in 2 rounds give 10 timed intervals. <code>oldread</code> is the old read kernel. <code>asmread</code> is the hand-written load-only loop. The other three are test loops.</li><li><code>--count</code>: each thread also reads hardware counters directly before and directly after every interval. The csv file gets one <code>C</code> row per thread and interval.</li><li><code>--pmu-type 11</code>: the type number of the counter unit. bwx12 passes it to Linux in the field <code>type</code> of <code>perf_event_attr</code>. A listing from CRB of 2026-11-13 shows 11 as the type of <code>armv8_pmuv3_0</code>, the counter unit of the CPU cores [Ref6].</li><li><code>--events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19</code>: six events, each written as NAME=CODE. NAME is the column title in the <code>C</code> rows. CODE selects the event. Linux gets it in the field <code>config</code>. Codes 0x198 to 0x19b count the responses that the core received with busy level 0, 1, 2 and 3. The busy level is a number from 0 to 3 that the mesh sends to a core with each answer [Ref12]. Code 0x19c counts the responses with the flag "CBusy Multi-threaded" set. Code 0x19 counts bus accesses [Ref5].</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: source of bwx12. The argument parser is the first part of the function `main` (lines 2904 to 2998). The usage text is in `usage` (lines 1737 to 1748). The helpers are `parse_bytes` (lines 334 to 349), `parse_cpus` (388 to 413), `parse_seq` (1750 to 1767) and `parse_events` (1771 to 1793). `open_counters` (1582 to 1607), `worker` (1632 to 1735) and the output loop of `main` (3039 to 3122) show what each option does to a thread and to the csv file.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: runner script. Lines 11 to 20 read a spec line, split it at `|`, write the launch line, start bwx12 with the arguments, send its standard output to the file named by the tag, and write the `rc` line.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: driver script of the rerun. Lines 2 to 6 are the comment that names the three parts. Line 25 stops the run when a spec file is missing or empty. Lines 28 and 29 (function `rxok`) test that launches.txt of a step holds exactly one `rc` line with the status 0. Line 32 stops the run when this test fails. Lines 30 to 34 (function `runx`) and 40 to 46 start rx.sh with a spec file as its input.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sh`: script of control I. Line 20 stops the run when like.spec is missing or empty. Line 25 (function `waitidle`) waits until the 1-minute load average is below 1.0. Line 30 starts rx.sh with like.spec as its input, once per pass of a loop with 2 passes. Lines 23 and 31 make the same test of launches.txt as go.sh and stop the run when it fails.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/asct-prep-20261116T231215Z/perf-list-details.txt`: output of the command `perf list --details` on CRB, saved on 2026-11-16. Lines 1148 to 1150 hold `bus_access` (event 0x19). Lines 1240 to 1259 hold `l2_chi_cbusy0` to `l2_chi_cbusy_mt` (events 0x198 to 0x19c).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/results/partA-20261113T204939Z/A7-core-events.txt`: listing of the counter unit of the CRB cores, read from `/sys/bus/event_source/devices` on 2026-11-13. Line 1 holds `armv8_pmuv3_0 type=11`. Line 8 holds `bus_access:event=0x0019`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Used here: the word list (lines 38 to 89), the start times of the two boots (sections 1.2 and 1.5), the integrity checks 8, 12, 13, 14, 15, 16 and 19 (section 1.4), the results of part L, of control I and of row F72d12 (sections 0, 3.2 and 3.4), the table of earlier runs with the rows L-1, F72d12, X2d12, X1d10, X1d10b and BASEd10 (section 4.1), and the record of the three test loops (section 4.8).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/r8.spec`: spec file with five lines, in the folder of rx.sh. Its line 1 is identical to the line of like.spec (compared with the tool `cmp` for this page).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: output of the first process that used this file. Lines 1 to 6 are the header lines. In them bwx12 repeats its options. The counts on this page come from all 5 csv files that this spec file produced in the rerun, and from the 9 bwx12 csv files of the rerun where the text says so.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md`: facts sheet of the investigation of 2026-11-15. Line 113 gives 2.08 counts of `bus_access` per 64 B line.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: parser of the analysis scripts of the rerun. Lines 337 to 352 read the T, I and P rows and only count the C rows. stat_bwx.py in the same folder reads the T rows and the I rows only (its lines 52 to 57).
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/asct-2026-11-16/notes.py`: word list of the ASCT cross-check report of this project. Line 34 defines ASCT. Line 54 defines the busy level.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`: script that writes sections 4 to 6 of the facts sheet. Lines 121 to 126 of the function `section4` read the three spec files. They test that the three argument lines differ in `--seq` only and that the launch line of row L-1 holds the arguments of like.spec. The function `need` of facts_text.py (lines 36 to 38) ends the script when a test fails.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: script that builds the report of the rerun. The function `spec_line` (lines 1178 to 1185) reads a spec file and requires exactly one line with a `|`. The function `launch_args` (lines 1188 to 1192) reads the arguments of a launch line of launches.txt. Lines 1195 to 1203 read the three spec files, compare the three argument lines, and test the launch lines of 7 folders against like.spec: row L-1, part L, control I and row F72d12. Line 1312 makes this test for the rows X1d10, X1d10b, X2d12 and BASEd10. The function `need` (lines 46 to 49) ends the script when a test fails.
