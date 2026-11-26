# `build_facts.py` explained

- Source file: `build_facts.py` in this folder (Python script, 1056 lines, 68288 bytes).
- sha256 of the source when this page was built: `38637021b501e44eb942e6ca1aa9ff118d4a02ee0d4f8859858bdfcb9a1766c1`.
- Role in the whole-chip test: Main analysis script: builds the interval records, runs integrity checks, writes facts.json and FACTS.md.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

This script reads the raw result files and builds one record with the rate in GB/s per timed interval: every interval of the rerun, and selected intervals of the earlier runs. It then runs 27 integrity checks, gets the statistics and the text from `facts_text.py`, and writes `S/facts.json` and `S/FACTS.md` when every check passes.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Rerun**: the whole-chip read test of 2026-11-17 on CRB, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s. go.sh ran parts A, L and C. go2.sh ran control I afterwards.
- **Memory module, DIMM**: one memory module (DIMM = dual in-line memory module). CRB has 12 slots.
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
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values. The C rows exist only for a process that ran with the counter option `--count`.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **GB, GB/s**: GB = 1e9 bytes. Every rate is in GB/s.
- **est.**: estimated, not measured directly.
- **`R`, `S`**: `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`, the result folders copied back from CRB. `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`, the folder of this script. Both names come from `facts_data.py`.
- **`fd.W15`, `fd.K13`**: two folders next to `S`. `w120-2026-11-15` holds rx.sh and r0.sh. `kernels-2026-11-13` holds run_kernels.sh.
- **`fd`**: the module `facts_data.py`, imported under this short name. It holds the parsers of the raw files and small helpers (`rel`, `sel`, `find`, `sha256`, `clock`). It writes nothing.
- **`fd.OPENED`**: the list in `facts_data.py` of the input files that were opened through `fd._open`. Lines 83, 234 and 805 of this script add more files to it. The file list of FACTS.md is checked against it.
- **`D`**: the dictionary that `collect` builds and that every later step reads. Main keys: `recs` (all interval records), `checks`, `A` (the 3 part A folders of the rerun), `X` (the 9 bwx12 folders of the rerun), `events` (the 12 steps in time order), `base`, `rx`, `step` (earlier data sets), `logs`, `try6`.
- **Record, interval record**: one Python dictionary per timed interval, made by `fd.base_record`. Every record has the same 40 keys. The list `D['recs']` holds all records. facts.json stores them under `intervals`.
- **`GBps`**: the field of a record that holds the rate of the interval in GB/s. Part A: the csv column `aggregate_GBps`. bwx runners: the sum over the T rows of bytes / elapsed_s / 1e9.
- **`aggregate_GBps`**: a column that the benchmark binary prints per interval: the sum of the bytes of all threads, divided by the longest per-thread elapsed time, in GB/s.
- **Pass count, `passes`**: part A only: total_bytes / bytes_per_thread of an interval row, as a whole number. For copy and asmcopy the value is 2 x the number of buffer passes, because the binary counts read plus written bytes for these two kernels.
- **Data set, `dataset`**: the field that says which group of runs a record belongs to. The rerun has `rerun-A`, `rerun-L`, `rerun-C` and `control-I`. Every earlier group has a short label. The entries below list these labels. The field `part` (A, L, C or I) says to which part of the test a record belongs: the earlier bwx12 and bwx11 data sets carry L, and the data sets of the first runner bwx carry C.
- **`role`**: the field that says how a data set is used: rerun, control, baseline, supporting, other binary, not a baseline, or 10 modules. F72d12 has its own value: a 7200 MT/s sample of the same boot that is not part of the rerun.
- **Baseline**: an 8000 MT/s run with 12 memory modules that the rules file names as the comparison for a part of the rerun.
- **A-1, A-2, A-3**: the 8000 MT/s baselines of part A, all of 2026-11-13. A-1 = `threads120.csv` of `R/kernels-20261113T181222Z` (the first test). A-2 = `A1.csv` of `R/partA-20261113T205055Z`. A-3 = 3 processes of `A3.csv` of the same folder (old read kernel only).
- **L-1 to L-4**: the 8000 MT/s rows of bwx12. L-1 (folder `w120-R8-...`) has the same argument line as part L. L-2, L-3 and L-4 are supporting runs of 4 s with other counter events. Of them only oldread at position 0 and asmread at position 1 are used.
- **R0, R0b**: rows of the other binary bwx11 at 8000 MT/s.
- **X2d12, X1d10, X1d10b, BASEd10**: bwx12 runs that are not baselines. X2d12 ran with a firmware test setting. The other three ran in boots with 10 memory modules.
- **F72d12**: an earlier run of the like.spec line in the same 7200 MT/s boot, about 2 h 10 min before the rerun. It is not part of the rerun.
- **B7a, B7b, C3a, C3b, B5a, B5b, B5a-rev, B5b-rev**: runs of the first runner bwx at 8000 MT/s (2026-11-13 and 2026-11-14). One csv file holds several processes. The two `-rev` sets hold the kernels in reverse order.
- **Rules file, rules V1 and V4**: the file `S/baselines-and-rules.txt`, written before the rerun started. V4 fixes the list of the 8000 MT/s baselines. V1 point 2 fixes the comparison: the range from minimum to maximum at 7200 MT/s against the same range at 8000 MT/s. The script does not read the list of the baselines from this file. The folders and files of the earlier data sets are written in the code of `collect` (lines 184 to 189, 207 to 221 and 258 to 267). `render` opens the file and uses its line 2, which holds the writing time [Ref2].
- **FINDINGS.md**: the facts sheet of the investigation of 2026-11-15 into the drop of the read rate. It lies in the folder `w120-2026-11-15` next to `S`. `section4` reads its section F2 and searches it for names of test loops. No number is taken from it.
- **`POS01`**: the set of the two pairs (oldread, position 0) and (asmread, position 1). As a filter it keeps only these two intervals of each round.
- **`READ3`**: the three kernel names oldread, read and asmread.
- **Facts sheet, FACTS.md**: the Markdown text that this script writes. Its section 3 answers Q1 and its section 4 answers Q2. The report script make_report.py does not take its numbers from this text. It computes them from the records of facts.json and from the raw csv files. Then it compares them with this text [Ref16].
- **facts.json**: the JSON output file of this script. `meta` describes the run and holds the checks. `verdicts` holds the answers. `intervals` holds one record per timed interval. The report script make_report.py reads this file.
- **Q1, Q2**: the two questions of the rerun. Q1: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much. Q2: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s [Ref4].
- **Verdicts, `V`**: the dictionary that `render` of `facts_text.py` returns. `V['q1']` and `V['q2']` are the answer sentences to Q1 and Q2. `write_json` stores `V` under `verdicts`.
- **`facts_text4.py`, `section4`**: the second file of the text code. `render` of `facts_text.py` calls its function `section4` for sections 4 to 6 of FACTS.md. `section4` ends the script with an error message unless every check passed [Ref11].
- **Check**: one entry of `D['checks']`: a key such as `I-agg`, a pass flag `ok`, and one line of text with the counted values. FACTS.md prints the checks in its section 1.4.
- **go.sh, go2.sh**: the two driver scripts of the rerun. go.sh ran 3 sessions and then one more part C process. go2.sh ran control I. Each printed state lines. The scripts name no log file. The command that started each script on CRB sent its standard output and its error output into the log [Ref14]. The last line of a complete log is `ALLDONE`.
- **`fail` (shell function)**: the function of go.sh and go2.sh that prints a line `FAILED: <reason>`, prints a state line and ends the script with the exit status 1.
- **`local.sha`, `go2.sha`**: two lists of sha256 values in `S`. `local.sha` lists go.sh, ra.sh and the three spec files. `go2.sha` lists go2.sh. The AI agent (Claude Code) that ran the rerun wrote each list on its own server from the local files. The same command line then copied the files and the list to CRB and tested the copies there with `sha256sum -c` [Ref14]. Check `sha-local` tests the present local files against the two lists. Since 2026-11-24 it fails for go.sh.
- **ra.sh**: the script of part A. It starts 24 processes one after the other: 2 rounds x 6 kernels x 2 binaries (bw_old, bw_new), each with 3 intervals of at least 0.5 s.
- **rx.sh, r0.sh**: rx.sh starts one process of the binary that it is given (bwx12 in the rerun) for each line of a spec file. It writes the result folder `w120-<name>-<time>`. r0.sh is the earlier runner script of the data set R0 (binary bwx11). It wrote no `binary` line into env.txt, so this script takes the checksum from the text of r0.sh.
- **run_kernels.sh**: the script of the first test of 2026-11-13. Its 120-thread part is what part A repeats.
- **`one` (shell function)**: the function of ra.sh and of run_kernels.sh that writes the `-- binary` header line and then starts one benchmark process with `--reps 3 --min-ms 500` (3 intervals of at least 500 ms each).
- **run_partA.sh, run_bwx.sh**: the scripts that wrote the result folders `partA-...`, `B7-...`, `C3-...` and `B5-...` of 2026-11-13 and 2026-11-14. Their csv files hold one header line `-- step ...` per process.
- **Section, step line**: the lines of one process inside a csv file of the first runner bwx. Each section starts with a `-- step ...` header line. A csv file of rx.sh has one section.
- **threads120.csv**: the result file of part A. Per process it holds one header line `-- binary ...` that ra.sh writes, one `# bandwidth:` line and one column header row that the binary prints, one row per interval (3 here), and one `best` row.
- **Interval row**: a row of a part A csv whose column 4 (`rep`) is a number: one row per timed interval. The `best` row, the column header row and the per-thread rows (`thread,...`) are not interval rows.
- **probe.txt**: the state file that ra.sh writes into a part A folder: time, load, logins, boot id, MemTotal, runnable tasks, Linux kernel release, a process list, the sha256 values of bw_old, bw_new and ra.sh, and one `load_after` line at the end of the session [Ref10].
- **env.txt, launches.txt, stderr.txt**: files that rx.sh writes into a bwx folder. env.txt: date, Linux kernel release, load, the logged-in users, a process list, and the line `binary <path> <sha256>`. launches.txt: one `launch` line directly before each process (tag, time, load, logins, arguments) and one `rc` line after it. stderr.txt: the error output of the processes. The script reads only its size [Ref10].
- **rc**: the exit status of a benchmark process, as rx.sh writes it into launches.txt with the end time. `rc 0` means that the process ended without an error.
- **Spec file**: a file with one line `tag|arguments`. rx.sh starts one bwx12 process with these arguments. like.spec is the line of part L and of control I. cfwd.spec and crev.spec are the two lines of part C.
- **Tag**: a short name. A folder tag such as T72A1, T72L2, T72C4 or T72I1 names one step of the rerun: the part and the session or process number. A process tag such as `a6456` is the first field of a spec line and the name of the csv file.
- **Step of the rerun, event**: one entry of `D['events']`: one session of part A (24 processes) or one bwx12 process. The rerun has 12 steps.
- **`gap_s`, start state**: `gap_s` is the time in seconds from the end of the previous step of the rerun to the first launch of this step, at 1 s resolution. The start state is a sentence built from it, for example "started 5 s after the 120-thread bwx12 process T72L1". The first step (T72A1) has no `gap_s`. Its sentence is built from the seconds since the first state line of the go.sh log.
- **`kernel_before`**: the kernel that was timed directly before an interval. bwx runners: the previous kernel of the sequence in the same process (for position 0 of round 1 it is the last kernel of the sequence). Part A: binary and kernel of the previous process in the same csv file. The first interval of a bwx process and the first process of a part A file get a text that starts with `none`. In A-3 the second and the third process get the text `not listed (other processes of the file ran in between)`, because the list holds 3 of the 12 processes of `A3.csv` (lines 124 to 129).
- **`proc_key`**: a text that is equal for all records of one process: folder, file, and the process number or the tag.
- **64+56 test, `is_64_56`**: true when an interval has 64 T rows on CPUs 0-63 and 56 T rows on CPUs 64-119, on 120 different CPUs.
- **Flag, `flagged`**: the last column of a T row. `-` means no flag. `flagged` is the number of T rows of an interval with another value. stat_bwx.py says that the runner writes `late` for a thread that started more than 100 us (microseconds) after the common start.
- **THP, huge pages**: transparent huge pages, the Linux feature that puts a buffer on 2 MiB pages. In a P row `kB_total` is the size of the buffer and `kB_huge` is the part of it on huge pages [Ref12].
- **`thp_fault_fallback`**: a column of a P row. bwx12 copies it from the Linux file `/proc/vmstat`, where it counts for the whole system [Ref12]. Linux adds 1 to it when a page fault cannot get a huge page and uses small pages in its place [Ref15]. Check `P-rows` prints its values and does not test them.
- **Load average, `load1`**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes. `load1` is the 1-minute value.
- **Runnable tasks**: the first number of the fourth field of `/proc/loadavg`: the tasks that are runnable at that moment.
- **Logins**: the number of logged-in users. The run scripts count them with `who | wc -l`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. The run scripts stop when it exists. A state line says `marker absent` or `marker present`.
- **Process window**: the time from the `launch` line to the `rc` line of a process in launches.txt. Both lines give whole seconds.
- **Linux kernel release**: the version text of the operating system kernel, as the command `uname -r` prints it.
- **sha256**: a checksum of a file, written as 64 hexadecimal digits. Equal values mean equal file content.
- **try6.txt**: the file `R/dimm7200-20261117/try6.txt`, written about 2 h 10 min before the rerun in the same boot. It holds the time, the boot id, MemTotal, the Linux message "This system has 12 DIMM sockets", and a count line: 12 entries with "Configured Memory Speed: 7200 MT/s". The module count of the records comes from the DIMM sockets line.
- **`boot72`**: the three fields that every record of the rerun gets: `speed_MTps` = 7200, `modules` = 12 and `boot` = the boot id of the rerun. The values are read from `try6.txt`. The records of F72d12 get the same three fields. The folder of F72d12 holds no boot id. Line 242 requires that its process ran between two readings of this boot id: `try6.txt` before it, and the first state line of the go.sh log after it.
- **`boots.txt`, `gaps.txt`**: two files in `R/dimm7200-20261117`. boots.txt lists the boots of the journal, one per row, with a boot number, the boot id, a first time and a last time. gaps.txt gives per boot the first and the last time of the Linux kernel log, a DIMM count and the number after `hwerr=`. Row 0 of boots.txt holds the boot id of the rerun, and the script takes row 0 of gaps.txt as the same boot. The last time of each row 0 is the time at which the file was written (20:06:19 and 20:06:34 UTC), about 2 h before the rerun.
- **DIMM report, boot table**: the file `/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md`, outside `R`. Its boot table lists each boot with a number, the Linux start time and the module count. It also gives the time until which the memory speed was 8000 MT/s.
- **Journal, Linux kernel log**: saved system logs of one boot in `R/dimm-check-20261117`. `h-5.txt` (journal) and `k-5.txt` (Linux kernel log) belong to the boot that started on 2026-11-09. Every baseline ran in that boot [Ref3]. `h-1.txt` and `k-1.txt` belong to a boot of 2026-11-17 with 10 modules.
- **Module list, `dmidecode`**: the file `R/dimm7200-20261117/dmi17-7200.txt`, saved in the boot of the rerun. It is output of the tool `dmidecode`, which prints the hardware table of the firmware. It holds 12 entries `Memory Device`, each with lines such as `Size: 32 GB` and `Configured Memory Speed: 7200 MT/s`.
- **`D['mod']`**: the dictionary that `open_mod` returns: the DIMM sockets message of a boot with 10 modules, the line `Memory: ...K/...K available` of two Linux kernel logs, line counts of the module list, and the value and the line number of the line `modules=` of `try6.txt`.
- **Hardware error record**: one journal line "Hardware error from APEI Generic Hardware Error Source" (APEI = ACPI Platform Error Interface). A later line with the same record number gives the severity, for example "corrected".
- **Span of a hardware error record**: the range from `off` - 1 to `off` + 1 seconds after the process start, where `off` is the journal time of the record minus the launch time. The record lies somewhere in this range, because both times are whole seconds.
- **Partner, other round**: the interval with the same kernel and the same position in the other round of the same process.
- **Firmware settings tool, uefisettings**: a tool that reads and sets firmware settings. `questions.json` is a saved list of all settings (name, answer, options, help). `set.txt` holds the replies of the `set` calls. "DIMM Frequency" is the setting of the memory speed.
- **TXREQ Max, TXREQ Min**: two firmware settings. The `set` calls saved in the folder `R/fwtest-20261117` changed them and then set them back. Their help texts say: maximum and minimum outstanding TXREQ transactions from the L2 transaction queue. FACTS.md describes the TXREQ settings as firmware settings that limit the read requests of the cores [Ref4].
- **setting-final.txt**: a file of the folder `R/dimm7200-20261117` with one line: `answer: "7200 MT/s",`. The comment of `open_fw` calls it the last reading of the memory speed setting. The line itself does not name the setting.
- **One-thread phase**: the first part of the test of 2026-11-13: processes with one thread, run before the 120-thread part. Its result file is `one-thread.csv`. The rerun did not repeat it.
- **`D['probe13']`, `p13`**: the dictionary that `open_probe13` returns: the sha256 values and the times of `probe.txt` of 2026-11-13, the number and the times of the header lines of the one-thread phase, facts of the journal of that boot (start, module count, hardware error records in the time spans of the baselines), and saved machine settings.
- **stat_k120.py, stat_bwx.py**: two smaller statistics tools in `S`. stat_k120.py reads `threads120.csv`. stat_bwx.py reads bwx csv files. This script uses them as a second reader (checks `x-k120` and `x-bwx`).
- **Second reader**: another script that reads the same data with its own code (stat_k120.py or stat_bwx.py). A check compares its values with the values of this script. For A-2 and A-3 stat_k120.py reads the copies under `S/base8000`, and this script reads the raw files.
- **`S/base8000`**: a folder with two copies in the form of `threads120.csv`, read by stat_k120.py. `partA-A1` is `A1.csv` (baseline A-2) with the header line of each process rewritten into the `-- binary` form. `partA-A3-onebuf500` holds the three processes of baseline A-3 in the same form. Inside these processes only the header lines differ from the raw files.

</details>

## Main flow

1. The script imports `facts_data.py` under the name `fd` and takes the folder names `R` and `S` from it. It sets four constants: the paths of the two driver logs (`GO_LOG`, `GO2_LOG`), the filter `POS01` and the kernel list `READ3` (lines 17-31).
2. When the file is run as a script, Python calls `main`. The script takes one optional argument, `--print`. This file reads no environment variable (lines 1055-1056).
3. `main` calls `collect` (line 1035). `collect` first reads the machine records. `fd.read_try6` reads `try6.txt`, the record of the boot of the rerun: boot id, MemTotal, 12 memory modules, 7200 MT/s. It also reads `boots.txt` and `gaps.txt`. `fd.read_boot_table` reads the DIMM report: the module count of each earlier boot and the time until which the memory speed was 8000 MT/s. `state_of` (line 58) uses them for the earlier result folders only. `fd.read_log` reads the logs of go.sh and go2.sh (lines 50-56).
4. Part A of the rerun: for each of the 3 sessions it finds the folder `R/k120-T72A1-<time>` (then T72A2, T72A3) and reads `probe.txt` and `threads120.csv`. The reader `fd.read_k120` keeps the rows whose column `rep` is a number. So it leaves out the `best` row and the column header row of each process [Ref1] (lines 66-72).
5. Parts L and C and control I: for each of the 9 folders `R/w120-<tag>-<time>` (tags T72L1 to T72L3, T72C1 to T72C4, T72I1, T72I2) it reads the one csv file, `env.txt` and `launches.txt`, and it takes the size of `stderr.txt`. `fd.read_bwx` stores the T rows by round, position and kernel. For each such group `fd.bwx_intervals` adds bytes / elapsed_s / 1e9 over the threads [Ref1] (lines 73-86).
6. It puts the 12 steps of the rerun (3 sessions of part A and 9 bwx12 processes) in time order. For each step it computes `gap_s`, the seconds from the end of the step before to the first launch of this step, and it builds a sentence that describes the start state (lines 88-117).
7. It builds the records of the rerun. `add_k120` (line 119) appends one record per interval row of part A, with `GBps` = the csv column `aggregate_GBps`. `add_bwx` (line 142) appends one record per bwx12 interval, with `GBps` = the sum over the T rows. No interval of the rerun is left out: all kernels of every process become records (lines 119-180).
8. It reads the 8000 MT/s baselines of part A and builds their records: A-1 (`threads120.csv` of 2026-11-13), A-2 (`A1.csv`) and A-3 (the 3 processes of `A3.csv` with the tags `onebuf-ms500-1` to `onebuf-ms500-3`). `open_probe13` reads the other records of the 2026-11-13 run (lines 182-204).
9. It reads 17 csv files of 11 earlier data sets of bwx12 and bwx11 (L-1 to L-4, R0, R0b, X2d12, X1d10, X1d10b, BASEd10, F72d12) and builds their records. For 8 of these sets the filter `POS01` keeps only oldread at position 0 and asmread at position 1. For L-1, X2d12 and F72d12 every interval is kept (lines 206-255).
10. It reads 8 data sets of the first runner bwx (files `B7.csv`, `C3.csv`, `B5.csv` in 6 folders). It keeps the sections whose tag starts with the prefix of the data set. In them it keeps only the kernels oldread, read and asmread (`READ3`) (lines 257-284).
11. It adds additional records that hold no rate of the rerun: the hardware error records of the 8000 MT/s boot (`hw_records`, `hw_compare`), the firmware settings (`open_fw`), the run before baseline A-2 (`open_a2pre`), and the proof of the module count (`open_mod`). Then `collect` returns `D` (lines 285-290).
12. `main` calls `run_checks` (line 1036). It appends 27 checks to `D['checks']`. Each check has a key, a pass flag and one line of text. For the checks it also reads the three spec files, go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, and the two checksum lists `local.sha` and `go2.sha`. The second readers read csv files again. stat_k120.py reads the part A files (for A-2 and A-3 the copies under `S/base8000`). stat_bwx.py reads the csv files of the 20 bwx12 and bwx11 folders. No second reader reads the csv files of the first runner bwx (lines 653-894).
13. `main` calls `render` of `facts_text.py`. `render` computes the ranges, the medians and the percent values from the field `GBps` of the records. It returns the verdicts `V` and the text of FACTS.md [Ref2]. For the text, `render` and `section4` open two more input files: the rules file and `FINDINGS.md`. `render` ends the script here when a check failed, or when the data do not show the pattern of a sentence of the text [Ref11]. Then no output file is written (line 1037).
14. `main` calls `write_json` (line 1038). It writes `S/facts.json` with three parts: `meta`, `verdicts`, and `intervals` (one line per record). Every float of the verdicts and of the records is rounded to 3 decimal places in this file (lines 899-1030).
15. `main` writes the text to `S/FACTS.md.tmp` and then renames that file to `S/FACTS.md` (lines 1039-1041).
16. With `--print` it prints the text of FACTS.md. It prints the number of checks, the number of failed checks, one line per failed check, the number of records and the two verdicts. Line 1052 would end the script with the exit status 1 when a check failed. But `render` ends the script before these lines when a check failed. So in the present code they run only when every check passed. The script then prints `failed: 0` and ends with the exit status 0 (lines 1042-1052).

## Behavior a reader must know

