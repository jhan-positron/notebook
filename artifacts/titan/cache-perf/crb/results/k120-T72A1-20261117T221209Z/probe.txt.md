# `probe.txt` explained: part A, session 1

## Short version

This file is the machine record of part A, session 1 of the whole-chip rerun at 7200 MT/s of 2026-11-17.
The script `ra.sh` wrote it: the state of the machine before the first process, the sha256 values of the two binaries, and the load after the last process.

## This file

- File: `probe.txt` in this folder (`crb/results/k120-T72A1-20261117T221209Z`).
- Size: 15 lines, 796 bytes. sha256 when this page was built: `7ea8b927f1c7578ec3aec2a0eb82a2a20d644c2d6702e60a99e1b85da94a205a`.
- Written by: `ra.sh` (the script of part A), before the first process and after the last one.
- Step of the run: part A, session 1, folder tag `T72A1`.

## The whole file (copied from the file by a script)

```text
 1  ## host=ubuntu utc=2026-11-17T22:12:14Z load_before=0.07 0.02 0.00 logins=0 name=T72A1
 2  ## boot_id=3bfc57a1-e235-4fe5-8c09-a94642f9b60b MemTotal: 395392808 kB runnable=2
 3  ## kernel=7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 thp=[always] madvise never
 4  ## busiest processes (pcpu user comm):
 5  %CPU USER     COMMAND
 6   0.3 jhan     systemd
 7   0.1 root     pr/ttyAMA-1
 8   0.0 root     systemd
 9   0.0 root     rcu_preempt
10   0.0 root     kworker/u512:0-bnxt_pf_wq
11  ## sha256:
12  e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
13  fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
14  6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254  /home/jhan/cache-perf/w120-7200-20261117/ra.sh
15  ## load_after=80.50 24.65 8.59 utc=2026-11-17T22:13:29Z MemTotal: 395392808 kB
```

The sections below explain the file type. The same text stands in the companion of every file of this type.

## The file type in short

Each `probe.txt` of part A is a record of the machine state that the script `ra.sh` wrote around the 24 benchmark processes of one session. Lines 1 to 14 were written directly before the first process, and line 15 after the last one. The file holds the time, the load, the boot id, the memory size and the checksums of the two binaries and of the script, and it holds no measured rate.

## What this file is

Path names used in this text:

- `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`
- `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`
- `K13` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13`

The files of this type:

| Session | File | Lines | Size |
|---|---|---|---|
| 1 | `R/k120-T72A1-20261117T221209Z/probe.txt` [Ref1] | 15 | 796 bytes |
| 2 | `R/k120-T72A2-20261117T221518Z/probe.txt` [Ref2] | 15 | 801 bytes |
| 3 | `R/k120-T72A3-20261117T221827Z/probe.txt` [Ref3] | 15 | 802 bytes |

This text holds for all three files. Each file has the same 15 lines in the same order, with the same number of words per line.

Who writes the file, and when [Ref4]:

- `ra.sh` (the script of part A) writes it. `go.sh` (the driver script of the rerun) starts `ra.sh` once per session [Ref5].
- The file is in the same folder as `threads120.csv`, the result file of the same session.
- Before it writes anything, `ra.sh` does six things:
    1. It restarts itself under the tool `taskset`. From then on the script and all its processes may use CPUs 0-119 only.
    2. It stops when the marker file `/tmp/positron-perf.RUNNING` exists. It repeats this test before it writes the file and before every process.
    3. It checks the checksums of `bw_old` and `bw_new` against two fixed values. It stops when one differs.
    4. It creates the result folder. The time in the folder name is taken at this moment.
    5. It waits until at most 2 tasks are runnable. It tries up to 40 times, 1 s apart. It stops the run when the count stays above 2.
    6. It sleeps 5 s.
- Then one block of commands writes lines 1 to 14 in one step.
- Then the 24 processes run. They write `threads120.csv`.
- Then one more command appends line 15.
- `ra.sh` does not reach this command when it stops before the last process has ended. It stops when the marker file exists before a process, or when a process ends with an error status (`set -e`: the script stops at the first failed command). Then the file holds 14 lines. Each of the three files holds line 15.

The whole session 1 file, lines 1 to 15 [Ref1]:

```
## host=ubuntu utc=2026-11-17T22:12:14Z load_before=0.07 0.02 0.00 logins=0 name=T72A1
## boot_id=3bfc57a1-e235-4fe5-8c09-a94642f9b60b MemTotal: 395392808 kB runnable=2
## kernel=7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858 thp=[always] madvise never
## busiest processes (pcpu user comm):
%CPU USER     COMMAND
 0.3 jhan     systemd
 0.1 root     pr/ttyAMA-1
 0.0 root     systemd
 0.0 root     rcu_preempt
 0.0 root     kworker/u512:0-bnxt_pf_wq
