# `clock_from_counts.py` explained, line by line

- Source file: `hwwatch-2026-11-24/clock_from_counts.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 131 lines, 6983 bytes).
- sha256 of the source when this page was built: `6745c660e624f804c6bfeafa971570273ca81a03b6183d8bab5e89fd732b52ea`.

## Short version: purpose

`clock_from_counts.py` is an analysis script that computes clock rates from cycle counts that earlier result files already hold. For a core it divides the cycles that one thread counted in one timed interval by the time for which the counter was enabled, and for a mesh it divides the count of the mesh cycle counter by the time for which that counter ran. It prints the lowest, the median and the highest clock rate of each csv file and of each group of mesh values (one group per result folder, kernel and mesh), and it starts no benchmark.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Trial**: one measurement in the trial layout of a runner csv file. By the design note, a file of this layout comes from a process with one pinned worker thread [Ref1].
- **Tag**: the name that a run script gives to one process. It starts the names of the files of that process.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Cycle counter**: a counter that counts clock cycles. For a core it is the event `CPU_CYCLES`. For a mesh it is the event `dtc_cycles`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Clock rate**: the frequency at which a core or a mesh runs. This script gives it in GHz, which is 1e9 cycles per second.
- **`C` row**: a row of a runner csv file that starts with `C`. It holds the counter values of one thread in one interval or trial.
- **Enabled time, running time**: two times of a counter in ns. `enabled_ns` is the time for which the counter was enabled. `running_ns` is the time for which it counted.
- **Scaled**: the word of this script for a row or a line whose counter did not run for the whole time. The script does not use such a value.
- **User mode**: the code of the program itself, in contrast to the code of the Linux kernel that works for the program.
- **`perf stat`**: a Linux tool that counts events for a time and prints the counts.
- **Median**: the middle value of a sorted list of numbers.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` takes the result folders from the command line. Without a folder it prints the docstring and ends with exit status 1 (lines 86 to 88).
2. For each folder it reads each csv file that lies directly in the folder. `core_clock` gives one clock rate per usable `C` row: the cycles divided by the enabled time (lines 92 to 95, lines 33 to 56).
3. For each folder it reads the `.perf` files. `mesh_clock` gives one clock rate per usable line of the event `dtc_cycles`, grouped by kernel and mesh. The kernel comes from `launches.txt` (lines 96 to 97, lines 59 to 82).
4. With `--json` it prints every value as JSON and ends (lines 98 to 101).
5. Without `--json` it prints the core table: one row per csv file with the lowest, the median and the highest clock rate, then a summary line (lines 102 to 113).
6. Then it prints the mesh table: one row per folder, kernel and mesh, then a summary line (lines 114 to 125).
7. When no file gave a value, it prints that no cycle counts were found (lines 126 to 127).

## Behavior a reader must know

- The script only reads result files and prints text. It starts no benchmark and writes no file.
- How a core clock rate is computed (line 53): one value per `C` row, which is one thread in one timed interval or trial. The value is the counted cycles divided by `enabled_ns`. Cycles per ns are GHz.
- The time of this division is the enabled time of the counter in the same row. It is not the length of the timed interval that the benchmark uses for its rates.
- By the docstring, the counter counts in user mode only. So each value is a lower bound of the clock rate (lines 11 to 12).
- A `C` row whose `running_ns` differs from `enabled_ns` is not used, and it is counted as scaled (lines 46 to 48). A row whose cycle count is not a number, for example `NA`, or whose enabled time is 0 is skipped without a count (lines 44 to 45).
- How a mesh clock rate is computed (line 81): one value per line of the event `dtc_cycles`. The value is the count divided by the time in ns for which the counter ran.
- A line of a `.perf` file whose share of the time is not exactly `100.00` is not used, and it is counted as scaled (lines 78 to 79).
- The docstring says that the output has one line per folder and kernel for the `.perf` files. The code prints one line per folder, kernel and mesh (lines 96 to 97).
- The output of one run of this script over the result folders of the repo is kept [Ref2]. Section 2 of the design note takes its numbers from that file [Ref1].

## Source and explanation, line by line

