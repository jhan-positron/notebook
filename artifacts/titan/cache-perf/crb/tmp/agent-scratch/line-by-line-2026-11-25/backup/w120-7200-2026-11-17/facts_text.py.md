# `facts_text.py` explained

- Source file: `facts_text.py` in this folder (Python script, 1488 lines, 112658 bytes).
- sha256 of the source when this page was built: `44b01d6fc629a3b17057664420c109ea121c1b2f054af72ac1ff62687b3dbf80`.
- Role in the whole-chip test: Analysis module: computes the old-against-new statistics, writes sections 0-3 and 7 of FACTS.md.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

`render(D)` takes the interval records that `build_facts.py` collected from the raw result files, and it returns the verdict object for facts.json and the complete text of the facts sheet `S/FACTS.md`. This file computes the old-against-new pairs, medians, drops and ranges. It writes the title, sections 0 to 3 and section 7 itself, and it calls facts_text4.py for sections 4 to 6.

<details>
<summary>Words used here</summary>

- **Rerun**: the whole-chip read test of 2026-11-17 at 7200 MT/s: the runs of the scripts go.sh and go2.sh.
- **go.sh, go2.sh, ra.sh, rx.sh, r0.sh**: the run scripts. go.sh is the driver script of the rerun: it runs three sessions and then one more part C process. go2.sh is the script of control I. ra.sh is the script of part A: it starts the 24 processes of bw_old and bw_new one after the other. rx.sh is the runner script of the bwx12 processes (parts L, C and I): it starts one process per line of a spec file. r0.sh is the earlier script that ran the two bwx11 processes of the data set R0.
- **S, R**: `S` is the folder of this script (`/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`). `R` is the folder `/home/jhan/workspace/titan/cache-perf/crb/results`. It holds the result folders that were copied back from CRB.
- **Facts sheet**: the file `S/FACTS.md`. `render` of this file builds its text, and `build_facts.py` writes the file. It holds the numbers of the rerun, and its section 7 lists the raw files that they come from. Its first lines call it the source for the report of the rerun. The report script make_report.py computes its numbers from the records of facts.json and compares them with the facts sheet [Ref9].
- **facts.json**: the second output file. It holds every record of `D['recs']` (one record per collected interval), plus the parts `meta` and `verdicts`. `build_facts.py` writes it.
- **Q1, Q2**: the two questions of the facts sheet. Q1: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much. Q2: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.
- **`D`**: the data object, a Python dictionary. The functions `collect` and `run_checks` of `build_facts.py` fill it from the raw files [Ref1]. This file only reads it. Keys used here: `recs` (the records), `checks` (the integrity checks), `A` (the 3 part A folders), `X` (the 9 bwx12 folders of the rerun), `events` (the steps of the run in time order), `logs` (the logs of go.sh and go2.sh), `P_kB` (the buffer sizes in kB in the P rows of the rerun), `base`, `rx` and `step` (earlier runs), `env_partA` (the text of env.txt of the run folder of A-2), and `try6`, `probe13`, `mod`, `fw`, `a2pre`, `boot_table` (records of the machine state).
- **Record**: one dictionary per timed interval, in the list `D['recs']`. The statistics use these fields: `dataset`, `binary`, `kernel`, `session`, `round`, `pos` (the position), `interval`, `tag`, `kernel_before`, `proc_key`, `boot`, `GBps`, `mesh0_GBps`, `mesh1_GBps`, `passes`, `min_ms`.
- **`GBps`**: the rate of one interval in GB/s, with GB = 1e9 bytes. It is set before this file runs. Part A: the value of the column `aggregate_GBps` of the interval row in `threads120.csv`. The records of the data sets A-2 and A-3 take it from `A1.csv` and `A3.csv`. bwx runners: the sum over the T rows of the interval (one row per thread) of `bytes / elapsed_s / 1e9` [Ref1] [Ref2].
- **`mesh0_GBps`, `mesh1_GBps`**: bwx records only: the same sum as `GBps`, taken over the threads on CPUs 0-63 (mesh 0) and over the threads on CPUs 64 and above (mesh 1) [Ref2]. The facts sheet prints them as "m0 + m1".
- **Data set (`dataset`)**: the field of a record that names its group of runs. Rerun at 7200 MT/s: `rerun-A`, `rerun-L`, `rerun-C`, `control-I`. Earlier run in the same 7200 MT/s boot: `F72d12`. 8000 MT/s runs of part A: `A-1`, `A-2`, `A-3`. 8000 MT/s runs of bwx12: `L-1` (the baseline with the identical argument line) and `L-2` to `L-4` (supporting rows). Runs of bwx11: `R0`, `R0b`. Runs of the first runner bwx: `B7a`, `B7b`, `C3a`, `C3b`. The facts sheet calls an earlier data set a "row", for example "row L-1". The records hold 8 more data sets, for example `X2d12` and three runs with 10 memory modules [Ref6]. This file selects none of them.
- **`BW12`, `BW11`, `BWX`**: three constants of this file with data set names. `BW12` = L-1 to L-4 (runner bwx12). `BW11` = R0, R0b (runner bwx11). `BWX` = B7a, B7b, C3a, C3b (first runner bwx).
- **F72d12**: one bwx12 process with the argument line of part L. It ran on 2026-11-17 at 20:02 UTC in the same 7200 MT/s boot, before the rerun. It is not part of the rerun.
- **`tag`**: the field of a record that names its process or step. Rerun: the folder tag of the step, for example `T72A1` (part A, session 1), `T72L1` or `T72C4`. Earlier bwx runs: the name of the csv file without `.csv`, or the tag of the process inside the csv [Ref1].
- **`kernel_before`**: bwx records: the kernel of the interval that ran directly before in the same process. For the first interval of a process the field holds the text `none (first interval of the process)`, which is the constant `FIRST` of this file. Part A records: binary and kernel of the process before it in the file. For the first process of a file the field holds the text `none (first process of the file)`. For the second and the third process of A-3 it holds a text that starts with `not listed`: other processes of `A3.csv` ran between the processes of A-3 [Ref1] [Ref2].
- **`proc_key`**: a text that names one process: folder, file, and process number or tag. The function `rng` counts the processes of a list with it.
- **Interval number**: the field `interval` of a record. Part A: the value of the column `rep` of the csv row (0, 1, 2). bwx runners: round x length of the kernel sequence + position.
- **Interval length (`min_ms`)**: the field `min_ms` of a record: the shortest length of one timed interval, in ms. Part A: 500 (0.5 s). `build_facts.py` writes this fixed value into every part A record [Ref1]. bwx runners: the value `min_ms` of the header line of the csv, 6000 (6 s) in the rerun.
- **`N`**: the statistics object that `analyse` returns, a dictionary. `N['pa']`: the 6 pairs of part A. `N['pl']`, `N['pi']`, `N['pf']`, `N['pc']`, `N['p80']`: the pairs of the data sets `rerun-L`, `control-I`, `F72d12`, `rerun-C` and `L-1`. `N['pool']`: the selector function `pool`. `render` adds `N['CG']`, the five groups of part C.
- **`dl`, `di`, `df`, `dcr`, `dca`, `dpa`**: six lists of drops in percent, one value per pair (lines 390 to 395). `dl`, `di` and `df` hold the drops of asmread in part L, in control I and in F72d12. `dcr` and `dca` hold the drops of `read` and of asmread in part C. `dpa` holds the drops of the 6 pairs of part A.
- **`L72o`, `L72a`, `I72o`, `I72a`, `F72o`, `F72a`, `A72o`, `C72o`, `P12o`, `P12a`**: record lists that `render` selects at lines 414 to 421. `L72`, `I72`, `F72`, `A72` and `C72` are part L, control I, F72d12, part A and part C at 7200 MT/s. `P12` is the pool of the data sets L-1 to L-4 at 8000 MT/s. The last letter names the kernel: o = oldread (`bw_old read` in part A), a = asmread. `P12o` holds oldread at position 0 only. `P12a` holds asmread at position 1 only. Three more names follow the same pattern. `PALLo` and `PALLa` are these pools plus the bwx11 data sets R0 and R0b. `A80o` is `bw_old read` of the data sets A-1 to A-3.
- **`cLo`, `cLa`, `cIo`, `cIa`, `cFo`, `cFa`, `cAo`, `cCo`**: the eight results of `compare` that `render` builds at lines 422 to 425. The second letter names the 7200 MT/s side: L = part L, I = control I, F = F72d12, A = part A, C = part C. The last letter names the kernel: o = the old read kernel (oldread, or `bw_old read` in part A), a = asmread. Each result holds `a` (the 7200 MT/s range), `b` (the 8000 MT/s range), `overlap`, `dist` (the distance of the nearest ends in GB/s), `wording` and `width`.
- **`V`**: the verdict object, a dictionary. `render` returns it. `build_facts.py` stores it in facts.json under `verdicts`.
- **Verdict**: the text that answers Q1 or Q2 (`V['q1']`, `V['q2']`).
- **`L`, `w`**: `L` is the list of the text lines of FACTS.md. `w` is a short name for `L.append`. One call `w(text)` adds one line. `L.extend(table(...))` adds the lines of one table.
- **Markdown**: the plain-text format of FACTS.md. A table row is one line with the cells between `|` characters.
- **UTC**: Coordinated Universal Time, the time standard without a time zone offset. All times of the facts sheet are in UTC.
- **File time**: the time of the last change of a file, as the file system stores it. The Python function `os.path.getmtime` returns it.
- **`ref`, [RefN]**: inside `render`, `ref` is the object of the class `Refs` that `register` returns. `ref(path)` returns the text `[RefN]`. N is the number of that file in the file list of section 7 of the facts sheet. These numbers belong to the facts sheet. They are not the reference numbers of this page.
- **`ctx`, `c`, `extra`**: `ctx` is the dictionary that `render` passes to `section4` of facts_text4.py (line 1459). It holds the record lists and comparisons of this file. `section4` adds its own results to it, and `short_version` reads them under the name `c`. `extra` holds a few texts and values of section 1 that go into `ctx`.
- **Template**: a text with placeholders such as `%s`, `%d` or `%.2f`. The Python operator `%` puts values into the placeholders.
- **Fixed text**: words that are written in a template of the source. No value from the data changes them.
- **Guard**: a call `need(condition, text)`. The script stops with an error message when the condition is false.
- **Lambda**: a small Python function that is written as one expression, in the form `name = lambda arguments: expression`.
- **Tuple**: a fixed list of values in Python, written in round brackets.
- **Pair**: two rates that are compared for Q1. Part A: the median of the bw_new process and the median of the bw_old process of the same session and round. bwx12: one interval of asmread or read, and the oldread interval of the same process and round.
- **Drop**: (1 - new rate / old rate) x 100, in percent. It says how far the new read kernel or asmread is below the old read kernel.
- **Ratio new/old**: the new rate divided by the old rate. It has no unit.
- **Median**: the middle value of a sorted list. For the 3 intervals of a part A process it is the second highest rate. For an even number of values the Python function `statistics.median` returns the mean of the two middle values.
- **Range**: the result of the function `rng` of facts_data.py for a list of records: the lowest rate `lo`, the highest rate `hi`, the median `med`, and the numbers of intervals `n`, of processes `procs`, of sessions `sessions` and of boots `boots` [Ref2].
- **Width**: of a range: (hi - lo) / lo x 100, in percent. For an 8000 MT/s range the facts sheet gives it as the size of a difference that the comparison cannot exclude (est.).
- **Wording**: the fixed result text of rule V1 point 2 [Ref5]. The constant `SAME` is "no difference seen" (the two ranges overlap). The constant `DIFFERS` is "differs between the 8000 MT/s boot and the 7200 MT/s boot" (the two ranges do not overlap).
- **cfwd, crev**: the two argument lines of part C. cfwd runs oldread, read, asmread. crev runs asmread, read, oldread.
- **Half up**: a rounding rule: a value exactly in the middle between two steps is rounded to the step that is farther from 0. For a positive value that is the higher step.
- **Decision (a) to (r)**: the lettered list in section 2 of the facts sheet. Each entry is a choice that the author made for the run or for the analysis.
- **Detail line**: one entry of the list `detail` of `short_version`. The facts sheet prints the 12 detail lines as bullets under the three sentences of section 0.
- **Step, event**: one run of ra.sh or rx.sh in the rerun. It is one entry of `D['events']`, with the folder tag, the times, the load and the start state.
- **Gap (`gap_s`)**: the first launch of a step minus the end of the previous 120-thread process of the rerun, in seconds.
- **Start state**: a text per step. It says what ran before the first process of the step: an idle machine, or a 120-thread process that ended some seconds before.
- **Integrity check**: one of the 27 checks of the raw files and scripts that the function `run_checks` of `build_facts.py` ran before `render` [Ref1]. Each check is one entry of the list `D['checks']` with a key (for example `sha-rx`), a result and a text. Section 1.4 of the facts sheet lists the checks.
- **probe.txt, env.txt, launches.txt, stderr.txt**: files that the run scripts wrote into a result folder. probe.txt (ra.sh, part A): boot id, MemTotal, load, sha256 of bw_old, bw_new and ra.sh. env.txt (rx.sh): start time, Linux release, load, busiest processes, sha256 of bwx12. launches.txt (rx.sh): the launch line with load and arguments, and the rc line. stderr.txt: the error output of bwx12.
- **try6.txt**: the record of the boot of the rerun. It holds the boot id, MemTotal, the Linux kernel message with the module count and the line with the memory speed 7200 MT/s.
- **DIMM report**: the file `DIMM-flaky-report.md` (constant `DIMM_REPORT` of facts_data.py). It holds the boot history with the module count of each boot and the change of the memory speed to 7200 MT/s.
- **Boot table**: the list of boots in section 3 of the DIMM report, with the number, the start time and the module count of each boot. `D['boot_table']` holds it. `D['boot_table']` also holds the time until which the memory speed setting was 8000 MT/s.
- **h-1.txt, h-5.txt, k-1.txt, k-5.txt**: files in `R/dimm-check-20261117`. h-1.txt and k-1.txt are the saved journal and the saved Linux kernel log of the 10-module boot that started on 2026-11-17 at 04:17 UTC. h-5.txt and k-5.txt are those of the 12-module boot in which the test of 2026-11-13 ran. That boot started on 2026-11-09.
- **boots.txt**: a file in `R/dimm7200-20261117` that lists the boots of the journal: one row per boot with a number, the boot id and two times. Row 0 is the boot of try6.txt, which is the boot of the rerun. Its two times are 20:02:21 and 20:06:19 UTC on 2026-11-17. The second time equals the file time of boots.txt. So the row covers the boot only up to the moment when the file was written.
- **Rules file**: the file `S/baselines-and-rules.txt`: the fixed list of 8000 MT/s baselines and the comparison rules V1 to V4, F1 and F2. It was written before the run [Ref5].
- **`local.sha`**: a file in `S`. It holds the sha256 values that go.sh, ra.sh and the three spec files like.spec, cfwd.spec and crev.spec had when the rerun started. Line 20 of go.sh was edited on 2026-11-24. Since then go.sh no longer has the value that the file lists for it. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit.
- **stat_k120.py, stat_bwx.py**: two earlier analysis scripts in `S`. They compute quick statistics of the part A files and of the bwx files. `build_facts.py` compares its own values with their output in two integrity checks [Ref1].
- **One-thread phase**: the part of the script of 2026-11-13 that ran 192 processes with one thread each. It ran after the build and the self-test, and before the 120-thread part.
- **Settings tool**: `uefisettings`, a tool of Arm that reads and writes firmware settings. It needs root.
- **Settings list (`questions.json`)**: a file that the settings tool wrote. It holds a list of entries. Each entry has the name of a firmware setting, its answer (the value), its options and a help text.
- **Reply file (`set.txt`)**: a file that holds what the settings tool answered to a change of a setting. Each reply to a change carries the flag `modified`. Three of the four files (folders x1, x2 and revert) start with a date line. They also hold replies to readings of a setting, which carry no such flag.
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
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Pass count**: total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. The facts sheet prints a pass count for these two kernels only. For copy and asmcopy the same division gives 2 x the number of buffer passes, because the binary counts read plus written bytes (header line of each process in threads120.csv: "copy counts read+write bytes"). facts.json holds that value in the field "passes".
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). "Load at launch" is the 1-minute value read directly before a process starts. The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **pr/ttyAMA-1**: a Linux kernel thread in the process lists. By its name it prints kernel messages to the serial console ttyAMA. This meaning was not checked on CRB.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **GiB**: 2^30 bytes. A "32 GB" module holds 32 GiB.
- **MiB**: 2^20 bytes. The buffer of one thread is 256 MiB.
- **Module list**: the output of the command `dmidecode -t 17`, which prints the hardware table of the firmware. It holds one entry "Memory Device" per memory module: 12 entries in the list saved in the boot of the rerun, and 10 entries in a 10-module boot by the DIMM report.
- **Journal**: the log store of Linux. It keeps the kernel log of earlier boots.
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues).
- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory settings. The saved replies of the settings tool name two of them: "TXREQ Max" and "TXREQ Min" (section 1.5, point 13 of the facts sheet).
- **2 MiB pages**: transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **Governor**: the Linux policy that sets the CPU frequency.
- **rc**: the exit status of a process. 0 means success.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Baseline, like-for-like**: an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.
- **Supporting row, other-binary row**: earlier 8000 MT/s runs that differ in interval length or counter setup (supporting), or that used another runner binary (other binary).
- **Ranges overlap**: two min-to-max ranges share at least one value.
- **n**: the number of measurements that a range comes from. It is written as intervals / processes / sessions / boots (rule V1 point 1). "No session" marks a row that is not part of a session of go.sh.
- **Pool**: the intervals of several rows taken together as one range.
- **Distance of the nearest ends**: for two ranges that do not overlap: the lowest value of the higher range minus the highest value of the lower range.
- **Rules V1 to V4, F1, F2**: the comparison rules in `baselines-and-rules.txt`.
- **FINDINGS.md**: the facts sheet of the investigation of 2026-11-15 into the drop of the read rate.
- **est.**: estimated, not measured directly.

</details>

## Main flow

1. `build_facts.py` imports this module. The import sets the fixed texts and three constants with the names of earlier 8000 MT/s data sets (`BW12`, `BW11`, `BWX`) (lines 9-33).
2. `build_facts.py` calls `render(D)`. `render` calls `analyse(D)` and `register(D)`, and it creates the verdict object `V` and the empty line list `L` (lines 341-357).
3. `analyse` builds the 6 pairs of part A. For each session (1 to 3) and each round (1, 2) it takes the 3 intervals of `bw_old read` and of `bw_new read`, the two medians, their ratio and the drop (lines 288-301).
4. `analyse` builds the pairs of five bwx12 data sets with `pairs`. One pair holds the oldread interval and the asmread interval of the same process and round, with the drop between them. A pair of part C also holds the `read` interval and its drop (lines 303-321).
5. `analyse` defines `pool`. It selects the records of several data sets for one kernel and, when given, one position (lines 323-330).
6. `register` gives every script, raw file and external source a reference number for the file list of section 7 (lines 156-274).
7. `render` reads values that several sections use: the two interval lengths (`secA`, `secX`), the buffer size, the start and end times of go.sh and go2.sh, and the time of the rules file. Guards check that the rules file is older than the run (lines 370-388).
8. `render` puts the drops of the pairs of the five 7200 MT/s data sets into six lists (`dl`, `di`, `df`, `dcr`, `dca`, `dpa`). The drops of the two L-1 pairs enter no list. A guard stops the script unless every drop of the six lists is above 0. A drop above 0 means that the new side is below the old read kernel. A second guard checks for every pair of part A that the highest `bw_new read` interval is below the lowest `bw_old read` interval (lines 390-397).
9. `render` splits the read and asmread intervals of part C into five groups by the kernel that ran directly before (`cgroup`) (lines 399-411).
10. `render` selects the record lists for Q2 and compares 8 pairs of ranges, 7200 MT/s against 8000 MT/s, with `compare` (lines 413-425).
11. `render` compares the load-only kernels of part A, session 1, with the 8000 MT/s range of the same round (list `pa3`) (lines 427-439).
12. It writes the title and the notes under the title (lines 441-457).
13. It writes the heading of section 0. Guards check the patterns that the Short version states. The index `i_short` remembers the place for the Short version. The function `short_version` is defined here and runs later (step 26) (lines 459-564).
14. It writes the word list, the request text and the questions Q1 and Q2 (lines 565-685).
15. Section 1.1: the table of the steps of the run with their times and gaps (lines 687-723).
16. Section 1.2: the table of the state lines, and the proof of the boot, the module count and the memory speed (lines 725-845).
17. Section 1.3: the system load at every launch (lines 847-915).
18. Section 1.4: the list of the integrity checks that `build_facts.py` ran (lines 917-926).
19. Section 1.5: the differences between the procedure of 2026-11-13 and part A, the Linux settings compared between the two boots, and what the saved files show about the firmware settings (lines 928-1150).
20. Section 2: the decisions (a) to (r) (lines 1152-1245).
21. Section 3.1, part A: one table row per process of `read` and `asmread` with the 3 interval rates and their median (24 of the 72 processes of part A), then one row per pair with the ratio and the drop (lines 1247-1304).
22. Section 3.2, parts L and I and the earlier run F72d12: one table row per pair with the oldread rate, the asmread rate and the drop (lines 1306-1351).
23. Section 3.3, part C: one table row per process and round, then one row per group with its range and its drops (lines 1353-1394).
24. Section 3.4: the table of the smallest and the largest drop per part or group, and the verdict text for Q1 (`V['q1']`) (lines 1396-1455).
25. It calls `section4` of facts_text4.py. That function appends sections 4, 5 and 6 to `L`, adds the rows of `V['q2_rows']` (36 of the 42 rows through `q2row`, line 359), and sets the verdict for Q2 [Ref3] [Ref6] (lines 1457-1466).
26. It calls `short_version` and inserts the three sentences and the detail list at the index `i_short`, which is inside section 0 (line 1467).
27. Section 7: the file list. A guard checks that every path in the list `OPENED` of facts_data.py is in the file list. `OPENED` holds the files that were opened with the function `_open`, and the paths that `build_facts.py` added [Ref1] [Ref2] (lines 1469-1484).
28. It joins the lines to one text, checks the date rule with `check_dates`, and returns `V` and the text (lines 1485-1488).
29. `build_facts.py` then writes `V` into facts.json and the text into `S/FACTS.md` [Ref1].

## Behavior a reader must know

- **A module, not a program.** The file has no `main` function. `build_facts.py` imports it and calls `render(D)` once [Ref1]. This file prints nothing and writes no file. `build_facts.py` writes facts.json and `S/FACTS.md` after `render` returns.
- **From a raw row to a printed rate.** Step 1: the benchmark writes the rows of one interval into a csv file. Step 2: facts_data.py reads the rows, and build_facts.py stores the rate of the interval in the field `GBps` of one record [Ref1] [Ref2]. Step 3: this file selects records with `sel` and groups them. It takes the median of the 3 intervals of a part A process, or the lowest and the highest value of a list (a range). A drop of a bwx12 pair is computed from the rates of two single intervals as the records hold them (statistic 2). Step 4: `g` prints the value with 2 decimals. This file computes no mean, and it adds no rates of different processes or sessions.
- **No result csv is read here.** Each rate is already in a record of `D['recs']` when `render` starts. Part A: the field `GBps` is the value of column 7 (`aggregate_GBps`) of one interval row of `threads120.csv`. The benchmark printed that value. The header line of the csv gives its formula: the sum of the bytes of all threads, divided by the longest elapsed time of a thread [Ref7]. The 8000 MT/s data sets A-2 and A-3 come from the files `A1.csv` and `A3.csv` [Ref1]. The interval rows of these files have the same columns. bwx runners: facts_data.py computes `GBps`. For each T row of the interval (one row per thread) it divides `bytes` (column 7) by `elapsed_s` (column 8) and by 1e9. Then it adds the values of all threads [Ref1] [Ref2] [Ref8]. This file adds no bytes and no thread rates. The only files that this file opens are the rules file, `ra.sh` and the DIMM report. It reads a time from the rules file and two numbers from `ra.sh` (the limit of runnable tasks and the sleep time in seconds). Guards check that the rules file and the DIMM report hold certain sentences. It takes no rate from these files.
- **Rows that never become a record.** The row `best` of each part A process is not an interval, and facts_data.py skips it. `A1.csv` and `A3.csv` also hold one row per thread and interval, with the first field `thread`. No record takes its rate from these rows [Ref2]. `A3.csv` holds 12 processes. Only the 3 processes with the tags `onebuf-ms500-1` to `onebuf-ms500-3` become records (data set A-3). `build_facts.py` uses only the header lines of the processes in four more csv files of bw_old and bw_new runs: `one-thread.csv` of the run of 2026-11-13, `A2.csv`, and `A5.csv` and `A6.csv` of the folder `partA-20261113T204939Z`. No record comes from these four files [Ref1]. A folder of an earlier bwx run can hold more csv files than its data set uses. Only the files that a list in `build_facts.py` names become records, for example `a6456.csv` out of the 5 csv files in the folder of L-1 [Ref1]. For L-1 to L-4 these are the files that the rules file lists [Ref5]. From the earlier data sets L-2 to L-4, R0 and R0b only oldread at position 0 and asmread at position 1 become records. From the data sets of the first runner bwx only the kernels oldread, read and asmread become records [Ref1] [Ref2]. The csv files of these data sets also hold more processes than the data sets use. Only the processes whose tag starts with `common-6000-` become records of B7a, B7b, C3a and C3b [Ref1]. These are 8 of the 48 processes of each file `B7.csv` and 4 of the 18 processes of each file `C3.csv` [Ref11]. The I row of a bwx interval holds a second rate in its column `aggregate_GBps`: the bytes of all threads divided by the longest elapsed time of a thread [Ref8]. No record takes its rate from the I row [Ref1] [Ref2]. The integrity check `I-agg` compares that value with the rate from the T rows. It covers the 9 bwx12 files of the rerun only. It passes when every difference is below 0.05 GB/s [Ref1].
- **Rates that this file does not use.** The statistics of this file use `read` and `asmread` of part A, `oldread` and `asmread` of part L, control I and F72d12, and `oldread`, `read` and `asmread` of part C. This file computes no statistic from the rates of write, copy, asmwrite and asmcopy (part A) or of read_nop96, read_nop256 and read_1pl (part L, control I, F72d12 and L-1). No interval is dropped as a warm-up interval. No outlier is removed. Every selected interval enters its median or its range.
- **Statistic 1: the pairs of part A (lines 288 to 301).** There is one pair per session (1, 2, 3) and round (1, 2). That gives 6 pairs. Each side is one process with exactly 3 intervals, and a guard checks this count. The two processes of a pair ran directly one after the other. In round 1 `bw_old read` is process 1 of part A in its session, and `bw_new read` is process 2. In round 2 `bw_new read` is process 23, and `bw_old read` is process 24, the last one [Ref6]. `old_med` and `new_med` are the medians of the 3 rates of `bw_old read` and of `bw_new read`. `ratio` = `new_med / old_med`. `drop` = `(1 - ratio) x 100`, in percent. `ratio_lo` = lowest bw_new interval / highest bw_old interval. `ratio_hi` = highest bw_new interval / lowest bw_old interval. `ao_ratio` and `an_ratio` are the medians of `bw_old asmread` and of `bw_new asmread`, each divided by `old_med`.
- **Statistic 2: the pairs of bwx12 (lines 303 to 321).** For each process (`tag`) of a data set and for each round (0, 1), `pairs` takes the one oldread record and the one record of each named kernel. `drop_<kernel>` = `(1 - GBps of that kernel / GBps of oldread) x 100`, in percent. No median is taken here: a pair uses two single intervals of the same process and round. The named kernel is asmread for `rerun-L`, `control-I`, `F72d12` and `L-1`. The named kernels are read and asmread for `rerun-C`. In a crev process of part C, oldread is the last kernel of each round (position 2). So a pair of a crev process compares read and asmread with an oldread interval that ran after them.
- **Statistic 3: the groups of part C (lines 399 to 411).** `cgroup` selects the part C records with one kernel and one `kernel_before`. The five groups are: read after oldread, read after asmread, asmread after read, asmread as the first interval, asmread after oldread. Each group keeps its records and their drops from statistic 2. A guard checks that the five groups together hold every read and asmread interval of part C. The facts sheet gives no range over all read intervals or over all asmread intervals of part C. `render` computes the range of all read intervals of part C once (`gC`, line 1399). No later line reads it.
- **Statistic 4: the range comparisons for Q2 (lines 413 to 425).** `compare` is called 8 times. Six calls compare oldread and asmread of part L, of control I and of F72d12 with the pool of the data sets L-1 to L-4 (oldread at position 0, asmread at position 1). One call compares `bw_old read` of part A with `bw_old read` of the data sets A-1 to A-3. In part A, in A-1 and in A-2, `bw_old read` of round 1 is the first process of its csv file, and `bw_old read` of round 2 is the last process [Ref6]. A-3 holds 3 processes of `bw_old read`, and other processes of `A3.csv` ran between them [Ref6]. One call compares oldread of part C with the oldread pool. The part C list holds oldread at position 0 (cfwd) and at position 2 (crev). The pool holds oldread at position 0 only. The oldread pool and the asmread pool each hold intervals of two lengths: 6 s in L-1 (2 of the 11 intervals) and 4 s in L-2 to L-4 (9 of the 11 intervals) [Ref6]. Part L, part C, control I and F72d12 hold intervals of 6 s only [Ref6]. Each call returns both min-to-max ranges, the result of the overlap test, the distance of the nearest ends, the wording and the width of the 8000 MT/s range.
- **The overlap test.** Two ranges overlap when `a.lo <= b.hi` and `b.lo <= a.hi` [Ref2]. So two ranges that only touch at one end count as overlapping. `compare` sets the wording to `SAME` when they overlap and to `DIFFERS` when they do not. The distance is positive when the 7200 MT/s range lies above the 8000 MT/s range, negative when it lies below, and 0 when the ranges overlap.
- **Statistic 5: the load-only kernels of part A, session 1 (lines 427 to 439).** For `bw_new read`, `bw_new asmread` and `bw_old asmread`, and for each round, the 3 intervals of session 1 are compared with the range of the data sets A-1 and A-2 of the same round. The result holds the distance in GB/s of each interval that lies above or below that range, and the count of the intervals inside it. The data set A-2 holds no process of `bw_old asmread`. So for that kernel the 8000 MT/s range comes from the 3 intervals of A-1 alone [Ref6]. A-1 has the process order of part A. A-2 ran its 12 processes in another order. For example, `bw_new read` of round 2 follows `bw_old write` in part A and in A-1 (process 23 of 24). In A-2 it follows `bw_new asmread` (process 11 of 12) [Ref6]. facts_text4.py prints the 6 results in section 4.3 of the facts sheet and appends them to `V['q2_rows']` [Ref3].
- **More ranges over several data sets together.** Besides statistics 4 and 5, three lines take the lowest and the highest `GBps` of a list that joins the records of several data sets (`rng`). Line 1138: `bw_old read` of the data sets A-1 and A-2 together (12 intervals of 4 processes), for the text that rule F1 point 5 requires. Line 1451: oldread over part L, control I and F72d12 together (12 intervals of 6 processes), and asmread over the same processes. The bullet after the verdict of section 3.4 prints the distance between the two ends of each of these two ranges. Line 542: the same asmread range, for a detail line of section 0. `short_version` also counts the `bw_old read` intervals of part A that lie below and above the 8000 MT/s range (lines 481 and 482).
- **Verdicts set in this file.** `V['q1']` (line 1433) is the answer text for Q1. Its percent values come from `pcr`. Each call of `pcr` gives the lowest and the highest drop of one list. The lists are the two read groups of part C, `dl`, `dpa`, the three asmread groups of part C, `di` and `df`. The Q1 sentence of the Short version (line 489) quotes the two read groups of part C only. `V['q1_parts']` (line 1426) holds 9 entries, one per part or group, each with the smallest and the largest drop in percent [Ref6]. `V['short_version']` (line 559) holds the three sentences and the detail list of section 0. `V['rule_wordings']` (line 345) holds the three fixed wordings. `q2row` (line 359) appends one comparison row to `V['q2_rows']` per call, and only facts_text4.py calls it. facts_text4.py appends the 6 rows of statistic 5 without `q2row` [Ref3]. facts_text4.py sets `V['q2']`, `V['insufficient_data']`, `V['hypotheses']` and the other entries [Ref3].
- **The answer words are fixed text.** The word "Yes" of `V['q1']` and sentences such as "still below" are written in the templates. They are not chosen by an `if`. Guards before them check that the data show the stated pattern. The file holds 66 calls of `need`. When one fails, `need` raises `SystemExit`, `render` does not return, and `build_facts.py` writes neither facts.json nor FACTS.md [Ref1].
- **A failed integrity check.** Section 1.4 prints `pass` or `FAILED` for each integrity check (line 921). This file has no guard on the result of a check. A guard in `section4` of facts_text4.py stops the script when a check failed [Ref3]. So a facts sheet that was written shows `pass` for every check.
- **Rounding.** Every statistic is computed from the `GBps` values as the records hold them. Rounding happens only where a value is printed or stored in `V`. `g` prints a rate with 2 decimals (0.01 GB/s) and `pc` prints a percent value with 1 decimal, both half up. Their helper `_q` first rounds to 6 decimals, which removes the small errors of binary floating-point numbers. Ratios are printed with `%.3f` and loads with `%.2f`, which use the rounding of Python. In `V`, the drops are rounded with `round(x, 2)` and the distances with `round(x, 3)`. `build_facts.py` rounds every floating-point number of `V` to 3 decimals when it writes facts.json [Ref1]. The part A csv prints `aggregate_GBps` with 2 decimals, so a part A rate has 2 decimals from the start [Ref7].
- **The Short version of section 0 is built after section 6.** The third sentence of the Short version and 4 of its 12 detail lines quote values that `section4` computes. So `render` remembers the index `i_short` (line 474), runs `section4` (line 1464) and then inserts the result of `short_version` at that index (line 1467).
- **Sections of S/FACTS.md that this file writes.** The title with its notes. Section 0 (Short version, the word list, the request, Q1 and Q2). Section 1 (run record, 1.1 to 1.5). Section 2 (decisions). Section 3 (Q1: old against new at 7200 MT/s, 3.1 to 3.4). Section 7 (files). Sections 4, 5 and 6 come from `section4` of facts_text4.py, which appends to the same list `L` [Ref3] [Ref4].
- **Import inside `render`.** facts_text4.py imports helper functions from this file in its first lines [Ref3]. This file imports `section4` inside `render` (line 1458), not at the top. An import at the top of both files makes Python raise an `ImportError` (checked with two test files of the same layout).
- **The pattern `(need(...), value)[1]`.** The lambdas `one` (line 286), `one_len` (line 372) and `one_set` (line 1063) build a tuple of two items and return the second. Python evaluates the first item, the guard, before it returns the value.
- **Global state.** `OTHER_DAY` is a set at module level. `hmd` adds each time of day that it prints for a day other than 2026-11-17. `render` empties the set at its start (line 357). `check_dates` uses it at the end to find a time of another day that is printed without its date.
- **Reference numbers follow the call order.** In `register` a file gets its number at its first `a(...)` call. So the order of these calls fixes the numbers `[RefN]` in the facts sheet.
- **What the guard of the file list covers.** The guard in line 1475 tests the paths in the list `OPENED` of facts_data.py. `_open` of facts_data.py adds each file that it opens to this list, and `build_facts.py` adds some paths itself [Ref1] [Ref2]. stat_bwx.py opens files without `_open`. So it adds no path to the list. For the integrity check `x-bwx`, stat_bwx.py reads every csv file of each folder that the check passes to it [Ref1] [Ref10]. So one run of `build_facts.py` also reads 35 csv files in the folders of earlier bwx runs that the file list does not name. An example is `a0001.csv` in the folder of L-1. No record comes from these 35 files.
- **A result that is not read.** `N['p80']` (line 321) holds the pairs of the 8000 MT/s data set `L-1`. No line of facts_text.py or facts_text4.py reads it. The call still runs the guard of `one` for that data set.

