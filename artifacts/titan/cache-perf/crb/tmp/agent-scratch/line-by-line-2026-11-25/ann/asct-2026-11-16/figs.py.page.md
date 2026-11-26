## Short version: purpose

`figs.py` draws the ten figures of the report of the ASCT cross-check. Each function returns one picture as SVG text: eight of them place numbers of `facts.json` and `baseline.json` on axes with the helpers of `svgchart.py`, and two of them draw fixed texts. The file computes no result of its own, apart from label values (differences in percent, factors, a formula for instruction counts) and the bar ends of our own loops in figure 8, which are the middle between two totals.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **`facts.json`**: the output of `facts.py`. It holds the numbers that `facts.py` derived for the report: medians, ranges and counts per cell, and the verdicts.
- **`baseline.json`**: the output of `baseline.py`. It holds the older values of our own loops and the vendor runs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read loop, new read loop**: the names of the report for the old read kernel and the new read kernel. The values of the new read loop are those of `asmread`, where they exist.
- **ASCT loop**: the read loop of the ASCT benchmark binary. By the texts of this file it loads the first 8 bytes of each 64-byte line.
- **`read_1pl`**: a loop of our own benchmark of 2026-11-15 with one load per line.
- **Line**: one cache line of 64 bytes.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings. `facts.py` gives for each cell the median, the smallest and the largest value (the range) and the count.
- **Median**: the middle value of a sorted list of values.
- **Interval**: one timed measurement inside a process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Long-latency miss**: by the word list of the report, a load that had to wait for its line.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Fit**: the straight line that `facts.py` fits to the points of cycles per line against L2 refills per line. `a` is its height at 0 refills and `b` its rise per refill.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Window depth**: the number of 64-byte cache lines that the loads inside the out-of-order window of a core touch. `baseline.json` gives it as a range for each loop.
- **Vendor runs**: two complete ASCT runs that the chip vendor made on its own machines. The report calls the machines Arm reference machine A0 and A1.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Front end**: the command `asct run` of ASCT. It starts the benchmark binary with settings of its own.
- **Counter capture**: the counter code of ASCT, with the name dietperf. The probe build of the benchmark binary holds it.
- **SVG**: Scalable Vector Graphics, a text format for drawings. A web page can hold SVG text directly.
- **Dumbbell chart**: a chart with one row per pair of values. Two dots on a common value axis show the pair, and a line joins them.
- **Marker**: the round dot of one data point.
- **Tooltip**: a small text box that the page shows when the pointer rests on a mark.
- **Hit area**: an invisible shape over a mark. It carries the tooltip text.

## Main flow

1. The file has no top-level run. `report.py` calls one function per figure and places the returned picture into the page. The steps below follow the file order.
2. `fig_size`, figure 3: two panels, one per CPU. Each shows the median rate against the buffer size for the old read loop, the new read loop and the ASCT loop, and the vendor sweeps as thin grey lines ({L14-56}).
3. `fig_fall`, figure 4: a dumbbell chart of the rate at 1 MiB against the rate at 8 MiB, one row per loop and CPU and one row per vendor machine ({L59-81}).
4. `fig_pad`, figure 7: the same kind of chart for the ASCT loop with 0, 1, 2, 4 and 8 injected NOPs ({L84-106}).
5. `fig_cost`, figure 5: two panels with dots of cycles per line against L2 refills per line, and the fitted lines ({L109-148}).
6. `fig_prefetch`, figure 6: up to six small panels, one per counter, with the count per line against the buffer size for both CPUs ({L151-189}).
7. `fig_chip`, figure 8: horizontal bars of the total rate with all threads, for three of our loops, the ASCT loop and the two vendor machines ({L192-221}).
8. `fig_nops`, figure 9: the total at 64+56 and the sums per mesh against the count of injected NOPs, with bands for our two loops and the vendor lines ({L224-279}).
9. `fig_threads`, figure 10: a dumbbell chart of the rate of one thread per mesh, with 0 injected NOPs against the best count ({L282-296}).
10. `fig_loops`, figure 2, and `fig_path`, figure 1: two drawings from fixed texts, without data ({L299-348}).

## Behavior a reader must know

- Scales: the size axes of figures 3 and 6 are logarithmic. Every value axis is linear and starts at 0. The x axis of figure 9 has one place per count of injected NOPs at equal distances, so it is not to scale ({L230}).
- A dot or a bar end of the ASCT loop is the median of the processes of its cell. A range line runs from the smallest to the largest value of the cell.
- The ranges of our own loops come from `baseline.json`. In figure 3 they are the `lo` and `hi` values that `facts.py` copied, which are percentiles for most sizes. In figures 8 and 9 they are the smallest and the largest total of 2026-11-15.
- In figure 8 the bar of one of our own loops ends at the middle between its smallest and its largest total, not at a median ({L200-201}).
- In figure 3 a size without a value ends a line. For the new read loop a missing value of the assembly form is replaced by the value of the C form ({L32-40}).
- The tooltips of figure 3 call the count of every point `processes`. For the points that come from the first run of 2026-11-13 the count is a number of intervals ({L41}).
- Each small panel of figure 6 has its own y axis ({L177-184}). The test of {L181} can never pass, so the tick step is never below 0.1.
- The instruction counts in the labels of figure 7 are a fixed text and a formula, not counter values ({L92}, {L98}).
- Figure 10 is left out when no count of injected NOPs above 0 has the highest total ({L286-287}).
- The value `last` of {L261} and the list `series` of {L120} are set but not used.
