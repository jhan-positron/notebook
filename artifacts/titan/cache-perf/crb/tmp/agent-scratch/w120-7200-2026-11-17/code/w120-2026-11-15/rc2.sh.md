# `rc2.sh` explained, line by line

- Source file: `w120-2026-11-15/rc2.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 35 lines, 2334 bytes).
- sha256 of the source when this page was built: `0585fe6939ca3435b8acb2884f17b78e853b9fdd2b8b6f8bb037dbb34c3ef231`.

## Short version: purpose

`rc2.sh` is a variant of the counter script `rc.sh`. It starts a benchmark binary once per line of a spec file and reads mesh counters as root with `sudo perf stat` while each process runs: one counter window of `WIN` seconds per event set. The difference is the form of an event set: a set line holds full `perf` event strings, and the script gives them to `perf` without a test and without a change.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. `rc2.sh` reads a file of the same form.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Full event string**: the name of a counter device, then `/`, the event with its parameters, and `/`. This is the form in which `perf` takes an event of a named device.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` (line 7).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 (lines 8 to 9).
3. Create the result folder, write `env.txt` and copy the event sets two times, as `sets.txt` and as `sets.ok` (lines 10 to 13).
4. For each line of the spec file: wait until the machine is quiet, write a `launch` line and start the binary in the background (lines 14 to 21).
5. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set (lines 22 to 30).
6. Wait for the end of the process and write its exit status to `launches.txt` (lines 31 to 32).
7. After the last line: make the user the owner of the result files and print a summary (lines 34 to 35).

## Behavior a reader must know

