# `launches.txt` explained: part C, session 3 (spec file cfwd.spec)

## Short version

This file is the launch record of part C, session 3 (spec file cfwd.spec) of the whole-chip rerun at 7200 MT/s of 2026-11-17.

## This file

- File: `launches.txt` in this folder (`crb/results/w120-T72C3-20261117T222054Z`).
- Size: 2 lines, 339 bytes. sha256 when this page was built: `b96eead4d8537f5066df9176cbed45d8162adabef2ba56a9edcd69a1da943d2c`.
- Written by: `rx.sh` (the runner script): one line before the process started and one line after it ended.
- Step of the run: part C, session 3 (spec file cfwd.spec), folder tag `T72C3`.

## The whole file (copied from the file by a script)

```text
1  launch cfwd utc 22:20:59 load 105.20 89.43 46.82 1/1028 15166 users 0 args --threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --seq oldread,read,asmread --count --pmu-type 11 --events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19
2  rc 0 cfwd utc 22:21:36
```

The sections below explain the file type. The same text stands in the companion of every file of this type.

## The file type in short

`launches.txt` is the launch record of rx.sh, the runner script for the bwx12 benchmark processes. For each process it holds one `launch` line (time, load, logins and arguments directly before the start) and one `rc` line (exit status and time after the end). The driver scripts go.sh and go2.sh stop the run unless the file holds exactly one `rc` line and that line reports the exit status 0.

Scope of this text:

- This text covers the file `launches.txt` in each of the nine folders `R/w120-T72*` of the rerun of 2026-11-17 (parts L and C, control I).
- The nine files have the same format. The section "The nine files" lists the values of each one.
- `R` is `/home/jhan/workspace/titan/cache-perf/crb/results`. The other folder letters are in "Words used here".

## What this file is

- **Writer.** rx.sh writes the file inside its loop over the lines of the spec file [Ref1].
- **How often.** Two lines per process: the `launch` line before the start and the `rc` line after the end. rx.sh appends the lines. It never rewrites the file.
- **In the nine folders.** Each spec file has one line. So each of the nine files has 2 lines: one `launch` line and one `rc` line.
- **Source of the times.** The two times come from the shell command `date`, in whole seconds. The timed intervals of the benchmark are in the csv file of the folder.

What rx.sh does for one line of the spec file [Ref1]:

1. It reads the line. The text before the first `|` becomes the tag. The text after it becomes the arguments.
2. It stops with exit status 3 when the marker file exists.
3. It waits until at most 2 tasks are runnable. It reads the count once per second, at most 40 times. After the 40th reading it continues, also when more than 2 tasks are runnable.
4. It sleeps 5 s.
5. It appends the `launch` line to `launches.txt`.
6. It starts the binary in the background on the CPUs 0 to 119. The standard output goes to `<tag>.csv`. The standard error goes to `stderr.txt`.
7. It tests once per second whether the process still exists. When the marker file appears in this time, rx.sh kills the process and stops with exit status 3. Then no `rc` line is written.
8. It reads the exit status of the process and appends the `rc` line.

Sample: lines 1 and 2 (the whole file) of `R/w120-T72L1-20261117T221329Z/launches.txt`.

```
launch a6456 utc 22:13:34 load 74.05 24.24 8.54 1/1019 8042 users 0 args --threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 6000 --rounds 2 --seq oldread,asmread,read_nop96,read_nop256,read_1pl --count --pmu-type 11 --events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19
rc 0 a6456 utc 22:14:36
```

## Line kinds

| Kind | How to recognise it | When rx.sh writes it | What it holds |
|---|---|---|---|
| `launch` line | It starts with the word `launch`. | After the wait and the 5 s sleep. The next command of rx.sh starts the process [Ref2]. | Tag, time, load, number of logins, arguments of the process. |
| `rc` line | It starts with the word `rc`. | After rx.sh found that the process has ended [Ref3]. | Exit status of the process, tag, time. |

- The two lines of one process hold the same tag. The csv file of the process is `<tag>.csv`.
- A `launch` line without an `rc` line means that rx.sh ended while the process ran. One cause is the marker file (step 7 above).

## Columns

Single spaces separate the fields of both line kinds.

### `launch` line

A `launch` line of the nine files has 34 fields: 13 fields before the arguments and 21 words of arguments. The examples are from line 1 of the sample above.

