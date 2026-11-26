# `report.py` explained, line by line

- Source file: `asct-2026-11-16/report.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 381 lines, 24664 bytes).
- sha256 of the source when this page was built: `0dc2cad194be4d891be61950180572a60858e8d265fb3b1745c54a2ac44b98dc`.

## Short version: purpose

`report.py` builds the report page of the ASCT cross-check, `ASCT-cross-check.html`. It reads the numbers (`facts.json`), the older values (`baseline.json`) and the text blocks (`notes.json`), formats the numbers into ten tables, takes the ten figures from `figs.py` and puts everything into one HTML page with a style sheet and a small script for tooltips. It computes no result: every number of the tables 1 to 8 is copied from an input file and only rounded.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Facts file, `facts.json`**: the output of `facts.py`. It holds the numbers that `facts.py` derived for the report: medians, ranges and counts per cell, and the verdicts.
- **Baseline file, `baseline.json`**: the output of `baseline.py`. It holds the older values of our own loops and the vendor runs.
- **Notes file, `notes.json`**: the output of `notes.py` and `dyn_notes.py`. It holds the text blocks, the figure captions and the references of the page.
- **Text block**: one named entry of the notes file. It is a list of paragraphs and bullet lists that are HTML already.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **R-A3, P-A5**: a rule and a prediction of the decisions file. `facts.py` computes their verdicts.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Old read loop, new read loop**: the names of the report for the old read kernel and the new read kernel. The report takes the values of the new read loop from `asmread`, where they exist.
- **ASCT loop**: the read loop of the ASCT benchmark binary.
- **`read_nop96`, `read_nop128`**: two loops of our own benchmark of 2026-11-15, load-only loops with 96 and with 128 `nop` instructions.
- **Process**: one start of a benchmark binary.
- **Cell**: all processes with the same settings. The facts file gives for each cell the median, the smallest and the largest value (the range) and the count `n`.
- **Median**: the middle value of a sorted list of values.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate that the ASCT binary prints for a whole process. It is the sum of the rates of its threads.
- **Lower bound of a total**: all bytes of a process divided by the time of its slowest thread. The facts file holds it as `floor`.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Line**: one cache line of 64 bytes.
- **Count per line**: a counter value divided by the lines that the thread passed in its measured phase.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part C, part NC**: two parts of the one-core runs. C: counters. NC: injected NOPs with counters.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Event set**: a named list of counter events that one process counts together.
- **L1, L2**: the two private caches of a core.
- **L2 refill**: one line that enters L2 from outside. The counter is `l2d_cache_refill`.
- **Long miss, long-latency miss**: by the word list of the report, a load that had to wait for its line.
- **Prefetcher**: the part of a core that requests lines before the program asks for them.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh counter**: a hardware counter of the mesh, the network on the chip that links the cores, the SLC and the memory ports. Reading it needs root.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Home node, gateway**: two parts of the mesh. A home node receives the memory requests of the cores. The gateway links the two meshes.
- **Flit**: one transfer unit on a link or a port of the mesh.
- **Busy level**: a value from 0 to 3 that a response message of the mesh carries. A higher value says that the sender is more busy.
- **64+56**: 64 threads on mesh 0 plus 56 threads on mesh 1, which is one thread on each of the CPUs 0 to 119.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Tag**: the name of one process of the mesh-counter runs.
- **Vendor runs, A0 and A1**: two complete ASCT runs that the chip vendor made on its own machines. The report calls the machines Arm reference machine A0 and A1.
- **Interval**: one timed measurement inside a process.
- **CSS**: the language of the style sheet of a web page. It sets the look of the elements.
- **Tooltip**: a small text box that the page shows when the pointer rests on a mark or when the mark has the keyboard focus.
- **Hit area**: an invisible shape over a chart mark. It carries the tooltip text in its attribute `data-tip`.
- **Folding block**: a block of the page that shows one line until the reader opens it.

## Main flow

1. Read the facts file, the baseline file and the notes file from the arguments 1 to 3 (lines 12 to 14).
2. Define the style sheet and the tooltip script as two texts (lines 17 to 65).
3. Define the table functions. Each one formats numbers of the facts file, and for some columns of the baseline file or the notes file, into one HTML table (lines 82 to 328).
4. Build the page from top to bottom: the main heading, the short version, the folded word list, then the sections 1 to 7 and the references. Each line adds a heading, text blocks of the notes file, figures of `figs.py` and tables (lines 344 to 375).
5. Wrap the pieces into one HTML page, write it to the file of argument 4 and print its size (lines 377 to 381).

## Behavior a reader must know

- The script computes no result. The only arithmetic is rounding, the sum of the two meshes for a mesh counter (line 230, lines 254 to 260) and the smallest and the largest total of the counted processes (line 190).
- Where a number of a table comes from: tables 1 to 8 read the facts file. Table 1 also reads the vendor sweep, table 6 the older layout totals and table 8 the vendor table, all from the baseline file. Table 4 also reads `peer_counters` of the notes file.
- A value that is missing gives an empty cell. A missing cell or tag never stops the script, but a missing key that a line reads without a test does, for example a caption of the notes file in line 349.
- Tables 9 and 10 need mesh counters. With the notes file of `dyn_notes.py` both functions return the paragraph `Insufficient data` in place of the table (line 216, line 266).
- Table 1 calls every value a median of the processes (line 85). For the old and the new read loop the facts file holds a median of row medians from the baseline file, and the range in the cell tooltip is a range of percentiles. At 1 GiB on CPU 2 the value of these two loops is a median of timed intervals of the first run. The columns `A0` and `A1` hold one value of the vendor sweep per size.
- The three rates in the header of table 9 are fixed numbers of line 223, not values of an input file.
- The description text names a script `check_notes.py`. This folder holds no such file (line 5).
- The imports of five colors in line 10, the function `bullets` and the style classes `key` and `v` are not used.
- The page is light theme only. It needs no other file: the style sheet, the script and all pictures are inside the page.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/report.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (381 lines, 24664 bytes, sha256 `0dc2cad194be4d891be61950180572a60858e8d265fb3b1745c54a2ac44b98dc`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text, modules and the three input files (lines 1 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""report.py FACTS.json BASELINE.json NOTES.json OUT.html: build ASCT-cross-check.html.` | Starts the description text of the file. Usage: four arguments, the facts file, the baseline file, the notes file and the output page. The script builds the report page `ASCT-cross-check.html`. |
| 3 | `FACTS comes from facts.py, BASELINE from baseline.py. NOTES holds the text blocks that a person (or the agent)` | Description, continued: the facts file comes from `facts.py` and the baseline file from `baseline.py`. The notes file holds the text blocks of the page. The text says that a person or the agent writes them. |
| 4 | `writes after reading the facts: short version, takeaways, verdict sentences, run notes. Every number in a` | Description, continued: the text blocks are written after reading the facts. They are the short version, the main points, the verdict sentences and the notes on the runs. |
| 5 | `NOTES text is checked by check_notes.py against FACTS before the page is delivered."""` | Description, last line: it says that a script `check_notes.py` checks every number of a notes text against the facts before the page is delivered. This folder holds no file with that name. In this folder the script `notes.py` writes the notes file and fills in the numbers from the facts file. |
| 6 | `import json` | Loads the module `json`, which reads and writes JSON files. |
| 7 | `import sys` | Loads the module `sys`, which gives the arguments of the script. |
| 9 | `import figs` | Loads the file `figs.py` of the same folder, which draws the figures. |
| 10 | `from svgchart import ASCT, CONTEXT, INK2, NEW, OLD, esc` | Takes five colors and the function `esc` from `svgchart.py`. `esc` makes a text safe for HTML. The script does not use the five colors. |
| 12 | `F = json.load(open(sys.argv[1]))` | `F`: the content of the facts file of argument 1 (`facts.json`). It holds the numbers that `facts.py` derived for the report. |
| 13 | `B = json.load(open(sys.argv[2]))` | `B`: the content of the baseline file of argument 2 (`baseline.json`). It holds the older values of our own loops and the vendor runs. |
| 14 | `N = json.load(open(sys.argv[3]))` | `N`: the content of the notes file of argument 3 (`notes.json`). It holds the text blocks, the captions and the references. |
| 15 | `MI = 1 << 20` | `MI`: 1 MiB in bytes. |

