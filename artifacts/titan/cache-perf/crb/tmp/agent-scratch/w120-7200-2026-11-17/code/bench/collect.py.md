# `collect.py` explained, line by line

- Source file: `bench/collect.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 123 lines, 5346 bytes).
- sha256 of the source when this page was built: `b6ca2a74bf83be62c416e597509bfe3e6263d393c40942570dcc245bbf028cf8`.

## Short version: purpose

`collect.py` reads the result folders of the first test scripts and prints one JSON text with their numbers, for the report. It takes the best latency per buffer size, the best rate per bandwidth run, and the counter events per load. It measures nothing itself.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Main folder**: a result folder of the script `run_crb.sh`.
- **Follow-up folder**: a result folder of the script `run_followup.sh`.
- **Uncore folder**: a result folder of the script `run_uncore.sh`, which counts events of the mesh.
- **JSON**: a text format for structured data.
- **`latency`**: the benchmark that follows a chain of pointers through a buffer with one thread. It prints one row per timed interval and one `best` row per buffer size, in nanoseconds per load.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. It prints one row per repetition and one `best` row per kernel, with the rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`best` row**: the row that a benchmark prints with its best value: the smallest ns per load of `latency`, or the highest rate of `bandwidth`.
- **Load**: one read of a pointer in `latency`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events for it.
- **Short run, long run**: two runs of the same benchmark under `perf stat` that differ only in the number of timed loads.
- **Mesh**: the network inside one half of the chip that connects the cores, the last cache level and the memory. It has counters of its own.
- **`AnonHugePages`**: a value that Linux reports for a process: the memory without a file behind it that lies on 2 MiB pages, in kB.
- **Rate**: bytes divided by time, in GB/s.
- **GB**: 1e9 bytes.

## Main flow

1. Read the three folder names from the arguments. The second and the third are optional (lines 89 to 92).
2. Main folder: read `latency.csv` and keep the `best` value per size, the rows of the single intervals and the `AnonHugePages` values (lines 93 to 96).
3. Main folder: compute the core events per load from the short and the long run of each size (`refills_per_load` divides the difference of the counts by the difference of the loads) (line 97).
4. Main folder: read the `best` rows of `bandwidth.csv` (line 98).
5. Follow-up folder, when given: read `latency-fresh.csv`, the three bandwidth files `pair.csv`, `asm.csv` and `dram.csv`, and the blocks of `latency-bycpu.csv` (lines 99 to 115).
6. Uncore folder, when given: compute the mesh events per load, and read the counts and the rates of the two streaming read runs (lines 116 to 120).
7. Print everything as JSON text to the standard output (line 121).

## Behavior a reader must know

- Latency numbers come from the `best` rows: column 4 (ns per load) under column 1 (size in bytes). The benchmark itself formed that minimum.
- Bandwidth numbers come from the `best` rows: column 7 (the total rate in GB/s), with the kernel, the thread count and the bytes per thread from the columns 1 to 3. The title line before a run is kept as the context of the row.
- Events per load: the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. A count is field 1 of a line of `perf stat`, under the event name in field 3. The loads are column 3 of the `best` rows.
- The script does not read the share of the time for which a counter was running (field 5 of a line of `perf stat`). So it does not notice a multiplexed counter, whose count is a scaled value.
- An event whose count is not a number, for example `<not counted>`, gets no rate. A size gets no rates when a file is missing or when the long run has no more loads than the short run.
- For the two streaming read runs of the uncore folder, the counts are stored unchanged, without a subtraction.
- The script writes no file. The caller sends the output to a file.
- A missing `latency.csv` or `bandwidth.csv` in the main folder stops the script with a Python error.

## Source and explanation, line by line

- Text shown: the file `bench/collect.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (123 lines, 5346 bytes, sha256 `b6ca2a74bf83be62c416e597509bfe3e6263d393c40942570dcc245bbf028cf8`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text and imports (lines 1 to 7)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""collect.py - merge CRB result directories into one JSON for the report.` | Starts the description text of the file. The script merges result folders of CRB into one JSON file for the report. CRB is the Arm reference server under test. JSON is a text format for structured data. |
| 4 | `usage: collect.py MAIN_DIR [FOLLOWUP_DIR] [UNCORE_DIR] > data.json` | Text of the description: the usage. The first argument is the main result folder. The follow-up folder and the uncore folder are optional. The JSON text goes to the standard output. The example sends it to a file `data.json`. |
| 5 | `"""` | Ends the description text. |
| 6 | `import csv, glob, json, os, re, sys` | Loads six standard modules. The code uses `json` (write JSON), `os` (paths and file tests), `re` (regular expressions) and `sys` (arguments and standard output). No line uses `csv` or `glob`. |

### Function `parse_bytes`: read a size such as `1.5M` (lines 8 to 12)

| Line | Source | Explanation |
|---:|---|---|
| 8 | `def parse_bytes(s):` | Starts the function `parse_bytes`. It turns a size text such as `1.5M` into a number of bytes. |
| 9 | `    m = re.fullmatch(r'([0-9.]+)([KMG]?)', s)` | `m`: the match of the whole text against a pattern. Group 1 is a number made of digits and dots. Group 2 is one of the capital letters `K`, `M` and `G`, or nothing. |
| 10 | `    v = float(m.group(1)); mul = {'': 1, 'K': 1 << 10, 'M': 1 << 20, 'G': 1 << 30}[m.group(2)]` | `v`: the number as a decimal value. `mul`: the factor of the letter: 1 for no letter, 1024 for `K`, 1048576 for `M` and 1073741824 for `G`. |
| 11 | `    return int(v * mul)` | Returns the product as a whole number of bytes. |

### Functions `latency_rows` and `best_by_size`: read an output file of `latency` (lines 13 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 13 | `def latency_rows(path):` | Starts the function `latency_rows`. It reads one output file of the program `latency`. |
| 14 | `    """rows: size_bytes, rep (int, 'freshN' or 'best'), loads, ns; plus AnonHugePages per size"""` | Description text of the function: each row has the size in bytes, the repetition (a number, `freshN` or `best`), the loads and the ns value. The function also gives the `AnonHugePages` value per size. |
| 15 | `    rows, huge = [], {}` | `rows`: the list of the data rows. `huge`: a dictionary from the buffer size to the `AnonHugePages` value in kB. This value is the memory of the `latency` process that lies on 2 MiB pages. |
| 16 | `    for line in open(path):` | Loop over the lines of the file. |
| 17 | `        line = line.strip()` | Removes the line end and the spaces at both ends. |
| 18 | `        m = re.match(r'# size_bytes=(\d+) AnonHugePages_kB=(-?\d+)', line)` | `m`: the match of the start of the line against the pattern of the comment line that `latency` prints once per size. Group 1 is the size in bytes. Group 2 is the kB value, which may have a minus sign. |
| 19 | `        if m:` | Tests whether the line is such a comment line. |
| 20 | `            huge[int(m.group(1))] = int(m.group(2)); continue` | Then stores the kB value under the size and goes on with the next line. |
| 21 | `        if not line or line.startswith('#') or line.startswith('size_bytes'):` | Tests for an empty line, for every other comment line (it starts with `#`) and for the header row (it starts with `size_bytes`). |
| 22 | `            continue` | Then skips the line. |
| 23 | `        s, rep, loads, ns = line.split(',')` | Splits the data row at the commas into its 4 fields: size, repetition, loads and nanoseconds per load. A line with another number of fields stops the script with an error. |
| 24 | `        rows.append({'size': int(s), 'rep': rep, 'loads': int(loads), 'ns': float(ns)})` | Appends the row as a dictionary: `size` and `loads` as whole numbers, `ns` as a decimal number, and `rep` as text. |
| 25 | `    return rows, huge` | Returns the rows and the dictionary of the kB values. |
| 27 | `def best_by_size(rows, key=lambda r: r['rep'] == 'best'):` | Starts the function `best_by_size`. It builds a dictionary from the buffer size to the ns value of the rows that the test `key` accepts. By default `key` accepts the rows whose repetition is `best`. `latency` prints one such row per size, with the smallest ns per load of its timed intervals. |
| 28 | `    out = {}` | `out`: the result dictionary. |
| 29 | `    for r in rows:` | Loop over the rows. |
| 30 | `        if key(r):` | Tests whether `key` accepts the row. |
| 31 | `            out[r['size']] = r['ns']` | Then stores the ns value under the size. A later row of the same size replaces an earlier one. |
| 32 | `    return out` | Returns the dictionary. |

### Function `bandwidth_rows`: read an output file of `bandwidth` (lines 34 to 48)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `def bandwidth_rows(path):` | Starts the function `bandwidth_rows`. It reads one output file of the program `bandwidth`. |
| 35 | `    """rows from bandwidth.c CSV, keeping the '-- ...' context lines as 'ctx'"""` | Description text of the function: the rows come from the CSV output of `bandwidth.c`. The title lines that start with `--` are kept as the context `ctx` of the rows that follow them. |
| 36 | `    rows, ctx = [], ''` | `rows`: the result list. `ctx`: the text of the last title line. It is empty at the start. |
| 37 | `    for line in open(path):` | Loop over the lines of the file. |
| 38 | `        line = line.strip()` | Removes the line end and the spaces at both ends. |
| 39 | `        if line.startswith('--'):` | Tests whether the line is a title line. A run script writes such a line before each run, and it starts with `--`. |
| 40 | `            ctx = line[2:].strip(); continue` | Then keeps its text without the two hyphens as the context and goes on with the next line. |
| 41 | `        if not line or line.startswith('#') or line.startswith('kernel,'):` | Tests for an empty line, a comment line and the header row (it starts with `kernel,`). |
| 42 | `            continue` | Then skips the line. |
| 43 | `        f = line.split(',')` | `f`: the fields of the row, split at the commas. |
| 44 | `        if f[3] != 'best':` | Tests whether the fourth field is not `best`. |
| 45 | `            continue` | Then skips the row. So only the `best` row of each kernel is used. `bandwidth` prints it with the highest total rate of all repetitions. |
| 46 | `        rows.append({'ctx': ctx, 'kernel': f[0], 'threads': int(f[1]), 'bytes': int(f[2]), 'gbps': float(f[6])})` | Appends a dictionary: the context, the kernel (field 1), the thread count (field 2), the bytes per thread (field 3) and the rate in GB/s (field 7, the column `aggregate_GBps`). That rate is the bytes of all threads divided by the time of the slowest thread. |
| 47 | `    return rows` | Returns the rows. |

### Function `perf_counts`: read a count file of `perf stat` (lines 49 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 49 | `def perf_counts(path):` | Starts the function `perf_counts`. It reads one count file of `perf stat` and returns a dictionary from the event name to the count. |
| 50 | `    out = {}` | `out`: the result dictionary. |
| 51 | `    if not os.path.exists(path):` | Tests whether the file does not exist. |
| 52 | `        return out` | Then returns the empty dictionary. |
| 53 | `    for line in open(path):` | Loop over the lines of the file. |
| 54 | `        f = line.strip().split(',')` | `f`: the fields of the line, split at the commas. In a line that `perf stat -x,` writes, field 1 is the count and field 3 is the event name. |
| 55 | `        if len(f) < 3 or line.startswith('#'):` | Tests for a line with fewer than 3 fields and for a comment line. |
| 56 | `            continue` | Then skips the line. |
| 57 | `        try:` | Starts a block that catches a conversion error. |
| 58 | `            out[f[2].split(':')[0]] = float(f[0])` | Stores the count as a decimal number under the event name. `split(':')[0]` keeps the name up to the first colon, so a suffix such as `:u` is dropped. |
| 59 | `        except ValueError:` | The error case: the first field is not a number, for example the text `<not counted>`. |
| 60 | `            out[f[2].split(':')[0]] = None` | Then stores `None` for that event. |
| 61 | `    return out` | Returns the dictionary. The function does not read the fifth field of a line, the share of the time for which the counter was running. |

### Functions `refills_per_load` and `sizes_csv_prefix`, and the two size lists (lines 63 to 87)

| Line | Source | Explanation |
|---:|---|---|
| 63 | `def refills_per_load(d, sizes_csv, prefix):` | Starts the function `refills_per_load`. `d` is a result folder. `sizes_csv` is a list of sizes with commas between them. `prefix` is the start of the file names: `latency-perfrun` or `chase`. |
| 64 | `    """(long - short) / (loads_long - loads_short), per event, per size"""` | Description text of the function: for each event and each size, the count of the long run minus the count of the short run, divided by the loads of the long run minus the loads of the short run. |
| 65 | `    res = {}` | `res`: the result: a dictionary from the size to the rates of its events. |
| 66 | `    short, _ = latency_rows(os.path.join(d, f'{prefix}-short.csv')) if os.path.exists(os.path.join(d, f'{prefix}-short.csv')) else ([], {})` | `short`: the rows of the file `PREFIX-short.csv`, which holds the output of `latency` in the short runs (`latency_rows`). When the file does not exist, the list is empty. |
| 67 | `    long_, _ = latency_rows(os.path.join(d, f'{prefix}-long.csv')) if os.path.exists(os.path.join(d, f'{prefix}-long.csv')) else ([], {})` | `long_`: the same for the file `PREFIX-long.csv`. |
| 68 | `    ls = {r['size']: r['loads'] for r in short if r['rep'] == 'best'}` | `ls`: a dictionary from the size to the number of loads of the `best` row of the short run. The expression in braces builds it from the rows. |
| 69 | `    ll = {r['size']: r['loads'] for r in long_ if r['rep'] == 'best'}` | `ll`: the same for the long run. |
| 70 | `    for tok in sizes_csv.split(','):` | Loop over the size texts of the list. |
| 71 | `        size = parse_bytes(tok)` | `size`: the size in bytes (`parse_bytes`). |
| 72 | `        cs = perf_counts(os.path.join(d, f'{sizes_csv_prefix(prefix)}-{tok}-short.csv'))` | `cs`: the counts of the short run of this size (`perf_counts`). The file name is the result of `sizes_csv_prefix`, then the size text, then `-short.csv`. |
| 73 | `        cl = perf_counts(os.path.join(d, f'{sizes_csv_prefix(prefix)}-{tok}-long.csv'))` | `cl`: the counts of the long run, from the file whose name ends with `-long.csv`. |
| 74 | `        if size in ls and size in ll and cs and cl and ll[size] > ls[size]:` | Goes on with this size only when both runs have a load number and counts, and when the long run has more loads than the short run. |
| 75 | `            per = {}` | `per`: the rates of the events of this size. |
| 76 | `            for ev in cl:` | Loop over the events of the long run. |
| 77 | `                if cl.get(ev) is not None and cs.get(ev) is not None:` | Tests whether both runs have a number for this event. |
| 78 | `                    per[ev] = (cl[ev] - cs[ev]) / (ll[size] - ls[size])` | Then computes the rate of the event per load: the difference of the two counts divided by the difference of the two load numbers. The subtraction removes what both runs have in common, such as the build of the buffer and the warm-up. |
| 79 | `            res[size] = per` | Stores the rates under the size. |
| 80 | `    return res` | Returns the result. |
| 82 | `def sizes_csv_prefix(prefix):` | Starts the function `sizes_csv_prefix`. It gives the start of the names of the count files. |
| 83 | `    return {'latency-perfrun': 'latency-perf', 'chase': 'cmn'}[prefix]` | `latency-perfrun` gives `latency-perf`, the count files of `run_crb.sh`. `chase` gives `cmn`, the count files of `run_uncore.sh`. |
| 85 | `LAT_SIZES = '4K,8K,16K,32K,48K,64K,96K,128K,256K,512K,1M,1.5M,2M,3M,4M,8M,16M,32M,64M,96M,128M,192M,256M,512M,1G,2G'` | `LAT_SIZES`: the 26 buffer sizes of the full plan of `run_crb.sh`. |
| 86 | `UNCORE_SIZES = '1M,8M,16M,32M,48M,64M,96M,128M,192M,256M,512M,1G'` | `UNCORE_SIZES`: the 12 buffer sizes of `run_uncore.sh`. |

### Function `main`: build the dictionary and print it as JSON (lines 88 to 123)

| Line | Source | Explanation |
|---:|---|---|
| 88 | `def main():` | Starts the function `main`. |
| 89 | `    main_dir = sys.argv[1]` | `main_dir`: the first argument, a result folder of `run_crb.sh`. |
| 90 | `    fu = sys.argv[2] if len(sys.argv) > 2 else None` | `fu`: the second argument, a result folder of `run_followup.sh`. It is `None` when the argument is missing. |
| 91 | `    un = sys.argv[3] if len(sys.argv) > 3 else None` | `un`: the third argument, a result folder of `run_uncore.sh`. It is `None` when the argument is missing. |
| 92 | `    out = {'main_dir': main_dir, 'followup_dir': fu, 'uncore_dir': un}` | `out`: the dictionary that becomes the JSON text. It starts with the three folder names. |
| 93 | `    rows, huge = latency_rows(os.path.join(main_dir, 'latency.csv'))` | Reads the file `latency.csv` of the main folder (`latency_rows`). |
| 94 | `    out['latency_repeated'] = best_by_size(rows)` | `latency_repeated`: for each size, the ns per load of its `best` row. The name says repeated: in these runs each timed interval walks the same chain of pointers repeatedly. |
| 95 | `    out['latency_repeated_reps'] = [r for r in rows if r['rep'] != 'best']` | `latency_repeated_reps`: all rows that are not `best` rows, so one row per timed interval. The expression in brackets builds the list. |
| 96 | `    out['anon_huge_kb'] = huge` | `anon_huge_kb`: the `AnonHugePages` value per size. |
| 97 | `    out['core_refills_per_load'] = refills_per_load(main_dir, LAT_SIZES, 'latency-perfrun')` | `core_refills_per_load`: for each size, the events per load of each core event (`refills_per_load`). The counts come from the files `latency-perf-SIZE-short.csv` and `latency-perf-SIZE-long.csv`. The loads come from `latency-perfrun-short.csv` and `latency-perfrun-long.csv`. |
| 98 | `    out['bandwidth_main'] = bandwidth_rows(os.path.join(main_dir, 'bandwidth.csv'))` | `bandwidth_main`: the `best` rows of the file `bandwidth.csv` (`bandwidth_rows`). |
| 99 | `    if fu:` | Tests whether a follow-up folder was given. |
| 100 | `        rows, _ = latency_rows(os.path.join(fu, 'latency-fresh.csv'))` | Reads the file `latency-fresh.csv` of that folder. |
| 101 | `        out['latency_fresh'] = best_by_size(rows)` | `latency_fresh`: for each size, the ns per load of its `best` row. In these runs each timed interval is one pass over a chain that was never walked before. |
| 102 | `        out['latency_fresh_reps'] = [r for r in rows if r['rep'] != 'best']` | `latency_fresh_reps`: one row per timed chain. |
| 103 | `        out['pair'] = bandwidth_rows(os.path.join(fu, 'pair.csv'))` | `pair`: the `best` rows of `pair.csv`, the runs with two threads on a pair of CPUs. |
| 104 | `        out['asm'] = bandwidth_rows(os.path.join(fu, 'asm.csv'))` | `asm`: the `best` rows of `asm.csv`, the runs of the kernels that are written in assembly. |
| 105 | `        out['dram'] = bandwidth_rows(os.path.join(fu, 'dram.csv'))` | `dram`: the `best` rows of `dram.csv`. |
| 106 | `        bycpu, cur = {}, None` | `bycpu`: a dictionary for the file `latency-bycpu.csv`. `cur`: the key of the block that is read at the moment. |
| 107 | `        for line in open(os.path.join(fu, 'latency-bycpu.csv')):` | Loop over the lines of `latency-bycpu.csv`. |
| 108 | `            line = line.strip()` | Removes the line end and the spaces at both ends. |
| 109 | `            m = re.match(r'-- cpu (\d+) (repeated\|fresh)', line)` | `m`: the match of the start of the line against the pattern of a title line: `-- cpu`, a number, and then `repeated` or `fresh`. Group 1 is the CPU number. Group 2 is the word. |
| 110 | `            if m:` | Tests whether the line is such a title line. |
| 111 | `                cur = f'cpu{m.group(1)}-{m.group(2)}'; bycpu[cur] = {}; continue` | Then starts a new block with a key such as `cpu3-repeated` and goes on with the next line. |
| 112 | `            f = line.split(',')` | `f`: the fields of the line, split at the commas. |
| 113 | `            if len(f) == 4 and f[1] == 'best':` | Tests whether the line has 4 fields and is a `best` row. |
| 114 | `                bycpu[cur][int(f[0])] = float(f[3])` | Then stores its ns per load (field 4) under its size (field 1) in the block. |
| 115 | `        out['latency_bycpu'] = bycpu` | `latency_bycpu`: the blocks of that file. |
| 116 | `    if un:` | Tests whether an uncore folder was given. |
| 117 | `        out['cmn_per_load'] = refills_per_load(un, UNCORE_SIZES, 'chase')` | `cmn_per_load`: for each size, the events per load of each mesh event (`refills_per_load`). The counts come from the files `cmn-SIZE-short.csv` and `cmn-SIZE-long.csv`. The loads come from `chase-short.csv` and `chase-long.csv`. |
| 118 | `        for tag in ('bw-8M-14T', 'bw-256M-64T'):` | Loop over the two streaming read runs of `run_uncore.sh`. |
| 119 | `            out['cmn_' + tag] = {'counts': perf_counts(os.path.join(un, f'cmn-{tag}.csv')),` | Stores one entry per run. `counts` holds the counts of the file `cmn-TAG.csv` unchanged. No short run is subtracted here, so these counts cover the whole `bandwidth` process. |
| 120 | `                                 'bw': bandwidth_rows(os.path.join(un, f'{tag}.csv'))}` | Continues the entry: `bw` holds the `best` rows of the file `TAG.csv`, the output of `bandwidth`. |
| 121 | `    json.dump(out, sys.stdout, indent=1, sort_keys=True)` | Writes `out` as JSON text to the standard output. `indent=1` puts every entry on a line of its own, and `sort_keys=True` sorts the keys. |
| 123 | `main()` | Calls `main`. All statements above only define names. This call does the work. |
