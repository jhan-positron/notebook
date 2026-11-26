# `anc2.py` explained, line by line

- Source file: `w120-2026-11-15/anc2.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 40 lines, 2134 bytes).
- sha256 of the source when this page was built: `bab861a3ea818588b4cff355704465794c4858acebdc49043e395cbf67ae1f57`.

## Short version: purpose

`anc2.py` reads one result folder of the counter script `rc2.sh`, taken with the event sets of `sets2.txt`. Its first part prints, per process and per 64 B line read, the request, data and response flits at the 24 memory ports. Its second part prints the scan of the event numbers 0 to 39 of the 48 memory controller counters.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Event set**: one line of `sets2.txt`: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command of `rc2.sh` counts one event set. Its counts stand in one file `TAG.SET.perf`.
- **Tag**: the name of a process in the spec file. It is the first part of the names of its output files.
- **`I` row**: the row that the runner prints for one interval. Its last field is the total rate in GB/s: the bytes of all threads divided by the longest thread time.
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back. `sets2.txt` names 12 of them per mesh.
- **Watchpoint**: a counter event that counts the flits of one channel at one device port. Its text holds `wp_chn_sel=` with the channel number.
- **Memory controller counters**: the 48 counter devices `arm_cspmu_mc_0` to `arm_cspmu_mc_47`.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder from the argument, the tags from the `launch` lines of `launches.txt`, and the rate of each process from the `I` rows of its CSV file (lines 4 to 9).
2. Define the function `rows`, which reads the data rows of one `.perf` file (lines 10 to 14).
3. Part 1: for each of the five memory port sets and each process, read the counter file. Divide each count by the number of lines of the process in the run time of the counter, and sum per event and per mesh (lines 16 to 28).
4. Print one line per set and process (line 29).
5. Part 2: for each event number from 0 to 39 and each process, read the file of the set `mcKK` and sum the counts per line over the 48 devices (lines 30 to 39).
6. Print the line of an event number when a process has a sum above 0 (line 40).

## Behavior a reader must know

- The script times nothing. The rate comes from the last field of an `I` row. The count, the run time of the counter and the percentage come from a row of a `.perf` file.
- The number of lines is an estimate: the mean rate of the whole interval times the run time of the counter. The script does not know how many bytes were read inside the window.
- Every count is divided by the lines of all threads of the process, on both meshes.
- The set names are fixed in the script: `snreq`, `snwdat`, `snrdat`, `snmesh`, `snrsp` and `mc00` to `mc39`. A folder without one of these files stops the script with an error.
- A row that `perf` could not count is not added to a sum. Part 1 shows the number of such rows under a name with `_NS`. Part 2 shows it after `ns`.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/anc2.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (40 lines, 2134 bytes, sha256 `bab861a3ea818588b4cff355704465794c4858acebdc49043e395cbf67ae1f57`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""anc2.py FOLDER: memory-port (SN-F) flit counts per 64 B line read, and the memory-controller PMU event scan."""` | Documentation text of the script, with the usage: `anc2.py FOLDER`. It prints the flit counts of the memory ports per 64 B line read, and the scan of the events of the memory controller counters. `SN-F` is the name of the memory port in the mesh. |
| 3 | `import sys,glob,re,collections` | Loads four modules of the standard library: `sys` for the arguments, `glob`, `re` for regular expressions, `collections` for the dictionaries with a default value. |
| 4 | `fold=sys.argv[1]` | `fold`: the first argument, a result folder of the script `rc2.sh` that was run with the event sets of `sets2.txt`. |
| 5 | `tags=[re.match(r'launch (\S+)',l).group(1) for l in open(fold+'/launches.txt') if l.startswith('launch')]` | `tags`: the list of the process tags, in the order of the launches. The comprehension goes through the lines of `launches.txt` that start with `launch`. The pattern matches `launch`, a space and then at least one character that is not a space. Group 1 holds these characters, the tag. |
| 6 | `rate={}` | `rate`: the rate of each process, by its tag. Empty at the start. |
| 7 | `for t in tags:` | Starts the loop over the tags. |
| 8 | `    for l in open(f'{fold}/{t}.csv'):` | Starts the loop over the lines of the file `TAG.csv`, the output of the runner process. |
| 9 | `        if l.startswith('I,'): rate[t]=float(l.split(',')[-1])` | For a line that starts with `I,` (the row of one interval): takes its last field, the total rate in GB/s that the runner computed, as the rate of this process. |
| 10 | `def rows(f):` | Starts the function `rows`. It reads one `.perf` file and gives its data rows one by one, each as a list of five fields. |
| 11 | `    for l in open(f):` | Starts the loop over the lines of the file. |
| 12 | `        if l.startswith('#') or not l.strip(): continue` | Skips a line that starts with `#` and a line that is empty. |
| 13 | `        a=l.strip().rsplit(',',4); h=a[0].split(',',2)` | Cuts the line into fields. An event name can hold commas, so a plain cut at every comma would break it. `rsplit(',',4)` cuts at the last four commas only. Its first piece `a[0]` is the count, the unit and the whole event name. `split(',',2)` cuts that piece at its first two commas into `h`: the count, the unit, the event. |
| 14 | `        yield [h[0],h[1],h[2],a[1],a[2]]` | Gives the row to the caller: the count, the unit, the event, the time for which the counter ran in ns (`a[1]`) and the percentage of the window for which it ran (`a[2]`). `yield` makes `rows` a generator: the caller gets one row per loop pass. |
| 15 | `print('rate',rate)` | Prints the word `rate` and the dictionary of the rates. |
| 16 | `print('== SN ports: per line read; sum over 12 ports of mesh0 / mesh1; then per-port min-max of mesh 0 (per line)')` | Prints the head of the first part: the counts of the memory ports per line read. Each event is shown as the sum over the 12 ports of mesh 0, a `/` and the sum over the 12 ports of mesh 1, then the lowest and the highest single port of mesh 0. |
| 17 | `for s in ('snreq','snwdat','snrdat','snmesh','snrsp'):` | Starts the loop over the five event sets of the memory ports, by their names in `sets2.txt`. |
| 18 | `    for t in tags:` | Starts the loop over the processes. |
| 19 | `        acc=collections.defaultdict(lambda:[0,0]); per=collections.defaultdict(list); mux=0` | Empties the data of one set and one process. `acc`: for each event a list of two sums, for mesh 0 and for mesh 1. `per`: for each event the list of the values of the single ports of mesh 0. `mux`: the number of rows whose counter did not run the whole window. |
| 20 | `        for p in rows(f'{fold}/{t}.{s}.perf'):` | Starts the loop over the rows of the file `TAG.SET.perf`. When the file is missing, the script stops with an error. |
| 21 | `             m=re.match(r'arm_cmn_(\d)/(\w+)',p[2]);  ` | The pattern matches `arm_cmn_`, one digit, `/`, and then letters, digits and underscores. Group 1 holds the digit, which is the mesh number. Group 2 holds the event name, up to the first comma or `/`. |
| 22 | `            if m.group(2)=='dtc_cycles': continue` | Skips the rows of the event `dtc_cycles`, the cycle counter that the run script adds to every window. |
| 23 | `            ch=re.search(r'wp_chn_sel=(\d)',p[2]); ev=m.group(2)+(('_ch'+ch.group(1)) if ch else '')` | `ch`: a search for `wp_chn_sel=` and one digit in the event text. Only a watchpoint event has it. `ev`: the event name, and for a watchpoint also `_ch` with the channel digit. So a watchpoint on the data channel becomes `watchpoint_up_ch3`. |
| 24 | `            if p[0].startswith('<'): acc[ev+'_NS'][int(m.group(1))]+=1; continue` | A row whose count starts with `<` has no count. The script adds 1 to a separate entry with `_NS` at the end of the event name, for the mesh of the row, and goes to the next row. |
| 25 | `            lines=rate[t]*1e9*float(p[3])/1e9/64` | `lines`: the number of 64 B lines that all threads of the process read while this counter ran. It is the rate in bytes per second (`rate` times 1e9), times the run time in seconds (field 3 divided by 1e9), divided by 64. The rate is the mean rate of the whole interval. |
| 26 | `             acc[ev][int(m.group(1))]+=float(p[0])/lines;  ` | Adds the count per line (the count divided by `lines`) to the sum of this event and this mesh. |
| 27 | `            if m.group(1)=='0': per[ev].append(float(p[0])/lines)` | For a row of mesh 0: also keeps the count per line of this one port in `per`. |
| 28 | `            if float(p[4])<99.9: mux+=1` | Counts the row in `mux` when its counter ran for less than 99.9 % of the window (field 4). |
| 29 | `        print(f'{s:7}{t:12}'+'  '.join(f'{e}={v[0]:.4f}/{v[1]:.4f} [{min(per[e]):.3f}-{max(per[e]):.3f}]' if per[e] else f'{e}={v}' for e,v in acc.items())+(f' MUX{mux}' if mux else ''))` | Prints one line: the set name (7 characters wide), the tag (12 wide), and then each event as `name=`, the sum of mesh 0, `/`, the sum of mesh 1 (4 decimals each), and in square brackets the lowest and the highest port of mesh 0 (3 decimals). An `_NS` entry has no port values and is printed as its list of two numbers. At the end stands `MUX` with the number of line 28, when it is not 0. |
| 30 | `print('== MC PMU scan: event k: sum over 48 instances per line read; nonzero instances')` | Prints the head of the second part: the scan of the memory controller counters. For each event number it shows the sum over the 48 counter devices per line read, and the number of devices with a count above 0. |
| 31 | `for k in range(40):` | Starts the loop over the event numbers 0 to 39. |
| 32 | `    out=f'ev{k:2}'; anyv=False` | `out`: the start of the output line, `ev` with the number in a field of 2 characters. `anyv`: becomes true when a process has a sum above 0. |
| 33 | `    for t in tags:` | Starts the loop over the processes. |
| 34 | `        tot=0; nz=0; ns=0` | `tot`: the sum of the counts per line. `nz`: the number of devices with a count above 0. `ns`: the number of rows without a count. |
| 35 | `        for p in rows(f'{fold}/{t}.mc{k:02d}.perf'):` | Starts the loop over the rows of the file `TAG.mcKK.perf`, where `KK` is the event number with two digits. |
| 36 | `            if 'cspmu' not in p[2]: continue` | Skips a row whose event text does not hold `cspmu`. These are the two `dtc_cycles` rows. |
| 37 | `            if p[0].startswith('<'): ns+=1; continue` | A row whose count starts with `<` has no count. It is counted in `ns`. |
| 38 | `            c=float(p[0]); tot+=c/(rate[t]*1e9*float(p[3])/1e9/64); nz+=c>0` | `c`: the count. `tot` grows by the count divided by the number of lines, computed as in line 25. `nz` grows by 1 when the count is above 0. |
| 39 | `        out+=f'  {t}: {tot:10.4f} nz{nz} ns{ns}'; anyv\|=tot>0` | Adds the process to the output line: the tag, the sum with 4 decimals, `nz` with its number and `ns` with its number. `anyv` becomes true when the sum is above 0. |
| 40 | `    if anyv: print(out)` | Prints the line of this event number only when at least one process has a sum above 0. So an event number that counted nothing in every process is not shown. |