### `CSS`: the style sheet of the page (lines 17 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `CSS = '''` | Starts the text `CSS`, the style sheet of the page. Each line of it gives the look of one kind of element. |
| 18 | `:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7}` | CSS: the colors of the page as named values: the page background, the surface of boxes, two ink colors, a muted grey, the grid color and the axis color. All are light-theme colors. |
| 19 | `*{box-sizing:border-box}` | CSS: the width of every element includes its padding and its border. |
| 20 | `body{margin:0;background:var(--page);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}` | CSS: the page body has no outer margin, the page background, the ink color and a system font of 15 px with a line height of 1.55. |
| 21 | `main{max-width:1000px;margin:0 auto;padding:28px 16px 80px}` | CSS: the main column is at most 1000 px wide and centered, with padding around it. |
| 22 | `h1{font-size:26px;line-height:1.25;margin:0 0 6px}` | CSS: the main heading has 26 px. |
| 23 | `h2{font-size:20px;margin:44px 0 10px;padding-top:14px;border-top:1px solid var(--grid)}` | CSS: a section heading has 20 px, 44 px of space above it and a thin line above it. |
| 24 | `h3{font-size:16px;margin:26px 0 8px}` | CSS: a sub heading has 16 px. |
| 25 | `p{margin:8px 0}` | CSS: a paragraph has 8 px of space above and below it. |
| 26 | `ul{margin:8px 0;padding-left:22px}` | CSS: a bullet list has 8 px of space above and below it and an indent of 22 px. |
| 27 | `li{margin:4px 0}` | CSS: a list item has 4 px of space above and below it. |
| 28 | `.sub{color:var(--ink2);margin:0 0 18px}` | CSS: the class `sub`, used for the subtitle: the second ink color and 18 px of space below it. |
| 29 | `.short{background:var(--surface);border:1px solid var(--grid);border-left:4px solid var(--ink2);border-radius:6px;padding:12px 16px;margin:16px 0}` | CSS: the class `short`, the box of the short version: a surface background, a thin border, a thick left border of 4 px, rounded corners and padding. |
| 30 | `.short h2{border:0;margin:0 0 6px;padding:0;font-size:16px}` | CSS: the heading inside that box has no line above it and 16 px. |
| 31 | `figure{margin:18px 0;background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:12px 12px 10px;overflow-x:auto}` | CSS: a figure is a box with a surface background, a thin border, rounded corners and padding. It gets a horizontal scroll bar when its content is wider than the box. |
| 32 | `figure svg{min-width:720px;display:block}` | CSS: a picture inside a figure is at least 720 px wide. |
| 33 | `figcaption{color:var(--ink2);font-size:13.5px;margin-top:8px}` | CSS: a figure caption has the second ink color, 13.5 px and 8 px of space above it. |
| 34 | `figcaption b{color:var(--ink)}` | CSS: bold text inside a caption has the main ink color. |
| 35 | `.tw{overflow-x:auto;margin:12px 0}` | CSS: the class `tw`, the wrapper of a table: a horizontal scroll bar when the table is wider than the column, and 12 px of space above and below it. |
| 36 | `table{border-collapse:collapse;font-size:13px;background:var(--surface);min-width:100%}` | CSS: a table has merged cell borders, 13 px text and a surface background, and it is at least as wide as the column. |
| 37 | `th,td{border:1px solid var(--grid);padding:4px 8px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}` | CSS: a table cell has a thin border, padding, right-aligned text, digits of equal width and no line break. |
| 38 | `th{background:#f1f0ec;color:var(--ink2);font-weight:600;white-space:normal}` | CSS: a header cell has a light background, the second ink color and bold text. Its text may break into lines. |
| 39 | `td.l,th.l{text-align:left;white-space:normal}` | CSS: a cell with the class `l` is left-aligned, and its text may break into lines. |
| 40 | `td.s,th.s{text-align:left}` | CSS: a cell with the class `s` is left-aligned. |
| 41 | `td.hl{background:#f3f1e6}` | CSS: a data cell with the class `hl` has a light tinted background. The tables use it to mark values at 8 MiB. |
| 42 | `caption{caption-side:top;text-align:left;color:var(--ink2);font-size:13px;padding:0 0 6px}` | CSS: a table caption stands above the table, left-aligned, in the second ink color with 13 px. |
| 43 | `details{background:var(--surface);border:1px solid var(--grid);border-radius:6px;padding:8px 14px;margin:12px 0}` | CSS: a folding block is a box with a surface background, a thin border, rounded corners and padding. |
| 44 | `summary{cursor:pointer;font-weight:600}` | CSS: the visible line of a folding block is bold and shows a pointer cursor. |
| 45 | `code,pre{font-family:ui-monospace,"DejaVu Sans Mono",Menlo,monospace;font-size:12.5px}` | CSS: code and code blocks use a font with characters of equal width and 12.5 px. |
| 46 | `pre{background:var(--surface);border:1px solid var(--grid);border-radius:6px;padding:10px 12px;overflow-x:auto;line-height:1.4}` | CSS: a code block is a box with a surface background, a thin border, rounded corners, padding and a horizontal scroll bar when needed. |
| 47 | `.key{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline}` | CSS: the class `key`, a round color dot of 10 px. No text of the scripts of this folder uses this class. |
| 48 | `.v{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12.5px;font-weight:600;border:1px solid var(--axis);background:var(--surface)}` | CSS: the class `v`, a small bold label with a border. No text of the scripts of this folder uses this class. |
| 49 | `.hit{cursor:default;outline:none}` | CSS: the class `hit`, the invisible hit areas of the charts: the standard cursor and no focus outline of the browser. |
| 50 | `.hit:focus{stroke:var(--ink2);stroke-width:1.5}` | CSS: a hit area that has the keyboard focus gets an outline of 1.5 px in the second ink color. |
| 51 | `#tip{position:fixed;display:none;pointer-events:none;background:#0b0b0b;color:#fff;font-size:12.5px;line-height:1.35;padding:6px 9px;border-radius:5px;max-width:340px;z-index:9}` | CSS: the element with the id `tip`, the tooltip box. It has a fixed place in the window and is hidden at first. It does not catch the pointer. It has a black background, white text of 12.5 px and a width of at most 340 px, and it lies above the other content. |
| 52 | `ol.refs{font-size:13.5px;padding-left:0;list-style:none}` | CSS: the reference list has 13.5 px, no indent and no numbers of its own. |
| 53 | `ol.refs li{margin:5px 0}` | CSS: an item of the reference list has 5 px of space above and below it. |
| 54 | `'''` | Ends the text `CSS`. |

### `JS`: the script of the page for the tooltips (lines 56 to 67)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `JS = '''` | Starts the text `JS`, the script that the page runs in the browser. It shows the tooltip of a chart mark. |
| 57 | `(function(){var t=document.getElementById('tip');` | JavaScript: starts a function that runs once when the page has loaded this script. `t` is the tooltip box, the element with the id `tip`. |
| 58 | `function show(e,el){t.textContent=el.getAttribute('data-tip');t.style.display='block';` | JavaScript: starts the function `show`. It copies the text of the attribute `data-tip` of the element `el` into the tooltip box and makes the box visible. |
| 59 | ` var x=(e.clientX\|\|el.getBoundingClientRect().left)+14,y=(e.clientY\|\|el.getBoundingClientRect().top)+14;` | JavaScript: `x`, `y`: the place of the box, 14 px right of and below the pointer. When the event has no pointer position, as for a keyboard focus, the top left corner of the element is used. |
| 60 | ` if(x+t.offsetWidth>innerWidth-8)x=innerWidth-t.offsetWidth-8;if(y+t.offsetHeight>innerHeight-8)y=y-t.offsetHeight-28;` | JavaScript: keeps the box inside the window. When it would pass the right edge, it is moved left. When it would pass the bottom edge, it is placed above the pointer. |
| 61 | ` t.style.left=x+'px';t.style.top=y+'px';}` | JavaScript: sets the place of the box and ends the function `show`. |
| 62 | `document.querySelectorAll('.hit').forEach(function(el){` | JavaScript: starts a loop over all elements with the class `hit`, which are the hit areas that `svgchart.py` writes. |
| 63 | ` el.addEventListener('pointermove',function(e){show(e,el)});el.addEventListener('pointerleave',function(){t.style.display='none'});` | JavaScript: the box is shown when the pointer moves over the hit area, and hidden when the pointer leaves it. |
| 64 | ` el.addEventListener('focus',function(e){show(e,el)});el.addEventListener('blur',function(){t.style.display='none'});});})();` | JavaScript: the box is shown when the hit area gets the keyboard focus, and hidden when it loses it. The line also ends the loop and the outer function and calls that function. |
| 65 | `'''` | Ends the text `JS`. |

### Helpers `lab`, `cell` and `rng` (lines 68 to 81)

| Line | Source | Explanation |
|---:|---|---|
| 68 | `def lab(b):` | Starts the function `lab`. It returns the label text of a size in bytes, such as `8 MiB`. |
| 69 | `    return F['labels'][str(b)]` | Takes the text from the dictionary `labels` of the facts file. |
| 72 | `def cell(v, nd=1):` | Starts the function `cell`. It formats a number for a table cell with `nd` decimals. The default is 1 decimal. |
| 73 | `    return '' if v is None else f'{v:.{nd}f}'` | Returns an empty text for `None`, and the number with a fixed count of decimals otherwise. |
| 76 | `def rng(d, nd=1):` | Starts the function `rng`. It returns one table cell for an entry that holds a median, a range and a count. |
| 77 | `    if not d:` | For a missing entry |
| 78 | `        return '<td></td>'` | it returns an empty cell. |
| 79 | `    return f'<td title="range {d["lo"]:.2f} to {d["hi"]:.2f}, n={d["n"]}">{d["median"]:.{nd}f}</td>'` | Returns a cell that shows the median with `nd` decimals. Its `title` attribute holds the range with 2 decimals and the count `n`. A browser shows that text when the pointer rests on the cell. |