## Call sequence in the whole-chip test

- `build_facts.py:main`: entry point: collects the data, runs the checks, then calls `render`
  - `render` (line 341): returns the verdict object `V` and the text of FACTS.md
    - `analyse` (line 283): builds the pairs for Q1 and the selector `pool`
      - `cell` (line 292): the 3 intervals of one part A process, sorted
        - `facts_data.py:sel`: returns the records that match every condition
      - `need` (line 36): guard: stops the script when a condition is false
      - `med` (line 279): median of the 3 rates of one part A process
      - `pairs` (line 304): bwx12 pairs and drops per process and round, 5 calls
        - `one` (line 286): checks that exactly one record matches and returns it
    - `register` (line 156): numbers every script and raw file for section 7
      - `Refs.add` (line 146): gives a new file the next reference number
    - `one_len` (line 372): the one interval length of a data set, in seconds
    - `facts_data.py:_open`: opens a file and notes its path for the file list
    - `mtime` (line 384): file time of the rules file and of `local.sha`
    - `cgroup` (line 402): records and drops of one part C group, 5 calls
    - `pool` (line 324): the 8000 MT/s pools of oldread and asmread, 4 calls
    - `compare` (line 333): 7200 MT/s range against 8000 MT/s range, 8 calls
      - `facts_data.py:rng`: lowest, highest and median rate, and the counts of a list
      - `facts_data.py:overlap`: true when two ranges share at least one value
      - `facts_data.py:gap`: distance of the nearest ends of two ranges, in GB/s
      - `facts_data.py:width_pct`: width of a range in percent of its lower end
    - `inside` (line 468): true when the 7200 MT/s range lies inside the 8000 MT/s range
    - `Refs.__call__` (line 151): `ref(path)`: the text `[RefN]` of a registered file
    - `hm` (line 64): formats a time as `HH:MM:SS`
    - `table` (line 132): Markdown lines of one table
    - `procs_str` (line 732): process counts per user of one state line, as text
    - `hmd` (line 72): formats a time with its date
    - `g` (line 46): formats a rate with 2 decimals, half up
      - `_q` (line 41): decimal rounding, half up
    - `dur` (line 90): formats seconds as hours, minutes and seconds
    - `inboot` (line 1000): number of the boot that contains a time
    - `facts_data.py:rel`: path as the sheet writes it: `R/...` or `S/...`
    - `one_set` (line 1063): the one reply to a change in a reply file `set.txt`
    - `sp` (line 50): formats a range as `lo to hi`
    - `nn` (line 98): formats the counts of a range as intervals / processes / boots
    - `lgap` (line 1141): seconds between the last two launches of a baseline file
    - `pc` (line 54): formats a percent value with 1 decimal, half up
    - `lrow` (line 1315): one table row of section 3.2 from one pair
    - `cellf` (line 1365): one part C rate with position and kernel before
    - `mm` (line 1367): the two mesh sums of a record as text
    - `cpair` (line 1401): one part C group for the Q1 table of section 3.4
      - `tags` (line 1400): the folder tags of a record list, each once
      - `sess` (line 108): the sessions of a record list as text
    - `pcr` (line 58): lowest and highest drop of a list, as text
    - `facts_text4.py:section4`: appends sections 4, 5, 6 and sets the verdict for Q2
      - `q2row` (line 359): adds one comparison row to `V['q2_rows']`
    - `short_version` (line 477): the three sentences and the detail list of section 0
      - `nns` (line 124): n as intervals / processes / sessions / boots
    - `check_dates` (line 79): finds a time of another day without its date
  - `build_facts.py:write_json`: writes facts.json with the records and `V`

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `need` | 36-38 | Guard. Raises `SystemExit` with a message when the condition is false. Then no output file is written. | - | - |
| `_q` | 41-43 | Rounds a number to the given step, half up, and returns it as text. It rounds to 6 decimals first. | - | - |
| `g` | 46-47 | Formats a rate with 2 decimals (0.01 GB/s), half up. | `_q` | - |
| `sp` | 50-51 | Formats a range as the text `lo to hi`, each end with 2 decimals. | `g` | - |
| `pc` | 54-55 | Formats a percent value with 1 decimal, half up. | `_q` | - |
| `pcr` | 58-61 | Lowest and highest of a list of percent values, as text with the unit. One value when both round to the same text. | `pc` | - |
| `hm` | 64-65 | Formats a time as `HH:MM:SS`. | - | - |
| `hmd` | 72-76 | Formats a time with its date. It notes the time of day in `OTHER_DAY` when the date is not 2026-11-17. | - | - |
| `check_dates` | 79-87 | Returns the sentences and table cells that hold a time of another day without a date. | - | - |
| `dur` | 90-95 | Formats a number of seconds as hours, minutes and seconds. | - | - |
| `nn` | 98-105 | Formats the counts of a range as intervals / processes / boots. Sessions are added on request. Boots can be left out. | - | - |
| `sess` | 108-121 | Names the sessions of rerun records as text. A process without a session (T72C4) counts as an extra process. | - | - |
| `nns` | 124-129 | Formats n of rerun records as intervals / processes / sessions / boots. | `facts_data:rng`, `sess` | - |
| `table` | 132-137 | Returns the Markdown lines of a table from a header list and a list of rows. | - | - |
| `Refs (class)` | 140-153 | The file list of section 7. It maps a path to its reference number and its description. | - | - |
| `__init__ (method of Refs)` | 143-144 | Creates the empty dictionary `d`. Later it maps a path to number and description. | - | - |
| `add (method of Refs)` | 146-149 | Registers a file once. A new file gets the next number. | - | - |
| `__call__ (method of Refs)` | 151-153 | Returns the text `[RefN]` of a registered file. A path that is not registered raises `KeyError`. | - | - |
| `register` | 156-274 | Registers every script, raw file and external source that the sheet cites, in a fixed order. Returns the `Refs` object. | `Refs`, `add` | - |
| `med` | 279-280 | Median of the field `GBps` of a list of records. | - | - |
| `analyse` | 283-330 | Builds the statistics object `N`: the 6 pairs of part A, the bwx12 pairs of five data sets, and the selector `pool`. | `cell`, `need`, `med`, `pairs` | - |
| `one (lambda in analyse)` | 286-286 | Checks that a list holds exactly one record and returns that record. | `need` | - |
| `cell (lambda in analyse)` | 292-293 | The part A records of one session, round, binary and kernel, sorted by interval number. | `facts_data:sel` | - |
| `pairs (in analyse)` | 304-316 | For each process and round of a bwx data set: the oldread record, the record of each named kernel, and the drop against oldread. | `facts_data:sel`, `one` | - |
| `pool (in analyse)` | 324-328 | Selects the records of several data sets for one kernel and, when given, one position. | `facts_data:sel` | - |
| `compare` | 333-336 | Compares a 7200 MT/s record list with an 8000 MT/s list: both ranges, overlap, distance, wording, width of the 8000 MT/s range. | `facts_data:rng`, `facts_data:overlap`, `facts_data:gap`, `facts_data:width_pct` | - |
| `render` | 341-1488 | Main function. Computes the remaining statistics, writes every line of FACTS.md into `L`, fills `V`, and returns `V` and the text. | `analyse`, `register`, `one_len`, `need`, `facts_data:_open`, `mtime`, `facts_data:sel`, `cgroup`, `pool`, `compare`, `facts_data:rng`, `inside`, `Refs.__call__`, `hm`, `table`, `procs_str`, `hmd`, `g`, `dur`, `facts_data:clock`, `facts_data:folder_date`, `inboot`, `facts_data:rel`, `one_set`, `sp`, `nn`, `lgap`, `med`, `pc`, `lrow`, `cellf`, `mm`, `cpair`, `pcr`, `tags`, `facts_text4:section4`, `short_version`, `check_dates` | - |
| `q2row (in render)` | 359-368 | Appends one comparison row to `V['q2_rows']`: both ranges, counts, overlap, distance, and the wording when `decides` is true. Only facts_text4.py calls it. | - | - |
| `one_len (lambda in render)` | 372-373 | Checks that a data set has one interval length (`min_ms`) and returns it as text in seconds. | `need`, `facts_data:sel` | - |
| `mtime (lambda in render)` | 384-384 | File time of a path as UTC date and time, in whole seconds. | - | - |
| `cgroup (in render)` | 402-406 | The part C records with one kernel and one kernel before it, and the drop of each record against oldread. | `facts_data:sel`, `need` | - |
| `inside (lambda in render)` | 468-468 | True when the 7200 MT/s range of a comparison lies fully inside its 8000 MT/s range. | - | - |
| `short_version (in render)` | 477-564 | Builds the three sentences and the detail list of section 0 from the comparisons and from values that `section4` stored. | `need`, `inside`, `nns`, `nn`, `pcr`, `pc`, `sp`, `g`, `hm`, `facts_data:rng` | - |
| `procs_str (in render)` | 732-735 | Formats the process counts per user of one state line. | - | - |
| `inboot (lambda in render)` | 1000-1000 | Number of the boot, from the boot table of the DIMM report, that contains a given time. | - | - |
| `one_set (lambda in render)` | 1063-1063 | Checks that a settings reply file holds one reply with `modified: true` and returns it. | `need` | - |
| `lgap (lambda in render)` | 1141-1141 | Seconds between the launches of the last two processes of a part A baseline file. | `facts_data:clock` | - |
| `lrow (in render)` | 1315-1320 | One table row of section 3.2 from one bwx12 pair: rates, mesh sums, drop, source lines. | `g`, `pc`, `Refs.__call__` | - |
| `cellf (lambda in render)` | 1365-1366 | Formats one part C rate with its position and the kernel before it. | `g` | - |
| `mm (lambda in render)` | 1367-1367 | Formats the two mesh sums of a record as `m0 + m1`. | `g` | - |
| `tags (lambda in render)` | 1400-1400 | The folder tags of a record list, each once, joined with commas. | - | - |
| `cpair (lambda in render)` | 1401-1402 | One part C entry for the Q1 table: part, group, label, drops, and the text for n. | `facts_data:rng`, `tags`, `sess` | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Module comment: what <code>render</code> returns</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  #!/usr/bin/env python3
   2  """facts_text.py - text and tables of FACTS.md, and the verdict object of facts.json.
   3
   4  Used by build_facts.py: render(D) returns (verdicts, text of FACTS.md).
   5  The templates below hold words only. Every number is formatted from the data that build_facts.py collected.
   6  Sentences that depend on the pattern of the data are guarded by `need(...)`: the script stops when the data
   7  do not show the pattern that the sentence states.
   8  """</pre></td><td valign="top"><code>build_facts.py</code> calls <code>render(D)</code> and gets two results: the verdict object and the text of FACTS.md [Ref1]. The comment says that the fixed texts of this file (the templates) hold words only, and that every number is formatted from the data that <code>build_facts.py</code> collected. It also says that each sentence that states a pattern of the data has a guard, a call of <code>need</code> (line 36). The script stops when the data do not show that pattern.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   9  import os
  10  import re
  11  import statistics
  12  from decimal import Decimal, ROUND_HALF_UP
  13
  14  import facts_data as fd
  15  from facts_data import R, S, rel, sel, rng, overlap, gap, width_pct
  16</pre></td><td valign="top">Imports.<ul><li><code>statistics</code> gives the median. <code>Decimal</code> and <code>ROUND_HALF_UP</code> give the decimal rounding of <code>_q</code> (line 41).</li><li><code>facts_data</code>, short name <code>fd</code>, is the module with the parsers and the range functions [Ref2].</li><li><code>R</code>, <code>S</code>: the results folder and the folder of this script.</li><li><code>sel(records, field=value, ...)</code> returns the records that match every condition. A condition value may be one value, a set of allowed values, or a function.</li><li><code>rng(records)</code> returns a range: the lowest, the highest and the median <code>GBps</code>, and the counts of intervals, processes, sessions and boots.</li><li><code>overlap</code>, <code>gap</code>, <code>width_pct</code>: the three range functions that <code>compare</code> uses (line 333). <code>rel</code> shortens a path to <code>R/...</code> or <code>S/...</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Constants: lists of earlier data sets</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  17  W15, K13 = fd.W15, fd.K13
  18  BW12 = ('L-1', 'L-2', 'L-3', 'L-4')            # baseline row and supporting rows of runner bwx12
  19  BW11 = ('R0', 'R0b')                           # rows of the other binary bwx11
  20  BWX = ('B7a', 'B7b', 'C3a', 'C3b')             # rows of the first runner bwx</pre></td><td valign="top"><code>W15</code> and <code>K13</code> are two folder paths from facts_data.py: the scratch folders of 2026-11-15 and of 2026-11-13. The three lists name earlier data sets, grouped by the runner program:<ul><li><code>BW12</code>: <code>L-1</code> to <code>L-4</code>, runs of bwx12. <code>L-1</code> is the baseline, and the other three are supporting rows.</li><li><code>BW11</code>: <code>R0</code> and <code>R0b</code>, runs of the older runner bwx11.</li><li><code>BWX</code>: <code>B7a</code>, <code>B7b</code>, <code>C3a</code>, <code>C3b</code>, runs of the first runner bwx.</li></ul></td></tr>
<tr><td colspan="2"><b>Constants: fixed texts</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  21  DIFFERS = 'differs between the 8000 MT/s boot and the 7200 MT/s boot'
  22  SAME = 'no difference seen'
  23  NO_READ = 'Insufficient data: no 8000 MT/s run of kernel read with bwx12'
  24  ADDED = 'added after the first numbers were seen'
  25  NOT_PLAN = 'not part of the plan fixed before the run'</pre></td><td valign="top">Fixed result texts.<ul><li><code>DIFFERS</code>, <code>SAME</code>: the two wordings that <code>compare</code> (line 333) can give.</li><li><code>NO_READ</code>: the text for a comparison that the data cannot give. It says that no 8000 MT/s run of the kernel <code>read</code> with bwx12 exists.</li><li><code>ADDED</code>, <code>NOT_PLAN</code>: two labels. In this file both are attached to control I.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  26  H1_MEAS = ('The like.spec line, run in turn from an idle start and directly after part A, at least 3 times each, in '
  27             'one boot, would resolve it (the measurement of hypothesis H1 in section 6).')
  28  FIRST = 'none (first interval of the process)'
  29  # rule V4, part L: "asmread stands in for the new read kernel (same loop: 8 ldp q per 256 B). Say so in the row label."
  30  STANDIN = 'asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B)'
  31  # Rules F2 points 2 and 3 against rules V1 point 2, V2 point 4 and V4 (part C list): see decision (r) in section 2.
  32  F2_NOTE = ('This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 '
  33             'and 3 would present part C at 7200 MT/s only (decision (r) in section 2).')
  34
  35</pre></td><td valign="top"><ul><li><code>H1_MEAS</code>: the sentence that names the measurement which would resolve hypothesis H1 of section 6.</li><li><code>FIRST</code>: the value of the field <code>kernel_before</code> of the first interval of a bwx process. <code>render</code> selects with it (line 408). <code>build_facts.py</code> writes the same text into the records as its own literal [Ref1].</li><li><code>STANDIN</code>: a text for the row labels of part L. It says that asmread is used in place of the new read kernel. The comment above it quotes rule V4.</li><li><code>F2_NOTE</code>: a note on the rules that the comparison of part C with 8000 MT/s follows. This file does not use it. facts_text4.py imports it [Ref3].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>need</code>: the guard</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  36  def need(cond, what):
  37      if not cond:
  38          raise SystemExit('facts_text.py: the data do not show the pattern of a sentence: ' + what)
  39
  40</pre></td><td valign="top">When <code>cond</code> is false, <code>need</code> raises <code>SystemExit</code> with a message that ends with the text <code>what</code>. Then <code>render</code> does not return. <code>build_facts.py</code> writes facts.json and FACTS.md only after <code>render</code> has returned [Ref1]. So a failed guard leaves both files as they were.</td></tr>
<tr><td colspan="2"><b>Function <code>_q</code>: decimal rounding, half up</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  41  def _q(x, step):
  42      """Decimal rounding, half up. Rounding to 6 places first removes binary floating-point noise."""
  43      return str(Decimal(repr(round(x, 6))).quantize(Decimal(step), rounding=ROUND_HALF_UP))
  44
  45</pre></td><td valign="top"><code>_q(x, step)</code> rounds <code>x</code> to the number of decimals of <code>step</code> and returns the result as text. This file calls it with the steps <code>'0.01'</code> and <code>'0.1'</code>.<ul><li><code>round(x, 6)</code> rounds to 6 decimals, and <code>repr</code> gives the shortest decimal text of that number. This removes the small errors of binary floating-point numbers, for example 0.19999999999999998 in place of 0.2.</li><li><code>Decimal(...)</code> reads the text as an exact decimal number.</li><li><code>quantize</code> rounds it to the decimals of the step. A value exactly in the middle between two steps goes to the step that is farther from 0. For a positive value that is the higher step.</li><li>Example: <code>_q(0.125, '0.01')</code> returns <code>0.13</code>. The Python format <code>%.2f</code> returns <code>0.12</code> for the same value.</li></ul></td></tr>
