# `go2.sh` explained

- Source file: `go2.sh` in this folder (Bash script, 35 lines, 2697 bytes).
- sha256 of the source when this page was built: `38edfa540997d706fa0cfb71e27d8c592122f27bf4fb7f1e1f91bfb197f02742`.
- Role in the whole-chip test: Driver of control I: the part L line twice, each from an idle machine.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

go2.sh runs the part L line (`like.spec`) two more times through `rx.sh`. Before each of the two processes it waits until the 1-minute load average is below 1.0.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rerun**: the whole-chip read test of 2026-11-17, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process**: a process is one start of a benchmark binary.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Idle start**: a launch at a 1-minute load average below 1.0.
- **Spec file**: a text file that `rx.sh` reads as its input. Each line is `tag|arguments of the binary` and gives one process. The tag becomes the name of the csv file of that process.
- **csv file**: a text file whose lines hold values separated by commas.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. The messages of go2.sh, `ra.sh` and `rx.sh` do not say what the file stands for. None of the scripts that test the file says who creates it. Since 2026-11-24 the message in line 20 of go.sh says what the file stands for: Jeremy or someone else is using CRB. Jeremy is another user of CRB. The page `go.sh.md` in this folder (the explanation of go.sh) names the notes that say this. The facts sheet of the rerun says that another user creates it during a performance test [Ref8].
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks, for example `1/1013` [Ref7].
- **Runnable tasks**: the number before the slash in the fourth field of `/proc/loadavg`: the processes and threads that are runnable at the moment of the reading [Ref7].
- **Governor**: the Linux policy that sets the CPU frequency.
- **Transparent huge pages (thp)**: a Linux feature that can place a buffer on 2 MiB pages.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **rc, exit status**: the number that a process returns when it ends. 0 means success. `launches.txt` writes it as `rc`.
- **launches.txt, launch line, rc line**: `launches.txt` is a file that `rx.sh` writes in each of its result folders. `rx.sh` appends a `launch` line directly before it starts a process: the tag, the time, the content of `/proc/loadavg`, the number of logins and the arguments. It appends an `rc` line after the process has ended: the exit status, the tag and the time.
- **Process id (pid)**: the number that Linux gives to a process.
- **Process group**: a set of processes that one signal can reach together. The group has the process id of its leader as its number.
- **File descriptor**: the number under which a process holds an open file.
- **CPU list**: the CPUs on which Linux may run a process (its CPU affinity).
- **taskset**: a Linux tool. `taskset -c 0-119 COMMAND` starts a command that may run on the CPUs 0 to 119 only. `taskset -cp PID` prints the CPU list of a running process.
- **Start command**: the command line that started go2.sh on CRB. It is not part of a script. An AI agent (Claude Code) ran the rerun, and the saved record of its commands holds this command line [Ref10].
- **UTC**: Coordinated Universal Time. All times of the run are written in UTC.

</details>

## Main flow

1. Set `set -u`, the paths on CRB, the two expected sha256 values and the expected boot id (the same values as in go.sh) (lines 6-12).
2. Define the helpers `state` (prints one state line) and `fail` (prints the reason and ends the run with exit status 1) (lines 13-14).
3. Print the process id of go2.sh (line 15).
4. Run the checks: marker file, lock file, sha256 of `rx.sh` and of bwx12, presence of `like.spec`, boot id, MemTotal. Each failed check calls `fail` (lines 16-22).
5. Define `rxok` (tests the `rc` line that `rx.sh` wrote) and `waitidle` (waits at most 15 min for a 1-minute load average below 1.0) (lines 23-25).
6. Print the first state line (line 26).
7. Twice: wait for an idle machine, print a state line, run `rx.sh` with `like.spec` (names `T72I1` and `T72I2`), test the `rc` line, print a state line (lines 27-33).
8. Print the last state line and `ALLDONE` (lines 34-35).

## Behavior a reader must know

