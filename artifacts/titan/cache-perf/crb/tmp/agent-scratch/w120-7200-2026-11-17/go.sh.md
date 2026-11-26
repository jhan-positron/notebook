# `go.sh` explained, line by line

- Source file: `go.sh` in this folder (Bash script, 48 lines, 3665 bytes).
- sha256 of the source when this page was built: `d68cf6c0468abeb658765b950b9bd86b34ff9556070efcd954824f6e936da2bd`.
- The column "Source" of the table below is a copy of the source, made by a script. The column "Line" holds the line numbers of the source.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell [Ref13]. A Markdown viewer shows `|`.
- A longer page stood here until 2026-11-24. A copy is kept: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/explain-bash-2026-11-24/go.sh.md.before-explain-bash`. The copy also holds the call sequence, a table of the functions and more notes on the rerun.

## Short version: purpose

go.sh is the top-level script of the whole-chip rerun of 2026-11-17 on CRB (the Arm reference server under test). It first checks that the machine and the files are the expected ones. Then it runs three sessions of part A (`ra.sh`), part L and part C (both through `rx.sh`), and one more part C process at the end.

## Words used here

- **Rerun**: the run of the whole-chip test on 2026-11-17, at a memory speed of 7200 MT/s. By line 8 of go.sh, it is compared with earlier results at 8000 MT/s.
- **Whole-chip test**: a memory benchmark with 120 threads on the CPUs 0 to 119.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM, a plug-in memory board.
- **bwx12**: the benchmark binary of 2026-11-15 that parts L and C run.
- **Process**: one start of a benchmark binary.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A, part L, part C**: the three steps of a session. Lines 3 to 5 of go.sh describe them.
- **Spec file**: a text file that `rx.sh` reads as its input. Its line has the form `tag|arguments of the binary` and gives one process.
- **State line**: a line that go.sh prints with the time, the boot id, MemTotal, the load, the logins, the marker file and the processes per user.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. By the message of line 20 it means that Jeremy or someone else is using CRB.
- **Jeremy**: another user of CRB. Notes of 2026-10-30 say that the marker file is present during each time window that is reserved for the measurements of Jeremy [Ref10].
- **Boot id**: a random identifier that Linux creates once per boot [Ref9]. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports in the file `/proc/meminfo`, in kB.
- **Load**: the content of the file `/proc/loadavg`: three load averages, the number of runnable tasks and of all tasks, and the newest process id [Ref11].
- **Governor**: the Linux policy that sets the CPU frequency.
- **Transparent huge pages (thp)**: a Linux feature that can place a buffer on 2 MiB pages.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status (rc)**: the number that a process returns when it ends. 0 means success.
- **launches.txt**: a file that `rx.sh` writes in its result folder. It holds one line `rc <exit status> <tag>` per process [Ref3].
- **Process id**: the number that Linux gives to a process. `$$` is the process id of the shell that runs the script.
- **Process group**: a set of processes that one signal can reach together. The group has the process id of its leader as its number.
- **File descriptor**: the number under which a process holds an open file.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Start command**: the command line that started go.sh on CRB in the rerun. No script of the run folder holds it. The saved record of the AI agent (Claude Code) that ran the rerun holds it [Ref5].
- **UTC**: Coordinated Universal Time.

## Main flow

1. Set `set -u`, the paths on CRB, the two expected sha256 values and the expected boot id (lines 9-16).
2. Define the helpers `state` (prints one state line) and `fail` (prints the reason and ends the run with exit status 1) (lines 17-18).
3. Print the process id of go.sh (line 19).
4. Run the checks: marker file, lock file, sha256 of `rx.sh` and of bwx12, presence of `ra.sh` and of the spec files, boot id, MemTotal. Each failed check calls `fail` (lines 20-27).
5. Define the helpers `rxok` (tests the `rc` line that `rx.sh` wrote) and `runx` (one call of `rx.sh`, then `rxok`, then a state line) (lines 28-34).
6. Print the Linux kernel command line, the governors, the huge page settings, the CPU list of the shell and the first state line (lines 35-39).
7. For the sessions 1, 2 and 3: run part A with `ra.sh`, then part L with `like.spec`, then part C with `cfwd.spec` (session 2: `crev.spec`). Print a state line after each step (lines 40-45).
8. Run one more part C process with `crev.spec` (line 46).
9. Print the last state line and `ALLDONE` (lines 47-48).

## Behavior a reader must know

- go.sh measures nothing itself. It reads the clock only for the time in a state line (line 17). It starts `ra.sh` and `rx.sh` and waits for them.
- A failed check stops the whole run with exit status 1 (helper `fail`, line 18). go.sh deletes nothing. So the result folders that were written before the failure stay on disk.
- The script has no `set -e`. A failed command stops the run only where the line calls `fail`. Lines 35 to 38 do not call it.
- The boot check (line 26) compares with one fixed boot id. So in every boot other than the boot of the rerun, go.sh stops at line 26 or at an earlier check [Ref1] [Ref9].
- CPU list: go.sh sets none. `ra.sh` restarts itself under `taskset -c 0-119` [Ref2]. `rx.sh` starts bwx12 under `taskset -c 0-119` [Ref3].
- Source of the CPU list that line 38 printed in the rerun (`0-119`) [Ref1]: the start command holds no `taskset` [Ref5]. A child process starts with the CPU list of its parent [Ref8]. So the shell of go.sh got the list from the process that started it. An inspection of CRB on 2026-10-30 found the systemd setting `CPUAffinity=0-119` [Ref6]. systemd is the first process of the system. The setting gives this list to systemd and to every process that descends from it.
- The start command of the rerun: `L=~/cache-perf/results/go-T72-$(date -u +%Y%m%dT%H%M%SZ).log; nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null &` [Ref5]. Its parts:
  - `L=...`: the name of the log file, with the UTC time of the start. go.sh itself names no log file.
  - `> $L 2>&1`: the standard output and the error output of go.sh go to the log file.
  - `< /dev/null`: go.sh gets an empty input.
  - `nohup`: go.sh ignores the hangup signal. This signal tells a program that its terminal or connection was closed [Ref7].
  - `setsid`: go.sh becomes the leader of a new process group [Ref7]. So the `kill` command that line 19 prints reaches go.sh and its child processes.
  - `&`: the command runs in the background. The shell that started it does not wait before its next command.
- Two texts of go.sh: this page shows the local text. It differs from the text that ran in the rerun in the message of line 20 only. The old line was `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"`. The message was changed on 2026-11-24 [Ref12].

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that also had one row per line.
- Text shown: the file `w120-7200-2026-11-17/go.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (56 lines, 4516 bytes, sha256 `e0258ab34b6bbc462c9f862fc9f0192f0ec5ee8d7dcbd92caef111f071b66b7e`).
- The other sections of this page describe an older text of the file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh` (48 lines, sha256 `d68cf6c0468abeb658765b950b9bd86b34ff9556070efcd954824f6e936da2bd`). Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

