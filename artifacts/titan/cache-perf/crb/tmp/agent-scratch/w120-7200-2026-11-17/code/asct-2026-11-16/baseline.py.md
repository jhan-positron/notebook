# `baseline.py` explained, line by line

- Source file: `asct-2026-11-16/baseline.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 109 lines, 6956 bytes).
- sha256 of the source when this page was built: `4c37884e23760dda4d24ac9a92935bdfde321b49a20559718c11548da174e900`.

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

1. Read `final8.json`. Group the rows of its block `size_curve` by kernel, CPU and buffer size. Keep for each cell the median of the row medians, the smallest `p5`, the largest `p95` and the sum of the process counts (lines 16 to 26).
2. Group the rows of the block `ZS` in the same way. Keep for each cell the median of six counter fields (lines 27 to 32).
3. Read `one-thread.csv` of the first run of 2026-11-13. Collect the rate of every interval of the kernel `read` per binary, CPU and buffer size. Keep the median, the smallest and the largest value and the count (lines 34 to 46).
4. Add the whole-chip values of the facts sheet of 2026-11-15 as fixed numbers (lines 48 to 74).
5. For each of the two vendor runs: read the one-core sweep and the settings from the result archive. Then cut three tables and eight machine values out of the console output with regular expressions (lines 76 to 101).
6. Write everything to the JSON file of argument 1 and print a short report (lines 102 to 109).

## Behavior a reader must know

- The script holds fixed paths of the agent server (lines 12 to 13). `final8.json` and the vendor files are not in this repo.
- Block 3 does not read the facts sheet. Its numbers are typed into lines 50 to 73. A later change of the facts sheet does not reach them. For this page each value was compared with the facts sheet, and all agree [Ref1].
- How block 1 combines: the `median` of a cell is a median of medians. `lo` and `hi` are the outer ends of the `p5` and `p95` values of the rows. They are not the smallest and the largest single process.
- How block 2 reads a rate: the seventh column (`aggregate_GBps`) of each data row with a numeric `rep`. The row `best` of each process is skipped [Ref2].
- Rates of the vendor sweep are divided by 1e3. So they are in GB/s with GB = 1e9 bytes, as all rates of the project.
- A missing heading in the console output stops the script with an error in line 90 or line 92. A missing value of `grab` only gives `None`.
- The scripts `notes.py`, `facts.py`, `figs.py`, `report.py` and `dyn_notes.py` of the same folder read the output file.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/baseline.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (109 lines, 6956 bytes, sha256 `4c37884e23760dda4d24ac9a92935bdfde321b49a20559718c11548da174e900`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, modules and fixed paths (lines 1 to 15)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""baseline.py OUT.json: collect the numbers of the earlier work that the ASCT cross-check is compared with.` | Starts the description text of the file. Usage: one argument, the output file. The script collects the numbers of the earlier work with which the ASCT cross-check is compared. |
| 3 | `Sources: final8.json of the 8 MiB work (2026-11-15), the first kernel run (2026-11-13), FINDINGS.md of the` | Description, continued: three of the four sources. `final8.json` of the 8 MiB work of 2026-11-15, the first run of the new kernels of 2026-11-13, and the facts sheet `FINDINGS.md`. |
| 4 | `whole-chip work (2026-11-15), and the two vendor ASCT baseline archives of the Arm welcome kit."""` | Description, last line: the facts sheet belongs to the whole-chip work of 2026-11-15. The fourth source is the two result archives of ASCT runs that the chip vendor made. They lie in the welcome kit of Arm. |
| 5 | `import collections` | Loads the module `collections`. The script uses its `defaultdict`, a dictionary that creates an empty entry for a new key. |
| 6 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 7 | `import re` | Loads the module `re` for regular expressions. |
| 8 | `import statistics as st` | Loads the module `statistics` under the short name `st`. The script uses its function `median`. |
| 9 | `import sys` | Loads the module `sys`, which gives the arguments of the script. |
| 10 | `import tarfile` | Loads the module `tarfile`, which reads files inside a `tar` archive. |
| 12 | `C = '/home/jhan/workspace/titan/cache-perf/crb'` | `C`: the fixed path of the project folder `crb` on the agent server. The input files of the blocks 1 and 2 lie below it. |
| 13 | `KIT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/asct/reports'` | `KIT`: the fixed path of the folder with the ASCT reports of the vendor, inside the welcome kit of Arm. |
| 14 | `out = {}` | `out`: the dictionary that becomes the output file. It starts empty. |

