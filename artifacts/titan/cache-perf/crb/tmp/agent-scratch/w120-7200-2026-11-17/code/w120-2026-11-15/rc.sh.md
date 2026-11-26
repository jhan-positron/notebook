# `rc.sh` explained, line by line

- Source file: `w120-2026-11-15/rc.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 45 lines, 2783 bytes).
- sha256 of the source when this page was built: `67acfa2a06eb72d9614f6f1e4b5c75ed2cfc112181bb119ffd7b4d8b0e63bc9a`.

## Short version: purpose

`rc.sh` starts a benchmark binary once per line of a spec file, on the CPUs 0 to 119. While each process runs its one long timed interval, the script reads the mesh counters as root with `sudo perf stat`: one counter window of `WIN` seconds per event set, each written to its own `.perf` file. It is the counter script of the 120-thread investigation for event sets that hold plain event names.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. `rc.sh` reads a file of the same form.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` (line 7).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 (lines 8 to 9).
3. Create the result folder and write `env.txt` and a copy of the event sets (lines 10 to 12).
4. Test every event with a `perf stat` run of the command `true`, and write the usable events to `sets.ok` (lines 14 to 21).
5. For each line of the spec file: wait until the machine is quiet, write a `launch` line and start the binary in the background (lines 22 to 29).
6. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set of `sets.ok` (lines 30 to 40).
7. Wait for the end of the process and write its exit status to `launches.txt` (lines 41 to 42).
8. After the last line: make the user the owner of the result files and print a summary (lines 44 to 45).

## Behavior a reader must know

