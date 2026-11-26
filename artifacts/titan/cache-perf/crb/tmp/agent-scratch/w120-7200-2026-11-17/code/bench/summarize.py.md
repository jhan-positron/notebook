# `summarize.py` explained, line by line

- Source file: `bench/summarize.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 174 lines, 6742 bytes).
- sha256 of the source when this page was built: `9b1bac8d6ed5a6f52e23864760eb75b00fd8f7a9328a3fd7fd865892f3b7c997`.

## Short version: purpose

`summarize.py` reads one result folder of the script `run_crb.sh` and prints three groups of Markdown tables. The tables show the latency per buffer size with the counter events per load, the bandwidth per buffer size and thread count, and one summary row per cache level. It measures nothing itself.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`latency`**: the benchmark that follows a chain of pointers through a buffer with one thread. It prints one row per timed interval and one `best` row per buffer size, in nanoseconds per load.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. It prints one row per repetition, with the total rate and the smallest and the largest rate of a single thread.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Load**: one read of a pointer in `latency`.
- **`best` row**: the row that `latency` prints with the smallest ns per load of a buffer size.
- **Total rate**: the column `aggregate_GBps` of `bandwidth`: the bytes of all threads divided by the time of the slowest thread, in GB/s.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Short run, long run**: two runs of `latency` under `perf stat` that differ only in the number of timed loads.
- **Refill**: a line that is brought into a cache from outside.
- **Case**: `run_crb.sh` names its bandwidth runs by the place where the buffers fit: L1, L2, L3 or DRAM. The source calls a case a regime.
- **L1, L2, L3, DRAM**: the cache of level 1 and of level 2 of one core, the last cache level, and the main memory.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Clock cycles**: the latency in ns times the clock rate of the cores in GHz.
- **Markdown**: a plain text format in which a table is written with vertical bars.
- **GB**: 1e9 bytes.
- **KiB, MiB, GiB**: 1024 bytes, 1048576 bytes and 1073741824 bytes.

## Main flow

1. Read the arguments: the result folder and the option `--ghz`, the clock rate of the cores (lines 97 to 105).
2. Read the input files: `latency.csv`, the count files and the load numbers of the short and the long runs, and `bandwidth.csv` (lines 107 to 114).
3. Print the latency table: one row per buffer size with the best ns per load, the clock cycles and 5 events per load (lines 116 to 137).
4. Print one bandwidth table per buffer size per thread: for each kernel the best total rate and the range of the per-thread rates, per thread count (lines 139 to 150).
5. Print the summary: one row per cache level with its latency and its read, write and copy rates (lines 152 to 170).

## Behavior a reader must know

- Latency per size: the `best` row of `latency.csv`, column 4. `latency` formed that minimum over its timed intervals.
- Events per load: the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. The counts are field 1 of the files `latency-perf-SIZE-short.csv` and `latency-perf-SIZE-long.csv`. The loads are column 3 of the `best` rows of `latency-perfrun-short.csv` and `latency-perfrun-long.csv`. A missing value gives `n/a`.
- The script does not read the share of the time for which a counter was running (field 5 of a line of `perf stat`).
- Bandwidth per run: of the repetition rows of `bandwidth.csv`, the script keeps the repetition with the highest total rate (column 7), together with the smallest and the largest per-thread rate of that same repetition (columns 8 and 9). It does not use the `best` rows of `bandwidth`.
- Only the kernels `read`, `write` and `copy` are read. Rows of other kernels are skipped.
- Latency of a level: the smallest best value of the sizes in the range of the level: 16 KiB to 32 KiB for L1, 256 KiB to 1 MiB for L2, 8 MiB to 64 MiB for L3, and 1 GiB to 2 GiB for DRAM.
- Rate of a level: the highest best total rate of all runs whose size per thread belongs to the level (32 KiB, 1 MiB, 8 MiB, and 256 MiB or 1 GiB), over all thread counts. The cell also shows the rate of the run with 1 thread.
- Clock cycles are computed, not measured: ns times the value of `--ghz`, which is 2.8 by default.
- With no argument or more than one argument the script prints its description text and ends with exit status 1.

## Source and explanation, line by line

- Text shown: the file `bench/summarize.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (174 lines, 6742 bytes, sha256 `9b1bac8d6ed5a6f52e23864760eb75b00fd8f7a9328a3fd7fd865892f3b7c997`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text and imports (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""summarize.py - print markdown tables from a run_crb.sh results directory.` | Starts the description text of the file. The script prints Markdown tables from one result folder of `run_crb.sh`. |
| 4 | `usage: summarize.py RESULTS_DIR [--ghz 2.8]` | Text of the description: the usage. The argument is the result folder. The option `--ghz` gives the clock rate of the cores in GHz, with 2.8 as the example. |
| 5 | `"""` | Ends the description text. |
| 6 | `import glob` | Loads the module `glob`, which finds files by a name pattern. |
| 7 | `import os` | Loads the module `os`, for paths and file tests. |
| 8 | `import sys` | Loads the module `sys`, for the arguments and the exit of the script. |

### The tables of cache levels, bandwidth cases and counter events (lines 10 to 20)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `LEVELS = [  # name, min size, max size (bytes) for the latency plateau pick` | `LEVELS`: for each cache level a name and a range of buffer sizes in bytes. By the comment the latency of a level is taken from the sizes of this range, where the curve of the latency is flat (the comment says plateau). |
| 11 | `    ("L1", 16 << 10, 32 << 10),` | L1: the sizes from 16 KiB to 32 KiB. `16 << 10` is 16 times 1024. |
| 12 | `    ("L2", 256 << 10, 1 << 20),` | L2: the sizes from 256 KiB to 1 MiB. |
| 13 | `    ("L3", 8 << 20, 64 << 20),` | L3: the sizes from 8 MiB to 64 MiB. L3 is the last cache level, which the project calls SLC. |
| 14 | `    ("DRAM", 1 << 30, 2 << 30),` | DRAM, the main memory: the sizes from 1 GiB to 2 GiB. |
| 15 | `]` | Ends the list `LEVELS`. |
| 16 | `REGIME_BY_BYTES = {32 << 10: "L1", 1 << 20: "L2", 8 << 20: "L3", 256 << 20: "DRAM", 1 << 30: "DRAM"}` | `REGIME_BY_BYTES`: a dictionary from the buffer size per thread of a bandwidth run to the name of its case: 32 KiB is L1, 1 MiB is L2, 8 MiB is L3, and 256 MiB and 1 GiB are DRAM. These are the sizes of the full plan of `run_crb.sh`. |
| 17 | `PERF_EVENTS = ["l1d_cache_refill", "l2d_cache_refill", "l3d_cache_refill",` | `PERF_EVENTS`: the names of the 7 counter events of `run_crb.sh`. This line holds the refills of the data caches of level 1, 2 and 3. |
| 18 | `               "ll_cache_miss_rd", "dtlb_walk", "cpu_cycles", "inst_retired"]` | Continues the list: read misses of the last cache level, walks of the page table for data accesses, processor cycles and executed instructions. |

### Functions `parse_size` and `fmt_size`: sizes as numbers and as short texts (lines 21 to 35)

| Line | Source | Explanation |
|---:|---|---|
| 21 | `def parse_size(tok):` | Starts the function `parse_size`. It turns a size text such as `1.5M` into a number of bytes. |
| 22 | `    mul = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}` | `mul`: the factors of the letters: 1024 for `K`, 1048576 for `M` and 1073741824 for `G`. |
| 23 | `    if tok[-1].upper() in mul:` | Tests whether the last character, as a capital letter, is one of these letters. |
| 24 | `        return int(float(tok[:-1]) * mul[tok[-1].upper()])` | Then returns the number before the letter times the factor, as a whole number. |
| 25 | `    return int(tok)` | A text without a letter is a number of bytes. |
| 28 | `def fmt_size(b):` | Starts the function `fmt_size`. It turns a number of bytes into a short text such as `8M` or `1.5M`. |
| 29 | `    for unit, div in (("G", 1 << 30), ("M", 1 << 20), ("K", 1 << 10)):` | Loop over the three units, from the largest to the smallest: `G`, `M` and `K`. |
| 30 | `        if b % div == 0 or b >= div:` | Tests whether the size is a multiple of the unit, or at least as large as the unit. |
| 31 | `            v = b / div` | `v`: the size divided by the unit. |
| 32 | `            return ("%g%s" % (v, unit))` | Returns the value and the letter of the unit. `%g` prints the number without useless zeros, so 1572864 bytes become `1.5M`. |
| 33 | `    return str(b)` | A size below 1024 bytes is returned as a plain number. |

### Function `csv_rows`: the data rows of a CSV file (lines 36 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 36 | `def csv_rows(path):` | Starts the function `csv_rows`. It gives the rows of a file one after the other, each as a list of fields. |
| 37 | `    with open(path) as f:` | Opens the file. `with` closes it at the end. |
| 38 | `        for line in f:` | Loop over the lines of the file. |
| 39 | `            line = line.strip()` | Removes the line end and the spaces at both ends. |
| 40 | `            if not line or line.startswith("#"):` | Tests for an empty line and for a comment line, which starts with `#`. |
| 41 | `                continue` | Then skips the line. |
| 42 | `            yield line.split(",")` | Gives the fields of the line, split at the commas, to the caller (`yield`). The function goes on with the next line when the caller asks for the next row. |

### Function `read_latency`: the `best` row of each buffer size (lines 45 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `def read_latency(path):` | Starts the function `read_latency`. It reads an output file of the program `latency`. |
| 46 | `    """size_bytes -> (best ns/load, loads)"""` | Description text of the function: the result maps the size in bytes to the pair of the best ns per load and the loads. |
| 47 | `    best = {}` | `best`: the result dictionary. |
| 48 | `    if not os.path.exists(path):` | Tests whether the file does not exist. |
| 49 | `        return best` | Then returns the empty dictionary. |
| 50 | `    for r in csv_rows(path):` | Loop over the data rows of the file (`csv_rows`). |
| 51 | `        if len(r) == 4 and r[1] == "best":` | Tests whether the row has 4 fields and its second field is `best`. `latency` prints one such row per size, with the smallest ns per load of its timed intervals. |
| 52 | `            best[int(r[0])] = (float(r[3]), int(r[2]))` | Then stores, under the size (field 1), the pair of the ns per load (field 4) and the number of loads (field 3). |
| 53 | `    return best` | Returns the dictionary. |

### Function `read_perf`: the counts of the short or of the long runs (lines 56 to 71)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `def read_perf(outdir, run):` | Starts the function `read_perf`. `outdir` is the result folder. `run` is `short` or `long`. |
| 57 | `    """size_bytes -> {event: count} for the 'short' or 'long' perf run;` | Description text of the function: the result maps the size in bytes to a dictionary from the event to the count, for the short or for the long run under `perf`. |
| 58 | `    perf stat -x, lines are value,unit,event,..."""` | The description goes on: a line that `perf stat -x,` writes has the fields value, unit, event and more. |
| 59 | `    perf = {}` | `perf`: the result dictionary. |
| 60 | `    suffix = "-%s.csv" % run` | `suffix`: the end of the file names: `-short.csv` or `-long.csv`. |
| 61 | `    for path in glob.glob(os.path.join(outdir, "latency-perf-*" + suffix)):` | Loop over the files of the folder whose names start with `latency-perf-` and end with the suffix (`glob.glob`). These are the count files, one per size. |
| 62 | `        tok = os.path.basename(path)[len("latency-perf-"):-len(suffix)]` | `tok`: the size text in the file name: the part between `latency-perf-` and the suffix. |
| 63 | `        counts = {}` | `counts`: the counts of this file. |
| 64 | `        for r in csv_rows(path):` | Loop over the data rows of the file. |
| 65 | `            if len(r) >= 3 and r[0].replace(".", "").isdigit():` | Tests whether the row has at least 3 fields and its first field is a number: only digits remain when the dots are removed. A row whose count is the text `<not counted>` fails this test. |
| 66 | `                counts[r[2].split(":")[0]] = float(r[0])` | Then stores the count as a decimal number under the event name. `split(":")[0]` keeps the name up to the first colon, so a suffix such as `:u` is dropped. |
| 67 | `        if counts:` | Tests whether the file gave at least one count. |
| 68 | `            perf[parse_size(tok)] = counts` | Then stores the counts under the size in bytes (`parse_size`). |
| 69 | `    return perf` | Returns the dictionary. The function does not read the fifth field of a row, the share of the time for which the counter was running. |

### Function `read_bandwidth`: the best repetition of each bandwidth run (lines 72 to 87)

| Line | Source | Explanation |
|---:|---|---|
| 72 | `def read_bandwidth(path):` | Starts the function `read_bandwidth`. It reads the output file of the program `bandwidth`. |
| 73 | `    """(bytes, kernel, threads) -> (best aggregate GB/s, per-thread min, max of the best rep)"""` | Description text of the function: the result maps the triple of bytes, kernel and threads to the best total rate in GB/s and to the smallest and the largest rate of a single thread in that repetition. |
| 74 | `    best = {}` | `best`: an empty dictionary. Only line 76 returns it. |
| 75 | `    if not os.path.exists(path):` | Tests whether the file does not exist. |
| 76 | `        return best` | Then returns the empty dictionary. |
| 77 | `    reps = {}` | `reps`: the result dictionary. |
| 78 | `    for r in csv_rows(path):` | Loop over the data rows of the file. |
| 79 | `        if len(r) < 9 or r[0] not in ("read", "write", "copy") or r[3] == "best":` | Tests for a row with fewer than 9 fields, for a row whose first field is not `read`, `write` or `copy`, and for a `best` row. So the header row and the rows of other kernels are skipped, and the rows of the single repetitions remain. |
| 80 | `            continue` | Then skips the row. |
| 81 | `        key = (int(r[2]), r[0], int(r[1]))` | `key`: the triple of the bytes per thread (field 3), the kernel (field 1) and the thread count (field 2). |
| 82 | `        agg = float(r[6])` | `agg`: the total rate of this repetition in GB/s (field 7, the column `aggregate_GBps`). It is the bytes of all threads divided by the time of the slowest thread. |
| 83 | `        if key not in reps or agg > reps[key][0]:` | Tests whether this is the first repetition of the key or one with a higher total rate. |
| 84 | `            reps[key] = (agg, float(r[7]), float(r[8]))` | Then keeps its total rate together with the smallest and the largest rate of a single thread of the same repetition (fields 8 and 9). |
| 85 | `    return reps` | Returns the dictionary: for each key the repetition with the highest total rate. |

### Function `table`: print one Markdown table (lines 88 to 95)

| Line | Source | Explanation |
|---:|---|---|
| 88 | `def table(headers, rows):` | Starts the function `table`. It prints one Markdown table. `headers` is the list of the column titles. `rows` is the list of the rows. |
| 89 | `    print("\| " + " \| ".join(headers) + " \|")` | Prints the title row: the titles with a vertical bar between them and at both ends. |
| 90 | `    print("\|" + "\|".join("---" for _ in headers) + "\|")` | Prints the separator row of a Markdown table: three hyphens per column. |
| 91 | `    for row in rows:` | Loop over the rows. |
| 92 | `        print("\| " + " \| ".join(str(c) for c in row) + " \|")` | Prints the row: each cell as text, with vertical bars as in the title row. |
| 93 | `    print()` | Prints an empty line after the table. |

### Function `main`: the arguments and the input files (lines 96 to 115)

| Line | Source | Explanation |
|---:|---|---|
| 96 | `def main():` | Starts the function `main`. |
| 97 | `    args = sys.argv[1:]` | `args`: the arguments of the command line without the script name. |
| 98 | `    ghz = 2.8` | `ghz`: the clock rate of the cores in GHz. The default is 2.8. |
| 99 | `    if "--ghz" in args:` | Tests whether the option `--ghz` is among the arguments. |
| 100 | `        i = args.index("--ghz")` | `i`: the place of the option in the list. |
| 101 | `        ghz = float(args[i + 1])` | Reads the value after the option as a decimal number. |
| 102 | `        del args[i:i + 2]` | Removes the option and its value from the list. |
| 103 | `    if len(args) != 1:` | Tests whether not exactly one argument is left. |
| 104 | `        sys.exit(__doc__)` | Then prints the description text of the file and ends the script with exit status 1 (`sys.exit` with a text). |
| 105 | `    outdir = args[0]` | `outdir`: the result folder. |
| 107 | `    lat = read_latency(os.path.join(outdir, "latency.csv"))` | `lat`: for each size, the best ns per load and its loads, from `latency.csv` (`read_latency`). |
| 108 | `    # Two perf runs per size with identical setup and different timed-load` | Comment: there are two runs under `perf` per size. Their setup is the same, and their numbers of timed loads differ. |
| 109 | `    # counts: the difference of the counts over the difference of the loads` | Comment: so the difference of the counts divided by the difference of the loads ... |
| 110 | `    # is the per-load rate of the timed chase alone.` | Comment: ... is the rate per load of the timed chase alone. |
| 111 | `    perf = {run: read_perf(outdir, run) for run in ("short", "long")}` | `perf`: the counts of the short runs and of the long runs (`read_perf`), in a dictionary with the keys `short` and `long`. |
| 112 | `    perf_loads = {run: {s: v[1] for s, v in read_latency(` | `perf_loads`: for `short` and for `long`, a dictionary from the size to the number of loads. The loads are the third field of the `best` rows of the files of line 113. |
| 113 | `        os.path.join(outdir, "latency-perfrun-%s.csv" % run)).items()} for run in ("short", "long")}` | Continues the statement of line 112: the files are `latency-perfrun-short.csv` and `latency-perfrun-long.csv`, the output of `latency` in the runs under `perf`. |
| 114 | `    bw = read_bandwidth(os.path.join(outdir, "bandwidth.csv"))` | `bw`: the best repetition of each bandwidth run, from `bandwidth.csv` (`read_bandwidth`). |

### Function `main`: the latency table (lines 116 to 138)

| Line | Source | Explanation |
|---:|---|---|
| 116 | `    print("## Latency (single thread, dependent loads, CPU pinned)\n")` | Prints the title of the first section: latency with a single thread, dependent loads, and the thread pinned to a CPU. |
| 117 | `    print("ns/load = best (minimum) over reps; cycles = ns x %.2f GHz; refills/load = "` | Prints a note below the title. First part: `ns/load` is the best value of the repetitions, which is the minimum. `cycles` is the ns value times the clock rate. The note shows the clock rate with 2 decimals. |
| 118 | `          "(count_long - count_short) / (loads_long - loads_short) from the two perf runs, "` | Second part of the note: `refills/load` is the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. |
| 119 | `          "so setup and warm-up cancel.\n" % ghz)` | Third part of the note: so the setup and the warm-up cancel. `% ghz` puts the clock rate into the text. |
| 120 | `    headers = ["size", "ns/load", "cycles"] + [e.replace("_cache_refill", "_refill") + "/load"` | `headers`: the column titles: `size`, `ns/load`, `cycles`, and then one column per event. The list expression of lines 120 to 121 builds the event titles: `_cache_refill` is shortened to `_refill`, and `/load` is added. |
| 121 | `                                                for e in PERF_EVENTS if e not in ("cpu_cycles", "inst_retired")]` | Continues the list expression: it leaves out the events `cpu_cycles` and `inst_retired`. So 5 event columns remain. |
| 122 | `    rows = []` | `rows`: the rows of the table. |
| 123 | `    for size in sorted(lat):` | Loop over the buffer sizes of `latency.csv`, from the smallest to the largest. |
| 124 | `        ns, _ = lat[size]` | `ns`: the best ns per load of this size. |
| 125 | `        row = [fmt_size(size), "%.2f" % ns, "%.1f" % (ns * ghz)]` | Starts the row: the size as a short text, the ns per load with 2 decimals, and the latency in clock cycles with 1 decimal. The cycles are the ns value times `ghz`: 1 ns at 2.8 GHz is 2.8 cycles. |
| 126 | `        c_short, c_long = perf["short"].get(size), perf["long"].get(size)` | `c_short`, `c_long`: the counts of the short and of the long run of this size, or `None` when a file is missing. |
| 127 | `        l_short, l_long = perf_loads["short"].get(size), perf_loads["long"].get(size)` | `l_short`, `l_long`: the numbers of loads of the short and of the long run. |
| 128 | `        for e in PERF_EVENTS:` | Loop over the events. |
| 129 | `            if e in ("cpu_cycles", "inst_retired"):` | Tests for the two events that get no column. |
| 130 | `                continue` | Then skips the event. |
| 131 | `            if c_short and c_long and l_short and l_long and l_long > l_short \` | Tests whether all four values exist, the long run has more loads than the short run, ... |
| 132 | `                    and e in c_short and e in c_long:` | ... and both runs have a count for this event. |
| 133 | `                row.append("%.3f" % ((c_long[e] - c_short[e]) / (l_long - l_short)))` | Then adds the events per load with 3 decimals: the difference of the counts divided by the difference of the loads. |
| 134 | `            else:` | The other case: a value is missing. |
| 135 | `                row.append("n/a")` | Then adds the text `n/a`. |
| 136 | `        rows.append(row)` | Adds the row to the table. |
| 137 | `    table(headers, rows)` | Prints the table (`table`). |

### Function `main`: one bandwidth table per buffer size (lines 139 to 151)

| Line | Source | Explanation |
|---:|---|---|
| 139 | `    print("## Bandwidth (GB = 1e9 bytes; best aggregate over reps)\n")` | Prints the title of the second section: bandwidth, with GB as 1e9 bytes, and the best total rate of the repetitions. |
| 140 | `    for bytes_ in sorted({k[0] for k in bw}):` | Loop over the buffer sizes per thread that occur in `bandwidth.csv`, from the smallest to the largest. The expression in braces builds the set of the sizes. |
| 141 | `        regime = REGIME_BY_BYTES.get(bytes_, "bytes=" + fmt_size(bytes_))` | `regime`: the name of the case of this size from `REGIME_BY_BYTES`. A size that is not in that dictionary gets the text `bytes=` and the size. |
| 142 | `        print("### %s regime: %s per thread\n" % (regime, fmt_size(bytes_)))` | Prints the title of the table: the case and the size per thread. |
| 143 | `        threads = sorted({k[2] for k in bw if k[0] == bytes_})` | `threads`: the thread counts that occur for this size, sorted. |
| 144 | `        headers = ["kernel"] + ["%dT agg" % t for t in threads] + ["%dT per-thr min..max" % t for t in threads]` | `headers`: the column titles: `kernel`, then one column per thread count for the total rate (`agg`), then one column per thread count for the smallest and the largest rate of a single thread. |
| 145 | `        rows = []` | `rows`: the rows of the table. |
| 146 | `        for kern in ("read", "write", "copy"):` | Loop over the three kernels `read`, `write` and `copy`. |
| 147 | `            agg = ["%.1f" % bw[(bytes_, kern, t)][0] if (bytes_, kern, t) in bw else "n/a" for t in threads]` | `agg`: for each thread count, the best total rate in GB/s with 1 decimal, or `n/a` when the run does not exist. |
| 148 | `            per = ["%.1f..%.1f" % bw[(bytes_, kern, t)][1:] if (bytes_, kern, t) in bw else "n/a" for t in threads]` | `per`: for each thread count, the smallest and the largest rate of a single thread in that best repetition, in the form `MIN..MAX`, or `n/a`. |
| 149 | `            rows.append([kern] + agg + per)` | Adds the row: the kernel, the total rates and the per-thread ranges. |
| 150 | `        table(headers, rows)` | Prints the table. |

### Function `main`: the summary by cache level, and the start of the script (lines 152 to 174)

| Line | Source | Explanation |
|---:|---|---|
| 152 | `    print("## Levels summary\n")` | Prints the title of the third section: the summary by level. |
| 153 | `    rows = []` | `rows`: the rows of the table. |
| 154 | `    for name, lo, hi in LEVELS:` | Loop over the four levels of `LEVELS`. |
| 155 | `        picks = [lat[s][0] for s in lat if lo <= s <= hi]` | `picks`: the best ns per load of every size of `latency.csv` that lies in the size range of the level. |
| 156 | `        ns = min(picks) if picks else None` | `ns`: the smallest of these values, or `None` when no size lies in the range. |
| 157 | `        lat_s = "%.2f ns (%.1f cycles)" % (ns, ns * ghz) if ns else "n/a (no size in %s..%s)" % (fmt_size(lo), fmt_size(hi))` | `lat_s`: the latency cell: the ns value with 2 decimals and the clock cycles with 1 decimal. Without a value the cell reads `n/a` with the size range. |
| 158 | `        regime_bytes = [b for b, r in REGIME_BY_BYTES.items() if r == name]` | `regime_bytes`: the buffer sizes per thread that `REGIME_BY_BYTES` gives to this level. |
| 159 | `        cells = [name, lat_s]` | `cells`: the row. It starts with the name of the level and the latency cell. |
| 160 | `        for kern in ("read", "write", "copy"):` | Loop over the three kernels. |
| 161 | `            keys = [k for k in bw if k[1] == kern and k[0] in regime_bytes]` | `keys`: the bandwidth runs of this kernel whose size belongs to the level. |
| 162 | `            if not keys:` | Tests whether there is no such run. |
| 163 | `                cells.append("n/a")` | Then adds the cell `n/a`. |
| 164 | `                continue` | And goes on with the next kernel. |
| 165 | `            kmax = max(keys, key=lambda k: bw[k][0])` | `kmax`: the run with the highest best total rate, over all thread counts and sizes of the level. |
| 166 | `            ones = [k for k in keys if k[2] == 1]` | `ones`: the runs of the level with 1 thread. |
| 167 | `            one = bw[ones[0]] if ones else None` | `one`: the values of the first of them, or `None` when there is none. |
| 168 | `            cells.append("%.1f @%dT, 1T=%s" % (bw[kmax][0], kmax[2], "%.1f" % one[0] if one else "n/a"))` | Adds the cell: the highest total rate with 1 decimal, the thread count of that run after `@`, and the rate of the run with 1 thread after `1T=`. |
| 169 | `        rows.append(cells)` | Adds the row to the table. |
| 170 | `    table(["level", "latency (best)", "read GB/s", "write GB/s", "copy GB/s"], rows)` | Prints the table with the titles level, latency, and the rates of read, write and copy in GB/s. |
| 173 | `if __name__ == "__main__":` | Tests whether the file was started as a script and not loaded as a module. |
| 174 | `    main()` | Then calls `main`. |