### Block 1: one core, from `final8.json` (lines 16 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 16 | `# 1. one core: old read, new read (C and assembly) per size and CPU` | Comment: block 1 holds the one-core values of the old read kernel and of the new read kernel (the C form and the assembly form) per buffer size and CPU. |
| 17 | `d = json.load(open(f'{C}/new-test-kernel/tackle-8mb-analysis/final8.json'))` | `d`: the content of `final8.json`, the result file of the analysis of the 8 MiB work. |
| 18 | `cells = collections.defaultdict(list)` | `cells`: a dictionary that gives an empty list for a new key. |
| 19 | `for r in d['size_curve']['rows']:` | Starts a loop over the rows of the block `size_curve` of `final8.json`. By the fields that the next lines use, a row holds a kernel, a CPU, a size, a step name, a median, two percentiles and a count `n`. |
| 20 | `    cells[(r['kernel'], r['cpu'], r['size_bytes'])].append(r)` | Puts the row into the list of its cell. The key of a cell is the kernel, the CPU and the buffer size in bytes. |
| 21 | `single = {}` | `single`: an empty dictionary for the result of block 1. |
| 22 | `for (k, cpu, b), rows in sorted(cells.items()):` | Starts a loop over the cells in sorted order of their keys. `rows` is the list of rows of one cell. |
| 23 | `    single[f'{k}.{cpu}.{b}'] = {'median': st.median(r['median'] for r in rows), 'lo': min(r['p5'] for r in rows),` | One entry per cell, with the key `kernel.cpu.bytes`. `median`: the median of the `median` values of the rows. `lo`: the smallest `p5` value of the rows. The line goes on in lines 24 to 25. |
| 24 | `                                'hi': max(r['p95'] for r in rows), 'rows': len(rows),` | Continues the entry of line 23. `hi`: the largest `p95` value of the rows. `rows`: the number of rows of the cell. |
| 25 | `                                'processes': sum(r['n'] for r in rows), 'steps': sorted({r['step'] for r in rows})}` | Ends the entry of line 23. `processes`: the sum of the `n` values of the rows. `steps`: the sorted list of the different step names of the rows. |
| 26 | `out['single'] = single` | Stores the result of block 1 under the key `single` of the output. |
| 27 | `# counters of step ZS (per line): cycles, L2 refills, L1 long misses, bus accesses` | Comment: the next lines take the counters of the step `ZS`, per cache line: cycles, L2 refills, long misses of L1 and bus accesses. |
| 28 | `zs = collections.defaultdict(list)` | `zs`: a dictionary that gives an empty list for a new key. |
| 29 | `for r in d['ZS']['rows']:` | Starts a loop over the rows of the block `ZS` of `final8.json`. |
| 30 | `    zs[(r['kernel'], r['cpu'], r['size_bytes'])].append(r)` | Puts the row into the list of its cell, with the same kind of key as in line 20. |
| 31 | `out['zs'] = {f'{k}.{cpu}.{b}': {f: st.median(r[f] for r in rows) for f in ('rate', 'cyc', 'r', 'l1_long_miss', 'l2_wb', 'bus_access')}` | Stores the key `zs` of the output. For each cell, with the key `kernel.cpu.bytes`, it holds the median over the rows of six fields: `rate`, `cyc` (cycles per line), `r` (L2 refills per line), `l1_long_miss`, `l2_wb` and `bus_access`. |
| 32 | `             for (k, cpu, b), rows in sorted(zs.items())}` | Continues line 31: the loop over the cells in sorted order of their keys. |

