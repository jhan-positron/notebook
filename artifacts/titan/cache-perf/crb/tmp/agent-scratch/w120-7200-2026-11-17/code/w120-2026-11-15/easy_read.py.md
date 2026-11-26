# `easy_read.py` explained, line by line

- Source file: `w120-2026-11-15/easy_read.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 473 lines, 33618 bytes).
- sha256 of the source when this page was built: `a617b0389fe06a75b45f4a017674bc879d7ea5917c4874f1afca90de47311df2`.

## Short version: purpose

`easy_read.py` builds the easy-read page of the report on the whole-chip read drop: one HTML file with two pictures, a word list, seven step boxes and 15 references. Every number of the page stands in this script as fixed text, copied from the facts sheet `FINDINGS.md`. The script reads no result file and computes no result.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Facts sheet of the investigation**: the file `FINDINGS.md` in the same folder as this script. It holds the numbers of the report of 2026-11-15 with the files that they come from.
- **Loop**: the word of the built page for a kernel. The script uses the kernel names of the runners, for example `oldread` and `asmread`, in the data of figure 2.
- **Total**: the sum of the rates of all threads, in GB/s.
- **64 plus 56**: 64 threads on mesh 0 and 56 threads on mesh 1, written `64+56` in the page.
- **Window**: the instructions that a core holds between fetch and retirement. This is the definition of the word list in line 180.
- **Window depth**: the number of 64 B lines that the loads inside one full window touch. This is the definition of the word list in line 181.
- **State**: one of the three words `slow`, `between` and `fast` that the list `P` gives to each loop.
- **SVG**: a text format for pictures that are made of lines, shapes and text. A browser draws it inside an HTML page.
- **CSS**: the style rules of an HTML page: sizes, colours, spacing.

## Main flow

1. Set the output path and the six colours (lines 6 to 10).
2. Hold the six data rows of figure 1 and define `fig1`, which draws one bar per row, from the lowest to the highest total (lines 14 to 47).
3. Hold the 29 data rows of figure 2, count the loops of each state, and define `fig2`, which draws one point per loop: the window depth on a logarithmic axis and the total on a linear axis (lines 52 to 141).
4. Hold the texts of the page: the 15 references, the function `ref` for a citation, the 23 word entries, the seven overview boxes, the seven steps (each built by the function `step`) and the style rules (lines 145 to 350).
5. Define `build`. It joins all parts into one HTML text, writes it to the file `OUT` and prints the path and the length (lines 353 to 470).
6. Call `build` (line 473).

## Behavior a reader must know

- The script has no input. Every rate, window depth and count of the page is typed into this file. So a number of the page is only as right as its copy from the facts sheet.
- One number can stand at several places. The values of the old read loop, for example, stand in the list `P` (line 73), in a label of figure 2 (lines 123 to 125), in the step texts and in the table (line 435). A change must be made at each place by hand.
- The output path is fixed (line 6). Each run replaces the file `whole-chip-read-drop-easy-read.html` in the folder `new-test-kernel` on the agent server.
- `build` is called at the top level (line 473). So the page is also written when another script imports this file.
- In figure 1 a bar spans the lowest and the highest value of a row, and the rate axis starts at 0. In figure 2 a point stands at the middle of the lowest and the highest total of a loop, not at a mean or a median, and the rate axis starts at 0.
- The paths in the reference texts are paths of the agent server (lines 7 to 8), not paths of the code repo.
- The check of line 83 stops the script when the list of figure 2 does not hold 29 rows.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/easy_read.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (473 lines, 33618 bytes, sha256 `a617b0389fe06a75b45f4a017674bc879d7ea5917c4874f1afca90de47311df2`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header, modules, paths and colours (lines 1 to 11)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""Builds the easy-read page of the whole-chip read drop report.` | Starts the documentation text of the script: it builds the easy-read page of the report on the whole-chip read drop. |
| 3 | `All numbers are copied from FINDINGS.md (the facts sheet) in this folder."""` | Ends the documentation text: all numbers are copied from `FINDINGS.md`, the facts sheet in this folder. So the numbers stand in this file as fixed text. The script reads no result file. |
| 4 | `import math, html` | Loads two modules of the standard library: `math` for the logarithm and the square root in figure 2, `html` to escape text that goes into the page. |
| 6 | `OUT = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop-easy-read.html"` | `OUT`: the path of the page that the script writes, an HTML file in the folder `new-test-kernel` on the agent server. |
| 7 | `R = "/home/jhan/workspace/titan/cache-perf/crb/results"` | `R`: the path of the folder with the result folders on the agent server. It is used only inside the reference texts of lines 145 to 161. |
| 8 | `W = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15"` | `W`: the path of the working folder of the investigation on the agent server. It is used only inside the reference texts. |
| 10 | `BLUE, ORANGE, GREY, INK, MUTED, GRID = "#1f6fc9", "#c2500a", "#6b6a66", "#0b0b0b", "#52514e", "#e4e3df"` | Six colour values as hexadecimal text: `BLUE` and `ORANGE` for the two main colours of the figures, `GREY`, `INK` (the text colour, nearly black), `MUTED` (a grey for axis text) and `GRID` (a light grey for grid lines). |

### Figure 1: the data (lines 12 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 12 | `# ---------------------------------------------------------------- figure 1` | Comment: a divider line with the title `figure 1`. |
| 13 | `# Original run, 120 threads, benchmark bandwidth.c, whole-pass stop, 0.5 s, n = 6 per loop.` | Comment: figure 1 shows the original run: 120 threads, the benchmark `bandwidth.c`, the whole-pass stop, intervals of 0.5 s, and 6 intervals per loop. |
| 14 | `F1 = [  # label, lo, hi, median or None, colour` | Starts the list `F1`, the six rows of figure 1. By the comment each row holds: the label, the lowest value, the highest value, the median or `None`, and the colour. The values are total rates in GB/s. |
| 15 | `    ("Read, old loop", 464.4, 466.7, None, GREY),` | Row 1: the old read loop. It holds its lowest and its highest total, no median, and the colour grey. |
| 16 | `    ("Read, new loop", 279.7, 304.1, None, BLUE),` | Row 2: the new read loop, with its lowest and its highest total, no median, and the colour blue. |
| 17 | `    ("Write, old loop", 140.9, 186.9, 144.6, GREY),` | Row 3: the old write loop, with its lowest total, its highest total and its median, in grey. |
| 18 | `    ("Write, new loop", 123.5, 147.8, 131.9, BLUE),` | Row 4: the new write loop, with its lowest total, its highest total and its median, in blue. |
| 19 | `    ("Copy, old loop", 155.0, 158.6, None, GREY),` | Row 5: the old copy loop, with its lowest and its highest total, no median, in grey. |
| 20 | `    ("Copy, new loop", 153.9, 162.4, None, BLUE),` | Row 6: the new copy loop, with its lowest and its highest total, no median, in blue. |
| 21 | `]` | Ends the list `F1`. |

### Function `fig1`: the bar chart of the original run (lines 24 to 49)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `def fig1():` | Starts the function `fig1`. It returns the text of figure 1 as an SVG picture: one horizontal bar per row of `F1`, from the lowest to the highest value. |
| 25 | `    w, h = 920, 318` | `w`, `h`: the width and the height of the picture, 920 by 318 units. |
| 26 | `    x0, x1 = 150, 700` | `x0`, `x1`: the horizontal positions of the two ends of the value axis. |
| 27 | `    sx = lambda v: x0 + (x1 - x0) * v / 500.0` | `sx`: a small function that turns a rate in GB/s into a horizontal position. The scale is linear: 0 GB/s lies at `x0` and 500 GB/s at `x1`. So the axis starts at 0. |
| 28 | `    o = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Range of the 120-thread total for the old and the new loop: read, write and copy">']` | `o`: the list of the text lines of the picture. Its first entry is the opening `<svg>` tag with the size, the role `img` and a label for screen readers that says what the figure shows. |
| 29 | `    for t in range(0, 501, 100):` | Starts the loop over the axis values 0, 100, 200, 300, 400 and 500 GB/s. |
| 30 | `        o.append(f'<line x1="{sx(t):.1f}" y1="28" x2="{sx(t):.1f}" y2="268" stroke="{GRID}"/>')` | Adds a vertical grid line at this value, in the colour `GRID`. |
| 31 | `        o.append(f'<text x="{sx(t):.1f}" y="286" font-size="12.5" fill="{MUTED}" text-anchor="middle">{t}</text>')` | Adds the number of this value under the grid line, centred, in the colour `MUTED`. |
| 32 | `    o.append(f'<text x="{(x0+x1)/2:.1f}" y="308" font-size="13" fill="{MUTED}" text-anchor="middle">Total of 120 threads, GB/s (the bar spans the lowest and the highest of 6 intervals)</text>')` | Adds the title of the axis under the numbers: the total of 120 threads in GB/s, and a note that a bar spans the lowest and the highest of 6 intervals. |
| 33 | `    notes = ["Looks like a large drop", "Looks like a drop", "No drop"]` | `notes`: three short texts, one for each pair of rows (read, write, copy). |
| 34 | `    for i, (lab, lo, hi, med, col) in enumerate(F1):` | Starts the loop over the six rows of `F1`. `i` is the row number from 0, and the five fields go to `lab`, `lo`, `hi`, `med` and `col`. |
| 35 | `        y = 48 + i * 36 + (i // 2) * 14` | `y`: the vertical position of the row. Each row lies 36 units below the row before it. `i // 2` is the number of the pair, and each pair adds 14 units more, so a gap parts the three pairs. |
| 36 | `        o.append(f'<text x="{x0-10}" y="{y+4.5}" font-size="13.5" fill="{INK}" text-anchor="end">{lab}</text>')` | Adds the label of the row at the left of the axis. `text-anchor="end"` lets the text end at that position. |
| 37 | `        o.append(f'<line x1="{sx(0):.1f}" y1="{y}" x2="{sx(lo):.1f}" y2="{y}" stroke="{col}" stroke-width="2" opacity="0.35"/>')` | Adds a thin, pale line from 0 GB/s to the lowest value, in the colour of the row. It joins the start of the axis to the bar. |
| 38 | `        o.append(f'<rect x="{sx(lo):.1f}" y="{y-8}" width="{max(sx(hi)-sx(lo),4):.1f}" height="16" rx="3" fill="{col}"/>')` | Adds the bar: a rectangle with round corners from the lowest to the highest value, 16 units high, in the colour of the row. `max(...,4)` makes it at least 4 units wide, so a narrow range stays visible. |
| 39 | `        txt = f"{lo} to {hi}"` | `txt`: the value text of the row: the lowest value, the word `to` and the highest value. |
| 40 | `        if med is not None:` | The next two lines run only when the row has a median. |
| 41 | `            o.append(f'<line x1="{sx(med):.1f}" y1="{y-11}" x2="{sx(med):.1f}" y2="{y+11}" stroke="{INK}" stroke-width="2"/>')` | Adds a short black vertical mark at the median. |
| 42 | `            txt += f" (median {med})"` | Adds the median in parentheses to the value text. |
| 43 | `        o.append(f'<text x="{sx(hi)+8:.1f}" y="{y+4.5}" font-size="13" fill="{INK}">{txt}</text>')` | Adds the value text at the right of the bar. |
| 44 | `        if i % 2 == 1:` | The next line runs for the second row of each pair (`i` is odd). |
| 45 | `            o.append(f'<text x="{w-12}" y="{y-13.5}" font-size="13.5" font-weight="600" fill="{INK}" text-anchor="end">{notes[i//2]}</text>')` | Adds the note of the pair in bold type at the right edge of the picture, a little above this row. |
| 46 | `    o.append("</svg>")` | Adds the closing `</svg>` tag. |
| 47 | `    return "\n".join(o)` | Returns the picture: all lines of `o`, joined with line breaks. |