- Three commands run as root: the two `sudo -n perf stat` commands of line 18 and line 37, and the `sudo -n chown` of line 44. The header comment names `perf stat` only.
- When `sudo` would need a password, every test of line 18 fails. Then every event is listed in `unsupported.txt`, `sets.ok` stays empty and no counter window is taken. The benchmark processes still run.
- The script times nothing of the benchmark. The runner times its own interval. A counter window is the run time of `sleep $WIN` under `perf stat`, and its counts are counts of the whole machine, not of one process.
- The windows of one process follow one after the other. So the timed interval must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. When the process ends earlier, line 32 writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script does not test that a window lies inside the timed interval. Only the pause of line 30 keeps the first window out of the start phase of the process.
- The marker file is checked four times: at the start, before each process, before each counter window, and once per second while the script waits for the end of a process. Each check ends the script with exit status 3. The last two also end the running process.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of the binary is written to `launches.txt` and is not tested.
- The test of line 18 uses the device `arm_cmn_0` only. Line 37 counts each event on both devices.
- The events of a set line must be separated by `;` (line 17). The header comment shows commas.
- This script does not call `hw.sh`. It makes no hardware record.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/rc.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (45 lines, 2783 bytes, sha256 `67acfa2a06eb72d9614f6f1e4b5c75ed2cfc112181bb119ffd7b4d8b0e63bc9a`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 45. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Header comment (lines 1 to 4)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# rc.sh NAME BINARY SHA256 SETS < spec - mesh counters (root, perf stat -a) during the steady interval of a benchmark process.` | Comment: the usage. The script takes four arguments: a name, the path of a binary, the sha256 that the binary must have and the path of a file with event sets. It reads a spec file as its input. By the comment it reads the mesh counters as root (`perf stat -a`) while a benchmark process is in its steady timed interval. |
| 3 | `# spec lines: tag\|arguments of the binary (one long timed interval). SETS: file, one event set per line: setname\|ev1,ev2,...` | Comment: each line of the spec file has the form `tag\|arguments of the binary` and gives one process with one long timed interval. Each line of the file with the event sets has the form `setname\|events`. The comment shows commas between the events. The code does not fit that: line 17 splits the events at `;`. |
| 4 | `# Each event EV is counted as arm_cmn_0/EV/ and arm_cmn_1/EV/. sudo is used for perf stat only. No system setting is changed.` | Comment: each event is counted two times, as an event of `arm_cmn_0` (the counter device of mesh 0) and of `arm_cmn_1` (mesh 1). By the comment `sudo` (root rights) is used for `perf stat` only, and no system setting is changed. The code has one more `sudo` command: the `chown` of line 44. |

### Settings, checks and the result folder (lines 5 to 12)

| Line | Source | Explanation |
|---:|---|---|
| 5 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 6 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 7 | `name=$1; BW=$2; sha=$3; sets=$4; WIN=${WIN:-4}; DELAY=${DELAY:-9}` | Reads the four arguments. `name` becomes a part of the name of the result folder. `BW` is the path of the binary to run. `sha` is the sha256 that the binary must have. `sets` is the path of the file with the event sets. `WIN` is the length of one counter window in seconds. `DELAY` is the wait in seconds between the start of a process and its first counter window. `${WIN:-4}` keeps the value of `WIN` when the caller has set it to a value that is not empty. If not, the value is 4. In the same way the default of `DELAY` is 9. |
| 8 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 4. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 9 | `echo "$sha  $BW" \| sha256sum -c - >/dev/null \|\| { echo "sha mismatch"; exit 2; }` | Checksum check of the binary. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the binary and compares the two values. Its report goes to `/dev/null`, which discards it. When the values differ or the file cannot be read, the script prints `sha mismatch` and ends with exit status 2. |
| 10 | `out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `w120-`, then `name`, then the UTC time of this moment (`date -u`), for example `w120-RC1-20261115T190208Z` [Ref2]. `mkdir -p` creates the folder. The time is read before the event tests of lines 15 to 21 and before the waits of line 25 and line 26. So it is at least 5 s before the start of the first process. |
| 11 | `{ date -u; uname -r; cat /proc/loadavg; who; echo "binary $BW $sha WIN $WIN DELAY $DELAY"; } > $out/env.txt` | Writes the file `env.txt` once, before any process. The braces group five commands, and `>` sends the output of all of them to the file. It holds, in this order: the UTC date and time (`date -u`), the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and one line with the word `binary`, the path and the expected sha256 of the binary, and the values of `WIN` and `DELAY`. |
| 12 | `cp $sets $out/sets.txt` | Copies the file with the event sets into the result folder, under the name `sets.txt`. So the result folder shows which sets the caller asked for. |

### Test of every event: which events can be counted on this machine (lines 13 to 21)

| Line | Source | Explanation |
|---:|---|---|
| 13 | `# keep only the events that open on this machine` | Comment: lines 14 to 21 keep only the events that open on this machine. An event opens when `perf` can start a counter for it. |
| 14 | `: > $out/sets.ok` | Creates `sets.ok` as an empty file. The command `:` does nothing, and `>` creates the file or cuts it to the length 0. Line 20 adds the lines. |
| 15 | `while IFS='\|' read -r sn evs; do` | Starts the loop over the lines of the file with the event sets (line 21 gives that file as the input of the loop). `IFS='\|'` splits each line at the first `\|`. The text before it goes to `sn`, the name of the set. The rest goes to `evs`, the events of the set. `-r` keeps each backslash as it is. |
| 16 | `  [ -z "$sn" ] && continue; ok=` | Skips a line with an empty set name, for example an empty line. For every other line, `ok=` empties the list of the events that passed the test. |
| 17 | `  for e in ${evs//;/ }; do` | Starts the loop over the events of one set. `${evs//;/ }` is the text of `evs` with every `;` replaced by a space. The shell splits the result at the spaces. So `e` holds one event name per pass. |
| 18 | `    if sudo -n perf stat -a -x, -e "arm_cmn_0/$e/" -o /dev/null -- true 2>/dev/null; then ok="$ok;$e"; else echo "unsupported $sn $e" >> $out/unsupported.txt; fi` | Tests one event. `sudo -n` runs `perf` as root and fails when it would need a password. `perf stat` counts events while a command runs. `-a`: on all CPUs, not only for that command. `-x,`: output lines with commas between the fields. `-e`: the event `e` of the counter device `arm_cmn_0`. `-o /dev/null` discards the counts. The command after `--` is `true`, which ends at once. `2>/dev/null` discards the error messages. So only the exit status counts. On success the event is added to `ok` with a `;` before it. On failure a line with `unsupported`, the set name and the event is appended to `unsupported.txt`. The device `arm_cmn_1` is not tested. |
| 19 | `  done` | Ends the loop over the events of one set (line 17). |
| 20 | `  [ -n "$ok" ] && echo "$sn\|${ok#;}" >> $out/sets.ok` | `-n` tests that the text of `ok` is not empty: at least one event passed. Then the line appends one line to `sets.ok`: the set name, `\|` and the events that passed, with `;` between them. `${ok#;}` is the text of `ok` without the `;` at its start. A set without a usable event gets no line. |
| 21 | `done < $sets` | Ends the loop over the event sets (line 15). `< $sets` makes the file with the event sets the input of the loop. |

### Loop: one process per line of the spec file, one counter window per event set (lines 22 to 43)

| Line | Source | Explanation |
|---:|---|---|
| 22 | `while IFS='\|' read -r tag args <&3; do` | Starts the loop over the lines of the spec file. `IFS='\|'` splits each line at the first `\|`. The text before it goes to `tag`. The rest of the line goes to `args`. `-r` keeps each backslash as it is. `<&3` makes `read` take the line from file descriptor 3. Line 43 makes descriptor 3 a copy of the standard input of the script, which is the spec file. |
| 23 | `  [ -z "$tag" ] && continue` | Skips a line with an empty tag, for example an empty line. |
| 24 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 4, before each process. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 25 | `  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 40 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, for example `1/1019`. `cut -d/ -f1` keeps the number before the slash. This is the number of tasks that are runnable now [Ref1]. When the number is 2 or less, the loop ends. If not, the script sleeps 1 s and tests again. After 40 tries (about 40 s) the loop ends too, and the script goes on without a message. |
| 26 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 27 | `  echo "launch $tag utc $(date -u +%T.%N) epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who \| wc -l) args $args" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the UTC time with nanoseconds (`%T.%N`), the word `epoch` with the time in seconds since 1970-01-01 00:00 UTC (`date +%s.%N`, also with nanoseconds), the content of `/proc/loadavg`, the number of logins and the arguments. This is the last reading of the machine state before the process starts. |
| 28 | `  taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &` | Starts the binary in the background (`&`). The script goes on immediately. `taskset -c 0-119` allows the new process to run on the CPUs 0 to 119 only. Then `taskset` replaces itself with the binary in the same process. So the process id of line 29 is the process id of the binary. `$args` has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary. The standard output of the binary goes to the file `TAG.csv` in the result folder. Error messages are appended to `stderr.txt`. The input is `/dev/null`, an empty input. So the binary cannot read the rest of the spec file. `rc.sh` pins no thread. The runner pins each thread to one CPU of its `--cpus` argument (function `worker` of `bwx12.c`). |
| 29 | `  pid=$!` | `pid`: the process id of the process that line 28 started. |
| 30 | `  sleep $DELAY` | Waits `DELAY` seconds (9 s by default) after the start of the process. By the header comment the counter windows must lie in the steady timed interval. This pause is the only thing that keeps them out of the start phase, in which the runner writes every buffer once and runs a warm-up pass (function `worker` of `bwx12.c`). The script does not test that the timed interval has begun. |
| 31 | `  while IFS='\|' read -r sn evs; do` | Starts the inner loop over the lines of `sets.ok` (line 39 gives that file as the input). `sn` is the name of the set and `evs` holds its events. Each pass takes one counter window. |
| 32 | `    kill -0 $pid 2>/dev/null \|\| { echo "process ended before set $sn of $tag" >> $out/launches.txt; break; }` | Tests whether the process still exists (`kill -0` sends no signal). When it has ended, the script appends the line `process ended before set <set name> of <tag>` to `launches.txt`, and `break` leaves the inner loop. The sets that remain get no window for this process. |
| 33 | `    [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }` | Marker check 3 of 4, before each counter window. When the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` and ends with exit status 3. |
| 34 | `    el=` | `el=`: empties the event list of this window. |
| 35 | `    for e in ${evs//;/ }; do el="$el,arm_cmn_0/$e/,arm_cmn_1/$e/"; done` | Builds the event list. For each event of the set, the loop appends `,arm_cmn_0/EV/,arm_cmn_1/EV/` to `el`, where `EV` stands for the event name. So each event is counted on the counter devices of both meshes. |
| 36 | `    echo "win $tag $sn start $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win <tag> <set name> start <time>` to `launches.txt`. The time is in seconds since 1970-01-01 00:00 UTC, with nanoseconds. |
| 37 | `    sudo -n perf stat -a -x, -e "arm_cmn_0/dtc_cycles/,arm_cmn_1/dtc_cycles/$el" -o $out/$tag.$sn.perf -- sleep $WIN 2>> $out/stderr.txt` | Takes one counter window. `sudo -n perf stat -a -x,` works as in line 18. `-e` gets the event list: `dtc_cycles` of both devices, then the events of the set from `el`. The analysis script `anc.py` uses `dtc_cycles` as the number of clock cycles of a mesh. `-o` writes the counts to the file `TAG.SET.perf` in the result folder. The command after `--` is `sleep $WIN`. So the counter window lasts `WIN` seconds (4 s by default). Each line of the file holds, with commas between them: the count, the unit, the event, the time for which the counter ran in ns, and the percentage of the window for which it ran [Ref3]. Error messages are appended to `stderr.txt`. The script does not test the exit status of `perf`. |
| 38 | `    echo "win $tag $sn end $(date +%s.%N)" >> $out/launches.txt` | Appends the line `win <tag> <set name> end <time>` to `launches.txt`. The two `win` lines give the start and the end of the window as the shell saw them. They also cover the time that `sudo` and `perf` need to start and to end. |
| 39 | `  done < $out/sets.ok` | Ends the inner loop (line 31). `< $out/sets.ok` makes `sets.ok` the input of the loop. So only the events that passed the test of line 18 are counted. |
| 40 | `  echo "sets done $tag $(date +%s.%N)" >> $out/launches.txt` | Appends the line `sets done <tag> <time>` to `launches.txt`. It marks the end of the last counter window of this process. |
| 41 | `  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done` | Waits for the process and watches the marker file. `kill -0 $pid` sends no signal. It only tests whether the process still exists. The loop runs as long as it exists. Marker check 4 of 4, once per second: when the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. So `rc.sh` sees the end of the binary up to about 1 s late. |
| 42 | `  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt` | `wait $pid` returns the exit status of the binary. The script appends the line `rc <exit status> <tag> utc <time>` to `launches.txt`. It does not test the status. The time in this line can be about 1 s later than the real end of the process (line 41). |
| 43 | `done 3<&0` | Ends the loop over the spec file (line 22). `3<&0` makes file descriptor 3 a copy of the standard input for the whole loop. The `read` of line 22 uses descriptor 3. The loop ends when the spec file has no more lines. |

### Owner of the result files and summary (lines 44 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 44 | `sudo -n chown -R $(id -un): $out 2>/dev/null` | Makes the user the owner of every file in the result folder. `perf` created the `.perf` files as root, so root owns them. `id -un` prints the name of the user. `chown -R` changes the owner of the folder and of everything in it. The colon after the name also sets the group to the login group of that user. `sudo -n` runs the command as root without a password prompt. `2>/dev/null` discards an error message. |

Line 45 holds a backslash directly before a `|`. It stands outside the table:

```text
echo "done $out"; cat $out/unsupported.txt 2>/dev/null; grep -c '^win' $out/launches.txt; grep '^rc\|ended' $out/launches.txt; wc -c < $out/stderr.txt; head -c 800 $out/stderr.txt
```

Explanation of line 45: Prints a short summary to the standard output: `done` and the path of the result folder, then the content of `unsupported.txt` when that file exists, then the number of `win` lines of `launches.txt` (2 per counter window), then every line of `launches.txt` that starts with `rc` or holds the text `ended`, then the size of `stderr.txt` in bytes, then the first 800 bytes of `stderr.txt`. The exit status of `rc.sh` is the status of the last command, `head`. It does not depend on the exit status of the binary.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC1-20261115T190208Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that line 10 builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