<tr><td colspan="2"><b>Functions <code>g</code>, <code>sp</code>, <code>pc</code>: rates, ranges, percent values as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  46  def g(x):
  47      return _q(x, '0.01')
  48
  49
  50  def sp(a):
  51      return '%s to %s' % (g(a['lo']), g(a['hi']))
  52
  53
  54  def pc(x):
  55      return _q(x, '0.1')
  56
  57</pre></td><td valign="top"><ul><li><code>g(x)</code>: a rate as text with 2 decimals (step 0.01 GB/s).</li><li><code>sp(a)</code>: a range as the text <code>lo to hi</code>. Both ends go through <code>g</code>.</li><li><code>pc(x)</code>: a percent value as text with 1 decimal (step 0.1).</li><li>These functions only make the printed text. The statistics of <code>analyse</code> and <code>compare</code> use the values before rounding.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pcr</code>: lowest and highest percent value</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  58  def pcr(ds):
  59      """Lowest and highest of a list of percent values, as text with the unit."""
  60      lo, hi = pc(min(ds)), pc(max(ds))
  61      return ('%s %%' % lo) if lo == hi else '%s %% to %s %%' % (lo, hi)
  62
  63</pre></td><td valign="top"><code>pcr(ds)</code> takes a list of percent values, for example the drops of all pairs of one part. It formats the lowest and the highest value with <code>pc</code>. When both texts are equal, it returns one value, for example <code>35.4 %</code> for the 2 drops of F72d12. Otherwise it returns both, for example <code>30.5 % to 31.2 %</code> for the 4 drops of the part C group <code>read after oldread</code> [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>hm</code>: time of day</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  64  def hm(t):
  65      return t.strftime('%H:%M:%S')
  66
  67</pre></td><td valign="top">Formats a time as <code>HH:MM:SS</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>hmd</code>: time with its date</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  68  RERUN_DAY = '2026-11-17'      # a time without a date is on this day (first lines of the sheet)
  69  OTHER_DAY = set()             # every time of day that the sheet prints for another day
  70
  71
  72  def hmd(t):
  73      """Date and time. Used for every time that is not on the day of the rerun, and where the date helps."""
  74      if t.strftime('%Y-%m-%d') != RERUN_DAY:
  75          OTHER_DAY.add(t.strftime('%H:%M:%S'))
  76      return t.strftime('%Y-%m-%d %H:%M:%S')
  77
  78</pre></td><td valign="top"><ul><li><code>RERUN_DAY</code>: the day of the rerun. In the sheet, a time without a date is on this day.</li><li><code>hmd(t)</code> returns date and time as <code>YYYY-MM-DD HH:MM:SS</code>. When the date is not <code>RERUN_DAY</code>, it also adds the time of day to the set <code>OTHER_DAY</code>.</li><li><code>OTHER_DAY</code> is a global variable of the module. <code>render</code> empties it at its start (line 357), and <code>check_dates</code> reads it.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>check_dates</code>: find a time without its date</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  79  def check_dates(text):
  80      """A time of another day must carry its date in the same sentence or table cell (rule in the first lines of
  81      the sheet). Returns the pieces of text that break the rule."""
  82      bad = []
  83      for line in text.split('\n'):
  84          for piece in re.split(r'\.\s+|\s\|\s', line):
  85              if any(t in piece for t in OTHER_DAY) and not re.search(r'\b2026-\d\d-\d\d\b', piece):
  86                  bad.append(piece)
  87      return bad
  88
  89</pre></td><td valign="top">It cuts every line of the finished sheet text into pieces. A piece ends at the end of a sentence (a period followed by white space) or at a table cell border (a <code>|</code> with one white-space character on each side). The function returns each piece that holds a time of day from <code>OTHER_DAY</code> and no date of the form <code>2026-MM-DD</code>. <code>render</code> calls it on the finished text (line 1486), and a guard stops the script when a piece is returned.</td></tr>
<tr><td colspan="2"><b>Function <code>dur</code>: seconds as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  90  def dur(sec):
  91      sec = int(round(sec))
  92      h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
  93      if h:
  94          return '%d h %d min %d s' % (h, m, s)
  95      return ('%d min %d s' % (m, s)) if m else '%d s' % s
  96
  97</pre></td><td valign="top">Rounds a number of seconds to whole seconds and formats it. Examples: <code>5 s</code>, <code>1 min 5 s</code>, <code>1 h 2 min 5 s</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>nn</code>: the counts of a range as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  98  def nn(a, sessions=False, boots=True):
  99      """n as intervals / processes (/ sessions) / boots."""
 100      t = '%d intervals / %d process%s' % (a['n'], a['procs'], '' if a['procs'] == 1 else 'es')
 101      if sessions:
 102          t += ' / %d sessions' % a['sessions']
 103      if boots:
 104          t += ' / %d boot%s' % (a['boots'], '' if a['boots'] == 1 else 's')
 105      return t
 106
 107</pre></td><td valign="top"><code>a</code> is a range (a result of <code>rng</code>). The result has the form <code>11 intervals / 7 processes / 1 boot</code>. With <code>sessions=True</code> the number of sessions is added before the boots. With <code>boots=False</code> the number of boots is left out.</td></tr>
<tr><td colspan="2"><b>Function <code>sess</code>: the sessions of a record list as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 108  def sess(rs):
 109      """Sessions of a list of rerun records, as text. T72C4 ran after the three sessions: it counts as an extra process."""
 110      rr = [r for r in rs if r['dataset'].startswith('rerun-')]      # control I and F72d12 belong to no session
 111      ss = sorted({r['session'] for r in rr if r['session'] is not None})
 112      extra = len({r['proc_key'] for r in rr if r['session'] is None})
 113      if len(ss) &gt; 2 and ss == list(range(ss[0], ss[-1] + 1)):
 114          t = '%d sessions' % len(ss)
 115      elif ss:
 116          t = 'session%s %s' % ('' if len(ss) == 1 else 's', ' and '.join(map(str, ss)))
 117      else:
 118          t = 'no session'
 119      if extra:
 120          t += ' and %d extra process%s' % (extra, '' if extra == 1 else 'es')
 121      return t
 122
 123</pre></td><td valign="top"><ul><li><code>rr</code>: only the records whose data set name starts with <code>rerun-</code>. The records of control I and of F72d12 are left out. So a list of such records gets the text <code>no session</code>.</li><li><code>ss</code>: the session numbers of <code>rr</code>, sorted, each once.</li><li><code>extra</code>: the number of processes in <code>rr</code> that have no session number. In the rerun that is T72C4, the fourth process of part C [Ref2].</li><li>Three or more session numbers with no missing number between them give a count, for example <code>3 sessions</code>. Otherwise the numbers are listed, for example <code>sessions 1 and 3</code>.</li><li>When <code>extra</code> is above 0, a text such as <code> and 1 extra process</code> is added.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>nns</code>: full count text of rerun records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 124  def nns(rs):
 125      """n of rerun records as intervals / processes / sessions / boots (rule V1 point 1)."""
 126      a = rng(rs)
 127      return '%d interval%s / %d process%s / %s / %d boot%s' % (
 128          a['n'], '' if a['n'] == 1 else 's', a['procs'], '' if a['procs'] == 1 else 'es', sess(rs), a['boots'],
 129          '' if a['boots'] == 1 else 's')
 130
 131</pre></td><td valign="top">Builds the text for n from a record list: intervals / processes / the text of <code>sess</code> / boots. The counts come from <code>rng(rs)</code>. Example: the 6 oldread records of part L give <code>6 intervals / 3 processes / 3 sessions / 1 boot</code> [Ref4].</td></tr>
<tr><td colspan="2"><b>Function <code>table</code>: the lines of one Markdown table</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 132  def table(head, rows):
 133      out = ['| ' + ' | '.join(head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
 134      for r in rows:
 135          out.append('| ' + ' | '.join(str(c) for c in r) + ' |')
 136      out.append('')
 137      return out
 138
 139</pre></td><td valign="top">Returns the lines of one table in Markdown, the plain-text format of FACTS.md. The lines are: the header line, the separator line, one line per row, and one empty line. The cells of a line stand between <code>|</code> characters.</td></tr>
<tr><td colspan="2"><b>Class <code>Refs</code>: the numbered file list of section 7</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 140  class Refs:
 141      """The file list of section 7. A file gets its number when it is registered."""
 142
 143      def __init__(self):
 144          self.d = {}
 145
 146      def add(self, path, desc):
 147          key = path if path.startswith('ext:') else os.path.abspath(path)
 148          if key not in self.d:
 149              self.d[key] = [len(self.d) + 1, desc]
 150
 151      def __call__(self, path):
 152          key = path if path.startswith('ext:') else os.path.abspath(path)
 153          return '[Ref%d]' % self.d[key][0]
 154
 155</pre></td><td valign="top"><ul><li><code>d</code> maps a key to a list of two items: the reference number and the description.</li><li><code>add(path, desc)</code>: the key is the absolute path. A name that starts with <code>ext:</code> marks an external source, and it is kept unchanged. A new key gets the next number, counted from 1. A key that is already in <code>d</code> is not changed.</li><li><code>__call__</code>: the call <code>ref(path)</code> returns the text <code>[RefN]</code> of a registered path. A path that was not registered raises <code>KeyError</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>register</code>: number every file that the sheet cites</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 156  def register(D):
 157      ref = Refs()
 158      a = ref.add</pre></td><td valign="top"><ul><li><code>ref</code>: a new, empty object of the class <code>Refs</code>.</li><li><code>a</code>: a short name for <code>ref.add</code>. Each call <code>a(path, description)</code> below registers one file.</li><li>A file gets its number at its first <code>a</code> call. So the order of the calls fixes the numbers <code>[RefN]</code> in the facts sheet.</li><li>The rows below only name the files of each block.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 159      a(os.path.join(S, 'build_facts.py'), 'script: builds this sheet and facts.json (records, integrity checks)')
 160      a(os.path.join(S, 'facts_data.py'), 'script: parsers of the raw files, range and overlap functions')
 161      a(os.path.join(S, 'facts_text.py'), 'script: text, tables, statistics and verdicts of sections 0 to 3 and 7')
 162      a(os.path.join(S, 'facts_text4.py'), 'script: text, tables, statistics and verdicts of sections 4 to 6')
 163      a(os.path.join(S, 'stat_k120.py'), 'existing tool: statistics of a threads120.csv, used here as a cross-check')
 164      a(os.path.join(S, 'stat_bwx.py'), 'existing tool: statistics of bwx csv files, used here as a cross-check')
 165      a(os.path.join(S, 'baselines-and-rules.txt'), 'the fixed list of 8000 MT/s baselines and the comparison rules '
 166        '(V1 to V4, F1, F2), written before the run')
 167      a(os.path.join(S, 'review-w1.json'), 'record of the review that produced the rules (findings F1 and F9 list the '
 168        'differences to the 2026-11-13 procedure). Read by the author, not by the script')</pre></td><td valign="top">Eight entries.<ul><li>The four scripts that build the sheet.</li><li>The two existing statistics tools <code>stat_k120.py</code> and <code>stat_bwx.py</code>, used as a cross-check.</li><li>The rules file.</li><li>The record of the review that produced the rules.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 169      a(os.path.join(S, 'go.sh'), 'driver script of the rerun: three sessions of parts A, L, C and a fourth C process')
 170      a(os.path.join(S, 'ra.sh'), 'script of part A: the 120-thread part of run_kernels.sh with the binaries of 2026-11-13')
 171      a(os.path.join(S, 'go2.sh'), 'script of control I: the part L line twice, each time from an idle machine')
 172      a(os.path.join(S, 'like.spec'), 'argument line of parts L and I for rx.sh (tag a6456)')
 173      a(os.path.join(S, 'cfwd.spec'), 'argument line of part C, order oldread, read, asmread')
 174      a(os.path.join(S, 'crev.spec'), 'argument line of part C, order asmread, read, oldread')
 175      a(os.path.join(S, 'local.sha'), 'sha256 list of go.sh, ra.sh and the spec files, written at launch')
 176      a(os.path.join(S, 'go2.sha'), 'sha256 of go2.sh, written at launch')
 177      a(os.path.join(S, 'base8000', 'partA-A1', 'threads120.csv'), 'copy of A1.csv with converted header lines, '
 178        'used only for the cross-check with stat_k120.py')
 179      a(os.path.join(S, 'base8000', 'partA-A3-onebuf500', 'threads120.csv'), 'copy of the three onebuf-ms500 processes '
 180        'of A3.csv with converted header lines, used only for the cross-check')</pre></td><td valign="top">The scripts and inputs of the run: <code>go.sh</code>, <code>ra.sh</code>, <code>go2.sh</code>, the three spec files, and the two sha256 files <code>local.sha</code> and <code>go2.sha</code>, which were written at launch. Then two copies of 8000 MT/s part A files with converted header lines. Their descriptions say that they are used only for the cross-check with <code>stat_k120.py</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 181      a(os.path.join(W15, 'rx.sh'), 'runner script of bwx12 processes (parts L, C, I). It writes env.txt, launches.txt and '
 182        'stderr.txt. Read by the author. Check %d of section 1.4 compares its sha256 with the value that go.sh and '
 183        'go2.sh test on CRB'
 184        % ([c['key'] for c in D['checks']].index('sha-rx') + 1))
 185      a(os.path.join(W15, 'r0.sh'), 'run script of row R0. It holds the sha256 of bwx11 (line %d)' % D['rx']['R0']['env']['sha_line'])
 186      a(os.path.join(W15, 'FINDINGS.md'), 'facts sheet of the investigation of 2026-11-15 (sections "The question", '
 187        'F1, F2). Read by the author')
 188      a(os.path.join(K13, 'run_kernels.sh'), 'the run script of 2026-11-13 ("whole chip test"). Read by the author. '
 189        'Check %d of section 1.4 compares its function one() with ra.sh'
 190        % ([c['key'] for c in D['checks']].index('A-args') + 1))
 191      a(D['logs']['go']['path'], 'log of go.sh: Linux command line, governor, huge page setting, 12 state lines')
 192      a(D['logs']['go2']['path'], 'log of go2.sh: 6 state lines')</pre></td><td valign="top">Files in the folders of the earlier work, and the two logs.<ul><li><code>rx.sh</code>, <code>r0.sh</code> and <code>FINDINGS.md</code> in the folder <code>W15</code>. The rerun also used <code>rx.sh</code>. It is the runner script of parts L and C and of control I.</li><li><code>run_kernels.sh</code> in the folder <code>K13</code>.</li><li>The log of go.sh and the log of go2.sh.</li><li>Two descriptions quote the number of an integrity check (a check of the raw files and the scripts that <code>build_facts.py</code> ran). The code finds that number as the index of the check key (<code>sha-rx</code>, <code>A-args</code>) in the list <code>D['checks']</code>, plus 1. Python counts an index from 0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 193      for x in D['A']:
 194          a(x['csv'], 'part A, session %d: 24 processes, 72 interval rows' % x['session'])
 195          a(x['probe']['path'], 'part A, session %d: boot id, MemTotal, load, sha256 of bw_old, bw_new, ra.sh' % x['session'])
 196      names = dict(L='part L', C='part C', I='control I')
 197      for x in D['X']:
 198          what = '%s, %s' % (names[x['part']], x['tag'])
 199          a(x['csv'], what + ': rows per interval (I), per thread (T), page state (P), counters (C)')
 200          a(os.path.join(x['folder'], 'env.txt'), what + ': start time, Linux release, load, busiest processes, sha256 of bwx12')
 201          a(os.path.join(x['folder'], 'launches.txt'), what + ': launch line with load and arguments, rc line')
 202          a(os.path.join(x['folder'], 'stderr.txt'), what + ': error output of bwx12')</pre></td><td valign="top">The raw files of the rerun.<ul><li>For each of the 3 part A folders: <code>threads120.csv</code> and <code>probe.txt</code>.</li><li>For each of the 9 bwx12 folders (3 of part L, 4 of part C, 2 of control I): the csv file, <code>env.txt</code>, <code>launches.txt</code> and <code>stderr.txt</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 203      b = D['base']
 204      a(os.path.join(b['A-1']['folder'], 'threads120.csv'), 'row A-1: the original whole-chip test of 2026-11-13, 24 processes')
 205      a(D['probe13']['path'], 'row A-1: sha256 of bw_old and bw_new, times of the 2026-11-13 run')
 206      a(D['probe13']['one_path'], 'one-thread part of the 2026-11-13 run (only its process count and times are used)')
 207      a(os.path.join(b['A-2']['folder'], 'A1.csv'), 'row A-2: 12 processes of 2026-11-13 20:50 UTC')
 208      a(os.path.join(b['A-3']['folder'], 'A3.csv'), 'row A-3: tags onebuf-ms500-1, -2, -3 (bw_old read)')
 209      a(os.path.join(b['A-2']['folder'], 'env.txt'), 'rows A-2, A-3: sha256 of bw_old and bw_new')</pre></td><td valign="top">The 8000 MT/s files of part A. For the data set <code>A-1</code>: <code>threads120.csv</code> of the test of 2026-11-13, its <code>probe.txt</code> and the csv of its one-thread part. For <code>A-2</code> and <code>A-3</code>: the files <code>A1.csv</code> and <code>A3.csv</code>, and the <code>env.txt</code> of their folder.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 210      for name, v in D['rx'].items():
 211          for t in v['secs']:
 212              a(os.path.join(v['folder'], t + '.csv'), 'row %s: bwx csv of process %s' % (name, t))
 213          if v['env']['has_binary_line']:
 214              a(os.path.join(v['folder'], 'env.txt'), 'row %s: start time, load, process list, sha256 of the binary' % name)
 215          else:
 216              a(os.path.join(v['folder'], 'env.txt'), 'row %s: start time, load, process list (%d lines, no sha256: the '
 217                'sha256 of %s is in r0.sh)' % (name, v['env']['n_lines'], fd.SHA_NAMES[v['env']['sha'][:8]]))
 218          a(os.path.join(v['folder'], 'launches.txt'), 'row %s: launch lines with load and arguments, rc lines' % name)
 219          a(os.path.join(v['folder'], 'stderr.txt'), 'row %s: error output' % name)
 220      for name, v in D['step'].items():
 221          same = [(n, x['prefix']) for n, x in D['step'].items() if (x['folder'], x['file']) == (v['folder'], v['file'])]
 222          a(os.path.join(v['folder'], v['file']), 'row%s %s: csv of runner bwx, processes with tag %s'
 223            % ('' if len(same) == 1 else 's', ' and '.join(n for n, _ in same), ' and '.join(x + '*' for _, x in same)))
 224          a(os.path.join(v['folder'], 'env.txt'), 'row%s %s: sha256 of runner bwx'
 225            % ('' if len(same) == 1 else 's', ' and '.join(n for n, _ in same)))</pre></td><td valign="top">The files of the earlier bwx runs.<ul><li>For each data set in <code>D['rx']</code> (runs that <code>rx.sh</code> or <code>r0.sh</code> started): the csv file of each process that <code>build_facts.py</code> read, <code>env.txt</code>, <code>launches.txt</code> and <code>stderr.txt</code>. A folder can hold more csv files, and these get no entry. When <code>env.txt</code> holds no sha256 line of the binary, the description says that the sha256 is in <code>r0.sh</code>.</li><li>For each data set in <code>D['step']</code> (runs of the first runner bwx): the csv file and <code>env.txt</code>. When several data sets use the same csv file, <code>same</code> lists them, and the description names all of them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 226      t = D['try6']
 227      a(t['path'], 'record of boot %s: 12 modules, 12 x "Configured Memory Speed: 7200 MT/s", MemTotal' % t['boot'][:8])
 228      a(t['gaps_path'], 'first and last kernel log time of the boots of the 7200 MT/s reboot test (row 0 is the boot of '
 229        'the rerun), the field hwerr of row 0, and the time line and the process list after the rows (lines %d to %d)'
 230        % (t['gaps_uptime_line'], t['gaps_top'][-1][3]))
 231      a(t['boots_path'], 'boot list of the journal: row 0 holds the boot id of try6.txt, which links gaps.txt to this boot')
 232      a(fd.DIMM_REPORT, 'DIMM report: boot history with module counts (section 3), change to 7200 MT/s (section 6.3)')
 233      a(D['probe13']['h5'], 'saved journal of the boot of 2026-11-09: Linux start, module count line, error records')
 234      a(D['probe13']['k5'], 'saved kernel log of the same boot: its last line and the line "Memory: ... available" '
 235        '(line %d)' % D['mod']['k-5']['line'])
 236      qt = fd.dt.datetime.utcfromtimestamp(os.path.getmtime(D['probe13']['q_path']))
 237      a(D['probe13']['q_path'], 'firmware settings list (file time %s UTC): the entry counts and the settings '
 238        '"DIMM Frequency", "TXREQ Max" and "TXREQ Min"' % qt.strftime('%Y-%m-%d %H:%M'))
 239      a('ext:cpufreq', 'external source: Linux kernel documentation, Documentation/admin-guide/pm/cpufreq.rst '
 240        '(scaling_cur_freq is given in kHz)')
 241      a('ext:proc5', 'external source: Linux manual page proc(5), entry /proc/loadavg (meaning of the load average '
 242        'fields)')</pre></td><td valign="top">Records of the machine state.<ul><li><code>try6.txt</code>, the file with the Linux kernel log times of the boots, and the boot list of the journal.</li><li>The DIMM report.</li><li>The saved journal and the saved Linux kernel log of the boot of 2026-11-09.</li><li>A firmware settings list. Its description quotes the file time.</li><li>Two external sources, named with <code>ext:</code>: a text of the Linux kernel documentation and the manual page proc(5).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 243      # files and sources added with the corrections of the review (numbered after the earlier entries)
 244      p13 = D['probe13']
 245      a(p13['a2_csv2'], 'second file of the run partA-20261113T205055Z: only the launch time of its first process is used '
 246        '(end of the time window of row A-2)')
 247      a(p13['pre']['when_path'], 'settings saved in the 2026-11-09 boot before the firmware test: time of the save')
 248      a(p13['pre']['cmdline_path'], 'same save: Linux kernel command line')
 249      a(p13['pre']['gov_path'], 'same save: two lines, "%s" and "%s" (the file does not name them)' % tuple(p13['pre']['gov']))
 250      a(p13['pre']['thp_path'], 'same save: transparent_hugepage/enabled')
 251      a('ext:ps1', 'external source: manual page ps(1) of procps-ng, entry "%cpu" (alias pcpu): the CPU time used, '
 252        'divided by the time the process has been running. The ps version on CRB was not checked (no ssh in this task)')</pre></td><td valign="top">Files and sources that were added with the corrections of the review. The comment says that they are numbered after the earlier entries.<ul><li>The second csv of the run folder of <code>A-2</code>.</li><li>Four files of a save of Linux settings in the boot of 2026-11-09.</li><li>The manual page ps(1), as an external source.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 253      # files added with the corrections of verification round 3 (numbered after the earlier entries)
 254      ap = D['a2pre']
 255      a(ap['env_path'], 'run folder of 2026-11-13 20:49 UTC that ended 8 s before the first process of row A-2: start '
 256        'line and end line')
 257      a(ap['files']['A5.csv']['path'], 'same folder: %d one-thread processes (header lines only)' % ap['files']['A5.csv']['n'])
 258      a(ap['files']['A6.csv']['path'], 'same folder: %d one-thread processes (header lines only)' % ap['files']['A6.csv']['n'])
 259      a(ap['launches_path'], 'same folder: one line per process')
 260      md = D['mod']
 261      a(md['h1'], 'saved journal of the 10-module boot of 2026-11-17 04:17 UTC: its first two lines')
 262      a(md['k-1']['path'], 'saved kernel log of the same 10-module boot: the line "Memory: ... available"')
 263      a(md['dmi']['path'], 'module list (output of dmidecode, type 17) saved in the boot of the rerun')
 264      fw = D['fw']
 265      a(fw['sets']['x1']['path'], 'reply of the firmware settings tool: change of "TXREQ Min" for another test')
 266      a(fw['sets']['x2']['path'], 'reply of the firmware settings tool: change of "TXREQ Max" for another test')
 267      a(fw['sets']['revert']['path'], 'replies of the firmware settings tool: both TXREQ settings set back and read back')
 268      a(fw['lists']['revert']['path'], 'firmware settings list saved after the set-back (file time %s UTC)'
 269        % fw['lists']['revert']['mtime'].strftime('%Y-%m-%d %H:%M:%S'))
 270      a(fw['lists']['x1']['path'], 'firmware settings list saved after the first change (file time %s UTC)'
 271        % fw['lists']['x1']['mtime'].strftime('%Y-%m-%d %H:%M:%S'))
 272      a(fw['sets']['dimm']['path'], 'reply of the firmware settings tool: "DIMM Frequency" set to 7200 MT/s')
 273      a(fw['final']['path'], 'last reading of the memory speed setting in the boot of the rerun (one line)')
 274      return ref
 275
 276</pre></td><td valign="top">Files that were added with the corrections of verification round 3.<ul><li>Four files of the run folder that ended 8 s before the first process of <code>A-2</code>.</li><li>The saved journal and the saved Linux kernel log of a 10-module boot.</li><li>The module list of the boot of the rerun.</li><li>The replies and the lists of the firmware settings tool, and the last reading of the memory speed setting.</li><li>The function returns <code>ref</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>med</code>: median rate of a record list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 277  # ----------------------------------------------------------------------------- statistics for all sections
 278
 279  def med(rs):
 280      return statistics.median(r['GBps'] for r in rs)
 281
 282</pre></td><td valign="top">Returns the median of the field <code>GBps</code> of the records in <code>rs</code>. <code>GBps</code> is the rate of one timed interval in GB/s. It is already in the record when this file runs [Ref1]. For 3 records the median is the middle value.</td></tr>
<tr><td colspan="2"><b>Function <code>analyse</code>: the pairs for Q1 and the selector <code>pool</code></b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 283  def analyse(D):
 284      recs = D['recs']
 285      N = {}
 286      one = lambda rs: (need(len(rs) == 1, 'one record expected, got %d' % len(rs)), rs[0])[1]
 287</pre></td><td valign="top"><code>recs</code> is the list of all interval records, and <code>N</code> collects the results. <code>one(rs)</code> is a helper: a guard checks that the list <code>rs</code> holds exactly one record, and the helper returns that record. It is written as a tuple of two items (a fixed list in round brackets): the guard and the record. Python runs the guard first and returns the second item.</td></tr>
<tr><td colspan="2"><b>Part A: one pair per session and round</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 288      # ---- Q1, part A: one pair per session and round
 289      pa = []
 290      for s in (1, 2, 3):
 291          for rd in (1, 2):
 292              cell = lambda b, k: sorted(sel(recs, dataset='rerun-A', session=s, round=rd, binary=b, kernel=k),
 293                                         key=lambda r: r['interval'])</pre></td><td valign="top">The two loops give 6 pairs: one per session (1, 2, 3) and round (1, 2) of part A. <code>cell(b, k)</code> selects the records of the data set <code>rerun-A</code> with this session, this round, the binary <code>b</code> and the kernel <code>k</code>, and it sorts them by the interval number. In part A each binary runs each kernel in one process per round [Ref6]. So one <code>cell</code> holds the intervals of one process.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 294              old, new, ao, an = cell('bw_old', 'read'), cell('bw_new', 'read'), cell('bw_old', 'asmread'), cell('bw_new', 'asmread')
 295              need(all(len(c) == 3 for c in (old, new, ao, an)), 'three intervals per process in part A')</pre></td><td valign="top">Four selections per pair:<ul><li><code>old</code>: kernel <code>read</code> of <code>bw_old</code>, the old read kernel.</li><li><code>new</code>: kernel <code>read</code> of <code>bw_new</code>, the new read kernel.</li><li><code>ao</code>, <code>an</code>: kernel <code>asmread</code> of <code>bw_old</code> and of <code>bw_new</code>.</li><li>The guard stops the script unless each selection holds exactly 3 records, the 3 timed intervals of one process.</li><li>Part A also holds records of the kernels write, copy, asmwrite and asmcopy [Ref6]. No selection takes them, so they enter no pair.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 296              vo, vn = [r['GBps'] for r in old], [r['GBps'] for r in new]</pre></td><td valign="top"><code>vo</code> and <code>vn</code> are the 3 rates of the old process and the 3 rates of the new process, in GB/s.<ul><li>Each rate is the field <code>GBps</code> of one record. For part A that is the value of column 7 (<code>aggregate_GBps</code>) of one interval row of <code>threads120.csv</code>, as the benchmark printed it with 2 decimals [Ref7].</li><li>The line of the csv that starts with <code># bandwidth:</code> gives the formula of the benchmark: the sum of the bytes of all threads, divided by the longest elapsed time of a thread [Ref7].</li><li>The row <code>best</code> of a process holds the highest of its 3 interval rates [Ref7]. It is not an interval row. facts_data.py skips it, so no record holds it [Ref2].</li><li>All 3 intervals are used, and no rates are added.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 297              pa.append(dict(session=s, round=rd, old=old, new=new, ao=ao, an=an, old_med=med(old), new_med=med(new),
 298                             ratio=med(new) / med(old), drop=(1 - med(new) / med(old)) * 100,
 299                             ratio_lo=min(vn) / max(vo), ratio_hi=max(vn) / min(vo),
 300                             ao_ratio=med(ao) / med(old), an_ratio=med(an) / med(old)))
 301      N['pa'] = pa
 302</pre></td><td valign="top">One dictionary per pair goes into <code>pa</code>, and <code>N['pa']</code> holds the 6 pairs.<ul><li><code>old_med</code>, <code>new_med</code>: the median of the 3 old rates and of the 3 new rates. These are the two rates that the pair compares.</li><li><code>ratio</code> = <code>new_med / old_med</code>.</li><li><code>drop</code> = <code>(1 - new_med / old_med) * 100</code>, in percent.</li><li><code>ratio_lo</code> = lowest new rate / highest old rate. <code>ratio_hi</code> = highest new rate / lowest old rate.</li><li><code>ao_ratio</code>, <code>an_ratio</code>: the median of <code>bw_old asmread</code> and the median of <code>bw_new asmread</code>, each divided by <code>old_med</code>.</li><li>Example, session 1, round 1: the old rates 467.83, 467.92 and 465.38 GB/s give <code>old_med</code> = 467.83 GB/s. The new rates 330.59, 330.09 and 333.25 GB/s give <code>new_med</code> = 330.59 GB/s. The drop is 29.34 % [Ref6].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pairs</code>: old-against-new pairs of a bwx data set</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 303      # ---- Q1, runner bwx12: pairs inside the same process and round
 304      def pairs(dataset, kernels):
 305          out = []
 306          tags = list(dict.fromkeys(r['tag'] for r in sel(recs, dataset=dataset)))</pre></td><td valign="top"><code>pairs(dataset, kernels)</code> builds the pairs of one data set of a bwx runner. <code>tags</code> holds the tags of the data set, each once, in the order of their first record. In the five data sets used below one tag is one process, for example <code>T72L1</code> [Ref6].</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 307          for tag in tags:
 308              for rd in (0, 1):
 309                  o = one(sel(recs, dataset=dataset, tag=tag, round=rd, kernel='oldread'))
 310                  p = dict(dataset=dataset, tag=tag, round=rd, old=o)
 311                  for k in kernels:
 312                      r = one(sel(recs, dataset=dataset, tag=tag, round=rd, kernel=k))
 313                      p[k] = r
 314                      p['drop_' + k] = (1 - r['GBps'] / o['GBps']) * 100
 315                  out.append(p)
 316          return out</pre></td><td valign="top">For each process and for the rounds 0 and 1:<ul><li><code>o</code>: the one <code>oldread</code> record of this process and round. The helper <code>one</code> stops the script when it finds no record or more than one.</li><li><code>r</code>: for each kernel <code>k</code> of the list, the one record of that kernel in the same process and round.</li><li><code>drop_&lt;k&gt;</code> = <code>(1 - r['GBps'] / o['GBps']) * 100</code>, in percent. Both rates are single intervals. No median is taken.</li><li><code>GBps</code> of a bwx record is a sum over the T rows of the interval (one row per thread): each thread gives <code>bytes / elapsed_s / 1e9</code>, and the values of all threads are added. <code>bytes</code> is column 7 and <code>elapsed_s</code> is column 8 of a T row [Ref8]. The column <code>aggregate_GBps</code> of the I row is not used for it [Ref1] [Ref2].</li><li>The rounds are fixed to 0 and 1. A record of a later round would enter no pair. The five data sets below hold only the rounds 0 and 1 [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 317      N['pl'] = pairs('rerun-L', ['asmread'])
 318      N['pi'] = pairs('control-I', ['asmread'])
 319      N['pf'] = pairs('F72d12', ['asmread'])
 320      N['pc'] = pairs('rerun-C', ['read', 'asmread'])
 321      N['p80'] = pairs('L-1', ['asmread'])
 322</pre></td><td valign="top">Five calls. The pair counts are those of the data [Ref6].<ul><li><code>N['pl']</code>: part L, asmread against oldread. 3 processes x 2 rounds = 6 pairs.</li><li><code>N['pi']</code>: control I, asmread against oldread. 2 processes x 2 rounds = 4 pairs.</li><li><code>N['pf']</code>: the earlier run F72d12, asmread against oldread. 1 process x 2 rounds = 2 pairs.</li><li><code>N['pc']</code>: part C, <code>read</code> and asmread against oldread. 4 processes x 2 rounds = 8 pairs, each with <code>drop_read</code> and <code>drop_asmread</code>.</li><li><code>N['p80']</code>: the 8000 MT/s baseline <code>L-1</code>, asmread against oldread, 2 pairs. No other line of facts_text.py or facts_text4.py reads it.</li><li>The records of read_nop96, read_nop256 and read_1pl enter no pair.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>pool</code>: records of several data sets</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 323      # ---- Q2: ranges
 324      def pool(names, kernel, pos=None):
 325          c = dict(dataset=set(names), kernel=kernel)
 326          if pos is not None:
 327              c['pos'] = pos
 328          return sel(recs, **c)
 329      N['pool'] = pool
 330      return N
 331
 332</pre></td><td valign="top"><code>pool(names, kernel, pos)</code> returns the records whose data set is one of <code>names</code> and whose kernel is <code>kernel</code>. When <code>pos</code> is given, the record must also have this position in the kernel sequence. <code>render</code> uses it to take the intervals of several 8000 MT/s data sets as one list (line 417). <code>analyse</code> stores the function as <code>N['pool']</code> and returns <code>N</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>compare</code>: 7200 MT/s range against 8000 MT/s range</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 333  def compare(r72, r80):
 334      a, b = rng(r72), rng(r80)
 335      ov = overlap(a, b)
 336      return dict(a=a, b=b, overlap=ov, dist=gap(a, b), wording=SAME if ov else DIFFERS, width=width_pct(b))
 337
 338</pre></td><td valign="top">Takes two record lists and returns one comparison.<ul><li><code>a</code>, <code>b</code>: the ranges of the 7200 MT/s list and of the 8000 MT/s list. Each range runs from the lowest to the highest <code>GBps</code> of its list. No interval is removed.</li><li><code>overlap</code>: true when <code>a.lo &lt;= b.hi</code> and <code>b.lo &lt;= a.hi</code> [Ref2]. Two ranges that share only one end value count as overlapping.</li><li><code>dist</code>: the distance of the nearest ends in GB/s. It is positive when <code>a</code> lies above <code>b</code>, negative when <code>a</code> lies below <code>b</code>, and 0 when they overlap.</li><li><code>wording</code>: <code>SAME</code> when the ranges overlap, <code>DIFFERS</code> when they do not.</li><li><code>width</code>: <code>(b.hi - b.lo) / b.lo * 100</code>, the width of the 8000 MT/s range in percent.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>render</code>: statistics, verdicts and the whole text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 339  # ----------------------------------------------------------------------------- the sheet
 340
 341  def render(D):
 342      recs = D['recs']
 343      N = analyse(D)
 344      ref = register(D)
 345      V = dict(q1=None, q2=None, q1_parts=[], q2_rows=[], insufficient_data=[], hypotheses=[], rule_wordings=dict(
 346          differs=DIFFERS, same=SAME, no_read=NO_READ))</pre></td><td valign="top">The main function of the file, from line 341 to line 1488. It first calls <code>analyse</code> (the pairs) and <code>register</code> (the file list). <code>V</code> is the verdict object. Its entries start empty, except <code>rule_wordings</code>, which holds the three fixed texts <code>DIFFERS</code>, <code>SAME</code> and <code>NO_READ</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 347      try6 = D['try6']
 348      go, go2 = D['logs']['go'], D['logs']['go2']
 349      A, X = D['A'], D['X']
 350      ev = D['events']
 351      evd = {e['tag']: e for e in ev}
 352      p13 = D['probe13']
 353      rules = os.path.join(S, 'baselines-and-rules.txt')
 354      L = []
 355      w = L.append
 356      extra = {}       # short texts and values of sections 1 to 3 that section 4 quotes
 357      OTHER_DAY.clear()
 358</pre></td><td valign="top">Short names for parts of <code>D</code>, and the output list.<ul><li><code>try6</code>: the boot record. <code>go</code>, <code>go2</code>: the logs of go.sh and go2.sh.</li><li><code>A</code>: the part A folders. <code>X</code>: the bwx12 folders.</li><li><code>ev</code>: the steps of the run. <code>evd</code>: the same steps by their folder tag. <code>p13</code>: the entry <code>probe13</code>. <code>rules</code>: the path of the rules file.</li><li><code>L</code> is the list of the text lines of FACTS.md. <code>w(text)</code> adds one line.</li><li><code>extra</code> collects short texts and values for <code>section4</code> of facts_text4.py. The comment names sections 1 to 3 as their source. The code sets both entries in section 1.5 (lines 1017 and 1128).</li><li><code>OTHER_DAY.clear()</code> empties the set that <code>hmd</code> fills.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>q2row</code>: one comparison row for facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 359      def q2row(part, kernel, row72, scope, c, decides, note='', row_label=None, scope_label=None):
 360          # row_7200 and scope_8000 are the keys of the row. They stay as they were in the earlier builds, so that a
 361          # tool can find a row. row_7200_label and scope_8000_label are the labels that FACTS.md prints.
 362          V['q2_rows'].append(dict(part=part, kernel=kernel, row_7200=row72, lo_7200=c['a']['lo'], hi_7200=c['a']['hi'],
 363                                   n_7200=c['a']['n'], processes_7200=c['a']['procs'], scope_8000=scope,
 364                                   lo_8000=c['b']['lo'], hi_8000=c['b']['hi'], n_8000=c['b']['n'],
 365                                   processes_8000=c['b']['procs'], overlap=c['overlap'],
 366                                   distance_GBps=round(c['dist'], 3), wording=c['wording'] if decides else None,
 367                                   decides=decides, note=note, row_7200_label=row_label or row72,
 368                                   scope_8000_label=scope_label or scope))
 369</pre></td><td valign="top">Appends one dictionary to <code>V['q2_rows']</code>. <code>c</code> is a result of <code>compare</code>.<ul><li>The row holds both ranges as they are (<code>lo_7200</code>, <code>hi_7200</code>, <code>lo_8000</code>, <code>hi_8000</code>), and the counts of intervals and processes of both sides.</li><li><code>distance_GBps</code> is <code>dist</code> rounded to 3 decimals (0.001 GB/s).</li><li><code>wording</code> is stored only when <code>decides</code> is true. Otherwise the field is <code>None</code>.</li><li><code>row_7200</code> and <code>scope_8000</code> are the keys of the row. The two <code>_label</code> fields hold the texts that FACTS.md prints. They default to the keys.</li><li>This file does not call <code>q2row</code>. In line 1464 it passes the function to <code>section4</code> of facts_text4.py [Ref3].</li></ul></td></tr>
<tr><td colspan="2"><b>Values that several sections use</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 370      # =============================================================================== numbers used in several places
 371      go_start, go_end = go['states'][0]['utc'], go['states'][-1]['utc']
 372      one_len = lambda ds: (need(len({r['min_ms'] for r in sel(recs, dataset=ds)}) == 1, 'one interval length in ' + ds),
 373                            '%g s' % (sel(recs, dataset=ds)[0]['min_ms'] / 1000))[1]
 374      secA, secX = one_len('rerun-A'), one_len('rerun-L')      # interval lengths: part A, bwx12 parts
 375      need(one_len('rerun-C') == secX == one_len('control-I'), 'parts L, C, I use the same interval length')
 376      need(len(D['P_kB']) == 1, 'one buffer size in the P rows')
 377      mib = '%g MiB' % (D['P_kB'][0] / 1024)
 378      go2_start, go2_end = go2['states'][0]['utc'], go2['states'][-1]['utc']
 379      f72t = D['rx']['F72d12']['launches']['a6456']['utc']</pre></td><td valign="top"><ul><li><code>go_start</code>, <code>go_end</code>: the times of the first and of the last state line in the log of go.sh. <code>go2_start</code>, <code>go2_end</code>: the same for go2.sh.</li><li><code>one_len(ds)</code>: a guard checks that all records of the data set <code>ds</code> have one value of <code>min_ms</code>, the minimum length of a timed interval in ms. The helper returns that length in seconds as text.</li><li><code>secA</code> is this minimum length for part A (<code>0.5 s</code>), and <code>secX</code> is the one for part L (<code>6 s</code>). A guard checks that part C and control I have the same value as part L. For part A, <code>build_facts.py</code> sets <code>min_ms</code> to the constant 500 [Ref1].</li><li><code>mib</code>: the buffer size of one thread as text, <code>256 MiB</code> (1 MiB = 2^20 bytes). It is the value of the column <code>kB_total</code> of the P rows, divided by 1024. A guard checks that all P rows of the 9 bwx12 files hold one value [Ref1].</li><li><code>f72t</code>: the launch time of the F72d12 process.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 380      rules_time = fd.dt.datetime.strptime(re.search(r'# Written (\S+)Z', fd._open(rules).read())[1], '%Y-%m-%dT%H:%M:%S')
 381      rules_lead = (go_start - rules_time).total_seconds()
 382      need(rules_lead &gt; 0, 'rules written before go.sh started')
 383      # file times on the clock of the agent's server (the start of go.sh above is on the clock of CRB)
 384      mtime = lambda p: fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(p)))
 385      rules_mtime, sha_mtime = mtime(rules), mtime(os.path.join(S, 'local.sha'))
 386      need(rules_mtime == rules_time, 'file time of the rules file equal to the time in its line 2')
 387      need('BEFORE the run (go.sh not yet started)' in fd._open(rules).read().splitlines()[1], 'line 2 of the rules file')
 388      need(sha_mtime &gt; rules_mtime, 'local.sha is newer than the rules file')
 389</pre></td><td valign="top">Guards on the time order of the rules file and the run.<ul><li><code>rules_time</code>: the time in the line <code># Written ...Z</code> of the rules file.</li><li><code>rules_lead</code>: the start of go.sh minus <code>rules_time</code>, in seconds. A guard needs a value above 0. So the time that the rules file states is earlier than the first state line of go.sh.</li><li><code>mtime(p)</code>: the time of the last change of the file <code>p</code>, in UTC, in whole seconds. The comment says that file times are on the clock of the agent's server, and that the start of go.sh is on the clock of CRB.</li><li>Three more guards. The file time of the rules file equals <code>rules_time</code>. Line 2 of the rules file holds the words <code>BEFORE the run (go.sh not yet started)</code>. The file <code>local.sha</code> is newer than the rules file.</li></ul></td></tr>
<tr><td colspan="2"><b>The drops of all pairs, and two guards for Q1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 390      dl = [p['drop_asmread'] for p in N['pl']]
 391      di = [p['drop_asmread'] for p in N['pi']]
 392      df = [p['drop_asmread'] for p in N['pf']]
 393      dcr = [p['drop_read'] for p in N['pc']]
 394      dca = [p['drop_asmread'] for p in N['pc']]
 395      dpa = [p['drop'] for p in N['pa']]
 396      need(min(dl + di + df + dcr + dca + dpa) &gt; 0, 'new kernel below old kernel in every pair')
 397      need(all(p['ratio_hi'] &lt; 1 for p in N['pa']), 'every bw_new read interval below every bw_old read interval of its pair')
 398</pre></td><td valign="top">Six lists of drops in percent, one value per pair.<ul><li><code>dl</code>, <code>di</code>, <code>df</code>: asmread against oldread in part L (6 values), in control I (4) and in F72d12 (2).</li><li><code>dcr</code>, <code>dca</code>: <code>read</code> against oldread and asmread against oldread in part C (8 values each).</li><li><code>dpa</code>: the drops of the 6 part A pairs.</li><li>First guard: the lowest of all 34 drops is above 0. So the new side is below the old read kernel in every pair.</li><li>Second guard: <code>ratio_hi</code> is below 1 in every part A pair. So the highest <code>bw_new read</code> interval is below the lowest <code>bw_old read</code> interval of the same pair.</li></ul></td></tr>