### Figure 2: the data and the counts of the three states (lines 50 to 89)

| Line | Source | Explanation |
|---:|---|---|
| 50 | `# ---------------------------------------------------------------- figure 2` | Comment: a divider line with the title `figure 2`. |
| 51 | `# name, window lo, window hi (lines), total min, total max (GB/s), state` | Comment: the fields of a row of `P`: the name of the loop, the low end and the high end of its window depth in lines, the lowest and the highest total in GB/s, and the state. |
| 52 | `P = [` | Starts the list `P`, the 29 points of figure 2. Each row is one read kernel at 64 plus 56 threads. The state is one of `slow`, `between` and `fast`. |
| 53 | `    ("read_1pl", 156, 164, 230.2, 235.0, "slow"),` | Row for `read_1pl` (one load per line): its range of the window depth, its range of the total, state `slow`. |
| 54 | `    ("read_sparse", 38, 42, 294.6, 301.5, "slow"),` | Row for `read_sparse`, state `slow`. |
| 55 | `    ("asmread", 36, 40, 288.5, 309.8, "slow"),` | Row for `asmread`, the load-only loop, state `slow`. |
| 56 | `    ("read_pf2048", 36, 40, 290.5, 306.8, "slow"),` | Row for `read_pf2048`, the load-only loop with software prefetch, state `slow`. |
| 57 | `    ("read_nop32", 36, 40, 284.8, 302.7, "slow"),` | Row for `read_nop32`, the load-only loop with 32 `nop`, state `slow`. |
| 58 | `    ("read_nop48", 32, 36, 305.4, 307.2, "slow"),` | Row for `read_nop48`, state `slow`. |
| 59 | `    ("read_dadd2", 32, 36, 290.1, 296.4, "slow"),` | Row for `read_dadd2`, the load-only loop with 2 vector adds, state `slow`. |
| 60 | `    ("read_sp24", 32, 34, 280.9, 283.2, "slow"),` | Row for `read_sp24`, state `slow`. |
| 61 | `    ("read_nop56", 28, 32, 308.6, 309.1, "slow"),` | Row for `read_nop56`, state `slow`. |
| 62 | `    ("read_dadd4", 28, 32, 280.1, 283.2, "slow"),` | Row for `read_dadd4`, state `slow`. |
| 63 | `    ("read_nop64", 28, 32, 325.5, 333.9, "between"),` | Row for `read_nop64`, state `between`. |
| 64 | `    ("read_sp32", 26, 30, 366.3, 366.6, "between"),` | Row for `read_sp32`, state `between`. |
| 65 | `    ("read_nop72", 24, 28, 459.0, 459.3, "fast"),` | Row for `read_nop72`, state `fast`. |
| 66 | `    ("read_dadd8", 24, 28, 462.4, 462.6, "fast"),` | Row for `read_dadd8`, state `fast`. |
| 67 | `    ("read_1pl_nop96", 24, 28, 460.8, 460.9, "fast"),` | Row for `read_1pl_nop96`, state `fast`. |
| 68 | `    ("read_nop80", 24, 28, 459.7, 459.8, "fast"),` | Row for `read_nop80`, state `fast`. |
| 69 | `    ("read_sp40", 22, 24, 466.8, 466.9, "fast"),` | Row for `read_sp40`, state `fast`. |
| 70 | `    ("read_nop88", 20, 24, 462.8, 462.9, "fast"),` | Row for `read_nop88`, state `fast`. |
| 71 | `    ("read_nop96", 20, 24, 465.5, 470.6, "fast"),` | Row for `read_nop96`, state `fast`. |
| 72 | `    ("read_sp48", 20, 22, 470.0, 470.1, "fast"),` | Row for `read_sp48`, state `fast`. |
| 73 | `    ("oldread", 18, 22, 465.5, 470.1, "fast"),` | Row for `oldread`, the old read loop, state `fast`. |
| 74 | `    ("read_sp56", 18, 20, 473.6, 473.7, "fast"),` | Row for `read_sp56`, state `fast`. |
| 75 | `    ("read_dadd16", 16, 20, 466.7, 469.8, "fast"),` | Row for `read_dadd16`, state `fast`. |
| 76 | `    ("read_iadd16", 16, 20, 469.2, 469.7, "fast"),` | Row for `read_iadd16`, state `fast`. |
| 77 | `    ("read_nop112", 16, 20, 471.1, 471.2, "fast"),` | Row for `read_nop112`, state `fast`. |
| 78 | `    ("read_nop128", 16, 20, 473.8, 476.4, "fast"),` | Row for `read_nop128`, state `fast`. |
| 79 | `    ("read_nop160", 12, 16, 477.9, 478.2, "fast"),` | Row for `read_nop160`, state `fast`. |
| 80 | `    ("read_nop192", 12, 16, 479.6, 479.8, "fast"),` | Row for `read_nop192`, state `fast`. |
| 81 | `    ("read_nop256", 8, 12, 543.9, 549.0, "fast"),` | Row for `read_nop256`, state `fast`. It is the row with the smallest window depth and the highest total of the list. |
| 82 | `]` | Ends the list `P`. |
| 83 | `assert len(P) == 29` | A check: the script stops with an error when `P` does not hold exactly 29 rows. |
| 84 | `NSLOW = sum(1 for p in P if p[5] == "slow")` | `NSLOW`: the number of rows with the state `slow`. For this list it is 10. |
| 85 | `NBETW = sum(1 for p in P if p[5] == "between")` | `NBETW`: the number of rows with the state `between`. For this list it is 2. |
| 86 | `NFAST = sum(1 for p in P if p[5] == "fast" and p[0] != "read_nop256")` | `NFAST`: the number of rows with the state `fast`, without `read_nop256`. For this list it is 16. The figure names `read_nop256` in a label of its own. |
| 87 | `COL = {"slow": ORANGE, "between": GREY, "fast": BLUE}` | `COL`: the colour of each state: orange for `slow`, grey for `between`, blue for `fast`. |

### Function `fig2`: total rate against window depth (lines 90 to 143)

