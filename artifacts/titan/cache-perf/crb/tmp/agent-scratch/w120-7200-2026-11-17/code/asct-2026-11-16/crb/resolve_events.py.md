# `resolve_events.py` explained, line by line

- Source file: `asct-2026-11-16/crb/resolve_events.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 48 lines, 2646 bytes).
- sha256 of the source when this page was built: `e55d21e0e0a15522c4ba7764c3f2b08bf3ed92c433b4a694004d858a86081e10`.

## Short version: purpose

`resolve_events.py` turns the event names of the file `events.txt` into the raw codes that the counter code of ASCT needs. The script `prep.sh` runs it on CRB. It writes the file `events.codes` with one line per event set and prints one report line per event name.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter unit of the cores**: the name under which Linux shows the counters of the cores, `armv8_pmuv3_0`.
- **Raw code**: the number that selects one counter event of a counter unit.
- **Event set**: a named list of counter events that one process counts together. `events.txt` holds one set per line.
- **sysfs**: the folder `/sys`, in which the Linux kernel shows its devices and their settings as files.
- **`perf list`**: the command that prints the counter events that the tool `perf` knows on a machine.
- **L1, L2**: the first and the second cache level of a core.
- **TLB**: the cache of a core for address translations.

## Main flow

1. Read the two arguments: the input file and the output file (line 6).
2. Read the event sets of the input file and collect every event name once (lines 7 to 9).
3. Source 1: for each name, read its code from the sysfs file of the event, when that file exists (lines 10 to 16).
4. Source 2: run `perf list --details` and take the code of each name that still has none (lines 17 to 30).
5. Source 3: take the code from the table `FALLBACK` for each name that still has none (lines 31 to 42).
6. Write the output file: one line per set, with a `name=0xCODE` pair for each name that has a code (lines 43 to 46).
7. Print the report: one line per name with its code and its source, or with the word `unresolved` (lines 47 to 48).

## Behavior a reader must know

- The three sources have a fixed order. A later source never replaces a code of an earlier source.
- A name without a code does not stop the script. It is left out of its set in the output file and shows as `unresolved` in the report.
- The description text at the top names two sources. The code has three.
- Pattern 3 in line 28 takes a code only when it starts with `0x`. The list of `perf` on CRB prints some small codes without `0x` [Ref1].
- In the run of 2026-11-16 all 43 names were resolved: 19 from sysfs, 24 from the list of `perf`, none from the table `FALLBACK` [Ref2].
- The script runs `perf list --details` itself. When `perf` is missing, the script stops with an error in line 17, before it writes the output file.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/resolve_events.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (48 lines, 2646 bytes, sha256 `e55d21e0e0a15522c4ba7764c3f2b08bf3ed92c433b4a694004d858a86081e10`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text, arguments and the event sets of the input (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""resolve_events.py EVENTS OUT: turn the event names of EVENTS (lines 'SET\|name,name,...') into raw codes of the` | Starts the description text of the file. Usage: the two arguments are the input file EVENTS and the output file OUT. The script turns the event names of the input (lines of the form `SET\|name,name,...`) into raw codes. |
| 3 | `core counter unit armv8_pmuv3_0. Sources, in this order: the sysfs event files, then 'perf list --details'.` | Description, continued: the codes are those of the counter unit of the cores, `armv8_pmuv3_0`. The text names two sources, in this order: the event files of sysfs, then the output of `perf list --details`. The code has a third source that the text does not name, the table `FALLBACK` in lines 32 to 39. |
| 4 | `OUT gets lines 'SET\|name=0xCODE,...'. A name without a code is dropped and printed as 'unresolved'."""` | Description, last line: the output file gets lines of the form `SET\|name=0xCODE,...`. A name without a code is left out and printed with the word `unresolved`. |
| 5 | `import os, re, subprocess, sys` | Loads four standard modules: `os` (file paths), `re` (regular expressions), `subprocess` (start another program) and `sys` (the arguments). |
| 6 | `src, dst = sys.argv[1], sys.argv[2]` | `src`: argument 1, the path of the input file. `dst`: argument 2, the path of the output file. |
| 7 | `sysd = '/sys/bus/event_source/devices/armv8_pmuv3_0/events'` | `sysd`: the sysfs folder with one small file per named event of the counter unit of the cores. |
| 8 | `sets = [(l.split('\|')[0], l.strip().split('\|')[1].split(',')) for l in open(src) if '\|' in l]` | `sets`: a list with one pair for each input line that holds a `\|`. The first part of the pair is the set name, the text in front of the first `\|`. The second part is the list of event names: the text after that `\|`, without the line end, split at the commas. |
| 9 | `names = sorted({n for _, ns in sets for n in ns})` | `names`: every event name of all sets, each one once, in sorted order. The braces build a set, which drops a name that occurs again, such as `cpu_cycles`. |