Line numbers of the older text and of the text shown here:

| Older text | Text shown here | Change |
|---|---|---|
| lines 1 to 7 | lines 1 to 7 | equal |
| (none) | lines 8 to 9 | added |
| lines 8 to 13 | lines 10 to 15 | equal |
| lines 14 to 16 | lines 16 to 21 | changed |
| lines 17 to 21 | lines 22 to 26 | equal |
| line 22 | line 27 | changed |
| lines 23 to 25 | lines 28 to 30 | equal |
| line 26 | (none) | removed |
| line 27 | line 31 | equal |
| (none) | line 32 | added |
| lines 28 to 32 | lines 33 to 37 | equal |
| (none) | line 38 | added |
| lines 33 to 41 | lines 39 to 47 | equal |
| (none) | line 48 | added |
| lines 42 to 47 | lines 49 to 54 | equal |
| (none) | line 55 | added |
| line 48 | line 56 | equal |

### Header comment (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# go.sh - whole-chip rerun at 7200 MT/s. Three sessions. Each session runs, one after the other:` | Comment: the name of the script and the plan. The run has three sessions. Each session runs the parts A, L and C, one after the other. |
| 3 | `#   A: ra.sh            (the 120-thread part of the 2026-11-13 test, same binaries, whole-pass stop, 0.5 s)` | Comment, part A: `ra.sh` repeats the 120-thread part of the test of 2026-11-13 with the same binaries. `whole-pass stop, 0.5 s` names the stop rule of these binaries and the minimum length of one timed interval (`--min-ms 500` in `ra.sh`) [Ref2]. |
| 4 | `#   L: rx.sh like.spec  (runner bwx12, common stop, 6 s, the 120-thread line of r8.spec unchanged)` | Comment, part L: `rx.sh` runs bwx12 with the spec file `like.spec`. `common stop, 6 s` stands for the arguments `--stop common --min-ms 6000` of the spec file [Ref4]. The one line of `like.spec` is equal to the first line of the older spec file `r8.spec` [Ref4]. |
| 5 | `#   C: rx.sh cfwd.spec or crev.spec (bwx12: old C read, new C read, asm read; session 2 in reverse order)` | Comment, part C: `rx.sh` runs bwx12 with `cfwd.spec` or `crev.spec`. One process times three read loops: the old C loop, the new C loop and the assembly loop (`--seq oldread,read,asmread` in `cfwd.spec`) [Ref4]. `crev.spec` holds the reverse order. Session 2 uses it. |
| 6 | `# After session 3 one more C process runs in reverse order (2 forward and 2 reverse processes in total).` | Comment: after session 3, one more part C process runs in reverse order. Part C then has 2 processes in forward order and 2 processes in reverse order. |
| 7 | `# No root. CPUs 0-119 only. ra.sh and rx.sh stop if /tmp/positron-perf.RUNNING exists.` | Comment: the run needs no root rights and uses the CPUs 0 to 119 only. `ra.sh` and `rx.sh` stop when the marker file exists. |
| 8 | `# ra.sh and rx.sh record the clock rate of the cores, the throttle flags and the power of each step (hw.sh).` | Comment: `ra.sh` and `rx.sh` record the clock rate of the cores, the throttle flags and the power of each step, with the functions of the file `hw.sh`. A step is one call of `ra.sh` or of `rx.sh`. Hardware record: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24. A throttle flag is such a sign: the firmware sets it when a thermal, power or current limit made a core deliver less than Linux requested. |
| 9 | `# HW=off: no such record. HW_POWER=off: no power record. Exit status 4: all steps ran, a hardware record is incomplete.` | Comment: two settings and one exit status. `HW=off`: `ra.sh` and `rx.sh` make no hardware record. `HW_POWER=off`: the hardware record is made without the tool `atx`. By the comment it then has no power record. `atx` is Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware. Exit status 4 of `go.sh`: all steps ran, and the hardware record of at least one step is incomplete (line 55). |
| 10 | `# 8000 MT/s baselines for the comparison: fixed list in baselines-and-rules.txt (same folder), fixed before this run.` | Comment: the rerun is compared with earlier results at 8000 MT/s. The file `baselines-and-rules.txt` lists them. By the comment, the list was fixed before this run. go.sh never reads that file. |

