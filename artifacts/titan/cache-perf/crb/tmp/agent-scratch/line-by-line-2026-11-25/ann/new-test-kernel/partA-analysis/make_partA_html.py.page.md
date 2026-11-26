## Short version: purpose

`make_partA_html.py` builds the result page of Part A, the screening part of the test plan of 2026-11-13, as one HTML file, from the json file that `analyze_partA.py` writes. It reads no measurement file: it prints the values of the json file as sentences, tables and charts, and it prints the words `Insufficient data` where a step, a file or a needed measurement is missing. The sentences that read the data are built from the values, and the fixed texts are definitions, quotations of the plan, captions and references.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan and how to analyse Part A.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The names B4, B5, B7, B8, B9, B10 and D2 are steps of the later parts of the plan.
- **Parts B, C and D of the plan**: the later parts of the plan. Part B uses a changed copy of the benchmark. Part C reads the counters of the cores. Part D needs root. These are not the parts of the later rerun.
- **Json file**: the file `partA-summary.json` that `analyze_partA.py` writes. It holds every measured value that the result page prints.
- **Result page**: the HTML file that this script writes, `partA-result.html` unless the caller names another.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`.
- **Launch, tag**: a launch is one start of a process by the run script `run_partA.sh`. The tag is the short name of the launch, for example `read_old-r1`.
- **Busiest processes, CPU use (`pcpu`)**: the 5 processes that the run script lists in the file `launches.txt` before each launch, each with the value of the column `pcpu` of the tool `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. So it is an average over the life of the process, not the CPU use at the launch.
- **Block**: the lines of one process in a csv file of a result folder.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither. The page shows them only when the json file says that they are usable.
- **Fastest half**: the half of the threads of one repetition that has the highest rates.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that the analysis script had to fix where the plan and the handoff note give none.
- **Range**: in the json file, four values of a list of numbers: the count, the lowest value, the median and the highest value.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Observed in screening**: the words with which the page introduces the results of the steps A1 to A6. No control ran with such a result.
- **Insufficient data**: the words that the page prints where a value or a measurement is missing, with the measurement that would give it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the counter hardware of a core.
- **SVE**: the scalable vector instruction set of Arm.
- **HTML, CSS, SVG**: the three formats of the page. HTML holds the text and the tables. CSS, the style sheet, sets fonts, colours and spacing. SVG holds the charts as drawing commands.
- **Class**: a name on an HTML element that selects its style, for example `take` for a highlighted statement and `miss` for a notice of missing data.
- **Hover text**: a text that a browser shows when the pointer rests on a mark of a chart.
- **Drawing unit**: the unit of the positions and sizes inside an SVG drawing. It is 1 pixel when the chart has its full width.
- **Q2a, H7a**: names of the plan. Q2a is the question why the old read kernel has a higher total than the new one with 120 threads. H7a is the hypothesis that the stop method and the short interval make a part of that difference.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the options `-o` and `--banner` and the path of the json file, and loads the json file ({L1340-1348}).
2. `build` opens the page: the head with the style sheet `CSS`, the banner when one is given, and the main heading ({L1284-1293}).
3. It adds the short version, which `short_version` builds as three sentences from the values, then the two questions and the list of the result folders ({L1294-1301}).
4. It adds the list of words from `WORDS` ({L1302}).
5. It adds the table of the seven steps: two columns that are quoted from the plan (`LOOKS`, `PLAN`), and one column that `points_to` builds from the data ({L1303-1309}).
6. It adds ten sections, each built by its own function: the system load, the blocks that are not used, the distribution of q, the passes per thread, the steps A1 and A2, and the steps A3 to A7 ({L1310}). The sections draw their charts with `strip_chart`, `mesh_pairs_chart`, `cpu_panels`, `a4_chart` and `a5_chart`, and they print numbers with `fx`.
7. It adds the limits of the page and the references ({L1311-1336}).
8. `main` writes the page to the output file and prints its path ({L1349-1351}).

## Behavior a reader must know

- The script reads one json file and writes one HTML file. It replaces an older file of the same name. It reads no result folder and runs nothing.
- All measured values come from the json file. The script itself derives simple values from them, for example differences, percentages, counts, lowest and highest values, the median of q per thread count ({L681}) and, for the panels per CPU, the median of the rates of each thread over the repetitions ({L413}).
- A number is printed by `fx` with 2 decimals unless the caller asks for another count. A value with a 5 as its third and last decimal keeps 3 decimals. Every other half is rounded away from zero ({L42-52}).
- The page marks its main statements about the steps A1 to A6 with the words `Observed in screening`: they start with these words or stand in a list under them. Not every sentence with a value carries them, for example the sentences on the load, on the passes, on the check of the level limits and on step A7. The generated sentences do not use the words `rejected` or `confirmed`. The test file checks on its test pages that these two words do not occur, and that the words `observed in screening` occur at least once.
- Where data is missing, the page does not stay silent: the function `missing` prints `Insufficient data` with the measurement that is missing ({L74-75}). A single missing value in a table cell is printed as a hyphen ({L62}).
- The pattern labels split and uniform appear only when the json file gives `labels_usable` as true. If not, the page gives q without labels, and it says `Insufficient data` for the thread counts of step B8 ({L742-746}).
- The level labels of step A5 appear only for a CPU whose labels the json file marks as usable ({L961-966}).
- Axes: the charts of q run from 0 to 1. The chart of the two meshes and the panels per CPU start at 0 GB/s. The chart of step A5 and the chart of step A6 do not start at 0, and the caption or the axis title says so ({L952}, {L1011}).
- In a chart of `strip_chart` a value outside the axis is drawn at the end of the axis ({L93}).
- Some numbers in the fixed texts are not read from the json file, for example the interval of 6000 ms in the row of step A4 ({L231}), the 3 intervals per process in the caption of step A6 ({L1012}) and the 0.3 s in the axis title of step A5 ({L891}).
- The sentence that no total of A1 meets rule 7 is printed whenever at least one repetition of A1 has fewer than 50 passes, also when others pass the check ({L255-258}).
- The page is one file: it loads no script, font or image, and it has a light colour scheme only.
- The exit status is 0 after a run that worked. A json file that cannot be read ends the program with a Python error.
- The result folder `partA-20261113T205055Z` holds a copy of this file with the same sha256, beside the page `partA-result.html` [Ref1].

## References

- [Ref1] the result folder `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the files `make_partA_html.py` (sha256 `1b9dc00f8e3aeaf1551f3c59eeb2e0cd713c6a2a8852a85235401c785a3d8b12`, as the file in the code folder) and `partA-result.html`.
