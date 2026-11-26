# `run_single.sh` explained, line by line

- Source file: `asct-2026-11-16/crb/run_single.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 72 lines, 4550 bytes).
- sha256 of the source when this page was built: `a6ad860ea9f1a58880f7cbfb031bed7a6c0934329c4752381966fb695f5b3e2e`.

## Short version: purpose

`run_single.sh` runs the one-core part of the ASCT cross-check on CRB. Each process is one start of the ASCT benchmark binary with one read thread on CPU 2 or CPU 41 and one buffer size, with or without counters and injected NOPs. The script stores the output of every process in a new result folder.

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
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next process when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists (lines 10 to 11).
2. Read the settings from the environment: the processes per case, the length of the measured phase, the parts, the buffer sizes and the two CPUs (lines 12 to 19).
3. Create the result folder, write the start state to `env.txt` and copy `events.codes` (lines 20 to 24).
4. Part U: for each size and each CPU, run the installed binary without counters, `REPS` times. Each run goes through the function `one`, which checks the two stop files, writes a `launch` line, runs the binary and writes its exit status (lines 35 to 39).
5. Part C: for each event set, size and CPU, run the probe binary with the counters of the set, `CREPS` times (lines 40 to 50).
6. Part N: run the installed binary with 1, 2, 4 and 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB on each CPU, `NREPS` times (lines 51 to 56).
7. Part NC, only when `PARTS` names it: run the probe binary with 1, 2 and 4 injected NOPs and the sets `A`, `B` and `E` at 1 MiB and 8 MiB on each CPU, `CREPS` times (lines 57 to 68).
8. Print a short summary (lines 69 to 72).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures. By the decisions file, the rate of one process is the line `Total Bandwidth (MB/sec)` of its output, divided by 1000 to give GB/s [Ref1].
- By the description text of the analysis script `analyze.py`, the rate of one thread is its repetitions times the buffer size, divided by its time. The binary prints the repetitions and the time of each thread in a line that starts with `tid = `. A repetition is one pass over the buffer.
- By the decisions file, ASCT counts 64 bytes for each cache line, although its read loop loads 8 bytes of the line [Ref1].
- Thread placement: the script limits each process to the CPUs 0 to 119 (`taskset`) and passes one CPU with `--bw-cpu`. The binary runs its one read thread on that CPU. The buffer is allocated inside the ASCT binary, whose source is not in this repo. By the text of the report script `dyn_notes.py`, the ASCT code allocates the buffer with `posix_memalign` and does not ask for huge pages.
- One process runs at a time. The two CPUs never run at the same time. The script does not wait for a quiet machine and does not pause between two processes.
- The parts run in the order of the file: U, C, N, NC. The order of the words in `PARTS` does not change this.
- The order inside a part alternates: odd rounds run CPU `CA` first and the sizes upward, even rounds run CPU `CB` first and the sizes downward. The parts N and NC alternate the CPU order only.
- The marker file and the STOP file are checked before every process, not during a process. The exit statuses are 3 for the marker file and 4 for the STOP file.
- The exit status of a benchmark process is written to `launches.txt` but not tested.
- With the default settings and 7 event sets, part U starts 256 processes, part C 448 and part N 96. The first run of 2026-11-16 started these 800 processes in this order [Ref2]. Part NC starts 72 processes. A second run with `PARTS` set to `NC` started them [Ref3].

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/run_single.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (72 lines, 4550 bytes, sha256 `a6ad860ea9f1a58880f7cbfb031bed7a6c0934329c4752381966fb695f5b3e2e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment (lines 1 to 8)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_single.sh - one core, ASCT read loop, size sweep. No root. CPUs 2 and 41 only (the CPUs of the 2026-11-15 work).` | Comment: the purpose. One core, the read loop of ASCT, a sweep over buffer sizes, no root rights. By the comment the script uses the CPUs 2 and 41 only, the CPUs of the work of 2026-11-15. Line 17 lets the caller choose two other CPUs. |
| 3 | `# Part U: the installed ASCT binary, no counters, REPS processes per CPU and size.` | Comment: part U uses the installed ASCT binary without counters. It starts `REPS` processes per CPU and buffer size. |
| 4 | `# Part N: the installed binary with 1, 2, 4, 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB, NREPS processes each.` | Comment: part N uses the installed binary with 1, 2, 4 and 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB. It starts `NREPS` processes per case. |
| 5 | `# Part C: ASCT's probe variant with ASCT's counter capture (environment DIETPERF_PMUv3), CREPS processes per` | Comment: part C uses the probe variant of the binary with the counter capture of ASCT. The environment variable `DIETPERF_PMUv3` carries the event codes. Part C starts `CREPS` processes per CPU, size and event set. |
| 6 | `#         CPU, size and event set. Every process is one ASCT bandwidth run with ASCT's default command line` | Comment, continued: every process is one bandwidth run of ASCT with the default command line of ASCT. |
| 7 | `#         (benchspec/memory_benchspec.py: --duration 0.25 --delay-seconds 0 --bw-fine-delay 0 --bw-write=0).` | Comment, continued: the file of ASCT that builds this command line (`benchspec/memory_benchspec.py`) and its options `--duration 0.25 --delay-seconds 0 --bw-fine-delay 0 --bw-write=0`. |
| 8 | `# Stop controls: marker file /tmp/positron-perf.RUNNING and ~/cache-perf/STOP are checked before every process.` | Comment: two files can stop the script, the marker file and `~/cache-perf/STOP`. Both are checked before every process. The comment block does not name part NC, which lines 57 to 68 hold. |