- **Rate of part A.** The script does not compute it. `add_k120` copies column 7 (`aggregate_GBps`) of each interval row of a part A csv into the field `GBps` (line 134). The csv is `threads120.csv`, or `A1.csv` and `A3.csv` for the baselines A-2 and A-3. The benchmark binary computed this value as the sum of the bytes of all threads divided by the longest per-thread elapsed time [Ref7]. The binary prints it with 2 decimal places (checked in the 216 interval rows of the 3 files of the rerun).
- **Rate of the bwx runners (bwx12, bwx11, bwx).** `add_bwx` takes `GBps` from `fd.bwx_intervals` (lines 145 and 153). That function computes bytes / elapsed_s / 1e9 for each T row (one thread) and adds the values of all T rows with the same round, position and kernel [Ref1]. So the bytes of each thread are divided by the elapsed time of that thread. In a T row `bytes` is column 7, `elapsed_s` is column 8 and `cpu` is column 6 [Ref8]. `mesh0_GBps` is the same sum over the threads on CPUs 0-63. `mesh1_GBps` is the sum over the threads on CPUs 64 and above.
- The two formulas differ. The field `rate_kind` of each record says which formula gave its `GBps`. The part A formula divides the bytes of all threads by one time, the longest per-thread time. The bwx formula divides the bytes of each thread by the time of that thread. So for the same threads the part A formula gives the lower value, or an equal one. Example from part A: the first interval row of `threads120.csv` of T72A1 (bw_old, kernel read) holds `aggregate_GBps` = 467.83 GB/s. Its column `per_thread_avg_GBps` holds 3.99 GB/s, the average of the 120 per-thread rates [Ref13]. The bwx formula would give the sum of these 120 rates: 120 x 3.99 GB/s = 478.8 GB/s (est., because the binary rounds the average to 0.01 GB/s) [Ref7]. Example from bwx12: the I row of an interval holds `aggregate_GBps`, which bwx12 computes with the part A formula [Ref8]. In the 9 files of the rerun the largest difference between this value and the sum over the T rows of the same interval is 0.018 GB/s (text of check `I-agg`, which prints 3 decimal places) [Ref9].
- The column `aggregate_GBps` of the I row of a bwx csv is not used as the rate. Check `I-agg` (lines 736 to 740) compares it with the sum over the T rows of the same interval. The check passes when the largest difference in the 9 files of the rerun is below 0.05 GB/s. Example: in `a6456.csv` of T72L1 the I row of the first oldread interval holds 462.29 GB/s, and the 120 T rows of the same interval sum to 462.300 GB/s [Ref8].
- **Rows that are left out.** Part A: the `best` row, the column header row and the per-thread rows (`thread,...`) of a process are not interval rows [Ref1]. A-3: only the processes of `A3.csv` with the tags `onebuf-ms500-1`, `-2`, `-3` are kept (line 189). Earlier folders of bwx12 and bwx11: only the csv files that the list `rx_sets` names give records (lines 207 to 221). These are 17 of the 52 csv files of the 11 folders. Data sets with the filter `POS01`: only oldread at position 0 and asmread at position 1 are kept (line 148). Data sets of the first runner bwx: only the sections whose tag starts with the prefix, and only the kernels of `READ3` (lines 276 and 280).
- No row is left out because of its value. A T row with a flag other than `-` stays in the sum. The field `flagged` counts such rows.
- **How the records name the two kernels.** Old read kernel: `binary` = `bw_old` with `kernel` = `read` in part A, and `kernel` = `oldread` in the bwx data sets. New read kernel: `binary` = `bw_new` with `kernel` = `read` in part A, and `kernel` = `read` in the bwx12 data sets. Among the bwx12 records only the data set `rerun-C` holds this kernel. The 8 data sets of the first runner bwx hold a kernel `read` too. The rules file counts it as the new read kernel, measured with another binary [Ref3]. Part L has no kernel `read`. The rules file uses asmread in its place there [Ref3].
- **No statistics in this file.** This file computes no minimum, no median, no maximum and no percent drop of a kernel. `facts_text.py` and `facts_text4.py` compute them from the records [Ref2] [Ref11]. The only arithmetic on rates here is in the checks `I-agg` and `x-bwx` and in the hardware error view (`hw_compare`, `hw_compare_json`: rate of one round minus rate of the other round).
- **Rounding.** The records in memory hold the values as parsed or summed. `facts_text.py` gets these unrounded values, and FACTS.md shows rates to 0.01 GB/s, rounded half up [Ref2]. In this file only `write_json` rounds, with the Python function `round`. Every float of the verdicts (through `r3all`) and of each record (line 1027) is rounded to 3 decimal places, which is 0.001 GB/s for a rate. In `meta` the rates and the interval times are rounded to 3 decimal places where they are built (lines 994 to 996 and `hw_compare_json`).
- **How the rates are compared in the checks.** `x-k120` requires exact equality with the values that stat_k120.py reads: rate, per-thread minimum, per-thread maximum and pass count of every interval row (lines 799 to 815) [Ref5]. It also requires the same binary name and kernel name for every process. `x-k120` covers all 333 interval rows of part A that give a record: the 3 sessions of the rerun, A-1, A-2 and A-3. `x-bwx` requires that the total and the two sums per mesh differ from the values of stat_bwx.py by at most 1e-9 GB/s (lines 816 to 834) [Ref6]. It also requires the same result of the 64+56 test and the same number of flagged T rows for every interval. `x-bwx` covers the csv files that this script reads from the 9 folders of the rerun and from the 11 folders of the earlier bwx12 and bwx11 data sets: 26 files with 297 intervals. It covers every interval of these files, also the intervals that the filter `POS01` keeps out of the records. It does not cover the 8 data sets of the first runner bwx (312 records). Limit of both checks: they show that two readers take the same numbers from the same rows. They do not test the formula of the rate. stat_bwx.py uses the same formula as `fd.bwx_intervals`: the sum over the T rows of bytes / elapsed_s / 1e9 [Ref6]. `fd.read_k120` finds the `-- binary` header lines with the pattern `HDR`, which it takes from stat_k120.py [Ref1].
- **The 27 checks, by key, in groups.** Logs and machine state: `log-go`, `log-go2`, `boot`, `memtotal`, `logins`, `uname`, `runnable`. Row counts and content of the files: `A-shape`, `A-order`, `I-rows`, `rc`, `stderr`, `6456`, `flags`, `P-rows`. Rates: `I-agg`, `x-k120`, `x-bwx`. Arguments: `args`, `args-R8`, `A-args`. Checksums: `sha-bw`, `sha-ra`, `sha-bwx12`, `sha-local`, `sha-rx`. Earlier data: `earlier`. All 27 passed in the build of 2026-11-17 [Ref9]. Since 2026-11-24 a new build fails `sha-local` (check 20 of the facts sheet). Line 20 of go.sh was edited on that day. So go.sh no longer has the sha256 that `local.sha` lists for it. The build then stops before it writes a file [Ref17].
- **What the checksum checks of the binaries compare.** The binary files bw_old, bw_new and bwx12 are not in the local folders. So this file computes no sha256 of a binary. It compares values that the run scripts recorded on CRB. `sha-bw` (lines 753 to 760): the values of bw_old and bw_new in the 3 `probe.txt` files of part A must be equal to those in `probe.txt` of the first test of 2026-11-13 (folder `R/kernels-20261113T181222Z`). `env.txt` of the folder of A-2 must hold the same two values. `sha-bwx12` (lines 764 to 771): the 9 `env.txt` files of the rerun must hold one value, equal to the line `SHA=` of the local go.sh. `env.txt` of the 9 earlier bwx12 data sets must hold this value too. This file computes a sha256 itself only for local text files: go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh and the three spec files.
- The order of the checks is the order of the `chk` calls in `run_checks`. FACTS.md numbers the checks in this order [Ref4]. The checks `sha-rx` and `A-args` were added last, at the end of the list. The comments at lines 844 and 867 give the reason: the numbers of the earlier checks stay as they were. The text of check `sha-rx` names check `sha-local` by its number. Line 866 computes this number from the position of `sha-local` in the list.
- **A failed check stops the script before any file is written.** `run_checks` only records the result of each check. But `render` calls `section4` of `facts_text4.py`, and that function ends the script unless every check passed [Ref11]. This stop prints the message `facts_text.py: the data do not show the pattern of a sentence: all integrity checks pass`, and the exit status is 1. So the list `bad` of `main` (line 1044) is always empty in the present code. No `FAILED` line is printed (line 1047), and line 1052 (exit status 1) does not run. An `assert` that fails (29 `assert` statements in this file) also ends the script before any file is written. Every other stop inside `facts_data.py`, `facts_text.py` or `facts_text4.py` does the same. The reason: both files are written at the end of `main`.
- **Records in the build of 2026-11-17: 793 records [Ref9].** rerun-A: 216 (3 sessions x 24 processes x 3 intervals). rerun-L: 30 (3 processes x 10 intervals). rerun-C: 24 (4 processes x 6 intervals). control-I: 20 (2 processes x 10 intervals). A-1: 72. A-2: 36. A-3: 9. The 11 earlier data sets of bwx12 and bwx11: 74. The 8 data sets of the first runner bwx: 312.
- In part A the field `gap_s` is set on the records of the first process of a session only. ra.sh starts processes 2 to 24 directly after the process before (line 171). In session 1 the field is `None` for the first process too, because no step of the rerun ran before it.
- The script reads its input files and changes none of them. It starts no benchmark and contacts no machine. It writes two files, `S/facts.json` and `S/FACTS.md`. Each is written under a temporary name and then renamed, so a reader never sees a part of a file. Line 23 tells Python to write no compiled copies of the imported modules (no `__pycache__` folder).
- Every file opened through `fd._open` is added to the list `fd.OPENED`. `facts_text.py` stops when a file of this list is missing in the file list of FACTS.md section 7 [Ref2]. Lines 83, 234 and 805 add a file to the list with a direct `append` call, because the script takes only its size or another tool opens it. The list does not hold every file that is read. stat_bwx.py opens every csv file of a folder with its own `open` call. So for check `x-bwx` it also reads 35 csv files of the earlier folders that this script does not read, for example `a0001.csv` in the folder of L-1. Their rows are not compared, and they give no record. `section4` opens `FINDINGS.md` with its own `open` call too. `facts_text.py` adds that file to the file list directly [Ref2].

## Call sequence in the whole-chip test

- `main` (line 1033): entry point: collect, check, render, then write the two output files
  - `collect` (line 50): reads the result files and saved machine records, builds the dictionary `D`
    - `facts_data.py:read_try6`: boot of the rerun: boot id, MemTotal, 12 modules, 7200 MT/s
    - `facts_data.py:read_boot_table`: boot table of the DIMM report, used for the earlier folders
    - `facts_data.py:read_log`: called twice: log of go.sh, then log of go2.sh
    - `facts_data.py:find`: the one result folder of each tag of the rerun
    - `facts_data.py:read_probe`: probe.txt of each part A folder
    - `facts_data.py:read_k120`: part A: processes and interval rows of 3 threads120.csv files
    - `facts_data.py:read_bwx`: parts L, C, I: the I, T and P rows of 9 csv files
    - `facts_data.py:bwx_intervals`: per interval: sum over the T rows of bytes / elapsed_s / 1e9
    - `facts_data.py:read_env`: env.txt: Linux kernel release and sha256 of bwx12
    - `facts_data.py:read_launches`: launches.txt: launch time, load, arguments, exit status
    - `facts_data.py:folder_date`: the time in a folder name, for the 12 steps of the rerun
    - `facts_data.py:clock`: turns a time of day of a run file into date and time
    - `add_k120` (line 119): rerun part A: 3 calls, one record per interval row
      - `iso` (line 34): formats the launch time of the process
      - `facts_data.py:base_record`: returns a record with every key, filled from the arguments
    - `add_bwx` (line 142): rerun parts L, C, I: 9 calls, one record per interval
      - `facts_data.py:bwx_intervals`: gives the rate of each interval (sum over its T rows)
      - `facts_data.py:base_record`: returns a record with every key, filled from the arguments
    - `facts_data.py:read_k120`: 8000 MT/s baselines A-1, A-2 and A-3
    - `open_probe13` (line 568): records of the 2026-11-13 run and the journal of its boot
      - `facts_data.py:read_error_records`: hardware error records of the saved journal
      - `facts_data.py:step_headers`: header lines of A1.csv, A2.csv and A3.csv
    - `state_of` (line 58): memory speed, module count and boot label of an earlier folder
      - `boot_of` (line 44): the boot of the DIMM report that contains a time
    - `add_k120` (line 119): baselines A-1, A-2, A-3: 3 calls
    - `add_bwx` (line 142): 17 earlier csv files of bwx12 and bwx11, 8 data sets with `POS01`
    - `add_bwx` (line 142): sections of the first runner bwx, kernels of `READ3` only
    - `hw_records` (line 296): hardware error records inside the process windows of 6 data sets
      - `facts_data.py:read_error_records`: hardware error records of the saved journal
      - `facts_data.py:bwx_intervals`: start time and end time of every interval of a process
    - `hw_compare` (line 340): intervals with a record against the same interval of the other round
      - `cmp_` (line 363): one interval, its partner, and the difference of the two rates
        - `other` (line 358): the interval of the same kernel and position in the other round
    - `open_fw` (line 429): saved firmware setting lists and replies of the settings tool
    - `open_a2pre` (line 509): the run folder that ended shortly before baseline A-2
      - `facts_data.py:step_headers`: header lines of A5.csv and A6.csv
    - `open_mod` (line 536): a 10-module boot, read for the two lines that prove 12 modules
  - `run_checks` (line 653): 27 checks, appended to `D['checks']` in a fixed order
    - `chk` (line 661): appends one check: key, pass flag, text
    - `per` (line 664): builds a text with one value per rerun folder
    - `facts_data.py:sha256`: checksums of the local scripts and spec files
    - `stat_k120.py:load`: second reader of the part A files, for check `x-k120`
    - `stat_bwx.py:interval_rows`: second reader of the bwx csv files, for check `x-bwx`
    - `facts_data.py:bwx_intervals`: the rates of this script, compared with those of stat_bwx.py
  - `facts_text.py:render`: ranges, medians, percent values, verdicts and the text of FACTS.md
    - `facts_text4.py:section4`: sections 4 to 6 of FACTS.md, ends the script unless every check passed
  - `write_json` (line 899): writes facts.json, rates rounded to 0.001 GB/s
    - `facts_data.py:sel`: selects records by field values, for the counts in `meta`
    - `iso` (line 34): formats every time of `meta`
    - `r3` (line 38): line 996: rate of an interval that holds or may hold an error record
    - `hw_compare_json` (line 400): the hardware error view in the form of facts.json
      - `r3` (line 38): rounds one number to 3 decimal places
    - `r3all` (line 1017): rounds every float of the verdicts
      - `r3` (line 38): rounds one number to 3 decimal places
    - `r3` (line 38): line 1027: rounds every float of each record

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `iso` | 34-35 | Formats a date and time as text such as `2026-11-17T22:12:14Z`. | - | - |
| `r3` | 38-39 | Rounds a number to 3 decimal places. Returns `None` for `None`. | - | - |
| `boot_of` | 44-47 | Returns the last boot of the DIMM report table whose Linux start time is not after the time `t`. | - | - |
| `collect` | 50-290 | Reads the raw result files and the saved machine records. Returns `D`: interval records, rerun folders, baselines, steps in time order, additional records. | `facts_data.py:read_try6`, `facts_data.py:read_boot_table`, `facts_data.py:read_log`, `facts_data.py:find`, `facts_data.py:read_probe`, `facts_data.py:read_k120`, `facts_data.py:read_bwx`, `facts_data.py:bwx_intervals`, `facts_data.py:read_env`, `facts_data.py:read_launches`, `facts_data.py:folder_date`, `facts_data.py:clock`, `add_k120`, `add_bwx`, `iso`, `open_probe13`, `facts_data.py:_open`, `state_of`, `hw_records`, `hw_compare`, `open_fw`, `open_a2pre`, `open_mod` | - |
| `state_of` | 58-64 | Nested in `collect`. Returns memory speed, module count and boot label of an earlier result folder, from the boot table of the DIMM report. | `facts_data.py:folder_date`, `boot_of` | - |
| `add_k120` | 119-140 | Nested in `collect`. Appends one record per interval row of bandwidth.c processes. `GBps` is the csv column `aggregate_GBps`, copied unchanged. | `facts_data.py:rel`, `iso`, `facts_data.py:clock`, `facts_data.py:base_record` | - |
| `add_bwx` | 142-160 | Nested in `collect`. Appends one record per interval of a bwx section. `GBps` is the sum over its T rows. Optional kernel and position filters. | `facts_data.py:bwx_intervals`, `facts_data.py:rel`, `facts_data.py:base_record` | - |
| `hw_records` | 296-337 | Finds the hardware error records of the saved journal inside the process windows of L-1 to L-4, R0, R0b. Tests each record against each interval. | `facts_data.py:read_error_records`, `facts_data.py:bwx_intervals` | - |
| `hw_compare` | 340-397 | For each interval with an error record: the rate minus the rate of the same kernel and position in the other round of the process. | `cmp_` | - |
| `other` | 358-361 | Nested in `hw_compare`. Returns the interval with the same position and kernel in the other round. | - | - |
| `cmp_` | 363-365 | Nested in `hw_compare`. Returns an interval, its partner of the other round, and the difference of the two rates in GB/s. | `other` | - |
| `hw_compare_json` | 400-426 | Turns the result of `hw_compare` into the form that facts.json stores. Rates are rounded to 0.001 GB/s. | `r3`, `facts_data.py:rel` | - |
| `open_fw` | 429-506 | Reads the saved firmware setting lists and the replies of the settings tool under `R`. Checks that no other such file exists. | `facts_data.py:_open` | - |
| `open_a2pre` | 509-533 | Reads the times and the process header lines of the run folder that ended shortly before the first process of baseline A-2. | `facts_data.py:_open`, `facts_data.py:step_headers` | - |
| `open_mod` | 536-565 | Reads what a boot with 10 modules shows in journal and Linux kernel log, and the module list saved in the boot of the rerun. | `facts_data.py:_open` | - |
| `open_probe13` | 568-648 | Reads the records of the 2026-11-13 run: checksums and times of probe.txt, the one-thread phase, error records of the journal, saved machine settings. | `facts_data.py:_open`, `facts_data.py:read_error_records`, `facts_data.py:step_headers` | - |
| `run_checks` | 653-894 | Appends 27 integrity checks to `D['checks']`: logs, boot id, row counts, thread placement, checksums, arguments, and two cross-checks of the rates. | `chk`, `per`, `facts_data.py:rel`, `facts_data.py:_open`, `facts_data.py:sha256`, `stat_k120.py:load`, `stat_bwx.py:interval_rows`, `facts_data.py:bwx_intervals` | - |
| `chk` | 661-662 | Nested in `run_checks`. Appends one check: key, pass flag, text. | - | - |
| `per` | 664-666 | Nested in `run_checks`. Builds a text such as `T72L1 10, T72L2 10` from a list of rerun folders and a function. | - | - |
| `write_json` | 899-1030 | Writes facts.json: `meta`, `verdicts`, and one line per interval record. Floats of verdicts and records are rounded to 3 decimal places. | `facts_data.py:sel`, `iso`, `facts_data.py:rel`, `hw_compare_json`, `r3all`, `r3` | - |
| `r3all` | 1017-1024 | Nested in `write_json`. Rounds every float inside nested dictionaries and lists to 3 decimal places. | `r3`, `r3all` | - |
| `main` | 1033-1052 | Entry point. Collects, checks, renders, writes facts.json and FACTS.md, prints check counts and verdicts. A failed check stops the script in `render`, before the writes. | `collect`, `run_checks`, `facts_text.py:render`, `write_json` | - |

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>File comment: inputs, outputs and usage</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">   1  #!/usr/bin/env python3
   2  """build_facts.py - builds the facts sheet of the 7200 MT/s whole-chip rerun of 2026-11-17.
   3
   4  Reads:  raw result files under R, the converted baseline copies under S/base8000, the scripts in S,
   5          and three records outside R (the DIMM report, FINDINGS.md of 2026-11-15, run_kernels.sh of 2026-11-13).
   6  Writes: S/facts.json and S/FACTS.md. It changes no other file.
   7
   8  Every number in FACTS.md is formatted by this script from a value that it read or computed.
   9  No measured number is typed by hand in the text templates of facts_text.py and facts_text4.py.
  10
  11  Usage: python3 build_facts.py            write both files, print the checks and the verdicts
  12         python3 build_facts.py --print    also print FACTS.md
  13
  14  Files: facts_data.py (parsers, range functions), build_facts.py (records, integrity checks, facts.json),
  15         facts_text.py and facts_text4.py (statistics, verdicts, text of FACTS.md).
  16  """</pre></td><td valign="top">The script reads raw result files and scripts. It writes two files, <code>S/facts.json</code> and <code>S/FACTS.md</code>, and it changes no other file. The comment says that every number in FACTS.md is formatted from a value that the script read or computed. The option <code>--print</code> also prints FACTS.md.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  17  import glob
  18  import json
  19  import os
  20  import re
  21  import sys
  22
  23  sys.dont_write_bytecode = True
  24
  25  import facts_data as fd                     # noqa: E402
  26  from facts_data import R, S, rel            # noqa: E402</pre></td><td valign="top">Imports of the Python standard library and of <code>facts_data.py</code>.<ul><li><code>sys.dont_write_bytecode = True</code>: Python writes no compiled copy (<code>.pyc</code> file) of the modules that are imported after this line.</li><li><code>facts_data.py</code> is imported under the name <code>fd</code>. The names <code>R</code>, <code>S</code> and <code>rel</code> come from it. <code>rel</code> shortens a path to the form <code>R/...</code> or <code>S/...</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Constants</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  27
  28  GO_LOG = os.path.join(R, 'go-T72-20261117T221209Z.log')
  29  GO2_LOG = os.path.join(R, 'go2-T72-20261117T222335Z.log')
  30  POS01 = {('oldread', 0), ('asmread', 1)}    # the positions of part L: oldread first, asmread directly after it
  31  READ3 = ('oldread', 'read', 'asmread')
  32
  33</pre></td><td valign="top"><ul><li><code>GO_LOG</code>, <code>GO2_LOG</code>: the logs of go.sh and go2.sh in <code>R</code>.</li><li><code>POS01</code>: a set of two pairs (kernel, position): <code>oldread</code> at position 0 and <code>asmread</code> at position 1. <code>add_bwx</code> (line 142) uses it as a filter for 8 earlier data sets.</li><li><code>READ3</code>: the kernel names <code>oldread</code>, <code>read</code> and <code>asmread</code>. Line 280 uses it as a filter for the data sets of the first runner bwx.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>iso</code>: date and time as text</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  34  def iso(t):
  35      return t.strftime('%Y-%m-%dT%H:%M:%SZ')
  36
  37</pre></td><td valign="top">Formats a date and time as text, for example <code>2026-11-17T22:12:14Z</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>r3</code>: round to 3 decimal places</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  38  def r3(x):
  39      return None if x is None else round(x, 3)
  40
  41</pre></td><td valign="top">Rounds a number to 3 decimal places with the Python function <code>round</code>. For a rate that is 0.001 GB/s. <code>None</code> stays <code>None</code>.<ul><li>Two functions call it: <code>hw_compare_json</code> (line 400) and <code>write_json</code> (line 899).</li><li>The records in memory are not rounded.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>boot_of</code>: the boot at a given time</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  42  # ----------------------------------------------------------------------------- collection
  43
  44  def boot_of(table, t):
  45      """Boot of the DIMM report table that contains time t."""
  46      cand = [b for b in table['boots'] if b['start'] &lt;= t]
  47      return cand[-1]
  48
  49</pre></td><td valign="top"><code>table['boots']</code> is the boot list of the DIMM report, sorted by Linux start time. The function returns the last boot whose start time is not after the time <code>t</code>. The script takes this boot as the boot that ran at the time <code>t</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>collect</code>: read all input files and build the records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  50  def collect():
  51      D = dict(recs=[], checks=[])
  52      recs = D['recs']
  53      try6 = D['try6'] = fd.read_try6()
  54      bt = D['boot_table'] = fd.read_boot_table()
  55      logs = D['logs'] = dict(go=fd.read_log(GO_LOG), go2=fd.read_log(GO2_LOG))
  56      boot72 = dict(speed_MTps=try6['speed_MTps'], modules=try6['dimm_sockets'], boot=try6['boot'])
  57</pre></td><td valign="top"><code>D</code> is the dictionary that the function returns at the end. <code>recs</code> is the list of all interval records. <code>checks</code> stays empty until <code>run_checks</code> (line 653) fills it.<ul><li><code>try6</code>: the values of <code>try6.txt</code>, the record of the boot of the rerun. <code>fd.read_try6</code> also reads the first and the last time of row 0 of <code>boots.txt</code> and of <code>gaps.txt</code>. It stops the script when row 0 of <code>boots.txt</code> does not hold the boot id of <code>try6.txt</code>.</li><li><code>bt</code>: the boot table of the DIMM report.</li><li><code>logs</code>: the lines of the two driver logs, with the state lines parsed.</li><li><code>boot72</code>: three fields that every record of the rerun gets. All three are read from <code>try6.txt</code>. <code>speed_MTps</code> is 7200, the speed in the line that ends with <code>Configured Memory Speed: 7200 MT/s</code>. <code>modules</code> is 12, the number in the Linux message <code>This system has 12 DIMM sockets</code>. <code>boot</code> is the boot id. The file also holds a line <code>modules=24</code>. No record field comes from that line.</li><li>The result folders of the rerun are not read for these fields. Check <code>boot</code> (line 679) tests that every state line of the two logs and the 3 <code>probe.txt</code> files of part A hold this boot id.</li></ul></td></tr>
<tr><td colspan="2"><b>Nested function <code>state_of</code>: speed, modules and boot of an earlier folder</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  58      def state_of(folder):
  59          """speed, modules and boot label of an earlier result folder, from the boot table of the DIMM report."""
  60          t = fd.folder_date(folder)
  61          assert t &lt; bt['until']['utc'], folder
  62          b = boot_of(bt, t)
  63          return dict(speed_MTps=bt['until']['speed'], modules=b['modules'],
  64                      boot='boot %d of the DIMM report (Linux start %s UTC)' % (b['no'], b['start'].strftime('%Y-%m-%d %H:%M')))
  65</pre></td><td valign="top">Returns the fields <code>speed_MTps</code>, <code>modules</code> and <code>boot</code> for a result folder of an earlier run. <code>t</code> is the time in the folder name.<ul><li>The <code>assert</code> stops the script when <code>t</code> is not before the time until which the memory speed was 8000 MT/s. The DIMM report gives 2026-11-17 19:43 UTC for that time.</li><li><code>speed_MTps</code> is the speed of that line of the report, 8000 MT/s.</li><li><code>modules</code> is the module count of the boot that <code>boot_of</code> returns.</li><li><code>boot</code> is a label, for example <code>boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>The rerun: files of part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  66      # ---- the rerun: part A
  67      A = D['A'] = []
  68      for tag, s in fd.RERUN_A:
  69          folder = fd.find('k120-' + tag)
  70          A.append(dict(part='A', tag=tag, session=s, folder=folder, csv=os.path.join(folder, 'threads120.csv'),
  71                        probe=fd.read_probe(os.path.join(folder, 'probe.txt')),
  72                        procs=fd.read_k120(os.path.join(folder, 'threads120.csv'))))</pre></td><td valign="top">For each of the 3 entries of <code>fd.RERUN_A</code> (tags T72A1, T72A2, T72A3 with the session numbers 1, 2, 3):<ul><li><code>fd.find</code> returns the one folder <code>R/k120-&lt;tag&gt;-&lt;time&gt;</code>. The script stops when it does not find exactly one folder.</li><li><code>fd.read_probe</code> reads <code>probe.txt</code> of the folder.</li><li><code>fd.read_k120</code> reads <code>threads120.csv</code>. It returns the processes in file order, each with its interval rows in <code>iv</code>. An interval row is a row whose column 4 (<code>rep</code>) is a number. So the <code>best</code> row and the column header row are left out [Ref1].</li><li>No rate is computed in these lines.</li></ul></td></tr>
