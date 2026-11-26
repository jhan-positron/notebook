# `facts_text4.py` explained

- Source file: `facts_text4.py` in this folder (Python script, 1615 lines, 133217 bytes).
- sha256 of the source when this page was built: `8eb812fd9a3c41aadad89a7faca46c1bd937999d407de964be7339031fc9feb7`.
- Role in the whole-chip test: Analysis module: compares 7200 with 8000 MT/s rates, writes FACTS.md sections 4 to 6
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

The file defines the function `section4`, which writes sections 4, 5 and 6 of the facts sheet `FACTS.md` and the Q2 entries of the verdict object of `facts.json`. The function compares the rates in GB/s of the 7200 MT/s rerun with the rates of the earlier 8000 MT/s runs, by the rules that were fixed before the run.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
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
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Idle start**: a launch at a 1-minute load average below 1.0.
- **Visit**: one time at which the same line was run. A later visit is the same line run again at a later time.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule of the bwx runners in the rows used here: all threads stop at the same time. The interval length (`min_ms`) is 4 s in rows L-2, L-3, L-4 and R0b. It is 6 s in every other bwx row of this file.
- **Pass count**: total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. The records hold it in the field `passes`.
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **Load average, load at launch**: the load average is the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes. "Load at launch" is the 1-minute value read directly before a process starts. The code names it `load1` or `load1_at_launch`.
- **%CPU**: the column pcpu of the tool ps in the process lists of env.txt. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process.
- **Boot, boot id**: a boot is one run of Linux from its start to its shutdown. The boot id is a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **Boot label**: the text in the field `boot` of an 8000 MT/s record, for example `boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)`. It gives the boot number of the DIMM report and the start time of Linux. A 7200 MT/s record holds the boot id in this field.
- **`speed_MTps`, `modules`, `boot`**: fields of a record: the memory speed in MT/s, the number of memory modules and the boot. `build_facts.py` sets the three fields. It does not read them from the files of the run folder. For an 8000 MT/s row they come from the DIMM report, for the time in the name of the run folder. A record of the rerun, of control I or of F72d12 gets the memory speed, the number of DIMM sockets and the boot id of try6.txt. An integrity check of `build_facts.py` compares the boot id of every state line and of every probe.txt with the boot id of try6.txt [Ref3]. probe.txt is the file that ra.sh (the script that runs part A) writes into a part A folder. It holds the boot id, MemTotal, the load and the sha256 of the two binaries.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **Journal**: the log store of Linux. It keeps the Linux kernel log of earlier boots.
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the Linux kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues). In the code one record is one journal line "Hardware error from APEI ...".
- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory settings. They were changed for another investigation.
- **rc**: the exit status of a process. 0 means success.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Baseline, like-for-like**: an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.
- **Supporting row, other-binary row**: earlier 8000 MT/s runs that differ in interval length or counter setup (supporting), or that used another runner binary (other binary).
- **n**: the number of measurements that a range comes from. It is written as intervals / processes / sessions / boots (rule V1 point 1).
- **est.**: estimated, not measured directly.
- **GB**: 1e9 bytes. GB/s is the unit of every rate.
- **Q1**: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much.
- **Q2**: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.
- **Drop (Q1)**: (1 - rate of the load-only kernel / rate of oldread) x 100, in percent. Both intervals come from the same bwx12 process and round. `facts_text.py` computes it. `c['dl']`, `c['di']`, `c['df']` and the second element of each `CG` entry hold these values.
- **Rerun**: the run of 2026-11-17 at 7200 MT/s by the driver script go.sh: three sessions with parts A, L and C, and one more part C process. The records of these parts have a `dataset` that starts with `rerun-`. Control I was run afterwards by the second driver script go2.sh. Its records have the dataset `control-I`.
- **FACTS.md, facts sheet, "this sheet"**: the Markdown file `S/FACTS.md` that `build_facts.py` writes. It is the source for the report of the rerun. The text templates call it "this sheet".
- **Present sheet, present values**: the file S/FACTS.md as it is now in the folder (file time 2026-11-18 04:55 UTC). Values quoted from it are examples of what the code printed with the present data [Ref4].
- **facts.json**: the second output of `build_facts.py`: every interval as one record, plus the objects "meta" and "verdicts".
- **R, S, W15**: folders. R is the results folder `crb/results`. S is the folder of this file, `crb/tmp/agent-scratch/w120-7200-2026-11-17`. W15 is the folder of the 2026-11-15 investigation, `crb/tmp/agent-scratch/w120-2026-11-15`.
- **like.spec, cfwd.spec, crev.spec**: the three argument lines of bwx12 in folder S. like.spec is the line of part L and of control I. cfwd.spec and crev.spec are the two lines of part C. The three lines differ only in the kernel sequence after `--seq`.
- **launches.txt, env.txt**: files that the runner script rx.sh writes into a run folder. launches.txt holds one launch line directly before a process starts (time, load averages, arguments) and one rc line after it ends (exit status, time). env.txt holds the date, the Linux release, the load, a process list and the sha256 of the binary. r0.sh is the runner script of row R0. It writes the same two files. Its env.txt holds no sha256 of the binary.
- **f72la, fenv**: `f72la` is the launch line of the F72d12 process (tag a6456) from its launches.txt: time, load averages, arguments, and the time of the rc line. `fenv` is the parsed env.txt of the F72d12 folder: `start` (its date line), `top` (the process list as user, %CPU, command, line number) and `n_lines` (the number of lines of the file). Both are set in lines 38 and 39.
- **try6.txt, boots.txt, gaps.txt**: records in `R/dimm7200-20261117`. try6.txt holds the reading of 12 modules at 7200 MT/s with the boot id of the rerun. boots.txt and gaps.txt number the boots of the journal. Their row 0 is the boot of try6.txt, with its first and last time.
- **First Linux kernel log line of the boot**: the time after `first=` in row 0 of gaps.txt, stored as `try6['first_log_utc']`. The code uses it as the start of the boot when it prints a time since boot.
- **uptime line of gaps.txt**: the output line of the Linux command `uptime` in gaps.txt. It holds the time of day at which gaps.txt was written (`try6['gaps_uptime_utc']`). The process-list lines after it are stored as `try6['gaps_top']`.
- **DIMM report**: the file `machines/arm-crb/DIMM-flaky-report.md`. It holds the boot history of CRB with the module count of each boot (`fd.DIMM_REPORT`).
- **FINDINGS.md**: the facts sheet of the investigation of 2026-11-15 into the drop of the read rate, in folder W15.
- **Rules V1 to V4, F1, F2**: the comparison rules in `S/baselines-and-rules.txt`, written before go.sh started. V1: the overlap test of 7200 MT/s against 8000 MT/s and its wording. V2: part C is grouped by the kernel that ran directly before. V3: part A, load-only kernels, wording inside or outside, no percent. V4: the fixed list of 8000 MT/s baselines. F1: the row labels and the 8000 MT/s reference of part A. F2: the bwx12 kernel read has no 8000 MT/s run [Ref5].
- **Decision (r), decision (p)**: decisions of the agent, listed in section 2 of FACTS.md. Decision (r): the sheet follows rules V1, V2 and V4 and compares part C with 8000 MT/s rows, although rule F2 points 2 and 3 would present part C at 7200 MT/s only. Decision (p): which processes of runner bwx serve as the reference of part C.
- **D**: the dict of collected data from `build_facts.py`. Keys used here: `recs` (the interval records), `rx` (run folders written by rx.sh or r0.sh, by row name), `step` (folders of runner bwx, by row name), `base` (the part A baselines A-1 to A-3), `X` (the bwx12 processes of parts L and C and of control I), `hw` and `hw_cmp` (hardware error records), `try6` (try6.txt, boots.txt and gaps.txt), `logs` (state lines of go.sh and go2.sh), `probe13` (records of the 2026-11-13 run and the path of the saved journal), `checks` (the integrity checks).
- **N**: the dict of statistics from the function `analyse` of `facts_text.py`. Used here: `N['pa']` (part A, one entry per session and round with the `bw_old read` records `old` and the `bw_new read` records `new`) and `N['pool']` (a function that returns the records of several rows for one kernel and position).
- **V**: the verdict object, a dict. `build_facts.py` writes it to `facts.json` under the key "verdicts".
- **L, w**: `L` is the list of the text lines of FACTS.md. `w` is `L.append`: it adds one line.
- **c**: the context dict from the function `render` of `facts_text.py`. It holds record lists, comparisons and short texts of sections 1 to 3. `section4` also stores its own results in it.
- **c['mesh'], c['dist'], c['f72_limit']**: values that `section4` stores in `c`: `c['mesh']` in line 1260, `c['dist']` in line 1152 and `c['f72_limit']` in line 1308. `c['dist']`: the six asmread distances of section 4.6. `c['mesh']`: three interval counts of section 4.7. `c['f72_limit']`: one sentence on the limit of F72d12 as an idle start.
- **ref**: `ref(path)` returns the label `[RefN]` of a file in the file list of section 7 of FACTS.md.
- **q2row**: a function of `render` in `facts_text.py`. It appends one range test to `V['q2_rows']`: both ranges, both n, the overlap flag, the distance, and the wording when `decides` is true.
- **need**: `need(condition, text)` stops the build with an error message when the condition is false.
- **The build**: one run of `build_facts.py`, which calls `render` and `section4` and writes FACTS.md and facts.json. "The build stops" means that `need` ends this run with an error message. The run then writes no FACTS.md and no facts.json.
- **Integrity check**: a test that `build_facts.py` runs on the raw files and on the scripts before the text of the sheet is built. `D['checks']` holds one result per check. Line 1461 stops the build unless every check passed. Section 1.4 of the present sheet lists 27 checks, all with the result `pass` [Ref3] [Ref4]. Since 2026-11-24 a new build stops at line 1461. Check 20 (key `sha-local`) fails then. It compares the sha256 of go.sh and of five other local scripts and spec files with the lists `local.sha` and `go2.sha`. Line 20 of go.sh was edited on 2026-11-24. So go.sh no longer has the sha256 that `local.sha` lists for it. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit.
- **Record, interval record**: one dict per interval in `D['recs']`. Fields used in this file: `dataset`, `binary`, `binary_sha256`, `kernel`, `kernel_before`, `round`, `pos`, `session`, `tag`, `proc_key`, `GBps`, `mesh0_GBps`, `mesh1_GBps`, `passes`, `per_thread_avg_GBps`, `speed_MTps`, `modules`, `boot`, `load1_at_launch`, `min_ms`, `stop`, `start`, `count`, `folder`, `file`, `line`.
- **GBps**: field of a record: the rate of one interval in GB/s. Part A: the column `aggregate_GBps` of the csv file. bwx runners: the sum over the T rows (threads) of bytes / elapsed_s / 1e9.
- **mesh0_GBps, mesh1_GBps**: fields of a bwx record: the sum of the thread rates on CPUs 0-63 and on CPUs 64-127. Their sum is `GBps`.
- **per_thread_avg_GBps**: field of a part A record: the column of the same name in the csv file. It is the average rate of the 120 threads of the interval, rounded to 0.01 GB/s.
- **proc_key**: field of a record: one value per process. `rng` counts the processes of a list with it.
- **kernel_before**: field of a bwx record: the kernel that was timed directly before in the same process. For the first interval of a process it is the text "none (first interval of the process)" (`FIRST`). `facts_data.py` takes the value from the kernel sequence in the header line `# bwx:` of the csv file (`seq=`). It does not compare the times of the intervals [Ref2]. In a part A record the field names the process before it in the csv file. This file does not read it there.
- **pos**: field of a bwx record: the position of the kernel in the sequence, counted from 0.
- **min_ms, stop, start, count**: fields of a record. `min_ms`: the least length of an interval in ms (option `--min-ms`). The sheet prints it as the interval length. `stop`: the stop rule. For a part A record `build_facts.py` sets `min_ms` to the constant 500 and `stop` to the constant `whole pass`. It does not read them from the csv file. For a bwx record both values come from the header lines that the binary prints into the csv file [Ref2] [Ref3]. `start`: the value of the runner option `--start` (`common` or `offset`). `count`: 1 when the run read core counters.
- **Tag**: the short name of a run folder or of a process. Rerun: T72A1 to T72A3 (the part A folders of sessions 1 to 3), T72L1 to T72L3 (part L), T72C1 to T72C4 (part C, T72C4 ran after the three sessions). Control I: T72I1 and T72I2. Earlier bwx12 and bwx11 folders: the name of the csv file without `.csv`, for example a6456 or p2add. Runner bwx: the tag of the `-- step` line, for example common-6000-common-p1. Rows A-2 and A-3: the tag of the `-- step` line of the process, for example onebuf-ms500-1. Row A-1 has no tag.
- **`-- step` line**: a header line of a csv file that starts with `-- step`. The run script writes it directly before it starts a process: run_bwx.sh for runner bwx, run_partA.sh for A1.csv and A3.csv. It holds the tag, the binary, the load averages, the time and the arguments of the process.
- **dataset, row**: field `dataset` of a record names the row that the record belongs to. A row is one group of processes. Rows of the rerun: `rerun-A`, `rerun-L`, `rerun-C`. Row of control I: `control-I`. Rows of earlier runs have the names below.
- **A-1, A-2, A-3**: the 8000 MT/s baseline rows of part A, all of 2026-11-13. A-1: `threads120.csv` of the folder kernels-20261113T181222Z, same process order as part A. A-2: `A1.csv` of the folder partA-20261113T205055Z, same binaries, other process order. The code labels its arguments as the same (line 94). The `-- step` lines of A1.csv show two differences from part A. The CPU list is written `0-63,64-119` in place of `0-119`. The option `--per-thread` is added: the binary prints one more line per thread and interval. A-3: `A3.csv` of the same folder, bw_old read only.
- **L-1, L-2, L-3, L-4 (`BW12`)**: the bwx12 rows at 8000 MT/s. L-1 is the baseline: one process with the argument line of like.spec (folder w120-R8). L-2 to L-4 are supporting rows (folders w120-R1, w120-R5, w120-R6): 4 s intervals and other counter events.
- **R0, R0b (`BW11`)**: rows of the other binary bwx11 at 8000 MT/s (folders w120-R0 and w120-R0b).
- **B7a, B7b, C3a, C3b (`BWX`)**: rows of the first runner bwx at 8000 MT/s: the processes with the tags `common-6000-*` in two B7 folders and two C3 folders of 2026-11-13 and 2026-11-14.
- **B5a, B5b, B5a-rev, B5b-rev**: rows of runner bwx from two B5 folders of 2026-11-14. Rows B5a and B5b hold the processes with the tags `b5-fwd-*`. Rows B5a-rev and B5b-rev hold the processes with the tags `b5-rev-*`, which ran the kernels in the reverse order.
- **X2d12**: a 12-module run with a firmware test setting. It is shown and not used as a baseline. One check also uses its two oldread intervals. Line 607 tests that the highest oldread rate of part L lies below every oldread record at 8000 MT/s with 12 modules (list `allo`, line 604).
- **X1d10, X1d10b, BASEd10**: runs in boots with 10 memory modules. The row table of section 4.1 lists them. Lines 197 to 201 compare their oldread rates with the DIMM report. Lines 1191 to 1210 use them for the texts of rule V1 points 3 and 4. No range test uses them.
- **F72d12**: one bwx12 process with the argument line of like.spec, run in the boot of the rerun at 7200 MT/s, before the rerun. It is a sample of the same boot. It is not a baseline and not part of the rerun.
- **Pool**: the intervals of several rows taken together as one list. Each pool holds the intervals of one kernel. Example: "pool L-1 to L-4" for oldread is `P12o`, every oldread interval at position 0 of rows L-1, L-2, L-3 and L-4.
- **Record lists of `c`**: `A72o`: `bw_old read` of part A. `A80o`: `bw_old read` of rows A-1 to A-3. `L72o`, `L72a`: oldread and asmread of part L. `I72o`, `I72a`: the same of control I. `F72o`, `F72a`: the same of row F72d12. `C72o`: oldread of part C. `P12o`, `P12a`: oldread at position 0 and asmread at position 1 of rows L-1 to L-4. `PALLo`, `PALLa`: the same with rows R0 and R0b added. In these names 72 stands for 7200 MT/s, 80 for 8000 MT/s, o for the old read kernel and a for asmread.
- **Range**: the dict that `rng` returns for a list of records: `lo` (lowest value), `hi` (highest value), `med` (median), `n` (number of intervals), `procs` (number of processes), `sessions` and `boots`. The value is `GBps` unless another field is named.
- **Median**: the middle value of a sorted list (Python `statistics.median`). For an even number of values it is the mean of the two middle values.
- **Half up**: the rounding rule of `g`, `sp`, `pc` and `_q`: a value exactly between two steps is rounded away from zero. `_q` rounds the value to 6 decimal places before it applies the rule.
- **Comparison**: the dict that `compare(r72, r80)` returns: `a` (range of the 7200 MT/s records), `b` (range of the 8000 MT/s records), `overlap`, `dist`, `wording` and `width`.
- **Comparisons of `c`**: `cLo`, `cLa`: part L against the pool L-1 to L-4, for oldread and for asmread. `cIo`, `cIa`: control I against the same pool. `cFo`, `cFa`: F72d12 against the same pool. `cAo`: `A72o` against `A80o`. `cCo`: `C72o` against `P12o`.
- **Ranges overlap**: two min-to-max ranges share at least one value.
- **Distance of the nearest ends, `dist`**: for two ranges that do not overlap: the lowest value of the higher range minus the highest value of the lower range, in GB/s. In the code the sign is positive when the first range given to `compare` is the higher one. In a test against 8000 MT/s the first range is the 7200 MT/s range. The value is 0 when the ranges overlap.
- **Farthest ends**: for two ranges: the highest value of the higher range minus the lowest value of the lower range, in GB/s. In the code: `far` (line 489), `far_boot` and `far_pool` (line 1148).
- **Width, `width`**: the width of a range in percent of its lower end: (hi - lo) / lo x 100. For an 8000 MT/s range, rule V1 point 2 calls it the size that the test cannot exclude.
- **Wording**: the fixed text that rule V1 point 2 gives to a test. `SAME` = "no difference seen" when the ranges overlap. `DIFFERS` = "differs between the 8000 MT/s boot and the 7200 MT/s boot" when they do not.
- **Scope, decides**: in `cmps`, a scope is one 8000 MT/s record list that a 7200 MT/s row is tested against, for example "L-1 alone" or "pool L-1 to L-4". `decides` is a flag of the scope. True: the wording of this test is the result of the row. False: the test is printed without a wording.
- **Deciding test**: the range test of a 7200 MT/s row against the scope that has `decides` = True. Only this test gets a wording by rule V1 point 2.
- **pa3, newread**: `pa3` is a list of 6 cells from `facts_text.py` for rule V3: bw_new read, bw_new asmread and bw_old asmread, each in round 1 and round 2. A cell holds the 3 intervals of session 1 (`s1`), the 3 intervals of row A-1 (`a1`) and the intervals of row A-2 (`a2`: 3 intervals, or none for bw_old asmread). `b80` is the 8000 MT/s range of the round: the range of the intervals of `a1` and `a2` together. The cell also holds the distances of the session-1 intervals that lie above this range (`above`) or below it (`below`), and the number that lie inside it (`inside`). `newread` holds the two cells of bw_new read.
- **CG**: the load-only intervals of part C in five groups, by the kernel that ran directly before (rule V2): read after oldread, read after asmread, asmread after read, asmread first, asmread after oldread. Each entry is a pair: the records, and their percent drops against oldread of the same process and round.
- **evd**: a dict by tag of the steps that go.sh and go2.sh ran: one entry per part A folder and one per bwx12 process. Fields used here: `part` (A, L, C or I), `tag`, `state` (text of the start state), `gap_s` (seconds between the end of the entry before and this launch), `load1` (load at launch), `first` (launch time, for part A of its first process), `prev` (the entry before).
- **Start state**: what the machine did before a launch. The code describes it by the load at launch and by the time since the previous 120-thread process ended.
- **`idle` group, `busy` group**: the two start-state groups of the processes of rows L-1 to L-4 (lines 533 and 534). `idle`: launched at a 1-minute load average below 1.0. `busy`: every other process. The checks in lines 536 to 538 show that each `busy` process was launched at most 30 s after a process with `--threads 120` ended.
- **`Io`, `Bo`, `Ia`, `Ba`**: record lists of the start-state view (line 540). `Io`, `Bo`: oldread at position 0 of the groups `idle` and `busy`. `Ia`, `Ba`: asmread at position 1 of the two groups. `aIo`, `aBo`, `aIa`, `aBa` are their ranges.
- **Window of a process**: the time from the launch line to the rc line of the process in launches.txt. Both lines give whole seconds.
- **inside, possible, outside**: the three positions of a hardware error record against an interval (`kind`). The journal and launches.txt give whole seconds. So the code gives a record a span of 2 s: from N - 1 to N + 1 seconds after the process start, where N is the journal time minus the time of the launch line. Inside: the whole span lies in the interval. Possible: the span and the interval share a part. The text prints it as "before or inside". Outside: neither.
- **Used intervals**: in the block on hardware error records: the intervals that the sheet uses, oldread at position 0 and asmread at position 1, in each round of a process.
- **Other round**: the interval of the same kernel at the same position in the other round of the same process. The processes of this comparison have two rounds, 0 and 1.
- **hw, hw_cmp**: `D['hw']` holds one entry per process of rows L-1 to L-4, R0 and R0b with the error records in its window. `D['hw_cmp']` holds three lists. `rows`: intervals to which records can be assigned. `border`: records at the border of two intervals. `clean`: positions of the processes with records at which neither round has a record inside it or at its border.
- **diff**: field of an entry of `D['hw_cmp']`, in GB/s. In `rows` and in the `intervals` of a `border` entry it is the rate of the interval minus the rate of its other round. In `clean` it is the rate of round 1 minus the rate of round 0.
- **`total` (field of an interval)**: field of an interval of a bwx csv file, as `D['hw']` and `D['hw_cmp']` hold it: the sum over its T rows of bytes / elapsed_s / 1e9, in GB/s. The interval record holds the same value as `GBps`.
- **--start common, --start offset**: two values of the runner option `--start`. This file does not say what the option does. It only keeps the processes of the two values apart (`scm`).
- **120 x average**: an estimate (est.) of the sum of the thread rates of a part A interval: 120 threads times `per_thread_avg_GBps`. The column is rounded to 0.01 GB/s. So the estimate is exact to 0.6 GB/s.
- **Fixed texts**: constants from `facts_text.py` that the templates insert. `ADDED` = "added after the first numbers were seen". `NOT_PLAN` = "not part of the plan fixed before the run". `NO_READ` = "Insufficient data: no 8000 MT/s run of kernel read with bwx12". `STANDIN` says that asmread is used in place of the new read kernel. `F2_NOTE` names decision (r). `H1_MEAS` names the measurement of hypothesis H1. Two more constants are set in this file (lines 14 and 15). `OWN` ends the table label of the rows F72d12 and control I. `OLD_OWN` ends their key in `facts.json`.
- **Template text**: the words of a `w(...)` line or of another text template that are written as they stand in the code. No value from the data is inserted into them.
- **Fixed words**: a text template without a placeholder for a measured value. The code prints it unchanged, or with a fixed label such as `ADDED`.
- **H1 to H5**: the five hypotheses of section 6: start state, time since boot, memory speed, pass counts in part A, load values. None of them is tested.

</details>

## Main flow

1. The module imports helper functions and fixed texts from `facts_data.py` and `facts_text.py`, and it sets two labels for the rows F72d12 and control I. It has no command line and it does no work when it is imported. `facts_text.py` calls `section4` once, after it has written the title lines, the heading of section 0 and sections 1 to 3. It writes the text of section 0 after the call [Ref1] (lines 1-15).
2. The function `secs` is defined. It prints the interval lengths of a record list, for example `6 s` (lines 18-21).
3. `section4` starts. It takes the collected data `D`, the statistics `N`, the verdict object `V`, the list of output lines `L`, the reference function `ref`, the row writer `q2row` and the context `c`. It unpacks the record lists and the comparisons that `facts_text.py` prepared, for example `L72o`, `P12o` and `cLo` (lines 24-42).
4. Four local helpers are defined: `src` (reference labels of the csv files of a record list), `ranges` (a table with one min-to-max range per row), `source` (the Source cell of the row table) and `cmps` (the table of the overlap tests, which also stores each test for `facts.json`) (lines 44-90).
5. One description text per earlier row is set (`DESC`). The three argument lines like.spec, cfwd.spec and crev.spec are read. The build stops unless they differ only in the value of `--seq` and row L-1 ran the line of like.spec (lines 92-127).
6. Section 4.1, rules and rows. The rule summary is written. The build stops unless rows A-1 to A-3, L-1 to L-4, R0, R0b, B7a, B7b, C3a, C3b, B5a and B5b share one boot label and every 7200 MT/s record holds the boot id of try6.txt. The second part of this check tests no file of the run. `build_facts.py` copies the boot id of try6.txt into every 7200 MT/s record [Ref3]. Rows X2d12, X1d10, X1d10b and BASEd10 are 8000 MT/s rows of other boots, and this check leaves them out. It also leaves out rows B5a-rev and B5b-rev, which come from the same two folders as B5a and B5b. A table of the 22 earlier rows is written: binary, stop rule, memory speed, load at launch, number of interval records and processes. Then the proof is written that row F72d12 ran in the boot of the rerun. The build stops unless the F72d12 process lies between two readings of the same boot id: try6.txt before it and the first state line of go.sh after it (lines 129-239).
7. Section 4.1, hardware error records. For the processes of rows L-1 to L-4, R0 and R0b the table says where each error record of the saved journal lies against the intervals that the sheet uses (oldread at position 0 and asmread at position 1 of each round). The build stops unless two records of one second lie inside the lowest asmread interval of the pool L-1 to L-4. The pool without this interval is stored as `P12a_wo` for section 4.4 (lines 241-333).
8. Section 4.1, hypothesis on corrected records. For every interval to which records can be assigned the table gives its rate minus the rate of the same kernel at the same position in the other round of the same process. Records at the border of two intervals cannot be assigned to one interval. The text counts them, and their intervals are not in the table. A difference counts when it is above `LIM` = 1.0 GB/s. The text says what fits the hypothesis and what does not (lines 334-439).
9. Section 4.2, old read kernel, parts A and L. Part A: the range of `bw_old read` of the rerun (`A72o`) is tested against rows A-1, A-2, A-3 and their pool (`A80o`). Part L: the range of oldread (`L72o`) is tested against L-1 alone, the pool L-1 to L-4 (`P12o`) and the pool with R0 and R0b (`PALLo`). The oldread ranges of F72d12 (`F72o`) and of control I (`I72o`) are tested against the same three record lists. For part L the distance of the nearest ends, of the medians and of the farthest ends is computed in GB/s and in percent (lines 441-520).
10. Section 4.2, view by start state. The processes of the pool L-1 to L-4 are split into two groups by the 1-minute load average at launch: below 1.0 (`idle`), or 1.0 and above (`busy`). The build stops unless every `busy` process was launched at most 30 s after a 120-thread bwx12 process ended. The oldread and asmread ranges of each group are formed. Parts L and C are compared with the second group. A group of the same kind is formed from the bwx11 rows: the processes that were launched at most 30 s after a 120-thread bwx11 process ended. For rows B7a, B7b, C3a and C3b of runner bwx the code takes every process and checks that it follows a 120-thread step in its csv file. It checks no time limit there (lines 522-666).
11. Section 4.2, old read kernel, part C. The oldread intervals of part C (`C72o`) are tested as one list. They are also tested separately by position: position 0 (cfwd) and position 2 (crev, directly after read) (lines 668-711).
12. Section 4.3, new read kernel in part A (rule V3). For each cell of `pa3` (binary, load-only kernel, round) the three intervals of session 1 get the wording inside or outside the 8000 MT/s range of the same round. One entry per cell is added to `V['q2_rows']`. The medians of `bw_new read` in session 1, row A-1 and row A-2 are compared (lines 713-776).
13. Section 4.3, view at an equal pass count. The same cells are compared again with only the intervals that completed 663 or 664 passes (lines 777-818).
14. Section 4.3, thread rates. The sum of the thread rates of an interval is estimated as 120 x the column `per_thread_avg_GBps`. The distance of the nearest ends by this estimate is set next to the distance by `aggregate_GBps`. The estimate is checked against the per-thread rows of A1.csv (lines 819-869).
15. Section 4.4, asmread in part L. The asmread ranges of part L (`L72a`), F72d12 and control I are tested against L-1 alone, the pool L-1 to L-4 (`P12a`) and the pool with R0 and R0b (`PALLa`). The tests are repeated against the pool without the interval that holds the error records (lines 871-931).
16. Section 4.5, load-only kernels in part C, grouped by the kernel that ran directly before. Kernel `read` has no bwx12 run at 8000 MT/s. Its two groups are shown next to the rows of runner bwx and get no wording. The group "asmread after oldread" is tested against the pool L-1 to L-4 (lines 933-1040).
17. Section 4.6, the three visits of the like.spec line in the 7200 MT/s boot (F72d12, part L, control I). The build stops unless the three asmread ranges lie in rising order without overlap: F72d12 lowest, then control I, then part L. The spread between the lowest and the highest value is computed. The distances of part L to F72d12 and to the pool L-1 to L-4 are stored in `c['dist']`. The texts that rule V1 points 3 and 4 require are written from the 10-module rows (lines 1042-1211).
18. Section 4.7, sums per mesh. For each row the lowest and the highest value of `mesh0_GBps` and of `mesh1_GBps` are printed. The build stops unless oldread at 7200 MT/s gave more on mesh 1 and less on mesh 0 than the bwx12 and bwx11 rows at 8000 MT/s (lines 1213-1283).
19. Section 4.8, a table that is kept as a record: the lowest to highest total of read_nop96, read_nop256 and read_1pl in part L, control I, F72d12 and L-1. No statement is made from it (lines 1285-1298).
20. Section 4.9, verdict for Q2. Two verdict texts are built from the values above: `V['q2_old_read']` and `V['q2_new_read']`. They are joined as `V['q2']`. Three more objects are stored for `facts.json`: `same_boot`, `pool_8000_by_start_state` and `part_A_thread_rates` (lines 1300-1433).
21. Section 5, a table that is kept as a record: write, copy, asmwrite and asmcopy of part A. A cell holds n, the lowest, the median and the highest rate. No statement is made from it (lines 1435-1453).
22. Section 6, three lists: what is established, what is not established (`V['insufficient_data']`) and the hypotheses H1 to H5 (`V['hypotheses']`). Before the lists are built, the build stops unless every integrity check of `build_facts.py` passed (line 1461) [Ref3]. The code counts in how many load-only cells of part A the round-2 process lies above the round-1 process without overlap. Here a cell is one session with one of `bw_new read`, `bw_old asmread` and `bw_new asmread`. That gives 9 cells (lines 1455-1615).

## Behavior a reader must know

- Where a rate comes from. This file reads no csv row. It works on the interval records in `D['recs']`, which `build_facts.py` made before. Field `GBps` of a part A record is the column `aggregate_GBps` of the interval line of the csv file. The binary computes that column as the sum of the bytes of all threads divided by the longest per-thread time. It prints the column with 2 decimal places [Ref6]. Field `GBps` of a bwx record is the sum over the T rows of the interval of bytes / elapsed_s / 1e9. Each T row uses the elapsed time of its own thread. The column aggregate_GBps of the I row is not used as the rate [Ref2] [Ref3]. Two blocks use parsed values that are not records. The block on hardware error records (lines 241 to 439) uses the interval dicts of `D['hw']` and `D['hw_cmp']`, with the rate in the field `total`. Line 512 and lines 1550 to 1552 print values of these dicts again. The check of the estimate (lines 844 to 851) uses the `thread` lines of A1.csv and the column per_thread_avg_GBps of its interval lines [Ref2].
- Rows that are left out before this file runs. From rows L-2, L-3, L-4, R0, R0b, X1d10, X1d10b and BASEd10 only oldread at position 0 and asmread at position 1 are records. From the folders of runner bwx only the kernels oldread, read and asmread are records, and only the processes whose tag starts with `common-6000-`, `b5-fwd-` or `b5-rev-`. From A3.csv only the processes with the tags onebuf-ms500-1, onebuf-ms500-2 and onebuf-ms500-3 are records [Ref3]. From a run folder of an earlier bwx12 or bwx11 row only the csv files that the row list of `build_facts.py` names give records. Example: the folder of row L-1 holds 5 csv files, and only a6456.csv gives records. From the folder partA-20261113T205055Z only A1.csv and A3.csv give records [Ref3]. A part A csv file also holds one `best` line per process and kernel, with the highest aggregate_GBps of its intervals. The parser skips this line. So it is not a record [Ref2] [Ref6].
- How records are selected here. `sel(recs, field=value, ...)` returns the records that match every condition. A condition value may be one value, a set of values or a function. Example: `sel(recs, dataset=set(BW12), kernel='asmread', pos=1)` returns asmread at position 1 of rows L-1 to L-4 [Ref2].
- Statistics. The file takes no mean over the intervals of a list. A list of intervals is described by `rng`: lowest value, highest value, median, number of intervals, number of processes, number of sessions and number of boots. `med` is the median of `GBps` of a list. For an even number of values the median is the mean of the two middle values [Ref1] [Ref2].
- The test of rule V1 point 2. `compare(r72, r80)` forms the range `a` of the 7200 MT/s records and the range `b` of the 8000 MT/s records. `overlap` is true when `a.lo <= b.hi` and `b.lo <= a.hi`. `dist` is the distance of the nearest ends in GB/s. It is positive when the 7200 MT/s range lies above, negative when it lies below, and 0 when the ranges overlap. `wording` is "no difference seen" for an overlap and "differs between the 8000 MT/s boot and the 7200 MT/s boot" otherwise. `width` is (b.hi - b.lo) / b.lo x 100, in percent [Ref1] [Ref2].
- Which test decides. `cmps` tests each 7200 MT/s row against one or more 8000 MT/s scopes. Only a scope with `decides` = True gets a wording. It is the pool A-1 to A-3 for `bw_old read` of part A, and the pool L-1 to L-4 for the bwx12 rows. The other scopes are printed without a wording. Six part C rows have no deciding test. Three of them are tested against the pool L-1 to L-4 with `decides` = False: oldread of cfwd at position 0, asmread as first interval, and asmread after read. The other three are tested only against rows of runner bwx, also with `decides` = False: oldread of crev at position 2, read after oldread, and read after asmread. So part C gets two wordings: one for all its oldread intervals and one for asmread after oldread.
- Rule V3 rows (part A, load-only kernels) do not use `compare`. `facts_text.py` counts how many of the 3 intervals of session 1 lie above, below or inside the 8000 MT/s range of the same round (`pa3`). Sessions 2 and 3 of part A are not part of this test. Rule V3 uses them for Q1 only [Ref5]. Lines 723 to 733 turn the counts into the wording "inside" or "outside". A cell with mixed counts gets a text with the three counts. No percent is computed [Ref1].
- Rounding. `g` prints a rate with 2 decimal places. `pc` prints a percent value with 1 decimal place. Both round half up. Range tests, differences and medians use the values before rounding. One check compares rounded text: line 199 prints the oldread rates of the three 10-module rows with `%.1f` and searches this text in the DIMM report. The columns "Distance of the nearest ends" of the test tables use the Python format `%+.2f` and not `g` (lines 85, 796 and 833). The estimate column of line 833 uses `%+.1f`. The other number columns of the table of thread rates (lines 832 and 833) and the two differences of lines 858 and 860 use `%.2f` or `%.1f`. These formats round the binary value of the number. So they can differ from `g` by one step for a value that ends in 5 at the next decimal place (tested: 2.675 gives `2.67` with `%.2f` and `2.68` with `g`). Values for `facts.json` are rounded with the Python function `round` in lines 742, 1387, 1388, 1432 and 1433. Later `build_facts.py` rounds every decimal number of `V` and of the interval records to 3 decimal places when it writes `facts.json` [Ref1] [Ref3].
- `need(condition, text)` stops the whole build with an error message when the condition is false. The file holds 89 calls of `need`. Most calls guard one sentence of the sheet: the build only finishes when the data show the pattern that the sentence states. A few calls guard a table or a later step, for example the calls in lines 53 and 848. A `need` line computes no rate [Ref1].
- What the function changes. `section4` returns nothing. It appends Markdown lines to the list `L`. It adds entries to the verdict object `V`. It stores values in the context `c` under the keys `hw`, `oldL`, `byst`, `partC_view`, `byst_other`, `thr`, `kF1`, `kI1`, `kAao`, `Aao`, `dist`, `mesh` and `f72_limit`. After the call, `facts_text.py` builds section 0 (the short version) from these values [Ref1].
- Verdicts written to `V`: `q2_rows` (one entry per range test), `q2_old_read`, `q2_new_read`, their join `q2`, `same_boot`, `pool_8000_by_start_state`, `part_A_thread_rates`, `insufficient_data` and `hypotheses`. `build_facts.py` writes `V` to `facts.json` under the key "verdicts" [Ref3].
- Sections of FACTS.md written by this file: 4.1 to 4.9 (Q2), 5 (record-only table of part A) and 6 (established, not established, hypotheses) [Ref4].
- Q1 is not computed here. The percent drop of the new read kernel against the old read kernel comes from `facts_text.py`. Section 6 of this file only prints these values: `c['dl']`, `c['di']`, `c['df']` and the second element of each `CG` entry [Ref1].
- Views that are not part of the rules fixed before the run: the comparison of intervals with hardware error records (section 4.1), the pool split by start state (section 4.2), the view at an equal pass count and the estimate from 120 x the per-thread average (section 4.3), and the sums per mesh (section 4.7). The rules file holds none of these five views [Ref5]. The text templates of this file say that the views of sections 4.1, 4.2 and 4.7 were added or looked at after the numbers were seen. They say that the view at an equal pass count was added while the sheet was built. They do not say when the estimate was added. Section 2 of FACTS.md says it. By its decision (o) the view at an equal pass count and the table of thread rates were added after the numbers were seen. `facts_text.py` writes that section [Ref1] [Ref4]. None of the five views calls `cmps` or `q2row`. So none of them adds a wording by rule V1 point 2.
- Thresholds that this file sets. `LIM` = 1.0 GB/s (line 353): a difference between the two rounds of a process counts only above this value. Load 1.0 (lines 533 and 534): a process launched at a 1-minute load average below 1.0 belongs to the group `idle`, every other process to the group `busy`. 30 s (lines 537, 569 and 593): the longest time between the end of a 120-thread process and a launch that counts as a start after 120-thread work. `full` = 64 x 6 + 56 x 5 = 664 passes (line 777). `half` = 120 x 0.005 = 0.6 GB/s (line 819), the largest rounding error of 120 x a value that is rounded to 0.01 GB/s. More fixed limits are used in `need` lines only: 60 s after 120-thread work and a 5-minute load average of 1.0 for control I (lines 898 and 899), 10 %CPU and 1 %CPU in the process lists (lines 1081 and 1307), 1 % for the old read kernel (lines 491 and 1204), and load 1 inside row L-2 (line 1563). Two more such limits: 1.2 GB/s (2 x `half`) for the estimate from 120 x average (lines 842 and 851), and 2 s after the process start for the error records of row L-1 (line 1163). They stop the build. They select no data.
- Main places where rates are selected, grouped or compared. Hardware error records: lines 297 to 303 (the lowest asmread interval of the pool L-1 to L-4 and the pool without it) and 353 to 358 (differences between the two rounds). Old read kernel: lines 446 to 459 (part A), 471 to 491 (part L), 523 to 611 (start-state groups) and 670 to 701 (part C). New read kernel in part A: lines 723 to 765 (rule V3 and medians), 777 to 796 (equal pass count) and 819 to 851 (120 x average). asmread in part L: lines 881 to 893 and 916 to 920. Load-only kernels in part C: lines 945 to 964, 988 to 1016 and 1030 to 1034. Three visits: lines 1045 to 1048, 1070 to 1074 and 1146 to 1151. Highest values at 8000 MT/s in section 4.6: lines 1110 to 1131 and 1183 to 1186. 10-module rows: lines 1191 to 1206. Sums per mesh: lines 1220 to 1259. Tables kept as a record: lines 1291 to 1296 and 1443 to 1451. Round 2 above round 1 in part A: lines 1462 to 1468. Rates of hypothesis H1 from rows R0 and L-2: lines 1560 to 1563.
- Formatting code. A line `w(...)` appends one line of Markdown text. A line `L.extend(table(...))` appends one table. Most lines of the file are such text templates with `%` placeholders. The values in the placeholders come from the statistics named above.
- The imported names `gap` and `sess` are not called in this file.
- How to read the call sequence: a helper is listed at its first call. `ranges` and `cmps` are listed at every call. Each call writes one table of the Q2 comparison. Two more entries differ. `_q` is listed at its direct call in line 627. `g` calls it before that. `q2row` is listed a second time at its direct call in line 963.

## Call sequence in the whole-chip test

- `build_facts.py:main`: entry point: collects the records, calls render, writes FACTS.md and facts.json
  - `facts_text.py:render`: writes sections 1 to 3, calls section4, then writes sections 0 and 7
    - `section4` (line 24): writes sections 4, 5 and 6 and the Q2 verdicts
      - `facts_data.py:sel`: returns the records that match the given field values
      - `facts_text.py:dur`: prints a time span as hours, minutes and seconds
      - `facts_data.py:_open`: opens like.spec, cfwd.spec and crev.spec and notes the file names
      - `noseq` (line 123): removes the `--seq` value before the three argument lines are compared
      - `facts_text.py:need`: stops the build when the data do not show a stated pattern
      - `facts_text.py:Refs.__call__`: the argument `ref`: returns the label `[RefN]` of a file
      - `source` (line 57): section 4.1: Source cell of each earlier row
        - `src` (line 44): labels of the csv files that hold the records
      - `facts_text.py:table`: formats a header and rows as a Markdown table
      - `facts_text.py:hmd`: prints a time with its date
      - `facts_text.py:hm`: prints a time of day as HH:MM:SS
      - `kind_txt` (line 262): section 4.1: position of an error record against the used intervals
        - `facts_text.py:g`: prints a number with 2 decimal places, rounded half up
      - `sg` (line 339): section 4.1: prints a rate difference with its sign
      - `c['hw']['cmp']['lst']` (line 373): joins the loop names with commas and `and`
      - `lst` (line 411): joins texts with commas and `and`
      - `ranges` (line 48): section 4.2: range table of bw_old read, part A and rows A-1 to A-3
        - `facts_data.py:rng`: lowest, highest, median, interval count and process count of a list
        - `facts_text.py:nn`: prints n as intervals / processes, with sessions and boots as options
        - `facts_text.py:sp`: prints a range as lowest to highest, 2 decimal places
      - `cmps` (line 71): section 4.2: overlap tests of bw_old read, part A
        - `facts_text.py:compare`: two ranges, overlap flag, nearest-end distance, wording, width
          - `facts_data.py:overlap`: true when two ranges share at least one value
          - `facts_data.py:gap`: distance of the nearest ends, signed, 0 for an overlap
          - `facts_data.py:width_pct`: width of a range in percent of its lower end
        - `facts_text.py:q2row`: appends the test to `V['q2_rows']` for facts.json
        - `facts_text.py:pc`: prints a percent value with 1 decimal place, rounded half up
      - `lrows` (line 471): range-table rows of L-1 to L-4 for one kernel and position
      - `orows` (line 472): range-table rows of R0 and R0b for one kernel and position
      - `ranges` (line 48): section 4.2: range table of oldread, part L and the 8000 MT/s rows
      - `cmps` (line 71): section 4.2: overlap tests of oldread for part L, F72d12 and control I
      - `grp` (line 539): start-state view: pool records of the group `idle` or `busy`
      - `names` (line 544): start-state view: the processes of a group as text
      - `loads` (line 543): start-state view: sorted loads at launch of a group
      - `lsrc` (line 545): start-state view: labels of the launches.txt files of a group
      - `facts_text.py:_q`: prints one percent value with 2 decimal places, rounded half up
      - `secs` (line 18): interval lengths of a record list as text
      - `scm` (line 674): keeps the records of processes with `--start common`
      - `ranges` (line 48): section 4.2: range table of oldread, part C and the 8000 MT/s rows
      - `cmps` (line 71): section 4.2: overlap tests of oldread for three part C groups
      - `facts_text.py:nns`: prints n of rerun records with the session text
      - `cellt` (line 722): section 4.3: three rates with their pass counts as one table cell
      - `facts_text.py:med`: median of the rates of a record list
      - `same` (line 781): section 4.3: keeps the intervals with 663 or 664 passes
      - `one_v` (line 42): prints one rate, or the range of several rates
      - `av` (line 825): section 4.3: per-thread average rates of a record list
      - `span` (line 826): prints one value, or lowest to highest
      - `ranges` (line 48): section 4.4: range table of asmread at position 1, all rows
      - `cmps` (line 71): section 4.4: overlap tests of asmread for part L, F72d12 and control I
      - `ranges` (line 48): section 4.5: range table of kernel read, part C and runner bwx rows
      - `facts_text.py:q2row`: section 4.5: stores the two read groups of part C, without a wording
      - `ranges` (line 48): section 4.5: range table of asmread, part C groups and 8000 MT/s rows
      - `m_k` (line 1004): section 4.5: key and label of a scope that matches the kernel before
      - `cmps` (line 71): section 4.5: overlap tests of asmread for three part C groups
      - `in_` (line 1126): section 4.6: tests whether a value lies inside a range
      - `where` (line 1132): section 4.6: says where one record comes from
      - `facts_text.py:pool`: section 4.7: `N['pool']`, the records of rows R0 and R0b
      - `mrow` (line 1220): section 4.7: one table row with the ranges of the two mesh sums
      - `side` (line 1311): section 4.9: both sides of a comparison as verdict text
      - `facts_data.py:rel`: section 4.9: path of env.txt as the facts sheet writes it
      - `facts_text.py:pcr`: section 6: lowest and highest of a list of percent values
      - `sgn` (line 1516): section 6: prints a rate difference with its sign

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `secs` | 18-21 | Returns the interval lengths of a record list as text, for example `6 s`, from the field `min_ms`. | - | - |
| `section4` | 24-1615 | Writes sections 4, 5 and 6 of FACTS.md, runs the Q2 range tests, and stores the Q2 verdicts and the hypotheses in `V`. | `sel`, `rng`, `compare`, `med`, `overlap`, `width_pct`, `need`, `table`, `ref`, `q2row`, `pool`, `secs`, `src`, `ranges`, `source`, `cmps`, `kind_txt`, `mrow`, `one_v`, `noseq`, `sg`, `lst`, `lrows`, `orows`, `grp`, `loads`, `names`, `lsrc`, `scm`, `cellt`, `same`, `av`, `span`, `m_k`, `in_`, `where`, `side`, `sgn`, `g`, `sp`, `pc`, `pcr`, `hm`, `hmd`, `dur`, `nn`, `nns`, `_q`, `fd._open`, `fd.rel` | - |
| `one_v` | 42-42 | Lambda. Prints the one rate of a list with one record, or the lowest-to-highest range of a longer list. | `g`, `sp`, `rng` | - |
| `src` | 44-46 | Returns the `[RefN]` labels of the csv files that hold the given records, each file once. | `ref` | - |
| `ranges` | 48-55 | Builds a range table: one row per record list with memory speed, modules, n, lowest to highest rate, median and source files. | `rng`, `need`, `nn`, `sp`, `g`, `src`, `table` | - |
| `source` | 57-69 | Builds the Source cell of the section 4.1 row table: csv files, plus the files with the load and the binary sha256. | `src`, `ref` | - |
| `cmps` | 71-90 | Runs `compare` for each 7200 MT/s row against each 8000 MT/s scope, stores each test with `q2row`, and returns the overlap table. | `compare`, `q2row`, `sp`, `pc`, `table` | - |
| `noseq` | 123-123 | Lambda. Removes the value of `--seq` from an argument line. The lines can then be compared without the kernel sequence. | - | - |
| `kind_txt` | 262-271 | Returns the position of one error record as text: `outside`, `inside` plus the interval, or `before or inside` plus the interval. | `g`, `need` | - |
| `sg` | 339-339 | Lambda. Prints a difference in GB/s with 2 decimal places and its sign. A value that rounds to zero prints as `0.00`. | `g` | - |
| `c['hw']['cmp']['lst']` | 373-373 | Lambda. Stored in `c`. Joins a list of texts with commas, and with `and` before the last text. | - | - |
| `lst` | 411-411 | Lambda. Joins a list of texts with commas, and with `and` before the last text. | - | - |
| `lrows` | 471-471 | Lambda. Returns one range-table row per row L-1 to L-4, for the given kernel and position. | `sel` | - |
| `orows` | 472-472 | Lambda. Returns one range-table row per row R0 and R0b, for the given kernel and position. | `sel` | - |
| `grp` | 539-539 | Lambda. Returns the records of rows L-1 to L-4 for one kernel and position whose process is in the given start-state group. | `sel` | - |
| `loads` | 543-543 | Lambda. Returns the sorted loads at launch of the given processes. | - | - |
| `names` | 544-544 | Lambda. Returns the given processes as text: row name and tag, joined with commas. | - | - |
| `lsrc` | 545-545 | Lambda. Returns the `[RefN]` labels of the launches.txt files of the given processes, each file once. | `ref` | - |
| `scm` | 674-674 | Lambda. Keeps the records whose process ran with `--start common`. | - | - |
| `cellt` | 722-722 | Lambda. Prints the intervals of one cell as rate and pass count in brackets, or `no process in this row` for an empty list. | `g` | - |
| `same` | 781-781 | Lambda. Keeps the records with 663 or 664 passes (`full - 1` or `full`). | - | - |
| `av` | 825-825 | Lambda. Returns the values of the field `per_thread_avg_GBps` of a record list. Line 1046 reuses the name for a range. | - | - |
| `span` | 826-826 | Lambda. Prints a list of numbers as one value when all are equal, otherwise as lowest to highest. | - | - |
| `m_k` | 1004-1005 | Lambda. Returns a pair for a scope that matches in the kernel before: the key in facts.json and the label in the table. | - | - |
| `in_` | 1126-1126 | Lambda. True when a value lies inside a range, the two ends included. | - | - |
| `where` | 1132-1132 | Lambda. Describes one record as text: process tag, folder, position, kernel before and the line of its I row. | - | - |
| `mrow` | 1220-1222 | Returns one table row of section 4.7: label, memory speed, interval count, range of the mesh 0 sums, range of the mesh 1 sums, source. | `rng`, `sp`, `src` | - |
| `side` | 1311-1311 | Lambda. Prints both sides of a comparison for a verdict: range and n at 7200 MT/s, range and n at 8000 MT/s. | `sp`, `nn` | - |
| `sgn` | 1516-1516 | Lambda. The same as `sg`: prints a difference in GB/s with its sign. | `g` | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Module comment and imports</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  #!/usr/bin/env python3
   2  """facts_text4.py - sections 4, 5 and 6 of FACTS.md (7200 MT/s against 8000 MT/s, record-only tables, conclusions).
   3
   4  Used by facts_text.py. The templates hold words only; every number is formatted from the collected data.
   5  """</pre></td><td valign="top">The module comment.<ul><li>This file writes sections 4, 5 and 6 of <code>FACTS.md</code>. <code>facts_text.py</code> uses it.</li><li>The comment says that the text templates hold words only, and that every number is formatted from the collected data.</li><li>A few counts are typed in the templates. Examples are "2 corrected records" in line 510 and "and 1" in line 430. A <code>need</code> call tests each of these two counts (lines 293 and 363).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   6  import os
   7  import re
   8
   9  import facts_data as fd
  10  from facts_data import R, sel, rng, overlap, gap, width_pct
  11  from facts_text import (need, g, sp, pc, pcr, hm, hmd, dur, nn, nns, sess, table, compare, med, BW12, BW11, BWX, DIFFERS,
  12                          SAME, NO_READ, W15, ADDED, NOT_PLAN, H1_MEAS, FIRST, F2_NOTE, STANDIN, _q)
  13</pre></td><td valign="top">Imports. <code>os</code> and <code>re</code> come from the Python standard library. The module <code>facts_data.py</code> is also imported as a whole under the name <code>fd</code>.<ul><li>From <code>facts_data.py</code>: the results folder <code>R</code>, the record filter <code>sel</code>, the range function <code>rng</code>, and <code>overlap</code>, <code>gap</code> and <code>width_pct</code> [Ref2].</li><li>From <code>facts_text.py</code>: the check <code>need</code>, the number formats <code>g</code>, <code>sp</code>, <code>pc</code>, <code>pcr</code> and <code>_q</code>, the time formats <code>hm</code>, <code>hmd</code> and <code>dur</code>, the n formats <code>nn</code> and <code>nns</code>, and <code>table</code>, <code>compare</code> and <code>med</code> [Ref1].</li><li>Also from <code>facts_text.py</code>: the row lists <code>BW12</code> (L-1 to L-4), <code>BW11</code> (R0, R0b) and <code>BWX</code> (B7a, B7b, C3a, C3b), the folder <code>W15</code>, and the fixed texts.</li><li><code>gap</code> and <code>sess</code> are imported and not called in this file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  14  OWN = '(same boot, own row)'      # label of F72d12 and control I in the range tests of rule V1 point 2
  15  OLD_OWN = '(same boot, not pooled)'   # the key of these rows in facts.json (kept from the earlier builds)
  16
  17</pre></td><td valign="top">Two labels for the rows F72d12 and control I in the range tests. <code>OWN</code> is the label that the tables of <code>FACTS.md</code> print. <code>OLD_OWN</code> is the key of the same rows in <code>facts.json</code>. The key stays as it was in earlier builds.</td></tr>
<tr><td colspan="2"><b>Function <code>secs</code>: interval lengths as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  18  def secs(rs):
  19      """Interval length of a list of records, as text."""
  20      v = sorted({r['min_ms'] for r in rs})
  21      return ' and '.join('%g s' % (x / 1000) for x in v)
  22
  23</pre></td><td valign="top">Collects the values of the field <code>min_ms</code> of the given records, each value once, in rising order. Each value is divided by 1000 and printed in seconds. Several values are joined with <code>and</code>. Example: records with <code>min_ms</code> 4000 and 6000 give <code>4 s and 6 s</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>section4</code>: sections 4 to 6 of the facts sheet</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  24  def section4(D, N, V, L, ref, q2row, c):
  25      recs = D['recs']
  26      w = L.append
  27      try6 = D['try6']
  28      rules = c['rules']
  29      evd = c['evd']
  30      pool = N['pool']</pre></td><td valign="top"><code>section4</code> starts here and ends at line 1615. <code>facts_text.py</code> calls it once [Ref1].<ul><li><code>recs</code>: the list of all interval records. This file reads no csv row. The rate of a record is its field <code>GBps</code>.</li><li>For a part A record <code>GBps</code> is the csv column <code>aggregate_GBps</code>. The header line of each process in the csv file gives its formula: sum(bytes) / max(per-thread elapsed_s). For a record of a bwx runner it is the sum over the T rows of bytes / elapsed_s / 1e9 [Ref2] [Ref3].</li><li><code>w</code>: appends one line of text to the output list <code>L</code>.</li><li><code>try6</code>: the reading of 12 modules at 7200 MT/s, with the boot id of the rerun.</li><li><code>rules</code>: the path of the rules file <code>baselines-and-rules.txt</code>. <code>evd</code>: the steps of <code>go.sh</code> and <code>go2.sh</code>, by tag.</li><li><code>pool</code>: the function <code>N['pool']</code>. It returns the records of several rows for one kernel and position.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  31      cLo, cLa, cIo, cIa, cFo, cFa, cAo, cCo = (c[k] for k in ('cLo', 'cLa', 'cIo', 'cIa', 'cFo', 'cFa', 'cAo', 'cCo'))
  32      L72o, L72a, I72o, I72a, F72o, F72a = (c[k] for k in ('L72o', 'L72a', 'I72o', 'I72a', 'F72o', 'F72a'))
  33      P12o, P12a, PALLo, PALLa, A72o, A80o, C72o = (c[k] for k in ('P12o', 'P12a', 'PALLo', 'PALLa', 'A72o', 'A80o', 'C72o'))
  34      pa3, newread = c['pa3'], c['newread']</pre></td><td valign="top">Reads the comparisons and the record lists from the context <code>c</code>. <code>facts_text.py</code> prepared them [Ref1]. In the names, <code>o</code> stands for the old read kernel and <code>a</code> for asmread.<ul><li>Line 31, comparisons against the pool L-1 to L-4: <code>cLo</code>, <code>cLa</code> (part L), <code>cIo</code>, <code>cIa</code> (control I), <code>cFo</code>, <code>cFa</code> (F72d12) and <code>cCo</code> (oldread of part C). <code>cAo</code> compares <code>bw_old read</code> of part A with rows A-1 to A-3.</li><li>Line 32, 7200 MT/s lists: oldread and asmread of part L (<code>L72o</code>, <code>L72a</code>), of control I (<code>I72o</code>, <code>I72a</code>) and of F72d12 (<code>F72o</code>, <code>F72a</code>).</li><li>Line 33, 8000 MT/s lists: <code>P12o</code> is oldread at position 0 of rows L-1 to L-4. <code>P12a</code> is asmread at position 1 of the same rows. <code>PALLo</code> and <code>PALLa</code> add rows R0 and R0b. <code>A80o</code> is <code>bw_old read</code> of rows A-1 to A-3.</li><li>Also line 33, 7200 MT/s lists: <code>A72o</code> is <code>bw_old read</code> of part A. <code>C72o</code> is oldread of part C at every position. That is position 0 in the cfwd processes and position 2 in the crev processes.</li><li>Line 34: <code>pa3</code> and <code>newread</code> hold the cells of rule V3 (part A, load-only kernels).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  35      C = sel(recs, dataset='rerun-C')
  36      first = FIRST
  37      CG = c['CG']
  38      f72la = D['rx']['F72d12']['launches']['a6456']
  39      fenv = D['rx']['F72d12']['env']
  40      f72dir = D['rx']['F72d12']['folder']
  41      S_ = os.path.dirname(rules)
  42      one_v = lambda rs: g(rs[0]['GBps']) if len(rs) == 1 else sp(rng(rs))      # a range, or the one value of one interval</pre></td><td valign="top"><ul><li><code>C</code>: all records of part C (<code>dataset</code> = <code>rerun-C</code>).</li><li><code>first</code>: the text that the field <code>kernel_before</code> holds for the first interval of a process.</li><li><code>CG</code>: the load-only intervals of part C in five groups (rule V2).</li><li><code>f72la</code>, <code>fenv</code>, <code>f72dir</code>: for the F72d12 process (tag <code>a6456</code>), the entry with its launch line and its rc line, the parsed content of its <code>env.txt</code>, and its run folder.</li><li><code>S_</code>: the folder of the rules file. It is folder S.</li><li><code>one_v</code>: a one-line function. For a list with one record it prints the rate with 2 decimal places. For a longer list it prints the lowest to the highest rate.</li></ul></td></tr>
<tr><td colspan="2"><b>Local helpers of <code>section4</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  43
  44      def src(rs):
  45          files = list(dict.fromkeys(os.path.join(R, r['folder'][2:], r['file']) for r in rs))
  46          return ' '.join(ref(f) for f in files)
  47</pre></td><td valign="top"><code>src</code> returns the reference labels of the csv files that hold the given records. It builds each path from the results folder <code>R</code>, the field <code>folder</code> without its first two characters <code>R/</code>, and the field <code>file</code>. Each file is named once, in the order of the records. <code>ref</code> turns a path into its label <code>[RefN]</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  48      def ranges(rows):
  49          out = []
  50          for label, what, rs in rows:
  51              a = rng(rs)
  52              st = sorted({(r['speed_MTps'], r['modules']) for r in rs})
  53              need(len(st) == 1, 'one machine state per row: ' + label)
  54              out.append([label, what, '%d MT/s, %d modules' % st[0], nn(a, boots=False), sp(a), g(a['med']), src(rs)])
  55          return table(['Row', 'What it is', 'Memory speed, modules', 'n', 'Min to max, GB/s', 'Median, GB/s', 'Source'], out)
  56</pre></td><td valign="top"><code>ranges</code> builds a range table with one row per record list <code>rs</code>.<ul><li><code>rng(rs)</code> gives the lowest value, the highest value and the median of <code>GBps</code>, the number of intervals and the number of processes [Ref2]. No mean over intervals is taken.</li><li>The median of an even number of values is the mean of the two middle values.</li><li>Line 53: the build stops unless all records of the list have the same memory speed and the same module count. <code>build_facts.py</code> sets both fields (see the explanation of lines 150 to 152).</li><li>The row prints n as intervals / processes, the range as lowest to highest, and the median. <code>sp</code> and <code>g</code> round to 2 decimal places. A value exactly between two steps is rounded away from zero (half up).</li><li>The last cell names the csv files (<code>src</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  57      def source(ds, rs):
  58          """Source cell of the row table: csv files, then where the load and the sha256 of the binary come from."""
  59          if ds in D['rx']:
  60              v = D['rx'][ds]
  61              sha = os.path.join(v['folder'], 'env.txt') if v['env']['has_binary_line'] else os.path.join(W15, 'r0.sh')
  62              return 'rates %s, load %s, sha256 %s' % (src(rs), ref(os.path.join(v['folder'], 'launches.txt')), ref(sha))
  63          if ds in D['step']:
  64              sha = os.path.join(D['step'][ds]['folder'], 'env.txt')
  65          elif ds == 'A-1':
  66              sha = D['probe13']['path']
  67          else:
  68              sha = os.path.join(D['base'][ds]['folder'], 'env.txt')
  69          return 'rates and load %s, sha256 %s' % (src(rs), ref(sha))
  70</pre></td><td valign="top"><code>source</code> builds the Source cell of the row table in section 4.1. The cell says where the rates, the load and the sha256 of the binary come from.<ul><li>A row written by <code>rx.sh</code> or <code>r0.sh</code> (a key of <code>D['rx']</code>): the csv files for the rates, <code>launches.txt</code> for the load, and <code>env.txt</code> for the sha256. When <code>env.txt</code> holds no binary line, the script <code>r0.sh</code> is named for the sha256.</li><li>A row of runner bwx (a key of <code>D['step']</code>): the csv file for the rates and the load, and <code>env.txt</code> of the folder for the sha256.</li><li>Row A-1: the csv file, and the file <code>probe.txt</code> of the 2026-11-13 run for the sha256.</li><li>Rows A-2 and A-3: the csv file, and <code>env.txt</code> of the run folder for the sha256.</li><li>The records of rows A-2 and A-3 take their sha256 from the <code>probe.txt</code> of row A-1, not from this <code>env.txt</code>. <code>build_facts.py</code> runs integrity checks (tests of the raw files and the scripts). Its check <code>sha-bw</code> tests that this <code>env.txt</code> holds the same two values [Ref3]. Line 1461 stops the build unless every integrity check passed.</li></ul></td></tr>
<tr><td colspan="2"><b>Helper <code>cmps</code>: the range tests of rule V1 point 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  71      def cmps(part, kernel, items, note='', notes=None):
  72          """items: (label of the 7200 MT/s row, records, [(label of the 8000 MT/s range, records, decides)]).
  73          A label may be a pair (key in facts.json, label in the table). The keys stay as they were in the earlier
  74          builds, because other tools find the rows of facts.json by them.
  75          note: text for the facts.json rows that carry a wording. notes: text per label for every row of that label."""</pre></td><td valign="top"><code>cmps</code> runs the range tests of one part and kernel.<ul><li><code>items</code> is a list of 7200 MT/s rows. Each row has a label, its records and a list of scopes.</li><li>A scope is one 8000 MT/s record list with a label and the flag <code>decides</code>.</li><li>A label may be a pair: the key for <code>facts.json</code> and the text for the table.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  76          out = []
  77          for label, r72, scopes in items:
  78              label, shown = label if isinstance(label, tuple) else (label, label)
  79              for scope, r80, decides in scopes:
  80                  scope, scope_shown = scope if isinstance(scope, tuple) else (scope, scope)
  81                  k = compare(r72, r80)
  82                  q2row(part, kernel, label, scope, k, decides, (notes or {}).get(label, note if decides else ''),
  83                        row_label=shown, scope_label=scope_shown)</pre></td><td valign="top">For each 7200 MT/s row and each scope:<ul><li><code>compare(r72, r80)</code> forms the min-to-max range <code>a</code> of the 7200 MT/s records and the range <code>b</code> of the 8000 MT/s records [Ref1].</li><li><code>overlap</code> is true when <code>a.lo &lt;= b.hi</code> and <code>b.lo &lt;= a.hi</code>. Two ranges that only share one end value count as an overlap.</li><li><code>dist</code> is the distance of the nearest ends in GB/s. It is positive when the 7200 MT/s range lies above, negative when it lies below, and 0 for an overlap.</li><li><code>width</code> is (b.hi - b.lo) / b.lo x 100: the width of the 8000 MT/s range in percent of its lower end.</li><li><code>q2row</code> stores the test in <code>V['q2_rows']</code> for <code>facts.json</code>: both ranges, both n, the overlap flag and the distance rounded to 3 decimal places. The stored wording is <code>None</code> (no value) unless <code>decides</code> is true.</li><li>The note of the stored test is the entry of <code>notes</code> for the label. Without such an entry it is <code>note</code> when <code>decides</code> is true, and empty otherwise.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  84                  out.append([shown, sp(k['a']), scope_shown, sp(k['b']), 'yes' if k['overlap'] else 'no',
  85                              '0' if k['overlap'] else '%+.2f' % k['dist'], pc(k['width']),
  86                              ('"%s"' % k['wording']) if decides else '-'])
  87          return table(['7200 MT/s row', 'Its range, GB/s', '8000 MT/s range used', 'That range, GB/s', 'Overlap',
  88                        'Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)',
  89                        'Width of the 8000 MT/s range, % of its lower end (est. from one boot)',
  90                        'Wording by rule V1 point 2'], out)
  91</pre></td><td valign="top">One table row per test: the 7200 MT/s row and its range, the 8000 MT/s scope and its range, <code>yes</code> or <code>no</code> for the overlap, the distance, the width and the wording.<ul><li>The distance cell is <code>0</code> for an overlap. Otherwise it is the signed value with 2 decimal places. It uses the Python format <code>%+.2f</code>, not the half-up rounding of <code>g</code>.</li><li>The width is printed with 1 decimal place (<code>pc</code>).</li><li>The wording is "no difference seen" for an overlap and "differs between the 8000 MT/s boot and the 7200 MT/s boot" otherwise. It is printed only when <code>decides</code> is true. Otherwise the cell is <code>-</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Descriptions of the earlier rows, check of the argument lines</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  92      DESC = {
  93          'A-1': 'baseline: the test of 2026-11-13, same process order as part A',
  94          'A-2': 'baseline: same binaries and arguments, other process order',
  95          'A-3': 'baseline: bw_old read only, same arguments as A-2',
  96          'L-1': 'baseline: identical argument line',
  97          'L-2': 'supporting: bwx12, other counter events',
  98          'L-3': 'supporting: bwx12, other counter events',
  99          'L-4': 'supporting: bwx12, other counter events',
 100          'R0': 'other binary (bwx11)',
 101          'R0b': 'other binary (bwx11)',
 102          'X2d12': 'not a baseline (firmware test setting), shown and not used',
 103          'F72d12': 'sample of the same boot as the rerun, earlier visit (load %.2f at launch, %s after the first kernel '
 104                    'log line of the boot), kept as its own row in every range test of rule V1 point 2'
 105                    % (f72la['load1'], dur((f72la['utc'] - try6['first_log_utc']).total_seconds())),
 106          'B7a': 'other binary (bwx), tags common-6000-*',
 107          'B7b': 'other binary (bwx), tags common-6000-*',
 108          'C3a': 'other binary (bwx), tags common-6000-*',
 109          'C3b': 'other binary (bwx), tags common-6000-*',
 110          'B5a': 'other binary (bwx), tags b5-fwd-*',
 111          'B5b': 'other binary (bwx), tags b5-fwd-*',
 112          'B5a-rev': 'other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only '
 113                     'for the highest values in section 4.6',
 114          'B5b-rev': 'other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only '
 115                     'for the highest values in section 4.6',
 116          'X1d10': '10 modules, changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4',
 117          'X1d10b': '10 modules, the same changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4',
 118          'BASEd10': '10 modules, original firmware settings, used only for the text of rule V1 point 4',
 119      }
 120</pre></td><td valign="top"><code>DESC</code> holds one description per earlier row. The row table of section 4.1 and the range tables print it in the column "What it is".<ul><li>All entries are template text (words written as they stand in the code), except the entry of F72d12.</li><li>That entry inserts two values: the load at launch of the F72d12 process, and the time from the first Linux kernel log line of the boot to that launch.</li><li>The load comes from <code>launches.txt</code>. The time of the first log line comes from <code>gaps.txt</code> [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 121      # L-1 inside the tables of part C: its argument line is that of part L. The lines of part C differ in --seq.
 122      spec = {n: fd._open(os.path.join(S_, n + '.spec')).read().strip().split('|', 1)[1] for n in ('like', 'cfwd', 'crev')}
 123      noseq = lambda a: re.sub(r'--seq \S+', '--seq', a)
 124      need(len({noseq(a) for a in spec.values()}) == 1 and len(set(spec.values())) == 3
 125           and D['rx']['L-1']['launches']['a6456']['args'] == spec['like'],
 126           'the three spec lines differ in --seq only, and L-1 has the line of like.spec')
 127      L1C = 'baseline of part L: its argument line is that of like.spec. It differs from cfwd.spec and crev.spec in --seq'
 128</pre></td><td valign="top">Reads the argument lines of <code>like.spec</code>, <code>cfwd.spec</code> and <code>crev.spec</code> from folder S.<ul><li>A spec file holds a tag, the character <code>|</code> and the arguments. The code keeps the arguments.</li><li><code>noseq</code> removes the value after <code>--seq</code> from an argument line.</li><li>Line 124: the build stops unless the three lines are equal after <code>noseq</code> and all differ before it.</li><li>Line 125: the build also stops unless the launch line of row L-1 (tag <code>a6456</code>) holds exactly the arguments of <code>like.spec</code>.</li><li><code>L1C</code>: the description of row L-1 for the tables of part C.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.1: the rules and the rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 129      # =============================================================================== 4
 130      w('## 4. Q2: 7200 MT/s against 8000 MT/s')
 131      w('')
 132      w('### 4.1 The rules and the rows')
 133      w('')
 134      w('The rules were fixed before the run %s. In short:' % ref(rules))
 135      w('')
 136      w('- Rule V1 point 2: per part and kernel, compare the min-to-max range of the 7200 MT/s intervals with the '
 137        'min-to-max range of the like-for-like 8000 MT/s intervals. If the ranges do not overlap, write "%s". If they '
 138        'overlap, write "%s" and give the width of the 8000 MT/s range as the size that the test cannot exclude.' % (DIFFERS, SAME))
 139      w('- Rule V1 point 3: never give a percent change of the new read kernel (bw_new read, bwx12 read, asmread) as an '
 140        'effect of the memory speed.')
 141      w('- Rule V1 point 4: for the old read kernel a difference above about 1 % may be reported as a difference '
 142        'between the two boots.')
 143      w('- Rule V3: part A, load-only kernels: one row per process, session 1 against the 8000 MT/s processes of the '
 144        'same round, wording "inside" or "outside", no percent. Sessions 2 and 3 are used for Q1 only.')
 145      w('- Rule V2: part C is grouped by the kernel that ran directly before.')
 146      w('- Rules V4 and F2: the kernel `read` of part C has no bwx12 run at 8000 MT/s.')
 147      w('- The rules contradict each other on part C. Rule F2 points 2 and 3 would use part L only for bwx12 and would '
 148        'present part C at 7200 MT/s only. Rules V1 point 2, V2 point 4 and V4 ask for a comparison of part C with '
 149        '8000 MT/s. This sheet follows V1, V2 and V4 (decision (r) in section 2).')</pre></td><td valign="top">Writes the headings of sections 4 and 4.1 and a summary of the rules: rule V1 points 2, 3 and 4, rule V3, rule V2, and rules V4 and F2. These lines compute no number.<ul><li>Line 134 says as template text that the rules were fixed before the run. <code>facts_text.py</code> tests it before it calls <code>section4</code>. The rules file states the time of its writing. That time must lie before the time of the first state line of the <code>go.sh</code> log, and it must equal the file time of the rules file [Ref1].</li><li>The two wordings of rule V1 point 2 are inserted from <code>DIFFERS</code> and <code>SAME</code>.</li><li>The last bullet says that the rules contradict each other on part C, and that the sheet follows V1, V2 and V4.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 150      b80 = sorted({r['boot'] for r in recs if r['dataset'] in BW12 + BW11 + BWX + ('A-1', 'A-2', 'A-3', 'B5a', 'B5b')})
 151      b72 = sorted({r['boot'] for r in recs if r['speed_MTps'] == 7200})
 152      need(len(b80) == 1 and b72 == [try6['boot']], 'one boot per memory speed')</pre></td><td valign="top">Check of the boots.<ul><li><code>b80</code>: the boot labels of the records of rows L-1 to L-4, R0, R0b, B7a, B7b, C3a, C3b, A-1, A-2, A-3, B5a and B5b, each label once. A boot label is a text such as <code>boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)</code>. Rows B5a-rev and B5b-rev are not in the list of line 150. Their records come from the same two folders as B5a and B5b [Ref3].</li><li><code>b72</code>: the boot ids of all records with a memory speed of 7200 MT/s, each id once.</li><li>Line 152: the build stops unless <code>b80</code> holds one label and <code>b72</code> holds only the boot id of <code>try6.txt</code>.</li><li><code>build_facts.py</code> sets the fields <code>speed_MTps</code>, <code>modules</code> and <code>boot</code> of a record. It does not read them from the files in the run folder [Ref3]. For a row of an earlier run, except F72d12, the three values come from the DIMM report, for the time in the name of the run folder. Every record of the rerun, of control I and of F72d12 gets the memory speed, the number of DIMM sockets and the boot id of <code>try6.txt</code>.</li><li>So the <code>b72</code> part of line 152 is true whatever the run files contain. It does not prove the boot of a run. The bullet in lines 153 to 156 names the two proofs.</li><li>Other code tests the boot of the 7200 MT/s rows. The integrity check <code>boot</code> of <code>build_facts.py</code> compares the boot id in every state line of the <code>go.sh</code> log and of the <code>go2.sh</code> log, and in the three <code>probe.txt</code> files of part A, with <code>try6.txt</code> [Ref3]. Line 1461 stops the build unless every integrity check passed. Lines 219 to 222 test row F72d12.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 153      w('- Each memory speed has exactly one boot. Every baseline row, supporting row and other-binary row at '
 154        '8000 MT/s comes from %s. Every 7200 MT/s row comes from boot %s. For the rerun the proof is in section 1.2. '
 155        'For row F72d12 it stands under the table below. The rows X2d12, X1d10, X1d10b and BASEd10 '
 156        'come from other boots. The table below names them.' % (b80[0], try6['boot'][:8]))</pre></td><td valign="top"><ul><li>This bullet of the sheet names the one 8000 MT/s boot and the first 8 characters of the 7200 MT/s boot id. It says that the proof for the rerun is in section 1.2, and that the proof for row F72d12 stands under the table.</li><li>Rows X2d12, X1d10, X1d10b and BASEd10 are 8000 MT/s rows that are not in the list of line 150. The bullet says as template text that they come from other boots. No <code>need</code> call of this file tests it. In the present sheet the row table gives them boots -2, -4, -3 and -1 of the DIMM report [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 157      gs = D['logs']['go']['states']
 158      w('- Label of the 7200 MT/s ranges of the rerun (rule V1 point 1): three sessions that ran within %s, all in '
 159        'boot %s. The rule text says "about 10 min (est.)". The value here is measured from the go.sh log.'
 160        % (dur((gs[-1]['utc'] - gs[0]['utc']).total_seconds()), try6['boot'][:8]))
 161      w('')
 162      w('Rows of earlier runs used in this section:')
 163      w('')</pre></td><td valign="top"><ul><li><code>gs</code> is the list of the state lines of the <code>go.sh</code> log.</li><li>The bullet gives the time from the first state line to the last state line as the time within which the three sessions ran. <code>dur</code> prints it in hours, minutes and seconds.</li><li>In the present log the last state line is the line <code>== end</code>. It stands after the state line of T72C4, the part C process that ran after the three sessions. So the printed time includes that process. Its present value is 10 min 9 s [Ref4].</li><li>Then the title line of the row table is written.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 164      rows = []
 165      for ds in ('A-1', 'A-2', 'A-3', 'L-1', 'L-2', 'L-3', 'L-4', 'R0', 'R0b', 'X2d12', 'F72d12', 'B7a', 'B7b', 'C3a',
 166                 'C3b', 'B5a', 'B5b', 'B5a-rev', 'B5b-rev', 'X1d10', 'X1d10b', 'BASEd10'):
 167          rs = sel(recs, dataset=ds)
 168          procs = {}
 169          for r in rs:
 170              procs.setdefault(r['proc_key'], r)
 171          loads = [p['load1_at_launch'] for p in procs.values()]
 172          bins = sorted({'%s (%s)' % (r['binary'], r['binary_sha256'][:8]) for r in rs})
 173          files = list(dict.fromkeys(r['file'] for r in rs))
 174          tags = list(dict.fromkeys(r['tag'] for r in rs if r['tag']))
 175          where = '%s: %s' % (rs[0]['folder'], ', '.join(files))</pre></td><td valign="top">Starts the table of the 22 earlier rows. For each row name <code>ds</code>:<ul><li><code>rs</code>: all records with this <code>dataset</code>.</li><li><code>procs</code>: the first record of each process, by <code>proc_key</code>. <code>loads</code>: the load at launch of each process.</li><li><code>bins</code>: the binaries, each with the first 8 characters of its sha256.</li><li><code>files</code>, <code>tags</code>: the csv file names and the process tags, each once, in record order.</li><li><code>where</code>: the folder and the file names.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 176          if ds in ('A-3', 'B7a', 'B7b', 'C3a', 'C3b', 'B5a', 'B5b', 'B5a-rev', 'B5b-rev'):
 177              where += ' (%d processes, tags %s to %s)' % (len(tags), tags[0], tags[-1])
 178          stop = sorted({'%s stop, %g s' % (r['stop'], r['min_ms'] / 1000) for r in rs})
 179          boot = rs[0]['boot'] if rs[0]['speed_MTps'] == 8000 else 'boot %s' % rs[0]['boot'][:8]
 180          srcs = source(ds, rs)
 181          if ds == 'F72d12':      # the folder holds no boot id: the proof stands under the table
 182              srcs += ', boot, modules and speed %s %s %s %s (proof under this table)' % (
 183                  ref(try6['path']), ref(try6['gaps_path']), ref(try6['boots_path']), ref(D['logs']['go']['path']))
 184          rows.append([ds, DESC[ds], where, ', '.join(bins), ', '.join(stop),
 185                       '%d MT/s, %d modules, %s' % (rs[0]['speed_MTps'], rs[0]['modules'], boot),
 186                       ('%.2f' % loads[0]) if len(loads) == 1 else '%.2f to %.2f' % (min(loads), max(loads)),
 187                       '%d / %d' % (len(rs), len(procs)), srcs])</pre></td><td valign="top"><ul><li>Lines 176-177: for A-3 and the rows of runner bwx the cell also gives the number of processes and the first and the last tag.</li><li><code>stop</code>: the stop rule and the interval length in seconds (<code>min_ms</code> / 1000). For rows A-1, A-2 and A-3 <code>build_facts.py</code> sets both as constants (<code>whole pass</code> and 500 ms). It does not read them from the csv file [Ref3].</li><li><code>boot</code>: the boot label of an 8000 MT/s row, or the first 8 characters of the boot id. Speed, modules and boot are taken from the first record of the row.</li><li>Lines 181-183: for F72d12 the Source cell also names <code>try6.txt</code>, <code>gaps.txt</code>, <code>boots.txt</code> and the <code>go.sh</code> log.</li><li>Line 186: the load at launch, as one value or as the lowest to the highest value of the processes, with 2 decimal places.</li><li>Line 187: the number of interval records and the number of processes of the row.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 188      L.extend(table(['Row', 'What it is', 'Folder and files', 'Binary (sha256, first 8 characters)', 'Stop rule, interval length',
 189                      'Memory speed, modules, boot', 'Load at launch (lowest to highest process)',
 190                      'Interval records in facts.json / processes', 'Source'], rows))
 191      w('- Column "Source": the csv files hold the rates. For the rows written by rx.sh or r0.sh the load is in '
 192        'launches.txt and the sha256 is in env.txt. For row R0 env.txt holds no sha256 %s, and the value comes from line %d '
 193        'of r0.sh %s. For the other rows the load is in the header lines of the csv file, and the sha256 is in probe.txt '
 194        'or env.txt of the run folder.'
 195        % (ref(os.path.join(D['rx']['R0']['folder'], 'env.txt')), D['rx']['R0']['env']['sha_line'], ref(os.path.join(W15, 'r0.sh'))))</pre></td><td valign="top">Appends the table with its 9 column titles. Then one bullet explains the column "Source". It inserts the number of the line of <code>r0.sh</code> that holds the sha256 of the binary of row R0.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 196      dimm_txt = fd._open(fd.DIMM_REPORT).read()
 197      x10 = {d: [r['GBps'] for r in sel(recs, dataset=d, kernel='oldread')] for d in ('X1d10', 'X1d10b', 'BASEd10')}
 198      need('Three more runs with changed TXREQ settings' in dimm_txt
 199           and all('%.1f / %.1f' % tuple(x10[d]) in dimm_txt for d in ('X1d10', 'X1d10b', 'BASEd10'))
 200           and 'One changed settings state gave 10 modules in two boots' in dimm_txt,
 201           'DIMM report: X1d10 and X1d10b are the runs with changed TXREQ settings, BASEd10 has the original settings')
 202      w('- Firmware settings of the 10-module rows: the DIMM report gives the old read values of X1d10 and X1d10b as '
 203        'runs with changed TXREQ settings, and those of BASEd10 as the run with the original settings (its sections '
 204        '6.1 and 6.2 %s). TXREQ is a group of firmware settings that were changed for another investigation.'
 205        % ref(fd.DIMM_REPORT))</pre></td><td valign="top">Check against the DIMM report.<ul><li><code>x10</code>: the oldread rates of the rows X1d10, X1d10b and BASEd10.</li><li>The format in line 199 takes exactly two rates per row. These are oldread at position 0 of round 0 and of round 1.</li><li>The build stops unless the report holds each pair as the text <code>a / b</code>, with 1 decimal place per rate (Python format <code>%.1f</code>).</li><li>The report must also hold two fixed phrases on the runs with changed TXREQ settings.</li><li>Then one bullet says which 10-module rows ran with changed settings. That assignment is template text. The check tests only that the texts are in the report. It does not test which pair the report gives for which settings.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 206      w('- The boot numbers are those of the boot history in the DIMM report %s.' % ref(fd.DIMM_REPORT))
 207      w('- From rows L-2 to L-4, R0 and R0b this sheet uses oldread at position 0 and asmread at position 1 only.')
 208      w('- The speed of the 2026-11-09 boot rests on the firmware setting, not on a reading of the applied speed '
 209        '(section 1.5, point 10).')
 210      fwx = c['fw']
 211      w('- Firmware settings of the two boots: section 1.5, point 13. In short: the two TXREQ settings were set back on '
 212        '%s. The settings list saved after that is equal to the list of the baseline boot in all %d readable values. '
 213        'No settings list exists from the boot of the rerun.' % (hmd(fwx['set_back']), fwx['readable']))</pre></td><td valign="top">Four bullets: the source of the boot numbers, the positions used from rows L-2 to L-4, R0 and R0b, the basis of the speed of the 2026-11-09 boot, and the firmware settings of the two boots. <code>fwx</code> supplies two values for the last bullet: the time at which the two TXREQ settings were set back, and the number of readable values of the settings list.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 214      # F72d12: its folder holds no boot id. Its process lies between two readings of the boot id of the rerun.
 215      f72env_txt = fd._open(os.path.join(f72dir, 'env.txt')).read()
 216      go0 = D['logs']['go']['states'][0]
 217      need(not re.search(r'boot|MemTotal|MT/s', f72env_txt) and fenv['n_lines'] == len(f72env_txt.splitlines()),
 218           'env.txt of F72d12 holds no boot id, no MemTotal and no memory speed')
 219      need(try6['utc'] &lt; f72la['utc'] &lt; f72la['rc_utc'] &lt; go0['utc'] and go0['boot'] == try6['boot']
 220           and try6['boots_first'] &lt;= f72la['utc'] and f72la['rc_utc'] &lt;= try6['boots_last']
 221           and try6['first_log_utc'] &lt;= f72la['utc'] and f72la['rc_utc'] &lt;= try6['last_log_utc'],
 222           'the F72d12 process lies between two readings of the same boot id and inside row 0 of boots.txt and gaps.txt')</pre></td><td valign="top">Checks for row F72d12. Its folder holds no boot id. The build stops unless all of these hold:<ul><li><code>env.txt</code> of the folder holds none of the texts <code>boot</code>, <code>MemTotal</code> and <code>MT/s</code>. Its line count equals the count that the parser stored.</li><li>The times lie in this order: the time of <code>try6.txt</code>, the launch line of the F72d12 process, its rc line, the first state line of the <code>go.sh</code> log (<code>go0</code>).</li><li>That state line holds the boot id of <code>try6.txt</code>.</li><li>The process lies inside the two times of row 0 of <code>boots.txt</code>, and inside the first and last log time of row 0 of <code>gaps.txt</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 223      w('- Boot, module count and speed of row F72d12. Its folder holds no boot id, no MemTotal and no memory speed: '
 224        'env.txt has %d lines with the date, the Linux release, the load, the process list and the binary %s. Its '
 225        'process ran from %s to %s %s. Line 1 of try6.txt holds the time %s, %.0f s before that launch. The file holds the boot id `%s` '
 226        '(line %d), MemTotal %d kB (line %d), "This system has %d DIMM sockets" (line %d) and "%d Configured Memory '
 227        'Speed: %d MT/s" (line %d) %s. The go.sh log holds the same boot id at %s (line %d) %s. Linux creates a boot id '
 228        'once per start (see the word list). So Linux was not started again between these two readings, and the F72d12 '
 229        'process ran in the boot of the rerun. Two more records fit this. Row 0 of boots.txt holds the same boot id '
 230        'with the times %s and %s (line %d) %s. Row 0 of gaps.txt spans %s to %s (line %d) %s. Limit, as for the rerun: '
 231        'the speed and the module count were not read during the process.'
 232        % (fenv['n_lines'], ref(os.path.join(f72dir, 'env.txt')), hm(f72la['utc']), hm(f72la['rc_utc']),
 233           ref(os.path.join(f72dir, 'launches.txt')), hm(try6['utc']), (f72la['utc'] - try6['utc']).total_seconds(),
 234           try6['boot'], try6['boot_line'], try6['memtotal_kB'], try6['memtotal_line'], try6['dimm_sockets'],
 235           try6['dimm_line'], try6['speed_count'], try6['speed_MTps'], try6['speed_line'], ref(try6['path']),
 236           hm(go0['utc']), go0['line'], ref(D['logs']['go']['path']), hm(try6['boots_first']), hm(try6['boots_last']),
 237           try6['boots_line'], ref(try6['boots_path']), hm(try6['first_log_utc']), hm(try6['last_log_utc']),
 238           try6['gaps_line'], ref(try6['gaps_path'])))
 239      w('')
 240</pre></td><td valign="top">Writes the proof as one bullet. The values are inserted from the files:<ul><li>The line count of <code>env.txt</code>, and the launch time and the rc time of the process.</li><li>From <code>try6.txt</code>: its time, the boot id, MemTotal, the number of DIMM sockets, and the memory speed with the count that stands before it in the file. Each has its line number. The line number 1 of the time is typed in the template. The parser reads the time from the first line of the file [Ref2].</li><li>The line of the <code>go.sh</code> log that holds the same boot id, with its time.</li><li>Row 0 of <code>boots.txt</code> and row 0 of <code>gaps.txt</code>, with their times and line numbers.</li></ul>The bullet ends with the limit: the speed and the module count were not read during the process.</td></tr>
<tr><td colspan="2"><b>Section 4.1: hardware error records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 241      # ---- hardware error records during the bwx12 and bwx11 rows of the 2026-11-09 boot
 242      hw = D['hw']
 243      p13 = D['probe13']
 244      allrec = [e for h in hw for e in h['records']]
 245      need(allrec and {e['severity'] for e in allrec} == {'corrected'}, 'the records in the process windows are all "corrected"')</pre></td><td valign="top"><code>hw</code> holds one entry per process of rows L-1 to L-4, R0 and R0b, with the hardware error records in its window. <code>p13</code> holds the path of the saved journal (<code>p13['h5']</code>). <code>allrec</code> is the list of all these records. The build stops unless the list is not empty and every record has the severity <code>corrected</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 246      w('Hardware error records during the bwx12 and bwx11 rows of the 2026-11-09 boot (rows L-1 to L-4, R0, R0b):')
 247      w('')
 248      w('- The journal is the one of section 1.5, point 8 %s. One record is one line "Hardware error from APEI ..." of '
 249        'the journal.' % ref(p13['h5']))
 250      w('- The window of a process is the time from its launch line to its rc line in launches.txt. rx.sh and r0.sh '
 251        'write the launch line directly before they start the process %s %s. In a table cell " / " separates the '
 252        'records of different seconds.'
 253        % (ref(os.path.join(W15, 'rx.sh')), ref(os.path.join(W15, 'r0.sh'))))
 254      w('- Time resolution. The journal and launches.txt give whole seconds. So a record that the journal dates N seconds '
 255        'after the launch line lies between N - 1 and N + 1 seconds after the process start (est.). The csv file gives '
 256        'the start and the end of every interval in seconds since the process start (T rows, columns t_start_s and '
 257        't_end_s). The journal time is the time of the log line. The time of the hardware event itself is not on record.')
 258      w('- The table below tests only the intervals that this sheet uses: oldread at position 0 and asmread at position 1. '
 259        'The second table of this block lists the intervals of all kernels and positions.')
 260      w('')
 261</pre></td><td valign="top">Writes the title of the block and four bullets: what one record is, what the window of a process is, the time resolution of 1 s, and which intervals the first table tests. These are the intervals that the sheet uses: oldread at position 0 and asmread at position 1. The bullets insert reference labels only, no number.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 262      def kind_txt(e):
 263          iv = e['interval']
 264          if e['kind'] == 'outside':
 265              return 'outside'
 266          span = '%s, round %d (%s s to %s s after the process start, I row in line %d)' % (
 267              iv['kernel'], iv['round'], g(iv['t_start']), g(iv['t_end']), iv['line'])
 268          if e['kind'] == 'inside':
 269              return 'inside ' + span
 270          need(e['offset_s'] - 1 &lt; iv['t_start'], 'a record that may lie inside an interval lies at its start')
 271          return 'before or inside ' + span</pre></td><td valign="top"><code>kind_txt</code> returns the position of one error record <code>e</code> against the used intervals, as text.<ul><li><code>outside</code>: the record touches no used interval.</li><li><code>inside</code> plus the interval: kernel, round, start and end in seconds after the process start, and the line of its I row. The start is the earliest thread start and the end is the latest thread end of the T rows [Ref2].</li><li><code>before or inside</code> plus the interval, for the kind <code>possible</code>. Line 270 stops the build unless the 2 s span of the record starts before the interval starts.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 272      rows = []
 273      for h in hw:
 274          la = h['launch']
 275          by_t = {}
 276          for e in h['records']:
 277              by_t.setdefault(e['utc'], []).append(e)
 278          need(all(len({kind_txt(e) for e in es}) == 1 for es in by_t.values()), 'the records of one second have one position')
 279          groups = sorted(by_t.items())
 280          rows.append([h['dataset'], h['tag'], hmd(la['utc']), hmd(la['rc_utc']), len(h['records']),
 281                       ' / '.join('%s: %s' % (hmd(t), ', '.join(str(e['line']) for e in es)) for t, es in groups) or '-',
 282                       ' / '.join('%.0f' % es[0]['offset_s'] for t, es in groups) or '-',
 283                       ' / '.join(kind_txt(es[0]) for t, es in groups) or '-',
 284                       '%s %s' % (ref(os.path.join(h['folder'], 'launches.txt')), ref(h['file']))])
 285      L.extend(table(['Row', 'Process', 'Launch line', 'rc line', 'Records in the window',
 286                      'Journal time: journal lines of the records', 'Seconds after the launch line',
 287                      'Position against the intervals used', 'Source'], rows))</pre></td><td valign="top">Builds the first table: one row per process of <code>hw</code>.<ul><li><code>by_t</code> groups the records of the process by their journal time. That time has a resolution of 1 s.</li><li>Line 278: the build stops unless all records of one second have the same position text.</li><li>Columns: row, process tag, time of the launch line, time of the rc line, number of records in the window, journal time with the journal lines of the records, whole seconds after the launch line, position (<code>kind_txt</code>), and the source files.</li><li>A process without records gets <code>-</code> in the three record columns.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 288      ins = [(h, e) for h in hw for e in h['records'] if e['kind'] == 'inside']
 289      pos = [(h, e) for h in hw for e in h['records'] if e['kind'] == 'possible']
 290      n_out = sum(1 for e in allrec if e['kind'] == 'outside')
 291      need(len(ins) == 2 and ins[0][1]['interval'] is ins[1][1]['interval'] and ins[0][1]['utc'] == ins[1][1]['utc'],
 292           'two records of one second lie inside one used interval')
 293      need(len(pos) == 2 and pos[0][1]['interval'] is pos[1][1]['interval'] and pos[0][1]['utc'] == pos[1][1]['utc'],
 294           'two records of one second may lie inside one used interval')</pre></td><td valign="top"><ul><li><code>ins</code>: the records of kind <code>inside</code>, each with its process. <code>pos</code>: the records of kind <code>possible</code>. Here the name <code>pos</code> is a list of records, not a position.</li><li><code>n_out</code>: the number of records of kind <code>outside</code>.</li><li>Lines 291-292: the build stops unless <code>ins</code> holds exactly 2 records that lie in the same interval and have the same journal time.</li><li>Lines 293-294: the same check for <code>pos</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 295      (hi_, ei), (hp, ep) = ins[0], pos[0]
 296      ivi, ivp = ei['interval'], ep['interval']
 297      low_a = min(P12a, key=lambda r: r['GBps'])
 298      need((ivi['kernel'], ivi['pos']) == ('asmread', 1) and hi_['dataset'] in BW12
 299           and (low_a['dataset'], low_a['tag'], low_a['line']) == (hi_['dataset'], hi_['tag'], ivi['line']),
 300           'the interval with records inside it is the lowest asmread interval of the pool L-1 to L-4')
 301      need((ivp['kernel'], ivp['pos'], ivp['round']) == ('oldread', 0, 0) and hp['dataset'] == 'L-1',
 302           'the interval that may hold records is oldread, round 0 of L-1')
 303      P12a_wo = [r for r in P12a if r is not low_a]
 304      c['hw'] = dict(inside=(hi_, ei), possible=(hp, ep), n_out=n_out, P12a_wo=P12a_wo, low_a=low_a)</pre></td><td valign="top">Finds the two used intervals with records, and the lowest asmread rate of the pool.<ul><li><code>ivi</code>: the interval with the 2 records inside it. <code>ivp</code>: the interval of the 2 records of kind <code>possible</code>.</li><li><code>low_a</code>: the record with the lowest <code>GBps</code> in <code>P12a</code> (asmread at position 1 of rows L-1 to L-4). In the present sheet it is 288.54 GB/s, round 1 of process p2add in row L-2 [Ref4].</li><li>Lines 298-300: the build stops unless <code>ivi</code> is asmread at position 1 of a row L-1 to L-4, and <code>low_a</code> is this interval (same row, same tag, same line of the I row).</li><li>Lines 301-302: the build stops unless <code>ivp</code> is oldread at position 0, round 0, of row L-1.</li><li><code>P12a_wo</code>: the list <code>P12a</code> without the record <code>low_a</code>. <code>P12a</code> itself is not changed. Section 4.4 compares the 7200 MT/s rows with <code>P12a_wo</code> again.</li><li><code>c['hw']</code> stores these values for the later sections.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 305      w('- All %d records in these windows have the severity "corrected".' % len(allrec))
 306      w('- Row %s: the %d records at %s (journal lines %s) are %.0f s after the launch line. %s, round %d was timed from '
 307        '%s s to %s s after the process start (T rows in lines %d to %d %s). So the records fall before this interval or '
 308        'inside it. The interval gave %s GB/s.'
 309        % (hp['dataset'], len(pos), hmd(ep['utc']), ' and '.join(str(e['line']) for _, e in pos), ep['offset_s'],
 310           ivp['kernel'], ivp['round'], g(ivp['t_start']), g(ivp['t_end']), ivp['T_first'], ivp['T_last'], ref(hp['file']),
 311           g(ivp['total'])))
 312      w('- Row %s, process %s: the %d records at %s (journal lines %s) are %.0f s after the launch line. %s, round %d '
 313        'was timed from %s s to %s s after the process start (T rows in lines %d to %d, I row in line %d %s). So the '
 314        'records fall inside this interval. It gave %s GB/s, the lowest asmread value of the pool L-1 to L-4 '
 315        '(section 4.4).'
 316        % (hi_['dataset'], hi_['tag'], len(ins), hmd(ei['utc']), ' and '.join(str(e['line']) for _, e in ins),
 317           ei['offset_s'], ivi['kernel'], ivi['round'], g(ivi['t_start']), g(ivi['t_end']), ivi['T_first'], ivi['T_last'],
 318           ivi['line'], ref(hi_['file']), g(ivi['total'])))
 319      w('- The other %d records of these windows fall outside the intervals that this sheet uses.' % n_out)
 320      w('- Processes with 0 records in their window: %s.'
 321        % ', '.join('%s %s' % (h['dataset'], h['tag']) for h in hw if not h['records']))</pre></td><td valign="top">Five bullets with inserted values:<ul><li>The number of records in all windows.</li><li>Row L-1: the 2 records that fall before or inside oldread, round 0, with the rate of that interval (<code>ivp['total']</code>).</li><li>The process with the 2 records inside its asmread interval, with the rate of that interval (<code>ivi['total']</code>).</li><li>The number of records outside the used intervals (<code>n_out</code>).</li><li>The processes with 0 records in their window.</li></ul><code>total</code> is the sum over the T rows of the interval of bytes / elapsed_s / 1e9. A record holds the same value in <code>GBps</code> [Ref2] [Ref3]. It is printed with 2 decimal places.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 322      need(try6['gaps_hwerr'] == 0 and try6['gaps_dimm'] == try6['dimm_sockets'], 'row 0 of gaps.txt: hwerr=0, 12 modules')
 323      w('- F72d12: line %d of gaps.txt shows "hwerr=%d" for row 0, with the kernel log times %s to %s %s. Row 0 of '
 324        'boots.txt holds the boot id of the rerun %s. The F72d12 process ran from %s to %s %s. By its name the field '
 325        'counts hardware error records. The script that wrote gaps.txt is not among the files of this task. So its '
 326        'count rule was not checked.'
 327        % (try6['gaps_line'], try6['gaps_hwerr'], hm(try6['first_log_utc']), hm(try6['last_log_utc']),
 328           ref(try6['gaps_path']), ref(try6['boots_path']), hm(f72la['utc']), hm(f72la['rc_utc']),
 329           ref(os.path.join(f72dir, 'launches.txt'))))
 330      w('- Rerun (parts A, L and C, control I): Insufficient data. The kernel log was not read (section 1.5, point 8).')
 331      w('- Not counted in this sheet: the records during the rows of runner bwx (B7a to B5b-rev) and during the rows of '
 332        'other boots (X2d12, X1d10, X1d10b, BASEd10). No wording by rule V1 point 2 rests on these rows. For the rows '
 333        'of runner bwx the same journal and the T rows of their csv files would give the count.')</pre></td><td valign="top">Line 322: the build stops unless row 0 of <code>gaps.txt</code> shows <code>hwerr=0</code> and as many DIMMs as <code>try6.txt</code> shows DIMM sockets. Then three bullets:<ul><li>F72d12: the <code>hwerr</code> value of <code>gaps.txt</code>, and the note that the count rule of that file was not checked.</li><li>Rerun: the template text "Insufficient data", with the reason that the Linux kernel log was not read.</li><li>Template text on the rows whose records were not counted: the rows of runner bwx and the rows of other boots.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.1: hypothesis on corrected records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 334      # ---- the hypothesis on corrected records. The csv files hold more than one interval with records: every interval
 335      # (all kernels and positions) of these processes with a record, against the same kernel at the same position in
 336      # the other round of the same process (build_facts.hw_compare).
 337      hc = D['hw_cmp']
 338      crow, cbor, ccl = hc['rows'], hc['border'], hc['clean']
 339      sg = lambda x: '0.00' if float(g(x)) == 0 else (g(x) if x &lt; 0 else '+' + g(x))      # a signed difference
 340      need(not any(r['other_has_records'] for r in crow)
 341           and not any(x['other_has_records'] for b in cbor for x in b['intervals']),
 342           'no other-round interval of the comparison has a record inside it or at its border')</pre></td><td valign="top"><code>hc</code> holds the comparison that <code>build_facts.py</code> made [Ref3].<ul><li><code>crow</code>: every interval, of all kernels and positions, to which records can be assigned. That means: the records lie inside it, or it is the only interval that their 2 s span touches. Each entry has the field <code>diff</code>: the rate of the interval minus the rate of its other round, in GB/s.</li><li><code>cbor</code>: the records whose 2 s span touches two intervals. The sheet says that such records lie at the border of two intervals.</li><li><code>ccl</code>: the positions at which neither round has a record inside it or at its border. There <code>diff</code> is the rate of round 1 minus the rate of round 0. Only the processes with at least one record supply such positions.</li><li><code>sg</code>: prints a difference with 2 decimal places and its sign. A value that rounds to zero prints as <code>0.00</code>.</li><li>Lines 340-342: the build stops when an other-round interval of the comparison has a record inside it or at its border.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 343      rp = [r for r in crow if r['iv'] is ivp]
 344      ri = [r for r in crow if r['iv'] is ivi]
 345      more = [r for r in crow if not r['used']]
 346      need(len(rp) == 1 and len(ri) == 1 and len(more) + 2 == len(crow) and rp[0]['where'] == 'before or inside'
 347           and all(r['where'] == 'inside' for r in crow if r is not rp[0]),
 348           'the two used intervals with records are in the comparison; every other interval has its records inside it')
 349      rp, ri = rp[0], ri[0]
 350      n_more, n_bor = sum(len(r['records']) for r in more), sum(len(b['records']) for b in cbor)
 351      need(n_more + n_bor == n_out and len(crow) &gt; 2 and cbor and all(len(b['intervals']) == 2 for b in cbor),
 352           'the records outside the used intervals lie inside other intervals or at the border of two intervals')</pre></td><td valign="top"><ul><li><code>rp</code>, <code>ri</code>: the entries of <code>crow</code> for the oldread interval <code>ivp</code> and for the asmread interval <code>ivi</code>. <code>more</code>: the entries of the intervals that the sheet does not use.</li><li>Lines 346-348: the build stops unless each of the two used intervals has exactly one entry and all other entries are in <code>more</code>. The records of <code>rp</code> must lie <code>before or inside</code>. The records of every other entry must lie <code>inside</code>.</li><li><code>n_more</code>, <code>n_bor</code>: the number of records in the entries of <code>more</code>, and the number of records at the borders.</li><li>Lines 351-352: the build stops unless these two numbers add up to <code>n_out</code>, <code>crow</code> has more than 2 entries, at least one border exists, and every border lies between exactly 2 intervals.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 353      LIM = 1.0       # GB/s: a difference between the two rounds above this value is counted as a difference
 354      low = sorted((r for r in crow if r['diff'] &lt; -LIM), key=lambda r: r['diff'])
 355      rest = [r for r in crow if not r['diff'] &lt; -LIM]
 356      cbig = [x for x in ccl if abs(x['diff']) &gt; LIM]
 357      cmax = max(ccl, key=lambda x: abs(x['diff']))
 358      low_in = [r for r in low if abs(r['diff']) &lt; abs(cmax['diff'])]</pre></td><td valign="top">The threshold and the groups of this comparison.<ul><li><code>LIM</code> = 1.0 GB/s. A difference between the two rounds counts only above this value. This file sets the value. The view is not part of the fixed rules (line 377).</li><li><code>low</code>: the entries of <code>crow</code> that lie more than 1.0 GB/s below their other round, the largest drop first.</li><li><code>rest</code>: all other entries of <code>crow</code>.</li><li><code>cbig</code>: the positions without records at which the two rounds differ by more than 1.0 GB/s.</li><li><code>cmax</code>: the position without records with the largest difference between the two rounds.</li><li><code>low_in</code>: the entries of <code>low</code> whose difference is smaller than the difference of <code>cmax</code>. Both are compared without their sign.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 359      need(low and low[0] is ri and rest and all(abs(r['diff']) &lt; LIM for r in rest) and any(r is rp for r in rest)
 360           and rp['diff'] &gt; 0 and min(r['diff'] for r in rest) &lt; 0,
 361           'intervals with records: some lie more than 1 GB/s below their other round, the others differ by less than '
 362           '1 GB/s, and oldread of L-1 is higher with records')
 363      need(len(low) - len(low_in) == 1 and low_in and abs(ri['diff']) &gt; abs(cmax['diff']) and cbig,
 364           'only the asmread interval of p2add differs by more than the largest difference between two rounds without records')
 365      need((cmax['dataset'], cmax['tag'], cmax['pos']) == (hi_['dataset'], hi_['tag'], ivi['pos'] + 1) and cmax['diff'] &lt; 0
 366           and ivi['round'] == 1,
 367           'the largest difference without records is at the position directly after the asmread interval with records, '
 368           'lower in the round of the records')
 369      need({(x['dataset'], x['tag']) for x in ccl} == {(r['dataset'], r['tag']) for r in crow},
 370           'the positions without records are counted in the processes of the table')</pre></td><td valign="top">Four checks. The build stops unless the data show each pattern that the text below states.<ul><li>Lines 359-362: <code>low</code> is not empty, and its largest drop is the asmread interval <code>ri</code>. Every entry of <code>rest</code> differs by less than 1.0 GB/s. The oldread interval <code>rp</code> is in <code>rest</code> and is higher than its other round. At least one entry of <code>rest</code> is lower than its other round.</li><li>Lines 363-364: exactly one entry of <code>low</code> differs by at least as much as <code>cmax</code>, and <code>ri</code> differs by more than <code>cmax</code>. <code>low_in</code> and <code>cbig</code> are not empty.</li><li>Lines 365-368: <code>cmax</code> lies in the process of <code>ivi</code>, at the position directly after it. Round 1 is the lower round at <code>cmax</code>, and <code>ivi</code> is in round 1.</li><li>Lines 369-370: the positions without records come from the same processes as the entries of <code>crow</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 371      bdiff = [x['diff'] for b in cbor for x in b['intervals']]
 372      c['hw']['cmp'] = dict(n=len(crow), low=low, rest=rest, cmax=cmax, n_clean=len(ccl), n_big=len(cbig), lim=LIM)
 373      c['hw']['cmp']['lst'] = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]</pre></td><td valign="top"><code>bdiff</code>: the differences of the border intervals against their other round. <code>c['hw']['cmp']</code> stores the counts, the groups, <code>cmax</code> and <code>LIM</code> for section 6. The stored function <code>lst</code> joins texts with commas, and with <code>and</code> before the last text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 374      w('- Hypothesis, not tested: a corrected record lowers the rate of the interval in which it falls. The files on '
 375        'hand hold more than one interval with records. The table below lists every interval of the processes above, '
 376        'of all kernels and positions, to which records can be assigned: the records fall inside it, or before or '
 377        'inside it. This view was added after the numbers were seen. It is not part of the fixed rules.')
 378      w('')
 379      w('Intervals with records, all kernels and positions (rows L-1 to L-4, R0, R0b). "Other round" is the interval of '
 380        'the same kernel at the same position in the other round of the same process. No other-round interval of this '
 381        'table has a record inside it or at its border. The position of the records follows the rule of the table '
 382        'above (1 s resolution, est.). A difference is computed from the values before rounding (first lines of this '
 383        'sheet).')
 384      w('')
 385      L.extend(table(['Row', 'Process', 'Interval with records', 'I row line', 'Journal lines of the records',
 386                      'Position of the records', 'Rate, GB/s', 'Other round: rate, GB/s (I row line)',
 387                      'With records minus other round, GB/s', 'Used by this sheet', 'Source'],
 388                     [[r['dataset'], r['tag'], '%s, round %d, position %d' % (r['iv']['kernel'], r['iv']['round'], r['iv']['pos']),
 389                       r['iv']['line'], ', '.join(str(e['line']) for e in r['records']), r['where'], g(r['iv']['total']),
 390                       '%s (%d)' % (g(r['other']['total']), r['other']['line']), sg(r['diff']),
 391                       'yes' if r['used'] else 'no', '%s %s' % (ref(r['file']), ref(p13['h5']))] for r in crow]))</pre></td><td valign="top">Writes the hypothesis as one bullet, an intro text and the second table. The table has one row per entry of <code>crow</code>. Its columns:<ul><li>Row, process, and the interval (kernel, round, position) with the line of its I row.</li><li>The journal lines of the records, and their position (<code>inside</code> or <code>before or inside</code>).</li><li>The rate of the interval, and the rate of the other round with the line of its I row.</li><li>The difference (<code>sg</code>), whether the sheet uses the interval, and the sources.</li></ul>The rates are printed with 2 decimal places. The difference is computed before rounding.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 392      # the loop names of this block that the word list does not define (the names come from the csv files)
 393      in_words = {'oldread', 'asmread', 'read', 'read_nop96', 'read_nop256', 'read_1pl'}
 394      loops = ({r['iv']['kernel'] for r in crow} | {x['iv']['kernel'] for b in cbor for x in b['intervals']} | {cmax['kernel']}) - in_words
 395      loops = sorted(loops, key=lambda k: (re.sub(r'\d+$', '', k), int(re.search(r'\d*$', k).group(0) or 0)))     # by stem, then by number
 396      with open(os.path.join(W15, 'FINDINGS.md'), encoding='utf-8') as fh:
 397          f2 = re.search(r'^## F2\..*?(?=^## )', fh.read(), re.S | re.M)          # its section F2, up to the next heading
 398      need(loops and f2 and all(re.search(r'\b%s\b' % re.escape(k), f2.group(0)) for k in loops)
 399           and {r['dataset'] for r in crow} | {b['dataset'] for b in cbor} | {cmax['dataset']} &lt;= set(BW12) | set(BW11),
 400           'the other loop names of the comparison are named in section F2 of FINDINGS.md, and their rows are rows of bwx12 and bwx11')
 401      w('%s are other test loops of bwx12 and bwx11. FINDINGS.md names them in its section F2 %s.'
 402        % (c['hw']['cmp']['lst'](loops), ref(os.path.join(W15, 'FINDINGS.md'))))
 403      w('')</pre></td><td valign="top">Names the test loops of this block that the word list of the sheet does not define.<ul><li><code>loops</code>: the kernel names of <code>crow</code>, of the border intervals and of <code>cmax</code>, without the six names of <code>in_words</code>. They are sorted by the name without its trailing number, then by that number.</li><li>Lines 396-397 read section F2 of <code>FINDINGS.md</code>, from the heading <code>## F2.</code> to the next line that starts with <code>## </code>.</li><li>The build stops unless every name appears in that section as a whole word, and all rows of the comparison are rows of bwx12 or bwx11.</li><li>One sentence then lists the names.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 404      btxt = ['%d record%s of %s %s, %.0f s after the launch line (journal line%s %s), between %s of round %d'
 405              % (len(b['records']), '' if len(b['records']) == 1 else 's', b['dataset'], b['tag'], b['records'][0]['offset_s'],
 406                 '' if len(b['records']) == 1 else 's', ' and '.join(str(e['line']) for e in b['records']),
 407                 ' and '.join(x['iv']['kernel'] for x in b['intervals']), b['intervals'][0]['iv']['round']) for b in cbor]
 408      need(all(len({x['iv']['round'] for x in b['intervals']}) == 1
 409               and b['intervals'][1]['iv']['pos'] == b['intervals'][0]['iv']['pos'] + 1 for b in cbor),
 410           'a border lies between two neighbour intervals of one round')
 411      lst = lambda xs: xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]</pre></td><td valign="top"><code>btxt</code> holds one text per border: the number of records, the row and the process, the seconds after the launch line, the journal lines, the two kernels and the round. The build stops unless the two intervals of each border are in the same round and at neighbour positions. <code>lst</code> joins texts with commas, and with <code>and</code> before the last text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 412      w('- Of the %d records outside the used intervals, %d fall inside the %d intervals of this table that the sheet '
 413        'does not use. The other %d lie at the border of two intervals. The 1 s resolution cannot assign them to one '
 414        'interval: %s. These %d intervals differ from their other round by %s to %s GB/s. They are not in the table.'
 415        % (n_out, n_more, len(more), n_bor, ', and '.join(btxt), sum(len(b['intervals']) for b in cbor),
 416           sg(min(bdiff)), sg(max(bdiff))))
 417      w('- What fits: %d of the %d intervals of the table are more than %g GB/s below their other round (%s GB/s). The '
 418        'largest difference belongs to the asmread interval of %s (%s GB/s), the lowest asmread value of the pool L-1 to '
 419        'L-4. No interval of the table is more than %g GB/s above its other round.'
 420        % (len(low), len(crow), LIM, lst([g(-r['diff']) for r in reversed(low)]), ri['tag'], g(ivi['total']), LIM))
 421      w('- What does not fit: the other %d intervals differ from their other round by less than %g GB/s (%s to %s GB/s). '
 422        'One of them is %s, round %d of row %s. It gave %s GB/s with records before or inside it. Round %d, without '
 423        'records, gave %s GB/s.'
 424        % (len(rest), LIM, sg(min(r['diff'] for r in rest)), sg(max(r['diff'] for r in rest)), ivp['kernel'], ivp['round'],
 425           rp['dataset'], g(ivp['total']), rp['other']['round'], g(rp['other']['total'])))
 426      w('- Limit: the two rounds of a process differ without records too. These %d processes have %d positions at '
 427        'which neither round has a record inside it or at its border. At %d of them the two rounds differ by more than '
 428        '%g GB/s. The largest difference is %s GB/s (%s of %s, lower in round %d, directly after the asmread interval '
 429        'with records). So %d of the %d lower intervals of the table (%s GB/s) are within the differences seen without '
 430        'records, and 1 (%s GB/s) is above them.'
 431        % (len({(r['dataset'], r['tag']) for r in crow}), len(ccl), len(cbig), LIM, g(abs(cmax['diff'])), cmax['kernel'],
 432           cmax['tag'], ivi['round'], len(low_in), len(low), ' and '.join(g(-r['diff']) for r in reversed(low_in)),
 433           g(-ri['diff'])))
 434      w('- This comparison is not a test of the hypothesis. Each interval has one other round to compare with. The '
 435        'comparison was chosen after the numbers were seen.')
 436      w('- Measurement that would confirm or reject it: a run that stores the kernel log time of every record beside the '
 437        'interval times, at both memory speeds (reading the kernel log needs root). More data are on hand and were not '
 438        'compared here: the records during the rows of runner bwx (see "Not counted in this sheet" above).')
 439      w('')</pre></td><td valign="top">Writes six bullets. The first four insert values:<ul><li>Records outside the used intervals: <code>n_more</code> fall inside the intervals of <code>more</code>, and <code>n_bor</code> lie at a border. The border intervals differ from their other round by the lowest to the highest value of <code>bdiff</code>.</li><li>What fits: <code>len(low)</code> of the <code>len(crow)</code> intervals lie more than <code>LIM</code> below their other round. The drops are printed as positive values, the smallest first.</li><li>What does not fit: the <code>len(rest)</code> other intervals, with the lowest and the highest of their differences, and the two rates of oldread of row L-1.</li><li>Limit: the number of positions without records (<code>len(ccl)</code>), how many of them differ by more than <code>LIM</code> (<code>len(cbig)</code>), the largest such difference, and the number of entries of <code>low_in</code>. The count in "and 1 ... is above them" is typed in the template. Line 363 tests it.</li><li>Template text: the comparison is not a test of the hypothesis.</li><li>Template text: the measurement that would confirm or reject the hypothesis.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.2: old read kernel, part A (<code>bw_old read</code>)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 440
 441      # ---- 4.2 old read
 442      w('### 4.2 Old read kernel')
 443      w('')
 444      w('**Part A, bw_old read.**')
 445      w('')
 446      a1o, a2o, a3o = (sel(recs, dataset=d, binary='bw_old', kernel='read') for d in ('A-1', 'A-2', 'A-3'))
 447      L.extend(ranges([('part A, sessions 1 to 3', 'rerun (one row per process is in section 3.1)', A72o),
 448                       ('A-1', DESC['A-1'], a1o), ('A-2', DESC['A-2'], a2o), ('A-3', DESC['A-3'], a3o),
 449                       ('pool A-1 to A-3', 'all like-for-like 8000 MT/s intervals of bw_old read', A80o)]))
 450      L.extend(cmps('A', 'bw_old read', [('part A, sessions 1 to 3', A72o, [
 451          ('A-1', a1o, False), ('A-2', a2o, False), ('A-3', a3o, False), ('pool A-1 to A-3', A80o, True)])]))</pre></td><td valign="top"><ul><li><code>a1o</code>, <code>a2o</code>, <code>a3o</code>: the records of rows A-1, A-2 and A-3 with <code>binary</code> = <code>bw_old</code> and <code>kernel</code> = <code>read</code>.</li><li>Lines 447-449: the range table. Its rows are part A of the rerun (<code>A72o</code>, sessions 1 to 3), A-1, A-2, A-3 and the pool A-1 to A-3 (<code>A80o</code>). In the present sheet <code>A72o</code> holds 18 intervals and <code>A80o</code> holds 21 intervals [Ref4].</li><li>Lines 450-451: <code>cmps</code> tests the range of <code>A72o</code> against four scopes: A-1, A-2, A-3 and the pool. Only the pool has <code>decides</code> = True. So only the test against the pool gets a wording.</li><li>Each test is also stored in <code>V['q2_rows']</code> with part <code>A</code> and kernel <code>bw_old read</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 452      b80 = rng(A80o)
 453      outs = []
 454      for p in N['pa']:
 455          a = rng(p['old'])
 456          if a['lo'] &gt; b80['hi']:
 457              outs.append('The process of session %d, round %d (%s GB/s) lies above it.' % (p['session'], p['round'], sp(a)))
 458          elif a['hi'] &lt; b80['lo']:
 459              outs.append('The process of session %d, round %d (%s GB/s) lies below it.' % (p['session'], p['round'], sp(a)))</pre></td><td valign="top">A check per process of part A.<ul><li><code>b80</code> is now the range of the pool A-1 to A-3. In line 150 the same name held the boot labels.</li><li><code>N['pa']</code> has one entry per session and round. <code>p['old']</code> holds the 3 <code>bw_old read</code> intervals of that process.</li><li>A sentence is noted in <code>outs</code> when the lowest of the 3 rates lies above the highest rate of the pool.</li><li>A sentence is also noted when the highest of the 3 rates lies below the lowest rate of the pool.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 460      w('- Wording by rule V1 point 2: "%s". n at 7200 MT/s: %s. n at 8000 MT/s: %s.'
 461        % (cAo['wording'], nn(cAo['a'], sessions=True), nn(cAo['b'])))
 462      w('- The test cannot exclude a difference of about %s %% (est. from one boot). That is the width of the 8000 MT/s '
 463        'range.' % pc(cAo['width']))
 464      if outs:
 465          w('- The 7200 MT/s range is wider than the 8000 MT/s range. %s The other %d processes overlap it.'
 466            % (' '.join(outs), len(N['pa']) - len(outs)))
 467      w('')
 468</pre></td><td valign="top">Three bullets:<ul><li>The wording of the test against the pool (<code>cAo['wording']</code>), with n at 7200 MT/s and n at 8000 MT/s.</li><li>The width of the 8000 MT/s range in percent with 1 decimal place (<code>cAo['width']</code>), as the size that the test cannot exclude.</li><li>Only when <code>outs</code> is not empty: the sentence "The 7200 MT/s range is wider than the 8000 MT/s range", the noted sentences, and the number of the other processes. Lines 464 to 466 do not compare the two widths. <code>facts_text.py</code> compares them after the call of <code>section4</code>, when it builds section 0 [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.2: old read kernel, part L (<code>oldread</code>)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 469      w('**Part L, oldread (position 0, the first interval of each round).**')
 470      w('')
 471      lrows = lambda k, pos: [(d, DESC[d], sel(recs, dataset=d, kernel=k, pos=pos)) for d in BW12]
 472      orows = lambda k, pos: [(d, DESC[d], sel(recs, dataset=d, kernel=k, pos=pos)) for d in BW11]
 473      x2o, x2a = sel(recs, dataset='X2d12', kernel='oldread'), sel(recs, dataset='X2d12', kernel='asmread')
 474      sL = 'rerun, each process started %s' % evd['T72L1']['state'].replace('started ', '').replace(' (T72A1)', ' of its session')
 475      sI = 'control, %s, idle start' % ADDED</pre></td><td valign="top"><ul><li><code>lrows(k, pos)</code>: one table row per row L-1 to L-4, with its records of kernel <code>k</code> at position <code>pos</code>. <code>orows</code> does the same for rows R0 and R0b.</li><li><code>x2o</code>, <code>x2a</code>: the oldread records and the asmread records of row X2d12.</li><li><code>sL</code>: the description of part L. It takes the start-state text of process T72L1 from <code>evd</code> and writes it for all three processes.</li><li>No <code>need</code> call of this file tests that T72L2 and T72L3 have the same start state. In <code>facts.json</code> the records of all three processes hold a <code>gap_s</code> of 5 s.</li><li><code>sI</code>: the description of control I.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 476      L.extend(ranges([('part L (T72L1 to T72L3)', sL, L72o)] + lrows('oldread', 0)
 477                      + [('pool L-1 to L-4', 'all bwx12 rows of the fixed list', P12o)] + orows('oldread', 0)
 478                      + [('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows', PALLo),
 479                         ('X2d12', DESC['X2d12'], x2o), ('F72d12', DESC['F72d12'], F72o), ('control I (T72I1, T72I2)', sI, I72o)]))</pre></td><td valign="top">The range table of oldread at position 0. Rows, in order: part L (<code>L72o</code>), L-1, L-2, L-3, L-4, the pool L-1 to L-4 (<code>P12o</code>), R0, R0b, the pool with R0 and R0b (<code>PALLo</code>), X2d12, F72d12 (<code>F72o</code>) and control I (<code>I72o</code>). Each row gives n, the lowest to the highest rate, and the median. Row X2d12 is shown only: no range test of this file uses it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 480      l1o, l1a = sel(recs, dataset='L-1', kernel='oldread'), sel(recs, dataset='L-1', kernel='asmread')
 481      sc_o = [('L-1 alone', l1o, False), ('pool L-1 to L-4', P12o, True), ('pool L-1 to L-4, R0, R0b', PALLo, False)]
 482      sc_a = [('L-1 alone', l1a, False), ('pool L-1 to L-4', P12a, True), ('pool L-1 to L-4, R0, R0b', PALLa, False)]
 483      L.extend(cmps('L', 'oldread', [('part L', L72o, sc_o), (('F72d12 ' + OLD_OWN, 'F72d12 ' + OWN), F72o, sc_o),
 484                                      (('control I ' + OLD_OWN, 'control I ' + OWN), I72o, sc_o)]))</pre></td><td valign="top">The range tests of oldread.<ul><li><code>l1o</code>, <code>l1a</code>: the oldread records and the asmread records of row L-1.</li><li><code>sc_o</code>: three 8000 MT/s scopes for oldread: L-1 alone, the pool L-1 to L-4, and the pool with R0 and R0b. Only the pool L-1 to L-4 has <code>decides</code> = True.</li><li><code>sc_a</code>: the same three scopes for asmread. Section 4.4 uses it.</li><li><code>cmps</code> tests three 7200 MT/s rows against the three scopes: part L, F72d12 and control I. That gives 9 tests. Each test is stored in <code>V['q2_rows']</code> with part <code>L</code> and kernel <code>oldread</code>.</li><li>F72d12 and control I are tested as their own rows. Their records are not added to the list of part L.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 485      kLo1 = compare(L72o, l1o)
 486      need(not kLo1['overlap'] and not compare(L72o, PALLo)['overlap'], 'part L oldread below every 8000 MT/s scope')
 487      w('- Part L, wording by rule V1 point 2: "%s". Part L is lower. n at 7200 MT/s: %s. n at 8000 MT/s: %s.'
 488        % (cLo['wording'], nn(cLo['a'], sessions=True), nn(cLo['b'])))</pre></td><td valign="top"><ul><li><code>kLo1</code> is the test of part L against L-1 alone.</li><li>Line 486 stops the build when the range of part L overlaps L-1 alone or the pool with R0 and R0b. It tests the overlap only, not the direction.</li><li>The bullet prints the wording of the test against the pool L-1 to L-4 (<code>cLo['wording']</code>) and both n.</li><li>The words "Part L is lower" are template text. <code>facts_text.py</code> tests this direction against the pool L-1 to L-4 before it calls <code>section4</code> [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 489      near, far, mid = -cLo['dist'], cLo['b']['hi'] - cLo['a']['lo'], cLo['b']['med'] - cLo['a']['med']
 490      c['oldL'] = dict(near=near, mid=mid, near_pct=near / cLo['b']['lo'] * 100, mid_pct=mid / cLo['b']['med'] * 100)
 491      need(c['oldL']['near_pct'] &lt; 1 &lt; c['oldL']['mid_pct'], 'old read, part L: nearest ends below 1 %, medians above 1 %')
 492      w('- Size against the pool L-1 to L-4: the nearest ends are %s GB/s apart (%s %% of the lower end of the '
 493        '8000 MT/s range, %s GB/s). The medians are %s GB/s apart (%s %% of the 8000 MT/s median, %s GB/s). The '
 494        'farthest ends are %s GB/s apart (%s %% of the same lower end). The 8000 MT/s range itself is %s %% wide.'
 495        % (g(near), pc(c['oldL']['near_pct']), g(cLo['b']['lo']), g(mid), pc(c['oldL']['mid_pct']), g(cLo['b']['med']),
 496           g(far), pc(far / cLo['b']['lo'] * 100), pc(cLo['width'])))</pre></td><td valign="top">The size of the difference between part L and the pool L-1 to L-4, from <code>cLo</code>. <code>a</code> is the range of part L and <code>b</code> is the range of the pool.<ul><li><code>near</code> = -<code>dist</code> = b.lo - a.hi: the distance of the nearest ends. Present value: 1.24 GB/s, 0.3 % of b.lo [Ref4].</li><li><code>far</code> = b.hi - a.lo: the distance of the farthest ends. Present value: 8.45 GB/s, 1.8 % of b.lo.</li><li><code>mid</code> = b.med - a.med: the distance of the medians. Present value: 6.27 GB/s, 1.3 % of b.med.</li><li>Percent values: <code>near</code> and <code>far</code> are divided by b.lo, <code>mid</code> by b.med, each times 100. Line 490 stores <code>near</code>, <code>mid</code> and their two percent values in <code>c['oldL']</code> for sections 4.9 and 6.</li><li>Line 491: the build stops unless <code>near</code> is below 1 % and <code>mid</code> is above 1 %. So it passes only when the median of the pool lies above the median of part L.</li><li>The bullet prints GB/s values with 2 decimal places and percent values with 1 decimal place. All are computed before rounding. It also prints the width of the pool range (<code>cLo['width']</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 497      w('- Rule V1 point 4 allows a report as "a difference between the two boots" above about 1 %. The rule does not '
 498        'say which distance counts. The distance of the nearest ends is below 1 %, and the distance of the medians is '
 499        'above 1 %.')
 500      w('- F72d12 and control I are runs of the same line in the same 7200 MT/s boot. Both were launched at a 1-minute '
 501        'load average below 1.0. Section 4.6 gives the differences of their start states. Control I was %s. Both '
 502        'overlap the 8000 MT/s range (%s and %s GB/s against %s GB/s).' % (ADDED, sp(cFo['a']), sp(cIo['a']), sp(cFo['b'])))</pre></td><td valign="top">Two bullets:<ul><li>Template text on rule V1 point 4: the rule does not say which distance counts. Its last sentence says that the distance of the nearest ends is below 1 % and that the distance of the medians is above 1 %. Line 491 tests this.</li><li>F72d12 and control I: their two ranges (<code>cFo['a']</code>, <code>cIo['a']</code>) and the range of the pool (<code>cFo['b']</code>).</li></ul>Three statements of the second bullet are template text here:<ul><li>Both rows are runs of the same line in the same 7200 MT/s boot. For control I the integrity checks <code>args</code> and <code>boot</code> of <code>build_facts.py</code> test it. For F72d12 the integrity check <code>args-R8</code> and lines 219 to 222 test it [Ref3].</li><li>Both ranges overlap the pool. <code>facts_text.py</code> tests it before it calls <code>section4</code> [Ref1].</li><li>Both rows were launched at a 1-minute load average below 1.0. For control I, <code>facts_text.py</code> tests it before it calls <code>section4</code> [Ref1]. For F72d12, no <code>need</code> call of this file tests it. The present load at launch of F72d12 is 0.34 [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 503      hp, ep = c['hw']['possible']
 504      need(not any(e['kind'] != 'outside' and e['interval']['kernel'] == 'oldread' and e['interval'] is not ep['interval']
 505                   for h in D['hw'] for e in h['records']), 'no other oldread interval with a record in or near it')
 506      # the same for the oldread intervals at other positions (row R0 holds oldread at two positions)
 507      need(not any(iv['kernel'] == 'oldread' and iv is not ep['interval']
 508                   for h in D['hw'] for e in h['records'] for _, iv in e['every']),
 509           'no other oldread interval at any position with a record in or near it')
 510      w('- Hardware error records (section 4.1): 2 corrected records fall before or inside oldread, round %d of row %s '
 511        '(%s GB/s). No other oldread interval of the rows L-1 to L-4, R0 and R0b has a record inside it. For the rerun '
 512        'the records are not known.' % (ep['interval']['round'], hp['dataset'], g(ep['interval']['total'])))</pre></td><td valign="top">Checks on the error records in oldread intervals. <code>ep</code> is one of the 2 records that fall before or inside oldread, round 0 of row L-1.<ul><li>Lines 504-505: the build stops when a record of kind <code>inside</code> or <code>possible</code> belongs to another used oldread interval.</li><li>Lines 507-509: the same check for the oldread intervals at every position (field <code>every</code>). Row R0 holds oldread at two positions.</li><li>The bullet prints the round, the row and the rate of the one oldread interval with records. Its count "2 corrected records" is typed in the template. Lines 245 and 293 test it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 513      need(cCo['overlap'], 'part C oldread overlaps the pool')
 514      w('- So against the whole pool L-1 to L-4, only the range of part L lies below the 8000 MT/s range among the '
 515        'bwx12 runs at 7200 MT/s. Part L started %s. The view below splits the pool by start state. In that view part C '
 516        'lies below the bwx12 processes of the pool that started after 120-thread work too. Against the other-binary '
 517        'processes with that kind of start state part C overlaps (limit in the view). The data do not show that the '
 518        'boot or the memory speed is the cause: each memory speed has one boot.'
 519        % evd['T72L1']['state'].replace('started ', '').replace(' (T72A1)', ''))
 520      w('')
 521</pre></td><td valign="top">Line 513: the build stops unless oldread of part C overlaps the pool L-1 to L-4 (<code>cCo</code>). The last bullet of this block is template text with one inserted value, the start-state text of T72L1. Its statements and their tests:<ul><li>Among the bwx12 runs at 7200 MT/s, only the range of part L lies below the pool. Line 513 tests the overlap of part C. <code>facts_text.py</code> tests part L, F72d12 and control I before it calls <code>section4</code> [Ref1].</li><li>In the view by start state, part C also lies below the bwx12 processes of the pool that started after 120-thread work. Line 577 tests it.</li><li>Against the other-binary processes with that kind of start state, part C overlaps. Line 606 tests it.</li><li>Each memory speed has one boot. Line 152 tests it for the 8000 MT/s rows of its list. For the 7200 MT/s records that check is true whatever the run files contain. The explanation of lines 150 to 152 names the tests of the 7200 MT/s boot.</li></ul>The function <code>section4</code>, which starts at line 24, continues after line 521 and ends at line 1615.</td></tr>
<tr><td colspan="2"><b>Section 4.2 view: the 8000 MT/s pool by start state</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 522      # ---- view: the 8000 MT/s pool split by the start state of the process (added after the numbers were seen)
 523      allla = [la for d in BW12 for la in D['rx'][d]['launches'].values()]
 524      st = {}
 525      for d in BW12:
 526          v = D['rx'][d]
 527          for tag in v['secs']:
 528              la = v['launches'][tag]
 529              before = sorted((l for l in allla if l['rc_utc'] is not None and l['rc_utc'] &lt;= la['utc']), key=lambda l: l['rc_utc'])
 530              prev = before[-1] if before else None
 531              st[(d, tag)] = dict(la=la, prev=prev, gap=(la['utc'] - prev['rc_utc']).total_seconds() if prev else None,
 532                                  first=min(v['launches'].values(), key=lambda l: l['utc']) is la, folder=v['folder'])</pre></td><td valign="top">These lines continue the function <code>section4</code> that starts at line 24. The view was added after the numbers were seen.<ul><li><code>allla</code>: every launch line of <code>launches.txt</code> in the run folders of rows L-1 to L-4. It also holds the launch lines of processes of these folders whose csv files the sheet does not use.</li><li>The loop visits each process of these rows. These are the processes whose csv files the sheet uses (<code>v['secs']</code>). <code>la</code> is the launch line of the process.</li><li><code>prev</code>: the process of <code>allla</code> that ended last at or before this launch, by the time of its rc line. It may lie in another run folder. It is <code>None</code> when no process ended before.</li><li><code>gap</code>: the seconds from the rc line of <code>prev</code> to the launch line of this process. Both lines give whole seconds.</li><li><code>first</code>: true when this launch is the earliest launch of its own run folder.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 533      idle = [k for k in st if st[k]['la']['load1'] &lt; 1.0]
 534      busy = [k for k in st if st[k]['la']['load1'] &gt;= 1.0]
 535      need(idle and busy and all(st[k]['first'] for k in idle), 'the processes below load 1.0 are the first of their run folder')
 536      need(all(' --threads 120 ' in ' ' + st[k]['prev']['args'] + ' ' and '--cpus 0-63,64-119' in st[k]['prev']['args']
 537               and 0 &lt; st[k]['gap'] &lt;= 30 for k in busy),
 538           'every other process of the pool started at most 30 s after a 120-thread bwx12 process')</pre></td><td valign="top">The processes are split by the 1-minute load average of their launch line (<code>load1</code>).<ul><li><code>idle</code>: load below 1.0. <code>busy</code>: load 1.0 or above.</li><li>Line 535 stops the build unless each group has a process and every <code>idle</code> process is the first of its run folder.</li><li>Lines 536 to 538 stop the build unless two things hold for every <code>busy</code> process. <code>prev</code> ran with <code>--threads 120</code> and <code>--cpus 0-63,64-119</code>. The process was launched more than 0 s and at most 30 s after <code>prev</code> ended.</li><li>This check reads the arguments of <code>prev</code> only. It does not read the name of a binary. All launch lines of <code>allla</code> come from the run folders of the bwx12 rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 539      grp = lambda keys, k, pos: [r for r in sel(recs, dataset=set(BW12), kernel=k, pos=pos) if (r['dataset'], r['tag']) in keys]
 540      Io, Ia, Bo, Ba = grp(idle, 'oldread', 0), grp(idle, 'asmread', 1), grp(busy, 'oldread', 0), grp(busy, 'asmread', 1)
 541      need(len(Io) + len(Bo) == len(P12o) and len(Ia) + len(Ba) == len(P12a), 'the two groups hold the whole pool')</pre></td><td valign="top"><code>grp</code> returns the records of rows L-1 to L-4 for one kernel and position whose process is in the given group. A process is matched by its row name and its tag.<ul><li><code>Io</code>, <code>Bo</code>: oldread at position 0 of the groups <code>idle</code> and <code>busy</code>.</li><li><code>Ia</code>, <code>Ba</code>: asmread at position 1 of the two groups.</li><li>Line 541 stops the build unless the two groups together have as many intervals as the pool lists <code>P12o</code> and <code>P12a</code>. So the split leaves out no interval of the pool.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 542      gaps_ = sorted(st[k]['gap'] for k in busy)
 543      loads = lambda keys: sorted(st[k]['la']['load1'] for k in keys)
 544      names = lambda keys: ', '.join('%s %s' % k for k in keys)
 545      lsrc = lambda keys: ' '.join(dict.fromkeys(ref(os.path.join(st[k]['folder'], 'launches.txt')) for k in keys))</pre></td><td valign="top">Helpers for the table and the text below.<ul><li><code>gaps_</code>: the <code>gap</code> values of the <code>busy</code> processes in seconds, sorted.</li><li><code>loads</code>: the sorted loads at launch of a group.</li><li><code>names</code>: the processes of a group as text, each as row name and tag.</li><li><code>lsrc</code>: the <code>[RefN]</code> labels of the <code>launches.txt</code> files of a group, each file once.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 546      w('The pool L-1 to L-4 split by the start state of the process. This view was looked at after the numbers were '
 547        'seen. It is not part of the fixed rules.')
 548      w('')
 549      L.extend(table(['8000 MT/s group', 'Processes', 'Load at launch', 'Work before the launch', 'n', 'oldread, GB/s',
 550                      'asmread, GB/s', 'Source'], [
 551          ['started at a load below 1.0', names(idle), ' and '.join(dict.fromkeys('%.2f' % x for x in loads(idle))),
 552           'first process of its run folder', nn(rng(Io)), sp(rng(Io)), sp(rng(Ia)), 'rates %s, launch lines %s' % (src(Io), lsrc(idle))],
 553          ['started after 120-thread work', names(busy), '%.2f to %.2f' % (loads(busy)[0], loads(busy)[-1]),
 554           'a 120-thread bwx12 process had ended %.0f s to %.0f s before' % (gaps_[0], gaps_[-1]), nn(rng(Bo)), sp(rng(Bo)),
 555           sp(rng(Ba)), 'rates %s, launch lines %s' % (src(Bo), lsrc(busy))]]))</pre></td><td valign="top">Writes the opening sentences of the view and its table. The sentences say that the view is not part of the fixed rules. The table has one row per group.<ul><li>Its columns are the group, the processes, the load at launch, the work before the launch, n, the lowest to highest oldread rate, the lowest to highest asmread rate, and the source files.</li><li>Here n is taken from the oldread list of the group. No line tests that the asmread list of the group has the same n. In the present data it has the same n in both groups.</li><li>The row of the <code>busy</code> group prints the lowest and the highest load, and the shortest and the longest <code>gap</code>.</li><li>Loads are printed with 2 decimal places, gaps as whole seconds.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 556      aIo, aBo, aIa, aBa = rng(Io), rng(Bo), rng(Ia), rng(Ba)
 557      need(aBo['lo'] &gt; aIo['hi'], '8000 MT/s: oldread after 120-thread work above oldread from a load below 1.0')
 558      need(overlap(aIa, aBa), '8000 MT/s: the two asmread groups overlap')
 559      kLB, kLaB = compare(L72o, Bo), compare(L72a, Ba)
 560      need(not kLB['overlap'] and kLB['dist'] &lt; 0 and not kLaB['overlap'] and kLaB['dist'] &gt; 0,
 561           'part L: oldread below and asmread above the 8000 MT/s group that started after 120-thread work')
 562      need(overlap(rng(F72o), aIo) and overlap(rng(I72o), aIo), 'F72d12 and control I overlap the 8000 MT/s group below load 1.0')</pre></td><td valign="top"><code>aIo</code>, <code>aBo</code>, <code>aIa</code> and <code>aBa</code> are the ranges of the four lists (lowest rate, highest rate, median, counts). Each <code>need</code> stops the build when its condition is false.<ul><li>Line 557: the lowest oldread rate of the <code>busy</code> group is above the highest oldread rate of the <code>idle</code> group.</li><li>Line 558: the asmread ranges of the two groups overlap.</li><li>Line 559: <code>kLB</code> compares oldread of part L (<code>L72o</code>) with <code>Bo</code>. <code>kLaB</code> compares asmread of part L (<code>L72a</code>) with <code>Ba</code>.</li><li>Lines 560 and 561: part L lies below <code>Bo</code> for oldread and above <code>Ba</code> for asmread, both without overlap.</li><li>Line 562: the oldread range of F72d12 overlaps the range of the <code>idle</code> group. The oldread range of control I overlaps it too.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 563      c['byst'] = dict(Io=aIo, Bo=aBo, Ia=aIa, Ba=aBa, idle=idle, busy=busy, gaps=gaps_, loads_busy=loads(busy),
 564                       near=-kLB['dist'], near_pct=-kLB['dist'] / aBo['lo'] * 100, asm_near=kLaB['dist'], names=names)</pre></td><td valign="top"><code>c['byst']</code> keeps the view for later sections of the sheet. The values are stored without rounding.<ul><li><code>near</code>: the lowest oldread rate of <code>Bo</code> minus the highest oldread rate of part L, in GB/s. It is <code>kLB['dist']</code> with the opposite sign.</li><li><code>near_pct</code>: <code>near</code> divided by the lowest oldread rate of <code>Bo</code>, times 100. Unit: percent.</li><li><code>asm_near</code>: the lowest asmread rate of part L minus the highest asmread rate of <code>Ba</code>, in GB/s.</li><li>In the present FACTS.md <code>near</code> is 4.27 GB/s. That is 0.9 % of 468.56 GB/s [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Part C in the start-state view</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 565      # part C in this view: its processes started after a 120-thread bwx12 process, like the second 8000 MT/s group
 566      Ctags = list(dict.fromkeys(r['tag'] for r in C72o))
 567      Cprev = [evd[t]['prev'] for t in Ctags]
 568      need(all(p_ is not None and p_['part'] in ('L', 'C') for p_ in Cprev)
 569           and all(0 &lt; evd[t]['gap_s'] &lt;= 30 for t in Ctags) and len({evd[t]['gap_s'] for t in Ctags}) == 1,
 570           'every part C process started at most 30 s after a 120-thread bwx12 process of the rerun, all after the same gap')</pre></td><td valign="top"><code>Ctags</code> holds the tags of the part C processes, taken from the oldread records <code>C72o</code>. <code>Cprev</code> holds, for each of them, the step that ran directly before it (<code>evd[t]['prev']</code>). The steps are the part A folders and the bwx12 processes of go.sh and go2.sh, in time order. The build stops unless all of these hold:<ul><li>Every step before is a bwx12 process of part L or of part C.</li><li>Every part C process was launched more than 0 s and at most 30 s after that step ended. The field <code>gap_s</code> holds this time.</li><li>All part C processes have the same <code>gap_s</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 571      Cf0 = sel(C72o, pos=0)
 572      Cf0tags = list(dict.fromkeys(r['tag'] for r in Cf0))
 573      need({r['kernel_before'] for r in sel(C72o, pos=2)} == {'read'} and len(Cf0) + len(sel(C72o, pos=2)) == len(C72o)
 574           and {next(x['spec'] for x in D['X'] if x['tag'] == t) for t in Cf0tags} == {'cfwd'},
 575           'oldread of part C: position 0 in cfwd, position 2 directly after read in crev')</pre></td><td valign="top"><code>Cf0</code> holds the oldread intervals of part C at position 0. <code>Cf0tags</code> holds the tags of their processes. The build stops unless all of these hold:<ul><li>Every oldread interval of part C at position 2 ran directly after kernel <code>read</code>.</li><li>Positions 0 and 2 together hold every oldread interval of part C.</li><li>Every process with oldread at position 0 has the spec name <code>cfwd</code> in <code>D['X']</code>. This name comes from a fixed list in <code>facts_data.py</code>, not from the launch line [Ref2]. <code>build_facts.py</code> compares the launch line of each process with its spec file in its check <code>args</code> [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 576      kCB, kCfB, kCIo = compare(C72o, Bo), compare(Cf0, Bo), compare(C72o, Io)
 577      need(not kCB['overlap'] and kCB['dist'] &lt; 0 and not kCfB['overlap'] and kCfB['dist'] &lt; 0 and kCIo['overlap'],
 578           'part C oldread: below the 8000 MT/s group that started after 120-thread work, overlap with the other group')
 579      Cload = sorted(evd[t]['load1'] for t in Ctags)
 580      c['partC_view'] = dict(all=kCB['a'], cf0=kCfB['a'], near=-kCB['dist'], near_pct=-kCB['dist'] / aBo['lo'] * 100,
 581                             near_cf0=-kCfB['dist'], gap=evd[Ctags[0]]['gap_s'], prev=[p_['tag'] for p_ in Cprev],
 582                             loads=Cload, both=rng(L72o + C72o))</pre></td><td valign="top">Three comparisons of oldread: all of part C against <code>Bo</code> (<code>kCB</code>), position 0 of part C against <code>Bo</code> (<code>kCfB</code>), and all of part C against <code>Io</code> (<code>kCIo</code>). The build stops unless part C lies below <code>Bo</code> without overlap in the first two, and overlaps <code>Io</code> in the third. <code>c['partC_view']</code> stores the result:<ul><li><code>all</code>, <code>cf0</code>: the ranges of all oldread intervals of part C and of its oldread intervals at position 0.</li><li><code>near</code>, <code>near_cf0</code>: the lowest rate of <code>Bo</code> minus the highest rate of part C, in GB/s. <code>near</code> uses all oldread intervals, <code>near_cf0</code> only position 0.</li><li><code>near_pct</code>: <code>near</code> divided by the lowest rate of <code>Bo</code>, times 100.</li><li><code>gap</code>, <code>prev</code>, <code>loads</code>: the <code>gap_s</code> of the first part C process, the tags of the steps before, and the sorted loads at launch (<code>Cload</code>).</li><li><code>both</code>: the range of oldread over part L and part C together. The text below prints only its counts.</li><li>In the present FACTS.md <code>near</code> is 0.42 GB/s and <code>near_cf0</code> is 0.73 GB/s [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>The same start state in the other-binary rows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 583      # the same kind of start state outside the pool: rows of bwx11 and of runner bwx (other binaries)
 584      alla11 = [la for d in BW11 for la in D['rx'][d]['launches'].values()]
 585      busy11 = []
 586      for d in BW11:
 587          v = D['rx'][d]
 588          for tag in v['secs']:
 589              la = v['launches'][tag]
 590              before = sorted((l for l in alla11 if l['rc_utc'] is not None and l['rc_utc'] &lt;= la['utc']), key=lambda l: l['rc_utc'])
 591              prev = before[-1] if before else None
 592              if (prev and ' --threads 120 ' in ' ' + prev['args'] + ' ' and '--cpus 0-63,64-119' in prev['args']
 593                      and 0 &lt; (la['utc'] - prev['rc_utc']).total_seconds() &lt;= 30):
 594                  busy11.append(dict(key=(d, tag), gap=(la['utc'] - prev['rc_utc']).total_seconds(), load=la['load1'],
 595                                     folder=v['folder']))
 596      B11o = [r for r in sel(recs, dataset=set(BW11), kernel='oldread', pos=0)
 597              if (r['dataset'], r['tag']) in {b['key'] for b in busy11}]</pre></td><td valign="top">The same kind of start state in rows R0 and R0b (binary bwx11). The loop repeats the search of lines 525 to 532 with the launch lines of the run folders of these two rows.<ul><li>A process enters <code>busy11</code> when two things hold. The process before it ran with <code>--threads 120</code> and <code>--cpus 0-63,64-119</code>. That process ended more than 0 s and at most 30 s before the launch.</li><li>No load value is tested here. Line 534 tests one for the pool.</li><li><code>B11o</code>: the oldread intervals at position 0 of the <code>busy11</code> processes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 598      bx0v = sel(recs, dataset=set(BWX), kernel='oldread', pos=0)
 599      prev120 = [s_['prev_step'] for n in BWX for s_ in D['step'][n]['secs']]
 600      need(busy11 and len(prev120) == rng(bx0v)['procs']
 601           and all(p_ is not None and ' --threads 120 ' in ' ' + p_['args'] + ' ' and p_['binary'] == 'bwx' for p_ in prev120),
 602           'every used process of runner bwx follows a 120-thread step of runner bwx in its csv file')</pre></td><td valign="top"><code>bx0v</code> holds oldread at position 0 of the runner bwx rows B7a, B7b, C3a and C3b. <code>prev120</code> holds one entry per used process of these rows: the <code>-- step</code> line (the header line) of the process directly before it in the same csv file. The check in lines 600 to 602 tests no time gap, no load and no <code>--cpus</code> list. The build stops unless all of these hold:<ul><li><code>busy11</code> is not empty.</li><li><code>prev120</code> has as many entries as <code>bx0v</code> has processes, and no entry is missing.</li><li>Every entry names the binary <code>bwx</code> and holds <code>--threads 120</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 603      aB11, aBx0 = rng(B11o), rng(bx0v)
 604      allo = sel(recs, speed_MTps=8000, modules=12, kernel='oldread')
 605      low_o = min(allo, key=lambda r: r['GBps'])
 606      need(overlap(rng(C72o), aB11) and overlap(rng(C72o), aBx0), 'part C oldread overlaps the other-binary rows of that start state')
 607      need(rng(L72o)['hi'] &lt; low_o['GBps'] and {r['binary'] for r in allo} == {'bwx12', 'bwx11', 'bwx'},
 608           'part L oldread below every oldread interval at 8000 MT/s with 12 modules')
 609      c['byst_other'] = dict(b11=aB11, bx0=aBx0, busy11=busy11, low_o=low_o, n_allo=len(allo),
 610                             bx0_load=[min(r['load1_at_launch'] for r in bx0v), max(r['load1_at_launch'] for r in bx0v)])
 611      c['byst']['L_hi'] = rng(L72o)['hi']</pre></td><td valign="top"><ul><li><code>aB11</code>, <code>aBx0</code>: the ranges of <code>B11o</code> and <code>bx0v</code>.</li><li><code>allo</code>: every oldread record at 8000 MT/s with 12 modules, of every row and every position. <code>low_o</code> is the record with the lowest rate.</li><li>Line 606 stops the build unless the oldread range of part C overlaps <code>aB11</code> and overlaps <code>aBx0</code>.</li><li>Lines 607 and 608 stop the build unless two things hold. The highest oldread rate of part L is below the rate of <code>low_o</code>. The binaries of <code>allo</code> are exactly bwx12, bwx11 and bwx.</li><li><code>c['byst_other']</code> and <code>c['byst']['L_hi']</code> keep these values for later sections. <code>bx0_load</code> is the lowest and the highest load at launch of <code>bx0v</code>.</li><li>In the present FACTS.md <code>allo</code> has 124 intervals [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 612      w('- oldread at 8000 MT/s: the %d processes of the pool that started after 120-thread work gave the %d highest '
 613        'values of the pool (%s GB/s). The %d processes that started at a load below 1.0 gave %s GB/s. The two groups do '
 614        'not overlap.' % (aBo['procs'], aBo['n'], sp(aBo), aIo['procs'], sp(aIo)))
 615      w('- Part L started %.0f s after part A. Against the group that started after 120-thread work, oldread of part L '
 616        '(%s GB/s) is lower by %s GB/s at the nearest ends (%s %% of %s GB/s). Against the whole pool this distance is '
 617        '%s GB/s.' % (evd['T72L1']['gap_s'], sp(cLo['a']), g(c['byst']['near']), pc(c['byst']['near_pct']), g(aBo['lo']), g(near)))
 618      pcv = c['partC_view']
 619      w('- Part C in this view. All %d part C processes started %.0f s after a 120-thread bwx12 process of the rerun '
 620        '(%s), at a load of %.2f to %.2f (sections 1.1 and 1.3). That is the kind of start state of the second '
 621        '8000 MT/s group (a 120-thread bwx12 process ended %.0f s to %.0f s before, load %.2f to %.2f). '
 622        'oldread of part C (%s GB/s, %s) lies below this group (%s GB/s, %s). The two ranges do not overlap. Part C is '
 623        'lower by %s GB/s at the nearest ends (%s %% of %s GB/s). Like the two wordings for part C, this comparison '
 624        'follows decision (r) in section 2.'
 625        % (len(Ctags), pcv['gap'], ', '.join(pcv['prev']), Cload[0], Cload[-1], gaps_[0], gaps_[-1], loads(busy)[0],
 626           loads(busy)[-1], sp(pcv['all']), nn(pcv['all']), sp(aBo),
 627           nn(aBo), g(pcv['near']), _q(pcv['near_pct'], '0.01'), g(aBo['lo'])))
 628      w('- The second group holds oldread at position 0 only. The position-matched intervals of part C are those of '
 629        'cfwd at position 0 (%s, load %s at launch): %s GB/s (%s). They are lower by %s GB/s at the nearest ends.'
 630        % (' and '.join(Cf0tags), ' and '.join('%.2f' % evd[t]['load1'] for t in Cf0tags), sp(pcv['cf0']),
 631           nn(pcv['cf0'], boots=False), g(pcv['near_cf0'])))
 632      w('- Against the group that started at a load below 1.0 (%s GB/s), oldread of part C overlaps.' % sp(aIo))
 633      w('- So in this view both 7200 MT/s parts that started after 120-thread work lie below the %d bwx12 processes of '
 634        'the pool L-1 to L-4 that started after 120-thread work (%s against %s, no overlap). For part C this holds '
 635        'against these %d processes only (see the limit below). The wording by rule V1 point 2 for part C '
 636        'does not change. It compares part C with the whole pool.'
 637        % (aBo['procs'], nn(pcv['both'], boots=False), nn(aBo, boots=False), aBo['procs']))
 638      w('- The rows that were launched at a load below 1.0 overlap. At 7200 MT/s F72d12 gave %s GB/s and control I (%s) '
 639        'gave %s GB/s. At 8000 MT/s the group gave %s GB/s.' % (sp(cFo['a']), ADDED, sp(cIo['a']), sp(aIo)))
 640      w('- asmread: part L (%s GB/s) lies %s GB/s above the group that started after 120-thread work (%s GB/s). The two '
 641        '8000 MT/s groups overlap for asmread.' % (sp(cLa['a']), g(kLaB['dist']), sp(aBa)))
 642      w('- So the 8000 MT/s rows do not show a lower oldread rate after 120-thread work. They show a higher one.')</pre></td><td valign="top">Writes nine list items of the view. Every number comes from the values above.<ul><li>Items 1 and 2 (lines 612 to 617): the two oldread groups at 8000 MT/s, and part L against the <code>busy</code> group. Item 2 says how many seconds after part A part L started. This number is the <code>gap_s</code> of process T72L1 only. The last number is <code>near</code> of line 489, the distance against the whole pool.</li><li>Items 3 to 6 (lines 619 to 637): part C against the two groups, from <code>c['partC_view']</code> and the ranges of the groups. Here <code>near_pct</code> is printed with 2 decimal places.</li><li>Item 7 (lines 638 and 639): the oldread ranges of F72d12, of control I and of the <code>idle</code> group.</li><li>Item 7 calls F72d12 and control I rows that were launched at a load below 1.0. Line 898 tests this load for control I. No <code>need</code> call of this file tests it for F72d12. The present load at launch of F72d12 is 0.34 [Ref4].</li><li>Item 8 (lines 640 and 641): asmread of part L against <code>Ba</code>.</li><li>Item 9 (line 642): the 8000 MT/s rows show a higher oldread rate after 120-thread work, not a lower one. The check in line 557 stops the build when the data do not show this.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 643      l11 = sorted(b['load'] for b in busy11)
 644      g11 = sorted({b['gap'] for b in busy11})
 645      lbx = sorted(r['load1_at_launch'] for r in bx0v)
 646      w('- Limit of the part C result in this view. The second group holds the %d bwx12 processes of the pool only. They '
 647        'are not all 8000 MT/s processes with that kind of start state. The other-binary rows hold more of them, and '
 648        'against these part C overlaps. %d bwx11 processes (%s) were launched %s s after a 120-thread bwx11 process, at '
 649        'a load of %.2f to %.2f. They gave oldread %s GB/s at position 0 (%s) %s, launch lines %s. The %d processes of '
 650        'runner bwx (rows %s) each follow a 120-thread process of runner bwx in their csv file. Their load at launch '
 651        'was %.2f to %.2f. They gave %s GB/s at position 0 (%s) %s. The highest oldread value of part C is %s GB/s.'
 652        % (aBo['procs'], len(busy11), ', '.join('%s %s' % b['key'] for b in busy11), ' or '.join('%.0f' % x for x in g11),
 653           l11[0], l11[-1], sp(aB11), nn(aB11, boots=False), src(B11o),
 654           ' '.join(dict.fromkeys(ref(os.path.join(b['folder'], 'launches.txt')) for b in busy11)), aBx0['procs'],
 655           ', '.join(BWX), lbx[0], lbx[-1], sp(aBx0), nn(aBx0, boots=False), src(bx0v), g(rng(C72o)['hi'])))
 656      w('- The part L result does not depend on this choice. The highest oldread value of part L (%s GB/s) is below '
 657        'every oldread interval at 8000 MT/s with 12 modules that this sheet holds (%d intervals of the binaries bwx12, '
 658        'bwx11 and bwx). The lowest of them is %s GB/s (row %s, process %s).'
 659        % (g(rng(L72o)['hi']), len(allo), g(low_o['GBps']), low_o['dataset'], low_o['tag']))
 660      w('- Limits of this view. For part L the work before the launch differs between the two speeds: part A (bw_old '
 661        'and bw_new) at 7200 MT/s, a bwx12 process at 8000 MT/s. For part C it is a bwx12 process at both speeds. The '
 662        'second group has intervals of %s and other counter events (rows L-2 to L-4). %d of the %d oldread intervals of '
 663        'part C are at position 2, directly after read. Each memory speed has one boot.'
 664        % (secs(Bo), len(sel(C72o, pos=2)), len(C72o)))
 665      w('- Insufficient data: why old read was lower in part L. ' + H1_MEAS)
 666      w('')
 667</pre></td><td valign="top">Writes the limits of the view.<ul><li><code>l11</code>, <code>g11</code>: the sorted loads at launch and the distinct <code>gap</code> values of the <code>busy11</code> processes. <code>lbx</code>: the sorted loads at launch of <code>bx0v</code>.</li><li>Lines 646 to 655: the <code>busy</code> group holds bwx12 processes only. Against the bwx11 processes and the bwx processes with that kind of start state part C overlaps. The item prints both ranges and the highest oldread rate of part C.</li><li>Lines 656 to 659: the highest oldread rate of part L is below every interval of <code>allo</code>. The item prints the number of intervals of <code>allo</code>, and the rate, row and tag of <code>low_o</code>.</li><li>Lines 660 to 664: four limits. They are the work before the launch, the interval lengths and counter events of <code>Bo</code>, the position of oldread in part C, and one boot per memory speed. The item prints the interval lengths of <code>Bo</code>, and how many oldread intervals of part C are at position 2.</li><li>Line 665: the measurement that would show why the old read kernel was lower in part L (<code>H1_MEAS</code>).</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.2: old read kernel in part C</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 668      w('**Part C, oldread.**')
 669      w('')
 670      Cf = sel(C, kernel='oldread', pos=0)
 671      Cr = sel(C, kernel='oldread', pos=2)
 672      bx0 = sel(recs, dataset=set(BWX), kernel='oldread', pos=0)
 673      bx7 = sel(recs, dataset=set(BWX), kernel='oldread', pos=7)
 674      scm = lambda rs: [r for r in rs if r['start'] == 'common']       # the processes of runner bwx with --start common
 675      need({r['start'] for r in C} == {'common'}, 'part C used --start common')
 676      nsc = rng(scm(bx0))['procs']</pre></td><td valign="top">Record lists for the two tables below.<ul><li><code>Cf</code>, <code>Cr</code>: oldread of part C at position 0 and at position 2.</li><li><code>bx0</code>, <code>bx7</code>: oldread of the runner bwx rows B7a, B7b, C3a and C3b at position 0 and at position 7.</li><li><code>scm</code> keeps the records of the processes that ran with <code>--start common</code>.</li><li>Line 675 stops the build unless every record of part C ran with <code>--start common</code>.</li><li><code>nsc</code>: the number of processes with <code>--start common</code> among <code>bx0</code>. The labels of lines 686, 952, 960 and 998 and the text of line 1028 print this number for other lists of runner bwx too: <code>bx7</code>, <code>bx1</code> (line 950), <code>bx6</code> (line 958) and <code>bx2</code> (line 975). No line tests it for these lists. In the present FACTS.md each of them has 12 such processes [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 677      L.extend(ranges([('part C, all oldread intervals', 'rerun, cfwd and crev', C72o),
 678                       ('part C, cfwd, position 0', 'first interval of each round', Cf),
 679                       ('part C, crev, position 2', 'directly after read', Cr),
 680                       ('L-1 alone', L1C + '. oldread at position 0', l1o),
 681                       ('pool L-1 to L-4', 'bwx12 rows, oldread at position 0', P12o),
 682                       ('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows, oldread at position 0', PALLo),
 683                       ('pool B7a, B7b, C3a, C3b, position 0', 'other binary (bwx), oldread at position 0', bx0),
 684                       ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), oldread at position 0', scm(bx0)),
 685                       ('pool B7a, B7b, C3a, C3b, position 7', 'other binary (bwx), oldread directly after read', bx7),
 686                       ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), oldread directly after read', scm(bx7))]))</pre></td><td valign="top">Writes the range table of oldread. Each row gives n, the lowest to highest rate and the median of one record list.<ul><li>Part C: all oldread intervals, position 0 only, and position 2 only.</li><li>The label of position 2 names the spec <code>crev</code>. Line 574 tests the spec name for position 0 only. In the present data the processes with oldread at position 2 are T72C2 and T72C4, the two crev processes.</li><li>8000 MT/s rows of the fixed list: L-1 alone, the pool L-1 to L-4, and the pool with rows R0 and R0b.</li><li>The row of L-1 alone says <code>oldread at position 0</code>. The code selects <code>l1o</code> by row and kernel, without a position (line 480). This file does not test the position of these records. In the present facts.json both records of <code>l1o</code> are at position 0.</li><li>Runner bwx at 8000 MT/s: position 0 and position 7. Each of these two lists is shown twice: with all processes, and with the <code>--start common</code> processes only.</li><li>The labels call position 7 of runner bwx <code>oldread directly after read</code>. The code selects <code>bx7</code> by position. This file does not test the kernel before of these rows. In the present facts.json <code>kernel_before</code> is <code>read</code> for every record of <code>bx7</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 687      kC1, kCall = compare(C72o, l1o), compare(C72o, PALLo)
 688      L.extend(cmps('C', 'oldread', [
 689          ('part C, all oldread intervals', C72o, [('L-1 alone (position 0)', l1o, False),
 690                                                   ('pool L-1 to L-4 (position 0)', P12o, True),
 691                                                   ('pool L-1 to L-4, R0, R0b (position 0)', PALLo, False)]),
 692          ('part C, cfwd, position 0', Cf, [('pool L-1 to L-4 (position 0)', P12o, False),
 693                                            ('other binary bwx, position 0', bx0, False)]),
 694          ('part C, crev, position 2', Cr, [('other binary bwx, position 7 (after read)', bx7, False)])], F2_NOTE))</pre></td><td valign="top"><code>cmps</code> runs six range tests and returns their table. It also stores each test in <code>V['q2_rows']</code>.<ul><li>All oldread intervals of part C against L-1 alone, against the pool L-1 to L-4, and against the pool with R0 and R0b. Only the test of all oldread intervals against the pool L-1 to L-4 has <code>decides</code> = True. So only this one of the six tests gets a wording.</li><li>Position 0 of part C against the pool L-1 to L-4 and against runner bwx at position 0.</li><li>Position 2 of part C against runner bwx at position 7.</li><li><code>kC1</code> and <code>kCall</code> (line 687) repeat two of the tests for the check in line 699.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 695      w('- Wording by rule V1 point 2: "%s". n at 7200 MT/s: %s. n at 8000 MT/s: %s. %s'
 696        % (cCo['wording'], nns(C72o), nn(cCo['b']), F2_NOTE))
 697      w('- The test cannot exclude a difference of about %s %% (est. from one boot). That is the width of the 8000 MT/s '
 698        'range (%s GB/s).' % (pc(cCo['width']), sp(cCo['b'])))
 699      need(kC1['overlap'] and kCall['overlap'], 'part C oldread overlaps L-1 alone and the pool with the other-binary rows')
 700      w('- The ranges also overlap against L-1 alone and against the pool with the other-binary rows.')</pre></td><td valign="top">Writes the result of the deciding test. <code>cCo</code> is the comparison of all oldread intervals of part C with the pool L-1 to L-4. <code>facts_text.py</code> made it [Ref1].<ul><li>The text prints its wording, both n, and the width of the 8000 MT/s range: (highest - lowest) / lowest x 100, with 1 decimal place.</li><li>Line 699 stops the build unless part C also overlaps L-1 alone and the pool with R0 and R0b.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 701      lowC = [r for r in C72o if r['GBps'] &lt; cCo['b']['lo']]
 702      w('- %d of the %d intervals of part C lie below the lowest value of the pool%s.'
 703        % (len(lowC), len(C72o), (' (%s)' % ', '.join(dict.fromkeys(r['tag'] for r in lowC))) if lowC else ''))
 704      w('- In the view by start state above (added after the numbers were seen), all %d intervals of part C lie below '
 705        'the %d bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (%s GB/s), by %s GB/s at the '
 706        'nearest ends. Against the other-binary processes with that kind of start state part C overlaps (limit in '
 707        'that view).'
 708        % (len(C72o), aBo['procs'], sp(aBo), g(pcv['near'])))
 709      w('- Only oldread at position 0 (cfwd) has a position-matched bwx12 baseline (rule V4). The rows of runner bwx '
 710        'are another binary. They are shown for the position after read.')
 711      w('')</pre></td><td valign="top"><code>lowC</code> holds the oldread intervals of part C whose rate is below the lowest rate of the pool L-1 to L-4. The text prints their number, the number of all oldread intervals of part C, and the tags of their processes. The next item repeats the result of the start-state view: the range of <code>Bo</code> and <code>near</code> of <code>c['partC_view']</code>. The last item has fixed words.</td></tr>
<tr><td colspan="2"><b>Section 4.3: new read kernel in part A (rule V3)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 712
 713      # ---- 4.3 new read, part A
 714      w('### 4.3 New read kernel in part A (rule V3)')
 715      w('')
 716      w('- Session 1 is compared with the 8000 MT/s processes of the same round in rows A-1 and A-2. bw_old asmread '
 717        'has a process in row A-1 only.')
 718      w('- A cell shows the three intervals in GB/s and, in brackets, their pass counts.')
 719      w('- No percent is given here (rules V3 and V1 point 3).')
 720      w('')
 721      rows = []
 722      cellt = lambda rs: ', '.join('%s (%d)' % (g(r['GBps']), r['passes']) for r in rs) if rs else 'no process in this row'</pre></td><td valign="top">Writes the title and three opening items. This section works on <code>pa3</code>, the six cells that <code>facts_text.py</code> prepared [Ref1].<ul><li>A cell is one binary with one load-only kernel in one round.</li><li>From the rerun a cell holds session 1 only. Sessions 2 and 3 of part A are left out of this section.</li><li><code>cellt</code> prints the intervals of one table cell: each rate with 2 decimal places and its pass count in brackets.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 723      for x in pa3:
 724          if x['inside'] == 3:
 725              word, dist = 'inside the range of the 8000 MT/s runs; no difference shown', '-'
 726          elif len(x['above']) == 3:
 727              word, dist = 'outside (above)', '%s to %s' % (g(min(x['above'])), g(max(x['above'])))
 728          elif len(x['below']) == 3:
 729              word, dist = 'outside (below)', '%s to %s' % (g(min(x['below'])), g(max(x['below'])))
 730          else:
 731              word = '%d of 3 intervals inside, %d above, %d below' % (x['inside'], len(x['above']), len(x['below']))
 732              dist = ', '.join(g(v) for v in x['above'] + x['below'])
 733          x['word'], x['dist_txt'] = word, dist</pre></td><td valign="top">The wording of rule V3 for one cell <code>x</code>. The 8000 MT/s range of the cell (<code>b80</code>) spans the intervals of rows A-1 and A-2 of the same binary, kernel and round. <code>facts_text.py</code> has counted how many of the 3 intervals of session 1 lie above its highest rate, below its lowest rate, or inside it [Ref1].<ul><li>All 3 inside: <code>inside the range of the 8000 MT/s runs; no difference shown</code>, and no distance.</li><li>All 3 above: <code>outside (above)</code>. The distance text gives the smallest and the largest of the 3 distances to the highest rate of <code>b80</code>, in GB/s.</li><li>All 3 below: <code>outside (below)</code>, with the distances to the lowest rate of <code>b80</code>.</li><li>Any other case: the three counts and every distance.</li><li>No percent and no median are computed here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 734          rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'], cellt(x['s1']), cellt(x['a1']), cellt(x['a2']),
 735                       sp(x['b80']), word, dist])
 736          V['q2_rows'].append(dict(part='A', kernel='%s %s' % (x['binary'], x['kernel']), row_7200='session 1, round %d' % x['round'],
 737                                   lo_7200=min(r['GBps'] for r in x['s1']), hi_7200=max(r['GBps'] for r in x['s1']), n_7200=3,
 738                                   processes_7200=1,
 739                                   scope_8000='%s, round %d' % (' and '.join(n for n, a in (('A-1', x['a1']), ('A-2', x['a2'])) if a),
 740                                                                x['round']), lo_8000=x['b80']['lo'],
 741                                   hi_8000=x['b80']['hi'], n_8000=x['b80']['n'], processes_8000=x['b80']['procs'],
 742                                   overlap=x['inside'] &gt; 0, distance_GBps=round(min(x['above'] or [0]), 3), wording=word,
 743                                   decides=True, note='rule V3: inside or outside the 8000 MT/s range of the same round'))
 744          V['q2_rows'][-1].update(row_7200_label=V['q2_rows'][-1]['row_7200'], scope_8000_label=V['q2_rows'][-1]['scope_8000'])</pre></td><td valign="top">Adds the table row of the cell, and its entry in <code>V['q2_rows']</code> for facts.json. The entry holds the wording of lines 724 to 732 and <code>decides</code> = True.<ul><li><code>lo_7200</code>, <code>hi_7200</code>: the lowest and the highest rate of the 3 intervals of session 1. <code>n_7200</code> = 3 and <code>processes_7200</code> = 1 are fixed numbers in the code.</li><li><code>scope_8000</code>: the rows that have a process for this cell (A-1, A-2 or both) and the round.</li><li><code>lo_8000</code>, <code>hi_8000</code>, <code>n_8000</code>, <code>processes_8000</code>: taken from <code>b80</code>.</li><li><code>overlap</code>: true when at least one of the 3 intervals lies inside <code>b80</code>. This is not the range test of <code>compare</code>.</li><li><code>distance_GBps</code>: the smallest distance above <code>b80</code>, rounded to 3 decimal places. It is 0 when no interval lies above, also for a cell that lies below.</li><li>Line 744 copies the two keys <code>row_7200</code> and <code>scope_8000</code> into the label fields.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 745      L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1', '8000 MT/s, A-1, same round',
 746                      '8000 MT/s, A-2, same round', '8000 MT/s range of the round, GB/s', 'Wording by rule V3',
 747                      'Distance to the nearer end of the range, GB/s'], rows))
 748      need(all(len(x['above']) == 3 for x in pa3), 'session 1 of every load-only cell above the 8000 MT/s range of its round')
 749      w('- All %d load-only cells of session 1 lie above the 8000 MT/s range of their round.' % len(pa3))</pre></td><td valign="top">Writes the table of the six cells. Line 748 stops the build unless all 3 intervals of session 1 lie above the 8000 MT/s range in every cell. So in a build that finishes, every cell has the wording <code>outside (above)</code>. Its <code>distance_GBps</code> is the lowest rate of session 1 minus the highest rate of <code>b80</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 750      s1new = sel(recs, dataset='rerun-A', session=1, binary='bw_new', kernel='read')
 751      a1n, a2n = sel(recs, dataset='A-1', binary='bw_new', kernel='read'), sel(recs, dataset='A-2', binary='bw_new', kernel='read')
 752      need(nn(rng(a1n)) == nn(rng(a2n)) and {r['round'] for r in a1n} == {r['round'] for r in a2n} ==
 753           {r['round'] for r in s1new} == {1, 2}, 'the three medians of bw_new read: the same n, rounds 1 and 2 together')
 754      w('- Rule V4 point 3 for bw_new read: the two 8000 MT/s medians are %s GB/s (A-1) and %s GB/s (A-2), %s GB/s '
 755        'apart. Each is the median of %s, rounds 1 and 2 taken together. The median of session 1 is %s GB/s (%s, rounds '
 756        '1 and 2 taken together). It is %s GB/s above A-1 and %s GB/s above A-2. Both distances are larger than the '
 757        'distance between the two baselines. The tables of this section keep the two rounds apart. These three medians '
 758        'take them together. Rule V4 point 3 quotes the two 8000 MT/s medians in this form %s.'
 759        % (g(med(a1n)), g(med(a2n)), g(abs(med(a2n) - med(a1n))), nn(rng(a1n)), g(med(s1new)), nns(s1new),
 760           g(med(s1new) - med(a1n)), g(med(s1new) - med(a2n)), ref(rules)))
 761      need(min(med(s1new) - med(a1n), med(s1new) - med(a2n)) &gt; abs(med(a2n) - med(a1n)), 'session 1 median further than the two baselines apart')</pre></td><td valign="top">Three medians of <code>bw_new read</code>, each over rounds 1 and 2 together.<ul><li><code>s1new</code>: session 1 of part A. <code>a1n</code>, <code>a2n</code>: rows A-1 and A-2.</li><li>Lines 752 and 753 stop the build unless two things hold. A-1 and A-2 have the same n (intervals, processes, boots). Each of the three lists holds rounds 1 and 2.</li><li><code>med</code> is the median of <code>GBps</code>. For an even number of values it is the mean of the two middle values.</li><li>The text prints the two 8000 MT/s medians, their distance, the median of session 1 and its distance to each of them.</li><li>Line 761 stops the build unless the smaller of these two distances is larger than the distance between the two 8000 MT/s medians.</li><li>In the present FACTS.md the medians are 289.54 GB/s (A-1), 304.43 GB/s (A-2) and 330.34 GB/s (session 1) [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 762      p72 = sorted({r['passes'] for x in pa3 for r in x['s1']})
 763      p80 = sorted({r['passes'] for x in pa3 for r in x['a1'] + x['a2']})
 764      n600 = sum(1 for x in pa3 for r in x['a1'] + x['a2'] if r['passes'] == min(p80))
 765      n80 = sum(len(x['a1'] + x['a2']) for x in pa3)
 766      w('- Pass counts differ: the 7200 MT/s intervals of this table completed %s passes. Of the %d intervals at '
 767        '8000 MT/s, %d completed %d passes, and the others %s. The whole-pass stop rule moves the rate together with '
 768        'the pass count (rule V3, effect a). So part A cannot give the size of a change.'
 769        % (' to '.join(map(str, [p72[0], p72[-1]])) if len(p72) &gt; 1 else str(p72[0]), n80, n600, min(p80),
 770           ', '.join(map(str, p80[1:]))))</pre></td><td valign="top">Pass counts of the intervals of the table.<ul><li><code>p72</code>: the distinct pass counts of the session 1 intervals of all cells, sorted. <code>p80</code>: the same for rows A-1 and A-2.</li><li><code>n80</code>: the number of 8000 MT/s intervals of the table. <code>n600</code>: how many of them have the lowest pass count of <code>p80</code>.</li><li>The text prints these values. It then states that the whole-pass stop moves the rate together with the pass count. So part A cannot give the size of a change.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 771      a1la = D['base']['A-1']['procs'][0]
 772      w('- Limit: session 1 started from an idle machine, without the one-thread phase of 2026-11-13 (section 1.5). Row '
 773        'A-1 started directly after its one-thread phase, at a load of %.2f (section 1.5, point 1). Row A-2 started %s, '
 774        'at a load of %.2f (section 1.5, point 11).'
 775        % (a1la['load1'], c['a2pre_txt'], D['probe13']['a2_first']['load1']))
 776      w('')</pre></td><td valign="top">Writes the limit of this comparison: session 1, row A-1 and row A-2 started from different states. <code>a1la</code> is the first process of row A-1. The text prints its load at launch, a text on the work before row A-2 (<code>c['a2pre_txt']</code>), and the load at the launch of the first process of row A-2.</td></tr>
<tr><td colspan="2"><b>Section 4.3 view: equal pass count</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 777      full = 64 * 6 + 56 * 5
 778      w('The same intervals, restricted to an equal pass count (%d or %d passes) and kept apart by round. This view is '
 779        'not part of rule V3. It was added while this sheet was built.' % (full - 1, full))
 780      w('')
 781      same = lambda rs: [r for r in rs if r['passes'] in (full - 1, full)]</pre></td><td valign="top"><code>full</code> = 64 x 6 + 56 x 5 = 664 passes. The code has no comment on the factors. The numbers fit 64 threads with 6 passes each plus 56 threads with 5 passes each. Rule V3 states that a thread faster than 2.684 GB/s runs a sixth pass in the 0.5 s interval [Ref5].<ul><li><code>same</code> keeps the intervals with 663 or 664 passes (<code>full - 1</code> or <code>full</code>).</li><li>Every interval with another pass count is left out of this view.</li><li>The opening text (lines 778 and 779) says that this view is not part of rule V3. It says that the view was added while the sheet was built.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 782      rows, eqr = [], []
 783      for x in pa3:
 784          b = x['a1'] + x['a2']
 785          s72, s80 = same(x['s1']), same(b)
 786          e = dict(x=x, s72=s72, s80=s80, k=compare(s72, s80) if s72 and s80 else None)
 787          eqr.append(e)
 788          if s80:
 789              per = ', '.join('%s %d' % (d, sum(r['dataset'] == d for r in s80)) for d in ('A-1', 'A-2') if any(r['dataset'] == d for r in s80))
 790              cell80 = '%s (n=%d: %s)' % (one_v(s80), len(s80), per)
 791          else:
 792              cell80 = 'no such interval (%d intervals, passes: %s)' % (len(b), ', '.join(map(str, sorted({r['passes'] for r in b}))))
 793          rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'],
 794                       '%s (n=%d)' % (one_v(s72), len(s72)) if s72 else 'no such interval', cell80,
 795                       ('yes' if e['k']['overlap'] else 'no') if e['k'] else '-',
 796                       ('0' if e['k']['overlap'] else '%+.2f' % e['k']['dist']) if e['k'] else '-'])
 797      L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1, GB/s', '8000 MT/s, A-1 and A-2, same round, GB/s',
 798                      'Overlap', 'Distance of the nearest ends, GB/s'], rows))</pre></td><td valign="top">One table row per cell. <code>s72</code> holds the session 1 intervals with 663 or 664 passes. <code>s80</code> holds those of rows A-1 and A-2 together.<ul><li><code>k</code> is <code>compare(s72, s80)</code> when both lists have an interval. If not, <code>k</code> is <code>None</code> and the two last columns show <code>-</code>.</li><li>The 7200 MT/s column prints the range of <code>s72</code> (or its one value) and n. An empty list prints <code>no such interval</code>.</li><li>The 8000 MT/s column prints the range of <code>s80</code>, n, and the number of intervals per row. When <code>s80</code> is empty, it prints <code>no such interval</code>, the number of all 8000 MT/s intervals of the cell, and their distinct pass counts.</li><li>The distance column prints <code>0</code> for an overlap. If not, it prints <code>k['dist']</code> in GB/s with the Python format <code>%+.2f</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 799      r1 = [e for e in eqr if e['x']['round'] == 1]
 800      r2 = [e for e in eqr if e['x']['round'] == 2]
 801      r1all = [r for e in r1 for r in e['x']['a1'] + e['x']['a2']]
 802      p1 = sorted({r['passes'] for r in r1all})
 803      need(not any(e['s80'] for e in r1) and len(p1) == 1, 'round 1 at 8000 MT/s: every interval has the same pass count, not the full one')
 804      both = [e for e in r2 if e['k']]
 805      need(both and all(not e['k']['overlap'] and e['k']['dist'] &gt; 0 for e in both),
 806           'equal pass count, round 2: session 1 above the 8000 MT/s intervals in every cell that has both sides')
 807      none2 = [e for e in r2 if not e['k']]
 808      w('- Round 1: no 8000 MT/s interval has %d or %d passes. All %d have %d passes. So round 1 gives no comparison at '
 809        'an equal pass count.' % (full - 1, full, len(r1all), p1[0]))
 810      w('- Round 2: %s have such intervals at both speeds. Session 1 lies above the 8000 MT/s intervals in %s, by %s GB/s '
 811        'at the nearest ends.%s'
 812        % (' and '.join('%s %s' % (e['x']['binary'], e['x']['kernel']) for e in both),
 813           'both cells' if len(both) == 2 else 'each of these %d cells' % len(both),
 814           ' and '.join(g(e['k']['dist']) for e in both),
 815           (' %s has no such 8000 MT/s interval.' % ' and '.join('%s %s' % (e['x']['binary'], e['x']['kernel']) for e in none2)) if none2 else ''))
 816      n2 = [r for e in r2 for r in e['x']['a1'] + e['x']['a2']]
 817      w('- Limit: this view uses %d of the %d round-2 intervals at 8000 MT/s.' % (sum(len(e['s80']) for e in r2), len(n2)))
 818      w('')</pre></td><td valign="top">Checks and text of this view.<ul><li><code>r1</code>, <code>r2</code>: the cells of round 1 and of round 2. <code>r1all</code>: all 8000 MT/s intervals of the round 1 cells.</li><li>Line 803 stops the build unless two things hold. No round 1 cell has an 8000 MT/s interval with 663 or 664 passes. All intervals of <code>r1all</code> have the same pass count.</li><li><code>both</code>: the round 2 cells that have a comparison. Lines 805 and 806 stop the build unless there is at least one, and session 1 lies above without overlap in each.</li><li><code>none2</code>: the round 2 cells without a comparison. The text names them.</li><li>The text says that the cells of <code>none2</code> have no such 8000 MT/s interval. A cell has no comparison when <code>s72</code> or <code>s80</code> is empty. The code does not test which of the two is empty. In the present FACTS.md the one such cell is <code>bw_old asmread</code>, and its 8000 MT/s list is the empty one [Ref4].</li><li>The last item prints how many of the round 2 intervals at 8000 MT/s this view uses.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.3 view: 120 x per-thread average (est.)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 819      half = 120 * 0.005       # largest rounding error of 120 x (a value rounded to 0.01 GB/s)
 820      w('Rates of the threads in the same rows, kept apart by round. The column per_thread_avg_GBps of the csv gives '
 821        'the average rate of the 120 threads of an interval. 120 times this value is the sum of the thread rates. It '
 822        'is an estimate (est.): the column is rounded to 0.01 GB/s, so each sum is exact to %.1f GB/s.' % half)
 823      w('')
 824      rows, tr = [], []
 825      av = lambda rs: [r['per_thread_avg_GBps'] for r in rs]
 826      span = lambda v, f='%.2f': (f % min(v)) if min(v) == max(v) else (f + ' to ' + f) % (min(v), max(v))</pre></td><td valign="top"><code>half</code> = 120 x 0.005 = 0.6 GB/s. The csv column <code>per_thread_avg_GBps</code> is rounded to 0.01 GB/s. So its rounding error is at most 0.005 GB/s, and 120 times the column is exact to 0.6 GB/s.<ul><li><code>av</code> returns the values of this column for a record list.</li><li><code>span</code> prints a list of numbers as one value when all are equal. If not, it prints the lowest to the highest value.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 827      for x in pa3:
 828          s1, a1, a2 = av(x['s1']), av(x['a1']), av(x['a2'])
 829          b = a1 + a2
 830          t = dict(x=x, est=120 * (min(s1) - max(b)), agg=min(x['above']), above=min(s1) &gt; max(b))
 831          tr.append(t)
 832          rows.append(['%s %s' % (x['binary'], x['kernel']), x['round'], span(s1), span(a1), span(a2) if a2 else 'no process',
 833                       span([120 * v for v in s1], '%.1f'), span([120 * v for v in b], '%.1f'), '%+.1f' % t['est'], '%+.2f' % t['agg']])
 834      L.extend(table(['Binary and kernel', 'Round', '7200 MT/s, session 1: average per thread, GB/s',
 835                      '8000 MT/s, A-1: average per thread, GB/s', '8000 MT/s, A-2: average per thread, GB/s',
 836                      '7200 MT/s: 120 x average, GB/s (est.)', '8000 MT/s, A-1 and A-2: 120 x average, GB/s (est.)',
 837                      'Distance of the nearest ends by 120 x average, GB/s (est.)',
 838                      'Distance of the nearest ends by aggregate_GBps, GB/s'], rows))</pre></td><td valign="top">One table row per cell. <code>s1</code>, <code>a1</code> and <code>a2</code> hold the per-thread averages of session 1, row A-1 and row A-2. <code>b</code> joins <code>a1</code> and <code>a2</code>.<ul><li><code>est</code>: 120 x (lowest value of <code>s1</code> - highest value of <code>b</code>). It is the distance of the nearest ends by the estimate, in GB/s.</li><li><code>agg</code>: the smallest value of <code>x['above']</code>. It is the lowest <code>aggregate_GBps</code> of session 1 minus the highest one of rows A-1 and A-2 in the same round.</li><li><code>above</code>: true when every value of <code>s1</code> is above every value of <code>b</code>.</li><li>The table prints the averages with 2 decimal places and 120 x average with 1 decimal place. It prints <code>est</code> with the format <code>%+.1f</code> and <code>agg</code> with <code>%+.2f</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 839      need(all(t['above'] for t in tr), 'per-thread average of session 1 above the 8000 MT/s processes of the same round in every cell')
 840      larger = [t for t in tr if t['est'] &gt; t['agg']]
 841      smaller = [t for t in tr if t['est'] &lt;= t['agg']]
 842      need(all(t['agg'] - t['est'] &lt;= 2 * half for t in smaller), 'a smaller estimated distance stays inside the rounding of the column')</pre></td><td valign="top">Line 839 stops the build unless <code>above</code> is true in every cell. <code>larger</code> holds the cells where <code>est</code> is greater than <code>agg</code>. <code>smaller</code> holds the other cells. Line 842 stops the build unless <code>agg</code> - <code>est</code> is at most 2 x <code>half</code> = 1.2 GB/s in every cell of <code>smaller</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 843      # check of the estimate on the file that holds one row per thread (row A-2, option --per-thread)
 844      chk_n, chk_max = 0, 0.0
 845      for p_ in D['base']['A-2']['procs']:
 846          for iv in p_['iv']:
 847              rows_ = p_['thr'][iv['rep']]
 848              need(len(rows_) == 120, '120 thread rows per interval in A1.csv')
 849              chk_n += 1
 850              chk_max = max(chk_max, abs(sum(rows_) - 120 * iv['tavg']))
 851      need(chk_max &lt;= 2 * half + 1e-9, 'sum of the thread rows of A1.csv equal to 120 x per_thread_avg within the rounding')</pre></td><td valign="top">Check of the estimate against measured thread rates. A1.csv (row A-2) was written with the option <code>--per-thread</code>. It holds one row per thread and interval.<ul><li>The loop visits every interval of every process of A1.csv. It does not select a kernel. The file holds read kernels and write kernels.</li><li><code>rows_</code> holds the thread rates of the interval. Line 848 stops the build unless there are 120.</li><li><code>chk_max</code>: the largest absolute difference between the sum of the 120 thread rates and 120 x <code>per_thread_avg_GBps</code>, over all intervals. <code>chk_n</code> counts the intervals.</li><li>Line 851 stops the build unless <code>chk_max</code> is at most 1.2 GB/s. The line adds 1e-9 GB/s to this limit for floating-point error.</li><li>In the present FACTS.md: 36 intervals, largest difference 0.66 GB/s [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 852      w('- In all %d cells every per-thread average of session 1 lies above every per-thread average of the 8000 MT/s '
 853        'processes of the same round.' % len(tr))
 854      w('- By 120 x average (est.) the distance of the nearest ends is larger than by aggregate_GBps in %d of the %d '
 855        'cells.%s' % (len(larger), len(tr),
 856                      (' In %s it is %s GB/s smaller. That is inside the rounding of the column (each end is exact to %.1f GB/s).'
 857                       % (' and '.join('%s %s, round %d' % (t['x']['binary'], t['x']['kernel'], t['x']['round']) for t in smaller),
 858                          ' and '.join('%.2f' % (t['agg'] - t['est']) for t in smaller), half)) if smaller else ''))
 859      w('- Check of the estimate: A1.csv (row A-2) holds one row per thread, rounded to 0.01 GB/s. Over its %d '
 860        'intervals the sum of the 120 thread rows differs from 120 x per_thread_avg_GBps by at most %.2f GB/s %s. Both '
 861        'sides are rounded, so a difference of up to %.1f GB/s fits.'
 862        % (chk_n, chk_max, ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv')), 2 * half))
 863      w('- So by this estimate the sum of the thread rates is also higher in session 1 than in the 8000 MT/s rows of '
 864        'the same round. The estimate does not show a part of a distance that comes from the pass count alone.')
 865      w('- Insufficient data: how much of each distance in the first table comes from the pass-count step of the '
 866        'whole-pass stop rule. Part A with the option --per-thread at 7200 MT/s would resolve it. It prints the rate of '
 867        'every thread, as A1.csv does.')
 868      w('')
 869      c['thr'] = tr
 870</pre></td><td valign="top">Writes five list items and stores the list <code>tr</code> in <code>c['thr']</code>.<ul><li>Item 1: every per-thread average of session 1 lies above those of the 8000 MT/s processes. Line 839 checks it.</li><li>Item 2: in how many cells <code>est</code> is larger than <code>agg</code>. For the cells of <code>smaller</code> it prints <code>agg</code> - <code>est</code> with 2 decimal places.</li><li>Item 3: the result of the A1.csv check. It prints <code>chk_n</code> and <code>chk_max</code>.</li><li>Items 4 and 5: what the estimate shows, and which measurement is missing.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.4: asmread in part L</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 871      # ---- 4.4 asmread part L
 872      w('### 4.4 Load-only loop in part L (asmread, position 1, directly after oldread)')
 873      w('')
 874      w('- asmread is used in place of the new read kernel here. It is the same loop of 8 "ldp q" loads per 256 B %s.'
 875        % ref(os.path.join(W15, 'FINDINGS.md')))
 876      w('- F72d12 and control I are separate 7200 MT/s rows of the same boot. In every range test of rule V1 point 2 '
 877        'each of them is its own row. Other places of this sheet give one range over several of these rows, for example '
 878        'the three visits in section 4.6 and the sums per mesh in section 4.7. Such a place says which rows it takes '
 879        'together.')
 880      w('')</pre></td><td valign="top">Writes the title and two opening items. The first says that asmread is used in place of the new read kernel. The second says that F72d12 and control I are separate rows in every range test.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 881      L.extend(ranges([('part L (T72L1 to T72L3). ' + STANDIN, sL, L72a)] + lrows('asmread', 1)
 882                      + [('pool L-1 to L-4', 'all bwx12 rows of the fixed list', P12a)] + orows('asmread', 1)
 883                      + [('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows', PALLa),
 884                         ('X2d12', DESC['X2d12'], x2a), ('F72d12', DESC['F72d12'], F72a), ('control I (T72I1, T72I2)', sI, I72a)]))</pre></td><td valign="top">Writes the range table of asmread. Each row gives n, the lowest to highest rate and the median of one record list.<ul><li>Part L (<code>L72a</code>).</li><li>Each of the rows L-1 to L-4 at position 1, and their pool (<code>P12a</code>).</li><li>Rows R0 and R0b at position 1, and the pool with them (<code>PALLa</code>).</li><li>X2d12, F72d12 (<code>F72a</code>) and control I (<code>I72a</code>).</li><li>The title in line 872 says <code>position 1, directly after oldread</code>. The code selects <code>L72a</code>, <code>F72a</code>, <code>I72a</code> and <code>x2a</code> (asmread of row X2d12, line 473) by row and kernel, without a position. This file does not test the position or the kernel before of these four lists. In the present facts.json every record of them has position 1 and <code>kernel_before</code> oldread.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 885      L.extend(cmps('L', 'asmread', [(('part L', 'part L. ' + STANDIN), L72a, sc_a),
 886                                      (('F72d12 ' + OLD_OWN, 'F72d12 ' + OWN), F72a, sc_a),
 887                                      (('control I ' + OLD_OWN, 'control I ' + OWN), I72a, sc_a)], notes={'part L': STANDIN}))</pre></td><td valign="top"><code>cmps</code> runs nine range tests: part L, F72d12 and control I, each against the three scopes of <code>sc_a</code> (line 482).<ul><li>The scopes are L-1 alone, the pool L-1 to L-4, and the pool with R0 and R0b.</li><li>Only the pool L-1 to L-4 decides. So three tests get a wording.</li><li><code>notes</code> adds the text of <code>STANDIN</code> to the three facts.json entries of part L.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 888      need(not compare(L72a, l1a)['overlap'] and not compare(L72a, PALLa)['overlap'], 'part L asmread above every 8000 MT/s scope')
 889      need(not cIa['overlap'] and cIa['dist'] &gt; 0, 'control I asmread above the 8000 MT/s pool')
 890      kF1, kI1 = compare(F72a, l1a), compare(I72a, l1a)
 891      need(not kF1['overlap'] and kF1['dist'] &gt; 0 and not kI1['overlap'] and kI1['dist'] &gt; 0,
 892           'asmread: F72d12 and control I above L-1 alone')
 893      c['kF1'], c['kI1'] = kF1, kI1</pre></td><td valign="top">Checks for the text below.<ul><li>Line 888: asmread of part L overlaps neither L-1 alone nor the pool with R0 and R0b. This line does not test which range is higher. <code>facts_text.py</code> tests that part L lies above the pool L-1 to L-4 [Ref1].</li><li>Line 889: control I lies above the pool L-1 to L-4 without overlap (<code>cIa</code>).</li><li>Lines 890 to 892: <code>kF1</code> and <code>kI1</code> compare F72d12 and control I with L-1 alone. Each must lie above it without overlap.</li><li>Line 893 keeps the two comparisons in <code>c</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 894      l1la = D['rx']['L-1']['launches']['a6456']
 895      Ila = [x['launches'][0] for x in D['X'] if x['part'] == 'I']
 896      Igap = [evd[x['tag']]['gap_s'] for x in D['X'] if x['part'] == 'I']
 897      Iref = ' '.join(ref(os.path.join(x['folder'], 'launches.txt')) for x in D['X'] if x['part'] == 'I')</pre></td><td valign="top">Start states of L-1 and of control I.<ul><li><code>l1la</code>: the launch line of the L-1 process a6456. <code>Ila</code>: the launch lines of the control I processes.</li><li><code>Igap</code>: for each control I process, the seconds since the step before it ended.</li><li><code>Iref</code>: the <code>[RefN]</code> labels of the <code>launches.txt</code> files of control I. Line 1175 uses it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 898      need(max(la['load1'] for la in Ila) &lt; 1.0 and l1la['load1'] &lt; 1.0 and min(la['load5'] for la in Ila) &gt; 1.0
 899           and max(l1la['load5'], l1la['load15']) &lt; 1.0 and min(Igap) &gt; 60,
 900           'control I and L-1: both below 1.0 in the 1-minute load, control I above 1.0 in the 5-minute load and more '
 901           'than 60 s after 120-thread work')</pre></td><td valign="top">The build stops unless all of these hold:<ul><li>The 1-minute load is below 1.0 for L-1 and for every control I process.</li><li>The 5-minute load of every control I process is above 1.0.</li><li>The 5-minute and the 15-minute load of L-1 are below 1.0.</li><li>Every <code>Igap</code> is above 60 s.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 902      w('- Part L, wording by rule V1 point 2: "%s". Part L is higher by %s GB/s at the nearest ends. n at 7200 MT/s: '
 903        '%s. n at 8000 MT/s: %s. The result is the same against L-1 alone and against the pool with the other-binary rows.'
 904        % (cLa['wording'], g(cLa['dist']), nn(cLa['a'], sessions=True), nn(cLa['b'])))
 905      w('- Control I (%s, idle start by the 1-minute load rule): "%s". It is higher by %s GB/s at the nearest ends '
 906        '(%s GB/s against L-1 alone). n at 7200 MT/s: %s. n at 8000 MT/s: %s. The start state of control I is not that '
 907        'of L-1. L-1 was launched at load averages of %.2f / %.2f / %.2f (1 / 5 / 15 min) %s. Control I was launched '
 908        '%s s after 120-thread work (section 4.6).'
 909        % (ADDED, cIa['wording'], g(cIa['dist']), g(kI1['dist']), nns(I72a), nn(cIa['b']), l1la['load1'], l1la['load5'],
 910           l1la['load15'], ref(os.path.join(D['rx']['L-1']['folder'], 'launches.txt')),
 911           ' s and '.join('%.0f' % v for v in Igap)))
 912      w('- F72d12 (same boot, same speed, load %.2f at launch): its range %s the pool L-1 to L-4%s.'
 913        % (f72la['load1'], 'overlaps' if cFa['overlap'] else 'does not overlap',
 914           ('. It does not overlap L-1 alone, where it is %s GB/s higher' % g(kF1['dist'])) if not kF1['overlap'] else ''))</pre></td><td valign="top">Writes three list items.<ul><li>Part L: the wording and the distance of <code>cLa</code> (part L against the pool L-1 to L-4), and both n.</li><li>Control I: the wording and the distance of <code>cIa</code>, the distance against L-1 alone (<code>kI1</code>), both n, the three load averages of L-1, and the <code>Igap</code> values.</li><li>F72d12: its load at launch, and whether its range overlaps the pool (<code>cFa</code>). When it does not overlap L-1 alone, the text adds the distance <code>kF1['dist']</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.4: the pool without the interval with error records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 915      hwc = c['hw']
 916      wo = rng(hwc['P12a_wo'])
 917      kLw, kFw, kIw = compare(L72a, hwc['P12a_wo']), compare(F72a, hwc['P12a_wo']), compare(I72a, hwc['P12a_wo'])
 918      need(not kLw['overlap'] and kLw['dist'] &gt; 0 and not kIw['overlap'] and kIw['dist'] &gt; 0 and kFw['overlap']
 919           and wo['lo'] &lt;= rng(F72a)['lo'] and rng(F72a)['hi'] &lt;= wo['hi'] and wo['hi'] == cLa['b']['hi'],
 920           'without the interval with error records: part L and control I above the pool, F72d12 inside it')
 921      c['hw']['wo'] = wo</pre></td><td valign="top"><code>hwc['P12a_wo']</code> is the pool <code>P12a</code> without its lowest interval. That interval has two hardware error records inside it (lines 297 to 303). <code>wo</code> is the range of this smaller pool. Lines 918 to 920 stop the build unless all of these hold:<ul><li>Part L and control I each lie above this pool without overlap.</li><li>F72d12 overlaps it, and the whole range of F72d12 lies inside <code>wo</code>.</li><li>The highest rate of <code>wo</code> equals the highest rate of the full pool.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 922      w('- Hardware error records (section 4.1): 2 corrected records fall inside the interval that sets the lower end of '
 923        'the pool L-1 to L-4 (%s GB/s, row %s, process %s, round %d). Without this one interval the pool spans %s GB/s '
 924        '(%s GB/s wide, %s %% of its lower end, %s). No wording by rule V1 point 2 changes with it: part L and control I '
 925        'still lie above the pool, and F72d12 still lies inside its range. The upper end of the pool is the same. So '
 926        'the distances of the nearest ends do not change. For the rerun the records are not known (section 1.5, '
 927        'point 8).'
 928        % (g(hwc['low_a']['GBps']), hwc['low_a']['dataset'], hwc['low_a']['tag'], hwc['low_a']['round'], sp(wo),
 929           g(wo['hi'] - wo['lo']), pc(width_pct(wo)), nn(wo)))
 930      w('- By rule V1 point 3 no percent change is given. Section 4.6 states what follows.')
 931      w('')
 932</pre></td><td valign="top">Writes the item on the hardware error records.<ul><li>It prints the rate, row, tag and round of the removed interval (<code>low_a</code>).</li><li>It prints the range of the pool without it, its width in GB/s (highest - lowest), its width in percent of its lower end, and n.</li><li>The count <code>2 corrected records</code> is typed in the template. Line 291 tests the count. Line 245 tests the severity. Lines 298 to 300 test that the interval with these records is <code>low_a</code>.</li><li>The last item (line 930) has fixed words.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.5: kernel read in part C</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 933      # ---- 4.5 part C load-only
 934      w('### 4.5 Load-only kernels in part C')
 935      w('')
 936      w('**Kernel `read` (new read kernel in bwx12).**')
 937      w('')
 938      w('- %s.' % NO_READ)
 939      w('- Text required by rule F2 point 3: The bwx12 kernel read (new C read loop) was never run with bwx12 at '
 940        '8000 MT/s. The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its '
 941        'place.')
 942      w('- The nearest data come from another binary: the first runner bwx of 2026-11-13. They are not a like-for-like '
 943        'baseline. The like-for-like 8000 MT/s baseline of the new read kernel is part A (section 4.3).')
 944      w('')</pre></td><td valign="top">Writes the title and three items for kernel <code>read</code>. They state that bwx12 never ran this kernel at 8000 MT/s (<code>NO_READ</code>). So the rows of runner bwx below come from another binary. They are not a like-for-like baseline.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 945      Rao = sel(C, kernel='read', kernel_before='oldread')
 946      Raa = sel(C, kernel='read', kernel_before='asmread')
 947      rows = [('part C, read after oldread (cfwd, position 1)', 'rerun', Rao)]
 948      for d in BWX:
 949          rows.append((d + ', read at position 1 (after oldread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=1)))
 950      bx1 = sel(recs, dataset=set(BWX), kernel='read', pos=1)
 951      rows.append(('pool B7a, B7b, C3a, C3b, position 1', 'other binary (bwx)', bx1))
 952      rows.append(('the same, only the %d processes with --start common' % nsc, 'other binary (bwx)', scm(bx1)))
 953      for d in ('B5a', 'B5b'):
 954          rows.append((d + ', read at position 1 (after oldread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=1)))
 955      rows.append(('part C, read after asmread (crev, position 1)', 'rerun', Raa))
 956      for d in BWX:
 957          rows.append((d + ', read at position 6 (after asmread)', DESC[d], sel(recs, dataset=d, kernel='read', pos=6)))
 958      bx6 = sel(recs, dataset=set(BWX), kernel='read', pos=6)
 959      rows.append(('pool B7a, B7b, C3a, C3b, position 6', 'other binary (bwx)', bx6))
 960      rows.append(('the same, only the %d processes with --start common' % nsc, 'other binary (bwx)', scm(bx6)))
 961      L.extend(ranges(rows))</pre></td><td valign="top">Rows of the range table of kernel <code>read</code>. Part C is grouped by the kernel that ran directly before (rule V2).<ul><li><code>Rao</code>: read of part C directly after oldread. <code>Raa</code>: read of part C directly after asmread.</li><li>Shown with <code>Rao</code>: read at position 1 of each of the rows B7a, B7b, C3a and C3b, and their pool <code>bx1</code>. Then the pool with the <code>--start common</code> processes only, and rows B5a and B5b.</li><li>Shown with <code>Raa</code>: read at position 6 of the same four rows, their pool <code>bx6</code>, and the pool with the <code>--start common</code> processes only.</li><li>The row labels call position 1 <code>after oldread</code> and position 6 <code>after asmread</code>.</li><li>For the bwx rows the code selects by position. This file does not test the kernel before of these rows. In the present facts.json <code>kernel_before</code> is oldread for every record of <code>bx1</code> and for every read record at position 1 of rows B5a and B5b. It is asmread for every record of <code>bx6</code>.</li><li>The labels of <code>Rao</code> and <code>Raa</code> add <code>cfwd, position 1</code> and <code>crev, position 1</code>. No line of this file tests these parts of the labels. In the present facts.json every record of <code>Rao</code> is at position 1 of a cfwd.csv file. Every record of <code>Raa</code> is at position 1 of a crev.csv file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 962      k1, k6 = compare(Rao, bx1), compare(Raa, bx6)
 963      q2row('C', 'read after oldread', 'part C, cfwd', 'other binary bwx, position 1 (not like-for-like)', k1, False, NO_READ)
 964      q2row('C', 'read after asmread', 'part C, crev', 'other binary bwx, position 6 (not like-for-like)', k6, False, NO_READ)
 965      w('- Against the other-binary pool of the same position, read after oldread is %s. Read after asmread is %s.'
 966        % tuple(('%s GB/s above its highest value' % g(k['dist'])) if k['dist'] &gt; 0 else
 967                ('%s GB/s below its lowest value' % g(-k['dist'])) if k['dist'] &lt; 0 else 'inside its range' for k in (k1, k6)))</pre></td><td valign="top"><code>k1</code> compares <code>Rao</code> with <code>bx1</code>. <code>k6</code> compares <code>Raa</code> with <code>bx6</code>.<ul><li><code>q2row</code> stores both tests in <code>V['q2_rows']</code> with <code>decides</code> = False and the note <code>NO_READ</code>. So they carry no wording.</li><li>The text prints each distance in GB/s. A positive <code>dist</code> prints as above the highest value of the bwx pool. A negative <code>dist</code> prints as below its lowest value.</li><li>A <code>dist</code> of 0 prints as <code>inside its range</code>. <code>dist</code> is 0 for every overlap, also when only a part of the two ranges overlaps.</li><li>In the present FACTS.md both distances are positive: 5.60 GB/s and 3.11 GB/s [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 968      cnt = sorted({(r['dataset'], r['count']) for r in sel(recs, dataset=set(BWX))})
 969      w('- Difference of these references (rule V2 point 4): they used the binary bwx of 2026-11-13. The csv headers '
 970        'show the counter setting: %s (count=1 means with core counters). Part C used bwx12 with counters.'
 971        % ', '.join('%s count=%d' % (d, c_) for d, c_ in cnt))
 972      allp = {r['proc_key']: r for r in sel(recs, dataset=set(BWX))}
 973      noff = sum(1 for r in allp.values() if r['start'] == 'offset')
 974      need(noff + nsc == len(allp) and noff &gt; 0, 'the processes of the bwx pool used --start common or --start offset')
 975      bx2 = sel(recs, dataset=set(BWX), kernel='asmread', pos=2)
 976      same_ends = all((rng(scm(v))['lo'], rng(scm(v))['hi']) == (rng(v)['lo'], rng(v)['hi']) for v in (bx1, bx2, bx6))
 977      w('- A second difference: %d of the %d processes of this pool (tags common-6000-offset-*) used --start offset. '
 978        'Part C used --start common %s %s. --start is an option of the runner. This sheet only notes that its value '
 979        'differs. The rows "only the %d processes with --start common" show the pool without them. %s'
 980        % (noff, len(allp), ref(os.path.join(S_, 'cfwd.spec')), ref(os.path.join(S_, 'crev.spec')), nsc,
 981           'At positions 1, 2 and 6 the lowest and the highest value stay the same, and the medians change.' if same_ends
 982           else 'Lowest and highest values change, see the rows.'))
 983      w('- Rule V4 and rule V2 point 4 name different process lists for these rows. Decision (p) in section 2 states '
 984        'the choice.')
 985      w('')</pre></td><td valign="top">Two differences of the bwx reference.<ul><li><code>cnt</code>: the distinct pairs of row name and <code>count</code> in the records of rows B7a, B7b, C3a and C3b. The text prints them. <code>count=1</code> means that the run read core counters.</li><li>The words <code>Part C used bwx12 with counters</code> are template text. No line of this file tests the field <code>count</code> of the part C records. In the present facts.json <code>count</code> is 1 for every record of part C.</li><li><code>allp</code>: one record per process of these rows. <code>noff</code> counts the processes with <code>--start offset</code>. Line 974 stops the build unless <code>noff</code> + <code>nsc</code> is the number of all processes and <code>noff</code> is above 0.</li><li><code>bx2</code>: asmread at position 2 of the bwx rows.</li><li><code>same_ends</code>: true when the lowest and the highest rate of <code>bx1</code>, <code>bx2</code> and <code>bx6</code> stay the same with the <code>--start common</code> processes only. It selects one of two sentences.</li><li>The first sentence also says <code>the medians change</code>. The code does not test this part. In the present FACTS.md each of the three medians changes [Ref4]. The last item (lines 983 and 984) has fixed words on decision (p).</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.5: kernel asmread in part C</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 986      w('**Kernel `asmread`.**')
 987      w('')
 988      Aao = sel(C, kernel='asmread', kernel_before='oldread')
 989      Aar = sel(C, kernel='asmread', kernel_before='read')
 990      Aaf = sel(C, kernel='asmread', kernel_before=first)
 991      L.extend(ranges([('part C, asmread after oldread (crev, round 1, position 0)', 'rerun, the condition of part L', Aao),
 992                       ('part C, asmread as first interval (crev, round 0, position 0)', 'rerun', Aaf),
 993                       ('part C, asmread after read (cfwd, position 2)', 'rerun', Aar),
 994                       ('L-1 alone', L1C + '. asmread at position 1 (after oldread)', l1a),
 995                       ('pool L-1 to L-4', 'bwx12 rows, asmread at position 1 (after oldread)', P12a),
 996                       ('pool L-1 to L-4, R0, R0b', 'bwx12 rows and other-binary rows, asmread at position 1 (after oldread)', PALLa),
 997                       ('pool B7a, B7b, C3a, C3b, position 2', 'other binary (bwx), asmread after read', bx2),
 998                       ('the same, only the %d processes with --start common' % nsc, 'other binary (bwx), asmread after read', scm(bx2))]))</pre></td><td valign="top">Kernel asmread of part C, in three groups by the kernel that ran directly before.<ul><li><code>Aao</code>: after oldread. <code>Aar</code>: after read. <code>Aaf</code>: asmread as the first interval of the process.</li><li>The range table shows the three groups, L-1 alone, the pool L-1 to L-4 (<code>P12a</code>) and the pool with R0 and R0b (<code>PALLa</code>).</li><li>It also shows asmread at position 2 of runner bwx (<code>bx2</code>), with all processes and with the <code>--start common</code> processes only. The records of rows B7a, B7b, C3a and C3b also hold asmread at position 5. In the present facts.json their <code>kernel_before</code> is <code>asmread2</code>, another kernel of runner bwx. No table row and no range test of section 4.5 uses these records.</li><li>The labels call position 2 of runner bwx <code>asmread after read</code>. The code selects <code>bx2</code> by position. This file does not test the kernel before of these rows. In the present facts.json <code>kernel_before</code> is <code>read</code> for every record of <code>bx2</code>.</li><li>The labels of the three groups also name the spec and the round, for example <code>crev, round 1, position 0</code>. The check in lines 999 to 1001 tests the positions of the three groups. No line of this file tests their specs or rounds. In the present facts.json they are as the labels say.</li><li>The row of L-1 alone says <code>asmread at position 1 (after oldread)</code>. The code selects <code>l1a</code> by row and kernel, without a position (line 480). The check in lines 999 to 1001 tests <code>PALLa</code>, not <code>l1a</code>. In the present facts.json both records of <code>l1a</code> are at position 1 with <code>kernel_before</code> oldread.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 999      need({r['pos'] for r in Aao} == {0} == {r['pos'] for r in Aaf} and {r['pos'] for r in Aar} == {2}
1000           and {r['pos'] for r in PALLa} == {1} and {r['kernel_before'] for r in PALLa} == {'oldread'},
1001           'asmread: position 0 or 2 in part C, position 1 directly after oldread in the rows L-1 to L-4, R0, R0b')</pre></td><td valign="top">Stops the build unless the positions are as the labels say.<ul><li><code>Aao</code> and <code>Aaf</code>: position 0.</li><li><code>Aar</code>: position 2.</li><li>Every interval of <code>PALLa</code>: position 1, directly after oldread.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1002      # The 8000 MT/s rows hold asmread at position 1, directly after oldread. The first group of part C matches them
1003      # in the kernel that ran directly before, not in the position. The other two groups match in neither.
1004      m_k = lambda name: (name + ' (after oldread)', name + ' (after oldread), asmread at position 1 against position 0 '
1005                          'in part C')
1006      m_0 = ('pool L-1 to L-4 (after oldread, position not matched)',
1007             'pool L-1 to L-4 (after oldread, at position 1): kernel before and position not matched')
1008      L.extend(cmps('C', 'asmread', [
1009          ('part C, asmread after oldread', Aao, [(m_k('L-1 alone'), l1a, False), (m_k('pool L-1 to L-4'), P12a, True),
1010                                                  (m_k('pool L-1 to L-4, R0, R0b'), PALLa, False)]),
1011          ('part C, asmread as first interval', Aaf, [(m_0, P12a, False)]),
1012          ('part C, asmread after read', Aar, [(m_0, P12a, False),
1013                                               ('other binary bwx, position 2 (after read)', bx2, False)])],
1014          F2_NOTE + ' The 8000 MT/s rows match in the kernel that ran directly before, not in the position.'))</pre></td><td valign="top"><code>m_k</code> and <code>m_0</code> build scope labels. A label says in what an 8000 MT/s list matches the part C group: the kernel before, the position, or neither. <code>cmps</code> runs six range tests.<ul><li><code>Aao</code> against L-1 alone, against the pool L-1 to L-4, and against the pool with R0 and R0b. These lists match in the kernel before, not in the position. Only the pool L-1 to L-4 decides.</li><li><code>Aaf</code> against the pool L-1 to L-4. It matches in neither.</li><li><code>Aar</code> against the pool L-1 to L-4 (it matches in neither) and against <code>bx2</code>.</li><li>The five tests without <code>decides</code> are printed without a wording.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1015      kAao = compare(Aao, P12a)
1016      need(not compare(Aao, l1a)['overlap'] and not compare(Aao, PALLa)['overlap'], 'part C asmread after oldread above every 8000 MT/s scope')
1017      w('- asmread after oldread, wording by rule V1 point 2: "%s". n at 7200 MT/s: %s (%s). n at 8000 MT/s: %s. The '
1018        'result is the same against L-1 alone and against the pool with the other-binary rows. %s'
1019        % (kAao['wording'], nns(Aao), ', '.join(dict.fromkeys(r['tag'] for r in Aao)), nn(kAao['b']), F2_NOTE))
1020      c['kAao'], c['Aao'] = kAao, Aao
1021      w('- No asmread group of part C has a position-matched bwx12 baseline (rule V4). The group "asmread after oldread" '
1022        '(crev, round 1, position 0) matches rows L-1 to L-4 (asmread at position 1) only in the kernel that ran '
1023        'directly before (rule V2 points 1 and 4). The other two groups do not match in that kernel either. Their rows '
1024        'in the table carry no wording.')
1025      w('- The rows without a wording also show part C next to 8000 MT/s rows. Decision (r) in section 2 names them.')</pre></td><td valign="top"><code>kAao</code> repeats the deciding test: <code>Aao</code> against <code>P12a</code>.<ul><li>Line 1016 stops the build unless <code>Aao</code> also overlaps neither L-1 alone nor the pool with R0 and R0b. This line does not test which range is higher. Line 1351 tests it for the pool L-1 to L-4.</li><li>The text prints the wording, both n and the tags of the processes of <code>Aao</code>.</li><li><code>c['kAao']</code> and <code>c['Aao']</code> keep the test for the short version in section 0.</li><li>The two last items have fixed words.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1026      w('- Rule V2 point 5 asks to state that part L and the forward order measure the lower of the two conditions. '
1027        'At 8000 MT/s (runner bwx) the median of read after oldread is %s GB/s below the median of read after asmread '
1028        '(%s GB/s with the %d --start common processes only). At 7200 MT/s it is %s GB/s below, and the two ranges '
1029        'overlap. The reverse order comes from %d processes (%s).'
1030        % (g(med(bx6) - med(bx1)), g(med(scm(bx6)) - med(scm(bx1))), nsc, g(med(Raa) - med(Rao)),
1031           len({r['proc_key'] for r in Raa}), ', '.join(dict.fromkeys(r['tag'] for r in Raa))))
1032      need(med(Raa) &gt; med(Rao) and overlap(rng(Raa), rng(Rao)), 'read after asmread above read after oldread, ranges overlap')</pre></td><td valign="top">Rule V2 point 5: which of the two conditions of kernel <code>read</code> is the lower one.<ul><li>8000 MT/s, runner bwx: <code>med(bx6) - med(bx1)</code>, the median of read at position 6 minus the median of read at position 1, in GB/s. The same with the <code>--start common</code> processes only.</li><li>7200 MT/s, part C: <code>med(Raa) - med(Rao)</code>.</li><li>The text also prints the number and the tags of the processes of <code>Raa</code>.</li><li>Line 1032 stops the build unless the 7200 MT/s difference is positive and the ranges of <code>Raa</code> and <code>Rao</code> overlap.</li><li>These lines do not test the sign of the two 8000 MT/s differences. In the present FACTS.md both are positive: 10.66 GB/s and 12.29 GB/s [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1033      kAA = compare(Aao, Aar)
1034      need(not kAA['overlap'] and kAA['dist'] &gt; 0, 'part C: asmread after oldread above asmread after read, no overlap')
1035      w('- For asmread the order is the opposite at 7200 MT/s. asmread directly after oldread (crev, round 1, the '
1036        'condition of part L) gave %s GB/s. asmread after read (cfwd) gave %s GB/s. The two ranges do not overlap. They '
1037        'are %s GB/s apart. So the part C data at 7200 MT/s do not show that part L measures the lower condition. '
1038        'Order and process are not separated: each order has %d processes.'
1039        % (' and '.join(g(r['GBps']) for r in Aao), sp(rng(Aar)), g(kAA['dist']), rng(Aar)['procs']))
1040      w('')
1041</pre></td><td valign="top"><code>kAA</code> compares <code>Aao</code> with <code>Aar</code>, both of part C at 7200 MT/s. Line 1034 stops the build unless asmread after oldread lies above asmread after read without overlap.<ul><li>The text prints each rate of <code>Aao</code>, the range of <code>Aar</code> and the distance in GB/s.</li><li>The text ends with the number of processes of each order. This number is the process count of <code>Aar</code> only. No line tests that <code>Aao</code> has the same count. In the present facts.json both lists have 2 processes.</li><li>The function <code>section4</code> continues after line 1041 with section 4.6.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.6: three visits in the 7200 MT/s boot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1042      # ---- 4.6 same boot
1043      w('### 4.6 What the rows of the same boot show, and what follows for Q2')
1044      w('')</pre></td><td valign="top">Continues the function <code>section4</code> that starts at line 24. These lines write the heading of section 4.6.<ul><li>Lines 1042 to 1615 read no csv row and no csv column. They work on the interval records, and on the comparisons and record lists that lines 31 to 33 took from <code>c</code>.</li><li>These lines call neither <code>cmps</code> nor <code>q2row</code>. So they add no range test to <code>V['q2_rows']</code>. The verdict texts of section 4.9 use the comparisons that were made before.</li><li>A total rate is the field <code>GBps</code> of a record, in GB/s. Part A record: the csv column <code>aggregate_GBps</code>. bwx record: the sum over the threads of bytes / elapsed_s / 1e9 [Ref2].</li><li>Section 4.7 uses two other fields of a bwx record: <code>mesh0_GBps</code> and <code>mesh1_GBps</code>, the sums per mesh (line 1221).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1045      allv = F72a + L72a + I72a
1046      av = rng(allv)
1047      kLI, kIF = compare(L72a, I72a), compare(I72a, F72a)
1048      need(not kLI['overlap'] and not kIF['overlap'] and kLI['dist'] &gt; 0 and kIF['dist'] &gt; 0, 'three visits in rising order without overlap')</pre></td><td valign="top"><ul><li><code>allv</code>: the asmread records of row F72d12, of part L and of control I, joined to one list. <code>facts_text.py</code> selected each list by <code>dataset</code> and <code>kernel</code>, with no position condition [Ref1]. In facts.json all of these records are at position 1. They are 2, 6 and 4 intervals.</li><li><code>av</code>: the lowest, the highest and the median rate of this list. Before this line <code>av</code> was a helper (line 825). From here it is a range.</li><li><code>kLI</code> compares part L with control I. <code>kIF</code> compares control I with F72d12. Here <code>compare</code> works on two lists of the same 7200 MT/s boot.</li><li>The build stops unless part L lies above control I and control I lies above F72d12, both without overlap.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1049      tI = [evd[t]['first'] for t in ('T72I1', 'T72I2')]
1050      tL = [evd[t]['first'] for t in ('T72L1', 'T72L2', 'T72L3')]
1051      w('The same argument line (like.spec) ran at three times in boot %s at 7200 MT/s. asmread at position 1 gave:'
1052        % try6['boot'][:8])
1053      w('')</pre></td><td valign="top"><code>tI</code> and <code>tL</code> hold the launch times of the two control I processes and of the three part L processes, from <code>evd</code>. The sentence that opens the section prints the first 8 characters of the boot id.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1054      L.extend(table(['Visit', 'Launch times', 'Start state', 'Time since the first kernel log line of the boot',
1055                      'asmread, GB/s', 'oldread, GB/s', 'n per kernel'], [
1056          ['F72d12', hm(f72la['utc']), 'load %.2f at launch. Process list %.0f s before the launch: %s at %s %%CPU'
1057           % (f72la['load1'], (f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1]),
1058           dur((f72la['utc'] - try6['first_log_utc']).total_seconds()),
1059           sp(rng(F72a)), sp(rng(F72o)), nn(rng(F72a), boots=False)],
1060          ['part L', '%s to %s' % (hm(tL[0]), hm(tL[-1])), '%.0f s after part A (load %.2f to %.2f)'
1061           % (evd['T72L1']['gap_s'], min(evd[t]['load1'] for t in ('T72L1', 'T72L2', 'T72L3')), max(evd[t]['load1'] for t in ('T72L1', 'T72L2', 'T72L3'))),
1062           '%s to %s' % (dur((tL[0] - try6['first_log_utc']).total_seconds()), dur((tL[-1] - try6['first_log_utc']).total_seconds())),
1063           sp(rng(L72a)), sp(rng(L72o)), nn(rng(L72a), boots=False)],
1064          ['control I (%s)' % ADDED, '%s and %s' % (hm(tI[0]), hm(tI[1])),
1065           'idle (load %.2f and %.2f), %.0f s and %.0f s after 120-thread work. Process lists: at most %s %%CPU'
1066           % (evd['T72I1']['load1'], evd['T72I2']['load1'], evd['T72I1']['gap_s'], evd['T72I2']['gap_s'],
1067              max(x['env']['pcpu_max'] for x in D['X'] if x['part'] == 'I')),
1068           '%s and %s' % (dur((tI[0] - try6['first_log_utc']).total_seconds()), dur((tI[1] - try6['first_log_utc']).total_seconds())),
1069           sp(rng(I72a)), sp(rng(I72o)), nn(rng(I72a), boots=False)]]))</pre></td><td valign="top">Writes the table of the three visits, one row per visit. <code>f72la</code> is the launch line of the F72d12 process. <code>fenv</code> is the parsed env.txt of its folder (lines 38 and 39).<ul><li>Launch times and start state: from <code>f72la</code> and <code>fenv</code> for F72d12, from <code>evd</code> for part L and control I. The control I row also prints the highest %CPU value of its two process lists, from the env.txt entries of <code>D['X']</code>.</li><li>The part L row prints the lowest and the highest load at launch of its three processes. Its gap after part A is the gap of T72L1 alone, here and in lines 1168, 1338 and 1581. None of these lines reads the gaps of T72L2 and T72L3. In facts.json the three gaps are equal (5 s).</li><li>The F72d12 row prints the first entry of the process list in env.txt. <code>facts_data.py</code> describes this list as sorted by %CPU, highest first [Ref2].</li><li>Time since the first Linux kernel log line of the boot: launch time minus <code>try6['first_log_utc']</code>, printed by <code>dur</code>.</li><li><code>asmread, GB/s</code> and <code>oldread, GB/s</code>: the lowest to the highest <code>GBps</code> of the list, with 2 decimal places. No mean is taken.</li><li><code>n per kernel</code>: intervals / processes. The code counts the asmread list only.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1070      spread = av['hi'] - av['lo']
1071      ov = rng(F72o + L72o + I72o)
1072      w('- The three asmread ranges do not overlap each other.')
1073      need(av['lo'] == rng(F72a)['lo'] and av['hi'] == rng(L72a)['hi'], 'asmread: lowest value in F72d12, highest in part L')
1074      need(ov['lo'] == rng(L72o)['lo'] and ov['hi'] == rng(I72o)['hi'], 'oldread: lowest value in part L, highest in control I')
1075      w('- The lowest asmread value of the three visits is %s GB/s (F72d12). The highest is %s GB/s (part L). They are '
1076        '%s GB/s apart (%s %% of the lowest value), at one memory speed, inside one boot.'
1077        % (g(av['lo']), g(av['hi']), g(spread), pc(spread / av['lo'] * 100)))
1078      w('- The two visits that were launched at a load below 1.0 (F72d12 and control I) are at least %s GB/s apart.' % g(kIF['dist']))</pre></td><td valign="top"><ul><li><code>spread</code>: the highest minus the lowest asmread rate of the three visits, in GB/s. In the present sheet the two rates are 327.93 and 301.90 GB/s, and <code>spread</code> prints as 26.03 GB/s [Ref4].</li><li><code>ov</code>: the range of the oldread intervals of the three visits.</li><li>Line 1072 writes fixed words: the three asmread ranges do not overlap each other. The check in line 1048 tests them.</li><li>Line 1073: the build stops unless the lowest asmread rate belongs to F72d12 and the highest to part L. Line 1074: the same check for oldread, with the lowest rate in part L and the highest in control I.</li><li>The percent value of the bullet is <code>spread / av['lo'] * 100</code>. That is the spread as a percent of the lowest rate (8.6 % in the present sheet).</li><li><code>kIF['dist']</code>: the lowest control I rate minus the highest F72d12 rate (11.00 GB/s in the present sheet). The words "launched at a load below 1.0" of line 1078 are typed in the template. The check in line 898 tests them for control I. No check tests them for F72d12. In facts.json its load at launch is 0.34.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1079      envI = [(x['tag'], x['env']['pcpu_max'], os.path.join(x['folder'], 'env.txt')) for x in D['X'] if x['part'] == 'I']
1080      t_env = (fenv['start'] - try6['first_log_utc']).total_seconds()
1081      need(t_env &gt; 0 and fenv['top'][0][1] &gt; 10 and max(v[1] for v in envI) &lt; 1, 'process list: F72d12 busy, control I not')
1082      w('- F72d12 and control I differ in more than the time since boot. env.txt of F72d12 was written at %s, %.0f s after '
1083        'the first kernel log line of the boot and %.0f s before the launch. It lists %s at %s %%CPU and %s at %s %%CPU '
1084        '(lines %d and %d %s). env.txt of %s lists at most %s %%CPU %s. So F72d12 is an idle start only by the '
1085        'load-average rule of this sheet.'
1086        % (hm(fenv['start']), t_env, (f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1],
1087           fenv['top'][1][2], fenv['top'][1][1], fenv['top'][0][3], fenv['top'][1][3], ref(os.path.join(f72dir, 'env.txt')),
1088           ' and '.join(v[0] for v in envI), max(v[1] for v in envI), ' '.join(ref(v[2]) for v in envI)))</pre></td><td valign="top">No rate is used in these lines. They compare the process lists of F72d12 and of control I.<ul><li><code>envI</code>: tag, highest %CPU and path of env.txt for each control I process.</li><li><code>t_env</code>: the seconds from the first Linux kernel log line of the boot to the date line of env.txt of F72d12.</li><li>The build stops unless <code>t_env</code> is positive, the first entry of the F72d12 list has more than 10 %CPU, and every control I list stays below 1 %CPU.</li><li>The bullet prints the first two entries of the F72d12 list with their line numbers in env.txt, and the highest %CPU value of the control I lists.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1089      gt = [t for t in try6.get('gaps_top', []) if t[2] == fenv['top'][0][2]]
1090      need(len(gt) == 1 and 'gaps_uptime_utc' in try6, 'gaps.txt holds a later %CPU value of the same thread')
1091      t_gap = (try6['gaps_uptime_utc'] - try6['first_log_utc']).total_seconds()
1092      cpu1, cpu2 = fenv['top'][0][1] / 100 * t_env, gt[0][1] / 100 * t_gap
1093      f72end = D['rx']['F72d12']['launches']['a6456']['rc_utc']
1094      need(fenv['start'] &lt; f72la['utc'] &lt; f72end &lt; try6['gaps_uptime_utc'] and cpu2 &gt; cpu1,
1095           'the F72d12 process lies between the two readings of the thread')
1096      w('- Hypothesis (not tested): the thread %s was still busy during the first seconds of the F72d12 process. What '
1097        'fits: its %%CPU value was %s at %s and %s at %s (line %d of gaps.txt %s). With the assumption that the thread '
1098        'started at the first kernel log line (%s), these values mean about %.1f s of CPU time in the first %.0f s and '
1099        'about %.1f s in the first %.0f s (est.). That is about %.1f s of CPU time in the %.0f s between the two '
1100        'readings (est.). The F72d12 process ran inside this time, from %s to %s. Measurement that would confirm or '
1101        'reject it: a sample of the load of every CPU, once per second, in the first minutes after a boot.'
1102        % (fenv['top'][0][2], fenv['top'][0][1], hm(fenv['start']), gt[0][1], hm(try6['gaps_uptime_utc']), gt[0][3],
1103           ref(try6['gaps_path']), hm(try6['first_log_utc']), cpu1, t_env, cpu2, t_gap, cpu2 - cpu1,
1104           (try6['gaps_uptime_utc'] - fenv['start']).total_seconds(), hm(f72la['utc']), hm(f72end)))</pre></td><td valign="top">A hypothesis on the first entry of the F72d12 process list, a thread with a high %CPU value. No rate is used.<ul><li><code>gt</code>: the process-list lines of gaps.txt that hold the command name of that first entry. The build stops unless exactly one exists and gaps.txt holds an <code>uptime</code> line. That line gives the time of day at which gaps.txt was written [Ref2].</li><li><code>t_gap</code>: the seconds from the first Linux kernel log line to that time.</li><li><code>cpu1</code>, <code>cpu2</code>: %CPU / 100 x seconds since the first Linux kernel log line. Each is an estimate (est.) of the CPU time of the thread in seconds, at one of the two readings. It assumes that the thread started at that log line.</li><li><code>f72end</code>: the time of the rc line of the F72d12 process.</li><li>The build stops unless the F72d12 process ran between the two readings and <code>cpu2</code> is above <code>cpu1</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1105      w('- The lowest oldread value of the three visits is %s GB/s (part L). The highest is %s GB/s (control I). They '
1106        'are %s GB/s apart (%s %% of the lowest value).' % (g(ov['lo']), g(ov['hi']), g(ov['hi'] - ov['lo']), pc((ov['hi'] - ov['lo']) / ov['lo'] * 100)))
1107      b12 = rng(P12a)
1108      w('- For comparison, the 8000 MT/s rows L-1 to L-4 span %s GB/s (%s GB/s wide, %s), also inside one boot.'
1109        % (sp(b12), g(b12['hi'] - b12['lo']), nn(b12)))</pre></td><td valign="top"><ul><li>The oldread bullet prints <code>ov['hi'] - ov['lo']</code> in GB/s, and the same value as a percent of the lowest oldread rate. Present values: 7.59 GB/s and 1.6 % [Ref4].</li><li><code>b12</code>: the range of <code>P12a</code>, asmread at position 1 of the 8000 MT/s rows L-1 to L-4. The bullet prints the range, its width <code>hi - lo</code> in GB/s, and n.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1110      lo_all = sel(recs, dataset=set(BWX), kernel={'read', 'asmread'})
1111      bxa = rng(lo_all)
1112      w('- The first runner bwx (other binary) gave %s GB/s for its load-only kernels read and asmread at 8000 MT/s in '
1113        'the processes with the tags common-6000-* (%s, %d folders of 2026-11-13 and 2026-11-14, same boot).'
1114        % (sp(bxa), nn(bxa), len(BWX)))
1115      w('- Rule V1 point 5: the 12-module data at 8000 MT/s reach %s GB/s (bw_new read, rows A-1 and A-2) and %s GB/s '
1116        '(bw_new asmread, rows A-1 and A-2). In the rows of runner bwx used in this sheet (B7a, B7b, C3a, C3b, tags '
1117        'common-6000-*) they reach %s GB/s (read) and %s GB/s (asmread).'
1118        % (g(rng(sel(recs, dataset={'A-1', 'A-2'}, binary='bw_new', kernel='read'))['hi']),
1119           g(rng(sel(recs, dataset={'A-1', 'A-2'}, binary='bw_new', kernel='asmread'))['hi']),
1120           g(rng(sel(recs, dataset=set(BWX), kernel='read'))['hi']), g(rng(sel(recs, dataset=set(BWX), kernel='asmread'))['hi'])))</pre></td><td valign="top"><ul><li><code>lo_all</code>: every record of the runner bwx rows B7a, B7b, C3a and C3b whose kernel is read or asmread. The selection has no position condition. <code>bxa</code> is the range of this list (192 intervals of 24 processes in the present sheet [Ref4]).</li><li>The bullet for rule V1 point 5 prints four highest rates at 8000 MT/s. Two are bw_new read and bw_new asmread over rows A-1 and A-2 together. Two are read and asmread over the four runner bwx rows.</li><li>Each of the four is <code>rng(...)['hi']</code>, the largest <code>GBps</code> of the selected records.</li><li>Rule V1 point 5 forbids the use of 280 to 310 GB/s as the 8000 MT/s range of the new kernel [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1121      b5rev = sel(recs, dataset={'B5a-rev', 'B5b-rev'})
1122      top_r = max(sel(b5rev, kernel='read'), key=lambda r: r['GBps'])
1123      top_a = max(sel(b5rev, kernel='asmread'), key=lambda r: r['GBps'])
1124      b5read = rng(sel(recs, dataset={'B5a', 'B5b', 'B5a-rev', 'B5b-rev'}, kernel='read'))
1125      gro, gra = rng(CG['read after oldread'][0]), rng(CG['read after asmread'][0])
1126      in_ = lambda v, a: a['lo'] &lt;= v &lt;= a['hi']
1127      need(top_r['GBps'] &gt; rng(sel(recs, dataset=set(BWX), kernel='read'))['hi']
1128           and top_a['GBps'] &gt; rng(sel(recs, dataset=set(BWX), kernel='asmread'))['hi'],
1129           'the reverse-order B5 processes hold higher values than the common-6000-* rows')
1130      need(in_(top_r['GBps'], gro) and in_(top_r['GBps'], gra) and in_(top_a['GBps'], rng(L72a)),
1131           'the highest B5 values lie inside the 7200 MT/s ranges')</pre></td><td valign="top"><ul><li><code>b5rev</code>: every record of rows B5a-rev and B5b-rev. <code>top_r</code> and <code>top_a</code> are the single records with the highest rate of kernel read and of kernel asmread among them.</li><li><code>b5read</code>: the range of kernel read over the four B5 rows, forward and reverse.</li><li><code>gro</code>, <code>gra</code>: the 7200 MT/s ranges of the part C groups read after oldread and read after asmread.</li><li><code>in_(v, a)</code>: true when the value <code>v</code> lies inside the range <code>a</code>, ends included.</li><li>First check: <code>top_r</code> and <code>top_a</code> are above the highest read rate and the highest asmread rate of rows B7a to C3b.</li><li>Second check: <code>top_r</code> lies inside both part C ranges, and <code>top_a</code> lies inside the asmread range of part L. The build stops when a check fails.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1132      where = lambda r: 'process %s of %s, position %d, directly after %s, I row in line %d' % (r['tag'], r['folder'], r['pos'], r['kernel_before'], r['line'])
1133      w('- Higher values of runner bwx exist outside these rows. The reverse-order processes of the two B5 folders '
1134        '(tags b5-rev-*, %d processes, one interval per kernel, common stop, %s) reach %s GB/s for read (%s) and %s GB/s '
1135        'for asmread (%s) %s. read_sparse and asmread2 are other kernels of runner bwx. Rule F2 point 4 quotes the range '
1136        'of read over the %d processes of the two B5 folders: %s GB/s %s.'
1137        % (rng(b5rev)['procs'], secs(b5rev), g(top_r['GBps']), where(top_r), g(top_a['GBps']), where(top_a),
1138           src([top_r, top_a]), b5read['procs'], sp(b5read), ref(rules)))
1139      w('- The read value of %s GB/s lies inside the 7200 MT/s ranges of both read groups of part C (%s and %s GB/s). The '
1140        'asmread value of %s GB/s lies inside the 7200 MT/s range of part L (%s GB/s). Both values come from another '
1141        'binary and another kernel order. They are not a like-for-like baseline.'
1142        % (g(top_r['GBps']), sp(gro), sp(gra), g(top_a['GBps']), sp(rng(L72a))))
1143      w('')</pre></td><td valign="top"><ul><li><code>where</code> describes one record as text: process tag, folder, position, kernel before, and the line of its I row in the csv file.</li><li>The first bullet prints <code>top_r</code> and <code>top_a</code> with their source. It also prints the number of reverse-order processes (<code>rng(b5rev)['procs']</code>) and their interval length (<code>secs</code>).</li><li>The same bullet prints the range <code>b5read</code> and its number of processes. Rule F2 point 4 quotes this range.</li><li>The second bullet prints the part C ranges and the part L range that hold the two values. It states that these values are not a like-for-like baseline.</li><li>No new rate is computed.</li><li>Two parts of the first bullet are typed in the template: the words "one interval per kernel, common stop" and the sentence on read_sparse and asmread2. No check tests them. In facts.json each of the 4 processes has one record for each of the kernels oldread, read and asmread. The field <code>stop</code> of every such record is <code>common</code>. The fields <code>kernel_before</code> of <code>top_r</code> and <code>top_a</code> are read_sparse and asmread2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1144      w('What follows for Q2:')
1145      w('')
1146      aL, aF, aP = rng(L72a), rng(F72a), rng(P12a)
1147      dist = dict(near_boot=aL['lo'] - aF['hi'], near_pool=cLa['dist'], med_boot=aL['med'] - aF['med'],
1148                  med_pool=aL['med'] - aP['med'], far_boot=aL['hi'] - aF['lo'], far_pool=aL['hi'] - aP['lo'])
1149      need(abs(dist['far_boot'] - spread) &lt; 1e-9, 'the farthest ends inside the boot are the spread of the three visits')
1150      need(dist['near_boot'] &gt; dist['near_pool'] and dist['med_boot'] &gt; dist['med_pool'] and dist['far_boot'] &lt; dist['far_pool'],
1151           'part L to F72d12 against part L to the 8000 MT/s pool: larger for nearest ends and medians, smaller for farthest ends')
1152      c['dist'] = dist
1153      w('- The same kind of distance is compared on both sides. Nearest ends: part L lies %s GB/s above the 8000 MT/s pool and %s GB/s above '
1154        'F72d12, the earlier visit of the same boot. Medians: %s GB/s and %s GB/s. Farthest ends: %s GB/s and %s GB/s.'
1155        % (g(dist['near_pool']), g(dist['near_boot']), g(dist['med_pool']), g(dist['med_boot']), g(dist['far_pool']), g(dist['far_boot'])))
1156      w('- So the move between two visits inside the 7200 MT/s boot is larger than the distance of part L to the '
1157        '8000 MT/s pool for the nearest ends and for the medians. It is smaller for the farthest ends.')</pre></td><td valign="top">Six distances of asmread in GB/s. <code>aL</code>, <code>aF</code> and <code>aP</code> are the ranges of part L, of F72d12 and of the 8000 MT/s pool L-1 to L-4.<ul><li><code>near_boot</code>: the lowest rate of part L minus the highest rate of F72d12. <code>near_pool</code>: <code>cLa['dist']</code>, the lowest rate of part L minus the highest rate of the pool.</li><li><code>med_boot</code>, <code>med_pool</code>: the median of part L minus the median of F72d12, and minus the median of the pool.</li><li><code>far_boot</code>, <code>far_pool</code>: the highest rate of part L minus the lowest rate of F72d12, and minus the lowest rate of the pool.</li><li>Present values, pool first and boot second: 12.48 and 18.87 GB/s (nearest ends), 17.61 and 20.54 GB/s (medians), 39.38 and 26.03 GB/s (farthest ends) [Ref4].</li><li>The build stops unless <code>far_boot</code> equals <code>spread</code>. It also stops unless the boot distance is the larger one for the nearest ends and for the medians, and the smaller one for the farthest ends.</li><li><code>c['dist']</code> keeps the six values for section 4.9 (line 1303).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1158      need(cFa['b']['lo'] &lt;= cFa['a']['lo'] and cFa['a']['hi'] &lt;= cFa['b']['hi'], 'F72d12 asmread inside the range of the pool L-1 to L-4')
1159      w('- One of the three 7200 MT/s visits (F72d12) lies inside the range of the 8000 MT/s pool L-1 to L-4. Against '
1160        'L-1 alone it is %s GB/s higher. The other two visits (part L and control I) lie above every row of the pool, '
1161        'by %s and %s GB/s at the nearest ends.' % (g(kF1['dist']), g(cLa['dist']), g(cIa['dist'])))</pre></td><td valign="top">The build stops unless both ends of the F72d12 asmread range lie inside the range of the pool L-1 to L-4 (<code>cFa</code>). The bullet prints three nearest-end distances in GB/s: F72d12 above L-1 alone (<code>kF1</code>, set in line 890), and part L and control I above the pool (<code>cLa</code>, <code>cIa</code>). Earlier checks test that each of the three distances is above 0 without overlap: line 891 (<code>kF1</code>), one check in <code>facts_text.py</code> (<code>cLa</code>) [Ref1] and line 889 (<code>cIa</code>).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1162      hp_, ep_ = c['hw']['possible']
1163      need(hp_['dataset'] == 'L-1' and ep_['offset_s'] + 1 &lt;= 2, 'L-1: records in the first 2 s of the process')
1164      w('- The comparison of part L with L-1 changes four things at once: the memory speed, the boot, the start state '
1165        '(%.0f s after part A against a start at load %.2f), and the hardware error records. Row L-1 has 2 corrected '
1166        'records in the first 2 s of its process (est., section 4.1). For the rerun the records are not known. A fifth thing '
1167        'is not known: the firmware settings of the boot of the rerun were not read (section 1.5, point 13).'
1168        % (evd['T72L1']['gap_s'], l1la['load1']))</pre></td><td valign="top"><ul><li><code>hp_</code>, <code>ep_</code>: the process and the first hardware error record of the kind <code>possible</code> from section 4.1 (lines 295 and 304).</li><li><code>offset_s</code>: the journal time of the record minus the time of the launch line, in seconds. Both times are whole seconds. So the record lies at most <code>offset_s + 1</code> seconds after the process start [Ref3].</li><li>The build stops unless the process belongs to row L-1 and <code>offset_s + 1</code> is at most 2 s.</li><li>The bullet lists what differs between part L and row L-1. It uses no rate. Its count "2 corrected records" is typed in the template. Lines 245 and 293 test it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1169      w('- Control I (%s) reduces the difference of the start '
1170        'state against L-1. The data do not show that it removes it. Control I is like L-1 by the 1-minute load rule '
1171        'only (%s against %.2f, all below 1.0). It was launched %s s after a 120-thread process, at 5-minute load '
1172        'averages of %s %s. L-1 was launched at load averages of %.2f / %.2f / %.2f (1 / 5 / 15 min) %s. So control I '
1173        'does not rule out an effect of the earlier 120-thread work (hypothesis H1 in section 6, not tested).'
1174        % (ADDED, ' and '.join('%.2f' % la['load1'] for la in Ila), l1la['load1'],
1175           ' s and '.join('%.0f' % v for v in Igap), ' and '.join('%.2f' % la['load5'] for la in Ila), Iref,
1176           l1la['load1'], l1la['load5'], l1la['load15'], ref(os.path.join(D['rx']['L-1']['folder'], 'launches.txt'))))
1177      w('- The 8000 MT/s pool also holds %d processes that started after 120-thread work (section 4.2, view by start '
1178        'state). Part L lies %s GB/s above their asmread range too.' % (c['byst']['Ba']['procs'], g(c['byst']['asm_near'])))</pre></td><td valign="top">Two bullets on the start state. No rate is computed.<ul><li>Control I against L-1: the load averages of the launch lines (<code>Ila</code> for control I, <code>l1la</code> for L-1), and the seconds since the last 120-thread process (<code>Igap</code>). The three names were set in lines 894 to 896. The check in line 898 tests the words "all below 1.0".</li><li>The pool L-1 to L-4: <code>c['byst']['Ba']['procs']</code> is the number of pool processes that started after 120-thread work. <code>c['byst']['asm_near']</code> is the distance in GB/s by which part L lies above their asmread range. Both come from the view by start state (line 563). The check in line 560 tests that part L lies above this range without overlap.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1179      w('- So the rerun shows that the load-only loop ran above the 8000 MT/s intervals of the same round (rows A-1 and '
1180        'A-2) in session 1 of part A. It ran above every bwx12 row of the fixed 8000 MT/s list (L-1 to L-4) in part L, '
1181        'in control I (%s) and in the group "asmread after oldread" of part C (comparison by decision (r) in section 2). '
1182        'It does not show that the memory speed is the cause.' % ADDED)
1183      xa1 = next(x for x in pa3 if (x['binary'], x['kernel'], x['round']) == ('bw_new', 'asmread', 1))
1184      top2 = max(sel(recs, dataset='A-2', binary='bw_new', kernel='asmread'), key=lambda r: r['GBps'])
1185      low1 = [r for r in xa1['s1'] if r['GBps'] &lt; top2['GBps']]
1186      need(top2['round'] == 2 and low1, 'part A: round-1 intervals of session 1 below the highest round-2 interval of A-2')
1187      w('- The statement for part A holds inside the same round only. %d intervals of bw_new asmread of session 1, round 1 '
1188        '(%s GB/s, lines %s %s) lie below the highest round-2 interval of row A-2 (%s GB/s, line %d %s).'
1189        % (len(low1), ' and '.join(g(r['GBps']) for r in low1), ' and '.join(str(r['line']) for r in low1), src(low1),
1190           g(top2['GBps']), top2['line'], src([top2])))</pre></td><td valign="top"><ul><li>Lines 1179 to 1182: a summary bullet. Its words are fixed: the code inserts no measured value. Checks test its statements: line 748 (part A), one check in <code>facts_text.py</code> (part L) [Ref1], line 889 (control I) and line 1351 (part C).</li><li><code>xa1</code>: the cell of <code>pa3</code> for bw_new asmread, round 1. <code>xa1['s1']</code> holds its 3 intervals of session 1.</li><li><code>top2</code>: the interval with the highest rate of bw_new asmread in row A-2. Both rounds are searched.</li><li><code>low1</code>: the intervals of <code>xa1['s1']</code> whose rate is below the rate of <code>top2</code>.</li><li>The build stops unless <code>top2</code> is a round-2 interval and <code>low1</code> is not empty.</li><li>The bullet prints the count, the rates and the csv line numbers. In the present sheet 2 intervals (321.15 and 321.79 GB/s) lie below 321.87 GB/s [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1191      x1 = sel(recs, dataset='X1d10', kernel='asmread')
1192      x1b = sel(recs, dataset='X1d10b', kernel='asmread')
1193      apart = (med(x1b) / med(x1) - 1) * 100
1194      o10 = rng(sel(recs, dataset={'X1d10', 'X1d10b', 'BASEd10'}, kernel='oldread'))
1195      ins = ('Insufficient data: whether a difference of the new read kernel comes from the memory speed. Speed and boot '
1196             'changed together. Two boots at equal settings (10 modules, one process each) gave asmread %s / %s and '
1197             '%s / %s GB/s, %s %% apart (medians). Runs in several boots per speed would resolve it (needs reboots, not '
1198             'part of this task).' % (g(x1[0]['GBps']), g(x1[1]['GBps']), g(x1b[0]['GBps']), g(x1b[1]['GBps']), pc(apart)))
1199      V['insufficient_data'].append(ins)
1200      w('- Text required by rule V1 point 3: %s %s' % (ins, src(x1 + x1b)))</pre></td><td valign="top">The text that rule V1 point 3 requires, from the 10-module rows.<ul><li><code>x1</code>, <code>x1b</code>: the asmread records of rows X1d10 and X1d10b. In facts.json each row is one process with 2 asmread intervals.</li><li><code>apart</code>: (median of <code>x1b</code> / median of <code>x1</code> - 1) x 100, in percent. The median of 2 values is their mean. Present value: 9.4 % [Ref4].</li><li><code>o10</code>: the range of oldread over the three 10-module rows X1d10, X1d10b and BASEd10.</li><li><code>ins</code>: the text of the rule with the 4 asmread rates and <code>apart</code>. In line 288 the name <code>ins</code> was a list. From here it is this text.</li><li>The text is appended to <code>V['insufficient_data']</code> and written as a bullet. Line 1554 later replaces that list.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1201      w('- Text of rule V1 point 4 for old read: three 10-module boots gave old read %s GB/s (%s %% wide, %s). So the '
1202        'boot alone moved old read by less than 1 %% there. %s'
1203        % (sp(o10), pc(width_pct(o10)), nn(o10), src(sel(recs, dataset={'X1d10', 'X1d10b', 'BASEd10'}, kernel='oldread'))))
1204      need(width_pct(o10) &lt; 1, '10-module old read range below 1 %')
1205      o10x = {d: rng(sel(recs, dataset=d, kernel='oldread')) for d in ('X1d10', 'X1d10b', 'BASEd10')}
1206      o10p = rng(sel(recs, dataset={'X1d10', 'X1d10b'}, kernel='oldread'))
1207      w('- Limit of this text: the three boots did not differ by the boot alone. X1d10 and X1d10b ran with the same '
1208        'changed TXREQ firmware settings (old read %s and %s GB/s). BASEd10 ran with the original settings (%s GB/s) '
1209        '%s. So the words "the boot alone" rest on the pair X1d10 and X1d10b (%s GB/s, %s %% wide, %s).'
1210        % (sp(o10x['X1d10']), sp(o10x['X1d10b']), sp(o10x['BASEd10']), ref(fd.DIMM_REPORT), sp(o10p), pc(width_pct(o10p)), nn(o10p)))
1211      w('')
1212</pre></td><td valign="top"><ul><li>The bullet for rule V1 point 4 prints the oldread range <code>o10</code>, its width and n. The width is <code>width_pct(o10)</code> = (highest - lowest) / lowest x 100. Present values: 359.56 to 362.15 GB/s, 0.7 % wide, 6 intervals of 3 processes in 3 boots [Ref4].</li><li>The build stops unless this width is below 1 %.</li><li><code>o10x</code>: the oldread range of each 10-module row alone. <code>o10p</code>: the range of X1d10 and X1d10b together.</li><li>The last bullet states a limit: only X1d10 and X1d10b ran with the same firmware settings. It prints the width of <code>o10p</code> (0.5 % in the present sheet). The settings of each row are typed in the template. The check in line 198 tests only that the DIMM report holds the oldread rates of the three rows and two phrases on changed TXREQ settings.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.7: sums per mesh</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1213      # ---- 4.7 per mesh
1214      w('### 4.7 Sums per mesh (looked at after the numbers were seen, not part of the fixed rules)')
1215      w('')
1216      w('The table gives the lowest and highest sum per mesh over the intervals of each row. Mesh 0 holds 64 threads, '
1217        'mesh 1 holds 56.')
1218      w('')
1219</pre></td><td valign="top">Writes the heading and the first lines of section 4.7. The heading says that this view was looked at after the numbers were seen. It is not part of the rules that were fixed before the run.<ul><li>The thread counts of the text (64 on mesh 0, 56 on mesh 1) are typed in the template.</li><li>Two integrity checks of <code>build_facts.py</code> test that every bwx record is an interval with 64 threads on CPUs 0-63 and 56 threads on CPUs 64-119 [Ref3]. Line 1461 stops the build when a check fails.</li></ul></td></tr>
<tr><td colspan="2"><b>Helper <code>mrow</code>: one table row of mesh sums</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1220      def mrow(label, rs):
1221          m0, m1 = rng(rs, 'mesh0_GBps'), rng(rs, 'mesh1_GBps')
1222          return [label, '%d MT/s' % rs[0]['speed_MTps'], len(rs), sp(m0), sp(m1), src(rs)]</pre></td><td valign="top">Returns one table row for a list of bwx records <code>rs</code>.<ul><li><code>mesh0_GBps</code> of a record: the sum of bytes / elapsed_s / 1e9 over the threads on CPUs 0-63 of one interval, in GB/s. <code>mesh1_GBps</code>: the same sum over the threads on CPUs 64 and higher [Ref2].</li><li><code>m0</code>, <code>m1</code>: the lowest and the highest value of each field over the list. No mean is taken.</li><li>The row holds the label, the memory speed of the first record, the number of intervals, both ranges and the source files.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1223      sets_o = [('part L', L72o), ('part C', C72o), ('control I (%s)' % ADDED, I72o), ('F72d12', F72o), ('pool L-1 to L-4 (bwx12)', P12o),
1224                ('R0, R0b (bwx11)', pool(BW11, 'oldread', 0)), ('B7a, B7b, C3a, C3b (bwx), positions 0 and 7', sel(recs, dataset=set(BWX), kernel='oldread'))]
1225      sets_a = [('part L, asmread', L72a),
1226                ('part C, read after oldread', CG['read after oldread'][0]), ('part C, read after asmread', CG['read after asmread'][0]),
1227                ('part C, asmread after read', CG['asmread after read'][0]),
1228                ('part C, asmread as first interval of the process', CG['asmread first'][0]),
1229                ('part C, asmread after oldread', CG['asmread after oldread'][0]),
1230                ('control I (%s), asmread' % ADDED, I72a), ('F72d12, asmread', F72a),
1231                ('pool L-1 to L-4 (bwx12), asmread at position 1', P12a),
1232                ('R0, R0b (bwx11), asmread at position 1', pool(BW11, 'asmread', 1)),
1233                ('B7a, B7b, C3a, C3b (bwx), read at positions 1 and 6 and asmread at positions 2 and 5', lo_all)]
1234      need({(r['kernel'], r['pos']) for r in lo_all} == {('read', 1), ('read', 6), ('asmread', 2), ('asmread', 5)},
1235           'positions of the load-only kernels of runner bwx')</pre></td><td valign="top">The lists that the two tables show, each as a pair of label and records.<ul><li><code>sets_o</code> holds 7 oldread lists: part L, part C, control I, F72d12, <code>P12o</code> (pool L-1 to L-4, position 0), rows R0 and R0b at position 0, and every oldread record of the runner bwx rows.</li><li><code>sets_a</code> holds 11 lists of load-only kernels. Eight are at 7200 MT/s: asmread of part L, the five part C groups of <code>CG</code>, and asmread of control I and of F72d12.</li><li>Three lists of <code>sets_a</code> are at 8000 MT/s: <code>P12a</code> (pool L-1 to L-4, position 1), rows R0 and R0b at position 1, and <code>lo_all</code> (line 1110).</li><li>The two runner bwx selections have no position condition. Their labels name the positions. For <code>lo_all</code> the build stops unless its records are exactly read at positions 1 and 6 and asmread at positions 2 and 5.</li><li>For oldread these lines do not check the label "positions 0 and 7". In facts.json the oldread records of these rows are at positions 0 and 7 only.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1236      w('- The sums of every interval are in facts.json (fields mesh0_GBps and mesh1_GBps). The tables of sections 3.2 '
1237        'and 3.3 print them for parts L and C, control I and F72d12 (columns "m0 + m1").')
1238      w('- The part C rows are shown next to 8000 MT/s rows here. Rule F2 points 2 and 3 would not do this (decision '
1239        '(r) in section 2). The bullets under the tables give the oldread result with part C and without it.')
1240      w('')
1241      w('oldread:')
1242      w('')
1243      L.extend(table(['Row', 'Memory speed', 'Intervals', 'Mesh 0, GB/s', 'Mesh 1, GB/s', 'Source'], [mrow(a, b) for a, b in sets_o]))
1244      w('Load-only kernels. Part C has one row per group (rule V2). No bwx12 row at 8000 MT/s holds the kernel read:')
1245      w('')
1246      L.extend(table(['Row', 'Memory speed', 'Intervals', 'Mesh 0, GB/s', 'Mesh 1, GB/s', 'Source'], [mrow(a, b) for a, b in sets_a]))</pre></td><td valign="top">Writes two notes and the two tables.<ul><li>Each table row comes from <code>mrow</code>: the lowest to the highest mesh 0 sum and mesh 1 sum over the intervals of one list.</li><li>The first table holds the 7 oldread lists of <code>sets_o</code>. The second table holds the 11 load-only lists of <code>sets_a</code>.</li><li>Line 1244 says in fixed words that no bwx12 row at 8000 MT/s holds the kernel read. No check tests these words. In facts.json no bwx12 record at 8000 MT/s has the kernel <code>read</code>. The kernel sequences (<code>seq=</code>) in the header lines of the csv files that <code>build_facts.py</code> reads for these rows name no kernel <code>read</code> either.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1247      o72 = L72o + C72o + I72o + F72o
1248      o80 = P12o + pool(BW11, 'oldread', 0)
1249      oxx = sel(recs, dataset=set(BWX), kernel='oldread')
1250      m0_72, m1_72 = rng(o72, 'mesh0_GBps'), rng(o72, 'mesh1_GBps')
1251      m0_80, m1_80 = rng(o80, 'mesh0_GBps'), rng(o80, 'mesh1_GBps')
1252      m0_x, m1_x = rng(oxx, 'mesh0_GBps'), rng(oxx, 'mesh1_GBps')
1253      need(m1_72['lo'] &gt; m1_80['hi'] and m0_72['hi'] &lt; m0_80['lo'], 'oldread mesh split differs against bwx12 and bwx11 rows')
1254      o72n = L72o + I72o + F72o                   # the same without part C (rule F2 points 2 and 3)
1255      m0_n, m1_n = rng(o72n, 'mesh0_GBps'), rng(o72n, 'mesh1_GBps')
1256      need(m1_n['lo'] &gt; m1_80['hi'] and m0_n['hi'] &lt; m0_80['lo'], 'oldread mesh split differs without part C too')
1257      o72p = L72o + F72o                          # the same without part C and without control I
1258      m0_p, m1_p = rng(o72p, 'mesh0_GBps'), rng(o72p, 'mesh1_GBps')
1259      need(m1_p['lo'] &gt; m1_80['hi'] and m0_p['hi'] &lt; m0_80['lo'], 'oldread mesh split differs without part C and control I too')
1260      c['mesh'] = dict(n_all=len(o72), n_noC=len(o72n), n_noCI=len(o72p))</pre></td><td valign="top">The checks for the oldread statement of this section.<ul><li><code>o72</code>: every oldread interval at 7200 MT/s, from part L, part C, control I and F72d12 (20 intervals in the present sheet).</li><li><code>o80</code>: oldread at position 0 of the bwx12 rows L-1 to L-4 and of the bwx11 rows R0 and R0b (18 intervals). <code>oxx</code>: oldread of the runner bwx rows (96 intervals) [Ref4].</li><li>For each list <code>rng</code> gives the lowest and the highest <code>mesh0_GBps</code> and <code>mesh1_GBps</code>.</li><li>The build stops unless two conditions hold. The lowest mesh 1 sum of <code>o72</code> is above the highest mesh 1 sum of <code>o80</code>. The highest mesh 0 sum of <code>o72</code> is below the lowest mesh 0 sum of <code>o80</code>.</li><li>The same check runs for <code>o72n</code> (without part C) and for <code>o72p</code> (without part C and without control I).</li><li><code>c['mesh']</code> keeps the three interval counts for section 6 (line 1503).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1261      F72_WHAT = 'the earlier run of the same boot'
1262      w('- oldread, all %d intervals at 7200 MT/s (F72d12, parts L and C, and control I, which was %s): mesh 1 gave '
1263        '%s GB/s and mesh 0 gave %s GB/s %s.' % (len(o72), ADDED, sp(m1_72), sp(m0_72), src(o72)))
1264      w('- oldread, the %d intervals of bwx12 and bwx11 at 8000 MT/s: mesh 1 gave %s GB/s and mesh 0 gave %s GB/s %s. '
1265        'Against these rows mesh 1 is higher and mesh 0 is lower in every 7200 MT/s interval.'
1266        % (len(o80), sp(m1_80), sp(m0_80), src(o80)))
1267      w('- The same without part C (rule F2 points 2 and 3, decision (r) in section 2): the %d oldread intervals of '
1268        'part L, of control I (%s) and of F72d12, %s, gave %s GB/s on mesh 1 and %s GB/s on mesh 0. Against the same '
1269        '8000 MT/s rows mesh 1 is higher and mesh 0 is lower in every one of these intervals too.'
1270        % (len(o72n), ADDED, F72_WHAT, sp(m1_n), sp(m0_n)))
1271      w('- The same without part C and without control I: the %d oldread intervals of part L and of F72d12 gave '
1272        '%s GB/s on mesh 1 and %s GB/s on mesh 0. Against the same 8000 MT/s rows mesh 1 is higher and mesh 0 is '
1273        'lower in every one of these intervals too. So the result does not rest on control I.'
1274        % (len(o72p), sp(m1_p), sp(m0_p)))</pre></td><td valign="top">Writes four bullets with the mesh 1 range and the mesh 0 range of <code>o72</code>, <code>o80</code>, <code>o72n</code> and <code>o72p</code>, each with its interval count. <code>F72_WHAT</code> is a fixed label for F72d12. No new value is computed.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1275      need(overlap(m1_x, m1_72) and overlap(m0_x, m0_72) and overlap(m1_x, m1_n) and m0_n['hi'] &lt; m0_x['lo'],
1276           'runner bwx rows: both mesh ranges overlap with part C; without part C mesh 1 overlaps and mesh 0 lies below')
1277      w('- This does not hold in full against the rows of the first runner bwx at 8000 MT/s. There mesh 1 gave %s GB/s '
1278        'and mesh 0 gave %s GB/s (%d intervals) %s. With part C, both 7200 MT/s ranges overlap these ranges. Without '
1279        'part C, the mesh 1 ranges overlap, and the mesh 0 range at 7200 MT/s ends %s GB/s below the mesh 0 range of '
1280        'runner bwx.' % (sp(m1_x), sp(m0_x), len(oxx), src(oxx), g(m0_x['lo'] - m0_n['hi'])))
1281      w('- So the split between the meshes also moved between visits at 8000 MT/s. Insufficient data: whether the '
1282        'memory speed changes the split. Runs in several boots per speed would resolve it.')
1283      w('')
1284</pre></td><td valign="top"><ul><li>The check against the runner bwx rows (<code>m0_x</code>, <code>m1_x</code>). The build stops unless four conditions hold.</li><li>With part C: the mesh 1 range and the mesh 0 range at 7200 MT/s both overlap the ranges of runner bwx.</li><li>Without part C: the mesh 1 ranges overlap, and the highest mesh 0 sum at 7200 MT/s lies below the lowest mesh 0 sum of runner bwx.</li><li>The bullet prints that last distance, <code>m0_x['lo'] - m0_n['hi']</code> (0.26 GB/s in the present sheet [Ref4]).</li><li>The last bullet has fixed words. It says that the data do not show whether the memory speed changes the split.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.8: record-only table of the test loops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1285      # ---- 4.8 record only
1286      w('### 4.8 Record only: read_nop96, read_nop256, read_1pl')
1287      w('')
1288      w('Total in GB/s, lowest to highest interval. No statement is made from this table.')
1289      w('')
1290      rows = []
1291      for k in ('read_nop96', 'read_nop256', 'read_1pl'):
1292          row = [k]
1293          for d in ('rerun-L', 'control-I', 'F72d12', 'L-1'):
1294              rs = sel(recs, dataset=d, kernel=k)
1295              row.append('%s (n=%d)' % (sp(rng(rs)), len(rs)))
1296          rows.append(row)
1297      L.extend(table(['Kernel', 'Part L, 7200 MT/s', 'Control I (%s), 7200 MT/s' % ADDED, 'F72d12, 7200 MT/s, same boot',
1298                      'L-1 (w120-R8), 8000 MT/s'], rows))
1299</pre></td><td valign="top">One table row per test loop (read_nop96, read_nop256, read_1pl). Four data columns, one per value of <code>dataset</code>: part L (<code>rerun-L</code>), control I, F72d12 and L-1.<ul><li><code>sel</code> takes every record with that kernel and that <code>dataset</code>.</li><li>A cell prints the lowest to the highest <code>GBps</code> and the number of intervals.</li><li>The sheet makes no statement from this table.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 4.9: verdict for Q2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1300      # ---- 4.9 verdict
1301      w('### 4.9 Verdict for Q2')
1302      w('')
1303      by, dist = c['byst'], c['dist']
1304      oth = c['byst_other']
1305      pcv, kF1, kI1 = c['partC_view'], c['kF1'], c['kI1']
1306      # limit of the visit F72d12 (section 4.6): its process list shows a busy kernel thread shortly before the launch
1307      need(fenv['top'][0][1] &gt; 10, 'process list of F72d12 shows a busy process')
1308      c['f72_limit'] = ('F72d12 is an idle start only by the load-average rule of this sheet: its process list, written '
1309                        '%.0f s before the launch, shows %s at %s %%CPU (section 4.6).'
1310                        % ((f72la['utc'] - fenv['start']).total_seconds(), fenv['top'][0][2], fenv['top'][0][1]))
1311      side = lambda k, n72: '7200 MT/s: %s GB/s, n = %s. 8000 MT/s: %s GB/s, n = %s' % (sp(k['a']), n72, sp(k['b']), nn(k['b']))</pre></td><td valign="top"><ul><li>Reads results of earlier sections from <code>c</code>. <code>by</code>: the start-state groups of the pool L-1 to L-4. <code>dist</code>: the six distances of line 1147. <code>oth</code>: the other-binary processes that started after 120-thread work. <code>pcv</code>: part C in the view by start state.</li><li><code>kF1</code>, <code>kI1</code>: asmread of F72d12 and of control I against L-1 alone.</li><li>The build stops unless the first entry of the F72d12 process list has more than 10 %CPU.</li><li><code>c['f72_limit']</code>: one sentence on the limit of F72d12 as an idle start. The verdict for the new read kernel (line 1376) and section 0 quote it [Ref1].</li><li><code>side(k, n72)</code>: prints both sides of a comparison <code>k</code>. These are the 7200 MT/s range with <code>n72</code> (its n as text), and the 8000 MT/s range with its n.</li></ul></td></tr>
<tr><td colspan="2"><b>Verdict text for the old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1312      V['q2_old_read'] = (
1313          'Old read kernel. Part A (bw_old read): "%s" (%s). The test cannot exclude a difference of about %s %% (est. '
1314          'from one boot), which is the width of the 8000 MT/s range. Part C (oldread): "%s" (%s). There the test '
1315          'cannot exclude a difference of about %s %% (est. from one boot). %s Part L (oldread): "%s" (%s). Part L is '
1316          'lower by %s GB/s at the nearest ends (%s %% '
1317          'of the lower end of the 8000 MT/s range, %s GB/s) and by %s GB/s between the medians (%s %% of the 8000 MT/s '
1318          'median, %s GB/s). Two other rows of the same line in the same 7200 MT/s boot overlap the 8000 MT/s range. '
1319          'F72d12 (%d process at %s UTC, before the rerun, load %.2f at launch) gave %s GB/s. Control I (%d processes, '
1320          'idle start, %s, %s) gave %s GB/s. So against the whole pool L-1 to L-4, only the range of part L, which '
1321          'started %.0f s after part A, lies below the 8000 MT/s range among the bwx12 runs. A view added after the '
1322          'numbers were seen splits the '
1323          '8000 MT/s pool by start state: the %d bwx12 processes of the pool that started %.0f s to %.0f s after a '
1324          '120-thread bwx12 process gave '
1325          '%s GB/s (%s), the highest oldread values of the pool. Part L is %s GB/s below them. Part C started %.0f s '
1326          'after 120-thread work too. It is %s GB/s below them at the nearest ends, and its %d position-matched '
1327          'intervals (cfwd, position 0) are %s GB/s below them. Limit: these %d processes are not all 8000 MT/s '
1328          'processes with that kind of start state. Against the other-binary processes that started after 120-thread '
1329          'work, part C overlaps (bwx11: %s GB/s, %s. Runner bwx, position 0: %s GB/s, %s). Part L lies below every '
1330          'oldread interval at 8000 MT/s with 12 modules that this sheet holds (the lowest is %s GB/s, row %s, process '
1331          '%s). So the 8000 MT/s rows do '
1332          'not show that a start after 120-thread work lowers the old read kernel. The data do not show that the boot '
1333          'or the memory speed is the cause: each memory speed has one boot. Insufficient data: why part L was lower. %s'</pre></td><td valign="top">The template of <code>V['q2_old_read']</code>, the Q2 verdict for the old read kernel. Its statements, in order:<ul><li>Part A (bw_old read) and part C (oldread): the wording of the range test, both ranges, and the width of the 8000 MT/s range in percent.</li><li>Part L (oldread): the wording, both ranges, and the distance of part L below the pool, at the nearest ends and between the medians.</li><li>F72d12 and control I: their oldread ranges. The text says that they overlap the 8000 MT/s range.</li><li>The view by start state: the pool processes that started after 120-thread work, and the distances of part L and of part C below them.</li><li>The other-binary processes, the lowest oldread interval at 8000 MT/s, and the measurement that would resolve the open question (<code>H1_MEAS</code>).</li><li>Earlier checks test fixed words of this text. <code>facts_text.py</code> stops the build before it calls <code>section4</code> unless parts A and C, control I and F72d12 overlap their 8000 MT/s range, and part L lies below the pool without overlap [Ref1]. The checks in lines 557 to 608 test the words on the view by start state, on the other-binary processes and on the lowest oldread interval at 8000 MT/s.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1334          % (cAo['wording'], side(cAo, nns(A72o)), pc(cAo['width']), cCo['wording'], side(cCo, nns(C72o)),
1335             pc(cCo['width']), F2_NOTE, cLo['wording'], side(cLo, nns(L72o)), g(c['oldL']['near']), pc(c['oldL']['near_pct']),
1336             g(cLo['b']['lo']), g(c['oldL']['mid']), pc(c['oldL']['mid_pct']), g(cLo['b']['med']), cFo['a']['procs'],
1337             hm(f72la['utc'])[:5], f72la['load1'], sp(cFo['a']), cIo['a']['procs'], ADDED, NOT_PLAN, sp(cIo['a']),
1338             evd['T72L1']['gap_s'], by['Bo']['procs'], by['gaps'][0], by['gaps'][-1], sp(by['Bo']), nn(by['Bo']),
1339             g(by['near']), pcv['gap'], g(pcv['near']), pcv['cf0']['n'], g(pcv['near_cf0']), by['Bo']['procs'],
1340             sp(oth['b11']), nn(oth['b11'], boots=False), sp(oth['bx0']), nn(oth['bx0'], boots=False),
1341             g(oth['low_o']['GBps']), oth['low_o']['dataset'], oth['low_o']['tag'], H1_MEAS))</pre></td><td valign="top">The values for the template, in the order of the text. This statement computes no new rate and no new distance. <code>nns</code> and <code>nn</code> form the n texts.<ul><li><code>cAo</code>: <code>A72o</code> against <code>A80o</code>. <code>cCo</code>: <code>C72o</code> against <code>P12o</code>. <code>cLo</code>: <code>L72o</code> against <code>P12o</code>. The three comparisons come from <code>facts_text.py</code> [Ref1].</li><li><code>c['oldL']</code> (line 490). <code>near</code>: the lowest rate of the pool minus the highest rate of part L, in GB/s. <code>near_pct</code>: <code>near</code> as a percent of that lowest pool rate. <code>mid</code>: the pool median minus the part L median. <code>mid_pct</code>: <code>mid</code> as a percent of the pool median.</li><li>Present values: 1.24 GB/s (0.3 %) at the nearest ends and 6.27 GB/s (1.3 %) between the medians [Ref4].</li><li><code>by['Bo']</code>, <code>by['gaps']</code>, <code>by['near']</code>: the oldread range of the pool processes that started after 120-thread work, their gaps in seconds, and the distance of part L below them (line 563).</li><li><code>pcv</code>, <code>oth</code>: part C in that view (line 580) and the other-binary rows (line 609).</li><li>Rates print with 2 decimal places (<code>g</code>, <code>sp</code>). Percent values print with 1 decimal place (<code>pc</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1342      # new read kernel, part A: the two rounds are kept apart (rule V3)
1343      need([x['round'] for x in newread] == [1, 2] and all(len(x['above']) == 3 for x in newread),
1344           'bw_new read of session 1: one cell per round, every interval above the 8000 MT/s range of its round')
1345      rounds = ' '.join('Round %d: %s to %s GB/s above the upper end of the round-%d range (%s GB/s).'
1346                        % (x['round'], g(min(x['above'])), g(max(x['above'])), x['round'], g(x['b80']['hi'])) for x in newread)
1347      n72r = {nns(x['s1']) for x in newread}
1348      n80r = {nn(x['b80']) for x in newread}
1349      need(len(n72r) == 1 and len(n80r) == 1, 'bw_new read: the same n in both rounds')
1350      kAw = compare(Aao, c['hw']['P12a_wo'])
1351      need(not kAw['overlap'] and kAw['dist'] == kAao['dist'] &gt; 0,
1352           'part C, asmread after oldread: above the pool without the interval with error records too')
1353      allv = rng(F72a + L72a + I72a)</pre></td><td valign="top">Checks and values for the verdict of the new read kernel.<ul><li>The build stops unless <code>newread</code> holds round 1 and round 2, and all 3 session-1 intervals of each round lie above the 8000 MT/s range of that round.</li><li><code>rounds</code>: per round, the smallest and the largest value of <code>above</code>. One value of <code>above</code> is the rate of a session-1 interval minus <code>b80['hi']</code>. <code>b80['hi']</code> is the highest rate of rows A-1 and A-2 in the same round [Ref1].</li><li><code>n72r</code>, <code>n80r</code>: n of each round as text. The build stops unless both rounds give the same text.</li><li><code>kAw</code>: the part C group asmread after oldread (<code>Aao</code>, line 988) against the pool L-1 to L-4 without the interval that holds the error records.</li><li>The build stops unless three conditions hold. The two ranges do not overlap. The distance <code>kAw['dist']</code> is above 0 (the part C group is the higher range). The distance equals the distance to the whole pool (<code>kAao</code>, line 1015).</li><li><code>allv</code>: now the range of asmread over the three visits. In line 1045 the name was a list.</li></ul></td></tr>
<tr><td colspan="2"><b>Verdict text for the new read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1354      V['q2_new_read'] = (
1355          'New read kernel. Part A (bw_new read, session 1): outside the 8000 MT/s range of the same round in both '
1356          'rounds. %s n per round at 7200 MT/s: %s. n per round at 8000 MT/s: %s. The pass counts '
1357          'differ, so part A gives no exact size. '</pre></td><td valign="top">The template of <code>V['q2_new_read']</code>, the Q2 verdict for the new read kernel. Lines 1355 to 1357 hold its first statement, on part A (bw_new read, session 1).<ul><li>The statement: outside the 8000 MT/s range of the same round in both rounds, with the text <code>rounds</code> and n of each round. No percent is given.</li><li>The next sentence is typed in the template: "The pass counts differ, so part A gives no exact size." Lines 762 to 770 print the pass counts in section 4.3.</li><li>No check compares the pass counts of the 7200 MT/s intervals with those of the 8000 MT/s intervals. In facts.json the 6 session-1 intervals of bw_new read have 664 passes each. Of the 12 bw_new read intervals of rows A-1 and A-2, 9 have 600 passes. The other 3 have 603, 663 and 664 passes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1358          'Part L (asmread, the same loop, used in place of the new read kernel): "%s" (%s). Part C, asmread directly '
1359          'after oldread (crev, round 1, position 0): "%s" (%s). Part C is higher by %s GB/s at the nearest ends. This '
1360          'baseline matches in the kernel that ran directly before. It does not match in the position: asmread is at '
1361          'position 1 in rows L-1 to L-4. %s Two corrected hardware error records fall inside the 8000 MT/s interval '
1362          'with the lowest asmread value (%s GB/s). Without this interval the 8000 MT/s range is %s GB/s (%s), and no '
1363          'wording changes (sections 4.1 and 4.4). Part C '
1364          '(kernel read): %s. The same line in the same 7200 MT/s boot gave asmread %s GB/s at %s UTC (F72d12, before '
1365          'the rerun, n = %s). That is inside the range of the 8000 MT/s pool L-1 to L-4. Against L-1 alone it is '
1366          '%s GB/s higher. %s Control I (idle start, %s, %s) gave asmread %s GB/s (n = %s). That is also above every bwx12 '
1367          'row of the fixed 8000 MT/s list, by %s GB/s at the nearest ends (%s GB/s against L-1 alone). The three '
1368          'visits of the boot span %s GB/s. Inside '
1369          'this one boot at one memory speed, part L lies %s GB/s above F72d12 at the nearest ends and %s GB/s between '
1370          'the medians. That is more than the distance of part L to the 8000 MT/s range (%s GB/s at the nearest ends, '
1371          '%s GB/s between the medians). Between the farthest ends the order is the opposite (%s GB/s inside the boot '
1372          'against %s GB/s to the 8000 MT/s range). %s'</pre></td><td valign="top">The rest of the template. Its statements, in order:<ul><li>Part L (asmread) and the part C group asmread after oldread: the wording of the range test and both ranges.</li><li>The interval with the hardware error records, and the 8000 MT/s range without it.</li><li>Part C, kernel read: the fixed text <code>NO_READ</code>.</li><li>F72d12: its asmread range, the words that it lies inside the range of the pool, and its distance above L-1 alone. Control I: its asmread range, and its distances above the pool and above L-1 alone.</li><li>The span of the three visits (<code>allv</code>), the six distances of <code>dist</code>, and the text <code>ins</code> of rule V1 point 3.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1373          % (rounds, sorted(n72r)[0], sorted(n80r)[0], cLa['wording'], side(cLa, nns(L72a)),
1374             kAao['wording'], side(kAao, nns(Aao)), g(kAao['dist']), F2_NOTE,
1375             g(c['hw']['low_a']['GBps']), sp(c['hw']['wo']), nn(c['hw']['wo']),
1376             NO_READ, sp(cFa['a']), hm(f72la['utc'])[:5], nns(F72a), g(kF1['dist']), c['f72_limit'], ADDED, NOT_PLAN, sp(cIa['a']),
1377             nns(I72a), g(cIa['dist']), g(kI1['dist']), sp(allv), g(dist['near_boot']),
1378             g(dist['med_boot']), g(dist['near_pool']), g(dist['med_pool']), g(dist['far_boot']), g(dist['far_pool']), ins))</pre></td><td valign="top">The values for the template, in the order of the text. No new rate and no new distance is computed. <code>nns</code> and <code>nn</code> form the n texts.<ul><li><code>cLa</code>: <code>L72a</code> against <code>P12a</code>. <code>kAao</code>: <code>Aao</code> against <code>P12a</code>. Each gives its wording, both ranges and <code>dist</code>.</li><li><code>c['hw']['low_a']</code>: the asmread interval of the pool with the lowest rate. <code>c['hw']['wo']</code>: the range of the pool without it (line 916).</li><li><code>cFa['a']</code>, <code>cIa['a']</code>: the asmread ranges of F72d12 and of control I.</li><li><code>kF1['dist']</code>, <code>kI1['dist']</code>: the distances of these two rows above L-1 alone. <code>cIa['dist']</code>: the distance of control I above the pool.</li><li><code>allv</code> and the six values of <code>dist</code> from section 4.6.</li><li>Earlier checks stop the build unless the fixed words hold: part L above the pool [Ref1], control I above the pool (line 889), F72d12 and control I above L-1 alone (line 891), F72d12 inside the pool (line 1158), the part C group above the pool (line 1351). More checks: the positions of asmread in the part C group and in rows L-1 to L-4 (line 999), the order of the distances (line 1150), and no change of a wording without the interval with error records (lines 918 and 1351). The count "Two" of the error records is typed in the template. Lines 245, 291 and 298 test the sentence that holds it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1379      V['q2'] = V['q2_old_read'] + ' ' + V['q2_new_read']
1380      w('**Verdict, old read kernel.** ' + V['q2_old_read'])
1381      w('')
1382      w('**Verdict, new read kernel.** ' + V['q2_new_read'])
1383      w('')</pre></td><td valign="top"><code>V['q2']</code> is the two verdict texts joined with one space. Both texts are written to the sheet as two paragraphs with bold labels.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1384      V['same_boot'] = dict(kernel='asmread, position 1, like.spec line', boot=try6['boot'], speed_MTps=try6['speed_MTps'],
1385                            F72d12=[rng(F72a)['lo'], rng(F72a)['hi']], part_L=[rng(L72a)['lo'], rng(L72a)['hi']],
1386                            control_I=[rng(I72a)['lo'], rng(I72a)['hi']], control_I_note='%s, %s' % (ADDED, NOT_PLAN),
1387                            spread_GBps=round(spread, 3), pool_8000_L1_to_L4=[b12['lo'], b12['hi']],
1388                            distance_part_L_to_pool_GBps=round(cLa['dist'], 3),
1389                            part_L_above_F72d12_GBps=dict(nearest_ends=dist['near_boot'], medians=dist['med_boot'],
1390                                                          farthest_ends=dist['far_boot']),
1391                            part_L_above_pool_8000_GBps=dict(nearest_ends=dist['near_pool'], medians=dist['med_pool'],
1392                                                             farthest_ends=dist['far_pool']),
1393                            F72d12_process_list=dict(file=fd.rel(os.path.join(f72dir, 'env.txt')), written=hm(fenv['start']),
1394                                                     launch=hm(f72la['utc']), load1_at_launch=f72la['load1'],
1395                                                     top=[dict(user=t[0], pcpu=t[1], command=t[2], line=t[3]) for t in fenv['top']]))</pre></td><td valign="top"><code>V['same_boot']</code>: the values of section 4.6 as an object for facts.json. It starts with a kernel label, the boot id and the memory speed from <code>try6</code>.<ul><li><code>F72d12</code>, <code>part_L</code>, <code>control_I</code>: the lowest and the highest asmread rate of each visit. <code>pool_8000_L1_to_L4</code>: the same for <code>P12a</code>.</li><li><code>spread_GBps</code>: <code>spread</code>, rounded to 3 decimal places. <code>distance_part_L_to_pool_GBps</code>: <code>cLa['dist']</code>, rounded in the same way.</li><li><code>part_L_above_F72d12_GBps</code>, <code>part_L_above_pool_8000_GBps</code>: the three boot distances and the three pool distances of <code>dist</code>.</li><li><code>F72d12_process_list</code>: the path and the time of env.txt, the launch time, the load at launch, and the entries of the process list.</li><li><code>build_facts.py</code> rounds every decimal number of <code>V</code> to 3 places when it writes facts.json [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1396      V['pool_8000_by_start_state'] = dict(
1397          note='view added after the numbers were seen, not part of the rules fixed before the run',
1398          below_load_1=dict(processes=by['names'](by['idle']), oldread=[by['Io']['lo'], by['Io']['hi']],
1399                            asmread=[by['Ia']['lo'], by['Ia']['hi']], n_intervals=by['Io']['n'], n_processes=by['Io']['procs']),
1400          after_120_thread_work=dict(processes=by['names'](by['busy']), gap_s=[by['gaps'][0], by['gaps'][-1]],
1401                                     load1=[by['loads_busy'][0], by['loads_busy'][-1]], oldread=[by['Bo']['lo'], by['Bo']['hi']],
1402                                     asmread=[by['Ba']['lo'], by['Ba']['hi']], n_intervals=by['Bo']['n'],
1403                                     n_processes=by['Bo']['procs']),
1404          part_L_oldread_below_second_group_GBps=by['near'], part_L_asmread_above_second_group_GBps=by['asm_near'],
1405          part_C=dict(start_state='every process started %.0f s after a 120-thread bwx12 process of the rerun (%s)'
1406                                  % (pcv['gap'], ', '.join(pcv['prev'])), load1=[pcv['loads'][0], pcv['loads'][-1]],
1407                      oldread=[pcv['all']['lo'], pcv['all']['hi']], n_intervals=pcv['all']['n'],
1408                      n_processes=pcv['all']['procs'], oldread_below_second_group_GBps=pcv['near'],
1409                      oldread_cfwd_position_0=[pcv['cf0']['lo'], pcv['cf0']['hi']],
1410                      n_intervals_cfwd_position_0=pcv['cf0']['n'],
1411                      oldread_cfwd_position_0_below_second_group_GBps=pcv['near_cf0'],
1412                      overlaps_group_below_load_1=True,
1413                      limit='"second group" is the group after_120_thread_work: bwx12 processes of the pool L-1 to L-4 '
1414                            'only. Against the other-binary processes with that kind of start state '
1415                            '(other_binary_after_120_thread_work) oldread of part C overlaps',
1416                      overlaps_other_binary_after_120_thread_work=True),</pre></td><td valign="top"><code>V['pool_8000_by_start_state']</code>: the view by start state of section 4.2 as an object for facts.json. No new value is computed.<ul><li><code>below_load_1</code>, <code>after_120_thread_work</code>: the two groups of the pool L-1 to L-4. Each holds its processes, the lowest and the highest oldread and asmread rate, and the numbers of intervals and processes. These two numbers come from the oldread list.</li><li><code>part_L_oldread_below_second_group_GBps</code>, <code>part_L_asmread_above_second_group_GBps</code>: <code>by['near']</code> and <code>by['asm_near']</code>.</li><li><code>part_C</code>: the start state, the loads, the oldread range and the counts of all part C intervals. Then the oldread range and the interval count of the cfwd intervals at position 0. Each of the two ranges has its distance below the second group.</li><li>The two <code>overlaps_...</code> flags are the constant <code>True</code>. The checks in lines 577 and 606 stop the build before this point when an overlap is missing.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1417          other_binary_after_120_thread_work=dict(
1418              note='8000 MT/s processes of other binaries that started after a 120-thread process of the same binary. '
1419                   'They are not part of the pool L-1 to L-4. oldread at position 0',
1420              bwx11=dict(processes=', '.join('%s %s' % b['key'] for b in oth['busy11']),
1421                         gap_s=sorted({b['gap'] for b in oth['busy11']}),
1422                         load1=[min(b['load'] for b in oth['busy11']), max(b['load'] for b in oth['busy11'])],
1423                         oldread=[oth['b11']['lo'], oth['b11']['hi']], n_intervals=oth['b11']['n'],
1424                         n_processes=oth['b11']['procs'], part_C_oldread_overlaps=True),
1425              runner_bwx=dict(rows=', '.join(BWX), load1=oth['bx0_load'],
1426                              oldread=[oth['bx0']['lo'], oth['bx0']['hi']], n_intervals=oth['bx0']['n'],
1427                              n_processes=oth['bx0']['procs'], part_C_oldread_overlaps=True)),
1428          part_L_below_every_oldread_interval_8000_12_modules=dict(
1429              part_L_highest_GBps=by['L_hi'], lowest_8000_GBps=oth['low_o']['GBps'], lowest_8000_dataset=oth['low_o']['dataset'],
1430              lowest_8000_process=oth['low_o']['tag'], n_intervals_8000=oth['n_allo']))</pre></td><td valign="top"><ul><li><code>other_binary_after_120_thread_work</code>: the 8000 MT/s processes of bwx11 and of runner bwx that started after a 120-thread process. Each entry holds processes or rows, gaps or loads, the oldread range at position 0 and the counts.</li><li>The flag <code>part_C_oldread_overlaps</code> is the constant <code>True</code>. The check in line 606 stops the build before this point when the overlap is missing.</li><li><code>part_L_below_every_oldread_interval_8000_12_modules</code>: the highest oldread rate of part L, and the lowest oldread rate of all 8000 MT/s records with 12 modules. It also holds the row and the process of that lowest record, and the number of such intervals (lines 604 to 611).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1431      V['part_A_thread_rates'] = [dict(kernel='%s %s' % (t['x']['binary'], t['x']['kernel']), round=t['x']['round'],
1432                                       nearest_ends_by_120_x_avg_GBps_est=round(t['est'], 1),
1433                                       nearest_ends_by_aggregate_GBps=round(t['agg'], 2)) for t in c['thr']]
1434</pre></td><td valign="top"><code>V['part_A_thread_rates']</code>: one entry per cell <code>t</code> of <code>c['thr']</code> from section 4.3 (line 869). Both values are in GB/s.<ul><li><code>t['est']</code>: 120 x (the lowest <code>per_thread_avg_GBps</code> of the session-1 intervals minus the highest <code>per_thread_avg_GBps</code> of rows A-1 and A-2 in the same round). It is an estimate (est.) of the nearest-end distance. It is rounded to 1 decimal place.</li><li><code>t['agg']</code>: the smallest value of <code>above</code> of the cell (line 830). That is the lowest session-1 rate above the 8000 MT/s range of the round, minus the highest rate of that range, by the column <code>aggregate_GBps</code>. It is rounded to 2 decimal places.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 5: record-only table of part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1435      # =============================================================================== 5
1436      w('## 5. Record only: write, copy, asmwrite, asmcopy of part A')
1437      w('')
1438      w('- No statement is made from these rows (rule V3). FINDINGS.md section F1 shows that the whole-pass stop rule '
1439        'at %s moves the write totals %s.' % (secs(sel(recs, dataset='rerun-A')), ref(os.path.join(W15, 'FINDINGS.md'))))
1440      w('- A cell shows n: lowest / median / highest rate in GB/s. The copy kernels count read plus written bytes.')
1441      w('')</pre></td><td valign="top">Writes the heading and two notes.<ul><li>The interval length in the first note comes from <code>secs</code> over all part A records of the rerun (0.5 s in the present sheet [Ref4]).</li><li>For a part A record the field <code>min_ms</code> is the constant 500 (in ms) that <code>build_facts.py</code> sets. It is not read from the csv file. An integrity check of <code>build_facts.py</code> tests that the part A script ra.sh starts the binary with the options <code>--reps 3 --min-ms 500</code> [Ref3].</li><li>The notes say that no statement is made from these rows. They also say that the copy kernels count read plus written bytes. This file does not compute that count. <code>build_facts.py</code> stops unless the header line that the binary prints for each copy and asmcopy process of part A and of rows A-1 to A-3 holds the words <code>copy counts read+write bytes</code> [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1442      rows = []
1443      for k in ('write', 'copy', 'asmwrite', 'asmcopy'):
1444          for b in ('bw_old', 'bw_new'):
1445              row = [k, b]
1446              for cond in (dict(dataset='A-1'), dict(dataset='rerun-A', session=1), dict(dataset='rerun-A', session=2),
1447                           dict(dataset='rerun-A', session=3)):
1448                  rs = sel(recs, binary=b, kernel=k, **cond)
1449                  a = rng(rs)
1450                  row.append('%d: %s / %s / %s' % (a['n'], g(a['lo']), g(a['med']), g(a['hi'])))
1451              rows.append(row)
1452      L.extend(table(['Kernel', 'Binary', '2026-11-13 (A-1), 8000 MT/s', 'Session 1, 7200 MT/s', 'Session 2, 7200 MT/s',
1453                      'Session 3, 7200 MT/s'], rows))
1454</pre></td><td valign="top">One table row per kernel (write, copy, asmwrite, asmcopy) and binary (bw_old, bw_new). Four data columns: row A-1, and sessions 1, 2 and 3 of part A of the rerun.<ul><li><code>sel</code> takes every record of that binary and kernel in the row or session. Both rounds go into one cell.</li><li>A cell prints n, then the lowest, the median and the highest <code>GBps</code>, with 2 decimal places.</li><li>In facts.json every cell has n = 6: 3 intervals of each of the 2 rounds.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 6: established, not established, hypotheses</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1455      # =============================================================================== 6
1456      w('## 6. What is established, what is not, and hypotheses')
1457      w('')
1458      w('### Established')
1459      w('')
1460      nck = len(D['checks'])
1461      need(all(k['ok'] for k in D['checks']), 'all integrity checks pass')</pre></td><td valign="top">Writes the heading. <code>nck</code> is the number of integrity checks in <code>D['checks']</code>. The build stops unless every check has a true <code>ok</code> field.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1462      r2 = 0
1463      cells = 0
1464      for s_ in (1, 2, 3):
1465          for b, k in (('bw_new', 'read'), ('bw_old', 'asmread'), ('bw_new', 'asmread')):
1466              a1_, a2_ = (sel(recs, dataset='rerun-A', session=s_, round=rd, binary=b, kernel=k) for rd in (1, 2))
1467              cells += 1
1468              r2 += rng(a2_)['lo'] &gt; rng(a1_)['hi']</pre></td><td valign="top">Counts in how many load-only cells of part A round 2 lies above round 1.<ul><li>A cell is one session (1, 2 or 3) and one of bw_new read, bw_old asmread and bw_new asmread. That gives 9 cells.</li><li><code>a1_</code>: the records of the cell in round 1. <code>a2_</code>: the records in round 2. In facts.json each list is one process with 3 intervals.</li><li><code>r2</code> increases by 1 when the lowest rate of round 2 is above the highest rate of round 1. Then the two ranges do not overlap.</li><li>In the present sheet <code>r2</code> is 8 of 9 cells [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1469      est = [
1470          'The rerun ran in boot %s with 12 memory modules (MemTotal %d kB in every state line). The same boot was '
1471          'recorded with 12 modules at 7200 MT/s at %s (section 1.2).' % (try6['boot'][:8], try6['memtotal_kB'], hm(try6['utc'])),
1472          'The run is complete: all %d integrity checks pass (section 1.4).' % nck,
1473          'Q1: the new read kernel is below the old read kernel in every pair of parts A and C. asmread is below the '
1474          'old read kernel in every pair of parts L and C (section 3.4).',
1475          'The size of the drop is not one value. Part L (asmread): %s. Part C: read after oldread %s, read after '
1476          'asmread %s, asmread after read %s, asmread as first interval %s, asmread after oldread %s. Control I (%s): '
1477          '%s. F72d12, the earlier run of the same boot: %s (section 3.4).'
1478          % (pcr(c['dl']), pcr(CG['read after oldread'][1]), pcr(CG['read after asmread'][1]), pcr(CG['asmread after read'][1]),
1479             pcr(CG['asmread first'][1]), pcr(CG['asmread after oldread'][1]), ADDED, pcr(c['di']), pcr(c['df'])),</pre></td><td valign="top"><code>est</code> is the list of the established points. Items 1 to 4:<ul><li>Item 1: the boot id, MemTotal and the time of the 12-module reading, from <code>try6</code>. Its words "in every state line" are typed in the template. The integrity checks <code>boot</code> and <code>memtotal</code> of <code>build_facts.py</code> compare the boot id and MemTotal of every state line with try6.txt [Ref3]. Item 2: the number of checks.</li><li>Item 3: Q1 in fixed words. <code>facts_text.py</code> checks it before it calls <code>section4</code>: the build stops there unless every pair has a drop above 0 % [Ref1].</li><li>Item 4: the size of the Q1 drop. A drop is (1 - rate of the load-only kernel / rate of oldread) x 100. Both intervals come from the same process and round [Ref1].</li><li><code>pcr</code> prints the lowest and the highest drop of a list, with 1 decimal place. When both round to the same text, it prints one value. <code>c['dl']</code>, <code>c['di']</code> and <code>c['df']</code> hold the asmread drops of part L, of control I and of F72d12. <code>CG[...][1]</code> holds the drops of one part C group.</li><li>Present values: 29.2 % to 30.5 % in part L, and 35.4 % in F72d12 [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1480          'Q2, old read kernel: against the whole 8000 MT/s pool (A-1 to A-3 for part A, L-1 to L-4 for the bwx12 '
1481          'rows) its range overlaps in part A, in part C, in control I (%s) and in F72d12. Only the range of part L '
1482          'lies below the pool, by %s GB/s at the nearest ends and by %s GB/s between the medians. In the view by start '
1483          'state (added after the numbers were seen), part C also lies below the %d bwx12 processes of the pool L-1 to '
1484          'L-4 that started after 120-thread work, by %s GB/s at the nearest ends. Against the other-binary processes '
1485          'with that kind of start state part C overlaps (section 4.2). The comparison of part C with 8000 MT/s '
1486          'follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.'
1487          % (ADDED, g(c['oldL']['near']), g(c['oldL']['mid']), by['Bo']['procs'], g(pcv['near'])),
1488          'Q2, load-only loop: in session 1 of part A it ran above the 8000 MT/s intervals of the same round (rows A-1 '
1489          'and A-2). In part L, in control I (%s) and in the group "asmread after oldread" of part C it ran above every '
1490          'bwx12 row of the fixed 8000 MT/s list, L-1 to L-4 (sections 4.3 to 4.5). The comparison of part C with '
1491          '8000 MT/s follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.' % ADDED,</pre></td><td valign="top">Items 5 and 6, the Q2 results.<ul><li>Item 5, old read kernel: prints <code>c['oldL']['near']</code> and <code>c['oldL']['mid']</code>. These are the distances of part L below the pool L-1 to L-4, at the nearest ends and between the medians.</li><li>Item 5 also prints the number of pool processes that started after 120-thread work, and <code>pcv['near']</code>, the distance of part C below them.</li><li>Item 6, load-only loop: fixed words with the label <code>ADDED</code>. No value is inserted.</li><li>Checks stop the build unless the data show what the two items state. Item 5: checks in <code>facts_text.py</code> (the overlaps, and part L below the pool) [Ref1], and lines 577 and 606 (part C). Item 6: line 748 (part A), one check in <code>facts_text.py</code> (part L) [Ref1], line 889 (control I) and line 1351 (part C).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1492          'In the one 7200 MT/s boot the load-only loop gave %s GB/s at %s and %s GB/s at %s to %s for the same '
1493          'argument line (section 4.6).' % (sp(rng(F72a)), hm(f72la['utc']), sp(rng(L72a)), hm(tL[0]), hm(tL[-1])),
1494          'In part A the second-round process of a load-only kernel is above the first-round process, without overlap, '
1495          'in %d of %d cells (3 sessions x bw_new read, bw_old asmread, bw_new asmread, see the table of section 3.1).' % (r2, cells),
1496          'Against the bwx12 and bwx11 rows at 8000 MT/s, oldread at 7200 MT/s read more on mesh 1 and less on mesh 0 '
1497          'in every interval. This holds with part C (%d intervals) and without part C (%d intervals of part L, of '
1498          'control I (%s) and of F72d12, the earlier run of the same boot). It also holds without part C and without '
1499          'control I (%d intervals of part L and of F72d12). This sheet shows part C next to 8000 MT/s rows by '
1500          'decision (r) in section 2. Rule F2 points '
1501          '2 and 3 would not do it. Against the rows of runner bwx the result does not hold in full: the mesh 1 ranges overlap, '
1502          'and the mesh 0 ranges overlap when part C is included (section 4.7, looked at after the numbers were seen).'
1503          % (c['mesh']['n_all'], c['mesh']['n_noC'], ADDED, c['mesh']['n_noCI']),</pre></td><td valign="top"><ul><li>Item 7: the asmread ranges of F72d12 and of part L, with their launch times.</li><li>Item 8: <code>r2</code> and <code>cells</code> from line 1462.</li><li>Item 9: the mesh result of section 4.7, with the three interval counts of <code>c['mesh']</code>.</li><li>Item 9 says in fixed words which mesh sums are higher, which are lower and which ranges overlap. The checks in lines 1253, 1256, 1259 and 1275 test these words.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1504          'The bwx12 row F72d12 ran in the boot of the rerun: its process lies between two readings of the same boot id '
1505          '(section 4.1).',
1506          'Hardware error records at 8000 MT/s: 2 corrected records fall inside the interval with the lowest asmread '
1507          'value of the pool L-1 to L-4, and 2 fall before or inside the first oldread interval of row L-1 (section '
1508          '4.1). No wording by rule V1 point 2 changes without the first of these intervals (section 4.4).',
1509      ]
1510      for i, t in enumerate(est, 1):
1511          w('%d. %s' % (i, t))
1512      w('')</pre></td><td valign="top">Items 10 and 11 have fixed words. The loop writes the items as a numbered list, 1 to 11.<ul><li>Item 10: line 219 stops the build unless the F72d12 process lies between two readings of the same boot id.</li><li>Item 11: the two counts of 2 records are typed in the template. Lines 245 and 291 to 302 test them and the two intervals. Lines 918 and 1351 test that no wording changes without the first interval.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 6: list of what is not established</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1513      w('### Not established')
1514      w('')
1515      hwx = c['hw']['cmp']
1516      sgn = lambda x: '0.00' if float(g(x)) == 0 else (g(x) if x &lt; 0 else '+' + g(x))      # a signed difference</pre></td><td valign="top"><code>hwx</code> is the result of the comparison of intervals with hardware error records (line 372). <code>sgn</code> prints a difference in GB/s with 2 decimal places and its sign. A value that rounds to zero prints as <code>0.00</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1517      notest = [
1518          ins,
1519          'Insufficient data: why the load-only loop differs between the three visits of the same boot (section 4.6). '
1520          'The measurements named under H1 and H2 would resolve it.',
1521          'Insufficient data: why old read was %s GB/s in part L and %s GB/s in control I (%s). The 8000 MT/s rows do '
1522          'not point to the start state: there the %d bwx12 processes that started after 120-thread work gave higher '
1523          'oldread values (%s GB/s, %s) than the %d processes that started at a load below 1.0 (%s GB/s, %s) (section '
1524          '4.2, view added after the numbers were seen). The measurement named under H1 would resolve it.'
1525          % (sp(rng(L72o)), sp(rng(I72o)), ADDED, by['Bo']['procs'], sp(by['Bo']), nn(by['Bo'], boots=False),
1526             by['Io']['procs'], sp(by['Io']), nn(by['Io'], boots=False)),
1527          NO_READ + '. A run of cfwd.spec and crev.spec at 8000 MT/s would resolve it (needs a change of the firmware '
1528          'setting and a reboot, so root and approval).',</pre></td><td valign="top"><code>notest</code> is the list of the points that are not established. Items 1 to 4:<ul><li>Item 1: the text <code>ins</code> of line 1195.</li><li>Item 2: fixed words on the three visits.</li><li>Item 3: the oldread ranges of part L and of control I. Then the oldread ranges and n of the two start-state groups of the pool (<code>by['Bo']</code>, <code>by['Io']</code>). The check in line 557 tests the words "gave higher oldread values".</li><li>Item 4: <code>NO_READ</code>, and the run that would resolve it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1529          'Insufficient data: whether hardware error records occurred during the rerun. A count of the "[Hardware Error]" '
1530          'lines of the kernel log would resolve it (needs root).',
1531          'Insufficient data: a direct reading of the memory speed during the rerun. `sudo dmidecode -t 17` would '
1532          'resolve it (needs root). The proof used here is the equal boot id.',
1533          'Insufficient data: whether the one-thread phase of 2026-11-13 changes the 120-thread rates (section 1.5).',
1534          'Insufficient data: whether the buffers of part A lay on 2 MiB pages. bandwidth.c does not record it. A run '
1535          'of the same kernels with bwx12 records it in "P" rows.',
1536          'Insufficient data: the applied memory speed in the boot of the 8000 MT/s baselines. That boot is over, so the '
1537          'reading cannot be taken any more. The firmware setting of that boot is on record (section 1.5, point 10).',
1538          'Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. The two '
1539          'TXREQ settings were set back before the 7200 MT/s reboot test, and the settings list saved after that is '
1540          'equal to the list of the baseline boot in its %d readable values. No list was saved in the boot of the '
1541          'rerun. A settings list saved in that boot would resolve it (needs root) (section 1.5, point 13).'
1542          % c['fw']['readable'],</pre></td><td valign="top">Items 5 to 10. Each names one thing that is not known. Items 5 to 9 have fixed words. Item 10 inserts one value: <code>c['fw']['readable']</code>, the number of readable values in the saved list of firmware settings [Ref1].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1543          'Insufficient data: whether a corrected hardware error record lowers the rate of an interval (hypothesis in '
1544          'section 4.1). The processes of rows L-1 to L-4, R0 and R0b hold %d intervals to which records can be '
1545          'assigned (all kernels and positions, view added after the numbers were seen). %d of them are more than '
1546          '%g GB/s below the same kernel at the same position in the other round of their process (%s GB/s). The other '
1547          '%d differ from it by less than %g GB/s (%s to %s GB/s). Without records the two rounds of the same processes '
1548          'differ by up to %s GB/s. This comparison is not a test. A run that stores the kernel log time of every '
1549          'record beside the interval times would resolve it (needs root).'
1550          % (hwx['n'], len(hwx['low']), hwx['lim'], hwx['lst']([g(-r['diff']) for r in reversed(hwx['low'])]),
1551             len(hwx['rest']), hwx['lim'], sgn(min(r['diff'] for r in hwx['rest'])),
1552             sgn(max(r['diff'] for r in hwx['rest'])), g(abs(hwx['cmax']['diff']))),
1553      ]</pre></td><td valign="top">Item 11, the comparison of intervals with hardware error records. <code>diff</code> is the rate of such an interval minus the rate of the same kernel at the same position in the other round of the same process.<ul><li><code>hwx['n']</code>: the number of intervals to which records can be assigned. <code>hwx['low']</code>: those with <code>diff</code> below -1.0 GB/s (<code>hwx['lim']</code> is 1.0 GB/s). <code>hwx['rest']</code>: the others. Line 359 stops the build unless every <code>diff</code> of <code>rest</code> is below 1.0 GB/s as an absolute value.</li><li>The text prints the <code>low</code> differences as positive numbers, smallest first. Then it prints the lowest and the highest <code>diff</code> of <code>rest</code> with their signs.</li><li><code>hwx['cmax']</code>: the position without records where the two rounds differ most. Its <code>diff</code> prints as an absolute value.</li><li>Present values: 8 intervals. 3 of them are 1.96, 3.69 and 10.07 GB/s lower. Without records the rounds differ by up to 6.24 GB/s [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1554      V['insufficient_data'] = notest
1555      for i, t in enumerate(notest, 1):
1556          w('%d. %s' % (i, t))
1557      w('')</pre></td><td valign="top"><code>V['insufficient_data']</code> is set to <code>notest</code>. Until this line the list held only the entry that line 1199 appended. The text <code>ins</code> stays in the list as item 1. The loop writes the items as a numbered list.</td></tr>
<tr><td colspan="2"><b>Section 6: hypotheses H1 to H5</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1558      w('### Hypotheses (not tested)')
1559      w('')
1560      r0 = {t: sel(recs, dataset='R0', tag=t, kernel='asmread') for t in ('p1', 'p2')}
1561      l2 = {t: sel(recs, dataset='L-2', tag=t, kernel='asmread', pos=1) for t in ('p1nop', 'p2add')}
1562      l2load = {t: D['rx']['L-2']['launches'][t]['load1'] for t in l2}
1563      need(rng(l2['p2add'])['hi'] &lt; rng(l2['p1nop'])['lo'] and l2load['p2add'] &gt; 1 &gt; l2load['p1nop'],
1564           'row L-2: asmread of p2add (after 120-thread work) below p1nop (load below 1.0)')</pre></td><td valign="top">Data for hypothesis H1 from two 8000 MT/s rows.<ul><li><code>r0</code>: the asmread records of the processes p1 and p2 of row R0 (bwx11). The selection has no position condition. For row R0, <code>build_facts.py</code> keeps only oldread at position 0 and asmread at position 1 as records [Ref3]. The csv files of p1 and p2 also hold asmread at position 10. These intervals are not used.</li><li><code>l2</code>: the asmread intervals at position 1 of the processes p1nop and p2add of row L-2. <code>l2load</code>: their loads at launch.</li><li>The build stops unless every asmread rate of p2add is below every asmread rate of p1nop.</li><li>It also stops unless p2add was launched at a load above 1 and p1nop at a load below 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1565      hyp = [
1566          'H1, start state. The rate of the load-only loop depends on the work that ran shortly before the launch. '
1567          'What fits: part L (launched %.0f s after part A) gave %s GB/s, and control I (idle start, %s, %s) gave '
1568          '%s GB/s. In part A '
1569          'the second round is above the first in %d of %d load-only cells. What does not fit: at 8000 MT/s process p2 '
1570          'of row R0 (other binary bwx11, load %.2f at launch) gave %s GB/s, below p1 (load %.2f) with %s GB/s. The '
1571          'bwx12 rows of the fixed list do not fit either (section 4.2, view by start state): the %d processes that started '
1572          '%.0f s to %.0f s after a 120-thread bwx12 process (%s, load %.2f to %.2f) gave asmread %s GB/s (%s), and the '
1573          '%d processes that started at a load below 1.0 (%s) gave %s GB/s (%s). The two ranges overlap. Inside row '
1574          'L-2, p2add (load %.2f) gave %s GB/s, below p1nop (load %.2f) with %s GB/s. For oldread the order is the '
1575          'opposite at 8000 MT/s: the same %d processes gave %s GB/s, above the %s GB/s of the %d processes at a load '
1576          'below 1.0. At 7200 MT/s oldread of part L (%s GB/s) was below control I (%s GB/s). Also, in part A the '
1577          'first-round process of bw_new read gave %s GB/s in session 1 (idle start), above session 2 (%s GB/s) and '
1578          'session 3 (%s GB/s), which started %.0f s after 120-thread work. Measurement that would confirm or reject '
1579          'it: the like.spec line, alternating between an idle start and a start directly after part A, at least 3 '
1580          'times each, in one boot.'</pre></td><td valign="top"><code>hyp</code> is the list of the five hypotheses. These lines are the template of H1 (start state). It names what fits, what does not fit, and the measurement that would confirm or reject the hypothesis. Lines 1581 to 1589 give the values for its placeholders.<ul><li>Checks test the words of this text that compare rates: lines 557 and 558 (the two start-state groups of the pool), line 1563 (row L-2) and line 1609 (part A).</li><li>oldread of part L below control I: two checks of <code>facts_text.py</code> together show it. Part L lies below the pool L-1 to L-4, and control I lies inside the range of that pool [Ref1].</li><li>No check tests the words "below p1" for row R0. In facts.json the asmread rates of p2 (296.02 and 296.22 GB/s) are below the rates of p1 (302.59 and 303.16 GB/s).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1581          % (evd['T72L1']['gap_s'], sp(rng(L72a)), ADDED, NOT_PLAN, sp(rng(I72a)), r2, cells, r0['p2'][0]['load1_at_launch'], sp(rng(r0['p2'])),
1582             r0['p1'][0]['load1_at_launch'], sp(rng(r0['p1'])),
1583             by['Ba']['procs'], by['gaps'][0], by['gaps'][-1], by['names'](by['busy']), by['loads_busy'][0], by['loads_busy'][-1],
1584             sp(by['Ba']), nn(by['Ba'], boots=False), by['Ia']['procs'], by['names'](by['idle']), sp(by['Ia']),
1585             nn(by['Ia'], boots=False), l2load['p2add'], ' and '.join(g(r['GBps']) for r in l2['p2add']), l2load['p1nop'],
1586             ' and '.join(g(r['GBps']) for r in l2['p1nop']), by['Bo']['procs'], sp(by['Bo']), sp(by['Io']), by['Io']['procs'],
1587             sp(rng(L72o)), sp(rng(I72o)),
1588             sp(rng(N['pa'][0]['new'])), sp(rng(N['pa'][2]['new'])),
1589             sp(rng(N['pa'][4]['new'])), evd['T72A2']['gap_s']),</pre></td><td valign="top">The values of H1, in the order of the text. The ranges of part L, of control I, of row R0 and of part A are formed here with <code>rng</code>. <code>sp</code> prints a range as the lowest to the highest <code>GBps</code>.<ul><li>Part L: the gap of T72L1 after part A, and the asmread range. Control I: the asmread range.</li><li><code>r2</code>, <code>cells</code>: the count of line 1462.</li><li>Row R0: the load at launch and the asmread range of p2 and of p1.</li><li>The two start-state groups of the pool (<code>by</code>): process counts, gaps, names, loads, asmread ranges and n. Then row L-2: the loads and the single asmread rates of p2add and of p1nop.</li><li>oldread: the ranges of the same two groups, of part L and of control I.</li><li>Part A: the bw_new read range of the round-1 process of sessions 1, 2 and 3 (<code>N['pa'][0]</code>, <code>[2]</code>, <code>[4]</code>), and the gap of T72A2 after 120-thread work. The text applies this one gap to sessions 2 and 3. These lines do not read the gap of T72A3. In facts.json that gap is also 5 s.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1590          'H2, time since boot. The rate of the load-only loop rises with the time since boot or with the work done '
1591          'since boot. What fits: F72d12 ran %s after the first kernel log line of the boot and gave the lowest values. '
1592          'The first process of the rerun started %s after that line. Limit: F72d12 also differs from control I (%s, %s) '
1593          'in its process list (%s at %s %%CPU, %.0f s before the launch, section 4.6). So the time since boot and the '
1594          'start phase of the machine are not separated. Measurement: repeat the idle-start line of '
1595          'control I some hours later in the same boot, and once directly after a reboot (a reboot needs approval).'
1596          % (dur((f72la['utc'] - try6['first_log_utc']).total_seconds()), dur((c['evd']['T72A1']['first'] - try6['first_log_utc']).total_seconds()),
1597             ADDED, NOT_PLAN, fenv['top'][0][2], fenv['top'][0][1], (f72la['utc'] - fenv['start']).total_seconds()),</pre></td><td valign="top">H2 (time since boot). No rate is used.<ul><li>The two time values are a launch time minus the time of the first Linux kernel log line of the boot, printed by <code>dur</code>. One is for F72d12. The other is for the first process of the rerun (<code>T72A1</code>).</li><li>The limit sentence prints the first entry of the F72d12 process list again.</li><li>The words "gave the lowest values" are typed in the template. The check in line 1048 tests them for asmread against part L and control I.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1598          'H3, memory speed. 7200 MT/s raises the rate of the load-only loop. The rerun cannot separate this from H1, '
1599          'H2 and the boot. Measurement: the like.spec line in several boots per speed (needs reboots and a change of '
1600          'the firmware setting).',
1601          'H4, pass counts in part A. An interval with %d passes has 6 passes on the %d threads of mesh 0 and 5 passes '
1602          'on the %d threads of mesh 1 (%d x 6 + %d x 5 = %d). threads120.csv has no row per thread, so the split is '
1603          'not proven. Measurement: part A with the option --per-thread.'
1604          % (64 * 6 + 56 * 5, 64, 56, 64, 56, 64 * 6 + 56 * 5),
1605          'H5, load values. The high load values at the launches come from the rerun\'s own earlier processes '
1606          '(section 1.3).',
1607      ]</pre></td><td valign="top">H3 and H5 have fixed words.<ul><li>H4 inserts the pass count <code>64 * 6 + 56 * 5</code> = 664 passes. That is 6 passes on each of the 64 threads of mesh 0 plus 5 passes on each of the 56 threads of mesh 1.</li><li>The text says that this split is not proven. The reason it gives: threads120.csv has no row per thread.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1608      need((64 * 6 + 56 * 5) in {r['passes'] for r in sel(recs, dataset='rerun-A', binary='bw_new', kernel='read')}, 'pass count of H4 occurs')
1609      need((N['pa'][0]['session'], N['pa'][2]['session'], N['pa'][4]['session']) == (1, 2, 3) and N['pa'][0]['round'] == 1
1610           and rng(N['pa'][0]['new'])['lo'] &gt; max(rng(N['pa'][2]['new'])['hi'], rng(N['pa'][4]['new'])['hi']),
1611           'first-round bw_new read of session 1 above sessions 2 and 3')</pre></td><td valign="top">Two checks for sentences of the hypotheses. The build stops unless both hold.<ul><li>H4: at least one bw_new read record of part A of the rerun has 664 in its field <code>passes</code>. In facts.json 16 of the 18 such records have 664 passes.</li><li>H1: the entries 0, 2 and 4 of <code>N['pa']</code> belong to sessions 1, 2 and 3, and entry 0 is round 1. The lowest bw_new read rate of entry 0 must be above the highest rate of entries 2 and 4.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1612      V['hypotheses'] = hyp
1613      for t in hyp:
1614          w('- ' + t)
1615      w('')</pre></td><td valign="top"><code>V['hypotheses']</code> is set to <code>hyp</code>. Each hypothesis is written as one bullet. The function <code>section4</code> ends here, and the file ends too. The function returns nothing.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`: Defines `need`, `_q`, `g`, `sp`, `pc`, `pcr`, `nn`, `nns`, `table` and the fixed texts (lines 18 to 137), `med` and `analyse` with `pool` (lines 279 to 330) and `compare` (lines 333 to 336). Its function `render` defines `q2row` (lines 359 to 368), prepares the record lists, the comparisons and `pa3` (lines 413 to 439), calls `section4` (lines 1458 to 1464) and then builds section 0 from `c` (line 1467).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: Defines `sel`, `rng`, `overlap`, `gap` and `width_pct` (lines 442 to 485). Its parsers compute the rate of an interval: `read_k120` takes the column aggregate_GBps of a part A csv file (lines 264 to 304), and `bwx_intervals` sums bytes / elapsed_s / 1e9 over the T rows of a bwx csv file (lines 356 to 383). Lines 9 to 13 and 436 to 437 state the two kinds of rate.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: Builds the interval records with `add_k120` and `add_bwx` (lines 119 to 160). Sets the fields `speed_MTps`, `modules` and `boot` of a record: from try6.txt for the 7200 MT/s rows (line 56), and from the DIMM report for the 8000 MT/s rows (function `state_of`, lines 58 to 64). Its integrity check `boot` compares the boot ids of the state lines and of the probe.txt files with try6.txt (lines 674 to 681). Names the rows of the earlier runs and the positions, kernels and tags that become records (lines 30 to 31 and 182 to 284). Places the hardware error records with `hw_records` and `hw_compare` (lines 293 to 397). Writes `V` and the interval records to facts.json and rounds their decimal numbers to 3 places (lines 1016 to 1029). The function `run_checks` (lines 653 to 894) holds the integrity checks. `main` is in lines 1033 to 1052. It calls `run_checks` before `render`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The output file. Sections 4, 5 and 6 are lines 436 to 949. The word list is lines 38 to 89. Lines 95 and 96 define Q1 and Q2. Section 2 (lines 275 to 302) lists the decisions (a) to (r). Section 1.4 (lines 211 to 239) lists the integrity checks.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`: The text of the rules V1 to V4, F1 and F2 and the fixed list of 8000 MT/s baselines, written before go.sh started (183 lines).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: Source of bw_new. It computes aggregate_GBps as total bytes / longest per-thread time / 1e9 and prints it and the three per-thread columns with 2 decimal places (lines 584 to 603). After the intervals of a kernel it prints one `best` line with the highest aggregate_GBps (lines 599 to 605). A `thread` line of the option --per-thread also has 2 decimal places (line 612). bandwidth.orig.c, the source of bw_old, has the same computation and format in its lines 427 to 448. Limit: the records of 2026-11-13 show two texts of bandwidth.c. This local file has the sha256 f1985072.... The file probe.txt of the timed run of 18:12:22 UTC (folder kernels-20261113T181222Z, row A-1) recorded the sha256 c1406e02... for bandwidth.c. The probe.txt files of the three result folders `kernels-20261113T181210Z`, `kernels-20261113T181222Z` and `kernels-20261113T183218Z` give the same sha256 for the binary bw_new (fd7c14df...). So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