- go2.sh measures nothing itself. It reads no clock for a rate and computes no rate. All timed intervals are inside the binary bwx12. While bwx12 runs, go2.sh only waits for `rx.sh`.
- `Idle` is a rule on the 1-minute load average only. In the rerun the two `idle before` state lines show 1-minute values of 0.95 and 0.99. The 5-minute values in the same two lines are 36.39 and 21.40 [Ref1].
- bwx12 does not start at the idle test. `rx.sh` first waits until at most 2 tasks are runnable, and then 5 s more [Ref2]. In the rerun the two launch lines (22:27:05 and 22:32:32) are 5 s after the two idle state lines (22:27:00 and 22:32:27). The launch lines show 1-minute load averages of 0.87 and 0.91 [Ref1] [Ref6].
- Time since the 120-thread work before, in the rerun: the first control process started 287 s after the end of the last process of go.sh (22:22:18 to 22:27:05). The second started 265 s after the end of the first (22:28:07 to 22:32:32). These are the times of the `rc` lines and the `launch` lines [Ref6].
- A failed check stops the whole run with exit status 1 (function `fail`, line 14). go2.sh uses the lock file of go.sh. So it cannot run while go.sh runs.
- go2.sh does not print the Linux kernel command line, the governors, the huge page settings or the CPU list of its shell. go.sh prints them [Ref9].
- How go2.sh was started on CRB: no script of the run folder holds the command. An AI agent (Claude Code) ran the rerun. Its transcript (the saved record of its commands and their outputs) holds the command [Ref10]. The agent sent one command line from its server to CRB with `ssh` (the remote login tool), as the user `jhan`. The part that starts go2.sh reads: `L=~/cache-perf/results/go2-T72-$(date -u +%Y%m%dT%H%M%SZ).log; nohup setsid ~/cache-perf/w120-7200-20261117/go2.sh > $L 2>&1 < /dev/null &`.
- What the start command sets: `> $L 2>&1` sends the standard output and the error output of go2.sh to the log file [Ref1]. go2.sh itself names no log file. `< /dev/null` gives go2.sh an empty input. `nohup` starts go2.sh with the hangup signal ignored. The hangup signal tells a program that its terminal or connection was closed. `setsid` makes go2.sh the leader of a new process group [Ref11]. So the `kill` command that line 15 prints reaches go2.sh and its child processes.
- Insufficient data: the CPU list of the shell of go2.sh in the rerun. The start command holds no `taskset` [Ref10]. go2.sh does not print the list. A line `taskset -cp $$` in go2.sh would resolve it for a later run. For comparison: the start command of go.sh had the same form [Ref10]. It ran about 11 min earlier in the same boot. The log of go.sh shows the list `0-119` for its shell [Ref12].
- Is the local go2.sh the script that ran: the log of go2.sh and the files that the run wrote to its result folders hold no checksum of go2.sh. The transcript holds the command that copied the files to CRB [Ref13]. The agent wrote go2.sh on its server and wrote its sha256 to the file `go2.sha`. It copied both files to CRB. There `sha256sum -c go2.sha` printed `go2.sh: OK`, about 5 s before the start command. The transcript holds no command of the agent between this test and the start command. The local go2.sh still has the sha256 of `go2.sha` (tested with `sha256sum -c` on 2026-11-21) [Ref14].
- What `users` in a state line shows: the number of lines that `who` prints. After the start of go2.sh the start command waited on CRB for the end of go2.sh (`wait $pid`). Then it printed the exit status and the log [Ref10]. So the `ssh` connection of the start command was open during the whole run. All 6 state lines show `users 0` [Ref1]. So `who` did not list this connection. `users 0` does not show that no connection to CRB was open.

## Call sequence in the whole-chip test

