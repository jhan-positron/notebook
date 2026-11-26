## Short version: purpose

`subtract.py` analyses one counter file of the script `run_sudo.sh`: `writebw.csv` of part 3 or `crossmesh.csv` of part 4. For each case and each mesh event it prints the number of events per cache line that the benchmark moved, computed from the difference between a long run and a short run. It also checks the data and ends with exit status 1 when a check fails.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Mesh event**: an event that a counter of a mesh counts, for example the requests that the home nodes received. `perf` prints its name as `arm_cmn_0/NAME/` for mesh 0 and `arm_cmn_1/NAME/` for mesh 1.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. Its row of a repetition holds the bytes that all threads moved (`total_bytes`) and the total rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Case, tag**: one setting of `bandwidth` in `run_sudo.sh`: a kernel, a buffer size and a thread count or CPU list. The tag is its short name, for example `asmwrite-8M-1`.
- **Event set**: the events that one run of `perf stat` counts.
- **Short run, long run**: two runs of the same case under the same event set. The timed interval of `bandwidth` lasts at least 200 ms in the short run and at least 2000 ms in the long run.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **Block**: the rows of one run in the input file: a title line that starts with `--`, then the output of `bandwidth`, then the count rows of `perf stat`.
- **Line**: a cache line, 64 bytes.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB**: 1e9 bytes.

## Main flow

1. Read the input file line by line and split it into blocks: one block per run, and one block for all idle controls ({L11-29}).
2. Compute the idle rate of each event in events per second ({L30-34}).
3. Pair the short and the long block of each case and event set ({L35-37}).
4. For each pair: check the data, compute the difference in cache lines, and print for each event on each mesh the rate per line with the background subtracted ({L38-57}).
5. Print the number of failed checks and their texts, and end with exit status 1 when a check failed ({L58-62}).

## Behavior a reader must know

- Rate per line of an event: the count of the long run minus the count of the short run, divided by the line difference, minus the background per line.
- Line difference: `total_bytes` of the long run minus `total_bytes` of the short run, divided by 64. `total_bytes` is field 5 of the row of repetition 0 of `bandwidth`. It covers the timed interval only, summed over all threads.
- The counts cover the whole `bandwidth` process, also the first write of the buffers and the warm-up. Both runs have that part, so the subtraction removes it.
- A count is field 1 of a count row of `perf stat`, under the event name in field 3. Field 4 is the running time of the counter in nanoseconds, and field 5 is the share of the time for which it ran, in percent.
- Background per line: the idle rate of the event (count of the idle control divided by its running time), times the difference of the running times of the long and the short run, divided by the line difference.
- A counter that ran less than 99.9 percent of the time gives the failure `multiplexed`. Its rate is still printed.
- The last column, `GB/s long`, is the total rate of the long run (field 7 of its repetition row).
- The exit status is 1 when any check failed: a missing run, a row without a numeric count, bad byte totals, a missing counter, a multiplexed counter, a missing idle control, or a file without pairs.
- The script reads its input only. It writes no file.