| Line | Source | Explanation |
|---:|---|---|
| 90 | `def fig2():` | Starts the function `fig2`. It returns the text of figure 2 as an SVG picture: one point per row of `P`, with the window depth on the horizontal axis and the total rate on the vertical axis. |
| 91 | `    w, h = 920, 470` | `w`, `h`: the width and the height of the picture, 920 by 470 units. |
| 92 | `    x0, x1, yt, yb = 70, 896, 26, 400` | The plot area: `x0` and `x1` are its left and right edge, `yt` and `yb` its top and bottom edge. |
| 93 | `    lx = lambda v: x0 + (x1 - x0) * (math.log(v) - math.log(7)) / (math.log(200) - math.log(7))` | `lx`: a small function that turns a window depth in lines into a horizontal position. The scale is logarithmic: 7 lines lie at `x0` and 200 lines at `x1`. |
| 94 | `    sy = lambda v: yb - (yb - yt) * v / 600.0` | `sy`: a small function that turns a rate in GB/s into a vertical position. The scale is linear: 0 GB/s lies at the bottom edge and 600 GB/s at the top edge. So the axis starts at 0. |
| 95 | `    o = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Total read rate of 120 threads against the window depth of the loop, 29 loop variants">']` | `o`: the list of the text lines of the picture. Its first entry is the opening `<svg>` tag with the size, the role `img` and a label for screen readers. |
| 96 | `    # band where the total falls` | Comment: the next line draws the band in which the total falls. |
| 97 | `    o.append(f'<rect x="{lx(28):.1f}" y="{yt}" width="{lx(32)-lx(28):.1f}" height="{yb-yt}" fill="#f3e9c9"/>')` | Adds a pale yellow rectangle over the whole height of the plot, from 28 lines to 32 lines on the horizontal axis. |
| 98 | `    for t in range(0, 601, 100):` | Starts the loop over the values 0 to 600 GB/s in steps of 100. |
| 99 | `        o.append(f'<line x1="{x0}" y1="{sy(t):.1f}" x2="{x1}" y2="{sy(t):.1f}" stroke="{GRID}"/>')` | Adds a horizontal grid line at this value. |
| 100 | `        o.append(f'<text x="{x0-8}" y="{sy(t)+4:.1f}" font-size="12.5" fill="{MUTED}" text-anchor="end">{t}</text>')` | Adds the number of this value at the left of the plot, with the text ending at the axis. |
| 101 | `    for t in (8, 10, 12, 16, 20, 24, 28, 32, 40, 60, 80, 120, 160):` | Starts the loop over the 13 marks of the horizontal axis: 8, 10, 12, 16, 20, 24, 28, 32, 40, 60, 80, 120 and 160 lines. |
| 102 | `        o.append(f'<line x1="{lx(t):.1f}" y1="{yb}" x2="{lx(t):.1f}" y2="{yb+5}" stroke="{MUTED}"/>')` | Adds a short tick below the axis at this depth. |
| 103 | `        o.append(f'<text x="{lx(t):.1f}" y="{yb+19}" font-size="12.5" fill="{MUTED}" text-anchor="middle">{t}</text>')` | Adds the number of this depth under the tick. |
| 104 | `    o.append(f'<line x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}" stroke="{MUTED}"/>')` | Adds the line of the horizontal axis at the bottom edge. |
| 105 | `    o.append(f'<text x="{(x0+x1)/2:.1f}" y="{yb+42}" font-size="13" fill="{MUTED}" text-anchor="middle">Window depth of the loop, cache lines (measured range, one thread). The axis is logarithmic.</text>')` | Adds the title of the horizontal axis: the window depth of the loop in cache lines, as a measured range with one thread, and the note that the axis is logarithmic. |
| 106 | `    o.append(f'<text transform="translate(18,{(yt+yb)/2:.1f}) rotate(-90)" font-size="13" fill="{MUTED}" text-anchor="middle">Total of 120 threads, GB/s</text>')` | Adds the title of the vertical axis, turned by 90 degrees: the total of 120 threads in GB/s. |
| 107 | `    for name, lo, hi, a, b, st in P:` | Starts the loop over the rows of `P`. The six fields go to `name`, `lo`, `hi`, `a`, `b` and `st`. |
| 108 | `        y = sy((a + b) / 2)` | `y`: the vertical position of the point. It is the middle of the lowest total `a` and the highest total `b`. |
| 109 | `        c = COL[st]` | `c`: the colour of the state of this row. |
| 110 | `        o.append(f'<line x1="{lx(lo):.1f}" y1="{y:.1f}" x2="{lx(hi):.1f}" y2="{y:.1f}" stroke="{c}" stroke-width="2.2" opacity="0.55"/>')` | Adds a horizontal line from the low end to the high end of the window depth, at the height `y`. It shows the measured range of the depth. |
| 111 | `        key = name in ("oldread", "asmread")` | `key`: true for the two main loops, `oldread` and `asmread`. |
| 112 | `        o.append(f'<circle cx="{lx(math.sqrt(lo*hi)):.1f}" cy="{y:.1f}" r="{6.5 if key else 4.2}" fill="{c}" stroke="{INK if key else "#fcfcfb"}" stroke-width="{2 if key else 1}"/>')` | Adds the point: a circle at the geometric mean of the two ends of the depth range (the square root of their product), which is the middle of the range on a logarithmic axis. The two main loops get a larger circle with a dark edge. |
| 114 | `    def lab(x, y, lines, anchor="start", bold=True):` | Starts the inner function `lab`. It writes a label of one or more text lines at the position `x`, `y`. |
| 115 | `        for i, t in enumerate(lines):` | Starts the loop over the text lines of the label. |
| 116 | `            fw = ' font-weight="600"' if bold and i == 0 else ""` | `fw`: the text that makes a line bold. It is set for the first line when `bold` is true, and empty in every other case. |
| 117 | `            o.append(f'<text x="{x:.1f}" y="{y+i*17:.1f}" font-size="13.5" fill="{INK}" text-anchor="{anchor}"{fw}>{html.escape(t)}</text>')` | Adds the text line, 17 units below the line before it. `html.escape` replaces the characters that have a special meaning in HTML. |
| 119 | `    def lead(xa, ya, xb, yb_):` | Starts the inner function `lead`. It draws a leader line, a thin line from a point to its label. |
| 120 | `        o.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb_:.1f}" stroke="{INK}" stroke-width="1"/>')` | Adds the line from `xa`, `ya` to `xb`, `yb_`, 1 unit wide, in the colour `INK`. |
| 122 | `    # old loop` | Comment: the label of the old read loop. |
| 123 | `    xo, yo = lx(math.sqrt(18 * 22)), sy(467.8)` | `xo`, `yo`: the position of the point of the old read loop, computed in the same way as in line 108 and line 112 from numbers that are written here a second time. |
| 124 | `    lead(xo - 5, yo + 6, lx(8.2) + 96, sy(400) - 14)` | Draws the leader line from that point to its label. |
| 125 | `    lab(lx(8.2), sy(400), ["Old read loop", "18 to 22 lines", "465.5 to 470.1 GB/s"])` | Writes the label of the old read loop, three text lines: its name, its window depth and its total. |
| 126 | `    # new loop` | Comment: the label of the new loop. |
| 127 | `    xn, yn = lx(math.sqrt(36 * 40)), sy(299.15)` | `xn`, `yn`: the position of the point of the new load-only loop, again from numbers written here a second time. |
| 128 | `    lead(xn + 5, yn + 6, xn + 44, sy(215) - 14)` | Draws the leader line from that point to its label. |
| 129 | `    lab(xn + 30, sy(215), ["New load-only loop", "36 to 40 lines", "288.5 to 309.8 GB/s", "about 36 % below the old loop"])` | Writes the label of the new load-only loop, four text lines: its name, its window depth, its total, and how far it lies below the old loop in percent. |
| 130 | `    # 256 nop` | Comment: the label of the loop with 256 `nop`. |
| 131 | `    lab(lx(12) + 10, sy(546.45) + 4.5, ["Load-only loop + 256 nop: 8 to 12 lines, 543.9 to 549.0 GB/s"])` | Writes a label of one line beside the point of `read_nop256`: its window depth and its total. |
| 132 | `    # one load per line` | Comment: the label of the loop with one load per line. |
| 133 | `    lab(lx(156) - 8, sy(232.6) - 34, ["One load per line", "156 to 164 lines", "230.2 to 235.0 GB/s"], "end")` | Writes the label of `read_1pl`, three text lines that end at the position (`"end"`): its name, its window depth and its total. |
| 134 | `    # groups` | Comment: the labels of the three groups. |
| 135 | `    lab(lx(32) + 12, sy(470) + 4.5, [f"Fast: {NFAST} loops, 459 to 480 GB/s"], "start", False)` | Writes the label of the fast group: the number `NFAST` of loops and the range of their totals. `False` at the end means not bold. |
| 136 | `    lab(lx(60), sy(345), [f"Slow: {NSLOW} loops, 230 to 310 GB/s"], "start", False)` | Writes the label of the slow group: the number `NSLOW` of loops and the range of their totals. |
| 137 | `    lead(lx(32), sy(110) - 4, lx(32) + 14, sy(110) - 4)` | Draws a short leader line at the right edge of the yellow band. |
| 138 | `    lab(lx(32) + 18, sy(110), ["The total falls here:", "at about 30 lines"])` | Writes the label of the band, two text lines: the total falls here, at about 30 lines. |
| 139 | `    lab(lx(24.5), sy(366.45) + 4.5, [f"Between: {NBETW} loops"], "end", False)` | Writes the label of the group between the two states, with the number `NBETW` of loops. |
| 140 | `    o.append("</svg>")` | Adds the closing `</svg>` tag. |
| 141 | `    return "\n".join(o)` | Returns the picture: all lines of `o`, joined with line breaks. |

### The reference list and the function `ref` (lines 144 to 167)

| Line | Source | Explanation |
|---:|---|---|
| 144 | `# ---------------------------------------------------------------- text` | Comment: a divider line with the title `text`. |
| 145 | `REFS = [` | Starts the list `REFS`, the 15 references of the page. The page numbers them from 1 in this order. |
| 146 | `    f"Facts sheet with every number of this page: {W}/FINDINGS.md",` | Reference 1: the facts sheet with every number of the page, `FINDINGS.md` in the working folder `W`. |
| 147 | `    "Full report: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-read-drop.html",` | Reference 2: the full report, an HTML file in the folder `new-test-kernel`. |
| 148 | `    f"Original run: {R}/kernels-20261113T181222Z/threads120.csv (benchmark bandwidth.c)",` | Reference 3: the original run, the file `threads120.csv` of one result folder (benchmark `bandwidth.c`). |
| 149 | `    f"Copy and write runs with a common stop: {R}/w120-R1-20261115T185140Z/ (files p4copy.csv, p3write.csv)",` | Reference 4: the copy and write runs with a common stop, two CSV files of one result folder. |
| 150 | `    f"Write under two stop rules at two interval lengths (earlier runs with 64 processes): {R}/B10a-* and {R}/B10b-*",` | Reference 5: the write runs under two stop rules at two interval lengths, earlier runs with 64 processes. |
| 151 | `    f"Read runs at 64+56: {R}/w120-R0-20261115T165608Z/, w120-R0b-20261115T170342Z/, w120-R1-20261115T185140Z/, w120-R5-20261115T203152Z/, w120-R6-20261115T203438Z/",` | Reference 6: the read runs at 64 plus 56 threads, five result folders. |
| 152 | `    f"Window test: {W}/robsize/ (program robsize.c, results in results/rob-k1-*.csv, rob-k2-*.csv, rob-k3-*.csv)",` | Reference 7: the window test, the folder `robsize` with the program `robsize.c` and three result files. |
| 153 | `    f"Thread layouts: {R}/w120-R0b-20261115T170342Z/ and {R}/w120-R1-20261115T185140Z/p5r5656.csv",` | Reference 8: the thread layouts, one result folder and one CSV file of a second one. |
| 154 | `    f"Different loops on the two meshes: {R}/w120-R3-20261115T193922Z/",` | Reference 9: the run with different loops on the two meshes, one result folder. |
| 155 | `    f"Latency probe: {R}/w120-R4-20261115T200016Z/",` | Reference 10: the latency probe, one result folder. |
| 156 | `    f"Mesh counters: {R}/w120-RC1-20261115T190208Z/. Memory-port counters: {R}/w120-RC2-20261115T192222Z/",` | Reference 11: the mesh counters and the memory-port counters, two result folders. |
| 157 | `    f"Scrambled-order run: {R}/w120-R7-20261115T205946Z/",` | Reference 12: the scrambled-order run, one result folder. |
| 158 | `    f"Test programs: {W}/../bwx12-2026-11-15/bwx12.c and {W}/../bwx13-2026-11-15/bwx13.c",` | Reference 13: the two test programs, `bwx12.c` and `bwx13.c`. |
| 159 | `    f"Load and login records of all runs: {R}/w120-*/env.txt and launches.txt",` | Reference 14: the load and login records of all runs, the files `env.txt` and `launches.txt` of the result folders. |
| 160 | `    f"Generator of this page: {W}/easy_read.py",` | Reference 15: the generator of the page, this script. |
| 161 | `]` | Ends the list `REFS`. |
| 164 | `def ref(*n):` | Starts the function `ref`. It takes one or more reference numbers and returns the citation text for the page. |
| 165 | `    return '<span class="ref">' + "".join(f"[Ref{i}]" for i in n) + "</span>"` | Returns an HTML `<span>` of the class `ref` that holds `[Ref` and the number and `]` for each number given. |