## sha256:
e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254  /home/jhan/cache-perf/w120-7200-20261117/ra.sh
## load_after=80.50 24.65 8.59 utc=2026-11-17T22:13:29Z MemTotal: 395392808 kB
```

## Line kinds

| Line | Kind | How to recognise it | What it holds |
|---|---|---|---|
| 1 | Start line | starts with `## host=` | host name, date and time, load averages, logins, name of the session |
| 2 | Boot line | starts with `## boot_id=` | boot id, memory size, count of runnable tasks |
| 3 | System line | starts with `## kernel=` | Linux kernel release, huge page setting of the system |
| 4 | Title of the process list | starts with `## busiest processes` | the names of the three columns that the script asked for |
| 5 | Column header of the process list | starts with `%CPU` | printed by the tool `ps` |
| 6 to 10 | Process rows | a number with one decimal, a user name, a command name | the 5 processes with the highest %CPU |
| 11 | Title of the checksums | the text `## sha256:` | nothing else |
| 12 to 14 | Checksum lines | 64 hexadecimal digits, two spaces, a file name | sha256 checksums of `bw_old`, `bw_new` and `ra.sh` |
| 15 | End line | starts with `## load_after=` | load averages, date and time, memory size after the last process |

Lines that start with `##` come from `echo` commands of `ra.sh`. The other lines are the output of the tools `ps` and `sha256sum` [Ref4].

## Columns

The file is not a table. So this section explains the fields of every line. The example values are those of the session 1 file [Ref1]. The command behind each field is in `ra.sh` [Ref4].

### Line 1: start line

| Field | Example | Unit | Meaning |
|---|---|---|---|
| `host=` | `ubuntu` | none | The host name of the machine (output of `hostname`). |
| `utc=` | `2026-11-17T22:12:14Z` | date and time, UTC | The time at which lines 1 to 14 were written. |
| `load_before=` (3 numbers) | `0.07 0.02 0.00` | tasks | The load averages over the last 1, 5 and 15 minutes. They are the first three fields of the file `/proc/loadavg`. |
| `logins=` | `0` | logins | The number of lines that the tool `who` prints. `who` lists the users who are logged in. |
| `name=` | `T72A1` | none | The first argument of `ra.sh`. `go.sh` passes T72A1, T72A2 or T72A3. The same name is part of the folder name. |

### Line 2: boot line

| Field | Example | Unit | Meaning |
|---|---|---|---|
| `boot_id=` | `3bfc57a1-e235-4fe5-8c09-a94642f9b60b` | none | The content of the file `/proc/sys/kernel/random/boot_id`. Equal boot ids mean the same boot. |
| `MemTotal:` | `395392808 kB` | kB (1 kB = 1024 bytes) | The line `MemTotal` of the file `/proc/meminfo`, with each run of spaces reduced to one space. It is the usable memory that Linux reports. |
| `runnable=` | `2` | tasks | The last count of runnable tasks that the wait loop of `ra.sh` read. It is the number before the slash in the fourth field of `/proc/loadavg`. |

Notes on line 2:

