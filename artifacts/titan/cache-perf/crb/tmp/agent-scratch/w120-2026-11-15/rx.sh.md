# `rx.sh` explained

- Source file: `rx.sh` in this folder (Bash script, 22 lines, 1419 bytes).
- sha256 of the source when this page was built: `d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab`.
- Role in the whole-chip test: Runner script: starts one bwx12 process per spec line and records its exit status.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header comment: usage</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  #!/usr/bin/env bash
 2  # rx.sh NAME BINARY SHA256 &lt; spec   - generic runner for the 120-thread investigation, no root.
 3  # spec lines: tag|arguments of the binary. Marker file checked before and during every process. CPUs 0-119 only.</pre></td><td valign="top">Usage: <code>rx.sh NAME BINARY SHA256</code>, with a spec file as input. Each line of the spec file is <code>tag|arguments of the binary</code> and gives one process. <code>Marker file</code> in the comment is the file <code>/tmp/positron-perf.RUNNING</code> (line 5). <code>CPUs 0-119 only</code> is set in line 17.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 4  set -u</pre></td><td valign="top"><code>set -u</code>: the script stops when it uses a variable that was never set. The script does not use <code>set -e</code>. So a failed command does not stop it.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 5  M=/tmp/positron-perf.RUNNING
 6  name=$1; BW=$2; sha=$3</pre></td><td valign="top"><code>M</code>: the path of the marker file. Then the three arguments:<ul><li><code>name</code>: a part of the name of the result folder</li><li><code>BW</code>: the path of the binary to run</li><li><code>sha</code>: the sha256 that the binary must have</li></ul></td></tr>
