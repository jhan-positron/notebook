# `cfwd.spec` explained

- Source file: `cfwd.spec` in this folder (text file, 1 lines, 246 bytes).
- sha256 of the source when this page was built: `cc04ea263193e6106a37ee7b238f878dd4a86312fcca7b14d821228ebc15e3d8`.
- Role in the whole-chip test: Argument line of part C, forward order: oldread, read, asmread in one process.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The file holds one line: a tag and the argument list of one bwx12 process, which the runner script rx.sh starts. The process pins 120 threads to CPUs 0 to 119 and times the old read kernel, the new read kernel and asmread in this order, for 6 s each, in 2 rounds (6 timed intervals).

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
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
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
- **Check 12, check 13, check 14, check 15**: numbered integrity checks in section 1.4 of the facts sheet. build_facts.py runs them and writes one line per check.
- **MiB**: 2^20 bytes (1048576 bytes). 256 MiB are 268435456 bytes.
- **GB**: 1e9 bytes.
- **Chunk**: 2 MiB of the buffer. With `--stop common` bwx12 calls the kernel on one chunk at a time and reads the clock after each chunk. After the last chunk of the buffer it goes on at byte 0.
- **Warm-up pass**: one call of the kernel on the whole buffer directly before its timed interval. It is not timed.
- **Counter unit (PMU)**: PMU means performance monitoring unit: the hardware event counters of a CPU core. Linux lists the unit of the CRB cores as the device `armv8_pmuv3_0` and gives it a type number [Ref5].
- **perf_event_attr**: the structure that a program hands to the Linux system call `perf_event_open` to open one counter. bwx12 fills the field `type` from `--pmu-type` and the field `config` from the CODE of `--events` [Ref1].
- **Busy level (CBusy)**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. The core counts the answers of each level. This is the definition of the ASCT cross-check report of this project [Ref10]. ASCT is the Arm System Characterization Tool, a tool of Arm for memory latency and bandwidth tests.
- **cbusy0, cbusy1, cbusy2, cbusy3**: column names that this line gives to the core events with the codes 0x198, 0x199, 0x19a and 0x19b. The tool `perf list` on CRB names them `l2_chi_cbusy0` to `l2_chi_cbusy3`. Its text for the first one is "Number of RXDAT or RXRSP response received with CBusy of 0". The other three texts end with 1, 2 and 3 [Ref4].
- **cbusy_mt**: column name for the core event with the code 0x19c. `perf list` on CRB names it `l2_chi_cbusy_mt` with the text "Number of RXDAT or RXRSP response received with CBusy Multi-threaded set" [Ref4]. Insufficient data: what the flag "Multi-threaded" means. The Arm documentation of this core event would resolve it.
- **bus_access**: column name for the core event with the code 0x19. `perf list` on CRB gives the text "Attributable Bus access" [Ref4].
- **RXDAT, RXRSP**: names in the event texts of `perf list`. By these texts they are the two kinds of response that carry the CBusy value [Ref4]. Insufficient data: their exact definition. The Arm documentation of these core events would resolve it.

</details>

## How to read this file

1. The line has two fields. The character `|` stands between them. rx.sh splits the line at the first `|` [Ref2] (line 1).
2. Field 1 is the tag `cfwd`. rx.sh uses it as the name of the csv file (`cfwd.csv`) and writes it into the two lines of launches.txt [Ref2]. The comment at the top of go.sh counts 2 forward and 2 reverse processes of part C. The 2 processes of this file are the forward ones [Ref3] (line 1).
3. Field 2 is the argument list of bwx12. rx.sh passes it without quotes. So the shell splits it at the spaces into 21 arguments [Ref2] (line 1).
4. The function `main` of bwx12.c reads the arguments from left to right. The table row of line 1 explains each one. When `main` does not know an option, it prints the usage text and ends the process with status 2 [Ref1].
5. go.sh starts rx.sh with this file as its input in sessions 1 and 3: folders T72C1 and T72C3 [Ref3].
6. bwx12 repeats the options in the first two lines of the csv file: `threads=120 bytes_per_thread=268435456 min_ms=6000` in line 1 and `seq=oldread,read,asmread rounds=2 stop=common start=common` in line 2. The header line of the `C` rows repeats the six event names, the type 11 and the six codes [Ref7].

## Behavior a reader must know

