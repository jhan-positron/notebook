# `run_followup3.sh` explained, line by line

- Source file: `bench/run_followup3.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 55 lines, 2613 bytes).
- sha256 of the source when this page was built: `af5682b3606e5e92af0c5125e4db555d106140ca192473b467b4d5d4b86c4f98`.

## Short version: purpose

`run_followup3.sh` runs three experiments of 2026-11-02 on CRB without root rights. Parts A and B measure the write rate and the read rate to main memory while the number of threads on each of the two meshes changes. Part C measures, for each of the CPUs 0 to 119 alone, the latency at a buffer of 16 MiB and the read rate at a buffer of 8 MiB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Mesh cache**: the word of the source for the SLC.
- **DRAM**: the main memory.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`asmread`, `asmwrite`**: two kernels of `bandwidth` that are written in assembly. `asmread` only loads, and `asmwrite` only stores.
- **Grid**: the set of pairs of thread counts: `a` threads on mesh 0 and `b` threads on mesh 1.
- **Standard mode, fresh mode**: two modes of `latency`. In the standard mode each timed repetition walks the same cycle of pointers repeatedly. In the fresh mode (option `--fresh`) each timed pass walks a cycle that was never walked before.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **MiB**: 1048576 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` (lines 10 to 13).
2. Stop when the marker file exists. Then create the result folder, send all later output to `log.txt` too, and build the programs (lines 14 to 23).
3. Define the two helper functions. `cpulist` builds the CPU list for `a` threads on mesh 0 and `b` threads on mesh 1, and `grid` starts `bandwidth` once per pair (lines 25 to 33).
4. Part A: the kernel `asmwrite` with 256 MiB per thread for 24 pairs of thread counts (lines 35 to 37).
5. Part B: the kernel `asmread` with 256 MiB per thread for 6 of these pairs (lines 39 to 41).
6. Part C, two times: for each CPU from 0 to 119, `latency` at 16 MiB in the standard mode and in the fresh mode, and then `bandwidth` with one `asmread` thread at 8 MiB (lines 43 to 54).
7. Print the time and the path of the result folder (line 55).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once at the start, then before each `bandwidth` process of the grids, and once per CPU in part C. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed benchmark process ends the script with the status of that command.
- Thread placement in the parts A and B: `bandwidth` pins thread number `i` to entry `i` of the CPU list. The list holds the first `a` CPUs of mesh 0 and then the first `b` CPUs of mesh 1. The highest CPU in use is 119.
- Thread placement in part C: one process at a time, with its one thread pinned to the CPU of the loop. No other benchmark runs at the same time.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- Files in the result folder: `log.txt`, `writegrid.csv` (part A), `readgrid.csv` (part B), and for each of the two sweeps of part C `percore-latency-N.csv` and `percore-asmread-N.csv`. A line that starts with `--` names the run whose rows follow.

## Source and explanation, line by line

- Text shown: the file `bench/run_followup3.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (55 lines, 2613 bytes, sha256 `af5682b3606e5e92af0c5125e4db555d106140ca192473b467b4d5d4b86c4f98`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and shell options (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_followup3.sh - 2026-11-02 follow-up, no root needed.` | Comment: the name of the script and its date, 2026-11-02. It is a later set of experiments that needs no root rights. |
| 3 | `#   A. DRAM write fall: asmwrite 256M with a threads on mesh 0 (CPUs 0..a-1) and` | Comment: part A looks at the fall of the write rate to DRAM, the main memory. It runs the kernel `asmwrite` with 256 MiB per thread, with `a` threads on mesh 0 (the CPUs 0 to `a - 1`). The sentence goes on in line 4. |
| 4 | `#      b threads on mesh 1 (CPUs 64..64+b-1), a and b varied independently.` | Comment: and with `b` threads on mesh 1 (the CPUs 64 to `64 + b - 1`). `a` and `b` are changed independently of each other. |
| 5 | `#   B. the same grid for asmread, a subset.` | Comment: part B runs the same grid of thread counts for the kernel `asmread`, but only a part of it. |
| 6 | `#   C. per-core sweep, CPUs 0-119, two sweeps: 16M mesh-cache latency (repeated` | Comment: part C is a sweep over the cores: the CPUs 0 to 119, two times. It measures the latency at a buffer of 16 MiB. The source calls this the latency of the mesh cache, its word for the SLC (the system level cache, the last cache level of the chip). |
| 7 | `#      and fresh) and 1-thread asmread 8M. Shows whether a core's position` | Comment: the latency is measured in the repeated way and in the fresh way. The sweep also measures `asmread` with 1 thread and 8 MiB. The next sentence starts here: the sweep shows whether the position of a core ... |
| 8 | `#      changes its mesh-cache latency and bandwidth.` | Comment: ... changes its latency and its bandwidth at the SLC. |
| 9 | `# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.` | Comment: the rules are those of `run_crb.sh`: only the CPUs 0 to 119, and the script stops when the marker file exists. |
| 10 | `set -euo pipefail` | Three shell options. `-e`: the script stops when a command fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails. |