### `table_sizes`: table 1, the read rate of one core per buffer size (lines 82 to 100)

| Line | Source | Explanation |
|---:|---|---|
| 82 | `def table_sizes():` | Starts the function `table_sizes`. It returns table 1 of the report. |
| 83 | `    v0 = dict(B['vendor']['a0_numa2_ddr_7200']['sweep'])` | `v0`: the one-core sweep of the vendor run A0 from the baseline file, as a dictionary from the size in bytes to the rate in GB/s. |
| 84 | `    v1 = dict(B['vendor']['a1_numa2_ddr_8000']['sweep'])` | `v1`: the same for the vendor run A1. |
| 85 | `    h = ('<div class="tw"><table><caption>Table 1. Read rate of one core, GB/s (GB = 10<sup>9</sup> bytes). Median of the processes. '` | Starts the table. Text of the page: the caption of table 1. It says that the values are read rates of one core in GB/s with GB = 1e9 bytes, and medians of the processes. The second claim holds for the ASCT columns of CRB only. For the old and the new read loop the cell shows the value of `baseline.json`. The script `baseline.py` builds it as the median of the fields `median` of the rows of `final8.json`, block `size_curve`. So it is a median of medians. At 1 GiB on CPU 2 it is the median of the timed intervals of the first run of 2026-11-13. The columns `A0` and `A1` show one value of the vendor sweep per size. The text goes on in lines 86 to 88. |
| 86 | `         'Point at a cell to see the range and the count. Empty cell: no run exists.</caption>'` | Text of the page, caption continued: the reader can point at a cell to see the range and the count, and an empty cell means that no run exists. For the old and the new read loop that range is not a range of processes. For the values that come from `final8.json` it reaches from the smallest field `p5` to the largest field `p95` of the rows. By their names these fields are the 5th and the 95th percentile. The cells of `A0` and `A1` have no such text. |
| 87 | `         '<tr><th class="s" rowspan="2">Buffer size</th><th colspan="3">CRB, CPU 2</th><th colspan="3">CRB, CPU 41</th><th colspan="2">ASCT read, Arm reference machines</th></tr>'` | Text of the page: the first header row. It holds `Buffer size`, three columns for CPU 2 of CRB, three for CPU 41 and two for the ASCT loop on the Arm reference machines. |
| 88 | `         '<tr><th>old read</th><th>new read</th><th>ASCT read</th><th>old read</th><th>new read</th><th>ASCT read</th><th>A0</th><th>A1</th></tr>')` | Text of the page: the second header row. For each CPU it names the old read loop, the new read loop and the ASCT loop. The last two columns are `A0` and `A1`. |
| 89 | `    for b in F['sizes']:` | Starts a loop over the 16 sizes. Each gives one table row. |
| 90 | `        hl = ' hl' if b == 8 * MI else ''` | `hl`: the mark for the highlight. Only the row of 8 MiB gets it. |
| 91 | `        row = f'<tr><td class="s{hl}">{lab(b)}</td>'` | `row`: starts the row with the label of the size. |
| 92 | `        for cpu in F['cpus']:` | Starts a loop over the two CPUs. |
| 93 | `            c = F['one'][str(cpu)]` | `c`: the values of this CPU from the facts file. |
| 94 | `            new = c['new'].get(str(b)) or c['newc'].get(str(b))` | `new`: the entry of the new read loop. It is the assembly form `asmread`, or the C form when the assembly form has no value at this size. |
| 95 | `            row += rng(c['old'].get(str(b))) + rng(new) + rng(c['asct'].get(str(b)))` | Adds three cells with `rng`: the old read loop, the new read loop and the ASCT loop. Each shows the median of its entry. For the two older loops the facts file takes the median and the range from the baseline file. |
| 96 | `        row += f'<td>{cell(v0.get(b))}</td><td>{cell(v1.get(b))}</td></tr>'` | Adds the two vendor cells: the rate of the sweep at exactly this size with 1 decimal, or an empty cell when the sweep has no such size. |
| 97 | `        h += row` | Adds the row to the table. |
| 98 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `CNT_COLS` and `table_counters`: tables 2a and 2b, all core counters per size (lines 101 to 121)

| Line | Source | Explanation |
|---:|---|---|
| 101 | `CNT_COLS = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l1d_cache_refill', 'L1 refills'), ('l2d_cache_refill', 'L2 refills'),` | `CNT_COLS`: the columns of table 2 as pairs of a counter name and a column title. This line holds the cycles, the instructions, the L1 refills and the L2 refills. |
| 102 | `            ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'), ('ll_cache_miss_rd', 'last-level misses'),` | Continues line 101: the long misses of L1 and of L2 and the last-level misses. |
| 103 | `            ('l1d_cache_hwprf', 'L1 hw prefetch'), ('l2d_cache_hwprf', 'L2 hw prefetch'), ('l2d_cache_l1hwprf', 'L2 access by L1 pf'),` | Continues line 101: the hardware prefetches of L1 and of L2 and the L2 accesses by the L1 prefetcher. |
| 104 | `            ('l2d_cache_refill_l1hwprf', 'L2 refill by L1 pf'), ('bus_access_rd', 'bus reads'), ('l2d_cache_wb', 'L2 write-backs'),` | Continues line 101: the L2 refills by the L1 prefetcher, the bus reads and the L2 write-backs. |
| 105 | `            ('stall_backend_mem', 'stall cycles, memory'), ('dtlb_walk', 'page-table walks')]` | Continues line 101: the stall cycles for memory and the page-table walks. The list has 15 columns. |
| 108 | `def table_counters(cpu):` | Starts the function `table_counters`. It returns the counter table of one CPU. |
| 109 | `    c = F['one'][str(cpu)]['cnt']` | `c`: the counter medians per size of this CPU, from `cnt` of the facts file. |
| 110 | `    cols = [(n, t) for n, t in CNT_COLS if any(n in c.get(str(b), {}) for b in F['sizes'])]` | `cols`: the columns of `CNT_COLS` whose counter has a value at one size or more. |
| 111 | `    h = (f'<div class="tw"><table><caption>Table 2{"a" if cpu == 2 else "b"}. ASCT read loop on CPU {cpu}: core counters per 64-byte line of the measured phase, '` | Starts the table. Text of the page: the caption. The table is `Table 2a` for CPU 2 and `Table 2b` for any other CPU. It holds core counters of the ASCT loop per 64-byte line of the measured phase. The text goes on in line 112. |
| 112 | `         'user mode. Median of the counted processes.</caption><tr><th class="s">Buffer size</th><th>rate, GB/s</th>' + ''.join(f'<th>{esc(t)}</th>' for _, t in cols) + '</tr>')` | Text of the page, caption continued: the counts are in user mode and are medians of the counted processes. Then the header row: `Buffer size`, `rate, GB/s` and one cell per column title. |
| 113 | `    for b in F['sizes']:` | Starts a loop over the 16 sizes. |
| 114 | `        k = c.get(str(b))` | `k`: the counter medians of this size. |
| 115 | `        if not k:` | A size without counters |
| 116 | `            continue` | gets no row. |
| 117 | `        hl = ' hl' if b == 8 * MI else ''` | `hl`: the mark for the highlight of the 8 MiB row. |
| 118 | `        h += f'<tr><td class="s{hl}">{lab(b)}</td><td>{k["_rate"]:.1f}</td>' + ''.join(f'<td>{cell(k.get(n), 3)}</td>' for n, _ in cols) + '</tr>'` | Adds the row: the label of the size, the median rate `_rate` of the counted processes with 1 decimal, and each counter per line with 3 decimals. A missing counter gives an empty cell. |
| 119 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `table_prefetch_rule`: table 3, rule R-A3 (lines 122 to 137)

