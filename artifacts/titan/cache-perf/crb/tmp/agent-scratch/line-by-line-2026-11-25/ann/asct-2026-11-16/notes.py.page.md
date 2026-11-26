## Short version: purpose

`notes.py` builds the text blocks of the report page of the ASCT cross-check and writes them to one JSON file. It holds the word list, the two questions, two figure captions and the reference list itself, and it lets the file `dyn_notes.py` add the blocks that depend on the results. It stops without output when a needed block is missing or when a text still holds a marker word such as `TODO`.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Report page**: the file `ASCT-cross-check.html`, the result page of the cross-check. The script `report.py` of the same folder builds it.
- **Text block**: one named piece of the text of the report page, in HTML.
- **Facts file**: the JSON file of argument 1. By the reference list in this script it holds all numbers of the report page and is built by `analyze.py` and `facts.py`.
- **Baseline file**: the JSON file of argument 2, written by `baseline.py`. It holds the older numbers with which the ASCT results are compared.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Read loop**: the word of the report page for a read kernel.
- **Gain**: how much faster the new read kernel is than the old one, in percent of the old rate.
- **64+56**: 64 threads on the CPUs 0 to 63 plus 56 threads on the CPUs 64 to 119.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Read the facts file and the baseline file ({L8-9}).
2. Compute two gains of the new read kernel from the medians of the first run, and take the whole-chip rows of the old and the new read loop from the baseline file ({L26-30}).
3. Build the block `words`, the word list of the report ({L32-68}).
4. Build the block `asked` with the two gains and the whole-chip totals ({L70-77}).
5. Set two figure captions ({L79-82}).
6. Build the block `refs`, the reference list of the report ({L84-99}).
7. Load `dyn_notes.py` and let its function `fill` add the other blocks. The helpers `p`, `ul` and `ref`, which make a paragraph, a list and citation marks, are passed to it ({L101-102}).
8. Stop when one of the 45 needed blocks is missing, or when a text holds one of three marker words ({L104-115}).
9. Write all blocks to the output file and print their number ({L116-117}).

## Behavior a reader must know

- The script measures nothing and reads no result folder. Its numbers come from the two input files, or they are fixed text.
- The two gains are ratios of medians: the median rate of `bw_new` divided by the median rate of `bw_old`, for the kernel `read` on CPU 2, at 8 MiB and at 1 MiB. `baseline.py` computes these medians from the file `one-thread.csv` of the first run.
- The description text says that every number of the text comes from the facts file or the baseline file. In this file the range in {L73} and the numbers of the word list ({L33-68}) are fixed text.
- The citation marks inside the source lines belong to the reference list of the report page ({L84-99}), not to this page.
- A missing block or a marker word ends the script with exit status 1 before the output file is written.
- The variable `MI` of {L10} is not used in this file.