### Settings and the helper `hwcount` (lines 11 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 12 | `D=$HOME/cache-perf/w120-7200-20261117` | `D`: the folder on CRB that holds `ra.sh` and the three spec files. |
| 13 | `RX=$HOME/cache-perf/w120-20261115/rx.sh` | `RX`: the path of the runner script `rx.sh`. |
| 14 | `BW=$HOME/cache-perf/bwx12-20261115/bwx12` | `BW`: the path of the binary bwx12. |
| 15 | `SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a` | `SHA`: the sha256 that the file bwx12 must have. Line 28 tests it. |
| 16 | `RXSHA=42023e5e3246a97f6885f57262b9168eef3207e7da5dd4c44840e48e301422c9` | `RXSHA`: the sha256 that `rx.sh` must have. Line 27 tests it. The file `w120-2026-11-15/rx.sh` of the code repo has this sha256. It is the text of 2026-11-24, which calls the hardware record. The older text of `go.sh` held the sha256 of the older `rx.sh` here. |
| 17 | `HWDIR=${HWDIR:-$HOME/cache-perf/hwwatch-20261124}` | `HWDIR`: the folder that holds `hw.sh`. When the caller has set the variable `HWDIR` to a value that is not empty, that value is kept. If not, the folder is `$HOME/cache-perf/hwwatch-20261124`. |
| 18 | `# Hardware record: ra.sh and rx.sh write it into the folder hw of each result folder. A failure in it does not stop a step.` | Comment: `ra.sh` and `rx.sh` write the hardware record into the folder `hw` of each result folder. By the comment, a failure in the record does not stop a step. This holds only after the record has started. When the start of the record fails, `ra.sh` and `rx.sh` end with exit status 7, and `go.sh` then stops (line 36 and line 47). |
| 19 | `# hwcount NAME counts the FAILED lines of the newest result folder NAME-<time>.` | Comment: `hwcount NAME` counts the lines that start with `FAILED` in the hardware record of the newest result folder `NAME-<time>`. After the start of the record, the functions of `hw.sh` write one such line for each failure. |
| 20 | `HWBAD=0` | `HWBAD`: the number of steps whose hardware record is incomplete. It starts at 0. The helper `hwcount` (line 21) adds 1 for each such step. Line 55 tests it. |
| 21 | `hwcount() { local d n; [ "${HW:-on}" = off ] && return 0; d=$(ls -d "$HOME"/cache-perf/results/"$1"-* 2>/dev/null \| tail -1); n=$(hw_failures "${d:-none}"); [ "$n" = 0 ] && return 0; HWBAD=$((HWBAD + 1)); echo "== hardware record of $1: FAILED lines: $n"; }` | Defines the helper `hwcount NAME`. It tests the hardware record of the step that has ended. `d` and `n` are local variables. With `HW=off` no record was made, and the helper returns at once. `${HW:-on}` gives `on` when `HW` is not set or empty. `ls -d` lists the result folders `NAME-<time>` in name order, and `tail -1` keeps the last one. The UTC time in the name puts the newest folder last. `2>/dev/null` discards the error message of `ls` when no folder matches. `hw_failures` (file `hw.sh`) prints the number of lines that start with `FAILED` in the file `hw/status.txt` of that folder, or `missing` when it finds no such file. `${d:-none}` gives it the word `none` when `ls` found no folder. When the answer is `0`, the helper returns. In every other case it adds 1 to `HWBAD` and prints a line that starts with `== hardware record of`, with NAME and the answer. The helper stops nothing. |

