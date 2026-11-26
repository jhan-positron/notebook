# `run_chip.sh` explained, line by line

- Source file: `asct-2026-11-16/crb/run_chip.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 72 lines, 4651 bytes).
- sha256 of the source when this page was built: `e1ebdd2fb657b3a6f1989cf3ad30de7e4d0907362a655a176c9728769174149a`.

## Short version: purpose

`run_chip.sh` runs the many-core part of the ASCT cross-check on CRB. Each process is one start of the ASCT benchmark binary with one read thread per CPU of a layout, up to 120 threads, and a buffer of 256 MiB per thread. The steps change the number of injected NOPs, the layout, the mix of reads and writes, and one step adds counters.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Probe binary, probe variant**: the same benchmark program, built by `prep.sh` with the flag `-DUSE_PROBE`. It holds the counter code of ASCT.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter capture**: the counter code of ASCT inside the probe binary. It reads a list of raw codes from the environment variable `DIETPERF_PMUv3`. It writes its counter files to the folder that `DIETPERF_OUTDIR` names.
- **Raw code**: the number that selects one counter event in the counter unit of the cores.
- **Event set**: a named list of counter events that one process counts together. The file `events.codes` holds one set per line.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Non-temporal store**: a store that tells the processor that the program will not read the data again soon.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Whole chip, 120 threads**: our runs use the CPUs 0 to 119 only: 64 threads on mesh 0 plus 56 threads on mesh 1.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next process when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists (lines 12 to 13).
2. Read the settings: the steps, the length of the measured phase and the fixed buffer size of 256 MiB per thread (lines 14 to 18).
3. Create the result folder, write the start state to `env.txt` and copy `events.codes` (lines 19 to 22).
4. Step `BASE`: 6 processes at 64+56 with 0 injected NOPs. Each process goes through the function `one`. It checks the two stop files, waits for a quiet machine, pauses 5 s, starts the binary with one `--bw-cpu` option per CPU (function `cpuflags`), watches the marker file and writes the exit status (line 46).
5. Step `DEF`: 3 processes of the same case with a measured phase of 0.25 s (line 47).
6. Step `NOPS`: 15 counts of injected NOPs at 64+56, first in rising order, then in falling order (lines 48 to 52).
7. Step `LAY`: the layouts 64+0, 0+56 and 56+56 at 0 and at 20 injected NOPs, 2 processes each (lines 53 to 55).
8. Step `MIX`: the traffic types 2 to 5 at 64+56, 2 processes each (lines 56 to 58).
9. Step `CNT`: the probe binary with each event set, at 64+56 with 0 and with 20 injected NOPs and at 64+0 with 0 injected NOPs (lines 59 to 68).
10. Print a short summary (lines 69 to 72).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures. By the decisions file, the rate of one process is the line `Total Bandwidth (MB/sec)` of its output, divided by 1000 to give GB/s [Ref1].
- By the description text of the analysis script `analyze.py`, the rate of one thread is its repetitions times the buffer size, divided by its time. The binary prints the repetitions and the time of each thread in a line that starts with `tid = `. A repetition is one pass over the buffer.
- By the decisions file, ASCT counts 64 bytes for each cache line, although its read loop loads 8 bytes of the line. The total of ASCT is the sum of the rates of the threads, and the threads measure over time spans of different length [Ref1].
- Thread placement: the script limits each process to the CPUs 0 to 119 (`taskset`) and passes one `--bw-cpu` option per CPU of the layout. The binary runs one read thread on each of these CPUs. The buffer is allocated inside the ASCT binary, whose source is not in this repo.
- One process runs at a time. Before each process the script waits until at most 2 tasks are runnable (at most about 60 s) and then 5 s more.
- Stops: the marker file and the STOP file before every process (exit status 3 and 4). During a process only the marker file is checked, once per second. When it appears, the script sends the termination signal to the process and ends with exit status 3.
- The exit status of a benchmark process is written to `launches.txt` but not tested.
- The steps run in the order of the file. The order of the words in `STEPS` does not change this.
- A wrong layout name does not stop the script (line 25). The binary would start without any `--bw-cpu` option. The layout names of this file are fixed in lines 46 to 63, so the case cannot happen without a change of the file.
- With the default settings and 7 event sets the script starts 80 processes: 6, 3, 30, 12, 8 and 21 for the six steps. The run of 2026-11-16 23:19 UTC started 80 processes [Ref2].
- That run used an earlier text of line 36 with the variable `r`. 8 result files of the steps `LAY` and `MIX` were overwritten. The two steps ran again at 23:44 UTC, after the variable got the name `rq` [Ref1].

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/run_chip.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (72 lines, 4651 bytes, sha256 `e1ebdd2fb657b3a6f1989cf3ad30de7e4d0907362a655a176c9728769174149a`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_chip.sh - many cores, ASCT read loop, 256 MiB per thread (the layout of the 2026-11-15 work:` | Comment: the purpose. Many cores run the read loop of ASCT, each thread with a buffer of 256 MiB. The thread layout is that of the work of 2026-11-15. |
| 3 | `# 64 threads on CPUs 0-63 + 56 threads on CPUs 64-119). No root. Never CPUs 120-127.` | Comment, continued: 64 threads on the CPUs 0 to 63 plus 56 threads on the CPUs 64 to 119. The script needs no root rights and never uses the CPUs 120 to 127. |
| 4 | `# Steps (STEPS selects): BASE  64+56, 0 injected NOPs, 6 processes` | Comment: the variable `STEPS` selects the steps. Step `BASE`: the layout 64+56 with 0 injected NOPs, 6 processes. |
| 5 | `#                        DEF   64+56, 0 injected NOPs, ASCT's default duration 0.25 s, 3 processes` | Comment: step `DEF`: the same case with the default length of the measured phase of ASCT, 0.25 s, 3 processes. |
| 6 | `#                        NOPS  64+56, injected NOPs (--bw-fine-delay) 1..180, 2 processes each` | Comment: step `NOPS`: the layout 64+56 with 1 to 180 injected NOPs (option `--bw-fine-delay`), 2 processes for each count. |
| 7 | `#                        LAY   layouts 64+0, 0+56, 56+56 at 0 and 20 injected NOPs, 2 processes each` | Comment: step `LAY`: the layouts 64+0, 0+56 and 56+56 at 0 and at 20 injected NOPs, 2 processes each. |
| 8 | `#                        MIX   64+56, the four read-write traffic types of ASCT's peak-bandwidth, 2 processes each` | Comment: step `MIX`: the layout 64+56 with the four traffic types of the peak-bandwidth benchmark of ASCT that mix reads and writes, 2 processes each. |
| 9 | `#                        CNT   ASCT's probe variant with counters: 64+56 at 0 and 20 NOPs, 64+0 at 0 NOPs` | Comment: step `CNT`: the probe variant of the binary with counters, at 64+56 with 0 and with 20 injected NOPs and at 64+0 with 0 injected NOPs. |
| 10 | `# Before every process: marker and STOP check, wait until at most 2 tasks are runnable, then 5 s.` | Comment: before every process the script checks the marker file and the STOP file, waits until at most 2 tasks are runnable, and then waits 5 s. |