### The word list and the flow boxes (lines 168 to 204)

| Line | Source | Explanation |
|---:|---|---|
| 168 | `WORDS = [` | Starts the list `WORDS`, the 23 entries of the section "Words used here" of the page. Each entry is a pair: the term and its definition. |
| 169 | `    ("CRB", "The Arm server under test. It has 128 cores of type Neoverse V3AE. The tests use CPUs 0 to 119."),` | Entry `CRB`: the Arm server under test, its core type and the CPUs that the tests use. |
| 170 | `    ("loop", "One timed loop of the benchmark. The benchmark calls it a kernel. It is not the Linux kernel."),` | Entry `loop`: one timed loop of the benchmark, which the benchmark calls a kernel. |
| 171 | `    ("old read loop", "The read loop of the old benchmark. Per 128 B it holds 4 load instructions and 8 vector adds."),` | Entry `old read loop`: what the read loop of the old benchmark holds per 128 B. |
| 172 | `    ("new read loop, load-only loop", "The read loop of the new benchmark. Per 256 B it holds 8 load instructions and nothing else. A C version and an assembly version exist. This page shows the assembly version where both were measured."),` | Entry `new read loop, load-only loop`: what the read loop of the new benchmark holds per 256 B, and which version the page shows. |
| 173 | `    ("nop", "An instruction that does nothing. It still uses one place in the window."),` | Entry `nop`: an instruction that does nothing and still uses one place in the window. |
| 174 | `    ("padded loop", "The load-only loop with nop instructions added."),` | Entry `padded loop`: the load-only loop with `nop` instructions added. |
| 175 | `    ("filler", "Extra instructions in a loop that are not needed to read the data: nop or adds."),` | Entry `filler`: extra instructions in a loop that are not needed to read the data. |
| 176 | `    ("line", "One cache line. It is 64 B."),` | Entry `line`: one cache line of 64 B. |
| 177 | `    ("address order", "The loop reads its buffer from the lowest address to the highest, one block after the next."),` | Entry `address order`: the loop reads its buffer from the lowest address to the highest. |
| 178 | `    ("scrambled order", "The loop reads the same bytes, but it jumps between the 256 B blocks."),` | Entry `scrambled order`: the loop reads the same bytes and jumps between the 256 B blocks. |
| 179 | `    ("slow state, fast state", "Slow state: the 120 threads at 64+56 run the new read loop (about 300 GB/s). Fast state: the same threads run the old loop or a padded loop (459 GB/s or more)."),` | Entry `slow state, fast state`: the two conditions of the 120 threads that the page compares. |
| 180 | `    ("window", "The instructions that a core holds between fetch and retirement. The core can start the loads of all instructions in the window before the first one finishes."),` | Entry `window`: the instructions that a core holds between fetch and retirement. |
| 181 | `    ("window depth", "The number of 64 B lines that the loads inside one full window touch. It was measured for each loop with one thread. The result is a range, for example 36 to 40 lines."),` | Entry `window depth`: the number of 64 B lines that the loads inside one full window touch. |
| 182 | `    ("mesh 0, mesh 1", "The chip has two meshes (grids of links that connect cores, cache and memory ports). CPUs 0 to 63 are on mesh 0. CPUs 64 to 119 are on mesh 1."),` | Entry `mesh 0, mesh 1`: the two meshes of the chip and their CPUs. |
| 183 | `    ("64+56", "64 threads on mesh 0 and 56 threads on mesh 1. Each thread reads its own 256 MiB buffer. Other layouts use the same form, for example 64+0."),` | Entry `64+56`: 64 threads on mesh 0 and 56 threads on mesh 1, each with its own buffer of 256 MiB. |
| 184 | `    ("DRAM", "The main memory of the machine. A 256 MiB buffer does not fit in the caches, so the data comes from DRAM."),` | Entry `DRAM`: the main memory of the machine. |
| 185 | `    ("total", "The sum of the rates of all threads, in GB/s. 1 GB is 1e9 bytes."),` | Entry `total`: the sum of the rates of all threads in GB/s. |
| 186 | `    ("whole-pass stop", "The stop rule of the benchmark. A thread stops only at the end of a whole pass over its buffer. The threads stop at different times."),` | Entry `whole-pass stop`: the stop rule of the benchmark. |
| 187 | `    ("common stop", "All threads stop at the same time."),` | Entry `common stop`. Its text says that all threads stop at the same time. In the runner each thread ends its interval at its first clock read at or after one common deadline, so the end times differ a little. |
| 188 | `    ("lines in flight", "The lines that one core has requested from memory and has not yet received."),` | Entry `lines in flight`: the lines that one core has requested from memory and has not yet received. |
| 189 | `    ("prefetcher", "The part of a core that requests data before the loop asks for it."),` | Entry `prefetcher`: the part of a core that requests data before the loop asks for it. |
| 190 | `    ("n", "The number of timed intervals behind a value."),` | Entry `n`: the number of timed intervals behind a value. |
| 191 | `    ("est.", "Estimate. The value is computed with an assumption. It is not measured directly."),` | Entry `est.`: an estimate, a value that is computed with an assumption. |
| 192 | `]` | Ends the list `WORDS`. |
| 194 | `FLOW = [` | Starts the list `FLOW`, the seven boxes of the overview in section 3 of the page. Each entry holds the step number, the question, the short answer, and the class `held` or `rej`. The class sets the colour of the line above the answer in the box: blue, or orange for `rej` (lines 337 to 338). |
| 195 | `    ("1", "Did all three drop?", "Only read", "held"),` | Box 1: the question whether all three kinds of loop dropped. Class `held`. |
| 196 | `    ("2", "What in the loop decides it?", "Enough filler of any kind. The adds are not needed.", "held"),` | Box 2: the question what in the loop decides the result. Class `held`. |
| 197 | `    ("3", "Why does filler help?", "It makes the window cover fewer lines", "held"),` | Box 3: the question why filler helps. Class `held`. |
| 198 | `    ("4", "Same in other thread layouts?", "Yes. The drop appears only with many threads on both meshes.", "held"),` | Box 4: the question whether other thread layouts show the same. Class `held`. |
| 199 | `    ("5", "Do deep-window cores take from the others?", "Yes", "held"),` | Box 5: the question whether cores with a deep window take from the others. Class `held`. |
| 200 | `    ("6", "Is the chip congested when slow?", "No", "rej"),` | Box 6: the question whether the chip is congested in the slow state. Class `rej`, the idea of this step was rejected. |
| 201 | `    ("7", "Is the deep window alone enough?", "No. It also needs address order.", "held"),` | Box 7: the question whether the deep window alone is enough. Class `held`. |
| 202 | `]` | Ends the list `FLOW`. |

### Function `step`: the HTML of one step box (lines 205 to 217)

| Line | Source | Explanation |
|---:|---|---|
| 205 | `def step(num, title, tag, tagtxt, q, idea, test, result):` | Starts the function `step`. It returns the HTML of one step of section 3: a number, a title, a tag, and four lists (question, idea, test, result). |
| 206 | `    def ul(items):` | Starts the inner function `ul`. It turns a list of texts into an HTML list. |
| 207 | `        return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"` | Returns the `<ul>` element with one `<li>` item per text. |
| 208 | `    return f"""<section class="step" id="s{num}">` | Starts the text that `step` returns: a `<section>` of the class `step` with the id `s` and the step number. The overview boxes link to this id. |
| 209 | `<h3><span class="num">{num}</span>{title}<span class="tag {tag}">{tagtxt}</span></h3>` | Text of the page: the heading of the step, with the number in a round mark, the title, and the tag text in a mark of the class `tag`. |
| 210 | `<div class="qitr">` | Text of the page: opens the grid with the four parts of the step. |
| 211 | `<div class="k">Question</div><div class="v">{ul(q)}</div>` | Text of the page: the label `Question` and the list of the question texts. |
| 212 | `<div class="k">Idea</div><div class="v">{ul(idea)}</div>` | Text of the page: the label `Idea` and the list of the idea texts. |
| 213 | `<div class="k">Test</div><div class="v">{ul(test)}</div>` | Text of the page: the label `Test` and the list of the test texts. |
| 214 | `<div class="k res">Result</div><div class="v res">{ul(result)}</div>` | Text of the page: the label `Result` and the list of the result texts. The class `res` gives this part its own background. |
| 215 | `</div></section>"""` | Ends the text: closes the grid and the section. |

### The list `STEPS`: the text of the seven steps (lines 218 to 299)

