# Facts sheet: whole-chip read test at 7200 MT/s, rerun of 2026-11-17

- This sheet is the source for the report of the rerun.
- The script `S/build_facts.py` wrote this file from the raw files of section 7. No measured number was typed by hand.
- GB = 1e9 bytes. All times are UTC. A time without a date is on 2026-11-17. A time on another day carries its date in the same sentence or table cell.
- R = `/home/jhan/workspace/titan/cache-perf/crb/results`
- S = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`
- A reference such as [Ref5] points to the file list in section 7.
- Rates are shown to 0.01 GB/s, rounded half up. A median of an even number of values can therefore differ by 0.01 GB/s from the output of stat_k120.py. A difference of two rates is computed from the values before rounding. It can therefore differ by 0.01 GB/s from the difference of the two rounded values.
- Fixed properties of the setup are written as the task and the run scripts give them: the CPU numbers of the two meshes, the loads per 256 B of each kernel, the two memory speeds, and the dates of earlier runs.

## 0. Short version

Q1: yes, at 7200 MT/s with 12 memory modules the new read kernel was still below the old read kernel: 30.5 % to 31.2 % lower when it ran directly after the old read kernel and 29.7 % to 31.1 % lower when it ran directly after asmread (part C, 6 s runs, 4 pairs each).

Q2, old read kernel: by the rule fixed before the run the result against the 8000 MT/s runs is "no difference seen" in the repeat of the 2026-11-13 test (part A, where the test cannot exclude a difference of about 1.2 %, est.) and in part C (about 1.0 %, est.), and the rate was lower in part L (461.61 to 464.29 GB/s, n = 6 intervals / 3 processes / 3 sessions / 1 boot, against 465.53 to 470.05 GB/s, n = 11 intervals / 7 processes / 1 boot), but the data do not show that the boot or the memory speed is the cause.

Q2, new read kernel: asmread (the hand-written loop with the same loads, used in place of the new read kernel) ran above every bwx12 row of the fixed 8000 MT/s list in part L (321.65 to 327.93 GB/s, n = 6 intervals / 3 processes / 3 sessions / 1 boot, against 288.54 to 309.17 GB/s, n = 11 intervals / 7 processes / 1 boot), in control I (313.78 to 317.60 GB/s, n = 4 intervals / 2 processes / no session / 1 boot, added after the first numbers were seen) and in the 2 part C intervals that ran directly after the old read kernel (324.73 to 326.12 GB/s), but an earlier run of the same line in the same 7200 MT/s boot gave 301.90 to 302.78 GB/s (F72d12, n = 2 intervals / 1 process / no session / 1 boot), and each memory speed has one boot, so the data do not show an effect of the memory speed.

More detail for these three sentences:

- Q1, part L (6 s runs): asmread was 29.2 % to 30.5 % below the old read kernel (6 pairs).
- Q1, part A (the repeat of the 2026-11-13 test, whole-pass stop, 0.5 s): the new read kernel was 28.5 % to 31.8 % below the old read kernel (6 pairs of process medians). These percent values are less exact than those of parts L and C (section 3.1).
- Q2, old read kernel, the two comparisons with the wording "no difference seen": part A gave 459.90 to 474.15 GB/s (n = 18 intervals / 6 processes / 3 sessions / 1 boot) against 463.58 to 469.03 GB/s (n = 21 intervals / 7 processes / 1 boot). Part C gave 464.00 to 468.14 GB/s (n = 8 intervals / 4 processes / 3 sessions and 1 extra process / 1 boot) against 465.53 to 470.05 GB/s (n = 11 intervals / 7 processes / 1 boot). The size that the test cannot exclude is the width of the 8000 MT/s range: 1.2 % of its lower end in part A and 1.0 % in part C (est. from one boot). In part A the 7200 MT/s range is wider than the 8000 MT/s range (14.25 GB/s against 5.45 GB/s): 3 of its 18 intervals lie below that range and 3 lie above it (section 4.2).
- Q2, part C: the fixed rules contradict each other here. Rule F2 points 2 and 3 would present part C at 7200 MT/s only. This sheet follows rules V1 point 2, V2 point 4 and V4 and compares part C with the 8000 MT/s rows (decision (r) in section 2).
- Q2, old read kernel: two other rows of the same line in the same 7200 MT/s boot lie inside the range of the 8000 MT/s pool L-1 to L-4. F72d12 (1 process at 20:02 UTC, before the rerun) gave 467.46 to 468.44 GB/s. Control I (2 processes, idle start, added after the first numbers were seen, not part of the plan fixed before the run) gave 466.30 to 469.20 GB/s.
- Q2, old read kernel, view added after the numbers were seen (section 4.2): the 5 bwx12 processes of the pool L-1 to L-4 that started 5 s to 25 s after a 120-thread bwx12 process gave 468.56 to 470.05 GB/s (7 intervals / 5 processes / 1 boot). Part L and part C also started after 120-thread work. Both lie below these 5 processes: part L by 4.27 GB/s and part C by 0.42 GB/s at the nearest ends. Limit: these 5 processes are not all 8000 MT/s processes with that kind of start state. Against the other-binary processes that started after 120-thread work, part C overlaps (bwx11: 467.86 to 469.96 GB/s, 4 intervals / 3 processes. Runner bwx, position 0: 467.34 to 472.95 GB/s, 48 intervals / 24 processes). Part L lies below these rows too.
- Q2, old read kernel: Insufficient data: why part L was lower. The like.spec line, run in turn from an idle start and directly after part A, at least 3 times each, in one boot, would resolve it (the measurement of hypothesis H1 in section 6).
- Q2, new read kernel, asmread in the three visits of the 7200 MT/s boot: F72d12 lies inside the range of the 8000 MT/s pool L-1 to L-4. Against L-1 alone (the baseline row with the identical argument line) it is 1.73 GB/s higher. F72d12 is an idle start only by the load-average rule of this sheet: its process list, written 5 s before the launch, shows pr/ttyAMA-1 at 51.6 %CPU (section 4.6). Control I (idle start, added after the first numbers were seen, not part of the plan fixed before the run) lies above every bwx12 row of the fixed 8000 MT/s list, by 4.61 GB/s at the nearest ends (13.62 GB/s against L-1 alone). The three visits (F72d12, part L, control I) span 301.90 to 327.93 GB/s.
- Q2, new read kernel, part C: asmread directly after oldread (crev, round 1, position 0) gave 324.73 to 326.12 GB/s (n = 2 intervals / 2 processes / session 2 and 1 extra process / 1 boot). By rule V1 point 2 the wording is "differs between the 8000 MT/s boot and the 7200 MT/s boot" against the pool L-1 to L-4 (288.54 to 309.17 GB/s, n = 11 intervals / 7 processes / 1 boot). Part C is higher by 15.56 GB/s at the nearest ends. The baseline matches in the kernel that ran directly before. It does not match in the position: asmread is at position 1 in rows L-1 to L-4. This comparison follows decision (r) in section 2.
- Q2, new read kernel: the new read kernel itself (bw_new read) lies outside (above) the 8000 MT/s range of the same round in session 1 of part A. The bwx12 kernel read has no 8000 MT/s run.
- Q2, machine state: the hardware error records during the rerun are not known (the kernel log was not read). At 8000 MT/s, 2 corrected records fall inside the interval with the lowest asmread value of the pool L-1 to L-4 (288.54 GB/s). Without this interval the pool spans 298.61 to 309.17 GB/s, and no wording changes (sections 4.1 and 4.4). The firmware settings of the boot of the rerun were not read, apart from the memory speed (section 1.5, point 13).
- Q2, new read kernel: Insufficient data: whether a difference comes from the memory speed. Runs in several boots per speed would resolve it.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Read kernel**: the inner loop of the benchmark that reads memory. In this sheet "kernel" means this loop. The operating system kernel is always written "Linux kernel".
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
- **Pass count**: total_bytes / bytes_per_thread of an interval row of part A. For the kernels read and asmread this is the number of buffer passes that all 120 threads completed in the interval. This sheet prints a pass count for these two kernels only. For copy and asmcopy the same division gives 2 x the number of buffer passes, because the binary counts read plus written bytes (header line of each process in threads120.csv: "copy counts read+write bytes"). facts.json holds that value in the field "passes".
- **Rate, total**: part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time. Unit GB/s.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg [Ref143]). "Load at launch" is the 1-minute value read directly before a process starts. The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time that a process has used, divided by the time since the process started [Ref149]. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **pr/ttyAMA-1**: a Linux kernel thread in the process lists. By its name it prints kernel messages to the serial console ttyAMA. This meaning was not checked on CRB.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **GiB**: 2^30 bytes. A "32 GB" module holds 32 GiB [Ref138].
- **Module list**: the output of the command `dmidecode -t 17`, which prints the hardware table of the firmware. It holds one entry "Memory Device" per memory module: 12 entries in the list saved in the boot of the rerun [Ref156], and 10 entries in a 10-module boot by the DIMM report [Ref138].
- **Journal**: the log store of Linux. It keeps the kernel log of earlier boots [Ref138].
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error. Linux prints it in the kernel log with the tag "[Hardware Error]". Its severity is "corrected" (the hardware repaired it) or "recoverable" (not repaired, the system continues) [Ref138].
- **TXREQ settings**: firmware settings that limit the read requests of the cores. They are not memory settings [Ref138]. The saved replies of the settings tool name two of them: "TXREQ Max" and "TXREQ Min" (section 1.5, point 13).
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

The request of 2026-11-17: "Given that the DIMM issue is resolved at 7200 MT/s, let's rerun the whole chip test. Please run old kernel which used portable C code and had read and add, and run new kernel which performed worse than old kernel. Compare the results."

- **Q1**: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much.
- **Q2**: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.

## 1. Run record

### 1.1 Steps and times

- go.sh (the driver script) ran from 22:12:09 to 22:22:18 [Ref23].
- go2.sh (the control, added after the first numbers of parts A, L and C were seen, not part of the plan fixed before the run) ran from 22:23:35 to 22:33:34 [Ref24].
- One session is part A, then part L, then part C. Three sessions ran one after the other. A fourth part C process (T72C4) followed [Ref9].

| Folder tag | What ran | Script start | First process launch | Last process launch | End of last process | Gap before the first launch, s | Source |
|---|---|---|---|---|---|---|---|
| T72A1 | part A, session 1: 24 processes of bw_old and bw_new | 22:12:09 | 22:12:14 | 22:13:27 | 22:13:29 | - | [Ref25] [Ref26] |
| T72L1 | part L, session 1: 1 process of bwx12 | 22:13:29 | 22:13:34 | - | 22:14:36 | 5 | [Ref33] |
| T72C1 | part C (cfwd), session 1: 1 process of bwx12 | 22:14:36 | 22:14:41 | - | 22:15:18 | 5 | [Ref45] |
| T72A2 | part A, session 2: 24 processes of bw_old and bw_new | 22:15:18 | 22:15:23 | 22:16:36 | 22:16:38 | 5 | [Ref27] [Ref28] |
| T72L2 | part L, session 2: 1 process of bwx12 | 22:16:38 | 22:16:43 | - | 22:17:45 | 5 | [Ref37] |
| T72C2 | part C (crev), session 2: 1 process of bwx12 | 22:17:45 | 22:17:50 | - | 22:18:27 | 5 | [Ref49] |
| T72A3 | part A, session 3: 24 processes of bw_old and bw_new | 22:18:27 | 22:18:32 | 22:19:45 | 22:19:47 | 5 | [Ref29] [Ref30] |
| T72L3 | part L, session 3: 1 process of bwx12 | 22:19:47 | 22:19:52 | - | 22:20:54 | 5 | [Ref41] |
| T72C3 | part C (cfwd), session 3: 1 process of bwx12 | 22:20:54 | 22:20:59 | - | 22:21:36 | 5 | [Ref53] |
| T72C4 | part C (crev): 1 process of bwx12 | 22:21:36 | 22:21:41 | - | 22:22:18 | 5 | [Ref57] |
| T72I1 | control I (added after the first numbers were seen): 1 process of bwx12 | 22:27:00 | 22:27:05 | - | 22:28:07 | 287 | [Ref61] |
| T72I2 | control I (added after the first numbers were seen): 1 process of bwx12 | 22:32:27 | 22:32:32 | - | 22:33:34 | 265 | [Ref65] |

- "Script start" is the time in the folder name. ra.sh and rx.sh take it when they start.
- "End of last process" is the `load_after` line of probe.txt for part A. For bwx12 it is the `rc` line of launches.txt.
- "Gap" is the first launch minus the end of the previous 120-thread process of the rerun.
- The time stamps have a resolution of 1 s. rx.sh checks once per second whether its process still runs [Ref19]. So a gap can be up to 2 s longer than the value shown (est.).
- T72A1 has no gap value. It was the first step, and the three load averages at its start were 0.07, 0.02 and 0.00 [Ref23].

### 1.2 Machine state and its proof

The table lists every state line of the two logs and the two state lines of every probe.txt.

| State line | Time | Boot id, first 8 characters | MemTotal, kB | Load average 1 / 5 / 15 min | Runnable / all tasks | Logins | Marker file | Processes per user |
|---|---|---|---|---|---|---|---|---|
| go log, line 6: start | 22:12:09 | 3bfc57a1 | 395392808 | 0.07 / 0.02 / 0.00 | 1 / 1013 | 0 | absent | jhan 11, root 985, 6 system accounts with 6 processes |
| probe.txt of T72A1, start | 22:12:14 | 3bfc57a1 | 395392808 | 0.07 / 0.02 / 0.00 | 2 (read at least 5 s before this time) / not recorded | 0 | not recorded | not recorded |
| go log, line 8: after T72A1 | 22:13:29 | 3bfc57a1 | 395392808 | 80.50 / 24.65 / 8.59 | 1 / 1018 | 0 | absent | jhan 11, root 990, 6 system accounts with 6 processes |
| probe.txt of T72A1, end | 22:13:29 | not recorded | 395392808 | 80.50 / 24.65 / 8.59 | not recorded | not recorded | not recorded | not recorded |
| go log, line 12: after T72L1 | 22:14:36 | 3bfc57a1 | 395392808 | 103.24 / 41.70 / 15.53 | 1 / 1017 | 0 | absent | jhan 11, root 989, 6 system accounts with 6 processes |
| go log, line 16: after T72C1 | 22:15:18 | 3bfc57a1 | 395392808 | 107.23 / 50.93 / 19.86 | 1 / 1016 | 0 | absent | jhan 11, root 988, 6 system accounts with 6 processes |
| probe.txt of T72A2, start | 22:15:23 | 3bfc57a1 | 395392808 | 98.64 / 50.08 / 19.76 | 2 (read at least 5 s before this time) / not recorded | 0 | not recorded | not recorded |
| go log, line 18: after T72A2 | 22:16:38 | 3bfc57a1 | 395392808 | 113.61 / 65.47 / 27.49 | 1 / 1018 | 0 | absent | jhan 11, root 990, 6 system accounts with 6 processes |
| probe.txt of T72A2, end | 22:16:38 | not recorded | 395392808 | 113.61 / 65.47 / 27.49 | not recorded | not recorded | not recorded | not recorded |
| go log, line 22: after T72L2 | 22:17:45 | 3bfc57a1 | 395392808 | 114.40 / 74.54 / 33.15 | 1 / 1023 | 0 | absent | jhan 11, root 995, 6 system accounts with 6 processes |
| go log, line 26: after T72C2 | 22:18:27 | 3bfc57a1 | 395392808 | 111.93 / 78.51 / 36.21 | 1 / 1024 | 0 | absent | jhan 11, root 996, 6 system accounts with 6 processes |
| probe.txt of T72A3, start | 22:18:32 | 3bfc57a1 | 395392808 | 102.96 / 77.21 / 36.02 | 2 (read at least 5 s before this time) / not recorded | 0 | not recorded | not recorded |
| go log, line 28: after T72A3 | 22:19:47 | 3bfc57a1 | 395392808 | 111.98 / 85.23 / 41.99 | 1 / 1025 | 0 | absent | jhan 11, root 997, 6 system accounts with 6 processes |
| probe.txt of T72A3, end | 22:19:47 | not recorded | 395392808 | 111.98 / 85.23 / 41.99 | not recorded | not recorded | not recorded | not recorded |
| go log, line 32: after T72L3 | 22:20:54 | 3bfc57a1 | 395392808 | 114.36 / 90.94 / 47.07 | 1 / 1027 | 0 | absent | jhan 11, root 999, 6 system accounts with 6 processes |
| go log, line 36: after T72C3 | 22:21:36 | 3bfc57a1 | 395392808 | 111.90 / 92.86 / 49.54 | 1 / 1029 | 0 | absent | jhan 11, root 1001, 6 system accounts with 6 processes |
| go log, line 40: after T72C4 | 22:22:18 | 3bfc57a1 | 395392808 | 101.73 / 92.95 / 51.63 | 1 / 1032 | 0 | absent | jhan 11, root 1004, 6 system accounts with 6 processes |
| go log, line 41: end | 22:22:18 | 3bfc57a1 | 395392808 | 101.73 / 92.95 / 51.63 | 1 / 1032 | 0 | absent | jhan 11, root 1004, 6 system accounts with 6 processes |
| go2 log, line 2: start | 22:23:35 | 3bfc57a1 | 395392808 | 29.09 / 72.30 / 47.62 | 1 / 1042 | 0 | absent | jhan 11, root 1014, 6 system accounts with 6 processes |
| go2 log, line 3: idle before T72I1 | 22:27:00 | 3bfc57a1 | 395392808 | 0.95 / 36.39 / 38.17 | 1 / 1042 | 0 | absent | jhan 11, root 1014, 6 system accounts with 6 processes |
| go2 log, line 7: after T72I1 | 22:28:07 | 3bfc57a1 | 395392808 | 76.28 / 51.13 / 43.11 | 1 / 1034 | 0 | absent | jhan 11, root 1006, 6 system accounts with 6 processes |
| go2 log, line 8: idle before T72I2 | 22:32:27 | 3bfc57a1 | 395392808 | 0.99 / 21.40 / 32.57 | 1 / 1037 | 0 | absent | jhan 11, root 1008, 6 system accounts with 6 processes |
| go2 log, line 12: after T72I2 | 22:33:34 | 3bfc57a1 | 395392808 | 70.15 / 38.41 / 37.68 | 1 / 1036 | 0 | absent | jhan 11, root 1008, 6 system accounts with 6 processes |
| go2 log, line 13: end | 22:33:34 | 3bfc57a1 | 395392808 | 70.15 / 38.41 / 37.68 | 1 / 1036 | 0 | absent | jhan 11, root 1008, 6 system accounts with 6 processes |

- **Boot.** All 18 state lines and all 3 probe.txt files hold the full boot id `3bfc57a1-e235-4fe5-8c09-a94642f9b60b`. This is the boot id in line 2 of try6.txt [Ref135].
- **12 modules.** MemTotal is 395392808 kB in every line of the table. try6.txt holds the same value in line 4 and the kernel message "This system has 12 DIMM sockets" in line 5 [Ref135].
- **Why these two values mean 12 modules.** The number in the kernel message is the number of modules that the firmware reports. It is not the number of slots of the board. The saved journal of the boot that started on 2026-11-17 04:17:19 reads "This system has 10 DIMM sockets" in line 2 [Ref154]. The DIMM report lists that boot with 10 modules. It takes the module count of every boot from this kernel line (its section 3) [Ref138].
- **Direct count.** Line 7 of try6.txt reads "12 Configured Memory Speed: 7200 MT/s" [Ref135]. The first number is the number of lines with this text in the module list, one line per module. The DIMM report gives the command: `dmidecode -t 17 | grep "Configured Memory Speed" | sort | uniq -c` (its section 6.3) [Ref138]. The module list that was saved later in the same boot has the file time 20:06:19. That is inside the span of row 0 of boots.txt [Ref137]. It holds 12 entries "Memory Device" and 12 lines "Configured Memory Speed: 7200 MT/s" [Ref156].
- **Memory size.** With 1 kB = 1024 bytes, 395392808 kB are 377.08 GiB. 12 modules of 32 GiB are 384 GiB [Ref138]. The kernel log of the 12-module boot of 2026-11-09 holds the line "Memory: 395280872K/402090256K available" (line 762 [Ref140]). The kernel log of the 10-module boot named above holds "Memory: 329221340K/334981392K available" (line 762 [Ref155]). The second numbers of the two lines differ by 67108864 K. That is 64 x 1024 x 1024 K. The DIMM report reads this as exactly 64 GiB, the size of two modules [Ref138].
- Line 6 of try6.txt reads "modules=24". This is not the module count. The module list holds 24 lines that contain the text "Size: 32 GB": 12 lines "Size: 32 GB" and 12 lines "Volatile Size: 32 GB" [Ref156]. Hypothesis, not checked: the script that wrote try6.txt counted these 24 lines. That script is not among the files of this task.
- **7200 MT/s.** Line 7 of try6.txt reads "12 Configured Memory Speed: 7200 MT/s". It was recorded at 20:02:21 in the same boot [Ref135]. The speed was not read again during the rerun, because that needs root. The proof for the rerun is the equal boot id. Assumption, not measured: the speed does not change inside one boot. The firmware applies the setting at the next start [Ref138].
- **Time since boot.** The first kernel log line of this boot is from 20:02:16 [Ref136]. go.sh started 2 h 9 min 53 s later.
- **Linux kernel command line** (line 2 of the go.sh log [Ref23]): `BOOT_IMAGE=/vmlinuz-7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 root=UUID=86f7cf19-9959-4dba-91b1-0052c9d45c21 ro isolcpus=domain,managed_irq,126-127 irqaffinity=0-119 cpufreq.default_governor=performance rcupdate.rcu_normal=1 console=tty1 console=ttyAMA0`
- **Governor.** 120 of the CPUs 0-119 use the governor "performance". `scaling_cur_freq` of CPU 0 was 2800000 (line 3 of the go.sh log [Ref23]). The unit of that file is kHz [Ref142], so the value is 2.8 GHz.
- **Huge page setting.** `transparent_hugepage/enabled` = `[always] madvise never`. `defrag` = `always defer defer+madvise [madvise] never` (line 4 of the go.sh log [Ref23]). The value in brackets is the active one.
- **Runnable tasks in probe.txt.** ra.sh reads the value in its wait loop, then sleeps 5 s, and then writes the probe line with a new time and a new load average [Ref10]. So the value 2 is from at least 5 s before the time shown in the table. The count at the first launch of part A is not recorded.
- **Logins.** Every state line shows 0 logins. Every probe.txt and every launch line of rx.sh shows 0 logins too.
- **Processes per user.** Only these users own processes in the 18 state lines: jhan, messagebus, polkitd, root, syslog, systemd-network, systemd-resolve, systemd-timesync. No other user appears.
- The user jhan owns 11 processes in every state line. root owns 985 to 1014. The 6 system accounts own 1 each.
- **Marker file.** It is "absent" in all 18 state lines.
- **CPU affinity of go.sh.** `affinity of this shell: pid 4864's current affinity list: 0-119` (line 5 of the go.sh log [Ref23]).
- **Hardware error records.** The kernel log was not read during or after the rerun (no root). try6.txt shows `hwerr=0` at 20:02:21, at the start of this boot [Ref135].

### 1.3 System load at every launch

The value is the 1-minute load average of Linux, read by the run script directly before it starts a process.

Part A. ra.sh writes the value into the "-- binary" line of each of the 24 processes.

