# `figs.py` explained, line by line

- Source file: `asct-2026-11-16/figs.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 348 lines, 22250 bytes).
- sha256 of the source when this page was built: `f398a82fd4ec763be32afbc8c35ce297aa825539172fd144d35e449aac50eae2`.

## Short version: purpose

`figs.py` draws the ten figures of the report of the ASCT cross-check. Each function returns one picture as SVG text: eight of them place numbers of `facts.json` and `baseline.json` on axes with the helpers of `svgchart.py`, and two of them draw fixed texts. The file computes no result of its own, apart from label values (differences in percent, factors, a formula for instruction counts) and the bar ends of our own loops in figure 8, which are the middle between two totals.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **`facts.json`**: the output of `facts.py`. It holds the numbers that `facts.py` derived for the report: medians, ranges and counts per cell, and the verdicts.
- **`baseline.json`**: the output of `baseline.py`. It holds the older values of our own loops and the vendor runs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read loop, new read loop**: the names of the report for the old read kernel and the new read kernel. The values of the new read loop are those of `asmread`, where they exist.
- **ASCT loop**: the read loop of the ASCT benchmark binary. By the texts of this file it loads the first 8 bytes of each 64-byte line.
- **`read_1pl`**: a loop of our own benchmark of 2026-11-15 with one load per line.
- **Line**: one cache line of 64 bytes.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings. `facts.py` gives for each cell the median, the smallest and the largest value (the range) and the count.
- **Median**: the middle value of a sorted list of values.
- **Interval**: one timed measurement inside a process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Long-latency miss**: by the word list of the report, a load that had to wait for its line.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Fit**: the straight line that `facts.py` fits to the points of cycles per line against L2 refills per line. `a` is its height at 0 refills and `b` its rise per refill.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Window depth**: the number of 64-byte cache lines that the loads inside the out-of-order window of a core touch. `baseline.json` gives it as a range for each loop.
- **Vendor runs**: two complete ASCT runs that the chip vendor made on its own machines. The report calls the machines Arm reference machine A0 and A1.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Front end**: the command `asct run` of ASCT. It starts the benchmark binary with settings of its own.
- **Counter capture**: the counter code of ASCT, with the name dietperf. The probe build of the benchmark binary holds it.
- **SVG**: Scalable Vector Graphics, a text format for drawings. A web page can hold SVG text directly.
- **Dumbbell chart**: a chart with one row per pair of values. Two dots on a common value axis show the pair, and a line joins them.
- **Marker**: the round dot of one data point.
- **Tooltip**: a small text box that the page shows when the pointer rests on a mark.
- **Hit area**: an invisible shape over a mark. It carries the tooltip text.

## Main flow

1. The file has no top-level run. `report.py` calls one function per figure and places the returned picture into the page. The steps below follow the file order.
2. `fig_size`, figure 3: two panels, one per CPU. Each shows the median rate against the buffer size for the old read loop, the new read loop and the ASCT loop, and the vendor sweeps as thin grey lines (lines 14 to 56).
3. `fig_fall`, figure 4: a dumbbell chart of the rate at 1 MiB against the rate at 8 MiB, one row per loop and CPU and one row per vendor machine (lines 59 to 81).
4. `fig_pad`, figure 7: the same kind of chart for the ASCT loop with 0, 1, 2, 4 and 8 injected NOPs (lines 84 to 106).
5. `fig_cost`, figure 5: two panels with dots of cycles per line against L2 refills per line, and the fitted lines (lines 109 to 148).
6. `fig_prefetch`, figure 6: up to six small panels, one per counter, with the count per line against the buffer size for both CPUs (lines 151 to 189).
7. `fig_chip`, figure 8: horizontal bars of the total rate with all threads, for three of our loops, the ASCT loop and the two vendor machines (lines 192 to 221).
8. `fig_nops`, figure 9: the total at 64+56 and the sums per mesh against the count of injected NOPs, with bands for our two loops and the vendor lines (lines 224 to 279).
9. `fig_threads`, figure 10: a dumbbell chart of the rate of one thread per mesh, with 0 injected NOPs against the best count (lines 282 to 296).
10. `fig_loops`, figure 2, and `fig_path`, figure 1: two drawings from fixed texts, without data (lines 299 to 348).

## Behavior a reader must know

- Scales: the size axes of figures 3 and 6 are logarithmic. Every value axis is linear and starts at 0. The x axis of figure 9 has one place per count of injected NOPs at equal distances, so it is not to scale (line 230).
- A dot or a bar end of the ASCT loop is the median of the processes of its cell. A range line runs from the smallest to the largest value of the cell.
- The ranges of our own loops come from `baseline.json`. In figure 3 they are the `lo` and `hi` values that `facts.py` copied, which are percentiles for most sizes. In figures 8 and 9 they are the smallest and the largest total of 2026-11-15.
- In figure 8 the bar of one of our own loops ends at the middle between its smallest and its largest total, not at a median (lines 200 to 201).
- In figure 3 a size without a value ends a line. For the new read loop a missing value of the assembly form is replaced by the value of the C form (lines 32 to 40).
- The tooltips of figure 3 call the count of every point `processes`. For the points that come from the first run of 2026-11-13 the count is a number of intervals (line 41).
- Each small panel of figure 6 has its own y axis (lines 177 to 184). The test of line 181 can never pass, so the tick step is never below 0.1.
- The instruction counts in the labels of figure 7 are a fixed text and a formula, not counter values (line 92, line 98).
- Figure 10 is left out when no count of injected NOPs above 0 has the highest total (lines 286 to 287).
- The value `last` of line 261 and the list `series` of line 120 are set but not used.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/figs.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (348 lines, 22250 bytes, sha256 `f398a82fd4ec763be32afbc8c35ce297aa825539172fd144d35e449aac50eae2`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text, the helpers of `svgchart.py`, the size ticks and `lab` (lines 1 to 13)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `"""figs.py - the figures of the ASCT cross-check report, drawn from facts.json and baseline.json."""` | Description text of the file: it holds the figures of the report of the ASCT cross-check. They are drawn from `facts.json` and `baseline.json`. |
| 2 | `from svgchart import (ASCT, AXIS, CONTEXT, GRID, INK, INK2, MUTED, NEW, OLD, SURFACE, Scale, dumbbell, esc, fmt,` | Takes the colors and the drawing helpers from the file `svgchart.py` of the same folder. This line names the colors and the first helpers. |
| 3 | `                      frame, hbars, hit_circle, legend, line_panel, marker, text)` | Continues line 2: the other helpers, from `frame` to `text`. |
| 5 | `MI = 1 << 20` | `MI`: 1 MiB in bytes, written as the number 1 shifted by 20 binary places. |
| 6 | `XT = [(MI, '1M'), (2 * MI, '2M'), (4 * MI, '4M'), (8 * MI, '8M'), (16 * MI, '16M'), (32 * MI, '32M'), (64 * MI, None),` | `XT`: the ticks of the size axis as pairs of a size in bytes and a label. This line holds 1, 2, 4, 8, 16 and 32 MiB with the labels `1M` to `32M`, and 64 MiB without a label. |
| 7 | `      (128 * MI, None), (256 * MI, '256M'), (1024 * MI, '1G')]` | Continues line 6: 128 MiB without a label, 256 MiB with the label `256M` and 1024 MiB with the label `1G`. A tick without a label is not drawn. |
| 10 | `def lab(F, b):` | Starts the function `lab`. It returns the label text of a size in bytes, such as `8 MiB`. |
| 11 | `    return F['labels'][str(b)]` | Takes the text from the dictionary `labels` of `facts.json`, which `facts.py` wrote. |

### `fig_size`: figure 3, the read rate of one core against the buffer size (lines 14 to 58)

| Line | Source | Explanation |
|---:|---|---|
| 14 | `def fig_size(F, B):` | Starts the function `fig_size`. `F` is the content of `facts.json` and `B` the content of `baseline.json`. The report shows the result as figure 3. |
| 15 | `    """Rate against buffer size, 1 MiB to 1 GiB, one panel per CPU."""` | Description of the function: the rate against the buffer size from 1 MiB to 1 GiB, with one panel per CPU. |
| 16 | `    w, h = 940, 420` | `w`, `h`: the picture is 940 units wide and 420 high. |
| 17 | `    out = [frame(w, h, 'Read rate of one core against buffer size',` | Opens the picture with its title, `Read rate of one core against buffer size`. The call goes on in line 18. |
| 18 | `                 'Three read loops on CRB CPUs 2 and 41 and the ASCT loop on two Arm reference machines.')]` | Continues line 17: the description for screen readers. It names three read loops on the CPUs 2 and 41 of CRB and the ASCT loop on two Arm reference machines. |
| 19 | `    out.append(legend([('old read', OLD, 'line'), ('new read', NEW, 'line'), ('ASCT read, CRB', ASCT, 'line'),` | Draws the legend at the top. The old read loop is a blue line with markers, the new read loop an orange one and the ASCT loop on CRB a green one. The call goes on in line 20. |
| 20 | `                       ('ASCT read, Arm reference machines (other firmware)', CONTEXT, 'thin')], 56, 22))` | Continues line 19: the ASCT loop on the Arm reference machines is a thin grey line. Its legend text says that they have another firmware. |
| 21 | `    for i, cpu in enumerate(F['cpus']):` | Starts a loop over the two CPUs. Each gets one panel. |
| 22 | `        c = F['one'][str(cpu)]` | `c`: the values of this CPU from `facts.json`. |
| 23 | `        x0 = 56 + i * 460` | `x0`: the left edge of the panel, 56 px for the first CPU and 516 px for the second. |
| 24 | `        series = []` | `series`: the lines of the panel. It starts empty. |
| 25 | `        for name, v in B['vendor'].items():` | Starts a loop over the two vendor runs of `baseline.json`. |
| 26 | `            pts = [(b, r, None, None, None) for b, r in v['sweep'] if MI <= b <= 1024 * MI]` | `pts`: the points of the vendor sweep from 1 MiB to 1 GiB. x is the buffer size and y the rate in GB/s. A point has no range and no tooltip. |
| 27 | `            series.append({'name': name, 'color': CONTEXT, 'pts': pts, 'kind': 'thin', 'nomarker': True})` | Adds the vendor run as a thin grey line without markers. The same two vendor lines appear in both panels. |
| 28 | `        for key, color, nm in (('old', OLD, 'old read'), ('new', NEW, 'new read'), ('asct', ASCT, 'ASCT read')):` | Starts a loop over the three loops on CRB: the old read loop, the new read loop and the ASCT loop, each with its color. |
| 29 | `            pts = []` | `pts`: the points of the line piece that is built now. |
| 30 | `            for b in F['sizes']:` | Starts a loop over the 16 sizes. |
| 31 | `                v = c[key].get(str(b))` | `v`: the entry of this loop and size: the median, the range and the count. |
| 32 | `                if key == 'new' and not v:      # 1 GiB exists only for the C form of the new loop (first run)` | For the new read loop, when the assembly form has no value. Comment: 1 GiB exists only for the C form of the new loop, from the first run. |
| 33 | `                    v = c['newc'].get(str(b))` | Then the value of the C form is taken. |
| 34 | `                if b < MI:` | A size below 1 MiB, which is 32 KiB, |
| 35 | `                    continue` | is not drawn. |
| 36 | `                if not v:           # a missing size ends the line: no line is drawn across a size without a run` | When the size has no value. Comment: a missing size ends the line, so no line is drawn across a size without a run. |
| 37 | `                    if pts:` | When points were collected before the gap, |
| 38 | `                        series.append({'name': nm, 'color': color, 'pts': pts})` | they become one line of their own, |
| 39 | `                    pts = []` | and a new line piece starts. |
| 40 | `                    continue` | The loop goes to the next size. |
| 41 | `                tip = f'{nm}, CPU {cpu}, {lab(F, b)}: {v["median"]:.2f} GB/s (range {v["lo"]:.2f} to {v["hi"]:.2f}, {v["n"]} processes)'` | `tip`: the tooltip text of the point: the loop, the CPU, the size, the median rate with 2 decimals, the range and the count. The text names the count `processes`. For a value from the first run of 2026-11-13, `facts.py` stores the number of timed intervals in `n`, so the word does not fit there. |
| 42 | `                pts.append((b, v['median'], v['lo'], v['hi'], tip))` | Adds the point. x is the buffer size and y the median rate. The low and the high end of the range come from `lo` and `hi` of the entry. |
| 43 | `            if pts:` | When points are left after the last size, |
| 44 | `                series.append({'name': nm, 'color': color, 'pts': pts})` | they become the last line of this loop. |
| 45 | `        out.append(line_panel(x0, 66, 400, 290, series, XT, [0, 20, 40, 60, 80, 100, 120], xlog=True,` | Draws the panel with `line_panel`: 400 px wide and 290 px high, with its top edge at 66 px. The x axis is logarithmic and runs from 1 MiB to 1 GiB. The y axis is linear, from 0 to 120 GB/s, with a tick every 20 GB/s. Each point is a marker at the median. A thin vertical line at a point shows its range when the range is larger than 3 px. The call goes on in lines 46 to 47. |
| 46 | `                              xlabel='buffer size (M = MiB, G = GiB), log scale', yunit='GB/s' if i == 0 else None,` | Continues line 45: the title of the x axis, which says that M means MiB, G means GiB and the scale is logarithmic. The unit `GB/s` is written at the first panel only. |
| 47 | `                              title=f'CPU {cpu}', vmark=(8 * MI, '8 MiB')))` | Continues line 45: the panel title with the CPU number, and a vertical reference line at 8 MiB with the label `8 MiB`. |
| 48 | `        # the three values at 8 MiB, as a small key inside the panel` | Comment: the three values at 8 MiB follow, as a small key inside the panel. |
| 49 | `        bx, by = x0 + 250, 84` | `bx`, `by`: the position of that key, 250 px right of the left edge of the panel and near its top. |
| 50 | `        out.append(text(bx, by, 'at 8 MiB', 11, MUTED))` | Writes the heading `at 8 MiB` of the key. |
| 51 | `        for j, (key, color, nm) in enumerate((('old', OLD, 'old'), ('new', NEW, 'new'), ('asct', ASCT, 'ASCT'))):` | Starts a loop over the three loops, with the short names `old`, `new` and `ASCT`. |
| 52 | `            v = c[key].get(str(8 * MI))` | `v`: the entry of the loop at 8 MiB. |
| 53 | `            if v:` | When it exists: |
| 54 | `                out.append(marker(bx + 4, by + 14 + 15 * j, color, r=3))` | draws a small marker in the color of the loop, |
| 55 | `                out.append(text(bx + 14, by + 18 + 15 * j, f'{nm} {v["median"]:.1f} GB/s', 11.5, INK, weight=600))` | and writes the short name and the median rate at 8 MiB with 1 decimal, in bold. For the new read loop this is the value of the assembly form. |
| 56 | `    return ''.join(out) + '</svg>'` | Returns the picture and closes it. |