### Settings and the record of the start state (lines 11 to 22)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `set -u` | `set -u`: the script stops when it uses a variable that was never set. There is no `set -e`. So a failed command alone does not stop the script. |
| 12 | `M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP` | `M`: the path of the marker file. `STOP`: the path of the STOP file, `cache-perf/STOP` in the home folder of the user. |
| 13 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check at the start. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 14 | `W=$HOME/cache-perf/asct-20261116` | `W`: the work folder on CRB. It holds the scripts, the probe binary and the file `events.codes`. |
| 15 | `PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin` | `PLAIN`: the installed binary, the benchmark program that the installer of ASCT built. |
| 16 | `PROBE=$W/loaded-latency-asct-probe-sve.bin` | `PROBE`: the probe binary that `prep.sh` built and copied to the work folder. |
| 17 | `STEPS=${STEPS:-BASE DEF NOPS LAY MIX CNT}; DUR=${DUR:-2}; BYTES=268435456` | Three settings. `STEPS`: the steps to run. `${STEPS:-BASE DEF NOPS LAY MIX CNT}` gives all six steps when `STEPS` is not set or is empty. `DUR`: the length of the measured phase, default 2 s. `BYTES`: the buffer size of each thread, 268435456 bytes (256 MiB). It is fixed. |
| 18 | `NUMA=$(command -v numactl \|\| ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)` | `NUMA`: the path of `numactl`. `command -v` gives the one in the search path. When there is none, `ls` gives the copy in the ASCT installation if it exists. If both fail, `NUMA` is empty. |
| 19 | `out=$HOME/cache-perf/results/asct-chip-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `asct-chip-` and the UTC time of this moment (`date -u`). `mkdir -p` creates it. |
| 20 | `{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu \| head -6` | Opens a group of commands that writes the file `env.txt` (line 21). This line writes the UTC date and time, the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and a header line with the 5 processes that have the highest CPU share (`ps` sorted by `pcpu`, then `head -6`). `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU share at this moment. |
| 21 | `  sha256sum $PLAIN $PROBE; echo "STEPS $STEPS DUR $DUR BYTES $BYTES numactl ${NUMA:-none}"; } > $out/env.txt 2>&1` | Continues the group. It writes the sha256 of both binaries and one line with `STEPS`, `DUR`, `BYTES` and the path of `numactl`. `${NUMA:-none}` gives `none` when `NUMA` is empty. The closing brace ends the group. Its output and its error messages (`2>&1`) go to `env.txt`. |
| 22 | `cp $W/events.codes $out/` | Copies `events.codes` into the result folder. That file holds the event sets with the raw codes that `prep.sh` wrote. |

### Function `cpuflags`: the `--bw-cpu` options of a layout (lines 23 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 23 | `cpuflags() { # cpuflags LAYOUT -> the --bw-cpu options` | Starts the function `cpuflags`. It gets a layout name and prints the `--bw-cpu` options for that layout, one option per CPU. |
| 24 | `  case $1 in` | Chooses the CPU ranges by the layout name. |
| 25 | `    6456) r="0-119";; 6400) r="0-63";; 0056) r="64-119";; 5656) r="0-55 64-119";; *) echo "bad layout $1" >&2; exit 2;;` | `6456`: the CPUs 0 to 119, which is 64 threads on mesh 0 plus 56 on mesh 1. `6400`: the CPUs 0 to 63, mesh 0 only. `0056`: the CPUs 64 to 119, mesh 1 only. `5656`: the CPUs 0 to 55 and 64 to 119, 56 threads on each mesh. Any other name: the function prints `bad layout` and the name to the error output and calls `exit 2`. Line 39 calls `cpuflags` inside `$( )`, which runs it in a copy of the shell. This `exit` therefore ends only the copy, and the script goes on. |
| 26 | `  esac` | Ends the `case` of line 24. |
| 27 | `  for part in $r; do for c in $(seq ${part%-*} ${part#*-}); do printf -- '--bw-cpu %d ' $c; done; done` | Prints the options. The outer loop takes each range of `r`. `${part%-*}` is the range without its last `-` and what follows, so the first CPU. `${part#*-}` is the range without everything up to the first `-`, so the last CPU. `seq` prints all numbers from the first to the last. `printf` writes `--bw-cpu`, the number and a space for each. The `--` in front tells `printf` that the next word is the format text and not an option. |
| 28 | `}` | Ends the function `cpuflags`. The function sets the variable `r`. It runs in a copy of the shell (line 39). So it does not change the `r` of the loops in lines 46 to 57. |

### Function `one`: run one benchmark process (lines 29 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `n=0` | `n`: the number of processes that have ended. It starts at 0. |
| 30 | `one() { # one TAG BINARY LAYOUT NOPS DURATION [TRAFFIC]   traffic: ASCT's --bw-write value, default 0 = all reads` | Starts the function `one`. It runs one benchmark process and waits for its end. Comment: the arguments are a tag, the binary, the layout, the number of injected NOPs, the length of the measured phase and, as an option, the traffic type. The traffic type is the value of the option `--bw-write` of ASCT. The default 0 means that all accesses are reads. |
| 31 | `  [ -e $M ] && { echo "marker: stop after $n processes"; exit 3; }` | Marker check before every process. When the marker file exists, the script prints `marker: stop after N processes` and ends with exit status 3. |
| 32 | `  [ -e $STOP ] && { echo "STOP file: stop after $n processes"; exit 4; }` | Check of the STOP file before every process. When it exists, the script prints `STOP file: stop after N processes` and ends with exit status 4. |
| 33 | `  # ASCT's Python layer creates the counter folder before the run; two threads that create it at the same time fail` | Comment: the reason for line 34. The Python layer of ASCT creates the counter folder before the run. By the comment, two threads that create the folder at the same time fail. |
| 34 | `  [ -n "${DIETPERF_OUTDIR:-}" ] && mkdir -p "$DIETPERF_OUTDIR"` | When the caller has set `DIETPERF_OUTDIR` (`-n`: the text is not empty), this line creates that folder before the run. `${DIETPERF_OUTDIR:-}` gives an empty text when the variable is not set. So `set -u` does not stop the script here. |
| 35 | `  # the name rq: the callers use r as their loop variable (r here overwrote 8 file names in the run of 23:19 UTC)` | Comment: why the variable of line 36 has the name `rq`. The callers use `r` as their loop variable. By the comment, an earlier text used `r` here, and that overwrote 8 file names in the run of 23:19 UTC. The decisions file records the same defect [Ref1]. |
| 36 | `  for i in $(seq 60); do rq=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); [ "$rq" -le 2 ] && break; sleep 1; done` | Waits until at most 2 tasks are runnable, with at most 60 tries. `cut -d' ' -f4 /proc/loadavg` takes the fourth field, which has a form such as `1/1100`. `cut -d/ -f1` keeps the number in front of the slash. This is the number of tasks that are runnable now. When `rq` is 2 or less (`-le`), `break` ends the loop. If not, the script sleeps 1 s and tests again. After 60 tries the script goes on without a message. |
| 37 | `  sleep 5` | A fixed pause of 5 s before the launch. |
| 38 | `  echo "launch $1 epoch $(date +%s.%N) load $(cat /proc/loadavg) users $(who \| wc -l)" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the time of this moment in seconds with nanoseconds (`date +%s.%N` counts from 1970-01-01 UTC), the content of `/proc/loadavg` and the number of logins (`who` piped to `wc -l`). This is the last reading of the machine state before the process starts. |
| 39 | `  taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $2 --duration $5 --delay-seconds 0 $(cpuflags $3) --bw-buflen $BYTES \` | Starts the binary of argument 2. `taskset -c 0-119` allows the process to run on the CPUs 0 to 119 only. `${NUMA:+$NUMA --membind 0}` gives `numactl --membind 0` when `NUMA` is not empty. The process then gets its memory from NUMA node 0 only. `--duration $5`: the length of the measured phase in seconds. `--delay-seconds 0`: the delay setting of the binary is 0 s. `$(cpuflags $3)` puts one `--bw-cpu` option per CPU of the layout here. The binary runs one read thread on each of these CPUs. `--bw-buflen $BYTES`: each thread has a buffer of 256 MiB. The backslash at the end continues the command in the next line. |
| 40 | `      --bw-fine-delay $4 --bw-write=${6:-0} --bw-cacheline-bytes 64 > $out/$1.out 2>&1 < /dev/null &` | Continues the command of line 39. `--bw-fine-delay $4`: the number of injected NOPs. `--bw-write=${6:-0}`: the traffic type, 0 when the caller gave no sixth argument. `--bw-cacheline-bytes 64`: one cache line has 64 bytes. The output and the error messages of the binary go to the file `TAG.out` in the result folder. The input is `/dev/null`, an empty input. The `&` at the end starts the process in the background. The script goes on immediately. |
| 41 | `  pid=$!` | `pid`: the process id of the process that line 39 started. `taskset` and `numactl` replace themselves with the next program in the same process. So this is the process id of the binary. |
| 42 | `  while kill -0 $pid 2>/dev/null; do [ -e $M ] && { kill $pid; echo "marker: killed $1"; exit 3; }; sleep 1; done` | Waits for the process and watches the marker file. `kill -0 $pid` sends no signal. It only tests whether the process still exists. The loop runs as long as it exists. Once per second: when the marker file exists, `kill $pid` sends the termination signal to the process. The script then prints `marker: killed` with the tag and ends with exit status 3. It writes no `rc` line in that case. If the marker file does not exist, `sleep 1` waits 1 s. The STOP file is not checked here. |
| 43 | `  wait $pid; echo "rc $? $1 epoch $(date +%s.%N)" >> $out/launches.txt; n=$((n+1))` | `wait $pid` returns the exit status of the binary. The line appends `rc`, that status, the tag and the time of this moment to `launches.txt`. Then it adds 1 to `n`. The loop of line 42 sleeps 1 s between two tests. So the time can be up to about 1 s later than the real end of the process. The status is not tested. |
| 44 | `}` | Ends the function `one`. |

### The steps without counters (lines 45 to 58)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `has() { case " $STEPS " in *" $1 "*) return 0;; esac; return 1; }` | Defines the function `has`. It returns 0 (true) when its argument is one of the words of `STEPS`, and 1 if not. The `case` puts a space at each end of `STEPS` and looks for the word with a space on each side. |
| 46 | `if has BASE; then for r in 1 2 3 4 5 6; do one w.6456.n0.d$DUR.$r $PLAIN 6456 0 $DUR; done; fi` | Step `BASE`: 6 processes with the numbers `r` from 1 to 6. Each call of `one` uses the tag `w.6456.n0.dDUR.r`, the installed binary, the layout `6456`, 0 injected NOPs and a measured phase of `DUR` seconds. |
| 47 | `if has DEF; then for r in 1 2 3; do one w.6456.n0.d0.25.$r $PLAIN 6456 0 0.25; done; fi` | Step `DEF`: 3 processes with the same layout and 0 injected NOPs, but with a measured phase of 0.25 s. The tags are `w.6456.n0.d0.25.r`. |
| 48 | `if has NOPS; then` | Step `NOPS` runs when `STEPS` holds the word. |
| 49 | `  NL="1 2 3 4 6 8 10 15 20 30 40 50 70 100 180"` | `NL`: the 15 counts of injected NOPs, from 1 to 180. |
| 50 | `  for nn in $NL; do one w.6456.n$nn.d$DUR.1 $PLAIN 6456 $nn $DUR; done` | First pass: the counts in rising order. Each call of `one` uses the tag `w.6456.nNOPS.dDUR.1`, the installed binary, the layout `6456`, the count `nn` and `DUR`. |
| 51 | `  for nn in $(echo $NL \| tr ' ' '\n' \| tac); do one w.6456.n$nn.d$DUR.2 $PLAIN 6456 $nn $DUR; done` | Second pass: the same counts in falling order. `tr` puts each count on its own line and `tac` reverses the order of the lines. The tags end with `.2`. |
| 52 | `fi` | Ends the `if` of line 48. |
| 53 | `if has LAY; then` | Step `LAY` runs when `STEPS` holds the word. |
| 54 | `  for r in 1 2; do for lay in 6400 0056 5656; do for nn in 0 20; do one w.$lay.n$nn.d$DUR.$r $PLAIN $lay $nn $DUR; done; done; done` | Three loops: over the process numbers `r` (1 and 2), over the layouts `lay` (`6400`, `0056` and `5656`) and over the NOP counts `nn` (0 and 20). Each pass calls `one` with the tag `w.LAYOUT.nNOPS.dDUR.r`, the installed binary, the layout, the count and `DUR`. |
| 55 | `fi` | Ends the `if` of line 53. |
| 56 | `if has MIX; then  # the other four traffic types of ASCT's peak-bandwidth benchmark (2: 3:1, 3: 2:1, 4: 1:1, 5: 2:1 non-temporal)` | Step `MIX` runs when `STEPS` holds the word. Comment: these are the other four traffic types of the peak-bandwidth benchmark of ASCT. By the comment, type 2 has 3 reads for each write, type 3 has 2 reads for each write, type 4 has 1 read for each write, and type 5 has 2 reads for each write with non-temporal stores. |
| 57 | `  for r in 1 2; do for t in 2 3 4 5; do one x.6456.t$t.d$DUR.$r $PLAIN 6456 0 $DUR $t; done; done` | Two loops: over the process numbers `r` (1 and 2) and over the traffic types `t` (2 to 5). Each pass calls `one` with the tag `x.6456.tTYPE.dDUR.r`, the installed binary, the layout `6456`, 0 injected NOPs, `DUR` and the type as the sixth argument. |
| 58 | `fi` | Ends the `if` of line 56. |

