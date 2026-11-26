# `rg.sh` explained, line by line

- Source file: `w120-2026-11-15/rg.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 29 lines, 1901 bytes).
- sha256 of the source when this page was built: `81feb87cd934940670b61af241aafa2c9a8586fea8c565cebde05175a9b4ff5b`.

## Short version: purpose

`rg.sh` starts groups of benchmark processes that run at the same time, on the CPUs 0 to 119 and without root rights. Each line of its spec file is one group, and each item of the line is one process with its own arguments, for example one process per mesh with a different kernel. It is the script of the 120-thread investigation for tests in which two sets of threads run different kernels at the same time.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. The spec file of `rg.sh` has another form: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Group**: the processes of one line of the spec file. The script starts them one after the other and then waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `.
- **Latency probe**: a second program that times memory loads on one CPU while the benchmark processes run on the other CPUs. The spec file `r4.spec` uses the program `robsize` for it.

## Main flow

1. Read the three arguments (line 6).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 (lines 7 to 8).
3. Create the result folder and write `env.txt` (lines 9 to 10).
4. For each line of the spec file: wait until the machine is quiet and write a `launch` line (lines 11 to 16).
5. Start one process per item of the line, in the background, and note each launch time (lines 17 to 24).
6. Wait until every process of the group has ended, with a check of the marker file once per second (lines 25 to 26).
7. Write one `rc` line with the exit status of each process (line 27).
8. After the last line: print a summary (line 29).

## Behavior a reader must know

- The processes of a group are started one after the other, as fast as the shell starts them. The script does not make their timed intervals begin at the same moment. Each process times its own interval, so the intervals of a group overlap only as far as the start phases of the processes allow.
- A group is over when all its processes have ended. Only then does the script go to the next line, with a new wait for a quiet machine and a new pause of 5 s.
- An item whose arguments start with `@` runs the text after the `@` as a full command (line 21). The checksum check of line 8 does not cover that program.
- The marker file is checked three times: at the start, before each group, and once per second while a group runs. Each check ends the script with exit status 3. The last one also ends every process of the group.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of each process is written to `launches.txt` and is not tested.
- An `rc` line holds the group name and no tag. The `rc` lines of a group stand in the order of the items of its spec line.
- The script runs no command as root.
- This script does not call `hw.sh`. It makes no hardware record.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rg.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (29 lines, 1901 bytes, sha256 `81feb87cd934940670b61af241aafa2c9a8586fea8c565cebde05175a9b4ff5b`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 3)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# rg.sh NAME BINARY SHA256 < spec - groups of processes that run at the same time (mixed kernels). No root.` | Comment: the usage. The script takes three arguments: a name, the path of a binary and the sha256 that the binary must have. It reads a spec file as its input. By the comment it starts groups of processes that run at the same time, for example with a different kernel in each process, and it needs no root rights. |
| 3 | `# spec lines: group\|tag=args ;; tag=args ...  (args that start with @ are a full command, used for the latency probe)   Marker file checked before and during every group. CPUs 0-119 only.` | Comment: each line of the spec file has the form `group\|tag=args ;; tag=args ...`: a group name, then one item per process, with ` ;; ` between the items. When the arguments of an item start with `@`, the rest is a full command that runs in place of the binary. By the comment this is used for the latency probe, a second program that times memory loads while the benchmark processes run. The marker file is checked before and during every group. Lines 21 to 22 limit each process to the CPUs 0 to 119. |

