# `run_followup.sh` explained, line by line

- Source file: `bench/run_followup.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 76 lines, 3619 bytes).
- sha256 of the source when this page was built: `a248a0fcb8de0074de9beec92f537fdfa02f2d8d313d589f27a493a5522d6285`.

## Short version: purpose

`run_followup.sh` runs five more experiments on CRB after the first sweep of 2026-10-30, without root rights. It starts `latency` and `bandwidth` with other settings: fresh chains, pairs of CPUs, the asm kernels, more thread counts and three different CPUs. Each part writes one CSV file into a new result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Asm kernels**: the kernels `asmread`, `asmwrite` and `asmcopy` of `bandwidth`. They are written in assembly and hold only loads and stores. `asmall` selects all three.
- **Compiled kernels**: the kernels `read`, `write` and `copy` of `bandwidth`, which are written in C. `all` selects all three.
- **Chain**: one cycle of pointers through all cache lines of the buffer of `latency`.
- **Fresh mode**: the mode of the option `--fresh` of `latency`. Each timed pass walks a chain that was never walked before.
- **Standard mode**: the mode of `latency` without `--fresh`. Each timed repetition walks the same chain repeatedly.
- **Temporal prefetcher**: the part of a core that records the order of earlier cache misses and fetches the same lines in the same order again.
- **L2 case, DRAM case**: buffer sizes that fit into the L2 cache of a core, or that are far larger than all caches. The source calls a case a regime.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` (lines 9 to 12).
2. Stop when the marker file exists. Then create the result folder, send all later output to `log.txt` too, and build the programs (lines 13 to 22).
3. Part A: `latency` in the fresh mode on CPU 3, one process per size, 25 sizes from 256 KiB to 2 GiB (lines 24 to 31).
4. Part B: `bandwidth` with 2 reading threads on 9 pairs of CPUs with 8 MiB per thread, and then three more runs with 1 MiB and 1 GiB (lines 33 to 44).
5. Part C: the asm kernels for buffer sizes from 32 KiB to 1 GiB and 1 to 120 threads, on the CPUs 0 to 119 and on the even CPUs (lines 46 to 59).
6. Part D: the compiled kernels with 256 MiB per thread: 48, 80 and 112 threads on the CPUs 0 to 119, and 32, 48 and 60 threads on the even CPUs (lines 61 to 66).
7. Part E: `latency` in the standard mode and in the fresh mode from the CPUs 3, 64 and 119 (lines 68 to 75).
8. Print the path of the result folder (line 76).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once at the start and then once per loop pass, before the first benchmark process of the pass. A loop pass of part E starts two `latency` processes, and the second one (line 74) has no check of its own. The three single runs of lines 39 to 44 have no check of their own either. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed benchmark process ends the script with the status of that command.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `latency` pins its one thread to the CPU of `--cpu`. `bandwidth` pins thread number `i` to entry `i` of its CPU list. So `t` threads on the list `0-119` use the CPUs 0 to `t - 1`, and `t` threads on the list `0-118:2` use the even CPUs 0 to 2 times `t` minus 2.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- Files in the result folder: `log.txt`, `latency-fresh.csv` (part A), `pair.csv` (part B), `asm.csv` (part C), `dram.csv` (part D) and `latency-bycpu.csv` (part E). In the files of the parts B to E a line that starts with `--` names the run whose rows follow.

## Source and explanation, line by line

- Text shown: the file `bench/run_followup.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (76 lines, 3619 bytes, sha256 `a248a0fcb8de0074de9beec92f537fdfa02f2d8d313d589f27a493a5522d6285`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and shell options (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_followup.sh - follow-up experiments after the first CRB sweep (2026-10-30).` | Comment: the name and the purpose of the script: more experiments after the first sweep on CRB of 2026-10-30. CRB is the Arm reference server under test. The parts A to E follow. |
| 3 | `#   A. fresh-chain latency (defeats a temporal prefetcher), CPU 3` | Comment: part A measures the latency with fresh chains on CPU 3. A fresh chain is a cycle of pointers that was never walked before. By the comment this defeats a temporal prefetcher, the part of a core that learns the order of earlier cache misses. |
| 4 | `#   B. CPU-pair bandwidth test: do two adjacent CPUs share a mesh port?` | Comment: part B is a bandwidth test with pairs of CPUs. Its question: do two neighbour CPUs share one port of the mesh? The mesh is the network that connects the cores, the last cache level and the memory. |
| 5 | `#   C. inline-asm kernels (loads/stores only) for peak per-core and aggregate bandwidth` | Comment: part C runs the kernels that are written in assembly inside the C file (inline asm). They hold loads and stores only. The comment names their purpose: the highest bandwidth per core and in total. |
| 6 | `#   D. DRAM regime at more thread counts` | Comment: part D runs the DRAM case (buffers far larger than the caches) with more thread counts. |
| 7 | `#   E. latency from CPUs 3, 64, 119 (mesh position)` | Comment: part E measures the latency from the CPUs 3, 64 and 119, to see the effect of the position on the mesh. |
| 8 | `# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.` | Comment: the rules are those of `run_crb.sh`: only the CPUs 0 to 119, and the script stops when the marker file exists. |
| 9 | `set -euo pipefail` | Three shell options. `-e`: the script stops when a command fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails. |

