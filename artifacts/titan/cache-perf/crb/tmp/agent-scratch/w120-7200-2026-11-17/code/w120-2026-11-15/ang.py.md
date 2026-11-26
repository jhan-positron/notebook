# `ang.py` explained, line by line

- Source file: `w120-2026-11-15/ang.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 14 lines, 741 bytes).
- sha256 of the source when this page was built: `92fbddc936df1872c90e20da48168006b512e7d54e6112d2ec4b03dc0365dcef`.

## Short version: purpose

`ang.py` reads one result folder of the script `rg.sh`, which runs groups of processes at the same time. For each group it prints one line: for each process the sum and the range of its thread rates in GB/s and its earliest start time, and at the end the total of the group.

## Words used here

- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line of the spec file, which run at the same time. The output of the item with the tag `TAG` is the file `GROUP.TAG.csv`.
- **`T` row**: the row that the runner prints for one thread in one interval. Field 3 holds the kernel, field 6 the bytes, field 7 the time in seconds, and field 9 the start time of the thread in seconds since the start of the process.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` (lines 4 to 5).
2. For each group, go through its output files in sorted order (lines 6 to 8).
3. For each file, read the `T` rows: the rate of each thread, the kernel name and the start time of each thread (lines 9 to 12).
4. Add one block per process to the output line, and add its rate sum to the total of the group (line 13).
5. Print the line of the group (line 14).

## Behavior a reader must know

- The script times nothing. The bytes, the time and the start time of a thread come from the fields 6, 7 and 9 of a `T` row.
- The rate sum of a process is the sum over every `T` row of its file. With one interval per process this is the sum of its thread rates. A file with several intervals would give the sum over all of them.
- The time after `t0=` is counted from the start of its own process. The `t0` values of two processes of a group do not share a zero point, so they do not show by themselves how far the two intervals overlap.
- The total of a group adds processes whose intervals are timed apart from each other.
- A file without a `T` row stops the script with an error (line 13). The output of a latency probe in a folder of `r4.spec` is such a file.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/ang.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (14 lines, 741 bytes, sha256 `92fbddc936df1872c90e20da48168006b512e7d54e6112d2ec4b03dc0365dcef`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""ang.py FOLDER: per group of simultaneous processes: rate sum and per-thread range of each process, and start times."""` | Documentation text of the script, with the usage: `ang.py FOLDER`. For each group of processes that ran at the same time it prints the rate sum and the range of the thread rates of each process, and the start times. |
| 3 | `import sys,glob,os,re` | Loads four modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os` for path names, `re` for regular expressions. |
| 4 | `fold=sys.argv[1]` | `fold`: the first argument, a result folder of the script `rg.sh`. |
| 5 | `groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]` | `groups`: the list of the group names, in the order of the launches. The comprehension goes through the lines of `launches.txt` that start with `launch`. The pattern matches `launch`, a space and then at least one character that is not a space. Group 1 of the pattern holds these characters, the name. |
| 6 | `for g in groups:` | Starts the loop over the groups. Each group gives one output line. |
| 7 | `    out=f'{g:30}'; tot=0` | `out`: the start of the output line, the group name in a field of 30 characters. `tot`: the rate sum of the whole group, 0 at the start. |
| 8 | `    for f in sorted(glob.glob(f'{fold}/{g}.*.csv')):` | Starts the loop over the output files of the group (`GROUP.*.csv`), in sorted order. Each file is the output of one process. |
| 9 | `        tag=os.path.basename(f).split('.')[-2]; r=[]; k=''; ts=[]` | `tag`: the item tag, the part of the file name before `.csv`. `r`: the list of the thread rates. `k`: the kernel name. `ts`: the list of the start times of the threads. All three are empty at the start. |
| 10 | `        for l in open(f):` | Starts the loop over the lines of the file. |
| 11 | `            p=l.split(',')` | `p`: the fields of the line, cut at the commas. |
| 12 | `            if p[0]=='T': r.append(float(p[6])/float(p[7])/1e9); k=p[3]; ts.append(float(p[9]))` | For a `T` row (one thread in one interval): adds the rate of the thread to `r`, in GB/s. It is the bytes (field 6) divided by the time of the thread in seconds (field 7) and by 1e9. `k` takes the kernel name (field 3). `ts` gets the start time of the thread (field 9), in seconds since the start of its own process. |
| 13 | `        tot+=sum(r); out+=f' {tag}:{k:11} {sum(r):6.1f} ({min(r):.2f}-{max(r):.2f}) t0={min(ts):.1f}'` | `tot` grows by the sum of the thread rates of this process. `out` gets one block for the process: the tag, a `:`, the kernel name in a field of 11 characters, the sum of the thread rates with 1 decimal, in parentheses the lowest and the highest thread rate with 2 decimals, and `t0=` with the earliest start time of a thread with 1 decimal. A file without a `T` row stops the script with an error here. |
| 14 | `    print(out+f'  total {tot:6.1f}')` | Prints the line of the group, with the word `total` and the rate sum of all processes of the group at the end. |