- `go2.sh` (line 1): control I: checks, then two times wait and one bwx12 process
  - `fail` (line 14): only when a check fails: state line, then exit status 1
  - `state` (line 13): state line at the start, before and after each process, at the end
  - `waitidle` (line 25): waits for a 1-minute load average below 1.0
  - `rx.sh`: checks, wait, starts bwx12 on CPUs 0-119, writes the rc line
    - `bwx12.c:main`: one process: 120 threads run the kernel sequence of like.spec
      - `bwx12.c:k_oldread`: old read kernel, first in the sequence
      - `bwx12.c:k_asmread`: hand-written load-only loop, second in the sequence
      - `bwx12.c:k_read_nop96, k_read_nop256, k_read_1pl`: test loops, third to fifth in the sequence
  - `rxok` (line 23): tests the rc line in launches.txt

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `state` | 13-13 | Prints one state line: label, time, boot id, MemTotal, load, logins, marker file, processes per user. | - | no |
| `fail` | 14-14 | Prints `FAILED:` and the message, prints a state line, ends go2.sh with exit status 1. | `state` | no |
| `rxok` | 23-23 | Tests that `launches.txt` of the newest result folder of that name holds exactly one `rc` line, with status 0. | - | no |
| `waitidle` | 25-25 | Tests every 5 s, at most 180 times, whether the 1-minute load average is below 1.0. Stops the run after 15 min. | `fail` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/go2.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (43 lines, 3608 bytes, sha256 `fe2f0a3277a942f76a73fd24432363bc44c132ad0e6a817c9522111d7af3dca0`).
- The other sections of this page describe an older text of the file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sh` (35 lines, sha256 `38edfa540997d706fa0cfb71e27d8c592122f27bf4fb7f1e1f91bfb197f02742`). Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

Line numbers of the older text and of the text shown here:

| Older text | Text shown here | Change |
|---|---|---|
| lines 1 to 5 | lines 1 to 5 | equal |
| (none) | lines 6 to 7 | added |
| lines 6 to 10 | lines 8 to 12 | equal |
| lines 11 to 12 | lines 13 to 18 | changed |
| lines 13 to 17 | lines 19 to 23 | equal |
| line 18 | line 24 | changed |
| lines 19 to 20 | lines 25 to 26 | equal |
| line 21 | (none) | removed |
| line 22 | line 27 | equal |
| (none) | line 28 | added |
| lines 23 to 31 | lines 29 to 37 | equal |
| (none) | line 38 | added |
| lines 32 to 34 | lines 39 to 41 | equal |
| (none) | line 42 | added |
| line 35 | line 43 | equal |

### Header comment (lines 1 to 7)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# go2.sh - control for the rerun of 2026-11-17: the 120-thread line of r8.spec (like.spec), started from an idle machine, twice.` | Comment: the name of the script and its task. `go2.sh` is a control for the rerun of 2026-11-17. It runs the 120-thread line of the spec file `r8.spec` twice, each time from an idle machine. The file `like.spec` holds that line. It is equal to the first line of `r8.spec`. |
| 3 | `# Reason: in go.sh every bwx12 process started about 5 s after other 120-thread work. The earlier runs of this line` | Comment: the reason for the control. By the comment, every `bwx12` process in `go.sh` started about 5 s after other 120-thread work. `rx.sh` pauses 5 s before each launch. The sentence goes on in line 4. |
| 4 | `# (w120-R8 at 8000 MT/s, w120-w120-F72d12 at 7200 MT/s) started from an idle machine (1-minute load average 0.00 and 0.34).` | Comment, continued: the earlier runs of this line started from an idle machine. `w120-R8` (at 8000 MT/s) and `w120-w120-F72d12` (at 7200 MT/s) are the result folders of those earlier runs. Each of the two folders holds 5 launch lines. The first one has the arguments of `like.spec`. These two launch lines show the 1-minute load averages 0.00 and 0.34 [Ref5]. |
| 5 | `# "Idle" here = 1-minute load average below 1.0. No root. CPUs 0-119 only. rx.sh stops if /tmp/positron-perf.RUNNING exists.` | Comment: `Idle` here means a 1-minute load average below 1.0. The run needs no root rights and uses the CPUs 0 to 119 only. `rx.sh` stops when the marker file exists. |
| 6 | `# rx.sh records the clock rate of the cores, the throttle flags and the power of each step (hw.sh).` | Comment: `rx.sh` records the clock rate of the cores, the throttle flags and the power of each step, with the functions of the file `hw.sh`. A step is one call of `rx.sh`. Hardware record: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24. A throttle flag is such a sign: the firmware sets it when a thermal, power or current limit made a core deliver less than Linux requested. |
| 7 | `# HW=off: no such record. HW_POWER=off: no power record. Exit status 4: all steps ran, a hardware record is incomplete.` | Comment: two settings and one exit status. `HW=off`: `rx.sh` makes no hardware record. `HW_POWER=off`: the hardware record is made without the tool `atx`. By the comment it then has no power record. `atx` is Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware. Exit status 4 of `go2.sh`: all steps ran, and the hardware record of at least one step is incomplete (line 42). |