### Start again on the CPUs 0 to 119, marker check, result folder and build (lines 10 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `if [[ -z ${_RUN_CRB_PINNED:-} ]]; then` | Tests whether the variable `_RUN_CRB_PINNED` is empty or not set. `${X:-}` gives an empty text for an unset variable, and `-z` is true for an empty text. The variable is empty in the first start of the script. |
| 11 | `    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"` | Then starts the script again under `taskset`. `exec` replaces the shell with `taskset -c 0-119`. That tool limits the process to the CPUs 0 to 119 and then runs the script (`$0`) with the same arguments (`$@`). `_RUN_CRB_PINNED=1` is set for the new start only, so the second start skips this block. Every process that the script starts inherits the CPU list. |
| 12 | `fi` | Ends the `if` of line 10. |
| 13 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. The file exists while another user runs a performance test on CRB. |
| 14 | `BENCH=$(cd "$(dirname "$0")" && pwd)` | `BENCH`: the folder of this script as an absolute path. `dirname` gives the folder part of the script path `$0`, `cd` goes there, and `pwd` prints the path. |
| 15 | `check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }` | Defines the function `check_marker` in one line. `-e` tests whether the marker file exists. `A && B` runs `B` only when `A` succeeds. So when the file exists, the function prints `exists: stopping` with the path to the error output (`>&2`) and ends the script with exit status 3. In the other case `return 0` makes the function succeed, so the option `-e` does not stop the script. |
| 16 | `check_marker` | The first marker check. Nothing was written up to here. |
| 17 | `OUT=$HOME/cache-perf/results/followup-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder: `$HOME/cache-perf/results/followup-` plus the UTC time of this moment. `date -u` prints it in the form year, month, day, the letter `T`, hour, minute, second, the letter `Z`. |
| 18 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders. |
| 19 | `exec > >(tee -a "$OUT/log.txt") 2>&1` | From here on the standard output of the script goes to the program `tee`. `tee` prints it and also appends it to `log.txt` in the result folder. `>( )` starts `tee` as a process of its own. `2>&1` sends the error output to the same place. |
| 20 | `echo "results: $OUT"` | Prints the path of the result folder. |
| 21 | `make -C "$BENCH"` | Builds the programs: `make -C` runs `make` in the folder of the script. A failed build ends the script. |
| 22 | `L="$BENCH/latency"; B="$BENCH/bandwidth"` | `L`: the path of the program `latency`. `B`: the path of the program `bandwidth`. |

### Part A: latency with fresh chains on CPU 3 (lines 24 to 32)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `echo "== A. fresh-chain latency, cpu 3"` | Prints the title of part A. |
| 25 | `: > "$OUT/latency-fresh.csv"` | Creates `latency-fresh.csv` as an empty file. `:` does nothing, and `>` creates the file or empties it. |
| 26 | `for s in 256K 512K 1M 1.5M 2M 3M 4M 6M 8M 12M 16M 24M 32M 40M 48M 56M 64M 80M 96M 128M 192M 256M; do` | Loop over 22 buffer sizes from 256 KiB to 256 MiB. |
| 27 | `    check_marker; $L --cpu 3 --sizes $s --fresh 8 >> "$OUT/latency-fresh.csv"` | Marker check, then one `latency` process for this size. The output is appended to `latency-fresh.csv`. `--cpu 3`: the one thread is pinned to CPU 3. `--fresh 8`: the buffer gets 8 chains. The program walks chain 0 twice as a warm-up. Then it times exactly one pass over each of the other 7 chains, so each timed pass uses a chain that was never walked. |
| 28 | `done` | Ends the loop of line 26. |
| 29 | `for s in 512M 1G 2G; do` | Loop over the 3 largest sizes: 512 MiB, 1 GiB and 2 GiB. |
| 30 | `    check_marker; $L --cpu 3 --sizes $s --fresh 3 >> "$OUT/latency-fresh.csv"` | Marker check, then `latency` with `--fresh 3`: 3 chains, so 2 timed passes per size. |
| 31 | `done` | Ends the loop of line 29. |

### Part B: two reading threads on a pair of CPUs (lines 33 to 45)

| Line | Source | Explanation |
|---:|---|---|
| 33 | `echo "== B. CPU-pair bandwidth (read, 8M per thread, 2 threads)"` | Prints the title of part B: the read kernel, 8 MiB per thread, 2 threads. |
| 34 | `: > "$OUT/pair.csv"` | Creates `pair.csv` as an empty file. |
| 35 | `for c in 0,1 0,2 0,3 1,2 2,3 0,64 0,119 4,5 4,6; do` | Loop over 9 pairs of CPUs. The pairs `0,1`, `2,3` and `4,5` are neighbours. `0,64` and `0,119` put the second thread on the other mesh: CPUs 0 to 63 sit on mesh 0 and CPUs 64 to 127 on mesh 1. |
| 36 | `    check_marker; echo "-- cpus $c" >> "$OUT/pair.csv"` | Marker check. Then appends a title line with the pair to `pair.csv`. |
| 37 | `    $B --threads 2 --cpus $c --bytes 8M --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"` | Starts `bandwidth` with 2 threads. Thread 0 is pinned to the first CPU of the pair and thread 1 to the second. Each thread reads its own buffer of 8 MiB (`--kernel read`). `--reps 2 --min-ms 300`: 2 timed repetitions of at least 300 ms each. The output is appended to `pair.csv`. |
| 38 | `done` | Ends the loop of line 35. |
| 39 | `echo "-- cpus 0,1 1M (L2 regime)" >> "$OUT/pair.csv"` | Appends a title line: the pair `0,1` with 1 MiB per thread. The text calls this the L2 case (regime): a buffer of this size fits into the L2 cache of a core. |
| 40 | `$B --threads 2 --cpus 0,1 --bytes 1M --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"` | Starts `bandwidth` with 2 threads on the CPUs 0 and 1 and 1 MiB per thread. |
| 41 | `echo "-- cpus 0,1 1G (DRAM regime)" >> "$OUT/pair.csv"` | Appends a title line: the pair `0,1` with 1 GiB per thread, the DRAM case. |
| 42 | `$B --threads 2 --cpus 0,1 --bytes 1G --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"` | Starts `bandwidth` with 2 threads on the CPUs 0 and 1 and 1 GiB per thread. |
| 43 | `echo "-- cpus 0,64 1G (DRAM regime)" >> "$OUT/pair.csv"` | Appends a title line: the pair `0,64` with 1 GiB per thread. |
| 44 | `$B --threads 2 --cpus 0,64 --bytes 1G --kernel read --reps 2 --min-ms 300 >> "$OUT/pair.csv"` | Starts `bandwidth` with 2 threads on the CPUs 0 and 64, one CPU of each mesh, and 1 GiB per thread. |