- **What is timed.** Each thread reads the clock when an interval starts and after every 2 MiB chunk. The last clock value ends the interval. Not timed: the first write of the buffer, one warm-up pass of each kernel over the whole buffer directly before its interval, the two counter readings, and the reading of the page state between two intervals [Ref1].
- **Start time.** With `--stop common` the main thread sets the common start time 2 ms after it released the workers. Each worker waits for that time in a loop that reads the clock. Then it reads the counters and reads the clock again. This clock value is the start of its interval. When it is more than 0.1 ms after the common start time, the `T` row of the thread gets the flag `late` [Ref1]. In the 9 bwx12 csv files of the rerun no `T` row has this flag (check 12 of the facts sheet) [Ref6].
- **Rate.** bwx12 counts 2 MiB for each chunk, for every kernel of this line. The `I` row of an interval holds the bytes of all threads divided by the longest thread time. The facts sheet uses the sum over the threads of bytes / elapsed time. In the 9 bwx12 csv files of the rerun the largest difference of the two values is 0.018 GB/s, rounded to 3 decimal places (check 14 of the facts sheet). GB = 1e9 bytes [Ref1] [Ref6].
- **Order.** Round 0: `oldread` is the first interval of the process, `read` runs directly after `oldread`, and `asmread` runs directly after `read`. Round 1: `oldread` runs directly after `asmread` of round 0, then the same order again. Between two intervals bwx12 prints the rows of the finished interval, reads the page state of all buffers, and runs one warm-up pass of the next kernel [Ref1].
- **Start state of the processes.** T72C1 and T72C3 were each launched 5 s after the end of the part L process of the same session. That process also runs 120 threads. The time stamps have a resolution of 1 s [Ref6].
- **Result that comes from this line.** The new read kernel `read`, directly after `oldread`, gave 320.89 to 324.98 GB/s in 4 intervals of 2 processes (T72C1, T72C3). That is 30.5 % to 31.2 % below `oldread` of the same process and round [Ref6].
- **Only the order differs from crev.spec.** The two files differ in the tag and in the value of `--seq`, and in nothing else (compared for this page). The facts sheet groups the intervals of part C by the kernel that ran directly before [Ref6].
- **No run of this line at 8000 MT/s.** The facts sheet states that the kernel `read` of bwx12 has no 8000 MT/s run [Ref6].
- **Buffers.** The line has no `--no-thp`. So bwx12 asks Linux for 2 MiB pages for every buffer. In the 9 bwx12 csv files of the rerun every `P` row shows the whole buffer (262144 kB) on 2 MiB pages (check 13 of the facts sheet) [Ref1] [Ref6].
- **Counters.** Each thread opens the six events for itself as one group, for user mode only [Ref1]. In the 2 csv files that this file produced, all 1440 `C` rows hold six event counts and no `NA` (counted for this page) [Ref7]. bwx12 prints `NA` for an event that Linux did not open [Ref1]. The analysis scripts of the rerun do not use the values. facts_data.py only counts the `C` rows, and stat_bwx.py does not read them [Ref9]. The facts sheet of the rerun does not describe the six events. No line of FACTS.md holds the text `cbusy` or `bus_access`. The meanings on this page come from the saved output of `perf list` on CRB [Ref4].
- **Type number 11.** Insufficient data: the type number of the counter unit in the boot of the rerun. The file `/sys/bus/event_source/devices/armv8_pmuv3_0/type`, read in that boot, would resolve it. The value 11 was read on 2026-11-13, in an earlier boot [Ref5] [Ref6]. A cross-check with the data was computed for this page. For each interval, the sum of the column `bus_access` over the 120 threads was divided by the number of 64 B lines (counted bytes / 64). The result is 2.08 to 2.09 counts per 64 B line in the 12 intervals that this file produced. It is 2.07 to 2.12 in all 74 bwx12 intervals of the rerun [Ref7]. The facts sheet of 2026-11-15 gives 2.08 for its runs [Ref8]. By the boot times in the facts sheet of the rerun, those runs were in the same earlier boot [Ref6]. The values are close. This is consistent with the assumption that type 11 selected the same counter unit in both boots. It is not a proof.
- **Checks that use this file.** go.sh stops before the first measurement when the file is missing or empty [Ref3]. After each step of rx.sh, go.sh reads launches.txt of the step. It stops unless it holds exactly one `rc` line and that line reads `rc 0` (exit status 0). So the file must start exactly one process [Ref3]. The facts sheet compares the tag and the arguments of every launch line with this file. They are equal in the 2 folders T72C1 and T72C3 (check 15) [Ref6]. The file local.sha in the same folder holds the sha256 of this file.
- **More scripts that read this file after the run.** facts_text4.py and make_report.py read this file too. Each of them stops when one of its tests fails. facts_text4.py writes sections 4 to 6 of the facts sheet. It tests that the argument lines of the three spec files differ in the value of `--seq` only [Ref11]. make_report.py builds the report of the rerun (the page whole-chip-rerun-7200.html). It tests that this file holds exactly one line, and it makes the same test of the three argument lines. It tests that the launch lines of the folders T72C1 and T72C3 hold the arguments of this file. It also searches every csv file under `results` (the folder that holds the result folders copied back from CRB) for the header line that holds the kernel sequence. It tests that the 4 part C folders, and no other folder, hold a csv file with the kernel sequence of this file or of crev.spec [Ref12]. On 2026-11-21 all of these tests hold (repeated with shell commands for this page).