| Field | Content | Unit or form | Meaning | Example |
|---|---|---|---|---|
| 1 | `launch` | fixed word | It marks the line kind. | `launch` |
| 2 | tag | name | Text before the first `\|` of the spec line. The csv file of the process is `<tag>.csv` [Ref2]. | `a6456` |
| 3 | `utc` | fixed word | It marks the next field. | `utc` |
| 4 | launch time | hh:mm:ss, 24-hour clock, UTC | Time that `date -u +%T` gave when rx.sh wrote the line [Ref2]. | `22:13:34` |
| 5 | `load` | fixed word | The next five fields are a copy of the file `/proc/loadavg` [Ref2]. | `load` |
| 6 | load average, 1 minute | tasks (an average count) | Number of tasks that are runnable or wait for disk input and output, averaged over the last 1 minute [Ref4]. | `74.05` |
| 7 | load average, 5 minutes | tasks | The same average over the last 5 minutes. | `24.24` |
| 8 | load average, 15 minutes | tasks | The same average over the last 15 minutes. | `8.54` |
| 9 | runnable / all | two counts with a `/` between them | Before the `/`: the tasks (processes and threads) that are runnable now. After the `/`: all tasks that exist now [Ref4]. | `1/1019` |
| 10 | last PID | process number | PID (process number) of the process that Linux created last [Ref4]. | `8042` |
| 11 | `users` | fixed word | It marks the next field. | `users` |
| 12 | logins | count | Number of lines that `who` printed. `who` prints one line per user who is logged on [Ref5]. | `0` |
| 13 | `args` | fixed word | All text after this word is the argument text. | `args` |
| 14 to 34 | arguments | text | Text after the first `\|` of the spec line, unchanged. rx.sh passes these words to the binary [Ref2]. | `--threads 120` and 19 more words |

- "Load at launch" in the facts sheet is field 6. facts.json holds it in the field `load1_at_launch`.
- Field 12 counts logins only. A state line of the run log, printed 5 s before the launch of the folder T72L1, shows `users 0` and 11 processes of the account jhan [Ref12]. So 0 logins does not mean 0 processes of users.
- go.sh and go2.sh were started through an ssh connection (ssh is the remote login tool). The connection stayed open until the script ended [Ref19]. Field 12 is 0 in all nine `launch` lines. So `who` did not count this connection.
- For the meaning of each argument, see the explanation of the spec files (`like.spec`, `cfwd.spec`, `crev.spec` in the folder `S`).

### `rc` line

An `rc` line has 5 fields. The examples are from line 2 of the sample above.

| Field | Content | Unit or form | Meaning | Example |
|---|---|---|---|---|
| 1 | `rc` | fixed word | It marks the line kind. The line reports the exit status (return code) of the process. | `rc` |
| 2 | exit status | whole number | Exit status of the process that rx.sh launched. rx.sh reads it with `wait` [Ref3]. | `0` |
| 3 | tag | name | The tag of the `launch` line of the same process. | `a6456` |
| 4 | `utc` | fixed word | It marks the next field. | `utc` |
| 5 | end time | hh:mm:ss, 24-hour clock, UTC | Time that `date -u +%T` gave when rx.sh wrote the line [Ref3]. | `22:14:36` |

What the exit status can be:

| Value | Meaning | Source |
|---|---|---|
| 0 | bwx12 reached the normal end of its function `main`. | [Ref6] |
| 1 | taskset could not set the CPU list. The binary did not start. bash gives the same status when it cannot open `<tag>.csv` or `stderr.txt`. | local test [Ref7] |
| 2 | bwx12 stopped on one of its error paths (`exit(2)` or `return 2`). | [Ref6] |
| 126 | taskset found the file of the binary and could not execute it (example: no execute permission). | local test [Ref7] |
| 127 | taskset did not find the file of the binary. bash gives the same status when it does not find `taskset` itself. | local test [Ref7] |
| above 128 | A signal ended the process. The value is 128 plus the number of the signal. Example: 143 for the signal TERM (number 15). | local test [Ref7] |

- The table holds for the arguments of the nine `launch` lines. These lines hold none of the options `--trial`, `--selftest` and `--list`.
- With one of these three options the function `main` of bwx12 returns early. Then the values 0, 1 and 2 can have another meaning [Ref6].

### How exact the two times are

- rx.sh reads the launch time. Its next command starts the process. So the launch time is the time directly before the start, in whole seconds.
- rx.sh tests once per second whether the process still exists. It writes the `rc` line after the test that finds no process. So the end time can be up to about 1 s later than the real end of the process (est.).
- The launch time is 5 s after line 1 of `env.txt` of the same folder, in all nine folders. rx.sh always sleeps 5 s between the wait loop and the `launch` line. A second reading of the wait loop comes only after one more sleep of 1 s. So the wait loop ended at its first reading in all nine folders.

