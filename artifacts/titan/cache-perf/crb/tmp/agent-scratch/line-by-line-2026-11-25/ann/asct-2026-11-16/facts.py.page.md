## Short version: purpose

`facts.py` turns the raw results of the ASCT cross-check (`asct.json`) and the older values of our own loops (`baseline.json`) into the numbers of the report. It reduces each cell to a median, a range and a count, computes ratios and a straight-line fit, and applies the predictions and rules of the decisions file as `True` or `False` verdicts. It writes one JSON file, which the project keeps as `facts.json` and which the text and page scripts read.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **P-A1, P-A4, P-A5, P-B1, P-B2, P-B3, R-A3, D-A2**: names of the decisions file. P is a prediction with a pass rule, R is a rule and D is an item that is only described.
- **Verdict**: the result of the test of one prediction or rule. `True` means that the prediction holds or that the rule finds a difference.
- **ASCT binary**: the benchmark program of ASCT, `loaded-latency-asct-sve.bin`. One start is one process.
- **ASCT loop**: the read loop of the ASCT binary. By the decisions file it loads 8 bytes from each 64-byte line.
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings, for example one CPU and one buffer size. By the decisions file a cell value is the median of its processes, and the range is the smallest to the largest value.
- **Median**: the middle value of a sorted list of values.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Line**: one cache line of 64 bytes.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase. `analyze.py` computes it.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Interval**: one timed measurement inside a process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Event set**: a named list of counter events that one process counts together.
- **Probe binary**: the ASCT binary built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT. The processes with counters use it.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB. The processes without counters use it.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Tag**: the name of one process of the mesh-counter runs.
- **Counting window**: one run of `perf stat -a` for the command `sleep` in the script `run_mesh.sh`.
- **DTC node**: by the Linux documentation the main controller of the counters of a mesh. It holds the global counters, and the cycle counter belongs to it [Ref3].
- **Vendor runs**: two complete ASCT runs that the chip vendor made on its own machines. Their console outputs and result archives lie in the welcome kit of Arm.
- **`launches.txt`**: a file that each run script writes into its result folder. It gets one `launch` line before each process and one `rc` line after it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Read `asct.json` from argument 1 and `baseline.json` from argument 2 ({L39-42}).
2. One core, for each of the CPUs 2 and 41 and each of the 16 sizes: reduce the ASCT processes of part U to a median, a range and a count. Put the older values of our three loops from `baseline.json` beside them. Take the median of each counter of part C ({L45-65}).
3. Per CPU: the ratio of the rate at 8 MiB to the rate at 1 MiB and the verdict of P-A1, the straight-line fit of cycles per line against L2 refills per line (the helper `linfit` fits by least squares), the clock rate that follows from the counters, the distance between counted and uncounted rates, and rule R-A3 for each prefetch counter ({L66-96}).
4. Injected NOPs on one core: the rates of part N with the verdict of P-A4, the counters of part NC with the verdict of P-A5, and the two lists of rule R-A3 over both CPUs ({L97-136}).
5. CPU 41 against CPU 2 per size, and the ratio of 8 MiB to 1 MiB of the vendor runs ({L137-143}).
6. Whole chip: merge all many-core folders. Reduce each cell to medians and ranges (helper `cell`). Compute the verdicts of P-B1, P-B2 and P-B3, the traffic types and the counters per mesh ({L145-213}).
7. Mesh counters: events per second and per line for each tag ({L215-233}).
8. Write the output file and print a short view to the console ({L234-251}).

## Behavior a reader must know

- Units: every rate is in GB/s with GB = 1e9 bytes. Every counter value of the cores is a count per 64-byte line. A mesh counter has two values, events per second and a count per line ({L226-228}). `ghz` is in GHz. The fields that end in `pct` are in percent.
- How values are combined: a cell is reduced by `stat` to the median, the smallest value, the largest value and the count of its processes. A counter of a one-core cell is the median over the processes that counted it. For a counted whole-chip case each process first gives the median over the threads of a mesh, and the value is the median of these thread medians over the event sets ({L199-205}).
- The verdict rules, as the code tests them:
  - P-A1 ({L70}): the ASCT rate at 8 MiB divided by the rate at 1 MiB is below 0.90, per CPU.
  - R-A3 ({L92-94}, {L130}): the value at 8 MiB lies outside the range of the values at 6 MiB and 12 MiB, after the range was widened at each end by 10 % of the mean of the two. A counter is different only when this holds on both CPUs.
  - P-A4 ({L104-109}): for each count of injected NOPs whose rate at 1 MiB is below 60 GB/s, the rate at 8 MiB is within 3 % of the rate at 1 MiB.
  - P-A5 ({L124-128}): `l2d_cache_lmiss_rd` per line at 8 MiB with 2 injected NOPs is below 0.8 times the value with 0 injected NOPs.
  - P-B1 ({L185-186}): the median total at 64+56 with 0 injected NOPs is below 334 GB/s. At 459 GB/s or more the prediction fails.
  - P-B2 ({L184}, {L187}): at least one count of injected NOPs from 1 to 40 has a median total of 459 GB/s or more.
  - P-B3 ({L192-193}): the median total is 330.6 to 368.55 GB/s for 64+0 and 302.1 to 337.785 GB/s for 0+56.
- The verdicts use the total that ASCT prints. The lower bound `floor` is computed beside it but takes part in no verdict.
- A verdict never stops the script. It is stored as `True`, `False` or `None`. `None` means that the data for the test is missing. For P-A4 it also means that no count of injected NOPs has a rate below 60 GB/s at 1 MiB ({L108}). Two verdicts have no `None`: P-B2 is `False` without data ({L187}), and P-A5 has no entry for a CPU without data ({L126}).
- Which verdicts the report uses: the scripts `report.py` and `dyn_notes.py` read the verdicts of rule R-A3 (`different`, `RA3_different`, `RA3_counted`). No other script of this folder reads `PA1`, `PA4`, `PB1`, `PB1_fail_hard`, `PB2`, `PB3` or a field `holds`. This script prints the verdicts of P-A1, P-A4, P-B1, P-B2 and P-B3 to the console ({L242-248}). The headings of the report that say that a prediction holds are fixed text of `dyn_notes.py`.
- The description text says that the report generator only formats what this file computes ({L3}). That is not exact: `dyn_notes.py` and `figs.py` compute further values from the output, such as percentages, factors and quotients.
- The ranges of our older loops are not ranges of processes. For the values from `final8.json` they are percentiles of rows. For 1 GiB on CPU 2 they are the smallest and the largest interval of the first run, and `n` counts intervals ({L55}, {L60}).
- Only the first one-core folder with part U is used, and the first folder with part NC. All many-core folders are merged ({L45-46}, {L149-155}).
- Several lines have no test for a missing value: {L68-69}, {L77}, {L138}, {L143}. A missing value stops the script there with an error, and no output file is written.
- The scripts `notes.py` and `report.py` of the same folder read the output file. They pass its content to `dyn_notes.py` and `figs.py`.

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`: the sections "Predictions and rules (fixed now)", "Readings fixed now", "Added 2026-11-16 20:45 UTC" (P-A4), "Added 2026-11-16 23:23 UTC" (P-A5) and "Record of 2026-11-16 23:50 UTC" (the defect of `run_chip.sh` and the second many-core folder).
- [Ref2] `asct.json` and `facts.json` in the folder `asct-2026-11-16`: the list `mesh` of the first file has no entry, and the dictionary `mesh` of the second file is empty.
- [Ref3] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": the cycle counter of the DTC node.