### Step `CNT`: the probe binary with counters (lines 59 to 68)

| Line | Source | Explanation |
|---:|---|---|
| 59 | `if has CNT; then` | Step `CNT` runs when `STEPS` holds the word. |
| 60 | `  while IFS='\|' read -r s evs <&3; do` | Starts a loop over the event sets, one line of `events.codes` per pass. `IFS='\|'` splits the line at the first `\|`. The set name goes to `s`. The list of `name=code` pairs goes to `evs`. `<&3` makes `read` take the line from file descriptor 3, which line 67 opens on the file. So the standard input of the commands inside the loop is not the file. |
| 61 | `    [ -z "$evs" ] && continue` | Skips a set that has no events (`-z`: the text is empty). |
| 62 | `    codes=$(echo "$evs" \| tr ',' '\n' \| cut -d= -f2 \| paste -sd,)` | `codes`: the raw codes of the set, joined with commas. `tr` puts each `name=code` pair on its own line. `cut -d= -f2` keeps the part after the `=`. `paste -sd,` joins the lines with commas. The result has a form such as `0x11,0x8,0x3`. |
| 63 | `    for cfg in "6456 0" "6456 20" "6400 0"; do` | Starts a loop over three cases. Each case is a layout and a NOP count: 64+56 with 0, 64+56 with 20, and 64+0 with 0. |
| 64 | `      set -- $cfg` | `set --` puts the two words of `cfg` into the arguments of the script. After it `$1` is the layout and `$2` is the NOP count. |
| 65 | `      DIETPERF_OUTDIR=$out/c.$s.$1.n$2.d DIETPERF_PMUv3=$codes one c.$s.$1.n$2 $PROBE $1 $2 $DUR` | Calls `one` with the tag `c.SET.LAYOUT.nNOPS`, the probe binary, the layout, the NOP count and `DUR`. The two assignments in front of the call hold for this call only. `DIETPERF_OUTDIR` names a folder `TAG.d` in the result folder for the counter files. `DIETPERF_PMUv3` holds the raw codes. `one` creates the folder (line 34), and the binary gets both variables in its environment. Each case runs one process per set. |
| 66 | `    done` | Ends the loop of line 63. |
| 67 | `  done 3< $W/events.codes` | Ends the loop of line 60. `3<` opens the file `events.codes` of the work folder on file descriptor 3 for the whole loop. |
| 68 | `fi` | Ends the `if` of line 59. |

