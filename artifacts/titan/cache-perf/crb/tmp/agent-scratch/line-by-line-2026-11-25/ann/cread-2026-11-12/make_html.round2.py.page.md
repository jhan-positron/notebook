## Short version: purpose

`make_html.round2.py` builds the result page of the cread test. It reads the rates of the three read kernels from `cread.csv`, draws a bar chart of the best rate per buffer size and kernel, and writes the chart, two tables and fixed text to `cread-result.html`. Only the chart, the two tables and two load values are computed: every other sentence of the page is fixed text in the script.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB. It ran on 2026-11-13 [Ref1].
- **`read`, `asmread`, `cread`**: the names of the three read kernels in `cread.csv`. `read` is C code with 16 running sums (function `k_read`). `asmread` is a hand-written load-only loop (function `k_asmread`). `cread` is a load-only loop in C (function `k_cread`).
- **`run_cread.sh`**: the run script of the cread test. It starts 16 benchmark processes and writes `cread.csv`.
- **`cread.csv`**: the output file of `run_cread.sh`. For each process it holds one header line that starts with `-- round`, and then the lines that the benchmark prints.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process. The script and the generated page call it a repetition.
- **Interval row**: the line of `cread.csv` for one interval. Its fields are the kernel, the thread count, the buffer size in bytes, the repetition, the bytes, the time, the rate (field 7) and three thread rates.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = `2^10` bytes. GiB = `2^30` bytes.
- **Best, median, lowest**: the highest, the middle and the lowest value of the 12 rates of one buffer size and kernel. With 12 values the median is the mean of the two middle values.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Fixed text**: text that is written in the script as it is. The script does not compute it from `cread.csv`.
- **Generated page**: the file `cread-result.html` that this script writes.
- **SVG**: a picture format that is written as text. A browser draws it.
- **CSS**: the language that sets the look of an HTML page.

## Main flow

1. Read `cread.csv`. Keep the load value of each header line. For each interval row of `read`, `asmread` and `cread`, keep the buffer size, the kernel and the rate of field 7 ({L4-11}).
2. Group the rates by buffer size and kernel, and stop unless each of the 12 groups holds 12 rates ({L12-15}).
3. Build the bar chart: one group of bars per buffer size, one bar per kernel, with the best rate as the length of the bar ({L16-37}).
4. Build the legend, the rows of the table of the best, median and lowest rates, and the rows of the table of the two ratios ({L38-44}).
5. Put the chart, the tables and two load values into the fixed text of the page ({L45-107}).
6. Write `cread-result.html` and print `ok` with the length of the page ({L108-109}).

## Behavior a reader must know

- The input and the output are named without a folder ({L5}, {L108}). So the script must run in the folder that holds `cread.csv`, and it writes `cread-result.html` there. The test data hold a copy of the script beside `cread.csv` [Ref1].
- Where each number comes from: every rate is field 7 (`aggregate_GBps`) of an interval row of `cread.csv`. The buffer size comes from the header line before the row. The script does not use the `best` rows of the benchmark. It takes the maximum itself.
- How the rates are combined: for each buffer size and kernel, the 12 rates of 2 rounds, 2 CPUs and 3 repetitions go into one list ({L14}). The two rounds and the two CPUs are not kept apart. The chart shows the maximum of the list. The first table shows the maximum, the median and the minimum. The second table divides the maximum of `cread` by the maximum of `asmread`, and the median by the median.
- The column of loads per cycle is an estimate: the best rate divided by an assumed clock rate of 2.8 GHz and by 16 B ({L43}). The script reads no clock rate. The dashed line at 134.4 GB/s uses the same assumed value ({L24}).
- Fixed text: the short version, the findings, the limits and the conditions hold numbers and times that are typed into the script ({L57}, {L77-80}, {L84-88}, {L93-98}). With another `cread.csv` they would not change.
- The script stops with an error and writes no page when a group does not hold exactly 12 rates ({L15}).
- The generated page has its own list of references ({L102-105}). They are not the references of this explanation page.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/cread-20261113T060510Z`: the result folder of the cread test in the repo of the test data. It holds the files `cread.csv`, `probe.txt`, `cread-result.html` and `make_html.py`. Check of 2026-11-25: the command `cmp` finds `make_html.py` equal to `make_html.round2.py`.