| Session | Load average 1 / 5 / 15 min before the first process (probe.txt) | Runnable tasks at the end of the wait of ra.sh (at least 5 s before the probe line) | Load at the first process | Lowest load of the 24 launches | Highest load of the 24 launches | Launches | Load average after the last process | Highest %CPU in the process list of probe.txt | Source |
|---|---|---|---|---|---|---|---|---|---|
| T72A1 | 0.07 / 0.02 / 0.00 | 2 | 0.07 | 0.07 | 77.06 | 24 | 80.50 / 24.65 / 8.59 | 0.3 | [Ref25] [Ref26] |
| T72A2 | 98.64 / 50.08 / 19.76 | 2 | 98.64 | 98.64 | 112.71 | 24 | 113.61 / 65.47 / 27.49 | 0.1 | [Ref27] [Ref28] |
| T72A3 | 102.96 / 77.21 / 36.02 | 2 | 102.96 | 98.02 | 111.98 | 24 | 111.98 / 85.23 / 41.99 | 0.1 | [Ref29] [Ref30] |

Parts L and C and control I. rx.sh writes the value into the launch line of launches.txt.

| Folder tag | Launch | Load 1 min | Load 5 min | Load 15 min | Runnable / all tasks | Logins | Highest %CPU in the process list of env.txt | Source |
|---|---|---|---|---|---|---|---|---|
| T72L1 | 22:13:34 | 74.05 | 24.24 | 8.54 | 1 / 1019 | 0 | 0.1 | [Ref33], process list [Ref32] |
| T72C1 | 22:14:41 | 94.97 | 41.01 | 15.45 | 1 / 1018 | 0 | 0.1 | [Ref45], process list [Ref44] |
| T72L2 | 22:16:43 | 104.52 | 64.38 | 27.34 | 1 / 1019 | 0 | 0.1 | [Ref37], process list [Ref36] |
| T72C2 | 22:17:50 | 105.24 | 73.30 | 32.97 | 1 / 1024 | 0 | 0.1 | [Ref49], process list [Ref48] |
| T72L3 | 22:19:52 | 103.01 | 83.82 | 41.76 | 1 / 1026 | 0 | 0.1 | [Ref41], process list [Ref40] |
| T72C3 | 22:20:59 | 105.20 | 89.43 | 46.82 | 1 / 1028 | 0 | 0.1 | [Ref53], process list [Ref52] |
| T72C4 | 22:21:41 | 102.94 | 91.31 | 49.28 | 1 / 1030 | 0 | 0.1 | [Ref57], process list [Ref56] |
| T72I1 | 22:27:05 | 0.87 | 35.79 | 37.97 | 1 / 1043 | 0 | 0.1 | [Ref61], process list [Ref60] |
| T72I2 | 22:32:32 | 0.91 | 21.05 | 32.39 | 1 / 1038 | 0 | 0.1 | [Ref65], process list [Ref64] |

- In session 1 of part A the load at launch rose from 0.07 at the first process to 77.06 at the last process.
- All launches of sessions 2 and 3 of part A and all launches of parts L and C saw a load of 74.05 to 112.71.
- The two launches of control I started at a load of 0.87 and 0.91.
- At every bwx12 launch 1 task was runnable (launch line of launches.txt).
- The process lists of env.txt show at most 0.1 %CPU. rx.sh writes env.txt when it starts [Ref19]. That was 5 s before each of the 9 launches (first line of env.txt against the launch line). %CPU is an average over the life of a process (see the word list). So the lists would show a new busy process. They cannot show a short busy phase of a process that has run since the boot.
- The process lists of probe.txt (part A) were written at the time of the probe line, directly before the first process [Ref10]. The same limit of %CPU holds for them.
- Hypothesis: the high load values come from the rerun's own 120-thread processes. Linux averages the load over the last 1, 5 and 15 minutes [Ref143], so the value stays high for some time after a process ends. The first launch of each of the 9 steps from T72L1 to T72C4 came 5 s after such an end (table of section 1.1). T72A1 had no earlier process of the rerun (load 0.07 at launch). T72I1 and T72I2 came 287 s and 265 s after one (load 0.87 and 0.91 at launch). The later launches of part A followed the previous part A process with no wait [Ref10]. The runnable counts and the 0 logins fit this. The process lists cannot test it (see the limit of %CPU above). A check that would confirm or reject it: sample /proc/loadavg and the list of running processes once per second between two steps. This was not done.

### 1.4 Integrity checks

1. pass: R/go-T72-20261117T221209Z.log: the last line is ALLDONE: yes. Lines that start with FAILED: 0.
2. pass: R/go2-T72-20261117T222335Z.log: the last line is ALLDONE: yes. Lines that start with FAILED: 0.
3. pass: boot id: 18 state lines of the two logs and 3 probe.txt files hold 1 distinct value(s). Equal to line 2 of try6.txt: yes.
4. pass: MemTotal: 18 state lines and 6 probe.txt values (start and end of each session) hold 1 distinct value(s): 395392808 kB. Equal to line 4 of try6.txt: yes.
5. pass: logins and marker file: logins = 0 and marker "absent" in 18 of 18 state lines. Logins = 0 in 3 of 3 probe.txt files and in 9 of 9 launch lines.
6. pass: part A, processes x intervals per threads120.csv (expected 24 x 3, 120 threads in every row): T72A1 24 x 3, 72 rows, threads 120, T72A2 24 x 3, 72 rows, threads 120, T72A3 24 x 3, 72 rows, threads 120.
7. pass: part A, order of the 24 processes (binary, kernel, round) equal to threads120.csv of 2026-11-13: T72A1 yes, T72A2 yes, T72A3 yes.
8. pass: "I" rows per bwx12 csv (expected 10 for parts L and I, 6 for part C): T72L1 10, T72L2 10, T72L3 10, T72C1 6, T72C2 6, T72C3 6, T72C4 6, T72I1 10, T72I2 10.
9. pass: launches.txt, one launch line with "rc 0" per folder: T72L1 rc 0, T72L2 rc 0, T72L3 rc 0, T72C1 rc 0, T72C2 rc 0, T72C3 rc 0, T72C4 rc 0, T72I1 rc 0, T72I2 rc 0.
10. pass: stderr.txt, bytes per folder (expected 0): T72L1 0, T72L2 0, T72L3 0, T72C1 0, T72C2 0, T72C3 0, T72C4 0, T72I1 0, T72I2 0.
11. pass: intervals with 120 threads = 64 on CPUs 0-63 + 56 on CPUs 64-119, on 120 different CPUs: T72L1 10 of 10, T72L2 10 of 10, T72L3 10 of 10, T72C1 6 of 6, T72C2 6 of 6, T72C3 6 of 6, T72C4 6 of 6, T72I1 10 of 10, T72I2 10 of 10.
12. pass: flags column of the T rows (one row per thread and interval): 8880 rows in the 9 files, distinct values ['-'], rows that are not "-": T72L1 0, T72L2 0, T72L3 0, T72C1 0, T72C2 0, T72C3 0, T72C4 0, T72I1 0, T72I2 0.
13. pass: "P" rows (one per thread before the first interval and after each interval): kB_total [262144] in all rows. Rows with kB_huge equal to kB_total: T72L1 1320 of 1320, T72L2 1320 of 1320, T72L3 1320 of 1320, T72C1 840 of 840, T72C2 840 of 840, T72C3 840 of 840, T72C4 840 of 840, T72I1 1320 of 1320, T72I2 1320 of 1320. Values of thp_fault_fallback: [0].
14. pass: total of the T rows against aggregate_GBps of the "I" row of the same interval, largest difference in GB/s (pass limit set by this script: below 0.05 GB/s): T72L1 0.018, T72L2 0.015, T72L3 0.013, T72C1 0.010, T72C2 0.014, T72C3 0.010, T72C4 0.015, T72I1 0.015, T72I2 0.012.
15. pass: tag and arguments of the launch line equal to the spec file: T72L1 like.spec yes, T72L2 like.spec yes, T72L3 like.spec yes, T72C1 cfwd.spec yes, T72C2 crev.spec yes, T72C3 cfwd.spec yes, T72C4 crev.spec yes, T72I1 like.spec yes, T72I2 like.spec yes.
16. pass: argument line of like.spec equal to the a6456 launch line of L-1 (w120-R8) and of F72d12: yes.
17. pass: sha256 of bw_old (e8fc0205...) and bw_new (fd7c14df...): the 3 probe.txt files of part A equal lines 19 and 20 of probe.txt of 2026-11-13: yes. env.txt of partA-20261113T205055Z holds the same two values: yes.
18. pass: sha256 of ra.sh in the 3 probe.txt files equal to S/ra.sh (6d67715e...): yes.
19. pass: sha256 of bwx12 in env.txt: 1 distinct value(s) in the 9 folders of parts L, C, I (cd58e564...). Equal to SHA= in go.sh: yes. The same value is in env.txt of L-1, L-2, L-3, L-4, X2d12, F72d12, X1d10, X1d10b, BASEd10.
20. pass: sha256 of the 6 local run files (cfwd.spec, crev.spec, go.sh, go2.sh, like.spec, ra.sh) equal to the lists local.sha and go2.sha: yes.
21. pass: Linux kernel release: 1 distinct value(s) in the 3 probe.txt and 9 env.txt files. Equal to the image name of the command line: yes.
22. pass: runnable tasks: 1 at the 9 bwx12 launches (launch line of rx.sh). Part A: the value runnable=2 of the 3 probe.txt files is the last value of the wait loop of ra.sh (ra.sh waits for 2 or fewer). ra.sh reads it, then sleeps 5 s, then writes the time and the load of the probe line. So the value is from at least 5 s before the time of the probe line, and the count at the first launch of part A is not recorded.
23. pass: cross-check with stat_k120.py: 333 interval rows (3 sessions of part A, A-1, and the copies of A-2 and A-3 under S/base8000, while this script reads the raw A1.csv and A3.csv) are equal in rate, per-thread minimum and maximum, and pass count: yes.
24. pass: cross-check with stat_bwx.py: 297 intervals of 20 folders (the 9 folders of parts L, C, I with 74 intervals, and the 17 csv files that section 7 lists from the 11 earlier rx.sh and r0.sh folders with 223 intervals) are equal in total, sum per mesh, the 64+56 test and the count of flagged rows: yes.
25. pass: earlier bwx intervals used in sections 3 and 4: 386 of 386 are 64+56 intervals with 0 flagged T rows. The 11 earlier rx.sh and r0.sh folders hold 0 bytes of stderr.txt in total. The rc values of their 17 processes used: 0.
26. pass: sha256 of the local rx.sh (d315814f...) equal to RXSHA= in go.sh and go2.sh: yes. Both scripts hold the line that tests this value with sha256sum on CRB and stops with "FAILED: rx.sh is not the script of 2026-11-15" when the copy on CRB differs: yes. Lines that start with FAILED in the two logs: 0. Limit: the 2 logs, the 3 probe.txt files and the 9 env.txt files of the rerun hold no sha256 of rx.sh, go.sh or go2.sh. So this check uses the local copies of go.sh and go2.sh (check 20).
27. pass: part A, arguments. The "-- binary" header lines of the 3 threads120.csv files of part A are equal to those of threads120.csv of 2026-11-13 in binary, kernel, threads, cpus, bytes and round: 72 of 72 lines (threads 120, cpus 0-119, bytes 256M in every line). The header line that the binary prints ends with "threads=120 bytes_per_thread=268435456 min_ms=500 thp=madvise" in all 96 processes of the 4 files. The function one() of ra.sh (lines 39 to 43) is equal to lines 60 to 64 of run_kernels.sh: yes. Its process line ends with the options "--reps 3 --min-ms 500": yes. sha256 of the local run_kernels.sh equal to line 18 of probe.txt of 2026-11-13: yes.

- Were the buffers on 2 MiB pages? Parts L, C and I: yes. Every "P" row shows the whole buffer (262144 kB) on huge pages (check 13). Part A: not recorded. bandwidth.c prints only the setting `thp=madvise` in its header line.

### 1.5 Limits: differences between the procedure of 2026-11-13 and part A

The timed part is the same: same two binaries (check 17), same arguments (check 27), same order of the 24 processes (check 7). The list below holds the differences that were found. It is not proven to be complete. Point 12 holds the Linux settings that were compared without a difference. Point 13 holds what is on record about the firmware settings. The list follows findings F9 and F1 of the review [Ref8].

1. **One-thread phase.** On 2026-11-13 the script first ran 192 one-thread processes, from 18:12:23 to 18:17:20 [Ref69]. The first 120-thread process started at 2026-11-13 18:17:21 with a load of 1.00 [Ref67]. Part A has no one-thread phase.
2. **Start state of the sessions.** Session 1 started from an idle machine, 5 s after go.sh started (1-minute load average 0.07). Session 2 started 5 s after the 120-thread bwx12 process T72C1. Session 3 started 5 s after the 120-thread bwx12 process T72C2.
3. **Wait before the first process.** ra.sh waits until 2 or fewer tasks are runnable and then sleeps 5 s [Ref10]. The script of 2026-11-13 built the binaries, ran a self-test and the one-thread phase, and had no wait [Ref22].
4. **Memory speed.** 8000 MT/s then, 7200 MT/s now. This is the intended change.
5. **Boot and time since boot.** The run of 2026-11-13 was in the boot that started on 2026-11-09 21:20:15 [Ref139]. Its first 120-thread process started 3.9 days after that. The rerun started 2 h 9 min 53 s after the start of its boot.
6. **Speed and boot changed together.** Each memory speed has exactly one boot in this comparison.
7. **2 MiB pages.** Neither script records the page state of the buffers for part A.
8. **Hardware error records.** The journal of the 2026-11-09 boot holds its first record at 2026-11-13 18:13:12 (line 3), during the one-thread phase of that run. It holds 0 records between 2026-11-13 18:17:21 and 2026-11-13 18:18:37, the 120-thread part of baseline A-1 [Ref139]. During baseline A-2 (A1.csv, 2026-11-13 20:50:55 to 2026-11-13 20:51:35 [Ref70] [Ref144]) the same journal holds 4 records with the severity "corrected": 2 at 2026-11-13 20:50:58, the second in which the process read_new-r1 (bw_new read) was launched (journal lines 121 and 149), and 2 at 2026-11-13 20:51:10, during the process write_new-r1 (bw_new write), launched at 2026-11-13 20:51:08 (journal lines 180 and 208). During the three processes of baseline A-3 (2026-11-13 20:58:16 to 2026-11-13 20:58:43 [Ref71]) it holds 0 records. For the rerun the kernel log was not read (no root). Insufficient data: whether records occurred during the rerun. A count of the "[Hardware Error]" lines of the kernel log after the run would resolve it (needs root). Section 4.1 gives the records during the bwx12 and bwx11 rows of the same boot.
9. **Module count of the 2026-11-13 run.** Its probe.txt holds no MemTotal and no boot id [Ref68]. The count comes from the saved journal: the boot started on 2026-11-09 21:20:15 with the line "This system has 12 DIMM sockets" [Ref139], and the saved kernel log of that boot ends with a line dated "Nov 17 03:44:00" [Ref140].
10. **Memory speed of the baseline boot.** No reading of the applied speed was saved in that boot. The firmware settings list with the file time 2026-11-17 02:09, which lies inside that boot, shows "DIMM Frequency" = "8000 MT/s" [Ref141]. The DIMM report gives 8000 MT/s as the setting until 2026-11-17 19:43 [Ref138].
11. **Second baseline A-2.** It ran the same binaries with `--cpus 0-63,64-119 --per-thread` in another process order, 12 processes, no copy kernels [Ref70]. It started 8 s after the end of a run of 68 s that held one-thread processes only. That run is the folder R/partA-20261113T204939Z. It started at 2026-11-13 20:49:39 and ended at 2026-11-13 20:50:47 (lines 1 and 19 of its env.txt [Ref150]). It ran 20 processes of bw_new, all with `--threads 1`: 4 in A5.csv and 16 in A6.csv, launched from 2026-11-13 20:49:39 to 2026-11-13 20:50:45 [Ref151] [Ref152]. Its launches.txt lists these 20 processes and no other [Ref153]. The first process of A1.csv started at 2026-11-13 20:50:55 with a 1-minute load average of 0.64 [Ref70].
12. **Compared between the two boots, no difference found.** Only these four settings of Linux were compared. Point 13 gives the firmware settings.
    - Linux kernel release: `7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858` in line 1 of the saved journal of the 2026-11-09 boot [Ref139] and in the command line of the rerun (line 2 of the go.sh log [Ref23]).
    - Linux kernel command line: the file cmdline.txt was saved on 2026-11-17 03:43:42 [Ref145] [Ref146]. By the boot history of the DIMM report that time lies inside the 2026-11-09 boot [Ref138]. Its text is equal to line 2 of the go.sh log [Ref23].
    - Governor: gov.txt of the same save holds the two lines "128 performance" and "2800000" [Ref147]. The file does not name them. The go.sh log holds "120 performance" for the CPUs 0-119 and `scaling_cur_freq` 2800000 for CPU 0 (line 3 [Ref23]). So the governor name is equal. The number 2800000 is equal too, but gov.txt does not say which CPU and which value it is.
    - Huge page setting: line 2 of env.txt of the A-2 run holds `[always] madvise never` and defrag `always defer defer+madvise [madvise] never` [Ref72]. thp.txt of the save named above holds `[always] madvise never` [Ref148]. Line 4 of the go.sh log holds the same values [Ref23].
13. **Firmware settings.** No settings list was saved in the boot of the rerun. The settings tool (`uefisettings`, a tool of Arm that reads and writes firmware settings) needs root [Ref138]. The saved records of the tool show this:
    - Baseline boot. The settings list with the file time 2026-11-17 02:09:50 holds 1490 entries. 604 have a readable value, 883 show "ValueUnavailable", and 3 show "VStoreError" (the tool could not read the value). It shows "TXREQ Max" = "Full L2 TQ", "TXREQ Min" = "1/32 L2 TQ" and "DIMM Frequency" = "8000 MT/s" [Ref141].
    - Changes for another test. Line 1 of set.txt of the folder x1 holds the date 2026-11-17 03:43:50. The file holds the reply "TXREQ Min" = "1/4 L2 TQ" (answer in line 9) with "modified: true" [Ref157]. Line 1 of set.txt of the folder x2 holds the date 2026-11-17 04:05:38. The file holds the reply "TXREQ Max" = "1/4 L2 TQ" with "modified": true (line 2) [Ref158].
    - Set back. Line 1 of set.txt of the folder revert holds the date 2026-11-17 04:13:19. The file holds the replies "TXREQ Max" = "Full L2 TQ" (line 2) and "TXREQ Min" = "1/32 L2 TQ" (line 4), both with "modified": true. Both values were read back in lines 6 and 8 [Ref159]. They are the values of the list of the baseline boot.
    - After the set-back. The settings list with the file time 2026-11-17 04:17:38 holds the same 1490 entries as the list of the baseline boot: the two lists are equal in the name, the answer, the options and the help text of every entry. The order of the entries differs [Ref160]. So the 604 readable values are equal. The 886 other values were not compared.
    - Memory speed. set.txt of the folder dimm7200-20261117 has the file time 2026-11-17 19:43:03. It holds one reply: "DIMM Frequency" = "7200 MT/s" (answer in line 8) with "modified: true" [Ref162]. setting-final.txt of that folder has the file time 20:06:19. That is inside the span of row 0 of boots.txt, the boot of the rerun [Ref137]. It holds the one line `answer: "7200 MT/s",` [Ref163]. The file does not name the setting. The DIMM report gives this reading as the setting "DIMM Frequency" (its section 6.3) [Ref138].
    - Search. A search of R by file name finds 4 files set.txt and 3 files questions.json. These are the 4 reply files and the 2 lists named in this point, and one more list with the file time 2026-11-17 03:48:37, saved after the first change. That list differs from the list of the baseline boot in one entry: "TXREQ Min" = "1/4 L2 TQ" [Ref161]. Among the 4 reply files, the only one that is later than the set-back is the change of "DIMM Frequency". A change that was made without a saved reply would not be on record here.
    - Limits. The newest settings list has the file time 2026-11-17 04:17:38. That is before the first kernel log line of the boot of the rerun (20:02:16, section 1.2). In each of the 3 saved lists 883 of the 1490 entries show "ValueUnavailable" in place of a value. The file times are those of the saved files. Insufficient data: the firmware settings in boot 3bfc57a1, apart from the memory speed. A settings list saved in that boot would resolve it (needs root).

Text required by rule F1 point 5 [Ref7]: The one-thread phase of the 2026-11-13 run was not repeated. Whether the work before the first 120-thread process changes the rate of the new read kernel is not known (Insufficient data: a run with the new kernel at several positions, after an idle start and after 120-thread work, would settle it). At 8000 MT/s the old read kernel gave 464.42 to 467.06 GB/s after one-thread work and directly after 120-thread work (rows A-1 and A-2, 12 intervals / 4 processes / 1 boot).
- Where the words of the last sentence come from. In both rows the round-1 process of bw_old read is the first process of the file. It started after one-thread work (points 1 and 11). The round-2 process is the last process of the file. The process before it in the file is the 120-thread process of bw_new read. That process was launched 2 s before it in row A-1 and 3 s before it in row A-2 [Ref67] [Ref70].

## 2. Decisions made by the agent for this run

These are decisions. They are not facts about the machine.

Decisions made before or during the run:

- (a) "Whole chip test" was read as the 120-thread part of run_kernels.sh of 2026-11-13 [Ref22]. The one-thread part was not repeated.
- (b) "Old kernel" = the kernel `read` of bw_old. "New kernel" = the kernel `read` of bw_new. Both binaries are the files of 2026-11-13 by sha256 (check 17).
- (c) Part A ran all six kernels (read, write, copy, asmread, asmwrite, asmcopy) to keep the process order of 2026-11-13. Statements are made for the read kernels only (rule V3 [Ref7]).
- (d) Parts L and C were added. Reason: FINDINGS.md section F1 shows that the 0.5 s whole-pass stop rule of bandwidth.c distorts totals [Ref21].
- (e) Three sessions ran one after the other without a pause, plus a fourth part C process. So part C has 2 processes per kernel order.
- (f) No root was used. So the memory speed is proven through the boot id only, and the kernel log was not read.
- (g) Control I was added after the first numbers of parts A, L and C were seen. Reason: an earlier run of the same line in the same boot (F72d12, 20:02 UTC) gave a lower asmread total than part L. Control I is therefore not part of the plan fixed before the run.
- (h) The baseline list and the comparison rules were fixed before go.sh started. The rules file has the file time 22:11:51 on the clock of the agent's server, and its line 2 says that go.sh had not yet started [Ref7]. S/local.sha, the sha256 list of the run files, has the file time 22:12:03 on the same clock, 12 s later [Ref15]. go.sh started at 22:12:09 by the clock of CRB [Ref23]. That is about 18 s after the rules file (est.: the two clocks were not compared).

Decisions made while this sheet was built, after the numbers were seen:

