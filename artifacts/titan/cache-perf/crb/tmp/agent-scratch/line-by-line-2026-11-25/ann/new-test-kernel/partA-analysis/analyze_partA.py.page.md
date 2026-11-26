## Short version: purpose

`analyze_partA.py` reads the result folders that `run_partA.sh` wrote and computes the values of Part A, the screening part of the test plan of 2026-11-13. For each repetition it gives the passes per thread, the thread rates of each mesh and the ratio q of slow to fast threads, and for each step a summary. It writes all of this to one json file, from which `make_partA_html.py` builds the result page.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan. Its section "How to analyse Part A" gives the rules that this script follows.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The steps A1 to A6 each have a csv file. Step A7 only reads system files.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`. The option `--reps` gives the number of repetitions per kernel, and `--min-ms` gives the shortest length of each.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **Launch, tag**: a launch is one start of a process by the run script. The tag is the short name of the launch, for example `read_old-r1`.
- **Busiest processes, CPU use (`pcpu`)**: the 5 processes that the run script lists in the file `launches.txt` before each launch, each with the value of the column `pcpu` of the tool `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. So it is an average over the life of the process, not the CPU use at the launch.
- **Block**: the lines of one process in a csv file: the header line of the run script and the output of the benchmark.
- **Header line**: the line that the run script writes before the output of a process. It starts with `-- step` and holds the tag, the binary, the waited seconds, the load, the logins, the UTC time and the options.
- **Data line**: an output line of the benchmark for one repetition, with 10 fields. The fields used here are the kernel, the threads, the bytes per thread, the repetition, `total_bytes`, `elapsed_s` and `aggregate_GBps`.
- **Thread line**: an output line of the benchmark for one thread and one repetition, printed with `--per-thread`. Its 6 fields are the word `thread`, the thread index, the CPU, the kernel, the repetition and the thread rate.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither.
- **Fastest half**: the `n//2` threads with the highest rates of one repetition with n threads.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that this script had to fix where the plan and the handoff note give none. The header text of the file lists them.
- **Json file**: the output of this script, `partA-summary.json` unless the caller names another file. The format json stores nested lists and dictionaries as text.
- **Range**: in the json file, four values of a list of numbers: the count, the lowest value, the median and the highest value.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the counter hardware of a core. Linux shows it as a counter device with a type number.
- **SVE**: the scalable vector instruction set of Arm.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the arguments: one or more result folders and the optional output path `--out` ({L702-710}).
2. `analyse` reads each folder in time order ({L633-642}). `parse_env` reads `env.txt`, the files of step A7 and `stderr.txt`. `parse_launches` reads `launches.txt`. `parse_csv` splits each csv file into blocks. `finish_block` turns each data line into a repetition with its passes per thread, its thread rates per mesh, q and the fastest half, and it marks a block that is not complete.
3. Of each step and tag the last complete block is used. The other blocks go to the list `not_used` ({L643-656}).
4. q is collected over all repetitions with at least 2 threads. `two_groups` tests whether q falls into two groups. Only then do the repetitions get a pattern label ({L657-668}).
5. The steps are summarised ({L669-698}): A1 and A2 per kernel (`step_a12`) and against each other (`compare_a1_a2`), A3 (`step_a3`), A4 with its bracket (`step_a4`), A5 (`step_a5`), A6 (`step_a6`), the check of the level limits (`level_check`), and the load readings (`load_check`, `load_summary`).
6. `main` writes the summary to the json file and prints a few lines about it ({L711-723}).

## Behavior a reader must know

- The script measures nothing. It reads the files of the result folders and writes one json file. It replaces an older file of the same name.
- Where each number comes from:
  - The total of a repetition is field 7, `aggregate_GBps`, of its data line in the csv file of the step. The script does not compute it again.
  - The passes per thread are field 5, `total_bytes`, divided by field 2, `threads`, times field 3, `bytes_per_thread`. For a copy kernel the result is halved. This is an average over the threads.
  - A thread rate is field 6 of a thread line, and its CPU is field 3. A CPU below 64 is on mesh 0.
  - The sum and the median per mesh are the sum and the median of these thread rates. The sum of thread rates is not the total.
  - q is the thread rate at the 10th percentile divided by the one at the 90th percentile, by the nearest-rank rule.
  - The rates of the steps A5 and A6 are the totals of their data lines. With one thread the total is the rate of the thread.
  - The interval length and the page setting come from the comment line of the benchmark that starts with `# bandwidth:`.
  - The load readings come from the header lines and from `launches.txt`. The run script wrote both directly before each launch.
- Values are combined as ranges and medians. A change between two cases is always a difference of two medians.
- One test decides for all of Part A whether the pattern labels are used ({L664}). When it fails, every label stays empty, step A4 gets no bracket, and the page gives q without labels.
- For the data of 2026-11-13 the stored json file gives `two_groups` false and `labels_usable` false, over 152 q values [Ref1].
- A block is used only when it is complete: no `killed` or `failed` line, the number of repetitions that `--reps` asked for, a best line per kernel, all thread lines, and no line that was not understood ({L204-218}).
- The best line of the benchmark is not used as a value. It only shows that a kernel ran to its end.
- A missing file is not an error. The part of the summary that needs it stays empty, and the step is listed under `steps_missing`.
- The exit status is 0 after a run that worked, and 2 when no folder is given or a path is not a folder.
- The four limits (0.65 and 0.85 for q, 69 and 70.5 GB/s for the level) are provisional. The json file records them under `limits`.
- The comment of {L460} says that a change over a missing thread count is not a change between neighbouring counts. The code only records the missing counts and can still give such a change as the bracket ({L462}).
- The result folder `partA-20261113T205055Z` holds a copy of this file with the same sha256, beside the json file `partA-summary.json` [Ref1].

## References

- [Ref1] the result folder `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the files `analyze_partA.py` (sha256 `d82f50aeb3b9488d2a919d05205c81fcb7abca00a099119b2e1ac27fd2fcb5e0`, as the file in the code folder) and `partA-summary.json` (key `q.decision`: `n` 152, `two_groups` false, `labels_usable` false).