<tr><td colspan="2"><b>The rerun: files of parts L, C and control I</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  73      # ---- the rerun: parts L, C and the control I (runner bwx12)
  74      X = D['X'] = []
  75      for part, items in (('L', fd.RERUN_L), ('C', fd.RERUN_C), ('I', fd.RERUN_I)):
  76          for it in items:
  77              folder = fd.find('w120-' + it[0])
  78              csvs = sorted(glob.glob(os.path.join(folder, '*.csv')))
  79              assert len(csvs) == 1, csvs
  80              secs = fd.read_bwx(csvs[0])
  81              assert len(secs) == 1
  82              err = os.path.join(folder, 'stderr.txt')
  83              fd.OPENED.append(err)
  84              X.append(dict(part=part, tag=it[0], session=it[1], spec=it[2] if part == 'C' else 'like', folder=folder,
  85                            csv=csvs[0], sec=secs[0], ivs=fd.bwx_intervals(secs[0]), env=fd.read_env(folder),
  86                            launches=fd.read_launches(folder), stderr_bytes=os.path.getsize(err)))
  87</pre></td><td valign="top">For each of the 9 tags of <code>fd.RERUN_L</code>, <code>fd.RERUN_C</code> and <code>fd.RERUN_I</code> (T72L1 to T72L3, T72C1 to T72C4, T72I1, T72I2):<ul><li><code>fd.find</code> returns the one folder <code>R/w120-&lt;tag&gt;-&lt;time&gt;</code>. The folder must hold exactly one csv file, and the file must hold exactly one section. If not, an <code>assert</code> stops the script.</li><li><code>sec</code>: the rows of the csv, read by <code>fd.read_bwx</code> and stored by kind: the T rows, the I rows, the P rows and the number of C rows. Only the T rows enter the rate. <code>ivs</code>: one entry per interval from <code>fd.bwx_intervals</code>. Its rate <code>total</code> is the sum over the T rows of bytes / elapsed_s / 1e9 [Ref1].</li><li><code>session</code>: the second value of the entry. It is <code>None</code> for T72C4. For control I it is the number of the control process (1 or 2).</li><li><code>spec</code>: <code>cfwd</code> or <code>crev</code> for part C, and <code>like</code> for part L and control I.</li><li><code>env</code>, <code>launches</code>: the content of <code>env.txt</code> and <code>launches.txt</code>.</li><li><code>stderr.txt</code> is not read. Only its size in bytes is stored. Line 83 adds its path to the list <code>fd.OPENED</code> directly.</li></ul></td></tr>
<tr><td colspan="2"><b>The 12 steps of the rerun in time order</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">  88      # ---- order in time, gap since the previous 120-thread process, start state
  89      ev = []
  90      for a in A:
  91          ev.append(dict(part='A', tag=a['tag'], session=a['session'], obj=a, start=fd.folder_date(a['folder']),
  92                         first=fd.clock(a['folder'], a['procs'][0]['utc']),
  93                         last=fd.clock(a['folder'], a['procs'][-1]['utc']), end=a['probe']['utc_after'],
  94                         load1=a['procs'][0]['load1']))
  95      for x in X:
  96          la = x['launches'][0]
  97          ev.append(dict(part=x['part'], tag=x['tag'], session=x['session'], obj=x, start=fd.folder_date(x['folder']),
  98                         first=la['utc'], last=la['utc'], end=la['rc_utc'], load1=la['load1']))
  99      ev.sort(key=lambda e: e['first'])</pre></td><td valign="top">Builds the list <code>ev</code> with one entry per step: 3 sessions of part A and 9 bwx12 processes.<ul><li>Part A: <code>start</code> is the time in the folder name. <code>first</code> and <code>last</code> are the launch times of the first and the last process, from the <code>-- binary</code> header lines of <code>threads120.csv</code>. <code>end</code> is the time of the <code>load_after</code> line, which ra.sh writes into <code>probe.txt</code> after the last process [Ref10]. <code>load1</code> is the 1-minute load average of the first header line.</li><li>bwx12 process: <code>first</code> and <code>last</code> are both the time of the <code>launch</code> line of <code>launches.txt</code>. <code>end</code> is the time of the <code>rc</code> line. <code>load1</code> is the 1-minute load average of the launch line.</li><li>Line 99 sorts the steps by <code>first</code>.</li><li>All these times are whole seconds.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 100      go_start = logs['go']['states'][0]['utc']
 101      prev = None
 102      for e in ev:
 103          e['prev'] = prev
 104          e['gap_s'] = None if prev is None else (e['first'] - prev['end']).total_seconds()
 105          if prev is None:
 106              e['state'] = ('started from an idle machine, %.0f s after go.sh started (1-minute load average %.2f)'
 107                            % ((e['first'] - go_start).total_seconds(), e['load1']))
 108          elif e['part'] == 'I':
 109              e['state'] = ('started from an idle machine (1-minute load average %.2f), %.0f s after the 120-thread '
 110                            'bwx12 process %s' % (e['load1'], e['gap_s'], prev['tag']))
 111          elif prev['part'] == 'A':
 112              e['state'] = 'started %.0f s after the last 120-thread process of part A (%s)' % (e['gap_s'], prev['tag'])
 113          else:
 114              e['state'] = 'started %.0f s after the 120-thread bwx12 process %s' % (e['gap_s'], prev['tag'])
 115          prev = e
 116      D['events'] = ev
 117      evd = {e['tag']: e for e in ev}
 118</pre></td><td valign="top"><code>go_start</code> is the time of the first state line of the go.sh log. The loop goes through the steps in time order.<ul><li><code>gap_s</code> = <code>first</code> of this step minus <code>end</code> of the step before, in seconds. The first step has <code>None</code>.</li><li>With the files of the rerun the gap is 5 s for the 9 steps that follow T72A1, up to T72C4. It is 287 s for T72I1 and 265 s for T72I2. facts.json lists these values under <code>meta.launches</code>.</li><li><code>state</code> is a sentence on the start of the step. It has four forms: the first step, a step of control I, a step after a session of part A, and a step after a bwx12 process. Example: <code>started 5 s after the 120-thread bwx12 process T72L1</code>.</li><li>The words <code>idle machine</code> in the first two forms are fixed text. These lines do not test the load. The sentence shows the 1-minute load average of the launch. The driver go2.sh waits for a 1-minute load average below 1.0 before each step of control I.</li><li><code>D['events']</code> keeps the list. <code>evd</code> finds a step by its tag.</li></ul></td></tr>
<tr><td colspan="2"><b>Nested function <code>add_k120</code>: records of part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 119      def add_k120(procs, folder, order_known=True, **common):
 120          for n, p in enumerate(procs, 1):
 121              before = 'none (first process of the file)'
 122              if n &gt; 1:
 123                  before = '%s %s' % (procs[n - 2]['binary'], procs[n - 2]['kernel'])
 124              if not order_known:
 125                  # The list holds only a part of the processes of the file. A process whose header line is line 1
 126                  # of the file is the first process of the file. Before every other one, processes ran that are
 127                  # not in the list.
 128                  before = ('none (first process of the file)' if p['hdr_line'] == 1 else
 129                            'not listed (other processes of the file ran in between)')</pre></td><td valign="top">Takes a list of processes from <code>fd.read_k120</code>. <code>n</code> numbers the processes of the list from 1. <code>before</code> becomes the field <code>kernel_before</code>:<ul><li>First process of the list: the text <code>none (first process of the file)</code>.</li><li>Later process: binary and kernel of the process before it in the list, for example <code>bw_old read</code>.</li><li>With <code>order_known=False</code> the list holds only a part of the processes of the file. This is used for baseline A-3 only (line 198). A process whose header line is line 1 of the file gets <code>none (first process of the file)</code>. Every other process gets <code>not listed (other processes of the file ran in between)</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 130              for iv in p['iv']:
 131                  rec = fd.base_record(
 132                      folder=rel(folder), file=os.path.basename(p['file']), line=iv['line'], process=n,
 133                      round=p['round'], interval=iv['rep'], kernel=p['kernel'], kernel_before=before,
 134                      binary=p['binary'], GBps=iv['agg'], rate_kind=fd.KIND_A, passes=iv['passes'],
 135                      per_thread_min_GBps=iv['tmin'], per_thread_max_GBps=iv['tmax'], per_thread_avg_GBps=iv['tavg'],
 136                      threads=iv['threads'], stop='whole pass', min_ms=500, load1_at_launch=p['load1'],
 137                      launch_utc=iso(fd.clock(folder, p['utc'])), tag=p['tag'])
 138                  rec.update(common)
 139                  rec['proc_key'] = '%s|%s|%d' % (rec['folder'], rec['file'], n) + ('|' + p['tag'] if p['tag'] else '')
 140                  recs.append(rec)
 141</pre></td><td valign="top"><b>The rate of part A.</b> Each interval row of each process becomes one record. No row is left out here. No value is rounded.<ul><li><code>GBps</code> = <code>iv['agg']</code>: column 7 (<code>aggregate_GBps</code>) of the interval row, as the binary printed it. The binary prints it with 2 decimal places (a resolution of 0.01 GB/s). The script does not compute it again. The binary computed it as the sum of the bytes of all threads divided by the longest per-thread elapsed time [Ref7].</li><li><code>rate_kind</code> = <code>fd.KIND_A</code>: a text that names this formula.</li><li><code>line</code>: the line number of the row in the csv. <code>interval</code>: column 4 (<code>rep</code>). <code>threads</code>: column 2. <code>passes</code>: column 5 (<code>total_bytes</code>) divided by column 3 (<code>bytes_per_thread</code>), as a whole number. For a read kernel that is the number of buffer passes of all threads together. The three <code>per_thread_..._GBps</code> fields: columns 8, 9 and 10.</li><li><code>stop='whole pass'</code> and <code>min_ms=500</code> (each timed interval lasts at least 500 ms) are constants of this line, for the rerun and for the baselines. They are not read from the csv. The <code># bandwidth:</code> line of every such process in the csv files does hold <code>min_ms=500</code>.</li><li><code>process</code> = <code>n</code>. <code>round</code>, <code>load1_at_launch</code> and <code>launch_utc</code> come from the header line of the process. In a <code>-- step</code> header line (A-2, A-3) the round is the number at the end of the tag.</li><li><code>rec.update(common)</code> sets the fields that the caller passes, for example <code>dataset</code>. <code>proc_key</code> joins folder, file and <code>n</code> with <code>|</code>, plus the tag when the process has one.</li></ul></td></tr>
<tr><td colspan="2"><b>Nested function <code>add_bwx</code>: records of one bwx process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 142      def add_bwx(sec, folder, proc_tag, kernels=None, positions=None, **common):
 143          nseq = len(sec['hdr']['seq'].split(','))
 144          h = sec['hdr']
 145          for iv in fd.bwx_intervals(sec):
 146              if kernels and iv['kernel'] not in kernels:
 147                  continue
 148              if positions and (iv['kernel'], iv['pos']) not in positions:
 149                  continue</pre></td><td valign="top">Takes one section <code>sec</code>, that is the rows of one process. <code>nseq</code> is the number of kernels in the sequence <code>seq</code> of the csv header. <code>fd.bwx_intervals(sec)</code> gives one entry per interval. Two optional filters leave intervals out:<ul><li><code>kernels</code>: an interval is skipped when its kernel name is not in this list.</li><li><code>positions</code>: an interval is skipped when the pair (kernel, position) is not in this set.</li><li>Both filters test only the kernel name and the position. No filter tests a rate.</li><li>Without a filter every interval becomes a record. The rerun is read without a filter (line 177).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 150              rec = fd.base_record(
 151                  folder=rel(folder), file=os.path.basename(sec['file']), line=iv['line'], round=iv['round'],
 152                  pos=iv['pos'], interval=iv['round'] * nseq + iv['pos'], kernel=iv['kernel'],
 153                  kernel_before=iv['kernel_before'] or 'none (first interval of the process)', GBps=iv['total'],
 154                  rate_kind=fd.KIND_X, mesh0_GBps=iv['mesh0'], mesh1_GBps=iv['mesh1'], threads=iv['threads'],</pre></td><td valign="top"><b>The rate of a bwx interval.</b> One record per interval that passed the filters. Nothing is rounded here.<ul><li><code>GBps</code> = <code>iv['total']</code>. The T rows are grouped by round, position and kernel (columns 2, 3 and 4 of the row). One group is one interval. <code>fd.bwx_intervals</code> computes <code>bytes</code> / <code>elapsed_s</code> / 1e9 (columns 7 and 8) for each T row (one thread) and adds the values of all T rows of the interval [Ref1]. So the bytes of each thread are divided by the elapsed time of that thread. The unit is GB/s (GB = 1e9 bytes).</li><li><code>mesh0_GBps</code>, <code>mesh1_GBps</code>: the same sum over the threads on CPUs 0-63, and over the threads on CPUs 64 and above. The CPU is column 6 (<code>cpu</code>) of the T row.</li><li><code>rate_kind</code> = <code>fd.KIND_X</code>: a text that names this formula. The column <code>aggregate_GBps</code> of the I row is not used here. The runner computed that column with the formula of part A: the sum of the bytes of all threads divided by the longest per-thread elapsed time. Check <code>I-agg</code> (line 738) compares it with <code>total</code>.</li><li><code>line</code>: the line number of the I row. <code>interval</code> = round x <code>nseq</code> + position, the number of the interval in the process, counted from 0. <code>kernel_before</code>: the kernel that was timed directly before, or <code>none (first interval of the process)</code>.</li><li><code>threads</code>: the number of T rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 155                  is_64_56=iv['is_64_56'], flagged=iv['flagged'], stop=h.get('stop'), start=h.get('start'),
 156                  min_ms=int(h['min_ms']),
 157                  count=int(h.get('count', 0)), thp=h.get('thp'), tag=proc_tag)
 158              rec.update(common)
 159              rec['proc_key'] = '%s|%s|%s' % (rec['folder'], rec['file'], proc_tag)
 160              recs.append(rec)
 161</pre></td><td valign="top">The other fields of the record.<ul><li><code>is_64_56</code>: the 64+56 test. <code>flagged</code>: the number of T rows with a flag. A flagged row stays in the sum.</li><li><code>stop</code>, <code>start</code>, <code>min_ms</code>, <code>count</code>, <code>thp</code> come from the header lines of the csv. In the 9 files of the rerun they are <code>common</code>, <code>common</code>, 6000 ms, 1 and <code>madvise</code>.</li><li><code>stop</code> = <code>common</code> with <code>min_ms</code> = 6000: bwx12.c sets one deadline for all threads, 6000 ms after the common start time. Each thread reads pieces of 2 MiB, and it stops after the first piece that ends at or after the deadline. Each thread reads the clock for its own start at or after the common start time. <code>elapsed_s</code> counts from that reading. So 6000 ms is not a lower limit for the elapsed time of one thread. In the 9 files of the rerun <code>elapsed_s</code> of a T row lies between 5.999979 s and 6.000457 s.</li><li><code>start</code> = <code>common</code> is the option <code>--start common</code> of bwx12.c: every thread starts each interval at byte 0 of its own buffer. It does not set the start time of an interval. <code>thp</code> = <code>madvise</code> says only that the runner asked Linux for 2 MiB pages for each buffer.</li><li><code>count</code> = 1 means that the runner was started with the option <code>--count</code>. With this option the runner reads counters for each thread and interval, and it writes the C rows.</li><li><code>rec.update(common)</code> sets the fields that the caller passes. <code>proc_key</code> joins folder, file and <code>proc_tag</code> with <code>|</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Records of the rerun: part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 162      # ---- records of the rerun
 163      for a in A:
 164          e = evd[a['tag']]
 165          n0 = len(recs)
 166          add_k120(a['procs'], a['folder'], dataset='rerun-A', part='A', role='rerun', session=a['session'],
 167                   gap_s=e['gap_s'], start_state=e['state'], **boot72)
 168          for rec in recs[n0:]:
 169              rec['tag'] = a['tag']
 170              rec['binary_sha256'] = a['probe']['sha'][rec['binary']]
 171              if rec['process'] &gt; 1:      # ra.sh starts processes 2 to 24 directly after the previous one, with no wait
 172                  rec['gap_s'] = None</pre></td><td valign="top">For each part A folder <code>add_k120</code> appends the records of its 24 processes. All 6 kernels of both binaries become records, with 3 intervals each. That gives 72 records per session and 216 in total [Ref9].<ul><li>The old read kernel is the records with <code>binary</code> = <code>bw_old</code> and <code>kernel</code> = <code>read</code>. The new read kernel is the records with <code>binary</code> = <code>bw_new</code> and <code>kernel</code> = <code>read</code>. Each has 18 records: 3 sessions x 2 rounds x 3 intervals.</li><li>Fields passed: <code>dataset</code> = <code>rerun-A</code>, <code>part</code> = <code>A</code>, <code>role</code> = <code>rerun</code>, the session number, <code>gap_s</code> and <code>start_state</code> of the step, and the three fields of <code>boot72</code>.</li><li><code>tag</code> is set to the folder tag, for example T72A1. <code>binary_sha256</code> is the sha256 value that <code>probe.txt</code> holds for the binary of the record.</li><li><code>gap_s</code> is set to <code>None</code> for processes 2 to 24. ra.sh starts them directly after the process before. <code>start_state</code> stays on all 72 records of a session. It describes the start of process 1.</li></ul></td></tr>
<tr><td colspan="2"><b>Records of the rerun: parts L, C and control I</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 173      role_of = dict(L='rerun', C='rerun', I='control, added after the first numbers of parts A, L and C were seen')
 174      for x in X:
 175          e = evd[x['tag']]
 176          la = x['launches'][0]
 177          add_bwx(x['sec'], x['folder'], x['tag'], dataset='control-I' if x['part'] == 'I' else 'rerun-' + x['part'],
 178                  part=x['part'], role=role_of[x['part']], session=x['session'], binary='bwx12',
 179                  binary_sha256=x['env']['sha'], load1_at_launch=la['load1'], launch_utc=iso(la['utc']),
 180                  gap_s=e['gap_s'], start_state=e['state'], **boot72)
 181</pre></td><td valign="top">For each of the 9 bwx12 folders <code>add_bwx</code> is called without a filter. So every interval of every kernel becomes a record: 10 per process of part L and of control I, 6 per process of part C. That gives 30 records for part L, 24 for part C and 20 for control I [Ref9].<ul><li>Part C holds both kernels: <code>oldread</code> is the old read kernel and <code>read</code> is the new read kernel, 8 records each. The sequence of part L and of control I holds <code>oldread</code>, <code>asmread</code> and three test loops. It holds no kernel <code>read</code>.</li><li><code>dataset</code> = <code>rerun-L</code>, <code>rerun-C</code> or <code>control-I</code>. <code>role</code> = <code>rerun</code> for parts L and C. For control I the role says that the control was added after the first numbers were seen.</li><li><code>binary</code> = <code>bwx12</code> is a constant of this line. <code>binary_sha256</code> comes from the <code>binary</code> line of <code>env.txt</code>. Check <code>sha-bwx12</code> (line 768) compares it with the value in go.sh.</li><li><code>load1_at_launch</code> and <code>launch_utc</code> come from the <code>launch</code> line. <code>gap_s</code> and <code>start_state</code> come from the step.</li><li><code>proc_tag</code> is the folder tag, for example T72L1.</li></ul></td></tr>
<tr><td colspan="2"><b>The 8000 MT/s baselines of part A: files</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 182      # ---- 8000 MT/s baselines of part A (fixed list of baselines-and-rules.txt)
 183      D['base'] = base = {}
 184      kfolder = os.path.join(R, 'kernels-20261113T181222Z')
 185      pfolder = os.path.join(R, 'partA-20261113T205055Z')
 186      base['A-1'] = dict(folder=kfolder, file='threads120.csv', procs=fd.read_k120(os.path.join(kfolder, 'threads120.csv')))
 187      base['A-2'] = dict(folder=pfolder, file='A1.csv', procs=fd.read_k120(os.path.join(pfolder, 'A1.csv')))
 188      base['A-3'] = dict(folder=pfolder, file='A3.csv', procs=fd.read_k120(
 189          os.path.join(pfolder, 'A3.csv'), only_tags=lambda t: re.fullmatch(r'onebuf-ms500-[123]', t) is not None))</pre></td><td valign="top">Reads the three baselines of part A with <code>fd.read_k120</code>. The comment says that the rules file fixes this list.<ul><li>A-1: <code>threads120.csv</code> of the folder <code>R/kernels-20261113T181222Z</code> (24 processes).</li><li>A-2: <code>A1.csv</code> of the folder <code>R/partA-20261113T205055Z</code> (12 processes).</li><li>A-3: <code>A3.csv</code> of the same folder. The test <code>only_tags</code> keeps only the processes with the tag <code>onebuf-ms500-1</code>, <code>onebuf-ms500-2</code> or <code>onebuf-ms500-3</code>. The file holds 12 processes. So 9 processes are left out with all their rows.</li><li><code>A1.csv</code> and <code>A3.csv</code> also hold rows that start with <code>thread,</code> (the per-thread rows of the option <code>--per-thread</code>). They are not interval rows, and they give no record. <code>fd.read_k120</code> keeps their rates in <code>thr</code> of the process [Ref1].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 190      # The copy kernels count read plus written bytes. The header line of every copy and asmcopy process must say so,
 191      # because facts.json gives the meaning of the field "passes" from it.
 192      cp = [p for procs in [a['procs'] for a in A] + [b['procs'] for b in base.values()] for p in procs
 193            if p['kernel'] in ('copy', 'asmcopy')]
 194      assert cp and all(p.get('copy_note') for p in cp), 'a copy process without the header note on read+write bytes'
 195      D['probe13'] = open_probe13(kfolder)
 196      D['env_partA'] = fd._open(os.path.join(pfolder, 'env.txt')).read()
 197      sha13 = D['probe13']['sha']</pre></td><td valign="top"><code>cp</code> is the list of all processes of the kernels <code>copy</code> and <code>asmcopy</code>, in the 3 files of the rerun and in the 3 baselines. The <code>assert</code> stops the script when the list is empty, or when the header line that the binary printed for one of them lacks the text <code>copy counts read+write bytes</code>. The reason: facts.json explains the field <code>passes</code> with this text.<ul><li><code>open_probe13</code> (line 568) reads the other records of the 2026-11-13 run. <code>sha13</code> holds the sha256 values of its <code>probe.txt</code>, by file name.</li><li><code>D['env_partA']</code> is the text of <code>env.txt</code> of the A-2 folder. Check <code>sha-bw</code> (line 756) uses it.</li></ul></td></tr>
<tr><td colspan="2"><b>The 8000 MT/s baselines of part A: records</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 198      for name, order_known in (('A-1', True), ('A-2', True), ('A-3', False)):
 199          b = base[name]
 200          n0 = len(recs)
 201          add_k120(b['procs'], b['folder'], order_known=order_known, dataset=name, part='A', role='baseline',
 202                   **state_of(b['folder']))
 203          for rec in recs[n0:]:
 204              rec['binary_sha256'] = sha13[rec['binary']]
 205</pre></td><td valign="top"><code>add_k120</code> appends the records of the three baselines. Every interval row of the kept processes becomes a record: 72 for A-1, 36 for A-2 and 9 for A-3 [Ref9].<ul><li><code>dataset</code> = <code>A-1</code>, <code>A-2</code> or <code>A-3</code>. <code>part</code> = <code>A</code>. <code>role</code> = <code>baseline</code>.</li><li><code>state_of</code> gives <code>speed_MTps</code> = 8000, the module count and the boot label.</li><li><code>order_known</code> is false for A-3 only (see line 124).</li><li><code>binary_sha256</code> is the value of <code>sha13</code> for the binary of the record: the sha256 value in <code>probe.txt</code> of the folder <code>R/kernels-20261113T181222Z</code> (the A-1 folder). The records of A-2 and A-3 get this value too. Their own folder is not read for this field. Check <code>sha-bw</code> (line 756) tests that <code>env.txt</code> of their folder holds the same two values.</li><li><code>session</code>, <code>gap_s</code> and <code>start_state</code> stay <code>None</code> in these records.</li></ul></td></tr>
