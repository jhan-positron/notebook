# `env.txt` explained: part C, session 1 (spec file cfwd.spec)

## Short version

This file is the machine record of part C, session 1 (spec file cfwd.spec) of the whole-chip rerun at 7200 MT/s of 2026-11-17.

## This file

- File: `env.txt` in this folder (`crb/results/w120-T72C1-20261117T221436Z`).
- Size: 10 lines, 380 bytes. sha256 when this page was built: `bb87e5cc9a9254a306a6fd9d4b1ce0fb083ec32f2667551755ad23dbbd1e2a8d`.
- Written by: `rx.sh` (the runner script), once, before it started the process.
- Step of the run: part C, session 1 (spec file cfwd.spec), folder tag `T72C1`.

## The whole file (copied from the file by a script)

```text
 1  Tue Nov 17 10:14:36 PM UTC 2026
 2  7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858
 3  103.24 41.70 15.53 1/1018 8262
 4  USER     %CPU COMMAND
 5  root      0.1 pr/ttyAMA-1
 6  root      0.0 systemd
 7  jhan      0.0 systemd
 8  root      0.0 rcu_preempt
 9  root      0.0 kworker/u512:0-bnxt_pf_wq
10  binary /home/jhan/cache-perf/bwx12-20261115/bwx12 cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a
```

The sections below explain the file type. The same text stands in the companion of every file of this type.

## The file type in short

`env.txt` records the state of the machine at the start of the runner script rx.sh (in the nine folders: 5 s before the start of the benchmark process). Its 10 lines hold the time, the Linux kernel release, the load, the five processes with the highest %CPU, and the path and checksum of the benchmark binary. It holds no measured rate and no name of a read kernel.

Scope of this text:

- This text covers the file `env.txt` in each of the nine folders `R/w120-T72*` of the rerun of 2026-11-17 (parts L and C, control I).
- The nine files have the same format. The section "The nine files" lists the values of each one.
- `R` is `/home/jhan/workspace/titan/cache-perf/crb/results`. The other folder letters are in "Words used here".

## What this file is

- **Writer.** rx.sh (the runner script for the bwx12 benchmark processes) writes the file with one group of six commands [Ref1].
- **Step of the run.** rx.sh first tests the marker file and the checksum of the binary. Then it creates the result folder. Then it writes `env.txt` [Ref2]. The wait, the 5 s sleep and the launch of the benchmark process come after that [Ref3].
- **How often.** rx.sh writes the file once per call. One call makes one result folder. In the nine folders one call launched one bwx12 process.
- **One line per what.** Each of the six commands writes its own output lines, in the order of the commands. The file records the state of the machine at one moment. It is not a table of measurements.
- **Time of the reading.** Line 1 and the folder name show the same time in whole seconds, in all nine folders. The launch line of `launches.txt` in the same folder is 5 s later, in all nine folders.

Sample: lines 1 to 10 (the whole file) of `R/w120-T72L1-20261117T221329Z/env.txt`.

```
Tue Nov 17 10:13:29 PM UTC 2026
7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858
80.50 24.65 8.59 1/1019 8032
USER     %CPU COMMAND
root      0.1 pr/ttyAMA-1
root      0.0 systemd
jhan      0.0 systemd
root      0.0 rcu_preempt
root      0.0 kworker/u512:0-bnxt_pf_wq
binary /home/jhan/cache-perf/bwx12-20261115/bwx12 cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a
```

## Line kinds

The line numbers are true for all nine files. Each file has 10 lines.

| Line | How to recognise it | Command of rx.sh that writes it [Ref1] | What it holds |
|---|---|---|---|
| 1 | It starts with a weekday and ends with the year. | `date -u` | Date and time of the reading, in UTC. |
| 2 | It is one word. | `uname -r` | Release of the running Linux kernel (the operating system kernel). |
| 3 | It has five fields. The fourth field holds a `/`. | `cat /proc/loadavg` | Load of the machine. |
| none | It would stand between line 3 and line 4. | `who` | One line per user who is logged on. `who` printed no line in the nine files. |
| 4 | It holds the three words `USER`, `%CPU`, `COMMAND`. | `ps -eo user,pcpu,comm --sort=-pcpu \| head -6` | Header of the process list. |
| 5 to 9 | Each line has three columns under the header. | the same command | The five processes with the highest %CPU, highest first. |
| 10 | It starts with the word `binary`. | `echo "binary $BW $sha"` | Path and sha256 checksum of the benchmark binary. |