- Text shown: the file `hwwatch-2026-11-24/clock_from_counts.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (131 lines, 6983 bytes, sha256 `6745c660e624f804c6bfeafa971570273ca81a03b6183d8bab5e89fd732b52ea`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Docstring: the two kinds of input files and the rule for a clock rate (lines 1 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""clock_from_counts.py - clock rates that earlier result files already hold, as cycle counts.` | Starts the docstring, a text at the top of the file that describes the script. It ends in line 24. This first line gives the purpose: the script computes clock rates from cycle counts that earlier result files already hold. |
| 4 | `Usage: clock_from_counts.py [--json] RESULT_FOLDER...` | Docstring: the usage. The script takes one or more result folders. `--json` is optional and prints the values as JSON, a text format for data. |
| 6 | `It reads two kinds of files in each result folder:` | Docstring: the script reads two kinds of files in each result folder. Lines 8 to 13 describe the first kind and lines 14 to 17 the second. |
| 8 | `1. csv files of the runner programs (bwx...) that were started with a cycle counter in --events (cycles=0x11 or` | Docstring: kind 1 is the csv files of the runner programs (`bwx` and its later versions). Only files of a run with a cycle counter in the option `--events` count. The counter is named `cycles=0x11` or, as line 9 adds, `cpu_cycles=0x11`. |
| 9 | `   cpu_cycles=0x11, the event CPU_CYCLES of the core). Their "C" rows hold, per timed interval (or per trial) and` | Docstring: `0x11` is the number of the event `CPU_CYCLES`, which counts the clock cycles of the core. The rows of these files that start with `C` hold values per timed interval (or per trial) and, as line 10 adds, per thread. |
| 10 | `   thread, the counted cycles and the time for which the counter was enabled. Core clock = cycles / enabled time.` | Docstring: a `C` row holds the counted cycles and the time for which the counter was enabled. The rule: core clock = cycles divided by enabled time. |
| 11 | `   The counter counts user mode only (the runner sets exclude_kernel), so the value is a lower bound of the clock` | Docstring: the runner sets the flag `exclude_kernel`. So the counter counts in user mode only, and the value is a lower bound of the clock rate. The reason follows in line 12. |
| 12 | `   rate: time that the thread spent in the Linux kernel or off the CPU adds no cycles. A row whose counter did not` | Docstring: time that the thread spent in the Linux kernel or off the CPU adds no cycles. Then a new sentence starts: a row whose counter did not run for the whole enabled time is handled in a special way (line 13). |
| 13 | `   run for the whole enabled time (running_ns differs from enabled_ns) is not used and is counted as "scaled".` | Docstring: such a row has a `running_ns` that differs from `enabled_ns`. It is not used, and it is counted as "scaled". |
| 14 | `2. files *.perf written by "perf stat -x," with the event dtc_cycles of the mesh (arm_cmn_0, arm_cmn_1; these runs` | Docstring: kind 2 is the files with the ending `.perf`. The Linux tool `perf stat` wrote them with the option `-x,` (fields with commas between them). They hold the event `dtc_cycles`, the cycle counter of a mesh. The two mesh counter devices are named `arm_cmn_0` and `arm_cmn_1`. By the docstring, the runs that wrote these files needed root rights. |
| 15 | `   needed root). A line is: count, unit, event, time that the counter ran in ns, share of the time in percent.` | Docstring: the fields of such a line: the count, the unit, the event, the time that the counter ran in ns, and the share of the time in percent. |
| 16 | `   Mesh clock = count / time. A line whose share is not 100.00 holds a count that perf scaled up from a part of the` | Docstring: the rule: mesh clock = count divided by time. A line whose share is not `100.00` holds a count that `perf` scaled up from a part of the time. |
| 17 | `   time. Such a line is not used and is counted as "scaled".` | Docstring: such a line is not used, and it is counted as "scaled". |
| 19 | `Output: one line per csv file and per (folder, kernel) of the perf files, then the lowest and highest value of all.` | Docstring: the output is one line per csv file and one line per pair (folder, kernel) of the `.perf` files, then the lowest and the highest value of all. The code prints one line per folder, kernel and mesh (lines 96 to 97). So the docstring leaves out the mesh. |
| 20 | `"ivals" counts the different (round, pos, kernel) or trial values of a file, and "rows/ival" the C rows per such` | Docstring: the column `ivals` counts the different values of (round, position, kernel) or of the trial in a file. The column `rows/ival` gives the number of `C` rows per such value. |
| 21 | `value. A csv file that holds several processes has more rows per value than one process has threads.` | Docstring: a csv file that holds several processes has more rows per value than one process has threads. |
| 22 | `The kernel of a perf file is the --seq value of the launch line with the same tag in launches.txt ("?" if none).` | Docstring: the kernel of a `.perf` file is the value of `--seq` in the launch line of `launches.txt` that has the same tag. It is `?` when there is no such line. |
| 23 | `Python 3 standard library only.` | Docstring: the script needs only the standard library of Python 3. |
| 24 | `"""` | Ends the docstring. |