### Source 1 (sysfs) and source 2 (the list of `perf`) (lines 10 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `code = {}` | `code`: an empty dictionary. Later it maps an event name to a pair: the code as a number and the name of the source. |
| 11 | `for n in names:` | Starts a loop over the event names. This loop is source 1, sysfs. |
| 12 | `    p = os.path.join(sysd, n)` | `p`: the path of the sysfs file of this event name. |
| 13 | `    if os.path.exists(p):` | Goes on only when that file exists. |
| 14 | `        m = re.search(r'event=0x([0-9a-fA-F]+)', open(p).read())` | Reads the file and searches the text `event=0x` with hexadecimal digits after it. Group 1 of the pattern holds the digits. |
| 15 | `        if m:` | Goes on only when the pattern was found. |
| 16 | `            code[n] = (int(m.group(1), 16), 'sysfs')` | Stores the code for the name, with the source `sysfs`. `int(..., 16)` reads the digits as a number in base 16. |
| 17 | `txt = subprocess.run(['perf', 'list', '--details'], capture_output=True, text=True).stdout` | Source 2. Runs the command `perf list --details` and keeps its standard output as text in `txt`. `capture_output=True` collects the output in place of printing it. `text=True` gives it as text and not as bytes. When the program `perf` is missing, this line stops the script with an error. |
| 18 | `last = None` | `last`: the event name of the most recent name line. `None` means that no name is active. |
| 19 | `for line in txt.split('\n'):` | Starts a loop over the lines of the output of `perf`. |
| 20 | `    m = re.match(r'^\s{2}([a-z0-9_]+)\s*$', line)` | Pattern 1: a line that holds two white-space characters, then a name of lowercase letters, digits and `_`, then nothing but white space. This is the name line of a named event. Group 1 holds the name. |
| 21 | `    if m:` | When pattern 1 matches: |
| 22 | `        last = m.group(1)` | remembers the name in `last`, |
| 23 | `        continue` | and goes to the next line of the output. |
| 24 | `    m = re.match(r'^\s{2}([a-z0-9_]+) OR armv8_pmuv3_0/', line)` | Pattern 2: a line that starts with two white-space characters, a name, and the text ` OR armv8_pmuv3_0/`. In this form `perf` lists an event that the Linux kernel names for the unit, as the saved list `perf-list-details.txt` shows [Ref1]. Source 1 already covers such an event. |
| 25 | `    if m:` | When pattern 2 matches: |
| 26 | `        last = None` | forgets the active name, so the code line that follows is not given to an older name, |
| 27 | `        continue` | and goes to the next line of the output. |
| 28 | `    m = re.search(r'armv8_pmuv3_0/event=(0x[0-9a-fA-F]+)/', line)` | Pattern 3, searched anywhere in the line: the text `armv8_pmuv3_0/event=`, a number that starts with `0x`, and a `/`. Group 1 holds the number with its `0x`. A code that `perf` prints without `0x` does not match. The saved list `perf-list-details.txt` of the run of 2026-11-16 holds such lines, for example with `event=8` [Ref1]. |
| 29 | `    if m and last and last in names and last not in code:` | The code is taken only when four things hold: pattern 3 was found, a name is active, the name is one of the wanted names, and the name has no code yet. So a code from sysfs is never replaced. |
| 30 | `        code[last] = (int(m.group(1), 16), 'perf-list')` | Stores the code for the active name, with the source `perf-list`. |