- A line of `who` would move lines 4 to 10 down by one line.
- A line of `who` would hold four values: the login name, the terminal line, the login time, and the remote host name or X display [Ref6].
- go.sh and go2.sh were started through an ssh connection (ssh is the remote login tool). The connection stayed open until the script ended [Ref16]. `who` printed no line for it. So an empty output of `who` does not show that no connection to CRB was open.
- make_report.py (the script that builds the HTML report) reads five of the nine files. It stops with an error when line 4 of one of them is not the header of the process list [Ref10].

## Columns

### Line 1: time

The line has 7 fields. Spaces separate them.

| Field | Name | Unit or form | Meaning |
|---|---|---|---|
| 1 | weekday | three letters | Day of the week. |
| 2 | month | three letters | Month. |
| 3 | day | day of the month | Day. |
| 4 | time | hh:mm:ss, 12-hour clock | Time of the reading. |
| 5 | AM or PM | text | Half of the day. `10:13:29 PM` is 22:13:29. |
| 6 | time zone | text, always `UTC` | The option `-u` makes `date` print Universal Time [Ref6]. |
| 7 | year | four digits | Year. |

- `date` without a format argument prints the default format of the locale of the shell [Ref6].
- On CRB this default format uses a 12-hour clock. The launch line and the rc line of `launches.txt` use a 24-hour clock.

### Line 2: Linux kernel release

The line has 1 field. `uname -r` prints the release of the running Linux kernel [Ref6]. All nine files hold `7.1.3-arm-agi-20260916-v0.7.2-g4dbc8bb88858`.

### Line 3: load

The line has 5 fields. It is a copy of the file `/proc/loadavg` [Ref4].

| Field | Name | Unit | Meaning |
|---|---|---|---|
| 1 | load average, 1 minute | tasks (an average count) | Number of tasks that are runnable or wait for disk input and output, averaged over the last 1 minute. |
| 2 | load average, 5 minutes | tasks | The same average over the last 5 minutes. |
| 3 | load average, 15 minutes | tasks | The same average over the last 15 minutes. |
| 4 | runnable / all | two counts with a `/` between them | Before the `/`: the tasks (processes and threads) that are runnable now. After the `/`: all tasks that exist now. |
| 5 | last PID | process number | PID (process number) of the process that Linux created last. |

### Lines 4 to 9: process list

Line 4 is the header. Lines 5 to 9 have 3 columns each.

| Column | Header | Unit | Meaning |
|---|---|---|---|
| 1 | `USER` | name | Effective user name of the process [Ref5]. |
| 2 | `%CPU` | percent | CPU time that the process has used, divided by the time since the process started [Ref5]. |
| 3 | `COMMAND` | name | Name of the executable, without its arguments [Ref5]. |

How the command makes the list [Ref5]:

- `-e` selects all processes.
- `-o user,pcpu,comm` prints the three columns of the table above.
- `--sort=-pcpu` sorts the rows by %CPU, the highest value first.
- `head -6` keeps the first 6 lines. These are the header and five processes.

Notes:

- A command name may hold spaces [Ref5]. No name in the nine files holds a space. Each of the lines 5 to 9 has 3 fields in all nine files.
- Rows with the same %CPU do not keep one order. Example: line 7 is `jhan      0.0 systemd` in `R/w120-T72C1-20261117T221436Z/env.txt` and `root      0.0 rcu_preempt` in `R/w120-T72C3-20261117T222054Z/env.txt`.

### Line 10: binary

The line has 3 fields.

| Field | Name | Unit or form | Meaning |
|---|---|---|---|
| 1 | `binary` | fixed word | Marks the line. |
| 2 | path | file path on CRB | Argument 2 of rx.sh: the benchmark binary that rx.sh launches [Ref2]. |
| 3 | sha256 | 64 hexadecimal digits | Argument 3 of rx.sh: the checksum that the caller expects for the binary [Ref2]. |

- rx.sh does not compute the checksum for this line. It prints the value that it received.
- rx.sh tested the file against this value before it created the folder. On a mismatch it prints `sha mismatch` and ends with status 2 [Ref2]. So an `env.txt` exists only when the test passed.
- All nine files hold the path `/home/jhan/cache-perf/bwx12-20261115/bwx12` and the sha256 `cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a`. This is the value `SHA=` of go.sh and of go2.sh [Ref12].
- The binary bwx12 is not in the local folders. So its sha256 cannot be computed again here. The value is known only from the records. One more record is the build record of bwx12, the file `build.txt`. It holds the same value [Ref17].

