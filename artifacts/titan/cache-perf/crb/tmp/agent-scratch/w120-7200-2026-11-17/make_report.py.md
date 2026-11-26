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

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/make_report.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (2834 lines, 213989 bytes, sha256 `3353042adcdfedb25da035362cd2e64905049cd71b021b7546d97ab30ef4563f`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: output, input and the rules of the script (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""make_report.py - builds the report page of the whole-chip read rerun at 7200 MT/s.` | Comment: starts the documentation text of the file. Python does not run the text between the two marks `"""` (lines 2 to 19). This line says that the script builds the report page of the whole-chip read rerun at 7200 MT/s. |
| 4 | `Output: crb/new-test-kernel/whole-chip-rerun-7200.html (one self-contained HTML file).` | Comment: the output is one HTML file, `whole-chip-rerun-7200.html`. Self-contained means that the page loads no other file. Line 31 holds the full path. Line 2793 tests that the page holds no script and no link to an external file. |
| 5 | `Input:  facts.json of this folder (records "intervals", meta.launches, meta.rerun).` | Comment: the input is the file `facts.json`: its list `intervals` and its parts `meta.launches` and `meta.rerun`. The comment says `of this folder`. The code takes the file from the fixed folder `S` (line 29, line 234). The script reads more files than this line names: `FACTS.md` (line 235), the three spec files and many raw result files (lines 841 to 1386). |
| 7 | `Rules of this script:` | Comment: starts the list of the rules of the script (lines 8 to 18). |
| 8 | `- Every measured number of the page is computed here from the interval records. No measured number is typed.` | Comment: rule 1. Every measured number of the page is computed in this script from the interval records. No measured number is written into the script as a fixed value. |
| 9 | `- facts.json holds the bwx rates rounded to 0.001 GB/s. For the last digit at 0.01 GB/s the function val() sums the` | Comment: rule 2. `facts.json` holds each rate of a bwx runner rounded to 0.001 GB/s. To get the right last digit at 0.01 GB/s, the function `val` (line 176) sums the thread rows of the raw csv file that a record names. |
| 10 | `  thread rows of the raw csv that a record names, and it stops when that sum does not round to the record value.` | Comment: rule 2, continued. The script stops when this sum does not round to the value of the record (line 187). |
| 11 | `- Record counts are asserted. A wrong count stops the build.` | Comment: rule 3. The script asserts the number of records of each group (`expect`, line 260). A wrong number stops the build. |
| 12 | `- The computed values are compared with FACTS.md and with the "verdicts" of facts.json.` | Comment: rule 4. The computed values are compared with `FACTS.md` and with the part `verdicts` of `facts.json` (lines 652 to 809). |
| 13 | `  A mismatch is printed in the self-check list, the page is not written, and the exit status is 1.` | Comment: rule 4, continued. A mismatch is printed in the self-check list. The page is then not written, and the exit status of the script is 1 (lines 2825 to 2827). |
| 14 | `- The facts of the section "Machine state" are checked in the raw files (read only) before they are written.` | Comment: rule 5. The facts of the page section `Machine state` are checked in the raw files before they are written into the page (lines 841 to 1386). The raw files are only read. |
| 15 | `- Every record must name its row in the raw csv file: the interval row with its rate (part A), or the interval row` | Comment: rule 6. Every record must name its row in the raw csv file. For part A this is the interval row with its rate. For bwx12 it is the interval row (I row) and the 120 thread rows (T rows) after it. |
| 16 | `  and the 120 thread rows after it (bwx12). A tooltip cites that row.` | Comment: rule 6, continued. A tooltip of the page cites that row. The function `src` (line 359) builds this text. |
| 17 | `- Figure 1 is drawn in three layouts (940, 726 and 386 px wide). The style block shows the one that fits the window.` | Comment: rule 7. Figure 1 is drawn in three layouts, 940, 726 and 386 px wide. The style block of the page shows the one layout that fits the window. |
| 18 | `Python 3 standard library only. Edit this file, never the HTML.` | Comment: the script needs only the Python 3 standard library. A change of the page must be made in this file, never in the HTML file. |
| 19 | `"""` | Ends the documentation text that starts in line 2. |

### Modules, fixed paths, colours and the two lists `CHECKS` and `PROSE` (lines 20 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `import html` | Loads the module `html` of the Python standard library. `esc` (line 108) uses it to make a text safe for HTML. |
| 21 | `import json` | Loads the module `json`. It parses `facts.json` (line 234) and the firmware settings files (line 1053, line 1069). |
| 22 | `import math` | Loads the module `math`. The drawing code of figure 2 uses it (line 1730), and one check of the built page does too (line 2817). |
| 23 | `import os` | Loads the module `os`. The script uses it for paths, for the test whether a file exists, for file times and for the scan of a folder tree. |
| 24 | `import re` | Loads the module `re`, which applies regular expressions. The script uses it to read numbers and fields from text lines. |
| 25 | `import sys` | Loads the module `sys`. `sys.exit` ends the script (line 43, line 2827). |
| 26 | `import time` | Loads the module `time`. It gives the wait of `read_retry` (line 76) and turns a file time into text (line 908). |
| 27 | `from decimal import Decimal, ROUND_HALF_UP` | Loads the number type `Decimal` and the rounding mode `ROUND_HALF_UP` from the module `decimal`. The script uses them for rounding (function `q`, line 90). All modules of lines 20 to 27 belong to the Python standard library. No other package is needed. |
| 29 | `S = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17"` | `S`: the scratch folder of the rerun. It holds `facts.json`, `FACTS.md` and the three spec files. |
| 30 | `R = "/home/jhan/workspace/titan/cache-perf/crb/results"` | `R`: the results folder. It holds the raw csv files and the other raw result files. |
| 31 | `OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"` | `OUT`: the page that the script writes (line 2829). |
| 32 | `EARLIER = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html"` | `EARLIER`: the earlier report page, of 2026-11-15, on the lower whole-chip read rate of the load-only loop. Lines 1384 to 1386 read it. |
| 34 | `BLUE, ORANGE = "#2a78d6", "#eb6834"          # old read kernel, load-only loop (validated, see palette check)` | Two colours of the figures, as hexadecimal codes. By the comment, `BLUE` marks the old read kernel and `ORANGE` marks the load-only loop. The comment also says that a palette check validated the two colours. That check is not in this file. |
| 35 | `INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"` | Four more colours. `INK` is the colour of normal text. `MUTED` is the grey of small text and of axis labels. `GRID` is the colour of grid lines. `SURF` is the background colour of the page. It also fills the hollow markers. |
| 36 | `BAND, BAND_EDGE, LINK = "#ebe9e0", "#b9b7ae", "#8d8c86"` | Three colours for single parts of the figures. `BAND` and `BAND_EDGE` are the fill and the edge of the grey band of figure 2 (lines 1805 to 1806). `LINK` is the colour of the line between the two dots of a row of figure 1 (line 1666). |
| 38 | `CHECKS = []          # (ok, text)` | `CHECKS`: the self-check list. It starts empty. `check` (line 52) adds one pair (pass or fail, text) per line. The end of the file prints the list (lines 2819 to 2824). |
| 39 | `PROSE = []           # visible prose outside tables, captions, word list and references (for the word count)` | `PROSE`: the text of the page that counts for the word limit. It starts empty. `P` (line 1488) and `UL` (line 1493) add to it. By the comment, tables, captions, the word list and the references are not counted. Line 2787 counts the words. |

### Functions `stop`, `need`, `check` and `grouped`: stops and the self-check list (lines 42 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `def stop(msg):` | Starts the function `stop`. It ends the script at once with a message. |
| 43 | `    sys.exit("make_report.py: STOP: " + msg)` | `sys.exit` with a text prints the text to the error output and ends the script with exit status 1. The text is `make_report.py: STOP:` and then the message `msg`. No later line runs. The page is written only at the end of the file (line 2829). So a stop leaves the page on disk as it was. |
| 46 | `def need(cond, msg):` | Starts the function `need`, the hard assertion of the script. The script uses it to assert record counts, the content of raw csv rows and the expected results of comparisons. |
| 47 | `    """Hard assertion. A wrong record count or a failed raw-file check stops the build."""` | Comment: the documentation text of `need`. It is a hard assertion. A wrong record count or a failed check of a raw file stops the build. |
| 48 | `    if not cond:` | Tests whether the condition `cond` is false. When `cond` is true, nothing happens. |
| 49 | `        stop(msg)` | On a false condition: calls `stop` (line 42) with the message `msg`. The script then ends with exit status 1. |
| 52 | `def check(ok, text):` | Starts the function `check`. It adds one line to the self-check list. The script continues after a failed check. |
| 53 | `    CHECKS.append((bool(ok), text))` | Appends the pair (pass or fail, text) to `CHECKS`. `bool(ok)` turns the value `ok` into true or false. The end of the file prints the list. It writes the page only when every line passed (lines 2821 to 2827). |
| 56 | `def grouped(label, start):` | Starts the function `grouped`. It joins many checks into one line of the self-check list. `start` is the length that `CHECKS` had before these checks. |
| 57 | `    """Replace the checks added since index start by one line: n of m equal, and the first mismatch."""` | Comment: the documentation text. The function replaces the checks that were added from the index `start` on by one line. That line gives how many of the comparisons are equal, and the first mismatch. |
| 58 | `    sub = CHECKS[start:]` | `sub`: the checks that were added from the position `start` on. |
| 59 | `    del CHECKS[start:]` | Removes these checks from `CHECKS`. |
| 60 | `    bad = [t for ok, t in sub if not ok]` | `bad`: the texts of the failed checks among them. The expression builds this list: it keeps the text `t` of each pair whose first value `ok` is false. |
| 61 | `    check(not bad, f"{label}: {len(sub) - len(bad)} of {len(sub)} comparisons equal" + ("" if not bad else ". First mismatch: " + bad[0]))` | Adds one check in their place. Its text is the label and then a count of the form `N of M comparisons equal`. The check passes only when `bad` is empty. After a failure the text also holds `First mismatch:` and the text of the first failed comparison. |

### Functions `read_retry` and `lines_of`: reading a text file (lines 64 to 84)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `def read_retry(path, parse, complete=lambda t: True):` | Starts the function `read_retry`. It reads a whole file and returns `parse(text)`. `complete` is a test of the text. Its default value is a function that accepts every text. |
| 65 | `    """Another agent rebuilds facts.json and FACTS.md from time to time. Retry a failed or partial read."""` | Comment: the documentation text. It gives the reason for the retries: another agent rebuilds `facts.json` and `FACTS.md` from time to time. A read can then fail, or it can find a file that is only partly written. |
| 66 | `    last = None` | `last`: the reason of the last failed try. It starts without a value. |
| 67 | `    for _ in range(10):` | Starts a loop of at most 10 tries. |
| 68 | `        try:` | Starts the block whose errors line 74 handles. |
| 69 | `            with open(path, encoding="utf-8") as f:` | Opens the file as UTF-8 text. Python closes the file when the block of line 70 ends. |
| 70 | `                text = f.read()` | Reads the whole file into `text`. |
| 71 | `            if complete(text):` | Tests the text with `complete`. |
| 72 | `                return parse(text)` | When the text is complete: returns the result of `parse(text)`. The function ends here. |
| 73 | `            last = "file is not complete"` | When the text is not complete: notes the reason `file is not complete`. The loop goes on to the wait of line 76. |
| 74 | `        except (OSError, ValueError) as e:` | Handles two kinds of error of lines 69 to 72. `OSError`: the file cannot be opened or read. `ValueError`: `parse` cannot read the text, or the bytes are not valid UTF-8. |
| 75 | `            last = e` | Notes the error as the reason. |
| 76 | `        time.sleep(1.5)` | Waits 1.5 s before the next try. The wait also runs after the tenth failed try. So the 10 waits add up to 15 s. |
| 77 | `    stop(f"cannot read {path}: {last}")` | After 10 failed tries: `stop` ends the script. The message names the path and the last reason. |
| 80 | `def lines_of(path):` | Starts the function `lines_of`. It returns the lines of a text file as a list. |
| 81 | `    with open(path, encoding="utf-8", errors="replace") as f:` | Opens the file as UTF-8 text. `errors="replace"`: a byte that is not valid UTF-8 becomes a replacement character. So the read does not fail on such a byte. |
| 82 | `        return f.read().splitlines()` | Reads the whole file and splits it into lines, without the line ends. The first line of the file is element 0 of the list. |

### Number helpers `D`, `q`, `f2`, `f1`, `median`, the helper `esc` and two stores (lines 85 to 115)

| Line | Source | Explanation |
|---:|---|---|
| 85 | `# ------------------------------------------------------------------ numbers` | Comment: a section title. The helpers for numbers follow. |
| 86 | `def D(x):` | Starts the function `D`. It converts a number to the type `Decimal`. |
| 87 | `    return x if isinstance(x, Decimal) else Decimal(str(x))` | Returns a `Decimal` unchanged. Any other number is converted through its text form (`str(x)`). So the floating-point number 467.83 becomes exactly the decimal value 467.83. |
| 90 | `def q(x, places="0.01"):` | Starts the function `q`. It rounds `x` to the step `places`, which is 0.01 by default. The functions `f2`, `f1` and `signed` call it. |
| 91 | `    return D(x).quantize(Decimal(places), rounding=ROUND_HALF_UP)` | Converts `x` with `D` and rounds it to the step (`quantize`). `ROUND_HALF_UP`: a value exactly between two steps is rounded away from zero. Example: 462.295 becomes 462.30. |
| 94 | `def f2(x):` | Starts the function `f2`. It turns a number into a text with 2 decimals. The script prints rates in GB/s with it. |
| 95 | `    return f"{q(x):.2f}"` | Rounds with `q` to 0.01. The format `.2f` then gives the text with 2 decimals. |
| 98 | `def f1(x):` | Starts the function `f1`. It turns a number into a text with 1 decimal. The script prints percent values with it. |
| 99 | `    return f"{q(x, '0.1'):.1f}"` | Rounds with `q` to 0.1. The format `.1f` then gives the text with 1 decimal. |
| 102 | `def median(vals):` | Starts the function `median`. It returns the middle value of a list of numbers. |
| 103 | `    s = sorted(vals)` | `s`: the values in rising order. |
| 104 | `    n = len(s)` | `n`: the number of values. |
| 105 | `    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2` | For an odd `n` it returns the middle value `s[n // 2]`. For an even `n` it returns the mean of the two middle values. `//` divides and drops the remainder. The result is not rounded here. |
| 108 | `def esc(s):` | Starts the function `esc`. It makes a text safe for HTML. |
| 109 | `    return html.escape(str(s), quote=True)` | `html.escape` replaces the characters `&`, `<`, `>`, `"` and `'` by their HTML codes. `quote=True` asks for the two quote characters too. So a value cannot change the structure of the page. |
| 112 | `_TROWS = {}` | `_TROWS`: a dictionary that starts empty. It keeps the T rows of every csv file that `t_rows` (line 124) has read, grouped by interval. |
| 113 | `_FILES = {}` | `_FILES`: a dictionary that starts empty. It keeps the lines of every csv file that `file_lines` (line 116) has read. So each csv file is read from disk only once. |

### Functions `file_lines` and `t_rows`: the 120 thread rows of a bwx12 record (lines 116 to 141)

| Line | Source | Explanation |
|---:|---|---|
| 116 | `def file_lines(rec):` | Starts the function `file_lines`. It returns the lines of the csv file that a record names. |
| 117 | `    """The lines of the csv file that a record names."""` | Comment: the documentation text. The function gives the lines of the csv file that a record names. |
| 118 | `    key = (rec["folder"], rec["file"])` | `key`: the two fields with which a record names its csv file. `folder` is for example `R/w120-T72L1-20261117T221329Z`, and `file` is for example `a6456.csv` [Ref4]. |
| 119 | `    if key not in _FILES:` | Tests whether this file was read before. |
| 120 | `        _FILES[key] = lines_of(os.path.join(R, rec["folder"].replace("R/", "", 1), rec["file"]))` | First use of a file: removes the first `R/` from `folder`. Then it joins the results folder `R` (line 30), the rest of `folder` and `file` to one path. `lines_of` (line 80) reads the file, and the lines are kept in `_FILES`. |
| 121 | `    return _FILES[key]` | Returns the kept lines. The first line of the file is element 0 of the list. |
| 124 | `def t_rows(rec):` | Starts the function `t_rows`. It returns the T rows of the interval of one bwx12 record. Each T row holds one thread. |
| 125 | `    """The T rows (one per thread) of the interval of a bwx record: (cpu, bytes, elapsed_s, t_start_s, t_end_s, line number).` | Comment: the documentation text. Each returned T row is a group of six values: cpu, bytes, `elapsed_s`, `t_start_s`, `t_end_s` and the line number. |
| 126 | `    They must be the 120 lines directly after the I row that the record names."""` | Comment: the documentation text, continued. The T rows must be the 120 lines directly after the I row that the record names. |
| 127 | `    key = (rec["folder"], rec["file"])` | `key`: the csv file of the record, as in line 118. |
| 128 | `    if key not in _TROWS:` | Tests whether the T rows of this file were read before. Lines 129 to 135 run only at the first call for a csv file. |
| 129 | `        d = {}` | `d`: a dictionary that maps an interval to the list of its T rows. It starts empty. |
| 130 | `        for no, line in enumerate(file_lines(rec), 1):` | Goes through all lines of the csv file. `no` is the line number, counted from 1. |
| 131 | `            if line.startswith("T,"):` | Keeps only the lines that start with `T,`. These are the T rows. |
| 132 | `                p = line.split(",")` | `p`: the fields of the row, split at the commas. Python counts from 0. So `p[1]` is the second field. |
| 133 | `                need(len(p) == 13, f"{key}: a T row without 13 fields")` | The script stops when a T row does not have 13 fields. |
| 134 | `                d.setdefault((int(p[1]), int(p[2]), p[3]), []).append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))` | Adds the row to the list of its interval. The key of an interval is round, position and kernel: `p[1]`, `p[2]`, `p[3]`. Six values are kept per row: `p[5]` cpu, `p[6]` bytes, `p[7]` `elapsed_s`, `p[9]` `t_start_s`, `p[10]` `t_end_s`, and the line number. The names are the column names of the csv header [Ref4]. The times are counted in seconds from the start of the process. The fields `tid`, `t_sched_s`, `passes` and `flags` are not read. `setdefault` creates the list at the first row of an interval. |
| 135 | `        _TROWS[key] = d` | Keeps the dictionary of this file in `_TROWS`. |
| 136 | `    tl = _TROWS[key].get((rec["round"], rec["pos"], rec["kernel"]), [])` | `tl`: the T rows with the round, the position and the kernel of the record. The list is empty when the file holds no such row. |
| 137 | `    need(len(tl) == 120, f"{key}: no 120 T rows for round {rec['round']} position {rec['pos']} {rec['kernel']}")` | The script stops unless these are exactly 120 rows. The key holds no process number. If a file held the same round, position and kernel in two processes, the count would be above 120 and the script would stop. |
| 138 | `    need([t[5] for t in tl] == list(range(rec["line"] + 1, rec["line"] + 121)), f"{key}: the T rows are not the 120 lines after line {rec['line']}")` | The script also stops unless these rows are the 120 lines directly after the I row of the record. The field `line` of the record is the line number of the I row. So the line numbers of the rows must run from `line + 1` to `line + 120`, in this order. |
| 139 | `    return tl` | Returns the 120 rows. |

### Functions `t_rows_block`, `i_row_rate` and `file_process`: checks of raw csv rows (lines 142 to 175)

| Line | Source | Explanation |
|---:|---|---|
| 142 | `def t_rows_block(rec):` | Starts the function `t_rows_block`. It returns the T rows of one record of the older runner bwx, in the form that `t_rows` returns. |
| 143 | `    """The T rows of an interval record of the older runner bwx, as t_rows() returns them.` | Comment: the documentation text. The function gives the T rows of an interval record of the older runner bwx, as `t_rows` returns them. |
| 144 | `    A csv file of that runner holds several processes. So the rows are taken by their place:` | Comment: the documentation text, continued. A csv file of that runner holds several processes. So the rows are taken by their place in the file. |
| 145 | `    they must be the 120 lines directly after the I row that the record names, with its round, position and kernel."""` | Comment: the documentation text, continued. The rows must be the 120 lines directly after the I row that the record names, with its round, position and kernel. |
| 146 | `    fl = file_lines(rec)` | `fl`: the lines of the csv file of the record. |
| 147 | `    where = f"{rec['folder']}/{rec['file']} line {rec['line']}"` | `where`: the folder, the file and the line number of the I row as one text. The stop messages use it. |
| 148 | `    tl = []` | `tl`: the list of the rows. It starts empty. |
| 149 | `    for no in range(rec["line"] + 1, rec["line"] + 121):` | Goes through the 120 line numbers directly after the I row of the record (field `line`). |
| 150 | `        p = fl[no - 1].split(",")` | `p`: the fields of this line, split at the commas. The line with the number `no` is element `no - 1` of the list. |
| 151 | `        need(len(p) == 13 and p[0] == "T" and (int(p[1]), int(p[2]), p[3]) == (rec["round"], rec["pos"], rec["kernel"]),` | The script stops unless the line has 13 fields, `T` in the first field, and the round, position and kernel of the record. |
| 152 | `             f"{where}: line {no} is not a T row of this interval")` | Continues the call of line 151: the stop message. It names the file and the line that is not a T row of this interval. |
| 153 | `        tl.append((int(p[5]), int(p[6]), float(p[7]), float(p[9]), float(p[10]), no))` | Keeps the same six values as line 134: cpu, bytes, `elapsed_s`, `t_start_s`, `t_end_s` and the line number. |
| 154 | `    need(len(fl) == rec["line"] + 120 or not fl[rec["line"] + 120].startswith("T,"), f"{where}: more than 120 T rows follow the I row")` | The script also stops when the next line after these 120 starts with `T,`. A file that ends with the 120th row passes too. So exactly 120 T rows follow the I row. |
| 155 | `    return tl` | Returns the 120 rows. |
| 158 | `def i_row_rate(rec):` | Starts the function `i_row_rate`. It returns the rate that the I row of a bwx record prints, in GB/s. |
| 159 | `    """The rate that the interval row (I row) of a bwx record prints, in GB/s. The row must be the row of this record."""` | Comment: the documentation text. The function gives the rate that the interval row (I row) of a bwx record prints, in GB/s. The row must be the row of this record. |
| 160 | `    p = file_lines(rec)[rec["line"] - 1].split(",")` | `p`: the fields of the line that the record names (field `line`), split at the commas. |
| 161 | `    need(len(p) == 9 and p[0] == "I" and (int(p[1]), int(p[2]), p[3], int(p[5])) == (rec["round"], rec["pos"], rec["kernel"], 120),` | The script stops unless the line has 9 fields, `I` in the first field, the round, position and kernel of the record, and 120 in the field threads (`p[5]`). |
| 162 | `         f"{rec['folder']}/{rec['file']} line {rec['line']}: not the I row of round {rec['round']} position {rec['pos']} {rec['kernel']}")` | Continues the call of line 161: the stop message with the file, the line number and the interval that was expected. |
| 163 | `    return Decimal(p[8])` | Returns `p[8]`, the field `aggregate_GBps`, as a `Decimal`. The runner computed this printed rate as the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with 1 GB = 1e9 bytes [Ref4]. |
| 166 | `def file_process(rec):` | Starts the function `file_process`. For a part A record it checks the csv row and returns the number of the process inside its csv file. |
| 167 | `    """Part A: the number of the process inside its csv file (1 = first), counted from the header lines ("-- ...") up to the record.` | Comment: the documentation text. Part A: the function gives the number of the process inside its csv file, where 1 is the first process. It counts the header lines, which start with `-- `, up to the record. |
| 168 | `    The row of the record must hold the rate of the record."""` | Comment: the documentation text, continued. The row of the record must hold the rate of the record. |
| 169 | `    fl = file_lines(rec)` | `fl`: the lines of the csv file of the record. |
| 170 | `    p = fl[rec["line"] - 1].split(",")` | `p`: the fields of the line that the record names (field `line`), split at the commas. |
| 171 | `    need(len(p) == 10 and p[0] == rec["kernel"] and int(p[1]) == 120 and int(p[3]) == rec["interval"] and D(p[6]) == D(rec["GBps"]),` | The script stops unless the line has 10 fields, `p[0]` is the kernel of the record, `p[1]` (threads) is 120, `p[3]` (rep) is the interval number of the record, and `p[6]` (`aggregate_GBps`) equals the field `GBps` of the record [Ref3]. The row holds no name of a binary, and this function does not compare the binary. |
| 172 | `         f"{rec['folder']}/{rec['file']} line {rec['line']}: not the interval row of this record")` | Continues the call of line 171: the stop message with the file and the line number. |
| 173 | `    return sum(1 for l in fl[:rec["line"]] if l.startswith("-- "))` | Returns the number of lines that start with `-- `, from the first line of the file up to this row. Each such line is the header line of one process. So the result is the number of the process inside the file, counted from 1. |

### Function `val`: the rate of one record in GB/s (lines 176 to 191)

| Line | Source | Explanation |
|---:|---|---|
| 176 | `def val(rec):` | Starts the function `val`. It returns the rate of one interval record in GB/s. The class `Rg` (line 192) and the function `drops_of` (line 421) take their rates from here. |
| 177 | `    """Rate of an interval record in GB/s.` | Comment: the documentation text. The function gives the rate of an interval record in GB/s. |
| 178 | `    Part A: the record holds the value of the csv (2 decimals).` | Comment: the documentation text, continued. A part A record holds the value of the csv file, with 2 decimals. |
| 179 | `    bwx runners: facts.json holds the rate rounded to 0.001 GB/s, and FACTS.md rounds the unrounded value to 0.01 GB/s.` | Comment: the documentation text, continued. For the bwx runners, `facts.json` holds the rate rounded to 0.001 GB/s. `FACTS.md` rounds the unrounded value to 0.01 GB/s. |
| 180 | `    For the same last digit this function sums the 120 T rows that the record names (the method of build_facts.py)` | Comment: the documentation text, continued. To get the same last digit, this function sums the 120 T rows that the record names. By the comment this is the method of `build_facts.py`, the script that wrote the facts sheet. |
| 181 | `    and stops when the sum does not round to the value of the record."""` | Comment: the end of the documentation text. The script stops when the sum does not round to the value of the record (line 187). |
| 182 | `    if rec["part"] == "A":` | Tests whether the record belongs to part A. |
| 183 | `        return D(rec["GBps"])` | Part A record: returns the field `GBps` of the record as a `Decimal`. Nothing is summed. This is the rate that the benchmark printed in the csv row with 2 decimals: the bytes of all threads divided by the longest elapsed time of one thread, in GB/s with 1 GB = 1e9 bytes [Ref3]. |
| 184 | `    if "_exact" not in rec:` | Every other record: tests whether the sum was computed before. Lines 185 to 188 run only at the first call for a record. |
| 185 | `        tl = t_rows(rec) if rec["binary"] == "bwx12" else t_rows_block(rec)` | `tl`: the 120 T rows of the record. They come from `t_rows` (line 124) when the binary is bwx12, else from `t_rows_block` (line 142). |
| 186 | `        tot =sum(b / e / 1e9 for c, b, e, *_ in tl if c < 64) + sum(b / e / 1e9 for c, b, e, *_ in tl if c >= 64)` | `tot`: the rate of the interval in GB/s. For each T row the line computes `b / e / 1e9`. `b` is the field bytes of the row and `e` is its field `elapsed_s`, in seconds. This is the rate of one thread in GB/s, with 1 GB = 1e9 bytes. So the bytes of each thread are divided by the elapsed time of that thread. This formula differs from the formula of part A (line 183). The line adds the rates of the threads with a CPU number below 64 (mesh 0), then the rates of the other threads (mesh 1), then the two sums. All 120 rows are in the sum. `facts_data.py`, a module of `build_facts.py`, adds in the same order, and `build_facts.py` takes its sum from there. |
| 187 | `        need(abs(round(tot, 3) - rec["GBps"]) < 1e-9, f"{rec['folder']}/{rec['file']} line {rec['line']}: sum of the T rows {tot:.6f} is not the record value {rec['GBps']}")` | The script stops unless the sum, rounded to 3 decimals, equals the field `GBps` of the record. The test allows a difference below 1e-9 GB/s, which covers the rounding error of floating-point numbers. |
| 188 | `        rec["_exact"] = Decimal(repr(round(tot, 6)))` | Stores the sum, rounded to 6 decimals, in the record under the key `_exact`, as a `Decimal`. Example: 462.300017 GB/s for the first interval of part L in session 1, where the I row prints 462.29 GB/s [Ref4]. |
| 189 | `    return rec["_exact"]` | Returns the stored value. Every later call for the same record returns it without a new sum. |

### Class `Rg`: the range of a group of records. Functions `plural` and `signed` (lines 192 to 228)

| Line | Source | Explanation |
|---:|---|---|
| 192 | `class Rg:` | Starts the class `Rg`. An `Rg` object holds the rates of a list of records and their lowest-to-highest range. |
| 193 | `    """Lowest-to-highest range of a list of interval records."""` | Comment: the documentation text. The class is the lowest-to-highest range of a list of interval records. |
| 195 | `    def __init__(self, recs):` | Starts the method that builds an `Rg` object from the list of records `recs`. |
| 196 | `        need(len(recs) > 0, "empty selection")` | The script stops when the list is empty. |
| 197 | `        self.recs = sorted(recs, key=lambda r: (r["launch_utc"], r["interval"]))` | `recs`: the records, sorted by the launch time of their process (`launch_utc`) and then by the interval number. |
| 198 | `        self.v = [val(r) for r in self.recs]` | `v`: the rate of each record from `val` (line 176), in this order. |
| 199 | `        self.lo, self.hi, self.med = min(self.v), max(self.v), median(self.v)` | `lo`, `hi`, `med`: the lowest rate, the highest rate and the median of `v`. For an even number of rates the median is the mean of the two middle rates (line 105). No record of the list is left out. |
| 200 | `        self.n = len(recs)` | `n`: the number of records, which is the number of intervals. |
| 201 | `        self.procs = sorted({r["proc_key"] for r in recs})` | `procs`: the different values of the field `proc_key`, sorted. Each value stands for one process. |
| 202 | `        self.np = len(self.procs)` | `np`: their count, which is the number of processes. |
| 204 | `    def txt(self):` | Starts the method `txt`. It gives the range as text. |
| 205 | `        return f"{f2(self.lo)} to {f2(self.hi)}"` | Returns the lowest rate, the word `to` and the highest rate as one text. `f2` gives each rate with 2 decimals. |
| 207 | `    def overlaps(self, other):` | Starts the method `overlaps`. It tests whether this range and the range `other` overlap. |
| 208 | `        return self.lo <= other.hi and other.lo <= self.hi` | True when the two ranges share at least one value. Two ranges that share exactly one value count as overlapping. The test uses the rates as `val` returns them (6 decimals for a bwx record), not the rounded text. |
| 210 | `    def nearest(self, other):` | Starts the method `nearest`. It gives the distance of the nearest ends of two ranges, in GB/s. |
| 211 | `        """Distance of the nearest ends, + when self is the higher range. 0 when the ranges overlap."""` | Comment: the documentation text. The result has the sign `+` when this range is the higher one. It is 0 when the ranges overlap. |
| 212 | `        if self.overlaps(other):` | Tests whether the two ranges overlap. |
| 213 | `            return Decimal(0)` | Overlap: returns 0. |
| 214 | `        return self.lo - other.hi if self.lo > other.hi else self.hi - other.lo` | No overlap: returns the gap between the two nearest ends. When this range is the higher one, the result is `self.lo - other.hi`, which is above 0. When it is the lower one, the result is `self.hi - other.lo`, which is below 0. |
| 216 | `    def farthest(self, other):` | Starts the method `farthest`. It gives the distance of the farthest ends of two ranges, in GB/s. |
| 217 | `        return max(self.hi - other.lo, other.hi - self.lo)` | Returns the larger of the two differences `self.hi - other.lo` and `other.hi - self.lo`. For two ranges that do not overlap, this is the highest end of the higher range minus the lowest end of the lower range. |
| 220 | `def plural(n, word):` | Starts the function `plural`. It returns a count with its word in the singular or the plural form. |
| 221 | `    return f"{n} {word}" if n == 1 else f"{n} {word}{'es' if word.endswith('s') else 's'}"` | For the count 1 it returns the count and the word, for example `1 process`. For any other count it adds `es` to a word that ends in `s`, and `s` to any other word. Examples: `3 processes` and `6 intervals`. |
| 224 | `def signed(x):` | Starts the function `signed`. It returns a value as text with its sign. |
| 225 | `    x = q(x)` | Rounds the value to 0.01 with `q`. |
| 226 | `    return "0" if x == 0 else f"{'+' if x > 0 else '-'}{abs(x):.2f}"` | Returns `0` when the rounded value is zero. Else it returns the sign `+` or `-` and the value with 2 decimals, for example `-1.24`. |

### Loading `facts.json` and `FACTS.md` (lines 229 to 241)

| Line | Source | Explanation |
|---:|---|---|
| 229 | `# ------------------------------------------------------------------ load the facts` | Comment: a section title. The script loads its two input files here. |
| 230 | `def facts_complete(t):` | Starts the function `facts_complete`. It tests whether the text of `FACTS.md` is complete. |
| 231 | `    return "Output files of this sheet" in t and "## 7. Files" in t` | True when the text holds the phrase `Output files of this sheet` and the heading `## 7. Files`. In `FACTS.md` section 7 is the last section, and the phrase is in the last line of the file. So a file that is only partly written fails the test, and `read_retry` tries again. |
| 234 | `FJ = read_retry(S + "/facts.json", json.loads)` | `FJ`: the content of `facts.json` as Python data. `read_retry` (line 64) reads the file with up to 10 tries and parses it with `json.loads`. A file that is only partly written makes `json.loads` fail, and `read_retry` tries again. |
| 235 | `FMD = read_retry(S + "/FACTS.md", lambda t: t, facts_complete)` | `FMD`: the text of `FACTS.md`. The parse function `lambda t: t` returns the text unchanged. `facts_complete` (line 230) is the test for a complete file. |
| 236 | `IV = FJ["intervals"]` | `IV`: the list of all interval records. The record groups below are selected from this list. |
| 237 | `META = FJ["meta"]` | `META`: the part `meta` of `facts.json`. It holds facts of the run. |
| 238 | `RERUN = META["rerun"]` | `RERUN`: the part `meta.rerun`. It holds the boot id, MemTotal, the memory speed and the start and end times of `go.sh` and `go2.sh`. |
| 239 | `need(len(IV) == META["counts"]["intervals"], "facts.json: number of interval records differs from meta.counts")` | The script stops when the number of records in `IV` differs from `meta.counts.intervals`. The file states 793 records [Ref2]. |

### Functions `sel` and `expect`: select records and assert the size of a group (lines 242 to 270)

| Line | Source | Explanation |
|---:|---|---|
| 242 | `def sel(**kw):` | Starts the function `sel`. It returns the records of `IV` that pass every test of the call, in the order of `IV`. Each argument names a record field and gives a test for it. Example: `sel(dataset="rerun-L", kernel="oldread", pos=0)` returns the records whose field `dataset` is `rerun-L`, whose `kernel` is `oldread` and whose `pos` is 0. |
| 243 | `    out = []` | `out`: the list of the selected records. It starts empty. |
| 244 | `    for r in IV:` | Goes through all interval records. |
| 245 | `        ok = True` | `ok`: whether the record has passed all tests so far. |
| 246 | `        for k, v in kw.items():` | Goes through the arguments of the call. `k` is the name of a field and `v` is its test. |
| 247 | `            if callable(v):` | Case 1: the test `v` is a function. |
| 248 | `                ok = v(r[k])` | The function must return true for the field value. |
| 249 | `            elif isinstance(v, (list, tuple, set)):` | Case 2: `v` is a list, a tuple or a set. |
| 250 | `                ok = r[k] in v` | The field value must be one of its elements. |
| 251 | `            else:` | Case 3: `v` is a plain value. |
| 252 | `                ok = r[k] == v` | The field value must be equal to it. |
| 253 | `            if not ok:` | Tests whether the record failed this test. |
| 254 | `                break` | A failed test ends the loop over the arguments. The other tests of this record are not run. |
| 255 | `        if ok:` | Tests whether the record passed every test. |
| 256 | `            out.append(r)` | Adds such a record to `out`. |
| 257 | `    return out` | Returns the selected records. |
| 260 | `def expect(recs, n, nproc, what):` | Starts the function `expect`. It asserts the size of a record group and returns the list unchanged. `what` names the group in the stop messages. |
| 261 | `    need(len(recs) == n, f"{what}: expected {n} interval records, found {len(recs)}")` | The script stops unless the list has exactly `n` records. |
| 262 | `    got = len({r["proc_key"] for r in recs})` | `got`: the number of different values of the field `proc_key`, which is the number of processes. |
| 263 | `    need(got == nproc, f"{what}: expected {nproc} processes, found {got}")` | The script stops unless the records come from exactly `nproc` processes. |
| 264 | `    need(all(r["threads"] == 120 for r in recs), f"{what}: a record is not a 120-thread interval")` | The script stops unless every record has 120 threads. |
| 265 | `    return recs` | Returns the list unchanged. So a call of `expect` can stand around a call of `sel`. |
| 268 | `LPOOL = ("L-1", "L-2", "L-3", "L-4")` | `LPOOL`: the names of the bwx12 datasets at 8000 MT/s, the rows L-1 to L-4. |
| 269 | `APOOL = ("A-1", "A-2", "A-3")` | `APOOL`: the names of the part A datasets at 8000 MT/s, the rows A-1 to A-3. |

### The record groups of the page, each with its expected size (lines 271 to 305)

| Line | Source | Explanation |
|---:|---|---|
| 271 | `# part A, the repeat of the 2026-11-13 test` | Comment: the next two lines select part A of the rerun, the repeat of the test of 2026-11-13. |
| 272 | `A_OLD = expect(sel(dataset="rerun-A", binary="bw_old", kernel="read"), 18, 6, "part A, bw_old read")` | `A_OLD`: dataset `rerun-A`, binary `bw_old`, kernel `read`. This is the old read kernel in part A at 7200 MT/s. `expect` stops the script unless the group has 18 intervals of 6 processes. |
| 273 | `A_NEW = expect(sel(dataset="rerun-A", binary="bw_new", kernel="read"), 18, 6, "part A, bw_new read")` | `A_NEW`: the same with the binary `bw_new`. This is the new read kernel. The group must also have 18 intervals of 6 processes. The part A intervals of the kernels write, copy, asmread, asmwrite and asmcopy are not selected. |
| 274 | `# part L and the rows of the same argument line` | Comment: the next six lines select part L and the other runs of the same argument line. Three datasets hold runs of the argument line of part L in the 7200 MT/s boot: `rerun-L` (part L), `control-I` (control I) and `F72d12`. |
| 275 | `L_OLD = expect(sel(dataset="rerun-L", kernel="oldread", pos=0), 6, 3, "part L, oldread")` | `L_OLD`: part L, `oldread` at position 0. Expected size: 6 intervals of 3 processes. |
| 276 | `L_ASM = expect(sel(dataset="rerun-L", kernel="asmread", pos=1), 6, 3, "part L, asmread")` | `L_ASM`: part L, `asmread` at position 1. Expected size: 6 intervals of 3 processes. The intervals of `read_nop96`, `read_nop256` and `read_1pl` of these processes are not selected. |
| 277 | `I_OLD = expect(sel(dataset="control-I", kernel="oldread", pos=0), 4, 2, "control I, oldread")` | `I_OLD`: control I, `oldread` at position 0. Expected size: 4 intervals of 2 processes. |
| 278 | `I_ASM = expect(sel(dataset="control-I", kernel="asmread", pos=1), 4, 2, "control I, asmread")` | `I_ASM`: control I, `asmread` at position 1. Expected size: 4 intervals of 2 processes. |
| 279 | `F_OLD = expect(sel(dataset="F72d12", kernel="oldread", pos=0), 2, 1, "F72d12, oldread")` | `F_OLD`: F72d12, `oldread` at position 0. Expected size: 2 intervals of 1 process. |
| 280 | `F_ASM = expect(sel(dataset="F72d12", kernel="asmread", pos=1), 2, 1, "F72d12, asmread")` | `F_ASM`: F72d12, `asmread` at position 1. Expected size: 2 intervals of 1 process. |
| 281 | `# part C` | Comment: the next eight lines select part C. |
| 282 | `C_OLD = expect(sel(dataset="rerun-C", kernel="oldread"), 8, 4, "part C, oldread")` | `C_OLD`: all part C intervals of `oldread`, at any position. Expected size: 8 intervals of 4 processes. |
| 283 | `C_READ = expect(sel(dataset="rerun-C", kernel="read"), 8, 4, "part C, read")` | `C_READ`: all part C intervals of the kernel `read`, which is the new read kernel in bwx12. Expected size: 8 intervals of 4 processes. |
| 284 | `C_ASM = expect(sel(dataset="rerun-C", kernel="asmread"), 8, 4, "part C, asmread")` | `C_ASM`: all part C intervals of `asmread`. Expected size: 8 intervals of 4 processes. |
| 285 | `C_READ_AO = expect([r for r in C_READ if r["kernel_before"] == "oldread"], 4, 2, "part C, read after oldread")` | `C_READ_AO`: the `read` intervals whose field `kernel_before` is `oldread`. These are the 4 intervals of the two cfwd processes. `expect` asserts 4 intervals of 2 processes. |
| 286 | `C_READ_AA = expect([r for r in C_READ if r["kernel_before"] == "asmread"], 4, 2, "part C, read after asmread")` | `C_READ_AA`: the `read` intervals that were timed directly after `asmread`. These are the 4 intervals of the two crev processes. Expected size: 4 intervals of 2 processes. |
| 287 | `C_ASM_AR = expect([r for r in C_ASM if r["kernel_before"] == "read"], 4, 2, "part C, asmread after read")` | `C_ASM_AR`: the `asmread` intervals directly after `read`. Expected size: 4 intervals of 2 processes. |
| 288 | `C_ASM_AO = expect([r for r in C_ASM if r["kernel_before"] == "oldread"], 2, 2, "part C, asmread after oldread")` | `C_ASM_AO`: the `asmread` intervals directly after `oldread`. Expected size: 2 intervals of 2 processes. The page compares these 2 intervals with the 8000 MT/s pool (line 498). |
| 289 | `C_ASM_FI = expect([r for r in C_ASM if r["kernel_before"].startswith("none")], 2, 2, "part C, asmread first interval")` | `C_ASM_FI`: the `asmread` intervals that are the first interval of their process. Their field `kernel_before` starts with `none`. Expected size: 2 intervals of 2 processes. |
| 290 | `# 8000 MT/s rows` | Comment: the next lines select the rows at 8000 MT/s. |
| 291 | `B_L_OLD = {d: sel(dataset=d, kernel="oldread", pos=0) for d in LPOOL}` | `B_L_OLD`: a dictionary. For each dataset `d` of L-1 to L-4 it holds the records of `oldread` at position 0. |
| 292 | `B_L_ASM = {d: sel(dataset=d, kernel="asmread", pos=1) for d in LPOOL}` | `B_L_ASM`: the same for `asmread` at position 1. |
| 293 | `for d, n, p in (("L-1", 2, 1), ("L-2", 4, 2), ("L-3", 2, 1), ("L-4", 3, 3)):` | Goes through the four datasets with their expected sizes per kernel: L-1 2 intervals of 1 process, L-2 4 of 2, L-3 2 of 1, L-4 3 of 3. |
| 294 | `    expect(B_L_OLD[d], n, p, f"{d}, oldread at position 0")` | `expect` asserts this size for the `oldread` group of the dataset. |
| 295 | `    expect(B_L_ASM[d], n, p, f"{d}, asmread at position 1")` | `expect` asserts the same size for the `asmread` group. |
| 296 | `P_L_OLD = expect([r for d in LPOOL for r in B_L_OLD[d]], 11, 7, "pool L-1 to L-4, oldread")` | `P_L_OLD`: the four datasets joined to one pool for `oldread`. The pool must have 11 intervals of 7 processes. |
| 297 | `P_L_ASM = expect([r for d in LPOOL for r in B_L_ASM[d]], 11, 7, "pool L-1 to L-4, asmread")` | `P_L_ASM`: the pool for `asmread`. It must have 11 intervals of 7 processes too. |
| 298 | `B_A_OLD = {d: sel(dataset=d, binary="bw_old", kernel="read") for d in APOOL}` | `B_A_OLD`: a dictionary. For each of the datasets A-1, A-2 and A-3 it holds the records of the kernel `read` of `bw_old`. |
| 299 | `B_A_NEW = {d: sel(dataset=d, binary="bw_new", kernel="read") for d in ("A-1", "A-2")}` | `B_A_NEW`: the same for `bw_new`, for A-1 and A-2 only. No A-3 group is built for `bw_new`. |
| 300 | `for d, n, p in (("A-1", 6, 2), ("A-2", 6, 2), ("A-3", 9, 3)):` | Goes through the three datasets with their expected sizes for `bw_old`: A-1 6 intervals of 2 processes, A-2 6 of 2, A-3 9 of 3. |
| 301 | `    expect(B_A_OLD[d], n, p, f"{d}, bw_old read")` | `expect` asserts this size. |
| 302 | `for d in ("A-1", "A-2"):` | Goes through A-1 and A-2. |
| 303 | `    expect(B_A_NEW[d], 6, 2, f"{d}, bw_new read")` | `expect` asserts 6 intervals of 2 processes for `bw_new` in each of the two datasets. |
| 304 | `P_A_OLD = expect([r for d in APOOL for r in B_A_OLD[d]], 21, 7, "pool A-1 to A-3, bw_old read")` | `P_A_OLD`: the pool A-1 to A-3 for `bw_old`. It must have 21 intervals of 7 processes. No pool is built for `bw_new`. |

### Hard assertions on all used records. The records of the older runner bwx (lines 306 to 338)

| Line | Source | Explanation |
|---:|---|---|
| 306 | `USED = (A_OLD + A_NEW + L_OLD + L_ASM + I_OLD + I_ASM + F_OLD + F_ASM + C_OLD + C_READ + C_ASM` | `USED`: every record of the groups above, once. These are all records of the figures and comparisons of the page. This line adds up the groups of the 7200 MT/s boot. |
| 307 | `        + P_L_OLD + P_L_ASM + P_A_OLD + B_A_NEW["A-1"] + B_A_NEW["A-2"])` | Continues the sum of line 306: the two pools of the rows L-1 to L-4, the pool A-1 to A-3 and the `bw_new` groups of A-1 and A-2. The expected sizes add up to 139 records. |
| 308 | `need(all(r["modules"] == 12 for r in USED), "a record used on the page is not a 12-module run")` | The script stops unless every record of `USED` comes from a run with 12 memory modules. |
| 309 | `SEVEN = [r for r in USED if r["speed_MTps"] == 7200]` | `SEVEN`: the records of `USED` at 7200 MT/s. |
| 310 | `EIGHT = [r for r in USED if r["speed_MTps"] == 8000]` | `EIGHT`: the records of `USED` at 8000 MT/s. |
| 311 | `need(len(SEVEN) + len(EIGHT) == len(USED), "a record has another memory speed")` | The script stops when a record of `USED` has another memory speed. |
| 312 | `need({r["boot"] for r in SEVEN} == {RERUN["boot_id"]}, "the 7200 MT/s records are not from one boot")` | The script stops unless all 7200 MT/s records hold the boot id of the rerun (`meta.rerun.boot_id`). |
| 313 | `need(len({r["boot"] for r in EIGHT}) == 1, "the 8000 MT/s records are not from one boot")` | The script stops unless all 8000 MT/s records share one value of the field `boot`. |
| 314 | `need({r["dataset"] for r in SEVEN} == {"rerun-A", "rerun-L", "rerun-C", "control-I", "F72d12"}, "7200 MT/s datasets")` | The script stops unless the 7200 MT/s records come from exactly these five datasets: `rerun-A`, `rerun-L`, `rerun-C`, `control-I` and `F72d12`. |
| 315 | `need(all(r["min_ms"] == 500 and r["stop"] == "whole pass" for r in USED if r["part"] == "A"), "part A method")` | Method of the part A records. The script stops unless `min_ms` is 500 (an interval lasts at least 0.5 s) and `stop` is `whole pass` in each of them. |
| 316 | `need(all(r["stop"] == "common" for r in USED if r["part"] != "A"), "bwx12 rows: stop rule")` | Method of all other records. The script stops unless `stop` is `common` in each of them. |
| 317 | `need(all(r["min_ms"] == 6000 for r in USED if r["dataset"] in ("rerun-L", "rerun-C", "control-I", "F72d12", "L-1")),` | The script stops unless `min_ms` is 6000 (6 s) in the records of part L, part C, control I, F72d12 and L-1. |
| 318 | `     "6 s rows")` | Continues the call of line 317: the stop message `6 s rows`. |
| 319 | `need(all(r["min_ms"] == 4000 for r in USED if r["dataset"] in ("L-2", "L-3", "L-4")), "4 s rows")` | The script stops unless `min_ms` is 4000 (4 s) in the records of L-2, L-3 and L-4. So the pool L-1 to L-4 holds 6 s intervals and 4 s intervals. |
| 320 | `# Rows of the older runner bwx (another binary, not like-for-like). The rules file names them as the reference of part C` | Comment: the next lines select rows of the older runner bwx. It is another binary, so these rows are not like-for-like. By the comment, the rules file names them as the reference of part C. |
| 321 | `# (rule V2 point 4: folders B7 and C3, tags common-6000-*). The page shows them in one note under Table 2 and gives no wording from them.` | Comment: the place in the rules file is rule V2 point 4, with the folders B7 and C3 and the tags `common-6000-*`. The page shows these rows in one note under Table 2 and takes no wording from them. |
| 322 | `BWX_POOL = ("B7a", "B7b", "C3a", "C3b")` | `BWX_POOL`: four datasets of the older runner bwx: B7a, B7b, C3a and C3b. |
| 323 | `X_READ_AO = expect(sel(dataset=BWX_POOL, kernel="read", pos=1), 48, 24, "runner bwx, read at position 1")` | `X_READ_AO`: the kernel `read` at position 1 in these datasets. `expect` asserts 48 intervals of 24 processes. |
| 324 | `X_READ_AA = expect(sel(dataset=BWX_POOL, kernel="read", pos=6), 48, 24, "runner bwx, read at position 6")` | `X_READ_AA`: the kernel `read` at position 6. Expected size: 48 intervals of 24 processes. |
| 325 | `X_ASM_AR = expect(sel(dataset=BWX_POOL, kernel="asmread", pos=2), 48, 24, "runner bwx, asmread at position 2")` | `X_ASM_AR`: `asmread` at position 2. Expected size: 48 intervals of 24 processes. |
| 326 | `X_LOADS = expect(sel(dataset=BWX_POOL, kernel=("read", "asmread")), 192, 24, "runner bwx, all intervals of read and asmread")` | `X_LOADS`: all `read` and `asmread` intervals of these datasets, 192 intervals of 24 processes. Besides the three groups above it holds 48 `asmread` intervals at position 5 [Ref2]. |
| 327 | `need({r["kernel_before"] for r in X_READ_AO} == {"oldread"} and {r["kernel_before"] for r in X_READ_AA} == {"asmread"}` | The script stops unless the kernel directly before is `oldread` in every record of `X_READ_AO` and `asmread` in every record of `X_READ_AA`. |
| 328 | `     and {r["kernel_before"] for r in X_ASM_AR} == {"read"}, "runner bwx: the kernel directly before is not as rule V2 point 4 states")` | Continues the call of line 327: the kernel directly before must be `read` in every record of `X_ASM_AR`. The stop message follows. |
| 329 | `need(all(r["tag"].startswith("common-6000-") for r in X_LOADS), "runner bwx: a row has another tag than common-6000-*")` | The script stops unless every tag of `X_LOADS` starts with `common-6000-`. |
| 330 | `# four more processes of the same runner with the reverse kernel order (two B5 folders): higher values at 8000 MT/s` | Comment: four more processes of the same runner ran the reverse kernel order. They lie in two B5 folders. By the comment they hold higher values at 8000 MT/s. Line 550 tests this. |
| 331 | `X_REV_READ = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="read"), 4, 4, "runner bwx, reverse order, read")` | `X_REV_READ`: the kernel `read` of the datasets `B5a-rev` and `B5b-rev`. Expected size: 4 intervals of 4 processes. |
| 332 | `X_REV_ASM = expect(sel(dataset=("B5a-rev", "B5b-rev"), kernel="asmread"), 4, 4, "runner bwx, reverse order, asmread")` | `X_REV_ASM`: `asmread` of the same two datasets. Expected size: 4 intervals of 4 processes. |
| 333 | `OTHER = X_LOADS + X_REV_READ + X_REV_ASM` | `OTHER`: `X_LOADS` and these two groups joined. The expected sizes add up to 200 records. |
| 334 | `need(all(r["binary"] == "bwx" and r["modules"] == 12 and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000 for r in OTHER),` | The script stops unless every record of `OTHER` has the binary `bwx`, 12 modules, 8000 MT/s, the common stop and `min_ms` 6000. |
| 335 | `     "runner bwx: a row is not a 6 s common-stop run of bwx at 8000 MT/s with 12 modules")` | Continues the call of line 334: the stop message. |
| 336 | `need({r["boot"] for r in OTHER} == {r["boot"] for r in EIGHT}, "runner bwx: a row is not from the boot of the other 8000 MT/s rows")` | The script stops unless the records of `OTHER` name the same boot as the records of `EIGHT`. |
| 337 | `check(True, f"record counts: {len(USED)} interval records used, all 120 threads, 12 modules; "` | Adds the first line of the self-check list, with the fixed result PASS. The script reaches this line only when all hard assertions above have passed. The text gives the number of records in `USED`. |
| 338 | `            f"7200 MT/s records from 1 boot, 8000 MT/s records from 1 boot; {len(OTHER)} more records of runner bwx (same 8000 MT/s boot) for one note under Table 2")` | Continues the call of line 337: the text also says that each memory speed has one boot, and it gives the number of records in `OTHER`. |

### First rate computation: the sum of the T rows against the rate of the I row (lines 339 to 358)

| Line | Source | Explanation |
|---:|---|---|
| 339 | `# bwx12 and bwx: the page value is the sum of the thread rows. The interval row of the csv prints a rate too: how far the two differ` | Comment: for bwx12 and bwx the page value is the sum of the thread rows. The interval row of the csv file prints a rate too. The next lines measure how far the two differ. |
| 340 | `BWX_USED = [r for r in USED if r["part"] != "A"]` | `BWX_USED`: the records of `USED` outside part A. All of them are bwx12 records [Ref2]. |
| 341 | `IROW_DIFF = [abs(q(val(r)) - i_row_rate(r)) for r in BWX_USED]` | `IROW_DIFF`: one difference per record of `BWX_USED`. `val` (line 176) gives the sum of the 120 T rows. `q` rounds it to 0.01 GB/s. Then the rate printed in the I row (`i_row_rate`, line 158) is subtracted, and `abs` drops the sign. These are the first calls of `val`. So the T rows of all bwx12 records of `USED` are read and checked here. |
| 342 | `IROW_MAX = max(IROW_DIFF)` | `IROW_MAX`: the largest of these differences. |
| 343 | `need(IROW_MAX <= Decimal("0.02"), f"bwx12: an interval row differs from the sum of its thread rows by {IROW_MAX} GB/s")` | The script stops when `IROW_MAX` is above 0.02 GB/s. In these lines the printed rate is only compared. The page value is the sum of the T rows. |
| 344 | `IROW_MAX_X = max(abs(q(val(r)) - i_row_rate(r)) for r in OTHER)` | `IROW_MAX_X`: the same largest difference for the records of `OTHER`. So the T rows of all records of the older runner bwx are read and checked here. |
| 345 | `need(IROW_MAX_X <= Decimal("0.02"), f"runner bwx: an interval row differs from the sum of its thread rows by {IROW_MAX_X} GB/s")` | The script stops when `IROW_MAX_X` is above 0.02 GB/s. In the saved output of a build both largest differences are 0.02 GB/s [Ref5]. |
| 346 | `# part A: the process number inside the file. facts.json counts the processes of rows A-1, A-2 and of the rerun in the same way` | Comment: part A, the number of a process inside its csv file. By the comment, `facts.json` counts the processes of the rows A-1 and A-2 and of the rerun in the same way. |
| 347 | `A_USED = [r for r in USED if r["part"] == "A"]` | `A_USED`: the part A records of `USED`. |
| 348 | `for r in A_USED:` | Goes through these records. |
| 349 | `    r["_fproc"] = file_process(r)` | `file_process` (line 166) checks the csv row of the record and returns the number of its process inside the file. The number is stored in the record under the key `_fproc`. |
| 350 | `need(all(r["_fproc"] == r["process"] for r in A_USED if r["dataset"] != "A-3"), "part A: a process number of facts.json is not the number of the process in its file")` | The script stops when `_fproc` differs from the field `process` of a record. The A-3 records are left out of this test. For A-3 the two numbers differ. `facts.json` numbers the three A-3 processes 1, 2 and 3 [Ref2]. In the file `A3.csv` of the folder `partA-20261113T205055Z` they are the first, the third and the fifth process. |
| 351 | `check(True, f"raw csv rows: {len(BWX_USED)} bwx12 records and {len(OTHER)} bwx records name their interval row and the 120 thread rows after it "` | Adds the second line of the self-check list, with the fixed result PASS. Its text gives the number of bwx12 records and of bwx records that name their interval row and the 120 thread rows after it. |
| 352 | `            f"(printed rate and sum of the thread rows differ by at most {f2(IROW_MAX)} GB/s for bwx12 and {f2(IROW_MAX_X)} GB/s for bwx); "` | Continues the text of line 351: the two largest differences between a printed rate and the sum of the thread rows, `IROW_MAX` and `IROW_MAX_X`, each with 2 decimals. |
| 353 | `            f"{len(A_USED)} part A records name the row with their rate")` | Continues the text of line 351: the number of part A records that name the row with their rate. |
| 356 | `SUM_NOTE = "The rate is the sum of the 120 thread rows after it"` | `SUM_NOTE`: a fixed sentence for the tooltip of a single bwx record. It says that the rate is the sum of the 120 thread rows after the interval row. `src` uses it (line 373). |

### Functions `src` and `hm`: source text for a tooltip, time of day as text (lines 359 to 380)

| Line | Source | Explanation |
|---:|---|---|
| 359 | `def src(recs):` | Starts the function `src`. It returns the source text of a value for a tooltip: the csv file and the line numbers of the records. |
| 360 | `    """Source text for a tooltip: file and line numbers. For bwx12 the lines are interval rows, and the rate is the sum of the thread rows."""` | Comment: the documentation text. The source text holds the file and the line numbers. For bwx12 the lines are interval rows, and the rate is the sum of the thread rows. |
| 361 | `    by = {}` | `by`: a dictionary from the path of a csv file to a list of line numbers. It starts empty. |
| 362 | `    for r in recs:` | Goes through the records. |
| 363 | `        by.setdefault(f"{r['folder']}/{r['file']}", []).append(r["line"])` | Adds the line number of the record (field `line`) to the list of its file. The path has the short form `R/...`: the field `folder`, a slash and the field `file`. |
| 364 | `    bwx = recs[0]["part"] != "A"` | `bwx`: true when the first record is not a part A record. The records then come from a bwx runner. |
| 365 | `    need(all((r["part"] != "A") == bwx for r in recs), "src: part A and bwx12 records in one source text")` | The script stops when one call mixes part A records and bwx records. |
| 367 | `    def one(p, ls):` | Starts the inner function `one`. It returns the text for one csv file: the path `p` and its line numbers `ls`. |
| 368 | `        many = len(ls) > 1` | `many`: true when the file has more than one line number. The text then uses the plural forms. |
| 369 | `        nums = ", ".join(str(x) for x in sorted(ls))` | `nums`: the line numbers in rising order, joined with commas. |
| 370 | `        return f"{p}, interval row{'s' if many else ''} in line{'s' if many else ''} {nums}" if bwx else f"{p} line{'s' if many else ''} {nums}"` | For bwx records the text is the path, then `interval row in line` or `interval rows in lines`, then the numbers. For part A records it is the path, then `line` or `lines`, then the numbers. For part A these lines are the interval rows that hold the rates. |
| 371 | `    out = " and ".join(one(p, ls) for p, ls in by.items())` | `out`: the texts of all files, joined with the word `and`. |
| 372 | `    if bwx:` | For bwx records one more sentence is added. |
| 373 | `        out += ". " + (SUM_NOTE if len(recs) == 1 else "Each rate is the sum of the 120 thread rows after its interval row")` | For one record the sentence is `SUM_NOTE` (line 356). For several records it says that each rate is the sum of the 120 thread rows after its interval row. |
| 374 | `    return out` | Returns the source text. |
| 377 | `def hm(utc, date=False):` | Starts the function `hm`. It turns a time stamp of the form `2026-11-17T22:12:14Z` into the text `22:12 UTC`. |
| 378 | `    return (utc[:10] + " " if date else "") + utc[11:16] + " UTC"` | `utc[11:16]` is the part with the hours and the minutes. The text ` UTC` follows it. With `date` true, the first 10 characters (the date) and a space stand in front, which gives `2026-11-17 22:12 UTC`. |

### Functions `n7200` and `n8000`: the text of n (lines 381 to 405)

| Line | Source | Explanation |
|---:|---|---|
| 381 | `def n7200(recs, pairs=None):` | Starts the function `n7200`. It returns the text of n for records of the 7200 MT/s boot, in four parts. Example: `6 intervals / 3 processes / 3 sessions / 1 boot`. |
| 382 | `    """n as intervals / processes / sessions / boots for records of the 7200 MT/s boot."""` | Comment: the documentation text. n is given as intervals / processes / sessions / boots. |
| 383 | `    ds = {r["dataset"] for r in recs}` | `ds`: the different datasets of the records. |
| 384 | `    np_ = len({r["proc_key"] for r in recs})` | `np_`: the number of processes (different values of `proc_key`). It is part 2 of the text. |
| 385 | `    first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")` | `first`, part 1 of the text: the number of pairs when `pairs` is given, else the number of records as intervals. `plural` (line 220) adds the word. |
| 386 | `    if ds <= {"control-I", "F72d12"}:` | Tests whether all records belong to control I or to F72d12. Between two sets, `<=` means: is a subset of. |
| 387 | `        sess = "no session"` | Then part 3 of the text is `no session`. These rows are not part of a session of `go.sh`. |
| 388 | `    else:` | Every other case: part 3 gives the sessions of the records. |
| 389 | `        named = sorted({r["session"] for r in recs if r["session"] is not None})` | `named`: the different session numbers of the records, sorted. Records without a session number are left out. |
| 390 | `        extra = len({r["proc_key"] for r in recs if r["session"] is None})` | `extra`: the number of processes without a session number. By the field list of `facts.json`, the session is empty for T72C4, the part C process that ran after session 3 [Ref2]. |
| 391 | `        if extra == 0:` | Case without such a process. |
| 392 | `            sess = plural(len(named), "session")` | Part 3 is the count of sessions, for example `3 sessions`. |
| 393 | `            if len(named) < 3:` | Tests whether the records come from fewer than 3 sessions. |
| 394 | `                sess = ("session " if len(named) == 1 else "sessions ") + " and ".join(str(s) for s in named)` | Then part 3 names the sessions: `session 1` for one session, or a list such as `sessions 1 and 3`. |
| 395 | `        else:` | Case with at least one process without a session number. |
| 396 | `            sess = (f"{plural(len(named), 'session')}" if len(named) != 1 else f"session {named[0]}") \` | Part 3 starts with the count of sessions, or with `session N` when there is exactly one session. The statement continues in line 397. |
| 397 | `                   + f" and {extra} extra process"` | Continues line 396: adds the words `and N extra process`, where N is the value of `extra`. Example of the whole part: `3 sessions and 1 extra process`. |
| 398 | `    return f"{first} / {plural(np_, 'process')} / {sess} / 1 boot"` | Returns the four parts, joined with ` / `. Part 4 is the fixed text `1 boot`. Line 312 asserts that all used 7200 MT/s records come from one boot. |
| 401 | `def n8000(recs, pairs=None):` | Starts the function `n8000`. It returns the text of n for 8000 MT/s records. This text has no session part. |
| 402 | `    first = plural(pairs, "pair") if pairs is not None else plural(len(recs), "interval")` | `first`, part 1 of the text, as in line 385: the number of pairs, or the number of records as intervals. |
| 403 | `    return f"{first} / {plural(len({r['proc_key'] for r in recs}), 'process')} / 1 boot"` | Returns part 1, the number of processes and the fixed text `1 boot`. Example: `11 intervals / 7 processes / 1 boot`. Line 313 asserts that all used 8000 MT/s records come from one boot. |

### Question Q1: functions `pairs_in_process`, `drop`, `drops_of` and `drop_txt` (lines 406 to 429)

| Line | Source | Explanation |
|---:|---|---|
| 406 | `# ------------------------------------------------------------------ Q1: drops` | Comment: a section title. The computation for question Q1 follows: the drop of the load-only loop below the old read kernel. |
| 407 | `def pairs_in_process(olds, news):` | Starts the function `pairs_in_process`. It builds the pairs for question Q1 from two record lists of a bwx runner: the old-kernel intervals `olds` and the load-only intervals `news`. |
| 408 | `    """Pairs of (old, load-only) intervals of the same process and round."""` | Comment: the documentation text. A pair is an old-kernel interval and a load-only interval of the same process and round. |
| 409 | `    out = []` | `out`: the list of the pairs. It starts empty. |
| 410 | `    for n in sorted(news, key=lambda r: (r["launch_utc"], r["round"])):` | Goes through the load-only intervals, sorted by launch time and round. |
| 411 | `        o = [x for x in olds if x["proc_key"] == n["proc_key"] and x["round"] == n["round"]]` | `o`: the intervals of `olds` with the same `proc_key` and the same `round` as the load-only interval `n`. |
| 412 | `        need(len(o) == 1, "pair: no single old-kernel interval for a load-only interval")` | The script stops unless exactly one such interval exists. |
| 413 | `        out.append((o[0], n))` | Adds the pair (old-kernel interval, load-only interval). Both intervals come from one process and one round of the kernel sequence. The order inside the round is not tested. In part L and in cfwd the old kernel is timed before the load-only loop of the pair. In crev it is timed after it. |
| 414 | `    return out` | Returns the list of pairs. |
| 417 | `def drop(old, new):` | Starts the function `drop`. It returns by how many percent the rate `new` lies below the rate `old`. |
| 418 | `    return (1 - D(new) / D(old)) * 100` | Returns `(1 - new / old) * 100`, computed with `Decimal` numbers. The result is above 0 when `new` is the lower rate. |
| 421 | `def drops_of(pairs):` | Starts the function `drops_of`. It returns the drop of every pair of a list. |
| 422 | `    return [drop(val(o), val(n)) for o, n in pairs]` | For each pair the old-kernel rate is `old` and the load-only rate is `new`. Both rates come from `val` (line 176). They are not rounded to 0.01 GB/s before the division. |
| 425 | `def drop_txt(ds):` | Starts the function `drop_txt`. It returns the text of a list of drops. |
| 426 | `    lo, hi = f1(min(ds)), f1(max(ds))` | `lo`, `hi`: the lowest and the highest drop of the list, each rounded to 0.1 % by `f1` and turned into text. |
| 427 | `    return f"{lo} %" if lo == hi else f"{lo} % to {hi} %"` | Returns a single value with ` %` when both rounded values are equal. Else it returns both, in the form `30.5 % to 31.2 %`. |

### Question Q1: the drops of all groups (lines 430 to 461)

| Line | Source | Explanation |
|---:|---|---|
| 430 | `Q1 = {}` | `Q1`: a dictionary with one entry per group of pairs. It starts empty. |
| 431 | `Q1["C_ao"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AO))` | Entry `C_ao`: part C, the kernel `read` directly after `oldread`, paired with `oldread` of the same process and round. |
| 432 | `Q1["C_aa"] = dict(pairs=pairs_in_process(C_OLD, C_READ_AA))` | Entry `C_aa`: part C, `read` directly after `asmread`, paired with `oldread` of the same process and round. |
| 433 | `Q1["L"] = dict(pairs=pairs_in_process(L_OLD, L_ASM))` | Entry `L`: part L, `asmread` at position 1 paired with `oldread` at position 0. |
| 434 | `Q1["I"] = dict(pairs=pairs_in_process(I_OLD, I_ASM))` | Entry `I`: the same pairs for control I. |
| 435 | `Q1["F"] = dict(pairs=pairs_in_process(F_OLD, F_ASM))` | Entry `F`: the same pairs for F72d12. |
| 436 | `Q1["L1"] = dict(pairs=pairs_in_process(B_L_OLD["L-1"], B_L_ASM["L-1"]))` | Entry `L1`: the same pairs for the 8000 MT/s row L-1. |
| 437 | `for k, npairs in (("C_ao", 4), ("C_aa", 4), ("L", 6), ("I", 4), ("F", 2), ("L1", 2)):` | Goes through the six groups with their expected numbers of pairs: 4, 4, 6, 4, 2 and 2. |
| 438 | `    need(len(Q1[k]["pairs"]) == npairs, f"Q1 {k}: expected {npairs} pairs")` | The script stops unless the group has this number of pairs. |
| 439 | `    Q1[k]["drops"] = drops_of(Q1[k]["pairs"])` | `drops`: one drop per pair, in percent. Saved output of a build: `C_ao` 30.5 % to 31.2 %, `C_aa` 29.7 % to 31.1 %, `L` 29.2 % to 30.5 % [Ref5]. |
| 440 | `    Q1[k]["old"] = Rg([o for o, _ in Q1[k]["pairs"]])` | `old`: the range of the old-kernel intervals of the pairs. So `old` of `C_ao` holds only the 4 `oldread` intervals of the cfwd processes, and `old` of `C_aa` holds only the 4 of the crev processes. |
| 441 | `    Q1[k]["new"] = Rg([n for _, n in Q1[k]["pairs"]])` | `new`: the range of the load-only intervals of the pairs. |
| 444 | `def a_pair(olds, news, rnd):` | Starts the function `a_pair`. It builds one pair of part A processes for the round `rnd`. In part A the two kernels run in two processes, one per binary. |
| 445 | `    o = Rg([r for r in olds if r["round"] == rnd])` | `o`: the range of the records of the old binary in this round. |
| 446 | `    n = Rg([r for r in news if r["round"] == rnd])` | `n`: the range of the records of the new binary in this round. |
| 447 | `    need(o.n == 3 and n.n == 3 and o.np == 1 and n.np == 1, "part A pair: expected 3 intervals of 1 process per kernel")` | The script stops unless each range has 3 intervals of 1 process. |
| 448 | `    return dict(old=o, new=n, drop=drop(o.med, n.med), round=rnd)` | Returns the two ranges, the round and the drop between the two medians. With 3 intervals the median is the middle one of the 3 rates. It is not always the second interval in time. Example: in session 1, round 1 the 3 rates of `bw_old` are 467.83, 467.92 and 465.38 GB/s in time order. The median is 467.83 GB/s, the first interval [Ref3]. |
| 451 | `A_PAIRS = {}       # (session, round) -> pair of process medians` | `A_PAIRS`: a dictionary from (session, round) to the pair of that session and round. It starts empty. By the comment a pair holds the medians of two processes. |
| 452 | `for s_ in (1, 2, 3):` | Goes through the sessions 1 to 3. |
| 453 | `    for rnd in (1, 2):` | Goes through the rounds 1 and 2. |
| 454 | `        A_PAIRS[(s_, rnd)] = a_pair([r for r in A_OLD if r["session"] == s_], [r for r in A_NEW if r["session"] == s_], rnd)` | Calls `a_pair` with the `bw_old` records and the `bw_new` records of this session. So part A at 7200 MT/s gives 6 pairs. |
| 455 | `A8_PAIRS = {(d, rnd): a_pair(B_A_OLD[d], B_A_NEW[d], rnd) for d in ("A-1", "A-2") for rnd in (1, 2)}` | `A8_PAIRS`: the same at 8000 MT/s: one pair per dataset (A-1, A-2) and round, so 4 pairs. |
| 456 | `Q1["A"] = dict(drops=[p["drop"] for p in A_PAIRS.values()])` | The entry `A` of `Q1`: the drops of the 6 pairs of `A_PAIRS`. |
| 457 | `Q1["A8"] = dict(drops=[p["drop"] for p in A8_PAIRS.values()])` | The entry `A8` of `Q1`: the drops of the 4 pairs of `A8_PAIRS`. |
| 458 | `SAME_LINE_DROPS = Q1["L"]["drops"] + Q1["I"]["drops"] + Q1["F"]["drops"]     # the like.spec line in the 7200 MT/s boot` | `SAME_LINE_DROPS`: the 12 drops of part L, control I and F72d12. By the comment these are the runs of the line of `like.spec` in the 7200 MT/s boot. |
| 459 | `ALL_7200_DROPS = Q1["C_ao"]["drops"] + Q1["C_aa"]["drops"] + SAME_LINE_DROPS + Q1["A"]["drops"]` | `ALL_7200_DROPS`: these 12 drops, the 8 drops of part C and the 6 drops of part A, so 26 drops. |
| 460 | `need(all(d > 0 for d in ALL_7200_DROPS), "a load-only interval is not below the old read kernel")` | The script stops unless each of the 26 drops is above 0. So in every pair at 7200 MT/s the load-only value must lie below the old-kernel value. |

### Question Q2: the ranges, the two fixed wordings, `width_pct` and `wording` (lines 462 to 484)

| Line | Source | Explanation |
|---:|---|---|
| 462 | `# ------------------------------------------------------------------ Q2: ranges` | Comment: a section title. The computation for question Q2 follows: the ranges at 7200 MT/s against the ranges at 8000 MT/s. |
| 463 | `rA_old, rPA_old = Rg(A_OLD), Rg(P_A_OLD)` | `rA_old`: the range of `A_OLD`, the old read kernel in part A. `rPA_old`: the range of the pool `P_A_OLD` (rows A-1 to A-3). The name of a range is `r` and then the name of its group. Building a range calls `val` for each of its records. |
| 464 | `rL_old, rL_asm = Rg(L_OLD), Rg(L_ASM)` | The two ranges of part L: `rL_old` for `oldread` and `rL_asm` for `asmread`. |
| 465 | `rC_old, rI_old, rI_asm, rF_old, rF_asm = Rg(C_OLD), Rg(I_OLD), Rg(I_ASM), Rg(F_OLD), Rg(F_ASM)` | Five more ranges: `oldread` of part C, `oldread` and `asmread` of control I, `oldread` and `asmread` of F72d12. |
| 466 | `rPL_old, rPL_asm = Rg(P_L_OLD), Rg(P_L_ASM)` | The two ranges of the pool L-1 to L-4: `rPL_old` for `oldread` and `rPL_asm` for `asmread`. |
| 467 | `rL1_asm = Rg(B_L_ASM["L-1"])` | `rL1_asm`: the range of `asmread` in row L-1 alone. |
| 468 | `rC_asm_ao = Rg(C_ASM_AO)` | `rC_asm_ao`: the range of the part C intervals of `asmread` directly after `oldread`. |
| 469 | `rC_read_ao, rC_read_aa = Rg(C_READ_AO), Rg(C_READ_AA)` | The two ranges of the kernel `read` in part C: directly after `oldread`, and directly after `asmread`. Lines 463 to 469 build 15 ranges in all. |
| 470 | `WORD_SAME = "no difference seen"` | `WORD_SAME`: the fixed wording of a comparison whose two ranges overlap. |
| 471 | `WORD_DIFF = "differs between the 8000 MT/s boot and the 7200 MT/s boot"` | `WORD_DIFF`: the fixed wording of a comparison whose two ranges do not overlap. |
| 472 | `need(FJ["verdicts"]["rule_wordings"]["same"] == WORD_SAME and FJ["verdicts"]["rule_wordings"]["differs"] == WORD_DIFF,` | The script stops when the two wordings are not equal to the two texts that `facts.json` stores under `verdicts.rule_wordings`. |
| 473 | `     "the fixed wordings differ from facts.json")` | Continues the call of line 472: the stop message. |
| 476 | `def width_pct(rg):` | Starts the function `width_pct`. It returns the width of a range in percent of its lower end. |
| 477 | `    """Width of a range in percent of its lower end: the size that a 'no difference seen' test cannot exclude (est.)."""` | Comment: the documentation text. It names the use: this width is the size of a difference that a result `no difference seen` cannot exclude. The comment marks the value as an estimate (est.). |
| 478 | `    return (rg.hi - rg.lo) / rg.lo * 100` | Returns `(hi - lo) / lo * 100`. |
| 481 | `def wording(r7, r8):` | Starts the function `wording`. It returns the fixed text of one comparison of a 7200 MT/s range `r7` with an 8000 MT/s range `r8`. |
| 482 | `    return WORD_SAME if r7.overlaps(r8) else WORD_DIFF` | Returns `WORD_SAME` when the two ranges overlap, else `WORD_DIFF`. So only the lowest and the highest rate of each group decide the wording. |

### Question Q2: the expected results of the old read kernel and of the load-only loop (lines 485 to 507)

| Line | Source | Explanation |
|---:|---|---|
| 485 | `# old read kernel` | Comment: the next lines handle the old read kernel. |
| 486 | `need(rA_old.overlaps(rPA_old) and rC_old.overlaps(rPL_old) and rF_old.overlaps(rPL_old) and rI_old.overlaps(rPL_old),` | The script stops unless four pairs of ranges overlap: part A with the pool A-1 to A-3, and part C, F72d12 and control I each with the `oldread` pool L-1 to L-4. |
| 487 | `     "old read: an expected overlap is missing")` | Continues the call of line 486: the stop message. |
| 488 | `need(not rL_old.overlaps(rPL_old) and rL_old.hi < rPL_old.lo, "old read, part L: expected below the 8000 MT/s pool")` | The script also stops unless the `oldread` range of part L lies fully below the pool L-1 to L-4. The line tests two things: no overlap, and the highest rate of part L is below the lowest rate of the pool. |
| 489 | `L_OLD_NEAR = rL_old.nearest(rPL_old)                       # negative: part L is lower` | `L_OLD_NEAR`: the distance of the nearest ends, part L against the pool. By the comment it is negative: part L is the lower range. Saved output of a build: part L 461.61 to 464.29 GB/s, pool 465.53 to 470.05 GB/s, nearest ends -1.24 GB/s [Ref5]. |
| 490 | `L_OLD_MED = rL_old.med - rPL_old.med` | `L_OLD_MED`: the median of part L minus the median of the pool. In the saved output of a build the two medians are 6.27 GB/s apart [Ref5]. |
| 491 | `L_OLD_NEAR_PCT = abs(L_OLD_NEAR) / rPL_old.lo * 100        # percent of the lower end of the 8000 MT/s range` | `L_OLD_NEAR_PCT`: the size of the first distance in percent of the lower end of the pool range. |
| 492 | `L_OLD_MED_PCT = abs(L_OLD_MED) / rPL_old.med * 100         # percent of the 8000 MT/s median` | `L_OLD_MED_PCT`: the size of the second distance in percent of the pool median. |
| 493 | `# load-only loop` | Comment: the next lines handle the load-only loop. They are hard assertions on the `asmread` ranges. |
| 494 | `need(not rL_asm.overlaps(rPL_asm) and rL_asm.lo > rPL_asm.hi, "asmread, part L: expected above the 8000 MT/s pool")` | The script stops unless part L lies fully above the pool L-1 to L-4: no overlap, and the lowest rate of part L is above the highest rate of the pool. |
| 495 | `need(rF_asm.overlaps(rPL_asm), "asmread, F72d12: expected inside the 8000 MT/s pool")` | The script stops unless F72d12 overlaps the pool. |
| 496 | `need(rPL_asm.lo <= rF_asm.lo and rF_asm.hi <= rPL_asm.hi, "asmread, F72d12: expected inside the 8000 MT/s pool")` | The script stops unless F72d12 lies inside the range of the pool: not below its lowest rate and not above its highest rate. |
| 497 | `need(not rI_asm.overlaps(rPL_asm) and rI_asm.lo > rPL_asm.hi, "asmread, control I: expected above the 8000 MT/s pool")` | The script stops unless control I lies fully above the pool. |
| 498 | `need(not rC_asm_ao.overlaps(rPL_asm), "asmread after oldread, part C: expected above the 8000 MT/s pool")` | The script stops unless part C, `asmread` directly after `oldread`, does not overlap the pool. This line does not test which of the two ranges is higher, although its stop message says `expected above`. Lines 2066 to 2068 test later that part C is the higher one. |
| 499 | `need(not rF_asm.overlaps(rL_asm) and not rF_asm.overlaps(rI_asm) and not rI_asm.overlaps(rL_asm),` | The script stops unless the ranges of F72d12, part L and control I do not overlap each other. |
| 500 | `     "the three visits of the 7200 MT/s boot overlap")` | Continues the call of line 499: the stop message. |
| 501 | `VISIT_LO, VISIT_HI = min(rF_asm.lo, rL_asm.lo, rI_asm.lo), max(rF_asm.hi, rL_asm.hi, rI_asm.hi)` | `VISIT_LO`, `VISIT_HI`: the lowest and the highest `asmread` rate over the three visits of the part L line in the 7200 MT/s boot (F72d12, part L, control I). |
| 502 | `VISIT_OLD_LO, VISIT_OLD_HI = min(rF_old.lo, rL_old.lo, rI_old.lo), max(rF_old.hi, rL_old.hi, rI_old.hi)` | `VISIT_OLD_LO`, `VISIT_OLD_HI`: the same two values for `oldread`. |
| 503 | `DIST = {  # the same kind of distance on both sides: part L against the 8000 MT/s pool, part L against F72d12` | `DIST`: three kinds of distance for the `asmread` range of part L. In each pair the first value is against the pool L-1 to L-4, and the second is against F72d12. By the comment both sides use the same kind of distance. |
| 504 | `    "nearest": (rL_asm.nearest(rPL_asm), rL_asm.nearest(rF_asm)),` | Entry `nearest`: the distance of the nearest ends. |
| 505 | `    "medians": (rL_asm.med - rPL_asm.med, rL_asm.med - rF_asm.med),` | Entry `medians`: the difference of the medians, part L minus the other range. |
| 506 | `    "farthest": (rL_asm.farthest(rPL_asm), rL_asm.farthest(rF_asm)),` | Entry `farthest`: the distance of the farthest ends. |
| 507 | `}` | Ends the dictionary `DIST` of line 503. |

### Part A by rule V3, the pool without its lowest interval, function `one_process` (lines 508 to 538)

| Line | Source | Explanation |
|---:|---|---|
| 508 | `# part A, new read kernel: session 1 against the 8000 MT/s processes of the same round (rule V3)` | Comment: part A, new read kernel. Session 1 is compared with the 8000 MT/s processes of the same round. The comment names the rule: V3. |
| 509 | `A_V3 = {}` | `A_V3`: a dictionary with one entry per round. It starts empty. |
| 510 | `for rnd in (1, 2):` | Goes through the rounds 1 and 2. |
| 511 | `    r7 = Rg([r for r in A_NEW if r["session"] == 1 and r["round"] == rnd])` | `r7`: the range of the `bw_new` intervals of session 1 in this round. Sessions 2 and 3 are not compared here. |
| 512 | `    r8 = Rg([r for d in ("A-1", "A-2") for r in B_A_NEW[d] if r["round"] == rnd])` | `r8`: the range of the `bw_new` intervals of A-1 and A-2 in the same round. |
| 513 | `    need(r7.n == 3 and r7.np == 1 and r8.n == 6 and r8.np == 2, "part A, rule V3: record counts")` | The script stops unless `r7` holds 3 intervals of 1 process and `r8` holds 6 intervals of 2 processes. |
| 514 | `    need(not r7.overlaps(r8) and r7.lo > r8.hi, "part A, session 1: expected above the 8000 MT/s range of the round")` | The script stops unless `r7` lies fully above `r8`. |
| 515 | `    A_V3[rnd] = dict(r7=r7, r8=r8, near=r7.nearest(r8),` | Stores the two ranges and `near`, the distance of their nearest ends, as the entry of this round. |
| 516 | `                     p7=sorted({r["passes"] for r in r7.recs}), p8=sorted(r["passes"] for r in r8.recs))` | Continues line 515: `p7` and `p8`, the pass counts of the intervals (field `passes`). `p7` holds each different pass count of session 1 once. `p8` holds the pass count of each of the 6 intervals at 8000 MT/s. |
| 517 | `need(all(len(A_V3[rnd]["p7"]) == 1 for rnd in (1, 2)), "part A, session 1, bw_new read: more than one pass count in a round")` | The script stops unless the 3 intervals of session 1 have one pass count in each round. |
| 519 | `# the pool L-1 to L-4 without the interval that holds the lowest asmread value (machine state section)` | Comment: the pool L-1 to L-4 without the interval that holds the lowest `asmread` value. By the comment the page section on the machine state uses the result. |
| 520 | `LOWEST_ASM = min(P_L_ASM, key=val)` | `LOWEST_ASM`: the record with the lowest `asmread` rate of the pool L-1 to L-4. `min` compares the records by their value of `val`. |
| 521 | `rPL_asm_wo = Rg([r for r in P_L_ASM if r is not LOWEST_ASM])` | `rPL_asm_wo`: the range of the pool without this one interval. It comes from 10 of the 11 `asmread` intervals. |
| 522 | `need(rL_asm.lo > rPL_asm_wo.hi, "part L does not lie above the pool without its lowest interval")` | The script stops unless the lowest `asmread` rate of part L is above the highest rate of this smaller pool. |
| 524 | `# part A, old read kernel: the 7200 MT/s range is wider than the 8000 MT/s range, and some of its intervals lie outside that range` | Comment: part A, old read kernel. The 7200 MT/s range is wider than the 8000 MT/s range, and some of its intervals lie outside that range. The next lines assert this. |
| 525 | `A_OLD_BELOW = [r for r in A_OLD if val(r) < rPA_old.lo]` | `A_OLD_BELOW`: the part A intervals of the old read kernel with a rate below the lowest rate of the pool A-1 to A-3. |
| 526 | `A_OLD_ABOVE = [r for r in A_OLD if val(r) > rPA_old.hi]` | `A_OLD_ABOVE`: those with a rate above the highest rate of the pool. |
| 527 | `A_OLD_W7, A_OLD_W8 = rA_old.hi - rA_old.lo, rPA_old.hi - rPA_old.lo` | `A_OLD_W7`, `A_OLD_W8`: the width (highest minus lowest rate) of the 7200 MT/s range and of the pool range, in GB/s. |
| 528 | `need(A_OLD_BELOW and A_OLD_ABOVE and A_OLD_W7 > A_OLD_W8, "part A, old read: the 7200 MT/s range is not wider than the 8000 MT/s range on both sides")` | The script stops unless both lists hold at least one record and the 7200 MT/s range is the wider one. |
| 531 | `def one_process(recs):` | Starts the function `one_process`. It names the one part A process that a list of 3 records comes from. Later code calls it for `A_OLD_BELOW` and for `A_OLD_ABOVE` (line 2087). |
| 532 | `    """'session s, round r' when the records are all intervals of one process of part A, else a stop."""` | Comment: the documentation text. The result is the text `session s, round r` when the records are all intervals of one process of part A. Else the script stops. |
| 533 | `    key = {(r["session"], r["round"], r["proc_key"]) for r in recs}` | `key`: the different groups (session, round, `proc_key`) of the records. |
| 534 | `    need(len(key) == 1 and len(recs) == 3, "part A, old read: the intervals outside the 8000 MT/s range are not the 3 intervals of one process")` | The script stops unless the list has exactly 3 records with one session, one round and one `proc_key`. |
| 535 | `    s_, rnd, _ = next(iter(key))` | Takes the session and the round from the one group. The third value, `proc_key`, is not used. |
| 536 | `    return f"session {s_}, round {rnd}"` | Returns the text `session s, round r` with these two numbers. |

### Part C against the rows of the older runner bwx (lines 539 to 554)

| Line | Source | Explanation |
|---:|---|---|
| 539 | `# rows of runner bwx (another binary): ranges with the same kernel directly before, for the note under Table 2` | Comment: rows of the runner bwx, another binary. The next lines build ranges with the same kernel directly before, for the note under Table 2. |
| 540 | `need({r["pos"] for r in C_ASM_AR} == {2} and {r["file"] for r in C_ASM_AR} == {"cfwd.csv"}, "part C, asmread after read: not position 2 of cfwd")` | The script stops unless the part C intervals of `asmread` directly after `read` are all at position 2 of the file `cfwd.csv`. |
| 541 | `rC_asm_ar = Rg(C_ASM_AR)` | `rC_asm_ar`: the range of these part C intervals. |
| 542 | `rX_read_ao, rX_read_aa, rX_asm_ar = Rg(X_READ_AO), Rg(X_READ_AA), Rg(X_ASM_AR)` | Three ranges of the runner bwx: `read` at position 1 (directly after `oldread`), `read` at position 6 (directly after `asmread`) and `asmread` at position 2 (directly after `read`). Lines 327 to 328 asserted the kernel directly before. |
| 543 | `X_PAIRS = [(rC_read_ao, rX_read_ao), (rC_read_aa, rX_read_aa), (rC_asm_ar, rX_asm_ar)]` | `X_PAIRS`: three pairs. Each puts a part C range next to the bwx range with the same kernel and the same kernel directly before. |
| 544 | `need(all(c.lo > x.hi for c, x in X_PAIRS), "part C: a group does not lie above the bwx rows with the same kernel directly before")` | The script stops unless each part C range lies fully above its bwx range. |
| 545 | `X_ABOVE = [c.nearest(x) for c, x in X_PAIRS]` | `X_ABOVE`: the three distances of the nearest ends, each for a part C range above its bwx range. |
| 546 | `X_MAX_READ = max(val(r) for r in X_LOADS if r["kernel"] == "read")` | `X_MAX_READ`: the highest `read` rate of all records of `X_LOADS`. |
| 547 | `X_MAX_ASM = max(val(r) for r in X_LOADS if r["kernel"] == "asmread")` | `X_MAX_ASM`: the highest `asmread` rate of all records of `X_LOADS`. |
| 548 | `need(X_MAX_READ == max(rX_read_ao.hi, rX_read_aa.hi) and X_MAX_ASM == rX_asm_ar.hi, "runner bwx: the highest read or asmread value is not in the three ranges used")` | The script stops unless these two maxima are upper ends of the three bwx ranges of line 542. So no `asmread` interval at position 5 holds a higher rate than the highest one at position 2. |
| 549 | `X_REV_MAX_READ, X_REV_MAX_ASM = max(val(r) for r in X_REV_READ), max(val(r) for r in X_REV_ASM)` | `X_REV_MAX_READ`, `X_REV_MAX_ASM`: the highest `read` rate and the highest `asmread` rate of the reverse-order processes. |
| 550 | `need(X_REV_MAX_READ > X_MAX_READ and X_REV_MAX_ASM > X_MAX_ASM, "runner bwx: the reverse-order processes do not hold higher values")` | The script stops unless each is above the maximum of `X_LOADS` for the same kernel. |
| 551 | `need(rC_read_ao.lo <= X_REV_MAX_READ <= rC_read_ao.hi and rC_read_aa.lo <= X_REV_MAX_READ <= rC_read_aa.hi,` | The script stops unless the highest reverse-order `read` rate lies inside both `read` ranges of part C. |
| 552 | `     "runner bwx, reverse order: the highest read value is not inside both read ranges of part C")` | Continues the call of line 551: the stop message. |
| 553 | `need(rL_asm.lo <= X_REV_MAX_ASM <= rL_asm.hi, "runner bwx, reverse order: the highest asmread value is not inside the asmread range of part L")` | The script stops unless the highest reverse-order `asmread` rate lies inside the `asmread` range of part L. |

### Cross-check helpers: `md_sections`, `md_tables`, `SEC`, `col` and `facts_row` (lines 555 to 609)

| Line | Source | Explanation |
|---:|---|---|
| 555 | `# ------------------------------------------------------------------ cross-check with FACTS.md and facts.json verdicts` | Comment: a section title. The cross-check follows: the computed values are compared with `FACTS.md` and with the verdict records of `facts.json`. |
| 556 | `def md_sections(md):` | Starts the function `md_sections`. It splits the text of `FACTS.md` at its headings and returns a dictionary from a section key to the section text. |
| 557 | `    secs, cur = {}, None` | `secs`: the dictionary of the sections. `cur`: the key of the section that is read now. It has no value before the first heading. |
| 558 | `    for line in md.splitlines():` | Goes through the text line by line. |
| 559 | `        m = re.match(r"^#{2,3} (.*)$", line)` | Tests whether the line is a heading. The pattern matches 2 or 3 `#` characters at the start of the line and then a space. The group holds the rest of the line, the text of the heading. |
| 560 | `        if m:` | A heading starts a new section. |
| 561 | `            k = re.match(r"^(\d+(?:\.\d+)?)[. ]", m.group(1))` | Looks for a number at the start of the heading text: digits, then an optional dot with more digits. A dot or a space must follow. The group holds the number, for example `0`, `3.4` or `4.9`. |
| 562 | `            cur = k.group(1) if k else "#" + m.group(1)` | The key of the section is this number. A heading without a number gets the key `#` plus its text. |
| 563 | `            secs[cur] = []` | Starts an empty list of lines for the section. |
| 564 | `        elif cur is not None:` | A line that is not a heading and that follows a heading. |
| 565 | `            secs[cur].append(line)` | Adds the line to the section. So the text of a section runs up to the next heading of these two levels. The text of section `3` ends where section `3.1` starts. Lines before the first heading are dropped. |
| 566 | `    return {k: "\n".join(v) for k, v in secs.items()}` | Returns the dictionary. The lines of each section are joined to one text. |
| 569 | `def md_tables(text):` | Starts the function `md_tables`. It parses the Markdown tables of a text and returns a list with one entry per table. A Markdown table is a group of text lines that start with the character `\|`. The cells stand between these characters. |
| 570 | `    tables, cur = [], None` | `tables`: the list of the tables. `cur`: the table that is read now. It has no value outside a table. |
| 571 | `    for line in text.splitlines():` | Goes through the text line by line. |
| 572 | `        if line.startswith("\|"):` | A line that starts with `\|` belongs to a table. |
| 573 | `            cells = [c.strip() for c in line.strip().strip("\|").split("\|")]` | `cells`: the cells of the line. The line loses the spaces and the `\|` characters at both ends. Then it is split at each `\|`, and each cell loses the spaces at its ends. |
| 574 | `            if cur is None:` | Tests whether this is the first line of a table. |
| 575 | `                cur = {"head": cells, "rows": []}` | The first line gives the column titles (`head`). The list of the rows starts empty. |
| 576 | `                tables.append(cur)` | Adds the new table to the list. |
| 577 | `            elif set("".join(cells)) <= set("-: "):` | A later line whose cells hold only the characters `-`, `:` and space. This is the separator line of the table. |
| 578 | `                continue` | The separator line is skipped. |
| 579 | `            else:` | Every other line of the table. |
| 580 | `                cur["rows"].append(dict(zip(cur["head"], cells)))` | It becomes one dictionary from column title to cell text. The dictionary is added to the rows of the table. |
| 581 | `        else:` | A line that does not start with `\|`. |
| 582 | `            cur = None` | It ends the table. |
| 583 | `    return tables` | Returns the list of the tables. |
| 586 | `SEC = md_sections(FMD)` | `SEC`: the sections of `FACTS.md`. It maps a section number, for example `3.4`, to the text of that section. |
| 587 | `for k_ in ("0", "3.1", "3.2", "3.3", "3.4", "4.2", "4.3", "4.4", "4.5", "4.6", "4.9"):` | Goes through the numbers of 11 sections. These are the sections that the cross-checks of lines 652 to 767 read. Section `1.5`, which line 1378 reads, is not in this list. |
| 588 | `    need(k_ in SEC and SEC[k_].strip(), f"FACTS.md: section {k_} not found")` | The script stops unless the section exists and holds text. |
| 589 | `NUM = r"[-+]?\d+(?:\.\d+)?"` | `NUM`: the regular expression for one number: an optional sign, digits, and an optional decimal part. |
| 592 | `def col(row, start):` | Starts the function `col`. It returns the cell of a table row whose column title starts with the text `start`. The callers use it for long titles. |
| 593 | `    ks = [k for k in row if k.startswith(start)]` | `ks`: the column titles of the row that start with `start`. |
| 594 | `    need(len(ks) == 1, f"FACTS.md table: no single column that starts with '{start}'")` | The script stops unless exactly one column title of the row starts with that text. |
| 595 | `    return row[ks[0]]` | Returns the cell of that column. Example: line 703 finds the title `Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)` with the start `Distance of the nearest ends`. |
| 598 | `def facts_row(sec, where, what):` | Starts the function `facts_row`. It finds one table row of a section of `FACTS.md`. `where` is a test function for a row. `what` names the row in the stop message. |
| 599 | `    """The first table row of a FACTS.md section for which where(row) is true."""` | Comment: the documentation text. The result is the first table row of the section for which `where(row)` is true. |
| 600 | `    for t in md_tables(SEC[sec]):` | Goes through all tables of the section, in their order. |
| 601 | `        for row in t["rows"]:` | Goes through the rows of the table. |
| 602 | `            try:` | Starts the block whose error line 605 handles. |
| 603 | `                if where(row):` | Applies the test to the row. |
| 604 | `                    return row` | Returns the first row that passes the test. |
| 605 | `            except KeyError:` | A test can read a column that the table of this row does not have. Python then raises `KeyError`. |
| 606 | `                continue` | Such a row is skipped. |
| 607 | `    stop(f"FACTS.md section {sec}: row not found: {what}")` | The script stops when no row of the section passes the test. |

### Cross-check helpers: `rng_of`, `near` and the five `xc` functions (lines 610 to 651)

| Line | Source | Explanation |
|---:|---|---|
| 610 | `def rng_of(cell):` | Starts the function `rng_of`. It reads a range from the text of a table cell. |
| 611 | `    m = re.search(rf"({NUM}) to ({NUM})", cell)` | Finds the first text of the form `number to number` in the cell. The two groups hold the two numbers. |
| 612 | `    need(m, f"FACTS.md: no range in cell '{cell}'")` | The script stops when the cell holds no such text. |
| 613 | `    return Decimal(m.group(1)), Decimal(m.group(2))` | Returns the two numbers as `Decimal`. |
| 616 | `def near(a, b, tol):` | Starts the function `near`. It is the comparison that the cross-checks use for rates, distances and percent values. `tol` is the tolerance: the largest allowed difference. |
| 617 | `    return abs(D(a) - D(b)) <= Decimal(tol)` | Converts both values to `Decimal`. True when they differ by at most `tol`. |
| 620 | `def xc_range(label, rg_lo, rg_hi, cell, tol="0.01", unit="GB/s", fmt=f2):` | Starts the function `xc_range`. It adds a check: a computed range against the range in a table cell of `FACTS.md`. The default tolerance is 0.01, for a rate in GB/s. |
| 621 | `    lo, hi = rng_of(cell)` | `rng_of` reads the two numbers of the `FACTS.md` cell. |
| 622 | `    check(near(q(rg_lo, tol), lo, tol) and near(q(rg_hi, tol), hi, tol),` | `q` (line 90) rounds the computed lowest value and the computed highest value to the rounding step `tol`. The check passes when each rounded value differs from its `FACTS.md` number by at most `tol`. So a difference of 0.01 GB/s in the last digit still passes. |
| 623 | `          f"{label}: computed {fmt(rg_lo)} to {fmt(rg_hi)} {unit}, FACTS.md {lo} to {hi} {unit}")` | Continues the call of line 622: the text of the check. It prints both ranges, the computed one and the one of `FACTS.md`. After a FAIL the script continues, and it does not write the page at the end. |
| 626 | `def xc_val(label, mine, cell, tol="0.01", unit="GB/s", fmt=f2):` | Starts the function `xc_val`. It does the same for one value: a computed value against a table cell of `FACTS.md`. The callers pass the tolerance 0.01 for a rate in GB/s and 0.1 for a percent value. |
| 627 | `    m = re.search(NUM, cell)` | Takes the first number of the cell, with its sign. |
| 628 | `    need(m, f"FACTS.md: no number in cell '{cell}'")` | The script stops when the cell holds no number. |
| 629 | `    theirs = Decimal(m.group(0))` | `theirs`: the number of `FACTS.md` as a `Decimal`. |
| 630 | `    check(near(q(mine, tol), theirs, tol), f"{label}: computed {fmt(mine)} {unit}, FACTS.md {theirs} {unit}")` | The computed value is rounded to `tol` and compared with `near`. The text of the check prints both values. |
| 633 | `def xc_text(label, sec, value, unit, tol="0.01", fmt=f2):` | Starts the function `xc_text`. It is for a value that `FACTS.md` gives in a sentence and not in a table cell. |
| 634 | `    """A number with this unit, equal within the tolerance, stands in the text of a FACTS.md section."""` | Comment: the documentation text. The check passes when a number with this unit, equal within the tolerance, stands in the text of a section of `FACTS.md`. |
| 635 | `    found = [Decimal(x) for x in re.findall(rf"({NUM}) ?{re.escape(unit)}", SEC[sec])]` | `found`: every number of the section text that is followed by the unit, with at most one space between them. `re.escape` makes the unit a literal text of the pattern. |
| 636 | `    check(any(near(q(abs(D(value)), tol), x, tol) for x in found),` | Takes the computed value without its sign (`abs`) and rounds it to `tol`. The check passes when at least one collected number differs from it by at most `tol`. The check does not test which sentence holds the number. |
| 637 | `          f"{label}: computed {fmt(abs(D(value)))} {unit}, present in FACTS.md section {sec}")` | Continues the call of line 636: the text of the check. It prints the computed value and the number of the section. It does not print the number that was found. |
| 640 | `def xc_text_range(label, sec, lo, hi, unit_mid, tol, fmt):` | Starts the function `xc_text_range`. It adds a check: a computed range against the text of a section of `FACTS.md`. |
| 641 | `    found = re.findall(rf"({NUM}){re.escape(unit_mid)} to ({NUM})", SEC[sec])` | `found`: every text of this form in the section: a number, the text `unit_mid`, the word `to`, a number. Example with ` %` as `unit_mid`: the text `30.5 % to 31.2`. |
| 642 | `    check(any(near(q(lo, tol), Decimal(a), tol) and near(q(hi, tol), Decimal(b), tol) for a, b in found),` | The check passes when one collected pair of numbers differs from the two rounded computed values by at most `tol` each. As in `xc_text`, the place of the text inside the section is not tested. |
| 643 | `          f"{label}: computed {fmt(lo)} to {fmt(hi)}, present in FACTS.md section {sec}")` | Continues the call of line 642: the text of the check, with the computed range only. |
| 646 | `def xc_drops(label, ds, row):` | Starts the function `xc_drops`. It adds a check: the lowest and the highest drop of a list against a table row of `FACTS.md`. |
| 647 | `    lo, hi = Decimal(col(row, "Smallest drop")), Decimal(col(row, "Largest drop"))` | `lo`, `hi`: the two numbers to compare with. They come from the columns `Smallest drop` and `Largest drop` of the `FACTS.md` row. |
| 648 | `    check(near(q(min(ds), "0.1"), lo, "0.1") and near(q(max(ds), "0.1"), hi, "0.1"),` | Rounds the lowest and the highest computed drop to 0.1 (percent). The check passes when each differs from its `FACTS.md` number by at most 0.1. The drops of the list were computed with `drop` (line 417) from rates that this script had not rounded for printing. For a bwx12 pair, the two rates are values of `val`, rounded to 6 decimals (line 188). For part A, the two rates are medians. Each is the median of the 3 rates of one process, as the csv file holds them (2 decimals). |
| 649 | `          f"{label}: computed {f1(min(ds))} % to {f1(max(ds))} %, FACTS.md {lo} % to {hi} %")` | Continues the call of line 648: the text of the check. It prints both pairs of values. |

### Cross-check of question Q1 with `FACTS.md` (lines 652 to 682)

| Line | Source | Explanation |
|---:|---|---|
| 652 | `# Q1 (headline values)` | Comment: the cross-check of question Q1 starts. By the comment these are headline values of the page. |
| 653 | `T34 = lambda part, frag: facts_row("3.4", lambda r: r["Part"].startswith(part) and frag in r["Pair"], f"{part} {frag}")` | `T34`: a lambda that returns one row of the table in `FACTS.md` section 3.4. The column `Part` of that row starts with the first text, and its column `Pair` holds the second text. |
| 654 | ``xc_drops("Q1 part C, read directly after oldread", Q1["C_ao"]["drops"], T34("C", "`read` (new read kernel) directly after `oldread`"))`` | `xc_drops` (line 646) compares the drops of the entry `C_ao` of `Q1` (line 430) with that table: part C, bwx12 kernel `read` directly after `oldread` (4 pairs). The saved output of a build shows 30.5 % to 31.2 %, both computed and in `FACTS.md` [Ref5]. |
| 655 | ``xc_drops("Q1 part C, read directly after asmread", Q1["C_aa"]["drops"], T34("C", "`read` (new read kernel) directly after `asmread`"))`` | The same for the entry `C_aa`: part C, `read` directly after `asmread` (4 pairs). The saved output of a build shows 29.7 % to 31.1 %, both computed and in `FACTS.md` [Ref5]. |
| 656 | `xc_drops("Q1 part L, asmread against oldread", Q1["L"]["drops"], T34("L", "asmread"))` | The same for part L: `asmread` against `oldread` (6 pairs). |
| 657 | `xc_drops("Q1 part A, process medians", Q1["A"]["drops"], T34("A", "bw_new"))` | The same for part A: the 6 drops between the medians of two processes. |
| 658 | `xc_drops("Q1 control I", Q1["I"]["drops"], T34("I (control", "asmread"))` | The same for control I (4 pairs). Its row is found by the start `I (control` of the column `Part`. |
| 659 | `xc_drops("Q1 F72d12", Q1["F"]["drops"], T34("F72d12", "asmread"))` | The same for F72d12 (2 pairs). These are six `xc_drops` calls. The table has 9 rows [Ref1]. Its three rows for `asmread` in part C have no check here. |
| 660 | `G33 = lambda g: facts_row("3.3", lambda r: r["Group"].startswith(g), g)` | `G33`: a lambda that returns the row of `FACTS.md` section 3.3 whose column `Group` starts with the given text. |
| 661 | `xc_range("part C, read after oldread", rC_read_ao.lo, rC_read_ao.hi, col(G33("read after oldread"), "Min to max"))` | `xc_range` (line 620) compares the lowest and the highest rate of a part C group with the column `Min to max` of its row. This call handles `read` after `oldread` (4 intervals). |
| 662 | `xc_range("part C, read after asmread", rC_read_aa.lo, rC_read_aa.hi, col(G33("read after asmread"), "Min to max"))` | The same for `read` after `asmread` (4 intervals). |
| 663 | `xc_range("part C, oldread", rC_old.lo, rC_old.hi, col(G33("oldread, all positions"), "Min to max"))` | The same for all `oldread` intervals of part C (8 intervals). |
| 664 | `for key_, ds in (("C_ao", Q1["C_ao"]["drops"]), ("C_aa", Q1["C_aa"]["drops"]), ("L", Q1["L"]["drops"]), ("A", Q1["A"]["drops"])):` | Goes through four lists of drops: the two of part C, the one of part L and the one of part A. |
| 665 | `    xc_text_range(f"Q1 drop {key_} in the Short version of FACTS.md", "0", min(ds), max(ds), " %", "0.1", f1)` | `xc_text_range` (line 640) tests that section 0 of `FACTS.md`, its Short version, holds this drop range, to 0.1 percent. |
| 666 | `g0 = len(CHECKS)` | `g0`: the length of `CHECKS` before the next loop. `grouped` needs it in line 673. |
| 667 | `for (s_, rnd), p in A_PAIRS.items():` | Goes through the 6 entries of `A_PAIRS` (line 451): one set of comparisons per session and round of part A. |
| 668 | `    row = facts_row("3.1", lambda r, s_=s_, rnd=rnd: r["Session"] == str(s_) and r["Round"] == str(rnd) and "New below old, %" in r,` | `facts_row` finds the row of section 3.1 with the same `Session` and `Round`, in the table that has the column `New below old, %`. The lambda takes `s_` and `rnd` as default values. So it keeps the values of this loop pass. |
| 669 | `                    f"session {s_} round {rnd}")` | Continues the call of line 668: the name of the row for the stop message. |
| 670 | `    xc_val(f"part A session {s_} round {rnd}, median bw_old read", p["old"].med, row["bw_old read, median GB/s"])` | `xc_val` (line 626) compares the median of the 3 intervals of `bw_old read` with the column `bw_old read, median GB/s`, to 0.01 GB/s. |
| 671 | `    xc_val(f"part A session {s_} round {rnd}, median bw_new read", p["new"].med, row["bw_new read, median GB/s"])` | The same for the median of the 3 intervals of `bw_new read`. |
| 672 | `    xc_val(f"part A session {s_} round {rnd}, new below old", p["drop"], row["New below old, %"], "0.1", "%", f1)` | `xc_val` compares the drop between the two medians with the column `New below old, %`, to 0.1 percent. |
| 673 | `grouped("FACTS.md section 3.1, part A per session and round: medians of bw_old read and bw_new read (0.01 GB/s) and the drop (0.1 %)", g0)` | `grouped` (line 56) replaces the 18 lines of the loop by one line that counts the equal comparisons. |
| 674 | `g0 = len(CHECKS)` | `g0`: the length of `CHECKS` before the next loop. |
| 675 | `for o, n in Q1["L"]["pairs"] + Q1["I"]["pairs"] + Q1["F"]["pairs"]:` | Goes through the 12 pairs of part L (6), control I (4) and F72d12 (2). |
| 676 | `    tag = n["tag"] if n["dataset"] != "F72d12" else "F72d12"` | `tag`: the folder tag of the pair. For F72d12 the text `F72d12` is used in place of the folder tag. |
| 677 | `    row = facts_row("3.2", lambda r, tag=tag, n=n: r["Folder tag or row"] == tag and r["Round"] == str(n["round"]), f"{tag} round {n['round']}")` | `facts_row` finds the row of section 3.2 by its column `Folder tag or row` and by the round. |
| 678 | `    xc_val(f"{tag} round {n['round']}, oldread", val(o), row["oldread, GB/s"])` | `xc_val` compares the `oldread` rate of the pair, a value of `val`, with the column `oldread, GB/s`, to 0.01 GB/s. |
| 679 | `    xc_val(f"{tag} round {n['round']}, asmread", val(n), row["asmread, GB/s"])` | The same for the `asmread` rate of the pair. |
| 680 | `    xc_val(f"{tag} round {n['round']}, asmread below oldread", drop(val(o), val(n)), row["asmread below oldread, %"], "0.1", "%", f1)` | `xc_val` compares the drop of the pair with the column `asmread below oldread, %`, to 0.1 percent. |
| 681 | `grouped("FACTS.md section 3.2, part L, control I and F72d12 per process and round: oldread and asmread (0.01 GB/s) and the drop (0.1 %)", g0)` | `grouped` joins the 36 comparisons of the loop into one line. |

### Cross-check of question Q2 with `FACTS.md`: old read kernel (lines 683 to 710)

| Line | Source | Explanation |
|---:|---|---|
| 683 | `# Q2 old read kernel (headline values)` | Comment: the cross-check of question Q2 for the old read kernel starts. |
| 684 | `R42 = lambda name: facts_row("4.2", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)` | `R42`: a lambda that returns one row of `FACTS.md` section 4.2. The column `Row` of that row starts with the given name, and its table has the column `Min to max, GB/s`. |
| 685 | `C42 = lambda a, b: facts_row("4.2", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"].startswith(b), f"{a} / {b}")` | `C42`: a lambda that returns the comparison row of section 4.2 for a 7200 MT/s row and an 8000 MT/s range. The columns `7200 MT/s row` and `8000 MT/s range used` must start with the two given texts. |
| 686 | `xc_range("Q2 old read, part A", rA_old.lo, rA_old.hi, R42("part A, sessions 1 to 3")["Min to max, GB/s"])` | `xc_range` compares the computed range of the old read kernel in part A with the column `Min to max, GB/s` of its row. Each computed range is the lowest and the highest value of `val` in its group of records (class `Rg`, line 192). Lines 686 to 692 compare 7 ranges in this way. |
| 687 | `xc_range("Q2 old read, pool A-1 to A-3", rPA_old.lo, rPA_old.hi, R42("pool A-1 to A-3")["Min to max, GB/s"])` | `xc_range` compares the range of the pool A-1 to A-3 (old read kernel) with its row. |
| 688 | `xc_range("Q2 old read, part L", rL_old.lo, rL_old.hi, R42("part L (T72L1 to T72L3)")["Min to max, GB/s"])` | `xc_range` compares the `oldread` range of part L with its row. |
| 689 | `xc_range("Q2 old read, pool L-1 to L-4", rPL_old.lo, rPL_old.hi, R42("pool L-1 to L-4")["Min to max, GB/s"])` | `xc_range` compares the `oldread` range of the pool L-1 to L-4 with its row. |
| 690 | `xc_range("Q2 old read, part C", rC_old.lo, rC_old.hi, R42("part C, all oldread intervals")["Min to max, GB/s"])` | `xc_range` compares the range of all `oldread` intervals of part C with its row. |
| 691 | `xc_range("Q2 old read, F72d12", rF_old.lo, rF_old.hi, R42("F72d12")["Min to max, GB/s"])` | `xc_range` compares the `oldread` range of F72d12 with its row. |
| 692 | `xc_range("Q2 old read, control I", rI_old.lo, rI_old.hi, R42("control I")["Min to max, GB/s"])` | `xc_range` compares the `oldread` range of control I with its row. |
| 693 | `xc_val("Q2 old read, median of part L", rL_old.med, R42("part L (T72L1 to T72L3)")["Median, GB/s"])` | `xc_val` compares the median of part L with the column `Median, GB/s` of its row. |
| 694 | `xc_val("Q2 old read, median of pool L-1 to L-4", rPL_old.med, R42("pool L-1 to L-4")["Median, GB/s"])` | The same for the median of the pool L-1 to L-4. |
| 695 | `row = C42("part A, sessions 1 to 3", "pool A-1 to A-3")` | `row`: the comparison row of part A against the pool A-1 to A-3. This is a comparison with overlap. |
| 696 | `check(WORD_SAME in col(row, "Wording") and wording(rA_old, rPA_old) == WORD_SAME, f'Q2 old read, part A: wording "{WORD_SAME}" computed and in FACTS.md')` | The check needs two things. The column `Wording` of the `FACTS.md` row must hold `no difference seen`. `wording` (line 481) must return the same text for the two computed ranges. |
| 697 | `xc_val("Q2 old read, part A: size the test cannot exclude (est.)", width_pct(rPA_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)` | `xc_val` compares `width_pct` of the 8000 MT/s pool (line 476) with the column `Width of the 8000 MT/s range`, to 0.1 percent. This width is the size that the test cannot exclude (est.). The saved output of a build shows 1.2 % for part A [Ref5]. |
| 698 | `row = C42("part C, all oldread intervals", "pool L-1 to L-4 (position 0)")` | `row`: the comparison row of part C against the pool L-1 to L-4. This is the second comparison with overlap. |
| 699 | `check(WORD_SAME in col(row, "Wording") and wording(rC_old, rPL_old) == WORD_SAME, f'Q2 old read, part C: wording "{WORD_SAME}" computed and in FACTS.md')` | The same two conditions as in line 696, for part C. |
| 700 | `xc_val("Q2 old read, part C: size the test cannot exclude (est.)", width_pct(rPL_old), col(row, "Width of the 8000 MT/s range"), "0.1", "%", f1)` | The same comparison of the width, for the pool L-1 to L-4. The saved output of a build shows 1.0 % for part C [Ref5]. |
| 701 | `row = C42("part L", "pool L-1 to L-4")` | `row`: the comparison row of part L against the pool L-1 to L-4. This is the one comparison of the old read kernel in which the two ranges do not overlap. |
| 702 | `check(WORD_DIFF in col(row, "Wording") and wording(rL_old, rPL_old) == WORD_DIFF, f'Q2 old read, part L: wording "{WORD_DIFF}" computed and in FACTS.md')` | The wording must be the text for a difference (`WORD_DIFF`), both in the `FACTS.md` row and from `wording`. |
| 703 | `xc_val("Q2 old read, part L: distance of the nearest ends", L_OLD_NEAR, col(row, "Distance of the nearest ends"))` | `L_OLD_NEAR` (line 489) is compared with the column `Distance of the nearest ends`. The value is negative: part L is the lower range. The saved output of a build shows -1.24 GB/s [Ref5]. |
| 704 | `xc_text("Q2 old read, part L: distance of the medians", "4.9", L_OLD_MED, "GB/s")` | `xc_text` (line 633) tests that section 4.9 holds the difference of the two medians in GB/s. The saved output of a build shows 6.27 GB/s [Ref5]. |
| 705 | `xc_text("Q2 old read, part L: nearest ends in percent", "4.9", L_OLD_NEAR_PCT, "%", "0.1", f1)` | The same for the distance of the nearest ends in percent of the lower end of the 8000 MT/s range (line 491). The saved output of a build shows 0.3 % [Ref5]. |
| 706 | `xc_text("Q2 old read, part L: medians in percent", "4.9", L_OLD_MED_PCT, "%", "0.1", f1)` | The same for the difference of the medians in percent of the 8000 MT/s median (line 492). The saved output of a build shows 1.3 % [Ref5]. |
| 707 | `for nm, rg in (("F72d12", rF_old), ("control I", rI_old)):` | Goes through F72d12 and control I. |
| 708 | `    row = C42(nm, "pool L-1 to L-4")` | `row`: the comparison row of this run against the pool L-1 to L-4. |
| 709 | `    check(col(row, "Overlap") == "yes" and rg.overlaps(rPL_old), f"Q2 old read, {nm}: overlaps the 8000 MT/s pool, computed and in FACTS.md")` | The check passes when the column `Overlap` reads `yes` and the computed range overlaps the pool. |

### Cross-check of question Q2 with `FACTS.md`: load-only loop (lines 711 to 744)

| Line | Source | Explanation |
|---:|---|---|
| 711 | `# Q2 load-only loop (headline values)` | Comment: the cross-check of question Q2 for the load-only loop starts. |
| 712 | `R44 = lambda name: facts_row("4.4", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)` | `R44`: a lambda that does for section 4.4 what `R42` does for section 4.2. |
| 713 | `C44 = lambda a, b: facts_row("4.4", lambda r: r["7200 MT/s row"].startswith(a) and r["8000 MT/s range used"] == b, f"{a} / {b}")` | `C44`: a lambda that does for section 4.4 what `C42` does for section 4.2. It requires that the cell `8000 MT/s range used` is exactly the given text, not only its start. |
| 714 | `xc_range("Q2 load-only, part L asmread", rL_asm.lo, rL_asm.hi, R44("part L (T72L1 to T72L3)")["Min to max, GB/s"])` | `xc_range` compares the `asmread` range of part L with the column `Min to max, GB/s` of its row. |
| 715 | `xc_range("Q2 load-only, pool L-1 to L-4 asmread", rPL_asm.lo, rPL_asm.hi, R44("pool L-1 to L-4")["Min to max, GB/s"])` | The same for the `asmread` range of the pool L-1 to L-4. |
| 716 | `xc_range("Q2 load-only, F72d12 asmread", rF_asm.lo, rF_asm.hi, R44("F72d12")["Min to max, GB/s"])` | The same for the `asmread` range of F72d12. |
| 717 | `xc_range("Q2 load-only, control I asmread", rI_asm.lo, rI_asm.hi, R44("control I")["Min to max, GB/s"])` | The same for the `asmread` range of control I. |
| 718 | `row = C44("part L", "pool L-1 to L-4")` | `row`: the comparison row of part L against the pool L-1 to L-4. |
| 719 | `check(WORD_DIFF in col(row, "Wording") and wording(rL_asm, rPL_asm) == WORD_DIFF, f'Q2 load-only, part L: wording "{WORD_DIFF}" computed and in FACTS.md')` | The wording must be the text for a difference (`WORD_DIFF`), both in the `FACTS.md` row and from `wording`. |
| 720 | `xc_val("Q2 load-only, part L: distance of the nearest ends", DIST["nearest"][0], col(row, "Distance of the nearest ends"))` | The distance of the nearest ends, the first value of the entry `nearest` of `DIST` (line 504), is compared with the column of that name. The saved output of a build shows 12.48 GB/s for part L [Ref5]. |
| 721 | `xc_val("Q2 load-only, F72d12 above L-1 alone", rF_asm.nearest(rL1_asm), col(C44("F72d12", "L-1 alone"), "Distance of the nearest ends"))` | The distance by which F72d12 lies above row L-1 alone is compared with its row. The saved output of a build shows 1.73 GB/s [Ref5]. |
| 722 | `check(col(C44("F72d12", "pool L-1 to L-4"), "Overlap") == "yes", "Q2 load-only, F72d12: inside the 8000 MT/s pool range, computed and in FACTS.md")` | This check reads `FACTS.md` only: the column `Overlap` of F72d12 against the pool must read `yes`. Lines 495 to 496 asserted the computed side. |
| 723 | `xc_val("Q2 load-only, control I above the pool", rI_asm.nearest(rPL_asm), col(C44("control I", "pool L-1 to L-4"), "Distance of the nearest ends"))` | The distance by which control I lies above the pool is compared with its row. The saved output of a build shows 4.61 GB/s [Ref5]. |
| 724 | `for rnd in (1, 2):` | Goes through the rounds 1 and 2. The lines of the loop handle the new read kernel of part A (`bw_new read`), once per round, by rule V3. |
| 725 | `    row = facts_row("4.3", lambda r, rnd=rnd: r["Binary and kernel"] == "bw_new read" and r["Round"] == str(rnd) and "Wording by rule V3" in r, f"bw_new read round {rnd}")` | `row`: the row of section 4.3 for `bw_new read` and this round, from the table that has the column `Wording by rule V3`. |
| 726 | `    v = A_V3[rnd]` | `v`: the entry of `A_V3` for the round (line 509). |
| 727 | `    xc_range(f"Q2 part A, bw_new read, round {rnd}: 8000 MT/s range", v["r8"].lo, v["r8"].hi, row["8000 MT/s range of the round, GB/s"])` | The range of the 6 intervals of the rows A-1 and A-2 (`r8`) is compared with the column `8000 MT/s range of the round, GB/s`. |
| 728 | `    cell7 = [Decimal(x) for x in re.findall(r"(\d+\.\d+) \(\d+\)", row["7200 MT/s, session 1"])]` | `cell7`: the rates in the cell `7200 MT/s, session 1`. The pattern finds each text of the form `rate (pass count)`: a number with a decimal part, a space and a whole number in parentheses. The group holds the rate. |
| 729 | `    check(len(cell7) == 3 and near(min(cell7), q(v["r7"].lo), "0.01") and near(max(cell7), q(v["r7"].hi), "0.01"),` | The check passes when the cell holds three such texts and their lowest and highest rate equal the ends of the range of the 3 intervals of session 1 (`r7`), to 0.01 GB/s. |
| 730 | `          f"Q2 part A, bw_new read, round {rnd}: session 1 computed {v['r7'].txt()} GB/s, FACTS.md {min(cell7)} to {max(cell7)} GB/s")` | Continues the call of line 729: the text of the check, with both ranges. |
| 731 | `    check(row["Wording by rule V3"] == "outside (above)", f"Q2 part A, bw_new read, round {rnd}: wording outside (above), computed and in FACTS.md")` | The cell `Wording by rule V3` must read `outside (above)`. Line 514 asserted the computed side. |
| 732 | `    xc_val(f"Q2 part A, bw_new read, round {rnd}: distance of the nearest ends", v["near"], col(row, "Distance to the nearer end"))` | The distance of the nearest ends is compared with the first number of the column `Distance to the nearer end`. |
| 733 | `    pc = sorted(int(x) for x in re.findall(r"\((\d+)\)", row["8000 MT/s, A-1, same round"] + row["8000 MT/s, A-2, same round"]))` | `pc`: the pass counts in the two 8000 MT/s cells of the row, sorted. The pattern finds each whole number in parentheses. |
| 734 | `    check(pc == v["p8"], f"Q2 part A, bw_new read, round {rnd}: pass counts at 8000 MT/s {v['p8']}, FACTS.md {pc}")` | The check passes when these pass counts equal the list `p8` of the records (line 516). |
| 735 | `row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after oldread") and r["8000 MT/s range used"].startswith("pool L-1 to L-4 (after oldread)"), "part C asmread after oldread")` | `row`: the row of section 4.5 for part C, `asmread` directly after `oldread` (2 intervals), against the `asmread` range of the pool L-1 to L-4. |
| 736 | `xc_range("Q2 load-only, part C asmread after oldread", rC_asm_ao.lo, rC_asm_ao.hi, col(row, "Its range"))` | The computed range is compared with the column `Its range`. |
| 737 | `xc_val("Q2 load-only, part C asmread after oldread: distance", rC_asm_ao.nearest(rPL_asm), col(row, "Distance of the nearest ends"))` | The distance of the nearest ends is compared with the column of that name. |
| 738 | `check("Insufficient data: no 8000 MT/s run of kernel read with bwx12" in SEC["4.5"], "Q2 part C, kernel read: Insufficient data wording present in FACTS.md section 4.5")` | Tests that section 4.5 holds the text `Insufficient data: no 8000 MT/s run of kernel read with bwx12`. The check tests only that this text is present. |
| 739 | `xc_text("three visits of the 7200 MT/s boot: span", "4.6", VISIT_HI - VISIT_LO, "GB/s")` | The three visits of the part L line in the 7200 MT/s boot: F72d12, part L and control I. The `asmread` span `VISIT_HI - VISIT_LO` (line 501) must stand in section 4.6 with the unit GB/s. The span is the highest value of the three visits minus the lowest value. The saved output of a build shows 26.03 GB/s [Ref5]. |
| 740 | `xc_text_range("three visits of the 7200 MT/s boot: lowest to highest asmread", "4.9", VISIT_LO, VISIT_HI, "", "0.01", f2)` | Section 4.9 must hold the lowest and the highest value as a text of the form `X to Y`. |
| 741 | `for kind in ("nearest", "medians", "farthest"):` | Goes through the three kinds of distance in `DIST` (line 503). |
| 742 | `    xc_text(f"part L above the 8000 MT/s pool, {kind}", "4.6", DIST[kind][0], "GB/s")` | The distance by which part L lies above the 8000 MT/s pool must stand in section 4.6. |
| 743 | `    xc_text(f"part L above F72d12, {kind}", "4.6", DIST[kind][1], "GB/s")` | The distance by which part L lies above F72d12 must stand in section 4.6 too. |
| 744 | `xc_text("same line in the 7200 MT/s boot: span of oldread", "3.4", VISIT_OLD_HI - VISIT_OLD_LO, "GB/s")` | The same span as in line 739 for `oldread` (line 502) must stand in section 3.4. The saved output of a build shows 7.59 GB/s [Ref5]. |

### Cross-check: range widths of part A, rows of the runner bwx (lines 745 to 768)

| Line | Source | Explanation |
|---:|---|---|
| 745 | `# part A, old read: widths of the two ranges. Rows of runner bwx: ranges, distances and highest values (note under Table 2)` | Comment: two more blocks of cross-checks. First the widths of the two ranges of the old read kernel in part A. Then the rows of the runner bwx: ranges, distances and highest values, for the note under Table 2. |
| 746 | `g0 = len(CHECKS)` | `g0`: the length of `CHECKS` before the first block. |
| 747 | `xc_text("part A, old read: width of the 7200 MT/s range", "0", A_OLD_W7, "GB/s")` | `xc_text` tests that section 0 holds the width of the 7200 MT/s range (`A_OLD_W7`, line 527). |
| 748 | `xc_text("part A, old read: width of the 8000 MT/s range", "0", A_OLD_W8, "GB/s")` | The same for the width of the 8000 MT/s pool range (`A_OLD_W8`). |
| 749 | `check(f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range and {len(A_OLD_ABOVE)} lie above it" in SEC["0"],` | The check builds the text `N of its M intervals lie below that range and K lie above it` from the computed counts (lines 525 to 526). It passes when section 0 holds this text. |
| 750 | `      f"part A, old read: {len(A_OLD_BELOW)} of {rA_old.n} intervals below the 8000 MT/s range and {len(A_OLD_ABOVE)} above it, computed and in FACTS.md section 0")` | Continues the call of line 749: the text of the check. |
| 751 | `grouped("FACTS.md section 0, part A, old read kernel: widths of the two ranges (0.01 GB/s) and the intervals outside the 8000 MT/s range", g0)` | `grouped` joins the 3 comparisons into one line. |
| 752 | `g0 = len(CHECKS)` | `g0`: the length of `CHECKS` before the second block. |
| 753 | `X45 = lambda name: facts_row("4.5", lambda r: r["Row"].startswith(name) and "Min to max, GB/s" in r, name)["Min to max, GB/s"]` | `X45`: a lambda that returns the cell `Min to max, GB/s` of a row of section 4.5. The column `Row` of that row starts with the given name. |
| 754 | `xc_range("runner bwx, read at position 1", rX_read_ao.lo, rX_read_ao.hi, X45("pool B7a, B7b, C3a, C3b, position 1"))` | `xc_range` compares a range of the pool of the bwx datasets B7a, B7b, C3a and C3b with its row. This call handles `read` at position 1. |
| 755 | `xc_range("runner bwx, read at position 6", rX_read_aa.lo, rX_read_aa.hi, X45("pool B7a, B7b, C3a, C3b, position 6"))` | The same for `read` at position 6. |
| 756 | `xc_range("runner bwx, asmread at position 2", rX_asm_ar.lo, rX_asm_ar.hi, X45("pool B7a, B7b, C3a, C3b, position 2"))` | The same for `asmread` at position 2. |
| 757 | `xc_text("part C, read after oldread, above the bwx rows", "4.5", X_ABOVE[0], "GB/s")` | The first distance of `X_ABOVE` (line 545): by how much the part C group `read` after `oldread` lies above its bwx range. It is searched in the text of section 4.5. |
| 758 | `xc_text("part C, read after asmread, above the bwx rows", "4.5", X_ABOVE[1], "GB/s")` | The second distance, for `read` after `asmread`. It is searched in the text of section 4.5 too. |
| 759 | `row = facts_row("4.5", lambda r: r["7200 MT/s row"].startswith("part C, asmread after read") and r["8000 MT/s range used"].startswith("other binary bwx"),` | `row`: the row of section 4.5 for part C, `asmread` after `read`, against the rows of the other binary bwx. |
| 760 | `                "part C asmread after read against runner bwx")` | Continues the call of line 759: the name of the row for the stop message. |
| 761 | `xc_val("part C, asmread after read, above the bwx rows", X_ABOVE[2], col(row, "Distance of the nearest ends"))` | The third distance is compared with the table cell `Distance of the nearest ends` of that row. |
| 762 | `xc_text("runner bwx: highest read value of the rows of rule V2 point 4", "4.6", X_MAX_READ, "GB/s")` | The highest `read` value of `X_LOADS` (line 546) is searched in section 4.6. |
| 763 | `xc_text("runner bwx: highest asmread value of the rows of rule V2 point 4", "4.6", X_MAX_ASM, "GB/s")` | The same for the highest `asmread` value of `X_LOADS` (line 547). |
| 764 | `xc_text("runner bwx, reverse order: highest read value", "4.6", X_REV_MAX_READ, "GB/s")` | The same for the highest `read` value of the reverse-order processes (line 549). |
| 765 | `xc_text("runner bwx, reverse order: highest asmread value", "4.6", X_REV_MAX_ASM, "GB/s")` | The same for the highest `asmread` value of the reverse-order processes. |
| 766 | `check(f"({len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot" in SEC["4.6"], f"runner bwx: {len(X_LOADS)} intervals / {Rg(X_LOADS).np} processes / 1 boot, computed and in FACTS.md section 4.6")` | The text for n is searched in section 4.6: an opening parenthesis, the number of intervals of `X_LOADS`, the number of its processes and `1 boot`. The counts come from the records: 192 intervals of 24 processes (line 326). |
| 767 | `grouped("FACTS.md sections 4.5 and 4.6, rows of runner bwx: 3 ranges, 3 distances and 4 highest values (0.01 GB/s), and n", g0)` | `grouped` joins the 11 comparisons of lines 754 to 766 into one line. |

### Cross-check with the verdict records of `facts.json` (lines 769 to 810)

| Line | Source | Explanation |
|---:|---|---|
| 769 | `# the same values against the "verdicts" records of facts.json` | Comment: the same values are now compared with the verdict records of `facts.json`. |
| 770 | `V = FJ["verdicts"]` | `V`: the part `verdicts` of `facts.json`. The modules `facts_text.py` and `facts_text4.py` computed its values during a run of `build_facts.py`. |
| 773 | `def vrow(part, kernel, row7, scope8):` | Starts the function `vrow`. It returns one verdict record of the list `q2_rows`. |
| 774 | `    hit = [r for r in V["q2_rows"] if r["part"] == part and r["kernel"] == kernel and r["row_7200"] == row7 and r["scope_8000"] == scope8]` | `hit`: the entries of `q2_rows` with the given part, kernel, 7200 MT/s row (field `row_7200`) and 8000 MT/s scope (field `scope_8000`). |
| 775 | `    need(len(hit) == 1, f"facts.json verdicts: no single row {part} / {kernel} / {row7} / {scope8}")` | The script stops unless exactly one entry matches. |
| 776 | `    return hit[0]` | Returns that entry. |
| 779 | `def xv(label, r7, r8, vr, dist):` | Starts the function `xv`. It adds a check: two computed ranges and a distance against one verdict record `vr`. |
| 780 | `    ok = (near(r7.lo, vr["lo_7200"], "0.001") and near(r7.hi, vr["hi_7200"], "0.001") and near(r8.lo, vr["lo_8000"], "0.001")` | `ok`, first part: the lowest and the highest value of the 7200 MT/s range and the lowest value of the 8000 MT/s range must each differ from the field of the record by at most 0.001 GB/s. The computed values are not rounded before this comparison. `build_facts.py` wrote these fields of the record rounded to 0.001 GB/s. |
| 781 | `          and near(r8.hi, vr["hi_8000"], "0.001") and near(dist, vr["distance_GBps"], "0.001") and r7.overlaps(r8) == vr["overlap"]` | Continues line 780: the same test for the highest value of the 8000 MT/s range and for the distance `dist`. The computed overlap result must equal the field `overlap`. |
| 782 | `          and r7.n == vr["n_7200"] and r8.n == vr["n_8000"] and r7.np == vr["processes_7200"] and r8.np == vr["processes_8000"])` | Continues line 780: the number of intervals (`n`) and the number of processes (`np`) of both ranges must equal the fields of the record exactly. |
| 783 | `    check(ok, f"{label}: ranges, n, overlap and distance equal to the verdict record of facts.json")` | `check` adds one PASS or FAIL line. |
| 786 | `g0 = len(CHECKS)` | `g0`: the length of `CHECKS` before the comparisons with the verdict records. |
| 787 | `xv("old read, part A", rA_old, rPA_old, vrow("A", "bw_old read", "part A, sessions 1 to 3", "pool A-1 to A-3"), 0)` | Old read kernel: part A against the pool A-1 to A-3. The last argument is the computed distance of the nearest ends. It is written as 0 here: the two ranges overlap. Lines 787 to 798 hold eleven `xv` calls. The list `q2_rows` of this `facts.json` has 42 entries, and these lines compare 11 of them [Ref2]. |
| 788 | `xv("old read, part L", rL_old, rPL_old, vrow("L", "oldread", "part L", "pool L-1 to L-4"), L_OLD_NEAR)` | Old read kernel: part L against the pool L-1 to L-4, with the distance `L_OLD_NEAR`. |
| 789 | `xv("old read, part C", rC_old, rPL_old, vrow("C", "oldread", "part C, all oldread intervals", "pool L-1 to L-4 (position 0)"), 0)` | Old read kernel: part C against the pool L-1 to L-4. The distance is written as 0. |
| 790 | `xv("old read, F72d12", rF_old, rPL_old, vrow("L", "oldread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)` | Old read kernel: F72d12 against the pool L-1 to L-4. The distance is written as 0. |
| 791 | `xv("old read, control I", rI_old, rPL_old, vrow("L", "oldread", "control I (same boot, not pooled)", "pool L-1 to L-4"), 0)` | Old read kernel: control I against the pool L-1 to L-4. The distance is written as 0. |
| 792 | `xv("asmread, part L", rL_asm, rPL_asm, vrow("L", "asmread", "part L", "pool L-1 to L-4"), DIST["nearest"][0])` | `asmread`: part L against the pool L-1 to L-4, with the first value of the entry `nearest` of `DIST`. |
| 793 | `xv("asmread, F72d12", rF_asm, rPL_asm, vrow("L", "asmread", "F72d12 (same boot, not pooled)", "pool L-1 to L-4"), 0)` | `asmread`: F72d12 against the pool. The distance is written as 0. So it is 0 in the five calls whose ranges overlap. |
| 794 | `xv("asmread, control I", rI_asm, rPL_asm, vrow("L", "asmread", "control I (same boot, not pooled)", "pool L-1 to L-4"), rI_asm.nearest(rPL_asm))` | `asmread`: control I against the pool, with the computed distance of the nearest ends. |
| 795 | `xv("asmread after oldread, part C", rC_asm_ao, rPL_asm, vrow("C", "asmread", "part C, asmread after oldread", "pool L-1 to L-4 (after oldread)"), rC_asm_ao.nearest(rPL_asm))` | `asmread` of part C directly after `oldread`, against the pool, with the computed distance of the nearest ends. |
| 796 | `for rnd in (1, 2):` | Goes through the rounds 1 and 2. |
| 797 | `    xv(f"bw_new read, session 1, round {rnd}", A_V3[rnd]["r7"], A_V3[rnd]["r8"],` | `bw_new read`: session 1 against the rows A-1 and A-2 of the same round. |
| 798 | `       vrow("A", "bw_new read", f"session 1, round {rnd}", f"A-1 and A-2, round {rnd}"), A_V3[rnd]["near"])` | Continues the call of line 797: the verdict record of this round and the distance `near` of `A_V3`. |
| 799 | `for key_, grp in (("C_ao", "read after oldread"), ("C_aa", "read after asmread")):` | Question Q1, part C: goes through the two groups of the bwx12 kernel `read`. |
| 800 | `    vr = [r for r in V["q1_parts"] if r["part"] == "C" and r["group"] == grp]` | `vr`: the entries of `verdicts.q1_parts` with the part `C` and this group. |
| 801 | `    need(len(vr) == 1, f"facts.json verdicts: no single Q1 row {grp}")` | The script stops unless exactly one such entry exists. |
| 802 | `    check(near(min(Q1[key_]["drops"]), vr[0]["smallest_drop_pct"], "0.01") and near(max(Q1[key_]["drops"]), vr[0]["largest_drop_pct"], "0.01"),` | The lowest and the highest computed drop must differ from the fields `smallest_drop_pct` and `largest_drop_pct` by at most 0.01 (percent). The drops are not rounded before this comparison. The record holds both fields rounded to 0.01 percent. |
| 803 | `          f"Q1 part C, {grp}: drops equal to the verdict record of facts.json to 0.01 %")` | Continues the call of line 802: the text of the check. |
| 804 | `grouped("verdict records of facts.json (11 comparisons of Q2 with ranges, n, overlap and distance to 0.001 GB/s; 2 drop ranges of Q1 to 0.01 %)", g0)` | `grouped` joins the 13 comparisons of lines 787 to 803 into one line. |
| 805 | `sb = V["same_boot"]` | `sb`: the record `verdicts.same_boot` of `facts.json`. It holds values for the three visits of the 7200 MT/s boot. |
| 806 | `check(near(VISIT_HI - VISIT_LO, sb["spread_GBps"], "0.001")` | The check passes when seven computed values differ from this record by at most 0.001 GB/s each. The first is the `asmread` span `VISIT_HI - VISIT_LO`. |
| 807 | `      and all(near(DIST[k][0], sb["part_L_above_pool_8000_GBps"][j], "0.001") and near(DIST[k][1], sb["part_L_above_F72d12_GBps"][j], "0.001")` | Continues the call of line 806: the other six values are the distances of `DIST`, each above the 8000 MT/s pool and above F72d12. |
| 808 | `              for k, j in (("nearest", "nearest_ends"), ("medians", "medians"), ("farthest", "farthest_ends"))),` | Continues line 807: the loop pairs each kind of distance with its field name in the record: nearest ends, medians and farthest ends. |
| 809 | `      "three visits of the 7200 MT/s boot: span and the 6 distances equal to the same_boot record of facts.json")` | Continues the call of line 806: the text of the check. |

### Reference helpers: `addref`, `ref` and `number_refs` (lines 811 to 840)

| Line | Source | Explanation |
|---:|---|---|
| 811 | `# ------------------------------------------------------------------ raw-file checks for the machine state section` | Comment: a section title. The checks of raw files for the page section on the machine state start here. The reference helpers are defined first. |
| 812 | `REFS = []            # (key, path, text shown, note)` | `REFS`: the list of the reference entries of the page. It starts empty. The comment names four values per entry: key, path, text shown and note. The code stores three: the key, the path text and the note (line 818). |
| 815 | `def addref(key, path, note, lines=None):` | Starts the function `addref`. It adds one entry to the reference list of the page. The calls of `addref` stand in lines 1389 to 1474. |
| 816 | `    need(os.path.exists(path), f"reference {key}: path does not exist: {path}")` | The script stops when the path does not exist. |
| 817 | `    shown = path.replace(R + "/", "R/").replace(S + "/", "S/")` | `shown`: the path in its short form. The start `R/` stands for the results folder and `S/` for the scratch folder. |
| 818 | `    REFS.append((key, shown + (f" ({lines})" if lines else ""), note))` | Stores three values: the key, the short path and the note. When `lines` is given, this text is appended to the path in parentheses. |
| 821 | `def ref(*keys):` | Starts the function `ref`. It returns the HTML text that the page carries at a place that cites references. |
| 822 | `    """Reference marks. The numbers are given at the end, in the order of first use on the page (number_refs)."""` | Comment: the documentation text. The function makes reference marks. The numbers are given at the end, in the order of first use on the page, by `number_refs` (line 828). |
| 823 | `    for k in keys:` | Goes through the keys of the call. |
| 824 | `        need(sum(1 for r in REFS if r[0] == k) == 1, f"unknown reference key {k}")` | The script stops unless the key has exactly one entry in `REFS`. |
| 825 | `    return '<span class="ref">' + "".join(f"\x00{k}\x00" for k in keys) + "</span>"` | Returns an element `span` of the class `ref`. It holds each key between two characters with the code 0 (written `\x00`). The reference numbers are not known yet. |
| 828 | `def number_refs(page):` | Starts the function `number_refs`. It numbers the references in the order of their first use. It runs once, on the text of the whole page (line 2784). |
| 829 | `    order = []` | `order`: the list of the cited keys. It starts empty. |
| 830 | `    for k in re.findall("\x00(.+?)\x00", page):` | Finds every mark in the page: the shortest text between two characters with the code 0. The group holds the key. |
| 831 | `        if k not in order:` | Tests whether the key is new. |
| 832 | `            order.append(k)` | Adds a new key. So `order` lists the keys in the order of their first mark in the page. |
| 833 | `    uncited = [r[0] for r in REFS if r[0] not in order]` | `uncited`: the keys of `REFS` that no mark names. |
| 834 | `    num = {k: i + 1 for i, k in enumerate(order + uncited)}` | `num`: the number of each key, counted from 1. The cited keys come first. The keys that are not cited get the numbers after them. |
| 835 | `    by_key = {r[0]: r for r in REFS}` | `by_key`: a dictionary from a key to its entry of `REFS`. |
| 836 | `    items = "".join(f'<li id="ref{num[k]}">[Ref{num[k]}] <code>{esc(by_key[k][1])}</code>: {esc(by_key[k][2])}</li>' for k in order + uncited)` | `items`: one list item per reference. It holds the link target `refN`, the text `[RefN]`, the path as code and the note. `esc` makes the path and the note safe for HTML. |
| 837 | `    page = re.sub("\x00(.+?)\x00", lambda m: f'<a href="#ref{num[m.group(1)]}">[Ref{num[m.group(1)]}]</a>', page)` | Replaces every mark by a link with the text `[RefN]`. The link leads to the list item of that reference. |
| 838 | `    return page.replace("\x01REFLIST\x01", items), uncited` | Puts the items in the place of the text `\x01REFLIST\x01` in the page. Returns the page and `uncited`. Line 2792 adds a FAIL line when `uncited` is not empty. |

### The two run logs: `STATE_RE` and function `state_lines` (lines 841 to 861)

| Line | Source | Explanation |
|---:|---|---|
| 841 | `GOLOG = R + "/go-T72-20261117T221209Z.log"` | `GOLOG`: the saved run log of `go.sh`, a file of the results folder. |
| 842 | `GO2LOG = R + "/go2-T72-20261117T222335Z.log"` | `GO2LOG`: the saved run log of `go2.sh`. |
| 843 | `STATE_RE = re.compile(r"^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) \d+ users (\d+) marker (\S+) processes per user: (.*)$")` | `STATE_RE`: the compiled regular expression for a state line. Such a line starts with `==`. The 12 groups hold, in this order: the name of the line, the UTC time, the boot id, MemTotal in kB, the three load averages (1, 5 and 15 minutes), the number of runnable tasks, the number of all tasks, the number of logins (after the word `users`), the state of the marker file, and the list after `processes per user:`. One more number stands before the word `users`. It is the last field of `/proc/loadavg`. The pattern matches it and does not keep it. `state_lines` uses 8 of the 12 groups. |
| 844 | `SYSTEM_ACCOUNTS = {"messagebus", "polkitd", "syslog", "systemd-network", "systemd-resolve", "systemd-timesync"}` | `SYSTEM_ACCOUNTS`: the names of the 6 accounts that the script calls system accounts. |
| 847 | `def state_lines(path):` | Starts the function `state_lines`. It parses the state lines of a run log and returns one dictionary per line that matches `STATE_RE`. |
| 848 | `    out = []` | `out`: the list of the dictionaries. It starts empty. |
| 849 | `    for no, line in enumerate(lines_of(path), 1):` | Goes through the lines of the log. `no` is the line number, counted from 1. |
| 850 | `        m = STATE_RE.match(line)` | Applies `STATE_RE` to the line, from its start. |
| 851 | `        if m:` | Only a state line is used. |
| 852 | `            users = {}` | `users`: a dictionary from an account name to its number of processes. It starts empty. |
| 853 | `            for part in m.group(12).split(";"):` | Splits the list after `processes per user:` (group 12) at each `;`. An entry of that list is a count, a space and an account name. Each entry ends with `;`. |
| 854 | `                part = part.split()` | Splits the entry at the spaces. |
| 855 | `                if len(part) == 2:` | Uses only an entry with exactly two words. The empty text after the last `;` is dropped this way. |
| 856 | `                    users[part[1]] = int(part[0])` | Stores the count as a whole number under the account name. |
| 857 | `            out.append(dict(line=no, name=m.group(1), utc=m.group(2), boot=m.group(3), mem=int(m.group(4)),` | Adds one dictionary for the state line. Its first entries are the line number, the name of the line (for example `start` or `after T72A1`), the time, the boot id and MemTotal in kB. |
| 858 | `                            load1=Decimal(m.group(5)), logins=int(m.group(10)), marker=m.group(11), users=users))` | Continues line 857: the 1-minute load average as a `Decimal`, the number of logins, the state of the marker file, and `users`. |
| 859 | `    return out` | Returns the list. |

### Hard assertions on the two run logs (lines 862 to 889)

| Line | Source | Explanation |
|---:|---|---|
| 862 | `ST_GO, ST_GO2 = state_lines(GOLOG), state_lines(GO2LOG)` | `ST_GO`, `ST_GO2`: the state lines of the log of `go.sh` and of the log of `go2.sh`, from `state_lines` (line 847). Each `need` call stops the script when its fact does not hold. Every test from here to line 1136 is such a call. The one exception is the `check` call of line 1035. |
| 863 | `need(len(ST_GO) == 12 and len(ST_GO2) == 6, "run logs: expected 12 and 6 state lines")` | The script stops unless the log of `go.sh` holds 12 state lines and the log of `go2.sh` holds 6. |
| 864 | `ST_ALL = ST_GO + ST_GO2` | `ST_ALL`: the 18 state lines of both logs. |
| 865 | `need(all(s["boot"] == RERUN["boot_id"] for s in ST_ALL), "run logs: a state line holds another boot id")` | The script stops unless all 18 lines hold the boot id of `meta.rerun` in `facts.json`. |
| 866 | `need(all(s["mem"] == RERUN["memtotal_kB"] for s in ST_ALL), "run logs: a state line holds another MemTotal")` | The script stops unless all 18 lines hold the MemTotal value of `meta.rerun`. |
| 867 | `need(all(s["logins"] == 0 and s["marker"] == "absent" for s in ST_ALL), "run logs: a login or the marker file")` | The script stops unless all 18 lines show 0 logins and the marker state `absent`. |
| 868 | `ACCOUNTS = set().union(*[set(s["users"]) for s in ST_ALL])` | `ACCOUNTS`: every account name that owns a process in at least one state line. |
| 869 | `need(ACCOUNTS == {"jhan", "root"} \| SYSTEM_ACCOUNTS, f"run logs: unexpected account owns a process: {sorted(ACCOUNTS)}")` | The script stops unless these are exactly `jhan`, `root` and the 6 system accounts. So only these accounts own processes. |
| 870 | `need(all(s["users"][a] == 1 for s in ST_ALL for a in SYSTEM_ACCOUNTS), "run logs: a system account owns more than 1 process")` | The script stops unless each system account owns exactly 1 process in every state line. |
| 871 | `JHAN_PROCS = sorted({s["users"]["jhan"] for s in ST_ALL})` | `JHAN_PROCS`: the different process counts of `jhan` in the state lines. |
| 872 | `need(len(JHAN_PROCS) == 1, "run logs: the process count of jhan changes")` | The script stops unless the process count of `jhan` is the same in all 18 lines. The process count of `root` is not tested. By the facts sheet it is 985 to 1014 in these lines [Ref1]. |
| 873 | `gl, g2l = lines_of(GOLOG), lines_of(GO2LOG)` | `gl`, `g2l`: all lines of the two run logs. |
| 874 | `GO_DONE = sum(1 for l in gl if l.startswith("done "))` | `GO_DONE`: the number of lines of the `go.sh` log that start with `done `. |
| 875 | `need(GO_DONE == 10 and gl[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in gl), "go.sh log: not 10 steps, or not ALLDONE")` | The script stops unless the `go.sh` log holds 10 such lines (one per step of the rerun), its last line is `ALLDONE` and no line starts with `FAILED`. |
| 876 | `need(sum(1 for l in g2l if l.startswith("done ")) == 2 and g2l[-1] == "ALLDONE" and not any(l.startswith("FAILED") for l in g2l), "go2.sh log")` | The same for the `go2.sh` log, with 2 lines that start with `done `. The other two conditions are the same. |
| 877 | `need(ST_GO[0]["utc"] == RERUN["go_start"] and ST_GO[-1]["utc"] == RERUN["go_end"], "go.sh log: start or end time differs from facts.json")` | The script stops unless the times of the first and of the last state line of the `go.sh` log equal the start time and the end time that `meta.rerun` holds for `go.sh`. |
| 878 | `need(ST_GO2[0]["utc"] == RERUN["go2_start"] and ST_GO2[-1]["utc"] == RERUN["go2_end"], "go2.sh log: start or end time differs from facts.json")` | The same for the `go2.sh` log and the two times that `meta.rerun` holds for `go2.sh`. |
| 879 | `LAUNCH = {l["tag"]: l for l in META["launches"]}` | `LAUNCH`: a dictionary from a folder tag to its entry of `meta.launches`. |
| 880 | `STEPS = ["T72A1", "T72L1", "T72C1", "T72A2", "T72L2", "T72C2", "T72A3", "T72L3", "T72C3", "T72C4", "T72I1", "T72I2"]` | `STEPS`: the folder tags of the 12 steps in run order: the 10 steps of the rerun and the 2 processes of control I. |
| 881 | `need([l["tag"] for l in META["launches"]] == STEPS, "meta.launches: unexpected list of steps")` | The script stops unless `meta.launches` names these 12 steps in this order. |
| 882 | `BWX_FOLDERS = sorted({r["folder"] for r in L_OLD + C_OLD + I_OLD})` | `BWX_FOLDERS`: the result folders of the `oldread` records of part L, part C and control I, sorted. |
| 883 | `need(len(BWX_FOLDERS) == 9, "expected 9 bwx12 folders of the rerun and the control")` | The script stops unless these are 9 folders. |
| 884 | `for fo in BWX_FOLDERS:` | Goes through the 9 folders. |
| 885 | `    ll = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")` | `ll`: the lines of the file `launches.txt` of the folder. The short form `R/` at the start of the folder name is replaced by the full path of the results folder. |
| 886 | `    need(sum(1 for l in ll if l.startswith("rc ")) == 1 and sum(1 for l in ll if l.startswith("rc 0 ")) == 1, f"{fo}: no single 'rc 0' line")` | The script stops unless the file holds exactly one line that starts with `rc `, and this line starts with `rc 0 `. So each folder holds one process, and its exit status is 0. |
| 887 | `check(True, f"run logs: {len(ST_ALL)} state lines hold boot id {RERUN['boot_id']} and MemTotal {RERUN['memtotal_kB']} kB, 0 logins; "` | `check(True, ...)` adds a summary line that is always PASS. The script reaches this line only when every `need` call above it held. The text gives the number of state lines, the boot id, MemTotal and the 0 logins. Each later block of raw-file checks up to line 1138 ends with such a line too. |
| 888 | `            f"accounts with processes: jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts; go.sh log: {GO_DONE} 'done' lines and ALLDONE; 9 bwx12 folders with one 'rc 0' line")` | Continues the text of line 887: the accounts with processes, the number of `done` lines of the `go.sh` log with `ALLDONE`, and the 9 bwx12 folders with one `rc 0` line. |

### The boot record `try6.txt`, and why F72d12 belongs to the 7200 MT/s boot (lines 890 to 919)

| Line | Source | Explanation |
|---:|---|---|
| 890 | `# the boot record of 12 modules at 7200 MT/s` | Comment: the next lines check the record of the boot with 12 modules at 7200 MT/s. |
| 891 | `TRY6 = R + "/dimm7200-20261117/try6.txt"` | `TRY6`: the path of `try6.txt`, the record of the 7200 MT/s boot. |
| 892 | `t6 = lines_of(TRY6)` | `t6`: the lines of the file. `t6[0]` is its first line. |
| 893 | `need(t6[1].strip() == RERUN["boot_id"], "try6.txt: line 2 is not the boot id of the rerun")` | The script stops unless the second line of the file is the boot id of the rerun. |
| 894 | `need(re.match(r"^MemTotal:\s+%d kB$" % RERUN["memtotal_kB"], t6[3]), "try6.txt: line 4 holds another MemTotal")` | The script stops unless the fourth line is the MemTotal line with the value of the rerun. The pattern is `MemTotal:`, spaces, the number of `meta.rerun` and ` kB`. |
| 895 | `m_ = re.match(r"^\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s$", t6[6])` | Applies a pattern to the seventh line: a count, the text `Configured Memory Speed:` and a speed in MT/s. Group 1 holds the count and group 2 holds the speed. |
| 896 | `need(m_ and int(m_.group(1)) == 12 and int(m_.group(2)) == RERUN["speed_MTps"] == 7200, "try6.txt: line 7 is not 12 x 7200 MT/s")` | The script stops unless the count is 12 and the speed is 7200, and `meta.rerun` gives 7200 MT/s too. |
| 897 | `need(t6[4].strip().endswith("ghes_edac: This system has 12 DIMM sockets."), "try6.txt: line 5 is not the kernel line with 12 modules")` | The script stops unless the fifth line ends with the Linux kernel message `ghes_edac: This system has 12 DIMM sockets.`. |
| 898 | `m_ = re.match(r"^modules=(\d+)$", t6[5].strip())` | Applies the pattern `modules=N` to the sixth line. The group holds the number N. |
| 899 | `need(m_, "try6.txt: line 6 is not a line 'modules=N'")` | The script stops unless the sixth line has this form. |
| 900 | `TRY6_MODLINE = int(m_.group(1))                            # not the module count: see the module list below` | `TRY6_MODLINE`: the number N of the sixth line. By the comment it is not the module count. Line 1170 compares it with the module list. In the saved output of a build it is 24 [Ref5]. |
| 901 | `TRY6_UTC = t6[0].strip()` | `TRY6_UTC`: the first line of the file, a time stamp. |
| 902 | `need(re.match(r"^2026-11-17T\d\d:\d\d:\d\dZ$", TRY6_UTC), "try6.txt: line 1 is not a time")` | The script stops unless this line is a time of 2026-11-17, in the form `2026-11-17THH:MM:SSZ`. The script does not read the third and the eighth line of the file. In the file `try6.txt` of the folder `dimm7200-20261117` the third line has the form of the output of the tool `uptime`, and the eighth line holds the text `hwerr=0`. In the saved output of a build the time of the first line is 20:02:21 [Ref5]. That is before the rerun, which started at 22:12:09 [Ref1]. |
| 903 | `# why F72d12 belongs to this boot` | Comment: the next lines show why F72d12 belongs to this boot. |
| 904 | `BOOTS = R + "/dimm7200-20261117/boots.txt"` | `BOOTS`: the path of `boots.txt`, the saved boot list of the journal. |
| 905 | `bl = [l.split() for l in lines_of(BOOTS) if l.strip()]` | `bl`: the rows of the file that are not empty, each split at the spaces. A row holds a boot number, a boot id without hyphens, and the first and the last time of the boot. |
| 906 | `need(bl[-1][0] == "0" and bl[-1][1] == RERUN["boot_id"].replace("-", ""), "boots.txt: row 0 is not the boot of the rerun")` | The script stops unless the last row has the number 0 and the boot id of the rerun. The boot id of `meta.rerun` is compared without its hyphens. |
| 907 | `BOOT_FIRST, BOOT_LAST = bl[-1][4], bl[-1][8]` | `BOOT_FIRST`, `BOOT_LAST`: the two times of day of this row, its fifth and its ninth field. |
| 908 | `need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(BOOTS))) == BOOT_LAST, "boots.txt: its file time is not the end time of row 0")` | The script stops unless the file time of `boots.txt` (the time of its last change), written as a UTC time of day, equals `BOOT_LAST`. So `BOOT_LAST` is the time at which the list was saved. The boot continued after it: the state lines of the rerun hold the same boot id (line 865). |
| 909 | `FL = R + "/w120-w120-F72d12-20261117T200231Z/launches.txt"` | `FL`: the path of `launches.txt` in the result folder of F72d12. |
| 910 | `fl = lines_of(FL)` | `fl`: the lines of that file. |
| 911 | `m1, m2 = re.match(r"^launch a6456 utc (\S+) load (\S+) ", fl[0]), re.match(r"^rc 0 a6456 utc (\S+)$", fl[1])` | Applies two patterns. The first line of the file must be the `launch` line of the process `a6456`: group 1 holds the launch time and group 2 holds the 1-minute load average. The second line must be the `rc 0` line of that process: its group holds the end time. |
| 912 | `need(m1 and m2, "F72d12 launches.txt: launch or rc line not found")` | The script stops unless both lines match. |
| 913 | `F_LAUNCH, F_END = m1.group(1), m2.group(1)` | `F_LAUNCH`, `F_END`: the launch time and the end time of the F72d12 process. |
| 914 | `need(F_OLD[0]["launch_utc"] == f"2026-11-17T{F_LAUNCH}Z" and D(m1.group(2)) == D(F_OLD[0]["load1_at_launch"]), "F72d12: launch differs from facts.json")` | The script stops unless the launch time and the load of that line equal the fields `launch_utc` and `load1_at_launch` of the first F72d12 record. |
| 915 | `need(TRY6_UTC[11:19] < F_LAUNCH and BOOT_FIRST <= F_LAUNCH < F_END <= BOOT_LAST and BOOT_LAST < ST_GO[0]["utc"][11:19],` | The script stops unless three things hold. The time in the first line of `try6.txt` is before the launch. The launch and the end lie from `BOOT_FIRST` to `BOOT_LAST`. `BOOT_LAST` is before the first state line of `go.sh`. These times are compared as texts `HH:MM:SS`. The dates in the rows of `boots.txt` are not compared. |
| 916 | `     "F72d12: the process does not lie inside the recorded time of boot 3bfc57a1")` | Continues the call of line 915: the stop message. It names the boot by the fixed text `3bfc57a1`, the first 8 characters of its boot id. |
| 917 | `check(True, f"try6.txt ({TRY6_UTC}): boot id of the rerun, MemTotal {RERUN['memtotal_kB']} kB, 12 x 7200 MT/s; boots.txt row 0 = this boot, "` | Adds the summary line of this block, always PASS. The text gives the time of `try6.txt`, MemTotal and the row of `boots.txt`. The saved output of a build shows the process from 20:02:36 to 20:03:37, inside 20:02:21 to 20:06:19 [Ref5]. |
| 918 | `            f"{BOOT_FIRST} to {BOOT_LAST}; F72d12 ran {F_LAUNCH} to {F_END} inside it")` | Continues the text of line 917: the two times of the boot row, and the launch and the end of F72d12. |

### Hardware error records and the Linux kernel log of the 8000 MT/s boot (lines 920 to 943)

| Line | Source | Explanation |
|---:|---|---|
| 920 | `# corrected hardware error records in the journal of the 8000 MT/s boot (defect partL-r3-partL-1, checked here)` | Comment: the next lines read the corrected hardware error records in the journal of the 8000 MT/s boot. The comment names a review finding by its identifier, `partL-r3-partL-1`, and says that it is checked here. The file `review-w2.json` in `S` holds this finding. |
| 921 | `JOURNAL = R + "/dimm-check-20261117/h-5.txt"` | `JOURNAL`: the path of `h-5.txt`. It holds saved journal lines of the 8000 MT/s boot. |
| 922 | `HW = []` | `HW`: the list of the hardware error records. It starts empty. |
| 923 | `for no, line in enumerate(lines_of(JOURNAL), 1):` | Goes through the lines of the journal file. `no` is the line number, counted from 1. |
| 924 | `    m_ = re.match(r"^(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$", line)` | The pattern matches a journal line of the Linux kernel that carries the tag `[Hardware Error]`. Group 1 holds the time stamp in front of `+00:00`. Group 2 holds the number in braces before the tag. Group 3 holds the message after the tag. |
| 925 | `    if not m_:` | Tests whether the line does not match. |
| 926 | `        continue` | Such a line is skipped. |
| 927 | `    if m_.group(3).startswith("Hardware error from APEI"):` | A message that starts with `Hardware error from APEI` opens a new record. |
| 928 | `        HW.append(dict(line=no, ts=m_.group(1), sev=None))` | The new record gets the line number and the time stamp. Its severity is not yet set. |
| 929 | `    elif m_.group(3).startswith("event severity:") and HW:` | A message that starts with `event severity:`, when `HW` holds a record. |
| 930 | `        HW[-1]["sev"] = m_.group(3).split(":", 1)[1].strip()` | It sets the severity of the newest record: the text after the colon. The other lines of a record are skipped. |
| 931 | `need(len(HW) > 0 and {h["sev"] for h in HW} == {"corrected"}, "journal: no records, or a severity other than 'corrected'")` | The script stops unless `HW` holds at least one record and every severity is `corrected`. The script reads no hardware error record of the 7200 MT/s boot. For the rerun the page says `Insufficient data` (line 2474). Lines 957 to 1032 count the records inside the time windows of the rows L-1 to L-4 and A-1 to A-3 only. No line counts them for the rows of the older runner bwx (the records of `OTHER`, line 333). The page says so (line 2562). |
| 932 | `# the saved kernel log of the same boot: its first and last line, the module count line, the same number of records` | Comment: the saved Linux kernel log of the same boot. The next lines check its first and its last line, the line with the module count, and that it holds the same number of records. |
| 933 | `KLOG = R + "/dimm-check-20261117/k-5.txt"` | `KLOG`: the path of `k-5.txt`, the saved Linux kernel log of the 8000 MT/s boot. |
| 934 | `kl = lines_of(KLOG)` | `kl`: the lines of that file. |
| 935 | `mk0, mk1 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[0]), re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", kl[-1])` | Applies one pattern to the first and to the last line of the log: `Nov`, a day of two digits and a time. Group 1 holds the day and group 2 holds the time. |
| 936 | `need(mk0 and mk1, "kernel log of the 8000 MT/s boot: first or last line has no time")` | The script stops unless both lines match. |
| 937 | `BOOT8_FROM, BOOT8_TO = f"2026-11-{mk0.group(1)}T{mk0.group(2)}Z", f"2026-11-{mk1.group(1)}T{mk1.group(2)}Z"` | `BOOT8_FROM`, `BOOT8_TO`: the times of the first and of the last line as time stamps. The year 2026 and the month 11 are fixed text of the script. |
| 938 | `need(sum(1 for l in kl if "ghes_edac: This system has 12 DIMM sockets" in l) == 1, "kernel log of the 8000 MT/s boot: module count line")` | The script stops unless the log holds exactly one line with `ghes_edac: This system has 12 DIMM sockets`. |
| 939 | `need(sum(1 for l in kl if "Hardware error from APEI" in l) == len(HW), "kernel log and journal of the 8000 MT/s boot: record counts differ")` | The script stops unless the log holds as many lines with `Hardware error from APEI` as `HW` has records. |
| 940 | `need(lines_of(JOURNAL)[0].startswith(BOOT8_FROM[:19]), "journal and kernel log of the 8000 MT/s boot: first line times differ")` | The script stops unless the first journal line starts with the time `BOOT8_FROM`. The last character `Z` of the time stamp is left out of the comparison. |
| 941 | `need(all(BOOT8_FROM < r["launch_utc"] < BOOT8_TO for r in EIGHT + OTHER), "an 8000 MT/s row was not launched inside the saved kernel log of its boot")` | The script stops unless every record of `EIGHT` and of `OTHER` (the used 8000 MT/s records, line 310 and line 333) has a launch time after `BOOT8_FROM` and before `BOOT8_TO`. The time stamps are compared as texts. |

### Functions `launch_window` and `hw_in`. Records during the rows L-1 to L-4 (lines 944 to 971)

| Line | Source | Explanation |
|---:|---|---|
| 944 | `def launch_window(folder, tag):` | Starts the function `launch_window`. It reads the file `launches.txt` of a result folder and returns the launch time and the end time of the process with the given tag. |
| 945 | `    ll = lines_of(R + "/" + folder + "/launches.txt")` | `ll`: the lines of `launches.txt` in that folder. |
| 946 | `    a = [re.match(rf"^launch {tag} utc (\S+) ", l) for l in ll]` | `a`: for each line, the result of the pattern `launch`, the tag, `utc` and a time. The group holds the launch time. |
| 947 | `    b = [re.match(rf"^rc 0 {tag} utc (\S+)$", l) for l in ll]` | `b`: the same for the pattern `rc 0`, the tag, `utc` and a time at the end of the line. The group holds the end time. |
| 948 | `    a, b = [x for x in a if x], [x for x in b if x]` | Keeps only the lines that matched. |
| 949 | `    need(len(a) == 1 and len(b) == 1, f"{folder}: launch window of {tag} not found")` | The script stops unless the file holds exactly one `launch` line and one `rc 0` line for the tag. |
| 950 | `    return a[0].group(1), b[0].group(1)` | Returns the two times. The end time is the time of the line `rc 0`. |
| 953 | `def hw_in(day, t0, t1):` | Starts the function `hw_in`. It returns the records of `HW` of one day whose time of day lies from `t0` to `t1`. |
| 954 | `    return [h for h in HW if h["ts"][:10] == day and t0 <= h["ts"][11:19] <= t1]` | A record counts when the first 10 characters of its time stamp are the day, and its time of day is not before `t0` and not after `t1`. Both ends count as inside. |
| 957 | `HW_ROWS = {}` | `HW_ROWS`: a dictionary with one entry per process of the rows L-1 to L-4. It starts empty. |
| 958 | `for d in LPOOL:` | Goes through the rows L-1 to L-4. |
| 959 | `    for pk in sorted({r["proc_key"] for r in B_L_ASM[d]}):` | Goes through the processes of the row. The loop takes them from the `asmread` records (`B_L_ASM`, line 292). |
| 960 | `        r0 = [r for r in B_L_ASM[d] if r["proc_key"] == pk][0]` | `r0`: the first record of the process. |
| 961 | `        folder, tag = r0["folder"].replace("R/", "", 1), r0["tag"]` | `folder`: the result folder of the record without the start `R/`. `tag`: the name of the process. |
| 962 | `        t0, t1 = launch_window(folder, tag)` | `launch_window` gives the launch time `t0` and the end time `t1` of the process. |
| 963 | `        need(r0["launch_utc"][11:19] == t0, f"{d} {tag}: launch time differs from facts.json")` | The script stops unless the launch time equals the time of day in the field `launch_utc` of the record. |
| 964 | `        HW_ROWS[(d, tag)] = dict(t0=t0, t1=t1, day=r0["launch_utc"][:10], recs=hw_in(r0["launch_utc"][:10], t0, t1))` | Stores, per row and tag, the two times, the day and the hardware error records inside this time window. |
| 965 | `HW_L1 = len(HW_ROWS[("L-1", "a6456")]["recs"])` | `HW_L1`: the number of records for L-1. |
| 966 | `HW_L2 = [len(HW_ROWS[("L-2", t)]["recs"]) for t in ("p1nop", "p2add")]` | `HW_L2`: the numbers of records for the two processes of L-2, `p1nop` and `p2add`. |
| 967 | `HW_L34 = sum(len(v["recs"]) for (d, _), v in HW_ROWS.items() if d in ("L-3", "L-4"))` | `HW_L34`: the total for L-3 and L-4. |
| 968 | `need(HW_L1 > 0 and min(HW_L2) > 0 and HW_L34 == 0, "journal: the record counts of rows L-1 to L-4 are not as the defect states")` | The script stops unless L-1 has at least 1 record, each L-2 process has at least 1, and L-3 and L-4 have 0. The saved output of a build shows 2 records for L-1, 5 and 4 for L-2, and 0 for L-3 and L-4 [Ref5]. |
| 969 | `# the part A rows of the same boot (A-1, A-2, A-3): records between the launches that the csv files hold` | Comment: the next lines handle the part A rows of the same boot (A-1, A-2, A-3). They count the records between the launches that the csv files hold. |

### Records during the rows A-1 to A-3: functions `a_headers` and `secs`, the checks (lines 972 to 1015)

| Line | Source | Explanation |
|---:|---|---|
| 972 | `def a_headers(rec):` | Starts the function `a_headers`, a helper for the rows A-1 to A-3, which ran in the 8000 MT/s boot too. It returns the process header lines of the csv file that a part A record names. |
| 973 | `    """(line number, launch time, text) of every process header line of the csv file of a part A record."""` | Comment: the documentation text. The result holds the line number, the launch time and the text of every process header line of the csv file of a part A record. |
| 974 | `    out = []` | `out`: the list of the header lines. It starts empty. |
| 975 | `    for no, l in enumerate(file_lines(rec), 1):` | Goes through the lines of the csv file that the record names. `no` is the line number, counted from 1. |
| 976 | `        if l.startswith("-- "):` | A process header line starts with `-- `. |
| 977 | `            m_ = re.search(r" utc (\d\d:\d\d:\d\d)\b", l)` | Looks for the launch time: the word `utc` and a time `HH:MM:SS`. The group holds the time. |
| 978 | `            need(m_, f"{rec['folder']}/{rec['file']} line {no}: header without a launch time")` | The script stops when a header line has no launch time. |
| 979 | `            out.append((no, m_.group(1), l))` | Adds the line number, the launch time and the text of the line. |
| 980 | `    return out` | Returns the list. |
| 983 | `def secs(hms):` | Starts the function `secs`. It converts a time `HH:MM:SS` to seconds, counted from midnight. |
| 984 | `    h, m, s_ = (int(x) for x in hms.split(":"))` | Splits the text at the colons into hours, minutes and seconds, each as a whole number. |
| 985 | `    return h * 3600 + m * 60 + s_` | Returns the hours times 3600 plus the minutes times 60 plus the seconds. |
| 988 | `A_DAY = "2026-11-13"` | `A_DAY`: the day of the rows A-1 to A-3. |
| 989 | `need({r["launch_utc"][:10] for d in APOOL for r in B_A_OLD[d]} == {A_DAY}, "rows A-1 to A-3 are not all of 2026-11-13")` | The script stops unless all `bw_old read` records of these rows have a launch time of 2026-11-13. |
| 990 | `HA1, HA2, HA3 = a_headers(B_A_OLD["A-1"][0]), a_headers(B_A_OLD["A-2"][0]), a_headers(B_A_OLD["A-3"][0])` | `HA1`, `HA2`, `HA3`: the header lists of the three csv files. Each call of `a_headers` takes the first `bw_old read` record of its row. |
| 991 | `A1_FIRST, A1_LAST, A2_FIRST, A2_LAST = HA1[0][1], HA1[-1][1], HA2[0][1], HA2[-1][1]` | The time window of A-1 and of A-2 runs from the first launch to the last launch in the file. `A1_FIRST`, `A1_LAST`, `A2_FIRST` and `A2_LAST` hold these four times. |
| 992 | `a3_used = sorted({r["_fproc"] for r in B_A_OLD["A-3"]})          # numbers of the processes used, inside the file` | `a3_used`: the numbers, inside the file, of the A-3 processes that the page uses. `_fproc` (line 349) gives the place of a process in the file. |
| 993 | `need(len(a3_used) == 3 and a3_used[-1] < len(HA3), "A-3: the 3 processes used, and a later process in the file")` | The csv file of A-3 holds more processes than the 3 that the page uses. The script stops unless the records name exactly 3 processes and the file holds a later process. |
| 994 | `A3_FIRST, A3_END = HA3[a3_used[0] - 1][1], HA3[a3_used[-1]][1]      # launch of the first one, launch of the process after the last one` | The window of A-3 runs from the launch of the first process used (`A3_FIRST`) to the launch of the process after the last one used (`A3_END`). |
| 995 | `need(A1_FIRST <= A1_LAST < A2_FIRST <= A2_LAST < A3_FIRST < A3_END, "rows A-1, A-2, A-3: order of the launch times")` | The script stops unless the six times are in order. So the three windows do not overlap. |
| 996 | `HW_A = hw_in(A_DAY, A1_FIRST, A3_END)` | `HW_A`: the records from the first launch of A-1 to the end of the A-3 window. |
| 997 | `HW_A2 = hw_in(A_DAY, A2_FIRST, A2_LAST)` | `HW_A2`: the records inside the window of A-2. |
| 998 | `need(len(HW_A) == len(HW_A2) == 4 and not hw_in(A_DAY, A1_FIRST, A1_LAST) and not hw_in(A_DAY, A3_FIRST, A3_END),` | The script stops unless the journal holds 4 records in `HW_A`, all 4 lie inside the window of A-2, and none lies inside the windows of A-1 and A-3. Records before the first launch of A-1 and after the end of the A-3 window are not counted in these lines. The file `h-5.txt` of the folder `dimm-check-20261117` holds 42 such records of 2026-11-13: 4 before (the last at 18:16:53, 28 s before that launch) and 38 after (the first at 20:59:34). |
| 999 | `     "journal: the records of 2026-11-13 are not 4 records inside row A-2 and 0 inside A-1 and A-3")` | Continues the call of line 998: the stop message. |
| 1000 | `# the last process of A-1 and of A-2 has no later header in its file: no record follows within 60 s of its launch` | Comment: the last process of A-1 and of A-2 has no later header line in its file. So no launch of a next process marks its end. In place of an end time, the next lines require that no record follows within 60 s of its launch. |
| 1001 | `for last in (A1_LAST, A2_LAST):` | Goes through the last launch of A-1 and the last launch of A-2. |
| 1002 | `    need(not [h for h in HW if h["ts"][:10] == A_DAY and 0 < secs(h["ts"][11:19]) - secs(last) <= 60], "journal: a record within 60 s after the last launch of A-1 or A-2")` | The script stops when a record of that day has a time from 1 s to 60 s after that launch. |
| 1003 | `HW_A2_T = sorted({h["ts"][11:19] for h in HW_A2})` | `HW_A2_T`: the different times of day of the 4 records in A-2, sorted. |
| 1004 | `need(len(HW_A2_T) == 2 and all(sum(1 for h in HW_A2 if h["ts"][11:19] == t) == 2 for t in HW_A2_T), "journal: row A-2 does not hold 2 + 2 records at two times")` | The script stops unless these are 2 times with 2 records each. |
| 1005 | `a2_new_r1 = [r for r in B_A_NEW["A-2"] if r["round"] == 1]` | `a2_new_r1`: the `bw_new read` records of round 1 in row A-2. |
| 1006 | `need(len(a2_new_r1) == 3 and a2_new_r1[0]["launch_utc"][11:19] == HW_A2_T[0] == HA2[a2_new_r1[0]["_fproc"] - 1][1],` | The script stops unless these are 3 records and the first time of `HW_A2_T` is the launch second of that process. The record field `launch_utc` and the header line of that process must both give this second. |
| 1007 | `     "journal: the first two records of row A-2 are not in the launch second of bw_new read, round 1")` | Continues the call of line 1006: the stop message. |
| 1008 | `a2_other = [h for i, h in enumerate(HA2) if h[1] <= HW_A2_T[1] and (i + 1 == len(HA2) or HW_A2_T[1] < HA2[i + 1][1])]` | `a2_other`: the process of the file in whose time the second pair of records falls. It is the last process of the file that was launched at or before the second time: the next header line, when one exists, has a later launch time. |
| 1009 | `need(len(a2_other) == 1, "journal: no single process of row A-2 for the second pair of records")` | The script stops unless exactly one such process exists. |
| 1010 | `m_ = re.search(r" binary (\S+) .* --kernel (\S+) ", a2_other[0][2])` | Reads the binary and the kernel from its header line: the word after `binary` (group 1) and the word after `--kernel` (group 2). |
| 1011 | `need(m_ and m_.group(2) not in ("read", "all"), "journal: the second pair of records of row A-2 falls into a read process")` | The script stops when the kernel is `read` or `all`. Its stop message calls such a process a read process. The script also stops, with the same message, when the header line does not fit the pattern of line 1010. |
| 1012 | `A2_OTHER = f"{m_.group(1)} {m_.group(2)}"` | `A2_OTHER`: the binary and the kernel of that process as one text. |
| 1013 | `check(True, f"journal of the 8000 MT/s boot, {A_DAY}: {len(HW_A)} corrected records from the first launch of A-1 ({A1_FIRST}) to the launch after the last A-3 process used ({A3_END}); "` | Adds the summary line of this block, always PASS. It gives the day, the number of records, the first launch of A-1 and the launch after the last A-3 process used. The saved output of a build shows 2 records at 20:50:58 and 2 at 20:51:10 [Ref5]. |
| 1014 | `            f"all in A-2: 2 at {HW_A2_T[0]} (launch second of bw_new read, round 1), 2 at {HW_A2_T[1]} (process {A2_OTHER}, launched {a2_other[0][1]})")` | Continues the text of line 1013: the two times with their processes. In the saved output of a build the second pair lies in a `bw_new write` process that was launched at 20:51:08 [Ref5]. |

### The interval with the lowest `asmread` rate of the pool, and function `clock` (lines 1016 to 1042)

| Line | Source | Explanation |
|---:|---|---|
| 1016 | `# the interval with the lowest asmread value of the pool: its time inside the process, from the T rows of the csv` | Comment: the interval with the lowest `asmread` value of the pool. The next lines compute its time inside the process from the T rows of the csv file. |
| 1017 | `need(LOWEST_ASM["dataset"] == "L-2" and LOWEST_ASM["tag"] == "p2add", "the lowest asmread interval of the pool is not in L-2 p2add")` | `LOWEST_ASM` (line 520) is the record with the lowest `asmread` rate of the pool. The script stops unless it belongs to row L-2, process `p2add`. |
| 1018 | `T_START = Decimal(repr(min(t[3] for t in t_rows(LOWEST_ASM))))      # seconds since the process start` | `T_START`: the lowest value of the field `t_start_s` (the tenth field) over the 120 T rows of this interval. `t_rows` (line 124) returns the rows. By the comment the value is in seconds from the start of the process. |
| 1019 | `T_END = Decimal(repr(max(t[4] for t in t_rows(LOWEST_ASM))))` | `T_END`: the highest value of the field `t_end_s` (the eleventh field) over these rows. |
| 1022 | `def clock(hms, add):` | Starts the function `clock`. It adds the seconds `add` to the time of day `hms`. |
| 1023 | `    """Launch time plus seconds since the process start, to the nearest second."""` | Comment: the documentation text. The result is the launch time plus the seconds from the process start, to the nearest second. |
| 1024 | `    h, m, s = (int(x) for x in hms.split(":"))` | Splits the time at the colons into hours, minutes and seconds. |
| 1025 | `    tot = h * 3600 + m * 60 + s + int(add.to_integral_value(rounding=ROUND_HALF_UP))` | `tot`: the time in seconds from midnight, plus `add` rounded to a whole number. A value exactly between two whole numbers is rounded up. |
| 1026 | `    return f"{tot // 3600:02d}:{tot // 60 % 60:02d}:{tot % 60:02d}"` | Returns the new time as `HH:MM:SS`, with two digits per part. |
| 1029 | `LOW_T0 = HW_ROWS[("L-2", "p2add")]["t0"]` | `LOW_T0`: the launch time of the process `p2add`, as `launches.txt` gives it (line 962). |
| 1030 | `LOW_FROM, LOW_TO = clock(LOW_T0, T_START), clock(LOW_T0, T_END)` | `LOW_FROM`, `LOW_TO`: the times of day at which the interval started and ended, to the nearest second (est.). The runner script `rx.sh` writes the launch time in whole seconds, directly before it starts the process. So both times can differ from the true times by about 1 s. |
| 1031 | `HW_LOW = hw_in(LOWEST_ASM["launch_utc"][:10], LOW_FROM, LOW_TO)` | `HW_LOW`: the hardware error records of that day from `LOW_FROM` to `LOW_TO`. |
| 1032 | `need(len(HW_LOW) == 2 and len({h["ts"] for h in HW_LOW}) == 1, "journal: not 2 records with one time inside the lowest asmread interval")` | The script stops unless these are exactly 2 records with one time stamp. This is the only interval for which the script computes a start time and an end time. It does not test whether a record lies inside any other interval. The counts of lines 957 to 999 are for the time window of a whole process (rows L-1 to L-4) or of a whole row (A-1 to A-3). The saved output of a build shows 2 records at 18:54:52, inside 18:54:51 to 18:54:55 [Ref5]. |
| 1033 | `m_ = re.search(rf"Without this (?:one )?interval the pool spans ({NUM}) to ({NUM}) GB/s", FMD)` | Searches `FACTS.md` for a sentence of the form `Without this interval the pool spans X to Y GB/s`. The word `one` before `interval` is optional. The two groups hold X and Y. |
| 1034 | `if m_:` | Case 1: `FACTS.md` holds such a sentence. |
| 1035 | `    check(near(q(rPL_asm_wo.lo), m_.group(1), "0.01") and near(q(rPL_asm_wo.hi), m_.group(2), "0.01"),` | The check compares both ends of `rPL_asm_wo` (line 521) with the sentence, to 0.01 GB/s. `rPL_asm_wo` is the range of the pool without this one interval. It is used only in line 522, in these lines and in one sentence of Table 5 (line 2567). Every other `asmread` comparison with the pool L-1 to L-4 uses `rPL_asm` or the list `P_L_ASM`, which hold all 11 intervals. So the lowest interval is not left out of the other results of the page. |
| 1036 | `          f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s, FACTS.md {m_.group(1)} to {m_.group(2)} GB/s")` | Continues the call of line 1035: the text of the check, with both ranges. |
| 1037 | `else:` | Case 2: `FACTS.md` holds no such sentence. |
| 1038 | `    check(True, f"pool L-1 to L-4 (asmread) without its lowest interval: computed {rPL_asm_wo.txt()} GB/s. FACTS.md holds no such sentence, so this value rests on the raw files only")` | The script adds a PASS line that says so. Its text says that the value then rests on the raw files only. |
| 1039 | `check(True, f"journal of the 8000 MT/s boot: corrected records during L-1: {HW_L1}, L-2: {HW_L2[0]} and {HW_L2[1]}, L-3 and L-4: {HW_L34}; "` | Adds the summary line of the journal checks, always PASS. It gives the numbers of records during L-1, during the two processes of L-2, and during L-3 and L-4. |
| 1040 | `            f"{len(HW_LOW)} records at {HW_LOW[0]['ts'][11:19]} inside the interval of {f2(val(LOWEST_ASM))} GB/s ({LOW_FROM} to {LOW_TO}); "` | Continues the text of line 1039: the records inside the lowest `asmread` interval, with their time, the rate of the interval and its two times. |
| 1041 | `            f"pool without it {rPL_asm_wo.txt()} GB/s")` | Continues the text of line 1039: the range of the pool without that interval. `state_table` (line 2503) prints these facts in Table 5. The saved output of a build shows 298.61 to 309.17 GB/s, computed and in `FACTS.md`, and 288.54 GB/s for the interval that is left out [Ref5]. |

### Firmware settings: function `set_records` and the checks of the settings files (lines 1043 to 1099)

| Line | Source | Explanation |
|---:|---|---|
| 1043 | `# firmware settings (defect state-r3-S3-1, checked here)` | Comment: the next lines check the firmware settings. The comment names a second review finding by its identifier, `state-r3-S3-1`. The file `review-w2.json` in `S` holds it. |
| 1044 | `FW = R + "/fwtest-20261117"` | `FW`: the result folder `fwtest-20261117` of the firmware test. |
| 1047 | `def set_records(path):` | Starts the function `set_records`. It reads one file `set.txt`, which holds the replies of the settings tool. |
| 1048 | `    """(name, answer) of every response of a settings file that carries 'modified: true', and the time of line 1."""` | Comment: the documentation text. The result is the pair (name, answer) of every response of a settings file that carries `modified: true`, and the time of the first line. |
| 1049 | `    text = "\n".join(lines_of(path))` | `text`: the whole file as one text. |
| 1050 | `    out = [(m.group(1), m.group(2)) for m in re.finditer(r'name: "([^"]+)",\s*answer: "([^"]+)",[^}]*\},\s*modified: true', text, re.S)]` | `out`, first form of a reply: a text block with the lines `name: "..."`, `answer: "..."` and `modified: true`. The pattern keeps the name (group 1) and the answer (group 2). Between the answer and `modified: true` it allows any text without a closing brace, then one closing brace and a comma. `re.S` lets the pattern run across line ends. |
| 1051 | `    for line in text.splitlines():` | Goes through the lines of the file. |
| 1052 | `        if line.startswith('{"responses"'):` | Second form of a reply: a JSON line that starts with `{"responses"`. |
| 1053 | `            for resp in json.loads(line)["responses"]:` | Parses the line and goes through its list `responses`. |
| 1054 | `                if resp.get("modified") is True:` | Uses only a reply whose field `modified` is true. |
| 1055 | `                    out.append((resp["question"]["name"], resp["question"]["answer"]))` | Adds the pair (name, answer) of the setting to `out`. |
| 1056 | `    m = re.match(r"^\w+ Nov 17 (\d\d:\d\d:\d\d) (AM\|PM) UTC 2026$", text.splitlines()[0])` | Applies a pattern to the first line of the file. It matches a date line of 17 November 2026 with `AM` or `PM`, of the form `Tue Nov 17 03:43:50 AM UTC 2026`. Group 1 holds the time in the 12-hour form, and group 2 holds `AM` or `PM`. |
| 1057 | `    when = None` | `when`: the time of the first line. It stays without a value when that line is not such a date line. |
| 1058 | `    if m:` | Tests whether the first line matched. |
| 1059 | `        h = int(m.group(1)[:2]) % 12 + (12 if m.group(2) == "PM" else 0)` | `h`: the hour in the 24-hour form. The hour 12 becomes 0, and 12 is added for `PM`. |
| 1060 | `        when = f"{h:02d}{m.group(1)[2:]}"` | `when`: the time as `HH:MM:SS` in the 24-hour form. |
| 1061 | `    return out, when` | Returns the list of pairs and the time. |
| 1064 | `X1, X1_T = set_records(FW + "/x1/set.txt")` | `X1`, `X1_T`: the changed settings and the time of the file `set.txt` in the folder `x1` of the firmware test. |
| 1065 | `X2, X2_T = set_records(FW + "/x2/set.txt")` | `X2`, `X2_T`: the same for the folder `x2`. |
| 1066 | `RV, RV_T = set_records(FW + "/revert/set.txt")` | `RV`, `RV_T`: the same for the folder `revert`. The revert is the step that set both values back. |
| 1067 | `D72, _ = set_records(R + "/dimm7200-20261117/set.txt")` | `D72`: the changed settings of the file `set.txt` in the folder `dimm7200-20261117`. Its time is not kept. So four files are read here. |
| 1068 | `need(X1 == [("TXREQ Min", "1/4 L2 TQ")] and X2 == [("TXREQ Max", "1/4 L2 TQ")], "fwtest: the two TXREQ changes are not as expected")` | The script stops unless `x1` holds one change, `TXREQ Min` to `1/4 L2 TQ`, and `x2` holds one change, `TXREQ Max` to `1/4 L2 TQ`. |
| 1069 | `Q_BASE = json.load(open(R + "/uefisettings-20261117/questions.json"))` | `Q_BASE`: the settings list that was saved in the 8000 MT/s boot, read from a JSON file. |
| 1070 | `Q_REV = json.load(open(FW + "/revert/questions.json"))` | `Q_REV`: the settings list that was saved after the revert. |
| 1071 | `orig = {x["name"]: x["answer"] for x in Q_BASE if x["name"] in ("TXREQ Max", "TXREQ Min")}` | `orig`: the values of `TXREQ Max` and `TXREQ Min` in `Q_BASE`. |
| 1072 | `need(len(orig) == 2 and sorted(RV) == sorted(orig.items()), "fwtest: the revert does not set both TXREQ settings to the original values")` | The script stops unless the revert changed exactly these two settings, to these values. |
| 1073 | `need(X1_T and X2_T and RV_T and X1_T < X2_T < RV_T, "fwtest: times of the three records")` | The script stops unless each of the three files gave a time and the times are in the order `x1`, `x2`, revert. |
| 1074 | `canon = lambda qs: sorted(json.dumps(x, sort_keys=True) for x in qs)` | `canon`: a lambda that turns a settings list into sorted JSON texts, one per entry. So two lists can be compared without their order. |
| 1075 | `need(len(Q_BASE) == len(Q_REV) and canon(Q_BASE) == canon(Q_REV), "fwtest: the settings list after the revert differs from the list of the 8000 MT/s boot")` | The script stops unless the two lists have the same length and the same entries. The order of the entries is not compared. |
| 1076 | `need([x["answer"] for x in Q_BASE if x["name"] == "DIMM Frequency"] == ["8000 MT/s"], "settings list of the 8000 MT/s boot: DIMM Frequency is not 8000 MT/s")` | The script stops unless `Q_BASE` holds exactly one setting `DIMM Frequency`, and its value is `8000 MT/s`. |
| 1077 | `QBASE_T = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(R + "/uefisettings-20261117/questions.json")))` | `QBASE_T`: the file time of the settings list of the 8000 MT/s boot, as a UTC time stamp. |
| 1078 | `need(BOOT8_FROM < QBASE_T < BOOT8_TO, "settings list of the 8000 MT/s boot: its file time is not inside that boot")` | The script stops unless this file time lies after `BOOT8_FROM` and before `BOOT8_TO` (line 937). |
| 1079 | `N_SET = len(Q_BASE)` | `N_SET`: the number of entries of the settings list. |
| 1080 | `SAME_ORDER = Q_BASE == Q_REV` | `SAME_ORDER`: whether the two lists are equal in their order too. |
| 1081 | `UNREAD = {}        # kind of error marker -> number of entries that show it in place of a value` | `UNREAD`: a dictionary from the name of an error marker to the number of entries that show this marker in place of a value. It starts empty. |
| 1082 | `for x in Q_BASE:` | Goes through the entries of `Q_BASE`. |
| 1083 | `    m_ = re.match(r"^<(\w+):", str(x["answer"]))` | Tests whether the answer of the entry is an error marker of the form `<Name: ...>`. The group holds the name. |
| 1084 | `    if m_:` | Only an entry with an error marker is counted. |
| 1085 | `        UNREAD[m_.group(1)] = UNREAD.get(m_.group(1), 0) + 1` | Adds 1 to the count of that marker name. |
| 1086 | `need(set(UNREAD) == {"ValueUnavailable", "VStoreError"}, f"settings list: unexpected kinds of error marker: {sorted(UNREAD)}")` | The script stops unless the marker names are exactly `ValueUnavailable` and `VStoreError`. For such an entry, line 1075 compares the marker text. It does not compare a value of the setting. |
| 1087 | `N_UNREAD = sum(UNREAD.values())` | `N_UNREAD`: the total number of entries without a readable value. The saved output of a build shows 1490 entries, of which 886 have no readable value [Ref5]. |
| 1088 | `need(D72 == [("DIMM Frequency", "7200 MT/s")], "dimm7200 set.txt: not the single change DIMM Frequency = 7200 MT/s")` | The script stops unless `set.txt` of the folder `dimm7200-20261117` holds one change: `DIMM Frequency` to `7200 MT/s`. |
| 1089 | `SET_FILES = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(R) for f in fs if f == "set.txt")` | `SET_FILES`: every file with the name `set.txt` under `R`, sorted. `os.walk` goes through the whole folder tree. |
| 1090 | `need(SET_FILES == sorted([FW + "/x1/set.txt", FW + "/x2/set.txt", FW + "/revert/set.txt", R + "/dimm7200-20261117/set.txt"]),` | The script stops unless these are exactly the 4 files that lines 1064 to 1067 read. |
| 1091 | `     "results folder: the files named set.txt are not the 4 expected ones")` | Continues the call of line 1090: the stop message. |
| 1092 | `D72_T = time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(R + "/dimm7200-20261117/set.txt")))` | `D72_T`: the file time of the `set.txt` of `dimm7200-20261117`, as a UTC time of day. |
| 1093 | `need(RV_T < D72_T < TRY6_UTC[11:19], "dimm7200 set.txt: file time is not between the revert and the boot record")` | The script stops unless this time lies after the time of the revert and before the time in the first line of `try6.txt`. Only the times of day are compared, not the dates. |
| 1094 | `check(True, f"firmware settings: TXREQ Min changed {X1_T}, TXREQ Max changed {X2_T}, both set back {RV_T} to the values of the 8000 MT/s list; "` | Adds the summary line of the firmware settings, always PASS. The saved output of a build shows the two changes at 03:43:50 and 04:05:38, the revert at 04:13:19 and the file time 19:43:03 [Ref5]. |
| 1095 | `            f"list after the revert equal in {N_SET} entries ({N_UNREAD} without a readable value: {UNREAD['ValueUnavailable']} ValueUnavailable, {UNREAD['VStoreError']} VStoreError); 4 files set.txt under R, last: DIMM Frequency = 7200 MT/s ({D72_T} file time)")` | Continues the text of line 1094: the number of equal entries of the two lists, the entries without a readable value per marker name, and the 4 files `set.txt` with the last change. |
| 1097 | `# start state of the three visits of the part L line in the 7200 MT/s boot (process lists, time since the start of the boot)` | Comment: the next lines check the start state of the three visits of the part L line in the 7200 MT/s boot. They use the process lists and the time from the start of the boot. |

### Start state of the three visits of the part L line: function `proc_list` and the checks (lines 1100 to 1139)

| Line | Source | Explanation |
|---:|---|---|
| 1100 | `def proc_list(path):` | Starts the function `proc_list`. It reads the process list of a file `env.txt`. The runner script `rx.sh` writes this list with the tool `ps`: sorted by %CPU, highest value first, and limited to the first 5 processes. `ps` computes %CPU as the CPU time that a process has used, divided by the time from the start of the process. So the value is an average over the life of the process. |
| 1101 | `    """Time of line 1 and the rows (user, %CPU, command) of the process list of an env.txt file."""` | Comment: the documentation text. The result is the time of the first line and the rows (user, %CPU, command) of the process list of an `env.txt` file. |
| 1102 | `    ll = lines_of(path)` | `ll`: the lines of the file. |
| 1103 | `    m_ = re.match(r"^\w+ Nov 17 (\d\d):(\d\d:\d\d) (AM\|PM) UTC 2026$", ll[0])` | Applies a pattern to the first line: a date line of 17 November 2026 with `AM` or `PM`. Group 1 holds the hour, group 2 holds the minutes and the seconds, and group 3 holds `AM` or `PM`. |
| 1104 | `    need(m_, f"{path}: line 1 is not a time of 2026-11-17")` | The script stops unless the first line is such a date line. |
| 1105 | `    when = f"{int(m_.group(1)) % 12 + (12 if m_.group(3) == 'PM' else 0):02d}:{m_.group(2)}"` | `when`: the time of that line as `HH:MM:SS` in the 24-hour form. The hour 12 becomes 0, and 12 is added for `PM`. |
| 1106 | `    need(ll[3].split() == ["USER", "%CPU", "COMMAND"], f"{path}: line 4 is not the head of the process list")` | The script stops unless the fourth line is the title line with the words `USER`, `%CPU` and `COMMAND`. `rx.sh` writes the output of the tool `who` (one line per login) before the process list. So the fourth line is the title line only when `who` printed no line. |
| 1107 | `    rows = []` | `rows`: the rows of the process list. The list starts empty. |
| 1108 | `    for no, l in enumerate(ll[4:], 5):` | Goes through the lines from the fifth line on. `no` is the line number. |
| 1109 | `        if l.startswith("binary "):` | Tests whether the line starts with `binary `. |
| 1110 | `            break` | The first such line ends the process list. |
| 1111 | `        u, c, name = l.split(None, 2)` | Splits the line into three parts at its first two runs of spaces: user, %CPU and command. |
| 1112 | `        rows.append((no, u, Decimal(c), name.strip()))` | Each such line becomes one row: line number, user, %CPU as a `Decimal`, command. Each of the 6 files `env.txt` that the script reads holds 5 such rows. These files lie in the result folders of F72d12, T72L1, T72L2, T72L3, T72I1 and T72I2 (line 1118, line 1131). |
| 1113 | `    need(len(rows) >= 3, f"{path}: process list too short")` | The script stops when there are fewer than 3 rows. |
| 1114 | `    return when, rows` | Returns `when` and the rows. |
| 1117 | `F_ENV = R + "/w120-w120-F72d12-20261117T200231Z/env.txt"` | `F_ENV`: the path of `env.txt` in the result folder of F72d12, the first of the three visits. |
| 1118 | `F_ENV_T, F_PROCS = proc_list(F_ENV)` | `F_ENV_T`: the time of its first line. `F_PROCS`: the rows of its process list. |
| 1119 | `F_TOP = max(F_PROCS, key=lambda x: x[2])` | `F_TOP`: the row of that list with the highest %CPU. |
| 1120 | `need(F_TOP[0] == 5 and F_TOP[3] == "pr/ttyAMA-1" and F_TOP[1] == "root", "F72d12 env.txt: the busiest process is not pr/ttyAMA-1 in line 5")` | The script stops unless this row is the fifth line of the file, the command `pr/ttyAMA-1` of the user `root`. |
| 1121 | `GAPS = R + "/dimm7200-20261117/gaps.txt"` | `GAPS`: the path of `gaps.txt`, a file that was saved in the 7200 MT/s boot. |
| 1122 | `m_ = re.match(r"^0 first=2026-11-17T(\d\d:\d\d:\d\d)\+00:00 ", lines_of(GAPS)[6])` | Applies a pattern to the seventh line of `gaps.txt`. The line must start with `0 first=` and a time of 2026-11-17. The group holds the time of day. |
| 1123 | `need(m_, "gaps.txt: line 7 is not the row of boot 0")` | The script stops unless the line has this form. By the stop message this line is the row of boot 0. |
| 1124 | `BOOT7_KLOG = m_.group(1)                                   # first kernel log line of the boot of the rerun` | `BOOT7_KLOG`: by the comment, the time of the first Linux kernel log line of the boot of the rerun. The script takes only this time from the line. By the facts sheet the same line holds a second time, 20:06:34, and the text `hwerr=0` [Ref1]. The script does not read them. |
| 1125 | `F_AFTER_BOOT_S = secs(F_LAUNCH) - secs(BOOT7_KLOG)` | `F_AFTER_BOOT_S`: the launch time of F72d12 minus `BOOT7_KLOG`, in seconds. |
| 1126 | `F_ENV_BEFORE_S = secs(F_LAUNCH) - secs(F_ENV_T)` | `F_ENV_BEFORE_S`: the launch time of F72d12 minus the time of the process list, in seconds. |
| 1127 | `need(0 < F_AFTER_BOOT_S < 60 and 0 < F_ENV_BEFORE_S < 60, "F72d12: launch is not shortly after the first kernel log line and the process list")` | The script stops unless both are above 0 s and below 60 s. The saved output of a build shows 20 s and 5 s, and 51.6 %CPU for `pr/ttyAMA-1` [Ref5]. |
| 1128 | `VISIT_ENV = {}` | `VISIT_ENV`: a dictionary with one entry per step of part L and of control I, the two later visits. It starts empty. |
| 1129 | `for tg in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):` | Goes through the 5 steps: three of part L and two of control I. |
| 1130 | `    fo = [r for r in L_OLD + I_OLD if r["tag"] == tg][0]["folder"].replace("R/", R + "/", 1)` | `fo`: the full path of the result folder of the step. It comes from the first `oldread` record with this tag. |
| 1131 | `    when, rows = proc_list(fo + "/env.txt")` | `proc_list` reads the file `env.txt` of that folder. |
| 1132 | `    need(0 < secs(LAUNCH[tg]["first_launch"][11:19]) - secs(when) < 60, f"{tg}: env.txt was not written shortly before the launch")` | The script stops unless the process list was written more than 0 s and less than 60 s before the first launch of the step (`first_launch` in `meta.launches`). |
| 1133 | `    VISIT_ENV[tg] = (fo + "/env.txt", max(x[2] for x in rows))` | Keeps the path of `env.txt` and the highest %CPU of its list. |
| 1134 | `L_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72L1", "T72L2", "T72L3"))` | `L_ENV_MAX`: the highest %CPU of the three lists of part L. |
| 1135 | `I_ENV_MAX = max(VISIT_ENV[t][1] for t in ("T72I1", "T72I2"))` | `I_ENV_MAX`: the highest %CPU of the two lists of control I. |
| 1136 | `need(max(L_ENV_MAX, I_ENV_MAX) < 1, "part L or control I: a process list shows a busy process")` | The script stops unless the highest %CPU value of all 5 lists is below 1 %. %CPU is an average over the life of a process. So this test cannot show a short busy phase of a process that has run from the boot on. |
| 1137 | `check(True, f"start state: F72d12 launched {F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG}); its process list, written {F_ENV_BEFORE_S} s before the launch, "` | Adds the summary line of this block, always PASS. It gives the seconds from the first Linux kernel log line of the boot to the launch of F72d12, and the seconds from its process list to the launch. |
| 1138 | `            f"shows {F_TOP[3]} at {F_TOP[2]} %CPU; process lists of part L and control I: at most {max(L_ENV_MAX, I_ENV_MAX)} %CPU")` | Continues the text of line 1137: the busiest process of F72d12 with its %CPU, and the highest %CPU of the lists of part L and control I. The saved output of a build shows at most 0.1 %CPU for these lists [Ref5]. |

### Module count: the boot with 10 modules, the module list, the sixth line of `try6.txt` (lines 1140 to 1176)

| Line | Source | Explanation |
|---:|---|---|
| 1140 | `# the number in the kernel line "This system has N DIMM sockets" is not the slot count: a boot of 2026-11-17 printed 10` | Comment: the number in the Linux kernel line `This system has N DIMM sockets` is not the slot count of the board. A boot of 2026-11-17 printed 10. The lines of this part continue the raw-file checks for the machine state section of the page, which start at line 811. |
| 1141 | `KLOG10 = R + "/dimm-check-20261117/k-1.txt"` | `KLOG10`: the path of `k-1.txt`, the saved Linux kernel log of the boot BASEd10 (line 1300). |
| 1142 | `k10 = lines_of(KLOG10)` | `k10`: the lines of that file. |
| 1143 | `K10_LINE = [i for i, l in enumerate(k10, 1) if "ghes_edac: This system has 10 DIMM sockets" in l]` | `K10_LINE`: the numbers of its lines with the text `ghes_edac: This system has 10 DIMM sockets`. |
| 1144 | `mk10 = re.match(r"^Nov (\d\d) (\d\d:\d\d:\d\d) ", k10[0])` | Applies the pattern of line 935 to the first line of the log: `Nov`, a day and a time. |
| 1145 | `need(len(K10_LINE) == 1 and mk10, "kernel log k-1.txt: no single line with 10 modules, or no time in line 1")` | The script stops unless exactly one such line exists and the first line starts with `Nov`, a day and a time. |
| 1146 | `BOOT10_FROM = f"2026-11-{mk10.group(1)} {mk10.group(2)}"` | `BOOT10_FROM`: the date and the time of the first line of that log. The year 2026 and the month 11 are fixed text of the script. In the saved output of a build it is 2026-11-17 04:17:19 [Ref5]. So this boot printed 10, and the boot of the rerun printed 12 (checked in line 897). |
| 1149 | `def mem_line(ll):` | Starts the function `mem_line`. It takes the lines of a Linux kernel log and finds the memory size line. |
| 1150 | `    hit = [(i, re.search(r"kernel: Memory: (\d+)K/(\d+)K available", l)) for i, l in enumerate(ll, 1)]` | Searches each line for the text `kernel: Memory: aK/bK available`, where a and b are numbers. Group 1 holds a and group 2 holds b. `hit` gets one pair per line: the line number and the result of the search. |
| 1151 | `    hit = [(i, int(m.group(2))) for i, m in hit if m]` | Keeps the lines that matched. Each becomes the line number and the number b (the second number, after the slash) as a whole number. |
| 1152 | `    need(len(hit) == 1, "kernel log: no single line 'Memory:'")` | The script stops unless exactly one line matches. |
| 1153 | `    return hit[0]` | Returns the line number and the number b of that line. |
| 1156 | `K10_MEM, K12_MEM = mem_line(k10), mem_line(kl)` | `K10_MEM`, `K12_MEM`: the memory size line of `k-1.txt` and of `k-5.txt`. `k10` holds the lines of `k-1.txt`. `kl` holds the lines of `k-5.txt`, the saved Linux kernel log of the 8000 MT/s boot (line 934). |
| 1157 | `MEM_LESS_GIB = Decimal(K12_MEM[1] - K10_MEM[1]) / (1024 * 1024)` | `MEM_LESS_GIB`: the difference of the two numbers after the slash, divided by 1024 x 1024. The numbers are in KiB (1 KiB = 1024 bytes). So the result is in GiB (1 GiB = 1024 x 1024 KiB). |
| 1158 | `need(MEM_LESS_GIB == 64, "kernel logs: the 10-module boot does not show 64 GiB less memory than the 8000 MT/s boot")` | The script stops unless the result is exactly 64 GiB. By the facts sheet the log of the 8000 MT/s boot holds 402090256K and the log of the boot with 10 modules holds 334981392K. The difference is 67108864 KiB [Ref1]. |
| 1159 | `# the module list that was saved in the boot of the rerun` | Comment: the next lines check the module list that was saved in the boot of the rerun. |
| 1160 | `DMI = R + "/dimm7200-20261117/dmi17-7200.txt"` | `DMI`: the path of `dmi17-7200.txt`, that module list. |
| 1161 | `dmi = lines_of(DMI)` | `dmi`: the lines of that file. |
| 1162 | `DMI_N = sum(1 for l in dmi if l.strip() == "Memory Device")` | `DMI_N`: the number of lines that are exactly `Memory Device`, one per module. |
| 1163 | `need(DMI_N == 12 and sum(1 for l in dmi if "Configured Memory Speed:" in l) == 12 == sum(1 for l in dmi if l.strip() == "Configured Memory Speed: 7200 MT/s"),` | The script stops unless `DMI_N` is 12, 12 lines hold the text `Configured Memory Speed:`, and 12 lines are exactly `Configured Memory Speed: 7200 MT/s`. |
| 1164 | `     "module list of the rerun boot: not 12 modules with one line 'Configured Memory Speed: 7200 MT/s' each")` | Continues the call of line 1163: the stop message. |
| 1165 | `need(time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(DMI))) == BOOT_LAST, "module list of the rerun boot: its file time is not inside row 0 of boots.txt")` | Reads the file time of the module list as a UTC time of day. The script stops unless it equals `BOOT_LAST`, the end time of row 0 of `boots.txt` (line 907). The stop message says `not inside row 0`, but the test is equality with that end time. |
| 1166 | `# line 6 of try6.txt ("modules=24") is not the module count: the module list holds that number of lines with the text "Size: 32 GB"` | Comment: the sixth line of `try6.txt`, which the comment quotes as `modules=24`, is not the module count. The module list holds that number of lines with the text `Size: 32 GB`. The next lines test this. |
| 1167 | `DMI_SIZE = sum(1 for l in dmi if "Size: 32 GB" in l)` | `DMI_SIZE`: the number of lines of the module list that contain `Size: 32 GB`. |
| 1168 | `DMI_SIZE_PLAIN = sum(1 for l in dmi if l.strip() == "Size: 32 GB")` | `DMI_SIZE_PLAIN`: the number of lines that are exactly `Size: 32 GB`. |
| 1169 | `DMI_SIZE_VOL = sum(1 for l in dmi if l.strip() == "Volatile Size: 32 GB")` | `DMI_SIZE_VOL`: the number of lines that are exactly `Volatile Size: 32 GB`. |
| 1170 | `need(DMI_SIZE == TRY6_MODLINE == DMI_SIZE_PLAIN + DMI_SIZE_VOL and DMI_SIZE_PLAIN == DMI_SIZE_VOL == DMI_N,` | The script stops unless `DMI_SIZE` equals `TRY6_MODLINE` (line 900) and the sum of the two exact counts, and each exact count equals `DMI_N`. So the number of the sixth line is two lines per module. |
| 1171 | `     "try6.txt line 6: its number is not the number of lines with 'Size: 32 GB' in the module list (one 'Size' and one 'Volatile Size' line per module)")` | Continues the call of line 1170: the stop message. The saved output of a build shows 24 lines: 12 `Size` lines and 12 `Volatile Size` lines [Ref5]. |
| 1172 | `check(True, f"module count: try6.txt line 5 holds '12 DIMM sockets'; the module list saved at {BOOT_LAST} holds {DMI_N} modules with one speed line each; "` | `check(True, ...)` adds one line to the self-check list. It holds the values that lines 1140 to 1171 checked. The line is always PASS: a false fact has already stopped the script in a `need` call. This first part of the text gives the line of `try6.txt` with `12 DIMM sockets` and the number of modules of the module list. |
| 1173 | `            f"the kernel log of the boot of {BOOT10_FROM} holds '10 DIMM sockets' and {MEM_LESS_GIB} GiB less memory; "` | Continues the text of line 1172: the Linux kernel log of the boot with `10 DIMM sockets`, and how many GiB of memory it shows less. |
| 1174 | `            f"try6.txt line 6 reads 'modules={TRY6_MODLINE}', and the module list holds {DMI_SIZE} lines with 'Size: 32 GB' ({DMI_SIZE_PLAIN} 'Size' and {DMI_SIZE_VOL} 'Volatile Size')")` | Continues the text of line 1172: the number in the sixth line of `try6.txt`, and the counts of the lines with `Size: 32 GB`. |
| 1175 | `need(all(l.startswith("done /home/jhan/") for l in gl + g2l if l.startswith("done ")), "run logs: a result folder is not under the home folder of jhan")` | `gl` and `g2l` are the lines of the two run logs (line 873). The script stops unless every line that starts with `done ` continues with `/home/jhan/`. So every result folder that the logs name lies under the home folder of the user jhan. |

### Argument lines: which process ran which line, and a scan of all csv header lines (lines 1177 to 1232)

| Line | Source | Explanation |
|---:|---|---|
| 1177 | `# the argument lines: which earlier rows ran the line of part L, and whether the lines of part C ran before` | Comment: the argument lines. The block up to line 1231 answers two questions from the raw files. Which earlier rows ran the argument line of part L? Did the argument lines of part C run before the rerun? |
| 1178 | `def spec_line(path):` | Starts the function `spec_line`. It reads a spec file. |
| 1179 | `    """(name, arguments, kernel sequence) of the one argument line of a spec file."""` | Comment: the documentation text. The result is the name, the arguments and the kernel sequence of the one argument line of a spec file. |
| 1180 | `    ll = [l for l in lines_of(path) if l.strip()]` | `ll`: the lines of the file without its empty lines. |
| 1181 | `    need(len(ll) == 1 and "\|" in ll[0], f"{path}: not one argument line")` | The script stops unless exactly one line is left and that line contains `\|`. |
| 1182 | `    name, args = ll[0].split("\|", 1)` | Splits the line at the first `\|` into the name and the arguments. |
| 1183 | `    m = re.search(r"--seq (\S+)", args)` | Looks for the kernel sequence: the word after `--seq`. The group holds it. |
| 1184 | `    need(m, f"{path}: no kernel sequence")` | The script stops when the arguments hold no `--seq`. |
| 1185 | `    return name, args.strip(), m.group(1)` | Returns the name, the arguments without spaces at both ends, and the kernel sequence. |
| 1188 | `def launch_args(folder, tag):` | Starts the function `launch_args`. `folder` is a result folder in the short form `R/...`. `tag` is the name of a process. |
| 1189 | `    """The arguments of the launch line of a process in launches.txt of a result folder (R/...)."""` | Comment: the documentation text. The result is the arguments of the launch line of a process in the file `launches.txt` of a result folder. |
| 1190 | `    hit = [l for l in lines_of(folder.replace("R/", R + "/", 1) + "/launches.txt") if l.startswith(f"launch {tag} ")]` | `hit`: the lines of `launches.txt` of that folder that start with `launch`, the tag and a space. |
| 1191 | `    need(len(hit) == 1 and " args " in hit[0], f"{folder}: no single launch line of {tag}")` | The script stops unless exactly one such line exists and holds the text ` args `. |
| 1192 | `    return hit[0].split(" args ", 1)[1].strip()` | Returns the text after ` args `, without spaces at both ends. The runner script `rx.sh` writes such a line directly before it starts the binary with these arguments. |
| 1195 | `SPEC = {nm: spec_line(f"{S}/{nm}.spec") for nm in ("like", "cfwd", "crev")}` | `SPEC`: a dictionary. It maps `like`, `cfwd` and `crev` to the result of `spec_line` for the spec file of that name in `S`. |
| 1196 | `LINE_L = SPEC["like"][0]                                   # the name of the part L line: its csv file carries it` | `LINE_L`: the name of the part L line. By the comment the csv file of such a process carries this name. The file `like.spec` gives the name `a6456`, so the csv file is `a6456.csv`. |
| 1197 | `no_seq = lambda a: re.sub(r"--seq \S+", "--seq X", a)` | `no_seq`: a lambda that replaces the kernel sequence of an argument line by `X`. |
| 1198 | `need(no_seq(SPEC["like"][1]) == no_seq(SPEC["cfwd"][1]) == no_seq(SPEC["crev"][1]) and len({v[2] for v in SPEC.values()}) == 3,` | The script stops unless the three argument lines are equal after this replacement and the three kernel sequences are three different texts. So the argument lines of part L and of part C differ in the kernel sequence only. Before the sequence all three files hold `--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2`. After the sequence all three hold `--count --pmu-type 11 --events` and the same list of 6 events. `--count` makes the runner count hardware events of the CPU. |
| 1199 | `     "the three argument lines do not differ in the kernel sequence only")` | Continues the call of line 1198: the stop message. |
| 1200 | `SAME_LINE_FOLDERS = sorted({r["folder"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]})` | `SAME_LINE_FOLDERS`: the sorted list of the result folders of the `oldread` records of part L, control I, F72d12 and row L-1. |
| 1201 | `need(len(SAME_LINE_FOLDERS) == 7 and all(launch_args(fo, LINE_L) == SPEC["like"][1] for fo in SAME_LINE_FOLDERS),` | The script stops unless the list has 7 folders and the launch line of the process `LINE_L` in each folder holds exactly the arguments of `like.spec`. |
| 1202 | `     "row L-1, part L, control I or F72d12: a process did not run the argument line of part L")` | Continues the call of line 1201: the stop message. |
| 1203 | `need({r["file"] for r in L_OLD + I_OLD + F_OLD + B_L_OLD["L-1"]} == {LINE_L + ".csv"}, "the csv file of a process of the part L line does not carry the name of the line")` | The script stops unless the csv file of each of these records is `LINE_L` plus `.csv`. So these rows ran the same benchmark arguments as part L. |
| 1204 | `C_FOLDERS = sorted({r["folder"] for r in C_OLD})` | `C_FOLDERS`: the sorted list of the result folders of the `oldread` records of part C. |
| 1205 | `for fo in C_FOLDERS:` | Goes through these folders. |
| 1206 | `    nms = sorted({r["file"][:-4] for r in C_OLD if r["folder"] == fo})` | `nms`: the csv file names of these records in the folder, without `.csv`. |
| 1207 | `    need(len(nms) == 1 and nms[0] in ("cfwd", "crev") and launch_args(fo, nms[0]) == SPEC[nms[0]][1], f"{fo}: the process did not run the argument line of its spec file")` | The script stops unless the folder has one name, the name is `cfwd` or `crev`, and the launch line of that process holds exactly the arguments of the spec file with the same name. |
| 1208 | `SEQ_FOLDERS, READ_FOLDERS, N_CSV = {}, set(), 0     # kernel sequence -> result folders with a csv file whose header line holds it` | Three stores for a scan of every csv file under the results folder `R`. `SEQ_FOLDERS` maps each kernel sequence to the set of result folders with a csv file whose header line holds it. `READ_FOLDERS` collects the folders with the kernel `read` in a sequence. `N_CSV` counts the csv files. The scan uses header lines only. It takes no rate from these files. |
| 1209 | `for dp_, _, fs_ in os.walk(R):` | `os.walk` goes through the folder tree of `R`, at any depth. `dp_` is a folder and `fs_` holds the names of its files. |
| 1210 | `    for f_ in fs_:` | Goes through the files of the folder. |
| 1211 | `        if f_.endswith(".csv"):` | Uses only the files whose name ends with `.csv`. |
| 1212 | `            N_CSV += 1` | Counts the file in `N_CSV`. |
| 1213 | `            with open(os.path.join(dp_, f_), encoding="utf-8", errors="replace") as fh_:` | Opens the csv file as UTF-8 text. A byte that is not valid UTF-8 becomes a replacement character. |
| 1214 | `                for l in fh_:` | Goes through the lines of the file. |
| 1215 | `                    if l.startswith("# bwx"):` | Only the lines that start with `# bwx` are used. |
| 1216 | `                        if re.match(r"^# bwx\d+ trial mode:", l):` | Tests whether the line has the form `# bwx`, digits and ` trial mode:`. |
| 1217 | `                            continue                # one-CPU trial files of older runners: they hold no kernel sequence` | Such a line is skipped. The comment says that these are one-CPU trial files of older runners, and that they hold no kernel sequence. Under the results folder `R`, 43 csv files hold such lines. All 43 lie in folders whose names start with `bwx8-`, `bwx9-`, `bwx10-` or `bwx11-`. None of these files holds a `# bwx: seq=` line. 37 of the 43 files hold process header lines. Each of these lines holds `--trial` and one CPU number. The other 6 files hold no process header line. |
| 1218 | `                        m_ = re.match(r"^# bwx: seq=(\S+)", l)` | Every line that is not skipped must start with `# bwx: seq=`. The group holds the kernel sequence. |
| 1219 | `                        need(m_, f"{dp_}/{f_}: a header line of a runner that is neither a kernel sequence nor a trial-mode header")` | If the line does not have this form, the script stops. |
| 1220 | `                        fo_ = "R/" + os.path.relpath(dp_, R).split(os.sep)[0]` | `fo_`: the top-level result folder of the file, in the short form `R/...`. |
| 1221 | `                        SEQ_FOLDERS.setdefault(m_.group(1), set()).add(fo_)` | Adds the folder to the set of this kernel sequence in `SEQ_FOLDERS`. |
| 1222 | `                        if "read" in m_.group(1).split(","):` | Tests whether the sequence names the kernel `read`. The sequence is split at its commas. So the names `oldread` and `asmread` do not count. |
| 1223 | `                            READ_FOLDERS.add(fo_)` | Adds the folder to `READ_FOLDERS`. |
| 1224 | `need(sorted(SEQ_FOLDERS[SPEC["cfwd"][2]] \| SEQ_FOLDERS[SPEC["crev"][2]]) == C_FOLDERS, "csv files of the results folder: a folder other than the 4 part C folders holds a part C kernel sequence")` | Three hard assertions on the result of the scan follow (line 1224, line 1227 and line 1229), then one line for the self-check list. This one: the folders with the sequence of `cfwd.spec` or of `crev.spec` must be exactly the part C folders. So no csv file in another folder under `R` holds a part C sequence. |
| 1225 | `# the kernel read in a sequence: the 4 part C folders, and folders of the older runner bwx (rules file, part A list: B7-*, C3-*, SHORT-*; part C list: B5-*)` | Comment: the kernel `read` in a sequence. By the comment it stands in the 4 part C folders and in folders of the older runner bwx. The comment names two lists of the rules file: the part A list with `B7-*`, `C3-*` and `SHORT-*`, and the part C list with `B5-*`. |
| 1226 | `READ_OTHER = sorted(READ_FOLDERS - set(C_FOLDERS))` | `READ_OTHER`: the folders with the kernel `read` in a sequence that are not part C folders, sorted. |
| 1227 | `need(READ_OTHER and all(re.match(r"^R/(B5\|B7\|C3\|SHORT)-2026111[34]T", fo_) for fo_ in READ_OTHER),` | The script stops unless the list is not empty and each name starts with `R/B5-`, `R/B7-`, `R/C3-` or `R/SHORT-` and a date of 2026-11-13 or 2026-11-14. The script tests the folder names only. In the csv files of the 7 folders of this list, every process header line names the binary `bwx`, except 3 lines of the file `SHORT.csv` in the folder `SHORT-20261113T214338Z`. These 3 lines name `bwx_o0`, `bwx_o36` and `bwx_o52`. The kernel sequences of these 3 lines do not hold `read`. So each of the 124 process header lines with `read` in its sequence names the binary `bwx`. |
| 1228 | `     f"csv files of the results folder: the kernel read is in a sequence of a folder that is neither part C nor a folder of runner bwx: {READ_OTHER}")` | Continues the call of line 1227: the stop message, with the list. |
| 1229 | `need({r["folder"] for r in OTHER} <= set(READ_OTHER), "runner bwx: a folder used on the page is not among the folders with the kernel read")` | The script stops unless every folder of the records in `OTHER` is in `READ_OTHER`. |
| 1230 | `check(True, f"argument lines: like.spec, cfwd.spec and crev.spec differ in the kernel sequence only; row L-1, part L, control I and F72d12 ({len(SAME_LINE_FOLDERS)} folders) ran the line of like.spec; "` | The `check` call adds one PASS line with the counts. The rules file states that no earlier bwx12 result at 8000 MT/s holds the kernel `read`. This scan tests that statement on the header lines. |
| 1231 | `            f"header lines of the {N_CSV} csv files under R: only the {len(C_FOLDERS)} part C folders hold a part C sequence; the kernel read is in a sequence there and in {len(READ_OTHER)} folders of runner bwx only")` | Continues the text of line 1230: the number of csv files under `R`, the number of part C folders and the number of folders in `READ_OTHER`. The saved output of a build shows 903 csv files, 4 part C folders and 7 folders in `READ_OTHER` [Ref5]. |

### Rows of the runner bwx: function `bwx_header` and the settings of the processes (lines 1233 to 1286)

| Line | Source | Explanation |
|---:|---|---|
| 1233 | `# rows of runner bwx: the header lines of their processes (start option, counter setting, load at launch).` | Comment: rows of the runner bwx. The next lines read the header lines of their processes: the start option, the counter setting and the load at launch. |
| 1234 | `# Rule V2 point 4 asks the report to state how these rows differ from part C. Table 6 gives their load at launch.` | Comment: rule V2 point 4 asks the report to state how these rows differ from part C. Table 6 of the page gives their load at launch. |
| 1235 | `def bwx_header(rec):` | Starts the function `bwx_header`. It takes one record of the older runner bwx and checks the header lines of its process in the csv file. |
| 1236 | `    """Header facts of the process of a record of runner bwx, read from its csv file: the line "-- step ... tag T ... loadavg L ... utc H:M:S args ..."` | Comment: the documentation text. The header facts of the process come from its csv file. The first source is the process header line before the record, of the form `-- step ... tag T ... loadavg L ... utc H:M:S args ...`. |
| 1237 | `    before the record, and the one line "# bwx: ..." that follows it. Both must agree with the record."""` | Comment: the documentation text, continued. The second source is the one line `# bwx: ...` that follows it. Both must agree with the record. |
| 1238 | `    fl = file_lines(rec)` | `fl`: the lines of the csv file of the record. |
| 1239 | `    i = rec["line"] - 1` | `i`: the index of the I row of the record in that list. |
| 1240 | `    while i >= 0 and not fl[i].startswith("-- "):` | Goes back from the I row, line by line, as long as the line does not start with `-- `. |
| 1241 | `        i -= 1` | Moves one line back. The loop ends at the nearest line that starts with `-- `. This is the process header line. |
| 1242 | `    where = f"{rec['folder']}/{rec['file']} line {i + 1}"` | `where`: the file and the line number of that header line, for the stop messages. |
| 1243 | `    m = re.match(r"^-- step \S+ tag (\S+) binary (\S+) .* loadavg (\S+) .* utc (\d\d:\d\d:\d\d) args (.*)$", fl[i]) if i >= 0 else None` | Applies a pattern to the header line. Group 1 holds the tag, group 2 the binary, group 3 the first number after `loadavg` (the 1-minute load average), group 4 the launch time and group 5 the arguments. `m` has no value when no header line was found. |
| 1244 | `    need(m and m.group(1) == rec["tag"] and m.group(2) == "bwx" and m.group(4) == rec["launch_utc"][11:19] and D(m.group(3)) == D(rec["load1_at_launch"]),` | The script stops unless that line holds the tag of the record, the binary `bwx`, the launch time of the record and its 1-minute load average at launch. |
| 1245 | `         f"{where}: not the header line of the process of this record (tag, binary, launch time or load differs)")` | Continues the call of line 1244: the stop message. |
| 1246 | `    hl = [l for l in fl[i + 1:rec["line"]] if l.startswith("# bwx:")]` | `hl`: the lines that start with `# bwx:` between the process header line and the I row. |
| 1247 | `    h = re.search(r" start=(\w+) .*\bcount=(\d)\b", hl[0]) if len(hl) == 1 else None` | `h`: when exactly one such line exists, the pattern reads the word after `start=` (group 1) and the digit after `count=` (group 2). If not, `h` has no value. |
| 1248 | `    need(h and h.group(1) == rec["start"] and int(h.group(2)) == rec["count"] and f"--start {rec['start']}" in m.group(5),` | The script stops unless exactly one `# bwx:` line was found, its `start=` and `count=` values equal the fields `start` and `count` of the record, and the arguments of the header line hold `--start` with the same value. |
| 1249 | `         f"{where}: the start option or the counter setting of the csv header differs from the record")` | Continues the call of line 1248: the stop message. |
| 1250 | `    sq = re.search(r"--seq (\S+)", m.group(5))` | `sq`: the result of the search for the kernel sequence, the word after `--seq`, in the arguments of the header line. |
| 1251 | `    need(sq, f"{where}: no kernel sequence in the header line")` | The script stops when the arguments hold no `--seq`. |
| 1252 | `    return dict(line=i + 1, start=h.group(1), count=int(h.group(2)), seq=sq.group(1), dataset=rec["dataset"], tag=rec["tag"], launch=rec["launch_utc"], load=D(rec["load1_at_launch"]))` | Returns the line number of the header line, the start option, the counter setting and the sequence. It adds the dataset, the tag, the launch time and the load of the record. |
| 1255 | `X_HEAD = {}` | `X_HEAD`: a dictionary with one result of `bwx_header` per process of `OTHER`. It starts empty. |
| 1256 | `for r in OTHER:` | Goes through the records of `OTHER`. |
| 1257 | `    if r["proc_key"] not in X_HEAD:` | Tests whether the process of the record (`proc_key`) is new. So the call uses the first record of each process in the list. |
| 1258 | `        X_HEAD[r["proc_key"]] = bwx_header(r)` | Calls `bwx_header` for that record and keeps the result under the `proc_key`. |
| 1259 | `X_POOL_HEAD = [h for h in X_HEAD.values() if h["dataset"] in BWX_POOL]` | `X_POOL_HEAD`: the results for the processes of the datasets B7a, B7b, C3a and C3b (`BWX_POOL`, line 322). |
| 1260 | `X_REV_HEAD = [h for h in X_HEAD.values() if h["dataset"] not in BWX_POOL]` | `X_REV_HEAD`: the results for the other processes. These are the reverse-order processes. |
| 1261 | `need(len(X_POOL_HEAD) == 24 and len(X_REV_HEAD) == 4, "runner bwx: expected 24 + 4 processes with a header line")` | The script stops unless `X_POOL_HEAD` has 24 processes and `X_REV_HEAD` has 4. |
| 1262 | `need({d: sorted({h["count"] for h in X_POOL_HEAD if h["dataset"] == d}) for d in BWX_POOL} == {"B7a": [0], "B7b": [0], "C3a": [1], "C3b": [1]},` | The script stops unless the counter setting is 0 in every process of B7a and B7b, and 1 in every process of C3a and C3b. |
| 1263 | `     "runner bwx: the counter setting is not 0 in the two B7 folders and 1 in the two C3 folders")` | Continues the call of line 1262: the stop message. |
| 1264 | `need(all(X_FILES_ := [sorted({r["folder"] for r in OTHER if r["dataset"] == d}) for d in BWX_POOL]) and [f[0][:5] for f in X_FILES_] == ["R/B7-", "R/B7-", "R/C3-", "R/C3-"],` | The script stops unless each of the four datasets has records, and its first folder name starts with `R/B7-`, `R/B7-`, `R/C3-`, `R/C3-`, in this order. The operator `:=` stores the folder lists in `X_FILES_` inside the expression. |
| 1265 | `     "runner bwx: the four datasets are not two B7 folders and two C3 folders")` | Continues the call of line 1264: the stop message. |
| 1266 | `X_OFFSET = sum(1 for h in X_POOL_HEAD if h["start"] == "offset")` | `X_OFFSET`: the number of the 24 processes with the start option `offset`. |
| 1267 | `need(X_OFFSET == 12 and {h["start"] for h in X_POOL_HEAD} == {"common", "offset"} and all((h["start"] == "offset") == ("-offset-" in h["tag"]) for h in X_POOL_HEAD),` | The script stops unless `X_OFFSET` is 12, the start options of the 24 processes are `common` and `offset`, and a process has `offset` exactly when its tag contains `-offset-`. |
| 1268 | `     "runner bwx: not 12 of the 24 processes with the start option 'offset'")` | Continues the call of line 1267: the stop message. |
| 1269 | `# part C: the same two settings, from the one "# bwx:" line of each csv file and from the launch line` | Comment: part C. The next lines read the same two settings from the one `# bwx:` line of each csv file and from the launch line. |
| 1270 | `for fo in C_FOLDERS:` | Goes through the part C folders. |
| 1271 | `    r0 = [r for r in C_OLD if r["folder"] == fo][0]` | `r0`: the first `oldread` record of the folder. |
| 1272 | `    hl = [l for l in file_lines(r0) if l.startswith("# bwx:")]` | `hl`: the lines of its csv file that start with `# bwx:`. |
| 1273 | `    need(len(hl) == 1 and " start=common " in hl[0] and re.search(r"\bcount=1\b", hl[0]) and "--start common" in launch_args(fo, r0["file"][:-4]) and "--count" in launch_args(fo, r0["file"][:-4]).split(),` | The script stops unless the file has exactly one `# bwx:` line, with `start=common` and `count=1`, and the launch line of the process holds `--start common` and the word `--count`. |
| 1274 | `         f"{fo}: part C did not run with the start option 'common' and with counters")` | Continues the call of line 1273: the stop message. |
| 1275 | `need(all(r["count"] == 1 and r["start"] == "common" for r in C_OLD + C_READ + C_ASM), "part C: a record holds another start option or counter setting")` | The script stops unless every part C record of `oldread`, `read` and `asmread` has `count` 1 and `start` `common`. |
| 1276 | `# the kernel sequence of the 24 bwx processes: 8 kernels, the order of cfwd at its start and the order of crev at its end` | Comment: the kernel sequence of the 24 bwx processes. It has 8 kernels, with the order of cfwd at its start and the order of crev at its end. |
| 1277 | `X_SEQ = {h["seq"] for h in X_POOL_HEAD}` | `X_SEQ`: the different kernel sequences of the 24 processes. |
| 1278 | `need(len(X_SEQ) == 1, f"runner bwx, tags common-6000-*: not one kernel sequence: {sorted(X_SEQ)}")` | The script stops unless all 24 header lines hold the same sequence. |
| 1279 | `X_SEQ = next(iter(X_SEQ)).split(",")` | The one sequence is split at its commas. `X_SEQ` is now the list of its kernels. |
| 1280 | `need(len(X_SEQ) == 8 and ",".join(X_SEQ[:3]) == SPEC["cfwd"][2] and ",".join(X_SEQ[-3:]) == SPEC["crev"][2],` | The script stops unless the sequence has 8 kernels, its first three are the sequence of `cfwd.spec` (oldread, read, asmread) and its last three are the sequence of `crev.spec` (asmread, read, oldread). So in these rows `read` at position 1 ran directly after `oldread`, and `read` at position 6 ran directly after `asmread`. |
| 1281 | `     "runner bwx, tags common-6000-*: the sequence does not hold the order of cfwd at its start and the order of crev at its end")` | Continues the call of line 1280: the stop message. |
| 1282 | `check(True, f"rows of runner bwx: {len(X_HEAD)} header lines agree with the records (tag, launch time, load, start option, counter setting); counter setting 0 in the two B7 folders and 1 in the two C3 folders; "` | The `check` call adds one PASS line with these counts. This first part of the text gives the number of header lines that agree with the records, and the counter settings of the B7 and the C3 folders. |
| 1283 | `            f"{X_OFFSET} of {len(X_POOL_HEAD)} processes with the start option 'offset'; part C: start option 'common' and counters in 4 of 4 csv headers; "` | Continues the text of line 1282: the number of processes with the start option `offset`, and the start option and the counters of part C. |
| 1284 | `            f"sequence of {len(X_SEQ)} kernels with the order of cfwd at positions 0 to 2 and the order of crev at positions 5 to 7")` | Continues the text of line 1282: the number of kernels of the sequence, and the positions of the order of cfwd and of the order of crev. |

### X2d12 and the three boots with 10 modules: function `klog_boot` and the checks (lines 1287 to 1349)

| Line | Source | Explanation |
|---:|---|---|
| 1287 | `# rows that the rules file quotes and that are not rows of the list. Each one ran the argument line of part L once on 2026-11-17, in a boot of its own:` | Comment: rows that the rules file quotes and that are not rows of the list of 8000 MT/s rows. Each one ran the argument line of part L once on 2026-11-17, in a boot of its own. |
| 1288 | `# X2d12 (12 modules, rules V2 point 4 and F2 point 2 against rule V4) and three boots with 10 modules (rule V1 points 3 and 4). Checked here in the raw files.` | Comment: these rows are X2d12 with 12 modules, and three boots with 10 modules (X1d10, X1d10b and BASEd10). The comment names the rules that quote them: V2 point 4 and F2 point 2 against V4 for X2d12, and V1 points 3 and 4 for the boots with 10 modules. The lines up to line 1344 check the rows in the raw files and compute their rates. The page shows these rates in notes under Table 2. No wording of the page comes from them. |
| 1289 | `def klog_boot(name):` | Starts the function `klog_boot`. It reads the saved Linux kernel log `name.txt` of the folder `dimm-check-20261117`. |
| 1290 | `    """First and last time, module count and its line number of a saved kernel log of 2026-11-17."""` | Comment: the documentation text. The result holds the first and the last time, the module count and its line number of a saved Linux kernel log of 2026-11-17. |
| 1291 | `    path = f"{R}/dimm-check-20261117/{name}.txt"` | `path`: the path of the log file. |
| 1292 | `    ll = lines_of(path)` | `ll`: the lines of that file. |
| 1293 | `    a, b = re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[0]), re.match(r"^Nov 17 (\d\d:\d\d:\d\d) ", ll[-1])` | Takes the time of day of the first and of the last line. Both lines must start with `Nov 17`. Each group holds a time. |
| 1294 | `    n = [(i, int(m.group(1))) for i, l in enumerate(ll, 1) for m in [re.search(r"ghes_edac: This system has (\d+) DIMM sockets", l)] if m]` | `n`: the lines with the text `ghes_edac: This system has N DIMM sockets`, each as its line number and the number N. |
| 1295 | `    need(a and b and len(n) == 1, f"{path}: no times of 2026-11-17 in the first and last line, or no single module count line")` | The script stops unless both times are found and exactly one such line exists. |
| 1296 | `    return dict(path=path, t0=a.group(1), t1=b.group(1), modules=n[0][1], line=n[0][0], last=len(ll))` | Returns the path, the two times (`t0`, `t1`), the number N (`modules`), the number of that line (`line`) and the number of lines of the file (`last`). |
| 1299 | `EXTRA = {}` | `EXTRA`: a dictionary with the records and the boot facts of the four rows. It starts empty. |
| 1300 | `for d_, kname in (("X1d10", "k-4"), ("X1d10b", "k-3"), ("X2d12", "k-2"), ("BASEd10", "k-1")):` | The loop runs once per row, each with the name of its Linux kernel log: X1d10 (log `k-4`), X1d10b (`k-3`), X2d12 (`k-2`), BASEd10 (`k-1`). |
| 1301 | `    o_ = expect(sel(dataset=d_, kernel="oldread", pos=0), 2, 1, f"{d_}, oldread at position 0")` | `o_`: the records of the dataset with `oldread` at position 0. `expect` stops unless they are 2 intervals of 1 process with 120 threads. |
| 1302 | `    a_ = expect(sel(dataset=d_, kernel="asmread", pos=1), 2, 1, f"{d_}, asmread at position 1")` | `a_`: the records with `asmread` at position 1, with the same expected size. Other records are left out: in `facts.json` the dataset X2d12 also holds 6 records of `read_nop96`, `read_nop256` and `read_1pl` [Ref2]. |
| 1303 | `    kb = klog_boot(kname)` | `kb`: the facts of the Linux kernel log of this row, from `klog_boot`. |
| 1304 | `    fo = o_[0]["folder"]` | `fo`: the result folder of the first `oldread` record. |
| 1305 | `    ll_ = lines_of(fo.replace("R/", R + "/", 1) + "/launches.txt")` | `ll_`: the lines of the file `launches.txt` of that folder. |
| 1306 | `    m1, m2 = re.match(rf"^launch {LINE_L} utc (\S+) load (\S+) ", ll_[0]), re.match(rf"^rc 0 {LINE_L} utc (\S+)$", ll_[1])` | The first two lines of `launches.txt` must be the `launch` line and the `rc 0` line of the process `LINE_L`. The first pattern keeps the launch time and the load. The second keeps the end time. |
| 1307 | `    need(m1 and m2, f"{d_}: launch or 'rc 0' line of the part L line not found in lines 1 and 2 of launches.txt")` | The script stops unless both lines match. |
| 1308 | `    need(all(r["folder"] == fo and r["file"] == LINE_L + ".csv" and r["binary"] == "bwx12" and r["speed_MTps"] == 8000 and r["stop"] == "common" and r["min_ms"] == 6000` | More hard assertions, on every record of the two groups. A record must name the folder `fo` and the file `LINE_L` plus `.csv`. It must be a bwx12 record at 8000 MT/s with the common stop and 6000 ms intervals. |
| 1309 | `             and r["modules"] == kb["modules"] and r["launch_utc"] == f"2026-11-17T{m1.group(1)}Z" and D(r["load1_at_launch"]) == D(m1.group(2)) for r in o_ + a_)` | Continues line 1308: the module count of the record must be the count of the Linux kernel log. Its launch time and its load must be those of the `launch` line. |
| 1310 | `         and {r["proc_key"] for r in o_} == {r["proc_key"] for r in a_} and {r["kernel_before"] for r in a_} == {"oldread"},` | Continues line 1308: both groups must come from one process, and each `asmread` interval must follow `oldread` directly. |
| 1311 | `         f"{d_}: a record is not a 6 s common-stop interval of bwx12 at 8000 MT/s with the module count of the kernel log, or its launch differs from launches.txt")` | Continues the call of line 1308: the stop message. |
| 1312 | `    need(launch_args(fo, LINE_L) == SPEC["like"][1], f"{d_}: the process did not run the argument line of part L")` | The script stops unless the launch line holds exactly the arguments of `like.spec`. |
| 1313 | `    need(kb["t0"] < m1.group(1) < m2.group(1) < kb["t1"] and BOOT8_TO[11:19] < kb["t0"] and BOOT8_TO[:10] == "2026-11-17",` | The script stops unless the launch and the end of the process lie between the first and the last line of the Linux kernel log. The log must also start after `BOOT8_TO` (line 937), the time of the last line of the saved Linux kernel log of the 8000 MT/s boot, and `BOOT8_TO` must be a time of 2026-11-17. |
| 1314 | `         f"{d_}: the process does not lie inside the kernel log {kname}.txt, or that boot does not start after the end of the 8000 MT/s boot of the list rows")` | Continues the call of line 1313: the stop message. |
| 1315 | `    bs_ = {r["boot"] for r in o_ + a_}` | `bs_`: the different boots that the records of the row name. |
| 1316 | `    need(len(bs_) == 1, f"{d_}: the records name more than one boot")` | The script stops unless the records of a row name one boot. |
| 1317 | `    EXTRA[d_] = dict(old=o_, asm=a_, klog=kb, folder=fo, launch=m1.group(1), end=m2.group(1), load=D(m1.group(2)), boot=bs_.pop())` | `EXTRA` keeps both groups, the log facts, the folder, the launch time, the end time, the load and the boot under the name of the row. |
| 1318 | `need(len({v["boot"] for v in EXTRA.values()} \| {r["boot"] for r in EIGHT}) == 5, "X2d12 and the 10-module rows: not four boots of their own")` | The script stops unless the four boots and the boot of the used 8000 MT/s records (`EIGHT`, line 310) are 5 different boots. |
| 1319 | `need(all(EXTRA[a]["klog"]["t1"] < EXTRA[b]["klog"]["t0"] for a, b in (("X1d10", "X1d10b"), ("X1d10b", "X2d12"), ("X2d12", "BASEd10"))), "X2d12 and the 10-module rows: the four kernel logs overlap in time")` | The script stops unless the four Linux kernel logs do not overlap in time. Their order is X1d10, X1d10b, X2d12, BASEd10. |
| 1320 | `need([EXTRA[d_]["klog"]["modules"] for d_ in ("X1d10", "X1d10b", "X2d12", "BASEd10")] == [10, 10, 12, 10], "X2d12 and the 10-module rows: module counts of the kernel logs")` | The script stops unless the module counts of the four logs are 10, 10, 12 and 10. |
| 1321 | `# firmware settings on record at the start of each of these boots (times of the files set.txt, all of 2026-11-17)` | Comment: the firmware settings on record at the start of each of these boots. They follow from the times of the files `set.txt`, which are all of 2026-11-17. |
| 1322 | `need(X1_T < EXTRA["X1d10"]["klog"]["t0"] and EXTRA["X1d10b"]["klog"]["t0"] < X2_T, "X1d10, X1d10b: the boots did not start between the TXREQ Min change and the TXREQ Max change")` | The script stops unless the log of X1d10 starts after the change of TXREQ Min (`X1_T`) and the log of X1d10b starts before the change of TXREQ Max (`X2_T`). With the order of line 1319, both boots started between the two changes. `X1_T`, `X2_T` and `RV_T` are the times in the first line of the three files `set.txt` of the TXREQ changes (lines 1064 to 1066). |
| 1323 | `need(X2_T < EXTRA["X2d12"]["klog"]["t0"] and EXTRA["X2d12"]["end"] < RV_T, "X2d12: the boot did not start after both TXREQ changes, or the process did not end before the revert")` | The script stops unless X2d12 started after both changes, and its process ended before both settings were changed to their original values again (`RV_T`). |
| 1324 | `need(RV_T < EXTRA["BASEd10"]["klog"]["t0"], "BASEd10: the boot did not start after the revert of the TXREQ settings")` | The script stops unless BASEd10 started after that. |
| 1325 | `need(all(v["klog"]["t1"] < D72_T for v in EXTRA.values()), "X2d12 or a 10-module boot did not end before the change of DIMM Frequency to 7200 MT/s was written")` | The script stops unless all four logs end before `D72_T` (line 1092), the file time of the settings file that changes DIMM Frequency to 7200 MT/s. Only the times of day are compared, not the dates. By `facts.json` the date of this file time is 2026-11-17 [Ref2]. |
| 1326 | `rX2_old, rX2_asm = Rg(EXTRA["X2d12"]["old"]), Rg(EXTRA["X2d12"]["asm"])` | `rX2_old`, `rX2_asm`: the ranges of the 2 `oldread` intervals and of the 2 `asmread` intervals of X2d12. Lines 1326 to 1330 compute rates of the four rows. The rows hold 16 records, and 14 of them get a rate. No line of the script computes a rate for the 2 `asmread` records of BASEd10. Each `Rg` call computes the rate of its records with `val` (line 176). The script does not compare these 14 rates with the rate that the I row prints: the test of lines 341 to 345 covers only `USED` and `OTHER`. In the files `a6456.csv` of the result folders of X1d10, X1d10b, X2d12 and BASEd10, each of the 14 sums, rounded to 0.01 GB/s, equals the printed rate or lies 0.01 GB/s above it. |
| 1327 | `T10_ASM = [Rg(EXTRA[d_]["asm"]) for d_ in ("X1d10", "X1d10b")]` | `T10_ASM`: the `asmread` ranges of X1d10 and of X1d10b, 2 intervals each. The median of 2 values is their mean. Rule V1 point 3 quotes these two boots as two boots at equal settings. BASEd10 is not in `T10_ASM`. It started after the revert (line 1324), so its recorded firmware settings differ from those of the two boots. |
| 1328 | `T10_APART = (max(g.med for g in T10_ASM) / min(g.med for g in T10_ASM) - 1) * 100       # percent of the lower median` | `T10_APART`: the higher of these two medians divided by the lower one, minus 1, times 100. It is the distance of the two medians in percent of the lower median. By the facts sheet the two boots gave 260.37 / 262.67 and 285.57 / 286.45 GB/s, 9.4 % apart [Ref1]. So the two medians are 261.52 and 286.01 GB/s. |
| 1329 | `rT10_old = Rg([r for d_ in ("X1d10", "X1d10b", "BASEd10") for r in EXTRA[d_]["old"]])` | `rT10_old`: the range of the `oldread` intervals of the three boots with 10 modules. As in every `Rg` call of lines 1326 to 1329, `val` gives each rate: the sum of `bytes / elapsed_s / 1e9` over the 120 T rows after the I row. `val` stops the script unless this sum, rounded to 0.001 GB/s, equals the field `GBps` of the record. |
| 1330 | `need(rT10_old.n == 6 and rT10_old.np == 3, "10-module boots, old read: not 6 intervals of 3 processes")` | The script stops unless this range has 6 intervals of 3 processes. |
| 1331 | `g0 = len(CHECKS)` | `g0`: the length of the self-check list before the cross-checks of these values with `FACTS.md`. |
| 1332 | `xc_range("X2d12, old read kernel", rX2_old.lo, rX2_old.hi, facts_row("4.2", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])` | The `oldread` range of X2d12 against the cell `Min to max, GB/s` of the X2d12 row in section 4.2, each end to 0.01 GB/s. A missing X2d12 row stops the script in `facts_row`. |
| 1333 | `xc_range("X2d12, asmread", rX2_asm.lo, rX2_asm.hi, facts_row("4.4", lambda r: r["Row"].startswith("X2d12") and "Min to max, GB/s" in r, "X2d12")["Min to max, GB/s"])` | The same for the `asmread` range of X2d12 and the X2d12 row in section 4.4. |
| 1334 | `m_ = re.search(rf"gave asmread ({NUM}) / ({NUM}) and ({NUM}) / ({NUM}) GB/s, ({NUM}) % apart", SEC["4.6"])` | Searches section 4.6 for a sentence of the form `gave asmread a / b and c / d GB/s, e % apart`. The five groups hold the five numbers. |
| 1335 | `check(bool(m_) and all(near(q(v), m_.group(i + 1), "0.01") for i, v in enumerate(T10_ASM[0].v + T10_ASM[1].v)) and near(q(T10_APART, "0.1"), m_.group(5), "0.1"),` | The four `asmread` values (rounded to 0.01 GB/s) and `T10_APART` (rounded to 0.1 %) are compared with that sentence. A sentence that is missing in section 4.6 gives a FAIL line. |
| 1336 | `      f"10-module boots, asmread: computed {' / '.join(f2(v) for v in T10_ASM[0].v)} and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s, {f1(T10_APART)} % apart, "` | Continues the call of line 1335: the first part of the text of the check, with the computed values. |
| 1337 | `      + (f"FACTS.md {m_.group(1)} / {m_.group(2)} and {m_.group(3)} / {m_.group(4)} GB/s, {m_.group(5)} % apart" if m_ else "sentence not found in FACTS.md section 4.6"))` | Continues the text of line 1336: the values of `FACTS.md`, or the note that the sentence was not found. |
| 1338 | `m_ = re.search(rf"three 10-module boots gave old read ({NUM}) to ({NUM}) GB/s \(({NUM}) % wide, {rT10_old.n} intervals / {rT10_old.np} processes / 3 boots\)", SEC["4.6"])` | Searches section 4.6 for the sentence on the old read range of the three 10-module boots, with the same n. The three groups hold the two ends of the range and its width in percent. |
| 1339 | `check(bool(m_) and near(q(rT10_old.lo), m_.group(1), "0.01") and near(q(rT10_old.hi), m_.group(2), "0.01") and near(q(width_pct(rT10_old), "0.1"), m_.group(3), "0.1"),` | Both ends (0.01 GB/s) and the width in percent of the lower end (`width_pct`, rounded to 0.1 %) are compared. A sentence that is missing in section 4.6 gives a FAIL line. |
| 1340 | `      f"10-module boots, old read: computed {rT10_old.txt()} GB/s, {f1(width_pct(rT10_old))} % wide, "` | Continues the call of line 1339: the first part of the text of the check, with the computed values. |
| 1341 | `      + (f"FACTS.md {m_.group(1)} to {m_.group(2)} GB/s, {m_.group(3)} % wide" if m_ else "sentence not found in FACTS.md section 4.6"))` | Continues the text of line 1340: the values of `FACTS.md`, or the note that the sentence was not found. |
| 1342 | `grouped("FACTS.md sections 4.2, 4.4 and 4.6, rows quoted by the rules file and not used for a wording: X2d12 (2 ranges), 10-module boots (4 asmread values, 1 old read range, 2 percent values)", g0)` | `grouped` replaces the 4 checks of lines 1332 to 1341 by one line of the self-check list. In each of the 4 checks, a comparison passes when the two values differ by at most one rounding step, 0.01 GB/s or 0.1 % (`near`, line 616). |
| 1343 | `check(True, f"X2d12 and the three 10-module boots: each process ran the argument line of part L inside its own saved kernel log (k-4, k-3, k-2, k-1: {', '.join(str(EXTRA[d_]['klog']['modules']) for d_ in ('X1d10', 'X1d10b', 'X2d12', 'BASEd10'))} modules); "` | The `check` call adds one PASS line that sums up lines 1299 to 1325. This first part of the text says that each process ran the argument line of part L inside its own saved Linux kernel log, and gives the module counts of the four logs. |
| 1344 | `            f"settings on record at the start of the boots: TXREQ Min changed (2 boots with 10 modules), TXREQ Min and TXREQ Max changed (X2d12), both set back (third boot with 10 modules)")` | Continues the text of line 1343: the firmware settings on record at the start of the boots. |
| 1345 | `# the two decisions of the facts sheet that this page follows were made after the numbers were seen (decisions (k) and (r) of its section 2)` | Comment: the two decisions of the facts sheet that this page follows were made after the numbers were seen. They are the decisions (k) and (r) of its section 2. |
| 1346 | `m_ = re.search(r"Decisions made while this sheet was built, after the numbers were seen:\n(.*?)\n## ", FMD, re.S)` | Searches `FACTS.md` for the list with the title `Decisions made while this sheet was built, after the numbers were seen:`. The group holds the text from that title to the next heading of level 2. `re.S` lets the pattern run across line ends. |
| 1347 | `need(m_ and re.search(r"^- \(k\) Range of the 8000 MT/s side", m_.group(1), re.M) and re.search(r"^- \(r\) Part C against 8000 MT/s", m_.group(1), re.M),` | The script stops unless this list has an item that starts with `- (k) Range of the 8000 MT/s side` and an item that starts with `- (r) Part C against 8000 MT/s`. The page follows both decisions. Decision (k) takes the pool of the rows L-1 to L-4 as the 8000 MT/s range for parts L and C. Decision (r) gives a comparison with 8000 MT/s rows for two rows of part C (`oldread`, and `asmread` directly after `oldread`), although rule F2 says to show part C at 7200 MT/s only [Ref1]. |
| 1348 | `     "FACTS.md section 2: decisions (k) and (r) are not listed under the decisions made after the numbers were seen")` | Continues the call of line 1347: the stop message. |

### The one-thread phase of 2026-11-13, rule F1 point 5, and the earlier report (lines 1350 to 1387)

| Line | Source | Explanation |
|---:|---|---|
| 1350 | `# the one-thread phase of the test of 2026-11-13 (rule F1 point 5): header lines of one-thread.csv, in the folder of row A-1` | Comment: the one-thread phase of the test of 2026-11-13 (rule F1 point 5). The next lines read the header lines of the file `one-thread.csv`, in the folder of row A-1. |
| 1351 | `ONE = R + "/kernels-20261113T181222Z/one-thread.csv"` | `ONE`: the path of `one-thread.csv` in the result folder of row A-1. |
| 1352 | `need(B_A_OLD["A-1"][0]["folder"] == "R/kernels-20261113T181222Z", "row A-1 is not in the folder of the one-thread file")` | The script stops when row A-1 is in another folder than this file. |
| 1353 | `one_h = [l for l in lines_of(ONE) if l.startswith("-- ")]` | `one_h`: the process header lines of the file, the lines that start with `-- `. |
| 1354 | `one_t = [re.search(r" utc (\d\d:\d\d:\d\d)$", l) for l in one_h]` | `one_t`: for each header line, the result of the search for the launch time at the end of the line: the word `utc` and a time. The group holds the time. |
| 1355 | `need(one_h and all(one_t) and all(" threads 1 " in l for l in one_h), "one-thread.csv: a header line is not a one-thread process with a launch time")` | The script stops unless the file has header lines, every header line has a launch time, and every header line holds the text ` threads 1 `. |
| 1356 | `ONE_N, ONE_FIRST, ONE_LAST = len(one_h), one_t[0].group(1), one_t[-1].group(1)` | `ONE_N`: the number of these processes. `ONE_FIRST`, `ONE_LAST`: the first and the last launch time. |
| 1357 | `need([m.group(1) for m in one_t] == sorted(m.group(1) for m in one_t) and 0 <= secs(A1_FIRST) - secs(ONE_LAST) <= 1,` | The script stops unless two things hold. No launch time is earlier than the one before it. The first 120-thread process of row A-1 (`A1_FIRST`, line 991) started 0 s to 1 s after the last one-thread launch. |
| 1358 | `     "one-thread.csv: the launch times are not in order, or the 120-thread part did not start within 1 s of the last one-thread launch")` | Continues the call of line 1357: the stop message. |
| 1359 | `check(True, f"one-thread phase of 2026-11-13: {ONE_N} one-thread processes launched {ONE_FIRST} to {ONE_LAST}; first 120-thread process of row A-1 launched {A1_FIRST}")` | Adds a PASS line with these values. The saved output of a build shows 192 one-thread processes from 18:12:23 to 18:17:20 and the first 120-thread launch at 18:17:21 [Ref5]. |
| 1360 | `# rule F1 point 5, third sentence: the old read kernel of rows A-1 and A-2 after one-thread work and directly after 120-thread work.` | Comment: rule F1 point 5, third sentence. It needs the rate of the old read kernel of the rows A-1 and A-2 after one-thread work and directly after 120-thread work. |
| 1361 | `# In both csv files the round-1 process of bw_old read is the first process, and the round-2 process is the last one.` | Comment: in both csv files the round-1 process of `bw_old read` is the first process, and the round-2 process is the last one. The next lines assert this. |
| 1362 | `rA12_old = Rg(expect(B_A_OLD["A-1"] + B_A_OLD["A-2"], 12, 4, "rows A-1 and A-2, bw_old read"))` | `rA12_old`: the range of the `bw_old read` records of the rows A-1 and A-2. `expect` stops unless they are 12 intervals of 4 processes. The rates are the `GBps` fields of these part A records. |
| 1363 | `A12_GAP = []                                               # seconds from the launch of the process before the round-2 process to the launch of the round-2 process` | `A12_GAP`: a list that starts empty. By the comment it gets, per row, the seconds from the launch of the process before the round-2 process to the launch of the round-2 process. |
| 1364 | `for d_, heads_ in (("A-1", HA1), ("A-2", HA2)):` | The loop tests the order of the processes in the csv files of the rows A-1 and A-2. `HA1` and `HA2` hold the process header lines of the two csv files (line 990). |
| 1365 | `    need(sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 1}) == [1] and sorted({r["_fproc"] for r in B_A_OLD[d_] if r["round"] == 2}) == [len(heads_)],` | The script stops unless the round-1 process of `bw_old read` is process 1 of the file and the round-2 process is the last process of the file. `_fproc` is the number of the process of a record inside its csv file (line 349). |
| 1366 | `         f"{d_}: bw_old read is not the first process (round 1) and the last process (round 2) of the csv file")` | Continues the call of line 1365: the stop message. |
| 1367 | `    need(" binary bw_new " in heads_[-2][2] and re.search(r"kernel read\b", heads_[-2][2]) and "threads 120 " in heads_[-2][2],` | The script stops unless the process before the last one is a 120-thread process of `bw_new` with the kernel `read`. The test reads the text of its header line. |
| 1368 | `         f"{d_}: the process before the last process of the csv file is not a 120-thread process of bw_new read")` | Continues the call of line 1367: the stop message. |
| 1369 | `    A12_GAP.append(secs(heads_[-1][1]) - secs(heads_[-2][1]))` | `A12_GAP` gets the seconds between the launches of these last two processes. |
| 1370 | `need(all(0 < x <= 5 for x in A12_GAP), f"rows A-1 and A-2: the round-2 process of bw_old read did not start within 5 s of the launch of the process before it: {A12_GAP}")` | The script stops unless each gap is above 0 s and at most 5 s. The saved output shows 2 s and 3 s [Ref5]. |
| 1371 | `# row A-2 started after one-thread work too: the run that ended before it (its own result folder) holds one-thread processes only` | Comment: row A-2 started after one-thread work too. The run that ended before it has its own result folder and holds one-thread processes only. |
| 1372 | `ONE2 = R + "/partA-20261113T204939Z"` | `ONE2`: the result folder of the run before row A-2. |
| 1373 | `one2_h = [l for f_ in ("A5.csv", "A6.csv") for l in lines_of(f"{ONE2}/{f_}") if l.startswith("-- ")]` | `one2_h`: the process header lines of the files `A5.csv` and `A6.csv` of that folder. |
| 1374 | `one2_end = [m.group(1) for m in (re.match(r"^## end utc=2026-11-13T(\d\d:\d\d:\d\d)Z", l) for l in lines_of(ONE2 + "/env.txt")) if m]` | `one2_end`: the end times of that run. The pattern takes the time of each line of `env.txt` that starts with `## end utc=2026-11-13T`. |
| 1375 | `need(one2_h and all(" --threads 1 " in l for l in one2_h) and len([l for l in lines_of(ONE2 + "/launches.txt") if l.startswith("== ")]) == len(one2_h)` | The script stops unless all of these hold. The two files have header lines, and every header line holds the text ` --threads 1 `. The file `launches.txt` of the folder has as many lines that start with `== ` as there are header lines. |
| 1376 | `     and sorted(f_ for f_ in os.listdir(ONE2) if f_.endswith(".csv")) == ["A5.csv", "A6.csv"] and len(one2_end) == 1 and 0 < secs(A2_FIRST) - secs(one2_end[0]) <= 10,` | Continues line 1375: `A5.csv` and `A6.csv` are the only csv files of the folder. `env.txt` holds exactly one such end line, and the first launch of row A-2 (`A2_FIRST`, line 991) is more than 0 s and at most 10 s after that time. |
| 1377 | `     "row A-2: the run before it does not hold one-thread processes only, or it did not end within 10 s before the first launch of row A-2")` | Continues the call of line 1375: the stop message. |
| 1378 | `xc_text_range("rule F1 point 5: old read kernel of rows A-1 and A-2", "1.5", rA12_old.lo, rA12_old.hi, "", "0.01", f2)` | `xc_text_range` (line 640) adds a check: the range of `rA12_old`, rounded to 0.01 GB/s, must be present in section 1.5 of `FACTS.md` in the form `low to high`. |
| 1379 | `check(True, f"rule F1 point 5: bw_old read of rows A-1 and A-2 gave {rA12_old.txt()} GB/s ({n8000(rA12_old.recs)}). In both csv files round 1 is the first process and round 2 is the last one, "` | The last `check` of this block adds a PASS line with the range, n and the gaps. The saved output shows 464.42 to 467.06 GB/s from 12 intervals of 4 processes [Ref5]. |
| 1380 | `            f"launched {A12_GAP[0]} s and {A12_GAP[1]} s after a 120-thread process of bw_new read. Row A-1 started within 1 s of the last launch of its one-thread phase. "` | Continues the text of line 1379: the two gaps of `A12_GAP`, and the sentence that row A-1 started within 1 s of the last launch of its one-thread phase. |
| 1381 | `            f"Row A-2 started {secs(A2_FIRST) - secs(one2_end[0])} s after the end of a run of {len(one2_h)} one-thread processes")` | Continues the text of line 1379: the seconds from the end of the run in `ONE2` to the first launch of row A-2, and the number of one-thread processes of that run. |
| 1383 | `# the earlier report does not establish the cause of the lower rate of the load-only loop` | Comment: the earlier report does not establish the cause of the lower rate of the load-only loop. The next lines check that the report says so. |
| 1384 | `need(os.path.exists(EARLIER), f"the earlier report does not exist: {EARLIER}")` | The script stops when the earlier report (`EARLIER`, line 32) does not exist. |
| 1385 | `with open(EARLIER, encoding="utf-8") as f_:` | Opens the earlier report as UTF-8 text. |
| 1386 | `    need("the rule inside the core that causes this is not established" in f_.read(), "the earlier report: the sentence 'not established' of its Short version was not found")` | The script stops unless its text holds the words `the rule inside the core that causes this is not established`. The reference list of the page says that the Short version of that report holds this statement (line 1455). The raw-file checks that started at line 811 end here. |

### Reference list of the page: scripts, logs and the csv files of the runs (lines 1388 to 1438)

| Line | Source | Explanation |
|---:|---|---|
| 1388 | `# ------------------------------------------------------------------ references` | Comment: a section title. The reference list of the page follows. `addref` (line 815) adds one entry to `REFS`: a key, the path in short form and a note. It stops the script when the path does not exist. All `addref` calls of the file are in lines 1389 to 1474. |
| 1389 | `addref("facts", S + "/FACTS.md", "the detailed record of this rerun (facts sheet): every interval, every check, every decision")` | Reference `facts`: the file `FACTS.md`, the facts sheet. The note calls it the detailed record of the rerun. |
| 1390 | `addref("json", S + "/facts.json", "every interval as one record, built from the raw files. Data source of this page")` | Reference `json`: the file `facts.json`. The note says that it holds every interval as one record and that it is the data source of the page. |
| 1391 | `addref("rules", S + "/baselines-and-rules.txt", "the list of 8000 MT/s rows and the comparison rules V1 to V4, F1, F2, written before the run")` | Reference `rules`: the rules file `baselines-and-rules.txt`. The note says that the list of 8000 MT/s rows and the comparison rules were written before the run. |
| 1392 | `addref("gen", S + "/make_report.py", "script: generator of this page. It computes every rate from the records of facts.json and prints the self-check list. "` | Reference `gen`: this script, as the generator of the page. Its note starts here: the script computes every rate from the records of `facts.json` and prints the self-check list. |
| 1393 | `       "The records hold each rate of bwx12 and bwx rounded to 0.001 GB/s. Rounding such a value again to 0.01 GB/s can change the last digit. "` | Continues the note of line 1392. It gives the reason for the sum in `val`: the records hold each rate of bwx12 and bwx rounded to 0.001 GB/s. A second rounding to 0.01 GB/s can change the last digit. |
| 1394 | `       "So the script sums the 120 thread rows that the record names and rounds the sum once. "` | Continues the note of line 1392: so the script sums the 120 thread rows that the record names and rounds the sum once. |
| 1395 | `       "It reads the machine-state facts of section 4 from the raw files")` | Ends the note of line 1392: the script reads the machine-state facts of section 4 of the page from the raw files. |
| 1396 | `addref("build", S + "/build_facts.py", "script: builds FACTS.md and facts.json from the raw files")` | Reference `build`: the script `build_facts.py`, which builds `FACTS.md` and `facts.json` from the raw files. |
| 1397 | `addref("go", S + "/go.sh", "script: driver of the rerun. Three sessions of parts A, L, C and a fourth part C process")` | Reference `go`: the script `go.sh`, the driver of the rerun. |
| 1398 | `addref("ra", S + "/ra.sh", "script: part A, the 120-thread part of the test of 2026-11-13 with the same two binaries")` | Reference `ra`: the script `ra.sh`, which runs part A. |
| 1399 | `addref("go2", S + "/go2.sh", "script: control I (added after the first numbers were seen), the part L line twice from an idle machine", "lines 2 and 24 to 33")` | Reference `go2`: the script `go2.sh`, the driver of control I. The last argument cites lines of that script. These line numbers are fixed text of this file. They are not computed. |
| 1400 | `addref("like", S + "/like.spec", "argument line of part L")` | Reference `like`: the spec file `like.spec`, the argument line of part L. |
| 1401 | `addref("cfwd", S + "/cfwd.spec", "argument line of part C, order oldread, read, asmread")` | Reference `cfwd`: the spec file `cfwd.spec`, the argument line of part C in the order oldread, read, asmread. |
| 1402 | `addref("crev", S + "/crev.spec", "argument line of part C, order asmread, read, oldread")` | Reference `crev`: the spec file `crev.spec`, the argument line of part C in the order asmread, read, oldread. |
| 1403 | `addref("golog", GOLOG, "log of go.sh: 12 state lines, 10 'done' lines, ALLDONE")` | Reference `golog`: the run log of `go.sh`. The note gives fixed counts: 12 state lines, 10 `done` lines and `ALLDONE`. Line 863 and line 875 assert these counts. |
| 1404 | `addref("go2log", GO2LOG, "log of go2.sh (control I, added after the first numbers were seen): 6 state lines, ALLDONE")` | Reference `go2log`: the run log of `go2.sh`. The note gives 6 state lines and `ALLDONE` (line 863, line 876). |
| 1405 | `for s_ in (1, 2, 3):` | Goes through the sessions 1 to 3. |
| 1406 | `    addref(f"A{s_}", R + "/" + [r for r in A_OLD if r["session"] == s_][0]["folder"][2:] + "/threads120.csv", f"part A, session {s_}: interval rows")` | Reference `A1`, `A2` or `A3`: the csv file `threads120.csv` of part A of this session. The path comes from the field `folder` of the first old-kernel record of the session, without its start `R/`. No rate is computed here. |
| 1407 | `for s_ in (1, 2, 3):` | Goes through the sessions 1 to 3 again. |
| 1408 | `    addref(f"L{s_}", R + "/" + [r for r in L_OLD if r["session"] == s_][0]["folder"][2:] + "/a6456.csv", f"part L, session {s_}: interval rows")` | Reference `L1`, `L2` or `L3`: the csv file `a6456.csv` of part L of this session. The path is found in the same way. |
| 1409 | `for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):` | Goes through the four folder tags of part C. |
| 1410 | `    r0 = [r for r in C_OLD if r["tag"] == t_][0]` | `r0`: the first `oldread` record of part C with this tag. |
| 1411 | `    addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"part C, process {t_}: interval rows")` | Reference with the tag as its key: the csv file of this part C process. The folder and the file name come from the fields `folder` and `file` of the record. |
| 1412 | `for t_ in ("T72I1", "T72I2"):` | Goes through the two folder tags of control I. |
| 1413 | `    r0 = [r for r in I_OLD if r["tag"] == t_][0]` | `r0`: the first `oldread` record of control I with this tag. |
| 1414 | `    addref(t_, R + "/" + r0["folder"][2:] + "/" + r0["file"], f"control I (added after the first numbers were seen), process {t_}: interval rows")` | Reference with the tag as its key: the csv file of this process of control I. |
| 1415 | `addref("F72", R + "/w120-w120-F72d12-20261117T200231Z/a6456.csv", "F72d12 (earlier run of the same boot, not part of the rerun): interval rows")` | Reference `F72`: the csv file of F72d12. |
| 1416 | `addref("F72l", FL, "F72d12 (earlier run of the same boot, not part of the rerun): launch time, load at launch and end of the process", "lines 1 and 2")` | Reference `F72l`: the file `launches.txt` of F72d12 (`FL`, line 909), for the launch time, the load at launch and the end of the process. The cited lines, its first two, are fixed text. |
| 1417 | `addref("F72e", F_ENV, "F72d12 (earlier run of the same boot, not part of the rerun): time and process list before the launch", f"lines 1 and {F_TOP[0]}")` | Reference `F72e`: the file `env.txt` of F72d12 (`F_ENV`, line 1117), for the time and the process list before the launch. The cited lines are its first line and the line of the busiest process (`F_TOP`, line 1119). |
| 1418 | `addref("gaps", GAPS, "first and last kernel log line of the boot of the rerun, saved in that boot", "line 7")` | Reference `gaps`: the file `gaps.txt`, for the first and the last Linux kernel log line of the boot of the rerun. The cited line, its seventh, is fixed text. |
| 1419 | `for t_ in ("T72L1", "T72L2", "T72L3", "T72I1", "T72I2"):` | Goes through the 5 steps of part L and of control I. |
| 1420 | `    addref("env" + t_, VISIT_ENV[t_][0], ("part L" if "L" in t_ else "control I (added after the first numbers were seen)") + f", process {t_}: time and process list before the launch")` | Reference `env` plus the tag: the `env.txt` file of this step (`VISIT_ENV`, line 1128). The note says `part L` when the tag holds the letter `L`, else it names control I. |
| 1421 | `addref("A-1", R + "/kernels-20261113T181222Z/threads120.csv", "row A-1 (8000 MT/s): the test of 2026-11-13. Header lines with the launch times", f"first and last header: lines {HA1[0][0]} and {HA1[-1][0]}")` | Reference `A-1`: the csv file of row A-1, `threads120.csv` of the test of 2026-11-13. The cited lines are its first and its last header line, computed from `HA1` (line 990). |
| 1422 | `addref("A-2", R + "/partA-20261113T205055Z/A1.csv", "row A-2 (8000 MT/s): same binaries, other process order. Header lines with the launch times",` | Reference `A-2`: the csv file of row A-2, `A1.csv`. The note says: same binaries, other process order. |
| 1423 | `       f"headers of bw_new read round 1 and of {A2_OTHER}: lines {HA2[a2_new_r1[0]['_fproc'] - 1][0]} and {a2_other[0][0]}")` | Continues line 1422: the cited lines are the header line of `bw_new read` round 1 and the header line of the process `A2_OTHER` (line 1012). The checks above found both. |
| 1424 | `addref("A-3", R + "/partA-20261113T205055Z/A3.csv", "row A-3 (8000 MT/s): three processes of bw_old read (tags onebuf-ms500-1, -2, -3)",` | Reference `A-3`: the csv file of row A-3, `A3.csv`. The note names its three processes of `bw_old read` by their tags. |
| 1425 | `       "headers in lines " + ", ".join(str(HA3[i - 1][0]) for i in a3_used) + f", next header in line {HA3[a3_used[-1]][0]}")` | Continues line 1424: the cited lines are the header lines of the 3 processes used and the next header line after the last of them (lines 992 to 994). |
| 1426 | `addref("L-1", R + "/w120-R8-20261117T020549Z/a6456.csv", "row L-1 (8000 MT/s): the argument line of part L")` | Reference `L-1`: the csv file of row L-1, which ran the argument line of part L. |
| 1427 | `addref("L-1l", R + "/w120-R8-20261117T020549Z/launches.txt", "row L-1: launch time with the argument line, and end of the process", "lines 1 and 2")` | Reference `L-1l`: the file `launches.txt` of row L-1, for the launch time with the argument line and the end of the process. The cited lines are fixed text. |
| 1428 | `addref("L-2a", R + "/w120-R1-20261115T185140Z/p1nop.csv", "row L-2 (8000 MT/s), process p1nop")` | Reference `L-2a`: the csv file of the process `p1nop` of row L-2. |
| 1429 | `addref("L-2b", R + "/w120-R1-20261115T185140Z/p2add.csv", "row L-2 (8000 MT/s), process p2add. It holds the lowest asmread interval of the pool. "` | Reference `L-2b`: the csv file of the process `p2add` of row L-2. Its note says that this file holds the lowest `asmread` interval of the pool (`LOWEST_ASM`, line 520). |
| 1430 | `       f"Its interval row prints {f2(i_row_rate(LOWEST_ASM))} GB/s. This page uses the sum of the 120 thread rows, {f2(val(LOWEST_ASM))} GB/s",` | Continues the note of line 1429 with two rates of that interval. The two rates use different formulas. `i_row_rate` (line 158) returns the rate that its I row prints: the total bytes of the 120 threads divided by the longest elapsed time of a thread. The first line of the csv file states this formula. `val` returns the sum of its 120 T rows: it divides the bytes of each thread by the elapsed time of that thread and adds the 120 results. `f2` rounds both to 0.01 GB/s. In the file `p2add.csv` of the folder `w120-R1-20261115T185140Z` the I row prints 288.53 GB/s, and the sum is 288.540691 GB/s. So the page shows 288.54 GB/s for this interval [Ref5]. |
| 1431 | `       f"interval row in line {LOWEST_ASM['line']}, the 120 thread rows in the lines after it")` | Continues line 1429: the cited lines are the I row of that interval, with its computed line number, and the 120 thread rows after it. |
| 1432 | `addref("L-2l", R + "/w120-R1-20261115T185140Z/launches.txt", "row L-2: launch times and ends of the two processes", "lines 1 to 4")` | Reference `L-2l`: the file `launches.txt` of row L-2, for the launch times and the ends of its two processes. The cited lines are fixed text. |
| 1433 | `addref("L-3", R + "/w120-R5-20261115T203152Z/thp.csv", "row L-3 (8000 MT/s)")` | Reference `L-3`: the csv file of row L-3, `thp.csv`. |
| 1434 | `addref("L-3l", R + "/w120-R5-20261115T203152Z/launches.txt", "row L-3: launch time and end of the process thp", "lines 3 and 4")` | Reference `L-3l`: the file `launches.txt` of row L-3, for the launch time and the end of the process `thp`. The cited lines are fixed text. |
| 1435 | `addref("L-4a", R + "/w120-R6-20261115T203438Z/st1.csv", "row L-4 (8000 MT/s), process st1")` | Reference `L-4a`: the csv file of the process `st1` of row L-4. |
| 1436 | `addref("L-4b", R + "/w120-R6-20261115T203438Z/st2.csv", "row L-4 (8000 MT/s), process st2")` | Reference `L-4b`: the csv file of the process `st2` of row L-4. |
| 1437 | `addref("L-4c", R + "/w120-R6-20261115T203438Z/st3.csv", "row L-4 (8000 MT/s), process st3")` | Reference `L-4c`: the csv file of the process `st3` of row L-4. |
| 1438 | `addref("L-4l", R + "/w120-R6-20261115T203438Z/launches.txt", "row L-4: launch times and ends of the three processes", "lines 1 to 6")` | Reference `L-4l`: the file `launches.txt` of row L-4, for the launch times and the ends of its three processes. The cited lines are fixed text. |

### Reference list of the page: raw files of the machine state checks, other rows (lines 1439 to 1478)

| Line | Source | Explanation |
|---:|---|---|
| 1439 | `addref("try6", TRY6, f"record of boot 3bfc57a1: time, boot id, MemTotal, kernel log line with the module count, the line \"modules={TRY6_MODLINE}\" (not the module count), "` | Reference `try6`: the file `try6.txt`, the record of the boot of the rerun. The note names the boot by the fixed text `3bfc57a1`. It lists the content: time, boot id, MemTotal, the Linux kernel log line with the module count, and the line `modules=N` with the number of line 900, marked as not the module count. |
| 1440 | `       "12 x \"Configured Memory Speed: 7200 MT/s\"", "lines 1, 2, 4, 5, 6 and 7")` | Continues line 1439: the note ends with the count 12 of the lines `Configured Memory Speed: 7200 MT/s`. The cited lines, six of the file, are fixed text. |
| 1441 | `addref("dmi", DMI, "module list saved in boot 3bfc57a1: 12 entries \"Memory Device\", each with one line \"Configured Memory Speed: 7200 MT/s\"")` | Reference `dmi`: the module list saved in the boot of the rerun (`DMI`, line 1160). |
| 1442 | `addref("boots", BOOTS, "boot list of the journal, saved in boot 3bfc57a1: row 0 is this boot", "line 9")` | Reference `boots`: the file `boots.txt`, the boot list of the journal. The note says that row 0 is this boot. The cited line is fixed text. |
| 1443 | `addref("journal", JOURNAL, "saved journal lines of the 8000 MT/s boot (started 2026-11-09): hardware error records",` | Reference `journal`: the saved journal lines of the 8000 MT/s boot, for the hardware error records. |
| 1444 | `       "lines " + ", ".join(str(x) for x in sorted([h["line"] for v in HW_ROWS.values() for h in v["recs"]] + [h["line"] for h in HW_A])))` | Continues line 1443: the cited lines are computed. They are the journal lines of the records that the checks counted: those of `HW_ROWS` (line 957) and those of `HW_A` (line 996), sorted. `addref` writes them in parentheses after the path. |
| 1445 | `addref("klog", KLOG, "saved kernel log of the 8000 MT/s boot (started 2026-11-09): first line, memory size line, module count line, last line",` | Reference `klog`: the saved Linux kernel log of the 8000 MT/s boot. |
| 1446 | `       f"lines 1, {K12_MEM[0]}, {[i for i, l in enumerate(kl, 1) if 'This system has 12 DIMM sockets' in l][0]} and {len(kl)}")` | Continues line 1445: the cited lines are computed: the first line, the memory size line (`K12_MEM`, line 1156), the line with `12 DIMM sockets` and the last line. |
| 1447 | `addref("klog10", KLOG10, f"saved kernel log of the boot that started on {BOOT10_FROM} UTC: first line, memory size line, module count line",` | Reference `klog10`: the saved Linux kernel log `k-1.txt` (`KLOG10`, line 1141) of the boot that started at `BOOT10_FROM`. |
| 1448 | `       f"lines 1, {K10_MEM[0]} and {K10_LINE[0]}")` | Continues line 1447: the cited lines are computed: the first line, the memory size line (`K10_MEM`) and the line with `10 DIMM sockets` (`K10_LINE`). |
| 1449 | `addref("x1", FW + "/x1/set.txt", "firmware setting change: TXREQ Min", "lines 1, 8, 9 and 18")` | Reference `x1`: the file `set.txt` of the folder `x1`, the change of TXREQ Min. The cited lines are fixed text. |
| 1450 | `addref("x2", FW + "/x2/set.txt", "firmware setting change: TXREQ Max", "lines 1 and 2")` | Reference `x2`: the file `set.txt` of the folder `x2`, the change of TXREQ Max. The cited lines are fixed text. |
| 1451 | `addref("rev", FW + "/revert/set.txt", "firmware settings set back: TXREQ Max and TXREQ Min", "lines 1, 2 and 4")` | Reference `rev`: the file `set.txt` of the folder `revert`, where both settings were set back. The cited lines are fixed text. |
| 1452 | `addref("qbase", R + "/uefisettings-20261117/questions.json", "firmware settings list of the 8000 MT/s boot")` | Reference `qbase`: the firmware settings list of the 8000 MT/s boot. |
| 1453 | `addref("qrev", FW + "/revert/questions.json", "firmware settings list saved after the revert")` | Reference `qrev`: the firmware settings list that was saved after the revert. |
| 1454 | `addref("d72", R + "/dimm7200-20261117/set.txt", "firmware setting change: DIMM Frequency = 7200 MT/s", "lines 7 and 8")` | Reference `d72`: the file `set.txt` of the folder `dimm7200-20261117`, the change of DIMM Frequency to 7200 MT/s. The cited lines are fixed text. |
| 1455 | `addref("earlier", EARLIER, "the earlier report (2026-11-15) on the lower whole-chip read rate of the load-only loop. Its Short version says that the cause is not established")` | Reference `earlier`: the earlier report (`EARLIER`, line 32). The note says that its Short version states that the cause is not established. Line 1386 asserts that the report holds this statement. |
| 1456 | `addref("one", ONE, "the one-thread phase of the test of 2026-11-13: one header line with the launch time per process", f"first and last header: lines {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][0]} and {[i for i, l in enumerate(lines_of(ONE), 1) if l.startswith('-- ')][-1]}")` | Reference `one`: the file `one-thread.csv` (`ONE`, line 1351). The cited lines are its first and its last header line. This line computes the two line numbers. |
| 1457 | `addref("xX2d12", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/" + LINE_L + ".csv", "row X2d12 (8000 MT/s, 12 modules, shown and not used): interval rows of the argument line of part L")` | Reference `xX2d12`: the csv file of row X2d12. The note says that the row is shown and not used. |
| 1458 | `addref("xX2d12l", R + "/" + EXTRA["X2d12"]["folder"][2:] + "/launches.txt", "row X2d12: launch time with the argument line and the load, and end of the process", "lines 1 and 2")` | Reference `xX2d12l`: the file `launches.txt` of row X2d12. The cited lines are fixed text. |
| 1459 | `addref("klogX2d12", EXTRA["X2d12"]["klog"]["path"], "saved kernel log of the boot of row X2d12: first line, module count line, last line",` | Reference `klogX2d12`: the saved Linux kernel log of the boot of row X2d12. |
| 1460 | `       f"lines 1, {EXTRA['X2d12']['klog']['line']} and {EXTRA['X2d12']['klog']['last']}")` | Continues line 1459: the cited lines are the first line, the line with the module count and the last line, from `klog_boot` (line 1289). |
| 1461 | `for d_ in ("X1d10", "X1d10b", "BASEd10"):` | Goes through the three boots with 10 modules. |
| 1462 | `    addref("x" + d_, R + "/" + EXTRA[d_]["folder"][2:] + "/" + LINE_L + ".csv", f"boot with 10 modules at 8000 MT/s (folder tag {d_}, not a row of the list): interval rows of the argument line of part L")` | Reference `x` plus the name of the row: the csv file of that boot. The note says that the row is not a row of the list. |
| 1463 | `for d_ in ("X1d10", "X1d10b"):` | Goes through X1d10 and X1d10b. |
| 1464 | `    addref("klog" + d_, EXTRA[d_]["klog"]["path"], f"saved kernel log of the boot of the folder tag {d_}: first line, module count line, last line",` | Reference `klog` plus the name of the row: the saved Linux kernel log of that boot. |
| 1465 | `           f"lines 1, {EXTRA[d_]['klog']['line']} and {EXTRA[d_]['klog']['last']}")` | Continues line 1464: the cited lines are the first line, the line with the module count and the last line. |
| 1466 | `need(EXTRA["BASEd10"]["klog"]["path"] == KLOG10, "BASEd10: its kernel log is not the file of the reference klog10")` | The script stops unless the Linux kernel log of BASEd10 is the file `KLOG10` of line 1141. That file already has the key `klog10` (line 1447). |
| 1467 | `X_FILES = {}` | `X_FILES`: a dictionary from a dataset of the older runner bwx to its csv file. It starts empty. |
| 1468 | `for d_ in BWX_POOL + ("B5a-rev", "B5b-rev"):` | Goes through the 6 datasets: B7a, B7b, C3a, C3b, B5a-rev and B5b-rev. |
| 1469 | `    fs_ = sorted({(r["folder"], r["file"]) for r in OTHER if r["dataset"] == d_})` | `fs_`: the different pairs (folder, file) of the records of this dataset in `OTHER`. |
| 1470 | `    need(len(fs_) == 1, f"runner bwx, {d_}: more than one csv file")` | The script stops unless the dataset has exactly one csv file. |
| 1471 | `    X_FILES[d_] = fs_[0]` | Keeps that pair under the name of the dataset. |
| 1472 | `    what_ = ("rows of runner bwx (other binary, 8000 MT/s), tags common-6000-*" if d_ in BWX_POOL else` | `what_`: the start of the note. For a dataset of `BWX_POOL` it names the rows of the runner bwx with the tags `common-6000-*`. |
| 1473 | `             "rows of runner bwx (other binary, 8000 MT/s), the two processes with another kernel order (tags b5-rev-*)")` | Continues line 1472: for the two other datasets it names the two processes with another kernel order, with the tags `b5-rev-*`. |
| 1474 | `    addref("x" + d_, R + "/" + fs_[0][0][2:] + "/" + fs_[0][1], what_ + ": interval rows. This page uses the sum of the 120 thread rows after an interval row")` | Reference `x` plus the name of the dataset: its csv file. The note adds that the page uses the sum of the 120 thread rows after an interval row. This is the last `addref` call of the file. |
| 1475 | `need(len(set(X_FILES.values())) == 6, "runner bwx: the 6 datasets do not come from 6 csv files")` | The script stops unless the 6 datasets come from 6 different csv files. |
| 1476 | `need(not {X_FILES[d_][0] for d_ in ("B5a-rev", "B5b-rev")} & {X_FILES[d_][0] for d_ in BWX_POOL} and Rg(X_REV_READ).procs == Rg(X_REV_ASM).procs,` | The script stops unless the two reverse-order datasets lie in other folders than the four pool datasets. It also stops unless the `read` records and the `asmread` records of the reverse-order datasets come from the same processes (`procs` of `Rg`, line 201). |
| 1477 | `     "runner bwx: the processes with the other kernel order are not the same 4 processes of two other result folders")` | Continues the call of line 1476: the stop message. |

### Small HTML helpers: the two fixed labels `CI` and `F72` (lines 1479 to 1483)

| Line | Source | Explanation |
|---:|---|---|
| 1479 | `# ------------------------------------------------------------------ small HTML helpers` | Comment: a section title. The small helpers for HTML follow. |
| 1480 | `CI = "control I (added after the first numbers were seen)"` | `CI`: a fixed label, the text for control I. A sentence of the page that uses the label says that control I was added after the first numbers were seen. Other places of the script write the same words directly. A check near the end of the file (from line 2794) tests every paragraph, list item, caption, tooltip, word definition and table row of the page. Each one that names control I or F72d12 must hold the words of its label. |
| 1481 | `F72 = "F72d12 (earlier run of the same boot, not part of the rerun)"` | `F72`: a fixed label, the text for F72d12. A sentence of the page that uses the label says that F72d12 is an earlier run of the same boot and not part of the rerun. |

### Small HTML helpers: `strip_tags`, `P`, `UL`, `table` and `small` (lines 1484 to 1518)

| Line | Source | Explanation |
|---:|---|---|
| 1484 | `def strip_tags(s):` | Starts the function `strip_tags`. It returns the plain text of a piece of HTML. The checks of the built page use it (lines 2787 to 2803), and so does the last line of the file (line 2834). |
| 1485 | `    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r'<span class="ref">.*?</span>', " ", s)))` | Works from the inside to the outside. The inner `re.sub` replaces every reference mark by a space. Its pattern matches a `span` element of the class `ref` with its content, up to the first `</span>`. The outer `re.sub` replaces every HTML tag by a space. Its pattern `<[^>]+>` matches a `<`, then one or more characters that are not `>`, then a `>`. Neither pattern has a group. `html.unescape` then turns HTML character codes such as `&amp;` back into characters. |
| 1488 | `def P(text, cls=None):` | Starts the function `P`. It returns one HTML paragraph. With `cls` the paragraph gets that class name. |
| 1489 | `    PROSE.append(text)` | Adds the text to the list `PROSE` (line 39). `PROSE` collects the text that counts for the word limit of the page (lines 2787 to 2789). |
| 1490 | `    return f'<p{" class=" + chr(34) + cls + chr(34) if cls else ""}>{text}</p>'` | Returns the text between `<p>` and `</p>`. When `cls` is given, the opening tag gets the attribute `class` with that name in double quotes. `chr(34)` is the double quote character. |
| 1493 | `def UL(items):` | Starts the function `UL`. It returns one HTML bullet list from a list of texts. |
| 1494 | `    PROSE.extend(items)` | Adds every item to `PROSE` for the word count. |
| 1495 | `    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"` | Returns the list: `<ul>`, then one `li` element per item, then `</ul>`. |
| 1498 | `WIDE = ("q1", "q2", "state", "load", "visits", "detail")        # tables with a fixed least width of 900 px (see the style block)` | `WIDE`: the class names of the six tables that have a least width of 900 px. Comment at the end of the line: the style block sets this width. The rule is in line 2613. `table` writes a scroll hint above each of these tables (line 1502). |
| 1501 | `def table(head, rows, cls=""):` | Starts the function `table`. It returns the HTML of one table. `head` is the list of column titles, `rows` is the list of rows, and `cls` is the class name of the table. The function computes no value. |
| 1502 | `    o = ['<p class="hint ht">If the table does not fit the screen, scroll it sideways.</p>' if cls in WIDE else ""]` | `o`: the list of the HTML pieces of the table. For a table whose class is in `WIDE`, the first piece is a hint: a paragraph of the classes `hint` and `ht` that tells the reader to scroll the table sideways. The style block shows this paragraph only in a window of at most 949 px (lines 2614 to 2615). For every other table the first piece is an empty text. |
| 1503 | `    o += [f'<div class="tw"><table class="{cls}"><thead><tr>']` | Opens a `div` element of the class `tw`, then the table with the class `cls`, the table head and its row. The style block lets this `div` scroll sideways when the table is wider than the page (line 2602). |
| 1504 | `    o += [f'<th{" class=n" if c.startswith("#") else ""}>{c.lstrip("#")}</th>' for c in head]` | Adds one head cell per column title. A title that starts with `#` marks a number column: the cell gets the class `n`, and `lstrip("#")` removes the `#` from the title that is shown. The style block aligns the class `n` to the right (line 2606). |
| 1505 | `    o.append("</tr></thead><tbody>")` | Closes the head row and the table head, and opens the table body. |
| 1506 | `    for r in rows:` | Starts the loop over the rows. |
| 1507 | `        if isinstance(r, str):` | Tests whether the row is one text and not a list of cells. |
| 1508 | `            o.append(f'<tr class="grp"><td colspan="{len(head)}">{r}</td></tr>')` | A row that is a text becomes one title row: a row of the class `grp` with a single cell that spans all columns. `colspan` gets the number of column titles. |
| 1509 | `            continue` | Goes on with the next row. |
| 1510 | `        o.append("<tr>" + "".join(f'<td{" class=n" if head[i].startswith("#") else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>")` | Any other row is a list of cells. The line writes one `td` cell per entry, between `<tr>` and `</tr>`. A cell of a number column (title with `#`) gets the class `n`. |
| 1511 | `    o.append("</tbody></table></div>")` | Closes the table body, the table and the `div`. |
| 1512 | `    return "".join(o)` | Joins the pieces and returns them as one text. |
| 1515 | `def small(s):` | Starts the function `small`. It puts a text into small type. |
| 1516 | `    return f'<span class="sm">{s}</span>'` | Returns the text inside a `span` element of the class `sm`. The style block gives this class a size of 12.5 px and a grey colour (line 2639). |

### Helpers of figure 1: `T`, `marker`, `kernel_name`, `dot_title`, `f1_row`, `bwx_row` (lines 1519 to 1560)

| Line | Source | Explanation |
|---:|---|---|
| 1519 | `# ------------------------------------------------------------------ figure 1: dumbbell` | Comment: a section mark. The code of figure 1 starts here. Figure 1 is a dumbbell chart: a chart with two dots per row and a line between them. |
| 1520 | `def T(x, y, s, size=12, fill=INK, anchor="start", weight=None, extra=""):` | Starts the function `T`. It returns one SVG `text` element. `x` and `y` give the place and `s` the text. `size` is the font size (12 px unless given), `fill` the colour (the text colour `INK` unless given), `anchor` the alignment, `weight` the font weight, and `extra` more attribute text. |
| 1521 | `    w = f' font-weight="{weight}"' if weight else ""` | `w`: the attribute `font-weight` when `weight` is given. If not, an empty text. |
| 1522 | `    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(s)}</text>'` | Returns the element. `x` and `y` are written with 1 decimal. `text-anchor` says which point of the text lies at `x`: its start, its middle or its end. `esc` (line 108) escapes the HTML special characters of the text. |
| 1525 | `HALO = f' paint-order="stroke" stroke="{SURF}" stroke-width="3.5" stroke-linejoin="round"'` | `HALO`: attribute text for `T`. It draws the outline of each letter with a stroke of 3.5 px in the background colour `SURF`. `paint-order="stroke"` paints this stroke first and the letter over it. So a line behind a text does not cross the letters. |
| 1526 | `TAB = ' style="font-variant-numeric:tabular-nums"'` | `TAB`: attribute text for `T`. It asks for digits of equal width (`tabular-nums`). |
| 1529 | `def marker(x, y, color, hollow, r=5.5):` | Starts the function `marker`. It returns the SVG of one dot of figure 1 at the place `x`, `y`. `color` is the colour of the kernel: `fig1` passes blue for the old read kernel and orange for the load-only loop (line 1669). `r` is the radius, 5.5 px unless given. |
| 1530 | `    """A hollow marker (8000 MT/s) carries its colour in the stroke. The hover style must not replace that stroke (classes ho and fi)."""` | Comment: the documentation text. A hollow marker stands for 8000 MT/s. It carries its colour in its outline (the SVG attribute `stroke`). The style for a dot under the pointer must not replace that outline. The classes `ho` and `fi` tell the style block which kind of dot it is (lines 2656 to 2657). |
| 1531 | `    if hollow:` | Tests whether the dot is hollow (a row at 8000 MT/s). |
| 1532 | `        return f'<circle class="mk ho" cx="{x:.1f}" cy="{y:.1f}" r="{r - 0.9:.1f}" fill="{SURF}" stroke="{color}" stroke-width="2.2"/>'` | A hollow dot: one circle of the classes `mk` and `ho` with the radius `r - 0.9` (4.6 px), the background colour inside, and an outline of 2.2 px in the kernel colour. |
| 1533 | `    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 1.6:.1f}" fill="{SURF}"/>'` | A filled dot (a row at 7200 MT/s), first piece: a circle in the background colour with the radius `r + 1.6` (7.1 px). It is drawn first, so it lies under the dot. |
| 1534 | `            f'<circle class="mk fi" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color}"/>')` | Second piece: the dot itself, a circle of the classes `mk` and `fi` with the radius `r` in the kernel colour. |
| 1537 | `def kernel_name(recs):` | Starts the function `kernel_name`. It returns the display name of the kernel of a list of records. It uses the first record only. |
| 1538 | `    r = recs[0]` | `r`: the first record of the list. |
| 1539 | `    if r["part"] == "A":` | Tests whether it is a part A record. |
| 1540 | `        return f"{r['binary']} read ({'old' if r['binary'] == 'bw_old' else 'new'} read kernel)"` | Part A: returns `bw_old read (old read kernel)` or `bw_new read (new read kernel)`, by the field `binary`. |
| 1541 | `    return {"oldread": "oldread (old read kernel)", "read": "read (new read kernel)",` | Every other record is a bwx record. The line returns the text for its field `kernel`: `oldread` gives `oldread (old read kernel)`, and `read` gives `read (new read kernel)`. |
| 1542 | `            "asmread": "asmread (in place of the new read kernel)"}[r["kernel"]]` | Continues the dictionary of line 1541: `asmread` gives `asmread (in place of the new read kernel)`. Any other kernel name ends the script with a Python error (`KeyError`). |
| 1545 | `def dot_title(name, rg):` | Starts the function `dot_title`. It returns the tooltip text of one dot of figure 1. `name` is the row name with its notes. `rg` is the `Rg` object (line 192) of one kernel of the row. |
| 1546 | `    vals = ", ".join(f2(v) for v in rg.v)` | `vals`: every interval rate of this kernel in the row, each rounded to 0.01 GB/s by `f2` (line 94), joined with commas. The values stand in the order of `rg.v`: by launch time, then by interval number (line 197). |
| 1547 | `    return (f"{name}: {kernel_name(rg.recs)}. Median {f2(rg.med)} GB/s. Intervals: {vals} GB/s. "` | Returns the text. This line writes the row name, the kernel (`kernel_name`), the median of the intervals in GB/s and the list `vals`. |
| 1548 | `            f"n = {plural(rg.n, 'interval')} / {plural(rg.np, 'process')}. Source: {src(rg.recs)}.")` | Continues the text of line 1547: n as intervals and processes (`plural`, line 220), and the source text of `src` (line 359), which names the csv file and the lines of the interval rows. |
| 1551 | `def f1_row(name, notes, old, new, drops, hollow, how):` | Starts the function `f1_row`. It packs the fields of one row of figure 1 into a dictionary. `old` and `new` are `Rg` objects: the old read kernel and the load-only loop. `drops` is a list of drops in percent. `hollow` is true for an 8000 MT/s row. `how` is a text that says how the drop was formed. |
| 1552 | `    return dict(name=name, notes=notes, old=old, new=new, drops=drops, hollow=hollow, how=how)` | Returns a dictionary that holds the seven arguments under the same names. |
| 1555 | `def bwx_row(name, notes, olds, news, hollow=False):` | Starts the function `bwx_row`. It builds one row of figure 1 from records of bwx12. `olds` are the old-kernel records of the row and `news` the load-only records. |
| 1556 | `    pr = pairs_in_process(olds, news)` | `pr`: the pairs of the row. `pairs_in_process` (line 407) pairs each load-only interval with the old-kernel interval of the same process and round. A process with 2 rounds gives 2 pairs. |
| 1557 | `    return f1_row(name, notes, Rg([o for o, _ in pr]), Rg([n for _, n in pr]), drops_of(pr), hollow,` | Returns the row through `f1_row`. `old` is the range (`Rg`) of the old-kernel intervals of the pairs, and `new` is the range of the load-only intervals. `drops_of` (line 421) gives one drop per pair: (1 - load-only rate / old rate) x 100. It uses the values of `val` (line 176) with 6 decimals, not the rates rounded to 0.01 GB/s. The median of 2 intervals is their mean. So each dot of a row with 2 pairs is the mean of 2 intervals. |
| 1558 | `                  "lowest and highest pair of the same process and round")` | Continues the call of line 1557: the text `how`. It says that the drop text of the row gives the lowest and the highest pair. Example: for the process T72C1, section 3.3 of the facts sheet gives 466.01 and 465.54 GB/s for `oldread`, and 320.90 and 320.89 GB/s for `read` [Ref1]. These rates give drops of 31.14 % and 31.07 %. Both round to 31.1 %, so the figure prints one value, 31.1 % (line 1663). |

### The rows and the two blocks of figure 1 (lines 1561 to 1592)

| Line | Source | Explanation |
|---:|---|---|
| 1561 | `IN_PLACE = "asmread in place of the new read kernel"` | `IN_PLACE`: the note text of the rows that use `asmread` in place of the new read kernel. |
| 1562 | `B1_8000 = [bwx_row(f"L-1 · {hm(B_L_OLD['L-1'][0]['launch_utc'], True)}", [IN_PLACE, "row with the argument line of part L"], olds=B_L_OLD["L-1"], news=B_L_ASM["L-1"], hollow=True)]` | `B1_8000`: the 8000 MT/s rows of the first block of figure 1 (6 s intervals, runner bwx12). It holds one hollow row, L-1, from the `oldread` records at position 0 and the `asmread` records at position 1 of that row (lines 291 to 292). The row name is `L-1`, a middle dot, and the date and time of the launch from `hm` (line 377). The second note says that this row ran the argument line of part L. The rows L-2 to L-4 are not rows of figure 1. |
| 1563 | `B1_7200 = [bwx_row(f"F72d12 · {hm(F_OLD[0]['launch_utc'])}", [IN_PLACE, "earlier run of the same boot, not part of the rerun"], olds=F_OLD, news=F_ASM)]` | `B1_7200`: the 7200 MT/s rows of the first block. The list starts with the row of F72d12, from `F_OLD` and `F_ASM` (lines 279 to 280). The row name holds the launch time. The second note says that F72d12 is an earlier run of the same boot and not part of the rerun. |
| 1564 | `for s_ in (1, 2, 3):` | Starts a loop over the three sessions. |
| 1565 | `    o_ = [r for r in L_OLD if r["session"] == s_]` | `o_`: the `oldread` records of part L of this session. They are at position 0 (line 275). |
| 1566 | `    B1_7200.append(bwx_row(f"Part L, session {s_} ({o_[0]['tag']})", [IN_PLACE], olds=o_, news=[r for r in L_ASM if r["session"] == s_]))` | Adds one row per session of part L. Its name holds the session number and the tag of the process. The load-only records are the `asmread` records at position 1 of the same session (line 276). |
| 1567 | `for t_ in ("T72C1", "T72C2", "T72C3", "T72C4"):` | Starts a loop over the four processes of part C. |
| 1568 | `    o_ = [r for r in C_OLD if r["tag"] == t_]` | `o_`: the `oldread` records of this process. |
| 1569 | `    n_ = [r for r in C_READ if r["tag"] == t_]` | `n_`: the records of the bwx12 kernel `read` (the new read kernel) of this process. |
| 1570 | `    B1_7200.append(bwx_row(f"Part C, {t_} ({o_[0]['file'][:-4]})", [f"kernel read = the new read kernel, after {n_[0]['kernel_before']}"], olds=o_, news=n_))` | Adds one row per process of part C, from its `oldread` records and its `read` records. The name holds the tag and the name of the csv file without `.csv`, which is the kernel order (`cfwd` or `crev`). The note names the kernel that ran directly before `read` (field `kernel_before`). The `asmread` intervals of part C are not in figure 1. A `crev` process times asmread, read, oldread. So in such a process the `oldread` interval of a pair ran after the `read` interval of the pair. |
| 1571 | `for t_ in ("T72I1", "T72I2"):` | Starts a loop over the two processes of control I. |
| 1572 | `    B1_7200.append(bwx_row(f"Control I, {t_}", [IN_PLACE, "added after the first numbers were seen"],` | Adds one row per process of control I. The second note says that control I was added after the first numbers were seen. |
| 1573 | `                           olds=[r for r in I_OLD if r["tag"] == t_], news=[r for r in I_ASM if r["tag"] == t_]))` | Continues the call of line 1572: the `oldread` records and the `asmread` records with the tag of this process. |
| 1574 | `B2_8000 = [f1_row(f"{d}, round {rnd} · {hm(p['old'].recs[0]['launch_utc'], True)}", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], True,` | `B2_8000`: the 8000 MT/s rows of the second block (0.5 s intervals, binaries `bw_old` and `bw_new`). Each row is built with `f1_row` from one entry `p` of `A8_PAIRS` (line 455). The row name holds the dataset, the round, and the date and time of the launch of the `bw_old` process. `p["old"]` and `p["new"]` are the ranges of the 3 intervals of the `bw_old` read process and of the `bw_new` read process. The row has one drop, `p["drop"]`. `True` makes the markers hollow. |
| 1575 | `                  "between the medians of the two processes")` | Continues the call of line 1574: the text `how`. The drop is taken between the medians of the two processes: (1 - median of `bw_new` read / median of `bw_old` read) x 100 (`a_pair`, line 444). |
| 1576 | `           for (d, rnd), p in A8_PAIRS.items()]` | The loop of the list: one row per entry of `A8_PAIRS`. These are the rows A-1 and A-2, each in round 1 and in round 2. That gives 4 rows. Row A-3 holds `bw_old` read only and is not in figure 1. |
| 1577 | `B2_7200 = [f1_row(f"Part A, session {s_}, round {rnd} (T72A{s_})", ["bw_new read against bw_old read"], p["old"], p["new"], [p["drop"]], False,` | `B2_7200`: the 7200 MT/s rows of the second block, built in the same way from `A_PAIRS` (line 451). The row name holds the session, the round and the folder tag. `False` makes the markers filled. Each interval rate of a part A row is the field `GBps` of the record: the column `aggregate_GBps` of its csv row, with 2 decimals. The header line of the csv file gives the formula of this column: the total bytes of all threads divided by the longest elapsed time of a thread [Ref3]. |
| 1578 | `                  "between the medians of the two processes")` | Continues the call of line 1577: the same text `how` as in line 1575. The rows of the first block use another formula for a rate: the sum of the 120 thread rates (`val`, line 176). |
| 1579 | `           for (s_, rnd), p in A_PAIRS.items()]` | The loop of the list: one row per entry of `A_PAIRS`. These are the sessions 1 to 3, each in round 1 and in round 2. That gives 6 rows. |
| 1580 | `F1_BLOCKS = [` | `F1_BLOCKS`: the data of figure 1, a list of two blocks. Each block is a dictionary with a title, the same title in two lines (`lines`, for the narrow layout) and two groups of rows. |
| 1581 | `    dict(title="6 s measurements, runner bwx12, all threads stop together", lines=["6 s measurements, runner bwx12,", "all threads stop together"],` | First block: the title and its two lines. The block holds the 6 s measurements of the runner bwx12, in which all threads stop together (the common stop). |
| 1582 | `         groups=[dict(title="8000 MT/s · hollow markers", rows=B1_8000), dict(title="7200 MT/s · filled markers", rows=B1_7200)]),` | The two groups of the first block: the 8000 MT/s rows `B1_8000` and the 7200 MT/s rows `B1_7200`. Each group title names the memory speed and the kind of marker (hollow or filled), with a middle dot between them. |
| 1583 | `    dict(title="0.5 s measurements, the two binaries of 2026-11-13, each thread finishes its pass",` | Second block: the title. The block holds the 0.5 s measurements of the two binaries of 2026-11-13, in which each thread finishes its pass (the whole-pass stop). |
| 1584 | `         lines=["0.5 s measurements, the two binaries of", "2026-11-13, each thread finishes its pass"],` | The same title in two lines. |
| 1585 | `         groups=[dict(title="8000 MT/s · hollow markers", rows=B2_8000), dict(title="7200 MT/s · filled markers", rows=B2_7200)]),` | The two groups of the second block: `B2_8000` and `B2_7200`, with the same group titles as in line 1582. |
| 1586 | `]` | Ends the list `F1_BLOCKS`. |
| 1587 | `SAME_LINE_ROWS = [r for r in B1_7200 if not r["name"].startswith("Part C")]` | `SAME_LINE_ROWS`: the rows of `B1_7200` whose name does not start with `Part C`. They are the rows of the argument line of part L in the 7200 MT/s boot: F72d12, the three sessions of part L and the two processes of control I. |
| 1588 | `need(len(SAME_LINE_ROWS) == 6, "figure 1: expected 6 rows of the argument line of part L in the 7200 MT/s boot")` | Hard assertion: the script stops unless these are 6 rows. The caption of figure 1 prints this number (line 2732). |
| 1589 | `F1_NROWS = sum(len(g["rows"]) for b in F1_BLOCKS for g in b["groups"])` | `F1_NROWS`: the number of all rows of figure 1, summed over the blocks and their groups. |
| 1590 | `need(F1_NROWS == 21, "figure 1: expected 21 rows")` | Hard assertion: the script stops unless figure 1 has 21 rows (1 + 10 + 4 + 6). |

### Function `fig1`: layout, vertical places, axis and grid lines (lines 1593 to 1643)

| Line | Source | Explanation |
|---:|---|---|
| 1593 | `def fig1(layout="wide"):` | Starts the function `fig1`. It draws figure 1 as SVG text. `layout` selects one of three widths: `wide`, `mid` or `narrow`. `build` calls it once per layout (lines 2729 to 2731). |
| 1594 | `    """The dumbbell chart in one of three layouts, so that it never scrolls sideways.` | Comment: the documentation text. The dumbbell chart is drawn in one of three layouts. So it never scrolls sideways. |
| 1595 | `    wide (940 px, windows from 1000 px) and mid (726 px, windows from 780 px): row names in a column at the left.` | Comment: the documentation text, continued. The layout `wide` is 940 px wide and is for windows from 1000 px. The layout `mid` is 726 px wide and is for windows from 780 px. Both write the row names in a column at the left. |
| 1596 | `    narrow (386 px, windows below 780 px): the row name stands above its dumbbell, so the chart fits into a 420 px wide window."""` | Comment: the documentation text, continued. The layout `narrow` is 386 px wide and is for windows below 780 px. The row name stands above its dumbbell. So the chart fits into a window that is 420 px wide. |
| 1597 | `    narrow = layout == "narrow"` | `narrow`: true when the layout is `narrow`. |
| 1598 | `    W, X0, X1 = {"wide": (940, 356, 846), "mid": (726, 300, 646), "narrow": (386, 26, 332)}[layout]` | Takes three numbers for the layout, in px. `W` is the width of the drawing. `X0` is the x place of 0 GB/s, and `X1` is the x place of 500 GB/s. In the wide layout the axis runs from 356 px to 846 px. |
| 1599 | `    XMAX = 500` | `XMAX`: the rate at the right end of the axis, 500 GB/s. |
| 1600 | `    sx = lambda v: X0 + (X1 - X0) * float(v) / XMAX` | `sx`: converts a rate in GB/s to an x place. The axis is linear and starts at 0. `float(v)` converts the rate to a floating-point number. Only the drawing uses this copy. |
| 1602 | `    def drawn(notes):` | Starts the inner function `drawn`. It returns the note lines of a row as this layout draws them. |
| 1603 | `        """The note lines as this layout draws them. The mid layout has a label column of 300 px:` | Comment: the documentation text of `drawn`. The function gives the note lines as this layout draws them. The mid layout has a label column of 300 px. |
| 1604 | `        a note of more than 44 characters is broken after its comma, so that it ends before the 0 gridline."""` | Comment: the documentation text, continued. There a note of more than 44 characters is broken after its comma. So the note ends before the grid line of 0 GB/s. |
| 1605 | `        if layout != "mid":` | Tests whether the layout is not `mid`. |
| 1606 | `            return list(notes)` | In the wide and in the narrow layout the notes are returned unchanged, as a new list. |
| 1607 | `        out = []` | `out`: the list of the note lines for the mid layout. |
| 1608 | `        for nt in notes:` | Starts the loop over the notes. |
| 1609 | `            if len(nt) > 44:` | Tests whether the note has more than 44 characters. |
| 1610 | `                need(", " in nt, f"figure 1, mid layout: the note '{nt}' is too long and has no comma to break at")` | Hard assertion: the script stops when such a note holds no comma with a space after it. The message names the note. |
| 1611 | `                a, b_ = nt.split(", ", 1)` | Splits the note at its first comma. `a` is the text before the comma, and `b_` is the text after it. |
| 1612 | `                out += [a + ",", b_]` | Adds two lines: `a` with the comma, and `b_`. |
| 1613 | `            else:` | A note of at most 44 characters: |
| 1614 | `                out.append(nt)` | It is added as one line. |
| 1615 | `        return out` | Returns the note lines. Ends the function `drawn`. |
| 1616 | `    y = 30` | `y`: the running vertical place in px. It starts at 30. Lines 1617 to 1630 give every block, group and row its place. No rate is used there. |
| 1617 | `    for b in F1_BLOCKS:` | Starts the loop over the two blocks. |
| 1618 | `        b["tl"] = b["lines"] if narrow else [b["title"]]` | `b["tl"]`: the title lines of the block. The narrow layout takes the two lines of `lines`. The other layouts take the one line `title`. |
| 1619 | `        b["y"] = y` | `b["y"]`: the top of the title bar of the block. |
| 1620 | `        b["th"] = 10 + 16 * len(b["tl"])` | `b["th"]`: the height of the title bar: 10 px plus 16 px per title line. |
| 1621 | `        y += b["th"] + 4` | Moves `y` below the title bar, with a gap of 4 px. |
| 1622 | `        for g in b["groups"]:` | Starts the loop over the two groups of the block. |
| 1623 | `            g["y"] = y` | `g["y"]`: the top of the group. |
| 1624 | `            y += 22` | Keeps 22 px for the group title. |
| 1625 | `            for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 1626 | `                r["dn"] = drawn(r["notes"])` | `r["dn"]`: the note lines of the row for this layout (`drawn`, line 1602). |
| 1627 | `                r["h"] = 52 + 13 * len(r["dn"]) if narrow else 22 + 13 * len(r["dn"])` | `r["h"]`: the height of the row. In the narrow layout it is 52 px plus 13 px per note line. The row name is drawn above the dots there. In the other layouts it is 22 px plus 13 px per note line. |
| 1628 | `                r["y"] = y` | `r["y"]`: the top of the row. |
| 1629 | `                y += r["h"]` | Moves `y` to the next row. |
| 1630 | `        y += 6` | Adds a gap of 6 px after each block. |
| 1631 | `    yb = y` | `yb`: the vertical place below the last row. The grid lines end there. |
| 1632 | `    H = yb + (64 if narrow else 50)` | `H`: the height of the whole drawing: `yb` plus 64 px in the narrow layout, or plus 50 px in the other layouts. This space holds the lower numbers and the title of the axis. |
| 1633 | `    o = [f'<svg class="{dict(wide="f1w", mid="f1m", narrow="f1n")[layout]}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Dumbbell chart: whole-chip read rate of the old read kernel and of the load-only loop, one row per bwx12 process or per round of the two part A binaries, {F1_NROWS} rows">']` | `o`: the list of the SVG pieces. It starts with the opening `svg` tag. The class is `f1w`, `f1m` or `f1n`, by the layout. With this class the style block shows the one layout that fits the window (lines 2646 to 2648). `viewBox`, `width` and `height` set the size: `W` by `H` px. `aria-label` is a text for screen readers. It names the kind of chart and says what a row is, with the number of rows `F1_NROWS`. |
| 1634 | `    for t in range(0, XMAX + 1, 100):` | Starts a loop over the rates 0, 100, 200, 300, 400 and 500 GB/s. |
| 1635 | `        o.append(f'<line x1="{sx(t):.1f}" y1="24" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/>')` | Draws a vertical grid line at this rate, from 24 px down to `yb`, in the colour `GRID`. |
| 1636 | `        o.append(T(sx(t), 17, t, 12, MUTED, "middle", extra=TAB))` | Writes the number of the rate above the grid line, centred, in the grey colour `MUTED`. |
| 1637 | `        o.append(T(sx(t), yb + 16, t, 12, MUTED, "middle", extra=TAB))` | Writes the same number below the grid line. |
| 1638 | `    o.append(T(sx(XMAX) + 15, 17, "GB/s", 12, MUTED))` | Writes the unit `GB/s` at the top, 15 px to the right of the grid line of 500 GB/s. |
| 1639 | `    if narrow:` | Tests whether the layout is `narrow`. |
| 1640 | `        o.append(T(W / 2, yb + 36, "Whole-chip read rate, GB/s", 12.5, MUTED, "middle"))` | Narrow layout: writes the axis title, the name of the quantity with its unit, in the middle of the drawing, 36 px below `yb`. |
| 1641 | `        o.append(T(W / 2, yb + 52, "The axis starts at 0.", 12.5, MUTED, "middle"))` | Narrow layout: writes a second line under it. It says that the axis starts at 0. |
| 1642 | `    else:` | The other two layouts: |
| 1643 | `        o.append(T((X0 + X1) / 2, yb + 38, "Whole-chip read rate, GB/s. The axis starts at 0.", 12.5, MUTED, "middle"))` | They write both texts as one line, centred under the axis, 38 px below `yb`. |

### Function `fig1`: title bars, labels and the marks of each row (lines 1644 to 1680)

| Line | Source | Explanation |
|---:|---|---|
| 1644 | `    for b in F1_BLOCKS:` | Starts the second loop over the blocks. This loop draws them. The lines up to line 1661 write titles and labels. They use no rate. |
| 1645 | `        o.append(f'<rect x="0" y="{b["y"]}" width="{W}" height="{b["th"]}" fill="#f1f0ec"/>')` | Draws the title bar of the block: a light grey rectangle over the full width `W`, with the height `b["th"]`. |
| 1646 | `        for i, tl in enumerate(b["tl"]):` | Starts the loop over the title lines. |
| 1647 | `            o.append(T(8 if narrow else 12, b["y"] + 17.5 + 16 * i, tl, 13, INK, weight=600))` | Writes one title line in bold type (weight 600, 13 px), 16 px below the line before it. The text starts 8 px from the left edge in the narrow layout and 12 px in the other layouts. |
| 1648 | `        for g in b["groups"]:` | Starts the loop over the groups of the block. |
| 1649 | `            o.append(T(8 if narrow else 12, g["y"] + 15, g["title"], 12, MUTED, weight=600, extra=HALO))` | Writes the group title in bold grey type, 15 px below the top of the group. |
| 1650 | `            for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 1651 | `                if narrow:` | Tests whether the layout is `narrow`. |
| 1652 | `                    ty = r["y"] + 14` | Narrow layout: `ty`, the vertical place of the row name, is 14 px below the top of the row. |
| 1653 | `                    cy = r["y"] + r["h"] - 13` | Narrow layout: `cy`, the vertical place of the two dots, is 13 px above the bottom of the row. So the name and the notes stand above the dots. |
| 1654 | `                    o.append(f'<line x1="0" y1="{r["y"] + r["h"]}" x2="{W}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/>')` | Narrow layout: draws a thin line under the row over the full width (colour `GRID`, opacity 0.6). |
| 1655 | `                else:` | The other two layouts: |
| 1656 | `                    cy = r["y"] + r["h"] / 2` | `cy` is the middle of the row. |
| 1657 | `                    ty = cy - 6.5 * len(r["dn"]) + 4` | `ty`: the vertical place of the row name. The value centres the name and its note lines at `cy`. |
| 1658 | `                tx = 12 if narrow else 24` | `tx`: the x place of the name and of the notes: 12 px in the narrow layout, 24 px in the other layouts. |
| 1659 | `                o.append(T(tx, ty, r["name"], 12.5, INK, extra=HALO))` | Writes the row name (12.5 px, colour `INK`, with the outline of `HALO`). |
| 1660 | `                for i, nt in enumerate(r["dn"]):` | Starts the loop over the note lines of the row. |
| 1661 | `                    o.append(T(tx, ty + 13 * (i + 1), nt, 11, MUTED, extra=HALO))` | Writes one note line under the name, 13 px per line, in grey type of 11 px. |
| 1662 | `                xo, xn = sx(r["old"].med), sx(r["new"].med)` | `xo` and `xn`: the x places of the two dots of the row. `xo` is `sx` of the median of the old read kernel (`r["old"].med`). `xn` is `sx` of the median of the load-only loop (`r["new"].med`). |
| 1663 | `                dt = drop_txt(r["drops"])` | `dt`: the drop text of the row from `drop_txt` (line 425): the lowest and the highest drop of the row with 1 decimal, or one value when both are printed equal. |
| 1664 | `                tipname = ", ".join([r["name"]] + r["notes"])` | `tipname`: the row name and the notes of the row, joined with commas. Every tooltip of the row starts with it. |
| 1665 | `                o.append(f'<g><title>{esc(tipname)}: drop of the load-only loop below the old read kernel: {esc(dt)} ({esc(r["how"])}, n = {plural(len(r["drops"]), "pair")}). Source: {esc(src(r["old"].recs + r["new"].recs))}.</title>'` | Adds an SVG group for the line between the two dots. This source line writes the tooltip of the group (the element `title`): `tipname`, the drop text `dt`, how the drop was formed (`how`), the number of pairs, and the source text of `src` (line 359) for the records of both kernels. |
| 1666 | `                         f'<line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{LINK}" stroke-width="1.5"/>'` | Continues the group of line 1665: the visible line from the median of the load-only loop to the median of the old read kernel, 1.5 px wide, in the grey colour `LINK`. |
| 1667 | `                         f'<line x1="{xn:.1f}" y1="{cy:.1f}" x2="{xo:.1f}" y2="{cy:.1f}" stroke="{SURF}" stroke-opacity="0" stroke-width="14"/>'` | Continues the group: a second line at the same place, 14 px wide and fully transparent. It gives the pointer a larger area that shows the tooltip. |
| 1668 | `                         + T((xo + xn) / 2, cy - 7, dt, 11 if narrow else 11.5, INK, "middle", extra=HALO + TAB) + "</g>")` | Continues the group: the drop text `dt`, centred 7 px above the middle of the line. Then the group is closed. |
| 1669 | `                for rg, x, color, side in ((r["old"], xo, BLUE, 1), (r["new"], xn, ORANGE, -1)):` | Starts a loop that runs twice. First run: the old read kernel, with its range `r["old"]`, the place `xo`, the colour `BLUE` and `side` equal to `1`. Second run: the load-only loop, with `r["new"]`, `xn`, the colour `ORANGE` and `side` equal to `-1`. |
| 1670 | `                    xa, xb = sx(rg.lo), sx(rg.hi)` | `xa` and `xb`: the x places of the lowest and of the highest interval rate of this kernel in the row. |
| 1671 | `                    o.append(f'<g class="pt"><title>{esc(dot_title(tipname, rg))}</title>'` | Adds an SVG group of the class `pt` for the dot. Its tooltip is the text of `dot_title` (line 1545). |
| 1672 | `                             f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="12" fill="{SURF}" fill-opacity="0"/>'` | Continues the group of line 1671: a transparent circle of 12 px radius around the dot. It also shows the tooltip. |
| 1673 | `                             + marker(x, cy, color, r["hollow"])` | Continues the group: the dot at the median, from `marker` (line 1529). It is hollow for an 8000 MT/s row and filled for a 7200 MT/s row. |
| 1674 | `                             + f'<path d="M{xa:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xb:.1f} {cy - 3.5:.1f}V{cy + 3.5:.1f}M{xa:.1f} {cy:.1f}H{xb:.1f}" stroke="{INK}" stroke-width="1.1" fill="none"/></g>')` | Continues the group: the range bar in the colour `INK`, 1.1 px wide. The path draws a vertical line of 7 px at `xa`, the same at `xb`, and a horizontal line from `xa` to `xb` at the height of the dot. So the bar runs from the lowest to the highest interval of the row, to the scale of the axis. Then the group is closed. |
| 1675 | `                    off = max(xb - x, x - xa) + 8` | `off`: the distance in px from the dot to the farther end of its range bar, plus 8 px. |
| 1676 | `                    o.append(T(x + side * max(off, 10.5), cy + 4.2, f2(rg.med), 12, INK, "start" if side > 0 else "end", extra=HALO + TAB))` | Writes the median with 2 decimals (`f2`) beside the dot: `off` px from its centre, and at least 10.5 px. So the number stands outside the range bar. `side` puts the number to the right of the blue dot and to the left of the orange dot. |
| 1677 | `    o.append("</svg>")` | Closes the `svg` element. |
| 1678 | `    return "\n".join(o)` | Joins the pieces with line breaks and returns the drawing as one text. So figure 1 shows one median and one range per kernel and row. It shows no mean over rows and no total over rows. |

### Helpers of figure 2: `beeswarm`, `p_row`, `plain_notes`, `note_lines` and two constants (lines 1681 to 1724)

| Line | Source | Explanation |
|---:|---|---|
| 1681 | `# ------------------------------------------------------------------ figure 2: every interval, two panels` | Comment: a section mark. The code of figure 2 starts here. Figure 2 shows every interval as one dot, in two panels. |
| 1682 | `def beeswarm(xs, r=4.3):` | Starts the function `beeswarm`. It returns one vertical offset per dot of a row. `xs` holds the x places of the dots of one row. `r` is the radius of a dot, 4.3 px unless given. |
| 1683 | `    """Vertical offsets so that dots of one row do not cover each other."""` | Comment: the documentation text. The offsets keep the dots of one row from covering each other. |
| 1684 | `    lanes = [0, -5.5, 5.5, -11, 11]` | `lanes`: the five possible offsets in px, in the order of use: `0`, `-5.5`, `5.5`, `-11` and `11`. |
| 1685 | `    placed, out = [], [0.0] * len(xs)` | `placed`: the dots that have an offset so far, each with its x place and its offset. `out`: the result list with one offset per dot. All offsets are 0.0 at the start. |
| 1686 | `    for i in sorted(range(len(xs)), key=lambda k: xs[k]):` | Starts the loop over the dots from left to right. `sorted` orders the numbers of the dots by their x place. |
| 1687 | `        for ln in lanes:` | Starts the loop over the five offsets, in the order of `lanes`. |
| 1688 | `            if all(abs(xs[i] - px) >= 2 * r or ln != pl for px, pl in placed):` | Tests whether this offset is free for the dot. It is free when every dot placed before is at least `2 * r` (8.6 px) away in x, or has another offset. |
| 1689 | `                break` | Takes the first free offset and leaves the inner loop. |
| 1690 | `        placed.append((xs[i], ln))` | Records the dot with its offset. When no offset was free, the inner loop has ended without a `break`, and `ln` is the last offset, 11 px. |
| 1691 | `        out[i] = ln` | Stores the offset at the place of this dot in `out`. |
| 1692 | `    return out` | Returns the offsets in the order of `xs`. An offset changes only the vertical place of a dot. The rate of the dot stays on the horizontal axis. `panel` calls this function (line 1781) and stops the script when two dots lie 5.2 px or less apart (line 1786). |
| 1695 | `def p_row(name, recs, hollow, notes=(), label=None, band=None, more=()):` | Starts the function `p_row`. It builds one row of figure 2. `recs` are the interval records of the row. `hollow` is true for an 8000 MT/s row. `notes` are fixed notes. `label` is a shorter name for the figure. `band` is the range of the 8000 MT/s rows of the block. `more` holds notes that follow the note of the band. |
| 1696 | `    """One row of figure 2. With band (the 8000 MT/s range of the block) the row gets a note with its place against the band.` | Comment: the documentation text. One row of figure 2. With `band`, the row gets a note that says where the row lies relative to the band. |
| 1697 | `    The rate is on the horizontal axis, so a higher row lies to the right of the band.` | Comment: the documentation text, continued. The rate is on the horizontal axis. So a row with higher rates lies to the right of the band. |
| 1698 | `    A note that starts with "!" is drawn in ink colour: it is the key distance of the row.` | Comment: the documentation text, continued. A note that starts with `!` is drawn in the ink colour. It is the key distance of the row. Line 1837 also draws such a note in bold type. |
| 1699 | `    A note that starts with "~" only repeats a part of the row name: it is drawn under the short label of the figure` | Comment: the documentation text, continued. A note that starts with `~` only repeats a part of the row name. It is drawn under the short label of the figure. |
| 1700 | `    and left out of the tooltip, which shows the full row name. "\|" is a line break inside one note."""` | Comment: the documentation text, continued. Such a note is left out of the tooltip, which shows the full row name. A `\|` is a line break inside one note. |
| 1701 | `    rg = Rg(recs)` | `rg`: the range of the records of the row (`Rg`, line 192). `Rg` calls `val` (line 176) for each record. It stores the lowest rate, the highest rate, the median, the number of intervals and the number of processes. |
| 1702 | `    notes = list(notes)` | Copies `notes` into a new list. |
| 1703 | `    if band is not None:` | Tests whether a band was given. |
| 1704 | `        d = rg.nearest(band)` | `d`: the distance of the nearest ends of the row and the band (`nearest`, line 210), computed from the rates before rounding. It is above 0 when the row is the higher range, below 0 when the row is the lower range, and 0 when the two ranges overlap. |
| 1705 | `        notes.append("!inside the band" if band.lo <= rg.lo and rg.hi <= band.hi else` | Adds the note of the band. It starts with `!`. First case: the note is `inside the band` when the lowest and the highest rate of the row lie inside the band. |
| 1706 | `                     f"!{f2(abs(d))} GB/s {'higher\|(right' if d > 0 else 'lower\|(left'} of the band)" if d != 0 else "!overlaps the band")` | Continues the expression of line 1705. Second case, `d` is not 0: the note gives the distance without its sign, rounded to 0.01 GB/s, with the words `higher` and `(right of the band)`, or `lower` and `(left of the band)`. The `\|` puts the words in round brackets on a second line. Third case: the note is `overlaps the band`. It applies when the two ranges share a value and the row is not inside the band. |
| 1707 | `    notes += list(more)` | Adds the notes of `more` after the note of the band. |
| 1708 | `    return dict(name=name, rg=rg, hollow=hollow, notes=notes, label=label or name)` | Returns a dictionary with the name, the range `rg`, the marker kind `hollow`, the notes and the label. Without `label` the label is the name. |
| 1711 | `def plain_notes(notes, tooltip=False):` | Starts the function `plain_notes`. It returns the notes of a row as plain text. |
| 1712 | `    """The notes of a row as plain text. For a tooltip the notes that only repeat the row name are left out."""` | Comment: the documentation text. For a tooltip, the notes that only repeat the row name are left out. |
| 1713 | `    return [n.lstrip("!~").replace("\|", " ") for n in notes if not (tooltip and n.startswith("~"))]` | Returns each note without the marks `!` and `~` at its start, and with a space in place of each `\|`. With `tooltip=True` the notes that start with `~` are left out. |
| 1716 | `def note_lines(notes):` | Starts the function `note_lines`. It returns the lines of the notes of a row as the figure draws them. |
| 1717 | `    """(text, strong) for every drawn line of the notes of a row."""` | Comment: the documentation text. The result holds one pair (text, strong) for every drawn line. |
| 1718 | `    return [(seg, n.startswith("!")) for n in notes for seg in n.lstrip("!~").split("\|")]` | Removes the marks at the start of each note and splits the note at each `\|` into lines. Each line carries a flag. The flag is true when the note starts with `!`. `panel` then draws the line in bold type (line 1837). |
| 1721 | `F2_GAPS = []         # per panel of figure 2: (title, number of dots, smallest distance of two dots in px, hover areas cut by a neighbour, areas of all hover areas in px2)` | `F2_GAPS`: an empty list. `panel` adds one entry per panel of figure 2 (line 1788). Comment at the end of the line: an entry holds the title, the number of dots, the smallest distance of two dots in px, the number of hover areas that a neighbour cuts, and the areas of all hover areas in square px. The page check of lines 2812 to 2817 reads the list. |
| 1722 | `HIT_R = 12.0         # radius of the hover area of a free-standing dot: 24 px across` | `HIT_R`: 12 px, the radius of the hover area of a dot that has no other dot within 24 px. Comment at the end of the line: such an area is 24 px across. |

### Functions `hit_cell` and `poly_area`: the hover area of one dot (lines 1725 to 1755)

| Line | Source | Explanation |
|---:|---|---|
| 1725 | `def hit_cell(i, pts, nseg=32):` | Starts the function `hit_cell`. It returns the hover area of the dot with the number `i`. `pts` holds the places of all dots of the panel. `nseg` is the number of corners of the first polygon, 32 unless given. This is layout code. It reads no rate. |
| 1726 | `    """The hover area of dot i: the part of a circle of radius HIT_R around the dot that is nearer to it than to any other dot.` | Comment: the documentation text. The hover area of the dot `i` is the part of a circle of the radius `HIT_R` around the dot that is nearer to this dot than to any other dot. |
| 1727 | `    The circle is a polygon of nseg corners. The half-way line to every dot within 2 x HIT_R cuts it (a Voronoi cell, clipped to the circle).` | Comment: the documentation text, continued. The circle is a polygon with `nseg` corners. The half-way line to every dot within 2 x `HIT_R` cuts it. The comment names the result a Voronoi cell that is clipped to the circle. A Voronoi cell is the set of the points that are nearer to one given point than to any other given point. |
| 1728 | `    So the areas of two dots never overlap, and the pointer only has to be nearest to a dot. Returns (corners, cut by a neighbour)."""` | Comment: the documentation text, continued. So the areas of two dots never overlap, and the pointer only has to be nearest to a dot. The function returns the corners, and a flag that says whether a neighbour cut the circle. |
| 1729 | `    x0, y0 = pts[i]` | `x0`, `y0`: the place of the dot `i`. |
| 1730 | `    poly = [(x0 + HIT_R * math.cos(2 * math.pi * k / nseg), y0 + HIT_R * math.sin(2 * math.pi * k / nseg)) for k in range(nseg)]` | `poly`: the first polygon. Its 32 corners lie on a circle of the radius `HIT_R` around the dot, at equal angles. |
| 1731 | `    cut = False` | `cut`: becomes true when a neighbour cuts the polygon. It starts as false. |
| 1732 | `    for j, (x1, y1) in enumerate(pts):` | Starts the loop over all dots of the panel. `j` is the number of the other dot, and `x1`, `y1` is its place. |
| 1733 | `        dx, dy = x1 - x0, y1 - y0` | `dx`, `dy`: the vector from the dot `i` to the other dot. |
| 1734 | `        if j == i or dx * dx + dy * dy >= (2 * HIT_R) ** 2:` | Skips the dot itself, and every dot that is 24 px (2 x `HIT_R`) or more away. The test compares the squared distances. |
| 1735 | `            continue` | Goes on with the next dot. |
| 1736 | `        mx, my = (x0 + x1) / 2, (y0 + y1) / 2` | `mx`, `my`: the point half-way between the two dots. |
| 1737 | `        side = [(px - mx) * dx + (py - my) * dy for px, py in poly]          # above 0: nearer to the other dot` | `side`: one number per corner of the polygon. Comment at the end of the line: a value above 0 means that the corner is nearer to the other dot. The number is the scalar product of two vectors: from the half-way point to the corner, and from the dot `i` to the other dot. |
| 1738 | `        out = []` | `out`: the corners of the polygon after this cut. |
| 1739 | `        for k, a in enumerate(poly):` | Starts the loop over the corners. `a` is the corner with the number `k`. |
| 1740 | `            b, sa, sb = poly[(k + 1) % len(poly)], side[k], side[(k + 1) % len(poly)]` | `b`: the next corner. After the last corner comes the first one. `sa` and `sb`: the `side` values of `a` and of `b`. |
| 1741 | `            if sa <= 0:` | Tests whether the corner `a` lies on the side of the dot `i`, or on the half-way line. |
| 1742 | `                out.append(a)` | Such a corner is kept. |
| 1743 | `            if (sa < 0 < sb) or (sb < 0 < sa):` | Tests whether the edge from `a` to `b` crosses the half-way line: one end has a value below 0 and the other end a value above 0. |
| 1744 | `                t = sa / (sa - sb)` | `t`: the fraction of the edge at which it crosses the line. |
| 1745 | `                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))` | Adds the crossing point as a new corner. |
| 1746 | `        cut = cut or len(out) != len(poly) or any(v > 0 for v in side)` | Sets `cut` to true when the number of corners changed, or when a corner had a `side` value above 0. |
| 1747 | `        poly = out` | The cut polygon replaces the polygon. |
| 1748 | `        need(len(poly) >= 3, "figure 2: a hover area is empty")` | Hard assertion: the script stops when the hover area has fewer than 3 corners. |
| 1749 | `    return poly, cut` | Returns the corners and the flag `cut`. |
| 1752 | `def poly_area(poly):` | Starts the function `poly_area`. It returns the area of a polygon in square px. Line 1788 calls it for each hover area. |
| 1753 | `    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2` | Computes the area from the coordinates of the corners. For each corner `a` and the next corner `b` it takes `a[0] * b[1] - b[0] * a[1]`. The area is half of the absolute value of the sum. |

### Function `panel`: places of the rows and dots, hover areas, head lines (lines 1756 to 1795)

| Line | Source | Explanation |
|---:|---|---|
| 1756 | `def panel(title, sub, lo, hi, majors, minors, blocks, color, aria):` | Starts the function `panel`. It draws one panel of figure 2 as SVG text. `build` calls it twice (line 2695 and line 2698): for the panel `Old read kernel` with the blocks `P_OLD_BLOCKS`, and for the panel `Load-only loop` with `P_NEW_BLOCKS`. `lo` and `hi` are the axis limits in GB/s. `majors` and `minors` are the rates of the grid lines. `color` is the colour of the dots: `build` passes `BLUE` for the old read kernel and `ORANGE` for the load-only loop. `aria` is a text for screen readers. |
| 1757 | `    W, X0, X1 = 466, 190, 450` | `W`: the width of the drawing, 466 px. `X0` and `X1`: the x places of the two ends of the axis, 190 px and 450 px. |
| 1758 | `    sx = lambda v: X0 + (X1 - X0) * (float(v) - lo) / (hi - lo)` | `sx`: converts a rate to an x place with a linear scale. The rate `lo` lies at 190 px and the rate `hi` at 450 px. `float(v)` converts the rate to a floating-point number. Only the drawing uses this copy. |
| 1759 | `    y = 98` | `y`: the running vertical place in px. It starts at 98, below the head lines. Lines 1760 to 1771 give each block, group and row its place. No rate is read there. |
| 1760 | `    for b in blocks:` | Starts the loop over the blocks. |
| 1761 | `        b["y"] = y` | `b["y"]`: the top of the title bar of the block. |
| 1762 | `        y += 22 + 13 * len(b["band_txt"])` | Keeps 22 px for the block title, plus 13 px for each line of `band_txt` (the text that describes the grey band). |
| 1763 | `        for g in b["groups"]:` | Starts the loop over the groups of the block. |
| 1764 | `            g["y"] = y` | `g["y"]`: the top of the group. |
| 1765 | `            y += 20 + 12 * len(g.get("sub", ()))` | Keeps 20 px for the group title, plus 12 px for each line of its sub-title `sub`. A group without `sub` has no such line. |
| 1766 | `            for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 1767 | `                r["h"] = max(30, 8 + 13 * (2 + len(note_lines(r["notes"]))))` | `r["h"]`: the height of the row: 8 px plus 13 px for each text line. The text lines are the label, the range line and the note lines (`note_lines`, line 1716). The lower limit of 30 px in the line never applies: with no note line the sum is already 34 px. |
| 1768 | `                r["y"] = y` | `r["y"]`: the top of the row. |
| 1769 | `                y += r["h"]` | Moves `y` to the next row. |
| 1770 | `        b["yend"] = y` | `b["yend"]`: the bottom of the block. |
| 1771 | `        y += 8` | Adds a gap of 8 px after the block. |
| 1772 | `    yb = y` | `yb`: the vertical place of the axis line, below the last block. |
| 1773 | `    H = yb + 56` | `H`: the height of the drawing, 56 px more than `yb`. This space holds the lower numbers and the title of the axis. |
| 1774 | `    # Place every dot first. Then give each dot its hover area: the part of a 12 px circle that is nearer to it than to any other dot.` | Comment: every dot is placed first. Then each dot gets its hover area: the part of a circle of 12 px radius that is nearer to it than to any other dot. |
| 1775 | `    # So the hover areas do not overlap, and the pointer only has to be nearest to a dot (a free-standing dot has a target of 24 px).` | Comment, continued: so the hover areas do not overlap, and the pointer only has to be nearest to a dot. A dot that stands alone has a target that is 24 px across. |
| 1776 | `    placed = []` | `placed`: the places of all dots of the panel, in the order of the blocks, groups and rows. It starts empty. |
| 1777 | `    for b in blocks:` | Starts the loop over the blocks. |
| 1778 | `        for g in b["groups"]:` | Starts the loop over the groups. |
| 1779 | `            for r in g["rows"]:` | Starts the loop over the rows. |
| 1780 | `                xs = [sx(v) for v in r["rg"].v]` | `xs`: the x place of each interval of the row: `sx` of its rate before rounding. `r["rg"].v` holds the rates of the records of the row, as `val` returned them. They stand in the order of `r["rg"].recs`: by launch time, then by interval number (line 197). So the row gets one dot per interval record. |
| 1781 | `                r["dots"] = [(rec, x, r["y"] + r["h"] / 2 + dy, len(placed) + i) for i, (rec, x, dy) in enumerate(zip(r["rg"].recs, xs, beeswarm(xs)))]` | `r["dots"]`: one entry per dot: the record, the x place, the y place and the number of the dot in the panel. The y place is the middle of the row plus the offset from `beeswarm` (line 1682). So dots of one row with near x places do not cover each other. |
| 1782 | `                placed += [(x, y_) for _, x, y_, _ in r["dots"]]` | Adds the places of these dots to `placed`. |
| 1783 | `    gap = [min(((x - a) ** 2 + (y_ - c) ** 2) ** 0.5 for j, (a, c) in enumerate(placed) if j != i) for i, (x, y_) in enumerate(placed)]` | `gap`: for each dot, the distance in px to the nearest other dot of the panel. |
| 1784 | `    # 5.2 px is the outer radius of the largest mark while the pointer is on it (hollow mark: r 3.4 plus half of the 3.6 px hover stroke).` | Comment: 5.2 px is the outer radius of the largest mark while the pointer is on it. That is the hollow mark: a radius of 3.4 px plus half of the outline of 3.6 px that the style block gives it then (line 2657). |
| 1785 | `    # A filled mark has r 4.3, a surface ring up to r 4.9 under it, and a hover stroke up to r 5.1.` | Comment, continued: a filled mark has a radius of 4.3 px, a ring in the background colour up to 4.9 px under it, and an outline up to 5.1 px while the pointer is on it. |
| 1786 | `    need(min(gap) > 5.2, f"figure 2, panel '{title}': two dots are {min(gap):.2f} px apart, so one mark covers the centre of the other")` | Hard assertion: the script stops when the smallest distance of two dots is 5.2 px or less. One mark would then cover the centre of the other. The message names the panel and the distance. |
| 1787 | `    cells = [hit_cell(i, placed) for i in range(len(placed))]` | `cells`: the hover area of every dot (`hit_cell`, line 1725). |
| 1788 | `    F2_GAPS.append((title, len(placed), min(gap), sum(1 for _, cut in cells if cut), [poly_area(c) for c, _ in cells]))` | Adds the entry of this panel to `F2_GAPS`: the title, the number of dots, the smallest distance, the number of hover areas that a neighbour cut, and the area of every hover area (`poly_area`). |
| 1789 | `    o = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(aria)}">']` | `o`: the list of the SVG pieces. It starts with the opening `svg` tag: the size `W` by `H` px and the text `aria` for screen readers, escaped with `esc`. |
| 1790 | `    o.append(T(10, 18, title, 13.5, INK, weight=600))` | First head line: the title of the panel in bold type (13.5 px), at the top left. |
| 1791 | `    o.append(T(10, 33, sub, 11.5, MUTED))` | Second head line: the sub-title `sub` in grey type. |
| 1792 | `    o.append(T(10, 48, "x axis: whole-chip read rate, GB/s.", 11.5, MUTED))` | Third head line: it says that the x axis is the whole-chip read rate in GB/s. |
| 1793 | `    o.append(T(10, 62, f"The axis starts at {lo} GB/s, not at 0.", 11.5, INK, weight=600))` | Fourth head line, in bold type: it says that the axis starts at `lo` GB/s and not at 0. |
| 1794 | `    o.append(T(10, 77, "under a row name: lowest to", 10.5, MUTED))` | Fifth head line: the first half of a key to the text under a row name. |
| 1795 | `    o.append(T(10, 89, "highest, GB/s (n intervals)", 10.5, MUTED))` | Sixth head line: the second half. Together the two lines say that the text under a row name gives the lowest and the highest rate in GB/s, and the number of intervals in round brackets. |

### Function `panel`: grey bands, grid lines, axis, titles and row labels (lines 1796 to 1838)

| Line | Source | Explanation |
|---:|---|---|
| 1796 | `    # The grey bands come first, and the grid lines are drawn over them. The grid colour is close to the band colour,` | Comment: the grey bands are drawn first, and the grid lines over them. The grid colour is close to the band colour. |
| 1797 | `    # so each grid line is drawn again inside a band in a darker tone. A dot inside a band can then be read against a line.` | Comment, continued: so each grid line is drawn again inside a band in a darker tone. A dot inside a band can then be read against a line. |
| 1798 | `    boxes = []` | `boxes`: the rectangle of each band, for the darker grid lines of lines 1813 to 1816. It starts empty. |
| 1799 | `    for b in blocks:` | Starts the loop over the blocks. |
| 1800 | `        on = [g for g in b["groups"] if g.get("band")]` | `on`: the groups of the block whose `band` flag is true. |
| 1801 | `        if b.get("band") and on:` | Tests whether the block has a band range and at least one such group. |
| 1802 | `            y0, y1 = on[0]["y"] + 2, on[-1]["rows"][-1]["y"] + on[-1]["rows"][-1]["h"]` | `y0`, `y1`: the top and the bottom of the band. It starts 2 px below the top of the first group of `on`. It ends at the bottom of the last row of the last group of `on`. |
| 1803 | `            xa, xb = sx(b["band"].lo), sx(b["band"].hi)` | `xa`, `xb`: the left and the right edge of the band: `sx` of the lowest and of the highest rate of the 8000 MT/s rows of the block (`b["band"]`). |
| 1804 | `            boxes.append((xa, xb, y0, y1))` | Stores the rectangle in `boxes`. |
| 1805 | `            o.append(f'<g><title>{esc(b["band_title"])}</title><rect x="{xa:.1f}" y="{y0}" width="{xb - xa:.1f}" height="{y1 - y0}" fill="{BAND}"/>'` | Draws the band as an SVG group: its tooltip (the text `band_title` of the block) and a rectangle in the colour `BAND`. |
| 1806 | `                     f'<path d="M{xa:.1f} {y0}V{y1}M{xb:.1f} {y0}V{y1}" stroke="{BAND_EDGE}"/></g>')` | Continues the group of line 1805: one vertical line at each side edge of the band, in the darker colour `BAND_EDGE`. |
| 1807 | `    for t in minors:` | Starts the loop over the rates of the minor grid lines. |
| 1808 | `        o.append(f'<line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}" stroke-opacity="0.55"/>')` | Draws a minor grid line from 94 px down to `yb`, in the colour `GRID` with an opacity of 0.55. |
| 1809 | `    for t in majors:` | Starts the loop over the rates of the major grid lines. |
| 1810 | `        o.append(f'<line x1="{sx(t):.1f}" y1="94" x2="{sx(t):.1f}" y2="{yb}" stroke="{GRID}"/>')` | Draws a major grid line in the colour `GRID`. |
| 1811 | `        o.append(T(sx(t), 88, t, 11.5, MUTED, "middle", extra=TAB))` | Writes the number of the rate above the rows, centred on the line. |
| 1812 | `        o.append(T(sx(t), yb + 16, t, 11.5, MUTED, "middle", extra=TAB))` | Writes the same number below the rows. |
| 1813 | `    for xa, xb, y0, y1 in boxes:` | Starts the loop over the band rectangles. |
| 1814 | `        for t in sorted(set(minors) \| set(majors)):` | Starts the loop over the rates of all grid lines, minor and major, in rising order. |
| 1815 | `            if xa + 3 < sx(t) < xb - 3:                 # a line within 3 px of a band edge would look like a second edge` | Tests whether the line lies inside the band, more than 3 px from each edge. Comment at the end of the line: a line within 3 px of a band edge would look like a second edge. |
| 1816 | `                o.append(f'<line x1="{sx(t):.1f}" y1="{y0}" x2="{sx(t):.1f}" y2="{y1}" stroke="{BAND_EDGE}" stroke-opacity="{0.6 if t in majors else 0.32}" pointer-events="none"/>')` | Draws the grid line again inside the band in the colour `BAND_EDGE`, with an opacity of 0.6 for a major line and 0.32 for a minor line. `pointer-events="none"` means that this line does not take the pointer. So the tooltip of the band still shows there. |
| 1817 | `    # axis line with a break mark: the axis does not start at 0` | Comment: the axis line has a break mark. The axis does not start at 0. |
| 1818 | `    o.append(f'<path d="M{X0 - 14} {yb}h5l3 -5l4 10l3 -5H{X1}" stroke="{MUTED}" fill="none"/>')` | Draws the axis line at the height `yb` in the colour `MUTED`. The path starts 14 px left of `X0` and goes 5 px to the right. Then it draws a zigzag over 10 px of width: 5 px up, 10 px down and 5 px up again. Then it goes on as a straight line to `X1`. |
| 1819 | `    o.append(T((X0 + X1) / 2 - 20, yb + 34, "Whole-chip read rate, GB/s", 12, MUTED, "middle"))` | Writes the axis title under the axis: the name of the quantity with its unit. |
| 1820 | `    o.append(T((X0 + X1) / 2 - 20, yb + 49, f"The axis starts at {lo} GB/s, not at 0.", 12, INK, "middle", weight=600))` | Writes a second line under it, in bold type: the axis starts at `lo` GB/s, not at 0. |
| 1821 | `    for b in blocks:` | Starts the second loop over the blocks. This loop writes the titles, the labels and the dots. |
| 1822 | `        o.append(f'<rect x="0" y="{b["y"]}" width="{W}" height="{18 + 13 * len(b["band_txt"])}" fill="#f1f0ec"/>')` | Draws the title bar of the block: a light grey rectangle over the full width, 18 px high plus 13 px per line of `band_txt`. |
| 1823 | `        o.append(T(10, b["y"] + 15, b["title"], 12.5, INK, weight=600))` | Writes the block title in bold type. |
| 1824 | `        for i, bt in enumerate(b["band_txt"]):` | Starts the loop over the lines of `band_txt`. |
| 1825 | `            o.append(T(10, b["y"] + 29 + 13 * i, bt, 10.5, MUTED))` | Writes one line of the band text in small grey type (10.5 px), 13 px per line. |
| 1826 | `        for g in b["groups"]:` | Starts the loop over the groups. |
| 1827 | `            o.append(T(10, g["y"] + 14, g["title"], 11.5, MUTED, weight=600, extra=HALO))` | Writes the group title in bold grey type. |
| 1828 | `            for i, st in enumerate(g.get("sub", ())):` | Starts the loop over the lines of the sub-title of the group. A group without `sub` has none. |
| 1829 | `                o.append(T(10, g["y"] + 26 + 12 * i, st, 10.5, MUTED))` | Writes one line of the sub-title in small grey type. |
| 1830 | `            for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 1831 | `                cy = r["y"] + r["h"] / 2` | `cy`: the middle of the row. |
| 1832 | `                nl = 2 + len(note_lines(r["notes"]))` | `nl`: the number of text lines of the row: the label, the range line and the note lines. |
| 1833 | `                ty = cy - 6.5 * (nl - 1) + 4` | `ty`: the vertical place of the label. The value centres the text lines at `cy`. |
| 1834 | `                o.append(T(18, ty, r["label"], 12, INK))` | Writes the label of the row, 18 px from the left edge. |
| 1835 | `                o.append(T(18, ty + 13, f"{r['rg'].txt()} ({r['rg'].n})", 10.5, MUTED, extra=TAB))` | Writes the range line under the label: `r['rg'].txt()`, and after it `r['rg'].n` in round brackets. That is the lowest and the highest rate of the row with 2 decimals, and the number of intervals. Example: the saved output of a build shows 461.61 to 464.29 GB/s for part L of the old read kernel [Ref5]. Line 275 asserts 6 intervals for it. So this line reads `461.61 to 464.29 (6)` for that row. |
| 1836 | `                for i, (nt, strong) in enumerate(note_lines(r["notes"])):` | Starts the loop over the note lines of the row. `strong` is true for a line of a note that starts with `!`. |
| 1837 | `                    o.append(T(18, ty + 13 * (i + 2), nt, 10.5, INK if strong else MUTED, weight=600 if strong else None))` | Writes one note line. A strong line is drawn in the colour `INK` and in bold type. Every other line is drawn in the grey colour `MUTED`. |
| 1838 | `                o.append(f'<line x1="{X0}" y1="{r["y"] + r["h"]}" x2="{X1}" y2="{r["y"] + r["h"]}" stroke="{GRID}" stroke-opacity="0.6"/>')` | Draws a thin line under the row, from `X0` to `X1`. |

### Function `panel`: the dots and their tooltips (lines 1839 to 1864)

| Line | Source | Explanation |
|---:|---|---|
| 1839 | `                for rec, x, yd, di in r["dots"]:` | Starts the loop over the dots of the row. `rec` is the record, `x` and `yd` are the place, and `di` is the number of the dot in the panel. |
| 1840 | `                    cell = "M" + "L".join(f"{cx_:.1f} {cy_:.1f}" for cx_, cy_ in cells[di][0]) + "Z"` | `cell`: the hover area of the dot as the text of an SVG path: `M`, then the corners of the polygon joined with `L`, then `Z`, which closes the outline. |
| 1841 | `                    kb = rec["kernel_before"]` | `kb`: the field `kernel_before` of the record: the kernel that was timed directly before in the same process. |
| 1842 | `                    if rec["part"] == "A" and rec["dataset"] == "A-3":` | Tests whether the record belongs to row A-3 of part A. |
| 1843 | `                        # row A-3 has no rounds: the number at the end of the tag counts the three repeats of the process` | Comment: row A-3 has no rounds. The number at the end of its tag counts the three repeats of the process. |
| 1844 | `                        where = f"process {rec['_fproc']} of the file (tag {rec['tag']}), interval {rec['interval'] + 1}"` | Row A-3: `where`, the text that names the interval in the tooltip, holds the number of the process inside its csv file (`_fproc`, set in line 349), the tag, and the interval number counted from 1. |
| 1845 | `                    elif rec["part"] == "A":` | Tests whether the record is any other part A record. |
| 1846 | `                        where = f"process {rec['_fproc']} of the file, round {rec['round']}, interval {rec['interval'] + 1}"` | Part A: `where` holds the number of the process inside its csv file, the round, and the interval number counted from 1. |
| 1847 | `                    else:` | Every other record is a bwx12 record: |
| 1848 | `                        after = ("no kernel ran before it" if kb.startswith("none") else` | `after`: a text about the kernel before. When the field starts with `none`, the text is `no kernel ran before it`. |
| 1849 | `                                 f"directly after {kb}" + ("" if kb in ("oldread", "read", "asmread") else " (another test loop of bwx12)"))` | Continues the expression of line 1848: in every other case the text is `directly after` with the name of that kernel. A kernel that is not `oldread`, `read` or `asmread` also gets the words `(another test loop of bwx12)`. |
| 1850 | `                        where = f"process {rec['tag']}, round {rec['round']}, position {rec['pos']}, {after}"` | bwx12: `where` holds the tag of the process, the round, the position and the text `after`. |
| 1851 | `                    tipname = ", ".join([r["name"]] + plain_notes(r["notes"], tooltip=True))` | `tipname`: the row name and the notes of the row as plain text, joined with commas. `plain_notes` is called with `tooltip=True`. So the notes that start with `~` are left out. |
| 1852 | `                    tip = (f"{tipname}: {kernel_name([rec])}, {where}: {f2(val(rec))} GB/s. "` | `tip`: the tooltip text of the dot. This line writes `tipname`, the kernel name (`kernel_name`, line 1537), `where`, and the rate of the interval: `f2(val(rec))`, the value of `val` rounded to 0.01 GB/s. Example: by section 3.3 of the facts sheet, the `read` interval of the process T72C1 in round 0, at position 1 and directly after `oldread`, gave 320.90 GB/s [Ref1]. |
| 1853 | `                           f"Row: {r['rg'].txt()} GB/s, n = {plural(r['rg'].n, 'interval')} / {plural(r['rg'].np, 'process')}. "` | Continues the text of line 1852: the range of the row in GB/s, and n as intervals and processes. |
| 1854 | `                           f"Source: {src([rec])}.")` | Continues the text: the source text of `src` (line 359), which names the csv file and the line of the interval row. For a bwx12 record it ends with the sentence that the rate is the sum of the 120 thread rows after that row. |
| 1855 | `                    # Both kinds of mark are 8.6 px across: the hollow one with its stroke, the filled one without a stroke on its edge.` | Comment: both kinds of mark are 8.6 px across. The hollow mark has this size with its outline. The filled mark has no outline on its edge. |
| 1856 | `                    # The filled mark has a surface-coloured ring of 0.6 px under it (r 4.9), which separates it from a dot that it overlaps.` | Comment, continued: the filled mark has a ring of 0.6 px in the background colour under it (radius 4.9 px). The ring separates it from a dot that it overlaps. |
| 1857 | `                    # Only the hover area takes the pointer, not the painted mark. So where two marks overlap, the nearer dot still answers.` | Comment, continued: only the hover area takes the pointer, not the painted mark. So where two marks overlap, the nearer dot still shows its tooltip. |
| 1858 | `                    o.append(f'<g class="pt"><title>{esc(tip)}</title><path d="{cell}" fill="{SURF}" fill-opacity="0"/><g pointer-events="none">'` | Writes the dot as an SVG group of the class `pt`: first the tooltip, then the hover area as a transparent path, then an inner group for the painted mark. `pointer-events="none"` on the inner group means that the mark does not take the pointer. |
| 1859 | `                             + (f'<circle class="mk ho" cx="{x:.1f}" cy="{yd:.1f}" r="3.4" fill="{SURF}" stroke="{color}" stroke-width="1.8"/>' if r["hollow"]` | Continues the group of line 1858: a row with `hollow` true (an 8000 MT/s row) gets a ring. It is a circle of the radius 3.4 px with the background colour inside and an outline of 1.8 px in the panel colour. |
| 1860 | `                                else f'<circle cx="{x:.1f}" cy="{yd:.1f}" r="4.9" fill="{SURF}"/><circle class="mk fi" cx="{x:.1f}" cy="{yd:.1f}" r="4.3" fill="{color}"/>') + "</g></g>")` | Continues the group: every other row (a 7200 MT/s row) gets a circle of the radius 4.9 px in the background colour, and on it a filled circle of the radius 4.3 px in the panel colour. Then both groups are closed. |
| 1861 | `    o.append("</svg>")` | Closes the `svg` element. |
| 1862 | `    return "\n".join(o)` | Joins the pieces with line breaks and returns the panel as one text. Ends the function `panel`. |

### `secs_txt`, `l_rows`, `band_title`, fixed notes, the blocks `P_OLD_BLOCKS` (lines 1865 to 1904)

| Line | Source | Explanation |
|---:|---|---|
| 1865 | `def secs_txt(recs):` | Starts the function `secs_txt`. It returns the interval length of a list of records as text, for example `6 s`. |
| 1866 | `    return f"{int(recs[0]['min_ms']) // 1000} s"` | Reads the field `min_ms` of the first record (the shortest length of one interval, in ms) and keeps the whole seconds. |
| 1869 | `def l_rows(pool):` | Starts the function `l_rows`. It returns the four rows L-1 to L-4 of figure 2 for one kernel. `pool` is `B_L_OLD` or `B_L_ASM` (lines 291 to 292). For each of the four rows it holds the `oldread` records at position 0, or the `asmread` records at position 1. |
| 1870 | `    rows = []` | `rows`: the result list. |
| 1871 | `    for d in LPOOL:` | Starts the loop over the four datasets of `LPOOL` (line 268). |
| 1872 | `        rows.append(p_row(d, pool[d], True, label=f"{d} ({secs_txt(pool[d])})"))` | Adds one `p_row` with hollow markers. The label is the row name with the interval length, for example `L-1 (6 s)`. No band is passed. So these rows get no note. |
| 1873 | `    return rows` | Returns the four rows. |
| 1876 | `def band_title(what, rg, n):` | Starts the function `band_title`. It returns the tooltip text of a grey band. |
| 1877 | `    files = ", ".join(sorted({f"{r['folder']}/{r['file']}" for r in rg.recs}))` | `files`: the csv files of the records of the band, each with its folder, sorted and joined with commas. The set keeps each file once. |
| 1878 | `    return f"Grey band: {what}. {rg.txt()} GB/s, n = {n}. Source: {files}."` | Returns the text: what the band shows (`what`), its range `rg.txt()` in GB/s, the text of n, and the source files. |
| 1881 | `F72_NOTES = ["earlier run of the same boot,\|not part of the rerun"]      # "\|" = line break inside one note` | `F72_NOTES`: the fixed note of the rows of F72d12. It says that F72d12 is an earlier run of the same boot and not part of the rerun. Comment at the end of the line: the `\|` is a line break inside one note. |
| 1882 | `IN_PLACE_2 = ["asmread in place of", "the new read kernel"]              # group label in two lines: it stays inside the label column` | `IN_PLACE_2`: a group label in two lines. Comment at the end of the line: in two lines the label stays inside the label column. |
| 1883 | `need(" ".join(IN_PLACE_2) == IN_PLACE, "figure 2: the group label is not the label of figure 1")` | Hard assertion: the script stops unless the two lines, joined with a space, equal the label `IN_PLACE` of figure 1 (line 1561). |
| 1884 | `need({(r["round"], r["pos"], r["file"]) for r in C_ASM_AO} == {(1, 0, "crev.csv")}, "part C, asmread after oldread: not crev, round 1, position 0")` | Hard assertion: the script stops unless both records of `C_ASM_AO` (part C, asmread directly after oldread, line 288) come from `crev.csv`, round 1, position 0. The order crev times asmread, read, oldread. So asmread at position 0 of round 1 follows oldread at position 2 of round 0. |
| 1885 | `CI_NOTES = ["added after the first\|numbers were seen"]` | `CI_NOTES`: the fixed note of the rows of control I. It says that control I was added after the first numbers were seen. |
| 1886 | `P_OLD_BLOCKS = [` | `P_OLD_BLOCKS`: the blocks of the panel `Old read kernel`, a list of two dictionaries. |
| 1887 | `    dict(title="0.5 s measurements, bw_old read", band=rPA_old,` | First block of the list: the 0.5 s measurements of part A, binary `bw_old`, kernel `read`. Its grey band is `rPA_old` (line 463): the range of the 21 intervals of the rows A-1 to A-3 (`P_A_OLD`, line 304). |
| 1888 | `         band_txt=["grey band = 8000 MT/s rows A-1 to A-3:", f"{rPA_old.txt()} GB/s, n = {n8000(P_A_OLD)}"],` | `band_txt`: the two text lines under the block title. They say what the band is, and they give its range and its n. `n8000` (line 401) writes n as intervals / processes / 1 boot. |
| 1889 | `         band_title=band_title("lowest to highest interval of the 8000 MT/s rows A-1 to A-3, bw_old read", rPA_old, n8000(P_A_OLD)),` | `band_title`: the tooltip text of the band (line 1876). |
| 1890 | `         groups=[dict(title="8000 MT/s", band=True, rows=[p_row(d, B_A_OLD[d], True) for d in APOOL]),` | The group `8000 MT/s`: one row for each of A-1, A-2 and A-3 with the records `B_A_OLD[d]` (line 298). Hollow markers, no note. |
| 1891 | `                 dict(title="7200 MT/s, part A", band=True, rows=[p_row(f"Part A, session {s_}", [r for r in A_OLD if r["session"] == s_], False, label=f"Session {s_} (T72A{s_})", band=rPA_old)` | The group `7200 MT/s, part A`: one row per session with the records of `A_OLD` of that session. A session has 6 such intervals from 2 processes (round 1 and round 2). The label holds the session number and the folder tag. `band=rPA_old` compares each row with the band. |
| 1892 | `                                                                  for s_ in (1, 2, 3)])]),` | The loop of the list of line 1891: the sessions 1, 2 and 3. The line also closes the group list and the first block. |
| 1893 | `    dict(title="6 s measurements, bwx12 oldread", band=rPL_old,` | Second block: the 6 s measurements of bwx12, kernel `oldread`. Its grey band is `rPL_old` (line 466): the range of the 11 `oldread` intervals at position 0 of the rows L-1 to L-4 (`P_L_OLD`, line 296). |
| 1894 | `         band_txt=["grey band = 8000 MT/s rows L-1 to L-4:", f"{rPL_old.txt()} GB/s, n = {n8000(P_L_OLD)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],` | `band_txt`: three text lines. The first two say what the band is, and they give its range and its n. The third states that the rows L-2 to L-4 are 4 s measurements with other hardware events counted. |
| 1895 | `         band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, oldread at position 0", rPL_old, n8000(P_L_OLD)),` | `band_title`: the tooltip text of the band. |
| 1896 | `         groups=[dict(title="8000 MT/s", band=True, rows=l_rows(B_L_OLD)),` | The group `8000 MT/s`: the four rows of `l_rows(B_L_OLD)`. |
| 1897 | `                 dict(title="7200 MT/s", band=True, rows=[` | The group `7200 MT/s`: four rows, each compared with the band (lines 1898 to 1901). |
| 1898 | `                     p_row("F72d12", F_OLD, False, F72_NOTES, band=rPL_old),` | Row F72d12: the 2 `oldread` intervals of `F_OLD`, with the note `F72_NOTES`. |
| 1899 | `                     p_row("Part L", L_OLD, False, label="Part L (3 sessions)", band=rPL_old, more=[f"!medians: {f2(abs(L_OLD_MED))} GB/s lower"]),` | Row part L: the 6 intervals of `L_OLD`. `more` gives it a second bold note: the difference of the two medians `L_OLD_MED` (line 490), without its sign, rounded to 0.01 GB/s. The saved output of a build shows the values of both notes of this row: -1.24 GB/s for the nearest ends and 6.27 GB/s for the medians [Ref5]. So the notes read `1.24 GB/s lower`, `(left of the band)` and `medians: 6.27 GB/s lower`. |
| 1900 | `                     p_row("Part C", C_OLD, False, label="Part C (4 processes)", band=rPL_old),` | Row part C: all 8 `oldread` intervals of `C_OLD`, at position 0 and at position 2. |
| 1901 | `                     p_row("Control I", I_OLD, False, CI_NOTES, band=rPL_old)])]),` | Row control I: the 4 intervals of `I_OLD`, with the note `CI_NOTES`. The line also closes the row list, the group list and the second block. |
| 1902 | `]` | Ends the list `P_OLD_BLOCKS`. |

### Function `a_new_block`, and the blocks `P_NEW_BLOCKS` of the panel for the load-only loop (lines 1905 to 1937)

| Line | Source | Explanation |
|---:|---|---|
| 1905 | `def a_new_block(rnd):` | Starts the function `a_new_block`. It returns the block of figure 2 for the kernel `read` of `bw_new` in one round `rnd` of part A. |
| 1906 | `    v = A_V3[rnd]` | `v`: the entry of `A_V3` for the round (lines 509 to 516). It holds two ranges of `bw_new` read. `r7` is the range of the 3 intervals of session 1 at 7200 MT/s. `r8` is the range of the 6 intervals of the rows A-1 and A-2 at 8000 MT/s. |
| 1907 | `    rows8 = [p_row(f"{d}, round {rnd}", [r for r in B_A_NEW[d] if r["round"] == rnd], True, label=d) for d in ("A-1", "A-2")]` | `rows8`: one row for A-1 and one for A-2, each with the 3 intervals of that round (1 process). Hollow markers. The label is the name of the dataset. |
| 1908 | `    rows7 = []` | `rows7`: the list of the 7200 MT/s rows. It starts empty. |
| 1909 | `    for s_ in (1, 2, 3):` | Starts the loop over the three sessions. |
| 1910 | `        rows7.append(p_row(f"Part A, session {s_}, round {rnd}", [r for r in A_NEW if r["session"] == s_ and r["round"] == rnd], False,` | Adds one row per session with the 3 intervals of `A_NEW` of that session and round. Filled markers. |
| 1911 | `                           [] if s_ == 1 else ["used for Q1 only (rule V3)"], label=f"Session {s_} (T72A{s_})", band=v["r8"] if s_ == 1 else None))` | Continues the call of line 1910. The row of session 1 has no fixed note and gets `band`. The rows of sessions 2 and 3 get the note `used for Q1 only (rule V3)` and no band. So only session 1 is compared with the band. The reading notes of the page state how the sessions differ (line 2689): sessions 2 and 3 started 5 s after a 120-thread process of part C, and session 1 and the rows A-1 and A-2 did not. Line 2486 stops the script unless the part A steps of sessions 2 and 3 started 5 s after a part C process. |
| 1912 | `    return dict(title=f"0.5 s measurements, bw_new read, round {rnd}", band=v["r8"],` | Returns the block. Its title names the 0.5 s measurements, `bw_new` read and the round. Its grey band is `r8`. |
| 1913 | `                band_txt=[f"grey band = 8000 MT/s rows A-1 and A-2 of round {rnd}:", f"{v['r8'].txt()} GB/s, n = {n8000(v['r8'].recs)}"],` | `band_txt`: two text lines. They say that the band holds the 8000 MT/s rows A-1 and A-2 of this round, and they give its range and its n. |
| 1914 | `                band_title=band_title(f"lowest to highest interval of the 8000 MT/s rows A-1 and A-2, bw_new read, round {rnd}", v["r8"], n8000(v["r8"].recs)),` | `band_title`: the tooltip text of the band (line 1876). |
| 1915 | `                groups=[dict(title="8000 MT/s", band=True, rows=rows8), dict(title="7200 MT/s, part A", band=True, rows=rows7)])` | The two groups of the block: `8000 MT/s` with `rows8`, and `7200 MT/s, part A` with `rows7`. |
| 1918 | `P_NEW_BLOCKS = [` | `P_NEW_BLOCKS`: the blocks of the panel `Load-only loop`, a list of three dictionaries. |
| 1919 | `    dict(title="6 s measurements, bwx12", band=rPL_asm,` | First block: the 6 s measurements of bwx12. Its grey band is `rPL_asm` (line 466): the range of the 11 `asmread` intervals at position 1 of the rows L-1 to L-4 (`P_L_ASM`, line 297). |
| 1920 | `         band_txt=["grey band = 8000 MT/s rows L-1 to L-4, asmread:", f"{rPL_asm.txt()} GB/s, n = {n8000(P_L_ASM)}", "(L-2 to L-4: 4 s measurements, other hardware events counted)"],` | `band_txt`: three text lines. The first two say what the band is, and they give its range and its n. The third states that the rows L-2 to L-4 are 4 s measurements with other hardware events counted. |
| 1921 | `         band_title=band_title("lowest to highest interval of the 8000 MT/s rows L-1 to L-4, asmread at position 1, directly after oldread", rPL_asm, n8000(P_L_ASM)),` | `band_title`: the tooltip text of the band. It says that the band holds `asmread` at position 1, directly after `oldread`. |
| 1922 | `         groups=[dict(title="8000 MT/s", sub=IN_PLACE_2, band=True, rows=l_rows(B_L_ASM)),` | The group `8000 MT/s`: the four rows of `l_rows(B_L_ASM)`. The sub-title `IN_PLACE_2` says that `asmread` stands in place of the new read kernel. |
| 1923 | `                 dict(title="7200 MT/s", sub=IN_PLACE_2, band=True, rows=[` | The group `7200 MT/s`, with the same sub-title: four rows, each compared with the band (lines 1924 to 1927). |
| 1924 | `                     p_row("F72d12", F_ASM, False, F72_NOTES, band=rPL_asm),` | Row F72d12: the 2 `asmread` intervals of `F_ASM`. |
| 1925 | `                     p_row("Part L", L_ASM, False, label="Part L (3 sessions)", band=rPL_asm),` | Row part L: the 6 `asmread` intervals of `L_ASM`. |
| 1926 | `                     p_row("Part C, asmread directly after oldread (crev, round 1, position 0)", C_ASM_AO, False, ["~asmread after oldread"], label="Part C (crev, round 1)", band=rPL_asm),` | Row part C, asmread directly after oldread: the 2 intervals of `C_ASM_AO` (order crev, round 1, position 0). The note that starts with `~` repeats a part of the row name under the short label. |
| 1927 | `                     p_row("Control I", I_ASM, False, CI_NOTES, band=rPL_asm)]),` | Row control I: the 4 `asmread` intervals of `I_ASM`. The line also closes this group. |
| 1928 | `                 dict(title="7200 MT/s, part C", sub=["no 8000 MT/s row of", "this kind (no band)"], band=False, rows=[` | The group `7200 MT/s, part C` with `band=False`: four rows without a comparison (lines 1929 to 1932). Its sub-title gives the reason: no 8000 MT/s row of this kind exists, so the group has no band. |
| 1929 | `                     p_row("Part C, read directly after oldread", C_READ_AO, False, ["~new read kernel,\|after oldread"], label="Part C, read"),` | Row of the bwx12 kernel `read` (the new read kernel) directly after `oldread`: the 4 intervals of `C_READ_AO`. |
| 1930 | `                     p_row("Part C, read directly after asmread", C_READ_AA, False, ["~new read kernel,\|after asmread"], label="Part C, read"),` | Row of the kernel `read` directly after `asmread`: the 4 intervals of `C_READ_AA`. |
| 1931 | `                     p_row("Part C, asmread directly after read", C_ASM_AR, False, ["~after read"], label="Part C, asmread"),` | Row of `asmread` directly after `read`: the 4 intervals of `C_ASM_AR`. |
| 1932 | `                     p_row("Part C, asmread as first interval of the process", C_ASM_FI, False, ["~first interval of the process"], label="Part C, asmread")])]),` | Row of `asmread` as the first interval of a process: the 2 intervals of `C_ASM_FI`. The line also closes this group and the first block. |
| 1933 | `    a_new_block(1), a_new_block(2),` | Adds the two blocks of `a_new_block`, for round 1 and for round 2. |
| 1934 | `]` | Ends the list `P_NEW_BLOCKS`. |
| 1935 | `P_OLD_BLOCKS.reverse()` | Reverses the order of the two blocks of `P_OLD_BLOCKS`. The 6 s block of bwx12 then comes first in both panels. |

### `panel_rows`, and the assertions for the caption of figure 2 (lines 1938 to 1962)

| Line | Source | Explanation |
|---:|---|---|
| 1938 | `def panel_rows(blocks, band_only=True):` | Starts the function `panel_rows`. It lists the rows of a panel. |
| 1939 | `    return [(b, g, r) for b in blocks for g in b["groups"] for r in g["rows"] if g["band"] or not band_only]` | Returns one entry (block, group, row) per row of a list of blocks. By default it leaves out the rows of a group whose `band` flag is false. With `band_only=False` it returns every row. |
| 1942 | `# facts that the takeaway line of figure 2 states: checked here, so the sentence cannot go stale` | Comment: the next lines check the facts that the bold first part of the caption of figure 2 states (line 2749). After the figure number this part holds two sentences. So a change of the data that makes one of them false stops the script. |
| 1943 | `OLD_7200_BELOW = [r["name"] for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"] and not r["rg"].overlaps(b["band"])]` | `OLD_7200_BELOW`: the names of the 7200 MT/s rows (not hollow) of the panel `Old read kernel` whose range does not overlap the band of their block (`overlaps`, line 207). |
| 1944 | `need(OLD_7200_BELOW == ["Part L"], f"figure 2, old read: the rows outside the band are {OLD_7200_BELOW}")` | Hard assertion: the script stops unless this list holds only `Part L`. |
| 1945 | `# every 7200 MT/s row of the panel "Old read kernel" is compared with its band: each one carries the bold text with its place` | Comment: every 7200 MT/s row of the panel `Old read kernel` is compared with its band. Each one carries the bold text with its place. |
| 1946 | `OLD_CMP = [r for b, g, r in panel_rows(P_OLD_BLOCKS) if not r["hollow"]]` | `OLD_CMP`: all 7200 MT/s rows of that panel. |
| 1947 | `need(len(OLD_CMP) == 7 and all(any(n.startswith("!") for n in r["notes"]) for r in OLD_CMP), "figure 2, old read: a 7200 MT/s row has no bold text with its place relative to the band")` | Hard assertion: the script stops unless these are 7 rows, and each one has a note that starts with `!`, with its place relative to the band. The 7 rows are the 3 sessions of part A, F72d12, part L, part C and control I. |
| 1948 | `NEW_CMP = [(b, r) for b, g, r in panel_rows(P_NEW_BLOCKS) if not r["hollow"] and any(n.startswith("!") for n in r["notes"])]   # rows that are compared with a band` | `NEW_CMP`: the 7200 MT/s rows of the panel `Load-only loop` that have a note that starts with `!`, each with its block. Comment at the end of the line: these are the rows that are compared with a band. |
| 1949 | `NEW_7200_IN = [r["name"] for b, r in NEW_CMP if r["rg"].overlaps(b["band"])]` | `NEW_7200_IN`: the names of the rows of `NEW_CMP` whose range overlaps the band. |
| 1950 | `NEW_7200_RIGHT = [r["name"] for b, r in NEW_CMP if r["rg"].lo > b["band"].hi]` | `NEW_7200_RIGHT`: the names of the rows of `NEW_CMP` whose lowest rate is above the highest rate of the band. |
| 1951 | `need(NEW_7200_IN == ["F72d12"] and len(NEW_7200_RIGHT) == 5 and len(NEW_CMP) == 6, f"figure 2, load-only: compared rows inside the band {NEW_7200_IN}, right of it {len(NEW_7200_RIGHT)}")` | Hard assertion: the script stops unless `NEW_CMP` has 6 rows, only F72d12 overlaps its band, and 5 rows lie above their band. |
| 1952 | `need(sorted(NEW_7200_RIGHT) == sorted(["Part L", "Part C, asmread directly after oldread (crev, round 1, position 0)", "Control I", "Part A, session 1, round 1", "Part A, session 1, round 2"]),` | Hard assertion: the script stops unless these 5 rows are part L, part C asmread directly after oldread, control I, and session 1 of part A in round 1 and in round 2. |
| 1953 | `     f"figure 2, load-only: the rows right of their band are not the five rows that the caption names: {NEW_7200_RIGHT}")` | Continues the call of line 1952: the message. It prints the rows that the script found. |
| 1954 | `F2_RIGHT_TXT = ("The rows to the right of their band are part L, the part C row &quot;asmread after oldread&quot;, session 1 of part A in both rounds, "` | `F2_RIGHT_TXT`: a sentence for the caption of figure 2 (line 2749). It names the rows to the right of their band: part L, the part C row of asmread after oldread, and session 1 of part A in both rounds. |
| 1955 | `                "and control I (added after the first numbers were seen).")` | Continues the text of line 1954: the fifth row, control I, with its label `added after the first numbers were seen`. |
| 1956 | `allv_old = [v for b, g, r in panel_rows(P_OLD_BLOCKS, False) for v in r["rg"].v]` | `allv_old`: the rates of all rows of the panel `Old read kernel`. |
| 1957 | `allv_new = [v for b, g, r in panel_rows(P_NEW_BLOCKS, False) for v in r["rg"].v]` | `allv_new`: the rates of all rows of the panel `Load-only loop`. `panel_rows` is called with `False` in both lines. So the part C rows without a band are included. |
| 1958 | `OLD_AX, NEW_AX = (458, 476), (276, 340)` | `OLD_AX` and `NEW_AX`: the axis limits of the two panels: 458 to 476 GB/s and 276 to 340 GB/s. |
| 1959 | `need(OLD_AX[0] < min(allv_old) and max(allv_old) < OLD_AX[1] and NEW_AX[0] < min(allv_new) and max(allv_new) < NEW_AX[1], "figure 2: a value lies outside an axis")` | Hard assertion: the script stops unless every rate lies between the limits of its panel. |
| 1960 | `N_DOTS = len(allv_old) + len(allv_new)` | `N_DOTS`: the number of dots of figure 2: the number of rates of both panels. The rows of the two panels hold the record groups that `USED` joins (lines 306 to 307), each group once. So by the record counts that the script asserts (lines 272 to 304, line 447), each record of `USED` is exactly one dot. The saved output of a build shows 139 dots and 139 records in `USED` [Ref5]. |

### The legends of the two figures (lines 1963 to 1990)

| Line | Source | Explanation |
|---:|---|---|
| 1963 | `def legend(items):` | Starts the function `legend`. It returns the HTML of a figure legend from a list of entries. Each entry is a symbol and a text. |
| 1964 | `    return '<div class="legend">' + "".join(f'<span class="li">{sw}<span>{txt}</span></span>' for sw, txt in items) + "</div>"` | Returns a `div` element of the class `legend`. Each entry becomes a `span` of the class `li` that holds the symbol `sw` and the text `txt`. |
| 1967 | `def sw_dot(color, hollow=False):` | Starts the function `sw_dot`. It returns a small SVG dot for a legend entry. |
| 1968 | `    c = (f'<circle cx="8" cy="8" r="4.6" fill="{SURF}" stroke="{color}" stroke-width="2.2"/>' if hollow else f'<circle cx="8" cy="8" r="5.5" fill="{color}"/>')` | `c`: the circle. When `hollow` is true, it is a ring with the background colour inside and an outline of 2.2 px in the given colour. If not, it is a filled circle of the radius 5.5 px. |
| 1969 | `    return f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">{c}</svg>'` | Returns the circle inside an `svg` element of 16 by 16 px. `aria-hidden="true"` tells a screen reader to skip the symbol. |
| 1972 | `SW_WHISK = f'<svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"><path d="M3 4.5V11.5M19 4.5V11.5M3 8H19" stroke="{INK}" stroke-width="1.1" fill="none"/></svg>'` | `SW_WHISK`: the legend symbol of the range bar of figure 1: two short vertical lines with a horizontal line between them, in the colour `INK`. |
| 1973 | `SW_BAND = f'<svg width="22" height="16" viewBox="0 0 22 16" aria-hidden="true"><rect x="1" y="1" width="20" height="14" fill="{BAND}"/><path d="M1 1V15M21 1V15" stroke="{BAND_EDGE}"/></svg>'` | `SW_BAND`: the legend symbol of the grey band of figure 2: a rectangle in the colour `BAND` with a darker line at its left edge and at its right edge. |
| 1974 | `SW_PCT = f'<svg width="30" height="16" viewBox="0 0 30 16" aria-hidden="true"><line x1="1" y1="11" x2="29" y2="11" stroke="{LINK}" stroke-width="1.5"/><text x="15" y="8" font-size="9" text-anchor="middle" fill="{INK}">%</text></svg>'` | `SW_PCT`: the legend symbol of the drop text of figure 1: a line in the grey colour `LINK` with a percent sign above its middle. |
| 1975 | `LEG1 = legend([` | `LEG1`: the legend of figure 1, with six entries. |
| 1976 | `    (sw_dot(BLUE), "old read kernel, named oldread in bwx12 (median of the row)"),` | First entry: a filled blue dot. It stands for the old read kernel, named `oldread` in bwx12. The text adds that a dot is the median of its row. |
| 1977 | `    (sw_dot(ORANGE), "load-only loop: new read kernel, or asmread where the row says so"),` | Second entry: a filled orange dot. It stands for the load-only loop: the new read kernel, or `asmread` where the row says so. |
| 1978 | `    (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),` | Third entry: a hollow grey dot. A hollow marker is an 8000 MT/s row. |
| 1979 | `    (sw_dot(MUTED), "filled marker: 7200 MT/s"),` | Fourth entry: a filled grey dot. A filled marker is a 7200 MT/s row. |
| 1980 | `    (SW_WHISK, "lowest to highest interval of the row, to scale (often narrower than the dot)"),` | Fifth entry: the range bar. It runs from the lowest to the highest interval of the row, to scale. The text adds that the bar is often narrower than the dot. |
| 1981 | `    (SW_PCT, "percent on the line: drop of the load-only loop below the old read kernel. A range gives the lowest and the highest pair of the row"),` | Sixth entry: the percent text on the line. It is the drop of the load-only loop below the old read kernel. A range gives the lowest and the highest pair of the row. |
| 1982 | `])` | Ends the list of `LEG1`. |
| 1983 | `LEG2 = legend([` | `LEG2`: the legend of figure 2, with five entries. |
| 1984 | `    (sw_dot(BLUE), "old read kernel, one dot per interval"),` | First entry: a filled blue dot. In figure 2 it is one interval of the old read kernel. |
| 1985 | `    (sw_dot(ORANGE), "load-only loop, one dot per interval"),` | Second entry: a filled orange dot. It is one interval of the load-only loop. |
| 1986 | `    (sw_dot(MUTED, True), "hollow marker: 8000 MT/s"),` | Third entry: a hollow grey dot for 8000 MT/s. |
| 1987 | `    (sw_dot(MUTED), "filled marker: 7200 MT/s"),` | Fourth entry: a filled grey dot for 7200 MT/s. |
| 1988 | `    (SW_BAND, "grey band: lowest to highest interval of the 8000 MT/s rows of the block"),` | Fifth entry: the grey band. It runs from the lowest to the highest interval of the 8000 MT/s rows of the block. |
| 1989 | `])` | Ends the list of `LEG2`. |

### `lab`, `only`, and `q1_table`: Table 1, the drop per part (lines 1991 to 2047)

| Line | Source | Explanation |
|---:|---|---|
| 1991 | `# ------------------------------------------------------------------ tables` | Comment: a section mark. The code of the tables starts here. |
| 1992 | `def lab(main, *subs):` | Starts the function `lab`. It returns a row label for a table cell. |
| 1993 | `    """A row label: the name, and under it its notes in small type (no semicolon between label parts)."""` | Comment: the documentation text. The label is the name, and under it its notes in small type. No semicolon stands between the parts of a label. |
| 1994 | `    return main + "".join("<br>" + small(x) for x in subs)` | Returns the name `main`, and after it each note on a new line (`<br>`) in small type (`small`, line 1515). |
| 1997 | `def only(values, what):` | Starts the function `only`. It returns the one distinct value of a list. `q1_table` calls it for a position or a kernel order that must be the same in all records of a group. |
| 1998 | `    vs = sorted(set(values))` | `vs`: the distinct values, sorted. |
| 1999 | `    need(len(vs) == 1, f"{what}: more than one value {vs}")` | Hard assertion: the script stops unless the list holds exactly one distinct value. The message names `what` and the values. |
| 2000 | `    return vs[0]` | Returns that value. |
| 2003 | `def q1_table():` | Starts the function `q1_table`. It builds Table 1 of the page, the drop per part. `build` calls it in line 2736. |
| 2004 | `    def row(label, key, n):` | Starts the inner function `row`. It builds one table row from an entry of `Q1` (lines 430 to 441). `key` names the entry, and `n` is the text of n. |
| 2005 | `        ds = Q1[key]["drops"]` | `ds`: the drops of the pairs of this entry, in percent (`drops_of`, line 421). |
| 2006 | `        return [label, f1(min(ds)), f1(max(ds)), Q1[key]["old"].txt(), Q1[key]["new"].txt(), n]` | Returns the 6 cells of the row: the label, the lowest and the highest drop with 1 decimal (`f1`), the range of the old-kernel intervals of the pairs, the range of the load-only intervals of the pairs, and n. |
| 2008 | `    def med_rng(pairs, which, rnd=None):` | Starts the inner function `med_rng`. It is used for the two part A rows only. `pairs` is `A_PAIRS` or `A8_PAIRS` (lines 451 to 455), with one entry per session (or 8000 MT/s row) and round. An entry holds the range of the 3 intervals of the `bw_old` process (`old`) and of the `bw_new` process (`new`). |
| 2009 | `        ms = [p[which].med for (_, r_), p in pairs.items() if rnd is None or r_ == rnd]` | `ms`: the median of each process of the kind `which`. With `rnd`, only the processes of that round are taken. |
| 2010 | `        return f"{f2(min(ms))} to {f2(max(ms))}"` | Returns the lowest and the highest of these medians with 2 decimals. |
| 2012 | `    def per_round(pairs):` | Starts the inner function `per_round`. It returns the cell text for `bw_new` read. |
| 2013 | `        return f"round 1: {med_rng(pairs, 'new', 1)}<br>round 2: {med_rng(pairs, 'new', 2)}<br>{small('(medians of the processes)')}"` | The text holds the range of the process medians of round 1, then on a new line that of round 2, then a small line that says that these are medians of the processes. |
| 2014 | `    a8 = Q1["A8"]["drops"]` | `a8`: the drops of the rows A-1 and A-2 at 8000 MT/s (`Q1["A8"]`, line 457). |
| 2015 | `    pos_ao, pos_aa, pos_l = only((r["pos"] for r in C_READ_AO), "position"), only((r["pos"] for r in C_READ_AA), "position"), only((r["pos"] for r in L_ASM), "position")` | `pos_ao`, `pos_aa`: the position of the kernel `read` in the two part C groups. `pos_l`: the position of `asmread` in part L. `only` stops the script when the records of a group hold more than one position. Section 3.3 of the facts sheet gives position 1 for `read` in both orders [Ref1]. |
| 2016 | `    ord_ao, ord_aa = only((r["file"][:-4] for r in C_READ_AO), "order"), only((r["file"][:-4] for r in C_READ_AA), "order")` | `ord_ao`, `ord_aa`: the kernel order of the two part C groups. It is the name of the csv file without `.csv` (`cfwd` or `crev`). |
| 2018 | `    def where(recs):` | Starts the inner function `where`. It names the sessions of the processes of a group of records. |
| 2019 | `        """Sessions of the processes of one kernel order of part C."""` | Comment: the documentation text. The function gives the sessions of the processes of one kernel order of part C. |
| 2020 | `        named = sorted({r["session"] for r in recs if r["session"] is not None})` | `named`: the session numbers of the records, sorted, without the records that have no session. |
| 2021 | `        extra = len({r["proc_key"] for r in recs if r["session"] is None})` | `extra`: the number of processes without a session number. |
| 2022 | `        return ("session " if len(named) == 1 else "sessions ") + " and ".join(str(x) for x in named) + (" and the extra process" if extra else "")` | Returns the text, for example `sessions 1 and 3`. When `extra` is not 0, the text ends with `and the extra process`. |
| 2023 | `    need(Rg(C_READ_AO).np == 2 and Rg(C_READ_AA).np == 2, "part C: not 2 processes per kernel order")` | Hard assertion: the script stops unless each kernel order of part C has 2 processes. |
| 2024 | `    rows = [` | `rows`: the list of the table rows. A text entry becomes a title row that spans all columns. A list entry becomes a row with 6 cells. |
| 2025 | `        "7200 MT/s, the planned rerun",` | Title row of the first group: the planned rerun at 7200 MT/s. |
| 2026 | `        row(f"<b>Part C</b>: kernel read (the new read kernel) at position {pos_ao}, directly after oldread (order {ord_ao}), processes T72C1 and T72C3 {ref('T72C1', 'T72C3')}", "C_ao", n7200(Q1["C_ao"]["new"].recs, 4)),` | Row of part C, kernel `read` directly after `oldread`: the entry `Q1["C_ao"]`. The label holds the position and the order from the records. The process tags T72C1 and T72C3 are typed, and no assertion compares them with the records. Section 3.3 of the facts sheet names these two processes for this group [Ref1]. The number of pairs, 4, is typed here for the text of n (`n7200`, line 381). Line 438 asserts the same number. The saved output of a build shows drops of 30.5 % to 31.2 % [Ref5]. |
| 2027 | `        row(f"<b>Part C</b>: kernel read (the new read kernel) at position {pos_aa}, directly after asmread (order {ord_aa}), processes T72C2 and T72C4 {ref('T72C2', 'T72C4')}", "C_aa", n7200(Q1["C_aa"]["new"].recs, 4)),` | Row of part C, kernel `read` directly after `asmread`: the entry `Q1["C_aa"]`. The tags T72C2 and T72C4 and the number of pairs, 4, are typed too. Section 3.3 of the facts sheet names these two processes for this group [Ref1]. The saved output of a build shows drops of 29.7 % to 31.1 % [Ref5]. |
| 2028 | `        row(f"<b>Part L</b>: asmread (in place of the new read kernel) at position {pos_l}, directly after oldread {ref('L1', 'L2', 'L3')}", "L", n7200(Q1["L"]["new"].recs, 6)),` | Row of part L, `asmread` against `oldread`: the entry `Q1["L"]`. The number of pairs, 6, is typed for the text of n, and line 438 asserts it. The saved output of a build shows drops of 29.2 % to 30.5 % [Ref5]. |
| 2029 | `        [f"<b>Part A</b>: bw_new read against bw_old read, 0.5 s, whole-pass stop. Drop between the medians of the two processes. Less exact than parts L and C {ref('A1', 'A2', 'A3')}",` | Row of part A, first cell: the label. It names the two binaries, the 0.5 s measurements and the whole-pass stop. It says that the drop is taken between the medians of the two processes, and that part A is less exact than parts L and C. |
| 2030 | `         f1(min(Q1["A"]["drops"])), f1(max(Q1["A"]["drops"])),` | Cells 2 and 3: the lowest and the highest of the 6 drops of `Q1["A"]`. Each one is the drop between the median of the `bw_old` process and the median of the `bw_new` process of one session and round (`a_pair`, line 444). The saved output of a build shows 28.5 % to 31.8 % [Ref5]. |
| 2031 | `         f"{med_rng(A_PAIRS, 'old')}<br>{small(f'(medians of the {rA_old.np} processes)')}", per_round(A_PAIRS),` | Cells 4 and 5 show process medians, not ranges of intervals: `med_rng` over the 6 `bw_old` processes, and `per_round` for `bw_new`. |
| 2032 | `         f"{len(A_PAIRS)} pairs of process medians / {plural(rA_old.np + Rg(A_NEW).np, 'process')} / 3 sessions / 1 boot"],` | Cell 6: the text of n: the number of pairs of process medians, the number of processes of both binaries, 3 sessions and 1 boot. |
| 2033 | `        "7200 MT/s, same boot, not part of the planned rerun (own rows in every comparison with 8000 MT/s)",` | Title row of the second group: the rows of the same boot that are not part of the planned rerun. |
| 2034 | `        row(f"<b>Control I</b> (added after the first numbers were seen, not part of the plan fixed before the run): asmread (in place of the new read kernel), idle start {ref('T72I1', 'T72I2')}", "I", n7200(Q1["I"]["new"].recs, 4)),` | Row of control I: the entry `Q1["I"]`, with 4 pairs. The saved output of a build shows drops of 31.9 % to 32.8 % [Ref5]. |
| 2035 | `        row("<b>F72d12</b> (earlier run of the same boot at " + hm(F_OLD[0]["launch_utc"]) + f", not part of the rerun): asmread (in place of the new read kernel) {ref('F72')}", "F", n7200(Q1["F"]["new"].recs, 2)),` | Row of F72d12: the entry `Q1["F"]`, with 2 pairs. The label holds the launch time from `hm` (line 377). The saved output of a build shows a drop of 35.4 % for both pairs [Ref5]. |
| 2036 | `        "8000 MT/s, for context only (same computation)",` | Title row of the third group: rows at 8000 MT/s, for context only, with the same computation. |
| 2037 | `        row(f"<b>L-1</b>: asmread (in place of the new read kernel) directly after oldread {ref('L-1')}", "L1", n8000(Q1["L1"]["new"].recs, 2)),` | Row of L-1: the entry `Q1["L1"]`, with 2 pairs. `n8000` (line 401) writes its n. Of the rows L-1 to L-4, `Q1` holds pairs of row L-1 only (line 436). So Table 1 has no row for L-2 to L-4. Computed with the formula of line 418 from the fields `GBps` of the records in `facts.json`, the two drops of L-1 are 35.9 % and 36.1 % [Ref2]. |
| 2038 | `        [f"<b>A-1, A-2</b>: bw_new read against bw_old read, drop between the medians of the two processes {ref('A-1', 'A-2')}", f1(min(a8)), f1(max(a8)),` | Row of A-1 and A-2: the label, and the lowest and the highest of the drops `a8`. Computed in the same way from the records in `facts.json`, the 4 drops span 33.1 % to 39.8 % [Ref2]. |
| 2039 | `         f"{med_rng(A8_PAIRS, 'old')}<br>{small(f'(medians of the {len(A8_PAIRS)} processes)')}", per_round(A8_PAIRS),` | Cells 4 and 5: the process medians of `A8_PAIRS`, as in line 2031. |
| 2040 | `         f"{len(A8_PAIRS)} pairs of process medians / {plural(Rg(B_A_OLD['A-1'] + B_A_OLD['A-2'] + B_A_NEW['A-1'] + B_A_NEW['A-2']).np, 'process')} / 1 boot"],` | Cell 6: the text of n: the number of pairs of process medians, the number of processes of both binaries in A-1 and A-2, and 1 boot. |
| 2041 | `        "Note",` | Title row of the last group: `Note`. |
| 2042 | `        f'<span class="tn">Part C: each kernel order has 2 processes. Order {ord_ao} ran in {where(C_READ_AO)}. Order {ord_aa} ran in {where(C_READ_AA)}. '` | The note row: one text over the full width. It says that each kernel order of part C has 2 processes, and in which sessions each order ran (`where`). Section 1.1 of the facts sheet shows the order cfwd in sessions 1 and 3, and the order crev in session 2 and in the extra process T72C4 [Ref1]. |
| 2043 | `        f"So kernel order and session are not fully separated {ref('go')}.</span>",` | Continues the text of line 2042: the conclusion that kernel order and session are not fully separated, with the reference mark of `go.sh`. |
| 2044 | `    ]` | Ends the list `rows`. |
| 2045 | `    return table(["Part and pair", "#Lowest drop, %", "#Highest drop, %", "#Old read kernel, GB/s", "#Load-only loop, GB/s", "n"], rows, "q1")` | Returns the HTML table (`table`, line 1501) with the class `q1`. Its 6 columns are: part and pair, lowest drop, highest drop, old read kernel, load-only loop, n. Table 1 has no row for the 8 `asmread` pairs of part C. The caption of the table says so (line 2735). |

### `tnote`, `cmp_cell`, and the assertions for the rows of Table 2 (lines 2048 to 2078)

| Line | Source | Explanation |
|---:|---|---|
| 2048 | `def tnote(head, *points):` | Starts the function `tnote`. It returns the HTML of a note under a table. |
| 2049 | `    """A note under a table: its first sentences, then one bullet per further point."""` | Comment: the documentation text. A note is its first sentences, then one bullet per further point. |
| 2050 | `    return f'<div class="tn">{head}' + '<ul class="cl">' + "".join(f"<li>{x}</li>" for x in points) + "</ul></div>"` | Returns a `div` element of the class `tn` with the text `head`, and after it a bullet list of the class `cl` with one item per point. |
| 2053 | `def cmp_cell(rg, n):` | Starts the function `cmp_cell`. It returns one range cell of Table 2. |
| 2054 | `    return f'<span class="num">{rg.txt()}</span><br>{small(n)}'` | The cell holds the range `rg.txt()` (the lowest and the highest rate with 2 decimals) in a `span` of the class `num`, and under it the text of n in small type. |
| 2057 | `rC_old_p0 = Rg([r for r in C_OLD if r["pos"] == 0])` | `rC_old_p0`: the range of the part C `oldread` intervals at position 0. |
| 2058 | `need(rC_old_p0.n == 4 and {r["file"] for r in rC_old_p0.recs} == {"cfwd.csv"} and rC_old_p0.overlaps(rPL_old), "part C, oldread at position 0: not 4 intervals of cfwd that overlap the pool")` | Hard assertion: the script stops unless these are 4 intervals, all from `cfwd.csv`, and their range overlaps the 8000 MT/s pool `rPL_old`. |
| 2059 | `C_OLD_P2 = [r for r in C_OLD if r["pos"] == 2]` | `C_OLD_P2`: the part C `oldread` intervals at position 2. |
| 2060 | `need(len(C_OLD_P2) == 4 and {r["file"] for r in C_OLD_P2} == {"crev.csv"} and {r["kernel_before"] for r in C_OLD_P2} == {"read"}, "part C, oldread at position 2: not 4 intervals of crev directly after read")` | Hard assertion: the script stops unless these are 4 intervals from `crev.csv`, each directly after the kernel `read`. |
| 2061 | `need({r["pos"] for r in P_L_OLD} == {0} and {r["pos"] for r in P_L_ASM} == {1} and {r["kernel_before"] for r in P_L_ASM} == {"oldread"}, "pool L-1 to L-4: positions")` | Hard assertion: every `oldread` record of the pool L-1 to L-4 must be at position 0. Every `asmread` record of the pool must be at position 1, directly after `oldread`. |
| 2062 | `xc_text_range("part C, oldread at position 0 (the position of the 8000 MT/s rows)", "4.2", rC_old_p0.lo, rC_old_p0.hi, "", "0.01", f2)` | Adds one line to the self-check list (`xc_text_range`, line 640). The line is PASS when the range of `rC_old_p0` stands in section 4.2 of `FACTS.md`, with a tolerance of 0.01 GB/s. The saved output of a build shows 465.54 to 467.83 GB/s [Ref5]. |
| 2063 | `# every comparison with 8000 MT/s of the rerun uses records of the rerun only: control I and F72d12 are never pooled into it` | Comment: every comparison of the rerun with 8000 MT/s uses records of the rerun only. Control I and F72d12 are never pooled into it. |
| 2064 | `for rg_ in (rA_old, rC_old, rL_old, rL_asm, rC_asm_ao, A_V3[1]["r7"], A_V3[2]["r7"]):` | Starts a loop over the seven 7200 MT/s ranges that the rerun compares with 8000 MT/s: part A, part C and part L of the old read kernel, `asmread` of part L, `asmread` directly after `oldread` of part C, and session 1 of `bw_new` read in round 1 and in round 2. |
| 2065 | `    need({r["dataset"] for r in rg_.recs} <= {"rerun-A", "rerun-L", "rerun-C"}, "a comparison of the rerun with 8000 MT/s holds a record of control I or F72d12")` | Hard assertion: each range must hold only records of the datasets `rerun-A`, `rerun-L` and `rerun-C`. So no record of control I or of F72d12 is part of a comparison of the rerun. |
| 2066 | `RERUN_CMP_NEW = [rL_asm.lo > rPL_asm.hi, rC_asm_ao.lo > rPL_asm.hi, A_V3[1]["r7"].lo > A_V3[1]["r8"].hi, A_V3[2]["r7"].lo > A_V3[2]["r8"].hi]` | `RERUN_CMP_NEW`: the 4 comparisons of the load-only loop, as a list of true and false values. An entry is true when the lowest 7200 MT/s rate is above the highest 8000 MT/s rate. The 4 comparisons are: `asmread` of part L against the pool, `asmread` directly after `oldread` of part C against the pool, and session 1 of part A (`bw_new` read) against A-1 and A-2 in round 1 and in round 2. |
| 2067 | `RERUN_CMP_C = 1                                             # one of them is a part C row (asmread directly after oldread), made by decision (r) of the facts sheet` | `RERUN_CMP_C`: the constant 1. Comment at the end of the line: one of the 4 comparisons is a part C row (asmread directly after oldread), made by decision (r) of the facts sheet. Line 2432 uses the constant. |
| 2068 | `need(all(RERUN_CMP_NEW), "load-only loop: a comparison of the rerun with 8000 MT/s is not 'higher'")` | Hard assertion: the script stops unless all 4 entries are true. |
| 2069 | `need(len(RERUN_CMP_NEW) == 4 and {r["dataset"] for r in rL_asm.recs} == {"rerun-L"} and {r["dataset"] for r in rC_asm_ao.recs} == {"rerun-C"}` | Hard assertion, first condition: the list has 4 entries, `rL_asm` holds only records of `rerun-L`, and `rC_asm_ao` holds only records of `rerun-C`. |
| 2070 | `     and all({r["kernel"] for r in rg_.recs} == {"asmread"} for rg_ in (rL_asm, rC_asm_ao))` | Continues the condition: both of these ranges hold only the kernel `asmread`. |
| 2071 | `     and all({(r["dataset"], r["binary"], r["kernel"], r["session"]) for r in A_V3[rnd]["r7"].recs} == {("rerun-A", "bw_new", "read", 1)} for rnd in (1, 2)),` | Continues the condition: in both rounds the range `r7` of `A_V3` holds only records of the dataset `rerun-A`, the binary `bw_new`, the kernel `read` and session 1. |
| 2072 | `     "load-only loop: the 4 comparisons of the rerun are not part L and part C with asmread, and session 1 of part A with bw_new read in rounds 1 and 2")` | The message of the assertion of line 2069. |
| 2073 | `# caption of Table 2: which of its rows are the comparisons that sentence 3 of the Short version counts` | Comment: the caption of Table 2 says which of its rows are the comparisons that sentence 3 of the Short version counts. |
| 2074 | `T2_RERUN_ROWS = (f"The block &quot;Load-only loop&quot; holds the {len(RERUN_CMP_NEW)} comparisons of the rerun that sentence 3 of the Short version counts. "` | `T2_RERUN_ROWS`: a text for the caption of Table 2 (line 2751). This line says that the block of the load-only loop holds the comparisons of the rerun that sentence 3 of the Short version counts. Their number comes from `len(RERUN_CMP_NEW)`, which is 4 (line 2069). |
| 2075 | `                 "Two use the new read kernel itself: part A, session 1, rounds 1 and 2. Two use asmread in its place: part L, and the part C row &quot;asmread directly after oldread&quot;. "` | Continues the text: two comparisons use the new read kernel itself (part A, session 1, rounds 1 and 2). Two use `asmread` in its place (part L, and the part C row of asmread directly after oldread). |
| 2076 | `                 f"The rows of {F72} and of {CI} are not comparisons of the rerun.")` | Continues the text: the rows of F72d12 and of control I are not comparisons of the rerun. The two names come with their labels, from the constants `F72` and `CI` (lines 1480 to 1481). |

### Function `q2_table`: the rows of Table 2 (7200 MT/s against 8000 MT/s) (lines 2079 to 2123)

| Line | Source | Explanation |
|---:|---|---|
| 2079 | `def q2_table():` | Starts the function `q2_table`. It builds Table 2 of the page: one row per comparison of a 7200 MT/s row with 8000 MT/s rows, and the notes of the table. `build` calls it in line 2752. |
| 2080 | `    pool_l = ("pool L-1 to L-4, oldread at position 0 (L-1: 6 s, the argument line of part L. It differs from the part C lines in the kernel order. "` | `pool_l`: the long label of the 8000 MT/s pool L-1 to L-4 for the row of part C (line 2089). This line states that row L-1 has 6 s intervals and ran the argument line of part L, and that this line differs from the part C lines in the kernel order. The label does not name one more difference. The processes of the rows L-2 to L-4 carry the names of their argument lines (lines 2318 to 2320). In the code folder `w120-2026-11-15`, the spec lines with these names (`p1nop` and `p2add` in `r1.spec`, `thp` in `r5.spec`, `st1` to `st3` in `r6.spec`) name 7 to 15 kernels, against 5 kernels in `like.spec`. Each of these sequences starts with oldread, asmread. |
| 2081 | `              "L-2 to L-4: 4 s, other hardware events counted) " + ref("L-1", "L-1l", "L-2a", "L-2b", "L-3", "L-4a", "L-4b", "L-4c"))` | Continues the label: the rows L-2 to L-4 have 4 s intervals with other hardware events counted. Then come 8 reference marks: the csv files of the four rows, and the file `launches.txt` of row L-1. So 2 of the 11 intervals of each pool are 6 s intervals and 9 are 4 s intervals (lines 293 to 297, lines 317 to 319). Every 7200 MT/s row that is compared with the pool has 6 s intervals. Two more differences show in the records of `facts.json`. In round 1 the kernel directly before `oldread` is `read_1pl` in the part L line, and another test loop in the rows L-2 and L-3 (field `kernel_before`) [Ref2]. The records of row L-4 hold round 0 only, and the part L line runs 2 rounds [Ref2]. |
| 2082 | `    pool_old, pool_asm = "pool L-1 to L-4, oldread at position 0<br>", "pool L-1 to L-4, asmread at position 1<br>"` | `pool_old`, `pool_asm`: the short labels of the two pools: `oldread` at position 0, and `asmread` at position 1. Each ends with a line break. |
| 2083 | `    cannot = lambda rg: f"The test cannot exclude a difference of about {f1(width_pct(rg))} % (est. from one boot)"` | `cannot`: returns the sentence about the difference that an overlap result cannot exclude. The size is `width_pct(rg)` (line 476): the width of the 8000 MT/s range in percent of its lower end, printed with 1 decimal. The sentence labels this size as an estimate (`est. from one boot`). |
| 2084 | `    rows = ["Old read kernel"]` | `rows`: the list of the table rows. It starts with the title row of the old read kernel. Each list entry that follows is one row with 6 cells: the row name, the 7200 MT/s range with n (`cmp_cell`, line 2053), the 8000 MT/s range with n, the overlap, the distance of the nearest ends, and the wording. |
| 2085 | `    rows.append(["Part A (bw_old read)", cmp_cell(rA_old, n7200(A_OLD)), f"pool A-1 to A-3 {ref('A-1', 'A-2', 'A-3')}<br>" + cmp_cell(rPA_old, n8000(P_A_OLD)), "yes", "0",` | Row of part A: `rA_old` (18 intervals of `bw_old` read) against the pool `rPA_old` (21 intervals of A-1 to A-3). The cells `yes` and `0` are typed here, as are the cells `yes`, `no` and `0` of every row of this function. The assertions of lines 486 to 498 and line 514 stop the script when a typed result does not hold. |
| 2086 | `                 f"&quot;{WORD_SAME}&quot;. {cannot(rPA_old)}. The 7200 MT/s range is wider than the 8000 MT/s range ({f2(A_OLD_W7)} GB/s against {f2(A_OLD_W8)} GB/s). "` | Continues the row: the wording cell. It starts with the fixed text `WORD_SAME` (line 470) between quotation marks (`&quot;`), and the sentence of `cannot`. Then it gives the width of both ranges, `A_OLD_W7` and `A_OLD_W8` (line 527). The wording cells of 9 of the 12 rows with 6 cells use the fixed texts `WORD_SAME` and `WORD_DIFF` (lines 470 to 471). |
| 2087 | `                 f"{len(A_OLD_BELOW)} of its {rA_old.n} intervals lie below that range ({one_process(A_OLD_BELOW)}), and {len(A_OLD_ABOVE)} lie above it ({one_process(A_OLD_ABOVE)})"])` | Continues the cell: the number of 7200 MT/s intervals below and above the 8000 MT/s range (lines 525 to 526). `one_process` (line 531) names the session and the round of each of these two groups. It stops the script unless a group holds the 3 intervals of one process. Section 4.2 of the facts sheet names the process of session 1, round 2 as the one below the range, and the process of session 3, round 1 as the one above it [Ref1]. |
| 2088 | `    rows.append([lab("Part C (oldread)", f"{rC_old_p0.n} intervals at position 0 (order cfwd), {len(C_OLD_P2)} at position 2 (order crev, directly after read)"),` | Row of part C: the label. Its note gives the number of `oldread` intervals at position 0 (order cfwd) and at position 2 (order crev, directly after `read`). |
| 2089 | `                 cmp_cell(rC_old, n7200(C_OLD)), pool_l + "<br>" + cmp_cell(rPL_old, n8000(P_L_OLD)), "yes", "0",` | Continues the row: `rC_old` (all 8 `oldread` intervals) against the pool `rPL_old` (11 `oldread` intervals at position 0), with the long label `pool_l`. Overlap `yes`, distance `0`. |
| 2090 | `                 f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. The 8000 MT/s rows hold oldread at position 0 only. "` | Continues the row: the wording cell, with `WORD_SAME` and the sentence of `cannot`. It states that the 8000 MT/s rows hold `oldread` at position 0 only. |
| 2091 | `                 f"The {rC_old_p0.n} part C intervals at position 0 span {rC_old_p0.txt()} GB/s and overlap too"])` | Continues the cell: the range of the 4 part C intervals at position 0, and the statement that this range overlaps the pool too. Line 2058 asserts that overlap. |
| 2092 | `    rows.append(["Part L (oldread at position 0)", cmp_cell(rL_old, n7200(L_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)), "no", signed(L_OLD_NEAR),` | Row of part L: `rL_old` (6 intervals) against `rPL_old`, overlap `no`. The distance is `L_OLD_NEAR` (line 489): the highest part L rate minus the lowest pool rate, a negative value. `signed` (line 224) prints it with its sign and 2 decimals. The saved output of a build shows -1.24 GB/s [Ref5]. |
| 2093 | `                 f"&quot;{WORD_DIFF}&quot;. Part L is lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends ({f1(L_OLD_NEAR_PCT)} % of the lower end of the 8000 MT/s range) "` | Continues the row: the wording cell, with `WORD_DIFF` (line 471). It gives the distance of the nearest ends without its sign, and the same distance in percent of the lower end of the 8000 MT/s range (`L_OLD_NEAR_PCT`, line 491). |
| 2094 | `                 f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_MED_PCT)} % of the 8000 MT/s median). The data do not show the cause (section 3)"])` | Continues the cell: the difference of the medians (`L_OLD_MED`, line 490), and the same value in percent of the 8000 MT/s median (`L_OLD_MED_PCT`, line 492). The last sentence says that the data do not show the cause. |
| 2095 | `    rows.append([lab("F72d12 (oldread)", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_old, n7200(F_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),` | Row of F72d12: `rF_old` (2 intervals) against `rPL_old`. It has its own row and is not pooled with part L. |
| 2096 | `                 "yes", "0", f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. Not pooled with part L"])` | Continues the row: overlap `yes`, distance `0`, and the wording cell with `WORD_SAME`, the sentence of `cannot` and the words `Not pooled with part L`. |
| 2097 | `    rows.append([lab("Control I (oldread)", "added after the first numbers were seen"), cmp_cell(rI_old, n7200(I_OLD)), pool_old + cmp_cell(rPL_old, n8000(P_L_OLD)),` | Row of control I: `rI_old` (4 intervals) against `rPL_old`. It has its own row too. |
| 2098 | `                 "yes", "0", f"&quot;{WORD_SAME}&quot;. {cannot(rPL_old)}. Not pooled with part L"])` | Continues the row: the same three cells as in line 2096. |
| 2099 | `    rows.append("Load-only loop (no percent change between the two speeds is given)")` | The title row of the load-only rows. It says that the table gives no percent change between the two memory speeds for the load-only loop. |
| 2100 | `    rows.append([lab("Part L (asmread at position 1)", "in place of the new read kernel"), cmp_cell(rL_asm, n7200(L_ASM)), pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)),` | Row of part L, `asmread` at position 1: `rL_asm` (6 intervals) against the pool `rPL_asm` (11 `asmread` intervals at position 1). |
| 2101 | `                 "no", signed(DIST["nearest"][0]), f"&quot;{WORD_DIFF}&quot;. Part L is higher"])` | Continues the row: overlap `no`. The distance is `DIST["nearest"][0]` (line 504): the lowest part L rate minus the highest pool rate. `signed` prints it with a plus sign. The saved output of a build shows 12.48 GB/s [Ref5]. The wording cell holds `WORD_DIFF` and says that part L is higher. |
| 2102 | `    for rnd in (1, 2):` | Starts a loop over the rounds 1 and 2. It adds one row of part A, session 1, per round. Table 2 has no row for sessions 2 and 3 of `bw_new` read. The comment in line 508 names rule V3 for the use of session 1. |
| 2103 | `        v = A_V3[rnd]` | `v`: the entry of `A_V3` for the round (lines 509 to 516). |
| 2104 | `        p8 = ", ".join(str(x) for x in sorted(set(v["p8"])))` | `p8`: the distinct pass counts of the 8000 MT/s intervals of the round (`v["p8"]`, line 516), sorted and joined with commas. |
| 2105 | `        rows.append([f"Part A, session 1, round {rnd} (bw_new read, the new read kernel)", cmp_cell(v["r7"], n7200(v["r7"].recs)),` | The row: the name, and `v["r7"]` (3 intervals of `bw_new` read of session 1) in the 7200 MT/s cell. |
| 2106 | `                     f"A-1 and A-2, round {rnd}<br>" + cmp_cell(v["r8"], n8000(v["r8"].recs)), "no", signed(v["near"]),` | Continues the row: `v["r8"]` (6 intervals of A-1 and A-2 of the same round) in the 8000 MT/s cell, overlap `no`, and the distance `v["near"]` (line 515), printed with a plus sign. The saved output of a build shows 32.75 GB/s in round 1 and 10.37 GB/s in round 2 [Ref5]. |
| 2107 | `                     f"outside (above) the 8000 MT/s range of the same round. Pass counts per interval: {v['p7'][0]} at 7200 MT/s, {p8} at 8000 MT/s. They are not all equal. So part A gives no exact size of the difference"])` | Continues the row: the wording cell. It does not use `WORD_DIFF`. It starts with the typed text `outside (above) the 8000 MT/s range of the same round`. Line 514 asserts this result. Then it gives the pass counts per interval: the one value of `p7` at 7200 MT/s, and the values `p8` at 8000 MT/s. Two typed sentences follow: the counts are not all equal, and so part A gives no exact size of the difference. No assertion checks the sentence about the pass counts. Section 4.3 of the facts sheet gives 664 passes at 7200 MT/s against 600 passes at 8000 MT/s in round 1, and against 600, 603, 663 and 664 passes in round 2 [Ref1]. |
| 2108 | `    rows.append(["Part C, kernel read (the new read kernel) at position 1",` | Row of part C, bwx12 kernel `read` (the new read kernel): the row name. The position 1 in this name is typed. No assertion compares it directly with the records of `C_READ` (line 283). `q1_table` reads the position of both groups from the records (line 2015). Section 3.3 of the facts sheet gives position 1 for both groups [Ref1]. |
| 2109 | `                 f'after oldread: <span class="num">{rC_read_ao.txt()}</span><br>{small(n7200(C_READ_AO))}<br>after asmread: <span class="num">{rC_read_aa.txt()}</span><br>{small(n7200(C_READ_AA))}',` | Continues the row: the 7200 MT/s cell with the two ranges `rC_read_ao` and `rC_read_aa`, each with its n. |
| 2110 | `                 "no bwx12 run", "-", "-",` | Continues the row: the 8000 MT/s cell holds `no bwx12 run`. The overlap cell and the distance cell hold `-`. |
| 2111 | `                 "Insufficient data: no 8000 MT/s run of kernel read with bwx12. The bwx12 kernel read (new C read loop) was never run with bwx12 at 8000 MT/s. "` | Continues the row: the wording cell. It starts with `Insufficient data`: the bwx12 kernel `read` was never run with bwx12 at 8000 MT/s. |
| 2112 | `                 f"The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its place {ref('rules', 'facts')}"])` | Continues the cell: the investigation of 2026-11-15 ran `asmread` in its place. Then come the reference marks of the rules file and of the facts sheet. |
| 2113 | `    rows.append([lab("Part C, asmread directly after oldread", "order crev, round 1, position 0", "in place of the new read kernel"), cmp_cell(rC_asm_ao, n7200(C_ASM_AO)),` | Row of part C, `asmread` directly after `oldread`: the label with two notes, and `rC_asm_ao` (2 intervals) in the 7200 MT/s cell. Table 2 has no comparison row for the other 6 `asmread` intervals of part C: the 4 intervals directly after `read` (`C_ASM_AR`), and the 2 intervals that are the first interval of their process (`C_ASM_FI`). Figure 2 shows them in the group without a band (lines 1931 to 1932). The note on the older runner bwx uses `C_ASM_AR` (line 2150). |
| 2114 | `                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rC_asm_ao.nearest(rPL_asm)),` | Continues the row: the pool `rPL_asm`, overlap `no`, and the distance `rC_asm_ao.nearest(rPL_asm)`, printed with a plus sign. The saved output of a build shows 15.56 GB/s [Ref5]. |
| 2115 | `                 f"&quot;{WORD_DIFF}&quot;. Part C is higher. The 8000 MT/s rows match in the kernel that ran directly before (oldread). "` | Continues the row: the wording cell, with `WORD_DIFF`. It says that part C is higher, and that the 8000 MT/s rows match in the kernel that ran directly before (`oldread`). |
| 2116 | `                 "They do not match in the position: asmread is at position 1 there"])` | Continues the cell: one mismatch. The 8000 MT/s rows hold `asmread` at position 1, and this row holds it at position 0. Line 1884 and line 2061 assert both positions. |
| 2117 | `    rows.append([lab("F72d12 (asmread at position 1)", "in place of the new read kernel", "earlier run of the same boot, not part of the rerun"), cmp_cell(rF_asm, n7200(F_ASM)),` | Row of F72d12, `asmread`: the label with two notes, and `rF_asm` in the 7200 MT/s cell. |
| 2118 | `                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "yes", "0",` | Continues the row: the pool `rPL_asm`, overlap `yes`, distance `0`. |
| 2119 | `                 f"inside the range of the 8000 MT/s pool: &quot;{WORD_SAME}&quot;. The test cannot exclude a difference of {f2(rPL_asm.hi - rPL_asm.lo)} GB/s, the width of that range (est. from one boot). "` | Continues the row: the wording cell. It says that F72d12 lies inside the range of the pool, with `WORD_SAME`. It gives the width of the pool range in GB/s as the difference that the test cannot exclude, marked as an estimate. |
| 2120 | `                 f"Against L-1 alone F72d12 is {f2(rF_asm.nearest(rL1_asm))} GB/s higher. Not pooled with part L"])` | Continues the cell: the distance of F72d12 above row L-1 alone (`rL1_asm`, line 467). The saved output of a build shows 1.73 GB/s [Ref5]. The cell ends with the words `Not pooled with part L`. |
| 2121 | `    rows.append([lab("Control I (asmread at position 1)", "in place of the new read kernel", "added after the first numbers were seen"), cmp_cell(rI_asm, n7200(I_ASM)),` | Row of control I, `asmread`: the label with two notes, and `rI_asm` in the 7200 MT/s cell. |
| 2122 | `                 pool_asm + cmp_cell(rPL_asm, n8000(P_L_ASM)), "no", signed(rI_asm.nearest(rPL_asm)),` | Continues the row: the pool `rPL_asm`, overlap `no`, and the distance `rI_asm.nearest(rPL_asm)`, printed with a plus sign. The saved output of a build shows 4.61 GB/s [Ref5]. |
| 2123 | `                 f"&quot;{WORD_DIFF}&quot;. Control I is higher. Not pooled with part L"])` | Continues the row: the wording cell, with `WORD_DIFF`. It says that control I is higher and is not pooled with part L. |

### Function `q2_table`: the tests of the pool and the notes under Table 2 (lines 2124 to 2183)

| Line | Source | Explanation |
|---:|---|---|
| 2124 | `    # the choice of the pool: the same test against row L-1 alone (the row with the argument line of part L)` | Comment: the choice of the pool. The same test is made against row L-1 alone. L-1 is the row with the argument line of part L. |
| 2125 | `    rL1_old = Rg(B_L_OLD["L-1"])` | `rL1_old`: the range of the `oldread` intervals of row L-1. |
| 2126 | `    alone = [("part L, oldread", rL_old, rPL_old, rL1_old), ("part C, oldread", rC_old, rPL_old, rL1_old), ("F72d12, oldread", rF_old, rPL_old, rL1_old),` | `alone`: the 8 rows that use the pool L-1 to L-4. Each entry holds a name, the 7200 MT/s range, the pool range, and the range of row L-1 alone. This line holds the entries of part L, part C and F72d12 for `oldread`. |
| 2127 | `             ("control I, oldread", rI_old, rPL_old, rL1_old), ("part L, asmread", rL_asm, rPL_asm, rL1_asm), ("part C, asmread", rC_asm_ao, rPL_asm, rL1_asm),` | Continues the list: control I for `oldread`, and part L and part C for `asmread`. |
| 2128 | `             ("F72d12, asmread", rF_asm, rPL_asm, rL1_asm), ("control I, asmread", rI_asm, rPL_asm, rL1_asm)]` | Continues the list: F72d12 and control I for `asmread`. |
| 2129 | `    changed = [nm for nm, r7, pool, l1 in alone if r7.overlaps(pool) != r7.overlaps(l1)]` | `changed`: the names of the rows whose overlap result against L-1 alone differs from the result against the pool. |
| 2130 | `    need(changed == ["F72d12, asmread"], f"table 2: rows whose overlap result changes against L-1 alone: {changed}")` | Hard assertion: the script stops unless this list holds only `F72d12, asmread`. |
| 2131 | `    # row X2d12 (12 modules, another boot, two changed TXREQ settings): shown, not used. Would it change an overlap result?` | Comment: row X2d12 (12 modules, another boot, two changed TXREQ settings) is shown and not used. The next lines test whether it would change an overlap result. |
| 2132 | `    pool_x = {id(rPL_old): Rg(P_L_OLD + EXTRA["X2d12"]["old"]), id(rPL_asm): Rg(P_L_ASM + EXTRA["X2d12"]["asm"])}` | `pool_x`: the two pools with the records of X2d12 added (`EXTRA`, line 1299). The dictionary uses `id(...)` of each pool range as its key. `id` gives a number that identifies an object. |
| 2133 | `    need(all(r7.overlaps(pool) == r7.overlaps(pool_x[id(pool)]) for nm, r7, pool, l1 in alone), "table 2: an overlap result changes when row X2d12 is added to the pool")` | Hard assertion: the script stops when an overlap result of one of the 8 rows changes with this larger pool. |
| 2134 | `    need(n8000(EXTRA["X2d12"]["old"]) == n8000(EXTRA["X2d12"]["asm"]), "X2d12: n differs between the two kernels")` | Hard assertion: the script stops unless the text of n of X2d12 is the same for both kernels. The note of line 2144 prints one n for both. |
| 2135 | `    rows.append("Notes")` | Adds the title row `Notes`. The notes follow, each as one row over the full width of the table. |
| 2136 | `    rows.append(f'<span class="tn">Pool or L-1 alone: with row L-1 alone in place of the pool L-1 to L-4, {len(alone) - len(changed)} of the {len(alone)} rows that use the pool keep their overlap result. '` | First note, pool or L-1 alone: how many of the 8 rows keep their overlap result with row L-1 alone in place of the pool (from `alone` and `changed`). |
| 2137 | `                f"The exception is F72d12 with asmread (earlier run of the same boot, not part of the rerun): it lies {f2(rF_asm.nearest(rL1_asm))} GB/s above L-1. "` | Continues the note: the exception, F72d12 with `asmread`, and its distance above L-1. |
| 2138 | `                f"The choice of the pool was made after the numbers were seen (decision (k) of the facts sheet) {ref('facts')}.</span>")` | Continues the note: the pool was chosen after the numbers were seen (decision (k) of the facts sheet). Then comes the reference mark of the facts sheet. |
| 2139 | `    rows.append('<span class="tn">Part C: the rules file contradicts itself here. Rule F2 (points 2 and 3) would show part C at 7200 MT/s only. '` | Second note, part C: a fixed text. It says that the rules file contradicts itself on part C. By rule F2 (points 2 and 3), part C would be shown at 7200 MT/s only. |
| 2140 | `                "Rules V1 (point 2), V2 (point 4) and V4 compare part C with the 8000 MT/s rows. This page follows the facts sheet (its decision (r) in section 2) "` | Continues the note: the rules V1 (point 2), V2 (point 4) and V4 compare part C with the 8000 MT/s rows. The page follows the facts sheet (its decision (r)). |
| 2141 | `                f"and compares the two part C rows that have an 8000 MT/s row of the list {ref('facts', 'rules')}. This choice was made after the numbers were seen.</span>")` | Continues the note: the page compares the two part C rows that have a row in the list of 8000 MT/s rows. The note states that this choice was made after the numbers were seen. |
| 2142 | `    rows.append(f'<span class="tn">Row X2d12 is shown here and not used. It is 1 process of the argument line of part L at 8000 MT/s with 12 modules, in another boot of 2026-11-17 {ref("xX2d12", "xX2d12l", "klogX2d12")}. '` | Third note, row X2d12: the row is shown and not used. It is 1 process of the argument line of part L at 8000 MT/s with 12 modules, in another boot of 2026-11-17. |
| 2143 | `                f"Rules V2 (point 4) and F2 (point 2) name it as an 8000 MT/s row of the part L line. Rule V4 lists it among the rows that are not used (a firmware test with two changed TXREQ settings) {ref('rules')}. "` | Continues the note: the rules V2 (point 4) and F2 (point 2) name the row as an 8000 MT/s row of the part L line. Rule V4 lists it among the rows that are not used, as a firmware test with two changed TXREQ settings. |
| 2144 | `                f"This page follows rule V4. X2d12 gave {rX2_old.txt()} GB/s for the old read kernel and {rX2_asm.txt()} GB/s for asmread ({n8000(EXTRA['X2d12']['old'])} per kernel). "` | Continues the note: the page follows rule V4. Then come the ranges `rX2_old` and `rX2_asm` (line 1326) and the text of n per kernel. |
| 2145 | `                f"With X2d12 added to the pool L-1 to L-4, all {len(alone)} rows that use the pool keep their overlap result.</span>")` | Continues the note: with X2d12 added to the pool, all 8 rows keep their overlap result (line 2133). |
| 2146 | `    # rows of the older runner bwx: named by the rules file, another binary, so no wording comes from them` | Comment: the rows of the older runner bwx. The rules file names them. They come from another binary, so no wording comes from them. |
| 2147 | `    n_rev = n8000(X_REV_READ)` | `n_rev`: the text of n of the `read` records of the bwx processes with the reverse kernel order. |
| 2148 | `    need(n_rev == n8000(X_REV_ASM) and n8000(X_READ_AO) == n8000(X_READ_AA) == n8000(X_ASM_AR), "runner bwx: n differs between the kernels")` | Hard assertion: the script stops when n differs between the kernels: between the two reverse-order groups, or between the three bwx groups of lines 323 to 325. |
| 2149 | `    x_refs = ref("xB7a", "xB7b", "xC3a", "xC3b")` | `x_refs`: the reference marks of the four csv files of the datasets B7a, B7b, C3a and C3b. |
| 2150 | `    sets = [("read after oldread", C_READ_AO, rX_read_ao, X_ABOVE[0]), ("read after asmread", C_READ_AA, rX_read_aa, X_ABOVE[1]), ("asmread after read", C_ASM_AR, rX_asm_ar, X_ABOVE[2])]` | `sets`: three groups of part C intervals. Each entry holds a name, the records, the range of the bwx rows with the same kernel directly before, and the distance `X_ABOVE` (line 545). |
| 2151 | `    need(len(sets) == len(X_PAIRS) and all(d_ > 0 for *_, d_ in sets), "runner bwx: the three sets of part C intervals")` | Hard assertion: the script stops unless there are as many sets as entries of `X_PAIRS` (line 543), and each distance is above 0. |
| 2152 | `    rows.append(tnote(` | Adds the fourth note, on the other runner binary, through `tnote` (line 2048). |
| 2153 | `        f"Other runner binary (bwx, not the bwx12 binary of the rerun): rule V2 (point 4) names 8000 MT/s rows (12 modules) of the older runner bwx for the comparison with part C {ref('rules')}.",` | The first text of the note: rule V2 (point 4) names 8000 MT/s rows (12 modules) of the older runner bwx for the comparison with part C. |
| 2154 | `        f"These rows differ from part C in at least four ways. They used the older binary bwx. Each process timed a sequence of {len(X_SEQ)} kernels, and a part C process timed {len(SPEC['cfwd'][2].split(','))}. "` | First bullet: how these rows differ from part C. They used the older binary bwx. Each process timed a sequence of `len(X_SEQ)` kernels, and a part C process timed as many as the sequence of `cfwd.spec` holds. Line 1280 asserts 8 kernels for bwx, and `cfwd.spec` names 3. |
| 2155 | `        "The processes of the two result folders B7-* ran without the counting of hardware events of the CPU (count=0 in the csv header), "` | Continues the bullet: the processes of the two result folders B7 ran without the counting of hardware events of the CPU (`count=0` in the csv header). Line 1262 asserts the counter setting of the four datasets. |
| 2156 | `        f"and those of the two folders C3-* ran with it (count=1). {X_OFFSET} of the {len(X_POOL_HEAD)} processes used the runner option <code>--start offset</code>. "` | Continues the bullet: those of the two folders C3 ran with it (`count=1`). `X_OFFSET` of the `len(X_POOL_HEAD)` processes used the runner option `--start offset`. Line 1261 and line 1267 assert 12 of 24. |
| 2157 | `        f"Part C used bwx12 with the counting of hardware events and <code>--start common</code> {x_refs} {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.",` | Continues the bullet: part C used bwx12 with the counting of hardware events and with `--start common`. Lines 1270 to 1275 assert both settings. Then come the reference marks. |
| 2158 | `        f"The highest of their load-only intervals ({n8000(X_LOADS)}) was {f2(X_MAX_READ)} GB/s for kernel read and {f2(X_MAX_ASM)} GB/s for asmread {x_refs}.",` | Second bullet: the highest bwx rate of the kernel `read` and of `asmread` (`X_MAX_READ`, `X_MAX_ASM`, lines 546 to 547), with the text of n of `X_LOADS`. |
| 2159 | `        f"{('Three' if len(sets) == 3 else str(len(sets)))} sets of part C intervals have such bwx rows with the same kernel directly before ({n8000(X_READ_AO)} per set at 8000 MT/s). "` | Third bullet: three sets of part C intervals have bwx rows with the same kernel directly before. The line gives n per set at 8000 MT/s. |
| 2160 | `        "Each set lies above the highest value of its bwx rows. The distances are those of the nearest ends. "` | Continues the bullet, typed text: each set lies above the highest value of its bwx rows, and the distances are those of the nearest ends. Line 544 asserts that each of the three part C ranges lies above its bwx range. |
| 2161 | `        + " ".join(f"The set &quot;{nm}&quot; ({n7200(recs)}) lies {f2(d_)} GB/s above {f2(xr.hi)} GB/s." for nm, recs, xr, d_ in sets),` | Continues the bullet: one sentence per set, with its name, its n, its distance above the bwx rows and the highest rate of these rows. |
| 2162 | `        f"The {Rg(X_REV_READ).np} bwx processes of two other result folders ran another kernel order. They reached {f2(X_REV_MAX_READ)} GB/s (read) and {f2(X_REV_MAX_ASM)} GB/s (asmread) "` | Fourth bullet: the bwx processes of two other result folders ran another kernel order. The line gives their highest rates (`X_REV_MAX_READ`, `X_REV_MAX_ASM`, line 549). Section 4.6 of the facts sheet gives 324.36 GB/s for `read` and 324.98 GB/s for `asmread` [Ref1]. |
| 2163 | `        f"({n_rev} per kernel) {ref('xB5a-rev', 'xB5b-rev')}. "` | Continues the bullet: the text of n per kernel and the reference marks of the two csv files. |
| 2164 | `        "The read value lies inside the 7200 MT/s range of both read rows of part C (after oldread and after asmread). The asmread value lies inside the 7200 MT/s asmread range of part L."))` | Continues the bullet: this `read` rate lies inside both 7200 MT/s `read` ranges of part C, and this `asmread` rate lies inside the 7200 MT/s `asmread` range of part L. Lines 551 to 553 assert both. |
| 2165 | `    # the three boots with 10 modules that rule V1 (points 3 and 4) quotes: how far two boots at 8000 MT/s differ` | Comment: the three boots with 10 modules that rule V1 (points 3 and 4) quotes. They show how far two boots at 8000 MT/s differ. |
| 2166 | `    n10 = n8000(T10_ASM[0].recs)` | `n10`: the text of n of the `asmread` records of the first of the two boots of `T10_ASM` (line 1327). |
| 2167 | `    need(n10 == n8000(T10_ASM[1].recs), "10-module boots: n differs between the two boots")` | Hard assertion: the script stops unless n is equal for the two boots. |
| 2168 | `    rows.append(tnote(` | Adds the fifth note, on the boots with 10 modules, through `tnote`. |
| 2169 | `        f"Boots with 10 modules (rule V1, points 3 and 4) {ref('rules')}: on 2026-11-17 three boots at 8000 MT/s found 10 modules. Each ran the argument line of part L once "` | The first text of the note: on 2026-11-17 three boots at 8000 MT/s found 10 modules, and each ran the argument line of part L once. |
| 2170 | `        f"{ref('xX1d10', 'klogX1d10', 'xX1d10b', 'klogX1d10b', 'xBASEd10', 'klog10')}. They are not rows of the list, and no wording comes from them.",` | Continues the text: the reference marks of the csv files and of the saved kernel logs. The text says that these boots are not rows of the list and that no wording comes from them. |
| 2171 | `        f"By the settings records of the results folder, two of these boots had the same firmware settings (TXREQ Min changed) {ref('x1', 'x2')}. Their asmread gave {' / '.join(f2(v) for v in T10_ASM[0].v)} GB/s "` | First bullet: by the settings records of the results folder, two of these boots had the same firmware settings (TXREQ Min changed). Line 1322 tests the start times of the two boots against the times of the settings changes. The line gives the `asmread` rates of the first of the two boots with 2 decimals. |
| 2172 | `        f"and {' / '.join(f2(v) for v in T10_ASM[1].v)} GB/s ({n10} each). The two medians are {f1(T10_APART)} % apart (percent of the lower median).",` | Continues the bullet: the `asmread` rates of the second boot, n, and `T10_APART` (line 1328): the distance of the two medians in percent of the lower median. |
| 2173 | `        f"The three boots gave {rT10_old.txt()} GB/s for the old read kernel ({plural(rT10_old.n, 'interval')} / {plural(rT10_old.np, 'process')} / 3 boots). This range is {f1(width_pct(rT10_old))} % wide.",` | Second bullet: the `oldread` range of the three boots (`rT10_old`, line 1329) with its n, and the width of this range in percent of its lower end. |
| 2174 | `        f"Limit: by the same records the third boot had the original firmware settings {ref('rev')}. So the three boots did not differ by the boot alone."))` | Third bullet, a limit: by the same records the third boot had the original firmware settings (line 1324). So the three boots did not differ by the boot alone. |
| 2175 | `    # rounding: a distance is computed before rounding (reader finding: two printed distances are not the difference of the printed rates)` | Comment: rounding. A distance is computed before rounding. By the comment, a reader found that two printed distances are not the difference of the printed rates. |
| 2176 | `    ex = [(f2(rF_asm.nearest(rL1_asm)), "this table", q(rF_asm.lo) - q(rL1_asm.hi)), (f2(DIST["farthest"][0]), "Table 4", q(rL_asm.hi) - q(rPL_asm.lo))]` | `ex`: two distances as examples: F72d12 above L-1 (this table), and the farthest ends of part L and the pool (Table 4). Each entry holds the printed distance, the place, and the difference of the two rounded rates. |
| 2177 | `    ex = [f"{shown} GB/s ({where_})" for shown, where_, from_rounded in ex if Decimal(shown) != from_rounded]` | Keeps an example only when the printed distance differs from the difference of the rounded rates. The printed distance is computed from the rates before rounding and then rounded to 0.01 GB/s. The saved output of a build shows 1.73 GB/s and 39.38 GB/s for these two distances [Ref5]. For the second one the rounded rates differ by 39.39 GB/s (327.93 minus 288.54) [Ref5]. For the first one they differ by 1.74 GB/s: 301.90 GB/s minus the 300.16 GB/s that section 4.4 of the facts sheet gives for L-1 [Ref1]. So both examples stay. |
| 2178 | `    rows.append('<span class="tn">Rounding: a distance is computed from the rates before rounding. So it can differ by 0.01 GB/s from the difference of the two rounded rates'` | Adds the last note, on rounding: a distance is computed from the rates before rounding. So it can differ by 0.01 GB/s from the difference of the two rounded rates. |
| 2179 | `                + (". Examples: " + " and ".join(ex) if ex else "") + ".</span>")` | Continues the note: the examples of `ex`, when there are any. |
| 2180 | `    return table(["7200 MT/s row", "Range at 7200 MT/s, GB/s, and n", "8000 MT/s rows: range, GB/s, and n", "Overlap", "#Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher)",` | Returns the HTML table with the class `q2`. This line holds five of its 6 column titles: the 7200 MT/s row, its range and n, the range and n of the 8000 MT/s rows, the overlap, and the distance of the nearest ends. In the distance column a plus sign means that the 7200 MT/s row is higher. |
| 2181 | `                  "Wording by the rules fixed before the run"], rows, "q2")` | Continues the call: the sixth column title, the wording by the rules that were fixed before the run. |

### `visits_table` (Table 3) and `dist_table` (Table 4) (lines 2184 to 2218)

| Line | Source | Explanation |
|---:|---|---|
| 2184 | `def visits_table():` | Starts the function `visits_table`. It builds Table 3 of the page. `build` calls it in line 2756. |
| 2185 | `    """The three visits of the part L line in the 7200 MT/s boot: when and from which state each one started."""` | Comment: the documentation text. The table shows the three visits of the part L line in the 7200 MT/s boot: when and from which state each one started. |
| 2186 | `    hms = lambda utc: utc[11:19]` | `hms`: takes the time of day `HH:MM:SS` from a UTC time stamp. |
| 2187 | `    l_launch = sorted({r["launch_utc"] for r in L_OLD})` | `l_launch`: the launch times of the part L processes, from the field `launch_utc` of the `oldread` records, sorted. |
| 2188 | `    i_launch = sorted({r["launch_utc"] for r in I_OLD})` | `i_launch`: the same for the processes of control I. |
| 2189 | `    l_load = sorted({D(r["load1_at_launch"]) for r in L_OLD})` | `l_load`: the 1-minute load averages at the launches of part L (field `load1_at_launch`), sorted. |
| 2190 | `    i_load = [D([r for r in I_OLD if r["tag"] == t][0]["load1_at_launch"]) for t in ("T72I1", "T72I2")]` | `i_load`: the load average at the launch of each of the two processes of control I. |
| 2191 | `    i_gap = [int(LAUNCH[t]["gap_s"]) for t in ("T72I1", "T72I2")]` | `i_gap`: for the two steps of control I, the seconds after the end of the previous 120-thread process (`gap_s` of `LAUNCH`, line 879). |
| 2192 | `    need(all(LAUNCH[t]["gap_s"] == 5 and "of part A" in LAUNCH[t]["start_state"] for t in ("T72L1", "T72L2", "T72L3")), "part L: a process did not start 5 s after part A")` | Hard assertion: the script stops unless each part L step started 5 s after part A. The test reads `gap_s` and looks for the words `of part A` in the text `start_state`. |
| 2193 | `    need(max(i_load) < 1 and D(F_OLD[0]["load1_at_launch"]) < 1, "control I or F72d12: load at launch is not below 1.0")` | Hard assertion: the script stops unless control I and F72d12 started at a load average below 1.0. |
| 2194 | `    per = lambda rg: n7200(rg.recs)` | `per`: returns the text of n of a range (`n7200`, line 381). |
| 2195 | `    need(n7200(F_ASM) == n7200(F_OLD) and n7200(L_ASM) == n7200(L_OLD) and n7200(I_ASM) == n7200(I_OLD), "table 3: n differs between the two kernels of a visit")` | Hard assertion: the script stops unless the text of n is equal for `asmread` and `oldread` in each visit. The table has one n column for both kernels. |
| 2196 | `    rows = [` | `rows`: one row per visit. The cells are: the visit, the launch time, the start state, the `asmread` range, the `oldread` range, and n per kernel. |
| 2197 | `        [lab("F72d12", "earlier run of the same boot, not part of the rerun"), F_LAUNCH,` | Row of F72d12: the label and the launch time `F_LAUNCH` (line 913). |
| 2198 | `         f"{F_AFTER_BOOT_S} s after the first kernel log line of the boot ({BOOT7_KLOG} UTC) {ref('gaps')}. Load average {f2(F_OLD[0]['load1_at_launch'])} at launch {ref('F72l')}. "` | Continues the row: the start state. It gives the seconds after the first kernel log line of the boot (`F_AFTER_BOOT_S`, line 1125), and the load average at launch from the first `oldread` record. The saved output of a build shows 20 s [Ref5]. Section 4.1 of the facts sheet gives a load of 0.34 [Ref1]. |
| 2199 | `         f"Process list, written {F_ENV_BEFORE_S} s before the launch: the Linux kernel thread {F_TOP[3]} at {F_TOP[2]} %CPU {ref('F72e')}",` | Continues the cell: the busiest process of the process list that was saved before the launch (`F_TOP`, line 1119). The line names it a Linux kernel thread. The saved output of a build shows `pr/ttyAMA-1` at 51.6 %CPU [Ref5]. |
| 2200 | `         rF_asm.txt(), rF_old.txt(), per(rF_asm)],` | Continues the row: the two ranges and n. A range is `txt()` of an `Rg` object: the lowest and the highest rate with 2 decimals. |
| 2201 | `        ["Part L", f"{hms(l_launch[0])} to {hms(l_launch[-1])}",` | Row of part L: the launch cell holds the first and the last of its 3 launch times. |
| 2202 | `         f"5 s after the last 120-thread process of part A. Load average {f2(l_load[0])} to {f2(l_load[-1])} at launch. "` | Continues the row: the start state. Part L started 5 s after the last 120-thread process of part A. The cell gives the lowest and the highest load of its 3 launches. The part `meta.launches` of `facts.json` holds 74.05, 104.52 and 103.01 for them [Ref2]. |
| 2203 | `         f"Process lists before the launch: at most {L_ENV_MAX} %CPU {ref('envT72L1', 'envT72L2', 'envT72L3')}",` | Continues the cell: the highest %CPU of the process lists that were saved before the launches (`L_ENV_MAX`, line 1134). The saved output of a build shows at most 0.1 %CPU for part L and control I [Ref5]. |
| 2204 | `         rL_asm.txt(), rL_old.txt(), per(rL_asm)],` | Continues the row: the two ranges and n. |
| 2205 | `        [lab("Control I", "added after the first numbers were seen"), " and ".join(hms(x) for x in i_launch),` | Row of control I: the launch cell holds its 2 launch times. |
| 2206 | `         f"Idle start: load average {f2(i_load[0])} and {f2(i_load[1])} at launch, {i_gap[0]} s and {i_gap[1]} s after the previous 120-thread process. "` | Continues the row: the start state, an idle start. The cell gives both loads and both gaps. The part `meta.launches` of `facts.json` holds loads of 0.87 and 0.91, and gaps of 287 s and 265 s [Ref2]. |
| 2207 | `         f"Process lists before the launch: at most {I_ENV_MAX} %CPU {ref('envT72I1', 'envT72I2')}",` | Continues the cell: the highest %CPU of the saved process lists (`I_ENV_MAX`, line 1135). |
| 2208 | `         rI_asm.txt(), rI_old.txt(), per(rI_asm)],` | Continues the row: the two ranges and n. |
| 2209 | `    ]` | Ends the list `rows`. |
| 2210 | `    return table(["Visit", "Launch, UTC", "Start state", "#asmread, GB/s", "#oldread, GB/s", "n per kernel"], rows, "visits")` | Returns the HTML table with the class `visits` and its 6 column titles. |
| 2213 | `def dist_table():` | Starts the function `dist_table`. It builds Table 4 of the page: three kinds of distance for `asmread`. `build` calls it in line 2758. |
| 2214 | `    names = {"nearest": "Nearest ends of the two ranges", "medians": "Medians", "farthest": "Farthest ends of the two ranges"}` | `names`: the row names of the three kinds: nearest ends, medians, farthest ends. |
| 2215 | `    rows = [[names[k], f2(DIST[k][0]), f2(DIST[k][1])] for k in ("nearest", "medians", "farthest")]` | `rows`: one row per kind. The two values of a row come from `DIST` (lines 503 to 507): `asmread` of part L against the 8000 MT/s pool, and `asmread` of part L against F72d12. `f2` rounds each value to 0.01 GB/s. The saved output of a build shows 12.48 and 18.87 GB/s (nearest ends), 17.61 and 20.54 GB/s (medians), and 39.38 and 26.03 GB/s (farthest ends) [Ref5]. |
| 2216 | `    return table(["Kind of distance", "#Part L above the 8000 MT/s pool L-1 to L-4, GB/s", "#Part L above F72d12 (same 7200 MT/s boot, earlier run, not part of the rerun), GB/s"], rows, "narrow")` | Returns the HTML table with the class `narrow`. The column titles name the kind of distance, part L above the pool L-1 to L-4, and part L above F72d12. |

### Function `load_table`: Table 6, the load average at each launch (lines 2219 to 2254)

| Line | Source | Explanation |
|---:|---|---|
| 2219 | `def load_table():` | Starts the function `load_table`. It builds Table 6 of the page. `build` calls it in line 2771. No rate is used here. The table holds launch times and 1-minute load averages. |
| 2220 | `    hms = lambda utc, date=False: (utc[:10] + " " if date else "") + utc[11:19] + " UTC"` | `hms`: writes a UTC time stamp as `HH:MM:SS UTC`, with the date in front when `date` is true. |
| 2221 | `    what = {"A": "part A, session {s}: first of {n} processes", "L": "part L, session {s}", "C": "part C", "I": "control I (added after the first numbers were seen)"}` | `what`: the text of the column `What` per part: A, L, C and I (control I). The text of part A has places for the session number and for a number of processes. |
| 2222 | `    rows = ["7200 MT/s: first launch of every step of the rerun and of control I (added after the first numbers were seen)"]` | `rows`: the list of the table rows. It starts with the title row of the first group: the first launch of every step of the rerun and of control I, at 7200 MT/s. |
| 2223 | `    for tg in STEPS:` | Starts the loop over the 12 steps of `STEPS` (line 880). |
| 2224 | `        l = LAUNCH[tg]` | `l`: the entry of the step in `LAUNCH` (line 879). |
| 2225 | `        w = what[l["part"]].format(s=l["session"], n=len({r["proc_key"] for r in sel(dataset="rerun-A", session=l["session"])}) if l["part"] == "A" else 0)` | `w`: the text of the step. For a part A step it holds the session and the number of processes of the session. The line counts the values of `proc_key` over all part A records of the session, with every kernel included. |
| 2226 | `        if l["part"] == "C":` | Tests whether the step is a part C step. |
| 2227 | `            w = "part C" + (f", session {l['session']}" if l["session"] else ", extra process")` | Part C: the text names the session, or says `extra process` for the step without a session. |
| 2228 | `        ld = f2(l["load1_at_first_launch"])` | `ld`: the 1-minute load average at the first launch of the step, with 2 decimals. |
| 2229 | `        if l["part"] == "A":` | Tests whether the step is a part A step. |
| 2230 | `            used = sorted({(r["launch_utc"], r["proc_key"]): D(r["load1_at_launch"]) for r in A_OLD + A_NEW if r["session"] == l["session"]}.items())` | `used`: for the `read` processes of the session that the page uses (`A_OLD` and `A_NEW`), the load at the launch of each process, in launch order. |
| 2231 | `            need(used[0][1] == D(l["load1_at_first_launch"]), "part A: the first read process is not the first launch of the step")` | Hard assertion: the script stops unless the first of these processes has the load of the first launch of the step. |
| 2232 | `            ld += "<br>" + small(f"the {len(used)} read processes used: " + ", ".join(f2(v) for _, v in used))` | Adds a small line to the load cell: the number of these processes and the load at the launch of each. |
| 2233 | `        rows.append([tg, w, hms(l["first_launch"]), ld, "-" if l["gap_s"] is None else f"{int(l['gap_s'])}"])` | Adds the row of the step: the tag, the text, the time of the first launch, the load cell, and the seconds after the end of the previous 120-thread process (`gap_s`). A step without this value gets `-`. The part `meta.launches` of `facts.json` holds a load of 0.07 for the step T72A1. It holds 74.05 to 105.24 for the 9 later steps of the rerun, each with a gap of 5 s, and 0.87 and 0.91 for the 2 steps of control I [Ref2]. |
| 2234 | `    rows.append("Earlier rows shown on this page: launch of every process")` | Adds the title row of the second group: the earlier rows of the page, with the launch of every process. |
| 2235 | `    rows.append(["F72d12", "earlier run of the same boot, not part of the rerun", hms(F_OLD[0]["launch_utc"]), f2(F_OLD[0]["load1_at_launch"]), "-"])` | Row of F72d12: the launch time and the load of its first `oldread` record. |
| 2236 | `    for d, recs in (("A-1", B_A_OLD["A-1"] + B_A_NEW["A-1"]), ("A-2", B_A_OLD["A-2"] + B_A_NEW["A-2"]), ("A-3", B_A_OLD["A-3"]),` | Starts a loop over the rows A-1 to A-3 and L-1 to L-4. The records are those of the kernel `read` of both binaries (A-1, A-2) and of `bw_old` (A-3). |
| 2237 | `                    ("L-1", B_L_OLD["L-1"]), ("L-2", B_L_OLD["L-2"]), ("L-3", B_L_OLD["L-3"]), ("L-4", B_L_OLD["L-4"])):` | Continues the list of the loop: for L-1 to L-4, the `oldread` records at position 0. |
| 2238 | `        procs = {}` | `procs`: one entry per process of the row. It starts empty. |
| 2239 | `        for r in recs:` | Starts the loop over the records of the row. |
| 2240 | `            procs[r["proc_key"]] = (r["launch_utc"], D(r["load1_at_launch"]))` | Stores the launch time and the load at launch under the `proc_key` of the record. So each process is kept once. |
| 2241 | `        ps = sorted(procs.values())` | `ps`: the entries in launch order. |
| 2242 | `        times = hms(ps[0][0], True) if len(ps) == 1 else f"{hms(ps[0][0], True)[:-4]} to {hms(ps[-1][0])}"` | `times`: the launch cell. It holds the launch time of a single process with its date, or the first and the last launch time of several processes. |
| 2243 | `        rows.append([d, f"8000 MT/s, {plural(len(ps), 'process')}", times, ", ".join(f2(x[1]) for x in ps), "-"])` | Adds the row: the name, the number of processes at 8000 MT/s, the launch cell, and one load per process in launch order. |
| 2244 | `    span = lambda a, b: f"{hms(a, True)[:-4]} to {hms(b, True) if a[:10] != b[:10] else hms(b)}"` | `span`: writes two time stamps as `first to last`. The second one gets its date only when the date differs from that of the first. |
| 2245 | `    for nm, heads, what_ in (("Runner bwx, tags common-6000-*", X_POOL_HEAD, "note under Table 2"), ("Runner bwx, tags b5-rev-*", X_REV_HEAD, "another kernel order, note under Table 2")):` | Starts a loop over the two groups of the older runner bwx: the processes with the tags `common-6000-*` (`X_POOL_HEAD`) and those with the tags `b5-rev-*` (`X_REV_HEAD`, lines 1259 to 1260). |
| 2246 | `        ls, ts = sorted(h["load"] for h in heads), sorted(h["launch"] for h in heads)` | `ls`, `ts`: the loads and the launch times of the group, sorted. They come from the header facts of the processes (`bwx_header`, line 1235). |
| 2247 | `        rows.append([nm, f"8000 MT/s, {plural(len(heads), 'process')} ({what_})", span(ts[0], ts[-1]), f"{f2(ls[0])} to {f2(ls[-1])}<br>" + small("lowest to highest"), "-"])` | Adds the row of the group: the first and the last launch, and the lowest and the highest load. |
| 2248 | `    rows.append(["X2d12", "8000 MT/s, 12 modules, 1 process, shown and not used (note under Table 2)", hms(EXTRA["X2d12"]["old"][0]["launch_utc"], True), f2(EXTRA["X2d12"]["load"]), "-"])` | Row of X2d12: the launch time and the load from `EXTRA` (line 1299). |
| 2249 | `    t10 = [EXTRA[d_] for d_ in ("X1d10", "X1d10b", "BASEd10")]` | `t10`: the entries of `EXTRA` for the three boots with 10 modules. |
| 2250 | `    rows.append(["Boots with 10 modules", f"8000 MT/s, {len(t10)} processes in {len(t10)} boots (note under Table 2)", span(t10[0]["old"][0]["launch_utc"], t10[-1]["old"][0]["launch_utc"]),` | Their shared row: the launch times of the first and of the last of the three processes. |
| 2251 | `                 ", ".join(f2(x["load"]) for x in t10), "-"])` | Continues the row: one load per process. |
| 2252 | `    return table(["Step or row", "What", "Launch", "#1-minute load average at launch", "#Time since the end of the previous 120-thread process of go.sh or go2.sh, s (given for their steps only)"], rows, "load")` | Returns the HTML table with the class `load` and its 5 column titles: step or row, what, launch, the 1-minute load average at launch, and the time in seconds after the end of the previous 120-thread process of `go.sh` or `go2.sh`. The last title says that this time is given for the steps of these two scripts only. |

### `detail_fig1` and `detail_fig2`: the table views of the two figures (lines 2255 to 2277)

| Line | Source | Explanation |
|---:|---|---|
| 2255 | `def detail_fig1():` | Starts the function `detail_fig1`. It builds the table view of figure 1. `build` calls it in line 2739. |
| 2256 | `    rows = []` | `rows`: the list of the table rows. It starts empty. |
| 2257 | `    for b in F1_BLOCKS:` | Starts the loop over the blocks of `F1_BLOCKS` (line 1580). |
| 2258 | `        for g in b["groups"]:` | Starts the loop over the groups of the block. |
| 2259 | `            rows.append(f"{b['title']} · {g['title'].split(' ·')[0]}")` | Adds one title row per block and group: the block title, a middle dot, and the group title up to its own middle dot. So the words about the kind of marker are left out. |
| 2260 | `            for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 2261 | `                rows.append([lab(esc(r["name"]), *[esc(n) for n in r["notes"]]),` | Adds one table row per row of figure 1. First cell: the row name with its notes (`lab`), escaped with `esc`. |
| 2262 | `                             f2(r["old"].med), ", ".join(f2(v) for v in r["old"].v), f2(r["new"].med), ", ".join(f2(v) for v in r["new"].v), drop_txt(r["drops"])])` | Continues the row: the median of the old read kernel, its interval rates, the median of the load-only loop, its interval rates, and the drop. Medians and rates are printed with 2 decimals (`f2`). The interval rates stand in the order of `Rg.v`: by launch time, then by interval number. `drop_txt` (line 425) gives the lowest and the highest drop of the row with 1 decimal, or one value when both are printed equal. |
| 2263 | `    return table(["Row", "#Old read kernel: median, GB/s", "#Its intervals, GB/s", "#Load-only loop: median, GB/s", "#Its intervals, GB/s", "#Drop"], rows, "detail")` | Returns the HTML table with the class `detail` and its 6 column titles. |
| 2266 | `def detail_fig2():` | Starts the function `detail_fig2`. It builds the table view of figure 2, with every interval. `build` calls it in line 2760. The page shows this table folded: it stays closed until the reader opens it. |
| 2267 | `    """Every interval of figure 2. A row carries the label that the figure shows, and each note once."""` | Comment: the documentation text. The table holds every interval of figure 2. A row carries the label that the figure shows, and each note once. |
| 2268 | `    rows = []` | `rows`: the list of the table rows. It starts empty. |
| 2269 | `    for nm, blocks in (("Old read kernel", P_OLD_BLOCKS), ("Load-only loop", P_NEW_BLOCKS)):` | Starts the loop over the two panels: `P_OLD_BLOCKS` for the old read kernel and `P_NEW_BLOCKS` for the load-only loop. |
| 2270 | `        for b in blocks:` | Starts the loop over the blocks of the panel. |
| 2271 | `            for g in b["groups"]:` | Starts the loop over the groups of the block. |
| 2272 | `                rows.append(" · ".join([nm, b["title"], g["title"] + (", " + " ".join(g["sub"]) if g.get("sub") else "")]))` | Adds one title row per group: the panel name, the block title and the group title, joined with middle dots. The sub-title of the group (`g["sub"]`) follows when the group has one. |
| 2273 | `                for r in g["rows"]:` | Starts the loop over the rows of the group. |
| 2274 | `                    rows.append([lab(esc(r["label"]), *[esc(n) for n in plain_notes(r["notes"])]), str(r["rg"].n), ", ".join(f2(v) for v in sorted(r["rg"].v))])` | Adds one table row with three cells: the label of the row with its notes as plain text, the number of intervals (`rg.n`), and the rate of every interval of the row (`rg.v`). These rates are the values of `val` for the records of the row. They are sorted from lowest to highest, and `f2` rounds each one to 0.01 GB/s. No rate is summed or averaged here. |
| 2275 | `    return table(["Row", "#n intervals", "Intervals, GB/s, sorted"], rows, "detail")` | Returns the HTML table with the class `detail` and its 3 column titles. |

### `facts_words` and `fw`: definitions copied from the word list of `FACTS.md` (lines 2278 to 2305)

| Line | Source | Explanation |
|---:|---|---|
| 2278 | `# ------------------------------------------------------------------ word list` | Comment: a section mark. The code of the word list of the page starts here. |
| 2279 | `def facts_words():` | Starts the function `facts_words`. It reads the word list of `FACTS.md` and returns a dictionary from each term to its definition. |
| 2280 | `    m = re.search(r"<summary>Words used here</summary>(.*?)</details>", FMD, re.S)` | Searches `FMD` (the text of `FACTS.md`, line 235) for the word list. The pattern matches the element `<summary>Words used here</summary>` and the text after it, up to the next `</details>`. Group 1 holds that text. `re.S` lets `.` match line breaks too. |
| 2281 | `    need(m, "FACTS.md: word list not found")` | Hard assertion: the script stops when this part is missing. |
| 2282 | `    out = {}` | `out`: the result dictionary. It starts empty. |
| 2283 | `    for line in m.group(1).splitlines():` | Starts the loop over the lines of the word list. |
| 2284 | `        k = re.match(r"^- \*\*(.+?)\*\*: (.*)$", line)` | Tests whether the line has the form `- **term**: definition`. Group 1 of the pattern holds the term between the two pairs of `**`. Group 2 holds the rest of the line, the definition. |
| 2285 | `        if k:` | Tests whether the line matched. |
| 2286 | `            out[k.group(1)] = k.group(2)` | Stores the definition under the term. |
| 2287 | `    return out` | Returns the dictionary. |
| 2290 | `FW_WORDS = facts_words()` | `FW_WORDS`: the dictionary that `facts_words` returns. |
| 2293 | `def fw(key, swap=()):` | Starts the function `fw`. It returns the definition of the term `key` from `FW_WORDS` as HTML text for the page. |
| 2294 | `    """A definition of the word list of FACTS.md, reused word for word ("this sheet" becomes "this page").` | Comment: the documentation text. A definition of the word list of `FACTS.md` is used again word for word. Only `this sheet` becomes `this page`. |
| 2295 | `    swap = (old, new): one phrase of the sheet that this page words in another way. The phrase must be present."""` | Comment: the documentation text, continued. `swap` is a pair (old, new): one phrase of the sheet that the page words in another way. The phrase must be present. |
| 2296 | `    need(key in FW_WORDS, f"FACTS.md word list: term '{key}' not found")` | Hard assertion: the script stops when the term is not in `FW_WORDS`. |
| 2297 | `    t = FW_WORDS[key]` | `t`: the definition text. |
| 2298 | `    if swap:` | Tests whether `swap` was given. |
| 2299 | `        need(swap[0] in t, f"FACTS.md word list, term '{key}': phrase '{swap[0]}' not found")` | Hard assertion: the script stops when the phrase `swap[0]` is not in the definition. |
| 2300 | `        t = t.replace(swap[0], swap[1])` | Replaces that phrase by `swap[1]`. |
| 2301 | `    t = re.sub(r"\s*\[Ref\d+\]", "", t).replace("this sheet", "this page").replace("This sheet", "This page")` | Removes each mark of the form `[RefN]`, with a number in place of N, and the white space before it. Then `this sheet` becomes `this page`, also with a capital first letter. |
| 2302 | ``    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(t).replace("&quot;", '"'))`` | `esc` escapes the HTML special characters. The double quotes are then written back as plain characters. Then a name between two backtick characters (the code marks of Markdown) becomes a `code` element. Group 1 of the pattern holds the name. |
| 2303 | `    return t[0].upper() + t[1:]` | Returns the text with a capital first letter. |

### Part A process counts, and the tags that the word list names (lines 2306 to 2322)

| Line | Source | Explanation |
|---:|---|---|
| 2306 | `BOOT8 = RERUN["boot_id"][:8]` | `BOOT8`: the first 8 characters of the boot id of the rerun. |
| 2307 | `# part A: how many processes a session ran, and how many of them this page uses (the scope cut is stated in the word list)` | Comment: the next lines count how many processes a session of part A ran, and how many of them the page uses. The word list states this cut of scope. |
| 2308 | `A_ALL = sel(dataset="rerun-A")` | `A_ALL`: all records of the dataset `rerun-A`, with every kernel and both binaries. Lines 2308 to 2316 read no rate. |
| 2309 | `A_KERNELS = [k for k in ("read", "write", "copy", "asmread", "asmwrite", "asmcopy") if any(r["kernel"] == k for r in A_ALL)]` | `A_KERNELS`: those of six kernel names that occur in `A_ALL`, in the order of the list in this line. |
| 2310 | `A_PER_SESSION = sorted({len({r["proc_key"] for r in A_ALL if r["session"] == s_}) for s_ in (1, 2, 3)})` | `A_PER_SESSION`: the number of processes of each session (different values of `proc_key`), as a sorted list of the different counts. |
| 2311 | `A_USED_PER_SESSION = sorted({len({r["proc_key"] for r in A_OLD + A_NEW if r["session"] == s_}) for s_ in (1, 2, 3)})` | `A_USED_PER_SESSION`: the same for the `read` processes that the page uses (`A_OLD + A_NEW`). The records of `facts.json` give 6 kernels, 24 processes per session and 4 used processes per session [Ref2]. |
| 2312 | `# part A: round 2 runs the processes of round 1 in the reverse order (launch order of session 1, by binary and kernel)` | Comment: in part A, round 2 runs the processes of round 1 in the reverse order. The test uses the launch order of session 1, by binary and kernel. |
| 2313 | `a_order = {rnd: [k for k, _ in sorted({(r["binary"], r["kernel"]): r["launch_utc"] for r in A_ALL if r["session"] == 1 and r["round"] == rnd}.items(), key=lambda kv: kv[1])] for rnd in (1, 2)}` | `a_order`: for session 1 and each round, the pairs (binary, kernel) in the order of their launch time. The inner dictionary keeps one launch time per pair, and `sorted` orders the pairs by that time. |
| 2314 | `need(len(a_order[1]) == 12 and a_order[2] == a_order[1][::-1], "part A, session 1: round 2 does not run the 12 processes of round 1 in the reverse order")` | Hard assertion: the script stops unless round 1 has 12 such pairs and round 2 has the same 12 in the reverse order. |
| 2315 | `need({r["kernel"] for r in A_ALL} == set(A_KERNELS) and {r["binary"] for r in A_ALL} == {"bw_old", "bw_new"} and {r["round"] for r in A_ALL} == {1, 2}` | Hard assertion, first conditions: part A holds only the kernels of `A_KERNELS`, the binaries `bw_old` and `bw_new`, and the rounds 1 and 2. |
| 2316 | `     and A_PER_SESSION == [len(A_KERNELS) * 2 * 2] and len(A_USED_PER_SESSION) == 1, "part A: a session is not kernels x 2 binaries x 2 rounds")` | Continues the condition: every session has the same number of processes, the number of kernels x 2 x 2 (2 binaries, 2 rounds). With 6 kernels this is 24. The number of used processes must be equal in all sessions too. |
| 2317 | `# names of argument lines that the tooltips of the earlier bwx12 rows show, and the tags of row A-3` | Comment: the names of argument lines that the tooltips of the earlier bwx12 rows show, and the tags of row A-3. |
| 2318 | `LINE_TAGS = sorted({r["tag"] for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]} \| {r["tag"] for r in F_OLD + F_ASM})` | `LINE_TAGS`: the sorted tags of the records that the page uses from the rows L-1 to L-4 and from F72d12. |
| 2319 | `need(LINE_TAGS == sorted([LINE_L, "p1nop", "p2add", "thp", "st1", "st2", "st3"])` | Hard assertion, first condition: these tags are `LINE_L`, `p1nop`, `p2add`, `thp`, `st1`, `st2` and `st3`. `LINE_L` (line 1196) is the name of the argument line in `like.spec`. It is `a6456` in that file. |
| 2320 | `     and all(r["file"] == r["tag"] + ".csv" for d in LPOOL for r in B_L_OLD[d] + B_L_ASM[d]), "rows L-1 to L-4 and F72d12: the tags are not the expected line names, or a csv file has another name")` | Continues the condition: the csv file of each of these records of the rows L-1 to L-4 has the name of its tag plus `.csv`. Then comes the message. |
| 2321 | `A3_TAGS = sorted({r["tag"] for r in B_A_OLD["A-3"]})` | `A3_TAGS`: the sorted tags of row A-3. |
| 2322 | `need(A3_TAGS == [f"onebuf-ms500-{i}" for i in (1, 2, 3)], "row A-3: unexpected tags")` | Hard assertion: the script stops unless they are `onebuf-ms500-1`, `onebuf-ms500-2` and `onebuf-ms500-3`. |

### The list `WORDS`: the word list of the page (lines 2323 to 2397)

| Line | Source | Explanation |
|---:|---|---|
| 2323 | `WORDS = [` | `WORDS`: the word list of the page, a list of pairs (term, definition). `build` (line 2677) writes it into the folded part `Words used here` of the page. |
| 2324 | `    ("Q1, Q2", "The two questions of the rerun. Q1: is the whole-chip read rate of the new read kernel still below that of the old read kernel at 7200 MT/s, and by how much. Q2: did the rate of either kernel differ from the earlier runs at 8000 MT/s."),` | Entry `Q1, Q2`: the two questions of the rerun. The text is typed: it is fixed text in the source, not a computed value. Q1 asks whether the new read kernel is still below the old one at 7200 MT/s, and by how much. Q2 asks whether the rate of either kernel differed from the earlier runs at 8000 MT/s. |
| 2325 | `    ("Rerun", f"The {GO_DONE} steps that go.sh ran at 7200 MT/s on 2026-11-17 from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC: 3 sessions of parts A, L and C, and one more part C process. "` | Entry `Rerun`: this line prints `GO_DONE` (line 874), the number of `done` lines in the log of `go.sh`, as the number of steps. Line 875 asserts that it is 10. It also prints the start time and the end time of `go.sh` from `RERUN`. The slice `[11:19]` takes the time of day `HH:MM:SS` from the time stamp. |
| 2326 | `              "Parts A and L repeat tests that ran earlier at 8000 MT/s. Part C is new. No earlier run in the results folder used one of its two argument lines. "` | Continues the entry: the parts A and L repeat tests that ran earlier at 8000 MT/s, and part C is new. No earlier run in the results folder used one of its two argument lines. |
| 2327 | `              f"Runs of the older runner bwx timed the same three kernels in both orders inside a longer sequence of {len(X_SEQ)} kernels (note under Table 2). "` | Continues the entry: `len(X_SEQ)` (line 1279), the number of kernels in the sequence of the older runner bwx. Line 1280 asserts that it is 8. |
| 2328 | `              "Control I (added after the first numbers were seen) and F72d12 (earlier run of the same boot) are not part of the rerun."),` | Continues the entry: control I and F72d12 are not part of the rerun. |
| 2329 | `    ("CRB", fw("CRB")),` | Entry `CRB`: copied from the word list of `FACTS.md` with `fw` (line 2293). |
| 2330 | `    ("Whole chip, 120 threads", "The runs use 120 threads on CPUs 0-119 only. Each thread reads its own buffer of 256 MiB from memory (1 MiB is 2^20 bytes)."),` | Entry `Whole chip, 120 threads`, typed: the runs use 120 threads on the CPUs 0 to 119 only. Each thread reads its own buffer of 256 MiB (1 MiB is `2^20` bytes). |
| 2331 | `    ("MT/s", fw("MT/s")),` | Entry `MT/s`: copied with `fw`. |
| 2332 | `    ("Memory module", "One DIMM (dual in-line memory module). CRB has 12 slots for them."),` | Entry `Memory module`, typed: one DIMM. CRB has 12 slots for them. |
| 2333 | `    ("GB/s", "Gigabytes per second. 1 GB is 1e9 bytes."),` | Entry `GB/s`, typed. It states the unit of every rate of the page: gigabytes per second, where 1 GB is 1e9 bytes. |
| 2334 | `    ("Read kernel", fw("Read kernel")),` | Entry `Read kernel`: copied with `fw`. |
| 2335 | `    ("Old read kernel", fw("Old read kernel")),` | Entry `Old read kernel`: copied with `fw`. |
| 2336 | `    ("New read kernel", fw("New read kernel")),` | Entry `New read kernel`: copied with `fw`. |
| 2337 | `    ("asmread", fw("asmread")),` | Entry `asmread`: copied with `fw`. |
| 2338 | `    ("Load-only loop", fw("Load-only loop")),` | Entry `Load-only loop`: copied with `fw`. In `FACTS.md` it means the new read kernel or `asmread`. |
| 2339 | `    ("bandwidth.c, bw_old, bw_new", fw("bandwidth.c, bw_old, bw_new")),` | Entry `bandwidth.c, bw_old, bw_new`: copied with `fw`. |
| 2340 | `    ("bwx12, bwx11, bwx", fw("bwx12, bwx11, bwx", ("bwx12 is the runner of the 2026-11-15 investigation.",` | Entry `bwx12, bwx11, bwx`: copied with `fw`. The `swap` argument replaces one sentence of the `FACTS.md` text. |
| 2341 | `                                                    "bwx12 is the runner of the investigation of 2026-11-15 into the lower read rate of the load-only loop."))),` | Continues the call: the longer sentence that takes its place. It says that bwx12 is the runner of the investigation of 2026-11-15 into the lower read rate of the load-only loop. |
| 2342 | `    ("Process, interval, round, position", "A process is one start of a benchmark binary. An interval is one timed measurement inside a process. "` | Entry `Process, interval, round, position`, typed: a process is one start of a benchmark binary, and an interval is one timed measurement inside a process. |
| 2343 | `                                           "bwx12 times a sequence of kernels and repeats the sequence. Each repeat is a round (counted from 0). "` | Continues the entry: bwx12 times a sequence of kernels and repeats it. Each repeat is a round, counted from 0. |
| 2344 | `                                           "The position is the place of a kernel in the sequence (counted from 0). "` | Continues the entry: the position is the place of a kernel in the sequence, counted from 0. |
| 2345 | `                                           f"In part A the script runs its {A_PER_SESSION[0] // 2} read, write and copy processes twice. Each run is a round (1 or 2). Round 2 runs the processes in the reverse order."),` | Continues the entry, for part A: the script runs its read, write and copy processes twice, and each run is a round (1 or 2). Round 2 runs the processes in the reverse order (line 2314). The line prints `A_PER_SESSION[0] // 2`, the number of processes of one round. With 24 processes per session this is 12 [Ref2]. |
| 2346 | `    ("Rate", fw("Rate, total", ("bwx runners", "bwx12 and bwx"))),` | Entry `Rate`: copied with `fw` from the `FACTS.md` entry `Rate, total`. It says how the page gets a rate. For part A it is the column `aggregate_GBps` that `bandwidth.c` prints. For bwx12 and bwx it is the sum over the threads of bytes / elapsed time. The unit is GB/s. `swap` replaces the words `bwx runners` by `bwx12 and bwx`. |
| 2347 | `    ("Interval row, thread rows", "bwx12 and bwx write two kinds of row into a csv file that this page uses. An interval row starts with the letter I and holds one interval. "` | Entry `Interval row, thread rows`, typed: bwx12 and bwx write two kinds of row into a csv file that the page uses. An interval row starts with the letter I and holds one interval. |
| 2348 | `                                  "A thread row starts with the letter T and holds one thread of one interval. The 120 thread rows of an interval follow its interval row."),` | Continues the entry: a thread row starts with the letter T and holds one thread of one interval. The 120 thread rows of an interval follow its interval row. |
| 2349 | `    ("Median", "The middle value of a sorted list. For an even number of values it is the mean of the two middle values."),` | Entry `Median`, typed: the middle value of a sorted list, or the mean of the two middle values for an even number of values. |
| 2350 | `    ("Facts sheet", "The file FACTS.md with its data file facts.json. It is the detailed record of this rerun. A script built it from the raw result files."),` | Entry `Facts sheet`, typed: the file `FACTS.md` with its data file `facts.json`. |
| 2351 | `    ("R, S", "Short forms of two folders: R is the results folder, and S is the scratch folder of this rerun. The reference list gives both paths."),` | Entry `R, S`, typed: the short forms of the results folder and of the scratch folder of the rerun. |
| 2352 | `    ("Session, step", fw("Session") + " go.sh ran 3 sessions and then one more part C process (T72C4). The n column calls T72C4 the extra process. "` | Entry `Session, step`: the `FACTS.md` definition of `Session` (`fw`), and typed text after it. `go.sh` ran 3 sessions and then one more part C process, T72C4. The n column calls T72C4 the extra process. |
| 2353 | `                      "A step is one part of one session, the extra part C process, or one process of control I (added after the first numbers were seen)."),` | Continues the entry: a step is one part of one session, the extra part C process, or one process of control I. |
| 2354 | `    ("go.sh, go2.sh", "The driver scripts. go.sh ran the planned rerun. go2.sh ran control I (added after the first numbers were seen)."),` | Entry `go.sh, go2.sh`, typed: the driver scripts. `go.sh` ran the planned rerun, and `go2.sh` ran control I. |
| 2355 | `    ("Part A", fw("Part A") + f" Each session ran {A_PER_SESSION[0]} processes: {len(A_KERNELS)} kernels ({', '.join(A_KERNELS)}) x 2 binaries x 2 rounds. "` | Entry `Part A`: the `FACTS.md` definition (`fw`), and after it the counts of lines 2309 to 2311: the processes per session and the kernel names. |
| 2356 | `               f"This page uses the {A_USED_PER_SESSION[0]} read processes of each session. The facts sheet holds the other {A_PER_SESSION[0] - A_USED_PER_SESSION[0]} (its sections 3.1 and 5) {ref('facts')}."),` | Continues the entry: the number of `read` processes of each session that the page uses, and the difference as the number of the other processes, which the facts sheet holds. With the records of `facts.json` these three counts are 24, 4 and 20 processes [Ref2]. |
| 2357 | `    ("Part L", "One bwx12 process that times oldread, then asmread, then three other test loops that this page does not use. The process runs this sequence twice (rounds 0 and 1)."),` | Entry `Part L`, typed: one bwx12 process that times `oldread`, then `asmread`, then three other test loops that the page does not use, in two rounds. Lines 275 to 276 select only `oldread` at position 0 and `asmread` at position 1 from part L. |
| 2358 | `    ("Part C, cfwd, crev, kernel order", fw("Part C") + " Each process runs its sequence twice (rounds 0 and 1). The kernel order is the order of the kernels in this sequence."),` | Entry `Part C, cfwd, crev, kernel order`: the `FACTS.md` definition of `Part C` (`fw`), and typed text after it: each process runs its sequence twice, and the kernel order is the order of the kernels in this sequence. |
| 2359 | `    ("Control I", fw("Control I")),` | Entry `Control I`: copied with `fw`. |
| 2360 | `    ("F72d12", "One process of the part L line. It ran at " + hm(F_OLD[0]["launch_utc"]) + " on 2026-11-17 for another test, in the same boot as the rerun and before it. It is not part of the rerun."),` | Entry `F72d12`, typed, with one value from the data: the launch time of the first record of `F_OLD`. `hm` (line 377) writes it as `HH:MM UTC`. |
| 2361 | `    ("T72A1 to T72I2", "The names of the result folders of the rerun (parts A, L, C) and of control I (I, added after the first numbers were seen): T72, then the letter, then a number."),` | Entry `T72A1 to T72I2`, typed: the names of the result folders of the rerun and of control I. |
| 2362 | `    ("A-1, A-2, A-3", "The 8000 MT/s rows for part A, all of 2026-11-13, with the same two binaries. A-1 is the original test. A-2 is a second run with another process order. A-3 is three more processes of bw_old read."),` | Entry `A-1, A-2, A-3`, typed: the 8000 MT/s rows for part A. |
| 2363 | `    ("L-1, L-2, L-3, L-4", "The 8000 MT/s rows for parts L and C, all with bwx12. L-1 (2026-11-17) used the argument line of part L unchanged. L-2 to L-4 (2026-11-15) used 4 s measurements and counted other hardware events of the CPU. From these rows only oldread at position 0 and asmread at position 1 are used."),` | Entry `L-1, L-2, L-3, L-4`, typed: the 8000 MT/s rows for the parts L and C. It states which intervals the page takes from these rows: only `oldread` at position 0 and `asmread` at position 1. Lines 291 to 292 make this selection. |
| 2364 | `    (", ".join(LINE_TAGS), f"Names of argument lines. In the rows L-1 to L-4 and in F72d12 (earlier run of the same boot, not part of the rerun) a bwx12 process carries the name of its line, and so does its csv file. "` | An entry whose term is the list of the tags of `LINE_TAGS` (line 2318). The definition says that these are names of argument lines. In the rows L-1 to L-4 and in F72d12 a bwx12 process carries the name of its line, and so does its csv file. |
| 2365 | `                           f"A tooltip names such a process by this name. {LINE_L} is the part L line."),` | Continues the entry: a tooltip names such a process by this name. The last sentence names `LINE_L` as the part L line. |
| 2366 | `    (f"{A3_TAGS[0]} to {A3_TAGS[-1]}", "The tags that the csv file of row A-3 gives its three processes."),` | An entry whose term names the first and the last tag of row A-3 (line 2321). |
| 2367 | `    ("Line, argument line, spec file", fw("Line, argument line") + " A spec file is a text file with one argument line."),` | Entry `Line, argument line, spec file`: the `FACTS.md` definition of `Line, argument line` (`fw`), and one typed sentence about the spec file. |
| 2368 | `    ("Visit", fw("Visit")),` | Entry `Visit`: copied with `fw`. |
| 2369 | `    ("Idle start", fw("Idle start")),` | Entry `Idle start`: copied with `fw`. |
| 2370 | `    ("Whole-pass stop", fw("Whole-pass stop")),` | Entry `Whole-pass stop`: copied with `fw`. |
| 2371 | `    ("Pass count", "Part A only: the number of buffer passes that all 120 threads completed in one interval."),` | Entry `Pass count`, typed: for part A only, the number of buffer passes that all 120 threads completed in one interval. |
| 2372 | `    ("Pair, drop", "A pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A the two kernels run in two processes. There the drop uses the medians of the two processes of one session and round."),` | Entry `Pair, drop`, typed. A pair is one load-only interval and one old-kernel interval of the same process and round. The drop of a pair is (1 - load-only rate / old-kernel rate) x 100, in percent. In part A it uses the medians of the two processes of one session and round. This is the computation of `drop` (line 417) and of `a_pair` (line 444). |
| 2373 | `    ("List of 8000 MT/s rows", "The 8000 MT/s runs with 12 modules that this page compares with: rows A-1 to A-3 and L-1 to L-4. The rules file fixed them before the run. "` | Entry `List of 8000 MT/s rows`, typed: the 8000 MT/s runs with 12 modules that the page compares with, the rows A-1 to A-3 and L-1 to L-4. The rules file fixed them before the run. |
| 2374 | `                               "The rules file also names rows of two older runner binaries (bwx11 and bwx). This page does not use the bwx11 rows. It shows the bwx rows in one note under Table 2 only. "` | Continues the entry: what the page leaves out. The rules file also names rows of two older runner binaries. The bwx11 rows are not used. The bwx rows appear in one note under Table 2 only. |
| 2375 | `                               "Two more notes under Table 2 show rows that the rules file names and that are not rows of the list: row X2d12, and three boots with 10 modules. No wording comes from them."),` | Continues the entry: two more notes under Table 2 show row X2d12 and the three boots with 10 modules. No wording comes from them. The tables 5 and 6 name these rows and print no rate of them. |
| 2376 | `    ("Pool", fw("Pool")),` | Entry `Pool`: copied with `fw`. |
| 2377 | `    ("Overlap of two ranges", fw("Ranges overlap")),` | Entry `Overlap of two ranges`: copied with `fw` from the `FACTS.md` entry `Ranges overlap`. |
| 2378 | `    ("Distance of the nearest ends, farthest ends", fw("Distance of the nearest ends") + " The distance of the farthest ends is the highest value of the higher range minus the lowest value of the lower range."),` | Entry `Distance of the nearest ends, farthest ends`: the `FACTS.md` definition of the nearest ends (`fw`), and one typed sentence: the distance of the farthest ends is the highest value of the higher range minus the lowest value of the lower range. |
| 2379 | `    ("n", fw("n")),` | Entry `n`: copied with `fw`. |
| 2380 | `    ("Rules V1 to V4, F1, F2", fw("Rules V1 to V4, F1, F2")),` | Entry `Rules V1 to V4, F1, F2`: copied with `fw`. |
| 2381 | `    ("Boot, boot id", f"A boot is one run of the machine from a start to the next restart. The boot id is a random identifier that Linux creates at each start. Equal boot ids mean the same boot. The rerun ran in boot {BOOT8} (the first 8 characters of its boot id)."),` | Entry `Boot, boot id`, typed, with one value from the data: `BOOT8` (line 2306), the first 8 characters of the boot id of the rerun. |
| 2382 | `    ("MemTotal", fw("MemTotal")),` | Entry `MemTotal`: copied with `fw`. |
| 2383 | `    ("State line", fw("State line")),` | Entry `State line`: copied with `fw`. |
| 2384 | `    ("Load average, load", fw("Load average")),` | Entry `Load average, load`: copied with `fw` from the `FACTS.md` entry `Load average`. |
| 2385 | `    ("%CPU, process list", "A process list is the output of the tool ps that a run script saves before a launch. "` | Entry `%CPU, process list`: one typed sentence about the process list. |
| 2386 | `                           + fw("%CPU", ("the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is", "%CPU is the column pcpu of this output. It is"))),` | Continues the entry: the `FACTS.md` definition of `%CPU` (`fw`). `swap` replaces its first words. The new words join the definition to the typed sentence. |
| 2387 | `    ("pr/ttyAMA-1", fw("pr/ttyAMA-1", ("By its name it prints kernel messages", "Its name suggests that it prints Linux kernel messages"))),` | Entry `pr/ttyAMA-1`: copied with `fw`. `swap` replaces the words `By its name it prints kernel messages` by `Its name suggests that it prints Linux kernel messages`. |
| 2388 | `    ("Exit status", "The number that a process returns when it ends. 0 means success."),` | Entry `Exit status`, typed. |
| 2389 | `    ("Root", "Administrator rights on the machine. They were not approved for this task."),` | Entry `Root`, typed: administrator rights on the machine. The text says that they were not approved for this task. |
| 2390 | `    ("Journal, kernel log", "The kernel log is the list of messages of the Linux kernel. The journal is the saved system log of one boot. It holds the kernel log."),` | Entry `Journal, kernel log`, typed. |
| 2391 | `    ("Hardware error record, corrected record", fw("Hardware error record")),` | Entry `Hardware error record, corrected record`: copied with `fw` from the `FACTS.md` entry `Hardware error record`. |
| 2392 | `    ("Module list", "The output of the command <code>dmidecode -t 17</code>. It holds one entry &quot;Memory Device&quot; per memory module, with the configured speed of the module."),` | Entry `Module list`, typed: the output of the command `dmidecode -t 17`, with one entry per memory module. |
| 2393 | `    ("Firmware setting, DIMM Frequency, TXREQ", "A firmware setting is a value that the machine applies at its next start. &quot;DIMM Frequency&quot; sets the memory speed. TXREQ is a group of settings that were changed for another investigation."),` | Entry `Firmware setting, DIMM Frequency, TXREQ`, typed. |
| 2394 | `    ("GiB", "2^30 bytes."),` | Entry `GiB`, typed: `2^30` bytes. |
| 2395 | `    ("est.", fw("est.")),` | Entry `est.`: copied with `fw`. |
| 2396 | `]` | Ends the list `WORDS`. |

### `nw`, the three sentences `SHORT`, and the list `SHORT_MORE` (lines 2398 to 2436)

| Line | Source | Explanation |
|---:|---|---|
| 2398 | `# ------------------------------------------------------------------ text of the page` | Comment: a section mark. The text of the page starts here. |
| 2399 | `def nw(text):` | Starts the function `nw`. It keeps a number and its unit on one line. |
| 2400 | `    """A number with its unit that must not break across two lines."""` | Comment: the documentation text. The text is a number with its unit that must not break across two lines. |
| 2401 | `    return f'<span class="num">{text}</span>'` | Returns the text inside a `span` element of the class `num`. The style block keeps such a text on one line (line 2638). |
| 2404 | `OLD_PARTS = [(rA_old, rPA_old), (rC_old, rPL_old), (rL_old, rPL_old)]          # old read kernel: parts A, C, L of the rerun` | `OLD_PARTS`: three pairs of ranges for the old read kernel. Each pair is a 7200 MT/s range and its 8000 MT/s range: part A with the pool A-1 to A-3, part C with the pool L-1 to L-4, and part L with the same pool. Comment at the end of the line: these are the parts A, C and L of the rerun. |
| 2405 | `need([a.overlaps(b) for a, b in OLD_PARTS] == [True, True, False], "Short version: the old read kernel does not overlap in parts A and C, with part L as the third part")` | Hard assertion: the script stops unless the three overlap results are true, true, false. Sentence 2 of the Short version states this result. |
| 2406 | `c_ao, c_aa = Q1["C_ao"]["drops"], Q1["C_aa"]["drops"]` | `c_ao`, `c_aa`: the drops of part C in percent, computed in lines 431 to 439. `c_ao` holds the drops of the 4 pairs with `read` directly after `oldread`. `c_aa` holds the drops of the 4 pairs with `read` directly after `asmread`. |
| 2407 | `need(only((r["kernel_before"] for r in C_READ_AA), "kernel before") == "asmread", "part C, second order: read does not follow asmread")` | Hard assertion: the script stops unless every record of `C_READ_AA` has `asmread` as its `kernel_before`. |
| 2408 | `need(VISIT_LO == rF_asm.lo and VISIT_HI == rL_asm.hi, "the span of the three visits does not run from F72d12 to part L")` | Hard assertion: the script stops unless `VISIT_LO` is the lowest `asmread` rate of F72d12 and `VISIT_HI` is the highest `asmread` rate of part L. |
| 2409 | `need(len(c_ao) == len(c_aa), "part C: the two kernel orders have different numbers of pairs")` | Hard assertion: the script stops unless both kernel orders have the same number of pairs. |
| 2410 | `c_all = c_ao + c_aa` | `c_all`: the two lists joined, 8 drops. |
| 2411 | `SHORT = [` | `SHORT`: the three sentences of the Short version of the page. They hold percent values and counts. They hold no rate in GB/s. |
| 2412 | `    f"At 7200 MT/s with 12 memory modules, the new read kernel (a benchmark loop with loads only) still read {nw(f1(min(c_all)) + ' %')} to {nw(f1(max(c_all)) + ' %')} less than the "` | Sentence 1, first half. It prints `min(c_all)` and `max(c_all)`: the lowest and the highest drop of the 8 pairs of part C. A pair is one interval of the bwx12 kernel `read` (the new read kernel) and the `oldread` interval of the same process and round. Its drop is (1 - rate of `read` / rate of `oldread`) x 100. Both rates are values of `val`: the sum of bytes / `elapsed_s` / 1e9 over the 120 thread rows of the interval (line 186), kept with 6 decimals. `f1` rounds a drop to 0.1 % only when it is printed. `nw` keeps each number with its percent sign on one line. |
| 2413 | `    f"old read kernel (each load is followed by an add) in {len(c_all)} pairs of 6 s measurements.",` | Sentence 1, second half. `len(c_all)` prints the number of pairs. The words `6 s measurements` are typed. Line 317 asserts a `min_ms` of 6000 (6 s) for these records. The saved output of a build shows 29.7 % to 31.2 % in 8 pairs [Ref5]. |
| 2414 | `    "For the old read kernel, no difference from the earlier 8000 MT/s runs was seen in two of the three tests (parts A and C), "` | Sentence 2, first half, typed: for the old read kernel, no difference from the earlier 8000 MT/s runs was seen in two of the three tests (the parts A and C). Line 2405 asserts this result. |
| 2415 | `    f"and in the third (part L) it was lower by {nw(f1(L_OLD_NEAR_PCT) + ' %')} (nearest ends of the two ranges) and {nw(f1(L_OLD_MED_PCT) + ' %')} (medians).",` | Sentence 2, second half. It prints `L_OLD_NEAR_PCT` (line 491) and `L_OLD_MED_PCT` (line 492) for the old read kernel in part L. The first is the distance of the nearest ends in percent of the lower end of the 8000 MT/s range. The second is the difference of the medians in percent of the 8000 MT/s median. The saved output of a build shows 0.3 % and 1.3 % [Ref5]. |
| 2416 | `    f"The load-only loop gave higher rates than these 8000 MT/s runs in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2), "` | Sentence 3, first half. It prints `len(RERUN_CMP_NEW)` (line 2066): the number of comparisons of the load-only loop of the rerun with 8000 MT/s rows. Line 2068 stops the script unless the 7200 MT/s range lies above the 8000 MT/s range in each of them. The saved output of a build shows 4 comparisons [Ref5]. |
| 2417 | `    "and the data do not show that the memory speed caused either difference.",` | Sentence 3, second half, typed: the data do not show that the memory speed caused either difference. |
| 2418 | `]` | Ends the list `SHORT`. |
| 2419 | `need(n7200(L_OLD) == n7200(L_ASM) and n8000(P_L_OLD) == n8000(P_L_ASM), "Short version, part L: n differs between the two kernels")` | Hard assertion: the text of n of part L must be equal for `oldread` and `asmread`. The same holds for the pool L-1 to L-4. Line 2426 prints one n for both kernels. |
| 2420 | `# Table 2 holds load-only comparisons that are not part of the rerun (F72d12 lies inside the 8000 MT/s range). So the count of sentence 3 must name its scope.` | Comment: Table 2 holds load-only comparisons that are not part of the rerun. F72d12 lies inside the 8000 MT/s range. So the count of sentence 3 must name its scope. |
| 2421 | `need(f"in all {len(RERUN_CMP_NEW)} comparisons of the rerun (Table 2)" in SHORT[2], "Short version, sentence 3: the count of comparisons does not name the rerun as its scope")` | Hard assertion: sentence 3 must hold the phrase `in all N comparisons of the rerun (Table 2)`, with N from `RERUN_CMP_NEW`. Line 2416 types the same phrase. So this test can fail only after an edit of that line. |
| 2422 | `need(rPL_asm.lo <= rF_asm.lo and rF_asm.hi <= rPL_asm.hi and rF_asm.hi < rL_asm.lo, "Short version: F72d12 is not inside the 8000 MT/s range and below part L")` | Hard assertion: the `asmread` range of F72d12 must lie inside the range of the 8000 MT/s pool. Its highest value must be below the lowest `asmread` value of part L. |
| 2423 | `SHORT_MORE = UL([` | `SHORT_MORE`: the bullet list of five items that the page shows under the three sentences. `UL` (line 1493) returns the HTML list and adds its items to `PROSE` for the word count. |
| 2424 | `    f"Sentence 1 (part C): {f1(min(c_ao))} % to {f1(max(c_ao))} % lower when the new read kernel ran directly after the old read kernel, "` | Item 1, for sentence 1: the lowest and the highest drop of `c_ao`, each with 1 decimal. These are the pairs in which the new read kernel ran directly after the old read kernel. |
| 2425 | `    f"and {f1(min(c_aa))} % to {f1(max(c_aa))} % lower directly after asmread, a hand-written loop with the same loads ({len(c_ao)} pairs / 2 processes each).",` | Continues item 1: the lowest and the highest drop of `c_aa` (directly after `asmread`), and the number of pairs per order. |
| 2426 | `    f"Part L (sentences 2 and 3), 7200 MT/s against 8000 MT/s: n = {n7200(L_OLD)} against {n8000(P_L_OLD)}. A boot is one run of the machine between two restarts. "` | Item 2, part L: n at 7200 MT/s and at 8000 MT/s. One sentence says what a boot is. |
| 2427 | `    f"Old read kernel: {rL_old.txt()} against {rPL_old.txt()} GB/s. It was lower by {f2(abs(L_OLD_NEAR))} GB/s at the nearest ends "` | Continues item 2, old read kernel: the two ranges (`rL_old`, `rPL_old`) and the distance of the nearest ends `abs(L_OLD_NEAR)` in GB/s. A range text comes from `Rg.txt` (line 204): the lowest and the highest rate, each rounded to 0.01 GB/s by `f2`. |
| 2428 | `    f"and by {f2(abs(L_OLD_MED))} GB/s between the medians ({f1(L_OLD_NEAR_PCT)} % and {f1(L_OLD_MED_PCT)} % of the 8000 MT/s values). The data do not show the cause. "` | Continues item 2: the difference of the medians `abs(L_OLD_MED)` in GB/s, and both values in percent of the 8000 MT/s values. The text says that the data do not show the cause. |
| 2429 | `    f"Load-only loop (asmread in place of the new read kernel): {rL_asm.txt()} against {rPL_asm.txt()} GB/s.",` | Continues item 2, load-only loop: the two `asmread` ranges (`rL_asm`, `rPL_asm`). |
| 2430 | `    f"Parts A and C (sentence 2): the tests cannot exclude a difference of about {f1(width_pct(rPA_old))} % and {f1(width_pct(rPL_old))} % (est.). Table 2 gives the ranges and n.",` | Item 3, for the parts A and C: `width_pct` (line 476) of the two 8000 MT/s ranges of the old read kernel. It is the width of a range in percent of its lower end. The page marks it `est.`. |
| 2431 | `    "Part C (sentences 2 and 3): the rules fixed before the run contradict each other on whether part C is compared with the 8000 MT/s runs. This page compares it. "` | Item 4, part C, typed: the rules that were fixed before the run contradict each other on whether part C is compared with the 8000 MT/s runs. The page compares it. |
| 2432 | `    f"That choice was made after the numbers were seen (note under Table 2). Without part C, sentence 2 keeps parts A and L, and sentence 3 keeps {len(RERUN_CMP_NEW) - RERUN_CMP_C} of its {len(RERUN_CMP_NEW)} comparisons.",` | Continues item 4: that choice was made after the numbers were seen. The line prints `len(RERUN_CMP_NEW) - RERUN_CMP_C`, the number of comparisons of sentence 3 that stay without part C. `RERUN_CMP_C` is the constant 1 of line 2067. |
| 2433 | `    f"Sentence 3: the comparison uses 1 boot per memory speed. {F72} ran the argument line of part L. Its asmread gave {rF_asm.txt()} GB/s ({n7200(F_ASM)}). "` | Item 5, for sentence 3: the comparison uses 1 boot per memory speed. The line prints the `asmread` range of F72d12 and its n. The name F72d12 comes with its label, from the constant `F72` (line 1481). |
| 2434 | `    f"That is inside the 8000 MT/s range. It is {f2(abs(DIST['nearest'][1]))} GB/s below part L at the nearest ends.",` | Continues item 5: this range is inside the 8000 MT/s range. The line prints `abs(DIST['nearest'][1])`: the distance of the nearest ends between part L and F72d12 (line 504). |
| 2435 | `])` | Ends the list. |

### Pair counts, the bullet lists of the page sections 1 to 3, and facts for Table 6 (lines 2437 to 2484)

| Line | Source | Explanation |
|---:|---|---|
| 2437 | `l1d = Q1["L1"]["drops"]` | `l1d`: the drops of the 2 pairs of row L-1 (8000 MT/s). |
| 2438 | `GO_SECS = secs(RERUN["go_end"][11:19]) - secs(RERUN["go_start"][11:19])` | `GO_SECS`: the run time of `go.sh` in seconds: the end time of day minus the start time of day (`secs`, line 983). |
| 2439 | `N_RERUN_PAIRS = (len(c_ao) + len(c_aa), len(Q1["L"]["drops"]), len(Q1["A"]["drops"]))` | `N_RERUN_PAIRS`: the numbers of pairs of part C, of part L and of part A. For part A a pair is a pair of process medians. By lines 437 to 438 and lines 451 to 456 these are 8, 6 and 6 pairs. |
| 2440 | `need(sum(N_RERUN_PAIRS) + len(Q1["I"]["drops"]) + len(Q1["F"]["drops"]) == len(ALL_7200_DROPS), "pair counts of the 7200 MT/s rows")` | Hard assertion: the script stops unless these numbers plus the pairs of control I and of F72d12 give the length of `ALL_7200_DROPS` (line 459). |
| 2441 | `# part C holds asmread too: its pairs with oldread of the same process and round (Table 1 does not show them)` | Comment: part C holds `asmread` too. Its pairs with `oldread` of the same process and round are counted here. Table 1 does not show them. |
| 2442 | `C_ASM_DROPS = drops_of(pairs_in_process(C_OLD, C_ASM))` | `C_ASM_DROPS`: `pairs_in_process` pairs each `asmread` interval of part C with the `oldread` interval of the same process and round. `drops_of` computes the drop of each pair. |
| 2443 | `need(len(C_ASM_DROPS) == 8 and all(d > 0 for d in C_ASM_DROPS), "part C: not 8 asmread pairs, or asmread is not below oldread in a pair")` | Hard assertion: the script stops unless there are 8 such drops and each one is above 0. The page uses only their number, in the caption of Table 1 (line 2735). |
| 2444 | `SEC1_INTRO = UL([` | `SEC1_INTRO`: the bullet list before figure 1, in page section 1 (question Q1). |
| 2445 | `    f"The rerun ran parts A, L and C three times (three sessions) and then part C once more, from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC, all in boot {BOOT8} {ref('go', 'golog')}.",` | Item 1: the rerun ran the parts A, L and C three times and then part C once more. The line prints the start time and the end time of `go.sh`, and `BOOT8`. |
| 2446 | `    f"Part A repeats the 120-thread part of the test of 2026-11-13 with the same two binaries {ref('ra')}. "` | Item 2: part A repeats the 120-thread part of the test of 2026-11-13 with the same two binaries. |
| 2447 | `    f"With its whole-pass stop the pass count of an interval changes by whole passes, and the rate changes with it. So part A is less exact than parts L and C {ref('facts')}.",` | Continues item 2: with the whole-pass stop, the pass count of an interval changes by whole passes, and the rate changes with it. So part A is less exact than the parts L and C. |
| 2448 | `    f"Part C runs the new read kernel itself {ref('cfwd', 'crev')}. Part L runs asmread in its place {ref('like')}.",` | Item 3: part C runs the new read kernel itself, and part L runs `asmread` in its place. |
| 2449 | `    f"This page does not examine why the load-only loop is lower. The investigation of 2026-11-15 examined it and did not establish the cause {ref('earlier')}.",` | Item 4: the page does not examine why the load-only loop is lower. The investigation of 2026-11-15 examined it and did not establish the cause. Lines 1384 to 1386 test that the earlier report says so. |
| 2450 | `])` | Ends the list. |
| 2451 | `SEC1_AFTER = UL([` | `SEC1_AFTER`: the bullet list after Table 1. |
| 2452 | `    f"The drop is not one fixed value. The same argument line gave {drop_txt(Q1['L']['drops'])} in part L, {drop_txt(Q1['I']['drops'])} in {CI} and {drop_txt(Q1['F']['drops'])} in {F72}, "` | Item 1: the drop is not one fixed value. The line prints `drop_txt` (line 425) of the drops of part L, of control I and of F72d12: the lowest and the highest drop with 1 decimal, or one value when both print equal. The saved output of a build shows 29.2 % to 30.5 % for part L, 31.9 % to 32.8 % for control I and 35.4 % for F72d12 [Ref5]. |
| 2453 | `    "all inside the one 7200 MT/s boot.",` | Continues item 1: all three ran inside the one 7200 MT/s boot. |
| 2454 | `    f"At 8000 MT/s the same line gave {drop_txt(l1d)} (row L-1). The data do not show that the smaller drop of the rerun is an effect of the memory speed (section 2).",` | Item 2: `drop_txt(l1d)`, the same text for row L-1 at 8000 MT/s. Line 2037 gives its two values. The text says that the data do not show that the smaller drop of the rerun is an effect of the memory speed. |
| 2455 | `])` | Ends the list. |
| 2456 | `SEC2_INTRO = UL([` | `SEC2_INTRO`: the bullet list at the start of page section 2 (question Q2). |
| 2457 | `    f"The comparison rules and the list of 8000 MT/s rows were fixed before the run {ref('rules')}. A rule compares the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s rows.",` | Item 1: the comparison rules and the list of 8000 MT/s rows were fixed before the run. A rule compares the lowest-to-highest range of the 7200 MT/s intervals with that of the 8000 MT/s rows. |
| 2458 | `    f"Overlap: &quot;{WORD_SAME}&quot;. The width of the 8000 MT/s range is then the size that the test cannot exclude (est.).",` | Item 2: the fixed wording for an overlap, `WORD_SAME` (line 470). The width of the 8000 MT/s range is then the size that the test cannot exclude, marked `est.`. |
| 2459 | `    f"No overlap: &quot;{WORD_DIFF}&quot;.",` | Item 3: the fixed wording for no overlap, `WORD_DIFF` (line 471). Table 2 has two rows without an overlap that do not hold `WORD_DIFF`: the part A rows of the new read kernel (line 2107). |
| 2460 | `    "The comparison uses exactly 1 boot per memory speed. So a difference between the two boots is not shown to be an effect of the memory speed.",` | Item 4, typed: the comparison uses exactly 1 boot per memory speed. So a difference between the two boots is not shown to be an effect of the memory speed. |
| 2461 | `])` | Ends the list. |
| 2462 | `SEC2_BOOT = UL([` | `SEC2_BOOT`: the bullet list under the heading about the rate of the load-only loop inside the one 7200 MT/s boot (lines 2753 to 2754). |
| 2463 | `    f"The part L line ran in three visits of the 7200 MT/s boot (Table 3): {F72}, part L, and {CI}.",` | Item 1: the part L line ran in three visits of the 7200 MT/s boot: F72d12, part L and control I. The two names come with their labels (`F72`, `CI`). |
| 2464 | `    f"The three asmread ranges do not overlap each other. Together they span {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s ({f2(VISIT_HI - VISIT_LO)} GB/s).",` | Item 2: the three `asmread` ranges do not overlap each other (line 499). The line prints `VISIT_LO` and `VISIT_HI` (line 501): the lowest and the highest `asmread` rate of the three visits. It also prints their difference. The saved output of a build shows 301.90 to 327.93 GB/s and a difference of 26.03 GB/s [Ref5]. |
| 2465 | `    "The three visits did not start from the same state. The data do not show which difference changed the rate.",` | Item 3, typed: the three visits did not start from the same state. The data do not show which difference changed the rate. |
| 2466 | `])` | Ends the list. |
| 2467 | `INSUFF = UL([` | `INSUFF`: the bullet list of page section 3, `What the data do not show`. It holds six typed items. Each one names a point that the data do not show, and the measurement that would resolve it. No computed value is printed here. |
| 2468 | `    "Insufficient data: whether a difference of the new read kernel comes from the memory speed. Runs in several boots per speed would resolve it (needs reboots and a change of the firmware setting).",` | Item 1: whether a difference of the new read kernel comes from the memory speed. Runs in several boots per speed would resolve it. |
| 2469 | `    "Insufficient data: why the rate of the load-only loop changed between the three visits of the one 7200 MT/s boot (Table 3). "` | Item 2: why the rate of the load-only loop changed between the three visits of the one 7200 MT/s boot. |
| 2470 | `    "Two measurements would resolve it. First: run the part L line alternately from an idle start and directly after part A, at least 3 times each in one boot. "` | Continues item 2: the first of two measurements that would resolve it. The part L line is run alternately from an idle start and directly after part A, at least 3 times each in one boot. |
| 2471 | `    "Second: repeat the idle-start line some hours later in the same boot, and once directly after a reboot (needs approval).",` | Continues item 2: the second measurement. The idle-start line is repeated some hours later in the same boot, and once directly after a reboot. |
| 2472 | `    "Insufficient data: why the old read kernel was lower in part L. The first of these two measurements would resolve it.",` | Item 3: why the old read kernel was lower in part L. The first measurement of item 2 would resolve it. |
| 2473 | `    "Insufficient data: no 8000 MT/s run of kernel read with bwx12. A run of the two part C lines at 8000 MT/s would resolve it (needs a firmware change and a reboot).",` | Item 4: no 8000 MT/s run of the kernel `read` with bwx12 exists. A run of the two part C lines at 8000 MT/s would resolve it. |
| 2474 | `    "Insufficient data: whether hardware error records occurred during the rerun. A count of the &quot;[Hardware Error]&quot; lines of the kernel log would resolve it (needs root, which was not approved for this task).",` | Item 5: whether hardware error records occurred during the rerun. A count of the lines with `[Hardware Error]` in the kernel log would resolve it. That needs root, which was not approved for this task. |
| 2475 | `    "Insufficient data: a direct reading of the memory speed during the rerun. A module list read during the rerun would resolve it. "` | Item 6: a direct reading of the memory speed during the rerun. A module list read during the rerun would resolve it. |
| 2476 | `    "The command <code>sudo dmidecode -t 17</code> prints this list (needs root).",` | Continues item 6: the command `sudo dmidecode -t 17` prints this list and needs root. |
| 2477 | `])` | Ends the list. |
| 2478 | `go_first = LAUNCH["T72A1"]` | `go_first`: the entry of `meta.launches` for the first step, T72A1. |
| 2479 | `others = [LAUNCH[t]["load1_at_first_launch"] for t in STEPS[1:10]]` | `others`: the 1-minute load average at the first launch of the steps 2 to 10 of `go.sh` (`STEPS[1:10]`, T72L1 to T72C4). |
| 2480 | `need(all(LAUNCH[t]["gap_s"] == 5 for t in STEPS[1:10]), "a step of go.sh did not start 5 s after the previous process")` | Hard assertion: the script stops unless each of these 9 steps has a `gap_s` of 5. Table 6 prints this field as the time in seconds after the end of the previous 120-thread process (line 2252). |
| 2481 | `need(LAUNCH["T72A1"]["gap_s"] is None, "T72A1 is not the first step")` | Hard assertion: the script stops unless T72A1 has no gap. |
| 2482 | `need(D(go_first["load1_at_first_launch"]) < 1, "the first launch of the rerun is not an idle start")` | Hard assertion: the script stops unless the load average at the first launch of T72A1 was below 1 (an idle start). |

### Facts for the reading notes of figure 2, and the function `cl` (lines 2485 to 2502)

| Line | Source | Explanation |
|---:|---|---|
| 2485 | `# reading notes of figure 2: the start of part A in sessions 2 and 3, and the load at the first launch of session 1 and of rows A-1 and A-2` | Comment: facts for the reading notes of figure 2: the start of part A in the sessions 2 and 3, and the load at the first launch of session 1 and of the rows A-1 and A-2. |
| 2486 | `need(all(LAUNCH[t]["gap_s"] == 5 and "120-thread bwx12 process T72C" in LAUNCH[t]["start_state"] for t in ("T72A2", "T72A3")), "part A, sessions 2 and 3: not started 5 s after a part C process")` | Hard assertion: the script stops unless part A of the sessions 2 and 3 started 5 s after a part C process. The test reads `gap_s` and the text `start_state` of the two entries of `LAUNCH`. |
| 2487 | `A_FIRST_LOAD = {"T72A1": D(go_first["load1_at_first_launch"])}` | `A_FIRST_LOAD`: the 1-minute load average at the first launch of T72A1 and of the rows A-1 and A-2. It starts with the value of T72A1. |
| 2488 | `for d_ in ("A-1", "A-2"):` | Starts a loop over the rows A-1 and A-2. |
| 2489 | `    first = min(sel(dataset=d_), key=lambda r: r["launch_utc"])` | `first`: the record with the earliest launch time of the whole dataset, with every kernel included. |
| 2490 | `    need(first in B_A_OLD[d_] and first["_fproc"] == 1 and first["round"] == 1, f"{d_}: the first process of the file is not a read process that this page uses")` | Hard assertion: the script stops unless `first` is a `bw_old` read record that the page uses, from the first process of its csv file, in round 1. |
| 2491 | `    A_FIRST_LOAD[d_] = D(first["load1_at_launch"])` | Stores the load at the launch of that process. |
| 2492 | `need(all(v < 2 for v in A_FIRST_LOAD.values()), "session 1, A-1 or A-2: the first process did not start at a low load average")` | Hard assertion: the script stops unless the three load values are below 2. |
| 2493 | `a_sess_n = {(len(x), len({r["proc_key"] for r in x})) for x in ([r for r in A_OLD if r["session"] == s_] for s_ in (1, 2, 3))}` | `a_sess_n`: for each session of `A_OLD`, the number of intervals and the number of processes, as a set of pairs. |
| 2494 | `need(a_sess_n == {(6, 2)}, "part A, old read kernel: a session does not have 6 intervals of 2 processes")` | Hard assertion: the script stops unless every session has 6 intervals of 2 processes. |
| 2495 | `A_SESSION_N = "6 intervals / 2 processes / 1 session / 1 boot"` | `A_SESSION_N`: the typed text of this n. The reading notes print it (line 2693). |
| 2498 | `def cl(*items):` | Starts the function `cl`. It returns a bullet list for use inside one table cell. |
| 2499 | `    """A list inside one table cell: one point per bullet."""` | Comment: the documentation text. The list has one point per bullet. |
| 2500 | `    return '<ul class="cl">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"` | Returns a `ul` element of the class `cl` with one `li` item per argument. |

### Function `state_table` (Table 5, the machine state), and the caption text of Table 6 (lines 2503 to 2579)

| Line | Source | Explanation |
|---:|---|---|
| 2503 | `def state_table():` | Starts the function `state_table`. It builds Table 5 of the page section `Machine state and system load`. Each row has three cells: a fact, its proof and its limit. `build` calls it in line 2768. |
| 2504 | `    hw_refs = ref("journal", "L-1l", "L-2l", "L-3l", "L-4l")` | `hw_refs`: the reference marks of the journal and of the four files `launches.txt` of the rows L-1 to L-4. |
| 2505 | `    low_day = LOWEST_ASM["launch_utc"][:10]` | `low_day`: the date of the launch of `LOWEST_ASM` (line 520), the record with the lowest `asmread` rate of the pool L-1 to L-4. |
| 2506 | `    need(HW_LOW[0]["ts"][:10] == low_day == "2026-11-15", "the lowest asmread interval of the pool is not of 2026-11-15")` | Hard assertion: the script stops unless the first hardware error record of that interval (`HW_LOW`, line 1031) has the same date, and the date is 2026-11-15. |
| 2507 | `    rows = [` | `rows`: the list of the 11 table rows. The rows 1 to 6 (lines 2508 to 2532) hold no rate. Their values come from `RERUN` (the part `meta.rerun` of `facts.json`) and from the raw-file checks of lines 811 to 1386. Lines 865 to 866 and lines 877 to 878 stop the script unless the run logs hold the same boot id, the same `MemTotal` and the same times as `RERUN`. |
| 2508 | `        ["12 memory modules during the rerun",` | Row 1, the fact: 12 memory modules during the rerun. |
| 2509 | `         cl(f"MemTotal is {RERUN['memtotal_kB']} kB in all {len(ST_ALL)} state lines of the two run logs {ref('golog', 'go2log')}.",` | Row 1, the proof, as a list of three points (`cl`, line 2498). First point: `MemTotal` in kB in all state lines of the two run logs, with their number `len(ST_ALL)`. |
| 2510 | `            f"The record of this boot (a file written at {TRY6_UTC[11:19]} UTC) holds the same value. It also holds the kernel log line &quot;This system has 12 DIMM sockets&quot; "` | Second point: the record of this boot (the file `try6.txt`) holds the same value. The line prints the time of that file from `TRY6_UTC` (line 901). The record also holds the kernel log line with `12 DIMM sockets`. |
| 2511 | `            f"and the count 12 of the lines &quot;Configured Memory Speed&quot; {ref('try6')}.",` | Continues the point: the record holds the count 12 of the lines with `Configured Memory Speed`. |
| 2512 | `            f"The module list saved in the same boot has one line &quot;Configured Memory Speed&quot; for each of its {DMI_N} modules {ref('dmi')}."),` | Third point: the module list that was saved in the same boot has one such line for each of its `DMI_N` modules (line 1162). |
| 2513 | `         cl(f"The record also holds the line &quot;modules={TRY6_MODLINE}&quot; {ref('try6')}. This is not the module count. The module list holds {DMI_SIZE} lines with the text &quot;Size: 32 GB&quot;: "` | Row 1, the limit, as a list of two points. First point: the record also holds a line `modules=N`, with the number `TRY6_MODLINE` (line 900). The text says that this is not the module count. The module list holds `DMI_SIZE` lines with the text `Size: 32 GB` (line 1167). |
| 2514 | `            f"{DMI_SIZE_PLAIN} lines &quot;Size&quot; and {DMI_SIZE_VOL} lines &quot;Volatile Size&quot; {ref('dmi')}.",` | Continues the point: how many of these lines are lines `Size`, and how many are lines `Volatile Size` (lines 1168 to 1169). |
| 2515 | `            f"Hypothesis, not checked: the script that wrote the record counted these {DMI_SIZE} lines. Reading that script would confirm or reject it.")],` | Second point, a hypothesis that was not checked: the script that wrote the record counted these lines. The text names the check that would confirm or reject it. |
| 2516 | `        ["Memory speed 7200 MT/s during the rerun",` | Row 2, the fact: the memory speed was 7200 MT/s during the rerun. |
| 2517 | `         f"Every state line holds the boot id {RERUN['boot_id']}. The record of this boot, written at {TRY6_UTC[11:19]} UTC, shows 12 x &quot;Configured Memory Speed: 7200 MT/s&quot; {ref('try6')}.",` | Row 2, the proof: every state line holds the boot id of the rerun. Then the cell names the record of this boot (the file `try6.txt`) with its time from `TRY6_UTC`. The record holds one line with the count 12 before the text `Configured Memory Speed: 7200 MT/s`. The page writes this as `12 x`. Lines 895 to 896 stop the script unless that line holds the count 12 and the speed 7200 MT/s. |
| 2518 | `         "The speed was not read during the rerun. Reading it needs root. Assumption, not measured: the speed does not change inside one boot."],` | Row 2, the limit, typed: the speed was not read during the rerun, and reading it needs root. The text states an assumption that was not measured: the speed does not change inside one boot. |
| 2519 | `        ["The rerun is complete",` | Row 3, the fact: the rerun is complete. |
| 2520 | `         f"go.sh ran from {RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC. The script stops at the first exit status other than 0 {ref('go')}. Its log holds {GO_DONE} &quot;done&quot; lines and the final line ALLDONE {ref('golog')}. So {GO_DONE} of {GO_DONE} steps ended with exit status 0.",` | Row 3, the proof: the start time and the end time of `go.sh`, and `GO_DONE` (line 874), the number of `done` lines of its log. The text says that the script stops at the first exit status other than 0, and that the log ends with the line `ALLDONE`. So all steps ended with exit status 0. |
| 2521 | `         "-"],` | Row 3, the limit: `-`. No limit is named. |
| 2522 | `        ["Logins and accounts with processes during go.sh",` | Row 4, the fact: logins and accounts with processes during `go.sh`. |
| 2523 | `         f"The {len(ST_GO)} state lines of the go.sh log show 0 logins. They list processes of {len(ACCOUNTS)} accounts only: jhan (the account that ran the rerun), root and {len(SYSTEM_ACCOUNTS)} system accounts {ref('golog')}.",` | Row 4, the proof: the number of state lines of the `go.sh` log (`len(ST_GO)`), all with 0 logins, and the accounts that own processes: `jhan`, `root` and the system accounts. Lines 867 to 870 assert these facts. |
| 2524 | `         "-"],` | Row 4, the limit: `-`. |
| 2525 | `        ["Control I (added after the first numbers were seen) ran afterwards",` | Row 5, the fact: control I ran afterwards. |
| 2526 | `         f"go2.sh waits for a 1-minute load average below 1.0 and then runs the part L line. It does this twice {ref('go2')}. It ran from {RERUN['go2_start'][11:19]} to {RERUN['go2_end'][11:19]} UTC. "` | Row 5, the proof: `go2.sh` waits for a 1-minute load average below 1.0 and then runs the part L line, twice. The line prints the start time and the end time of `go2.sh`. |
| 2527 | `         f"Its log holds 2 &quot;done&quot; lines and the final line ALLDONE {ref('go2log')}.",` | Continues the proof: the log of `go2.sh` holds 2 `done` lines and the final line `ALLDONE` (line 876). |
| 2528 | `         "Control I is not part of the plan fixed before the run."],` | Row 5, the limit: control I is not part of the plan that was fixed before the run. |
| 2529 | `        [f"F72d12 (earlier run of the same boot, not part of the rerun) belongs to boot {BOOT8}",` | Row 6, the fact: F72d12 belongs to the boot of the rerun (`BOOT8`). |
| 2530 | `         f"The record of this boot was written at {TRY6_UTC[11:19]} UTC {ref('try6')}. The boot list, saved at {BOOT_LAST} UTC, shows this boot from {BOOT_FIRST} UTC as the last boot {ref('boots')}. "` | Row 6, the proof: the time of the record of this boot, and the boot list (`BOOT_FIRST`, `BOOT_LAST`, line 907), which shows this boot as the last boot. |
| 2531 | `         f"The F72d12 process ran from {F_LAUNCH} to {F_END} UTC {ref('F72l')}. The go.sh log shows the same boot id at {RERUN['go_start'][11:19]} UTC {ref('golog')}.",` | Continues the proof: the times of the F72d12 process (`F_LAUNCH`, `F_END`, line 913), and the time at which the `go.sh` log shows the same boot id. Line 915 asserts the order of these times. |
| 2532 | `         "The proof uses these times only. The speed was not read during the process."],` | Row 6, the limit: the proof uses these times only. The speed was not read during the process. |
| 2533 | `        ["Work before the first 120-thread process of part A",` | Row 7, the fact: the work before the first 120-thread process of part A. |
| 2534 | `         f"On 2026-11-13 the test script launched {ONE_N} one-thread processes from {ONE_FIRST} to {ONE_LAST} UTC, directly before its 120-thread part {ref('one')}. "` | Row 7, the proof: the number and the times of the one-thread processes that the test script of 2026-11-13 launched directly before its 120-thread part (`ONE_N`, `ONE_FIRST`, `ONE_LAST`, line 1356). |
| 2535 | `         f"The rerun did not repeat this one-thread phase {ref('ra')}. "` | Continues the proof: the rerun did not repeat this one-thread phase. |
| 2536 | `         f"At 8000 MT/s the old read kernel gave {rA12_old.txt()} GB/s after one-thread work and directly after 120-thread work (rows A-1 and A-2, {n8000(rA12_old.recs)}) {ref('A-1', 'A-2', 'facts')}.",` | Continues the proof: the one range of rates of this table, `rA12_old.txt()`. It is the lowest and the highest rate of `bw_old` read over the 12 intervals of the rows A-1 and A-2 (line 1362), with its n. The saved output of a build shows 464.42 to 467.06 GB/s [Ref5]. |
| 2537 | `         "Insufficient data: whether the work before the first 120-thread process changes the rate of the new read kernel. "` | Row 7, the limit: `Insufficient data` on whether the work before the first 120-thread process changes the rate of the new read kernel. |
| 2538 | `         f"A run with the new kernel at several positions, after an idle start and after 120-thread work, would resolve it {ref('rules')}."],` | Continues the limit: the run that would resolve it, with the new kernel at several positions, after an idle start and after 120-thread work. |
| 2539 | `        ["Firmware settings other than the memory speed",` | Row 8, the fact: firmware settings other than the memory speed. |
| 2540 | `         f"Two TXREQ settings were changed for another test on 2026-11-17, at {X1_T} and {X2_T} UTC {ref('x1', 'x2')}. Both were set back at {RV_T} UTC to their values of the 8000 MT/s boot {ref('rev')}. "` | Row 8, the proof: the times of the changes of the two TXREQ settings (`X1_T`, `X2_T`), and the time at which both were set back to their values of the 8000 MT/s boot (`RV_T`, lines 1064 to 1066). |
| 2541 | `         f"The settings list saved after that is equal to the list of the 8000 MT/s boot in all {N_SET} entries{'' if SAME_ORDER else ' (the order of the entries differs)'} {ref('qbase', 'qrev')}. "` | Continues the proof: the settings list that was saved after that is equal to the list of the 8000 MT/s boot in all `N_SET` entries (line 1079). When the order of the entries differs (`SAME_ORDER` is false), the text says so. |
| 2542 | `         f"The only later change on record is DIMM Frequency = 7200 MT/s (file time {D72_T} UTC) {ref('d72')}.",` | Continues the proof: the only later change on record, DIMM Frequency = 7200 MT/s, with the file time `D72_T` (line 1092). |
| 2543 | `         cl(f"{N_UNREAD} of the {N_SET} entries show no readable value in both lists ({UNREAD['ValueUnavailable']} show ValueUnavailable, {UNREAD['VStoreError']} show VStoreError).",` | Row 8, the limit, as a list of three points. First point: `N_UNREAD` of the `N_SET` entries show no readable value in both lists, with the count per kind of error marker (lines 1081 to 1087). |
| 2544 | `            f"&quot;On record&quot; means the {len(SET_FILES)} files named set.txt in the results folder.",` | Second point: what `on record` means: the files named `set.txt` in the results folder, with their number `len(SET_FILES)`. |
| 2545 | `            "Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. No full list was saved in that boot. A settings list saved in that boot would resolve it (needs root).")],` | Third point: `Insufficient data` on the firmware settings in the boot of the rerun, apart from the memory speed. No full list was saved in that boot. |
| 2546 | `        ["The 8000 MT/s rows: one boot, 12 modules",` | Row 9, the fact: the 8000 MT/s rows come from one boot with 12 modules. |
| 2547 | `         cl(f"The saved kernel log of that boot runs from {BOOT8_FROM[:10]} {BOOT8_FROM[11:19]} to {BOOT8_TO[:10]} {BOOT8_TO[11:19]} UTC and holds the line &quot;This system has 12 DIMM sockets&quot; {ref('klog')}.",` | Row 9, the proof, as a list of four points. First point: the start and the end of the saved kernel log of that boot (`BOOT8_FROM`, `BOOT8_TO`, line 937), which holds the line with `12 DIMM sockets`. |
| 2548 | `            f"The kernel log of the boot that started on {BOOT10_FROM} UTC holds &quot;This system has 10 DIMM sockets&quot;, and its memory size line shows {MEM_LESS_GIB} GiB less {ref('klog10')}. "` | Second point: the kernel log of the boot that started on `BOOT10_FROM` holds the line with `10 DIMM sockets`. Its memory size line shows `MEM_LESS_GIB` GiB less (line 1157): the memory of the 8000 MT/s boot minus the memory of this boot (1 GiB is `2^30` bytes). Line 1158 asserts 64 GiB. |
| 2549 | `            "So the number in this line is not the slot count of the board. This page reads it as the number of modules that the boot found.",` | Continues the point: so the number in this line is not the slot count of the board. The page reads it as the number of modules that the boot found. |
| 2550 | `            f"Every process of the rows A-1 to A-3, of the rows L-1 to L-4 and of runner bwx was launched inside the time of this kernel log {ref('json')}. "` | Third point: every process of the rows A-1 to A-3, of the rows L-1 to L-4 and of the runner bwx was launched inside the time of this kernel log (line 941). |
| 2551 | `            "Row X2d12 and the three boots with 10 modules ran in later boots (notes under Table 2).",` | Continues the point: row X2d12 and the three boots with 10 modules ran in later boots. |
| 2552 | `            f"The settings list saved in that boot shows DIMM Frequency = 8000 MT/s {ref('qbase')}."),` | Fourth point: the settings list that was saved in that boot shows DIMM Frequency = 8000 MT/s (line 1076). |
| 2553 | `         "No reading of the applied speed was saved in that boot."],` | Row 9, the limit: no reading of the applied speed was saved in that boot. |
| 2554 | `        ["Corrected hardware error records in the 8000 MT/s rows",` | Row 10, the fact: corrected hardware error records in the 8000 MT/s rows. |
| 2555 | `         cl(f"Rows L-1 to L-4: the journal of the 8000 MT/s boot holds corrected hardware error records during two of the four rows. It holds {HW_L1} during L-1, and {HW_L2[0]} and {HW_L2[1]} during the two processes of L-2. "` | Row 10, the proof, as a list of two points. First point: the numbers of corrected hardware error records in the journal during the rows L-1 and L-2 (`HW_L1`, `HW_L2`, lines 965 to 966). |
| 2556 | `            f"It holds {HW_L34} during L-3 and L-4 {hw_refs}.",` | Continues the point: the number during L-3 and L-4 (`HW_L34`, line 967). Line 968 asserts that it is 0. |
| 2557 | `            f"Rows A-1 to A-3 ({A_DAY}): the journal holds {len(HW_A)} records between the first launch of A-1 ({A1_FIRST} UTC) and the launch that followed the last A-3 process used here ({A3_END} UTC). "` | Second point, rows A-1 to A-3: the number of records (`HW_A`, line 996) between the first launch of A-1 and the launch that followed the last A-3 process used here. |
| 2558 | `            f"All {len(HW_A)} records have times inside row A-2. 2 records have the time {HW_A2_T[0]} UTC. The bw_new read process of round 1 was launched at {HW_A2_T[0]} UTC too. "` | Continues the point: all these records have times inside row A-2. 2 records have the time of the launch of the `bw_new` read process of round 1 (`HW_A2_T[0]`, line 1003). |
| 2559 | `            f"The other 2 records have the time {HW_A2_T[1]} UTC. A {A2_OTHER} process, which this page does not use, was launched {secs(HW_A2_T[1]) - secs(a2_other[0][1])} s before that {ref('journal', 'A-1', 'A-2', 'A-3')}."),` | Continues the point: the other 2 records, at the time `HW_A2_T[1]`. A process `A2_OTHER` (line 1012), which the page does not use, was launched some seconds before that. The line computes these seconds. |
| 2560 | `         cl("The data do not show that a record changed a rate.",` | Row 10, the limit, as a list of three points. First point: the data do not show that a record changed a rate. |
| 2561 | `            "For the rerun the kernel log was not read (section 3).",` | Second point: for the rerun the kernel log was not read. |
| 2562 | `            "The rows of runner bwx (note under Table 2) were not checked for such records.")],` | Third point: the rows of the runner bwx were not checked for such records. |
| 2563 | `        ["The lowest asmread value of the 8000 MT/s pool comes from an interval with corrected hardware error records",` | Row 11, the fact: the lowest `asmread` value of the 8000 MT/s pool comes from an interval with corrected hardware error records. |
| 2564 | `         cl(f"The lowest asmread value of the pool L-1 to L-4 is {f2(val(LOWEST_ASM))} GB/s. Its interval ran from about {LOW_FROM} to {LOW_TO} UTC on {low_day} "` | Row 11, the proof, as a list of three points. First point: `f2(val(LOWEST_ASM))`, the lowest `asmread` rate of the pool. It is the value of `val` for that one interval: the sum of bytes / `elapsed_s` / 1e9 over its 120 thread rows. `LOW_FROM` and `LOW_TO` (line 1030) are the start time and the end time of the interval. The saved output of a build shows 288.54 GB/s [Ref5]. |
| 2565 | `            f"(est.: time of the launch line plus the seconds since the process start in the thread rows) {ref('L-2b', 'L-2l')}.",` | Continues the point: how the two times were formed: the time of the launch line plus the seconds after the process start in the thread rows. The page marks them `est.`. |
| 2566 | `            f"{len(HW_LOW)} corrected hardware error records have the journal time {low_day} {HW_LOW[0]['ts'][11:19]} UTC, inside this interval {ref('journal')}.",` | Second point: the number of corrected hardware error records with a journal time inside this interval (`HW_LOW`, line 1031), and that time. |
| 2567 | `            f"Without this one interval the pool spans {rPL_asm_wo.txt()} GB/s ({n8000(rPL_asm_wo.recs)}). Part L ({rL_asm.txt()} GB/s, {n7200(L_ASM)}) still lies above it, by {f2(rL_asm.nearest(rPL_asm_wo))} GB/s at the nearest ends."),` | Third point: the range of the pool without this one interval (`rPL_asm_wo`, line 521) and the `asmread` range of part L (`rL_asm`), each with its n. It also prints `rL_asm.nearest(rPL_asm_wo)`: the lowest `asmread` rate of part L minus the highest rate of that smaller pool. The saved output of a build shows 298.61 to 309.17 GB/s for the pool without the interval and 321.65 to 327.93 GB/s for part L [Ref5]. |
| 2568 | `         "The data do not show that the records lowered this interval. Both times have a resolution of 1 s."],` | Row 11, the limit: the data do not show that the records lowered this interval. Both times have a resolution of 1 s. |
| 2569 | `    ]` | Ends the list `rows`. |
| 2570 | `    return table(["Fact", "Proof", "Limit"], rows, "state")` | Passes the rows to `table` (line 1501) with the class `state` and the column titles `Fact`, `Proof` and `Limit`, and returns the result. |
| 2573 | `LOAD_CAPTION = (f"The first launch of the rerun was at a 1-minute load average of {f2(go_first['load1_at_first_launch'])}. The other {len(others)} steps of go.sh started at a 1-minute load average of "` | `LOAD_CAPTION`: the caption text of Table 6 (line 2770). This line prints the 1-minute load average at the first launch of the rerun (`go_first`, line 2478) and the number of the other steps of `go.sh` (`others`, line 2479). |
| 2574 | `                f"{f2(min(others))} to {f2(max(others))}, each 5 s after a 120-thread process of the rerun had ended. "` | Continues the text: the lowest and the highest load of `others`. Each of these steps started 5 s after a 120-thread process of the rerun had ended (line 2480). In `meta.launches` of `facts.json` the first launch has a load average of 0.07, and the other 9 steps have 74.05 to 105.24 [Ref2]. |
| 2575 | `                "Hypothesis, not tested: these high values come from the rerun's own 120-thread processes. Two more facts fit it. The load value is an average over the last minute. "` | Continues the text: a hypothesis that was not tested. The high values come from the 120-thread processes of the rerun itself. The text names a first fact that fits it: the load value is an average over the last minute. |
| 2576 | `                f"The state lines of the go.sh log show 0 logins and processes of jhan, root and {len(SYSTEM_ACCOUNTS)} system accounts only {ref('golog')}. "` | Continues the text: the second fact. The state lines of the `go.sh` log show 0 logins, and processes of `jhan`, `root` and the system accounts only. |
| 2577 | `                "A sample of the load average and of the running processes, taken once per second between two steps, would confirm or reject it.")` | Continues the text: the measurement that would confirm or reject the hypothesis: a sample of the load average and of the running processes, taken once per second between two steps. |

### `CSS`: the style block of the page (lines 2580 to 2676)

| Line | Source | Explanation |
|---:|---|---|
| 2580 | `CSS = """` | `CSS`: a text constant with the style rules of the page. `build` puts it into the `style` element (line 2707). It holds no data. The text ends in line 2674. |
| 2581 | `:root{color-scheme:light}` | CSS: the page uses the light colour scheme only. |
| 2582 | `*{box-sizing:border-box}` | CSS: for every element, the width and the height include the padding and the border. |
| 2583 | `body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: the page body has no outer margin, the background colour `#fcfcfb`, the text colour `#0b0b0b`, and a system font of 16 px with a line height of 1.55. The two colours are the values of `SURF` and `INK` (line 35). |
| 2584 | `main{max-width:980px;margin:0 auto;padding:28px 16px 64px}` | CSS: the content (`main`) is at most 980 px wide and centred. Its padding is 28 px at the top, 16 px at each side and 64 px at the bottom. |
| 2585 | `h1{font-size:28px;line-height:1.25;margin:0 0 6px}` | CSS: the page title (`h1`) has a font size of 28 px. |
| 2586 | `h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}` | CSS: a section heading (`h2`) has a font size of 21 px and a thin line above it. |
| 2587 | `h3{font-size:17px;margin:22px 0 8px}` | CSS: a lower heading (`h3`) has a font size of 17 px. |
| 2588 | `p{margin:8px 0}` | CSS: a paragraph has a margin of 8 px above and below. |
| 2589 | `ul{margin:4px 0 8px;padding-left:22px}` | CSS: a bullet list has an indent of 22 px. |
| 2590 | `li{margin:3px 0}` | CSS: a list item has a margin of 3 px above and below. |
| 2591 | `a{color:inherit}` | CSS: a link has the colour of the text around it. |
| 2592 | `code{font-size:0.92em;overflow-wrap:anywhere}` | CSS: code text is a little smaller (0.92 of the size around it), and a long name may break at any character. |
| 2593 | `.sub{color:#52514e;font-size:14px;margin:0 0 18px}` | CSS: the class `sub`, the line under the page title (line 2712): grey, 14 px. |
| 2594 | `.short{background:#f1f0ec;border-left:4px solid #2a78d6;padding:12px 16px;margin:14px 0}` | CSS: the class `short`, the box of the Short version (line 2715): a light grey background, and a bar of 4 px in the blue of `BLUE` at its left edge. |
| 2595 | `.short p{margin:6px 0}` | CSS: the paragraphs inside that box have a margin of 6 px above and below. |
| 2596 | `.more{font-size:14.5px;margin:10px 0 0}` | CSS: the class `more`, the line that starts the detail list under the box (line 2718): 14.5 px. |
| 2597 | `.more+ul{font-size:14.5px}` | CSS: the bullet list directly after that line has the same size. |
| 2598 | `dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}` | CSS: the word list (`dl` of the class `words`) is a grid with two columns. The term column is 120 to 210 px wide, and the definition column takes the rest. |
| 2599 | `dl.words dt{font-weight:600}` | CSS: a term of the word list is in bold type. |
| 2600 | `dl.words dd{margin:0}` | CSS: a definition has no margin. |
| 2601 | `@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}` | CSS: in a window of at most 600 px the word list has one column, and each definition has a margin of 8 px below it. |
| 2602 | `.tw{overflow-x:auto;margin:10px 0}` | CSS: the class `tw`, the box around a table (line 1503): it scrolls sideways when the table is wider. |
| 2603 | `table{border-collapse:collapse;font-size:14px;line-height:1.35}` | CSS: the base style of the tables: joined cell borders, a font size of 14 px, a line height of 1.35. |
| 2604 | `th,td{border-bottom:1px solid #e4e3df;padding:4px 10px;text-align:left;vertical-align:top}` | CSS: head cells and body cells get a thin line below and a padding of 4 px and 10 px. Their text starts at the top left. |
| 2605 | `th{background:#f1f0ec;font-weight:600}` | CSS: head cells get a light grey background and bold type. |
| 2606 | `td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}` | CSS: a cell of the class `n` (a number column, line 1504) is right-aligned and has digits of equal width. |
| 2607 | `td.n{white-space:nowrap}` | CSS: the text of a body cell of the class `n` stays on one line. |
| 2608 | `tr.grp td{background:#f8f7f4;font-weight:600;color:#52514e;font-size:13px}` | CSS: a title row inside a table (class `grp`, line 1508): a lighter background, and bold grey type of 13 px. |
| 2609 | `tr.grp td .tn{font-weight:400;color:#0b0b0b;font-size:13.5px}` | CSS: a note inside such a row (class `tn`): normal weight, the text colour, 13.5 px. |
| 2610 | `tr.grp td .tn ul.cl{margin-top:3px}` | CSS: a bullet list inside such a note gets a margin of 3 px above it. |
| 2611 | `/* Widths: the page content is the window width minus 32 px, and minus up to 17 px more when the browser draws a scrollbar.` | CSS comment: the page content is the window width minus 32 px, and minus up to 17 px more when the browser draws a scrollbar. |
| 2612 | `   The wide tables have a least width of 900 px. So a wide table can scroll sideways in windows below 949 px, and the hint is shown there. */` | CSS comment, continued: the wide tables have a least width of 900 px. So a wide table can scroll sideways in windows below 949 px, and the hint is shown there. |
| 2613 | `table.q1,table.q2,table.state,table.load,table.visits,table.detail{min-width:900px}` | CSS: the six wide tables (classes `q1`, `q2`, `state`, `load`, `visits` and `detail`) have a least width of 900 px. |
| 2614 | `.hint{display:none;color:#52514e;font-size:13.5px;margin:4px 0}` | CSS: the class `hint` is hidden by default. It is grey text of 13.5 px. |
| 2615 | `@media (max-width:949px){.hint.ht{display:block}}` | CSS: in a window of at most 949 px the hint above a wide table (classes `hint` and `ht`, line 1502) is shown. The comment says `below 949 px`. The rule also applies at exactly 949 px. |
| 2616 | `/* A panel of figure 2 is 468 px wide with its border: it can scroll sideways in windows below 517 px. */` | CSS comment: a panel of figure 2 is 468 px wide with its border. By the comment it can scroll sideways in windows below 517 px. The rule of line 2617 uses 519 px, not 517 px. |
| 2617 | `@media (max-width:519px){.hint.h2{display:block}}` | CSS: in a window of at most 519 px the hint for the panels of figure 2 (classes `hint` and `h2`, line 2747) is shown. |
| 2618 | `table.state td:first-child{min-width:150px}` | CSS: Table 5 (class `state`): the first column is at least 150 px wide. |
| 2619 | `table.state td:nth-child(2){min-width:300px}` | CSS: Table 5: the second column is at least 300 px wide. |
| 2620 | `table.state td:nth-child(3){min-width:190px}` | CSS: Table 5: the third column is at least 190 px wide. |
| 2621 | `table.q1 td:first-child{min-width:190px}` | CSS: Table 1 (class `q1`): the first column is at least 190 px wide. |
| 2622 | `table.q1 td:last-child{min-width:130px}` | CSS: Table 1: the last column is at least 130 px wide. |
| 2623 | `table.q2 td:first-child{min-width:140px}` | CSS: Table 2 (class `q2`): the first column is at least 140 px wide. |
| 2624 | `table.q2 td:nth-child(2),table.q2 td:nth-child(3){min-width:160px}` | CSS: Table 2: the second and the third column are at least 160 px wide. |
| 2625 | `table.q2 td:last-child{min-width:220px}` | CSS: Table 2: the last column is at least 220 px wide. |
| 2626 | `table.q2 th:nth-child(5){min-width:110px}` | CSS: Table 2: the fifth head cell, the one of the distance column, is at least 110 px wide. |
| 2627 | `table.visits td:first-child{min-width:120px}` | CSS: Table 3 (class `visits`): the first column is at least 120 px wide. |
| 2628 | `table.visits td:nth-child(2){min-width:90px}` | CSS: Table 3: the second column is at least 90 px wide. |
| 2629 | `table.visits td:nth-child(3){min-width:280px}` | CSS: Table 3: the third column is at least 280 px wide. |
| 2630 | `table.visits td:last-child{min-width:110px}` | CSS: Table 3: the last column is at least 110 px wide. |
| 2631 | `table.narrow{max-width:760px}` | CSS: Table 4 (class `narrow`) is at most 760 px wide. |
| 2632 | `table.load td.n{white-space:normal}` | CSS: Table 6 (class `load`): the text of a cell of the class `n` may wrap. |
| 2633 | `table.load td:nth-child(2){min-width:150px}` | CSS: Table 6: the second column is at least 150 px wide. |
| 2634 | `table.load td:nth-child(3){min-width:110px}` | CSS: Table 6: the third column is at least 110 px wide. |
| 2635 | `table.load td:nth-child(4){min-width:170px}` | CSS: Table 6: the fourth column is at least 170 px wide. |
| 2636 | `table.load td:nth-child(5){min-width:190px}` | CSS: Table 6: the fifth column is at least 190 px wide. |
| 2637 | `table.detail{font-size:13px}` | CSS: the table views of the two figures (class `detail`) have a font size of 13 px. |
| 2638 | `.num{font-variant-numeric:tabular-nums;white-space:nowrap}` | CSS: the class `num` (line 2401) has digits of equal width and keeps a number and its unit on one line. |
| 2639 | `.sm{color:#52514e;font-size:12.5px}` | CSS: the class `sm` (function `small`, line 1515): grey, 12.5 px. |
| 2640 | `figure{margin:16px 0}` | CSS: a figure has a margin of 16 px above and below. |
| 2641 | `.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}` | CSS: the class `fig`, the box around a drawing: it scrolls sideways when the drawing is wider, and it has a thin border with round corners. |
| 2642 | `.fig.fit{width:fit-content;max-width:100%}` | CSS: a box with the classes `fig` and `fit` is as wide as its content, and at most as wide as the page. |
| 2643 | `.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: a drawing inside such a box is shown as a block and uses the system font. |
| 2644 | `/* Figure 1 has three layouts, so it never scrolls sideways: 940 px wide in windows from 1000 px, 726 px from 780 px, 386 px below that.` | CSS comment: figure 1 has three layouts, so it never scrolls sideways. It is 940 px wide in windows from 1000 px, 726 px wide from 780 px, and 386 px wide below that. |
| 2645 | `   The box has a border of 1 px on each side, so the layouts need 942 + 49 px and 728 + 49 px of window width. */` | CSS comment, continued: the box has a border of 1 px on each side. So the two larger layouts need 942 + 49 px and 728 + 49 px of window width. |
| 2646 | `.fig svg.f1m,.fig svg.f1n{display:none}` | CSS: the mid layout (class `f1m`) and the narrow layout (class `f1n`) of figure 1 are hidden by default. So a window of 1000 px or more shows the wide layout. |
| 2647 | `@media (max-width:999px){.fig svg.f1w{display:none}.fig svg.f1m{display:block}}` | CSS: in a window of at most 999 px the wide layout (class `f1w`) is hidden and the mid layout is shown. |
| 2648 | `@media (max-width:779px){.fig svg.f1m{display:none}.fig svg.f1n{display:block;max-width:100%;height:auto}}` | CSS: in a window of at most 779 px the mid layout is hidden and the narrow layout is shown. The narrow drawing shrinks with the window. |
| 2649 | `.panels{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start}` | CSS: the class `panels`, the box of figure 2: its two panels stand side by side when the window is wide enough, with a gap of 10 px. If not, the second panel moves below the first. |
| 2650 | `.panels>.fig,.panels>.col{flex:0 1 468px;max-width:100%}` | CSS: each of the two parts of that box has a width of 468 px and may shrink. |
| 2651 | `ul.how{font-size:13.5px;color:#52514e;margin:10px 0 0;padding-left:20px}` | CSS: the reading notes under a figure (class `how`): grey, 13.5 px. |
| 2652 | `.legend{display:flex;flex-wrap:wrap;gap:4px 18px;font-size:13.5px;margin:0 0 8px}` | CSS: a legend (class `legend`): its entries stand in a row and wrap, in 13.5 px. |
| 2653 | `.legend .li{display:inline-flex;align-items:center;gap:6px}` | CSS: one legend entry (class `li`): the symbol and the text are centred on one line, 6 px apart. |
| 2654 | `.legend svg{flex:none}` | CSS: a legend symbol keeps its size. |
| 2655 | `.scale{font-size:13.5px;margin:0 0 8px}` | CSS: the class `scale`, the note about the two scales of figure 2 (line 2746): 13.5 px. |
| 2656 | `g.pt:hover .mk.fi{stroke:#0b0b0b;stroke-width:1.6}` | CSS: a filled dot under the pointer gets an outline of 1.6 px in the text colour. |
| 2657 | `g.pt:hover .mk.ho{stroke-width:3.6}` | CSS: a hollow dot under the pointer gets a wider outline of 3.6 px. It keeps its colour. |
| 2658 | `figcaption{font-size:14.5px;margin-top:8px}` | CSS: a figure caption: 14.5 px, with a margin of 8 px above it. |
| 2659 | `.take{font-weight:600}` | CSS: the class `take`, the first part of a figure caption (line 2732, line 2749): bold type. In both captions this part holds the figure number and two sentences. |
| 2660 | `.ref{color:#52514e;font-size:0.85em}` | CSS: a reference mark (class `ref`, line 825): grey and smaller. |
| 2661 | `.ref a{text-decoration:none;white-space:nowrap}` | CSS: the link of a reference mark is not underlined and does not break across two lines. |
| 2662 | `.ref a:hover{text-decoration:underline}` | CSS: the link is underlined while the pointer is on it. |
| 2663 | `.note{color:#52514e;font-size:14px}` | CSS: the class `note`, the two notes of the reference section (lines 2774 to 2775): grey, 14 px. |
| 2664 | `.tcap{font-size:14.5px;margin:18px 0 0}` | CSS: the class `tcap`, a table caption: 14.5 px, with a margin of 18 px above it. |
| 2665 | `.tcap b{font-weight:600}` | CSS: the bold part of a table caption has the weight 600. |
| 2666 | `.tcap b .ref{font-weight:400}` | CSS: a reference mark inside that bold part has normal weight. |
| 2667 | `td ul.cl{margin:0;padding-left:16px}` | CSS: a bullet list inside a table cell (class `cl`, line 2498): no margin, an indent of 16 px. |
| 2668 | `td ul.cl li{margin:0 0 5px}` | CSS: its items have a margin of 5 px below. |
| 2669 | `td ul.cl li:last-child{margin-bottom:0}` | CSS: its last item has no margin below. |
| 2670 | `ol.refs{font-size:14px;padding-left:0;list-style:none}` | CSS: the reference list (`ol` of the class `refs`): 14 px, no numbers from the list itself, no indent. |
| 2671 | `ol.refs li{margin:5px 0;overflow-wrap:anywhere}` | CSS: an item of the reference list may break at any character. |
| 2672 | `details{margin:8px 0}` | CSS: a folded part (`details`) has a margin of 8 px above and below. |
| 2673 | `summary{cursor:pointer;font-weight:600}` | CSS: the title of a folded part (`summary`) is in bold type, and the pointer shows a hand over it. |
| 2674 | `"""` | Ends the text constant `CSS`. |

### Function `build`: word list, reading notes and the two panels of figure 2 (lines 2677 to 2700)

| Line | Source | Explanation |
|---:|---|---|
| 2677 | `def build():` | Starts the function `build`. It returns the whole HTML page as one text. Line 2784 calls it. All figure functions and table functions run inside this call. |
| 2678 | `    words = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in WORDS)` | `words`: the word list as HTML: one pair of the elements `dt` (term) and `dd` (definition) per entry of `WORDS` (line 2323). |
| 2679 | `    short = "".join(P(s) for s in SHORT)` | `short`: one paragraph per sentence of `SHORT` (line 2411). `P` (line 1488) also adds each sentence to `PROSE` for the word count. |
| 2680 | `    how1 = ('<ul class="how">'` | `how1`: the reading notes under figure 1, a bullet list of the class `how` with three items. |
| 2681 | `            "<li>Each dot is the median of the intervals of its row. Point at a mark to see its values and its source file.</li>"` | Item 1: each dot of figure 1 is the median of the intervals of its row. `fig1` places the dots at these medians (line 1662). The item also tells the reader to point at a mark to see its values and its source file. |
| 2682 | `            f"<li>For bwx12 a source names the interval row of the csv file. The rate is the sum of the 120 thread rows after it. This sum differs from the rate printed in the interval row by at most {f2(IROW_MAX)} GB/s.</li>"` | Item 2 tells the reader how a bwx12 rate is computed. The source text of a tooltip (`src`, line 359) names the interval row of the csv file. The rate is the sum over the 120 thread rows after it: `val` (line 176) adds bytes / `elapsed_s` / 1e9 of each thread row. The item prints `f2(IROW_MAX)` (line 342). `IROW_MAX` is the largest difference between this sum, rounded to 0.01 GB/s, and the rate printed in the interval row, over the bwx12 records of `USED`. Line 343 allows at most 0.02 GB/s. The saved output of a build shows 0.02 GB/s [Ref5]. |
| 2683 | `            f"<li>The data of both figures come from facts.json, the data file of the facts sheet {ref('json')}.</li></ul>")` | Item 3: the data of both figures come from `facts.json`, the data file of the facts sheet. The line closes the list. |
| 2684 | `    how2 = ('<ul class="how">'` | `how2`: the reading notes of figure 2, a bullet list of the class `how` with four items. `fig2` puts them under the first panel (line 2697). |
| 2685 | `            "<li>A 7200 MT/s row with all dots left of the band, or all dots right of it, does not overlap the 8000 MT/s range.</li>"` | Item 1: a 7200 MT/s row with all dots left of the band, or all dots right of it, does not overlap the 8000 MT/s range. |
| 2686 | `            "<li>The bold text under a row name says where the row lies relative to the band: left of it (lower), inside it, overlapping it, or right of it (higher). "` | Item 2: the bold text under a row name says where the row lies relative to the band: left of it (lower), inside it, overlapping it, or right of it (higher). `p_row` writes this text (lines 1705 to 1706). |
| 2687 | `            "A 7200 MT/s row without bold text is not compared with a band.</li>"` | Continues item 2: a 7200 MT/s row without bold text is not compared with the grey band of its block (the range of the 8000 MT/s rows). |
| 2688 | `            "<li>Panel &quot;Load-only loop&quot;, 0.5 s blocks: only session 1 is compared, each round against the same round (rule V3). "` | Item 3, for the 0.5 s blocks of the panel `Load-only loop` (part A, `bw_new` read): only session 1 is compared, each round against the same round (rule V3). `A_V3` (line 509) holds these two comparisons. |
| 2689 | `            "Sessions 2 and 3 started 5 s after a 120-thread process of part C. Session 1 and the rows A-1 and A-2 did not. "` | Continues item 3: the sessions 2 and 3 started 5 s after a 120-thread process of part C. Session 1 and the rows A-1 and A-2 did not. Line 2486 asserts the first of these two sentences. |
| 2690 | `            f"Their first process started at a 1-minute load average of {f2(A_FIRST_LOAD['T72A1'])}, {f2(A_FIRST_LOAD['A-1'])} and {f2(A_FIRST_LOAD['A-2'])} (Table 6).</li>"` | Continues item 3: the three load values of `A_FIRST_LOAD` (lines 2487 to 2491): the 1-minute load average at the first launch of session 1, of row A-1 and of row A-2. |
| 2691 | `            f"<li>The figure shows {N_DOTS} intervals. Control I was added after the first numbers were seen. "` | Item 4: the number of dots `N_DOTS` (line 1960), and the label of control I. |
| 2692 | `            "Table 2 gives n for every comparison, except the three part A session rows of the old read kernel. "` | Continues item 4: Table 2 gives n for every comparison, except the three part A session rows of the old read kernel. |
| 2693 | `            f"Each of them has {A_SESSION_N} and is a part of the Table 2 row &quot;Part A (bw_old read)&quot;.</li></ul>")` | Continues item 4: the text `A_SESSION_N` (line 2495), the n of each of these three rows. The line closes the list. |
| 2694 | `    fig2 = ('<div class="panels"><div class="col"><div class="fig">'` | `fig2`: the two panels of figure 2 inside a `div` of the class `panels`. The first panel stands in a column (class `col`) together with the reading notes `how2`. |
| 2695 | `            + panel("Old read kernel", "bw_old read and bwx12 oldread", OLD_AX[0], OLD_AX[1], range(460, 477, 4), range(458, 477, 2), P_OLD_BLOCKS, BLUE,` | Draws the panel `Old read kernel` (`panel`, line 1756): the blocks `P_OLD_BLOCKS`, blue dots, an x axis from 458 to 476 GB/s (`OLD_AX`). The two `range` arguments give the grid lines: a label every 4 GB/s (460 to 476) and a grid line every 2 GB/s (458 to 476). The axis does not start at 0. `panel` writes this into the panel (line 1793, line 1820). |
| 2696 | `                    "Strip plot: every interval of the old read kernel, rows by method and memory speed")` | Continues the call: the text for screen readers. It names the chart a strip plot (one dot per measurement along one axis) of every interval of the old read kernel. |
| 2697 | `            + '</div>' + how2 + '</div><div class="fig">'` | Closes the box of the first panel, adds `how2`, closes the column and opens the box of the second panel. |
| 2698 | `            + panel("Load-only loop", "new read kernel, or asmread in its place where the label says so", NEW_AX[0], NEW_AX[1], range(280, 341, 20), range(280, 341, 10), P_NEW_BLOCKS, ORANGE,` | Draws the panel `Load-only loop`: the blocks `P_NEW_BLOCKS`, orange dots, an x axis from 276 to 340 GB/s (`NEW_AX`). It has a label every 20 GB/s (280 to 340) and a grid line every 10 GB/s. This axis does not start at 0 either. |
| 2699 | `                    "Strip plot: every interval of the load-only loop, rows by method and memory speed")` | Continues the call: the text for screen readers, for the load-only loop. |
| 2700 | `            + "</div></div>")` | Closes the box of the second panel and the `div` of the class `panels`. |

### Function `build`: the HTML text of the page (lines 2701 to 2783)

| Line | Source | Explanation |
|---:|---|---|
| 2701 | `    page = f"""<!doctype html>` | `page`: the page text, one f-string that ends in line 2780. Each expression between braces is replaced by its value. This first line declares the document as HTML. |
| 2702 | `<html lang="en" data-theme="light">` | Opens the `html` element: the language is English, and the attribute `data-theme` is `light`. |
| 2703 | `<head>` | Opens the head of the page. |
| 2704 | `<meta charset="utf-8">` | Head: the page is encoded in UTF-8. |
| 2705 | `<meta name="viewport" content="width=device-width,initial-scale=1">` | Head: the page is as wide as the window of the device, at a zoom of 1. |
| 2706 | `<title>Whole-chip read test at 7200 MT/s</title>` | Head: the title that the browser shows for the page. |
| 2707 | `<style>{CSS}</style>` | Head: the style block `CSS` (line 2580) inside a `style` element. |
| 2708 | `</head>` | Closes the head. |
| 2709 | `<body>` | Opens the body of the page. |
| 2710 | `<main>` | Opens the element `main`, the content box of at most 980 px (line 2584). |
| 2711 | `<h1>Whole-chip read test at 7200 MT/s: old read kernel against new read kernel</h1>` | The page title: the whole-chip read test at 7200 MT/s, old read kernel against new read kernel. |
| 2712 | `<p class="sub">2026-11-17, all times in UTC. Machine: CRB (an Arm reference server with 128 CPUs). 120 threads on CPUs 0-119, 256 MiB per thread. 12 memory modules at 7200 MT/s (million transfers per second, the unit of memory speed).</p>` | A typed line under the title (class `sub`) with the date, the machine and the method: all times in UTC, 120 threads on the CPUs 0 to 119, 256 MiB per thread, and 12 memory modules at 7200 MT/s. It also says what CRB and MT/s mean. |
| 2714 | `<h2 id="short">Short version</h2>` | The heading of the Short version. |
| 2715 | `<div class="short">` | Opens the box of the Short version (class `short`). |
| 2716 | `{short}` | The three sentences (`short`, line 2679). |
| 2717 | `</div>` | Closes the box. |
| 2718 | `<p class="more">More detail for these three sentences:</p>` | A line that starts the detail list for the three sentences (class `more`). |
| 2719 | `{SHORT_MORE}` | The bullet list `SHORT_MORE` (line 2423). |
| 2721 | `<details><summary>Words used here</summary>` | Opens a folded part with the title `Words used here`. It stays closed until the reader opens it. |
| 2722 | `<dl class="words">{words}</dl>` | The word list (`words`, line 2678) as a `dl` element of the class `words`. |
| 2723 | `</details>` | Closes the folded part. |
| 2725 | `<h2 id="q1">1. Is the new read kernel still below the old one? (Q1)</h2>` | The heading of page section 1 (question Q1): is the new read kernel still below the old one. |
| 2726 | `{SEC1_INTRO}` | The bullet list `SEC1_INTRO` (line 2444). |
| 2727 | `<figure>` | Opens the figure element of figure 1. |
| 2728 | `{LEG1}` | The legend `LEG1` (line 1975). |
| 2729 | `<div class="fig fit">{fig1("wide")}` | Opens the box of figure 1 (classes `fig` and `fit`) and draws the wide layout with `fig1` (line 1593). |
| 2730 | `{fig1("mid")}` | Draws the mid layout into the same box. |
| 2731 | `{fig1("narrow")}</div>` | Draws the narrow layout and closes the box. The style block shows one of the three drawings (lines 2646 to 2648). |
| 2732 | `<figcaption><span class="take">Figure 1. In the {len(SAME_LINE_ROWS)} rows that ran the argument line of part L (the same benchmark arguments) at 7200 MT/s, the blue dot (old read kernel) stays at nearly the same place, and the orange dot (load-only loop) moves. The intervals of the blue dots span {f2(VISIT_OLD_HI - VISIT_OLD_LO)} GB/s, and those of the orange dots span {f2(VISIT_HI - VISIT_LO)} GB/s.</span> The {len(SAME_LINE_ROWS)} rows are part L, {CI} and {F72}. Their ranges are {f2(VISIT_OLD_LO)} to {f2(VISIT_OLD_HI)} GB/s (old read kernel) and {f2(VISIT_LO)} to {f2(VISIT_HI)} GB/s (load-only loop). The orange dot is left of the blue dot in every row of the figure. So the load-only rate is lower in every row.</figcaption>` | The caption of figure 1. Its bold first part prints `len(SAME_LINE_ROWS)`, which line 1588 asserts to be 6, and two differences: `VISIT_OLD_HI - VISIT_OLD_LO` for the old read kernel and `VISIT_HI - VISIT_LO` for the load-only loop (lines 501 to 502). Each one is the highest minus the lowest interval rate over part L, control I and F72d12. The caption then names the 6 rows, with the labels of control I and of F72d12, and prints the four rates as two ranges. The last two sentences are typed: the orange dot is left of the blue dot in every row, so the load-only rate is lower in every row. Line 460 asserts a drop above 0 for every pair at 7200 MT/s. No assertion covers the 5 rows at 8000 MT/s. |
| 2733 | `{how1}` | The reading notes `how1` (line 2680). |
| 2734 | `</figure>` | Closes the figure element. |
| 2735 | `<p class="tcap"><b>Table 1. The drop per part.</b> The load-only loop is below the old read kernel in all {sum(N_RERUN_PAIRS)} pairs of the rerun rows of this table. It is also below it in the {len(C_ASM_DROPS)} asmread pairs of part C, which the table does not show {ref('T72C1', 'T72C2', 'T72C3', 'T72C4')}.</p>` | The caption of Table 1 (class `tcap`). It prints `sum(N_RERUN_PAIRS)` (line 2439), the number of pairs of the rerun rows of the table, and `len(C_ASM_DROPS)` (line 2442), the number of `asmread` pairs of part C, which the table does not show. By the text the load-only loop is below the old read kernel in all of them. Line 460 and line 2443 assert this. |
| 2736 | `{q1_table()}` | Table 1 from `q1_table()` (line 2003). |
| 2737 | `{SEC1_AFTER}` | The bullet list `SEC1_AFTER` (line 2451). |
| 2738 | `<details><summary>Table view of Figure 1: every row</summary>` | Opens a folded part with the table view of figure 1. |
| 2739 | `{detail_fig1()}` | The table of `detail_fig1()` (line 2255). |
| 2740 | `</details>` | Closes the folded part. |
| 2742 | `<h2 id="q2">2. Did a rate differ from the 8000 MT/s runs? (Q2)</h2>` | The heading of page section 2 (question Q2): did a rate differ from the 8000 MT/s runs. |
| 2743 | `{SEC2_INTRO}` | The bullet list `SEC2_INTRO` (line 2456). |
| 2744 | `<figure>` | Opens the figure element of figure 2. |
| 2745 | `{LEG2}` | The legend `LEG2` (line 1983). |
| 2746 | `<p class="scale">The two panels have different scales. The panel &quot;Old read kernel&quot; shows {OLD_AX[1] - OLD_AX[0]} GB/s over its width, and the panel &quot;Load-only loop&quot; shows {NEW_AX[1] - NEW_AX[0]} GB/s. So the same distance on the screen is {f1(Decimal(NEW_AX[1] - NEW_AX[0]) / Decimal(OLD_AX[1] - OLD_AX[0]))} times as many GB/s in the panel &quot;Load-only loop&quot;.</p>` | A note about the scales (class `scale`): the two panels have different scales. It prints the width of each axis from `OLD_AX` and `NEW_AX` (line 1958): 18 GB/s and 64 GB/s. It prints their ratio with 1 decimal: 3.6. So the same distance on the screen is 3.6 times as many GB/s in the panel `Load-only loop`. |
| 2747 | `<p class="hint h2">If a panel does not fit the screen, scroll it sideways to see all dots.</p>` | A hint to scroll a panel sideways (classes `hint` and `h2`). The style block shows it only in a window of at most 519 px (line 2617). |
| 2748 | `{fig2}` | The two panels (`fig2`, line 2694). |
| 2749 | `<figcaption><span class="take">Figure 2. In the panel &quot;Old read kernel&quot; every 7200 MT/s row overlaps the grey band of its block, except part L. In the panel &quot;Load-only loop&quot; every 7200 MT/s row that is compared with a band lies to the right of it (higher), except F72d12 (earlier run of the same boot, not part of the rerun).</span> {F2_RIGHT_TXT} Part L of the old read kernel lies {f2(abs(L_OLD_NEAR))} GB/s left of its band at the nearest ends (lower), and its median is {f2(abs(L_OLD_MED))} GB/s below the median of the band rows. F72d12 lies inside its band.</figcaption>` | The caption of figure 2. Its bold first part says that every 7200 MT/s row of the panel `Old read kernel` overlaps the grey band of its block, except part L. It also says that every compared 7200 MT/s row of the panel `Load-only loop` lies to the right of its band, except F72d12. Line 1944 and lines 1951 to 1953 assert both. Then the caption prints `F2_RIGHT_TXT` (line 1954), `abs(L_OLD_NEAR)` (the distance of part L of the old read kernel left of its band) and `abs(L_OLD_MED)` (the distance of its median below the median of the band rows). |
| 2750 | `</figure>` | Closes the figure element. |
| 2751 | `<p class="tcap"><b>Table 2. 7200 MT/s against 8000 MT/s, one row per comparison.</b> The rows that are compared come from 1 boot per memory speed. All {GO_DONE} steps of the rerun ran inside one period of {GO_SECS // 60} min {GO_SECS % 60} s ({RERUN['go_start'][11:19]} to {RERUN['go_end'][11:19]} UTC) of the 7200 MT/s boot. {T2_RERUN_ROWS}</p>` | The caption of Table 2. It says that the compared rows come from 1 boot per memory speed. It prints `GO_DONE`, the run time `GO_SECS` (line 2438) as minutes and seconds, the start time and the end time of `go.sh`, and the text `T2_RERUN_ROWS` (line 2074). |
| 2752 | `{q2_table()}` | Table 2 from `q2_table()` (line 2079). |
| 2753 | `<h3>The rate of the load-only loop changed inside the one 7200 MT/s boot</h3>` | A lower heading: the rate of the load-only loop changed inside the one 7200 MT/s boot. |
| 2754 | `{SEC2_BOOT}` | The bullet list `SEC2_BOOT` (line 2462). |
| 2755 | `<p class="tcap"><b>Table 3. The three visits of the part L line in the 7200 MT/s boot.</b> asmread is at position 1 and oldread at position 0 of each process {ref('json')}.</p>` | The caption of Table 3. It says that `asmread` is at position 1 and `oldread` at position 0 of each process. Lines 275 to 280 select the records of the three visits at these positions. |
| 2756 | `{visits_table()}` | Table 3 from `visits_table()` (line 2184). |
| 2757 | `<p class="tcap"><b>Table 4. Three kinds of distance (asmread), each for part L against the 8000 MT/s pool and for part L against F72d12 (earlier run of the same boot, not part of the rerun) {ref('json')}.</b> n of part L: {n7200(L_ASM)}. n of the pool L-1 to L-4: {n8000(P_L_ASM)}. n of F72d12: {n7200(F_ASM)}. At the nearest ends and at the medians, part L lies farther above F72d12 than above the pool. At the farthest ends the order is the opposite.</p>` | The caption of Table 4. It prints the texts of n of part L, of the pool L-1 to L-4 and of F72d12. Two typed sentences follow: at the nearest ends and at the medians, part L lies farther above F72d12 than above the pool, and at the farthest ends the order is the opposite. No assertion checks them. The values of line 2215 agree with them. |
| 2758 | `{dist_table()}` | Table 4 from `dist_table()` (line 2213). |
| 2759 | `<details><summary>Table view of Figure 2: every interval</summary>` | Opens a folded part with the table view of figure 2. |
| 2760 | `{detail_fig2()}` | The table of `detail_fig2()` (line 2266). |
| 2761 | `</details>` | Closes the folded part. |
| 2763 | `<h2 id="open">3. What the data do not show</h2>` | The heading of page section 3: what the data do not show. |
| 2764 | `{INSUFF}` | The bullet list `INSUFF` (line 2467). |
| 2766 | `<h2 id="state">4. Machine state and system load</h2>` | The heading of page section 4: machine state and system load. |
| 2767 | `<p class="tcap"><b>Table 5. Machine state: each fact with its proof and its limit.</b></p>` | The caption of Table 5: each fact of the machine state with its proof and its limit. |
| 2768 | `{state_table()}` | Table 5 from `state_table()` (line 2503). |
| 2769 | `<h3>System load</h3>` | A lower heading: system load. |
| 2770 | `<p class="tcap"><b>Table 6. 1-minute load average of Linux, read by the scripts directly before each launch {ref('json')}.</b> {LOAD_CAPTION}</p>` | The caption of Table 6: the 1-minute load average of Linux, read by the scripts directly before each launch. The text `LOAD_CAPTION` follows (line 2573). |
| 2771 | `{load_table()}` | Table 6 from `load_table()` (line 2219). |
| 2773 | `<h2 id="refs">References</h2>` | The heading of the reference section. |
| 2774 | `<p class="note">A script computed every rate of this page from the interval records of the facts sheet and from the thread rows of the csv files that these records name. It read the facts of section 4 from the raw files cited there {ref('gen', 'json', 'facts', 'build')}.</p>` | A typed note (class `note`): a script computed every rate of the page from the interval records of the facts sheet and from the thread rows of the csv files that these records name. It read the facts of section 4 from the raw files cited there. Then come four reference marks: this script, `facts.json`, `FACTS.md` and `build_facts.py`. |
| 2775 | `<p class="note">R = <code>{R}</code><br>S = <code>{S}</code></p>` | A second note: the two folder paths `R` and `S` (lines 29 to 30). |
| 2776 | `<ol class="refs">\x01REFLIST\x01</ol>` | The reference list. `\x01REFLIST\x01` (the word REFLIST between two control characters) is a placeholder. `number_refs` replaces it by the list items (line 838). |
| 2777 | `</main>` | Closes the element `main`. |
| 2778 | `</body>` | Closes the body. |
| 2779 | `</html>` | Closes the `html` element. |
| 2780 | `"""` | Ends the f-string. |
| 2781 | `    return page` | Returns the page text. |

### Building the page, and the checks of the built page (lines 2784 to 2818)

| Line | Source | Explanation |
|---:|---|---|
| 2784 | `PAGE, UNCITED = number_refs(build())` | Calls `build`, and then `number_refs` (line 828) with its result. `number_refs` replaces each reference mark by `[RefN]`, numbered in the order of first use, and writes the reference list. `PAGE` is the finished page text. `UNCITED` is the list of the reference keys that the page never cites. |
| 2786 | `# ------------------------------------------------------------------ checks of the built page` | Comment: a section mark. The checks of the built page start here. Each `check` call (line 52) adds one PASS or FAIL line to `CHECKS`. The script does not stop here. |
| 2787 | `words_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in PROSE)   # a lone "%" or "/" is not a word` | `words_n`: the number of words in `PROSE`, the texts that `P` and `UL` collected. `strip_tags` (line 1484) removes the tags and the reference marks first. The pattern `\S+` finds each run of characters without white space. A run counts as a word when it holds a letter or a digit (pattern `[A-Za-z0-9]`). Comment at the end of the line: a lone `%` or `/` is not a word. |
| 2788 | `how_n = sum(len([w for w in re.findall(r"\S+", strip_tags(t)) if re.search(r"[A-Za-z0-9]", w)]) for t in re.findall(r'<ul class="how">(.*?)</ul>', PAGE, re.S))` | `how_n`: the same count for the reading notes under the two figures. The pattern finds each list of the class `how` in `PAGE`. Its group 1 holds the text between `<ul class="how">` and the next `</ul>`. `re.S` lets that text span several lines. |
| 2789 | `check(700 <= words_n <= 1000, f"prose outside tables, captions, word list and references: {words_n} words (target 700 to 1000). "` | Check: `words_n` must be from 700 to 1000 words. The message prints the count. |
| 2790 | `                              f"Counted as captions and not as prose: the figure and table captions, and the reading notes under the two figures ({how_n} words)")` | Continues the message: it names what is counted as captions and not as prose, and prints `how_n`. |
| 2791 | `check(len(SHORT) == 3 and all(len(re.findall(r"[.!?](?:\s\|$)", strip_tags(s).replace("MT/s.", "MT/s"))) == 1 for s in SHORT), "Short version: 3 sentences")` | Check: `SHORT` must hold 3 texts, each with exactly one sentence end. A sentence end is `.`, `!` or `?` before white space or at the end of the text. So a decimal point does not count. A full stop directly after `MT/s` does not count either: `replace` removes it before the count. |
| 2792 | `check(not UNCITED, f"references: {len(REFS)} paths exist, {len(REFS) - len(UNCITED)} are cited in the body, numbered in the order of first use")` | Check: no reference may be uncited. The message prints the number of references (`len(REFS)`) and the number that the body cites. |
| 2793 | `check(not re.search(r"prefers-color-scheme\|<script\|<link\|@import\|url\(\|<img\|src=", PAGE), "one light theme, no script, no external file")` | Check: the page must hold none of the texts `prefers-color-scheme`, `<script`, `<link`, `@import`, `url(`, `<img` and `src=`. So it has one colour theme, no script and no external file. |
| 2794 | `# control I and F72d12 carry their label in every bullet, caption, table row and tooltip that names them` | Comment: control I and F72d12 must carry their label in every bullet, caption, table row and tooltip that names them. |
| 2795 | `units = [strip_tags(x[1]) for x in re.findall(r"<(li\|p\|figcaption\|title\|dd\|tr)\b[^>]*>(.*?)</\1>", PAGE, re.S)]` | `units`: the texts of the `li`, `p`, `figcaption`, `title`, `dd` and `tr` elements of the page, each as plain text. In the pattern, group 1 holds the tag name, and group 2 holds the content up to the first closing tag of the same name (`\1`). `\b` keeps a longer tag name such as `path` from matching `p`. The search goes on after the end of a match. So a list item inside a table row is not a unit of its own. It belongs to the unit of that row. |
| 2796 | `for lab_, pat, must in (("control I", r"[Cc]ontrol I\b", ("added after the first numbers were seen",)),` | Starts a loop that runs once for control I and once for F72d12. Each run has a name, a pattern and the label texts. For control I the pattern matches `control I` or `Control I` at a word end, and the label is `added after the first numbers were seen`. |
| 2797 | `                        ("F72d12", r"F72d12", ("not part of the rerun",))):` | Continues the list of the loop: for F72d12 the pattern is the name, and the label is `not part of the rerun`. |
| 2798 | `    hit = [u for u in units if re.search(pat, u)]` | `hit`: the units that name it. |
| 2799 | `    miss = [u for u in hit if not any(m in u for m in must)]` | `miss`: those units of `hit` that hold none of its label texts. |
| 2800 | `    check(len(hit) > 0 and not miss, f"label of {lab_}: {len(hit)} text units name it, {len(miss)} without the label in the same unit" + ("" if not miss else ": " + " \| ".join(m[:60] for m in miss)))` | Check: passes when `hit` is not empty and `miss` is empty. The message prints both counts. For a failed check it adds the first 60 characters of each unit of `miss`. |
| 2801 | `check(len(re.findall(r"<title>", PAGE)) - 1 >= N_DOTS + 2 * F1_NROWS, f"tooltips: {len(re.findall(r'<title>', PAGE)) - 1} SVG titles for {N_DOTS} interval dots and {3 * F1_NROWS} marks of figure 1 (drawn in three layouts)")` | Check of the tooltips. The line counts the `<title>` tags of the page and subtracts 1 for the page title. The rest are tooltips. The check passes when their number is at least `N_DOTS + 2 * F1_NROWS`. This is a lower limit. With the 139 dots of the saved output and the 21 rows of line 1590 it is 139 + 2 x 21 = 181 tooltips [Ref5]. The message prints `3 * F1_NROWS`, not the limit of the test. The saved output of a build shows 333 tooltips [Ref5]. |
| 2802 | `# wording checks of the visible text and of the tooltips (the style block is not text)` | Comment: wording checks of the visible text and of the tooltips. The style block is not text. |
| 2803 | `VISIBLE = strip_tags(re.sub(r"<style>.*?</style>", " ", PAGE, flags=re.S))` | `VISIBLE`: the text of the page without the style block and without tags. The inner `re.sub` removes the `style` element with its content. The tooltips are included. |
| 2804 | `BANNED = [";", "load-only kernel", "at three times", "directly after none", "counter events", "bwx runners", "I row", "T rows", "ran above", "loop moved",` | `BANNED`: 16 phrases that a review rejected. This line holds the first ten. The semicolon is one of them. |
| 2805 | `          "identical argument line", "facts file", "fall into", "lies against", "explains why", "By its name"]` | Continues the list: six more phrases. |
| 2806 | `found = [b for b in BANNED if b in VISIBLE]` | `found`: the phrases of `BANNED` that stand in `VISIBLE`. |
| 2807 | `check(not found, f"wording: none of {len(BANNED)} phrases that the review rejected is in the text or in a tooltip (semicolon, 'load-only kernel', 'at three times', ...)" + ("" if not found else ". Found: " + ", ".join(repr(b) for b in found)))` | Check: passes when none of them is in the visible text or in a tooltip. A failed check lists the phrases that were found. |
| 2809 | `# "kernel" alone means the benchmark loop on this page. The operating system kernel is written "Linux kernel" ("kernel log" has its own entry in the word list)` | Comment: on the page, the word kernel alone means the benchmark loop. The operating system kernel is written `Linux kernel`. The term `kernel log` has its own entry in the word list. |
| 2810 | `bare = re.findall(r"(?<!Linux )\bkernel (?:thread\|line\|message)\w*", VISIBLE)` | `bare`: every place where `kernel thread`, `kernel line` or `kernel message` stands without `Linux` and a space directly before it. `(?<!Linux )` is the part of the pattern that tests the text directly before the match: it must not be `Linux` and a space. `\w*` also takes a plural ending. |
| 2811 | `check(not bare, "wording: every kernel thread, kernel line and kernel message is written with 'Linux' before it" + ("" if not bare else ". Found: " + ", ".join(sorted(set(bare)))))` | Check: passes when the list `bare` is empty. A failed check lists what was found. |
| 2812 | `f2_areas = sorted(a for g in F2_GAPS for a in g[4])` | `f2_areas`: the areas of all hover areas of figure 2, sorted. `panel` stored them in `F2_GAPS` (line 1788). |
| 2813 | `check(len(F2_GAPS) == 2 and sum(g[1] for g in F2_GAPS) == N_DOTS == len(f2_areas),` | The last check covers the hover areas of figure 2. It passes when `F2_GAPS` holds 2 panels, and the number of dots and the number of areas both equal `N_DOTS`. |
| 2814 | `      f"figure 2, hover areas: {N_DOTS} dots. The smallest distance of two dots is {min(g[2] for g in F2_GAPS):.2f} px (more than 5.2 px, the largest radius of a mark). "` | The message, first part: the number of dots, and the smallest distance of two dots in px. |
| 2815 | `      f"Each hover area is the part of a circle of {HIT_R:.0f} px radius that is nearer to its dot than to any other dot, so no two areas overlap. "` | Continues the message: what a hover area is: the part of a circle of the radius `HIT_R` that is nearer to its dot than to any other dot. |
| 2816 | `      f"{N_DOTS - sum(g[3] for g in F2_GAPS)} areas are the full circle ({max(f2_areas):.0f} px2), and a neighbour cuts {sum(g[3] for g in F2_GAPS)}. "` | Continues the message: how many areas are the full circle, with the size of that circle in square px, and how many a neighbour cuts. |
| 2817 | `      f"Smallest area {f2_areas[0]:.0f} px2, median {median(f2_areas):.0f} px2 (a painted mark of 4.3 px radius covers {math.pi * 4.3 ** 2:.0f} px2)")` | Continues the message: the smallest area and the median area. For comparison it gives the area that a painted mark of 4.3 px radius covers. |

### Printing the self-check list and writing the page (lines 2819 to 2834)

| Line | Source | Explanation |
|---:|---|---|
| 2819 | `print("self-check list of make_report.py")` | Prints the title line of the self-check list. |
| 2820 | `bad = 0` | `bad`: the number of FAIL lines. It starts at 0. |
| 2821 | `for ok, text in CHECKS:` | Starts the loop over the entries of `CHECKS`. |
| 2822 | `    bad += 0 if ok else 1` | Adds 1 to `bad` for an entry that failed. |
| 2823 | `    print(("  PASS  " if ok else "  FAIL  ") + text)` | Prints one line per entry, with `PASS` or `FAIL` before its text. |
| 2824 | `print(f"{len(CHECKS) - bad} of {len(CHECKS)} checks pass")` | Prints how many checks pass. The saved output of a build shows `98 of 98 checks pass` [Ref5]. |
| 2825 | `if bad:` | Tests whether at least one check failed. |
| 2826 | `    print("NOT WRITTEN: a check failed. The page on disk was not changed.")` | Prints `NOT WRITTEN` with the reason: a check failed, and the page on disk was not changed. |
| 2827 | `    sys.exit(1)` | Ends the script with exit status 1. The output file is not opened in this case. So the page on disk stays as it was. |
| 2828 | `DATA = PAGE.encode("utf-8")` | `DATA`: `PAGE` encoded as UTF-8 (the usual byte encoding of text). The script reaches this line only when every check passed and no `need` call stopped it before. |
| 2829 | `with open(OUT, "wb") as f:` | Opens `OUT` (line 31) for writing bytes. An older page file is replaced. Lines 2829 to 2830 are the only write of the script. |
| 2830 | `    f.write(DATA)` | Writes the bytes. |
| 2831 | `print(f"wrote {OUT} ({len(DATA)} bytes, {len(PAGE)} characters)")` | Prints the path, the size in bytes and the number of characters. The saved output of a build shows a page of 425796 bytes [Ref5]. |
| 2832 | `print("Short version as built:")` | Prints a title line for the Short version. |
| 2833 | `for s in SHORT:` | Starts the loop over the three sentences of `SHORT`. |
| 2834 | `    print("  " + re.sub(r"\s+", " ", strip_tags(s)).replace("( ", "(").replace(" )", ")").strip())` | Prints each sentence as plain text: without tags (`strip_tags`), with each run of white space as one space, and without the space that this leaves inside a round bracket. This is the last line of the file. |

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