### Settings and the record of the start state (lines 9 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 9 | `set -u` | `set -u`: the script stops when it uses a variable that was never set. There is no `set -e`. So a failed command alone does not stop the script. |
| 10 | `M=/tmp/positron-perf.RUNNING; STOP=$HOME/cache-perf/STOP` | `M`: the path of the marker file. `STOP`: the path of the STOP file, `cache-perf/STOP` in the home folder of the user. |
| 11 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check at the start. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 12 | `W=$HOME/cache-perf/asct-20261116` | `W`: the work folder on CRB. It holds the scripts, the probe binary and the file `events.codes`. |
| 13 | `PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin` | `PLAIN`: the installed binary, the benchmark program that the installer of ASCT built. |
| 14 | `PROBE=$W/loaded-latency-asct-probe-sve.bin` | `PROBE`: the probe binary that `prep.sh` built and copied to the work folder. |
| 15 | `REPS=${REPS:-8}; CREPS=${CREPS:-2}; DUR=${DUR:-0.25}; PARTS=${PARTS:-U N C}` | Four settings. Each keeps the value that the caller has set in the environment. `${REPS:-8}` gives 8 when `REPS` is not set or empty. `REPS`: processes per CPU and size in part U, default 8. `CREPS`: processes per CPU, size and event set in the parts C and NC, default 2. `DUR`: the length of the measured phase, default 0.25 s. `PARTS`: the parts to run, default `U N C`. |
| 16 | `SIZES=${SIZES:-"32768 1048576 1572864 2097152 2621440 3145728 4194304 5242880 6291456 8388608 12582912 16777216 25165824 33554432 268435456 1073741824"}` | `SIZES`: the buffer sizes in bytes. The caller can set another list. The 16 default values are 32 KiB, then 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 16, 24 and 32 MiB, then 256 MiB (268435456 bytes) and 1 GiB (1073741824 bytes). |
| 17 | `CA=${CA:-2}; CB=${CB:-41}   # the two CPUs; the defaults are the CPUs of the 2026-11-15 work` | `CA` and `CB`: the two CPUs, default 2 and 41. Comment: the defaults are the CPUs of the work of 2026-11-15. |
| 18 | `RSIZES=$(echo $SIZES \| tr ' ' '\n' \| tac \| tr '\n' ' ')` | `RSIZES`: the same sizes in reverse order. The first `tr` puts each size on its own line. `tac` reverses the order of the lines. The second `tr` joins them with spaces again. |
| 19 | `NUMA=$(command -v numactl \|\| ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)` | `NUMA`: the path of `numactl`. `command -v` gives the one in the search path. When there is none, `ls` gives the copy in the ASCT installation if it exists. If both fail, `NUMA` is empty. |
| 20 | `out=$HOME/cache-perf/results/asct-single-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `asct-single-` and the UTC time of this moment (`date -u`). `mkdir -p` creates it. |
| 21 | `{ echo "utc $(date -u +%FT%TZ)"; uname -r; cat /proc/loadavg; who; ps -eo user,pcpu,comm --sort=-pcpu \| head -6` | Opens a group of commands that writes the file `env.txt` (line 22). This line writes the UTC date and time, the release of the running Linux kernel (`uname -r`), the content of `/proc/loadavg`, one line per login (`who`), and a header line with the 5 processes that have the highest CPU share (`ps` sorted by `pcpu`, then `head -6`). `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU share at this moment. |
| 22 | `  sha256sum $PLAIN $PROBE; echo "REPS $REPS CREPS $CREPS DUR $DUR PARTS $PARTS CPUS $CA $CB numactl ${NUMA:-none}"; echo "SIZES $SIZES"; } > $out/env.txt 2>&1` | Continues the group. It writes the sha256 of both binaries, one line with the settings (`REPS`, `CREPS`, `DUR`, `PARTS`, the two CPUs and the path of `numactl`) and one line with the sizes. `${NUMA:-none}` gives `none` when `NUMA` is empty. The value of `NREPS` (line 53) is not written. The closing brace ends the group. Its output and its error messages (`2>&1`) go to `env.txt`. |
| 23 | `cp $W/events.codes $out/` | Copies `events.codes` into the result folder. That file holds the event sets with the raw codes that `prep.sh` wrote. |
| 24 | `n=0` | `n`: the number of processes that have ended. It starts at 0. |

### Function `one`: run one benchmark process (lines 25 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `one() { # one TAG BINARY CPU BYTES [NOPS]  (environment of the caller is passed on)` | Starts the function `one`. It runs one benchmark process and waits for its end. Comment: the arguments are a tag, the binary, the CPU, the buffer size in bytes and, as an option, the number of injected NOPs. Environment variables that the caller sets in front of the call reach the binary. |
| 26 | `  [ -e $M ] && { echo "marker: stop after $n processes"; exit 3; }` | Marker check before every process. When the marker file exists, the script prints `marker: stop after N processes` and ends with exit status 3. |
| 27 | `  [ -e $STOP ] && { echo "STOP file: stop after $n processes"; exit 4; }` | Check of the STOP file before every process. When it exists, the script prints `STOP file: stop after N processes` and ends with exit status 4. |
| 28 | `  # ASCT's Python layer creates the counter folder before the run; two threads that create it at the same time fail` | Comment: the reason for line 29. The Python layer of ASCT creates the counter folder before the run. By the comment, two threads that create the folder at the same time fail. |
| 29 | `  [ -n "${DIETPERF_OUTDIR:-}" ] && mkdir -p "$DIETPERF_OUTDIR"` | When the caller has set `DIETPERF_OUTDIR` (`-n`: the text is not empty), this line creates that folder before the run. `${DIETPERF_OUTDIR:-}` gives an empty text when the variable is not set. So `set -u` does not stop the script here. |
| 30 | `  echo "launch $1 epoch $(date +%s.%N) load $(cat /proc/loadavg)" >> $out/launches.txt` | Appends one `launch` line to `launches.txt`: the tag, the time of this moment in seconds with nanoseconds (`date +%s.%N` counts from 1970-01-01 UTC) and the content of `/proc/loadavg`. This is the last reading of the machine state before the process starts. The script does not wait for a quiet machine and does not pause. |
| 31 | `  taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $2 --duration $DUR --delay-seconds 0 --bw-cpu $3 --bw-buflen $4 \` | Starts the binary of argument 2 in the foreground. The script waits for its end. `taskset -c 0-119` allows the process to run on the CPUs 0 to 119 only. `${NUMA:+$NUMA --membind 0}` gives `numactl --membind 0` when `NUMA` is not empty. The process then gets its memory from NUMA node 0 only. `--duration $DUR`: the length of the measured phase in seconds. `--delay-seconds 0`: the delay setting of the binary is 0 s. `--bw-cpu $3`: one read thread on the CPU of argument 3. `--bw-buflen $4`: the buffer size in bytes. The backslash at the end continues the command in the next line. |
| 32 | `      --bw-fine-delay ${5:-0} --bw-write=0 --bw-cacheline-bytes 64 > $out/$1.out 2>&1 < /dev/null` | Continues the command of line 31. `--bw-fine-delay ${5:-0}`: the number of injected NOPs. It is 0 when the caller gave no fifth argument. `--bw-write=0`: all accesses are reads. `--bw-cacheline-bytes 64`: one cache line has 64 bytes. The output and the error messages of the binary go to the file `TAG.out` in the result folder. The input is `/dev/null`, an empty input. So the binary cannot read the event list that the loops of the parts C and NC read. |
| 33 | `  echo "rc $? $1" >> $out/launches.txt; n=$((n+1))` | Appends the word `rc`, the exit status of the binary and the tag to `launches.txt`. Then it adds 1 to `n`. The status is not tested. So the script goes on after a failed process. |
| 34 | `}` | Ends the function `one`. |

### Part U: the installed binary, no counters (lines 35 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `case " $PARTS " in *" U "*)` | Part U runs when the word `U` stands in `PARTS`. The `case` puts a space at each end of the value of `PARTS`. Then it compares the text with the pattern `*" U "*`: any text that holds `U` with a space on each side. |
| 36 | `for r in $(seq $REPS); do` | Starts a loop over the process numbers `r` from 1 to `REPS`. `seq` prints these numbers. |
| 37 | `  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; sz=$SIZES; else cpus="$CB $CA"; sz=$RSIZES; fi` | Alternates the order from round to round. `$((r % 2))` is the remainder of `r` divided by 2. In a round with an odd `r` the CPU order is `CA` then `CB`, and the sizes go from the first to the last of `SIZES`. In a round with an even `r` the CPU order is `CB` then `CA`, and the sizes go in reverse order. |
| 38 | `  for b in $sz; do for c in $cpus; do one u.$c.$b.$r $PLAIN $c $b; done; done` | Two loops: over the sizes `b` of this round and, inside, over the two CPUs `c`. Each pass calls `one` with the tag `u.CPU.BYTES.r`, the installed binary, the CPU and the size. So for each size the two CPUs run one after the other, never at the same time. |
| 39 | `done;; esac` | Ends the loop of line 36 and the `case` of line 35. |

### Part C: the probe binary with counters (lines 40 to 50)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `case " $PARTS " in *" C "*)` | Part C runs when the word `C` stands in `PARTS`. It runs before part N. The header comment names N first. |
| 41 | `for r in $(seq $CREPS); do` | Starts a loop over the process numbers `r` from 1 to `CREPS`. |
| 42 | `  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; sz=$SIZES; else cpus="$CB $CA"; sz=$RSIZES; fi` | Alternates the CPU order and the size order as in line 37. |
| 43 | `  while IFS='\|' read -r s evs; do` | Starts a loop over the event sets, one line of `events.codes` per pass (line 49). `IFS='\|'` splits the line at the first `\|`. The set name goes to `s`. The list of `name=code` pairs goes to `evs`. `-r` keeps each backslash as it is. |
| 44 | `    [ -z "$evs" ] && continue` | Skips a set that has no events (`-z`: the text is empty). |
| 45 | `    codes=$(echo "$evs" \| tr ',' '\n' \| cut -d= -f2 \| paste -sd,)` | `codes`: the raw codes of the set, joined with commas. `tr` puts each `name=code` pair on its own line. `cut -d= -f2` keeps the part after the `=`. `paste -sd,` joins the lines with commas. The result has a form such as `0x11,0x8,0x3`. |
| 46 | `    for b in $sz; do for c in $cpus; do` | Starts two loops: over the sizes `b` of this round and, inside, over the two CPUs `c`. |
| 47 | `      DIETPERF_OUTDIR=$out/c.$s.$c.$b.$r.d DIETPERF_PMUv3=$codes one c.$s.$c.$b.$r $PROBE $c $b` | Calls `one` with the tag `c.SET.CPU.BYTES.r`, the probe binary, the CPU and the size. The two assignments in front of the call hold for this call only. `DIETPERF_OUTDIR` names a folder `TAG.d` in the result folder for the counter files. `DIETPERF_PMUv3` holds the raw codes. `one` creates the folder (line 29), and the binary gets both variables in its environment. |
| 48 | `    done; done` | Ends the two loops of line 46. |
| 49 | `  done < $W/events.codes` | Ends the loop of line 43. Its input is the file `events.codes` in the work folder. |
| 50 | `done;; esac` | Ends the loop of line 41 and the `case` of line 40. |

### Part N: injected NOPs, no counters (lines 51 to 56)

| Line | Source | Explanation |
|---:|---|---|
| 51 | `# Part N: the ASCT loop with injected NOPs (a loop that is limited by its own instructions), 3 sizes` | Comment: part N runs the ASCT loop with injected NOPs at 3 sizes. By the comment, such a loop is limited by its own instructions. |
| 52 | `case " $PARTS " in *" N "*)` | Part N runs when the word `N` stands in `PARTS`. The word `NC` does not start it. The pattern needs a space on each side of `N`. |
| 53 | `for r in $(seq ${NREPS:-4}); do` | Starts a loop over the process numbers `r` from 1 to `NREPS`. `${NREPS:-4}` gives 4 when `NREPS` is not set or is empty. |
| 54 | `  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; else cpus="$CB $CA"; fi` | Alternates the CPU order only: `CA` then `CB` for an odd `r`, `CB` then `CA` for an even `r`. |
| 55 | `  for nn in 1 2 4 8; do for b in 32768 1048576 8388608; do for c in $cpus; do one n.$nn.$c.$b.$r $PLAIN $c $b $nn; done; done; done` | Three loops: over the NOP counts `nn` (1, 2, 4 and 8), over three sizes `b` (32768, 1048576 and 8388608 bytes, which are 32 KiB, 1 MiB and 8 MiB) and over the two CPUs `c`. Each pass calls `one` with the tag `n.NOPS.CPU.BYTES.r`, the installed binary, the CPU, the size and the NOP count as the fifth argument. |
| 56 | `done;; esac` | Ends the loop of line 53 and the `case` of line 52. |