<tr><td colspan="2"><b>Checks before the first process</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 7  [ -e $M ] &amp;&amp; { echo "RUNNING file present: stop"; exit 3; }</pre></td><td valign="top">Marker check 1 of 3.<ul><li>Test: does the file <code>/tmp/positron-perf.RUNNING</code> exist.</li><li>On failure (the file exists): the script prints <code>RUNNING file present: stop</code> and ends with exit status 3. It has written no file at this point.</li><li>Purpose: the script does not say who creates the file or what the file stands for.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 8  echo "$sha  $BW" | sha256sum -c - &gt;/dev/null || { echo "sha mismatch"; exit 2; }</pre></td><td valign="top">Checksum check of the binary.<ul><li>Test: <code>sha256sum -c -</code> reads one line <code>checksum  path</code> from <code>echo</code>, computes the sha256 of the binary and compares it with the third argument. Its report goes to <code>/dev/null</code>, which discards it.</li><li>On failure (the content differs, or the file cannot be read): the script prints <code>sha mismatch</code> and ends with exit status 2.</li><li>Purpose: the script gives none. The caller chooses the expected value.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 9  out=$HOME/cache-perf/results/w120-$name-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out</pre></td><td valign="top">Result folder: <code>~/cache-perf/results/w120-&lt;name&gt;-&lt;UTC time&gt;</code>, for example <code>w120-T72L1-20261117T221329Z</code> [Ref1]. <code>mkdir -p</code> creates it. The time in the name is read here, before the wait of lines 14 and 15. So it is at least 5 s before the start of the first process.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">10  { date -u; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu | head -6; echo "binary $BW $sha"; } &gt; $out/env.txt</pre></td><td valign="top">Writes the file <code>env.txt</code> once, before any process. It holds, in this order:<ul><li>the UTC date and time (<code>date -u</code>)</li><li>the release of the running Linux kernel (<code>uname -r</code>)</li><li>the content of <code>/proc/loadavg</code></li><li>the logged-in users, one line each (<code>who</code>). It prints nothing when nobody is logged in.</li><li>a header line and the 5 processes with the highest %CPU (<code>ps</code> sorted by <code>pcpu</code>, then <code>head -6</code>)</li><li>the word <code>binary</code>, the path of the binary and the expected sha256</li></ul></td></tr>
<tr><td colspan="2"><b>Loop: one process per spec line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">11  while IFS='|' read -r tag args; do
12    [ -z "$tag" ] &amp;&amp; continue</pre></td><td valign="top">Reads the input (the spec file) line by line.<ul><li><code>IFS='|'</code> splits each line at the first <code>|</code>. The text before it goes to <code>tag</code>. The rest of the line goes to <code>args</code>.</li><li><code>-r</code> keeps each backslash as it is.</li><li>Line 12 skips a line with an empty tag, for example an empty line.</li><li>Each of the three spec files of the rerun holds one line. So each call of rx.sh starts one process [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">13    [ -e $M ] &amp;&amp; { echo "marker: stop"; exit 3; }</pre></td><td valign="top">Marker check 2 of 3, before each process. When the marker file exists, the script prints <code>marker: stop</code> and ends with exit status 3.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">14    for i in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg | cut -d/ -f1); [ "$r" -le 2 ] &amp;&amp; break; sleep 1; done</pre></td><td valign="top">Wait for at most 2 runnable tasks, with at most 40 tries.<ul><li>Test: <code>cut -d' ' -f4 /proc/loadavg</code> takes the fourth field, for example <code>1/1019</code>. <code>cut -d/ -f1</code> keeps the number before the slash. This is the number of tasks that are runnable now [Ref5].</li><li>When the number is 2 or less, the loop ends immediately.</li><li>If not, the script sleeps 1 s and tests again.</li><li>On failure (still above 2 after 40 tries, about 40 s): the loop ends too. The script goes on and starts the process. It prints no message.</li><li>Purpose: the script does not say why the limit is 2.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">15    sleep 5</pre></td><td valign="top">A fixed pause of 5 s after the wait.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">16    echo "launch $tag utc $(date -u +%T) load $(cat /proc/loadavg) users $(who | wc -l) args $args" &gt;&gt; $out/launches.txt</pre></td><td valign="top">Appends one <code>launch</code> line to <code>launches.txt</code>: the tag, the UTC time (hours:minutes:seconds), the content of <code>/proc/loadavg</code>, the number of logins, and the arguments. This is the last reading of the machine state before the process starts.</td></tr>
<tr><td colspan="2"><b>Start of the binary and wait for its end</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">17    taskset -c 0-119 $BW $args &gt; $out/$tag.csv 2&gt;&gt; $out/stderr.txt &lt; /dev/null &amp;</pre></td><td valign="top">Starts the binary in the background (<code>&amp;</code>). The script goes on immediately.<ul><li>CPU list: <code>taskset -c 0-119</code> allows the new process to run on the CPUs 0 to 119 only. Then <code>taskset</code> replaces itself with the binary in the same process. So the process id of line 18 is the process id of the binary.</li><li>Arguments: <code>$args</code> has no quotes. So the shell splits it at the spaces, and each word becomes one argument of the binary.</li><li>Output: the standard output of the binary goes to <code>&lt;tag&gt;.csv</code> in the result folder. <code>&gt;</code> creates the file, or empties it when it exists. Error messages are appended to <code>stderr.txt</code> (<code>2&gt;&gt;</code>).</li><li>Input: <code>/dev/null</code>, an empty input. So the binary cannot read the rest of the spec file, which is the input of the loop.</li><li>rx.sh pins no thread. bwx12 pins each thread to one CPU of its <code>--cpus</code> argument [Ref3].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">18    pid=$!
19    while kill -0 $pid 2&gt;/dev/null; do [ -e $M ] &amp;&amp; { kill $pid; echo "marker: killed"; exit 3; }; sleep 1; done</pre></td><td valign="top">Waits for the process and watches the marker file.<ul><li><code>pid=$!</code> keeps the process id of the started process.</li><li><code>kill -0 $pid</code> sends no signal. It only tests whether the process still exists. The loop runs as long as it exists.</li><li>Marker check 3 of 3, once per second: when the marker file exists, <code>kill $pid</code> sends the termination signal to the process. The script prints <code>marker: killed</code> and ends with exit status 3. It writes no <code>rc</code> line then.</li><li>If the marker file does not exist, <code>sleep 1</code> waits 1 s.</li><li>So rx.sh sees the end of the binary up to about 1 s late. This loop runs in the shell of rx.sh while the binary measures.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">20    wait $pid; echo "rc $? $tag utc $(date -u +%T)" &gt;&gt; $out/launches.txt
21  done</pre></td><td valign="top"><code>wait $pid</code> returns the exit status of the binary. The script appends the line <code>rc &lt;exit status&gt; &lt;tag&gt; utc &lt;time&gt;</code> to <code>launches.txt</code>. It does not test the status, and it goes on with the next spec line. The time in this line can be about 1 s later than the real end of the process (the poll of line 19).</td></tr>
<tr><td colspan="2"><b>Summary and exit status</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">22  echo "done $out"; grep -c . $out/launches.txt; grep '^rc' $out/launches.txt | grep -v '^rc 0' ; wc -c &lt; $out/stderr.txt; head -c 600 $out/stderr.txt</pre></td><td valign="top">Prints a short summary to the standard output:<ul><li><code>done</code> and the path of the result folder</li><li>the number of non-empty lines of <code>launches.txt</code> (2 per finished process: one <code>launch</code> line and one <code>rc</code> line)</li><li>every <code>rc</code> line whose status is not 0</li><li>the size of <code>stderr.txt</code> in bytes</li><li>the first 600 bytes of <code>stderr.txt</code></li><li>The exit status of rx.sh is the status of the last command, <code>head</code>. It does not depend on the exit status of the binary.</li></ul></td></tr>
</table>

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