### Part C: the asm kernels (lines 46 to 60)

| Line | Source | Explanation |
|---:|---|---|
| 46 | `echo "== C. asm kernels"` | Prints the title of part C. |
| 47 | `: > "$OUT/asm.csv"` | Creates `asm.csv` as an empty file. |
| 48 | `run_bw() { local k=$1 bytes=$2 cpus=$3; shift 3; for t in "$@"; do check_marker; echo "-- kernel $k bytes $bytes cpus $cpus threads $t" >> "$OUT/asm.csv";` | Starts the function `run_bw`. Its arguments are the kernel, the buffer size per thread, the CPU list and then any number of thread counts. `shift 3` removes the first three arguments, so `$@` holds the thread counts only. The loop runs once per thread count: a marker check, then a title line to `asm.csv` with the kernel, the size, the CPU list and the thread count. |
| 49 | `    $B --threads $t --cpus $cpus --bytes $bytes --kernel $k --reps 3 --min-ms 500 >> "$OUT/asm.csv"; done; }` | Continues the loop body: starts `bandwidth` with `t` threads. The program pins thread number `i` to entry `i` of the CPU list. `--reps 3 --min-ms 500`: 3 timed repetitions of at least 500 ms per kernel. The output is appended to `asm.csv`. `done` ends the loop and the closing brace ends the function. |
| 50 | `run_bw asmall 32K 0-119 1 120` | `asmall` runs the three asm kernels `asmread`, `asmwrite` and `asmcopy` one after the other. Here: 32 KiB per thread, with 1 thread and with 120 threads on the CPUs 0 to 119. |
| 51 | `run_bw asmall 1M  0-119 1 120` | The three asm kernels with 1 MiB per thread, with 1 thread and with 120 threads. |
| 52 | `run_bw asmread  8M 0-119 1 2 4 8 14` | `asmread` with 8 MiB per thread and 1, 2, 4, 8 and 14 threads. The threads sit on the first CPUs of the list: `t` threads use the CPUs 0 to `t - 1`. |
| 53 | `run_bw asmwrite 8M 0-119 1 2 4 8 14` | `asmwrite` with 8 MiB per thread and the same thread counts. |
| 54 | `run_bw asmcopy  8M 0-119 1 2 4 7` | `asmcopy` with two buffers of 8 MiB per thread and 1, 2, 4 and 7 threads. |
| 55 | `run_bw asmall 1G 0-119 1 2 4 8` | The three asm kernels with 1 GiB per thread and 1, 2, 4 and 8 threads. |
| 56 | `run_bw asmall 256M 0-119 16 32 64 96 120` | The three asm kernels with 256 MiB per thread and 16, 32, 64, 96 and 120 threads. |
| 57 | `# even-CPU placement: one thread per CPU pair, if pairs share a port` | Comment: the next two calls put the threads on the even CPUs only. That is one thread per pair of CPUs, which matters when the two CPUs of a pair share a port. |
| 58 | `run_bw asmread 8M 0-118:2 1 2 4 8 14 32 56` | `asmread` with 8 MiB per thread on the list `0-118:2`: the CPUs 0, 2, 4 and so on up to 118. Thread number `i` sits on CPU 2 times `i`. The thread counts are 1, 2, 4, 8, 14, 32 and 56. |
| 59 | `run_bw asmall 256M 0-118:2 32 60` | The three asm kernels with 256 MiB per thread on the even CPUs, with 32 and with 60 threads. |