### The nine files

The rows are in the order of time. A script made the table from the files.

| Folder (under `R`) | Line 1: time | Line 3: load | Highest %CPU in lines 5 to 9 | Lines | Bytes |
|---|---|---|---|---|---|
| `w120-T72L1-20261117T221329Z` | `Tue Nov 17 10:13:29 PM UTC 2026` | `80.50 24.65 8.59 1/1019 8032` | 0.1 | 10 | 378 |
| `w120-T72C1-20261117T221436Z` | `Tue Nov 17 10:14:36 PM UTC 2026` | `103.24 41.70 15.53 1/1018 8262` | 0.1 | 10 | 380 |
| `w120-T72L2-20261117T221638Z` | `Tue Nov 17 10:16:38 PM UTC 2026` | `113.61 65.47 27.49 1/1019 11476` | 0.1 | 10 | 381 |
| `w120-T72C2-20261117T221745Z` | `Tue Nov 17 10:17:45 PM UTC 2026` | `114.40 74.54 33.15 1/1024 11714` | 0.1 | 10 | 381 |
| `w120-T72L3-20261117T221947Z` | `Tue Nov 17 10:19:47 PM UTC 2026` | `111.98 85.23 41.99 1/1026 14921` | 0.1 | 10 | 381 |
| `w120-T72C3-20261117T222054Z` | `Tue Nov 17 10:20:54 PM UTC 2026` | `114.36 90.94 47.07 1/1028 15156` | 0.1 | 10 | 381 |
| `w120-T72C4-20261117T222136Z` | `Tue Nov 17 10:21:36 PM UTC 2026` | `111.90 92.86 49.54 2/1030 15364` | 0.1 | 10 | 381 |
| `w120-T72I1-20261117T222700Z` | `Tue Nov 17 10:27:00 PM UTC 2026` | `0.95 36.39 38.17 1/1043 15958` | 0.1 | 10 | 358 |
| `w120-T72I2-20261117T223227Z` | `Tue Nov 17 10:32:27 PM UTC 2026` | `0.99 21.40 32.57 1/1038 16320` | 0.1 | 10 | 379 |

- The 1-minute load average is 80.50 to 114.40 tasks in the seven folders of go.sh (parts L and C). It is 0.95 and 0.99 tasks in the two folders of go2.sh (control I).
- The highest %CPU is 0.1 % in all nine files. It belongs to the process `pr/ttyAMA-1` in line 5 of each file.
- Each driver script prints a state line directly before it calls rx.sh. In all nine folders the first three fields of line 3 are equal to the load values of that state line [Ref13]. Line 1 and that state line show the same time in whole seconds.

### Limits of this file

- The reading is older than the launch. The load at the launch is in the launch line of `launches.txt`. Example: line 3 of `R/w120-T72L1-20261117T221329Z/env.txt` holds a 1-minute load average of 80.50 tasks. Line 1 of `launches.txt` in the same folder holds 74.05 tasks, 5 s later.
- %CPU is an average over the life of a process. It is not the use at the moment of the reading. So the list would show a new busy process. It cannot show a short busy phase of a process that has run since the boot [Ref9].
- The list holds five processes only.
- The file holds the sha256 of the benchmark binary only. It holds no sha256 of rx.sh. go.sh and go2.sh test the sha256 of rx.sh before their first call of rx.sh. They stop on a mismatch [Ref12].
- The file holds no boot id, no MemTotal and no memory speed. The state lines of the run logs hold the boot id and MemTotal [Ref13]. A comment in go.sh names the file that recorded the memory speed of this boot: `results/dimm7200-20261117/try6.txt` [Ref12].
- Insufficient data: the versions of `ps`, `who` and `date` on CRB. A run of `ps --version`, `who --version` and `date --version` on CRB would resolve it. The meanings above come from the manual pages named in [Ref4], [Ref5] and [Ref6].

## Old read kernel and new read kernel in this file

This section does not apply: `env.txt` names no read kernel.

- One `env.txt` belongs to the one bwx12 process of its folder. That process ran every kernel of its sequence, one after the other.
- The sequence holds the old read kernel and one or two load-only loops. In part L and control I it also holds three test loops (`read_nop96`, `read_nop256`, `read_1pl`).
- So the file describes the state before the process. It does not describe the state before each kernel.
- Line 10 names the binary that ran every kernel of the folder.

## Which code reads this file

