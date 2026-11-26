# `rx.sh` explained

- Source file: `w120-2026-11-15/rx.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 29 lines, 2027 bytes).
- sha256 of the source when this page was built: `42023e5e3246a97f6885f57262b9168eef3207e7da5dd4c44840e48e301422c9`.
- Role in the whole-chip test: Runner script: starts one bwx12 process per spec line and records its exit status.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

rx.sh runs one benchmark process per line of a spec file, on the CPUs 0 to 119. It stores the output of each process as a csv file in a new result folder. It also writes the machine state before the run (`env.txt`) and the launch time and the exit status of each process (`launches.txt`).

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rerun**: the whole-chip read test of 2026-11-17, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process**: a process is one start of a benchmark binary.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **Spec file**: a text file that `rx.sh` reads as its input. Each line is `tag|arguments of the binary` and gives one process. The tag becomes the name of the csv file of that process.
- **csv file**: a text file whose lines hold values separated by commas.
- **Marker file**: the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. The messages of rx.sh, `ra.sh` and go2.sh do not say what the file stands for. None of the scripts that test the file says who creates it. Since 2026-11-24 the message in line 20 of go.sh says what the file stands for: Jeremy or someone else is using CRB. Jeremy is another user of CRB. The page `go.sh.md` in the folder of go.sh (the explanation of go.sh) names the notes that say this. The facts sheet of the rerun says that another user creates it during a performance test [Ref7].
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks, for example `1/1013` [Ref5].
- **Runnable tasks**: the number before the slash in the fourth field of `/proc/loadavg`: the processes and threads that are runnable at the moment of the reading [Ref5].
- **%CPU**: the column pcpu of the tool ps. It is the CPU time that a process has used, divided by the time since the process started [Ref8]. So it is an average over the life of the process.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **rc, exit status**: the number that a process returns when it ends. 0 means success. `launches.txt` writes it as `rc`.
- **Process id (pid)**: the number that Linux gives to a process.
- **CPU list**: the CPUs on which Linux may run a process (its CPU affinity). A child process starts with the list of its parent [Ref6].
- **taskset**: a Linux tool. `taskset -c 0-119 COMMAND` starts a command that may run on the CPUs 0 to 119 only. `taskset -cp PID` prints the CPU list of a running process.
- **UTC**: Coordinated Universal Time. All times of the run are written in UTC.

</details>

## Main flow

1. Read the three arguments: the name for the result folder, the path of the binary, the expected sha256 (lines 5-6).
2. Stop with exit status 3 when the marker file exists. Stop with exit status 2 when the sha256 of the binary differs (lines 7-8).
3. Create the result folder `w120-<name>-<UTC time>` and write `env.txt` (lines 9-10).
4. For each spec line: test the marker file, wait until at most 2 tasks are runnable (at most 40 s), sleep 5 s, append the `launch` line to `launches.txt` (lines 11-16).
5. Start the binary in the background under `taskset -c 0-119`, with its output in `<tag>.csv`, its error messages in `stderr.txt` and an empty input (line 17).
6. Test once per second whether the process still exists. Kill it and stop with exit status 3 when the marker file appears (lines 18-19).
7. Take the exit status of the process with `wait` and append the `rc` line to `launches.txt` (line 20).
8. After the last spec line: print the result folder, the line count of `launches.txt`, the `rc` lines that are not 0, and the size and the first 600 bytes of `stderr.txt` (line 22).

## Behavior a reader must know

- rx.sh measures nothing itself. It reads no clock for a rate and computes no rate. All timed intervals are inside the binary. The times in `launches.txt` have a step of 1 s and come from `date`.
- Exit status of rx.sh: 3 when the marker file exists (lines 7, 13, 19), 2 when the sha256 differs (line 8), otherwise the status of the last command `head` (line 22). A failed binary does not change it. A caller that needs the status of the binary must read the `rc` line. go.sh and go2.sh do this in their function `rxok`.
- The wait for at most 2 runnable tasks cannot stop the run. After 40 tries the script starts the process anyway and prints no message. The `launch` line holds `/proc/loadavg` as read after the wait and the 5 s pause.
- Thread placement: `taskset -c 0-119` gives the process the CPU list 0 to 119. bwx12 then pins thread i to entry i of its `--cpus` list [Ref3]. Both counts start at 0. The spec lines of the rerun hold `--threads 120 --cpus 0-63,64-119` [Ref2]. So thread i runs on CPU i.
- While the binary runs, the shell of rx.sh does three things once per second: it runs `kill -0`, it tests the marker file, and it starts one `sleep 1` process. rx.sh sets no CPU list for its own shell. So these steps run on the CPU list that rx.sh inherited [Ref6]. Under go.sh that list was 0-119 in the rerun [Ref4]. These are the CPUs of the benchmark threads.
- Insufficient data: the effect of this once-per-second poll on the measured rates. A comparison run of the same spec line without the poll loop would resolve it.
- Insufficient data: the CPU list of rx.sh under go2.sh. go2.sh does not print it [Ref4]. The command lines that started go.sh and go2.sh on CRB hold no `taskset` [Ref9]. The command of go2.sh is the command of go.sh with `go2-T72-` and `go2.sh` in place of `go-T72-` and `go.sh`. A line `taskset -cp $$` in go2.sh would resolve it for a later run.
- When the marker file appears during a process, rx.sh kills the process and ends. The csv file of that process then holds only what the binary wrote before the signal. `launches.txt` then holds a `launch` line without an `rc` line.
- rx.sh does not record the boot id, MemTotal or the memory speed. `env.txt` holds only the time, the Linux kernel release, the load, the logins, a process list and the binary. go.sh and go2.sh record the boot id and MemTotal in their state lines.
- Is the local rx.sh the script that ran in the rerun: go.sh and go2.sh hold the sha256 that rx.sh must have. Each of the two scripts tests the copy of rx.sh on CRB against this value before its first process. It stops the run when the copy differs [Ref10]. Line 20 of the local go.sh was edited on 2026-11-24 (the text of one message). The lines of go.sh that hold this value and its test are the same as in the text that ran [Ref10]. The logs of go.sh and go2.sh hold no line that starts with `FAILED`, and each log ends with `ALLDONE` [Ref11]. The local rx.sh has this sha256 (computed with `sha256sum` on 2026-11-21). So the local rx.sh has the content of the copy that the two scripts tested. The files that rx.sh wrote in the rerun hold no checksum of rx.sh.
- What `users` in a `launch` line shows: the number of lines that `who` prints. `env.txt` holds the lines of `who` themselves. go.sh and go2.sh were started through `ssh` (the remote login tool). The two `ssh` connections were open until these scripts ended [Ref9]. In the rerun all 9 `launch` lines show `users 0`, and no `env.txt` holds a line of `who` [Ref12]. So `who` did not list these connections. `users 0` does not show that no connection to CRB was open.

## Call sequence in the whole-chip test

- `go.sh:runx or go2.sh`: callers: 7 calls in parts L and C, 2 calls in control I
  - `rx.sh` (line 1): checks, result folder, env.txt, then the loop over the spec lines
    - `bwx12.c:main`: one process on CPUs 0-119: 120 threads, kernel sequence of the spec line
      - `bwx12.c:k_oldread`: old read kernel (parts L and C, control I)
      - `bwx12.c:k_read`: new read kernel (part C only)
      - `bwx12.c:k_asmread`: hand-written load-only loop (parts L and C, control I)
      - `bwx12.c:k_read_nop96, k_read_nop256, k_read_1pl`: test loops (part L and control I)

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-2026-11-15/rx.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (29 lines, 2027 bytes, sha256 `42023e5e3246a97f6885f57262b9168eef3207e7da5dd4c44840e48e301422c9`).
- The other sections of this page describe an older text of the file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh` (22 lines, sha256 `d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab`). Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