### `fig_fall`: figure 4, the rate at 1 MiB against the rate at 8 MiB (lines 59 to 83)

| Line | Source | Explanation |
|---:|---|---|
| 59 | `def fig_fall(F, B):` | Starts the function `fig_fall`. The report shows the result as figure 4. |
| 60 | `    """1 MiB against 8 MiB for every loop and machine."""` | Description of the function: 1 MiB against 8 MiB for every loop and machine. |
| 61 | `    rows = []` | `rows`: the rows of the chart. It starts empty. |
| 62 | `    for cpu in F['cpus']:` | Starts a loop over the two CPUs. |
| 63 | `        c = F['one'][str(cpu)]` | `c`: the values of this CPU. |
| 64 | `        for key, color, nm in (('old', OLD, 'old read'), ('new', NEW, 'new read'), ('asct', ASCT, 'ASCT read')):` | Starts a loop over the old read loop, the new read loop and the ASCT loop. |
| 65 | `            a, b = c[key][str(MI)], c[key][str(8 * MI)]` | `a`, `b`: the entries of the loop at 1 MiB and at 8 MiB. |
| 66 | `            if not a or not b:` | When one of the two is missing, |
| 67 | `                continue` | the loop gets no row. |
| 68 | `            rows.append({'label': f'{nm}, CPU {cpu}', 'sub': 'CRB', 'a': a['median'], 'b': b['median'], 'ca': color, 'cb': color,` | Adds one row. The label is the loop and the CPU, and the second label line is `CRB`. Value `a` is the median rate at 1 MiB and value `b` the median rate at 8 MiB. Both dots have the color of the loop. The dictionary goes on in lines 69 to 71. |
| 69 | `                         'tipa': f'{nm}, CPU {cpu}, 1 MiB: {a["median"]:.2f} GB/s (range {a["lo"]:.2f} to {a["hi"]:.2f})',` | Continues line 68: the tooltip of the 1 MiB dot with the median and the range, in GB/s with 2 decimals. |
| 70 | `                         'tipb': f'{nm}, CPU {cpu}, 8 MiB: {b["median"]:.2f} GB/s (range {b["lo"]:.2f} to {b["hi"]:.2f})',` | Continues line 68: the tooltip of the 8 MiB dot. |
| 71 | `                         'delta': f'{(b["median"] / a["median"] - 1) * 100:+.1f} %'})` | Continues line 68: `delta`, the change from 1 MiB to 8 MiB in percent. It is the ratio of the two medians minus 1, times 100, with a sign and 1 decimal. The chart writes it at the right edge of the row. |
| 72 | `    for name, tag in (('a0_numa2_ddr_7200', 'Arm reference machine A0'), ('a1_numa2_ddr_8000', 'Arm reference machine A1')):` | Starts a loop over the two vendor runs. Their display names are `Arm reference machine A0` and `Arm reference machine A1`. |
| 73 | `        v = F['vendor_ratio'][name]` | `v`: the rates at 1 MiB and 8 MiB and their ratio, from `vendor_ratio` of `facts.json`. |
| 74 | `        cpu = B['vendor'][name]['cpu'][0]` | `cpu`: the CPU of the one-core sweep of the vendor run, from `baseline.json`. |
| 75 | `        rows.append({'label': 'ASCT read', 'sub': f'{tag}, CPU {cpu}', 'a': v['m1'], 'b': v['m8'], 'ca': CONTEXT, 'cb': CONTEXT,` | Adds one grey row for the ASCT loop on this machine. The second label line names the machine and the CPU. The dictionary goes on in lines 76 to 78. |
| 76 | `                     'tipa': f'ASCT read, {tag}, 1 MiB: {v["m1"]:.2f} GB/s (one process, vendor run)',` | Continues line 75: the tooltip of the 1 MiB dot. It says that the value is one process of the vendor run. |
| 77 | `                     'tipb': f'ASCT read, {tag}, 8 MiB: {v["m8"]:.2f} GB/s (one process, vendor run)',` | Continues line 75: the tooltip of the 8 MiB dot. |
| 78 | `                     'delta': f'{(v["ratio"] - 1) * 100:+.1f} %'})` | Continues line 75: `delta`, the ratio of line 73 minus 1 in percent, with a sign and 1 decimal. |
| 79 | `    return dumbbell(940, rows, 250, 800, [0, 20, 40, 60, 80, 100, 120], 'read rate, GB/s', 'Read rate at 1 MiB and at 8 MiB',` | Draws the chart with `dumbbell`. The value axis is linear, from 0 to 120 GB/s with a tick every 20 GB/s, between 250 px and 800 px. Its unit text is `read rate, GB/s`. The call goes on in lines 80 to 81. |
| 80 | `                    'One row per loop and machine. The hollow dot is the rate at 1 MiB, the filled dot the rate at 8 MiB.',` | Continues line 79: the description for screen readers. It says that the hollow dot is the rate at 1 MiB and the filled dot the rate at 8 MiB. |
| 81 | `                    ('1 MiB', '8 MiB'), rowh=38, top=52)` | Continues line 79: the key names `1 MiB` and `8 MiB`, a row height of 38 px and the first row at 52 px. |

