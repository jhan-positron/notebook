## Short version: purpose

`analyze_writepath.py` analyses the file `writepath.csv` that part 5 of the script `run_sudo.sh` writes. For each case and each event it prints the number of events per cache line, per second and per cycle, computed from the difference between a long run and a short run. It also checks the data and ends with exit status 1 when a check fails.

## Words used here

- **Mesh**: the network inside one half of the chip. It connects the cores, the last cache level and the memory, and it has counters of its own.
- **Crosspoint**: a junction of the mesh. Part 5 counts events at the crosspoint with the node id `0x98`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **Event name**: the name that `perf` prints for an event. `arm_cmn_0/NAME/` is an event of mesh 0, `arm_cmn_1/NAME/` one of mesh 1, and `armv8_pmuv3_0/NAME/` one of the core.
- **Cycle counter**: an event that counts clock cycles: `dtc_cycles` for a mesh and `cycles` for the core.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. Its row of a repetition holds the bytes that all threads moved (`total_bytes`) and the total rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Case, tag**: one setting of `bandwidth` in part 5 of `run_sudo.sh`: a kernel, a buffer size, a thread count and a CPU list. The tag is its short name, for example `w8M-c2`.
- **Event set, label**: the events that one run of `perf stat` counts. The label is the short name of the set, for example `xpdat` or `core1`.
- **Short run, long run**: two runs of the same case under the same event set. The timed interval of `bandwidth` lasts at least 200 ms in the short run and at least 2000 ms in the long run.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **Block**: the rows of one run in the input file: a title line that starts with `--`, then the output of `bandwidth`, then the count rows of `perf stat`.
- **Line**: a cache line, 64 bytes.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB**: 1e9 bytes.

## Main flow

1. Read the input file line by line and split it into blocks: one block per measured run and one block per idle control ({L10-28}).
2. Compute the idle rate of each event in events per second ({L29-33}).
3. Pair the short and the long block of each case and event set ({L34-36}).
4. For each pair: check the data, compute the difference in cache lines, and compute for each event the rate per line, per second and per cycle with the background subtracted. The function `short` makes the event names shorter for the output ({L41-62}).
5. Print the number of failed checks and their texts, and end with exit status 1 when a check failed ({L63-66}).

## Behavior a reader must know

- Rate per line of an event: the count of the long run minus the count of the short run minus the background, divided by the line difference.
- Line difference: `total_bytes` of the long run minus `total_bytes` of the short run, divided by 64. `total_bytes` is field 5 of the row of repetition 0 of `bandwidth`. It covers the timed interval only, summed over all threads of the case.
- The core event sets of part 5 count on CPU 2 only (`-C 2` in `run_sudo.sh`). So in a case with 2 or 4 threads the rate per line of a core event divides the events of one CPU by the lines of all threads.
- Rate per second: the same count difference divided by the difference of the running times of the two counters.
- Rate per cycle: the same count difference divided by the value `cyc` of a cycle counter of the same set. `cyc` is the count of that counter in the long run minus its count in the short run minus its background. A set with the cycle counters of both meshes uses the counter of mesh 0 for all its events.
- The background is subtracted from a cycle counter too ({L54-58}). So when a cycle counter counts at the same rate in the idle control as in a run, the divisor is near 0. The column `per cycle` is then not a rate per cycle, and the row of the cycle counter itself shows that small remainder and not its count. By the report of the project this happened in the run of part 5: the cycle counter of the mesh counted 2.0e9 cycles per second also in the idle control, and the script left about 6500 per second of it. The report calls the column `per cycle` of this script not usable [Ref1].
- Background: the idle rate of the event (count of the idle control divided by its running time) times the difference of the running times of the long and the short run.
- A count row is read from both ends: the count is the first field, the running time in nanoseconds the fourth field from the end, and the percent value the third field from the end. The fields from the third one up to the fifth one from the end are the event name, which can hold commas.
- A counter that ran less than 99.9 percent of the time gives the failure `multiplexed`. Its rates are still printed.
- The exit status is 1 when any check failed: a missing run, a row without a numeric count, bad byte totals, an event that is missing in the short run, a multiplexed counter, a missing idle control, or a file without pairs.
- The script reads its input only. It writes no file.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/crb-memory-hierarchy.html`: the report page of the first tests. Its paragraph that starts with "Corrected on 2026-11-11" is about the mesh cycle counter (event `dtc_cycles`) in the file `writepath.csv` of the run `sudo-20261102T211150Z`. By that paragraph each count divided by its counting time gives 1.9995 to 2.0000 GHz, with the machine idle and with busy cores. The earlier value of about 6,500 per second was what remained after `analyze_writepath.py` subtracted the count of the idle control. The script still does this, so its per-cycle column is not usable.