### Block 2: the first run of 2026-11-13, from `one-thread.csv` (lines 34 to 47)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `# 2. the first run of 2026-11-13 (program bandwidth.c, CPU 0 and CPU 2, sizes 32K 1M 8M 1G)` | Comment: block 2 holds the first run of 2026-11-13 with the program `bandwidth.c`, on CPU 0 and CPU 2, with the sizes 32 KiB, 1 MiB, 8 MiB and 1 GiB. |
| 35 | `first = collections.defaultdict(list)` | `first`: a dictionary that gives an empty list for a new key. |
| 36 | `cur = None` | `cur`: the header values of the process whose rows are read now. `None` means that no header was seen yet. |
| 37 | `for line in open(f'{C}/results/kernels-20261113T181222Z/one-thread.csv'):` | Starts a loop over the lines of the file `one-thread.csv` in the result folder `kernels-20261113T181222Z`. |
| 38 | `    m = re.match(r'-- binary (\S+) kernel (\S+) threads 1 cpus (\d+) bytes (\S+) ', line)` | Pattern for the header line that starts each process in this file. It matches the text `-- binary`, a name, `kernel`, a name, `threads 1 cpus`, a number, `bytes`, a size text and a space. The four groups hold the binary, the kernel, the CPU and the size text. |
| 39 | `    if m:` | When the line is a header line: |
| 40 | `        cur = m.groups()` | keeps the four groups in `cur`, |
| 41 | `        continue` | and goes to the next line of the file. |
| 42 | `    f = line.strip().split(',')` | `f`: the fields of the line, split at the commas. |
| 43 | `    if cur and len(f) > 6 and f[3].isdigit():` | Takes a line as a data row when three things hold: a header was seen, the line has more than 6 fields, and its fourth field (the column `rep`) is a number. This skips the comment line, the line with the column titles and the row whose `rep` is `best`. |
| 44 | `        first[(cur[0], cur[1], int(cur[2]), int(f[2]))].append(float(f[6]))` | Appends the rate of the row to the list of its key. The rate is the seventh field, the column `aggregate_GBps`. By the comment line of the file it is the sum of the bytes divided by the longest elapsed time of a thread, in GB/s [Ref2]. The key is the binary, the kernel, the CPU and the bytes per thread, which the third field holds. |
| 45 | `out['first'] = {f'{b}.{k}.{cpu}.{size}': {'median': st.median(v), 'lo': min(v), 'hi': max(v), 'n': len(v)}` | Stores the key `first` of the output. For each key, written as `binary.kernel.cpu.bytes`, it holds the median, the smallest value (`lo`), the largest value (`hi`) and the number (`n`) of the rates. |
| 46 | `                for (b, k, cpu, size), v in sorted(first.items()) if k == 'read'}` | Continues line 45: the loop over the keys in sorted order. It keeps only the keys whose kernel is `read`. |

### Block 3: whole-chip values, typed in from the facts sheet (lines 48 to 75)