### Part D: the DRAM case with the compiled kernels (lines 61 to 67)

| Line | Source | Explanation |
|---:|---|---|
| 61 | `echo "== D. DRAM regime, compiled kernels, more thread counts"` | Prints the title of part D. The compiled kernels are the kernels `read`, `write` and `copy` that are written in C. |
| 62 | `: > "$OUT/dram.csv"` | Creates `dram.csv` as an empty file. |
| 63 | `run_bw2() { local k=$1 bytes=$2 cpus=$3; shift 3; for t in "$@"; do check_marker; echo "-- kernel $k bytes $bytes cpus $cpus threads $t" >> "$OUT/dram.csv";` | Starts the function `run_bw2`. It is the same as `run_bw` of lines 48 to 49, but its title lines go to `dram.csv`. |
| 64 | `    $B --threads $t --cpus $cpus --bytes $bytes --kernel $k --reps 3 --min-ms 500 >> "$OUT/dram.csv"; done; }` | Continues the loop body: starts `bandwidth` with 3 repetitions of at least 500 ms per kernel and appends the output to `dram.csv`. |
| 65 | `run_bw2 all 256M 0-119 48 80 112` | `all` runs the kernels `read`, `write` and `copy`. Here: 256 MiB per thread with 48, 80 and 112 threads on the CPUs 0 to 119. `t` threads use the CPUs 0 to `t - 1`. |
| 66 | `run_bw2 all 256M 0-118:2 32 48 60` | The same kernels with 256 MiB per thread on the even CPUs (`0-118:2`), with 32, 48 and 60 threads. |

### Part E: latency from three CPUs, and the end (lines 68 to 76)

| Line | Source | Explanation |
|---:|---|---|
| 68 | `echo "== E. latency by CPU (repeated and fresh)"` | Prints the title of part E. |
| 69 | `: > "$OUT/latency-bycpu.csv"` | Creates `latency-bycpu.csv` as an empty file. |
| 70 | `for c in 3 64 119; do` | Loop over three CPUs: 3, 64 and 119. |
| 71 | `    check_marker; echo "-- cpu $c repeated" >> "$OUT/latency-bycpu.csv"` | Marker check. Then appends a title line: the CPU and the word `repeated`. |
| 72 | `    $L --cpu $c --sizes 1M,16M,1G --reps 2 --min-ms 300 >> "$OUT/latency-bycpu.csv"` | Starts `latency` in the standard mode for 3 sizes: 1 MiB, 16 MiB and 1 GiB. The thread is pinned to this CPU. 2 timed repetitions of at least 300 ms each walk the same chain repeatedly. |
| 73 | `    echo "-- cpu $c fresh" >> "$OUT/latency-bycpu.csv"` | Appends a title line: the CPU and the word `fresh`. |
| 74 | `    $L --cpu $c --sizes 16M,64M,1G --fresh 3 >> "$OUT/latency-bycpu.csv"` | Starts `latency` in the fresh mode for 16 MiB, 64 MiB and 1 GiB. `--fresh 3`: 2 timed passes per size, each over a chain that was never walked. |
| 75 | `done` | Ends the loop of line 70. |
| 76 | `echo "== done"; echo "$OUT"` | Prints the title `== done` and then the path of the result folder. |
