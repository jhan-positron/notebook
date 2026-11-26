# `anc3.py` explained, line by line

- Source file: `w120-2026-11-15/anc3.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 34 lines, 1849 bytes).
- sha256 of the source when this page was built: `a408bc60be29dd6a20e7f5d04b5184fadb6db370e8a1f4c0f7689aa73e7bf662`.

## Short version: purpose

`anc3.py` reads one result folder of the counter script `rgc.sh`, in which each group has one runner process on mesh 0 and one on mesh 1. It prints a table with one column per group: the read rate of each mesh, and every mesh counter event as a count in millions per second for mesh 0 and for mesh 1. The line rate of each mesh stands in the same table, in millions of lines per second.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Group**: the processes of one line of the spec file, which run at the same time. The output of the item `m0` is the file `GROUP.m0.csv`, that of the item `m1` is `GROUP.m1.csv`.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Counter window**: the time for which one `perf stat` command of `rgc.sh` counts one event set. Its counts stand in one file `GROUP.SET.perf`.
- **`T` row**: the row that the runner prints for one thread in one interval. Field 6 holds the bytes and field 7 the time in seconds.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` (lines 5 to 6).
2. Define the function `rows`, which reads the data rows of one `.perf` file (lines 7 to 11).
3. For each group, read the two runner outputs and sum the thread rates per mesh (lines 13 to 20).
4. For each counter file of the group, read every row and add the count per second to the sum of its event and its mesh (lines 21 to 28).
5. Print the table: the head, the rates in GB/s, the rates in millions of lines per second, and one line per event (lines 29 to 34).

## Behavior a reader must know