| Line | Source | Explanation |
|---:|---|---|
| 218 | `STEPS = [` | Starts the list `STEPS`. Each entry is one call of `step` and so the HTML of one step box. Every result number in these texts is fixed text of this file. |
| 219 | `    step(1, "Did read, write and copy all drop?", "held", "Idea held",` | Step 1: the number, the title (did read, write and copy all drop), the class `held` and the tag text `Idea held`. |
| 220 | `         ["Read and write looked lower. Copy did not. Is each of these three results real?"],` | Step 1, question: read and write looked lower and copy did not, and the step asks whether each of the three results is real. |
| 221 | `         ["The benchmark uses the whole-pass stop.",` | Step 1, idea, text 1: the benchmark uses the whole-pass stop. |
| 222 | `          "With this rule the threads stop at different times.",` | Step 1, idea, text 2: with this rule the threads stop at different times. |
| 223 | `          "This can move a total without any change in the chip."],` | Step 1, idea, text 3: this can move a total without any change in the chip. |
| 224 | `         ["Run old and new loops with a common stop at 64+56 " + ref(4) + ".",` | Step 1, test, text 1: run old and new loops with a common stop at 64 plus 56 threads. `ref(4)` adds the citation of reference 4. |
| 225 | `          "Compare write under two stop rules (whole-pass stop, common stop), each with intervals of 0.5 s and 15 s. These are earlier runs with 64 processes. Each case has 64 intervals " + ref(5) + "."],` | Step 1, test, text 2: compare write under two stop rules, each with intervals of 0.5 s and 15 s, in earlier runs with 64 processes (reference 5). |
| 226 | `         ["Copy: 152.4 to 153.6 GB/s for all loops. No drop.",` | Step 1, result, text 1: the range of the copy totals of all loops, and that copy did not drop. |
| 227 | `          "Write, earlier runs, whole-pass stop at 0.5 s: old is 21.5 % above new (medians 144.1 and 118.6 GB/s).",` | Step 1, result, text 2: for write in the earlier runs with the whole-pass stop at 0.5 s, how far the old loop lies above the new one, with the two medians. |
| 228 | `          "Write, earlier runs, common stop: old is 3.7 % above new at 0.5 s (medians 126.4 and 122.0 GB/s) and 3.1 % above new at 15 s (126.6 and 122.8 GB/s). The percentages are copied from the facts sheet.",` | Step 1, result, text 3: the same comparison with the common stop, at 0.5 s and at 15 s. The text says that the percentages are copied from the facts sheet. |
| 229 | `          "Write at 64+56 with a common stop: old 126.1 to 126.8 GB/s, new 121.3 to 129.3 GB/s (2 intervals per loop) " + ref(4) + ".",` | Step 1, result, text 4: the write totals of the old and the new loop at 64 plus 56 threads with a common stop (reference 4). |
| 230 | `          "Read: 465.5 to 470.1 GB/s (old) against 288.5 to 309.8 GB/s (new). This drop stays " + ref(6) + ".",` | Step 1, result, text 5: the read totals of the old and the new loop, and that this drop stays (reference 6). |
| 231 | `          "<b>So only read dropped by a large amount. Copy did not drop. Write keeps a small difference of 3 to 4 %.</b>"]),` | Step 1, result, text 6, in bold: only read dropped by a large amount, copy did not drop, and write keeps a small difference. The `]),` ends the result list and the call of `step`. |
| 232 | `    step(2, "What in the loop decides fast or slow?", "held", "Idea A rejected, idea B held",` | Step 2: the number, the title (what in the loop decides fast or slow), the class `held` and the tag text `Idea A rejected, idea B held`. |
| 233 | `         ["The old loop has 8 vector adds per 128 B. The new loop has none. Do the adds matter?"],` | Step 2, question: the old loop has 8 vector adds per 128 B and the new loop has none, and the step asks whether the adds matter. |
| 234 | `         ["Idea A: the adds must wait for the loaded data, and this slows the loads down in a useful way.",` | Step 2, idea A: the adds must wait for the loaded data, and this slows the loads down in a useful way. |
| 235 | `          "Idea B: enough extra instructions of any kind help, also instructions that do nothing."],` | Step 2, idea B: enough extra instructions of any kind help, also instructions that do nothing. |
| 236 | `         ["Build 26 new loop variants in a copy of the test program " + ref(13) + ".",` | Step 2, test, text 1: build 26 new loop variants in a copy of the test program (reference 13). |
| 237 | `          "Add vector adds that use the loaded data. Add vector adds that do not use it. Add nop instructions.",` | Step 2, test, text 2: add vector adds that use the loaded data, vector adds that do not use it, and `nop` instructions. |
| 238 | `          "Measure each variant at 64+56 " + ref(6) + "."],` | Step 2, test, text 3: measure each variant at 64 plus 56 threads (reference 6). |
| 239 | `         ["16 adds per 256 B that use the data: 466.7 to 469.8 GB/s.",` | Step 2, result, text 1: the total range with 16 adds per 256 B that use the data. |
| 240 | `          "16 adds per 256 B that do not use the data: 469.2 to 469.7 GB/s. This is the same.",` | Step 2, result, text 2: the total range with 16 adds that do not use the data, and that it is the same. |
| 241 | `          "72 to 192 nop per 256 B: 459 to 480 GB/s. 256 nop per 256 B: 543.9 to 549.0 GB/s.",` | Step 2, result, text 3: the total ranges with 72 to 192 `nop` and with 256 `nop` per 256 B. |
| 242 | `          "32 to 56 nop per 256 B: 284.8 to 309.1 GB/s. This is too little filler.",` | Step 2, result, text 4: the total range with 32 to 56 `nop`, which the text calls too little filler. |
| 243 | `          "Software prefetch instructions: 289 to 316 GB/s. They do not help.",` | Step 2, result, text 5: the total range with software prefetch instructions, and that they do not help. |
| 244 | `          "<b>Idea A is rejected. Idea B held: the kind of filler does not matter, the amount does.</b>"]),` | Step 2, result, text 6, in bold: idea A is rejected and idea B held. The kind of filler does not matter, the amount does. The `]),` ends the call of `step`. |
| 245 | `    step(3, "Why does filler help?", "held", "Idea held",` | Step 3: the number, the title (why does filler help), the class `held` and the tag text `Idea held`. |
| 246 | `         ["What does a nop change, when it does no work?"],` | Step 3, question: what a `nop` changes when it does no work. |
| 247 | `         ["The window of a core holds a fixed number of instructions.",` | Step 3, idea, text 1: the window of a core holds a fixed number of instructions. |
| 248 | `          "Filler takes places in the window. Then fewer loads fit in the window.",` | Step 3, idea, text 2: filler takes places in the window, so fewer loads fit in it. |
| 249 | `          "So the window covers fewer lines."],` | Step 3, idea, text 3: so the window covers fewer lines. |
| 250 | `         ["Measure the window with one thread " + ref(7) + ".",` | Step 3, test, text 1: measure the window with one thread (reference 7). |
| 251 | `          "Measure, for each loop, how many lines one full window covers."],` | Step 3, test, text 2: measure, for each loop, how many lines one full window covers. |
| 252 | `         ["The window holds 684 nop, or 159 instructions that write a vector register.",` | Step 3, result, text 1: how many `nop` and how many instructions that write a vector register the window holds. |
| 253 | `          "Old loop: 18 to 22 lines. New loop: 36 to 40 lines.",` | Step 3, result, text 2: the window depth of the old loop and of the new loop in lines. |
| 254 | `          "All loops with a range at or above 32 to 34 lines are slow. All loops with a range at or below 24 to 28 lines are fast.",` | Step 3, result, text 3: the two depth ranges that part the slow loops from the fast loops. |
| 255 | `          "Four loops lie between these (26 to 32 lines). Two are slow and two are in between (325.5 to 366.6 GB/s).",` | Step 3, result, text 4: the four loops that lie between these ranges, and their states. |
| 256 | `          "The adds of the old loop use up the vector-register places of the window (159 places). The old loop is fast for this reason, not because the adds wait for data.",` | Step 3, result, text 5: the adds of the old loop use up the vector-register places of the window, and the old loop is fast for this reason. |
| 257 | `          "<b>This is the chart of section 2.</b>"]),` | Step 3, result, text 6, in bold: this is the chart of section 2. The `]),` ends the call of `step`. |
| 258 | `    step(4, "Is it the same in other thread layouts?", "held", "Idea held",` | Step 4: the number, the title (is it the same in other thread layouts), the class `held` and the tag text `Idea held`. |
| 259 | `         ["Does a padded loop behave like the old loop everywhere?"],` | Step 4, question: whether a padded loop behaves like the old loop everywhere. |
| 260 | `         ["If the window depth is the cause, a padded loop with a similar depth follows the old loop in every layout."],` | Step 4, idea: if the window depth is the cause, a padded loop with a similar depth follows the old loop in every layout. |
| 261 | `         ["Run the old loop, the new loop and two padded loops in 7 layouts " + ref(8) + ".",` | Step 4, test, text 1: run the old loop, the new loop and two padded loops in 7 layouts (reference 8). |
| 262 | `          "Each pair of loop and layout has one interval."],` | Step 4, test, text 2: each pair of loop and layout has one interval. |
| 263 | `         ["Both padded loops (96 nop and 128 nop) are within 2.3 % of the old loop in all 7 layouts.",` | Step 4, result, text 1: how close the two padded loops stay to the old loop in all 7 layouts. |
| 264 | `          "64+0 (mesh 0 only): old 348.0 GB/s, new 348.4 GB/s. No drop.",` | Step 4, result, text 2: the old and the new total with all threads on mesh 0, and that there is no drop. |
| 265 | `          "56+56: old 534.8 GB/s, new 300.1 GB/s.",` | Step 4, result, text 3: the old and the new total at 56 plus 56 threads. |
| 266 | `          "<b>The drop exists only with many threads on both meshes.</b>"]),` | Step 4, result, text 4, in bold: the drop exists only with many threads on both meshes. The `]),` ends the call of `step`. |
| 267 | `    step(5, "Do deep-window cores take from the others?", "held", "Idea held",` | Step 5: the number, the title (do deep-window cores take from the others), the class `held` and the tag text `Idea held`. |
| 268 | `         ["Does the rate of a thread depend on the loop of the other threads?"],` | Step 5, question: whether the rate of a thread depends on the loop of the other threads. |
| 269 | `         ["A core with a deep window requests more lines ahead. It may take a larger share of the memory traffic."],` | Step 5, idea: a core with a deep window requests more lines ahead and may take a larger share of the memory traffic. |
| 270 | `         ["Run two processes at the same time, one per mesh, with different loops " + ref(9) + "."],` | Step 5, test: run two processes at the same time, one per mesh, with different loops (reference 9). |
| 271 | `         ["New loop on mesh 0, 256-nop loop on mesh 1: mesh 0 reads 349.8 GB/s, mesh 1 reads 108.2 GB/s.",` | Step 5, result, text 1: the rates of the two meshes with the new loop on mesh 0 and the loop with 256 `nop` on mesh 1. |
| 272 | `          "Mesh 0 alone with the new loop reads 348 GB/s. So mesh 0 reads as if mesh 1 were idle.",` | Step 5, result, text 2: the rate of mesh 0 alone with the new loop, and that mesh 0 reads as if mesh 1 were idle. |
| 273 | `          "256-nop loop on both: 327.4 and 221.8 GB/s (total 549.1 GB/s).",` | Step 5, result, text 3: the two rates and the total with the loop with 256 `nop` on both meshes. |
| 274 | `          "New loop on both: 175.7 and 127.2 GB/s (total 302.9 GB/s).",` | Step 5, result, text 4: the two rates and the total with the new loop on both meshes. |
| 275 | `          "<b>The deeper window takes the larger share. When all cores have a deep window, all are slow.</b>"]),` | Step 5, result, text 5, in bold: the deeper window takes the larger share, and when all cores have a deep window, all are slow. The `]),` ends the call of `step`. |
| 276 | `    step(6, "Is the chip congested in the slow state?", "rej", "Idea rejected",` | Step 6: the number, the title (is the chip congested in the slow state), the class `rej` and the tag text `Idea rejected`. |
| 277 | `         ["Are the mesh or DRAM overloaded in the slow state?"],` | Step 6, question: whether the mesh or the memory are overloaded in the slow state. |
| 278 | `         ["Too many requests fill the queues of the mesh. Requests are retried. DRAM does wasted reads."],` | Step 6, idea: too many requests fill the queues of the mesh, requests are retried, and the memory does wasted reads. |
| 279 | `         ["Read the counters of the mesh and of the 24 memory ports with root rights " + ref(11) + ".",` | Step 6, test, text 1: read the counters of the mesh and of the 24 memory ports with root rights (reference 11). |
| 280 | `          "Measure the time of one memory request on one core per mesh, while the other 118 cores read " + ref(10) + "."],` | Step 6, test, text 2: measure the time of one memory request on one core per mesh while the other 118 cores read (reference 10). |
| 281 | `         ["DRAM gets 1.00 read request per line in the slow state and 1.00 in the fast state with 96 nop. The 256-nop loop has 1.08. So the slow state wastes no read.",` | Step 6, result, text 1: the read requests per line that the memory gets in the slow state, in the fast state with 96 `nop`, and with 256 `nop`. |
| 282 | `          "Request retries per line: 0.047 (slow) against 0.072 (fast). The slow state has fewer.",` | Step 6, result, text 2: the request retries per line in the slow and in the fast state. |
| 283 | `          "One exception: data-link stalls to the north and south are higher in the slow state (north: 0.119 against 0.069 per line).",` | Step 6, result, text 3: one exception, the data-link stalls to the north and to the south. |
| 284 | `          "One memory request takes 203 to 211 ns with the new loop on all cores (slow) against 238 to 287 ns with a padded loop on all cores (fast). The slow state is quicker.",` | Step 6, result, text 4: the time of one memory request in the slow and in the fast state. |
| 285 | `          "Lines in flight per core: 6.5 to 9.2 (slow, est.) against 14.9 to 25.3 (fast, est.).",` | Step 6, result, text 5: the lines in flight per core in both states. The text marks both values as estimates. |
| 286 | `          "<b>No queue and no memory port is congested. In the slow state the cores keep fewer requests outstanding.</b>"]),` | Step 6, result, text 6, in bold: no queue and no memory port is congested, and in the slow state the cores keep fewer requests outstanding. The `]),` ends the call of `step`. |
| 287 | `    step(7, "Is the deep window alone enough?", "held", "Idea held",` | Step 7: the number, the title (is the deep window alone enough), the class `held` and the tag text `Idea held`. |
| 288 | `         ["Is the cause the number of lines in the window, or the way a core treats a stream in address order?"],` | Step 7, question: whether the cause is the number of lines in the window, or the way in which a core treats a stream in address order. |
| 289 | `         ["A core treats a stream in address order in a special way (the prefetcher follows it).",` | Step 7, idea, text 1: a core treats a stream in address order in a special way: the prefetcher follows it. |
| 290 | `          "If this is part of the cause, the same loads in a scrambled order do not show the drop."],` | Step 7, idea, text 2: if this is part of the cause, the same loads in a scrambled order do not show the drop. |
| 291 | `         ["Read the same bytes with the same loads, but visit the 256 B blocks in a scrambled order " + ref(12) + ".",` | Step 7, test, text 1: read the same bytes with the same loads, and visit the 256 B blocks in a scrambled order (reference 12). |
| 292 | `          "One interval of 10 s per loop and order at 64+56. One scrambled order was tested."],` | Step 7, test, text 2: one interval of 10 s per loop and order at 64 plus 56 threads, with one scrambled order tested. |
| 293 | `         ["Address order, load-only loop: 297.8 GB/s.",` | Step 7, result, text 1: the total of the load-only loop in address order. |
| 294 | `          "Scrambled order, same loads: 489.6 GB/s.",` | Step 7, result, text 2: the total of the same loads in scrambled order. |
| 295 | `          "In scrambled order the deep window is the faster one (489.6 against 382.5 GB/s with 256 nop).",` | Step 7, result, text 3: in scrambled order the deep window is the faster one, with the two totals. |
| 296 | `          "<b>In this run the drop needed a deep window and address order together.</b>",` | Step 7, result, text 4, in bold: in this run the drop needed a deep window and address order together. |
| 297 | `          "Hypothesis: a core limits its own requests for a stream in address order (section 4). Steps 6 and 7 fit this. They do not prove it."]),` | Step 7, result, text 5: a hypothesis, marked as such: a core limits its own requests for a stream in address order. The text says that steps 6 and 7 fit this and do not prove it. The `]),` ends the call of `step`. |
| 298 | `]` | Ends the list `STEPS`. |