<tr><td colspan="2"><b>Earlier data sets of bwx12 and bwx11</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 206      # ---- bwx folders written by rx.sh or r0.sh (one csv per process)
 207      rx_sets = [
 208          # dataset, role, folder prefix, files, positions
 209          ('L-1', 'baseline (identical argument line)', 'w120-R8', ['a6456.csv'], None),
 210          ('L-2', 'supporting (4 s, other counter events)', 'w120-R1', ['p1nop.csv', 'p2add.csv'], POS01),
 211          ('L-3', 'supporting (4 s, other counter events)', 'w120-R5', ['thp.csv'], POS01),
 212          ('L-4', 'supporting (4 s, other counter events)', 'w120-R6', ['st1.csv', 'st2.csv', 'st3.csv'], POS01),
 213          ('R0', 'other binary (bwx11)', 'w120-R0', ['p1.csv', 'p2.csv'], POS01),
 214          ('R0b', 'other binary (bwx11), 4 s', 'w120-R0b', ['cA.csv', 'cB.csv', 'cC.csv'], POS01),
 215          ('X2d12', 'not a baseline (firmware test setting)', 'w120-X2d12', ['a6456.csv'], None),
 216          ('X1d10', '10 modules', 'w120-X1d10', ['a6456.csv'], POS01),
 217          ('X1d10b', '10 modules', 'w120-X1d10b', ['a6456.csv'], POS01),
 218          ('BASEd10', '10 modules', 'w120-BASEd10', ['a6456.csv'], POS01),
 219          ('F72d12', '7200 MT/s sample of the same boot, earlier visit, not part of the rerun', 'w120-w120-F72d12',
 220           ['a6456.csv'], None),
 221      ]</pre></td><td valign="top">The table <code>rx_sets</code> has one entry per data set: name, role, start of the folder name, csv files, position filter.<ul><li>8 data sets have the filter <code>POS01</code>: L-2, L-3, L-4, R0, R0b, X1d10, X1d10b and BASEd10. Of them only <code>oldread</code> at position 0 and <code>asmread</code> at position 1 become records. Every other interval is left out.</li><li>Example: the sequence of <code>p1.csv</code> of R0 holds <code>asmread</code> again at position 10 and <code>oldread</code> again at position 11. The intervals at these two positions are left out in both rounds of the process.</li><li>3 data sets have no filter (<code>None</code>): L-1, X2d12 and F72d12. Every interval of their file <code>a6456.csv</code> becomes a record.</li><li>Only the csv files named in the table give records. Example: the folder of L-1 holds 5 csv files, and only <code>a6456.csv</code> gives records.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 222      D['rx'] = {}
 223      for name, role, prefix, files, positions in rx_sets:
 224          folder = fd.find(prefix)
 225          env = fd.read_env(folder)
 226          env['has_binary_line'] = env['sha'] is not None
 227          if env['sha'] is None:      # r0.sh wrote no binary line to env.txt; the script itself holds the checksum
 228              txt = fd._open(os.path.join(fd.W15, 'r0.sh')).read()
 229              env['sha'] = re.search(r'echo "([0-9a-f]{64})  \$BW"', txt)[1]
 230              env['sha_line'] = next(i for i, l in enumerate(txt.splitlines(), 1) if env['sha'] in l)
 231              env['binary'] = re.search(r'^BW=(\S+)', txt, re.M)[1]
 232          la = {l['tag']: l for l in fd.read_launches(folder)}
 233          err = os.path.join(folder, 'stderr.txt')
 234          fd.OPENED.append(err)</pre></td><td valign="top">For each data set:<ul><li><code>fd.find</code> returns the one folder. <code>fd.read_env</code> reads its <code>env.txt</code>.</li><li><code>env['sha']</code> is the sha256 value of the runner binary, from the <code>binary</code> line of <code>env.txt</code>. <code>has_binary_line</code> records whether that line exists.</li><li>The folder of R0 has no such line. r0.sh wrote none. Then the value is taken from the text of r0.sh: the 64 hexadecimal digits of the line <code>echo "&lt;digits&gt;  $BW"</code>. <code>sha_line</code> is the number of that line. <code>binary</code> is the path after <code>BW=</code>.</li><li><code>la</code>: the launch lines of <code>launches.txt</code>, by tag.</li><li>The path of <code>stderr.txt</code> is added to <code>fd.OPENED</code>. Only the size of the file is used (line 248).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 235          if name == 'F72d12':
 236              # The folder holds no boot id. Its process lies between two readings of the boot id of the rerun:
 237              # try6.txt before it and the first state line of go.sh after it. The text of section 4.1 states this.
 238              st = dict(boot72)
 239              assert fd.folder_date(folder) &gt; try6['first_log_utc']
 240              f72 = la[files[0][:-4]]
 241              go0 = logs['go']['states'][0]
 242              assert try6['utc'] &lt; f72['utc'] &lt; f72['rc_utc'] &lt; go0['utc'] and go0['boot'] == try6['boot'], 'F72d12'
 243              assert try6['boots_first'] &lt;= f72['utc'] and f72['rc_utc'] &lt;= try6['boots_last'], 'F72d12, boots.txt'
 244              assert try6['first_log_utc'] &lt;= f72['utc'] and f72['rc_utc'] &lt;= try6['last_log_utc'], 'F72d12, gaps.txt'
 245          else:
 246              st = state_of(folder)</pre></td><td valign="top">Sets <code>st</code>: the fields speed, modules and boot of the data set.<ul><li>Every data set except F72d12: <code>state_of(folder)</code> takes the values from the DIMM report.</li><li>F72d12: <code>st</code> is a copy of <code>boot72</code>: 7200 MT/s, 12 modules, the boot id of the rerun. The folder holds no boot id. So four <code>assert</code> statements test the times of the process.</li><li>The time in the folder name must lie after the first Linux kernel log line of this boot.</li><li>The process must start after the time of <code>try6.txt</code> and end before the first state line of go.sh. That state line must hold the boot id of <code>try6.txt</code>.</li><li>The process must lie inside the time range of this boot in <code>boots.txt</code> and in <code>gaps.txt</code>. These two files of the folder <code>R/dimm7200-20261117</code> hold rows with a boot number, a first time and a last time. Row 0 of <code>boots.txt</code> holds the boot id of the rerun. <code>gaps.txt</code> holds no boot id, and the script takes its row 0 as the same boot.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 247          D['rx'][name] = dict(folder=folder, env=env, launches=la, files=files, role=role, state=st, secs={},
 248                               stderr_bytes=os.path.getsize(err))
 249          for fn in files:
 250              sec = fd.read_bwx(os.path.join(folder, fn))[0]
 251              tag = fn[:-4]
 252              D['rx'][name]['secs'][tag] = sec
 253              add_bwx(sec, folder, tag, positions=positions, dataset=name, part='L', role=role,
 254                      binary=fd.SHA_NAMES[env['sha'][:8]], binary_sha256=env['sha'], load1_at_launch=la[tag]['load1'],
 255                      launch_utc=iso(la[tag]['utc']), **st)
 256</pre></td><td valign="top"><code>D['rx'][name]</code> keeps the folder, <code>env</code>, the launch lines, the role, <code>st</code> and the size of <code>stderr.txt</code>. For each csv file of the data set:<ul><li><code>sec</code> is the first section of the file. The csv files named in the table hold no <code>-- step</code> line. So each is one section. <code>tag</code> is the file name without <code>.csv</code>, for example <code>a6456</code>.</li><li><code>add_bwx</code> appends the records with the position filter of the data set. <code>dataset</code> is the name of the data set, and <code>part</code> is <code>L</code>.</li><li><code>binary</code> is the short name that <code>fd.SHA_NAMES</code> gives for the first 8 digits of the sha256 value: <code>bwx12</code> or <code>bwx11</code>.</li><li><code>load1_at_launch</code> and <code>launch_utc</code> come from the launch line with the same tag.</li><li>The 11 data sets give 74 records [Ref9].</li></ul></td></tr>
<tr><td colspan="2"><b>Data sets of the first runner bwx</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 257      # ---- folders of the first runner bwx (2026-11-13/14): one csv with one section per process
 258      step_sets = [
 259          ('B7a', 'B7-20261113T232859Z', 'B7.csv', 'common-6000-'),
 260          ('B7b', 'B7-20261114T024352Z', 'B7.csv', 'common-6000-'),
 261          ('C3a', 'C3-20261114T022708Z', 'C3.csv', 'common-6000-'),
 262          ('C3b', 'C3-20261114T054116Z', 'C3.csv', 'common-6000-'),
 263          ('B5a', 'B5-20261114T011723Z', 'B5.csv', 'b5-fwd-'),
 264          ('B5b', 'B5-20261114T043213Z', 'B5.csv', 'b5-fwd-'),
 265          ('B5a-rev', 'B5-20261114T011723Z', 'B5.csv', 'b5-rev-'),
 266          ('B5b-rev', 'B5-20261114T043213Z', 'B5.csv', 'b5-rev-'),
 267      ]</pre></td><td valign="top">The table <code>step_sets</code> has one entry per data set: name, folder under <code>R</code>, csv file, and the start of the process tags that belong to the data set. One csv file holds several processes. Two data sets can share one file. Example: B5a and B5a-rev both read <code>B5.csv</code> of the folder <code>B5-20261114T011723Z</code>, with the tag prefixes <code>b5-fwd-</code> and <code>b5-rev-</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 268      D['step'] = {}
 269      for name, fname, csv, prefix in step_sets:
 270          folder = os.path.join(R, fname)
 271          envtxt = fd._open(os.path.join(folder, 'env.txt')).read()
 272          sha = re.search(r'^([0-9a-f]{64})  bwx$', envtxt, re.M)[1]
 273          allsecs = fd.read_bwx(os.path.join(folder, csv))
 274          for i, s in enumerate(allsecs):
 275              s['prev_step'] = allsecs[i - 1]['step'] if i else None
 276          secs = [s for s in allsecs if s['step']['tag'].startswith(prefix)]
 277          D['step'][name] = dict(folder=folder, file=csv, sha=sha, secs=secs, prefix=prefix)</pre></td><td valign="top">For each data set:<ul><li><code>sha</code> is the sha256 value of the binary <code>bwx</code>, from the line of <code>env.txt</code> that ends with two spaces and <code>bwx</code>.</li><li><code>fd.read_bwx</code> returns all sections of the csv, one per <code>-- step</code> header line. <code>prev_step</code> of a section is the header of the section before it in the file. It is <code>None</code> for the first section.</li><li><code>secs</code> keeps only the sections whose tag starts with the prefix of the data set. The other sections of the file give no record in this data set. Example: <code>B7.csv</code> of B7a holds 48 sections, and the prefix <code>common-6000-</code> keeps 8 of them. 4 of the 8 have a tag <code>common-6000-offset-...</code>. Their processes ran with <code>--start offset</code>, and their records have <code>start</code> = <code>offset</code>.</li><li><code>D['step'][name]</code> keeps the folder, the file name, <code>sha</code>, <code>secs</code> and the prefix.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 278          for sec in secs:
 279              st = sec['step']
 280              add_bwx(sec, folder, st['tag'], kernels=READ3, dataset=name, part='C',
 281                      role='other binary (bwx)' + (', reverse kernel order, not in the list of rule V4'
 282                                                   if name.endswith('-rev') else ''),
 283                      binary=fd.SHA_NAMES[sha[:8]], binary_sha256=sha, load1_at_launch=st['load1'],
 284                      launch_utc=iso(fd.clock(folder, st['utc'])), **state_of(folder))</pre></td><td valign="top">For each kept section <code>add_bwx</code> is called with <code>kernels=READ3</code>. So only the intervals of <code>oldread</code>, <code>read</code> and <code>asmread</code> become records. The other kernels of the sequence are left out, for example <code>asmread2</code> and <code>read_nop4</code>.<ul><li>No position filter is set. In the sequence of <code>B7.csv</code> and <code>C3.csv</code> each of the three kernels stands at two positions: <code>oldread</code> at 0 and 7, <code>read</code> at 1 and 6, <code>asmread</code> at 2 and 5. The intervals at both positions become records in both rounds of the process.</li><li><code>proc_tag</code> is the tag of the <code>-- step</code> line. <code>part</code> = <code>C</code>.</li><li><code>role</code> = <code>other binary (bwx)</code>. The two data sets whose name ends with <code>-rev</code> get the added text <code>, reverse kernel order, not in the list of rule V4</code>.</li><li><code>binary</code> is <code>bwx</code>, the name that <code>fd.SHA_NAMES</code> gives for <code>sha</code>. <code>load1_at_launch</code> and <code>launch_utc</code> come from the <code>-- step</code> line. <code>state_of</code> gives speed, modules and boot.</li><li>The 8 data sets give 312 records [Ref9].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 285      D['hw'] = hw_records(D)
 286      D['hw_cmp'] = hw_compare(D['hw'])
 287      D['fw'] = open_fw()
 288      D['a2pre'] = open_a2pre()
 289      D['mod'] = open_mod()
 290      return D
 291
 292</pre></td><td valign="top">Adds five more entries to <code>D</code>. They hold no rate of the rerun, and they change no record.<ul><li><code>D['hw']</code>, <code>D['hw_cmp']</code>: the hardware error records inside the process windows of 6 earlier data sets, and a comparison (<code>hw_records</code>, <code>hw_compare</code>).</li><li><code>D['fw']</code>: the saved firmware settings (<code>open_fw</code>).</li><li><code>D['a2pre']</code>: the run before baseline A-2 (<code>open_a2pre</code>).</li><li><code>D['mod']</code>: what a boot with 10 modules shows in the lines that the facts sheet uses as proof of 12 modules (<code>open_mod</code>, line 536).</li></ul>Then <code>collect</code> returns <code>D</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 293  HW_ROWS = ('L-1', 'L-2', 'L-3', 'L-4', 'R0', 'R0b')     # the bwx12 and bwx11 rows of the 2026-11-09 boot
 294
 295</pre></td><td valign="top"><code>HW_ROWS</code>: the 6 data sets whose processes <code>hw_records</code> tests: L-1 to L-4, R0 and R0b. All are 8000 MT/s data sets of bwx12 and bwx11 from the boot that started on 2026-11-09.</td></tr>
<tr><td colspan="2"><b>Function <code>hw_records</code>: hardware error records inside process windows</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 296  def hw_records(D):
 297      """Hardware error records of the saved journal of the 2026-11-09 boot inside the process windows of the
 298      rows HW_ROWS. The window of a process runs from its launch line to its rc line in launches.txt.
 299      Both the journal and launches.txt give whole seconds. So a record with the journal time J and a launch
 300      line with the time L lies between J - L - 1 and J - L + 1 seconds after the process start.
 301      A record is 'inside' an interval when this whole span lies between the start and the end of the interval,
 302      'possible' when the span and the interval share a part, and 'outside' otherwise.
 303      The fields 'kind' and 'interval' of a record test only the intervals that the sheet uses: oldread at position 0
 304      and asmread at position 1. The field 'every' holds the same test against every interval of the process."""</pre></td><td valign="top">The comment gives the rule. The tests of this function use no rate.<ul><li>The journal and <code>launches.txt</code> both give whole seconds. <code>off</code> is the journal time of a record minus the launch time. So the record lies between <code>off</code> - 1 and <code>off</code> + 1 seconds after the process start.</li><li><code>inside</code>: this whole span lies between the start and the end of an interval.</li><li><code>possible</code>: the span and the interval share a part.</li><li><code>outside</code>: neither of the two.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 305      errs = fd.read_error_records(D['probe13']['h5'])
 306      boots = {D['rx'][n]['state']['boot'] for n in HW_ROWS}
 307      assert len(boots) == 1, boots
 308      out = []
 309      for name in HW_ROWS:
 310          v = D['rx'][name]
 311          for tag, sec in v['secs'].items():
 312              la = v['launches'][tag]
 313              assert D['probe13']['boot_start'] &lt; la['utc'] &lt; la['rc_utc']
 314              allv = fd.bwx_intervals(sec)
 315              used = [iv for iv in allv if (iv['kernel'], iv['pos']) in POS01]
 316              hits = []</pre></td><td valign="top"><code>errs</code>: all hardware error records of the saved journal <code>h-5.txt</code>. The first <code>assert</code> requires one boot label for all 6 data sets. For each csv file of each data set:<ul><li><code>la</code> is its launch line. The second <code>assert</code> requires that the launch lies after the start of that boot and before the <code>rc</code> time.</li><li><code>allv</code>: all intervals of the process, from <code>fd.bwx_intervals</code>. That call computes the rate <code>total</code> of every interval again. This includes the intervals that the filter <code>POS01</code> left out of the records. <code>hw_compare</code> (line 340) uses these rates.</li><li><code>used</code>: the intervals that pass <code>POS01</code>, that is <code>oldread</code> at position 0 and <code>asmread</code> at position 1.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 317              for e in errs:
 318                  if not la['utc'] &lt;= e['utc'] &lt;= la['rc_utc']:
 319                      continue
 320                  off = (e['utc'] - la['utc']).total_seconds()
 321                  kind, where = 'outside', None
 322                  for iv in used:
 323                      if iv['t_start'] &lt;= off - 1 and off + 1 &lt;= iv['t_end']:
 324                          kind, where = 'inside', iv
 325                      elif off - 1 &lt; iv['t_end'] and iv['t_start'] &lt; off + 1 and kind != 'inside':
 326                          kind, where = 'possible', iv</pre></td><td valign="top">For each record whose time lies in the process window (launch time to <code>rc</code> time, both ends included): <code>off</code> is the journal time minus the launch time, in seconds.<ul><li>The loop tests the span from <code>off</code> - 1 to <code>off</code> + 1 against each interval of <code>used</code>.</li><li>The start and the end of an interval are the earliest thread start and the latest thread end, in seconds since the process start.</li><li><code>kind</code> becomes <code>inside</code> or <code>possible</code>, and <code>where</code> is the interval. A result <code>inside</code> is not replaced by a later <code>possible</code>.</li><li><code>kind</code> stays <code>outside</code> when the span touches no interval of <code>used</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 327                  # the same test against every interval of the process (all kernels and positions), for hw_compare()
 328                  every = []
 329                  for iv in allv:
 330                      if iv['t_start'] &lt;= off - 1 and off + 1 &lt;= iv['t_end']:
 331                          every.append(('inside', iv))
 332                      elif off - 1 &lt; iv['t_end'] and iv['t_start'] &lt; off + 1:
 333                          every.append(('possible', iv))
 334                  hits.append(dict(e, offset_s=off, kind=kind, interval=where, every=every))
 335              out.append(dict(dataset=name, tag=tag, folder=v['folder'], file=sec['file'], launch=la, used=used,
 336                              all=allv, records=hits))
 337      return out
 338
 339</pre></td><td valign="top"><code>every</code>: the same test against all intervals of the process, with every result <code>inside</code> or <code>possible</code> kept. <code>hw_compare</code> uses this list. Each record is stored with <code>offset_s</code>, <code>kind</code>, <code>interval</code> and <code>every</code>. The function returns one entry per process: data set, tag, folder, file, launch line, <code>used</code>, <code>all</code> and <code>records</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>hw_compare</code>: an interval with a record against the other round</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 340  def hw_compare(hw):
 341      """Every interval (all kernels and positions) of the processes of hw_records() that has a record, against the
 342      interval of the same kernel at the same position in the other round of the same process.
 343      rows:   the records lie inside the interval, or the interval is the only one that their span of +-1 s touches.
 344      border: records whose span touches two intervals. The 1 s resolution cannot assign them to one of them.
 345      clean:  the positions at which neither round has a record inside it or at its border, with round 1 minus round 0.
 346      This is a view added after the numbers were seen. The sheet draws no wording by rule V1 point 2 from it."""</pre></td><td valign="top">The comment names the three result lists.<ul><li><code>rows</code>: intervals with a record inside, and intervals that are the only one that the span of a record touches.</li><li><code>border</code>: records whose span touches two intervals. The resolution of 1 s cannot assign them to one interval.</li><li><code>clean</code>: positions at which no round has a record.</li><li>The comment also says that this view was added after the numbers were seen, and that the facts sheet draws no wording by rule V1 point 2 from it.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 347      rows, border, clean = [], [], []
 348      for h in hw:
 349          if not h['records']:
 350              continue
 351          ivs = h['all']
 352          assert {iv['round'] for iv in ivs} == {0, 1}, (h['dataset'], h['tag'])
 353          mark = {}                                   # id(interval) -&gt; every record that touches it
 354          for e in h['records']:
 355              for kind, iv in e['every']:
 356                  mark.setdefault(id(iv), []).append(e)</pre></td><td valign="top">Processes without a record are skipped.<ul><li><code>ivs</code> is the list of all intervals of the process. The <code>assert</code> requires that the rounds of the process are exactly 0 and 1.</li><li><code>mark</code> holds, for each interval, the records whose span touches it (<code>inside</code> or <code>possible</code>).</li><li>The key <code>id(iv)</code> is the identity number that Python gives to the interval object.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 357
 358          def other(iv):
 359              o = [x for x in ivs if (x['pos'], x['kernel']) == (iv['pos'], iv['kernel']) and x['round'] != iv['round']]
 360              assert len(o) == 1, (h['dataset'], h['tag'], iv['pos'])
 361              return o[0]
 362
 363          def cmp_(iv):
 364              o = other(iv)
 365              return dict(iv=iv, other=o, other_has_records=id(o) in mark, diff=iv['total'] - o['total'])</pre></td><td valign="top">Two nested helpers.<ul><li><code>other(iv)</code> returns the interval with the same position and kernel in the other round. The <code>assert</code> requires exactly one such interval.</li><li><code>cmp_(iv)</code> returns the interval, its partner <code>other</code>, the flag <code>other_has_records</code>, and <code>diff</code>.</li><li><code>diff</code> = <code>total</code> of the interval minus <code>total</code> of the partner, in GB/s. <code>total</code> is the rate of an interval: the sum over its T rows.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 366          owner = {}                                  # id(interval) -&gt; (interval, where, records assigned to it)
 367          by_t = {}
 368          for e in h['records']:
 369              kinds = [k for k, _ in e['every']]
 370              assert 1 &lt;= len(kinds) &lt;= 2, (h['dataset'], h['tag'], e['line'], kinds)
 371              if len(kinds) == 1:
 372                  iv = e['every'][0][1]
 373                  if kinds[0] == 'inside':
 374                      where = 'inside'
 375                  else:
 376                      assert e['offset_s'] - 1 &lt; iv['t_start'] and iv is ivs[0], (h['dataset'], h['tag'], e['line'])
 377                      where = 'before or inside'
 378                  slot = owner.setdefault(id(iv), (iv, where, []))
 379                  assert slot[1] == where
 380                  slot[2].append(e)
 381              else:
 382                  assert kinds == ['possible', 'possible'], (h['dataset'], h['tag'], e['line'], kinds)
 383                  by_t.setdefault(e['utc'], []).append(e)</pre></td><td valign="top">Assigns each record of the process to one interval or to a border between two intervals. <code>kinds</code> holds one entry (<code>inside</code> or <code>possible</code>) for each interval that the span of the record touches. It must hold 1 or 2 entries.<ul><li>One entry <code>inside</code>: the record goes to that interval with <code>where</code> = <code>inside</code>.</li><li>One entry <code>possible</code>: the <code>assert</code> requires that the span starts before the start of the interval, and that the interval is the first one of the process. <code>where</code> = <code>before or inside</code>.</li><li>Two entries: both must be <code>possible</code>. The record lies at the border of two intervals. It goes to <code>by_t</code> under its journal time.</li><li><code>owner</code> holds, for each interval of the first two cases, the interval, <code>where</code> and its records. All records of one interval must have the same <code>where</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 384          for iv, where, es in owner.values():
 385              rows.append(dict(cmp_(iv), dataset=h['dataset'], tag=h['tag'], file=h['file'], where=where, records=es,
 386                               used=(iv['kernel'], iv['pos']) in POS01))
 387          for t, es in sorted(by_t.items()):
 388              pair = [iv for _, iv in es[0]['every']]
 389              assert all([iv for _, iv in e['every']] == pair for e in es)
 390              border.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], records=es,
 391                                 intervals=[cmp_(iv) for iv in pair]))</pre></td><td valign="top">Builds two of the result lists.<ul><li><code>rows</code>: one entry per interval of <code>owner</code>. It holds the result of <code>cmp_</code>, the data set, the tag, the file, <code>where</code> and the records. <code>used</code> is true when the interval passes <code>POS01</code>.</li><li><code>border</code>: one entry per journal time of <code>by_t</code>. The <code>assert</code> requires that all records of that time touch the same two intervals. The entry holds the result of <code>cmp_</code> for both intervals.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 392          for pos in sorted({iv['pos'] for iv in ivs}):
 393              a, b = sorted((iv for iv in ivs if iv['pos'] == pos), key=lambda iv: iv['round'])
 394              if id(a) not in mark and id(b) not in mark:
 395                  clean.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], pos=pos, kernel=a['kernel'],
 396                                    r0=a, r1=b, diff=b['total'] - a['total']))
 397      return dict(rows=rows, border=border, clean=clean)
 398
 399</pre></td><td valign="top"><code>clean</code>: for each position, <code>a</code> is the interval of round 0 and <code>b</code> is the interval of round 1. When neither is in <code>mark</code>, one entry is added with <code>diff</code> = <code>total</code> of round 1 minus <code>total</code> of round 0, in GB/s. The function returns the three lists.</td></tr>
