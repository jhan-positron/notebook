# `rgc.sh` explained, line by line

- Source file: `w120-2026-11-15/rgc.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 36 lines, 2199 bytes).
- sha256 of the source when this page was built: `f0e2e11fc5f059d75be464d9fe3f6c0e4c733ef7466cce0cceda75646f06d04e`.

## Short version: purpose

`rgc.sh` joins the two scripts `rg.sh` and `rc2.sh`. It starts groups of benchmark processes that run at the same time, one group per line of its spec file, on the CPUs 0 to 119. While a group runs, it reads mesh counters as root with `sudo perf stat`: one counter window of `WIN` seconds per event set.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. The spec file of `rgc.sh` has another form: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Group**: the processes of one line of the spec file. The script starts them one after the other and then waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together. In this script the events are full `perf` event strings, with the device name in each of them.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` (line 6).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 (lines 7 to 8).
3. Create the result folder, write `env.txt` and copy the event sets to `sets.ok` (lines 9 to 11).
4. For each line of the spec file: wait until the machine is quiet and write a `launch` line (lines 12 to 17).
5. Start one process per item of the line, in the background (lines 18 to 24).
6. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set (lines 25 to 30).
7. Wait until every process of the group has ended, and write one `rc` line per process (lines 31 to 33).
8. After the last line: make the user the owner of the result files and print a summary (lines 35 to 36).

## Behavior a reader must know