### `fig_pad`: figure 7, the ASCT loop with injected NOPs on one core (lines 84 to 108)

| Line | Source | Explanation |
|---:|---|---|
| 84 | `def fig_pad(F):` | Starts the function `fig_pad`. The report shows the result as figure 7. |
| 85 | `    """The ASCT loop with injected NOPs on one core: 1 MiB against 8 MiB."""` | Description of the function: the ASCT loop with injected NOPs on one core, 1 MiB against 8 MiB. |
| 86 | `    rows = []` | `rows`: the rows of the chart. It starts empty. |
| 87 | `    for cpu in F['cpus']:` | Starts a loop over the two CPUs. |
| 88 | `        c = F['one'][str(cpu)]` | `c`: the values of this CPU. |
| 89 | `        for nn in (0, 1, 2, 4, 8):` | Starts a loop over the counts 0, 1, 2, 4 and 8 of injected NOPs. |
| 90 | `            if nn == 0:` | For 0 injected NOPs: |
| 91 | `                a, b = c['asct'][str(MI)], c['asct'][str(8 * MI)]` | `a`, `b`: the ASCT entries of part U at 1 MiB and at 8 MiB. |
| 92 | `                inst = '1.4 instructions per line'` | `inst`: the fixed text `1.4 instructions per line` for the second label line. |
| 93 | `            else:` | For the other counts: |
| 94 | `                r = F['pad'].get(f'{cpu}.{nn}')` | `r`: the row of part N for this CPU and count, from `pad` of `facts.json`. |
| 95 | `                if not r:` | When it is missing, |
| 96 | `                    continue` | the count gets no row. |
| 97 | `                a, b = r[str(MI)], r[str(8 * MI)]` | `a`, `b`: the entries of the row at 1 MiB and at 8 MiB. |
| 98 | `                inst = f'{6 + 3 * nn} instructions per line'` | `inst`: the text for the second label line. The number of instructions per line is computed as 6 plus 3 times the count of injected NOPs. It is not a counter value. |
| 99 | `            nm = f'{nn} injected NOPs, CPU {cpu}'` | `nm`: the label of the row, the count of injected NOPs and the CPU. |
| 100 | `            rows.append({'label': nm, 'sub': inst, 'a': a['median'], 'b': b['median'], 'ca': ASCT, 'cb': ASCT,` | Adds one green row. Value `a` is the median rate at 1 MiB and value `b` the median rate at 8 MiB. The dictionary goes on in lines 101 to 103. |
| 101 | `                         'tipa': f'ASCT read, {nm}, 1 MiB: {a["median"]:.2f} GB/s (range {a["lo"]:.2f} to {a["hi"]:.2f}, {a["n"]} processes)',` | Continues line 100: the tooltip of the 1 MiB dot with the median, the range and the number of processes. |
| 102 | `                         'tipb': f'ASCT read, {nm}, 8 MiB: {b["median"]:.2f} GB/s (range {b["lo"]:.2f} to {b["hi"]:.2f}, {b["n"]} processes)',` | Continues line 100: the tooltip of the 8 MiB dot. |
| 103 | `                         'delta': f'{(b["median"] / a["median"] - 1) * 100:+.1f} %'})` | Continues line 100: `delta`, the change from 1 MiB to 8 MiB in percent, with a sign and 1 decimal. |
| 104 | `    return dumbbell(940, rows, 250, 800, [0, 20, 40, 60, 80, 100, 120], 'read rate, GB/s', 'ASCT read loop with injected NOPs: 1 MiB and 8 MiB',` | Draws the chart with `dumbbell`, with the same value axis as figure 4: linear, from 0 to 120 GB/s, in GB/s. The call goes on in lines 105 to 106. |
| 105 | `                    'One row per count of injected NOPs and CPU. The hollow dot is the rate at 1 MiB, the filled dot the rate at 8 MiB.',` | Continues line 104: the description for screen readers. The hollow dot is the rate at 1 MiB and the filled dot the rate at 8 MiB. |
| 106 | `                    ('1 MiB', '8 MiB'), rowh=38, top=52)` | Continues line 104: the key names, the row height and the position of the first row. |

### `fig_cost`: figure 5, cycles per line against L2 refills per line (lines 109 to 150)