### The nine files

The rows are in the order of time. A script made the table from the files.

| Folder (under `R`) | Tag | Launch time (UTC) | Load 1 / 5 / 15 min | Runnable / all | Last PID | Users | Exit status | Time of the rc line (UTC) | Launch line to rc line |
|---|---|---|---|---|---|---|---|---|---|
| `w120-T72L1-20261117T221329Z` | `a6456` | 22:13:34 | 74.05 / 24.24 / 8.54 | 1 / 1019 | 8042 | 0 | 0 | 22:14:36 | 62 s |
| `w120-T72C1-20261117T221436Z` | `cfwd` | 22:14:41 | 94.97 / 41.01 / 15.45 | 1 / 1018 | 8272 | 0 | 0 | 22:15:18 | 37 s |
| `w120-T72L2-20261117T221638Z` | `a6456` | 22:16:43 | 104.52 / 64.38 / 27.34 | 1 / 1019 | 11486 | 0 | 0 | 22:17:45 | 62 s |
| `w120-T72C2-20261117T221745Z` | `crev` | 22:17:50 | 105.24 / 73.30 / 32.97 | 1 / 1024 | 11724 | 0 | 0 | 22:18:27 | 37 s |
| `w120-T72L3-20261117T221947Z` | `a6456` | 22:19:52 | 103.01 / 83.82 / 41.76 | 1 / 1026 | 14931 | 0 | 0 | 22:20:54 | 62 s |
| `w120-T72C3-20261117T222054Z` | `cfwd` | 22:20:59 | 105.20 / 89.43 / 46.82 | 1 / 1028 | 15166 | 0 | 0 | 22:21:36 | 37 s |
| `w120-T72C4-20261117T222136Z` | `crev` | 22:21:41 | 102.94 / 91.31 / 49.28 | 1 / 1030 | 15374 | 0 | 0 | 22:22:18 | 37 s |
| `w120-T72I1-20261117T222700Z` | `a6456` | 22:27:05 | 0.87 / 35.79 / 37.97 | 1 / 1043 | 15968 | 0 | 0 | 22:28:07 | 62 s |
| `w120-T72I2-20261117T223227Z` | `a6456` | 22:32:32 | 0.91 / 21.05 / 32.39 | 1 / 1038 | 16330 | 0 | 0 | 22:33:34 | 62 s |

- The 1-minute load average at launch is 74.05 to 105.24 tasks in the seven folders of go.sh (parts L and C). It is 0.87 and 0.91 tasks in the two folders of go2.sh (control I).
- 1 task was runnable at each of the nine launches. `who` listed 0 logins at each launch. Every process ended with the exit status 0.
- The wait loop of rx.sh tests the count of runnable tasks. It does not test the load average. So the seven processes of go.sh started with 1 runnable task at a 1-minute load average of 74.05 to 105.24 tasks. A comment in go2.sh states that every bwx12 process of go.sh started about 5 s after other 120-thread work [Ref10]. The 1-minute load average is an average over the last 1 minute. So it still counts the threads of that work.
- The time from the `launch` line to the `rc` line is 62 s for the tag `a6456`. The csv file of these folders holds 10 interval rows of 6.00 s each (60 s in total).
- The time is 37 s for the tags `cfwd` and `crev`. The csv file of these folders holds 6 interval rows of 6.00 s each (36 s in total).

## Old read kernel and new read kernel in this file

The file has one `launch` line per process. It has no line per kernel. The argument `--seq` of the `launch` line names the kernels of the process, in the order in which the process runs them.

| Tag | Spec file | Value of `--seq` in the `launch` line | Folders |
|---|---|---|---|
| `a6456` | `like.spec` | `oldread,asmread,read_nop96,read_nop256,read_1pl` | T72L1, T72L2, T72L3, T72I1, T72I2 |
| `cfwd` | `cfwd.spec` | `oldread,read,asmread` | T72C1, T72C3 |
| `crev` | `crev.spec` | `asmread,read,oldread` | T72C2, T72C4 |

