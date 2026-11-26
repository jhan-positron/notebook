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

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# go.sh - whole-chip rerun at 7200 MT/s. Three sessions. Each session runs, one after the other:` | Comment: the name of the script and the plan. The run has three sessions. Each session runs the parts A, L and C, one after the other. |
| 3 | `#   A: ra.sh            (the 120-thread part of the 2026-11-13 test, same binaries, whole-pass stop, 0.5 s)` | Comment, part A: `ra.sh` repeats the 120-thread part of the test of 2026-11-13 with the same binaries. `whole-pass stop, 0.5 s` names the stop rule of these binaries and their minimum run time (`--min-ms 500` in `ra.sh`) [Ref2]. |
| 4 | `#   L: rx.sh like.spec  (runner bwx12, common stop, 6 s, the 120-thread line of r8.spec unchanged)` | Comment, part L: `rx.sh` runs bwx12 with the spec file `like.spec`. `common stop, 6 s` stands for the arguments `--stop common --min-ms 6000` of the spec file [Ref4]. The one line of `like.spec` is equal to line 1 of the older spec file `r8.spec` [Ref4]. |
| 5 | `#   C: rx.sh cfwd.spec or crev.spec (bwx12: old C read, new C read, asm read; session 2 in reverse order)` | Comment, part C: `rx.sh` runs bwx12 with `cfwd.spec` or `crev.spec`. One process times three read loops: the old C loop, the new C loop and the assembly loop (`--seq oldread,read,asmread` in `cfwd.spec`) [Ref4]. `crev.spec` holds the reverse order. Session 2 uses it. |
| 6 | `# After session 3 one more C process runs in reverse order (2 forward and 2 reverse processes in total).` | Comment: after session 3, one more part C process runs in reverse order. Part C then has 2 processes in forward order and 2 processes in reverse order. |
| 7 | `# No root. CPUs 0-119 only. ra.sh and rx.sh stop if /tmp/positron-perf.RUNNING exists.` | Comment: the run needs no root rights and uses the CPUs 0 to 119 only. `ra.sh` and `rx.sh` stop when the marker file exists. |
| 8 | `# 8000 MT/s baselines for the comparison: fixed list in baselines-and-rules.txt (same folder), fixed before this run.` | Comment: the rerun is compared with earlier results at 8000 MT/s. The file `baselines-and-rules.txt` lists them. By the comment, the list was fixed before this run. go.sh never reads that file. |
| 9 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 10 | `D=$HOME/cache-perf/w120-7200-20261117` | `D`: the folder on CRB that holds `ra.sh` and the three spec files. |
| 11 | `RX=$HOME/cache-perf/w120-20261115/rx.sh` | `RX`: the path of the runner script `rx.sh`. |
| 12 | `BW=$HOME/cache-perf/bwx12-20261115/bwx12` | `BW`: the path of the binary bwx12. |
| 13 | `SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a` | `SHA`: the sha256 that the file bwx12 must have. Line 23 tests it. |
| 14 | `RXSHA=d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab` | `RXSHA`: the sha256 that `rx.sh` must have. Line 22 tests it. |
| 15 | `# The boot in which results/dimm7200-20261117/try6.txt recorded 12 modules at 7200 MT/s.` | Comment: the origin of the boot id in line 16. It is the boot in which the file `try6.txt` recorded 12 memory modules at 7200 MT/s [Ref1]. |
| 16 | `BOOT=3bfc57a1-e235-4fe5-8c09-a94642f9b60b` | `BOOT`: the boot id that the running system must have. Line 26 tests it. |
| 17 | `state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo \| tr -s ' ') load $(cat /proc/loadavg) users $(who \| wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] && echo present \|\| echo absent) processes per user: $(ps -eo user= \| sort \| uniq -c \| tr -s ' ' \| tr '\n' ';')"; }` | Defines the helper `state LABEL`. It prints one state line and stops nothing. The line holds `==`, the label, the UTC time (`date -u`), the boot id and the `MemTotal` line of `/proc/meminfo`. Then it holds the load, which is the content of `/proc/loadavg`. Then it holds the number of logins: `who` prints one line per login, and `wc -l` counts the lines. Then it holds `present` or `absent` for the marker file. The last part is the number of processes of each user: `ps -eo user=` prints the user of every process, and `sort` with `uniq -c` counts equal lines. `tr -s ' '` reduces each run of spaces to one space. `tr '\n' ';'` joins the counts with `;`. |
| 18 | `fail() { echo "FAILED: $1"; state abort; exit 1; }` | Defines the helper `fail MESSAGE`. It prints `FAILED:` and the message. Then it prints a state line with the label `abort`. Then it ends go.sh with exit status 1. |
| 19 | `echo "go.sh pid $$ (stop everything: kill -TERM -- -$$)"` | Prints the process id of go.sh and a command that stops the run. `kill -TERM -- -PID` sends the termination signal to every process of the process group with that number. The command reaches go.sh and its child processes only when go.sh is the leader of its process group. go.sh does not make itself the leader. In the rerun the start command did it with `setsid` [Ref5]. |
| 20 | `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"` | Check of the marker file: when the file exists (`-e`), `fail` stops the run with this message. The words after the comma were added on 2026-11-24, after the rerun [Ref12]. |
| 21 | `exec 9> "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 \|\| fail "another go.sh holds the lock"` | Lock against a second run. `exec 9> FILE` opens the lock file for writing as file descriptor 9 of the shell. It creates the file when it is missing. `flock -n 9` asks for an exclusive lock on that file and does not wait. When another process holds the lock, `fail` stops the run. |
| 22 | `echo "$RXSHA  $RX" \| sha256sum -c - > /dev/null \|\| fail "rx.sh is not the script of 2026-11-15"` | Checksum check of `rx.sh`. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the file and compares the two values. `> /dev/null` discards its report. When the values differ or the file cannot be read, `fail` stops the run. |
| 23 | `echo "$SHA  $BW" \| sha256sum -c - > /dev/null \|\| fail "bwx12 is not the binary of 2026-11-15"` | The same check for the binary bwx12, with the checksum of line 13. |
| 24 | `for f in "$D/ra.sh" "$BW"; do [ -x "$f" ] \|\| fail "not executable: $f"; done` | For `ra.sh` and for bwx12: when the file is missing or not executable (`-x`), `fail` stops the run. |
| 25 | `for f in like cfwd crev; do [ -s "$D/$f.spec" ] \|\| fail "missing $D/$f.spec"; done` | For `like.spec`, `cfwd.spec` and `crev.spec` in the folder `D`: when the file is missing or empty (`-s`), `fail` stops the run. |
| 26 | `[ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] \|\| fail "boot id is not the boot checked at 12 modules, 7200 MT/s"` | Boot check: when the boot id of the running system differs from `BOOT` (line 16), `fail` stops the run. The check reads the boot id only. It does not read the memory speed or the number of modules. |
| 27 | `[ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] \|\| fail "MemTotal below 395000000 kB: not 12 modules"` | Memory size check. `awk` prints the second field of the `MemTotal` line of `/proc/meminfo`, a value in kB. When the value is below 395000000 kB (about 376.7 GiB), `fail` stops the run. By the message, a lower value means: not 12 modules. In the rerun the value was 395392808 kB [Ref1]. |
| 28 | `# rx.sh ends with status 0 also when bwx12 failed: it only writes "rc N tag" to launches.txt. Each spec file has one line, so exactly one "rc 0" line is required.` | Comment: the reason for line 29. `rx.sh` ends with status 0 also when bwx12 failed. It only writes a line `rc N tag` to the file `launches.txt`. Each spec file has one line. So exactly one line `rc 0` must be there. |
| 29 | `rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2>/dev/null \| tail -1); [ -n "$l" ] && [ "$(grep -c '^rc ' "$l")" = 1 ] && [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }` | Defines the helper `rxok NAME`. It tests the exit status that `rx.sh` recorded for the bwx12 process. `ls -d` lists the `launches.txt` files of all result folders `w120-NAME-<time>` in name order, and `tail -1` keeps the last one. The time in the folder name puts the newest folder last [Ref3]. `2>/dev/null` discards the error message of `ls` when no file matches. The helper succeeds only when three tests pass. Test 1: a file was found (`-n`). Test 2: the file holds exactly 1 line that starts with `rc` and a space. Test 3: it holds exactly 1 line that starts with `rc 0` and a space. `grep -c` counts the matching lines. |
| 30 | `runx() { # name spec` | Starts the definition of the helper `runx NAME SPEC`. It runs one step of part L or part C. |
| 31 | `  bash "$RX" "$1" "$BW" "$SHA" < "$2" \|\| fail "rx.sh $1 rc $?"` | Runs `rx.sh` with `bash` and three arguments: NAME, the path of bwx12 and its expected sha256. The spec file is the input of `rx.sh` (`< "$2"`). go.sh waits until `rx.sh` has ended. On a non-zero exit status, `fail` stops the run and prints that status (`$?`). |
| 32 | `  rxok "$1" \|\| fail "bwx12 $1: exit status not 0 (launches.txt, stderr.txt)"` | Calls `rxok` (line 29). When it does not succeed, `fail` stops the run. The message names two files of the result folder to read: `launches.txt` and `stderr.txt`. |
| 33 | `  state "after $1"` | Prints a state line with the label `after NAME`. |
| 34 | `}` | Ends the definition of `runx`. |
| 35 | `echo "== cmdline $(cat /proc/cmdline)"` | Prints the command line of the running Linux kernel (file `/proc/cmdline`). This line and the next three lines only write to the log. None of them is a check. |
| 36 | `echo "== governors of CPUs 0-119: $(for c in $(seq 0 119); do cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_governor; done \| sort \| uniq -c \| tr -s ' ' \| tr '\n' ';') cpu0 scaling_cur_freq $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)"` | Prints the governor of each of the CPUs 0 to 119, counted per governor name (`sort` with `uniq -c`). Then it prints the file `scaling_cur_freq` of CPU 0: the current frequency that Linux reports for that CPU, in kHz [Ref11]. |
| 37 | `echo "== thp enabled $(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag $(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Prints the two settings of transparent huge pages: the files `enabled` and `defrag`. |
| 38 | `echo "== affinity of this shell: $(taskset -cp $$)"` | `taskset -cp $$` prints the CPU list of this shell. go.sh does not set this list. In the rerun the log shows `0-119` [Ref1]. |
| 39 | `state start` | Prints the first state line, with the label `start`. |
| 40 | `for s in 1 2 3; do` | Starts a loop over the sessions: `s` is 1, then 2, then 3. |
| 41 | `  "$D/ra.sh" T72A$s \|\| fail "ra.sh session $s rc $?"` | Part A: runs `ra.sh` with the name `T72A1`, `T72A2` or `T72A3` and waits for its end. On a non-zero exit status, `fail` stops the run and prints that status. |
| 42 | `  state "after T72A$s"` | Prints a state line with the label `after T72A<s>`. Here `<s>` stands for the session number. |
| 43 | `  runx T72L$s "$D/like.spec"` | Part L: `runx` (lines 30 to 34) runs one bwx12 process with `like.spec` and the name `T72L<s>`. |
| 44 | `  if [ "$s" = 2 ]; then runx T72C$s "$D/crev.spec"; else runx T72C$s "$D/cfwd.spec"; fi` | Part C: one bwx12 process with the name `T72C<s>`. Session 2 uses `crev.spec` (reverse order). Sessions 1 and 3 use `cfwd.spec` (forward order). |
| 45 | `done` | Ends the loop. |
| 46 | `runx T72C4 "$D/crev.spec"` | One more part C process after session 3, with `crev.spec` and the name `T72C4`. No part A and no part L run between `T72C3` and `T72C4`. |
| 47 | `state end` | Prints the last state line, with the label `end`. |
| 48 | `echo ALLDONE` | Prints `ALLDONE`. The script reaches this line only when no check called `fail`. |

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