| Line | Source | Explanation |
|---:|---|---|
| 109 | `def fig_cost(F, B):` | Starts the function `fig_cost`. The report shows the result as figure 5. |
| 110 | `    """Cycles per line against the share of lines refilled into L2."""` | Description of the function: the cycles per line against the share of lines that are refilled into L2. |
| 111 | `    w, h = 940, 380` | `w`, `h`: the picture is 940 units wide and 380 high. |
| 112 | `    out = [frame(w, h, 'Core cycles per line against L2 refills per line',` | Opens the picture with its title, `Core cycles per line against L2 refills per line`. The call goes on in line 113. |
| 113 | `                 'ASCT loop and new read loop, CPUs 2 and 41, sizes 1 to 32 MiB.')]` | Continues line 112: the description for screen readers. It names the ASCT loop and the new read loop, the CPUs 2 and 41 and the sizes 1 to 32 MiB. |
| 114 | `    out.append(legend([('old read', OLD, 'dot'), ('new read', NEW, 'dot'), ('ASCT read', ASCT, 'dot'),` | Draws the legend: a blue dot for the old read loop, an orange dot for the new read loop and a green dot for the ASCT loop. The call goes on in line 115. |
| 115 | `                       ('straight line fitted to the dots', INK2, 'thin')], 56, 22))` | Continues line 114: a thin dark grey line stands for a straight line that is fitted to the dots. |
| 116 | `    for i, cpu in enumerate(F['cpus']):` | Starts a loop over the two CPUs. Each gets one panel. |
| 117 | `        c = F['one'][str(cpu)]` | `c`: the values of this CPU from `facts.json`. |
| 118 | `        x0, y0, pw, ph = 56 + i * 460, 62, 400, 250` | The panel is 400 px wide and 250 px high. Its left edge is at 56 px for the first CPU and at 516 px for the second. |
| 119 | `        sx, sy = Scale(0, 1, x0, x0 + pw), Scale(0, 3.5, y0 + ph, y0)` | `sx`: the x scale, linear from 0 to 1 L2 refill per line. `sy`: the y scale, linear from 0 to 3.5 cycles per line. The value 0 is at the bottom. |
| 120 | `        series, hits = [], []` | `series` and `hits` start empty. The function uses `hits` for the tooltips and does not use `series`. |
| 121 | `        out.append(line_panel(x0, y0, pw, ph, [], [(0, '0'), (0.2, '0.2'), (0.4, '0.4'), (0.6, '0.6'), (0.8, '0.8'), (1.0, '1.0')],` | Draws the empty panel with `line_panel`: the axes and the grid without any series. The x ticks run from 0 to 1.0 in steps of 0.2. The call goes on in lines 122 to 123. |
| 122 | `                              [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5], xlog=False, xlabel='L2 refills per line (share of lines that enter L2 from outside)',` | Continues line 121: the y ticks run from 0 to 3.5 in steps of 0.5. The x axis is linear. Its title says that an L2 refill per line is the share of lines that enter L2 from outside. |
| 123 | `                              title=f'CPU {cpu}: core cycles per line', ynd=1))` | Continues line 121: the panel title with the CPU number, and 1 decimal for the y tick labels. |
| 124 | `        for key, color, nm, fitkey in (('oldread', OLD, 'old read', None), ('asmread', NEW, 'new read', 'fit_new')):` | Starts a loop over our two loops of 2026-11-15: the old read loop (`oldread`, blue, no fitted line) and the new read loop (`asmread`, orange, with the fit `fit_new`). |
| 125 | `            for b in F['sizes']:` | Starts a loop over the 16 sizes. |
| 126 | `                z = B['zs'].get(f'{key}.{cpu}.{b}')` | `z`: the counter values of this loop, CPU and size from the block `zs` of `baseline.json`. |
| 127 | `                if not z:` | A size without values |
| 128 | `                    continue` | is skipped. |
| 129 | `                out.append(marker(sx(z['r']), sy(z['cyc']), color, r=3))` | Draws one dot. x is `r`, the L2 refills per line. y is `cyc`, the cycles per line. |
| 130 | `                hits.append(hit_circle(sx(z['r']), sy(z['cyc']), f'{nm}, CPU {cpu}, {lab(F, b)}: {z["cyc"]:.3f} cycles and {z["r"]:.3f} L2 refills per line', r=8))` | Adds the tooltip of the dot: the loop, the CPU, the size, the cycles and the L2 refills per line with 3 decimals. |
| 131 | `            if fitkey:` | For the new read loop only: |
| 132 | `                f = c[fitkey]` | `f`: its fit from `facts.json`. |
| 133 | `                out.append(f'<line x1="{sx(0):.1f}" y1="{sy(f["a"]):.1f}" x2="{sx(1):.1f}" y2="{sy(f["a"] + f["b"]):.1f}" stroke="{INK2}" stroke-width="1.2"/>')` | Draws the fitted line from x = 0 to x = 1. Its height is `a` at x = 0 and `a + b` at x = 1. |
| 134 | `        for b in F['sizes']:` | Starts a loop over the 16 sizes, for the ASCT loop. |
| 135 | `            k = c['cnt'].get(str(b))` | `k`: the counter medians of the ASCT loop at this size. |
| 136 | `            if not k or 'l2d_cache_refill' not in k or not (MI <= b <= 32 * MI):` | A size is drawn only when it was counted, holds `l2d_cache_refill` and lies from 1 MiB to 32 MiB. |
| 137 | `                continue` | Any other size is skipped. |
| 138 | `            out.append(marker(sx(k['l2d_cache_refill']), sy(k['cpu_cycles']), ASCT, r=3))` | Draws one green dot. x is `l2d_cache_refill` per line and y is `cpu_cycles` per line. |
| 139 | `            hits.append(hit_circle(sx(k['l2d_cache_refill']), sy(k['cpu_cycles']),` | Adds the tooltip of the dot. The call goes on in line 140. |
| 140 | `                                   f'ASCT read, CPU {cpu}, {lab(F, b)}: {k["cpu_cycles"]:.3f} cycles and {k["l2d_cache_refill"]:.3f} L2 refills per line', r=8))` | Continues line 139: the tooltip text with the CPU, the size, the cycles and the L2 refills per line with 3 decimals. |
| 141 | `        if c.get('fit'):` | When `facts.json` holds a fit for the ASCT loop: |
| 142 | `            f = c['fit']` | `f`: that fit. |
| 143 | `            out.append(f'<line x1="{sx(0):.1f}" y1="{sy(f["a"]):.1f}" x2="{sx(1):.1f}" y2="{sy(f["a"] + f["b"]):.1f}" stroke="{INK2}" stroke-width="1.2"/>')` | Draws its line from x = 0 to x = 1, in the same way as line 133. |
| 144 | `            out.append(text(x0 + 8, y0 + ph - 30, f'ASCT: {f["a"]:.2f} + {f["b"]:.2f} x refills', 11.5, INK, weight=600))` | Writes the formula of the ASCT fit in bold near the bottom left of the panel: `a` and `b` with 2 decimals. |
| 145 | `        fn = c['fit_new']` | `fn`: the fit of the new read loop. |
| 146 | `        out.append(text(x0 + 8, y0 + ph - 12, f'new read: {fn["a"]:.2f} + {fn["b"]:.2f} x refills', 11.5, INK, weight=600))` | Writes the formula of that fit below the first one. |
| 147 | `        out.append(''.join(hits))` | Adds the hit areas of this panel after its marks. |
| 148 | `    return ''.join(out) + '</svg>'` | Returns the picture and closes it. |

### `PF_PANELS` and `fig_prefetch`: figure 6, prefetch counters per line against size (lines 151 to 191)