| Line | Source | Explanation |
|---:|---|---|
| 122 | `def table_prefetch_rule():` | Starts the function `table_prefetch_rule`. It returns table 3 of the report. |
| 123 | `    names = F.get('RA3_counted', [])` | `names`: the prefetch counters that rule R-A3 could judge on both CPUs, from `RA3_counted` of the facts file. |
| 124 | `    h = ('<div class="tw"><table><caption>Table 3. Rule R-A3: prefetch counters per line at 6, 8 and 12 MiB. "Different" means that the 8 MiB value lies '` | Starts the table. Text of the page: the caption of table 3. It names rule R-A3 and the prefetch counters per line at 6, 8 and 12 MiB. The text goes on in line 125. |
| 125 | `         'outside the range of the two neighbours, extended by 10 % of their mean.</caption>'` | Text of the page, caption continued: `Different` means that the value at 8 MiB lies outside the range of the two neighbours, after the range was extended by 10 % of their mean. |
| 126 | `         '<tr><th class="l" rowspan="2">Counter</th><th colspan="4">CPU 2</th><th colspan="4">CPU 41</th><th rowspan="2">Different on both CPUs</th></tr>'` | Text of the page: the first header row. It holds `Counter`, four columns for CPU 2, four for CPU 41 and `Different on both CPUs`. |
| 127 | `         '<tr><th>6 MiB</th><th>8 MiB</th><th>12 MiB</th><th>different</th><th>6 MiB</th><th>8 MiB</th><th>12 MiB</th><th>different</th></tr>')` | Text of the page: the second header row. For each CPU it holds `6 MiB`, `8 MiB`, `12 MiB` and `different`. |
| 128 | `    for n in names:` | Starts a loop over the counters. |
| 129 | `        row = f'<tr><td class="l"><code>{n}</code></td>'` | `row`: starts the row with the counter name. |
| 130 | `        for cpu in F['cpus']:` | Starts a loop over the two CPUs. |
| 131 | `            p = F['one'][str(cpu)]['prefetch'][n]` | `p`: the result of the rule for this counter and CPU, from `prefetch` of the facts file. |
| 132 | `            row += f'<td>{p["v6"]:.3f}</td><td class="hl">{p["v8"]:.3f}</td><td>{p["v12"]:.3f}</td><td>{"yes" if p["different"] else "no"}</td>'` | Adds four cells: the values at 6, 8 and 12 MiB with 3 decimals, and `yes` or `no` for the verdict `different` of this CPU. The 8 MiB cell is highlighted. |
| 133 | `        row += f'<td>{"yes" if n in F["RA3_different"] else "no"}</td></tr>'` | Adds the last cell: `yes` when the counter is in `RA3_different`, the list of the counters that are different on both CPUs, and `no` otherwise. |
| 134 | `        h += row` | Adds the row to the table. |
| 135 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `table_nops` and `table_layouts`: tables 5 and 6, the whole chip (lines 138 to 164)

| Line | Source | Explanation |
|---:|---|---|
| 138 | `def table_nops():` | Starts the function `table_nops`. It returns table 5 of the report. |
| 139 | `    ch = F['chip']` | `ch`: the results for the whole chip from the facts file. |
| 140 | `    h = ('<div class="tw"><table><caption>Table 5. ASCT read loop at 64+56 threads, 256 MiB per thread: total read rate against injected NOPs, GB/s. '` | Starts the table. Text of the page: the caption of table 5. The ASCT loop runs at 64+56 threads with 256 MiB per thread, and the table gives the total read rate against the injected NOPs in GB/s. The text goes on in lines 141 to 144. |
| 141 | `         'Total and sums: what ASCT prints, median of the processes. Lower bound: all bytes of a process divided by the time of its slowest thread. '` | Text of the page, caption continued: the total and the sums are what ASCT prints, as the median of the processes. The lower bound is all bytes of a process divided by the time of its slowest thread. The sums per mesh are not a line of the ASCT output. The script `analyze.py` adds up the thread rates of each mesh. |
| 142 | `         'Thread: median thread of the mesh. Time: shortest and longest measured phase of a thread, seconds.</caption>'` | Text of the page, caption continued: `Thread` is the median thread of the mesh. `Time` is the shortest and the longest measured phase of a thread in seconds. |
| 143 | `         '<tr><th>Injected NOPs</th><th>processes</th><th>total</th><th>range of the total</th><th>lower bound</th><th>mesh 0 sum</th><th>mesh 1 sum</th>'` | Text of the page: the header cells for the injected NOPs, the number of processes, the total, the range of the total, the lower bound and the sums of mesh 0 and mesh 1. |
| 144 | `         '<th>thread, mesh 0</th><th>thread, mesh 1</th><th>time of a thread, s</th></tr>')` | Text of the page: the header cells for the thread of mesh 0, the thread of mesh 1 and the time of a thread. |
| 145 | `    for n in sorted(ch['nops'], key=int):` | Starts a loop over the counts of injected NOPs in rising order. The keys are text, so `key=int` sorts them as numbers. |
| 146 | `        v = ch['nops'][n]` | `v`: the cell of this count. |
| 147 | `        h += (f'<tr><td>{n}</td><td>{v["n"]}</td><td>{v["median"]:.1f}</td><td>{v["lo"]:.1f} to {v["hi"]:.1f}</td><td>{v["floor"]:.1f}</td><td>{v["mesh0"]:.1f}</td><td>{v["mesh1"]:.1f}</td>'` | Adds the row: the count, the number of processes `n`, the median total, the smallest and the largest total, the median lower bound `floor` and the median sums of mesh 0 and mesh 1, all in GB/s with 1 decimal. The text goes on in line 148. |
| 148 | `              f'<td>{v["thr0"][1]:.2f}</td><td>{v["thr1"][1]:.2f}</td><td>{v["sec"][0]:.2f} to {v["sec"][1]:.2f}</td></tr>')` | Continues line 147: the median thread rate of mesh 0 and of mesh 1 with 2 decimals, and the shortest and the longest measured time of a thread in seconds. |
| 149 | `    return h + '</table></div>'` | Returns the table and closes it. |
| 152 | `def table_layouts():` | Starts the function `table_layouts`. It returns table 6 of the report. |
| 153 | `    ch = F['chip']` | `ch`: the results for the whole chip. |
| 154 | `    names = {'6400': ('64+0', '64+0'), '0056': ('0+56', '0+56'), '5656': ('56+56', '56+56')}` | `names`: for each layout of the facts file its display name and its key in the baseline file: `64+0`, `0+56` and `56+56`. |
| 155 | `    h = ('<div class="tw"><table><caption>Table 6. Other thread layouts, 256 MiB per thread, total GB/s. ASCT columns: median (range, count of processes). The four right columns are the single intervals of 2026-11-15.</caption>'` | Starts the table. Text of the page: the caption of table 6. It holds other thread layouts with 256 MiB per thread, as totals in GB/s. The ASCT columns give the median, the range and the count of processes. The four right columns are single intervals of 2026-11-15. |
| 156 | `         '<tr><th class="l">Layout</th><th>ASCT, 0 NOPs</th><th>ASCT, 20 NOPs</th><th>old read</th><th>new read</th><th>read_nop96</th><th>read_nop128</th></tr>')` | Text of the page: the header row with the layout, the ASCT loop with 0 and with 20 injected NOPs, and the four older loops: old read, new read, `read_nop96` and `read_nop128`. |
| 157 | `    for lay, (nm, key) in names.items():` | Starts a loop over the three layouts. |
| 158 | `        a, b = ch['layouts'][lay].get('0'), ch['layouts'][lay].get('20')` | `a`, `b`: the ASCT cells of the layout with 0 and with 20 injected NOPs. |
| 159 | `        o = B['chip']['layouts'][key]` | `o`: the four older totals of the layout from the baseline file, block `chip`, list `layouts`. |
| 160 | `        h += (f'<tr><td class="l">{nm}</td>' + ''.join(f'<td>{x["median"]:.1f} ({x["lo"]:.1f} to {x["hi"]:.1f}, n={x["n"]})</td>' if x else '<td></td>' for x in (a, b))` | Adds the row: the layout name, then for each ASCT cell the median, the range and the count `n`, or an empty cell. The text goes on in line 161. |
| 161 | `              + ''.join(f'<td>{x:.1f}</td>' for x in o) + '</tr>')` | Continues line 160: the four older totals with 1 decimal. |
| 162 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `CHIP_CNT` and `table_chip_counters`: table 7, core counters with all threads (lines 165 to 204)