<tr><td colspan="2"><b>Function <code>hw_compare_json</code>: the comparison in the form of facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 400  def hw_compare_json(hc):
 401      """hw_compare() as a record of facts.json (meta.hardware_error_records.all_intervals)."""
 402      iv_ = lambda x: dict(kernel=x['kernel'], round=x['round'], pos=x['pos'], line=x['line'],
 403                           t_start_s=round(x['t_start'], 3), t_end_s=round(x['t_end'], 3), GBps=r3(x['total']))
 404      cmp_ = lambda x: dict(iv_(x['iv']), other_round=dict(iv_(x['other']), has_records=x['other_has_records']),
 405                            minus_other_round_GBps=r3(x['diff']))
 406      recs_ = lambda es: dict(journal_lines=[e['line'] for e in es], offset_s=sorted({e['offset_s'] for e in es}))
 407      cmax = max(hc['clean'], key=lambda x: abs(x['diff']))</pre></td><td valign="top">Three helpers and one value:<ul><li><code>iv_</code>: kernel, round, position and line of an interval. <code>t_start_s</code> and <code>t_end_s</code> are rounded to 0.001 s. <code>GBps</code> is <code>total</code> rounded to 0.001 GB/s by <code>r3</code>.</li><li><code>cmp_</code>: the fields of <code>iv_</code> for the interval, the same for the partner under <code>other_round</code>, and <code>minus_other_round_GBps</code>. That value is <code>diff</code>, rounded to 0.001 GB/s. <code>diff</code> was formed from the unrounded rates.</li><li><code>recs_</code>: the journal line numbers and the distinct offsets of a list of records.</li><li><code>cmax</code>: the entry of <code>clean</code> with the largest absolute difference.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 408      return dict(
 409          note='view added after the numbers were seen, not part of the rules fixed before the run. Every interval '
 410               '(all kernels and positions) of the processes above that has a record, by the same rule as "kind": the '
 411               'span offset_s - 1 to offset_s + 1 against the interval. other_round = the interval of the same kernel at '
 412               'the same position in the other round of the same process. minus_other_round_GBps = rate of the interval '
 413               'with records minus the rate of other_round. The comparison is not a test: the hypothesis that a '
 414               'corrected record lowers the rate of its interval is not tested',
 415          with_records=[dict(dataset=r['dataset'], tag=r['tag'], file=rel(r['file']), where=r['where'],
 416                             used_by_the_sheet=r['used'], **recs_(r['records']), **cmp_(r)) for r in hc['rows']],
 417          at_the_border_of_two_intervals=[dict(dataset=b['dataset'], tag=b['tag'], file=rel(b['file']),
 418                                               intervals=[cmp_(x) for x in b['intervals']], **recs_(b['records']))
 419                                          for b in hc['border']],
 420          positions_without_records=dict(
 421              note='positions of the processes with records at which neither round has a record inside it or at its '
 422                   'border. Difference = round 1 minus round 0',
 423              n_positions=len(hc['clean']),
 424              n_positions_above_1_GBps=sum(abs(x['diff']) &gt; 1.0 for x in hc['clean']),
 425              largest=dict(dataset=cmax['dataset'], tag=cmax['tag'], kernel=cmax['kernel'], pos=cmax['pos'],
 426                           round_1_minus_round_0_GBps=r3(cmax['diff']))))
 427
 428</pre></td><td valign="top">Returns the dictionary that facts.json stores under <code>meta.hardware_error_records.all_intervals</code>.<ul><li><code>note</code>: a fixed text. It says that the view was added after the numbers were seen and that the comparison is not a test.</li><li><code>with_records</code>: one entry per element of <code>rows</code>.</li><li><code>at_the_border_of_two_intervals</code>: one entry per element of <code>border</code>.</li><li><code>positions_without_records</code>: the number of entries of <code>clean</code>, the number of them with an absolute difference above 1.0 GB/s, and the entry with the largest absolute difference.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>open_fw</code>: saved firmware settings</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 429  def open_fw():
 430      """Records of the firmware settings tool (uefisettings) under R: the saved settings lists, the replies of
 431      every 'set' call, and the last reading of the memory speed setting."""
 432      mtime = lambda p: fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(p)))
 433      out = dict(lists={}, sets={})
 434      # every file with one of the two names under R, so that the text can say that no other one exists
 435      found = dict(set=[], q=[])
 436      for root, dirs, names in os.walk(R):
 437          dirs.sort()
 438          for n in sorted(names):
 439              if n == 'set.txt':
 440                  found['set'].append(os.path.join(root, n))
 441              elif n == 'questions.json':
 442                  found['q'].append(os.path.join(root, n))</pre></td><td valign="top">Reads the records of the firmware settings tool under <code>R</code>. This function reads no rate. <code>mtime</code> gives the modification time of a file in UTC, in whole seconds. The loop goes through the whole folder tree of <code>R</code>, and it collects the path of every file with the name <code>set.txt</code> or <code>questions.json</code>.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 443      lists = dict(base=os.path.join(R, 'uefisettings-20261117', 'questions.json'),
 444                   x1=os.path.join(R, 'fwtest-20261117', 'x1', 'post', 'questions.json'),
 445                   revert=os.path.join(R, 'fwtest-20261117', 'revert', 'questions.json'))
 446      sets = dict(x1=os.path.join(R, 'fwtest-20261117', 'x1', 'set.txt'),
 447                  x2=os.path.join(R, 'fwtest-20261117', 'x2', 'set.txt'),
 448                  revert=os.path.join(R, 'fwtest-20261117', 'revert', 'set.txt'),
 449                  dimm=os.path.join(R, 'dimm7200-20261117', 'set.txt'))
 450      assert sorted(found['q']) == sorted(lists.values()), found['q']
 451      assert sorted(found['set']) == sorted(sets.values()), found['set']</pre></td><td valign="top">The files that the script expects.<ul><li><code>lists</code>: three saved lists of all settings (<code>questions.json</code>), with the keys <code>base</code>, <code>x1</code> and <code>revert</code>.</li><li><code>sets</code>: four files with the replies of <code>set</code> calls (<code>set.txt</code>), with the keys <code>x1</code>, <code>x2</code>, <code>revert</code> and <code>dimm</code>.</li><li>The two <code>assert</code> statements stop the script when the files found under <code>R</code> are not exactly these 7 files.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 452      key = lambda e: (e['name'], e['answer'], json.dumps(e['options']), e['help'])
 453      for k, path in lists.items():
 454          q = json.loads(fd._open(path).read())
 455          assert all(sorted(e) == ['answer', 'help', 'name', 'options'] for e in q), path
 456          val = {}
 457          for n in ('TXREQ Max', 'TXREQ Min', 'DIMM Frequency'):
 458              hit = [e['answer'] for e in q if e['name'] == n]
 459              assert len(hit) == 1, (path, n)
 460              val[n] = hit[0]
 461          un = sum(1 for e in q if e['answer'].startswith('&lt;ValueUnavailable'))
 462          err = sum(1 for e in q if e['answer'].startswith('&lt;VStoreError'))      # a read error of the tool, not a value
 463          out['lists'][k] = dict(path=path, mtime=mtime(path), n=len(q), unavailable=un, store_error=err,
 464                                 readable=len(q) - un - err,
 465                                 val=val, keys=sorted(map(key, q)), order=[key(e) for e in q])</pre></td><td valign="top">For each of the three lists the file is parsed as JSON. Every entry must have exactly the four keys <code>answer</code>, <code>help</code>, <code>name</code> and <code>options</code>.<ul><li><code>val</code>: the answer of the settings <code>TXREQ Max</code>, <code>TXREQ Min</code> and <code>DIMM Frequency</code>. Each name must occur exactly once. The first two are the settings that the <code>set.txt</code> files of the folder <code>fwtest-20261117</code> name.</li><li><code>unavailable</code>, <code>store_error</code>: the number of entries whose answer starts with <code>&lt;ValueUnavailable</code> or with <code>&lt;VStoreError</code>. <code>readable</code> is the number of the other entries.</li><li><code>keys</code>, <code>order</code>: every entry as a tuple of name, answer, options and help. <code>keys</code> is sorted. <code>order</code> keeps the file order.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 466      b, r = out['lists']['base'], out['lists']['revert']
 467      out['same_entries'] = b['keys'] == r['keys']
 468      out['same_order'] = b['order'] == r['order']
 469      out['x1_diff'] = sorted(set(out['lists']['x1']['keys']) ^ set(b['keys']))</pre></td><td valign="top">Compares the lists.<ul><li><code>same_entries</code>: true when <code>base</code> and <code>revert</code> hold the same entries after sorting.</li><li><code>same_order</code>: true when the two files hold the entries in the same order.</li><li><code>x1_diff</code>: the entries that are in only one of <code>x1</code> and <code>base</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 470      # the replies of the 'set' calls. Two forms exist: one JSON object per line, or the debug print of the tool.
 471      for k, path in sets.items():
 472          lines = fd._open(path).read().splitlines()
 473          try:
 474              when, when_line = fd.dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y'), 1
 475          except ValueError:
 476              when, when_line = None, None
 477          rep = []
 478          block = None</pre></td><td valign="top">For each <code>set.txt</code>: <code>when</code> is the date and time of line 1, when line 1 has the form <code>Tue Nov 17 03:43:50 AM UTC 2026</code>. If line 1 has another form, <code>when</code> and <code>when_line</code> are <code>None</code>. <code>rep</code> will hold the replies. <code>block</code> holds a reply that is still being read.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 479          for ln, l in enumerate(lines, 1):
 480              t = l.strip()
 481              if t.startswith('{"responses"'):
 482                  for x in json.loads(t)['responses']:
 483                      rep.append(dict(kind='set' if 'modified' in x else 'get', name=x['question']['name'],
 484                                      answer=x['question']['answer'], modified=x.get('modified'), line=ln))
 485              elif t in ('SetResponse {', 'GetResponse {'):
 486                  block = dict(kind=t[:3].lower(), name=None, answer=None, modified=None, line=None)
 487              elif block is not None:
 488                  m = re.match(r'(name|answer): "(.*)",$', t)
 489                  if m and block[m[1]] is None:
 490                      block[m[1]] = m[2]
 491                      if m[1] == 'answer':
 492                          block['line'] = ln
 493                  m = re.match(r'modified: (true|false),$', t)
 494                  if m:
 495                      block['modified'] = m[1] == 'true'
 496                  if t.startswith('is_translated:'):
 497                      rep.append(block)
 498                      block = None
 499          assert rep and all(x['name'] and x['answer'] for x in rep), path
 500          out['sets'][k] = dict(path=path, when=when, when_line=when_line, mtime=mtime(path), replies=rep,
 501                                set=[x for x in rep if x['kind'] == 'set'], get=[x for x in rep if x['kind'] == 'get'])</pre></td><td valign="top">Collects the replies. The files hold two forms.<ul><li>A line that starts with <code>{"responses"</code> is JSON. Each response gives one reply. Its kind is <code>set</code> when the response has the key <code>modified</code>, and <code>get</code> when not.</li><li>A block that starts with <code>SetResponse {</code> or <code>GetResponse {</code> is the debug print of the tool. The first <code>name:</code> line and the first <code>answer:</code> line of the block are kept, and the value of <code>modified:</code>. The line <code>is_translated:</code> ends the block.</li><li>Each reply holds kind, setting name, answer, <code>modified</code> and a line number.</li><li>The <code>assert</code> requires at least one reply, and a name and an answer in every reply. <code>out['sets']</code> keeps the time, the replies, and the replies split by kind.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 502      fin = os.path.join(R, 'dimm7200-20261117', 'setting-final.txt')
 503      fl = fd._open(fin).read().splitlines()
 504      assert len(fl) == 1, fin
 505      out['final'] = dict(path=fin, mtime=mtime(fin), text=fl[0].strip(), answer=re.search(r'answer: "(.*)",', fl[0])[1])
 506      return out
 507
 508</pre></td><td valign="top">Reads <code>setting-final.txt</code> of the folder <code>R/dimm7200-20261117</code>. The comment of the function calls it the last reading of the memory speed setting.<ul><li>The file must hold exactly one line.</li><li><code>answer</code> is the text between the quotes after <code>answer:</code>.</li><li>In the file that line is <code>answer: "7200 MT/s",</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>open_a2pre</code>: the run folder before baseline A-2</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 509  def open_a2pre():
 510      """The run folder that ended 8 s before the first process of baseline A-2: its times and its processes."""
 511      folder = os.path.join(R, 'partA-20261113T204939Z')
 512      T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
 513      env_path = os.path.join(folder, 'env.txt')
 514      env = fd._open(env_path).read().splitlines()
 515      m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) .* steps=(.*)$', env[0])
 516      end = [(ln, re.match(r'## end utc=(\S+) loadavg=(\S+) ', l)) for ln, l in enumerate(env, 1) if l.startswith('## end utc=')]
 517      assert m and len(end) == 1 and end[0][1], env_path
 518      out = dict(folder=folder, env_path=env_path, start=T(m[1]), start_line=1, steps=m[3].split(),
 519                 end=T(end[0][1][1]), end_line=end[0][0], load_end=float(end[0][1][2]), files={})</pre></td><td valign="top">Reads the folder <code>R/partA-20261113T204939Z</code>. This function reads no rate.<ul><li>Line 1 of its <code>env.txt</code> gives the start time and the list of steps after <code>steps=</code>.</li><li>The line <code>## end utc=...</code> gives the end time and the 1-minute load average at the end. The <code>assert</code> requires exactly one such line.</li><li>In the file the end time is 20:50:47 UTC. The first header line of <code>A1.csv</code> of baseline A-2 gives 20:50:55 UTC. That is 8 s later.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 520      hdr = []
 521      for n in ('A5.csv', 'A6.csv'):
 522          h = fd.step_headers(os.path.join(folder, n))
 523          out['files'][n] = dict(path=os.path.join(folder, n), n=len(h))
 524          hdr += h
 525      out['hdr'] = hdr
 526      out['threads'] = sorted({re.search(r'--threads (\S+)', h['args'])[1] for h in hdr})
 527      out['binaries'] = sorted({h['binary'] for h in hdr})
 528      out['first'], out['last'] = min(h['utc'] for h in hdr), max(h['utc'] for h in hdr)</pre></td><td valign="top"><code>fd.step_headers</code> returns the <code>-- step</code> header lines of <code>A5.csv</code> and <code>A6.csv</code>. The function stores:<ul><li>the number of header lines per file, and all header lines in <code>hdr</code>.</li><li><code>threads</code>: the distinct values of <code>--threads</code>. <code>binaries</code>: the distinct binaries.</li><li><code>first</code>, <code>last</code>: the first and the last launch time.</li><li>In this folder the two files hold 4 and 16 header lines. All 20 processes ran <code>bw_new</code> with <code>--threads 1</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 529      # launches.txt of that folder: one '== file tag' line per process
 530      lp = os.path.join(folder, 'launches.txt')
 531      ll = [l.split()[1] for l in fd._open(lp) if l.startswith('== ')]
 532      out['launches_path'], out['launches_n'], out['launches_files'] = lp, len(ll), sorted(set(ll))
 533      return out
 534
 535</pre></td><td valign="top">Reads <code>launches.txt</code> of the same folder.<ul><li>A line that starts with <code>== </code> belongs to one process. Its second word is the name of the csv file.</li><li>The function stores the number of these lines and the distinct file names.</li></ul>Then it returns <code>out</code>.</td></tr>
<tr><td colspan="2"><b>Function <code>open_mod</code>: files that support the count of 12 modules</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 536  def open_mod():
 537      """What a boot with 10 modules shows in the two lines that the sheet uses as proof of 12 modules:
 538      the saved journal and kernel log of the 10-module boot of 2026-11-17 04:17, and the module list that
 539      was saved in the boot of the rerun."""
 540      C = os.path.join(R, 'dimm-check-20261117')
 541      h1 = os.path.join(C, 'h-1.txt')
 542      hl = fd._open(h1).read().splitlines()
 543      out = dict(h1=h1, h1_start=fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S'),
 544                 h1_dimm=int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1]), h1_dimm_line=2)</pre></td><td valign="top"><code>collect</code> calls this function at line 289 and stores the result in <code>D['mod']</code>. No rate is read here. FACTS.md uses two values as proof of 12 modules: MemTotal and the DIMM sockets message. This function reads what a boot with 10 modules shows: its DIMM sockets message and the memory size line of its Linux kernel log.<ul><li>It first reads <code>h-1.txt</code>, the saved journal of a boot of 2026-11-17 with 10 memory modules.</li><li><code>h1_start</code>: the start time of that boot, from the first 19 characters of line 1.</li><li><code>h1_dimm</code>: the number in the message <code>This system has N DIMM sockets</code> of line 2. It is 10 in this file.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 545      for k in ('k-1.txt', 'k-5.txt'):
 546          path = os.path.join(C, k)
 547          kl = fd._open(path).read().splitlines()
 548          hit = [(ln, re.search(r'kernel: Memory: (\d+)K/(\d+)K available', l)) for ln, l in enumerate(kl, 1)
 549                 if 'kernel: Memory: ' in l]
 550          assert len(hit) == 1 and hit[0][1], path
 551          out[k[:3]] = dict(path=path, line=hit[0][0], avail_K=int(hit[0][1][1]), total_K=int(hit[0][1][2]),
 552                            stamp=kl[hit[0][0] - 1][:15])</pre></td><td valign="top">Reads two saved Linux kernel logs: <code>k-1.txt</code> of the same 10-module boot and <code>k-5.txt</code> of the boot that started on 2026-11-09.<ul><li>Each file must hold exactly one line with the text <code>kernel: Memory: </code> in the form <code>...K/...K available</code>. If not, the <code>assert</code> stops the script.</li><li>Example, line 762 of <code>k-1.txt</code>: <code>Memory: 329221340K/334981392K available</code>.</li><li><code>out['k-1']</code> and <code>out['k-5']</code> keep the line number, the two numbers (<code>avail_K</code>, <code>total_K</code>) and the first 15 characters of the line, which are its time stamp.</li><li><code>facts_text.py</code> stops the script unless the two <code>total_K</code> values differ by 64 x 1024 x 1024 K. FACTS.md states that the DIMM report reads this difference as 64 GiB (1 GiB = 2^30 bytes), the size of two modules.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 553      dmi = os.path.join(R, 'dimm7200-20261117', 'dmi17-7200.txt')
 554      dl = fd._open(dmi).read().splitlines()
 555      out['dmi'] = dict(path=dmi, mtime=fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(dmi))),
 556                        devices=sum(1 for l in dl if l.strip() == 'Memory Device'),
 557                        speed=sum(1 for l in dl if l.strip() == 'Configured Memory Speed: 7200 MT/s'),
 558                        size=sum(1 for l in dl if l.strip() == 'Size: 32 GB'),
 559                        volatile=sum(1 for l in dl if l.strip() == 'Volatile Size: 32 GB'),
 560                        size_any=sum(1 for l in dl if 'Size: 32 GB' in l))</pre></td><td valign="top">Reads <code>dmi17-7200.txt</code>, the module list that was saved in the boot of the rerun. The file is the output of the command <code>dmidecode -t 17</code>, which prints the hardware table of the firmware. The function counts lines. For the first four counts it compares the line without the tabs and spaces at its two ends.<ul><li><code>devices</code>: lines equal to <code>Memory Device</code>. The file holds one such entry per memory module.</li><li><code>speed</code>: lines equal to <code>Configured Memory Speed: 7200 MT/s</code>.</li><li><code>size</code>: lines equal to <code>Size: 32 GB</code>. <code>volatile</code>: lines equal to <code>Volatile Size: 32 GB</code>.</li><li><code>size_any</code>: lines that hold the text <code>Size: 32 GB</code> at any place. This count includes the lines of <code>size</code> and of <code>volatile</code>.</li><li>In this file the five counts are 12, 12, 12, 12 and 24.</li><li><code>mtime</code>: the time of the last change of the file, in UTC, in whole seconds. <code>facts_text.py</code> stops the script unless this time lies inside the time span of row 0 of <code>boots.txt</code>. Row 0 is the boot of the rerun.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 561      t6 = fd._open(os.path.join(R, 'dimm7200-20261117', 'try6.txt')).read().splitlines()
 562      m = [(ln, re.fullmatch(r'modules=(\d+)', l)) for ln, l in enumerate(t6, 1) if l.startswith('modules=')]
 563      assert len(m) == 1 and m[0][1]
 564      out['try6_modules'], out['try6_modules_line'] = int(m[0][1][1]), m[0][0]
 565      return out
 566
 567</pre></td><td valign="top">Reads <code>try6.txt</code> once more and looks for lines that start with <code>modules=</code>. Exactly one such line must exist, and it must have the form <code>modules=N</code>. If not, the <code>assert</code> stops the script.<ul><li><code>try6_modules</code> is N, and <code>try6_modules_line</code> is the line number. In this file line 6 reads <code>modules=24</code>.</li><li><code>facts_text.py</code> stops the script unless N equals <code>size_any</code>, the count of the lines with the text <code>Size: 32 GB</code>.</li><li>The module count of the records (12) does not come from this line. <code>collect</code> takes it from the DIMM sockets line of the same file, in line 56 of this script.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>open_probe13</code>: records of the first test of 2026-11-13</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 568  def open_probe13(kfolder):
 569      """probe.txt and one-thread.csv of the 2026-11-13 run: checksums, times, one-thread phase."""
 570      path = os.path.join(kfolder, 'probe.txt')
 571      lines = fd._open(path).read().splitlines()
 572      sha, sha_line = {}, {}
 573      for ln, l in enumerate(lines, 1):
 574          m = re.match(r'^([0-9a-f]{64})  (\S+)$', l)
 575          if m:
 576              sha[m[2]] = m[1]
 577              sha_line[m[2]] = ln
 578      T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
 579      out = dict(path=path, sha=sha, sha_line=sha_line)</pre></td><td valign="top"><code>collect</code> calls this function at line 195 with the folder <code>R/kernels-20261113T181222Z</code>, the folder of baseline A-1. The result is stored in <code>D['probe13']</code>. No rate is read here.<ul><li>The function first reads <code>probe.txt</code> of that folder.</li><li>Every line that consists of 64 hexadecimal digits, two spaces and a name gives one entry of <code>sha</code> (name to sha256) and one entry of <code>sha_line</code> (name to line number).</li><li>In this file the lines 18, 19 and 20 hold the values of <code>run_kernels.sh</code>, <code>bw_old</code> and <code>bw_new</code>. The checks <code>sha-bw</code> and <code>A-args</code> use them.</li><li>No check of this script uses the entries of the source files. Line 15 records the sha256 <code>c1406e02...</code> for <code>bandwidth.c</code>. The local <code>bandwidth.c</code> in the folder <code>kernels-2026-11-13</code> has another sha256, <code>f1985072...</code>. That is the value in <code>probe.txt</code> of the run of 18:32:18 UTC on the same day, which built the binaries and timed nothing.</li><li>Both records give the same sha256 for the binary <code>bw_new</code> (<code>fd7c14df...</code>). So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above <code>k_read</code> with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (<code>/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl</code>, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.</li><li><code>T</code> turns a time text such as <code>2026-11-13T18:12:22Z</code> into a date and time.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 580      for ln, l in enumerate(lines, 1):
 581          m = re.match(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+)', l)
 582          if m:
 583              out['utc'], out['load_before'], out['logins'] = T(m[1]), (m[2], m[3], m[4]), int(m[5])
 584          m = re.match(r'## one-thread done load=(\S+) \S+ \S+ utc=(\S+)', l)
 585          if m:
 586              out['one_done_load'], out['one_done_utc'], out['one_done_line'] = float(m[1]), T(m[2]), ln
 587          m = re.match(r'## load_after=(\S+) \S+ \S+ utc=(\S+)', l)
 588          if m:
 589              out['load_after'], out['utc_after'], out['after_line'] = float(m[1]), T(m[2]), ln
 590      out['has_memtotal'] = any('MemTotal' in l for l in lines)
 591      out['has_boot_id'] = any('boot_id' in l for l in lines)</pre></td><td valign="top">Finds three lines of the same <code>probe.txt</code> that start with <code>##</code>.<ul><li>The <code>## host=</code> line gives the start time (<code>utc</code>), the three load averages (<code>load_before</code>) and the number of logins.</li><li>The <code>## one-thread done</code> line gives the 1-minute load average and the time at the end of the one-thread phase (<code>one_done_load</code>, <code>one_done_utc</code>).</li><li>The <code>## load_after=</code> line gives the 1-minute load average and the time after the 120-thread part (<code>load_after</code>, <code>utc_after</code>).</li><li><code>has_memtotal</code> and <code>has_boot_id</code> say whether any line of the file holds the text <code>MemTotal</code> or <code>boot_id</code>. Both are false for this file. <code>facts_text.py</code> stops the script if one of them is true.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 592      one = os.path.join(kfolder, 'one-thread.csv')
 593      hdr = [l for l in fd._open(one) if l.startswith('-- binary')]
 594      out['one_path'], out['one_n'] = one, len(hdr)
 595      out['one_first'] = re.search(r'utc (\S+)', hdr[0])[1]
 596      out['one_last'] = re.search(r'utc (\S+)', hdr[-1])[1]</pre></td><td valign="top">Reads <code>one-thread.csv</code> of the same folder, the result file of the one-thread phase. Only the header lines that start with <code>-- binary</code> are kept.<ul><li><code>one_n</code> is their number (192 in this file).</li><li><code>one_first</code> and <code>one_last</code> are the times of day of the first and the last header line.</li><li>No interval row of this file is used. So no one-thread rate enters the records.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 597      # journal of that boot (saved 2026-11-17): start, module line, error records during the run
 598      h5 = os.path.join(R, 'dimm-check-20261117', 'h-5.txt')
 599      hl = fd._open(h5).read().splitlines()
 600      out['h5'] = h5
 601      out['boot_start'] = fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S')
 602      out['boot_dimm'] = int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1])
 603      day = out['utc'].strftime('%Y-%m-%dT')
 604      first_rec = next(i for i, l in enumerate(hl, 1) if '[Hardware Error]' in l)
 605      out['first_record_line'] = first_rec
 606      out['first_record_utc'] = fd.dt.datetime.strptime(hl[first_rec - 1][:19], '%Y-%m-%dT%H:%M:%S')
 607      lo, hi = out['one_done_utc'], out['utc_after']
 608      out['records_in_120'] = sum(1 for l in hl if l.startswith(day) and '[Hardware Error]' in l
 609                                  and lo &lt;= fd.dt.datetime.strptime(l[:19], '%Y-%m-%dT%H:%M:%S') &lt;= hi)</pre></td><td valign="top">Reads <code>h-5.txt</code>, the saved journal of the boot that started on 2026-11-09. The test of 2026-11-13 ran in that boot.<ul><li><code>boot_start</code>: the start time of the boot, from line 1. <code>boot_dimm</code>: the number in the DIMM sockets message of line 2 (12 in this file).</li><li><code>first_record_line</code>, <code>first_record_utc</code>: the line number and the time of the first line with the text <code>[Hardware Error]</code>.</li><li><code>records_in_120</code>: the number of lines of the day of the test that hold <code>[Hardware Error]</code> and whose time lies from <code>one_done_utc</code> to <code>utc_after</code>, both ends included. This span is the 120-thread part of baseline A-1.</li><li>The code counts lines here, and one record has several such lines. The count is 0 in this data.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 610      # the same journal for the baselines A-2 and A-3 (one record = one line 'Hardware error from APEI ...')
 611      errs = fd.read_error_records(h5)
 612      pfolder = os.path.join(R, 'partA-20261113T205055Z')
 613      h1 = fd.step_headers(os.path.join(pfolder, 'A1.csv'))
 614      h2 = fd.step_headers(os.path.join(pfolder, 'A2.csv'))
 615      h3 = fd.step_headers(os.path.join(pfolder, 'A3.csv'))
 616      out['a2_csv2'] = os.path.join(pfolder, 'A2.csv')
 617      out['a2_window'] = (h1[0]['utc'], h2[0]['utc'])
 618      out['a2_first'] = h1[0]</pre></td><td valign="top"><code>fd.read_error_records</code> returns every hardware error record of the same journal, one per line <code>Hardware error from APEI ...</code> (321 records in this file). <code>fd.step_headers</code> returns the <code>-- step</code> header lines of <code>A1.csv</code>, <code>A2.csv</code> and <code>A3.csv</code> in <code>R/partA-20261113T205055Z</code>. Each process has one such header line. The line gives the launch time of the process.<ul><li><code>a2_window</code>: from the launch of the first process of <code>A1.csv</code> to the launch of the first process of <code>A2.csv</code>. This is the time span of baseline A-2.</li><li><code>a2_first</code>: the header line of the first process of <code>A1.csv</code>. <code>a2_csv2</code>: the path of <code>A2.csv</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 619      # The first A-3 process is the first process of A3.csv. run_partA.sh ran the steps in the order of
 620      # 'steps=' in env.txt, so the process directly before it is the last process of A2.csv.
 621      steps = re.search(r' steps=(.*)$', fd._open(os.path.join(pfolder, 'env.txt')).read().splitlines()[0])[1].split()
 622      assert steps.index('A2') + 1 == steps.index('A3') and h3[0]['line'] == 1 and h2[-1]['utc'] &lt; h3[0]['utc']
 623      out['a3_prev'] = h2[-1]
 624      out['a3_first'] = h3[0]</pre></td><td valign="top">Finds the process that ran directly before the first process of baseline A-3.<ul><li>Line 1 of <code>env.txt</code> holds the list <code>steps=A1 A2 A3 A4</code>. The comment says that the script run_partA.sh ran the steps in this order.</li><li>The <code>assert</code> stops the script unless three things hold. A3 directly follows A2 in that list. The first header line of <code>A3.csv</code> is line 1 of the file. The last process of <code>A2.csv</code> was launched before the first process of <code>A3.csv</code>.</li><li>Then <code>a3_prev</code> is the last process of <code>A2.csv</code>, and <code>a3_first</code> is the first process of <code>A3.csv</code>.</li><li><code>write_json</code> names <code>a3_prev</code> in the description of the field <code>kernel_before</code> (lines 931 to 936).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 625      out['a2_records'] = []
 626      for e in errs:
 627          if out['a2_window'][0] &lt;= e['utc'] &lt;= out['a2_window'][1]:
 628              i = max(k for k, h in enumerate(h1) if h['utc'] &lt;= e['utc'])
 629              out['a2_records'].append(dict(e, proc=h1[i], next=h1[i + 1] if i + 1 &lt; len(h1) else None))
 630      i3 = [k for k, h in enumerate(h3) if re.fullmatch(r'onebuf-ms500-[123]', h['tag'])]
 631      out['a3_window'] = (h3[i3[0]]['utc'], h3[i3[-1] + 1]['utc'])
 632      out['a3_records'] = [e for e in errs if out['a3_window'][0] &lt;= e['utc'] &lt;= out['a3_window'][1]]
 633      out['n_records_boot'] = len(errs)</pre></td><td valign="top">Finds the hardware error records during the baselines A-2 and A-3.<ul><li><code>a2_records</code>: every record whose time lies in <code>a2_window</code>, both ends included. Each one also gets <code>proc</code>, the last process of <code>A1.csv</code> that was launched at or before the time of the record, and <code>next</code>, the process after it. This data has 4 such records.</li><li><code>i3</code>: the places of the processes of <code>A3.csv</code> whose tag is <code>onebuf-ms500-1</code>, <code>onebuf-ms500-2</code> or <code>onebuf-ms500-3</code>. These three processes are baseline A-3.</li><li><code>a3_window</code>: from the launch of the first of them to the launch of the process after the last of them.</li><li><code>a3_records</code>: the records inside <code>a3_window</code> (none in this data).</li><li><code>n_records_boot</code>: the number of all records of the journal.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 634      out['journal_release'] = re.search(r'Linux version (\S+)', hl[0])[1]
 635      # machine settings saved in the same boot (2026-11-17 03:43 UTC, before the firmware test)
 636      pre = os.path.join(R, 'fwtest-20261117', 'pre')
 637      rd = lambda n: fd._open(os.path.join(pre, n)).read().strip()
 638      out['pre'] = dict(folder=pre, when_path=os.path.join(pre, 'when.txt'), cmdline_path=os.path.join(pre, 'cmdline.txt'),
 639                        gov_path=os.path.join(pre, 'gov.txt'), thp_path=os.path.join(pre, 'thp.txt'),
 640                        when=fd.dt.datetime.strptime(rd('when.txt'), '%a %b %d %I:%M:%S %p UTC %Y'),
 641                        cmdline=rd('cmdline.txt'), gov=[l.strip() for l in rd('gov.txt').splitlines()], thp=rd('thp.txt'))</pre></td><td valign="top"><code>journal_release</code> is the Linux kernel release of that boot, from the text <code>Linux version ...</code> in line 1 of the journal. <code>facts_text.py</code> stops the script unless it equals the release of the rerun. <code>out['pre']</code> holds machine settings that were saved in the same boot, in the folder <code>R/fwtest-20261117/pre</code>:<ul><li><code>when</code>: the time of the save, from <code>when.txt</code> (2026-11-17 03:43:42 UTC).</li><li><code>cmdline</code>: the Linux boot arguments, from <code>cmdline.txt</code>. <code>facts_text.py</code> stops the script unless they equal the boot arguments in the <code>== cmdline</code> line of the go.sh log.</li><li><code>gov</code>: the two lines of <code>gov.txt</code>. In this file they read <code>128 performance</code> and <code>2800000</code>. <code>facts_text.py</code> stops the script unless line 1 is <code>128</code>, a space and the governor name of the go.sh log, and line 2 is the value <code>scaling_cur_freq</code> of CPU 0 of that log.</li><li>A governor is the Linux policy that sets the CPU frequency. <code>scaling_cur_freq</code> is a file of Linux that gives the current frequency of a CPU in kHz (Linux kernel documentation, page "CPU Performance Scaling"). So the value 2800000 of the go.sh log is 2.8 GHz. The same page says that in most cases the value is the frequency that Linux last requested from the hardware. It also says that the CPU may run at another frequency.</li><li><code>thp</code>: the huge-page setting of Linux, from <code>thp.txt</code> (<code>[always] madvise never</code> in this file). <code>facts_text.py</code> stops the script unless it equals the <code>enabled</code> value in the <code>== thp</code> line of the go.sh log.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 642      k5 = os.path.join(R, 'dimm-check-20261117', 'k-5.txt')
 643      kl = fd._open(k5).read().splitlines()
 644      out['k5'], out['k5_last_line'], out['k5_last'] = k5, len(kl), kl[-1][:15]
 645      q = os.path.join(R, 'uefisettings-20261117', 'questions.json')
 646      m = re.search(r'"name":"DIMM Frequency","answer":"(\d+) MT/s"', fd._open(q).read())
 647      out['q_path'], out['q_speed'] = q, int(m[1])
 648      return out
 649
 650</pre></td><td valign="top"><ul><li><code>k5_last_line</code> is the number of lines of the Linux kernel log <code>k-5.txt</code>. <code>k5_last</code> is the time stamp of its last line (<code>Nov 17 03:44:00</code> in this file).</li><li><code>q_speed</code> is the memory speed of the entry <code>DIMM Frequency</code> in <code>questions.json</code> of the folder <code>R/uefisettings-20261117</code>, the saved list of firmware settings. It is 8000 MT/s in this file.</li><li>The function returns <code>out</code>.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>run_checks</code>: 27 integrity checks</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 651  # ----------------------------------------------------------------------------- integrity checks
 652
 653  def run_checks(D):
 654      """Integrity checks. One line of text per check; the line names every folder that it covers."""
 655      C = D['checks']
 656      recs = D['recs']
 657      try6 = D['try6']
 658      A, X = D['A'], D['X']
 659      yn = lambda b: 'yes' if b else 'NO'
 660
 661      def chk(key, ok, text):
 662          C.append(dict(key=key, ok=bool(ok), text=text))
 663
 664      def per(items, fn):
 665          """'T72L1 10, T72L2 10, ...' for a list of rerun folders."""
 666          return ', '.join('%s %s' % (i['tag'], fn(i)) for i in items)
 667</pre></td><td valign="top"><code>main</code> calls this function after <code>collect</code> (line 1036). It appends 27 checks to the list <code>D['checks']</code> in a fixed order. It changes no record.<ul><li><code>yn</code> turns a truth value into the text <code>yes</code> or <code>NO</code>.</li><li><code>chk</code> appends one check: a key, the pass flag <code>ok</code> and one line of text.</li><li><code>per</code> builds a text with one value per rerun folder, for example <code>T72L1 10, T72L2 10</code>.</li><li>A check that fails does not stop this function. The stop comes later: <code>render</code> ends the script when a check failed (see <code>main</code>, line 1037).</li><li>A failed <code>assert</code> (lines 807 and 858) ends the script immediately.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks 1 to 5: logs, boot id, MemTotal, logins</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 668      # logs
 669      for name in ('go', 'go2'):
 670          lg = D['logs'][name]
 671          chk('log-' + name, lg['alldone'] and not lg['failed'],
 672              '%s: the last line is ALLDONE: %s. Lines that start with FAILED: %d'
 673              % (rel(lg['path']), yn(lg['lines'][-1] == 'ALLDONE'), len(lg['failed'])))</pre></td><td valign="top">Checks <code>log-go</code> and <code>log-go2</code>, one per driver log. A check passes when the log holds a line <code>ALLDONE</code> and no line that starts with <code>FAILED</code>. The text says whether the last line is <code>ALLDONE</code>, and it gives the number of <code>FAILED</code> lines.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 674      # boot id and MemTotal of every state line and every probe.txt
 675      states = D['logs']['go']['states'] + D['logs']['go2']['states']
 676      boots = {s['boot'] for s in states} | {a['probe']['boot'] for a in A}
 677      mems = {s['memtotal_kB'] for s in states} | {a['probe']['memtotal_kB'] for a in A} | \
 678             {a['probe']['memtotal_after_kB'] for a in A}
 679      chk('boot', boots == {try6['boot']},
 680          'boot id: %d state lines of the two logs and %d probe.txt files hold %d distinct value(s). Equal to line 2 of '
 681          'try6.txt: %s' % (len(states), len(A), len(boots), yn(boots == {try6['boot']})))
 682      chk('memtotal', mems == {try6['memtotal_kB']},
 683          'MemTotal: %d state lines and %d probe.txt values (start and end of each session) hold %d distinct value(s): '
 684          '%s kB. Equal to line %d of try6.txt: %s'
 685          % (len(states), 2 * len(A), len(mems), ', '.join(str(m) for m in sorted(mems)), try6['memtotal_line'],
 686             yn(mems == {try6['memtotal_kB']})))</pre></td><td valign="top">Checks <code>boot</code> and <code>memtotal</code>.<ul><li><code>states</code>: the state lines of both logs (18 in this data).</li><li><code>boot</code> passes when the boot ids of all state lines and of the 3 <code>probe.txt</code> files of part A are one value, and this value is the boot id in <code>try6.txt</code>.</li><li><code>memtotal</code> passes in the same way for MemTotal. Each <code>probe.txt</code> gives two values: one from the start and one from the end of its session.</li><li><code>try6.txt</code> is the record of 12 modules at 7200 MT/s. So the two checks show that every step of the rerun ran in the boot of that record, with the same MemTotal.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 687      ok = (all(s['logins'] == 0 and s['marker'] == 'absent' for s in states)
 688            and all(a['probe']['logins'] == 0 for a in A) and all(x['launches'][0]['logins'] == 0 for x in X))
 689      chk('logins', ok,
 690          'logins and marker file: logins = 0 and marker "absent" in %d of %d state lines. Logins = 0 in %d of %d '
 691          'probe.txt files and in %d of %d launch lines'
 692          % (sum(s['logins'] == 0 and s['marker'] == 'absent' for s in states), len(states),
 693             sum(a['probe']['logins'] == 0 for a in A), len(A),
 694             sum(x['launches'][0]['logins'] == 0 for x in X), len(X)))</pre></td><td valign="top">Check <code>logins</code>. It passes when three things hold:<ul><li>Every state line shows 0 logins and the marker <code>absent</code>.</li><li>Every <code>probe.txt</code> of part A shows 0 logins.</li><li>The launch line of every bwx12 folder shows 0 logins.</li></ul>The text gives the counts, for example <code>18 of 18 state lines</code>.</td></tr>