- (i) Rate per interval. Part A uses the column aggregate_GBps of the file. The bwx runners use the sum over the threads of bytes / elapsed time. This is the method of stat_k120.py and stat_bwx.py. facts.json holds the rates rounded to 0.001 GB/s.
- (j) Ratio new/old in part A = median of the 3 intervals of the bw_new process divided by the median of the 3 intervals of the bw_old process of the same session and round. The lowest and the highest ratio of single intervals are given beside it. The lowest ratio is the lowest bw_new interval divided by the highest bw_old interval of the same session and round. The highest ratio is the highest bw_new interval divided by the lowest bw_old interval. These are the two extremes over all 9 pairs of one bw_new interval and one bw_old interval. They are not the ratios of the intervals with the same number.
- (k) Range of the 8000 MT/s side in the overlap test of rule V1 point 2, parts L and C: the pool of the baseline row L-1 and the supporting rows L-2 to L-4 (all bwx12). The result against L-1 alone and against the pool with the other-binary rows is shown beside it, so the reader can see whether this choice matters.
- (l) From every earlier bwx12 and bwx11 row only oldread at position 0 and asmread at position 1 are used. These are the positions of part L.
- (m) Row X2d12 is shown and not used. Rule V4 lists it as "not a baseline" (firmware test setting). Rules V2 point 4 and F2 point 2 name it as a baseline. The two texts contradict each other. This sheet follows V4, because V4 is the fixed list.
- (n) The sums per mesh in section 4.7 were compared after the numbers were seen. That comparison is not part of the rules fixed before the run.
- (o) The view "equal pass count" in section 4.3 and the table of thread rates under it were added after the numbers were seen. They are not part of rule V3. Both keep the two rounds apart.
- (p) Rows of runner bwx (other binary) as the reference of part C. Rule V4 names for the two B7 folders the tags common-6000-common-p1 to p4. Rule V2 point 4 names the tags common-6000-* (24 processes in the 4 folders B7a, B7b, C3a, C3b). The two texts contradict each other. This sheet uses the 24 processes of rule V2 point 4, because that rule defines the comparison per position and quotes the ranges of these 24 processes. This is the opposite choice to decision (m). 12 of the 24 processes used --start offset. Section 4.5 shows the values of the 12 processes with --start common beside the pool. No verdict rests on these rows.
- (q) The view "pool L-1 to L-4 split by the start state" in section 4.2 was added after the numbers were seen. It is not part of the rules fixed before the run.
- (r) Part C against 8000 MT/s. Rule F2 point 2 says: "bwx12, 7200 against 8000 MT/s: use part L only". Rule F2 point 3 says: "Part C: present it as old against new at 7200 MT/s only." Rule V1 point 2 asks for the comparison "Per part (A, L, C) and kernel". Rule V2 point 4 names the 8000 MT/s reference of each group of part C. The part C list of rule V4 says: "oldread, asmread: the part L list". The texts contradict each other [Ref7]. This sheet follows V1, V2 and V4. It gives a wording by rule V1 point 2 for two rows of part C: oldread, and asmread directly after oldread. Reason 1: V4 is the fixed list of baselines, and it names a baseline for these two kernels of part C. Decision (m) follows V4 on the same ground. Reason 2: finding F2 is about the kernel `read`, which has no bwx12 run at 8000 MT/s, and this sheet gives no wording for `read`. Reason 3: point 3 of F2 itself speaks of an 8000 MT/s column for part C. Its second sentence reads: "In any 8000 MT/s column, the cell of "read" must say "no bwx12 run" and must not hold the asmread value." If F2 points 2 and 3 are followed instead, this sheet gives neither of the two wordings, and the view by start state of section 4.2 has no part C row. Each place that gives one of the two wordings names this decision. For the three sentences of the Short version the detail list under them names it. The part C rows of the view by start state name it too. Part C would then still be shown next to 8000 MT/s rows in at least three kinds of places. First, the sums per mesh of section 4.7 and item 9 of "Established" in section 6: both name this decision and give the oldread result without part C too. Second, the comparisons with the rows of runner bwx in sections 4.2, 4.5 and 4.6: rules V2 point 4 and F2 point 4 name such rows as references, and this sheet labels them as rows of another binary. Third, the rows without a wording in the two part C tables of sections 4.2 and 4.5. So this sheet does not claim that part C would then answer Q1 only.

## 3. Q1: old against new at 7200 MT/s

### 3.1 Part A: bw_old and bw_new, whole-pass stop, 0.5 s, 3 intervals per process

Start state of the sessions:

- Session 1 (T72A1) started from an idle machine, 5 s after go.sh started (1-minute load average 0.07).
- Session 2 (T72A2) started 5 s after the 120-thread bwx12 process T72C1.
- Session 3 (T72A3) started 5 s after the 120-thread bwx12 process T72C2.

One row is one process. A cell shows the rate in GB/s and, in brackets, the pass count of the interval.

| Session | Start state of the session | Round | Binary and kernel | Launch | Load at launch | Interval 1, GB/s (passes) | Interval 2 | Interval 3 | Median, GB/s | Slowest to fastest thread, GB/s | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 1 | bw_old read (old read kernel) | 22:12:14 | 0.07 | 467.83 (954) | 467.92 (951) | 465.38 (944) | 467.83 | 2.98 to 4.95 | [Ref25], lines 4-6 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 1 | bw_new read (new read kernel) | 22:12:16 | 0.07 | 330.59 (664) | 330.09 (664) | 333.25 (664) | 330.59 | 2.63 to 3.03 | [Ref25], lines 11-13 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 1 | bw_old asmread | 22:12:33 | 28.45 | 321.15 (664) | 326.26 (664) | 322.56 (664) | 322.56 | 2.54 to 2.96 | [Ref25], lines 46-48 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 1 | bw_new asmread | 22:12:35 | 28.45 | 321.15 (664) | 325.55 (664) | 321.79 (664) | 321.79 | 2.57 to 2.96 | [Ref25], lines 53-55 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 2 | bw_old read (old read kernel) | 22:13:27 | 77.06 | 461.71 (921) | 461.33 (920) | 459.90 (919) | 461.33 | 3.00 to 5.11 | [Ref25], lines 165-167 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 2 | bw_new read (new read kernel) | 22:13:25 | 77.06 | 327.60 (664) | 332.82 (664) | 326.68 (664) | 327.60 | 2.60 to 3.03 | [Ref25], lines 158-160 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 2 | bw_old asmread | 22:13:08 | 64.84 | 331.23 (664) | 340.22 (699) | 336.20 (720) | 336.20 | 2.64 to 3.04 | [Ref25], lines 123-125 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 2 | bw_new asmread | 22:13:06 | 59.95 | 331.77 (664) | 331.36 (664) | 331.73 (664) | 331.73 | 2.62 to 3.01 | [Ref25], lines 116-118 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 1 | bw_old read (old read kernel) | 22:15:23 | 98.64 | 468.21 (956) | 468.62 (954) | 467.85 (953) | 468.21 | 2.99 to 4.94 | [Ref27], lines 4-6 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 1 | bw_new read (new read kernel) | 22:15:25 | 98.64 | 322.67 (664) | 325.26 (664) | 324.42 (664) | 324.42 | 2.61 to 2.96 | [Ref27], lines 11-13 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 1 | bw_old asmread | 22:15:42 | 103.37 | 317.29 (664) | 318.93 (664) | 317.63 (664) | 317.63 | 2.53 to 2.90 | [Ref27], lines 46-48 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 1 | bw_new asmread | 22:15:44 | 104.95 | 323.23 (664) | 324.52 (664) | 323.46 (664) | 323.46 | 2.58 to 2.95 | [Ref27], lines 53-55 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 2 | bw_old read (old read kernel) | 22:16:36 | 112.71 | 467.52 (957) | 467.55 (961) | 465.89 (944) | 467.52 | 2.96 to 4.95 | [Ref27], lines 165-167 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 2 | bw_new read (new read kernel) | 22:16:34 | 112.71 | 330.32 (664) | 328.62 (664) | 328.96 (664) | 328.96 | 2.62 to 3.00 | [Ref27], lines 158-160 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 2 | bw_old asmread | 22:16:17 | 109.82 | 328.16 (664) | 327.55 (664) | 322.57 (664) | 327.55 | 2.56 to 2.98 | [Ref27], lines 123-125 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 2 | bw_new asmread | 22:16:15 | 109.82 | 339.91 (673) | 327.38 (664) | 328.17 (664) | 328.17 | 2.63 to 3.06 | [Ref27], lines 116-118 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 1 | bw_old read (old read kernel) | 22:18:32 | 102.96 | 474.15 (968) | 469.73 (961) | 469.37 (957) | 469.73 | 2.94 to 4.97 | [Ref29], lines 4-6 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 1 | bw_new read (new read kernel) | 22:18:34 | 104.25 | 315.55 (664) | 320.46 (664) | 320.89 (664) | 320.46 | 2.47 to 2.92 | [Ref29], lines 11-13 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 1 | bw_old asmread | 22:18:51 | 99.78 | 322.48 (664) | 321.44 (664) | 323.27 (664) | 322.48 | 2.57 to 2.94 | [Ref29], lines 46-48 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 1 | bw_new asmread | 22:18:53 | 99.78 | 317.85 (664) | 320.87 (664) | 320.27 (664) | 320.27 | 2.55 to 2.92 | [Ref29], lines 53-55 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 2 | bw_old read (old read kernel) | 22:19:45 | 111.98 | 465.61 (940) | 465.55 (937) | 466.63 (943) | 465.61 | 3.00 to 4.98 | [Ref29], lines 165-167 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 2 | bw_new read (new read kernel) | 22:19:42 | 110.93 | 336.41 (719) | 331.45 (664) | 332.96 (718) | 332.96 | 2.66 to 3.01 | [Ref29], lines 158-160 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 2 | bw_old asmread | 22:19:26 | 108.73 | 327.87 (664) | 324.25 (664) | 324.04 (664) | 324.25 | 2.60 to 2.98 | [Ref29], lines 123-125 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 2 | bw_new asmread | 22:19:24 | 108.73 | 332.75 (664) | 327.70 (664) | 328.77 (664) | 328.77 | 2.62 to 3.02 | [Ref29], lines 116-118 |

New against old per session and round:

| Session | Start state of the session | Round | bw_old read, median GB/s | bw_new read, median GB/s | Ratio new/old | New below old, % | Lowest to highest ratio of single intervals (lowest bw_new / highest bw_old to highest bw_new / lowest bw_old) | bw_old asmread / bw_old read | bw_new asmread / bw_old read |
|---|---|---|---|---|---|---|---|---|---|
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 1 | 467.83 | 330.59 | 0.707 | 29.3 | 0.705 to 0.716 | 0.689 | 0.688 |
| 1 | started from an idle machine, 5 s after go.sh started (1-minute load average 0.07) | 2 | 461.33 | 327.60 | 0.710 | 29.0 | 0.708 to 0.724 | 0.729 | 0.719 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 1 | 468.21 | 324.42 | 0.693 | 30.7 | 0.689 to 0.695 | 0.678 | 0.691 |
| 2 | started 5 s after the 120-thread bwx12 process T72C1 | 2 | 467.52 | 328.96 | 0.704 | 29.6 | 0.703 to 0.709 | 0.701 | 0.702 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 1 | 469.73 | 320.46 | 0.682 | 31.8 | 0.666 to 0.684 | 0.687 | 0.682 |
| 3 | started 5 s after the 120-thread bwx12 process T72C2 | 2 | 465.61 | 332.96 | 0.715 | 28.5 | 0.710 to 0.723 | 0.696 | 0.706 |

- The new read kernel is below the old read kernel in all 6 pairs. The highest single-interval ratio is 0.724 (session 1, round 2). It is the highest bw_new interval divided by the lowest bw_old interval of that session and round (332.82 GB/s divided by 459.90 GB/s). Decision (j) in section 2 gives the definition.
- The columns "bw_old asmread / bw_old read" and "bw_new asmread / bw_old read" are ratios of process medians.
- asmread gives 0.678 to 0.729 of the old read kernel in both binaries. So the lower rate belongs to the load-only loop, not to the binary.
- Pass counts: bw_new read completed 664, 718 or 719 passes per interval. bw_old read completed 919 to 968.
- Limit of part A (rule V3 [Ref7]): with the whole-pass stop the pass count moves in steps, and the rate moves with it. So the percent values of part A are less exact than those of parts L and C.

### 3.2 Parts L and I: bwx12, common stop, 6 s, oldread then asmread

- In these parts asmread is used in place of the new read kernel. It is the same loop: 8 "ldp q" loads per 256 B.
- The drop is computed inside the same process and round: (1 - asmread / oldread) x 100.
- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1.

| Folder tag or row | What | Round | Load at launch | oldread, GB/s | oldread m0 + m1 | asmread, GB/s | asmread m0 + m1 | asmread below oldread, % | Source |
|---|---|---|---|---|---|---|---|---|---|
| T72L1 | part L, session 1. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 0 | 74.05 | 462.30 | 305.13 + 157.17 | 321.76 | 178.60 + 143.16 | 30.4 | [Ref31], I rows in lines 128 and 490 |
| T72L1 | part L, session 1. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 1 | 74.05 | 461.61 | 303.67 + 157.94 | 321.65 | 176.81 + 144.84 | 30.3 | [Ref31], I rows in lines 1938 and 2300 |
| T72L2 | part L, session 2. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 0 | 104.52 | 464.29 | 306.59 + 157.70 | 322.65 | 177.48 + 145.17 | 30.5 | [Ref35], I rows in lines 128 and 490 |
| T72L2 | part L, session 2. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 1 | 104.52 | 464.04 | 305.54 + 158.50 | 325.33 | 177.81 + 147.52 | 29.9 | [Ref35], I rows in lines 1938 and 2300 |
| T72L3 | part L, session 3. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 0 | 103.01 | 462.97 | 304.98 + 157.99 | 327.93 | 178.69 + 149.24 | 29.2 | [Ref39], I rows in lines 128 and 490 |
| T72L3 | part L, session 3. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 1 | 103.01 | 461.79 | 303.43 + 158.36 | 323.11 | 175.75 + 147.35 | 30.0 | [Ref39], I rows in lines 1938 and 2300 |
| T72I1 | control I (idle start, added later) | 0 | 0.87 | 466.58 | 309.88 + 156.70 | 313.78 | 172.10 + 141.68 | 32.7 | [Ref59], I rows in lines 128 and 490 |
| T72I1 | control I (idle start, added later) | 1 | 0.87 | 467.21 | 309.95 + 157.27 | 314.09 | 170.63 + 143.46 | 32.8 | [Ref59], I rows in lines 1938 and 2300 |
| T72I2 | control I (idle start, added later) | 0 | 0.91 | 469.20 | 309.32 + 159.88 | 316.54 | 171.58 + 144.95 | 32.5 | [Ref63], I rows in lines 128 and 490 |
| T72I2 | control I (idle start, added later) | 1 | 0.91 | 466.30 | 306.00 + 160.30 | 317.60 | 172.93 + 144.68 | 31.9 | [Ref63], I rows in lines 1938 and 2300 |
| F72d12 | earlier visit of the same boot (20:02), not part of the rerun | 0 | 0.34 | 468.44 | 308.78 + 159.66 | 302.78 | 162.82 + 139.95 | 35.4 | [Ref119], I rows in lines 128 and 490 |
| F72d12 | earlier visit of the same boot (20:02), not part of the rerun | 1 | 0.34 | 467.46 | 307.61 + 159.84 | 301.90 | 162.29 + 139.61 | 35.4 | [Ref119], I rows in lines 1938 and 2300 |

- Every part L process started 5 s after the last 120-thread process of part A of its session.
- The two control I processes started from an idle machine: the load at launch was 0.87 and 0.91, and the previous 120-thread process had ended 287 and 265 s before.
- F72d12 started 20 s after the first kernel log line of the boot, at a load of 0.34 [Ref121] [Ref136]. Section 4.1 gives the proof that it ran in the boot of the rerun.
- The process list of F72d12 differs from those of the rerun. Its env.txt was written at 20:02:31, 5 s before the launch. It lists pr/ttyAMA-1 at 51.6 %CPU and systemd at 13.1 %CPU (lines 5 and 6 [Ref120]). The env.txt files of the 9 bwx12 launches of the rerun show at most 0.1 %CPU. So F72d12 is an idle start only by the load-average rule of this sheet (section 4.6).

### 3.3 Part C: bwx12, common stop, 6 s, oldread, read and asmread in one process

- `read` is the new read kernel in bwx12. `oldread` is the old read kernel.
- cfwd runs oldread, read, asmread. crev runs asmread, read, oldread. Each process runs its sequence twice (rounds 0 and 1).
- Each drop is computed against oldread of the same process and round.
- "m0 + m1" are the sums over the threads of mesh 0 and of mesh 1, in GB/s. Section 4.7 uses them.

| Folder tag | Order | Round | Load at launch | oldread, GB/s | oldread m0 + m1 | read, GB/s | read m0 + m1 | asmread, GB/s | asmread m0 + m1 | read below oldread, % | asmread below oldread, % | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T72C1 | cfwd | 0 | 94.97 | 466.01 (position 0, after nothing: first interval) | 308.39 + 157.63 | 320.90 (position 1, after oldread) | 178.20 + 142.70 | 320.86 (position 2, after read) | 177.73 + 143.13 | 31.1 | 31.1 | [Ref43], I rows in lines 128, 490, 852 |
| T72C1 | cfwd | 1 | 94.97 | 465.54 (position 0, after asmread) | 308.12 + 157.42 | 320.89 (position 1, after oldread) | 176.69 + 144.20 | 321.84 (position 2, after read) | 177.96 + 143.88 | 31.1 | 30.9 | [Ref43], I rows in lines 1214, 1576, 1938 |
| T72C2 | crev | 0 | 105.24 | 467.55 (position 2, after read) | 310.77 + 156.78 | 322.22 (position 1, after asmread) | 177.98 + 144.24 | 319.43 (position 0, after nothing: first interval) | 175.68 + 143.75 | 31.1 | 31.7 | [Ref47], I rows in lines 852, 490, 128 |
| T72C2 | crev | 1 | 105.24 | 468.14 (position 2, after read) | 310.92 + 157.23 | 324.43 (position 1, after asmread) | 178.21 + 146.21 | 324.73 (position 0, after oldread) | 179.38 + 145.35 | 30.7 | 30.6 | [Ref47], I rows in lines 1938, 1576, 1214 |
| T72C3 | cfwd | 0 | 105.20 | 467.83 (position 0, after nothing: first interval) | 310.13 + 157.70 | 322.02 (position 1, after oldread) | 176.90 + 145.12 | 322.07 (position 2, after read) | 177.36 + 144.71 | 31.2 | 31.2 | [Ref51], I rows in lines 128, 490, 852 |
| T72C3 | cfwd | 1 | 105.20 | 467.49 (position 0, after asmread) | 309.71 + 157.79 | 324.98 (position 1, after oldread) | 178.81 + 146.17 | 323.41 (position 2, after read) | 177.89 + 145.51 | 30.5 | 30.8 | [Ref51], I rows in lines 1214, 1576, 1938 |
| T72C4 | crev | 0 | 102.94 | 464.88 (position 2, after read) | 307.60 + 157.29 | 325.05 (position 1, after asmread) | 179.39 + 145.66 | 324.88 (position 0, after nothing: first interval) | 178.59 + 146.29 | 30.1 | 30.1 | [Ref55], I rows in lines 852, 490, 128 |
| T72C4 | crev | 1 | 102.94 | 464.00 (position 2, after read) | 307.05 + 156.94 | 326.27 (position 1, after asmread) | 180.65 + 145.61 | 326.12 (position 0, after oldread) | 180.41 + 145.70 | 29.7 | 29.7 | [Ref55], I rows in lines 1938, 1576, 1214 |

Groups by the kernel that ran directly before (rule V2 [Ref7]):

| Group | Where | Folder tags | n | Min to max, GB/s | Below oldread of the same process and round, % |
|---|---|---|---|---|---|
| read after oldread | cfwd, rounds 0 and 1 | T72C1, T72C3 | 4 intervals / 2 processes | 320.89 to 324.98 | 30.5 to 31.2 |
| read after asmread | crev, rounds 0 and 1 | T72C2, T72C4 | 4 intervals / 2 processes | 322.22 to 326.27 | 29.7 to 31.1 |
| asmread after read | cfwd, rounds 0 and 1 | T72C1, T72C3 | 4 intervals / 2 processes | 320.86 to 323.41 | 30.8 to 31.2 |
| asmread as first interval of the process | crev, round 0 | T72C2, T72C4 | 2 intervals / 2 processes | 319.43 to 324.88 | 30.1 to 31.7 |
| asmread after oldread (the condition of part L) | crev, round 1 | T72C2, T72C4 | 2 intervals / 2 processes | 324.73 to 326.12 | 29.7 to 30.6 |
| oldread, all positions | cfwd position 0, crev position 2 | T72C1, T72C2, T72C3, T72C4 | 8 intervals / 4 processes | 464.00 to 468.14 | - |

- Limit (rule V2 point 5): the reverse order comes from 2 processes (T72C2 in session 2, T72C4 after session 3). With 2 processes per order, order and session are still not fully separated.

### 3.4 Verdict for Q1

| Part | Pair | Smallest drop, % | Largest drop, % | n |
|---|---|---|---|---|
| C | bwx12 `read` (new read kernel) directly after `oldread` (cfwd), against `oldread` of the same process and round | 30.5 | 31.2 | 4 pairs: 4 intervals per kernel / 2 processes (T72C1, T72C3) / sessions 1 and 3 / 1 boot |
| C | bwx12 `read` (new read kernel) directly after `asmread` (crev), against `oldread` of the same process and round | 29.7 | 31.1 | 4 pairs: 4 intervals per kernel / 2 processes (T72C2, T72C4) / session 2 and 1 extra process / 1 boot |
| C | bwx12 `asmread` directly after `read` (cfwd), against `oldread` of the same process and round | 30.8 | 31.2 | 4 pairs: 4 intervals per kernel / 2 processes (T72C1, T72C3) / sessions 1 and 3 / 1 boot |
| C | bwx12 `asmread` as first interval of the process (crev, round 0), against `oldread` of the same process and round | 30.1 | 31.7 | 2 pairs: 2 intervals per kernel / 2 processes (T72C2, T72C4) / session 2 and 1 extra process / 1 boot |
| C | bwx12 `asmread` directly after `oldread` (crev, round 1), against `oldread` of the same process and round | 29.7 | 30.6 | 2 pairs: 2 intervals per kernel / 2 processes (T72C2, T72C4) / session 2 and 1 extra process / 1 boot |
| L | bwx12 `asmread` (used in place of the new read kernel) against `oldread`, same process and round | 29.2 | 30.5 | 6 pairs: 6 intervals per kernel / 3 processes / 3 sessions / 1 boot |
| A | bw_new `read` against bw_old `read`, medians of 3 intervals, same session and round | 28.5 | 31.8 | 6 pairs of process medians: 18 intervals per kernel / 6 processes per kernel / 3 sessions / 1 boot |
| I (control, added after the first numbers were seen) | bwx12 `asmread` against `oldread`, same process and round | 31.9 | 32.8 | 4 pairs: 4 intervals per kernel / 2 processes / no session / 1 boot |
| F72d12 (earlier visit, not part of the rerun) | bwx12 `asmread` against `oldread`, same process and round | 35.4 | 35.4 | 2 pairs: 2 intervals per kernel / 1 process / no session / 1 boot |

- Part C has one row per group (rule V2 [Ref7]). No range is given over all read intervals or over all asmread intervals of part C.

**Verdict.** Yes. At 7200 MT/s with 12 memory modules the new read kernel is still below the old read kernel. Part C (bwx12 kernel read against oldread of the same process and round, common stop, 6 s): 30.5 % to 31.2 % lower when read ran directly after oldread (4 pairs, 2 processes: T72C1, T72C3), and 29.7 % to 31.1 % lower when read ran directly after asmread (4 pairs, 2 processes: T72C2, T72C4). Part L, asmread (the same loop, used in place of the new read kernel) against oldread: 29.2 % to 30.5 % lower (6 pairs, 3 processes, 3 sessions). Part A, the repeat of the 2026-11-13 test, bw_new read against bw_old read, whole-pass stop, 0.5 s: 28.5 % to 31.8 % lower (6 pairs of process medians, 3 sessions). The percent values of part A are less exact than those of parts L and C. The new read kernel is below the old read kernel in all 8 pairs of part C and in all 6 pairs of part A. asmread is below the old read kernel in all 6 pairs of part L and in all 8 pairs of part C (30.8 % to 31.2 % after read, 30.1 % to 31.7 % as first interval, 29.7 % to 30.6 % after oldread). The size is not one fixed value: control I (idle start, added after the first numbers were seen, not part of the plan fixed before the run) gave 31.9 % to 32.8 %, and the earlier run F72d12 of the same boot (not part of the rerun) gave 35.4 %. All values come from 1 boot.

- In the table of section 3.2 the lowest and the highest oldread value are 7.59 GB/s apart (461.61 and 469.20 GB/s). The lowest and the highest asmread value are 26.03 GB/s apart (301.90 and 327.93 GB/s). So the size of the drop follows the load-only loop.

## 4. Q2: 7200 MT/s against 8000 MT/s

### 4.1 The rules and the rows