### Start again on the CPUs 0 to 119, marker check, result folder and build (lines 11 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `if [[ -z ${_RUN_CRB_PINNED:-} ]]; then` | Tests whether the variable `_RUN_CRB_PINNED` is empty or not set. `${X:-}` gives an empty text for an unset variable, and `-z` is true for an empty text. The variable is empty in the first start of the script. |
| 12 | `    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"` | Then starts the script again under `taskset`. `exec` replaces the shell with `taskset -c 0-119`. That tool limits the process to the CPUs 0 to 119 and then runs the script (`$0`) with the same arguments (`$@`). `_RUN_CRB_PINNED=1` is set for the new start only, so the second start skips this block. Every process that the script starts inherits the CPU list. |
| 13 | `fi` | Ends the `if` of line 11. |
| 14 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. The file exists while another user runs a performance test on CRB. |
| 15 | `BENCH=$(cd "$(dirname "$0")" && pwd)` | `BENCH`: the folder of this script as an absolute path. `dirname` gives the folder part of the script path `$0`, `cd` goes there, and `pwd` prints the path. |
| 16 | `check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }` | Defines the function `check_marker` in one line. `-e` tests whether the marker file exists. `A && B` runs `B` only when `A` succeeds. So when the file exists, the function prints `exists: stopping` with the path to the error output (`>&2`) and ends the script with exit status 3. In the other case `return 0` makes the function succeed, so the option `-e` does not stop the script. |
| 17 | `check_marker` | The first marker check. Nothing was written up to here. |
| 18 | `OUT=$HOME/cache-perf/results/followup3-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder: `$HOME/cache-perf/results/followup3-` plus the UTC time of this moment (`date -u` with a format). |
| 19 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders. |
| 20 | `exec > >(tee -a "$OUT/log.txt") 2>&1` | From here on the standard output of the script goes to the program `tee`. `tee` prints it and also appends it to `log.txt` in the result folder. `>( )` starts `tee` as a process of its own. `2>&1` sends the error output to the same place. |
| 21 | `echo "results: $OUT"; date -u` | Prints the path of the result folder and then the UTC date and time. |
| 22 | `make -C "$BENCH"` | Builds the programs: `make -C` runs `make` in the folder of the script. A failed build ends the script. |
| 23 | `L="$BENCH/latency"; B="$BENCH/bandwidth"` | `L`: the path of the program `latency`. `B`: the path of the program `bandwidth`. |

### Functions `cpulist` and `grid`: threads on mesh 0 and on mesh 1 (lines 25 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `cpulist() { # a threads on mesh 0, b threads on mesh 1 -> cpu list` | Starts the function `cpulist`. By the comment it turns `a` threads on mesh 0 and `b` threads on mesh 1 into a CPU list. |
| 26 | `    local a=$1 b=$2 l=""` | `a`, `b`: the two arguments. `l`: the list, empty at the start. `local` keeps the names inside the function. |
| 27 | `    (( a > 0 )) && l="0-$((a-1))"` | When `a` is above 0: the list becomes `0-` plus `a - 1`, the first `a` CPUs of mesh 0. `(( ))` compares numbers, and `$(( ))` computes a number. |
| 28 | `    (( b > 0 )) && l="${l:+$l,}64-$((64+b-1))"` | When `b` is above 0: adds `64-` plus `64 + b - 1`, the first `b` CPUs of mesh 1. `${l:+$l,}` gives the list so far with a comma, or nothing when the list is empty. For `a` 16 and `b` 16 the result is `0-15,64-79`. |
| 29 | `    echo "$l"` | Prints the list. The caller takes it with `$( )`. |
| 30 | `}` | Ends the function `cpulist`. |
| 31 | `grid() { local k=$1 out=$2; shift 2; for ab in "$@"; do local a=${ab%,*} b=${ab#*,}; check_marker` | Starts the function `grid`. Its arguments are the kernel, the output file and then any number of pairs of the form `a,b`. `shift 2` removes the first two arguments, so `$@` holds the pairs. The loop runs once per pair. `${ab%,*}` is the part before the comma (`a`), and `${ab#*,}` is the part after it (`b`). Then comes a marker check. |
| 32 | `    echo "-- kernel $k mesh0 $a mesh1 $b cpus $(cpulist $a $b)" >> "$out"` | Continues the loop body: appends a title line to the output file: the kernel, the threads on mesh 0, the threads on mesh 1 and the CPU list. |
| 33 | `    $B --threads $((a+b)) --cpus "$(cpulist $a $b)" --bytes 256M --kernel $k --reps 3 --min-ms 500 >> "$out"; done; }` | Continues the loop body: starts `bandwidth` with `a + b` threads on that CPU list. The program pins thread number `i` to entry `i` of the list. So the first `a` threads sit on the CPUs 0 to `a - 1`, and the other `b` threads on the CPUs 64 to `64 + b - 1`. Each thread has a buffer of 256 MiB. `--reps 3 --min-ms 500`: 3 timed repetitions of at least 500 ms. The output is appended to the output file. `done` ends the loop and the closing brace ends the function. |

### Parts A and B: the grids for `asmwrite` and `asmread` (lines 35 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `echo "== A. asmwrite 256M, threads per mesh grid"; date -u` | Prints the title of part A and the UTC date and time. |
| 36 | `: > "$OUT/writegrid.csv"` | Creates `writegrid.csv` as an empty file. `:` does nothing, and `>` creates the file or empties it. |
| 37 | `grid asmwrite "$OUT/writegrid.csv" 16,0 32,0 48,0 64,0 0,16 0,32 0,48 0,56 16,16 32,16 16,32 32,32 48,16 16,48 48,32 32,48 48,48 64,16 64,32 64,48 64,56 48,56 32,56 16,56` | Part A: the kernel `asmwrite` for 24 pairs of thread counts. The pairs hold 0, 16, 32, 48 or 64 threads on mesh 0 and 0, 16, 32, 48 or 56 threads on mesh 1. With 56 threads on mesh 1 the highest CPU is 119. |
| 39 | `echo "== B. asmread 256M, subset of the grid"; date -u` | Prints the title of part B and the UTC date and time. |
| 40 | `: > "$OUT/readgrid.csv"` | Creates `readgrid.csv` as an empty file. |
| 41 | `grid asmread "$OUT/readgrid.csv" 64,0 0,56 16,16 32,32 48,48 64,56` | Part B: the kernel `asmread` for 6 of these pairs: `64,0`, `0,56`, `16,16`, `32,32`, `48,48` and `64,56`. |

### Part C: the sweep over the CPUs 0 to 119, and the end (lines 43 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `echo "== C. per-core sweep"; date -u` | Prints the title of part C and the UTC date and time. |
| 44 | `for sweep in 1 2; do` | Loop: the whole sweep runs two times, with the numbers 1 and 2. |
| 45 | `    : > "$OUT/percore-latency-$sweep.csv"; : > "$OUT/percore-asmread-$sweep.csv"` | Creates the two empty files of this sweep: `percore-latency-N.csv` and `percore-asmread-N.csv`, with the sweep number in the place of `N`. |
| 46 | `    for c in $(seq 0 119); do` | Loop over the CPUs 0 to 119. `seq 0 119` prints these numbers. |
| 47 | `        check_marker` | Marker check once per CPU, before its three benchmark processes. |
| 48 | `        echo "-- cpu $c" >> "$OUT/percore-latency-$sweep.csv"` | Appends a title line with the CPU to the latency file. |
| 49 | `        $L --cpu $c --sizes 16M --reps 2 --min-ms 300 >> "$OUT/percore-latency-$sweep.csv"` | Starts `latency` in the standard mode: the thread is pinned to this CPU, the buffer has 16 MiB, and there are 2 timed repetitions of at least 300 ms each. Each repetition walks the same cycle of pointers repeatedly. The comment of line 6 calls this the repeated way. |
| 50 | `        $L --cpu $c --sizes 16M --fresh 3 >> "$OUT/percore-latency-$sweep.csv"` | Starts `latency` in the fresh mode on the same CPU and with the same size. `--fresh 3`: 2 timed passes, each over a cycle of pointers that was never walked before. |
| 51 | `        echo "-- cpu $c" >> "$OUT/percore-asmread-$sweep.csv"` | Appends a title line with the CPU to the bandwidth file. |
| 52 | `        $B --threads 1 --cpus $c --bytes 8M --kernel asmread --reps 3 --min-ms 300 >> "$OUT/percore-asmread-$sweep.csv"` | Starts `bandwidth` with 1 thread that is pinned to this CPU. It runs the kernel `asmread` over a buffer of 8 MiB: 3 timed repetitions of at least 300 ms each. |
| 53 | `    done` | Ends the loop of line 46. |
| 54 | `done` | Ends the loop of line 44. |
| 55 | `echo "== done"; date -u; echo "$OUT"` | Prints the title `== done`, the UTC date and time, and the path of the result folder. |