| Line | Source | Explanation |
|---:|---|---|
| 165 | `CHIP_CNT = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l2d_cache_refill', 'L2 refills'), ('l1d_cache_refill', 'L1 refills'),` | `CHIP_CNT`: the rows of table 7 as pairs of a counter name and a row title. This line holds the cycles, the instructions, the L2 refills and the L1 refills. |
| 166 | `            ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'), ('ll_cache_miss_rd', 'last-level misses'),` | Continues line 165: the long misses of L1 and of L2 and the last-level misses. |
| 167 | `            ('l2d_cache_hwprf', 'L2 hardware prefetch events'), ('l1d_cache_hwprf', 'L1 hardware prefetch events'),` | Continues line 165: the hardware prefetch events of L2 and of L1. |
| 168 | `            ('l2d_cache_l1hwprf', 'L2 accesses caused by the L1 prefetcher'), ('l2d_cache_refill_l1hwprf', 'L2 refills caused by the L1 prefetcher'),` | Continues line 165: the L2 accesses and the L2 refills that the L1 prefetcher caused. |
| 169 | `            ('bus_access', 'bus accesses'), ('bus_access_rd', 'bus reads'), ('l2d_cache_wb', 'L2 write-backs'),` | Continues line 165: the bus accesses, the bus reads and the L2 write-backs. |
| 170 | `            ('l2_chi_cbusy0', 'responses with busy level 0'), ('l2_chi_cbusy1', 'responses with busy level 1'),` | Continues line 165: the responses with busy level 0 and with busy level 1. |
| 171 | `            ('l2_chi_cbusy2', 'responses with busy level 2'), ('l2_chi_cbusy3', 'responses with busy level 3'), ('l2_chi_cbusy_mt', 'busy, multi-threaded flag'),` | Continues line 165: the responses with busy level 2 and 3, and a counter with the title `busy, multi-threaded flag`. |
| 172 | `            ('stall_backend_mem', 'stall cycles, memory'), ('stall_backend_l2d', 'stall cycles, L2'), ('stall_backend_l1d', 'stall cycles, L1'),` | Continues line 165: the stall cycles for memory, for L2 and for L1. |
| 173 | `            ('stall_backend_membound', 'stall cycles, memory bound'), ('dtlb_walk', 'page-table walks'), ('l1d_cache_prfm', 'software prefetches')]` | Continues line 165: the stall cycles with the title `memory bound`, the page-table walks and the software prefetches. The list has 25 rows. |
| 176 | `def table_chip_counters():` | Starts the function `table_chip_counters`. It returns table 7 of the report. |
| 177 | `    cnt = F['chip'].get('cnt', {})` | `cnt`: the counted many-core cases from the facts file. |
| 178 | `    keys = [k for k in ('6456.n0', '6456.n20', '6400.n0') if k in cnt]` | `keys`: the cases that exist, out of 64+56 with 0 injected NOPs, 64+56 with 20 and 64+0 with 0. |
| 179 | `    if not keys:` | Without any case |
| 180 | `        return '<p>Insufficient data: no counted whole-chip run exists.</p>'` | the function returns a paragraph in place of the table. It says `Insufficient data` and that no counted whole-chip run exists. |
| 181 | `    names = {'6456.n0': '64+56, 0 NOPs', '6456.n20': '64+56, 20 NOPs', '6400.n0': '64+0, 0 NOPs'}` | `names`: the display name of each case. |
| 182 | `    h = ('<div class="tw"><table><caption>Table 7. ASCT read loop, whole chip: core counters per 64-byte line, median over the threads of a mesh '` | Starts the table. Text of the page: the caption of table 7. It holds core counters of the ASCT loop per 64-byte line for the whole chip, as the median over the threads of a mesh. The text goes on in line 183. |
| 183 | `         '(user mode, measured phase). The first row gives the total rate of the counted processes.</caption><tr><th class="l" rowspan="2">Counter (name on CRB)</th>')` | Text of the page, caption continued: the counts are in user mode and for the measured phase, and the first row gives the total rate of the counted processes. Then the first header cell, `Counter (name on CRB)`. |
| 184 | `    for k in keys:` | Starts a loop over the cases, for the first header row. |
| 185 | `        h += f'<th colspan="{1 if k == "6400.n0" else 2}">{names[k]}</th>'` | Adds the header cell of the case. It spans two columns, or one column for 64+0, which has threads on mesh 0 only. |
| 186 | `    h += '</tr><tr>' + ''.join('<th>mesh 0</th>' + ('' if k == '6400.n0' else '<th>mesh 1</th>') for k in keys) + '</tr>'` | Adds the second header row: `mesh 0` for every case and `mesh 1` for every case except 64+0. |
| 187 | `    h += '<tr><td class="l">total rate of the counted processes, GB/s</td>'` | Starts the first data row with the label `total rate of the counted processes, GB/s`. |
| 188 | `    for k in keys:` | Starts a loop over the cases. |
| 189 | `        t = cnt[k]['totals'].values()` | `t`: the totals that ASCT printed for the counted processes of the case, one per event set. |
| 190 | `        h += f'<td colspan="{1 if k == "6400.n0" else 2}" style="text-align:center">{min(t):.0f} to {max(t):.0f}</td>'` | Adds one centered cell with the smallest and the largest of these totals, without decimals. |
| 191 | `    h += '</tr>'` | Ends the first data row. |
| 192 | `    for n, title in CHIP_CNT:` | Starts a loop over the rows of `CHIP_CNT`. |
| 193 | `        if not any(n in cnt[k]['ev'] for k in keys):` | A counter that no case holds |
| 194 | `            continue` | gets no row. |
| 195 | `        row = f'<tr><td class="l">{esc(title)} (<code>{n}</code>)</td>'` | `row`: starts the row with the title and the counter name. |
| 196 | `        for k in keys:` | Starts a loop over the cases. |
| 197 | `            e = cnt[k]['ev'].get(n)` | `e`: the values of the counter in this case, or `None`. |
| 198 | `            row += f'<td>{cell(e["mesh0"] if e else None, 3)}</td>'` | Adds the value of mesh 0 with 3 decimals. By `facts.py` it is the median over the event sets of the median over the threads of mesh 0. |
| 199 | `            if k != '6400.n0':` | For every case except 64+0 |
| 200 | `                row += f'<td>{cell(e["mesh1"] if e else None, 3)}</td>'` | adds the value of mesh 1 in the same way. |
| 201 | `        h += row + '</tr>'` | Adds the row to the table. |
| 202 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `MESH_ROWS` and `table_mesh_chip`: table 9, mesh counters with all threads (lines 205 to 237)

| Line | Source | Explanation |
|---:|---|---|
| 205 | `MESH_ROWS = [('hns_pocq_retry_all', 'home-node request retries'), ('hns_qos_pocq_occupancy_all', 'home-node queue occupancy'),` | `MESH_ROWS`: the rows of table 9 as pairs of a mesh event and a row title. This line holds the titles `home-node request retries` and `home-node queue occupancy`. |
| 206 | `             ('hns_mc_retries_local_all', 'memory-controller retries'), ('ccra_chidat_stalls', 'gateway data stalls'),` | Continues line 205: the titles `memory-controller retries` and `gateway data stalls`. |
| 207 | `             ('hns_cbusy11_all', 'home-node busy level 3'), ('mxp_e_req_txflit_stall', 'request-link stalls, east'),` | Continues line 205: the titles `home-node busy level 3` and `request-link stalls, east`. |
| 208 | `             ('mxp_e_dat_txflit_stall', 'data-link stalls, east'), ('mxp_n_dat_txflit_stall', 'data-link stalls, north'),` | Continues line 205: the titles `data-link stalls, east` and `data-link stalls, north`. |
| 209 | `             ('mxp_s_dat_txflit_stall', 'data-link stalls, south'), ('hns_mc_reqs_local_all', 'memory-controller requests'),` | Continues line 205: the titles `data-link stalls, south` and `memory-controller requests`. |
| 210 | `             ('hns_cache_miss_all', 'SLC misses'), ('hns_pocq_reqs_recvd_all', 'home-node requests received')]` | Continues line 205: the titles `SLC misses` and `home-node requests received`. The list has 12 rows. |
| 213 | `def table_mesh_chip():` | Starts the function `table_mesh_chip`. It returns table 9 of the report, or a paragraph when there is no data. |
| 214 | `    tags = [t for t in N.get('mesh_chip_tags', []) if t in F['mesh']]` | `tags`: the tags that the notes file lists under `mesh_chip_tags` and that the facts file holds under `mesh`. |
| 215 | `    if not tags:` | Without such a tag |
| 216 | `        return '<p><b>Insufficient data.</b> ' + esc(N.get('mesh_chip_missing', 'No mesh-counter run of the whole chip exists.')) + '</p>'` | the function returns a paragraph that starts with `Insufficient data.` and holds the text `mesh_chip_missing` of the notes file. The script `dyn_notes.py` of this folder sets `mesh_chip_tags` to an empty list. So with its notes file this is always the result. |
| 217 | `    peer = B['chip']['mesh_per_line']` | `peer`: the mesh counter values per line of the loops of 2026-11-15, from the baseline file. |
| 218 | `    h = ('<div class="tw"><table><caption>Table 9. Mesh counters per 64-byte line read, sum of both meshes, system-wide (root). '` | Starts the table. Text of the page: the caption of table 9. It holds mesh counters per 64-byte line read, as the sum of both meshes, counted for the whole system as root. The text goes on in line 219. |
| 219 | `         'ASCT columns: this work. Right columns: the loops of 2026-11-15 (run w120-RC1).</caption><tr><th class="l">Counter</th>')` | Text of the page, caption continued: the ASCT columns are this work, and the right columns are the loops of 2026-11-15 from the run `w120-RC1`. Then the first header cell, `Counter`. |
| 220 | `    for t in tags:` | Starts a loop over the tags. |
| 221 | `        m = F['mesh'][t]` | `m`: the values of the tag. |
| 222 | `        h += f'<th>ASCT, {esc(N["mesh_tag_names"].get(t, t))}<br>{m["rate"]:.0f} GB/s</th>'` | Adds a header cell with the display name of the tag and its rate in GB/s without decimals. |
| 223 | `    h += '<th>new read<br>299 GB/s</th><th>read_nop96<br>470 GB/s</th><th>old read<br>468 GB/s</th></tr>'` | Adds three fixed header cells for the older loops: new read with 299 GB/s, `read_nop96` with 470 GB/s and old read with 468 GB/s. These three rates are numbers that the line holds. |
| 224 | `    for n, title in MESH_ROWS:` | Starts a loop over the rows of `MESH_ROWS`. |
| 225 | `        if not any(n in F['mesh'][t]['ev'] for t in tags) and n not in peer:` | An event that no tag holds and that the older values do not hold |
| 226 | `            continue` | gets no row. |
| 227 | `        row = f'<tr><td class="l">{esc(title)} (<code>{n}</code>)</td>'` | `row`: starts the row with the title and the event name. |
| 228 | `        for t in tags:` | Starts a loop over the tags. |
| 229 | `            e = F['mesh'][t]['ev'].get(n)` | `e`: the values of the event for this tag. |
| 230 | `            v = (e.get('mesh0', 0) + e.get('mesh1', 0)) if e and ('mesh0' in e or 'mesh1' in e) else None` | `v`: the count per line of mesh 0 plus that of mesh 1. A missing mesh counts as 0. It is `None` when the event has no value per line at all. |
| 231 | `            row += f'<td>{cell(v, 4)}</td>'` | Adds the value with 4 decimals. |
| 232 | `        p = peer.get(n)` | `p`: the three older values of the event. |
| 233 | `        row += ''.join(f'<td>{x:.4g}</td>' for x in p) if p else '<td></td><td></td><td></td>'` | Adds them with 4 significant digits, or three empty cells. |
| 234 | `        h += row + '</tr>'` | Adds the row to the table. |
| 235 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `SINGLE_MESH`, `mesh_val` and `table_mesh_single`: table 10, mesh counters with one core (lines 238 to 288)