<tr><td colspan="2"><b>Checks 6 and 7: shape and order of part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 695      # part A: 24 processes x 3 intervals, same process order as on 2026-11-13
 696      order13 = [(p['binary'], p['kernel'], p['round']) for p in D['base']['A-1']['procs']]
 697      shape = lambda a: (len(a['procs']), sorted({len(p['iv']) for p in a['procs']}),
 698                         sorted({iv['threads'] for p in a['procs'] for iv in p['iv']}))
 699      ok = all(shape(a) == (24, [3], [120]) and all([iv['rep'] for iv in p['iv']] == [0, 1, 2] for p in a['procs'])
 700               for a in A)
 701      chk('A-shape', ok, 'part A, processes x intervals per threads120.csv (expected 24 x 3, 120 threads in every row): '
 702          + per(A, lambda a: '%d x %s, %d rows, threads %s' % (shape(a)[0], '/'.join(map(str, shape(a)[1])),
 703                                                                sum(len(p['iv']) for p in a['procs']),
 704                                                                '/'.join(map(str, shape(a)[2])))))
 705      same = lambda a: [(p['binary'], p['kernel'], p['round']) for p in a['procs']] == order13
 706      chk('A-order', all(same(a) for a in A),
 707          'part A, order of the 24 processes (binary, kernel, round) equal to threads120.csv of 2026-11-13: '
 708          + per(A, lambda a: yn(same(a))))</pre></td><td valign="top">Checks <code>A-shape</code> and <code>A-order</code>, on the 3 <code>threads120.csv</code> files of part A.<ul><li><code>order13</code>: binary, kernel and round of the 24 processes of baseline A-1, in file order.</li><li><code>shape</code> returns three values of one file: the number of processes, the distinct numbers of interval rows per process, and the distinct values of the column <code>threads</code> of the interval rows.</li><li><code>A-shape</code> passes when every file has 24 processes with 3 interval rows each, the column <code>threads</code> is 120 in every row, and the column <code>rep</code> of each process reads 0, 1, 2.</li><li><code>A-order</code> passes when the processes of every file have the same order of binary, kernel and round as in A-1.</li><li>With both checks passed, each session holds 2 processes x 3 interval rows of <code>bw_old</code> with the kernel <code>read</code>, and the same of <code>bw_new</code>. That gives 18 interval rows per read kernel in the 3 sessions.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks 8 to 13: rows of the bwx12 files of the rerun</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 709      # bwx12 folders of the rerun
 710      want_i = dict(L=10, I=10, C=6)
 711      chk('I-rows', all(len(x['sec']['I']) == want_i[x['part']] == len(x['ivs']) for x in X),
 712          '"I" rows per bwx12 csv (expected 10 for parts L and I, 6 for part C): ' + per(X, lambda x: len(x['sec']['I'])))
 713      chk('rc', all(len(x['launches']) == 1 and x['launches'][0]['rc'] == '0' for x in X),
 714          'launches.txt, one launch line with "rc 0" per folder: '
 715          + per(X, lambda x: 'rc ' + '/'.join(str(l['rc']) for l in x['launches'])))
 716      chk('stderr', all(x['stderr_bytes'] == 0 for x in X),
 717          'stderr.txt, bytes per folder (expected 0): ' + per(X, lambda x: x['stderr_bytes']))</pre></td><td valign="top">Three checks on the 9 bwx12 folders of the rerun (<code>X</code>).<ul><li><code>I-rows</code>: the number of I rows of the csv must equal the expected number, and it must equal the number of intervals that <code>fd.bwx_intervals</code> built from the T rows. The expected number is 10 for parts L and I (2 rounds x 5 kernels) and 6 for part C (2 rounds x 3 kernels).</li><li><code>rc</code>: <code>launches.txt</code> must hold exactly one launch line, and its exit status must be <code>0</code>.</li><li><code>stderr</code>: <code>stderr.txt</code> must hold 0 bytes.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 718      ok6456 = lambda x: sum(iv['is_64_56'] and iv['threads'] == 120 for iv in x['ivs'])
 719      chk('6456', all(ok6456(x) == len(x['ivs']) for x in X),
 720          'intervals with 120 threads = 64 on CPUs 0-63 + 56 on CPUs 64-119, on 120 different CPUs: '
 721          + per(X, lambda x: '%d of %d' % (ok6456(x), len(x['ivs']))))
 722      nflag = lambda x: sum(iv['flagged'] for iv in x['ivs'])
 723      D['n_T_rows'] = sum(iv['threads'] for x in X for iv in x['ivs'])
 724      vals = sorted({f for x in X for iv in x['ivs'] for f in iv['flags']})
 725      chk('flags', vals == ['-'],
 726          'flags column of the T rows (one row per thread and interval): %d rows in the 9 files, distinct values %s, '
 727          'rows that are not "-": %s' % (D['n_T_rows'], vals, per(X, nflag)))</pre></td><td valign="top">Checks <code>6456</code> and <code>flags</code>, on the T rows of the 9 files.<ul><li><code>6456</code> passes when every interval has 120 T rows and passes the 64+56 test: 64 threads on CPUs 0-63 and 56 threads on CPUs 64-119, on 120 different CPUs.</li><li><code>D['n_T_rows']</code>: the number of T rows of all intervals (8880 in this data, which is 74 intervals x 120 threads).</li><li><code>vals</code>: the distinct values of the flags column over these T rows.</li><li><code>flags</code> passes when <code>-</code> is the only value. The text also gives the number of flagged rows per folder.</li><li>Neither check removes a row. A T row with a flag stays in the sum of its interval.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 728      huge = lambda x: sum(1 for p in x['sec']['P'] if p[5] == p[4])
 729      tot = sorted({p[4] for x in X for p in x['sec']['P']})
 730      fb = sorted({p[7] for x in X for p in x['sec']['P']})
 731      D['P_kB'] = tot
 732      chk('P-rows', all(huge(x) == len(x['sec']['P']) &gt; 0 for x in X),
 733          '"P" rows (one per thread before the first interval and after each interval): kB_total %s in all rows. Rows '
 734          'with kB_huge equal to kB_total: %s. Values of thp_fault_fallback: %s'
 735          % (tot, per(X, lambda x: '%d of %d' % (huge(x), len(x['sec']['P']))), fb))</pre></td><td valign="top">Check <code>P-rows</code>, on the page state of the buffers. A P row is stored as a tuple of the values after the leading <code>P</code>. Counted from 0, its places 4, 5 and 7 hold the columns <code>kB_total</code>, <code>kB_huge</code> and <code>thp_fault_fallback</code>.<ul><li><code>huge(x)</code>: the number of P rows of a folder in which <code>kB_huge</code> equals <code>kB_total</code>. In such a row the whole buffer is on huge pages.</li><li><code>tot</code>: the distinct values of <code>kB_total</code>. The only value in this data is 262144 kB. With 1 kB = 1024 bytes this is 256 MiB (1 MiB = 2^20 bytes), the size of one buffer. The list is kept as <code>D['P_kB']</code> for the text of FACTS.md.</li><li><code>fb</code>: the distinct values of <code>thp_fault_fallback</code>. The text prints them. They are not part of the pass condition.</li><li>The check passes when every folder has at least one P row and <code>kB_huge</code> equals <code>kB_total</code> in all of its P rows.</li></ul></td></tr>
<tr><td colspan="2"><b>Check 14, <code>I-agg</code>: sum of the T rows against the I row</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 736      dmax = lambda x: max(abs(iv['total'] - iv['I_agg']) for iv in x['ivs'])
 737      agg_limit = 0.05        # GB/s; the pass limit of this check
 738      chk('I-agg', max(dmax(x) for x in X) &lt; agg_limit,
 739          'total of the T rows against aggregate_GBps of the "I" row of the same interval, largest difference in GB/s '
 740          '(pass limit set by this script: below %.2f GB/s): ' % agg_limit + per(X, lambda x: '%.3f' % dmax(x)))</pre></td><td valign="top"><b>The rate of this script against the rate that bwx12 printed.</b><ul><li><code>iv['total']</code> is the rate that the records use: the sum over the T rows of bytes / elapsed_s / 1e9. The bytes of each thread are divided by the elapsed time of that thread.</li><li><code>iv['I_agg']</code> is the column <code>aggregate_GBps</code> of the I row of the same interval. bwx12 computed it as the bytes of all threads / the longest per-thread time, and it printed 2 decimal places.</li><li><code>dmax(x)</code>: the largest absolute difference of the two values over the intervals of one folder, in GB/s.</li><li>The check passes when the largest <code>dmax</code> of the 9 folders is below <code>agg_limit</code> = 0.05 GB/s. This limit is a choice of the script.</li><li>In this data the largest difference is 0.018 GB/s, in T72L1 [Ref9].</li><li>Example: the interval of round 0, position 0 (oldread) of T72L1 has <code>total</code> = 462.300 GB/s and <code>I_agg</code> = 462.29 GB/s [Ref8].</li></ul></td></tr>