## Call sequence in the whole-chip test

- `go.sh:runx`: sessions 1 and 3: starts rx.sh with cfwd.spec as input (T72C1, T72C3)
  - `rx.sh:top level`: splits tag and arguments, starts bwx12, writes cfwd.csv
    - `bwx12.c:main`: reads the 21 arguments, starts 120 workers, prints the csv rows
      - `bwx12.c:parse_long`: checks the numbers of --threads, --rounds and --pmu-type
      - `bwx12.c:parse_cpus`: builds the CPU list 0 to 119
      - `bwx12.c:parse_bytes`: turns 256M into 268435456 bytes
      - `bwx12.c:parse_seq`: looks up the 3 kernel names and keeps their order
      - `bwx12.c:parse_events`: stores the six event names and codes
      - `bwx12.c:worker`: one thread: pins, opens counters, allocates, times each kernel
        - `bwx12.c:pin_cpu`: pins the thread to its CPU of the list
        - `bwx12.c:open_counters`: opens the six events as one group of the thread
        - `bwx12.c:alloc_buf`: maps the 256 MiB buffer and asks for 2 MiB pages
        - `bwx12.c:k_write`: first write of the buffer by its own thread, not timed
        - `bwx12.c:call`: runs one kernel on a range of the buffer
          - `bwx12.c:k_oldread`: position 0: old read kernel, 16 running sums
          - `bwx12.c:k_read`: position 1: new read kernel, loads only
          - `bwx12.c:k_asmread`: position 2: load-only loop, 8 ldp q per 256 B
- `build_facts.py:main`: after the run: builds the facts sheet
  - `build_facts.py:run_checks`: check 15: launch lines against the spec files
  - `facts_text.py:render`: writes the text of the facts sheet
    - `facts_text4.py:section4`: tests that the three argument lines differ in --seq only
