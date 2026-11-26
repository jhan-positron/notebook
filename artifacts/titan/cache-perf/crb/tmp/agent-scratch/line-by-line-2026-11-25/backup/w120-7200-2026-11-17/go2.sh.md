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

## Source and explanation, side by side

<table style="table-layout:fixed;width:100%">
<colgroup><col style="width:56%"><col style="width:44%"></colgroup>
<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>
<tr><td colspan="2"><b>Header comment: why this control exists</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 1  #!/usr/bin/env bash
 2  # go2.sh - control for the rerun of 2026-11-17: the 120-thread line of r8.spec (like.spec), started from an idle machine, twice.
 3  # Reason: in go.sh every bwx12 process started about 5 s after other 120-thread work. The earlier runs of this line
 4  # (w120-R8 at 8000 MT/s, w120-w120-F72d12 at 7200 MT/s) started from an idle machine (1-minute load average 0.00 and 0.34).
 5  # "Idle" here = 1-minute load average below 1.0. No root. CPUs 0-119 only. rx.sh stops if /tmp/positron-perf.RUNNING exists.</pre></td><td valign="top">The comment gives the task and the reason.<ul><li>Task: run the line of <code>like.spec</code> twice, each time from an idle machine.</li><li>Reason: in go.sh every bwx12 process started about 5 s after other 120-thread work. The earlier runs of this line started from an idle machine.</li><li><code>w120-R8</code> and <code>w120-w120-F72d12</code> are the result folders of those earlier runs. Each of the two folders holds 5 launch lines. The first one has the arguments of <code>like.spec</code>. These two launch lines show the 1-minute load averages 0.00 and 0.34 [Ref5].</li><li><code>Idle</code> here means a 1-minute load average below 1.0.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 6  set -u</pre></td><td valign="top"><code>set -u</code>: the script stops when it uses a variable that was never set. The script does not use <code>set -e</code>. So a failed command does not stop it. Each check below calls <code>fail</code> by itself.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0"> 7  D=$HOME/cache-perf/w120-7200-20261117
 8  RX=$HOME/cache-perf/w120-20261115/rx.sh
 9  BW=$HOME/cache-perf/bwx12-20261115/bwx12