| Line | Source | Explanation |
|---:|---|---|
| 151 | `PF_PANELS = [('l2d_cache_hwprf', 'L2 hardware prefetch events'), ('l1d_cache_hwprf', 'L1 hardware prefetch events'),` | `PF_PANELS`: the list of the small panels of figure 6, as pairs of a counter name and a panel title. This line holds the hardware prefetch events of L2 and of L1. |
| 152 | `             ('l2d_cache_l1hwprf', 'L2 accesses by the L1 prefetcher'), ('l2d_cache_refill_l1hwprf', 'L2 refills by the L1 prefetcher'),` | Continues line 151: the L2 accesses and the L2 refills that the L1 prefetcher caused. |
| 153 | `             ('l1d_cache_lmiss_rd', 'L1 long-latency read misses'), ('l2d_cache_lmiss_rd', 'L2 long-latency read misses')]` | Continues line 151: the read misses with a long latency of L1 and of L2. |
| 156 | `def fig_prefetch(F):` | Starts the function `fig_prefetch`. The report shows the result as figure 6. |
| 157 | `    """Prefetch-related core counters per line against size, small multiples."""` | Description of the function: counters that have to do with prefetching, per line against the size, as a set of small panels. |
| 158 | `    panels = [(n, t) for n, t in PF_PANELS if any(n in F['one'][str(c)]['cnt'].get(str(8 * MI), {}) for c in F['cpus'])]` | `panels`: the entries of `PF_PANELS` whose counter has a value at 8 MiB on at least one CPU. |
| 159 | `    cols = 3` | `cols`: 3 panels stand side by side. |
| 160 | `    rows = (len(panels) + cols - 1) // cols` | `rows`: the number of panel rows, which is the number of panels divided by 3 and rounded up. |
| 161 | `    w, h = 940, 56 + rows * 218` | `w`, `h`: the picture is 940 units wide. Its height is 56 plus 218 for each panel row. |
| 162 | `    out = [frame(w, h, 'Prefetch-related core counters per line against buffer size', 'ASCT read loop, CPUs 2 and 41.')]` | Opens the picture with its title, `Prefetch-related core counters per line against buffer size`. The description names the ASCT loop and the CPUs 2 and 41. |
| 163 | `    out.append(legend([('CPU 2', INK2, 'line'), ('CPU 41', MUTED, 'hollow')], 50, 22))` | Draws the legend: CPU 2 is a dark grey line with filled markers, and CPU 41 a grey line with hollow markers. |
| 164 | `    xt = [(MI, '1M'), (2 * MI, '2M'), (4 * MI, '4M'), (8 * MI, '8M'), (16 * MI, '16M'), (32 * MI, '32M')]` | `xt`: the ticks of the size axis, from 1 MiB to 32 MiB with the labels `1M` to `32M`. |
| 165 | `    for i, (name, title) in enumerate(panels):` | Starts a loop over the panels. |
| 166 | `        vals = []` | `vals`: all values of the panel, for the choice of its y axis. |
| 167 | `        series = []` | `series`: the two lines of the panel. |
| 168 | `        for cpu, color, kind in ((2, INK2, 'line'), (41, MUTED, 'hollow')):` | Starts a loop over the two CPUs with their colors and marker kinds. |
| 169 | `            pts = []` | `pts`: the points of this CPU. |
| 170 | `            for b in F['sizes']:` | Starts a loop over the 16 sizes. |
| 171 | `                k = F['one'][str(cpu)]['cnt'].get(str(b))` | `k`: the counter medians of this CPU and size, from `cnt` of `facts.json`. |
| 172 | `                if not k or name not in k or not (MI <= b <= 32 * MI):` | A size is used only when it was counted, holds this counter and lies from 1 MiB to 32 MiB. |
| 173 | `                    continue` | Any other size is skipped. |
| 174 | `                pts.append((b, k[name], None, None, f'{title}, CPU {cpu}, {lab(F, b)}: {k[name]:.3f} per line'))` | Adds the point. x is the buffer size and y the count per line. The tooltip gives the panel title, the CPU, the size and the value with 3 decimals. |
| 175 | `                vals.append(k[name])` | Keeps the value for the choice of the axis. |
| 176 | `            series.append({'name': f'CPU {cpu}', 'color': color, 'pts': pts, 'kind': kind})` | Adds the line of this CPU. |
| 177 | `        top = max(vals + [0.1])` | `top`: the largest value of the panel, or 0.1 when all values are smaller. |
| 178 | `        step = 0.5 if top <= 2 else 1 if top <= 4 else 2 if top <= 8 else 5 if top <= 20 else 10` | `step`: the distance between two y ticks. It is 0.5 for a top value up to 2, 1 up to 4, 2 up to 8, 5 up to 20 and 10 above that. |
| 179 | `        if top <= 0.5:` | For a top value up to 0.5 |
| 180 | `            step = 0.1` | the step is 0.1. |
| 181 | `        if top <= 0.05:` | Tests for a top value up to 0.05. By line 177 the top value is at least 0.1. So this test never passes. |
| 182 | `            step = 0.01` | The step 0.01, which is never set for the reason of line 181. |
| 183 | `        n = int(top / step) + 1` | `n`: the number of steps. It is chosen in a way that the highest tick lies above the largest value. |
| 184 | `        yt = [round(step * j, 4) for j in range(n + 1)]` | `yt`: the y ticks, from 0 in steps of `step`. So every panel has its own y axis, and the heights of two panels cannot be compared directly. |
| 185 | `        x0 = 50 + (i % cols) * 300` | `x0`: the left edge of the panel. The three columns are 300 px apart. |
| 186 | `        y0 = 70 + (i // cols) * 218` | `y0`: the top edge of the panel. The panel rows are 218 px apart. |
| 187 | `        out.append(line_panel(x0, y0, 240, 130, series, xt, yt, xlog=True, title=title, vmark=(8 * MI, ''),` | Draws the panel with `line_panel`: 240 px wide and 130 px high. The x axis is logarithmic, from 1 MiB to 32 MiB. The y axis is linear and starts at 0. A vertical reference line without a label marks 8 MiB. The call goes on in line 188. |
| 188 | `                              ynd=2 if step < 0.1 else 1 if step < 1 else 0, xlabel='buffer size' if i // cols == rows - 1 else None))` | Continues line 187: the y tick labels have 2 decimals for a step below 0.1, 1 decimal for a step below 1 and none otherwise. Only the panels of the last row get the title `buffer size` of the x axis. |
| 189 | `    return ''.join(out) + '</svg>'` | Returns the picture and closes it. |

### `fig_chip`: figure 8, the totals with all threads (lines 192 to 223)

| Line | Source | Explanation |
|---:|---|---|
| 192 | `def fig_chip(F, B):` | Starts the function `fig_chip`. The report shows the result as figure 8. |
| 193 | `    """Totals at 64+56."""` | Description of the function: the totals at 64+56. |
| 194 | `    ch = F['chip']` | `ch`: the results for the whole chip from `facts.json`. |
| 195 | `    L = {r[0]: r for r in B['chip']['loops']}` | `L`: the rows of the list `loops` of `baseline.json`, block `chip`, by the name of the loop. A row holds the name, a short description, the window depth in lines, the smallest and the largest total in GB/s and the number of intervals. They are the values of 2026-11-15. |
| 196 | `    rows = []` | `rows`: the bars of the chart. It starts empty. |
| 198 | `    def ours(name, labeltxt, color):` | Starts the helper function `ours`. It adds the bar of one of our own loops. |
| 199 | `        r = L[name]` | `r`: the row of the loop. |
| 200 | `        mid = (r[3] + r[4]) / 2` | `mid`: the middle between the smallest and the largest total of the loop. |
| 201 | `        rows.append({'label': labeltxt, 'sub': f'{r[1]}; window {r[2].replace("-", " to ")} lines', 'v': mid, 'lo': r[3], 'hi': r[4], 'color': color,` | Adds the bar. The second label line holds the description and the window depth. The bar ends at `mid`, which is not a median. The range line on the bar runs from the smallest to the largest total. The dictionary goes on in line 202. |
| 202 | `                     'value_label': f'{r[3]:.0f} to {r[4]:.0f}', 'tip': f'{labeltxt}: {r[3]} to {r[4]} GB/s over {r[5]} intervals (2026-11-15)'})` | Continues line 201: the value label shows the smallest and the largest total without decimals. The tooltip gives both in GB/s, the number of intervals and the date 2026-11-15. |
| 203 | `    ours('old read', 'old read', OLD)` | Adds the blue bar of the old read loop. |
| 204 | `    ours('new read (asmread)', 'new read', NEW)` | Adds the orange bar of the new read loop, from the row of its assembly form `asmread`. |
| 205 | `    ours('read_1pl', 'our one-load-per-line loop (read_1pl)', CONTEXT)` | Adds a grey bar for `read_1pl`, our loop with one load per line. |
| 206 | `    b = ch['base']` | `b`: the ASCT cell at 64+56 with 0 injected NOPs. |
| 207 | `    rows.append({'label': 'ASCT read, 0 injected NOPs', 'sub': f'8 ldr x per 8 lines; {b["n"]} processes', 'v': b['median'], 'lo': b['lo'], 'hi': b['hi'], 'color': ASCT,` | Adds its green bar. The bar ends at the median total of the processes, and the range line runs from the smallest to the largest total. The second label line holds the fixed text `8 ldr x per 8 lines` and the number of processes. The dictionary goes on in line 208. |
| 208 | `                 'value_label': f'{b["median"]:.1f}', 'tip': f'ASCT read, 0 NOPs: median {b["median"]:.1f} GB/s, range {b["lo"]:.1f} to {b["hi"]:.1f}, {b["n"]} processes'})` | Continues line 207: the value label is the median with 1 decimal. The tooltip gives the median, the range and the number of processes. |
| 209 | `    n = ch['bestN']` | `n`: the count of injected NOPs with the highest median total, from `bestN` of `facts.json`. |
| 210 | `    if n is not None and str(n) in ch['nops'] and n != 0:` | Only when such a count exists, has a cell and is not 0: |
| 211 | `        v = ch['nops'][str(n)]` | `v`: its cell. |
| 212 | `        rows.append({'label': f'ASCT read, {n} injected NOPs', 'sub': f'the N with the highest total; {v["n"]} processes', 'v': v['median'], 'lo': v['lo'], 'hi': v['hi'], 'color': ASCT,` | adds a second green bar for the ASCT loop with this count of injected NOPs. It ends at the median total and has the range line. The dictionary goes on in line 213. |
| 213 | `                     'value_label': f'{v["median"]:.1f}', 'tip': f'ASCT read, {n} NOPs: median {v["median"]:.1f} GB/s, range {v["lo"]:.1f} to {v["hi"]:.1f}, {v["n"]} processes'})` | Continues line 212: the value label and the tooltip, as in line 208. |
| 214 | `    for name, tag in (('a0_numa2_ddr_7200', 'A0'), ('a1_numa2_ddr_8000', 'A1')):` | Starts a loop over the two vendor runs, with the short names `A0` and `A1`. |
| 215 | `        v = B['vendor'][name]` | `v`: the values of the vendor run from `baseline.json`. |
| 216 | `        bw = dict((n, x) for n, _, x in v['nops'])[0]` | `bw`: the bandwidth of the vendor run at 0 injected NOPs, in GB/s. It is the third field of the row with 0 injected NOPs of its list `nops`. |
| 217 | `        rows.append({'label': f'ASCT read, 0 injected NOPs, Arm machine {tag}', 'sub': f'vendor run, {v["cpus"]} CPUs, {v["numa"]} NUMA nodes, firmware {v["bios"].split("-")[-1]}',` | Adds one grey bar for the ASCT loop with 0 injected NOPs on this machine. The second label line gives the number of CPUs, the number of NUMA nodes and the firmware version, which is the piece after the last hyphen of the firmware text. The dictionary goes on in lines 218 to 219. |
| 218 | `                     'v': bw, 'lo': None, 'hi': None, 'color': CONTEXT, 'value_label': f'{bw:.1f}',` | Continues line 217: the bar ends at `bw`. It has no range line. The value label is `bw` with 1 decimal. |
| 219 | `                     'tip': f'Vendor run on Arm reference machine {tag}: {bw} GB/s at 0 injected NOPs (loaded-latency table, one process)'})` | Continues line 217: the tooltip. It says that the value comes from the table of the loaded latency and is one process. |
| 220 | `    return hbars(940, rows, 390, 850, [0, 100, 200, 300, 400, 500, 600, 700], 'total read rate, GB/s',` | Draws the chart with `hbars`. The value axis is linear, from 0 to 700 GB/s with a tick every 100 GB/s, between 390 px and 850 px. Its unit text is `total read rate, GB/s`. The bars start at 0. The call goes on in line 221. |
| 221 | `                 'Total read rate with all threads', 'CRB: 64+56 threads. Old read, new read, a one-load-per-line loop and the ASCT loop. Grey: other loops and other machines.', rowh=40, top=26)` | Continues line 220: the title `Total read rate with all threads` and the description for screen readers. It says that grey stands for other loops and other machines. |

