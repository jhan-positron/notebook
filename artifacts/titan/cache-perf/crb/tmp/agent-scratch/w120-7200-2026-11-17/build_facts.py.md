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

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/build_facts.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1056 lines, 68288 bytes, sha256 `38637021b501e44eb942e6ca1aa9ff118d4a02ee0d4f8859858bdfcb9a1766c1`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### File comment: inputs, outputs and usage (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. This file is the entry point of the build of the facts sheet. |
| 2 | `"""build_facts.py - builds the facts sheet of the 7200 MT/s whole-chip rerun of 2026-11-17.` | Comment: starts the file comment. It is a text between two `"""` marks, and Python does not run it. This line says what the script does: it builds the facts sheet of the whole-chip rerun at 7200 MT/s of 2026-11-17. |
| 4 | `Reads:  raw result files under R, the converted baseline copies under S/base8000, the scripts in S,` | Comment: what the script reads. First part of the list: the raw result files under `R`, the converted copies of two baseline files under `S/base8000`, and the scripts in `S`. `R` is the results folder. `S` is the folder of this script. |
| 5 | `        and three records outside R (the DIMM report, FINDINGS.md of 2026-11-15, run_kernels.sh of 2026-11-13).` | Comment: the list goes on with three records outside `R`: the DIMM report, `FINDINGS.md` of 2026-11-15 and `run_kernels.sh` of 2026-11-13. |
| 6 | `Writes: S/facts.json and S/FACTS.md. It changes no other file.` | Comment: the script writes two files, `S/facts.json` and `S/FACTS.md`. It changes no other file. |
| 8 | `Every number in FACTS.md is formatted by this script from a value that it read or computed.` | Comment: every number in `FACTS.md` is formatted by this script from a value that it read or computed. |
| 9 | `No measured number is typed by hand in the text templates of facts_text.py and facts_text4.py.` | Comment: no measured number is typed by hand in the text templates of `facts_text.py` and `facts_text4.py`. This is not true for every template: the file list in `facts_text.py` holds the fixed text `ended 8 s before the first process of row A-2`. |
| 11 | `Usage: python3 build_facts.py            write both files, print the checks and the verdicts` | Comment: the usage. Without an argument the script writes both files and prints the checks and the verdicts. The verdicts are the answer sentences to the two questions of the rerun. |
| 12 | `       python3 build_facts.py --print    also print FACTS.md` | Comment: with the argument `--print` the script also prints the text of `FACTS.md`. |
| 14 | `Files: facts_data.py (parsers, range functions), build_facts.py (records, integrity checks, facts.json),` | Comment: the files of the build. `facts_data.py` holds the parsers and the range functions. `build_facts.py` builds the records, runs the integrity checks and writes `facts.json`. |
| 15 | `       facts_text.py and facts_text4.py (statistics, verdicts, text of FACTS.md).` | Comment: `facts_text.py` and `facts_text4.py` compute the statistics and the verdicts and write the text of `FACTS.md`. |
| 16 | `"""` | Ends the file comment. |

### Imports and constants (lines 17 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `import glob` | Loads the Python module `glob`. The function `collect` uses it to list the csv files of a result folder (line 78). |
| 18 | `import json` | Loads the Python module `json`. The script uses it to read the saved firmware settings (line 454) and to write `facts.json` (line 1025). |
| 19 | `import os` | Loads the Python module `os`. The script uses it for path functions, file sizes and file times. |
| 20 | `import re` | Loads the Python module `re`. It gives regular expressions. A regular expression is a text pattern. The parts of a pattern in round brackets are called groups. Their text is taken out as values, counted from group 1. |
| 21 | `import sys` | Loads the Python module `sys`. The script uses it for the setting of line 23, for its arguments (line 1042) and for `sys.exit` (line 1052). |
| 23 | `sys.dont_write_bytecode = True` | Python writes no compiled copy (`.pyc` file) of the modules that are imported after this line. |
| 25 | `import facts_data as fd                     # noqa: E402` | Loads the module `facts_data.py` of the same folder under the short name `fd`. It holds the parsers of the raw files and small helper functions. The mark `# noqa: E402` tells a style checker not to report that this import stands below other code. |
| 26 | `from facts_data import R, S, rel            # noqa: E402` | Takes three names from `facts_data.py` for direct use. `R`: the results folder. `S`: the folder of the scripts. `rel`: a function that shortens a path to the form `R/...` or `S/...`. |
| 28 | `GO_LOG = os.path.join(R, 'go-T72-20261117T221209Z.log')` | `GO_LOG`: the path of the log of `go.sh` in `R`. The log holds the standard output and the error output of that script [Ref14]. |
| 29 | `GO2_LOG = os.path.join(R, 'go2-T72-20261117T222335Z.log')` | `GO2_LOG`: the path of the log of `go2.sh` in `R`, of the same kind [Ref14]. |
| 30 | `POS01 = {('oldread', 0), ('asmread', 1)}    # the positions of part L: oldread first, asmread directly after it` | `POS01`: a set of two pairs of kernel and position: `oldread` at position 0 and `asmread` at position 1. The comment says that these are the positions of part L: `oldread` first, `asmread` directly after it. `add_bwx` (line 142) uses the set as a filter for 8 earlier data sets. |
| 31 | `READ3 = ('oldread', 'read', 'asmread')` | `READ3`: the three kernel names `oldread`, `read` and `asmread`. Line 280 uses it as a filter for the data sets of the first runner `bwx`. |

### Functions `iso`, `r3` and `boot_of` (lines 34 to 49)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `def iso(t):` | Starts the function `iso`. It formats a date and time as text. |
| 35 | `    return t.strftime('%Y-%m-%dT%H:%M:%SZ')` | Returns the text in the form `YYYY-MM-DDTHH:MM:SSZ`, for example `2026-11-17T22:12:14Z`. In the file `facts.json` this text is the field `launch_utc` of the first record. The letter `T` stands between the date and the time of day. The letter `Z` at the end stands for UTC. The function adds it as fixed text. |
| 38 | `def r3(x):` | Starts the function `r3`. It rounds a number to 3 decimal places. Two functions call it: `hw_compare_json` (line 400) and `write_json` (line 899). The records in memory are not rounded. |
| 39 | `    return None if x is None else round(x, 3)` | `None` stays `None`. Every other value is rounded with the Python function `round`. For a rate that is a step of 0.001 GB/s. |
| 42 | `# ----------------------------------------------------------------------------- collection` | Comment: a divider line. The block below collects the data. |
| 44 | `def boot_of(table, t):` | Starts the function `boot_of`. It finds the boot that ran at the time `t`. `table` is the boot table of the DIMM report, as `fd.read_boot_table` returns it. |
| 45 | `    """Boot of the DIMM report table that contains time t."""` | Comment: the function returns the boot of the DIMM report table that contains the time `t`. |
| 46 | `    cand = [b for b in table['boots'] if b['start'] <= t]` | `cand`: the boots whose Linux start time is not after `t`. `table['boots']` is sorted by start time. |
| 47 | `    return cand[-1]` | Returns the last of them. The script takes this boot as the boot that ran at the time `t`. |

### Function `collect`: the machine records and the nested function `state_of` (lines 50 to 65)

| Line | Source | Explanation |
|---:|---|---|
| 50 | `def collect():` | Starts the function `collect`. It reads all input files and builds the interval records. `main` calls it first (line 1035). |
| 51 | `    D = dict(recs=[], checks=[])` | `D`: the dictionary that the function returns at the end (line 290). Every later step reads it. `recs` will hold all interval records. `checks` stays empty until `run_checks` (line 653) fills it. |
| 52 | `    recs = D['recs']` | `recs`: a short name for the list `D['recs']`. |
| 53 | `    try6 = D['try6'] = fd.read_try6()` | `try6`: the values of `try6.txt`, the record of the boot of the rerun: time, boot id, `MemTotal`, the number of DIMM sockets and the memory speed. `fd.read_try6` also reads the first and the last time of row 0 of `boots.txt` and of `gaps.txt`. It stops the script when row 0 of `boots.txt` does not hold the boot id of `try6.txt`. |
| 54 | `    bt = D['boot_table'] = fd.read_boot_table()` | `bt`: the boot table of the DIMM report: the boots with start time and module count, and the time until which the memory speed setting was 8000 MT/s. |
| 55 | `    logs = D['logs'] = dict(go=fd.read_log(GO_LOG), go2=fd.read_log(GO2_LOG))` | `logs`: the two driver logs, read by `fd.read_log`. Each entry holds the lines of the log, with the state lines as parsed values. The key `go` is the log of `go.sh`. The key `go2` is the log of `go2.sh`. |
| 56 | `    boot72 = dict(speed_MTps=try6['speed_MTps'], modules=try6['dimm_sockets'], boot=try6['boot'])` | `boot72`: three fields that every record of the rerun gets. All three are read from `try6.txt`. `speed_MTps` is 7200, the speed in the line of that file that ends with `Configured Memory Speed: 7200 MT/s`. `modules` is 12, the number in the Linux message `This system has 12 DIMM sockets`. `boot` is the boot id. The file also holds a line `modules=24`. No record field comes from that line. The result folders of the rerun are not read for these fields. Check `boot` (line 679) tests that every state line of the two logs and the 3 `probe.txt` files of part A hold this boot id. |
| 58 | `    def state_of(folder):` | Starts the nested function `state_of`. It returns the fields `speed_MTps`, `modules` and `boot` for a result folder of an earlier run. |
| 59 | `        """speed, modules and boot label of an earlier result folder, from the boot table of the DIMM report."""` | Comment: the speed, the module count and the boot label of an earlier result folder, from the boot table of the DIMM report. |
| 60 | `        t = fd.folder_date(folder)` | `t`: the time in the folder name. |
| 61 | `        assert t < bt['until']['utc'], folder` | The `assert` stops the script when `t` is not before the time until which the memory speed setting was 8000 MT/s. That time stands in the row `Memory speed until` of the DIMM report. The facts sheet `FACTS.md` says that the DIMM report gives 8000 MT/s as the setting until 2026-11-17 19:43. The error of the `assert` shows the folder. |
| 62 | `        b = boot_of(bt, t)` | `b`: the boot of the DIMM report that ran at the time `t` (line 44). |
| 63 | `        return dict(speed_MTps=bt['until']['speed'], modules=b['modules'],` | Returns the three fields. `speed_MTps`: the speed of that row of the report, 8000 MT/s. `modules`: the module count of the boot `b`. |
| 64 | `                    boot='boot %d of the DIMM report (Linux start %s UTC)' % (b['no'], b['start'].strftime('%Y-%m-%d %H:%M')))` | Ends the dictionary of line 63. `boot`: a label with the boot number and the start time of Linux, in the form `boot N of the DIMM report (Linux start YYYY-MM-DD HH:MM UTC)`. Example from the records of `facts.json`: `boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC)` [Ref9]. |

### `collect`: the files of the rerun (part A, then parts L, C and control I) (lines 66 to 87)

| Line | Source | Explanation |
|---:|---|---|
| 66 | `    # ---- the rerun: part A` | Comment: the rerun, part A. |
| 67 | `    A = D['A'] = []` | `A`: the list of the part A folders of the rerun, also kept as `D['A']`. |
| 68 | `    for tag, s in fd.RERUN_A:` | Loop over the 3 entries of `fd.RERUN_A`: the tags `T72A1`, `T72A2`, `T72A3` with the session numbers 1, 2, 3. |
| 69 | `        folder = fd.find('k120-' + tag)` | `fd.find` returns the one folder in `R` whose name starts with `k120-`, the tag and `-2026`. The script stops when it does not find exactly one folder. |
| 70 | `        A.append(dict(part='A', tag=tag, session=s, folder=folder, csv=os.path.join(folder, 'threads120.csv'),` | Adds one entry per session: the part, the tag, the session number, the folder and the path of `threads120.csv`. |
| 71 | `                      probe=fd.read_probe(os.path.join(folder, 'probe.txt')),` | `probe`: the values of `probe.txt` of the folder, read by `fd.read_probe`: times, load averages, logins, boot id, `MemTotal`, runnable tasks and the sha256 values of `bw_old`, `bw_new` and `ra.sh`. |
| 72 | `                      procs=fd.read_k120(os.path.join(folder, 'threads120.csv'))))` | Ends the entry of line 70. `procs`: the processes of `threads120.csv` in file order, each with its interval rows in `iv`. An interval row is a row whose column 4 (`rep`) is a number. So the `best` row and the column header row are left out [Ref1]. No rate is computed in these lines. |
| 73 | `    # ---- the rerun: parts L, C and the control I (runner bwx12)` | Comment: the rerun, parts L and C and the control I, all with the runner `bwx12`. |
| 74 | `    X = D['X'] = []` | `X`: the list of the bwx12 folders of the rerun, also kept as `D['X']`. |
| 75 | `    for part, items in (('L', fd.RERUN_L), ('C', fd.RERUN_C), ('I', fd.RERUN_I)):` | Loop over the three bwx12 parts with their lists of tags: 3 tags of part L, 4 of part C and 2 of control I. These are 9 tags: `T72L1` to `T72L3`, `T72C1` to `T72C4`, `T72I1` and `T72I2`. |
| 76 | `        for it in items:` | Loop over the entries of one list. `it[0]` is the tag and `it[1]` is the session number. |
| 77 | `            folder = fd.find('w120-' + it[0])` | `fd.find` returns the one folder in `R` whose name starts with `w120-`, the tag and `-2026`. |
| 78 | `            csvs = sorted(glob.glob(os.path.join(folder, '*.csv')))` | `csvs`: the csv files of the folder, sorted by name. |
| 79 | `            assert len(csvs) == 1, csvs` | The folder must hold exactly one csv file. If not, the `assert` stops the script and shows the list. |
| 80 | `            secs = fd.read_bwx(csvs[0])` | `secs`: the sections of the csv, read by `fd.read_bwx`. A section holds the rows of one process, stored by kind: the T rows, the I rows, the P rows and the number of C rows. |
| 81 | `            assert len(secs) == 1` | The file must hold exactly one section, which is one process. If not, the `assert` stops the script. |
| 82 | `            err = os.path.join(folder, 'stderr.txt')` | `err`: the path of `stderr.txt` of the folder. |
| 83 | `            fd.OPENED.append(err)` | Adds this path to the list `fd.OPENED` directly. The file is not read. Only its size is taken (line 86). `facts_text.py` compares the list `fd.OPENED` with the file list of `FACTS.md` [Ref2]. |
| 84 | `            X.append(dict(part=part, tag=it[0], session=it[1], spec=it[2] if part == 'C' else 'like', folder=folder,` | Adds one entry per bwx12 folder. `session`: the second value of the entry. It is `None` for `T72C4`. For control I it is the number of the control process (1 or 2). `spec`: the name of the spec file: `cfwd` or `crev` for part C, and `like` for part L and control I. |
| 85 | `                          csv=csvs[0], sec=secs[0], ivs=fd.bwx_intervals(secs[0]), env=fd.read_env(folder),` | Continues the entry of line 84. `sec`: the one section of the csv. Only its T rows enter the rate. `ivs`: one entry per interval from `fd.bwx_intervals`. Its rate `total` is the sum over the T rows of `bytes / elapsed_s / 1e9` [Ref1]. `env`: the values of `env.txt`. |
| 86 | `                          launches=fd.read_launches(folder), stderr_bytes=os.path.getsize(err)))` | Ends the entry of line 84. `launches`: the `launch` lines of `launches.txt`, each with the values of its `rc` line. `stderr_bytes`: the size of `stderr.txt` in bytes. |

### `collect`: the steps of the rerun in time order, `gap_s` and the start state (lines 88 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 88 | `    # ---- order in time, gap since the previous 120-thread process, start state` | Comment: the order in time, the gap from the previous 120-thread process, and the start state. |
| 89 | `    ev = []` | `ev`: the list of the steps of the rerun. One step is one session of part A or one bwx12 process. With 3 sessions and 9 bwx12 processes the list holds 12 steps. |
| 90 | `    for a in A:` | Loop over the 3 sessions of part A. |
| 91 | `        ev.append(dict(part='A', tag=a['tag'], session=a['session'], obj=a, start=fd.folder_date(a['folder']),` | Adds the step of a session. `obj`: the entry of `A`. `start`: the time in the folder name. `ra.sh` creates the folder at this time. |
| 92 | `                       first=fd.clock(a['folder'], a['procs'][0]['utc']),` | `first`: the launch time of the first process, from the first `-- binary` header line of `threads120.csv`. `fd.clock` joins the time of day of that line with the date of the folder name. |
| 93 | `                       last=fd.clock(a['folder'], a['procs'][-1]['utc']), end=a['probe']['utc_after'],` | `last`: the launch time of the last process. `end`: the time of the `load_after` line, which `ra.sh` writes into `probe.txt` after the last process [Ref10]. |
| 94 | `                       load1=a['procs'][0]['load1']))` | Ends the entry of line 91. `load1`: the 1-minute load average of the first header line. |
| 95 | `    for x in X:` | Loop over the 9 bwx12 folders. |
| 96 | `        la = x['launches'][0]` | `la`: the first `launch` line of `launches.txt`. Check `rc` (line 713) tests that the file holds exactly one. |
| 97 | `        ev.append(dict(part=x['part'], tag=x['tag'], session=x['session'], obj=x, start=fd.folder_date(x['folder']),` | Adds the step of a bwx12 process. `obj`: the entry of `X`. `start`: the time in the folder name. |
| 98 | `                       first=la['utc'], last=la['utc'], end=la['rc_utc'], load1=la['load1']))` | Ends the entry of line 97. `first` and `last`: both the time of the `launch` line. `end`: the time of the `rc` line. `load1`: the 1-minute load average of the `launch` line. All these times are whole seconds. |
| 99 | `    ev.sort(key=lambda e: e['first'])` | Sorts the steps by `first`, the time of their first launch. |
| 100 | `    go_start = logs['go']['states'][0]['utc']` | `go_start`: the time of the first state line of the log of `go.sh`. |
| 101 | `    prev = None` | `prev`: the step before the present one. It is `None` at the first step. |
| 102 | `    for e in ev:` | Loop over the steps in time order. |
| 103 | `        e['prev'] = prev` | Stores the step before in the step. |
| 104 | `        e['gap_s'] = None if prev is None else (e['first'] - prev['end']).total_seconds()` | `gap_s`: `first` of this step minus `end` of the step before, in seconds. The first step has `None`. In the build of 2026-11-17 the gap is 5 s for the 9 steps that follow `T72A1`, up to `T72C4`. It is 287 s for `T72I1` and 265 s for `T72I2`. `facts.json` lists these values under `meta.launches` [Ref9]. |
| 105 | `        if prev is None:` | Form 1 of the start state: the first step of the rerun. |
| 106 | `            e['state'] = ('started from an idle machine, %.0f s after go.sh started (1-minute load average %.2f)'` | `state`: a sentence on the start of the step. For the first step it reads `started from an idle machine`, then the seconds from the start of `go.sh` and the 1-minute load average of the launch. The words `idle machine` are fixed text. These lines do not test the load. |
| 107 | `                          % ((e['first'] - go_start).total_seconds(), e['load1']))` | Continues the statement of line 106: the two values of the sentence. The seconds are `first` minus `go_start`, printed without decimals. The load average is printed with 2 decimals. |
| 108 | `        elif e['part'] == 'I':` | Form 2: a step of control I. |
| 109 | `            e['state'] = ('started from an idle machine (1-minute load average %.2f), %.0f s after the 120-thread '` | The sentence reads `started from an idle machine`, with the 1-minute load average of the launch, then `gap_s` and the tag of the step before. The words `idle machine` are fixed text here too. The driver `go2.sh` waits for a 1-minute load average below 1.0 before each step of control I. |
| 110 | `                          'bwx12 process %s' % (e['load1'], e['gap_s'], prev['tag']))` | Continues the statement of line 109: the end of the text and its three values. |
| 111 | `        elif prev['part'] == 'A':` | Form 3: a step that follows a session of part A. |
| 112 | `            e['state'] = 'started %.0f s after the last 120-thread process of part A (%s)' % (e['gap_s'], prev['tag'])` | The sentence gives `gap_s` and the tag of that session. |
| 113 | `        else:` | Form 4: a step that follows a bwx12 process. |
| 114 | `            e['state'] = 'started %.0f s after the 120-thread bwx12 process %s' % (e['gap_s'], prev['tag'])` | The sentence gives `gap_s` and the tag of that process. Example from `meta.launches` of `facts.json`: `started 5 s after the 120-thread bwx12 process T72L1` [Ref9]. |
| 115 | `        prev = e` | This step becomes the step before for the next turn of the loop. |
| 116 | `    D['events'] = ev` | `D['events']` keeps the list of steps. |
| 117 | `    evd = {e['tag']: e for e in ev}` | `evd`: a dictionary that finds a step by its tag. |

### `collect`: nested function `add_k120`, the records of part A (lines 119 to 141)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `    def add_k120(procs, folder, order_known=True, **common):` | Starts the nested function `add_k120`. It appends one record per interval row of processes of `bw_old` and `bw_new`. `procs`: a list of processes from `fd.read_k120`. `order_known`: false when the list holds only a part of the processes of the file. `**common`: fields that every record of the call gets. |
| 120 | `        for n, p in enumerate(procs, 1):` | Loop over the processes. `n` numbers the processes of the list from 1. |
| 121 | `            before = 'none (first process of the file)'` | `before` becomes the field `kernel_before`. The first process of the list gets the text `none (first process of the file)`. |
| 122 | `            if n > 1:` | Tests for a later process of the list. |
| 123 | `                before = '%s %s' % (procs[n - 2]['binary'], procs[n - 2]['kernel'])` | It gets the binary and the kernel of the process before it in the list, for example `bw_old read`. |
| 124 | `            if not order_known:` | The case `order_known=False`. It is used for baseline A-3 only (line 198). |
| 125 | `                # The list holds only a part of the processes of the file. A process whose header line is line 1` | Comment: the list holds only a part of the processes of the file. The sentence on a process whose header line is the first line of the file goes on in line 126. |
| 126 | `                # of the file is the first process of the file. Before every other one, processes ran that are` | Comment: such a process is the first process of the file. Before every other process of the list, processes ran that are not in the list (the sentence ends in line 127). |
| 127 | `                # not in the list.` | Comment: the last words of the sentence of line 126. |
| 128 | `                before = ('none (first process of the file)' if p['hdr_line'] == 1 else` | A process whose header line is the first line of the file gets `none (first process of the file)`. |
| 129 | `                          'not listed (other processes of the file ran in between)')` | Every other process gets `not listed (other processes of the file ran in between)`. |
| 130 | `            for iv in p['iv']:` | Loop over the interval rows of the process. Each interval row becomes one record. No row is left out here. |
| 131 | `                rec = fd.base_record(` | Creates the record with all 40 keys (function `base_record` of `facts_data.py`). Lines 132 to 137 give its values. |
| 132 | `                    folder=rel(folder), file=os.path.basename(p['file']), line=iv['line'], process=n,` | `folder`: the folder in the short form `R/...`. `file`: the name of the csv. `line`: the line number of the interval row in the csv. `process`: the number `n`. |
| 133 | `                    round=p['round'], interval=iv['rep'], kernel=p['kernel'], kernel_before=before,` | `round`: the round of the header line. In a `-- step` header line (A-2, A-3) it is the number at the end of the tag. `interval`: column 4 (`rep`) of the row. `kernel`: the kernel of the header line. `kernel_before`: the text of lines 121 to 129. |
| 134 | `                    binary=p['binary'], GBps=iv['agg'], rate_kind=fd.KIND_A, passes=iv['passes'],` | The rate of part A. `GBps` = `iv['agg']`: column 7 (`aggregate_GBps`) of the interval row, as the binary printed it, with 2 decimal places (a step of 0.01 GB/s). The script does not compute it again and does not round it. The binary computed it as the sum of the bytes of all threads divided by the longest per-thread elapsed time [Ref7]. `rate_kind` = `fd.KIND_A`: a text that names this formula. `passes`: column 5 (`total_bytes`) divided by column 3 (`bytes_per_thread`), as a whole number. For a read kernel that is the number of buffer passes of all threads together. |
| 135 | `                    per_thread_min_GBps=iv['tmin'], per_thread_max_GBps=iv['tmax'], per_thread_avg_GBps=iv['tavg'],` | The three per-thread fields: columns 8, 9 and 10 of the row, the lowest, the highest and the mean per-thread rate in GB/s. |
| 136 | `                    threads=iv['threads'], stop='whole pass', min_ms=500, load1_at_launch=p['load1'],` | `threads`: column 2. `stop='whole pass'` and `min_ms=500` (each timed interval lasts at least 500 ms) are constants of this line, for the rerun and for the baselines. They are not read from the csv. The `# bandwidth:` line of every such process in the csv files does hold `min_ms=500`. These files are the 3 files `threads120.csv` of the rerun, `threads120.csv` of A-1, `A1.csv`, and `A3.csv` for its three `onebuf-ms500` processes. `load1_at_launch`: the 1-minute load average of the header line. |
| 137 | `                    launch_utc=iso(fd.clock(folder, p['utc'])), tag=p['tag'])` | Ends the call of line 131. `launch_utc`: the launch time of the process, from the time of day of the header line and the date of the folder name. `tag`: the tag of a `-- step` header line, or `None`. |
| 138 | `                rec.update(common)` | Sets the fields that the caller passed, for example `dataset`. |
| 139 | `                rec['proc_key'] = '%s\|%s\|%d' % (rec['folder'], rec['file'], n) + ('\|' + p['tag'] if p['tag'] else '')` | `proc_key`: a text that is equal for all records of one process. It joins the folder, the file and `n` with `\|`, plus the tag when the process has one. |
| 140 | `                recs.append(rec)` | Adds the record to the list `D['recs']`. |

### `collect`: nested function `add_bwx`, the records of one bwx process (lines 142 to 161)