Line numbers of the older text and of the text shown here:

| Older text | Text shown here | Change |
|---|---|---|
| lines 1 to 3 | lines 1 to 3 | equal |
| (none) | line 4 | added |
| lines 4 to 6 | lines 5 to 7 | equal |
| (none) | lines 8 to 9 | added |
| lines 7 to 9 | lines 10 to 12 | equal |
| line 10 | lines 13 to 14 | changed |
| lines 11 to 14 | lines 15 to 18 | equal |
| (none) | line 19 | added |
| lines 15 to 20 | lines 20 to 25 | equal |
| (none) | line 26 | added |
| line 21 | line 27 | equal |
| (none) | line 28 | added |
| line 22 | line 29 | equal |

### Header comment (lines 1 to 4)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# rx.sh NAME BINARY SHA256 < spec   - generic runner for the 120-thread investigation, no root.` | Comment: the usage. The script takes three arguments: a name, the path of a binary and the sha256 that the binary must have. It reads a spec file as its input. By the comment it is the runner of the 120-thread investigation and needs no root rights. |
| 3 | `# spec lines: tag\|arguments of the binary. Marker file checked before and during every process. CPUs 0-119 only.` | Comment: each line of the spec file has the form `tag\|arguments of the binary` and gives one process. The marker file (line 6) is checked before and during every process. Line 22 limits each process to the CPUs 0 to 119. |
| 4 | `# hw.sh records the clock rate, the throttle flags and the power in OUT/hw (HW=off: no such record; exit status 7: it is not usable).` | Comment: the file `hw.sh` records the clock rate of the cores, the throttle flags and the power in the folder `hw` of the result folder. This is the hardware record. A throttle flag is set by the firmware when a thermal, power or current limit made a core deliver less than Linux requested. With `HW=off` no such record is made. The script ends with exit status 7 when the record is not usable. |