### Imports (lines 25 to 32)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `import glob` | `glob` finds files by a name pattern (line 70, line 92). |
| 26 | `import json` | `json` writes the values as JSON (line 99). |
| 27 | `import os` | `os` gives the functions for paths and files. |
| 28 | `import re` | `re` gives regular expressions (line 66). |
| 29 | `import statistics` | `statistics` computes the median (line 109, line 121). |
| 30 | `import sys` | `sys` gives the arguments of the command line, the standard output and the exit of the program. |

### Function `core_clock`: the clock rates of the cores from one csv file (lines 33 to 58)

| Line | Source | Explanation |
|---:|---|---|
| 33 | `def core_clock(path):` | Starts the function `core_clock`. It reads one csv file of a runner and returns one clock rate per usable `C` row. |
| 34 | `    """{"intervals": n, "threads": [C rows per interval], "ghz": [values], "scaled": n, "kernels": [...]} or None` | Docstring: the keys of the result. `intervals`: the number of intervals. `threads`: the numbers of `C` rows per interval. `ghz`: the clock rates. `scaled`: the number of rows that were not used. `kernels`: the kernel names. The sentence goes on in line 35. |
| 35 | `    when the file has no C rows with a column "cycles" or "cpu_cycles"."""` | Docstring: the function returns `None` when the file has no `C` rows with a column `cycles` or `cpu_cycles`. |
| 36 | `    hdr, col, ghz, per, kernels, scaled = None, None, [], {}, [], 0` | Six variables start empty. `hdr`: the column names. `col`: the name of the cycle column. `ghz`: the clock rates. `per`: the number of rows per interval. `kernels`: the kernel names. `scaled`: the count of rows that were not used. |
| 37 | `    with open(path, errors="replace") as fh:` | Opens the file. `errors="replace"`: a byte that is not valid text is replaced and does not stop the read. |
| 38 | `        for line in fh:` | Starts a loop over the lines. |
| 39 | `            if line.startswith("# C,"):` | A line that starts with `# C,` is the header of the `C` rows. |
| 40 | `                hdr = line[2:].split(";")[0].strip().split(",")` | `hdr`: the column names. The statement drops the first two characters (`#` and a space), keeps the text before the first `;`, and splits it at the commas. The first name is `C`. Other names are `round`, `pos`, `kernel`, `enabled_ns` and `running_ns`. |
| 41 | `                col = "cycles" if "cycles" in hdr else ("cpu_cycles" if "cpu_cycles" in hdr else None)` | `col`: `cycles` when the header has a column of that name. If not, `cpu_cycles` when the header has that name. If not, `None`: the file has no cycle counter. |
| 42 | `            elif line.startswith("C,") and hdr and col:` | A line that starts with `C,` is a data row. It is used only after a header with a cycle column. |
| 43 | `                d = dict(zip(hdr, line.strip().split(",")))` | `d`: a dictionary from each column name to the field of this row. |
| 44 | `                if not d.get(col, "").isdigit() or not d.get("enabled_ns", "").isdigit() or int(d["enabled_ns"]) == 0:` | Tests three cases in which the row is skipped: the cycle count is not a number of digits only (for example `NA`), the enabled time is not such a number, or the enabled time is 0. |
| 45 | `                    continue` | Then: goes on with the next line. Such a row is not counted as scaled. |
| 46 | `                if d.get("running_ns") != d["enabled_ns"]:` | Tests whether the counter did not run for the whole enabled time: the text of `running_ns` differs from the text of `enabled_ns`. Then the count covers only a part of the enabled time (lines 12 to 13). |
| 47 | `                    scaled += 1` | Then: adds 1 to `scaled`. |
| 48 | `                    continue` | Goes on with the next line. The row gives no clock rate. |
| 49 | `                key = tuple(d.get(k) for k in ("round", "pos", "kernel", "trial"))` | `key`: the interval of the row: its values of `round`, `pos`, `kernel` and `trial`. A column that the file does not have gives `None`. |
| 50 | `                per[key] = per.get(key, 0) + 1` | Adds 1 to the number of rows of this interval. |
| 51 | `                if d.get("kernel") and d["kernel"] not in kernels:` | Tests whether the row names a kernel that is not yet in the list. |
| 52 | `                    kernels.append(d["kernel"])` | Then: adds the kernel name. So the list keeps the order in which the kernels first occur. |
| 53 | `                ghz.append(int(d[col]) / int(d["enabled_ns"]))` | The clock rate of this row: the counted cycles divided by `enabled_ns`, the time in ns for which the counter was enabled. Cycles per ns are GHz: 1 cycle per ns is 1e9 cycles per second. The value belongs to one thread in one timed interval or trial. |
| 54 | `    if not ghz and not scaled:` | Tests whether the file gave no clock rate and no scaled row. |
| 55 | `        return None` | Then: returns `None`. |
| 56 | `    return {"intervals": len(per), "threads": sorted(set(per.values())), "ghz": ghz, "scaled": scaled, "kernels": kernels}` | Returns the result. `intervals`: the number of different keys. `threads`: the different numbers of rows per key, sorted. `ghz`: all clock rates in file order. `scaled` and `kernels` as collected. |

