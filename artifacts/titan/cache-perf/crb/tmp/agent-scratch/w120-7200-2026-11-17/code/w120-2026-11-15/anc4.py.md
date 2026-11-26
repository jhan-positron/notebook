# `anc4.py` explained, line by line

- Source file: `w120-2026-11-15/anc4.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 36 lines, 2050 bytes).
- sha256 of the source when this page was built: `28354f7a2321120d4d206224c560783cd8978482bc0ef992c3e7eee5901889ed`.

## Short version: purpose

`anc4.py` reads one result folder of the counter script `rgc.sh`, taken with the watchpoint sets of `sets4.txt`. For each group of processes and each mesh it prints the mean rate of a thread, the data flits and the response flits per second that reach 4 core ports, and the share of these flits that carries each busy level from 0 to 3. The script reads the busy level from the match value of each watchpoint.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
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
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits.
- **Channel**: the kind of a flit. The script reads the channel number 3 as the data channel (`DAT`) and every other number as the response channel (`RSP`).
- **Core port**: a port of the mesh to which cores are joined. The watchpoints of `sets4.txt` sit at 4 of them per mesh.
- **Watchpoint**: a counter event that counts the flits of one channel at one port. A match value (`wp_val`) and a mask (`wp_mask`) choose the flits. A mask of all ones hides every bit, so every flit counts.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo.

## Main flow

1. Take the folder from the argument and the group names from the `launch` lines of `launches.txt` (lines 4 to 5).
2. Define the function `rows`, which reads the data rows of one `.perf` file (lines 6 to 10).
3. For each group, read the two runner outputs and compute the mean thread rate of each mesh (lines 11 to 18).
4. Read every counter file of the group. For each watchpoint row, find the mesh, the channel and the busy level, and add the count per second to the sum of that key (lines 19 to 28).
5. For each mesh and channel, sum the four levels and compute the share of each level (lines 29 to 35).
6. Print one line per group (line 36).

## Behavior a reader must know

- The script times nothing. The bytes and the time of a thread come from the fields 6 and 7 of a `T` row. A count and the run time of its counter come from the fields 0 and 3 of a row of a `.perf` file.
- The four levels of one channel come from two counter windows (`dat01` and `dat23`, or `rsp01` and `rsp23`), which `rgc.sh` takes one after the other. So a share compares counts of two different times.
- The value after `all` comes from a third window (`datA3` or `rspA3`). The sum of the four levels and this value are counted at different times, so they need not be equal.
- The bit positions of the busy level are fixed in line 26: a shift by 44 bits for data flits, by 28 bits for response flits.
- The counts are sums over 4 core ports of a mesh, not over all core ports.
- A row that `perf` could not count is left out of the sums. The line shows the number of such rows after `NS`.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/anc4.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (36 lines, 2050 bytes, sha256 `28354f7a2321120d4d206224c560783cd8978482bc0ef992c3e7eee5901889ed`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""anc4.py FOLDER: share of DAT and RSP flits delivered to core ports that carry each CBusy level (0..3), per mesh (sum of 4 core ports)."""` | Documentation text of the script, with the usage: `anc4.py FOLDER`. It prints the share of the data flits (DAT) and of the response flits (RSP) delivered to core ports that carry each busy level from 0 to 3. `CBusy` is the name of the busy level in the mesh. The values are per mesh, as the sum of 4 core ports. |
| 3 | `import sys,glob,os,re,collections` | Loads five modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os` for path names, `re` for regular expressions, `collections` for the dictionary with a default value. |
| 4 | `fold=sys.argv[1]` | `fold`: the first argument, a result folder of the script `rgc.sh` that was run with the event sets of `sets4.txt`. |
| 5 | `groups=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]` | `groups`: the list of the group names, in the order of the launches. The comprehension goes through the lines of `launches.txt` that start with `launch`. The pattern matches `launch`, a space and then at least one character that is not a space. Group 1 of the pattern holds these characters, the name. |
| 6 | `def rows(f):` | Starts the function `rows`. It reads one `.perf` file and gives its data rows one by one, each as a list of five fields. |
| 7 | `    for l in open(f):` | Starts the loop over the lines of the file. |
| 8 | `        if l.startswith('#') or not l.strip(): continue` | Skips a line that starts with `#` and a line that is empty. |
| 9 | `        a=l.strip().rsplit(',',4); h=a[0].split(',',2)` | Cuts the line into fields. An event name can hold commas, so a plain cut at every comma would break it. `rsplit(',',4)` cuts at the last four commas only. Its first piece `a[0]` is the count, the unit and the whole event name. `split(',',2)` cuts that piece at its first two commas into `h`: the count, the unit, the event. |
| 10 | `        yield [h[0],h[1],h[2],a[1],a[2]]` | Gives the row to the caller: the count, the unit, the event, the time for which the counter ran in ns (`a[1]`) and the percentage of the window for which it ran (`a[2]`). |
| 11 | `for g in groups:` | Starts the loop over the groups. Each group gives one output line. |
| 12 | `    rate={}` | `rate`: the mean thread rate of each mesh of this group. Empty at the start. |
| 13 | `    for f in glob.glob(f'{fold}/{g}.m?.csv'):` | Starts the loop over the runner outputs of the group. The pattern `GROUP.m?.csv` fits the files of the items `m0` and `m1`. |
| 14 | `        m=int(os.path.basename(f).split('.')[-2][1]); r=[]` | `m`: the mesh number of the file, the digit of the item tag in the file name. `r`: the list of the thread rates of this file, empty at the start. |
| 15 | `        for l in open(f):` | Starts the loop over the lines of the file. |
| 16 | `            p=l.split(',')` | `p`: the fields of the line, cut at the commas. |
| 17 | `            if p[0]=='T': r.append(float(p[6])/float(p[7])/1e9)` | For a `T` row (one thread in one interval): adds the rate of the thread to `r`, in GB/s. It is the bytes of the thread (field 6) divided by its own time in seconds (field 7) and by 1e9. |
| 18 | `        rate[m]=sum(r)/len(r)` | Stores the mean of the thread rates (their sum divided by their number) as the rate of this mesh, in GB/s per thread. |
| 19 | `    acc=collections.defaultdict(float); mux=0; ns=0` | Empties the counter data of the group. `acc`: sums in millions per second, by mesh, channel, busy level and set name. `mux`: the number of rows whose counter did not run the whole window. `ns`: the number of rows without a count. |
| 20 | `    for f in sorted(glob.glob(f'{fold}/{g}.*.perf')):` | Starts the loop over all counter files of the group (`GROUP.*.perf`), in sorted order. |
| 21 | `        for p in rows(f):` | Starts the loop over the rows of the file. |
| 22 | `            m=re.match(r'arm_cmn_(\d)/watchpoint_down.*wp_chn_sel=(\d).*wp_val=(\w+),wp_mask=(\w+)',p[2])` | Reads the event text of a watchpoint. The pattern matches `arm_cmn_`, one digit, `/watchpoint_down`, and later `wp_chn_sel=` with one digit, and later `wp_val=` with a value, a comma and `wp_mask=` with a value. Group 1 holds the mesh digit, group 2 the channel digit, group 3 the text of the match value, group 4 the text of the mask. |
| 23 | `            if not m: continue` | Skips every row that is not such a watchpoint, for example the rows of `dtc_cycles`. |
| 24 | `            if p[0].startswith('<'): ns+=1; continue` | A row whose count starts with `<` has no count. It is counted in `ns` and skipped. |
| 25 | `            mesh=int(m.group(1)); ch='DAT' if m.group(2)=='3' else 'RSP'; val=int(m.group(3),16); mask=int(m.group(4),16)` | Turns the four groups into values. `mesh`: the mesh number. `ch`: `DAT` when the channel digit is 3, `RSP` in every other case. `val` and `mask`: the match value and the mask as numbers, read as hexadecimal text. |
| 26 | `            lvl='all' if mask==0xffffffffffffffff else str((val>>(44 if ch=='DAT' else 28))&3)` | `lvl`: the busy level that this watchpoint counts. A mask of all ones hides every bit, so the watchpoint counts all flits and the level is the word `all`. In every other case the level is two bits of the match value: the bits 44 and 45 for a data flit, the bits 28 and 29 for a response flit. `str` turns the number 0 to 3 into text. |
| 27 | `            acc[(mesh,ch,lvl,os.path.basename(f).split('.')[-2])]+=float(p[0])/(float(p[3])/1e9)/1e6` | Adds the count per second to the sum of this mesh, channel, level and set name. The count is divided by the run time of the counter in seconds (field 3 holds ns) and by 1e6. So the unit is millions of flits per second. The rows of the 4 core ports of a mesh fall on the same key and are added together. |
| 28 | `            if float(p[4])<99.9: mux+=1` | Counts the row in `mux` when its counter ran for less than 99.9 % of the window (field 4). |
| 29 | `    out=f'{g:26}'` | `out`: the start of the output line, the group name in a field of 26 characters. |
| 30 | `    for mesh in (0,1):` | Starts the loop over the two meshes. |
| 31 | `        out+=f' \| m{mesh} {rate.get(mesh,0):4.2f}GB/s/thr'` | Adds to `out`: `\|`, `m` with the mesh number, and the mean thread rate of this mesh with 2 decimals and the unit `GB/s/thr`. A mesh without a runner process shows 0.00. |
| 32 | `        for ch in ('DAT','RSP'):` | Starts the loop over the two channels, `DAT` and `RSP`. |
| 33 | `            lv={l:sum(v for k,v in acc.items() if k[0]==mesh and k[1]==ch and k[2]==l and not k[3].endswith('A3')) for l in '0123'}` | `lv`: a dictionary with one sum per busy level `0` to `3`, for this mesh and channel. The comprehension adds the entries of `acc` with this mesh, channel and level, but not those of a set whose name ends with `A3`. So the level 3 of the control sets `datA3` and `rspA3` is not counted twice. |
| 34 | `            tot=sum(lv.values()); al=sum(v for k,v in acc.items() if k[0]==mesh and k[1]==ch and k[2]=='all')` | `tot`: the sum of the four levels. `al`: the sum of the entries with the level `all`, which come from the sets whose name ends with `A3`. |
| 35 | `            out+=f' {ch} {tot:6.1f}M/s(all {al:6.1f}) %c0-3:'+' '.join(f'{100*lv[l]/tot:5.1f}' if tot else '  -  ' for l in '0123')` | Adds to `out`: the channel name, `tot` with 1 decimal and the unit `M/s`, in parentheses `all` with `al`, and after `%c0-3:` the share of each of the four levels in percent of `tot`, with 1 decimal. When `tot` is 0 each share is shown as `-`. |
| 36 | `    print(out+(f' MUX{mux}' if mux else '')+(f' NS{ns}' if ns else ''))` | Prints the line of the group. At the end stand `MUX` with the number of line 28 and `NS` with the number of line 24, each only when it is not 0. |