| Line | Source | Explanation |
|---:|---|---|
| 142 | `    def add_bwx(sec, folder, proc_tag, kernels=None, positions=None, **common):` | Starts the nested function `add_bwx`. It appends one record per interval of one section `sec`, which holds the rows of one bwx process. `proc_tag`: the tag of the process. `kernels`, `positions`: two optional filters. `**common`: fields that every record of the call gets. |
| 143 | `        nseq = len(sec['hdr']['seq'].split(','))` | `nseq`: the number of kernels in the sequence `seq` of the csv header. |
| 144 | `        h = sec['hdr']` | `h`: the settings of the csv header. |
| 145 | `        for iv in fd.bwx_intervals(sec):` | Loop over the intervals of the section. `fd.bwx_intervals(sec)` gives one entry per interval, with the rate from the T rows. |
| 146 | `            if kernels and iv['kernel'] not in kernels:` | Filter `kernels`: an interval is skipped when its kernel name is not in this list. |
| 147 | `                continue` | Goes on with the next interval. |
| 148 | `            if positions and (iv['kernel'], iv['pos']) not in positions:` | Filter `positions`: an interval is skipped when the pair of kernel and position is not in this set. |
| 149 | `                continue` | Goes on with the next interval. Both filters test only the kernel name and the position. No filter tests a rate. Without a filter every interval becomes a record. The rerun is read without a filter (line 177). |
| 150 | `            rec = fd.base_record(` | Creates the record of one interval that passed the filters. Lines 151 to 157 give its values. Nothing is rounded here. |
| 151 | `                folder=rel(folder), file=os.path.basename(sec['file']), line=iv['line'], round=iv['round'],` | `folder`: the folder in the short form `R/...`. `file`: the name of the csv. `line`: the line number of the I row of the interval. `round`: the round, counted from 0. |
| 152 | `                pos=iv['pos'], interval=iv['round'] * nseq + iv['pos'], kernel=iv['kernel'],` | `pos`: the position. `interval` = round x `nseq` + position. This is the number of the interval in the process, counted from 0. `kernel`: the kernel name. |
| 153 | `                kernel_before=iv['kernel_before'] or 'none (first interval of the process)', GBps=iv['total'],` | The rate of a bwx interval. `GBps` = `iv['total']`. The T rows are grouped by round, position and kernel (columns 2, 3 and 4 of the row). One group is one interval. `fd.bwx_intervals` computes `bytes` / `elapsed_s` / 1e9 (columns 7 and 8) for each T row, which is one thread. It adds the values of all T rows of the interval [Ref1]. So the bytes of each thread are divided by the elapsed time of that thread. The unit is GB/s (GB = 1e9 bytes). `kernel_before`: the kernel that was timed directly before, or the text `none (first interval of the process)`. |
| 154 | `                rate_kind=fd.KIND_X, mesh0_GBps=iv['mesh0'], mesh1_GBps=iv['mesh1'], threads=iv['threads'],` | `rate_kind` = `fd.KIND_X`: a text that names this formula. The column `aggregate_GBps` of the I row is not used here. The runner computed that column with the formula of part A: the sum of the bytes of all threads divided by the longest per-thread elapsed time. Check `I-agg` (line 738) compares it with `total`. `mesh0_GBps`, `mesh1_GBps`: the same sum over the threads on the CPUs 0 to 63, and over the threads on the CPUs 64 and above. The CPU is column 6 (`cpu`) of the T row. `threads`: the number of T rows. |
| 155 | `                is_64_56=iv['is_64_56'], flagged=iv['flagged'], stop=h.get('stop'), start=h.get('start'),` | `is_64_56`: the result of the 64+56 test. `flagged`: the number of T rows with a flag. A flagged row stays in the sum. `stop`, `start`: two settings of the csv header. `stop` = `common`: `bwx12.c` sets one deadline for all threads, `min_ms` milliseconds after the common start time. Each thread reads pieces of 2 MiB and stops after the first piece that ends at or after the deadline. `start` = `common` is the option `--start common`: every thread starts each interval at byte 0 of its own buffer. It does not set the start time of an interval. |
| 156 | `                min_ms=int(h['min_ms']),` | `min_ms`: the interval length of the csv header in ms, as a number. Each thread reads the clock for its own start at or after the common start time, and `elapsed_s` counts from that reading. So `min_ms` is not a lower limit for the elapsed time of one thread. In the 9 bwx12 csv files of the rerun `elapsed_s` of a T row lies between 5.999979 s and 6.000457 s. |
| 157 | `                count=int(h.get('count', 0)), thp=h.get('thp'), tag=proc_tag)` | Ends the call of line 150. `count`: the header value `count`, or 0 when the header has none. The value 1 means that the runner was started with the option `--count`. With this option the runner reads counters for each thread and interval and writes the C rows. `thp`: `madvise` says only that the runner asked Linux for 2 MiB pages for each buffer. `tag`: the tag of the process. In the header lines of the 9 bwx12 csv files of the rerun, `stop`, `start`, `min_ms`, `count` and `thp` are `common`, `common`, 6000 ms, 1 and `madvise`. |
| 158 | `            rec.update(common)` | Sets the fields that the caller passed, for example `dataset`. |
| 159 | `            rec['proc_key'] = '%s\|%s\|%s' % (rec['folder'], rec['file'], proc_tag)` | `proc_key`: a text that is equal for all records of one process. It joins the folder, the file and `proc_tag` with `\|`. |
| 160 | `            recs.append(rec)` | Adds the record to the list `D['recs']`. |

### `collect`: the records of the rerun (lines 162 to 181)

| Line | Source | Explanation |
|---:|---|---|
| 162 | `    # ---- records of the rerun` | Comment: the records of the rerun. |
| 163 | `    for a in A:` | Loop over the 3 part A folders of the rerun. |
| 164 | `        e = evd[a['tag']]` | `e`: the step of this session (lines 89 to 117). |
| 165 | `        n0 = len(recs)` | `n0`: the number of records so far. The records of the next call start at this place of the list. |
| 166 | `        add_k120(a['procs'], a['folder'], dataset='rerun-A', part='A', role='rerun', session=a['session'],` | `add_k120` appends the records of the 24 processes of the session. All 6 kernels of both binaries become records, with 3 intervals each. That gives 72 records per session and 216 in total [Ref9]. Fields passed: `dataset` = `rerun-A`, `part` = `A`, `role` = `rerun` and the session number. The old read kernel is the records with `binary` = `bw_old` and `kernel` = `read`. The new read kernel is the records with `binary` = `bw_new` and `kernel` = `read`. Each has 18 records in `facts.json`: 3 sessions x 2 rounds x 3 intervals [Ref9]. |
| 167 | `                 gap_s=e['gap_s'], start_state=e['state'], **boot72)` | Ends the call of line 166: `gap_s` and `start_state` of the step, and the three fields of `boot72` (line 56). |
| 168 | `        for rec in recs[n0:]:` | Loop over the records that this call appended. |
| 169 | `            rec['tag'] = a['tag']` | `tag` is set to the folder tag, for example `T72A1`. |
| 170 | `            rec['binary_sha256'] = a['probe']['sha'][rec['binary']]` | `binary_sha256`: the sha256 that `probe.txt` of the folder holds for the binary of the record. |
| 171 | `            if rec['process'] > 1:      # ra.sh starts processes 2 to 24 directly after the previous one, with no wait` | Tests for the processes 2 to 24 of the session. The comment gives the reason: `ra.sh` starts them directly after the process before, with no wait. |
| 172 | `                rec['gap_s'] = None` | Their `gap_s` is set to `None`. So in part A only the records of the first process of a session keep a `gap_s`. `start_state` stays on all 72 records of a session. It describes the start of process 1. |
| 173 | `    role_of = dict(L='rerun', C='rerun', I='control, added after the first numbers of parts A, L and C were seen')` | `role_of`: the text of the field `role` per part. Parts L and C get `rerun`. Control I gets a text that says that the control was added after the first numbers of parts A, L and C were seen. |
| 174 | `    for x in X:` | Loop over the 9 bwx12 folders of the rerun. |
| 175 | `        e = evd[x['tag']]` | `e`: the step of this process. |
| 176 | `        la = x['launches'][0]` | `la`: the `launch` line of the process. |
| 177 | `        add_bwx(x['sec'], x['folder'], x['tag'], dataset='control-I' if x['part'] == 'I' else 'rerun-' + x['part'],` | `add_bwx` is called without a filter. So every interval of every kernel becomes a record: 10 per process of part L and of control I, 6 per process of part C. That gives 30 records for part L, 24 for part C and 20 for control I [Ref9]. `proc_tag` is the folder tag, for example `T72L1`. `dataset`: `rerun-L`, `rerun-C` or `control-I`. |
| 178 | `                part=x['part'], role=role_of[x['part']], session=x['session'], binary='bwx12',` | Continues the call of line 177: the part, the role, the session and `binary` = `bwx12`, a constant of this line. Part C holds both kernels: `oldread` is the old read kernel and `read` is the new read kernel, 8 records each [Ref9]. The sequence of part L and of control I holds `oldread`, `asmread` and three test loops. It holds no kernel `read`. |
| 179 | `                binary_sha256=x['env']['sha'], load1_at_launch=la['load1'], launch_utc=iso(la['utc']),` | Continues the call of line 177. `binary_sha256`: the sha256 of the `binary` line of `env.txt`. Check `sha-bwx12` (line 768) compares it with the value in `go.sh`. `load1_at_launch`, `launch_utc`: the 1-minute load average and the time of the `launch` line. |
| 180 | `                gap_s=e['gap_s'], start_state=e['state'], **boot72)` | Ends the call of line 177: `gap_s` and `start_state` of the step, and the three fields of `boot72`. |

### `collect`: the 8000 MT/s baselines of part A (lines 182 to 205)

| Line | Source | Explanation |
|---:|---|---|
| 182 | `    # ---- 8000 MT/s baselines of part A (fixed list of baselines-and-rules.txt)` | Comment: the 8000 MT/s baselines of part A. The rules file `baselines-and-rules.txt` fixes this list [Ref3]. |
| 183 | `    D['base'] = base = {}` | `base`: a dictionary for the three baselines, also kept as `D['base']`. |
| 184 | `    kfolder = os.path.join(R, 'kernels-20261113T181222Z')` | `kfolder`: the result folder of the first test of 2026-11-13 in `R`. |
| 185 | `    pfolder = os.path.join(R, 'partA-20261113T205055Z')` | `pfolder`: the result folder of the script `run_partA.sh` of 2026-11-13 in `R`. |
| 186 | `    base['A-1'] = dict(folder=kfolder, file='threads120.csv', procs=fd.read_k120(os.path.join(kfolder, 'threads120.csv')))` | Baseline A-1: `threads120.csv` of `kfolder`, read by `fd.read_k120`. The file holds 24 processes. |
| 187 | `    base['A-2'] = dict(folder=pfolder, file='A1.csv', procs=fd.read_k120(os.path.join(pfolder, 'A1.csv')))` | Baseline A-2: `A1.csv` of `pfolder`. The file holds 12 processes. |
| 188 | `    base['A-3'] = dict(folder=pfolder, file='A3.csv', procs=fd.read_k120(` | Baseline A-3: `A3.csv` of the same folder. The call goes on in line 189. |
| 189 | `        os.path.join(pfolder, 'A3.csv'), only_tags=lambda t: re.fullmatch(r'onebuf-ms500-[123]', t) is not None))` | Ends the call of line 188. The test `only_tags` keeps only the processes whose tag is `onebuf-ms500-1`, `onebuf-ms500-2` or `onebuf-ms500-3`. `re.fullmatch` requires that the whole tag fits the pattern. The file `A3.csv` holds 12 processes. So 9 processes are left out with all their rows. `A1.csv` and `A3.csv` also hold rows that start with `thread,` (the per-thread rows of the option `--per-thread`). They are not interval rows, and they give no record. `fd.read_k120` keeps their rates in `thr` of the process [Ref1]. |
| 190 | `    # The copy kernels count read plus written bytes. The header line of every copy and asmcopy process must say so,` | Comment: the copy kernels count the bytes read plus the bytes written. The header line of every process of `copy` and `asmcopy` must say so (the reason follows in line 191). |
| 191 | `    # because facts.json gives the meaning of the field "passes" from it.` | Comment: the reason: `facts.json` gives the meaning of the field `passes` from this header text. |
| 192 | `    cp = [p for procs in [a['procs'] for a in A] + [b['procs'] for b in base.values()] for p in procs` | `cp`: the list of all processes of the kernels `copy` and `asmcopy`, in the 3 files of the rerun and in the 3 baselines. |
| 193 | `          if p['kernel'] in ('copy', 'asmcopy')]` | Continues the list of line 192: the test on the kernel name. |
| 194 | `    assert cp and all(p.get('copy_note') for p in cp), 'a copy process without the header note on read+write bytes'` | The `assert` stops the script when the list is empty. It also stops the script when the header line that the binary printed for one of these processes lacks the text `copy counts read+write bytes`. |
| 195 | `    D['probe13'] = open_probe13(kfolder)` | `open_probe13` (line 568) reads the other records of the run of 2026-11-13. The result is kept as `D['probe13']`. |
| 196 | `    D['env_partA'] = fd._open(os.path.join(pfolder, 'env.txt')).read()` | `D['env_partA']`: the text of `env.txt` of `pfolder`, the folder of A-2 and A-3. Check `sha-bw` (line 756) uses it. |
| 197 | `    sha13 = D['probe13']['sha']` | `sha13`: the sha256 values of `probe.txt` of 2026-11-13, by file name. |
| 198 | `    for name, order_known in (('A-1', True), ('A-2', True), ('A-3', False)):` | Loop over the three baselines. `order_known` is false for A-3 only (line 124). |
| 199 | `        b = base[name]` | `b`: the entry of the baseline. |
| 200 | `        n0 = len(recs)` | `n0`: the number of records so far. |
| 201 | `        add_k120(b['procs'], b['folder'], order_known=order_known, dataset=name, part='A', role='baseline',` | `add_k120` appends the records of the baseline. Every interval row of the kept processes becomes a record: 72 for A-1, 36 for A-2 and 9 for A-3 [Ref9]. `dataset` = `A-1`, `A-2` or `A-3`. `part` = `A`. `role` = `baseline`. `session`, `gap_s` and `start_state` stay `None` in these records. |
| 202 | `                 **state_of(b['folder']))` | Ends the call of line 201: `state_of` (line 58) gives `speed_MTps` = 8000, the module count and the boot label. The rules file says that every baseline ran in the boot of 2026-11-09 with 12 memory modules at 8000 MT/s [Ref3]. |
| 203 | `        for rec in recs[n0:]:` | Loop over the records that this call appended. |
| 204 | `            rec['binary_sha256'] = sha13[rec['binary']]` | `binary_sha256`: the value of `sha13` for the binary of the record. This is the sha256 in `probe.txt` of `kfolder`, the A-1 folder. The records of A-2 and A-3 get this value too. Their own folder is not read for this field. Check `sha-bw` (line 756) tests that `env.txt` of their folder holds the same two values. |

### `collect`: the earlier data sets of `bwx12` and `bwx11` (lines 206 to 256)

| Line | Source | Explanation |
|---:|---|---|
| 206 | `    # ---- bwx folders written by rx.sh or r0.sh (one csv per process)` | Comment: the bwx folders that `rx.sh` or `r0.sh` wrote. Such a folder holds one csv per process. |
| 207 | `    rx_sets = [` | `rx_sets`: starts the table of the earlier data sets of `bwx12` and `bwx11`. Each entry gives 5 values. |
| 208 | `        # dataset, role, folder prefix, files, positions` | Comment: the 5 values of an entry: the data set name, the role, the start of the folder name, the csv files and the position filter. |
| 209 | `        ('L-1', 'baseline (identical argument line)', 'w120-R8', ['a6456.csv'], None),` | L-1: the baseline with the identical argument line. Folder `w120-R8-...`, file `a6456.csv`, no filter (`None`). So every interval of the file becomes a record. Only the csv files named in the table give records. Example: the folder of L-1 holds 5 csv files, and only `a6456.csv` gives records. |
| 210 | `        ('L-2', 'supporting (4 s, other counter events)', 'w120-R1', ['p1nop.csv', 'p2add.csv'], POS01),` | L-2: a supporting run with intervals of 4 s and other counter events. Folder `w120-R1-...`, two csv files, filter `POS01`. Of them only `oldread` at position 0 and `asmread` at position 1 become records. Every other interval is left out. |
| 211 | `        ('L-3', 'supporting (4 s, other counter events)', 'w120-R5', ['thp.csv'], POS01),` | L-3: a supporting run of the same kind. Folder `w120-R5-...`, file `thp.csv`, filter `POS01`. |
| 212 | `        ('L-4', 'supporting (4 s, other counter events)', 'w120-R6', ['st1.csv', 'st2.csv', 'st3.csv'], POS01),` | L-4: a supporting run of the same kind. Folder `w120-R6-...`, three csv files, filter `POS01`. |
| 213 | `        ('R0', 'other binary (bwx11)', 'w120-R0', ['p1.csv', 'p2.csv'], POS01),` | R0: a run of the other binary `bwx11`. Folder `w120-R0-...`, files `p1.csv` and `p2.csv`, filter `POS01`. Example of what the filter drops: the sequence of `p1.csv` of R0 (header line `# bwx:` of the file) holds `asmread` again at position 10 and `oldread` again at position 11. The intervals at these two positions are left out in both rounds of the process. |
| 214 | `        ('R0b', 'other binary (bwx11), 4 s', 'w120-R0b', ['cA.csv', 'cB.csv', 'cC.csv'], POS01),` | R0b: a run of `bwx11` with intervals of 4 s. Folder `w120-R0b-...`, three csv files, filter `POS01`. |
| 215 | `        ('X2d12', 'not a baseline (firmware test setting)', 'w120-X2d12', ['a6456.csv'], None),` | X2d12: not a baseline. The role text says that it ran with a firmware test setting. Folder `w120-X2d12-...`, file `a6456.csv`, no filter. |
| 216 | `        ('X1d10', '10 modules', 'w120-X1d10', ['a6456.csv'], POS01),` | X1d10: a run with 10 memory modules. Folder `w120-X1d10-...`, file `a6456.csv`, filter `POS01`. |
| 217 | `        ('X1d10b', '10 modules', 'w120-X1d10b', ['a6456.csv'], POS01),` | X1d10b: a second run with 10 memory modules. Folder `w120-X1d10b-...`, file `a6456.csv`, filter `POS01`. |
| 218 | `        ('BASEd10', '10 modules', 'w120-BASEd10', ['a6456.csv'], POS01),` | BASEd10: a third run with 10 memory modules. Folder `w120-BASEd10-...`, file `a6456.csv`, filter `POS01`. |
| 219 | `        ('F72d12', '7200 MT/s sample of the same boot, earlier visit, not part of the rerun', 'w120-w120-F72d12',` | F72d12: the role text says that it is a 7200 MT/s sample of the same boot from an earlier visit, and not part of the rerun. The folder name starts with `w120-w120-F72d12`. |
| 220 | `         ['a6456.csv'], None),` | Ends the entry of line 219: file `a6456.csv`, no filter. |
| 221 | `    ]` | Ends the table. 8 data sets have the filter `POS01`: L-2, L-3, L-4, R0, R0b, X1d10, X1d10b and BASEd10. 3 data sets have no filter: L-1, X2d12 and F72d12. Only the csv files named in the table give records. |
| 222 | `    D['rx'] = {}` | `D['rx']`: a dictionary for these data sets, by name. |
| 223 | `    for name, role, prefix, files, positions in rx_sets:` | Loop over the 11 entries of the table. |
| 224 | `        folder = fd.find(prefix)` | `fd.find` returns the one folder in `R` whose name starts with the prefix and `-2026`. |
| 225 | `        env = fd.read_env(folder)` | `env`: the values of `env.txt` of the folder (`fd.read_env`). |
| 226 | `        env['has_binary_line'] = env['sha'] is not None` | `has_binary_line`: whether `env.txt` holds a line `binary PATH CHECKSUM`. `env['sha']` is the sha256 of that line, or `None` without such a line. |
| 227 | `        if env['sha'] is None:      # r0.sh wrote no binary line to env.txt; the script itself holds the checksum` | The case without a `binary` line. `env.txt` in the folder of R0 has no such line. The comment gives the reason: `r0.sh` wrote none, and the script itself holds the checksum. `r0.sh` is the run script of the data set R0. |
| 228 | `            txt = fd._open(os.path.join(fd.W15, 'r0.sh')).read()` | `txt`: the text of `r0.sh` in the folder `fd.W15`. |
| 229 | `            env['sha'] = re.search(r'echo "([0-9a-f]{64})  \$BW"', txt)[1]` | The sha256 is taken from the text of `r0.sh`. The pattern fits the text `echo "`, 64 hexadecimal digits, two spaces and `$BW"`. Group 1 holds the 64 digits. In `r0.sh` this `echo` feeds the test of the binary with `sha256sum -c`. |
| 230 | `            env['sha_line'] = next(i for i, l in enumerate(txt.splitlines(), 1) if env['sha'] in l)` | `sha_line`: the number of the first line of `r0.sh` that holds this checksum. |
| 231 | `            env['binary'] = re.search(r'^BW=(\S+)', txt, re.M)[1]` | `binary`: the path of the binary, the text after `BW=` at the start of a line of `r0.sh`. |
| 232 | `        la = {l['tag']: l for l in fd.read_launches(folder)}` | `la`: the launch entries of `launches.txt` (`fd.read_launches`), as a dictionary by tag. |
| 233 | `        err = os.path.join(folder, 'stderr.txt')` | `err`: the path of `stderr.txt` of the folder. |
| 234 | `        fd.OPENED.append(err)` | Adds this path to `fd.OPENED` directly. The file is not read. Only its size is used (line 248). |
| 235 | `        if name == 'F72d12':` | The case of the data set F72d12. Lines 238 to 244 set its fields `st` and test the times of its process. |
| 236 | `            # The folder holds no boot id. Its process lies between two readings of the boot id of the rerun:` | Comment: the folder holds no boot id. Its process lies between two readings of the boot id of the rerun (the sentence goes on in line 237). |
| 237 | `            # try6.txt before it and the first state line of go.sh after it. The text of section 4.1 states this.` | Comment: the two readings are `try6.txt` before the process and the first state line of `go.sh` after it. The text of section 4.1 of the facts sheet states this. |
| 238 | `            st = dict(boot72)` | `st`: a copy of `boot72` (line 56): the memory speed and the module count of `try6.txt` and the boot id of the rerun. |
| 239 | `            assert fd.folder_date(folder) > try6['first_log_utc']` | Test 1: the time in the folder name must lie after the first line of the Linux kernel log of this boot (`first_log_utc`, from row 0 of `gaps.txt`). If not, the `assert` stops the script. |
| 240 | `            f72 = la[files[0][:-4]]` | `f72`: the launch entry of the process. Its tag is the name of the first csv file without `.csv`, which is `a6456`. |
| 241 | `            go0 = logs['go']['states'][0]` | `go0`: the first state line of the log of `go.sh`. |
| 242 | `            assert try6['utc'] < f72['utc'] < f72['rc_utc'] < go0['utc'] and go0['boot'] == try6['boot'], 'F72d12'` | Test 2: the process must start after the time of `try6.txt` and end before the first state line of `go.sh`. That state line must hold the boot id of `try6.txt`. The end of the process is the time of its `rc` line. |
| 243 | `            assert try6['boots_first'] <= f72['utc'] and f72['rc_utc'] <= try6['boots_last'], 'F72d12, boots.txt'` | Test 3: the process must lie inside the time range of row 0 of `boots.txt`. Row 0 of `boots.txt` holds the boot id of the rerun. |
| 244 | `            assert try6['first_log_utc'] <= f72['utc'] and f72['rc_utc'] <= try6['last_log_utc'], 'F72d12, gaps.txt'` | Test 4: the process must lie inside the time range of row 0 of `gaps.txt`, from the first to the last line of the Linux kernel log. `gaps.txt` holds no boot id. The script takes its row 0 as the same boot. |
| 245 | `        else:` | Every other data set. |
| 246 | `            st = state_of(folder)` | `st`: `state_of(folder)` takes the memory speed, the module count and the boot label from the DIMM report (line 58). |
| 247 | `        D['rx'][name] = dict(folder=folder, env=env, launches=la, files=files, role=role, state=st, secs={},` | `D['rx'][name]` keeps the folder, `env`, the launch entries, the file names, the role, `st` and an empty dictionary `secs`. |
| 248 | `                             stderr_bytes=os.path.getsize(err))` | Ends the entry of line 247. `stderr_bytes`: the size of `stderr.txt` in bytes. |
| 249 | `        for fn in files:` | Loop over the csv files of the data set. |
| 250 | `            sec = fd.read_bwx(os.path.join(folder, fn))[0]` | `sec`: the first section of the file. The 17 csv files named in the table hold no `-- step` line. So each is one section. |
| 251 | `            tag = fn[:-4]` | `tag`: the file name without `.csv`, for example `a6456`. `rx.sh` and `r0.sh` name the csv after the tag of the process. |
| 252 | `            D['rx'][name]['secs'][tag] = sec` | Keeps the section in `secs` under the tag. |
| 253 | `            add_bwx(sec, folder, tag, positions=positions, dataset=name, part='L', role=role,` | `add_bwx` appends the records with the position filter of the data set. `dataset` is the name of the data set, and `part` is `L`. The 11 data sets give 74 records [Ref9]. |
| 254 | `                    binary=fd.SHA_NAMES[env['sha'][:8]], binary_sha256=env['sha'], load1_at_launch=la[tag]['load1'],` | Continues the call of line 253. `binary`: the short name that `fd.SHA_NAMES` gives for the first 8 digits of the sha256, `bwx12` or `bwx11`. `binary_sha256`: the full value. `load1_at_launch`: the 1-minute load average of the launch entry with the same tag. |
| 255 | `                    launch_utc=iso(la[tag]['utc']), **st)` | Ends the call of line 253: the time of that launch entry and the three fields of `st`. |