- The three files hold the same boot id. `go.sh` holds the same value. Its comment calls it the boot in which 12 memory modules at 7200 MT/s were recorded. `go.sh` stops when the boot id of the machine differs [Ref5].
- `go.sh` tests the boot id once, at its start, before session 1. At the same place it stops when MemTotal is below 395000000 kB [Ref5]. It does not repeat the two tests before sessions 2 and 3.
- The facts sheet states that the value 395392808 kB belongs to a boot with 12 memory modules. It gives the size as 377.08 GiB [Ref9].
- The file does not hold the memory speed. The speed was not read during the rerun. Reading it needs root. The proof for 7200 MT/s is the boot id: a record of the same boot, written at 20:02:21 UTC, shows 12 modules at 7200 MT/s. The facts sheet adds an assumption that was not measured: the speed does not change inside one boot [Ref9].
- `runnable` was not read at the time of line 1. The script read it, then slept 5 s, then wrote lines 1 to 14. So the value is from at least 5 s before the time in line 1.
- The count of runnable tasks at the launch of the first process is not recorded [Ref8].

### Line 3: system line

| Field | Example | Unit | Meaning |
|---|---|---|---|
| `kernel=` | `7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858` | none | The release of the Linux kernel (output of `uname -r`). This is the operating system kernel. It is not a read kernel. |
| `thp=` (3 words) | `[always] madvise never` | none | The content of the file `/sys/kernel/mm/transparent_hugepage/enabled`. The word in brackets is the active setting [Ref9]. |

Note on `thp`: `threads120.csv` holds the text `thp=madvise` in its formula lines. That text comes from the benchmark binary. It says that the binary asked for huge pages. Line 3 of `probe.txt` is the setting of the whole system. The two texts do not contradict each other.

### Lines 4 to 10: process list

- Line 4 is a title. It names the three columns that the script asked `ps` for: `pcpu`, `user`, `comm`.
- Line 5 is the column header that `ps` prints for them: `%CPU`, `USER`, `COMMAND`.
- Lines 6 to 10 are the 5 processes with the highest %CPU of all processes of the machine, highest first.
- The script takes the first 6 lines of the `ps` output. So the list never has more than 5 processes.

| No. | Name | Example (line 6) | Unit | Meaning |
|---|---|---|---|---|
| 1 | `%CPU` | `0.3` | percent | The CPU time that the process has used, divided by the time since the process started [Ref9]. |
| 2 | `USER` | `jhan` | none | The user name that the process runs under. |
| 3 | `COMMAND` | `systemd` | none | The name of the command. |

Notes on the process list:

- %CPU is an average over the life of a process. It is not the use at the moment of the reading [Ref9]. So the list would show a new busy process. It cannot show a short busy phase of a process that has run since the boot.
- The highest value is 0.3 % in the session 1 file and 0.1 % in the files of sessions 2 and 3.

### Lines 11 to 14: checksums

Line 11 is a title. Lines 12 to 14 are output of the tool `sha256sum`: the checksum, two spaces, the file name as the script gave it.

| Line | File | Meaning |
|---|---|---|
| 12 | `bw_old` | The binary with the old read kernel. The script reads it from the folder `~/cache-perf/scratch-kernels-20261113` on CRB. |
| 13 | `bw_new` | The binary with the new read kernel, from the same folder. |
| 14 | `/home/jhan/cache-perf/w120-7200-20261117/ra.sh` | The script itself, under the path with which it was started on CRB. |

What these lines prove:

- Lines 12 to 14 are the same in all three files.
- Lines 12 and 13 hold the two values that `ra.sh` itself checks at its start, before it creates the result folder [Ref4]. They are also the values that the test of 2026-11-13 recorded for `bw_old` and `bw_new` [Ref6]. That test is the 8000 MT/s baseline A-1 [Ref10]. So the rerun at 7200 MT/s used the same two binaries as the test at 8000 MT/s.
- Line 14 is equal to the sha256 checksum of the local file `S/ra.sh` (6d67715e...). So the local `S/ra.sh` is the text that ran on CRB.
- The files `bw_old` and `bw_new` are not in the local folders. So their checksums cannot be computed again here. They are known only from records such as the `probe.txt` files and the fixed values in `ra.sh`.

How the checksums lead to the source files [Ref6] [Ref7]:

- The script `run_kernels.sh` of 2026-11-13 builds `bw_old` from `bandwidth.orig.c` and `bw_new` from `bandwidth.c` at every start. Then it records the checksums of the sources and of the binaries.
- Its run of 18:12:22 UTC was the timed run (mode `all`). It is the baseline A-1. It recorded `bandwidth.orig.c` as 61228754... and `bandwidth.c` as c1406e02...
- Its run of 18:32:18 UTC built the binaries and timed nothing (mode `probe`). It recorded `bandwidth.orig.c` as 61228754... and `bandwidth.c` as f1985072...
- A third record, of a run of 18:12:10 UTC in mode `probe`, holds the same checksums as the run of 18:12:22.
- All three records hold the same two binary checksums: e8fc0205... for `bw_old` and fd7c14df... for `bw_new`.
- The local file `K13/bandwidth.orig.c` has the checksum 61228754... The local file `K13/bandwidth.c` has the checksum f1985072...
- So the local `K13/bandwidth.c` is the text of the 18:32:18 run. It is not the text of the timed run of 18:12:22. Both texts gave a `bw_new` with the same checksum. So the machine code is not in doubt.
- The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref11]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.

### Line 15: end line

| Field | Example | Unit | Meaning |
|---|---|---|---|
| `load_after=` (3 numbers) | `80.50 24.65 8.59` | tasks | The load averages over the last 1, 5 and 15 minutes, read after the last of the 24 processes ended. |
| `utc=` | `2026-11-17T22:13:29Z` | date and time, UTC | The time at which line 15 was written. |
| `MemTotal:` | `395392808 kB` | kB | The same reading as in line 2, taken again. |

Times that follow from lines 1 and 15, and from the folder names:

| Session | Time in the folder name | Time in line 1 | Time in line 15 | Line 1 minus folder name | Line 15 minus line 1 |
|---|---|---|---|---|---|
| 1 | 22:12:09 | 22:12:14 | 22:13:29 | 5 s | 75 s |
| 2 | 22:15:18 | 22:15:23 | 22:16:38 | 5 s | 75 s |
| 3 | 22:18:27 | 22:18:32 | 22:19:47 | 5 s | 75 s |

- The 24 processes of a session took 75 s together, at a resolution of 1 s.
- Line 1 was written 5 s after the folder was named, at a resolution of 1 s. The fixed sleep takes 5 s. One more try of the wait loop adds 1 s. So the wait loop ended at its first try in all three sessions.

Load values of the three files:

| Session | `load_before` (1 / 5 / 15 min) | `runnable` | `load_after` (1 / 5 / 15 min) | Highest %CPU of the list |
|---|---|---|---|---|
| 1 | 0.07 / 0.02 / 0.00 | 2 | 80.50 / 24.65 / 8.59 | 0.3 % |
| 2 | 98.64 / 50.08 / 19.76 | 2 | 113.61 / 65.47 / 27.49 | 0.1 % |
| 3 | 102.96 / 77.21 / 36.02 | 2 | 111.98 / 85.23 / 41.99 | 0.1 % |

- Sessions 2 and 3 started with a 1-minute load average near 100. The wait loop had counted only 2 runnable tasks at least 5 s earlier.
- The load average is an average over past minutes. Hypothesis of the facts sheet: the high values come from the 120-thread processes of the rerun that ended shortly before [Ref9]. The facts sheet names the check that would confirm or reject it: sample `/proc/loadavg` and the list of running processes once per second between two steps. This check was not done [Ref9].

## Old read kernel and new read kernel in this file

- The file holds no rate and no row per kernel.
- It names the two binaries. Line 12 is `bw_old`, the binary with the old read kernel. Line 13 is `bw_new`, the binary with the new read kernel.
- The machine state of the file holds for both kernels alike. `ra.sh` writes one `probe.txt` per session. It does not write one per process.
- The load directly before each single process is not in this file. It is the field `load` of the process header lines of `threads120.csv`.

## Which code reads this file

`S/facts_data.py`, function `read_probe` [Ref8]:

