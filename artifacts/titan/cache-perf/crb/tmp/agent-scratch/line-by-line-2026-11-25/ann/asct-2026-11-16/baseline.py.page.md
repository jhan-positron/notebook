## Short version: purpose

`baseline.py` collects the older numbers with which the report of the ASCT cross-check compares the ASCT results. It reads the result file of the 8 MiB work, the first run of the new kernels and two ASCT runs of the chip vendor, and it holds the whole-chip values of the facts sheet of 2026-11-15 as fixed numbers. It writes all of them to one JSON file, which the other scripts of the report read.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **8 MiB work**: the tests of 2026-11-15 on the small gain of the new read kernel at a buffer of 8 MiB. Its analysis wrote the file `final8.json`.
- **Step**: a named group of runs of the 8 MiB work, such as `S2` or `ZS`.
- **Cell**: all rows of one kernel, one CPU and one buffer size.
- **Facts sheet of 2026-11-15**: the file `FINDINGS.md` in the folder `w120-2026-11-15`. It holds the numbers of the whole-chip work of that day.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Window depth**: the number of 64-byte cache lines that the loads inside the out-of-order window of a core touch. The facts sheet gives it as a range for each loop.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **Median**: the middle value of a sorted list of values.
- **`p5`, `p95`**: two fields of a row of `final8.json`. By their names they are the 5th and the 95th percentile of the values of the row.
- **Vendor runs**: two complete ASCT runs that the chip vendor made on its own machines. Their console outputs and result archives lie in the welcome kit of Arm.
- **Injected NOPs**: an option of the ASCT binary. For N above 0 the binary runs an empty loop of N rounds after each load.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Home node, gateway**: two parts of the mesh. A home node receives the memory requests of the cores. The gateway links the two meshes.
- **Busy level**: a value from 0 to 3 that a response message of the mesh carries. A higher value says that the sender is more busy.

## Main flow

1. Read `final8.json`. Group the rows of its block `size_curve` by kernel, CPU and buffer size. Keep for each cell the median of the row medians, the smallest `p5`, the largest `p95` and the sum of the process counts ({L16-26}).
2. Group the rows of the block `ZS` in the same way. Keep for each cell the median of six counter fields ({L27-32}).
3. Read `one-thread.csv` of the first run of 2026-11-13. Collect the rate of every interval of the kernel `read` per binary, CPU and buffer size. Keep the median, the smallest and the largest value and the count ({L34-46}).
4. Add the whole-chip values of the facts sheet of 2026-11-15 as fixed numbers ({L48-74}).
5. For each of the two vendor runs: read the one-core sweep and the settings from the result archive. Then cut three tables and eight machine values out of the console output with regular expressions ({L76-101}).
6. Write everything to the JSON file of argument 1 and print a short report ({L102-109}).

## Behavior a reader must know

- The script holds fixed paths of the agent server ({L12-13}). `final8.json` and the vendor files are not in this repo.
- Block 3 does not read the facts sheet. Its numbers are typed into {L50-73}. A later change of the facts sheet does not reach them. For this page each value was compared with the facts sheet, and all agree [Ref1].
- How block 1 combines: the `median` of a cell is a median of medians. `lo` and `hi` are the outer ends of the `p5` and `p95` values of the rows. They are not the smallest and the largest single process.
- How block 2 reads a rate: the seventh column (`aggregate_GBps`) of each data row with a numeric `rep`. The row `best` of each process is skipped [Ref2].
- Rates of the vendor sweep are divided by 1e3. So they are in GB/s with GB = 1e9 bytes, as all rates of the project.
- A missing heading in the console output stops the script with an error in {L90} or {L92}. A missing value of `grab` only gives `None`.
- The scripts `notes.py`, `facts.py`, `figs.py`, `report.py` and `dyn_notes.py` of the same folder read the output file.

## References

- [Ref1] `FINDINGS.md` in the folder `w120-2026-11-15`: the sections "The question", F2, F4 and F5.
- [Ref2] `one-thread.csv` in the result folder `kernels-20261113T181222Z` of the test folder `2026-11-13-new-read-kernel`: the header lines, the comment line with the definition of `aggregate_GBps`, and the column titles.
- [Ref3] The console outputs of the vendor runs in the welcome kit of Arm, folder `tools/asct/reports`: the files `asct_run_output_a0_numa2_ddr_7200.txt` and `asct_run_output_a1_numa2_ddr_8000.txt`, with the headings and the column titles of the tables.
