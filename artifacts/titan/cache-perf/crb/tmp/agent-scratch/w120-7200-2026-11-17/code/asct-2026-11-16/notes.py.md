# `notes.py` explained, line by line

- Source file: `asct-2026-11-16/notes.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 117 lines, 11149 bytes).
- sha256 of the source when this page was built: `13906f3c14e9985d5a3ce1217e1c0124949aebc3f63b98496c00045d99597589`.

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

1. Read the facts file and the baseline file (lines 8 to 9).
2. Compute two gains of the new read kernel from the medians of the first run, and take the whole-chip rows of the old and the new read loop from the baseline file (lines 26 to 30).
3. Build the block `words`, the word list of the report (lines 32 to 68).
4. Build the block `asked` with the two gains and the whole-chip totals (lines 70 to 77).
5. Set two figure captions (lines 79 to 82).
6. Build the block `refs`, the reference list of the report (lines 84 to 99).
7. Load `dyn_notes.py` and let its function `fill` add the other blocks. The helpers `p`, `ul` and `ref`, which make a paragraph, a list and citation marks, are passed to it (lines 101 to 102).
8. Stop when one of the 45 needed blocks is missing, or when a text holds one of three marker words (lines 104 to 115).
9. Write all blocks to the output file and print their number (lines 116 to 117).

## Behavior a reader must know

- The script measures nothing and reads no result folder. Its numbers come from the two input files, or they are fixed text.
- The two gains are ratios of medians: the median rate of `bw_new` divided by the median rate of `bw_old`, for the kernel `read` on CPU 2, at 8 MiB and at 1 MiB. `baseline.py` computes these medians from the file `one-thread.csv` of the first run.
- The description text says that every number of the text comes from the facts file or the baseline file. In this file the range in line 73 and the numbers of the word list (lines 33 to 68) are fixed text.
- The citation marks inside the source lines belong to the reference list of the report page (lines 84 to 99), not to this page.
- A missing block or a marker word ends the script with exit status 1 before the output file is written.
- The variable `MI` of line 10 is not used in this file.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/notes.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (117 lines, 11149 bytes, sha256 `13906f3c14e9985d5a3ce1217e1c0124949aebc3f63b98496c00045d99597589`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, the two input files and three helpers for HTML text (lines 1 to 25)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""notes.py FACTS.json BASELINE.json OUT.json: the text blocks of ASCT-cross-check.html.` | Starts the description text of the file. Usage: three arguments, the facts file, the baseline file and the output file. The script builds the text blocks of the report page `ASCT-cross-check.html`. |
| 3 | `Every number in the text is taken from FACTS or BASELINE by this script, so the text cannot drift from the data.` | Description, continued: by this text the script takes every number of the text from the facts file or from the baseline file, so the text cannot differ from the data. This is not exact for this file. The word list and line 73 hold numbers as fixed text. |
| 4 | `Blocks that depend on what the data shows are written in dyn_notes.py (imported below) after the runs."""` | Description, last line: the blocks that depend on what the data shows are written in the file `dyn_notes.py`, after the runs. Line 101 loads that file. |
| 5 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 6 | `import sys` | Loads the module `sys`, which gives the arguments and can end the script. |
| 8 | `F = json.load(open(sys.argv[1]))` | `F`: the content of the facts file, argument 1. It holds the results of the ASCT runs. |
| 9 | `B = json.load(open(sys.argv[2]))` | `B`: the content of the baseline file, argument 2. The script `baseline.py` writes that file. It holds the older numbers for the comparison. |
| 10 | `MI = 1 << 20` | `MI`: 1048576, the number of bytes of 1 MiB (`1 << 20` shifts 1 by 20 bits). No later line of this file uses it. |
| 11 | `N = {}` | `N`: the dictionary of the text blocks, empty at first. A key is the name of a block. A value is a text or a list of texts in HTML. |
| 14 | `def p(*s):` | Defines the helper `p`. It makes one HTML paragraph from its arguments. |
| 15 | `    return '<p>' + ' '.join(s) + '</p>'` | The body of `p`: joins the arguments with spaces and puts the paragraph tags around them. |
| 18 | `def ul(*items):` | Defines the helper `ul`. It makes one HTML list with a list item for each argument. |
| 19 | `    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'` | The body of `ul`: wraps each argument in list-item tags, joins them and puts the list tags around them. |
| 22 | `def ref(*n):` | Defines the helper `ref`. It turns reference numbers into the citation marks of the report. |
| 23 | `    return ' '.join(f'[Ref{i}]' for i in n)` | The body of `ref`: writes each number as `Ref` and the number in square brackets, with spaces between the marks. |