### Settings, checks and the start of the hardware record (lines 5 to 14)

| Line | Source | Explanation |
|---:|---|---|
| 5 | `set -u` | The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it. |
| 6 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 7 | `name=$1; BW=$2; sha=$3` | Reads the three arguments. `name` becomes a part of the name of the result folder. `BW` is the path of the binary to run. `sha` is the sha256 that the binary must have. |
| 8 | `HWDIR=${HWDIR:-$HOME/cache-perf/hwwatch-20261124}` | `HWDIR`: the folder that holds `hw.sh`. When the caller has set the variable `HWDIR` to a value that is not empty, that value is kept. If not, the folder is `$HOME/cache-perf/hwwatch-20261124`. |
| 9 | `if [ "${HW:-on}" = off ]; then hw_init() { :; }; hw_begin() { :; }; hw_end() { :; }; hw_done() { :; }; else . "$HWDIR/hw.sh" \|\| { echo "cannot read $HWDIR/hw.sh: stop"; exit 7; }; fi` | Chooses the hardware record. When the variable `HW` is `off`, the line defines four functions that do nothing: `hw_init`, `hw_begin`, `hw_end` and `hw_done`. The command `:` does nothing and succeeds. In every other case the line reads the file `hw.sh` into this shell (the command `.`). That file defines the real functions. When `hw.sh` cannot be read, the script prints a message that starts with `cannot read` and ends with exit status 7. |
| 10 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 3. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 11 | `echo "$sha  $BW" \| sha256sum -c - >/dev/null \|\| { echo "sha mismatch"; exit 2; }` | Checksum check of the binary. `echo` writes one line with the expected checksum and the path. `sha256sum -c -` reads that line, computes the sha256 of the binary and compares the two values. Its report goes to `/dev/null`, which discards it. When the values differ or the file cannot be read, the script prints `sha mismatch` and ends with exit status 2. |
| 12 | `out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `w120-`, then `name`, then the UTC time of this moment (`date -u`), for example `w120-T72L1-20261117T221329Z` [Ref1]. `mkdir -p` creates the folder. The time is read before the waits of line 18 and line 20. So it is at least 5 s before the start of the first process. |
| 13 | `{ date -u; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu \| head -6; echo "binary $BW $sha"; echo "hw ${HW:-on} power ${HW_POWER:-require}"; } > $out/env.txt` | Writes the file `env.txt` once, before any process. It holds, in this order: the UTC date and time (`date -u`), the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), a header line and the 5 processes with the highest %CPU (`ps` sorted by `pcpu`, then `head -6`), the word `binary` with the path and the expected sha256 of the binary, and the settings of the hardware record. The last line shows `on` and `require` when the variables `HW` and `HW_POWER` are not set or are empty. %CPU (`pcpu`) is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. |
| 14 | `hw_init $out \|\| { echo "hardware record not usable: stop"; exit 7; }` | Starts the hardware record for the result folder. `hw_init` first tests the tools (function `hw_check` of `hw.sh`). Then it writes the files `status.txt` and `probe.txt` in the folder `hw` of the result folder. Then it starts two background programs. The first is the frequency sampler (`hwwatch.py watch`, one sample per second unless `HW_PERIOD_S` says otherwise). The second is the vendor tool `atx` (Arm Telemetrix), which reads power, temperature and frequency values of the firmware. `atx` is started only when `HW_POWER` is `require`. Both are pinned to CPU 119 unless `HW_CPU` says otherwise, and line 28 stops them. So during the timed intervals of a 120-thread process on the CPUs 0 to 119 they share CPU 119 with one benchmark thread. `hw_init` also sets a trap that calls `hw_done` when the shell of the script ends. When `hw_init` fails, the script prints `hardware record not usable: stop` and ends with exit status 7. With `HW=off` the call does nothing (line 9). |

### Loop: one process per line of the spec file (lines 15 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 15 | `while IFS='\|' read -r tag args; do` | Starts the loop over the lines of the input, which is the spec file. `IFS='\|'` splits each line at the first `\|`. The text before it goes to `tag`. The rest of the line goes to `args`. `-r` keeps each backslash as it is. Each of the three spec files of the rerun holds one line. So each call of `rx.sh` in the rerun started one process [Ref2]. |
| 16 | `  [ -z "$tag" ] && continue` | Skips a line with an empty tag, for example an empty line. |
| 17 | `  [ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 3, before each process. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. |
| 18 | `  for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$r" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 40 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, for example `1/1019`. `cut -d/ -f1` keeps the number before the slash. This is the number of tasks that are runnable now [Ref5]. When the number is 2 or less, the loop ends. If not, the script sleeps 1 s and tests again. After 40 tries (about 40 s) the loop ends too, and the script goes on without a message. |
| 19 | `  c=$(printf '%s' "$args" \| sed -n 's/.*--cpus  *\([0-9][0-9,-]*\).*/\1/p'); hw_begin "$tag" "${c:-0-119}"` | Finds the CPU list of the process and takes the first snapshot of the hardware record. `sed` prints the value that follows `--cpus` in the arguments: a list of digits, commas and hyphens such as `0-63,64-119`. `c` is empty when the arguments hold no `--cpus`. `hw_begin` gets the tag and the CPU list. When `c` is empty, the list is `0-119`. `hw_begin` gives the process a numbered label and writes a snapshot of these CPUs to a file `NNN-TAG.before.txt` in the folder `hw`. By the comment in `hw.sh`, this call must stand before the quiet time of the launch. The quiet time is the pause of line 20. |
| 20 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 21 | `  echo "launch $tag utc $(date -u +%T) load $(cat /proc/loadavg) users $(who \| wc -l) args $args" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the UTC time (hours, minutes, seconds), the content of `/proc/loadavg`, the number of logins and the arguments. This is the last reading of the machine state before the process starts. |
| 22 | `  taskset -c 0-119 $BW $args > $out/$tag.csv 2>> $out/stderr.txt < /dev/null &` | Starts the binary in the background (`&`). The script goes on immediately. `taskset -c 0-119` allows the new process to run on the CPUs 0 to 119 only. Then `taskset` replaces itself with the binary in the same process. So the process id of line 23 is the process id of the binary. `$args` has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary. The standard output of the binary goes to the file `TAG.csv` in the result folder. Error messages are appended to `stderr.txt`. The input is `/dev/null`, an empty input. So the binary cannot read the rest of the spec file. `rx.sh` pins no thread. `bwx12` pins each thread to one CPU of its `--cpus` argument [Ref3]. |
| 23 | `  pid=$!` | `pid`: the process id of the process that line 22 started. |
| 24 | `  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done` | Waits for the process and watches the marker file. `kill -0 $pid` sends no signal. It only tests whether the process still exists. The loop runs as long as it exists. Marker check 3 of 3, once per second: when the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. So `rx.sh` sees the end of the binary up to about 1 s late. This loop runs in the shell of `rx.sh` while the binary measures. Each turn starts one `sleep` process. The `taskset` of line 22 limits only the binary. The shell of `rx.sh` and its `sleep` processes may run on every CPU that the caller of `rx.sh` may use. |
| 25 | `  wait $pid; echo "rc $? $tag utc $(date -u +%T)" >> $out/launches.txt` | `wait $pid` returns the exit status of the binary. The script appends the line `rc <exit status> <tag> utc <time>` to `launches.txt`. It does not test the status. The time in this line can be about 1 s later than the real end of the process (line 24). |
| 26 | `  hw_end` | Takes the second snapshot of the hardware record, after the process (file `NNN-TAG.after.txt`). `hw_end` also tests that the sampler is still running, and `atx` too when `HW_POWER` is `require`. When a snapshot fails or a program is not running, `hw_end` adds a line that starts with `FAILED` to the file `status.txt` in the folder `hw`. It does not stop the script. |
| 27 | `done` | Ends the loop. The loop ends when the input has no more lines. |

### End of the hardware record and summary (lines 28 to 29)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `hw_done` | Stops the hardware record. `hw_done` ends the sampler and `atx`, adds its last lines to `status.txt` and removes the trap of line 14. |
| 29 | `echo "done $out"; grep -c . $out/launches.txt; grep '^rc' $out/launches.txt \| grep -v '^rc 0' ; wc -c < $out/stderr.txt; head -c 600 $out/stderr.txt` | Prints a short summary to the standard output: `done` and the path of the result folder, then the number of non-empty lines of `launches.txt` (2 per finished process: one `launch` line and one `rc` line), then every `rc` line whose status is not 0, then the size of `stderr.txt` in bytes, then the first 600 bytes of `stderr.txt`. The exit status of `rx.sh` is the status of the last command, `head`. It does not depend on the exit status of the binary. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z`: example of a result folder of rx.sh. It holds a6456.csv, env.txt, launches.txt (one `launch` line, one `rc 0` line) and stderr.txt (0 bytes).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec, cfwd.spec, crev.spec`: the three spec files of the rerun. Each holds one line with the tag (a6456, cfwd, crev) and the arguments, among them `--threads 120 --cpus 0-63,64-119`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: source of bwx12. Line 3011: thread i gets entry `i % ncpus` of the `--cpus` list. Line 1642: the thread pins itself to that CPU with `pin_cpu` (line 415, `sched_setaffinity`). Line 2911: `restrict_cpus` removes every CPU above 119 from the allowed set.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log`: log of go.sh in the rerun. Line 5: `affinity of this shell: pid 4864's current affinity list: 0-119`. The log of go2.sh holds no such line.
- [Ref5] external source: Linux manual page proc(5), entry /proc/loadavg (meaning of the five fields).
- [Ref6] external source: Linux manual page sched_setaffinity(2) (a child process inherits the CPU affinity of its parent).
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: facts sheet of the rerun. Lines 38 to 89 hold its word list. The definitions under "Words used here" come from there.
- [Ref8] external source: manual page ps(1) of procps-ng, entry "%cpu" (alias pcpu). The ps version on CRB was not checked.
- [Ref9] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: the transcript of the AI agent (Claude Code) that ran the rerun on 2026-11-17, one JSON record per line. It lies outside the project folder. Line 313 holds the command line that started go.sh on CRB. Line 365 holds the one that started go2.sh. Both have the form `nohup setsid <script> > <log file> 2>&1 < /dev/null &`. After this part each command line holds `wait $pid`, then an `echo` of the exit status of the script, then `cat` of the log file. Lines 336 and 378 hold the outputs, with `go.sh exit status 0` and `go2.sh exit status 0`. The agent sent them to CRB with `ssh` (the remote login tool), as the user `jhan`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh and /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go2.sh`: the two scripts that call rx.sh in the rerun. Line 14 of go.sh and line 11 of go2.sh hold `RXSHA=d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab`. Line 22 of go.sh and line 18 of go2.sh test the file rx.sh against this value with `sha256sum -c`. When it differs, they call the function `fail`, which ends the script with exit status 1. Line 20 of the local go.sh was edited on 2026-11-24 (the text of one message). Lines 14 and 22 of go.sh are the same as in the text that ran. The page `go.sh.md` in the folder of go.sh (the explanation of go.sh) gives the proof.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/results/go-T72-20261117T221209Z.log and /home/jhan/workspace/titan/cache-perf/crb/results/go2-T72-20261117T222335Z.log`: the logs of go.sh and go2.sh in the rerun. Neither holds a line that starts with `FAILED` (counted with `grep -c` on 2026-11-21). The last line of each log is `ALLDONE`.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z (and the folders of T72L2, T72L3, T72C1, T72C2, T72C3, T72C4, T72I1 and T72I2 next to it)`: the 9 result folders of rx.sh in the rerun. The `launch` line of each `launches.txt` holds `users 0`. Each `env.txt` has 10 lines. Line 3 is the content of `/proc/loadavg`, and line 4 is the title line of `ps`. So `who` wrote no line between them (read on 2026-11-21).