The rules were fixed before the run [Ref7]. In short:

- Rule V1 point 2: per part and kernel, compare the min-to-max range of the 7200 MT/s intervals with the min-to-max range of the like-for-like 8000 MT/s intervals. If the ranges do not overlap, write "differs between the 8000 MT/s boot and the 7200 MT/s boot". If they overlap, write "no difference seen" and give the width of the 8000 MT/s range as the size that the test cannot exclude.
- Rule V1 point 3: never give a percent change of the new read kernel (bw_new read, bwx12 read, asmread) as an effect of the memory speed.
- Rule V1 point 4: for the old read kernel a difference above about 1 % may be reported as a difference between the two boots.
- Rule V3: part A, load-only kernels: one row per process, session 1 against the 8000 MT/s processes of the same round, wording "inside" or "outside", no percent. Sessions 2 and 3 are used for Q1 only.
- Rule V2: part C is grouped by the kernel that ran directly before.
- Rules V4 and F2: the kernel `read` of part C has no bwx12 run at 8000 MT/s.
- The rules contradict each other on part C. Rule F2 points 2 and 3 would use part L only for bwx12 and would present part C at 7200 MT/s only. Rules V1 point 2, V2 point 4 and V4 ask for a comparison of part C with 8000 MT/s. This sheet follows V1, V2 and V4 (decision (r) in section 2).
- Each memory speed has exactly one boot. Every baseline row, supporting row and other-binary row at 8000 MT/s comes from boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC). Every 7200 MT/s row comes from boot 3bfc57a1. For the rerun the proof is in section 1.2. For row F72d12 it stands under the table below. The rows X2d12, X1d10, X1d10b and BASEd10 come from other boots. The table below names them.
- Label of the 7200 MT/s ranges of the rerun (rule V1 point 1): three sessions that ran within 10 min 9 s, all in boot 3bfc57a1. The rule text says "about 10 min (est.)". The value here is measured from the go.sh log.

Rows of earlier runs used in this section:

| Row | What it is | Folder and files | Binary (sha256, first 8 characters) | Stop rule, interval length | Memory speed, modules, boot | Load at launch (lowest to highest process) | Interval records in facts.json / processes | Source |
|---|---|---|---|---|---|---|---|---|
| A-1 | baseline: the test of 2026-11-13, same process order as part A | R/kernels-20261113T181222Z: threads120.csv | bw_new (fd7c14df), bw_old (e8fc0205) | whole pass stop, 0.5 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 1.00 to 85.38 | 72 / 24 | rates and load [Ref67], sha256 [Ref68] |
| A-2 | baseline: same binaries and arguments, other process order | R/partA-20261113T205055Z: A1.csv | bw_new (fd7c14df), bw_old (e8fc0205) | whole pass stop, 0.5 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 0.64 to 37.30 | 36 / 12 | rates and load [Ref70], sha256 [Ref72] |
| A-3 | baseline: bw_old read only, same arguments as A-2 | R/partA-20261113T205055Z: A3.csv (3 processes, tags onebuf-ms500-1 to onebuf-ms500-3) | bw_old (e8fc0205) | whole pass stop, 0.5 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 106.53 to 114.44 | 9 / 3 | rates and load [Ref71], sha256 [Ref72] |
| L-1 | baseline: identical argument line | R/w120-R8-20261117T020549Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 0.00 | 10 / 1 | rates [Ref73], load [Ref75], sha256 [Ref74] |
| L-2 | supporting: bwx12, other counter events | R/w120-R1-20261115T185140Z: p1nop.csv, p2add.csv | bwx12 (cd58e564) | common stop, 4 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 0.00 to 94.23 | 8 / 2 | rates [Ref77] [Ref78], load [Ref80], sha256 [Ref79] |
| L-3 | supporting: bwx12, other counter events | R/w120-R5-20261115T203152Z: thp.csv | bwx12 (cd58e564) | common stop, 4 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 53.98 | 4 / 1 | rates [Ref82], load [Ref84], sha256 [Ref83] |
| L-4 | supporting: bwx12, other counter events | R/w120-R6-20261115T203438Z: st1.csv, st2.csv, st3.csv | bwx12 (cd58e564) | common stop, 4 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 65.54 to 88.24 | 6 / 3 | rates [Ref86] [Ref87] [Ref88], load [Ref90], sha256 [Ref89] |
| R0 | other binary (bwx11) | R/w120-R0-20261115T165608Z: p1.csv, p2.csv | bwx11 (f1215f9e) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 0.00 to 85.15 | 8 / 2 | rates [Ref92] [Ref93], load [Ref95], sha256 [Ref20] |
| R0b | other binary (bwx11) | R/w120-R0b-20261115T170342Z: cA.csv, cB.csv, cC.csv | bwx11 (f1215f9e) | common stop, 4 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 9.44 to 64.02 | 6 / 3 | rates [Ref97] [Ref98] [Ref99], load [Ref101], sha256 [Ref100] |
| X2d12 | not a baseline (firmware test setting), shown and not used | R/w120-X2d12-20261117T040922Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 8000 MT/s, 12 modules, boot -2 of the DIMM report (Linux start 2026-11-17 04:09 UTC) | 0.31 | 10 / 1 | rates [Ref103], load [Ref105], sha256 [Ref104] |
| F72d12 | sample of the same boot as the rerun, earlier visit (load 0.34 at launch, 20 s after the first kernel log line of the boot), kept as its own row in every range test of rule V1 point 2 | R/w120-w120-F72d12-20261117T200231Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 7200 MT/s, 12 modules, boot 3bfc57a1 | 0.34 | 10 / 1 | rates [Ref119], load [Ref121], sha256 [Ref120], boot, modules and speed [Ref135] [Ref136] [Ref137] [Ref23] (proof under this table) |
| B7a | other binary (bwx), tags common-6000-* | R/B7-20261113T232859Z: B7.csv (8 processes, tags common-6000-common-p1 to common-6000-offset-p4) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 113.70 to 120.23 | 96 / 8 | rates and load [Ref123], sha256 [Ref124] |
| B7b | other binary (bwx), tags common-6000-* | R/B7-20261114T024352Z: B7.csv (8 processes, tags common-6000-common-p1 to common-6000-offset-p4) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 118.22 to 120.04 | 96 / 8 | rates and load [Ref125], sha256 [Ref126] |
| C3a | other binary (bwx), tags common-6000-* | R/C3-20261114T022708Z: C3.csv (4 processes, tags common-6000-common-p1 to common-6000-offset-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 116.54 to 119.69 | 48 / 4 | rates and load [Ref127], sha256 [Ref128] |
| C3b | other binary (bwx), tags common-6000-* | R/C3-20261114T054116Z: C3.csv (4 processes, tags common-6000-common-p1 to common-6000-offset-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 108.92 to 118.24 | 48 / 4 | rates and load [Ref129], sha256 [Ref130] |
| B5a | other binary (bwx), tags b5-fwd-* | R/B5-20261114T011723Z: B5.csv (2 processes, tags b5-fwd-p1 to b5-fwd-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 115.58 to 119.55 | 6 / 2 | rates and load [Ref131], sha256 [Ref132] |
| B5b | other binary (bwx), tags b5-fwd-* | R/B5-20261114T043213Z: B5.csv (2 processes, tags b5-fwd-p1 to b5-fwd-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 101.73 to 117.16 | 6 / 2 | rates and load [Ref133], sha256 [Ref134] |
| B5a-rev | other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only for the highest values in section 4.6 | R/B5-20261114T011723Z: B5.csv (2 processes, tags b5-rev-p1 to b5-rev-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 118.38 to 120.33 | 6 / 2 | rates and load [Ref131], sha256 [Ref132] |
| B5b-rev | other binary (bwx), tags b5-rev-*, reverse kernel order, not in the list of rule V4, used only for the highest values in section 4.6 | R/B5-20261114T043213Z: B5.csv (2 processes, tags b5-rev-p1 to b5-rev-p2) | bwx (5b702073) | common stop, 6 s | 8000 MT/s, 12 modules, boot -5 of the DIMM report (Linux start 2026-11-09 21:20 UTC) | 112.71 to 118.87 | 6 / 2 | rates and load [Ref133], sha256 [Ref134] |
| X1d10 | 10 modules, changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4 | R/w120-X1d10-20261117T034916Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 8000 MT/s, 10 modules, boot -4 of the DIMM report (Linux start 2026-11-17 03:48 UTC) | 0.50 | 4 / 1 | rates [Ref107], load [Ref109], sha256 [Ref108] |
| X1d10b | 10 modules, the same changed TXREQ firmware settings, used only for the text of rule V1 points 3 and 4 | R/w120-X1d10b-20261117T040407Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 8000 MT/s, 10 modules, boot -3 of the DIMM report (Linux start 2026-11-17 03:57 UTC) | 0.00 | 4 / 1 | rates [Ref111], load [Ref113], sha256 [Ref112] |
| BASEd10 | 10 modules, original firmware settings, used only for the text of rule V1 point 4 | R/w120-BASEd10-20261117T041738Z: a6456.csv | bwx12 (cd58e564) | common stop, 6 s | 8000 MT/s, 10 modules, boot -1 of the DIMM report (Linux start 2026-11-17 04:17 UTC) | 0.26 | 4 / 1 | rates [Ref115], load [Ref117], sha256 [Ref116] |

- Column "Source": the csv files hold the rates. For the rows written by rx.sh or r0.sh the load is in launches.txt and the sha256 is in env.txt. For row R0 env.txt holds no sha256 [Ref94], and the value comes from line 8 of r0.sh [Ref20]. For the other rows the load is in the header lines of the csv file, and the sha256 is in probe.txt or env.txt of the run folder.
- Firmware settings of the 10-module rows: the DIMM report gives the old read values of X1d10 and X1d10b as runs with changed TXREQ settings, and those of BASEd10 as the run with the original settings (its sections 6.1 and 6.2 [Ref138]). TXREQ is a group of firmware settings that were changed for another investigation.
- The boot numbers are those of the boot history in the DIMM report [Ref138].
- From rows L-2 to L-4, R0 and R0b this sheet uses oldread at position 0 and asmread at position 1 only.
- The speed of the 2026-11-09 boot rests on the firmware setting, not on a reading of the applied speed (section 1.5, point 10).
- Firmware settings of the two boots: section 1.5, point 13. In short: the two TXREQ settings were set back on 2026-11-17 04:13:19. The settings list saved after that is equal to the list of the baseline boot in all 604 readable values. No settings list exists from the boot of the rerun.
- Boot, module count and speed of row F72d12. Its folder holds no boot id, no MemTotal and no memory speed: env.txt has 10 lines with the date, the Linux release, the load, the process list and the binary [Ref120]. Its process ran from 20:02:36 to 20:03:37 [Ref121]. Line 1 of try6.txt holds the time 20:02:21, 15 s before that launch. The file holds the boot id `3bfc57a1-e235-4fe5-8c09-a94642f9b60b` (line 2), MemTotal 395392808 kB (line 4), "This system has 12 DIMM sockets" (line 5) and "12 Configured Memory Speed: 7200 MT/s" (line 7) [Ref135]. The go.sh log holds the same boot id at 22:12:09 (line 6) [Ref23]. Linux creates a boot id once per start (see the word list). So Linux was not started again between these two readings, and the F72d12 process ran in the boot of the rerun. Two more records fit this. Row 0 of boots.txt holds the same boot id with the times 20:02:21 and 20:06:19 (line 9) [Ref137]. Row 0 of gaps.txt spans 20:02:16 to 20:06:34 (line 7) [Ref136]. Limit, as for the rerun: the speed and the module count were not read during the process.

Hardware error records during the bwx12 and bwx11 rows of the 2026-11-09 boot (rows L-1 to L-4, R0, R0b):

- The journal is the one of section 1.5, point 8 [Ref139]. One record is one line "Hardware error from APEI ..." of the journal.
- The window of a process is the time from its launch line to its rc line in launches.txt. rx.sh and r0.sh write the launch line directly before they start the process [Ref19] [Ref20]. In a table cell " / " separates the records of different seconds.
- Time resolution. The journal and launches.txt give whole seconds. So a record that the journal dates N seconds after the launch line lies between N - 1 and N + 1 seconds after the process start (est.). The csv file gives the start and the end of every interval in seconds since the process start (T rows, columns t_start_s and t_end_s). The journal time is the time of the log line. The time of the hardware event itself is not on record.
- The table below tests only the intervals that this sheet uses: oldread at position 0 and asmread at position 1. The second table of this block lists the intervals of all kernels and positions.

| Row | Process | Launch line | rc line | Records in the window | Journal time: journal lines of the records | Seconds after the launch line | Position against the intervals used | Source |
|---|---|---|---|---|---|---|---|---|
| L-1 | a6456 | 2026-11-17 02:05:54 | 2026-11-17 02:06:56 | 2 | 2026-11-17 02:05:55: 9344, 9372 | 1 | before or inside oldread, round 0 (0.43 s to 6.43 s after the process start, I row in line 128) | [Ref75] [Ref73] |
| L-2 | p1nop | 2026-11-15 18:51:45 | 2026-11-15 18:53:40 | 5 | 2026-11-15 18:52:07: 7083, 7111 / 2026-11-15 18:52:31: 7142 / 2026-11-15 18:53:21: 7170, 7198 | 22 / 46 / 96 | outside / outside / outside | [Ref80] [Ref77] |
| L-2 | p2add | 2026-11-15 18:53:45 | 2026-11-15 18:55:50 | 4 | 2026-11-15 18:54:52: 7229, 7257 / 2026-11-15 18:55:15: 7288, 7316 | 67 / 90 | inside asmread, round 1 (65.99 s to 70.00 s after the process start, I row in line 5920) / outside | [Ref80] [Ref78] |
| L-3 | thp | 2026-11-15 20:33:04 | 2026-11-15 20:34:18 | 0 | - | - | - | [Ref84] [Ref82] |
| L-4 | st1 | 2026-11-15 20:34:43 | 2026-11-15 20:35:12 | 0 | - | - | - | [Ref90] [Ref86] |
| L-4 | st2 | 2026-11-15 20:35:17 | 2026-11-15 20:35:46 | 0 | - | - | - | [Ref90] [Ref87] |
| L-4 | st3 | 2026-11-15 20:35:52 | 2026-11-15 20:36:21 | 0 | - | - | - | [Ref90] [Ref88] |
| R0 | p1 | 2026-11-15 16:56:08 | 2026-11-15 16:58:36 | 7 | 2026-11-15 16:56:48: 6847, 6875 / 2026-11-15 16:56:55: 6906 / 2026-11-15 16:57:56: 6937, 6965 / 2026-11-15 16:58:24: 6996, 7024 | 40 / 47 / 108 / 136 | outside / outside / outside / outside | [Ref95] [Ref92] |
| R0 | p2 | 2026-11-15 16:58:51 | 2026-11-15 17:01:18 | 0 | - | - | - | [Ref95] [Ref93] |
| R0b | cA | 2026-11-15 17:03:47 | 2026-11-15 17:04:12 | 0 | - | - | - | [Ref101] [Ref97] |
| R0b | cB | 2026-11-15 17:04:17 | 2026-11-15 17:04:42 | 0 | - | - | - | [Ref101] [Ref98] |
| R0b | cC | 2026-11-15 17:04:47 | 2026-11-15 17:05:13 | 0 | - | - | - | [Ref101] [Ref99] |

- All 18 records in these windows have the severity "corrected".
- Row L-1: the 2 records at 2026-11-17 02:05:55 (journal lines 9344 and 9372) are 1 s after the launch line. oldread, round 0 was timed from 0.43 s to 6.43 s after the process start (T rows in lines 129 to 248 [Ref73]). So the records fall before this interval or inside it. The interval gave 468.06 GB/s.
- Row L-2, process p2add: the 2 records at 2026-11-15 18:54:52 (journal lines 7229 and 7257) are 67 s after the launch line. asmread, round 1 was timed from 65.99 s to 70.00 s after the process start (T rows in lines 5921 to 6040, I row in line 5920 [Ref78]). So the records fall inside this interval. It gave 288.54 GB/s, the lowest asmread value of the pool L-1 to L-4 (section 4.4).
- The other 14 records of these windows fall outside the intervals that this sheet uses.
- Processes with 0 records in their window: L-3 thp, L-4 st1, L-4 st2, L-4 st3, R0 p2, R0b cA, R0b cB, R0b cC.
- F72d12: line 7 of gaps.txt shows "hwerr=0" for row 0, with the kernel log times 20:02:16 to 20:06:34 [Ref136]. Row 0 of boots.txt holds the boot id of the rerun [Ref137]. The F72d12 process ran from 20:02:36 to 20:03:37 [Ref121]. By its name the field counts hardware error records. The script that wrote gaps.txt is not among the files of this task. So its count rule was not checked.
- Rerun (parts A, L and C, control I): Insufficient data. The kernel log was not read (section 1.5, point 8).
- Not counted in this sheet: the records during the rows of runner bwx (B7a to B5b-rev) and during the rows of other boots (X2d12, X1d10, X1d10b, BASEd10). No wording by rule V1 point 2 rests on these rows. For the rows of runner bwx the same journal and the T rows of their csv files would give the count.
- Hypothesis, not tested: a corrected record lowers the rate of the interval in which it falls. The files on hand hold more than one interval with records. The table below lists every interval of the processes above, of all kernels and positions, to which records can be assigned: the records fall inside it, or before or inside it. This view was added after the numbers were seen. It is not part of the fixed rules.

Intervals with records, all kernels and positions (rows L-1 to L-4, R0, R0b). "Other round" is the interval of the same kernel at the same position in the other round of the same process. No other-round interval of this table has a record inside it or at its border. The position of the records follows the rule of the table above (1 s resolution, est.). A difference is computed from the values before rounding (first lines of this sheet).

| Row | Process | Interval with records | I row line | Journal lines of the records | Position of the records | Rate, GB/s | Other round: rate, GB/s (I row line) | With records minus other round, GB/s | Used by this sheet | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| L-1 | a6456 | oldread, round 0, position 0 | 128 | 9344, 9372 | before or inside | 468.06 | 467.35 (1938) | +0.70 | yes | [Ref73] [Ref139] |
| L-2 | p1nop | read_nop72, round 0, position 5 | 1938 | 7083, 7111 | inside | 459.28 | 459.02 (7006) | +0.26 | no | [Ref77] [Ref139] |
| L-2 | p1nop | read_nop112, round 1, position 9 | 8454 | 7170, 7198 | inside | 471.11 | 471.15 (3386) | -0.04 | no | [Ref77] [Ref139] |
| L-2 | p2add | asmread, round 1, position 1 | 5920 | 7229, 7257 | inside | 288.54 | 298.61 (490) | -10.07 | yes | [Ref78] [Ref139] |
| R0 | p1 | read_1pl, round 0, position 6 | 2300 | 6847, 6875 | inside | 231.42 | 231.08 (6644) | +0.33 | no | [Ref92] [Ref139] |
| R0 | p1 | read_pf256, round 0, position 7 | 2662 | 6906 | inside | 289.13 | 292.83 (7006) | -3.69 | no | [Ref92] [Ref139] |
| R0 | p1 | read_nop128, round 1, position 5 | 6282 | 6937, 6965 | inside | 476.39 | 476.39 (1938) | 0.00 | no | [Ref92] [Ref139] |
| R0 | p1 | asmread, round 1, position 10 | 8092 | 6996, 7024 | inside | 303.03 | 304.99 (3748) | -1.96 | no | [Ref92] [Ref139] |

- Of the 14 records outside the used intervals, 11 fall inside the 6 intervals of this table that the sheet does not use. The other 3 lie at the border of two intervals. The 1 s resolution cannot assign them to one interval: 1 record of L-2 p1nop, 46 s after the launch line (journal line 7142), between read_nop128 and read_nop160 of round 0, and 2 records of L-2 p2add, 90 s after the launch line (journal lines 7288 and 7316), between read_iadd16 and read_sparse of round 1. These 4 intervals differ from their other round by -1.35 to +0.57 GB/s. They are not in the table.
- What fits: 3 of the 8 intervals of the table are more than 1 GB/s below their other round (1.96, 3.69 and 10.07 GB/s). The largest difference belongs to the asmread interval of p2add (288.54 GB/s), the lowest asmread value of the pool L-1 to L-4. No interval of the table is more than 1 GB/s above its other round.
- What does not fit: the other 5 intervals differ from their other round by less than 1 GB/s (-0.04 to +0.70 GB/s). One of them is oldread, round 0 of row L-1. It gave 468.06 GB/s with records before or inside it. Round 1, without records, gave 467.35 GB/s.
- Limit: the two rounds of a process differ without records too. These 4 processes have 34 positions at which neither round has a record inside it or at its border. At 10 of them the two rounds differ by more than 1 GB/s. The largest difference is 6.24 GB/s (read_dadd2 of p2add, lower in round 1, directly after the asmread interval with records). So 2 of the 3 lower intervals of the table (1.96 and 3.69 GB/s) are within the differences seen without records, and 1 (10.07 GB/s) is above them.
- This comparison is not a test of the hypothesis. Each interval has one other round to compare with. The comparison was chosen after the numbers were seen.
- Measurement that would confirm or reject it: a run that stores the kernel log time of every record beside the interval times, at both memory speeds (reading the kernel log needs root). More data are on hand and were not compared here: the records during the rows of runner bwx (see "Not counted in this sheet" above).

### 4.2 Old read kernel

**Part A, bw_old read.**

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part A, sessions 1 to 3 | rerun (one row per process is in section 3.1) | 7200 MT/s, 12 modules | 18 intervals / 6 processes | 459.90 to 474.15 | 467.54 | [Ref25] [Ref27] [Ref29] |
| A-1 | baseline: the test of 2026-11-13, same process order as part A | 8000 MT/s, 12 modules | 6 intervals / 2 processes | 464.42 to 466.65 | 465.48 | [Ref67] |
| A-2 | baseline: same binaries and arguments, other process order | 8000 MT/s, 12 modules | 6 intervals / 2 processes | 464.66 to 467.06 | 465.83 | [Ref70] |
| A-3 | baseline: bw_old read only, same arguments as A-2 | 8000 MT/s, 12 modules | 9 intervals / 3 processes | 463.58 to 469.03 | 466.42 | [Ref71] |
| pool A-1 to A-3 | all like-for-like 8000 MT/s intervals of bw_old read | 8000 MT/s, 12 modules | 21 intervals / 7 processes | 463.58 to 469.03 | 465.91 | [Ref67] [Ref70] [Ref71] |

| 7200 MT/s row | Its range, GB/s | 8000 MT/s range used | That range, GB/s | Overlap | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | Wording by rule V1 point 2 |
|---|---|---|---|---|---|---|---|
| part A, sessions 1 to 3 | 459.90 to 474.15 | A-1 | 464.42 to 466.65 | yes | 0 | 0.5 | - |
| part A, sessions 1 to 3 | 459.90 to 474.15 | A-2 | 464.66 to 467.06 | yes | 0 | 0.5 | - |
| part A, sessions 1 to 3 | 459.90 to 474.15 | A-3 | 463.58 to 469.03 | yes | 0 | 1.2 | - |
| part A, sessions 1 to 3 | 459.90 to 474.15 | pool A-1 to A-3 | 463.58 to 469.03 | yes | 0 | 1.2 | "no difference seen" |

- Wording by rule V1 point 2: "no difference seen". n at 7200 MT/s: 18 intervals / 6 processes / 3 sessions / 1 boot. n at 8000 MT/s: 21 intervals / 7 processes / 1 boot.
- The test cannot exclude a difference of about 1.2 % (est. from one boot). That is the width of the 8000 MT/s range.
- The 7200 MT/s range is wider than the 8000 MT/s range. The process of session 1, round 2 (459.90 to 461.71 GB/s) lies below it. The process of session 3, round 1 (469.37 to 474.15 GB/s) lies above it. The other 4 processes overlap it.

**Part L, oldread (position 0, the first interval of each round).**

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part L (T72L1 to T72L3) | rerun, each process started 5 s after the last 120-thread process of part A of its session | 7200 MT/s, 12 modules | 6 intervals / 3 processes | 461.61 to 464.29 | 462.63 | [Ref31] [Ref35] [Ref39] |
| L-1 | baseline: identical argument line | 8000 MT/s, 12 modules | 2 intervals / 1 process | 467.35 to 468.06 | 467.71 | [Ref73] |
| L-2 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 4 intervals / 2 processes | 465.53 to 469.68 | 467.38 | [Ref77] [Ref78] |
| L-3 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 2 intervals / 1 process | 469.65 to 470.05 | 469.85 | [Ref82] |
| L-4 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 3 intervals / 3 processes | 468.56 to 469.27 | 468.91 | [Ref86] [Ref87] [Ref88] |
| pool L-1 to L-4 | all bwx12 rows of the fixed list | 8000 MT/s, 12 modules | 11 intervals / 7 processes | 465.53 to 470.05 | 468.91 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| R0 | other binary (bwx11) | 8000 MT/s, 12 modules | 4 intervals / 2 processes | 469.32 to 469.96 | 469.68 | [Ref92] [Ref93] |
| R0b | other binary (bwx11) | 8000 MT/s, 12 modules | 3 intervals / 3 processes | 466.77 to 469.28 | 467.86 | [Ref97] [Ref98] [Ref99] |
| pool L-1 to L-4, R0, R0b | bwx12 rows and other-binary rows | 8000 MT/s, 12 modules | 18 intervals / 12 processes | 465.53 to 470.05 | 469.10 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| X2d12 | not a baseline (firmware test setting), shown and not used | 8000 MT/s, 12 modules | 2 intervals / 1 process | 469.36 to 470.68 | 470.02 | [Ref103] |
| F72d12 | sample of the same boot as the rerun, earlier visit (load 0.34 at launch, 20 s after the first kernel log line of the boot), kept as its own row in every range test of rule V1 point 2 | 7200 MT/s, 12 modules | 2 intervals / 1 process | 467.46 to 468.44 | 467.95 | [Ref119] |
| control I (T72I1, T72I2) | control, added after the first numbers were seen, idle start | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 466.30 to 469.20 | 466.89 | [Ref59] [Ref63] |

| 7200 MT/s row | Its range, GB/s | 8000 MT/s range used | That range, GB/s | Overlap | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | Wording by rule V1 point 2 |
|---|---|---|---|---|---|---|---|
| part L | 461.61 to 464.29 | L-1 alone | 467.35 to 468.06 | no | -3.06 | 0.2 | - |
| part L | 461.61 to 464.29 | pool L-1 to L-4 | 465.53 to 470.05 | no | -1.24 | 1.0 | "differs between the 8000 MT/s boot and the 7200 MT/s boot" |
| part L | 461.61 to 464.29 | pool L-1 to L-4, R0, R0b | 465.53 to 470.05 | no | -1.24 | 1.0 | - |
| F72d12 (same boot, own row) | 467.46 to 468.44 | L-1 alone | 467.35 to 468.06 | yes | 0 | 0.2 | - |
| F72d12 (same boot, own row) | 467.46 to 468.44 | pool L-1 to L-4 | 465.53 to 470.05 | yes | 0 | 1.0 | "no difference seen" |
| F72d12 (same boot, own row) | 467.46 to 468.44 | pool L-1 to L-4, R0, R0b | 465.53 to 470.05 | yes | 0 | 1.0 | - |
| control I (same boot, own row) | 466.30 to 469.20 | L-1 alone | 467.35 to 468.06 | yes | 0 | 0.2 | - |
| control I (same boot, own row) | 466.30 to 469.20 | pool L-1 to L-4 | 465.53 to 470.05 | yes | 0 | 1.0 | "no difference seen" |
| control I (same boot, own row) | 466.30 to 469.20 | pool L-1 to L-4, R0, R0b | 465.53 to 470.05 | yes | 0 | 1.0 | - |

- Part L, wording by rule V1 point 2: "differs between the 8000 MT/s boot and the 7200 MT/s boot". Part L is lower. n at 7200 MT/s: 6 intervals / 3 processes / 3 sessions / 1 boot. n at 8000 MT/s: 11 intervals / 7 processes / 1 boot.
- Size against the pool L-1 to L-4: the nearest ends are 1.24 GB/s apart (0.3 % of the lower end of the 8000 MT/s range, 465.53 GB/s). The medians are 6.27 GB/s apart (1.3 % of the 8000 MT/s median, 468.91 GB/s). The farthest ends are 8.45 GB/s apart (1.8 % of the same lower end). The 8000 MT/s range itself is 1.0 % wide.
- Rule V1 point 4 allows a report as "a difference between the two boots" above about 1 %. The rule does not say which distance counts. The distance of the nearest ends is below 1 %, and the distance of the medians is above 1 %.
- F72d12 and control I are runs of the same line in the same 7200 MT/s boot. Both were launched at a 1-minute load average below 1.0. Section 4.6 gives the differences of their start states. Control I was added after the first numbers were seen. Both overlap the 8000 MT/s range (467.46 to 468.44 and 466.30 to 469.20 GB/s against 465.53 to 470.05 GB/s).
- Hardware error records (section 4.1): 2 corrected records fall before or inside oldread, round 0 of row L-1 (468.06 GB/s). No other oldread interval of the rows L-1 to L-4, R0 and R0b has a record inside it. For the rerun the records are not known.
- So against the whole pool L-1 to L-4, only the range of part L lies below the 8000 MT/s range among the bwx12 runs at 7200 MT/s. Part L started 5 s after the last 120-thread process of part A. The view below splits the pool by start state. In that view part C lies below the bwx12 processes of the pool that started after 120-thread work too. Against the other-binary processes with that kind of start state part C overlaps (limit in the view). The data do not show that the boot or the memory speed is the cause: each memory speed has one boot.

The pool L-1 to L-4 split by the start state of the process. This view was looked at after the numbers were seen. It is not part of the fixed rules.

| 8000 MT/s group | Processes | Load at launch | Work before the launch | n | oldread, GB/s | asmread, GB/s | Source |
|---|---|---|---|---|---|---|---|
| started at a load below 1.0 | L-1 a6456, L-2 p1nop | 0.00 | first process of its run folder | 4 intervals / 2 processes / 1 boot | 465.53 to 468.06 | 298.71 to 305.57 | rates [Ref73] [Ref77], launch lines [Ref75] [Ref80] |
| started after 120-thread work | L-2 p2add, L-3 thp, L-4 st1, L-4 st2, L-4 st3 | 53.98 to 94.23 | a 120-thread bwx12 process had ended 5 s to 25 s before | 7 intervals / 5 processes / 1 boot | 468.56 to 470.05 | 288.54 to 309.17 | rates [Ref78] [Ref82] [Ref86] [Ref87] [Ref88], launch lines [Ref80] [Ref84] [Ref90] |

- oldread at 8000 MT/s: the 5 processes of the pool that started after 120-thread work gave the 7 highest values of the pool (468.56 to 470.05 GB/s). The 2 processes that started at a load below 1.0 gave 465.53 to 468.06 GB/s. The two groups do not overlap.
- Part L started 5 s after part A. Against the group that started after 120-thread work, oldread of part L (461.61 to 464.29 GB/s) is lower by 4.27 GB/s at the nearest ends (0.9 % of 468.56 GB/s). Against the whole pool this distance is 1.24 GB/s.
- Part C in this view. All 4 part C processes started 5 s after a 120-thread bwx12 process of the rerun (T72L1, T72L2, T72L3, T72C3), at a load of 94.97 to 105.24 (sections 1.1 and 1.3). That is the kind of start state of the second 8000 MT/s group (a 120-thread bwx12 process ended 5 s to 25 s before, load 53.98 to 94.23). oldread of part C (464.00 to 468.14 GB/s, 8 intervals / 4 processes / 1 boot) lies below this group (468.56 to 470.05 GB/s, 7 intervals / 5 processes / 1 boot). The two ranges do not overlap. Part C is lower by 0.42 GB/s at the nearest ends (0.09 % of 468.56 GB/s). Like the two wordings for part C, this comparison follows decision (r) in section 2.
- The second group holds oldread at position 0 only. The position-matched intervals of part C are those of cfwd at position 0 (T72C1 and T72C3, load 94.97 and 105.20 at launch): 465.54 to 467.83 GB/s (4 intervals / 2 processes). They are lower by 0.73 GB/s at the nearest ends.
- Against the group that started at a load below 1.0 (465.53 to 468.06 GB/s), oldread of part C overlaps.
- So in this view both 7200 MT/s parts that started after 120-thread work lie below the 5 bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (14 intervals / 7 processes against 7 intervals / 5 processes, no overlap). For part C this holds against these 5 processes only (see the limit below). The wording by rule V1 point 2 for part C does not change. It compares part C with the whole pool.
- The rows that were launched at a load below 1.0 overlap. At 7200 MT/s F72d12 gave 467.46 to 468.44 GB/s and control I (added after the first numbers were seen) gave 466.30 to 469.20 GB/s. At 8000 MT/s the group gave 465.53 to 468.06 GB/s.
- asmread: part L (321.65 to 327.93 GB/s) lies 12.48 GB/s above the group that started after 120-thread work (288.54 to 309.17 GB/s). The two 8000 MT/s groups overlap for asmread.
- So the 8000 MT/s rows do not show a lower oldread rate after 120-thread work. They show a higher one.
- Limit of the part C result in this view. The second group holds the 5 bwx12 processes of the pool only. They are not all 8000 MT/s processes with that kind of start state. The other-binary rows hold more of them, and against these part C overlaps. 3 bwx11 processes (R0 p2, R0b cB, R0b cC) were launched 5 or 15 s after a 120-thread bwx11 process, at a load of 43.39 to 85.15. They gave oldread 467.86 to 469.96 GB/s at position 0 (4 intervals / 3 processes) [Ref93] [Ref98] [Ref99], launch lines [Ref95] [Ref101]. The 24 processes of runner bwx (rows B7a, B7b, C3a, C3b) each follow a 120-thread process of runner bwx in their csv file. Their load at launch was 108.92 to 120.23. They gave 467.34 to 472.95 GB/s at position 0 (48 intervals / 24 processes) [Ref123] [Ref125] [Ref127] [Ref129]. The highest oldread value of part C is 468.14 GB/s.
- The part L result does not depend on this choice. The highest oldread value of part L (464.29 GB/s) is below every oldread interval at 8000 MT/s with 12 modules that this sheet holds (124 intervals of the binaries bwx12, bwx11 and bwx). The lowest of them is 465.53 GB/s (row L-2, process p1nop).
- Limits of this view. For part L the work before the launch differs between the two speeds: part A (bw_old and bw_new) at 7200 MT/s, a bwx12 process at 8000 MT/s. For part C it is a bwx12 process at both speeds. The second group has intervals of 4 s and other counter events (rows L-2 to L-4). 4 of the 8 oldread intervals of part C are at position 2, directly after read. Each memory speed has one boot.
- Insufficient data: why old read was lower in part L. The like.spec line, run in turn from an idle start and directly after part A, at least 3 times each, in one boot, would resolve it (the measurement of hypothesis H1 in section 6).

**Part C, oldread.**

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part C, all oldread intervals | rerun, cfwd and crev | 7200 MT/s, 12 modules | 8 intervals / 4 processes | 464.00 to 468.14 | 466.75 | [Ref43] [Ref47] [Ref51] [Ref55] |
| part C, cfwd, position 0 | first interval of each round | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 465.54 to 467.83 | 466.75 | [Ref43] [Ref51] |
| part C, crev, position 2 | directly after read | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 464.00 to 468.14 | 466.22 | [Ref47] [Ref55] |
| L-1 alone | baseline of part L: its argument line is that of like.spec. It differs from cfwd.spec and crev.spec in --seq. oldread at position 0 | 8000 MT/s, 12 modules | 2 intervals / 1 process | 467.35 to 468.06 | 467.71 | [Ref73] |
| pool L-1 to L-4 | bwx12 rows, oldread at position 0 | 8000 MT/s, 12 modules | 11 intervals / 7 processes | 465.53 to 470.05 | 468.91 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| pool L-1 to L-4, R0, R0b | bwx12 rows and other-binary rows, oldread at position 0 | 8000 MT/s, 12 modules | 18 intervals / 12 processes | 465.53 to 470.05 | 469.10 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| pool B7a, B7b, C3a, C3b, position 0 | other binary (bwx), oldread at position 0 | 8000 MT/s, 12 modules | 48 intervals / 24 processes | 467.34 to 472.95 | 470.53 | [Ref123] [Ref125] [Ref127] [Ref129] |
| the same, only the 12 processes with --start common | other binary (bwx), oldread at position 0 | 8000 MT/s, 12 modules | 24 intervals / 12 processes | 467.34 to 472.19 | 470.53 | [Ref123] [Ref125] [Ref127] [Ref129] |
| pool B7a, B7b, C3a, C3b, position 7 | other binary (bwx), oldread directly after read | 8000 MT/s, 12 modules | 48 intervals / 24 processes | 467.04 to 472.34 | 469.66 | [Ref123] [Ref125] [Ref127] [Ref129] |
| the same, only the 12 processes with --start common | other binary (bwx), oldread directly after read | 8000 MT/s, 12 modules | 24 intervals / 12 processes | 467.04 to 471.54 | 469.61 | [Ref123] [Ref125] [Ref127] [Ref129] |

| 7200 MT/s row | Its range, GB/s | 8000 MT/s range used | That range, GB/s | Overlap | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | Wording by rule V1 point 2 |
|---|---|---|---|---|---|---|---|
| part C, all oldread intervals | 464.00 to 468.14 | L-1 alone (position 0) | 467.35 to 468.06 | yes | 0 | 0.2 | - |
| part C, all oldread intervals | 464.00 to 468.14 | pool L-1 to L-4 (position 0) | 465.53 to 470.05 | yes | 0 | 1.0 | "no difference seen" |
| part C, all oldread intervals | 464.00 to 468.14 | pool L-1 to L-4, R0, R0b (position 0) | 465.53 to 470.05 | yes | 0 | 1.0 | - |
| part C, cfwd, position 0 | 465.54 to 467.83 | pool L-1 to L-4 (position 0) | 465.53 to 470.05 | yes | 0 | 1.0 | - |
| part C, cfwd, position 0 | 465.54 to 467.83 | other binary bwx, position 0 | 467.34 to 472.95 | yes | 0 | 1.2 | - |
| part C, crev, position 2 | 464.00 to 468.14 | other binary bwx, position 7 (after read) | 467.04 to 472.34 | yes | 0 | 1.1 | - |

- Wording by rule V1 point 2: "no difference seen". n at 7200 MT/s: 8 intervals / 4 processes / 3 sessions and 1 extra process / 1 boot. n at 8000 MT/s: 11 intervals / 7 processes / 1 boot. This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 and 3 would present part C at 7200 MT/s only (decision (r) in section 2).
- The test cannot exclude a difference of about 1.0 % (est. from one boot). That is the width of the 8000 MT/s range (465.53 to 470.05 GB/s).
- The ranges also overlap against L-1 alone and against the pool with the other-binary rows.
- 2 of the 8 intervals of part C lie below the lowest value of the pool (T72C4).
- In the view by start state above (added after the numbers were seen), all 8 intervals of part C lie below the 5 bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (468.56 to 470.05 GB/s), by 0.42 GB/s at the nearest ends. Against the other-binary processes with that kind of start state part C overlaps (limit in that view).
- Only oldread at position 0 (cfwd) has a position-matched bwx12 baseline (rule V4). The rows of runner bwx are another binary. They are shown for the position after read.

### 4.3 New read kernel in part A (rule V3)

- Session 1 is compared with the 8000 MT/s processes of the same round in rows A-1 and A-2. bw_old asmread has a process in row A-1 only.
- A cell shows the three intervals in GB/s and, in brackets, their pass counts.
- No percent is given here (rules V3 and V1 point 3).

| Binary and kernel | Round | 7200 MT/s, session 1 | 8000 MT/s, A-1, same round | 8000 MT/s, A-2, same round | 8000 MT/s range of the round, GB/s | Wording by rule V3 | Distance to the nearer end of the range, GB/s |
|---|---|---|---|---|---|---|---|
| bw_new read | 1 | 330.59 (664), 330.09 (664), 333.25 (664) | 285.06 (600), 279.66 (600), 280.27 (600) | 288.94 (600), 293.39 (600), 297.34 (600) | 279.66 to 297.34 | outside (above) | 32.75 to 35.91 |
| bw_new read | 2 | 327.60 (664), 332.82 (664), 326.68 (664) | 304.05 (600), 299.58 (600), 294.02 (600) | 311.51 (663), 311.67 (603), 316.31 (664) | 294.02 to 316.31 | outside (above) | 10.37 to 16.51 |
| bw_new asmread | 1 | 321.15 (664), 325.55 (664), 321.79 (664) | 271.10 (600), 282.31 (600), 275.99 (600) | 287.53 (600), 292.60 (600), 304.09 (600) | 271.10 to 304.09 | outside (above) | 17.06 to 21.46 |
| bw_new asmread | 2 | 331.77 (664), 331.36 (664), 331.73 (664) | 305.90 (664), 296.90 (600), 295.72 (600) | 318.68 (664), 321.87 (664), 314.43 (622) | 295.72 to 321.87 | outside (above) | 9.49 to 9.90 |
| bw_old asmread | 1 | 321.15 (664), 326.26 (664), 322.56 (664) | 276.76 (600), 273.87 (600), 272.79 (600) | no process in this row | 272.79 to 276.76 | outside (above) | 44.39 to 49.50 |
| bw_old asmread | 2 | 331.23 (664), 340.22 (699), 336.20 (720) | 282.02 (600), 288.05 (600), 283.85 (600) | no process in this row | 282.02 to 288.05 | outside (above) | 43.18 to 52.17 |

- All 6 load-only cells of session 1 lie above the 8000 MT/s range of their round.
- Rule V4 point 3 for bw_new read: the two 8000 MT/s medians are 289.54 GB/s (A-1) and 304.43 GB/s (A-2), 14.89 GB/s apart. Each is the median of 6 intervals / 2 processes / 1 boot, rounds 1 and 2 taken together. The median of session 1 is 330.34 GB/s (6 intervals / 2 processes / session 1 / 1 boot, rounds 1 and 2 taken together). It is 40.80 GB/s above A-1 and 25.92 GB/s above A-2. Both distances are larger than the distance between the two baselines. The tables of this section keep the two rounds apart. These three medians take them together. Rule V4 point 3 quotes the two 8000 MT/s medians in this form [Ref7].
- Pass counts differ: the 7200 MT/s intervals of this table completed 664 to 720 passes. Of the 30 intervals at 8000 MT/s, 23 completed 600 passes, and the others 603, 622, 663, 664. The whole-pass stop rule moves the rate together with the pass count (rule V3, effect a). So part A cannot give the size of a change.
- Limit: session 1 started from an idle machine, without the one-thread phase of 2026-11-13 (section 1.5). Row A-1 started directly after its one-thread phase, at a load of 1.00 (section 1.5, point 1). Row A-2 started 8 s after the end of a run of 68 s that held one-thread processes only, at a load of 0.64 (section 1.5, point 11).

The same intervals, restricted to an equal pass count (663 or 664 passes) and kept apart by round. This view is not part of rule V3. It was added while this sheet was built.

| Binary and kernel | Round | 7200 MT/s, session 1, GB/s | 8000 MT/s, A-1 and A-2, same round, GB/s | Overlap | Distance of the nearest ends, GB/s |
|---|---|---|---|---|---|
| bw_new read | 1 | 330.09 to 333.25 (n=3) | no such interval (6 intervals, passes: 600) | - | - |
| bw_new read | 2 | 326.68 to 332.82 (n=3) | 311.51 to 316.31 (n=2: A-2 2) | no | +10.37 |
| bw_new asmread | 1 | 321.15 to 325.55 (n=3) | no such interval (6 intervals, passes: 600) | - | - |
| bw_new asmread | 2 | 331.36 to 331.77 (n=3) | 305.90 to 321.87 (n=3: A-1 1, A-2 2) | no | +9.49 |
| bw_old asmread | 1 | 321.15 to 326.26 (n=3) | no such interval (3 intervals, passes: 600) | - | - |
| bw_old asmread | 2 | 331.23 (n=1) | no such interval (3 intervals, passes: 600) | - | - |

- Round 1: no 8000 MT/s interval has 663 or 664 passes. All 15 have 600 passes. So round 1 gives no comparison at an equal pass count.
- Round 2: bw_new read and bw_new asmread have such intervals at both speeds. Session 1 lies above the 8000 MT/s intervals in both cells, by 10.37 and 9.49 GB/s at the nearest ends. bw_old asmread has no such 8000 MT/s interval.
- Limit: this view uses 5 of the 15 round-2 intervals at 8000 MT/s.

Rates of the threads in the same rows, kept apart by round. The column per_thread_avg_GBps of the csv gives the average rate of the 120 threads of an interval. 120 times this value is the sum of the thread rates. It is an estimate (est.): the column is rounded to 0.01 GB/s, so each sum is exact to 0.6 GB/s.

| Binary and kernel | Round | 7200 MT/s, session 1: average per thread, GB/s | 8000 MT/s, A-1: average per thread, GB/s | 8000 MT/s, A-2: average per thread, GB/s | 7200 MT/s: 120 x average, GB/s (est.) | 8000 MT/s, A-1 and A-2: 120 x average, GB/s (est.) | Distance of the nearest ends by 120 x average, GB/s (est.) | Distance of the nearest ends by aggregate_GBps, GB/s |
|---|---|---|---|---|---|---|---|---|
| bw_new read | 1 | 2.83 to 2.86 | 2.38 to 2.43 | 2.45 to 2.52 | 339.6 to 343.2 | 285.6 to 302.4 | +37.2 | +32.75 |
| bw_new read | 2 | 2.80 to 2.85 | 2.51 to 2.59 | 2.64 to 2.69 | 336.0 to 342.0 | 301.2 to 322.8 | +13.2 | +10.37 |
| bw_new asmread | 1 | 2.76 to 2.78 | 2.28 to 2.42 | 2.44 to 2.60 | 331.2 to 333.6 | 273.6 to 312.0 | +19.2 | +17.06 |
| bw_new asmread | 2 | 2.83 | 2.55 to 2.56 | 2.70 to 2.73 | 339.6 | 306.0 to 327.6 | +12.0 | +9.49 |
| bw_old asmread | 1 | 2.74 to 2.79 | 2.28 to 2.32 | no process | 328.8 to 334.8 | 273.6 to 278.4 | +50.4 | +44.39 |
| bw_old asmread | 2 | 2.83 to 2.94 | 2.39 to 2.48 | no process | 339.6 to 352.8 | 286.8 to 297.6 | +42.0 | +43.18 |

- In all 6 cells every per-thread average of session 1 lies above every per-thread average of the 8000 MT/s processes of the same round.
- By 120 x average (est.) the distance of the nearest ends is larger than by aggregate_GBps in 5 of the 6 cells. In bw_old asmread, round 2 it is 1.18 GB/s smaller. That is inside the rounding of the column (each end is exact to 0.6 GB/s).
- Check of the estimate: A1.csv (row A-2) holds one row per thread, rounded to 0.01 GB/s. Over its 36 intervals the sum of the 120 thread rows differs from 120 x per_thread_avg_GBps by at most 0.66 GB/s [Ref70]. Both sides are rounded, so a difference of up to 1.2 GB/s fits.
- So by this estimate the sum of the thread rates is also higher in session 1 than in the 8000 MT/s rows of the same round. The estimate does not show a part of a distance that comes from the pass count alone.
- Insufficient data: how much of each distance in the first table comes from the pass-count step of the whole-pass stop rule. Part A with the option --per-thread at 7200 MT/s would resolve it. It prints the rate of every thread, as A1.csv does.

### 4.4 Load-only loop in part L (asmread, position 1, directly after oldread)

- asmread is used in place of the new read kernel here. It is the same loop of 8 "ldp q" loads per 256 B [Ref21].
- F72d12 and control I are separate 7200 MT/s rows of the same boot. In every range test of rule V1 point 2 each of them is its own row. Other places of this sheet give one range over several of these rows, for example the three visits in section 4.6 and the sums per mesh in section 4.7. Such a place says which rows it takes together.

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part L (T72L1 to T72L3). asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | rerun, each process started 5 s after the last 120-thread process of part A of its session | 7200 MT/s, 12 modules | 6 intervals / 3 processes | 321.65 to 327.93 | 322.88 | [Ref31] [Ref35] [Ref39] |
| L-1 | baseline: identical argument line | 8000 MT/s, 12 modules | 2 intervals / 1 process | 298.71 to 300.16 | 299.44 | [Ref73] |
| L-2 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 4 intervals / 2 processes | 288.54 to 305.57 | 300.76 | [Ref77] [Ref78] |
| L-3 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 2 intervals / 1 process | 306.07 to 306.79 | 306.43 | [Ref82] |
| L-4 | supporting: bwx12, other counter events | 8000 MT/s, 12 modules | 3 intervals / 3 processes | 305.27 to 309.17 | 305.55 | [Ref86] [Ref87] [Ref88] |
| pool L-1 to L-4 | all bwx12 rows of the fixed list | 8000 MT/s, 12 modules | 11 intervals / 7 processes | 288.54 to 309.17 | 305.27 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| R0 | other binary (bwx11) | 8000 MT/s, 12 modules | 4 intervals / 2 processes | 296.02 to 303.16 | 299.41 | [Ref92] [Ref93] |
| R0b | other binary (bwx11) | 8000 MT/s, 12 modules | 3 intervals / 3 processes | 299.94 to 309.75 | 300.24 | [Ref97] [Ref98] [Ref99] |
| pool L-1 to L-4, R0, R0b | bwx12 rows and other-binary rows | 8000 MT/s, 12 modules | 18 intervals / 12 processes | 288.54 to 309.75 | 302.75 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| X2d12 | not a baseline (firmware test setting), shown and not used | 8000 MT/s, 12 modules | 2 intervals / 1 process | 301.95 to 307.08 | 304.51 | [Ref103] |
| F72d12 | sample of the same boot as the rerun, earlier visit (load 0.34 at launch, 20 s after the first kernel log line of the boot), kept as its own row in every range test of rule V1 point 2 | 7200 MT/s, 12 modules | 2 intervals / 1 process | 301.90 to 302.78 | 302.34 | [Ref119] |
| control I (T72I1, T72I2) | control, added after the first numbers were seen, idle start | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 313.78 to 317.60 | 315.31 | [Ref59] [Ref63] |

| 7200 MT/s row | Its range, GB/s | 8000 MT/s range used | That range, GB/s | Overlap | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | Wording by rule V1 point 2 |
|---|---|---|---|---|---|---|---|
| part L. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 321.65 to 327.93 | L-1 alone | 298.71 to 300.16 | no | +21.48 | 0.5 | - |
| part L. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 321.65 to 327.93 | pool L-1 to L-4 | 288.54 to 309.17 | no | +12.48 | 7.1 | "differs between the 8000 MT/s boot and the 7200 MT/s boot" |
| part L. asmread is used in place of the new read kernel (same loop: 8 "ldp q" loads per 256 B) | 321.65 to 327.93 | pool L-1 to L-4, R0, R0b | 288.54 to 309.75 | no | +11.90 | 7.3 | - |
| F72d12 (same boot, own row) | 301.90 to 302.78 | L-1 alone | 298.71 to 300.16 | no | +1.73 | 0.5 | - |
| F72d12 (same boot, own row) | 301.90 to 302.78 | pool L-1 to L-4 | 288.54 to 309.17 | yes | 0 | 7.1 | "no difference seen" |
| F72d12 (same boot, own row) | 301.90 to 302.78 | pool L-1 to L-4, R0, R0b | 288.54 to 309.75 | yes | 0 | 7.3 | - |
| control I (same boot, own row) | 313.78 to 317.60 | L-1 alone | 298.71 to 300.16 | no | +13.62 | 0.5 | - |
| control I (same boot, own row) | 313.78 to 317.60 | pool L-1 to L-4 | 288.54 to 309.17 | no | +4.61 | 7.1 | "differs between the 8000 MT/s boot and the 7200 MT/s boot" |
| control I (same boot, own row) | 313.78 to 317.60 | pool L-1 to L-4, R0, R0b | 288.54 to 309.75 | no | +4.03 | 7.3 | - |

- Part L, wording by rule V1 point 2: "differs between the 8000 MT/s boot and the 7200 MT/s boot". Part L is higher by 12.48 GB/s at the nearest ends. n at 7200 MT/s: 6 intervals / 3 processes / 3 sessions / 1 boot. n at 8000 MT/s: 11 intervals / 7 processes / 1 boot. The result is the same against L-1 alone and against the pool with the other-binary rows.
- Control I (added after the first numbers were seen, idle start by the 1-minute load rule): "differs between the 8000 MT/s boot and the 7200 MT/s boot". It is higher by 4.61 GB/s at the nearest ends (13.62 GB/s against L-1 alone). n at 7200 MT/s: 4 intervals / 2 processes / no session / 1 boot. n at 8000 MT/s: 11 intervals / 7 processes / 1 boot. The start state of control I is not that of L-1. L-1 was launched at load averages of 0.00 / 0.00 / 0.00 (1 / 5 / 15 min) [Ref75]. Control I was launched 287 s and 265 s after 120-thread work (section 4.6).
- F72d12 (same boot, same speed, load 0.34 at launch): its range overlaps the pool L-1 to L-4. It does not overlap L-1 alone, where it is 1.73 GB/s higher.
- Hardware error records (section 4.1): 2 corrected records fall inside the interval that sets the lower end of the pool L-1 to L-4 (288.54 GB/s, row L-2, process p2add, round 1). Without this one interval the pool spans 298.61 to 309.17 GB/s (10.55 GB/s wide, 3.5 % of its lower end, 10 intervals / 7 processes / 1 boot). No wording by rule V1 point 2 changes with it: part L and control I still lie above the pool, and F72d12 still lies inside its range. The upper end of the pool is the same. So the distances of the nearest ends do not change. For the rerun the records are not known (section 1.5, point 8).
- By rule V1 point 3 no percent change is given. Section 4.6 states what follows.

### 4.5 Load-only kernels in part C

**Kernel `read` (new read kernel in bwx12).**

- Insufficient data: no 8000 MT/s run of kernel read with bwx12.
- Text required by rule F2 point 3: The bwx12 kernel read (new C read loop) was never run with bwx12 at 8000 MT/s. The 2026-11-15 investigation ran asmread (hand-written loop with the same 8 loads per 256 B) in its place.
- The nearest data come from another binary: the first runner bwx of 2026-11-13. They are not a like-for-like baseline. The like-for-like 8000 MT/s baseline of the new read kernel is part A (section 4.3).

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part C, read after oldread (cfwd, position 1) | rerun | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 320.89 to 324.98 | 321.46 | [Ref43] [Ref51] |
| B7a, read at position 1 (after oldread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 16 intervals / 8 processes | 285.04 to 315.29 | 297.19 | [Ref123] |
| B7b, read at position 1 (after oldread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 16 intervals / 8 processes | 282.89 to 292.38 | 289.40 | [Ref125] |
| C3a, read at position 1 (after oldread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 8 intervals / 4 processes | 289.43 to 305.13 | 292.04 | [Ref127] |
| C3b, read at position 1 (after oldread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 8 intervals / 4 processes | 291.59 to 303.07 | 299.85 | [Ref129] |
| pool B7a, B7b, C3a, C3b, position 1 | other binary (bwx) | 8000 MT/s, 12 modules | 48 intervals / 24 processes | 282.89 to 315.29 | 292.22 | [Ref123] [Ref125] [Ref127] [Ref129] |
| the same, only the 12 processes with --start common | other binary (bwx) | 8000 MT/s, 12 modules | 24 intervals / 12 processes | 282.89 to 315.29 | 291.96 | [Ref123] [Ref125] [Ref127] [Ref129] |
| B5a, read at position 1 (after oldread) | other binary (bwx), tags b5-fwd-* | 8000 MT/s, 12 modules | 2 intervals / 2 processes | 307.75 to 308.73 | 308.24 | [Ref131] |
| B5b, read at position 1 (after oldread) | other binary (bwx), tags b5-fwd-* | 8000 MT/s, 12 modules | 2 intervals / 2 processes | 290.65 to 310.55 | 300.60 | [Ref133] |
| part C, read after asmread (crev, position 1) | rerun | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 322.22 to 326.27 | 324.74 | [Ref47] [Ref55] |
| B7a, read at position 6 (after asmread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 16 intervals / 8 processes | 299.27 to 319.11 | 310.35 | [Ref123] |
| B7b, read at position 6 (after asmread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 16 intervals / 8 processes | 293.43 to 301.68 | 297.61 | [Ref125] |
| C3a, read at position 6 (after asmread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 8 intervals / 4 processes | 298.72 to 314.55 | 305.09 | [Ref127] |
| C3b, read at position 6 (after asmread) | other binary (bwx), tags common-6000-* | 8000 MT/s, 12 modules | 8 intervals / 4 processes | 297.44 to 314.47 | 308.23 | [Ref129] |
| pool B7a, B7b, C3a, C3b, position 6 | other binary (bwx) | 8000 MT/s, 12 modules | 48 intervals / 24 processes | 293.43 to 319.11 | 302.88 | [Ref123] [Ref125] [Ref127] [Ref129] |
| the same, only the 12 processes with --start common | other binary (bwx) | 8000 MT/s, 12 modules | 24 intervals / 12 processes | 293.43 to 319.11 | 304.25 | [Ref123] [Ref125] [Ref127] [Ref129] |

- Against the other-binary pool of the same position, read after oldread is 5.60 GB/s above its highest value. Read after asmread is 3.11 GB/s above its highest value.
- Difference of these references (rule V2 point 4): they used the binary bwx of 2026-11-13. The csv headers show the counter setting: B7a count=0, B7b count=0, C3a count=1, C3b count=1 (count=1 means with core counters). Part C used bwx12 with counters.
- A second difference: 12 of the 24 processes of this pool (tags common-6000-offset-*) used --start offset. Part C used --start common [Ref13] [Ref14]. --start is an option of the runner. This sheet only notes that its value differs. The rows "only the 12 processes with --start common" show the pool without them. At positions 1, 2 and 6 the lowest and the highest value stay the same, and the medians change.
- Rule V4 and rule V2 point 4 name different process lists for these rows. Decision (p) in section 2 states the choice.

**Kernel `asmread`.**

| Row | What it is | Memory speed, modules | n | Min to max, GB/s | Median, GB/s | Source |
|---|---|---|---|---|---|---|
| part C, asmread after oldread (crev, round 1, position 0) | rerun, the condition of part L | 7200 MT/s, 12 modules | 2 intervals / 2 processes | 324.73 to 326.12 | 325.42 | [Ref47] [Ref55] |
| part C, asmread as first interval (crev, round 0, position 0) | rerun | 7200 MT/s, 12 modules | 2 intervals / 2 processes | 319.43 to 324.88 | 322.15 | [Ref47] [Ref55] |
| part C, asmread after read (cfwd, position 2) | rerun | 7200 MT/s, 12 modules | 4 intervals / 2 processes | 320.86 to 323.41 | 321.96 | [Ref43] [Ref51] |
| L-1 alone | baseline of part L: its argument line is that of like.spec. It differs from cfwd.spec and crev.spec in --seq. asmread at position 1 (after oldread) | 8000 MT/s, 12 modules | 2 intervals / 1 process | 298.71 to 300.16 | 299.44 | [Ref73] |
| pool L-1 to L-4 | bwx12 rows, asmread at position 1 (after oldread) | 8000 MT/s, 12 modules | 11 intervals / 7 processes | 288.54 to 309.17 | 305.27 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| pool L-1 to L-4, R0, R0b | bwx12 rows and other-binary rows, asmread at position 1 (after oldread) | 8000 MT/s, 12 modules | 18 intervals / 12 processes | 288.54 to 309.75 | 302.75 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| pool B7a, B7b, C3a, C3b, position 2 | other binary (bwx), asmread after read | 8000 MT/s, 12 modules | 48 intervals / 24 processes | 284.74 to 320.54 | 301.57 | [Ref123] [Ref125] [Ref127] [Ref129] |
| the same, only the 12 processes with --start common | other binary (bwx), asmread after read | 8000 MT/s, 12 modules | 24 intervals / 12 processes | 284.74 to 320.54 | 301.88 | [Ref123] [Ref125] [Ref127] [Ref129] |

| 7200 MT/s row | Its range, GB/s | 8000 MT/s range used | That range, GB/s | Overlap | Distance of the nearest ends, GB/s (+ = 7200 MT/s row higher) | Width of the 8000 MT/s range, % of its lower end (est. from one boot) | Wording by rule V1 point 2 |
|---|---|---|---|---|---|---|---|
| part C, asmread after oldread | 324.73 to 326.12 | L-1 alone (after oldread), asmread at position 1 against position 0 in part C | 298.71 to 300.16 | no | +24.56 | 0.5 | - |
| part C, asmread after oldread | 324.73 to 326.12 | pool L-1 to L-4 (after oldread), asmread at position 1 against position 0 in part C | 288.54 to 309.17 | no | +15.56 | 7.1 | "differs between the 8000 MT/s boot and the 7200 MT/s boot" |
| part C, asmread after oldread | 324.73 to 326.12 | pool L-1 to L-4, R0, R0b (after oldread), asmread at position 1 against position 0 in part C | 288.54 to 309.75 | no | +14.98 | 7.3 | - |
| part C, asmread as first interval | 319.43 to 324.88 | pool L-1 to L-4 (after oldread, at position 1): kernel before and position not matched | 288.54 to 309.17 | no | +10.26 | 7.1 | - |
| part C, asmread after read | 320.86 to 323.41 | pool L-1 to L-4 (after oldread, at position 1): kernel before and position not matched | 288.54 to 309.17 | no | +11.69 | 7.1 | - |
| part C, asmread after read | 320.86 to 323.41 | other binary bwx, position 2 (after read) | 284.74 to 320.54 | no | +0.32 | 12.6 | - |

- asmread after oldread, wording by rule V1 point 2: "differs between the 8000 MT/s boot and the 7200 MT/s boot". n at 7200 MT/s: 2 intervals / 2 processes / session 2 and 1 extra process / 1 boot (T72C2, T72C4). n at 8000 MT/s: 11 intervals / 7 processes / 1 boot. The result is the same against L-1 alone and against the pool with the other-binary rows. This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 and 3 would present part C at 7200 MT/s only (decision (r) in section 2).
- No asmread group of part C has a position-matched bwx12 baseline (rule V4). The group "asmread after oldread" (crev, round 1, position 0) matches rows L-1 to L-4 (asmread at position 1) only in the kernel that ran directly before (rule V2 points 1 and 4). The other two groups do not match in that kernel either. Their rows in the table carry no wording.
- The rows without a wording also show part C next to 8000 MT/s rows. Decision (r) in section 2 names them.
- Rule V2 point 5 asks to state that part L and the forward order measure the lower of the two conditions. At 8000 MT/s (runner bwx) the median of read after oldread is 10.66 GB/s below the median of read after asmread (12.29 GB/s with the 12 --start common processes only). At 7200 MT/s it is 3.28 GB/s below, and the two ranges overlap. The reverse order comes from 2 processes (T72C2, T72C4).
- For asmread the order is the opposite at 7200 MT/s. asmread directly after oldread (crev, round 1, the condition of part L) gave 324.73 and 326.12 GB/s. asmread after read (cfwd) gave 320.86 to 323.41 GB/s. The two ranges do not overlap. They are 1.32 GB/s apart. So the part C data at 7200 MT/s do not show that part L measures the lower condition. Order and process are not separated: each order has 2 processes.

### 4.6 What the rows of the same boot show, and what follows for Q2

The same argument line (like.spec) ran at three times in boot 3bfc57a1 at 7200 MT/s. asmread at position 1 gave:

| Visit | Launch times | Start state | Time since the first kernel log line of the boot | asmread, GB/s | oldread, GB/s | n per kernel |
|---|---|---|---|---|---|---|
| F72d12 | 20:02:36 | load 0.34 at launch. Process list 5 s before the launch: pr/ttyAMA-1 at 51.6 %CPU | 20 s | 301.90 to 302.78 | 467.46 to 468.44 | 2 intervals / 1 process |
| part L | 22:13:34 to 22:19:52 | 5 s after part A (load 74.05 to 104.52) | 2 h 11 min 18 s to 2 h 17 min 36 s | 321.65 to 327.93 | 461.61 to 464.29 | 6 intervals / 3 processes |
| control I (added after the first numbers were seen) | 22:27:05 and 22:32:32 | idle (load 0.87 and 0.91), 287 s and 265 s after 120-thread work. Process lists: at most 0.1 %CPU | 2 h 24 min 49 s and 2 h 30 min 16 s | 313.78 to 317.60 | 466.30 to 469.20 | 4 intervals / 2 processes |

- The three asmread ranges do not overlap each other.
- The lowest asmread value of the three visits is 301.90 GB/s (F72d12). The highest is 327.93 GB/s (part L). They are 26.03 GB/s apart (8.6 % of the lowest value), at one memory speed, inside one boot.
- The two visits that were launched at a load below 1.0 (F72d12 and control I) are at least 11.00 GB/s apart.
- F72d12 and control I differ in more than the time since boot. env.txt of F72d12 was written at 20:02:31, 15 s after the first kernel log line of the boot and 5 s before the launch. It lists pr/ttyAMA-1 at 51.6 %CPU and systemd at 13.1 %CPU (lines 5 and 6 [Ref120]). env.txt of T72I1 and T72I2 lists at most 0.1 %CPU [Ref60] [Ref64]. So F72d12 is an idle start only by the load-average rule of this sheet.
- Hypothesis (not tested): the thread pr/ttyAMA-1 was still busy during the first seconds of the F72d12 process. What fits: its %CPU value was 51.6 at 20:02:31 and 5.4 at 20:06:34 (line 10 of gaps.txt [Ref136]). With the assumption that the thread started at the first kernel log line (20:02:16), these values mean about 7.7 s of CPU time in the first 15 s and about 13.9 s in the first 258 s (est.). That is about 6.2 s of CPU time in the 243 s between the two readings (est.). The F72d12 process ran inside this time, from 20:02:36 to 20:03:37. Measurement that would confirm or reject it: a sample of the load of every CPU, once per second, in the first minutes after a boot.
- The lowest oldread value of the three visits is 461.61 GB/s (part L). The highest is 469.20 GB/s (control I). They are 7.59 GB/s apart (1.6 % of the lowest value).
- For comparison, the 8000 MT/s rows L-1 to L-4 span 288.54 to 309.17 GB/s (20.63 GB/s wide, 11 intervals / 7 processes / 1 boot), also inside one boot.
- The first runner bwx (other binary) gave 282.89 to 320.54 GB/s for its load-only kernels read and asmread at 8000 MT/s in the processes with the tags common-6000-* (192 intervals / 24 processes / 1 boot, 4 folders of 2026-11-13 and 2026-11-14, same boot).
- Rule V1 point 5: the 12-module data at 8000 MT/s reach 316.31 GB/s (bw_new read, rows A-1 and A-2) and 321.87 GB/s (bw_new asmread, rows A-1 and A-2). In the rows of runner bwx used in this sheet (B7a, B7b, C3a, C3b, tags common-6000-*) they reach 319.11 GB/s (read) and 320.54 GB/s (asmread).
- Higher values of runner bwx exist outside these rows. The reverse-order processes of the two B5 folders (tags b5-rev-*, 4 processes, one interval per kernel, common stop, 6 s) reach 324.36 GB/s for read (process b5-rev-p1 of R/B5-20261114T011723Z, position 7, directly after read_sparse, I row in line 4127) and 324.98 GB/s for asmread (process b5-rev-p1 of R/B5-20261114T011723Z, position 1, directly after asmread2, I row in line 2675) [Ref131]. read_sparse and asmread2 are other kernels of runner bwx. Rule F2 point 4 quotes the range of read over the 8 processes of the two B5 folders: 290.65 to 324.36 GB/s [Ref7].
- The read value of 324.36 GB/s lies inside the 7200 MT/s ranges of both read groups of part C (320.89 to 324.98 and 322.22 to 326.27 GB/s). The asmread value of 324.98 GB/s lies inside the 7200 MT/s range of part L (321.65 to 327.93 GB/s). Both values come from another binary and another kernel order. They are not a like-for-like baseline.

What follows for Q2:

- The same kind of distance is compared on both sides. Nearest ends: part L lies 12.48 GB/s above the 8000 MT/s pool and 18.87 GB/s above F72d12, the earlier visit of the same boot. Medians: 17.61 GB/s and 20.54 GB/s. Farthest ends: 39.38 GB/s and 26.03 GB/s.
- So the move between two visits inside the 7200 MT/s boot is larger than the distance of part L to the 8000 MT/s pool for the nearest ends and for the medians. It is smaller for the farthest ends.
- One of the three 7200 MT/s visits (F72d12) lies inside the range of the 8000 MT/s pool L-1 to L-4. Against L-1 alone it is 1.73 GB/s higher. The other two visits (part L and control I) lie above every row of the pool, by 12.48 and 4.61 GB/s at the nearest ends.
- The comparison of part L with L-1 changes four things at once: the memory speed, the boot, the start state (5 s after part A against a start at load 0.00), and the hardware error records. Row L-1 has 2 corrected records in the first 2 s of its process (est., section 4.1). For the rerun the records are not known. A fifth thing is not known: the firmware settings of the boot of the rerun were not read (section 1.5, point 13).
- Control I (added after the first numbers were seen) reduces the difference of the start state against L-1. The data do not show that it removes it. Control I is like L-1 by the 1-minute load rule only (0.87 and 0.91 against 0.00, all below 1.0). It was launched 287 s and 265 s after a 120-thread process, at 5-minute load averages of 35.79 and 21.05 [Ref61] [Ref65]. L-1 was launched at load averages of 0.00 / 0.00 / 0.00 (1 / 5 / 15 min) [Ref75]. So control I does not rule out an effect of the earlier 120-thread work (hypothesis H1 in section 6, not tested).
- The 8000 MT/s pool also holds 5 processes that started after 120-thread work (section 4.2, view by start state). Part L lies 12.48 GB/s above their asmread range too.
- So the rerun shows that the load-only loop ran above the 8000 MT/s intervals of the same round (rows A-1 and A-2) in session 1 of part A. It ran above every bwx12 row of the fixed 8000 MT/s list (L-1 to L-4) in part L, in control I (added after the first numbers were seen) and in the group "asmread after oldread" of part C (comparison by decision (r) in section 2). It does not show that the memory speed is the cause.
- The statement for part A holds inside the same round only. 2 intervals of bw_new asmread of session 1, round 1 (321.15 and 321.79 GB/s, lines 53 and 55 [Ref25]) lie below the highest round-2 interval of row A-2 (321.87 GB/s, line 3308 [Ref70]).
- Text required by rule V1 point 3: Insufficient data: whether a difference of the new read kernel comes from the memory speed. Speed and boot changed together. Two boots at equal settings (10 modules, one process each) gave asmread 260.37 / 262.67 and 285.57 / 286.45 GB/s, 9.4 % apart (medians). Runs in several boots per speed would resolve it (needs reboots, not part of this task). [Ref107] [Ref111]
- Text of rule V1 point 4 for old read: three 10-module boots gave old read 359.56 to 362.15 GB/s (0.7 % wide, 6 intervals / 3 processes / 3 boots). So the boot alone moved old read by less than 1 % there. [Ref107] [Ref111] [Ref115]
- Limit of this text: the three boots did not differ by the boot alone. X1d10 and X1d10b ran with the same changed TXREQ firmware settings (old read 359.56 to 361.50 and 359.58 to 361.21 GB/s). BASEd10 ran with the original settings (359.89 to 362.15 GB/s) [Ref138]. So the words "the boot alone" rest on the pair X1d10 and X1d10b (359.56 to 361.50 GB/s, 0.5 % wide, 4 intervals / 2 processes / 2 boots).

### 4.7 Sums per mesh (looked at after the numbers were seen, not part of the fixed rules)

The table gives the lowest and highest sum per mesh over the intervals of each row. Mesh 0 holds 64 threads, mesh 1 holds 56.

- The sums of every interval are in facts.json (fields mesh0_GBps and mesh1_GBps). The tables of sections 3.2 and 3.3 print them for parts L and C, control I and F72d12 (columns "m0 + m1").
- The part C rows are shown next to 8000 MT/s rows here. Rule F2 points 2 and 3 would not do this (decision (r) in section 2). The bullets under the tables give the oldread result with part C and without it.

oldread:

| Row | Memory speed | Intervals | Mesh 0, GB/s | Mesh 1, GB/s | Source |
|---|---|---|---|---|---|
| part L | 7200 MT/s | 6 | 303.43 to 306.59 | 157.17 to 158.50 | [Ref31] [Ref35] [Ref39] |
| part C | 7200 MT/s | 8 | 307.05 to 310.92 | 156.78 to 157.79 | [Ref43] [Ref47] [Ref51] [Ref55] |
| control I (added after the first numbers were seen) | 7200 MT/s | 4 | 306.00 to 309.95 | 156.70 to 160.30 | [Ref59] [Ref63] |
| F72d12 | 7200 MT/s | 2 | 307.61 to 308.78 | 159.66 to 159.84 | [Ref119] |
| pool L-1 to L-4 (bwx12) | 8000 MT/s | 11 | 312.95 to 318.70 | 150.27 to 152.93 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| R0, R0b (bwx11) | 8000 MT/s | 7 | 314.57 to 317.41 | 152.16 to 153.04 | [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| B7a, B7b, C3a, C3b (bwx), positions 0 and 7 | 8000 MT/s | 96 | 310.20 to 320.61 | 151.27 to 158.30 | [Ref123] [Ref125] [Ref127] [Ref129] |

Load-only kernels. Part C has one row per group (rule V2). No bwx12 row at 8000 MT/s holds the kernel read:

| Row | Memory speed | Intervals | Mesh 0, GB/s | Mesh 1, GB/s | Source |
|---|---|---|---|---|---|
| part L, asmread | 7200 MT/s | 6 | 175.75 to 178.69 | 143.16 to 149.24 | [Ref31] [Ref35] [Ref39] |
| part C, read after oldread | 7200 MT/s | 4 | 176.69 to 178.81 | 142.70 to 146.17 | [Ref43] [Ref51] |
| part C, read after asmread | 7200 MT/s | 4 | 177.98 to 180.65 | 144.24 to 146.21 | [Ref47] [Ref55] |
| part C, asmread after read | 7200 MT/s | 4 | 177.36 to 177.96 | 143.13 to 145.51 | [Ref43] [Ref51] |
| part C, asmread as first interval of the process | 7200 MT/s | 2 | 175.68 to 178.59 | 143.75 to 146.29 | [Ref47] [Ref55] |
| part C, asmread after oldread | 7200 MT/s | 2 | 179.38 to 180.41 | 145.35 to 145.70 | [Ref47] [Ref55] |
| control I (added after the first numbers were seen), asmread | 7200 MT/s | 4 | 170.63 to 172.93 | 141.68 to 144.95 | [Ref59] [Ref63] |
| F72d12, asmread | 7200 MT/s | 2 | 162.29 to 162.82 | 139.61 to 139.95 | [Ref119] |
| pool L-1 to L-4 (bwx12), asmread at position 1 | 8000 MT/s | 11 | 159.55 to 173.59 | 128.99 to 135.87 | [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] |
| R0, R0b (bwx11), asmread at position 1 | 8000 MT/s | 7 | 165.18 to 174.70 | 129.48 to 135.05 | [Ref92] [Ref93] [Ref97] [Ref98] [Ref99] |
| B7a, B7b, C3a, C3b (bwx), read at positions 1 and 6 and asmread at positions 2 and 5 | 8000 MT/s | 192 | 154.90 to 182.53 | 126.96 to 139.45 | [Ref123] [Ref125] [Ref127] [Ref129] |

- oldread, all 20 intervals at 7200 MT/s (F72d12, parts L and C, and control I, which was added after the first numbers were seen): mesh 1 gave 156.70 to 160.30 GB/s and mesh 0 gave 303.43 to 310.92 GB/s [Ref31] [Ref35] [Ref39] [Ref43] [Ref47] [Ref51] [Ref55] [Ref59] [Ref63] [Ref119].
- oldread, the 18 intervals of bwx12 and bwx11 at 8000 MT/s: mesh 1 gave 150.27 to 153.04 GB/s and mesh 0 gave 312.95 to 318.70 GB/s [Ref73] [Ref77] [Ref78] [Ref82] [Ref86] [Ref87] [Ref88] [Ref92] [Ref93] [Ref97] [Ref98] [Ref99]. Against these rows mesh 1 is higher and mesh 0 is lower in every 7200 MT/s interval.
- The same without part C (rule F2 points 2 and 3, decision (r) in section 2): the 12 oldread intervals of part L, of control I (added after the first numbers were seen) and of F72d12, the earlier run of the same boot, gave 156.70 to 160.30 GB/s on mesh 1 and 303.43 to 309.95 GB/s on mesh 0. Against the same 8000 MT/s rows mesh 1 is higher and mesh 0 is lower in every one of these intervals too.
- The same without part C and without control I: the 8 oldread intervals of part L and of F72d12 gave 157.17 to 159.84 GB/s on mesh 1 and 303.43 to 308.78 GB/s on mesh 0. Against the same 8000 MT/s rows mesh 1 is higher and mesh 0 is lower in every one of these intervals too. So the result does not rest on control I.
- This does not hold in full against the rows of the first runner bwx at 8000 MT/s. There mesh 1 gave 151.27 to 158.30 GB/s and mesh 0 gave 310.20 to 320.61 GB/s (96 intervals) [Ref123] [Ref125] [Ref127] [Ref129]. With part C, both 7200 MT/s ranges overlap these ranges. Without part C, the mesh 1 ranges overlap, and the mesh 0 range at 7200 MT/s ends 0.26 GB/s below the mesh 0 range of runner bwx.
- So the split between the meshes also moved between visits at 8000 MT/s. Insufficient data: whether the memory speed changes the split. Runs in several boots per speed would resolve it.

### 4.8 Record only: read_nop96, read_nop256, read_1pl

Total in GB/s, lowest to highest interval. No statement is made from this table.

| Kernel | Part L, 7200 MT/s | Control I (added after the first numbers were seen), 7200 MT/s | F72d12, 7200 MT/s, same boot | L-1 (w120-R8), 8000 MT/s |
|---|---|---|---|---|
| read_nop96 | 461.68 to 465.61 (n=6) | 466.80 to 468.26 (n=4) | 468.54 to 468.96 (n=2) | 468.36 to 468.65 (n=2) |
| read_nop256 | 560.92 to 561.22 (n=6) | 561.01 to 561.37 (n=4) | 560.88 to 561.25 (n=2) | 547.59 to 547.82 (n=2) |
| read_1pl | 233.29 to 237.32 (n=6) | 230.44 to 232.96 (n=4) | 228.30 to 231.10 (n=2) | 231.39 to 231.42 (n=2) |

### 4.9 Verdict for Q2

**Verdict, old read kernel.** Old read kernel. Part A (bw_old read): "no difference seen" (7200 MT/s: 459.90 to 474.15 GB/s, n = 18 intervals / 6 processes / 3 sessions / 1 boot. 8000 MT/s: 463.58 to 469.03 GB/s, n = 21 intervals / 7 processes / 1 boot). The test cannot exclude a difference of about 1.2 % (est. from one boot), which is the width of the 8000 MT/s range. Part C (oldread): "no difference seen" (7200 MT/s: 464.00 to 468.14 GB/s, n = 8 intervals / 4 processes / 3 sessions and 1 extra process / 1 boot. 8000 MT/s: 465.53 to 470.05 GB/s, n = 11 intervals / 7 processes / 1 boot). There the test cannot exclude a difference of about 1.0 % (est. from one boot). This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 and 3 would present part C at 7200 MT/s only (decision (r) in section 2). Part L (oldread): "differs between the 8000 MT/s boot and the 7200 MT/s boot" (7200 MT/s: 461.61 to 464.29 GB/s, n = 6 intervals / 3 processes / 3 sessions / 1 boot. 8000 MT/s: 465.53 to 470.05 GB/s, n = 11 intervals / 7 processes / 1 boot). Part L is lower by 1.24 GB/s at the nearest ends (0.3 % of the lower end of the 8000 MT/s range, 465.53 GB/s) and by 6.27 GB/s between the medians (1.3 % of the 8000 MT/s median, 468.91 GB/s). Two other rows of the same line in the same 7200 MT/s boot overlap the 8000 MT/s range. F72d12 (1 process at 20:02 UTC, before the rerun, load 0.34 at launch) gave 467.46 to 468.44 GB/s. Control I (2 processes, idle start, added after the first numbers were seen, not part of the plan fixed before the run) gave 466.30 to 469.20 GB/s. So against the whole pool L-1 to L-4, only the range of part L, which started 5 s after part A, lies below the 8000 MT/s range among the bwx12 runs. A view added after the numbers were seen splits the 8000 MT/s pool by start state: the 5 bwx12 processes of the pool that started 5 s to 25 s after a 120-thread bwx12 process gave 468.56 to 470.05 GB/s (7 intervals / 5 processes / 1 boot), the highest oldread values of the pool. Part L is 4.27 GB/s below them. Part C started 5 s after 120-thread work too. It is 0.42 GB/s below them at the nearest ends, and its 4 position-matched intervals (cfwd, position 0) are 0.73 GB/s below them. Limit: these 5 processes are not all 8000 MT/s processes with that kind of start state. Against the other-binary processes that started after 120-thread work, part C overlaps (bwx11: 467.86 to 469.96 GB/s, 4 intervals / 3 processes. Runner bwx, position 0: 467.34 to 472.95 GB/s, 48 intervals / 24 processes). Part L lies below every oldread interval at 8000 MT/s with 12 modules that this sheet holds (the lowest is 465.53 GB/s, row L-2, process p1nop). So the 8000 MT/s rows do not show that a start after 120-thread work lowers the old read kernel. The data do not show that the boot or the memory speed is the cause: each memory speed has one boot. Insufficient data: why part L was lower. The like.spec line, run in turn from an idle start and directly after part A, at least 3 times each, in one boot, would resolve it (the measurement of hypothesis H1 in section 6).

**Verdict, new read kernel.** New read kernel. Part A (bw_new read, session 1): outside the 8000 MT/s range of the same round in both rounds. Round 1: 32.75 to 35.91 GB/s above the upper end of the round-1 range (297.34 GB/s). Round 2: 10.37 to 16.51 GB/s above the upper end of the round-2 range (316.31 GB/s). n per round at 7200 MT/s: 3 intervals / 1 process / session 1 / 1 boot. n per round at 8000 MT/s: 6 intervals / 2 processes / 1 boot. The pass counts differ, so part A gives no exact size. Part L (asmread, the same loop, used in place of the new read kernel): "differs between the 8000 MT/s boot and the 7200 MT/s boot" (7200 MT/s: 321.65 to 327.93 GB/s, n = 6 intervals / 3 processes / 3 sessions / 1 boot. 8000 MT/s: 288.54 to 309.17 GB/s, n = 11 intervals / 7 processes / 1 boot). Part C, asmread directly after oldread (crev, round 1, position 0): "differs between the 8000 MT/s boot and the 7200 MT/s boot" (7200 MT/s: 324.73 to 326.12 GB/s, n = 2 intervals / 2 processes / session 2 and 1 extra process / 1 boot. 8000 MT/s: 288.54 to 309.17 GB/s, n = 11 intervals / 7 processes / 1 boot). Part C is higher by 15.56 GB/s at the nearest ends. This baseline matches in the kernel that ran directly before. It does not match in the position: asmread is at position 1 in rows L-1 to L-4. This comparison of part C with 8000 MT/s follows rules V1 point 2, V2 point 4 and V4. Rule F2 points 2 and 3 would present part C at 7200 MT/s only (decision (r) in section 2). Two corrected hardware error records fall inside the 8000 MT/s interval with the lowest asmread value (288.54 GB/s). Without this interval the 8000 MT/s range is 298.61 to 309.17 GB/s (10 intervals / 7 processes / 1 boot), and no wording changes (sections 4.1 and 4.4). Part C (kernel read): Insufficient data: no 8000 MT/s run of kernel read with bwx12. The same line in the same 7200 MT/s boot gave asmread 301.90 to 302.78 GB/s at 20:02 UTC (F72d12, before the rerun, n = 2 intervals / 1 process / no session / 1 boot). That is inside the range of the 8000 MT/s pool L-1 to L-4. Against L-1 alone it is 1.73 GB/s higher. F72d12 is an idle start only by the load-average rule of this sheet: its process list, written 5 s before the launch, shows pr/ttyAMA-1 at 51.6 %CPU (section 4.6). Control I (idle start, added after the first numbers were seen, not part of the plan fixed before the run) gave asmread 313.78 to 317.60 GB/s (n = 4 intervals / 2 processes / no session / 1 boot). That is also above every bwx12 row of the fixed 8000 MT/s list, by 4.61 GB/s at the nearest ends (13.62 GB/s against L-1 alone). The three visits of the boot span 301.90 to 327.93 GB/s. Inside this one boot at one memory speed, part L lies 18.87 GB/s above F72d12 at the nearest ends and 20.54 GB/s between the medians. That is more than the distance of part L to the 8000 MT/s range (12.48 GB/s at the nearest ends, 17.61 GB/s between the medians). Between the farthest ends the order is the opposite (26.03 GB/s inside the boot against 39.38 GB/s to the 8000 MT/s range). Insufficient data: whether a difference of the new read kernel comes from the memory speed. Speed and boot changed together. Two boots at equal settings (10 modules, one process each) gave asmread 260.37 / 262.67 and 285.57 / 286.45 GB/s, 9.4 % apart (medians). Runs in several boots per speed would resolve it (needs reboots, not part of this task).

## 5. Record only: write, copy, asmwrite, asmcopy of part A

- No statement is made from these rows (rule V3). FINDINGS.md section F1 shows that the whole-pass stop rule at 0.5 s moves the write totals [Ref21].
- A cell shows n: lowest / median / highest rate in GB/s. The copy kernels count read plus written bytes.

| Kernel | Binary | 2026-11-13 (A-1), 8000 MT/s | Session 1, 7200 MT/s | Session 2, 7200 MT/s | Session 3, 7200 MT/s |
|---|---|---|---|---|---|
| write | bw_old | 6: 140.91 / 144.62 / 186.88 | 6: 143.48 / 144.74 / 181.27 | 6: 143.68 / 144.73 / 181.69 | 6: 143.50 / 144.51 / 146.08 |
| write | bw_new | 6: 123.52 / 131.92 / 147.78 | 6: 117.23 / 120.72 / 142.53 | 6: 117.43 / 123.33 / 144.11 | 6: 117.53 / 117.69 / 147.49 |
| copy | bw_old | 6: 154.96 / 157.21 / 158.56 | 6: 155.39 / 156.37 / 157.43 | 6: 155.18 / 156.15 / 157.47 | 6: 155.06 / 156.02 / 158.24 |
| copy | bw_new | 6: 153.91 / 156.10 / 162.41 | 6: 154.79 / 155.79 / 160.92 | 6: 154.46 / 156.26 / 159.00 | 6: 155.06 / 155.89 / 156.91 |
| asmwrite | bw_old | 6: 117.52 / 117.64 / 147.83 | 6: 117.33 / 117.57 / 148.08 | 6: 117.55 / 117.63 / 143.80 | 6: 117.34 / 117.60 / 128.92 |
| asmwrite | bw_new | 6: 117.26 / 117.50 / 152.01 | 6: 117.54 / 120.83 / 143.78 | 6: 117.61 / 123.81 / 139.84 | 6: 117.32 / 117.65 / 147.72 |
| asmcopy | bw_old | 6: 153.82 / 157.43 / 158.46 | 6: 154.41 / 155.49 / 157.75 | 6: 154.39 / 155.73 / 156.47 | 6: 154.18 / 155.89 / 157.93 |
| asmcopy | bw_new | 6: 153.58 / 155.37 / 158.37 | 6: 155.02 / 155.74 / 156.21 | 6: 153.71 / 155.40 / 158.01 | 6: 153.85 / 155.11 / 158.90 |

## 6. What is established, what is not, and hypotheses

### Established

1. The rerun ran in boot 3bfc57a1 with 12 memory modules (MemTotal 395392808 kB in every state line). The same boot was recorded with 12 modules at 7200 MT/s at 20:02:21 (section 1.2).
2. The run is complete: all 27 integrity checks pass (section 1.4).
3. Q1: the new read kernel is below the old read kernel in every pair of parts A and C. asmread is below the old read kernel in every pair of parts L and C (section 3.4).
4. The size of the drop is not one value. Part L (asmread): 29.2 % to 30.5 %. Part C: read after oldread 30.5 % to 31.2 %, read after asmread 29.7 % to 31.1 %, asmread after read 30.8 % to 31.2 %, asmread as first interval 30.1 % to 31.7 %, asmread after oldread 29.7 % to 30.6 %. Control I (added after the first numbers were seen): 31.9 % to 32.8 %. F72d12, the earlier run of the same boot: 35.4 % (section 3.4).
5. Q2, old read kernel: against the whole 8000 MT/s pool (A-1 to A-3 for part A, L-1 to L-4 for the bwx12 rows) its range overlaps in part A, in part C, in control I (added after the first numbers were seen) and in F72d12. Only the range of part L lies below the pool, by 1.24 GB/s at the nearest ends and by 6.27 GB/s between the medians. In the view by start state (added after the numbers were seen), part C also lies below the 5 bwx12 processes of the pool L-1 to L-4 that started after 120-thread work, by 0.42 GB/s at the nearest ends. Against the other-binary processes with that kind of start state part C overlaps (section 4.2). The comparison of part C with 8000 MT/s follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.
6. Q2, load-only loop: in session 1 of part A it ran above the 8000 MT/s intervals of the same round (rows A-1 and A-2). In part L, in control I (added after the first numbers were seen) and in the group "asmread after oldread" of part C it ran above every bwx12 row of the fixed 8000 MT/s list, L-1 to L-4 (sections 4.3 to 4.5). The comparison of part C with 8000 MT/s follows decision (r) in section 2: rule F2 points 2 and 3 would not make it.
7. In the one 7200 MT/s boot the load-only loop gave 301.90 to 302.78 GB/s at 20:02:36 and 321.65 to 327.93 GB/s at 22:13:34 to 22:19:52 for the same argument line (section 4.6).
8. In part A the second-round process of a load-only kernel is above the first-round process, without overlap, in 8 of 9 cells (3 sessions x bw_new read, bw_old asmread, bw_new asmread, see the table of section 3.1).
9. Against the bwx12 and bwx11 rows at 8000 MT/s, oldread at 7200 MT/s read more on mesh 1 and less on mesh 0 in every interval. This holds with part C (20 intervals) and without part C (12 intervals of part L, of control I (added after the first numbers were seen) and of F72d12, the earlier run of the same boot). It also holds without part C and without control I (8 intervals of part L and of F72d12). This sheet shows part C next to 8000 MT/s rows by decision (r) in section 2. Rule F2 points 2 and 3 would not do it. Against the rows of runner bwx the result does not hold in full: the mesh 1 ranges overlap, and the mesh 0 ranges overlap when part C is included (section 4.7, looked at after the numbers were seen).
10. The bwx12 row F72d12 ran in the boot of the rerun: its process lies between two readings of the same boot id (section 4.1).
11. Hardware error records at 8000 MT/s: 2 corrected records fall inside the interval with the lowest asmread value of the pool L-1 to L-4, and 2 fall before or inside the first oldread interval of row L-1 (section 4.1). No wording by rule V1 point 2 changes without the first of these intervals (section 4.4).

### Not established

1. Insufficient data: whether a difference of the new read kernel comes from the memory speed. Speed and boot changed together. Two boots at equal settings (10 modules, one process each) gave asmread 260.37 / 262.67 and 285.57 / 286.45 GB/s, 9.4 % apart (medians). Runs in several boots per speed would resolve it (needs reboots, not part of this task).
2. Insufficient data: why the load-only loop differs between the three visits of the same boot (section 4.6). The measurements named under H1 and H2 would resolve it.
3. Insufficient data: why old read was 461.61 to 464.29 GB/s in part L and 466.30 to 469.20 GB/s in control I (added after the first numbers were seen). The 8000 MT/s rows do not point to the start state: there the 5 bwx12 processes that started after 120-thread work gave higher oldread values (468.56 to 470.05 GB/s, 7 intervals / 5 processes) than the 2 processes that started at a load below 1.0 (465.53 to 468.06 GB/s, 4 intervals / 2 processes) (section 4.2, view added after the numbers were seen). The measurement named under H1 would resolve it.
4. Insufficient data: no 8000 MT/s run of kernel read with bwx12. A run of cfwd.spec and crev.spec at 8000 MT/s would resolve it (needs a change of the firmware setting and a reboot, so root and approval).
5. Insufficient data: whether hardware error records occurred during the rerun. A count of the "[Hardware Error]" lines of the kernel log would resolve it (needs root).
6. Insufficient data: a direct reading of the memory speed during the rerun. `sudo dmidecode -t 17` would resolve it (needs root). The proof used here is the equal boot id.
7. Insufficient data: whether the one-thread phase of 2026-11-13 changes the 120-thread rates (section 1.5).
8. Insufficient data: whether the buffers of part A lay on 2 MiB pages. bandwidth.c does not record it. A run of the same kernels with bwx12 records it in "P" rows.
9. Insufficient data: the applied memory speed in the boot of the 8000 MT/s baselines. That boot is over, so the reading cannot be taken any more. The firmware setting of that boot is on record (section 1.5, point 10).
10. Insufficient data: the firmware settings in the boot of the rerun, apart from the memory speed. The two TXREQ settings were set back before the 7200 MT/s reboot test, and the settings list saved after that is equal to the list of the baseline boot in its 604 readable values. No list was saved in the boot of the rerun. A settings list saved in that boot would resolve it (needs root) (section 1.5, point 13).
11. Insufficient data: whether a corrected hardware error record lowers the rate of an interval (hypothesis in section 4.1). The processes of rows L-1 to L-4, R0 and R0b hold 8 intervals to which records can be assigned (all kernels and positions, view added after the numbers were seen). 3 of them are more than 1 GB/s below the same kernel at the same position in the other round of their process (1.96, 3.69 and 10.07 GB/s). The other 5 differ from it by less than 1 GB/s (-0.04 to +0.70 GB/s). Without records the two rounds of the same processes differ by up to 6.24 GB/s. This comparison is not a test. A run that stores the kernel log time of every record beside the interval times would resolve it (needs root).

### Hypotheses (not tested)

- H1, start state. The rate of the load-only loop depends on the work that ran shortly before the launch. What fits: part L (launched 5 s after part A) gave 321.65 to 327.93 GB/s, and control I (idle start, added after the first numbers were seen, not part of the plan fixed before the run) gave 313.78 to 317.60 GB/s. In part A the second round is above the first in 8 of 9 load-only cells. What does not fit: at 8000 MT/s process p2 of row R0 (other binary bwx11, load 85.15 at launch) gave 296.02 to 296.22 GB/s, below p1 (load 0.00) with 302.59 to 303.16 GB/s. The bwx12 rows of the fixed list do not fit either (section 4.2, view by start state): the 5 processes that started 5 s to 25 s after a 120-thread bwx12 process (L-2 p2add, L-3 thp, L-4 st1, L-4 st2, L-4 st3, load 53.98 to 94.23) gave asmread 288.54 to 309.17 GB/s (7 intervals / 5 processes), and the 2 processes that started at a load below 1.0 (L-1 a6456, L-2 p1nop) gave 298.71 to 305.57 GB/s (4 intervals / 2 processes). The two ranges overlap. Inside row L-2, p2add (load 94.23) gave 298.61 and 288.54 GB/s, below p1nop (load 0.00) with 305.57 and 302.90 GB/s. For oldread the order is the opposite at 8000 MT/s: the same 5 processes gave 468.56 to 470.05 GB/s, above the 465.53 to 468.06 GB/s of the 2 processes at a load below 1.0. At 7200 MT/s oldread of part L (461.61 to 464.29 GB/s) was below control I (466.30 to 469.20 GB/s). Also, in part A the first-round process of bw_new read gave 330.09 to 333.25 GB/s in session 1 (idle start), above session 2 (322.67 to 325.26 GB/s) and session 3 (315.55 to 320.89 GB/s), which started 5 s after 120-thread work. Measurement that would confirm or reject it: the like.spec line, alternating between an idle start and a start directly after part A, at least 3 times each, in one boot.
- H2, time since boot. The rate of the load-only loop rises with the time since boot or with the work done since boot. What fits: F72d12 ran 20 s after the first kernel log line of the boot and gave the lowest values. The first process of the rerun started 2 h 9 min 58 s after that line. Limit: F72d12 also differs from control I (added after the first numbers were seen, not part of the plan fixed before the run) in its process list (pr/ttyAMA-1 at 51.6 %CPU, 5 s before the launch, section 4.6). So the time since boot and the start phase of the machine are not separated. Measurement: repeat the idle-start line of control I some hours later in the same boot, and once directly after a reboot (a reboot needs approval).
- H3, memory speed. 7200 MT/s raises the rate of the load-only loop. The rerun cannot separate this from H1, H2 and the boot. Measurement: the like.spec line in several boots per speed (needs reboots and a change of the firmware setting).
- H4, pass counts in part A. An interval with 664 passes has 6 passes on the 64 threads of mesh 0 and 5 passes on the 56 threads of mesh 1 (64 x 6 + 56 x 5 = 664). threads120.csv has no row per thread, so the split is not proven. Measurement: part A with the option --per-thread.
- H5, load values. The high load values at the launches come from the rerun's own earlier processes (section 1.3).

## 7. Files

Every raw file and script that this sheet uses, one line each. R and S are the folders named at the top.

- [Ref1] `S/build_facts.py`: script: builds this sheet and facts.json (records, integrity checks)
- [Ref2] `S/facts_data.py`: script: parsers of the raw files, range and overlap functions
- [Ref3] `S/facts_text.py`: script: text, tables, statistics and verdicts of sections 0 to 3 and 7
- [Ref4] `S/facts_text4.py`: script: text, tables, statistics and verdicts of sections 4 to 6
- [Ref5] `S/stat_k120.py`: existing tool: statistics of a threads120.csv, used here as a cross-check
- [Ref6] `S/stat_bwx.py`: existing tool: statistics of bwx csv files, used here as a cross-check
- [Ref7] `S/baselines-and-rules.txt`: the fixed list of 8000 MT/s baselines and the comparison rules (V1 to V4, F1, F2), written before the run
- [Ref8] `S/review-w1.json`: record of the review that produced the rules (findings F1 and F9 list the differences to the 2026-11-13 procedure). Read by the author, not by the script
- [Ref9] `S/go.sh`: driver script of the rerun: three sessions of parts A, L, C and a fourth C process
- [Ref10] `S/ra.sh`: script of part A: the 120-thread part of run_kernels.sh with the binaries of 2026-11-13
- [Ref11] `S/go2.sh`: script of control I: the part L line twice, each time from an idle machine
- [Ref12] `S/like.spec`: argument line of parts L and I for rx.sh (tag a6456)
- [Ref13] `S/cfwd.spec`: argument line of part C, order oldread, read, asmread
- [Ref14] `S/crev.spec`: argument line of part C, order asmread, read, oldread
- [Ref15] `S/local.sha`: sha256 list of go.sh, ra.sh and the spec files, written at launch
- [Ref16] `S/go2.sha`: sha256 of go2.sh, written at launch
- [Ref17] `S/base8000/partA-A1/threads120.csv`: copy of A1.csv with converted header lines, used only for the cross-check with stat_k120.py
- [Ref18] `S/base8000/partA-A3-onebuf500/threads120.csv`: copy of the three onebuf-ms500 processes of A3.csv with converted header lines, used only for the cross-check
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: runner script of bwx12 processes (parts L, C, I). It writes env.txt, launches.txt and stderr.txt. Read by the author. Check 26 of section 1.4 compares its sha256 with the value that go.sh and go2.sh test on CRB
- [Ref20] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/r0.sh`: run script of row R0. It holds the sha256 of bwx11 (line 8)
- [Ref21] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md`: facts sheet of the investigation of 2026-11-15 (sections "The question", F1, F2). Read by the author
- [Ref22] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: the run script of 2026-11-13 ("whole chip test"). Read by the author. Check 27 of section 1.4 compares its function one() with ra.sh
- [Ref23] `R/go-T72-20261117T221209Z.log`: log of go.sh: Linux command line, governor, huge page setting, 12 state lines
- [Ref24] `R/go2-T72-20261117T222335Z.log`: log of go2.sh: 6 state lines
- [Ref25] `R/k120-T72A1-20261117T221209Z/threads120.csv`: part A, session 1: 24 processes, 72 interval rows
- [Ref26] `R/k120-T72A1-20261117T221209Z/probe.txt`: part A, session 1: boot id, MemTotal, load, sha256 of bw_old, bw_new, ra.sh
- [Ref27] `R/k120-T72A2-20261117T221518Z/threads120.csv`: part A, session 2: 24 processes, 72 interval rows
- [Ref28] `R/k120-T72A2-20261117T221518Z/probe.txt`: part A, session 2: boot id, MemTotal, load, sha256 of bw_old, bw_new, ra.sh
- [Ref29] `R/k120-T72A3-20261117T221827Z/threads120.csv`: part A, session 3: 24 processes, 72 interval rows
- [Ref30] `R/k120-T72A3-20261117T221827Z/probe.txt`: part A, session 3: boot id, MemTotal, load, sha256 of bw_old, bw_new, ra.sh
- [Ref31] `R/w120-T72L1-20261117T221329Z/a6456.csv`: part L, T72L1: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref32] `R/w120-T72L1-20261117T221329Z/env.txt`: part L, T72L1: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref33] `R/w120-T72L1-20261117T221329Z/launches.txt`: part L, T72L1: launch line with load and arguments, rc line
- [Ref34] `R/w120-T72L1-20261117T221329Z/stderr.txt`: part L, T72L1: error output of bwx12
- [Ref35] `R/w120-T72L2-20261117T221638Z/a6456.csv`: part L, T72L2: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref36] `R/w120-T72L2-20261117T221638Z/env.txt`: part L, T72L2: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref37] `R/w120-T72L2-20261117T221638Z/launches.txt`: part L, T72L2: launch line with load and arguments, rc line
- [Ref38] `R/w120-T72L2-20261117T221638Z/stderr.txt`: part L, T72L2: error output of bwx12
- [Ref39] `R/w120-T72L3-20261117T221947Z/a6456.csv`: part L, T72L3: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref40] `R/w120-T72L3-20261117T221947Z/env.txt`: part L, T72L3: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref41] `R/w120-T72L3-20261117T221947Z/launches.txt`: part L, T72L3: launch line with load and arguments, rc line
- [Ref42] `R/w120-T72L3-20261117T221947Z/stderr.txt`: part L, T72L3: error output of bwx12
- [Ref43] `R/w120-T72C1-20261117T221436Z/cfwd.csv`: part C, T72C1: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref44] `R/w120-T72C1-20261117T221436Z/env.txt`: part C, T72C1: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref45] `R/w120-T72C1-20261117T221436Z/launches.txt`: part C, T72C1: launch line with load and arguments, rc line
- [Ref46] `R/w120-T72C1-20261117T221436Z/stderr.txt`: part C, T72C1: error output of bwx12
- [Ref47] `R/w120-T72C2-20261117T221745Z/crev.csv`: part C, T72C2: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref48] `R/w120-T72C2-20261117T221745Z/env.txt`: part C, T72C2: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref49] `R/w120-T72C2-20261117T221745Z/launches.txt`: part C, T72C2: launch line with load and arguments, rc line
- [Ref50] `R/w120-T72C2-20261117T221745Z/stderr.txt`: part C, T72C2: error output of bwx12
- [Ref51] `R/w120-T72C3-20261117T222054Z/cfwd.csv`: part C, T72C3: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref52] `R/w120-T72C3-20261117T222054Z/env.txt`: part C, T72C3: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref53] `R/w120-T72C3-20261117T222054Z/launches.txt`: part C, T72C3: launch line with load and arguments, rc line
- [Ref54] `R/w120-T72C3-20261117T222054Z/stderr.txt`: part C, T72C3: error output of bwx12
- [Ref55] `R/w120-T72C4-20261117T222136Z/crev.csv`: part C, T72C4: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref56] `R/w120-T72C4-20261117T222136Z/env.txt`: part C, T72C4: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref57] `R/w120-T72C4-20261117T222136Z/launches.txt`: part C, T72C4: launch line with load and arguments, rc line
- [Ref58] `R/w120-T72C4-20261117T222136Z/stderr.txt`: part C, T72C4: error output of bwx12
- [Ref59] `R/w120-T72I1-20261117T222700Z/a6456.csv`: control I, T72I1: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref60] `R/w120-T72I1-20261117T222700Z/env.txt`: control I, T72I1: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref61] `R/w120-T72I1-20261117T222700Z/launches.txt`: control I, T72I1: launch line with load and arguments, rc line
- [Ref62] `R/w120-T72I1-20261117T222700Z/stderr.txt`: control I, T72I1: error output of bwx12
- [Ref63] `R/w120-T72I2-20261117T223227Z/a6456.csv`: control I, T72I2: rows per interval (I), per thread (T), page state (P), counters (C)
- [Ref64] `R/w120-T72I2-20261117T223227Z/env.txt`: control I, T72I2: start time, Linux release, load, busiest processes, sha256 of bwx12
- [Ref65] `R/w120-T72I2-20261117T223227Z/launches.txt`: control I, T72I2: launch line with load and arguments, rc line
- [Ref66] `R/w120-T72I2-20261117T223227Z/stderr.txt`: control I, T72I2: error output of bwx12
- [Ref67] `R/kernels-20261113T181222Z/threads120.csv`: row A-1: the original whole-chip test of 2026-11-13, 24 processes
- [Ref68] `R/kernels-20261113T181222Z/probe.txt`: row A-1: sha256 of bw_old and bw_new, times of the 2026-11-13 run
- [Ref69] `R/kernels-20261113T181222Z/one-thread.csv`: one-thread part of the 2026-11-13 run (only its process count and times are used)
- [Ref70] `R/partA-20261113T205055Z/A1.csv`: row A-2: 12 processes of 2026-11-13 20:50 UTC
- [Ref71] `R/partA-20261113T205055Z/A3.csv`: row A-3: tags onebuf-ms500-1, -2, -3 (bw_old read)
- [Ref72] `R/partA-20261113T205055Z/env.txt`: rows A-2, A-3: sha256 of bw_old and bw_new
- [Ref73] `R/w120-R8-20261117T020549Z/a6456.csv`: row L-1: bwx csv of process a6456
- [Ref74] `R/w120-R8-20261117T020549Z/env.txt`: row L-1: start time, load, process list, sha256 of the binary
- [Ref75] `R/w120-R8-20261117T020549Z/launches.txt`: row L-1: launch lines with load and arguments, rc lines
- [Ref76] `R/w120-R8-20261117T020549Z/stderr.txt`: row L-1: error output
- [Ref77] `R/w120-R1-20261115T185140Z/p1nop.csv`: row L-2: bwx csv of process p1nop
- [Ref78] `R/w120-R1-20261115T185140Z/p2add.csv`: row L-2: bwx csv of process p2add
- [Ref79] `R/w120-R1-20261115T185140Z/env.txt`: row L-2: start time, load, process list, sha256 of the binary
- [Ref80] `R/w120-R1-20261115T185140Z/launches.txt`: row L-2: launch lines with load and arguments, rc lines
- [Ref81] `R/w120-R1-20261115T185140Z/stderr.txt`: row L-2: error output
- [Ref82] `R/w120-R5-20261115T203152Z/thp.csv`: row L-3: bwx csv of process thp
- [Ref83] `R/w120-R5-20261115T203152Z/env.txt`: row L-3: start time, load, process list, sha256 of the binary
- [Ref84] `R/w120-R5-20261115T203152Z/launches.txt`: row L-3: launch lines with load and arguments, rc lines
- [Ref85] `R/w120-R5-20261115T203152Z/stderr.txt`: row L-3: error output
- [Ref86] `R/w120-R6-20261115T203438Z/st1.csv`: row L-4: bwx csv of process st1
- [Ref87] `R/w120-R6-20261115T203438Z/st2.csv`: row L-4: bwx csv of process st2
- [Ref88] `R/w120-R6-20261115T203438Z/st3.csv`: row L-4: bwx csv of process st3
- [Ref89] `R/w120-R6-20261115T203438Z/env.txt`: row L-4: start time, load, process list, sha256 of the binary
- [Ref90] `R/w120-R6-20261115T203438Z/launches.txt`: row L-4: launch lines with load and arguments, rc lines
- [Ref91] `R/w120-R6-20261115T203438Z/stderr.txt`: row L-4: error output
- [Ref92] `R/w120-R0-20261115T165608Z/p1.csv`: row R0: bwx csv of process p1
- [Ref93] `R/w120-R0-20261115T165608Z/p2.csv`: row R0: bwx csv of process p2
- [Ref94] `R/w120-R0-20261115T165608Z/env.txt`: row R0: start time, load, process list (9 lines, no sha256: the sha256 of bwx11 is in r0.sh)
- [Ref95] `R/w120-R0-20261115T165608Z/launches.txt`: row R0: launch lines with load and arguments, rc lines
- [Ref96] `R/w120-R0-20261115T165608Z/stderr.txt`: row R0: error output
- [Ref97] `R/w120-R0b-20261115T170342Z/cA.csv`: row R0b: bwx csv of process cA
- [Ref98] `R/w120-R0b-20261115T170342Z/cB.csv`: row R0b: bwx csv of process cB
- [Ref99] `R/w120-R0b-20261115T170342Z/cC.csv`: row R0b: bwx csv of process cC
- [Ref100] `R/w120-R0b-20261115T170342Z/env.txt`: row R0b: start time, load, process list, sha256 of the binary
- [Ref101] `R/w120-R0b-20261115T170342Z/launches.txt`: row R0b: launch lines with load and arguments, rc lines
- [Ref102] `R/w120-R0b-20261115T170342Z/stderr.txt`: row R0b: error output
- [Ref103] `R/w120-X2d12-20261117T040922Z/a6456.csv`: row X2d12: bwx csv of process a6456
- [Ref104] `R/w120-X2d12-20261117T040922Z/env.txt`: row X2d12: start time, load, process list, sha256 of the binary
- [Ref105] `R/w120-X2d12-20261117T040922Z/launches.txt`: row X2d12: launch lines with load and arguments, rc lines
- [Ref106] `R/w120-X2d12-20261117T040922Z/stderr.txt`: row X2d12: error output
- [Ref107] `R/w120-X1d10-20261117T034916Z/a6456.csv`: row X1d10: bwx csv of process a6456
- [Ref108] `R/w120-X1d10-20261117T034916Z/env.txt`: row X1d10: start time, load, process list, sha256 of the binary
- [Ref109] `R/w120-X1d10-20261117T034916Z/launches.txt`: row X1d10: launch lines with load and arguments, rc lines
- [Ref110] `R/w120-X1d10-20261117T034916Z/stderr.txt`: row X1d10: error output
- [Ref111] `R/w120-X1d10b-20261117T040407Z/a6456.csv`: row X1d10b: bwx csv of process a6456
- [Ref112] `R/w120-X1d10b-20261117T040407Z/env.txt`: row X1d10b: start time, load, process list, sha256 of the binary
- [Ref113] `R/w120-X1d10b-20261117T040407Z/launches.txt`: row X1d10b: launch lines with load and arguments, rc lines
- [Ref114] `R/w120-X1d10b-20261117T040407Z/stderr.txt`: row X1d10b: error output
- [Ref115] `R/w120-BASEd10-20261117T041738Z/a6456.csv`: row BASEd10: bwx csv of process a6456
- [Ref116] `R/w120-BASEd10-20261117T041738Z/env.txt`: row BASEd10: start time, load, process list, sha256 of the binary
- [Ref117] `R/w120-BASEd10-20261117T041738Z/launches.txt`: row BASEd10: launch lines with load and arguments, rc lines
- [Ref118] `R/w120-BASEd10-20261117T041738Z/stderr.txt`: row BASEd10: error output
- [Ref119] `R/w120-w120-F72d12-20261117T200231Z/a6456.csv`: row F72d12: bwx csv of process a6456
- [Ref120] `R/w120-w120-F72d12-20261117T200231Z/env.txt`: row F72d12: start time, load, process list, sha256 of the binary
- [Ref121] `R/w120-w120-F72d12-20261117T200231Z/launches.txt`: row F72d12: launch lines with load and arguments, rc lines
- [Ref122] `R/w120-w120-F72d12-20261117T200231Z/stderr.txt`: row F72d12: error output
- [Ref123] `R/B7-20261113T232859Z/B7.csv`: row B7a: csv of runner bwx, processes with tag common-6000-*
- [Ref124] `R/B7-20261113T232859Z/env.txt`: row B7a: sha256 of runner bwx
- [Ref125] `R/B7-20261114T024352Z/B7.csv`: row B7b: csv of runner bwx, processes with tag common-6000-*
- [Ref126] `R/B7-20261114T024352Z/env.txt`: row B7b: sha256 of runner bwx
- [Ref127] `R/C3-20261114T022708Z/C3.csv`: row C3a: csv of runner bwx, processes with tag common-6000-*
- [Ref128] `R/C3-20261114T022708Z/env.txt`: row C3a: sha256 of runner bwx
- [Ref129] `R/C3-20261114T054116Z/C3.csv`: row C3b: csv of runner bwx, processes with tag common-6000-*
- [Ref130] `R/C3-20261114T054116Z/env.txt`: row C3b: sha256 of runner bwx
- [Ref131] `R/B5-20261114T011723Z/B5.csv`: rows B5a and B5a-rev: csv of runner bwx, processes with tag b5-fwd-* and b5-rev-*
- [Ref132] `R/B5-20261114T011723Z/env.txt`: rows B5a and B5a-rev: sha256 of runner bwx
- [Ref133] `R/B5-20261114T043213Z/B5.csv`: rows B5b and B5b-rev: csv of runner bwx, processes with tag b5-fwd-* and b5-rev-*
- [Ref134] `R/B5-20261114T043213Z/env.txt`: rows B5b and B5b-rev: sha256 of runner bwx
- [Ref135] `R/dimm7200-20261117/try6.txt`: record of boot 3bfc57a1: 12 modules, 12 x "Configured Memory Speed: 7200 MT/s", MemTotal
- [Ref136] `R/dimm7200-20261117/gaps.txt`: first and last kernel log time of the boots of the 7200 MT/s reboot test (row 0 is the boot of the rerun), the field hwerr of row 0, and the time line and the process list after the rows (lines 8 to 12)
- [Ref137] `R/dimm7200-20261117/boots.txt`: boot list of the journal: row 0 holds the boot id of try6.txt, which links gaps.txt to this boot
- [Ref138] `/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md`: DIMM report: boot history with module counts (section 3), change to 7200 MT/s (section 6.3)
- [Ref139] `R/dimm-check-20261117/h-5.txt`: saved journal of the boot of 2026-11-09: Linux start, module count line, error records
- [Ref140] `R/dimm-check-20261117/k-5.txt`: saved kernel log of the same boot: its last line and the line "Memory: ... available" (line 762)
- [Ref141] `R/uefisettings-20261117/questions.json`: firmware settings list (file time 2026-11-17 02:09 UTC): the entry counts and the settings "DIMM Frequency", "TXREQ Max" and "TXREQ Min"
- [Ref142] external source: Linux kernel documentation, Documentation/admin-guide/pm/cpufreq.rst (scaling_cur_freq is given in kHz)
- [Ref143] external source: Linux manual page proc(5), entry /proc/loadavg (meaning of the load average fields)
- [Ref144] `R/partA-20261113T205055Z/A2.csv`: second file of the run partA-20261113T205055Z: only the launch time of its first process is used (end of the time window of row A-2)
- [Ref145] `R/fwtest-20261117/pre/when.txt`: settings saved in the 2026-11-09 boot before the firmware test: time of the save
- [Ref146] `R/fwtest-20261117/pre/cmdline.txt`: same save: Linux kernel command line
- [Ref147] `R/fwtest-20261117/pre/gov.txt`: same save: two lines, "128 performance" and "2800000" (the file does not name them)
- [Ref148] `R/fwtest-20261117/pre/thp.txt`: same save: transparent_hugepage/enabled
- [Ref149] external source: manual page ps(1) of procps-ng, entry "%cpu" (alias pcpu): the CPU time used, divided by the time the process has been running. The ps version on CRB was not checked (no ssh in this task)
- [Ref150] `R/partA-20261113T204939Z/env.txt`: run folder of 2026-11-13 20:49 UTC that ended 8 s before the first process of row A-2: start line and end line
- [Ref151] `R/partA-20261113T204939Z/A5.csv`: same folder: 4 one-thread processes (header lines only)
- [Ref152] `R/partA-20261113T204939Z/A6.csv`: same folder: 16 one-thread processes (header lines only)
- [Ref153] `R/partA-20261113T204939Z/launches.txt`: same folder: one line per process
- [Ref154] `R/dimm-check-20261117/h-1.txt`: saved journal of the 10-module boot of 2026-11-17 04:17 UTC: its first two lines
- [Ref155] `R/dimm-check-20261117/k-1.txt`: saved kernel log of the same 10-module boot: the line "Memory: ... available"
- [Ref156] `R/dimm7200-20261117/dmi17-7200.txt`: module list (output of dmidecode, type 17) saved in the boot of the rerun
- [Ref157] `R/fwtest-20261117/x1/set.txt`: reply of the firmware settings tool: change of "TXREQ Min" for another test
- [Ref158] `R/fwtest-20261117/x2/set.txt`: reply of the firmware settings tool: change of "TXREQ Max" for another test
- [Ref159] `R/fwtest-20261117/revert/set.txt`: replies of the firmware settings tool: both TXREQ settings set back and read back
- [Ref160] `R/fwtest-20261117/revert/questions.json`: firmware settings list saved after the set-back (file time 2026-11-17 04:17:38 UTC)
- [Ref161] `R/fwtest-20261117/x1/post/questions.json`: firmware settings list saved after the first change (file time 2026-11-17 03:48:37 UTC)
- [Ref162] `R/dimm7200-20261117/set.txt`: reply of the firmware settings tool: "DIMM Frequency" set to 7200 MT/s
- [Ref163] `R/dimm7200-20261117/setting-final.txt`: last reading of the memory speed setting in the boot of the rerun (one line)

Output files of this sheet: `S/FACTS.md` (this file) and `S/facts.json` (every interval as one record, plus "meta" and "verdicts").