### `fig_nops`: figure 9, the total against the injected NOPs (lines 224 to 281)

| Line | Source | Explanation |
|---:|---|---|
| 224 | `def fig_nops(F, B):` | Starts the function `fig_nops`. The report shows the result as figure 9. |
| 225 | `    """Total against injected NOPs, ordinal x axis."""` | Description of the function: the total against the injected NOPs, with an x axis that has one place per count. |
| 226 | `    ch = F['chip']` | `ch`: the results for the whole chip from `facts.json`. |
| 227 | `    ns = [n for n in (0, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100, 180) if str(n) in ch['nops']]` | `ns`: the counts of injected NOPs that have a cell, out of the 16 counts from 0 to 180. |
| 228 | `    w, h = 940, 430` | `w`, `h`: the picture is 940 units wide and 430 high. |
| 229 | `    x0, y0, pw, ph = 60, 70, 700, 290` | The plot area is 700 px wide and 290 px high. Its left edge is at 60 px and its top edge at 70 px. |
| 230 | `    pos = {n: x0 + 20 + i * (pw - 40) / (len(ns) - 1) for i, n in enumerate(ns)}` | `pos`: the x position of each count. The counts stand at equal distances in the order of the list, from 20 px inside the left edge to 20 px inside the right edge. So the distance between two counts says nothing about their difference. The formula needs at least two counts. |
| 231 | `    top = 700` | `top`: 700, the highest value of the y axis in GB/s. |
| 232 | `    sy = Scale(0, top, y0 + ph, y0)` | `sy`: the y scale, linear from 0 at the bottom to 700 GB/s at the top. |
| 233 | `    out = [frame(w, h, 'Total read rate at 64+56 threads against injected NOPs',` | Opens the picture with its title, `Total read rate at 64+56 threads against injected NOPs`. The call goes on in line 234. |
| 234 | `                 'ASCT loop on CRB, per-mesh sums, and the vendor runs on two Arm reference machines.')]` | Continues line 233: the description for screen readers. It names the ASCT loop on CRB, the sums per mesh and the vendor runs on two Arm reference machines. |
| 235 | `    out.append(legend([('CRB total', ASCT, 'line'), ('CRB mesh 0 (64 threads)', INK2, 'line'), ('CRB mesh 1 (56 threads)', MUTED, 'hollow'),` | Draws the legend: the total of CRB is a green line, the sum of mesh 0 (64 threads) a dark grey line and the sum of mesh 1 (56 threads) a grey line with hollow markers. The call goes on in line 236. |
| 236 | `                       ('Arm reference machines, vendor runs', CONTEXT, 'thin')], x0, 22))` | Continues line 235: the vendor runs on the Arm reference machines are thin grey lines. |
| 237 | `    for t in range(0, top + 1, 100):` | Starts a loop over the y ticks, from 0 to 700 in steps of 100. |
| 238 | `        out.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x0 + pw}" y2="{sy(t):.1f}" stroke="{GRID}" stroke-width="1"/>')` | Draws a horizontal grid line at the tick. |
| 239 | `        out.append(text(x0 - 6, sy(t) + 4, str(t), 11, MUTED, 'end'))` | Writes the tick value left of the plot. |
| 240 | `    out.append(text(x0 - 40, y0 - 14, 'GB/s', 11, MUTED))` | Writes the unit `GB/s` above the y axis. |
| 241 | `    out.append(f'<line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')` | Draws the x axis along the bottom edge of the plot. |
| 242 | `    for n in ns:` | Starts a loop over the counts of injected NOPs. |
| 243 | `        out.append(text(pos[n], y0 + ph + 16, str(n), 11, MUTED, 'middle'))` | Writes each count below the axis at its position. |
| 244 | `    out.append(text(x0 + pw / 2, y0 + ph + 34, 'injected NOPs per line (ASCT option --bw-fine-delay); positions are evenly spaced, not to scale', 11, MUTED, 'middle'))` | Writes the title of the x axis. It says that the values are injected NOPs per line, set by the ASCT option `--bw-fine-delay`, and that the positions are evenly spaced and not to scale. |
| 245 | `    # reference bands of the 2026-11-15 loops` | Comment: the reference bands of the loops of 2026-11-15 follow. |
| 246 | `    L = {r[0]: r for r in B['chip']['loops']}` | `L`: the rows of the list `loops` of `baseline.json` by the name of the loop. |
| 247 | `    for name, color, labeltxt in (('old read', OLD, 'old read'), ('new read (asmread)', NEW, 'new read')):` | Starts a loop over the old read loop (blue) and the new read loop (orange). |
| 248 | `        r = L[name]` | `r`: the row of the loop. |
| 249 | `        ya, yb = sy(r[4]), sy(r[3])` | `ya`, `yb`: the heights of the largest and of the smallest total of the loop on the y axis. |
| 250 | `        out.append(f'<rect x="{x0}" y="{ya:.1f}" width="{pw}" height="{max(2, yb - ya):.1f}" fill="{color}" opacity="0.28"/>')` | Draws a band in the color of the loop over the full width of the plot. It reaches from the smallest to the largest total of 2026-11-15 and is at least 2 px high. It is partly transparent. |
| 251 | `        out.append(marker(x0 + pw + 12, (ya + yb) / 2, color, r=3))` | Draws a small marker right of the plot at the height of the band. |
| 252 | `        out.append(text(x0 + pw + 22, (ya + yb) / 2 + 4, f'{labeltxt} {r[3]:.0f} to {r[4]:.0f}', 11.5, INK))` | Writes the name of the loop and its smallest and largest total without decimals beside that marker. |
| 253 | `    hits = []` | `hits`: the hit areas. |
| 254 | `    for name, v in B['vendor'].items():` | Starts a loop over the two vendor runs. |
| 255 | `        pts = [(pos[n], sy(bw)) for n, _, bw in sorted(v['nops']) if n in pos]` | `pts`: the points of the vendor run for the counts that CRB also has. x is the position of the count and y the bandwidth in GB/s from the list `nops` of the vendor run. |
| 256 | `        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(pts))` | `d`: the path of the line through these points. |
| 257 | `        out.append(f'<path d="{d}" fill="none" stroke="{CONTEXT}" stroke-width="1.2"/>')` | Draws it as a thin grey line without markers. |
| 258 | `        for n, _, bw in v['nops']:` | Starts a loop over the rows of the vendor run. |
| 259 | `            if n in pos:` | For a count that CRB also has: |
| 260 | `                hits.append(hit_circle(pos[n], sy(bw), f'vendor run {name}, {n} NOPs: {bw} GB/s ({v["cpus"]} CPUs, {v["numa"]} NUMA nodes, firmware {v["bios"]})', r=7))` | adds a tooltip at the point: the name of the vendor run, the count, the bandwidth in GB/s, the number of CPUs, the number of NUMA nodes and the firmware. |
| 261 | `        last = max((n for n, _, _ in v['nops'] if n in pos), default=None)` | `last`: the largest count of the vendor run that the chart shows. No later line uses this value. |
| 262 | `    for key, color, kind, nm in (('mesh0', INK2, 'line', 'mesh 0 sum'), ('mesh1', MUTED, 'hollow', 'mesh 1 sum'), ('median', ASCT, 'line', 'total')):` | Starts a loop over three lines of CRB: the sum of mesh 0 (dark grey), the sum of mesh 1 (grey, hollow markers) and the total (green). The keys `mesh0`, `mesh1` and `median` name the fields of a cell in `facts.json`. |
| 263 | `        pts = [(pos[n], sy(ch['nops'][str(n)][key]), n) for n in ns]` | `pts`: one point per count. x is the position of the count. y is the field of the cell: the median over the processes of the sum of the thread rates of the mesh, or the median total that ASCT printed. |
| 264 | `        d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y, _) in enumerate(pts))` | `d`: the path of the line through these points. |
| 265 | `        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')` | Draws the line with a width of 2 px. |
| 266 | `        for x, y, n in pts:` | Starts a loop over the points. |
| 267 | `            v = ch['nops'][str(n)]` | `v`: the cell of the count. |
| 268 | `            if key == 'median' and abs(sy(v['lo']) - sy(v['hi'])) > 3:` | Only for the total, and only when its range is larger than 3 px: |
| 269 | `                out.append(f'<line x1="{x:.1f}" y1="{sy(v["lo"]):.1f}" x2="{x:.1f}" y2="{sy(v["hi"]):.1f}" stroke="{color}" stroke-width="1.2" opacity="0.6"/>')` | draws a thin vertical line from the smallest to the largest total of the processes. |
| 270 | `            out.append(marker(x, y, color, hollow=kind == 'hollow', r=3.2))` | Draws the marker of the point. It is hollow for mesh 1. |
| 271 | `            hits.append(hit_circle(x, y, f'CRB {nm}, {n} NOPs: {v[key]:.1f} GB/s' + (f' (range {v["lo"]:.1f} to {v["hi"]:.1f}, {v["n"]} processes)' if key == 'median' else ''), r=8))` | Adds the tooltip of the point: the name of the line, the count and the value in GB/s with 1 decimal. For the total it also gives the range and the number of processes. |
| 272 | `    # direct labels: N = 0 and the best N` | Comment: two direct labels follow, one at 0 injected NOPs and one at the best count. |
| 273 | `    v0 = ch['nops'][str(ns[0])]` | `v0`: the cell of the first count of the list, which is 0 injected NOPs when that cell exists. |
| 274 | `    out.append(text(pos[ns[0]] + 8, sy(v0['median']) - 8, f'{v0["median"]:.1f}', 12, INK, weight=600))` | Writes its median total with 1 decimal in bold, above and right of its point. |
| 275 | `    bn = ch['bestN']` | `bn`: the count with the highest median total, from `bestN`. |
| 276 | `    if bn is not None and bn != ns[0]:` | When it exists and is not the first count: |
| 277 | `        vb = ch['nops'][str(bn)]` | `vb`: its cell. |
| 278 | `        out.append(text(pos[bn], sy(vb['median']) - 10, f'{vb["median"]:.1f}', 12, INK, 'middle', weight=600))` | writes its median total with 1 decimal in bold, centered above its point. |
| 279 | `    return ''.join(out) + ''.join(hits) + '</svg>'` | Returns the drawing, then the hit areas, and closes the picture. |