### Part NC: injected NOPs with counters (lines 57 to 68)

| Line | Source | Explanation |
|---:|---|---|
| 57 | `# Part NC (added 2026-11-16 after the first data, see DECISIONS.md): the padded ASCT loop with counters, sets A B E` | Comment: part NC was added on 2026-11-16 after the first data. The comment points to `DECISIONS.md`. Part NC runs the padded ASCT loop, which is the loop with injected NOPs, with counters for the sets A, B and E. |
| 58 | `case " $PARTS " in *" NC "*)` | Part NC runs when the word `NC` stands in `PARTS`. The default of `PARTS` in line 15 does not hold it. |
| 59 | `for r in $(seq $CREPS); do` | Starts a loop over the process numbers `r` from 1 to `CREPS`. |
| 60 | `  if [ $((r % 2)) = 1 ]; then cpus="$CA $CB"; else cpus="$CB $CA"; fi` | Alternates the CPU order as in line 54. |
| 61 | `  while IFS='\|' read -r s evs; do` | Starts a loop over the lines of `events.codes` (line 67). The set name goes to `s`, the rest of the line to `evs`. |
| 62 | `    case $s in A\|B\|E) ;; *) continue;; esac` | Keeps only the sets `A`, `B` and `E`. For any other set name, `continue` goes to the next line of `events.codes`. |
| 63 | `    codes=$(echo "$evs" \| tr ',' '\n' \| cut -d= -f2 \| paste -sd,)` | `codes`: the raw codes of the set, joined with commas, as in line 45. |
| 64 | `    for nn in 1 2 4; do for b in 1048576 8388608; do for c in $cpus; do` | Starts three loops: over the NOP counts `nn` (1, 2 and 4), over two sizes `b` (1048576 and 8388608 bytes, which are 1 MiB and 8 MiB) and over the two CPUs `c`. |
| 65 | `      DIETPERF_OUTDIR=$out/nc.$s.$nn.$c.$b.$r.d DIETPERF_PMUv3=$codes one nc.$s.$nn.$c.$b.$r $PROBE $c $b $nn` | Calls `one` with the tag `nc.SET.NOPS.CPU.BYTES.r`, the probe binary, the CPU, the size and the NOP count. As in line 47, `DIETPERF_OUTDIR` names the counter folder `TAG.d` and `DIETPERF_PMUv3` holds the raw codes. |
| 66 | `    done; done; done` | Ends the three loops of line 64. |
| 67 | `  done < $W/events.codes` | Ends the loop of line 61. Its input is the file `events.codes` in the work folder. |
| 68 | `done;; esac` | Ends the loop of line 59 and the `case` of line 58. |