### Settings and the helper `hwcount` (lines 8 to 18)

| Line | Source | Explanation |
|---:|---|---|
| 8 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. Each check below calls `fail` by itself. |
| 9 | `D=$HOME/cache-perf/w120-7200-20261117` | `D`: the folder on CRB that holds `like.spec`. Lines 9 to 14 are equal to the lines of `go.sh` that set the same six variables. |
| 10 | `RX=$HOME/cache-perf/w120-20261115/rx.sh` | `RX`: the path of the runner script `rx.sh`. |
| 11 | `BW=$HOME/cache-perf/bwx12-20261115/bwx12` | `BW`: the path of the binary `bwx12`. |
| 12 | `SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a` | `SHA`: the sha256 that the file `bwx12` must have. Line 25 tests it. |
| 13 | `RXSHA=42023e5e3246a97f6885f57262b9168eef3207e7da5dd4c44840e48e301422c9` | `RXSHA`: the sha256 that `rx.sh` must have. Line 24 tests it. The file `w120-2026-11-15/rx.sh` of the code repo has this sha256. It is the text of 2026-11-24, which calls the hardware record. The older text of `go2.sh` held the sha256 of the older `rx.sh` here. |
| 14 | `HWDIR=${HWDIR:-$HOME/cache-perf/hwwatch-20261124}` | `HWDIR`: the folder that holds `hw.sh`. When the caller has set the variable `HWDIR` to a value that is not empty, that value is kept. If not, the folder is `$HOME/cache-perf/hwwatch-20261124`. |
| 15 | `# Hardware record: ra.sh and rx.sh write it into the folder hw of each result folder. A failure in it does not stop a step.` | Comment: `ra.sh` and `rx.sh` write the hardware record into the folder `hw` of each result folder. `go2.sh` calls `rx.sh` only, not `ra.sh`. By the comment, a failure in the record does not stop a step. This holds only after the record has started. When the start of the record fails, `rx.sh` ends with exit status 7, and `go2.sh` then stops (line 36). |
| 16 | `# hwcount NAME counts the FAILED lines of the newest result folder NAME-<time>.` | Comment: `hwcount NAME` counts the lines that start with `FAILED` in the hardware record of the newest result folder `NAME-<time>`. After the start of the record, the functions of `hw.sh` write one such line for each failure. |
| 17 | `HWBAD=0` | `HWBAD`: the number of steps whose hardware record is incomplete. It starts at 0. The helper `hwcount` (line 18) adds 1 for each such step. Line 42 tests it. |
| 18 | `hwcount() { local d n; [ "${HW:-on}" = off ] && return 0; d=$(ls -d "$HOME"/cache-perf/results/"$1"-* 2>/dev/null \| tail -1); n=$(hw_failures "${d:-none}"); [ "$n" = 0 ] && return 0; HWBAD=$((HWBAD + 1)); echo "== hardware record of $1: FAILED lines: $n"; }` | Defines the helper `hwcount NAME`. It tests the hardware record of the step that has ended. `d` and `n` are local variables. With `HW=off` no record was made, and the helper returns at once. `${HW:-on}` gives `on` when `HW` is not set or empty. `ls -d` lists the result folders `NAME-<time>` in name order, and `tail -1` keeps the last one. The UTC time in the name puts the newest folder last. `2>/dev/null` discards the error message of `ls` when no folder matches. `hw_failures` (file `hw.sh`) prints the number of lines that start with `FAILED` in the file `hw/status.txt` of that folder, or `missing` when it finds no such file. `${d:-none}` gives it the word `none` when `ls` found no folder. When the answer is `0`, the helper returns. In every other case it adds 1 to `HWBAD` and prints a line that starts with `== hardware record of`, with NAME and the answer. The helper stops nothing. |

