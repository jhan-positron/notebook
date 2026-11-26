## Short version: purpose

`report.py` builds the report page of the ASCT cross-check, `ASCT-cross-check.html`. It reads the numbers (`facts.json`), the older values (`baseline.json`) and the text blocks (`notes.json`), formats the numbers into ten tables, takes the ten figures from `figs.py` and puts everything into one HTML page with a style sheet and a small script for tooltips. It computes no result: every number of the tables 1 to 8 is copied from an input file and only rounded.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Facts file, `facts.json`**: the output of `facts.py`. It holds the numbers that `facts.py` derived for the report: medians, ranges and counts per cell, and the verdicts.
- **Baseline file, `baseline.json`**: the output of `baseline.py`. It holds the older values of our own loops and the vendor runs.
- **Notes file, `notes.json`**: the output of `notes.py` and `dyn_notes.py`. It holds the text blocks, the figure captions and the references of the page.
- **Text block**: one named entry of the notes file. It is a list of paragraphs and bullet lists that are HTML already.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **R-A3, P-A5**: a rule and a prediction of the decisions file. `facts.py` computes their verdicts.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read loop, new read loop**: the names of the report for the old read kernel and the new read kernel. The report takes the values of the new read loop from `asmread`, where they exist.
- **ASCT loop**: the read loop of the ASCT benchmark binary.
- **`read_nop96`, `read_nop128`**: two loops of our own benchmark of 2026-11-15, load-only loops with 96 and with 128 `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings. The facts file gives for each cell the median, the smallest and the largest value (the range) and the count `n`.
- **Median**: the middle value of a sorted list of values.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **Lower bound of a total**: all bytes of a process divided by the time of its slowest thread. The facts file holds it as `floor`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Line**: one cache line of 64 bytes.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part C, part NC**: two parts of the one-core runs. C: counters. NC: injected NOPs with counters.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Event set**: a named list of counter events that one process counts together.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Long miss, long-latency miss**: by the word list of the report, a load that had to wait for its line.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh counter**: a hardware counter of the mesh, the network on the chip that links the cores, the SLC and the memory ports. Reading it needs root.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Home node, gateway**: two parts of the mesh. A home node receives the memory requests of the cores. The gateway links the two meshes.
- **Flit**: one transfer unit on a link or a port of the mesh.
- **Busy level**: a value from 0 to 3 that a response message of the mesh carries. A higher value says that the sender is more busy.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Tag**: the name of one process of the mesh-counter runs.
- **Vendor runs, A0 and A1**: two complete ASCT runs that the chip vendor made on its own machines. The report calls the machines Arm reference machine A0 and A1.
- **Interval**: one timed measurement inside a process.
- **CSS**: the language of the style sheet of a web page. It sets the look of the elements.
- **Tooltip**: a small text box that the page shows when the pointer rests on a mark or when the mark has the keyboard focus.
- **Hit area**: an invisible shape over a chart mark. It carries the tooltip text in its attribute `data-tip`.
- **Folding block**: a block of the page that shows one line until the reader opens it.

## Main flow

1. Read the facts file, the baseline file and the notes file from the arguments 1 to 3 ({L12-14}).
2. Define the style sheet and the tooltip script as two texts ({L17-65}).
3. Define the table functions. Each one formats numbers of the facts file, and for some columns of the baseline file or the notes file, into one HTML table ({L82-328}).
4. Build the page from top to bottom: the main heading, the short version, the folded word list, then the sections 1 to 7 and the references. Each line adds a heading, text blocks of the notes file, figures of `figs.py` and tables ({L344-375}).
5. Wrap the pieces into one HTML page, write it to the file of argument 4 and print its size ({L377-381}).

## Behavior a reader must know

- The script computes no result. The only arithmetic is rounding, the sum of the two meshes for a mesh counter ({L230}, {L254-260}) and the smallest and the largest total of the counted processes ({L190}).
- Where a number of a table comes from: tables 1 to 8 read the facts file. Table 1 also reads the vendor sweep, table 6 the older layout totals and table 8 the vendor table, all from the baseline file. Table 4 also reads `peer_counters` of the notes file.
- A value that is missing gives an empty cell. A missing cell or tag never stops the script, but a missing key that a line reads without a test does, for example a caption of the notes file in {L349}.
- Tables 9 and 10 need mesh counters. With the notes file of `dyn_notes.py` both functions return the paragraph `Insufficient data` in place of the table ({L216}, {L266}).
- Table 1 calls every value a median of the processes ({L85}). For the old and the new read loop the facts file holds a median of row medians from the baseline file, and the range in the cell tooltip is a range of percentiles. At 1 GiB on CPU 2 the value of these two loops is a median of timed intervals of the first run. The columns `A0` and `A1` hold one value of the vendor sweep per size.
- The three rates in the header of table 9 are fixed numbers of {L223}, not values of an input file.
- The description text names a script `check_notes.py`. This folder holds no such file ({L5}).
- The imports of five colors in {L10}, the function `bullets` and the style classes `key` and `v` are not used.
- The page is light theme only. It needs no other file: the style sheet, the script and all pictures are inside the page.