- Two commands run as root: the `sudo -n perf stat` of line 27 and the `sudo -n chown` of line 34. The header comment names `perf stat` only.
- No event is tested before the run. When `perf` cannot count an event, or when `sudo` would need a password, the script goes on: it does not test the exit status of `perf`. The error message of `perf` goes to `stderr.txt`, and the summary of line 35 prints the first 800 bytes of that file.
- The script times nothing of the benchmark. The runner times its own interval. A counter window is the run time of `sleep $WIN` under `perf stat`, and its counts are counts of the whole machine, not of one process.
- The windows of one process follow one after the other. So the timed interval must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. When the process ends earlier, line 24 writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script does not test that a window lies inside the timed interval. Only the pause of line 22 keeps the first window out of the start phase of the process.
- The marker file is checked four times: at the start, before each process, before each counter window, and once per second while the script waits for the end of a process. Each check ends the script with exit status 3. The last two also end the running process.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of the binary is written to `launches.txt` and is not tested.
- The comment of line 4 does not fit the code: the script adds no device name to an event.
- This script does not call `hw.sh`. It makes no hardware record.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rc2.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (35 lines, 2334 bytes, sha256 `0585fe6939ca3435b8acb2884f17b78e853b9fdd2b8b6f8bb037dbb34c3ef231`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 35. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Header comment (lines 1 to 4)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# rc2.sh NAME BINARY SHA256 SETS < spec - like rc.sh, but each set line holds full perf event strings: setname\|event,event,...` | Comment: the usage, with the same four arguments and the same input as `rc.sh`. The difference: each line of the file with the event sets holds full `perf` event strings, in the form `setname\|event,event,...`. A full event string names the counter device and the event with its parameters, for example `arm_cmn_0/mxp_p0_req_txflit_valid,bynodeid=1,nodeid=0x8/`. |
| 3 | `# spec lines: tag\|arguments of the binary (one long timed interval). SETS: file, one event set per line: setname\|ev1,ev2,...` | Comment: each line of the spec file has the form `tag\|arguments of the binary` and gives one process with one long timed interval. Each line of the file with the event sets has the form `setname\|events`, with commas between the events. In this script the commas fit the code: line 27 gives the events to `perf` as they stand, and `perf` takes a list with commas. |
| 4 | `# Each event EV is counted as arm_cmn_0/EV/ and arm_cmn_1/EV/. sudo is used for perf stat only. No system setting is changed.` | Comment: this line is equal to the same line of `rc.sh`. Its first sentence does not fit this script. `rc2.sh` does not put `arm_cmn_0/` and `arm_cmn_1/` around an event: line 27 gives each event string to `perf` as the set line holds it. So the set line itself must name the counter device. By the comment `sudo` (root rights) is used for `perf stat` only, and no system setting is changed. The code has one more `sudo` command: the `chown` of line 34. |

### Settings, checks and the result folder (lines 5 to 13)

| Line | Source | Explanation |
|---:|---|---|
| 5 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 6 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 7 | `name=$1; BW=$2; sha=$3; sets=$4; WIN=${WIN:-4}; DELAY=${DELAY:-9}` | Reads the four arguments. `name` becomes a part of the name of the result folder. `BW` is the path of the binary to run. `sha` is the sha256 that the binary must have. `sets` is the path of the file with the event sets. `WIN` is the length of one counter window in seconds. `DELAY` is the wait in seconds between the start of a process and its first counter window. `${WIN:-4}` keeps the value of `WIN` when the caller has set it to a value that is not empty. If not, the value is 4. In the same way the default of `DELAY` is 9. |
| 8 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 4. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 9 | `echo "$sha  $BW" \| sha256sum -c - >/dev/null \|\| { echo "sha mismatch"; exit 2; }` | Checksum check of the binary. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the binary and compares the two values. Its report goes to `/dev/null`, which discards it. When the values differ or the file cannot be read, the script prints `sha mismatch` and ends with exit status 2. |
| 10 | `out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `w120-`, then `name`, then the UTC time of this moment (`date -u`), for example `w120-RC2-20261115T192222Z` [Ref2]. `mkdir -p` creates the folder. The time is read before the waits of line 17 and line 18. So it is at least 5 s before the start of the first process. |
| 11 | `{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha WIN $WIN DELAY $DELAY"; } > $out/env.txt` | Writes the file `env.txt` once, before any process. The braces group five commands, and `>` sends the output of all of them to the file. It holds, in this order: the UTC date and time (`date -u`), the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and one line with the word `binary`, the path and the expected sha256 of the binary, and the values of `WIN` and `DELAY`. |
| 12 | `cp $sets $out/sets.txt` | Copies the file with the event sets into the result folder, under the name `sets.txt`. So the result folder shows which sets the caller asked for. |
| 13 | `cp $sets $out/sets.ok` | Copies the file with the event sets a second time, under the name `sets.ok`. In `rc.sh` the file `sets.ok` holds only the events that passed a test. `rc2.sh` has no such test: every set is used as it stands. The inner loop of lines 23 to 29 reads `sets.ok`. |

### Loop: one process per line of the spec file, one counter window per event set (lines 14 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 14 | `while IFS='\|' read -r tag args <&3; do` | Starts the loop over the lines of the spec file. `IFS='\|'` splits each line at the first `\|`. The text before it goes to `tag`. The rest of the line goes to `args`. `-r` keeps each backslash as it is. `<&3` makes `read` take the line from file descriptor 3. Line 33 makes descriptor 3 a copy of the standard input of the script, which is the spec file. |
| 15 | `  [ -z "$tag" ] && continue` | Skips a line with an empty tag, for example an empty line. |
| 16 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 4, before each process. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 17 | `  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 40 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, for example `1/1019`. `cut -d/ -f1` keeps the number before the slash. This is the number of tasks that are runnable now [Ref1]. When the number is 2 or less, the loop ends. If not, the script sleeps 1 s and tests again. After 40 tries (about 40 s) the loop ends too, and the script goes on without a message. |
| 18 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 19 | `  echo "launch $tag utc $(date -u +%T.%N) epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who \| wc -l) args $args" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the UTC time with nanoseconds (`%T.%N`), the word `epoch` with the time in seconds since 1970-01-01 00:00 UTC (`date +%s.%N`, also with nanoseconds), the content of `/proc/loadavg`, the number of logins and the arguments. This is the last reading of the machine state before the process starts. |
| 20 | `  taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &` | Starts the binary in the background (`&`). The script goes on immediately. `taskset -c 0-119` allows the new process to run on the CPUs 0 to 119 only. Then `taskset` replaces itself with the binary in the same process. So the process id of line 21 is the process id of the binary. `$args` has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary. The standard output of the binary goes to the file `TAG.csv` in the result folder. Error messages are appended to `stderr.txt`. The input is `/dev/null`, an empty input. So the binary cannot read the rest of the spec file. `rc2.sh` pins no thread. The runner pins each thread to one CPU of its `--cpus` argument (function `worker` of `bwx12.c`). |
| 21 | `  pid=$!` | `pid`: the process id of the process that line 20 started. |
| 22 | `  sleep $DELAY` | Waits `DELAY` seconds (9 s by default) after the start of the process, before the first counter window. In its start phase the runner writes every buffer once and runs a warm-up pass before it times (function `worker` of `bwx12.c`). This pause is the only thing that keeps the windows out of that phase. The script does not test that the timed interval has begun. |
| 23 | `  while IFS='\|' read -r sn evs; do` | Starts the inner loop over the lines of `sets.ok` (line 29 gives that file as the input). `sn` is the name of the set and `evs` holds its events. Each pass takes one counter window. |
| 24 | `    kill -0 $pid 2>/dev/null \|\| { echo "process ended before set $sn of $tag" >> $out/launches.txt; break; }` | Tests whether the process still exists (`kill -0` sends no signal). When it has ended, the script appends the line `process ended before set <set name> of <tag>` to `launches.txt`, and `break` leaves the inner loop. The sets that remain get no window for this process. |
| 25 | `    [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }` | Marker check 3 of 4, before each counter window. When the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` and ends with exit status 3. |
| 26 | `    echo "win $tag $sn start $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win <tag> <set name> start <time>` to `launches.txt`. The time is in seconds since 1970-01-01 00:00 UTC, with nanoseconds. |
| 27 | `    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/,$evs" -o $out/$tag.$sn.perf -- sleep $WIN 2>> $out/stderr.txt` | Takes one counter window. `sudo -n` runs `perf` as root and fails when it would need a password. `perf stat` counts events while a command runs. `-a`: on all CPUs, not only for that command. `-x,`: output lines with commas between the fields. `-e` gets the event list: `dtc_cycles` of the two counter devices, then the text of `evs` as the set line holds it. `-o` writes the counts to the file `TAG.SET.perf` in the result folder. The command after `--` is `sleep $WIN`. So the counter window lasts `WIN` seconds (4 s by default). Each line of the file holds: the count, the unit, the event, the time for which the counter ran in ns, and the percentage of the window for which it ran [Ref3]. Error messages are appended to `stderr.txt`. The exit status of `perf` is not tested. |
| 28 | `    echo "win $tag $sn end $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win <tag> <set name> end <time>` to `launches.txt`. The two `win` lines give the start and the end of the window as the shell saw them. They also cover the time that `sudo` and `perf` need to start and to end. |
| 29 | `  done < $out/sets.ok` | Ends the inner loop (line 23). `< $out/sets.ok` makes `sets.ok` the input of the loop. In this script `sets.ok` is a plain copy of the file with the event sets (line 13). |
| 30 | `  echo "sets done $tag $(date +%s.%N)" >> $out/launches.txt` | Appends the line `sets done <tag> <time>` to `launches.txt`. It marks the end of the last counter window of this process. |
| 31 | `  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done` | Waits for the process and watches the marker file. `kill -0 $pid` sends no signal. It only tests whether the process still exists. The loop runs as long as it exists. Marker check 4 of 4, once per second: when the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. So `rc2.sh` sees the end of the binary up to about 1 s late. |
| 32 | `  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt` | `wait $pid` returns the exit status of the binary. The script appends the line `rc <exit status> <tag> utc <time>` to `launches.txt`. It does not test the status. The time in this line can be about 1 s later than the real end of the process (line 31). |
| 33 | `done 3<&0` | Ends the loop over the spec file (line 14). `3<&0` makes file descriptor 3 a copy of the standard input for the whole loop. The `read` of line 14 uses descriptor 3. The loop ends when the spec file has no more lines. |

### Owner of the result files and summary (lines 34 to 35)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `sudo -n chown -R $(id -un): $out 2>/dev/null` | Makes the user the owner of every file in the result folder. `perf` created the `.perf` files as root, so root owns them. `id -un` prints the name of the user. `chown -R` changes the owner of the folder and of everything in it. The colon after the name also sets the group to the login group of that user. `sudo -n` runs the command as root without a password prompt. `2>/dev/null` discards an error message. |

Line 35 holds a backslash directly before a `|`. It stands outside the table:

```text
echo "done $out"; cat $out/unsupported.txt 2>/dev/null; grep -c '^win' $out/launches.txt; grep '^rc\|ended' $out/launches.txt; wc -c < $out/stderr.txt; head -c 800 $out/stderr.txt
```

Explanation of line 35: Prints a short summary to the standard output: `done` and the path of the result folder, then the content of `unsupported.txt` when that file exists, then the number of `win` lines of `launches.txt` (2 per counter window), then every line of `launches.txt` that starts with `rc` or holds the text `ended`, then the size of `stderr.txt` in bytes, then the first 800 bytes of `stderr.txt`. No line of `rc2.sh` writes `unsupported.txt`, so the `cat` command prints nothing. The exit status of `rc2.sh` is the status of the last command, `head`. It does not depend on the exit status of the binary.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC2-20261115T192222Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that line 10 builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
