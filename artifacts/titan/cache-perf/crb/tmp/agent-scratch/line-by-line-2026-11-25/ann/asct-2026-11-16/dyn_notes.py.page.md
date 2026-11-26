## Short version: purpose

`dyn_notes.py` holds the text of the report of the ASCT cross-check that was written after the runs: the method, the result texts for both questions, the comparison with the vendor runs, the run record and the short version. The script `notes.py` calls its function `fill`, which writes each text block into a dictionary and fills numbers of `facts.json` and `baseline.json` into the sentences. The conclusions, most verdict words and a number of values are fixed text, so they do not follow the data files.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Report page**: the file `ASCT-cross-check.html`, the result page of the cross-check. The script `report.py` of the same folder builds it.
- **Text block**: one named piece of the text of the report page, in HTML. `N` holds the blocks by name.
- **Facts file**: the file `facts.json`, the output of `facts.py`. It holds the numbers that `facts.py` derived for the report: medians, ranges and counts per cell, and the verdicts.
- **Baseline file**: the file `baseline.json`, the output of `baseline.py`. It holds the older values of our own loops and the vendor runs.
- **Fixed text**: text that stands in the source line as it is. The code fills no value into it. A number or a verdict in a fixed text does not change when the data files change.
- **Filled in**: a value that the code takes from a data file and formats into a sentence.
- **Reference N of the report**: entry N of the reference list of the report page, which `notes.py` holds. The helper `ref` writes its citation mark. These numbers are not the references of this page.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **P-A1, P-A4, P-A5, P-B1, P-B2, P-B3, R-A3, D-A2**: names of the decisions file. P is a prediction with a pass rule, R is a rule and D is an item that is only described. `facts.py` computes the verdicts.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Read loop**: the word of the report page for a read kernel. Old read and new read are the old and the new read kernel. The report takes the values of the new read loop from `asmread`, where they exist.
- **ASCT loop, ASCT read**: the read loop of the ASCT benchmark binary, the function `my_read_no_nops_rep_64b`. With injected NOPs it is the function `my_read`.
- **`read_1pl`, `read_nop64`**: two loops of our own benchmark of 2026-11-15: one load per line, and a load-only loop with 64 `nop` instructions.
- **Front end**: the command `asct run` of ASCT. It starts the benchmark binary with settings of its own.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Probe build**: the same benchmark program, built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT, which has the name dietperf.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Preparation folder**: the result folder of the script `prep.sh`. It holds the machine record `env.txt`, the checksum list `sha.txt`, the event list `resolve.txt` and the listings.
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings. The facts file gives for each cell the median, the smallest and the largest value (the range) and the count.
- **Median**: the middle value of a sorted list of values.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **Lower bound of a total**: all bytes of a process divided by the time of its slowest thread. The facts file holds it as `floor`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Line**: one cache line of 64 bytes.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Event set**: a named list of counter events that one process counts together.
- **L1, L2**: the two private caches of a core.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`. The report names the count per line r.
- **Long-latency miss**: by the word list of the report, a load that had to wait for its line.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Window**: by the word list of the report, the instructions that a core holds in flight at one moment.
- **Fit**: the straight line that `facts.py` fits to the points of cycles per line against L2 refills per line. `a` is its height at 0 refills and `b` its rise per refill.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh counter**: a hardware counter of the mesh, the network on the chip that links the cores, the SLC and the memory ports. Reading it needs root.
- **Busy level**: a value from 0 to 3 that a response message of the mesh carries. A higher value says that the sender is more busy.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119. 64+0, 0+56 and 56+56 name other layouts in the same way.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Vendor runs, A0 and A1**: two complete ASCT runs that the chip vendor made on its own machines. The report calls the machines Arm reference machine A0 and A1.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM, a plug-in memory board.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **`launches.txt`**: a file that each run script writes into its result folder. It gets one `launch` line before each process and one `rc` line after it.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `notes.py` calls `fill` with its dictionary `N`, the facts file, the baseline file and its helpers `p`, `ul` and `ref` ({L288}).
2. `fill` reads the machine-code listings of the ASCT binaries and the checksum list (`loop_facts`) and builds three helper texts: two from them, and one from the counted instructions per line of the facts file ({L290-295}).
3. `static_blocks` writes the blocks `how`, `loops` and `capture`: how ASCT was used, the three read loops, and what ASCT can capture ({L14-90}).
4. `q1_blocks` writes the first blocks of question 1: the one-core rates, the cost per line and the prefetchers, with the captions of the figures 3 to 6 ({L159-285}).
5. `q1_more` writes the blocks on the injected NOPs, on the SLC and the mesh, and the verdict for question 1. It stores the counter values of our own loops (`peer_counters`, read from `final8.json`) for table 4, and it sets the lists of mesh tags to empty lists ({L309-399}).
6. `q2_blocks` writes the blocks of question 2, the whole chip, with the captions of the figures 8 to 10 ({L402-508}).
7. `tail_blocks` writes the comparison with the vendor runs, the run record with the deviations, the open items, the subtitle and the short version ({L511-611}).
8. `fill` removes the three helper texts from `N` ({L301-302}).

## Behavior a reader must know

- A row that starts with `Text` or `Item`, and a row that continues one of them, gives what the text of the report says. It is not a finding of this page, and no row was compared with the result files.
- The file measures nothing. Its arithmetic is small: sums, differences, ratios, percentages, and the smallest and the largest value of a list. Each row below says for a filled-in number which field it comes from.
- The description text says that every number comes from the facts file or the baseline file ({L2}). That is not so. `peer_counters` reads `final8.json` ({L104}), and many values are fixed text.
- The headings that say that a prediction holds are fixed text. The lines do not read the verdict fields of the facts file: P-A1 ({L204}), P-A5 ({L333}), P-A4 ({L342}), P-B1 ({L437}), P-B2 ({L438}) and P-B3 ({L457}). Only the heading for rule R-A3 follows the facts file ({L266}).
- Fixed values about results stand, among other places, in {L191}, {L200}, {L202}, {L320}, {L352}, {L370}, {L376}, {L390-393}, {L396}, {L481}, {L489} and {L599}. Fixed times and counts of the run record stand in {L561-589}.
- Six texts are chosen by a test of the data: {L81}, {L198-199}, {L257}, {L266-269}, {L291-293} and {L320-321}. One more piece of text appears only when its value exists ({L245}).
- The sentence of {L257} says that the counters for prefetch instructions are 0 at every size. The test of {L251} reads the values at 6, 8 and 12 MiB only.
- The number that {L572} calls rows that fail is the length of three lists of problem texts. These lists hold every kind of problem that `analyze.py` found.
- The paths of {L98-99} and {L118} fit the first place of the file on the agent server. In the code repo they lead nowhere, and the machine-code listings are not in the repo [Ref1].
- Most lines read a field without a test. A missing field stops the script with an error, and `notes.py` then writes no notes file.
- {L367} sets the lists of mesh tags to empty lists. So the report shows the two texts `Insufficient data` in place of the tables 9 and 10.
- The function `pct` ({L151}) and the name `pf` ({L248}) are not used.

## References

- [Ref1] `README.md` of the repo `arm-crb`, section "What a reader must know": the point "Fixed paths", and the list "Left out on purpose", which names the six machine-code listings of the ASCT binary in `asct-prep-20261116T231215Z`.
