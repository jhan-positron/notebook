# `run_crb.sh` explained, line by line

- Source file: `bench/run_crb.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 162 lines, 6744 bytes).
- sha256 of the source when this page was built: `d84d8546919f013d0719e59446401052be489f49d40df8cff8d3d6c1f05b2e20`.

## Short version: purpose

`run_crb.sh` runs the first measurement plan on CRB without root rights. It measures the load latency per buffer size with `latency`, repeats that sweep under `perf stat` to count cache refills, and measures the read, write and copy throughput with `bandwidth` for several buffer sizes and thread counts. It keeps all processes on the CPUs 0 to 119, stops when the marker file exists, and writes its results into a new result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the program built from `latency.c`. One thread follows a random cycle of pointers through a buffer. The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Cycle**: in `latency`, one walk through all cache lines of the buffer. The event `cpu_cycles` is another thing: it counts the clock cycles of the processor.
- **Chunk**: the loads that `latency` does between two reads of its clock: a whole number of cycles, about 1048576 loads for a small buffer.
- **Sweep**: a row of runs of one program with one setting changed from run to run, for example the buffer size.
- **Case**: the script names four cases by the place where the buffers of the threads fit: L1, L2, L3 and DRAM. The source calls a case a regime.
- **L1, L2, L3, DRAM**: the cache of level 1 and of level 2 of one core, the last cache level, and the main memory.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Refill**: a line that is brought into a cache from outside.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Governor**: the Linux policy that sets the CPU frequency.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options: stop on a failed command and on an unset variable (line 21).
2. Start the script again under `taskset -c 0-119`. Every process of the run then stays on the CPUs 0 to 119 (lines 25 to 27).
3. Set the paths and read the argument `--quick` (lines 29 to 39).
4. Check the CPU list of the variable `CPUS`. Stop when it holds a CPU above 119 (lines 41 to 52).
5. Stop when the marker file exists. Then create the result folder and send all later output to `log.txt` too (lines 61 to 65).
6. Choose the plan: the quick plan or the full plan with its sizes, times and thread counts (lines 69 to 90).
7. Build the programs with `make` (lines 92 to 93).
8. Write the description of the machine to `sysinfo.txt` (lines 95 to 110).
9. Latency sweep: start one `latency` process per buffer size on CPU 3 (quick plan: on the first CPU of the list `CPUS`) and collect the output in `latency.csv` (lines 112 to 117).
10. Latency sweep under `perf stat`: for each size, one short and one long run of `latency` with 7 counter events (lines 122 to 140).
11. Bandwidth sweep: the function `run_bw` starts `bandwidth` once per thread count, for the L1, L2, L3 and DRAM cases (lines 142 to 159).
12. Print the path of the result folder (lines 161 to 162).

## Behavior a reader must know

- The script times nothing itself. Every time and every rate comes from `latency` or `bandwidth`.
- Marker checks: once before the result folder is created, then before each `latency` process of the first sweep, once per size before the two runs under `perf stat`, and before each `bandwidth` process. The long run under `perf stat` has no check of its own. A check that finds the file ends the script with exit status 3. A benchmark process that already runs is not stopped.
- Exit status 2 means a wrong argument or a bad CPU list. With the option `-e`, a failed `make`, a failed `latency` of the first sweep or a failed `bandwidth` also ends the script, with the status of that command.
- A failed run under `perf stat` does not end the script. It prints a message and goes on with the next size.
- Thread placement: `taskset` limits the script and all its child processes to the CPUs 0 to 119. `latency` pins its one thread to CPU 3 in the full plan, and to the first CPU of the list `CPUS` in the quick plan. `bandwidth` pins thread number `i` to entry `i` of the CPU list, so `t` threads use the CPUs 0 to `t - 1` with the default list.
- No command passes `--no-thp`. So both programs ask Linux for 2 MiB pages for their buffers.
- `perf stat` counts for the whole `latency` process, also for the build of the buffer and the warm-up. That is why each size has a short and a long run: the analysis script `summarize.py` divides the difference of the counts by the difference of the loads.
- The script runs `perf` without root rights. A comment of `run_sudo.sh` says that the Linux setting `perf_event_paranoid` is 2 on CRB. With this value a normal user can count events in user mode only [Ref3].
- The comment of line 119 says that the short run times exactly 2 cycles. For the sizes of the plan up to 16 MiB the short run times one chunk of about 1048576 loads, which is 4 cycles or more.
- The header comment counts 27 bandwidth configurations. The full plan starts `bandwidth` 33 times (lines 153 to 159).
- Files in the result folder: `log.txt`, `sysinfo.txt`, `latency.csv`, `latency-perfrun-short.csv`, `latency-perfrun-long.csv`, two files `latency-perf-SIZE-short.csv` and `latency-perf-SIZE-long.csv` per size, and `bandwidth.csv`.

## Source and explanation, line by line

- Text shown: the file `bench/run_crb.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (162 lines, 6744 bytes, sha256 `d84d8546919f013d0719e59446401052be489f49d40df8cff8d3d6c1f05b2e20`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and shell options (lines 1 to 22)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_crb.sh - cache latency and bandwidth measurement plan for CRB.` | Comment: the name and the purpose of the script: the plan of the cache latency and bandwidth measurements on CRB, the Arm reference server under test. |
| 3 | `#` | Comment: an empty comment line. |
| 4 | `# Usage: ./run_crb.sh [--quick]` | Comment: the usage. The script takes at most one argument, `--quick`. |
| 5 | `#   --quick   tiny sizes, 1-2 threads, short timings; for a local smoke test` | Comment: `--quick` runs very small sizes, 1 or 2 threads and short timings. It is meant as a short trial of the script on a local machine. |
| 6 | `#             (set CPUS=0-7 to limit the CPU list on a small host)` | Comment: on a small machine the caller can set `CPUS=0-7` to limit the CPU list. |
| 7 | `#` | Comment: an empty comment line. |
| 8 | `# Estimated wall time of the full run (est.):` | Comment: starts the estimate of the run time of the full plan. Every time in lines 9 to 17 is an estimate (est.). |
| 9 | `#   latency sweep:   26 sizes x 3 reps x 0.3 s = 23 s, plus the sizes above` | Comment: the latency sweep: 26 sizes times 3 repetitions times 0.3 s is 23 s (est.). The sentence goes on in line 10. |
| 10 | `#                    256 MiB where two cycles exceed 0.3 s (1G ~16 s, 2G ~32 s,` | Comment: more time is needed for the sizes above 256 MiB, where two cycles last longer than 0.3 s: about 16 s for `1G` and about 32 s for `2G` (est.). |
| 11 | `#                    512M ~8 s), plus permutation build: about 2 min` | Comment: and about 8 s for `512M` (est.). The time for the build of the pointer order (the comment says permutation) is added. The comment gives about 2 minutes for this step (est.). |
| 12 | `#   latency + perf:  same sweep twice per size (2 cycles, then max(1 s, 6` | Comment: the latency sweep under `perf`: the same sweep twice per size. The first run has 2 cycles. The second run lasts for the longer one of 1 s and 6 cycles. |
| 13 | `#                    cycles)); the 256M-2G sizes dominate: about 2.5 min` | Comment: the sizes from `256M` to `2G` take most of that time. The comment gives about 2.5 minutes for this step (est.). |
| 14 | `#   bandwidth:       27 configurations, 3 reps x 0.5 s per kernel: about 100 s` | Comment: the bandwidth sweep: 27 configurations, with 3 repetitions of 0.5 s per kernel. That is about 100 s of timed loops (est.). With the full plan, lines 153 to 159 start `bandwidth` 33 times. |
| 15 | `#                    of timed loops, plus first touch (up to 120 x 256 MiB x 2` | Comment: the time for the first touch of the buffers is added. The largest configuration has 120 threads, each with 2 buffers of 256 MiB. |
| 16 | `#                    = 60 GiB resident at the largest configuration): about 3-4 min` | Comment: that is 60 GiB of memory in use at the same time. The comment gives about 3 to 4 minutes for the bandwidth sweep (est.). |
| 17 | `#   total:           about 8-9 min` | Comment: the total is about 8 to 9 minutes (est.). |
| 18 | `#` | Comment: an empty comment line. |
| 19 | `# Reads /sys and /proc only for sysinfo.txt; never writes to /sys, cpufreq or` | Comment: the script reads files below `/sys` and `/proc` only for the file `sysinfo.txt`. It never writes to `/sys`, to the frequency settings (`cpufreq`) or to `sysctl`, the Linux tool for system settings. |
| 20 | `# sysctl, never uses sudo, writes only under $HOME/cache-perf.` | Comment: it never uses `sudo`, and it writes only below `$HOME/cache-perf`. |
| 21 | `set -euo pipefail` | Three shell options. `-e`: the script stops when a command fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails, not only the last one. |

### Start the script again on the CPUs 0 to 119 (lines 23 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 23 | `# Run everything (bash, make, tee, perf, the benchmarks' main threads) under` | Comment: everything must run on the allowed CPUs: `bash`, `make`, `tee`, `perf` and the main threads of the benchmarks. The comment calls the allowed CPUs the CPU mask. |
| 24 | `# the allowed CPU mask; the benchmarks' own pinning is a subset of it.` | Comment: the benchmarks pin their own threads to CPUs inside this list. |
| 25 | `if [[ -z ${_RUN_CRB_PINNED:-} ]]; then` | Tests whether the variable `_RUN_CRB_PINNED` is empty or not set. `${X:-}` gives an empty text when the variable is not set, so the option `-u` does not stop the script here. `-z` is true for an empty text. The variable is empty in the first start of the script. |
| 26 | `    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"` | Then starts the script again under `taskset`. `exec` replaces the shell with `taskset -c 0-119`. That tool limits the process to the CPUs 0 to 119 and then runs the script (`$0`) with the same arguments (`$@`). `_RUN_CRB_PINNED=1` is set for the new start only, so the second start skips this block. Every process that the script starts inherits the CPU list. |
| 27 | `fi` | Ends the `if` of line 25. |

### Settings and the argument `--quick` (lines 29 to 40)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. The file exists while another user runs a performance test on CRB. |
| 30 | `CPUS=${CPUS:-0-119}          # CPUs 120-127 are reserved; never list them` | `CPUS`: the CPU list for the threads of `bandwidth`. It keeps the value of the environment variable `CPUS` when that is set and not empty. In the other case it is `0-119`. The comment: the CPUs 120 to 127 are reserved and must never be listed. |
| 31 | `LAT_CPU=3` | `LAT_CPU`: the CPU on which `latency` runs: CPU 3. |
| 32 | `BENCH=$(cd "$(dirname "$0")" && pwd)` | `BENCH`: the folder of this script as an absolute path. `dirname` gives the folder part of the script path `$0`. `cd` goes there, and `pwd` prints the path. Both run inside `$( )`, so the folder of the script itself does not change. |
| 33 | `QUICK=0` | `QUICK`: 0 stands for the full plan. |
| 34 | `case ${1:-} in` | Looks at the first argument. `${1:-}` gives an empty text when there is none. |
| 35 | `    "") ;;` | No argument: nothing to do. |
| 36 | `    --quick) QUICK=1 ;;` | The argument `--quick`: sets `QUICK` to 1. |
| 37 | `    *) echo "usage: $0 [--quick]" >&2; exit 2 ;;` | Every other argument: prints the usage line to the error output (`>&2`) and ends the script with exit status 2. |
| 38 | `esac` | Ends the `case` of line 34. |
| 39 | `[[ $# -le 1 ]] \|\| { echo "usage: $0 [--quick]" >&2; exit 2; }` | Tests the number of arguments (`$#`). `A \|\| B` runs `B` only when `A` fails. So with more than 1 argument the script prints the usage line and ends with exit status 2. |

### Check of the CPU list (lines 41 to 53)

| Line | Source | Explanation |
|---:|---|---|
| 41 | `for tok in ${CPUS//,/ }; do` | Loop over the pieces of the CPU list. `${CPUS//,/ }` replaces every comma with a space, and the shell splits the result at the spaces. |
| 42 | `    if [[ ! $tok =~ ^([0-9]+)(-([0-9]+))?$ ]]; then` | Tests whether the piece does not match a pattern (`=~` compares with a regular expression). The pattern is one number, or two numbers with a hyphen between them. Group 1 holds the first number and group 3 the second. A piece with a step such as `0-118:2` does not match. |
| 43 | `        echo "CPUS=$CPUS: bad token '$tok'" >&2; exit 2` | Then prints the list and the bad piece to the error output and ends the script with exit status 2. |
| 44 | `    fi` | Ends the `if` of line 42. |
| 45 | `    lo=${BASH_REMATCH[1]}; hi=${BASH_REMATCH[3]:-$lo}` | `lo`: the first number of the piece (`BASH_REMATCH[1]`). `hi`: the second number, or `lo` when the piece is one number. |
| 46 | `    if (( lo > hi )); then` | Tests whether the first number is above the second. `(( ))` compares numbers. |
| 47 | `        echo "CPUS=$CPUS: reversed range '$tok'" >&2; exit 2` | Then prints that the range is reversed and ends the script with exit status 2. |
| 48 | `    fi` | Ends the `if` of line 46. |
| 49 | `    if (( hi > 119 )); then` | Tests whether the piece goes above CPU 119. |
| 50 | `        echo "CPUS=$CPUS contains CPUs outside 0-119 (120-127 are reserved)" >&2; exit 2` | Then prints that the list holds CPUs outside 0 to 119 and that 120 to 127 are reserved. The script ends with exit status 2. |
| 51 | `    fi` | Ends the `if` of line 49. |
| 52 | `done` | Ends the loop of line 41. |

### Marker check, result folder and log file (lines 54 to 66)

| Line | Source | Explanation |
|---:|---|---|
| 54 | `check_marker() {` | Starts the function `check_marker`. It ends the script with exit status 3 when the marker file exists. |
| 55 | `    if [[ -e $MARKER ]]; then` | Tests whether the marker file exists (`-e`). |
| 56 | `        echo "$MARKER exists: another team's timed run is active, stopping" >&2` | Then prints to the error output that the file exists, that a timed run of another team is active, and that the script stops. |
| 57 | `        exit 3` | Then ends the script with exit status 3. |
| 58 | `    fi` | Ends the `if` of line 55. |
| 59 | `}` | Ends the function `check_marker`. |
| 61 | `check_marker` | The first marker check. Nothing was written up to here. |
| 62 | `OUT=$HOME/cache-perf/results/$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder: `$HOME/cache-perf/results/` plus the UTC time of this moment. `date -u` prints the time in the form year, month, day, the letter `T`, hour, minute, second, the letter `Z`. |
| 63 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders and does not fail when the folder exists. |
| 64 | `exec > >(tee -a "$OUT/log.txt") 2>&1` | From here on the standard output of the script goes to the program `tee`. `tee` prints it and also appends it to the file `log.txt` in the result folder (`-a`). `>( )` starts `tee` as a process of its own. `2>&1` sends the error output to the same place. |
| 65 | `echo "results: $OUT"` | Prints the path of the result folder. |

### The plan: buffer sizes, times and thread counts (lines 67 to 91)

| Line | Source | Explanation |
|---:|---|---|
| 67 | `# Bandwidth regimes. Copy uses two buffers per thread, so its thread list is` | Comment: the settings below define the bandwidth cases, which the comment calls regimes. The copy kernel uses two buffers per thread. So its list of thread counts has a limit of its own, which line 68 gives. |
| 68 | `# capped separately to keep 2 x bytes x threads inside the level under test.` | Comment: 2 times the buffer size times the number of threads must fit into the cache level under test. |
| 69 | `if (( QUICK )); then` | Tests whether `--quick` was given. |
| 70 | `    LAT_CPU=${CPUS%%[-,]*}   # first CPU of the list: a small host may lack CPU 3` | Quick plan: `LAT_CPU` becomes the first CPU of the list. `${CPUS%%[-,]*}` cuts the text off at the first hyphen or comma. The comment: a small machine may have no CPU 3. |
| 71 | `    LAT_SIZES=4K,16K,64K,1M,8M` | Quick plan: 5 buffer sizes for `latency`. |
| 72 | `    LAT_REPS=1; LAT_MS=50; PERF_MS=50` | Quick plan: `latency` runs 1 repetition of at least 50 ms. The long run under `perf` lasts at least 50 ms. |
| 73 | `    BW_REPS=1; BW_MS=50` | Quick plan: `bandwidth` runs 1 repetition of at least 50 ms per kernel. |
| 74 | `    L1_THREADS="1 2"; L2_THREADS="1 2"` | Quick plan: 1 and 2 threads for the L1 case and for the L2 case. |
| 75 | `    L3_BYTES=8M; L3_RW_THREADS="1 2"; L3_COPY_THREADS="1"` | Quick plan, L3 case: 8 MiB per thread, 1 and 2 threads for read and write, and 1 thread for copy. |
| 76 | `    DRAM_SMALL_BYTES=64M; DRAM_SMALL_THREADS="1"` | Quick plan, small DRAM case: 64 MiB per thread and 1 thread. |
| 77 | `    DRAM_BYTES=32M; DRAM_THREADS="2"` | Quick plan, large DRAM case: 32 MiB per thread and 2 threads. |
| 78 | `else` | The other case: the full plan. |
| 79 | `    LAT_SIZES=4K,8K,16K,32K,48K,64K,96K,128K,256K,512K,1M,1.5M,2M,3M,4M,8M,16M,32M,64M,96M,128M,192M,256M,512M,1G,2G` | Full plan: the 26 buffer sizes of `latency`, from 4 KiB to 2 GiB. `K`, `M` and `G` stand for 1024 bytes, 1024 times 1024 bytes, and 1024 times that. |
| 80 | `    LAT_REPS=3; LAT_MS=300; PERF_MS=1000` | Full plan: `latency` runs 3 repetitions of at least 300 ms each. The long run under `perf` lasts at least 1000 ms. |
| 81 | `    BW_REPS=3; BW_MS=500` | Full plan: `bandwidth` runs 3 repetitions of at least 500 ms per kernel. |
| 82 | `    L1_THREADS="1 8 32 120"; L2_THREADS="1 8 32 120"` | Full plan: 1, 8, 32 and 120 threads for the L1 case (32 KiB per thread, line 153) and for the L2 case (1 MiB per thread, line 154). |
| 83 | `    # L3: 8 MiB per thread (4x the 2 MiB L2); 14 x 8 MiB = 112 MiB and` | Comment: the L3 case uses 8 MiB per thread, 4 times the L2 size of 2 MiB. 14 threads times 8 MiB is 112 MiB. |
| 84 | `    # copy 7 x 2 x 8 MiB = 112 MiB both stay under the 128 MiB L3.` | Comment: for copy, 7 threads times 2 buffers times 8 MiB is 112 MiB too. By the comment both stay below the L3 size of 128 MiB. The project calls this last cache level SLC. |
| 85 | `    L3_BYTES=8M; L3_RW_THREADS="1 2 4 8 12 14"; L3_COPY_THREADS="1 2 4 7"` | Full plan, L3 case: 8 MiB per thread. 1, 2, 4, 8, 12 and 14 threads for read and write. 1, 2, 4 and 7 threads for copy. |
| 86 | `    # DRAM: 1 GiB per thread (8x L3) for the small thread counts, where the` | Comment: the DRAM case uses 1 GiB per thread, 8 times the L3 size, for the small thread counts. By the comment the value per core is read from these runs. |
| 87 | `    # per-core number is read; 256 MiB per thread for the large ones.` | Comment: the large thread counts use 256 MiB per thread. |
| 88 | `    DRAM_SMALL_BYTES=1G; DRAM_SMALL_THREADS="1 2 4 8"` | Full plan, small DRAM case: 1 GiB per thread with 1, 2, 4 and 8 threads. |
| 89 | `    DRAM_BYTES=256M; DRAM_THREADS="16 32 64 96 120"` | Full plan, large DRAM case: 256 MiB per thread with 16, 32, 64, 96 and 120 threads. |
| 90 | `fi` | Ends the `if` of line 69. |

### Build the programs and write `sysinfo.txt` (lines 92 to 111)

| Line | Source | Explanation |
|---:|---|---|
| 92 | `echo "== build"` | Prints the title `== build`. |
| 93 | `make -C "$BENCH"` | Builds the programs: `make -C` runs `make` in the folder of the script. A failed build ends the script (option `-e`). |
| 95 | `echo "== sysinfo"` | Prints the title `== sysinfo`. |
| 96 | `{` | Starts a group of commands. The output of the whole group goes to the file `sysinfo.txt` (line 110). |
| 97 | `    echo "## date"; date -u` | Writes a title line and then the UTC date and time. |
| 98 | `    echo "## uname"; uname -a` | The name, the version and the machine type of the running Linux kernel (`uname -a`). |
| 99 | `    echo "## nproc"; nproc` | The number of CPUs that this process may use (`nproc`). Under the `taskset` of line 26 these are the CPUs 0 to 119. |
| 100 | `    echo "## gcc"; gcc --version` | The version of `gcc`. |
| 101 | `    echo "## cmdline"; cat /proc/cmdline` | The command line of the Linux kernel of this boot (file `/proc/cmdline`). |
| 102 | `    echo "## governor"; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null \|\| echo none` | The governor of CPU 0, the Linux policy that sets the CPU frequency. `2>/dev/null` discards an error message. When the file cannot be read, `\|\| echo none` prints `none`. |
| 103 | `    echo "## thp"; cat /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag \|\| true` | The Linux settings for transparent huge pages, the 2 MiB pages that Linux can use in place of its smaller standard pages: the files `enabled` and `defrag`. `\|\| true` keeps the script running when a file cannot be read. |
| 104 | `    echo "## lscpu"; lscpu` | The description of the processor (`lscpu`). |
| 105 | `    echo "## cache sysfs (cpu0)"` | A title line for the cache list. |
| 106 | `    for d in /sys/devices/system/cpu/cpu0/cache/index*; do` | Loop over the cache entries that Linux lists for CPU 0 (the folders `index0`, `index1` and so on). |
| 107 | `        echo "$d: level=$(cat "$d/level") type=$(cat "$d/type") size=$(cat "$d/size") ways=$(cat "$d/ways_of_associativity") line=$(cat "$d/coherency_line_size") sets=$(cat "$d/number_of_sets") shared_cpu_list=$(cat "$d/shared_cpu_list")"` | Prints one line per cache: the folder, the level, the type, the size, the number of ways, the line size, the number of sets and the list of the CPUs that share the cache. Each value is read with `cat` from a file of that folder. |
| 108 | `    done` | Ends the loop of line 106. |
| 109 | `    echo "## interrupts"; cat /proc/interrupts` | The interrupt counts per CPU (file `/proc/interrupts`). |
| 110 | `} > "$OUT/sysinfo.txt" 2>&1` | Ends the group. Its standard output and its error output go to `sysinfo.txt` in the result folder. `>` replaces an old file of that name. |

### Latency sweep: one `latency` process per buffer size (lines 112 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 112 | `echo "== latency sweep (cpu $LAT_CPU)"` | Prints the title of the step with the CPU of `latency`. |
| 113 | `: > "$OUT/latency.csv"` | Creates `latency.csv` as an empty file. `:` is a command that does nothing, and `>` creates the file or empties it. |
| 114 | `for size in ${LAT_SIZES//,/ }; do` | Loop over the buffer sizes of the plan. |
| 115 | `    check_marker` | Marker check before each size. |
| 116 | `    "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps $LAT_REPS --min-ms $LAT_MS >> "$OUT/latency.csv"` | Starts `latency` for one size and appends its output to `latency.csv` (`>>`). `--cpu`: the program pins its one thread to `LAT_CPU`. That is CPU 3 in the full plan and the first CPU of the list `CPUS` in the quick plan (line 70). `--reps` and `--min-ms`: in the full plan 3 timed repetitions of at least 300 ms each. The command holds no `--no-thp`, so the program asks Linux for 2 MiB pages. Each size is a new process. The script waits for its end. |
| 117 | `done` | Ends the loop of line 114. |

### Latency sweep under `perf stat`: a short and a long run per size (lines 119 to 141)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `# Two perf runs per size: "short" = exactly 2 timed cycles, "long" = at least` | Comment: two runs under `perf` per size. By the comment the run named short times exactly 2 cycles. This holds for the sizes of the plan from 32 MiB up. For the sizes of the plan up to 16 MiB `latency` reads its clock only after about 1048576 loads, which is 4 cycles or more. The run named long times at least ... The sentence goes on in line 120. |
| 120 | `# PERF_MS and 6 cycles. Setup (first touch, permutation, warm-up) is identical` | Comment: ... `PERF_MS` milliseconds and 6 cycles. The setup is the same in both runs: the first touch, the build of the pointer order and the warm-up. |
| 121 | `# in both, so count_long - count_short is the refills of the extra timed loads.` | Comment: so the count of the long run minus the count of the short run is the number of refills that the extra timed loads cause. A refill is a line that is brought into a cache from outside. |
| 122 | `echo "== latency sweep under perf stat (short: 2 cycles; long: >= $PERF_MS ms and 6 cycles)"` | Prints the title of the step with the value of `PERF_MS`. |
| 123 | `PERF_EVENTS=l1d_cache_refill,l2d_cache_refill,l3d_cache_refill,ll_cache_miss_rd,dtlb_walk,cpu_cycles,inst_retired` | `PERF_EVENTS`: the 7 counter events. `l1d_cache_refill`, `l2d_cache_refill` and `l3d_cache_refill`: refills of the data cache of level 1, 2 and 3. `ll_cache_miss_rd`: read accesses that miss the last cache level. `dtlb_walk`: data accesses that need a walk of the page table. `cpu_cycles`: processor cycles. `inst_retired`: executed instructions [Ref2]. |
| 124 | `if command -v perf >/dev/null; then` | Tests whether a command with the name `perf` exists (`command -v`). `>/dev/null` discards its output. |
| 125 | `    : > "$OUT/latency-perfrun-short.csv"` | Creates the empty file `latency-perfrun-short.csv`. It will hold the output of `latency` in the short runs. |
| 126 | `    : > "$OUT/latency-perfrun-long.csv"` | Creates the empty file `latency-perfrun-long.csv` for the long runs. |
| 127 | `    for size in ${LAT_SIZES//,/ }; do` | Loop over the buffer sizes of the plan. |
| 128 | `        check_marker` | Marker check before each size. |
| 129 | `        if ! perf stat -x, -e "$PERF_EVENTS" -o "$OUT/latency-perf-$size-short.csv" -- \` | The short run. `perf stat` starts the command that follows `--` and counts the events for that process, from its start to its end [Ref1]. So the counts also hold the build of the buffer and the warm-up. `-x,`: one line per event, with commas between the fields. `-e`: the events of line 123. `-o`: the counts go to the file `latency-perf-SIZE-short.csv`, with the size in the place of `SIZE`. `!` reverses the result: the condition is true when the command fails. The backslash continues the command in the next line. |
| 130 | `                "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps 1 --min-ms 0 --min-cycles 2 \` | Continues the short run: the command that `perf` starts. `latency` on the CPU of `LAT_CPU` (CPU 3 in the full plan), one size, 1 repetition, no minimum time (`--min-ms 0`) and at least 2 cycles (`--min-cycles 2`). |
| 131 | `                >> "$OUT/latency-perfrun-short.csv" \|\|` | Continues the short run: the output of `latency` is appended to `latency-perfrun-short.csv`. `\|\|`: the long run starts only when the short run did not fail. |
| 132 | `           ! perf stat -x, -e "$PERF_EVENTS" -o "$OUT/latency-perf-$size-long.csv" -- \` | The long run: the same `perf stat` command. The counts go to the file `latency-perf-SIZE-long.csv`. |
| 133 | `                "$BENCH/latency" --cpu "$LAT_CPU" --sizes "$size" --reps 1 --min-ms $PERF_MS --min-cycles 6 \` | Continues the long run: `latency` with 1 repetition, at least `PERF_MS` milliseconds (1000 in the full plan) and at least 6 cycles. |
| 134 | `                >> "$OUT/latency-perfrun-long.csv"; then` | Continues the long run: the output of `latency` is appended to `latency-perfrun-long.csv`. `then` ends the condition. |
| 135 | `            echo "perf stat failed for size $size; continuing"` | When one of the two runs failed: prints a message with the size. The script goes on with the next size. |
| 136 | `        fi` | Ends the `if` of line 129. |
| 137 | `    done` | Ends the loop of line 127. |
| 138 | `else` | The other case: no command `perf` was found. |
| 139 | `    echo "perf not found; skipping the perf run"` | Prints that `perf` was not found and that the step is skipped. |
| 140 | `fi` | Ends the `if` of line 124. |

### Bandwidth sweep and the end of the script (lines 142 to 162)

| Line | Source | Explanation |
|---:|---|---|
| 142 | `echo "== bandwidth sweep (cpus $CPUS)"` | Prints the title of the step with the CPU list. |
| 143 | `: > "$OUT/bandwidth.csv"` | Creates `bandwidth.csv` as an empty file. |
| 144 | `run_bw() { # kernel bytes thread-list` | Starts the function `run_bw`. Its three arguments are the kernel, the buffer size per thread and a list of thread counts. |
| 145 | `    local kernel=$1 bytes=$2 t` | `kernel`, `bytes`: the first two arguments. `t`: the loop variable. `local` keeps the three names inside the function. |
| 146 | `    for t in $3; do` | Loop over the thread counts of the third argument. |
| 147 | `        check_marker` | Marker check before each start of `bandwidth`. |
| 148 | `        echo "-- kernel $kernel bytes $bytes threads $t"` | Prints one line to the log: the kernel, the buffer size and the thread count. |
| 149 | `        "$BENCH/bandwidth" --threads "$t" --cpus "$CPUS" --bytes "$bytes" --kernel "$kernel" \` | Starts `bandwidth`. `--threads`: the number of threads. `--cpus`: the CPU list. The program pins its thread number `i` to entry `i` of the list. So with the list `0-119` the `t` threads sit on the CPUs 0 to `t - 1`. `--bytes`: the buffer size of each thread. `--kernel`: the kernel. `all` runs the read, the write and the copy kernel one after the other in the same process. The backslash continues the command. |
| 150 | `            --reps $BW_REPS --min-ms $BW_MS >> "$OUT/bandwidth.csv"` | Continues the command: in the full plan 3 repetitions of at least 500 ms per kernel. The output is appended to `bandwidth.csv`. |
| 151 | `    done` | Ends the loop of line 146. |
| 152 | `}` | Ends the function `run_bw`. |
| 153 | `run_bw all 32K "$L1_THREADS"` | L1 case: all three kernels with 32 KiB per thread. |
| 154 | `run_bw all 1M "$L2_THREADS"` | L2 case: all three kernels with 1 MiB per thread. |
| 155 | `run_bw read "$L3_BYTES" "$L3_RW_THREADS"` | L3 case, read kernel: 8 MiB per thread. |
| 156 | `run_bw write "$L3_BYTES" "$L3_RW_THREADS"` | L3 case, write kernel: 8 MiB per thread. |
| 157 | `run_bw copy "$L3_BYTES" "$L3_COPY_THREADS"` | L3 case, copy kernel: two buffers of 8 MiB per thread, with the shorter list of thread counts. |
| 158 | `run_bw all "$DRAM_SMALL_BYTES" "$DRAM_SMALL_THREADS"` | Small DRAM case: all three kernels with 1 GiB per thread. |
| 159 | `run_bw all "$DRAM_BYTES" "$DRAM_THREADS"` | Large DRAM case: all three kernels with 256 MiB per thread. |
| 161 | `echo "== done"` | Prints the title `== done`. |
| 162 | `echo "$OUT"` | Prints the path of the result folder as the last line of the log. |

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events for it. The options `-e`, `-x` and `-o`).
- [Ref2] external source: Arm Architecture Reference Manual for A-profile architecture, the list of the common events of the performance monitors (`L1D_CACHE_REFILL`, `L2D_CACHE_REFILL`, `L3D_CACHE_REFILL`, `LL_CACHE_MISS_RD`, `DTLB_WALK`, `CPU_CYCLES`, `INST_RETIRED`).
- [Ref3] external source: Linux manual page `perf_event_open(2)`, the file `/proc/sys/kernel/perf_event_paranoid` (the value 2 allows only measurements in user space).