### Function `mesh_clock`: the clock rates of the meshes from the `.perf` files of one folder (lines 59 to 84)

| Line | Source | Explanation |
|---:|---|---|
| 59 | `def mesh_clock(folder):` | Starts the function `mesh_clock`. It reads the `.perf` files of one result folder and returns the mesh clock rates per kernel and mesh. |
| 60 | `    """{(kernel, mesh): {"ghz": [...], "scaled": n}} of the *.perf files of one result folder."""` | Docstring: the result is a dictionary. Its key is a pair (kernel, mesh). Its value holds the list `ghz` and the count `scaled`. |
| 61 | `    seq = {}` | `seq`: per tag, the value of `--seq` of its launch line. It starts empty. |
| 62 | `    lp = os.path.join(folder, "launches.txt")` | `lp`: the path of `launches.txt` in the folder. The script expects one line per process in it that starts with the word `launch` (line 66). |
| 63 | `    if os.path.isfile(lp):` | Tests whether the file exists. |
| 64 | `        with open(lp, errors="replace") as fh:` | Then: opens it. |
| 65 | `            for line in fh:` | Starts a loop over its lines. |
| 66 | `                m = re.match(r"launch (\S+) .*?--seq (\S+)", line)` | The pattern accepts a line that starts with the word `launch` and a space. Group 1 holds the next word, the tag. Then any text follows, as short as possible, up to `--seq` and a space. Group 2 holds the word after it, the kernel sequence of the process. |
| 67 | `                if m:` | Tests whether the line fits. |
| 68 | `                    seq.setdefault(m.group(1), m.group(2))` | Then: stores the sequence under the tag. `setdefault` keeps the first value when a tag occurs again. |
| 69 | `    out = {}` | `out`: the result, empty at the start. |
| 70 | `    for p in sorted(glob.glob(os.path.join(folder, "*.perf"))):` | Starts a loop over the files of the folder whose names end with `.perf`, sorted by name. |
| 71 | `        tag = os.path.basename(p).split(".")[0]` | `tag`: the file name up to its first dot. So the file `tagA.s01.perf` has the tag `tagA`. |
| 72 | `        with open(p, errors="replace") as fh:` | Opens the file. |
| 73 | `            for line in fh:` | Starts a loop over its lines. |
| 74 | `                f = line.strip().split(",")` | `f`: the fields of the line, split at the commas. |
| 75 | `                if len(f) < 5 or not f[2].endswith("/dtc_cycles/") or not f[0].isdigit() or not f[3].isdigit() or int(f[3]) == 0:` | Tests five cases in which the line is skipped: it has fewer than 5 fields, the event (field 3) does not end with `/dtc_cycles/`, the count (field 1) is not a number of digits only, the time (field 4) is not such a number, or the time is 0. |
| 76 | `                    continue` | Then: goes on with the next line. |
| 77 | `                d = out.setdefault((seq.get(tag, "?"), f[2].split("/")[0]), {"ghz": [], "scaled": 0})` | `d`: the entry of this kernel and this mesh. The kernel is the sequence of the tag, or `?` when `launches.txt` has no launch line for the tag. The mesh is the event name up to its first slash, for example `arm_cmn_0`. `setdefault` creates the entry at its first line. |
| 78 | `                if f[4] != "100.00":` | Tests whether the share of the time (field 5) is not exactly the text `100.00`. |
| 79 | `                    d["scaled"] += 1` | Then: adds 1 to `scaled`. The line gives no clock rate. |
| 80 | `                else:` | If the share is `100.00`, line 81 runs. |
| 81 | `                    d["ghz"].append(int(f[0]) / int(f[3]))` | The clock rate of this line: the count of `dtc_cycles` divided by the time in ns for which the counter ran. Counts per ns are GHz. |
| 82 | `    return out` | Returns the result. |