### Helpers `state` and `fail`, and the process id (lines 19 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 19 | `state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo \| tr -s ' ') load $(cat /proc/loadavg) users $(who \| wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] && echo present \|\| echo absent) processes per user: $(ps -eo user= \| sort \| uniq -c \| tr -s ' ' \| tr '\n' ';')"; }` | Defines the helper `state LABEL`. It prints one state line and stops nothing. The line holds `==`, the label, the UTC time (`date -u`), the boot id and the `MemTotal` line of `/proc/meminfo`. Then it holds the content of `/proc/loadavg`: the three load averages, the runnable tasks and all tasks in the form `1/1013`, and the newest process id [Ref7]. Then it holds the number of logins: `who` prints one line per login, and `wc -l` counts the lines. Then it holds `present` or `absent` for the marker file. The last part is the number of processes of each user: `ps -eo user=` prints the user of every process, and `sort` with `uniq -c` counts equal lines. `tr -s ' '` reduces each run of spaces to one space. `tr '\n' ';'` joins the counts with `;`. |
| 20 | `fail() { echo "FAILED: $1"; state abort; exit 1; }` | Defines the helper `fail MESSAGE`. It prints `FAILED:` and the message. Then it prints a state line with the label `abort`. Then it ends `go2.sh` with exit status 1. Every failed check of `go2.sh` ends here, and no later step runs. |
| 21 | `echo "go2.sh pid $$ (stop everything: kill -TERM -- -$$)"` | Prints the process id of `go2.sh` and a command that stops the run. `kill -TERM -- -PID` sends the termination signal to every process of the process group with that number. The command reaches `go2.sh` and its child processes only when `go2.sh` is the leader of its process group. `go2.sh` does not make itself the leader. In the rerun the start command ran `go2.sh` through the tool `setsid` [Ref10]. This tool starts a program as the leader of a new process group [Ref11]. So `go2.sh` was the leader in the rerun. |