### `collect`: the data sets of the first runner `bwx`, and the last entries of `D` (lines 257 to 292)

| Line | Source | Explanation |
|---:|---|---|
| 257 | `    # ---- folders of the first runner bwx (2026-11-13/14): one csv with one section per process` | Comment: the folders of the first runner `bwx` (2026-11-13 and 2026-11-14). Such a folder holds one csv with one section per process. |
| 258 | `    step_sets = [` | `step_sets`: starts the table of these data sets. Each entry gives the name, the folder under `R`, the csv file and the start of the process tags that belong to the data set. |
| 259 | `        ('B7a', 'B7-20261113T232859Z', 'B7.csv', 'common-6000-'),` | B7a: `B7.csv` of the first B7 folder, tags that start with `common-6000-`. `run_bwx.sh` builds such a tag from the stop rule, the interval length in ms, the start place and a process number. So the prefix keeps the processes with the common stop and intervals of 6000 ms. |
| 260 | `        ('B7b', 'B7-20261114T024352Z', 'B7.csv', 'common-6000-'),` | B7b: `B7.csv` of the second B7 folder, same prefix. |
| 261 | `        ('C3a', 'C3-20261114T022708Z', 'C3.csv', 'common-6000-'),` | C3a: `C3.csv` of the first C3 folder, same prefix. |
| 262 | `        ('C3b', 'C3-20261114T054116Z', 'C3.csv', 'common-6000-'),` | C3b: `C3.csv` of the second C3 folder, same prefix. |
| 263 | `        ('B5a', 'B5-20261114T011723Z', 'B5.csv', 'b5-fwd-'),` | B5a: `B5.csv` of the first B5 folder, tags that start with `b5-fwd-`. `run_bwx.sh` gives this tag to the processes with the forward kernel sequence. |
| 264 | `        ('B5b', 'B5-20261114T043213Z', 'B5.csv', 'b5-fwd-'),` | B5b: `B5.csv` of the second B5 folder, prefix `b5-fwd-`. |
| 265 | `        ('B5a-rev', 'B5-20261114T011723Z', 'B5.csv', 'b5-rev-'),` | B5a-rev: the same file as B5a, with the prefix `b5-rev-`, the processes with the reverse kernel sequence. So two data sets can share one csv file. |
| 266 | `        ('B5b-rev', 'B5-20261114T043213Z', 'B5.csv', 'b5-rev-'),` | B5b-rev: the same file as B5b, with the prefix `b5-rev-`. |
| 267 | `    ]` | Ends the table. |
| 268 | `    D['step'] = {}` | `D['step']`: a dictionary for these data sets, by name. |
| 269 | `    for name, fname, csv, prefix in step_sets:` | Loop over the 8 entries of the table. |
| 270 | `        folder = os.path.join(R, fname)` | `folder`: the path of the folder under `R`. |
| 271 | `        envtxt = fd._open(os.path.join(folder, 'env.txt')).read()` | `envtxt`: the text of `env.txt` of the folder. |
| 272 | `        sha = re.search(r'^([0-9a-f]{64})  bwx$', envtxt, re.M)[1]` | `sha`: the sha256 of the binary `bwx`. The pattern fits a line of `env.txt` that holds 64 hexadecimal digits, two spaces and the name `bwx`, and nothing more. Group 1 holds the digits. |
| 273 | `        allsecs = fd.read_bwx(os.path.join(folder, csv))` | `allsecs`: all sections of the csv (`fd.read_bwx`), one per `-- step` header line. |
| 274 | `        for i, s in enumerate(allsecs):` | Loop over the sections with their index `i`, counted from 0. |
| 275 | `            s['prev_step'] = allsecs[i - 1]['step'] if i else None` | `prev_step` of a section: the header values of the section before it in the file. It is `None` for the first section. |
| 276 | `        secs = [s for s in allsecs if s['step']['tag'].startswith(prefix)]` | `secs`: only the sections whose tag starts with the prefix of the data set. The other sections of the file give no record in this data set. Example: `B7.csv` of B7a (folder `B7-20261113T232859Z`) holds 48 sections, and the prefix `common-6000-` keeps 8 of them. 4 of the 8 have a tag `common-6000-offset-...`. Their processes ran with `--start offset`, and their records have `start` = `offset`. |
| 277 | `        D['step'][name] = dict(folder=folder, file=csv, sha=sha, secs=secs, prefix=prefix)` | `D['step'][name]` keeps the folder, the file name, `sha`, `secs` and the prefix. |
| 278 | `        for sec in secs:` | Loop over the kept sections. |
| 279 | `            st = sec['step']` | `st`: the values of the `-- step` header line of the section. |
| 280 | `            add_bwx(sec, folder, st['tag'], kernels=READ3, dataset=name, part='C',` | `add_bwx` is called with `kernels=READ3`. So only the intervals of `oldread`, `read` and `asmread` become records. The other kernels of the sequence are left out, for example `asmread2` and `read_nop4`. No position filter is set. In the sequence of `B7.csv` and `C3.csv` (`B7SEQ` in `run_bwx.sh`) each of the three kernels stands at two positions: `oldread` at 0 and 7, `read` at 1 and 6, `asmread` at 2 and 5. The intervals at both positions become records in both rounds of the process. `proc_tag` is the tag of the `-- step` line. `part` = `C`. |
| 281 | `                    role='other binary (bwx)' + (', reverse kernel order, not in the list of rule V4'` | `role`: the text `other binary (bwx)`. The addition of line 282 follows for two data sets. |
| 282 | `                                                 if name.endswith('-rev') else ''),` | Ends the expression of line 281. The two data sets whose name ends with `-rev` get the added text `, reverse kernel order, not in the list of rule V4`. |
| 283 | `                    binary=fd.SHA_NAMES[sha[:8]], binary_sha256=sha, load1_at_launch=st['load1'],` | `binary`: the name that `fd.SHA_NAMES` gives for the first 8 digits of `sha`. The dictionary holds the name `bwx` for one checksum. `binary_sha256`: the full value. `load1_at_launch`: the 1-minute load average of the `-- step` line. |
| 284 | `                    launch_utc=iso(fd.clock(folder, st['utc'])), **state_of(folder))` | Ends the call of line 280. `launch_utc`: the launch time, from the time of day of the `-- step` line and the date of the folder name. `state_of` gives the memory speed, the module count and the boot label. The 8 data sets give 312 records [Ref9]. |
| 285 | `    D['hw'] = hw_records(D)` | `D['hw']`: the hardware error records inside the process windows of 6 earlier data sets (line 296). Lines 285 to 289 add five entries to `D`. They hold no rate of the rerun, and they change no record. |
| 286 | `    D['hw_cmp'] = hw_compare(D['hw'])` | `D['hw_cmp']`: a comparison of the intervals that have such a record (line 340). |
| 287 | `    D['fw'] = open_fw()` | `D['fw']`: the saved firmware settings (line 429). |
| 288 | `    D['a2pre'] = open_a2pre()` | `D['a2pre']`: the run folder before baseline A-2 (line 509). |
| 289 | `    D['mod'] = open_mod()` | `D['mod']`: what a boot with 10 modules shows in the lines that the facts sheet uses as proof of 12 modules (line 536). |
| 290 | `    return D` | Returns `D` to `main`. |

### `HW_ROWS` and function `hw_records`: hardware error records inside process windows (lines 293 to 339)

| Line | Source | Explanation |
|---:|---|---|
| 293 | `HW_ROWS = ('L-1', 'L-2', 'L-3', 'L-4', 'R0', 'R0b')     # the bwx12 and bwx11 rows of the 2026-11-09 boot` | `HW_ROWS`: the 6 data sets whose processes `hw_records` tests: L-1 to L-4, R0 and R0b. The comment says that these are the rows of `bwx12` and `bwx11` of the boot of 2026-11-09. In the records of `facts.json` all 6 data sets hold 8000 MT/s [Ref9]. |
| 296 | `def hw_records(D):` | Starts the function `hw_records`. It finds the hardware error records of the journal that lie inside the time of a process. The tests of this function use no rate. |
| 297 | `    """Hardware error records of the saved journal of the 2026-11-09 boot inside the process windows of the` | Comment: the function returns the hardware error records of the saved journal of the boot of 2026-11-09 that lie inside the process windows (the sentence goes on in line 298). |
| 298 | `    rows HW_ROWS. The window of a process runs from its launch line to its rc line in launches.txt.` | Comment: the processes are those of the rows `HW_ROWS`. The window of a process runs from its `launch` line to its `rc` line in `launches.txt`. |
| 299 | `    Both the journal and launches.txt give whole seconds. So a record with the journal time J and a launch` | Comment: both the journal and `launches.txt` give whole seconds. The sentence on a record with the journal time J and a launch line with the time L goes on in line 300. |
| 300 | `    line with the time L lies between J - L - 1 and J - L + 1 seconds after the process start.` | Comment: such a record lies between J - L - 1 and J - L + 1 seconds after the process start. |
| 301 | `    A record is 'inside' an interval when this whole span lies between the start and the end of the interval,` | Comment: a record is `inside` an interval when this whole span lies between the start and the end of the interval. |
| 302 | `    'possible' when the span and the interval share a part, and 'outside' otherwise.` | Comment: it is `possible` when the span and the interval share a part, and `outside` in every other case. |
| 303 | `    The fields 'kind' and 'interval' of a record test only the intervals that the sheet uses: oldread at position 0` | Comment: the fields `kind` and `interval` of a record test only the intervals that the facts sheet uses: `oldread` at position 0 (the sentence goes on in line 304). |
| 304 | `    and asmread at position 1. The field 'every' holds the same test against every interval of the process."""` | Comment: and `asmread` at position 1. The field `every` holds the same test against every interval of the process. |
| 305 | `    errs = fd.read_error_records(D['probe13']['h5'])` | `errs`: all hardware error records of the saved journal `h-5.txt` (`fd.read_error_records`). The path comes from `open_probe13` (line 600). |
| 306 | `    boots = {D['rx'][n]['state']['boot'] for n in HW_ROWS}` | `boots`: the boot labels of the 6 data sets. |
| 307 | `    assert len(boots) == 1, boots` | The `assert` requires that the 6 data sets have one and the same boot label. The error shows the labels. |
| 308 | `    out = []` | `out`: the result list, empty at first. |
| 309 | `    for name in HW_ROWS:` | Loop over the 6 data sets. |
| 310 | `        v = D['rx'][name]` | `v`: the entry of the data set in `D['rx']`. |
| 311 | `        for tag, sec in v['secs'].items():` | Loop over the csv files of the data set. `tag` names the process and `sec` holds its rows. |
| 312 | `            la = v['launches'][tag]` | `la`: the launch entry of the process. |
| 313 | `            assert D['probe13']['boot_start'] < la['utc'] < la['rc_utc']` | The `assert` requires that the launch lies after the start of that boot and before the time of the `rc` line. |
| 314 | `            allv = fd.bwx_intervals(sec)` | `allv`: all intervals of the process, from `fd.bwx_intervals`. That call computes the rate `total` of every interval again. This includes the intervals that the filter `POS01` left out of the records. `hw_compare` (line 340) uses these rates. |
| 315 | `            used = [iv for iv in allv if (iv['kernel'], iv['pos']) in POS01]` | `used`: the intervals that pass `POS01`, which are `oldread` at position 0 and `asmread` at position 1. |
| 316 | `            hits = []` | `hits`: the records inside the window of this process, empty at first. |
| 317 | `            for e in errs:` | Loop over all records of the journal. |
| 318 | `                if not la['utc'] <= e['utc'] <= la['rc_utc']:` | Tests whether the time of the record lies outside the process window. The window runs from the time of the `launch` line to the time of the `rc` line, both ends included. |
| 319 | `                    continue` | A record outside the window is skipped. |
| 320 | `                off = (e['utc'] - la['utc']).total_seconds()` | `off`: the journal time of the record minus the time of the `launch` line, in seconds. The code takes the time of the `launch` line as the start of the process. |
| 321 | `                kind, where = 'outside', None` | `kind` starts as `outside`, and `where` (the interval of the record) as `None`. |
| 322 | `                for iv in used:` | Loop over the intervals of `used`. Each one is tested against the span from `off` - 1 to `off` + 1. |
| 323 | `                    if iv['t_start'] <= off - 1 and off + 1 <= iv['t_end']:` | Tests whether the whole span lies inside the interval. The start of an interval is its earliest thread start (`t_start`). The end is its latest thread end (`t_end`). Both are in seconds from the process start. |
| 324 | `                        kind, where = 'inside', iv` | Then `kind` is `inside`, and `where` is this interval. |
| 325 | `                    elif off - 1 < iv['t_end'] and iv['t_start'] < off + 1 and kind != 'inside':` | If not: tests whether the span and the interval share a part. A result `inside` of an earlier interval is not replaced. |
| 326 | `                        kind, where = 'possible', iv` | Then `kind` is `possible`, and `where` is this interval. |
| 327 | `                # the same test against every interval of the process (all kernels and positions), for hw_compare()` | Comment: the same test follows against every interval of the process (all kernels and positions). The function `hw_compare` uses it. |
| 328 | `                every = []` | `every`: the list of the results, empty at first. |
| 329 | `                for iv in allv:` | Loop over all intervals of the process. |
| 330 | `                    if iv['t_start'] <= off - 1 and off + 1 <= iv['t_end']:` | Tests whether the whole span lies inside the interval. |
| 331 | `                        every.append(('inside', iv))` | Then the pair of `inside` and the interval is added. |
| 332 | `                    elif off - 1 < iv['t_end'] and iv['t_start'] < off + 1:` | If not: tests whether the span and the interval share a part. |
| 333 | `                        every.append(('possible', iv))` | Then the pair of `possible` and the interval is added. An interval that the span does not touch gives no pair. |
| 334 | `                hits.append(dict(e, offset_s=off, kind=kind, interval=where, every=every))` | Stores the record with four more fields: `offset_s` (the value `off`), `kind`, `interval` (the value `where`) and `every`. |
| 335 | `            out.append(dict(dataset=name, tag=tag, folder=v['folder'], file=sec['file'], launch=la, used=used,` | Adds one entry per process: the data set, the tag, the folder, the csv file, the launch entry and `used`. |
| 336 | `                            all=allv, records=hits))` | Ends the entry of line 335: `all` (the list `allv`) and `records` (the list `hits`). |
| 337 | `    return out` | Returns the list with one entry per process. |

### Function `hw_compare`: an interval with a record against the other round (lines 340 to 399)

| Line | Source | Explanation |
|---:|---|---|
| 340 | `def hw_compare(hw):` | Starts the function `hw_compare`. It takes the result of `hw_records`. For each interval with a record it finds the interval of the same kernel and position in the other round, and the difference of the two rates. |
| 341 | `    """Every interval (all kernels and positions) of the processes of hw_records() that has a record, against the` | Comment: every interval (all kernels and positions) of the processes of `hw_records` that has a record is set against another interval (named in line 342). |
| 342 | `    interval of the same kernel at the same position in the other round of the same process.` | Comment: the other interval is that of the same kernel at the same position in the other round of the same process. |
| 343 | `    rows:   the records lie inside the interval, or the interval is the only one that their span of +-1 s touches.` | Comment: result list `rows`: the records lie inside the interval, or the interval is the only one that their span of plus or minus 1 s touches. |
| 344 | `    border: records whose span touches two intervals. The 1 s resolution cannot assign them to one of them.` | Comment: result list `border`: records whose span touches two intervals. The resolution of 1 s cannot assign them to one of the two. |
| 345 | `    clean:  the positions at which neither round has a record inside it or at its border, with round 1 minus round 0.` | Comment: result list `clean`: the positions at which neither round has a record inside it or at its border, with the rate of round 1 minus the rate of round 0. |
| 346 | `    This is a view added after the numbers were seen. The sheet draws no wording by rule V1 point 2 from it."""` | Comment: this view was added after the numbers were seen. The facts sheet draws no wording by rule V1 point 2 from it. Rule V1 point 2 of the rules file fixes the comparison of the 7200 MT/s range with the 8000 MT/s range [Ref3]. |
| 347 | `    rows, border, clean = [], [], []` | The three result lists, empty at first. |
| 348 | `    for h in hw:` | Loop over the processes of `hw_records`. |
| 349 | `        if not h['records']:` | Tests whether the process has no record. |
| 350 | `            continue` | Such a process is skipped. |
| 351 | `        ivs = h['all']` | `ivs`: the list of all intervals of the process. |
| 352 | `        assert {iv['round'] for iv in ivs} == {0, 1}, (h['dataset'], h['tag'])` | The `assert` requires that the rounds of the process are exactly 0 and 1. The error shows the data set and the tag. |
| 353 | `        mark = {}                                   # id(interval) -> every record that touches it` | `mark`: for each interval, every record whose span touches it (`inside` or `possible`). The key `id(iv)` is the identity number that Python gives to the interval object. |
| 354 | `        for e in h['records']:` | Loop over the records of the process. |
| 355 | `            for kind, iv in e['every']:` | Loop over the pairs of `every` of the record. |
| 356 | `                mark.setdefault(id(iv), []).append(e)` | Adds the record to the list of the interval. `setdefault` creates the list at the first record. |
| 358 | `        def other(iv):` | Starts the nested function `other`. It returns the interval with the same position and kernel in the other round. |
| 359 | `            o = [x for x in ivs if (x['pos'], x['kernel']) == (iv['pos'], iv['kernel']) and x['round'] != iv['round']]` | `o`: the intervals of the process with the same position and kernel and another round. |
| 360 | `            assert len(o) == 1, (h['dataset'], h['tag'], iv['pos'])` | The `assert` requires exactly one such interval. |
| 361 | `            return o[0]` | Returns it. |
| 363 | `        def cmp_(iv):` | Starts the nested function `cmp_`. It compares one interval with its partner of the other round. |
| 364 | `            o = other(iv)` | `o`: the partner (line 358). |
| 365 | `            return dict(iv=iv, other=o, other_has_records=id(o) in mark, diff=iv['total'] - o['total'])` | Returns the interval, the partner `other`, the flag `other_has_records` (whether a record touches the partner) and `diff`. `diff` = `total` of the interval minus `total` of the partner, in GB/s. `total` is the rate of an interval: the sum over its T rows. |
| 366 | `        owner = {}                                  # id(interval) -> (interval, where, records assigned to it)` | `owner`: for each interval that gets records, the interval, the text `where` and the records assigned to it. |
| 367 | `        by_t = {}` | `by_t`: the records at a border of two intervals, by their journal time. |
| 368 | `        for e in h['records']:` | Loop over the records of the process. Each record goes to one interval or to a border. |
| 369 | `            kinds = [k for k, _ in e['every']]` | `kinds`: one entry (`inside` or `possible`) for each interval that the span of the record touches. |
| 370 | `            assert 1 <= len(kinds) <= 2, (h['dataset'], h['tag'], e['line'], kinds)` | The `assert` requires 1 or 2 entries. The error shows the data set, the tag, the journal line and the entries. |
| 371 | `            if len(kinds) == 1:` | The case of one entry: the span touches one interval only. |
| 372 | `                iv = e['every'][0][1]` | `iv`: that interval. |
| 373 | `                if kinds[0] == 'inside':` | Tests whether the entry is `inside`. |
| 374 | `                    where = 'inside'` | Then the record goes to that interval with `where` = `inside`. |
| 375 | `                else:` | The other case: one entry `possible`. |
| 376 | `                    assert e['offset_s'] - 1 < iv['t_start'] and iv is ivs[0], (h['dataset'], h['tag'], e['line'])` | The `assert` requires that the span starts before the start of the interval, and that the interval is the first one of the process. So the record lies before the first interval or inside it. |
| 377 | `                    where = 'before or inside'` | `where` = `before or inside`. |
| 378 | `                slot = owner.setdefault(id(iv), (iv, where, []))` | `slot`: the entry of the interval in `owner`. `setdefault` creates it at the first record of the interval. |
| 379 | `                assert slot[1] == where` | The `assert` requires that all records of one interval have the same `where`. |
| 380 | `                slot[2].append(e)` | Adds the record to the records of the interval. |
| 381 | `            else:` | The case of two entries: the span touches two intervals. |
| 382 | `                assert kinds == ['possible', 'possible'], (h['dataset'], h['tag'], e['line'], kinds)` | The `assert` requires that both entries are `possible`. Then the record lies at the border of two intervals. |
| 383 | `                by_t.setdefault(e['utc'], []).append(e)` | The record goes to `by_t` under its journal time. |
| 384 | `        for iv, where, es in owner.values():` | Loop over the intervals of `owner`. Each one gives one entry of `rows`. |
| 385 | `            rows.append(dict(cmp_(iv), dataset=h['dataset'], tag=h['tag'], file=h['file'], where=where, records=es,` | The entry holds the result of `cmp_` for the interval, the data set, the tag, the file, `where` and the records. |
| 386 | `                             used=(iv['kernel'], iv['pos']) in POS01))` | Ends the entry of line 385. `used`: true when the interval passes `POS01`. |
| 387 | `        for t, es in sorted(by_t.items()):` | Loop over the journal times of `by_t` in time order. Each one gives one entry of `border`. |
| 388 | `            pair = [iv for _, iv in es[0]['every']]` | `pair`: the two intervals that the span of the first record of this time touches. |
| 389 | `            assert all([iv for _, iv in e['every']] == pair for e in es)` | The `assert` requires that all records of this time touch the same two intervals. |
| 390 | `            border.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], records=es,` | The entry holds the data set, the tag, the file and the records. |
| 391 | `                               intervals=[cmp_(iv) for iv in pair]))` | Ends the entry of line 390. `intervals`: the result of `cmp_` for both intervals. |
| 392 | `        for pos in sorted({iv['pos'] for iv in ivs}):` | Loop over the positions of the process, in rising order. This loop builds `clean`. |
| 393 | `            a, b = sorted((iv for iv in ivs if iv['pos'] == pos), key=lambda iv: iv['round'])` | `a`: the interval of round 0 at this position. `b`: the interval of round 1. |
| 394 | `            if id(a) not in mark and id(b) not in mark:` | Tests whether no record touches `a` and no record touches `b`. |
| 395 | `                clean.append(dict(dataset=h['dataset'], tag=h['tag'], file=h['file'], pos=pos, kernel=a['kernel'],` | Then one entry is added: the data set, the tag, the file, the position and the kernel. |
| 396 | `                                  r0=a, r1=b, diff=b['total'] - a['total']))` | Ends the entry of line 395. `r0`, `r1`: the two intervals. `diff` = `total` of round 1 minus `total` of round 0, in GB/s. |
| 397 | `    return dict(rows=rows, border=border, clean=clean)` | Returns the three lists. |

### Function `hw_compare_json`: the comparison in the form of `facts.json` (lines 400 to 428)

| Line | Source | Explanation |
|---:|---|---|
| 400 | `def hw_compare_json(hc):` | Starts the function `hw_compare_json`. It turns the result of `hw_compare` into the form that `facts.json` stores. `write_json` calls it (line 1001). |
| 401 | `    """hw_compare() as a record of facts.json (meta.hardware_error_records.all_intervals)."""` | Comment: the result of `hw_compare` as a record of `facts.json`, under `meta.hardware_error_records.all_intervals`. |
| 402 | `    iv_ = lambda x: dict(kernel=x['kernel'], round=x['round'], pos=x['pos'], line=x['line'],` | `iv_`: a small function for one interval. It returns the kernel, the round, the position and the line number of the I row. |
| 403 | `                         t_start_s=round(x['t_start'], 3), t_end_s=round(x['t_end'], 3), GBps=r3(x['total']))` | Ends the dictionary of line 402. `t_start_s` and `t_end_s` are rounded to 0.001 s. `GBps` is `total`, rounded to 0.001 GB/s by `r3` (line 38). |
| 404 | `    cmp_ = lambda x: dict(iv_(x['iv']), other_round=dict(iv_(x['other']), has_records=x['other_has_records']),` | `cmp_`: a small function for one result of the `cmp_` of `hw_compare`. It returns the fields of `iv_` for the interval, and the same fields for the partner under `other_round`, with the flag `has_records`. |
| 405 | `                          minus_other_round_GBps=r3(x['diff']))` | Ends the dictionary of line 404. `minus_other_round_GBps`: the value `diff`, rounded to 0.001 GB/s. `diff` was formed from the rates before rounding. |
| 406 | `    recs_ = lambda es: dict(journal_lines=[e['line'] for e in es], offset_s=sorted({e['offset_s'] for e in es}))` | `recs_`: a small function for a list of records. It returns the journal line numbers and the different values of `offset_s`, sorted. |
| 407 | `    cmax = max(hc['clean'], key=lambda x: abs(x['diff']))` | `cmax`: the entry of `clean` with the largest absolute difference. |
| 408 | `    return dict(` | Returns the dictionary that `facts.json` stores. Lines 409 to 426 give its entries. |
| 409 | `        note='view added after the numbers were seen, not part of the rules fixed before the run. Every interval '` | `note`: a fixed text of `facts.json`. This line: the view was added after the numbers were seen, and it is not part of the rules fixed before the run. |
| 410 | `             '(all kernels and positions) of the processes above that has a record, by the same rule as "kind": the '` | Text of the note: the view covers every interval (all kernels and positions) of the processes that has a record, by the same rule as the field `kind`. |
| 411 | `             'span offset_s - 1 to offset_s + 1 against the interval. other_round = the interval of the same kernel at '` | Text of the note: the rule is the span `offset_s - 1` to `offset_s + 1` against the interval. `other_round` is the interval of the same kernel (the text goes on in line 412). |
| 412 | `             'the same position in the other round of the same process. minus_other_round_GBps = rate of the interval '` | Text of the note: at the same position in the other round of the same process. `minus_other_round_GBps` is the rate of the interval (the text goes on in line 413). |
| 413 | `             'with records minus the rate of other_round. The comparison is not a test: the hypothesis that a '` | Text of the note: with records minus the rate of `other_round`. The comparison is not a test (the text goes on in line 414). |
| 414 | `             'corrected record lowers the rate of its interval is not tested',` | Text of the note: the hypothesis that a corrected record lowers the rate of its interval is not tested. |
| 415 | `        with_records=[dict(dataset=r['dataset'], tag=r['tag'], file=rel(r['file']), where=r['where'],` | `with_records`: one entry per element of `rows`. It holds the data set, the tag, the csv file in the short form of `rel` and `where`. |
| 416 | `                           used_by_the_sheet=r['used'], **recs_(r['records']), **cmp_(r)) for r in hc['rows']],` | Ends the entry of line 415: `used_by_the_sheet` (the value `used`), the fields of `recs_` for the records and the fields of `cmp_` for the interval. |
| 417 | `        at_the_border_of_two_intervals=[dict(dataset=b['dataset'], tag=b['tag'], file=rel(b['file']),` | `at_the_border_of_two_intervals`: one entry per element of `border`, with the data set, the tag and the csv file. |
| 418 | `                                             intervals=[cmp_(x) for x in b['intervals']], **recs_(b['records']))` | Continues the entry of line 417: the fields of `cmp_` for each of the two intervals, and the fields of `recs_` for the records. |
| 419 | `                                        for b in hc['border']],` | Ends the list of line 417. |
| 420 | `        positions_without_records=dict(` | `positions_without_records`: a summary of the list `clean`. |
| 421 | `            note='positions of the processes with records at which neither round has a record inside it or at its '` | `note`: a fixed text. It says that these are the positions of the processes with records at which neither round has a record inside it or at its border. |
| 422 | `                 'border. Difference = round 1 minus round 0',` | Ends the text of line 421: the difference is round 1 minus round 0. |
| 423 | `            n_positions=len(hc['clean']),` | `n_positions`: the number of entries of `clean`. |
| 424 | `            n_positions_above_1_GBps=sum(abs(x['diff']) > 1.0 for x in hc['clean']),` | `n_positions_above_1_GBps`: the number of entries whose absolute difference is above 1.0 GB/s. |
| 425 | `            largest=dict(dataset=cmax['dataset'], tag=cmax['tag'], kernel=cmax['kernel'], pos=cmax['pos'],` | `largest`: the entry of `clean` with the largest absolute difference: its data set, tag, kernel and position. |
| 426 | `                         round_1_minus_round_0_GBps=r3(cmax['diff']))))` | Ends the dictionary. `round_1_minus_round_0_GBps`: the difference of that entry, rounded to 0.001 GB/s. |