### The two gains and the block `words` (the word list of the report) (lines 26 to 68)

| Line | Source | Explanation |
|---:|---|---|
| 26 | `first = B['first']` | `first`: the block `first` of the baseline file. It holds the one-core rates of the first run of 2026-11-13 per binary, kernel, CPU and buffer size. |
| 27 | `g8 = (first['bw_new.read.2.8388608']['median'] / first['bw_old.read.2.8388608']['median'] - 1) * 100` | `g8`: the gain of the new read kernel at 8 MiB on CPU 2, in percent. It is the median rate of `bw_new` at 8388608 bytes divided by the median rate of `bw_old` at the same size, minus 1, times 100. |
| 28 | `g1 = (first['bw_new.read.2.1048576']['median'] / first['bw_old.read.2.1048576']['median'] - 1) * 100` | `g1`: the same gain at 1 MiB (1048576 bytes) on CPU 2. |
| 29 | `L = {r[0]: r for r in B['chip']['loops']}` | `L`: a dictionary from the name of a read loop to its row in the list `loops` of the block `chip` of the baseline file. A row holds the window depth and the smallest and the largest whole-chip total. |
| 30 | `old, new = L['old read'], L['new read (asmread)']` | `old` and `new`: the rows of the old read loop and of the new read loop in its assembly form (`asmread`). |
| 32 | `N['words'] = [ul(` | Starts the block `words`. It is a list with one element, the HTML list that `ul` builds from the entries of lines 33 to 68. |
| 33 | `    '<b>CRB</b>: the Arm Phoenix Reference Server in our lab, 128 cores (Arm part 0xd83), one NUMA node.',` | Word list of the report: the entry for the machine CRB. The numbers in it (cores, part number, NUMA nodes) are fixed text. |
| 34 | `    '<b>ASCT</b>: the Arm System Characterization Tool, version 0.7.1+77461b3. It is Arm\'s tool for memory latency and bandwidth tests.',` | Word list: the entry for ASCT, with its version as fixed text. The `\'` writes an apostrophe inside the text. |
| 35 | `    '<b>read loop</b>: the few instructions that a benchmark repeats to read a buffer. This report compares three read loops.',` | Word list: the entry for the term read loop. |
| 36 | `    '<b>old read</b>: the read loop of our benchmark before 2026-11-13. It loads every byte and adds the loaded values.',` | Word list: the entry for the old read loop of our benchmark. |
| 37 | `    '<b>new read</b>: the read loop of our benchmark since 2026-11-13. It loads every byte and does no other work. '` | Word list: the entry for the new read loop of our benchmark. The text goes on in line 38. |
| 38 | `    'Its values here are those of the assembly form (<code>asmread</code>) unless a line says otherwise.',` | Continues the entry of line 37: which form of the new read loop the values of the report belong to. |
| 39 | `    '<b>ASCT read</b>: the read loop of ASCT (function <code>my_read_no_nops_rep_64b</code>). It loads 8 bytes of each 64-byte line.',` | Word list: the entry for the read loop of ASCT, with the name of its function and the bytes that it loads per cache line. |
| 40 | `    '<b>line</b>: one 64-byte cache line. Caches and memory move data in lines.',` | Word list: the entry for a cache line. |
| 41 | `    '<b>L1, L2</b>: the two private caches of a core, 64 KiB and 2 MiB.',` | Word list: the entry for the two private caches of a core, with their sizes as fixed text. |
| 42 | `    '<b>SLC</b>: the system-level cache, 128 MiB, shared by all cores. Linux calls it L3.',` | Word list: the entry for the SLC, with its size as fixed text. |
| 43 | `    '<b>mesh</b>: the on-chip network that links cores, SLC and memory ports. CRB has two meshes: mesh 0 holds CPUs 0 to 63, mesh 1 holds CPUs 64 to 127.',` | Word list: the entry for the mesh and for the CPUs of mesh 0 and mesh 1. |
| 44 | `    '<b>64+56</b>: 64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119, one thread per CPU, 256 MiB per thread.',` | Word list: the entry for the thread layout 64+56. |
| 45 | `    '<b>injected NOPs (N)</b>: an ASCT option (<code>--bw-fine-delay N</code>). ASCT then runs an empty loop of N rounds after each load. ASCT calls the rounds NOPs. One round has 3 instructions.',` | Word list: the entry for the injected NOPs of ASCT, with the option that sets them. |
| 46 | `    '<b>window</b>: the instructions that a core holds in flight at one moment. A read loop with few instructions per line puts many lines into one window.',` | Word list: the entry for the out-of-order window of a core. |
| 47 | `    '<b>prefetcher</b>: the part of a core that requests lines before the program asks for them.',` | Word list: the entry for the prefetcher. |
| 48 | `    '<b>core counter</b>: a hardware counter inside a core, for example cycles or cache refills. ASCT reads them through its capture code named dietperf.',` | Word list: the entry for a core counter and for the counter code of ASCT. |
| 49 | `    '<b>probe build</b>: the variant of the ASCT benchmark binary that contains the capture code.',` | Word list: the entry for the probe build of the ASCT binary. |
| 50 | `    '<b>mesh counter</b>: a hardware counter of the mesh (Linux units <code>arm_cmn_0</code> and <code>arm_cmn_1</code>). Reading it needs root.',` | Word list: the entry for a mesh counter, with the names of the two mesh units of Linux. |
| 51 | `    '<b>L2 refill</b>: one line that enters L2 from the SLC or from memory. The counter is <code>l2d_cache_refill</code>.',` | Word list: the entry for an L2 refill, with the name of its counter. |
| 52 | `    '<b>long-latency miss</b>: a load that had to wait for its line. A load whose line was prefetched in time is not counted.',` | Word list: the entry for a long-latency miss. |
| 53 | `    '<b>L1 prefetches, L2 prefetches</b>: the counts of the counters <code>l1d_cache_hwprf</code> and <code>l2d_cache_hwprf</code>. One count is one request of the hardware prefetcher of that cache.',` | Word list: the entry for the L1 and the L2 prefetches, with the names of the two counters. |
| 54 | `    '<b>busy level</b>: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. The core counts the answers of each level (counters <code>l2_chi_cbusy0</code> to <code>l2_chi_cbusy3</code>).',` | Word list: the entry for the busy level, with the names of the four counters of a core. |
| 55 | `    '<b>hop</b>: one step from one crosspoint of the mesh to the next.',` | Word list: the entry for a hop on the mesh. |
| 56 | `    '<b>slow state</b>: the condition at 64+56 in which a thread reads about 2 GB/s. In the fast condition it reads about 5 GB/s.',` | Word list: the entry for the slow state at 64+56. The two rates in it are fixed text. |
| 57 | `    '<b>lower bound of a total</b>: all bytes that the threads of one process read, divided by the time of the slowest thread. ASCT itself adds the rates of the threads.',` | Word list: the entry for the lower bound of a total, the second way in which the report gives a whole-chip rate. |
| 58 | `    '<b>huge page</b>: a memory page of 2 MiB or more. A normal page has 4 KiB. With transparent huge pages the kernel gives huge pages to a program that did not ask for them.',` | Word list: the entry for a huge page and for transparent huge pages. |
| 59 | `    '<b>P-A1, R-A3, D-A2 and similar names</b>: the predictions (P), rules (R) and descriptive items (D) of the decisions file. They were written before the data that they judge.',` | Word list: the entry for the names of the predictions, rules and descriptive items of the decisions file. |
| 60 | `    '<b>part U, N, C, NC</b>: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.',` | Word list: the entry for the four parts U, N, C and NC of the one-core runs. |
| 61 | `    '<b>marker file</b>: the file <code>/tmp/positron-perf.RUNNING</code> on CRB. The other user of CRB creates it while his tests run.',` | Word list: the entry for the marker file. |
| 62 | `    '<b>process</b>: one start of the ASCT benchmark binary. It prints one rate.',` | Word list: the entry for a process. |
| 63 | `    '<b>median, range</b>: the middle value of the processes of a cell, and the smallest to the largest value.',` | Word list: the entry for the median and the range of a cell. |
| 64 | `    '<b>GB</b>: 10<sup>9</sup> bytes. <b>KiB, MiB, GiB</b>: 2<sup>10</sup>, 2<sup>20</sup>, 2<sup>30</sup> bytes.',` | Word list: the entry for the units GB, KiB, MiB and GiB. |
| 65 | `    '<b>Arm reference machines A0 and A1</b>: the two machines of the vendor baseline runs in the Arm welcome kit. They have firmware v0.9.0 and two NUMA nodes.',` | Word list: the entry for the two reference machines of the vendor runs. |
| 66 | `    '<b>NUMA node</b>: a group of cores and the memory that the firmware declares as local to them.',` | Word list: the entry for a NUMA node. |
| 67 | `    '<b>block</b>: a time window that Jeremy Conner reserves on CRB in Slack channel #phoenix-crb.',` | Word list: the entry for a block, a time window that another user reserves on CRB. |
| 68 | `    '<b>est.</b>: an estimate, not a measurement.')]` | Word list: the entry for the mark of an estimate. The two closing brackets end the call of `ul` and the list of the block. |

