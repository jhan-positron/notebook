# `subtract.py` explained, line by line

- Source file: `bench/subtract.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 62 lines, 3414 bytes).
- sha256 of the source when this page was built: `7072267671e16d264c9382d2456a6ed9ca56d713d473d54bde60f1374d76a6c5`.

## Short version: purpose

`subtract.py` analyses one counter file of the script `run_sudo.sh`: `writebw.csv` of part 3 or `crossmesh.csv` of part 4. For each case and each mesh event it prints the number of events per cache line that the benchmark moved, computed from the difference between a long run and a short run. It also checks the data and ends with exit status 1 when a check fails.

## Words used here

- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Mesh event**: an event that a counter of a mesh counts, for example the requests that the home nodes received. `perf` prints its name as `arm_cmn_0/NAME/` for mesh 0 and `arm_cmn_1/NAME/` for mesh 1.
- **`perf stat`**: a command of the Linux tool `perf`. It starts a program and prints the counts of the chosen counter events.
- **`bandwidth`**: the benchmark whose threads read, write or copy their buffers. Its row of a repetition holds the bytes that all threads moved (`total_bytes`) and the total rate in GB/s.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Case, tag**: one setting of `bandwidth` in `run_sudo.sh`: a kernel, a buffer size and a thread count or CPU list. The tag is its short name, for example `asmwrite-8M-1`.
- **Event set**: the events that one run of `perf stat` counts.
- **Short run, long run**: two runs of the same case under the same event set. The timed interval of `bandwidth` lasts at least 200 ms in the short run and at least 2000 ms in the long run.
- **Idle control**: a run of `perf stat` over `sleep 2`. It gives the counts of 2 s without a benchmark.
- **Block**: the rows of one run in the input file: a title line that starts with `--`, then the output of `bandwidth`, then the count rows of `perf stat`.
- **Line**: a cache line, 64 bytes.
- **Multiplexed**: Linux lets several events use the same hardware counter one after the other. A multiplexed event does not count the whole time.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **GB**: 1e9 bytes.

## Main flow

1. Read the input file line by line and split it into blocks: one block per run, and one block for all idle controls (lines 11 to 29).
2. Compute the idle rate of each event in events per second (lines 30 to 34).
3. Pair the short and the long block of each case and event set (lines 35 to 37).
4. For each pair: check the data, compute the difference in cache lines, and print for each event on each mesh the rate per line with the background subtracted (lines 38 to 57).
5. Print the number of failed checks and their texts, and end with exit status 1 when a check failed (lines 58 to 62).

## Behavior a reader must know

- Rate per line of an event: the count of the long run minus the count of the short run, divided by the line difference, minus the background per line.
- Line difference: `total_bytes` of the long run minus `total_bytes` of the short run, divided by 64. `total_bytes` is field 5 of the row of repetition 0 of `bandwidth`. It covers the timed interval only, summed over all threads.
- The counts cover the whole `bandwidth` process, also the first write of the buffers and the warm-up. Both runs have that part, so the subtraction removes it.
- A count is field 1 of a count row of `perf stat`, under the event name in field 3. Field 4 is the running time of the counter in nanoseconds, and field 5 is the share of the time for which it ran, in percent.
- Background per line: the idle rate of the event (count of the idle control divided by its running time), times the difference of the running times of the long and the short run, divided by the line difference.
- A counter that ran less than 99.9 percent of the time gives the failure `multiplexed`. Its rate is still printed.
- The last column, `GB/s long`, is the total rate of the long run (field 7 of its repetition row).
- The exit status is 1 when any check failed: a missing run, a row without a numeric count, bad byte totals, a missing counter, a multiplexed counter, a missing idle control, or a file without pairs.
- The script reads its input only. It writes no file.

## Source and explanation, line by line

- Text shown: the file `bench/subtract.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (62 lines, 3414 bytes, sha256 `7072267671e16d264c9382d2456a6ed9ca56d713d473d54bde60f1374d76a6c5`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text and imports (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""subtract.py - rates per cache line from the short/long counter runs of run_sudo.sh parts 3 and 4.` | Starts the description text of the file. The script computes rates per cache line from the short and the long counter runs of the parts 3 and 4 of `run_sudo.sh`. |
| 3 | `Reads writebw.csv or crossmesh.csv. For each case (tag) and declared event set: rate =` | Text of the description: the script reads `writebw.csv` or `crossmesh.csv`. For each case (tag) and each declared event set it computes a rate. The formula follows in line 4. |
| 4 | `(long count - short count) / (long lines - short lines), lines = total_bytes / 64 from the` | Text of the description: the rate is the count of the long run minus the count of the short run, divided by the lines of the long run minus the lines of the short run. The lines are the value `total_bytes` divided by 64. The source of that value follows in line 5. |
| 5 | `bandwidth tool's rep-0 row, minus the idle background rate scaled by the interval difference.` | Text of the description: `total_bytes` comes from the row of repetition 0 of the tool `bandwidth`. From the rate the script subtracts the idle background rate, scaled by the difference of the two intervals. |
| 6 | `Checks (each failure is listed and makes the exit status 1): every declared event present as a` | Text of the description: the checks. Each failure is listed and makes the exit status 1. Check 1 starts here: every declared event must be present as a ... |
| 7 | `numeric count on both meshes in both runs; every counter ran 100 % of its interval; the long run` | Text of the description: ... numeric count on both meshes in both runs. Check 2: every counter ran 100 percent of its interval. The code accepts 99.9 percent and more (line 52). Check 3 starts here: the long run ... |
| 8 | `moved more bytes than the short one; a numeric idle control exists for every event (a rate without` | Text of the description: ... moved more bytes than the short run. Check 4: a numeric idle control exists for every event. The sentence in parentheses starts here: a rate without ... |
| 9 | `one is printed with bg=none and counts as a failure)."""` | Text of the description: ... an idle control is printed with `bg=none` and counts as a failure. The code prints the word `none` in the background column (line 56). This line ends the description text. |
| 10 | `import sys, re, collections` | Loads three standard modules: `sys` (arguments and exit status), `re` (regular expressions) and `collections` (the type `defaultdict`). |

### Read the file into blocks: one block per run (lines 11 to 29)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `f = sys.argv[1]` | `f`: the path of the input file, the first argument of the script. |
| 12 | `blocks = []` | `blocks`: the list of the blocks. A block is one run: a title line and the rows that follow it. |
| 13 | `cur = None` | `cur`: the block that is read at the moment. It is `None` before the first title line. |
| 14 | `for L in open(f):` | Loop over the lines of the file. |
| 15 | `    L = L.rstrip('\n')` | Removes the line end. |
| 16 | `    m = re.match(r'-- (\S+) (short\|long) events (\S+) args', L)` | `m`: the match of the start of the line against the pattern of a title line that the function `counted` of `run_sudo.sh` writes: `--`, a tag, `short` or `long`, the word `events`, the event names, and the word `args`. Group 1 is the tag, group 2 is `short` or `long`, and group 3 is the event names with commas between them. `\S+` stands for a text without spaces. |
| 17 | `    if m:` | Tests whether the line is such a title line. |
| 18 | `        cur = dict(tag=m.group(1), len=m.group(2), events=m.group(3).split(','), bytes=None, counts={}, bad=[]); blocks.append(cur); continue` | Then starts a new block: the tag, the length, the list of the event names (split at the commas), no byte total yet, no counts and no bad rows. The block is added to the list, and the loop goes on with the next line. |
| 19 | `    if L.startswith('-- background'):` | Tests whether the line starts with `-- background`, the title line of the idle controls. |
| 20 | `        cur = dict(tag='idle', len='idle', events=[], counts={}, bad=[]); blocks.append(cur); continue` | Then starts a block with the tag `idle` and goes on with the next line. All count rows of the idle controls fall into this one block. |
| 21 | `    p = L.split(',')` | `p`: the fields of the line, split at the commas. |
| 22 | `    if cur is None: continue` | Skips every line that stands before the first title line. |
| 23 | `    if len(p) >= 7 and p[3] == '0' and p[0] in ('asmwrite', 'asmread', 'read', 'write', 'copy', 'asmcopy'):` | Tests whether the line is the row of repetition 0 of `bandwidth`: at least 7 fields, the fourth field is `0`, and the first field is the name of a kernel. The runs of `run_sudo.sh` ask for one repetition, so this is the only repetition row of a run. |
| 24 | `        cur['bytes'] = int(p[4]); cur['gbps'] = float(p[6])` | Then keeps two values of that row. `bytes`: field 5, `total_bytes`, the bytes that all threads moved in the timed interval. `gbps`: field 7, the total rate in GB/s. |
| 25 | `    elif len(p) >= 5 and '/' in p[2]:` | The other case: tests whether the line is a count row of `perf stat`: at least 5 fields, and a slash in the third field, the event name. |
| 26 | `        if p[0].isdigit() and p[3].isdigit():` | Tests whether the count (field 1) and the running time of the counter (field 4) hold digits only. |
| 27 | `            cur['counts'][p[2]] = (int(p[0]), float(p[3]) / 1e9, float(p[4]))` | Then stores three values under the event name: the count, the running time in seconds (field 4 is in nanoseconds, so it is divided by 1e9), and the share of the time for which the counter was running, in percent (field 5). |
| 28 | `        else:` | The other case: the count is not a number. |
| 29 | `            cur['bad'].append(p[2] + ':' + p[0])` | Then notes the row as bad: the event name and the first field, for example `<not counted>`. |

### The idle rates and the pairs of a short and a long run (lines 30 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 30 | `idle = {}` | `idle`: for each event, the rate of the idle control in events per second. |
| 31 | `for b in blocks:` | Loop over the blocks. |
| 32 | `    if b['tag'] == 'idle':` | Takes the idle blocks only. |
| 33 | `        for ev, (c, t, pct) in b['counts'].items():` | Loop over the counts of the block: the event `ev`, its count `c`, its running time `t` in seconds and its percent value `pct`. |
| 34 | `            if pct >= 99.9: idle[ev] = c / t` | Stores the idle rate: the count divided by the running time. An event whose counter ran less than 99.9 percent of the time gets no idle rate. |
| 35 | `by = collections.defaultdict(dict)` | `by`: a dictionary that pairs the blocks. The key is the tag together with the event names. Under it stand the block of the short run and the block of the long run. |
| 36 | `for b in blocks:` | Loop over the blocks. |
| 37 | `    if b['tag'] != 'idle': by[(b['tag'], tuple(b['events']))][b['len']] = b` | Puts every block that is not an idle block under its key, at `short` or at `long`. |

### Compute and print the rates, list the failed checks, set the exit status (lines 38 to 62)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `fail = []` | `fail`: the list of the failed checks, as texts. |
| 39 | `print(f"{'case':28} {'event':44} {'per line':>9} {'bg/line':>8} {'GB/s long':>9}")` | Prints the header row of the output: `case`, `event`, `per line`, `bg/line` and `GB/s long`. The numbers in the format, such as `28` and `>9`, are the widths of the columns in characters. |
| 40 | `for (tag, events), d in sorted(by.items()):` | Loop over the pairs, sorted by tag and event names. `d` holds the short and the long block. |
| 41 | `    if 'short' not in d or 'long' not in d: fail.append(f'{tag} {events}: missing short or long run'); continue` | Check: both a short and a long run exist. If not, a failure is noted and the pair is skipped. |
| 42 | `    s, l = d['short'], d['long']` | `s`, `l`: the block of the short run and the block of the long run. |
| 43 | `    for blk in (s, l):` | Loop over the two blocks. |
| 44 | `        for bad in blk['bad']: fail.append(f"{tag} {blk['len']}: uncounted row {bad}")` | Notes one failure for each bad row of the block (`uncounted row`). |
| 45 | `    if not s.get('bytes') or not l.get('bytes') or l['bytes'] <= s['bytes']: fail.append(f'{tag}: bad byte totals'); continue` | Check: both runs have a byte total, and the long run moved more bytes than the short run. If not, the failure `bad byte totals` is noted and the pair is skipped. |
| 46 | `    dlines = (l['bytes'] - s['bytes']) / 64` | `dlines`: the number of cache lines that the long run moved more than the short run: the difference of the two byte totals divided by 64. |
| 47 | `    for e in events:` | Loop over the event names of the set. |
| 48 | `        for mesh in (0, 1):` | Loop over the two meshes. |
| 49 | `            ev = f'arm_cmn_{mesh}/{e}/'` | `ev`: the event name as `perf` printed it: `arm_cmn_0/NAME/` or `arm_cmn_1/NAME/`. |
| 50 | `            if ev not in l['counts'] or ev not in s['counts']: fail.append(f'{tag} {ev}: counter missing in short or long run'); continue` | Check: the event has a count in both runs. If not, a failure is noted and the event is skipped. |
| 51 | `            (cl, tl, pl), (cs, ts, ps) = l['counts'][ev], s['counts'][ev]` | `cl`, `tl`, `pl`: the count, the running time in seconds and the percent value of the long run. `cs`, `ts`, `ps`: the same values of the short run. |
| 52 | `            if pl < 99.9 or ps < 99.9: fail.append(f'{tag} {ev}: multiplexed ({ps:.0f} % / {pl:.0f} %)')` | Check: both counters ran at least 99.9 percent of the time. If not, the failure `multiplexed` is noted with both percent values. The rate is still printed. |
| 53 | `            if ev in idle:` | Tests whether the event has an idle rate. |
| 54 | `                bg = idle[ev] * (tl - ts) / dlines; bgs = f'{bg:8.4f}'` | Then `bg` is the background per line: the idle rate in events per second, times the difference of the two running times in seconds, divided by `dlines`. `bgs` is the same value as text with 4 decimals. |
| 55 | `            else:` | The other case: no idle rate. |
| 56 | `                bg = 0.0; bgs = '    none'; fail.append(f'{tag} {ev}: no idle control measured')` | Then the background is 0, the text is `none`, and the failure `no idle control measured` is noted. |
| 57 | `            print(f"{tag:28} {ev:44} {(cl - cs) / dlines - bg:9.3f} {bgs} {l['gbps']:9.1f}")` | Prints one row: the tag, the event, the rate per line with 3 decimals, the background per line, and the total rate of the long run in GB/s. The rate per line is the count of the long run minus the count of the short run, divided by `dlines`, minus the background. |
| 58 | `if not by: fail.append('no measurement pairs in the file')` | Check: the file held at least one pair. If not, a failure is noted. |
| 59 | `print('checks failed:', len(fail))` | Prints the number of entries of the failure list. A text that was noted several times counts several times here. |
| 60 | `for x in sorted(set(fail))[:40]: print('  ', x)` | Prints up to 40 of the failure texts, each text once, in sorted order. |
| 61 | `if len(set(fail)) > 40: print('   ...')` | Prints `...` when there are more than 40 different texts. |
| 62 | `sys.exit(1 if fail else 0)` | Ends the script with exit status 1 when a failure was noted, and with exit status 0 when none was noted. |