### Function `open_fw`: the saved files of the firmware settings tool (lines 429 to 451)

| Line | Source | Explanation |
|---:|---|---|
| 429 | `def open_fw():` | Starts the function `open_fw`. It reads the saved records of the firmware settings tool under `R`. The tool reads and sets firmware settings. This function reads no rate. |
| 430 | `    """Records of the firmware settings tool (uefisettings) under R: the saved settings lists, the replies of` | Comment: the records of the firmware settings tool (`uefisettings`) under `R`: the saved settings lists and the replies of the `set` calls (the list goes on in line 431). |
| 431 | `    every 'set' call, and the last reading of the memory speed setting."""` | Comment: and the last reading of the memory speed setting. |
| 432 | `    mtime = lambda p: fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(p)))` | `mtime`: a small function that gives the time of the last change of a file, as a `datetime` value in UTC, cut to whole seconds. |
| 433 | `    out = dict(lists={}, sets={})` | `out`: the result, with an empty dictionary for the lists and one for the `set` files. |
| 434 | `    # every file with one of the two names under R, so that the text can say that no other one exists` | Comment: the script collects every file with one of the two names under `R`. So the text can say that no other such file exists. |
| 435 | `    found = dict(set=[], q=[])` | `found`: the paths found, one list for `set.txt` and one for `questions.json`. |
| 436 | `    for root, dirs, names in os.walk(R):` | `os.walk` goes through the whole folder tree of `R`. For each folder it gives the path `root`, the sub folders `dirs` and the file names `names`. |
| 437 | `        dirs.sort()` | Sorts the sub folders in place. So the walk visits them in the order of their names. |
| 438 | `        for n in sorted(names):` | Loop over the file names of the folder, in sorted order. |
| 439 | `            if n == 'set.txt':` | Tests for a file with the name `set.txt`. |
| 440 | `                found['set'].append(os.path.join(root, n))` | Adds its path to the list `set`. |
| 441 | `            elif n == 'questions.json':` | Tests for a file with the name `questions.json`. |
| 442 | `                found['q'].append(os.path.join(root, n))` | Adds its path to the list `q`. |
| 443 | `    lists = dict(base=os.path.join(R, 'uefisettings-20261117', 'questions.json'),` | `lists`: the three saved lists of all settings (`questions.json`) that the script expects. `base`: the list in the folder `uefisettings-20261117`. |
| 444 | `                 x1=os.path.join(R, 'fwtest-20261117', 'x1', 'post', 'questions.json'),` | `x1`: the list in the folder `fwtest-20261117/x1/post`. |
| 445 | `                 revert=os.path.join(R, 'fwtest-20261117', 'revert', 'questions.json'))` | `revert`: the list in the folder `fwtest-20261117/revert`. |
| 446 | `    sets = dict(x1=os.path.join(R, 'fwtest-20261117', 'x1', 'set.txt'),` | `sets`: the four files with the replies of `set` calls (`set.txt`) that the script expects. `x1`: the file in the folder `fwtest-20261117/x1`. |
| 447 | `                x2=os.path.join(R, 'fwtest-20261117', 'x2', 'set.txt'),` | `x2`: the file in the folder `fwtest-20261117/x2`. |
| 448 | `                revert=os.path.join(R, 'fwtest-20261117', 'revert', 'set.txt'),` | `revert`: the file in the folder `fwtest-20261117/revert`. |
| 449 | `                dimm=os.path.join(R, 'dimm7200-20261117', 'set.txt'))` | `dimm`: the file in the folder `dimm7200-20261117`. |
| 450 | `    assert sorted(found['q']) == sorted(lists.values()), found['q']` | The `assert` stops the script when the files `questions.json` found under `R` are not exactly these three. The error shows the files found. |
| 451 | `    assert sorted(found['set']) == sorted(sets.values()), found['set']` | The `assert` stops the script when the files `set.txt` found under `R` are not exactly these four. |

### `open_fw`: the three settings lists (lines 452 to 469)

| Line | Source | Explanation |
|---:|---|---|
| 452 | `    key = lambda e: (e['name'], e['answer'], json.dumps(e['options']), e['help'])` | `key`: a small function that turns one entry of a settings list into a tuple: name, answer, options (as JSON text) and help text. |
| 453 | `    for k, path in lists.items():` | Loop over the three lists. |
| 454 | `        q = json.loads(fd._open(path).read())` | `q`: the content of the file, read as JSON. It is a list of entries. |
| 455 | `        assert all(sorted(e) == ['answer', 'help', 'name', 'options'] for e in q), path` | The `assert` requires that every entry has exactly the four keys `answer`, `help`, `name` and `options`. |
| 456 | `        val = {}` | `val`: the answers of three settings, empty at first. |
| 457 | `        for n in ('TXREQ Max', 'TXREQ Min', 'DIMM Frequency'):` | Loop over three setting names. `DIMM Frequency` is the setting of the memory speed. `TXREQ Max` and `TXREQ Min` are the settings that the `set.txt` files of the folder `fwtest-20261117` name. |
| 458 | `            hit = [e['answer'] for e in q if e['name'] == n]` | `hit`: the answers of the entries with this name. |
| 459 | `            assert len(hit) == 1, (path, n)` | The `assert` requires that the name occurs exactly once in the list. |
| 460 | `            val[n] = hit[0]` | Stores the answer under the name. |
| 461 | `        un = sum(1 for e in q if e['answer'].startswith('<ValueUnavailable'))` | `un`: the number of entries whose answer starts with `<ValueUnavailable`. |
| 462 | `        err = sum(1 for e in q if e['answer'].startswith('<VStoreError'))      # a read error of the tool, not a value` | `err`: the number of entries whose answer starts with `<VStoreError`. The comment says that this is a read error of the tool, not a value. |
| 463 | `        out['lists'][k] = dict(path=path, mtime=mtime(path), n=len(q), unavailable=un, store_error=err,` | Stores the list under its key. `path`: the path of the file. `mtime`: the file time. `n`: the number of entries. `unavailable`, `store_error`: the two counts. |
| 464 | `                               readable=len(q) - un - err,` | `readable`: the number of the other entries. |
| 465 | `                               val=val, keys=sorted(map(key, q)), order=[key(e) for e in q])` | Ends the entry of line 463. `val`: the three answers. `keys`: every entry as a tuple of `key`, sorted. `order`: the same tuples in the order of the file. |
| 466 | `    b, r = out['lists']['base'], out['lists']['revert']` | `b`, `r`: the lists `base` and `revert`. |
| 467 | `    out['same_entries'] = b['keys'] == r['keys']` | `same_entries`: true when `base` and `revert` hold the same entries after sorting. |
| 468 | `    out['same_order'] = b['order'] == r['order']` | `same_order`: true when the two files hold the entries in the same order. |
| 469 | `    out['x1_diff'] = sorted(set(out['lists']['x1']['keys']) ^ set(b['keys']))` | `x1_diff`: the entries that are in only one of `x1` and `base`. The operator `^` gives the elements that are in exactly one of two sets. |

### `open_fw`: the replies of the `set` calls and the last reading (lines 470 to 508)

| Line | Source | Explanation |
|---:|---|---|
| 470 | `    # the replies of the 'set' calls. Two forms exist: one JSON object per line, or the debug print of the tool.` | Comment: the replies of the `set` calls. The files hold two forms: one JSON object per line, or the debug print of the tool. |
| 471 | `    for k, path in sets.items():` | Loop over the four `set.txt` files. |
| 472 | `        lines = fd._open(path).read().splitlines()` | `lines`: the lines of the file. |
| 473 | `        try:` | Starts a `try` block: the next line may fail. |
| 474 | `            when, when_line = fd.dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y'), 1` | `when`: the date and time of the first line of the file. The form string reads a weekday, a month name, a day, a time on the 12-hour clock with `AM` or `PM`, the word `UTC` and a year. Example: the first line of `set.txt` in the folder `fwtest-20261117/x1` is `Tue Nov 17 03:43:50 AM UTC 2026`. `when_line` is 1, the number of that line in the file. |
| 475 | `        except ValueError:` | The case that the first line has another form. |
| 476 | `            when, when_line = None, None` | Then `when` and `when_line` are `None`. |
| 477 | `        rep = []` | `rep`: the list of the replies of the file. |
| 478 | `        block = None` | `block`: a reply of the debug print form that is still being read. `None` means that no block is open. |
| 479 | `        for ln, l in enumerate(lines, 1):` | Loop over the lines of the file. `ln` is the line number, counted from 1. |
| 480 | `            t = l.strip()` | `t`: the line without the spaces at its two ends. |
| 481 | `            if t.startswith('{"responses"'):` | Form 1: a line that starts with `{"responses"`. The whole line is one JSON object. |
| 482 | `                for x in json.loads(t)['responses']:` | Loop over the responses of the object. Each response gives one reply. |
| 483 | `                    rep.append(dict(kind='set' if 'modified' in x else 'get', name=x['question']['name'],` | The kind of the reply is `set` when the response has the key `modified`, and `get` when not. `name`: the name of the setting. |
| 484 | `                                    answer=x['question']['answer'], modified=x.get('modified'), line=ln))` | Ends the entry of line 483: the answer, the value of `modified` (`None` when the response has none) and the line number. |
| 485 | `            elif t in ('SetResponse {', 'GetResponse {'):` | Form 2, the debug print of the tool: a line `SetResponse {` or `GetResponse {` starts a block. |
| 486 | `                block = dict(kind=t[:3].lower(), name=None, answer=None, modified=None, line=None)` | `block`: a new reply. Its kind is the first 3 letters of the line in lower case, `set` or `get`. The other values are `None` for now. |
| 487 | `            elif block is not None:` | A line inside an open block. |
| 488 | `                m = re.match(r'(name\|answer): "(.*)",$', t)` | Tests for a line that starts with `name:` or `answer:`, followed by a text in double quotes and a comma. Group 1: the word `name` or `answer`. Group 2: the text between the quotes. |
| 489 | `                if m and block[m[1]] is None:` | The value is taken only when the block has none yet. So the first `name:` line and the first `answer:` line of a block are kept. |
| 490 | `                    block[m[1]] = m[2]` | Stores the text under `name` or `answer`. |
| 491 | `                    if m[1] == 'answer':` | Tests whether the line was the `answer:` line. |
| 492 | `                        block['line'] = ln` | Then the line number of the reply is the number of this line. |
| 493 | `                m = re.match(r'modified: (true\|false),$', t)` | Tests for a line `modified: true,` or `modified: false,`. Group 1 is the word `true` or `false`. |
| 494 | `                if m:` | The line fits. |
| 495 | `                    block['modified'] = m[1] == 'true'` | Stores the value of `modified` as true or false. |
| 496 | `                if t.startswith('is_translated:'):` | A line that starts with `is_translated:` ends the block. |
| 497 | `                    rep.append(block)` | Adds the block to the replies. |
| 498 | `                    block = None` | No block is open after that. |
| 499 | `        assert rep and all(x['name'] and x['answer'] for x in rep), path` | The `assert` requires at least one reply, and a name and an answer in every reply. |
| 500 | `        out['sets'][k] = dict(path=path, when=when, when_line=when_line, mtime=mtime(path), replies=rep,` | Stores the file under its key: the path, `when`, `when_line`, the file time and all replies. |
| 501 | `                              set=[x for x in rep if x['kind'] == 'set'], get=[x for x in rep if x['kind'] == 'get'])` | Ends the entry of line 500: the replies split by kind, under `set` and `get`. |
| 502 | `    fin = os.path.join(R, 'dimm7200-20261117', 'setting-final.txt')` | `fin`: the path of `setting-final.txt` in the folder `dimm7200-20261117`. |
| 503 | `    fl = fd._open(fin).read().splitlines()` | `fl`: the lines of that file. |
| 504 | `    assert len(fl) == 1, fin` | The `assert` requires that the file holds exactly one line. |
| 505 | `    out['final'] = dict(path=fin, mtime=mtime(fin), text=fl[0].strip(), answer=re.search(r'answer: "(.*)",', fl[0])[1])` | `final`: the path, the file time, the line without spaces at its ends, and `answer`, the text between the quotes after `answer:`. In the file `setting-final.txt` that line is `answer: "7200 MT/s",`. The comment of line 431 calls it the last reading of the memory speed setting. The line itself does not name the setting. |
| 506 | `    return out` | Returns the result. |

### Function `open_a2pre`: the run folder before baseline A-2 (lines 509 to 535)

| Line | Source | Explanation |
|---:|---|---|
| 509 | `def open_a2pre():` | Starts the function `open_a2pre`. It reads the times and the process header lines of one earlier run folder. This function reads no rate. |
| 510 | `    """The run folder that ended 8 s before the first process of baseline A-2: its times and its processes."""` | Comment: the run folder that ended 8 s before the first process of baseline A-2: its times and its processes. |
| 511 | `    folder = os.path.join(R, 'partA-20261113T204939Z')` | `folder`: the folder `partA-20261113T204939Z` in `R`. |
| 512 | `    T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')` | `T`: a small function that turns a text of the form `YYYY-MM-DDTHH:MM:SSZ` into a `datetime` value. |
| 513 | `    env_path = os.path.join(folder, 'env.txt')` | `env_path`: the path of `env.txt` of the folder. |
| 514 | `    env = fd._open(env_path).read().splitlines()` | `env`: the lines of that file. |
| 515 | `    m = re.match(r'## host=\S+ utc=(\S+) loadavg=(\S+) .* steps=(.*)$', env[0])` | Compares the first line of `env.txt` with the form `## host=NAME utc=TIME loadavg=LOAD ... steps=LIST`. Group 1: the start time. Group 2: the 1-minute load average. Group 3: the list of the steps after `steps=`. |
| 516 | `    end = [(ln, re.match(r'## end utc=(\S+) loadavg=(\S+) ', l)) for ln, l in enumerate(env, 1) if l.startswith('## end utc=')]` | `end`: the lines that start with `## end utc=`, each as the line number and the match. Group 1: the end time. Group 2: the 1-minute load average at the end. |
| 517 | `    assert m and len(end) == 1 and end[0][1], env_path` | The `assert` requires that the first line fits, and that exactly one end line exists and fits. |
| 518 | `    out = dict(folder=folder, env_path=env_path, start=T(m[1]), start_line=1, steps=m[3].split(),` | `out`: the result. `start`: the start time. `start_line`: 1, the number of that line in the file. `steps`: the list of the step names. |
| 519 | `               end=T(end[0][1][1]), end_line=end[0][0], load_end=float(end[0][1][2]), files={})` | Ends the dictionary of line 518. `end`: the end time. `end_line`: the line number of the end line. `load_end`: the 1-minute load average at the end. `files`: empty for now. In `env.txt` of this folder the end time is 20:50:47 UTC. The first header line of `A1.csv` of baseline A-2 gives 20:50:55 UTC. That is 8 s later. |
| 520 | `    hdr = []` | `hdr`: the header lines of all processes, empty at first. |
| 521 | `    for n in ('A5.csv', 'A6.csv'):` | Loop over the two csv files `A5.csv` and `A6.csv` of the folder. |
| 522 | `        h = fd.step_headers(os.path.join(folder, n))` | `h`: the `-- step` header lines of the file (`fd.step_headers`). Each process has one such line. |
| 523 | `        out['files'][n] = dict(path=os.path.join(folder, n), n=len(h))` | Stores the path of the file and the number of its header lines. |
| 524 | `        hdr += h` | Adds the header lines to `hdr`. |
| 525 | `    out['hdr'] = hdr` | Keeps all header lines in the result. |
| 526 | `    out['threads'] = sorted({re.search(r'--threads (\S+)', h['args'])[1] for h in hdr})` | `threads`: the different values of the option `--threads` in the arguments of these processes, sorted. |
| 527 | `    out['binaries'] = sorted({h['binary'] for h in hdr})` | `binaries`: the different binaries, sorted. In this folder `A5.csv` and `A6.csv` hold 4 and 16 header lines. All 20 processes ran `bw_new` with `--threads 1`. `facts_text.py` stops the script unless this holds for every process of the folder. |
| 528 | `    out['first'], out['last'] = min(h['utc'] for h in hdr), max(h['utc'] for h in hdr)` | `first`, `last`: the first and the last launch time of these processes. |
| 529 | `    # launches.txt of that folder: one '== file tag' line per process` | Comment: `launches.txt` of that folder holds one line of the form `== FILE TAG` per process. |
| 530 | `    lp = os.path.join(folder, 'launches.txt')` | `lp`: the path of `launches.txt`. |
| 531 | `    ll = [l.split()[1] for l in fd._open(lp) if l.startswith('== ')]` | `ll`: the second word of every line that starts with `== `. This word is the name of the csv file of the process. |
| 532 | `    out['launches_path'], out['launches_n'], out['launches_files'] = lp, len(ll), sorted(set(ll))` | Stores the path, the number of these lines (`launches_n`) and the different file names, sorted (`launches_files`). |
| 533 | `    return out` | Returns the result. `facts_text.py` computes the gap to baseline A-2 from it: the launch time of the first process of `A1.csv` minus `end`. It stops the script unless this gap is above 0 s and below 60 s. |

### Function `open_mod`: files that support the count of 12 modules (lines 536 to 567)

| Line | Source | Explanation |
|---:|---|---|
| 536 | `def open_mod():` | Starts the function `open_mod`. `collect` stores its result in `D['mod']` (line 289). No rate is read here. The facts sheet uses two values as proof of 12 modules: `MemTotal` and the DIMM sockets message. This function reads what a boot with 10 modules shows for them. |
| 537 | `    """What a boot with 10 modules shows in the two lines that the sheet uses as proof of 12 modules:` | Comment: what a boot with 10 modules shows in the two lines that the facts sheet uses as proof of 12 modules (the list goes on in line 538). |
| 538 | `    the saved journal and kernel log of the 10-module boot of 2026-11-17 04:17, and the module list that` | Comment: the sources are the saved journal and the saved Linux kernel log of the 10-module boot of 2026-11-17 04:17, and the module list (the sentence ends in line 539). |
| 539 | `    was saved in the boot of the rerun."""` | Comment: the module list was saved in the boot of the rerun. |
| 540 | `    C = os.path.join(R, 'dimm-check-20261117')` | `C`: the folder `dimm-check-20261117` in `R`. |
| 541 | `    h1 = os.path.join(C, 'h-1.txt')` | `h1`: the path of `h-1.txt`, the saved journal of the boot with 10 modules. |
| 542 | `    hl = fd._open(h1).read().splitlines()` | `hl`: the lines of that file. |
| 543 | `    out = dict(h1=h1, h1_start=fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S'),` | `out`: the result. `h1_start`: the start time of that boot, from the first 19 characters of the first line of the journal. They have the form `YYYY-MM-DDTHH:MM:SS`. |
| 544 | `               h1_dimm=int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1]), h1_dimm_line=2)` | Ends the dictionary of line 543. `h1_dimm`: the number in the message `This system has N DIMM sockets` of the second line. It is 10 in `h-1.txt`. `h1_dimm_line`: 2, the number of that line. `facts_text.py` stops the script unless `h1_dimm` is 10. |
| 545 | `    for k in ('k-1.txt', 'k-5.txt'):` | Loop over two saved Linux kernel logs: `k-1.txt` of the same 10-module boot and `k-5.txt` of the boot that started on 2026-11-09. |
| 546 | `        path = os.path.join(C, k)` | `path`: the path of the log. |
| 547 | `        kl = fd._open(path).read().splitlines()` | `kl`: the lines of the log. |
| 548 | `        hit = [(ln, re.search(r'kernel: Memory: (\d+)K/(\d+)K available', l)) for ln, l in enumerate(kl, 1)` | `hit`: the lines that hold the text `kernel: Memory: `, each as the line number and a match of the form `Memory: NUMBERK/NUMBERK available`. Group 1: the first number. Group 2: the second number. Both are in units of K. Example from `k-1.txt`: `Memory: 329221340K/334981392K available`. |
| 549 | `               if 'kernel: Memory: ' in l]` | Continues the list of line 548: the test on the text `kernel: Memory: `. |
| 550 | `        assert len(hit) == 1 and hit[0][1], path` | The `assert` requires exactly one such line, and that it has this form. |
| 551 | `        out[k[:3]] = dict(path=path, line=hit[0][0], avail_K=int(hit[0][1][1]), total_K=int(hit[0][1][2]),` | Stores the log under `k-1` or `k-5`: the path, the line number, the first number as `avail_K` and the second number as `total_K`. |
| 552 | `                          stamp=kl[hit[0][0] - 1][:15])` | Ends the entry of line 551. `stamp`: the first 15 characters of that line, which are its time stamp. `facts_text.py` stops the script unless the two `total_K` values differ by 64 x 1024 x 1024 K. `FACTS.md` states that the DIMM report reads this difference as 64 GiB (1 GiB = 1073741824 bytes), the size of two modules. |
| 553 | `    dmi = os.path.join(R, 'dimm7200-20261117', 'dmi17-7200.txt')` | `dmi`: the path of `dmi17-7200.txt`, the module list that was saved in the boot of the rerun. `facts_text.py` calls it the output of `dmidecode`, type 17. `dmidecode` prints the hardware table of the firmware. |
| 554 | `    dl = fd._open(dmi).read().splitlines()` | `dl`: the lines of that file. |
| 555 | `    out['dmi'] = dict(path=dmi, mtime=fd.dt.datetime.utcfromtimestamp(int(os.path.getmtime(dmi))),` | Stores the path and the file time `mtime` (UTC, whole seconds). `facts_text.py` stops the script unless this time lies inside the time span of row 0 of `boots.txt`. The next lines count lines of the file. |
| 556 | `                      devices=sum(1 for l in dl if l.strip() == 'Memory Device'),` | `devices`: the lines that are equal to `Memory Device`, compared without the spaces and tabs at their two ends. The file holds one such entry per memory module. |
| 557 | `                      speed=sum(1 for l in dl if l.strip() == 'Configured Memory Speed: 7200 MT/s'),` | `speed`: the lines that are equal to `Configured Memory Speed: 7200 MT/s`. |
| 558 | `                      size=sum(1 for l in dl if l.strip() == 'Size: 32 GB'),` | `size`: the lines that are equal to `Size: 32 GB`. |
| 559 | `                      volatile=sum(1 for l in dl if l.strip() == 'Volatile Size: 32 GB'),` | `volatile`: the lines that are equal to `Volatile Size: 32 GB`. |
| 560 | `                      size_any=sum(1 for l in dl if 'Size: 32 GB' in l))` | `size_any`: the lines that hold the text `Size: 32 GB` at any place. This count includes the lines of `size` and of `volatile`. In `dmi17-7200.txt` the five counts are 12, 12, 12, 12 and 24. `facts_text.py` stops the script unless `devices`, `speed`, `size` and `volatile` are all 12. |
| 561 | `    t6 = fd._open(os.path.join(R, 'dimm7200-20261117', 'try6.txt')).read().splitlines()` | `t6`: the lines of `try6.txt`, read once more. |
| 562 | `    m = [(ln, re.fullmatch(r'modules=(\d+)', l)) for ln, l in enumerate(t6, 1) if l.startswith('modules=')]` | `m`: the lines that start with `modules=`, each as the line number and a match. `re.fullmatch` requires that the whole line is `modules=` and a number. Group 1 is the number. |
| 563 | `    assert len(m) == 1 and m[0][1]` | The `assert` requires exactly one such line of this form. |
| 564 | `    out['try6_modules'], out['try6_modules_line'] = int(m[0][1][1]), m[0][0]` | `try6_modules`: the number. `try6_modules_line`: the line number. In `try6.txt` the sixth line reads `modules=24`. `facts_text.py` stops the script unless the number equals `size_any`. The module count of the records (12) does not come from this line. `collect` takes it from the DIMM sockets line of the same file (line 56). |
| 565 | `    return out` | Returns the result. |