<tr><td colspan="2"><b>Checks 15 to 22: arguments, checksums, Linux release, runnable tasks</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 741      # spec lines
 742      spec = {n: fd._open(os.path.join(S, n + '.spec')).read().strip().split('|', 1) for n in ('like', 'cfwd', 'crev')}
 743      okarg = lambda x: [x['launches'][0]['tag'], x['launches'][0]['args']] == spec[x['spec']]
 744      chk('args', all(okarg(x) for x in X),
 745          'tag and arguments of the launch line equal to the spec file: '
 746          + per(X, lambda x: '%s.spec %s' % (x['spec'], yn(okarg(x)))))
 747      r8 = D['rx']['L-1']['launches']['a6456']['args']
 748      f72 = D['rx']['F72d12']['launches']['a6456']['args']
 749      chk('args-R8', spec['like'][1] == r8 == f72,
 750          'argument line of like.spec equal to the a6456 launch line of L-1 (w120-R8) and of F72d12: %s'
 751          % yn(spec['like'][1] == r8 == f72))</pre></td><td valign="top">Checks <code>args</code> and <code>args-R8</code>, on the arguments of the bwx12 processes.<ul><li><code>spec</code>: the content of <code>like.spec</code>, <code>cfwd.spec</code> and <code>crev.spec</code>, each split at the first <code>|</code> into tag and arguments.</li><li><code>args</code> passes when the tag and the arguments of the launch line of every rerun folder equal the spec file of that folder. The arguments hold the stop rule (<code>--stop common</code>), the interval length (<code>--min-ms 6000</code>) and the kernel sequence (<code>--seq</code>).</li><li>With the common stop, bwx12 sets one deadline for all threads, 6000 ms after the common start time. A thread stops at its first clock reading at or after the deadline. So 6000 ms is not a lower limit for the timed span of one thread. In the 8880 T rows of the rerun the column <code>elapsed_s</code> lies between 5.999979 s and 6.000457 s.</li><li><code>args-R8</code> passes when the arguments of <code>like.spec</code> equal the arguments of the <code>a6456</code> launch line of L-1 and of F72d12.</li><li>With both checks passed, part L, control I, baseline L-1 and F72d12 ran with the same argument line.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 752      # checksums of the binaries
 753      p13 = D['probe13']
 754      ok = all(a['probe']['sha'][b] == p13['sha'][b] for a in A for b in ('bw_old', 'bw_new'))
 755      ok2 = all(re.search(r'^%s  %s$' % (p13['sha'][b], b), D['env_partA'], re.M) for b in ('bw_old', 'bw_new'))
 756      chk('sha-bw', ok and ok2,
 757          'sha256 of bw_old (%s...) and bw_new (%s...): the 3 probe.txt files of part A equal lines %d and %d of '
 758          'probe.txt of 2026-11-13: %s. env.txt of partA-20261113T205055Z holds the same two values: %s'
 759          % (p13['sha']['bw_old'][:8], p13['sha']['bw_new'][:8], p13['sha_line']['bw_old'], p13['sha_line']['bw_new'],
 760             yn(ok), yn(ok2)))
 761      ra = fd.sha256(os.path.join(S, 'ra.sh'))
 762      ok = all(a['probe']['sha']['ra.sh'] == ra for a in A)
 763      chk('sha-ra', ok, 'sha256 of ra.sh in the 3 probe.txt files equal to S/ra.sh (%s...): %s' % (ra[:8], yn(ok)))</pre></td><td valign="top">Checks <code>sha-bw</code> and <code>sha-ra</code>. <code>p13</code> is the result of <code>open_probe13</code>.<ul><li><code>ok</code>: the sha256 values of <code>bw_old</code> and <code>bw_new</code> in the 3 <code>probe.txt</code> files of part A equal the values in <code>probe.txt</code> of 2026-11-13. ra.sh computed the values of part A on CRB with <code>sha256sum</code>, once at the start of each session [Ref10]. Before that, ra.sh tests both binaries against the two sha256 values that are written in its own text, and it stops when the test fails.</li><li><code>ok2</code>: <code>env.txt</code> of the folder <code>partA-20261113T205055Z</code> holds the same two values. This folder holds the baselines A-2 and A-3.</li><li><code>sha-bw</code> passes when <code>ok</code> and <code>ok2</code> are true. Then part A of the rerun and the baselines A-1, A-2 and A-3 ran the same two binaries.</li><li><code>sha-ra</code> passes when the sha256 of the local file <code>S/ra.sh</code> equals the value of <code>ra.sh</code> in each <code>probe.txt</code>. ra.sh wrote that value on CRB from its own file.</li><li>The script computes no sha256 of a binary. The files <code>bw_old</code>, <code>bw_new</code> and <code>bwx12</code> are not in the local folders. So <code>sha-bw</code> and <code>sha-bwx12</code> (next row) compare only sha256 values that the records hold.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 764      shas = {x['env']['sha'] for x in X}
 765      same12 = [n for n in ('L-1', 'L-2', 'L-3', 'L-4', 'X2d12', 'F72d12', 'X1d10', 'X1d10b', 'BASEd10')
 766                if D['rx'][n]['env']['sha'] in shas]
 767      go_sha = re.search(r'^SHA=([0-9a-f]{64})', fd._open(os.path.join(S, 'go.sh')).read(), re.M)[1]
 768      chk('sha-bwx12', len(shas) == 1 and len(same12) == 9 and {go_sha} == shas,
 769          'sha256 of bwx12 in env.txt: %d distinct value(s) in the %d folders of parts L, C, I (%s...). Equal to SHA= '
 770          'in go.sh: %s. The same value is in env.txt of %s'
 771          % (len(shas), len(X), sorted(shas)[0][:8], yn({go_sha} == shas), ', '.join(same12)))</pre></td><td valign="top">Check <code>sha-bwx12</code>.<ul><li><code>shas</code>: the distinct sha256 values of bwx12 in <code>env.txt</code> of the 9 rerun folders.</li><li>rx.sh does not compute this value. It takes the value from its third argument. It tests the binary against the value with <code>sha256sum -c</code> and stops when the test fails. Then it writes the value into <code>env.txt</code>. go.sh and go2.sh pass their value <code>SHA</code> as this argument.</li><li><code>same12</code>: the earlier bwx12 data sets, out of 9 names, whose <code>env.txt</code> holds a value of <code>shas</code>.</li><li><code>go_sha</code>: the value of the line <code>SHA=</code> in the local <code>go.sh</code>. go.sh tests the bwx12 binary on CRB against this value.</li><li>The check passes when <code>shas</code> holds one value, all 9 earlier data sets hold it, and it equals <code>go_sha</code>. Then parts L and C, control I and these 9 data sets ran the same bwx12 binary.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 772      listed = {}
 773      for f in ('local.sha', 'go2.sha'):
 774          for l in fd._open(os.path.join(S, f)):
 775              h, n = l.split()
 776              listed[os.path.basename(n)] = h
 777      bad = [n for n, h in listed.items() if fd.sha256(os.path.join(S, n)) != h]
 778      chk('sha-local', not bad,
 779          'sha256 of the %d local run files (%s) equal to the lists local.sha and go2.sha: %s'
 780          % (len(listed), ', '.join(sorted(listed)), yn(not bad)))</pre></td><td valign="top">Check <code>sha-local</code>.<ul><li>The files <code>local.sha</code> and <code>go2.sha</code> in <code>S</code> hold one line per file: a sha256 value and a file name. <code>listed</code> maps each file name to its value.</li><li>This data lists 6 files: <code>go.sh</code>, <code>go2.sh</code>, <code>ra.sh</code> and the 3 spec files.</li><li><code>bad</code> holds the names whose local file in <code>S</code> has another sha256. The check passes when <code>bad</code> is empty.</li><li>The check reads local files only. A pass shows that the 6 files in <code>S</code> have not changed since the two lists were written. The row of lines 853 to 866 says what is known about the copies on CRB.</li><li>The stored sheet shows a pass. A new build fails since 2026-11-24. Line 20 of go.sh was edited on that day (the text of one message). So <code>bad</code> holds <code>go.sh</code>. With the old line 20 put back the check passes again [Ref17].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 781      # Linux kernel release, runnable tasks
 782      rel_ = {a['probe']['kernel'] for a in A} | {x['env']['kernel'] for x in X}
 783      cmd_rel = re.search(r'vmlinuz-(\S+)', D['logs']['go']['other']['cmdline'][0])[1]
 784      chk('uname', rel_ == {cmd_rel},
 785          'Linux kernel release: %d distinct value(s) in the %d probe.txt and %d env.txt files. Equal to the image '
 786          'name of the command line: %s' % (len(rel_), len(A), len(X), yn(rel_ == {cmd_rel})))</pre></td><td valign="top">Check <code>uname</code>.<ul><li><code>rel_</code>: the distinct values of the Linux kernel release in the 3 <code>probe.txt</code> files and the 9 <code>env.txt</code> files.</li><li><code>cmd_rel</code>: the text after <code>vmlinuz-</code> in the <code>== cmdline</code> line of the go.sh log. In this log the boot arguments start with <code>BOOT_IMAGE=/vmlinuz-7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858</code>. So <code>cmd_rel</code> is the release part of the name of the Linux image.</li><li>The check passes when <code>rel_</code> holds one value and this value equals <code>cmd_rel</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 787      run_ = [x['launches'][0]['runnable'] for x in X] + [a['probe']['runnable'] for a in A]
 788      limit = int(re.search(r'\$r -le (\d+)', fd._open(os.path.join(S, 'ra.sh')).read())[1])
 789      rx_, ra_ = [x['launches'][0]['runnable'] for x in X], [a['probe']['runnable'] for a in A]
 790      sleep_ = int(re.search(r'^sleep (\d+)', fd._open(os.path.join(S, 'ra.sh')).read(), re.M)[1])
 791      span = lambda v: str(min(v)) if min(v) == max(v) else '%d to %d' % (min(v), max(v))
 792      chk('runnable', max(run_) &lt;= limit,
 793          'runnable tasks: %s at the %d bwx12 launches (launch line of rx.sh). Part A: the value runnable=%s of the %d '
 794          'probe.txt files is the last value of the wait loop of ra.sh (ra.sh waits for %d or fewer). ra.sh reads it, '
 795          'then sleeps %d s, then writes the time and the load of the probe line. So the value is from at least %d s '
 796          'before the time of the probe line, and the count at the first launch of part A is not recorded'
 797          % (span(rx_), len(X), span(ra_), len(A), limit, sleep_, sleep_))</pre></td><td valign="top">Check <code>runnable</code>, on the runnable tasks before a launch.<ul><li><code>rx_</code>: the number of runnable tasks in the launch line of each of the 9 bwx12 folders. <code>ra_</code>: the value <code>runnable=</code> of each of the 3 <code>probe.txt</code> files.</li><li><code>limit</code>: the number in the text <code>$r -le 2</code> of <code>ra.sh</code>, read from the script. ra.sh waits before its first process until at most 2 tasks are runnable.</li><li><code>sleep_</code>: the number in the first line of <code>ra.sh</code> that starts with <code>sleep</code> (5 s).</li><li>The check passes when the largest of the 12 values is not above <code>limit</code>. In this data the value is 1 in the 9 launch lines and 2 in the 3 <code>probe.txt</code> files.</li><li>The text of the check also says what the data do not show. ra.sh reads the value, then sleeps 5 s, then writes the probe line. So the number of runnable tasks at the first launch of part A is not recorded.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks 23 and 24: the rates against two other readers</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 798      # cross-check against the existing tools
 799      n_k, bad_k = 0, 0
 800      pairs = [(a['folder'], a['procs']) for a in A] + [
 801          (D['base']['A-1']['folder'], D['base']['A-1']['procs']),
 802          (os.path.join(S, 'base8000', 'partA-A1'), D['base']['A-2']['procs']),
 803          (os.path.join(S, 'base8000', 'partA-A3-onebuf500'), D['base']['A-3']['procs'])]
 804      for folder, mine in pairs:
 805          fd.OPENED.append(os.path.join(folder, 'threads120.csv'))
 806          theirs = fd.stat_k120.load(folder)
 807          assert len(theirs) == len(mine), folder
 808          for t, m in zip(theirs, mine):
 809              a = [(iv['agg'], iv['tmin'], iv['tmax'], iv['passes']) for iv in m['iv']]
 810              n_k += len(a)
 811              bad_k += a != [tuple(i) for i in t['iv']] or (t['binary'], t['kernel']) != (m['binary'], m['kernel'])
 812      chk('x-k120', bad_k == 0,
 813          'cross-check with stat_k120.py: %d interval rows (3 sessions of part A, A-1, and the copies of A-2 and A-3 '
 814          'under S/base8000, while this script reads the raw A1.csv and A3.csv) are equal in rate, per-thread minimum '
 815          'and maximum, and pass count: %s' % (n_k, yn(bad_k == 0)))</pre></td><td valign="top"><b>Check x-k120: a second reader of the part A rows.</b> stat_k120.py reads the interval rows a second time with its own parser [Ref5].<ul><li><code>pairs</code>: the 3 part A folders of the rerun, the folder of A-1, and two folders under <code>S/base8000</code>. These two hold copies of the A-2 and A-3 processes in the form of <code>threads120.csv</code>. The records of A-2 and A-3 come from the raw <code>A1.csv</code> and <code>A3.csv</code>.</li><li>The two readers must return the same number of processes per folder, or the <code>assert</code> stops the script.</li><li>For every interval row the check compares four values: <code>aggregate_GBps</code> (column 7), <code>per_thread_min_GBps</code> (column 8), <code>per_thread_max_GBps</code> (column 9), and the pass count (column 5 / column 3, rounded down). It also compares binary and kernel of each process.</li><li>The comparison is exact equality. No difference is allowed.</li><li><code>n_k</code> counts the compared interval rows (333 in this data). <code>bad_k</code> counts the processes with any difference. The check passes when <code>bad_k</code> is 0.</li><li>Line 805 adds each <code>threads120.csv</code> to <code>fd.OPENED</code>. The reason: stat_k120.py does not open it through <code>fd._open</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 816      n_x, bad_x, n_rerun = 0, 0, 0
 817      folders = [(x['folder'], {os.path.basename(x['csv'])[:-4]: x['sec']}) for x in X] + \
 818                [(v['folder'], v['secs']) for v in D['rx'].values()]
 819      for i, (folder, secs) in enumerate(folders):
 820          theirs = {(r['file'], r['round'], r['pos'], r['kernel']): r for r in fd.stat_bwx.interval_rows(folder)}
 821          for tag, sec in secs.items():
 822              for iv in fd.bwx_intervals(sec):
 823                  t = theirs[(tag + '.csv', iv['round'], iv['pos'], iv['kernel'])]
 824                  n_x += 1
 825                  n_rerun += i &lt; len(X)
 826                  bad_x += (abs(t['total'] - iv['total']) &gt; 1e-9 or abs(t['h0_sum'] - iv['mesh0']) &gt; 1e-9
 827                            or abs(t['h1_sum'] - iv['mesh1']) &gt; 1e-9 or t['is_64_56'] != iv['is_64_56']
 828                            or t['flagged'] != iv['flagged'])
 829      chk('x-bwx', bad_x == 0,
 830          'cross-check with stat_bwx.py: %d intervals of %d folders (the %d folders of parts L, C, I with %d intervals, '
 831          'and the %d csv files that section 7 lists from the %d earlier rx.sh and r0.sh folders with %d intervals) are '
 832          'equal in total, sum per mesh, the 64+56 test and the count of flagged rows: %s'
 833          % (n_x, len(folders), len(X), n_rerun, sum(len(v['secs']) for v in D['rx'].values()), len(D['rx']),
 834             n_x - n_rerun, yn(bad_x == 0)))</pre></td><td valign="top"><b>Check x-bwx: a second reader of the bwx rows.</b> stat_bwx.py computes the rate of every interval with its own parser [Ref6].<ul><li><code>folders</code>: the 9 rerun folders and the 11 folders of the earlier bwx12 and bwx11 data sets (<code>D['rx']</code>). The folders of the first runner bwx (<code>D['step']</code>) are not part of this check.</li><li>Every interval of the csv files that this script read from these 20 folders is looked up in the rows of stat_bwx.py by file name, round, position and kernel. This includes the intervals that the filter <code>POS01</code> kept out of the records. An interval that stat_bwx.py does not return ends the script with the Python error <code>KeyError</code> (line 823).</li><li>An interval counts as different when the total, the sum of mesh 0 or the sum of mesh 1 differs by more than 1e-9 GB/s (1 byte per second). It also counts when the 64+56 test or the number of flagged rows differs.</li><li>The two scripts add the per-thread rates in a different order. So a limit above 0 is needed. stat_bwx.py adds all T rows in file order. This script adds each mesh first and then the two sums. The largest difference in this data is about 5e-13 GB/s.</li><li><code>n_x</code> counts the compared intervals (297 in this data: 74 of the rerun and 223 earlier ones). The check passes when <code>bad_x</code> is 0.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks 25 to 27: earlier data, rx.sh, arguments of part A</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 835      # earlier intervals
 836      b = [r for r in recs if r['is_64_56'] is not None and r['dataset'] not in ('rerun-L', 'rerun-C', 'control-I')]
 837      okb = sum(1 for r in b if r['is_64_56'] and r['flagged'] == 0)
 838      errs = sum(v['stderr_bytes'] for v in D['rx'].values())
 839      rcs = sorted({v['launches'][t]['rc'] for v in D['rx'].values() for t in v['secs']})
 840      chk('earlier', okb == len(b) and errs == 0 and rcs == ['0'],
 841          'earlier bwx intervals used in sections 3 and 4: %d of %d are 64+56 intervals with 0 flagged T rows. The %d '
 842          'earlier rx.sh and r0.sh folders hold %d bytes of stderr.txt in total. The rc values of their %d processes used: %s'
 843          % (okb, len(b), len(D['rx']), errs, sum(len(v['secs']) for v in D['rx'].values()), '/'.join(rcs)))</pre></td><td valign="top">Check <code>earlier</code>, on the bwx records that do not belong to the rerun.<ul><li><code>b</code>: the records that have a 64+56 value and whose data set is not <code>rerun-L</code>, <code>rerun-C</code> or <code>control-I</code>. Only bwx records have this value. This data has 386 such records.</li><li><code>okb</code>: the number of them that pass the 64+56 test and have 0 flagged T rows.</li><li><code>errs</code>: the bytes of <code>stderr.txt</code> of the 11 folders of <code>D['rx']</code>, added. <code>rcs</code>: the distinct exit statuses of the 17 processes whose csv files this script reads. The <code>launches.txt</code> files of these folders hold 52 launch lines. The exit statuses of the other 35 processes are not tested here.</li><li>The check passes when <code>okb</code> equals the size of <code>b</code>, <code>errs</code> is 0, and <code>0</code> is the only exit status.</li><li>The exit status and <code>stderr.txt</code> of the folders of the first runner bwx are not tested here.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 844      # rx.sh: the local copy against the checksum that go.sh and go2.sh test on CRB (added last, so that the
 845      # numbers of the checks above stay as they were)
 846      rx = fd.sha256(os.path.join(fd.W15, 'rx.sh'))
 847      scripts = {n: fd._open(os.path.join(S, n)).read() for n in ('go.sh', 'go2.sh')}
 848      rxsha = {n: re.search(r'^RXSHA=([0-9a-f]{64})$', t, re.M)[1] for n, t in scripts.items()}
 849      stop_msg = 'rx.sh is not the script of 2026-11-15'
 850      stop_line = 'echo "$RXSHA  $RX" | sha256sum -c - &gt; /dev/null || fail "%s"' % stop_msg
 851      has_stop = all(stop_line in t and 'fail() { echo "FAILED: $1";' in t for t in scripts.values())
 852      n_failed = sum(len(D['logs'][n]['failed']) for n in ('go', 'go2'))</pre></td><td valign="top">Check <code>sha-rx</code>, on the runner script rx.sh. The comment says that it was added after the checks above. Their numbers then stay as they were.<ul><li><code>rx</code>: the sha256 of the local <code>rx.sh</code>. <code>rxsha</code>: the value of the line <code>RXSHA=</code> in the local <code>go.sh</code> and <code>go2.sh</code>.</li><li><code>has_stop</code>: both scripts hold the line that tests <code>rx.sh</code> against <code>RXSHA</code> with <code>sha256sum</code> and calls <code>fail</code> when the test fails. In both scripts <code>fail</code> prints a line that starts with <code>FAILED:</code>, prints a state line and ends the script with the exit status 1. <code>has_stop</code> also requires that both scripts hold the first part of that function, the <code>echo</code> of the <code>FAILED:</code> line. It does not test the rest of the function.</li><li><code>n_failed</code>: the number of <code>FAILED</code> lines in the two logs.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 853      # limit of this check: no record of the rerun holds a checksum of rx.sh, go.sh or go2.sh that was taken on CRB
 854      crb_texts = ['\n'.join(D['logs'][n]['lines']) for n in ('go', 'go2')] + \
 855                  [fd._open(a['probe']['path']).read() for a in A] + \
 856                  [fd._open(os.path.join(x['folder'], 'env.txt')).read() for x in X]
 857      local_sha = [rx] + [fd.sha256(os.path.join(S, n)) for n in ('go.sh', 'go2.sh')]
 858      assert not any(h in t for h in local_sha for t in crb_texts), 'a CRB record holds one of these checksums: revise the text'
 859      chk('sha-rx', set(rxsha.values()) == {rx} and has_stop and n_failed == 0,
 860          'sha256 of the local rx.sh (%s...) equal to RXSHA= in go.sh and go2.sh: %s. Both scripts hold the line that '
 861          'tests this value with sha256sum on CRB and stops with "FAILED: %s" when the copy on CRB differs: %s. Lines '
 862          'that start with FAILED in the two logs: %d. Limit: the %d logs, the %d probe.txt files and the %d env.txt '
 863          'files of the rerun hold no sha256 of rx.sh, go.sh or go2.sh. So this check uses the local copies of go.sh '
 864          'and go2.sh (check %d)'
 865          % (rx[:8], yn(set(rxsha.values()) == {rx}), stop_msg, yn(has_stop), n_failed, len(D['logs']), len(A), len(X),
 866             [c['key'] for c in C].index('sha-local') + 1))</pre></td><td valign="top"><ul><li><code>crb_texts</code>: the text of the 2 logs, of the 3 <code>probe.txt</code> files and of the 9 <code>env.txt</code> files of the rerun. <code>local_sha</code>: the sha256 values of the local rx.sh, go.sh and go2.sh. Since 2026-11-24 the value for go.sh is that of the edited file. It is not the value of the text that ran.</li><li>The <code>assert</code> in line 858 stops the script when one of these texts holds one of the three checksums.</li><li>The comment in line 853 names the limit of the check: no record of the rerun holds a checksum of rx.sh, go.sh or go2.sh that was taken on CRB. So the check uses the local copies of go.sh and go2.sh. The text of the check says this.</li><li>The record of the Claude Code session of 2026-11-17 holds a test of both driver scripts on CRB [Ref14]. This record lies outside the project folder, and this script does not read it. Two commands of that record wrote <code>local.sha</code> and <code>go2.sha</code> in the local folder <code>S</code> and copied the listed files to CRB. There they ran <code>sha256sum -c</code>, which compares each file with its sha256 in the list. The output shows <code>go.sh: OK</code> and <code>go2.sh: OK</code>.</li><li>The check passes when both <code>RXSHA</code> values equal <code>rx</code>, <code>has_stop</code> is true and <code>n_failed</code> is 0. Then neither driver script stopped at its test of rx.sh on CRB.</li><li>The text names the check <code>sha-local</code> by its number. Line 866 takes the number from the place of that check in the list.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 867      # arguments of part A against the test of 2026-11-13 (added after the checks above, so that their numbers stay)
 868      a1 = D['base']['A-1']['procs']
 869      hdr = lambda p: (p['binary'], p['kernel'], p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes'], p['round'])
 870      n_all = sum(len(a['procs']) for a in A)
 871      n_same = sum(hdr(p) == hdr(q) for a in A if len(a['procs']) == len(a1) for p, q in zip(a['procs'], a1))
 872      every = [p for a in A for p in a['procs']] + a1
 873      hv = sorted({(p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes']) for p in every})
 874      bw = sorted({p.get('bw_hdr') for p in every}, key=str)
 875      ra_lines = fd._open(os.path.join(S, 'ra.sh')).read().splitlines()
 876      rk_path = os.path.join(fd.K13, 'run_kernels.sh')
 877      rk_lines = fd._open(rk_path).read().splitlines()
 878      i_ra = next(i for i, l in enumerate(ra_lines) if l.startswith('one() {'))
 879      i_rk = next(i for i, l in enumerate(rk_lines) if l.startswith('one() {'))
 880      same_fn = ra_lines[i_ra:i_ra + 5] == rk_lines[i_rk:i_rk + 5] and ra_lines[i_ra + 4] == '}'
 881      opts = '--reps 3 --min-ms 500'
 882      has_opts = ra_lines[i_ra + 3].rstrip().endswith(opts + ' &gt;&gt; "$1"')
 883      rk_ok = p13['sha'].get('run_kernels.sh') == fd.sha256(rk_path)</pre></td><td valign="top">Check <code>A-args</code>, on the arguments of part A. It compares part A of the rerun with baseline A-1, the first test of 2026-11-13.<ul><li><code>hdr(p)</code>: six values of the <code>-- binary</code> header line of a process: binary, kernel, threads, cpus, bytes and round.</li><li><code>n_same</code>: the number of rerun processes whose six values equal those of the process at the same place in A-1. <code>n_all</code>: the number of all rerun processes.</li><li><code>hv</code>: the distinct values of threads, cpus and bytes over the processes of all 4 files. <code>bw</code>: the distinct ends of the <code># bandwidth:</code> line that the binary prints. This end holds threads, bytes per thread, <code>min_ms</code> and <code>thp</code>.</li><li><code>same_fn</code>: the 5 lines of the function <code>one</code> in <code>ra.sh</code> equal the 5 lines of <code>one</code> in <code>run_kernels.sh</code>. <code>one</code> starts one benchmark process.</li><li><code>has_opts</code>: the line of <code>one</code> that starts the binary ends with <code>--reps 3 --min-ms 500 &gt;&gt; "$1"</code>. So each process times 3 intervals of at least 500 ms each.</li><li><code>rk_ok</code>: the sha256 of the local <code>run_kernels.sh</code> equals the value in <code>probe.txt</code> of 2026-11-13.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 884      ok = n_same == n_all and len(hv) == 1 and len(bw) == 1 and bw[0] and same_fn and has_opts and rk_ok
 885      chk('A-args', ok,
 886          'part A, arguments. The "-- binary" header lines of the %d threads120.csv files of part A are equal to those '
 887          'of threads120.csv of 2026-11-13 in binary, kernel, threads, cpus, bytes and round: %d of %d lines (threads %s, '
 888          'cpus %s, bytes %s in every line). The header line that the binary prints ends with "%s" in all %d processes of '
 889          'the %d files. The function one() of ra.sh (lines %d to %d) is equal to lines %d to %d of run_kernels.sh: %s. '
 890          'Its process line ends with the options "%s": %s. sha256 of the local run_kernels.sh equal to line %d of '
 891          'probe.txt of 2026-11-13: %s'
 892          % (len(A), n_same, n_all, hv[0][0], hv[0][1], hv[0][2], bw[0], len(every), len(A) + 1, i_ra + 1, i_ra + 5,
 893             i_rk + 1, i_rk + 5, yn(same_fn), opts, yn(has_opts), p13['sha_line'].get('run_kernels.sh', 0), yn(rk_ok)))
 894      return C
 895
 896</pre></td><td valign="top">The check passes when all of these hold: <code>n_same</code> equals <code>n_all</code>, <code>hv</code> holds one value, <code>bw</code> holds one value that is not empty, and <code>same_fn</code>, <code>has_opts</code> and <code>rk_ok</code> are true. In this data all 72 header lines of the rerun equal those of A-1, with threads 120, cpus 0-119 and bytes 256M. The binary printed <code>min_ms=500 thp=madvise</code> in all 96 processes of the 4 files [Ref9]. The function then returns the list of checks.</td></tr>
<tr><td colspan="2"><b>Function <code>write_json</code>: writes facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 897  # ----------------------------------------------------------------------------- facts.json
 898
 899  def write_json(D, V, path):
 900      recs = D['recs']
 901      try6 = D['try6']
 902      meta = dict(
 903          title='Facts of the whole-chip read rerun at 7200 MT/s, CRB, 2026-11-17',
 904          written_by='S/build_facts.py (with S/facts_data.py, S/facts_text.py and S/facts_text4.py)',
 905          R=R, S=S,</pre></td><td valign="top"><code>main</code> calls this function with <code>D</code>, the verdicts <code>V</code> and the path <code>S/facts.json</code> (line 1038).<ul><li>Lines 902 to 1014 build the dictionary <code>meta</code>, the first of the three parts of the file.</li><li><code>meta</code> describes the run. It holds no interval record.</li><li>Its first entries are a title, the names of the scripts that wrote the file, and the folder paths <code>R</code> and <code>S</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 906          units=dict(GBps='GB/s with GB = 1e9 bytes', load1_at_launch='1-minute load average of Linux at the launch of '
 907                     'the process', gap_s='seconds between the end of the previous 120-thread process of the rerun and '
 908                     'this launch (1 s resolution). bwx12 records: the launch of their process. Part A: set on the '
 909                     'first process of a session only; null for processes 2 to 24, which ra.sh starts directly after '
 910                     'the previous part A process with no wait', passes='part A only: total_bytes / bytes_per_thread of the '
 911                     'interval row. For read, asmread, write and asmwrite this is the number of buffer passes of all '
 912                     'threads in the interval. For copy and asmcopy (%d records) it is 2 x that number, because the '
 913                     'binary counts read plus written bytes for these two kernels: the header line of each of their '
 914                     'processes in the csv says "copy counts read+write bytes"'
 915                     % len(fd.sel(recs, part='A', kernel={'copy', 'asmcopy'})), min_ms='shortest length of one interval, milliseconds',
 916                     speed_MTps='memory speed, million transfers per second'),
 917          rate_kinds=dict(part_A=fd.KIND_A, bwx=fd.KIND_X + '. This file rounds it to 0.001 GB/s. FACTS.md formats the '
 918                          'unrounded value'),</pre></td><td valign="top"><code>units</code> and <code>rate_kinds</code>: texts that explain fields of the records.<ul><li><code>GBps</code>: GB/s with GB = 1e9 bytes.</li><li><code>load1_at_launch</code>, <code>gap_s</code>, <code>passes</code>, <code>min_ms</code>, <code>speed_MTps</code>: one text each. The text of <code>passes</code> holds the number of records of the kernels <code>copy</code> and <code>asmcopy</code> (96 in this data), counted with <code>fd.sel</code>.</li><li><code>rate_kinds</code> repeats the two rate formulas. <code>fd.KIND_A</code> is the formula of part A: the column <code>aggregate_GBps</code> of the csv. The text adds how the binary computed this column: the sum of the bytes of all threads / the longest per-thread time [Ref13]. <code>fd.KIND_X</code> is the formula of the bwx runners: the sum over the T rows of bytes / elapsed_s / 1e9.</li><li>The text of the bwx formula adds that facts.json rounds this rate to 0.001 GB/s, and that FACTS.md formats the value that is not rounded.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 919          fields=dict(dataset='rerun-A, rerun-L, rerun-C, control-I, F72d12, or the label of an earlier row '
 920                      '(A-1..A-3, L-1..L-4, R0, R0b, X2d12, X1d10, X1d10b, BASEd10, B7a, B7b, C3a, C3b, B5a, B5b, '
 921                      'B5a-rev, B5b-rev)',
 922                      role='rerun, control, baseline, supporting, other binary, not a baseline, 10 modules',
 923                      round='part A: round of the script (1 or 2). In A-3 it is the repeat number. bwx: round of the '
 924                            'kernel sequence inside the process, from 0',
 925                      pos='bwx only: position of the kernel in the sequence of the process, from 0',
 926                      interval='number of the interval inside the process, from 0',
 927                      kernel_before='bwx: the kernel timed directly before in the same process. Part A: binary and '
 928                                    'kernel of the process that ran directly before in the same csv file. "none (first '
 929                                    'process of the file)" says nothing about the work before the file. Row A-3 holds 3 '
 930                                    'of the 12 processes of A3.csv: its first process is the first process of that file '
 931                                    '(the process directly before it is the last process of A2.csv: %s %s, tag %s, '
 932                                    'launched %s, arguments "%s"). Before each of the other two, a process ran that '
 933                                    'is not in the list ("not listed ...")'
 934                                    % (D['probe13']['a3_prev']['binary'], D['probe13']['a3_prev']['kernel'],
 935                                       D['probe13']['a3_prev']['tag'], iso(D['probe13']['a3_prev']['utc']),
 936                                       D['probe13']['a3_prev']['args']),
 937                      mesh0_GBps='bwx only: sum over the threads on CPUs 0-63',
 938                      mesh1_GBps='bwx only: sum over the threads on CPUs 64-127',
 939                      line='line number of the interval row in the file (part A) or of its "I" row (bwx)',
 940                      proc_key='one value per process',
 941                      session='rerun: session of go.sh (1 to 3); null for T72C4, which ran after session 3. '
 942                              'control-I: number of the control process (1 or 2); it is not a session',
 943                      start='bwx only: value of the option --start in the csv header (common or offset)',
 944                      start_state='start state of the step that holds the record: the session of part A, or the '
 945                                  'bwx12 process. In part A it describes the first process of the session',
 946                      per_thread_avg_GBps='part A only: column per_thread_avg_GBps of the csv, rounded to 0.01 GB/s '
 947                                          'by the binary',
 948                      q2_rows='verdicts.q2_rows: row_7200 and scope_8000 are the keys of a row. They are kept as in '
 949                              'the earlier builds of this file, so that a tool can find a row. row_7200_label and '
 950                              'scope_8000_label are the labels that FACTS.md prints. Where a key says "not pooled", '
 951                              'the label says "own row": the row is its own row in every range test of rule V1 point '
 952                              '2. Where a key says "(after oldread)", the label adds that the 8000 MT/s rows hold '
 953                              'asmread at position 1 and part C holds it at position 0'),</pre></td><td valign="top"><code>fields</code>: 15 texts for the reader of facts.json.<ul><li>14 texts explain one field of a record each. The text <code>q2_rows</code> explains the keys of a row in <code>verdicts.q2_rows</code>.</li><li>Only the text of <code>kernel_before</code> holds values from the data. It names the process that ran directly before the first process of baseline A-3 (<code>a3_prev</code> of <code>open_probe13</code>).</li><li>Three texts concern rate fields. <code>mesh0_GBps</code> is the sum over the threads on CPUs 0-63. <code>mesh1_GBps</code> is the sum over the threads on CPUs 64-127.</li><li>Both fields hold a value in bwx records only. In a part A record they are <code>null</code>.</li><li><code>per_thread_avg_GBps</code> holds a value in part A records only. It is the csv column of the same name, which the binary rounds to 0.01 GB/s.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 954          rerun=dict(boot_id=try6['boot'], modules=try6['dimm_sockets'], speed_MTps=try6['speed_MTps'],
 955                     memtotal_kB=try6['memtotal_kB'],
 956                     speed_proof='%s line %d, read at %s in the same boot. Not read during the rerun (no root)'
 957                                 % (rel(try6['path']), try6['speed_line'], iso(try6['utc'])),
 958                     go_start=iso(D['logs']['go']['states'][0]['utc']), go_end=iso(D['logs']['go']['states'][-1]['utc']),
 959                     go2_start=iso(D['logs']['go2']['states'][0]['utc']), go2_end=iso(D['logs']['go2']['states'][-1]['utc']),
 960                     kernel_log_read=False, root_used=False),
 961          launches=[dict(tag=e['tag'], part=e['part'], session=e['session'], script_start=iso(e['start']),
 962                         first_launch=iso(e['first']), end=iso(e['end']), gap_s=e['gap_s'], load1_at_first_launch=e['load1'],
 963                         start_state=e['state']) for e in D['events']],
 964          checks=[dict(key=c['key'], ok=c['ok'], text=c['text']) for c in D['checks']],
 965          counts=dict(intervals=len(recs), by_dataset={k: len(fd.sel(recs, dataset=k))
 966                                                       for k in dict.fromkeys(r['dataset'] for r in recs)}),
 967          rules='S/baselines-and-rules.txt (fixed before the run)',
 968          control_note='control-I was added after the first numbers of parts A, L and C were seen. It is not part of '
 969                       'the plan fixed before the run',</pre></td><td valign="top">More entries of <code>meta</code>:<ul><li><code>rerun</code>: boot id, module count, memory speed and MemTotal from <code>try6.txt</code>. <code>speed_proof</code> names the line of <code>try6.txt</code> that holds the memory speed, and it says that the speed was not read during the rerun. The entry also holds the times of the first and the last state line of go.sh and of go2.sh. Two fixed values say that the Linux kernel log was not read and that root rights were not used.</li><li><code>launches</code>: the 12 steps of the rerun in time order. Each has tag, part, session, three times, <code>gap_s</code>, the 1-minute load average at the first launch and the start state.</li><li><code>checks</code>: the 27 checks with key, pass flag and text.</li><li><code>counts</code>: the number of all records and the number per data set, in the order in which the data sets first appear. Records are counted here. No rate is added.</li><li><code>rules</code> and <code>control_note</code>: two fixed texts.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 970          F72d12_boot=dict(
 971              note='the folder of F72d12 holds no boot id. Its process lies between two readings of the same boot id',
 972              process=[iso(D['rx']['F72d12']['launches']['a6456']['utc']), iso(D['rx']['F72d12']['launches']['a6456']['rc_utc'])],
 973              boot_id_before=dict(file=rel(try6['path']), line=try6['boot_line'], utc=iso(try6['utc'])),
 974              boot_id_after=dict(file=rel(GO_LOG), line=D['logs']['go']['states'][0]['line'],
 975                                 utc=iso(D['logs']['go']['states'][0]['utc'])),
 976              boots_txt_row_0=dict(file=rel(try6['boots_path']), line=try6['boots_line'],
 977                                   first=iso(try6['boots_first']), last=iso(try6['boots_last'])),
 978              gaps_txt_row_0=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], first=iso(try6['first_log_utc']),
 979                                  last=iso(try6['last_log_utc']), hwerr=try6['gaps_hwerr'])),</pre></td><td valign="top"><code>F72d12_boot</code>: the reason why the records of F72d12 carry the boot of the rerun. The folder of F72d12 holds no boot id.<ul><li>The entry gives the launch time and the end time of its process.</li><li>It gives two readings of the same boot id: <code>try6.txt</code> before the process and the first state line of the go.sh log after it.</li><li>It also gives row 0 of <code>boots.txt</code> and of <code>gaps.txt</code> with their times.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 980          hardware_error_records=dict(
 981              journal=rel(D['probe13']['h5']),
 982              note='records of the journal of the 2026-11-09 boot inside the window of each process (launch line to rc '
 983                   'line of launches.txt). One record = one line "Hardware error from APEI ...". offset_s = journal time '
 984                   'minus launch time; both have a resolution of 1 s. kind: "inside" = the span offset_s - 1 to '
 985                   'offset_s + 1 lies inside a used interval (oldread at position 0 or asmread at position 1), '
 986                   '"possible" = the span and a used interval share a part, "outside" = neither',
 987              processes=[dict(dataset=h['dataset'], tag=h['tag'], file=rel(h['file']), launch=iso(h['launch']['utc']),
 988                              rc=iso(h['launch']['rc_utc']), n_records=len(h['records']),
 989                              records=[dict(journal_line=e['line'], utc=iso(e['utc']), record=e['id'],
 990                                            severity=e['severity'], offset_s=e['offset_s'], kind=e['kind'],
 991                                            interval=None if e['interval'] is None else dict(
 992                                                kernel=e['interval']['kernel'], round=e['interval']['round'],
 993                                                pos=e['interval']['pos'], line=e['interval']['line'],
 994                                                t_start_s=round(e['interval']['t_start'], 3),
 995                                                t_end_s=round(e['interval']['t_end'], 3),
 996                                                GBps=r3(e['interval']['total'])))
 997                                       for e in h['records']]) for h in D['hw']],
 998              F72d12=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], hwerr=try6['gaps_hwerr'],
 999                          first=iso(try6['first_log_utc']), last=iso(try6['last_log_utc'])),
1000              rerun='Insufficient data: the kernel log was not read during or after the rerun (no root)',
1001              all_intervals=hw_compare_json(D['hw_cmp'])),</pre></td><td valign="top"><code>hardware_error_records</code>: a copy of what <code>hw_records</code> and <code>hw_compare</code> built (<code>D['hw']</code>, <code>D['hw_cmp']</code>).<ul><li><code>processes</code>: one entry per process of L-1 to L-4, R0 and R0b, with the hardware error records of the journal inside its process window.</li><li>A record of the kind <code>inside</code> or <code>possible</code> carries its interval. Lines 994 to 996 round the start time and the end time of that interval to 0.001 s and its rate to 0.001 GB/s. The rate is <code>total</code>, the sum over the T rows.</li><li><code>F72d12</code>: the value <code>hwerr</code> of row 0 of <code>gaps.txt</code>. <code>rerun</code>: a fixed text that says that the Linux kernel log was not read for the rerun.</li><li><code>all_intervals</code>: the result of <code>hw_compare_json</code> (line 400).</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1002          firmware_settings=dict(
1003              note='no settings list was saved in the boot of the rerun (the settings tool needs root). File times are '
1004                   'those of the saved files. "line" of a reply is the line of the file that holds its answer',
1005              lists={k: dict(file=rel(v['path']), file_time=iso(v['mtime']), entries=v['n'], readable=v['readable'],
1006                             value_unavailable=v['unavailable'], vstore_error=v['store_error'], values=v['val']) for k, v in D['fw']['lists'].items()},
1007              base_and_revert_hold_the_same_entries=D['fw']['same_entries'],
1008              set_replies={k: dict(file=rel(v['path']), time_in_line_1=iso(v['when']) if v['when'] else None,
1009                                   file_time=iso(v['mtime']),
1010                                   replies=[dict(kind=x['kind'], name=x['name'], answer=x['answer'], modified=x['modified'],
1011                                                 line=x['line']) for x in v['replies']])
1012                           for k, v in D['fw']['sets'].items()},
1013              last_reading=dict(file=rel(D['fw']['final']['path']), file_time=iso(D['fw']['final']['mtime']),
1014                                text=D['fw']['final']['text'])))</pre></td><td valign="top"><code>firmware_settings</code>: a copy of what <code>open_fw</code> read. It holds the saved settings lists with file name and file time, the replies of the <code>set</code> calls of the firmware settings tool, and the last reading of the memory speed setting. A fixed note says that no settings list was saved in the boot of the rerun.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1015      # The file is written under another name and then renamed, so that a reader never sees a part of it.
1016      with open(path + '.tmp', 'w') as f:
1017          def r3all(o):
1018              if isinstance(o, float):
1019                  return r3(o)
1020              if isinstance(o, dict):
1021                  return {k: r3all(v) for k, v in o.items()}
1022              if isinstance(o, list):
1023                  return [r3all(v) for v in o]
1024              return o</pre></td><td valign="top">The file is first written under the name <code>facts.json.tmp</code>. <code>r3all</code> goes through nested dictionaries and lists and rounds every float (a floating-point number) to 3 decimal places with <code>r3</code> (line 38). It returns every other value unchanged.</td></tr>
<tr><td colspan="2"><b>Rounding of the rates in facts.json</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1025          f.write('{\n"meta": ' + json.dumps(meta, indent=1) + ',\n"verdicts": ' + json.dumps(r3all(V), indent=1)
1026                  + ',\n"intervals": [\n')
1027          rounded = lambda r: {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}
1028          f.write(',\n'.join(json.dumps(rounded(r), separators=(',', ':')) for r in recs))
1029          f.write('\n]\n}\n')
1030      os.replace(path + '.tmp', path)
1031
1032</pre></td><td valign="top"><ul><li>Line 1025 writes <code>meta</code> as it was built, then the verdicts after <code>r3all</code>. <code>meta</code> does not go through <code>r3all</code>.</li><li>Line 1027: <code>rounded</code> returns a copy of a record in which every float is rounded to 3 decimal places with the Python function <code>round</code>. For a rate this is 0.001 GB/s.</li><li>The float fields of a record are <code>GBps</code>, <code>mesh0_GBps</code>, <code>mesh1_GBps</code>, <code>per_thread_min_GBps</code>, <code>per_thread_max_GBps</code>, <code>per_thread_avg_GBps</code>, <code>load1_at_launch</code> and <code>gap_s</code>.</li><li>A part A rate has 2 decimal places in the csv. The rounding does not change it. A bwx rate changes. Example: the sum 462.30001702 GB/s of T72L1 is written as 462.3.</li><li>Line 1028 writes one line per record, in the order of <code>D['recs']</code>. The records in memory keep their values.</li><li><code>os.replace</code> then renames the file to <code>facts.json</code>. So a reader never sees a part of the file.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>main</code>: collect, check, render, write</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1033  def main():
1034      import facts_text
1035      D = collect()
1036      run_checks(D)
1037      V, text = facts_text.render(D)
1038      write_json(D, V, os.path.join(S, 'facts.json'))
1039      with open(os.path.join(S, 'FACTS.md.tmp'), 'w') as f:
1040          f.write(text)
1041      os.replace(os.path.join(S, 'FACTS.md.tmp'), os.path.join(S, 'FACTS.md'))</pre></td><td valign="top">The entry point of the script. <code>facts_text.py</code> is imported here, inside the function.<ul><li><code>collect</code> reads the result files and builds the records in <code>D</code>. <code>run_checks</code> appends the 27 checks.</li><li><code>facts_text.render</code> computes the statistics from the field <code>GBps</code> of the records. It returns the verdicts <code>V</code> and the text of FACTS.md [Ref2]. The lowest, the median and the highest rate of each kernel and the percent values are computed there, not in this file.</li><li><b>A failed check stops the script inside this call.</b> <code>render</code> calls <code>section4</code> of <code>facts_text4.py</code>. That function ends the script with an error message unless every check has <code>ok</code> true. Then no output file is written, and the exit status is 1.</li><li>A test that wrote no file confirmed this. With one check set to failed, <code>render</code> ended the script with the message <code>facts_text.py: the data do not show the pattern of a sentence: all integrity checks pass</code>.</li><li><code>write_json</code> writes <code>S/facts.json</code>.</li><li>The text is written to <code>S/FACTS.md.tmp</code>. Then the file is renamed to <code>S/FACTS.md</code>.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1042      if '--print' in sys.argv:
1043          print(text)
1044      bad = [c for c in D['checks'] if not c['ok']]
1045      print('checks: %d, failed: %d' % (len(D['checks']), len(bad)))
1046      for c in bad:
1047          print('  FAILED', c['key'], c['text'])
1048      print('intervals in facts.json: %d' % len(D['recs']))
1049      print('Q1:', V['q1'])
1050      print('Q2:', V['q2'])
1051      if bad:
1052          sys.exit(1)
1053
1054</pre></td><td valign="top"><ul><li>With the argument <code>--print</code> the script prints the text of FACTS.md.</li><li><code>bad</code> is the list of the checks with <code>ok</code> false. The script prints the number of checks and the number of failed checks, then one line <code>FAILED</code> with key and text per failed check.</li><li>It prints the number of records and the verdicts <code>Q1</code> and <code>Q2</code>.</li><li>Line 1052 gives the exit status 1 when <code>bad</code> is not empty.</li><li>In the present code these lines are reached only when all checks passed. The reason: <code>render</code> stops the script before them when a check failed (see the row above). So <code>bad</code> is empty here, no <code>FAILED</code> line is printed, and the script ends with the exit status 0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">1055  if __name__ == '__main__':
1056      main()</pre></td><td valign="top">When the file is run as a script, Python calls <code>main</code>.</td></tr>
</table>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: `read_k120` (lines 264 to 304) reads the interval rows of part A. `read_bwx` (lines 313 to 353) stores the T rows by round, position and kernel. `bwx_intervals` (lines 356 to 383) adds the T rows of each interval. `base_record` (lines 421 to 433) lists the keys of a record. Line 271 of `read_k120` matches the `-- binary` header line with the pattern `HDR` of stat_k120.py.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`: `analyse` (line 283), `compare` (line 333) and `render` (line 341) compute the pairs, ranges, medians and percent values from the records. `g` (line 46) formats a rate to 0.01 GB/s, rounded half up. Lines 1474 and 1475 compare `fd.OPENED` with the file list of FACTS.md. Line 186 of `register` adds `FINDINGS.md` to that file list. Lines 380 to 388 read line 2 of the rules file: `render` stops when the writing time in that line is not before the first state line of the go.sh log.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`: Line 18 says that every baseline ran in the boot of 2026-11-09 with 12 memory modules at 8000 MT/s. The fixed list of the 8000 MT/s baselines (lines 21 to 43, asmread in place of the new read kernel in line 36) and rule V1 (lines 70 to 82). Lines 40 and 78 name the kernel `read` of the runner bwx as the nearest data for the new read kernel of part C.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The word list (lines 38 to 89), the questions Q1 and Q2 (lines 95 and 96), and the 27 check lines of section 1.4 (lines 213 to 239).
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: `load` (lines 24 to 44) reads the interval rows of a `threads120.csv` a second time.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py`: `read_csv` (lines 38 to 58) computes bytes / elapsed_s / 1e9 for each T row (line 54). `interval_rows` (lines 61 to 81) computes total, sums per mesh, the 64+56 test and the flagged count a second time.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z/threads120.csv`: Lines 1 to 7: the header line of ra.sh, the `# bandwidth:` line with the formula of `aggregate_GBps`, the column names, 3 interval rows and the `best` row.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/a6456.csv`: Lines 1 to 6: the header lines with the column names of the I, T, P and C rows. Line 1 gives the formula of `aggregate_GBps`: sum(bytes) / max(per-thread elapsed_s). Line 128: the I row of round 0, position 0 (oldread). Lines 129 to 248: its 120 T rows.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: `meta.counts`: 793 records and the count per data set. `meta.checks`: 27 checks, all with `ok` true (file written 2026-11-17 at 20:55 local time, which is 2026-11-18 04:55 UTC).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: Line 17 writes a state line. Lines 40 to 46 give the order of the steps. `ra.sh` (same folder, lines 30 to 36 and 49) writes probe.txt. `rx.sh` (folder `w120-2026-11-15`, lines 10, 16 and 20) writes env.txt and launches.txt.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`: `section4` (from line 24) writes sections 4 to 6 of FACTS.md. Line 1461 ends the script unless every check passed. It uses `need` of `facts_text.py` (line 36), which raises `SystemExit` with a message. `render` calls `section4` at line 1464 of `facts_text.py`. `section4` also computes ranges from the records. For this it calls `rng` of `facts_data.py` (lowest value, highest value and median of a list of records) and `compare` of `facts_text.py`, for example at lines 51 and 81.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: `read_smaps` (lines 1515 to 1542) takes `kB_total` from the line `Size:` and `kB_huge` from the line `AnonHugePages:` of the entry of the buffer in `/proc/self/smaps`. `read_vmstat` (lines 1545 to 1560) reads four counters of `/proc/vmstat`, among them `thp_fault_fallback`. The comment at line 1544 says that they count for the whole system.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`: Lines 427 to 446 (source of bw_old) print an interval row. `aggregate_GBps` = total bytes / longest per-thread time / 1e9, printed with 2 decimal places. `per_thread_avg_GBps` = the sum of the per-thread rates bytes / elapsed_s / 1e9, divided by the thread count. `bandwidth.c` of the same folder (source of bw_new) holds the same code in lines 584 to 603. This local text of `bandwidth.c` has the sha256 `f1985072...`. `probe.txt` of the build-only run of 18:32:18 UTC on 2026-11-13 (`R/kernels-20261113T183218Z`, line 15) holds this value. `probe.txt` of the timed run of 18:12:22 UTC (`R/kernels-20261113T181222Z`, line 15) holds another sha256 for `bandwidth.c` (`c1406e02...`). All three `probe.txt` records of that day hold the same sha256 for the binary bw_new (`fd7c14df...`). ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text. The record of the Claude Code session of that day holds the edit (`/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000). With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- [Ref14] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: The record of the Claude Code session of 2026-11-17, one JSON record per line. It lies outside the project folder. Line 313 holds the command that started go.sh on CRB, and line 365 the command that started go2.sh. Both have the form `nohup setsid SCRIPT > $L 2>&1 < /dev/null &`, where `L` is the path of the log. The part `> $L 2>&1` sends the standard output and the error output of the script into the log. Line 309 holds the command line that wrote `local.sha`, copied go.sh, ra.sh, the three spec files and the list to CRB, and ran `sha256sum -c local.sha` there. Line 353 holds the same steps for go2.sh and `go2.sha`.
- [Ref15] External source: Linux kernel documentation, page "Transparent Hugepage Support" (docs.kernel.org/admin-guide/mm/transhuge.html), section "Monitoring usage". It lists `thp_fault_fallback` among the counters of `/proc/vmstat`. It says that the counter is incremented if a page fault fails to allocate or charge a huge page and instead falls back to using small pages.
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: The header text (lines 5 to 12) names facts.json as the input. It says that the function `val` sums the thread rows of the raw csv for the last digit of a bwx rate, and that the computed values are compared with FACTS.md.
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24`: tests of 2026-11-24 for the edit of line 20 of go.sh. The files that end with `.out` hold their output. `go.sh.as-run-2026-11-17` is a copy of go.sh from before the edit. `check_line20.py` reads the local go.sh and puts the old line back in a copy of the text in memory. It does not change the file. That text has the sha256 that `local.sha` lists for go.sh. `check_facts_build.py` runs this script in a copy of `S`. With the edited go.sh the build ends with status 1 and writes no file. With the old line 20 it passes.