### Function `main`: read the folders, and the JSON output (lines 85 to 101)

| Line | Source | Explanation |
|---:|---|---|
| 85 | `def main():` | Starts the function `main`. |
| 86 | `    args = [a for a in sys.argv[1:] if a != "--json"]` | `args`: the arguments of the command line without `--json`. These are the result folders. |
| 87 | `    if not args:` | Tests whether no folder was given. |
| 88 | `        sys.exit(__doc__)` | Then: `sys.exit` with a text prints the docstring to the error output and ends the script with exit status 1. |
| 89 | `    core, mesh = [], []` | `core`: the results of the csv files. `mesh`: the results of the `.perf` files. Both start empty. |
| 90 | `    for folder in args:` | Starts a loop over the folders. |
| 91 | `        folder = folder.rstrip("/")` | Removes a slash at the end of the folder name. |
| 92 | `        for p in sorted(glob.glob(os.path.join(folder, "*.csv"))):` | Starts a loop over the csv files that lie directly in the folder, sorted by name. Folders below it are not searched. |
| 93 | `            r = core_clock(p)` | `r`: the result of `core_clock` for this file. |
| 94 | `            if r:` | Tests whether the file gave a result. A file without a cycle counter gives `None`. |
| 95 | `                core.append(dict(r, file=os.path.join(os.path.basename(folder), os.path.basename(p))))` | Then: adds the result with one more key, `file`: the name of the folder and the name of the file. |
| 96 | `        for (kernel, m), d in sorted(mesh_clock(folder).items()):` | Starts a loop over the pairs (kernel, mesh) that `mesh_clock` found in the folder, sorted. |
| 97 | `            mesh.append(dict(d, folder=os.path.basename(folder), kernel=kernel, mesh=m))` | Adds the entry with three more keys: the name of the folder, the kernel and the mesh. |
| 98 | `    if "--json" in sys.argv[1:]:` | Tests whether `--json` was given. |
| 99 | `        json.dump({"core": core, "mesh": mesh}, sys.stdout)` | Then: writes both lists as JSON to the standard output. The JSON form holds every single clock rate. |
| 100 | `        print()` | Prints a line break after the JSON text. |
| 101 | `        return` | Ends `main`. The text tables are not printed. |

### Function `main`: the two text tables (lines 102 to 131)