### Source 3: the table `FALLBACK` (lines 31 to 42)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `# Fallback: codes from ASCT's own table (src/core/asct_pmu_api.py) and two codes the 2026-11-15 runs used.` | Comment: the table that follows is the last source. By the comment its codes come from the table of ASCT itself (file `src/core/asct_pmu_api.py`), and two codes are those that the runs of 2026-11-15 used. The comment does not say which two. |
| 32 | `FALLBACK = {'cpu_cycles': 0x11, 'inst_retired': 0x08, 'l1d_cache_refill': 0x03, 'l2d_cache_refill': 0x17,` | Starts the dictionary `FALLBACK`, event name to code. This line holds four events: cycles, instructions and the refills of the L1 and of the L2 data cache. |
| 33 | `            'l1d_cache_lmiss_rd': 0x39, 'l2d_cache_lmiss_rd': 0x4009, 'll_cache_miss_rd': 0x37, 'bus_access': 0x19,` | Table, continued: the long-latency read misses of L1 and L2, the read misses of the last cache level, and the bus accesses. |
| 34 | `            'bus_access_rd': 0x60, 'l2d_cache_wb': 0x18, 'l2d_cache_wb_victim': 0x56, 'l2d_cache_wb_clean': 0x57,` | Table, continued: the bus accesses that are reads and three write-back events of the L2 data cache. |
| 35 | `            'l1d_cache_wb': 0x15, 'bus_cycles': 0x1d, 'stall_backend_mem': 0x4005, 'stall_backend': 0x24,` | Table, continued: the write-backs of the L1 data cache, the bus cycles, the memory stall cycles and the backend stalls. |
| 36 | `            'stall_frontend': 0x23, 'dtlb_walk': 0x34, 'l1d_tlb_refill': 0x05, 'l2d_tlb_refill': 0x2d,` | Table, continued: the frontend stalls, the walks of the translation tables, and the refills of the L1 and of the L2 data TLB. |
| 37 | `            'l1d_cache_rd': 0x40, 'l2d_cache_rd': 0x50, 'll_cache_rd': 0x36, 'l3d_cache_lmiss_rd': 0x400b,` | Table, continued: the read accesses to L1, to L2 and to the last cache level, and the long-latency read misses of the level 3 data cache. |
| 38 | `            'l1d_cache_refill_outer': 0x45, 'l1d_cache_refill_inner': 0x44, 'l1d_cache_hwprf': 0x8154,` | Table, continued: the two kinds of L1 refills (`outer` and `inner`) and the hardware prefetches of L1. |
| 39 | `            'l2d_cache_hwprf': 0x8155}` | Table, last line: the hardware prefetches of L2. The closing brace ends the dictionary. It holds 28 of the 43 names of `events.txt`. |
| 40 | `for n in names:` | Starts a loop over the event names. |
| 41 | `    if n not in code and n in FALLBACK:` | For a name that still has no code and stands in the table: |
| 42 | `        code[n] = (FALLBACK[n], 'fallback-table')` | stores the code of the table, with the source `fallback-table`. |

### The output file and the report (lines 43 to 48)

| Line | Source | Explanation |
|---:|---|---|
| 43 | `with open(dst, 'w') as f:` | Opens the output file for writing. An older file of that name is replaced. |
| 44 | `    for s, ns in sets:` | Starts a loop over the sets, in the order of the input file. |
| 45 | `        ok = [f'{n}=0x{code[n][0]:x}' for n in ns if n in code]` | `ok`: the list of the texts `name=0xCODE` for the names of this set that have a code, in the order of the input line. `:x` writes the number in hexadecimal with lowercase letters and no leading zeros. A name without a code is left out. |
| 46 | `        f.write(f'{s}\|{",".join(ok)}\n')` | Writes one line: the set name, a `\|`, and the texts of `ok` with commas between them. A set in which no name has a code gives a line with nothing after the `\|`. The loops of `prep.sh`, of part C of `run_single.sh` and of `run_chip.sh` skip such a line. |
| 47 | `for n in names:` | Starts a loop over the event names for the report. |
| 48 | `    print(('resolved   %-28s 0x%-5x %s' % (n, code[n][0], code[n][1])) if n in code else 'unresolved %s' % n)` | Prints one report line per name. With a code: the word `resolved`, the name in a column of 28 characters, the code in hexadecimal with `0x` in front, and the source. Without a code: the word `unresolved` and the name. `prep.sh` sends this report to the file `resolve.txt`. |

## References

- [Ref1] `perf-list-details.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the output of `perf list --details` on CRB, with lines such as `armv8_pmuv3_0/event=8/`.
- [Ref2] `resolve.txt` in the same result folder: 43 lines that start with `resolved`, 19 with the source `sysfs` and 24 with the source `perf-list`.