- It reads the whole file as one text. It finds the fields with regular expressions.
- Line 1: it keeps the time, the three load averages, the logins and the name. It does not keep the host name.
- Line 2: it keeps the boot id, MemTotal and the count of runnable tasks.
- Line 3: it keeps the Linux kernel release and the huge page setting.
- Lines 6 to 10: it keeps only the highest %CPU value.
- Lines 12 to 14: it keeps the three checksums under the names `bw_old`, `bw_new` and `ra.sh`.
- Line 15: it keeps the three load averages, the time and MemTotal.

`S/build_facts.py` calls `read_probe` for the three files. The scripts of the facts sheet use the values in this way [Ref8]:

- The checksum of `bw_old` or `bw_new` goes into the field `binary_sha256` of every record of part A of the rerun in `facts.json` (the data file of the facts sheet). The part A records of the 8000 MT/s baselines take this field from the `probe.txt` of the test of 2026-11-13.
- The time of line 15 is taken as the end of part A of a session.
- The checks of the facts sheet test these values. The boot id, the two MemTotal values and the Linux kernel release must be equal to the other records of the boot. The logins must be 0. The count of runnable tasks must not be above the limit of `ra.sh`. The checksums must be equal to the records of 2026-11-13 and to the local `S/ra.sh`.
- The tables of the facts sheet print the load averages of lines 1 and 15 and the highest %CPU [Ref9].

Other scripts:

- `S/stat_k120.py` (quick statistics of `threads120.csv`) does not read this file.
- `S/make_report.py` (the script that builds the report page) does not open this file. Its part A values come from `facts.json` and from `threads120.csv`.
- No value of this file enters a rate. The file serves to prove the conditions of the run: same boot, same binaries, same script, and the load at the start and at the end.

<details>
<summary>Words used here</summary>

The entries marked (facts sheet) are copied word for word from the word list of the facts sheet `S/FACTS.md` [Ref9]. One exception: the entry "Read kernel" says "On this page" where the facts sheet says "In this sheet".