### The block `asked`, two figure captions and the reference list (lines 69 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 70 | `N['asked'] = [` | Starts the block `asked`, the section of the report on what was asked. It is a list of three parts. |
| 71 | `    p('Two results of our own read benchmark on CRB are not understood.'),` | Part 1: a paragraph that says that two results of our benchmark are not understood. |
| 72 | `    ul(f'<b>Question 1, 8 MiB.</b> The new read loop is {g1:.1f} % faster than the old read loop at 1 MiB on one core. '` | Part 2: a list with the two questions. This line starts question 1 and puts in `g1`, the gain at 1 MiB on one core, with one decimal. |
| 73 | `       f'At 8 MiB the gain was {g8:.2f} % in the first run of 2026-11-13 {ref(1)}. The runs of 2026-11-15 found 0.2 to 6.7 % {ref(2)}.',` | Continues question 1. It puts in `g8`, the gain at 8 MiB in the first run, with two decimals, and the citation mark of reference 1 of the report. Then it names the range that the runs of 2026-11-15 found, with reference 2. The two numbers of that range are fixed text. |
| 74 | `       f'<b>Question 2, whole chip.</b> At 64+56 threads the old read loop reads {old[3]:.1f} to {old[4]:.1f} GB/s in total. '` | Question 2. It puts in the smallest and the largest total of the old read loop at 64+56, with one decimal. These are the entries `old[3]` and `old[4]` of the row. Python counts the entries from 0. |
| 75 | `       f'The new read loop reads {new[3]:.1f} to {new[4]:.1f} GB/s {ref(3)}.'),` | Continues question 2 with the smallest and the largest total of the new read loop (row `new`) and the citation mark of reference 3. The closing bracket ends the list of the two questions. |
| 76 | `    p('The request for this work: repeat both tests with ASCT on the same cores and sizes, compare the rates with the old and the new loop, '` | Part 3: a paragraph with the request for this work: repeat both tests with ASCT on the same cores and sizes, and compare the rates. |
| 77 | `      'and capture the counters and registers that ASCT can reach, with a focus on the prefetchers.')]` | Continues the paragraph of line 76: capture the counters and registers that ASCT can reach, most of all for the prefetchers. The closing brackets end the paragraph and the block. |
| 79 | `N['cap_path'] = ('<b>Figure 1.</b> The ASCT front end fixes its core and needs huge pages. So the runs called the ASCT benchmark binary directly, '` | Sets the block `cap_path`, the caption of Figure 1 of the report: why the runs called the ASCT binary directly. |
| 80 | `                 'with the command line that the front end builds.')` | Continues the caption of line 79. |
| 81 | `N['cap_loops'] = ('<b>Figure 2.</b> The ASCT loop loads one eighth of the bytes that it counts. Its rate is comparable with ours only when the '` | Sets the block `cap_loops`, the caption of Figure 2 of the report: how many of the counted bytes the ASCT loop loads, and when its rate can be compared with ours. |
| 82 | `                  'transfer of lines is the limit, not the work inside the core.')` | Continues the caption of line 81. |
| 84 | `N['refs'] = [` | Starts the block `refs`, the reference list of the report. It has 14 entries. |
| 85 | `    '[Ref1] First run of the new loops, 2026-11-13: <code>crb/results/kernels-20261113T181222Z/one-thread.csv</code> and <code>threads120.csv</code>. The gain uses the medians of 6 repetitions on CPU 2.',` | Entry 1 of the reference list: the two result files of the first run of the new loops, and how the gain is computed. |
| 86 | `    '[Ref2] The 8 MiB work of 2026-11-15: <code>crb/new-test-kernel/tackle-8mb-results.md</code>. Numbers from <code>tackle-8mb-analysis/final8.json</code>, blocks <code>size_curve</code>, <code>ZS</code>, <code>evict</code> (step <code>ZC</code>) and <code>prefetch</code> (step <code>YC</code>).',` | Entry 2: the result page and the result file of the 8 MiB work, with the names of the blocks that were used. |
| 87 | `    '[Ref3] The whole-chip work of 2026-11-15: <code>crb/tmp/agent-scratch/w120-2026-11-15/FINDINGS.md</code>, sections F2 to F4. Report <code>crb/new-test-kernel/whole-chip-read-drop.html</code>.',` | Entry 3: the facts sheet and the report page of the whole-chip work of 2026-11-15. |
| 88 | `    '[Ref4] ASCT source, tarball <code>~/asct/asct-0.7.1+77461b3/asct-0.7.1+77461b3.tar.gz</code> on CRB: <code>src/core/recipes/impl/memory_load_latency.py</code> and <code>recipe_benchmark_base.py</code> (choice of CPUs), <code>src/core/recipes/configuration/schema.py</code> (user settings), <code>src/core/benchspec/memory_benchspec.py</code> (command line).',` | Entry 4: the source files of ASCT that choose the CPUs, define the user settings and build the command line. |
| 89 | `    '[Ref5] ASCT benchmark source in the same tarball: <code>extern/infra-microbenchmarks/loaded-latency/bandwidth.c</code> (read loops, timing), <code>alloc.c</code> (buffer), <code>main.c</code> (total).',` | Entry 5: the source files of the ASCT benchmark: the read loops and the timing, the buffer, and the total. |
| 90 | `    '[Ref6] ASCT counter and register code in the same tarball: <code>extern/dietperf/dietperf.h</code>, <code>src/core/asct_pmu_api.py</code>, <code>src/core/asct_env.py</code>, <code>src/core/config/ubench.json</code>, <code>src/core/recipes/impl/sysreg.py</code>, <code>src/core/recipes/impl/cmn.py</code>, <code>src/lib/cmn-tools/cmn_api.py</code>.',` | Entry 6: the source files of the counter code and of the register code of ASCT. |
| 91 | `    '[Ref7] ASCT manual, <code>~/asct/asct-0.7.1+77461b3/asct_docs/index.html</code> on CRB, section "Huge-page requirements for runs without root privileges".',` | Entry 7: the section of the ASCT manual on huge pages. |
| 92 | `    '[Ref8] Decisions and predictions of this work, written before the first run: <code>crb/tmp/agent-scratch/asct-2026-11-16/DECISIONS.md</code>.',` | Entry 8: the decisions file of this work. |
| 93 | `    '[Ref9] Run scripts of this work: <code>crb/tmp/agent-scratch/asct-2026-11-16/crb/</code> (<code>prep.sh</code>, <code>run_single.sh</code>, <code>run_chip.sh</code>, <code>run_mesh.sh</code>, event lists).',` | Entry 9: the folder with the run scripts of this work and the event lists. |
| 94 | `    '[Ref10] Results of this work: folders <code>crb/results/asct-*</code>. All numbers of this page are in <code>crb/tmp/agent-scratch/asct-2026-11-16/asct.json</code> and <code>facts.json</code> (built by <code>analyze.py</code> and <code>facts.py</code>).',` | Entry 10: the result folders of this work and the two JSON files that hold all numbers of the report page. |
| 95 | `    '[Ref11] Vendor baseline runs: <code>vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/reports/</code> (two console outputs and two result archives). The file <code>raw/bandwidth-sweep/bandwidth-sweep.ubench.json</code> of each archive holds the one-core sweep.',` | Entry 11: the vendor runs in the welcome kit of Arm. |
| 96 | `    '[Ref12] CRB machine record: <code>crb/inspection-record-2026-10-30.md</code> (firmware, NUMA) and <code>crb/results/dmidecode-t17-2026-10-30.txt</code> (memory modules).',` | Entry 12: the two machine records of CRB, one for firmware and NUMA and one for the memory modules. |
| 97 | `    '[Ref13] Rules for the shared machine: <code>crb/jeremy-plan-constraints-2026-10-30.md</code>. Block announcement in Slack #phoenix-crb of 2026-11-16 16:14 UTC.',` | Entry 13: the rules for the shared machine and the announcement of a reserved time window in Slack. |
| 98 | `    '[Ref14] Positions of the cores on the mesh: <code>crb/results/sudo-20261102T054936Z/core-positions.json</code> and <code>crb/results/cmn-map.txt</code>.',` | Entry 14: the two files that give the positions of the cores on the mesh. |
| 99 | `]` | Ends the list of the block `refs`. |