### Function `open_probe13`: `probe.txt` and `one-thread.csv` of the run of 2026-11-13 (lines 568 to 596)

| Line | Source | Explanation |
|---:|---|---|
| 568 | `def open_probe13(kfolder):` | Starts the function `open_probe13`. `collect` calls it with the folder `kernels-20261113T181222Z`, the folder of baseline A-1 (line 195). No rate is read here. |
| 569 | `    """probe.txt and one-thread.csv of the 2026-11-13 run: checksums, times, one-thread phase."""` | Comment: the function reads `probe.txt` and `one-thread.csv` of the run of 2026-11-13: checksums, times and the one-thread phase. The one-thread phase is the first part of that test: processes with one thread, run before the 120-thread part. |
| 570 | `    path = os.path.join(kfolder, 'probe.txt')` | `path`: the path of `probe.txt` of that folder. |
| 571 | `    lines = fd._open(path).read().splitlines()` | `lines`: the lines of the file. |
| 572 | `    sha, sha_line = {}, {}` | `sha`: a dictionary from name to sha256. `sha_line`: a dictionary from name to line number. |
| 573 | `    for ln, l in enumerate(lines, 1):` | Loop over the lines. `ln` is the line number, counted from 1. |
| 574 | `        m = re.match(r'^([0-9a-f]{64})  (\S+)$', l)` | Tests for a line that holds 64 hexadecimal digits, two spaces and a name, and nothing more. Group 1: the digits. Group 2: the name. |
| 575 | `        if m:` | The line fits. |
| 576 | `            sha[m[2]] = m[1]` | Stores the sha256 under the name. No check of this script uses the entries of the source files. In this `probe.txt` the fifteenth line records the sha256 `c1406e02...` for `bandwidth.c`. The local `bandwidth.c` in the folder `kernels-2026-11-13` has another sha256, `f1985072...`. That is the value in `probe.txt` of the run of 18:32:18 UTC on the same day, which built the binaries and timed nothing. Both records give the same sha256 for the binary `bw_new` (`fd7c14df...`). So the machine code is not in doubt. The two texts differ in comment lines only. No code line differs [Ref13]. |
| 577 | `            sha_line[m[2]] = ln` | Stores the line number under the name. In this `probe.txt` the eighteenth, the nineteenth and the twentieth line hold the values of `run_kernels.sh`, `bw_old` and `bw_new`. The checks `sha-bw` and `A-args` use them. |
| 578 | `    T = lambda s: fd.dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')` | `T`: a small function that turns a time text such as `2026-11-13T18:12:22Z` into a `datetime` value. The example is the time in the first line of this `probe.txt`. |
| 579 | `    out = dict(path=path, sha=sha, sha_line=sha_line)` | `out`: the result, with the path and the two dictionaries. |
| 580 | `    for ln, l in enumerate(lines, 1):` | Loop over the lines once more. It finds three lines that start with `##`. |
| 581 | `        m = re.match(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+)', l)` | Tests for the line that starts with `## host=`. Group 1: the start time. Groups 2 to 4: the three load averages after `load_before=`. Group 5: the number of logins. |
| 582 | `        if m:` | The line fits. |
| 583 | `            out['utc'], out['load_before'], out['logins'] = T(m[1]), (m[2], m[3], m[4]), int(m[5])` | Stores the start time as `utc`, the three load averages as texts in `load_before`, and the number of logins. |
| 584 | `        m = re.match(r'## one-thread done load=(\S+) \S+ \S+ utc=(\S+)', l)` | Tests for the line that starts with `## one-thread done`. Group 1: the 1-minute load average. Group 2: the time. `run_kernels.sh` writes this line at the end of the one-thread phase. |
| 585 | `        if m:` | The line fits. |
| 586 | `            out['one_done_load'], out['one_done_utc'], out['one_done_line'] = float(m[1]), T(m[2]), ln` | Stores them as `one_done_load` and `one_done_utc`, with the line number. |
| 587 | `        m = re.match(r'## load_after=(\S+) \S+ \S+ utc=(\S+)', l)` | Tests for the line that starts with `## load_after=`. Group 1: the 1-minute load average. Group 2: the time. `run_kernels.sh` writes this line after the 120-thread part. |
| 588 | `        if m:` | The line fits. |
| 589 | `            out['load_after'], out['utc_after'], out['after_line'] = float(m[1]), T(m[2]), ln` | Stores them as `load_after` and `utc_after`, with the line number. |
| 590 | `    out['has_memtotal'] = any('MemTotal' in l for l in lines)` | `has_memtotal`: whether any line of the file holds the text `MemTotal`. |
| 591 | `    out['has_boot_id'] = any('boot_id' in l for l in lines)` | `has_boot_id`: whether any line holds the text `boot_id`. Both values are false for this `probe.txt`. `facts_text.py` stops the script if one of them is true. |
| 592 | `    one = os.path.join(kfolder, 'one-thread.csv')` | `one`: the path of `one-thread.csv` of the same folder, the result file of the one-thread phase. |
| 593 | `    hdr = [l for l in fd._open(one) if l.startswith('-- binary')]` | `hdr`: the lines of that file that start with `-- binary`. Only these header lines are kept. No interval row of this file is used. So no one-thread rate enters the records. |
| 594 | `    out['one_path'], out['one_n'] = one, len(hdr)` | `one_path`: the path. `one_n`: the number of header lines (192 in `one-thread.csv`). This is the number of processes of the one-thread phase. |
| 595 | `    out['one_first'] = re.search(r'utc (\S+)', hdr[0])[1]` | `one_first`: the time of day after the word `utc` in the first header line, as text. |
| 596 | `    out['one_last'] = re.search(r'utc (\S+)', hdr[-1])[1]` | `one_last`: the same for the last header line. |

### `open_probe13`: the journal of that boot and the time spans of the baselines (lines 597 to 633)

| Line | Source | Explanation |
|---:|---|---|
| 597 | `    # journal of that boot (saved 2026-11-17): start, module line, error records during the run` | Comment: the journal of that boot, saved on 2026-11-17: its start, the line of the module count and the error records during the run. |
| 598 | `    h5 = os.path.join(R, 'dimm-check-20261117', 'h-5.txt')` | `h5`: the path of `h-5.txt` in the folder `dimm-check-20261117`, the saved journal of the boot that started on 2026-11-09. The test of 2026-11-13 ran in that boot. The rules file says that every baseline ran in that boot [Ref3]. |
| 599 | `    hl = fd._open(h5).read().splitlines()` | `hl`: the lines of the journal. |
| 600 | `    out['h5'] = h5` | Keeps the path in the result. |
| 601 | `    out['boot_start'] = fd.dt.datetime.strptime(hl[0][:19], '%Y-%m-%dT%H:%M:%S')` | `boot_start`: the start time of the boot, from the first 19 characters of the first line. |
| 602 | `    out['boot_dimm'] = int(re.search(r'This system has (\d+) DIMM sockets', hl[1])[1])` | `boot_dimm`: the number in the DIMM sockets message of the second line (12 in `h-5.txt`). `facts_text.py` stops the script unless it is 12. |
| 603 | `    day = out['utc'].strftime('%Y-%m-%dT')` | `day`: the date of the test as text in the form `YYYY-MM-DDT`, from the start time of `probe.txt`. |
| 604 | `    first_rec = next(i for i, l in enumerate(hl, 1) if '[Hardware Error]' in l)` | `first_rec`: the number of the first line of the journal that holds the text `[Hardware Error]`. |
| 605 | `    out['first_record_line'] = first_rec` | Keeps it as `first_record_line`. |
| 606 | `    out['first_record_utc'] = fd.dt.datetime.strptime(hl[first_rec - 1][:19], '%Y-%m-%dT%H:%M:%S')` | `first_record_utc`: the time of that line, from its first 19 characters. |
| 607 | `    lo, hi = out['one_done_utc'], out['utc_after']` | `lo`, `hi`: the end of the one-thread phase and the time of the `load_after` line. This span is the 120-thread part of baseline A-1. |
| 608 | `    out['records_in_120'] = sum(1 for l in hl if l.startswith(day) and '[Hardware Error]' in l` | `records_in_120`: the number of lines of the day of the test that hold `[Hardware Error]` and whose time lies from `lo` to `hi`. The code counts lines here, and one record has several such lines. With `h-5.txt` and the two times of this `probe.txt` the count is 0. |
| 609 | `                                and lo <= fd.dt.datetime.strptime(l[:19], '%Y-%m-%dT%H:%M:%S') <= hi)` | Ends the expression of line 608: the test on the time, with both ends included. |
| 610 | `    # the same journal for the baselines A-2 and A-3 (one record = one line 'Hardware error from APEI ...')` | Comment: the same journal is read for the baselines A-2 and A-3. One record is one line `Hardware error from APEI ...`. |
| 611 | `    errs = fd.read_error_records(h5)` | `errs`: every hardware error record of the journal (`fd.read_error_records`), one per line `Hardware error from APEI ...`. The journal `h-5.txt` holds 321 records. |
| 612 | `    pfolder = os.path.join(R, 'partA-20261113T205055Z')` | `pfolder`: the folder `partA-20261113T205055Z` in `R`. |
| 613 | `    h1 = fd.step_headers(os.path.join(pfolder, 'A1.csv'))` | `h1`: the `-- step` header lines of `A1.csv` (`fd.step_headers`). Each process has one such line. The line gives the launch time of the process. |
| 614 | `    h2 = fd.step_headers(os.path.join(pfolder, 'A2.csv'))` | `h2`: the header lines of `A2.csv`. |
| 615 | `    h3 = fd.step_headers(os.path.join(pfolder, 'A3.csv'))` | `h3`: the header lines of `A3.csv`. |
| 616 | `    out['a2_csv2'] = os.path.join(pfolder, 'A2.csv')` | `a2_csv2`: the path of `A2.csv`. |
| 617 | `    out['a2_window'] = (h1[0]['utc'], h2[0]['utc'])` | `a2_window`: from the launch of the first process of `A1.csv` to the launch of the first process of `A2.csv`. This is the time span of baseline A-2. |
| 618 | `    out['a2_first'] = h1[0]` | `a2_first`: the header line of the first process of `A1.csv`. |
| 619 | `    # The first A-3 process is the first process of A3.csv. run_partA.sh ran the steps in the order of` | Comment: the first A-3 process is the first process of `A3.csv`. The script `run_partA.sh` ran the steps in the order of (the sentence goes on in line 620). |
| 620 | `    # 'steps=' in env.txt, so the process directly before it is the last process of A2.csv.` | Comment: the list `steps=` in `env.txt`. So the process directly before the first A-3 process is the last process of `A2.csv`. |
| 621 | `    steps = re.search(r' steps=(.*)$', fd._open(os.path.join(pfolder, 'env.txt')).read().splitlines()[0])[1].split()` | `steps`: the list of the step names after `steps=` in the first line of `env.txt` of `pfolder`. That line holds the list `steps=A1 A2 A3 A4`. |
| 622 | `    assert steps.index('A2') + 1 == steps.index('A3') and h3[0]['line'] == 1 and h2[-1]['utc'] < h3[0]['utc']` | The `assert` stops the script unless three things hold. A3 directly follows A2 in that list. The first header line of `A3.csv` is the first line of the file. The last process of `A2.csv` was launched before the first process of `A3.csv`. |
| 623 | `    out['a3_prev'] = h2[-1]` | `a3_prev`: the last process of `A2.csv`. `write_json` names it in the text of the field `kernel_before` (lines 931 to 936). |
| 624 | `    out['a3_first'] = h3[0]` | `a3_first`: the first process of `A3.csv`. |
| 625 | `    out['a2_records'] = []` | `a2_records`: the hardware error records during baseline A-2, empty at first. |
| 626 | `    for e in errs:` | Loop over all records of the journal. |
| 627 | `        if out['a2_window'][0] <= e['utc'] <= out['a2_window'][1]:` | Tests whether the time of the record lies in `a2_window`, both ends included. |
| 628 | `            i = max(k for k, h in enumerate(h1) if h['utc'] <= e['utc'])` | `i`: the place of the last process of `A1.csv` that was launched at or before the time of the record. |
| 629 | `            out['a2_records'].append(dict(e, proc=h1[i], next=h1[i + 1] if i + 1 < len(h1) else None))` | Adds the record with two more fields. `proc`: that process. `next`: the process after it, or `None` when it is the last one. The journal `h-5.txt` has 4 records in this time span. |
| 630 | `    i3 = [k for k, h in enumerate(h3) if re.fullmatch(r'onebuf-ms500-[123]', h['tag'])]` | `i3`: the places of the processes of `A3.csv` whose tag is `onebuf-ms500-1`, `onebuf-ms500-2` or `onebuf-ms500-3`. These three processes are baseline A-3. |
| 631 | `    out['a3_window'] = (h3[i3[0]]['utc'], h3[i3[-1] + 1]['utc'])` | `a3_window`: from the launch of the first of them to the launch of the process after the last of them. The loop of `run_partA.sh` starts a `twobuf-ms500` process after each of them. So the window also covers such processes. |
| 632 | `    out['a3_records'] = [e for e in errs if out['a3_window'][0] <= e['utc'] <= out['a3_window'][1]]` | `a3_records`: the records whose time lies in `a3_window`, both ends included. The journal `h-5.txt` has none in this time span. |
| 633 | `    out['n_records_boot'] = len(errs)` | `n_records_boot`: the number of all records of the journal. |

### `open_probe13`: the Linux release and the saved machine settings (lines 634 to 650)

| Line | Source | Explanation |
|---:|---|---|
| 634 | `    out['journal_release'] = re.search(r'Linux version (\S+)', hl[0])[1]` | `journal_release`: the Linux kernel release of that boot, the word after `Linux version` in the first line of the journal. `facts_text.py` stops the script unless it equals the release of the rerun. |
| 635 | `    # machine settings saved in the same boot (2026-11-17 03:43 UTC, before the firmware test)` | Comment: machine settings that were saved in the same boot, on 2026-11-17 at 03:43 UTC, before the firmware test. |
| 636 | `    pre = os.path.join(R, 'fwtest-20261117', 'pre')` | `pre`: the folder `fwtest-20261117/pre` in `R`. |
| 637 | `    rd = lambda n: fd._open(os.path.join(pre, n)).read().strip()` | `rd`: a small function that returns the text of one file of that folder, without spaces and line ends at its two ends. |
| 638 | `    out['pre'] = dict(folder=pre, when_path=os.path.join(pre, 'when.txt'), cmdline_path=os.path.join(pre, 'cmdline.txt'),` | `out['pre']`: the saved settings. This line: the folder and the paths of `when.txt` and `cmdline.txt`. |
| 639 | `                      gov_path=os.path.join(pre, 'gov.txt'), thp_path=os.path.join(pre, 'thp.txt'),` | Continues the dictionary of line 638: the paths of `gov.txt` and `thp.txt`. A governor is the Linux policy that sets the CPU frequency. `scaling_cur_freq` is a file of Linux that gives the current frequency of a CPU in kHz (Linux kernel documentation, page "CPU Performance Scaling"). So the value 2800000 of the log of `go.sh` is 2.8 GHz. The same page says that in most cases the value is the frequency that Linux last requested from the hardware. It also says that the CPU may run at another frequency. |
| 640 | `                      when=fd.dt.datetime.strptime(rd('when.txt'), '%a %b %d %I:%M:%S %p UTC %Y'),` | `when`: the time of the save, from `when.txt` (2026-11-17 03:43:42 UTC). The form string reads the output of `date -u`: weekday, month name, day, time on the 12-hour clock with `AM` or `PM`, the word `UTC` and the year. `facts_text.py` stops the script unless this time lies in the boot of the 8000 MT/s baselines. |
| 641 | `                      cmdline=rd('cmdline.txt'), gov=[l.strip() for l in rd('gov.txt').splitlines()], thp=rd('thp.txt'))` | Ends the dictionary of line 638. `cmdline`: the Linux boot arguments, from `cmdline.txt`. `gov`: the two lines of `gov.txt`. In this file they read `128 performance` and `2800000`. `thp`: the huge-page setting of Linux, from `thp.txt` (`[always] madvise never` in this file). `facts_text.py` stops the script unless three things hold. `cmdline` equals the boot arguments in the `== cmdline` line of the log of `go.sh`. The first line of `gov` is `128`, a space and the governor name of that log, and the second line is the value `scaling_cur_freq` of CPU 0 of that log. `thp` equals the `enabled` value in the `== thp` line of that log. |
| 642 | `    k5 = os.path.join(R, 'dimm-check-20261117', 'k-5.txt')` | `k5`: the path of `k-5.txt`, the saved Linux kernel log of that boot. |
| 643 | `    kl = fd._open(k5).read().splitlines()` | `kl`: the lines of that log. |
| 644 | `    out['k5'], out['k5_last_line'], out['k5_last'] = k5, len(kl), kl[-1][:15]` | `k5_last_line`: the number of lines of the log. `k5_last`: the first 15 characters of its last line, which are its time stamp (`Nov 17 03:44:00` in `k-5.txt`). |
| 645 | `    q = os.path.join(R, 'uefisettings-20261117', 'questions.json')` | `q`: the path of `questions.json` in the folder `uefisettings-20261117`, the saved list of firmware settings. |
| 646 | `    m = re.search(r'"name":"DIMM Frequency","answer":"(\d+) MT/s"', fd._open(q).read())` | Searches the text of that file for the entry with the name `DIMM Frequency`. Group 1 is the number of its answer, a speed in MT/s. |
| 647 | `    out['q_path'], out['q_speed'] = q, int(m[1])` | `q_path`: the path. `q_speed`: the memory speed of that entry, as a number. It is 8000 MT/s in this file. |
| 648 | `    return out` | Returns the result. |

### Function `run_checks`: the list of checks and the helpers `chk` and `per` (lines 651 to 667)

| Line | Source | Explanation |
|---:|---|---|
| 651 | `# ----------------------------------------------------------------------------- integrity checks` | Comment: a divider line. The block below holds the integrity checks. |
| 653 | `def run_checks(D):` | Starts the function `run_checks`. `main` calls it after `collect` (line 1036). It appends 27 checks to the list `D['checks']` in a fixed order. It changes no record. A check that fails does not stop this function. The stop comes later, in `render` (line 1037). |
| 654 | `    """Integrity checks. One line of text per check; the line names every folder that it covers."""` | Comment: the integrity checks. Each check gives one line of text, and the line names every folder that it covers. |
| 655 | `    C = D['checks']` | `C`: the list of checks, `D['checks']`. |
| 656 | `    recs = D['recs']` | `recs`: the list of all records. |
| 657 | `    try6 = D['try6']` | `try6`: the values of `try6.txt`. |
| 658 | `    A, X = D['A'], D['X']` | `A`: the 3 part A folders of the rerun. `X`: the 9 bwx12 folders of the rerun. |
| 659 | `    yn = lambda b: 'yes' if b else 'NO'` | `yn`: a small function that turns a truth value into the text `yes` or `NO`. |
| 661 | `    def chk(key, ok, text):` | Starts the nested function `chk`. It appends one check. |
| 662 | `        C.append(dict(key=key, ok=bool(ok), text=text))` | The check holds a key such as `I-agg`, the pass flag `ok` (true or false) and one line of text. |
| 664 | `    def per(items, fn):` | Starts the nested function `per`. It builds a text with one value per folder of the rerun. |
| 665 | `        """'T72L1 10, T72L2 10, ...' for a list of rerun folders."""` | Comment: the text has the form `T72L1 10, T72L2 10, ...` for a list of rerun folders. |
| 666 | `        return ', '.join('%s %s' % (i['tag'], fn(i)) for i in items)` | For each folder the text holds its tag and the value that the function `fn` returns for it. The parts are joined with a comma and a space. |

### Checks 1 to 5: the two logs, the boot id, `MemTotal`, logins and marker file (lines 668 to 694)

| Line | Source | Explanation |
|---:|---|---|
| 668 | `    # logs` | Comment: the checks of the logs. |
| 669 | `    for name in ('go', 'go2'):` | Loop over the two driver logs. It gives the checks `log-go` and `log-go2`. |
| 670 | `        lg = D['logs'][name]` | `lg`: the values of one log, from `fd.read_log`. |
| 671 | `        chk('log-' + name, lg['alldone'] and not lg['failed'],` | The check passes when the log holds a line `ALLDONE` and no line that starts with `FAILED`. |
| 672 | `            '%s: the last line is ALLDONE: %s. Lines that start with FAILED: %d'` | Text of the check: the path of the log, whether the last line is `ALLDONE`, and the number of lines that start with `FAILED`. |
| 673 | `            % (rel(lg['path']), yn(lg['lines'][-1] == 'ALLDONE'), len(lg['failed'])))` | Ends the call of line 671: the three values of the text. The path has the short form of `rel`. The pass flag tests for a line `ALLDONE` at any place. The text says whether it is the last line. |
| 674 | `    # boot id and MemTotal of every state line and every probe.txt` | Comment: the boot id and `MemTotal` of every state line and of every `probe.txt`. |
| 675 | `    states = D['logs']['go']['states'] + D['logs']['go2']['states']` | `states`: the state lines of both logs. The build of 2026-11-17 has 18 of them [Ref9]. |
| 676 | `    boots = {s['boot'] for s in states} \| {a['probe']['boot'] for a in A}` | `boots`: the different boot ids of all state lines and of the `probe.txt` files of part A. The operator between the two sets joins them. |
| 677 | `    mems = {s['memtotal_kB'] for s in states} \| {a['probe']['memtotal_kB'] for a in A} \| \` | `mems`: the different `MemTotal` values of all state lines and of the start of each `probe.txt`. The backslash continues the statement on the next line. |
| 678 | `           {a['probe']['memtotal_after_kB'] for a in A}` | Ends the statement of line 677: the `MemTotal` values of the end of each `probe.txt`. So each `probe.txt` gives two values, one from the start and one from the end of its session. |
| 679 | `    chk('boot', boots == {try6['boot']},` | Check `boot`. It passes when all these boot ids are one value, and this value is the boot id of `try6.txt`. `try6.txt` is the record of 12 modules at 7200 MT/s. So a pass shows that every step of the rerun ran in the boot of that record. |
| 680 | `        'boot id: %d state lines of the two logs and %d probe.txt files hold %d distinct value(s). Equal to line 2 of '` | Text of the check: the number of state lines, the number of `probe.txt` files and the number of different boot ids. |
| 681 | `        'try6.txt: %s' % (len(states), len(A), len(boots), yn(boots == {try6['boot']})))` | Ends the call of line 679: the end of the text (whether the value equals the second line of `try6.txt`) and its four values. |
| 682 | `    chk('memtotal', mems == {try6['memtotal_kB']},` | Check `memtotal`. It passes when all these `MemTotal` values are one value, equal to `MemTotal` of `try6.txt`. |
| 683 | `        'MemTotal: %d state lines and %d probe.txt values (start and end of each session) hold %d distinct value(s): '` | Text of the check: the number of state lines, the number of `probe.txt` values (start and end of each session) and the number of different values. |
| 684 | `        '%s kB. Equal to line %d of try6.txt: %s'` | Continues the text: the values in kB, and whether they equal the `MemTotal` line of `try6.txt`. |
| 685 | `        % (len(states), 2 * len(A), len(mems), ', '.join(str(m) for m in sorted(mems)), try6['memtotal_line'],` | Continues the call of line 682: the values of the text. The number of `probe.txt` values is 2 x the number of part A folders. |
| 686 | `           yn(mems == {try6['memtotal_kB']})))` | Ends the call of line 682: the last value, `yes` or `NO`. |
| 687 | `    ok = (all(s['logins'] == 0 and s['marker'] == 'absent' for s in states)` | `ok` for check `logins`, first condition: every state line shows 0 logins and the marker `absent`. The marker file is `/tmp/positron-perf.RUNNING`. |
| 688 | `          and all(a['probe']['logins'] == 0 for a in A) and all(x['launches'][0]['logins'] == 0 for x in X))` | Ends the expression of line 687. Second condition: every `probe.txt` of part A shows 0 logins. Third condition: the `launch` line of every bwx12 folder shows 0 logins. |
| 689 | `    chk('logins', ok,` | Check `logins`. It passes when all three conditions hold. |
| 690 | `        'logins and marker file: logins = 0 and marker "absent" in %d of %d state lines. Logins = 0 in %d of %d '` | Text of the check: the number of state lines with 0 logins and the marker `absent`, out of all state lines. The build of 2026-11-17 gives `18 of 18 state lines` [Ref9]. |
| 691 | `        'probe.txt files and in %d of %d launch lines'` | Continues the text: the same count for the `probe.txt` files and for the `launch` lines. |
| 692 | `        % (sum(s['logins'] == 0 and s['marker'] == 'absent' for s in states), len(states),` | Continues the call of line 689: the two numbers for the state lines. |
| 693 | `           sum(a['probe']['logins'] == 0 for a in A), len(A),` | Continues the call of line 689: the two numbers for the `probe.txt` files. |
| 694 | `           sum(x['launches'][0]['logins'] == 0 for x in X), len(X)))` | Ends the call of line 689: the two numbers for the `launch` lines. |

### Checks 6 and 7: shape and process order of part A (lines 695 to 708)

| Line | Source | Explanation |
|---:|---|---|
| 695 | `    # part A: 24 processes x 3 intervals, same process order as on 2026-11-13` | Comment: part A must hold 24 processes x 3 intervals, in the same process order as on 2026-11-13. |
| 696 | `    order13 = [(p['binary'], p['kernel'], p['round']) for p in D['base']['A-1']['procs']]` | `order13`: the binary, the kernel and the round of each process of baseline A-1, in file order. |
| 697 | `    shape = lambda a: (len(a['procs']), sorted({len(p['iv']) for p in a['procs']}),` | `shape`: a small function that returns three values of one `threads120.csv`: the number of processes, the different numbers of interval rows per process, and (in line 698) a third value. |
| 698 | `                       sorted({iv['threads'] for p in a['procs'] for iv in p['iv']}))` | Ends the function of line 697. The third value: the different values of the column `threads` of the interval rows. |
| 699 | `    ok = all(shape(a) == (24, [3], [120]) and all([iv['rep'] for iv in p['iv']] == [0, 1, 2] for p in a['procs'])` | `ok` for check `A-shape`: every file has 24 processes with 3 interval rows each, the column `threads` is 120 in every row, and the column `rep` of each process reads 0, 1, 2. |
| 700 | `             for a in A)` | Ends the expression of line 699: the test covers every part A folder. |
| 701 | `    chk('A-shape', ok, 'part A, processes x intervals per threads120.csv (expected 24 x 3, 120 threads in every row): '` | Check `A-shape`. Its text starts with the expected values: 24 x 3, and 120 threads in every row. |
| 702 | `        + per(A, lambda a: '%d x %s, %d rows, threads %s' % (shape(a)[0], '/'.join(map(str, shape(a)[1])),` | Continues the text with one part per folder: the number of processes, the numbers of interval rows per process, the number of all interval rows and the thread counts. |
| 703 | `                                                              sum(len(p['iv']) for p in a['procs']),` | Continues the call of line 701: the number of all interval rows of the file. |
| 704 | `                                                              '/'.join(map(str, shape(a)[2])))))` | Ends the call of line 701: the thread counts, joined with `/`. |
| 705 | `    same = lambda a: [(p['binary'], p['kernel'], p['round']) for p in a['procs']] == order13` | `same`: a small function that tests whether the processes of one file have the same order of binary, kernel and round as `order13`. |
| 706 | `    chk('A-order', all(same(a) for a in A),` | Check `A-order`. It passes when this holds for every part A file. With both checks passed, each session holds 2 processes x 3 interval rows of `bw_old` with the kernel `read`, and the same of `bw_new`. That gives 18 interval rows per read kernel in the 3 sessions. |
| 707 | `        'part A, order of the 24 processes (binary, kernel, round) equal to threads120.csv of 2026-11-13: '` | Text of the check: the order of the 24 processes (binary, kernel, round) is compared with `threads120.csv` of 2026-11-13. |
| 708 | `        + per(A, lambda a: yn(same(a))))` | Ends the call of line 706: `yes` or `NO` per folder. |