- `oldread` is the old read kernel.
- `read` is the new read kernel.
- `asmread` is a hand-written load-only loop with the same loads as the new read kernel.
- The tag `a6456` has no entry `read`. So the folders of part L and of control I hold no interval of the new read kernel itself. Their load-only loop is `asmread`.
- All kernels of one `--seq` list ran in the same process, one after the other. So the two lines of the file describe all of them together. The file does not give the time or the load at the start of each kernel.
- The argument `--rounds 2` is in every `launch` line. The csv file holds 2 interval rows for each entry of `--seq`.
- The rows of each kernel are in `<tag>.csv` of the same folder.

## Which code reads this file

No rate comes from this file. The rates of a folder come from `<tag>.csv`. For each timed interval the analysis adds bytes / elapsed_s / 1e9 over the T rows (one row per thread). The result is a rate in GB/s (GB = 1e9 bytes) [Ref13]. This file gives the load at launch, the launch time and the end time that the analysis reports next to the rates.

### How go.sh uses the `rc` line (function `rxok`)

The function `rxok` of go.sh [Ref8]:

```
rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null | tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }
```

1. go.sh calls rx.sh through its function `runx`, with the name of the folder (for example `T72L1`) and a spec file [Ref8].
2. The exit status of rx.sh does not show whether bwx12 failed. rx.sh ends with the status of its last command, and this command only prints the first 600 bytes of `stderr.txt` [Ref9]. A comment in go.sh states this reason [Ref8].
3. So `runx` calls `rxok` with the name of the folder directly after rx.sh. When rx.sh itself ends with a status other than 0 (2 for a wrong checksum, 3 for the marker file), `runx` stops go.sh before it calls `rxok`.
4. `rxok` lists the files `launches.txt` of all folders `w120-<name>-*`. It takes the last one in the order of the names. The folder names end with the UTC time. So this is the newest folder of that name.
5. `rxok` makes three tests. A file was found. Exactly 1 line of the file starts with `rc ` (one process ended and rx.sh recorded it). Exactly 1 line starts with `rc 0 ` (the exit status of this process is 0).
6. `rxok` succeeds only when all three tests hold. Each spec file has one line. So exactly one `rc` line is required [Ref8].
7. When `rxok` fails, go.sh prints `FAILED: bwx12 <name>: exit status not 0 (launches.txt, stderr.txt)` and a state line. Then go.sh ends with exit status 1. No later part of the run starts [Ref8].
8. go2.sh holds the same function and uses it in the same way after each call of rx.sh [Ref10].

In this run the two logs hold no line that starts with `FAILED`. Both logs end with the line `ALLDONE` [Ref12].

### Other readers

| Reader | What it takes from `launches.txt` | What it does with it |
|---|---|---|
| rx.sh, its last line [Ref9] | The number of lines that are not empty. Every `rc` line that does not start with `rc 0`. | It prints both to its standard output. In the run logs the line `2` follows each `done` line of an rx.sh folder. No `rc` line follows [Ref12]. |
| facts_data.py, patterns `LAUNCH` and `RC`, function `read_launches` [Ref11] | `launch` line: fields 2, 4, 6, 7, 8, 9, 12 and the arguments. Field 10 (last PID) is matched and not kept. `rc` line: fields 2, 3 and 5. | It returns one record per `launch` line. It joins an `rc` line to the first `launch` line of the same tag that has no `rc` line yet. It adds the date of the folder name to both times. |
| build_facts.py [Ref14] | The record of `read_launches` for each of the nine folders. | It sorts the parts by launch time. It computes `gap_s`: the seconds from the end of the part before to this launch. The end of an rx.sh folder is the time of its `rc` line. It writes field 6 and the launch time into the fields `load1_at_launch` and `launch_utc` of each record of the nine folders in facts.json (one record per timed interval). It runs the checks 5, 9, 15 and 22 (see below). |
| facts_text.py [Ref15] | Launch time, the three load averages, runnable / all tasks, logins. | It writes the table of the load at launch in FACTS.md. |
| facts_text4.py [Ref18] | The 1-minute and the 5-minute load average of the two `launch` lines of control I. The launch times, the load at launch and `gap_s` of part L and of control I, as build_facts.py computed them. | It stops with an error when a 1-minute value of control I is not below 1.0 tasks, or when a 5-minute value of control I is not above 1.0 tasks, or when `gap_s` of a control I launch is not above 60 s. It writes the launch times, the loads and `gap_s` into the table of section 4.6 of FACTS.md. |
| make_report.py [Ref16] | The lines that start with `rc `. The text after ` args ` of the `launch` line. | It stops with an error unless each of the nine files has exactly one line that starts with `rc ` and one that starts with `rc 0 `. It stops with an error unless the argument text is equal to the argument text of the spec file. |