### The blocks of `dyn_notes.py`, two checks and the output (lines 100 to 117)

| Line | Source | Explanation |
|---:|---|---|
| 101 | `import dyn_notes  # noqa: E402  (the blocks written after the runs)` | Loads the module `dyn_notes`, the file `dyn_notes.py` of the same folder. It holds the blocks that were written after the runs. The comment `noqa: E402` tells a style checker to accept that this `import` does not stand at the top of the file. |
| 102 | `dyn_notes.fill(N, F, B, p, ul, ref)` | Calls `dyn_notes.fill`. It gets the dictionary `N`, the two input files `F` and `B` and the three helpers. It adds the other blocks to `N`. |
| 104 | `need = ['subtitle', 'short', 'words', 'asked', 'how', 'loops', 'q1_intro', 'q1_rates', 'q1_cost_intro', 'q1_cost', 'q1_pf_intro', 'q1_pf',` | `need`: starts the list of the 45 block names that the report page needs. This line holds the first twelve, from the subtitle to the prefetch part of question 1. |
| 105 | `        'q1_pad_intro', 'q1_pad', 'q1_mesh_intro', 'q1_mesh', 'q1_verdict', 'q2_intro', 'q2_rates', 'q2_layouts', 'q2_cnt_intro', 'q2_cnt',` | Continues the list: the other blocks of question 1 and the first blocks of question 2. |
| 106 | `        'q2_mesh_intro', 'q2_mesh', 'q2_verdict', 'vendor', 'vendor2', 'capture', 'runs', 'open', 'refs', 'cap_path', 'cap_loops', 'cap_size',` | Continues the list: the last blocks of question 2, the blocks on the vendor runs, on the capture, on the runs and on the open points, the reference list and three captions. |
| 107 | `        'cap_fall', 'cap_cost', 'cap_prefetch', 'cap_pad', 'cap_chip', 'cap_nops', 'cap_threads', 'mesh_tag_names', 'mesh_chip_tags',` | Continues the list: seven more captions and two blocks with tag names of the mesh-counter runs. |
| 108 | `        'mesh_single_tags', 'peer_counters']` | Ends the list with the last two names. |
| 109 | `missing = [k for k in need if k not in N]` | `missing`: the names of `need` that `N` does not hold. |
| 110 | `if missing:` | When at least one block is missing: |
| 111 | `    sys.exit(f'notes blocks missing: {missing}')` | ends the script. `sys.exit` with a text prints `notes blocks missing:` and the names to the error output and returns exit status 1. No output file is written. |
| 112 | `blob = json.dumps(N)` | `blob`: all blocks as one JSON text. |
| 113 | `for bad in ('TODO', 'PLACEHOLDER', 'FAKE'):` | Starts a loop over three marker words: `TODO`, `PLACEHOLDER` and `FAKE`. |
| 114 | `    if bad in blob:` | When the text of the blocks holds the marker word: |
| 115 | `        sys.exit(f'notes contain the marker {bad}')` | ends the script with the message `notes contain the marker` and the word, and with exit status 1. No output file is written. |
| 116 | `json.dump(N, open(sys.argv[3], 'w'), indent=1)` | Writes `N` as a JSON file to the path of argument 3, with an indent of 1 space per level. |
| 117 | `print('notes written', len(N), 'blocks')` | Prints `notes written`, the number of blocks and the word `blocks`. |