No rate comes from this file. The rates of a folder come from the csv file of the folder. For each timed interval the analysis adds bytes / elapsed_s / 1e9 over the T rows (one row per thread). The result is a rate in GB/s (GB = 1e9 bytes) [Ref14].

| Reader | What it takes from `env.txt` | What it does with it |
|---|---|---|
| facts_data.py, function `read_env` [Ref7] | Line 1 as the start time. Line 2 as the Linux kernel release. Line 3 as text. Every process row from line 4 on (user, %CPU, command, line number). The path and the sha256 of the line that starts with `binary`. The number of lines. | It returns these values to build_facts.py. It also returns the highest %CPU. |
| build_facts.py [Ref8] | The values of `read_env` for each of the nine folders. | Check 19 passes when three conditions hold. Line 10 holds one sha256 value in the nine files. This value is equal to `SHA=` of go.sh. The `env.txt` files of nine other bwx12 runs (the rows L-1, L-2, L-3, L-4, X2d12, F72d12, X1d10, X1d10b and BASEd10 of the facts sheet) hold the same value. Check 21 passes when line 2 of the nine files and the three probe.txt files of part A hold one value, and this value is equal to the release in the kernel image name of the Linux command line. Each check appears in section 1.4 of FACTS.md with the word "pass" or "FAILED". build_facts.py also writes the sha256 into the field `binary_sha256` of each record of the nine folders in facts.json (one record per timed interval). It also searches the whole text of the nine files for the sha256 of the local rx.sh, go.sh and go2.sh. It stops with an error when it finds one. |
| facts_text.py [Ref9] | The highest %CPU and the start time. | It writes the table column "Highest %CPU in the process list of env.txt" of FACTS.md. It writes the number of seconds from line 1 to the launch line. |
| facts_text4.py [Ref15] | The highest %CPU of the two folders of control I (a value of `read_env`). | It writes the value into the table and the text of section 4.6 of FACTS.md. It stops with an error when the value is not below 1 %. |
| make_report.py, function `proc_list` [Ref10] | Line 1, line 4 and the process rows up to the `binary` line, for the five folders of part L and control I. | It stops with an error unless line 1 is more than 0 s and less than 60 s before the launch time. It stops with an error unless the highest %CPU is below 1 %. |