| Line | Source | Explanation |
|---:|---|---|
| 48 | `# 3. whole chip, 64+56, 256 MiB per thread (FINDINGS.md of 2026-11-15, section F2 and the question section)` | Comment: block 3 holds the whole-chip values at 64+56 with 256 MiB per thread. They come from the facts sheet `FINDINGS.md` of 2026-11-15, section F2 and the section of the question. The values of lines 65 to 73 stand in the sections F4 and F5, which the comment does not name. |
| 49 | `out['chip'] = {` | Starts the key `chip` of the output. All values of lines 50 to 73 are fixed numbers in this file. The script does not read `FINDINGS.md`. |
| 50 | `    'source': 'tmp/agent-scratch/w120-2026-11-15/FINDINGS.md',` | `source`: the path of the facts sheet, as text for the reader of the output. |
| 51 | `    'loops': [` | `loops`: starts a list with one row per read loop. |
| 52 | `        # name, what, window depth in lines, total GB/s low, high, intervals` | Comment: the fields of a row: the name, what the loop holds, the window depth in cache lines, the smallest and the largest total in GB/s, and the number of intervals. |
| 53 | `        ['old read', '4 ldp q + 8 vector adds per 128 B', '18-22', 465.5, 470.1, 22],` | Row for the old read kernel. The values that the line holds stand in the row `oldread` of the table in section F2 of the facts sheet [Ref1]. |
| 54 | `        ['new read (asmread)', '8 ldp q per 256 B, no other work', '36-40', 288.5, 309.8, 22],` | Row for the new read kernel in its assembly form. The values stand in the row `asmread` of that table [Ref1]. |
| 55 | `        ['read_1pl', '4 ldr q per 256 B, one load per line', '156-164', 230.2, 235.0, 16],` | Row for `read_1pl`, the loop with one load per cache line. The values stand in the row of that name [Ref1]. |
| 56 | `        ['read_nop64', '8 ldp q + 64 nop', '28-32', 325.5, 333.9, 13],` | Row for `read_nop64`, the load-only loop with 64 `nop` instructions. The values stand in the row of that name [Ref1]. |
| 57 | `        ['read_nop96', '8 ldp q + 96 nop', '20-24', 465.5, 470.6, 16],` | Row for `read_nop96`, the load-only loop with 96 `nop` instructions. The values stand in the row of that name [Ref1]. |
| 58 | `        ['read_1pl_nop96', '4 ldr q + 96 nop', '24-28', 460.8, 460.9, 2],` | Row for `read_1pl_nop96`, the loop `read_1pl` with 96 `nop` instructions. The values stand in the row of that name [Ref1]. |
| 59 | `        ['read_nop256', '8 ldp q + 256 nop', '8-12', 543.9, 549.0, 9],` | Row for `read_nop256`, the load-only loop with 256 `nop` instructions. The values stand in the row of that name [Ref1]. |
| 60 | `    ],` | Ends the list `loops`. |
| 61 | `    'first_run': {'old': [464.4, 466.7], 'new_c': [279.7, 304.1], 'asm': [271.1, 305.9], 'n': 6},` | `first_run`: the totals of the original run of 2026-11-13 with 120 threads, as smallest and largest value in GB/s for the old kernel, the new C kernel and the assembly kernel, and the number of values (6). The values stand in the section "The question" of the facts sheet [Ref1]. |
| 62 | `    'layouts': {  # oldread, asmread, read_nop96, read_nop128, one interval per cell` | `layouts`: starts a dictionary of other thread layouts. Comment: the four values of a layout belong to the loops `oldread`, `asmread`, `read_nop96` and `read_nop128`, with one interval per cell. |
| 63 | `        '56+56': [534.8, 300.1, 538.1, 547.1], '64+0': [348.0, 348.4, 349.0, 351.0], '0+56': [318.0, 318.1, 319.2, 321.7]},` | The totals in GB/s for the layouts 56+56, 64+0 and 0+56. The values stand in section F2 of the facts sheet, under "Other layouts" [Ref1]. The closing brace ends `layouts`. |
| 64 | `    'per_thread': {'slow': {'mesh0': [2.5, 2.75], 'mesh1': [2.25, 2.45]}, 'fast': {'mesh0': [4.27, 5.45], 'mesh1': [2.51, 2.78]}},` | `per_thread`: the rate of one thread in GB/s, as smallest and largest value, for the slow state and for the fast state, each for mesh 0 and for mesh 1. The values stand in section F2 of the facts sheet [Ref1]. |
| 65 | `    'core_counters_per_line': {'bus_access': 2.08, 'l2d_cache_refill': 1.000, 'l2d_cache_hwprf': 1.000,` | `core_counters_per_line`: counter values of a core per cache line: bus accesses, L2 refills and L2 hardware prefetches. The line goes on in line 66. |
| 66 | `                               'cycles_slow': [66, 77], 'cycles_fast_mesh0': [35, 37]},` | Continues line 65: the cycles per line in the slow state and, for mesh 0, in the fast state, each as smallest and largest value. The values of lines 65 to 66 stand in the last paragraph of section F4 of the facts sheet [Ref1]. |
| 67 | `    'mesh_per_line': {  # slow asmread 299 GB/s \| fast read_nop96 470 \| fast oldread 468 (run w120-RC1)` | `mesh_per_line`: starts a dictionary of mesh counter values per cache line. Comment: the three values of an event belong to three processes of the run `w120-RC1`: the slow one with `asmread`, the fast one with `read_nop96` and the fast one with `oldread`. |
| 68 | `        'hns_pocq_retry_all': [0.047, 0.072, 0.069], 'hns_qos_pocq_occupancy_all': [0.087, 0.121, 0.118],` | The values for the request retries and for the queue occupancy of the home nodes [Ref1]. |
| 69 | `        'hns_mc_retries_local_all': [0.0046, 0.043, 0.039], 'ccra_chidat_stalls': [0.21, 0.73, 0.73],` | The values for the retries at the memory controllers and for the data stalls of the gateway [Ref1]. |
| 70 | `        'hns_cbusy11_all': [0.21, 1.49, 1.53], 'mxp_e_req_txflit_stall': [0.013, 0.167, 0.163],` | The values for busy level 3 at the home nodes and for the stalls of the request link to the east [Ref1]. |
| 71 | `        'mxp_e_dat_txflit_stall': [0.162, 0.344, 0.351], 'mxp_n_dat_txflit_stall': [0.119, 0.069, 0.073],` | The values for the stalls of the data link to the east and to the north [Ref1]. |
| 72 | `        'mxp_s_dat_txflit_stall': [0.027, 0.020, 0.025]},` | The values for the stalls of the data link to the south. The closing brace ends `mesh_per_line`. The values of lines 68 to 72 stand in section F4 of the facts sheet [Ref1]. |
| 73 | `    'one_thread_256M_cpu2': {'asmread': 35.7},` | `one_thread_256M_cpu2`: the rate of `asmread` with one thread on CPU 2 and a buffer of 256 MiB, in GB/s. The value stands in section F5 of the facts sheet [Ref1]. |
| 74 | `}` | Ends the dictionary of the key `chip`. |