10  SHA=cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a
11  RXSHA=d315814fa650c53538af1d76df4f1f927ccb4b0c99dc45fd4cc1f4a94f590aab
12  BOOT=3bfc57a1-e235-4fe5-8c09-a94642f9b60b</pre></td><td valign="top">Paths on CRB, two expected checksums and the expected boot id. All six values are equal to those in go.sh.<ul><li><code>D</code>: the folder that holds <code>like.spec</code>. <code>RX</code>: the runner script <code>rx.sh</code>. <code>BW</code>: the binary bwx12.</li><li><code>SHA</code>: the sha256 that the file bwx12 must have. <code>RXSHA</code>: the sha256 that <code>rx.sh</code> must have.</li><li><code>BOOT</code>: the boot id that the running system must have.</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>state</code>: print one state line</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">13  state() { echo "== $1 utc $(date -u +%FT%TZ) boot $(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo | tr -s ' ') load $(cat /proc/loadavg) users $(who | wc -l) marker $([ -e /tmp/positron-perf.RUNNING ] &amp;&amp; echo present || echo absent) processes per user: $(ps -eo user= | sort | uniq -c | tr -s ' ' | tr '\n' ';')"; }</pre></td><td valign="top">Prints one line that starts with <code>==</code> and the label given as argument. It only reports. It stops nothing. The line holds:<ul><li>the UTC time and the boot id</li><li>the <code>MemTotal</code> line of <code>/proc/meminfo</code> (<code>tr -s ' '</code> reduces each run of spaces to one space)</li><li>the content of <code>/proc/loadavg</code>: the three load averages, the runnable tasks and all tasks as <code>1/1013</code>, and the newest process id [Ref7]</li><li>the number of logins: <code>who</code> prints one line per login, and <code>wc -l</code> counts the lines</li><li><code>present</code> or <code>absent</code> for the file <code>/tmp/positron-perf.RUNNING</code></li><li>the number of processes of each user: <code>ps -eo user=</code> prints the user of every process, and <code>sort | uniq -c</code> counts equal lines</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>fail</code>: stop the run</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">14  fail() { echo "FAILED: $1"; state abort; exit 1; }</pre></td><td valign="top">Prints <code>FAILED:</code> and the message. Then it prints a state line with the label <code>abort</code>. Then it ends go2.sh with exit status 1. Every failed check of go2.sh ends here, and no later step runs.</td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">15  echo "go2.sh pid $$ (stop everything: kill -TERM -- -$$)"</pre></td><td valign="top">Prints the process id of go2.sh and a command that stops the run.<ul><li><code>kill -TERM -- -&lt;pid&gt;</code> sends the termination signal to every process of the process group with that number.</li><li>This stops go2.sh and its child processes only when go2.sh is the leader of its process group. go2.sh does not make itself the leader.</li><li>In the rerun the start command ran go2.sh through the tool <code>setsid</code> [Ref10]. This tool starts a program as the leader of a new process group [Ref11]. So go2.sh was the leader in the rerun.</li></ul></td></tr>
<tr><td colspan="2"><b>Checks before the run</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">16  [ -e /tmp/positron-perf.RUNNING ] &amp;&amp; fail "RUNNING file present"</pre></td><td valign="top">Check of the marker file.<ul><li>Test: does the file <code>/tmp/positron-perf.RUNNING</code> exist.</li><li>On failure (the file exists): <code>fail</code> stops the run with <code>RUNNING file present</code>.</li><li><code>waitidle</code> (line 25) tests the file again at each of its tries. <code>rx.sh</code> tests it before the process and once per second while the process runs [Ref2].</li><li>Purpose: go2.sh does not say who creates the file or what the file stands for.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">17  exec 9&gt; "$HOME/cache-perf/results/go-T72.lock"; flock -n 9 || fail "another go.sh holds the lock"</pre></td><td valign="top">Lock against a second run.<ul><li><code>exec 9&gt; ...</code> opens the file <code>go-T72.lock</code> for writing as file descriptor 9 of the shell. It creates the file when it is missing.</li><li>Test: <code>flock -n 9</code> asks for an exclusive lock on that file and does not wait.</li><li>On failure (another process holds the lock, or the lock file could not be opened): <code>fail</code> stops the run with <code>another go.sh holds the lock</code>.</li><li>Purpose, by the message <code>another go.sh holds the lock</code>: go2.sh must not run at the same time as go.sh. go.sh uses the same lock file. A second go2.sh would fail here too.</li><li>The lock lasts as long as file descriptor 9 is open: until go2.sh and the child processes that inherited it have ended.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">18  echo "$RXSHA  $RX" | sha256sum -c - &gt; /dev/null || fail "rx.sh is not the script of 2026-11-15"
19  echo "$SHA  $BW" | sha256sum -c - &gt; /dev/null || fail "bwx12 is not the binary of 2026-11-15"</pre></td><td valign="top">Checksum checks of <code>rx.sh</code> (line 18) and of the binary bwx12 (line 19).<ul><li>Test: <code>sha256sum -c -</code> reads one line <code>checksum  path</code> from <code>echo</code>, computes the sha256 of that file and compares the two values. Its report goes to <code>/dev/null</code>, which discards it.</li><li>On failure (the content differs, or the file cannot be read): <code>fail</code> stops the run.</li><li>Purpose, by the messages: the two files must be the script and the binary of 2026-11-15.</li><li>Cross-check: the build record of bwx12 lists the value of <code>SHA</code> for the file <code>bwx12</code> [Ref4]. The binary itself is not in the local folders. The local copy of <code>rx.sh</code> has the value of <code>RXSHA</code> (computed with <code>sha256sum</code> on 2026-11-21) [Ref2].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">20  [ -s "$D/like.spec" ] || fail "missing $D/like.spec"</pre></td><td valign="top">File check.<ul><li>Test: <code>like.spec</code> exists and is not empty (<code>-s</code>).</li><li>On failure: <code>fail</code> with <code>missing &lt;path&gt;</code>.</li><li>go2.sh does not test the checksum of <code>like.spec</code>. In the rerun the <code>launch</code> lines of the two control processes hold the arguments of the local <code>like.spec</code> (compared with <code>diff</code> on 2026-11-21) [Ref6].</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">21  [ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || fail "boot id is not the boot checked at 12 modules, 7200 MT/s"</pre></td><td valign="top">Boot check.<ul><li>Test: the boot id of the running system is equal to <code>BOOT</code> (line 12).</li><li>On failure: <code>fail</code> stops the run.</li><li>Purpose, by the message: the run must happen in the boot that was checked at 12 modules and 7200 MT/s.</li><li>The check compares the boot id only. It does not read the memory speed or the number of modules.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">22  [ "$(awk '/^MemTotal/{print $2}' /proc/meminfo)" -ge 395000000 ] || fail "MemTotal below 395000000 kB: not 12 modules"</pre></td><td valign="top">Memory size check.<ul><li>Test: <code>awk</code> prints the second field of the <code>MemTotal</code> line of <code>/proc/meminfo</code>, a value in kB. The value must be 395000000 kB or more.</li><li>On failure: <code>fail</code> stops the run.</li><li>Purpose, by the message: a lower value means <code>not 12 modules</code>. The script does not say how the limit was chosen.</li><li>In the rerun each of the 6 state lines shows 395392808 kB [Ref1].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>rxok</code>: did the bwx12 process end with status 0</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">23  rxok() { local l; l=$(ls -d "$HOME"/cache-perf/results/w120-"$1"-*/launches.txt 2&gt;/dev/null | tail -1); [ -n "$l" ] &amp;&amp; [ "$(grep -c '^rc ' "$l")" = 1 ] &amp;&amp; [ "$(grep -c '^rc 0 ' "$l")" = 1 ]; }</pre></td><td valign="top"><code>rxok NAME</code> reads the file <code>launches.txt</code> of the newest result folder <code>w120-NAME-&lt;time&gt;</code>. Its text is equal to <code>rxok</code> in go.sh.<ul><li><code>ls -d ... | tail -1</code> lists the matching files in name order and keeps the last one. The time in the folder name puts the newest folder last.</li><li>The function succeeds only when a file was found, the file holds exactly 1 line that starts with <code>rc </code>, and it holds exactly 1 line that starts with <code>rc 0 </code>.</li><li><code>rx.sh</code> writes one line <code>rc &lt;exit status&gt; &lt;tag&gt;</code> per process. It ends with status 0 also when bwx12 failed [Ref2].</li></ul></td></tr>
<tr><td colspan="2"><b>Function <code>waitidle</code>: wait for an idle machine</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">24  # wait until the 1-minute load average is below 1.0 (at most 15 min)
25  waitidle() { local i; for i in $(seq 180); do [ -e /tmp/positron-perf.RUNNING ] &amp;&amp; fail "RUNNING file present"; awk '{exit !($1 &lt; 1.0)}' /proc/loadavg &amp;&amp; return 0; sleep 5; done; fail "1-minute load average not below 1.0 after 15 min"; }</pre></td><td valign="top">Tries up to 180 times:<ul><li>When the marker file exists, <code>fail</code> stops the run.</li><li><code>awk</code> reads <code>/proc/loadavg</code>. When the first field (the 1-minute load average) is below 1.0, <code>awk</code> ends with status 0 and the function returns. The run goes on.</li><li>If not, the function sleeps 5 s and tries again.</li><li>After 180 tries (180 x 5 s = 15 min) <code>fail</code> stops the run.</li><li>The test reads the 1-minute value only. It does not test the 5-minute value or the number of runnable tasks.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">26  state start</pre></td><td valign="top">State line with the label <code>start</code>.</td></tr>
<tr><td colspan="2"><b>Two control processes</b></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">27  for i in 1 2; do
28    waitidle
29    state "idle before T72I$i"
30    bash "$RX" T72I$i "$BW" "$SHA" &lt; "$D/like.spec" || fail "rx.sh T72I$i rc $?"
31    rxok T72I$i || fail "bwx12 T72I$i: exit status not 0 (launches.txt, stderr.txt)"
32    state "after T72I$i"
33  done</pre></td><td valign="top">Runs the same steps twice, with the names <code>T72I1</code> and <code>T72I2</code>.<ul><li>Line 28: <code>waitidle</code> (line 25) waits for a 1-minute load average below 1.0.</li><li>Line 29: a state line records the machine state at that moment.</li><li>Line 30: <code>rx.sh</code> runs one bwx12 process with the arguments of <code>like.spec</code> [Ref3]. The spec file is the input of <code>rx.sh</code>. On a non-zero exit status of <code>rx.sh</code>: <code>fail</code> stops the run.</li><li>Line 31: when <code>rxok</code> (line 23) does not succeed, <code>fail</code> stops the run.</li><li>Line 32: a state line after the process.</li><li><code>rx.sh</code> adds its own wait before the launch: until at most 2 tasks are runnable (at most 40 s), then 5 s [Ref2]. When more than 2 tasks are still runnable after the 40 s, <code>rx.sh</code> starts the process anyway. So bwx12 starts 5 s or more after the idle test.</li></ul></td></tr>
<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">34  state end
35  echo ALLDONE</pre></td><td valign="top">Final state line with the label <code>end</code>, then the word <code>ALLDONE</code>. The script reaches these lines only when no check called <code>fail</code>.</td></tr>
</table>

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