| Line | Source | Explanation |
|---:|---|---|
| 238 | `SINGLE_MESH = [('hns_slc_sf_cache_access_all', 'SLC lookups'), ('hns_cache_miss_all', 'SLC misses'), ('hns_cache_fill_all', 'SLC fills'),` | `SINGLE_MESH`: the rows of table 10 as pairs of a mesh event and a row title. This line holds the titles `SLC lookups`, `SLC misses` and `SLC fills`. |
| 239 | `               ('hns_sf_hit_all', 'snoop-filter hits'), ('hns_pocq_reqs_recvd_all', 'home-node requests received'), ('hns_pocq_retry_all', 'home-node request retries'),` | Continues line 238: the titles `snoop-filter hits`, `home-node requests received` and `home-node request retries`. |
| 240 | `               ('hns_mc_reqs_local_all', 'memory-controller requests'), ('hns_slc_eviction_all_all', 'SLC evictions'), ('hns_seq_hit', 'sequential-stream hits'),` | Continues line 238: the titles `memory-controller requests`, `SLC evictions` and `sequential-stream hits`. |
| 241 | `               ('hns_cbusy00_all', 'busy level 0'), ('hns_cbusy01_all', 'busy level 1'), ('hns_cbusy10_all', 'busy level 2'), ('hns_cbusy11_all', 'busy level 3'),` | Continues line 238: the titles `busy level 0` to `busy level 3`, for the four events `hns_cbusy00_all` to `hns_cbusy11_all`. |
| 242 | `               ('hns_txdat_stall', 'home-node data stalls'), ('mxp_p0_dat_txflit_valid', 'data flits delivered at device port 0'),` | Continues line 238: the titles `home-node data stalls` and `data flits delivered at device port 0`. |
| 243 | `               ('mxp_p1_dat_txflit_valid', 'data flits delivered at device port 1'), ('_dat_links', 'data flits forwarded on mesh links (east + west + north + south)'),` | Continues line 238: the title `data flits delivered at device port 1`, and the special name `_dat_links`. Its title says that it stands for the data flits that are forwarded on the mesh links to the east, west, north and south. |
| 244 | `               ('_req_links', 'request flits forwarded on mesh links (east + west + north + south)')]` | Continues line 238: the special name `_req_links` for the request flits that are forwarded on the same four links. The list has 18 rows. |
| 247 | `def mesh_val(tag, name):` | Starts the function `mesh_val`. It returns two values of one row for one tag: the count per line and the events per second, each as the sum of both meshes. |
| 248 | `    ev = F['mesh'][tag]['ev']` | `ev`: the events of the tag from the facts file. |
| 249 | `    if name in ('_dat_links', '_req_links'):` | For the two special names: |
| 250 | `        kind = 'dat' if name == '_dat_links' else 'req'` | `kind`: `dat` for the data flits and `req` for the request flits. |
| 251 | `        parts = [ev.get(f'mxp_{d}_{kind}_txflit_valid') for d in 'ewns']` | `parts`: the four events for the links to the east, west, north and south, with names of the form `mxp_e_dat_txflit_valid`. |
| 252 | `        if any(p is None for p in parts):` | When one of the four is missing, |
| 253 | `            return None, None` | the function returns no values. |
| 254 | `        return (sum(p.get('mesh0', 0) + p.get('mesh1', 0) for p in parts) if all('mesh0' in p for p in parts) else None,` | Returns the sum of the counts per line over the four events and both meshes, or `None` when one event has no value per line for mesh 0. The call goes on in line 255. |
| 255 | `                sum(p['mesh0_per_s'] + p['mesh1_per_s'] for p in parts))` | Continues line 254: the second value, the sum of the events per second over the four events and both meshes. |
| 256 | `    e = ev.get(name)` | `e`: the values of a plain event. |
| 257 | `    if not e:` | When the tag does not hold it, |
| 258 | `        return None, None` | the function returns no values. |
| 259 | `    per_line = (e.get('mesh0', 0) + e.get('mesh1', 0)) if ('mesh0' in e or 'mesh1' in e) else None` | `per_line`: the count per line of mesh 0 plus that of mesh 1. It is `None` when the event has no value per line. |
| 260 | `    return per_line, e.get('mesh0_per_s', 0) + e.get('mesh1_per_s', 0)` | Returns the count per line and the sum of the events per second of both meshes. |
| 263 | `def table_mesh_single():` | Starts the function `table_mesh_single`. It returns table 10 of the report, or a paragraph when there is no data. |
| 264 | `    tags = [t for t in N.get('mesh_single_tags', []) if t in F['mesh']]` | `tags`: the tags that the notes file lists under `mesh_single_tags` and that the facts file holds under `mesh`. |
| 265 | `    if not tags:` | Without such a tag |
| 266 | `        return '<p><b>Insufficient data.</b> ' + esc(N.get('mesh_single_missing', 'No mesh-counter run of one core exists.')) + '</p>'` | the function returns a paragraph that starts with `Insufficient data.` and holds the text `mesh_single_missing` of the notes file. The script `dyn_notes.py` of this folder sets `mesh_single_tags` to an empty list. So with its notes file this is always the result. |
| 267 | `    idle = N.get('mesh_idle_tag')` | `idle`: the tag of the idle window, from the notes file. It is `None` when the notes file has no such entry. |
| 268 | `    h = ('<div class="tw"><table><caption>Table 10. Mesh counters while one core runs the ASCT read loop, sum of both meshes, system-wide (root). '` | Starts the table. Text of the page: the caption of table 10. It holds mesh counters while one core runs the ASCT loop, as the sum of both meshes, counted for the whole system as root. The text goes on in line 269. |
| 269 | `         'Values are per 64-byte line read by that core. The idle column is in events per second, because no line is read.</caption><tr><th class="l">Counter</th>')` | Text of the page, caption continued: the values are per 64-byte line that this core read. The idle column is in events per second, for the reason that no line is read then. Then the first header cell, `Counter`. |
| 270 | `    for t in tags:` | Starts a loop over the tags. |
| 271 | `        m = F['mesh'][t]` | `m`: the values of the tag. |
| 272 | `        h += f'<th>{esc(N["mesh_tag_names"].get(t, t))}<br>{m["rate"]:.1f} GB/s</th>'` | Adds a header cell with the display name of the tag and its rate in GB/s with 1 decimal. |
| 273 | `    if idle in F['mesh']:` | When the facts file holds the idle tag, |
| 274 | `        h += '<th>idle,<br>events/s</th>'` | adds the header cell `idle, events/s`. |
| 275 | `    h += '</tr>'` | Ends the header row. |
| 276 | `    for n, title in SINGLE_MESH:` | Starts a loop over the rows of `SINGLE_MESH`. |
| 277 | `        vals = [mesh_val(t, n) for t in tags]` | `vals`: the two values of `mesh_val` for each tag. |
| 278 | `        if all(v[0] is None for v in vals):` | A row without any count per line |
| 279 | `            continue` | is left out. |
| 280 | `        code = '' if n.startswith('_') else f' (<code>{n}</code>)'` | `code`: the event name in parentheses, or nothing for the two special names, which start with an underscore. |
| 281 | `        row = f'<tr><td class="l">{esc(title)}{code}</td>' + ''.join(f'<td>{cell(v[0], 3)}</td>' for v in vals)` | `row`: the row with the title, the event name and the count per line of each tag with 3 decimals. |
| 282 | `        if idle in F['mesh']:` | When the facts file holds the idle tag: |
| 283 | `            iv = mesh_val(idle, n)[1]` | `iv`: the events per second of this row in the idle window. |
| 284 | `            row += f'<td>{"" if iv is None else f"{iv:,.0f}"}</td>'` | Adds that value without decimals and with commas between groups of three digits, or an empty cell. |
| 285 | `        h += row + '</tr>'` | Adds the row to the table. |
| 286 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `PAD_COLS` and `table_pad`: table 4, the ASCT loop with injected NOPs (lines 289 to 315)