### `fig_threads`: figure 10, the rate of one thread by mesh (lines 282 to 298)

| Line | Source | Explanation |
|---:|---|---|
| 282 | `def fig_threads(F):` | Starts the function `fig_threads`. The report shows the result as figure 10. |
| 283 | `    """Per-thread rate by mesh, 0 NOPs against the best N."""` | Description of the function: the rate per thread by mesh, with 0 injected NOPs against the best count. |
| 284 | `    ch = F['chip']` | `ch`: the results for the whole chip from `facts.json`. |
| 285 | `    bn = ch['bestN']` | `bn`: the count of injected NOPs with the highest median total. |
| 286 | `    if bn in (None, 0) or str(bn) not in ch['nops']:` | When there is no such count, when it is 0, or when it has no cell, |
| 287 | `        return ''` | the function returns an empty text. The report then shows no figure here. |
| 288 | `    a, b = ch['nops']['0'], ch['nops'][str(bn)]` | `a`, `b`: the cells at 64+56 with 0 injected NOPs and with the best count. |
| 289 | `    rows = []` | `rows`: the rows of the chart. It starts empty. |
| 290 | `    for m, nm, k in (('thr0', 'mesh 0, CPUs 0 to 63', 64), ('thr1', 'mesh 1, CPUs 64 to 119', 56)):` | Starts a loop over the two meshes: `thr0` for mesh 0 with the CPUs 0 to 63 and 64 threads, and `thr1` for mesh 1 with the CPUs 64 to 119 and 56 threads. |
| 291 | `        rows.append({'label': nm, 'sub': f'median of {k} threads', 'a': a[m][1], 'b': b[m][1], 'ca': ASCT, 'cb': ASCT,` | Adds one green row. Value `a` is the middle entry of the thread range with 0 injected NOPs, and value `b` the same with the best count. By `facts.py` this entry is the median over the processes of the median thread rate of the mesh. The second label line says `median of 64 threads` or `median of 56 threads`. The dictionary goes on in lines 292 to 294. |
| 292 | `                     'tipa': f'{nm}, 0 NOPs: median thread {a[m][1]:.2f} GB/s (threads from {a[m][0]:.2f} to {a[m][2]:.2f})',` | Continues line 291: the tooltip of the dot for 0 injected NOPs. It gives the median thread rate and the slowest and the fastest thread, in GB/s with 2 decimals. |
| 293 | `                     'tipb': f'{nm}, {bn} NOPs: median thread {b[m][1]:.2f} GB/s (threads from {b[m][0]:.2f} to {b[m][2]:.2f})',` | Continues line 291: the tooltip of the dot for the best count. |
| 294 | `                     'delta': f'x {b[m][1] / a[m][1]:.2f}'})` | Continues line 291: `delta`, the factor between the two median thread rates, written as `x` and a number with 2 decimals. |
| 295 | `    return dumbbell(940, rows, 250, 800, [0, 1, 2, 3, 4, 5, 6], 'read rate of one thread, GB/s', 'Rate of one thread by mesh',` | Draws the chart with `dumbbell`. The value axis is linear, from 0 to 6 GB/s with a tick every 1 GB/s. Its unit text is `read rate of one thread, GB/s`. The call goes on in line 296. |
| 296 | `                    'Hollow dot: 0 injected NOPs. Filled dot: the N with the highest total.', ('0 injected NOPs', f'{bn} injected NOPs'), rowh=42, top=52, nd=2)` | Continues line 295: the description says that the hollow dot is 0 injected NOPs and the filled dot the count with the highest total. The key names follow, and the value labels have 2 decimals. |

### `fig_loops`: figure 2, what each read loop loads from one line (lines 299 to 319)