### Checks 8 to 14: rows of the bwx12 files of the rerun, and the T rows against the I row (lines 709 to 740)

| Line | Source | Explanation |
|---:|---|---|
| 709 | `    # bwx12 folders of the rerun` | Comment: the bwx12 folders of the rerun. |
| 710 | `    want_i = dict(L=10, I=10, C=6)` | `want_i`: the expected number of I rows per csv: 10 for parts L and I (2 rounds x 5 kernels) and 6 for part C (2 rounds x 3 kernels). |
| 711 | `    chk('I-rows', all(len(x['sec']['I']) == want_i[x['part']] == len(x['ivs']) for x in X),` | Check `I-rows`. The number of I rows of each csv must equal the expected number. It must also equal the number of intervals that `fd.bwx_intervals` built from the T rows. |
| 712 | `        '"I" rows per bwx12 csv (expected 10 for parts L and I, 6 for part C): ' + per(X, lambda x: len(x['sec']['I'])))` | Text of the check: the expected numbers, and the number of I rows per folder. |
| 713 | `    chk('rc', all(len(x['launches']) == 1 and x['launches'][0]['rc'] == '0' for x in X),` | Check `rc`. `launches.txt` of each folder must hold exactly one launch entry, and its exit status must be `0`. |
| 714 | `        'launches.txt, one launch line with "rc 0" per folder: '` | Text of the check: one `launch` line with `rc 0` per folder. |
| 715 | `        + per(X, lambda x: 'rc ' + '/'.join(str(l['rc']) for l in x['launches'])))` | Ends the call of line 713: the exit statuses of each folder, joined with `/`. |
| 716 | `    chk('stderr', all(x['stderr_bytes'] == 0 for x in X),` | Check `stderr`. `stderr.txt` of each folder must hold 0 bytes. |
| 717 | `        'stderr.txt, bytes per folder (expected 0): ' + per(X, lambda x: x['stderr_bytes']))` | Text of the check: the bytes per folder, with the expected value 0. |
| 718 | `    ok6456 = lambda x: sum(iv['is_64_56'] and iv['threads'] == 120 for iv in x['ivs'])` | `ok6456`: a small function that counts the intervals of one folder that have 120 T rows and pass the 64+56 test: 64 threads on the CPUs 0 to 63 and 56 threads on the CPUs 64 to 119, on 120 different CPUs. |
| 719 | `    chk('6456', all(ok6456(x) == len(x['ivs']) for x in X),` | Check `6456`. It passes when every interval of every folder is counted. |
| 720 | `        'intervals with 120 threads = 64 on CPUs 0-63 + 56 on CPUs 64-119, on 120 different CPUs: '` | Text of the check: it names the placement of the 120 threads. |
| 721 | `        + per(X, lambda x: '%d of %d' % (ok6456(x), len(x['ivs']))))` | Ends the call of line 719: the count per folder, in the form `N of M`. |
| 722 | `    nflag = lambda x: sum(iv['flagged'] for iv in x['ivs'])` | `nflag`: a small function that gives the number of flagged T rows of one folder. |
| 723 | `    D['n_T_rows'] = sum(iv['threads'] for x in X for iv in x['ivs'])` | `D['n_T_rows']`: the number of T rows of all intervals of the 9 files. The build of 2026-11-17 has 8880 of them, which is 74 intervals x 120 threads [Ref9]. |
| 724 | `    vals = sorted({f for x in X for iv in x['ivs'] for f in iv['flags']})` | `vals`: the different values of the flags column over these T rows, sorted. |
| 725 | `    chk('flags', vals == ['-'],` | Check `flags`. It passes when `-` is the only value. Neither this check nor check `6456` removes a row. A T row with a flag stays in the sum of its interval. |
| 726 | `        'flags column of the T rows (one row per thread and interval): %d rows in the 9 files, distinct values %s, '` | Text of the check: the number of T rows in the 9 files and the different flag values. |
| 727 | `        'rows that are not "-": %s' % (D['n_T_rows'], vals, per(X, nflag)))` | Ends the call of line 725: the number of rows per folder whose flag is not `-`, and the three values of the text. |
| 728 | `    huge = lambda x: sum(1 for p in x['sec']['P'] if p[5] == p[4])` | `huge`: a small function that counts the P rows of one folder in which `kB_huge` equals `kB_total`. In such a row the whole buffer is on huge pages. A P row is stored as a tuple of the values after the leading `P`. Counted from 0, its places 4, 5 and 7 hold the columns `kB_total`, `kB_huge` and `thp_fault_fallback`. |
| 729 | `    tot = sorted({p[4] for x in X for p in x['sec']['P']})` | `tot`: the different values of `kB_total`. The only value in the build of 2026-11-17 is 262144 kB [Ref9]. With 1 kB = 1024 bytes this is 256 MiB (1 MiB = 1048576 bytes), the size of one buffer. |
| 730 | `    fb = sorted({p[7] for x in X for p in x['sec']['P']})` | `fb`: the different values of `thp_fault_fallback`. Linux adds 1 to this counter when a page fault cannot get a huge page and uses small pages in its place [Ref15]. The counter is for the whole system [Ref12]. |
| 731 | `    D['P_kB'] = tot` | Keeps `tot` as `D['P_kB']` for the text of `FACTS.md`. |
| 732 | `    chk('P-rows', all(huge(x) == len(x['sec']['P']) > 0 for x in X),` | Check `P-rows`. It passes when every folder has at least one P row and `kB_huge` equals `kB_total` in all of its P rows. |
| 733 | `        '"P" rows (one per thread before the first interval and after each interval): kB_total %s in all rows. Rows '` | Text of the check: the values of `kB_total`. The text also says that the runner writes one P row per thread before the first interval and after each interval. |
| 734 | `        'with kB_huge equal to kB_total: %s. Values of thp_fault_fallback: %s'` | Continues the text: the rows with `kB_huge` equal to `kB_total`, and the values of `thp_fault_fallback`. The text prints these values. They are not part of the pass condition. |
| 735 | `        % (tot, per(X, lambda x: '%d of %d' % (huge(x), len(x['sec']['P']))), fb))` | Ends the call of line 732: the three values of the text, with the count per folder in the form `N of M`. |
| 736 | `    dmax = lambda x: max(abs(iv['total'] - iv['I_agg']) for iv in x['ivs'])` | The rate of this script against the rate that `bwx12` printed. `dmax`: the largest absolute difference between `iv['total']` and `iv['I_agg']` over the intervals of one folder, in GB/s. `iv['total']` is the rate that the records use: the sum over the T rows of `bytes / elapsed_s / 1e9`, each thread with its own elapsed time. `iv['I_agg']` is the column `aggregate_GBps` of the I row of the same interval. `bwx12` computed it as the bytes of all threads / the longest per-thread time and printed 2 decimal places [Ref8]. |
| 737 | `    agg_limit = 0.05        # GB/s; the pass limit of this check` | `agg_limit`: 0.05 GB/s, the pass limit of this check. The limit is a choice of the script. |
| 738 | `    chk('I-agg', max(dmax(x) for x in X) < agg_limit,` | Check `I-agg`. It passes when the largest `dmax` of the 9 folders is below `agg_limit`. In the build of 2026-11-17 the largest difference is 0.018 GB/s, in `T72L1` [Ref9]. Example: the interval of round 0, position 0 (`oldread`) of `T72L1` has `total` = 462.300 GB/s and `I_agg` = 462.29 GB/s [Ref8]. |
| 739 | `        'total of the T rows against aggregate_GBps of the "I" row of the same interval, largest difference in GB/s '` | Text of the check: the total of the T rows is compared with `aggregate_GBps` of the I row of the same interval, and the largest difference is given in GB/s. |
| 740 | `        '(pass limit set by this script: below %.2f GB/s): ' % agg_limit + per(X, lambda x: '%.3f' % dmax(x)))` | Ends the call of line 738: the pass limit with 2 decimals, and `dmax` per folder with 3 decimals. |

### Checks 15 to 22: arguments, checksums, Linux release, runnable tasks (lines 741 to 797)

| Line | Source | Explanation |
|---:|---|---|
| 741 | `    # spec lines` | Comment: the spec lines. |
| 742 | `    spec = {n: fd._open(os.path.join(S, n + '.spec')).read().strip().split('\|', 1) for n in ('like', 'cfwd', 'crev')}` | `spec`: the content of `like.spec`, `cfwd.spec` and `crev.spec` in `S`, each split at the first `\|` into the tag and the arguments. |
| 743 | `    okarg = lambda x: [x['launches'][0]['tag'], x['launches'][0]['args']] == spec[x['spec']]` | `okarg`: a small function that tests whether the tag and the arguments of the `launch` line of one folder equal the two parts of its spec file. |
| 744 | `    chk('args', all(okarg(x) for x in X),` | Check `args`. It passes when this holds for every folder of the rerun. The arguments hold the stop rule (`--stop common`), the interval length (`--min-ms 6000`) and the kernel sequence (`--seq`). With the common stop, `bwx12` sets one deadline for all threads, 6000 ms after the common start time. A thread stops at its first clock reading at or after the deadline. Its own start reading comes at or after the common start time. So 6000 ms is not a lower limit for the timed span of one thread. In the 8880 T rows of the 9 bwx12 csv files of the rerun the column `elapsed_s` lies between 5.999979 s and 6.000457 s. |
| 745 | `        'tag and arguments of the launch line equal to the spec file: '` | Text of the check: the tag and the arguments of the `launch` line are compared with the spec file. |
| 746 | `        + per(X, lambda x: '%s.spec %s' % (x['spec'], yn(okarg(x)))))` | Ends the call of line 744: the spec file and `yes` or `NO` per folder. |
| 747 | `    r8 = D['rx']['L-1']['launches']['a6456']['args']` | `r8`: the arguments of the `a6456` launch line of the data set L-1. |
| 748 | `    f72 = D['rx']['F72d12']['launches']['a6456']['args']` | `f72`: the arguments of the `a6456` launch line of the data set F72d12. |
| 749 | `    chk('args-R8', spec['like'][1] == r8 == f72,` | Check `args-R8`. It passes when the arguments of `like.spec` equal both. With the checks `args` and `args-R8` passed, part L, control I, baseline L-1 and F72d12 ran with the same argument line. |
| 750 | `        'argument line of like.spec equal to the a6456 launch line of L-1 (w120-R8) and of F72d12: %s'` | Text of the check: the argument line of `like.spec` is compared with the `a6456` launch line of L-1 (folder `w120-R8`) and of F72d12. |
| 751 | `        % yn(spec['like'][1] == r8 == f72))` | Ends the call of line 749: `yes` or `NO`. |
| 752 | `    # checksums of the binaries` | Comment: the checksums of the binaries. The script computes no sha256 of a binary. The files `bw_old`, `bw_new` and `bwx12` are not in the local folders. So the checks `sha-bw` and `sha-bwx12` compare only sha256 values that the records hold. |
| 753 | `    p13 = D['probe13']` | `p13`: the result of `open_probe13` (line 568). |
| 754 | `    ok = all(a['probe']['sha'][b] == p13['sha'][b] for a in A for b in ('bw_old', 'bw_new'))` | `ok`: the sha256 values of `bw_old` and `bw_new` in the 3 `probe.txt` files of part A equal the values in `probe.txt` of 2026-11-13. `ra.sh` computes these values on CRB with `sha256sum`, once at the start of each session [Ref10]. Before that, `ra.sh` tests both binaries against the two sha256 values that are written in its own text, and it stops when the test fails. |
| 755 | `    ok2 = all(re.search(r'^%s  %s$' % (p13['sha'][b], b), D['env_partA'], re.M) for b in ('bw_old', 'bw_new'))` | `ok2`: the text of `env.txt` of the folder `partA-20261113T205055Z` holds a line with each of the two values, two spaces and the name of the binary. This folder holds the baselines A-2 and A-3. |
| 756 | `    chk('sha-bw', ok and ok2,` | Check `sha-bw`. It passes when `ok` and `ok2` are true. Then part A of the rerun and the baselines A-1, A-2 and A-3 ran the same two binaries. |
| 757 | `        'sha256 of bw_old (%s...) and bw_new (%s...): the 3 probe.txt files of part A equal lines %d and %d of '` | Text of the check: the first 8 digits of the two sha256 values, and the numbers of the two lines of `probe.txt` of 2026-11-13 that hold them. |
| 758 | `        'probe.txt of 2026-11-13: %s. env.txt of partA-20261113T205055Z holds the same two values: %s'` | Continues the text: whether the 3 `probe.txt` files equal those lines, and whether `env.txt` of the folder `partA-20261113T205055Z` holds the same two values. |
| 759 | `        % (p13['sha']['bw_old'][:8], p13['sha']['bw_new'][:8], p13['sha_line']['bw_old'], p13['sha_line']['bw_new'],` | Continues the call of line 756: the first 8 digits of the two values and their two line numbers. |
| 760 | `           yn(ok), yn(ok2)))` | Ends the call of line 756: `yes` or `NO` for `ok` and for `ok2`. |
| 761 | `    ra = fd.sha256(os.path.join(S, 'ra.sh'))` | `ra`: the sha256 of the local file `S/ra.sh`, computed by `fd.sha256`. |
| 762 | `    ok = all(a['probe']['sha']['ra.sh'] == ra for a in A)` | `ok`: each `probe.txt` holds this value for `ra.sh`. `ra.sh` writes that value on CRB from its own file. |
| 763 | `    chk('sha-ra', ok, 'sha256 of ra.sh in the 3 probe.txt files equal to S/ra.sh (%s...): %s' % (ra[:8], yn(ok)))` | Check `sha-ra`. It passes when `ok` is true. The text gives the first 8 digits of the value. |
| 764 | `    shas = {x['env']['sha'] for x in X}` | `shas`: the different sha256 values of `bwx12` in `env.txt` of the 9 rerun folders. `rx.sh` does not compute this value. It takes the value from its third argument, tests the binary against it with `sha256sum -c` and stops when the test fails. Then it writes the value into `env.txt`. `go.sh` and `go2.sh` pass their value `SHA` as this argument. |
| 765 | `    same12 = [n for n in ('L-1', 'L-2', 'L-3', 'L-4', 'X2d12', 'F72d12', 'X1d10', 'X1d10b', 'BASEd10')` | `same12`: the earlier bwx12 data sets, out of the 9 names of this line, whose `env.txt` holds a value of `shas`. |
| 766 | `              if D['rx'][n]['env']['sha'] in shas]` | Ends the list of line 765: the test on the sha256 of the data set. |
| 767 | `    go_sha = re.search(r'^SHA=([0-9a-f]{64})', fd._open(os.path.join(S, 'go.sh')).read(), re.M)[1]` | `go_sha`: the 64 hexadecimal digits after `SHA=` at the start of a line of the local `go.sh`. `go.sh` tests the `bwx12` binary on CRB against this value. |
| 768 | `    chk('sha-bwx12', len(shas) == 1 and len(same12) == 9 and {go_sha} == shas,` | Check `sha-bwx12`. It passes when `shas` holds one value, all 9 earlier data sets hold it, and it equals `go_sha`. Then parts L and C, control I and these 9 data sets ran the same `bwx12` binary. |
| 769 | `        'sha256 of bwx12 in env.txt: %d distinct value(s) in the %d folders of parts L, C, I (%s...). Equal to SHA= '` | Text of the check: the number of different values in the folders of parts L, C and I, with the first 8 digits, and whether the value equals `SHA=` in `go.sh`. |
| 770 | `        'in go.sh: %s. The same value is in env.txt of %s'` | Continues the text: the earlier data sets whose `env.txt` holds the same value. |
| 771 | `        % (len(shas), len(X), sorted(shas)[0][:8], yn({go_sha} == shas), ', '.join(same12)))` | Ends the call of line 768: the five values of the text. |
| 772 | `    listed = {}` | `listed`: a dictionary from file name to sha256, empty at first. |
| 773 | `    for f in ('local.sha', 'go2.sha'):` | Loop over the two checksum lists `local.sha` and `go2.sha` in `S`. |
| 774 | `        for l in fd._open(os.path.join(S, f)):` | Loop over the lines of the list. Each line holds a sha256 and a file name. |
| 775 | `            h, n = l.split()` | `h`: the sha256. `n`: the file name. |
| 776 | `            listed[os.path.basename(n)] = h` | Stores the sha256 under the file name without its folder part. The build of 2026-11-17 lists 6 files: `go.sh`, `go2.sh`, `ra.sh` and the 3 spec files [Ref9]. |
| 777 | `    bad = [n for n, h in listed.items() if fd.sha256(os.path.join(S, n)) != h]` | `bad`: the names whose local file in `S` has another sha256. |
| 778 | `    chk('sha-local', not bad,` | Check `sha-local`. It passes when `bad` is empty. The check reads local files only. A pass shows that each listed file in `S` still has the sha256 of its list. The stored facts sheet shows a pass. From 2026-11-24 on a new build fails. The text of one message of `go.sh` was edited on that day. So `bad` holds `go.sh`. With the old text put back the check passes again [Ref17]. Lines 853 to 866 say what is known about the copies on CRB. |
| 779 | `        'sha256 of the %d local run files (%s) equal to the lists local.sha and go2.sha: %s'` | Text of the check: the number of local run files, their names, and whether they equal the lists `local.sha` and `go2.sha`. |
| 780 | `        % (len(listed), ', '.join(sorted(listed)), yn(not bad)))` | Ends the call of line 778: the three values of the text. |
| 781 | `    # Linux kernel release, runnable tasks` | Comment: the Linux kernel release and the runnable tasks. |
| 782 | `    rel_ = {a['probe']['kernel'] for a in A} \| {x['env']['kernel'] for x in X}` | `rel_`: the different values of the Linux kernel release in the 3 `probe.txt` files and the 9 `env.txt` files. |
| 783 | `    cmd_rel = re.search(r'vmlinuz-(\S+)', D['logs']['go']['other']['cmdline'][0])[1]` | `cmd_rel`: the text after `vmlinuz-` in the `== cmdline` line of the log of `go.sh`, up to the next space. In this log the boot arguments start with `BOOT_IMAGE=/vmlinuz-7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858`. So `cmd_rel` is the release part of the name of the Linux image. |
| 784 | `    chk('uname', rel_ == {cmd_rel},` | Check `uname`. It passes when `rel_` holds one value and this value equals `cmd_rel`. |
| 785 | `        'Linux kernel release: %d distinct value(s) in the %d probe.txt and %d env.txt files. Equal to the image '` | Text of the check: the number of different release values in the `probe.txt` and `env.txt` files. |
| 786 | `        'name of the command line: %s' % (len(rel_), len(A), len(X), yn(rel_ == {cmd_rel})))` | Ends the call of line 784: the end of the text (whether the value equals the image name of the command line) and its four values. |
| 787 | `    run_ = [x['launches'][0]['runnable'] for x in X] + [a['probe']['runnable'] for a in A]` | `run_`: the number of runnable tasks in the `launch` line of each of the 9 bwx12 folders, and the value `runnable=` of each of the 3 `probe.txt` files. |
| 788 | `    limit = int(re.search(r'\$r -le (\d+)', fd._open(os.path.join(S, 'ra.sh')).read())[1])` | `limit`: the number in the text `$r -le N` of `S/ra.sh`, read from the script. `ra.sh` waits before its first process until at most this number of tasks is runnable. In the text of `ra.sh` the number is 2. |
| 789 | `    rx_, ra_ = [x['launches'][0]['runnable'] for x in X], [a['probe']['runnable'] for a in A]` | `rx_`, `ra_`: the two groups of `run_` as separate lists. |
| 790 | `    sleep_ = int(re.search(r'^sleep (\d+)', fd._open(os.path.join(S, 'ra.sh')).read(), re.M)[1])` | `sleep_`: the number in the first line of `S/ra.sh` that starts with `sleep`, in seconds. In the text of `ra.sh` it is 5 s. |
| 791 | `    span = lambda v: str(min(v)) if min(v) == max(v) else '%d to %d' % (min(v), max(v))` | `span`: a small function that gives a list of numbers as text: one number when all are equal, or `LOW to HIGH`. |
| 792 | `    chk('runnable', max(run_) <= limit,` | Check `runnable`. It passes when the largest of the 12 values is not above `limit`. In the build of 2026-11-17 the value is 1 in the 9 `launch` lines and 2 in the 3 `probe.txt` files [Ref9]. |
| 793 | `        'runnable tasks: %s at the %d bwx12 launches (launch line of rx.sh). Part A: the value runnable=%s of the %d '` | Text of the check: the runnable tasks at the bwx12 launches. For part A it says that the value `runnable=` of `probe.txt` is (the text goes on in line 794). |
| 794 | `        'probe.txt files is the last value of the wait loop of ra.sh (ra.sh waits for %d or fewer). ra.sh reads it, '` | Continues the text: the last value of the wait loop of `ra.sh`, with the limit of that loop. `ra.sh` reads the value (the text goes on in line 795). |
| 795 | `        'then sleeps %d s, then writes the time and the load of the probe line. So the value is from at least %d s '` | Continues the text: then `ra.sh` sleeps, then it writes the time and the load of the probe line. So the value is from some seconds (the text goes on in line 796). |
| 796 | `        'before the time of the probe line, and the count at the first launch of part A is not recorded'` | Continues the text: before the time of the probe line. The count at the first launch of part A is not recorded. So the text also says what the data do not show. |
| 797 | `        % (span(rx_), len(X), span(ra_), len(A), limit, sleep_, sleep_))` | Ends the call of line 792: the seven values of the text. |

### Checks 23 and 24: the rates against two other readers (lines 798 to 834)