- Both checks passed in the facts sheet FACTS.md [Ref11].
- stat_bwx.py and stat_k120.py (the two scripts for quick statistics) do not read this file.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process**: one start of a benchmark binary.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries. The script ra.sh runs it and writes the state record `probe.txt` into its folder.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg [Ref4]).
- **%CPU**: the column pcpu of the tool ps in the process lists of env.txt and probe.txt. It is the CPU time that a process has used, divided by the time since the process started [Ref5]. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **pr/ttyAMA-1**: a Linux kernel thread in the process lists. By its name it prints kernel messages to the serial console ttyAMA. This meaning was not checked on CRB.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **Run log**: the file that holds the standard output and the error output of go.sh or of go2.sh [Ref16]. The two run logs are `go-T72-20261117T221209Z.log` and `go2-T72-20261117T222335Z.log` in the folder `R` [Ref13].
- **rx.sh**: the runner script of parts L and C and of control I. It reads a spec file, launches one bwx12 process per line and writes `env.txt`, `launches.txt`, `stderr.txt` and one csv file per process.
- **go.sh, go2.sh**: the two driver scripts of the rerun. go.sh runs the three sessions. go2.sh runs control I. Both call rx.sh.
- **Result folder**: the folder that one call of rx.sh creates. Its name is `w120-<name>-<UTC time>`. The name is `T72L<s>` for part L of session s, `T72C<s>` for part C and `T72I<i>` for run i of control I. `T72C4` is one more part C process that go.sh runs after session 3.
- **Spec file**: the input of rx.sh. Each line holds a tag, the character `|` and the arguments of one bwx12 process.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. rx.sh stops when this file exists.
- **Csv file**: the file `<tag>.csv` of a result folder. It holds the result rows that bwx12 prints. A T row holds the values of one thread in one timed interval.
- **facts_data.py, build_facts.py, facts_text.py, facts_text4.py**: the scripts that read the raw files of the rerun and write the facts sheet. The facts sheet is `facts.json` (data) and `FACTS.md` (text) in the folder `S`.
- **Locale**: the language and country setting of a shell. It selects the default format of dates.
- **sha256**: a checksum of 64 hexadecimal digits. Two files with the same sha256 have the same content.
- **UTC**: Coordinated Universal Time, the time zone of all times in these files.
- **PID**: the number that Linux gives to a process.
- **Folder letters**: `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`. `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`. `W15` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15`. On CRB the folder `R` was `~/cache-perf/results`.

</details>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`, line 10: the group of six commands that writes `env.txt`.
- [Ref2] The same file, lines 6 to 9: the arguments, the test of the marker file, the test of the checksum with `sha256sum -c` (exit status 2 on a mismatch), the creation of the result folder.
- [Ref3] The same file, lines 11 to 17: the loop over the spec lines, the wait, the 5 s sleep, the launch line and the start of the process.
- [Ref4] External source: Linux manual page proc_loadavg(5) (older releases: proc(5), entry /proc/loadavg), read at `https://man7.org/linux/man-pages/man5/proc_loadavg.5.html` on 2026-11-21. It gives the five fields of `/proc/loadavg`. No manual page is installed on the server of this task.
- [Ref5] External source: manual page ps(1) of procps-ng, read at `https://man7.org/linux/man-pages/man1/ps.1.html` on 2026-11-21: the options `-e`, `-o` and `--sort`, the format names `user` (effective user name), `pcpu` (alias of `%cpu`) and `comm`, and the note "CPU usage is currently expressed as the percentage of time spent running during the entire lifetime of a process". The command `ps L` of procps-ng 3.3.17 on the server of this task lists the headers `USER`, `%CPU` and `COMMAND` for these three names.
- [Ref6] GNU coreutils manual, file `/usr/share/info/coreutils.info.gz` on the server of this task (coreutils 8.32): section 20.6 (`who` prints one line per user who is logged on, with the login name, the terminal line, the login time, and the remote host name or X display), section 21.1 (`date`: the default format depends on the locale, `-u` prints Universal Time), section 21.4 (`uname -r` prints the kernel release).
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`, lines 159 to 171: function `read_env`.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`, lines 82 to 86 (call of `read_env` per folder), lines 176 to 180 (field `binary_sha256`), lines 764 to 771 (check of the sha256), lines 782 to 786 (check of the Linux kernel release), lines 853 to 858 (search for the sha256 of rx.sh, go.sh and go2.sh in the text of the nine files).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`, lines 868 to 874 (table with the highest %CPU) and lines 888 to 895 (seconds from line 1 to the launch line, and what the process list can show).
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`, lines 1100 to 1114 (function `proc_list`) and lines 1128 to 1136 (the five folders and the two tests).
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`, line 231 (check 19, sha256 of bwx12) and line 233 (check 21, Linux kernel release).
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`, lines 12, 13 and 31 (path and sha256 that go.sh passes to rx.sh), lines 14 and 22 (the sha256 of rx.sh and its test) and line 15 (the comment that names `try6.txt`). `go2.sh` in the same folder, lines 9, 10 and 30 (path and sha256 of the binary), lines 11 and 18 (the sha256 of rx.sh and its test).
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log`, lines 8, 12, 18, 22, 28, 32 and 36 (the state line before each of the seven calls of rx.sh). `/home/jhan/workspace/titan/cache-perf/crb/results/go2-T72-20261117T222335Z.log`, lines 3 and 8 (the same for the two calls of control I).
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`, lines 9 to 13: the two kinds of rate. For the bwx runners the rate is the sum over the T rows (threads) of bytes / elapsed_s / 1e9. Lines 356 to 383 (function `bwx_intervals`): the sum is made for each interval (round, position, kernel).
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`, lines 1064 to 1067 (the row of control I in the table of section 4.6) and lines 1079 to 1088 (the test of the highest %CPU of control I, and the sentence that reports it).
- [Ref16] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the record of the Claude Code session of 2026-11-17. This file lies outside the project folder. No script of the folder `S` holds the command that started the run. Line 313 of the record holds the command for go.sh, and line 365 holds the command for go2.sh. Each command was sent with ssh as user jhan. Its start part is `nohup setsid <script> > <log file> 2>&1 < /dev/null &`. The part `> <log file> 2>&1` sends the standard output and the error output of the script to the log file. The command then waits for the end of the script. Lines 336 and 378 hold the output of the two commands, with `go.sh exit status 0` and `go2.sh exit status 0`.
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`, line 20: the sha256 of the binary bwx12 in the record of its build on CRB (2026-11-15). A search with `find` under `/home/jhan/workspace/titan/cache-perf` finds no file with the name `bwx12`.