### Summary on the standard output (lines 69 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 69 | `echo "done $out processes $n"` | Prints `done`, the path of the result folder and the number of processes that ran. |
| 70 | `grep -c '^rc 0 ' $out/launches.txt; grep '^rc' $out/launches.txt \| grep -v '^rc 0 ' \| head -5` | Prints the number of lines of `launches.txt` that start with `rc 0 `. These are the processes with exit status 0 (`grep -c` counts the lines). Then it prints up to 5 `rc` lines with another status: the first `grep` keeps the `rc` lines, `grep -v` drops those with status 0, and `head -5` keeps 5 lines. |
| 71 | `grep -h "Total Bandwidth (MB/sec)" $out/u.$CA.8388608.*.out 2>/dev/null \| head -8` | Prints up to 8 lines `Total Bandwidth (MB/sec)` from the output files of part U for the CPU `CA` at 8388608 bytes (8 MiB). `-h` leaves out the file names. `2>/dev/null` discards the error message when no such file exists. |
| 72 | `cat /proc/loadavg` | Prints the content of `/proc/loadavg` at the end of the run. The exit status of the script is the status of this last command. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Runs" and "Readings fixed now".
- [Ref2] `launches.txt` and `env.txt` in the result folder `asct-single-20261116T231240Z` of the test folder `2026-11-16-asct-cross-check`: 800 `launch` lines, first 256 with a tag that starts with `u`, then 448 with `c`, then 96 with `n`.
- [Ref3] `env.txt` in the result folder `asct-single-20261116T233721Z` of the same test folder (`PARTS NC`), and the file `logs/nc.log` (`processes 72`).