The checks of build_facts.py that use this file, with their results in FACTS.md [Ref17]:

- Check 5: logins = 0 in 9 of 9 `launch` lines. Result: pass.
- Check 9: one `launch` line with `rc 0` per folder. Result: pass.
- Check 15: tag and arguments of the `launch` line are equal to the spec file. Result: pass.
- Check 22: the number of runnable tasks at the 9 bwx12 launches (field 9, the part before the `/`). The check passes when no count is above 2 tasks. The value 2 is the limit of the wait loop of ra.sh (the script of part A), and build_facts.py reads it from ra.sh. The check also tests the `runnable` values of the three probe.txt files of part A (probe.txt is the state record that ra.sh writes into its folder). The check reports 1 task at the 9 bwx12 launches. Result: pass.

stat_bwx.py and stat_k120.py (the two scripts for quick statistics) do not read this file.

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
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0).
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg [Ref4]). "Load at launch" is the 1-minute value read directly before a process starts. The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **Run log**: the file that holds the standard output and the error output of go.sh or of go2.sh [Ref19]. The two run logs are `go-T72-20261117T221209Z.log` and `go2-T72-20261117T222335Z.log` in the folder `R` [Ref12]. rx.sh inherits both outputs from the driver script. So the lines that rx.sh prints are in the run log.
- **rx.sh**: the runner script of parts L and C and of control I. It reads a spec file, launches one bwx12 process per line and writes `env.txt`, `launches.txt`, `stderr.txt` and one csv file per process.
- **go.sh, go2.sh**: the two driver scripts of the rerun. go.sh runs the three sessions. go2.sh runs control I. Both call rx.sh.
- **Result folder**: the folder that one call of rx.sh creates. Its name is `w120-<name>-<UTC time>`. The name is `T72L<s>` for part L of session s, `T72C<s>` for part C and `T72I<i>` for run i of control I. `T72C4` is one more part C process that go.sh runs after session 3.
- **Spec file**: the input of rx.sh. Each line holds a tag, the character `|` and the arguments of one bwx12 process.
- **Tag**: the name of one process inside a result folder: `a6456`, `cfwd` or `crev` in the nine folders.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. rx.sh stops when this file exists.
- **Exit status**: the number that a process returns to the shell when it ends. 0 means success.
- **Standard output, standard error**: the two output streams of a process. bwx12 prints its result rows to the standard output and its messages to the standard error.
- **taskset**: the Linux tool that starts a command on a given list of CPUs.
- **UTC**: Coordinated Universal Time, the time zone of all times in these files.
- **PID**: the number that Linux gives to a process.
- **Csv file**: the file `<tag>.csv` of a result folder. It holds the result rows that bwx12 prints. An I row holds one timed interval. A T row holds the values of one thread in one timed interval.
- **facts_data.py, build_facts.py, facts_text.py, facts_text4.py**: the scripts that read the raw files of the rerun and write the facts sheet. The facts sheet is `facts.json` (data) and `FACTS.md` (text) in the folder `S`.
- **make_report.py**: the script that builds the HTML report of the rerun.
- **Folder letters**: `R` = `/home/jhan/workspace/titan/cache-perf/crb/results`. `S` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17`. `W15` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15`. `BWX12` = `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15`. On CRB the folder `R` was `~/cache-perf/results`.