### Checks before the first step (lines 22 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"` | Check of the marker file: when the file exists (`-e`), `fail` stops the run with `RUNNING file present`. The helper `waitidle` (line 31) tests the file again at each of its tries. `rx.sh` tests it before the process and once per second while the process runs [Ref2]. `go2.sh` does not say who creates the file or what the file stands for. |
| 23 | `exec 9> "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 \|\| fail "another go.sh holds the lock"` | Lock against a second run. `exec 9> FILE` opens the file `go-T72.lock` for writing as file descriptor 9 of the shell. It creates the file when it is missing. `flock -n 9` asks for an exclusive lock on that file and does not wait. When another process holds the lock, or the lock file could not be opened, `fail` stops the run with `another go.sh holds the lock`. `go.sh` uses the same lock file. So `go2.sh` cannot run at the same time as `go.sh`, and a second `go2.sh` fails here too. The lock lasts as long as file descriptor 9 is open: until `go2.sh` and the child processes that inherited it have ended. |
| 24 | `echo "$RXSHA  $RX" \| sha256sum -c - > /dev/null \|\| fail "rx.sh is not the script of 2026-11-24"` | Checksum check of `rx.sh`. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the file and compares the two values. `> /dev/null` discards its report. When the values differ or the file cannot be read, `fail` stops the run. The message names the expected text: the `rx.sh` of 2026-11-24. |
| 25 | `echo "$SHA  $BW" \| sha256sum -c - > /dev/null \|\| fail "bwx12 is not the binary of 2026-11-15"` | The same check for the binary `bwx12`, with the checksum of line 12. By the message, the file must be the binary of 2026-11-15. The build record of `bwx12` lists the value of `SHA` for the file `bwx12` [Ref4]. The binary itself is not in the local folders. |
| 26 | `[ -s "$D/like.spec" ] \|\| fail "missing $D/like.spec"` | File check: when `like.spec` is missing or empty (`-s`), `fail` stops the run with `missing` and the path. `go2.sh` does not test the checksum of `like.spec`. In the rerun the `launch` lines of the two control processes hold the arguments of the local `like.spec` (compared with `diff` on 2026-11-21) [Ref6]. |
| 27 | `[ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] \|\| fail "MemTotal below 395000000 kB: not 12 modules"` | Memory size check. `awk` prints the second field of the `MemTotal` line of `/proc/meminfo`, a value in kB. When the value is below 395000000 kB (about 376.7 GiB), `fail` stops the run. By the message, a lower value means: not 12 modules. The script does not say how the limit was chosen. In the rerun each of the 6 state lines shows 395392808 kB [Ref1]. |
| 28 | `if [ "${HW:-on}" != off ]; then . "$HWDIR/hw.sh" \|\| fail "cannot read $HWDIR/hw.sh"; hw_check \|\| fail "hardware record not usable (the lines above say why)"; fi` | Test of the hardware record, before any step. With `HW=off` the line does nothing. In every other case the command `.` reads the file `hw.sh` into this shell. That file defines the functions `hw_check` and `hw_failures`, which `go2.sh` calls. When the file cannot be read, `fail` stops the run. Then `hw_check` tests the tools of the record: the frequency files of Linux for CPU 0, a trial of the frequency sampler on CPU 119 and, when `HW_POWER` is `require`, a trial collection of `atx` of 5 s. These values are the defaults of `hw.sh`. The frequency sampler is the program of the hardware record that reads the clock rate of the cores during a step, once per second by default. When a test fails, `hw_check` prints the reason and `fail` stops the run. After a success `hw_check` exports the variable `HW_CHECKED`. With it, the later calls of `hw_check`, which `rx.sh` makes through `hw_init`, return at once and do not repeat the trials. |

### Helpers `rxok` and `waitidle` (lines 29 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null \| tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }` | Defines the helper `rxok NAME`. Its text is equal to `rxok` in `go.sh`. It tests the exit status that `rx.sh` recorded for the `bwx12` process. `ls -d` lists the `launches.txt` files of all result folders `w120-NAME-<time>` in name order, and `tail -1` keeps the last one. The time in the folder name puts the newest folder last. `2>/dev/null` discards the error message of `ls` when no file matches. The helper succeeds only when three tests pass. Test 1: a file was found (`-n`). Test 2: the file holds exactly 1 line that starts with `rc` and a space. Test 3: it holds exactly 1 line that starts with `rc 0` and a space. `grep -c` counts the matching lines. `rx.sh` writes one line `rc <exit status> <tag>` per process. It ends with status 0 also when `bwx12` failed [Ref2]. |
| 30 | `# wait until the 1-minute load average is below 1.0 (at most 15 min)` | Comment: the task of `waitidle` (line 31). It waits until the 1-minute load average is below 1.0, for at most 15 min. |
| 31 | `waitidle() { local i; for i in $(seq 180); do [ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"; awk '{exit !($1 < 1.0)}' /proc/loadavg && return 0; sleep 5; done; fail "1-minute load average not below 1.0 after 15 min"; }` | Defines the helper `waitidle`. It tries up to 180 times (`seq 180`). `local i` keeps its counter apart from the `i` of the loop of line 33. At each try: when the marker file exists, `fail` stops the run with `RUNNING file present`. Then `awk` reads `/proc/loadavg`. Its program `exit !($1 < 1.0)` ends `awk` with status 0 when the first field, the 1-minute load average, is below 1.0. In that case the helper returns and the run goes on. If not, the helper sleeps 5 s and tries again. After 180 tries (180 times 5 s = 15 min) `fail` stops the run. The test reads the 1-minute value only. It does not test the 5-minute value or the number of runnable tasks. |