### The text `CSS`: the style sheet of the page (lines 300 to 352)

| Line | Source | Explanation |
|---:|---|---|
| 300 | `CSS = """` | Starts the text `CSS`, the style rules of the page. The text ends in line 350. |
| 301 | `:root{color-scheme:light}` | CSS: the page asks the browser for a light colour scheme only. |
| 302 | `*{box-sizing:border-box}` | CSS: the width and the height of every element include its padding and its border. |
| 303 | `body{margin:0;background:#fcfcfb;color:#0b0b0b;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: the body has no margin, a background that is nearly white, nearly black text, and a system font of 16 px with a line height of 1.55. |
| 304 | `main{max-width:980px;margin:0 auto;padding:28px 16px 64px}` | CSS: the main block is at most 980 px wide and centred, with padding around it. |
| 305 | `h1{font-size:28px;line-height:1.25;margin:0 0 6px}` | CSS: the main heading has 28 px type. |
| 306 | `h2{font-size:21px;margin:40px 0 10px;padding-top:14px;border-top:1px solid #e4e3df}` | CSS: a section heading has 21 px type, space above it and a thin line at its top. |
| 307 | `h3{font-size:17px;margin:0 0 8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}` | CSS: a sub heading has 17 px type. Its parts (the number mark, the title, the tag) stand in one row with a gap of 10 px and may wrap. |
| 308 | `p{margin:8px 0}` | CSS: a paragraph has a margin of 8 px above and below. |
| 309 | `ul{margin:4px 0 8px;padding-left:22px}` | CSS: a list has small margins and a left padding of 22 px. |
| 310 | `li{margin:3px 0}` | CSS: a list item has a margin of 3 px above and below. |
| 311 | `.sub{color:#52514e;font-size:14px;margin:0 0 18px}` | CSS: the class `sub`, the line under the main heading, is grey with 14 px type. |
| 312 | `.short{background:#f1f0ec;border-left:4px solid #1f6fc9;padding:12px 16px;margin:14px 0}` | CSS: the class `short`, the box of the short version, has a light grey background and a blue bar of 4 px at its left. |
| 313 | `.short p{margin:4px 0}` | CSS: a paragraph inside that box has a margin of 4 px. |
| 314 | `dl.words{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:4px 14px;margin:8px 0;font-size:15px}` | CSS: the word list is a grid of two columns, the term in a column of 120 px to 210 px and the definition beside it. |
| 315 | `dl.words dt{font-weight:600}` | CSS: a term of the word list is bold. |
| 316 | `dl.words dd{margin:0}` | CSS: a definition of the word list has no margin. |
| 317 | `@media (max-width:600px){dl.words{grid-template-columns:1fr;gap:0}dl.words dd{margin:0 0 8px}}` | CSS: on a screen of at most 600 px width the word list has one column. |
| 318 | `.tw{overflow-x:auto;margin:10px 0}` | CSS: the class `tw`, the wrapper of a table, scrolls sideways when the table is too wide. |
| 319 | `table{border-collapse:collapse;font-size:14px;line-height:1.35}` | CSS: a table has joined cell borders and 14 px type. |
| 320 | `th,td{border-bottom:1px solid #e4e3df;padding:4px 10px;text-align:left;vertical-align:top}` | CSS: a table cell has a thin line at its bottom, padding, and text at the left and at the top. |
| 321 | `th{background:#f1f0ec;font-weight:600}` | CSS: a head cell has a light grey background and bold type. |
| 322 | `td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}` | CSS: a cell of the class `n` holds a number: it is right-aligned, uses digits of equal width and does not wrap. |
| 323 | `figure{margin:16px 0}` | CSS: a figure has a margin of 16 px above and below. |
| 324 | `.fig{overflow-x:auto;border:1px solid #e4e3df;border-radius:6px;background:#fcfcfb}` | CSS: the class `fig`, the frame of a picture, has a thin border with round corners and scrolls sideways when the picture is too wide. |
| 325 | `.fig svg{display:block;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}` | CSS: a picture inside the frame is a block and uses the system font. |
| 326 | `figcaption{font-size:14.5px;margin-top:6px}` | CSS: a figure caption has 14.5 px type. |
| 327 | `.take{font-weight:600}` | CSS: the class `take`, the first sentence of a caption, is bold. |
| 328 | `.ref{color:#52514e;font-size:0.85em;white-space:nowrap}` | CSS: the class `ref`, a citation, is grey, a little smaller, and does not wrap. |
| 329 | `.note{color:#52514e;font-size:14px}` | CSS: the class `note` is grey with 14 px type. |
| 330 | `ol.refs{font-size:14px;padding-left:0;list-style:none}` | CSS: the reference list has 14 px type, no indent and no list numbers. |
| 331 | `ol.refs li{margin:5px 0;overflow-wrap:anywhere}` | CSS: an entry of the reference list has a margin of 5 px, and a long path may break at any place. |
| 332 | `details{margin:8px 0}` | CSS: a folded block has a margin of 8 px above and below. |
| 333 | `summary{cursor:pointer;font-weight:600}` | CSS: the title of a folded block is bold and shows a hand pointer. |
| 334 | `.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px 0;margin:14px 0}` | CSS: the class `flow`, the row of overview boxes, lays its boxes out in a row that may wrap. |
| 335 | `.flow a{flex:1 1 108px;max-width:150px;border:1px solid #c9c7c0;border-radius:6px;padding:8px 8px 9px;background:#fff;color:inherit;text-decoration:none;font-size:13px;line-height:1.35;display:flex;flex-direction:column;gap:5px}` | CSS: one overview box is a link without underline, 108 px to 150 px wide, with a thin border, round corners, a white background and 13 px type. Its parts stand one below the other. |
| 336 | `.flow a .q{font-weight:600}` | CSS: the question in an overview box is bold. |
| 337 | `.flow a .a{margin-top:auto;border-top:3px solid #1f6fc9;padding-top:5px}` | CSS: the answer in an overview box stands at the bottom, under a blue line of 3 px. |
| 338 | `.flow a.rej .a{border-top-color:#c2500a}` | CSS: in a box of the class `rej` that line is orange. |
| 339 | `.flow .arr{flex:0 0 18px;display:flex;align-items:center;justify-content:center;color:#52514e;font-size:16px}` | CSS: the arrow between two boxes is 18 px wide, centred and grey. |
| 340 | `.num{display:inline-flex;width:26px;height:26px;border-radius:50%;background:#0b0b0b;color:#fff;align-items:center;justify-content:center;font-size:14px;font-weight:600;flex:none}` | CSS: the class `num`, the number mark, is a black circle of 26 px with a white bold number. |
| 341 | `.flow .num{width:21px;height:21px;font-size:12px}` | CSS: inside an overview box the number mark is 21 px. |
| 342 | `.tag{font-size:12.5px;font-weight:600;padding:1px 8px;border-radius:10px;border:1px solid #1f6fc9;color:#17559b;background:#eaf2fc}` | CSS: the class `tag`, the tag of a step, is a small bold text in a round mark with a blue border and a light blue background. |
| 343 | `.tag.rej{border-color:#c2500a;color:#99400a;background:#fdf0e6}` | CSS: a tag of the class `rej` is orange. |
| 344 | `.step{border:1px solid #e4e3df;border-radius:8px;padding:14px 16px 8px;margin:14px 0;background:#fff}` | CSS: the class `step`, a step box, has a thin border, round corners, padding and a white background. |
| 345 | `.qitr{display:grid;grid-template-columns:92px 1fr;gap:2px 12px}` | CSS: the class `qitr`, the four parts of a step, is a grid: a column of 92 px for the labels and a column for the texts. |
| 346 | `.qitr .k{font-weight:600;color:#52514e;padding-top:4px}` | CSS: a label of that grid is bold and grey. |
| 347 | `.qitr .k.res{color:#0b0b0b}` | CSS: the label of the result is nearly black. |
| 348 | `.qitr .v.res{background:#f6f5f1;border-radius:6px;padding:2px 6px}` | CSS: the text of the result has a light background with round corners. |
| 349 | `@media (max-width:600px){.qitr{grid-template-columns:1fr}}` | CSS: on a screen of at most 600 px width that grid has one column. |
| 350 | `"""` | Ends the text `CSS`. |

### Function `build`: the page text and the output file (lines 353 to 473)

| Line | Source | Explanation |
|---:|---|---|
| 353 | `def build():` | Starts the function `build`. It puts the page together and writes it to the file `OUT`. |
| 354 | `    flow = []` | `flow`: the list of the HTML pieces of the overview boxes, empty at the start. |
| 355 | `    for i, (n, q, a, cls) in enumerate(FLOW):` | Starts the loop over the seven entries of `FLOW`. `i` is the number from 0, and the four fields go to `n`, `q`, `a` and `cls`. |
| 356 | `        if i:` | The next line runs for every box except the first. |
| 357 | `            flow.append('<span class="arr" aria-hidden="true">&rarr;</span>')` | Adds an arrow between two boxes: a `<span>` with the HTML name `&rarr;` of a right arrow. `aria-hidden` hides it from screen readers. |
| 358 | `        flow.append(f'<a class="{cls}" href="#s{n}"><span class="num">{n}</span><span class="q">{q}</span><span class="a">{a}</span></a>')` | Adds the box: a link to the step with the id `s` and the number, with the class `held` or `rej`. It holds the number mark, the question and the short answer. |
| 359 | `    words = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in WORDS)` | `words`: the HTML of the word list. For each pair of `WORDS` it holds the term in a `<dt>` element and the definition in a `<dd>` element. |
| 360 | `    refs = "".join(f"<li>[Ref{i+1}] {html.escape(t)}</li>" for i, t in enumerate(REFS))` | `refs`: the HTML of the reference list. For each text of `REFS` it holds one `<li>` item with `[Ref`, the number from 1, `]` and the text. `html.escape` replaces the characters that have a special meaning in HTML. |
| 361 | `    page = f"""<!doctype html>` | Starts the text `page`. The `f` before the quotes makes Python replace each expression in braces by its value. This first line of the page says that the document is HTML. |
| 362 | `<html lang="en" data-theme="light">` | Text of the page: opens the document. The language is English, and the attribute `data-theme` is `light`. |
| 363 | `<head>` | Text of the page: opens the head of the document. |
| 364 | `<meta charset="utf-8">` | Text of the page: the character set is UTF-8. |
| 365 | `<meta name="viewport" content="width=device-width,initial-scale=1">` | Text of the page: the page is as wide as the screen of the device. |
| 366 | `<title>Whole-chip read drop: easy read</title>` | Text of the page: the title in the browser tab. |
| 367 | `<style>{CSS}</style>` | Text of the page: the style rules. The braces put the text `CSS` of lines 300 to 350 into the page. |
| 368 | `</head>` | Text of the page: closes the head. |
| 369 | `<body>` | Text of the page: opens the body. |
| 370 | `<main>` | Text of the page: opens the main block. |
| 371 | `<h1>Why the whole-chip read rate fell with the new test loop: easy read</h1>` | Text of the page: the main heading, which asks why the whole-chip read rate fell with the new test loop. |
| 372 | `<p class="sub">CRB, 120 threads. The investigation ran on 2026-11-15. The original run is from 2026-11-13. This page is the simple version of the full report {ref(2)}. All numbers come from the facts sheet {ref(1)}.</p>` | Text of the page: the line under the heading: the machine, the number of threads, the dates of the investigation and of the original run, and two citations. The page is the simple version of the full report (reference 2), and all numbers come from the facts sheet (reference 1). |
| 374 | `<h2 id="short">Short version</h2>` | Text of the page: the heading of the short version. |
| 375 | `<div class="short">` | Text of the page: opens the box of the short version. |
| 376 | `<p>The benchmark has read, write and copy loops, and with 120 threads only the read total dropped by a large amount: about 300 GB/s with the new loop against about 468 GB/s with the old loop (36 % lower).</p>` | Text of the page: sentence 1 of the short version: with 120 threads only the read total dropped by a large amount, with the totals of the new and of the old loop. |
| 377 | `<p>The new read loop holds only loads, and each core then works on 36 to 40 cache lines at one time instead of 18 to 22.</p>` | Text of the page: sentence 2 of the short version: the new read loop holds only loads, and each core then works on more cache lines at one time. |
| 378 | `<p>The total is 230 to 310 GB/s above about 30 lines, 459 to 480 GB/s at 12 to 28 lines, and 543.9 to 549.0 GB/s (the highest measured) at 8 to 12 lines, and the rule inside the core that causes this is not established.</p>` | Text of the page: sentence 3 of the short version: the total in three ranges of the window depth, and that the rule inside the core that causes this is not established. |
| 379 | `</div>` | Text of the page: closes the box of the short version. |
| 381 | `<details><summary>Words used here</summary>` | Text of the page: opens a folded block with the title `Words used here`. |
| 382 | `<dl class="words">{words}</dl>` | Text of the page: the word list. The braces put in the text `words` of line 359. |
| 383 | `</details>` | Text of the page: closes the folded block. |
| 385 | `<h2 id="goal">1. The goal</h2>` | Text of the page: the heading of section 1, the goal. |
| 386 | `<h3>The problem</h3>` | Text of the page: the sub heading `The problem`. |
| 387 | `<ul>` | Text of the page: opens a list. |
| 388 | `<li>The benchmark got new test loops for read, write and copy.</li>` | Text of the page: list item: the benchmark got new test loops for read, write and copy. |
| 389 | `<li>The new loops were made to do less work per byte. For example, the new read loop has no adds.</li>` | Text of the page: list item: the new loops were made to do less work per byte. |
| 390 | `<li>An earlier test run used old and new loops with 120 threads on CRB {ref(3)}.</li>` | Text of the page: list item: an earlier test run used old and new loops with 120 threads on CRB (reference 3). |
| 391 | `<li>The read total and the write total were lower with the new loops. The copy total was not lower in that file.</li>` | Text of the page: list item: the read total and the write total were lower with the new loops, and the copy total was not. |
| 392 | `</ul>` | Text of the page: closes the list. |
| 393 | `<figure>` | Text of the page: opens the block of figure 1. |
| 394 | `<div class="fig">{fig1()}</div>` | Text of the page: the frame with figure 1. The braces call `fig1` and put its picture in. |
| 395 | `<figcaption><span class="take">Figure 1. The original run: read and write look lower with the new loop, copy does not.</span> 120 threads, stop rule of the benchmark (whole-pass stop), 0.5 s intervals, 6 intervals per loop. The new loop here is the C version. The black mark on a write bar is the median {ref(3)}.</figcaption>` | Text of the page: the caption of figure 1. Its first sentence is the main message. The rest names the conditions of the original run (reference 3). |
| 396 | `</figure>` | Text of the page: closes the block of figure 1. |
| 397 | `<h3>Why it is a mystery</h3>` | Text of the page: the sub heading `Why it is a mystery`. |
| 398 | `<ul>` | Text of the page: opens a list. |
| 399 | `<li><b>Less work gave a lower rate.</b> The new read loop does only loads. It was expected to be at least as fast as the old loop.</li>` | Text of the page: list item: less work gave a lower rate. |
| 400 | `<li><b>With threads on one mesh there is no drop.</b> 64 threads on mesh 0 read 348.0 GB/s with the old loop and 348.4 GB/s with the new loop {ref(8)}.</li>` | Text of the page: list item: with threads on one mesh there is no drop (reference 8). |
| 401 | `<li><b>More threads gave a lower total.</b> The new loop reads 445.0 GB/s with 64+32 threads and 300.1 GB/s with 56+56 threads {ref(8)}.</li>` | Text of the page: list item: more threads gave a lower total (reference 8). |
| 402 | `<li><b>The goal:</b> find which drops are real, and find the cause.</li>` | Text of the page: list item: the goal is to find which drops are real, and to find the cause. |
| 403 | `</ul>` | Text of the page: closes the list. |
| 405 | `<h2 id="answer">2. The answer in one chart</h2>` | Text of the page: the heading of section 2, the answer in one chart. |
| 406 | `<ul>` | Text of the page: opens a list. |
| 407 | `<li>Each point is one read loop, run with 120 threads (64+56).</li>` | Text of the page: list item: each point is one read loop, run with 120 threads. |
| 408 | `<li>The horizontal position is the window depth: how many cache lines the core works on at one time.</li>` | Text of the page: list item: the horizontal position is the window depth. |
| 409 | `<li>The vertical position is the total read rate.</li>` | Text of the page: list item: the vertical position is the total read rate. |
| 410 | `</ul>` | Text of the page: closes the list. |
| 411 | `<figure>` | Text of the page: opens the block of figure 2. |
| 412 | `<div class="fig">{fig2()}</div>` | Text of the page: the frame with figure 2. The braces call `fig2` and put its picture in. |
| 413 | `<figcaption><span class="take">Figure 2. The total depends on the window depth. Loops with a range at or above 32 to 34 lines are slow. Loops with a range at or below 24 to 28 lines are fast.</span> 29 loop variants at 64+56, common stop. Each point is the middle of the lowest and the highest interval (2 to 22 intervals per loop). The horizontal bar is the measured range of the window depth {ref(6, 7)}.</figcaption>` | Text of the page: the caption of figure 2. Its first sentence is the main message. The rest says what a point and a horizontal bar stand for (references 6 and 7). |
| 414 | `</figure>` | Text of the page: closes the block of figure 2. |
| 415 | `<ul>` | Text of the page: opens a list. |
| 416 | `<li><b>The old loop is fast for a reason that nobody intended.</b> Its 8 vector adds per 128 B fill the window. So its window covers only 18 to 22 lines.</li>` | Text of the page: list item: the old loop is fast for a reason that nobody intended. |
| 417 | `<li><b>The new loop removed the adds.</b> Its window covers 36 to 40 lines. This is above the limit of about 30 lines.</li>` | Text of the page: list item: the new loop removed the adds, and its window covers more lines. |
| 418 | `<li><b>The remedy is verified.</b> 72 to 192 nop per 256 B give 459 to 480 GB/s. 256 nop give 543.9 to 549.0 GB/s. This is 17 % above the old loop.</li>` | Text of the page: list item: the remedy is verified, with the totals of the padded loops. |
| 419 | `<li><b>The best point is not known.</b> The loop with 8 to 12 lines gave the highest total. No loop with fewer than 8 lines was tested.</li>` | Text of the page: list item: the best point is not known. No loop with fewer than 8 lines was tested. |
| 420 | `<li><b>Write and copy are not part of this.</b> Copy did not drop. Most of the write drop comes from the stop rule of the benchmark (step 1).</li>` | Text of the page: list item: write and copy are not part of this. |
| 421 | `</ul>` | Text of the page: closes the list. |
| 422 | `<h3>How to read the table</h3>` | Text of the page: the sub heading `How to read the table`. |
| 423 | `<ul>` | Text of the page: opens a list. |
| 424 | `<li><b>Window.</b> A window is not one pass of the loop. It is a part of the core: the list of instructions that the core has fetched and has not yet finished. On CRB it holds up to 684 nop. Several passes of a loop fit in it at one time.</li>` | Text of the page: list item: what the window is. |
| 425 | `<li><b>Window depth.</b> The number of 64 B cache lines that the loads inside one full window touch. The core can request all these lines from memory at one time. Example: about 9 to 10 passes of the new loop fit in the window, and each pass reads 4 lines, so the depth is 36 to 40 lines.</li>` | Text of the page: list item: what the window depth is, with an example. |
| 426 | `<li><b>Sum of the read rates.</b> 120 threads run at the same time: 64 threads on CPUs 0 to 63 and 56 threads on CPUs 64 to 119 (written 64+56). The value is the sum of the rates of all 120 threads.</li>` | Text of the page: list item: what the sum of the read rates is. |
| 427 | `<li><b>Timed intervals (n).</b> The number of timed measurements behind the row. The rate column shows the lowest and the highest of these n measurements.</li>` | Text of the page: list item: what the number of timed intervals (n) is. |
| 428 | `</ul>` | Text of the page: closes the list. |
| 429 | `<div class="tw"><table>` | Text of the page: opens a table inside its wrapper. |
| 430 | `<tr><th>Loop</th><th class="n">Cache lines in one full window (window depth)</th><th class="n">Sum of the read rates of all 120 threads, GB/s</th><th class="n">Timed intervals (n)</th></tr>` | Text of the page: the head row of the table: the loop, the cache lines in one full window, the sum of the read rates of all 120 threads in GB/s, and the number of timed intervals. |
| 431 | `<tr><td>One load per line</td><td class="n">156 to 164</td><td class="n">230.2 to 235.0</td><td class="n">16</td></tr>` | Text of the page: table row for the loop with one load per line. Its three numbers are fixed text. |
| 432 | `<tr><td>New load-only loop</td><td class="n">36 to 40</td><td class="n">288.5 to 309.8</td><td class="n">22</td></tr>` | Text of the page: table row for the new load-only loop. |
| 433 | `<tr><td>Load-only loop + 64 nop</td><td class="n">28 to 32</td><td class="n">325.5 to 333.9</td><td class="n">13</td></tr>` | Text of the page: table row for the load-only loop with 64 `nop`. |
| 434 | `<tr><td>Load-only loop + 72 nop</td><td class="n">24 to 28</td><td class="n">459.0 to 459.3</td><td class="n">2</td></tr>` | Text of the page: table row for the load-only loop with 72 `nop`. |
| 435 | `<tr><td>Old read loop</td><td class="n">18 to 22</td><td class="n">465.5 to 470.1</td><td class="n">22</td></tr>` | Text of the page: table row for the old read loop. |
| 436 | `<tr><td>Load-only loop + 256 nop</td><td class="n">8 to 12</td><td class="n">543.9 to 549.0</td><td class="n">9</td></tr>` | Text of the page: table row for the load-only loop with 256 `nop`. |
| 437 | `</table></div>` | Text of the page: closes the table and its wrapper. |
| 438 | `<p class="note">The full report has all 29 rows {ref(2)}.</p>` | Text of the page: a note that the full report has all 29 rows (reference 2). |
| 440 | `<h2 id="path">3. How we got there</h2>` | Text of the page: the heading of section 3, how we got there. |
| 441 | `<p>Seven steps. Each step has a question, an idea, a test and a result. Select a box to go to the step.</p>` | Text of the page: a paragraph: seven steps, each with a question, an idea, a test and a result. |
| 442 | `<div class="flow">{''.join(flow)}</div>` | Text of the page: the row of overview boxes. The braces join the pieces of `flow` from lines 354 to 358. |
| 443 | `<p class="note">Blue line: the idea of the step held. Orange line: the idea of the step was rejected.</p>` | Text of the page: a note on the two line colours of the boxes: blue for an idea that held, orange for an idea that was rejected. |
| 444 | `{''.join(STEPS)}` | Text of the page: the seven step boxes. The braces join the entries of `STEPS`. |
| 446 | `<h2 id="open">4. What is still open</h2>` | Text of the page: the heading of section 4, what is still open. |
| 447 | `<ul>` | Text of the page: opens a list. |
| 448 | `<li><b>The exact rule inside the core.</b> Insufficient data. Hypothesis: the core lowers its limit of outstanding requests, or its prefetcher asks for less, for a stream in address order. The manual of an older core type (Neoverse V2) documents such controls. Three things can resolve it. First: read two control registers of the core on CRB. This needs a kernel module or firmware access. The approval for this task did not cover either. Second: read the prefetch section of the manual of this core type (Neoverse V3AE). Third: ask Arm, with the data of steps 5 and 6.</li>` | Text of the page: list item: the exact rule inside the core, with a hypothesis and three ways to resolve it. |
| 449 | `<li><b>The write total with writers on both meshes.</b> Write falls from 455 GB/s on one mesh to 120 to 129 GB/s at 64+56. This is the same for old and new loops. Insufficient data on the cause.</li>` | Text of the page: list item: the write total with writers on both meshes. |
| 450 | `<li><b>The 3 to 4 % by which old write stays above new write with a common stop.</b> Insufficient data on the cause.</li>` | Text of the page: list item: the small amount by which old write stays above new write with a common stop. |
| 451 | `</ul>` | Text of the page: closes the list. |
| 453 | `<h2 id="limits">5. Limits of the data</h2>` | Text of the page: the heading of section 5, the limits of the data. |
| 454 | `<ul>` | Text of the page: opens a list. |
| 455 | `<li>One machine. All new runs are from one evening: 2026-11-15, 16:56 to 21:03 UTC. Figure 1 is the original run of 2026-11-13. The write comparison under two stop rules (step 1) uses earlier runs with 64 processes.</li>` | Text of the page: list item: one machine, and all new runs are from one evening. |
| 456 | `<li>System load: the 1-minute load average was 0.00 to 71.24 at the start of the scripts, and up to 109.60 at a process launch (101 launches). The high values follow the scripts' own earlier 120-thread processes (hypothesis, not checked further). At every launch 1 task was runnable and 0 users were logged in {ref(14)}.</li>` | Text of the page: list item: the system load at the start of the scripts and at the process launches (reference 14). |
| 457 | `<li>Steps 4 and 7 have one interval per measured case.</li>` | Text of the page: list item: steps 4 and 7 have one interval per measured case. |
| 458 | `<li>Step 7 tested one scrambled order. The window depth of the scrambled loops was assumed equal to the address-order loops. It was not measured.</li>` | Text of the page: list item: step 7 tested one scrambled order, and the window depth of the scrambled loops was assumed, not measured. |
| 459 | `<li>Lines in flight (step 6) are estimates: lines per second of a thread times the time of one probe request.</li>` | Text of the page: list item: the lines in flight of step 6 are estimates. |
| 460 | `<li>The benchmark source <code>bench/bandwidth.c</code> was not changed. The new loop variants are in two copies of the test program {ref(13)}.</li>` | Text of the page: list item: the benchmark source `bench/bandwidth.c` was not changed (reference 13). |
| 461 | `</ul>` | Text of the page: closes the list. |
| 463 | `<h2 id="refs">References</h2>` | Text of the page: the heading of the references. |
| 464 | `<ol class="refs">{refs}</ol>` | Text of the page: the reference list. The braces put in the text `refs` of line 360. |
| 465 | `</main>` | Text of the page: closes the main block. |
| 466 | `</body>` | Text of the page: closes the body. |
| 467 | `</html>` | Text of the page: closes the document. |
| 468 | `"""` | Ends the text `page`. |
| 469 | `    open(OUT, "w").write(page)` | Writes the page to the file `OUT`. The mode `"w"` replaces a file that is already there. |
| 470 | `    print("wrote", OUT, len(page), "bytes")` | Prints `wrote`, the path of the file and the length of the page text. The message calls the unit bytes. `len` counts characters, which is the same number as long as every character is plain ASCII. |
| 473 | `build()` | Calls `build`. This line stands outside every function, so the page is written each time the file runs. |