### Helpers `state` and `fail`, and the process id (lines 22 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo \| tr -s ' ') load $(cat /proc/loadavg) users $(who \| wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] && echo present \|\| echo absent) processes per user: $(ps -eo user= \| sort \| uniq -c \| tr -s ' ' \| tr '\n' ';')"; }` | Defines the helper `state LABEL`. It prints one state line and stops nothing. The line holds `==`, the label, the UTC time (`date -u`), the boot id and the `MemTotal` line of `/proc/meminfo`. Then it holds the load, which is the content of `/proc/loadavg`. Then it holds the number of logins: `who` prints one line per login, and `wc -l` counts the lines. Then it holds `present` or `absent` for the marker file. The last part is the number of processes of each user: `ps -eo user=` prints the user of every process, and `sort` with `uniq -c` counts equal lines. `tr -s ' '` reduces each run of spaces to one space. `tr '\n' ';'` joins the counts with `;`. |
| 23 | `fail() { echo "FAILED: $1"; state abort; exit 1; }` | Defines the helper `fail MESSAGE`. It prints `FAILED:` and the message. Then it prints a state line with the label `abort`. Then it ends go.sh with exit status 1. |
| 24 | `echo "go.sh pid $$ (stop everything: kill -TERM -- -$$)"` | Prints the process id of go.sh and a command that stops the run. `kill -TERM -- -PID` sends the termination signal to every process of the process group with that number. The command reaches go.sh and its child processes only when go.sh is the leader of its process group. go.sh does not make itself the leader. In the rerun the start command did it with `setsid` [Ref5]. |

