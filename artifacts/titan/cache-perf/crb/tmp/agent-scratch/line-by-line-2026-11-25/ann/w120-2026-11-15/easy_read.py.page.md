## Short version: purpose

`easy_read.py` builds the easy-read page of the report on the whole-chip read drop: one HTML file with two pictures, a word list, seven step boxes and 15 references. Every number of the page stands in this script as fixed text, copied from the facts sheet `FINDINGS.md`. The script reads no result file and computes no result.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Facts sheet of the investigation**: the file `FINDINGS.md` in the same folder as this script. It holds the numbers of the report of 2026-11-15 with the files that they come from.
- **Loop**: the word of the built page for a kernel. The script uses the kernel names of the runners, for example `oldread` and `asmread`, in the data of figure 2.
- **Total**: the sum of the rates of all threads, in GB/s.
- **64 plus 56**: 64 threads on mesh 0 and 56 threads on mesh 1, written `64+56` in the page.
- **Window**: the instructions that a core holds between fetch and retirement. This is the definition of the word list in {L180}.
- **Window depth**: the number of 64 B lines that the loads inside one full window touch. This is the definition of the word list in {L181}.
- **State**: one of the three words `slow`, `between` and `fast` that the list `P` gives to each loop.
- **SVG**: a text format for pictures that are made of lines, shapes and text. A browser draws it inside an HTML page.
- **CSS**: the style rules of an HTML page: sizes, colours, spacing.

## Main flow

1. Set the output path and the six colours ({L6-10}).
2. Hold the six data rows of figure 1 and define `fig1`, which draws one bar per row, from the lowest to the highest total ({L14-47}).
3. Hold the 29 data rows of figure 2, count the loops of each state, and define `fig2`, which draws one point per loop: the window depth on a logarithmic axis and the total on a linear axis ({L52-141}).
4. Hold the texts of the page: the 15 references, the function `ref` for a citation, the 23 word entries, the seven overview boxes, the seven steps (each built by the function `step`) and the style rules ({L145-350}).
5. Define `build`. It joins all parts into one HTML text, writes it to the file `OUT` and prints the path and the length ({L353-470}).
6. Call `build` ({L473}).

## Behavior a reader must know

- The script has no input. Every rate, window depth and count of the page is typed into this file. So a number of the page is only as right as its copy from the facts sheet.
- One number can stand at several places. The values of the old read loop, for example, stand in the list `P` ({L73}), in a label of figure 2 ({L123-125}), in the step texts and in the table ({L435}). A change must be made at each place by hand.
- The output path is fixed ({L6}). Each run replaces the file `whole-chip-read-drop-easy-read.html` in the folder `new-test-kernel` on the agent server.
- `build` is called at the top level ({L473}). So the page is also written when another script imports this file.
- In figure 1 a bar spans the lowest and the highest value of a row, and the rate axis starts at 0. In figure 2 a point stands at the middle of the lowest and the highest total of a loop, not at a mean or a median, and the rate axis starts at 0.
- The paths in the reference texts are paths of the agent server ({L7-8}), not paths of the code repo.
- The check of {L83} stops the script when the list of figure 2 does not hold 29 rows.