- **CRB** (facts sheet): the Arm reference server under test. It has 128 CPUs.
- **MT/s** (facts sheet): million transfers per second, the unit of memory speed.
- **Memory module** (facts sheet): one DIMM. CRB has 12 slots.
- **Read kernel** (facts sheet): the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel** (facts sheet): portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel** (facts sheet): NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **bandwidth.c, bw_old, bw_new** (facts sheet): the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx** (facts sheet): later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Session** (facts sheet): one pass of go.sh through part A, part L and part C.
- **Part A** (facts sheet): the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Load average** (facts sheet, without its reference mark): the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). "Load at launch" is the 1-minute value read directly before a process starts. The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU** (facts sheet, without its reference mark): the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **pr/ttyAMA-1** (facts sheet): a Linux kernel thread in the process lists. By its name it prints kernel messages to the serial console ttyAMA. This meaning was not checked on CRB.
- **Boot id** (facts sheet): a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal** (facts sheet): the usable memory that Linux reports, in kB.
- **Marker file** (facts sheet): `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **Rerun**: the read test with 120 threads of 2026-11-17, run by `go.sh` at a memory speed of 7200 MT/s. The earlier runs that it is compared with had a memory speed of 8000 MT/s.
- **Baseline A-1**: the 120-thread part of the test of 2026-11-13, run by `run_kernels.sh` at 8000 MT/s. Part A repeats it. A-1 is its name in the list of baselines that was fixed before the rerun.
- **GiB**: 2^30 bytes.
- **UTC**: Coordinated Universal Time, the time zone of every time in the file and in the folder names.
- **sha256 checksum**: a number of 64 hexadecimal digits that the tool `sha256sum` computes from the bytes of a file. Two files with the same checksum are taken as the same file.
- **Huge pages, thp**: memory pages of 2 MiB that Linux can use in place of the small standard pages. "thp" stands for transparent huge pages, the Linux feature that provides them without a change of the program.
- **Runnable task**: a process or thread that is running or is ready to run on a CPU.
- **ps, who, uname, hostname, sha256sum**: standard Linux tools. `ps` lists processes. `who` lists the users who are logged in. `uname -r` prints the release of the Linux kernel. `hostname` prints the name of the machine. `sha256sum` prints checksums.
- **ra.sh**: the script of part A. **go.sh**: the driver script of the rerun. It runs 3 sessions.
- **run_kernels.sh**: the script of the test of 2026-11-13. It built the two binaries and ran the first part A.
- **threads120.csv**: the result file of part A. It holds the rates of the 24 processes of a session.
- **facts.json, FACTS.md**: the data file and the text of the facts sheet of the rerun. `build_facts.py` writes both from the raw result files.
- **facts_data.py**: the file with the functions that read the raw result files for the facts sheet. `build_facts.py` uses these functions.

</details>

## References

- [Ref1] `R/k120-T72A1-20261117T221209Z/probe.txt`: session 1 file (first instance), lines 1 to 15.
- [Ref2] `R/k120-T72A2-20261117T221518Z/probe.txt`: session 2 file, lines 1 to 15.
- [Ref3] `R/k120-T72A3-20261117T221827Z/probe.txt`: session 3 file (last instance), lines 1 to 15.
- [Ref4] `S/ra.sh`: line 8 (`set -e`), line 9 (restart under `taskset`), lines 11 to 13, 29 and 40 (test of the marker file), lines 14 to 20 (checksum test of the two binaries), lines 21 to 23 (folder name and folder), line 24 (function `load`), lines 26 to 28 (wait loop and sleep), lines 30 to 36 (the block that writes lines 1 to 14), line 49 (the command that writes line 15).
- [Ref5] `S/go.sh`: lines 15, 16 and 26 (the boot id that the run requires, with its comment), line 27 (lower limit for MemTotal), lines 40 to 42 (one call of `ra.sh` per session).
- [Ref6] `R/kernels-20261113T181222Z/probe.txt` (run of 18:12:22 UTC): line 1 (mode `all`), lines 14 and 15 (checksums of `bandwidth.orig.c` and `bandwidth.c`), lines 19 and 20 (checksums of `bw_old` and `bw_new`). `R/kernels-20261113T183218Z/probe.txt` (run of 18:32:18 UTC) and `R/kernels-20261113T181210Z/probe.txt` (run of 18:12:10 UTC): the same line numbers, mode `probe` in line 1.
- [Ref7] `K13/run_kernels.sh`: lines 4 to 6 and line 56 (the mode `probe` ends before the timed runs), lines 31 and 32 (build of the two binaries at every start), line 37 (checksums of the sources and the binaries). `K13/bandwidth.orig.c` and `K13/bandwidth.c`: the local source files, checksums computed with `sha256sum` in this task. The checksum of the local `K13/run_kernels.sh` (6a91bbbe...) is equal to line 18 of the three files of [Ref6].
- [Ref8] `S/facts_data.py`: lines 117 to 130 (function `read_probe`). `S/build_facts.py`: lines 66 to 72 (call), line 93 (end time of part A), line 170 (field `binary_sha256` of the rerun records), lines 195 to 204 (the same field of the baseline records, from `probe.txt` of 2026-11-13), lines 674 to 694 (checks of boot id, MemTotal and logins), lines 752 to 763 (checks of the checksums), lines 781 to 797 (checks of the Linux kernel release and of the runnable tasks). `S/facts_text.py`: lines 748 to 753 and lines 858 and 859 (tables with the load averages and the highest %CPU).
- [Ref9] `S/FACTS.md`: lines 38 to 71 and line 77 (word list, with the entries "Load average", "%CPU", "Boot id", "MemTotal", "Marker file"), lines 159 and 162 (MemTotal and the 12 modules, 377.08 GiB), line 164 (7200 MT/s was recorded at 20:02:21 UTC in the same boot and was not read again during the rerun), line 168 (huge page setting, the value in brackets is the active one), lines 183 to 187 (table of the load values of part A), lines 207 and 208 (what a %CPU list can and cannot show), line 209 (hypothesis on the high load values).
- [Ref10] `S/baselines-and-rules.txt`: line 18 and lines 21 and 22 (baseline A-1 is the test of 2026-11-13: 8000 MT/s, the same two binaries).
- [Ref11] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
