# `an.py` explained, line by line

- Source file: `w120-2026-11-15/an.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 32 lines, 1729 bytes).
- sha256 of the source when this page was built: `64816d71ed731f4952430375e4c1d544a7a363df15366b0c69afb27286dc98ae`.

## Short version: purpose

`an.py` reads the CSV files that a runner wrote into one result folder and prints one line per timed interval. The line holds the total read, write or copy rate in GB/s, the rate and the range of the thread rates of each mesh, and each counter event per 64 B line of each mesh. It is one of the analysis scripts of the 120-thread investigation.

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
- **`I` row**: the row of one interval. Its last field is the total rate that the runner computed: the bytes of all threads divided by the longest thread time.
- **`enabled_ns`, `running_ns`**: two times in ns that Linux returns with each counter read (the runner source names them `time_enabled` and `time_running`): the time for which the counters of the thread were enabled, and the time for which they really counted.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder and the file names from the arguments. Without file names, take every `.csv` file of the folder (line 4).
2. For each file, read all lines: the event names from the header of the counter rows, the bytes and the time of each thread from the `T` rows, the counts from the `C` rows (lines 5 to 12).
3. Print the head line of the file (line 13).
4. For each interval, compute the rate of each thread as bytes divided by time, and sum the rates per mesh and in total (lines 14 to 23).
5. When the file has counters: for each mesh, divide the sum of each event by the number of 64 B lines of that mesh (lines 24 to 31).
6. Print the line of the interval (line 32).

## Behavior a reader must know

- The script times nothing. Every number comes from a CSV file of a runner: the bytes from field 6 and the time from field 7 of a `T` row, the counts from the fields after `cputime_ns` of a `C` row.
- The total of line 23 is the sum of the thread rates, each with its own time. The runner prints another total in its `I` row. With the common stop all threads have nearly the same time, so the two totals are close.
- A thread is put on mesh 0 or mesh 1 by its CPU number alone: below 64 or not.
- Events per line are computed per mesh: the counts of the threads of a mesh divided by the lines of the same threads. For a copy kernel a line counts once, not once for the read and once for the write.
- A `C` row with the value `NA` stops the script with an error (line 12).
- The mark `RUN` of line 31 means that the counters did not count for the whole interval.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/an.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (32 lines, 1729 bytes, sha256 `64816d71ed731f4952430375e4c1d544a7a363df15366b0c69afb27286dc98ae`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""an.py FOLDER [file...]: per interval of each csv: total and per-mesh rate (GB/s), per-thread range, and each counter per 64 B line per mesh."""` | Documentation text of the script, with the usage: `an.py FOLDER [file...]`. For each interval of each CSV file it prints the total rate and the rate per mesh in GB/s, the range of the thread rates, and each counter per 64 B line per mesh. |
| 3 | `import sys,glob,os,collections` | Loads four modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os` for path names, `collections` for the ordered dictionary. |
| 4 | `fold=sys.argv[1]; files=sys.argv[2:] or sorted(os.path.basename(x) for x in glob.glob(fold+'/*.csv'))` | `fold`: the first argument, a result folder. `files`: the other arguments, which are file names inside that folder. When there are none, `files` is the sorted list of the names of all files in the folder that end with `.csv`. `os.path.basename` cuts the folder part from each path. |
| 5 | `for f in files:` | Starts the loop over the CSV files. Each one is the output of one runner process. |
| 6 | `    T=collections.OrderedDict(); C={}; ev=None; copyk=False` | Empties the data of the file. `T`: an ordered dictionary for the `T` rows, the rows of one thread in one interval. `C`: a dictionary for the `C` rows, the counter rows. `ev`: the list of the event names, `None` until a header line gives it. `copyk` is set here and never used again. |
| 7 | `    for l in open(os.path.join(fold,f)):` | Starts the loop over the lines of the file. |
| 8 | `        p=l.rstrip('\n').split(',')` | `p`: the fields of the line. `rstrip` removes the line break at the end, and `split(',')` cuts the line at each comma. |
| 9 | `        if l.startswith('#') and 'C,round' in l:` | Tests for the header line of the counter rows: a line that starts with `#` and holds the text `C,round`. The runner prints it once when it counts events. |
| 10 | `            h=l.strip('# \n').split(';')[0].split(','); ev=h[9:]` | Takes the event names from that header. `strip('# \n')` removes the characters `#`, space and line break from both ends. `split(';')[0]` keeps the text before the first `;`, which is the list of the column names. `split(',')` cuts it into names. `h[9:]` drops the first 9 names (`C`, `round`, `pos`, `kernel`, `tid`, `cpu`, `enabled_ns`, `running_ns`, `cputime_ns`). What remains in `ev` are the event names. |
| 11 | `        if p[0]=='T': T.setdefault((p[1],p[2],p[3]),{})[int(p[5])]=(float(p[6]),float(p[7]))` | Stores a `T` row. The key is the interval: round, position and kernel name (fields 1, 2, 3). Under it the row is stored by its CPU number (field 5). The value is a pair: the bytes of the thread (field 6) and its time in seconds (field 7). `setdefault` creates the inner dictionary at the first row of an interval. |
| 12 | `        if p[0]=='C': C[(p[1],p[2],p[3],int(p[5]))]=[float(x) for x in p[6:]]` | Stores a `C` row. The key is round, position, kernel name and CPU number. The value is the list of all fields from field 6 on, as numbers: `enabled_ns`, `running_ns`, `cputime_ns`, then one count per event. A field `NA` (an event that did not open) cannot be converted by `float`, so the script stops there with an error. |
| 13 | `    print('==',f,'events per line (mesh0 \| mesh1):',ev)` | Prints the head line of the file: `==`, the file name, the text `events per line (mesh0 \| mesh1):` and the list of the event names. |
| 14 | `    for k,v in T.items():` | Starts the loop over the intervals of the file, in the order of the file. `k` is the key (round, position, kernel) and `v` holds the threads of the interval. |
| 15 | `        div=2 if 'copy' in k[2] else 1` | `div`: 2 when the kernel name holds the text `copy`, 1 in every other case. The runner counts the read bytes plus the written bytes for a copy kernel. So the bytes are divided by 2 to get the lines that were copied. |
| 16 | `        out=f'{k[0]} {k[1]:>2} {k[2]:14}'` | `out`: the start of the output line: the round, the position in a field of 2 characters, and the kernel name in a field of 14 characters. |
| 17 | `        tot=0; parts=[]` | `tot`: the total rate of the interval, 0 at the start. `parts`: the two texts for mesh 0 and mesh 1. |
| 18 | `        for lo,hi in ((0,64),(64,128)):` | Starts the loop over the two halves of the chip: the CPUs 0 to 63 (mesh 0) and the CPUs 64 to 127 (mesh 1). |
| 19 | `            cs=[c for c in v if lo<=c<hi]` | `cs`: the CPUs of this interval that lie in this half. The comprehension goes through the CPU numbers of `v`. |
| 20 | `            if not cs: parts.append('      -                 '); continue` | When no thread of the interval ran on this mesh, the part is a `-` between spaces, and the loop goes to the next half. |
| 21 | `            r=[v[c][0]/v[c][1]/1e9 for c in cs]; tot+=sum(r)` | `r`: the list of the thread rates of this mesh in GB/s. The rate of one thread is its bytes divided by its own time in seconds, divided by 1e9. `tot` grows by the sum of these rates. |
| 22 | `            parts.append(f'{sum(r):6.1f} ({min(r):.2f}-{max(r):.2f})')` | The part of this mesh: the sum of its thread rates with 1 decimal, and in parentheses the lowest and the highest thread rate with 2 decimals. |
| 23 | `        out+=f' tot {tot:6.1f} m0 {parts[0]} m1 {parts[1]}'` | Adds to `out`: the word `tot` with the total rate, `m0` with the part of mesh 0 and `m1` with the part of mesh 1. The total is the sum of the thread rates. It is not the total of the `I` row of the runner, which divides all bytes by the longest thread time. |
| 24 | `        if ev:` | Lines 25 to 31 run only when the file has counter rows (`ev` is a list that is not empty). Line 32 is not a part of this `if`: it runs for every interval. |
| 25 | `            for lo,hi in ((0,64),(64,128)):` | Starts a second loop over the two meshes, for the counters. |
| 26 | `                cs=[c for c in v if lo<=c<hi and k+(c,) in C]` | `cs`: the CPUs of this mesh for which a `C` row of this interval exists. `k+(c,)` is the key of line 12: the interval key with the CPU number added. |
| 27 | `                if not cs: continue` | Skips a mesh without counter rows. |
| 28 | `                lines=sum(v[c][0] for c in cs)/64/div` | `lines`: the number of 64 B lines that the threads of this mesh handled in the interval: the sum of their bytes, divided by 64 and by `div`. |
| 29 | `                s=[sum(C[k+(c,)][i] for c in cs) for i in range(3+len(ev))]` | `s`: one sum per column of the `C` rows, over the threads of this mesh. The columns 0, 1 and 2 are `enabled_ns`, `running_ns` and `cputime_ns`. The columns from 3 on are the events. |
| 30 | `                out+=' \|'+' '.join(f'{s[3+i]/lines:7.3f}' for i in range(len(ev)))` | Adds to `out` a `\|` and then, for each event, its sum divided by `lines`, in a field of 7 characters with 3 decimals. So each number is events per 64 B line, for one mesh. The numbers of mesh 0 come first, then a second `\|` and the numbers of mesh 1. |
| 31 | `                if s[1]<0.999*s[0]: out+=f' RUN{s[1]/s[0]:.2f}'` | A warning mark. `s[0]` is the time for which the counters were enabled, and `s[1]` the time for which they really counted. When the second is below 99.9 % of the first, the script adds `RUN` and the ratio with 2 decimals. The counts of such a line are too low by about that ratio. |
| 32 | `        print(out)` | Prints the output line of the interval. |
