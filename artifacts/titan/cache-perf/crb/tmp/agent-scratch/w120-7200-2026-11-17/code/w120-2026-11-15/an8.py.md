# `an8.py` explained, line by line

- Source file: `w120-2026-11-15/an8.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 19 lines, 1244 bytes).
- sha256 of the source when this page was built: `46a421dacc372d335efe4c9c0fbdb9f62cefab23399a61470b10eb501c0146ee`.

## Short version: purpose

`an8.py` reads the runner CSV files of one or more result folders in which the threads counted the busy-level events of their cores. For each interval and each mesh it prints the read rate in GB/s, the number of responses per 64 B line, and the share of the busy levels 0 to 3 among these responses. It fits the runs of the spec files `r8.spec` and `r8g.spec`.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`T` row**: the row that the runner prints for one thread in one interval. Its fields are: `T`, round, position, kernel, thread number, CPU, bytes, time in seconds, three clock times, passes, flags.
- **`C` row**: the counter row of one thread in one interval. Its fields are: `C`, round, position, kernel, thread number, CPU, `enabled_ns`, `running_ns`, `cputime_ns`, then one count per event.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo.
- **Response**: an answer of the mesh that a core receives. The core counts the answers of each busy level in its own event.
- **Line**: one cache line, 64 B.

## Main flow

1. For each folder of the arguments, take every `.csv` file in sorted order (lines 4 to 5).
2. Read the file: the bytes and the time of each thread from the `T` rows, the counts from the `C` rows (lines 6 to 10).
3. For each interval and each mesh, take the threads that have both kinds of row (lines 11 to 14).
4. Compute the rate of the mesh, its number of 64 B lines, and the sums of the first four events (lines 15 to 18).
5. Print one line with the rate, the responses per line and the share of each busy level (line 19).

## Behavior a reader must know

- The script times nothing. The bytes come from field 6 and the time from field 7 of a `T` row. The counts come from the first four event columns of a `C` row.
- The script takes the first four events as the busy levels 0 to 3 without a test. A CSV file with another order of events gives numbers under the wrong names.
- The rate of a mesh is the sum of its thread rates, each with its own time.
- A share is a count divided by the sum of the four counts, not by the number of lines.
- A `C` row with the value `NA` stops the script with an error (line 10). A mesh whose four sums are all 0 stops it with a division by zero (line 19).

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/an8.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (19 lines, 1244 bytes, sha256 `46a421dacc372d335efe4c9c0fbdb9f62cefab23399a61470b10eb501c0146ee`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""an8.py FOLDER...: per csv, kernel, round and mesh: rate GB/s, responses per 64 B line, and share of busy level 0,1,2,3 (percent of all counted responses)."""` | Documentation text of the script, with the usage: `an8.py FOLDER...`. For each CSV file, kernel, round and mesh it prints the rate in GB/s, the responses per 64 B line, and the share of the busy levels 0, 1, 2 and 3 in percent of all counted responses. |
| 3 | `import sys,glob,os,collections` | Loads four modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os` for path names, `collections` for the ordered dictionary. |
| 4 | `for fold in sys.argv[1:]:` | Starts the loop over the arguments. Each one is a result folder. |
| 5 | `    for path in sorted(glob.glob(fold+'/*.csv')):` | Starts the loop over all files of the folder that end with `.csv`, in sorted order. Each one is the output of one runner process. |
| 6 | `        T=collections.OrderedDict(); C={}` | Empties the data of the file. `T`: an ordered dictionary for the `T` rows, the rows of one thread in one interval. `C`: a dictionary for the `C` rows, the counter rows. |
| 7 | `        for l in open(path):` | Starts the loop over the lines of the file. |
| 8 | `            p=l.rstrip('\n').split(',')` | `p`: the fields of the line. `rstrip` removes the line break at the end, and `split(',')` cuts the line at each comma. |
| 9 | `            if p[0]=='T': T.setdefault((p[1],p[2],p[3]),{})[int(p[5])]=(float(p[6]),float(p[7]))` | Stores a `T` row. The key is the interval: round, position and kernel name (fields 1, 2, 3). Under it the row is stored by its CPU number (field 5). The value is a pair: the bytes of the thread (field 6) and its time in seconds (field 7). |
| 10 | `            if p[0]=='C': C[(p[1],p[2],p[3],int(p[5]))]=[float(x) for x in p[6:]]` | Stores a `C` row. The key is round, position, kernel name and CPU number. The value is the list of all fields from field 6 on, as numbers: `enabled_ns`, `running_ns`, `cputime_ns`, then one count per event. A field `NA` (an event that did not open) cannot be converted by `float`, so the script stops there with an error. |
| 11 | `        for k,v in T.items():` | Starts the loop over the intervals of the file, in the order of the file. `k` is the key (round, position, kernel) and `v` holds the threads of the interval. |
| 12 | `            for name,lo,hi in (('half0',0,64),('half1',64,128)):` | Starts the loop over the two halves of the chip: `half0` is the CPUs 0 to 63 (mesh 0), `half1` is the CPUs 64 to 127 (mesh 1). |
| 13 | `                cs=[c for c in v if lo<=c<hi and k+(c,) in C]` | `cs`: the CPUs of this half that have a `T` row and a `C` row in this interval. |
| 14 | `                if not cs: continue` | Skips a half without such threads. |
| 15 | `                rate=sum(v[c][0]/v[c][1] for c in cs)/1e9` | `rate`: the rate of this half in GB/s. It is the sum of the thread rates, each one the bytes of the thread divided by its own time in seconds, and the sum is divided by 1e9. |
| 16 | `                lines=sum(v[c][0] for c in cs)/64` | `lines`: the number of 64 B lines that the threads of this half read: the sum of their bytes divided by 64. |
| 17 | `                s=[sum(C[k+(c,)][3+i] for c in cs) for i in range(4)]` | `s`: four sums over the threads of this half, one for each of the first four event columns of the `C` rows (list places 3 to 6, after the three time columns). The script does not read the event names. It assumes, without a test, that the first four events are the responses with the busy levels 0, 1, 2 and 3, as in the spec files `r8.spec` and `r8g.spec`. |
| 18 | `                tot=sum(s)` | `tot`: the sum of the four, which is all counted responses of this half. |
| 19 | `                print(f'{os.path.basename(path):24} r{k[0]} {k[2]:12} {name} n={len(cs):3} {rate:6.1f} GB/s  resp/line {tot/lines:5.2f}  L0 {100*s[0]/tot:5.1f}%  L1 {100*s[1]/tot:5.1f}%  L2 {100*s[2]/tot:5.1f}%  L3 {100*s[3]/tot:5.1f}%  L3/line {s[3]/lines:5.2f}')` | Prints one line: the file name (24 characters wide), `r` with the round, the kernel name (12 wide), the half, `n=` with the number of threads, the rate with 1 decimal and `GB/s`, `resp/line` with the responses per 64 B line (`tot` divided by `lines`), then `L0` to `L3` with the share of each busy level in percent of `tot`, and `L3/line` with the responses of level 3 per line. When `tot` is 0 the division fails and the script stops with an error. |