</details>

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`, lines 11 to 21: the loop over the lines of the spec file (read of tag and arguments, test of the marker file, wait, 5 s sleep, `launch` line, start of the process, test once per second, `rc` line).
- [Ref2] The same file, line 16 (the `echo` that writes the `launch` line) and line 17 (the start of the process with `taskset -c 0-119`, the csv file `<tag>.csv`, the file `stderr.txt`).
- [Ref3] The same file, line 19 (the test once per second with `kill -0`, and the stop when the marker file appears) and line 20 (`wait`, then the `echo` that writes the `rc` line).
- [Ref4] External source: Linux manual page proc_loadavg(5) (older releases: proc(5), entry /proc/loadavg), read at `https://man7.org/linux/man-pages/man5/proc_loadavg.5.html` on 2026-11-21. It gives the five fields of `/proc/loadavg`. No manual page is installed on the server of this task.
- [Ref5] GNU coreutils manual, file `/usr/share/info/coreutils.info.gz` on the server of this task (coreutils 8.32): section 20.6 (`who` prints one line per user who is logged on) and section 21.1 (`date`: `-u` prints Universal Time, `%T` is the 24-hour time hh:mm:ss). The versions of `who` and `date` on CRB were not checked (no ssh in this task).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: line 3125 (`return 0` at the end of `main`), lines 3007 and 3014 (`return 2` in `main` after a message), the 26 lines that hold `exit(2)`, and lines 2912 to 2924 (the early returns of `main` for `--trial`, `--selftest` and `--list`). `bwx12_selftest.c` in the same folder, lines 683 and 710: the function `selftest` returns 2, 1 or 0.
- [Ref7] Local test on the server of this task (GNU bash 5.1.16, taskset of util-linux 2.37.2), in the scratch folder of this task: `wait` gave 143 for a process ended by the signal TERM, 7 for a process that ended with `exit 7`, and 127 for `taskset -c 0` with a binary that does not exist. `taskset -c 0` with a file that has no execute permission printed `Permission denied` and ended with status 126. `taskset -c 99999 true` (a CPU that does not exist) printed `failed to set pid <n>'s affinity: Invalid argument` and ended with status 1. A command name that does not exist, started in the background, printed `<name>: command not found`, and `wait` gave 127. The command `true`, started in the background with an output file in a folder that does not exist (first as the target of `>`, then as the target of `2>>`), made bash print `No such file or directory`, and `wait` gave 1 in both cases. The versions of bash and taskset on CRB were not checked (no ssh in this task).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: line 18 (function `fail`: prints `FAILED:`, prints a state line, ends with status 1), line 28 (the comment with the reason), line 29 (function `rxok`), lines 30 to 34 (function `runx`), lines 43, 44 and 46 (the calls of `runx`).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`, line 22: the last line of the script. It prints `done <folder>`, the number of lines of `launches.txt` that are not empty, the `rc` lines that do not start with `rc 0`, the size of `stderr.txt` in bytes and the first 600 bytes of `stderr.txt`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sh`: line 23 (function `rxok`, the same text as in go.sh), lines 30 and 31 (call of rx.sh, then `rxok`) and lines 3 to 5 (the comment: in go.sh every bwx12 process started about 5 s after other 120-thread work).
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`: lines 133 and 134 (patterns `LAUNCH` and `RC`), lines 137 to 156 (function `read_launches`), lines 68 to 74 (function `clock`: adds the date of the folder name to a time).
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log` (42 lines): the state lines (for example line 8: `users 0` and `11 jhan`), the 7 `done` lines of rx.sh folders, each followed by the lines `2` and `0`, and the last line `ALLDONE`. `/home/jhan/workspace/titan/cache-perf/crb/results/go2-T72-20261117T222335Z.log` (14 lines): the same for the 2 folders of control I.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`, lines 9 to 13: the two kinds of rate. For the bwx runners the rate is the sum over the T rows (threads) of bytes / elapsed_s / 1e9. Lines 356 to 383 (function `bwx_intervals`): the sum is made for each interval (round, position, kernel).
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`: lines 82 to 86 (call of `read_launches` per folder), lines 95 to 104 (order in time and `gap_s`), lines 176 to 180 (`load1_at_launch`, `launch_utc`), lines 687 to 694 (check of the logins), lines 713 to 715 (check of the `rc` line), lines 742 to 746 (check of tag and arguments), lines 787 to 797 (check of the runnable tasks).
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`, lines 865 to 887: the table of the load at launch and the sentences below it.
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`: lines 884 to 886 (one `rc 0` line per folder), lines 1188 to 1192 (function `launch_args`), lines 1201 and 1207 (the argument text against the spec files).
- [Ref17] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`, lines 217, 221, 227 and 234: the results of the checks 5, 9, 15 and 22.
- [Ref18] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`, lines 895 to 901 (the test of the load averages and of `gap_s` of control I) and lines 1049 to 1067 (launch times, loads and `gap_s` in the table of section 4.6).
- [Ref19] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the record of the Claude Code session of 2026-11-17. This file lies outside the project folder. No script of the folder `S` holds the command that started the run. Line 313 of the record holds the command for go.sh, and line 365 holds the command for go2.sh. Each command was sent with ssh as user jhan. Its start part is `nohup setsid <script> > <log file> 2>&1 < /dev/null &`. The part `> <log file> 2>&1` sends the standard output and the error output of the script to the log file. The command then waits for the end of the script. Lines 336 and 378 hold the output of the two commands, with `go.sh exit status 0` and `go2.sh exit status 0`.