| Line | Source | Explanation |
|---:|---|---|
| 299 | `def fig_loops():` | Starts the function `fig_loops`. It takes no data. The report shows the result as figure 2. |
| 300 | `    """What each loop loads from one 64-byte line."""` | Description of the function: what each loop loads from one 64-byte line. |
| 301 | `    w, h = 940, 250` | `w`, `h`: the picture is 940 units wide and 250 high. |
| 302 | `    out = [frame(w, h, 'What each read loop loads from one 64-byte line', 'Old read and new read load all 64 bytes, the ASCT loop loads 8 bytes.')]` | Opens the picture with its title, `What each read loop loads from one 64-byte line`. The description says that the old and the new read loop load all 64 bytes and that the ASCT loop loads 8 bytes. |
| 303 | `    rows = [('old read', 'loads all 64 bytes (2 ldp q), then 4 vector adds on them', OLD, 8, 'counts 64 bytes'),` | `rows`: three fixed rows. Each holds a name, a description, a color, the number of filled cells and a text. The first is the old read loop: it loads all 64 bytes with 2 `ldp q` instructions and then runs 4 vector adds on them. 8 cells are filled. |
| 304 | `            ('new read', 'loads all 64 bytes (2 ldp q), no other work', NEW, 8, 'counts 64 bytes'),` | The second row, the new read loop: it loads all 64 bytes with 2 `ldp q` instructions and does no other work. 8 cells are filled. |
| 305 | `            ('ASCT read', 'loads the first 8 bytes (1 ldr x), no other work', ASCT, 1, 'counts 64 bytes')]` | The third row, the ASCT loop: it loads the first 8 bytes with 1 `ldr x` instruction and does no other work. 1 cell is filled. The text of all three rows is `counts 64 bytes`. |
| 306 | `    x0, cw = 330, 52` | `x0`: the left edge of the cells, at 330 px. `cw`: the width of one cell, 52 px. |
| 307 | `    out.append(text(x0, 24, 'one 64-byte cache line, drawn as eight 8-byte cells', 11.5, MUTED))` | Writes a heading above the cells: one 64-byte cache line is drawn as eight cells of 8 bytes. |
| 308 | `    for i, (nm, what, color, k, cnt) in enumerate(rows):` | Starts a loop over the three rows. |
| 309 | `        y = 44 + i * 62` | `y`: the top edge of the cells of this row. The rows are 62 px apart. |
| 310 | `        out.append(text(12, y + 16, nm, 13, INK, weight=600))` | Writes the name of the loop in bold at the left. |
| 311 | `        out.append(text(12, y + 33, what, 11, MUTED))` | Writes the description of the loop below the name, in grey. |
| 312 | `        for j in range(8):` | Starts a loop over the 8 cells of the line. |
| 313 | `            fill = color if j < k else SURFACE` | `fill`: the color of the loop for the first `k` cells and the background color for the others. |
| 314 | `            out.append(f'<rect x="{x0 + j * (cw + 2)}" y="{y}" width="{cw}" height="26" rx="3" fill="{fill}" stroke="{AXIS}" stroke-width="1"/>')` | Draws the cell as a rectangle with rounded corners and a grey outline. So a filled cell stands for 8 bytes that the loop loads. |
| 315 | `        out.append(text(x0 + 8 * (cw + 2) + 12, y + 17, cnt, 11.5, INK2))` | Writes the text `counts 64 bytes` right of the cells. |
| 316 | `    out.append(text(x0, 44 + 3 * 62 + 4, 'filled cell = bytes that the loop loads', 11, MUTED))` | Writes a note below the rows: a filled cell stands for bytes that the loop loads. |
| 317 | `    return ''.join(out) + '</svg>'` | Returns the picture and closes it. |

### `fig_path`: figure 1, how ASCT was driven (lines 320 to 348)

| Line | Source | Explanation |
|---:|---|---|
| 320 | `def fig_path():` | Starts the function `fig_path`. It takes no data. The report shows the result as figure 1. |
| 321 | `    """How ASCT was driven."""` | Description of the function: how ASCT was driven. |
| 322 | `    w, h = 940, 210` | `w`, `h`: the picture is 940 units wide and 210 high. |
| 323 | `    out = [frame(w, h, 'How ASCT was driven in this work', 'The front end asct run was not used; its benchmark binary was called with the same command line.')]` | Opens the picture with its title, `How ASCT was driven in this work`. The description says that the front end `asct run` was not used and that its benchmark binary was called with the same command line. |
| 325 | `    def box(x, y, bw, bh, t1, t2=None, used=True):` | Starts the helper function `box`. It draws a box with rounded corners and one or two lines of text. `used` says whether the box belongs to the path that ran. |
| 326 | `        s = f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" fill="{SURFACE}" stroke="{INK2 if used else AXIS}" stroke-width="{1.5 if used else 1}"/>'` | `s`: the rectangle of the box. Its outline is dark grey and 1.5 px wide for a used box, and light grey and 1 px wide for a box that was not used. |
| 327 | `        s += text(x + bw / 2, y + (20 if t2 else bh / 2 + 4), t1, 12, INK if used else MUTED, 'middle', weight=600)` | Adds the first text line in bold, centered in the box. It is grey for a box that was not used. |
| 328 | `        if t2:` | When a second text line is given: |
| 329 | `            s += text(x + bw / 2, y + 37, t2, 10.5, MUTED, 'middle')` | adds it below the first one, smaller and in grey. |
| 330 | `        return s` | Returns the box. |
| 332 | `    def arrow(xa, ya, xb, yb, used=True):` | Starts the helper function `arrow`. It draws an arrow from the point `xa`, `ya` to the point `xb`, `yb`. |
| 333 | `        c = INK2 if used else AXIS` | `c`: the color, dark grey for a used path and light grey otherwise. |
| 334 | `        return (f'<line x1="{xa}" y1="{ya}" x2="{xb - 6}" y2="{yb}" stroke="{c}" stroke-width="1.5"/>'` | Returns the shaft, a line that ends 6 px before the target. The returned text goes on in line 335. |
| 335 | `                f'<path d="M{xb},{yb} l-8,-4 v8 z" fill="{c}"/>')` | Continues line 334: the head, a small filled triangle with its tip at the target. |
| 336 | `    out.append(box(20, 24, 250, 50, 'asct run (front end)', 'fixed core CPU 127, needs huge pages', used=False))` | Draws the box at the top left for the front end `asct run`, with the second line `fixed core CPU 127, needs huge pages`. It is marked as not used. |
| 337 | `    out.append(box(20, 122, 250, 50, 'our run scripts', 'CPUs 2 and 41, CPUs 0 to 119, our sizes'))` | Draws the box at the bottom left for our run scripts, with the second line `CPUs 2 and 41, CPUs 0 to 119, our sizes`. |
| 338 | `    out.append(box(380, 72, 250, 54, 'ASCT benchmark binary', 'loaded-latency-asct-sve.bin, same options'))` | Draws the box in the middle for the ASCT benchmark binary, with the second line `loaded-latency-asct-sve.bin, same options`. |
| 339 | `    out.append(box(700, 24, 220, 50, 'ASCT read loop', 'my_read_no_nops_rep_64b, my_read'))` | Draws the box at the top right for the ASCT read loop, with the names of its two functions, `my_read_no_nops_rep_64b` and `my_read`. |
| 340 | `    out.append(box(700, 122, 220, 50, 'ASCT counter capture', 'dietperf, probe build of the binary'))` | Draws the box at the bottom right for the counter capture of ASCT, with the second line `dietperf, probe build of the binary`. |
| 341 | `    out.append(arrow(270, 49, 380, 90, used=False))` | Draws a light grey arrow from the front end to the binary. It is marked as not used. |
| 342 | `    out.append(arrow(270, 147, 380, 108))` | Draws a dark arrow from our run scripts to the binary. |
| 343 | `    out.append(arrow(630, 90, 700, 49))` | Draws a dark arrow from the binary to the read loop. |
| 344 | `    out.append(arrow(630, 108, 700, 147))` | Draws a dark arrow from the binary to the counter capture. |
| 345 | `    out.append(text(300, 52, 'not used', 11, MUTED))` | Writes `not used` beside the light grey arrow. |
| 346 | `    out.append(text(300, 152, 'used', 11, INK2))` | Writes `used` beside the arrow from our run scripts. |
| 347 | `    out.append(text(20, 200, 'Grey box and arrow: the path that this work could not use. Dark boxes and arrows: the path that ran.', 11, MUTED))` | Writes a note at the bottom: the grey box and arrow are the path that this work could not use, and the dark boxes and arrows are the path that ran. |
| 348 | `    return ''.join(out) + '</svg>'` | Returns the picture and closes it. |