### Block 4: the ASCT runs of the vendor (lines 76 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 76 | `# 4. vendor ASCT baseline runs` | Comment: block 4 holds the baseline runs that the vendor made with ASCT. |
| 77 | `vend = {}` | `vend`: an empty dictionary for the result of block 4. |
| 78 | `for name in ('a0_numa2_ddr_7200', 'a1_numa2_ddr_8000'):` | Starts a loop over the names of the two vendor runs, `a0_numa2_ddr_7200` and `a1_numa2_ddr_8000`. |
| 79 | `    t = tarfile.open(f'{KIT}/asct_run_results_{name}.tar.gz')` | `t`: opens the result archive of this run, `asct_run_results_NAME.tar.gz`, in the folder `KIT`. |
| 80 | `    base = f'asct_run_results_{name}/raw'` | `base`: the folder `raw` inside the archive. |
| 81 | `    def js(p):` | Defines the helper `js`. It reads one JSON file below `base` from the archive. |
| 82 | `        return json.load(t.extractfile(f'{base}/{p}'))` | The body of `js`: `extractfile` gives the file inside the archive, and `json.load` reads it. |
| 83 | `    bs = js('bandwidth-sweep/bandwidth-sweep.ubench.json')` | `bs`: the result file of the ASCT benchmark `bandwidth-sweep`, which measures one core at many buffer sizes. |
| 84 | `    sweep = sorted((int(bs['sizes'][k]), bs['total_bandwidth_mbps'][k] / 1e3) for k in bs['sizes'])` | `sweep`: a sorted list of pairs, one per buffer size of the sweep: the size in bytes and the total rate in GB/s. The rate is the value `total_bandwidth_mbps` of the same key divided by 1e3, which turns MB/s into GB/s. |
| 85 | `    meta = js('bandwidth-sweep/metadata.json')` | `meta`: the file `metadata.json` of the same benchmark. It holds the settings of the vendor run. |
| 86 | `    txt = open(f'{KIT}/asct_run_output_{name}.txt').read()` | `txt`: the whole console output of the vendor run, the file `asct_run_output_NAME.txt` in the folder `KIT`. |
| 87 | `    def grab(pat):` | Defines the helper `grab`. It searches a pattern in `txt` and returns the text of group 1. |
| 88 | `        m = re.search(pat, txt)` | The body of `grab`: `re.search` finds the first place where the pattern matches. |
| 89 | `        return m.group(1).strip() if m else None` | Returns group 1 without spaces at its ends, or `None` when the pattern was not found. |
| 90 | `    ll = re.findall(r'^\s+(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$', txt.split('LOADED-LATENCY')[1].split('C2C-LATENCY')[0], re.M)` | `ll`: the rows of the table "loaded latency". The line cuts the text between the headings `LOADED-LATENCY` and `C2C-LATENCY`. The pattern matches a line that holds only four numbers: an integer and three decimal numbers. The groups hold the injected NOPs, the latency in ns, the bandwidth in GB/s and a percentage [Ref3]. `re.M` lets the pattern test each line alone. |
| 91 | `    pk = re.findall(r'^\s*(All Reads\|3:1 Reads-Writes\|2:1 Reads-Writes\|1:1 Reads-Writes\|2:1 Rd-Wr \(Non-Temporal\))\s+([0-9.]+)\s+([0-9.]+)', txt, re.M)` | `pk`: the rows of the table of the peak bandwidth. The pattern matches a line that starts with one of five traffic types, from `All Reads` to `2:1 Rd-Wr (Non-Temporal)`, and then holds two numbers. The groups hold the traffic type, the bandwidth in GB/s and a percentage [Ref3]. |
| 92 | `    cn = re.findall(r'^Node (\d)\s+([0-9.]+)\s+([0-9.]+)\s*$', txt.split('CROSS-NUMA-BANDWIDTH')[1].split('LATENCY-SWEEP')[0], re.M)` | `cn`: the rows of the table of the bandwidth between NUMA nodes. The line cuts the text between the headings `CROSS-NUMA-BANDWIDTH` and `LATENCY-SWEEP`. The pattern matches a line that starts with `Node`, has one digit and then two numbers. The groups hold the node and the two bandwidths in GB/s [Ref3]. |
| 93 | `    vend[name] = {'sweep': sweep, 'cpu': meta['config']['target_cpus'], 'duration': meta['config']['duration'],` | Starts the entry of this vendor run. `sweep`: the list of line 84. `cpu`: the CPU of the sweep, from the settings in `meta`. `duration`: the length of the measured phase, from the same settings. |
| 94 | `                  'binary': meta['benchmark_binary'], 'cpus': grab(r'CPUs:\s+(\d+)'), 'numa': grab(r'NUMA nodes:\s+(\d+)'),` | `binary`: the name of the benchmark binary, from `meta`. `cpus`: the number that follows `CPUs:` in the console output. `numa`: the number that follows `NUMA nodes:`. |
| 95 | `                  'bios': grab(r'Version:\s+(AGI-CPU-CRB-\S+)'), 'speed': grab(r'Speed:\s+(\d+)'),` | `bios`: the text that follows `Version:` and starts with `AGI-CPU-CRB-`, which is the firmware version. `speed`: the number that follows `Speed:`, the memory speed. |
| 96 | `                  'channels': grab(r'# of channels:\s+(\d+)'), 'board': grab(r'Version:\s+(EVT\d)'),` | `channels`: the number that follows `# of channels:`. `board`: the text `EVT` with one digit that follows `Version:`. |
| 97 | `                  'kernel_cfg': grab(r'Config:\s+(\S+)'), 'thp': grab(r'Transparent HP:\s+(\S+)'),` | `kernel_cfg`: the word that follows `Config:`, the path of the configuration file of the Linux kernel. `thp`: the word that follows `Transparent HP:`, the setting of transparent huge pages. |
| 98 | `                  'nops': [[int(a), float(b), float(c)] for a, b, c, _ in ll],` | `nops`: one list per row of `ll`: the injected NOPs as an integer, the latency and the bandwidth as numbers. The percentage is dropped. |
| 99 | `                  'peak': {a: [float(b), float(c)] for a, b, c in pk},` | `peak`: a dictionary from the traffic type to its bandwidth and its percentage. |
| 100 | `                  'cross_numa': [[float(b), float(c)] for _, b, c in cn]}` | `cross_numa`: one list per row of `cn` with the two bandwidths. The node number is dropped. The closing brace ends the entry. |
| 101 | `out['vendor'] = vend` | Stores the result of block 4 under the key `vendor` of the output. |

