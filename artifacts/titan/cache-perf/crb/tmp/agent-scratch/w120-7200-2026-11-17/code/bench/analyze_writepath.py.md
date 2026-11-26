# `analyze_writepath.py` explained, line by line

- Source file: `bench/analyze_writepath.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 66 lines, 3951 bytes).
- sha256 of the source when this page was built: `8724e8e92e07aa1a67b6c54f0859dbdc479bf80319177860019d0a61892eeff2`.

## Short version: purpose

`analyze_writepath.py` analyses the file `writepath.csv` that part 5 of the script `run_sudo.sh` writes. For each case and each event it prints the number of events per cache line, per second and per cycle, computed from the difference between a long run and a short run. It also checks the data and ends with exit status 1 when a check fails.

## Words used here

- **Mesh**: the network inside one half of the chip. It connects the cores, the last cache level and the memory, and it has counters of its own.
- **Crosspoint**: a junction of the mesh. Part 5 counts events at the crosspoint with the node id `0x98`.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **Event name**: the name that `perf` prints for an event. `arm_cmn_0/NAME/` is an event of mesh 0, `arm_cmn_1/NAME/` one of mesh 1, and `armv8_pmuv3_0/NAME/` one of the core.
- **Cycle counter**: an event that counts clock cycles: `dtc_cycles` for a mesh and `cycles` for the core.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. Its row of a repetition holds the bytes that all threads moved (`total_bytes`) and the total rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Case, tag**: one setting of `bandwidth` in part 5 of `run_sudo.sh`: a kernel, a buffer size, a thread count and a CPU list. The tag is its short name, for example `w8M-c2`.
- **Event set, label**: the events that one run of `perf stat` counts. The label is the short name of the set, for example `xpdat` or `core1`.
- **Short run, long run**: two runs of the same case under the same event set. The timed interval of `bandwidth` lasts at least 200 ms in the short run and at least 2000 ms in the long run.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **Block**: the rows of one run in the input file: a title line that starts with `--`, then the output of `bandwidth`, then the count rows of `perf stat`.
- **Line**: a cache line, 64 bytes.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB**: 1e9 bytes.

## Main flow

1. Read the input file line by line and split it into blocks: one block per measured run and one block per idle control (lines 10 to 28).
2. Compute the idle rate of each event in events per second (lines 29 to 33).
3. Pair the short and the long block of each case and event set (lines 34 to 36).
4. For each pair: check the data, compute the difference in cache lines, and compute for each event the rate per line, per second and per cycle with the background subtracted. The function `short` makes the event names shorter for the output (lines 41 to 62).
5. Print the number of failed checks and their texts, and end with exit status 1 when a check failed (lines 63 to 66).

## Behavior a reader must know

- Rate per line of an event: the count of the long run minus the count of the short run minus the background, divided by the line difference.
- Line difference: `total_bytes` of the long run minus `total_bytes` of the short run, divided by 64. `total_bytes` is field 5 of the row of repetition 0 of `bandwidth`. It covers the timed interval only, summed over all threads of the case.
- The core event sets of part 5 count on CPU 2 only (`-C 2` in `run_sudo.sh`). So in a case with 2 or 4 threads the rate per line of a core event divides the events of one CPU by the lines of all threads.
- Rate per second: the same count difference divided by the difference of the running times of the two counters.
- Rate per cycle: the same count difference divided by the value `cyc` of a cycle counter of the same set. `cyc` is the count of that counter in the long run minus its count in the short run minus its background. A set with the cycle counters of both meshes uses the counter of mesh 0 for all its events.
- The background is subtracted from a cycle counter too (lines 54 to 58). So when a cycle counter counts at the same rate in the idle control as in a run, the divisor is near 0. The column `per cycle` is then not a rate per cycle, and the row of the cycle counter itself shows that small remainder and not its count. By the report of the project this happened in the run of part 5: the cycle counter of the mesh counted 2.0e9 cycles per second also in the idle control, and the script left about 6500 per second of it. The report calls the column `per cycle` of this script not usable [Ref1].
- Background: the idle rate of the event (count of the idle control divided by its running time) times the difference of the running times of the long and the short run.
- A count row is read from both ends: the count is the first field, the running time in nanoseconds the fourth field from the end, and the percent value the third field from the end. The fields from the third one up to the fifth one from the end are the event name, which can hold commas.
- A counter that ran less than 99.9 percent of the time gives the failure `multiplexed`. Its rates are still printed.
- The exit status is 1 when any check failed: a missing run, a row without a numeric count, bad byte totals, an event that is missing in the short run, a multiplexed counter, a missing idle control, or a file without pairs.
- The script reads its input only. It writes no file.

## Source and explanation, line by line

- Text shown: the file `bench/analyze_writepath.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (66 lines, 3951 bytes, sha256 `8724e8e92e07aa1a67b6c54f0859dbdc479bf80319177860019d0a61892eeff2`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text and imports (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""analyze_writepath.py - rates from run_sudo.sh part 5 (writepath.csv): per 64 B line, per second,` | Starts the description text of the file. The script computes rates from part 5 of `run_sudo.sh`, whose data file is `writepath.csv`. The rates are per 64-byte line, per second, and a third kind that line 3 names. |
| 3 | `and per mesh cycle where a cycle counter was in the same set.` | Text of the description: the third kind is the rate per cycle of the mesh. It exists where a cycle counter was in the same event set. |
| 4 | `Each case (tag) and set (label) has a short and a long run; rate = (long - short) counts over` | Text of the description: each case (tag) and each event set (label) has a short and a long run. The rate is the counts of the long run minus the counts of the short run, divided by ... The sentence goes on in line 5. |
| 5 | `(long - short) lines, minus the idle rate times the interval difference, as in subtract.py.` | Text of the description: ... the lines of the long run minus the lines of the short run. The idle rate times the difference of the intervals is subtracted, as in `subtract.py`. |
| 6 | `Event names may contain commas (bynodeid=1,nodeid=0x98), so perf rows are parsed from both ends.` | Text of the description: an event name can hold commas, as in `bynodeid=1,nodeid=0x98`. So a count row of `perf` is read from both of its ends. |
| 7 | `Checks: every counter ran 100 %, both runs present, long moved more bytes, idle control present.` | Text of the description: the checks: every counter ran 100 percent, both runs are present, the long run moved more bytes, and an idle control is present. The code accepts 99.9 percent and more (line 53). |
| 8 | `Exit 1 if any check fails. Usage: analyze_writepath.py <results dir>/writepath.csv"""` | Text of the description: the exit status is 1 when a check fails. The usage: the argument is the path of `writepath.csv` in a result folder. This line ends the description text. |
| 9 | `import sys, re, collections` | Loads three standard modules: `sys` (arguments and exit status), `re` (regular expressions) and `collections` (the type `defaultdict`). |

### Read the file into blocks: one block per run (lines 10 to 28)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `f = sys.argv[1]` | `f`: the path of the input file, the first argument of the script. |
| 11 | `blocks, cur = [], None` | `blocks`: the list of the blocks. A block is one run: a title line and the rows that follow it. `cur`: the block that is read at the moment, `None` at the start. |
| 12 | `for L in open(f):` | Loop over the lines of the file. |
| 13 | `    L = L.rstrip('\n')` | Removes the line end. |
| 14 | `    m = re.match(r'-- (\S+) (short\|long) set (\S+) events', L)` | `m`: the match of the start of the line against the pattern of a title line that the function `counted2` of `run_sudo.sh` writes: `--`, a tag, `short` or `long`, the word `set`, a label, and the word `events`. Group 1 is the tag, group 2 is `short` or `long`, and group 3 is the label of the event set. `\S+` stands for a text without spaces. |
| 15 | `    if m:` | Tests whether the line is such a title line. |
| 16 | `        cur = dict(tag=m.group(1), len=m.group(2), label=m.group(3), bytes=None, counts={}, bad=[]); blocks.append(cur); continue` | Then starts a new block: the tag, the length, the label, no byte total yet, no counts and no bad rows. The block is added to the list, and the loop goes on with the next line. |
| 17 | `    m = re.match(r'-- idle set (\S+) events', L)` | `m`: the match against the title line of an idle control: `-- idle set`, a label, and the word `events`. Group 1 is the label. |
| 18 | `    if m:` | Tests whether the line is such a title line. |
| 19 | `        cur = dict(tag='idle', len='idle', label=m.group(1), counts={}, bad=[]); blocks.append(cur); continue` | Then starts a block with the tag `idle` and that label, and goes on with the next line. |
| 20 | `    if L.startswith('-- background'): cur = None; continue` | A line that starts with `-- background` ends the block that was read. The rows after it are ignored until the next title line. |
| 21 | `    if cur is None: continue` | Skips a line that belongs to no block. |
| 22 | `    p = L.split(',')` | `p`: the fields of the line, split at the commas. |
| 23 | `    if len(p) >= 7 and p[3] == '0' and p[0] in ('asmwrite', 'asmread', 'read', 'write', 'copy', 'asmcopy'):` | Tests whether the line is the row of repetition 0 of `bandwidth`: at least 7 fields, the fourth field is `0`, and the first field is the name of a kernel. The runs of `run_sudo.sh` ask for one repetition, so this is the only repetition row of a run. |
| 24 | `        cur['bytes'] = int(p[4]); cur['gbps'] = float(p[6]); continue` | Then keeps two values of that row and goes on with the next line. `bytes`: field 5, `total_bytes`, the bytes that all threads moved in the timed interval. `gbps`: field 7, the total rate in GB/s. |
| 25 | `    if len(p) >= 7 and p[-1] == '' and p[-2] == '' and '/' in L:` | Tests whether the line is a count row of `perf stat`: at least 7 fields, the last two fields are empty, and the line holds a slash. |
| 26 | `        name = ','.join(p[2:-4]); cnt, rt, pct = p[0], p[-4], p[-3]` | Reads the row from both ends. `name`: the event name: the fields from the third one up to the fifth one from the end, joined with commas again. `cnt`: the first field, the count. `rt`: the fourth field from the end, the running time of the counter in nanoseconds. `pct`: the third field from the end, the share of the time for which the counter was running, in percent. |
| 27 | `        if cnt.isdigit() and rt.isdigit(): cur['counts'][name] = (int(cnt), int(rt) / 1e9, float(pct))` | When the count and the running time hold digits only: stores the count, the running time in seconds and the percent value under the event name. |
| 28 | `        else: cur['bad'].append(name + ':' + cnt)` | In the other case: notes the row as bad, with the event name and the first field. |

### The idle rates, the pairs of runs and the function `short` (lines 29 to 40)

| Line | Source | Explanation |
|---:|---|---|
| 29 | `idle = {}` | `idle`: for each event, the rate of the idle control in events per second. |
| 30 | `for b in blocks:` | Loop over the blocks. |
| 31 | `    if b['tag'] == 'idle':` | Takes the idle blocks only. |
| 32 | `        for ev, (c, t, pct) in b['counts'].items():` | Loop over the counts of the block: the event `ev`, its count `c`, its running time `t` in seconds and its percent value `pct`. |
| 33 | `            if pct >= 99.9: idle[ev] = c / t` | Stores the idle rate: the count divided by the running time. An event whose counter ran less than 99.9 percent of the time gets no idle rate. The rates are stored by event name only. So an event that is in several sets keeps the rate of the last idle block that holds it. |
| 34 | `by = collections.defaultdict(dict)` | `by`: a dictionary that pairs the blocks. The key is the tag together with the label of the set. Under it stand the block of the short run and the block of the long run. |
| 35 | `for b in blocks:` | Loop over the blocks. |
| 36 | `    if b['tag'] != 'idle': by[(b['tag'], b['label'])][b['len']] = b` | Puts every block that is not an idle block under its key, at `short` or at `long`. |
| 37 | `fail, out = [], collections.defaultdict(dict)` | `fail`: the list of the failed checks, as texts. `out`: a dictionary of the results by tag. Line 62 fills it, but no line prints it or writes it to a file. |
| 38 | `def short(ev):` | Starts the function `short`. It makes an event name shorter for the output. |
| 39 | `    ev = ev.replace(',bynodeid=1,nodeid=0x98', '@xp98')` | Replaces the text `,bynodeid=1,nodeid=0x98` with `@xp98`. That text limits an event to the crosspoint with the node id `0x98`. |
| 40 | `    return ev.replace('armv8_pmuv3_0/', 'core/').replace('arm_cmn_', 'mesh')` | Replaces `armv8_pmuv3_0/` with `core/` and `arm_cmn_` with `mesh`, and returns the result. So `arm_cmn_0/dtc_cycles/` becomes `mesh0/dtc_cycles/`. |

### Compute and print the rates, list the failed checks, set the exit status (lines 41 to 66)

| Line | Source | Explanation |
|---:|---|---|
| 41 | `print(f"{'case':14} {'set':8} {'event':46} {'per line':>9} {'per s':>12} {'per cycle':>10} {'GB/s':>6}")` | Prints the header row of the output: `case`, `set`, `event`, `per line`, `per s`, `per cycle` and `GB/s`. The numbers in the format, such as `14` and `>9`, are the widths of the columns in characters. |
| 42 | `for (tag, label), d in sorted(by.items()):` | Loop over the pairs, sorted by tag and label. `d` holds the short and the long block. |
| 43 | `    if 'short' not in d or 'long' not in d: fail.append(f'{tag} {label}: missing short or long run'); continue` | Check: both a short and a long run exist. If not, a failure is noted and the pair is skipped. |
| 44 | `    s, l = d['short'], d['long']` | `s`, `l`: the block of the short run and the block of the long run. |
| 45 | `    for blk in (s, l):` | Loop over the two blocks. |
| 46 | `        for bad in blk['bad']: fail.append(f"{tag} {label} {blk['len']}: uncounted row {bad}")` | Notes one failure for each bad row of the block (`uncounted row`). |
| 47 | `    if not s.get('bytes') or not l.get('bytes') or l['bytes'] <= s['bytes']: fail.append(f'{tag} {label}: bad byte totals'); continue` | Check: both runs have a byte total, and the long run moved more bytes than the short run. If not, the failure `bad byte totals` is noted and the pair is skipped. |
| 48 | `    dlines = (l['bytes'] - s['bytes']) / 64` | `dlines`: the number of cache lines that the long run moved more than the short run: the difference of the two byte totals divided by 64. The byte totals hold the bytes of all threads of the case. |
| 49 | `    rates = {}` | `rates`: the results of the events of this pair. |
| 50 | `    for ev in l['counts']:` | Loop over the events of the long run. |
| 51 | `        if ev not in s['counts']: fail.append(f'{tag} {label} {ev}: missing in short run'); continue` | Check: the event also has a count in the short run. If not, a failure is noted and the event is skipped. |
| 52 | `        (cl, tl, pl), (cs, ts, ps) = l['counts'][ev], s['counts'][ev]` | `cl`, `tl`, `pl`: the count, the running time in seconds and the percent value of the long run. `cs`, `ts`, `ps`: the same values of the short run. |
| 53 | `        if pl < 99.9 or ps < 99.9: fail.append(f'{tag} {label} {ev}: multiplexed ({ps:.0f} % / {pl:.0f} %)')` | Check: both counters ran at least 99.9 percent of the time. If not, the failure `multiplexed` is noted with both percent values. The rate is still computed. |
| 54 | `        if ev not in idle: fail.append(f'{tag} {label} {ev}: no idle control'); bg = 0.0` | Check: the event has an idle rate. If not, the failure `no idle control` is noted, and the background `bg` is 0. |
| 55 | `        else: bg = idle[ev] * (tl - ts)` | With an idle rate: `bg` is the background count: the idle rate in events per second times the difference of the two running times in seconds. |
| 56 | `        dt = tl - ts` | `dt`: the difference of the two running times in seconds. |
| 57 | `        rates[ev] = ((cl - cs - bg) / dlines, (cl - cs - bg) / dt if dt > 0 else float('nan'), cl - cs - bg)` | Stores three values for the event. The first is the events per line: the count of the long run minus the count of the short run minus the background, divided by `dlines`. The second is the events per second: the same difference divided by `dt`. It is not a number when `dt` is 0 or below. The third is the difference itself. |
| 58 | `    cyc = next((rates[e][2] for e in rates if e.endswith('/dtc_cycles/') or e.endswith('/cycles/')), None)` | `cyc`: the divisor of the column `per cycle`: the third value of line 57 for a cycle counter of the same set. That is its count of the long run minus its count of the short run minus its idle background. So when a cycle counter counts at the same rate in the idle control as in a run, `cyc` is near 0 and not the number of cycles. It is taken from the first event whose name ends with `/dtc_cycles/` (the cycle counter of a mesh) or with `/cycles/` (the cycle counter of the core). `None` stands for a set without such an event. A set with the cycle counters of both meshes gives the one of mesh 0, which comes first. |
| 59 | `    for ev, (pl_, ps_, raw) in rates.items():` | Loop over the results of the events. |
| 60 | `        pc = f'{raw / cyc:10.4f}' if cyc and not (ev.endswith('/dtc_cycles/') or ev.endswith('/cycles/')) else ' ' * 10` | `pc`: the events per cycle with 4 decimals: the count difference of the event divided by `cyc`. The cell stays blank for a set without a cycle counter and for a cycle counter itself. |
| 61 | `        print(f"{tag:14} {label:8} {short(ev):46} {pl_:9.3f} {ps_:12.4g} {pc} {l['gbps']:6.1f}")` | Prints one row: the tag, the label of the set, the short event name, the events per line with 3 decimals, the events per second with 4 significant digits, the events per cycle, and the total rate of the long run in GB/s. |
| 62 | `        out[tag][short(ev)] = (pl_, ps_, raw / cyc if cyc else None)` | Stores the three rates of the event in `out`, under the tag and the short event name. |
| 63 | `if not by: fail.append('no measurement pairs in the file')` | Check: the file held at least one pair. If not, a failure is noted. |
| 64 | `print('checks failed:', len(set(fail)))` | Prints the number of different failure texts. |
| 65 | `for x in sorted(set(fail))[:40]: print('  ', x)` | Prints up to 40 of the failure texts, each text once, in sorted order. |
| 66 | `sys.exit(1 if fail else 0)` | Ends the script with exit status 1 when a failure was noted, and with exit status 0 when none was noted. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-10-30-memory-hierarchy/report/crb-memory-hierarchy.html`: the report page of the first tests. Its paragraph that starts with "Corrected on 2026-11-11" is about the mesh cycle counter (event `dtc_cycles`) in the file `writepath.csv` of the run `sudo-20261102T211150Z`. By that paragraph each count divided by its counting time gives 1.9995 to 2.0000 GHz, with the machine idle and with busy cores. The earlier value of about 6,500 per second was what remained after `analyze_writepath.py` subtracted the count of the idle control. The script still does this, so its per-cycle column is not usable.