### Summary on the standard output (lines 69 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 69 | `echo "done $out processes $n"` | Prints `done`, the path of the result folder and the number of processes that ran. |
| 70 | `grep -c '^rc 0 ' $out/launches.txt; grep '^rc' $out/launches.txt \| grep -v '^rc 0 ' \| head -5` | Prints the number of lines of `launches.txt` that start with `rc 0 `. These are the processes with exit status 0 (`grep -c` counts the lines). Then it prints up to 5 `rc` lines with another status: the first `grep` keeps the `rc` lines, `grep -v` drops those with status 0, and `head -5` keeps 5 lines. |
| 71 | `for f in $out/w.6456.n0.d$DUR.*.out $out/w.6456.n20.d$DUR.*.out; do [ -e $f ] && echo "$(basename $f) $(grep -h 'Total Bandwidth (MB/sec)' $f)"; done` | For each output file of the layout 64+56 at 0 and at 20 injected NOPs with the length `DUR`: prints the file name and its line `Total Bandwidth (MB/sec)`. `[ -e $f ]` skips a pattern that matches no file. |
| 72 | `cat /proc/loadavg` | Prints the content of `/proc/loadavg` at the end of the run. The exit status of the script is the status of this last command. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Readings fixed now", "Added 2026-11-16 23:37 UTC" and "Record of 2026-11-16 23:50 UTC".
- [Ref2] `launches.txt` and `env.txt` in the result folder `asct-chip-20261116T231956Z` of the test folder `2026-11-16-asct-cross-check`: 80 `launch` lines and the line `STEPS BASE DEF NOPS LAY MIX CNT DUR 2`.