| Line | Source | Explanation |
|---:|---|---|
| 289 | `PAD_COLS = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'),` | `PAD_COLS`: the counter columns of table 4 as pairs of a counter name and a column title. This line holds the cycles, the instructions and the long misses of L1 and of L2. |
| 290 | `            ('l1d_cache_hwprf', 'L1 prefetches'), ('l2d_cache_hwprf', 'L2 prefetches'), ('l2d_cache_l1hwprf', 'L2 accesses by the L1 prefetcher'),` | Continues line 289: the prefetches of L1 and of L2 and the L2 accesses by the L1 prefetcher. |
| 291 | `            ('l2d_cache_refill', 'L2 refills'), ('stall_backend_mem', 'stall cycles, memory')]` | Continues line 289: the L2 refills and the stall cycles for memory. The list has 9 columns. |
| 294 | `def table_pad():` | Starts the function `table_pad`. It returns table 4 of the report. |
| 295 | `    """ASCT loop with 0, 1, 2, 4 injected NOPs at 1 MiB and 8 MiB, with the new read loop of 2026-11-15 beside it."""` | Description of the function: the ASCT loop with 0, 1, 2 and 4 injected NOPs at 1 MiB and 8 MiB, with the new read loop of 2026-11-15 beside it. |
| 296 | `    peer = N.get('peer_counters', {})` | `peer`: the counter values of our own loops of 2026-11-15, from `peer_counters` of the notes file. The script `dyn_notes.py` reads them from `final8.json`. |
| 297 | `    h = ('<div class="tw"><table><caption>Table 4. ASCT read loop with injected NOPs on one core: rate and core counters per 64-byte line. '` | Starts the table. Text of the page: the caption of table 4. It holds the rate and the core counters per 64-byte line of the ASCT loop with injected NOPs on one core. The text goes on in lines 298 to 299. |
| 298 | `         'Median of the counted processes. NOPs: injected NOPs. Rows "new read": our loop on 2026-11-15, for the counters that were counted then.</caption>'` | Text of the page, caption continued: the values are medians of the counted processes. The rows `new read` are our loop on 2026-11-15, for the counters that were counted then. |
| 299 | `         '<tr><th class="s">CPU</th><th class="s">Size</th><th class="l">Loop</th><th>rate, GB/s</th>' + ''.join(f'<th>{esc(t)}</th>' for _, t in PAD_COLS) + '</tr>')` | Text of the page: the header row with the CPU, the size, the loop, the rate in GB/s and one cell per column of `PAD_COLS`. |
| 300 | `    for cpu in F['cpus']:` | Starts a loop over the two CPUs. |
| 301 | `        for b, short in ((MI, '1M'), (8 * MI, '8M')):` | Starts a loop over the sizes 1 MiB and 8 MiB, each with its short name `1M` or `8M`. |
| 302 | `            for nn in (0, 1, 2, 4):` | Starts a loop over the counts 0, 1, 2 and 4 of injected NOPs. |
| 303 | `                k = F['one'][str(cpu)]['cnt'].get(str(b)) if nn == 0 else F.get('padcnt', {}).get(f'{cpu}.{nn}.{b}')` | `k`: the counter medians of the cell. For 0 injected NOPs they come from part C (`cnt` of the facts file). For the other counts they come from part NC (`padcnt`). |
| 304 | `                if not k:` | A cell without values |
| 305 | `                    continue` | gets no row. |
| 306 | `                hl = ' class="hl"' if b == 8 * MI and nn in (0, 2) else ''` | `hl`: the highlight of the rate cell. It is set at 8 MiB for 0 and for 2 injected NOPs. These are the two cases that prediction P-A5 compares. |
| 307 | `                h += (f'<tr><td class="s">{cpu}</td><td class="s">{lab(b)}</td><td class="s">ASCT read, {nn} NOPs</td><td{hl}>{k["_rate"]:.1f}</td>'` | Adds the row: the CPU, the label of the size, the loop with its count of injected NOPs and the median rate `_rate` with 1 decimal. The text goes on in line 308. |
| 308 | `                      + ''.join(f'<td>{cell(k.get(n), 4 if n == "l2d_cache_lmiss_rd" else 3)}</td>' for n, _ in PAD_COLS) + '</tr>')` | Continues line 307: one cell per counter of `PAD_COLS`, each a count per line. `l2d_cache_lmiss_rd` has 4 decimals and the others have 3. |
| 309 | `            pk = peer.get(f'new.{short}.{cpu}')` | `pk`: the values of the new read loop for this size and CPU, under the key `new`, short size name and CPU. |
| 310 | `            if pk:` | When they exist: |
| 311 | `                h += (f'<tr><td class="s">{cpu}</td><td class="s">{lab(b)}</td><td class="s">new read, 2026-11-15</td><td>{pk["rate"]:.1f}</td>'` | adds a row with the loop name `new read, 2026-11-15` and its rate with 1 decimal. The text goes on in line 312. |
| 312 | `                      + ''.join(f'<td>{cell(pk.get(n), 4 if n == "l2d_cache_lmiss_rd" else 3)}</td>' for n, _ in PAD_COLS) + '</tr>')` | Continues line 311: one cell per counter. A counter that was not counted on 2026-11-15 gives an empty cell. |
| 313 | `    return h + '</table></div>'` | Returns the table and closes it. |

### `table_mix`: table 8, the traffic types (lines 316 to 330)

| Line | Source | Explanation |
|---:|---|---|
| 316 | `def table_mix():` | Starts the function `table_mix`. It returns table 8 of the report. |
| 317 | `    """ASCT peak-bandwidth traffic types: CRB at 64+56 beside the two vendor runs."""` | Description of the function: the traffic types of the ASCT benchmark `peak-bandwidth`, with CRB at 64+56 beside the two vendor runs. |
| 318 | `    mix = F['chip'].get('mix', {})` | `mix`: the cells of the traffic types 2 to 5 from the facts file. |
| 319 | `    names = [('0', 'All Reads'), ('2', '3:1 Reads-Writes'), ('3', '2:1 Reads-Writes'), ('4', '1:1 Reads-Writes'), ('5', '2:1 Rd-Wr (Non-Temporal)')]` | `names`: the five traffic types as pairs of the value of the option `--bw-write` and the name that ASCT gives: `All Reads` for 0, `3:1 Reads-Writes` for 2, `2:1 Reads-Writes` for 3, `1:1 Reads-Writes` for 4 and `2:1 Rd-Wr (Non-Temporal)` for 5. |
| 320 | `    v0, v1 = B['vendor']['a0_numa2_ddr_7200'], B['vendor']['a1_numa2_ddr_8000']` | `v0`, `v1`: the vendor runs A0 and A1 from the baseline file. |
| 321 | `    h = ('<div class="tw"><table><caption>Table 8. The five traffic types of the ASCT benchmark <code>peak-bandwidth</code>, total GB/s. '` | Starts the table. Text of the page: the caption of table 8. It holds the five traffic types of the ASCT benchmark `peak-bandwidth` as totals in GB/s. The text goes on in lines 322 to 323. |
| 322 | `         'CRB: 64+56 threads, 0 injected NOPs, median (range). A0 and A1: the vendor runs, all CPUs of the machine.</caption>'` | Text of the page, caption continued: the CRB column is for 64+56 threads with 0 injected NOPs, as median and range. The columns A0 and A1 are the vendor runs with all CPUs of the machine. |
| 323 | `         f'<tr><th class="l">Traffic type (ASCT name)</th><th>CRB, 120 threads</th><th>A0, {v0["cpus"]} CPUs</th><th>A1, {v1["cpus"]} CPUs</th></tr>')` | Text of the page: the header row. The headers of the vendor columns hold the number of CPUs of each machine from the baseline file. |
| 324 | `    for t, nm in names:` | Starts a loop over the five traffic types. |
| 325 | `        d = F['chip']['base'] if t == '0' else mix.get(t)` | `d`: the cell of the type. For `All Reads` it is the cell `base`, the read processes at 64+56 with 0 injected NOPs. For the others it comes from `mix`. |
| 326 | `        c = f'{d["median"]:.1f} ({d["lo"]:.1f} to {d["hi"]:.1f}, n={d["n"]})' if d else ''` | `c`: the text of the CRB cell: the median, the smallest and the largest total with 1 decimal and the count `n`. It is empty without a cell. |
| 327 | `        h += f'<tr><td class="l">{esc(nm)}</td><td>{c}</td><td>{v0["peak"][nm][0]:.1f}</td><td>{v1["peak"][nm][0]:.1f}</td></tr>'` | Adds the row: the name of the type, the CRB cell and the bandwidth of each vendor run for this type with 1 decimal. The vendor value is the first number of the entry `peak` of the baseline file. |
| 328 | `    return h + '</table></div>'` | Returns the table and closes it. |

### Helpers `fig`, `bullets` and `block` (lines 331 to 343)