### Settings, checks and the result folder (lines 4 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 4 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 5 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 6 | `name=$1; BW=$2; sha=$3` | Reads the three arguments. `name` becomes a part of the name of the result folder. `BW` is the path of the binary to run. `sha` is the sha256 that the binary must have. |
| 7 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 3. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 8 | `echo "$sha  $BW" \| sha256sum -c - >/dev/null \|\| { echo "sha mismatch"; exit 2; }` | Checksum check of the binary. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the binary and compares the two values. Its report goes to `/dev/null`, which discards it. When the values differ or the file cannot be read, the script prints `sha mismatch` and ends with exit status 2. The check covers the binary `BW` only. The program of an item that starts with `@` (line 21) is not checked. |
| 9 | `out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `w120-`, then `name`, then the UTC time of this moment (`date -u`), for example `w120-R3-20261115T193922Z` [Ref2]. `mkdir -p` creates the folder. The time is read before the waits of line 14 and line 15. So it is at least 5 s before the start of the first process. |
| 10 | `{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha"; } > $out/env.txt` | Writes the file `env.txt` once, before any process. The braces group five commands, and `>` sends the output of all of them to the file. It holds, in this order: the UTC date and time (`date -u`), the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and one line with the word `binary`, the path and the expected sha256 of the binary. |

### Loop: one group of processes per line of the spec file (lines 11 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `while IFS='\|' read -r grp items; do` | Starts the loop over the lines of the input, which is the spec file. `IFS='\|'` splits each line at the first `\|`. The text before it goes to `grp`, the name of the group. The rest of the line goes to `items`. `-r` keeps each backslash as it is. |
| 12 | `  [ -z "$grp" ] && continue` | Skips a line with an empty group name, for example an empty line. |
| 13 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 3, before each group. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 14 | `  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 40 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, for example `1/1019`. `cut -d/ -f1` keeps the number before the slash. This is the number of tasks that are runnable now [Ref1]. When the number is 2 or less, the loop ends. If not, the script sleeps 1 s and tests again. After 40 tries (about 40 s) the loop ends too, and the script goes on without a message. |
| 15 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 16 | `  echo "launch $grp utc $(date -u +%T) load $(cat /proc/loadavg) users $(who \| wc -l) items $items" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the group name, the UTC time (hours, minutes, seconds), the content of `/proc/loadavg`, the number of logins and the items of the group. This is the last reading of the machine state before the processes of the group start. |
| 17 | `  pids=` | `pids=`: empties the list of the process ids of this group. |
| 18 | `  while read -r it; do` | Starts the inner loop over the items of the group. Line 24 gives it one item per line. `read -r it` puts one item into `it` and removes the spaces at its two ends. |
| 19 | `    [ -z "$it" ] && continue` | Skips an empty item. |
| 20 | `    tag=${it%%=*}; args=${it#*=}` | Splits the item at its first `=`. `${it%%=*}` removes the longest text at the end that starts with `=`. What stays is the tag. `${it#*=}` removes the shortest text at the start that ends with `=`. What stays is the argument text. An `=` inside the arguments, as in `--events cycles=0x11`, stays in `args`. |
| 21 | `    if [ "${args#@}" != "$args" ]; then taskset -c 0-119 ${args#@} > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null &` | Tests whether the arguments start with `@`. `${args#@}` is the text of `args` without an `@` at its start. When it differs from `args`, the text after the `@` is run as a full command, in the background (`&`). `taskset -c 0-119` allows the new process to run on the CPUs 0 to 119 only. Then `taskset` replaces itself with that command in the same process. The text has no quotes. So the shell splits it at the spaces into the program and its arguments. The standard output goes to the file `GROUP.TAG.csv` in the result folder. Error messages are appended to `stderr.txt`. The input is `/dev/null`, an empty input. The binary `BW` is not used for such an item. |
| 22 | `    else taskset -c 0-119 $BW $args > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null & fi` | In every other case: starts the binary `BW` with the arguments of the item, in the same way as line 21: in the background, on the CPUs 0 to 119 only, with its standard output in `GROUP.TAG.csv`. `$args` has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary. `fi` ends the `if` of line 21. `rg.sh` pins no thread. The runner pins each thread to one CPU of its `--cpus` argument (function `worker` of `bwx12.c`). |
| 23 | `    pids="$pids $!"; echo "start $grp $tag epoch $(date +%s.%N)" >> $out/launches.txt` | Adds the process id of the new process (`$!`) to `pids`. Then appends the line `start <group> <tag> epoch <time>` to `launches.txt`. The time is in seconds since 1970-01-01 00:00 UTC, with nanoseconds. It is read directly after the launch. So it is the time of the launch, not the time at which the process begins its timed interval. |
| 24 | `  done < <(echo "$items" \| sed 's/ ;; /\n/g')` | Ends the inner loop (line 18) and gives it its input. `echo` prints the items of the group. `sed` replaces each ` ;; ` (a space, two semicolons, a space) with a line break. So each item stands on its own line. The form `< <(...)` makes the output of these two commands the input of the loop. The loop itself runs in the shell of the script. So `pids` keeps its value after the loop, and the processes are children of this shell, which the `wait` of line 27 needs. The loop starts the items one after the other and does not wait between them. |
| 25 | `  while :; do alive=0; for p in $pids; do kill -0 $p 2>/dev/null && alive=1; done; [ $alive = 0 ] && break` | Waits until every process of the group has ended. `while :` loops without an end condition. Each pass sets `alive` to 0. Then `kill -0` tests each process id of `pids` (it sends no signal), and `alive` becomes 1 when at least one process still exists. When `alive` is still 0, `break` leaves the loop. |
| 26 | `    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }; sleep 1; done` | Continues the loop of line 25. Marker check 3 of 3, once per second: when the marker file exists, `kill $pids` sends the termination signal to every process of the group. The script then prints `marker: killed` and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. So `rg.sh` sees the end of the group up to about 1 s late. `done` ends the loop. |
| 27 | `  for p in $pids; do wait $p; echo "rc $? $grp" >> $out/launches.txt; done` | For each process of the group, in the order of the launch: `wait $p` returns its exit status, and the script appends the line `rc <exit status> <group>` to `launches.txt`. The line holds no tag and no time. The script does not test the status. |
| 28 | `done` | Ends the loop over the lines of the spec file (line 11). The loop ends when the input has no more lines. |

### Summary (line 29)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `echo "done $out"; grep -c '^rc 0' $out/launches.txt; grep '^rc' $out/launches.txt \| grep -vc '^rc 0'; wc -c < $out/stderr.txt; head -c 500 $out/stderr.txt` | Prints a short summary to the standard output: `done` and the path of the result folder, then the number of `rc` lines with the status 0 (`grep -c` counts the lines of `launches.txt` that start with `rc 0`), then the number of `rc` lines with another status (`grep -v` drops the lines that start with `rc 0`, and `-c` counts the rest), then the size of `stderr.txt` in bytes, then the first 500 bytes of `stderr.txt`. The exit status of `rg.sh` is the status of the last command, `head`. It does not depend on the exit status of a process. |

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-R3-20261115T193922Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that line 9 builds.