### Checks before the first step (lines 25 to 32)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"` | Check of the marker file: when the file exists (`-e`), `fail` stops the run with this message. The words after the comma were added on 2026-11-24, after the rerun [Ref12]. |
| 26 | `exec 9> "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 \|\| fail "another go.sh holds the lock"` | Lock against a second run. `exec 9> FILE` opens the lock file for writing as file descriptor 9 of the shell. It creates the file when it is missing. `flock -n 9` asks for an exclusive lock on that file and does not wait. When another process holds the lock, `fail` stops the run. `fail` also stops the run, with the same message, when the lock file could not be opened. |
| 27 | `echo "$RXSHA  $RX" \| sha256sum -c - > /dev/null \|\| fail "rx.sh is not the script of 2026-11-24"` | Checksum check of `rx.sh`. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the file and compares the two values. `> /dev/null` discards its report. When the values differ or the file cannot be read, `fail` stops the run. The message names the expected text: the `rx.sh` of 2026-11-24. |
| 28 | `echo "$SHA  $BW" \| sha256sum -c - > /dev/null \|\| fail "bwx12 is not the binary of 2026-11-15"` | The same check for the binary bwx12, with the checksum of line 15. |
| 29 | `for f in "$D/ra.sh" "$BW"; do [ -x "$f" ] \|\| fail "not executable: $f"; done` | For `ra.sh` and for bwx12: when the file is missing or not executable (`-x`), `fail` stops the run. |
| 30 | `for f in like cfwd crev; do [ -s "$D/$f.spec" ] \|\| fail "missing $D/$f.spec"; done` | For `like.spec`, `cfwd.spec` and `crev.spec` in the folder `D`: when the file is missing or empty (`-s`), `fail` stops the run. |
| 31 | `[ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] \|\| fail "MemTotal below 395000000 kB: not 12 modules"` | Memory size check. `awk` prints the second field of the `MemTotal` line of `/proc/meminfo`, a value in kB. When the value is below 395000000 kB (about 376.7 GiB), `fail` stops the run. By the message, a lower value means: not 12 modules. In the rerun the value was 395392808 kB [Ref1]. |
| 32 | `if [ "${HW:-on}" != off ]; then . "$HWDIR/hw.sh" \|\| fail "cannot read $HWDIR/hw.sh"; hw_check \|\| fail "hardware record not usable (the lines above say why)"; fi` | Test of the hardware record, before any step. With `HW=off` the line does nothing. In every other case the command `.` reads the file `hw.sh` into this shell. That file defines the functions `hw_check` and `hw_failures`, which `go.sh` calls. When the file cannot be read, `fail` stops the run. Then `hw_check` tests the tools of the record: the frequency files of Linux for CPU 0, a trial of the frequency sampler on CPU 119 and, when `HW_POWER` is `require`, a trial collection of `atx` of 5 s. These values are the defaults of `hw.sh`. The frequency sampler is the program of the hardware record that reads the clock rate of the cores during a step, once per second by default. When a test fails, `hw_check` prints the reason and `fail` stops the run. After a success `hw_check` exports the variable `HW_CHECKED`. With it, the later calls of `hw_check`, which `ra.sh` and `rx.sh` make through `hw_init`, return at once and do not repeat the trials. |

### Helpers `rxok` and `runx` (lines 33 to 40)

| Line | Source | Explanation |
|---:|---|---|
| 33 | `# rx.sh ends with status 0 also when bwx12 failed: it only writes "rc N tag" to launches.txt. Each spec file has one line, so exactly one "rc 0" line is required.` | Comment: the reason for line 34. `rx.sh` ends with status 0 also when bwx12 failed. It only writes a line `rc N tag` to the file `launches.txt`. Each spec file has one line. So exactly one line `rc 0` must be there. |
| 34 | `rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null \| tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }` | Defines the helper `rxok NAME`. It tests the exit status that `rx.sh` recorded for the bwx12 process. `ls -d` lists the `launches.txt` files of all result folders `w120-NAME-<time>` in name order, and `tail -1` keeps the last one. The time in the folder name puts the newest folder last [Ref3]. `2>/dev/null` discards the error message of `ls` when no file matches. The helper succeeds only when three tests pass. Test 1: a file was found (`-n`). Test 2: the file holds exactly 1 line that starts with `rc` and a space. Test 3: it holds exactly 1 line that starts with `rc 0` and a space. `grep -c` counts the matching lines. |
| 35 | `runx() { # name spec` | Starts the definition of the helper `runx NAME SPEC`. It runs one step of part L or part C. |
| 36 | `  bash "$RX" "$1" "$BW" "$SHA" < "$2" \|\| fail "rx.sh $1 rc $?"` | Runs `rx.sh` with `bash` and three arguments: NAME, the path of bwx12 and its expected sha256. The spec file is the input of `rx.sh` (`< "$2"`). go.sh waits until `rx.sh` has ended. On a non-zero exit status, `fail` stops the run and prints that status (`$?`). |
| 37 | `  rxok "$1" \|\| fail "bwx12 $1: exit status not 0 (launches.txt, stderr.txt)"` | Calls `rxok` (line 34). When it does not succeed, `fail` stops the run. The message names two files of the result folder to read: `launches.txt` and `stderr.txt`. |
| 38 | `  hwcount "w120-$1"` | Tests the hardware record of this step. `hwcount` (line 21) reads the newest result folder `w120-NAME-<time>`, the folder that `rx.sh` wrote in line 36. When the record holds `FAILED` lines or has no status file, `hwcount` adds 1 to `HWBAD` and prints one line. The run goes on in both cases. |
| 39 | `  state "after $1"` | Prints a state line with the label `after NAME`. |
| 40 | `}` | Ends the definition of `runx`. |

