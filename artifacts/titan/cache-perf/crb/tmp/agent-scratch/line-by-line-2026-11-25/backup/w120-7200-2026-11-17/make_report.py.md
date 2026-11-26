# `make_report.py` explained

- Source file: `make_report.py` in this folder (Python script, 2834 lines, 213989 bytes).
- sha256 of the source when this page was built: `3353042adcdfedb25da035362cd2e64905049cd71b021b7546d97ab30ef4563f`.
- Role in the whole-chip test: Last analysis step: builds the HTML report page from facts.json and raw csv rows.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

This script computes the rates, the ranges and the drops of the report page `whole-chip-rerun-7200.html` from the interval records of `facts.json` and from the thread rows of the raw csv files. It writes the page only when all of its self-checks pass.

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
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line. This script takes no rate from them.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **go.sh, go2.sh, ra.sh, rx.sh**: the run scripts of the test. go.sh is the driver of the rerun. go2.sh is the driver of control I. ra.sh runs part A. rx.sh starts bwx12 once for each argument line of a spec file (parts L and C, control I).
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Spec file**: a text file with one argument line: `like.spec` (part L), `cfwd.spec` and `crev.spec` (part C). The line has the form `name|arguments`.
- **cfwd, crev, kernel order**: the two argument lines of part C. cfwd times oldread, read, asmread. crev times asmread, read, oldread. The kernel order is the order of the kernels in this sequence.
- **Idle start**: a launch at a 1-minute load average below 1.0.
- **Visit**: one time at which the same line was run. A later visit is the same line run again at a later time.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at nearly the same time (after 6 s, or after 4 s in the rows L-2 to L-4).
- **Pass count**: total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. A record holds it in the field `passes`.
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **GB, GB/s**: 1 GB is 1e9 bytes. GB/s is gigabytes per second.
- **csv file**: a text file whose lines hold values separated by commas.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values. This script reads the I rows and the T rows only.
- **I row (interval row)**: 9 fields: `I`, round, pos, kernel, bytes_per_thread, threads, total_bytes, max_elapsed_s, aggregate_GBps.
- **T row (thread row)**: 13 fields: `T`, round, pos, kernel, tid, cpu, bytes, elapsed_s, t_sched_s, t_start_s, t_end_s, passes, flags. The times are seconds since the start of the process.
- **Interval row of part A**: a line of a part A csv file with 10 fields: kernel, threads, bytes_per_thread, rep (the interval number), total_bytes, elapsed_s, aggregate_GBps, per_thread_min_GBps, per_thread_max_GBps, per_thread_avg_GBps. The field `elapsed_s` holds the longest elapsed time of a thread. A row with the text `best` in the field `rep` is not an interval row: it repeats the highest rate of the process [Ref9]. The file is `threads120.csv` in the rerun and in row A-1, `A1.csv` in row A-2 and `A3.csv` in row A-3.
- **Process header line**: a line of a csv file that starts with `-- `. The run script writes it before each process. It holds the binary, the kernel or the arguments, the 1-minute load average and the launch time.
- **`# bwx:` line**: the header line that a bwx runner prints into its csv file. It holds the kernel sequence (`seq=`), the stop rule, the start option (`start=`) and the counter setting (`count=`).
- **Trial-mode header**: a csv header line of the form `# bwx<digits> trial mode:`. The script comment says that such files are one-CPU trial files of older runners. They hold no kernel sequence.
- **Start option, counter setting**: `start` is the runner option `--start` (common or offset). `count=1` means that the runner counted hardware events of the CPU, `count=0` that it did not.
- **launches.txt, env.txt**: two files of a result folder of the runner script rx.sh. launches.txt holds one line `launch ...` and one line `rc ...` per process. env.txt is written when the script starts. It holds a process list.
- **probe.txt**: a record file that the test script of 2026-11-13 (`run_kernels.sh`) writes into its result folder. Among other lines it holds the sha256 values of the source files and of the binaries that the script built.
- **rc**: the exit status of a process. 0 means success.
- **Rerun**: the 10 steps that go.sh ran at 7200 MT/s on 2026-11-17: 3 sessions of parts A, L and C, and one more part C process (T72C4).
- **Q1, Q2**: the two questions of the rerun. Q1: at 7200 MT/s, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much. Q2: did the rate of either kernel differ from the earlier runs with 12 modules at 8000 MT/s.
- **Step**: one part of one session, the extra part C process (T72C4), or one process of control I.
- **T72A1 to T72I2**: the folder tags of the 12 steps: T72, then the letter of the part (A, L, C, or I for control I), then a number.
- **Run log**: the text that go.sh or go2.sh printed during the run. It is saved in `R` as `go-T72-20261117T221209Z.log` and `go2-T72-20261117T222335Z.log`.
- **Page**: the HTML report that this script writes: `whole-chip-rerun-7200.html` (`OUT`, line 31).
- **F72d12**: one process of the part L line that ran at 20:02 UTC on 2026-11-17 for another test, in the same boot as the rerun and before it. It is not part of the rerun.
- **A-1, A-2, A-3**: the 8000 MT/s rows for part A, all of 2026-11-13, with the same two binaries. A-1 is the original test. A-2 is a second run with another process order. A-3 is three more processes of bw_old read.
- **L-1, L-2, L-3, L-4**: the 8000 MT/s rows for parts L and C, all with bwx12. L-1 (2026-11-17) used the argument line of part L unchanged. L-2 to L-4 (2026-11-15) used 4 s intervals and counted other hardware events of the CPU.
- **List of 8000 MT/s rows**: the 8000 MT/s runs with 12 modules that the page compares with: rows A-1 to A-3 and L-1 to L-4. The rules file fixed them before the run.
- **Pool**: the intervals of several rows taken together as one range.
- **B7a, B7b, C3a, C3b, B5a-rev, B5b-rev**: datasets of the older runner bwx at 8000 MT/s. The page shows them in one note under Table 2. No wording comes from them.
- **X2d12, X1d10, X1d10b, BASEd10**: four processes of the part L line on 2026-11-17 at 8000 MT/s, each in a boot of its own. X2d12 had 12 modules. The other three had 10 modules. The page shows them in notes under Table 2. No wording comes from them. One of these notes reports a test: X2d12 is added to the pool L-1 to L-4. All 8 rows of Table 2 that use this pool keep their overlap result (line 2133).
- **Rules V1 to V4, F1, F2, and the rules file**: the comparison rules in `baselines-and-rules.txt`. They and the list of 8000 MT/s rows were fixed before the run.
- **FACTS.md, facts sheet**: the detailed record of the rerun. The script `build_facts.py` wrote it from the raw files. This script reads it to compare its own numbers with it and to copy word definitions.
- **facts.json**: the data file of the facts sheet, written by `build_facts.py`. Its list `intervals` holds one record per timed interval. Its part `meta` holds facts of the run. Its part `verdicts` holds the comparison results of the facts sheet.
- **Interval record**: one entry of the list `intervals` of facts.json: a dictionary with the fields of one timed interval.
- **Record fields used here**: `dataset` (the run group), `part` (A, L, C or I), `binary`, `kernel`, `round`, `pos`, `interval` (number inside the process, from 0), `GBps` (the rate: 2 decimals for part A, 3 decimals for bwx), `folder`, `file`, `line` (line of the interval row in the csv file), `proc_key` (one value per process), `session`, `tag`, `kernel_before`, `threads`, `modules`, `speed_MTps`, `boot`, `min_ms`, `stop`, `start`, `count`, `passes`, `process`, `launch_utc`, `load1_at_launch`.
- **Dataset**: the field `dataset` of a record. `rerun-A`, `rerun-L` and `rerun-C` are the three parts of the rerun. `control-I` is control I. Every other value names an earlier run.
- **kernel_before**: field of a bwx record: the kernel that was timed directly before in the same process. It starts with `none` for the first interval of a process.
- **Tag**: the field `tag` of a record: the folder tag of the step (for example T72L1), or the name that an earlier run gave the process. The records of row A-1 hold no tag.
- **`min_ms`, `stop`**: `min_ms` is the shortest length of one interval in milliseconds. `stop` is the stop rule: `whole pass` or `common`.
- **`meta.rerun`, `meta.launches`, `meta.counts`**: parts of facts.json. `meta.rerun` holds the boot id, MemTotal, the memory speed and the start and end times of go.sh and go2.sh. `meta.launches` holds one entry per step with its first launch, its load and its gap. `meta.counts.intervals` is the number of interval records.
- **`gap_s`, `load1_at_first_launch`, `start_state`**: fields of an entry of `meta.launches`. `gap_s`: the seconds since the end of the previous 120-thread process (no value for the first step). `load1_at_first_launch`: the 1-minute load average at the first launch of the step. `start_state`: a text that says from which state the step started.
- **Verdict record**: an entry of the part `verdicts` of facts.json. It holds one comparison result that a run of `build_facts.py` computed: ranges, n, overlap and distance, or a drop range. The files `facts_text.py` and `facts_text4.py` build these records. A run of `build_facts.py` loads both files.
- **`IV`, `META`, `RERUN`, `FJ`, `FMD`**: globals of this script. `FJ` is the parsed facts.json. `IV` is its list of interval records. `META` is its part `meta`. `RERUN` is `meta.rerun`. `FMD` is the text of FACTS.md.
- **Names of record groups**: globals that hold a list of records. First part: `A`, `L`, `C` = part A, L, C of the rerun, `I` = control I, `F` = F72d12, `B_A`, `B_L` = 8000 MT/s rows per dataset (a dictionary), `P_A`, `P_L` = pool of these rows, `X_` = older runner bwx. Second part: `OLD` = old read kernel, `NEW` = bw_new read, `ASM` = asmread, `READ` = kernel read of bwx12 (of the runner bwx in the `X_` groups). Suffix: `AO` = directly after oldread, `AA` = directly after asmread, `AR` = directly after read, `FI` = first interval of the process.
- **Names of ranges**: a global whose name starts with `r` and a capital letter is an `Rg` object. In most cases it is the range of the group with the same name. Examples: `rL_old` is the range of `L_OLD`, `rPL_asm` is the range of the pool `P_L_ASM`, `rX_read_ao` is the range of `X_READ_AO`.
- **`USED`, `OTHER`, `EXTRA`**: `USED`: all records of the figures and comparisons. `OTHER`: the records of the older runner bwx. `EXTRA`: a dictionary with the records and boot facts of X2d12 and of the three boots with 10 modules.
- **`SEVEN`, `EIGHT`**: the records of `USED` at 7200 MT/s and at 8000 MT/s (lines 309 and 310).
- **`BWX_USED`, `A_USED`**: `BWX_USED`: the records of `USED` outside part A, all of the binary bwx12 (line 340). `A_USED`: the part A records of `USED` (line 347).
- **`_exact`, `_fproc`**: two keys that this script adds to a record in memory. `_exact` is the sum of the T rows, rounded to 6 decimals (`val`, line 188). `_fproc` is the number of the process inside its csv file, counted from 1 (line 349, used part A records only). facts.json does not hold them.
- **`is_64_56`, `flagged`**: two fields of a bwx12 or bwx record of facts.json. This script does not read them. `is_64_56` is true when the interval has 64 threads on CPUs 0-63 and 56 threads on CPUs 64-119, on 120 different CPUs. `flagged` is the number of its T rows with a value other than `-` in the field `flags` [Ref8].
- **`IROW_MAX`, `IROW_MAX_X`**: the largest absolute difference between the sum of the T rows, rounded to 0.01 GB/s, and the rate printed in the I row. `IROW_MAX` is for the bwx12 records of `USED`, `IROW_MAX_X` for the records of `OTHER` (lines 342 and 344).
- **`Q1`**: a dictionary with one entry per pair group: `C_ao`, `C_aa` (part C, read after oldread or after asmread), `L`, `I`, `F`, `L1` (row L-1), `A` and `A8` (part A at 7200 and at 8000 MT/s). An entry of a bwx12 group holds the pairs, the drops and the two ranges. The entries `A` and `A8` hold the drops only.
- **`A_PAIRS`, `A8_PAIRS`, `A_V3`, `DIST`**: `A_PAIRS` and `A8_PAIRS`: per session (or dataset) and round of part A, the two ranges and the drop between the two medians. `A_V3`: per round, session 1 of bw_new read against the rows A-1 and A-2 of the same round. `DIST`: three kinds of distance of the asmread range of part L, against the pool L-1 to L-4 and against F72d12.
- **`c_ao`, `c_aa`, `c_all`**: the drops of part C in percent. `c_ao`: the 4 pairs with `read` directly after `oldread`. `c_aa`: the 4 pairs with `read` directly after `asmread`. `c_all`: both lists joined, 8 drops (lines 2406 and 2410).
- **`VISIT_LO`, `VISIT_HI`, `VISIT_OLD_LO`, `VISIT_OLD_HI`**: the lowest and the highest rate over the three visits of the part L line in the 7200 MT/s boot (F72d12, part L, control I): the first two for asmread, the last two for oldread (lines 501 and 502).
- **`LOWEST_ASM`, `rPL_asm_wo`**: `LOWEST_ASM` is the record with the lowest asmread rate of the pool L-1 to L-4 (line 520). `rPL_asm_wo` is the range of that pool without this one interval (line 521).
- **`A_OLD_BELOW`, `A_OLD_ABOVE`**: the part A intervals of the old read kernel at 7200 MT/s with a rate below the lowest rate, or above the highest rate, of the pool A-1 to A-3 (lines 525 and 526).
- **`X_PAIRS`, `X_ABOVE`, `X_MAX_READ`, `X_MAX_ASM`, `X_REV_MAX_READ`, `X_REV_MAX_ASM`**: values for the note on the older runner bwx. `X_PAIRS`: three part C ranges, each with the bwx range of the same kernel and the same kernel directly before. `X_ABOVE`: the distance of the nearest ends of each pair. `X_MAX_READ`, `X_MAX_ASM`: the highest read and asmread rate of `X_LOADS`, the read and asmread records of the datasets B7a, B7b, C3a and C3b (line 326). `X_REV_MAX_READ`, `X_REV_MAX_ASM`: the same for the reverse-order processes (lines 543 to 549).
- **`CHECKS`, `PROSE`, `REFS`**: `CHECKS`: the self-check list, one entry (pass or fail, text) per line. `PROSE`: the text of the page that counts for the word limit. `REFS`: the entries of the reference list.
- **`SEC`**: a dictionary from the number of a FACTS.md section (for example `3.4`) to its text.
- **`LAUNCH`, `STEPS`**: `STEPS` is the list of the 12 folder tags in run order. `LAUNCH` maps a tag to its entry of `meta.launches`.
- **`HA1`, `HA2`, `HA3`**: lists made in line 990: one entry (line number, launch time, text) per process header line of the csv file of row A-1, A-2 or A-3.
- **`SPEC`, `LINE_L`**: `SPEC` maps like, cfwd and crev to the name, the arguments and the kernel sequence of that spec file (line 1195). `LINE_L` is the name of the part L line, `a6456` in the saved data (line 1196).
- **`F1_BLOCKS`**: the data of figure 1 (line 1580): two blocks, each with a group of 8000 MT/s rows and a group of 7200 MT/s rows. A row holds two `Rg` objects and its drops.
- **`P_OLD_BLOCKS`, `P_NEW_BLOCKS`**: the data of figure 2: the blocks of the panel `Old read kernel` (line 1886) and of the panel `Load-only loop` (line 1918). A block holds its grey band and its groups of rows.
- **`FW_WORDS`**: the dictionary from term to definition that `facts_words` reads from the word list of FACTS.md (line 2290).
- **`WORDS`**: the word list of the page: a list of pairs (term, definition) (line 2323). `build` writes it into the folded part `Words used here`.
- **`SHORT_MORE`**: the bullet list of five items that the page shows under the three sentences of the Short version (line 2423).
- **`BOOT8`**: the first 8 characters of the boot id of the rerun (line 2306).
- **Hard assertion**: a call of `need`. When its condition is false the script stops at once.
- **Self-check list**: the list `CHECKS`. The script prints it at the end with PASS or FAIL per line.
- **Cross-check**: a comparison of a value that this script computed with the same value in FACTS.md or in a verdict record.
- **Tolerance (`tol`)**: the largest difference at which a cross-check still passes. Against FACTS.md it is 0.01 GB/s for a rate and 0.1 for a percent value. Against a verdict record it is 0.001 GB/s for a rate and 0.01 for a drop in percent.
- **Rounding step**: the unit to which `q` rounds a value before a comparison or before printing, for example 0.01 GB/s.
- **Summary line**: a line that `check(True, ...)` adds to the self-check list at the end of a block of hard assertions. It is always PASS, and it prints the values that the block found.
- **Review finding**: an entry of the file `review-w2.json` in `S`. It names a defect that a review of the facts sheet found. Two comments of the script (lines 920 and 1043) cite such an entry by its identifier.
- **Range**: the lowest and the highest rate of a group of intervals. In this script a range is an object of the class `Rg`.
- **Ranges overlap**: two min-to-max ranges share at least one value.
- **Distance of the nearest ends**: for two ranges that do not overlap: the lowest value of the higher range minus the highest value of the lower range.
- **Distance of the farthest ends**: the highest value of the higher range minus the lowest value of the lower range.
- **Span (of the three visits)**: the highest value of the three visits minus the lowest value, in GB/s: `VISIT_HI - VISIT_LO` for asmread, `VISIT_OLD_HI - VISIT_OLD_LO` for oldread.
- **n**: the number of measurements that a range comes from. It is written as intervals / processes / sessions / boots (rule V1 point 1). "No session" marks a row that is not part of a session of go.sh.
- **Median**: the middle value of a sorted list. For an even number of values it is the mean of the two middle values.
- **Pair, drop**: a pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A the drop uses the medians of the two processes of one session and round.
- **Wording**: the fixed text of a comparison result: `no difference seen` when the two ranges overlap, `differs between the 8000 MT/s boot and the 7200 MT/s boot` when they do not.
- **Boot, boot id**: a boot is one run of the machine from a start to the next restart. The boot id is a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **7200 MT/s boot, 8000 MT/s boot**: the 7200 MT/s boot is the boot of the rerun (boot id 3bfc57a1...). The 8000 MT/s boot is the one boot, started on 2026-11-09, in which all 8000 MT/s records of `USED` and `OTHER` ran. X2d12 and the three boots with 10 modules are four later boots.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user. It starts with `==`.
- **System account**: one of the 6 account names in `SYSTEM_ACCOUNTS` (line 844), for example `syslog`. The script stops unless each of them owns exactly 1 process in every state line (line 870).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes. "Load at launch" is the 1-minute value read directly before a process starts.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **%CPU, process list**: a process list is the output of the tool ps that a run script saves before a launch. %CPU is its column pcpu: the CPU time that a process has used, divided by the time since the process started.
- **Journal, kernel log**: the kernel log is the list of messages of the Linux kernel. The journal is the log store of Linux. It keeps the kernel log of earlier boots.
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues).
- **Module list**: the output of the command `dmidecode -t 17`, which prints the hardware table of the firmware. It holds one entry "Memory Device" per memory module.
- **Firmware setting, DIMM Frequency, TXREQ**: a firmware setting is a value that the machine applies at its next start. "DIMM Frequency" sets the memory speed. The TXREQ settings limit the read requests of the cores. They are not memory settings. A file `set.txt` holds the replies of the settings tool to the changes of one step: one change in the folders `x1`, `x2` and `dimm7200-20261117`, two changes in the folder `revert`.
- **Revert**: the step of the firmware test (folder `fwtest-20261117/revert`) that set `TXREQ Max` and `TXREQ Min` back to their values of the 8000 MT/s boot.
- **Error marker**: a text of the form `<Name: ...>` that a settings list holds in place of a value that could not be read. The two names are `ValueUnavailable` and `VStoreError`.
- **Date line**: line 1 of an env.txt file and of the three set.txt files of the firmware test, of the form `Tue Nov 17 03:43:50 AM UTC 2026`. The script converts its time to the 24-hour form.
- **try6.txt, boots.txt**: two files saved in the 7200 MT/s boot. try6.txt is the record of that boot: time, boot id, MemTotal, the kernel log line with the module count, and the count of the lines "Configured Memory Speed: 7200 MT/s". boots.txt is the boot list of the journal.
- **Saved kernel logs and journal**: files of the folder `R/dimm-check-20261117`. `k-5.txt` is the saved kernel log of the 8000 MT/s boot, and `h-5.txt` holds saved journal lines of that boot. `k-1.txt` to `k-4.txt` are the saved kernel logs of four later boots at 8000 MT/s: BASEd10, X2d12, X1d10b and X1d10, in this order.
- **gaps.txt, dmi17-7200.txt, questions.json**: more raw files. gaps.txt was saved in the 7200 MT/s boot: its line 7 holds the time of the first kernel log line of that boot. dmi17-7200.txt is the module list saved in that boot. A file questions.json is a firmware settings list that the settings tool saved.
- **File time**: the time of the last change of a file, as the file system stores it.
- **Time window**: the time from the launch of a process to its end (`launch_window`, line 944). For the rows A-1 and A-2 it runs from the first launch to the last launch in the csv file. For row A-3 it runs from the launch of the first process used to the launch of the process after the last one used.
- **UTC**: Coordinated Universal Time, the time standard without a time zone offset. The times of the run logs and of the records are in UTC.
- **One-thread phase**: the one-thread processes that the test of 2026-11-13 ran directly before its 120-thread part. The rerun did not repeat them.
- **Earlier report**: the report page of 2026-11-15 on the lower whole-chip read rate of the load-only loop (`EARLIER`, line 32).
- **R, S**: short forms of two folders. R is the results folder `/home/jhan/workspace/titan/cache-perf/crb/results`. S is the scratch folder of the rerun `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`. A record writes the folder of its csv file as `R/...`.
- **Reference key**: the short name of a reference inside this script, for example `golog`. `ref` writes it into the page as a mark, and `number_refs` replaces each mark by `[RefN]`.
- **HTML**: HyperText Markup Language, the text format of a web page. The page that this script writes is one HTML file.
- **SVG**: Scalable Vector Graphics: the drawing format of the two figures. It is text inside the HTML page.
- **Tooltip**: the text that a browser shows while the pointer rests on a mark. In SVG it is an element with the name `title`.
- **Dumbbell chart**: a chart with two dots per row and a line between them. Figure 1 uses it: one dot for the old read kernel, one for the load-only loop.
- **Strip plot**: a chart with one dot per measurement along one axis. Figure 2 uses it: one dot per interval.
- **Grey band**: in figure 2: the lowest-to-highest range of the 8000 MT/s rows of a block.
- **Block, group, row (of a figure)**: the data structure of both figures. A block is one method (for example the 6 s measurements with bwx12). A block holds groups (8000 MT/s, 7200 MT/s). A group holds rows.
- **Layout (wide, mid, narrow)**: the three widths in which figure 1 is drawn: 940, 726 and 386 px. The style block shows the one that fits the window.
- **Style block**: the text constant `CSS` (line 2580). It holds the style rules of the page, for example sizes, colours and widths. `build` puts it into the `style` element of the HTML page (line 2707).
- **Hollow marker, filled marker**: a hollow dot marks an 8000 MT/s row. A filled dot marks a 7200 MT/s row.
- **Hover area**: the invisible area around a dot of figure 2 that shows the tooltip of the dot.
- **Short version (of the page)**: the three sentences at the top of the page. The list `SHORT` (line 2411) holds them.
- **Reading notes**: the two small bullet lists `how1` and `how2` that the page shows under figure 1 and under the first panel of figure 2. They are counted as captions, not as prose.
- **Folded**: a part of the page that stays closed until the reader opens it (an HTML element `details`).
- **Typed (cell or value)**: written in the script as a fixed text or number, not computed from the records. Example: the cells `yes`, `no` and `0` of Table 2.
- **px**: pixel, the unit of length on the screen. The sizes of the style block and the positions and sizes of the two figures are given in px.
- **Decimal**: a Python number type that stores decimal digits exactly, without the binary rounding of a floating-point number.
- **ROUND_HALF_UP**: the rounding mode of `Decimal` used here: a value exactly between two steps is rounded away from zero. Example: 0.125 becomes 0.13.
- **lambda**: a Python function without a `def` statement, written in one expression. Example: `T34 = lambda part, frag: ...`.
- **f-string**: a Python text with the letter `f` before its first quote. Each `{expression}` inside it is replaced by the value of the expression.
- **Dictionary**: the Python type `dict`: a table from keys to values. A record of facts.json is a dictionary.
- **Regular expression**: a search pattern for text. The Python module `re` applies it. The script uses it to read numbers and fields from text lines.
- **Markdown table**: a group of text lines that start with `|`. The cells stand between the `|` characters. The first line holds the column titles, and the second line is a separator line of `-` characters.
- **JSON**: a text format for data: lists, dictionaries, numbers and texts. facts.json and questions.json use it.
- **UTF-8**: the usual byte encoding of text. The page file is written in it.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **KiB, MiB, GiB**: 1 KiB is 1024 bytes. 1 MiB is 1024 KiB (2^20 bytes). 1 GiB is 1024 MiB (2^30 bytes).
- **est.**: estimated, not measured directly.

</details>

## Main flow

1. The script takes no command-line argument and reads no environment variable. Its paths are constants: the scratch folder `S`, the results folder `R`, the output page `OUT` and the earlier report `EARLIER` (lines 29-32).
2. It creates two empty lists that later code fills: `CHECKS` (the lines of the self-check list) and `PROSE` (page text for the word count) (lines 38-39).
3. It defines the helpers that the rest of the file uses. They are the stop and check functions, the number and rounding functions, and the readers of the raw csv rows. The function `val` gives the rate of one record. The class `Rg` holds the range of a group of records (lines 42-226).
4. It loads `facts.json` and `FACTS.md` with `read_retry` (up to 10 tries, 1.5 s apart). `IV` becomes the list of all interval records. The script stops when the number of records differs from the count that `facts.json` states (lines 229-239).
5. It selects the record groups of the page with `sel`. For each group `expect` asserts the number of intervals and of processes. The groups at 7200 MT/s are part A, part L, part C, control I and F72d12. The groups at 8000 MT/s are the rows A-1 to A-3 and L-1 to L-4 (lines 242-304).
6. It asserts the method of all used records (`USED`). All have 12 memory modules, and each memory speed has one boot. Part A has intervals of at least 0.5 s (`min_ms` is 500) with the whole-pass stop. The bwx12 records have 6 s or 4 s intervals (`min_ms` is 6000 or 4000) with the common stop. It also selects the records of the older runner bwx (`OTHER`) (lines 306-338).
7. First rate computation. For every bwx12 record of `USED` and every record of `OTHER`, `val` sums the 120 thread rows of the raw csv file. `val` stops unless the sum, rounded to 0.001 GB/s, equals the field `GBps` of the record. The script also stops when a sum, rounded to 0.01 GB/s, differs by more than 0.02 GB/s from the rate printed in the interval row. For every used part A record, `file_process` checks the csv row against the record (lines 339-353).
8. Question Q1. It pairs each load-only interval with the old-kernel interval of the same process and round, and computes the drop of each pair in percent. For part A it computes the drop between the medians of the two processes of one session and round. It stops when a drop at 7200 MT/s is not above 0 (lines 406-460).
9. Question Q2. It builds the lowest-to-highest range of each group and tests each 7200 MT/s range for overlap with its 8000 MT/s range. For some comparisons it also computes the distance of the nearest ends. For part L it also computes the difference of the medians. For `asmread` of part L it also computes the distance of the farthest ends. A `need` call asserts the expected result of each comparison (lines 462-553).
10. Cross-check. It compares the computed drops, ranges, medians, distances and wordings with the tables and the text of `FACTS.md`, and with the verdict records of `facts.json`. Each comparison adds a PASS or FAIL line to `CHECKS`. For 5 blocks of comparisons, `grouped` then replaces the lines of the block by one line (lines 555-809).
11. Raw-file checks for the page section on the machine state and for the notes under Table 2. It reads the two run logs, the boot record, and the saved journal and kernel logs. It reads the firmware settings files, the process lists and the module list. It reads the three spec files and the header lines of every csv file under `R`. A fact that does not hold stops the script. Three places in these lines compare a computed value with `FACTS.md` and add a line to the self-check list (lines 1033 to 1038, 1331 to 1342 and 1378) (lines 811-1386).
12. It builds the reference list of the page with `addref`. The script stops when a referenced path does not exist (lines 1388-1477).
13. It defines the HTML and SVG helpers and the two drawing functions `fig1` and `panel`. It prepares the 21 rows of figure 1 and the blocks of the two panels of figure 2. It asserts the facts that the caption of figure 2 states (lines 1479-1989).
14. It defines the functions that build Tables 1 to 4 and 6 and the two table views of the figures. Lines 2057 to 2076 assert more facts about the rows of Table 2. Line 2062 adds one more cross-check with `FACTS.md` to the self-check list (lines 1991-2275).
15. It builds the word list of the page (58 entries). 30 definitions come from the word list of `FACTS.md` with the function `fw`. 24 of them stand alone, and 6 get more text from this script. In 4 of the 30, `fw` replaces one phrase of the sheet by another wording (argument `swap`). The other 28 definitions are written in this script (lines 2278-2396).
16. It builds the text of the page from the computed values: the three sentences of the Short version and the bullet lists of the sections. It also defines `state_table` (Table 5) and builds the caption of Table 6 (lines 2398-2577).
17. `build` assembles the style block, the text, the figures and the tables into one HTML string. `number_refs` then numbers the references in the order of their first use (lines 2580-2784).
18. It checks the built page. The checks cover the number of words, the three sentences of the Short version, and that every reference is cited. They cover that the page holds no script and no external file. They cover the labels of control I and F72d12, the number of tooltips, phrases that a review rejected, and the hover areas of figure 2. One more check requires the word `Linux` before each `kernel thread`, `kernel line` and `kernel message` (line 2811) (lines 2786-2817).
19. It prints the self-check list. When a line is FAIL, it prints `NOT WRITTEN` and exits with status 1, and the page on disk stays as it was. When all lines are PASS, it writes the page to `OUT` and prints the three sentences of the Short version (lines 2819-2834).

## Behavior a reader must know

- **Input and output.** The script reads `S/facts.json`, `S/FACTS.md`, the three spec files in `S`, raw result files under `R` and the earlier report page. It changes none of these files. It writes one file: the page `OUT` (line 31). Lines 2828 to 2830 are the only write. They run after all checks.
- **Source of every rate.** Every measured rate on the page is a value of the function `val` (line 176), or it is computed from such values (a median, a distance, a drop or a width in percent). Two places of the page are exceptions. Both use the rate that an I row prints. One reference entry quotes the printed rate of one interval, next to the value of `val` (line 1430). The interval is the lowest `asmread` interval of the pool L-1 to L-4. The reading notes under figure 1 give `IROW_MAX` (line 2682). It is the largest difference between a value of `val`, rounded to 0.01 GB/s, and the rate that its I row prints, over the bwx12 records of `USED`. No measured rate is typed in the script. Each interval record of `facts.json` names its csv file (fields `folder` and `file`) and the line of its interval row (field `line`). For a rate, the script opens only the csv files that the records name. Load averages, pass counts and launch times come from fields of the records and of `meta.launches`. Some of these values come from raw files. The launch time and the end time of F72d12 come from its file `launches.txt`. The load of X2d12 and of the three 10-module boots comes from their files `launches.txt`. The launch times of the rows A-1 to A-3 and of the one-thread phase in Table 5 come from the process header lines of their csv files. The script stops unless the launch time and the load from `launches.txt` equal the fields of the records (lines 914 and 1309).
- **Record selection.** `sel` (line 242) filters the list `IV` by field values. `expect` (line 260) stops unless the group has the expected number of intervals and of processes, and 120 threads in every record. Lines 272 to 304 name every group of the figures with its expected counts. Example: part L has 6 intervals of 3 processes per kernel (lines 275 and 276).
- **Rate of a part A record (binaries bw_old and bw_new).** `val` returns the field `GBps` of the record. It does not compute this rate again from bytes and time. The value is the column `aggregate_GBps` of the part A csv file, which the benchmark binary prints with 2 decimals. In the rerun this file is `threads120.csv`. The header line of that csv gives the formula: the sum of the bytes of all threads, divided by the longest elapsed time of a thread, with 1 GB = 1e9 bytes [Ref3]. The source of the benchmark computes the column in this way [Ref9]. After the 3 interval rows of a process, the binary prints one more row with the text `best` in the field `rep`. It repeats the highest rate of the 3 intervals. No record names such a row, and the page does not use it. For part A the page uses the 3 interval rows: all 3 for the ranges, and their median for the drop. `file_process` (line 166) checks the csv row that the record names: 10 fields, the kernel of the record, 120 threads, the interval number, and a rate equal to `GBps`.
- **Rate of a bwx12 or bwx record.** `val` takes the 120 T rows (one row per thread) that follow the I row of the record. For each T row it computes `bytes / elapsed_s / 1e9` (the 7th and the 8th field of the row). It adds the values of the threads with a CPU number below 64, then the values of the other threads, and then the two sums (line 186). So the rate is the sum of 120 thread rates. The bytes of each thread are divided by the elapsed time of that thread. The script stops unless this sum, rounded to 3 decimals, equals the field `GBps` of the record (line 187). `val` stores the sum, rounded to 6 decimals, in the record under the key `_exact`. Every later call returns the stored value.
- **The rate printed in the I row is not the page value.** The I row prints the total bytes divided by the longest elapsed time of a thread (column `aggregate_GBps`, 2 decimals). The script reads this column in two places. Lines 341 to 345 test it. The script stops when the page value, rounded to 0.01 GB/s, differs from the printed value by more than 0.02 GB/s. In the saved build the largest difference was 0.02 GB/s, both for bwx12 and for bwx [Ref5]. The page value was never below the printed value. The difference was 0.00 to 0.02 GB/s for the 70 bwx12 records and also for the 200 bwx records. These two ranges were computed again for this companion. The page gives the largest difference of the bwx12 records in the reading notes under figure 1 (line 2682). Line 1430 quotes the printed rate of one interval in a reference entry. Example: the I row of round 0, position 0 (`oldread`) in the part L csv file of session 1 prints 462.29 GB/s. The sum of its 120 T rows is 462.300017 GB/s. The page shows 462.30 GB/s [Ref4].
- **Two formulas for a rate.** A part A rate is the total bytes of all threads divided by the longest elapsed time of a thread. A bwx12 or bwx rate is the sum of the 120 thread rates. Each drop and each comparison of the page uses two rates of the same formula.
- **What the row readers check, and what they do not check.** For a bwx12 record, `t_rows` (line 124) requires 13 fields in every T row of the csv file. The interval must have exactly 120 T rows with the round, the position and the kernel of the record, and they must be the 120 lines directly after the I row. A csv file of the older runner bwx holds several processes. So for a record of that runner, `t_rows_block` (line 142) checks the 120 lines after the I row one by one. The script does not read the fields `tid`, `t_sched_s`, `passes` and `flags` of a T row. It does not test that the 120 CPU numbers differ. The facts sheet reports a test of the CPU numbers as its integrity check 11 and a test of the field `flags` as its integrity check 12. These two checks cover the 9 bwx12 csv files of the rerun and of control I [Ref1]. Each bwx12 and bwx record of `facts.json` also holds the fields `is_64_56` and `flagged` [Ref8]. This script does not read them. In the 286 bwx12 and bwx records that this script uses, `is_64_56` is true and `flagged` is 0. This count was made for this companion.
- **Which records stand for which kernel.** Old read kernel: kernel `read` of the binary `bw_old` (part A), and kernel `oldread` of bwx12 (parts L and C, control I, F72d12, rows L-1 to L-4). New read kernel: kernel `read` of the binary `bw_new` (part A), and kernel `read` of bwx12 (part C only). In part L, control I, F72d12 and the rows L-1 to L-4 the page uses `asmread` in place of the new read kernel. Part C holds `asmread` intervals too. The page compares the 2 intervals that ran directly after `oldread` with the 8000 MT/s pool (`C_ASM_AO`, line 288).
- **Records used and records left out.** `facts.json` holds 793 interval records [Ref2]. The page uses 139 of them for its figures and comparisons (`USED`, line 306) and 200 records of the older runner bwx for one note under Table 2 (`OTHER`, line 333) [Ref5]. It selects 16 more records of four other 8000 MT/s boots for two notes (`EXTRA`, lines 1299 to 1317). 14 of them give a rate. The 2 `asmread` records of BASEd10 give none. The script tests their fields only (lines 1308 to 1310). No rate is taken from the part A kernels write, copy, asmread, asmwrite and asmcopy. Their records are used for counts and for the launch order only (lines 2225, 2308 to 2316 and 2489). No rate is taken from the bwx12 kernels read_nop96, read_nop256 and read_1pl. From the rows L-1 to L-4 the script selects only `oldread` at position 0 and `asmread` at position 1. For the kernels that the page uses, no interval is left out as a warm-up. `USED` holds every `read` record of the part A datasets that it names, and every `oldread`, `asmread` and `read` record of its bwx12 datasets. In the csv files these records are the I rows of every round of each bwx12 process, and the 3 interval rows of each part A process that is used. These counts were made for this companion. No `sel` call names the datasets R0, R0b, B5a and B5b.
- **Grouping.** The class `Rg` (line 192) turns a list of records into a range. It stores the lowest rate, the highest rate and the median. It stores the number of intervals (`n`) and the number of processes (`np`, the number of different values of the field `proc_key`). The page gives ranges and medians. The median of an even number of values is the mean of the two middle values. So the median of a group of 2 intervals is their mean. Example: each dot of a bwx12 row of figure 1 is the mean of the 2 intervals of one process. Apart from such medians the page gives no mean over intervals, processes or sessions. It gives no single total per kernel over the whole rerun.
- **Drop of the load-only loop (question Q1).** For bwx12, `pairs_in_process` (line 407) pairs each load-only interval with the one old-kernel interval that has the same `proc_key` and the same `round`. In part L, control I, F72d12, row L-1 and the cfwd processes of part C, the old-kernel interval of a pair of the dictionary `Q1` (line 430) ran directly before the load-only interval. In the crev processes of part C it ran directly after it. The drop of a pair is `(1 - load-only rate / old rate) x 100`, computed from the values of `val`, not from the printed values. The page shows the lowest and the highest drop of a group with 1 decimal. In part A the two kernels run in two processes. So `a_pair` (line 444) takes the median of the 3 intervals of each process of one session and round, and the drop is computed between the two medians. The first sentence of the Short version gives the lowest and the highest drop of the 8 pairs of part C: bwx12 kernel `read` against `oldread` (lines 2406 to 2413).
- **Comparison with the 8000 MT/s rows (question Q2).** The script compares the range of a 7200 MT/s group with the range of its 8000 MT/s rows. When the two ranges share at least one value (`overlaps`, line 207), the wording is `no difference seen`. The page then gives the width of the 8000 MT/s range as the size that the test cannot exclude (an estimate). For the old read kernel this width is in percent of the lower end of the range (`width_pct`, line 476). For the one `asmread` row that overlaps (F72d12) it is in GB/s (line 2119). When the ranges share no value, the wording is `differs between the 8000 MT/s boot and the 7200 MT/s boot`, and the page gives the distance of the nearest ends. Two rows carry another wording. They are the part A rows of the new read kernel: session 1, each round against the same round of the rows A-1 and A-2. Their wording is the typed text `outside (above)` of rule V3 (line 2107). In Table 2 the cells `yes`, `no` and `0` and the wording of each row are typed. Hard assertions (lines 486 to 498 and 514) stop the script when the ranges do not give the typed result. For the bwx12 kernel `read` of part C, Table 2 gives no comparison with a row of the list. No 8000 MT/s run of this kernel with bwx12 exists, and the row says `Insufficient data` (line 2111). A note under Table 2 says how far each of the two `read` ranges of part C lies above the 8000 MT/s rows of the older runner bwx with the same kernel and the same kernel directly before (lines 2159 to 2161). These rows come from the datasets B7a, B7b, C3a and C3b. No wording comes from this note.
- **Rounding.** The sum of the T rows is computed with floating-point numbers (line 186). `val` rounds this sum to 6 decimals and stores it as a `Decimal` (line 188). All later computations with a rate use the Python type `Decimal`. The drawing code is the one exception. It converts a rate to a floating-point number for the place of a mark (lines 1600 and 1758). After the rounding of line 188, a value is rounded only when it is printed or compared: `f2` rounds to 0.01 (used for GB/s) and `f1` rounds to 0.1 (used for percent values). A value exactly between two steps is rounded away from zero. Distances and drops are computed from the values of `val`, not from the printed values. So a printed distance can differ by 0.01 GB/s from the difference of the two printed rates.
- **Checks that stop the build at once.** The function `need` (line 46) has 238 call sites. When its condition is false, `stop` prints `make_report.py: STOP:` with the reason and ends the script with exit status 1. No page is written. These calls belong to six groups. First: the number of records and processes of every group (`expect`). Second: the method fields of the used records (lines 308 to 319). Third: the raw csv rows. The script tests the T rows of every bwx12 and bwx record that gives a rate. It tests the I row of the bwx12 records of `USED` and of the records of `OTHER`. It tests the csv row of every used part A record. Fourth: the expected result of every comparison of this run. Fifth: the facts of the raw files for the machine state section. Sixth: the needs of the page itself. Four examples follow. Every reference path exists. `FACTS.md` holds the sections, table rows and terms that the script looks for. The comparison results that the caption of figure 2 and the Short version state are true (lines 1944, 1951, 2068 and 2405). No two dots of figure 2 lie within 5.2 px.
- **Checks that are listed.** The function `check` (line 52) adds one line with PASS or FAIL to the list `CHECKS`, and the script continues. The cross-check helpers `xc_range`, `xc_val`, `xc_text`, `xc_text_range`, `xc_drops` and `xv` compare computed values with `FACTS.md` and with the verdict records of `facts.json`. Lines 2819 to 2827 print the list. When one line is FAIL, the script prints `NOT WRITTEN`, exits with status 1 and leaves the page on disk unchanged. The saved output of a build shows 98 lines, all PASS [Ref5] [Ref6]. 14 of the 98 lines are summary lines of the form `check(True, ...)`. Such a line is always PASS. It prints values that the hard assertions before it have tested.
- **Tolerance of the cross-checks.** A cross-check with `FACTS.md` passes when the two rounded values differ by at most one step: 0.01 GB/s for a rate, 0.1 for a percent value (`near`, line 616). So a PASS line does not prove that the last digit is equal. A line of `xc_range`, `xc_val` or `xc_drops` prints both values. A line of `xc_text` or `xc_text_range` prints the computed value only. A PASS line of `grouped` prints only how many comparisons are equal. A FAIL line of `grouped` also prints the first mismatch. The verdict records of `facts.json` are compared to 0.001 GB/s (`xv`, line 779). The two drop ranges of part C are compared with their verdict records to 0.01 % (line 802).
- **The script fits this one data set.** Many `need` calls assert the result that this run gave. Two examples: part L of the old read kernel must lie below the 8000 MT/s pool (line 488), and every drop at 7200 MT/s must be above 0 (line 460). With data that give another result the script stops. It does not report the other result.
- **File times are used as facts.** Four checks read the modification time of a raw file (lines 908, 1077, 1092 and 1165). A copy of the results folder that does not keep the file times stops the script.
- **Figures of the page.** Figure 1 (`fig1`, line 1593) is a dumbbell chart with 21 rows. A row shows the median of the old read kernel, the median of the load-only loop, the lowest-to-highest range of each, and the drop in percent. The figure is drawn three times, 940, 726 and 386 px wide, and the style block shows the one that fits the window. Figure 2 (`panel`, line 1756) has two panels with the titles `Old read kernel` and `Load-only loop`. It shows one dot per interval (139 dots) and a grey band for the range of the 8000 MT/s rows of a block [Ref5]. Each dot of both figures has a tooltip that names the csv file and the lines of its interval rows.
- **Tables of the page.** Table 1 (`q1_table`): the drop per part. Table 2 (`q2_table`): 7200 MT/s against 8000 MT/s, one row per comparison, with notes. Table 3 (`visits_table`): the three visits of the part L line in the 7200 MT/s boot. Table 4 (`dist_table`): three kinds of distance for asmread. Table 5 (`state_table`): the machine state, each fact with its proof and its limit. Table 6 (`load_table`): the 1-minute load average at the first launch of every step and at the launches of the earlier rows. Two more tables hold every plotted value of the two figures (`detail_fig1`, `detail_fig2`).
- **Final numbers of the saved build, as an example.** Part C, 120 threads, 6 s intervals: `oldread` gave 464.00 to 468.14 GB/s (8 intervals). The bwx12 kernel `read` gave 320.89 to 324.98 GB/s directly after `oldread` (4 intervals) and 322.22 to 326.27 GB/s directly after `asmread` (4 intervals). The drop was 30.5 % to 31.2 % after `oldread` and 29.7 % to 31.1 % after `asmread` [Ref5].
- **Tests of this script.** `test_make_report.py` runs copies of this script. In 9 cases the copy reads a damaged copy of `facts.json`. In 1 case the copy names an earlier report that does not exist. Its saved output shows these 10 cases. Each one ended with exit status 1 and wrote no page. The case without damage ended with exit status 0 [Ref7].

## Call sequence in the whole-chip test

- `top-level statements of make_report.py` (line 20): No main function: statements run top to bottom. Small text helpers are left out.
  - `read_retry` (line 64): Lines 234 and 235: loads facts.json and FACTS.md, with up to 10 tries.
    - `facts_complete` (line 230): FACTS.md only: tests that the text holds its last section.
  - `need` (line 46): First call in line 239. Hard assertion with 238 call sites in the file.
    - `stop` (line 42): Prints a STOP message and ends the script with exit status 1.
  - `sel` (line 242): Lines 272 to 332: selects the interval records of one group.
  - `expect` (line 260): The same lines: asserts the number of intervals and processes of the group.
  - `check` (line 52): First call in line 337. Adds one PASS or FAIL line to `CHECKS`.
  - `val` (line 176): Line 341: rate of each bwx12 record of `USED`. Line 344: records of `OTHER`.
    - `t_rows` (line 124): bwx12 record: the 120 T rows directly after its I row.
      - `file_lines` (line 116): Reads the csv file of the record once and keeps its lines.
        - `lines_of` (line 80): Opens the file and returns its lines.
    - `t_rows_block` (line 142): Record of the older runner bwx: the same 120 rows, read by line number.
  - `q` (line 90): Lines 341 and 344: rounds the sum to 0.01 GB/s for the test.
  - `i_row_rate` (line 158): The same lines: the rate printed in the I row.
  - `file_process` (line 166): Line 349: checks each used part A record against its csv row.
  - `pairs_in_process` (line 407): Lines 431 to 436: old and load-only interval of one process and round.
  - `drops_of` (line 421): Line 439: the drop of each pair in percent.
    - `drop` (line 417): (1 - new / old) x 100.
    - `val` (line 176): Returns the value that the first call stored in the record.
  - `Rg` (line 192): Lines 440 to 469: the range object of each record group.
    - `__init__ (method of Rg)` (line 195): Sorts the records. Stores lowest, highest, median, n and the processes.
      - `val` (line 176): Rate of each record of the group.
      - `median` (line 102): Median of these rates.
  - `a_pair` (line 444): Lines 454 and 455: part A, drop between the medians of two processes.
  - `overlaps (method of Rg)` (line 207): Lines 486 to 514: tests the expected overlap results of this run.
  - `nearest (method of Rg)` (line 210): Lines 489 to 545: distance of the nearest ends of two ranges.
  - `farthest (method of Rg)` (line 216): Line 506: distance of the farthest ends, for part L with asmread.
  - `md_sections` (line 556): Line 586: splits FACTS.md into its numbered sections.
  - `T34 (lambda)` (line 653): Lines 654 to 659: finds the row of a part in FACTS.md section 3.4.
    - `facts_row` (line 598): First table row of the section that passes the test.
      - `md_tables` (line 569): Parses the Markdown tables of the section.
  - `xc_drops` (line 646): Lines 654 to 659: computed drops against that row.
    - `col` (line 592): Picks one cell of the row by the start of its column title.
    - `near` (line 616): True when two values differ by at most the tolerance.
    - `check` (line 52): Adds the PASS or FAIL line.
  - `xc_range` (line 620): Line 661 and later: a computed range against a FACTS.md table cell.
    - `rng_of` (line 610): Reads the two numbers of the cell.
  - `xc_text_range` (line 640): Line 665 and later: a range that stands in the text of FACTS.md.
  - `xc_val` (line 626): Line 670 and later: one computed value against a FACTS.md table cell.
  - `grouped` (line 56): Line 673 and later: replaces the checks of one block by one line.
  - `wording` (line 481): Lines 696 to 719: the fixed text for overlap or no overlap.
  - `width_pct` (line 476): Line 697 and later: width of a range in percent of its lower end.
  - `xc_text` (line 633): Line 704 and later: a value with its unit in the text of FACTS.md.
  - `vrow` (line 773): Lines 787 to 798: finds one verdict record of facts.json.
  - `xv` (line 779): Lines 787 to 797: computed ranges, n and distance against that record.
  - `state_lines` (line 847): Line 862: the state lines of the logs of go.sh and go2.sh.
  - `launch_window` (line 944): Line 962: launch and end time of each process of rows L-1 to L-4.
  - `hw_in` (line 953): Line 964 and later: hardware error records between two times.
  - `a_headers` (line 972): Line 990: process header lines of the csv files of rows A-1 to A-3.
  - `secs` (line 983): Line 1002 and later: a time of day in seconds.
  - `t_rows` (line 124): Lines 1018 and 1019: start and end of the lowest asmread interval.
  - `clock` (line 1022): Line 1030: launch time plus seconds, as a time of day.
  - `set_records` (line 1047): Lines 1064 to 1067: changed firmware settings in four set.txt files.
  - `proc_list` (line 1100): Lines 1118 and 1131: process lists that were saved before a launch.
  - `mem_line` (line 1149): Line 1156: the memory size line of two saved Linux kernel logs.
  - `spec_line` (line 1178): Line 1195: the argument lines of like.spec, cfwd.spec and crev.spec.
  - `launch_args` (line 1188): Line 1201 and later: the arguments of a launch line in launches.txt.
  - `bwx_header` (line 1235): Line 1258: header lines of each process of runner bwx.
  - `klog_boot` (line 1289): Line 1303: saved Linux kernel logs of X2d12 and of three 10-module boots.
  - `addref` (line 815): Lines 1389 to 1474: reference entries. Each path must exist.
  - `bwx_row` (line 1555): Lines 1562 to 1572: the rows of figure 1 for bwx12.
    - `pairs_in_process` (line 407): Pairs the intervals of the row.
    - `Rg` (line 192): Range of each kernel of the row.
    - `drops_of` (line 421): Drops of the pairs of the row.
    - `f1_row` (line 1551): Packs the row into a dictionary.
  - `f1_row` (line 1551): Lines 1574 and 1577: the rows of figure 1 for part A.
  - `band_title` (line 1876): Line 1889 and later: tooltip text of a grey band of figure 2.
  - `p_row` (line 1695): Lines 1890 to 1932: the rows of figure 2, each with its range.
    - `Rg` (line 192): Range of the records of the row.
  - `l_rows` (line 1869): Lines 1896 and 1922: the rows L-1 to L-4 of figure 2.
  - `a_new_block` (line 1905): Line 1933: the blocks of figure 2 for bw_new read, rounds 1 and 2.
  - `panel_rows` (line 1938): Lines 1943 to 1957: lists the rows of a panel for the caption tests.
  - `legend` (line 1963): Lines 1975 and 1983: the legends of the two figures.
  - `facts_words` (line 2279): Line 2290: reads the word list of FACTS.md.
  - `fw` (line 2293): Lines 2329 to 2395: copies definitions of that word list.
  - `ref` (line 821): Line 2356 and later: a reference mark. Its number comes later.
  - `UL` (line 1493): Lines 2423 to 2467: the bullet lists of the page text.
  - `build` (line 2677): Line 2784: assembles the whole page as one text.
    - `P` (line 1488): Line 2679: the three paragraphs of the Short version.
    - `panel` (line 1756): Lines 2695 and 2698: figure 2, one call per panel.
      - `beeswarm` (line 1682): Vertical offsets of the dots of one row.
      - `hit_cell` (line 1725): Hover area of each dot.
      - `val` (line 176): Rate of a dot, for its tooltip.
      - `src` (line 359): File and line numbers of a dot, for its tooltip.
    - `fig1` (line 1593): Lines 2729 to 2731: figure 1 in the wide, mid and narrow layout.
      - `drop_txt` (line 425): Drop text on the line between the two dots.
      - `dot_title` (line 1545): Tooltip text of a dot.
    - `q1_table` (line 2003): Line 2736: Table 1, the drop per part.
      - `table` (line 1501): HTML of the table. Every table function ends with this call.
    - `detail_fig1` (line 2255): Line 2739: the table view of figure 1.
    - `q2_table` (line 2079): Line 2752: Table 2, 7200 MT/s against 8000 MT/s, with its notes.
    - `visits_table` (line 2184): Line 2756: Table 3, the three visits of the part L line.
    - `dist_table` (line 2213): Line 2758: Table 4, three kinds of distance.
    - `detail_fig2` (line 2266): Line 2760: the table view of figure 2.
    - `state_table` (line 2503): Line 2768: Table 5, the machine state.
    - `load_table` (line 2219): Line 2771: Table 6, the 1-minute load average at launch.
  - `number_refs` (line 828): Line 2784: numbers the references in the order of first use.
  - `strip_tags` (line 1484): Lines 2787 to 2803: plain text of the page for the page checks.
  - `check` (line 52): Lines 2789 to 2813: the checks of the built page.
  - `end of the top-level statements` (line 2819): Prints the self-check list. Writes the page only when every line is PASS.

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `stop` | 42-43 | Ends the script at once: prints `make_report.py: STOP:` with the message and exits with status 1. | - | - |
| `need` | 46-49 | Hard assertion: calls `stop` with the message when the condition is false. | `stop` | - |
| `check` | 52-53 | Adds one entry (pass or fail, text) to the self-check list `CHECKS`. The script continues. | - | - |
| `grouped` | 56-61 | Replaces the checks added since index `start` by one line: how many comparisons are equal, and the first mismatch. | `check` | - |
| `read_retry` | 64-77 | Reads and parses a text file. After a failed or incomplete read it waits 1.5 s and tries again. Stops after 10 tries. | `stop` | - |
| `lines_of` | 80-82 | Returns the lines of a text file as a list. Bytes that are not valid UTF-8 are replaced. | - | - |
| `D` | 86-87 | Converts a number to the type `Decimal` through its text form. | - | - |
| `q` | 90-91 | Rounds a value to a step (0.01 by default). A value exactly between two steps is rounded away from zero. | `D` | - |
| `f2` | 94-95 | Rounds with `q` to 0.01 and returns the text with 2 decimals. | `q` | - |
| `f1` | 98-99 | Rounds with `q` to 0.1 and returns the text with 1 decimal. | `q` | - |
| `median` | 102-105 | Median of a list: the middle value, or the mean of the two middle values for an even count. | - | - |
| `esc` | 108-109 | Escapes the HTML special characters of a text, quotes included. | - | - |
| `file_lines` | 116-121 | Returns the lines of the csv file that a record names. Each file is read once and kept in `_FILES`. | `lines_of` | - |
| `t_rows` | 124-139 | bwx12 record: returns the 120 T rows of its interval. Stops unless they are the 120 lines directly after its I row. | `file_lines`, `need` | - |
| `t_rows_block` | 142-155 | Record of the older runner bwx: returns the 120 T rows after its I row, checked line by line. Stops when a 121st follows. | `file_lines`, `need` | - |
| `i_row_rate` | 158-163 | Returns the rate that the I row of a bwx record prints (9th field). Stops when the line is not that I row. | `file_lines`, `need` | - |
| `file_process` | 166-173 | Part A: stops unless the record's csv row holds its kernel, 120 threads, interval number and rate. Returns the process number inside the file. | `file_lines`, `need`, `D` | - |
| `val` | 176-189 | Rate of one record in GB/s. Part A: the field `GBps`. bwx12 and bwx: the sum of `bytes/elapsed_s/1e9` over its 120 T rows. | `D`, `t_rows`, `t_rows_block`, `need` | - |
| `Rg` | 192-217 | Class: the range of a list of interval records, with lowest, highest and median rate, number of intervals and number of processes. | - | - |
| `__init__ (method of Rg)` | 195-202 | Stops on an empty list. Sorts the records by launch time and interval, calls `val` for each, stores `lo`, `hi`, `med`, `n`, `procs`, `np`. | `need`, `val`, `median` | - |
| `txt (method of Rg)` | 204-205 | Returns the text `lowest to highest` with 2 decimals. | `f2` | - |
| `overlaps (method of Rg)` | 207-208 | True when this range and the other range share at least one value. | - | - |
| `nearest (method of Rg)` | 210-214 | Distance of the nearest ends of two ranges. Above 0 when this range is the higher one. 0 when the ranges overlap. | `Rg.overlaps` | - |
| `farthest (method of Rg)` | 216-217 | Distance of the farthest ends of two ranges: the larger of the two differences highest minus lowest. | - | - |
| `plural` | 220-221 | Returns a count with its word in singular or plural, for example `1 process` or `3 processes`. | - | - |
| `signed` | 224-226 | Returns a value with 2 decimals and its sign. A value that rounds to zero becomes `0`. | `q` | - |
| `facts_complete` | 230-231 | True when the text of FACTS.md holds the title of section 7 and the phrase `Output files of this sheet`. | - | - |
| `sel` | 242-257 | Returns the interval records whose fields match all keyword arguments. A value can be one value, a list of allowed values or a test function. | - | - |
| `expect` | 260-265 | Stops unless a selection has exactly `n` records from exactly `nproc` processes, all with 120 threads. Returns the selection. | `need` | - |
| `src` | 359-374 | Source text for a tooltip: csv file and line numbers of the records. For bwx records it adds that the rate sums the thread rows. | `need`, `one` | - |
| `one (inside src)` | 367-370 | Returns the text for one csv file: its path and its line numbers. | - | - |
| `hm` | 377-378 | Formats a UTC time stamp as `HH:MM UTC`, with the date in front when `date` is true. | - | - |
| `n7200` | 381-398 | Text of n for records of the 7200 MT/s boot: intervals (or pairs) / processes / sessions / 1 boot. | `plural` | - |
| `n8000` | 401-403 | Text of n for 8000 MT/s records: intervals (or pairs) / processes / 1 boot. | `plural` | - |
| `pairs_in_process` | 407-414 | Pairs each load-only interval with the old-kernel interval of the same process and round. Stops unless exactly one such interval exists. | `need` | - |
| `drop` | 417-418 | Drop in percent: (1 - new / old) x 100. | `D` | - |
| `drops_of` | 421-422 | Returns the drop of every pair, computed from the `val` of its two intervals. | `drop`, `val` | - |
| `drop_txt` | 425-427 | Text of a list of drops: the lowest and the highest with 1 decimal, or one value when both are printed equal. | `f1` | - |
| `a_pair` | 444-448 | Part A, one round: the ranges of the 3 intervals of the old process and of the new process, and the drop between their medians. | `Rg`, `need`, `drop` | - |
| `width_pct` | 476-478 | Width of a range in percent of its lower end. | - | - |
| `wording` | 481-482 | Returns the fixed text `no difference seen` when two ranges overlap, and the fixed text for a difference when they do not. | `Rg.overlaps` | - |
| `one_process` | 531-536 | Returns the text `session s, round r` when the records are the 3 intervals of one part A process. Else it stops. | `need` | - |
| `md_sections` | 556-566 | Splits the text of FACTS.md at its headings of level 2 and 3. Returns a dictionary from section number to section text. | - | - |
| `md_tables` | 569-583 | Parses the Markdown tables of a text. Each table row becomes a dictionary from column title to cell text. | - | - |
| `col` | 592-595 | Returns the cell of a table row whose column title starts with a given text. Stops unless exactly one column matches. | `need` | - |
| `facts_row` | 598-607 | Returns the first table row of a FACTS.md section for which the test function is true. Stops when no row matches. | `md_tables`, `stop` | - |
| `rng_of` | 610-613 | Reads the text `number to number` from a table cell and returns the two numbers. Stops when the cell holds no range. | `need` | - |
| `near` | 616-617 | True when two numbers differ by at most the tolerance. | `D` | - |
| `xc_range` | 620-623 | Adds a check: a computed range, rounded to the tolerance, against the range in a FACTS.md table cell. | `rng_of`, `check`, `near`, `q` | - |
| `xc_val` | 626-630 | Adds a check: a computed value, rounded to the tolerance, against the first number of a FACTS.md table cell. | `need`, `check`, `near`, `q` | - |
| `xc_text` | 633-637 | Adds a check: a number with the given unit, equal within the tolerance, stands in the text of a FACTS.md section. The sign is ignored. | `check`, `near`, `q`, `D` | - |
| `xc_text_range` | 640-643 | Adds a check: a text `low to high`, equal within the tolerance, stands in the text of a FACTS.md section. | `check`, `near`, `q` | - |
| `xc_drops` | 646-649 | Adds a check: the lowest and highest computed drop against the columns `Smallest drop` and `Largest drop` of a FACTS.md row, to 0.1. | `col`, `check`, `near`, `q`, `f1` | - |
| `T34 (lambda)` | 653-653 | Lambda: the row of FACTS.md section 3.4 for a part and a pair text. | `facts_row` | - |
| `G33 (lambda)` | 660-660 | Lambda: the row of FACTS.md section 3.3 whose column `Group` starts with a text. | `facts_row` | - |
| `R42 (lambda)` | 684-684 | Lambda: the row of FACTS.md section 4.2 whose column `Row` starts with a name and that has a range column. | `facts_row` | - |
| `C42 (lambda)` | 685-685 | Lambda: the comparison row of FACTS.md section 4.2 for a 7200 MT/s row and an 8000 MT/s range. | `facts_row` | - |
| `R44 (lambda)` | 712-712 | Lambda: the row of FACTS.md section 4.4 whose column `Row` starts with a name and that has a range column. | `facts_row` | - |
| `C44 (lambda)` | 713-713 | Lambda: the comparison row of FACTS.md section 4.4 for a 7200 MT/s row and an 8000 MT/s range. | `facts_row` | - |
| `X45 (lambda)` | 753-753 | Lambda: the range cell of the row of FACTS.md section 4.5 whose column `Row` starts with a name. | `facts_row` | - |
| `vrow` | 773-776 | Returns the one verdict record of `verdicts.q2_rows` with the given part, kernel, 7200 MT/s row and 8000 MT/s scope. Stops otherwise. | `need` | - |
| `xv` | 779-783 | Adds a check: two computed ranges, n, process counts, overlap and distance against one verdict record, to 0.001 GB/s. | `near`, `Rg.overlaps`, `check` | - |
| `addref` | 815-818 | Adds one entry to the reference list `REFS`. Stops when the path does not exist. | `need` | - |
| `ref` | 821-825 | Returns the HTML mark for one or more reference keys. `number_refs` fills in the numbers later. Stops on an unknown key. | `need` | - |
| `number_refs` | 828-838 | Numbers the references in the order of first use and writes the reference list into the page. Returns the page and the keys never cited. | `esc` | - |
| `state_lines` | 847-859 | Parses the state lines of a run log: line number, time, boot id, MemTotal, 1-minute load, logins, marker file, processes per user. | `lines_of` | - |
| `launch_window` | 944-950 | Returns the launch time and the end time of one process, from its `launch` line and its `rc 0` line in launches.txt. | `lines_of`, `need` | - |
| `hw_in` | 953-954 | Returns the hardware error records of the journal on one day between two times, both ends included. | - | - |
| `a_headers` | 972-980 | Returns line number, launch time and text of every process header line of the csv file of a part A record. | `file_lines`, `need` | - |
| `secs` | 983-985 | Converts a time `HH:MM:SS` to seconds since midnight. | - | - |
| `clock` | 1022-1026 | Adds seconds to a time `HH:MM:SS` and returns the new time, rounded to a whole second. | - | - |
| `set_records` | 1047-1061 | Returns the firmware settings that a set.txt file marks as modified, and the time of its first line. | `lines_of` | - |
| `canon (lambda)` | 1074-1074 | Lambda: the sorted JSON texts of the entries of a settings list, to compare two lists without their order. | - | - |
| `proc_list` | 1100-1114 | Returns the time of line 1 and the rows (line, user, %CPU, command) of the process list in an env.txt file. | `lines_of`, `need` | - |
| `mem_line` | 1149-1153 | Returns the line number and the second number of the one line `Memory: ...K/...K available` of a kernel log. | `need` | - |
| `spec_line` | 1178-1185 | Returns the name, the arguments and the kernel sequence of the one argument line of a spec file. | `lines_of`, `need` | - |
| `launch_args` | 1188-1192 | Returns the arguments of the launch line of one process in launches.txt of a result folder. | `lines_of`, `need` | - |
| `no_seq (lambda)` | 1197-1197 | Lambda: replaces the kernel sequence of an argument line by `X`. | - | - |
| `bwx_header` | 1235-1252 | Record of runner bwx: finds the header lines of its process. Stops unless tag, launch time, load, start option and counter setting agree. | `file_lines`, `need`, `D` | - |
| `klog_boot` | 1289-1296 | Returns the first and last time, the module count and its line number of a saved kernel log of 2026-11-17. | `lines_of`, `need` | - |
| `strip_tags` | 1484-1485 | Removes the reference marks and all HTML tags from a text. | - | - |
| `P` | 1488-1490 | Returns one HTML paragraph and adds its text to `PROSE` for the word count. | - | - |
| `UL` | 1493-1495 | Returns one HTML bullet list and adds its items to `PROSE` for the word count. | - | - |
| `table` | 1501-1512 | Returns the HTML of one table. A row that is a text becomes a group title row. A column title with `#` is right-aligned. | - | - |
| `small` | 1515-1516 | Wraps a text in small type. | - | - |
| `T` | 1520-1522 | Returns one SVG text element. | `esc` | - |
| `marker` | 1529-1534 | Returns the SVG circle of one dot of figure 1: hollow for 8000 MT/s, filled for 7200 MT/s. | - | - |
| `kernel_name` | 1537-1542 | Returns the display name of the kernel of the first record, for example `oldread (old read kernel)`. | - | - |
| `dot_title` | 1545-1548 | Tooltip text of one dot of figure 1: median, interval values, n and the source rows. | `f2`, `kernel_name`, `plural`, `src` | - |
| `f1_row` | 1551-1552 | Packs the fields of one row of figure 1 into a dictionary. | - | - |
| `bwx_row` | 1555-1558 | One row of figure 1 for bwx12 records: pairs the intervals, builds the two ranges and the drops. | `pairs_in_process`, `f1_row`, `Rg`, `drops_of` | - |
| `fig1` | 1593-1678 | Draws figure 1 (dumbbell chart, 21 rows) as SVG in one of three layouts: wide, mid or narrow. | `drawn`, `T`, `drop_txt`, `esc`, `plural`, `src`, `dot_title`, `marker`, `f2` | - |
| `drawn (inside fig1)` | 1602-1615 | Mid layout only: breaks a note of more than 44 characters after its comma. | `need` | - |
| `beeswarm` | 1682-1692 | Returns a vertical offset per dot, so that dots of one row with near x values do not cover each other. | - | - |
| `p_row` | 1695-1708 | One row of figure 2: the range of its records, and a note that says where the row lies relative to the grey band. | `Rg`, `Rg.nearest`, `f2` | - |
| `plain_notes` | 1711-1713 | Returns the notes of a row as plain text, without the marks `!` and `~` and with a space for each line break mark. | - | - |
| `note_lines` | 1716-1718 | Returns every drawn line of the notes of a row, each with a flag for bold type. | - | - |
| `hit_cell` | 1725-1749 | Hover area of a figure 2 dot: the part of a circle (radius 12 px) nearer to this dot than to any other. | `need` | - |
| `poly_area` | 1752-1753 | Area of a polygon in square pixels. | - | - |
| `panel` | 1756-1862 | Draws one panel of figure 2: a dot with tooltip per interval, a grey band per block. Stops when two dots lie within 5.2 px. | `note_lines`, `beeswarm`, `need`, `hit_cell`, `poly_area`, `esc`, `T`, `Rg.txt`, `plain_notes`, `kernel_name`, `f2`, `val`, `plural`, `src` | - |
| `secs_txt` | 1865-1866 | Returns the interval length of the first record as text, for example `6 s`, from the field `min_ms`. | - | - |
| `l_rows` | 1869-1873 | Returns the four rows L-1 to L-4 of figure 2 for one kernel. | `p_row`, `secs_txt` | - |
| `band_title` | 1876-1878 | Tooltip text of a grey band: what it shows, its range, n and its source files. | `Rg.txt` | - |
| `a_new_block` | 1905-1915 | Returns the block of figure 2 for bw_new read of one round: rows A-1 and A-2, then sessions 1 to 3. | `p_row`, `Rg.txt`, `n8000`, `band_title` | - |
| `panel_rows` | 1938-1939 | Lists (block, group, row) for every row of a panel. By default it lists only the rows of groups with a band. | - | - |
| `legend` | 1963-1964 | Returns the HTML of a figure legend. | - | - |
| `sw_dot` | 1967-1969 | Returns the small SVG dot of one legend entry. | - | - |
| `lab` | 1992-1994 | Returns a row label: the name, and its notes under it in small type. | `small` | - |
| `only` | 1997-2000 | Returns the one distinct value of a list. Stops unless the list holds exactly one distinct value. | `need` | - |
| `q1_table` | 2003-2045 | Builds Table 1: per part the lowest and highest drop, the ranges of both kernels, and n. | `only`, `need`, `Rg`, `row`, `ref`, `n7200`, `f1`, `med_rng`, `small`, `per_round`, `plural`, `hm`, `n8000`, `where`, `table` | - |
| `row (inside q1_table)` | 2004-2006 | One table row for a key of `Q1`: label, lowest and highest drop, the two ranges, n. | `f1`, `Rg.txt` | - |
| `med_rng (inside q1_table)` | 2008-2010 | Text `lowest to highest` of the process medians of part A pairs, for one round or for all. | `f2` | - |
| `per_round (inside q1_table)` | 2012-2013 | Cell text with the range of the bw_new medians of round 1 and of round 2. | `med_rng`, `small` | - |
| `where (inside q1_table)` | 2018-2022 | Text that names the sessions of the processes of one kernel order of part C. | - | - |
| `tnote` | 2048-2050 | Returns a note under a table: a first text, then one bullet per further point. | - | - |
| `cmp_cell` | 2053-2054 | Returns a table cell: a range, and n under it in small type. | `Rg.txt`, `small` | - |
| `q2_table` | 2079-2181 | Builds Table 2: one row per comparison of a 7200 MT/s row with 8000 MT/s rows (ranges, n, overlap, distance, wording), and its notes. | `ref`, `f1`, `width_pct`, `cmp_cell`, `n7200`, `n8000`, `f2`, `one_process`, `lab`, `Rg.txt`, `signed`, `small`, `Rg.nearest`, `Rg`, `Rg.overlaps`, `need`, `tnote`, `plural`, `q`, `table` | - |
| `visits_table` | 2184-2210 | Builds Table 3: the three visits of the part L line in the 7200 MT/s boot, with launch time, start state and ranges. | `D`, `need`, `n7200`, `lab`, `ref`, `f2`, `Rg.txt`, `table` | - |
| `dist_table` | 2213-2216 | Builds Table 4: three kinds of distance of part L (asmread) above the 8000 MT/s pool and above F72d12. | `f2`, `table` | - |
| `load_table` | 2219-2252 | Builds Table 6: the 1-minute load average at the first launch of every step and at the launches of the earlier rows. | `sel`, `f2`, `D`, `need`, `small`, `plural`, `table` | - |
| `detail_fig1` | 2255-2263 | Builds the table view of figure 1: per row the two medians, the interval values and the drop. | `lab`, `esc`, `f2`, `drop_txt`, `table` | - |
| `detail_fig2` | 2266-2275 | Builds the table view of figure 2: per row n and the sorted interval values. | `lab`, `esc`, `plain_notes`, `f2`, `table` | - |
| `facts_words` | 2279-2287 | Reads the word list of FACTS.md. Returns a dictionary from term to definition. | `need` | - |
| `fw` | 2293-2303 | Returns one definition of the FACTS.md word list for the page: `this sheet` becomes `this page`, reference marks are removed. | `need`, `esc` | - |
| `nw` | 2399-2401 | Wraps a number with its unit so that it does not break across two lines. | - | - |
| `cl` | 2498-2500 | Returns a bullet list for use inside one table cell. | - | - |
| `state_table` | 2503-2570 | Builds Table 5: the machine state. Each row holds a fact, its proof from the raw files, and its limit. | `ref`, `need`, `cl`, `Rg.txt`, `n8000`, `secs`, `f2`, `val`, `n7200`, `Rg.nearest`, `table` | - |
| `build` | 2677-2781 | Builds the whole HTML page as one text: Short version, word list, sections 1 to 4 with figures and tables, reference list. | `P`, `f2`, `ref`, `panel`, `fig1`, `q1_table`, `detail_fig1`, `f1`, `q2_table`, `visits_table`, `n7200`, `n8000`, `dist_table`, `detail_fig2`, `state_table`, `load_table` | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File header: input, output and rules</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  #!/usr/bin/env python3
   2  """make_report.py - builds the report page of the whole-chip read rerun at 7200 MT/s.
   3
   4  Output: crb/new-test-kernel/whole-chip-rerun-7200.html (one self-contained HTML file).
   5  Input:  facts.json of this folder (records "intervals", meta.launches, meta.rerun).
   6
   7  Rules of this script:
   8  - Every measured number of the page is computed here from the interval records. No measured number is typed.
   9  - facts.json holds the bwx rates rounded to 0.001 GB/s. For the last digit at 0.01 GB/s the function val() sums the
  10    thread rows of the raw csv that a record names, and it stops when that sum does not round to the record value.
  11  - Record counts are asserted. A wrong count stops the build.
  12  - The computed values are compared with FACTS.md and with the "verdicts" of facts.json.
  13    A mismatch is printed in the self-check list, the page is not written, and the exit status is 1.
  14  - The facts of the section "Machine state" are checked in the raw files (read only) before they are written.
  15  - Every record must name its row in the raw csv file: the interval row with its rate (part A), or the interval row
  16    and the 120 thread rows after it (bwx12). A tooltip cites that row.
  17  - Figure 1 is drawn in three layouts (940, 726 and 386 px wide). The style block shows the one that fits the window.
  18  Python 3 standard library only. Edit this file, never the HTML.
  19  """</pre></td><td valign="top">Header comment of the script. It names the output (one HTML page) and the input (<code>facts.json</code>), and it lists the rules of the script:<ul><li>No measured number is typed. Each one is computed from the interval records.</li><li>For a bwx record, <code>val</code> (line 176) sums the thread rows of the raw csv file that the record names.</li><li>A wrong record count stops the build.</li><li>A mismatch with <code>FACTS.md</code> or with the verdict records of <code>facts.json</code> is printed in the self-check list. The page is then not written, and the exit status is 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  20  import html
  21  import json
  22  import math
  23  import os
  24  import re
  25  import sys
  26  import time
  27  from decimal import Decimal, ROUND_HALF_UP</pre></td><td valign="top">Modules of the Python standard library. No other package is needed. <code>Decimal</code> and <code>ROUND_HALF_UP</code> are used for rounding (function <code>q</code>, line 90).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  28
  29  S = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"
  30  R = "/home/jhan/workspace/titan/cache-perf/crb/results"
  31  OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"
  32  EARLIER = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html"</pre></td><td valign="top">Fixed paths. <code>S</code> is the scratch folder of the rerun, which holds <code>facts.json</code> and <code>FACTS.md</code>. <code>R</code> is the results folder with the raw csv files. <code>OUT</code> is the page that the script writes, and <code>EARLIER</code> is the earlier report page.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  33
  34  BLUE, ORANGE = "#2a78d6", "#eb6834"          # old read kernel, load-only loop (validated, see palette check)
  35  INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
  36  BAND, BAND_EDGE, LINK = "#ebe9e0", "#b9b7ae", "#8d8c86"</pre></td><td valign="top">Colours of the page as hexadecimal codes. The comment assigns <code>BLUE</code> to the old read kernel and <code>ORANGE</code> to the load-only loop.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  37
  38  CHECKS = []          # (ok, text)
  39  PROSE = []           # visible prose outside tables, captions, word list and references (for the word count)
  40
  41</pre></td><td valign="top">Two lists that start empty. <code>CHECKS</code> collects the lines of the self-check list, each as a pair (pass or fail, text). <code>PROSE</code> collects the prose of the page for the word count. The comment names what is not counted: tables, captions, the word list and the references.</td></tr>
<tr><td colspan="2"><b>Function <code>stop</code>: end the script with a message</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  42  def stop(msg):
  43      sys.exit("make_report.py: STOP: " + msg)
  44
  45</pre></td><td valign="top"><code>sys.exit</code> with a text prints the text to the error output and ends the script with exit status 1. No later line runs. The page is written only at the end of the file. So a stop leaves the page on disk as it was.</td></tr>
<tr><td colspan="2"><b>Function <code>need</code>: hard assertion</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  46  def need(cond, msg):
  47      """Hard assertion. A wrong record count or a failed raw-file check stops the build."""
  48      if not cond:
  49          stop(msg)
  50
  51</pre></td><td valign="top">When <code>cond</code> is false, it calls <code>stop</code> with the message. When <code>cond</code> is true, nothing happens. The script uses it to assert record counts, the content of raw csv rows, and the expected results of comparisons.</td></tr>
<tr><td colspan="2"><b>Function <code>check</code>: one line of the self-check list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  52  def check(ok, text):
  53      CHECKS.append((bool(ok), text))
  54
  55</pre></td><td valign="top">Appends the pair (pass or fail, text) to <code>CHECKS</code>. The script continues after a failed check. The end of the file prints the list. It writes the page only when every line passed.</td></tr>
<tr><td colspan="2"><b>Function <code>grouped</code>: join many checks into one line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  56  def grouped(label, start):
  57      """Replace the checks added since index start by one line: n of m equal, and the first mismatch."""
  58      sub = CHECKS[start:]
  59      del CHECKS[start:]
  60      bad = [t for ok, t in sub if not ok]
  61      check(not bad, f"{label}: {len(sub) - len(bad)} of {len(sub)} comparisons equal" + ("" if not bad else ". First mismatch: " + bad[0]))
  62
  63</pre></td><td valign="top">Removes from <code>CHECKS</code> all checks that were added since position <code>start</code>. It adds one check in their place. The new line states how many of the comparisons were equal, and it passes only when all were equal. After a failure the line also holds the text of the first failed comparison.</td></tr>
<tr><td colspan="2"><b>Function <code>read_retry</code>: read a file, up to 10 tries</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  64  def read_retry(path, parse, complete=lambda t: True):
  65      """Another agent rebuilds facts.json and FACTS.md from time to time. Retry a failed or partial read."""
  66      last = None
  67      for _ in range(10):
  68          try:
  69              with open(path, encoding="utf-8") as f:
  70                  text = f.read()
  71              if complete(text):
  72                  return parse(text)
  73              last = "file is not complete"
  74          except (OSError, ValueError) as e:
  75              last = e
  76          time.sleep(1.5)
  77      stop(f"cannot read {path}: {last}")
  78
  79</pre></td><td valign="top">Reads the whole file and returns <code>parse(text)</code>. It waits 1.5 s and tries again in three cases: the file cannot be read (<code>OSError</code>), the parse fails (<code>ValueError</code>), or <code>complete(text)</code> is false. After 10 failed tries it calls <code>stop</code>. The comment gives the reason: another agent rebuilds the two input files from time to time, and a read can then find a file that is only partly written.</td></tr>
<tr><td colspan="2"><b>Function <code>lines_of</code>: the lines of a text file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  80  def lines_of(path):
  81      with open(path, encoding="utf-8", errors="replace") as f:
  82          return f.read().splitlines()
  83
  84</pre></td><td valign="top">Returns the lines of a file as a list, without the line ends. A byte that is not valid UTF-8 is replaced by a replacement character. So the read does not fail on such a byte.</td></tr>
<tr><td colspan="2"><b>Function <code>D</code>: convert a number to <code>Decimal</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  85  # ------------------------------------------------------------------ numbers
  86  def D(x):
  87      return x if isinstance(x, Decimal) else Decimal(str(x))
  88
  89</pre></td><td valign="top">Returns a <code>Decimal</code> unchanged. Any other number is converted through its text form. So the floating-point number 467.83 becomes exactly the decimal value 467.83.</td></tr>
<tr><td colspan="2"><b>Function <code>q</code>: round to a step</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  90  def q(x, places="0.01"):
  91      return D(x).quantize(Decimal(places), rounding=ROUND_HALF_UP)
  92
  93</pre></td><td valign="top">Rounds <code>x</code> to the step <code>places</code>, which is 0.01 by default. A value exactly between two steps is rounded away from zero: 462.295 becomes 462.30. The functions <code>f2</code>, <code>f1</code> and <code>signed</code> call it.</td></tr>
<tr><td colspan="2"><b>Functions <code>f2</code> and <code>f1</code>: number to text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  94  def f2(x):
  95      return f"{q(x):.2f}"
  96
  97
  98  def f1(x):
  99      return f"{q(x, '0.1'):.1f}"
 100
 101</pre></td><td valign="top"><code>f2</code> rounds with <code>q</code> to 0.01 and returns the text with 2 decimals. The script prints rates in GB/s with it. <code>f1</code> rounds to 0.1 and returns the text with 1 decimal. The script prints percent values with it.</td></tr>
<tr><td colspan="2"><b>Function <code>median</code>: the middle value</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 102  def median(vals):
 103      s = sorted(vals)
 104      n = len(s)
 105      return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
 106
 107</pre></td><td valign="top">Sorts the values. For an odd count it returns the middle value. For an even count it returns the mean of the two middle values. The result is not rounded here.</td></tr>
<tr><td colspan="2"><b>Function <code>esc</code>: make a text safe for HTML</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 108  def esc(s):
 109      return html.escape(str(s), quote=True)
 110
 111</pre></td><td valign="top">Replaces the characters <code>&amp;</code>, <code>&lt;</code>, <code>&gt;</code>, <code>"</code> and <code>'</code> by their HTML codes. So a value cannot change the structure of the page.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 112  _TROWS = {}
 113  _FILES = {}
 114
 115</pre></td><td valign="top">Two dictionaries that start empty. <code>_FILES</code> keeps the lines of every csv file that <code>file_lines</code> has read. <code>_TROWS</code> keeps the T rows of every csv file that <code>t_rows</code> has read, grouped by interval. So <code>file_lines</code> reads each csv file from disk only once.</td></tr>
<tr><td colspan="2"><b>Function <code>file_lines</code>: the csv file of a record</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 116  def file_lines(rec):
 117      """The lines of the csv file that a record names."""
 118      key = (rec["folder"], rec["file"])
 119      if key not in _FILES:
 120          _FILES[key] = lines_of(os.path.join(R, rec["folder"].replace("R/", "", 1), rec["file"]))
 121      return _FILES[key]
 122
 123</pre></td><td valign="top">A record names its csv file with two fields: <code>folder</code>, for example <code>R/w120-T72L1-20261117T221329Z</code>, and <code>file</code>, for example <code>a6456.csv</code>. The function removes the first <code>R/</code> from <code>folder</code> and joins the results folder <code>R</code> (line 30), the rest and <code>file</code> to one path. It reads the file with <code>lines_of</code> and keeps the lines in <code>_FILES</code>. Line 1 of the file is element 0 of the list.</td></tr>
<tr><td colspan="2"><b>Function <code>t_rows</code>: the 120 thread rows of a bwx12 record</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 124  def t_rows(rec):
 125      """The T rows (one per thread) of the interval of a bwx record: (cpu, bytes, elapsed_s, t_start_s, t_end_s, line number).
 126      They must be the 120 lines directly after the I row that the record names."""
 127      key = (rec["folder"], rec["file"])
 128      if key not in _TROWS:
 129          d = {}
 130          for no, line in enumerate(file_lines(rec), 1):
 131              if line.startswith("T,"):
 132                  p = line.split(",")
 133                  need(len(p) == 13, f"{key}: a T row without 13 fields")
 134                  d.setdefault((int(p[1]), int(p[2]), p[3]), []).append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))
 135          _TROWS[key] = d
 136      tl = _TROWS[key].get((rec["round"], rec["pos"], rec["kernel"]), [])
 137      need(len(tl) == 120, f"{key}: no 120 T rows for round {rec['round']} position {rec['pos']} {rec['kernel']}")
 138      need([t[5] for t in tl] == list(range(rec["line"] + 1, rec["line"] + 121)), f"{key}: the T rows are not the 120 lines after line {rec['line']}")
 139      return tl
 140
 141</pre></td><td valign="top">Returns the T rows of the interval of one bwx12 record. Each T row holds one thread.<ul><li>First call for a csv file: every line that starts with <code>T,</code> is split at the commas into <code>p</code>. The script stops when such a line does not have 13 fields.</li><li>The rows are grouped by round, position and kernel: <code>p[1]</code>, <code>p[2]</code>, <code>p[3]</code>. Python counts from 0. So <code>p[1]</code> is field 2.</li><li>Six values are kept per row: <code>p[5]</code> cpu, <code>p[6]</code> bytes, <code>p[7]</code> elapsed_s, <code>p[9]</code> t_start_s, <code>p[10]</code> t_end_s, and the line number. The names are the column names of the csv header [Ref4]. The fields tid, t_sched_s, passes and flags are not read.</li><li>Then the function takes the rows with the round, position and kernel of the record. The script stops unless they are exactly 120.</li><li>The script also stops unless these rows are the 120 lines directly after the I row of the record (field <code>line</code>).</li><li>The key holds no process number. If a file held the same round, position and kernel in two processes, the count would be above 120 and the script would stop.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>t_rows_block</code>: the same for the older runner bwx</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 142  def t_rows_block(rec):
 143      """The T rows of an interval record of the older runner bwx, as t_rows() returns them.
 144      A csv file of that runner holds several processes. So the rows are taken by their place:
 145      they must be the 120 lines directly after the I row that the record names, with its round, position and kernel."""
 146      fl = file_lines(rec)
 147      where = f"{rec['folder']}/{rec['file']} line {rec['line']}"
 148      tl = []
 149      for no in range(rec["line"] + 1, rec["line"] + 121):
 150          p = fl[no - 1].split(",")
 151          need(len(p) == 13 and p[0] == "T" and (int(p[1]), int(p[2]), p[3]) == (rec["round"], rec["pos"], rec["kernel"]),
 152               f"{where}: line {no} is not a T row of this interval")
 153          tl.append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))
 154      need(len(fl) == rec["line"] + 120 or not fl[rec["line"] + 120].startswith("T,"), f"{where}: more than 120 T rows follow the I row")
 155      return tl
 156
 157</pre></td><td valign="top">Returns the T rows of one record of the older runner bwx, in the form of <code>t_rows</code>. A csv file of that runner holds several processes. So the rows are taken by their place in the file.<ul><li>It reads the 120 lines directly after the I row of the record (field <code>line</code>).</li><li>The script stops unless each of these lines has 13 fields, <code>T</code> in the first field, and the round, position and kernel of the record.</li><li>The script also stops when the next line after these 120 starts with <code>T,</code>. So exactly 120 T rows follow the I row.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>i_row_rate</code>: the rate printed in the I row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 158  def i_row_rate(rec):
 159      """The rate that the interval row (I row) of a bwx record prints, in GB/s. The row must be the row of this record."""
 160      p = file_lines(rec)[rec["line"] - 1].split(",")
 161      need(len(p) == 9 and p[0] == "I" and (int(p[1]), int(p[2]), p[3], int(p[5])) == (rec["round"], rec["pos"], rec["kernel"], 120),
 162           f"{rec['folder']}/{rec['file']} line {rec['line']}: not the I row of round {rec['round']} position {rec['pos']} {rec['kernel']}")
 163      return Decimal(p[8])
 164
 165</pre></td><td valign="top">Splits the line that the record names (field <code>line</code>) at the commas. The script stops unless the line has 9 fields, <code>I</code> in the first field, the round, position and kernel of the record, and 120 in the field threads (<code>p[5]</code>). The function returns <code>p[8]</code>, the field aggregate_GBps, as a <code>Decimal</code>. The runner computed this printed rate as the bytes of all threads divided by the longest elapsed time of one thread [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>file_process</code>: check the csv row of a part A record</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 166  def file_process(rec):
 167      """Part A: the number of the process inside its csv file (1 = first), counted from the header lines ("-- ...") up to the record.
 168      The row of the record must hold the rate of the record."""
 169      fl = file_lines(rec)
 170      p = fl[rec["line"] - 1].split(",")
 171      need(len(p) == 10 and p[0] == rec["kernel"] and int(p[1]) == 120 and int(p[3]) == rec["interval"] and D(p[6]) == D(rec["GBps"]),
 172           f"{rec['folder']}/{rec['file']} line {rec['line']}: not the interval row of this record")
 173      return sum(1 for l in fl[:rec["line"]] if l.startswith("-- "))
 174
 175</pre></td><td valign="top"><ul><li>It splits the line that the record names (field <code>line</code>) at the commas into <code>p</code>.</li><li>The script stops unless the line has 10 fields, <code>p[0]</code> is the kernel of the record, <code>p[1]</code> (threads) is 120, <code>p[3]</code> (rep) is the interval number of the record, and <code>p[6]</code> (aggregate_GBps) equals the field <code>GBps</code> of the record [Ref3].</li><li>The row holds no name of a binary, and this function does not compare the binary.</li><li>It returns the number of lines that start with <code>-- </code> from line 1 of the file up to this row. Each such line is the header line of one process. So the result is the number of the process inside the file, counted from 1.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>val</code>: the rate of one record in GB/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 176  def val(rec):
 177      """Rate of an interval record in GB/s.
 178      Part A: the record holds the value of the csv (2 decimals).
 179      bwx runners: facts.json holds the rate rounded to 0.001 GB/s, and FACTS.md rounds the unrounded value to 0.01 GB/s.
 180      For the same last digit this function sums the 120 T rows that the record names (the method of build_facts.py)
 181      and stops when the sum does not round to the value of the record."""
 182      if rec["part"] == "A":
 183          return D(rec["GBps"])
 184      if "_exact" not in rec:
 185          tl = t_rows(rec) if rec["binary"] == "bwx12" else t_rows_block(rec)
 186          tot =sum(b / e / 1e9 for c, b, e, *_ in tl if c &lt; 64) + sum(b / e / 1e9 for c, b, e, *_ in tl if c &gt;= 64)
 187          need(abs(round(tot, 3) - rec["GBps"]) &lt; 1e-9, f"{rec['folder']}/{rec['file']} line {rec['line']}: sum of the T rows {tot:.6f} is not the record value {rec['GBps']}")
 188          rec["_exact"] = Decimal(repr(round(tot, 6)))
 189      return rec["_exact"]
 190
 191</pre></td><td valign="top">Returns the rate of one interval record in GB/s. The class <code>Rg</code> and the function <code>drops_of</code> take their rates from here.<ul><li>Part A record: it returns the field <code>GBps</code> of the record. Nothing is summed. This is the rate that the benchmark printed in the csv row with 2 decimals: the bytes of all threads divided by the longest elapsed time of one thread [Ref3].</li><li>Other records: it takes the 120 T rows from <code>t_rows</code> when the binary is bwx12, else from <code>t_rows_block</code>.</li><li>Line 186 computes <code>bytes / elapsed_s / 1e9</code> for each T row: the rate of one thread in GB/s, with 1 GB = 1e9 bytes. So each thread is divided by its own elapsed time. This formula differs from the formula of part A.</li><li>It adds the rates of the threads with a CPU number below 64 (mesh 0), then the rates of the other threads (mesh 1), then the two sums. All 120 rows are in the sum. <code>facts_data.py</code> adds in the same order, and <code>build_facts.py</code> (named in the comment of lines 177 to 181) takes its sum from there.</li><li>Line 187: the script stops unless the sum, rounded to 3 decimals, equals the field <code>GBps</code> of the record.</li><li>Line 188 stores the sum, rounded to 6 decimals, in the record as <code>_exact</code>. Every later call returns the stored value. Example: 462.300017 GB/s for the first interval of part L in session 1, where the I row prints 462.29 GB/s [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Class <code>Rg</code>: the range of a group of records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 192  class Rg:
 193      """Lowest-to-highest range of a list of interval records."""
 194
 195      def __init__(self, recs):
 196          need(len(recs) &gt; 0, "empty selection")
 197          self.recs = sorted(recs, key=lambda r: (r["launch_utc"], r["interval"]))
 198          self.v = [val(r) for r in self.recs]
 199          self.lo, self.hi, self.med = min(self.v), max(self.v), median(self.v)
 200          self.n = len(recs)
 201          self.procs = sorted({r["proc_key"] for r in recs})
 202          self.np = len(self.procs)
 203</pre></td><td valign="top">An <code>Rg</code> object holds the rates of a list of records and their lowest-to-highest range.<ul><li>The script stops when the list is empty.</li><li><code>recs</code>: the records, sorted by the launch time of their process (<code>launch_utc</code>) and then by the interval number.</li><li><code>v</code>: the rate of each record from <code>val</code>, in this order.</li><li><code>lo</code>, <code>hi</code>, <code>med</code>: the lowest rate, the highest rate and the median of <code>v</code>. No record of the list is left out.</li><li><code>n</code>: the number of records, which is the number of intervals.</li><li><code>procs</code> and <code>np</code>: the different values of the field <code>proc_key</code>, and their count, which is the number of processes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 204      def txt(self):
 205          return f"{f2(self.lo)} to {f2(self.hi)}"
 206
 207      def overlaps(self, other):
 208          return self.lo &lt;= other.hi and other.lo &lt;= self.hi
 209</pre></td><td valign="top"><code>txt</code> returns the text <code>lowest to highest</code>, each rate with 2 decimals. <code>overlaps</code> is true when the two ranges share at least one value. Two ranges that share exactly one value count as overlapping. The test uses the rates as <code>val</code> returns them (6 decimals for a bwx record), not the rounded text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 210      def nearest(self, other):
 211          """Distance of the nearest ends, + when self is the higher range. 0 when the ranges overlap."""
 212          if self.overlaps(other):
 213              return Decimal(0)
 214          return self.lo - other.hi if self.lo &gt; other.hi else self.hi - other.lo
 215
 216      def farthest(self, other):
 217          return max(self.hi - other.lo, other.hi - self.lo)
 218
 219</pre></td><td valign="top"><code>nearest</code> returns 0 when the two ranges overlap. Else it returns the gap between the two nearest ends in GB/s: above 0 when this range is the higher one, below 0 when it is the lower one. <code>farthest</code> returns the larger of the two differences <code>self.hi - other.lo</code> and <code>other.hi - self.lo</code>. For two ranges that do not overlap, this is the highest end of the higher range minus the lowest end of the lower range.</td></tr>
<tr><td colspan="2"><b>Function <code>plural</code>: a count with its word</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 220  def plural(n, word):
 221      return f"{n} {word}" if n == 1 else f"{n} {word}{'es' if word.endswith('s') else 's'}"
 222
 223</pre></td><td valign="top">Returns the count and the word, for example <code>1 process</code>, <code>3 processes</code> or <code>6 intervals</code>. For a count other than 1 it adds <code>es</code> to a word that ends in <code>s</code>, and <code>s</code> to any other word.</td></tr>
<tr><td colspan="2"><b>Function <code>signed</code>: a value with its sign</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 224  def signed(x):
 225      x = q(x)
 226      return "0" if x == 0 else f"{'+' if x &gt; 0 else '-'}{abs(x):.2f}"
 227
 228</pre></td><td valign="top">Rounds the value to 0.01 with <code>q</code>. It returns <code>0</code> when the rounded value is zero. Else it returns the sign <code>+</code> or <code>-</code> and the value with 2 decimals, for example <code>-1.24</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>facts_complete</code>: is <code>FACTS.md</code> complete</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 229  # ------------------------------------------------------------------ load the facts
 230  def facts_complete(t):
 231      return "Output files of this sheet" in t and "## 7. Files" in t
 232
 233</pre></td><td valign="top">True when the text holds the heading <code>## 7. Files</code> and the phrase <code>Output files of this sheet</code>. In <code>FACTS.md</code> section 7 is the last section, and the phrase is in the last line of the file. So a file that is only partly written fails the test, and <code>read_retry</code> tries again.</td></tr>
<tr><td colspan="2"><b>Load <code>facts.json</code> and <code>FACTS.md</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 234  FJ = read_retry(S + "/facts.json", json.loads)
 235  FMD = read_retry(S + "/FACTS.md", lambda t: t, facts_complete)
 236  IV = FJ["intervals"]
 237  META = FJ["meta"]
 238  RERUN = META["rerun"]
 239  need(len(IV) == META["counts"]["intervals"], "facts.json: number of interval records differs from meta.counts")
 240
 241</pre></td><td valign="top"><ul><li><code>FJ</code> is <code>facts.json</code>, parsed with <code>json.loads</code>. <code>FMD</code> is the text of <code>FACTS.md</code>.</li><li><code>IV</code> is the list of all interval records. The record groups below are selected from this list.</li><li><code>META</code> is the part <code>meta</code> of <code>facts.json</code>, and <code>RERUN</code> is <code>meta.rerun</code>.</li><li>The script stops when the number of records in <code>IV</code> differs from <code>meta.counts.intervals</code>. The file states 793 records [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>sel</code>: select records by field values</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 242  def sel(**kw):
 243      out = []
 244      for r in IV:
 245          ok = True
 246          for k, v in kw.items():
 247              if callable(v):
 248                  ok = v(r[k])
 249              elif isinstance(v, (list, tuple, set)):
 250                  ok = r[k] in v
 251              else:
 252                  ok = r[k] == v
 253              if not ok:
 254                  break
 255          if ok:
 256              out.append(r)
 257      return out
 258
 259</pre></td><td valign="top">Returns the records of <code>IV</code> that pass every test of the call, in the order of <code>IV</code>. Each argument names a record field and gives a test for it. Example: <code>sel(dataset="rerun-L", kernel="oldread", pos=0)</code> returns the records whose field <code>dataset</code> is <code>rerun-L</code>, whose <code>kernel</code> is <code>oldread</code> and whose <code>pos</code> is 0.<ul><li>A plain value: the field must be equal to it.</li><li>A list, tuple or set: the field value must be one of its elements.</li><li>A function: it must return true for the field value.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>expect</code>: assert the size of a group</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 260  def expect(recs, n, nproc, what):
 261      need(len(recs) == n, f"{what}: expected {n} interval records, found {len(recs)}")
 262      got = len({r["proc_key"] for r in recs})
 263      need(got == nproc, f"{what}: expected {nproc} processes, found {got}")
 264      need(all(r["threads"] == 120 for r in recs), f"{what}: a record is not a 120-thread interval")
 265      return recs
 266
 267</pre></td><td valign="top">The script stops unless the list has exactly <code>n</code> records, they come from exactly <code>nproc</code> processes (different values of <code>proc_key</code>), and every record has 120 threads. The function returns the list unchanged. <code>what</code> names the group in the stop message.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 268  LPOOL = ("L-1", "L-2", "L-3", "L-4")
 269  APOOL = ("A-1", "A-2", "A-3")
 270</pre></td><td valign="top">The names of the 8000 MT/s datasets. <code>LPOOL</code> lists the bwx12 rows L-1 to L-4, and <code>APOOL</code> lists the part A rows A-1 to A-3.</td></tr>
<tr><td colspan="2"><b>Record groups: part A at 7200 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 271  # part A, the repeat of the 2026-11-13 test
 272  A_OLD = expect(sel(dataset="rerun-A", binary="bw_old", kernel="read"), 18, 6, "part A, bw_old read")
 273  A_NEW = expect(sel(dataset="rerun-A", binary="bw_new", kernel="read"), 18, 6, "part A, bw_new read")</pre></td><td valign="top"><ul><li><code>A_OLD</code>: dataset <code>rerun-A</code>, binary <code>bw_old</code>, kernel <code>read</code>. This is the old read kernel.</li><li><code>A_NEW</code>: the same with the binary <code>bw_new</code>. This is the new read kernel.</li><li>Each group must have 18 intervals of 6 processes.</li><li>The part A intervals of the kernels write, copy, asmread, asmwrite and asmcopy are not selected.</li></ul></td></tr>
<tr><td colspan="2"><b>Record groups: the part L line at 7200 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 274  # part L and the rows of the same argument line
 275  L_OLD = expect(sel(dataset="rerun-L", kernel="oldread", pos=0), 6, 3, "part L, oldread")
 276  L_ASM = expect(sel(dataset="rerun-L", kernel="asmread", pos=1), 6, 3, "part L, asmread")
 277  I_OLD = expect(sel(dataset="control-I", kernel="oldread", pos=0), 4, 2, "control I, oldread")
 278  I_ASM = expect(sel(dataset="control-I", kernel="asmread", pos=1), 4, 2, "control I, asmread")
 279  F_OLD = expect(sel(dataset="F72d12", kernel="oldread", pos=0), 2, 1, "F72d12, oldread")
 280  F_ASM = expect(sel(dataset="F72d12", kernel="asmread", pos=1), 2, 1, "F72d12, asmread")</pre></td><td valign="top"><ul><li>Three datasets hold runs of the argument line of part L in the 7200 MT/s boot: <code>rerun-L</code> (part L), <code>control-I</code> (control I) and <code>F72d12</code>.</li><li>For each, the group that ends in <code>_OLD</code> holds <code>oldread</code> at position 0, and the group that ends in <code>_ASM</code> holds <code>asmread</code> at position 1.</li><li>Expected size of each group: part L 6 intervals of 3 processes, control I 4 of 2, F72d12 2 of 1.</li><li>The intervals of read_nop96, read_nop256 and read_1pl of these processes are not selected.</li></ul></td></tr>
<tr><td colspan="2"><b>Record groups: part C at 7200 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 281  # part C
 282  C_OLD = expect(sel(dataset="rerun-C", kernel="oldread"), 8, 4, "part C, oldread")
 283  C_READ = expect(sel(dataset="rerun-C", kernel="read"), 8, 4, "part C, read")
 284  C_ASM = expect(sel(dataset="rerun-C", kernel="asmread"), 8, 4, "part C, asmread")
 285  C_READ_AO = expect([r for r in C_READ if r["kernel_before"] == "oldread"], 4, 2, "part C, read after oldread")
 286  C_READ_AA = expect([r for r in C_READ if r["kernel_before"] == "asmread"], 4, 2, "part C, read after asmread")
 287  C_ASM_AR = expect([r for r in C_ASM if r["kernel_before"] == "read"], 4, 2, "part C, asmread after read")
 288  C_ASM_AO = expect([r for r in C_ASM if r["kernel_before"] == "oldread"], 2, 2, "part C, asmread after oldread")
 289  C_ASM_FI = expect([r for r in C_ASM if r["kernel_before"].startswith("none")], 2, 2, "part C, asmread first interval")</pre></td><td valign="top"><ul><li><code>C_OLD</code>, <code>C_READ</code>, <code>C_ASM</code>: all part C intervals of <code>oldread</code>, <code>read</code> and <code>asmread</code>, at any position. Each group must have 8 intervals of 4 processes.</li><li><code>C_READ_AO</code>: the <code>read</code> intervals whose field <code>kernel_before</code> is <code>oldread</code>. These are the 4 intervals of the two cfwd processes.</li><li><code>C_READ_AA</code>: the <code>read</code> intervals timed directly after <code>asmread</code>. These are the 4 intervals of the two crev processes.</li><li><code>C_ASM_AR</code>, <code>C_ASM_AO</code>, <code>C_ASM_FI</code>: the <code>asmread</code> intervals directly after <code>read</code> (4 intervals), directly after <code>oldread</code> (2), and first in their process (2). Each of the three groups comes from 2 processes.</li></ul></td></tr>
<tr><td colspan="2"><b>Record groups: bwx12 rows at 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 290  # 8000 MT/s rows
 291  B_L_OLD = {d: sel(dataset=d, kernel="oldread", pos=0) for d in LPOOL}
 292  B_L_ASM = {d: sel(dataset=d, kernel="asmread", pos=1) for d in LPOOL}
 293  for d, n, p in (("L-1", 2, 1), ("L-2", 4, 2), ("L-3", 2, 1), ("L-4", 3, 3)):
 294      expect(B_L_OLD[d], n, p, f"{d}, oldread at position 0")
 295      expect(B_L_ASM[d], n, p, f"{d}, asmread at position 1")
 296  P_L_OLD = expect([r for d in LPOOL for r in B_L_OLD[d]], 11, 7, "pool L-1 to L-4, oldread")
 297  P_L_ASM = expect([r for d in LPOOL for r in B_L_ASM[d]], 11, 7, "pool L-1 to L-4, asmread")</pre></td><td valign="top"><ul><li><code>B_L_OLD[d]</code> and <code>B_L_ASM[d]</code>: for each dataset <code>d</code> of L-1 to L-4, <code>oldread</code> at position 0 and <code>asmread</code> at position 1.</li><li>Expected size per kernel: L-1 2 intervals of 1 process, L-2 4 of 2, L-3 2 of 1, L-4 3 of 3.</li><li><code>P_L_OLD</code> and <code>P_L_ASM</code>: the four datasets joined to one pool per kernel. Each pool must have 11 intervals of 7 processes.</li></ul></td></tr>
<tr><td colspan="2"><b>Record groups: part A rows at 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 298  B_A_OLD = {d: sel(dataset=d, binary="bw_old", kernel="read") for d in APOOL}
 299  B_A_NEW = {d: sel(dataset=d, binary="bw_new", kernel="read") for d in ("A-1", "A-2")}
 300  for d, n, p in (("A-1", 6, 2), ("A-2", 6, 2), ("A-3", 9, 3)):
 301      expect(B_A_OLD[d], n, p, f"{d}, bw_old read")
 302  for d in ("A-1", "A-2"):
 303      expect(B_A_NEW[d], 6, 2, f"{d}, bw_new read")
 304  P_A_OLD = expect([r for d in APOOL for r in B_A_OLD[d]], 21, 7, "pool A-1 to A-3, bw_old read")
 305</pre></td><td valign="top"><ul><li><code>B_A_OLD[d]</code>: kernel <code>read</code> of <code>bw_old</code> in A-1, A-2 and A-3. Expected sizes: 6 intervals of 2 processes, 6 of 2, and 9 of 3.</li><li><code>B_A_NEW[d]</code>: kernel <code>read</code> of <code>bw_new</code> in A-1 and A-2, 6 intervals of 2 processes each. No A-3 group is built for <code>bw_new</code>.</li><li><code>P_A_OLD</code>: the pool A-1 to A-3 for <code>bw_old</code>, 21 intervals of 7 processes. No pool is built for <code>bw_new</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>All used records: modules, speed and boot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 306  USED = (A_OLD + A_NEW + L_OLD + L_ASM + I_OLD + I_ASM + F_OLD + F_ASM + C_OLD + C_READ + C_ASM
 307          + P_L_OLD + P_L_ASM + P_A_OLD + B_A_NEW["A-1"] + B_A_NEW["A-2"])
 308  need(all(r["modules"] == 12 for r in USED), "a record used on the page is not a 12-module run")
 309  SEVEN = [r for r in USED if r["speed_MTps"] == 7200]
 310  EIGHT = [r for r in USED if r["speed_MTps"] == 8000]
 311  need(len(SEVEN) + len(EIGHT) == len(USED), "a record has another memory speed")
 312  need({r["boot"] for r in SEVEN} == {RERUN["boot_id"]}, "the 7200 MT/s records are not from one boot")
 313  need(len({r["boot"] for r in EIGHT}) == 1, "the 8000 MT/s records are not from one boot")
 314  need({r["dataset"] for r in SEVEN} == {"rerun-A", "rerun-L", "rerun-C", "control-I", "F72d12"}, "7200 MT/s datasets")</pre></td><td valign="top"><ul><li><code>USED</code> holds every record of the groups above once. The expected sizes add up to 139 records.</li><li>The script stops unless every record of <code>USED</code> comes from a run with 12 memory modules.</li><li><code>SEVEN</code> and <code>EIGHT</code>: the records at 7200 MT/s and at 8000 MT/s. The script stops when a record has another speed.</li><li>All 7200 MT/s records must have the boot id of the rerun (<code>meta.rerun.boot_id</code>). All 8000 MT/s records must share one value of the field <code>boot</code>.</li><li>The 7200 MT/s records must come from exactly these datasets: <code>rerun-A</code>, <code>rerun-L</code>, <code>rerun-C</code>, <code>control-I</code>, <code>F72d12</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 315  need(all(r["min_ms"] == 500 and r["stop"] == "whole pass" for r in USED if r["part"] == "A"), "part A method")
 316  need(all(r["stop"] == "common" for r in USED if r["part"] != "A"), "bwx12 rows: stop rule")
 317  need(all(r["min_ms"] == 6000 for r in USED if r["dataset"] in ("rerun-L", "rerun-C", "control-I", "F72d12", "L-1")),
 318       "6 s rows")
 319  need(all(r["min_ms"] == 4000 for r in USED if r["dataset"] in ("L-2", "L-3", "L-4")), "4 s rows")</pre></td><td valign="top">The method fields of the used records. The script stops unless all hold:<ul><li>Part A records: <code>min_ms</code> is 500 (an interval lasts at least 0.5 s) and <code>stop</code> is <code>whole pass</code>.</li><li>All other records: <code>stop</code> is <code>common</code>.</li><li>Part L, part C, control I, F72d12 and L-1: <code>min_ms</code> is 6000 (6 s).</li><li>L-2, L-3 and L-4: <code>min_ms</code> is 4000 (4 s). So the pool L-1 to L-4 holds 6 s intervals and 4 s intervals.</li></ul></td></tr>
<tr><td colspan="2"><b>Records of the older runner bwx</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 320  # Rows of the older runner bwx (another binary, not like-for-like). The rules file names them as the reference of part C
 321  # (rule V2 point 4: folders B7 and C3, tags common-6000-*). The page shows them in one note under Table 2 and gives no wording from them.
 322  BWX_POOL = ("B7a", "B7b", "C3a", "C3b")
 323  X_READ_AO = expect(sel(dataset=BWX_POOL, kernel="read", pos=1), 48, 24, "runner bwx, read at position 1")
 324  X_READ_AA = expect(sel(dataset=BWX_POOL, kernel="read", pos=6), 48, 24, "runner bwx, read at position 6")
 325  X_ASM_AR = expect(sel(dataset=BWX_POOL, kernel="asmread", pos=2), 48, 24, "runner bwx, asmread at position 2")
 326  X_LOADS = expect(sel(dataset=BWX_POOL, kernel=("read", "asmread")), 192, 24, "runner bwx, all intervals of read and asmread")
 327  need({r["kernel_before"] for r in X_READ_AO} == {"oldread"} and {r["kernel_before"] for r in X_READ_AA} == {"asmread"}
 328       and {r["kernel_before"] for r in X_ASM_AR} == {"read"}, "runner bwx: the kernel directly before is not as rule V2 point 4 states")
 329  need(all(r["tag"].startswith("common-6000-") for r in X_LOADS), "runner bwx: a row has another tag than common-6000-*")</pre></td><td valign="top"><ul><li><code>BWX_POOL</code>: four datasets of the older runner bwx: B7a, B7b, C3a and C3b. The comment says that the rules file names them as the reference of part C, and that the page shows them in one note under Table 2.</li><li><code>X_READ_AO</code>: <code>read</code> at position 1. <code>X_READ_AA</code>: <code>read</code> at position 6. <code>X_ASM_AR</code>: <code>asmread</code> at position 2. Each must have 48 intervals of 24 processes.</li><li><code>X_LOADS</code>: all <code>read</code> and <code>asmread</code> intervals of these datasets, 192 intervals of 24 processes. Besides the three groups it holds 48 <code>asmread</code> intervals at position 5 (counted in <code>facts.json</code> for this companion).</li><li>The script stops unless the kernel directly before is <code>oldread</code>, <code>asmread</code> and <code>read</code> for the three groups, in this order.</li><li>It also stops unless every tag of <code>X_LOADS</code> starts with <code>common-6000-</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 330  # four more processes of the same runner with the reverse kernel order (two B5 folders): higher values at 8000 MT/s
 331  X_REV_READ = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="read"), 4, 4, "runner bwx, reverse order, read")
 332  X_REV_ASM = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="asmread"), 4, 4, "runner bwx, reverse order, asmread")
 333  OTHER = X_LOADS + X_REV_READ + X_REV_ASM
 334  need(all(r["binary"] == "bwx" and r["modules"] == 12 and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000 for r in OTHER),
 335       "runner bwx: a row is not a 6 s common-stop run of bwx at 8000 MT/s with 12 modules")
 336  need({r["boot"] for r in OTHER} == {r["boot"] for r in EIGHT}, "runner bwx: a row is not from the boot of the other 8000 MT/s rows")</pre></td><td valign="top"><ul><li><code>X_REV_READ</code>, <code>X_REV_ASM</code>: <code>read</code> and <code>asmread</code> of the datasets B5a-rev and B5b-rev. Each must have 4 intervals of 4 processes. The comment says that these processes ran the reverse kernel order.</li><li><code>OTHER</code> joins <code>X_LOADS</code> and these two groups. The expected sizes add up to 200 records.</li><li>The script stops unless every record of <code>OTHER</code> has the binary <code>bwx</code>, 12 modules, 8000 MT/s, the common stop and <code>min_ms</code> 6000.</li><li>It also stops unless the records of <code>OTHER</code> come from the boot of the other 8000 MT/s records.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 337  check(True, f"record counts: {len(USED)} interval records used, all 120 threads, 12 modules; "
 338              f"7200 MT/s records from 1 boot, 8000 MT/s records from 1 boot; {len(OTHER)} more records of runner bwx (same 8000 MT/s boot) for one note under Table 2")</pre></td><td valign="top">Adds the first line of the self-check list, with the fixed result PASS. The script reaches this line only when all hard assertions above have passed. The line states the number of used records and of bwx records.</td></tr>
<tr><td colspan="2"><b>Sum of the T rows against the rate of the I row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 339  # bwx12 and bwx: the page value is the sum of the thread rows. The interval row of the csv prints a rate too: how far the two differ
 340  BWX_USED = [r for r in USED if r["part"] != "A"]
 341  IROW_DIFF = [abs(q(val(r)) - i_row_rate(r)) for r in BWX_USED]
 342  IROW_MAX = max(IROW_DIFF)
 343  need(IROW_MAX &lt;= Decimal("0.02"), f"bwx12: an interval row differs from the sum of its thread rows by {IROW_MAX} GB/s")
 344  IROW_MAX_X = max(abs(q(val(r)) - i_row_rate(r)) for r in OTHER)
 345  need(IROW_MAX_X &lt;= Decimal("0.02"), f"runner bwx: an interval row differs from the sum of its thread rows by {IROW_MAX_X} GB/s")</pre></td><td valign="top"><ul><li><code>BWX_USED</code>: the records of <code>USED</code> outside part A. All of them are bwx12 records.</li><li>For each record, <code>val</code> gives the sum of the 120 T rows. This sum is rounded to 0.01 GB/s, and the rate printed in the I row (<code>i_row_rate</code>) is subtracted. <code>IROW_MAX</code> is the largest absolute difference.</li><li>The script stops when <code>IROW_MAX</code> is above 0.02 GB/s. The same test runs for the records of <code>OTHER</code> with <code>IROW_MAX_X</code>.</li><li>These are the first calls of <code>val</code>. So the T rows of all bwx12 records of <code>USED</code> and of all records of <code>OTHER</code> are read and checked here.</li><li>In these lines the printed rate is only compared. The page value is the sum of the T rows.</li><li>In the saved output of a build both largest differences are 0.02 GB/s [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Part A: the csv row and the process number</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 346  # part A: the process number inside the file. facts.json counts the processes of rows A-1, A-2 and of the rerun in the same way
 347  A_USED = [r for r in USED if r["part"] == "A"]
 348  for r in A_USED:
 349      r["_fproc"] = file_process(r)
 350  need(all(r["_fproc"] == r["process"] for r in A_USED if r["dataset"] != "A-3"), "part A: a process number of facts.json is not the number of the process in its file")
 351  check(True, f"raw csv rows: {len(BWX_USED)} bwx12 records and {len(OTHER)} bwx records name their interval row and the 120 thread rows after it "
 352              f"(printed rate and sum of the thread rows differ by at most {f2(IROW_MAX)} GB/s for bwx12 and {f2(IROW_MAX_X)} GB/s for bwx); "
 353              f"{len(A_USED)} part A records name the row with their rate")
 354
 355</pre></td><td valign="top"><ul><li><code>A_USED</code>: the part A records of <code>USED</code>. For each one, <code>file_process</code> checks the csv row and returns the number of the process inside the file. The number is stored in the record as <code>_fproc</code>.</li><li>The script stops when <code>_fproc</code> differs from the field <code>process</code> of a record. The A-3 records are left out of this test.</li><li>For A-3 the two numbers differ (checked for this companion): <code>facts.json</code> numbers the three A-3 processes 1, 2 and 3, and in the file <code>A3.csv</code> they are the processes 1, 3 and 5.</li><li>Lines 351 to 353 add the second line of the self-check list, with the fixed result PASS. It holds the record counts and the two largest differences.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>src</code>: source text for a tooltip</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 356  SUM_NOTE = "The rate is the sum of the 120 thread rows after it"
 357
 358
 359  def src(recs):
 360      """Source text for a tooltip: file and line numbers. For bwx12 the lines are interval rows, and the rate is the sum of the thread rows."""
 361      by = {}
 362      for r in recs:
 363          by.setdefault(f"{r['folder']}/{r['file']}", []).append(r["line"])
 364      bwx = recs[0]["part"] != "A"
 365      need(all((r["part"] != "A") == bwx for r in recs), "src: part A and bwx12 records in one source text")
 366
 367      def one(p, ls):
 368          many = len(ls) &gt; 1
 369          nums = ", ".join(str(x) for x in sorted(ls))
 370          return f"{p}, interval row{'s' if many else ''} in line{'s' if many else ''} {nums}" if bwx else f"{p} line{'s' if many else ''} {nums}"
 371      out = " and ".join(one(p, ls) for p, ls in by.items())
 372      if bwx:
 373          out += ". " + (SUM_NOTE if len(recs) == 1 else "Each rate is the sum of the 120 thread rows after its interval row")
 374      return out
 375
 376</pre></td><td valign="top">Returns the source text of a value for a tooltip: the csv file and the line numbers of the records. The script stops when one call mixes part A records and bwx records. For part A the lines are the interval rows that hold the rates. For bwx records the lines are the I rows, and the text adds that each rate is the sum of the 120 thread rows after its I row.</td></tr>
<tr><td colspan="2"><b>Function <code>hm</code>: time of day as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 377  def hm(utc, date=False):
 378      return (utc[:10] + " " if date else "") + utc[11:16] + " UTC"
 379
 380</pre></td><td valign="top">Turns a time stamp such as <code>2026-11-17T22:12:14Z</code> into <code>22:12 UTC</code>. With <code>date</code> true it puts the date in front: <code>2026-11-17 22:12 UTC</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>n7200</code>: the text of n at 7200 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 381  def n7200(recs, pairs=None):
 382      """n as intervals / processes / sessions / boots for records of the 7200 MT/s boot."""
 383      ds = {r["dataset"] for r in recs}
 384      np_ = len({r["proc_key"] for r in recs})
 385      first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")
 386      if ds &lt;= {"control-I", "F72d12"}:
 387          sess = "no session"
 388      else:
 389          named = sorted({r["session"] for r in recs if r["session"] is not None})
 390          extra = len({r["proc_key"] for r in recs if r["session"] is None})
 391          if extra == 0:
 392              sess = plural(len(named), "session")
 393              if len(named) &lt; 3:
 394                  sess = ("session " if len(named) == 1 else "sessions ") + " and ".join(str(s) for s in named)
 395          else:
 396              sess = (f"{plural(len(named), 'session')}" if len(named) != 1 else f"session {named[0]}") \
 397                     + f" and {extra} extra process"
 398      return f"{first} / {plural(np_, 'process')} / {sess} / 1 boot"
 399
 400</pre></td><td valign="top">Returns the text of n in four parts, for example <code>6 intervals / 3 processes / 3 sessions / 1 boot</code>.<ul><li>Part 1: the number of records, or the number of pairs when <code>pairs</code> is given.</li><li>Part 2: the number of processes (different values of <code>proc_key</code>).</li><li>Part 3: <code>no session</code> when all records belong to control I or F72d12. Else it gives the sessions of the records: a count such as <code>3 sessions</code>, or the session numbers such as <code>sessions 1 and 3</code>.</li><li>Processes without a session number are added to part 3 as extra processes, for example <code>3 sessions and 1 extra process</code>. In the rerun this is the extra part C process T72C4.</li><li>Part 4: the fixed text <code>1 boot</code>. Line 312 asserts that all used 7200 MT/s records come from one boot.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>n8000</code>: the text of n at 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 401  def n8000(recs, pairs=None):
 402      first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")
 403      return f"{first} / {plural(len({r['proc_key'] for r in recs}), 'process')} / 1 boot"
 404
 405</pre></td><td valign="top">The same text without the session part: intervals (or pairs), processes, and the fixed text <code>1 boot</code>. Example: <code>11 intervals / 7 processes / 1 boot</code>. Line 313 asserts that all used 8000 MT/s records come from one boot.</td></tr>
<tr><td colspan="2"><b>Function <code>pairs_in_process</code>: pair old and load-only intervals</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 406  # ------------------------------------------------------------------ Q1: drops
 407  def pairs_in_process(olds, news):
 408      """Pairs of (old, load-only) intervals of the same process and round."""
 409      out = []
 410      for n in sorted(news, key=lambda r: (r["launch_utc"], r["round"])):
 411          o = [x for x in olds if x["proc_key"] == n["proc_key"] and x["round"] == n["round"]]
 412          need(len(o) == 1, "pair: no single old-kernel interval for a load-only interval")
 413          out.append((o[0], n))
 414      return out
 415</pre></td><td valign="top">Builds the pairs for question Q1 from two record lists of a bwx runner.<ul><li>It goes through the load-only intervals <code>news</code>, sorted by launch time and round.</li><li>For each one it takes the intervals of <code>olds</code> with the same <code>proc_key</code> and the same <code>round</code>. The script stops unless exactly one exists.</li><li>The result is a list of pairs (old-kernel interval, load-only interval). Both intervals of a pair come from one process and one round of the kernel sequence.</li><li>The order inside the round is not tested. In part L and in cfwd the old kernel is timed before the load-only loop of the pair. In crev it is timed after it.</li></ul></td></tr>
<tr><td colspan="2"><b>Functions <code>drop</code> and <code>drops_of</code>: the drop in percent</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 416
 417  def drop(old, new):
 418      return (1 - D(new) / D(old)) * 100
 419
 420
 421  def drops_of(pairs):
 422      return [drop(val(o), val(n)) for o, n in pairs]
 423
 424</pre></td><td valign="top"><code>drop</code> returns <code>(1 - new / old) x 100</code>: by how many percent the rate <code>new</code> lies below the rate <code>old</code>. <code>drops_of</code> returns the drop of every pair, with the old-kernel rate as <code>old</code> and the load-only rate as <code>new</code>. Both rates come from <code>val</code>. They are not rounded to 0.01 GB/s before the division.</td></tr>
<tr><td colspan="2"><b>Function <code>drop_txt</code>: text of a list of drops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 425  def drop_txt(ds):
 426      lo, hi = f1(min(ds)), f1(max(ds))
 427      return f"{lo} %" if lo == hi else f"{lo} % to {hi} %"
 428
 429</pre></td><td valign="top">Rounds the lowest and the highest drop of the list to 0.1 % with <code>f1</code>. It returns <code>lowest % to highest %</code>, or a single value when both rounded values are equal. Example: <code>30.5 % to 31.2 %</code>.</td></tr>
<tr><td colspan="2"><b>Question Q1: the drops of the bwx12 pairs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 430  Q1 = {}
 431  Q1["C_ao"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AO))
 432  Q1["C_aa"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AA))
 433  Q1["L"] = dict(pairs=pairs_in_process(L_OLD, L_ASM))
 434  Q1["I"] = dict(pairs=pairs_in_process(I_OLD, I_ASM))
 435  Q1["F"] = dict(pairs=pairs_in_process(F_OLD, F_ASM))
 436  Q1["L1"] = dict(pairs=pairs_in_process(B_L_OLD["L-1"], B_L_ASM["L-1"]))
 437  for k, npairs in (("C_ao", 4), ("C_aa", 4), ("L", 6), ("I", 4), ("F", 2), ("L1", 2)):
 438      need(len(Q1[k]["pairs"]) == npairs, f"Q1 {k}: expected {npairs} pairs")
 439      Q1[k]["drops"] = drops_of(Q1[k]["pairs"])
 440      Q1[k]["old"] = Rg([o for o, _ in Q1[k]["pairs"]])
 441      Q1[k]["new"] = Rg([n for _, n in Q1[k]["pairs"]])
 442
 443</pre></td><td valign="top"><code>Q1</code> gets one entry per group of pairs.<ul><li><code>C_ao</code>: part C, <code>read</code> directly after <code>oldread</code>, paired with <code>oldread</code>. <code>C_aa</code>: part C, <code>read</code> directly after <code>asmread</code>, paired with <code>oldread</code>.</li><li><code>L</code>, <code>I</code>, <code>F</code>, <code>L1</code>: <code>asmread</code> at position 1 paired with <code>oldread</code> at position 0, for part L, control I, F72d12 and the 8000 MT/s row L-1.</li><li>The script stops unless the six groups have 4, 4, 6, 4, 2 and 2 pairs.</li><li>Each entry gets <code>drops</code> (one drop per pair), <code>old</code> (the range of the old-kernel intervals of its pairs) and <code>new</code> (the range of its load-only intervals).</li><li>So <code>old</code> of <code>C_ao</code> holds only the 4 <code>oldread</code> intervals of the cfwd processes, and <code>old</code> of <code>C_aa</code> only the 4 of the crev processes.</li><li>Saved output of a build: <code>C_ao</code> 30.5 % to 31.2 %, <code>C_aa</code> 29.7 % to 31.1 %, <code>L</code> 29.2 % to 30.5 % [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>a_pair</code>: one pair of part A processes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 444  def a_pair(olds, news, rnd):
 445      o = Rg([r for r in olds if r["round"] == rnd])
 446      n = Rg([r for r in news if r["round"] == rnd])
 447      need(o.n == 3 and n.n == 3 and o.np == 1 and n.np == 1, "part A pair: expected 3 intervals of 1 process per kernel")
 448      return dict(old=o, new=n, drop=drop(o.med, n.med), round=rnd)
 449
 450</pre></td><td valign="top"><ul><li>In part A the two kernels run in two processes, one per binary.</li><li><code>a_pair</code> builds the range of the round <code>rnd</code> for the old binary (<code>o</code>) and for the new binary (<code>n</code>).</li><li>The script stops unless each range has 3 intervals of 1 process.</li><li>The drop is computed between the two medians. With 3 intervals the median is the middle one of the 3 rates. It is not always the second interval in time.</li><li>Example: in session 1, round 1 the 3 rates of <code>bw_old</code> are 467.83, 467.92 and 465.38 GB/s in time order. The median is 467.83 GB/s, the first interval [Ref3].</li></ul></td></tr>
<tr><td colspan="2"><b>Question Q1: drops of part A, test of all drops</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 451  A_PAIRS = {}       # (session, round) -&gt; pair of process medians
 452  for s_ in (1, 2, 3):
 453      for rnd in (1, 2):
 454          A_PAIRS[(s_, rnd)] = a_pair([r for r in A_OLD if r["session"] == s_], [r for r in A_NEW if r["session"] == s_], rnd)
 455  A8_PAIRS = {(d, rnd): a_pair(B_A_OLD[d], B_A_NEW[d], rnd) for d in ("A-1", "A-2") for rnd in (1, 2)}
 456  Q1["A"] = dict(drops=[p["drop"] for p in A_PAIRS.values()])
 457  Q1["A8"] = dict(drops=[p["drop"] for p in A8_PAIRS.values()])
 458  SAME_LINE_DROPS = Q1["L"]["drops"] + Q1["I"]["drops"] + Q1["F"]["drops"]     # the like.spec line in the 7200 MT/s boot
 459  ALL_7200_DROPS = Q1["C_ao"]["drops"] + Q1["C_aa"]["drops"] + SAME_LINE_DROPS + Q1["A"]["drops"]
 460  need(all(d &gt; 0 for d in ALL_7200_DROPS), "a load-only interval is not below the old read kernel")
 461</pre></td><td valign="top"><ul><li><code>A_PAIRS</code>: one pair per session (1 to 3) and round (1, 2) of part A at 7200 MT/s, so 6 pairs.</li><li><code>A8_PAIRS</code>: one pair per dataset (A-1, A-2) and round at 8000 MT/s, so 4 pairs.</li><li><code>Q1["A"]</code> and <code>Q1["A8"]</code> hold the drops of these pairs.</li><li><code>SAME_LINE_DROPS</code>: the 12 drops of part L, control I and F72d12. <code>ALL_7200_DROPS</code>: these plus the 8 drops of part C and the 6 drops of part A, so 26 drops.</li><li>The script stops unless each of the 26 drops is above 0. So in every pair at 7200 MT/s the load-only value must lie below the old-kernel value.</li></ul></td></tr>
<tr><td colspan="2"><b>Question Q2: the ranges of the groups</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 462  # ------------------------------------------------------------------ Q2: ranges
 463  rA_old, rPA_old = Rg(A_OLD), Rg(P_A_OLD)
 464  rL_old, rL_asm = Rg(L_OLD), Rg(L_ASM)
 465  rC_old, rI_old, rI_asm, rF_old, rF_asm = Rg(C_OLD), Rg(I_OLD), Rg(I_ASM), Rg(F_OLD), Rg(F_ASM)
 466  rPL_old, rPL_asm = Rg(P_L_OLD), Rg(P_L_ASM)
 467  rL1_asm = Rg(B_L_ASM["L-1"])
 468  rC_asm_ao = Rg(C_ASM_AO)
 469  rC_read_ao, rC_read_aa = Rg(C_READ_AO), Rg(C_READ_AA)</pre></td><td valign="top">One <code>Rg</code> object for each of 15 record groups. The name is <code>r</code> plus the name of the group: <code>rL_old</code> is the range of <code>L_OLD</code>, <code>rPL_asm</code> is the range of the pool <code>P_L_ASM</code>, <code>rPA_old</code> is the range of the pool <code>P_A_OLD</code>. <code>rL1_asm</code> is the range of <code>asmread</code> in row L-1 alone. Building a range calls <code>val</code> for each of its records.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 470  WORD_SAME = "no difference seen"
 471  WORD_DIFF = "differs between the 8000 MT/s boot and the 7200 MT/s boot"
 472  need(FJ["verdicts"]["rule_wordings"]["same"] == WORD_SAME and FJ["verdicts"]["rule_wordings"]["differs"] == WORD_DIFF,
 473       "the fixed wordings differ from facts.json")
 474
 475</pre></td><td valign="top">The two fixed wordings of a comparison result. The script stops when they are not equal to the two texts that <code>facts.json</code> stores under <code>verdicts.rule_wordings</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>width_pct</code>: width of a range in percent</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 476  def width_pct(rg):
 477      """Width of a range in percent of its lower end: the size that a 'no difference seen' test cannot exclude (est.)."""
 478      return (rg.hi - rg.lo) / rg.lo * 100
 479
 480</pre></td><td valign="top">Returns <code>(hi - lo) / lo x 100</code>: the width of the range in percent of its lower end. The comment names the use: the size of a difference that a result <code>no difference seen</code> cannot exclude. The comment marks this as an estimate.</td></tr>
<tr><td colspan="2"><b>Function <code>wording</code>: the fixed text of one comparison</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 481  def wording(r7, r8):
 482      return WORD_SAME if r7.overlaps(r8) else WORD_DIFF
 483
 484</pre></td><td valign="top">Returns <code>no difference seen</code> when the 7200 MT/s range and the 8000 MT/s range overlap. Else it returns <code>differs between the 8000 MT/s boot and the 7200 MT/s boot</code>. So only the lowest and the highest rate of each group decide the wording.</td></tr>
<tr><td colspan="2"><b>Old read kernel: 7200 MT/s against 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 485  # old read kernel
 486  need(rA_old.overlaps(rPA_old) and rC_old.overlaps(rPL_old) and rF_old.overlaps(rPL_old) and rI_old.overlaps(rPL_old),
 487       "old read: an expected overlap is missing")
 488  need(not rL_old.overlaps(rPL_old) and rL_old.hi &lt; rPL_old.lo, "old read, part L: expected below the 8000 MT/s pool")
 489  L_OLD_NEAR = rL_old.nearest(rPL_old)                       # negative: part L is lower
 490  L_OLD_MED = rL_old.med - rPL_old.med
 491  L_OLD_NEAR_PCT = abs(L_OLD_NEAR) / rPL_old.lo * 100        # percent of the lower end of the 8000 MT/s range
 492  L_OLD_MED_PCT = abs(L_OLD_MED) / rPL_old.med * 100         # percent of the 8000 MT/s median</pre></td><td valign="top"><ul><li>The script stops unless four pairs of ranges overlap: part A with the pool A-1 to A-3, and part C, F72d12 and control I each with the <code>oldread</code> pool L-1 to L-4.</li><li>It also stops unless the <code>oldread</code> range of part L lies fully below the pool L-1 to L-4.</li><li><code>L_OLD_NEAR</code>: the distance of the nearest ends, part L against the pool. It is below 0. <code>L_OLD_MED</code>: the median of part L minus the median of the pool.</li><li><code>L_OLD_NEAR_PCT</code>: the size of the first distance in percent of the lower end of the pool range. <code>L_OLD_MED_PCT</code>: the size of the second in percent of the pool median.</li><li>Saved output of a build: part L 461.61 to 464.29 GB/s, pool 465.53 to 470.05 GB/s, nearest ends -1.24 GB/s, medians 6.27 GB/s apart [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Load-only loop: 7200 MT/s against 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 493  # load-only loop
 494  need(not rL_asm.overlaps(rPL_asm) and rL_asm.lo &gt; rPL_asm.hi, "asmread, part L: expected above the 8000 MT/s pool")
 495  need(rF_asm.overlaps(rPL_asm), "asmread, F72d12: expected inside the 8000 MT/s pool")
 496  need(rPL_asm.lo &lt;= rF_asm.lo and rF_asm.hi &lt;= rPL_asm.hi, "asmread, F72d12: expected inside the 8000 MT/s pool")
 497  need(not rI_asm.overlaps(rPL_asm) and rI_asm.lo &gt; rPL_asm.hi, "asmread, control I: expected above the 8000 MT/s pool")
 498  need(not rC_asm_ao.overlaps(rPL_asm), "asmread after oldread, part C: expected above the 8000 MT/s pool")
 499  need(not rF_asm.overlaps(rL_asm) and not rF_asm.overlaps(rI_asm) and not rI_asm.overlaps(rL_asm),
 500       "the three visits of the 7200 MT/s boot overlap")</pre></td><td valign="top">Hard assertions on the <code>asmread</code> ranges. The script stops unless all hold:<ul><li>Line 494: part L lies fully above the pool L-1 to L-4.</li><li>Lines 495 and 496: F72d12 lies inside the range of the pool.</li><li>Line 497: control I lies fully above the pool.</li><li>Line 498: part C, <code>asmread</code> directly after <code>oldread</code>, does not overlap the pool. This line does not test which of the two ranges is higher.</li><li>Lines 499 and 500: the ranges of F72d12, part L and control I do not overlap each other.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 501  VISIT_LO, VISIT_HI = min(rF_asm.lo, rL_asm.lo, rI_asm.lo), max(rF_asm.hi, rL_asm.hi, rI_asm.hi)
 502  VISIT_OLD_LO, VISIT_OLD_HI = min(rF_old.lo, rL_old.lo, rI_old.lo), max(rF_old.hi, rL_old.hi, rI_old.hi)
 503  DIST = {  # the same kind of distance on both sides: part L against the 8000 MT/s pool, part L against F72d12
 504      "nearest": (rL_asm.nearest(rPL_asm), rL_asm.nearest(rF_asm)),
 505      "medians": (rL_asm.med - rPL_asm.med, rL_asm.med - rF_asm.med),
 506      "farthest": (rL_asm.farthest(rPL_asm), rL_asm.farthest(rF_asm)),
 507  }</pre></td><td valign="top"><ul><li><code>VISIT_LO</code>, <code>VISIT_HI</code>: the lowest and the highest <code>asmread</code> rate over the three visits of the part L line in the 7200 MT/s boot (F72d12, part L, control I). <code>VISIT_OLD_LO</code>, <code>VISIT_OLD_HI</code>: the same for <code>oldread</code>.</li><li><code>DIST</code>: three kinds of distance for the <code>asmread</code> range of part L. In each pair the first value is against the pool L-1 to L-4, and the second is against F72d12.</li><li><code>nearest</code>: the distance of the nearest ends. <code>medians</code>: the difference of the medians. <code>farthest</code>: the distance of the farthest ends.</li></ul></td></tr>
<tr><td colspan="2"><b>Part A, new read kernel: session 1 against A-1 and A-2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 508  # part A, new read kernel: session 1 against the 8000 MT/s processes of the same round (rule V3)
 509  A_V3 = {}
 510  for rnd in (1, 2):
 511      r7 = Rg([r for r in A_NEW if r["session"] == 1 and r["round"] == rnd])
 512      r8 = Rg([r for d in ("A-1", "A-2") for r in B_A_NEW[d] if r["round"] == rnd])
 513      need(r7.n == 3 and r7.np == 1 and r8.n == 6 and r8.np == 2, "part A, rule V3: record counts")
 514      need(not r7.overlaps(r8) and r7.lo &gt; r8.hi, "part A, session 1: expected above the 8000 MT/s range of the round")
 515      A_V3[rnd] = dict(r7=r7, r8=r8, near=r7.nearest(r8),
 516                       p7=sorted({r["passes"] for r in r7.recs}), p8=sorted(r["passes"] for r in r8.recs))
 517  need(all(len(A_V3[rnd]["p7"]) == 1 for rnd in (1, 2)), "part A, session 1, bw_new read: more than one pass count in a round")
 518</pre></td><td valign="top">For each round (1 and 2), with kernel <code>read</code> of <code>bw_new</code>:<ul><li><code>r7</code>: the range of the intervals of session 1. <code>r8</code>: the range of the intervals of A-1 and A-2 of the same round.</li><li>Line 513: the script stops unless <code>r7</code> holds 3 intervals of 1 process and <code>r8</code> holds 6 intervals of 2 processes.</li><li>Line 514: the script stops unless <code>r7</code> lies fully above <code>r8</code>. <code>near</code> is the distance of the nearest ends.</li><li><code>p7</code> and <code>p8</code>: the pass counts of the intervals (field <code>passes</code>). The script stops unless the 3 intervals of session 1 have one pass count per round.</li><li>Sessions 2 and 3 are not compared here. The comment names the rule: V3.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 519  # the pool L-1 to L-4 without the interval that holds the lowest asmread value (machine state section)
 520  LOWEST_ASM = min(P_L_ASM, key=val)
 521  rPL_asm_wo = Rg([r for r in P_L_ASM if r is not LOWEST_ASM])
 522  need(rL_asm.lo &gt; rPL_asm_wo.hi, "part L does not lie above the pool without its lowest interval")
 523</pre></td><td valign="top"><code>LOWEST_ASM</code> is the record with the lowest <code>asmread</code> rate of the pool L-1 to L-4. <code>rPL_asm_wo</code> is the range of the pool without this one interval. The script stops unless the lowest <code>asmread</code> rate of part L is above the highest rate of this smaller pool. The comment says that the section on the machine state uses the result.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 524  # part A, old read kernel: the 7200 MT/s range is wider than the 8000 MT/s range, and some of its intervals lie outside that range
 525  A_OLD_BELOW = [r for r in A_OLD if val(r) &lt; rPA_old.lo]
 526  A_OLD_ABOVE = [r for r in A_OLD if val(r) &gt; rPA_old.hi]
 527  A_OLD_W7, A_OLD_W8 = rA_old.hi - rA_old.lo, rPA_old.hi - rPA_old.lo
 528  need(A_OLD_BELOW and A_OLD_ABOVE and A_OLD_W7 &gt; A_OLD_W8, "part A, old read: the 7200 MT/s range is not wider than the 8000 MT/s range on both sides")
 529
 530</pre></td><td valign="top"><code>A_OLD_BELOW</code> and <code>A_OLD_ABOVE</code>: the part A intervals of the old read kernel with a rate below the lowest rate, or above the highest rate, of the pool A-1 to A-3. <code>A_OLD_W7</code> and <code>A_OLD_W8</code>: the width (highest minus lowest) of the 7200 MT/s range and of the pool range. The script stops unless both lists hold at least one record and the 7200 MT/s range is the wider one.</td></tr>
<tr><td colspan="2"><b>Function <code>one_process</code>: name the process of 3 intervals</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 531  def one_process(recs):
 532      """'session s, round r' when the records are all intervals of one process of part A, else a stop."""
 533      key = {(r["session"], r["round"], r["proc_key"]) for r in recs}
 534      need(len(key) == 1 and len(recs) == 3, "part A, old read: the intervals outside the 8000 MT/s range are not the 3 intervals of one process")
 535      s_, rnd, _ = next(iter(key))
 536      return f"session {s_}, round {rnd}"
 537
 538</pre></td><td valign="top">The script stops unless the list has exactly 3 records with one session, one round and one <code>proc_key</code>. The function then returns the text <code>session s, round r</code>. Later code calls it for <code>A_OLD_BELOW</code> and for <code>A_OLD_ABOVE</code>.</td></tr>
<tr><td colspan="2"><b>Part C against the rows of the older runner bwx</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 539  # rows of runner bwx (another binary): ranges with the same kernel directly before, for the note under Table 2
 540  need({r["pos"] for r in C_ASM_AR} == {2} and {r["file"] for r in C_ASM_AR} == {"cfwd.csv"}, "part C, asmread after read: not position 2 of cfwd")
 541  rC_asm_ar = Rg(C_ASM_AR)
 542  rX_read_ao, rX_read_aa, rX_asm_ar = Rg(X_READ_AO), Rg(X_READ_AA), Rg(X_ASM_AR)
 543  X_PAIRS = [(rC_read_ao, rX_read_ao), (rC_read_aa, rX_read_aa), (rC_asm_ar, rX_asm_ar)]
 544  need(all(c.lo &gt; x.hi for c, x in X_PAIRS), "part C: a group does not lie above the bwx rows with the same kernel directly before")
 545  X_ABOVE = [c.nearest(x) for c, x in X_PAIRS]</pre></td><td valign="top"><ul><li>Line 540: the script stops unless the part C intervals of <code>asmread</code> directly after <code>read</code> are all at position 2 of <code>cfwd.csv</code>.</li><li>Lines 541 and 542 build the ranges of four groups: <code>C_ASM_AR</code>, <code>X_READ_AO</code>, <code>X_READ_AA</code>, <code>X_ASM_AR</code>.</li><li><code>X_PAIRS</code> puts each of three part C ranges next to the bwx range with the same kernel and the same kernel directly before.</li><li>The script stops unless each part C range lies fully above its bwx range. <code>X_ABOVE</code> holds the three distances of the nearest ends.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 546  X_MAX_READ = max(val(r) for r in X_LOADS if r["kernel"] == "read")
 547  X_MAX_ASM = max(val(r) for r in X_LOADS if r["kernel"] == "asmread")
 548  need(X_MAX_READ == max(rX_read_ao.hi, rX_read_aa.hi) and X_MAX_ASM == rX_asm_ar.hi, "runner bwx: the highest read or asmread value is not in the three ranges used")
 549  X_REV_MAX_READ, X_REV_MAX_ASM = max(val(r) for r in X_REV_READ), max(val(r) for r in X_REV_ASM)
 550  need(X_REV_MAX_READ &gt; X_MAX_READ and X_REV_MAX_ASM &gt; X_MAX_ASM, "runner bwx: the reverse-order processes do not hold higher values")
 551  need(rC_read_ao.lo &lt;= X_REV_MAX_READ &lt;= rC_read_ao.hi and rC_read_aa.lo &lt;= X_REV_MAX_READ &lt;= rC_read_aa.hi,
 552       "runner bwx, reverse order: the highest read value is not inside both read ranges of part C")
 553  need(rL_asm.lo &lt;= X_REV_MAX_ASM &lt;= rL_asm.hi, "runner bwx, reverse order: the highest asmread value is not inside the asmread range of part L")
 554</pre></td><td valign="top"><ul><li><code>X_MAX_READ</code>, <code>X_MAX_ASM</code>: the highest <code>read</code> rate and the highest <code>asmread</code> rate of all records of <code>X_LOADS</code>.</li><li>Line 548: the script stops unless these two maxima are upper ends of the three bwx ranges of line 542. So no <code>asmread</code> interval at position 5 holds a higher rate than the highest one at position 2.</li><li><code>X_REV_MAX_READ</code>, <code>X_REV_MAX_ASM</code>: the highest rates of the reverse-order processes. The script stops unless each is above the maximum of <code>X_LOADS</code> for the same kernel.</li><li>Lines 551 to 553: the script stops unless the highest reverse-order <code>read</code> rate lies inside both <code>read</code> ranges of part C, and the highest reverse-order <code>asmread</code> rate lies inside the <code>asmread</code> range of part L.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>md_sections</code>: split <code>FACTS.md</code> into sections</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 555  # ------------------------------------------------------------------ cross-check with FACTS.md and facts.json verdicts
 556  def md_sections(md):
 557      secs, cur = {}, None
 558      for line in md.splitlines():
 559          m = re.match(r"^#{2,3} (.*)$", line)
 560          if m:
 561              k = re.match(r"^(\d+(?:\.\d+)?)[. ]", m.group(1))
 562              cur = k.group(1) if k else "#" + m.group(1)
 563              secs[cur] = []
 564          elif cur is not None:
 565              secs[cur].append(line)
 566      return {k: "\n".join(v) for k, v in secs.items()}
 567
 568</pre></td><td valign="top"><ul><li>It goes through the text line by line. A line that starts with <code>## </code> or <code>### </code> is a heading and starts a new section.</li><li>The key of a section is the number at the start of its heading, for example <code>0</code>, <code>3.4</code> or <code>4.9</code>. A heading without a number gets the key <code>#</code> plus its text.</li><li>The lines below a heading, up to the next heading of these two levels, are the text of the section. So the text of section <code>3</code> ends where section <code>3.1</code> starts.</li><li>Lines before the first heading are dropped.</li><li>It returns a dictionary from key to section text.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>md_tables</code>: parse the Markdown tables of a text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 569  def md_tables(text):
 570      tables, cur = [], None
 571      for line in text.splitlines():
 572          if line.startswith("|"):
 573              cells = [c.strip() for c in line.strip().strip("|").split("|")]
 574              if cur is None:
 575                  cur = {"head": cells, "rows": []}
 576                  tables.append(cur)
 577              elif set("".join(cells)) &lt;= set("-: "):
 578                  continue
 579              else:
 580                  cur["rows"].append(dict(zip(cur["head"], cells)))
 581          else:
 582              cur = None
 583      return tables
 584
 585</pre></td><td valign="top">This function belongs to the cross-check block that starts in line 555. A Markdown table is a group of text lines that start with <code>|</code>. The cells stand between the <code>|</code> characters.<ul><li>The first line of a table gives the column titles (<code>head</code>).</li><li>A later line whose cells hold only the characters <code>-</code>, <code>:</code> and space is the separator line. It is skipped.</li><li>Every other line becomes one dictionary from column title to cell text.</li><li>A line that does not start with <code>|</code> ends the table.</li></ul>The function returns a list with one entry per table.</td></tr>
<tr><td colspan="2"><b><code>SEC</code>: the sections of FACTS.md, and the number pattern <code>NUM</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 586  SEC = md_sections(FMD)
 587  for k_ in ("0", "3.1", "3.2", "3.3", "3.4", "4.2", "4.3", "4.4", "4.5", "4.6", "4.9"):
 588      need(k_ in SEC and SEC[k_].strip(), f"FACTS.md: section {k_} not found")
 589  NUM = r"[-+]?\d+(?:\.\d+)?"
 590
 591</pre></td><td valign="top"><code>md_sections</code> (line 556) splits the text of FACTS.md at its headings. <code>SEC</code> maps a section number, for example <code>3.4</code>, to the text of that section.<ul><li>The script stops unless 11 sections exist and hold text. These are the sections that the cross-checks of lines 652 to 767 read.</li><li><code>NUM</code> is the regular expression for one number: an optional sign, digits, and an optional decimal part.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>col</code>: one cell of a table row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 592  def col(row, start):
 593      ks = [k for k in row if k.startswith(start)]
 594      need(len(ks) == 1, f"FACTS.md table: no single column that starts with '{start}'")
 595      return row[ks[0]]
 596
 597</pre></td><td valign="top"><code>col</code> returns the cell whose column title starts with the text <code>start</code>. The script stops unless exactly one column title of the row starts with that text. The callers use it for long titles. Example: line 703 finds the title <code>Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)</code> with the start <code>Distance of the nearest ends</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>facts_row</code>: find one row of a FACTS.md table</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 598  def facts_row(sec, where, what):
 599      """The first table row of a FACTS.md section for which where(row) is true."""
 600      for t in md_tables(SEC[sec]):
 601          for row in t["rows"]:
 602              try:
 603                  if where(row):
 604                      return row
 605              except KeyError:
 606                  continue
 607      stop(f"FACTS.md section {sec}: row not found: {what}")
 608
 609</pre></td><td valign="top"><code>facts_row</code> reads all tables of one FACTS.md section in their order.<ul><li>It returns the first row for which the test function <code>where</code> is true.</li><li>A test can read a column that the table of a row lacks. Python then raises <code>KeyError</code>, and the row is skipped.</li><li>The script stops when no row passes the test.</li></ul></td></tr>
<tr><td colspan="2"><b>Functions <code>rng_of</code> and <code>near</code>: read a range, compare two values</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 610  def rng_of(cell):
 611      m = re.search(rf"({NUM}) to ({NUM})", cell)
 612      need(m, f"FACTS.md: no range in cell '{cell}'")
 613      return Decimal(m.group(1)), Decimal(m.group(2))
 614
 615
 616  def near(a, b, tol):
 617      return abs(D(a) - D(b)) &lt;= Decimal(tol)
 618
 619</pre></td><td valign="top"><ul><li><code>rng_of</code> finds the first text of the form <code>number to number</code> in a table cell. It returns the two numbers as <code>Decimal</code>. The script stops when the cell holds no such text.</li><li><code>near</code> is the comparison that the cross-checks use for rates, distances and percent values. It converts both values to <code>Decimal</code>. It is true when they differ by at most the tolerance <code>tol</code> (the largest allowed difference).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>xc_range</code>: a computed range against a table cell</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 620  def xc_range(label, rg_lo, rg_hi, cell, tol="0.01", unit="GB/s", fmt=f2):
 621      lo, hi = rng_of(cell)
 622      check(near(q(rg_lo, tol), lo, tol) and near(q(rg_hi, tol), hi, tol),
 623            f"{label}: computed {fmt(rg_lo)} to {fmt(rg_hi)} {unit}, FACTS.md {lo} to {hi} {unit}")
 624
 625</pre></td><td valign="top"><ul><li><code>rng_of</code> reads the two numbers of the FACTS.md cell.</li><li><code>q</code> (line 90) rounds the computed lowest value and the computed highest value to the rounding step <code>tol</code>. The default is 0.01 (GB/s). A value exactly between two steps is rounded away from zero.</li><li>The check passes when each rounded value differs from its FACTS.md number by at most <code>tol</code>. So a difference of 0.01 GB/s in the last digit still passes.</li><li><code>check</code> adds one PASS or FAIL line that prints both ranges. After a FAIL the script continues, and it does not write the page at the end.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>xc_val</code>: a computed value against a table cell</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 626  def xc_val(label, mine, cell, tol="0.01", unit="GB/s", fmt=f2):
 627      m = re.search(NUM, cell)
 628      need(m, f"FACTS.md: no number in cell '{cell}'")
 629      theirs = Decimal(m.group(0))
 630      check(near(q(mine, tol), theirs, tol), f"{label}: computed {fmt(mine)} {unit}, FACTS.md {theirs} {unit}")
 631
 632</pre></td><td valign="top"><code>xc_val</code> does the same for one value.<ul><li>It takes the first number of the cell, with its sign. The script stops when the cell holds no number.</li><li>The computed value is rounded to <code>tol</code> and compared with <code>near</code>.</li><li>The callers pass 0.01 for a rate in GB/s and 0.1 for a percent value.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>xc_text</code>: a computed value against the text of a section</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 633  def xc_text(label, sec, value, unit, tol="0.01", fmt=f2):
 634      """A number with this unit, equal within the tolerance, stands in the text of a FACTS.md section."""
 635      found = [Decimal(x) for x in re.findall(rf"({NUM}) ?{re.escape(unit)}", SEC[sec])]
 636      check(any(near(q(abs(D(value)), tol), x, tol) for x in found),
 637            f"{label}: computed {fmt(abs(D(value)))} {unit}, present in FACTS.md section {sec}")
 638
 639</pre></td><td valign="top"><code>xc_text</code> is for a value that FACTS.md gives in a sentence and not in a table cell.<ul><li>It collects every number of the section text that is followed by the unit, with at most one space between them.</li><li>It takes the computed value without its sign and rounds it to <code>tol</code>.</li><li>The check passes when at least one collected number differs from it by at most <code>tol</code>.</li><li>The check does not test which sentence holds the number.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>xc_text_range</code>: a computed range against the text of a section</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 640  def xc_text_range(label, sec, lo, hi, unit_mid, tol, fmt):
 641      found = re.findall(rf"({NUM}){re.escape(unit_mid)} to ({NUM})", SEC[sec])
 642      check(any(near(q(lo, tol), Decimal(a), tol) and near(q(hi, tol), Decimal(b), tol) for a, b in found),
 643            f"{label}: computed {fmt(lo)} to {fmt(hi)}, present in FACTS.md section {sec}")
 644
 645</pre></td><td valign="top"><code>xc_text_range</code> collects every text of this form in the section: a number, the text <code>unit_mid</code>, the word <code>to</code>, a number. Example with <code>unit_mid</code> = <code> %</code>: the text <code>30.5 % to 31.2</code>. The check passes when one collected pair of numbers differs from the two rounded computed values by at most <code>tol</code> each. As in <code>xc_text</code>, the place of the text inside the section is not tested.</td></tr>
<tr><td colspan="2"><b>Function <code>xc_drops</code>: computed drops against a table row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 646  def xc_drops(label, ds, row):
 647      lo, hi = Decimal(col(row, "Smallest drop")), Decimal(col(row, "Largest drop"))
 648      check(near(q(min(ds), "0.1"), lo, "0.1") and near(q(max(ds), "0.1"), hi, "0.1"),
 649            f"{label}: computed {f1(min(ds))} % to {f1(max(ds))} %, FACTS.md {lo} % to {hi} %")
 650
 651</pre></td><td valign="top"><code>xc_drops</code> takes the lowest and the highest drop of a list and rounds each to 0.1 (percent).<ul><li>The drops of the list were computed with <code>drop</code> (line 417) from rates that this script had not rounded for printing.</li><li>For a bwx12 pair, the two rates are values of <code>val</code>, rounded to 6 decimals (line 188).</li><li>For part A, the two rates are medians. Each is the median of the 3 rates of one process, as the csv file holds them (2 decimals).</li><li>The columns <code>Smallest drop</code> and <code>Largest drop</code> of the FACTS.md row give the two numbers to compare with.</li><li>The check passes when each pair differs by at most 0.1 (percent).</li></ul></td></tr>
<tr><td colspan="2"><b>Cross-check of question Q1 with FACTS.md</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 652  # Q1 (headline values)
 653  T34 = lambda part, frag: facts_row("3.4", lambda r: r["Part"].startswith(part) and frag in r["Pair"], f"{part} {frag}")
 654  xc_drops("Q1 part C, read directly after oldread", Q1["C_ao"]["drops"], T34("C", "`read` (new read kernel) directly after `oldread`"))
 655  xc_drops("Q1 part C, read directly after asmread", Q1["C_aa"]["drops"], T34("C", "`read` (new read kernel) directly after `asmread`"))
 656  xc_drops("Q1 part L, asmread against oldread", Q1["L"]["drops"], T34("L", "asmread"))
 657  xc_drops("Q1 part A, process medians", Q1["A"]["drops"], T34("A", "bw_new"))
 658  xc_drops("Q1 control I", Q1["I"]["drops"], T34("I (control", "asmread"))
 659  xc_drops("Q1 F72d12", Q1["F"]["drops"], T34("F72d12", "asmread"))</pre></td><td valign="top"><code>T34</code> returns one row of the table in FACTS.md section 3.4. The column <code>Part</code> of that row starts with the first text, and its column <code>Pair</code> holds the second text. Six <code>xc_drops</code> calls compare the drops of <code>Q1</code> (line 430) with that table:<ul><li>part C: bwx12 kernel <code>read</code> directly after <code>oldread</code> (4 pairs), and directly after <code>asmread</code> (4 pairs),</li><li>part L: <code>asmread</code> against <code>oldread</code> (6 pairs),</li><li>part A: the 6 drops between the medians of two processes,</li><li>control I (4 pairs) and F72d12 (2 pairs).</li></ul>The table has 9 rows. Its three rows for <code>asmread</code> in part C have no check here. The saved output of a build shows 30.5 % to 31.2 % and 29.7 % to 31.1 % for part C, both computed and in FACTS.md [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 660  G33 = lambda g: facts_row("3.3", lambda r: r["Group"].startswith(g), g)
 661  xc_range("part C, read after oldread", rC_read_ao.lo, rC_read_ao.hi, col(G33("read after oldread"), "Min to max"))
 662  xc_range("part C, read after asmread", rC_read_aa.lo, rC_read_aa.hi, col(G33("read after asmread"), "Min to max"))
 663  xc_range("part C, oldread", rC_old.lo, rC_old.hi, col(G33("oldread, all positions"), "Min to max"))
 664  for key_, ds in (("C_ao", Q1["C_ao"]["drops"]), ("C_aa", Q1["C_aa"]["drops"]), ("L", Q1["L"]["drops"]), ("A", Q1["A"]["drops"])):
 665      xc_text_range(f"Q1 drop {key_} in the Short version of FACTS.md", "0", min(ds), max(ds), " %", "0.1", f1)</pre></td><td valign="top"><code>G33</code> returns the row of FACTS.md section 3.3 whose column <code>Group</code> starts with the given text.<ul><li>Three <code>xc_range</code> calls compare the lowest and the highest rate of a part C group with the column <code>Min to max</code> of its row. The groups are <code>read</code> after <code>oldread</code> (4 intervals), <code>read</code> after <code>asmread</code> (4 intervals) and all <code>oldread</code> intervals (8 intervals).</li><li>The loop tests with <code>xc_text_range</code> that section 0 of FACTS.md (its Short version) holds four drop ranges, to 0.1 percent: the two of part C, the one of part L and the one of part A.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 666  g0 = len(CHECKS)
 667  for (s_, rnd), p in A_PAIRS.items():
 668      row = facts_row("3.1", lambda r, s_=s_, rnd=rnd: r["Session"] == str(s_) and r["Round"] == str(rnd) and "New below old, %" in r,
 669                      f"session {s_} round {rnd}")
 670      xc_val(f"part A session {s_} round {rnd}, median bw_old read", p["old"].med, row["bw_old read, median GB/s"])
 671      xc_val(f"part A session {s_} round {rnd}, median bw_new read", p["new"].med, row["bw_new read, median GB/s"])
 672      xc_val(f"part A session {s_} round {rnd}, new below old", p["drop"], row["New below old, %"], "0.1", "%", f1)
 673  grouped("FACTS.md section 3.1, part A per session and round: medians of bw_old read and bw_new read (0.01 GB/s) and the drop (0.1 %)", g0)</pre></td><td valign="top">Part A, one set of comparisons per session and round (the 6 entries of <code>A_PAIRS</code>, line 451).<ul><li><code>facts_row</code> finds the row of section 3.1 with the same <code>Session</code> and <code>Round</code>, in the table that has the column <code>New below old, %</code>.</li><li><code>xc_val</code> compares the median of the 3 intervals of <code>bw_old read</code> and the median of the 3 intervals of <code>bw_new read</code>, each to 0.01 GB/s.</li><li><code>xc_val</code> compares the drop between the two medians with the column <code>New below old, %</code>, to 0.1 percent.</li><li><code>g0</code> is the length of <code>CHECKS</code> before the loop. <code>grouped</code> (line 56) replaces the 18 lines of the loop by one line that counts the equal comparisons.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 674  g0 = len(CHECKS)
 675  for o, n in Q1["L"]["pairs"] + Q1["I"]["pairs"] + Q1["F"]["pairs"]:
 676      tag = n["tag"] if n["dataset"] != "F72d12" else "F72d12"
 677      row = facts_row("3.2", lambda r, tag=tag, n=n: r["Folder tag or row"] == tag and r["Round"] == str(n["round"]), f"{tag} round {n['round']}")
 678      xc_val(f"{tag} round {n['round']}, oldread", val(o), row["oldread, GB/s"])
 679      xc_val(f"{tag} round {n['round']}, asmread", val(n), row["asmread, GB/s"])
 680      xc_val(f"{tag} round {n['round']}, asmread below oldread", drop(val(o), val(n)), row["asmread below oldread, %"], "0.1", "%", f1)
 681  grouped("FACTS.md section 3.2, part L, control I and F72d12 per process and round: oldread and asmread (0.01 GB/s) and the drop (0.1 %)", g0)
 682</pre></td><td valign="top">The same for the 12 pairs of part L (6), control I (4) and F72d12 (2).<ul><li>The row of section 3.2 is found by its column <code>Folder tag or row</code> and by the round. For F72d12 the text <code>F72d12</code> is used in place of the folder tag.</li><li>Three values are compared: the <code>oldread</code> rate and the <code>asmread</code> rate of the pair (each the value of <code>val</code>, to 0.01 GB/s) and the drop of the pair (to 0.1 percent).</li><li><code>grouped</code> joins the 36 comparisons into one line.</li></ul></td></tr>
<tr><td colspan="2"><b>Cross-check of question Q2 with FACTS.md: old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 683  # Q2 old read kernel (headline values)
 684  R42 = lambda name: facts_row("4.2", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)
 685  C42 = lambda a, b: facts_row("4.2", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"].startswith(b), f"{a} / {b}")
 686  xc_range("Q2 old read, part A", rA_old.lo, rA_old.hi, R42("part A, sessions 1 to 3")["Min to max, GB/s"])
 687  xc_range("Q2 old read, pool A-1 to A-3", rPA_old.lo, rPA_old.hi, R42("pool A-1 to A-3")["Min to max, GB/s"])
 688  xc_range("Q2 old read, part L", rL_old.lo, rL_old.hi, R42("part L (T72L1 to T72L3)")["Min to max, GB/s"])
 689  xc_range("Q2 old read, pool L-1 to L-4", rPL_old.lo, rPL_old.hi, R42("pool L-1 to L-4")["Min to max, GB/s"])
 690  xc_range("Q2 old read, part C", rC_old.lo, rC_old.hi, R42("part C, all oldread intervals")["Min to max, GB/s"])
 691  xc_range("Q2 old read, F72d12", rF_old.lo, rF_old.hi, R42("F72d12")["Min to max, GB/s"])
 692  xc_range("Q2 old read, control I", rI_old.lo, rI_old.hi, R42("control I")["Min to max, GB/s"])
 693  xc_val("Q2 old read, median of part L", rL_old.med, R42("part L (T72L1 to T72L3)")["Median, GB/s"])
 694  xc_val("Q2 old read, median of pool L-1 to L-4", rPL_old.med, R42("pool L-1 to L-4")["Median, GB/s"])</pre></td><td valign="top"><code>R42</code> returns one row of FACTS.md section 4.2. The column <code>Row</code> of that row starts with the given name, and its table has the column <code>Min to max, GB/s</code>. <code>C42</code> returns the comparison row for a 7200 MT/s row and an 8000 MT/s range.<ul><li>Lines 686 to 692 compare 7 computed ranges of the old read kernel: part A, the pool A-1 to A-3, part L, the pool L-1 to L-4, part C, F72d12 and control I.</li><li>Lines 693 and 694 compare the median of part L and the median of the pool L-1 to L-4 with the column <code>Median, GB/s</code>.</li></ul>Each computed range is the lowest and the highest value of <code>val</code> in its group of records (class <code>Rg</code>, line 192).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 695  row = C42("part A, sessions 1 to 3", "pool A-1 to A-3")
 696  check(WORD_SAME in col(row, "Wording") and wording(rA_old, rPA_old) == WORD_SAME, f'Q2 old read, part A: wording "{WORD_SAME}" computed and in FACTS.md')
 697  xc_val("Q2 old read, part A: size the test cannot exclude (est.)", width_pct(rPA_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)
 698  row = C42("part C, all oldread intervals", "pool L-1 to L-4 (position 0)")
 699  check(WORD_SAME in col(row, "Wording") and wording(rC_old, rPL_old) == WORD_SAME, f'Q2 old read, part C: wording "{WORD_SAME}" computed and in FACTS.md')
 700  xc_val("Q2 old read, part C: size the test cannot exclude (est.)", width_pct(rPL_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)</pre></td><td valign="top">Two comparisons with overlap: part A against the pool A-1 to A-3, and part C against the pool L-1 to L-4.<ul><li>The <code>check</code> call needs two things. The column <code>Wording</code> of the FACTS.md row must hold <code>no difference seen</code>. <code>wording</code> (line 481) must return the same text for the two computed ranges.</li><li><code>xc_val</code> compares <code>width_pct</code> of the 8000 MT/s pool (line 476) with the column <code>Width of the 8000 MT/s range</code>, to 0.1 percent. This width is the size that the test cannot exclude (est.).</li></ul>The saved output of a build shows 1.2 % for part A and 1.0 % for part C [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 701  row = C42("part L", "pool L-1 to L-4")
 702  check(WORD_DIFF in col(row, "Wording") and wording(rL_old, rPL_old) == WORD_DIFF, f'Q2 old read, part L: wording "{WORD_DIFF}" computed and in FACTS.md')
 703  xc_val("Q2 old read, part L: distance of the nearest ends", L_OLD_NEAR, col(row, "Distance of the nearest ends"))
 704  xc_text("Q2 old read, part L: distance of the medians", "4.9", L_OLD_MED, "GB/s")
 705  xc_text("Q2 old read, part L: nearest ends in percent", "4.9", L_OLD_NEAR_PCT, "%", "0.1", f1)
 706  xc_text("Q2 old read, part L: medians in percent", "4.9", L_OLD_MED_PCT, "%", "0.1", f1)
 707  for nm, rg in (("F72d12", rF_old), ("control I", rI_old)):
 708      row = C42(nm, "pool L-1 to L-4")
 709      check(col(row, "Overlap") == "yes" and rg.overlaps(rPL_old), f"Q2 old read, {nm}: overlaps the 8000 MT/s pool, computed and in FACTS.md")
 710</pre></td><td valign="top">Part L against the pool L-1 to L-4. This is the one comparison of the old read kernel in which the two ranges do not overlap.<ul><li>The wording must be the text for a difference, both in the FACTS.md row and from <code>wording</code>.</li><li><code>L_OLD_NEAR</code> (line 489) is compared with the column <code>Distance of the nearest ends</code>. The value is negative: part L is the lower range.</li><li>Three <code>xc_text</code> calls test that section 4.9 holds three values. The first is the difference of the two medians in GB/s. The second is the distance of the nearest ends in percent of the lower end of the 8000 MT/s range (line 491). The third is the difference of the medians in percent of the 8000 MT/s median (line 492).</li><li>For F72d12 and for control I the check passes when the column <code>Overlap</code> reads <code>yes</code> and the computed range overlaps the pool.</li></ul>The saved output of a build shows -1.24 GB/s, 6.27 GB/s, 0.3 % and 1.3 % [Ref5].</td></tr>
<tr><td colspan="2"><b>Cross-check of question Q2 with FACTS.md: load-only loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 711  # Q2 load-only loop (headline values)
 712  R44 = lambda name: facts_row("4.4", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)
 713  C44 = lambda a, b: facts_row("4.4", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"] == b, f"{a} / {b}")
 714  xc_range("Q2 load-only, part L asmread", rL_asm.lo, rL_asm.hi, R44("part L (T72L1 to T72L3)")["Min to max, GB/s"])
 715  xc_range("Q2 load-only, pool L-1 to L-4 asmread", rPL_asm.lo, rPL_asm.hi, R44("pool L-1 to L-4")["Min to max, GB/s"])
 716  xc_range("Q2 load-only, F72d12 asmread", rF_asm.lo, rF_asm.hi, R44("F72d12")["Min to max, GB/s"])
 717  xc_range("Q2 load-only, control I asmread", rI_asm.lo, rI_asm.hi, R44("control I")["Min to max, GB/s"])
 718  row = C44("part L", "pool L-1 to L-4")
 719  check(WORD_DIFF in col(row, "Wording") and wording(rL_asm, rPL_asm) == WORD_DIFF, f'Q2 load-only, part L: wording "{WORD_DIFF}" computed and in FACTS.md')
 720  xc_val("Q2 load-only, part L: distance of the nearest ends", DIST["nearest"][0], col(row, "Distance of the nearest ends"))
 721  xc_val("Q2 load-only, F72d12 above L-1 alone", rF_asm.nearest(rL1_asm), col(C44("F72d12", "L-1 alone"), "Distance of the nearest ends"))
 722  check(col(C44("F72d12", "pool L-1 to L-4"), "Overlap") == "yes", "Q2 load-only, F72d12: inside the 8000 MT/s pool range, computed and in FACTS.md")
 723  xc_val("Q2 load-only, control I above the pool", rI_asm.nearest(rPL_asm), col(C44("control I", "pool L-1 to L-4"), "Distance of the nearest ends"))</pre></td><td valign="top"><code>R44</code> and <code>C44</code> do for section 4.4 what <code>R42</code> and <code>C42</code> do for section 4.2. <code>C44</code> requires that the cell <code>8000 MT/s range used</code> is exactly the given text, not only its start.<ul><li>Lines 714 to 717: the <code>asmread</code> ranges of part L, the pool L-1 to L-4, F72d12 and control I.</li><li>Lines 718 to 720: part L against the pool. The wording must be the text for a difference. The distance of the nearest ends is the first value of <code>DIST["nearest"]</code> (line 504).</li><li>Line 721: the distance by which F72d12 lies above row L-1 alone.</li><li>Line 722 reads FACTS.md only: the column <code>Overlap</code> of F72d12 against the pool must read <code>yes</code>. Lines 495 and 496 asserted the computed side.</li><li>Line 723: the distance by which control I lies above the pool.</li></ul>The saved output of a build shows 12.48 GB/s for part L, 1.73 GB/s for F72d12 and 4.61 GB/s for control I [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 724  for rnd in (1, 2):
 725      row = facts_row("4.3", lambda r, rnd=rnd: r["Binary and kernel"] == "bw_new read" and r["Round"] == str(rnd) and "Wording by rule V3" in r, f"bw_new read round {rnd}")
 726      v = A_V3[rnd]
 727      xc_range(f"Q2 part A, bw_new read, round {rnd}: 8000 MT/s range", v["r8"].lo, v["r8"].hi, row["8000 MT/s range of the round, GB/s"])
 728      cell7 = [Decimal(x) for x in re.findall(r"(\d+\.\d+) \(\d+\)", row["7200 MT/s, session 1"])]
 729      check(len(cell7) == 3 and near(min(cell7), q(v["r7"].lo), "0.01") and near(max(cell7), q(v["r7"].hi), "0.01"),
 730            f"Q2 part A, bw_new read, round {rnd}: session 1 computed {v['r7'].txt()} GB/s, FACTS.md {min(cell7)} to {max(cell7)} GB/s")
 731      check(row["Wording by rule V3"] == "outside (above)", f"Q2 part A, bw_new read, round {rnd}: wording outside (above), computed and in FACTS.md")
 732      xc_val(f"Q2 part A, bw_new read, round {rnd}: distance of the nearest ends", v["near"], col(row, "Distance to the nearer end"))
 733      pc = sorted(int(x) for x in re.findall(r"\((\d+)\)", row["8000 MT/s, A-1, same round"] + row["8000 MT/s, A-2, same round"]))
 734      check(pc == v["p8"], f"Q2 part A, bw_new read, round {rnd}: pass counts at 8000 MT/s {v['p8']}, FACTS.md {pc}")</pre></td><td valign="top">New read kernel of part A (<code>bw_new read</code>), once per round (rule V3). <code>v</code> is the entry of <code>A_V3</code> for the round (line 509). The row comes from the table of section 4.3 that has the column <code>Wording by rule V3</code>.<ul><li>The range of the 6 intervals of rows A-1 and A-2 (<code>r8</code>) is compared with the column <code>8000 MT/s range of the round, GB/s</code>.</li><li>The cell <code>7200 MT/s, session 1</code> must hold three texts of the form <code>rate (pass count)</code>. Their lowest and highest rate are compared with the range of the 3 intervals of session 1 (<code>r7</code>), to 0.01 GB/s.</li><li>The cell <code>Wording by rule V3</code> must read <code>outside (above)</code>. Line 514 asserted the computed side.</li><li>The distance of the nearest ends is compared with the first number of the column <code>Distance to the nearer end</code>.</li><li>The pass counts in the two 8000 MT/s cells, sorted, must equal the list <code>p8</code> of the records.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 735  row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after oldread") and r["8000 MT/s range used"].startswith("pool L-1 to L-4 (after oldread)"), "part C asmread after oldread")
 736  xc_range("Q2 load-only, part C asmread after oldread", rC_asm_ao.lo, rC_asm_ao.hi, col(row, "Its range"))
 737  xc_val("Q2 load-only, part C asmread after oldread: distance", rC_asm_ao.nearest(rPL_asm), col(row, "Distance of the nearest ends"))
 738  check("Insufficient data: no 8000 MT/s run of kernel read with bwx12" in SEC["4.5"], "Q2 part C, kernel read: Insufficient data wording present in FACTS.md section 4.5")</pre></td><td valign="top">Part C, <code>asmread</code> directly after <code>oldread</code> (2 intervals), against the <code>asmread</code> range of the pool L-1 to L-4. The row of section 4.5 gives the range in the column <code>Its range</code> and the distance of the nearest ends. Line 738 tests that section 4.5 holds the text <code>Insufficient data: no 8000 MT/s run of kernel read with bwx12</code>. The check tests only that this text is present.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 739  xc_text("three visits of the 7200 MT/s boot: span", "4.6", VISIT_HI - VISIT_LO, "GB/s")
 740  xc_text_range("three visits of the 7200 MT/s boot: lowest to highest asmread", "4.9", VISIT_LO, VISIT_HI, "", "0.01", f2)
 741  for kind in ("nearest", "medians", "farthest"):
 742      xc_text(f"part L above the 8000 MT/s pool, {kind}", "4.6", DIST[kind][0], "GB/s")
 743      xc_text(f"part L above F72d12, {kind}", "4.6", DIST[kind][1], "GB/s")
 744  xc_text("same line in the 7200 MT/s boot: span of oldread", "3.4", VISIT_OLD_HI - VISIT_OLD_LO, "GB/s")</pre></td><td valign="top">The three visits of the part L line in the 7200 MT/s boot: F72d12, part L and control I.<ul><li>Line 739: the <code>asmread</code> span <code>VISIT_HI - VISIT_LO</code> (line 501) must stand in section 4.6 with the unit GB/s. The span is the highest value of the three visits minus the lowest value.</li><li>Line 740: section 4.9 must hold the lowest and the highest value as a text of the form <code>X to Y</code>.</li><li>Lines 741 to 743: the three kinds of distance in <code>DIST</code> must stand in section 4.6, each for part L above the 8000 MT/s pool and for part L above F72d12.</li><li>Line 744: the same span for <code>oldread</code> (line 502) must stand in section 3.4.</li></ul>The saved output of a build shows 26.03 GB/s for <code>asmread</code> and 7.59 GB/s for <code>oldread</code> [Ref5].</td></tr>
<tr><td colspan="2"><b>Cross-check: range widths of part A, rows of runner bwx</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 745  # part A, old read: widths of the two ranges. Rows of runner bwx: ranges, distances and highest values (note under Table 2)
 746  g0 = len(CHECKS)
 747  xc_text("part A, old read: width of the 7200 MT/s range", "0", A_OLD_W7, "GB/s")
 748  xc_text("part A, old read: width of the 8000 MT/s range", "0", A_OLD_W8, "GB/s")
 749  check(f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range and {len(A_OLD_ABOVE)} lie above it" in SEC["0"],
 750        f"part A, old read: {len(A_OLD_BELOW)} of {rA_old.n} intervals below the 8000 MT/s range and {len(A_OLD_ABOVE)} above it, computed and in FACTS.md section 0")
 751  grouped("FACTS.md section 0, part A, old read kernel: widths of the two ranges (0.01 GB/s) and the intervals outside the 8000 MT/s range", g0)</pre></td><td valign="top">Old read kernel in part A.<ul><li>Two <code>xc_text</code> calls test that section 0 holds the width of the 7200 MT/s range (<code>A_OLD_W7</code>) and the width of the 8000 MT/s pool range (<code>A_OLD_W8</code>), both from line 527.</li><li>The <code>check</code> call builds the text <code>N of its M intervals lie below that range and K lie above it</code> from the computed counts (lines 525 and 526). It passes when section 0 holds this text.</li><li><code>grouped</code> joins the 3 comparisons into one line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 752  g0 = len(CHECKS)
 753  X45 = lambda name: facts_row("4.5", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)["Min to max, GB/s"]
 754  xc_range("runner bwx, read at position 1", rX_read_ao.lo, rX_read_ao.hi, X45("pool B7a, B7b, C3a, C3b, position 1"))
 755  xc_range("runner bwx, read at position 6", rX_read_aa.lo, rX_read_aa.hi, X45("pool B7a, B7b, C3a, C3b, position 6"))
 756  xc_range("runner bwx, asmread at position 2", rX_asm_ar.lo, rX_asm_ar.hi, X45("pool B7a, B7b, C3a, C3b, position 2"))
 757  xc_text("part C, read after oldread, above the bwx rows", "4.5", X_ABOVE[0], "GB/s")
 758  xc_text("part C, read after asmread, above the bwx rows", "4.5", X_ABOVE[1], "GB/s")
 759  row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after read") and r["8000 MT/s range used"].startswith("other binary bwx"),
 760                  "part C asmread after read against runner bwx")
 761  xc_val("part C, asmread after read, above the bwx rows", X_ABOVE[2], col(row, "Distance of the nearest ends"))
 762  xc_text("runner bwx: highest read value of the rows of rule V2 point 4", "4.6", X_MAX_READ, "GB/s")
 763  xc_text("runner bwx: highest asmread value of the rows of rule V2 point 4", "4.6", X_MAX_ASM, "GB/s")
 764  xc_text("runner bwx, reverse order: highest read value", "4.6", X_REV_MAX_READ, "GB/s")
 765  xc_text("runner bwx, reverse order: highest asmread value", "4.6", X_REV_MAX_ASM, "GB/s")
 766  check(f"({len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot" in SEC["4.6"], f"runner bwx: {len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot, computed and in FACTS.md section 4.6")
 767  grouped("FACTS.md sections 4.5 and 4.6, rows of runner bwx: 3 ranges, 3 distances and 4 highest values (0.01 GB/s), and n", g0)
 768</pre></td><td valign="top">Rows of the older runner bwx, for the note under Table 2. <code>X45</code> returns the cell <code>Min to max, GB/s</code> of a row of section 4.5.<ul><li>Lines 754 to 756: three ranges of the pool of the bwx datasets B7a, B7b, C3a and C3b: <code>read</code> at position 1, <code>read</code> at position 6 and <code>asmread</code> at position 2.</li><li>Lines 757 to 761: the three distances of <code>X_ABOVE</code> (line 545), by which a part C group lies above one of these ranges. Two are searched in the text of section 4.5. The third is compared with a table cell.</li><li>Lines 762 to 765: the four highest values of lines 546 to 549, searched in section 4.6.</li><li>Line 766: the text for n, searched in section 4.6. The counts come from the records: 192 intervals of 24 processes (line 326).</li></ul><code>grouped</code> joins the 11 comparisons into one line.</td></tr>
<tr><td colspan="2"><b>Function <code>vrow</code>: one verdict record of facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 769  # the same values against the "verdicts" records of facts.json
 770  V = FJ["verdicts"]
 771
 772
 773  def vrow(part, kernel, row7, scope8):
 774      hit = [r for r in V["q2_rows"] if r["part"] == part and r["kernel"] == kernel and r["row_7200"] == row7 and r["scope_8000"] == scope8]
 775      need(len(hit) == 1, f"facts.json verdicts: no single row {part} / {kernel} / {row7} / {scope8}")
 776      return hit[0]
 777
 778</pre></td><td valign="top"><code>V</code> is the part <code>verdicts</code> of facts.json. The modules <code>facts_text.py</code> and <code>facts_text4.py</code> computed its values during a run of <code>build_facts.py</code>. <code>vrow</code> returns the entry of the list <code>q2_rows</code> with the given part, kernel, 7200 MT/s row and 8000 MT/s scope. The script stops unless exactly one entry matches.</td></tr>
<tr><td colspan="2"><b>Function <code>xv</code>: two computed ranges against a verdict record</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 779  def xv(label, r7, r8, vr, dist):
 780      ok = (near(r7.lo, vr["lo_7200"], "0.001") and near(r7.hi, vr["hi_7200"], "0.001") and near(r8.lo, vr["lo_8000"], "0.001")
 781            and near(r8.hi, vr["hi_8000"], "0.001") and near(dist, vr["distance_GBps"], "0.001") and r7.overlaps(r8) == vr["overlap"]
 782            and r7.n == vr["n_7200"] and r8.n == vr["n_8000"] and r7.np == vr["processes_7200"] and r8.np == vr["processes_8000"])
 783      check(ok, f"{label}: ranges, n, overlap and distance equal to the verdict record of facts.json")
 784
 785</pre></td><td valign="top"><ul><li>The lowest and the highest value of both ranges and the distance <code>dist</code> must each differ from the field of the record by at most 0.001 GB/s. The computed values are not rounded before this comparison. <code>build_facts.py</code> wrote these fields of the record rounded to 0.001 GB/s.</li><li>The computed overlap result must equal the field <code>overlap</code>.</li><li>The number of intervals (<code>n</code>) and the number of processes (<code>np</code>) of both ranges must equal the fields of the record exactly.</li><li><code>check</code> adds one PASS or FAIL line.</li></ul></td></tr>
<tr><td colspan="2"><b>Cross-check with the verdict records of facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 786  g0 = len(CHECKS)
 787  xv("old read, part A", rA_old, rPA_old, vrow("A", "bw_old read", "part A, sessions 1 to 3", "pool A-1 to A-3"), 0)
 788  xv("old read, part L", rL_old, rPL_old, vrow("L", "oldread", "part L", "pool L-1 to L-4"), L_OLD_NEAR)
 789  xv("old read, part C", rC_old, rPL_old, vrow("C", "oldread", "part C, all oldread intervals", "pool L-1 to L-4 (position 0)"), 0)
 790  xv("old read, F72d12", rF_old, rPL_old, vrow("L", "oldread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)
 791  xv("old read, control I", rI_old, rPL_old, vrow("L", "oldread", "control I (same boot, not pooled)", "pool L-1 to L-4"), 0)
 792  xv("asmread, part L", rL_asm, rPL_asm, vrow("L", "asmread", "part L", "pool L-1 to L-4"), DIST["nearest"][0])
 793  xv("asmread, F72d12", rF_asm, rPL_asm, vrow("L", "asmread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)
 794  xv("asmread, control I", rI_asm, rPL_asm, vrow("L", "asmread", "control I (same boot, not pooled)", "pool L-1 to L-4"), rI_asm.nearest(rPL_asm))
 795  xv("asmread after oldread, part C", rC_asm_ao, rPL_asm, vrow("C", "asmread", "part C, asmread after oldread", "pool L-1 to L-4 (after oldread)"), rC_asm_ao.nearest(rPL_asm))
 796  for rnd in (1, 2):
 797      xv(f"bw_new read, session 1, round {rnd}", A_V3[rnd]["r7"], A_V3[rnd]["r8"],
 798         vrow("A", "bw_new read", f"session 1, round {rnd}", f"A-1 and A-2, round {rnd}"), A_V3[rnd]["near"])</pre></td><td valign="top">Eleven <code>xv</code> calls. The list <code>q2_rows</code> of this facts.json has 42 entries, and these lines compare 11 of them [Ref2].<ul><li>Old read kernel: part A against the pool A-1 to A-3. Part L, part C, F72d12 and control I against the pool L-1 to L-4.</li><li><code>asmread</code>: part L, F72d12, control I, and part C directly after <code>oldread</code>, each against the pool L-1 to L-4.</li><li><code>bw_new read</code>: session 1 against rows A-1 and A-2 of the same round, for round 1 and for round 2.</li></ul>The last argument is the computed distance of the nearest ends. It is written as 0 in the five calls whose ranges overlap.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 799  for key_, grp in (("C_ao", "read after oldread"), ("C_aa", "read after asmread")):
 800      vr = [r for r in V["q1_parts"] if r["part"] == "C" and r["group"] == grp]
 801      need(len(vr) == 1, f"facts.json verdicts: no single Q1 row {grp}")
 802      check(near(min(Q1[key_]["drops"]), vr[0]["smallest_drop_pct"], "0.01") and near(max(Q1[key_]["drops"]), vr[0]["largest_drop_pct"], "0.01"),
 803            f"Q1 part C, {grp}: drops equal to the verdict record of facts.json to 0.01 %")
 804  grouped("verdict records of facts.json (11 comparisons of Q2 with ranges, n, overlap and distance to 0.001 GB/s; 2 drop ranges of Q1 to 0.01 %)", g0)</pre></td><td valign="top">Question Q1, part C.<ul><li>For each of the two groups of the bwx12 kernel <code>read</code>, the script takes the one entry of <code>verdicts.q1_parts</code> with the part <code>C</code> and that group. It stops unless exactly one such entry exists.</li><li>The lowest and the highest computed drop must differ from the fields <code>smallest_drop_pct</code> and <code>largest_drop_pct</code> by at most 0.01 (percent). The drops are not rounded before this comparison. The record holds both fields rounded to 0.01 percent.</li><li><code>grouped</code> joins the 13 comparisons of lines 787 to 803 into one line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 805  sb = V["same_boot"]
 806  check(near(VISIT_HI - VISIT_LO, sb["spread_GBps"], "0.001")
 807        and all(near(DIST[k][0], sb["part_L_above_pool_8000_GBps"][j], "0.001") and near(DIST[k][1], sb["part_L_above_F72d12_GBps"][j], "0.001")
 808                for k, j in (("nearest", "nearest_ends"), ("medians", "medians"), ("farthest", "farthest_ends"))),
 809        "three visits of the 7200 MT/s boot: span and the 6 distances equal to the same_boot record of facts.json")
 810</pre></td><td valign="top">The record <code>verdicts.same_boot</code> of facts.json holds values for the three visits of the 7200 MT/s boot. The check passes when seven computed values differ from it by at most 0.001 GB/s each.<ul><li>The first is the <code>asmread</code> span <code>VISIT_HI - VISIT_LO</code>.</li><li>The other six are the distances of <code>DIST</code>: nearest ends, medians and farthest ends, each above the 8000 MT/s pool and above F72d12.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>addref</code>: one entry of the reference list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 811  # ------------------------------------------------------------------ raw-file checks for the machine state section
 812  REFS = []            # (key, path, text shown, note)
 813
 814
 815  def addref(key, path, note, lines=None):
 816      need(os.path.exists(path), f"reference {key}: path does not exist: {path}")
 817      shown = path.replace(R + "/", "R/").replace(S + "/", "S/")
 818      REFS.append((key, shown + (f" ({lines})" if lines else ""), note))
 819
 820</pre></td><td valign="top">The comment in line 811 starts the checks of raw files for the page section on the machine state. The reference helpers are defined first. <code>REFS</code> is the list of the reference entries of the page.<ul><li><code>addref</code> stops the script when the path does not exist.</li><li>It shortens the path to <code>R/...</code> or <code>S/...</code>. It appends the text <code>lines</code> in parentheses when one is given.</li><li>It stores three values: the key, this path text and the note.</li><li>The calls of <code>addref</code> stand in lines 1389 to 1474.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>ref</code>: a reference mark in the page text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 821  def ref(*keys):
 822      """Reference marks. The numbers are given at the end, in the order of first use on the page (number_refs)."""
 823      for k in keys:
 824          need(sum(1 for r in REFS if r[0] == k) == 1, f"unknown reference key {k}")
 825      return '&lt;span class="ref"&gt;' + "".join(f"\x00{k}\x00" for k in keys) + "&lt;/span&gt;"
 826
 827</pre></td><td valign="top"><code>ref</code> returns the HTML text that the page carries at a place that cites references. The script stops unless each key has exactly one entry in <code>REFS</code>. The text holds each key between two characters with the code 0 (written <code>\x00</code>). The reference numbers are not known yet.</td></tr>
<tr><td colspan="2"><b>Function <code>number_refs</code>: number the references by first use</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 828  def number_refs(page):
 829      order = []
 830      for k in re.findall("\x00(.+?)\x00", page):
 831          if k not in order:
 832              order.append(k)
 833      uncited = [r[0] for r in REFS if r[0] not in order]
 834      num = {k: i + 1 for i, k in enumerate(order + uncited)}
 835      by_key = {r[0]: r for r in REFS}
 836      items = "".join(f'&lt;li id="ref{num[k]}"&gt;[Ref{num[k]}] &lt;code&gt;{esc(by_key[k][1])}&lt;/code&gt;: {esc(by_key[k][2])}&lt;/li&gt;' for k in order + uncited)
 837      page = re.sub("\x00(.+?)\x00", lambda m: f'&lt;a href="#ref{num[m.group(1)]}"&gt;[Ref{num[m.group(1)]}]&lt;/a&gt;', page)
 838      return page.replace("\x01REFLIST\x01", items), uncited
 839
 840</pre></td><td valign="top"><code>number_refs</code> runs once, on the text of the whole page (line 2784).<ul><li><code>order</code> lists the keys in the order of their first mark in the page.</li><li><code>uncited</code> lists the keys of <code>REFS</code> that no mark names. They get the numbers after the cited ones.</li><li>Every mark is replaced by a link with the text <code>[RefN]</code>.</li><li>One list item per reference is built. The items replace the text <code>\x01REFLIST\x01</code> in the page.</li><li>The function returns the page and <code>uncited</code>. Line 2792 adds a FAIL line when <code>uncited</code> is not empty.</li></ul></td></tr>
<tr><td colspan="2"><b>Raw-file checks for the machine state section: the two run logs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 841  GOLOG = R + "/go-T72-20261117T221209Z.log"
 842  GO2LOG = R + "/go2-T72-20261117T222335Z.log"
 843  STATE_RE = re.compile(r"^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) \d+ users (\d+) marker (\S+) processes per user: (.*)$")
 844  SYSTEM_ACCOUNTS = {"messagebus", "polkitd", "syslog", "systemd-network", "systemd-resolve", "systemd-timesync"}
 845
 846</pre></td><td valign="top"><code>GOLOG</code> and <code>GO2LOG</code> are the saved run logs of go.sh and go2.sh. <code>STATE_RE</code> is the regular expression for a state line. It captures 12 fields, and <code>state_lines</code> uses 8 of them. <code>SYSTEM_ACCOUNTS</code> names the 6 accounts that the script calls system accounts.</td></tr>
<tr><td colspan="2"><b>Function <code>state_lines</code>: parse the state lines of a run log</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 847  def state_lines(path):
 848      out = []
 849      for no, line in enumerate(lines_of(path), 1):
 850          m = STATE_RE.match(line)
 851          if m:
 852              users = {}
 853              for part in m.group(12).split(";"):
 854                  part = part.split()
 855                  if len(part) == 2:
 856                      users[part[1]] = int(part[0])
 857              out.append(dict(line=no, name=m.group(1), utc=m.group(2), boot=m.group(3), mem=int(m.group(4)),
 858                              load1=Decimal(m.group(5)), logins=int(m.group(10)), marker=m.group(11), users=users))
 859      return out
 860
 861</pre></td><td valign="top"><code>state_lines</code> returns one dictionary per line that matches <code>STATE_RE</code>.<ul><li>Its first entries are the line number, the name of the line (for example <code>start</code> or <code>after T72A1</code>), the time, the boot id and MemTotal in kB.</li><li>The other entries are the 1-minute load average, the number of logins (the number after the word <code>users</code>), the state of the marker file, and <code>users</code>.</li><li><code>users</code> maps an account name to its number of processes. It is read from the list after <code>processes per user:</code>. An entry of that list has the form <code>11 jhan</code> and ends with <code>;</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Hard assertions on the two run logs</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 862  ST_GO, ST_GO2 = state_lines(GOLOG), state_lines(GO2LOG)
 863  need(len(ST_GO) == 12 and len(ST_GO2) == 6, "run logs: expected 12 and 6 state lines")
 864  ST_ALL = ST_GO + ST_GO2
 865  need(all(s["boot"] == RERUN["boot_id"] for s in ST_ALL), "run logs: a state line holds another boot id")
 866  need(all(s["mem"] == RERUN["memtotal_kB"] for s in ST_ALL), "run logs: a state line holds another MemTotal")
 867  need(all(s["logins"] == 0 and s["marker"] == "absent" for s in ST_ALL), "run logs: a login or the marker file")
 868  ACCOUNTS = set().union(*[set(s["users"]) for s in ST_ALL])
 869  need(ACCOUNTS == {"jhan", "root"} | SYSTEM_ACCOUNTS, f"run logs: unexpected account owns a process: {sorted(ACCOUNTS)}")
 870  need(all(s["users"][a] == 1 for s in ST_ALL for a in SYSTEM_ACCOUNTS), "run logs: a system account owns more than 1 process")
 871  JHAN_PROCS = sorted({s["users"]["jhan"] for s in ST_ALL})
 872  need(len(JHAN_PROCS) == 1, "run logs: the process count of jhan changes")</pre></td><td valign="top">Each <code>need</code> call stops the script when its fact does not hold. Every test from here to line 1139 is such a call. The one exception is the <code>check</code> call of line 1035.<ul><li>The log of go.sh holds 12 state lines, and the log of go2.sh holds 6.</li><li>All 18 lines hold the boot id and the MemTotal value of <code>meta.rerun</code> in facts.json.</li><li>All 18 lines show 0 logins and the marker state <code>absent</code>.</li><li>Only <code>jhan</code>, <code>root</code> and the 6 system accounts own processes. Each system account owns exactly 1 process in every line.</li><li>The process count of <code>jhan</code> is the same in all 18 lines. The process count of <code>root</code> is not tested. It is 985 to 1014 in these lines.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 873  gl, g2l = lines_of(GOLOG), lines_of(GO2LOG)
 874  GO_DONE = sum(1 for l in gl if l.startswith("done "))
 875  need(GO_DONE == 10 and gl[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in gl), "go.sh log: not 10 steps, or not ALLDONE")
 876  need(sum(1 for l in g2l if l.startswith("done ")) == 2 and g2l[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in g2l), "go2.sh log")
 877  need(ST_GO[0]["utc"] == RERUN["go_start"] and ST_GO[-1]["utc"] == RERUN["go_end"], "go.sh log: start or end time differs from facts.json")
 878  need(ST_GO2[0]["utc"] == RERUN["go2_start"] and ST_GO2[-1]["utc"] == RERUN["go2_end"], "go2.sh log: start or end time differs from facts.json")</pre></td><td valign="top"><ul><li>The go.sh log must hold 10 lines that start with <code>done </code> (one per step of the rerun). Its last line must be <code>ALLDONE</code>. No line may start with <code>FAILED</code>.</li><li>The go2.sh log must hold 2 lines that start with <code>done </code>. The other two conditions are the same.</li><li>The times of the first and the last state line of each log must equal the start time and the end time that <code>meta.rerun</code> holds for go.sh and for go2.sh.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 879  LAUNCH = {l["tag"]: l for l in META["launches"]}
 880  STEPS = ["T72A1", "T72L1", "T72C1", "T72A2", "T72L2", "T72C2", "T72A3", "T72L3", "T72C3", "T72C4", "T72I1", "T72I2"]
 881  need([l["tag"] for l in META["launches"]] == STEPS, "meta.launches: unexpected list of steps")
 882  BWX_FOLDERS = sorted({r["folder"] for r in L_OLD + C_OLD + I_OLD})
 883  need(len(BWX_FOLDERS) == 9, "expected 9 bwx12 folders of the rerun and the control")
 884  for fo in BWX_FOLDERS:
 885      ll = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")
 886      need(sum(1 for l in ll if l.startswith("rc ")) == 1 and sum(1 for l in ll if l.startswith("rc 0 ")) == 1, f"{fo}: no single 'rc 0' line")
 887  check(True, f"run logs: {len(ST_ALL)} state lines hold boot id {RERUN['boot_id']} and MemTotal {RERUN['memtotal_kB']} kB, 0 logins; "
 888              f"accounts with processes: jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts; go.sh log: {GO_DONE} 'done' lines and ALLDONE; 9 bwx12 folders with one 'rc 0' line")
 889</pre></td><td valign="top"><ul><li><code>LAUNCH</code> maps a folder tag to its entry of <code>meta.launches</code>. That list must name the 12 steps of <code>STEPS</code> in this order.</li><li><code>BWX_FOLDERS</code> holds the result folders of the <code>oldread</code> records of part L, part C and control I. There must be 9 folders.</li><li>In each of these folders, launches.txt must hold exactly one line that starts with <code>rc </code>, and this line must start with <code>rc 0 </code>. So each folder holds one process, and its exit status is 0.</li><li><code>check(True, ...)</code> adds a summary line that is always PASS. The script reaches this line only when every <code>need</code> call above it held. Each later block of raw-file checks up to line 1139 ends with such a line too.</li></ul></td></tr>
<tr><td colspan="2"><b>Boot record <code>try6.txt</code> of the 7200 MT/s boot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 890  # the boot record of 12 modules at 7200 MT/s
 891  TRY6 = R + "/dimm7200-20261117/try6.txt"
 892  t6 = lines_of(TRY6)
 893  need(t6[1].strip() == RERUN["boot_id"], "try6.txt: line 2 is not the boot id of the rerun")
 894  need(re.match(r"^MemTotal:\s+%d kB$" % RERUN["memtotal_kB"], t6[3]), "try6.txt: line 4 holds another MemTotal")
 895  m_ = re.match(r"^\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s$", t6[6])
 896  need(m_ and int(m_.group(1)) == 12 and int(m_.group(2)) == RERUN["speed_MTps"] == 7200, "try6.txt: line 7 is not 12 x 7200 MT/s")
 897  need(t6[4].strip().endswith("ghes_edac: This system has 12 DIMM sockets."), "try6.txt: line 5 is not the kernel line with 12 modules")
 898  m_ = re.match(r"^modules=(\d+)$", t6[5].strip())
 899  need(m_, "try6.txt: line 6 is not a line 'modules=N'")</pre></td><td valign="top"><code>TRY6</code> is the path of try6.txt, and <code>t6</code> holds its lines. The script stops unless the record holds these facts:<ul><li>line 2 is the boot id of the rerun,</li><li>line 4 is the MemTotal value of the rerun,</li><li>line 7 holds the count 12 before the text <code>Configured Memory Speed: 7200 MT/s</code>, and <code>meta.rerun</code> gives 7200 MT/s too,</li><li>line 5 ends with the Linux kernel message <code>ghes_edac: This system has 12 DIMM sockets.</code>,</li><li>line 6 has the form <code>modules=N</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 900  TRY6_MODLINE = int(m_.group(1))                            # not the module count: see the module list below
 901  TRY6_UTC = t6[0].strip()
 902  need(re.match(r"^2026-11-17T\d\d:\d\d:\d\dZ$", TRY6_UTC), "try6.txt: line 1 is not a time")</pre></td><td valign="top"><ul><li><code>TRY6_MODLINE</code> is the N of line 6. It is 24 in this file, and it is not the module count. Line 1170 compares it with the module list.</li><li><code>TRY6_UTC</code> is line 1. The script stops unless it is a time of 2026-11-17.</li><li>The script does not read lines 3 and 8 of the file. Line 3 is the output of the tool <code>uptime</code>. Line 8 holds the text <code>hwerr=0</code>.</li><li>The command that wrote try6.txt is known from a record of the AI agent (Claude Code) that ran it. By this command, <code>hwerr</code> is the number of lines with the text <code>Hardware error from APEI</code> in the Linux kernel log (tool <code>dmesg</code>). The record is the file <code>4a6b911c-1987-43f1-be61-e96fcfc7261d.jsonl</code>. It lies outside the project folder.</li><li>The file was written at 20:02:21 (line 1), before the rerun started at 22:12:09.</li></ul></td></tr>
<tr><td colspan="2"><b>Why F72d12 belongs to the 7200 MT/s boot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 903  # why F72d12 belongs to this boot
 904  BOOTS = R + "/dimm7200-20261117/boots.txt"
 905  bl = [l.split() for l in lines_of(BOOTS) if l.strip()]
 906  need(bl[-1][0] == "0" and bl[-1][1] == RERUN["boot_id"].replace("-", ""), "boots.txt: row 0 is not the boot of the rerun")
 907  BOOT_FIRST, BOOT_LAST = bl[-1][4], bl[-1][8]
 908  need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(BOOTS))) == BOOT_LAST, "boots.txt: its file time is not the end time of row 0")</pre></td><td valign="top"><code>boots.txt</code> is the saved boot list of the journal. A row holds a boot number, a boot id without hyphens, and the first and the last time of the boot.<ul><li>The last row must have the number 0 and the boot id of the rerun.</li><li><code>BOOT_FIRST</code> and <code>BOOT_LAST</code> are the two times of day of this row (its 5th and its 9th field).</li><li>The file time of boots.txt (the time of its last change), written as a UTC time of day, must equal <code>BOOT_LAST</code>. So <code>BOOT_LAST</code> is the time at which the list was saved. The boot continued after it: the state lines of the rerun hold the same boot id.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 909  FL = R + "/w120-w120-F72d12-20261117T200231Z/launches.txt"
 910  fl = lines_of(FL)
 911  m1, m2 = re.match(r"^launch a6456 utc (\S+) load (\S+) ", fl[0]), re.match(r"^rc 0 a6456 utc (\S+)$", fl[1])
 912  need(m1 and m2, "F72d12 launches.txt: launch or rc line not found")
 913  F_LAUNCH, F_END = m1.group(1), m2.group(1)
 914  need(F_OLD[0]["launch_utc"] == f"2026-11-17T{F_LAUNCH}Z" and D(m1.group(2)) == D(F_OLD[0]["load1_at_launch"]), "F72d12: launch differs from facts.json")
 915  need(TRY6_UTC[11:19] &lt; F_LAUNCH and BOOT_FIRST &lt;= F_LAUNCH &lt; F_END &lt;= BOOT_LAST and BOOT_LAST &lt; ST_GO[0]["utc"][11:19],
 916       "F72d12: the process does not lie inside the recorded time of boot 3bfc57a1")
 917  check(True, f"try6.txt ({TRY6_UTC}): boot id of the rerun, MemTotal {RERUN['memtotal_kB']} kB, 12 x 7200 MT/s; boots.txt row 0 = this boot, "
 918              f"{BOOT_FIRST} to {BOOT_LAST}; F72d12 ran {F_LAUNCH} to {F_END} inside it")
 919</pre></td><td valign="top"><ul><li>Lines 1 and 2 of the launches.txt of F72d12 must be the <code>launch</code> line and the <code>rc 0</code> line of the process <code>a6456</code>. They give the launch time <code>F_LAUNCH</code> and the end time <code>F_END</code>.</li><li>The launch time and the 1-minute load average of that line must equal the fields <code>launch_utc</code> and <code>load1_at_launch</code> of the first F72d12 record.</li><li>The time in line 1 of try6.txt must be before the launch. The launch and the end must lie from <code>BOOT_FIRST</code> to <code>BOOT_LAST</code>. <code>BOOT_LAST</code> must be before the first state line of go.sh.</li><li>These times are compared as texts <code>HH:MM:SS</code>. The dates in the rows of boots.txt are not compared.</li></ul>The saved output of a build shows the process from 20:02:36 to 20:03:37, inside 20:02:21 to 20:06:19 [Ref5].</td></tr>
<tr><td colspan="2"><b>Hardware error records in the journal of the 8000 MT/s boot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 920  # corrected hardware error records in the journal of the 8000 MT/s boot (defect partL-r3-partL-1, checked here)
 921  JOURNAL = R + "/dimm-check-20261117/h-5.txt"
 922  HW = []
 923  for no, line in enumerate(lines_of(JOURNAL), 1):
 924      m_ = re.match(r"^(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$", line)
 925      if not m_:
 926          continue
 927      if m_.group(3).startswith("Hardware error from APEI"):
 928          HW.append(dict(line=no, ts=m_.group(1), sev=None))
 929      elif m_.group(3).startswith("event severity:") and HW:
 930          HW[-1]["sev"] = m_.group(3).split(":", 1)[1].strip()
 931  need(len(HW) &gt; 0 and {h["sev"] for h in HW} == {"corrected"}, "journal: no records, or a severity other than 'corrected'")</pre></td><td valign="top"><code>h-5.txt</code> holds saved journal lines of the 8000 MT/s boot. The loop keeps the lines of the Linux kernel that carry the tag <code>[Hardware Error]</code>.<ul><li>A message that starts with <code>Hardware error from APEI</code> opens a new record in <code>HW</code>: line number, time stamp, severity not yet set.</li><li>A message that starts with <code>event severity:</code> sets the severity of the newest record.</li><li>The other lines of a record are skipped.</li><li>The script stops unless <code>HW</code> holds at least one record and every severity is <code>corrected</code>.</li><li>The script reads no hardware error record of the 7200 MT/s boot. For the rerun the page says <code>Insufficient data</code> (line 2474).</li><li>Lines 957 to 1032 count the records inside the time windows of the rows L-1 to L-4 and A-1 to A-3 only. No line counts them for the rows of the older runner bwx (the records of <code>OTHER</code>, line 333). The page says so (line 2562).</li></ul>The comment names a review finding by its identifier. The file <code>review-w2.json</code> in <code>S</code> holds this finding.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 932  # the saved kernel log of the same boot: its first and last line, the module count line, the same number of records
 933  KLOG = R + "/dimm-check-20261117/k-5.txt"
 934  kl = lines_of(KLOG)
 935  mk0, mk1 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[0]), re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[-1])
 936  need(mk0 and mk1, "kernel log of the 8000 MT/s boot: first or last line has no time")
 937  BOOT8_FROM, BOOT8_TO = f"2026-11-{mk0.group(1)}T{mk0.group(2)}Z", f"2026-11-{mk1.group(1)}T{mk1.group(2)}Z"
 938  need(sum(1 for l in kl if "ghes_edac: This system has 12 DIMM sockets" in l) == 1, "kernel log of the 8000 MT/s boot: module count line")
 939  need(sum(1 for l in kl if "Hardware error from APEI" in l) == len(HW), "kernel log and journal of the 8000 MT/s boot: record counts differ")
 940  need(lines_of(JOURNAL)[0].startswith(BOOT8_FROM[:19]), "journal and kernel log of the 8000 MT/s boot: first line times differ")
 941  need(all(BOOT8_FROM &lt; r["launch_utc"] &lt; BOOT8_TO for r in EIGHT + OTHER), "an 8000 MT/s row was not launched inside the saved kernel log of its boot")
 942
 943</pre></td><td valign="top"><code>k-5.txt</code> is the saved kernel log of the 8000 MT/s boot.<ul><li><code>BOOT8_FROM</code> and <code>BOOT8_TO</code> are the times of its first and its last line. Both lines must start with <code>Nov</code>, the day and the time. The year 2026 and the month 11 are fixed text of the script.</li><li>The log must hold exactly one line with <code>ghes_edac: This system has 12 DIMM sockets</code>.</li><li>It must hold as many lines with <code>Hardware error from APEI</code> as <code>HW</code> has records.</li><li>The first journal line must start with the time <code>BOOT8_FROM</code>.</li><li>Every record of <code>EIGHT</code> and of <code>OTHER</code> (the used 8000 MT/s records, lines 310 and 333) must have a launch time after <code>BOOT8_FROM</code> and before <code>BOOT8_TO</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Functions <code>launch_window</code> and <code>hw_in</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 944  def launch_window(folder, tag):
 945      ll = lines_of(R + "/" + folder + "/launches.txt")
 946      a = [re.match(rf"^launch {tag} utc (\S+) ", l) for l in ll]
 947      b = [re.match(rf"^rc 0 {tag} utc (\S+)$", l) for l in ll]
 948      a, b = [x for x in a if x], [x for x in b if x]
 949      need(len(a) == 1 and len(b) == 1, f"{folder}: launch window of {tag} not found")
 950      return a[0].group(1), b[0].group(1)
 951
 952
 953  def hw_in(day, t0, t1):
 954      return [h for h in HW if h["ts"][:10] == day and t0 &lt;= h["ts"][11:19] &lt;= t1]
 955
 956</pre></td><td valign="top"><ul><li><code>launch_window</code> reads launches.txt of a result folder. It returns the launch time and the end time of the process with the given tag. The end time is the time of its line <code>rc 0</code>. The script stops unless the file holds exactly one <code>launch</code> line and one <code>rc 0</code> line for the tag.</li><li><code>hw_in</code> returns the records of <code>HW</code> of one day whose time of day lies from <code>t0</code> to <code>t1</code>. Both ends count as inside.</li></ul></td></tr>
<tr><td colspan="2"><b>Hardware error records during the rows L-1 to L-4</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 957  HW_ROWS = {}
 958  for d in LPOOL:
 959      for pk in sorted({r["proc_key"] for r in B_L_ASM[d]}):
 960          r0 = [r for r in B_L_ASM[d] if r["proc_key"] == pk][0]
 961          folder, tag = r0["folder"].replace("R/", "", 1), r0["tag"]
 962          t0, t1 = launch_window(folder, tag)
 963          need(r0["launch_utc"][11:19] == t0, f"{d} {tag}: launch time differs from facts.json")
 964          HW_ROWS[(d, tag)] = dict(t0=t0, t1=t1, day=r0["launch_utc"][:10], recs=hw_in(r0["launch_utc"][:10], t0, t1))
 965  HW_L1 = len(HW_ROWS[("L-1", "a6456")]["recs"])
 966  HW_L2 = [len(HW_ROWS[("L-2", t)]["recs"]) for t in ("p1nop", "p2add")]
 967  HW_L34 = sum(len(v["recs"]) for (d, _), v in HW_ROWS.items() if d in ("L-3", "L-4"))
 968  need(HW_L1 &gt; 0 and min(HW_L2) &gt; 0 and HW_L34 == 0, "journal: the record counts of rows L-1 to L-4 are not as the defect states")</pre></td><td valign="top">The loop handles each process of the rows L-1 to L-4. It takes the processes from the <code>asmread</code> records (<code>B_L_ASM</code>, line 292).<ul><li><code>launch_window</code> gives the launch time and the end time of the process. The launch time must equal the field <code>launch_utc</code> of the record.</li><li><code>HW_ROWS</code> stores, per row and tag, the two times, the day and the hardware error records inside this time window.</li><li><code>HW_L1</code> is the count for L-1. <code>HW_L2</code> holds the counts of the two processes of L-2. <code>HW_L34</code> is the total of L-3 and L-4.</li><li>The script stops unless L-1 has at least 1 record, each L-2 process has at least 1, and L-3 and L-4 have 0.</li></ul>The saved output of a build shows 2 records for L-1, 5 and 4 for L-2, and 0 for L-3 and L-4 [Ref5].</td></tr>
<tr><td colspan="2"><b>Functions <code>a_headers</code> and <code>secs</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 969  # the part A rows of the same boot (A-1, A-2, A-3): records between the launches that the csv files hold
 970
 971
 972  def a_headers(rec):
 973      """(line number, launch time, text) of every process header line of the csv file of a part A record."""
 974      out = []
 975      for no, l in enumerate(file_lines(rec), 1):
 976          if l.startswith("-- "):
 977              m_ = re.search(r" utc (\d\d:\d\d:\d\d)\b", l)
 978              need(m_, f"{rec['folder']}/{rec['file']} line {no}: header without a launch time")
 979              out.append((no, m_.group(1), l))
 980      return out
 981
 982
 983  def secs(hms):
 984      h, m, s_ = (int(x) for x in hms.split(":"))
 985      return h * 3600 + m * 60 + s_
 986
 987</pre></td><td valign="top">Helpers for the rows A-1 to A-3, which ran in the 8000 MT/s boot too.<ul><li><code>a_headers</code> returns the line number, the launch time and the text of every process header line of the csv file that a part A record names. The launch time is the text <code>HH:MM:SS</code> after the word <code>utc</code>. The script stops when a header line has none.</li><li><code>secs</code> converts a time <code>HH:MM:SS</code> to seconds since midnight.</li></ul></td></tr>
<tr><td colspan="2"><b>Hardware error records during the rows A-1 to A-3</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 988  A_DAY = "2026-11-13"
 989  need({r["launch_utc"][:10] for d in APOOL for r in B_A_OLD[d]} == {A_DAY}, "rows A-1 to A-3 are not all of 2026-11-13")
 990  HA1, HA2, HA3 = a_headers(B_A_OLD["A-1"][0]), a_headers(B_A_OLD["A-2"][0]), a_headers(B_A_OLD["A-3"][0])
 991  A1_FIRST, A1_LAST, A2_FIRST, A2_LAST = HA1[0][1], HA1[-1][1], HA2[0][1], HA2[-1][1]
 992  a3_used = sorted({r["_fproc"] for r in B_A_OLD["A-3"]})          # numbers of the processes used, inside the file
 993  need(len(a3_used) == 3 and a3_used[-1] &lt; len(HA3), "A-3: the 3 processes used, and a later process in the file")
 994  A3_FIRST, A3_END = HA3[a3_used[0] - 1][1], HA3[a3_used[-1]][1]      # launch of the first one, launch of the process after the last one
 995  need(A1_FIRST &lt;= A1_LAST &lt; A2_FIRST &lt;= A2_LAST &lt; A3_FIRST &lt; A3_END, "rows A-1, A-2, A-3: order of the launch times")
 996  HW_A = hw_in(A_DAY, A1_FIRST, A3_END)
 997  HW_A2 = hw_in(A_DAY, A2_FIRST, A2_LAST)
 998  need(len(HW_A) == len(HW_A2) == 4 and not hw_in(A_DAY, A1_FIRST, A1_LAST) and not hw_in(A_DAY, A3_FIRST, A3_END),
 999       "journal: the records of 2026-11-13 are not 4 records inside row A-2 and 0 inside A-1 and A-3")</pre></td><td valign="top">All <code>bw_old read</code> records of these rows must be of 2026-11-13. <code>HA1</code>, <code>HA2</code> and <code>HA3</code> are the header lists of the three csv files.<ul><li>The time window of A-1 and of A-2 runs from the first launch to the last launch in the file.</li><li>The csv file of A-3 holds more processes than the 3 that the page uses. Its window runs from the launch of the first process used to the launch of the process after the last one used. <code>_fproc</code> (line 349) gives the place of a process in the file. The script stops unless the records name exactly 3 processes and the file holds a later process.</li><li>The six times must be in order, so the three windows do not overlap.</li><li>The script stops unless the journal holds 4 records from the first launch of A-1 to the end of the A-3 window. All 4 must lie inside the window of A-2, and none inside the windows of A-1 and A-3.</li><li>Records before the first launch of A-1 and after the end of the A-3 window are not counted in these lines. The file <code>h-5.txt</code> holds 42 such records of 2026-11-13: 4 before (the last at 18:16:53, 28 s before that launch) and 38 after (the first at 20:59:34).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1000  # the last process of A-1 and of A-2 has no later header in its file: no record follows within 60 s of its launch
1001  for last in (A1_LAST, A2_LAST):
1002      need(not [h for h in HW if h["ts"][:10] == A_DAY and 0 &lt; secs(h["ts"][11:19]) - secs(last) &lt;= 60], "journal: a record within 60 s after the last launch of A-1 or A-2")
1003  HW_A2_T = sorted({h["ts"][11:19] for h in HW_A2})
1004  need(len(HW_A2_T) == 2 and all(sum(1 for h in HW_A2 if h["ts"][11:19] == t) == 2 for t in HW_A2_T), "journal: row A-2 does not hold 2 + 2 records at two times")</pre></td><td valign="top">The last process of A-1 and of A-2 has no later header line in its file. So no launch of a next process marks its end.<ul><li>In place of an end time the script requires that no record has a time from 1 s to 60 s after that launch.</li><li><code>HW_A2_T</code> holds the different times of day of the 4 records in A-2. The script stops unless these are 2 times with 2 records each.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1005  a2_new_r1 = [r for r in B_A_NEW["A-2"] if r["round"] == 1]
1006  need(len(a2_new_r1) == 3 and a2_new_r1[0]["launch_utc"][11:19] == HW_A2_T[0] == HA2[a2_new_r1[0]["_fproc"] - 1][1],
1007       "journal: the first two records of row A-2 are not in the launch second of bw_new read, round 1")
1008  a2_other = [h for i, h in enumerate(HA2) if h[1] &lt;= HW_A2_T[1] and (i + 1 == len(HA2) or HW_A2_T[1] &lt; HA2[i + 1][1])]
1009  need(len(a2_other) == 1, "journal: no single process of row A-2 for the second pair of records")
1010  m_ = re.search(r" binary (\S+) .* --kernel (\S+) ", a2_other[0][2])
1011  need(m_ and m_.group(2) not in ("read", "all"), "journal: the second pair of records of row A-2 falls into a read process")
1012  A2_OTHER = f"{m_.group(1)} {m_.group(2)}"
1013  check(True, f"journal of the 8000 MT/s boot, {A_DAY}: {len(HW_A)} corrected records from the first launch of A-1 ({A1_FIRST}) to the launch after the last A-3 process used ({A3_END}); "
1014              f"all in A-2: 2 at {HW_A2_T[0]} (launch second of bw_new read, round 1), 2 at {HW_A2_T[1]} (process {A2_OTHER}, launched {a2_other[0][1]})")
1015</pre></td><td valign="top">Which processes of A-2 the 4 records lie in.<ul><li>The first time must be the launch second of the <code>bw_new read</code> process of round 1. The record field <code>launch_utc</code> and the header line of that process must both give this second.</li><li><code>a2_other</code> is the last process of the file that was launched at or before the second time. Exactly one must exist.</li><li>Its header line gives the binary and the kernel. The script stops when the kernel is <code>read</code> or <code>all</code>. Its stop message calls such a process a read process.</li><li><code>check(True, ...)</code> adds the summary line.</li></ul>The saved output of a build shows 2 records at 20:50:58 and 2 at 20:51:10. The second pair lies in a <code>bw_new write</code> process that was launched at 20:51:08 [Ref5].</td></tr>
<tr><td colspan="2"><b>The interval with the lowest asmread rate of the pool</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1016  # the interval with the lowest asmread value of the pool: its time inside the process, from the T rows of the csv
1017  need(LOWEST_ASM["dataset"] == "L-2" and LOWEST_ASM["tag"] == "p2add", "the lowest asmread interval of the pool is not in L-2 p2add")
1018  T_START = Decimal(repr(min(t[3] for t in t_rows(LOWEST_ASM))))      # seconds since the process start
1019  T_END = Decimal(repr(max(t[4] for t in t_rows(LOWEST_ASM))))
1020
1021</pre></td><td valign="top"><code>LOWEST_ASM</code> (line 520) is the record with the lowest <code>asmread</code> rate of the pool.<ul><li>The script stops unless it belongs to row L-2, process <code>p2add</code>.</li><li><code>t_rows</code> (line 124) returns the 120 T rows of this interval.</li><li><code>T_START</code> is the lowest value of their 10th field <code>t_start_s</code>. <code>T_END</code> is the highest value of their 11th field <code>t_end_s</code>. Both are seconds since the start of the process.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>clock</code>: add seconds to a time of day</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1022  def clock(hms, add):
1023      """Launch time plus seconds since the process start, to the nearest second."""
1024      h, m, s = (int(x) for x in hms.split(":"))
1025      tot = h * 3600 + m * 60 + s + int(add.to_integral_value(rounding=ROUND_HALF_UP))
1026      return f"{tot // 3600:02d}:{tot // 60 % 60:02d}:{tot % 60:02d}"
1027
1028</pre></td><td valign="top"><code>clock</code> rounds the seconds <code>add</code> to a whole number. A value exactly between two whole numbers is rounded up. It adds the result to the time <code>hms</code> and returns the new time as <code>HH:MM:SS</code>.</td></tr>
<tr><td colspan="2"><b>Hardware error records inside the lowest asmread interval</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1029  LOW_T0 = HW_ROWS[("L-2", "p2add")]["t0"]
1030  LOW_FROM, LOW_TO = clock(LOW_T0, T_START), clock(LOW_T0, T_END)
1031  HW_LOW = hw_in(LOWEST_ASM["launch_utc"][:10], LOW_FROM, LOW_TO)
1032  need(len(HW_LOW) == 2 and len({h["ts"] for h in HW_LOW}) == 1, "journal: not 2 records with one time inside the lowest asmread interval")</pre></td><td valign="top"><ul><li><code>LOW_T0</code> is the launch time of the process <code>p2add</code>, as launches.txt gives it (line 962).</li><li><code>LOW_FROM</code> and <code>LOW_TO</code> are the times of day at which the interval started and ended, to the nearest second (est.). The runner script rx.sh wrote the launch time in whole seconds, directly before it started the process. So both times can differ from the true times by about 1 s.</li><li><code>HW_LOW</code> holds the hardware error records of that day from <code>LOW_FROM</code> to <code>LOW_TO</code>. The script stops unless these are exactly 2 records with one time stamp.</li><li>This is the only interval for which the script computes a start time and an end time. It does not test whether a record lies inside any other interval. The counts of lines 957 to 999 are for the time window of a whole process (rows L-1 to L-4) or of a whole row (A-1 to A-3).</li></ul>The saved output of a build shows 2 records at 18:54:52, inside 18:54:51 to 18:54:55 [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1033  m_ = re.search(rf"Without this (?:one )?interval the pool spans ({NUM}) to ({NUM}) GB/s", FMD)
1034  if m_:
1035      check(near(q(rPL_asm_wo.lo), m_.group(1), "0.01") and near(q(rPL_asm_wo.hi), m_.group(2), "0.01"),
1036            f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s, FACTS.md {m_.group(1)} to {m_.group(2)} GB/s")
1037  else:
1038      check(True, f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s. FACTS.md holds no such sentence, so this value rests on the raw files only")
1039  check(True, f"journal of the 8000 MT/s boot: corrected records during L-1: {HW_L1}, L-2: {HW_L2[0]} and {HW_L2[1]}, L-3 and L-4: {HW_L34}; "
1040              f"{len(HW_LOW)} records at {HW_LOW[0]['ts'][11:19]} inside the interval of {f2(val(LOWEST_ASM))} GB/s ({LOW_FROM} to {LOW_TO}); "
1041              f"pool without it {rPL_asm_wo.txt()} GB/s")
1042</pre></td><td valign="top"><code>rPL_asm_wo</code> (line 521) is the range of the pool without this one interval. It comes from 10 of the 11 <code>asmread</code> intervals.<ul><li><code>rPL_asm_wo</code> is used only in line 522, in these lines and in one sentence of Table 5 (line 2567). Every other <code>asmread</code> comparison with the pool L-1 to L-4 uses <code>rPL_asm</code> or the list <code>P_L_ASM</code>, which hold all 11 intervals. So the lowest interval is not left out of the other results of the page.</li><li>When FACTS.md holds a sentence of the form <code>Without this interval the pool spans X to Y GB/s</code>, the check compares both values to 0.01 GB/s.</li><li>When FACTS.md holds no such sentence, the script adds a PASS line that says so.</li><li>The second <code>check(True, ...)</code> adds the summary line of the journal checks.</li></ul><code>state_table</code> (line 2503) prints these facts in Table 5. The saved output of a build shows 298.61 to 309.17 GB/s on both sides, and 288.54 GB/s for the interval that is left out [Ref5].</td></tr>
<tr><td colspan="2"><b>Function <code>set_records</code>: the changed settings of a <code>set.txt</code> file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1043  # firmware settings (defect state-r3-S3-1, checked here)
1044  FW = R + "/fwtest-20261117"
1045
1046
1047  def set_records(path):
1048      """(name, answer) of every response of a settings file that carries 'modified: true', and the time of line 1."""
1049      text = "\n".join(lines_of(path))
1050      out = [(m.group(1), m.group(2)) for m in re.finditer(r'name: "([^"]+)",\s*answer: "([^"]+)",[^}]*\},\s*modified: true', text, re.S)]
1051      for line in text.splitlines():
1052          if line.startswith('{"responses"'):
1053              for resp in json.loads(line)["responses"]:
1054                  if resp.get("modified") is True:
1055                      out.append((resp["question"]["name"], resp["question"]["answer"]))
1056      m = re.match(r"^\w+ Nov 17 (\d\d:\d\d:\d\d) (AM|PM) UTC 2026$", text.splitlines()[0])
1057      when = None
1058      if m:
1059          h = int(m.group(1)[:2]) % 12 + (12 if m.group(2) == "PM" else 0)
1060          when = f"{h:02d}{m.group(1)[2:]}"
1061      return out, when
1062
1063</pre></td><td valign="top"><code>FW</code> is the result folder <code>fwtest-20261117</code>. <code>set_records</code> reads one file <code>set.txt</code>.<ul><li>It returns the pairs (name, answer) of every reply in the file that is marked as modified. Two forms of reply are read. The first is a text block with the lines <code>name: "..."</code>, <code>answer: "..."</code> and <code>modified: true</code>. The second is a JSON line that starts with <code>{"responses"</code>.</li><li>It also returns the time of line 1 as <code>HH:MM:SS</code> in the 24-hour form. For this, line 1 must be a date line of 17 November 2026 with AM or PM. Example: line 1 of <code>set.txt</code> in the folder <code>x1</code> reads <code>Tue Nov 17 03:43:50 AM UTC 2026</code>. For another line 1 the time is <code>None</code>.</li></ul>The comment names a second review finding of <code>review-w2.json</code>.</td></tr>
<tr><td colspan="2"><b>Firmware settings: the changes that the result files hold</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1064  X1, X1_T = set_records(FW + "/x1/set.txt")
1065  X2, X2_T = set_records(FW + "/x2/set.txt")
1066  RV, RV_T = set_records(FW + "/revert/set.txt")
1067  D72, _ = set_records(R + "/dimm7200-20261117/set.txt")
1068  need(X1 == [("TXREQ Min", "1/4 L2 TQ")] and X2 == [("TXREQ Max", "1/4 L2 TQ")], "fwtest: the two TXREQ changes are not as expected")</pre></td><td valign="top">Four files are read: <code>set.txt</code> of the folders <code>x1</code>, <code>x2</code> and <code>revert</code> of <code>FW</code>, and <code>set.txt</code> of the folder <code>dimm7200-20261117</code>. The script stops unless <code>x1</code> holds one change, <code>TXREQ Min</code> to <code>1/4 L2 TQ</code>, and <code>x2</code> holds one change, <code>TXREQ Max</code> to <code>1/4 L2 TQ</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1069  Q_BASE = json.load(open(R + "/uefisettings-20261117/questions.json"))
1070  Q_REV = json.load(open(FW + "/revert/questions.json"))
1071  orig = {x["name"]: x["answer"] for x in Q_BASE if x["name"] in ("TXREQ Max", "TXREQ Min")}
1072  need(len(orig) == 2 and sorted(RV) == sorted(orig.items()), "fwtest: the revert does not set both TXREQ settings to the original values")
1073  need(X1_T and X2_T and RV_T and X1_T &lt; X2_T &lt; RV_T, "fwtest: times of the three records")
1074  canon = lambda qs: sorted(json.dumps(x, sort_keys=True) for x in qs)
1075  need(len(Q_BASE) == len(Q_REV) and canon(Q_BASE) == canon(Q_REV), "fwtest: the settings list after the revert differs from the list of the 8000 MT/s boot")
1076  need([x["answer"] for x in Q_BASE if x["name"] == "DIMM Frequency"] == ["8000 MT/s"], "settings list of the 8000 MT/s boot: DIMM Frequency is not 8000 MT/s")
1077  QBASE_T = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(R + "/uefisettings-20261117/questions.json")))
1078  need(BOOT8_FROM &lt; QBASE_T &lt; BOOT8_TO, "settings list of the 8000 MT/s boot: its file time is not inside that boot")</pre></td><td valign="top"><ul><li><code>Q_BASE</code> is the settings list that was saved in the 8000 MT/s boot. <code>Q_REV</code> is the list that was saved after the revert (the step that set both values back).</li><li><code>orig</code> holds the values of <code>TXREQ Max</code> and <code>TXREQ Min</code> in <code>Q_BASE</code>. The revert must have changed exactly these two settings, to these values.</li><li>The times of line 1 must be in the order <code>x1</code>, <code>x2</code>, revert.</li><li><code>canon</code> turns a list into sorted JSON texts. The two lists must have the same length and the same entries. The order of the entries is not compared.</li><li><code>Q_BASE</code> must hold exactly one setting <code>DIMM Frequency</code>, and its value must be <code>8000 MT/s</code>.</li><li>The file time of <code>Q_BASE</code> must lie after <code>BOOT8_FROM</code> and before <code>BOOT8_TO</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1079  N_SET = len(Q_BASE)
1080  SAME_ORDER = Q_BASE == Q_REV
1081  UNREAD = {}        # kind of error marker -&gt; number of entries that show it in place of a value
1082  for x in Q_BASE:
1083      m_ = re.match(r"^&lt;(\w+):", str(x["answer"]))
1084      if m_:
1085          UNREAD[m_.group(1)] = UNREAD.get(m_.group(1), 0) + 1
1086  need(set(UNREAD) == {"ValueUnavailable", "VStoreError"}, f"settings list: unexpected kinds of error marker: {sorted(UNREAD)}")
1087  N_UNREAD = sum(UNREAD.values())</pre></td><td valign="top"><ul><li><code>N_SET</code> is the number of entries of the settings list.</li><li><code>SAME_ORDER</code> tells whether the two lists are equal in their order too.</li><li><code>UNREAD</code> counts the entries whose answer is an error marker of the form <code>&lt;Name: ...&gt;</code> and not a value, per marker name. The script stops unless the marker names are exactly <code>ValueUnavailable</code> and <code>VStoreError</code>. For such an entry, line 1075 compares the marker text. It does not compare a value of the setting.</li><li><code>N_UNREAD</code> is the total.</li></ul>The saved output of a build shows 1490 entries, of which 886 have no readable value [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1088  need(D72 == [("DIMM Frequency", "7200 MT/s")], "dimm7200 set.txt: not the single change DIMM Frequency = 7200 MT/s")
1089  SET_FILES = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(R) for f in fs if f == "set.txt")
1090  need(SET_FILES == sorted([FW + "/x1/set.txt", FW + "/x2/set.txt", FW + "/revert/set.txt", R + "/dimm7200-20261117/set.txt"]),
1091       "results folder: the files named set.txt are not the 4 expected ones")
1092  D72_T = time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(R + "/dimm7200-20261117/set.txt")))
1093  need(RV_T &lt; D72_T &lt; TRY6_UTC[11:19], "dimm7200 set.txt: file time is not between the revert and the boot record")
1094  check(True, f"firmware settings: TXREQ Min changed {X1_T}, TXREQ Max changed {X2_T}, both set back {RV_T} to the values of the 8000 MT/s list; "
1095              f"list after the revert equal in {N_SET} entries ({N_UNREAD} without a readable value: {UNREAD['ValueUnavailable']} ValueUnavailable, {UNREAD['VStoreError']} VStoreError); 4 files set.txt under R, last: DIMM Frequency = 7200 MT/s ({D72_T} file time)")
1096</pre></td><td valign="top"><ul><li><code>set.txt</code> of the folder <code>dimm7200-20261117</code> must hold one change: <code>DIMM Frequency</code> to <code>7200 MT/s</code>.</li><li><code>os.walk</code> finds every file with the name <code>set.txt</code> under <code>R</code>. The script stops unless these are exactly the 4 files above.</li><li><code>D72_T</code> is the file time of the <code>set.txt</code> of <code>dimm7200-20261117</code> as a UTC time of day. It must lie after the time of the revert and before the time in line 1 of try6.txt. Only the times of day are compared, not the dates.</li><li><code>check(True, ...)</code> adds the summary line.</li></ul>The saved output of a build shows the two changes at 03:43:50 and 04:05:38, the revert at 04:13:19 and the file time 19:43:03 [Ref5].</td></tr>
<tr><td colspan="2"><b>Function <code>proc_list</code>: the process list of an env.txt file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1097  # start state of the three visits of the part L line in the 7200 MT/s boot (process lists, time since the start of the boot)
1098
1099
1100  def proc_list(path):
1101      """Time of line 1 and the rows (user, %CPU, command) of the process list of an env.txt file."""
1102      ll = lines_of(path)
1103      m_ = re.match(r"^\w+ Nov 17 (\d\d):(\d\d:\d\d) (AM|PM) UTC 2026$", ll[0])
1104      need(m_, f"{path}: line 1 is not a time of 2026-11-17")
1105      when = f"{int(m_.group(1)) % 12 + (12 if m_.group(3) == 'PM' else 0):02d}:{m_.group(2)}"
1106      need(ll[3].split() == ["USER", "%CPU", "COMMAND"], f"{path}: line 4 is not the head of the process list")
1107      rows = []
1108      for no, l in enumerate(ll[4:], 5):
1109          if l.startswith("binary "):
1110              break
1111          u, c, name = l.split(None, 2)
1112          rows.append((no, u, Decimal(c), name.strip()))
1113      need(len(rows) &gt;= 3, f"{path}: process list too short")
1114      return when, rows
1115
1116</pre></td><td valign="top">The runner script rx.sh writes the process list of env.txt with the tool <code>ps</code>: sorted by %CPU, highest value first, and limited to the first 5 processes. <code>ps</code> computes %CPU as the CPU time that a process has used, divided by the time since the process started. So the value is an average over the life of the process.<ul><li>Line 1 of the file must be a date line of 17 November 2026 with AM or PM. <code>when</code> is its time as <code>HH:MM:SS</code> in the 24-hour form.</li><li>Line 4 must be the title line with the words <code>USER</code>, <code>%CPU</code> and <code>COMMAND</code>. rx.sh writes the output of the tool <code>who</code> (one line per login) before the process list. So line 4 is the title line only when <code>who</code> printed no line.</li><li>Each line from line 5 up to the first line that starts with <code>binary </code> becomes one row: line number, user, %CPU as <code>Decimal</code>, command. Each of the 6 files read here holds 5 such rows.</li><li>The script stops when there are fewer than 3 rows.</li><li>The function returns <code>when</code> and the rows.</li></ul></td></tr>
<tr><td colspan="2"><b>Start state of the three visits of the part L line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1117  F_ENV = R + "/w120-w120-F72d12-20261117T200231Z/env.txt"
1118  F_ENV_T, F_PROCS = proc_list(F_ENV)
1119  F_TOP = max(F_PROCS, key=lambda x: x[2])
1120  need(F_TOP[0] == 5 and F_TOP[3] == "pr/ttyAMA-1" and F_TOP[1] == "root", "F72d12 env.txt: the busiest process is not pr/ttyAMA-1 in line 5")
1121  GAPS = R + "/dimm7200-20261117/gaps.txt"
1122  m_ = re.match(r"^0 first=2026-11-17T(\d\d:\d\d:\d\d)\+00:00 ", lines_of(GAPS)[6])
1123  need(m_, "gaps.txt: line 7 is not the row of boot 0")
1124  BOOT7_KLOG = m_.group(1)                                   # first kernel log line of the boot of the rerun
1125  F_AFTER_BOOT_S = secs(F_LAUNCH) - secs(BOOT7_KLOG)
1126  F_ENV_BEFORE_S = secs(F_LAUNCH) - secs(F_ENV_T)
1127  need(0 &lt; F_AFTER_BOOT_S &lt; 60 and 0 &lt; F_ENV_BEFORE_S &lt; 60, "F72d12: launch is not shortly after the first kernel log line and the process list")</pre></td><td valign="top">F72d12, the first of the three visits.<ul><li><code>F_TOP</code> is the row of its process list with the highest %CPU. The script stops unless this is line 5 of the file, the command <code>pr/ttyAMA-1</code> of the user <code>root</code>.</li><li>Line 7 of gaps.txt gives <code>BOOT7_KLOG</code>, the time of the first kernel log line of the 7200 MT/s boot. The script stops unless this line starts with <code>0 first=</code> and a time of 2026-11-17.</li><li>The script takes only this time from the line. The same line holds a second time (20:06:34, after <code>last=</code>) and the text <code>hwerr=0</code>. The script does not read them.</li><li><code>F_AFTER_BOOT_S</code> is the launch time of F72d12 minus <code>BOOT7_KLOG</code>, in seconds. <code>F_ENV_BEFORE_S</code> is the launch time minus the time of the process list.</li><li>Both must be above 0 s and below 60 s.</li></ul>The saved output of a build shows 20 s and 5 s, and 51.6 %CPU for <code>pr/ttyAMA-1</code> [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1128  VISIT_ENV = {}
1129  for tg in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):
1130      fo = [r for r in L_OLD + I_OLD if r["tag"] == tg][0]["folder"].replace("R/", R + "/", 1)
1131      when, rows = proc_list(fo + "/env.txt")
1132      need(0 &lt; secs(LAUNCH[tg]["first_launch"][11:19]) - secs(when) &lt; 60, f"{tg}: env.txt was not written shortly before the launch")
1133      VISIT_ENV[tg] = (fo + "/env.txt", max(x[2] for x in rows))
1134  L_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72L1", "T72L2", "T72L3"))
1135  I_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72I1", "T72I2"))
1136  need(max(L_ENV_MAX, I_ENV_MAX) &lt; 1, "part L or control I: a process list shows a busy process")
1137  check(True, f"start state: F72d12 launched {F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG}); its process list, written {F_ENV_BEFORE_S} s before the launch, "
1138              f"shows {F_TOP[3]} at {F_TOP[2]} %CPU; process lists of part L and control I: at most {max(L_ENV_MAX, I_ENV_MAX)} %CPU")
1139</pre></td><td valign="top">Part L and control I, the two later visits (5 steps).<ul><li>For each step, <code>proc_list</code> reads env.txt of the result folder of the step.</li><li>The process list must have been written more than 0 s and less than 60 s before the first launch of the step (<code>first_launch</code> in <code>meta.launches</code>).</li><li><code>VISIT_ENV</code> keeps the path of env.txt and the highest %CPU of its list.</li><li>The script stops unless the highest %CPU value of all 5 lists is below 1 %. %CPU is an average over the life of a process. So this test cannot show a short busy phase of a process that has run since the boot.</li><li><code>check(True, ...)</code> adds the summary line.</li></ul>The saved output of a build shows at most 0.1 %CPU [Ref5].</td></tr>
<tr><td colspan="2"><b>Machine state checks, continued: the boot with 10 modules</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1140  # the number in the kernel line "This system has N DIMM sockets" is not the slot count: a boot of 2026-11-17 printed 10
1141  KLOG10 = R + "/dimm-check-20261117/k-1.txt"
1142  k10 = lines_of(KLOG10)
1143  K10_LINE = [i for i, l in enumerate(k10, 1) if "ghes_edac: This system has 10 DIMM sockets" in l]
1144  mk10 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", k10[0])
1145  need(len(K10_LINE) == 1 and mk10, "kernel log k-1.txt: no single line with 10 modules, or no time in line 1")
1146  BOOT10_FROM = f"2026-11-{mk10.group(1)} {mk10.group(2)}"
1147
1148</pre></td><td valign="top">These lines are top-level statements. They continue the raw-file checks for the machine state section of the page, which start at line 811.<ul><li><code>k-1.txt</code> is the saved kernel log of the boot BASEd10. <code>K10_LINE</code> holds the numbers of its lines with the text <code>This system has 10 DIMM sockets</code>.</li><li>The script stops unless exactly one such line exists and line 1 starts with <code>Nov</code>, a day and a time.</li><li><code>BOOT10_FROM</code> is the date and time of line 1 of that log. The year 2026 and the month 11 are fixed text of the script. In the saved output of a build it is 2026-11-17 04:17:19 [Ref5].</li></ul>The comment gives the purpose. The number in this Linux kernel line is not the number of slots of the board: this boot printed 10, and the boot of the rerun printed 12 (checked in line 897).</td></tr>
<tr><td colspan="2"><b>Function <code>mem_line</code>: the memory size line of a kernel log</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1149  def mem_line(ll):
1150      hit = [(i, re.search(r"kernel: Memory: (\d+)K/(\d+)K available", l)) for i, l in enumerate(ll, 1)]
1151      hit = [(i, int(m.group(2))) for i, m in hit if m]
1152      need(len(hit) == 1, "kernel log: no single line 'Memory:'")
1153      return hit[0]
1154
1155</pre></td><td valign="top">Takes the lines of a kernel log. It searches each line for the text <code>kernel: Memory: &lt;a&gt;K/&lt;b&gt;K available</code>. It stops unless exactly one line matches. It returns the line number and the number <code>&lt;b&gt;</code> (the second number, after the slash) as an integer.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1156  K10_MEM, K12_MEM = mem_line(k10), mem_line(kl)
1157  MEM_LESS_GIB = Decimal(K12_MEM[1] - K10_MEM[1]) / (1024 * 1024)
1158  need(MEM_LESS_GIB == 64, "kernel logs: the 10-module boot does not show 64 GiB less memory than the 8000 MT/s boot")</pre></td><td valign="top"><code>k10</code> holds the lines of <code>k-1.txt</code>. <code>kl</code> holds the lines of <code>k-5.txt</code>, the saved kernel log of the 8000 MT/s boot (line 934).<ul><li><code>MEM_LESS_GIB</code> is the difference of the two numbers after the slash, divided by 1024 x 1024.</li><li>The numbers are in KiB (1 KiB = 1024 bytes), so the result is in GiB (1 GiB = 1024 x 1024 KiB).</li><li>The script stops unless the result is exactly 64 GiB.</li><li><code>k-5.txt</code> holds 402090256K and <code>k-1.txt</code> holds 334981392K, so the difference is 67108864 KiB.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1159  # the module list that was saved in the boot of the rerun
1160  DMI = R + "/dimm7200-20261117/dmi17-7200.txt"
1161  dmi = lines_of(DMI)
1162  DMI_N = sum(1 for l in dmi if l.strip() == "Memory Device")
1163  need(DMI_N == 12 and sum(1 for l in dmi if "Configured Memory Speed:" in l) == 12 == sum(1 for l in dmi if l.strip() == "Configured Memory Speed: 7200 MT/s"),
1164       "module list of the rerun boot: not 12 modules with one line 'Configured Memory Speed: 7200 MT/s' each")
1165  need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(DMI))) == BOOT_LAST, "module list of the rerun boot: its file time is not inside row 0 of boots.txt")</pre></td><td valign="top"><code>dmi17-7200.txt</code> is the module list that was saved in the boot of the rerun.<ul><li><code>DMI_N</code> counts the lines that are exactly <code>Memory Device</code> (one per module).</li><li>The script stops unless <code>DMI_N</code> is 12, 12 lines hold the text <code>Configured Memory Speed:</code>, and 12 lines are exactly <code>Configured Memory Speed: 7200 MT/s</code>.</li><li>Line 1165 reads the modification time of the file as a UTC time of day. The script stops unless it equals <code>BOOT_LAST</code>, the end time of row 0 of <code>boots.txt</code> (line 907). The message says <code>not inside row 0</code>, but the test is equality with that end time.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1166  # line 6 of try6.txt ("modules=24") is not the module count: the module list holds that number of lines with the text "Size: 32 GB"
1167  DMI_SIZE = sum(1 for l in dmi if "Size: 32 GB" in l)
1168  DMI_SIZE_PLAIN = sum(1 for l in dmi if l.strip() == "Size: 32 GB")
1169  DMI_SIZE_VOL = sum(1 for l in dmi if l.strip() == "Volatile Size: 32 GB")
1170  need(DMI_SIZE == TRY6_MODLINE == DMI_SIZE_PLAIN + DMI_SIZE_VOL and DMI_SIZE_PLAIN == DMI_SIZE_VOL == DMI_N,
1171       "try6.txt line 6: its number is not the number of lines with 'Size: 32 GB' in the module list (one 'Size' and one 'Volatile Size' line per module)")</pre></td><td valign="top">Line 6 of <code>try6.txt</code> reads <code>modules=24</code> in the saved data. <code>TRY6_MODLINE</code> is that number (line 900). The comment says that it is not the module count. These lines test that it is the number of lines with <code>Size: 32 GB</code> in the module list, two per module.<ul><li><code>DMI_SIZE</code> counts the lines of the module list that contain <code>Size: 32 GB</code>.</li><li><code>DMI_SIZE_PLAIN</code> counts the lines that are exactly <code>Size: 32 GB</code>. <code>DMI_SIZE_VOL</code> counts the lines that are exactly <code>Volatile Size: 32 GB</code>.</li><li>The script stops unless <code>DMI_SIZE</code> equals <code>TRY6_MODLINE</code> and the sum of the two exact counts, and each exact count equals <code>DMI_N</code>.</li><li>The saved output of a build shows 24 lines: 12 <code>Size</code> lines and 12 <code>Volatile Size</code> lines [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1172  check(True, f"module count: try6.txt line 5 holds '12 DIMM sockets'; the module list saved at {BOOT_LAST} holds {DMI_N} modules with one speed line each; "
1173              f"the kernel log of the boot of {BOOT10_FROM} holds '10 DIMM sockets' and {MEM_LESS_GIB} GiB less memory; "
1174              f"try6.txt line 6 reads 'modules={TRY6_MODLINE}', and the module list holds {DMI_SIZE} lines with 'Size: 32 GB' ({DMI_SIZE_PLAIN} 'Size' and {DMI_SIZE_VOL} 'Volatile Size')")</pre></td><td valign="top"><code>check(True, ...)</code> adds one line to the self-check list. It holds the values that lines 1140 to 1171 checked. The line is always PASS: a false fact has already stopped the script in a <code>need</code> call.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1175  need(all(l.startswith("done /home/jhan/") for l in gl + g2l if l.startswith("done ")), "run logs: a result folder is not under the home folder of jhan")
1176</pre></td><td valign="top"><code>gl</code> and <code>g2l</code> are the lines of the two run logs (line 873). The script stops unless every line that starts with <code>done </code> continues with <code>/home/jhan/</code>. So every result folder that the logs name lies under the home folder of the user jhan.</td></tr>
<tr><td colspan="2"><b>Argument lines: which process ran which line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1177  # the argument lines: which earlier rows ran the line of part L, and whether the lines of part C ran before</pre></td><td valign="top">The block up to line 1231 answers two questions from the raw files. Which earlier rows ran the argument line of part L? Did the argument lines of part C run before the rerun?</td></tr>
<tr><td colspan="2"><b>Function <code>spec_line</code>: the argument line of a spec file</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1178  def spec_line(path):
1179      """(name, arguments, kernel sequence) of the one argument line of a spec file."""
1180      ll = [l for l in lines_of(path) if l.strip()]
1181      need(len(ll) == 1 and "|" in ll[0], f"{path}: not one argument line")
1182      name, args = ll[0].split("|", 1)
1183      m = re.search(r"--seq (\S+)", args)
1184      need(m, f"{path}: no kernel sequence")
1185      return name, args.strip(), m.group(1)
1186
1187</pre></td><td valign="top">Reads a spec file and drops its empty lines.<ul><li>It stops unless exactly one line is left and that line contains <code>|</code>.</li><li>It splits the line at the first <code>|</code> into the name and the arguments.</li><li>It returns the name, the arguments without spaces at both ends, and the kernel sequence (the word after <code>--seq</code>).</li><li>It stops when the arguments hold no <code>--seq</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>launch_args</code>: the arguments of a launch line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1188  def launch_args(folder, tag):
1189      """The arguments of the launch line of a process in launches.txt of a result folder (R/...)."""
1190      hit = [l for l in lines_of(folder.replace("R/", R + "/", 1) + "/launches.txt") if l.startswith(f"launch {tag} ")]
1191      need(len(hit) == 1 and " args " in hit[0], f"{folder}: no single launch line of {tag}")
1192      return hit[0].split(" args ", 1)[1].strip()
1193
1194</pre></td><td valign="top"><code>folder</code> is a result folder in the short form <code>R/...</code>. <code>tag</code> is the name of a process.<ul><li>The function reads <code>launches.txt</code> of that folder and takes the lines that start with <code>launch &lt;tag&gt; </code>.</li><li>It stops unless exactly one such line exists and holds the text <code> args </code>.</li><li>It returns the text after <code> args </code>.</li><li>The runner script <code>rx.sh</code> writes such a line directly before it starts the binary with these arguments.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1195  SPEC = {nm: spec_line(f"{S}/{nm}.spec") for nm in ("like", "cfwd", "crev")}
1196  LINE_L = SPEC["like"][0]                                   # the name of the part L line: its csv file carries it
1197  no_seq = lambda a: re.sub(r"--seq \S+", "--seq X", a)</pre></td><td valign="top"><code>SPEC</code> maps <code>like</code>, <code>cfwd</code> and <code>crev</code> to the result of <code>spec_line</code> for the spec file of that name in <code>S</code>.<ul><li><code>LINE_L</code> is the name of the part L line. In the saved data it is <code>a6456</code>, and the csv file of such a process is <code>a6456.csv</code>.</li><li>The lambda <code>no_seq</code> replaces the kernel sequence of an argument line by <code>X</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1198  need(no_seq(SPEC["like"][1]) == no_seq(SPEC["cfwd"][1]) == no_seq(SPEC["crev"][1]) and len({v[2] for v in SPEC.values()}) == 3,
1199       "the three argument lines do not differ in the kernel sequence only")</pre></td><td valign="top">The script stops unless the three argument lines are equal after this replacement and the three kernel sequences are three different texts. So the argument lines of part L and of part C differ in the kernel sequence only.<ul><li>Before the sequence all three files hold <code>--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2</code>.</li><li>After the sequence all three hold <code>--count --pmu-type 11 --events</code> and the same list of 6 events. <code>--count</code> makes the runner count hardware events of the CPU.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1200  SAME_LINE_FOLDERS = sorted({r["folder"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]})
1201  need(len(SAME_LINE_FOLDERS) == 7 and all(launch_args(fo, LINE_L) == SPEC["like"][1] for fo in SAME_LINE_FOLDERS),
1202       "row L-1, part L, control I or F72d12: a process did not run the argument line of part L")
1203  need({r["file"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]} == {LINE_L + ".csv"}, "the csv file of a process of the part L line does not carry the name of the line")</pre></td><td valign="top"><code>SAME_LINE_FOLDERS</code> is the sorted list of the result folders of the <code>oldread</code> records of part L, control I, F72d12 and row L-1. The script stops unless the list has 7 folders and the launch line of the process <code>LINE_L</code> in each folder holds exactly the arguments of <code>like.spec</code>. Line 1203 stops the script unless the csv file of each of these records is <code>LINE_L</code> plus <code>.csv</code>. So these rows ran the same benchmark arguments as part L.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1204  C_FOLDERS = sorted({r["folder"] for r in C_OLD})
1205  for fo in C_FOLDERS:
1206      nms = sorted({r["file"][:-4] for r in C_OLD if r["folder"] == fo})
1207      need(len(nms) == 1 and nms[0] in ("cfwd", "crev") and launch_args(fo, nms[0]) == SPEC[nms[0]][1], f"{fo}: the process did not run the argument line of its spec file")</pre></td><td valign="top"><code>C_FOLDERS</code> is the sorted list of the result folders of the <code>oldread</code> records of part C. For each folder the script takes the csv file names of these records, without <code>.csv</code>. It stops unless the folder has one name, the name is <code>cfwd</code> or <code>crev</code>, and the launch line of that process holds exactly the arguments of the spec file with the same name.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1208  SEQ_FOLDERS, READ_FOLDERS, N_CSV = {}, set(), 0     # kernel sequence -&gt; result folders with a csv file whose header line holds it
1209  for dp_, _, fs_ in os.walk(R):
1210      for f_ in fs_:
1211          if f_.endswith(".csv"):
1212              N_CSV += 1
1213              with open(os.path.join(dp_, f_), encoding="utf-8", errors="replace") as fh_:
1214                  for l in fh_:
1215                      if l.startswith("# bwx"):
1216                          if re.match(r"^# bwx\d+ trial mode:", l):
1217                              continue                # one-CPU trial files of older runners: they hold no kernel sequence</pre></td><td valign="top">A scan of every csv file under the results folder <code>R</code>, at any depth. <code>N_CSV</code> counts the files. The scan uses header lines only. It takes no rate from these files.<ul><li>Only the lines that start with <code># bwx</code> are used.</li><li>A line of the form <code># bwx&lt;digits&gt; trial mode:</code> is skipped. The comment says that such files are one-CPU trial files of older runners and hold no kernel sequence.</li><li>Read again for this companion: 43 csv files hold such lines. All 43 lie in folders whose names start with <code>bwx8-</code>, <code>bwx9-</code>, <code>bwx10-</code> or <code>bwx11-</code>. None of these files holds a <code># bwx: seq=</code> line.</li><li>37 of the 43 files hold process header lines. Each of these lines holds <code>--trial</code> and one CPU number. The other 6 files hold no process header line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1218                          m_ = re.match(r"^# bwx: seq=(\S+)", l)
1219                          need(m_, f"{dp_}/{f_}: a header line of a runner that is neither a kernel sequence nor a trial-mode header")
1220                          fo_ = "R/" + os.path.relpath(dp_, R).split(os.sep)[0]
1221                          SEQ_FOLDERS.setdefault(m_.group(1), set()).add(fo_)
1222                          if "read" in m_.group(1).split(","):
1223                              READ_FOLDERS.add(fo_)</pre></td><td valign="top">The lines that start with <code># bwx</code> and are not skipped:<ul><li>Each one must start with <code># bwx: seq=</code>. If not, the script stops.</li><li><code>fo_</code> is the top-level result folder of the file, in the form <code>R/...</code>.</li><li><code>SEQ_FOLDERS</code> maps each kernel sequence to the set of folders with a file that holds it.</li><li><code>READ_FOLDERS</code> collects the folders with a sequence that names the kernel <code>read</code>. The sequence is split at its commas, so the names <code>oldread</code> and <code>asmread</code> do not count.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1224  need(sorted(SEQ_FOLDERS[SPEC["cfwd"][2]] | SEQ_FOLDERS[SPEC["crev"][2]]) == C_FOLDERS, "csv files of the results folder: a folder other than the 4 part C folders holds a part C kernel sequence")</pre></td><td valign="top">Three hard assertions on the result of the scan follow (lines 1224, 1227 and 1229), then one line for the self-check list. Line 1224: the folders with the sequence of <code>cfwd.spec</code> or of <code>crev.spec</code> must be exactly the part C folders. So no csv file in another folder under <code>R</code> holds a part C sequence.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1225  # the kernel read in a sequence: the 4 part C folders, and folders of the older runner bwx (rules file, part A list: B7-*, C3-*, SHORT-*; part C list: B5-*)
1226  READ_OTHER = sorted(READ_FOLDERS - set(C_FOLDERS))</pre></td><td valign="top"><code>READ_OTHER</code> lists the folders with the kernel <code>read</code> in a sequence that are not part C folders. The comment calls them folders of the older runner bwx.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1227  need(READ_OTHER and all(re.match(r"^R/(B5|B7|C3|SHORT)-2026111[34]T", fo_) for fo_ in READ_OTHER),
1228       f"csv files of the results folder: the kernel read is in a sequence of a folder that is neither part C nor a folder of runner bwx: {READ_OTHER}")</pre></td><td valign="top">The script stops unless both hold:<ul><li>The list <code>READ_OTHER</code> is not empty.</li><li>Each name starts with <code>R/B5-</code>, <code>R/B7-</code>, <code>R/C3-</code> or <code>R/SHORT-</code> and a date of 2026-11-13 or 2026-11-14.</li></ul>The script tests the folder names only. Read again for this companion:<ul><li>Every process header line of the 7 folders names the binary <code>bwx</code>, except 3 lines of the <code>SHORT</code> folder. These 3 lines name <code>bwx_o0</code>, <code>bwx_o36</code> and <code>bwx_o52</code>.</li><li>The kernel sequences of these 3 lines do not hold <code>read</code>. So each of the 124 process header lines with <code>read</code> in its sequence names the binary <code>bwx</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1229  need({r["folder"] for r in OTHER} &lt;= set(READ_OTHER), "runner bwx: a folder used on the page is not among the folders with the kernel read")</pre></td><td valign="top">Every folder of the records in <code>OTHER</code> must be in <code>READ_OTHER</code>. If not, the script stops.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1230  check(True, f"argument lines: like.spec, cfwd.spec and crev.spec differ in the kernel sequence only; row L-1, part L, control I and F72d12 ({len(SAME_LINE_FOLDERS)} folders) ran the line of like.spec; "
1231              f"header lines of the {N_CSV} csv files under R: only the {len(C_FOLDERS)} part C folders hold a part C sequence; the kernel read is in a sequence there and in {len(READ_OTHER)} folders of runner bwx only")
1232</pre></td><td valign="top">The <code>check</code> call adds one PASS line with the counts. The rules file states that no earlier bwx12 result at 8000 MT/s holds the kernel <code>read</code>. This scan tests that statement on the header lines. The saved output of a build shows 903 csv files, 4 part C folders and 7 folders in <code>READ_OTHER</code> [Ref5].</td></tr>
<tr><td colspan="2"><b>Function <code>bwx_header</code>: header lines of a bwx process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1233  # rows of runner bwx: the header lines of their processes (start option, counter setting, load at launch).
1234  # Rule V2 point 4 asks the report to state how these rows differ from part C. Table 6 gives their load at launch.
1235  def bwx_header(rec):
1236      """Header facts of the process of a record of runner bwx, read from its csv file: the line "-- step ... tag T ... loadavg L ... utc H:M:S args ..."
1237      before the record, and the one line "# bwx: ..." that follows it. Both must agree with the record."""
1238      fl = file_lines(rec)
1239      i = rec["line"] - 1
1240      while i &gt;= 0 and not fl[i].startswith("-- "):
1241          i -= 1
1242      where = f"{rec['folder']}/{rec['file']} line {i + 1}"
1243      m = re.match(r"^-- step \S+ tag (\S+) binary (\S+) .* loadavg (\S+) .* utc (\d\d:\d\d:\d\d) args (.*)$", fl[i]) if i &gt;= 0 else None
1244      need(m and m.group(1) == rec["tag"] and m.group(2) == "bwx" and m.group(4) == rec["launch_utc"][11:19] and D(m.group(3)) == D(rec["load1_at_launch"]),
1245           f"{where}: not the header line of the process of this record (tag, binary, launch time or load differs)")</pre></td><td valign="top">Takes one record of the older runner bwx and checks the header lines of its process in the csv file. Rule V2 point 4 asks the report to state how these rows differ from part C (comment in lines 1233 and 1234). Table 6 of the page gives their load at launch.<ul><li>From the I row of the record the function goes back line by line to the nearest line that starts with <code>-- </code> (the process header line).</li><li>That line must hold the tag of the record, the binary <code>bwx</code>, the launch time of the record and its 1-minute load average at launch. If not, the script stops.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1246      hl = [l for l in fl[i + 1:rec["line"]] if l.startswith("# bwx:")]
1247      h = re.search(r" start=(\w+) .*\bcount=(\d)\b", hl[0]) if len(hl) == 1 else None
1248      need(h and h.group(1) == rec["start"] and int(h.group(2)) == rec["count"] and f"--start {rec['start']}" in m.group(5),
1249           f"{where}: the start option or the counter setting of the csv header differs from the record")
1250      sq = re.search(r"--seq (\S+)", m.group(5))
1251      need(sq, f"{where}: no kernel sequence in the header line")
1252      return dict(line=i + 1, start=h.group(1), count=int(h.group(2)), seq=sq.group(1), dataset=rec["dataset"], tag=rec["tag"], launch=rec["launch_utc"], load=D(rec["load1_at_launch"]))
1253
1254</pre></td><td valign="top">The second half of <code>bwx_header</code>. The script stops unless both hold:<ul><li>Exactly one <code># bwx:</code> line lies between the process header line and the I row. Its <code>start=</code> and <code>count=</code> values equal the fields <code>start</code> and <code>count</code> of the record. The arguments of the header line hold <code>--start</code> with the same value.</li><li>The arguments hold a kernel sequence (<code>--seq</code>).</li></ul>It returns the line number of the header line, the start option, the counter setting and the sequence. It adds the dataset, the tag, the launch time and the load of the record.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1255  X_HEAD = {}
1256  for r in OTHER:
1257      if r["proc_key"] not in X_HEAD:
1258          X_HEAD[r["proc_key"]] = bwx_header(r)
1259  X_POOL_HEAD = [h for h in X_HEAD.values() if h["dataset"] in BWX_POOL]
1260  X_REV_HEAD = [h for h in X_HEAD.values() if h["dataset"] not in BWX_POOL]</pre></td><td valign="top"><code>X_HEAD</code> gets one <code>bwx_header</code> result per process of <code>OTHER</code> (one per <code>proc_key</code>). The call uses the first record of the process in the list. <code>X_POOL_HEAD</code> holds the processes of the datasets B7a, B7b, C3a and C3b (<code>BWX_POOL</code>, line 322). <code>X_REV_HEAD</code> holds the others.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1261  need(len(X_POOL_HEAD) == 24 and len(X_REV_HEAD) == 4, "runner bwx: expected 24 + 4 processes with a header line")
1262  need({d: sorted({h["count"] for h in X_POOL_HEAD if h["dataset"] == d}) for d in BWX_POOL} == {"B7a": [0], "B7b": [0], "C3a": [1], "C3b": [1]},
1263       "runner bwx: the counter setting is not 0 in the two B7 folders and 1 in the two C3 folders")
1264  need(all(X_FILES_ := [sorted({r["folder"] for r in OTHER if r["dataset"] == d}) for d in BWX_POOL]) and [f[0][:5] for f in X_FILES_] == ["R/B7-", "R/B7-", "R/C3-", "R/C3-"],
1265       "runner bwx: the four datasets are not two B7 folders and two C3 folders")
1266  X_OFFSET = sum(1 for h in X_POOL_HEAD if h["start"] == "offset")
1267  need(X_OFFSET == 12 and {h["start"] for h in X_POOL_HEAD} == {"common", "offset"} and all((h["start"] == "offset") == ("-offset-" in h["tag"]) for h in X_POOL_HEAD),
1268       "runner bwx: not 12 of the 24 processes with the start option 'offset'")</pre></td><td valign="top">The script stops unless all of these hold:<ul><li><code>X_POOL_HEAD</code> has 24 processes and <code>X_REV_HEAD</code> has 4.</li><li>The counter setting is 0 in every process of B7a and B7b, and 1 in every process of C3a and C3b.</li><li>Each of the four datasets has records, and its first folder name starts with <code>R/B7-</code>, <code>R/B7-</code>, <code>R/C3-</code>, <code>R/C3-</code>, in this order. The operator <code>:=</code> stores the folder lists in <code>X_FILES_</code> inside the expression.</li><li><code>X_OFFSET</code> is 12. It counts the processes of the 24 with the start option <code>offset</code>. The others have <code>common</code>. A process has <code>offset</code> exactly when its tag contains <code>-offset-</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1269  # part C: the same two settings, from the one "# bwx:" line of each csv file and from the launch line
1270  for fo in C_FOLDERS:
1271      r0 = [r for r in C_OLD if r["folder"] == fo][0]
1272      hl = [l for l in file_lines(r0) if l.startswith("# bwx:")]
1273      need(len(hl) == 1 and " start=common " in hl[0] and re.search(r"\bcount=1\b", hl[0]) and "--start common" in launch_args(fo, r0["file"][:-4]) and "--count" in launch_args(fo, r0["file"][:-4]).split(),
1274           f"{fo}: part C did not run with the start option 'common' and with counters")
1275  need(all(r["count"] == 1 and r["start"] == "common" for r in C_OLD + C_READ + C_ASM), "part C: a record holds another start option or counter setting")</pre></td><td valign="top">The same two settings for part C. For each part C folder the script takes the csv file of the first <code>oldread</code> record. It stops unless the file has exactly one <code># bwx:</code> line, with <code>start=common</code> and <code>count=1</code>, and the launch line of the process holds <code>--start common</code> and the word <code>--count</code>. Line 1275 stops the script unless every part C record of <code>oldread</code>, <code>read</code> and <code>asmread</code> has <code>count</code> 1 and <code>start</code> <code>common</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1276  # the kernel sequence of the 24 bwx processes: 8 kernels, the order of cfwd at its start and the order of crev at its end
1277  X_SEQ = {h["seq"] for h in X_POOL_HEAD}
1278  need(len(X_SEQ) == 1, f"runner bwx, tags common-6000-*: not one kernel sequence: {sorted(X_SEQ)}")
1279  X_SEQ = next(iter(X_SEQ)).split(",")
1280  need(len(X_SEQ) == 8 and ",".join(X_SEQ[:3]) == SPEC["cfwd"][2] and ",".join(X_SEQ[-3:]) == SPEC["crev"][2],
1281       "runner bwx, tags common-6000-*: the sequence does not hold the order of cfwd at its start and the order of crev at its end")
1282  check(True, f"rows of runner bwx: {len(X_HEAD)} header lines agree with the records (tag, launch time, load, start option, counter setting); counter setting 0 in the two B7 folders and 1 in the two C3 folders; "
1283              f"{X_OFFSET} of {len(X_POOL_HEAD)} processes with the start option 'offset'; part C: start option 'common' and counters in 4 of 4 csv headers; "
1284              f"sequence of {len(X_SEQ)} kernels with the order of cfwd at positions 0 to 2 and the order of crev at positions 5 to 7")
1285
1286</pre></td><td valign="top"><code>X_SEQ</code> is the kernel sequence of the 24 processes.<ul><li>The script stops unless all 24 header lines hold the same sequence.</li><li>Then the sequence is split at its commas.</li><li>The script stops unless it has 8 kernels, its first three are the sequence of <code>cfwd.spec</code> (oldread, read, asmread) and its last three are the sequence of <code>crev.spec</code> (asmread, read, oldread).</li><li>So in these rows <code>read</code> at position 1 ran directly after <code>oldread</code>, and <code>read</code> at position 6 ran directly after <code>asmread</code>.</li><li>The <code>check</code> call adds one PASS line with these counts.</li></ul></td></tr>
<tr><td colspan="2"><b>X2d12 and the three boots with 10 modules</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1287  # rows that the rules file quotes and that are not rows of the list. Each one ran the argument line of part L once on 2026-11-17, in a boot of its own:
1288  # X2d12 (12 modules, rules V2 point 4 and F2 point 2 against rule V4) and three boots with 10 modules (rule V1 points 3 and 4). Checked here in the raw files.</pre></td><td valign="top">The rules file quotes four more processes that are not rows of the list of 8000 MT/s rows. Each one ran the argument line of part L once on 2026-11-17, in a boot of its own: X2d12 with 12 modules, and X1d10, X1d10b and BASEd10 with 10 modules.<ul><li>The lines up to 1344 check them in the raw files and compute their rates.</li><li>The page shows these rates in notes under Table 2.</li><li>No wording of the page comes from them.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>klog_boot</code>: times and module count of a kernel log</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1289  def klog_boot(name):
1290      """First and last time, module count and its line number of a saved kernel log of 2026-11-17."""
1291      path = f"{R}/dimm-check-20261117/{name}.txt"
1292      ll = lines_of(path)
1293      a, b = re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[0]), re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[-1])
1294      n = [(i, int(m.group(1))) for i, l in enumerate(ll, 1) for m in [re.search(r"ghes_edac: This system has (\d+) DIMM sockets", l)] if m]
1295      need(a and b and len(n) == 1, f"{path}: no times of 2026-11-17 in the first and last line, or no single module count line")
1296      return dict(path=path, t0=a.group(1), t1=b.group(1), modules=n[0][1], line=n[0][0], last=len(ll))
1297
1298</pre></td><td valign="top">Reads the saved kernel log <code>&lt;name&gt;.txt</code> of the folder <code>dimm-check-20261117</code>.<ul><li>It takes the time of day of the first and of the last line. Both lines must start with <code>Nov 17</code>.</li><li>It collects the lines of the form <code>This system has N DIMM sockets</code>.</li><li>It stops unless both times are found and exactly one such line exists.</li><li>It returns the path, the two times (<code>t0</code>, <code>t1</code>), the number N (<code>modules</code>), the number of that line (<code>line</code>) and the number of lines of the file (<code>last</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1299  EXTRA = {}
1300  for d_, kname in (("X1d10", "k-4"), ("X1d10b", "k-3"), ("X2d12", "k-2"), ("BASEd10", "k-1")):
1301      o_ = expect(sel(dataset=d_, kernel="oldread", pos=0), 2, 1, f"{d_}, oldread at position 0")
1302      a_ = expect(sel(dataset=d_, kernel="asmread", pos=1), 2, 1, f"{d_}, asmread at position 1")
1303      kb = klog_boot(kname)
1304      fo = o_[0]["folder"]
1305      ll_ = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")
1306      m1, m2 = re.match(rf"^launch {LINE_L} utc (\S+) load (\S+) ", ll_[0]), re.match(rf"^rc 0 {LINE_L} utc (\S+)$", ll_[1])
1307      need(m1 and m2, f"{d_}: launch or 'rc 0' line of the part L line not found in lines 1 and 2 of launches.txt")</pre></td><td valign="top">The loop runs once per row: X1d10 (log <code>k-4</code>), X1d10b (<code>k-3</code>), X2d12 (<code>k-2</code>), BASEd10 (<code>k-1</code>).<ul><li><code>o_</code> and <code>a_</code> are the records of the dataset with <code>oldread</code> at position 0 and with <code>asmread</code> at position 1. <code>expect</code> stops unless each group has 2 intervals of 1 process with 120 threads. Other records are left out: in facts.json the dataset X2d12 also holds 6 records of read_nop96, read_nop256 and read_1pl.</li><li><code>kb</code> holds the facts of the kernel log from <code>klog_boot</code>. <code>fo</code> is the result folder of the first <code>oldread</code> record.</li><li>Lines 1 and 2 of <code>launches.txt</code> must be the <code>launch</code> line and the <code>rc 0</code> line of the process <code>LINE_L</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1308      need(all(r["folder"] == fo and r["file"] == LINE_L + ".csv" and r["binary"] == "bwx12" and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000
1309               and r["modules"] == kb["modules"] and r["launch_utc"] == f"2026-11-17T{m1.group(1)}Z" and D(r["load1_at_launch"]) == D(m1.group(2)) for r in o_ + a_)
1310           and {r["proc_key"] for r in o_} == {r["proc_key"] for r in a_} and {r["kernel_before"] for r in a_} == {"oldread"},
1311           f"{d_}: a record is not a 6 s common-stop interval of bwx12 at 8000 MT/s with the module count of the kernel log, or its launch differs from launches.txt")
1312      need(launch_args(fo, LINE_L) == SPEC["like"][1], f"{d_}: the process did not run the argument line of part L")</pre></td><td valign="top">More hard assertions inside the loop. Lines 1308 to 1311:<ul><li>Every record must name the folder <code>fo</code> and the file <code>LINE_L</code> plus <code>.csv</code>.</li><li>It must be a bwx12 record at 8000 MT/s with the common stop and 6000 ms intervals.</li><li>Its module count must be the count of the kernel log.</li><li>Its launch time and load must be those of the <code>launch</code> line.</li><li>Both groups must come from one process, and each <code>asmread</code> interval must follow <code>oldread</code> directly.</li></ul>Line 1312: the launch line must hold exactly the arguments of <code>like.spec</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1313      need(kb["t0"] &lt; m1.group(1) &lt; m2.group(1) &lt; kb["t1"] and BOOT8_TO[11:19] &lt; kb["t0"] and BOOT8_TO[:10] == "2026-11-17",
1314           f"{d_}: the process does not lie inside the kernel log {kname}.txt, or that boot does not start after the end of the 8000 MT/s boot of the list rows")
1315      bs_ = {r["boot"] for r in o_ + a_}
1316      need(len(bs_) == 1, f"{d_}: the records name more than one boot")
1317      EXTRA[d_] = dict(old=o_, asm=a_, klog=kb, folder=fo, launch=m1.group(1), end=m2.group(1), load=D(m1.group(2)), boot=bs_.pop())</pre></td><td valign="top">The last hard assertions inside the loop.<ul><li>Line 1313: launch and end of the process must lie between the first and the last line of the kernel log. The log must start after <code>BOOT8_TO</code> (line 937), the time of the last line of the saved kernel log of the 8000 MT/s boot. <code>BOOT8_TO</code> must be a time of 2026-11-17.</li><li>Lines 1315 and 1316: the records of a row must name one boot.</li><li>Line 1317: <code>EXTRA</code> then keeps both groups, the log facts, the folder, the launch time, the end time, the load and the boot.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1318  need(len({v["boot"] for v in EXTRA.values()} | {r["boot"] for r in EIGHT}) == 5, "X2d12 and the 10-module rows: not four boots of their own")
1319  need(all(EXTRA[a]["klog"]["t1"] &lt; EXTRA[b]["klog"]["t0"] for a, b in (("X1d10", "X1d10b"), ("X1d10b", "X2d12"), ("X2d12", "BASEd10"))), "X2d12 and the 10-module rows: the four kernel logs overlap in time")
1320  need([EXTRA[d_]["klog"]["modules"] for d_ in ("X1d10", "X1d10b", "X2d12", "BASEd10")] == [10, 10, 12, 10], "X2d12 and the 10-module rows: module counts of the kernel logs")</pre></td><td valign="top">More hard assertions on the four rows.<ul><li>Line 1318: the four boots and the boot of the used 8000 MT/s records (<code>EIGHT</code>, line 310) are 5 different boots.</li><li>Line 1319: the four kernel logs do not overlap in time. Their order is X1d10, X1d10b, X2d12, BASEd10.</li><li>Line 1320: the module counts of the four logs are 10, 10, 12 and 10.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1321  # firmware settings on record at the start of each of these boots (times of the files set.txt, all of 2026-11-17)
1322  need(X1_T &lt; EXTRA["X1d10"]["klog"]["t0"] and EXTRA["X1d10b"]["klog"]["t0"] &lt; X2_T, "X1d10, X1d10b: the boots did not start between the TXREQ Min change and the TXREQ Max change")
1323  need(X2_T &lt; EXTRA["X2d12"]["klog"]["t0"] and EXTRA["X2d12"]["end"] &lt; RV_T, "X2d12: the boot did not start after both TXREQ changes, or the process did not end before the revert")
1324  need(RV_T &lt; EXTRA["BASEd10"]["klog"]["t0"], "BASEd10: the boot did not start after the revert of the TXREQ settings")
1325  need(all(v["klog"]["t1"] &lt; D72_T for v in EXTRA.values()), "X2d12 or a 10-module boot did not end before the change of DIMM Frequency to 7200 MT/s was written")</pre></td><td valign="top">More hard assertions. They test the order in time of the four boots and of the recorded changes of the firmware settings. Lines 1322 to 1324 compare the first log line of each boot with <code>X1_T</code>, <code>X2_T</code> and <code>RV_T</code> (lines 1064 to 1066). These are the times in line 1 of the three files <code>set.txt</code> of the TXREQ changes.<ul><li>X1d10 and X1d10b started after the change of TXREQ Min and before the change of TXREQ Max.</li><li>X2d12 started after both changes, and its process ended before both settings were changed to their original values again (<code>RV_T</code>).</li><li>BASEd10 started after that.</li><li>Line 1325: all four logs end before <code>D72_T</code> (line 1092), the file time of the settings file that changes DIMM Frequency to 7200 MT/s. Only the times of day are compared, not the dates. Read again for this companion: the date of this file time is 2026-11-17.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1326  rX2_old, rX2_asm = Rg(EXTRA["X2d12"]["old"]), Rg(EXTRA["X2d12"]["asm"])</pre></td><td valign="top">Lines 1326 to 1330 compute rates of the four rows.<ul><li>The rows hold 16 records, and 14 of them get a rate. No line of the script computes a rate for the 2 <code>asmread</code> records of BASEd10.</li><li>Each <code>Rg</code> call computes the rate of its records with <code>val</code> (line 176): the sum of <code>bytes / elapsed_s / 1e9</code> over the 120 T rows after the I row.</li><li><code>val</code> stops the script unless this sum, rounded to 0.001 GB/s, equals the field <code>GBps</code> of the record.</li><li>The script does not compare these 14 rates with the rate that the I row prints: the test of lines 341 to 345 covers only <code>USED</code> and <code>OTHER</code>. Computed again for this companion: each of the 14 sums, rounded to 0.01 GB/s, equals the printed rate or lies 0.01 GB/s above it.</li></ul><code>rX2_old</code> and <code>rX2_asm</code> are the ranges of the 2 <code>oldread</code> intervals and of the 2 <code>asmread</code> intervals of X2d12.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1327  T10_ASM = [Rg(EXTRA[d_]["asm"]) for d_ in ("X1d10", "X1d10b")]
1328  T10_APART = (max(g.med for g in T10_ASM) / min(g.med for g in T10_ASM) - 1) * 100       # percent of the lower median
1329  rT10_old = Rg([r for d_ in ("X1d10", "X1d10b", "BASEd10") for r in EXTRA[d_]["old"]])
1330  need(rT10_old.n == 6 and rT10_old.np == 3, "10-module boots, old read: not 6 intervals of 3 processes")</pre></td><td valign="top">The values of the boots with 10 modules:<ul><li><code>T10_ASM</code>: the <code>asmread</code> ranges of X1d10 and of X1d10b, 2 intervals each. The median of 2 values is their mean. Rule V1 point 3 quotes these two boots as two boots at equal settings.</li><li>BASEd10 is not in <code>T10_ASM</code>. It started after the revert (line 1324), so its recorded firmware settings differ from those of the two boots.</li><li><code>T10_APART</code>: the higher of these two medians divided by the lower one, minus 1, times 100. It is the distance of the two medians in percent of the lower median.</li><li><code>rT10_old</code>: the range of the <code>oldread</code> intervals of the three boots with 10 modules. The script stops unless it has 6 intervals of 3 processes.</li></ul>Computed again for this companion: the two medians are 261.52 and 286.01 GB/s, which gives 9.4 %.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1331  g0 = len(CHECKS)
1332  xc_range("X2d12, old read kernel", rX2_old.lo, rX2_old.hi, facts_row("4.2", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])
1333  xc_range("X2d12, asmread", rX2_asm.lo, rX2_asm.hi, facts_row("4.4", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])</pre></td><td valign="top">Cross-checks of these values with <code>FACTS.md</code>. <code>g0</code> is the length of the self-check list before them. Lines 1332 and 1333: the two ranges of X2d12 against the cell <code>Min to max, GB/s</code> of the X2d12 row in sections 4.2 and 4.4, each end to 0.01 GB/s. A missing X2d12 row stops the script in <code>facts_row</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1334  m_ = re.search(rf"gave asmread ({NUM}) / ({NUM}) and ({NUM}) / ({NUM}) GB/s, ({NUM}) % apart", SEC["4.6"])
1335  check(bool(m_) and all(near(q(v), m_.group(i + 1), "0.01") for i, v in enumerate(T10_ASM[0].v + T10_ASM[1].v)) and near(q(T10_APART, "0.1"), m_.group(5), "0.1"),
1336        f"10-module boots, asmread: computed {' / '.join(f2(v) for v in T10_ASM[0].v)} and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s, {f1(T10_APART)} % apart, "
1337        + (f"FACTS.md {m_.group(1)} / {m_.group(2)} and {m_.group(3)} / {m_.group(4)} GB/s, {m_.group(5)} % apart" if m_ else "sentence not found in FACTS.md section 4.6"))</pre></td><td valign="top">Lines 1334 to 1337: section 4.6 must hold a sentence of the form <code>gave asmread a / b and c / d GB/s, e % apart</code>. The four <code>asmread</code> values (rounded to 0.01 GB/s) and <code>T10_APART</code> (rounded to 0.1 %) are compared with it. A sentence that is missing in section 4.6 gives a FAIL line.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1338  m_ = re.search(rf"three 10-module boots gave old read ({NUM}) to ({NUM}) GB/s \(({NUM}) % wide, {rT10_old.n} intervals / {rT10_old.np} processes / 3 boots\)", SEC["4.6"])
1339  check(bool(m_) and near(q(rT10_old.lo), m_.group(1), "0.01") and near(q(rT10_old.hi), m_.group(2), "0.01") and near(q(width_pct(rT10_old), "0.1"), m_.group(3), "0.1"),
1340        f"10-module boots, old read: computed {rT10_old.txt()} GB/s, {f1(width_pct(rT10_old))} % wide, "
1341        + (f"FACTS.md {m_.group(1)} to {m_.group(2)} GB/s, {m_.group(3)} % wide" if m_ else "sentence not found in FACTS.md section 4.6"))
1342  grouped("FACTS.md sections 4.2, 4.4 and 4.6, rows quoted by the rules file and not used for a wording: X2d12 (2 ranges), 10-module boots (4 asmread values, 1 old read range, 2 percent values)", g0)</pre></td><td valign="top"><ul><li>Lines 1338 to 1341: section 4.6 must hold the sentence on the old read range of the three 10-module boots, with the same n. Both ends (0.01 GB/s) and the width in percent of the lower end (<code>width_pct</code>, rounded to 0.1 %) are compared. A sentence that is missing in section 4.6 gives a FAIL line.</li><li>Line 1342: <code>grouped</code> replaces the 4 checks of lines 1332 to 1341 by one line of the self-check list.</li><li>In each of the 4 checks, a comparison passes when the two values differ by at most one rounding step, 0.01 GB/s or 0.1 % (<code>near</code>, line 616).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1343  check(True, f"X2d12 and the three 10-module boots: each process ran the argument line of part L inside its own saved kernel log (k-4, k-3, k-2, k-1: {', '.join(str(EXTRA[d_]['klog']['modules']) for d_ in ('X1d10', 'X1d10b', 'X2d12', 'BASEd10'))} modules); "
1344              f"settings on record at the start of the boots: TXREQ Min changed (2 boots with 10 modules), TXREQ Min and TXREQ Max changed (X2d12), both set back (third boot with 10 modules)")</pre></td><td valign="top">The <code>check</code> call adds one PASS line that summarises lines 1299 to 1325.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1345  # the two decisions of the facts sheet that this page follows were made after the numbers were seen (decisions (k) and (r) of its section 2)
1346  m_ = re.search(r"Decisions made while this sheet was built, after the numbers were seen:\n(.*?)\n## ", FMD, re.S)
1347  need(m_ and re.search(r"^- \(k\) Range of the 8000 MT/s side", m_.group(1), re.M) and re.search(r"^- \(r\) Part C against 8000 MT/s", m_.group(1), re.M),
1348       "FACTS.md section 2: decisions (k) and (r) are not listed under the decisions made after the numbers were seen")
1349</pre></td><td valign="top">Lines 1346 to 1348 search <code>FACTS.md</code> for the list with the title <code>Decisions made while this sheet was built, after the numbers were seen:</code>. The script stops unless this list has the items <code>(k) Range of the 8000 MT/s side</code> and <code>(r) Part C against 8000 MT/s</code>. The page follows both decisions.<ul><li>Decision (k) takes the pool of rows L-1 to L-4 as the 8000 MT/s range for parts L and C.</li><li>Decision (r) gives a comparison with 8000 MT/s rows for two rows of part C (<code>oldread</code>, and <code>asmread</code> directly after <code>oldread</code>), although rule F2 says to show part C at 7200 MT/s only.</li></ul></td></tr>
<tr><td colspan="2"><b>One-thread phase of 2026-11-13 and rule F1 point 5</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1350  # the one-thread phase of the test of 2026-11-13 (rule F1 point 5): header lines of one-thread.csv, in the folder of row A-1
1351  ONE = R + "/kernels-20261113T181222Z/one-thread.csv"
1352  need(B_A_OLD["A-1"][0]["folder"] == "R/kernels-20261113T181222Z", "row A-1 is not in the folder of the one-thread file")
1353  one_h = [l for l in lines_of(ONE) if l.startswith("-- ")]
1354  one_t = [re.search(r" utc (\d\d:\d\d:\d\d)$", l) for l in one_h]
1355  need(one_h and all(one_t) and all(" threads 1 " in l for l in one_h), "one-thread.csv: a header line is not a one-thread process with a launch time")
1356  ONE_N, ONE_FIRST, ONE_LAST = len(one_h), one_t[0].group(1), one_t[-1].group(1)
1357  need([m.group(1) for m in one_t] == sorted(m.group(1) for m in one_t) and 0 &lt;= secs(A1_FIRST) - secs(ONE_LAST) &lt;= 1,
1358       "one-thread.csv: the launch times are not in order, or the 120-thread part did not start within 1 s of the last one-thread launch")
1359  check(True, f"one-thread phase of 2026-11-13: {ONE_N} one-thread processes launched {ONE_FIRST} to {ONE_LAST}; first 120-thread process of row A-1 launched {A1_FIRST}")</pre></td><td valign="top"><code>one-thread.csv</code> lies in the result folder of row A-1. Line 1352 stops the script when row A-1 is in another folder.<ul><li><code>one_h</code> holds the process header lines of the file (lines that start with <code>-- </code>). <code>one_t</code> holds the launch time at the end of each line.</li><li>The script stops unless every header line has a launch time and holds the text <code> threads 1 </code>.</li><li><code>ONE_N</code> is the number of these processes. <code>ONE_FIRST</code> and <code>ONE_LAST</code> are the first and the last launch time.</li><li>Line 1357: no launch time may be earlier than the one before it. The first 120-thread process of row A-1 (<code>A1_FIRST</code>, line 991) must start 0 s to 1 s after the last one-thread launch.</li></ul>The saved output of a build shows 192 one-thread processes from 18:12:23 to 18:17:20 and the first 120-thread launch at 18:17:21 [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1360  # rule F1 point 5, third sentence: the old read kernel of rows A-1 and A-2 after one-thread work and directly after 120-thread work.
1361  # In both csv files the round-1 process of bw_old read is the first process, and the round-2 process is the last one.
1362  rA12_old = Rg(expect(B_A_OLD["A-1"] + B_A_OLD["A-2"], 12, 4, "rows A-1 and A-2, bw_old read"))</pre></td><td valign="top">Rule F1 point 5 needs the rate of the old read kernel after one-thread work and directly after 120-thread work. <code>rA12_old</code> is the range of the bw_old read records of rows A-1 and A-2. <code>expect</code> stops unless they are 12 intervals of 4 processes. The rates are the <code>GBps</code> fields of these part A records.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1363  A12_GAP = []                                               # seconds from the launch of the process before the round-2 process to the launch of the round-2 process
1364  for d_, heads_ in (("A-1", HA1), ("A-2", HA2)):
1365      need(sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 1}) == [1] and sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 2}) == [len(heads_)],
1366           f"{d_}: bw_old read is not the first process (round 1) and the last process (round 2) of the csv file")
1367      need(" binary bw_new " in heads_[-2][2] and re.search(r"kernel read\b", heads_[-2][2]) and "threads 120 " in heads_[-2][2],
1368           f"{d_}: the process before the last process of the csv file is not a 120-thread process of bw_new read")
1369      A12_GAP.append(secs(heads_[-1][1]) - secs(heads_[-2][1]))
1370  need(all(0 &lt; x &lt;= 5 for x in A12_GAP), f"rows A-1 and A-2: the round-2 process of bw_old read did not start within 5 s of the launch of the process before it: {A12_GAP}")</pre></td><td valign="top">The loop tests the order of the processes in the csv files of rows A-1 and A-2.<ul><li><code>HA1</code> and <code>HA2</code> are the process header lines of the two csv files (line 990). <code>_fproc</code> is the number of the process of a record inside its csv file (line 349).</li><li>Line 1365: in each file the round-1 process of bw_old read must be process 1, and the round-2 process must be the last process.</li><li>Line 1367: the process before the last one must be a 120-thread process of bw_new with the kernel <code>read</code>.</li><li><code>A12_GAP</code> gets the seconds between the launches of these last two processes. Line 1370 stops the script unless each gap is above 0 s and at most 5 s. The saved output shows 2 s and 3 s [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1371  # row A-2 started after one-thread work too: the run that ended before it (its own result folder) holds one-thread processes only
1372  ONE2 = R + "/partA-20261113T204939Z"
1373  one2_h = [l for f_ in ("A5.csv", "A6.csv") for l in lines_of(f"{ONE2}/{f_}") if l.startswith("-- ")]
1374  one2_end = [m.group(1) for m in (re.match(r"^## end utc=2026-11-13T(\d\d:\d\d:\d\d)Z", l) for l in lines_of(ONE2 + "/env.txt")) if m]
1375  need(one2_h and all(" --threads 1 " in l for l in one2_h) and len([l for l in lines_of(ONE2 + "/launches.txt") if l.startswith("== ")]) == len(one2_h)
1376       and sorted(f_ for f_ in os.listdir(ONE2) if f_.endswith(".csv")) == ["A5.csv", "A6.csv"] and len(one2_end) == 1 and 0 &lt; secs(A2_FIRST) - secs(one2_end[0]) &lt;= 10,
1377       "row A-2: the run before it does not hold one-thread processes only, or it did not end within 10 s before the first launch of row A-2")</pre></td><td valign="top">Row A-2 started after one-thread work too. <code>ONE2</code> is the result folder of the run before it. The script stops unless all of these hold:<ul><li>Every process header line of <code>A5.csv</code> and <code>A6.csv</code> holds the text <code> --threads 1 </code>.</li><li><code>launches.txt</code> of the folder has as many lines that start with <code>== </code> as there are header lines.</li><li><code>A5.csv</code> and <code>A6.csv</code> are the only csv files of the folder.</li><li><code>env.txt</code> holds exactly one line <code>## end utc=...</code>, and the first launch of row A-2 (<code>A2_FIRST</code>, line 991) is more than 0 s and at most 10 s after that time.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1378  xc_text_range("rule F1 point 5: old read kernel of rows A-1 and A-2", "1.5", rA12_old.lo, rA12_old.hi, "", "0.01", f2)
1379  check(True, f"rule F1 point 5: bw_old read of rows A-1 and A-2 gave {rA12_old.txt()} GB/s ({n8000(rA12_old.recs)}). In both csv files round 1 is the first process and round 2 is the last one, "
1380              f"launched {A12_GAP[0]} s and {A12_GAP[1]} s after a 120-thread process of bw_new read. Row A-1 started within 1 s of the last launch of its one-thread phase. "
1381              f"Row A-2 started {secs(A2_FIRST) - secs(one2_end[0])} s after the end of a run of {len(one2_h)} one-thread processes")
1382</pre></td><td valign="top"><code>xc_text_range</code> adds a check: the range of <code>rA12_old</code>, rounded to 0.01 GB/s, must be present in section 1.5 of <code>FACTS.md</code> in the form <code>low to high</code>. The last <code>check</code> adds a PASS line with the range, n and the gaps. The saved output shows 464.42 to 467.06 GB/s from 12 intervals of 4 processes [Ref5].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1383  # the earlier report does not establish the cause of the lower rate of the load-only loop
1384  need(os.path.exists(EARLIER), f"the earlier report does not exist: {EARLIER}")
1385  with open(EARLIER, encoding="utf-8") as f_:
1386      need("the rule inside the core that causes this is not established" in f_.read(), "the earlier report: the sentence 'not established' of its Short version was not found")
1387</pre></td><td valign="top">The earlier report (<code>EARLIER</code>, line 32) must exist, and its text must hold the words <code>the rule inside the core that causes this is not established</code>. If not, the script stops. The reference list of the page says that the Short version of that report holds this statement (line 1455). The raw-file checks that started at line 811 end here.</td></tr>
<tr><td colspan="2"><b>Reference list of the page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1388  # ------------------------------------------------------------------ references
1389  addref("facts", S + "/FACTS.md", "the detailed record of this rerun (facts sheet): every interval, every check, every decision")
1390  addref("json", S + "/facts.json", "every interval as one record, built from the raw files. Data source of this page")
1391  addref("rules", S + "/baselines-and-rules.txt", "the list of 8000 MT/s rows and the comparison rules V1 to V4, F1, F2, written before the run")</pre></td><td valign="top"><code>addref</code> (line 815) adds one entry to <code>REFS</code>: a key, the path in short form and a note. It stops when the path does not exist. All <code>addref</code> calls of the file are in lines 1389 to 1474. These lines add the facts sheet, <code>facts.json</code> and the rules file.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1392  addref("gen", S + "/make_report.py", "script: generator of this page. It computes every rate from the records of facts.json and prints the self-check list. "
1393         "The records hold each rate of bwx12 and bwx rounded to 0.001 GB/s. Rounding such a value again to 0.01 GB/s can change the last digit. "
1394         "So the script sums the 120 thread rows that the record names and rounds the sum once. "
1395         "It reads the machine-state facts of section 4 from the raw files")</pre></td><td valign="top">The note of the key <code>gen</code> (the reference to this script) gives the reason for the sum in <code>val</code>. The records hold each bwx rate rounded to 0.001 GB/s. A second rounding to 0.01 GB/s can change the last digit. So the script sums the 120 thread rows and rounds once.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1396  addref("build", S + "/build_facts.py", "script: builds FACTS.md and facts.json from the raw files")
1397  addref("go", S + "/go.sh", "script: driver of the rerun. Three sessions of parts A, L, C and a fourth part C process")
1398  addref("ra", S + "/ra.sh", "script: part A, the 120-thread part of the test of 2026-11-13 with the same two binaries")
1399  addref("go2", S + "/go2.sh", "script: control I (added after the first numbers were seen), the part L line twice from an idle machine", "lines 2 and 24 to 33")
1400  addref("like", S + "/like.spec", "argument line of part L")
1401  addref("cfwd", S + "/cfwd.spec", "argument line of part C, order oldread, read, asmread")
1402  addref("crev", S + "/crev.spec", "argument line of part C, order asmread, read, oldread")
1403  addref("golog", GOLOG, "log of go.sh: 12 state lines, 10 'done' lines, ALLDONE")
1404  addref("go2log", GO2LOG, "log of go2.sh (control I, added after the first numbers were seen): 6 state lines, ALLDONE")</pre></td><td valign="top">References to <code>build_facts.py</code>, to the scripts <code>go.sh</code>, <code>ra.sh</code> and <code>go2.sh</code>, to the three spec files and to the two run logs.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1405  for s_ in (1, 2, 3):
1406      addref(f"A{s_}", R + "/" + [r for r in A_OLD if r["session"] == s_][0]["folder"][2:] + "/threads120.csv", f"part A, session {s_}: interval rows")
1407  for s_ in (1, 2, 3):
1408      addref(f"L{s_}", R + "/" + [r for r in L_OLD if r["session"] == s_][0]["folder"][2:] + "/a6456.csv", f"part L, session {s_}: interval rows")
1409  for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):
1410      r0 = [r for r in C_OLD if r["tag"] == t_][0]
1411      addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"part C, process {t_}: interval rows")
1412  for t_ in ("T72I1", "T72I2"):
1413      r0 = [r for r in I_OLD if r["tag"] == t_][0]
1414      addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"control I (added after the first numbers were seen), process {t_}: interval rows")
1415  addref("F72", R + "/w120-w120-F72d12-20261117T200231Z/a6456.csv", "F72d12 (earlier run of the same boot, not part of the rerun): interval rows")
1416  addref("F72l", FL, "F72d12 (earlier run of the same boot, not part of the rerun): launch time, load at launch and end of the process", "lines 1 and 2")
1417  addref("F72e", F_ENV, "F72d12 (earlier run of the same boot, not part of the rerun): time and process list before the launch", f"lines 1 and {F_TOP[0]}")
1418  addref("gaps", GAPS, "first and last kernel log line of the boot of the rerun, saved in that boot", "line 7")
1419  for t_ in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):
1420      addref("env" + t_, VISIT_ENV[t_][0], ("part L" if "L" in t_ else "control I (added after the first numbers were seen)") + f", process {t_}: time and process list before the launch")</pre></td><td valign="top">References to the csv files of the rerun, one per step: part A (sessions 1 to 3, <code>threads120.csv</code>), part L (sessions 1 to 3, <code>a6456.csv</code>), part C (T72C1 to T72C4) and control I (T72I1, T72I2).<ul><li>Each path comes from the field <code>folder</code> of the first old-kernel record of that session or tag.</li><li>For part C and control I the file name comes from the field <code>file</code>.</li><li>Then follow the files of F72d12 (csv file, <code>launches.txt</code>, <code>env.txt</code>), <code>gaps.txt</code>, and the <code>env.txt</code> files of part L and control I (<code>VISIT_ENV</code>, line 1128).</li><li>No rate is computed here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1421  addref("A-1", R + "/kernels-20261113T181222Z/threads120.csv", "row A-1 (8000 MT/s): the test of 2026-11-13. Header lines with the launch times", f"first and last header: lines {HA1[0][0]} and {HA1[-1][0]}")
1422  addref("A-2", R + "/partA-20261113T205055Z/A1.csv", "row A-2 (8000 MT/s): same binaries, other process order. Header lines with the launch times",
1423         f"headers of bw_new read round 1 and of {A2_OTHER}: lines {HA2[a2_new_r1[0]['_fproc'] - 1][0]} and {a2_other[0][0]}")
1424  addref("A-3", R + "/partA-20261113T205055Z/A3.csv", "row A-3 (8000 MT/s): three processes of bw_old read (tags onebuf-ms500-1, -2, -3)",
1425         "headers in lines " + ", ".join(str(HA3[i - 1][0]) for i in a3_used) + f", next header in line {HA3[a3_used[-1]][0]}")
1426  addref("L-1", R + "/w120-R8-20261117T020549Z/a6456.csv", "row L-1 (8000 MT/s): the argument line of part L")
1427  addref("L-1l", R + "/w120-R8-20261117T020549Z/launches.txt", "row L-1: launch time with the argument line, and end of the process", "lines 1 and 2")
1428  addref("L-2a", R + "/w120-R1-20261115T185140Z/p1nop.csv", "row L-2 (8000 MT/s), process p1nop")</pre></td><td valign="top">References to the 8000 MT/s rows. Rows A-1, A-2 and A-3: the csv files, with the line numbers of the header lines that the checks above used. Then the csv file and <code>launches.txt</code> of row L-1, and the csv file of process p1nop of row L-2.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1429  addref("L-2b", R + "/w120-R1-20261115T185140Z/p2add.csv", "row L-2 (8000 MT/s), process p2add. It holds the lowest asmread interval of the pool. "
1430         f"Its interval row prints {f2(i_row_rate(LOWEST_ASM))} GB/s. This page uses the sum of the 120 thread rows, {f2(val(LOWEST_ASM))} GB/s",
1431         f"interval row in line {LOWEST_ASM['line']}, the 120 thread rows in the lines after it")</pre></td><td valign="top">The reference to the csv file of process p2add of row L-2. Its note holds two rates of the lowest <code>asmread</code> interval of the pool (<code>LOWEST_ASM</code>, line 520). The two rates use different formulas.<ul><li><code>i_row_rate</code> returns the rate that its I row prints. The I row divides the total bytes of the 120 threads by the longest elapsed time of a thread. Line 1 of the csv file states this formula.</li><li><code>val</code> returns the sum of its 120 T rows. It divides the bytes of each thread by the elapsed time of that thread and adds the 120 results.</li><li><code>f2</code> rounds both to 0.01 GB/s.</li><li>Read again for this companion from the csv file of process p2add: the I row prints 288.53 GB/s, and the sum is 288.540691 GB/s. So the page shows 288.54 GB/s for this interval.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1432  addref("L-2l", R + "/w120-R1-20261115T185140Z/launches.txt", "row L-2: launch times and ends of the two processes", "lines 1 to 4")
1433  addref("L-3", R + "/w120-R5-20261115T203152Z/thp.csv", "row L-3 (8000 MT/s)")
1434  addref("L-3l", R + "/w120-R5-20261115T203152Z/launches.txt", "row L-3: launch time and end of the process thp", "lines 3 and 4")
1435  addref("L-4a", R + "/w120-R6-20261115T203438Z/st1.csv", "row L-4 (8000 MT/s), process st1")
1436  addref("L-4b", R + "/w120-R6-20261115T203438Z/st2.csv", "row L-4 (8000 MT/s), process st2")
1437  addref("L-4c", R + "/w120-R6-20261115T203438Z/st3.csv", "row L-4 (8000 MT/s), process st3")
1438  addref("L-4l", R + "/w120-R6-20261115T203438Z/launches.txt", "row L-4: launch times and ends of the three processes", "lines 1 to 6")</pre></td><td valign="top">References to <code>launches.txt</code> of row L-2, and to the csv files and <code>launches.txt</code> of rows L-3 and L-4.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1439  addref("try6", TRY6, f"record of boot 3bfc57a1: time, boot id, MemTotal, kernel log line with the module count, the line \"modules={TRY6_MODLINE}\" (not the module count), "
1440         "12 x \"Configured Memory Speed: 7200 MT/s\"", "lines 1, 2, 4, 5, 6 and 7")
1441  addref("dmi", DMI, "module list saved in boot 3bfc57a1: 12 entries \"Memory Device\", each with one line \"Configured Memory Speed: 7200 MT/s\"")
1442  addref("boots", BOOTS, "boot list of the journal, saved in boot 3bfc57a1: row 0 is this boot", "line 9")
1443  addref("journal", JOURNAL, "saved journal lines of the 8000 MT/s boot (started 2026-11-09): hardware error records",
1444         "lines " + ", ".join(str(x) for x in sorted([h["line"] for v in HW_ROWS.values() for h in v["recs"]] + [h["line"] for h in HW_A])))
1445  addref("klog", KLOG, "saved kernel log of the 8000 MT/s boot (started 2026-11-09): first line, memory size line, module count line, last line",
1446         f"lines 1, {K12_MEM[0]}, {[i for i, l in enumerate(kl, 1) if 'This system has 12 DIMM sockets' in l][0]} and {len(kl)}")
1447  addref("klog10", KLOG10, f"saved kernel log of the boot that started on {BOOT10_FROM} UTC: first line, memory size line, module count line",
1448         f"lines 1, {K10_MEM[0]} and {K10_LINE[0]}")
1449  addref("x1", FW + "/x1/set.txt", "firmware setting change: TXREQ Min", "lines 1, 8, 9 and 18")
1450  addref("x2", FW + "/x2/set.txt", "firmware setting change: TXREQ Max", "lines 1 and 2")
1451  addref("rev", FW + "/revert/set.txt", "firmware settings set back: TXREQ Max and TXREQ Min", "lines 1, 2 and 4")
1452  addref("qbase", R + "/uefisettings-20261117/questions.json", "firmware settings list of the 8000 MT/s boot")
1453  addref("qrev", FW + "/revert/questions.json", "firmware settings list saved after the revert")
1454  addref("d72", R + "/dimm7200-20261117/set.txt", "firmware setting change: DIMM Frequency = 7200 MT/s", "lines 7 and 8")
1455  addref("earlier", EARLIER, "the earlier report (2026-11-15) on the lower whole-chip read rate of the load-only loop. Its Short version says that the cause is not established")
1456  addref("one", ONE, "the one-thread phase of the test of 2026-11-13: one header line with the launch time per process", f"first and last header: lines {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][0]} and {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][-1]}")</pre></td><td valign="top">References to the raw files of the machine state checks: <code>try6.txt</code>, the module list, <code>boots.txt</code>, the journal lines and the kernel log of the 8000 MT/s boot, the kernel log <code>k-1.txt</code> of the boot BASEd10 (10 modules), the firmware settings files, the earlier report and <code>one-thread.csv</code>. Several entries hold line numbers that the checks computed. <code>addref</code> writes them in brackets after the path. Examples: the lines of the hardware error records (line 1444) and the memory size lines (lines 1446 and 1448).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1457  addref("xX2d12", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/" + LINE_L + ".csv", "row X2d12 (8000 MT/s, 12 modules, shown and not used): interval rows of the argument line of part L")
1458  addref("xX2d12l", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/launches.txt", "row X2d12: launch time with the argument line and the load, and end of the process", "lines 1 and 2")
1459  addref("klogX2d12", EXTRA["X2d12"]["klog"]["path"], "saved kernel log of the boot of row X2d12: first line, module count line, last line",
1460         f"lines 1, {EXTRA['X2d12']['klog']['line']} and {EXTRA['X2d12']['klog']['last']}")
1461  for d_ in ("X1d10", "X1d10b", "BASEd10"):
1462      addref("x" + d_, R + "/" + EXTRA[d_]["folder"][2:] + "/" + LINE_L + ".csv", f"boot with 10 modules at 8000 MT/s (folder tag {d_}, not a row of the list): interval rows of the argument line of part L")
1463  for d_ in ("X1d10", "X1d10b"):
1464      addref("klog" + d_, EXTRA[d_]["klog"]["path"], f"saved kernel log of the boot of the folder tag {d_}: first line, module count line, last line",
1465             f"lines 1, {EXTRA[d_]['klog']['line']} and {EXTRA[d_]['klog']['last']}")
1466  need(EXTRA["BASEd10"]["klog"]["path"] == KLOG10, "BASEd10: its kernel log is not the file of the reference klog10")</pre></td><td valign="top">References to the csv file, <code>launches.txt</code> and the kernel log of X2d12, and to the csv files and kernel logs of the boots with 10 modules. Line 1466 stops the script unless the kernel log of BASEd10 is the file <code>KLOG10</code> of line 1141. That file already has the key <code>klog10</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1467  X_FILES = {}
1468  for d_ in BWX_POOL + ("B5a-rev", "B5b-rev"):
1469      fs_ = sorted({(r["folder"], r["file"]) for r in OTHER if r["dataset"] == d_})
1470      need(len(fs_) == 1, f"runner bwx, {d_}: more than one csv file")
1471      X_FILES[d_] = fs_[0]
1472      what_ = ("rows of runner bwx (other binary, 8000 MT/s), tags common-6000-*" if d_ in BWX_POOL else
1473               "rows of runner bwx (other binary, 8000 MT/s), the two processes with another kernel order (tags b5-rev-*)")
1474      addref("x" + d_, R + "/" + fs_[0][0][2:] + "/" + fs_[0][1], what_ + ": interval rows. This page uses the sum of the 120 thread rows after an interval row")
1475  need(len(set(X_FILES.values())) == 6, "runner bwx: the 6 datasets do not come from 6 csv files")
1476  need(not {X_FILES[d_][0] for d_ in ("B5a-rev", "B5b-rev")} &amp; {X_FILES[d_][0] for d_ in BWX_POOL} and Rg(X_REV_READ).procs == Rg(X_REV_ASM).procs,
1477       "runner bwx: the processes with the other kernel order are not the same 4 processes of two other result folders")
1478</pre></td><td valign="top">References to the csv files of the older runner bwx.<ul><li>For each of the 6 datasets (B7a, B7b, C3a, C3b, B5a-rev, B5b-rev) the script takes the folder and the file of its records in <code>OTHER</code>.</li><li>It stops unless each dataset has exactly one csv file and the 6 files are different.</li><li>Line 1476 stops the script unless the two <code>-rev</code> datasets lie in other folders than the four pool datasets.</li><li>It also stops unless the <code>read</code> records and the <code>asmread</code> records of the <code>-rev</code> datasets come from the same processes (<code>procs</code> of <code>Rg</code>).</li></ul></td></tr>
<tr><td colspan="2"><b>Small HTML helpers</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1479  # ------------------------------------------------------------------ small HTML helpers
1480  CI = "control I (added after the first numbers were seen)"
1481  F72 = "F72d12 (earlier run of the same boot, not part of the rerun)"
1482
1483</pre></td><td valign="top">Two fixed labels. <code>CI</code> is the text for control I, and <code>F72</code> is the text for F72d12.<ul><li>A sentence of the page that uses a label says that control I was added after the first numbers were seen, or that F72d12 is not part of the rerun.</li><li>Other places of the script write the same words directly.</li><li>A check near the end of the file (from line 2794) tests every paragraph, list item, caption, tooltip, word definition and table row of the page. Each one that names control I or F72d12 must hold these words.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>strip_tags</code>: plain text of an HTML text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1484  def strip_tags(s):
1485      return html.unescape(re.sub(r"&lt;[^&gt;]+&gt;", " ", re.sub(r'&lt;span class="ref"&gt;.*?&lt;/span&gt;', " ", s)))
1486
1487</pre></td><td valign="top">Removes the reference marks (<code>span</code> elements of the class <code>ref</code>). Then it replaces every HTML tag by a space. Then it turns HTML character codes such as <code>&amp;amp;</code> back into characters. The page checks at the end of the file use it.</td></tr>
<tr><td colspan="2"><b>Function <code>P</code>: one paragraph</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1488  def P(text, cls=None):
1489      PROSE.append(text)
1490      return f'&lt;p{" class=" + chr(34) + cls + chr(34) if cls else ""}&gt;{text}&lt;/p&gt;'
1491
1492</pre></td><td valign="top">Adds the text to <code>PROSE</code> (the text that counts for the word limit) and returns it as an HTML paragraph. With <code>cls</code> the paragraph gets that class name. <code>chr(34)</code> is the double quote character.</td></tr>
<tr><td colspan="2"><b>Function <code>UL</code>: one bullet list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1493  def UL(items):
1494      PROSE.extend(items)
1495      return "&lt;ul&gt;" + "".join(f"&lt;li&gt;{x}&lt;/li&gt;" for x in items) + "&lt;/ul&gt;"
1496
1497</pre></td><td valign="top">Adds the items to <code>PROSE</code> and returns them as an HTML bullet list.</td></tr>
<tr><td colspan="2"><b>Function <code>table</code>: HTML of one table</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1498  WIDE = ("q1", "q2", "state", "load", "visits", "detail")        # tables with a fixed least width of 900 px (see the style block)
1499
1500
1501  def table(head, rows, cls=""):
1502      o = ['&lt;p class="hint ht"&gt;If the table does not fit the screen, scroll it sideways.&lt;/p&gt;' if cls in WIDE else ""]
1503      o += [f'&lt;div class="tw"&gt;&lt;table class="{cls}"&gt;&lt;thead&gt;&lt;tr&gt;']
1504      o += [f'&lt;th{" class=n" if c.startswith("#") else ""}&gt;{c.lstrip("#")}&lt;/th&gt;' for c in head]
1505      o.append("&lt;/tr&gt;&lt;/thead&gt;&lt;tbody&gt;")
1506      for r in rows:
1507          if isinstance(r, str):
1508              o.append(f'&lt;tr class="grp"&gt;&lt;td colspan="{len(head)}"&gt;{r}&lt;/td&gt;&lt;/tr&gt;')
1509              continue
1510          o.append("&lt;tr&gt;" + "".join(f'&lt;td{" class=n" if head[i].startswith("#") else ""}&gt;{c}&lt;/td&gt;' for i, c in enumerate(r)) + "&lt;/tr&gt;")
1511      o.append("&lt;/tbody&gt;&lt;/table&gt;&lt;/div&gt;")
1512      return "".join(o)
1513
1514</pre></td><td valign="top"><code>WIDE</code> names the table classes with a least width of 900 px. For such a table the function first writes a hint to scroll sideways.<ul><li><code>head</code> is the list of column titles. A title that starts with <code>#</code> marks a number column: the <code>#</code> is removed, and the cells get the class <code>n</code>. The style block aligns this class to the right (line 2606).</li><li>A row that is a text becomes one title row over all columns (class <code>grp</code>).</li><li>Any other row is a list of cells.</li></ul>The function computes no value.</td></tr>
<tr><td colspan="2"><b>Function <code>small</code>: text in small type</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1515  def small(s):
1516      return f'&lt;span class="sm"&gt;{s}&lt;/span&gt;'
1517
1518</pre></td><td valign="top">Wraps a text in a <code>span</code> element of the class <code>sm</code> (small type).</td></tr>
<tr><td colspan="2"><b>Function <code>T</code>: one SVG text element</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1519  # ------------------------------------------------------------------ figure 1: dumbbell
1520  def T(x, y, s, size=12, fill=INK, anchor="start", weight=None, extra=""):
1521      w = f' font-weight="{weight}"' if weight else ""
1522      return f'&lt;text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}&gt;{esc(s)}&lt;/text&gt;'
1523
1524</pre></td><td valign="top">Line 1519 starts the code of figure 1, the dumbbell chart. <code>T</code> returns one SVG <code>text</code> element at the place <code>x</code>, <code>y</code>, with a font size, a colour, an alignment (<code>anchor</code>) and an optional weight. The text is escaped with <code>esc</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1525  HALO = f' paint-order="stroke" stroke="{SURF}" stroke-width="3.5" stroke-linejoin="round"'
1526  TAB = ' style="font-variant-numeric:tabular-nums"'
1527
1528</pre></td><td valign="top">Two attribute texts for <code>T</code>. <code>HALO</code> draws a 3.5 px wide outline in the background colour <code>SURF</code> under the letters. So a line behind a text does not cross the letters. <code>TAB</code> asks for digits of equal width.</td></tr>
<tr><td colspan="2"><b>Function <code>marker</code>: one dot of figure 1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1529  def marker(x, y, color, hollow, r=5.5):
1530      """A hollow marker (8000 MT/s) carries its colour in the stroke. The hover style must not replace that stroke (classes ho and fi)."""
1531      if hollow:
1532          return f'&lt;circle class="mk ho" cx="{x:.1f}" cy="{y:.1f}" r="{r - 0.9:.1f}" fill="{SURF}" stroke="{color}" stroke-width="2.2"/&gt;'
1533      return (f'&lt;circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 1.6:.1f}" fill="{SURF}"/&gt;'
1534              f'&lt;circle class="mk fi" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}"/&gt;')
1535
1536</pre></td><td valign="top">Returns the SVG circle of one dot. <code>color</code> is the colour of the kernel: <code>fig1</code> passes blue for the old read kernel and orange for the load-only loop (line 1669).<ul><li>A hollow dot (an 8000 MT/s row) has the background colour inside and an outline of 2.2 px in the kernel colour.</li><li>A filled dot (a 7200 MT/s row) is a circle in the kernel colour on a larger circle in the background colour.</li><li>The classes <code>ho</code> and <code>fi</code> tell the style block which kind of dot it is. So the style for a dot under the pointer does not replace the outline of a hollow dot.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>kernel_name</code>: display name of a kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1537  def kernel_name(recs):
1538      r = recs[0]
1539      if r["part"] == "A":
1540          return f"{r['binary']} read ({'old' if r['binary'] == 'bw_old' else 'new'} read kernel)"
1541      return {"oldread": "oldread (old read kernel)", "read": "read (new read kernel)",
1542              "asmread": "asmread (in place of the new read kernel)"}[r["kernel"]]
1543
1544</pre></td><td valign="top">Uses the first record of the list only.<ul><li>Part A record: <code>bw_old read (old read kernel)</code> or <code>bw_new read (new read kernel)</code>, by the field <code>binary</code>.</li><li>bwx record: <code>oldread (old read kernel)</code>, <code>read (new read kernel)</code> or <code>asmread (in place of the new read kernel)</code>, by the field <code>kernel</code>. Any other kernel name ends the script with a Python error (<code>KeyError</code>).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>dot_title</code>: tooltip of a dot of figure 1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1545  def dot_title(name, rg):
1546      vals = ", ".join(f2(v) for v in rg.v)
1547      return (f"{name}: {kernel_name(rg.recs)}. Median {f2(rg.med)} GB/s. Intervals: {vals} GB/s. "
1548              f"n = {plural(rg.n, 'interval')} / {plural(rg.np, 'process')}. Source: {src(rg.recs)}.")
1549
1550</pre></td><td valign="top"><code>rg</code> is an <code>Rg</code> object (line 192). The text gives the row name, the kernel, the median, every interval value, n as intervals and processes, and the source rows from <code>src</code> (line 359). <code>f2</code> rounds each rate here to 0.01 GB/s. The interval values are in the order of launch time and interval number, as <code>Rg</code> sorted them.</td></tr>
<tr><td colspan="2"><b>Function <code>f1_row</code>: one row of figure 1 as a dictionary</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1551  def f1_row(name, notes, old, new, drops, hollow, how):
1552      return dict(name=name, notes=notes, old=old, new=new, drops=drops, hollow=hollow, how=how)
1553
1554</pre></td><td valign="top">Returns a dictionary that holds its seven arguments under the same names.<ul><li><code>old</code> and <code>new</code> are <code>Rg</code> objects: the old read kernel and the load-only loop.</li><li><code>drops</code> is a list of drops in percent.</li><li><code>hollow</code> is true for an 8000 MT/s row.</li><li><code>how</code> is a text that says how the drop was formed.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>bwx_row</code>: figure 1 row of one bwx12 process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1555  def bwx_row(name, notes, olds, news, hollow=False):
1556      pr = pairs_in_process(olds, news)
1557      return f1_row(name, notes, Rg([o for o, _ in pr]), Rg([n for _, n in pr]), drops_of(pr), hollow,
1558                    "lowest and highest pair of the same process and round")
1559
1560</pre></td><td valign="top"><code>olds</code> and <code>news</code> are the old-kernel records and the load-only records of one row.<ul><li><code>pairs_in_process</code> (line 407) pairs each load-only interval with the old-kernel interval of the same process and round.</li><li><code>old</code> is the range (<code>Rg</code>) of the old-kernel intervals of the pairs. <code>new</code> is the range of the load-only intervals.</li><li><code>drops_of</code> (line 421) gives one drop per pair: (1 - load-only rate / old rate) x 100. It uses the <code>val</code> values (6 decimals), not the rates rounded to 0.01 GB/s.</li><li>A process with 2 rounds gives 2 pairs. The median of 2 intervals is their mean, so each dot of such a row is the mean of 2 intervals.</li><li>Example, computed again for this companion: process T72C1 gave 466.013926 and 465.540271 GB/s for <code>oldread</code>, and 320.900964 and 320.888793 GB/s for <code>read</code>. The two drops are 31.14 % and 31.07 %. Both round to 31.1 %, so the figure prints one value, 31.1 %.</li></ul></td></tr>
<tr><td colspan="2"><b>Rows of figure 1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1561  IN_PLACE = "asmread in place of the new read kernel"
1562  B1_8000 = [bwx_row(f"L-1 · {hm(B_L_OLD['L-1'][0]['launch_utc'], True)}", [IN_PLACE, "row with the argument line of part L"], olds=B_L_OLD["L-1"], news=B_L_ASM["L-1"], hollow=True)]
1563  B1_7200 = [bwx_row(f"F72d12 · {hm(F_OLD[0]['launch_utc'])}", [IN_PLACE, "earlier run of the same boot, not part of the rerun"], olds=F_OLD, news=F_ASM)]
1564  for s_ in (1, 2, 3):
1565      o_ = [r for r in L_OLD if r["session"] == s_]
1566      B1_7200.append(bwx_row(f"Part L, session {s_} ({o_[0]['tag']})", [IN_PLACE], olds=o_, news=[r for r in L_ASM if r["session"] == s_]))
1567  for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):
1568      o_ = [r for r in C_OLD if r["tag"] == t_]
1569      n_ = [r for r in C_READ if r["tag"] == t_]
1570      B1_7200.append(bwx_row(f"Part C, {t_} ({o_[0]['file'][:-4]})", [f"kernel read = the new read kernel, after {n_[0]['kernel_before']}"], olds=o_, news=n_))
1571  for t_ in ("T72I1", "T72I2"):
1572      B1_7200.append(bwx_row(f"Control I, {t_}", [IN_PLACE, "added after the first numbers were seen"],
1573                             olds=[r for r in I_OLD if r["tag"] == t_], news=[r for r in I_ASM if r["tag"] == t_]))</pre></td><td valign="top"><code>B1_8000</code> and <code>B1_7200</code> are the row lists of the first block of figure 1 (6 s intervals, runner bwx12). <code>IN_PLACE</code> is the note of the rows that use asmread in place of the new read kernel.<ul><li><code>B1_8000</code>: one hollow row, L-1. Rows L-2 to L-4 are not rows of figure 1.</li><li>F72d12: one row.</li><li>Part L: one row per session, from the <code>oldread</code> records at position 0 and the <code>asmread</code> records at position 1 of that session.</li><li>Part C: one row per process (T72C1 to T72C4), from its <code>oldread</code> records and its <code>read</code> records. The note names the kernel that ran directly before <code>read</code>. The <code>asmread</code> intervals of part C are not in figure 1.</li><li>Control I: one row per process (T72I1, T72I2).</li></ul>In a crev process (sequence asmread, read, oldread) the <code>oldread</code> interval of a pair ran after the <code>read</code> interval of the pair.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1574  B2_8000 = [f1_row(f"{d}, round {rnd} · {hm(p['old'].recs[0]['launch_utc'], True)}", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], True,
1575                    "between the medians of the two processes")
1576             for (d, rnd), p in A8_PAIRS.items()]</pre></td><td valign="top">The row lists of the second block (0.5 s intervals, binaries bw_old and bw_new). <code>B2_8000</code> holds one hollow row per entry of <code>A8_PAIRS</code> (line 455): rows A-1 and A-2, rounds 1 and 2. That gives 4 rows. Row A-3 holds bw_old read only and is not in figure 1.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1577  B2_7200 = [f1_row(f"Part A, session {s_}, round {rnd} (T72A{s_})", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], False,
1578                    "between the medians of the two processes")
1579             for (s_, rnd), p in A_PAIRS.items()]</pre></td><td valign="top"><code>B2_7200</code> holds one row per entry of <code>A_PAIRS</code> (line 451): sessions 1 to 3, rounds 1 and 2. That gives 6 rows. In each row of both lists:<ul><li><code>old</code> and <code>new</code> are the ranges of the 3 intervals of the bw_old read process and of the bw_new read process.</li><li>Each interval rate is the field <code>GBps</code> of the record: the column <code>aggregate_GBps</code> of its csv row, with 2 decimals. The header line of the csv file gives the formula of this column: the total bytes of all threads divided by the longest elapsed time of a thread [Ref3].</li><li>The row has one drop, between the two medians: (1 - median of bw_new read / median of bw_old read) x 100 (<code>a_pair</code>, line 444).</li></ul>The rows of the first block use another formula for a rate: the sum of the 120 thread rates (<code>val</code>, line 176).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1580  F1_BLOCKS = [
1581      dict(title="6 s measurements, runner bwx12, all threads stop together", lines=["6 s measurements, runner bwx12,", "all threads stop together"],
1582           groups=[dict(title="8000 MT/s · hollow markers", rows=B1_8000), dict(title="7200 MT/s · filled markers", rows=B1_7200)]),
1583      dict(title="0.5 s measurements, the two binaries of 2026-11-13, each thread finishes its pass",
1584           lines=["0.5 s measurements, the two binaries of", "2026-11-13, each thread finishes its pass"],
1585           groups=[dict(title="8000 MT/s · hollow markers", rows=B2_8000), dict(title="7200 MT/s · filled markers", rows=B2_7200)]),
1586  ]</pre></td><td valign="top"><code>F1_BLOCKS</code> is the data of figure 1: two blocks, each with a group of 8000 MT/s rows and a group of 7200 MT/s rows. <code>lines</code> holds the block title in two lines for the narrow layout.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1587  SAME_LINE_ROWS = [r for r in B1_7200 if not r["name"].startswith("Part C")]
1588  need(len(SAME_LINE_ROWS) == 6, "figure 1: expected 6 rows of the argument line of part L in the 7200 MT/s boot")
1589  F1_NROWS = sum(len(g["rows"]) for b in F1_BLOCKS for g in b["groups"])
1590  need(F1_NROWS == 21, "figure 1: expected 21 rows")
1591
1592</pre></td><td valign="top">Two counts of the rows of figure 1, each with a hard assertion:<ul><li><code>SAME_LINE_ROWS</code> holds the rows of <code>B1_7200</code> whose name does not start with <code>Part C</code>. They are the rows of the argument line of part L in the 7200 MT/s boot. The script stops unless there are 6.</li><li><code>F1_NROWS</code> is the number of all rows. The script stops unless it is 21 (1 + 10 + 4 + 6).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>fig1</code>: draws figure 1 as SVG</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1593  def fig1(layout="wide"):
1594      """The dumbbell chart in one of three layouts, so that it never scrolls sideways.
1595      wide (940 px, windows from 1000 px) and mid (726 px, windows from 780 px): row names in a column at the left.
1596      narrow (386 px, windows below 780 px): the row name stands above its dumbbell, so the chart fits into a 420 px wide window."""
1597      narrow = layout == "narrow"
1598      W, X0, X1 = {"wide": (940, 356, 846), "mid": (726, 300, 646), "narrow": (386, 26, 332)}[layout]
1599      XMAX = 500
1600      sx = lambda v: X0 + (X1 - X0) * float(v) / XMAX
1601</pre></td><td valign="top"><code>layout</code> selects one of three widths: <code>wide</code> (940 px), <code>mid</code> (726 px) or <code>narrow</code> (386 px). <code>W</code> is the width of the drawing. <code>X0</code> and <code>X1</code> are the x places of 0 GB/s and of 500 GB/s (<code>XMAX</code>). <code>sx</code> converts a rate in GB/s to an x place on this linear axis, which starts at 0.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1602      def drawn(notes):
1603          """The note lines as this layout draws them. The mid layout has a label column of 300 px:
1604          a note of more than 44 characters is broken after its comma, so that it ends before the 0 gridline."""
1605          if layout != "mid":
1606              return list(notes)
1607          out = []
1608          for nt in notes:
1609              if len(nt) &gt; 44:
1610                  need(", " in nt, f"figure 1, mid layout: the note '{nt}' is too long and has no comma to break at")
1611                  a, b_ = nt.split(", ", 1)
1612                  out += [a + ",", b_]
1613              else:
1614                  out.append(nt)
1615          return out</pre></td><td valign="top">The inner function <code>drawn</code> returns the note lines of a row. In the mid layout only, it breaks a note of more than 44 characters after its first comma. It stops the script when such a note has no comma.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1616      y = 30
1617      for b in F1_BLOCKS:
1618          b["tl"] = b["lines"] if narrow else [b["title"]]
1619          b["y"] = y
1620          b["th"] = 10 + 16 * len(b["tl"])
1621          y += b["th"] + 4
1622          for g in b["groups"]:
1623              g["y"] = y
1624              y += 22
1625              for r in g["rows"]:
1626                  r["dn"] = drawn(r["notes"])
1627                  r["h"] = 52 + 13 * len(r["dn"]) if narrow else 22 + 13 * len(r["dn"])
1628                  r["y"] = y
1629                  y += r["h"]
1630          y += 6
1631      yb = y
1632      H = yb + (64 if narrow else 50)</pre></td><td valign="top">Vertical places. No rate is used here. The loop goes through the blocks, groups and rows from top to bottom.<ul><li>It stores the <code>y</code> value of each one in its dictionary.</li><li>A block also gets the height of its title bar (<code>th</code>), and a row gets its height (<code>h</code>).</li><li>In the wide and the mid layout a row is 22 px high plus 13 px per note line.</li><li>In the narrow layout a row is 52 px high plus 13 px per note line. The row name is drawn above the dots there.</li><li><code>H</code> is the height of the whole drawing.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1633      o = [f'&lt;svg class="{dict(wide="f1w", mid="f1m", narrow="f1n")[layout]}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Dumbbell chart: whole-chip read rate of the old read kernel and of the load-only loop, one row per bwx12 process or per round of the two part A binaries, {F1_NROWS} rows"&gt;']
1634      for t in range(0, XMAX + 1, 100):
1635          o.append(f'&lt;line x1="{sx(t):.1f}" y1="24" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/&gt;')
1636          o.append(T(sx(t), 17, t, 12, MUTED, "middle", extra=TAB))
1637          o.append(T(sx(t), yb + 16, t, 12, MUTED, "middle", extra=TAB))
1638      o.append(T(sx(XMAX) + 15, 17, "GB/s", 12, MUTED))
1639      if narrow:
1640          o.append(T(W / 2, yb + 36, "Whole-chip read rate, GB/s", 12.5, MUTED, "middle"))
1641          o.append(T(W / 2, yb + 52, "The axis starts at 0.", 12.5, MUTED, "middle"))
1642      else:
1643          o.append(T((X0 + X1) / 2, yb + 38, "Whole-chip read rate, GB/s. The axis starts at 0.", 12.5, MUTED, "middle"))</pre></td><td valign="top">Starts the SVG element. Its class (<code>f1w</code>, <code>f1m</code> or <code>f1n</code>) lets the style block show the one layout that fits the window. The loop draws a vertical grid line every 100 GB/s from 0 to 500 GB/s, with the number above and below it. The last lines write the unit <code>GB/s</code> and the axis title <code>Whole-chip read rate, GB/s. The axis starts at 0.</code></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1644      for b in F1_BLOCKS:
1645          o.append(f'&lt;rect x="0" y="{b["y"]}" width="{W}" height="{b["th"]}" fill="#f1f0ec"/&gt;')
1646          for i, tl in enumerate(b["tl"]):
1647              o.append(T(8 if narrow else 12, b["y"] + 17.5 + 16 * i, tl, 13, INK, weight=600))
1648          for g in b["groups"]:
1649              o.append(T(8 if narrow else 12, g["y"] + 15, g["title"], 12, MUTED, weight=600, extra=HALO))
1650              for r in g["rows"]:
1651                  if narrow:
1652                      ty = r["y"] + 14
1653                      cy = r["y"] + r["h"] - 13
1654                      o.append(f'&lt;line x1="0" y1="{r["y"] + r["h"]}" x2="{W}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/&gt;')
1655                  else:
1656                      cy = r["y"] + r["h"] / 2
1657                      ty = cy - 6.5 * len(r["dn"]) + 4
1658                  tx = 12 if narrow else 24
1659                  o.append(T(tx, ty, r["name"], 12.5, INK, extra=HALO))
1660                  for i, nt in enumerate(r["dn"]):
1661                      o.append(T(tx, ty + 13 * (i + 1), nt, 11, MUTED, extra=HALO))</pre></td><td valign="top">Draws the grey title bar of each block, the title of each group, and the name and the note lines of each row. <code>cy</code> is the vertical place of the dots of a row. In the narrow layout the name is drawn above the dots, and a thin line is drawn under the row. No rate is used here.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1662                  xo, xn = sx(r["old"].med), sx(r["new"].med)
1663                  dt = drop_txt(r["drops"])
1664                  tipname = ", ".join([r["name"]] + r["notes"])
1665                  o.append(f'&lt;g&gt;&lt;title&gt;{esc(tipname)}: drop of the load-only loop below the old read kernel: {esc(dt)} ({esc(r["how"])}, n = {plural(len(r["drops"]), "pair")}). Source: {esc(src(r["old"].recs + r["new"].recs))}.&lt;/title&gt;'
1666                           f'&lt;line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{LINK}" stroke-width="1.5"/&gt;'
1667                           f'&lt;line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{SURF}" stroke-opacity="0" stroke-width="14"/&gt;'
1668                           + T((xo + xn) / 2, cy - 7, dt, 11 if narrow else 11.5, INK, "middle", extra=HALO + TAB) + "&lt;/g&gt;")</pre></td><td valign="top">Draws the measured values of one row.<ul><li><code>xo</code> and <code>xn</code> are the x places of the median of the old read kernel and of the median of the load-only loop.</li><li><code>dt</code> is the drop text from <code>drop_txt</code> (line 425): the lowest and the highest drop of the row with 1 decimal, or one value when both are printed equal.</li><li>Lines 1665 to 1668 draw the grey line between the two medians and write <code>dt</code> above its middle. The tooltip of the line gives the drop, how it was formed (<code>how</code>), the number of pairs and the source rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1669                  for rg, x, color, side in ((r["old"], xo, BLUE, 1), (r["new"], xn, ORANGE, -1)):
1670                      xa, xb = sx(rg.lo), sx(rg.hi)
1671                      o.append(f'&lt;g class="pt"&gt;&lt;title&gt;{esc(dot_title(tipname, rg))}&lt;/title&gt;'
1672                               f'&lt;circle cx="{x:.1f}" cy="{cy:.1f}" r="12" fill="{SURF}" fill-opacity="0"/&gt;'
1673                               + marker(x, cy, color, r["hollow"])
1674                               + f'&lt;path d="M{xa:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xb:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xa:.1f} {cy:.1f}H{xb:.1f}" stroke="{INK}" stroke-width="1.1" fill="none"/&gt;&lt;/g&gt;')
1675                      off = max(xb - x, x - xa) + 8
1676                      o.append(T(x + side * max(off, 10.5), cy + 4.2, f2(rg.med), 12, INK, "start" if side &gt; 0 else "end", extra=HALO + TAB))
1677      o.append("&lt;/svg&gt;")
1678      return "\n".join(o)
1679
1680</pre></td><td valign="top">The loop of line 1669 runs once for the old read kernel (blue, number at the right) and once for the load-only loop (orange, number at the left).<ul><li>It draws the dot at the median with <code>marker</code>, and a thin bar from the lowest to the highest interval with a short vertical line at each end.</li><li>It writes the median with 2 decimals (<code>f2</code>).</li><li>Each dot has the tooltip of <code>dot_title</code> and an invisible circle of 12 px radius around it, which also shows the tooltip.</li></ul>Lines 1677 and 1678 close the SVG element and return the drawing as one text. So figure 1 shows one median and one range per kernel and row. It shows no mean over rows and no total over rows.</td></tr>
<tr><td colspan="2"><b>Function <code>beeswarm</code>: vertical offsets of dots (figure 2)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1681  # ------------------------------------------------------------------ figure 2: every interval, two panels
1682  def beeswarm(xs, r=4.3):
1683      """Vertical offsets so that dots of one row do not cover each other."""
1684      lanes = [0, -5.5, 5.5, -11, 11]
1685      placed, out = [], [0.0] * len(xs)
1686      for i in sorted(range(len(xs)), key=lambda k: xs[k]):
1687          for ln in lanes:
1688              if all(abs(xs[i] - px) &gt;= 2 * r or ln != pl for px, pl in placed):
1689                  break
1690          placed.append((xs[i], ln))
1691          out[i] = ln
1692      return out
1693
1694</pre></td><td valign="top">Line 1681 starts the code of figure 2. <code>xs</code> holds the x places of the dots of one row.<ul><li>The function processes the dots from left to right.</li><li>Each dot gets the first of five vertical offsets (0, -5.5, 5.5, -11, 11 px) in which no dot placed before lies closer than 8.6 px in x (2 x <code>r</code>).</li><li>When no offset is free, the dot gets the last one, 11 px.</li><li>The function returns the offsets in the order of <code>xs</code>.</li><li>The offset changes only the vertical place of a dot. The rate of the dot stays on the horizontal axis.</li><li><code>panel</code> calls this function (line 1781) and stops the script when two dots lie 5.2 px or less apart (line 1786).</li></ul>The next function, <code>p_row</code>, starts at line 1695.</td></tr>
<tr><td colspan="2"><b>Function <code>p_row</code>: one row of figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1695  def p_row(name, recs, hollow, notes=(), label=None, band=None, more=()):
1696      """One row of figure 2. With band (the 8000 MT/s range of the block) the row gets a note with its place against the band.
1697      The rate is on the horizontal axis, so a higher row lies to the right of the band.
1698      A note that starts with "!" is drawn in ink colour: it is the key distance of the row.
1699      A note that starts with "~" only repeats a part of the row name: it is drawn under the short label of the figure
1700      and left out of the tooltip, which shows the full row name. "|" is a line break inside one note."""
1701      rg = Rg(recs)
1702      notes = list(notes)
1703      if band is not None:
1704          d = rg.nearest(band)
1705          notes.append("!inside the band" if band.lo &lt;= rg.lo and rg.hi &lt;= band.hi else
1706                       f"!{f2(abs(d))} GB/s {'higher|(right' if d &gt; 0 else 'lower|(left'} of the band)" if d != 0 else "!overlaps the band")
1707      notes += list(more)
1708      return dict(name=name, rg=rg, hollow=hollow, notes=notes, label=label or name)
1709
1710</pre></td><td valign="top"><ul><li><code>Rg(recs)</code> (line 192) builds the range of the records of the row. It calls <code>val</code> (line 176) for each record. It stores the lowest rate, the highest rate, the median, the number of intervals and the number of processes.</li><li><code>band</code> is the range of the 8000 MT/s rows of the block. When it is given, the row gets one note that starts with <code>!</code>. <code>rg.nearest(band)</code> (line 210) gives the distance of the nearest ends of the two ranges, from the rates before rounding.</li><li>The note is <code>inside the band</code> when the lowest and the highest rate of the row lie inside the band. It is <code>overlaps the band</code> when the two ranges share a value and the row is not inside.</li><li>In every other case the note gives the distance, rounded to 0.01 GB/s, with the words <code>higher (right of the band)</code> or <code>lower (left of the band)</code>.</li><li>Line 1707 adds the notes of <code>more</code> after the note of the band. The function returns a dictionary with the name, the range <code>rg</code>, the marker kind <code>hollow</code>, the notes and the label. Without <code>label</code> the label is the name.</li><li>Example from the page of the saved build: the row <code>Part L</code> of the old read kernel has the note <code>1.24 GB/s lower (left of the band)</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>plain_notes</code>: notes as plain text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1711  def plain_notes(notes, tooltip=False):
1712      """The notes of a row as plain text. For a tooltip the notes that only repeat the row name are left out."""
1713      return [n.lstrip("!~").replace("|", " ") for n in notes if not (tooltip and n.startswith("~"))]
1714
1715</pre></td><td valign="top">Returns the notes of a row without the marks at their start, and with a space in place of each <code>|</code> (a line break inside a note). The mark <code>!</code> means a bold note. The mark <code>~</code> means a note that only repeats a part of the row name. With <code>tooltip=True</code> the <code>~</code> notes are left out.</td></tr>
<tr><td colspan="2"><b>Function <code>note_lines</code>: drawn lines of the notes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1716  def note_lines(notes):
1717      """(text, strong) for every drawn line of the notes of a row."""
1718      return [(seg, n.startswith("!")) for n in notes for seg in n.lstrip("!~").split("|")]
1719
1720</pre></td><td valign="top">Splits each note at <code>|</code> into the lines that the figure draws. Each line carries a flag. The flag is true when the note starts with <code>!</code>. <code>panel</code> then draws the line in bold type (line 1837).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1721  F2_GAPS = []         # per panel of figure 2: (title, number of dots, smallest distance of two dots in px, hover areas cut by a neighbour, areas of all hover areas in px2)
1722  HIT_R = 12.0         # radius of the hover area of a free-standing dot: 24 px across
1723
1724</pre></td><td valign="top"><code>F2_GAPS</code> collects one entry per panel of figure 2. The page check in lines 2812 to 2817 reads it. <code>HIT_R</code> is the radius of the hover area of a dot that has no other dot within 24 px: 12 px (pixels, the unit of length on the screen).</td></tr>
<tr><td colspan="2"><b>Function <code>hit_cell</code>: hover area of one dot</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1725  def hit_cell(i, pts, nseg=32):
1726      """The hover area of dot i: the part of a circle of radius HIT_R around the dot that is nearer to it than to any other dot.
1727      The circle is a polygon of nseg corners. The half-way line to every dot within 2 x HIT_R cuts it (a Voronoi cell, clipped to the circle).
1728      So the areas of two dots never overlap, and the pointer only has to be nearest to a dot. Returns (corners, cut by a neighbour)."""
1729      x0, y0 = pts[i]
1730      poly = [(x0 + HIT_R * math.cos(2 * math.pi * k / nseg), y0 + HIT_R * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]
1731      cut = False
1732      for j, (x1, y1) in enumerate(pts):
1733          dx, dy = x1 - x0, y1 - y0
1734          if j == i or dx * dx + dy * dy &gt;= (2 * HIT_R) ** 2:
1735              continue
1736          mx, my = (x0 + x1) / 2, (y0 + y1) / 2
1737          side = [(px - mx) * dx + (py - my) * dy for px, py in poly]          # above 0: nearer to the other dot
1738          out = []
1739          for k, a in enumerate(poly):
1740              b, sa, sb = poly[(k + 1) % len(poly)], side[k], side[(k + 1) % len(poly)]
1741              if sa &lt;= 0:
1742                  out.append(a)
1743              if (sa &lt; 0 &lt; sb) or (sb &lt; 0 &lt; sa):
1744                  t = sa / (sa - sb)
1745                  out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
1746          cut = cut or len(out) != len(poly) or any(v &gt; 0 for v in side)
1747          poly = out
1748          need(len(poly) &gt;= 3, "figure 2: a hover area is empty")
1749      return poly, cut
1750
1751</pre></td><td valign="top"><ul><li>Layout code. It reads no rate.</li><li>It starts with a circle of radius <code>HIT_R</code> around dot <code>i</code>, as a polygon with 32 corners.</li><li>For every other dot that is less than 24 px away, it cuts the polygon at the line half-way between the two dots. So the hover areas of two dots never overlap.</li><li>The script stops when a hover area has fewer than 3 corners.</li><li>It returns the corners, and a flag that is true when a neighbour cut the circle.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>poly_area</code>: area of a polygon</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1752  def poly_area(poly):
1753      return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2
1754
1755</pre></td><td valign="top">Returns the area of a polygon from the coordinates of its corners, in square pixels. Line 1788 calls it for each hover area.</td></tr>
<tr><td colspan="2"><b>Function <code>panel</code>: draws one panel of figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1756  def panel(title, sub, lo, hi, majors, minors, blocks, color, aria):
1757      W, X0, X1 = 466, 190, 450
1758      sx = lambda v: X0 + (X1 - X0) * (float(v) - lo) / (hi - lo)</pre></td><td valign="top"><ul><li><code>build</code> calls it twice (lines 2695 and 2698): for the panel <code>Old read kernel</code> with <code>P_OLD_BLOCKS</code>, and for the panel <code>Load-only loop</code> with <code>P_NEW_BLOCKS</code>.</li><li><code>lo</code> and <code>hi</code> are the axis limits in GB/s. <code>sx</code> converts a rate to a horizontal position with a linear scale: the rate <code>lo</code> lies at 190 px and the rate <code>hi</code> at 450 px.</li><li><code>sx</code> converts the rate to a floating-point number. Only the drawing uses this copy.</li><li><code>color</code> is the colour of the dots of the panel. <code>build</code> passes <code>BLUE</code> for the old read kernel and <code>ORANGE</code> for the load-only loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1759      y = 98
1760      for b in blocks:
1761          b["y"] = y
1762          y += 22 + 13 * len(b["band_txt"])
1763          for g in b["groups"]:
1764              g["y"] = y
1765              y += 20 + 12 * len(g.get("sub", ()))
1766              for r in g["rows"]:
1767                  r["h"] = max(30, 8 + 13 * (2 + len(note_lines(r["notes"]))))
1768                  r["y"] = y
1769                  y += r["h"]
1770          b["yend"] = y
1771          y += 8
1772      yb = y
1773      H = yb + 56</pre></td><td valign="top">Vertical layout. Each block, group and row gets its position <code>y</code>, and each row gets its height <code>h</code>. The height of a row grows by 13 px per note line. No rate is read here.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1774      # Place every dot first. Then give each dot its hover area: the part of a 12 px circle that is nearer to it than to any other dot.
1775      # So the hover areas do not overlap, and the pointer only has to be nearest to a dot (a free-standing dot has a target of 24 px).
1776      placed = []
1777      for b in blocks:
1778          for g in b["groups"]:
1779              for r in g["rows"]:
1780                  xs = [sx(v) for v in r["rg"].v]
1781                  r["dots"] = [(rec, x, r["y"] + r["h"] / 2 + dy, len(placed) + i) for i, (rec, x, dy) in enumerate(zip(r["rg"].recs, xs, beeswarm(xs)))]
1782                  placed += [(x, y_) for _, x, y_, _ in r["dots"]]
1783      gap = [min(((x - a) ** 2 + (y_ - c) ** 2) ** 0.5 for j, (a, c) in enumerate(placed) if j != i) for i, (x, y_) in enumerate(placed)]
1784      # 5.2 px is the outer radius of the largest mark while the pointer is on it (hollow mark: r 3.4 plus half of the 3.6 px hover stroke).
1785      # A filled mark has r 4.3, a surface ring up to r 4.9 under it, and a hover stroke up to r 5.1.
1786      need(min(gap) &gt; 5.2, f"figure 2, panel '{title}': two dots are {min(gap):.2f} px apart, so one mark covers the centre of the other")
1787      cells = [hit_cell(i, placed) for i in range(len(placed))]
1788      F2_GAPS.append((title, len(placed), min(gap), sum(1 for _, cut in cells if cut), [poly_area(c) for c, _ in cells]))</pre></td><td valign="top"><ul><li>One dot per interval record. <code>r["rg"].v</code> holds the rates of the records of the row, as <code>val</code> returned them. They stand in the order of <code>r["rg"].recs</code>: by launch time, then by interval number (line 197).</li><li>The horizontal position of a dot is <code>sx</code> of its rate before rounding. <code>beeswarm</code> (line 1682) gives each dot a vertical offset. So dots of one row with near x values do not cover each other.</li><li>Each entry of <code>r["dots"]</code> holds the record, x, y and the index of the dot in the panel.</li><li><code>gap</code> is the distance of each dot to the nearest other dot of the panel. The script stops when the smallest distance is 5.2 px or less. 5.2 px is the outer radius of the largest mark while the pointer is on it.</li><li><code>hit_cell</code> builds the hover area of each dot.</li><li><code>F2_GAPS</code> gets one entry for this panel: the title, the number of dots, the smallest distance, the number of hover areas that a neighbour cut, and the areas of all hover areas.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1789      o = [f'&lt;svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(aria)}"&gt;']
1790      o.append(T(10, 18, title, 13.5, INK, weight=600))
1791      o.append(T(10, 33, sub, 11.5, MUTED))
1792      o.append(T(10, 48, "x axis: whole-chip read rate, GB/s.", 11.5, MUTED))
1793      o.append(T(10, 62, f"The axis starts at {lo} GB/s, not at 0.", 11.5, INK, weight=600))
1794      o.append(T(10, 77, "under a row name: lowest to", 10.5, MUTED))
1795      o.append(T(10, 89, "highest, GB/s (n intervals)", 10.5, MUTED))</pre></td><td valign="top">Starts the SVG text of the panel. It writes the head lines: the title, the sub-title, the unit of the x axis, and the sentence that the axis starts at <code>lo</code> GB/s and not at 0. Lines 1794 and 1795 explain the text under a row name: lowest to highest rate in GB/s, and the number of intervals.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1796      # The grey bands come first, and the grid lines are drawn over them. The grid colour is close to the band colour,
1797      # so each grid line is drawn again inside a band in a darker tone. A dot inside a band can then be read against a line.
1798      boxes = []
1799      for b in blocks:
1800          on = [g for g in b["groups"] if g.get("band")]
1801          if b.get("band") and on:
1802              y0, y1 = on[0]["y"] + 2, on[-1]["rows"][-1]["y"] + on[-1]["rows"][-1]["h"]
1803              xa, xb = sx(b["band"].lo), sx(b["band"].hi)
1804              boxes.append((xa, xb, y0, y1))
1805              o.append(f'&lt;g&gt;&lt;title&gt;{esc(b["band_title"])}&lt;/title&gt;&lt;rect x="{xa:.1f}" y="{y0}" width="{xb - xa:.1f}" height="{y1 - y0}" fill="{BAND}"/&gt;'
1806                       f'&lt;path d="M{xa:.1f} {y0}V{y1}M{xb:.1f} {y0}V{y1}" stroke="{BAND_EDGE}"/&gt;&lt;/g&gt;')
1807      for t in minors:
1808          o.append(f'&lt;line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}" stroke-opacity="0.55"/&gt;')
1809      for t in majors:
1810          o.append(f'&lt;line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/&gt;')
1811          o.append(T(sx(t), 88, t, 11.5, MUTED, "middle", extra=TAB))
1812          o.append(T(sx(t), yb + 16, t, 11.5, MUTED, "middle", extra=TAB))
1813      for xa, xb, y0, y1 in boxes:
1814          for t in sorted(set(minors) | set(majors)):
1815              if xa + 3 &lt; sx(t) &lt; xb - 3:                 # a line within 3 px of a band edge would look like a second edge
1816                  o.append(f'&lt;line x1="{sx(t):.1f}" y1="{y0}" x2="{sx(t):.1f}" y2="{y1}" stroke="{BAND_EDGE}" stroke-opacity="{0.6 if t in majors else 0.32}" pointer-events="none"/&gt;')
1817      # axis line with a break mark: the axis does not start at 0
1818      o.append(f'&lt;path d="M{X0 - 14} {yb}h5l3 -5l4 10l3 -5H{X1}" stroke="{MUTED}" fill="none"/&gt;')
1819      o.append(T((X0 + X1) / 2 - 20, yb + 34, "Whole-chip read rate, GB/s", 12, MUTED, "middle"))
1820      o.append(T((X0 + X1) / 2 - 20, yb + 49, f"The axis starts at {lo} GB/s, not at 0.", 12, INK, "middle", weight=600))</pre></td><td valign="top"><ul><li>Lines 1798 to 1806 draw the grey band of each block that has one. Horizontally the band runs from <code>sx(b["band"].lo)</code> to <code>sx(b["band"].hi)</code>: the lowest and the highest rate of the 8000 MT/s rows of the block. Vertically it covers the groups whose <code>band</code> flag is true.</li><li>The tooltip of the band is the text <code>band_title</code> of the block.</li><li>Lines 1807 to 1816 draw the grid lines at the rates <code>minors</code> and <code>majors</code>, and the numbers of the major lines above and below the rows. Inside a band each grid line is drawn again in a darker tone. A grid line within 3 px of a band edge is not drawn again (line 1815).</li><li>Lines 1817 to 1820 draw the axis line with a break mark, the axis title, and again the sentence that the axis does not start at 0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1821      for b in blocks:
1822          o.append(f'&lt;rect x="0" y="{b["y"]}" width="{W}" height="{18 + 13 * len(b["band_txt"])}" fill="#f1f0ec"/&gt;')
1823          o.append(T(10, b["y"] + 15, b["title"], 12.5, INK, weight=600))
1824          for i, bt in enumerate(b["band_txt"]):
1825              o.append(T(10, b["y"] + 29 + 13 * i, bt, 10.5, MUTED))
1826          for g in b["groups"]:
1827              o.append(T(10, g["y"] + 14, g["title"], 11.5, MUTED, weight=600, extra=HALO))
1828              for i, st in enumerate(g.get("sub", ())):
1829                  o.append(T(10, g["y"] + 26 + 12 * i, st, 10.5, MUTED))
1830              for r in g["rows"]:
1831                  cy = r["y"] + r["h"] / 2
1832                  nl = 2 + len(note_lines(r["notes"]))
1833                  ty = cy - 6.5 * (nl - 1) + 4
1834                  o.append(T(18, ty, r["label"], 12, INK))
1835                  o.append(T(18, ty + 13, f"{r['rg'].txt()} ({r['rg'].n})", 10.5, MUTED, extra=TAB))
1836                  for i, (nt, strong) in enumerate(note_lines(r["notes"])):
1837                      o.append(T(18, ty + 13 * (i + 2), nt, 10.5, INK if strong else MUTED, weight=600 if strong else None))
1838                  o.append(f'&lt;line x1="{X0}" y1="{r["y"] + r["h"]}" x2="{X1}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/&gt;')</pre></td><td valign="top"><ul><li>Writes the title bar of each block with its <code>band_txt</code> lines, the title of each group with its <code>sub</code> lines, and the label of each row.</li><li>Under the label it writes <code>r['rg'].txt()</code>, and after it <code>r['rg'].n</code> in round brackets: the lowest and the highest rate of the row with 2 decimals, and the number of intervals. Example from the page of the saved build: <code>461.61 to 464.29 (6)</code> for part L of the old read kernel.</li><li>Then it writes the note lines. A line of a <code>!</code> note is drawn in the colour <code>INK</code> and in bold type. Every other line is drawn in the colour <code>MUTED</code>.</li><li>Line 1838 draws a thin line under the row.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1839                  for rec, x, yd, di in r["dots"]:
1840                      cell = "M" + "L".join(f"{cx_:.1f} {cy_:.1f}" for cx_, cy_ in cells[di][0]) + "Z"
1841                      kb = rec["kernel_before"]
1842                      if rec["part"] == "A" and rec["dataset"] == "A-3":
1843                          # row A-3 has no rounds: the number at the end of the tag counts the three repeats of the process
1844                          where = f"process {rec['_fproc']} of the file (tag {rec['tag']}), interval {rec['interval'] + 1}"
1845                      elif rec["part"] == "A":
1846                          where = f"process {rec['_fproc']} of the file, round {rec['round']}, interval {rec['interval'] + 1}"
1847                      else:
1848                          after = ("no kernel ran before it" if kb.startswith("none") else
1849                                   f"directly after {kb}" + ("" if kb in ("oldread", "read", "asmread") else " (another test loop of bwx12)"))
1850                          where = f"process {rec['tag']}, round {rec['round']}, position {rec['pos']}, {after}"</pre></td><td valign="top"><ul><li>Loop over the dots of the row. <code>cell</code> is the SVG path of the hover area of the dot.</li><li><code>where</code> names the interval of the dot for the tooltip.</li><li>Part A, row A-3: the number of the process inside its csv file (<code>_fproc</code>, set in line 349), the tag, and the interval number counted from 1.</li><li>Part A, every other row: the number of the process inside its csv file, the round, and the interval number counted from 1.</li><li>bwx12: the tag of the process, the round, the position, and the kernel that was timed directly before (<code>kernel_before</code>). When no kernel ran before, the text is <code>no kernel ran before it</code>. A kernel before that is not oldread, read or asmread gets the words <code>another test loop of bwx12</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1851                      tipname = ", ".join([r["name"]] + plain_notes(r["notes"], tooltip=True))
1852                      tip = (f"{tipname}: {kernel_name([rec])}, {where}: {f2(val(rec))} GB/s. "
1853                             f"Row: {r['rg'].txt()} GB/s, n = {plural(r['rg'].n, 'interval')} / {plural(r['rg'].np, 'process')}. "
1854                             f"Source: {src([rec])}.")</pre></td><td valign="top"><ul><li><code>tip</code> is the tooltip text of the dot. It starts with the row name and the notes of the row (<code>plain_notes</code>, without the <code>~</code> notes), the kernel name and <code>where</code>.</li><li>Then comes the rate of the interval: <code>f2(val(rec))</code>, the value of <code>val</code> rounded to 0.01 GB/s.</li><li>Then come the range of the row, n as intervals and processes, and the source text of <code>src</code> (line 359): the csv file and the line of the interval row. For a bwx12 record the source text ends with the sentence that the rate is the sum of the 120 thread rows after that row.</li><li>Example from the page of the saved build: <code>Part C, read directly after oldread: read (new read kernel), process T72C1, round 0, position 1, directly after oldread: 320.90 GB/s.</code></li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1855                      # Both kinds of mark are 8.6 px across: the hollow one with its stroke, the filled one without a stroke on its edge.
1856                      # The filled mark has a surface-coloured ring of 0.6 px under it (r 4.9), which separates it from a dot that it overlaps.
1857                      # Only the hover area takes the pointer, not the painted mark. So where two marks overlap, the nearer dot still answers.
1858                      o.append(f'&lt;g class="pt"&gt;&lt;title&gt;{esc(tip)}&lt;/title&gt;&lt;path d="{cell}" fill="{SURF}" fill-opacity="0"/&gt;&lt;g pointer-events="none"&gt;'
1859                               + (f'&lt;circle class="mk ho" cx="{x:.1f}" cy="{yd:.1f}" r="3.4" fill="{SURF}" stroke="{color}" stroke-width="1.8"/&gt;' if r["hollow"]
1860                                  else f'&lt;circle cx="{x:.1f}" cy="{yd:.1f}" r="4.9" fill="{SURF}"/&gt;&lt;circle class="mk fi" cx="{x:.1f}" cy="{yd:.1f}" r="4.3" fill="{color}"/&gt;') + "&lt;/g&gt;&lt;/g&gt;")
1861      o.append("&lt;/svg&gt;")
1862      return "\n".join(o)
1863
1864</pre></td><td valign="top"><ul><li>Writes the dot: first the invisible hover area with the tooltip, then the painted mark.</li><li>A row with <code>hollow</code> true (an 8000 MT/s row) gets a ring of radius 3.4 px in the panel colour.</li><li>Every other row (a 7200 MT/s row) gets a filled circle of radius 4.3 px in the same colour.</li><li>Lines 1861 and 1862 close the SVG text and return it.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>secs_txt</code>: interval length as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1865  def secs_txt(recs):
1866      return f"{int(recs[0]['min_ms']) // 1000} s"
1867
1868</pre></td><td valign="top">Returns the interval length of the first record of a list as text, for example <code>6 s</code>. It reads the field <code>min_ms</code> (the shortest length of one interval, in ms) and keeps the whole seconds.</td></tr>
<tr><td colspan="2"><b>Function <code>l_rows</code>: rows L-1 to L-4 of figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1869  def l_rows(pool):
1870      rows = []
1871      for d in LPOOL:
1872          rows.append(p_row(d, pool[d], True, label=f"{d} ({secs_txt(pool[d])})"))
1873      return rows
1874
1875</pre></td><td valign="top"><ul><li><code>pool</code> is <code>B_L_OLD</code> or <code>B_L_ASM</code> (lines 291 and 292). For each row L-1 to L-4 it holds the oldread records at position 0, or the asmread records at position 1.</li><li>Each of the four becomes one <code>p_row</code> with hollow markers. The label is the row name with the interval length, for example <code>L-1 (6 s)</code>.</li><li>No band is passed. So these rows get no note.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>band_title</code>: tooltip text of a grey band</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1876  def band_title(what, rg, n):
1877      files = ", ".join(sorted({f"{r['folder']}/{r['file']}" for r in rg.recs}))
1878      return f"Grey band: {what}. {rg.txt()} GB/s, n = {n}. Source: {files}."
1879
1880</pre></td><td valign="top">Returns the tooltip text of a grey band: what the band shows, its range <code>rg.txt()</code> in GB/s, n, and the sorted names of the csv files of its records.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1881  F72_NOTES = ["earlier run of the same boot,|not part of the rerun"]      # "|" = line break inside one note
1882  IN_PLACE_2 = ["asmread in place of", "the new read kernel"]              # group label in two lines: it stays inside the label column
1883  need(" ".join(IN_PLACE_2) == IN_PLACE, "figure 2: the group label is not the label of figure 1")
1884  need({(r["round"], r["pos"], r["file"]) for r in C_ASM_AO} == {(1, 0, "crev.csv")}, "part C, asmread after oldread: not crev, round 1, position 0")
1885  CI_NOTES = ["added after the first|numbers were seen"]</pre></td><td valign="top"><ul><li><code>F72_NOTES</code> and <code>CI_NOTES</code> are the fixed notes of the rows F72d12 and control I.</li><li><code>IN_PLACE_2</code> is a group label in two lines. The script stops unless it equals the label <code>IN_PLACE</code> of figure 1 (line 1561).</li><li>Line 1884 stops the script unless both records of <code>C_ASM_AO</code> (part C, asmread directly after oldread) come from <code>crev.csv</code>, round 1, position 0. The order crev times asmread, read, oldread. So asmread at position 0 of round 1 follows oldread at position 2 of round 0.</li></ul></td></tr>
<tr><td colspan="2"><b><code>P_OLD_BLOCKS</code>: blocks of the panel Old read kernel</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1886  P_OLD_BLOCKS = [
1887      dict(title="0.5 s measurements, bw_old read", band=rPA_old,
1888           band_txt=["grey band = 8000 MT/s rows A-1 to A-3:", f"{rPA_old.txt()} GB/s, n = {n8000(P_A_OLD)}"],
1889           band_title=band_title("lowest to highest interval of the 8000 MT/s rows A-1 to A-3, bw_old read", rPA_old, n8000(P_A_OLD)),
1890           groups=[dict(title="8000 MT/s", band=True, rows=[p_row(d, B_A_OLD[d], True) for d in APOOL]),
1891                   dict(title="7200 MT/s, part A", band=True, rows=[p_row(f"Part A, session {s_}", [r for r in A_OLD if r["session"] == s_], False, label=f"Session {s_} (T72A{s_})", band=rPA_old)
1892                                                                    for s_ in (1, 2, 3)])]),</pre></td><td valign="top"><ul><li>First block of the list: the 0.5 s measurements of part A, binary bw_old, kernel <code>read</code>.</li><li>Grey band: <code>rPA_old</code> (line 463), the range of the 21 intervals of the rows A-1 to A-3 (<code>P_A_OLD</code>, line 304).</li><li>Group <code>8000 MT/s</code>: one row for each of A-1, A-2 and A-3 with the records <code>B_A_OLD[d]</code> (line 298). Hollow markers, no note.</li><li>Group <code>7200 MT/s, part A</code>: one row per session with the records of <code>A_OLD</code> of that session. A session has 6 such intervals from 2 processes (round 1 and round 2). Each row is compared with the band.</li><li><code>n8000</code> (line 401) writes n of the band as intervals / processes / 1 boot.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1893      dict(title="6 s measurements, bwx12 oldread", band=rPL_old,
1894           band_txt=["grey band = 8000 MT/s rows L-1 to L-4:", f"{rPL_old.txt()} GB/s, n = {n8000(P_L_OLD)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],
1895           band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, oldread at position 0", rPL_old, n8000(P_L_OLD)),
1896           groups=[dict(title="8000 MT/s", band=True, rows=l_rows(B_L_OLD)),
1897                   dict(title="7200 MT/s", band=True, rows=[
1898                       p_row("F72d12", F_OLD, False, F72_NOTES, band=rPL_old),
1899                       p_row("Part L", L_OLD, False, label="Part L (3 sessions)", band=rPL_old, more=[f"!medians: {f2(abs(L_OLD_MED))} GB/s lower"]),
1900                       p_row("Part C", C_OLD, False, label="Part C (4 processes)", band=rPL_old),
1901                       p_row("Control I", I_OLD, False, CI_NOTES, band=rPL_old)])]),
1902  ]
1903
1904</pre></td><td valign="top"><ul><li>Second block: the 6 s measurements of bwx12, kernel <code>oldread</code>. Line 1894 states that the rows L-2 to L-4 are 4 s measurements.</li><li>Grey band: <code>rPL_old</code> (line 466), the range of the 11 oldread intervals at position 0 of the rows L-1 to L-4 (<code>P_L_OLD</code>, line 296).</li><li>Group <code>8000 MT/s</code>: <code>l_rows(B_L_OLD)</code>.</li><li>Group <code>7200 MT/s</code>: four rows, each compared with the band. They are F72d12 (<code>F_OLD</code>, 2 intervals), part L (<code>L_OLD</code>, 6 intervals), part C (<code>C_OLD</code>, all 8 oldread intervals, at position 0 and at position 2) and control I (<code>I_OLD</code>, 4 intervals).</li><li>The row of part L gets a second bold note: the difference of the two medians <code>L_OLD_MED</code> (line 490), without its sign, rounded to 0.01 GB/s.</li><li>In the page of the saved build, part L has the notes <code>1.24 GB/s lower (left of the band)</code> and <code>medians: 6.27 GB/s lower</code>. The saved output holds both values. It prints the first one with its sign, as -1.24 GB/s [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>a_new_block</code>: block of bw_new read, one round</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1905  def a_new_block(rnd):
1906      v = A_V3[rnd]
1907      rows8 = [p_row(f"{d}, round {rnd}", [r for r in B_A_NEW[d] if r["round"] == rnd], True, label=d) for d in ("A-1", "A-2")]
1908      rows7 = []
1909      for s_ in (1, 2, 3):
1910          rows7.append(p_row(f"Part A, session {s_}, round {rnd}", [r for r in A_NEW if r["session"] == s_ and r["round"] == rnd], False,
1911                             [] if s_ == 1 else ["used for Q1 only (rule V3)"], label=f"Session {s_} (T72A{s_})", band=v["r8"] if s_ == 1 else None))
1912      return dict(title=f"0.5 s measurements, bw_new read, round {rnd}", band=v["r8"],
1913                  band_txt=[f"grey band = 8000 MT/s rows A-1 and A-2 of round {rnd}:", f"{v['r8'].txt()} GB/s, n = {n8000(v['r8'].recs)}"],
1914                  band_title=band_title(f"lowest to highest interval of the 8000 MT/s rows A-1 and A-2, bw_new read, round {rnd}", v["r8"], n8000(v["r8"].recs)),
1915                  groups=[dict(title="8000 MT/s", band=True, rows=rows8), dict(title="7200 MT/s, part A", band=True, rows=rows7)])
1916
1917</pre></td><td valign="top"><ul><li><code>A_V3[rnd]</code> (lines 509 to 516) holds two ranges of bw_new <code>read</code> for the round. <code>r7</code> is the range of the 3 intervals of session 1 at 7200 MT/s. <code>r8</code> is the range of the 6 intervals of the rows A-1 and A-2 at 8000 MT/s.</li><li>The grey band of the block is <code>r8</code>.</li><li><code>rows8</code>: one row for A-1 and one for A-2, each with the 3 intervals of that round (1 process). Hollow markers.</li><li><code>rows7</code>: one row per session with the 3 intervals of <code>A_NEW</code> of that session and round.</li><li>Only the row of session 1 gets <code>band</code>. So only session 1 is compared with the band. The rows of sessions 2 and 3 get the note <code>used for Q1 only (rule V3)</code>.</li><li>The reading note <code>how2</code> of the page states how the sessions differ (line 2689). By this note, sessions 2 and 3 started 5 s after a 120-thread process of part C. Session 1 and the rows A-1 and A-2 did not. Line 2486 stops the script unless the part A steps of sessions 2 and 3 started 5 s after a part C process.</li></ul></td></tr>
<tr><td colspan="2"><b><code>P_NEW_BLOCKS</code>: blocks of the panel Load-only loop</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1918  P_NEW_BLOCKS = [
1919      dict(title="6 s measurements, bwx12", band=rPL_asm,
1920           band_txt=["grey band = 8000 MT/s rows L-1 to L-4, asmread:", f"{rPL_asm.txt()} GB/s, n = {n8000(P_L_ASM)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],
1921           band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, asmread at position 1, directly after oldread", rPL_asm, n8000(P_L_ASM)),
1922           groups=[dict(title="8000 MT/s", sub=IN_PLACE_2, band=True, rows=l_rows(B_L_ASM)),
1923                   dict(title="7200 MT/s", sub=IN_PLACE_2, band=True, rows=[
1924                       p_row("F72d12", F_ASM, False, F72_NOTES, band=rPL_asm),
1925                       p_row("Part L", L_ASM, False, label="Part L (3 sessions)", band=rPL_asm),
1926                       p_row("Part C, asmread directly after oldread (crev, round 1, position 0)", C_ASM_AO, False, ["~asmread after oldread"], label="Part C (crev, round 1)", band=rPL_asm),
1927                       p_row("Control I", I_ASM, False, CI_NOTES, band=rPL_asm)]),
1928                   dict(title="7200 MT/s, part C", sub=["no 8000 MT/s row of", "this kind (no band)"], band=False, rows=[
1929                       p_row("Part C, read directly after oldread", C_READ_AO, False, ["~new read kernel,|after oldread"], label="Part C, read"),
1930                       p_row("Part C, read directly after asmread", C_READ_AA, False, ["~new read kernel,|after asmread"], label="Part C, read"),
1931                       p_row("Part C, asmread directly after read", C_ASM_AR, False, ["~after read"], label="Part C, asmread"),
1932                       p_row("Part C, asmread as first interval of the process", C_ASM_FI, False, ["~first interval of the process"], label="Part C, asmread")])]),
1933      a_new_block(1), a_new_block(2),
1934  ]</pre></td><td valign="top"><ul><li>First block: the 6 s measurements of bwx12. Line 1920 states that the rows L-2 to L-4 are 4 s measurements. Grey band: <code>rPL_asm</code> (line 466), the range of the 11 asmread intervals at position 1 of the rows L-1 to L-4 (<code>P_L_ASM</code>, line 297).</li><li>Group <code>8000 MT/s</code>: <code>l_rows(B_L_ASM)</code>.</li><li>Group <code>7200 MT/s</code>, asmread in place of the new read kernel, each row compared with the band: F72d12 (<code>F_ASM</code>, 2 intervals), part L (<code>L_ASM</code>, 6 intervals), part C asmread directly after oldread (<code>C_ASM_AO</code>, 2 intervals) and control I (<code>I_ASM</code>, 4 intervals).</li><li>Group <code>7200 MT/s, part C</code> with <code>band=False</code>: four rows without a comparison. Two hold the bwx12 kernel <code>read</code> (the new read kernel): directly after oldread (<code>C_READ_AO</code>, 4 intervals) and directly after asmread (<code>C_READ_AA</code>, 4 intervals). Two hold asmread: directly after read (<code>C_ASM_AR</code>, 4 intervals) and as the first interval of a process (<code>C_ASM_FI</code>, 2 intervals).</li><li>The label of this group gives the reason: <code>no 8000 MT/s row of this kind (no band)</code>.</li><li>Line 1933 adds the two blocks of <code>a_new_block</code>, for round 1 and for round 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1935  P_OLD_BLOCKS.reverse()
1936
1937</pre></td><td valign="top">Reverses the order of the two blocks of <code>P_OLD_BLOCKS</code>. The 6 s block of bwx12 then comes first in both panels.</td></tr>
<tr><td colspan="2"><b>Function <code>panel_rows</code>: the rows of a panel as a list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1938  def panel_rows(blocks, band_only=True):
1939      return [(b, g, r) for b in blocks for g in b["groups"] for r in g["rows"] if g["band"] or not band_only]
1940
1941</pre></td><td valign="top">Returns one entry (block, group, row) per row of a block list. By default it leaves out the rows of a group whose <code>band</code> flag is false. With <code>band_only=False</code> it returns every row.</td></tr>
<tr><td colspan="2"><b>Assertions for the caption of figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1942  # facts that the takeaway line of figure 2 states: checked here, so the sentence cannot go stale
1943  OLD_7200_BELOW = [r["name"] for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"] and not r["rg"].overlaps(b["band"])]
1944  need(OLD_7200_BELOW == ["Part L"], f"figure 2, old read: the rows outside the band are {OLD_7200_BELOW}")
1945  # every 7200 MT/s row of the panel "Old read kernel" is compared with its band: each one carries the bold text with its place
1946  OLD_CMP = [r for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"]]
1947  need(len(OLD_CMP) == 7 and all(any(n.startswith("!") for n in r["notes"]) for r in OLD_CMP), "figure 2, old read: a 7200 MT/s row has no bold text with its place relative to the band")</pre></td><td valign="top"><ul><li><code>OLD_7200_BELOW</code>: the names of the 7200 MT/s rows (not hollow) of the panel <code>Old read kernel</code> whose range does not overlap the band of their block (<code>overlaps</code>, line 207). The script stops unless this list holds only <code>Part L</code>.</li><li><code>OLD_CMP</code>: all 7200 MT/s rows of that panel. The script stops unless there are 7 rows and each one has a <code>!</code> note with its place relative to the band.</li><li>The 7 rows are the 3 sessions of part A, F72d12, part L, part C and control I.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1948  NEW_CMP = [(b, r) for b, g, r in panel_rows(P_NEW_BLOCKS) if not r["hollow"] and any(n.startswith("!") for n in r["notes"])]   # rows that are compared with a band
1949  NEW_7200_IN = [r["name"] for b, r in NEW_CMP if r["rg"].overlaps(b["band"])]
1950  NEW_7200_RIGHT = [r["name"] for b, r in NEW_CMP if r["rg"].lo &gt; b["band"].hi]
1951  need(NEW_7200_IN == ["F72d12"] and len(NEW_7200_RIGHT) == 5 and len(NEW_CMP) == 6, f"figure 2, load-only: compared rows inside the band {NEW_7200_IN}, right of it {len(NEW_7200_RIGHT)}")
1952  need(sorted(NEW_7200_RIGHT) == sorted(["Part L", "Part C, asmread directly after oldread (crev, round 1, position 0)", "Control I", "Part A, session 1, round 1", "Part A, session 1, round 2"]),
1953       f"figure 2, load-only: the rows right of their band are not the five rows that the caption names: {NEW_7200_RIGHT}")
1954  F2_RIGHT_TXT = ("The rows to the right of their band are part L, the part C row &amp;quot;asmread after oldread&amp;quot;, session 1 of part A in both rounds, "
1955                  "and control I (added after the first numbers were seen).")</pre></td><td valign="top"><ul><li><code>NEW_CMP</code>: the 7200 MT/s rows of the panel <code>Load-only loop</code> that have a <code>!</code> note. These are the rows that are compared with a band.</li><li><code>NEW_7200_IN</code>: the rows of <code>NEW_CMP</code> whose range overlaps the band. <code>NEW_7200_RIGHT</code>: the rows whose lowest rate is above the highest rate of the band.</li><li>The script stops unless <code>NEW_CMP</code> has 6 rows, only F72d12 overlaps its band, and 5 rows lie above their band.</li><li>Line 1952 stops the script unless these 5 rows are part L, part C asmread directly after oldread, control I, and session 1 of part A in round 1 and in round 2.</li><li><code>F2_RIGHT_TXT</code> is the caption sentence that names these 5 rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1956  allv_old = [v for b, g, r in panel_rows(P_OLD_BLOCKS, False) for v in r["rg"].v]
1957  allv_new = [v for b, g, r in panel_rows(P_NEW_BLOCKS, False) for v in r["rg"].v]
1958  OLD_AX, NEW_AX = (458, 476), (276, 340)
1959  need(OLD_AX[0] &lt; min(allv_old) and max(allv_old) &lt; OLD_AX[1] and NEW_AX[0] &lt; min(allv_new) and max(allv_new) &lt; NEW_AX[1], "figure 2: a value lies outside an axis")
1960  N_DOTS = len(allv_old) + len(allv_new)
1961
1962</pre></td><td valign="top"><ul><li><code>allv_old</code> and <code>allv_new</code>: the rates of all rows of each panel. The part C rows without a band are included.</li><li><code>OLD_AX</code> and <code>NEW_AX</code> are the axis limits of the two panels: 458 to 476 GB/s and 276 to 340 GB/s. The script stops unless every rate lies between the limits of its panel.</li><li><code>N_DOTS</code> is the number of dots of figure 2: the number of rates of both panels. The saved build gave 139 dots, and <code>USED</code> holds 139 records [Ref5]. A test for this companion confirmed that each record of <code>USED</code> is exactly one dot.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>legend</code>: HTML of a figure legend</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1963  def legend(items):
1964      return '&lt;div class="legend"&gt;' + "".join(f'&lt;span class="li"&gt;{sw}&lt;span&gt;{txt}&lt;/span&gt;&lt;/span&gt;' for sw, txt in items) + "&lt;/div&gt;"
1965
1966</pre></td><td valign="top">Returns the HTML of a legend from a list of entries. Each entry is a symbol and a text.</td></tr>
<tr><td colspan="2"><b>Function <code>sw_dot</code>: dot symbol of a legend</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1967  def sw_dot(color, hollow=False):
1968      c = (f'&lt;circle cx="8" cy="8" r="4.6" fill="{SURF}" stroke="{color}" stroke-width="2.2"/&gt;' if hollow else f'&lt;circle cx="8" cy="8" r="5.5" fill="{color}"/&gt;')
1969      return f'&lt;svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"&gt;{c}&lt;/svg&gt;'
1970
1971</pre></td><td valign="top">Returns a small SVG dot for a legend entry: a ring when <code>hollow</code> is true, else a filled circle.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1972  SW_WHISK = f'&lt;svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"&gt;&lt;path d="M3 4.5V11.5M19 4.5V11.5M3 8H19" stroke="{INK}" stroke-width="1.1" fill="none"/&gt;&lt;/svg&gt;'
1973  SW_BAND = f'&lt;svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"&gt;&lt;rect x="1" y="1" width="20" height="14" fill="{BAND}"/&gt;&lt;path d="M1 1V15M21 1V15" stroke="{BAND_EDGE}"/&gt;&lt;/svg&gt;'
1974  SW_PCT = f'&lt;svg width="30" height="16" viewBox="0 0 30 16" aria-hidden="true"&gt;&lt;line x1="1" y1="11" x2="29" y2="11" stroke="{LINK}" stroke-width="1.5"/&gt;&lt;text x="15" y="8" font-size="9" text-anchor="middle" fill="{INK}"&gt;%&lt;/text&gt;&lt;/svg&gt;'
1975  LEG1 = legend([
1976      (sw_dot(BLUE), "old read kernel, named oldread in bwx12 (median of the row)"),
1977      (sw_dot(ORANGE), "load-only loop: new read kernel, or asmread where the row says so"),
1978      (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),
1979      (sw_dot(MUTED), "filled marker: 7200 MT/s"),
1980      (SW_WHISK, "lowest to highest interval of the row, to scale (often narrower than the dot)"),
1981      (SW_PCT, "percent on the line: drop of the load-only loop below the old read kernel. A range gives the lowest and the highest pair of the row"),
1982  ])
1983  LEG2 = legend([
1984      (sw_dot(BLUE), "old read kernel, one dot per interval"),
1985      (sw_dot(ORANGE), "load-only loop, one dot per interval"),
1986      (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),
1987      (sw_dot(MUTED), "filled marker: 7200 MT/s"),
1988      (SW_BAND, "grey band: lowest to highest interval of the 8000 MT/s rows of the block"),
1989  ])
1990</pre></td><td valign="top"><ul><li><code>SW_WHISK</code>, <code>SW_BAND</code> and <code>SW_PCT</code> are the legend symbols for the range line, the grey band and the percent text.</li><li><code>LEG1</code> is the legend of figure 1. <code>LEG2</code> is the legend of figure 2.</li><li>The legend texts state the encoding of both figures. The colour <code>BLUE</code> marks the old read kernel, and the colour <code>ORANGE</code> marks the load-only loop. A hollow marker is an 8000 MT/s row, and a filled marker is a 7200 MT/s row.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>lab</code>: row label with notes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1991  # ------------------------------------------------------------------ tables
1992  def lab(main, *subs):
1993      """A row label: the name, and under it its notes in small type (no semicolon between label parts)."""
1994      return main + "".join("&lt;br&gt;" + small(x) for x in subs)
1995
1996</pre></td><td valign="top">Start of the table code. <code>lab</code> returns a row label for a table cell: the name, and each note on a new line in small type.</td></tr>
<tr><td colspan="2"><b>Function <code>only</code>: the one value of a list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1997  def only(values, what):
1998      vs = sorted(set(values))
1999      need(len(vs) == 1, f"{what}: more than one value {vs}")
2000      return vs[0]
2001
2002</pre></td><td valign="top">Returns the one distinct value of a list. The script stops unless the list holds exactly one distinct value. <code>q1_table</code> calls it for a position or a kernel order that must be the same in all records of a group.</td></tr>
<tr><td colspan="2"><b>Function <code>q1_table</code>: Table 1, the drop per part</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2003  def q1_table():
2004      def row(label, key, n):
2005          ds = Q1[key]["drops"]
2006          return [label, f1(min(ds)), f1(max(ds)), Q1[key]["old"].txt(), Q1[key]["new"].txt(), n]
2007
2008      def med_rng(pairs, which, rnd=None):
2009          ms = [p[which].med for (_, r_), p in pairs.items() if rnd is None or r_ == rnd]
2010          return f"{f2(min(ms))} to {f2(max(ms))}"
2011
2012      def per_round(pairs):
2013          return f"round 1: {med_rng(pairs, 'new', 1)}&lt;br&gt;round 2: {med_rng(pairs, 'new', 2)}&lt;br&gt;{small('(medians of the processes)')}"</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2736. The inner function <code>row</code> builds one table row from an entry of <code>Q1</code> (lines 430 to 441). <code>ds</code> is the list of the drops of its pairs, in percent (<code>drops_of</code>, line 421).</li><li>The cells of the row are: the label, the lowest and the highest drop with 1 decimal (<code>f1</code>), the range of the old-kernel intervals of the pairs, the range of the load-only intervals of the pairs, and n.</li><li><code>med_rng</code> is used for the two part A rows only. <code>pairs</code> is <code>A_PAIRS</code> or <code>A8_PAIRS</code> (lines 451 to 455), with one entry per session (or 8000 MT/s row) and round. An entry holds the range of the 3 intervals of the bw_old process (<code>old</code>) and of the bw_new process (<code>new</code>).</li><li><code>med_rng</code> takes the median of each process and returns the lowest and the highest of these medians with 2 decimals. With <code>rnd</code> it uses the processes of one round only.</li><li><code>per_round</code> returns this text for bw_new <code>read</code>, once for round 1 and once for round 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2014      a8 = Q1["A8"]["drops"]
2015      pos_ao, pos_aa, pos_l = only((r["pos"] for r in C_READ_AO), "position"), only((r["pos"] for r in C_READ_AA), "position"), only((r["pos"] for r in L_ASM), "position")
2016      ord_ao, ord_aa = only((r["file"][:-4] for r in C_READ_AO), "order"), only((r["file"][:-4] for r in C_READ_AA), "order")
2017
2018      def where(recs):
2019          """Sessions of the processes of one kernel order of part C."""
2020          named = sorted({r["session"] for r in recs if r["session"] is not None})
2021          extra = len({r["proc_key"] for r in recs if r["session"] is None})
2022          return ("session " if len(named) == 1 else "sessions ") + " and ".join(str(x) for x in named) + (" and the extra process" if extra else "")
2023      need(Rg(C_READ_AO).np == 2 and Rg(C_READ_AA).np == 2, "part C: not 2 processes per kernel order")</pre></td><td valign="top"><ul><li><code>a8</code>: the drops of the rows A-1 and A-2 at 8000 MT/s (<code>Q1["A8"]</code>, line 457).</li><li><code>pos_ao</code>, <code>pos_aa</code>: the position of the kernel <code>read</code> in the two part C groups. <code>pos_l</code>: the position of asmread in part L. <code>ord_ao</code>, <code>ord_aa</code>: the kernel order. It is the csv file name without <code>.csv</code> (cfwd or crev). <code>only</code> stops the script when the records of a group hold more than one value.</li><li><code>where</code> returns the sessions of the processes of a record group, for example <code>sessions 1 and 3</code>. A process without a session number is named <code>the extra process</code>.</li><li>Line 2023 stops the script unless each kernel order of part C has 2 processes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2024      rows = [
2025          "7200 MT/s, the planned rerun",
2026          row(f"&lt;b&gt;Part C&lt;/b&gt;: kernel read (the new read kernel) at position {pos_ao}, directly after oldread (order {ord_ao}), processes T72C1 and T72C3 {ref('T72C1', 'T72C3')}", "C_ao", n7200(Q1["C_ao"]["new"].recs, 4)),
2027          row(f"&lt;b&gt;Part C&lt;/b&gt;: kernel read (the new read kernel) at position {pos_aa}, directly after asmread (order {ord_aa}), processes T72C2 and T72C4 {ref('T72C2', 'T72C4')}", "C_aa", n7200(Q1["C_aa"]["new"].recs, 4)),
2028          row(f"&lt;b&gt;Part L&lt;/b&gt;: asmread (in place of the new read kernel) at position {pos_l}, directly after oldread {ref('L1', 'L2', 'L3')}", "L", n7200(Q1["L"]["new"].recs, 6)),
2029          [f"&lt;b&gt;Part A&lt;/b&gt;: bw_new read against bw_old read, 0.5 s, whole-pass stop. Drop between the medians of the two processes. Less exact than parts L and C {ref('A1', 'A2', 'A3')}",
2030           f1(min(Q1["A"]["drops"])), f1(max(Q1["A"]["drops"])),
2031           f"{med_rng(A_PAIRS, 'old')}&lt;br&gt;{small(f'(medians of the {rA_old.np} processes)')}", per_round(A_PAIRS),
2032           f"{len(A_PAIRS)} pairs of process medians / {plural(rA_old.np + Rg(A_NEW).np, 'process')} / 3 sessions / 1 boot"],</pre></td><td valign="top"><ul><li><code>rows</code> is the list of table rows. A text entry becomes a title row that spans all columns. A list entry becomes a row with 6 cells.</li><li>Part C, kernel <code>read</code> directly after oldread: <code>Q1["C_ao"]</code>. Part C, <code>read</code> directly after asmread: <code>Q1["C_aa"]</code>. Part L, asmread against oldread: <code>Q1["L"]</code>.</li><li>The numbers of pairs (4, 4 and 6) are typed here for the text of n (<code>n7200</code>, line 381). Line 438 asserts the same numbers for the pair lists. The process tags in the labels of the two part C rows are typed too (T72C1 and T72C3 in line 2026, T72C2 and T72C4 in line 2027), and no assertion compares them with the records. In the saved build the records of <code>C_READ_AO</code> hold the tags T72C1 and T72C3, and the records of <code>C_READ_AA</code> hold T72C2 and T72C4 (computed again for this companion).</li><li>Part A: the lowest and the highest of the 6 drops of <code>Q1["A"]</code>. Each of them is the drop between the median of the bw_old process and the median of the bw_new process of one session and round (<code>a_pair</code>, line 444).</li><li>The two rate cells of part A show process medians, not interval ranges: <code>med_rng</code> over the 6 bw_old processes, and <code>per_round</code> for bw_new.</li><li>The saved build gave these drops: 30.5 % to 31.2 % (<code>read</code> after oldread), 29.7 % to 31.1 % (<code>read</code> after asmread), 29.2 % to 30.5 % (part L) and 28.5 % to 31.8 % (part A) [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2033          "7200 MT/s, same boot, not part of the planned rerun (own rows in every comparison with 8000 MT/s)",
2034          row(f"&lt;b&gt;Control I&lt;/b&gt; (added after the first numbers were seen, not part of the plan fixed before the run): asmread (in place of the new read kernel), idle start {ref('T72I1', 'T72I2')}", "I", n7200(Q1["I"]["new"].recs, 4)),
2035          row("&lt;b&gt;F72d12&lt;/b&gt; (earlier run of the same boot at " + hm(F_OLD[0]["launch_utc"]) + f", not part of the rerun): asmread (in place of the new read kernel) {ref('F72')}", "F", n7200(Q1["F"]["new"].recs, 2)),
2036          "8000 MT/s, for context only (same computation)",
2037          row(f"&lt;b&gt;L-1&lt;/b&gt;: asmread (in place of the new read kernel) directly after oldread {ref('L-1')}", "L1", n8000(Q1["L1"]["new"].recs, 2)),
2038          [f"&lt;b&gt;A-1, A-2&lt;/b&gt;: bw_new read against bw_old read, drop between the medians of the two processes {ref('A-1', 'A-2')}", f1(min(a8)), f1(max(a8)),
2039           f"{med_rng(A8_PAIRS, 'old')}&lt;br&gt;{small(f'(medians of the {len(A8_PAIRS)} processes)')}", per_round(A8_PAIRS),
2040           f"{len(A8_PAIRS)} pairs of process medians / {plural(Rg(B_A_OLD['A-1'] + B_A_OLD['A-2'] + B_A_NEW['A-1'] + B_A_NEW['A-2']).np, 'process')} / 1 boot"],
2041          "Note",
2042          f'&lt;span class="tn"&gt;Part C: each kernel order has 2 processes. Order {ord_ao} ran in {where(C_READ_AO)}. Order {ord_aa} ran in {where(C_READ_AA)}. '
2043          f"So kernel order and session are not fully separated {ref('go')}.&lt;/span&gt;",
2044      ]
2045      return table(["Part and pair", "#Lowest drop, %", "#Highest drop, %", "#Old read kernel, GB/s", "#Load-only loop, GB/s", "n"], rows, "q1")
2046
2047</pre></td><td valign="top"><ul><li>Rows of the same boot that are not part of the planned rerun: control I (<code>Q1["I"]</code>, 4 pairs) and F72d12 (<code>Q1["F"]</code>, 2 pairs). The saved build gave 31.9 % to 32.8 % and 35.4 % [Ref5].</li><li>Rows at 8000 MT/s, for context: L-1 (<code>Q1["L1"]</code>, 2 pairs), and A-1 with A-2 (the drops <code>a8</code> and the process medians of <code>A8_PAIRS</code>). The page of the saved build shows 35.9 % to 36.1 % and 33.1 % to 39.8 %.</li><li>The note row says in which sessions each kernel order of part C ran. In the page of the saved build, order cfwd ran in sessions 1 and 3, and order crev ran in session 2 and in the extra process. The note concludes that kernel order and session are not fully separated.</li><li>Table 1 has no row for the 8 asmread pairs of part C. The caption of the table (line 2735) says so. Table 1 also has no row for the 8000 MT/s rows L-2 to L-4. Of the rows L-1 to L-4, <code>Q1</code> holds pairs of row L-1 only (line 436).</li><li>Line 2045 returns the HTML table (<code>table</code>, line 1501). Its 6 columns are: part and pair, lowest drop, highest drop, old read kernel, load-only loop, n.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>tnote</code>: note under a table</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2048  def tnote(head, *points):
2049      """A note under a table: its first sentences, then one bullet per further point."""
2050      return f'&lt;div class="tn"&gt;{head}' + '&lt;ul class="cl"&gt;' + "".join(f"&lt;li&gt;{x}&lt;/li&gt;" for x in points) + "&lt;/ul&gt;&lt;/div&gt;"
2051
2052</pre></td><td valign="top">Returns the HTML of a note under a table: a first text, then one bullet per further point.</td></tr>
<tr><td colspan="2"><b>Function <code>cmp_cell</code>: range cell of Table 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2053  def cmp_cell(rg, n):
2054      return f'&lt;span class="num"&gt;{rg.txt()}&lt;/span&gt;&lt;br&gt;{small(n)}'
2055
2056</pre></td><td valign="top">Returns one cell of Table 2: the range <code>rg.txt()</code> (lowest to highest rate with 2 decimals), and the text of n under it in small type.</td></tr>
<tr><td colspan="2"><b>Assertions for the rows of Table 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2057  rC_old_p0 = Rg([r for r in C_OLD if r["pos"] == 0])
2058  need(rC_old_p0.n == 4 and {r["file"] for r in rC_old_p0.recs} == {"cfwd.csv"} and rC_old_p0.overlaps(rPL_old), "part C, oldread at position 0: not 4 intervals of cfwd that overlap the pool")
2059  C_OLD_P2 = [r for r in C_OLD if r["pos"] == 2]
2060  need(len(C_OLD_P2) == 4 and {r["file"] for r in C_OLD_P2} == {"crev.csv"} and {r["kernel_before"] for r in C_OLD_P2} == {"read"}, "part C, oldread at position 2: not 4 intervals of crev directly after read")
2061  need({r["pos"] for r in P_L_OLD} == {0} and {r["pos"] for r in P_L_ASM} == {1} and {r["kernel_before"] for r in P_L_ASM} == {"oldread"}, "pool L-1 to L-4: positions")
2062  xc_text_range("part C, oldread at position 0 (the position of the 8000 MT/s rows)", "4.2", rC_old_p0.lo, rC_old_p0.hi, "", "0.01", f2)</pre></td><td valign="top"><ul><li><code>rC_old_p0</code>: the range of the part C oldread intervals at position 0. The script stops unless these are 4 intervals, all from <code>cfwd.csv</code>, and their range overlaps the 8000 MT/s pool <code>rPL_old</code>.</li><li><code>C_OLD_P2</code>: the part C oldread intervals at position 2. The script stops unless these are 4 intervals from <code>crev.csv</code>, each directly after the kernel <code>read</code>.</li><li>Line 2061: every oldread record of the pool L-1 to L-4 must be at position 0. Every asmread record of the pool must be at position 1, directly after oldread.</li><li>Line 2062 adds one line to the self-check list (<code>xc_text_range</code>, line 640). The line is PASS when the range of <code>rC_old_p0</code> stands in section 4.2 of FACTS.md, with a tolerance of 0.01 GB/s. The saved build gave 465.54 to 467.83 GB/s [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2063  # every comparison with 8000 MT/s of the rerun uses records of the rerun only: control I and F72d12 are never pooled into it
2064  for rg_ in (rA_old, rC_old, rL_old, rL_asm, rC_asm_ao, A_V3[1]["r7"], A_V3[2]["r7"]):
2065      need({r["dataset"] for r in rg_.recs} &lt;= {"rerun-A", "rerun-L", "rerun-C"}, "a comparison of the rerun with 8000 MT/s holds a record of control I or F72d12")
2066  RERUN_CMP_NEW = [rL_asm.lo &gt; rPL_asm.hi, rC_asm_ao.lo &gt; rPL_asm.hi, A_V3[1]["r7"].lo &gt; A_V3[1]["r8"].hi, A_V3[2]["r7"].lo &gt; A_V3[2]["r8"].hi]
2067  RERUN_CMP_C = 1                                             # one of them is a part C row (asmread directly after oldread), made by decision (r) of the facts sheet
2068  need(all(RERUN_CMP_NEW), "load-only loop: a comparison of the rerun with 8000 MT/s is not 'higher'")
2069  need(len(RERUN_CMP_NEW) == 4 and {r["dataset"] for r in rL_asm.recs} == {"rerun-L"} and {r["dataset"] for r in rC_asm_ao.recs} == {"rerun-C"}
2070       and all({r["kernel"] for r in rg_.recs} == {"asmread"} for rg_ in (rL_asm, rC_asm_ao))
2071       and all({(r["dataset"], r["binary"], r["kernel"], r["session"]) for r in A_V3[rnd]["r7"].recs} == {("rerun-A", "bw_new", "read", 1)} for rnd in (1, 2)),
2072       "load-only loop: the 4 comparisons of the rerun are not part L and part C with asmread, and session 1 of part A with bw_new read in rounds 1 and 2")</pre></td><td valign="top"><ul><li>Lines 2064 and 2065: each 7200 MT/s range that the rerun compares with 8000 MT/s must hold only records of the datasets <code>rerun-A</code>, <code>rerun-L</code> and <code>rerun-C</code>. So no record of control I or F72d12 is part of a comparison of the rerun.</li><li><code>RERUN_CMP_NEW</code>: the 4 comparisons of the load-only loop. An entry is true when the lowest 7200 MT/s rate is above the highest 8000 MT/s rate.</li><li>The 4 comparisons are: asmread of part L against the pool, asmread directly after oldread of part C against the pool, and session 1 of part A (bw_new <code>read</code>) against A-1 and A-2 in round 1 and in round 2.</li><li>Line 2068 stops the script unless all 4 are true. Lines 2069 to 2072 stop it unless the records of the 4 ranges have these datasets, kernels and session.</li><li><code>RERUN_CMP_C = 1</code> records that one of the 4 is a part C row. Line 2432 uses it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2073  # caption of Table 2: which of its rows are the comparisons that sentence 3 of the Short version counts
2074  T2_RERUN_ROWS = (f"The block &amp;quot;Load-only loop&amp;quot; holds the {len(RERUN_CMP_NEW)} comparisons of the rerun that sentence 3 of the Short version counts. "
2075                   "Two use the new read kernel itself: part A, session 1, rounds 1 and 2. Two use asmread in its place: part L, and the part C row &amp;quot;asmread directly after oldread&amp;quot;. "
2076                   f"The rows of {F72} and of {CI} are not comparisons of the rerun.")
2077
2078</pre></td><td valign="top"><code>T2_RERUN_ROWS</code> is a text for the caption of Table 2 (line 2751). It names the 4 comparisons of the rerun that sentence 3 of the Short version counts. The number 4 in it comes from <code>len(RERUN_CMP_NEW)</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>q2_table</code>: Table 2, 7200 MT/s against 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2079  def q2_table():
2080      pool_l = ("pool L-1 to L-4, oldread at position 0 (L-1: 6 s, the argument line of part L. It differs from the part C lines in the kernel order. "
2081                "L-2 to L-4: 4 s, other hardware events counted) " + ref("L-1", "L-1l", "L-2a", "L-2b", "L-3", "L-4a", "L-4b", "L-4c"))
2082      pool_old, pool_asm = "pool L-1 to L-4, oldread at position 0&lt;br&gt;", "pool L-1 to L-4, asmread at position 1&lt;br&gt;"
2083      cannot = lambda rg: f"The test cannot exclude a difference of about {f1(width_pct(rg))} % (est. from one boot)"</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2752. <code>pool_l</code>, <code>pool_old</code> and <code>pool_asm</code> are label texts for the 8000 MT/s pool L-1 to L-4.</li><li><code>pool_l</code> is the long label of the row <code>Part C (oldread)</code> (line 2089). It states that row L-1 has 6 s intervals and ran the argument line of part L. It states that this line differs from the part C lines in the kernel order. It states that the rows L-2 to L-4 have 4 s intervals with other hardware events counted.</li><li>So 2 of the 11 intervals of each pool are 6 s intervals, and 9 are 4 s intervals. Every 7200 MT/s row that is compared with the pool has 6 s intervals (lines 317 to 319).</li><li>The label does not name two more differences of the rows L-2 to L-4. Their processes timed longer kernel sequences: 7 to 15 kernels, against 5 kernels in the part L line. Each sequence starts with oldread, asmread. In round 1 the kernel directly before oldread is read_1pl in the part L line. In the rows L-2 and L-3 it is another test loop. The 3 processes of row L-4 ran 1 round, and the part L line runs 2 rounds. These facts were read for this companion from the <code># bwx:</code> header lines of the 6 csv files of these rows.</li><li><code>cannot(rg)</code> returns the sentence on the difference that an overlap result cannot exclude. The size is <code>width_pct(rg)</code> (line 476): the width of the 8000 MT/s range in percent of its lower end, printed with 1 decimal.</li><li>The sentence labels this size as an estimate (<code>est. from one boot</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2084      rows = ["Old read kernel"]
2085      rows.append(["Part A (bw_old read)", cmp_cell(rA_old, n7200(A_OLD)), f"pool A-1 to A-3 {ref('A-1', 'A-2', 'A-3')}&lt;br&gt;" + cmp_cell(rPA_old, n8000(P_A_OLD)), "yes", "0",
2086                   f"&amp;quot;{WORD_SAME}&amp;quot;. {cannot(rPA_old)}. The 7200 MT/s range is wider than the 8000 MT/s range ({f2(A_OLD_W7)} GB/s against {f2(A_OLD_W8)} GB/s). "
2087                   f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range ({one_process(A_OLD_BELOW)}), and {len(A_OLD_ABOVE)} lie above it ({one_process(A_OLD_ABOVE)})"])
2088      rows.append([lab("Part C (oldread)", f"{rC_old_p0.n} intervals at position 0 (order cfwd), {len(C_OLD_P2)} at position 2 (order crev, directly after read)"),
2089                   cmp_cell(rC_old, n7200(C_OLD)), pool_l + "&lt;br&gt;" + cmp_cell(rPL_old, n8000(P_L_OLD)), "yes", "0",
2090                   f"&amp;quot;{WORD_SAME}&amp;quot;. {cannot(rPL_old)}. The 8000 MT/s rows hold oldread at position 0 only. "
2091                   f"The {rC_old_p0.n} part C intervals at position 0 span {rC_old_p0.txt()} GB/s and overlap too"])
2092      rows.append(["Part L (oldread at position 0)", cmp_cell(rL_old, n7200(L_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)), "no", signed(L_OLD_NEAR),
2093                   f"&amp;quot;{WORD_DIFF}&amp;quot;. Part L is lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends ({f1(L_OLD_NEAR_PCT)} % of the lower end of the 8000 MT/s range) "
2094                   f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_MED_PCT)} % of the 8000 MT/s median). The data do not show the cause (section 3)"])
2095      rows.append([lab("F72d12 (oldread)", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_old, n7200(F_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),
2096                   "yes", "0", f"&amp;quot;{WORD_SAME}&amp;quot;. {cannot(rPL_old)}. Not pooled with part L"])
2097      rows.append([lab("Control I (oldread)", "added after the first numbers were seen"), cmp_cell(rI_old, n7200(I_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),
2098                   "yes", "0", f"&amp;quot;{WORD_SAME}&amp;quot;. {cannot(rPL_old)}. Not pooled with part L"])</pre></td><td valign="top"><ul><li>Rows of the old read kernel. Each list entry is one table row with 6 cells: the row name, the 7200 MT/s range with n (<code>cmp_cell</code>), the 8000 MT/s range with n, the overlap, the distance of the nearest ends, and the wording.</li><li>In every row of this function the cells <code>yes</code>, <code>no</code> and <code>0</code> are typed. The assertions in lines 486 to 498 and 514 stop the script when a typed result does not hold. The wording cells of 9 of the 12 rows with 6 cells use the fixed texts <code>WORD_SAME</code> and <code>WORD_DIFF</code> (lines 470 and 471). The other 3 rows have their own text: the two part A rows of bw_new <code>read</code>, and the part C row of the bwx12 kernel <code>read</code>.</li><li>Part A: <code>rA_old</code> (18 intervals of bw_old <code>read</code>) against the pool <code>rPA_old</code> (21 intervals of A-1 to A-3). The text adds the width of both ranges, and the number of 7200 MT/s intervals below and above the 8000 MT/s range (lines 525 to 528). <code>one_process</code> (line 531) names the session and the round of each of these two groups. It stops the script unless a group holds the 3 intervals of one process. In the page of the saved build, the 3 intervals of session 1, round 2 lie below the range, and the 3 intervals of session 3, round 1 lie above it.</li><li>Part C: <code>rC_old</code> (all 8 oldread intervals) against the pool <code>rPL_old</code> (11 oldread intervals at position 0). The text states that the 8000 MT/s rows hold oldread at position 0 only. It adds the range of the 4 part C intervals at position 0. It states that this range overlaps the pool too (asserted in line 2058).</li><li>Part L: <code>rL_old</code> (6 intervals) against <code>rPL_old</code>, overlap <code>no</code>. The distance <code>L_OLD_NEAR</code> (line 489) is the highest part L rate minus the lowest pool rate, a negative value. <code>signed</code> (line 224) prints it with its sign and 2 decimals. The text adds the difference of the medians, and both values in percent. The saved build gave -1.24 GB/s [Ref5].</li><li>F72d12 (<code>rF_old</code>, 2 intervals) and control I (<code>rI_old</code>, 4 intervals): each has its own row against <code>rPL_old</code>. They are not pooled with part L.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2099      rows.append("Load-only loop (no percent change between the two speeds is given)")
2100      rows.append([lab("Part L (asmread at position 1)", "in place of the new read kernel"), cmp_cell(rL_asm, n7200(L_ASM)), pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)),
2101                   "no", signed(DIST["nearest"][0]), f"&amp;quot;{WORD_DIFF}&amp;quot;. Part L is higher"])
2102      for rnd in (1, 2):
2103          v = A_V3[rnd]
2104          p8 = ", ".join(str(x) for x in sorted(set(v["p8"])))
2105          rows.append([f"Part A, session 1, round {rnd} (bw_new read, the new read kernel)", cmp_cell(v["r7"], n7200(v["r7"].recs)),
2106                       f"A-1 and A-2, round {rnd}&lt;br&gt;" + cmp_cell(v["r8"], n8000(v["r8"].recs)), "no", signed(v["near"]),
2107                       f"outside (above) the 8000 MT/s range of the same round. Pass counts per interval: {v['p7'][0]} at 7200 MT/s, {p8} at 8000 MT/s. They are not all equal. So part A gives no exact size of the difference"])</pre></td><td valign="top"><ul><li>Line 2099 is the title row of the load-only rows.</li><li>Part L, asmread at position 1: <code>rL_asm</code> (6 intervals) against the pool <code>rPL_asm</code> (11 asmread intervals at position 1), overlap <code>no</code>. The distance is <code>DIST["nearest"][0]</code> (line 504): the lowest part L rate minus the highest pool rate. The saved build gave +12.48 GB/s [Ref5].</li><li>Part A, session 1, one row per round: <code>v["r7"]</code> (3 intervals of bw_new <code>read</code>) against <code>v["r8"]</code> (6 intervals of A-1 and A-2 of the same round), overlap <code>no</code>. The distance is <code>v["near"]</code> (line 515). The saved build gave +32.75 GB/s in round 1 and +10.37 GB/s in round 2 [Ref5]. Table 2 has no row for sessions 2 and 3 of bw_new <code>read</code>. The comment in line 508 names rule V3 for the use of session 1.</li><li>The wording cell of these two rows does not use <code>WORD_DIFF</code>. It starts with the typed text <code>outside (above) the 8000 MT/s range of the same round</code>. Line 514 asserts this result.</li><li>Then the cell gives the pass counts per interval: the one value of <code>p7</code> at 7200 MT/s, and the distinct values of <code>p8</code> at 8000 MT/s (line 516). Two typed sentences follow: the counts are not all equal, and part A therefore gives no exact size of the difference.</li><li>No assertion checks the sentence on the pass counts. In the page of the saved build it holds: 664 passes at 7200 MT/s against 600 passes at 8000 MT/s in round 1, and against 600, 603, 663 and 664 passes in round 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2108      rows.append(["Part C, kernel read (the new read kernel) at position 1",
2109                   f'after oldread: &lt;span class="num"&gt;{rC_read_ao.txt()}&lt;/span&gt;&lt;br&gt;{small(n7200(C_READ_AO))}&lt;br&gt;after asmread: &lt;span class="num"&gt;{rC_read_aa.txt()}&lt;/span&gt;&lt;br&gt;{small(n7200(C_READ_AA))}',
2110                   "no bwx12 run", "-", "-",
2111                   "Insufficient data: no 8000 MT/s run of kernel read with bwx12. The bwx12 kernel read (new C read loop) was never run with bwx12 at 8000 MT/s. "
2112                   f"The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its place {ref('rules', 'facts')}"])
2113      rows.append([lab("Part C, asmread directly after oldread", "order crev, round 1, position 0", "in place of the new read kernel"), cmp_cell(rC_asm_ao, n7200(C_ASM_AO)),
2114                   pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rC_asm_ao.nearest(rPL_asm)),
2115                   f"&amp;quot;{WORD_DIFF}&amp;quot;. Part C is higher. The 8000 MT/s rows match in the kernel that ran directly before (oldread). "
2116                   "They do not match in the position: asmread is at position 1 there"])
2117      rows.append([lab("F72d12 (asmread at position 1)", "in place of the new read kernel", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_asm, n7200(F_ASM)),
2118                   pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "yes", "0",
2119                   f"inside the range of the 8000 MT/s pool: &amp;quot;{WORD_SAME}&amp;quot;. The test cannot exclude a difference of {f2(rPL_asm.hi - rPL_asm.lo)} GB/s, the width of that range (est. from one boot). "
2120                   f"Against L-1 alone F72d12 is {f2(rF_asm.nearest(rL1_asm))} GB/s higher. Not pooled with part L"])
2121      rows.append([lab("Control I (asmread at position 1)", "in place of the new read kernel", "added after the first numbers were seen"), cmp_cell(rI_asm, n7200(I_ASM)),
2122                   pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rI_asm.nearest(rPL_asm)),
2123                   f"&amp;quot;{WORD_DIFF}&amp;quot;. Control I is higher. Not pooled with part L"])</pre></td><td valign="top"><ul><li>Part C, bwx12 kernel <code>read</code> (the new read kernel): the two 7200 MT/s ranges <code>rC_read_ao</code> and <code>rC_read_aa</code>, each with n. The 8000 MT/s cell holds <code>no bwx12 run</code>. The overlap cell and the distance cell hold <code>-</code>. The text starts with <code>Insufficient data</code>: this kernel was never run with bwx12 at 8000 MT/s.</li><li>The position 1 in the name of this row is typed. No assertion compares it directly with the records of <code>C_READ</code> (line 283). <code>q1_table</code> reads the position of both groups from the records (line 2015). Table 1 of the saved build prints position 1 for both.</li><li>Part C, asmread directly after oldread: <code>rC_asm_ao</code> (2 intervals) against the pool <code>rPL_asm</code>, overlap <code>no</code>. The distance is <code>rC_asm_ao.nearest(rPL_asm)</code>. The saved build gave +15.56 GB/s [Ref5]. The text of the row states one mismatch: the 8000 MT/s rows hold asmread at position 1, and this row holds it at position 0. Lines 1884 and 2061 assert both positions.</li><li>Table 2 has no comparison row for the other 6 asmread intervals of part C: the 4 intervals directly after <code>read</code> (<code>C_ASM_AR</code>), and the 2 intervals that are the first interval of their process (<code>C_ASM_FI</code>). Figure 2 shows them in the group without a band (lines 1931 and 1932). The note on the older runner bwx uses <code>C_ASM_AR</code> (line 2150).</li><li>F72d12, asmread: <code>rF_asm</code> against <code>rPL_asm</code>, overlap <code>yes</code>. The text gives the width of the pool range in GB/s, and the distance of F72d12 above row L-1 alone (<code>rL1_asm</code>, line 467). The saved build gave 1.73 GB/s above L-1 [Ref5].</li><li>Control I, asmread: <code>rI_asm</code> against <code>rPL_asm</code>, overlap <code>no</code>. The saved build gave +4.61 GB/s [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2124      # the choice of the pool: the same test against row L-1 alone (the row with the argument line of part L)
2125      rL1_old = Rg(B_L_OLD["L-1"])
2126      alone = [("part L, oldread", rL_old, rPL_old, rL1_old), ("part C, oldread", rC_old, rPL_old, rL1_old), ("F72d12, oldread", rF_old, rPL_old, rL1_old),
2127               ("control I, oldread", rI_old, rPL_old, rL1_old), ("part L, asmread", rL_asm, rPL_asm, rL1_asm), ("part C, asmread", rC_asm_ao, rPL_asm, rL1_asm),
2128               ("F72d12, asmread", rF_asm, rPL_asm, rL1_asm), ("control I, asmread", rI_asm, rPL_asm, rL1_asm)]
2129      changed = [nm for nm, r7, pool, l1 in alone if r7.overlaps(pool) != r7.overlaps(l1)]
2130      need(changed == ["F72d12, asmread"], f"table 2: rows whose overlap result changes against L-1 alone: {changed}")
2131      # row X2d12 (12 modules, another boot, two changed TXREQ settings): shown, not used. Would it change an overlap result?
2132      pool_x = {id(rPL_old): Rg(P_L_OLD + EXTRA["X2d12"]["old"]), id(rPL_asm): Rg(P_L_ASM + EXTRA["X2d12"]["asm"])}
2133      need(all(r7.overlaps(pool) == r7.overlaps(pool_x[id(pool)]) for nm, r7, pool, l1 in alone), "table 2: an overlap result changes when row X2d12 is added to the pool")
2134      need(n8000(EXTRA["X2d12"]["old"]) == n8000(EXTRA["X2d12"]["asm"]), "X2d12: n differs between the two kernels")</pre></td><td valign="top"><ul><li>A test of the choice of the pool. <code>alone</code> lists the 8 rows that use the pool L-1 to L-4. Each entry holds the 7200 MT/s range, the pool range, and the range of row L-1 alone.</li><li><code>changed</code>: the rows whose overlap result against L-1 alone differs from the result against the pool. The script stops unless this list holds only <code>F72d12, asmread</code>.</li><li><code>pool_x</code>: the two pools with the records of X2d12 added. The script stops when an overlap result changes with this larger pool.</li><li>Line 2134 stops the script unless the text of n of X2d12 is the same for both kernels.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2135      rows.append("Notes")
2136      rows.append(f'&lt;span class="tn"&gt;Pool or L-1 alone: with row L-1 alone in place of the pool L-1 to L-4, {len(alone) - len(changed)} of the {len(alone)} rows that use the pool keep their overlap result. '
2137                  f"The exception is F72d12 with asmread (earlier run of the same boot, not part of the rerun): it lies {f2(rF_asm.nearest(rL1_asm))} GB/s above L-1. "
2138                  f"The choice of the pool was made after the numbers were seen (decision (k) of the facts sheet) {ref('facts')}.&lt;/span&gt;")
2139      rows.append('&lt;span class="tn"&gt;Part C: the rules file contradicts itself here. Rule F2 (points 2 and 3) would show part C at 7200 MT/s only. '
2140                  "Rules V1 (point 2), V2 (point 4) and V4 compare part C with the 8000 MT/s rows. This page follows the facts sheet (its decision (r) in section 2) "
2141                  f"and compares the two part C rows that have an 8000 MT/s row of the list {ref('facts', 'rules')}. This choice was made after the numbers were seen.&lt;/span&gt;")
2142      rows.append(f'&lt;span class="tn"&gt;Row X2d12 is shown here and not used. It is 1 process of the argument line of part L at 8000 MT/s with 12 modules, in another boot of 2026-11-17 {ref("xX2d12", "xX2d12l", "klogX2d12")}. '
2143                  f"Rules V2 (point 4) and F2 (point 2) name it as an 8000 MT/s row of the part L line. Rule V4 lists it among the rows that are not used (a firmware test with two changed TXREQ settings) {ref('rules')}. "
2144                  f"This page follows rule V4. X2d12 gave {rX2_old.txt()} GB/s for the old read kernel and {rX2_asm.txt()} GB/s for asmread ({n8000(EXTRA['X2d12']['old'])} per kernel). "
2145                  f"With X2d12 added to the pool L-1 to L-4, all {len(alone)} rows that use the pool keep their overlap result.&lt;/span&gt;")</pre></td><td valign="top"><ul><li>Line 2135 adds the title row <code>Notes</code>. Three notes follow, each as one row over the full width of the table.</li><li>Pool or L-1 alone: how many of the 8 rows keep their overlap result (from <code>alone</code> and <code>changed</code>), and the distance of F72d12 above L-1. The note states that the pool was chosen after the numbers were seen.</li><li>Part C: a fixed text. It says that the rules file contradicts itself on part C. The page compares the two part C rows that have a row in the list of 8000 MT/s rows. The note states that this choice was made after the numbers were seen.</li><li>X2d12: the ranges <code>rX2_old</code> and <code>rX2_asm</code> (line 1326) and n. The note says that the row is shown and not used.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2146      # rows of the older runner bwx: named by the rules file, another binary, so no wording comes from them
2147      n_rev = n8000(X_REV_READ)
2148      need(n_rev == n8000(X_REV_ASM) and n8000(X_READ_AO) == n8000(X_READ_AA) == n8000(X_ASM_AR), "runner bwx: n differs between the kernels")
2149      x_refs = ref("xB7a", "xB7b", "xC3a", "xC3b")
2150      sets = [("read after oldread", C_READ_AO, rX_read_ao, X_ABOVE[0]), ("read after asmread", C_READ_AA, rX_read_aa, X_ABOVE[1]), ("asmread after read", C_ASM_AR, rX_asm_ar, X_ABOVE[2])]
2151      need(len(sets) == len(X_PAIRS) and all(d_ &gt; 0 for *_, d_ in sets), "runner bwx: the three sets of part C intervals")
2152      rows.append(tnote(
2153          f"Other runner binary (bwx, not the bwx12 binary of the rerun): rule V2 (point 4) names 8000 MT/s rows (12 modules) of the older runner bwx for the comparison with part C {ref('rules')}.",
2154          f"These rows differ from part C in at least four ways. They used the older binary bwx. Each process timed a sequence of {len(X_SEQ)} kernels, and a part C process timed {len(SPEC['cfwd'][2].split(','))}. "
2155          "The processes of the two result folders B7-* ran without the counting of hardware events of the CPU (count=0 in the csv header), "
2156          f"and those of the two folders C3-* ran with it (count=1). {X_OFFSET} of the {len(X_POOL_HEAD)} processes used the runner option &lt;code&gt;--start offset&lt;/code&gt;. "
2157          f"Part C used bwx12 with the counting of hardware events and &lt;code&gt;--start common&lt;/code&gt; {x_refs} {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.",
2158          f"The highest of their load-only intervals ({n8000(X_LOADS)}) was {f2(X_MAX_READ)} GB/s for kernel read and {f2(X_MAX_ASM)} GB/s for asmread {x_refs}.",
2159          f"{('Three' if len(sets) == 3 else str(len(sets)))} sets of part C intervals have such bwx rows with the same kernel directly before ({n8000(X_READ_AO)} per set at 8000 MT/s). "
2160          "Each set lies above the highest value of its bwx rows. The distances are those of the nearest ends. "
2161          + " ".join(f"The set &amp;quot;{nm}&amp;quot; ({n7200(recs)}) lies {f2(d_)} GB/s above {f2(xr.hi)} GB/s." for nm, recs, xr, d_ in sets),
2162          f"The {Rg(X_REV_READ).np} bwx processes of two other result folders ran another kernel order. They reached {f2(X_REV_MAX_READ)} GB/s (read) and {f2(X_REV_MAX_ASM)} GB/s (asmread) "
2163          f"({n_rev} per kernel) {ref('xB5a-rev', 'xB5b-rev')}. "
2164          "The read value lies inside the 7200 MT/s range of both read rows of part C (after oldread and after asmread). The asmread value lies inside the 7200 MT/s asmread range of part L."))</pre></td><td valign="top"><ul><li>The note on the rows of the older runner bwx. The comment in line 2146 states that no wording comes from them.</li><li>Lines 2147 and 2148 take the text of n of the bwx groups. The script stops when n differs between the kernels.</li><li><code>sets</code>: three groups of part C intervals. Each has the range of the bwx rows with the same kernel directly before, and the distance <code>X_ABOVE</code> (line 545). The script stops unless each distance is above 0.</li><li>The note lists how the bwx rows differ from part C: the binary, the number of kernels in the sequence, the counter setting and the start option.</li><li>It gives the highest bwx rate of the kernel <code>read</code> and of asmread (<code>X_MAX_READ</code>, <code>X_MAX_ASM</code>, lines 546 and 547). For each set it gives the distance of the part C range above the highest rate of its bwx rows.</li><li>It gives the highest rates of the bwx processes with another kernel order (<code>X_REV_MAX_READ</code>, <code>X_REV_MAX_ASM</code>, line 549). The note states that this <code>read</code> rate lies inside both 7200 MT/s <code>read</code> ranges of part C, and that this asmread rate lies inside the 7200 MT/s asmread range of part L. Lines 551 to 553 assert both. The page of the saved build shows 324.36 GB/s (<code>read</code>) and 324.98 GB/s (asmread) for these 8000 MT/s processes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2165      # the three boots with 10 modules that rule V1 (points 3 and 4) quotes: how far two boots at 8000 MT/s differ
2166      n10 = n8000(T10_ASM[0].recs)
2167      need(n10 == n8000(T10_ASM[1].recs), "10-module boots: n differs between the two boots")
2168      rows.append(tnote(
2169          f"Boots with 10 modules (rule V1, points 3 and 4) {ref('rules')}: on 2026-11-17 three boots at 8000 MT/s found 10 modules. Each ran the argument line of part L once "
2170          f"{ref('xX1d10', 'klogX1d10', 'xX1d10b', 'klogX1d10b', 'xBASEd10', 'klog10')}. They are not rows of the list, and no wording comes from them.",
2171          f"By the settings records of the results folder, two of these boots had the same firmware settings (TXREQ Min changed) {ref('x1', 'x2')}. Their asmread gave {' / '.join(f2(v) for v in T10_ASM[0].v)} GB/s "
2172          f"and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s ({n10} each). The two medians are {f1(T10_APART)} % apart (percent of the lower median).",
2173          f"The three boots gave {rT10_old.txt()} GB/s for the old read kernel ({plural(rT10_old.n, 'interval')} / {plural(rT10_old.np, 'process')} / 3 boots). This range is {f1(width_pct(rT10_old))} % wide.",
2174          f"Limit: by the same records the third boot had the original firmware settings {ref('rev')}. So the three boots did not differ by the boot alone."))</pre></td><td valign="top"><ul><li>The note on the three boots with 10 modules. Its text says that no wording comes from them.</li><li><code>n10</code>: the text of n of the asmread records of one boot. The script stops unless it is equal for the two boots of <code>T10_ASM</code> (line 1327).</li><li>The note gives the asmread rates of these two boots with 2 decimals, and <code>T10_APART</code> (line 1328): the distance of their two medians in percent of the lower median.</li><li>It gives the oldread range of the three boots (<code>rT10_old</code>, line 1329) and the width of this range in percent of its lower end.</li><li>By the text of the note, the two boots of <code>T10_ASM</code> had the same firmware settings. The third boot had the original settings. The note names this as a limit: the three boots did not differ by the boot alone.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2175      # rounding: a distance is computed before rounding (reader finding: two printed distances are not the difference of the printed rates)
2176      ex = [(f2(rF_asm.nearest(rL1_asm)), "this table", q(rF_asm.lo) - q(rL1_asm.hi)), (f2(DIST["farthest"][0]), "Table 4", q(rL_asm.hi) - q(rPL_asm.lo))]
2177      ex = [f"{shown} GB/s ({where_})" for shown, where_, from_rounded in ex if Decimal(shown) != from_rounded]
2178      rows.append('&lt;span class="tn"&gt;Rounding: a distance is computed from the rates before rounding. So it can differ by 0.01 GB/s from the difference of the two rounded rates'
2179                  + (". Examples: " + " and ".join(ex) if ex else "") + ".&lt;/span&gt;")
2180      return table(["7200 MT/s row", "Range at 7200 MT/s, GB/s, and n", "8000 MT/s rows: range, GB/s, and n", "Overlap", "#Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)",
2181                    "Wording by the rules fixed before the run"], rows, "q2")
2182
2183</pre></td><td valign="top"><ul><li>The rounding note. <code>ex</code> holds two distances: F72d12 above L-1 (this table), and the farthest ends of part L and the pool (Table 4).</li><li>For each one it compares the printed distance with the difference of the two rounded rates. The printed distance is computed from the rates before rounding and then rounded to 0.01 GB/s. An example stays in the note only when the two values differ.</li><li>In the page of the saved build both examples stay: 1.73 GB/s and 39.38 GB/s. The differences of the rounded rates are 1.74 GB/s and 39.39 GB/s (computed again for this companion).</li><li>Lines 2180 and 2181 return the HTML table with 6 columns.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>visits_table</code>: Table 3, visits of the part L line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2184  def visits_table():
2185      """The three visits of the part L line in the 7200 MT/s boot: when and from which state each one started."""
2186      hms = lambda utc: utc[11:19]
2187      l_launch = sorted({r["launch_utc"] for r in L_OLD})
2188      i_launch = sorted({r["launch_utc"] for r in I_OLD})
2189      l_load = sorted({D(r["load1_at_launch"]) for r in L_OLD})
2190      i_load = [D([r for r in I_OLD if r["tag"] == t][0]["load1_at_launch"]) for t in ("T72I1", "T72I2")]
2191      i_gap = [int(LAUNCH[t]["gap_s"]) for t in ("T72I1", "T72I2")]
2192      need(all(LAUNCH[t]["gap_s"] == 5 and "of part A" in LAUNCH[t]["start_state"] for t in ("T72L1", "T72L2", "T72L3")), "part L: a process did not start 5 s after part A")
2193      need(max(i_load) &lt; 1 and D(F_OLD[0]["load1_at_launch"]) &lt; 1, "control I or F72d12: load at launch is not below 1.0")
2194      per = lambda rg: n7200(rg.recs)
2195      need(n7200(F_ASM) == n7200(F_OLD) and n7200(L_ASM) == n7200(L_OLD) and n7200(I_ASM) == n7200(I_OLD), "table 3: n differs between the two kernels of a visit")</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2756. <code>l_launch</code> and <code>i_launch</code>: the launch times of the part L processes and of the control I processes, from the field <code>launch_utc</code> of the oldread records.</li><li><code>l_load</code> and <code>i_load</code>: the 1-minute load averages at these launches (field <code>load1_at_launch</code>). <code>i_gap</code>: the seconds since the end of the previous 120-thread process (<code>gap_s</code> of <code>LAUNCH</code>, line 879).</li><li>Line 2192 stops the script unless each part L step started 5 s after part A.</li><li>Line 2193 stops the script unless control I and F72d12 started at a load average below 1.0.</li><li>Line 2195 stops the script unless the text of n is equal for asmread and oldread in each visit.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2196      rows = [
2197          [lab("F72d12", "earlier run of the same boot, not part of the rerun"), F_LAUNCH,
2198           f"{F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG} UTC) {ref('gaps')}. Load average {f2(F_OLD[0]['load1_at_launch'])} at launch {ref('F72l')}. "
2199           f"Process list, written {F_ENV_BEFORE_S} s before the launch: the Linux kernel thread {F_TOP[3]} at {F_TOP[2]} %CPU {ref('F72e')}",
2200           rF_asm.txt(), rF_old.txt(), per(rF_asm)],
2201          ["Part L", f"{hms(l_launch[0])} to {hms(l_launch[-1])}",
2202           f"5 s after the last 120-thread process of part A. Load average {f2(l_load[0])} to {f2(l_load[-1])} at launch. "
2203           f"Process lists before the launch: at most {L_ENV_MAX} %CPU {ref('envT72L1', 'envT72L2', 'envT72L3')}",
2204           rL_asm.txt(), rL_old.txt(), per(rL_asm)],
2205          [lab("Control I", "added after the first numbers were seen"), " and ".join(hms(x) for x in i_launch),
2206           f"Idle start: load average {f2(i_load[0])} and {f2(i_load[1])} at launch, {i_gap[0]} s and {i_gap[1]} s after the previous 120-thread process. "
2207           f"Process lists before the launch: at most {I_ENV_MAX} %CPU {ref('envT72I1', 'envT72I2')}",
2208           rI_asm.txt(), rI_old.txt(), per(rI_asm)],
2209      ]
2210      return table(["Visit", "Launch, UTC", "Start state", "#asmread, GB/s", "#oldread, GB/s", "n per kernel"], rows, "visits")
2211
2212</pre></td><td valign="top"><ul><li>One row per visit: F72d12, part L and control I.</li><li>The cells are: the visit, the launch time, the start state, the asmread range, the oldread range, and n per kernel. The launch cell of part L holds the first and the last of its 3 launch times. The launch cell of control I holds its 2 launch times. The two ranges are <code>txt()</code> of the <code>Rg</code> objects: lowest to highest rate with 2 decimals.</li><li>The start state of F72d12 uses values of the raw-file checks in lines 1117 to 1127: the seconds since the first kernel log line of the boot, and the busiest process of the saved process list. It also gives the load average at launch, from the first oldread record.</li><li>The start states of part L and control I give the load at launch and the highest %CPU of the saved process lists (<code>L_ENV_MAX</code>, <code>I_ENV_MAX</code>, lines 1134 and 1135). For part L the text gives the lowest and the highest load of its 3 launches. For control I it gives both loads.</li><li>In the page of the saved build, F72d12 started 20 s after the first kernel log line of the boot, at a load average of 0.34. Part L started 5 s after part A, at load averages of 74.05 to 104.52. Control I started at load averages of 0.87 and 0.91, 287 s and 265 s after the previous 120-thread process.</li><li>In the saved build, the process list of F72d12 shows <code>pr/ttyAMA-1</code> at 51.6 %CPU [Ref5]. Line 2199 names it a Linux kernel thread. The process lists of part L and control I show at most 0.1 %CPU [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>dist_table</code>: Table 4, three kinds of distance</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2213  def dist_table():
2214      names = {"nearest": "Nearest ends of the two ranges", "medians": "Medians", "farthest": "Farthest ends of the two ranges"}
2215      rows = [[names[k], f2(DIST[k][0]), f2(DIST[k][1])] for k in ("nearest", "medians", "farthest")]
2216      return table(["Kind of distance", "#Part L above the 8000 MT/s pool L-1 to L-4, GB/s", "#Part L above F72d12 (same 7200 MT/s boot, earlier run, not part of the rerun), GB/s"], rows, "narrow")
2217
2218</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2758. The table has one row per kind of distance: nearest ends, medians, farthest ends.</li><li>The two values of a row come from <code>DIST</code> (lines 503 to 507): asmread of part L against the 8000 MT/s pool, and asmread of part L against F72d12. <code>f2</code> rounds each value to 0.01 GB/s.</li><li>The saved build gave 12.48 and 18.87 GB/s (nearest ends), 17.61 and 20.54 GB/s (medians), and 39.38 and 26.03 GB/s (farthest ends) [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>load_table</code>: Table 6, load average at each launch</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2219  def load_table():
2220      hms = lambda utc, date=False: (utc[:10] + " " if date else "") + utc[11:19] + " UTC"
2221      what = {"A": "part A, session {s}: first of {n} processes", "L": "part L, session {s}", "C": "part C", "I": "control I (added after the first numbers were seen)"}
2222      rows = ["7200 MT/s: first launch of every step of the rerun and of control I (added after the first numbers were seen)"]
2223      for tg in STEPS:
2224          l = LAUNCH[tg]
2225          w = what[l["part"]].format(s=l["session"], n=len({r["proc_key"] for r in sel(dataset="rerun-A", session=l["session"])}) if l["part"] == "A" else 0)
2226          if l["part"] == "C":
2227              w = "part C" + (f", session {l['session']}" if l["session"] else ", extra process")
2228          ld = f2(l["load1_at_first_launch"])
2229          if l["part"] == "A":
2230              used = sorted({(r["launch_utc"], r["proc_key"]): D(r["load1_at_launch"]) for r in A_OLD + A_NEW if r["session"] == l["session"]}.items())
2231              need(used[0][1] == D(l["load1_at_first_launch"]), "part A: the first read process is not the first launch of the step")
2232              ld += "&lt;br&gt;" + small(f"the {len(used)} read processes used: " + ", ".join(f2(v) for _, v in used))
2233          rows.append([tg, w, hms(l["first_launch"]), ld, "-" if l["gap_s"] is None else f"{int(l['gap_s'])}"])</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2771. No rate is used here. The table holds launch times and 1-minute load averages.</li><li>First group: one row per step of <code>STEPS</code> (line 880), from its entry in <code>LAUNCH</code>: the first launch, the load at that launch, and the seconds since the end of the previous 120-thread process.</li><li>For a part A step the text gives the number of processes of the session. Line 2225 counts the values of <code>proc_key</code> over all part A records of the session, with every kernel included.</li><li>For a part A step the load cell also lists the load at the launch of each <code>read</code> process that the page uses (<code>A_OLD</code> and <code>A_NEW</code> of the session), in launch order.</li><li>Line 2231 stops the script unless the first of these processes has the load of the first launch of the step.</li><li>In the page of the saved build, step T72A1 started at a load average of 0.07. The 9 later steps of the rerun started at load averages of 74.05 to 105.24, each 5 s after the previous 120-thread process. The 2 steps of control I started at load averages of 0.87 and 0.91.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2234      rows.append("Earlier rows shown on this page: launch of every process")
2235      rows.append(["F72d12", "earlier run of the same boot, not part of the rerun", hms(F_OLD[0]["launch_utc"]), f2(F_OLD[0]["load1_at_launch"]), "-"])
2236      for d, recs in (("A-1", B_A_OLD["A-1"] + B_A_NEW["A-1"]), ("A-2", B_A_OLD["A-2"] + B_A_NEW["A-2"]), ("A-3", B_A_OLD["A-3"]),
2237                      ("L-1", B_L_OLD["L-1"]), ("L-2", B_L_OLD["L-2"]), ("L-3", B_L_OLD["L-3"]), ("L-4", B_L_OLD["L-4"])):
2238          procs = {}
2239          for r in recs:
2240              procs[r["proc_key"]] = (r["launch_utc"], D(r["load1_at_launch"]))
2241          ps = sorted(procs.values())
2242          times = hms(ps[0][0], True) if len(ps) == 1 else f"{hms(ps[0][0], True)[:-4]} to {hms(ps[-1][0])}"
2243          rows.append([d, f"8000 MT/s, {plural(len(ps), 'process')}", times, ", ".join(f2(x[1]) for x in ps), "-"])
2244      span = lambda a, b: f"{hms(a, True)[:-4]} to {hms(b, True) if a[:10] != b[:10] else hms(b)}"
2245      for nm, heads, what_ in (("Runner bwx, tags common-6000-*", X_POOL_HEAD, "note under Table 2"), ("Runner bwx, tags b5-rev-*", X_REV_HEAD, "another kernel order, note under Table 2")):
2246          ls, ts = sorted(h["load"] for h in heads), sorted(h["launch"] for h in heads)
2247          rows.append([nm, f"8000 MT/s, {plural(len(heads), 'process')} ({what_})", span(ts[0], ts[-1]), f"{f2(ls[0])} to {f2(ls[-1])}&lt;br&gt;" + small("lowest to highest"), "-"])
2248      rows.append(["X2d12", "8000 MT/s, 12 modules, 1 process, shown and not used (note under Table 2)", hms(EXTRA["X2d12"]["old"][0]["launch_utc"], True), f2(EXTRA["X2d12"]["load"]), "-"])
2249      t10 = [EXTRA[d_] for d_ in ("X1d10", "X1d10b", "BASEd10")]
2250      rows.append(["Boots with 10 modules", f"8000 MT/s, {len(t10)} processes in {len(t10)} boots (note under Table 2)", span(t10[0]["old"][0]["launch_utc"], t10[-1]["old"][0]["launch_utc"]),
2251                   ", ".join(f2(x["load"]) for x in t10), "-"])
2252      return table(["Step or row", "What", "Launch", "#1-minute load average at launch", "#Time since the end of the previous 120-thread process of go.sh or go2.sh, s (given for their steps only)"], rows, "load")
2253
2254</pre></td><td valign="top"><ul><li>Second group: the earlier rows of the page. Line 2234 adds its title row <code>Earlier rows shown on this page: launch of every process</code>.</li><li>F72d12: the launch time and the load of its first oldread record.</li><li>Rows A-1 to A-3 and L-1 to L-4: one load per process (<code>proc_key</code>), in launch order. The launch cell holds the launch time of a single process, or the first and the last launch time of several processes. The records are those of the kernel <code>read</code> of both binaries (A-1, A-2), of bw_old (A-3), and the oldread records at position 0 (L-1 to L-4).</li><li>The two groups of the older runner bwx: the first and the last launch, and the lowest and the highest load, from the header facts of their processes (<code>X_POOL_HEAD</code>, <code>X_REV_HEAD</code>, lines 1259 and 1260).</li><li>X2d12: the launch time and the load from <code>EXTRA</code> (line 1299). The three boots with 10 modules share one row: the launch times of the first and of the last of the three processes, and one load per process.</li><li>Line 2252 returns the HTML table with 5 columns.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>detail_fig1</code>: table view of figure 1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2255  def detail_fig1():
2256      rows = []
2257      for b in F1_BLOCKS:
2258          for g in b["groups"]:
2259              rows.append(f"{b['title']} · {g['title'].split(' ·')[0]}")
2260              for r in g["rows"]:
2261                  rows.append([lab(esc(r["name"]), *[esc(n) for n in r["notes"]]),
2262                               f2(r["old"].med), ", ".join(f2(v) for v in r["old"].v), f2(r["new"].med), ", ".join(f2(v) for v in r["new"].v), drop_txt(r["drops"])])
2263      return table(["Row", "#Old read kernel: median, GB/s", "#Its intervals, GB/s", "#Load-only loop: median, GB/s", "#Its intervals, GB/s", "#Drop"], rows, "detail")
2264
2265</pre></td><td valign="top"><ul><li><code>build</code> calls it in line 2739. It writes one title row per block and group of <code>F1_BLOCKS</code> (line 1580), and one table row per row of figure 1.</li><li>The cells are: the row name with its notes, the median of the old read kernel, its interval rates, the median of the load-only loop, its interval rates, and the drop.</li><li>Medians and rates are printed with 2 decimals (<code>f2</code>). The interval rates stand in the order of <code>Rg.v</code>: by launch time, then by interval number.</li><li><code>drop_txt</code> (line 425) gives the lowest and the highest drop of the row with 1 decimal, or one value when both are printed equal.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>detail_fig2</code>: table view of figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2266  def detail_fig2():
2267      """Every interval of figure 2. A row carries the label that the figure shows, and each note once."""
2268      rows = []
2269      for nm, blocks in (("Old read kernel", P_OLD_BLOCKS), ("Load-only loop", P_NEW_BLOCKS)):
2270          for b in blocks:
2271              for g in b["groups"]:
2272                  rows.append(" · ".join([nm, b["title"], g["title"] + (", " + " ".join(g["sub"]) if g.get("sub") else "")]))
2273                  for r in g["rows"]:
2274                      rows.append([lab(esc(r["label"]), *[esc(n) for n in plain_notes(r["notes"])]), str(r["rg"].n), ", ".join(f2(v) for v in sorted(r["rg"].v))])
2275      return table(["Row", "#n intervals", "Intervals, GB/s, sorted"], rows, "detail")
2276
2277</pre></td><td valign="top">Builds the table <code>Table view of Figure 2: every interval</code> of the page. The page shows it folded: it stays closed until the reader opens it. It goes through the two panels (<code>P_OLD_BLOCKS</code> for the old read kernel, <code>P_NEW_BLOCKS</code> for the load-only loop). In each panel it goes through the blocks, the groups and the rows.<ul><li>Each group gets one title row: the panel name, the block title and the group title. The sub-title of the group (<code>g["sub"]</code>) follows when the group has one.</li><li>Each row of the figure gets one table row with three cells: the label of the row with its notes, the number of intervals (<code>rg.n</code>), and the rate of every interval of the row (<code>rg.v</code>).</li><li>These rates are the values of <code>val</code> for the records of the row. They are sorted from lowest to highest. <code>f2</code> rounds each one to 0.01 GB/s.</li><li>No rate is summed or averaged here.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>facts_words</code>: the word list of FACTS.md</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2278  # ------------------------------------------------------------------ word list
2279  def facts_words():
2280      m = re.search(r"&lt;summary&gt;Words used here&lt;/summary&gt;(.*?)&lt;/details&gt;", FMD, re.S)
2281      need(m, "FACTS.md: word list not found")
2282      out = {}
2283      for line in m.group(1).splitlines():
2284          k = re.match(r"^- \*\*(.+?)\*\*: (.*)$", line)
2285          if k:
2286              out[k.group(1)] = k.group(2)
2287      return out
2288
2289
2290  FW_WORDS = facts_words()
2291</pre></td><td valign="top">Finds in <code>FMD</code> (the text of FACTS.md) the part between <code>&lt;summary&gt;Words used here&lt;/summary&gt;</code> and the next <code>&lt;/details&gt;</code>. The script stops when this part is missing. Each line of the form <code>- **term**: definition</code> becomes one entry of the returned dictionary, from the term to its definition. Line 2290 stores the dictionary in <code>FW_WORDS</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>fw</code>: one definition, copied for the page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2292
2293  def fw(key, swap=()):
2294      """A definition of the word list of FACTS.md, reused word for word ("this sheet" becomes "this page").
2295      swap = (old, new): one phrase of the sheet that this page words in another way. The phrase must be present."""
2296      need(key in FW_WORDS, f"FACTS.md word list: term '{key}' not found")
2297      t = FW_WORDS[key]
2298      if swap:
2299          need(swap[0] in t, f"FACTS.md word list, term '{key}': phrase '{swap[0]}' not found")
2300          t = t.replace(swap[0], swap[1])
2301      t = re.sub(r"\s*\[Ref\d+\]", "", t).replace("this sheet", "this page").replace("This sheet", "This page")
2302      t = re.sub(r"`([^`]+)`", r"&lt;code&gt;\1&lt;/code&gt;", esc(t).replace("&amp;quot;", '"'))
2303      return t[0].upper() + t[1:]
2304</pre></td><td valign="top">Returns the definition of the term <code>key</code> from <code>FW_WORDS</code> as HTML text. The script stops when the term is missing.<ul><li><code>swap = (old, new)</code>: the phrase <code>old</code> is replaced by <code>new</code>. The script stops when <code>old</code> is not in the definition.</li><li>Marks of the form <code>[RefN]</code>, with a number in place of N, are removed. <code>this sheet</code> becomes <code>this page</code>.</li><li><code>esc</code> escapes the HTML special characters. The double quotes are then written back as plain characters.</li><li>A name between two backtick characters (the code marks of Markdown) becomes a <code>code</code> element.</li><li>The first letter becomes a capital letter.</li></ul></td></tr>
<tr><td colspan="2"><b>Part A: process counts for the word list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2305
2306  BOOT8 = RERUN["boot_id"][:8]
2307  # part A: how many processes a session ran, and how many of them this page uses (the scope cut is stated in the word list)
2308  A_ALL = sel(dataset="rerun-A")
2309  A_KERNELS = [k for k in ("read", "write", "copy", "asmread", "asmwrite", "asmcopy") if any(r["kernel"] == k for r in A_ALL)]
2310  A_PER_SESSION = sorted({len({r["proc_key"] for r in A_ALL if r["session"] == s_}) for s_ in (1, 2, 3)})
2311  A_USED_PER_SESSION = sorted({len({r["proc_key"] for r in A_OLD + A_NEW if r["session"] == s_}) for s_ in (1, 2, 3)})
2312  # part A: round 2 runs the processes of round 1 in the reverse order (launch order of session 1, by binary and kernel)
2313  a_order = {rnd: [k for k, _ in sorted({(r["binary"], r["kernel"]): r["launch_utc"] for r in A_ALL if r["session"] == 1 and r["round"] == rnd}.items(), key=lambda kv: kv[1])] for rnd in (1, 2)}
2314  need(len(a_order[1]) == 12 and a_order[2] == a_order[1][::-1], "part A, session 1: round 2 does not run the 12 processes of round 1 in the reverse order")
2315  need({r["kernel"] for r in A_ALL} == set(A_KERNELS) and {r["binary"] for r in A_ALL} == {"bw_old", "bw_new"} and {r["round"] for r in A_ALL} == {1, 2}
2316       and A_PER_SESSION == [len(A_KERNELS) * 2 * 2] and len(A_USED_PER_SESSION) == 1, "part A: a session is not kernels x 2 binaries x 2 rounds")</pre></td><td valign="top">These lines count the processes of part A. They read no rate. With the facts.json of this task they give 6 kernels, 24 processes per session and 4 used processes per session.<ul><li><code>BOOT8</code>: the first 8 characters of the boot id of the rerun.</li><li><code>A_ALL</code>: all records of the dataset <code>rerun-A</code>, with every kernel and both binaries. <code>A_KERNELS</code>: those of six kernel names that occur in <code>A_ALL</code>.</li><li><code>A_PER_SESSION</code>: the number of processes of each session (different values of <code>proc_key</code>), as a sorted list of the different counts. <code>A_USED_PER_SESSION</code>: the same for the read processes that the page uses (<code>A_OLD + A_NEW</code>).</li><li><code>a_order</code>: for session 1 and each round, the pairs (binary, kernel) in the order of their launch time. Line 2314 stops unless round 1 has 12 such pairs and round 2 has the same 12 in the reverse order.</li><li>Lines 2315 and 2316 stop unless part A holds only these kernels, the binaries <code>bw_old</code> and <code>bw_new</code>, and the rounds 1 and 2. The number of processes of every session must be the number of kernels x 2 x 2 (2 binaries, 2 rounds). With this data: 6 x 2 x 2 = 24. The number of used processes must be equal in all sessions.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2317  # names of argument lines that the tooltips of the earlier bwx12 rows show, and the tags of row A-3
2318  LINE_TAGS = sorted({r["tag"] for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]} | {r["tag"] for r in F_OLD + F_ASM})
2319  need(LINE_TAGS == sorted([LINE_L, "p1nop", "p2add", "thp", "st1", "st2", "st3"])
2320       and all(r["file"] == r["tag"] + ".csv" for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]), "rows L-1 to L-4 and F72d12: the tags are not the expected line names, or a csv file has another name")
2321  A3_TAGS = sorted({r["tag"] for r in B_A_OLD["A-3"]})
2322  need(A3_TAGS == [f"onebuf-ms500-{i}" for i in (1, 2, 3)], "row A-3: unexpected tags")</pre></td><td valign="top"><ul><li><code>LINE_TAGS</code>: the sorted tags of the records that the page uses from the rows L-1 to L-4 and from F72d12.</li><li>Lines 2319 and 2320 stop unless these tags are <code>LINE_L</code>, <code>p1nop</code>, <code>p2add</code>, <code>thp</code>, <code>st1</code>, <code>st2</code> and <code>st3</code>. <code>LINE_L</code> (line 1196) is the name of the argument line in <code>like.spec</code>. It is <code>a6456</code> in that file.</li><li>The same test also stops unless the csv file of each of these records of the rows L-1 to L-4 has the name of its tag plus <code>.csv</code>.</li><li><code>A3_TAGS</code>: the tags of row A-3. Line 2322 stops unless they are <code>onebuf-ms500-1</code> to <code>onebuf-ms500-3</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>List <code>WORDS</code>: the word list of the page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2323  WORDS = [
2324      ("Q1, Q2", "The two questions of the rerun. Q1: is the whole-chip read rate of the new read kernel still below that of the old read kernel at 7200 MT/s, and by how much. Q2: did the rate of either kernel differ from the earlier runs at 8000 MT/s."),
2325      ("Rerun", f"The {GO_DONE} steps that go.sh ran at 7200 MT/s on 2026-11-17 from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC: 3 sessions of parts A, L and C, and one more part C process. "
2326                "Parts A and L repeat tests that ran earlier at 8000 MT/s. Part C is new. No earlier run in the results folder used one of its two argument lines. "
2327                f"Runs of the older runner bwx timed the same three kernels in both orders inside a longer sequence of {len(X_SEQ)} kernels (note under Table 2). "
2328                "Control I (added after the first numbers were seen) and F72d12 (earlier run of the same boot) are not part of the rerun."),</pre></td><td valign="top"><code>WORDS</code> is a list of pairs (term, definition). <code>build</code> (line 2677) writes it into the folded part <code>Words used here</code> of the page. These lines hold the first two entries.<ul><li>The entry <code>Q1, Q2</code> is typed. Typed means fixed text in the source, not a computed value.</li><li>The entry <code>Rerun</code> takes four values from the data. The next three bullets name them.</li><li><code>GO_DONE</code> (line 874): the number of <code>done</code> lines in the log of go.sh. Line 875 asserts that it is 10.</li><li>The start time and the end time of go.sh from <code>RERUN</code>. The slice <code>[11:19]</code> takes the time of day <code>HH:MM:SS</code> from the time stamp.</li><li><code>len(X_SEQ)</code> (line 1279): the number of kernels in the sequence of the older runner bwx. Line 1280 asserts that it is 8.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2329      ("CRB", fw("CRB")),
2330      ("Whole chip, 120 threads", "The runs use 120 threads on CPUs 0-119 only. Each thread reads its own buffer of 256 MiB from memory (1 MiB is 2^20 bytes)."),
2331      ("MT/s", fw("MT/s")),
2332      ("Memory module", "One DIMM (dual in-line memory module). CRB has 12 slots for them."),
2333      ("GB/s", "Gigabytes per second. 1 GB is 1e9 bytes."),
2334      ("Read kernel", fw("Read kernel")),
2335      ("Old read kernel", fw("Old read kernel")),
2336      ("New read kernel", fw("New read kernel")),
2337      ("asmread", fw("asmread")),
2338      ("Load-only loop", fw("Load-only loop")),
2339      ("bandwidth.c, bw_old, bw_new", fw("bandwidth.c, bw_old, bw_new")),
2340      ("bwx12, bwx11, bwx", fw("bwx12, bwx11, bwx", ("bwx12 is the runner of the 2026-11-15 investigation.",
2341                                                      "bwx12 is the runner of the investigation of 2026-11-15 into the lower read rate of the load-only loop."))),</pre></td><td valign="top">Entries for the machine and for the kernels.<ul><li>A call of <code>fw</code> copies the definition from FACTS.md.</li><li>The entries <code>Whole chip, 120 threads</code>, <code>Memory module</code> and <code>GB/s</code> are typed here.</li><li>The entry <code>GB/s</code> states the unit of every rate of the page: 1 GB is 1e9 bytes.</li><li>For <code>bwx12, bwx11, bwx</code> the <code>swap</code> argument replaces one sentence of the FACTS.md text by a longer one.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2342      ("Process, interval, round, position", "A process is one start of a benchmark binary. An interval is one timed measurement inside a process. "
2343                                             "bwx12 times a sequence of kernels and repeats the sequence. Each repeat is a round (counted from 0). "
2344                                             "The position is the place of a kernel in the sequence (counted from 0). "
2345                                             f"In part A the script runs its {A_PER_SESSION[0] // 2} read, write and copy processes twice. Each run is a round (1 or 2). Round 2 runs the processes in the reverse order."),
2346      ("Rate", fw("Rate, total", ("bwx runners", "bwx12 and bwx"))),
2347      ("Interval row, thread rows", "bwx12 and bwx write two kinds of row into a csv file that this page uses. An interval row starts with the letter I and holds one interval. "
2348                                    "A thread row starts with the letter T and holds one thread of one interval. The 120 thread rows of an interval follow its interval row."),
2349      ("Median", "The middle value of a sorted list. For an even number of values it is the mean of the two middle values."),
2350      ("Facts sheet", "The file FACTS.md with its data file facts.json. It is the detailed record of this rerun. A script built it from the raw result files."),
2351      ("R, S", "Short forms of two folders: R is the results folder, and S is the scratch folder of this rerun. The reference list gives both paths."),
2352      ("Session, step", fw("Session") + " go.sh ran 3 sessions and then one more part C process (T72C4). The n column calls T72C4 the extra process. "
2353                        "A step is one part of one session, the extra part C process, or one process of control I (added after the first numbers were seen)."),
2354      ("go.sh, go2.sh", "The driver scripts. go.sh ran the planned rerun. go2.sh ran control I (added after the first numbers were seen)."),
2355      ("Part A", fw("Part A") + f" Each session ran {A_PER_SESSION[0]} processes: {len(A_KERNELS)} kernels ({', '.join(A_KERNELS)}) x 2 binaries x 2 rounds. "
2356                 f"This page uses the {A_USED_PER_SESSION[0]} read processes of each session. The facts sheet holds the other {A_PER_SESSION[0] - A_USED_PER_SESSION[0]} (its sections 3.1 and 5) {ref('facts')}."),</pre></td><td valign="top">Entries for the method. These matter for the rates:<ul><li><code>Rate</code> (line 2346) is copied from the FACTS.md entry <code>Rate, total</code>. It says how the page gets a rate. Part A: the column <code>aggregate_GBps</code> that bandwidth.c prints. bwx12 and bwx: the sum over the threads of bytes / elapsed time. The unit is GB/s.</li><li><code>Interval row, thread rows</code> (lines 2347 and 2348) says that the 120 thread rows of an interval follow its interval row.</li><li><code>Part A</code> (lines 2355 and 2356) prints the counts of lines 2309 to 2311: the processes per session, the kernel names, and the read processes that the page uses. It prints the difference as the number of the other processes, which the facts sheet holds. With this data: 24, 4 and 20 processes.</li><li>Line 2345 prints <code>A_PER_SESSION[0] // 2</code>: the number of processes of one round (12 with this data).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2357      ("Part L", "One bwx12 process that times oldread, then asmread, then three other test loops that this page does not use. The process runs this sequence twice (rounds 0 and 1)."),
2358      ("Part C, cfwd, crev, kernel order", fw("Part C") + " Each process runs its sequence twice (rounds 0 and 1). The kernel order is the order of the kernels in this sequence."),
2359      ("Control I", fw("Control I")),
2360      ("F72d12", "One process of the part L line. It ran at " + hm(F_OLD[0]["launch_utc"]) + " on 2026-11-17 for another test, in the same boot as the rerun and before it. It is not part of the rerun."),
2361      ("T72A1 to T72I2", "The names of the result folders of the rerun (parts A, L, C) and of control I (I, added after the first numbers were seen): T72, then the letter, then a number."),
2362      ("A-1, A-2, A-3", "The 8000 MT/s rows for part A, all of 2026-11-13, with the same two binaries. A-1 is the original test. A-2 is a second run with another process order. A-3 is three more processes of bw_old read."),
2363      ("L-1, L-2, L-3, L-4", "The 8000 MT/s rows for parts L and C, all with bwx12. L-1 (2026-11-17) used the argument line of part L unchanged. L-2 to L-4 (2026-11-15) used 4 s measurements and counted other hardware events of the CPU. From these rows only oldread at position 0 and asmread at position 1 are used."),
2364      (", ".join(LINE_TAGS), f"Names of argument lines. In the rows L-1 to L-4 and in F72d12 (earlier run of the same boot, not part of the rerun) a bwx12 process carries the name of its line, and so does its csv file. "
2365                             f"A tooltip names such a process by this name. {LINE_L} is the part L line."),
2366      (f"{A3_TAGS[0]} to {A3_TAGS[-1]}", "The tags that the csv file of row A-3 gives its three processes."),</pre></td><td valign="top">Entries for the parts and for the earlier rows. The first two bullets name values from the data. The last two bullets name entries that say which intervals the page uses.<ul><li><code>F72d12</code>: the launch time of the first record of <code>F_OLD</code>. <code>hm</code> (line 377) writes it as <code>HH:MM UTC</code>.</li><li>The entry of lines 2364 and 2365 has the tags of <code>LINE_TAGS</code> as its term. The entry of line 2366 names the first and the last tag of row A-3.</li><li>The entry <code>L-1, L-2, L-3, L-4</code> (line 2363) states which intervals the page takes from these rows: only <code>oldread</code> at position 0 and <code>asmread</code> at position 1. Lines 291 and 292 make this selection.</li><li>The entry <code>Part L</code> (line 2357) says that the page does not use the three other test loops of a part L process. Lines 275 and 276 select only <code>oldread</code> at position 0 and <code>asmread</code> at position 1 from part L.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2367      ("Line, argument line, spec file", fw("Line, argument line") + " A spec file is a text file with one argument line."),
2368      ("Visit", fw("Visit")),
2369      ("Idle start", fw("Idle start")),
2370      ("Whole-pass stop", fw("Whole-pass stop")),
2371      ("Pass count", "Part A only: the number of buffer passes that all 120 threads completed in one interval."),
2372      ("Pair, drop", "A pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A the two kernels run in two processes. There the drop uses the medians of the two processes of one session and round."),
2373      ("List of 8000 MT/s rows", "The 8000 MT/s runs with 12 modules that this page compares with: rows A-1 to A-3 and L-1 to L-4. The rules file fixed them before the run. "
2374                                 "The rules file also names rows of two older runner binaries (bwx11 and bwx). This page does not use the bwx11 rows. It shows the bwx rows in one note under Table 2 only. "
2375                                 "Two more notes under Table 2 show rows that the rules file names and that are not rows of the list: row X2d12, and three boots with 10 modules. No wording comes from them."),
2376      ("Pool", fw("Pool")),
2377      ("Overlap of two ranges", fw("Ranges overlap")),
2378      ("Distance of the nearest ends, farthest ends", fw("Distance of the nearest ends") + " The distance of the farthest ends is the highest value of the higher range minus the lowest value of the lower range."),
2379      ("n", fw("n")),
2380      ("Rules V1 to V4, F1, F2", fw("Rules V1 to V4, F1, F2")),
2381      ("Boot, boot id", f"A boot is one run of the machine from a start to the next restart. The boot id is a random identifier that Linux creates at each start. Equal boot ids mean the same boot. The rerun ran in boot {BOOT8} (the first 8 characters of its boot id)."),
2382      ("MemTotal", fw("MemTotal")),
2383      ("State line", fw("State line")),
2384      ("Load average, load", fw("Load average")),
2385      ("%CPU, process list", "A process list is the output of the tool ps that a run script saves before a launch. "
2386                             + fw("%CPU", ("the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is", "%CPU is the column pcpu of this output. It is"))),
2387      ("pr/ttyAMA-1", fw("pr/ttyAMA-1", ("By its name it prints kernel messages", "Its name suggests that it prints Linux kernel messages"))),
2388      ("Exit status", "The number that a process returns when it ends. 0 means success."),
2389      ("Root", "Administrator rights on the machine. They were not approved for this task."),
2390      ("Journal, kernel log", "The kernel log is the list of messages of the Linux kernel. The journal is the saved system log of one boot. It holds the kernel log."),
2391      ("Hardware error record, corrected record", fw("Hardware error record")),
2392      ("Module list", "The output of the command &lt;code&gt;dmidecode -t 17&lt;/code&gt;. It holds one entry &amp;quot;Memory Device&amp;quot; per memory module, with the configured speed of the module."),
2393      ("Firmware setting, DIMM Frequency, TXREQ", "A firmware setting is a value that the machine applies at its next start. &amp;quot;DIMM Frequency&amp;quot; sets the memory speed. TXREQ is a group of settings that were changed for another investigation."),
2394      ("GiB", "2^30 bytes."),
2395      ("est.", fw("est.")),
2396  ]
2397</pre></td><td valign="top">The other entries. Most are copied with <code>fw</code>, some with a changed phrase. The first three bullets name entries that state how the page compares rates. The last bullet names the one entry of these lines with a value from the data.<ul><li><code>Pair, drop</code> (line 2372): the drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A it uses the medians of the two processes of one session and round. This is the computation of <code>drop</code> (line 417) and of <code>a_pair</code> (line 444).</li><li><code>Pool</code>, <code>Overlap of two ranges</code> and <code>Distance of the nearest ends, farthest ends</code> give the terms of the comparison with the 8000 MT/s rows.</li><li><code>List of 8000 MT/s rows</code> (lines 2373 to 2375) names what the page leaves out. The bwx11 rows are not used. The rates of the bwx rows, of row X2d12 and of the three boots with 10 modules appear in notes under Table 2 only. Tables 5 and 6 name these rows and print no rate of them.</li><li><code>Boot, boot id</code> (line 2381) prints <code>BOOT8</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>nw</code>: a number that stays on one line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2398  # ------------------------------------------------------------------ text of the page
2399  def nw(text):
2400      """A number with its unit that must not break across two lines."""
2401      return f'&lt;span class="num"&gt;{text}&lt;/span&gt;'
2402
2403</pre></td><td valign="top">Wraps a text in a <code>span</code> element of the class <code>num</code>. The style block (line 2638) keeps such a text on one line.</td></tr>
<tr><td colspan="2"><b>Short version: tests before the three sentences</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2404  OLD_PARTS = [(rA_old, rPA_old), (rC_old, rPL_old), (rL_old, rPL_old)]          # old read kernel: parts A, C, L of the rerun
2405  need([a.overlaps(b) for a, b in OLD_PARTS] == [True, True, False], "Short version: the old read kernel does not overlap in parts A and C, with part L as the third part")
2406  c_ao, c_aa = Q1["C_ao"]["drops"], Q1["C_aa"]["drops"]
2407  need(only((r["kernel_before"] for r in C_READ_AA), "kernel before") == "asmread", "part C, second order: read does not follow asmread")
2408  need(VISIT_LO == rF_asm.lo and VISIT_HI == rL_asm.hi, "the span of the three visits does not run from F72d12 to part L")
2409  need(len(c_ao) == len(c_aa), "part C: the two kernel orders have different numbers of pairs")
2410  c_all = c_ao + c_aa</pre></td><td valign="top"><ul><li><code>OLD_PARTS</code>: three pairs of ranges for the old read kernel. Each pair is a 7200 MT/s range and its 8000 MT/s range: part A with the pool A-1 to A-3, part C with the pool L-1 to L-4, part L with the same pool.</li><li>Line 2405 stops unless the three overlap results are true, true, false. Sentence 2 of the Short version states this result.</li><li><code>c_ao</code>, <code>c_aa</code>: the drops of part C in percent, computed in lines 431 to 439. <code>c_ao</code> holds the drops of the 4 pairs with <code>read</code> directly after <code>oldread</code>. <code>c_aa</code> holds the drops of the 4 pairs with <code>read</code> directly after <code>asmread</code>.</li><li>Line 2407 stops unless every record of <code>C_READ_AA</code> has <code>asmread</code> as its <code>kernel_before</code>.</li><li>Line 2408 stops unless <code>VISIT_LO</code> is the lowest asmread rate of F72d12 and <code>VISIT_HI</code> is the highest asmread rate of part L.</li><li>Line 2409 stops unless both orders have the same number of pairs. <code>c_all</code> joins the two lists: 8 drops.</li></ul></td></tr>
<tr><td colspan="2"><b><code>SHORT</code>: the three sentences of the Short version</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2411  SHORT = [
2412      f"At 7200 MT/s with 12 memory modules, the new read kernel (a benchmark loop with loads only) still read {nw(f1(min(c_all)) + ' %')} to {nw(f1(max(c_all)) + ' %')} less than the "
2413      f"old read kernel (each load is followed by an add) in {len(c_all)} pairs of 6 s measurements.",
2414      "For the old read kernel, no difference from the earlier 8000 MT/s runs was seen in two of the three tests (parts A and C), "
2415      f"and in the third (part L) it was lower by {nw(f1(L_OLD_NEAR_PCT) + ' %')} (nearest ends of the two ranges) and {nw(f1(L_OLD_MED_PCT) + ' %')} (medians).",
2416      f"The load-only loop gave higher rates than these 8000 MT/s runs in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2), "
2417      "and the data do not show that the memory speed caused either difference.",
2418  ]</pre></td><td valign="top">The three sentences hold percent values and counts. They hold no rate in GB/s.<ul><li><b>Sentence 1</b> prints <code>min(c_all)</code> and <code>max(c_all)</code>: the lowest and the highest drop of the 8 pairs of part C. A pair is one interval of the bwx12 kernel <code>read</code> (the new read kernel) and the <code>oldread</code> interval of the same process and round. Its drop is (1 - rate of <code>read</code> / rate of <code>oldread</code>) x 100.</li><li>Both rates are values of <code>val</code>: the sum of bytes / elapsed_s / 1e9 over the 120 thread rows of the interval (line 186), kept with 6 decimals. <code>f1</code> rounds a drop to 0.1 % only when it is printed.</li><li><code>len(c_all)</code> prints the number of pairs. The words <code>6 s measurements</code> are typed. Line 317 asserts a <code>min_ms</code> of 6000 (6 s) for these records.</li><li><b>Sentence 2</b> prints <code>L_OLD_NEAR_PCT</code> (line 491) and <code>L_OLD_MED_PCT</code> (line 492) for the old read kernel in part L. The first is the distance of the nearest ends in percent of the lower end of the 8000 MT/s range. The second is the difference of the medians in percent of the 8000 MT/s median.</li><li><b>Sentence 3</b> prints <code>len(RERUN_CMP_NEW)</code> (line 2066): the number of comparisons of the load-only loop of the rerun with 8000 MT/s rows. Line 2068 stops unless the 7200 MT/s range lies above the 8000 MT/s range in each of them.</li><li>The saved output of a build shows 29.7 % to 31.2 % in 8 pairs, then 0.3 % and 1.3 %, then 4 comparisons [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2419  need(n7200(L_OLD) == n7200(L_ASM) and n8000(P_L_OLD) == n8000(P_L_ASM), "Short version, part L: n differs between the two kernels")
2420  # Table 2 holds load-only comparisons that are not part of the rerun (F72d12 lies inside the 8000 MT/s range). So the count of sentence 3 must name its scope.
2421  need(f"in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2)" in SHORT[2], "Short version, sentence 3: the count of comparisons does not name the rerun as its scope")
2422  need(rPL_asm.lo &lt;= rF_asm.lo and rF_asm.hi &lt;= rPL_asm.hi and rF_asm.hi &lt; rL_asm.lo, "Short version: F72d12 is not inside the 8000 MT/s range and below part L")</pre></td><td valign="top">Three more tests of the sentences. Each one is a <code>need</code> call. The script stops when one of them fails.<ul><li>Line 2419: the text of n of part L must be equal for <code>oldread</code> and <code>asmread</code>. The same holds for the pool L-1 to L-4. Line 2426 prints one n for both kernels.</li><li>Line 2421: sentence 3 must hold the phrase <code>in all N comparisons of the rerun (Table 2)</code>, with N from <code>RERUN_CMP_NEW</code>. Line 2416 types the same phrase. So this test can fail only after an edit of that line.</li><li>Line 2422: the asmread range of F72d12 must lie inside the range of the 8000 MT/s pool. Its highest value must be below the lowest asmread value of part L.</li></ul></td></tr>
<tr><td colspan="2"><b><code>SHORT_MORE</code>: five items under the Short version</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2423  SHORT_MORE = UL([
2424      f"Sentence 1 (part C): {f1(min(c_ao))} % to {f1(max(c_ao))} % lower when the new read kernel ran directly after the old read kernel, "
2425      f"and {f1(min(c_aa))} % to {f1(max(c_aa))} % lower directly after asmread, a hand-written loop with the same loads ({len(c_ao)} pairs / 2 processes each).",
2426      f"Part L (sentences 2 and 3), 7200 MT/s against 8000 MT/s: n = {n7200(L_OLD)} against {n8000(P_L_OLD)}. A boot is one run of the machine between two restarts. "
2427      f"Old read kernel: {rL_old.txt()} against {rPL_old.txt()} GB/s. It was lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends "
2428      f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_NEAR_PCT)} % and {f1(L_OLD_MED_PCT)} % of the 8000 MT/s values). The data do not show the cause. "
2429      f"Load-only loop (asmread in place of the new read kernel): {rL_asm.txt()} against {rPL_asm.txt()} GB/s.",
2430      f"Parts A and C (sentence 2): the tests cannot exclude a difference of about {f1(width_pct(rPA_old))} % and {f1(width_pct(rPL_old))} % (est.). Table 2 gives the ranges and n.",
2431      "Part C (sentences 2 and 3): the rules fixed before the run contradict each other on whether part C is compared with the 8000 MT/s runs. This page compares it. "
2432      f"That choice was made after the numbers were seen (note under Table 2). Without part C, sentence 2 keeps parts A and L, and sentence 3 keeps {len(RERUN_CMP_NEW) - RERUN_CMP_C} of its {len(RERUN_CMP_NEW)} comparisons.",
2433      f"Sentence 3: the comparison uses 1 boot per memory speed. {F72} ran the argument line of part L. Its asmread gave {rF_asm.txt()} GB/s ({n7200(F_ASM)}). "
2434      f"That is inside the 8000 MT/s range. It is {f2(abs(DIST['nearest'][1]))} GB/s below part L at the nearest ends.",
2435  ])
2436</pre></td><td valign="top"><code>UL</code> (line 1493) returns an HTML bullet list and adds its items to <code>PROSE</code> for the word count. The five items print these computed values:<ul><li>Item 1: the lowest and the highest drop of <code>c_ao</code> and of <code>c_aa</code>, each with 1 decimal, and the number of pairs per order.</li><li>Item 2, part L: n at 7200 MT/s and at 8000 MT/s. For the old read kernel it prints the two ranges (<code>rL_old</code>, <code>rPL_old</code>), the distance of the nearest ends <code>abs(L_OLD_NEAR)</code> and the difference of the medians <code>abs(L_OLD_MED)</code> in GB/s, and both in percent. For asmread it prints the two ranges (<code>rL_asm</code>, <code>rPL_asm</code>).</li><li>Item 3: <code>width_pct</code> (line 476) of the two 8000 MT/s ranges of the old read kernel. It is the width of a range in percent of its lower end. The page marks it <code>est.</code>.</li><li>Item 4: <code>len(RERUN_CMP_NEW) - RERUN_CMP_C</code>, the number of comparisons that stay without part C. <code>RERUN_CMP_C</code> is the constant 1 of line 2067.</li><li>Item 5: the asmread range of F72d12, its n, and <code>abs(DIST['nearest'][1])</code>. This is the distance of the nearest ends between part L and F72d12 (line 504).</li><li>A range text comes from <code>Rg.txt</code> (line 204): the lowest and the highest rate, each rounded to 0.01 GB/s by <code>f2</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Pair counts for section 1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2437  l1d = Q1["L1"]["drops"]
2438  GO_SECS = secs(RERUN["go_end"][11:19]) - secs(RERUN["go_start"][11:19])
2439  N_RERUN_PAIRS = (len(c_ao) + len(c_aa), len(Q1["L"]["drops"]), len(Q1["A"]["drops"]))
2440  need(sum(N_RERUN_PAIRS) + len(Q1["I"]["drops"]) + len(Q1["F"]["drops"]) == len(ALL_7200_DROPS), "pair counts of the 7200 MT/s rows")
2441  # part C holds asmread too: its pairs with oldread of the same process and round (Table 1 does not show them)
2442  C_ASM_DROPS = drops_of(pairs_in_process(C_OLD, C_ASM))
2443  need(len(C_ASM_DROPS) == 8 and all(d &gt; 0 for d in C_ASM_DROPS), "part C: not 8 asmread pairs, or asmread is not below oldread in a pair")</pre></td><td valign="top"><ul><li><code>l1d</code>: the drops of the 2 pairs of row L-1 (8000 MT/s).</li><li><code>GO_SECS</code>: the run time of go.sh in seconds. It is the end time of day minus the start time of day (<code>secs</code>, line 983).</li><li><code>N_RERUN_PAIRS</code>: the numbers of pairs of part C, part L and part A. For part A a pair is a pair of process medians. With this data: 8, 6 and 6 pairs.</li><li>Line 2440 stops unless these numbers plus the pairs of control I and of F72d12 give the length of <code>ALL_7200_DROPS</code> (line 459).</li><li><code>C_ASM_DROPS</code>: part C times asmread too. <code>pairs_in_process</code> pairs each asmread interval of part C with the <code>oldread</code> interval of the same process and round. <code>drops_of</code> computes the drop of each pair.</li><li>Line 2443 stops unless there are 8 such drops and each one is above 0. The page uses only their number, in the caption of Table 1 (line 2735).</li></ul></td></tr>
<tr><td colspan="2"><b>Text of section 1 (question Q1)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2444  SEC1_INTRO = UL([
2445      f"The rerun ran parts A, L and C three times (three sessions) and then part C once more, from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC, all in boot {BOOT8} {ref('go', 'golog')}.",
2446      f"Part A repeats the 120-thread part of the test of 2026-11-13 with the same two binaries {ref('ra')}. "
2447      f"With its whole-pass stop the pass count of an interval changes by whole passes, and the rate changes with it. So part A is less exact than parts L and C {ref('facts')}.",
2448      f"Part C runs the new read kernel itself {ref('cfwd', 'crev')}. Part L runs asmread in its place {ref('like')}.",
2449      f"This page does not examine why the load-only loop is lower. The investigation of 2026-11-15 examined it and did not establish the cause {ref('earlier')}.",
2450  ])
2451  SEC1_AFTER = UL([
2452      f"The drop is not one fixed value. The same argument line gave {drop_txt(Q1['L']['drops'])} in part L, {drop_txt(Q1['I']['drops'])} in {CI} and {drop_txt(Q1['F']['drops'])} in {F72}, "
2453      "all inside the one 7200 MT/s boot.",
2454      f"At 8000 MT/s the same line gave {drop_txt(l1d)} (row L-1). The data do not show that the smaller drop of the rerun is an effect of the memory speed (section 2).",
2455  ])</pre></td><td valign="top"><code>SEC1_INTRO</code> and <code>SEC1_AFTER</code> are the bullet lists before and after figure 1 and Table 1. Their computed values:<ul><li>The start time and the end time of go.sh, and <code>BOOT8</code>.</li><li><code>drop_txt</code> (line 425) of the drops of part L, of control I and of F72d12. It prints the lowest and the highest drop with 1 decimal. It prints one value when both print equal.</li><li><code>drop_txt(l1d)</code>: the same for row L-1 at 8000 MT/s. The page file on disk (<code>OUT</code>, line 31) shows 35.9 % to 36.1 % for it.</li><li>The saved output of a build shows 29.2 % to 30.5 % for part L, 31.9 % to 32.8 % for control I and 35.4 % for F72d12 [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b>Text of section 2 (question Q2)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2456  SEC2_INTRO = UL([
2457      f"The comparison rules and the list of 8000 MT/s rows were fixed before the run {ref('rules')}. A rule compares the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s rows.",
2458      f"Overlap: &amp;quot;{WORD_SAME}&amp;quot;. The width of the 8000 MT/s range is then the size that the test cannot exclude (est.).",
2459      f"No overlap: &amp;quot;{WORD_DIFF}&amp;quot;.",
2460      "The comparison uses exactly 1 boot per memory speed. So a difference between the two boots is not shown to be an effect of the memory speed.",
2461  ])
2462  SEC2_BOOT = UL([
2463      f"The part L line ran in three visits of the 7200 MT/s boot (Table 3): {F72}, part L, and {CI}.",
2464      f"The three asmread ranges do not overlap each other. Together they span {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s ({f2(VISIT_HI - VISIT_LO)} GB/s).",
2465      "The three visits did not start from the same state. The data do not show which difference changed the rate.",
2466  ])</pre></td><td valign="top"><ul><li><code>SEC2_INTRO</code> states the comparison rule. The rule compares the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s rows.</li><li><code>SEC2_INTRO</code> then gives the fixed wording of each result. For an overlap it is <code>WORD_SAME</code> (line 470): <code>no difference seen</code>. For no overlap it is <code>WORD_DIFF</code> (line 471).</li><li>Table 2 has two rows without an overlap that do not hold <code>WORD_DIFF</code>. They are the part A rows of the new read kernel. Line 2107 writes <code>outside (above) the 8000 MT/s range of the same round</code> there.</li><li><code>SEC2_BOOT</code> prints <code>VISIT_LO</code> and <code>VISIT_HI</code> (line 501): the lowest and the highest asmread rate of the three visits of the part L line in the 7200 MT/s boot. It also prints their difference.</li><li>The saved output of a build shows 301.90 to 327.93 GB/s and a difference of 26.03 GB/s [Ref5].</li></ul></td></tr>
<tr><td colspan="2"><b><code>INSUFF</code>: text of section 3</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2467  INSUFF = UL([
2468      "Insufficient data: whether a difference of the new read kernel comes from the memory speed. Runs in several boots per speed would resolve it (needs reboots and a change of the firmware setting).",
2469      "Insufficient data: why the rate of the load-only loop changed between the three visits of the one 7200 MT/s boot (Table 3). "
2470      "Two measurements would resolve it. First: run the part L line alternately from an idle start and directly after part A, at least 3 times each in one boot. "
2471      "Second: repeat the idle-start line some hours later in the same boot, and once directly after a reboot (needs approval).",
2472      "Insufficient data: why the old read kernel was lower in part L. The first of these two measurements would resolve it.",
2473      "Insufficient data: no 8000 MT/s run of kernel read with bwx12. A run of the two part C lines at 8000 MT/s would resolve it (needs a firmware change and a reboot).",
2474      "Insufficient data: whether hardware error records occurred during the rerun. A count of the &amp;quot;[Hardware Error]&amp;quot; lines of the kernel log would resolve it (needs root, which was not approved for this task).",
2475      "Insufficient data: a direct reading of the memory speed during the rerun. A module list read during the rerun would resolve it. "
2476      "The command &lt;code&gt;sudo dmidecode -t 17&lt;/code&gt; prints this list (needs root).",
2477  ])</pre></td><td valign="top">Six typed items for the page section <code>What the data do not show</code>. Each one names a point that the data do not show, and the measurement that would resolve it. No computed value is printed here.</td></tr>
<tr><td colspan="2"><b>Load at launch: facts for Table 6 and for figure 2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2478  go_first = LAUNCH["T72A1"]
2479  others = [LAUNCH[t]["load1_at_first_launch"] for t in STEPS[1:10]]
2480  need(all(LAUNCH[t]["gap_s"] == 5 for t in STEPS[1:10]), "a step of go.sh did not start 5 s after the previous process")
2481  need(LAUNCH["T72A1"]["gap_s"] is None, "T72A1 is not the first step")
2482  need(D(go_first["load1_at_first_launch"]) &lt; 1, "the first launch of the rerun is not an idle start")
2483
2484</pre></td><td valign="top"><ul><li><code>go_first</code>: the entry of <code>meta.launches</code> for the first step, T72A1.</li><li><code>others</code>: the 1-minute load average at the first launch of the steps 2 to 10 of go.sh (<code>STEPS[1:10]</code>, T72L1 to T72C4).</li><li>Line 2480 stops unless each of these 9 steps has a <code>gap_s</code> of 5. Table 6 prints this field as the time in seconds since the end of the previous 120-thread process (line 2252).</li><li>Line 2481 stops unless T72A1 has no gap. Line 2482 stops unless its load average was below 1 (an idle start).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2485  # reading notes of figure 2: the start of part A in sessions 2 and 3, and the load at the first launch of session 1 and of rows A-1 and A-2
2486  need(all(LAUNCH[t]["gap_s"] == 5 and "120-thread bwx12 process T72C" in LAUNCH[t]["start_state"] for t in ("T72A2", "T72A3")), "part A, sessions 2 and 3: not started 5 s after a part C process")
2487  A_FIRST_LOAD = {"T72A1": D(go_first["load1_at_first_launch"])}
2488  for d_ in ("A-1", "A-2"):
2489      first = min(sel(dataset=d_), key=lambda r: r["launch_utc"])
2490      need(first in B_A_OLD[d_] and first["_fproc"] == 1 and first["round"] == 1, f"{d_}: the first process of the file is not a read process that this page uses")
2491      A_FIRST_LOAD[d_] = D(first["load1_at_launch"])
2492  need(all(v &lt; 2 for v in A_FIRST_LOAD.values()), "session 1, A-1 or A-2: the first process did not start at a low load average")
2493  a_sess_n = {(len(x), len({r["proc_key"] for r in x})) for x in ([r for r in A_OLD if r["session"] == s_] for s_ in (1, 2, 3))}
2494  need(a_sess_n == {(6, 2)}, "part A, old read kernel: a session does not have 6 intervals of 2 processes")
2495  A_SESSION_N = "6 intervals / 2 processes / 1 session / 1 boot"
2496</pre></td><td valign="top">Facts for the reading notes under figure 2 (the list <code>how2</code>, line 2684).<ul><li>Line 2486 stops unless part A of sessions 2 and 3 started 5 s after a part C process. The test reads <code>gap_s</code> and the text <code>start_state</code> of the two entries of <code>LAUNCH</code>.</li><li><code>A_FIRST_LOAD</code>: the 1-minute load average at the first launch of T72A1 and of the rows A-1 and A-2. For a row, <code>first</code> is the record with the earliest launch time of the whole dataset.</li><li>Line 2490 stops unless <code>first</code> is a <code>bw_old</code> read record that the page uses, from the first process of its csv file, in round 1.</li><li>Line 2492 stops unless the three load values are below 2.</li><li><code>a_sess_n</code>: for each session of <code>A_OLD</code>, the number of intervals and the number of processes. Line 2494 stops unless every session has 6 intervals of 2 processes. <code>A_SESSION_N</code> is the typed text of this n.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>cl</code>: bullet list inside a table cell</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2497
2498  def cl(*items):
2499      """A list inside one table cell: one point per bullet."""
2500      return '&lt;ul class="cl"&gt;' + "".join(f"&lt;li&gt;{x}&lt;/li&gt;" for x in items) + "&lt;/ul&gt;"
2501
2502</pre></td><td valign="top">Returns an HTML list of the class <code>cl</code> with one item per argument.</td></tr>
<tr><td colspan="2"><b>Function <code>state_table</code>: Table 5, the machine state</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2503  def state_table():
2504      hw_refs = ref("journal", "L-1l", "L-2l", "L-3l", "L-4l")
2505      low_day = LOWEST_ASM["launch_utc"][:10]
2506      need(HW_LOW[0]["ts"][:10] == low_day == "2026-11-15", "the lowest asmread interval of the pool is not of 2026-11-15")</pre></td><td valign="top">Builds Table 5 of the page section <code>Machine state and system load</code>. Each row has three cells: a fact, its proof and its limit.<ul><li><code>LOWEST_ASM</code> (line 520) is the record with the lowest asmread rate of the pool L-1 to L-4. <code>low_day</code> is the date of its launch.</li><li>Line 2506 stops unless the first hardware error record of that interval (<code>HW_LOW</code>, line 1031) has the same date, and the date is 2026-11-15.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2507      rows = [
2508          ["12 memory modules during the rerun",
2509           cl(f"MemTotal is {RERUN['memtotal_kB']} kB in all {len(ST_ALL)} state lines of the two run logs {ref('golog', 'go2log')}.",
2510              f"The record of this boot (a file written at {TRY6_UTC[11:19]} UTC) holds the same value. It also holds the kernel log line &amp;quot;This system has 12 DIMM sockets&amp;quot; "
2511              f"and the count 12 of the lines &amp;quot;Configured Memory Speed&amp;quot; {ref('try6')}.",
2512              f"The module list saved in the same boot has one line &amp;quot;Configured Memory Speed&amp;quot; for each of its {DMI_N} modules {ref('dmi')}."),
2513           cl(f"The record also holds the line &amp;quot;modules={TRY6_MODLINE}&amp;quot; {ref('try6')}. This is not the module count. The module list holds {DMI_SIZE} lines with the text &amp;quot;Size: 32 GB&amp;quot;: "
2514              f"{DMI_SIZE_PLAIN} lines &amp;quot;Size&amp;quot; and {DMI_SIZE_VOL} lines &amp;quot;Volatile Size&amp;quot; {ref('dmi')}.",
2515              f"Hypothesis, not checked: the script that wrote the record counted these {DMI_SIZE} lines. Reading that script would confirm or reject it.")],
2516          ["Memory speed 7200 MT/s during the rerun",
2517           f"Every state line holds the boot id {RERUN['boot_id']}. The record of this boot, written at {TRY6_UTC[11:19]} UTC, shows 12 x &amp;quot;Configured Memory Speed: 7200 MT/s&amp;quot; {ref('try6')}.",
2518           "The speed was not read during the rerun. Reading it needs root. Assumption, not measured: the speed does not change inside one boot."],
2519          ["The rerun is complete",
2520           f"go.sh ran from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC. The script stops at the first exit status other than 0 {ref('go')}. Its log holds {GO_DONE} &amp;quot;done&amp;quot; lines and the final line ALLDONE {ref('golog')}. So {GO_DONE} of {GO_DONE} steps ended with exit status 0.",
2521           "-"],
2522          ["Logins and accounts with processes during go.sh",
2523           f"The {len(ST_GO)} state lines of the go.sh log show 0 logins. They list processes of {len(ACCOUNTS)} accounts only: jhan (the account that ran the rerun), root and {len(SYSTEM_ACCOUNTS)} system accounts {ref('golog')}.",
2524           "-"],
2525          ["Control I (added after the first numbers were seen) ran afterwards",
2526           f"go2.sh waits for a 1-minute load average below 1.0 and then runs the part L line. It does this twice {ref('go2')}. It ran from {RERUN['go2_start'][11:19]} to {RERUN['go2_end'][11:19]} UTC. "
2527           f"Its log holds 2 &amp;quot;done&amp;quot; lines and the final line ALLDONE {ref('go2log')}.",
2528           "Control I is not part of the plan fixed before the run."],
2529          [f"F72d12 (earlier run of the same boot, not part of the rerun) belongs to boot {BOOT8}",
2530           f"The record of this boot was written at {TRY6_UTC[11:19]} UTC {ref('try6')}. The boot list, saved at {BOOT_LAST} UTC, shows this boot from {BOOT_FIRST} UTC as the last boot {ref('boots')}. "
2531           f"The F72d12 process ran from {F_LAUNCH} to {F_END} UTC {ref('F72l')}. The go.sh log shows the same boot id at {RERUN['go_start'][11:19]} UTC {ref('golog')}.",
2532           "The proof uses these times only. The speed was not read during the process."],</pre></td><td valign="top">Rows 1 to 6 of the table. They hold no rate. Their values come from <code>RERUN</code> (the entry <code>meta.rerun</code> of facts.json) and from the raw-file checks of lines 811 to 1386. Lines 865, 866, 877 and 878 stop unless the run logs hold the same boot id, the same <code>MemTotal</code> and the same times as <code>RERUN</code>.<ul><li>12 memory modules: <code>MemTotal</code> of all state lines, the record of the boot in try6.txt (<code>TRY6_UTC</code>, <code>TRY6_MODLINE</code>) and the counts of the module list (<code>DMI_N</code>, <code>DMI_SIZE</code>).</li><li>Memory speed 7200 MT/s: the boot id and the record of the boot. The limit cell says that the speed was not read during the rerun.</li><li>The rerun is complete: the times of go.sh and <code>GO_DONE</code>, the number of <code>done</code> lines of its log.</li><li>Logins and accounts: the number of state lines of the go.sh log and the accounts that own processes.</li><li>Control I: the times of go2.sh.</li><li>F72d12: the boot list (<code>BOOT_FIRST</code>, <code>BOOT_LAST</code>) and the times of the F72d12 process (<code>F_LAUNCH</code>, <code>F_END</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2533          ["Work before the first 120-thread process of part A",
2534           f"On 2026-11-13 the test script launched {ONE_N} one-thread processes from {ONE_FIRST} to {ONE_LAST} UTC, directly before its 120-thread part {ref('one')}. "
2535           f"The rerun did not repeat this one-thread phase {ref('ra')}. "
2536           f"At 8000 MT/s the old read kernel gave {rA12_old.txt()} GB/s after one-thread work and directly after 120-thread work (rows A-1 and A-2, {n8000(rA12_old.recs)}) {ref('A-1', 'A-2', 'facts')}.",
2537           "Insufficient data: whether the work before the first 120-thread process changes the rate of the new read kernel. "
2538           f"A run with the new kernel at several positions, after an idle start and after 120-thread work, would resolve it {ref('rules')}."],
2539          ["Firmware settings other than the memory speed",
2540           f"Two TXREQ settings were changed for another test on 2026-11-17, at {X1_T} and {X2_T} UTC {ref('x1', 'x2')}. Both were set back at {RV_T} UTC to their values of the 8000 MT/s boot {ref('rev')}. "
2541           f"The settings list saved after that is equal to the list of the 8000 MT/s boot in all {N_SET} entries{'' if SAME_ORDER else ' (the order of the entries differs)'} {ref('qbase', 'qrev')}. "
2542           f"The only later change on record is DIMM Frequency = 7200 MT/s (file time {D72_T} UTC) {ref('d72')}.",
2543           cl(f"{N_UNREAD} of the {N_SET} entries show no readable value in both lists ({UNREAD['ValueUnavailable']} show ValueUnavailable, {UNREAD['VStoreError']} show VStoreError).",
2544              f"&amp;quot;On record&amp;quot; means the {len(SET_FILES)} files named set.txt in the results folder.",
2545              "Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. No full list was saved in that boot. A settings list saved in that boot would resolve it (needs root).")],
2546          ["The 8000 MT/s rows: one boot, 12 modules",
2547           cl(f"The saved kernel log of that boot runs from {BOOT8_FROM[:10]} {BOOT8_FROM[11:19]} to {BOOT8_TO[:10]} {BOOT8_TO[11:19]} UTC and holds the line &amp;quot;This system has 12 DIMM sockets&amp;quot; {ref('klog')}.",
2548              f"The kernel log of the boot that started on {BOOT10_FROM} UTC holds &amp;quot;This system has 10 DIMM sockets&amp;quot;, and its memory size line shows {MEM_LESS_GIB} GiB less {ref('klog10')}. "
2549              "So the number in this line is not the slot count of the board. This page reads it as the number of modules that the boot found.",
2550              f"Every process of the rows A-1 to A-3, of the rows L-1 to L-4 and of runner bwx was launched inside the time of this kernel log {ref('json')}. "
2551              "Row X2d12 and the three boots with 10 modules ran in later boots (notes under Table 2).",
2552              f"The settings list saved in that boot shows DIMM Frequency = 8000 MT/s {ref('qbase')}."),
2553           "No reading of the applied speed was saved in that boot."],</pre></td><td valign="top">Rows 7 to 9.<ul><li>Work before the first 120-thread process: the number and the times of the one-thread processes of 2026-11-13. This row prints one range of rates: <code>rA12_old.txt()</code>. It is the lowest and the highest rate of <code>bw_old</code> read over the 12 intervals of the rows A-1 and A-2 (line 1362). The saved output of a build shows 464.42 to 467.06 GB/s [Ref5].</li><li>Firmware settings: the times of the changes of the two TXREQ settings, the number of entries of the settings list (<code>N_SET</code>), the entries without a readable value (<code>N_UNREAD</code>), and the file time of the change to 7200 MT/s (<code>D72_T</code>).</li><li>The 8000 MT/s rows: the start and the end of the saved kernel log of that boot. The row also prints <code>MEM_LESS_GIB</code> (line 1157): how many GiB less memory the kernel log of one boot with 10 modules shows than the kernel log of the 8000 MT/s boot (1 GiB is 2^30 bytes).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2554          ["Corrected hardware error records in the 8000 MT/s rows",
2555           cl(f"Rows L-1 to L-4: the journal of the 8000 MT/s boot holds corrected hardware error records during two of the four rows. It holds {HW_L1} during L-1, and {HW_L2[0]} and {HW_L2[1]} during the two processes of L-2. "
2556              f"It holds {HW_L34} during L-3 and L-4 {hw_refs}.",
2557              f"Rows A-1 to A-3 ({A_DAY}): the journal holds {len(HW_A)} records between the first launch of A-1 ({A1_FIRST} UTC) and the launch that followed the last A-3 process used here ({A3_END} UTC). "
2558              f"All {len(HW_A)} records have times inside row A-2. 2 records have the time {HW_A2_T[0]} UTC. The bw_new read process of round 1 was launched at {HW_A2_T[0]} UTC too. "
2559              f"The other 2 records have the time {HW_A2_T[1]} UTC. A {A2_OTHER} process, which this page does not use, was launched {secs(HW_A2_T[1]) - secs(a2_other[0][1])} s before that {ref('journal', 'A-1', 'A-2', 'A-3')}."),
2560           cl("The data do not show that a record changed a rate.",
2561              "For the rerun the kernel log was not read (section 3).",
2562              "The rows of runner bwx (note under Table 2) were not checked for such records.")],
2563          ["The lowest asmread value of the 8000 MT/s pool comes from an interval with corrected hardware error records",
2564           cl(f"The lowest asmread value of the pool L-1 to L-4 is {f2(val(LOWEST_ASM))} GB/s. Its interval ran from about {LOW_FROM} to {LOW_TO} UTC on {low_day} "
2565              f"(est.: time of the launch line plus the seconds since the process start in the thread rows) {ref('L-2b', 'L-2l')}.",
2566              f"{len(HW_LOW)} corrected hardware error records have the journal time {low_day} {HW_LOW[0]['ts'][11:19]} UTC, inside this interval {ref('journal')}.",
2567              f"Without this one interval the pool spans {rPL_asm_wo.txt()} GB/s ({n8000(rPL_asm_wo.recs)}). Part L ({rL_asm.txt()} GB/s, {n7200(L_ASM)}) still lies above it, by {f2(rL_asm.nearest(rPL_asm_wo))} GB/s at the nearest ends."),
2568           "The data do not show that the records lowered this interval. Both times have a resolution of 1 s."],
2569      ]
2570      return table(["Fact", "Proof", "Limit"], rows, "state")
2571</pre></td><td valign="top">Rows 10 and 11, and the return.<ul><li>Row 10 prints the numbers of corrected hardware error records in the journal during the rows L-1 to L-4 (<code>HW_L1</code>, <code>HW_L2</code>, <code>HW_L34</code>) and during the rows A-1 to A-3 (<code>HW_A</code>).</li><li>Row 11 prints <code>f2(val(LOWEST_ASM))</code>: the lowest asmread rate of the pool. It is the value of <code>val</code> for that one interval: the sum of bytes / elapsed_s / 1e9 over its 120 thread rows. <code>LOW_FROM</code> and <code>LOW_TO</code> (line 1030) are the start time and the end time of the interval: the launch time plus the seconds since the process start in the thread rows. The page marks them <code>est.</code>.</li><li>Row 11 also prints the range of the pool without this one interval (<code>rPL_asm_wo</code>, line 521) and the asmread range of part L (<code>rL_asm</code>), each with its n. It prints <code>rL_asm.nearest(rPL_asm_wo)</code> too: the lowest asmread rate of part L minus the highest rate of that smaller pool.</li><li>The saved output of a build shows 288.54 GB/s for the lowest value, 298.61 to 309.17 GB/s for the pool without it, and 321.65 to 327.93 GB/s for part L [Ref5].</li><li>Line 2570 passes the rows to <code>table</code> (line 1501) with the column titles <code>Fact</code>, <code>Proof</code> and <code>Limit</code>.</li></ul></td></tr>
<tr><td colspan="2"><b><code>LOAD_CAPTION</code>: caption text of Table 6</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2572
2573  LOAD_CAPTION = (f"The first launch of the rerun was at a 1-minute load average of {f2(go_first['load1_at_first_launch'])}. The other {len(others)} steps of go.sh started at a 1-minute load average of "
2574                  f"{f2(min(others))} to {f2(max(others))}, each 5 s after a 120-thread process of the rerun had ended. "
2575                  "Hypothesis, not tested: these high values come from the rerun's own 120-thread processes. Two more facts fit it. The load value is an average over the last minute. "
2576                  f"The state lines of the go.sh log show 0 logins and processes of jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts only {ref('golog')}. "
2577                  "A sample of the load average and of the running processes, taken once per second between two steps, would confirm or reject it.")
2578
2579</pre></td><td valign="top">Prints the 1-minute load average at the first launch of the rerun (<code>go_first</code>). Then it prints the lowest and the highest load of <code>others</code>, the 9 other steps of go.sh. The text states a hypothesis that was not tested: the high values come from the 120-thread processes of the rerun itself. In <code>meta.launches</code> of facts.json the first launch has a load average of 0.07, and the other 9 steps have 74.05 to 105.24 [Ref2].</td></tr>
<tr><td colspan="2"><b><code>CSS</code>: the style block of the page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2580  CSS = """
2581  :root{color-scheme:light}
2582  *{box-sizing:border-box}
2583  body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
2584  main{max-width:980px;margin:0 auto;padding:28px 16px 64px}
2585  h1{font-size:28px;line-height:1.25;margin:0 0 6px}
2586  h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}
2587  h3{font-size:17px;margin:22px 0 8px}
2588  p{margin:8px 0}
2589  ul{margin:4px 0 8px;padding-left:22px}
2590  li{margin:3px 0}
2591  a{color:inherit}
2592  code{font-size:0.92em;overflow-wrap:anywhere}
2593  .sub{color:#52514e;font-size:14px;margin:0 0 18px}
2594  .short{background:#f1f0ec;border-left:4px solid #2a78d6;padding:12px 16px;margin:14px 0}
2595  .short p{margin:6px 0}
2596  .more{font-size:14.5px;margin:10px 0 0}
2597  .more+ul{font-size:14.5px}
2598  dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}
2599  dl.words dt{font-weight:600}
2600  dl.words dd{margin:0}
2601  @media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}
2602  .tw{overflow-x:auto;margin:10px 0}
2603  table{border-collapse:collapse;font-size:14px;line-height:1.35}
2604  th,td{border-bottom:1px solid #e4e3df;padding:4px 10px;text-align:left;vertical-align:top}
2605  th{background:#f1f0ec;font-weight:600}
2606  td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
2607  td.n{white-space:nowrap}
2608  tr.grp td{background:#f8f7f4;font-weight:600;color:#52514e;font-size:13px}
2609  tr.grp td .tn{font-weight:400;color:#0b0b0b;font-size:13.5px}
2610  tr.grp td .tn ul.cl{margin-top:3px}</pre></td><td valign="top">A text constant with the style rules of the page. <code>build</code> puts it into the <code>style</code> element (line 2707). It holds no data. This first part sets:<ul><li>one light colour theme (<code>color-scheme:light</code>) and a page width of at most 980 px (pixels).</li><li>the headings, the box of the Short version and the word list in two columns (one column in a window of at most 600 px).</li><li>the base style of the tables. A cell of the class <code>n</code> is right-aligned.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2611  /* Widths: the page content is the window width minus 32 px, and minus up to 17 px more when the browser draws a scrollbar.
2612     The wide tables have a least width of 900 px. So a wide table can scroll sideways in windows below 949 px, and the hint is shown there. */
2613  table.q1,table.q2,table.state,table.load,table.visits,table.detail{min-width:900px}
2614  .hint{display:none;color:#52514e;font-size:13.5px;margin:4px 0}
2615  @media (max-width:949px){.hint.ht{display:block}}
2616  /* A panel of figure 2 is 468 px wide with its border: it can scroll sideways in windows below 517 px. */
2617  @media (max-width:519px){.hint.h2{display:block}}
2618  table.state td:first-child{min-width:150px}
2619  table.state td:nth-child(2){min-width:300px}
2620  table.state td:nth-child(3){min-width:190px}
2621  table.q1 td:first-child{min-width:190px}
2622  table.q1 td:last-child{min-width:130px}
2623  table.q2 td:first-child{min-width:140px}
2624  table.q2 td:nth-child(2),table.q2 td:nth-child(3){min-width:160px}
2625  table.q2 td:last-child{min-width:220px}
2626  table.q2 th:nth-child(5){min-width:110px}
2627  table.visits td:first-child{min-width:120px}
2628  table.visits td:nth-child(2){min-width:90px}
2629  table.visits td:nth-child(3){min-width:280px}
2630  table.visits td:last-child{min-width:110px}
2631  table.narrow{max-width:760px}
2632  table.load td.n{white-space:normal}
2633  table.load td:nth-child(2){min-width:150px}
2634  table.load td:nth-child(3){min-width:110px}
2635  table.load td:nth-child(4){min-width:170px}
2636  table.load td:nth-child(5){min-width:190px}
2637  table.detail{font-size:13px}
2638  .num{font-variant-numeric:tabular-nums;white-space:nowrap}
2639  .sm{color:#52514e;font-size:12.5px}</pre></td><td valign="top">Width rules.<ul><li>The wide tables (classes <code>q1</code>, <code>q2</code>, <code>state</code>, <code>load</code>, <code>visits</code> and <code>detail</code>) have a least width of 900 px. In a window below 949 px such a table can scroll sideways.</li><li>The rule of line 2615 shows a hint line in a window of at most 949 px. Line 2617 shows a second hint for the panels of figure 2 in a window of at most 519 px.</li><li>Most of the other rules set the least width of single columns.</li><li>The class <code>num</code> (line 2638) keeps a number and its unit on one line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2640  figure{margin:16px 0}
2641  .fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}
2642  .fig.fit{width:fit-content;max-width:100%}
2643  .fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
2644  /* Figure 1 has three layouts, so it never scrolls sideways: 940 px wide in windows from 1000 px, 726 px from 780 px, 386 px below that.
2645     The box has a border of 1 px on each side, so the layouts need 942 + 49 px and 728 + 49 px of window width. */
2646  .fig svg.f1m,.fig svg.f1n{display:none}
2647  @media (max-width:999px){.fig svg.f1w{display:none}.fig svg.f1m{display:block}}
2648  @media (max-width:779px){.fig svg.f1m{display:none}.fig svg.f1n{display:block;max-width:100%;height:auto}}
2649  .panels{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start}
2650  .panels&gt;.fig,.panels&gt;.col{flex:0 1 468px;max-width:100%}
2651  ul.how{font-size:13.5px;color:#52514e;margin:10px 0 0;padding-left:20px}
2652  .legend{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:13.5px;margin:0 0 8px}
2653  .legend .li{display:inline-flex;align-items:center;gap:6px}
2654  .legend svg{flex:none}
2655  .scale{font-size:13.5px;margin:0 0 8px}
2656  g.pt:hover .mk.fi{stroke:#0b0b0b;stroke-width:1.6}
2657  g.pt:hover .mk.ho{stroke-width:3.6}
2658  figcaption{font-size:14.5px;margin-top:8px}
2659  .take{font-weight:600}
2660  .ref{color:#52514e;font-size:0.85em}
2661  .ref a{text-decoration:none;white-space:nowrap}
2662  .ref a:hover{text-decoration:underline}
2663  .note{color:#52514e;font-size:14px}
2664  .tcap{font-size:14.5px;margin:18px 0 0}
2665  .tcap b{font-weight:600}
2666  .tcap b .ref{font-weight:400}
2667  td ul.cl{margin:0;padding-left:16px}
2668  td ul.cl li{margin:0 0 5px}
2669  td ul.cl li:last-child{margin-bottom:0}
2670  ol.refs{font-size:14px;padding-left:0;list-style:none}
2671  ol.refs li{margin:5px 0;overflow-wrap:anywhere}
2672  details{margin:8px 0}
2673  summary{cursor:pointer;font-weight:600}
2674  """
2675
2676</pre></td><td valign="top">Rules for the figures and for the rest of the page.<ul><li>Figure 1 exists in three layouts (classes <code>f1w</code>, <code>f1m</code> and <code>f1n</code>). The rules show the wide one in a window of 1000 px or more, the middle one from 780 px to 999 px, and the narrow one below 780 px.</li><li>The two panels of figure 2 stand side by side when the window is wide enough.</li><li>The other rules style more parts of the page. Among them are the legends, a dot under the pointer, the captions, the reference marks, the reference list and the folded parts.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>build</code>: the whole page as one text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2677  def build():
2678      words = "".join(f"&lt;dt&gt;{k}&lt;/dt&gt;&lt;dd&gt;{v}&lt;/dd&gt;" for k, v in WORDS)
2679      short = "".join(P(s) for s in SHORT)</pre></td><td valign="top"><code>words</code>: one pair of the HTML elements <code>dt</code> (term) and <code>dd</code> (definition) per entry of <code>WORDS</code>. <code>short</code>: one paragraph per sentence of <code>SHORT</code>. <code>P</code> (line 1488) also adds each sentence to <code>PROSE</code> for the word count.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2680      how1 = ('&lt;ul class="how"&gt;'
2681              "&lt;li&gt;Each dot is the median of the intervals of its row. Point at a mark to see its values and its source file.&lt;/li&gt;"
2682              f"&lt;li&gt;For bwx12 a source names the interval row of the csv file. The rate is the sum of the 120 thread rows after it. This sum differs from the rate printed in the interval row by at most {f2(IROW_MAX)} GB/s.&lt;/li&gt;"
2683              f"&lt;li&gt;The data of both figures come from facts.json, the data file of the facts sheet {ref('json')}.&lt;/li&gt;&lt;/ul&gt;")
2684      how2 = ('&lt;ul class="how"&gt;'
2685              "&lt;li&gt;A 7200 MT/s row with all dots left of the band, or all dots right of it, does not overlap the 8000 MT/s range.&lt;/li&gt;"
2686              "&lt;li&gt;The bold text under a row name says where the row lies relative to the band: left of it (lower), inside it, overlapping it, or right of it (higher). "
2687              "A 7200 MT/s row without bold text is not compared with a band.&lt;/li&gt;"
2688              "&lt;li&gt;Panel &amp;quot;Load-only loop&amp;quot;, 0.5 s blocks: only session 1 is compared, each round against the same round (rule V3). "
2689              "Sessions 2 and 3 started 5 s after a 120-thread process of part C. Session 1 and the rows A-1 and A-2 did not. "
2690              f"Their first process started at a 1-minute load average of {f2(A_FIRST_LOAD['T72A1'])}, {f2(A_FIRST_LOAD['A-1'])} and {f2(A_FIRST_LOAD['A-2'])} (Table 6).&lt;/li&gt;"
2691              f"&lt;li&gt;The figure shows {N_DOTS} intervals. Control I was added after the first numbers were seen. "
2692              "Table 2 gives n for every comparison, except the three part A session rows of the old read kernel. "
2693              f"Each of them has {A_SESSION_N} and is a part of the Table 2 row &amp;quot;Part A (bw_old read)&amp;quot;.&lt;/li&gt;&lt;/ul&gt;")</pre></td><td valign="top"><code>how1</code> and <code>how2</code> are the reading notes under figure 1 and under figure 2.<ul><li><code>how1</code> says that each dot of figure 1 is the median of the intervals of its row. <code>fig1</code> places the dots at these medians (line 1662).</li><li><code>how1</code> then tells the reader how a bwx12 rate is computed. The source text of a tooltip (<code>src</code>, line 359) names the interval row of the csv file. The rate is the sum over the 120 thread rows after it: <code>val</code> (line 176) adds bytes / elapsed_s / 1e9 of each thread row.</li><li>It prints <code>f2(IROW_MAX)</code> (line 342). <code>IROW_MAX</code> is the largest difference between this sum, rounded to 0.01 GB/s, and the rate printed in the interval row, over the bwx12 records of <code>USED</code>. Line 343 allows at most 0.02 GB/s. The saved output of a build shows 0.02 GB/s [Ref5].</li><li><code>how2</code> says that a 7200 MT/s row without bold text is not compared with the grey band of its block (the range of the 8000 MT/s rows). In the 0.5 s blocks of the panel <code>Load-only loop</code> (part A, <code>bw_new</code> read) only session 1 is compared, each round against the same round. <code>A_V3</code> (line 509) holds these two comparisons.</li><li><code>how2</code> prints the three load values of <code>A_FIRST_LOAD</code>, the number of dots <code>N_DOTS</code> (line 1960) and the text <code>A_SESSION_N</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2694      fig2 = ('&lt;div class="panels"&gt;&lt;div class="col"&gt;&lt;div class="fig"&gt;'
2695              + panel("Old read kernel", "bw_old read and bwx12 oldread", OLD_AX[0], OLD_AX[1], range(460, 477, 4), range(458, 477, 2), P_OLD_BLOCKS, BLUE,
2696                      "Strip plot: every interval of the old read kernel, rows by method and memory speed")
2697              + '&lt;/div&gt;' + how2 + '&lt;/div&gt;&lt;div class="fig"&gt;'
2698              + panel("Load-only loop", "new read kernel, or asmread in its place where the label says so", NEW_AX[0], NEW_AX[1], range(280, 341, 20), range(280, 341, 10), P_NEW_BLOCKS, ORANGE,
2699                      "Strip plot: every interval of the load-only loop, rows by method and memory speed")
2700              + "&lt;/div&gt;&lt;/div&gt;")</pre></td><td valign="top"><code>fig2</code> holds the two panels of figure 2. <code>panel</code> (line 1756) draws each one.<ul><li>Panel <code>Old read kernel</code>: the blocks <code>P_OLD_BLOCKS</code>, blue dots, an x axis from 458 to 476 GB/s (<code>OLD_AX</code>).</li><li>Panel <code>Load-only loop</code>: the blocks <code>P_NEW_BLOCKS</code>, orange dots, an x axis from 276 to 340 GB/s (<code>NEW_AX</code>).</li><li>The two <code>range</code> arguments of a call give the grid lines. The first panel has a grid line every 2 GB/s and a label every 4 GB/s. The second panel has a grid line every 10 GB/s and a label every 20 GB/s.</li><li>Neither axis starts at 0. <code>panel</code> writes this into each panel (lines 1793 and 1820).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2701      page = f"""&lt;!doctype html&gt;
2702  &lt;html lang="en" data-theme="light"&gt;
2703  &lt;head&gt;
2704  &lt;meta charset="utf-8"&gt;
2705  &lt;meta name="viewport" content="width=device-width,initial-scale=1"&gt;
2706  &lt;title&gt;Whole-chip read test at 7200 MT/s&lt;/title&gt;
2707  &lt;style&gt;{CSS}&lt;/style&gt;
2708  &lt;/head&gt;
2709  &lt;body&gt;
2710  &lt;main&gt;
2711  &lt;h1&gt;Whole-chip read test at 7200 MT/s: old read kernel against new read kernel&lt;/h1&gt;
2712  &lt;p class="sub"&gt;2026-11-17, all times in UTC. Machine: CRB (an Arm reference server with 128 CPUs). 120 threads on CPUs 0-119, 256 MiB per thread. 12 memory modules at 7200 MT/s (million transfers per second, the unit of memory speed).&lt;/p&gt;
2713
2714  &lt;h2 id="short"&gt;Short version&lt;/h2&gt;
2715  &lt;div class="short"&gt;
2716  {short}
2717  &lt;/div&gt;
2718  &lt;p class="more"&gt;More detail for these three sentences:&lt;/p&gt;
2719  {SHORT_MORE}
2720
2721  &lt;details&gt;&lt;summary&gt;Words used here&lt;/summary&gt;
2722  &lt;dl class="words"&gt;{words}&lt;/dl&gt;
2723  &lt;/details&gt;</pre></td><td valign="top">The page text starts here. It is one f-string that ends in line 2780. These lines write:<ul><li>the head of the page with the style block and the title.</li><li>a typed line with the machine and the method: 120 threads on CPUs 0-119, 256 MiB per thread, 12 memory modules at 7200 MT/s.</li><li>the box with the three sentences (<code>short</code>) and the list <code>SHORT_MORE</code>.</li><li>the folded word list (<code>words</code>).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2724
2725  &lt;h2 id="q1"&gt;1. Is the new read kernel still below the old one? (Q1)&lt;/h2&gt;
2726  {SEC1_INTRO}
2727  &lt;figure&gt;
2728  {LEG1}
2729  &lt;div class="fig fit"&gt;{fig1("wide")}
2730  {fig1("mid")}
2731  {fig1("narrow")}&lt;/div&gt;
2732  &lt;figcaption&gt;&lt;span class="take"&gt;Figure 1. In the {len(SAME_LINE_ROWS)} rows that ran the argument line of part L (the same benchmark arguments) at 7200 MT/s, the blue dot (old read kernel) stays at nearly the same place, and the orange dot (load-only loop) moves. The intervals of the blue dots span {f2(VISIT_OLD_HI - VISIT_OLD_LO)} GB/s, and those of the orange dots span {f2(VISIT_HI - VISIT_LO)} GB/s.&lt;/span&gt; The {len(SAME_LINE_ROWS)} rows are part L, {CI} and {F72}. Their ranges are {f2(VISIT_OLD_LO)} to {f2(VISIT_OLD_HI)} GB/s (old read kernel) and {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s (load-only loop). The orange dot is left of the blue dot in every row of the figure. So the load-only rate is lower in every row.&lt;/figcaption&gt;
2733  {how1}
2734  &lt;/figure&gt;
2735  &lt;p class="tcap"&gt;&lt;b&gt;Table 1. The drop per part.&lt;/b&gt; The load-only loop is below the old read kernel in all {sum(N_RERUN_PAIRS)} pairs of the rerun rows of this table. It is also below it in the {len(C_ASM_DROPS)} asmread pairs of part C, which the table does not show {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.&lt;/p&gt;
2736  {q1_table()}
2737  {SEC1_AFTER}
2738  &lt;details&gt;&lt;summary&gt;Table view of Figure 1: every row&lt;/summary&gt;
2739  {detail_fig1()}
2740  &lt;/details&gt;</pre></td><td valign="top">Page section 1 (question Q1).<ul><li><code>SEC1_INTRO</code>, the legend <code>LEG1</code>, and figure 1 three times: <code>fig1</code> (line 1593) with the layouts <code>wide</code>, <code>mid</code> and <code>narrow</code>.</li><li>The caption of figure 1 prints <code>len(SAME_LINE_ROWS)</code>. Line 1588 asserts 6 rows. It prints two differences: <code>VISIT_OLD_HI - VISIT_OLD_LO</code> for the old read kernel and <code>VISIT_HI - VISIT_LO</code> for the load-only loop (lines 501 and 502). Each one is the highest minus the lowest interval rate over part L, control I and F72d12. The caption also prints these four rates as two ranges.</li><li>The caption of Table 1 prints <code>sum(N_RERUN_PAIRS)</code> and <code>len(C_ASM_DROPS)</code>.</li><li><code>q1_table()</code> (line 2003) builds Table 1, the drop per part. <code>SEC1_AFTER</code> follows.</li><li><code>detail_fig1()</code> (line 2255) builds the folded table view of figure 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2741
2742  &lt;h2 id="q2"&gt;2. Did a rate differ from the 8000 MT/s runs? (Q2)&lt;/h2&gt;
2743  {SEC2_INTRO}
2744  &lt;figure&gt;
2745  {LEG2}
2746  &lt;p class="scale"&gt;The two panels have different scales. The panel &amp;quot;Old read kernel&amp;quot; shows {OLD_AX[1] - OLD_AX[0]} GB/s over its width, and the panel &amp;quot;Load-only loop&amp;quot; shows {NEW_AX[1] - NEW_AX[0]} GB/s. So the same distance on the screen is {f1(Decimal(NEW_AX[1] - NEW_AX[0]) / Decimal(OLD_AX[1] - OLD_AX[0]))} times as many GB/s in the panel &amp;quot;Load-only loop&amp;quot;.&lt;/p&gt;
2747  &lt;p class="hint h2"&gt;If a panel does not fit the screen, scroll it sideways to see all dots.&lt;/p&gt;
2748  {fig2}
2749  &lt;figcaption&gt;&lt;span class="take"&gt;Figure 2. In the panel &amp;quot;Old read kernel&amp;quot; every 7200 MT/s row overlaps the grey band of its block, except part L. In the panel &amp;quot;Load-only loop&amp;quot; every 7200 MT/s row that is compared with a band lies to the right of it (higher), except F72d12 (earlier run of the same boot, not part of the rerun).&lt;/span&gt; {F2_RIGHT_TXT} Part L of the old read kernel lies {f2(abs(L_OLD_NEAR))} GB/s left of its band at the nearest ends (lower), and its median is {f2(abs(L_OLD_MED))} GB/s below the median of the band rows. F72d12 lies inside its band.&lt;/figcaption&gt;
2750  &lt;/figure&gt;
2751  &lt;p class="tcap"&gt;&lt;b&gt;Table 2. 7200 MT/s against 8000 MT/s, one row per comparison.&lt;/b&gt; The rows that are compared come from 1 boot per memory speed. All {GO_DONE} steps of the rerun ran inside one period of {GO_SECS // 60} min {GO_SECS % 60} s ({RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC) of the 7200 MT/s boot. {T2_RERUN_ROWS}&lt;/p&gt;
2752  {q2_table()}
2753  &lt;h3&gt;The rate of the load-only loop changed inside the one 7200 MT/s boot&lt;/h3&gt;
2754  {SEC2_BOOT}
2755  &lt;p class="tcap"&gt;&lt;b&gt;Table 3. The three visits of the part L line in the 7200 MT/s boot.&lt;/b&gt; asmread is at position 1 and oldread at position 0 of each process {ref('json')}.&lt;/p&gt;
2756  {visits_table()}
2757  &lt;p class="tcap"&gt;&lt;b&gt;Table 4. Three kinds of distance (asmread), each for part L against the 8000 MT/s pool and for part L against F72d12 (earlier run of the same boot, not part of the rerun) {ref('json')}.&lt;/b&gt; n of part L: {n7200(L_ASM)}. n of the pool L-1 to L-4: {n8000(P_L_ASM)}. n of F72d12: {n7200(F_ASM)}. At the nearest ends and at the medians, part L lies farther above F72d12 than above the pool. At the farthest ends the order is the opposite.&lt;/p&gt;
2758  {dist_table()}
2759  &lt;details&gt;&lt;summary&gt;Table view of Figure 2: every interval&lt;/summary&gt;
2760  {detail_fig2()}
2761  &lt;/details&gt;</pre></td><td valign="top">Page section 2 (question Q2).<ul><li><code>SEC2_INTRO</code>, the legend <code>LEG2</code>, and a note on the scales. The first panel shows 18 GB/s over its width and the second shows 64 GB/s. The note prints the ratio with 1 decimal: 3.6.</li><li><code>fig2</code> and its caption. The caption prints <code>F2_RIGHT_TXT</code> (line 1954), <code>abs(L_OLD_NEAR)</code> and <code>abs(L_OLD_MED)</code>.</li><li>The caption of Table 2 prints <code>GO_DONE</code>, the run time <code>GO_SECS</code> as minutes and seconds, and <code>T2_RERUN_ROWS</code> (line 2074). <code>q2_table()</code> (line 2079) builds Table 2.</li><li><code>SEC2_BOOT</code>, then Table 3 from <code>visits_table()</code> (line 2184).</li><li>Table 4 from <code>dist_table()</code> (line 2213). Its caption prints the texts of n of part L, of the pool L-1 to L-4 and of F72d12.</li><li><code>detail_fig2()</code> (line 2266) builds the folded table view of figure 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2762
2763  &lt;h2 id="open"&gt;3. What the data do not show&lt;/h2&gt;
2764  {INSUFF}
2765
2766  &lt;h2 id="state"&gt;4. Machine state and system load&lt;/h2&gt;
2767  &lt;p class="tcap"&gt;&lt;b&gt;Table 5. Machine state: each fact with its proof and its limit.&lt;/b&gt;&lt;/p&gt;
2768  {state_table()}
2769  &lt;h3&gt;System load&lt;/h3&gt;
2770  &lt;p class="tcap"&gt;&lt;b&gt;Table 6. 1-minute load average of Linux, read by the scripts directly before each launch {ref('json')}.&lt;/b&gt; {LOAD_CAPTION}&lt;/p&gt;
2771  {load_table()}</pre></td><td valign="top">Page sections 3 and 4. Section 3 is the list <code>INSUFF</code>. Section 4 holds Table 5 from <code>state_table()</code> (line 2503), and Table 6 from <code>load_table()</code> (line 2219) with the caption text <code>LOAD_CAPTION</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2772
2773  &lt;h2 id="refs"&gt;References&lt;/h2&gt;
2774  &lt;p class="note"&gt;A script computed every rate of this page from the interval records of the facts sheet and from the thread rows of the csv files that these records name. It read the facts of section 4 from the raw files cited there {ref('gen', 'json', 'facts', 'build')}.&lt;/p&gt;
2775  &lt;p class="note"&gt;R = &lt;code&gt;{R}&lt;/code&gt;&lt;br&gt;S = &lt;code&gt;{S}&lt;/code&gt;&lt;/p&gt;
2776  &lt;ol class="refs"&gt;\x01REFLIST\x01&lt;/ol&gt;
2777  &lt;/main&gt;
2778  &lt;/body&gt;
2779  &lt;/html&gt;
2780  """
2781      return page
2782</pre></td><td valign="top">The reference section of the page.<ul><li>A typed note says that a script computed every rate from the interval records of the facts sheet and from the thread rows of the csv files that these records name.</li><li>Line 2775 prints the two folder paths <code>R</code> and <code>S</code>.</li><li><code>\x01REFLIST\x01</code> (the word REFLIST between two control characters) is a placeholder. <code>number_refs</code> replaces it by the reference list.</li><li>Line 2781 returns the page text.</li></ul></td></tr>
<tr><td colspan="2"><b>Build the page and number the references</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2783
2784  PAGE, UNCITED = number_refs(build())
2785</pre></td><td valign="top">Line 2784 calls <code>build</code>. All figure functions and table functions run inside this call.<ul><li><code>number_refs</code> (line 828) then replaces each reference mark by <code>[RefN]</code>, numbered in the order of first use, and writes the reference list.</li><li><code>PAGE</code> is the finished page text.</li><li><code>UNCITED</code> is the list of the reference keys that the page never cites.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks of the built page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2786  # ------------------------------------------------------------------ checks of the built page
2787  words_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in PROSE)   # a lone "%" or "/" is not a word
2788  how_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in re.findall(r'&lt;ul class="how"&gt;(.*?)&lt;/ul&gt;', PAGE, re.S))
2789  check(700 &lt;= words_n &lt;= 1000, f"prose outside tables, captions, word list and references: {words_n} words (target 700 to 1000). "
2790                                f"Counted as captions and not as prose: the figure and table captions, and the reading notes under the two figures ({how_n} words)")
2791  check(len(SHORT) == 3 and all(len(re.findall(r"[.!?](?:\s|$)", strip_tags(s).replace("MT/s.", "MT/s"))) == 1 for s in SHORT), "Short version: 3 sentences")
2792  check(not UNCITED, f"references: {len(REFS)} paths exist, {len(REFS) - len(UNCITED)} are cited in the body, numbered in the order of first use")
2793  check(not re.search(r"prefers-color-scheme|&lt;script|&lt;link|@import|url\(|&lt;img|src=", PAGE), "one light theme, no script, no external file")</pre></td><td valign="top">Each <code>check</code> call adds one PASS or FAIL line to <code>CHECKS</code>. The script does not stop here.<ul><li><code>words_n</code>: the number of words in <code>PROSE</code>, the texts that <code>P</code> and <code>UL</code> collected. <code>strip_tags</code> (line 1484) removes the tags and the reference marks first. A word is a run of characters without white space that holds a letter or a digit. <code>how_n</code> is the same count for the reading notes under the two figures.</li><li>Line 2789: <code>words_n</code> must be from 700 to 1000 words.</li><li>Line 2791: <code>SHORT</code> must hold 3 texts, each with exactly one sentence end. A sentence end is <code>.</code>, <code>!</code> or <code>?</code> before white space or at the end of the text. A decimal point does not count. A full stop directly after <code>MT/s</code> does not count.</li><li>Line 2792: no reference may be uncited.</li><li>Line 2793: the page must hold none of the texts <code>prefers-color-scheme</code>, <code>&lt;script</code>, <code>&lt;link</code>, <code>@import</code>, <code>url(</code>, <code>&lt;img</code> and <code>src=</code>. So it has one colour theme, no script and no external file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2794  # control I and F72d12 carry their label in every bullet, caption, table row and tooltip that names them
2795  units = [strip_tags(x[1]) for x in re.findall(r"&lt;(li|p|figcaption|title|dd|tr)\b[^&gt;]*&gt;(.*?)&lt;/\1&gt;", PAGE, re.S)]
2796  for lab_, pat, must in (("control I", r"[Cc]ontrol I\b", ("added after the first numbers were seen",)),
2797                          ("F72d12", r"F72d12", ("not part of the rerun",))):
2798      hit = [u for u in units if re.search(pat, u)]
2799      miss = [u for u in hit if not any(m in u for m in must)]
2800      check(len(hit) &gt; 0 and not miss, f"label of {lab_}: {len(hit)} text units name it, {len(miss)} without the label in the same unit" + ("" if not miss else ": " + " | ".join(m[:60] for m in miss)))
2801  check(len(re.findall(r"&lt;title&gt;", PAGE)) - 1 &gt;= N_DOTS + 2 * F1_NROWS, f"tooltips: {len(re.findall(r'&lt;title&gt;', PAGE)) - 1} SVG titles for {N_DOTS} interval dots and {3 * F1_NROWS} marks of figure 1 (drawn in three layouts)")</pre></td><td valign="top"><ul><li><code>units</code>: the texts of the <code>li</code>, <code>p</code>, <code>figcaption</code>, <code>title</code>, <code>dd</code> and <code>tr</code> elements of the page. A list item inside a table row is not a unit of its own. It belongs to the unit of that row.</li><li>The loop runs once for control I and once for F72d12. <code>hit</code> holds the units that name it. <code>miss</code> holds those of them without its label. The label is <code>added after the first numbers were seen</code> for control I and <code>not part of the rerun</code> for F72d12.</li><li>The check of line 2800 passes when <code>hit</code> is not empty and <code>miss</code> is empty.</li><li>Line 2801 counts the <code>&lt;title&gt;</code> tags of the page and subtracts 1 for the page title. The rest are tooltips. The check passes when their number is at least <code>N_DOTS + 2 * F1_NROWS</code>.</li><li>This is a lower limit: 139 + 2 x 21 = 181 tooltips with this data. The message prints <code>3 * F1_NROWS</code>, not the limit of the test. The saved output of a build shows 333 tooltips [Ref5].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2802  # wording checks of the visible text and of the tooltips (the style block is not text)
2803  VISIBLE = strip_tags(re.sub(r"&lt;style&gt;.*?&lt;/style&gt;", " ", PAGE, flags=re.S))
2804  BANNED = [";", "load-only kernel", "at three times", "directly after none", "counter events", "bwx runners", "I row", "T rows", "ran above", "loop moved",
2805            "identical argument line", "facts file", "fall into", "lies against", "explains why", "By its name"]
2806  found = [b for b in BANNED if b in VISIBLE]
2807  check(not found, f"wording: none of {len(BANNED)} phrases that the review rejected is in the text or in a tooltip (semicolon, 'load-only kernel', 'at three times', ...)" + ("" if not found else ". Found: " + ", ".join(repr(b) for b in found)))
2808
2809  # "kernel" alone means the benchmark loop on this page. The operating system kernel is written "Linux kernel" ("kernel log" has its own entry in the word list)
2810  bare = re.findall(r"(?&lt;!Linux )\bkernel (?:thread|line|message)\w*", VISIBLE)
2811  check(not bare, "wording: every kernel thread, kernel line and kernel message is written with 'Linux' before it" + ("" if not bare else ". Found: " + ", ".join(sorted(set(bare)))))</pre></td><td valign="top"><ul><li><code>VISIBLE</code>: the text of the page without the style block and without tags. It includes the tooltips.</li><li><code>BANNED</code>: 16 phrases that a review rejected. The semicolon is one of them. The check of line 2807 passes when none of them is in <code>VISIBLE</code>.</li><li><code>bare</code>: every place where <code>kernel thread</code>, <code>kernel line</code> or <code>kernel message</code> stands without <code>Linux</code> directly before it. The check of line 2811 passes when this list is empty.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2812  f2_areas = sorted(a for g in F2_GAPS for a in g[4])
2813  check(len(F2_GAPS) == 2 and sum(g[1] for g in F2_GAPS) == N_DOTS == len(f2_areas),
2814        f"figure 2, hover areas: {N_DOTS} dots. The smallest distance of two dots is {min(g[2] for g in F2_GAPS):.2f} px (more than 5.2 px, the largest radius of a mark). "
2815        f"Each hover area is the part of a circle of {HIT_R:.0f} px radius that is nearer to its dot than to any other dot, so no two areas overlap. "
2816        f"{N_DOTS - sum(g[3] for g in F2_GAPS)} areas are the full circle ({max(f2_areas):.0f} px2), and a neighbour cuts {sum(g[3] for g in F2_GAPS)}. "
2817        f"Smallest area {f2_areas[0]:.0f} px2, median {median(f2_areas):.0f} px2 (a painted mark of 4.3 px radius covers {math.pi * 4.3 ** 2:.0f} px2)")
2818</pre></td><td valign="top">The last check covers the hover areas of figure 2.<ul><li><code>panel</code> adds one entry per panel to <code>F2_GAPS</code> (line 1788). The entry holds the title, the number of dots, the smallest distance of two dots in px, the number of hover areas that a neighbour cuts, and the size of every hover area.</li><li>The check passes when there are 2 panels, and the number of dots and the number of areas both equal <code>N_DOTS</code>.</li><li>Its message reports the smallest distance, the smallest area and the median area.</li></ul></td></tr>
<tr><td colspan="2"><b>Print the self-check list and decide</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2819  print("self-check list of make_report.py")
2820  bad = 0
2821  for ok, text in CHECKS:
2822      bad += 0 if ok else 1
2823      print(("  PASS  " if ok else "  FAIL  ") + text)
2824  print(f"{len(CHECKS) - bad} of {len(CHECKS)} checks pass")
2825  if bad:
2826      print("NOT WRITTEN: a check failed. The page on disk was not changed.")
2827      sys.exit(1)</pre></td><td valign="top">Prints one line per entry of <code>CHECKS</code>, with <code>PASS</code> or <code>FAIL</code> before its text.<ul><li><code>bad</code> counts the FAIL lines. Line 2824 prints how many checks pass.</li><li>When <code>bad</code> is above 0, the script prints <code>NOT WRITTEN</code> and ends with exit status 1 (<code>sys.exit(1)</code>).</li><li>The output file is not opened in that case. So the page on disk stays as it was.</li></ul></td></tr>
<tr><td colspan="2"><b>Write the page</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">2828  DATA = PAGE.encode("utf-8")
2829  with open(OUT, "wb") as f:
2830      f.write(DATA)
2831  print(f"wrote {OUT} ({len(DATA)} bytes, {len(PAGE)} characters)")
2832  print("Short version as built:")
2833  for s in SHORT:
2834      print("  " + re.sub(r"\s+", " ", strip_tags(s)).replace("( ", "(").replace(" )", ")").strip())</pre></td><td valign="top">The only write of the script. It runs only when every check passed and no <code>need</code> call stopped the script before.<ul><li>Lines 2828 to 2830 encode <code>PAGE</code> as UTF-8 (the usual byte encoding of text) and write the bytes to <code>OUT</code> (line 31). An older page file is replaced.</li><li>Line 2831 prints the path, the size in bytes and the number of characters.</li><li>Lines 2832 to 2834 print the three sentences of <code>SHORT</code> as plain text: without tags, and with each run of white space as one space.</li><li>The saved output of a build shows 98 of 98 checks as PASS and a page of 425796 bytes [Ref5].</li><li>Line 2834 is the last line of the file.</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: lines 38 to 89: the word list. The project words of this companion are copied from it. Lines 223 and 224: integrity checks 11 (64 + 56 threads on 120 different CPUs) and 12 (flags column of the T rows). Line 226: integrity check 14 (total of the T rows against the rate of the I row).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: `meta.counts.intervals` is 793. `meta.rate_kinds` says what the field `GBps` holds for part A and for the bwx runners. `meta.fields` gives the meaning of 14 of the 40 fields of a record.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: part A, session 1. Line 1: a process header line. Line 2: the header line with the formula of `aggregate_GBps`. Line 3: the 10 column names. Line 4: the first interval row (467.83 GB/s). Lines 4 to 6: the 3 interval rows of the first process (467.83, 467.92 and 465.38 GB/s). Line 7: its row with `best` (467.92 GB/s).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: part L, session 1. Line 1: the header line with the formula of `aggregate_GBps`. Lines 3 and 4: the column names of the I rows and of the T rows. Line 128: the I row of round 0, position 0, oldread, with the printed rate 462.29 GB/s. Lines 129 to 248: its 120 T rows (64 with a CPU number below 64, 56 with a CPU number from 64 up). Their sum by the method of `val` is 462.300017 GB/s. This sum was computed again for this companion.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/render/build-output.txt`: saved output of a run of this script. Line 2: 139 records used and 200 records of runner bwx. Line 3: 70 bwx12 records, 200 bwx records, 69 part A records. The same line gives the largest difference between a printed rate and the sum of the thread rows: 0.02 GB/s for bwx12 and 0.02 GB/s for bwx. Lines 4, 5 and 10 to 12: the drops and ranges of part C. Line 96: 139 dots. Line 100: 98 of 98 checks pass. Line 101: page size 425796 bytes.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/render/sha256-final.txt`: lists the sha256 3353042a... for make_report.py. The script file had the same sha256 on 2026-11-21. The page file had the size 425796 bytes on that day, as the saved output states. So the saved output fits this version of the script.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/render/fail-loud-test-output.txt`: saved output of `test_make_report.py` (in `S`): 11 cases. The case without damage ended with exit status 0. Each of the 10 other cases ended with a STOP message, exit status 1 and no page.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: lines 377 and 378: the function `bwx_intervals` computes `is_64_56` (64 threads with a CPU number below 64, 56 threads from 64 up, no CPU number above 119, 120 different CPU numbers) and `flagged` (the number of T rows with a flag other than `-`).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: the source of the binary bw_new. Lines 580 to 605: for each interval the loop sums the bytes of all threads, takes the longest elapsed time of a thread, and prints the total divided by that time and by 1e9 with 2 decimals (`aggregate_GBps`). After the loop it prints the row with `best`: the highest of these rates. The file `bandwidth.orig.c` in the same folder is the source of the binary bw_old. It holds the same code in its lines 423 to 448. This local text of `bandwidth.c` has the sha256 `f1985072...`. The file `probe.txt` of a build-only run of 18:32:18 UTC on 2026-11-13 (folder `kernels-20261113T183218Z` of R, line 15) holds this value. The file `probe.txt` of the timed run of 18:12:22 UTC (folder `kernels-20261113T181222Z` of R, line 15) holds another sha256 for `bandwidth.c` (`c1406e02...`). All three `probe.txt` records of that day hold the same sha256 for the binary bw_new (`fd7c14df...`). ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