| Line | Source | Explanation |
|---:|---|---|
| 798 | `    # cross-check against the existing tools` | Comment: the cross-check against the existing tools. |
| 799 | `    n_k, bad_k = 0, 0` | `n_k`: the number of compared interval rows. `bad_k`: the number of processes with a difference. Both start at 0. |
| 800 | `    pairs = [(a['folder'], a['procs']) for a in A] + [` | `pairs`: the folders that `stat_k120.py` reads, each with the processes that this script read. First the 3 part A folders of the rerun. |
| 801 | `        (D['base']['A-1']['folder'], D['base']['A-1']['procs']),` | Then the folder of A-1. |
| 802 | `        (os.path.join(S, 'base8000', 'partA-A1'), D['base']['A-2']['procs']),` | Then the folder `S/base8000/partA-A1`, with the processes of A-2. |
| 803 | `        (os.path.join(S, 'base8000', 'partA-A3-onebuf500'), D['base']['A-3']['procs'])]` | Then the folder `S/base8000/partA-A3-onebuf500`, with the processes of A-3. The two folders under `S/base8000` hold copies of the A-2 and A-3 processes in the form of `threads120.csv`. The records of A-2 and A-3 come from the raw `A1.csv` and `A3.csv`. |
| 804 | `    for folder, mine in pairs:` | Loop over these 6 folders. |
| 805 | `        fd.OPENED.append(os.path.join(folder, 'threads120.csv'))` | Adds `threads120.csv` of the folder to `fd.OPENED`. The reason: `stat_k120.py` does not open the file through `fd._open`. |
| 806 | `        theirs = fd.stat_k120.load(folder)` | Check `x-k120`, a second reader of the part A rows. `theirs`: the processes that `stat_k120.py` reads from the folder with its own parser [Ref5]. |
| 807 | `        assert len(theirs) == len(mine), folder` | The `assert` stops the script when the two readers return another number of processes for the folder. |
| 808 | `        for t, m in zip(theirs, mine):` | Loop over the processes of both readers in pairs. |
| 809 | `            a = [(iv['agg'], iv['tmin'], iv['tmax'], iv['passes']) for iv in m['iv']]` | `a`: four values of every interval row of this script: `aggregate_GBps` (column 7), `per_thread_min_GBps` (column 8), `per_thread_max_GBps` (column 9), and the pass count (column 5 / column 3, rounded down). |
| 810 | `            n_k += len(a)` | Adds the number of these interval rows to `n_k`. |
| 811 | `            bad_k += a != [tuple(i) for i in t['iv']] or (t['binary'], t['kernel']) != (m['binary'], m['kernel'])` | Adds 1 to `bad_k` when the four values of any row differ from those of `stat_k120.py`, or when the binary or the kernel of the process differs. The comparison is exact equality. No difference is allowed. |
| 812 | `    chk('x-k120', bad_k == 0,` | The check passes when `bad_k` is 0. In the build of 2026-11-17 `n_k` is 333 interval rows [Ref9]. |
| 813 | `        'cross-check with stat_k120.py: %d interval rows (3 sessions of part A, A-1, and the copies of A-2 and A-3 '` | Text of the check: the number of interval rows and what they cover: the 3 sessions of part A, A-1, and the copies of A-2 and A-3. |
| 814 | `        'under S/base8000, while this script reads the raw A1.csv and A3.csv) are equal in rate, per-thread minimum '` | Continues the text: the copies lie under `S/base8000`, while this script reads the raw `A1.csv` and `A3.csv`. The rows are equal in rate, per-thread minimum (the text goes on in line 815). |
| 815 | `        'and maximum, and pass count: %s' % (n_k, yn(bad_k == 0)))` | Ends the call of line 812: the end of the text (per-thread maximum and pass count) and its two values. |
| 816 | `    n_x, bad_x, n_rerun = 0, 0, 0` | `n_x`: the number of compared intervals. `bad_x`: the number of intervals with a difference. `n_rerun`: the number of compared intervals of the rerun. |
| 817 | `    folders = [(x['folder'], {os.path.basename(x['csv'])[:-4]: x['sec']}) for x in X] + \` | `folders`: the folders that `stat_bwx.py` reads, each with the sections that this script read. First the 9 folders of the rerun. The key of a section is the name of the csv without `.csv`. |
| 818 | `              [(v['folder'], v['secs']) for v in D['rx'].values()]` | Ends the statement of line 817: then the 11 folders of the earlier bwx12 and bwx11 data sets (`D['rx']`). The folders of the first runner `bwx` (`D['step']`) are not part of this check. |
| 819 | `    for i, (folder, secs) in enumerate(folders):` | Loop over these 20 folders with their index `i`. |
| 820 | `        theirs = {(r['file'], r['round'], r['pos'], r['kernel']): r for r in fd.stat_bwx.interval_rows(folder)}` | Check `x-bwx`, a second reader of the bwx rows. `theirs`: the rows of `stat_bwx.py` for the folder, by file name, round, position and kernel. `stat_bwx.py` computes the rate of every interval of every csv of the folder with its own parser [Ref6]. |
| 821 | `        for tag, sec in secs.items():` | Loop over the sections that this script read from the folder. |
| 822 | `            for iv in fd.bwx_intervals(sec):` | Loop over the intervals of the section, computed again by `fd.bwx_intervals`. This includes the intervals that the filter `POS01` kept out of the records. |
| 823 | `                t = theirs[(tag + '.csv', iv['round'], iv['pos'], iv['kernel'])]` | `t`: the row of `stat_bwx.py` for this interval. An interval that `stat_bwx.py` does not return ends the script with the Python error `KeyError`. |
| 824 | `                n_x += 1` | Counts the interval. |
| 825 | `                n_rerun += i < len(X)` | Counts it as an interval of the rerun when the folder is one of the first 9. |
| 826 | `                bad_x += (abs(t['total'] - iv['total']) > 1e-9 or abs(t['h0_sum'] - iv['mesh0']) > 1e-9` | Adds 1 to `bad_x` when the interval differs. First tests: the total or the sum of mesh 0 differs by more than 1e-9 GB/s, which is 1 byte per second. The two scripts add the per-thread rates in another order. So a limit above 0 is needed. `stat_bwx.py` adds all T rows in file order. This script adds each mesh first and then the two sums. In the 26 csv files of this check the largest difference is about 5e-13 GB/s. |
| 827 | `                          or abs(t['h1_sum'] - iv['mesh1']) > 1e-9 or t['is_64_56'] != iv['is_64_56']` | Continues the expression of line 826: the sum of mesh 1 differs by more than 1e-9 GB/s, or the result of the 64+56 test differs. |
| 828 | `                          or t['flagged'] != iv['flagged'])` | Ends the expression of line 826: or the number of flagged rows differs. |
| 829 | `    chk('x-bwx', bad_x == 0,` | The check passes when `bad_x` is 0. In the build of 2026-11-17 `n_x` is 297 intervals: 74 of the rerun and 223 earlier ones [Ref9]. |
| 830 | `        'cross-check with stat_bwx.py: %d intervals of %d folders (the %d folders of parts L, C, I with %d intervals, '` | Text of the check: the number of intervals and folders, with the share of the 9 folders of parts L, C and I. |
| 831 | `        'and the %d csv files that section 7 lists from the %d earlier rx.sh and r0.sh folders with %d intervals) are '` | Continues the text: the number of csv files of the earlier `rx.sh` and `r0.sh` folders that section 7 of the facts sheet lists, with their intervals. |
| 832 | `        'equal in total, sum per mesh, the 64+56 test and the count of flagged rows: %s'` | Continues the text: the intervals are equal in total, sum per mesh, the 64+56 test and the count of flagged rows. |
| 833 | `        % (n_x, len(folders), len(X), n_rerun, sum(len(v['secs']) for v in D['rx'].values()), len(D['rx']),` | Continues the call of line 829: the values of the text. |
| 834 | `           n_x - n_rerun, yn(bad_x == 0)))` | Ends the call of line 829: the number of earlier intervals (`n_x` minus `n_rerun`) and `yes` or `NO`. |

### Checks 25 and 26: the earlier bwx records and the script `rx.sh` (lines 835 to 866)

| Line | Source | Explanation |
|---:|---|---|
| 835 | `    # earlier intervals` | Comment: the earlier intervals. |
| 836 | `    b = [r for r in recs if r['is_64_56'] is not None and r['dataset'] not in ('rerun-L', 'rerun-C', 'control-I')]` | `b`: the records that have a 64+56 value and whose data set is not `rerun-L`, `rerun-C` or `control-I`. Only bwx records have this value. The build of 2026-11-17 has 386 such records [Ref9]. |
| 837 | `    okb = sum(1 for r in b if r['is_64_56'] and r['flagged'] == 0)` | `okb`: the number of them that pass the 64+56 test and have 0 flagged T rows. |
| 838 | `    errs = sum(v['stderr_bytes'] for v in D['rx'].values())` | `errs`: the bytes of `stderr.txt` of the 11 folders of `D['rx']`, added. |
| 839 | `    rcs = sorted({v['launches'][t]['rc'] for v in D['rx'].values() for t in v['secs']})` | `rcs`: the different exit statuses of the 17 processes whose csv files this script reads from these folders. The `launches.txt` files of these 11 folders hold 52 launch lines. The exit statuses of the other 35 processes are not tested here. |
| 840 | `    chk('earlier', okb == len(b) and errs == 0 and rcs == ['0'],` | Check `earlier`. It passes when `okb` equals the size of `b`, `errs` is 0, and `0` is the only exit status. The exit status and `stderr.txt` of the folders of the first runner `bwx` are not tested here. |
| 841 | `        'earlier bwx intervals used in sections 3 and 4: %d of %d are 64+56 intervals with 0 flagged T rows. The %d '` | Text of the check: how many of the earlier bwx intervals are 64+56 intervals with 0 flagged T rows. |
| 842 | `        'earlier rx.sh and r0.sh folders hold %d bytes of stderr.txt in total. The rc values of their %d processes used: %s'` | Continues the text: the bytes of `stderr.txt` of the earlier `rx.sh` and `r0.sh` folders in total, and the exit statuses of their processes used. |
| 843 | `        % (okb, len(b), len(D['rx']), errs, sum(len(v['secs']) for v in D['rx'].values()), '/'.join(rcs)))` | Ends the call of line 840: the six values of the text. |
| 844 | `    # rx.sh: the local copy against the checksum that go.sh and go2.sh test on CRB (added last, so that the` | Comment: check `sha-rx` compares the local copy of `rx.sh` with the checksum that `go.sh` and `go2.sh` test on CRB. It was added last (the reason follows in line 845). |
| 845 | `    # numbers of the checks above stay as they were)` | Comment: the reason: the numbers of the checks above stay as they were. |
| 846 | `    rx = fd.sha256(os.path.join(fd.W15, 'rx.sh'))` | `rx`: the sha256 of the local `rx.sh` in the folder `fd.W15`. |
| 847 | `    scripts = {n: fd._open(os.path.join(S, n)).read() for n in ('go.sh', 'go2.sh')}` | `scripts`: the texts of the local `go.sh` and `go2.sh` in `S`. |
| 848 | `    rxsha = {n: re.search(r'^RXSHA=([0-9a-f]{64})$', t, re.M)[1] for n, t in scripts.items()}` | `rxsha`: the 64 hexadecimal digits of the line `RXSHA=` in each of the two scripts. |
| 849 | `    stop_msg = 'rx.sh is not the script of 2026-11-15'` | `stop_msg`: the message that the two scripts print when their test of `rx.sh` fails, as this script expects it. |
| 850 | `    stop_line = 'echo "$RXSHA  $RX" \| sha256sum -c - > /dev/null \|\| fail "%s"' % stop_msg` | `stop_line`: the line of the two scripts that tests `rx.sh` against `RXSHA` with `sha256sum -c` and calls `fail` with that message when the test fails. |
| 851 | `    has_stop = all(stop_line in t and 'fail() { echo "FAILED: $1";' in t for t in scripts.values())` | `has_stop`: both scripts hold `stop_line`, and both hold the first part of the function `fail`, the `echo` of the `FAILED:` line. The rest of `fail` is not tested. In both scripts `fail` prints a line that starts with `FAILED:`, prints a state line and ends the script with exit status 1. The texts of `go.sh` and `go2.sh` in the code repo were changed on 2026-11-24. They hold the date 2026-11-24 in this message. For those texts `has_stop` is false. |
| 852 | `    n_failed = sum(len(D['logs'][n]['failed']) for n in ('go', 'go2'))` | `n_failed`: the number of lines that start with `FAILED` in the two logs. |
| 853 | `    # limit of this check: no record of the rerun holds a checksum of rx.sh, go.sh or go2.sh that was taken on CRB` | Comment: the limit of this check: no record of the rerun holds a checksum of `rx.sh`, `go.sh` or `go2.sh` that was taken on CRB. |
| 854 | `    crb_texts = ['\n'.join(D['logs'][n]['lines']) for n in ('go', 'go2')] + \` | `crb_texts`: the texts that came from CRB. First the 2 logs. |
| 855 | `                [fd._open(a['probe']['path']).read() for a in A] + \` | Continues the list of line 854: the 3 `probe.txt` files of the rerun. |
| 856 | `                [fd._open(os.path.join(x['folder'], 'env.txt')).read() for x in X]` | Ends the list of line 854: the 9 `env.txt` files of the rerun. |
| 857 | `    local_sha = [rx] + [fd.sha256(os.path.join(S, n)) for n in ('go.sh', 'go2.sh')]` | `local_sha`: the sha256 values of the local `rx.sh`, `go.sh` and `go2.sh`. For `go.sh` this is the value of the file as it is now in `S`. After the edit of 2026-11-24 it is not the value of the text that ran [Ref17]. |
| 858 | `    assert not any(h in t for h in local_sha for t in crb_texts), 'a CRB record holds one of these checksums: revise the text'` | The `assert` stops the script when one of these texts holds one of the three checksums. Its message asks to revise the text of the check. |
| 859 | `    chk('sha-rx', set(rxsha.values()) == {rx} and has_stop and n_failed == 0,` | Check `sha-rx`. It passes when both `RXSHA` values equal `rx`, `has_stop` is true and `n_failed` is 0. Then neither driver script stopped at its test of `rx.sh` on CRB. The record of the Claude Code session of 2026-11-17 holds a test of both driver scripts on CRB [Ref14]. This script does not read that record. Two commands of the record wrote `local.sha` and `go2.sha` in `S` and copied the listed files to CRB. There they ran `sha256sum -c`, which compares each file with its sha256 in the list. The output shows `go.sh: OK` and `go2.sh: OK`. |
| 860 | `        'sha256 of the local rx.sh (%s...) equal to RXSHA= in go.sh and go2.sh: %s. Both scripts hold the line that '` | Text of the check: the first 8 digits of the sha256 of the local `rx.sh`, and whether it equals `RXSHA=` in `go.sh` and `go2.sh`. It then says that both scripts hold the line (the text goes on in line 861). |
| 861 | `        'tests this value with sha256sum on CRB and stops with "FAILED: %s" when the copy on CRB differs: %s. Lines '` | Continues the text: that tests this value with `sha256sum` on CRB and stops with `FAILED:` and the message when the copy on CRB differs. |
| 862 | `        'that start with FAILED in the two logs: %d. Limit: the %d logs, the %d probe.txt files and the %d env.txt '` | Continues the text: the number of `FAILED` lines in the two logs. Then the limit: the logs, the `probe.txt` files and the `env.txt` files (the text goes on in line 863). |
| 863 | `        'files of the rerun hold no sha256 of rx.sh, go.sh or go2.sh. So this check uses the local copies of go.sh '` | Continues the text: of the rerun hold no sha256 of `rx.sh`, `go.sh` or `go2.sh`. So this check uses the local copies of `go.sh` (the text goes on in line 864). |
| 864 | `        'and go2.sh (check %d)'` | Ends the text: and `go2.sh`, and it names the check `sha-local` by its number. |
| 865 | `        % (rx[:8], yn(set(rxsha.values()) == {rx}), stop_msg, yn(has_stop), n_failed, len(D['logs']), len(A), len(X),` | Continues the call of line 859: the values of the text. |
| 866 | `           [c['key'] for c in C].index('sha-local') + 1))` | Ends the call of line 859: the number of the check `sha-local`. It is the place of that check in the list, counted from 1. |

### Check 27: the arguments of part A against the test of 2026-11-13 (lines 867 to 896)

| Line | Source | Explanation |
|---:|---|---|
| 867 | `    # arguments of part A against the test of 2026-11-13 (added after the checks above, so that their numbers stay)` | Comment: the arguments of part A are compared with the test of 2026-11-13. The check was added after the checks above. So their numbers stay as they were. |
| 868 | `    a1 = D['base']['A-1']['procs']` | `a1`: the processes of baseline A-1, the first test of 2026-11-13. |
| 869 | `    hdr = lambda p: (p['binary'], p['kernel'], p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes'], p['round'])` | `hdr`: a small function that gives six values of the `-- binary` header line of a process: binary, kernel, threads, cpus, bytes and round. |
| 870 | `    n_all = sum(len(a['procs']) for a in A)` | `n_all`: the number of all processes of part A of the rerun. |
| 871 | `    n_same = sum(hdr(p) == hdr(q) for a in A if len(a['procs']) == len(a1) for p, q in zip(a['procs'], a1))` | `n_same`: the number of rerun processes whose six values equal those of the process at the same place in A-1. A file with another number of processes than A-1 adds nothing. |
| 872 | `    every = [p for a in A for p in a['procs']] + a1` | `every`: all processes of the 3 files of the rerun and of A-1. |
| 873 | `    hv = sorted({(p['hdr_threads'], p['hdr_cpus'], p['hdr_bytes']) for p in every})` | `hv`: the different values of threads, cpus and bytes over these processes. |
| 874 | `    bw = sorted({p.get('bw_hdr') for p in every}, key=str)` | `bw`: the different ends of the `# bandwidth:` line that the binary prints. This end holds threads, bytes per thread, `min_ms` and `thp`. |
| 875 | `    ra_lines = fd._open(os.path.join(S, 'ra.sh')).read().splitlines()` | `ra_lines`: the lines of `S/ra.sh`. |
| 876 | `    rk_path = os.path.join(fd.K13, 'run_kernels.sh')` | `rk_path`: the path of `run_kernels.sh` in the folder `fd.K13`. |
| 877 | `    rk_lines = fd._open(rk_path).read().splitlines()` | `rk_lines`: the lines of that file. |
| 878 | `    i_ra = next(i for i, l in enumerate(ra_lines) if l.startswith('one() {'))` | `i_ra`: the place of the first line of `ra.sh` that starts with `one() {`. This line starts the shell function `one`, which starts one benchmark process. |
| 879 | `    i_rk = next(i for i, l in enumerate(rk_lines) if l.startswith('one() {'))` | `i_rk`: the same place in `run_kernels.sh`. |
| 880 | `    same_fn = ra_lines[i_ra:i_ra + 5] == rk_lines[i_rk:i_rk + 5] and ra_lines[i_ra + 4] == '}'` | `same_fn`: the 5 lines from that place are equal in both scripts, and the fifth line of `ra.sh` is `}`. So the function `one` has 5 lines and is the same in both. In the text of `ra.sh` in the code repo, changed on 2026-11-24, the function `one` has two more lines. For that text `same_fn` is false. |
| 881 | `    opts = '--reps 3 --min-ms 500'` | `opts`: the options `--reps 3 --min-ms 500`. |
| 882 | `    has_opts = ra_lines[i_ra + 3].rstrip().endswith(opts + ' >> "$1"')` | `has_opts`: the fourth line of the function `one` of `ra.sh`, the line that starts the binary, ends with these options and the text `>> "$1"`. So each process times 3 intervals of at least 500 ms each. |
| 883 | `    rk_ok = p13['sha'].get('run_kernels.sh') == fd.sha256(rk_path)` | `rk_ok`: the sha256 of the local `run_kernels.sh` equals the value in `probe.txt` of 2026-11-13. |
| 884 | `    ok = n_same == n_all and len(hv) == 1 and len(bw) == 1 and bw[0] and same_fn and has_opts and rk_ok` | `ok`: `n_same` equals `n_all`, `hv` holds one value, `bw` holds one value that is not empty, and `same_fn`, `has_opts` and `rk_ok` are true. |
| 885 | `    chk('A-args', ok,` | Check `A-args`. It passes when `ok` is true. In the build of 2026-11-17 all 72 header lines of the rerun equal those of A-1, with threads 120, cpus 0-119 and bytes 256M. The binary printed `min_ms=500 thp=madvise` in all 96 processes of the 4 files [Ref9]. |
| 886 | `        'part A, arguments. The "-- binary" header lines of the %d threads120.csv files of part A are equal to those '` | Text of the check: the `-- binary` header lines of the `threads120.csv` files of part A are compared with those (the text goes on in line 887). |
| 887 | `        'of threads120.csv of 2026-11-13 in binary, kernel, threads, cpus, bytes and round: %d of %d lines (threads %s, '` | Continues the text: of `threads120.csv` of 2026-11-13 in binary, kernel, threads, cpus, bytes and round, with the count of equal lines. |
| 888 | `        'cpus %s, bytes %s in every line). The header line that the binary prints ends with "%s" in all %d processes of '` | Continues the text: the values of cpus and bytes, and the end of the header line that the binary prints in all processes. |
| 889 | `        'the %d files. The function one() of ra.sh (lines %d to %d) is equal to lines %d to %d of run_kernels.sh: %s. '` | Continues the text: the lines of the function `one` in `ra.sh`, and whether they equal the lines of `run_kernels.sh`. |
| 890 | `        'Its process line ends with the options "%s": %s. sha256 of the local run_kernels.sh equal to line %d of '` | Continues the text: whether the process line ends with the options, and whether the sha256 of the local `run_kernels.sh` equals (the text goes on in line 891). |
| 891 | `        'probe.txt of 2026-11-13: %s'` | Ends the text: the line of `probe.txt` of 2026-11-13. |
| 892 | `        % (len(A), n_same, n_all, hv[0][0], hv[0][1], hv[0][2], bw[0], len(every), len(A) + 1, i_ra + 1, i_ra + 5,` | Continues the call of line 885: the values of the text. The line numbers of `one` are counted from 1. |
| 893 | `           i_rk + 1, i_rk + 5, yn(same_fn), opts, yn(has_opts), p13['sha_line'].get('run_kernels.sh', 0), yn(rk_ok)))` | Ends the call of line 885: the last values. The line number of `run_kernels.sh` in `probe.txt` is 0 when the file has no such entry. |
| 894 | `    return C` | Returns the list of checks. |

### Function `write_json`: the first entries of `meta`, the units and the two kinds of rate (lines 897 to 918)

| Line | Source | Explanation |
|---:|---|---|
| 897 | `# ----------------------------------------------------------------------------- facts.json` | Comment: a divider line. The block below writes `facts.json`. |
| 899 | `def write_json(D, V, path):` | Starts the function `write_json`. `main` calls it with `D`, the verdicts `V` and the path `S/facts.json` (line 1038). The file has three parts: `meta`, `verdicts` and `intervals`. |
| 900 | `    recs = D['recs']` | `recs`: the list of all records. |
| 901 | `    try6 = D['try6']` | `try6`: the values of `try6.txt`. |
| 902 | `    meta = dict(` | `meta`: starts the dictionary of the first part of the file. Lines 903 to 1014 build it. `meta` describes the run. It holds no interval record. |
| 903 | `        title='Facts of the whole-chip read rerun at 7200 MT/s, CRB, 2026-11-17',` | `title`: a fixed text that names the rerun. |
| 904 | `        written_by='S/build_facts.py (with S/facts_data.py, S/facts_text.py and S/facts_text4.py)',` | `written_by`: a fixed text with the names of the four scripts that write the file. |
| 905 | `        R=R, S=S,` | The folder paths `R` and `S`. |
| 906 | `        units=dict(GBps='GB/s with GB = 1e9 bytes', load1_at_launch='1-minute load average of Linux at the launch of '` | `units`: texts that explain fields of the records. `GBps`: GB/s with GB = 1e9 bytes. `load1_at_launch`: its text starts here: the 1-minute load average of Linux at the launch of (the text goes on in line 907). |
| 907 | `                   'the process', gap_s='seconds between the end of the previous 120-thread process of the rerun and '` | Ends the text of `load1_at_launch`: the process. Starts the text of `gap_s`: the seconds between the end of the previous 120-thread process of the rerun and (the text goes on in line 908). |
| 908 | `                   'this launch (1 s resolution). bwx12 records: the launch of their process. Part A: set on the '` | Text of `gap_s`: this launch, with a resolution of 1 s. For bwx12 records it is the launch of their process. For part A it is set on (the text goes on in line 909). |
| 909 | `                   'first process of a session only; null for processes 2 to 24, which ra.sh starts directly after '` | Text of `gap_s`: the first process of a session only. It is `null` for the processes 2 to 24, which `ra.sh` starts directly after (the text goes on in line 910). |
| 910 | `                   'the previous part A process with no wait', passes='part A only: total_bytes / bytes_per_thread of the '` | Ends the text of `gap_s`: the previous part A process with no wait. Starts the text of `passes`: for part A only, `total_bytes / bytes_per_thread` of the interval row. |
| 911 | `                   'interval row. For read, asmread, write and asmwrite this is the number of buffer passes of all '` | Text of `passes`: for `read`, `asmread`, `write` and `asmwrite` this is the number of buffer passes of all threads in the interval. |
| 912 | `                   'threads in the interval. For copy and asmcopy (%d records) it is 2 x that number, because the '` | Text of `passes`: for `copy` and `asmcopy` it is 2 x that number. The place `%d` takes the number of records of these two kernels. The text of `facts.json` holds 96 records there [Ref9]. |
| 913 | `                   'binary counts read plus written bytes for these two kernels: the header line of each of their '` | Text of `passes`: the reason is that the binary counts the bytes read plus the bytes written for these two kernels. The header line of each of their processes (the text goes on in line 914). |
| 914 | `                   'processes in the csv says "copy counts read+write bytes"'` | Ends the text of `passes`: in the csv says `copy counts read+write bytes`. |
| 915 | `                   % len(fd.sel(recs, part='A', kernel={'copy', 'asmcopy'})), min_ms='shortest length of one interval, milliseconds',` | The value for the place `%d` of line 912: the number of records with the part `A` and the kernel `copy` or `asmcopy`, selected with `fd.sel`. Then the text of `min_ms`: the shortest length of one interval, in milliseconds. |
| 916 | `                   speed_MTps='memory speed, million transfers per second'),` | Ends the dictionary `units`. `speed_MTps`: the memory speed in million transfers per second. |
| 917 | `        rate_kinds=dict(part_A=fd.KIND_A, bwx=fd.KIND_X + '. This file rounds it to 0.001 GB/s. FACTS.md formats the '` | `rate_kinds`: the two rate formulas. `part_A` is `fd.KIND_A`: the column `aggregate_GBps` of the csv. The binary computed this column as the sum of the bytes of all threads / the longest per-thread time [Ref13]. `bwx` is `fd.KIND_X`: the sum over the T rows of `bytes / elapsed_s / 1e9`. The text adds that this file rounds the bwx rate to 0.001 GB/s. |
| 918 | `                        'unrounded value'),` | Ends the text of line 917: `FACTS.md` formats the value that is not rounded. |

### `write_json`: the texts that explain the fields of a record (lines 919 to 953)