| Line | Source | Explanation |
|---:|---|---|
| 102 | `    if core:` | The core table is printed only when a csv file gave a result. |
| 103 | `        print("Core clock from the cycle counter of each thread (user mode, GHz = cycles per ns of enabled time):")` | Prints the heading of the core table. It says that the values come from the cycle counter of each thread, in user mode, and that GHz means cycles per ns of enabled time. |
| 104 | `        print("%-46s %6s %9s %8s %8s %8s %7s  kernels" % ("csv file", "ivals", "rows/ival", "min", "median", "max", "scaled"))` | Prints the column names: `csv file`, `ivals`, `rows/ival`, `min`, `median`, `max`, `scaled` and `kernels`. |
| 105 | `        for r in core:` | Starts a loop over the results, one per csv file. |
| 106 | `            g = r["ghz"]` | `g`: the clock rates of this file. |
| 107 | `            print("%-46s %6d %9s %8s %8s %8s %7d  %s" % (` | Prints the row of the file. The statement continues in lines 108 to 109. |
| 108 | `                r["file"], r["intervals"], "/".join(str(x) for x in r["threads"]), "%.4f" % min(g) if g else "-",` | The values: the file, the number of intervals, the numbers of rows per interval with slashes between them, and the lowest clock rate in GHz with 4 decimals. A file without a value gets `-`. |
| 109 | `                "%.4f" % statistics.median(g) if g else "-", "%.4f" % max(g) if g else "-", r["scaled"], ",".join(r["kernels"])))` | Continues the values: the median and the highest clock rate in GHz with 4 decimals, the number of scaled rows, and the kernel names with commas between them. |
| 110 | `        allg = [v for r in core for v in r["ghz"]]` | `allg`: the clock rates of all csv files in one list. |
| 111 | `        if allg:` | Tests whether there is a value. |
| 112 | `            print("all %d csv files: %d values in %d intervals, lowest %.4f GHz, highest %.4f GHz, %d scaled rows not used" % (` | Then: prints the summary line of the core table. The statement continues in line 113. |
| 113 | `                len(core), len(allg), sum(r["intervals"] for r in core), min(allg), max(allg), sum(r["scaled"] for r in core)))` | The values of the summary: the number of csv files, the number of clock rates, the sum of the interval counts of the files, the lowest and the highest clock rate in GHz, and the number of scaled rows that were not used. |
| 114 | `    if mesh:` | The mesh table is printed only when a `.perf` file gave an entry. |
| 115 | `        print("Mesh clock from dtc_cycles (GHz = count per ns that the counter ran; only lines with a share of 100.00):")` | Prints the heading of the mesh table. It says that GHz means the count per ns that the counter ran, and that only lines with a share of `100.00` are used. |
| 116 | `        print("%-30s %-14s %-10s %5s %9s %9s %9s %7s" % ("result folder", "kernel", "mesh", "n", "min", "median", "max", "scaled"))` | Prints the column names: `result folder`, `kernel`, `mesh`, `n`, `min`, `median`, `max` and `scaled`. |
| 117 | `        for r in mesh:` | Starts a loop over the entries, one per folder, kernel and mesh. |
| 118 | `            g = r["ghz"]` | `g`: the clock rates of this entry. |
| 119 | `            print("%-30s %-14s %-10s %5d %9s %9s %9s %7d" % (` | Prints the row of the entry. The statement continues in lines 120 to 121. |
| 120 | `                r["folder"], r["kernel"][:14], r["mesh"], len(g), "%.5f" % min(g) if g else "-",` | The values: the folder, the kernel cut to 14 characters, the mesh, the number of clock rates, and the lowest clock rate in GHz with 5 decimals. An entry without a value gets `-`. |
| 121 | `                "%.5f" % statistics.median(g) if g else "-", "%.5f" % max(g) if g else "-", r["scaled"]))` | Continues the values: the median and the highest clock rate in GHz with 5 decimals, and the number of scaled lines. |
| 122 | `        allg = [v for r in mesh for v in r["ghz"]]` | `allg`: the clock rates of all entries in one list. |
| 123 | `        if allg:` | Tests whether there is a value. |
| 124 | `            print("all folders: %d values, lowest %.5f GHz, highest %.5f GHz, %d scaled lines not used" % (` | Then: prints the summary line of the mesh table. The statement continues in line 125. |
| 125 | `                len(allg), min(allg), max(allg), sum(r["scaled"] for r in mesh)))` | The values of the summary: the number of clock rates, the lowest and the highest in GHz, and the number of scaled lines that were not used. |
| 126 | `    if not core and not mesh:` | Tests whether neither a csv file nor a `.perf` file gave anything. |
| 127 | `        print("no cycle counts found in: " + " ".join(args))` | Then: prints `no cycle counts found in:` and the folders. |
| 130 | `if __name__ == "__main__":` | Lines 130 to 131 run `main` only when the file is started as a program, not when another file imports it. The test file imports it. |
| 131 | `    main()` | Calls `main`. When `main` returns, the script ends with exit status 0. |

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its section 2 describes the analysis with this script and says that the files of the test `2026-11-15-tackle-8mb` have the trial layout, with one pinned worker thread per process.
- [Ref2] The file `status/2026-11-24-hw-record-evidence/clock_from_counts.out` of the same repo: the output of the command `python3 code/hwwatch-2026-11-24/clock_from_counts.py tests/*/*`. Its first line gives the time of the run: 2026-11-25T01:38:28Z.