| Line | Source | Explanation |
|---:|---|---|
| 331 | `def fig(svg, caption):` | Starts the function `fig`. It wraps one picture and its caption into a figure of the page. |
| 332 | `    return f'<figure>{svg}<figcaption>{caption}</figcaption></figure>' if svg else ''` | Returns the figure element with the picture and the caption below it. For an empty picture text it returns nothing, so the figure is left out. |
| 335 | `def bullets(items):` | Starts the function `bullets`. It turns a list of texts into a bullet list. No line of this file calls it. |
| 336 | `    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'` | Returns the list element with one item per text. |
| 339 | `def block(key):` | Starts the function `block`. It returns one text block of the notes file. |
| 340 | `    """A NOTES text block: a list of paragraphs or bullet lists, already HTML."""` | Description of the function: a text block of the notes file is a list of paragraphs or bullet lists that are HTML already. |
| 341 | `    return ''.join(N.get(key, []))` | Joins the pieces of the block with the name `key`. A block that the notes file does not hold gives an empty text. |

### The page, section by section (lines 344 to 376)

| Line | Source | Explanation |
|---:|---|---|
| 344 | `parts = []` | `parts`: the pieces of the page in their order. It starts empty. |
| 345 | `parts.append(f'<h1>ASCT cross-check of two open read-throughput questions on CRB</h1><p class="sub">{N["subtitle"]}</p>')` | The main heading, `ASCT cross-check of two open read-throughput questions on CRB`, and below it the subtitle from the entry `subtitle` of the notes file. |
| 346 | `parts.append('<div class="short"><h2>Short version</h2>' + block('short') + '</div>')` | The box `Short version` with the block `short` of the notes file. |
| 347 | `parts.append('<details><summary>Words used here</summary>' + block('words') + '</details>')` | The folding block `Words used here` with the block `words`. It is folded when the page opens. |
| 348 | `parts.append('<h2>1. What was asked, and how ASCT was used</h2>' + block('asked'))` | The heading of section 1, `What was asked, and how ASCT was used`, and the block `asked`. |
| 349 | `parts.append(fig(figs.fig_path(), N['cap_path']))` | Figure 1, drawn by `figs.fig_path`, with the caption `cap_path` of the notes file. |
| 350 | `parts.append(block('how'))` | The block `how`: how ASCT was used. |
| 351 | `parts.append('<h3>The three read loops</h3>' + fig(figs.fig_loops(), N['cap_loops']) + block('loops'))` | The sub heading `The three read loops`, figure 2 (`fig_loops`) with its caption, and the block `loops`. |
| 352 | `parts.append('<h2>2. Question 1: the small gain of the new read loop at 8 MiB</h2>' + block('q1_intro'))` | The heading of section 2, `Question 1: the small gain of the new read loop at 8 MiB`, and the block `q1_intro`. |
| 353 | `parts.append(fig(figs.fig_size(F, B), N['cap_size']))` | Figure 3 (`fig_size`) with the caption `cap_size`. |
| 354 | `parts.append(fig(figs.fig_fall(F, B), N['cap_fall']))` | Figure 4 (`fig_fall`) with the caption `cap_fall`. |
| 355 | `parts.append(block('q1_rates') + table_sizes())` | The block `q1_rates` and table 1. |
| 356 | `parts.append('<h3>Core counters: cost per line</h3>' + block('q1_cost_intro') + fig(figs.fig_cost(F, B), N['cap_cost']) + block('q1_cost'))` | The sub heading `Core counters: cost per line`, the block `q1_cost_intro`, figure 5 (`fig_cost`) and the block `q1_cost`. |
| 357 | `parts.append('<h3>Core counters: the prefetchers</h3>' + block('q1_pf_intro') + fig(figs.fig_prefetch(F), N['cap_prefetch']) + table_prefetch_rule() + block('q1_pf'))` | The sub heading `Core counters: the prefetchers`, the block `q1_pf_intro`, figure 6 (`fig_prefetch`), table 3 and the block `q1_pf`. |
| 358 | `parts.append('<details><summary>Table 2. All core counters per line, by buffer size (CPU 2 and CPU 41)</summary>' + table_counters(2) + table_counters(41) + '</details>')` | A folding block with the title `Table 2. All core counters per line, by buffer size (CPU 2 and CPU 41)`. It holds table 2a for CPU 2 and table 2b for CPU 41. |
| 359 | `parts.append('<h3>The ASCT loop with injected NOPs: a test of the prefetch explanation</h3>' + block('q1_pad_intro') + fig(figs.fig_pad(F), N['cap_pad']) + table_pad() + block('q1_pad'))` | The sub heading `The ASCT loop with injected NOPs: a test of the prefetch explanation`, the block `q1_pad_intro`, figure 7 (`fig_pad`), table 4 and the block `q1_pad`. |
| 360 | `parts.append('<h3>SLC, mesh and distance</h3>' + block('q1_mesh_intro') + table_mesh_single() + block('q1_mesh'))` | The sub heading `SLC, mesh and distance`, the block `q1_mesh_intro`, table 10 or the paragraph that stands in its place, and the block `q1_mesh`. |
| 361 | `parts.append('<h3>Verdict for question 1</h3>' + block('q1_verdict'))` | The sub heading `Verdict for question 1` and the block `q1_verdict`. |
| 362 | `parts.append('<h2>3. Question 2: the low whole-chip read rate</h2>' + block('q2_intro'))` | The heading of section 3, `Question 2: the low whole-chip read rate`, and the block `q2_intro`. |
| 363 | `parts.append(fig(figs.fig_chip(F, B), N['cap_chip']))` | Figure 8 (`fig_chip`) with the caption `cap_chip`. |
| 364 | `parts.append(fig(figs.fig_nops(F, B), N['cap_nops']))` | Figure 9 (`fig_nops`) with the caption `cap_nops`. |
| 365 | `parts.append(block('q2_rates') + table_nops())` | The block `q2_rates` and table 5. |
| 366 | `parts.append(fig(figs.fig_threads(F), N['cap_threads']))` | Figure 10 (`fig_threads`) with the caption `cap_threads`. The figure is left out when `fig_threads` returns an empty text. |
| 367 | `parts.append(table_layouts() + block('q2_layouts'))` | Table 6 and the block `q2_layouts`. |
| 368 | `parts.append('<h3>Core counters at 64+56</h3>' + block('q2_cnt_intro') + table_chip_counters() + block('q2_cnt'))` | The sub heading `Core counters at 64+56`, the block `q2_cnt_intro`, table 7 and the block `q2_cnt`. |
| 369 | `parts.append('<h3>Mesh counters at 64+56</h3>' + block('q2_mesh_intro') + table_mesh_chip() + block('q2_mesh'))` | The sub heading `Mesh counters at 64+56`, the block `q2_mesh_intro`, table 9 or the paragraph that stands in its place, and the block `q2_mesh`. |
| 370 | `parts.append('<h3>Verdict for question 2</h3>' + block('q2_verdict'))` | The sub heading `Verdict for question 2` and the block `q2_verdict`. |
| 371 | `parts.append('<h2>4. What the vendor baseline runs add</h2>' + block('vendor') + table_mix() + block('vendor2'))` | The heading of section 4, `What the vendor baseline runs add`, the block `vendor`, table 8 and the block `vendor2`. |
| 372 | `parts.append('<h2>5. What ASCT can capture, and what was captured</h2>' + block('capture'))` | The heading of section 5, `What ASCT can capture, and what was captured`, and the block `capture`. |
| 373 | `parts.append('<h2>6. Runs, machine load and deviations</h2>' + block('runs'))` | The heading of section 6, `Runs, machine load and deviations`, and the block `runs`. |
| 374 | `parts.append('<h2>7. Open items</h2>' + block('open'))` | The heading of section 7, `Open items`, and the block `open`. |
| 375 | `parts.append('<h2>References</h2><ol class="refs">' + ''.join(f'<li>{r}</li>' for r in N['refs']) + '</ol>')` | The heading `References` and a list with one item per entry of `refs` of the notes file. |

### Writing the page (lines 377 to 381)

| Line | Source | Explanation |
|---:|---|---|
| 377 | `page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'` | `page`: the whole page as one text. It starts with the document type, the language `en`, the character set `utf-8` and a setting that fits the page to the width of a small screen. The text goes on in lines 378 to 379. |
| 378 | `        '<title>ASCT cross-check</title><style>' + CSS + '</style></head><body><main>' + ''.join(parts)` | Continues line 377: the title `ASCT cross-check` of the browser tab, the style sheet `CSS`, and inside the main column all pieces of `parts`. |
| 379 | `        + '</main><div id="tip" role="tooltip"></div><script>' + JS + '</script></body></html>')` | Continues line 377: the empty tooltip box with the id `tip`, the script `JS` and the end of the page. |
| 380 | `open(sys.argv[4], 'w').write(page)` | Writes the page to the file of argument 4. |
| 381 | `print('written', sys.argv[4], len(page), 'bytes')` | Prints the word `written`, the path, the number of characters of the page and the word `bytes`. |
