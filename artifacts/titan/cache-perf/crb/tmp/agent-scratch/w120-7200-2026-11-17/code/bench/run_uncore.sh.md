# `run_uncore.sh` explained, line by line

- Source file: `bench/run_uncore.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 48 lines, 2490 bytes).
- sha256 of the source when this page was built: `5e764669631f8979d70c5e3c3d65d48e4fccde58401f7d5297b19b94e53d5dc7`.

## Short version: purpose

`run_uncore.sh` counts events of the SLC, the last cache level, with the counters of the two meshes while a benchmark runs. It runs the pointer chase of `latency` at 12 buffer sizes, each once short and once long, and then two streaming reads of `bandwidth`. It starts only when the Linux setting `perf_event_paranoid` is 0 or below, and it stops when the marker file exists.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh, CMN**: the network inside one half of the chip. It connects the cores, the SLC and the memory. Arm calls it CMN (Coherent Mesh Network).
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Home node**: a node of the mesh that owns a part of the memory addresses and holds one part of the SLC. Arm calls this node type HN-S. The event names of the home nodes start with `hns`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: a counter unit. Linux shows the counters of the two meshes as the PMUs `arm_cmn_0` and `arm_cmn_1`.
- **Uncore PMU**: a counter unit that does not belong to one core. Its counters count for the whole system.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **`perf_event_paranoid`**: the Linux setting that decides what a user without root rights may count.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time, and `perf` prints a scaled count for it.
- **`latency`**: the program built from `latency.c`. One thread follows a cycle of pointers through a buffer (the pointer chase). The program prints the time per load in nanoseconds.
- **`bandwidth`**: the program built from `bandwidth.c`. Each of its threads reads, writes or copies its own buffer. The program prints the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Cycle**: in `latency`, one walk through all cache lines of the buffer.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **MiB, GiB**: 1048576 bytes and 1073741824 bytes.

## Main flow

1. Set the shell options and start the script again under `taskset -c 0-119` (lines 9 to 12).
2. Stop when the marker file exists (lines 13 to 16).
3. Stop with exit status 4 when `perf_event_paranoid` is above 0 (lines 17 to 18).
4. Create the result folder, send all later output to `log.txt` too, and build the programs (lines 19 to 23).
5. Build the event list: 7 events of the home nodes on each of the two meshes (lines 24 to 30).
6. For each of 12 buffer sizes: run `latency` on CPU 3 under `perf stat`, first short and then long (lines 33 to 40).
7. Run `bandwidth` under `perf stat` twice: 14 reading threads with 8 MiB each, then 64 reading threads with 256 MiB each (lines 42 to 47).
8. Print the path of the result folder (line 48).

## Behavior a reader must know

- The script times nothing itself. The times come from `latency` and `bandwidth`. The counts come from `perf stat`.
- `perf stat -a` counts for the whole system from the start to the end of the benchmark process. So a count also holds the events of other programs, and it holds the build of the buffer and the warm-up of the benchmark. The short and the long run of a size exist to subtract the build and the warm-up.
- The script asks for 7 events per mesh in one `perf stat` run. In the result files of the run of 2026-10-30, 2 of 364 event rows show 100.00 in the field for the share of the running time. The other rows show 0 to 58 percent, and 10 rows hold `<not counted>` in place of a count [Ref3]. So the events were multiplexed in that run, and its counts are scaled values [Ref1].
- The comment of line 31 says that the short run has 2 cycles. For the sizes 1 MiB, 8 MiB and 16 MiB the short run does one chunk of 1048576 loads, which is 64, 8 and 4 cycles.
- Marker checks: once at the start, once before the two runs of each size, and once before each `bandwidth` run. A check that finds the file ends the script with exit status 3. A process that already runs is not stopped.
- With the option `-e` a failed `make` or a failed `perf stat` ends the script with the status of that command.
- Thread placement: `taskset` limits everything to the CPUs 0 to 119. `latency` pins its one thread to CPU 3. `bandwidth` pins thread number `i` to entry `i` of the list `0-119`: 14 threads use the CPUs 0 to 13, and 64 threads use the CPUs 0 to 63.
- Files in the result folder: `log.txt`, `chase-short.csv` and `chase-long.csv` (output of `latency`), `cmn-SIZE-short.csv` and `cmn-SIZE-long.csv` per size (counts), `bw-8M-14T.csv` and `bw-256M-64T.csv` (output of `bandwidth`), and `cmn-bw-8M-14T.csv` and `cmn-bw-256M-64T.csv` (counts).

## Source and explanation, line by line

- Text shown: the file `bench/run_uncore.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (48 lines, 2490 bytes, sha256 `5e764669631f8979d70c5e3c3d65d48e4fccde58401f7d5297b19b94e53d5dc7`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and shell options (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_uncore.sh - count CMN (mesh) system-level-cache events while the pointer` | Comment: the name and the purpose of the script. It counts events of the system level cache in the mesh while the pointer chase of `latency` runs. CMN is the Arm name of the mesh, the network that connects the cores, the last cache level and the memory. The project calls the system level cache SLC. |
| 3 | `# chase runs at chosen footprints, to tell whether the sysfs "L3" is the mesh SLC` | Comment: the chase runs at chosen buffer sizes (the comment says footprints). The first question: is the cache that Linux lists as `L3` in its system files (sysfs) the SLC of the mesh? The sentence ends in line 4. |
| 4 | `# and where its hits turn into DRAM reads.` | Comment: the second question: at which size do the hits of that cache become reads from DRAM, the main memory? |
| 5 | `# Needs kernel.perf_event_paranoid <= 0 (uncore PMUs are system-wide). The CMN` | Comment: the script needs the Linux setting `kernel.perf_event_paranoid` at 0 or below. The reason by the comment: the counter units of the mesh are uncore PMUs, and they count for the whole system. The next sentence starts here: the events of the CMN ... |
| 6 | `# PMU events are opened on the PMU's own cpumask CPU (cpu 0), not on every CPU,` | Comment: ... PMU are opened on one CPU only: the CPU that the file `cpumask` of the PMU names, which the comment gives as CPU 0. They are not opened on every CPU. |
| 7 | `# so no interrupt reaches CPUs 120-127.` | Comment: so no interrupt reaches the CPUs 120 to 127. |
| 8 | `# Same rules as run_crb.sh: CPUs 0-119 only, stops if the RUNNING marker appears.` | Comment: the rules are those of `run_crb.sh`: only the CPUs 0 to 119, and the script stops when the marker file exists. |
| 9 | `set -euo pipefail` | Three shell options. `-e`: the script stops when a command fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails. |

### Start again on the CPUs 0 to 119, the two checks, the result folder and the build (lines 10 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `if [[ -z ${_RUN_CRB_PINNED:-} ]]; then` | Tests whether the variable `_RUN_CRB_PINNED` is empty or not set. `${X:-}` gives an empty text for an unset variable, and `-z` is true for an empty text. The variable is empty in the first start of the script. |
| 11 | `    _RUN_CRB_PINNED=1 exec taskset -c 0-119 "$0" "$@"` | Then starts the script again under `taskset`. `exec` replaces the shell with `taskset -c 0-119`. That tool limits the process to the CPUs 0 to 119 and then runs the script (`$0`) with the same arguments (`$@`). `_RUN_CRB_PINNED=1` is set for the new start only, so the second start skips this block. Every process that the script starts inherits the CPU list. |
| 12 | `fi` | Ends the `if` of line 10. |
| 13 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. The file exists while another user runs a performance test on CRB. |
| 14 | `BENCH=$(cd "$(dirname "$0")" && pwd)` | `BENCH`: the folder of this script as an absolute path. `dirname` gives the folder part of the script path `$0`, `cd` goes there, and `pwd` prints the path. |
| 15 | `check_marker() { [[ -e $MARKER ]] && { echo "$MARKER exists: stopping" >&2; exit 3; }; return 0; }` | Defines the function `check_marker` in one line. `-e` tests whether the marker file exists. `A && B` runs `B` only when `A` succeeds. So when the file exists, the function prints `exists: stopping` with the path to the error output (`>&2`) and ends the script with exit status 3. In the other case `return 0` makes the function succeed, so the option `-e` does not stop the script. |
| 16 | `check_marker` | The first marker check. Nothing was written up to here. |
| 17 | `P=$(cat /proc/sys/kernel/perf_event_paranoid)` | `P`: the value of the Linux setting `perf_event_paranoid`, read from its file. The setting decides what a user without root rights may count. |
| 18 | `if (( P > 0 )); then echo "perf_event_paranoid=$P; need <= 0" >&2; exit 4; fi` | Tests whether the value is above 0 (`(( ))` compares numbers). Then the script prints the value and the text `need <= 0` to the error output and ends with exit status 4. It has written no file at this point. |
| 19 | `OUT=$HOME/cache-perf/results/uncore-$(date -u +%Y%m%dT%H%M%SZ)` | `OUT`: the result folder: `$HOME/cache-perf/results/uncore-` plus the UTC time of this moment (`date -u` with a format). |
| 20 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders. |
| 21 | `exec > >(tee -a "$OUT/log.txt") 2>&1` | From here on the standard output of the script goes to the program `tee`. `tee` prints it and also appends it to `log.txt` in the result folder. `>( )` starts `tee` as a process of its own. `2>&1` sends the error output to the same place. |
| 22 | `echo "results: $OUT"` | Prints the path of the result folder. |
| 23 | `make -C "$BENCH"` | Builds the programs: `make -C` runs `make` in the folder of the script. A failed build ends the script. |

### The event list: 7 events on each of the two meshes (lines 24 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `EV=""` | `EV`: the event list for `perf`. It is empty at the start. |
| 25 | `for c in 0 1; do` | Loop over the two meshes, 0 and 1. |
| 26 | `    for e in hns_slc_sf_cache_access_all hns_cache_miss_all hns_cache_fill_all hns_sf_hit_all hns_pocq_reqs_recvd_read hns_mc_reqs_local_all hns_mc_reqs_remote_all; do` | Loop over 7 event names. The prefix `hns` stands for the home nodes (node type HN-S), the nodes that hold the parts of the SLC. The notes of the project name these 7 counts as: SLC accesses, cache misses, cache fills, hits of the snoop filter, read requests received, and memory requests of the kinds local and remote [Ref4]. |
| 27 | `        EV="$EV${EV:+,}arm_cmn_$c/$e/"` | Appends one event to the list, in the form `arm_cmn_N/NAME/`: the PMU of mesh `N` and the event name. `${EV:+,}` gives a comma when the list is not empty. An event in this form names no node. So it counts the sum over all home nodes of that mesh [Ref2]. |
| 28 | `    done` | Ends the loop of line 26. |
| 29 | `done` | Ends the loop of line 25. |
| 30 | `echo "events: $EV"` | Prints the whole event list to the log: 14 events, 7 for each mesh. |

### The pointer chase under `perf stat`: a short and a long run per size (lines 31 to 40)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `# Two runs per size, like run_crb.sh: short (2 cycles) and long (6+ cycles, >= 1 s).` | Comment: two runs per size, as in `run_crb.sh`: a short run with 2 cycles, and a long run with 6 or more cycles and at least 1 s. A cycle is one walk through all lines of the buffer. For the sizes below 32 MiB the short run does more than 2 cycles: `latency` reads its clock only after about 1048576 loads. |
| 32 | `# count_long - count_short divided by loads_long - loads_short = events per load.` | Comment: the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run, gives the events per load. |
| 33 | `: > "$OUT/chase-short.csv"; : > "$OUT/chase-long.csv"` | Creates two empty files: `chase-short.csv` and `chase-long.csv`. `:` does nothing, and `>` creates the file or empties it. They will hold the output of `latency`. |
| 34 | `for s in 1M 8M 16M 32M 48M 64M 96M 128M 192M 256M 512M 1G; do` | Loop over 12 buffer sizes from 1 MiB to 1 GiB. |
| 35 | `    check_marker` | Marker check before the two runs of a size. |
| 36 | `    perf stat -a -x, -e "$EV" -o "$OUT/cmn-$s-short.csv" -- \` | The short run. `perf stat` starts the command that follows `--` and counts until that command ends. `-a`: it counts for the whole system and not only for the command [Ref1]. So a count holds every event of its type in the mesh during the run, whichever process causes it. `-x,`: one line per event, with commas between the fields. `-e`: the 14 events. `-o`: the counts go to the file `cmn-SIZE-short.csv`, with the size in the place of `SIZE`. The backslash continues the command. |
| 37 | `        "$BENCH/latency" --cpu 3 --sizes $s --reps 1 --min-ms 0 --min-cycles 2 >> "$OUT/chase-short.csv"` | Continues the short run: `latency` with its thread pinned to CPU 3, one size, 1 repetition, no minimum time (`--min-ms 0`) and at least 2 cycles. Its output is appended to `chase-short.csv`. |
| 38 | `    perf stat -a -x, -e "$EV" -o "$OUT/cmn-$s-long.csv" -- \` | The long run: the same `perf stat` command. The counts go to the file `cmn-SIZE-long.csv`. |
| 39 | `        "$BENCH/latency" --cpu 3 --sizes $s --reps 1 --min-ms 1000 --min-cycles 6 >> "$OUT/chase-long.csv"` | Continues the long run: `latency` with 1 repetition, at least 1000 ms and at least 6 cycles. Its output is appended to `chase-long.csv`. |
| 40 | `done` | Ends the loop of line 34. |

### Two streaming reads under `perf stat`, and the end (lines 41 to 48)

| Line | Source | Explanation |
|---:|---|---|
| 41 | `# Streaming read, 14 threads x 8 MiB (the "L3 regime"): are the reads served by the SLC?` | Comment: a streaming read with 14 threads and 8 MiB per thread, which the comment calls the L3 case (regime). Its question: does the SLC serve these reads? |
| 42 | `check_marker` | Marker check. |
| 43 | `perf stat -a -x, -e "$EV" -o "$OUT/cmn-bw-8M-14T.csv" -- \` | `perf stat` with the same options as in line 36. The counts go to the file `cmn-bw-8M-14T.csv`. |
| 44 | `    "$BENCH/bandwidth" --threads 14 --cpus 0-119 --bytes 8M --kernel read --reps 1 --min-ms 1000 > "$OUT/bw-8M-14T.csv"` | Continues the command: `bandwidth` with 14 threads. The program pins thread number `i` to entry `i` of the list `0-119`, so the threads sit on the CPUs 0 to 13. Each thread reads its own buffer of 8 MiB (`--kernel read`), in 1 repetition of at least 1000 ms. `>` writes the output of `bandwidth` to the file `bw-8M-14T.csv`. |
| 45 | `check_marker` | Marker check. |
| 46 | `perf stat -a -x, -e "$EV" -o "$OUT/cmn-bw-256M-64T.csv" -- \` | `perf stat` with the same options. The counts go to the file `cmn-bw-256M-64T.csv`. |
| 47 | `    "$BENCH/bandwidth" --threads 64 --cpus 0-119 --bytes 256M --kernel read --reps 1 --min-ms 1000 > "$OUT/bw-256M-64T.csv"` | Continues the command: `bandwidth` with 64 reading threads on the CPUs 0 to 63, which are the CPUs of mesh 0. Each thread has a buffer of 256 MiB. There is 1 repetition of at least 1000 ms. The output goes to the file `bw-256M-64T.csv`. |
| 48 | `echo "== done"; echo "$OUT"` | Prints the title `== done` and then the path of the result folder. |

## References

- [Ref1] external source: manual page `perf-stat(1)` (the command runs a program and counts events. `-a` counts on all CPUs of the system. The fields of an output line with `-x` are the count, the unit, the event name, the running time of the counter and the share of the measurement time for which the counter was running. The option `--no-scale` turns the scaling of the counts off).
- [Ref2] external source: Linux kernel documentation, page `admin-guide/perf/arm-cmn` (an event counts the sum over all nodes of its type, unless `bynodeid` and `nodeid` select one node).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/uncore-20261030T203537Z`: a result folder with the file names of this script, started on 2026-10-30 at 20:35 UTC. Its 26 files `cmn-*.csv` hold 364 event rows. 2 rows show 100.00 in the fifth field, the share of the running time. The other rows show 0.00 to 58.00, and 10 rows hold `<not counted>` in the first field (counted with a script on 2026-11-25).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/plan-2026-11-02.md`: the plan note of 2026-11-02. Its section "Part 3" names the home node events: write and read requests received, cache access and miss, fill, memory requests (local), memory requests (remote), evictions and snoop-filter hits.
