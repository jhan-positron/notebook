# `anc.py` explained, line by line

- Source file: `w120-2026-11-15/anc.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 30 lines, 1522 bytes).
- sha256 of the source when this page was built: `5738550bc195a52cf8070057b9fadd665ac59aa86ad6002226900eb9c4341e24`.

## Short version: purpose

`anc.py` reads one result folder of the counter script `rc.sh` and prints a table of the mesh counters. Each row is one event, each column one process, and each cell holds the count of mesh 0 and of mesh 1, divided by the number of 64 B lines that the process read during the counter window. With the mode `cyc` the counts are divided by the clock cycles of the mesh.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. The script `rc.sh` reads it with `sudo perf stat`.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. The digit in the name is the mesh number.
- **Counter window**: the time for which one `perf stat` command of `rc.sh` counts one set of events. Its counts stand in one file `TAG.SET.perf`.
- **Tag**: the name of a process in the spec file. It is the first part of the names of its output files.
- **`I` row**: the row that the runner prints for one interval. Its last field is the total rate in GB/s: the bytes of all threads divided by the longest thread time.
- **`dtc_cycles`**: the event that `rc.sh` adds to every window. This script uses its count as the number of clock cycles of a mesh.
- **Line**: one cache line, 64 B.

## Main flow

1. Take the folder and the mode from the arguments (line 4).
2. Read the tags of the processes from the `launch` lines of `launches.txt` (lines 5 to 8).
3. Read the rate of each process from the `I` rows of its CSV file (lines 9 to 11).
4. For each process and each counter file `TAG.s*.perf`, read every row: the mesh, the event, the count, the run time of the counter and the percentage (lines 13 to 21).
5. Divide each count by the number of lines of the process in that run time, or by the cycles of the mesh (lines 22 to 25).
6. Print the rates and the table, and a warning when a counter did not run the whole window (lines 26 to 30).

## Behavior a reader must know

- The script times nothing. The rate comes from the last field of an `I` row. The count comes from field 0, the run time from field 3 and the percentage from field 4 of a row of a `.perf` file.
- The number of lines is an estimate. The script takes the mean rate of the whole interval and the run time of the counter. It does not know how many bytes were read inside the window.
- Both values of a cell are divided by the lines of all threads of the process, on both meshes. So `m0` is the count of mesh 0 per line that any thread read.
- The script reads only the sets whose name starts with `s` (line 14). These are the set names of the file `sets1.txt`.
- A process without an `I` row in its CSV file has no rate, and the script stops with an error at line 23.
- A row that `perf` could not count is skipped without a message (line 19).

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/anc.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (30 lines, 1522 bytes, sha256 `5738550bc195a52cf8070057b9fadd665ac59aa86ad6002226900eb9c4341e24`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""anc.py FOLDER [mode]: mesh counters per 64 B line read (all threads), per mesh 'm0/m1'. mode=cyc gives counts per mesh cycle instead."""` | Documentation text of the script, with the usage: `anc.py FOLDER [mode]`. It prints the mesh counters per 64 B line that all threads read, with one value per mesh in the form `m0/m1`. With the mode `cyc` it prints the counts per clock cycle of the mesh. |
| 3 | `import sys,glob,os,re,collections` | Loads five modules of the standard library: `sys` for the arguments, `glob` to find files by a pattern, `os`, `re` for regular expressions, `collections` for the ordered dictionary. |
| 4 | `fold=sys.argv[1]; mode=sys.argv[2] if len(sys.argv)>2 else 'line'` | `fold`: the first argument, a result folder of the script `rc.sh`. `mode`: the second argument when there is one. If not, it is `line`. |
| 5 | `tags=[]; rate={}` | `tags`: the list of the process tags, empty at the start. `rate`: the rate of each process, by its tag. |
| 6 | `for l in open(fold+'/launches.txt'):` | Starts the loop over the lines of `launches.txt`, the launch record of the folder. |
| 7 | `    m=re.match(r'launch (\S+)',l)` | The pattern matches a line that starts with `launch`, a space and then at least one character that is not a space. Group 1 holds these characters: the tag of the process. |
| 8 | `    if m: tags.append(m.group(1))` | Adds the tag to `tags` when the line matched. So `tags` holds the tags in the order of the launches. |
| 9 | `for t in tags:` | Starts the loop over the tags. |
| 10 | `    for l in open(f'{fold}/{t}.csv'):` | Starts the loop over the lines of the file `TAG.csv`, the output of the runner process. |
| 11 | `        if l.startswith('I,'): rate[t]=float(l.split(',')[-1])` | For a line that starts with `I,` (the row of one interval): takes its last field, the total rate in GB/s that the runner computed, as the rate of this process. When a file holds several `I` rows, the script keeps the rate of the last one. |
| 12 | `val=collections.OrderedDict(); warn=set()` | `val`: an ordered dictionary for the results: event name, then tag, then mesh number. `warn`: a set for the rows whose counter did not run the whole window. |
| 13 | `for t in tags:` | Starts the second loop over the tags. |
| 14 | `    for f in sorted(glob.glob(f'{fold}/{t}.s*.perf')):` | Starts the loop over the counter files of this process, in sorted order. The pattern `TAG.s*.perf` takes only sets whose name starts with `s`. Each file holds the counts of one counter window. |
| 15 | `        cyc={}` | `cyc`: the clock cycles of each mesh in this window, empty at the start. |
| 16 | `        rows=[l.strip().split(',') for l in open(f) if l.strip() and not l.startswith('#')]` | `rows`: the data rows of the file, each one cut into fields at the commas. The comprehension leaves out empty lines and lines that start with `#`. By the output form of `perf stat -x,` the fields are: the count, the unit, the event, the time for which the counter ran in ns, and the percentage of the window for which it ran. |
| 17 | `        for p in rows:` | Starts the loop over the rows. |
| 18 | `            m=re.match(r'arm_cmn_(\d)/(.*)/',p[2]); mesh=int(m.group(1)); ev=m.group(2)` | Reads the event field (field 2). The pattern matches `arm_cmn_`, one digit, `/`, any text, and a last `/`. Group 1 holds the digit, which is the mesh number and goes to `mesh`. Group 2 holds the event name and goes to `ev`. A row of another counter device does not match, and the script then stops with an error. |
| 19 | `            if p[0].startswith('<'): continue` | Skips a row whose first field starts with the character `<`. `perf` writes a text in angle brackets there when it has no count for the event. |
| 20 | `            c=float(p[0]); sec=float(p[3])/1e9` | `c`: the count. `sec`: the time for which the counter ran, in seconds (field 3 holds ns). |
| 21 | `            if float(p[4])<99.9: warn.add((t,ev,p[4]))` | When the counter ran for less than 99.9 % of the window (field 4), the script notes the tag, the event and the percentage in `warn`. |
| 22 | `            if ev=='dtc_cycles': cyc[mesh]=c; continue` | The event `dtc_cycles` is the count of the clock cycles of the mesh. The script keeps it in `cyc` and goes to the next row. |
| 23 | `            lines=rate[t]*1e9*sec/64` | `lines`: the number of 64 B lines that all threads of the process read while this counter ran. It is the rate of the process in bytes per second (`rate` times 1e9), times `sec`, divided by 64. The rate is the mean rate of the whole interval, not the rate inside the window. |
| 24 | `            v=c/lines if mode=='line' else c/cyc[mesh]` | `v`: the result for this row. In the mode `line` it is the count divided by `lines`. In every other mode it is the count divided by the clock cycles of the same mesh. The script `rc.sh` puts `dtc_cycles` first in each window, so `cyc` is set before it is used. |
| 25 | `            val.setdefault(ev,{}).setdefault(t,{})[mesh]=v` | Stores `v` under the event name, the tag and the mesh number. `setdefault` creates the inner dictionaries when they are missing. |
| 26 | `print('rate GB/s:',' '.join(f'{t}={rate[t]:.0f}' for t in tags))` | Prints the first output line: `rate GB/s:` and, for each tag, the tag with its rate without decimals. |
| 27 | `print(f'{"event":34}'+''.join(f'{t[:13]:>15}' for t in tags))` | Prints the head of the table: the word `event` in a field of 34 characters, then each tag, cut to 13 characters, in a field of 15 characters. |
| 28 | `for ev,d in val.items():` | Starts the loop over the events, in the order in which they were first read. |
| 29 | `    print(f'{ev:34}'+''.join((f'{d[t][0]:7.3f}/{d[t][1]:<7.3f}' if t in d and len(d[t])==2 else f'{"-":>15}') for t in tags))` | Prints one table line: the event name in a field of 34 characters, then one cell per tag. A cell holds the value of mesh 0, a `/` and the value of mesh 1, each with 3 decimals. When the tag has no value for this event, or a value for one mesh only, the cell is a `-`. |
| 30 | `if warn: print('MULTIPLEXED:',sorted(warn)[:10],len(warn))` | When `warn` is not empty: prints `MULTIPLEXED:`, the first 10 entries in sorted order, and the number of all entries. Multiplexed means that the counter shared its hardware with other events and counted only a part of the window. |