### Lines for the log: settings of the machine and the first state line (lines 41 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 41 | `echo "== cmdline $(cat /proc/cmdline)"` | Prints the command line of the running Linux kernel (file `/proc/cmdline`). This line and the next three lines only write to the log. None of them is a check. |
| 42 | `echo "== governors of CPUs 0-119: $(for c in $(seq 0 119); do cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_governor; done \| sort \| uniq -c \| tr -s ' ' \| tr '\n' ';') cpu0 scaling_cur_freq $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)"` | Prints the governor of each of the CPUs 0 to 119, counted per governor name (`sort` with `uniq -c`). Then it prints the file `scaling_cur_freq` of CPU 0: the current frequency that Linux reports for that CPU, in kHz [Ref11]. |
| 43 | `echo "== thp enabled $(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag $(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Prints the two settings of transparent huge pages: the files `enabled` and `defrag`. |
| 44 | `echo "== affinity of this shell: $(taskset -cp $$)"` | `taskset -cp $$` prints the CPU list of this shell. go.sh does not set this list. In the rerun the log shows `0-119` [Ref1]. |
| 45 | `state start` | Prints the first state line, with the label `start`. |

### The three sessions, the last part C process and the end (lines 46 to 56)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `for s in 1 2 3; do` | Starts a loop over the sessions: `s` is 1, then 2, then 3. |
| 47 | `  "$D/ra.sh" T72A$s \|\| fail "ra.sh session $s rc $?"` | Part A: runs `ra.sh` with the name `T72A1`, `T72A2` or `T72A3` and waits for its end. On a non-zero exit status, `fail` stops the run and prints that status. |
| 48 | `  hwcount "k120-T72A$s"` | Tests the hardware record of part A. `hwcount` (line 21) reads the newest result folder `k120-T72A<s>-<time>`, the folder that `ra.sh` wrote in line 47. Here `<s>` stands for the session number. When the record holds `FAILED` lines or has no status file, `hwcount` adds 1 to `HWBAD` and prints one line. The run goes on in both cases. |
| 49 | `  state "after T72A$s"` | Prints a state line with the label `after T72A<s>`. Here `<s>` stands for the session number. |
| 50 | `  runx T72L$s "$D/like.spec"` | Part L: `runx` (lines 35 to 40) runs one bwx12 process with `like.spec` and the name `T72L<s>`. |
| 51 | `  if [ "$s" = 2 ]; then runx T72C$s "$D/crev.spec"; else runx T72C$s "$D/cfwd.spec"; fi` | Part C: one bwx12 process with the name `T72C<s>`. Session 2 uses `crev.spec` (reverse order). Sessions 1 and 3 use `cfwd.spec` (forward order). |
| 52 | `done` | Ends the loop. |
| 53 | `runx T72C4 "$D/crev.spec"` | One more part C process after session 3, with `crev.spec` and the name `T72C4`. No part A and no part L run between `T72C3` and `T72C4`. |
| 54 | `state end` | Prints the last state line, with the label `end`. |
| 55 | `[ "$HWBAD" = 0 ] \|\| { echo "DONE, but the hardware record of $HWBAD steps is incomplete (lines above that start with: == hardware record)"; exit 4; }` | Tests `HWBAD` (line 20) after the last state line. When it is not 0, the line prints `DONE, but the hardware record of N steps is incomplete`, where N is the value of `HWBAD`. The text in parentheses tells the reader to look at the lines above that start with `== hardware record`. Then `go.sh` ends with exit status 4, and `ALLDONE` is not printed. When `HWBAD` is 0, `go.sh` goes on to line 56. |
| 56 | `echo ALLDONE` | Prints `ALLDONE`. The script reaches this line only when no check called `fail` and line 55 did not end the script. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log`, `/home/jhan/workspace/titan/cache-perf/crb/results/dimm7200-20261117/try6.txt`: the log of go.sh in the rerun, and the record of the memory check. Log: line 5 holds the CPU list `0-119` of the shell. Line 6 holds the boot id of line 16 of go.sh. All 12 state lines hold `MemTotal: 395392808 kB` and `marker absent`. No line starts with `FAILED`. The last line is `ALLDONE`. `try6.txt`: line 2 holds the same boot id. Line 7 holds the count 12 for the text `Configured Memory Speed: 7200 MT/s`.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: part A script. `set -euo pipefail`: line 8. Restart under `taskset -c 0-119`: line 9. `--min-ms 500`: line 42.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: runner script. The result folder name ends with the UTC start time: line 9. Start of the binary under `taskset -c 0-119`: line 17. The `rc` line: line 20. This copy has the sha256 of line 14 of go.sh.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`, `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/cfwd.spec`, `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/crev.spec`, `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/r8.spec`: the three spec files and the older spec file. Each of the three holds one line with `--threads 120 --cpus 0-63,64-119`, `--stop common` and `--min-ms 6000`. `--seq` gives the loop order: `oldread,asmread,read_nop96,read_nop256,read_1pl` (like), `oldread,read,asmread` (cfwd), `asmread,read,oldread` (crev). Line 1 of `r8.spec` is equal to the line of `like.spec`.
- [Ref5] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the saved record of the AI agent (Claude Code) that ran the rerun, one JSON record per line. It lies outside the project folder. Line 313 holds the command that the agent sent to CRB at 22:12:08 UTC on 2026-11-17. It holds the start command and no `taskset`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/inspection-record-2026-10-30.md`: inspection of CRB on 2026-10-30. Line 140: the file `/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf` holds `CPUAffinity=0-119`, and process 1 and every process that descends from it have the CPU list 0-119.
- [Ref7] external source: Linux manual pages nohup(1), setsid(1) and setsid(2). `nohup` runs a command that ignores the hangup signal. `setsid` runs a program in a new Linux session. The process that creates the session becomes the leader of a new process group.
- [Ref8] external source: Linux manual page sched_setaffinity(2). A child process inherits the CPU affinity of its parent.
- [Ref9] external source: Linux manual page random(4), entry `/proc/sys/kernel/random/boot_id`. The value is generated once per boot.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md`: notes of 2026-10-30 about the tests of Jeremy. Line 12 defines a block: a reserved whole-host window in which Jeremy runs measurements. Line 13: the file `/tmp/positron-perf.RUNNING` is present for the whole block.
- [Ref11] external sources: Linux manual page proc(5), entry `/proc/loadavg` (meaning of the five fields). Linux kernel documentation "CPU Performance Scaling" (`admin-guide/pm/cpufreq`), entry `scaling_cur_freq` (the value is in kHz).
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/go-edit-2026-11-24/go.sh.as-run-2026-11-17`, `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/local.sha`: a copy of go.sh from before the edit of 2026-11-24, and the checksum list that was written when the files were copied to CRB on 2026-11-17. The copy differs from the local go.sh in line 20 only. The copy has the sha256 that line 1 of `local.sha` lists for go.sh.
- [Ref13] external source: GitHub Flavored Markdown Spec, section 4.10 "Tables (extension)". A `|` inside a table cell is written `\|`, also inside a code span. The script that built this page read the page back with pandoc (reader `gfm`). Each source cell was equal to its line of go.sh.