- The script times nothing. The bytes and the time of a thread come from the fields 6 and 7 of a `T` row. A count and the run time of its counter come from the fields 0 and 3 of a row of a `.perf` file.
- The counts are per second, not per line. The count of a window is divided by the run time of its counter. The line rate stands in its own table line, so the division per line is left to the reader.
- The rate of a mesh is taken from the whole interval of the process. The counts are taken from one window inside that interval.
- A group with a process on one mesh only stops the script with an error at line 31.
- A row that `perf` could not count is skipped without a message (line 25).
- The mark `*` in a cell means that at least one counter of the cell ran for less than 99.9 % of its window.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/anc3.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (34 lines, 1849 bytes, sha256 `a408bc60be29dd6a20e7f5d04b5184fadb6db370e8a1f4c0f7689aa73e7bf662`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""anc3.py FOLDER: mixed-kernel groups with mesh counters. Prints counts in millions per second, per mesh 'm0/m1'.` | Starts the documentation text of the script, with the usage: `anc3.py FOLDER`. The folder holds groups of processes with different kernels, with mesh counters. The script prints the counts in millions per second, with one value per mesh in the form `m0/m1`. |
| 3 | `Line rates (M lines/s) per mesh come from the T rows of the two processes."""` | Ends the documentation text: the line rates per mesh, in millions of lines per second, come from the `T` rows of the two processes of a group. |
| 4 | `import sys,glob,os,re,collections` | Loads five modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os` for path names, `re` for regular expressions, `collections` for the ordered dictionary. |
| 5 | `fold=sys.argv[1]` | `fold`: the first argument, a result folder of the script `rgc.sh`. |
| 6 | `groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]` | `groups`: the list of the group names, in the order of the launches. The comprehension goes through the lines of `launches.txt` that start with `launch`. The pattern matches `launch`, a space and then at least one character that is not a space. Group 1 of the pattern holds these characters, the name. |
| 7 | `def rows(f):` | Starts the function `rows`. It reads one `.perf` file and gives its data rows one by one, each as a list of five fields. |
| 8 | `    for l in open(f):` | Starts the loop over the lines of the file. |
| 9 | `        if l.startswith('#') or not l.strip(): continue` | Skips a line that starts with `#` and a line that is empty. |
| 10 | `        a=l.strip().rsplit(',',4); h=a[0].split(',',2)` | Cuts the line into fields. An event name can hold commas, so a plain cut at every comma would break it. `rsplit(',',4)` cuts at the last four commas only. Its first piece `a[0]` is the count, the unit and the whole event name. `split(',',2)` cuts that piece at its first two commas into `h`: the count, the unit, the event. |
| 11 | `        yield [h[0],h[1],h[2],a[1],a[2]]` | Gives the row to the caller: the count, the unit, the event, the time for which the counter ran in ns (`a[1]`) and the percentage of the window for which it ran (`a[2]`). |
| 12 | `val=collections.OrderedDict(); rate={}` | `val`: an ordered dictionary for the results: event name, then group name. `rate`: the rate of each group and mesh. |
| 13 | `for g in groups:` | Starts the loop over the groups. |
| 14 | `    rate[g]={}` | Starts with an empty dictionary of rates for this group. |
| 15 | `    for f in glob.glob(f'{fold}/{g}.m?.csv'):` | Starts the loop over the runner outputs of the group. The pattern `GROUP.m?.csv` fits the files of the items `m0` and `m1`. |
| 16 | `        m=int(os.path.basename(f).split('.')[-2][1]); s=0` | `m`: the mesh number of the file. `split('.')[-2]` takes the part of the file name before `.csv`, which is the item tag, and `[1]` takes its second character, the digit. `s`: the rate sum of this file, 0 at the start. |
| 17 | `        for l in open(f):` | Starts the loop over the lines of the file. |
| 18 | `            p=l.split(',')` | `p`: the fields of the line, cut at the commas. |
| 19 | `            if p[0]=='T': s+=float(p[6])/float(p[7])` | For a `T` row (one thread in one interval): adds the rate of the thread to `s`. The rate is the bytes of the thread (field 6) divided by its own time in seconds (field 7), in bytes per second. |
| 20 | `        rate[g][m]=s` | Stores the sum as the rate of this group and this mesh, in bytes per second. It is the sum over every `T` row of the file. With one interval per process this is the sum of the thread rates. |
| 21 | `    for f in sorted(glob.glob(f'{fold}/{g}.*.perf')):` | Starts the loop over all counter files of the group (`GROUP.*.perf`), in sorted order. Each file holds one counter window. |
| 22 | `        sn=os.path.basename(f).split('.')[-2]` | `sn`: the set name, the part of the file name before `.perf`. The script does not use it again. |
| 23 | `        for p in rows(f):` | Starts the loop over the rows of the file. |
| 24 | `            m=re.match(r'arm_cmn_(\d)/(\w+)',p[2]); mesh=int(m.group(1)); ev=m.group(2)` | The pattern matches `arm_cmn_`, one digit, `/`, and then letters, digits and underscores. Group 1 holds the digit, which goes to `mesh`. Group 2 holds the event name, up to the first comma or `/`, and goes to `ev`. |
| 25 | `            if ev=='dtc_cycles' or p[0].startswith('<'): continue` | Skips the rows of the cycle counter `dtc_cycles` and the rows whose count starts with `<`, which have no count. |
| 26 | `            if 'nodeid' in p[2]: ev='SN_'+ev` | When the event text holds `nodeid`, the event counts at one node only. The script then puts `SN_` before the event name. In `sets3.txt` these are the events at the memory ports. |
| 27 | `            d=val.setdefault(ev,{}).setdefault(g,{0:0.0,1:0.0}); d[mesh]+=float(p[0])/(float(p[3])/1e9)/1e6` | `d`: the entry of this event and this group, a dictionary with the two sums of mesh 0 and mesh 1, created with 0.0 when it is missing. The line adds to the sum of the mesh: the count, divided by the run time of the counter in seconds (field 3 holds ns), divided by 1e6. So the unit is millions per second. Rows with the same event name and mesh are added together, for example the 12 memory ports of a mesh. |
| 28 | `            if float(p[4])<99.9: d['mux']=1` | When the counter ran for less than 99.9 % of the window (field 4), the entry gets the mark `mux`. |
| 29 | `sh=lambda g:g.replace('read_','').replace('asmread','asm')` | `sh`: a small function that makes a group name shorter for the table head. It removes every `read_` and then replaces `asmread` by `asm`. So `read_nop256_asmread` becomes `nop256_asm`, and `asmread_read_nop256` becomes `asmnop256`. |
| 30 | `print(f'{"M per second":30}'+''.join(f'{sh(g):>18}' for g in groups))` | Prints the head of the table: `M per second` in a field of 30 characters, then each short group name in a field of 18 characters. |
| 31 | `print(f'{"GB/s m0/m1":30}'+''.join(f'{rate[g][0]/1e9:9.0f}/{rate[g][1]/1e9:<8.0f}' for g in groups))` | Prints the line `GB/s m0/m1`: for each group the rate of mesh 0 and the rate of mesh 1 in GB/s (bytes per second divided by 1e9), without decimals, with a `/` between them. A group that has no process on one of the meshes stops the script with an error here. |
| 32 | `print(f'{"Mlines/s m0/m1":30}'+''.join(f'{rate[g][0]/64e6:9.2f}/{rate[g][1]/64e6:<8.2f}' for g in groups))` | Prints the line `Mlines/s m0/m1`: for each group the rate of each mesh in millions of 64 B lines per second (bytes per second divided by 64e6), with 2 decimals. |
| 33 | `for ev,d in val.items():` | Starts the loop over the events, in the order in which they were first read. |
| 34 | `    print(f'{ev:30}'+''.join((f'{d[g][0]:9.2f}/{d[g][1]:<8.2f}'+('' if 'mux' not in d[g] else '*') if g in d else f'{"-":>18}') for g in groups))` | Prints one table line: the event name in a field of 30 characters, then one cell per group. A cell holds the value of mesh 0, a `/` and the value of mesh 1, with 2 decimals, and a `*` when the entry has the mark `mux`. When the group has no value for this event, the cell is a `-`. |