### The two control processes and the end (lines 32 to 43)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `state start` | Prints the first state line, with the label `start`. |
| 33 | `for i in 1 2; do` | Starts a loop that runs the same steps twice: `i` is 1, then 2. The two control processes get the names `T72I1` and `T72I2`. |
| 34 | `  waitidle` | Calls `waitidle` (line 31). It waits until the 1-minute load average is below 1.0, or stops the run after 15 min. |
| 35 | `  state "idle before T72I$i"` | Prints a state line with the label `idle before T72I<i>`. Here `<i>` stands for the number of the pass, 1 or 2. The line records the state of the machine directly after the idle test has passed. |
| 36 | `  bash "$RX" T72I$i "$BW" "$SHA" < "$D/like.spec" \|\| fail "rx.sh T72I$i rc $?"` | Runs `rx.sh` with `bash` and three arguments: the name `T72I<i>`, the path of `bwx12` and its expected sha256. The spec file is the input of `rx.sh` (`< "$D/like.spec"`). So `rx.sh` runs one `bwx12` process with the arguments of `like.spec` [Ref3]. `go2.sh` waits until `rx.sh` has ended. On a non-zero exit status, `fail` stops the run and prints that status (`$?`). `rx.sh` adds its own wait before the launch: until at most 2 tasks are runnable (at most 40 s), then 5 s [Ref2]. When more than 2 tasks are still runnable after the 40 s, `rx.sh` starts the process anyway. So `bwx12` starts 5 s or more after the idle test. The present text of `rx.sh` also starts the hardware record and takes its first snapshot before the 5 s. |
| 37 | `  rxok T72I$i \|\| fail "bwx12 T72I$i: exit status not 0 (launches.txt, stderr.txt)"` | Calls `rxok` (line 29). When it does not succeed, `fail` stops the run. The message names two files of the result folder to read: `launches.txt` and `stderr.txt`. |
| 38 | `  hwcount "w120-T72I$i"` | Tests the hardware record of this step. `hwcount` (line 18) reads the newest result folder `w120-T72I<i>-<time>`, the folder that `rx.sh` wrote in line 36. When the record holds `FAILED` lines or has no status file, `hwcount` adds 1 to `HWBAD` and prints one line. The run goes on in both cases. |
| 39 | `  state "after T72I$i"` | Prints a state line with the label `after T72I<i>`, after the process has ended. |
| 40 | `done` | Ends the loop of line 33. |
| 41 | `state end` | Prints the last state line, with the label `end`. |
| 42 | `[ "$HWBAD" = 0 ] \|\| { echo "DONE, but the hardware record of $HWBAD steps is incomplete (lines above that start with: == hardware record)"; exit 4; }` | Tests `HWBAD` (line 17) after the last state line. When it is not 0, the line prints `DONE, but the hardware record of N steps is incomplete`, where N is the value of `HWBAD`. The text in parentheses tells the reader to look at the lines above that start with `== hardware record`. Then `go2.sh` ends with exit status 4, and `ALLDONE` is not printed. When `HWBAD` is 0, `go2.sh` goes on to line 43. |
| 43 | `echo ALLDONE` | Prints `ALLDONE`. The script reaches this line only when no check called `fail` and line 42 did not end the script. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/go2-T72-20261117T222335Z.log`: log of go2.sh in the rerun: 6 state lines, each with `MemTotal: 395392808 kB` and `users 0`. The two `idle before` lines hold the times 22:27:00 and 22:32:27 and the loads `0.95 36.39 38.17` and `0.99 21.40 32.57`. The last line is `ALLDONE`.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: runner script. Marker tests: lines 7, 13 and 19. Wait rule: lines 14 and 15. The `rc` line: line 20. Exit status of the last command: line 22. sha256 of this copy: d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`: the spec file of part L and control I. It holds one line with the tag a6456. `--seq` gives the kernel order oldread,asmread,read_nop96,read_nop256,read_1pl.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: build record of bwx12. Line 20 lists the sha256 cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a for the file `bwx12`.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-R8-20261117T020549Z/launches.txt and /home/jhan/workspace/titan/cache-perf/crb/results/w120-w120-F72d12-20261117T200231Z/launches.txt`: line 1 of each file is the launch line of the tag a6456. It shows `load 0.00 0.00 0.00` (R8) and `load 0.34 0.09 0.03` (F72d12).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72I1-20261117T222700Z/launches.txt, /home/jhan/workspace/titan/cache-perf/crb/results/w120-T72I2-20261117T223227Z/launches.txt and /home/jhan/workspace/titan/cache-perf/crb/results/w120-T72C4-20261117T222136Z/launches.txt`: launch and rc lines. T72I1: launch 22:27:05 with load 0.87, rc 0 at 22:28:07. T72I2: launch 22:32:32 with load 0.91, rc 0 at 22:33:34. T72C4 (last process of go.sh): rc 0 at 22:22:18. In the launch lines of T72I1 and T72I2 the text after the word `args` is equal to the text after the `|` in the local like.spec.
- [Ref7] external source: Linux manual page proc(5), entry /proc/loadavg (meaning of the five fields).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Lines 38 to 89 hold its word list. The definitions under "Words used here" come from there.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: the driver script that ran before go2.sh in the rerun. Lines 35 to 38 print the Linux kernel command line, the governors, the huge page settings and the CPU list of its shell. Line 20 of this local file was edited on 2026-11-24 (the text of one message). The lines named here are unchanged.
- [Ref10] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the transcript of the AI agent (Claude Code) that ran the rerun on 2026-11-17, one JSON record per line. It lies outside the project folder. Line 365 holds the command that the agent ran at 22:23:35 UTC (clock of the agent's server): `ssh`, its options, the user name and the address of CRB, and in quotes the command line for CRB: `if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi; L=~/cache-perf/results/go2-T72-$(date -u +%Y%m%dT%H%M%SZ).log; nohup setsid ~/cache-perf/w120-7200-20261117/go2.sh > $L 2>&1 < /dev/null & pid=$!; echo "log $L pid $pid"; wait $pid; echo "go2.sh exit status $?"; cat $L`. Line 378 holds the output of that command, as the agent read it after the run. Its first two lines are `log /home/jhan/cache-perf/results/go2-T72-20261117T222335Z.log pid 15823` and `go2.sh exit status 0`. Line 1 of the go2.sh log shows the same process id. Line 313 holds the command that started go.sh, run at 22:12:08 UTC. It is the same command with `go-T72-` and `go.sh` in place of `go2-T72-` and `go2.sh`.
- [Ref11] external source: Linux manual pages setsid(1) and setsid(2). The tool `setsid` runs a program in a new Linux session. The process that creates a Linux session also becomes the leader of a new process group: its process group id is made the same as its process id.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log`: log of go.sh in the rerun. Line 5: `affinity of this shell: pid 4864's current affinity list: 0-119`. Its state lines hold the boot id 3bfc57a1-e235-4fe5-8c09-a94642f9b60b, the boot id of the go2.sh log.
- [Ref13] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the same transcript as Ref10. It lies outside the project folder. Line 353 holds a command that the agent ran at 22:23:30 UTC (clock of the agent's server). The command wrote the file go2.sh in the local run folder and wrote `go2.sha` with `sha256sum go2.sh > go2.sha`. It packed both files with `tar` (a tool that joins files into one stream) and sent them to CRB through `ssh`. On CRB it unpacked them in the folder `~/cache-perf/w120-7200-20261117` and ran `sha256sum -c go2.sha`. Line 354 holds the output with `go2.sh: OK`. Lines 355 to 364 hold no command. Line 365 holds the start command, run at 22:23:35 UTC.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sha`: one line: the sha256 of go2.sh, 38edfa540997d706fa0cfb71e27d8c592122f27bf4fb7f1e1f91bfb197f02742. `sha256sum -c go2.sha`, run in the local run folder on 2026-11-21, printed `go2.sh: OK`.