| Line | Source | Explanation |
|---:|---|---|
| 919 | `        fields=dict(dataset='rerun-A, rerun-L, rerun-C, control-I, F72d12, or the label of an earlier row '` | `fields`: 15 texts for the reader of `facts.json`. 14 texts explain one field of a record each. `dataset`: the names of the data sets of the rerun and F72d12, or the label of an earlier row (the text goes on in line 920). |
| 920 | `                    '(A-1..A-3, L-1..L-4, R0, R0b, X2d12, X1d10, X1d10b, BASEd10, B7a, B7b, C3a, C3b, B5a, B5b, '` | Text of `dataset`: the labels of the earlier rows, from A-1 to B5b. |
| 921 | `                    'B5a-rev, B5b-rev)',` | Ends the text of `dataset`: the two labels B5a-rev and B5b-rev. |
| 922 | `                    role='rerun, control, baseline, supporting, other binary, not a baseline, 10 modules',` | `role`: the possible roles of a data set: rerun, control, baseline, supporting, other binary, not a baseline, 10 modules. |
| 923 | `                    round='part A: round of the script (1 or 2). In A-3 it is the repeat number. bwx: round of the '` | `round`: in part A it is the round of the script (1 or 2). In A-3 it is the repeat number. For a bwx record it is the round of the (the text goes on in line 924). |
| 924 | `                          'kernel sequence inside the process, from 0',` | Ends the text of `round`: kernel sequence inside the process, counted from 0. |
| 925 | `                    pos='bwx only: position of the kernel in the sequence of the process, from 0',` | `pos`: for bwx records only, the position of the kernel in the sequence of the process, counted from 0. |
| 926 | `                    interval='number of the interval inside the process, from 0',` | `interval`: the number of the interval inside the process, counted from 0. |
| 927 | `                    kernel_before='bwx: the kernel timed directly before in the same process. Part A: binary and '` | `kernel_before`: for a bwx record the kernel that was timed directly before in the same process. For part A the binary and (the text goes on in line 928). |
| 928 | `                                  'kernel of the process that ran directly before in the same csv file. "none (first '` | Text of `kernel_before`: the kernel of the process that ran directly before in the same csv file. The value that starts with `none (first` (the text goes on in line 929). |
| 929 | `                                  'process of the file)" says nothing about the work before the file. Row A-3 holds 3 '` | Text of `kernel_before`: `process of the file)` says nothing about the work before the file. Row A-3 holds 3 (the text goes on in line 930). |
| 930 | `                                  'of the 12 processes of A3.csv: its first process is the first process of that file '` | Text of `kernel_before`: of the 12 processes of `A3.csv`. Its first process is the first process of that file. |
| 931 | `                                  '(the process directly before it is the last process of A2.csv: %s %s, tag %s, '` | Text of `kernel_before`: the process directly before it is the last process of `A2.csv`. Three places take its binary, its kernel and its tag. |
| 932 | `                                  'launched %s, arguments "%s"). Before each of the other two, a process ran that '` | Text of `kernel_before`: two more places take its launch time and its arguments. Before each of the other two processes of A-3, a process ran that (the text goes on in line 933). |
| 933 | `                                  'is not in the list ("not listed ...")'` | Ends the text of `kernel_before`: is not in the list, with the value `not listed ...`. |
| 934 | `                                  % (D['probe13']['a3_prev']['binary'], D['probe13']['a3_prev']['kernel'],` | The values for the places of lines 931 to 932: the binary and the kernel of `a3_prev`, the process that `open_probe13` found (line 623). This is the only text of `fields` that holds values from the data. |
| 935 | `                                     D['probe13']['a3_prev']['tag'], iso(D['probe13']['a3_prev']['utc']),` | Continues the values: the tag and the launch time of `a3_prev`, formatted by `iso`. |
| 936 | `                                     D['probe13']['a3_prev']['args']),` | Ends the values: the arguments of `a3_prev`. |
| 937 | `                    mesh0_GBps='bwx only: sum over the threads on CPUs 0-63',` | `mesh0_GBps`: for bwx records only, the sum over the threads on the CPUs 0 to 63. In a part A record the field is `null`. |
| 938 | `                    mesh1_GBps='bwx only: sum over the threads on CPUs 64-127',` | `mesh1_GBps`: for bwx records only, the sum over the threads on the CPUs 64 to 127. In a part A record the field is `null`. |
| 939 | `                    line='line number of the interval row in the file (part A) or of its "I" row (bwx)',` | `line`: the line number of the interval row in the file (part A), or of its I row (bwx). |
| 940 | `                    proc_key='one value per process',` | `proc_key`: one value per process. |
| 941 | `                    session='rerun: session of go.sh (1 to 3); null for T72C4, which ran after session 3. '` | `session`: for the rerun the session of `go.sh` (1 to 3). It is `null` for `T72C4`, which the text says ran after session 3. |
| 942 | `                            'control-I: number of the control process (1 or 2); it is not a session',` | Ends the text of `session`: in a record of `control-I` it is the number of the control process (1 or 2), and not a session. |
| 943 | `                    start='bwx only: value of the option --start in the csv header (common or offset)',` | `start`: for bwx records only, the value of the option `--start` in the csv header (`common` or `offset`). |
| 944 | `                    start_state='start state of the step that holds the record: the session of part A, or the '` | `start_state`: the start state of the step that holds the record. A step is a session of part A or a (the text goes on in line 945). |
| 945 | `                                'bwx12 process. In part A it describes the first process of the session',` | Ends the text of `start_state`: bwx12 process. In part A it describes the first process of the session. |
| 946 | `                    per_thread_avg_GBps='part A only: column per_thread_avg_GBps of the csv, rounded to 0.01 GB/s '` | `per_thread_avg_GBps`: for part A only, the column `per_thread_avg_GBps` of the csv, rounded to 0.01 GB/s (the text goes on in line 947). |
| 947 | `                                        'by the binary',` | Ends the text of `per_thread_avg_GBps`: by the binary. |
| 948 | `                    q2_rows='verdicts.q2_rows: row_7200 and scope_8000 are the keys of a row. They are kept as in '` | `q2_rows`: this text explains the keys of a row in `verdicts.q2_rows`. `row_7200` and `scope_8000` are the keys of a row. They are kept as in (the text goes on in line 949). |
| 949 | `                            'the earlier builds of this file, so that a tool can find a row. row_7200_label and '` | Text of `q2_rows`: the earlier builds of this file. So a tool can find a row. `row_7200_label` and (the text goes on in line 950). |
| 950 | `                            'scope_8000_label are the labels that FACTS.md prints. Where a key says "not pooled", '` | Text of `q2_rows`: `scope_8000_label` are the labels that `FACTS.md` prints. Where a key says `not pooled`, (the text goes on in line 951). |
| 951 | `                            'the label says "own row": the row is its own row in every range test of rule V1 point '` | Text of `q2_rows`: the label says `own row`. The row is its own row in every range test of rule V1 point (the text goes on in line 952). |
| 952 | `                            '2. Where a key says "(after oldread)", the label adds that the 8000 MT/s rows hold '` | Text of `q2_rows`: 2. Where a key says `(after oldread)`, the label adds that the 8000 MT/s rows hold (the text goes on in line 953). |
| 953 | `                            'asmread at position 1 and part C holds it at position 0'),` | Ends the text of `q2_rows` and the dictionary `fields`: `asmread` at position 1, and part C holds it at position 0. |

### `write_json`: the rerun, the steps, the checks, the counts and the boot of F72d12 (lines 954 to 979)

| Line | Source | Explanation |
|---:|---|---|
| 954 | `        rerun=dict(boot_id=try6['boot'], modules=try6['dimm_sockets'], speed_MTps=try6['speed_MTps'],` | `rerun`: the boot id, the module count and the memory speed, all from `try6.txt`. |
| 955 | `                   memtotal_kB=try6['memtotal_kB'],` | `memtotal_kB`: `MemTotal` of `try6.txt` in kB. |
| 956 | `                   speed_proof='%s line %d, read at %s in the same boot. Not read during the rerun (no root)'` | `speed_proof`: a text that names the proof of the memory speed: a file, a line number and the time of the reading in the same boot. It says that the speed was not read during the rerun, for lack of root rights. |
| 957 | `                               % (rel(try6['path']), try6['speed_line'], iso(try6['utc'])),` | The values of the text of line 956: the path of `try6.txt` in the short form of `rel`, the number of its speed line and its time. |
| 958 | `                   go_start=iso(D['logs']['go']['states'][0]['utc']), go_end=iso(D['logs']['go']['states'][-1]['utc']),` | `go_start`, `go_end`: the times of the first and the last state line of the log of `go.sh`. |
| 959 | `                   go2_start=iso(D['logs']['go2']['states'][0]['utc']), go2_end=iso(D['logs']['go2']['states'][-1]['utc']),` | `go2_start`, `go2_end`: the same two times of the log of `go2.sh`. |
| 960 | `                   kernel_log_read=False, root_used=False),` | Ends the dictionary `rerun` with two fixed values. `kernel_log_read` is false: the Linux kernel log was not read. `root_used` is false: root rights were not used. |
| 961 | `        launches=[dict(tag=e['tag'], part=e['part'], session=e['session'], script_start=iso(e['start']),` | `launches`: the 12 steps of the rerun in time order (lines 89 to 117). Each entry holds the tag, the part, the session and `script_start`, the time in the folder name. |
| 962 | `                       first_launch=iso(e['first']), end=iso(e['end']), gap_s=e['gap_s'], load1_at_first_launch=e['load1'],` | Continues the entry of line 961: the time of the first launch, the end time, `gap_s` and the 1-minute load average at the first launch. |
| 963 | `                       start_state=e['state']) for e in D['events']],` | Ends the list of line 961: the start state of each step. |
| 964 | `        checks=[dict(key=c['key'], ok=c['ok'], text=c['text']) for c in D['checks']],` | `checks`: the 27 checks with key, pass flag and text. |
| 965 | `        counts=dict(intervals=len(recs), by_dataset={k: len(fd.sel(recs, dataset=k))` | `counts`: the number of all records, and the number per data set. The number per data set is the number of records that `fd.sel` selects for it. Records are counted here. No rate is added. The build of 2026-11-17 holds 793 records [Ref9]. |
| 966 | `                                                     for k in dict.fromkeys(r['dataset'] for r in recs)}),` | Ends the dictionary of line 965. `dict.fromkeys` gives the data sets in the order in which they first appear in the records. |
| 967 | `        rules='S/baselines-and-rules.txt (fixed before the run)',` | `rules`: a fixed text that names the rules file and says that it was fixed before the run. |
| 968 | `        control_note='control-I was added after the first numbers of parts A, L and C were seen. It is not part of '` | `control_note`: a fixed text. Control I was added after the first numbers of parts A, L and C were seen. It is not part of (the text goes on in line 969). |
| 969 | `                     'the plan fixed before the run',` | Ends the text of line 968: the plan fixed before the run. |
| 970 | `        F72d12_boot=dict(` | `F72d12_boot`: the reason why the records of F72d12 carry the boot of the rerun. |
| 971 | `            note='the folder of F72d12 holds no boot id. Its process lies between two readings of the same boot id',` | `note`: the folder of F72d12 holds no boot id. Its process lies between two readings of the same boot id. |
| 972 | `            process=[iso(D['rx']['F72d12']['launches']['a6456']['utc']), iso(D['rx']['F72d12']['launches']['a6456']['rc_utc'])],` | `process`: the launch time and the end time of the process of F72d12. |
| 973 | `            boot_id_before=dict(file=rel(try6['path']), line=try6['boot_line'], utc=iso(try6['utc'])),` | `boot_id_before`: the first reading of the boot id: the file `try6.txt`, the line number and the time. |
| 974 | `            boot_id_after=dict(file=rel(GO_LOG), line=D['logs']['go']['states'][0]['line'],` | `boot_id_after`: the second reading: the log of `go.sh` and the line number of its first state line. |
| 975 | `                               utc=iso(D['logs']['go']['states'][0]['utc'])),` | Ends the entry of line 974: the time of that state line. |
| 976 | `            boots_txt_row_0=dict(file=rel(try6['boots_path']), line=try6['boots_line'],` | `boots_txt_row_0`: row 0 of `boots.txt`: the file and the line number. |
| 977 | `                                 first=iso(try6['boots_first']), last=iso(try6['boots_last'])),` | Ends the entry of line 976: the first and the last time of that row. |
| 978 | `            gaps_txt_row_0=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], first=iso(try6['first_log_utc']),` | `gaps_txt_row_0`: row 0 of `gaps.txt`: the file, the line number and the first time of the Linux kernel log. |
| 979 | `                                last=iso(try6['last_log_utc']), hwerr=try6['gaps_hwerr'])),` | Ends the entry of line 978 and the dictionary `F72d12_boot`: the last time of the log and the value `hwerr` of that row. |

### `write_json`: the hardware error records and the firmware settings (lines 980 to 1014)

| Line | Source | Explanation |
|---:|---|---|
| 980 | `        hardware_error_records=dict(` | `hardware_error_records`: a copy of what `hw_records` and `hw_compare` built (`D['hw']`, `D['hw_cmp']`). |
| 981 | `            journal=rel(D['probe13']['h5']),` | `journal`: the path of the saved journal `h-5.txt`, in the short form of `rel`. |
| 982 | `            note='records of the journal of the 2026-11-09 boot inside the window of each process (launch line to rc '` | `note`: a fixed text. It says that these are the records of the journal of the boot of 2026-11-09 inside the window of each process, from the `launch` line to the `rc` (the text goes on in line 983). |
| 983 | `                 'line of launches.txt). One record = one line "Hardware error from APEI ...". offset_s = journal time '` | Text of the note: line of `launches.txt`. One record is one line `Hardware error from APEI ...`. `offset_s` is the journal time (the text goes on in line 984). |
| 984 | `                 'minus launch time; both have a resolution of 1 s. kind: "inside" = the span offset_s - 1 to '` | Text of the note: minus the launch time. Both have a resolution of 1 s. The kind `inside` means that the span from `offset_s - 1` to (the text goes on in line 985). |
| 985 | `                 'offset_s + 1 lies inside a used interval (oldread at position 0 or asmread at position 1), '` | Text of the note: `offset_s + 1` lies inside a used interval. A used interval is `oldread` at position 0 or `asmread` at position 1. |
| 986 | `                 '"possible" = the span and a used interval share a part, "outside" = neither',` | Ends the note: `possible` means that the span and a used interval share a part. `outside` means neither. |
| 987 | `            processes=[dict(dataset=h['dataset'], tag=h['tag'], file=rel(h['file']), launch=iso(h['launch']['utc']),` | `processes`: one entry per process of L-1 to L-4, R0 and R0b. This line: the data set, the tag, the csv file and the launch time. |
| 988 | `                            rc=iso(h['launch']['rc_utc']), n_records=len(h['records']),` | Continues the entry of line 987: the time of the `rc` line and the number of records inside the process window. |
| 989 | `                            records=[dict(journal_line=e['line'], utc=iso(e['utc']), record=e['id'],` | `records`: one entry per record. This line: the line number in the journal, the time and the record number. |
| 990 | `                                          severity=e['severity'], offset_s=e['offset_s'], kind=e['kind'],` | Continues the entry of line 989: the severity, `offset_s` and `kind`. |
| 991 | `                                          interval=None if e['interval'] is None else dict(` | `interval`: `None` for a record of the kind `outside`. A record of the kind `inside` or `possible` carries its interval. |
| 992 | `                                              kernel=e['interval']['kernel'], round=e['interval']['round'],` | The interval: its kernel and its round. |
| 993 | `                                              pos=e['interval']['pos'], line=e['interval']['line'],` | The interval: its position and the line number of its I row. |
| 994 | `                                              t_start_s=round(e['interval']['t_start'], 3),` | The interval: its start time in seconds from the process start, rounded to 0.001 s. |
| 995 | `                                              t_end_s=round(e['interval']['t_end'], 3),` | The interval: its end time, rounded to 0.001 s. |
| 996 | `                                              GBps=r3(e['interval']['total'])))` | The interval: `GBps`, its rate, rounded to 0.001 GB/s by `r3`. The rate is `total`, the sum over the T rows. |
| 997 | `                                     for e in h['records']]) for h in D['hw']],` | Ends the two lists: one entry per record of a process, and one entry per process of `D['hw']`. |
| 998 | `            F72d12=dict(file=rel(try6['gaps_path']), line=try6['gaps_line'], hwerr=try6['gaps_hwerr'],` | `F72d12`: the file `gaps.txt`, the line number of its row 0 and the value `hwerr` of that row. |
| 999 | `                        first=iso(try6['first_log_utc']), last=iso(try6['last_log_utc'])),` | Ends the entry of line 998: the first and the last time of the Linux kernel log in that row. |
| 1000 | `            rerun='Insufficient data: the kernel log was not read during or after the rerun (no root)',` | `rerun`: a fixed text. It says `Insufficient data`: the Linux kernel log was not read during or after the rerun, for lack of root rights. |
| 1001 | `            all_intervals=hw_compare_json(D['hw_cmp'])),` | `all_intervals`: the result of `hw_compare_json` (line 400). Ends the dictionary `hardware_error_records`. |
| 1002 | `        firmware_settings=dict(` | `firmware_settings`: a copy of what `open_fw` read (line 429). |
| 1003 | `            note='no settings list was saved in the boot of the rerun (the settings tool needs root). File times are '` | `note`: a fixed text. No settings list was saved in the boot of the rerun. The reason in the text: the settings tool needs root rights. File times are (the text goes on in line 1004). |
| 1004 | `                 'those of the saved files. "line" of a reply is the line of the file that holds its answer',` | Ends the note: those of the saved files. The value `line` of a reply is the line of the file that holds its answer. |
| 1005 | `            lists={k: dict(file=rel(v['path']), file_time=iso(v['mtime']), entries=v['n'], readable=v['readable'],` | `lists`: the three saved settings lists. Each entry holds the file, the file time, the number of entries and the number of readable entries. |
| 1006 | `                           value_unavailable=v['unavailable'], vstore_error=v['store_error'], values=v['val']) for k, v in D['fw']['lists'].items()},` | Ends the entry of line 1005: the two counts of entries without a value, and the answers of the three settings of line 457. |
| 1007 | `            base_and_revert_hold_the_same_entries=D['fw']['same_entries'],` | `base_and_revert_hold_the_same_entries`: the value `same_entries` of line 467. |
| 1008 | `            set_replies={k: dict(file=rel(v['path']), time_in_line_1=iso(v['when']) if v['when'] else None,` | `set_replies`: the four `set.txt` files. Each entry holds the file and the time of its first line, or `None` when that line holds no time. |
| 1009 | `                                 file_time=iso(v['mtime']),` | Continues the entry of line 1008: the file time. |
| 1010 | `                                 replies=[dict(kind=x['kind'], name=x['name'], answer=x['answer'], modified=x['modified'],` | `replies`: one entry per reply of the file: the kind, the name of the setting, the answer and `modified`. |
| 1011 | `                                               line=x['line']) for x in v['replies']])` | Ends the entry of line 1010: the line number of the reply. |
| 1012 | `                         for k, v in D['fw']['sets'].items()},` | Ends the dictionary `set_replies`: one entry per file. |
| 1013 | `            last_reading=dict(file=rel(D['fw']['final']['path']), file_time=iso(D['fw']['final']['mtime']),` | `last_reading`: the file `setting-final.txt` and its file time. |
| 1014 | `                              text=D['fw']['final']['text'])))` | Ends the dictionary `meta`: the text of the one line of that file. |

### `write_json`: rounding and writing of the file (lines 1015 to 1032)

| Line | Source | Explanation |
|---:|---|---|
| 1015 | `    # The file is written under another name and then renamed, so that a reader never sees a part of it.` | Comment: the file is written under another name and then renamed. So a reader never sees a part of it. |
| 1016 | `    with open(path + '.tmp', 'w') as f:` | Opens the file `facts.json.tmp` in `S` for writing. `with` closes it at the end of the block. |
| 1017 | `        def r3all(o):` | Starts the nested function `r3all`. It goes through nested dictionaries and lists and rounds every float in them. A float is a number with a decimal point in Python. |
| 1018 | `            if isinstance(o, float):` | Tests whether the value is a float. |
| 1019 | `                return r3(o)` | A float is rounded to 3 decimal places with `r3` (line 38). |
| 1020 | `            if isinstance(o, dict):` | Tests whether the value is a dictionary. |
| 1021 | `                return {k: r3all(v) for k, v in o.items()}` | Returns a new dictionary with every value passed through `r3all`. |
| 1022 | `            if isinstance(o, list):` | Tests whether the value is a list. |
| 1023 | `                return [r3all(v) for v in o]` | Returns a new list with every element passed through `r3all`. |
| 1024 | `            return o` | Every other value is returned unchanged. |
| 1025 | `        f.write('{\n"meta": ' + json.dumps(meta, indent=1) + ',\n"verdicts": ' + json.dumps(r3all(V), indent=1)` | Writes the first two parts of the file. `meta` is written as it was built. It does not go through `r3all`. The verdicts `V` are written after `r3all`. `json.dumps` with `indent=1` writes one value per line, with 1 space per nesting level. |
| 1026 | `                + ',\n"intervals": [\n')` | Ends the statement of line 1025: the start of the third part, the list `intervals`. |
| 1027 | `        rounded = lambda r: {k: (r3(v) if isinstance(v, float) else v) for k, v in r.items()}` | `rounded`: a small function that returns a copy of a record in which every float is rounded to 3 decimal places with `r3`. For a rate this is a step of 0.001 GB/s. The float fields of a record are `GBps`, `mesh0_GBps`, `mesh1_GBps`, the three `per_thread` fields, `load1_at_launch` and `gap_s`. A part A rate has 2 decimal places in the csv. So the rounding does not change it. A bwx rate changes. Example: the T rows of the first `oldread` interval in `a6456.csv` of `T72L1` sum to 462.30001702 GB/s. In `facts.json` the record of this interval holds 462.3. |
| 1028 | `        f.write(',\n'.join(json.dumps(rounded(r), separators=(',', ':')) for r in recs))` | Writes one line per record, in the order of `D['recs']`. `separators=(',', ':')` writes a record without spaces. The records in memory keep their values. |
| 1029 | `        f.write('\n]\n}\n')` | Writes the end of the list and of the file. |
| 1030 | `    os.replace(path + '.tmp', path)` | `os.replace` renames `facts.json.tmp` to `facts.json`. A file `facts.json` that exists is replaced in one step. |

### Function `main`: collect, check, render, write (lines 1033 to 1056)

| Line | Source | Explanation |
|---:|---|---|
| 1033 | `def main():` | Starts the function `main`, the entry point of the script. |
| 1034 | `    import facts_text` | Loads the module `facts_text.py`. The import stands inside the function. So it runs when `main` is called. |
| 1035 | `    D = collect()` | `collect` (line 50) reads the result files and builds the records in `D`. |
| 1036 | `    run_checks(D)` | `run_checks` (line 653) appends the 27 checks to `D['checks']`. |
| 1037 | `    V, text = facts_text.render(D)` | `facts_text.render` computes the statistics from the field `GBps` of the records. It returns the verdicts `V` and the text of `FACTS.md` [Ref2]. The lowest, the median and the highest rate of each kernel and the percent values are computed there, not in this file. A failed check stops the script inside this call. `render` calls `section4` of `facts_text4.py`. Unless every check has `ok` true, `section4` ends the script with the message `facts_text.py: the data do not show the pattern of a sentence: all integrity checks pass` [Ref11]. Then no output file is written, and the exit status is 1. A test of 2026-11-24 with a failed check confirmed this: it wrote no file [Ref17]. |
| 1038 | `    write_json(D, V, os.path.join(S, 'facts.json'))` | `write_json` (line 899) writes `S/facts.json`. |
| 1039 | `    with open(os.path.join(S, 'FACTS.md.tmp'), 'w') as f:` | Opens the file `S/FACTS.md.tmp` for writing. |
| 1040 | `        f.write(text)` | Writes the text of the facts sheet into it. |
| 1041 | `    os.replace(os.path.join(S, 'FACTS.md.tmp'), os.path.join(S, 'FACTS.md'))` | Renames `S/FACTS.md.tmp` to `S/FACTS.md`. So a reader never sees a part of the file. |
| 1042 | `    if '--print' in sys.argv:` | Tests whether the argument `--print` was given. `sys.argv` is the list of the arguments of the script. |
| 1043 | `        print(text)` | Then the script prints the text of `FACTS.md`. |
| 1044 | `    bad = [c for c in D['checks'] if not c['ok']]` | `bad`: the list of the checks with `ok` false. |
| 1045 | `    print('checks: %d, failed: %d' % (len(D['checks']), len(bad)))` | Prints the number of checks and the number of failed checks, in the form `checks: N, failed: M`. |
| 1046 | `    for c in bad:` | Loop over the failed checks. |
| 1047 | `        print('  FAILED', c['key'], c['text'])` | Prints one line per failed check: the word `FAILED`, the key and the text of the check. |
| 1048 | `    print('intervals in facts.json: %d' % len(D['recs']))` | Prints the number of records, in the form `intervals in facts.json: N`. |
| 1049 | `    print('Q1:', V['q1'])` | Prints the verdict `Q1`, the answer sentence to the first question of the rerun. |
| 1050 | `    print('Q2:', V['q2'])` | Prints the verdict `Q2`, the answer sentence to the second question. |
| 1051 | `    if bad:` | Tests whether a check failed. |
| 1052 | `        sys.exit(1)` | Then the script ends with exit status 1. In the present code lines 1044 to 1052 are reached only when all checks passed. The reason: `render` stops the script before them when a check failed (line 1037). So `bad` is empty here, no `FAILED` line is printed, and the script ends with exit status 0. |
| 1055 | `if __name__ == '__main__':` | Tests whether the file was started as a script. When another script imports the file, the test is false. |
| 1056 | `    main()` | Then Python calls `main`. |

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
