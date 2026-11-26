# `make_html.round2.py` explained, line by line

- Source file: `cread-2026-11-12/make_html.round2.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 109 lines, 10078 bytes).
- sha256 of the source when this page was built: `ce0915a972fbb1a9bfb8df75a0ceaad7de63278144a136afdb35ae83d2d199e1`.

## Short version: purpose

`make_html.round2.py` builds the result page of the cread test. It reads the rates of the three read kernels from `cread.csv`, draws a bar chart of the best rate per buffer size and kernel, and writes the chart, two tables and fixed text to `cread-result.html`. Only the chart, the two tables and two load values are computed: every other sentence of the page is fixed text in the script.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB. It ran on 2026-11-13 [Ref1].
- **`read`, `asmread`, `cread`**: the names of the three read kernels in `cread.csv`. `read` is C code with 16 running sums (function `k_read`). `asmread` is a hand-written load-only loop (function `k_asmread`). `cread` is a load-only loop in C (function `k_cread`).
- **`run_cread.sh`**: the run script of the cread test. It starts 16 benchmark processes and writes `cread.csv`.
- **`cread.csv`**: the output file of `run_cread.sh`. For each process it holds one header line that starts with `-- round`, and then the lines that the benchmark prints.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process. The script and the generated page call it a repetition.
- **Interval row**: the line of `cread.csv` for one interval. Its fields are the kernel, the thread count, the buffer size in bytes, the repetition, the bytes, the time, the rate (field 7) and three thread rates.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = `2^10` bytes. GiB = `2^30` bytes.
- **Best, median, lowest**: the highest, the middle and the lowest value of the 12 rates of one buffer size and kernel. With 12 values the median is the mean of the two middle values.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Fixed text**: text that is written in the script as it is. The script does not compute it from `cread.csv`.
- **Generated page**: the file `cread-result.html` that this script writes.
- **SVG**: a picture format that is written as text. A browser draws it.
- **CSS**: the language that sets the look of an HTML page.

## Main flow

1. Read `cread.csv`. Keep the load value of each header line. For each interval row of `read`, `asmread` and `cread`, keep the buffer size, the kernel and the rate of field 7 (lines 4 to 11).
2. Group the rates by buffer size and kernel, and stop unless each of the 12 groups holds 12 rates (lines 12 to 15).
3. Build the bar chart: one group of bars per buffer size, one bar per kernel, with the best rate as the length of the bar (lines 16 to 37).
4. Build the legend, the rows of the table of the best, median and lowest rates, and the rows of the table of the two ratios (lines 38 to 44).
5. Put the chart, the tables and two load values into the fixed text of the page (lines 45 to 107).
6. Write `cread-result.html` and print `ok` with the length of the page (lines 108 to 109).

## Behavior a reader must know

- The input and the output are named without a folder (line 5, line 108). So the script must run in the folder that holds `cread.csv`, and it writes `cread-result.html` there. The test data hold a copy of the script beside `cread.csv` [Ref1].
- Where each number comes from: every rate is field 7 (`aggregate_GBps`) of an interval row of `cread.csv`. The buffer size comes from the header line before the row. The script does not use the `best` rows of the benchmark. It takes the maximum itself.
- How the rates are combined: for each buffer size and kernel, the 12 rates of 2 rounds, 2 CPUs and 3 repetitions go into one list (line 14). The two rounds and the two CPUs are not kept apart. The chart shows the maximum of the list. The first table shows the maximum, the median and the minimum. The second table divides the maximum of `cread` by the maximum of `asmread`, and the median by the median.
- The column of loads per cycle is an estimate: the best rate divided by an assumed clock rate of 2.8 GHz and by 16 B (line 43). The script reads no clock rate. The dashed line at 134.4 GB/s uses the same assumed value (line 24).
- Fixed text: the short version, the findings, the limits and the conditions hold numbers and times that are typed into the script (line 57, lines 77 to 80, lines 84 to 88, lines 93 to 98). With another `cread.csv` they would not change.
- The script stops with an error and writes no page when a group does not hold exactly 12 rates (line 15).
- The generated page has its own list of references (lines 102 to 105). They are not the references of this explanation page.

## Source and explanation, line by line

- Text shown: the file `cread-2026-11-12/make_html.round2.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (109 lines, 10078 bytes, sha256 `ce0915a972fbb1a9bfb8df75a0ceaad7de63278144a136afdb35ae83d2d199e1`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Read `cread.csv` and group the rates (lines 1 to 15)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""Build cread-result.html from cread.csv (same folder)."""` | The description of the script: it builds the page `cread-result.html` from the file `cread.csv` of the same folder. |
| 3 | `import re, statistics as st, html` | Imports three modules of the Python standard library: `re` (regular expressions), `statistics` under the short name `st` (for the median) and `html` (for the function `html.escape`). |
| 4 | `rows=[];ctx=None;loads=[]` | Three start values. `rows`: the list of the rates that the script keeps. `ctx`: the fields of the last header line, `None` before the first one. `loads`: the list of the load values of the header lines. |
| 5 | `for l in open('cread.csv'):` | Loop over the lines of `cread.csv`. The file is opened by its name alone. So the script must run in the folder that holds the file. |
| 6 | `    l=l.strip()` | Removes the line end and the spaces at both ends of the line. |
| 7 | `    m=re.match(r'-- round (\d) cpu (\d+) bytes (\S+) load (\S+)',l)` | `re.match` tests whether the line starts with the pattern. The pattern fits the header line that `run_cread.sh` writes before each process: the text `-- round`, the round, `cpu`, the CPU, `bytes`, the size, `load` and the load value. Group 1 holds the round (one digit). Group 2 holds the CPU number (one or more digits). Group 3 holds the buffer size text such as `32K` (the characters up to the next space). Group 4 holds the load average of the last minute (the characters up to the next space). The rest of the header line, the UTC time, is not read. |
| 8 | `    if m: ctx=m.groups(); loads.append(float(ctx[3])); continue` | For a header line: `ctx` keeps the four groups, the load value is added to `loads` as a number, and `continue` goes on with the next line of the file. |
| 9 | `    p=l.split(',')` | For every other line: `p` is the list of the fields of the line, split at each comma. |
| 10 | `    if p[0] in('read','asmread','cread') and p[3]!='best':` | Keeps only the interval rows of the three read kernels. The first field must be `read`, `asmread` or `cread`, and the fourth field (the repetition) must not be `best`. This drops the two header lines that the benchmark prints per process and its `best` rows. |
| 11 | `        rows.append((ctx[2],p[0],float(p[6])))` | Adds one entry to `rows`: the buffer size text of the last header line (`ctx[2]`), the kernel name, and the rate as a number. The rate is field 7 of the row, the column `aggregate_GBps`, in GB/s. `run_cread.sh` starts each process with 1 thread, so this is the rate of that thread. |
| 12 | `SIZES=[('32K','32 KiB','fits L1'),('1M','1 MiB','fits L2'),('8M','8 MiB','fits the SLC'),('1G','1 GiB','DRAM')]` | `SIZES`: the four buffer sizes. Each entry holds the size text of `cread.csv`, the label for the page and a note on where a buffer of this size fits: the L1 cache, the L2 cache, the SLC, or only memory (DRAM). The notes are fixed text of the script. |
| 13 | `K=[('asmread','asm loop (k_asmread)','#2a78d6'),('cread','C loop, loads only (k_cread)','#eb6834'),('read','C loop with 16 sums (k_read)','#1baf7a')]` | `K`: the three kernels in the order of the chart: `asmread`, `cread`, `read`. Each entry holds the kernel name of `cread.csv`, the label for the page and the color of its bar. |
| 14 | `S={(b,k):[r[2] for r in rows if r[0]==b and r[1]==k] for b,_,_ in SIZES for k,_,_ in K}` | `S`: a dictionary with one entry per buffer size and kernel, 12 entries in all. The key is the pair of size and kernel. The value is the list of the rates of all entries of `rows` with this size and this kernel. The rates of both rounds and of both CPUs go into the same list. |
| 15 | `assert all(len(v)==12 for v in S.values())` | Stops the script with an error unless every one of the 12 lists holds exactly 12 rates. 12 is 2 rounds times 2 CPUs times 3 repetitions, the count that one run of `run_cread.sh` gives. No page is written in that case. |

### Build the bar chart (lines 16 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 16 | `W=760;L=150;R=70;PW=W-L-R;XMAX=140;bh=14;gap=4;gh=3*(bh+gap)+22` | The sizes of the chart, in the units of the drawing. `W`: the width, 760. `L`: the left margin, 150. `R`: the right margin, 70. `PW`: the width of the plot area, 540. `XMAX`: the rate at the right end of the axis, 140 GB/s. `bh`: the height of one bar, 14. `gap`: the space between two bars, 4. `gh`: the height of one group of three bars, 76. |
| 17 | `H=40+len(SIZES)*gh+46` | `H`: the height of the drawing: 40 at the top, 4 groups of 76, and 46 at the bottom. This gives 390. |
| 18 | `x=lambda v:L+v/XMAX*PW` | `x`: a small function that turns a rate in GB/s into a horizontal position. 0 GB/s gives the left edge of the plot area (150), and 140 GB/s gives its right edge (690). |
| 19 | `o=[f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Read rate of three loops at four buffer sizes">']` | `o`: the list of the text lines of the chart. The chart is an SVG drawing, a picture format that is written as text. The first entry opens the drawing with its size and with a label for screen readers. |
| 20 | `for t in range(0,141,20):` | Loop over the axis values 0, 20, 40 and so on up to 140 GB/s. |
| 21 | `    o.append(f'<line x1="{x(t):.1f}" y1="30" x2="{x(t):.1f}" y2="{H-44}" stroke="#e6e5e0" stroke-width="1"/>')` | Adds a thin vertical grid line at this axis value. |
| 22 | `    o.append(f'<text x="{x(t):.1f}" y="{H-28}" text-anchor="middle" class="ax">{t}</text>')` | Adds the number of this axis value below the plot area. |
| 23 | `o.append(f'<text x="{L+PW/2}" y="{H-8}" text-anchor="middle" class="ax">read rate, GB/s (best of 12 repetitions), one thread</text>')` | Adds the title of the axis: `read rate, GB/s (best of 12 repetitions), one thread`. |
| 24 | `lim=134.4` | `lim`: 134.4 GB/s. This is the rate of 3 loads of 16 B per cycle at a clock rate of 2.8 GHz: 3 times 16 B times 2.8e9 per second. The 2.8 GHz is an assumed value. The script reads no clock rate. |
| 25 | `o.append(f'<line x1="{x(lim):.1f}" y1="22" x2="{x(lim):.1f}" y2="{H-44}" stroke="#52514e" stroke-width="1" stroke-dasharray="4 3"/>')` | Adds a dashed vertical line at 134.4 GB/s. |
| 26 | `o.append(f'<text x="{x(lim)-4:.1f}" y="18" text-anchor="end" class="ax">3 loads of 16 B per cycle = 134.4 GB/s (est., assuming 2.8 GHz)</text>')` | Adds the label of the dashed line. The label marks the value as an estimate that assumes 2.8 GHz. |
| 27 | `y=40` | `y`: the vertical position of the top of the first group of bars. |
| 28 | `for b,name,lvl in SIZES:` | Loop over the four buffer sizes. Each size gives one group of three bars. |
| 29 | `    o.append(f'<text x="{L-10}" y="{y+bh+gap+4}" text-anchor="end" class="lab">{name}</text>')` | Adds the label of the group at the left: the size, for example `32 KiB`. |
| 30 | `    o.append(f'<text x="{L-10}" y="{y+bh+gap+20}" text-anchor="end" class="ax">{lvl}</text>')` | Adds the note of the group below the label, for example `fits L1`. |
| 31 | `    for i,(k,kn,c) in enumerate(K):` | Loop over the three kernels. `i` is 0, 1 or 2 and sets the place of the bar in the group. |
| 32 | `        v=max(S[b,k]);yy=y+i*(bh+gap)` | `v`: the highest of the 12 rates of this size and kernel. The page calls it the best rate. `yy`: the vertical position of this bar. |
| 33 | `        o.append(f'<path d="M{L},{yy} H{x(v)-4:.1f} a4,4 0 0 1 4,4 v{bh-8} a4,4 0 0 1 -4,4 H{L} Z" fill="{c}"><title>{html.escape(kn)}, {name}: best {v:.2f} GB/s, median {st.median(S[b,k]):.2f}, lowest {min(S[b,k]):.2f}</title></path>')` | Adds the bar: a filled shape in the color of the kernel, from the left edge of the plot area to the position of `v`, with rounded corners at its right end. The `title` element inside it is a text that a browser shows when the mouse pointer is over the bar: the kernel label, the size, and the best, the median and the lowest rate with 2 decimals. `html.escape` replaces the characters of the label that have a meaning in HTML. |
| 34 | `        o.append(f'<text x="{x(v)+6:.1f}" y="{yy+bh-3}" class="val">{v:.1f}</text>')` | Adds the best rate as a number with 1 decimal at the right of the bar. |
| 35 | `    y+=gh` | Moves `y` down by the height of one group. |
| 36 | `o.append(f'<line x1="{L}" y1="30" x2="{L}" y2="{H-44}" stroke="#52514e" stroke-width="1"/></svg>')` | Adds the vertical axis line at the left edge of the plot area and closes the drawing. |
| 37 | `svg='\n'.join(o)` | `svg`: the whole chart as one text, with a line break between the entries of `o`. |

### Build the legend and the rows of the two tables (lines 38 to 44)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `legend=''.join(f'<span class="lg"><i style="background:{c}"></i>{html.escape(kn)}</span>' for _,kn,c in K)` | `legend`: the legend of the chart as HTML text. For each kernel it holds a small square in the color of the kernel and the label. |
| 39 | `tr=''` | `tr`: the rows of the first table as HTML text. It starts empty. |
| 40 | `for b,name,lvl in SIZES:` | Loop over the four buffer sizes. |
| 41 | `    for k,kn,_ in K:` | Loop over the three kernels. |
| 42 | `        v=S[b,k];mx=max(v)` | `v`: the 12 rates of this size and kernel. `mx`: the highest of them. |
| 43 | `        tr+=f'<tr><td>{name}</td><td>{html.escape(kn)}</td><td>{mx:.2f}</td><td>{st.median(v):.2f}</td><td>{min(v):.2f}</td><td>{mx/2.8/16:.2f}</td></tr>\n'` | Adds one table row with 6 cells: the size, the kernel label, the best rate (`mx`), the median and the lowest rate, each in GB/s with 2 decimals, and `mx/2.8/16`. That last value is the best rate in loads of 16 B per cycle: GB/s divided by 2.8 GHz gives bytes per cycle, and the division by 16 gives loads. It is an estimate: the 2.8 GHz is assumed. |
| 44 | `ratio=''.join(f'<tr><td>{name}</td><td>{max(S[b,"cread"])/max(S[b,"asmread"]):.4f}</td><td>{st.median(S[b,"cread"])/st.median(S[b,"asmread"]):.4f}</td></tr>' for b,name,_ in SIZES)` | `ratio`: the rows of the second table as HTML text, one row per buffer size. Each row holds the size, the best rate of `cread` divided by the best rate of `asmread`, and the median of `cread` divided by the median of `asmread`. Both ratios have 4 decimals. |

### The page text: head and CSS rules (lines 45 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 45 | `page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` | Starts `page`, the text of the whole HTML page, as one format string that ends in line 107. Python puts a value in the place of each name in single braces, such as `{legend}`. Double braces give one brace in the output, which the CSS lines need. This line holds the start of the HTML head: the document type, the language, the character set and the setting for small screens. |
| 46 | `<title>C loop that only loads, measured on CRB</title>` | Text of the page: the title that the browser shows for the page. |
| 47 | `<style>` | Text of the page: starts the block of CSS rules. CSS is the language that sets the look of an HTML page. |
| 48 | `:root{{color-scheme:light}}` | CSS: the page uses a light color scheme. |
| 49 | `body{{background:#fcfcfb;color:#0b0b0b;font:16px/1.5 system-ui,"IBM Plex Sans",sans-serif;max-width:820px;margin:24px auto;padding:0 16px}}` | CSS: the body has a near-white background, near-black text, a font size of 16 px and a width of at most 820 px. It is centered in the window. |
| 50 | `h1{{font-size:24px}} h2{{font-size:18px;margin-top:28px}}` | CSS: the font sizes of the two heading levels, 24 px and 18 px. |
| 51 | `.ax{{font-size:11px;fill:#52514e}} .lab{{font-size:13px;fill:#0b0b0b;font-weight:600}} .val{{font-size:12px;fill:#0b0b0b}}` | CSS: three kinds of text in the chart: axis text (11 px, gray), group labels (13 px, bold) and value labels (12 px). |
| 52 | `.lg{{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e}} .lg i{{width:12px;height:12px;border-radius:3px;margin-right:6px;display:inline-block}}` | CSS: the entries of the legend and their color squares of 12 px. |
| 53 | `table{{border-collapse:collapse;font-size:14px;margin:8px 0}} td,th{{border-bottom:1px solid #e6e5e0;padding:4px 10px;text-align:right}} td:nth-child(-n+2),th:nth-child(-n+2){{text-align:left}}` | CSS: the tables. A cell has a bottom border of 1 px and right-aligned text. The first two columns are left-aligned. |
| 54 | `.take{{background:#f1f0ec;padding:10px 14px;border-radius:6px}} code{{font-size:14px}} .tw{{overflow-x:auto}}` | CSS: the gray boxes of the class `take`, the font size of code text, and a wrapper that lets a wide table scroll sideways. |
| 55 | `</style></head><body>` | Text of the page: ends the CSS block and the head, and starts the body. |

### The page text: short version, word list, chart and tables (lines 56 to 74)

| Line | Source | Explanation |
|---:|---|---|
| 56 | `<h1>C loop that only loads, measured on CRB</h1>` | Text of the page: the main heading. |
| 57 | `<p class="take"><b>Short version.</b> A read loop written in C that only loads (<code>k_cread</code>) reads at nearly the same rate as the hand-written asm loop (<code>k_asmread</code>) at all four buffer sizes. The best rates differ by less than 0.7 %. The old C loop with 16 sums (<code>k_read</code>) reaches about half of that rate at 32 KiB.</p>` | Text of the page: the box with the short version. It is fixed text: its statements and its number are typed into the script and are not computed from `cread.csv`. |
| 58 | `<h2>Words used here</h2>` | Text of the page: the heading of the word list. |
| 59 | `<ul>` | Text of the page: starts the word list. |
| 60 | `<li><b>CRB</b>: the Arm Phoenix Reference Server, 128 cores, where all runs were made.</li>` | Text of the page: the entry for CRB. |
| 61 | `<li><b>k_asmread</b>: the read loop written by hand in assembly. One pass runs 8 <code>ldp q</code> instructions (16 loads of 16 B, 256 B), one add, one compare and one branch.</li>` | Text of the page: the entry for `k_asmread`, with the instructions of one loop pass. |
| 62 | `<li><b>k_cread</b>: the new loop in C. It loads 16 values of 16 B and names them in an empty asm statement. In the measured binary gcc 14.2 compiles one pass to 11 instructions of the same kinds and counts as k_asmread [Ref2].</li>` | Text of the page: the entry for `k_cread`. It is fixed text, and it cites the second reference of the generated page. |
| 63 | `<li><b>k_read</b>: the old loop in C. It adds every 8 B word into one of 16 sums. One pass of 128 B runs 4 <code>ldp q</code> and 8 vector adds [Ref2].</li>` | Text of the page: the entry for `k_read`. It is fixed text. |
| 64 | `<li><b>SLC</b>: system level cache, the cache that all cores share. Linux lists it as L3.</li>` | Text of the page: the entry for SLC, the system level cache. |
| 65 | `<li><b>GB</b>: 10<sup>9</sup> bytes. <b>KiB, MiB, GiB</b>: 2<sup>10</sup>, 2<sup>20</sup>, 2<sup>30</sup> bytes.</li>` | Text of the page: the entry for the units GB, KiB, MiB and GiB. |
| 66 | `</ul>` | Text of the page: ends the word list. |
| 67 | `<h2>Result</h2>` | Text of the page: the heading of the result section. |
| 68 | `<div>{legend}</div>` | Text of the page: the legend. Python puts the text of `legend` here (line 38). |
| 69 | `{svg}` | The chart. Python puts the text of `svg` here (line 37). |
| 70 | `<p class="take">The blue bar and the orange bar have nearly the same length in every group (the rates differ by less than 0.7 %). The green bar (the loop with sums) is shorter in every group.</p>` | Text of the page: a box below the chart that says how to read the three bars. It is fixed text with a fixed number. |
| 71 | `<div class="tw"><table><tr><th>Buffer</th><th>Loop</th><th>Best, GB/s</th><th>Median, GB/s</th><th>Lowest, GB/s</th><th>Loads of 16 B per cycle (est., from the best rate, assuming 2.8 GHz)</th></tr>` | Text of the page: starts the first table and gives its 6 column heads: the buffer, the loop, the best, the median and the lowest rate in GB/s, and the loads of 16 B per cycle. The last head marks its values as an estimate that assumes 2.8 GHz. |
| 72 | `{tr}</table></div>` | The rows of the first table. Python puts the text of `tr` here (lines 39 to 43). Then the table ends. |
| 73 | `<p>Each row has 12 repetitions: 2 CPUs (0 and 2), 2 rounds, 3 repetitions of at least 0.5 s [Ref1].</p>` | Text of the page: a note that each table row has 12 repetitions: 2 CPUs, 2 rounds and 3 repetitions of at least 0.5 s. It is fixed text. |
| 74 | `<div class="tw"><table><tr><th>Buffer</th><th>k_cread / k_asmread, best</th><th>k_cread / k_asmread, median</th></tr>{ratio}</table></div>` | Text of the page: the second table. Its head names the two ratios of `k_cread` to `k_asmread`. Python puts the rows of `ratio` here (line 44). |

### The page text: findings, limits and conditions (lines 75 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 75 | `<h2>What the data shows</h2>` | Text of the page: the heading of the findings. |
| 76 | `<ul>` | Text of the page: starts the list of the findings. |
| 77 | `<li><b>At 32 KiB the best rates of both loops that only load are 133.2 to 133.3 GB/s, which is 2.97 loads of 16 B per cycle (est., assuming 2.8 GHz).</b> This run measured neither the clock nor cycles. The best rate of the loop with sums is 66.76 GB/s, which is 1.49 (est., assuming 2.8 GHz) [Ref1].</li>` | Text of the page: finding 1, about the best rates at 32 KiB. It is fixed text: the rates in it are typed into the script. |
| 78 | `<li><b>At 1 MiB and 8 MiB the rates of the two loops that only load are still nearly equal (they differ by less than 0.2 %).</b> The loop with sums stays at about 67 GB/s at 32 KiB, 1 MiB and 8 MiB [Ref1]. So up to 8 MiB its rate does not depend on the buffer size.</li>` | Text of the page: finding 2, about the rates at 1 MiB and 8 MiB. It is fixed text. |
| 79 | `<li><b>At 1 GiB the best rate of the loop with sums (28.73 GB/s) is 7.1 % below the best rate of k_cread (30.93 GB/s) and 6.5 % below that of k_asmread (30.74 GB/s)</b> [Ref1].</li>` | Text of the page: finding 3, about the rates at 1 GiB. It is fixed text. |
| 80 | `<li><b>At 32 KiB this run gives rates close to those of the report.</b> The report gives 132.7 GB/s for the asm loop and 66.8 GB/s for the loop with sums, measured on 2026-10-30 with an earlier build [Ref3]. In this run the best of 12 repetitions was 133.21 and 66.76 GB/s [Ref1].</li>` | Text of the page: finding 4, a comparison with the rates of an earlier report. It is fixed text. |
| 81 | `</ul>` | Text of the page: ends the list of the findings. |
| 82 | `<h2>Limits of this run</h2>` | Text of the page: the heading of the limits of the run. |
| 83 | `<ul>` | Text of the page: starts the list of the limits. |
| 84 | `<li><b>Order.</b> In every process the loops ran in the order k_read, k_asmread, k_cread. At 1 GiB the best rate of k_cread was 0.26 % to 0.81 % above the best rate of k_asmread in each of the four processes [Ref1]. An effect of the order is not excluded. A run with the order reversed would resolve it.</li>` | Text of the page: limit 1, the order of the kernels in every process: `k_read`, `k_asmread`, `k_cread`. It is fixed text. |
| 85 | `<li><b>Low repetitions.</b> At 32 KiB the three repetitions of k_cread in the first process (CPU 0, round 1) gave 131.84 to 131.95 GB/s, about 1 % below the other nine. At 8 MiB on CPU 2, round 1, the six repetitions of the two loops that only load gave 67.85 to 68.31 GB/s, against 69.75 to 71.15 GB/s in the other three processes. At 8 MiB the first repetition of k_asmread was also low in two more processes (70.01 and 69.75 GB/s). The cause was not examined.</li>` | Text of the page: limit 2, repetitions with low rates. It is fixed text. |
| 86 | `<li><b>One thread only.</b> No run with several threads was made.</li>` | Text of the page: limit 3, one thread only. |
| 87 | `<li><b>The loop start addresses differ.</b> The loop of k_cread starts at 0x1e24 and the loop of k_asmread at 0x1d1c [Ref2]. The rates are still nearly equal in this run.</li>` | Text of the page: limit 4, the loops of the two load-only kernels start at different addresses. It is fixed text. |
| 88 | `<li><b>Not a test of hypotheses A and B of the report.</b> k_cread has no vector adds. The loop with loads and adds in a 3:2 ratio is still not run.</li>` | Text of the page: limit 5, the run is not a test of two hypotheses of an earlier report. It is fixed text. |
| 89 | `</ul>` | Text of the page: ends the list of the limits. |
| 90 | `<h2>Conditions</h2>` | Text of the page: the heading of the conditions of the run. |
| 91 | `<ul>` | Text of the page: starts the list of the conditions. |
| 92 | `<li>Host load (1-minute load average of Linux) before the run: {loads[0]:.2f}, with no logins [Ref2]. The highest load recorded before a process was {max(loads):.2f} [Ref1]. This benchmark ran one busy thread during that time. No file shows what else ran.</li>` | Text of the page: the load of the machine. Python puts two computed values here, both with 2 decimals. `loads[0]` is the load value of the first header line of `cread.csv`. `max(loads)` is the highest load value of all header lines. The words around them are fixed text. |
| 93 | `<li>The run script stops if the file <code>/tmp/positron-perf.RUNNING</code> exists, and it checks before every process [Ref4].</li>` | Text of the page: the run script stops when the marker file `/tmp/positron-perf.RUNNING` exists. It is fixed text. |
| 94 | `<li>A check by hand in the login before the run (06:04 UTC) showed no process of the account positron-perf. Its output was not saved, so no file holds this observation.</li>` | Text of the page: a check by hand before the run, whose output was not saved. It is fixed text. |
| 95 | `<li>Run started 2026-11-13 06:05:10 UTC and ended 06:06:25 UTC [Ref2].</li>` | Text of the page: the start time and the end time of the run. It is fixed text: both times are typed into the script. |
| 96 | `<li>gcc 14.2.0, flags <code>-O3 -march=native -fno-tree-loop-distribute-patterns -pthread</code>, the flags of <code>bench/Makefile</code> [Ref2].</li>` | Text of the page: the compiler version and the compiler flags. It is fixed text. |
| 97 | `<li>The binary is a scratch copy of <code>bench/bandwidth.c</code> with the kernel <code>cread</code> added. <code>bench/bandwidth.c</code> was not changed [Ref4].</li>` | Text of the page: the binary is a copy of the benchmark source with the kernel `cread` added. It is fixed text. |
| 98 | `<li>The color palette is the first three slots of the dataviz skill. Its validator script could not be run here (no <code>node</code> on this machine).</li>` | Text of the page: a note on the colors of the chart. It is fixed text. |
| 99 | `</ul>` | Text of the page: ends the list of the conditions. |

### The page text: references, and the output file (lines 100 to 109)

| Line | Source | Explanation |
|---:|---|---|
| 100 | `<h2>References</h2>` | Text of the page: the heading of the references of the generated page. |
| 101 | `<ul>` | Text of the page: starts the list of the references. |
| 102 | `<li>[Ref1] <code>crb/results/cread-20261113T060510Z/cread.csv</code></li>` | Text of the page: reference 1 of the generated page, the file `cread.csv`. The path is fixed text. |
| 103 | `<li>[Ref2] <code>crb/results/cread-20261113T060510Z/probe.txt</code> (load, compiler, checksums, objdump of the three loops in the measured binary)</li>` | Text of the page: reference 2 of the generated page, the file `probe.txt` of the same result folder. |
| 104 | `<li>[Ref3] <code>crb/crb-memory-hierarchy.html</code>, section "The read loop compiled from C: 1.5 loads per cycle"</li>` | Text of the page: reference 3 of the generated page, a section of the report page `crb-memory-hierarchy.html`. |
| 105 | `<li>[Ref4] <code>crb/tmp/agent-scratch/cread-2026-11-12/bandwidth_cread.c</code> and <code>run_cread.sh</code></li>` | Text of the page: reference 4 of the generated page, the files `bandwidth_cread.c` and `run_cread.sh`. |
| 106 | `</ul>` | Text of the page: ends the list of the references. |
| 107 | `</body></html>'''` | Text of the page: ends the body and the page. The three quote characters end the format string that starts in line 45. |
| 108 | `open('cread-result.html','w').write(page)` | Writes the page to the file `cread-result.html` in the current folder. An older file of that name is replaced. |
| 109 | `print('ok',len(page))` | Prints the word `ok` and the number of characters of the page. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-cread/cread-20261113T060510Z`: the result folder of the cread test in the repo of the test data. It holds the files `cread.csv`, `probe.txt`, `cread-result.html` and `make_html.py`. Check of 2026-11-25: the command `cmp` finds `make_html.py` equal to `make_html.round2.py`.