### The output file and a short report (lines 102 to 109)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `json.dump(out, open(sys.argv[1], 'w'), indent=1)` | Writes `out` as a JSON file to the path of argument 1, with an indent of 1 space per level. |
| 103 | `print('single cells', len(single), 'zs cells', len(out['zs']), 'first', len(out['first']))` | Prints three counts: the cells of `single`, the cells of `zs` and the entries of `first`. |
| 104 | `for k in ('oldread.2.8388608', 'asmread.2.8388608', 'read.2.8388608', 'oldread.41.1048576', 'asmread.41.1048576'):` | Starts a loop over five keys of `single`: three kernels on CPU 2 at 8388608 bytes (8 MiB) and two kernels on CPU 41 at 1048576 bytes (1 MiB). |
| 105 | `    print(k, single.get(k))` | Prints the key and its entry, or `None` when `single` has no such key. |
| 106 | `print({k: v for k, v in out['first'].items() if '.2.' in k})` | Prints the entries of `first` whose key holds `.2.`, which are those of CPU 2. |
| 107 | `for n, v in vend.items():` | Starts a loop over the two vendor runs. |
| 108 | `    print(n, v['cpus'], v['numa'], v['bios'], v['speed'], v['channels'], v['board'], v['cpu'], v['peak'].get('All Reads'), v['cross_numa'], v['nops'][-3:])` | Prints one line per vendor run: the number of CPUs, the NUMA nodes, the firmware version, the memory speed, the channels, the board, the CPU of the sweep, the entry `All Reads` of `peak`, the values between NUMA nodes and the last three rows of `nops`. |
| 109 | `    print('   sweep 1M 8M:', [x for x in v['sweep'] if x[0] in (1048576, 8388608, 4194304, 16777216, 33554432, 268435456, 1073741824, 32768)])` | Prints the sweep values of this vendor run for eight buffer sizes, from 32768 bytes (32 KiB) to 1073741824 bytes (1 GiB). The label of the line names only 1M and 8M. |

## References

- [Ref1] `FINDINGS.md` in the folder `w120-2026-11-15`: the sections "The question", F2, F4 and F5.
- [Ref2] `one-thread.csv` in the result folder `kernels-20261113T181222Z` of the test folder `2026-11-13-new-read-kernel`: the header lines, the comment line with the definition of `aggregate_GBps`, and the column titles.
- [Ref3] The console outputs of the vendor runs in the welcome kit of Arm, folder `tools/asct/reports`: the files `asct_run_output_a0_numa2_ddr_7200.txt` and `asct_run_output_a1_numa2_ddr_8000.txt`, with the headings and the column titles of the tables.