<tr><td colspan="2"><b>Part C: groups by the kernel that ran directly before</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 399      # part C grouped by the kernel that ran directly before (rule V2): name -&gt; (records, drops against oldread)
 400      Crec = sel(recs, dataset='rerun-C')
 401
 402      def cgroup(kernel, before):
 403          rs = sel(Crec, kernel=kernel, kernel_before=before)
 404          ds = [p['drop_' + kernel] for r in rs for p in N['pc'] if p[kernel] is r]
 405          need(len(ds) == len(rs) &gt; 0, 'one drop per interval of a part C group')
 406          return rs, ds</pre></td><td valign="top"><code>Crec</code> holds all records of part C. <code>cgroup(kernel, before)</code> builds one group.<ul><li><code>rs</code>: the part C records of this kernel whose field <code>kernel_before</code> equals <code>before</code>.</li><li><code>ds</code>: for each record of <code>rs</code>, the drop of the pair in <code>N['pc']</code> that holds this same record. So each drop still compares the interval with the oldread interval of its own process and round.</li><li>The guard needs as many drops as records, and at least one record.</li><li>The function returns the two lists <code>rs</code> and <code>ds</code>.</li><li>facts_data.py sets <code>kernel_before</code> from the kernel sequence in the header line of the csv, not from time stamps [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 407      CG = {'read after oldread': cgroup('read', 'oldread'), 'read after asmread': cgroup('read', 'asmread'),
 408            'asmread after read': cgroup('asmread', 'read'), 'asmread first': cgroup('asmread', FIRST),
 409            'asmread after oldread': cgroup('asmread', 'oldread')}
 410      N['CG'] = CG
 411      need(sum(len(v[0]) for v in CG.values()) == len(sel(Crec, kernel={'read', 'asmread'})), 'the five groups hold every load-only interval of part C')
 412</pre></td><td valign="top">The five groups, with the number of intervals in the rerun [Ref6]:<ul><li><code>read after oldread</code>: 4 intervals, from the cfwd processes T72C1 and T72C3.</li><li><code>read after asmread</code>: 4 intervals, from the crev processes T72C2 and T72C4.</li><li><code>asmread after read</code>: 4 intervals (cfwd).</li><li><code>asmread first</code>: 2 intervals. asmread is the first interval of a crev process (round 0).</li><li><code>asmread after oldread</code>: 2 intervals. In round 1 of a crev process asmread follows oldread, the last kernel of round 0.</li><li>The guard checks that the five groups together hold as many records as part C has <code>read</code> and asmread records. <code>N['CG']</code> stores the groups.</li></ul></td></tr>
<tr><td colspan="2"><b>Record lists for Q2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 413      pool = N['pool']
 414      L72o, L72a = sel(recs, dataset='rerun-L', kernel='oldread'), sel(recs, dataset='rerun-L', kernel='asmread')
 415      I72o, I72a = sel(recs, dataset='control-I', kernel='oldread'), sel(recs, dataset='control-I', kernel='asmread')
 416      F72o, F72a = sel(recs, dataset='F72d12', kernel='oldread'), sel(recs, dataset='F72d12', kernel='asmread')
 417      P12o, P12a = pool(BW12, 'oldread', 0), pool(BW12, 'asmread', 1)
 418      PALLo, PALLa = pool(BW12 + BW11, 'oldread', 0), pool(BW12 + BW11, 'asmread', 1)
 419      A72o = sel(recs, dataset='rerun-A', binary='bw_old', kernel='read')
 420      A80o = sel(recs, dataset={'A-1', 'A-2', 'A-3'}, binary='bw_old', kernel='read')
 421      C72o = sel(recs, dataset='rerun-C', kernel='oldread')</pre></td><td valign="top">Each list is made with <code>sel</code> or <code>pool</code>. The counts are those of the data [Ref6].<ul><li><code>L72o</code>, <code>L72a</code>: oldread and asmread of part L (6 intervals each). <code>I72o</code>, <code>I72a</code>: control I (4 each). <code>F72o</code>, <code>F72a</code>: F72d12 (2 each).</li><li><code>P12o</code>: the 8000 MT/s pool of oldread at position 0 in the data sets <code>L-1</code> to <code>L-4</code> (11 intervals of 7 processes). <code>P12a</code>: asmread at position 1 in the same data sets (11 intervals). Each pool holds intervals of two lengths: 6 s in <code>L-1</code> (2 of the 11, the length of part L) and 4 s in <code>L-2</code> to <code>L-4</code> (9 of the 11) [Ref6].</li><li><code>PALLo</code>, <code>PALLa</code>: the same pools plus the bwx11 data sets <code>R0</code> and <code>R0b</code> (18 intervals each). This file does not use them itself. In lines 1461 and 1462 it passes them to facts_text4.py.</li><li><code>A72o</code>: <code>bw_old read</code> of part A, all sessions and rounds (18 intervals of 6 processes).</li><li><code>A80o</code>: <code>bw_old read</code> of the 8000 MT/s data sets <code>A-1</code>, <code>A-2</code> and <code>A-3</code> (21 intervals of 7 processes).</li><li><code>C72o</code>: oldread of part C at both of its positions, 0 in cfwd and 2 in crev (8 intervals of 4 processes).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 422      cLo, cLa = compare(L72o, P12o), compare(L72a, P12a)
 423      cIo, cIa = compare(I72o, P12o), compare(I72a, P12a)
 424      cFo, cFa = compare(F72o, P12o), compare(F72a, P12a)
 425      cAo, cCo = compare(A72o, A80o), compare(C72o, P12o)
 426</pre></td><td valign="top">Eight calls of <code>compare</code> (line 333). Each call takes all intervals of a list as one range from the lowest to the highest rate. No call here uses a record of the new read kernel.<ul><li><code>cLo</code>, <code>cLa</code>: oldread and asmread of part L against <code>P12o</code> and <code>P12a</code>.</li><li><code>cIo</code>, <code>cIa</code>: control I against the same two pools.</li><li><code>cFo</code>, <code>cFa</code>: F72d12 against the same two pools.</li><li><code>cAo</code>: <code>bw_old read</code> of part A against <code>A80o</code>.</li><li><code>cCo</code>: oldread of part C against <code>P12o</code>.</li><li>Example <code>cLo</code>: 461.61 to 464.29 GB/s against 465.53 to 470.05 GB/s. The ranges do not overlap, <code>dist</code> is -1.24 GB/s, and the wording is <code>DIFFERS</code> [Ref4] [Ref6].</li></ul></td></tr>
<tr><td colspan="2"><b>Part A, session 1: load-only kernels against 8000 MT/s</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 427      # part A, load-only kernels, session 1 against the same round at 8000 MT/s (rule V3)
 428      pa3 = []
 429      for b, k in (('bw_new', 'read'), ('bw_new', 'asmread'), ('bw_old', 'asmread')):
 430          for rd in (1, 2):
 431              s1 = sorted(sel(recs, dataset='rerun-A', session=1, round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
 432              a1 = sorted(sel(recs, dataset='A-1', round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
 433              a2 = sorted(sel(recs, dataset='A-2', round=rd, binary=b, kernel=k), key=lambda r: r['interval'])
 434              b80 = rng(a1 + a2)
 435              above = [r['GBps'] - b80['hi'] for r in s1 if r['GBps'] &gt; b80['hi']]
 436              below = [b80['lo'] - r['GBps'] for r in s1 if r['GBps'] &lt; b80['lo']]
 437              pa3.append(dict(binary=b, kernel=k, round=rd, s1=s1, a1=a1, a2=a2, b80=b80, above=above, below=below,
 438                              inside=3 - len(above) - len(below)))
 439      newread = [x for x in pa3 if (x['binary'], x['kernel']) == ('bw_new', 'read')]
 440</pre></td><td valign="top">The list <code>pa3</code> gets 6 entries: 3 kernels (<code>bw_new read</code>, <code>bw_new asmread</code>, <code>bw_old asmread</code>) x 2 rounds. The comment names rule V3.<ul><li><code>s1</code>: the 3 intervals of session 1 of the rerun for this binary, kernel and round.</li><li><code>a1</code>, <code>a2</code>: the intervals of the 8000 MT/s data sets <code>A-1</code> and <code>A-2</code> for the same binary, kernel and round. <code>b80</code> is the range of both lists together.</li><li><code>above</code>: for each interval of <code>s1</code> above <code>b80.hi</code>, its distance to <code>b80.hi</code> in GB/s. <code>below</code>: the same for an interval below <code>b80.lo</code>.</li><li><code>inside</code> = 3 - the number above - the number below.</li><li><code>A-2</code> holds no <code>bw_old asmread</code> record. So for that kernel <code>b80</code> comes from the 3 intervals of <code>A-1</code> alone [Ref6].</li><li><code>newread</code>: the 2 entries of <code>bw_new read</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Title and notes of FACTS.md</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 441      # =============================================================================== title
 442      w('# Facts sheet: whole-chip read test at 7200 MT/s, rerun of 2026-11-17')
 443      w('')
 444      w('- This sheet is the source for the report of the rerun.')
 445      w('- The script `S/build_facts.py` wrote this file from the raw files of section 7. No measured number was typed by '
 446        'hand.')
 447      w('- GB = 1e9 bytes. All times are UTC. A time without a date is on %s. A time on another day carries its date '
 448        'in the same sentence or table cell.' % RERUN_DAY)
 449      w('- R = `%s`' % R)
 450      w('- S = `%s`' % S)
 451      w('- A reference such as [Ref5] points to the file list in section 7.')
 452      w('- Rates are shown to 0.01 GB/s, rounded half up. A median of an even number of values can therefore differ by '
 453        '0.01 GB/s from the output of stat_k120.py. A difference of two rates is computed from the values before '
 454        'rounding. It can therefore differ by 0.01 GB/s from the difference of the two rounded values.')
 455      w('- Fixed properties of the setup are written as the task and the run scripts give them: the CPU numbers of the '
 456        'two meshes, the loads per 256 B of each kernel, the two memory speeds, and the dates of earlier runs.')
 457      w('')
 458</pre></td><td valign="top">Writes the title line and the list of notes under it: the source of the numbers, the units (GB = 1e9 bytes, times in UTC), the date rule, the folders <code>R</code> and <code>S</code>, the meaning of <code>[RefN]</code>, and the rounding. The rounding note says that rates are shown to 0.01 GB/s, half up, and that a difference of two rates is computed before rounding. So a printed difference can differ by 0.01 GB/s from the difference of the two printed rates. The last note says that fixed properties of the setup are written as the task and the run scripts give them: the CPU numbers of the two meshes, the loads per 256 B of each kernel, the two memory speeds, and the dates of earlier runs.</td></tr>
<tr><td colspan="2"><b>Section 0: heading and guards of the Short version</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 459      # =============================================================================== 0
 460      w('## 0. Short version')
 461      w('')
 462      need(not cLa['overlap'] and cLa['dist'] &gt; 0, 'part L asmread above the 8000 MT/s pool')
 463      need(cFa['overlap'], 'F72d12 asmread inside the 8000 MT/s pool')
 464      need(cAo['overlap'] and cCo['overlap'], 'old read: parts A and C overlap the 8000 MT/s range')
 465      need(not cLo['overlap'] and cLo['dist'] &lt; 0, 'old read: part L below the 8000 MT/s pool')
 466      need(cIo['overlap'] and cFo['overlap'], 'old read: control I and F72d12 overlap the 8000 MT/s pool')
 467      need(all(x['inside'] == 0 and not x['below'] for x in newread), 'bw_new read of session 1 above the 8000 MT/s range')</pre></td><td valign="top">Writes the heading <code>## 0. Short version</code>. Then guards check the patterns that the three sentences of the Short version state:<ul><li>asmread of part L: its range does not overlap the 8000 MT/s pool and lies above it.</li><li>asmread of F72d12: its range overlaps the pool.</li><li>Old read kernel, parts A and C: each range overlaps its 8000 MT/s range.</li><li>Old read kernel, part L: its range does not overlap the pool and lies below it.</li><li>Old read kernel, control I and F72d12: each range overlaps the pool.</li><li><code>bw_new read</code>, session 1, both rounds: no interval lies inside or below the 8000 MT/s range. So all 3 intervals lie above it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 468      inside = lambda k: k['b']['lo'] &lt;= k['a']['lo'] and k['a']['hi'] &lt;= k['b']['hi']
 469      need(inside(cFo) and inside(cIo), 'old read: F72d12 and control I inside the 8000 MT/s pool')
 470      c_ro, c_ra = CG['read after oldread'], CG['read after asmread']
 471      need(len(c_ro[1]) == len(c_ra[1]), 'equal number of pairs in both read groups of part C')
 472      # The three sentences and the detail list quote numbers of section 4 (the view by start state). They are built
 473      # after section 4 by short_version() and are inserted at this place.
 474      i_short = len(L)
 475      V['short_version'] = None
 476</pre></td><td valign="top"><ul><li><code>inside(k)</code> is true when the 7200 MT/s range of a comparison lies fully inside its 8000 MT/s range. A guard needs this for oldread of F72d12 and of control I.</li><li><code>c_ro</code>, <code>c_ra</code>: the groups <code>read after oldread</code> and <code>read after asmread</code>. A guard needs the same number of drops in both.</li><li><code>i_short = len(L)</code> remembers the current end of the line list. The three sentences quote numbers of section 4. So <code>short_version</code> (line 477) builds them after section 4, and <code>render</code> inserts them at this index (line 1467).</li><li><code>V['short_version']</code> is set to <code>None</code> here. <code>short_version</code> fills it later (line 559).</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>short_version</code>: the text of section 0</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 477      def short_version(c):</pre></td><td valign="top">These lines are inside the function <code>render</code>, which starts at line 341.<ul><li><code>short_version</code> is defined inside <code>render</code>. It can read the variables of <code>render</code>.</li><li>It does not run at this place. <code>render</code> calls it at line 1467 with the dictionary <code>ctx</code> as <code>c</code>. By then <code>section4</code> of facts_text4.py has added its results to <code>ctx</code>.</li><li>It computes no rate. It takes lowest and highest values, differences and counts from record lists that already hold <code>GBps</code>, and it rounds them for the text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 478          by, pcv, kF1, kI1 = c['byst'], c['partC_view'], c['kF1'], c['kI1']
 479          kAao, oth = c['kAao'], c['byst_other']</pre></td><td valign="top">These two lines take six results of <code>section4</code> out of <code>c</code> [Ref3]:<ul><li><code>by</code> (<code>c['byst']</code>): the oldread and asmread ranges of the 8000 MT/s pool L-1 to L-4, split by the start state of the process.</li><li><code>pcv</code> (<code>c['partC_view']</code>): oldread of part C compared with the pool processes that started after 120-thread work.</li><li><code>kF1</code>, <code>kI1</code>: asmread of F72d12 and of control I, each compared with the data set L-1 alone.</li><li><code>kAao</code>: the part C asmread intervals that ran directly after oldread, compared with the asmread pool of L-1 to L-4.</li><li><code>oth</code> (<code>c['byst_other']</code>): oldread ranges of the runners bwx11 and bwx for processes that started after 120-thread work.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 480          need(not kAao['overlap'] and kAao['dist'] &gt; 0, 'part C: asmread after oldread above the 8000 MT/s pool')</pre></td><td valign="top">A comparison such as <code>kAao</code> is a result of <code>compare</code> (line 333). Its key <code>a</code> is the 7200 MT/s range, <code>b</code> is the 8000 MT/s range, and <code>dist</code> is the distance of the nearest ends in GB/s. This guard needs no overlap and a distance above 0. Then every part C asmread interval that ran directly after oldread is above the highest asmread rate of the 8000 MT/s pool.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 481          a_lo = sum(1 for r in A72o if r['GBps'] &lt; cAo['b']['lo'])
 482          a_hi = sum(1 for r in A72o if r['GBps'] &gt; cAo['b']['hi'])
 483          need(a_lo &gt; 0 and a_hi &gt; 0 and cAo['a']['hi'] - cAo['a']['lo'] &gt; cAo['b']['hi'] - cAo['b']['lo'],
 484               'part A, old read: the 7200 MT/s range is wider than the 8000 MT/s range on both sides')</pre></td><td valign="top"><code>A72o</code> holds the <code>bw_old read</code> intervals of part A from all sessions and rounds (line 419). <code>cAo['b']</code> is the range of <code>bw_old read</code> in the 8000 MT/s data sets A-1 to A-3 (line 425).<ul><li><code>a_lo</code> counts the intervals of <code>A72o</code> whose <code>GBps</code> is below the lowest 8000 MT/s rate.</li><li><code>a_hi</code> counts the intervals whose <code>GBps</code> is above the highest 8000 MT/s rate.</li><li>Both tests are strict (<code>&lt;</code>, <code>&gt;</code>), and they use the values before rounding.</li><li>The guard needs at least one interval on each side. It also needs the 7200 MT/s range (<code>hi - lo</code>, in GB/s) to be wider than the 8000 MT/s range.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 485          need(inside(cFa), 'asmread: F72d12 inside the range of the 8000 MT/s pool')
 486          nL, nP = nns(L72o), nn(cLo['b'])
 487          need(nns(L72a) == nL and nn(cLa['b']) == nP, 'part L: the same n for oldread and asmread on both sides')</pre></td><td valign="top"><ul><li>Line 485: guard. The asmread range of F72d12 must lie inside the asmread range of the 8000 MT/s pool (<code>inside</code>, line 468).</li><li><code>nL</code>: the text for n of the oldread intervals of part L. <code>nns</code> writes it as intervals / processes / sessions / boots.</li><li><code>nP</code>: the text for n of the 8000 MT/s oldread pool. <code>nn</code> writes it as intervals / processes / boots.</li><li>Line 487: guard. The asmread side must give the same two texts. So the sentences below use <code>nL</code> and <code>nP</code> for both kernels.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 488          short = [
 489              'Q1: yes, at 7200 MT/s with 12 memory modules the new read kernel was still below the old read kernel: %s '
 490              'lower when it ran directly after the old read kernel and %s lower when it ran directly after asmread '
 491              '(part C, %s runs, %d pairs each).' % (pcr(c_ro[1]), pcr(c_ra[1]), secX, len(c_ro[1])),</pre></td><td valign="top"><code>short</code> is the list of the three sentences. Sentence 1 answers Q1 from the read intervals of part C.<ul><li><code>c_ro[1]</code>: the drops of the group "read after oldread". <code>c_ra[1]</code>: the drops of the group "read after asmread" (lines 402 to 409 and 470).</li><li>One drop is <code>(1 - GBps of read / GBps of oldread) x 100</code>, in percent. Both intervals come from the same process and round (lines 309 to 314).</li><li>In the group "read after asmread" (the crev processes) the oldread interval of the pair is the last of its round. It ran after the read interval.</li><li><code>pcr</code> takes the lowest and the highest drop of a list and prints each with 1 decimal, half up.</li><li><code>secX</code> is the interval length of the bwx12 parts as text. <code>len(c_ro[1])</code> is the number of pairs per group. The guard of line 471 checks that both groups hold the same number.</li><li>The word "yes" is fixed text. The guard of line 396 checks it: every drop must be above 0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 492              'Q2, old read kernel: by the rule fixed before the run the result against the 8000 MT/s runs is "%s" in '
 493              'the repeat of the 2026-11-13 test (part A, where the test cannot exclude a difference of about %s %%, '
 494              'est.) and in part C (about %s %%, est.), and the rate was lower in part L (%s GB/s, n = %s, against '
 495              '%s GB/s, n = %s), but the data do not show that the boot or the memory speed is the cause.'
 496              % (SAME, pc(cAo['width']), pc(cCo['width']), sp(cLo['a']), nL, sp(cLo['b']), nP),</pre></td><td valign="top">Sentence 2 is about the old read kernel in Q2.<ul><li><code>SAME</code> is the fixed wording. The guard of line 464 checks that part A (<code>cAo</code>) and part C (<code>cCo</code>) overlap their 8000 MT/s ranges.</li><li><code>pc(cAo['width'])</code>, <code>pc(cCo['width'])</code>: the width of each 8000 MT/s range, <code>(hi - lo) / lo x 100</code>, in percent with 1 decimal.</li><li><code>sp(cLo['a'])</code>: the lowest and the highest oldread rate of part L. <code>sp(cLo['b'])</code>: the lowest and the highest rate of the 8000 MT/s oldread pool (L-1 to L-4, position 0). <code>sp</code> prints each end with 2 decimals.</li><li>The words "the rate was lower in part L" are fixed text. The guard of line 465 checks them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 497              'Q2, new read kernel: asmread (the hand-written loop with the same loads, used in place of the new read '
 498              'kernel) ran above every bwx12 row of the fixed 8000 MT/s list in part L (%s GB/s, n = %s, against %s GB/s, '
 499              'n = %s), in control I (%s GB/s, n = %s, %s) and in the %d part C intervals that ran directly after the old '
 500              'read kernel (%s GB/s), but an earlier run of the same line in the same 7200 MT/s boot gave %s GB/s '
 501              '(F72d12, n = %s), and each memory speed has one boot, so the data do not show an effect of the memory '
 502              'speed.'
 503              % (sp(cLa['a']), nL, sp(cLa['b']), nP, sp(cIa['a']), nns(I72a), ADDED, kAao['a']['n'], sp(kAao['a']),
 504                 sp(cFa['a']), nns(F72a)),
 505          ]</pre></td><td valign="top">Sentence 3 is about the load-only loop in Q2. It uses asmread in place of the new read kernel.<ul><li><code>sp(cLa['a'])</code> against <code>sp(cLa['b'])</code>: the asmread range of part L against the asmread range of the 8000 MT/s pool (L-1 to L-4, position 1).</li><li><code>sp(cIa['a'])</code>, <code>nns(I72a)</code>: the asmread range of control I and its n.</li><li><code>kAao['a']['n']</code>, <code>sp(kAao['a'])</code>: the number and the range of the part C asmread intervals that ran directly after oldread.</li><li><code>sp(cFa['a'])</code>, <code>nns(F72a)</code>: the asmread range of F72d12 and its n.</li><li>The words "ran above every bwx12 row" are fixed text. Guards check them: line 462 for part L, line 480 for part C, and a guard in <code>section4</code> for control I [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 506          detail = [
 507              'Q1, part L (%s runs): asmread was %s below the old read kernel (%d pairs).' % (secX, pcr(dl), len(dl)),
 508              'Q1, part A (the repeat of the 2026-11-13 test, whole-pass stop, %s): the new read kernel was %s below the '
 509              'old read kernel (%d pairs of process medians). These percent values are less exact than those of parts L '
 510              'and C (section 3.1).' % (secA, pcr(dpa), len(dpa)),</pre></td><td valign="top"><code>detail</code> is the list of the 12 detail lines. The first two are about Q1.<ul><li><code>dl</code>: the drops of part L (line 390). Each one compares the asmread interval with the oldread interval of the same process and round.</li><li><code>dpa</code>: the drops of part A (line 395). Each one compares the median of the 3 <code>bw_new read</code> intervals with the median of the 3 <code>bw_old read</code> intervals of the same session and round.</li><li><code>pcr</code> prints the lowest and the highest drop of each list. <code>len</code> gives the number of pairs. In this run each list holds 6 drops [Ref4].</li><li><code>secA</code> is the interval length of part A as text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 511              'Q2, old read kernel, the two comparisons with the wording "%s": part A gave %s GB/s (n = %s) against '
 512              '%s GB/s (n = %s). Part C gave %s GB/s (n = %s) against %s GB/s (n = %s). The size that the test cannot '
 513              'exclude is the width of the 8000 MT/s range: %s %% of its lower end in part A and %s %% in part C (est. '
 514              'from one boot). In part A the 7200 MT/s range is wider than the 8000 MT/s range (%s GB/s against '
 515              '%s GB/s): %d of its %d intervals lie below that range and %d lie above it (section 4.2).'
 516              % (SAME, sp(cAo['a']), nns(A72o), sp(cAo['b']), nn(cAo['b']), sp(cCo['a']), nns(C72o), sp(cCo['b']),
 517                 nn(cCo['b']), pc(cAo['width']), pc(cCo['width']), g(cAo['a']['hi'] - cAo['a']['lo']),
 518                 g(cAo['b']['hi'] - cAo['b']['lo']), a_lo, cAo['a']['n'], a_hi),</pre></td><td valign="top">Detail line 3 gives the numbers behind the wording <code>SAME</code> of sentence 2.<ul><li>Part A: <code>sp(cAo['a'])</code> is the lowest and the highest rate of all <code>bw_old read</code> intervals of part A. <code>sp(cAo['b'])</code> is the same for the data sets A-1 to A-3.</li><li>Part C: <code>sp(cCo['a'])</code> covers all oldread intervals of part C. <code>sp(cCo['b'])</code> covers the 8000 MT/s oldread pool.</li><li><code>pc(cAo['width'])</code>, <code>pc(cCo['width'])</code>: the widths of the two 8000 MT/s ranges in percent of their lower ends.</li><li><code>g(cAo['a']['hi'] - cAo['a']['lo'])</code>: the width of the 7200 MT/s range of part A in GB/s. The difference is taken before rounding. The next value is the same for the 8000 MT/s range.</li><li><code>a_lo</code>, <code>a_hi</code>: the counts of lines 481 and 482. <code>cAo['a']['n']</code>: the number of <code>bw_old read</code> intervals of part A.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 519              'Q2, part C: the fixed rules contradict each other here. Rule F2 points 2 and 3 would present part C at '
 520              '7200 MT/s only. This sheet follows rules V1 point 2, V2 point 4 and V4 and compares part C with the '
 521              '8000 MT/s rows (decision (r) in section 2).',
 522              'Q2, old read kernel: two other rows of the same line in the same 7200 MT/s boot lie inside the range of '
 523              'the 8000 MT/s pool L-1 to L-4. F72d12 (%d process at %s UTC, before the rerun) gave %s GB/s. Control I '
 524              '(%d processes, idle start, %s, %s) gave %s GB/s.'
 525              % (cFo['a']['procs'], hm(f72t)[:5], sp(cFo['a']), cIo['a']['procs'], ADDED, NOT_PLAN, sp(cIo['a'])),</pre></td><td valign="top"><ul><li>Lines 519 to 521: detail line 4 is fixed text about the rules for part C.</li><li>Lines 522 to 525: detail line 5 gives the oldread ranges of F72d12 (<code>cFo['a']</code>) and of control I (<code>cIo['a']</code>), each with its number of processes.</li><li><code>hm(f72t)[:5]</code> is the launch time of the F72d12 process as hours and minutes (line 379).</li><li>The words "lie inside the range" are fixed text. The guard of line 469 checks them.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 526              'Q2, old read kernel, view added after the numbers were seen (section 4.2): the %d bwx12 processes of the '
 527              'pool L-1 to L-4 that started %.0f s to %.0f s after a 120-thread bwx12 process gave %s GB/s (%s). Part L '
 528              'and part C also started after 120-thread work. Both lie below these %d processes: part L by %s GB/s and '
 529              'part C by %s GB/s at the nearest ends. Limit: these %d processes are not all 8000 MT/s processes with that '
 530              'kind of start state. Against the other-binary processes that started after 120-thread work, part C '
 531              'overlaps (bwx11: %s GB/s, %s. Runner bwx, position 0: %s GB/s, %s). Part L lies below these rows too.'
 532              % (by['Bo']['procs'], by['gaps'][0], by['gaps'][-1], sp(by['Bo']), nn(by['Bo']), by['Bo']['procs'],
 533                 g(by['near']), g(pcv['near']), by['Bo']['procs'], sp(oth['b11']), nn(oth['b11'], boots=False),
 534                 sp(oth['bx0']), nn(oth['bx0'], boots=False)),
 535              'Q2, old read kernel: Insufficient data: why part L was lower. ' + H1_MEAS,</pre></td><td valign="top">Detail line 6 quotes the view by start state that <code>section4</code> computed [Ref3].<ul><li><code>by['Bo']</code>: the oldread range (position 0) of the pool processes that were launched at a 1-minute load average of 1.0 or more. A guard in <code>section4</code> checks that each of them started at most 30 s after the end of a 120-thread bwx12 process.</li><li><code>by['gaps'][0]</code>, <code>by['gaps'][-1]</code>: the shortest and the longest time between the end of that 120-thread process and the launch, printed in whole seconds.</li><li><code>by['near']</code>: the lowest rate of <code>by['Bo']</code> minus the highest oldread rate of part L, in GB/s. <code>pcv['near']</code>: the same for part C.</li><li><code>oth['b11']</code>, <code>oth['bx0']</code>: the oldread ranges (position 0) of bwx11 and of the first runner bwx. <code>nn(..., boots=False)</code> writes n as intervals / processes.</li><li>Line 535: detail line 7 is fixed text plus the constant <code>H1_MEAS</code> (line 26).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 536              'Q2, new read kernel, asmread in the three visits of the 7200 MT/s boot: F72d12 lies inside the range of '
 537              'the 8000 MT/s pool L-1 to L-4. Against L-1 alone (the baseline row with the identical argument line) it '
 538              'is %s GB/s higher. %s Control I (idle start, %s, %s) lies above every bwx12 row of the fixed 8000 MT/s '
 539              'list, by %s GB/s at the nearest ends (%s GB/s against L-1 alone). The three visits (F72d12, part L, '
 540              'control I) span %s GB/s.'
 541              % (g(kF1['dist']), c['f72_limit'], ADDED, NOT_PLAN, g(cIa['dist']), g(kI1['dist']),
 542                 sp(rng(F72a + L72a + I72a))),</pre></td><td valign="top">Detail line 8 is about asmread in the three visits of the 7200 MT/s boot.<ul><li><code>kF1['dist']</code>: the lowest asmread rate of F72d12 minus the highest asmread rate of L-1 alone, in GB/s.</li><li><code>c['f72_limit']</code>: a sentence that <code>section4</code> built about the process list of F72d12 [Ref3].</li><li><code>cIa['dist']</code>: the lowest asmread rate of control I minus the highest rate of the pool L-1 to L-4. <code>kI1['dist']</code>: the same against L-1 alone.</li><li><code>rng(F72a + L72a + I72a)</code>: the three record lists are joined to one list. <code>rng</code> takes the lowest and the highest <code>GBps</code> of all asmread intervals of F72d12, part L and control I. No rates are added.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 543              'Q2, new read kernel, part C: asmread directly after oldread (crev, round 1, position 0) gave %s GB/s '
 544              '(n = %s). By rule V1 point 2 the wording is "%s" against the pool L-1 to L-4 (%s GB/s, n = %s). Part C is '
 545              'higher by %s GB/s at the nearest ends. The baseline matches in the kernel that ran directly before. It '
 546              'does not match in the position: asmread is at position 1 in rows L-1 to L-4. This comparison follows '
 547              'decision (r) in section 2.'
 548              % (sp(kAao['a']), nns(c['Aao']), kAao['wording'], sp(kAao['b']), nn(kAao['b']), g(kAao['dist'])),
 549              'Q2, new read kernel: the new read kernel itself (bw_new read) lies outside (above) the 8000 MT/s range of '
 550              'the same round in session 1 of part A. The bwx12 kernel read has no 8000 MT/s run.',</pre></td><td valign="top"><ul><li>Lines 543 to 548: detail line 9 prints the comparison <code>kAao</code>. The values are the range and n of the part C asmread intervals directly after oldread (<code>c['Aao']</code>), the wording, the range and n of the 8000 MT/s asmread pool, and the distance of the nearest ends.</li><li>The guard of line 480 allows no overlap. So <code>kAao['wording']</code> is <code>DIFFERS</code> here.</li><li>Lines 549 and 550: detail line 10 is fixed text. The guard of line 467 checks its first sentence: in session 1 of part A every <code>bw_new read</code> interval is above the 8000 MT/s range of its round.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 551              'Q2, machine state: the hardware error records during the rerun are not known (the kernel log was not '
 552              'read). At 8000 MT/s, 2 corrected records fall inside the interval with the lowest asmread value of the '
 553              'pool L-1 to L-4 (%s GB/s). Without this interval the pool spans %s GB/s, and no wording changes '
 554              '(sections 4.1 and 4.4). The firmware settings of the boot of the rerun were not read, apart from the '
 555              'memory speed (section 1.5, point 13).' % (g(c['hw']['low_a']['GBps']), sp(c['hw']['wo'])),
 556              'Q2, new read kernel: Insufficient data: whether a difference comes from the memory speed. Runs in several '
 557              'boots per speed would resolve it.',
 558          ]</pre></td><td valign="top"><ul><li>Lines 551 to 555: detail line 11. <code>c['hw']['low_a']['GBps']</code> is the lowest asmread rate of the 8000 MT/s pool. <code>c['hw']['wo']</code> is the range of the pool without that one interval. <code>section4</code> computes both [Ref3].</li><li>The count "2 corrected records" and the words "no wording changes" are fixed text. Guards in <code>section4</code> check them [Ref3].</li><li>Lines 556 and 557: detail line 12 is fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 559          V['short_version'] = dict(sentences=short, detail=detail)
 560          out = []
 561          for s_ in short:
 562              out += [s_, '']
 563          out += ['More detail for these three sentences:', ''] + ['- ' + d_ for d_ in detail] + ['']
 564          return out</pre></td><td valign="top">Line 559 stores the three sentences and the 12 detail lines in the verdict object <code>V</code>. So facts.json holds them too. Lines 560 to 563 build the lines for the sheet: each sentence with an empty line after it, the line "More detail for these three sentences:", and one bullet per detail line. <code>render</code> inserts the returned list at the index <code>i_short</code> (line 1467).</td></tr>
<tr><td colspan="2"><b>Section 0: the word list</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 565      w('&lt;details&gt;')
 566      w('&lt;summary&gt;Words used here&lt;/summary&gt;')
 567      w('')
 568      words = [</pre></td><td valign="top">After the definition of <code>short_version</code>, <code>render</code> continues here.<ul><li>These lines write the first lines of a folded block (<code>&lt;details&gt;</code>). A browser shows it closed until the reader opens it.</li><li><code>words</code> is a list of 52 pairs: a term and its definition.</li><li>41 definitions are fixed text. 11 definitions get a value or a reference number, as the next rows say.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 569          ('CRB', 'the Arm reference server under test. It has 128 CPUs.'),
 570          ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.'),
 571          ('Whole chip, 120 threads, 64+56', 'our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on '
 572           'mesh 1. Each thread reads its own buffer of %s from memory.' % mib),
 573          ('MT/s', 'million transfers per second, the unit of memory speed.'),
 574          ('Memory module', 'one DIMM. CRB has 12 slots.'),
 575          ('Read kernel', 'the inner loop of the benchmark that reads memory. In this sheet "kernel" means this loop. '
 576           'The operating system kernel is always written "Linux kernel".'),
 577          ('Old read kernel', 'portable C code with 16 running sums. Each load is followed by an add. Its name is '
 578           '`read` in the binary bw_old and `oldread` in the runner bwx12.'),
 579          ('New read kernel', 'NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name '
 580           'is `read` in the binary bw_new and `read` in bwx12.'),
 581          ('asmread', 'a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. '
 582           '"ldp q" is the Arm instruction that loads two 16-byte vector registers.'),
 583          ('Load-only loop', 'the new read kernel or asmread.'),
 584          ('read_nop96, read_nop256, read_1pl', 'test loops of bwx12: the asmread loop with 96 or 256 no-operation '
 585           'instructions per 256 B, and a loop with one load per 64 B line.'),
 586          ('bandwidth.c, bw_old, bw_new', 'the benchmark and its two binaries of 2026-11-13. bw_old was built from the '
 587           'old source, bw_new from the new source.'),
 588          ('bwx12, bwx11, bwx', 'later runner programs for the same loops. They print one row per thread. bwx12 is the '
 589           'runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.'),
 590          ('Process, interval, round, position', 'a process is one start of a benchmark binary. An interval is one timed '
 591           'measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a '
 592           'round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In '
 593           'part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.'),
 594          ('Session', 'one pass of go.sh through part A, part L and part C.'),
 595          ('Part A', 'the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.'),
 596          ('Part L', 'one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.'),
 597          ('Part C', 'one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).'),</pre></td><td valign="top">Definitions of the machine, the kernels, the binaries and the parts of the run. All are fixed text. Only line 572 inserts a value: <code>mib</code>, the buffer size per thread. It comes from the P rows of the bwx12 files of the rerun (lines 376 and 377).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 598          ('Control I', 'the part L line, started from an idle machine, twice. It was %s. It is %s.' % (ADDED, NOT_PLAN)),
 599          ('Line, argument line', 'the arguments of one bwx12 process, as a spec file holds them. "The same line" means '
 600           'a process with the same arguments.'),
 601          ('Idle start', 'a launch at a 1-minute load average below 1.0.'),
 602          ('Visit', 'one time at which the same line was run. A later visit is the same line run again at a later time.'),
 603          ('State line', 'a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins '
 604           'and the processes per user.'),</pre></td><td valign="top">The entry for control I gets the two constants <code>ADDED</code> and <code>NOT_PLAN</code> (lines 24 and 25). The other entries of these lines are fixed text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 605          ('I, T, P, C rows', 'the row kinds of a bwx csv file: one I row per interval, one T row per thread and '
 606           'interval, one P row per thread before the first interval and after each interval (it holds the page state '
 607           'of the buffer), and one C row per thread and interval with counter values.'),
 608          ('Whole-pass stop', 'the stop rule of bandwidth.c: after the minimum time (%s here) each thread finishes '
 609           'the pass over its buffer that it is in. The threads stop at different times.' % secA),
 610          ('Common stop', 'the stop rule used with bwx12 here: all threads stop at the same time (after %s).' % secX),
 611          ('Pass count', 'total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread '
 612           'this is the number of buffer passes that all 120 threads completed in the interval. This sheet prints a pass '
 613           'count for these two kernels only. For copy and asmcopy the same division gives 2 x the number of buffer '
 614           'passes, because the binary counts read plus written bytes (header line of each process in threads120.csv: '
 615           '"copy counts read+write bytes"). facts.json holds that value in the field "passes".'),
 616          ('Rate, total', 'part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the '
 617           'threads of bytes / elapsed time. Unit GB/s.'),</pre></td><td valign="top">Entries on the row kinds of a bwx csv file (lines 605 to 607) and on how a rate is measured. They are fixed text with two values from the records.<ul><li>"Whole-pass stop" and "Common stop" (lines 608 to 610) say what ends a timed interval in part A and in the bwx12 parts.</li><li><code>secA</code>, <code>secX</code>: the interval lengths of part A and of the bwx12 parts, from the field <code>min_ms</code> of the records (lines 372 to 374).</li><li>"Pass count" (lines 611 to 615) says that copy and asmcopy count read plus written bytes.</li><li>"Rate, total" (lines 616 and 617) names the two sources of a rate. Part A: the column <code>aggregate_GBps</code> that the benchmark prints. bwx runners: the bytes of each thread are divided by the elapsed time of that thread and by 1e9, and the values of all threads are added [Ref2].</li><li>The entry does not give the formula of <code>aggregate_GBps</code>. The header line of each process in <code>threads120.csv</code> gives it: the sum of the bytes divided by the longest elapsed time of a thread [Ref7].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 618          ('Load average', 'the number of tasks that are runnable or wait for disk input and output, averaged by Linux '
 619           'over the last 1, 5 and 15 minutes (file /proc/loadavg %s). "Load at launch" is the 1-minute value read '
 620           'directly before a process starts. The fourth field of the file gives the tasks that are runnable now and '
 621           'the number of all tasks.' % ref('ext:proc5')),
 622          ('%CPU', 'the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time '
 623           'that a process has used, divided by the time since the process started %s. So it is an average over the '
 624           'life of the process. It is not the use at the moment of the reading.' % ref('ext:ps1')),
 625          ('pr/ttyAMA-1', 'a Linux kernel thread in the process lists. By its name it prints kernel messages to the '
 626           'serial console ttyAMA. This meaning was not checked on CRB.'),
 627          ('Boot id', 'a random identifier that Linux creates at each start. Equal boot ids mean the same boot.'),
 628          ('MemTotal', 'the usable memory that Linux reports, in kB.'),
 629          ('GiB', '2^30 bytes. A "32 GB" module holds 32 GiB %s.' % ref(fd.DIMM_REPORT)),
 630          ('Module list', 'the output of the command `dmidecode -t 17`, which prints the hardware table of the firmware. '
 631           'It holds one entry "Memory Device" per memory module: %d entries in the list saved in the boot of the rerun '
 632           '%s, and 10 entries in a 10-module boot by the DIMM report %s.'
 633           % (D['mod']['dmi']['devices'], ref(D['mod']['dmi']['path']), ref(fd.DIMM_REPORT))),
 634          ('Journal', 'the log store of Linux. It keeps the kernel log of earlier boots %s.' % ref(fd.DIMM_REPORT)),
 635          ('Hardware error record', 'a message that the firmware passes to Linux when hardware reports an error. Linux '
 636           'prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware '
 637           'repaired it) or "recoverable" (not repaired, the system continues) %s.' % ref(fd.DIMM_REPORT)),
 638          ('TXREQ settings', 'firmware settings that limit the read requests of the cores. They are not memory settings '
 639           '%s. The saved replies of the settings tool name two of them: "TXREQ Max" and "TXREQ Min" (section 1.5, '
 640           'point 13).' % ref(fd.DIMM_REPORT)),</pre></td><td valign="top">Entries about the machine state. Each <code>ref(...)</code> call inserts the reference number of a source: the manual pages for the load average and for <code>%CPU</code>, the DIMM report, and the saved module list. Line 633 inserts the number of "Memory Device" entries that <code>build_facts.py</code> counted in the module list [Ref1]. The other words are fixed text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 641          ('2 MiB pages', 'transparent huge pages. The "P" rows of bwx12 report how many kB of each buffer lie on them.'),
 642          ('Marker file', '`/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts '
 643           'stop when it exists.'),
 644          ('Governor', 'the Linux policy that sets the CPU frequency.'),
 645          ('rc', 'the exit status of a process. 0 means success.'),
 646          ('sha256', 'a checksum. Two files with the same sha256 have the same content.'),
 647          ('Baseline, like-for-like', 'an earlier 8000 MT/s run with 12 modules that used the same binary and method as '
 648           'a part of the rerun. The list was fixed before the run.'),
 649          ('Supporting row, other-binary row', 'earlier 8000 MT/s runs that differ in interval length or counter setup '
 650           '(supporting), or that used another runner binary (other binary).'),
 651          ('Ranges overlap', 'two min-to-max ranges share at least one value.'),
 652          ('n', 'the number of measurements that a range comes from. It is written as intervals / processes / sessions / '
 653           'boots (rule V1 point 1). "No session" marks a row that is not part of a session of go.sh.'),
 654          ('Pool', 'the intervals of several rows taken together as one range.'),
 655          ('Distance of the nearest ends', 'for two ranges that do not overlap: the lowest value of the higher range '
 656           'minus the highest value of the lower range.'),
 657          ('Rules V1 to V4, F1, F2', 'the comparison rules in `baselines-and-rules.txt`.'),
 658          ('FINDINGS.md', 'the facts sheet of the investigation of 2026-11-15 into the drop of the read rate.'),
 659          ('est.', 'estimated, not measured directly.'),
 660      ]</pre></td><td valign="top">The remaining entries are fixed text: 2 MiB pages, marker file, governor, rc, sha256, and the terms of the comparison rules (baseline, ranges overlap, n, pool, distance of the nearest ends).</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 661      wl_txt = fd._open(fd.DIMM_REPORT).read()
 662      need('A "32 GB" module holds 32 GiB.' in wl_txt
 663           and '- **Journal**: the log store of Linux. It keeps the kernel log of earlier boots.' in wl_txt
 664           and 'a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel '
 665               'log with the tag `[Hardware Error]`. Its severity is "corrected" (hardware repaired it) or "recoverable" '
 666               '(not repaired, system continues).' in wl_txt
 667           and '- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory '
 668               'settings.' in wl_txt
 669           and 'the table in which the firmware lists the hardware for the operating system. The command `dmidecode` '
 670               'prints it.' in wl_txt
 671           and '10 entries in a 10-module boot, 12 entries otherwise' in wl_txt,
 672           'DIMM report: the definitions that the word list quotes')</pre></td><td valign="top">Guard for the definitions that quote the DIMM report.<ul><li><code>fd._open</code> opens the report and adds its path to the list <code>OPENED</code> of facts_data.py. A guard near the end of <code>render</code> (line 1475) stops the script when an opened file is not in the file list of section 7.</li><li>The guard of these lines checks that six fixed texts are in the report, character by character. If one is missing, the script stops.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 673      for k, v in words:
 674          w('- **%s**: %s' % (k, v))
 675      w('')
 676      w('&lt;/details&gt;')
 677      w('')</pre></td><td valign="top">Writes one bullet line per entry, with the term in bold. Then it closes the block.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 678      w('The request of 2026-11-17: "Given that the DIMM issue is resolved at 7200 MT/s, let\'s rerun the whole chip '
 679        'test. Please run old kernel which used portable C code and had read and add, and run new kernel which '
 680        'performed worse than old kernel. Compare the results."')
 681      w('')
 682      w('- **Q1**: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below '
 683        'that of the old read kernel, and by how much.')
 684      w('- **Q2**: did either kernel\'s rate differ from the earlier runs with 12 modules at 8000 MT/s.')
 685      w('')
 686</pre></td><td valign="top">Writes the request of the user as a quote, and the two questions Q1 and Q2. All of it is fixed text.</td></tr>
<tr><td colspan="2"><b>Section 1.1: steps and times</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 687      # =============================================================================== 1
 688      w('## 1. Run record')
 689      w('')
 690      w('### 1.1 Steps and times')
 691      w('')
 692      w('- go.sh (the driver script) ran from %s to %s %s.' % (hm(go_start), hm(go_end), ref(go['path'])))
 693      w('- go2.sh (the control, added after the first numbers of parts A, L and C were seen, %s) ran from %s to %s %s.'
 694        % (NOT_PLAN, hm(go2_start), hm(go2_end), ref(go2['path'])))
 695      w('- One session is part A, then part L, then part C. Three sessions ran one after the other. A fourth part C '
 696        'process (T72C4) followed %s.' % ref(os.path.join(S, 'go.sh')))
 697      w('')</pre></td><td valign="top">Writes the headings of section 1 and of section 1.1, and three bullets.<ul><li><code>go_start</code>, <code>go_end</code>: the times of the first and the last state line of the go.sh log (line 371). <code>go2_start</code>, <code>go2_end</code>: the same for the go2.sh log (line 378).</li><li><code>hm</code> prints a time as <code>HH:MM:SS</code>. Each <code>ref(...)</code> call adds the reference number of a log or of go.sh.</li><li>The third bullet (lines 695 and 696) is fixed text about the order of the sessions.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 698      rows = []
 699      for e in ev:
 700          o = e['obj']
 701          if e['part'] == 'A':
 702              what = 'part A, session %d: 24 processes of bw_old and bw_new' % e['session']
 703              src = '%s %s' % (ref(o['csv']), ref(o['probe']['path']))
 704              last = hm(e['last'])
 705          else:
 706              what = {'L': 'part L', 'C': 'part C (%s)' % o['spec'], 'I': 'control I (%s)' % ADDED}[e['part']]
 707              what += (', session %d' % e['session']) if e['part'] in 'LC' and e['session'] else ''
 708              what += ': 1 process of bwx12'
 709              src = ref(os.path.join(o['folder'], 'launches.txt'))
 710              last = '-'
 711          rows.append([e['tag'], what, hm(e['start']), hm(e['first']), last, hm(e['end']),
 712                       '-' if e['gap_s'] is None else '%.0f' % e['gap_s'], src])
 713      L.extend(table(['Folder tag', 'What ran', 'Script start', 'First process launch', 'Last process launch',
 714                      'End of last process', 'Gap before the first launch, s', 'Source'], rows))</pre></td><td valign="top">Builds one table row per step and adds the table with <code>table</code> (line 132). <code>ev</code> holds the steps in the order of their first launch [Ref1]. <code>o</code> is the folder record of the step.<ul><li>Part A step: the text names the session and the count of 24 processes, which is fixed text. The sources are <code>threads120.csv</code> and probe.txt. <code>last</code> is the launch time of the last process.</li><li>bwx12 step: the text is part L, part C with the name of its spec file, or control I. A session number is added only for a part L or part C step that has one. The source is launches.txt. <code>last</code> is <code>-</code>.</li><li>Line 711: <code>e['start']</code> is the time in the folder name. <code>e['first']</code> is the first launch. <code>e['end']</code> is the end of the last process.</li><li>Line 712: the gap in whole seconds, or <code>-</code> when the step has none.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 715      w('- "Script start" is the time in the folder name. ra.sh and rx.sh take it when they start.')
 716      w('- "End of last process" is the `load_after` line of probe.txt for part A. For bwx12 it is the `rc` line of '
 717        'launches.txt.')
 718      w('- "Gap" is the first launch minus the end of the previous 120-thread process of the rerun.')
 719      w('- The time stamps have a resolution of 1 s. rx.sh checks once per second whether its process still runs %s. '
 720        'So a gap can be up to 2 s longer than the value shown (est.).' % ref(os.path.join(W15, 'rx.sh')))
 721      w('- T72A1 has no gap value. It was the first step, and the three load averages at its start were %.2f, %.2f and '
 722        '%.2f %s.' % (go['states'][0]['load1'], go['states'][0]['load5'], go['states'][0]['load15'], ref(go['path'])))
 723      w('')
 724</pre></td><td valign="top">Writes five notes under the table.<ul><li>Lines 715 to 718: three notes of fixed text. They say where the columns "Script start", "End of last process" and "Gap" come from.</li><li>Lines 719 and 720: a note on the 1 s resolution of the time stamps, with the reference number of rx.sh.</li><li>Lines 721 and 722: T72A1 has no gap. The note prints the three load averages of the first state line of the go.sh log, each with 2 decimals.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 1.2: machine state and its proof</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 725      # ---- 1.2
 726      w('### 1.2 Machine state and its proof')
 727      w('')
 728      w('The table lists every state line of the two logs and the two state lines of every probe.txt.')
 729      w('')
 730      rows = []
 731</pre></td><td valign="top">Writes the heading and one line of introduction. The list <code>rows</code> of line 730 is not used in this section. Line 854 gives the name a new list.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 732      def procs_str(p):
 733          other = {k: v for k, v in p.items() if k not in ('jhan', 'root')}
 734          return 'jhan %d, root %d, %d system accounts with %d processes' % (p.get('jhan', 0), p.get('root', 0), len(other),
 735                                                                         sum(other.values()))</pre></td><td valign="top"><code>procs_str</code> turns the process counts per user of one state line into text. <code>p</code> maps a user name to a number of processes. The text gives the count of <code>jhan</code>, the count of <code>root</code>, the number of other accounts and the sum of their processes.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 736      ra_txt = fd._open(os.path.join(S, 'ra.sh')).read()
 737      ra_limit, ra_sleep = re.search(r'\$r -le (\d+)', ra_txt)[1], re.search(r'^sleep (\d+)', ra_txt, re.M)[1]</pre></td><td valign="top">Reads the text of ra.sh (the script of part A) and takes two numbers out of it with regular expressions.<ul><li><code>ra_limit</code>: the number after <code>$r -le</code>. The wait loop of ra.sh ends when the count of runnable tasks is at or below it.</li><li><code>ra_sleep</code>: the number in the first line that starts with <code>sleep</code>. ra.sh waits this number of seconds after the loop.</li><li>The lines below use <code>ra_sleep</code>. Section 1.5 uses <code>ra_limit</code> (line 950).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 738      statelist = []
 739      for lg in (go, go2):
 740          for s_ in lg['states']:
 741              statelist.append((s_['utc'], [os.path.basename(lg['path']).split('-')[0] + ' log, line %d: %s' % (s_['line'], s_['label']),
 742                                hm(s_['utc']), s_['boot'][:8], s_['memtotal_kB'],
 743                                '%.2f / %.2f / %.2f' % (s_['load1'], s_['load5'], s_['load15']),
 744                                '%d / %d' % (s_['runnable'], s_['tasks']), s_['logins'], s_['marker'], procs_str(s_['procs'])]))</pre></td><td valign="top">Collects the state lines of the two logs. <code>go</code> and <code>go2</code> hold the parsed logs of go.sh and go2.sh. Each entry of <code>statelist</code> is a pair: the time of the line, and its table row. The row holds the log name with line number and label, the time, the first 8 characters of the boot id, MemTotal, the three load averages, runnable tasks / all tasks, the logins, the state of the marker file, and the text of <code>procs_str</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 745      for a_ in A:
 746          p = a_['probe']
 747          statelist.append((p['utc'], ['probe.txt of %s, start' % a_['tag'], hm(p['utc']), p['boot'][:8], p['memtotal_kB'],
 748                                       '%.2f / %.2f / %.2f' % p['load_before'],
 749                                       '%d (read at least %s s before this time) / not recorded' % (p['runnable'], ra_sleep),
 750                                       p['logins'],
 751                                       'not recorded', 'not recorded']))
 752          statelist.append((p['utc_after'], ['probe.txt of %s, end' % a_['tag'], hm(p['utc_after']), 'not recorded', p['memtotal_after_kB'],
 753                                             '%.2f / %.2f / %.2f' % p['load_after'], 'not recorded', 'not recorded', 'not recorded',
 754                                             'not recorded']))</pre></td><td valign="top">Adds two rows per part A folder from its probe.txt.<ul><li>Start row: time, boot id, MemTotal, load averages and logins of the first probe lines. The runnable count gets the note that it was read at least <code>ra_sleep</code> seconds before this time.</li><li>End row: time, MemTotal and load averages of the <code>load_after</code> line.</li><li>A value that probe.txt does not hold is written as <code>not recorded</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 755      statelist.sort(key=lambda t: t[0])
 756      L.extend(table(['State line', 'Time', 'Boot id, first 8 characters', 'MemTotal, kB', 'Load average 1 / 5 / 15 min',
 757                      'Runnable / all tasks', 'Logins', 'Marker file', 'Processes per user'], [r for _, r in statelist]))</pre></td><td valign="top">Sorts all rows by their time and adds the table. The sort of Python keeps the order of insertion for rows with the same time. So a log row stands before a probe.txt row of the same second.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 758      sysacc = sorted({k for s_ in go['states'] + go2['states'] for k in s_['procs'] if k not in ('jhan', 'root')})
 759      users = sorted({k for s_ in go['states'] + go2['states'] for k in s_['procs']})
 760      nst = len(go['states']) + len(go2['states'])
 761      w('- **Boot.** All %d state lines and all %d probe.txt files hold the full boot id `%s`. This is the boot id in '
 762        'line 2 of try6.txt %s.' % (nst, len(A), try6['boot'], ref(try6['path'])))
 763      w('- **12 modules.** MemTotal is %d kB in every line of the table. try6.txt holds the same value in line %d and '
 764        'the kernel message "This system has %d DIMM sockets" in line %d %s.'
 765        % (try6['memtotal_kB'], try6['memtotal_line'], try6['dimm_sockets'], try6['dimm_line'], ref(try6['path'])))</pre></td><td valign="top"><ul><li><code>sysacc</code>: the user names other than <code>jhan</code> and <code>root</code> that own processes in a state line. <code>users</code>: all user names. <code>nst</code>: the number of state lines of both logs.</li><li>Lines 761 and 762 write the bullet on the boot id. The full boot id comes from try6.txt.</li><li>Lines 763 to 765 write the bullet on the 12 modules: MemTotal, its line number in try6.txt, the number in the kernel message and its line number.</li><li>The words "all" and "in every line" are fixed text. The integrity checks <code>boot</code> and <code>memtotal</code> of <code>build_facts.py</code> test them [Ref1]. A guard in <code>section4</code> stops the script when a check failed [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 766      md = D['mod']
 767      dimm_txt = fd._open(fd.DIMM_REPORT).read()
 768      b10 = [b for b in D['boot_table']['boots'] if b['start'].strftime('%Y-%m-%d %H:%M') == md['h1_start'].strftime('%Y-%m-%d %H:%M')]
 769      need(len(b10) == 1 and b10[0]['modules'] == md['h1_dimm'] == 10 and p13['boot_dimm'] == 12,
 770           'the journal h-1.txt is the 10-module boot of the DIMM report, the journal h-5.txt a 12-module boot')
 771      need('The module count comes from the kernel line `ghes_edac: This system has N DIMM sockets`' in dimm_txt
 772           and 'differs by exactly 64 GiB between the two states. That equals two modules.' in dimm_txt
 773           and 'CRB has 12 memory modules of 32 GiB each.' in dimm_txt
 774           and 'sudo dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c' in dimm_txt,
 775           'DIMM report: source of the module count, the 64 GiB step, the module size, the command of the speed line')
 776      need(md['k-1']['stamp'] == md['h1_start'].strftime('%b %d %H:%M:%S')
 777           and md['k-5']['stamp'] == p13['boot_start'].strftime('%b %d %H:%M:%S'),
 778           'the "Memory:" lines belong to the boots of the two journals')
 779      need(md['k-5']['total_K'] - md['k-1']['total_K'] == 64 * 1024 * 1024, 'the two totals differ by 64 x 1024 x 1024 K')
 780      dm = md['dmi']
 781      need(dm['devices'] == dm['speed'] == dm['size'] == dm['volatile'] == try6['speed_count'] == 12
 782           and dm['size_any'] == dm['size'] + dm['volatile'] == md['try6_modules'],
 783           'module list of the boot of the rerun: 12 entries, 24 lines with the text "Size: 32 GB"')
 784      need(try6['boots_first'] &lt;= dm['mtime'] &lt;= try6['boots_last'], 'file time of the module list inside row 0 of boots.txt')</pre></td><td valign="top">Loads the data for the proof of the module count and runs six guards. <code>md</code> holds values that <code>build_facts.py</code> read from the saved journal h-1.txt, two kernel logs, the module list and try6.txt [Ref1].<ul><li>Line 769: the boot table of the DIMM report lists exactly one boot with the start minute of the journal h-1.txt. Both sources give 10 modules for it. The journal h-5.txt gives 12.</li><li>Lines 771 to 775: four fixed texts stand in the DIMM report.</li><li>Lines 776 to 778: the "Memory:" line of each kernel log carries the start time of the journal of the same boot (h-1.txt or h-5.txt).</li><li>Line 779: the two totals differ by exactly 64 x 1024 x 1024 K.</li><li>Lines 781 to 783: the module list holds 12 entries, 12 speed lines and 12 lines of each of the two size kinds. The speed line of try6.txt gives 12 too. The count of all size lines equals the value <code>modules=</code> of try6.txt.</li><li>Line 784: the file time of the module list lies inside the time span of row 0 of boots.txt.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 785      w('- **Why these two values mean 12 modules.** The number in the kernel message is the number of modules that the '
 786        'firmware reports. It is not the number of slots of the board. The saved journal of the boot that started on %s '
 787        'reads "This system has %d DIMM sockets" in line %d %s. The DIMM report lists that boot with %d modules. It '
 788        'takes the module count of every boot from this kernel line (its section 3) %s.'
 789        % (hmd(md['h1_start']), md['h1_dimm'], md['h1_dimm_line'], ref(md['h1']), b10[0]['modules'], ref(fd.DIMM_REPORT)))
 790      w('- **Direct count.** Line %d of try6.txt reads "%d Configured Memory Speed: %d MT/s" %s. The first number is the '
 791        'number of lines with this text in the module list, one line per module. The DIMM report gives the command: '
 792        '`dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c` (its section 6.3) %s. The module list that '
 793        'was saved later in the same boot has the file time %s. That is inside the span of row 0 of boots.txt %s. It '
 794        'holds %d entries "Memory Device" and %d lines "Configured Memory Speed: %d MT/s" %s.'
 795        % (try6['speed_line'], try6['speed_count'], try6['speed_MTps'], ref(try6['path']), ref(fd.DIMM_REPORT),
 796           hm(dm['mtime']), ref(try6['boots_path']), dm['devices'], dm['speed'], try6['speed_MTps'], ref(dm['path'])))</pre></td><td valign="top">Writes two bullets.<ul><li>Lines 785 to 789: why the kernel message proves the module count. The values are the start of the 10-module boot (<code>hmd</code> prints date and time), its module count, the line number in the journal, and the count from the boot table.</li><li>Lines 790 to 796: the direct count. The values are the speed line of try6.txt, the file time of the module list, and the counts of its "Memory Device" entries and of its speed lines.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 797      w('- **Memory size.** With 1 kB = 1024 bytes, %d kB are %s GiB. 12 modules of 32 GiB are 384 GiB %s. The kernel '
 798        'log of the 12-module boot of 2026-11-09 holds the line "Memory: %dK/%dK available" (line %d %s). The kernel log '
 799        'of the 10-module boot named above holds "Memory: %dK/%dK available" (line %d %s). The second numbers of the '
 800        'two lines differ by %d K. That is 64 x 1024 x 1024 K. The DIMM report reads this as exactly 64 GiB, the size '
 801        'of two modules %s.'
 802        % (try6['memtotal_kB'], g(try6['memtotal_kB'] / 1024 / 1024), ref(fd.DIMM_REPORT), md['k-5']['avail_K'],
 803           md['k-5']['total_K'], md['k-5']['line'], ref(md['k-5']['path']), md['k-1']['avail_K'], md['k-1']['total_K'],
 804           md['k-1']['line'], ref(md['k-1']['path']), md['k-5']['total_K'] - md['k-1']['total_K'], ref(fd.DIMM_REPORT)))
 805      w('- Line %d of try6.txt reads "modules=%d". This is not the module count. The module list holds %d lines that '
 806        'contain the text "Size: 32 GB": %d lines "Size: 32 GB" and %d lines "Volatile Size: 32 GB" %s. Hypothesis, not '
 807        'checked: the script that wrote try6.txt counted these %d lines. That script is not among the files of this '
 808        'task.' % (md['try6_modules_line'], md['try6_modules'], dm['size_any'], dm['size'], dm['volatile'], ref(dm['path']),
 809                   dm['size_any']))</pre></td><td valign="top"><ul><li>Lines 797 to 804: the bullet on the memory size. <code>g(try6['memtotal_kB'] / 1024 / 1024)</code> converts MemTotal from kB to GiB and prints 2 decimals. The other values are the two numbers and the line number of each "Memory:" line, and the difference of the two totals.</li><li>The date 2026-11-09 and the value 384 GiB in this bullet are fixed text.</li><li>Lines 805 to 809: the bullet on the line <code>modules=</code> of try6.txt. It prints the three counts of the size lines of the module list. The hypothesis in it is fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 810      w('- **7200 MT/s.** Line %d of try6.txt reads "%d Configured Memory Speed: %d MT/s". It was recorded at %s in the '
 811        'same boot %s. The speed was not read again during the rerun, because that needs root. The proof for the '
 812        'rerun is the equal boot id. Assumption, not measured: the speed does not change inside one boot. The firmware '
 813        'applies the setting at the next start %s.'
 814        % (try6['speed_line'], try6['speed_count'], try6['speed_MTps'], hm(try6['utc']), ref(try6['path']), ref(fd.DIMM_REPORT)))
 815      w('- **Time since boot.** The first kernel log line of this boot is from %s %s. go.sh started %s later.'
 816        % (hm(try6['first_log_utc']), ref(try6['gaps_path']), dur((go_start - try6['first_log_utc']).total_seconds())))
 817      w('- **Linux kernel command line** (line %d of the go.sh log %s): `%s`'
 818        % (go['other']['cmdline'][1], ref(go['path']), go['other']['cmdline'][0]))</pre></td><td valign="top">Three bullets.<ul><li>Lines 810 to 814: the memory speed. Line number, count and speed come from the speed line of try6.txt. <code>hm(try6['utc'])</code> is the time in the first line of try6.txt. The assumption that the speed does not change inside one boot is fixed text.</li><li>Lines 815 and 816: the time since boot. It is the start of go.sh minus the time of the first kernel log line of this boot. <code>dur</code> prints it as hours, minutes and seconds.</li><li>Lines 817 and 818: the Linux kernel command line and its line number in the go.sh log.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 819      gv = go['other']['governors'][0]
 820      gov = re.findall(r'(\d+) (\w+);', gv)
 821      cur = int(re.search(r'scaling_cur_freq (\d+)', gv)[1])
 822      need(len(gov) == 1, 'one governor value')
 823      w('- **Governor.** %s of the CPUs 0-119 use the governor "%s". `scaling_cur_freq` of CPU 0 was %d (line %d of the '
 824        'go.sh log %s). The unit of that file is kHz %s, so the value is %.1f GHz.'
 825        % (gov[0][0], gov[0][1], cur, go['other']['governors'][1], ref(go['path']), ref('ext:cpufreq'), cur / 1e6))
 826      thp = re.match(r'thp enabled (.*) defrag (.*)', go['other']['thp'][0])
 827      w('- **Huge page setting.** `transparent_hugepage/enabled` = `%s`. `defrag` = `%s` (line %d of the go.sh log %s). '
 828        'The value in brackets is the active one.' % (thp[1], thp[2], go['other']['thp'][1], ref(go['path'])))</pre></td><td valign="top"><ul><li><code>gv</code> is the governors line of the go.sh log. <code>gov</code> holds every pair of a CPU count and a governor name in it. <code>cur</code> is the number after <code>scaling_cur_freq</code>.</li><li>The guard of line 822 checks that the line names one governor only.</li><li>Lines 823 to 825 print the count, the governor and <code>cur</code>. <code>cur / 1e6</code> converts kHz to GHz, printed with 1 decimal.</li><li>Lines 826 to 828 split the huge page line of the log into the values of <code>enabled</code> and <code>defrag</code> and print both.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 829      w('- **Runnable tasks in probe.txt.** ra.sh reads the value in its wait loop, then sleeps %s s, and then writes '
 830        'the probe line with a new time and a new load average %s. So the value %s is from at least %s s before the '
 831        'time shown in the table. The count at the first launch of part A is not recorded.'
 832        % (ra_sleep, ref(os.path.join(S, 'ra.sh')), '/'.join(sorted({str(a_['probe']['runnable']) for a_ in A})), ra_sleep))
 833      w('- **Logins.** Every state line shows 0 logins. Every probe.txt and every launch line of rx.sh shows 0 logins too.')
 834      w('- **Processes per user.** Only these users own processes in the %d state lines: %s. No other user appears.'
 835        % (nst, ', '.join(users)))
 836      jh = sorted({s_['procs'].get('jhan', 0) for s_ in go['states'] + go2['states']})
 837      rt = [s_['procs'].get('root', 0) for s_ in go['states'] + go2['states']]
 838      w('- The user jhan owns %s processes in every state line. root owns %d to %d. The %d system accounts own 1 each.'
 839        % ('/'.join(map(str, jh)), min(rt), max(rt), len(sysacc)))
 840      w('- **Marker file.** It is "absent" in all %d state lines.' % nst)
 841      w('- **CPU affinity of go.sh.** `%s` (line %d of the go.sh log %s).'
 842        % (go['other']['affinity'][0], go['other']['affinity'][1], ref(go['path'])))
 843      w('- **Hardware error records.** The kernel log was not read during or after the rerun (no root). try6.txt shows '
 844        '`hwerr=%d` at %s, at the start of this boot %s.' % (try6['hwerr'], hm(try6['utc']), ref(try6['path'])))
 845      w('')
 846</pre></td><td valign="top">The remaining bullets of section 1.2.<ul><li>Lines 829 to 832: the runnable count of probe.txt. The values are <code>ra_sleep</code> and the distinct counts of the probe.txt files.</li><li>Line 833 is fixed text about the logins. Line 840 says that the marker file is absent in all <code>nst</code> state lines. The integrity check <code>logins</code> of <code>build_facts.py</code> tests both statements [Ref1].</li><li>Lines 834 to 839: the users that own processes. <code>jh</code> holds the distinct counts of <code>jhan</code>. <code>rt</code> holds the count of <code>root</code> per state line, and the text prints its lowest and its highest value.</li><li>The words "own 1 each" of line 838 are fixed text. No <code>need</code> call and no integrity check tests them.</li><li>Lines 841 to 844: the CPU affinity line of the go.sh log, and the value <code>hwerr=</code> of try6.txt with its time.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 1.3: system load at every launch</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 847      # ---- 1.3
 848      w('### 1.3 System load at every launch')
 849      w('')
 850      w('The value is the 1-minute load average of Linux, read by the run script directly before it starts a process.')
 851      w('')
 852      w('Part A. ra.sh writes the value into the "-- binary" line of each of the 24 processes.')
 853      w('')</pre></td><td valign="top">Writes the heading and two lines of fixed text. The first says where the load value comes from: the run script reads the 1-minute load average directly before it starts a process. The second says that ra.sh writes the value into the "-- binary" line of each process.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 854      rows = []
 855      for a_ in A:
 856          ls = [p['load1'] for p in a_['procs']]
 857          pr = a_['probe']
 858          rows.append([a_['tag'], '%.2f / %.2f / %.2f' % pr['load_before'], pr['runnable'], '%.2f' % ls[0], '%.2f' % min(ls),
 859                       '%.2f' % max(ls), len(ls), '%.2f / %.2f / %.2f' % pr['load_after'], pr['pcpu_max'],
 860                       '%s %s' % (ref(a_['csv']), ref(pr['path']))])
 861      L.extend(table(['Session', 'Load average 1 / 5 / 15 min before the first process (probe.txt)',
 862                      'Runnable tasks at the end of the wait of ra.sh (at least %s s before the probe line)' % ra_sleep,
 863                      'Load at the first process', 'Lowest load of the 24 launches', 'Highest load of the 24 launches',
 864                      'Launches', 'Load average after the last process', 'Highest %CPU in the process list of probe.txt', 'Source'], rows))</pre></td><td valign="top">The table of part A: one row per session. <code>ls</code> holds the load at launch of each process of the session, from its header line in <code>threads120.csv</code>. The row gives the three load averages of probe.txt before the first process, the runnable count, the load at the first launch, the lowest and the highest load of all launches, the number of launches, the three load averages after the last process, and the highest <code>%CPU</code> of the process list in probe.txt.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 865      w('Parts L and C and control I. rx.sh writes the value into the launch line of launches.txt.')
 866      w('')
 867      rows = []
 868      for x in sorted(X, key=lambda x: x['launches'][0]['utc']):
 869          la = x['launches'][0]
 870          rows.append([x['tag'], hm(la['utc']), '%.2f' % la['load1'], '%.2f' % la['load5'], '%.2f' % la['load15'],
 871                       '%d / %d' % (la['runnable'], la['tasks']), la['logins'], x['env']['pcpu_max'],
 872                       '%s, process list %s' % (ref(os.path.join(x['folder'], 'launches.txt')), ref(os.path.join(x['folder'], 'env.txt')))])
 873      L.extend(table(['Folder tag', 'Launch', 'Load 1 min', 'Load 5 min', 'Load 15 min', 'Runnable / all tasks', 'Logins',
 874                      'Highest %CPU in the process list of env.txt', 'Source'], rows))</pre></td><td valign="top">The table of the bwx12 steps: one row per folder of parts L and C and of control I, in the order of the launch time. <code>la</code> is the launch line of launches.txt. The row gives the launch time, the three load averages, runnable tasks / all tasks, the logins, and the highest <code>%CPU</code> of the process list in env.txt.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 875      hi = [x for x in X if x['launches'][0]['load1'] &gt;= 1.0]
 876      lo = [x for x in X if x['launches'][0]['load1'] &lt; 1.0]
 877      need({x['part'] for x in lo} == {'I'} and len(lo) == 2, 'only control I started below load 1.0')
 878      s1l = [p['load1'] for p in A[0]['procs']]
 879      rest = [p['load1'] for a_ in A[1:] for p in a_['procs']] + [x['launches'][0]['load1'] for x in hi]
 880      need(s1l == sorted(s1l), 'load rises from process to process in session 1')
 881      w('- In session 1 of part A the load at launch rose from %.2f at the first process to %.2f at the last process.'
 882        % (s1l[0], s1l[-1]))
 883      w('- All launches of sessions 2 and 3 of part A and all launches of parts L and C saw a load of %.2f to %.2f.'
 884        % (min(rest), max(rest)))
 885      w('- The two launches of control I started at a load of %s.' % ' and '.join('%.2f' % x['launches'][0]['load1'] for x in lo))
 886      need({x['launches'][0]['runnable'] for x in X} == {1}, '1 runnable task at every bwx12 launch')
 887      w('- At every bwx12 launch 1 task was runnable (launch line of launches.txt).')</pre></td><td valign="top">Notes on the load, with their guards.<ul><li><code>hi</code>, <code>lo</code>: the bwx12 steps with a load at launch of 1.0 or more, and below 1.0. The guard of line 877 checks that <code>lo</code> holds exactly the two control I steps.</li><li><code>s1l</code>: the loads of the launches of session 1 of part A, in file order. The guard of line 880 checks that the load never falls from one launch to the next.</li><li><code>rest</code>: the loads of all launches of sessions 2 and 3 of part A and of the steps in <code>hi</code>. Lines 883 and 884 print the lowest and the highest. Line 885 prints the loads of the steps in <code>lo</code>.</li><li>The guard of line 886 checks that exactly 1 task was runnable at every bwx12 launch.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 888      envgap = sorted({(x['launches'][0]['utc'] - x['env']['start']).total_seconds() for x in X})
 889      need(min(envgap) &gt; 0, 'env.txt written before the launch')
 890      w('- The process lists of env.txt show at most %s %%CPU. rx.sh writes env.txt when it starts %s. That was %s s '
 891        'before each of the %d launches (first line of env.txt against the launch line). %%CPU is an average over the '
 892        'life of a process (see the word list). So the lists would show a new busy process. They cannot show a short '
 893        'busy phase of a process that has run since the boot.'
 894        % (max(x['env']['pcpu_max'] for x in X), ref(os.path.join(W15, 'rx.sh')),
 895           ' to '.join('%.0f' % v for v in sorted({envgap[0], envgap[-1]})), len(X)))
 896      w('- The process lists of probe.txt (part A) were written at the time of the probe line, directly before the '
 897        'first process %s. The same limit of %%CPU holds for them.' % ref(os.path.join(S, 'ra.sh')))</pre></td><td valign="top"><ul><li><code>envgap</code>: for each bwx12 step, the launch time minus the time in the first line of env.txt, in seconds. The guard checks that every value is above 0. So env.txt was written before the launch.</li><li>Lines 890 to 895 print the highest <code>%CPU</code> of all env.txt files, the smallest and the largest of these differences, and the number of launches. The rest is fixed text about the limit of <code>%CPU</code>.</li><li>Lines 896 and 897: fixed text about the process lists of probe.txt, with the reference number of ra.sh.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 898      ev_near = [e for e in ev if e['gap_s'] is not None and e['part'] != 'I']      # steps of go.sh after the first one
 899      ev_far = [e for e in ev if e['part'] == 'I']                                  # the two control steps of go2.sh
 900      need(ev[0]['gap_s'] is None and ev[0]['tag'] == 'T72A1' and len(ev_near) + len(ev_far) + 1 == len(ev)
 901           and max(e['gap_s'] for e in ev_near) &lt; 10 &lt; min(e['gap_s'] for e in ev_far),
 902           'gaps: the first step has none, the other steps of go.sh have a short one, the control steps a long one')
 903      w('- Hypothesis: the high load values come from the rerun\'s own 120-thread processes. Linux averages the load '
 904        'over the last 1, 5 and 15 minutes %s, so the value stays high for some time after a process ends. The first '
 905        'launch of each of the %d steps from %s to %s came %s s after such an end (table of section 1.1). %s had no '
 906        'earlier process of the rerun (load %.2f at launch). %s came %s s after one (load %s at launch). The later '
 907        'launches of part A followed the previous part A '
 908        'process with no wait %s. The runnable counts and the 0 logins fit this. The process lists cannot test it (see '
 909        'the limit of %%CPU above). A check that would confirm or reject it: sample /proc/loadavg and the list of '
 910        'running processes once per second between two steps. This was not done.'
 911        % (ref('ext:proc5'), len(ev_near), ev_near[0]['tag'], ev_near[-1]['tag'],
 912           ' or '.join('%.0f' % v for v in sorted({e['gap_s'] for e in ev_near})), ev[0]['tag'], ev[0]['load1'],
 913           ' and '.join(e['tag'] for e in ev_far), ' s and '.join('%.0f' % e['gap_s'] for e in ev_far),
 914           ' and '.join('%.2f' % e['load1'] for e in ev_far), ref(os.path.join(S, 'ra.sh'))))
 915      w('')
 916</pre></td><td valign="top">The hypothesis on the high load values.<ul><li><code>ev_near</code>: the steps that have a gap and are not control I. <code>ev_far</code>: the control I steps.</li><li>The guard of lines 900 to 902 checks four things. The first step is T72A1 and has no gap. The two lists hold all other steps. Every gap in <code>ev_near</code> is below 10 s. Every gap in <code>ev_far</code> is above 10 s.</li><li>Lines 903 to 914 write the bullet. The values are the number of steps in <code>ev_near</code>, their first and last tag, their distinct gaps, the load of the first step, and the tags, gaps and loads of the control I steps.</li><li>The hypothesis and the check that would test it are fixed text.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 1.4: integrity checks</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 917      # ---- 1.4
 918      w('### 1.4 Integrity checks')
 919      w('')
 920      for i, c in enumerate(D['checks'], 1):
 921          w('%d. %s: %s.' % (i, 'pass' if c['ok'] else 'FAILED', c['text']))
 922      w('')</pre></td><td valign="top">Writes one numbered line per integrity check of <code>D['checks']</code>: the number, <code>pass</code> or <code>FAILED</code>, and the text of the check.<ul><li><code>build_facts.py</code> ran the checks before it called <code>render</code> [Ref1].</li><li>Three checks test the rates. One compares the rate from the T rows (the sum of the thread rates) with <code>aggregate_GBps</code> of the I row of the same interval. Its pass limit is a difference below 0.05 GB/s. It covers only the 9 bwx12 files of the rerun. Two compare the intervals with the output of stat_k120.py and stat_bwx.py (two earlier analysis scripts in <code>S</code>).</li><li>A guard in <code>section4</code> stops the script when a check failed [Ref3]. So a sheet that was written shows <code>pass</code> in every line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 923      w('- Were the buffers on 2 MiB pages? Parts L, C and I: yes. Every "P" row shows the whole buffer (%s kB) on huge '
 924        'pages (check %d). Part A: not recorded. bandwidth.c prints only the setting `thp=madvise` in its header line.'
 925        % ('/'.join(map(str, D['P_kB'])), [c['key'] for c in D['checks']].index('P-rows') + 1))
 926      w('')
 927</pre></td><td valign="top">Writes the bullet on 2 MiB pages.<ul><li><code>D['P_kB']</code>: the distinct buffer sizes in kB of the P rows. The guard of line 376 allows one value only.</li><li>The check number is the place of the check <code>P-rows</code> in the list, counted from 1. That check tests the fixed words that every P row shows the whole buffer on huge pages [Ref1].</li><li>For part A the bullet says in fixed text that the page state was not recorded.</li><li>The function <code>render</code> continues with section 1.5 at line 928. It ends at line 1488.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 1.5: differences between the 2026-11-13 procedure and part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 928      # ---- 1.5
 929      a1p = D['base']['A-1']['procs']
 930      a1first = fd.clock(D['base']['A-1']['folder'], a1p[0]['utc'])
 931      w('### 1.5 Limits: differences between the procedure of 2026-11-13 and part A')
 932      w('')
 933      w('The timed part is the same: same two binaries (check %d), same arguments (check %d), same order of the 24 '
 934        'processes (check %d). The list below holds the differences that were found. It is not proven to be complete. '
 935        'Point 12 holds the Linux settings that were compared without a difference. Point 13 holds what is on record '
 936        'about the firmware settings. The list follows findings F9 and F1 of the review %s.'
 937        % ([c['key'] for c in D['checks']].index('sha-bw') + 1, [c['key'] for c in D['checks']].index('A-args') + 1,
 938           [c['key'] for c in D['checks']].index('A-order') + 1, ref(os.path.join(S, 'review-w1.json'))))
 939      w('')</pre></td><td valign="top">These lines continue the function <code>render</code> that starts at line 341. They write the heading and the first paragraph of section 1.5.<ul><li><code>a1p</code> is the list of the processes of baseline A-1, read from <code>threads120.csv</code> of the run of 2026-11-13.</li><li><code>a1first</code> is the launch time of its first process.</li><li>The three check numbers in that paragraph are the places of the checks <code>sha-bw</code>, <code>A-args</code> and <code>A-order</code> in the list <code>D['checks']</code>, counted from 1 as in section 1.4.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 940      OTHER_DAY.update([p13['one_first'], p13['one_last']])      # printed below with the date in the same sentence
 941      need(fd.folder_date(D['base']['A-1']['folder']).strftime('%Y-%m-%d') == '2026-11-13', 'date of the A-1 folder')
 942      w('1. **One-thread phase.** On 2026-11-13 the script first ran %d one-thread processes, from %s to %s %s. The '
 943        'first 120-thread process started at %s with a load of %.2f %s. Part A has no one-thread phase.'
 944        % (p13['one_n'], p13['one_first'], p13['one_last'], ref(p13['one_path']), hmd(a1first), a1p[0]['load1'],
 945           ref(os.path.join(D['base']['A-1']['folder'], 'threads120.csv'))))</pre></td><td valign="top">Point 1, the one-thread phase (the part of the 2026-11-13 run with one thread per process, before the 120-thread part).<ul><li>Line 940 adds the first and the last launch time of that phase to the set <code>OTHER_DAY</code>. These two times are text from the csv. The function <code>hmd</code> (line 72), which adds a time of another day to this set, does not format them.</li><li>The guard in line 941 checks that the folder name of A-1 holds the date 2026-11-13. The template states that date as fixed text.</li><li>The sentence prints the number of one-thread processes. build_facts.py counted the <code>-- binary</code> header lines of <code>one-thread.csv</code> for it.</li><li>It also prints <code>a1first</code> and the 1-minute load average from the header line of that process.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 946      w('2. **Start state of the sessions.** Session 1 %s. Session 2 %s. Session 3 %s.'
 947        % (evd['T72A1']['state'], evd['T72A2']['state'], evd['T72A3']['state']))
 948      w('3. **Wait before the first process.** ra.sh waits until %s or fewer tasks are runnable and then sleeps %s s %s. '
 949        'The script of 2026-11-13 built the binaries, ran a self-test and the one-thread phase, and had no wait %s.'
 950        % (ra_limit, ra_sleep, ref(os.path.join(S, 'ra.sh')), ref(os.path.join(K13, 'run_kernels.sh'))))
 951      w('4. **Memory speed.** 8000 MT/s then, 7200 MT/s now. This is the intended change.')</pre></td><td valign="top">Points 2 to 4.<ul><li>Point 2 prints the start state of the three part A sessions from <code>evd</code>, which holds the steps of the run by folder tag.</li><li>Point 3 prints <code>ra_limit</code> and <code>ra_sleep</code>. Line 737 took both numbers from the text of ra.sh: the highest count of runnable tasks at which the wait ends, and the sleep after the wait in seconds.</li><li>The second sentence of point 3 says that the script of 2026-11-13 built the binaries, ran a self-test and the one-thread phase, and had no wait. It is fixed text. No guard in this file checks it. The local copy of that script (run_kernels.sh) agrees with it. It runs the build, the self-test, the one-thread phase and the 120-thread part in this order, and it holds no <code>sleep</code> command and no wait loop.</li><li>Point 4 is fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 952      # records of the same journal during the baselines A-2 and A-3 (one record = one line "Hardware error from APEI ...")
 953      a2r = p13['a2_records']
 954      sev = sorted({e['severity'] for e in a2r})
 955      parts = []
 956      for t in sorted({e['utc'] for e in a2r}):
 957          es = [e for e in a2r if e['utc'] == t]
 958          pr = es[0]['proc']
 959          need(all(e['proc'] is pr for e in es), 'records of one second belong to one process of A1.csv')
 960          name = '%s (%s %s)' % (pr['tag'], pr['binary'], pr['kernel'])
 961          if pr['utc'] == t:
 962              where = 'the second in which the process %s was launched' % name
 963          else:
 964              where = 'during the process %s, launched at %s' % (name, hmd(pr['utc']))
 965          parts.append('%d at %s, %s (journal lines %s)' % (len(es), hmd(t), where, ' and '.join(str(e['line']) for e in es)))
 966      a2csv = os.path.join(D['base']['A-2']['folder'], 'A1.csv')
 967      if a2r:
 968          a2txt = ('During baseline A-2 (A1.csv, %s to %s %s %s) the same journal holds %d record%s with the severity '
 969                   '"%s": %s.' % (hmd(p13['a2_window'][0]), hmd(p13['a2_window'][1]), ref(a2csv),
 970                                  ref(p13['a2_csv2']), len(a2r), '' if len(a2r) == 1 else 's', '" or "'.join(sev),
 971                                  ', and '.join(parts)))
 972      else:
 973          a2txt = ('During baseline A-2 (A1.csv, %s to %s %s %s) the same journal holds 0 records.'
 974                   % (hmd(p13['a2_window'][0]), hmd(p13['a2_window'][1]), ref(a2csv), ref(p13['a2_csv2'])))
 975      a3txt = ('During the three processes of baseline A-3 (%s to %s %s) it holds %d record%s.'
 976               % (hmd(p13['a3_window'][0]), hmd(p13['a3_window'][1]), ref(os.path.join(D['base']['A-3']['folder'], 'A3.csv')),
 977                  len(p13['a3_records']), '' if len(p13['a3_records']) == 1 else 's'))</pre></td><td valign="top">Builds two sentences about hardware error records during the baselines A-2 and A-3. Point 8 prints them.<ul><li><code>a2r</code> holds the records of the saved journal with a time between the first launch of <code>A1.csv</code> and the first launch of <code>A2.csv</code>. build_facts.py gave each record the last process of <code>A1.csv</code> that was launched at or before it.</li><li>The loop groups the records by their second. A guard checks that all records of one second belong to one process. Each group becomes one text piece with the count, the time, the process and the journal lines.</li><li><code>a2txt</code> gives the number of records and their severity, or the words <code>0 records</code> when <code>a2r</code> is empty.</li><li><code>a3txt</code> gives the number of records in the time span of the three processes of A-3.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 978      w('5. **Boot and time since boot.** The run of 2026-11-13 was in the boot that started on %s %s. Its first '
 979        '120-thread process started %.1f days after that. The rerun started %s after the start of its boot.'
 980        % (p13['boot_start'].strftime('%Y-%m-%d %H:%M:%S'), ref(p13['h5']),
 981           (a1first - p13['boot_start']).total_seconds() / 86400, dur((go_start - try6['first_log_utc']).total_seconds())))
 982      w('6. **Speed and boot changed together.** Each memory speed has exactly one boot in this comparison.')
 983      w('7. **2 MiB pages.** Neither script records the page state of the buffers for part A.')</pre></td><td valign="top">Points 5 to 7.<ul><li>Point 5 prints the start of the boot of the 2026-11-13 run. build_facts.py took it from the first line of the saved journal.</li><li>The time from that start to <code>a1first</code> is divided by 86400 s and printed in days with 1 decimal.</li><li>For the rerun, <code>dur</code> formats the time from the first Linux kernel log line of its boot to the start of go.sh.</li><li>Points 6 and 7 are fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 984      w('8. **Hardware error records.** The journal of the 2026-11-09 boot holds its first record at %s (line %d), '
 985        'during the one-thread phase of that run. It holds %d records between %s and %s, the 120-thread part of '
 986        'baseline A-1 %s. %s %s For '
 987        'the rerun the kernel log was not read (no root). Insufficient data: whether records occurred during the '
 988        'rerun. A count of the "[Hardware Error]" lines of the kernel log after the run would resolve it (needs root). '
 989        'Section 4.1 gives the records during the bwx12 and bwx11 rows of the same boot.'
 990        % (hmd(p13['first_record_utc']), p13['first_record_line'], p13['records_in_120'],
 991           hmd(p13['one_done_utc']), hmd(p13['utc_after']), ref(p13['h5']), a2txt, a3txt))</pre></td><td valign="top">Point 8, hardware error records.<ul><li>It prints the time and the line number of the first record in the journal of the 2026-11-09 boot. The words "during the one-thread phase of that run" are fixed text. No guard compares the time of that record with the times of the phase.</li><li><code>records_in_120</code> is the number of journal lines with the tag <code>[Hardware Error]</code> between the end of the one-thread phase and the end of the 120-thread part of A-1. build_facts.py counts lines for this value. For A-2 and A-3 it counts records, and one record has more than one line. The value is 0 in the facts sheet [Ref4].</li><li>The sentences <code>a2txt</code> and <code>a3txt</code> follow.</li><li>The statement for the rerun is fixed text: the Linux kernel log was not read, and the count is marked as "Insufficient data".</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 992      w('9. **Module count of the 2026-11-13 run.** Its probe.txt holds no MemTotal and no boot id %s. The count comes '
 993        'from the saved journal: the boot started on %s with the line "This system has %d DIMM sockets" %s, and the '
 994        'saved kernel log of that boot ends with a line dated "%s" %s.'
 995        % (ref(p13['path']), p13['boot_start'].strftime('%Y-%m-%d %H:%M:%S'), p13['boot_dimm'], ref(p13['h5']),
 996           p13['k5_last'], ref(p13['k5'])))
 997      need(not p13['has_memtotal'] and not p13['has_boot_id'], 'probe.txt of 2026-11-13 has no MemTotal and no boot id')</pre></td><td valign="top">Point 9, the module count of the 2026-11-13 run. It prints the boot start, the number from the journal line <code>This system has N DIMM sockets</code>, and the date text of the last line of the saved Linux kernel log. The guard in line 997 checks that the probe.txt of that run holds neither the text <code>MemTotal</code> nor the text <code>boot_id</code>, as the first sentence states.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 998      qt = fd.dt.datetime.utcfromtimestamp(os.path.getmtime(p13['q_path']))
 999      bts = D['boot_table']['boots']
1000      inboot = lambda t: [b for b in bts if b['start'] &lt;= t][-1]['no']
1001      need(inboot(qt) == inboot(a1first), 'file time of the settings list lies in the boot of the 2026-11-13 run')
1002      w('10. **Memory speed of the baseline boot.** No reading of the applied speed was saved in that boot. The '
1003        'firmware settings list with the file time %s, which lies inside that boot, shows "DIMM Frequency" = '
1004        '"%d MT/s" %s. The DIMM report gives %d MT/s as the setting until %s %s.'
1005        % (qt.strftime('%Y-%m-%d %H:%M'), p13['q_speed'], ref(p13['q_path']), D['boot_table']['until']['speed'],
1006           D['boot_table']['until']['utc'].strftime('%Y-%m-%d %H:%M'), ref(fd.DIMM_REPORT)))</pre></td><td valign="top">Point 10, the memory speed of the baseline boot.<ul><li><code>qt</code> is the file time of the saved settings list <code>questions.json</code>, read as UTC. A settings list is a file of the settings tool with one entry per firmware setting.</li><li><code>inboot(t)</code> returns the number of the last boot in the boot history of the DIMM report that started at or before the time <code>t</code>.</li><li>The guard checks that <code>qt</code> and <code>a1first</code> lie in the same boot.</li><li>The sentence prints <code>qt</code>, the value of the setting "DIMM Frequency" in that list, and the speed and its end time from the DIMM report.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1007      a2p = D['base']['A-2']['procs']
1008      a2opts = sorted({' '.join(re.findall(r'--cpus \S+|--per-thread', p['args'])) for p in a2p})
1009      need(len(a2opts) == 1 and not any('copy' in p['kernel'] for p in a2p), 'A-2: one option set, no copy kernel')
1010      ap = D['a2pre']
1011      a2gap = (p13['a2_first']['utc'] - ap['end']).total_seconds()
1012      need(ap['threads'] == ['1'] and ap['binaries'] == ['bw_new'] and ap['launches_n'] == len(ap['hdr'])
1013           and ap['launches_files'] == sorted(ap['files']) and ap['start'] &lt;= ap['first'] &lt;= ap['last'] &lt;= ap['end']
1014           and 0 &lt; a2gap &lt; 60 and p13['a2_first']['line'] == 1 and p13['a2_first']['utc'] == p13['a2_window'][0]
1015           and ap['steps'][-2:] == ['A5', 'A6'],
1016           'the folder before A-2 holds one-thread processes of bw_new only, and it ended shortly before A-2 started')
1017      extra['a2pre_txt'] = ('%.0f s after the end of a run of %.0f s that held one-thread processes only'
1018                        % (a2gap, (ap['end'] - ap['start']).total_seconds()))
1019      w('11. **Second baseline A-2.** It ran the same binaries with `%s` in another process order, %d processes, no '
1020        'copy kernels %s. It started %s. That run is the folder %s. It started at %s and ended at %s (lines %d and %d '
1021        'of its env.txt %s). It ran %d processes of %s, all with `--threads %s`: %d in A5.csv and %d in A6.csv, launched '
1022        'from %s to %s %s %s. Its launches.txt lists these %d processes and no other %s. The first process of A1.csv '
1023        'started at %s with a 1-minute load average of %.2f %s.'
1024        % (a2opts[0], len(a2p), ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv')), extra['a2pre_txt'], rel(ap['folder']),
1025           hmd(ap['start']), hmd(ap['end']), ap['start_line'], ap['end_line'], ref(ap['env_path']), len(ap['hdr']),
1026           ap['binaries'][0], ap['threads'][0], ap['files']['A5.csv']['n'], ap['files']['A6.csv']['n'], hmd(ap['first']),
1027           hmd(ap['last']), ref(ap['files']['A5.csv']['path']), ref(ap['files']['A6.csv']['path']), ap['launches_n'],
1028           ref(ap['launches_path']), hmd(p13['a2_first']['utc']), p13['a2_first']['load1'],
1029           ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv'))))</pre></td><td valign="top">Point 11, the second baseline A-2.<ul><li><code>a2opts</code> collects the option texts <code>--cpus ...</code> and <code>--per-thread</code> of every A-2 process. A guard checks that all processes used one option set and that no process ran a copy kernel.</li><li><code>ap</code> describes the run folder that ended shortly before A-2. <code>a2gap</code> is the time from its end to the first launch of <code>A1.csv</code>, in seconds.</li><li>The guard in lines 1012 to 1016 tests the patterns that point 11 states about that folder. Every process in its two csv files (A5.csv and A6.csv) ran <code>bw_new</code> with 1 thread. Its launches.txt holds as many entries as these two files hold processes, and it names the same two files. Its times are in order. <code>a2gap</code> is above 0 s and below 60 s. The header line of the first process of <code>A1.csv</code> is line 1 of that file. The step list in line 1 of the env.txt of the run folder <code>ap</code> ends with A5 and A6.</li><li>That step list holds three steps. The first one is A7. The guard does not test A7. The folder holds four text files of A7 and no csv file of A7.</li><li><code>extra['a2pre_txt']</code> keeps the text about this gap. facts_text4.py uses it again.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1030      # settings that were compared between the two boots and found equal
1031      pre = p13['pre']
1032      cmd72 = go['other']['cmdline'][0]
1033      rel72 = re.search(r'vmlinuz-(\S+)', cmd72)[1]
1034      thp80 = re.search(r'^## thp=(.*) defrag=(.*)$', D['env_partA'], re.M)
1035      need(inboot(pre['when']) == inboot(a1first), 'the settings were saved in the boot of the 8000 MT/s baselines')
1036      need(p13['journal_release'] == rel72, 'same Linux kernel release in both boots')
1037      need(pre['cmdline'] == cmd72, 'same Linux kernel command line in both boots')
1038      need(pre['gov'] == ['128 %s' % gov[0][1], str(cur)], 'gov.txt holds the governor and the frequency value of the go.sh log')
1039      need((thp80[1].strip(), thp80[2].strip()) == (thp[1].strip(), thp[2].strip()) and pre['thp'] == thp[1].strip(),
1040           'same huge page setting in both boots')
1041      w('12. **Compared between the two boots, no difference found.** Only these four settings of Linux were compared. '
1042        'Point 13 gives the firmware settings.')
1043      w('    - Linux kernel release: `%s` in line 1 of the saved journal of the 2026-11-09 boot %s and in the command '
1044        'line of the rerun (line %d of the go.sh log %s).' % (rel72, ref(p13['h5']), go['other']['cmdline'][1], ref(go['path'])))
1045      w('    - Linux kernel command line: the file cmdline.txt was saved on %s %s %s. By the boot history of the DIMM '
1046        'report that time lies inside the 2026-11-09 boot %s. Its text is equal to line %d of the go.sh log %s.'
1047        % (pre['when'].strftime('%Y-%m-%d %H:%M:%S'), ref(pre['when_path']), ref(pre['cmdline_path']), ref(fd.DIMM_REPORT),
1048           go['other']['cmdline'][1], ref(go['path'])))
1049      w('    - Governor: gov.txt of the same save holds the two lines "%s" and "%s" %s. The file does not name them. The '
1050        'go.sh log holds "%s %s" for the CPUs 0-119 and `scaling_cur_freq` %d for CPU 0 (line %d %s). So the governor '
1051        'name is equal. The number %d is equal too, but gov.txt does not say which CPU and which value it is.'
1052        % (pre['gov'][0], pre['gov'][1], ref(pre['gov_path']), gov[0][0], gov[0][1], cur, go['other']['governors'][1],
1053           ref(go['path']), cur))
1054      w('    - Huge page setting: line %d of env.txt of the A-2 run holds `%s` and defrag `%s` %s. thp.txt of the save '
1055        'named above holds `%s` %s. Line %d of the go.sh log holds the same values %s.'
1056        % (D['env_partA'][:thp80.start()].count('\n') + 1, thp80[1].strip(), thp80[2].strip(),
1057           ref(os.path.join(D['base']['A-2']['folder'], 'env.txt')), pre['thp'],
1058           ref(pre['thp_path']), go['other']['thp'][1], ref(go['path'])))</pre></td><td valign="top">Point 12, four settings of Linux that were compared between the two boots.<ul><li><code>cmd72</code> is the Linux kernel command line of the rerun from the go.sh log. <code>rel72</code> is the release text after <code>vmlinuz-</code> in it.</li><li><code>thp80</code> is the huge page setting in env.txt of the A-2 run.</li><li>Five guards check: the settings were saved inside the boot of the 8000 MT/s baselines. The Linux kernel release is equal. The command line is equal. gov.txt holds the governor name and the frequency value of the go.sh log. The huge page setting is equal.</li><li>Then the point is written with one sub-bullet per setting. Each sub-bullet names the files and the lines that hold the two values.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1059      # firmware settings: what the saved replies and lists of the settings tool show
1060      fw = D['fw']
1061      fb, fx, fr = fw['lists']['base'], fw['lists']['x1'], fw['lists']['revert']
1062      sx1, sx2, srv, sdm, fin = fw['sets']['x1'], fw['sets']['x2'], fw['sets']['revert'], fw['sets']['dimm'], fw['final']
1063      one_set = lambda v: (need(len(v['set']) == 1 and v['set'][0]['modified'] is True, 'one set reply, modified: true'), v['set'][0])[1]
1064      x1s, x2s, dms = one_set(sx1), one_set(sx2), one_set(sdm)
1065      rvs = {x['name']: x for x in srv['set']}
1066      rvg = {x['name']: x for x in srv['get']}
1067      need(fb['path'] == p13['q_path'] and fb['n'] == fr['n'] == fx['n'] and fw['same_entries'] and not fw['same_order']
1068           and fb['unavailable'] == fr['unavailable'] and fb['val'] == fr['val'],
1069           'the settings list after the set-back holds the same entries as the list of the baseline boot')
1070      need((x1s['name'], x2s['name'], dms['name']) == ('TXREQ Min', 'TXREQ Max', 'DIMM Frequency')
1071           and sorted(rvs) == sorted(rvg) == ['TXREQ Max', 'TXREQ Min'] and all(x['modified'] is True for x in srv['set'])
1072           and all(rvs[n]['answer'] == rvg[n]['answer'] == fb['val'][n] for n in rvs)
1073           and x1s['answer'] != fb['val']['TXREQ Min'] and x2s['answer'] != fb['val']['TXREQ Max'],
1074           'TXREQ Min and TXREQ Max were changed and then set back to the values of the list of the baseline boot')
1075      need(sx1['when'] &lt; sx2['when'] &lt; srv['when'] &lt; fr['mtime'] &lt; sdm['mtime'] &lt; try6['first_log_utc'] &lt; fin['mtime']
1076           and fb['mtime'] &lt; sx1['when'] &lt; fx['mtime'] &lt; sx2['when'] and sdm['when'] is None
1077           and try6['boots_first'] &lt;= fin['mtime'] &lt;= try6['boots_last'],
1078           'order in time of the replies and lists of the settings tool')
1079      need([k for k in fx['val'] if fx['val'][k] != fb['val'][k]] == ['TXREQ Min'] and fx['val']['TXREQ Min'] == x1s['answer']
1080           and len(fw['x1_diff']) == 2, 'the list after the first change differs in TXREQ Min only')
1081      need(dms['answer'] == '%d MT/s' % try6['speed_MTps'] == fin['answer'] and fb['val']['DIMM Frequency'] == '%d MT/s' % p13['q_speed'],
1082           'DIMM Frequency: 8000 MT/s in the lists, set to 7200 MT/s, read as 7200 MT/s')
1083      need('It needs root rights.' in dimm_txt and 'reads and writes firmware settings' in dimm_txt
1084           and 'State of CRB after the test (2026-11-17 20:06): "DIMM Frequency" = `7200 MT/s`' in dimm_txt,
1085           'DIMM report: the settings tool needs root, and the last reading is the setting "DIMM Frequency"')</pre></td><td valign="top">Point 13, firmware settings: the data and seven guards.<ul><li><code>fb</code>, <code>fx</code> and <code>fr</code> are the three saved settings lists: from the baseline boot, after the first change of a setting, and after the set-back. The set-back is the step that set the two changed settings to their earlier values again.</li><li><code>sx1</code>, <code>sx2</code>, <code>srv</code> and <code>sdm</code> are the four reply files <code>set.txt</code>. A reply file holds what the settings tool answered to a change. <code>fin</code> is the last reading of the memory speed.</li><li><code>one_set</code> returns the one reply of a file. Its guard checks that the file holds exactly one reply to a change and that this reply says <code>modified: true</code>.</li><li>The guards check: the list after the set-back holds the same entries as the baseline list. "TXREQ Min" and "TXREQ Max" were changed and then set back to the baseline values. The dates and file times of the records are in the stated order. The list after the first change differs in "TXREQ Min" only. The DIMM report holds three text pieces that the text uses.</li><li>The guard in line 1081 is about "DIMM Frequency". The reply to the change and the last reading both hold the speed of try6.txt (7200 MT/s). The baseline list holds the speed that point 10 prints (8000 MT/s). Point 10 reads its value from the same file as the baseline list. So this part of the guard compares two readings of one file. The guard holds neither of the two numbers as a fixed value.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1086      w('13. **Firmware settings.** No settings list was saved in the boot of the rerun. The settings tool '
1087        '(`uefisettings`, a tool of Arm that reads and writes firmware settings) needs root %s. The saved records of '
1088        'the tool show this:' % ref(fd.DIMM_REPORT))
1089      w('    - Baseline boot. The settings list with the file time %s holds %d entries. %d have a readable value, %d '
1090        'show "ValueUnavailable", and %d show "VStoreError" (the tool could not read the value). It shows '
1091        '"TXREQ Max" = "%s", "TXREQ Min" = "%s" and "DIMM Frequency" = "%s" %s.'
1092        % (hmd(fb['mtime']), fb['n'], fb['readable'], fb['unavailable'], fb['store_error'], fb['val']['TXREQ Max'], fb['val']['TXREQ Min'],
1093           fb['val']['DIMM Frequency'], ref(fb['path'])))
1094      w('    - Changes for another test. Line %d of set.txt of the folder x1 holds the date %s. The file holds the reply '
1095        '"%s" = "%s" (answer in line %d) with "modified: true" %s. Line %d of set.txt of the folder x2 holds the date '
1096        '%s. The file holds the reply "%s" = "%s" with "modified": true (line %d) %s.'
1097        % (sx1['when_line'], hmd(sx1['when']), x1s['name'], x1s['answer'], x1s['line'], ref(sx1['path']),
1098           sx2['when_line'], hmd(sx2['when']), x2s['name'], x2s['answer'], x2s['line'], ref(sx2['path'])))
1099      w('    - Set back. Line %d of set.txt of the folder revert holds the date %s. The file holds the replies '
1100        '"TXREQ Max" = "%s" (line %d) and "TXREQ Min" = "%s" (line %d), both with "modified": true. Both values were read '
1101        'back in lines %d and %d %s. They are the values of the list of the baseline boot.'
1102        % (srv['when_line'], hmd(srv['when']), rvs['TXREQ Max']['answer'], rvs['TXREQ Max']['line'],
1103           rvs['TXREQ Min']['answer'], rvs['TXREQ Min']['line'], rvg['TXREQ Max']['line'], rvg['TXREQ Min']['line'],
1104           ref(srv['path'])))
1105      w('    - After the set-back. The settings list with the file time %s holds the same %d entries as the list of the '
1106        'baseline boot: the two lists are equal in the name, the answer, the options and the help text of every entry. '
1107        'The order of the entries differs %s. So the %d readable values are equal. The %d other values were not '
1108        'compared.' % (hmd(fr['mtime']), fr['n'], ref(fr['path']), fr['readable'], fr['unavailable'] + fr['store_error']))</pre></td><td valign="top">Writes point 13 with its first four sub-bullets: the settings list of the baseline boot with its counts of readable and unreadable values, the two changes for another test, the set-back with the values read back, and the list after the set-back. Every number, date and line number comes from <code>fw</code>. The setting names in the first and the third sub-bullet are fixed text. The count of the values that were not compared is <code>unavailable + store_error</code> of the list after the set-back.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1109      w('    - Memory speed. set.txt of the folder dimm7200-20261117 has the file time %s. It holds one reply: "%s" = '
1110        '"%s" (answer in line %d) with "modified: true" %s. setting-final.txt of that folder has the file time %s. That is inside '
1111        'the span of row 0 of boots.txt, the boot of the rerun %s. It holds the one line `%s` %s. The file does not '
1112        'name the setting. The DIMM report gives this reading as the setting "DIMM Frequency" (its section 6.3) %s.'
1113        % (hmd(sdm['mtime']), dms['name'], dms['answer'], dms['line'], ref(sdm['path']), hm(fin['mtime']),
1114           ref(try6['boots_path']), fin['text'], ref(fin['path']), ref(fd.DIMM_REPORT)))
1115      w('    - Search. A search of R by file name finds %d files set.txt and %d files questions.json. These are the %d '
1116        'reply files and the %d lists named in this point, and one more list with the file time %s, saved after the '
1117        'first change. That list differs from the list of the baseline boot in one entry: "TXREQ Min" = "%s" %s. Among '
1118        'the %d reply files, the only one that is later than the set-back is the change of "DIMM Frequency". A change '
1119        'that was made without a saved reply would not be on record here.'
1120        % (len(fw['sets']), len(fw['lists']), len(fw['sets']), len(fw['lists']) - 1, hmd(fx['mtime']),
1121           fx['val']['TXREQ Min'], ref(fx['path']), len(fw['sets'])))
1122      need(fx['unavailable'] == fb['unavailable'], 'the same number of entries without a value in all three lists')
1123      w('    - Limits. The newest settings list has the file time %s. That is before the first kernel log line of the '
1124        'boot of the rerun (%s, section 1.2). In each of the %d saved lists %d of the %d entries show "ValueUnavailable" '
1125        'in place of a value. The file times are those of the saved files. Insufficient data: the firmware settings in '
1126        'boot %s, apart from the memory speed. A settings list saved in that boot would resolve it (needs root).'
1127        % (hmd(fr['mtime']), hm(try6['first_log_utc']), len(fw['lists']), fr['unavailable'], fr['n'], try6['boot'][:8]))
1128      extra['fw'] = dict(set_back=srv['when'], readable=fr['readable'], unavailable=fr['unavailable'])
1129      w('')</pre></td><td valign="top">Writes the last three sub-bullets of point 13: the change of the memory speed with its last reading, the result of the search for reply files and settings lists under <code>R</code>, and the limits.<ul><li>The guard in line 1122 checks that the list after the first change holds as many entries with the text "ValueUnavailable" as the baseline list.</li><li>The "Insufficient data" sentence about the firmware settings of the boot of the rerun is fixed text. Only the first 8 characters of the boot id are placed in it.</li><li><code>extra['fw']</code> keeps three values for facts_text4.py. That file reads two of them: <code>set_back</code> and <code>readable</code> [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1130      a12o = sel(recs, dataset={'A-1', 'A-2'}, binary='bw_old', kernel='read')
1131      need({(r['dataset'], r['round'], r['process']) for r in a12o}
1132           == {('A-1', 1, 1), ('A-1', 2, len(D['base']['A-1']['procs'])), ('A-2', 1, 1), ('A-2', 2, len(a2p))},
1133           'bw_old read of A-1 and A-2: the first process of the file in round 1, the last process in round 2')
1134      w('Text required by rule F1 point 5 %s: The one-thread phase of the 2026-11-13 run was not repeated. Whether the '
1135        'work before the first 120-thread process changes the rate of the new read kernel is not known (Insufficient '
1136        'data: a run with the new kernel at several positions, after an idle start and after 120-thread work, would '
1137        'settle it). At 8000 MT/s the old read kernel gave %s GB/s after one-thread work and directly after 120-thread '
1138        'work (rows A-1 and A-2, %s).' % (ref(rules), sp(rng(a12o)), nn(rng(a12o))))</pre></td><td valign="top"><b>Range of the old read kernel at 8000 MT/s</b>, for the text that rule F1 point 5 requires.<ul><li><code>a12o</code> selects the records of <code>bw_old read</code> in the data sets A-1 and A-2. The data set A-3 also holds <code>bw_old read</code> records. This line leaves them out. The comparison of part A in line 425 uses all three data sets (<code>A80o</code>, line 420).</li><li>The guard checks that they come from 4 processes: the first process of each file in round 1, and the last process of each file in round 2.</li><li><code>rng(a12o)</code> takes the lowest and the highest <code>GBps</code> of all these intervals together. <code>sp</code> prints both ends with 2 decimals, and <code>nn</code> prints the counts. The sentence prints no median and no mean.</li><li>In the facts sheet the result is 464.42 to 467.06 GB/s from 12 intervals of 4 processes. With the 9 intervals of the 3 processes of A-3 the range is 463.58 to 469.03 GB/s [Ref4] [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1139      need({r['kernel_before'] for r in a12o if r['round'] == 2} == {'bw_new read'},
1140           'bw_old read, round 2 of A-1 and A-2: the process before it in the file is bw_new read')
1141      lgap = lambda folder, procs: (fd.clock(folder, procs[-1]['utc']) - fd.clock(folder, procs[-2]['utc'])).total_seconds()
1142      g1, g2 = lgap(D['base']['A-1']['folder'], a1p), lgap(D['base']['A-2']['folder'], a2p)
1143      need(0 &lt; g1 &lt; 10 and 0 &lt; g2 &lt; 10, 'the last process of A-1 and A-2 was launched a few seconds after the one before')
1144      w('- Where the words of the last sentence come from. In both rows the round-1 process of bw_old read is the first '
1145        'process of the file. It started after one-thread work (points 1 and 11). The round-2 process is the last '
1146        'process of the file. The process before it in the file is the 120-thread process of bw_new read. That process '
1147        'was launched %.0f s before it in row A-1 and %.0f s before it in row A-2 %s %s.'
1148        % (g1, g2, ref(os.path.join(D['base']['A-1']['folder'], 'threads120.csv')),
1149           ref(os.path.join(D['base']['A-2']['folder'], 'A1.csv'))))
1150      w('')
1151</pre></td><td valign="top">Two guards and one bullet for the words "after one-thread work and directly after 120-thread work" of the sentence before.<ul><li>The first guard checks that in round 2 the process before <code>bw_old read</code> in the file is <code>bw_new read</code>.</li><li><code>lgap</code> returns the seconds between the launches of the last two processes of a file. The second guard checks that this time is above 0 s and below 10 s in A-1 and in A-2.</li><li>The bullet prints both times.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 2: the decisions (a) to (r)</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1152      # =============================================================================== 2
1153      w('## 2. Decisions made by the agent for this run')
1154      w('')
1155      w('These are decisions. They are not facts about the machine.')
1156      w('')
1157      w('Decisions made before or during the run:')
1158      w('')</pre></td><td valign="top">Writes the heading of section 2 and its first lines. All of this is fixed text.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1159      dec = [
1160          '"Whole chip test" was read as the 120-thread part of run_kernels.sh of 2026-11-13 %s. The one-thread part '
1161          'was not repeated.' % ref(os.path.join(K13, 'run_kernels.sh')),
1162          '"Old kernel" = the kernel `read` of bw_old. "New kernel" = the kernel `read` of bw_new. Both binaries are the '
1163          'files of 2026-11-13 by sha256 (check %d).' % ([c['key'] for c in D['checks']].index('sha-bw') + 1),
1164          'Part A ran all six kernels (read, write, copy, asmread, asmwrite, asmcopy) to keep the process order of '
1165          '2026-11-13. Statements are made for the read kernels only (rule V3 %s).' % ref(rules),
1166          'Parts L and C were added. Reason: FINDINGS.md section F1 shows that the %s whole-pass stop rule of '
1167          'bandwidth.c distorts totals %s.' % (secA, ref(os.path.join(W15, 'FINDINGS.md'))),
1168          'Three sessions ran one after the other without a pause, plus a fourth part C process. So part C has 2 '
1169          'processes per kernel order.',
1170          'No root was used. So the memory speed is proven through the boot id only, and the kernel log was not read.',
1171          'Control I was added after the first numbers of parts A, L and C were seen. Reason: an earlier run of the same '
1172          'line in the same boot (F72d12, %s UTC) gave a lower asmread total than part L. Control I is therefore not '
1173          'part of the plan fixed before the run.' % hm(f72t)[:5],
1174          'The baseline list and the comparison rules were fixed before go.sh started. The rules file has the file '
1175          'time %s on the clock of the agent\'s server, and its line 2 says that go.sh had not yet started %s. '
1176          'S/local.sha, the sha256 list of the run files, has the file time %s on the same clock, %.0f s later %s. '
1177          'go.sh started at %s by the clock of CRB %s. That is about %.0f s after the rules file (est.: the two clocks '
1178          'were not compared).'
1179          % (hm(rules_mtime), ref(rules), hm(sha_mtime), (sha_mtime - rules_mtime).total_seconds(),
1180             ref(os.path.join(S, 'local.sha')), hm(go_start), ref(go['path']), rules_lead),
1181      ]
1182      for i, d in enumerate(dec):
1183          w('- (%s) %s' % ('abcdefgh'[i], d))
1184      w('')</pre></td><td valign="top"><code>dec</code> holds the eight decisions (a) to (h), made before or during the run. The sentences are fixed text. The loop writes one bullet per decision with its letter. The placed values are:<ul><li>reference numbers, and the number of the check <code>sha-bw</code>,</li><li><code>secA</code>, the interval length of part A,</li><li>the launch time of F72d12 in hours and minutes,</li><li>for decision (h): the file times of the rules file and of <code>local.sha</code>, the seconds between them, the start of go.sh, and <code>rules_lead</code>. <code>rules_lead</code> is the time from the time written in the rules file to the start of go.sh, in seconds (line 381).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1185      w('Decisions made while this sheet was built, after the numbers were seen:')
1186      w('')
1187      bwxp = {r['proc_key']: r['start'] for r in sel(recs, dataset=set(BWX))}
1188      bwx_off = sum(1 for v in bwxp.values() if v == 'offset')
1189      need(set(bwxp.values()) == {'common', 'offset'}, 'the processes of the bwx pool used --start common or --start offset')</pre></td><td valign="top">Counts for decision (p).<ul><li><code>bwxp</code> maps each process of the four data sets of the first runner bwx (<code>BWX</code>) to its field <code>start</code>, the value of the runner option <code>--start</code>.</li><li>In the source of the runner bwx (bwx.c), <code>--start common</code> makes every thread start at byte 0 of its buffer. <code>--start offset</code> makes thread i start at byte (i x 37 mod n) x 2 MiB of its buffer. n is the number of 2 MiB blocks of the buffer.</li><li><code>bwx_off</code> is the number of processes with the value <code>offset</code>.</li><li>The guard checks that both values <code>common</code> and <code>offset</code> occur and that no other value occurs.</li><li>In the facts sheet these are 24 processes, 12 of them with <code>offset</code> [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1190      dec2 = [
1191          'Rate per interval. Part A uses the column aggregate_GBps of the file. The bwx runners use the sum over the '
1192          'threads of bytes / elapsed time. This is the method of stat_k120.py and stat_bwx.py. facts.json holds the '
1193          'rates rounded to 0.001 GB/s.',
1194          'Ratio new/old in part A = median of the 3 intervals of the bw_new process divided by the median of the 3 '
1195          'intervals of the bw_old process of the same session and round. The lowest and the highest ratio of single '
1196          'intervals are given beside it. The lowest ratio is the lowest bw_new interval divided by the highest bw_old '
1197          'interval of the same session and round. The highest ratio is the highest bw_new interval divided by the '
1198          'lowest bw_old interval. These are the two extremes over all 9 pairs of one bw_new interval and one bw_old '
1199          'interval. They are not the ratios of the intervals with the same number.',</pre></td><td valign="top"><code>dec2</code> holds the ten decisions (i) to (r), made after the numbers were seen. The first two state the method of the rate and of the ratio. Both are fixed text: no line derives them from the code.<ul><li><b>(i) Rate per interval.</b> Part A: the column <code>aggregate_GBps</code> of the csv. bwx runners: the bytes of each thread divided by the elapsed time of that thread, added over the threads. build_facts.py and facts_data.py set the field <code>GBps</code> in this way [Ref1] [Ref2]. build_facts.py rounds the rates to 0.001 GB/s only when it writes facts.json.</li><li><b>(j) Ratio new/old in part A.</b> The median of the 3 <code>bw_new</code> intervals divided by the median of the 3 <code>bw_old</code> intervals of the same session and round. Line 298 computes it.</li><li>Line 299 computes the lowest and the highest ratio of single intervals as (j) states: lowest <code>bw_new</code> / highest <code>bw_old</code>, and highest <code>bw_new</code> / lowest <code>bw_old</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1200          'Range of the 8000 MT/s side in the overlap test of rule V1 point 2, parts L and C: the pool of the baseline '
1201          'row L-1 and the supporting rows L-2 to L-4 (all bwx12). The result against L-1 alone and against the pool '
1202          'with the other-binary rows is shown beside it, so the reader can see whether this choice matters.',
1203          'From every earlier bwx12 and bwx11 row only oldread at position 0 and asmread at position 1 are used. These '
1204          'are the positions of part L.',
1205          'Row X2d12 is shown and not used. Rule V4 lists it as "not a baseline" (firmware test setting). Rules V2 '
1206          'point 4 and F2 point 2 name it as a baseline. The two texts contradict each other. This sheet follows V4, '
1207          'because V4 is the fixed list.',
1208          'The sums per mesh in section 4.7 were compared after the numbers were seen. That comparison is not part of '
1209          'the rules fixed before the run.',
1210          'The view "equal pass count" in section 4.3 and the table of thread rates under it were added after the '
1211          'numbers were seen. They are not part of rule V3. Both keep the two rounds apart.',
1212          'Rows of runner bwx (other binary) as the reference of part C. Rule V4 names for the two B7 folders the '
1213          'tags common-6000-common-p1 to p4. Rule V2 point 4 names the tags common-6000-* (%d processes in the %d '
1214          'folders %s). The two texts contradict each other. This sheet uses the %d processes of rule '
1215          'V2 point 4, because that rule defines the comparison per position and quotes the ranges of these %d '
1216          'processes. This is the opposite choice to decision (m). %d of the %d processes used --start offset. '
1217          'Section 4.5 shows the values of the %d processes with --start common beside the pool. No verdict rests on '
1218          'these rows.' % (len(bwxp), len(BWX), ', '.join(BWX), len(bwxp), len(bwxp), bwx_off, len(bwxp), len(bwxp) - bwx_off),
1219          'The view "pool L-1 to L-4 split by the start state" in section 4.2 was added after the numbers were seen. It '
1220          'is not part of the rules fixed before the run.',</pre></td><td valign="top">Decisions (k) to (q). All are fixed text, except the counts in (p).<ul><li>(k) names the 8000 MT/s side of the overlap test for parts L and C: the pool of the data sets L-1 to L-4. Line 417 builds this pool.</li><li>(l) says that only oldread at position 0 and asmread at position 1 of the earlier bwx12 and bwx11 rows are used. build_facts.py applies this filter when it builds the records of L-2 to L-4, R0 and R0b [Ref1]. For L-1, <code>pool</code> applies it through its position argument (line 417).</li><li>(m) says that row X2d12 is shown and not used.</li><li>(n), (o) and (q) name three views that were added after the numbers were seen.</li><li>(p) places <code>len(bwxp)</code>, the number and the names of the <code>BWX</code> data sets, <code>bwx_off</code>, and the number of processes with <code>--start common</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1221          'Part C against 8000 MT/s. Rule F2 point 2 says: "bwx12, 7200 against 8000 MT/s: use part L only". Rule F2 '
1222          'point 3 says: "Part C: present it as old against new at 7200 MT/s only." Rule V1 point 2 asks for the '
1223          'comparison "Per part (A, L, C) and kernel". Rule V2 point 4 names the 8000 MT/s reference of each group of '
1224          'part C. The part C list of rule V4 says: "oldread, asmread: the part L list". The texts contradict each '
1225          'other %s. This sheet follows V1, V2 and V4. It gives a wording by rule V1 point 2 for two rows of part C: '
1226          'oldread, and asmread directly after oldread. Reason 1: V4 is the fixed list of baselines, and it names a '
1227          'baseline for these two kernels of part C. Decision (m) follows V4 on the same ground. Reason 2: finding F2 '
1228          'is about the kernel `read`, which has no bwx12 run at 8000 MT/s, and this sheet gives no wording for `read`. '
1229          'Reason 3: point 3 of F2 itself speaks of an 8000 MT/s column for part C. Its second sentence reads: "In any '
1230          '8000 MT/s column, the cell of "read" must say "no bwx12 run" and must not hold the asmread value." '
1231          'If F2 points 2 and 3 are followed instead, this sheet gives neither of the two wordings, and the view by '
1232          'start state of section 4.2 has no part C row. Each place that gives one of the two wordings names this '
1233          'decision. For the three sentences of the Short version the detail list under them names it. The part C rows '
1234          'of the view by start state name it too. Part C would then still be shown next to 8000 MT/s rows in at '
1235          'least three kinds of places. First, the sums per mesh of section 4.7 and item 9 of "Established" in section '
1236          '6: both name this decision and give the oldread result without part C too. Second, the comparisons with the '
1237          'rows of runner bwx in sections 4.2, 4.5 and 4.6: rules V2 point 4 and F2 point 4 name such rows as '
1238          'references, and this sheet labels them as rows of another binary. Third, the rows without a wording in the '
1239          'two part C tables of sections 4.2 and 4.5. So this sheet does not claim that part C would then answer Q1 '
1240          'only.' % ref(rules),
1241      ]
1242      need(len(dec2) == len('ijklmnopqr'), 'one letter per decision')
1243      for i, d in enumerate(dec2):
1244          w('- (%s) %s' % ('ijklmnopqr'[i], d))
1245      w('')
1246</pre></td><td valign="top">Decision (r) and the loop that writes the list.<ul><li>(r) is fixed text with one reference number. It says that the rules contradict each other about a comparison of part C with 8000 MT/s. It says that this sheet gives a wording for two rows of part C: oldread, and asmread directly after oldread.</li><li>The guard in line 1242 checks that <code>dec2</code> has 10 entries, one per letter from i to r.</li><li>The loop writes one bullet per decision with its letter.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 3.1: part A, old against new</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1247      # =============================================================================== 3
1248      w('## 3. Q1: old against new at 7200 MT/s')
1249      w('')
1250      w('### 3.1 Part A: bw_old and bw_new, whole-pass stop, %s, 3 intervals per process' % secA)
1251      w('')
1252      w('Start state of the sessions:')
1253      w('')
1254      for a_ in A:
1255          w('- Session %d (%s) %s.' % (a_['session'], a_['tag'], evd[a_['tag']]['state']))
1256      w('')
1257      w('One row is one process. A cell shows the rate in GB/s and, in brackets, the pass count of the interval.')
1258      w('')</pre></td><td valign="top">Writes the headings of section 3 and of section 3.1. <code>secA</code> is the interval length of part A as text (<code>0.5 s</code> in the facts sheet [Ref4]). The loop writes one bullet per session with its folder tag and its start state. The last sentence says how to read the table that follows.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1259      rows = []
1260      # rule F1 point 2: the start state of the session is part of the row label (the column beside the session number)
1261      slabel = {a_['session']: evd[a_['tag']]['state'] for a_ in A}
1262      for p in N['pa']:
1263          for label, cell in (('bw_old read (old read kernel)', p['old']), ('bw_new read (new read kernel)', p['new']),
1264                              ('bw_old asmread', p['ao']), ('bw_new asmread', p['an'])):</pre></td><td valign="top"><b>Table 1 of section 3.1: one row per process.</b><ul><li><code>slabel</code> maps a session number to its start state text.</li><li>The outer loop runs once for each of the 6 pairs of <code>N['pa']</code>. There is one pair per session and round.</li><li>The inner loop takes the four processes of a pair: <code>bw_old read</code>, <code>bw_new read</code>, <code>bw_old asmread</code> and <code>bw_new asmread</code>. This is the order of the table rows. In round 1 it is also the order of the launches. In round 2 the four processes were launched in the reverse order (column Launch) [Ref4].</li><li><code>cell</code> is the list of the 3 interval records of that process, sorted by interval number (lines 292 to 294).</li><li>The processes of write, copy, asmwrite and asmcopy are not in this table. Section 5 of the facts sheet gives the lowest, the median and the highest rate of their intervals for each kernel, binary and session [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1265              r0 = cell[0]
1266              rows.append([p['session'], slabel[p['session']], p['round'], label, r0['launch_utc'][11:19],
1267                           '%.2f' % r0['load1_at_launch']]
1268                          + ['%s (%d)' % (g(r['GBps']), r['passes']) for r in cell]
1269                          + [g(med(cell)), '%.2f to %.2f' % (min(r['per_thread_min_GBps'] for r in cell),
1270                                                             max(r['per_thread_max_GBps'] for r in cell)),
1271                             '%s, lines %d-%d' % (ref(os.path.join(R, r0['folder'][2:], r0['file'])), cell[0]['line'], cell[-1]['line'])])</pre></td><td valign="top">The cells of one row. No rate is added to another rate here.<ul><li>Launch: characters 12 to 19 of <code>launch_utc</code>, the time as <code>HH:MM:SS</code>. Load at launch: 2 decimals.</li><li>Interval 1, 2, 3: the records with the interval numbers 0, 1 and 2. Each cell shows <code>g(r['GBps'])</code> and, in brackets, the pass count. <code>GBps</code> is column 7 (<code>aggregate_GBps</code>) of one interval row of <code>threads120.csv</code>. Line 2 of that file gives its formula: the bytes of all threads divided by the longest elapsed time of one thread [Ref7].</li><li>Median: <code>med(cell)</code>, the middle value of the 3 rates, printed with 2 decimals.</li><li>Slowest to fastest thread: the lowest <code>per_thread_min_GBps</code> and the highest <code>per_thread_max_GBps</code> of the 3 intervals. These are columns 8 and 9 of the interval rows.</li><li>Source: the reference number of the csv, and the line numbers of the first and the third interval row. <code>r0['folder'][2:]</code> removes the leading <code>R/</code> of the folder text.</li><li>Example, session 1, round 1, <code>bw_old read</code>: 467.83 GB/s (954 passes), 467.92 GB/s (951 passes), 465.38 GB/s (944 passes), median 467.83 GB/s, source lines 4-6 of the csv [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1272      L.extend(table(['Session', 'Start state of the session', 'Round', 'Binary and kernel', 'Launch', 'Load at launch',
1273                      'Interval 1, GB/s (passes)', 'Interval 2', 'Interval 3', 'Median, GB/s',
1274                      'Slowest to fastest thread, GB/s', 'Source'], rows))</pre></td><td valign="top"><code>table</code> turns the column titles and the rows into Markdown lines. <code>L.extend</code> appends them to the sheet. The table has 24 rows: 6 pairs with 4 processes each.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1275      w('New against old per session and round:')
1276      w('')
1277      rows = []
1278      for p in N['pa']:
1279          rows.append([p['session'], slabel[p['session']], p['round'], g(p['old_med']), g(p['new_med']), '%.3f' % p['ratio'],
1280                       pc(p['drop']),
1281                       '%.3f to %.3f' % (p['ratio_lo'], p['ratio_hi']), '%.3f' % p['ao_ratio'], '%.3f' % p['an_ratio']])
1282      L.extend(table(['Session', 'Start state of the session', 'Round', 'bw_old read, median GB/s', 'bw_new read, median GB/s',
1283                      'Ratio new/old', 'New below old, %',
1284                      'Lowest to highest ratio of single intervals (lowest bw_new / highest bw_old to highest bw_new / '
1285                      'lowest bw_old)', 'bw_old asmread / bw_old read', 'bw_new asmread / bw_old read'], rows))</pre></td><td valign="top"><b>Table 2 of section 3.1: one row per pair.</b> <code>analyse</code> computed every value in lines 297 to 300 from the <code>GBps</code> values before rounding. These lines only format them.<ul><li><code>old_med</code>, <code>new_med</code>: the medians of the 3 intervals of <code>bw_old read</code> and of <code>bw_new read</code>, printed by <code>g</code> with 2 decimals.</li><li>Ratio new/old: <code>new_med / old_med</code>, printed with 3 decimals.</li><li>New below old: the drop <code>(1 - ratio) x 100</code>, printed by <code>pc</code> with 1 decimal.</li><li><code>ratio_lo</code> to <code>ratio_hi</code>: lowest <code>bw_new</code> interval / highest <code>bw_old</code> interval, and highest <code>bw_new</code> interval / lowest <code>bw_old</code> interval.</li><li>The last two columns: the median of <code>bw_old asmread</code> / <code>old_med</code>, and the median of <code>bw_new asmread</code> / <code>old_med</code>.</li><li>Example, session 1, round 1: 467.83 and 330.59 GB/s, ratio 0.707, drop 29.3 % [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1286      passes_new = sorted({r['passes'] for p in N['pa'] for r in p['new']})
1287      passes_old = [r['passes'] for p in N['pa'] for r in p['old']]
1288      top = max(N['pa'], key=lambda p: p['ratio_hi'])
1289      w('- The new read kernel is below the old read kernel in all %d pairs. The highest single-interval ratio is %.3f '
1290        '(session %d, round %d). It is the highest bw_new interval divided by the lowest bw_old interval of that '
1291        'session and round (%s GB/s divided by %s GB/s). Decision (j) in section 2 gives the definition.'
1292        % (len(N['pa']), top['ratio_hi'], top['session'], top['round'], g(max(r['GBps'] for r in top['new'])),
1293           g(min(r['GBps'] for r in top['old']))))
1294      w('- The columns "bw_old asmread / bw_old read" and "bw_new asmread / bw_old read" are ratios of process medians.')
1295      w('- asmread gives %.3f to %.3f of the old read kernel in both binaries. So the lower rate belongs to the '
1296        'load-only loop, not to the binary.' % (min(min(p['ao_ratio'], p['an_ratio']) for p in N['pa']),
1297                                                max(max(p['ao_ratio'], p['an_ratio']) for p in N['pa'])))</pre></td><td valign="top">The first three bullets under the tables.<ul><li><code>passes_new</code> holds the pass counts of all <code>bw_new read</code> intervals of the 6 pairs, each value once, sorted. <code>passes_old</code> holds the pass counts of all <code>bw_old read</code> intervals.</li><li><code>top</code> is the pair with the highest <code>ratio_hi</code>. Bullet 1 prints the number of pairs, that ratio with its session and round, and the two rates that form it: the highest <code>bw_new</code> rate and the lowest <code>bw_old</code> rate of that pair.</li><li>The words "below the old read kernel in all pairs" are fixed text. The guards in lines 396 and 397 check them before any line of the sheet is written.</li><li>Bullet 2 is fixed text.</li><li>Bullet 3 prints the lowest and the highest of the 12 values <code>ao_ratio</code> and <code>an_ratio</code> of the 6 pairs, with 3 decimals. Its second sentence ("So the lower rate belongs to the load-only loop, not to the binary") is fixed text. No guard checks it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1298      w('- Pass counts: bw_new read completed %s passes per interval. bw_old read completed %d to %d.'
1299        % (', '.join(map(str, passes_new[:-1])) + ' or %d' % passes_new[-1] if 1 &lt; len(passes_new) &lt;= 4 else
1300           '%d to %d' % (passes_new[0], passes_new[-1]),
1301           min(passes_old), max(passes_old)))
1302      w('- Limit of part A (rule V3 %s): with the whole-pass stop the pass count moves in steps, and the rate moves '
1303        'with it. So the percent values of part A are less exact than those of parts L and C.' % ref(rules))
1304      w('')
1305</pre></td><td valign="top">Bullets 4 and 5 under the tables.<ul><li>Bullet 4 prints the pass counts. For <code>bw_new read</code> it lists each value when there are 2 to 4 different values, and it prints the lowest and the highest value in every other case. For <code>bw_old read</code> it prints the lowest and the highest value.</li><li>In the facts sheet these are "664, 718 or 719" and "919 to 968" passes per interval [Ref4].</li><li>Bullet 5 is fixed text: the limit of part A by rule V3.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 3.2: parts L and I, oldread against asmread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1306      # ---- 3.2
1307      w('### 3.2 Parts L and I: bwx12, common stop, %s, oldread then asmread' % secX)
1308      w('')
1309      w('- In these parts asmread is used in place of the new read kernel. It is the same loop: 8 "ldp q" loads per 256 B.')
1310      w('- The drop is computed inside the same process and round: (1 - asmread / oldread) x 100.')
1311      w('- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1.')
1312      w('')
1313      rows = []
1314</pre></td><td valign="top">Writes the heading of section 3.2 and three fixed bullets. <code>secX</code> is the interval length of the bwx12 parts as text (<code>6 s</code> in the facts sheet [Ref4]).<ul><li>The first bullet says that asmread is the same loop as the new read kernel: 8 "ldp q" loads per 256 B. This is fixed text. This script reads no machine code.</li><li>The saved objdump listing of bwx12 agrees with that bullet. The tool objdump prints the machine code of a binary as assembler text. In <code>k_asmread</code> and in <code>k_read</code>, one loop pass holds 8 <code>ldp</code> instructions on <code>q</code> registers and moves the pointer by 256 bytes.</li><li>The second bullet states the formula of the drop. Line 314 computes the drop with this formula.</li><li>The words "oldread then asmread" of the heading are fixed text. No line of this file tests the position of these two kernels in part L, in control I or in F72d12. The records agree with the words: in each of these processes oldread is at position 0 and asmread is at position 1 of both rounds. In round 1, oldread runs directly after read_1pl, the last kernel of round 0 [Ref6].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>lrow</code>: one table row of section 3.2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1315      def lrow(p, what):
1316          o, a_ = p['old'], p['asmread']
1317          return [p['tag'] if p['dataset'] != 'F72d12' else 'F72d12', what, p['round'], '%.2f' % o['load1_at_launch'], g(o['GBps']),
1318                  '%s + %s' % (g(o['mesh0_GBps']), g(o['mesh1_GBps'])), g(a_['GBps']),
1319                  '%s + %s' % (g(a_['mesh0_GBps']), g(a_['mesh1_GBps'])), pc(p['drop_asmread']),
1320                  '%s, I rows in lines %d and %d' % (ref(os.path.join(R, o['folder'][2:], o['file'])), o['line'], a_['line'])]</pre></td><td valign="top">Builds one table row from one pair <code>p</code> of the function <code>pairs</code> (line 304). <code>o</code> is the oldread record and <code>a_</code> is the asmread record of the same process and round.<ul><li>Tag: the folder tag. For the data set F72d12 the fixed text <code>F72d12</code> is used. The tag of such a record is the name of its csv file without <code>.csv</code>, which is <code>a6456</code>.</li><li>Rates: <code>g(o['GBps'])</code> and <code>g(a_['GBps'])</code>. Each is the sum of <code>bytes / elapsed_s / 1e9</code> over the T rows of one interval (one row per thread), printed with 2 decimals.</li><li><code>m0 + m1</code>: the sums over the threads of mesh 0 and of mesh 1. Each value is rounded separately. So the two printed values can add up to 0.01 GB/s more or less than the printed rate.</li><li>Drop: <code>pc(p['drop_asmread'])</code>. That is <code>(1 - asmread / oldread) x 100</code>, printed with 1 decimal.</li><li>Source: the csv and the line numbers of the two I rows. The printed rate is not the value of the I row. The I row holds the bytes of all threads divided by the longest elapsed time of one thread. Example: line 128 of the csv of T72L1 holds 462.29 GB/s, and the table shows 462.30 GB/s [Ref8] [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1321      for p in N['pl']:
1322          rows.append(lrow(p, 'part L, session %d. %s' % (p['old']['session'], STANDIN)))
1323      for p in N['pi']:
1324          rows.append(lrow(p, 'control I (idle start, added later)'))
1325      for p in N['pf']:
1326          rows.append(lrow(p, 'earlier visit of the same boot (%s), not part of the rerun' % hm(f72t)[:5]))
1327      L.extend(table(['Folder tag or row', 'What', 'Round', 'Load at launch', 'oldread, GB/s', 'oldread m0 + m1', 'asmread, GB/s',
1328                      'asmread m0 + m1', 'asmread below oldread, %', 'Source'], rows))</pre></td><td valign="top">These lines belong to <code>render</code> again. They fill the table of section 3.2 with one row per pair. A process has two pairs: round 0 and round 1.<ul><li><code>N['pl']</code> gives the rows of part L, <code>N['pi']</code> the rows of control I, and <code>N['pf']</code> the rows of the earlier run F72d12. In the facts sheet these are 6, 4 and 2 rows [Ref4].</li><li>The label of a part L row holds the text of the constant <code>STANDIN</code> (line 30): asmread is used in place of the new read kernel.</li><li>The table leaves out the intervals of read_nop96, read_nop256 and read_1pl of the same processes. Section 4.8 of the facts sheet gives the lowest and the highest rate of each of these three kernels for part L, for control I and for F72d12 [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1329      gl = sorted({evd[t]['gap_s'] for t in ('T72L1', 'T72L2', 'T72L3')})
1330      w('- Every part L process started %s s after the last 120-thread process of part A of its session.'
1331        % ' or '.join('%.0f' % x for x in gl))
1332      w('- The two control I processes started from an idle machine: the load at launch was %s, and the previous '
1333        '120-thread process had ended %s s before.'
1334        % (' and '.join('%.2f' % evd[t]['load1'] for t in ('T72I1', 'T72I2')),
1335           ' and '.join('%.0f' % evd[t]['gap_s'] for t in ('T72I1', 'T72I2'))))
1336      w('- F72d12 started %.0f s after the first kernel log line of the boot, at a load of %.2f %s %s. Section 4.1 '
1337        'gives the proof that it ran in the boot of the rerun.'
1338        % ((D['rx']['F72d12']['launches']['a6456']['utc'] - try6['first_log_utc']).total_seconds(),
1339           D['rx']['F72d12']['launches']['a6456']['load1'], ref(os.path.join(D['rx']['F72d12']['folder'], 'launches.txt')),
1340           ref(try6['gaps_path'])))
1341      fenv = D['rx']['F72d12']['env']
1342      need(len(fenv['top']) &gt;= 2 and fenv['top'][0][1] &gt; 10 * max(x['env']['pcpu_max'] for x in X),
1343           'process list of F72d12 shows a busy process, the lists of the rerun do not')
1344      w('- The process list of F72d12 differs from those of the rerun. Its env.txt was written at %s, %.0f s before the '
1345        'launch. It lists %s at %s %%CPU and %s at %s %%CPU (lines %d and %d %s). The env.txt files of the %d bwx12 '
1346        'launches of the rerun show at most %s %%CPU. So F72d12 is an idle start only by the load-average rule of '
1347        'this sheet (section 4.6).'
1348        % (hm(fenv['start']), (D['rx']['F72d12']['launches']['a6456']['utc'] - fenv['start']).total_seconds(),
1349           fenv['top'][0][2], fenv['top'][0][1], fenv['top'][1][2], fenv['top'][1][1], fenv['top'][0][3], fenv['top'][1][3],
1350           ref(os.path.join(D['rx']['F72d12']['folder'], 'env.txt')), len(X), max(x['env']['pcpu_max'] for x in X)))
1351      w('')
1352</pre></td><td valign="top">The four bullets under the table of section 3.2. They hold no rate.<ul><li><code>gl</code> holds the gaps of the three part L steps in seconds, each value once. The words "after the last 120-thread process of part A of its session" are fixed text. No guard in this file checks which step ran before a part L step. The table of section 1.1 of the facts sheet agrees with the words: it lists the steps in the order of their first launch, and each part L step follows the part A step of its session [Ref4].</li><li>The control I bullet prints the load at launch and the gap of the steps T72I1 and T72I2.</li><li>The F72d12 bullet prints the seconds from the first Linux kernel log line of the boot to its launch, and the load at launch.</li><li><code>fenv</code> holds the values that facts_data.py read from env.txt of F72d12. The process list of that file is sorted by %CPU, highest first. The guard checks that it lists at least 2 processes, and that the %CPU of the first one is more than 10 times the highest %CPU in the env.txt files of the rerun.</li><li>The last bullet prints these two processes with their %CPU and their line numbers.</li></ul></td></tr>
<tr><td colspan="2"><b>Section 3.3: part C, oldread, read and asmread</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1353      # ---- 3.3
1354      w('### 3.3 Part C: bwx12, common stop, %s, oldread, read and asmread in one process' % secX)
1355      w('')
1356      w('- `read` is the new read kernel in bwx12. `oldread` is the old read kernel.')
1357      w('- cfwd runs oldread, read, asmread. crev runs asmread, read, oldread. Each process runs its sequence twice '
1358        '(rounds 0 and 1).')
1359      w('- Each drop is computed against oldread of the same process and round.')
1360      w('- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1, in GB/s. Section 4.7 uses them.')
1361      w('')</pre></td><td valign="top">Writes the heading of section 3.3 and four fixed bullets. They name the kernels and the two orders cfwd and crev. They state that each drop is computed against oldread of the same process and round.<ul><li>The first bullet says that <code>read</code> of bwx12 is the new read kernel and that <code>oldread</code> of bwx12 is the old read kernel. This is fixed text. This script reads no machine code.</li><li>The saved objdump listings agree with that bullet. The listing of bwx12 (the file listing.txt of its build of 2026-11-15) holds its functions <code>k_read</code> and <code>k_oldread</code>. The file probe.txt in the folder of baseline A-1 (the run of 2026-11-13) holds <code>k_read</code> of bw_new and <code>k_read</code> of bw_old.</li><li>Both files describe the binaries of the rerun. The record of that bwx12 build (build.txt) holds the sha256 of this listing.txt and the sha256 of bwx12 that the driver script go.sh tests. That probe.txt holds the sha256 values of bw_old and bw_new that ra.sh, the script of part A, tests.</li><li><code>k_read</code> of bwx12 and <code>k_read</code> of bw_new hold the same 13 instructions. <code>k_oldread</code> of bwx12 and <code>k_read</code> of bw_old hold the same 70 instructions. In these functions the two listings differ only in addresses and in the function name that a label shows.</li><li>First kind of address difference: each function lies at another place in its binary. So the address of each line differs, and so does the printed target of each branch inside a function (1 branch in the new read kernel, 3 in the old one). The distance from the start of the function to the target is equal in both listings.</li><li>Second kind: 3 instructions of the old read kernel name an address outside the function. They are two <code>adrp</code> instructions (each forms the address of a memory page) and one <code>bl</code> instruction (a function call). These addresses differ. The 3 instructions lie outside the loop.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1362      rows = []
1363      for p in N['pc']:
1364          x = next(x for x in X if x['tag'] == p['tag'])
1365          cellf = lambda r: '%s (position %d, after %s)' % (g(r['GBps']), r['pos'], r['kernel_before'].replace(
1366              'none (first interval of the process)', 'nothing: first interval'))
1367          mm = lambda r: '%s + %s' % (g(r['mesh0_GBps']), g(r['mesh1_GBps']))
1368          rows.append([p['tag'], x['spec'], p['round'], '%.2f' % p['old']['load1_at_launch'], cellf(p['old']), mm(p['old']),
1369                       cellf(p['read']), mm(p['read']), cellf(p['asmread']), mm(p['asmread']), pc(p['drop_read']),
1370                       pc(p['drop_asmread']),
1371                       '%s, I rows in lines %d, %d, %d' % (ref(x['csv']), p['old']['line'], p['read']['line'], p['asmread']['line'])])
1372      L.extend(table(['Folder tag', 'Order', 'Round', 'Load at launch', 'oldread, GB/s', 'oldread m0 + m1', 'read, GB/s',
1373                      'read m0 + m1', 'asmread, GB/s', 'asmread m0 + m1', 'read below oldread, %',
1374                      'asmread below oldread, %', 'Source'], rows))</pre></td><td valign="top"><b>Table 1 of section 3.3: one row per process and round.</b> The loop runs once for each pair of <code>N['pc']</code>. Each pair holds the oldread, the read and the asmread record of one process and round.<ul><li><code>x</code> is the entry of <code>X</code> with the same folder tag. It gives the order (<code>cfwd</code> or <code>crev</code>) and the path of the csv.</li><li><code>cellf</code> prints one rate with 2 decimals, its position in the sequence, and the kernel that ran directly before. <code>mm</code> prints the two mesh sums.</li><li>The two drop columns print <code>drop_read</code> and <code>drop_asmread</code> with 1 decimal. Line 314 computed them as <code>(1 - GBps of the kernel / GBps of oldread) x 100</code>, with oldread of the same process and round.</li><li>Source: the csv and the line numbers of the three I rows.</li><li>In the facts sheet the table has 8 rows: 4 processes with 2 rounds each [Ref4].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1375      w('Groups by the kernel that ran directly before (rule V2 %s):' % ref(rules))
1376      w('')
1377      C = Crec
1378      groups = [
1379          ('read after oldread', CG['read after oldread'], 'cfwd, rounds 0 and 1'),
1380          ('read after asmread', CG['read after asmread'], 'crev, rounds 0 and 1'),
1381          ('asmread after read', CG['asmread after read'], 'cfwd, rounds 0 and 1'),
1382          ('asmread as first interval of the process', CG['asmread first'], 'crev, round 0'),
1383          ('asmread after oldread (the condition of part L)', CG['asmread after oldread'], 'crev, round 1'),
1384          ('oldread, all positions', (sel(C, kernel='oldread'), None), 'cfwd position 0, crev position 2'),
1385      ]</pre></td><td valign="top"><b>Table 2 of section 3.3: the groups.</b> <code>C</code> is a second name for <code>Crec</code>, the list of all part C records (line 400). <code>groups</code> holds six entries.<ul><li>The first five are the groups of <code>CG</code>, each with its records and its drops against oldread (lines 402 to 409).</li><li>The sixth entry selects all oldread records of part C, and it has no drops.</li><li>The third item of each entry, for example <code>cfwd, rounds 0 and 1</code>, is fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1386      rows = []
1387      for name, (rs, ds), where in groups:
1388          a_ = rng(rs)
1389          dtxt = '%s to %s' % (pc(min(ds)), pc(max(ds))) if ds else '-'
1390          rows.append([name, where, ', '.join(dict.fromkeys(r['tag'] for r in rs)), nn(a_, boots=False), sp(a_), dtxt])
1391      L.extend(table(['Group', 'Where', 'Folder tags', 'n', 'Min to max, GB/s', 'Below oldread of the same process and round, %'], rows))
1392      w('- Limit (rule V2 point 5): the reverse order comes from 2 processes (T72C2 in session 2, T72C4 after session 3). '
1393        'With 2 processes per order, order and session are still not fully separated.')
1394      w('')
1395</pre></td><td valign="top">One table row per group. The read intervals after oldread and the read intervals after asmread stay in separate rows.<ul><li><code>rng(rs)</code> takes the lowest and the highest <code>GBps</code> of the records of the group, and the counts.</li><li>Folder tags: the tags of the records, each once, in the order of the records.</li><li>n: <code>nn</code> with <code>boots=False</code> prints intervals / processes.</li><li>Min to max: <code>sp</code> prints the lowest and the highest rate with 2 decimals.</li><li>Last column: the lowest and the highest drop of the group with 1 decimal, or <code>-</code> for the oldread row.</li><li>The bullet after the table is fixed text: the limit of rule V2 point 5. The process names T72C2 and T72C4 and the number 2 in it are fixed text too. No guard compares them with the records. The table of section 1.1 agrees with them: it lists T72C2 as part C (crev) of session 2 and T72C4 as part C (crev) after the steps of session 3, and the other two part C steps as cfwd [Ref4].</li></ul></td></tr>
<tr><td colspan="2"><b>Section 3.4: the drops per part and the verdict for Q1</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1396      # ---- 3.4
1397      w('### 3.4 Verdict for Q1')
1398      w('')
1399      gL, gI, gC, gA = rng(L72a), rng(I72a), rng(sel(C, kernel='read')), rng(sel(recs, dataset='rerun-A', binary='bw_new', kernel='read'))
1400      tags = lambda rs: ', '.join(dict.fromkeys(r['tag'] for r in rs))
1401      cpair = lambda key, what: ('C', key, what, CG[key][1], '%d pairs: %d intervals per kernel / %d processes (%s) / %s / 1 boot'
1402                                 % (len(CG[key][1]), len(CG[key][0]), rng(CG[key][0])['procs'], tags(CG[key][0]), sess(CG[key][0])))</pre></td><td valign="top">Writes the heading of section 3.4 and prepares its table.<ul><li><code>gL</code>, <code>gI</code>, <code>gC</code> and <code>gA</code> are the results of <code>rng</code> for asmread of part L, asmread of control I, <code>read</code> of part C and <code>bw_new read</code> of part A. Only counts of these results are used below: <code>n</code>, <code>procs</code> and <code>sessions</code> of <code>gL</code> and of <code>gA</code>, and <code>n</code> and <code>procs</code> of <code>gI</code>. No later line reads <code>gC</code>.</li><li><code>tags</code> returns the folder tags of a record list, each once.</li><li><code>cpair(key, what)</code> returns the table entry of one part C group: the part <code>C</code>, the group key, a label, the drop list <code>CG[key][1]</code>, and the text for n.</li><li>That text holds the number of pairs (the number of drops), the number of intervals, the number of processes with their tags, the sessions from <code>sess</code>, and the fixed words <code>1 boot</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1403      q1p = [
1404          cpair('read after oldread', 'bwx12 `read` (new read kernel) directly after `oldread` (cfwd), against `oldread` of '
1405                'the same process and round'),
1406          cpair('read after asmread', 'bwx12 `read` (new read kernel) directly after `asmread` (crev), against `oldread` of '
1407                'the same process and round'),
1408          cpair('asmread after read', 'bwx12 `asmread` directly after `read` (cfwd), against `oldread` of the same process '
1409                'and round'),
1410          cpair('asmread first', 'bwx12 `asmread` as first interval of the process (crev, round 0), against `oldread` of '
1411                'the same process and round'),
1412          cpair('asmread after oldread', 'bwx12 `asmread` directly after `oldread` (crev, round 1), against `oldread` of '
1413                'the same process and round'),
1414          ('L', None, 'bwx12 `asmread` (used in place of the new read kernel) against `oldread`, same process and round', dl,
1415           '%d pairs: %d intervals per kernel / %d processes / %d sessions / 1 boot' % (len(dl), gL['n'], gL['procs'], gL['sessions'])),
1416          ('A', None, 'bw_new `read` against bw_old `read`, medians of 3 intervals, same session and round', dpa,
1417           '%d pairs of process medians: %d intervals per kernel / %d processes per kernel / %d sessions / 1 boot' % (len(dpa), gA['n'], gA['procs'], gA['sessions'])),
1418          ('I (control, %s)' % ADDED, None, 'bwx12 `asmread` against `oldread`, same process and round', di,
1419           '%d pairs: %d intervals per kernel / %d processes / no session / 1 boot' % (len(di), gI['n'], gI['procs'])),
1420          ('F72d12 (earlier visit, not part of the rerun)', None, 'bwx12 `asmread` against `oldread`, same process and round', df,
1421           '%d pairs: %d intervals per kernel / 1 process / no session / 1 boot' % (len(df), len(df))),
1422      ]</pre></td><td valign="top"><code>q1p</code> lists the 9 rows of the Q1 table. Each entry holds the part, the group key, the label of the pair, a list of drops in percent, and the text for n.<ul><li>5 entries for the groups of part C, built by <code>cpair</code>.</li><li>Part L with <code>dl</code>, control I with <code>di</code>, and F72d12 with <code>df</code>. Each list holds the <code>drop_asmread</code> of every pair of that data set (lines 390 to 392).</li><li>Part A with <code>dpa</code>: the 6 drops between the process medians (line 395).</li><li>The numbers in the n texts are <code>len</code> of the drop list and counts from <code>gL</code>, <code>gA</code> and <code>gI</code>. <code>gL</code> and <code>gI</code> count asmread records, and <code>gA</code> counts <code>bw_new read</code> records. The words "per kernel", "1 boot", "no session" and "1 process" are fixed text.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1423      rows = []
1424      for part, group, what, ds, n in q1p:
1425          rows.append([part, what, pc(min(ds)), pc(max(ds)), n])
1426          V['q1_parts'].append(dict(part=part, group=group, pair=what.replace('`', ''), smallest_drop_pct=round(min(ds), 2),
1427                                    largest_drop_pct=round(max(ds), 2), n=n))
1428      L.extend(table(['Part', 'Pair', 'Smallest drop, %', 'Largest drop, %', 'n'], rows))
1429      w('- Part C has one row per group (rule V2 %s). No range is given over all read intervals or over all asmread '
1430        'intervals of part C.' % ref(rules))
1431      w('')</pre></td><td valign="top"><b>The smallest and the largest drop of each row.</b> For each entry the loop takes <code>min(ds)</code> and <code>max(ds)</code> of its drop list. No mean and no median of the drops is used.<ul><li>The table of the facts sheet shows both values with 1 decimal, rounded half up by <code>pc</code>.</li><li><code>V['q1_parts']</code> gets one entry per row. It holds both values rounded to 2 decimals by the Python function <code>round</code>. The label is stored without its backquotes.</li><li>Example, part A: 28.5 % and 31.8 % in the facts sheet, 28.49 % and 31.78 % in facts.json [Ref4] [Ref6].</li><li>The bullet after the table is fixed text: part C has one row per group.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1432      g_ro, g_ra = CG['read after oldread'], CG['read after asmread']
1433      V['q1'] = (
1434          'Yes. At 7200 MT/s with 12 memory modules the new read kernel is still below the old read kernel. Part C '
1435          '(bwx12 kernel read against oldread of the same process and round, common stop, %s): %s lower when read ran '
1436          'directly after oldread (%d pairs, %d processes: %s), and %s lower when read ran directly after asmread '
1437          '(%d pairs, %d processes: %s). Part L, asmread (the same loop, used in place of the new read kernel) against '
1438          'oldread: %s lower (%d pairs, %d processes, %d sessions). Part A, the repeat of the 2026-11-13 test, bw_new '
1439          'read against bw_old read, whole-pass stop, %s: %s lower (%d pairs of process medians, %d sessions). The '
1440          'percent values of part A are less exact than those of parts L and C. The new read kernel is below the old '
1441          'read kernel in all %d pairs of part C and in all %d pairs of part A. asmread is below the old read kernel in '
1442          'all %d pairs of part L and in all %d pairs of part C (%s after read, %s as first interval, %s after oldread). '
1443          'The size is not one fixed value: control I (idle start, %s, %s) gave %s, and the earlier run F72d12 of the '
1444          'same boot (not part of the rerun) gave %s. All values come from 1 boot.'
1445          % (secX, pcr(g_ro[1]), len(g_ro[1]), rng(g_ro[0])['procs'], tags(g_ro[0]), pcr(g_ra[1]), len(g_ra[1]),
1446             rng(g_ra[0])['procs'], tags(g_ra[0]), pcr(dl), len(dl), gL['procs'], gL['sessions'], secA, pcr(dpa), len(dpa),
1447             gA['sessions'], len(dcr), len(dpa), len(dl), len(dca), pcr(CG['asmread after read'][1]),
1448             pcr(CG['asmread first'][1]), pcr(CG['asmread after oldread'][1]), ADDED, NOT_PLAN, pcr(di), pcr(df)))
1449      w('**Verdict.** ' + V['q1'])
1450      w('')</pre></td><td valign="top"><b>The verdict for Q1.</b> <code>V['q1']</code> is one template that starts with the fixed word <code>Yes</code>. No <code>if</code> chooses the answer. The guard in line 396 checked before that every drop is above 0.<ul><li><code>pcr</code> prints the lowest and the highest drop of a list with 1 decimal. It prints one value when both round to the same text.</li><li>Part C, kernel <code>read</code>: <code>pcr</code> of the groups read after oldread (<code>g_ro</code>) and read after asmread (<code>g_ra</code>), each with its number of pairs, its number of processes and the folder tags.</li><li>Part C, asmread: <code>pcr</code> of each of its three groups (after read, as first interval, after oldread). Part L: <code>pcr(dl)</code>. Part A: <code>pcr(dpa)</code>. Control I: <code>pcr(di)</code>. F72d12: <code>pcr(df)</code>.</li><li>The four counts "in all N pairs" are <code>len(dcr)</code>, <code>len(dpa)</code>, <code>len(dl)</code> and <code>len(dca)</code>. <code>secX</code> and <code>secA</code> are the two interval lengths. <code>ADDED</code> and <code>NOT_PLAN</code> are fixed texts about control I.</li><li>The words "common stop" and "whole-pass stop" are fixed text here and in the headings of sections 3.1 to 3.3. No line of this file reads the field <code>stop</code> (the stop rule) of the records. Every bwx12 record of the rerun holds <code>common</code> in that field [Ref6]. It is the value of <code>stop=</code> in the header line of the csv [Ref8]. Every part A record holds <code>whole pass</code> [Ref6]. build_facts.py writes this fixed text into the part A records, and the csv of part A does not name a stop rule [Ref1] [Ref7].</li><li>Line 1449 writes the text into the sheet after the bold word "Verdict.".</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1451      so, sa = rng(L72o + I72o + F72o), rng(L72a + I72a + F72a)
1452      w('- In the table of section 3.2 the lowest and the highest oldread value are %s GB/s apart (%s and %s GB/s). The '
1453        'lowest and the highest asmread value are %s GB/s apart (%s and %s GB/s). So the size of the drop follows the '
1454        'load-only loop.' % (g(so['hi'] - so['lo']), g(so['lo']), g(so['hi']), g(sa['hi'] - sa['lo']), g(sa['lo']), g(sa['hi'])))
1455      w('')
1456</pre></td><td valign="top">The bullet after the verdict.<ul><li><code>so</code> is the range of the oldread records of part L, control I and F72d12 taken together. <code>sa</code> is the same for asmread.</li><li>The bullet prints <code>hi - lo</code>, <code>lo</code> and <code>hi</code> of each range. The difference is computed before rounding and then printed with 2 decimals.</li><li>In the facts sheet the two differences are 7.59 GB/s for oldread and 26.03 GB/s for asmread [Ref4].</li><li>The sentence "So the size of the drop follows the load-only loop" is fixed text. No guard compares the two differences.</li></ul></td></tr>
<tr><td colspan="2"><b>Sections 4 to 6: call of <code>section4</code>, then section 0</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1457      # =============================================================================== 4
1458      from facts_text4 import section4
1459      ctx = dict(
1460          cLo=cLo, cLa=cLa, cIo=cIo, cIa=cIa, cFo=cFo, cFa=cFa, cAo=cAo, cCo=cCo, pa3=pa3, newread=newread,
1461          L72o=L72o, L72a=L72a, I72o=I72o, I72a=I72a, F72o=F72o, F72a=F72a, P12o=P12o, P12a=P12a, PALLo=PALLo,
1462          PALLa=PALLa, A72o=A72o, A80o=A80o, C72o=C72o, rules=rules, evd=evd, dl=dl, di=di, df=df, CG=CG)
1463      ctx.update(extra)
1464      section4(D, N, V, L, ref, q2row, ctx)
1465      need(sum(1 for r_ in V['q2_rows'] if r_['part'] == 'C' and r_['decides']) == 2,
1466           'two rows of part C carry a wording by rule V1 point 2 (decision (r))')</pre></td><td valign="top">Imports <code>section4</code> from facts_text4.py here, inside <code>render</code>. facts_text4.py itself imports helper functions from this file in its first lines [Ref3].<ul><li><code>ctx</code> collects what <code>section4</code> needs from this file: the 8 comparisons <code>cLo</code> to <code>cCo</code>, <code>pa3</code>, <code>newread</code>, the record lists, the 8000 MT/s pools, the path <code>rules</code>, the steps <code>evd</code>, the drop lists <code>dl</code>, <code>di</code>, <code>df</code>, and the groups <code>CG</code>.</li><li><code>ctx.update(extra)</code> adds the two entries that section 1.5 stored in <code>extra</code> (lines 1017 and 1128).</li><li><code>section4</code> appends sections 4, 5 and 6 to <code>L</code> and fills <code>V</code> [Ref3].</li><li>The guard checks that exactly 2 rows of <code>V['q2_rows']</code> have the part <code>C</code> and a true <code>decides</code>. Decision (r) states this number.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1467      L[i_short:i_short] = short_version(ctx)       # section 0, written last
1468</pre></td><td valign="top">Inserts the lines that <code>short_version(ctx)</code> returns at the index <code>i_short</code> (line 474). The slice <code>L[i_short:i_short]</code> is empty, so no line is replaced. The Short version therefore stands in section 0. It is built after section 6.</td></tr>
<tr><td colspan="2"><b>Section 7: the file list, and the return value</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1469      # =============================================================================== 7
1470      w('## 7. Files')
1471      w('')
1472      w('Every raw file and script that this sheet uses, one line each. R and S are the folders named at the top.')
1473      w('')
1474      missing = [p for p in dict.fromkeys(fd.OPENED) if os.path.abspath(p) not in ref.d]
1475      need(not missing, 'every file that the script opened is in the file list: %s' % missing)
1476      for key, (n, desc) in ref.d.items():
1477          if key.startswith('ext:'):
1478              w('- [Ref%d] %s' % (n, desc))
1479          else:
1480              w('- [Ref%d] `%s`: %s' % (n, rel(key), desc))
1481      w('')
1482      w('Output files of this sheet: `S/FACTS.md` (this file) and `S/facts.json` (every interval as one record, plus '
1483        '"meta" and "verdicts").')
1484      w('')</pre></td><td valign="top">Writes section 7.<ul><li><code>fd.OPENED</code> holds every path that the function <code>_open</code> of facts_data.py opened. build_facts.py appended more paths to it: the stderr.txt files, and the threads120.csv files of its cross-check with stat_k120.py [Ref1].</li><li>The guard checks that each of these paths is registered in <code>ref.d</code>. When one is missing, the script stops and names it.</li><li>The loop writes one line per registered entry, in the order of the reference numbers. An entry whose key starts with <code>ext:</code> is an external source, and it prints its description only. A file prints its path and its description. <code>rel</code> shortens a path under <code>R</code> or <code>S</code> to <code>R/...</code> or <code>S/...</code>. A file outside both folders keeps its full path.</li><li>The last line names the two output files.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1485      text = '\n'.join(L)
1486      bad = check_dates(text)
1487      need(OTHER_DAY and not bad, 'a time of another day stands without its date in the same sentence or cell: %s' % bad[:3])
1488      return V, text</pre></td><td valign="top">The function <code>render</code> and the file end here.<ul><li>Line 1485 joins the lines of <code>L</code> with newline characters to one text.</li><li><code>check_dates</code> returns every sentence or table cell that holds a time of another day without a date.</li><li>The guard stops the script when <code>OTHER_DAY</code> is empty or when such a piece exists.</li><li><code>render</code> returns <code>V</code> and the text.</li></ul></td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: The caller. `main` (lines 1033 to 1052) calls `render(D)` and then writes facts.json and FACTS.md. `collect` (lines 50 to 290) builds the records: `add_k120` (lines 119 to 140) sets `GBps` of a part A record, `add_bwx` (lines 142 to 160) sets `GBps` of a bwx record. Lines 30 and 31 hold the two filters: oldread at position 0 with asmread at position 1, and the kernels oldread, read, asmread. `run_checks` (line 653) runs the integrity checks. `write_json` (lines 899 to 1030) rounds the floating-point numbers of `V` and of the records to 3 decimals. The files `A1.csv` and `A3.csv` of the data sets A-2 and A-3 are named in lines 187 to 189. Lines 188 and 189 keep only the processes of `A3.csv` with the tags `onebuf-ms500-1` to `onebuf-ms500-3`. Lines 207 to 221 name the csv files of each earlier bwx data set that rx.sh or r0.sh wrote. The integrity check `I-agg` is in lines 736 to 740. Lines 83, 234 and 805 add paths to the list `OPENED` of facts_data.py. Line 820 calls `interval_rows` of stat_bwx.py for each folder of the integrity check `x-bwx`. Lines 258 to 267 name the csv file and the tag prefix of each data set of the first runner bwx. Line 276 keeps only the processes whose tag starts with that prefix. Lines 121 to 129 set `kernel_before` of a part A record. Lines 592 to 596 read the header lines of `one-thread.csv`. Line 614 and lines 521 to 524 read the header lines of `A2.csv`, `A5.csv` and `A6.csv` with `step_headers` of facts_data.py.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: The parsers and range functions. `read_k120` (lines 264 to 304) reads the interval rows of a part A csv and skips the row `best` (line 298). `read_bwx` (lines 313 to 353) and `bwx_intervals` (lines 356 to 383) read the T rows and add the thread rates. `sel` (line 442), `rng` (line 461), `overlap` (line 471), `gap` (line 475), `width_pct` (line 484). `_open` (line 39) opens a file and adds its path to the list `OPENED` (line 36). `read_k120` stores a row with the first field `thread` apart from the interval rows (lines 294 to 297).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`: The second text module. Lines 11 and 12 import helper functions from facts_text.py. `section4` (line 24) writes sections 4, 5 and 6. Its guard in line 1461 stops the script when an integrity check failed. `section4` sets `V['q2']` (line 1379), `V['insufficient_data']` (line 1554) and `V['hypotheses']` (line 1612).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The output text. Section 0 starts at line 12, the word list at line 38, section 1 at line 98, section 2 at line 275, section 3 at line 303, section 4 at line 436 and section 7 at line 950.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`: The fixed list of 8000 MT/s baselines and the rules V1 to V4, F1 and F2. Point 2 of the rule of finding V1 gives the two wordings. Lines 28 to 32 list the csv files of the rows L-1 to L-4.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: The output that holds `V` under `verdicts`: 9 entries in `q1_parts` and 42 entries in `q2_rows`. Its part `intervals` holds the records. The data set A-2 has no record of `bw_old asmread` there. Its part `meta` counts the records of each of the 26 data sets (`counts`, `by_dataset`). The field `min_ms` of a record gives its interval length: 6000 ms in the records of L-1 and of the 7200 MT/s bwx12 data sets, 4000 ms in the records of L-2 to L-4. The field `process` of a record of the data set `rerun-A` numbers the 24 processes of part A in its session from 1. It is 1 for `bw_old read` and 2 for `bw_new read` in round 1, and 24 and 23 in round 2, in all three sessions. In the records of `bw_old read`, `process` is 1 in round 1 and 24 in round 2 for A-1, and 1 and 12 for A-2. A-1 holds 24 processes and A-2 holds 12. In the records of the second and the third process of A-3, `kernel_before` starts with `not listed`. In the records of `bw_new read` of round 2, `process` and `kernel_before` are 23 and `bw_old write` in `rerun-A` and in A-1, and 11 and `bw_new asmread` in A-2.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: Example of a part A file. Line 2 gives the formula of `aggregate_GBps`. Line 3 names the columns. Line 4 is an interval row with the rate 467.83 GB/s in column 7.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: Example of a bwx12 file. Line 4 names the columns of a T row: `cpu` is column 6, `bytes` is column 7, `elapsed_s` is column 8. Line 3 names the columns of an I row: `total_bytes` is column 7, `max_elapsed_s` is column 8, `aggregate_GBps` is column 9. Line 128 is the I row of the first oldread interval. Its `total_bytes` divided by its `max_elapsed_s` and by 1e9 gives its `aggregate_GBps`, 462.29 GB/s. The rate from the T rows of that interval (the sum of `bytes / elapsed_s / 1e9` over its 120 T rows) is 462.30 GB/s.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: The report generator. Its header comment names facts.json as the input (line 5). It says that the computed values are compared with FACTS.md (line 12).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py`: The earlier statistics script for bwx csv files. `interval_rows` (line 61) reads every file `*.csv` of a folder (line 64). `read_csv` (line 38) opens each file with the Python function `open` (line 43). It does not use `_open` of facts_data.py.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/results/B7-20261113T232859Z/B7.csv`: Example of a csv file of the first runner bwx. Each process starts with one line `-- step`. This file holds 48 such lines, and 8 of them hold a tag that starts with `common-6000-`. The file `B7.csv` of the folder `B7-20261114T024352Z` gives the same two counts. Each of the two files `C3.csv` (folders `C3-20261114T022708Z` and `C3-20261114T054116Z`) holds 18 such lines, and 4 of them hold a tag with that prefix.