- `make_report.py:top level`: after the run: builds the report, tests launch lines against this file
  - `make_report.py:spec_line`: reads the one line: tag, arguments, kernel sequence
  - `make_report.py:launch_args`: reads the arguments of one launch line of launches.txt

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/cfwd.spec` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1 lines, 246 bytes, sha256 `cc04ea263193e6106a37ee7b238f878dd4a86312fcca7b14d821228ebc15e3d8`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/cfwd.spec`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `cfwd\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --seq oldread,read,asmread --count --pmu-type 11 --events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19` | One spec line: the tag, a `\|` character, then the 21 arguments of one `bwx12` process [Ref2] [Ref1]. `cfwd`: the tag. It names the output file `cfwd.csv`. `bwx12` does not receive it. `--threads 120`: 120 threads. `--cpus 0-63,64-119`: thread i is pinned to entry i of this list. So 64 threads run on mesh 0 and 56 on mesh 1. `--bytes 256M`: each thread writes its own buffer of 256 MiB (268435456 bytes) once before the first interval. Every kernel works on the whole buffer. `--stop common`: all threads start an interval at one common time. A thread reads the clock after each 2 MiB chunk. It stops at the first value that is not before the common deadline. `--start common`: each thread starts every interval at byte 0 of its buffer. This is a position, not a time. It is the default. `--min-ms 6000`: the deadline is 6000 ms (6 s) after the common start time. `--rounds 2`: the kernel sequence runs 2 times. `--seq`: the 3 kernels to time, one interval each, in this order. 2 rounds give 6 timed intervals. `--count`: each thread reads hardware counters directly before and after each interval. `--pmu-type 11`: the type number of the counter unit. A listing from CRB of 2026-11-13 shows 11 for the cores [Ref5]. `--events`: six events as NAME=CODE. NAME is the column title in the `C` rows. In this order they count the responses to the core with busy level 0, 1, 2 and 3, those with the flag `CBusy Multi-threaded`, and bus accesses [Ref4]. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: source of bwx12. The argument parser is the first part of the function `main` (lines 2904 to 2998). The usage text is in `usage` (lines 1737 to 1748). The helpers are `parse_bytes` (lines 334 to 349), `parse_cpus` (388 to 413), `parse_seq` (1750 to 1767) and `parse_events` (1771 to 1793). `open_counters` (1582 to 1607), `worker` (1632 to 1735) and the output loop of `main` (3039 to 3122) show what each option does to a thread and to the csv file.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: runner script. Lines 11 to 20 read a spec line, split it at `|`, write the launch line, start bwx12 with the arguments, send its standard output to the file named by the tag, and write the `rc` line.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: driver script of the rerun. Lines 2 to 6 are the comment that names the three parts. Line 25 stops the run when a spec file is missing or empty. Lines 28 and 29 (function `rxok`) test that launches.txt of a step holds exactly one `rc` line with the status 0. Line 32 stops the run when this test fails. Lines 30 to 34 (function `runx`) and 40 to 46 start rx.sh with a spec file as its input.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/asct-prep-20261116T231215Z/perf-list-details.txt`: output of the command `perf list --details` on CRB, saved on 2026-11-16. Lines 1148 to 1150 hold `bus_access` (event 0x19). Lines 1240 to 1259 hold `l2_chi_cbusy0` to `l2_chi_cbusy_mt` (events 0x198 to 0x19c).
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/partA-20261113T204939Z/A7-core-events.txt`: listing of the counter unit of the CRB cores, read from `/sys/bus/event_source/devices` on 2026-11-13. Line 1 holds `armv8_pmuv3_0 type=11`. Line 8 holds `bus_access:event=0x0019`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Used here: the word list (lines 38 to 89), the launch times of the steps (section 1.1), the start times of the two boots (sections 1.2 and 1.5), the integrity checks 8, 12, 13, 14 and 15 (section 1.4), the results of part C (section 3.3), and the statement that the bwx12 kernel `read` has no 8000 MT/s run (sections 0 and 6).
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72C1-20261117T221436Z/cfwd.csv`: output of the first process that used this file. Lines 1 to 6 are the header lines. In them bwx12 repeats its options. The counts on this page come from all 2 csv files that this spec file produced in the rerun, and from the 9 bwx12 csv files of the rerun where the text says so.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md`: facts sheet of the investigation of 2026-11-15. Line 113 gives 2.08 counts of `bus_access` per 64 B line.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: parser of the analysis scripts of the rerun. Lines 337 to 352 read the T, I and P rows and only count the C rows. stat_bwx.py in the same folder reads the T rows and the I rows only (its lines 52 to 57).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/asct-2026-11-16/notes.py`: word list of the ASCT cross-check report of this project. Line 34 defines ASCT. Line 54 defines the busy level.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`: script that writes sections 4 to 6 of the facts sheet. Lines 121 to 126 of the function `section4` read the three spec files. They test that the three argument lines differ in `--seq` only. The function `need` of facts_text.py (lines 36 to 38) ends the script when a test fails.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: script that builds the report of the rerun. The function `spec_line` (lines 1178 to 1185) reads a spec file and requires exactly one line with a `|`. The function `launch_args` (lines 1188 to 1192) reads the arguments of a launch line of launches.txt. Lines 1195 to 1199 read the three spec files and compare the three argument lines. Lines 1204 to 1207 test the launch line of each part C folder against the spec file that has the name of its csv file. Lines 1208 to 1224 search every csv file under `results` for the header line with the kernel sequence and test which folders hold a part C kernel sequence. The function `need` (lines 46 to 49) ends the script when a test fails.