- Two commands run as root: the `sudo -n perf stat` of line 29 and the `sudo -n chown` of line 35. The header comment names `perf stat` only.
- No event is tested before the run. When `perf` cannot count an event, or when `sudo` would need a password, the script goes on: it does not test the exit status of `perf`. The error message goes to `stderr.txt`.
- The processes of a group are started one after the other. The script does not make their timed intervals begin at the same moment. Each process times its own interval.
- The counts of a window are counts of the whole machine while all processes of the group run. The device name of an event tells the mesh, not the process.
- The windows of a group follow one after the other. So every timed interval of the group must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. As soon as one process of the group has ended, line 27 writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script writes no `start` line and no `win` line. So `launches.txt` shows the launch of a group only in its `launch` line, with a time in whole seconds, and it does not show when a window began.
- The marker file is checked four times: at the start, before each group, before each counter window, and once per second while the script waits for the end of a group. Each check ends the script with exit status 3. The last two also end every process of the group.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of each process is written to `launches.txt` and is not tested.
- This script does not call `hw.sh`. It makes no hardware record.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rgc.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (36 lines, 2199 bytes, sha256 `f0e2e11fc5f059d75be464d9fe3f6c0e4c733ef7466cce0cceda75646f06d04e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 3)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# rgc.sh NAME BINARY SHA256 SETS < spec - groups of simultaneous processes (mixed kernels) with mesh counters (root, perf stat -a).` | Comment: the usage. The script takes four arguments: a name, the path of a binary, the sha256 that the binary must have and the path of a file with event sets. It reads a spec file as its input. By the comment it starts groups of processes that run at the same time, for example with a different kernel in each process, and it reads the mesh counters as root (`perf stat -a`). |
| 3 | `# spec lines: group\|tag=args ;; tag=args ...   SETS lines: setname\|full perf event list. sudo is used for perf stat only.` | Comment: each line of the spec file has the form `group\|tag=args ;; tag=args ...`: a group name, then one item per process, with ` ;; ` between the items. Each line of the file with the event sets has the form `setname\|full perf event list`. By the comment `sudo` (root rights) is used for `perf stat` only. The code has one more `sudo` command: the `chown` of line 35. |

### Settings, checks and the result folder (lines 4 to 11)

| Line | Source | Explanation |
|---:|---|---|
| 4 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 5 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 6 | `name=$1; BW=$2; sha=$3; sets=$4; WIN=${WIN:-3}; DELAY=${DELAY:-9}` | Reads the four arguments. `name` becomes a part of the name of the result folder. `BW` is the path of the binary to run. `sha` is the sha256 that the binary must have. `sets` is the path of the file with the event sets. `WIN` is the length of one counter window in seconds. `DELAY` is the wait in seconds between the launch of a group and its first counter window. `${WIN:-3}` keeps the value of `WIN` when the caller has set it to a value that is not empty. If not, the value is 3. In the same way the default of `DELAY` is 9. |
| 7 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 4. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 8 | `echo "$sha  $BW" \| sha256sum -c - >/dev/null \|\| { echo "sha mismatch"; exit 2; }` | Checksum check of the binary. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the binary and compares the two values. Its report goes to `/dev/null`, which discards it. When the values differ or the file cannot be read, the script prints `sha mismatch` and ends with exit status 2. |
| 9 | `out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `w120-`, then `name`, then the UTC time of this moment (`date -u`), for example `w120-RC3-20261115T194737Z` [Ref2]. `mkdir -p` creates the folder. The time is read before the waits of line 15 and line 16. So it is at least 5 s before the start of the first process. |
| 10 | `{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha WIN $WIN DELAY $DELAY"; } > $out/env.txt` | Writes the file `env.txt` once, before any process. The braces group five commands, and `>` sends the output of all of them to the file. It holds, in this order: the UTC date and time (`date -u`), the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and one line with the word `binary`, the path and the expected sha256 of the binary, and the values of `WIN` and `DELAY`. |
| 11 | `cp $sets $out/sets.ok` | Copies the file with the event sets into the result folder, under the name `sets.ok`. The script does not test the events: every set is used as it stands. The loop of lines 26 to 30 reads this copy. |

### Loop: one group of processes per line of the spec file, one counter window per event set (lines 12 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 12 | `while IFS='\|' read -r grp items <&3; do` | Starts the loop over the lines of the spec file. `IFS='\|'` splits each line at the first `\|`. The text before it goes to `grp`, the name of the group. The rest of the line goes to `items`. `-r` keeps each backslash as it is. `<&3` makes `read` take the line from file descriptor 3. Line 34 makes descriptor 3 a copy of the standard input of the script, which is the spec file. |
| 13 | `  [ -z "$grp" ] && continue` | Skips a line with an empty group name, for example an empty line. |
| 14 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 4, before each group. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 15 | `  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 40 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, for example `1/1019`. `cut -d/ -f1` keeps the number before the slash. This is the number of tasks that are runnable now [Ref1]. When the number is 2 or less, the loop ends. If not, the script sleeps 1 s and tests again. After 40 tries (about 40 s) the loop ends too, and the script goes on without a message. |
| 16 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 17 | `  echo "launch $grp utc $(date -u +%T) load $(cat /proc/loadavg) users $(who \| wc -l) items $items" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the group name, the UTC time (hours, minutes, seconds), the content of `/proc/loadavg`, the number of logins and the items of the group. This is the last reading of the machine state before the processes of the group start. |
| 18 | `  pids=` | `pids=`: empties the list of the process ids of this group. |
| 19 | `  while read -r it; do` | Starts the inner loop over the items of the group. Line 24 gives it one item per line. `read -r it` puts one item into `it` and removes the spaces at its two ends. |
| 20 | `    [ -z "$it" ] && continue` | Skips an empty item. |
| 21 | `    tag=${it%%=*}; args=${it#*=}` | Splits the item at its first `=`. `${it%%=*}` removes the longest text at the end that starts with `=`. What stays is the tag. `${it#*=}` removes the shortest text at the start that ends with `=`. What stays is the argument text. An `=` inside the arguments, as in `--events cycles=0x11`, stays in `args`. |
| 22 | `    taskset -c 0-119 $BW $args > $out/$grp.$tag.csv 2>> $out/stderr.txt < /dev/null &` | Starts the binary `BW` with the arguments of the item, in the background (`&`). `taskset -c 0-119` allows the new process to run on the CPUs 0 to 119 only. Then `taskset` replaces itself with the binary in the same process. `$args` has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary. The standard output goes to the file `GROUP.TAG.csv` in the result folder. Error messages are appended to `stderr.txt`. The input is `/dev/null`, an empty input. The script `rg.sh` has a special case for arguments that start with `@`. This script has none. `rgc.sh` pins no thread. The runner pins each thread to one CPU of its `--cpus` argument (function `worker` of `bwx12.c`). |
| 23 | `    pids="$pids $!"` | Adds the process id of the new process (`$!`) to `pids`. The script writes no line with the launch time of a process. |
| 24 | `  done < <(echo "$items" \| sed 's/ ;; /\n/g')` | Ends the inner loop (line 19) and gives it its input. `echo` prints the items of the group. `sed` replaces each ` ;; ` (a space, two semicolons, a space) with a line break. So each item stands on its own line. The form `< <(...)` makes the output of these two commands the input of the loop. The loop itself runs in the shell of the script. So `pids` keeps its value after the loop, and the processes are children of this shell, which the `wait` of line 33 needs. The loop starts the items one after the other and does not wait between them. |
| 25 | `  sleep $DELAY` | Waits `DELAY` seconds (9 s by default) after the last launch of the group, before the first counter window. In its start phase a runner writes every buffer once and runs a warm-up pass before it times (function `worker` of `bwx12.c`). This pause is the only thing that keeps the windows out of that phase. The script does not test that the timed intervals have begun. |
| 26 | `  while IFS='\|' read -r sn evs; do` | Starts the loop over the lines of `sets.ok` (line 30 gives that file as the input). `IFS='\|'` splits each line at the first `\|`. `sn` gets the name of the set and `evs` the event list. Each pass takes one counter window. |
| 27 | `    for p in $pids; do kill -0 $p 2>/dev/null \|\| { echo "process ended before set $sn of $grp" >> $out/launches.txt; break 2; }; done` | Tests whether every process of the group still exists (`kill -0` sends no signal). When one has ended, the script appends the line `process ended before set <set name> of <group>` to `launches.txt`. `break 2` then leaves two loops: this `for` loop and the loop over the sets (line 26). So the sets that remain get no window for this group. |
| 28 | `    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }` | Marker check 3 of 4, before each counter window. When the marker file exists, `kill $pids` sends the termination signal to every process of the group. The script then prints `marker: killed` and ends with exit status 3. |
| 29 | `    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/,$evs" -o $out/$grp.$sn.perf -- sleep $WIN 2>> $out/stderr.txt` | Takes one counter window. `sudo -n` runs `perf` as root and fails when it would need a password. `perf stat` counts events while a command runs. `-a`: on all CPUs, not only for that command. `-x,`: output lines with commas between the fields. `-e` gets the event list: `dtc_cycles` of the two counter devices, then the text of `evs` as the set line holds it. `-o` writes the counts to the file `GROUP.SET.perf` in the result folder. The command after `--` is `sleep $WIN`. So the counter window lasts `WIN` seconds (3 s by default). Each line of the file holds: the count, the unit, the event, the time for which the counter ran in ns, and the percentage of the window for which it ran [Ref3]. Error messages are appended to `stderr.txt`. The exit status of `perf` is not tested. |
| 30 | `  done < $out/sets.ok` | Ends the loop over the sets (line 26). `< $out/sets.ok` makes `sets.ok` the input of the loop. |
| 31 | `  while :; do alive=0; for p in $pids; do kill -0 $p 2>/dev/null && alive=1; done; [ $alive = 0 ] && break` | Waits until every process of the group has ended. `while :` loops without an end condition. Each pass sets `alive` to 0. Then `kill -0` tests each process id of `pids` (it sends no signal), and `alive` becomes 1 when at least one process still exists. When `alive` is still 0, `break` leaves the loop. |
| 32 | `    [ -e $M ] && { kill $pids; echo "marker: killed"; exit 3; }; sleep 1; done` | Continues the loop of line 31. Marker check 4 of 4, once per second: when the marker file exists, `kill $pids` sends the termination signal to every process of the group. The script then prints `marker: killed` and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. So `rgc.sh` sees the end of the group up to about 1 s late. `done` ends the loop. |
| 33 | `  for p in $pids; do wait $p; echo "rc $? $grp" >> $out/launches.txt; done` | For each process of the group, in the order of the launch: `wait $p` returns its exit status, and the script appends the line `rc <exit status> <group>` to `launches.txt`. The line holds no tag and no time. The script does not test the status. |
| 34 | `done 3<&0` | Ends the loop over the lines of the spec file (line 12). `3<&0` makes file descriptor 3 a copy of the standard input for the whole loop. The `read` of line 12 uses descriptor 3. The loop ends when the spec file has no more lines. |

### Owner of the result files and summary (lines 35 to 36)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `sudo -n chown -R $(id -un): $out 2>/dev/null` | Makes the user the owner of every file in the result folder. `perf` created the `.perf` files as root, so root owns them. `id -un` prints the name of the user. `chown -R` changes the owner of the folder and of everything in it. The colon after the name also sets the group to the login group of that user. `sudo -n` runs the command as root without a password prompt. `2>/dev/null` discards an error message. |
| 36 | `echo "done $out"; grep -c '^rc 0' $out/launches.txt; grep -c 'ended' $out/launches.txt; wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt` | Prints a short summary to the standard output: `done` and the path of the result folder, then the number of `rc` lines with the status 0 (`grep -c` counts the lines of `launches.txt` that start with `rc 0`), then the number of lines that hold the text `ended` (the lines that line 27 writes), then the size of `stderr.txt` in bytes, then the first 600 bytes of `stderr.txt`. The exit status of `rgc.sh` is the status of the last command, `head`. It does not depend on the exit status of a process. |

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC3-20261115T194737Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that line 9 builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
