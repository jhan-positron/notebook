# `make_partA_html.py` explained, line by line

- Source file: `new-test-kernel/partA-analysis/make_partA_html.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 1355 lines, 108175 bytes).
- sha256 of the source when this page was built: `1b9dc00f8e3aeaf1551f3c59eeb2e0cd713c6a2a8852a85235401c785a3d8b12`.

## Short version: purpose

`make_partA_html.py` builds the result page of Part A, the screening part of the test plan of 2026-11-13, as one HTML file, from the json file that `analyze_partA.py` writes. It reads no measurement file: it prints the values of the json file as sentences, tables and charts, and it prints the words `Insufficient data` where a step, a file or a needed measurement is missing. The sentences that read the data are built from the values, and the fixed texts are definitions, quotations of the plan, captions and references.

## Words used here

- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan and how to analyse Part A.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The names B4, B5, B7, B8, B9, B10 and D2 are steps of the later parts of the plan.
- **Parts B, C and D of the plan**: the later parts of the plan. Part B uses a changed copy of the benchmark. Part C reads the counters of the cores. Part D needs root. These are not the parts of the later rerun.
- **Json file**: the file `partA-summary.json` that `analyze_partA.py` writes. It holds every measured value that the result page prints.
- **Result page**: the HTML file that this script writes, `partA-result.html` unless the caller names another.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of the tags**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are the hand-written kernels, taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`.
- **Launch, tag**: a launch is one start of a process by the run script `run_partA.sh`. The tag is the short name of the launch, for example `read_old-r1`.
- **Busiest processes, CPU use (`pcpu`)**: the 5 processes that the run script lists in the file `launches.txt` before each launch, each with the value of the column `pcpu` of the tool `ps`. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. So it is an average over the life of the process, not the CPU use at the launch.
- **Block**: the lines of one process in a csv file of a result folder.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rate**: bytes divided by time, in GB/s.
- **Total**: the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest elapsed time of a thread.
- **Thread rate**: the bytes of one thread divided by its own elapsed time. The benchmark prints it with 2 decimals.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Thread count `a+b`**: a threads on mesh 0 and b threads on mesh 1, for example `64+56`.
- **Pass**: one sweep of a thread over its whole buffer.
- **2 % check**: rule 7 of the plan: one pass may take at most 2 % of the interval. That means at least 50 passes per thread.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. It has no unit.
- **Pattern labels: split, uniform, between**: the provisional labels of a repetition: q below 0.65, q above 0.85, or neither. The page shows them only when the json file says that they are usable.
- **Fastest half**: the half of the threads of one repetition that has the highest rates.
- **Bracket**: the two neighbouring thread counts of step A4 between which the pattern label changes.
- **Level labels: low, high, changing**: the provisional labels of an interval with one thread at 8 MiB: a rate below 69 GB/s, above 70.5 GB/s, or neither.
- **Choice C1 to C11**: a definition that the analysis script had to fix where the plan and the handoff note give none.
- **Range**: in the json file, four values of a list of numbers: the count, the lowest value, the median and the highest value.
- **Median**: the middle value of a sorted list. With an even count it is the mean of the two middle values.
- **Observed in screening**: the words with which the page introduces the results of the steps A1 to A6. No control ran with such a result.
- **Insufficient data**: the words that the page prints where a value or a measurement is missing, with the measurement that would give it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **PMU**: performance monitoring unit, the counter hardware of a core.
- **SVE**: the scalable vector instruction set of Arm.
- **HTML, CSS, SVG**: the three formats of the page. HTML holds the text and the tables. CSS, the style sheet, sets fonts, colours and spacing. SVG holds the charts as drawing commands.
- **Class**: a name on an HTML element that selects its style, for example `take` for a highlighted statement and `miss` for a notice of missing data.
- **Hover text**: a text that a browser shows when the pointer rests on a mark of a chart.
- **Drawing unit**: the unit of the positions and sizes inside an SVG drawing. It is 1 pixel when the chart has its full width.
- **Q2a, H7a**: names of the plan. Q2a is the question why the old read kernel has a higher total than the new one with 120 threads. H7a is the hypothesis that the stop method and the short interval make a part of that difference.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the options `-o` and `--banner` and the path of the json file, and loads the json file (lines 1340 to 1348).
2. `build` opens the page: the head with the style sheet `CSS`, the banner when one is given, and the main heading (lines 1284 to 1293).
3. It adds the short version, which `short_version` builds as three sentences from the values, then the two questions and the list of the result folders (lines 1294 to 1301).
4. It adds the list of words from `WORDS` (line 1302).
5. It adds the table of the seven steps: two columns that are quoted from the plan (`LOOKS`, `PLAN`), and one column that `points_to` builds from the data (lines 1303 to 1309).
6. It adds ten sections, each built by its own function: the system load, the blocks that are not used, the distribution of q, the passes per thread, the steps A1 and A2, and the steps A3 to A7 (line 1310). The sections draw their charts with `strip_chart`, `mesh_pairs_chart`, `cpu_panels`, `a4_chart` and `a5_chart`, and they print numbers with `fx`.
7. It adds the limits of the page and the references (lines 1311 to 1336).
8. `main` writes the page to the output file and prints its path (lines 1349 to 1351).

## Behavior a reader must know

- The script reads one json file and writes one HTML file. It replaces an older file of the same name. It reads no result folder and runs nothing.
- All measured values come from the json file. The script itself derives simple values from them, for example differences, percentages, counts, lowest and highest values, the median of q per thread count (line 681) and, for the panels per CPU, the median of the rates of each thread over the repetitions (line 413).
- A number is printed by `fx` with 2 decimals unless the caller asks for another count. A value with a 5 as its third and last decimal keeps 3 decimals. Every other half is rounded away from zero (lines 42 to 52).
- The page marks its main statements about the steps A1 to A6 with the words `Observed in screening`: they start with these words or stand in a list under them. Not every sentence with a value carries them, for example the sentences on the load, on the passes, on the check of the level limits and on step A7. The generated sentences do not use the words `rejected` or `confirmed`. The test file checks on its test pages that these two words do not occur, and that the words `observed in screening` occur at least once.
- Where data is missing, the page does not stay silent: the function `missing` prints `Insufficient data` with the measurement that is missing (lines 74 to 75). A single missing value in a table cell is printed as a hyphen (line 62).
- The pattern labels split and uniform appear only when the json file gives `labels_usable` as true. If not, the page gives q without labels, and it says `Insufficient data` for the thread counts of step B8 (lines 742 to 746).
- The level labels of step A5 appear only for a CPU whose labels the json file marks as usable (lines 961 to 966).
- Axes: the charts of q run from 0 to 1. The chart of the two meshes and the panels per CPU start at 0 GB/s. The chart of step A5 and the chart of step A6 do not start at 0, and the caption or the axis title says so (line 952, line 1011).
- In a chart of `strip_chart` a value outside the axis is drawn at the end of the axis (line 93).
- Some numbers in the fixed texts are not read from the json file, for example the interval of 6000 ms in the row of step A4 (line 231), the 3 intervals per process in the caption of step A6 (line 1012) and the 0.3 s in the axis title of step A5 (line 891).
- The sentence that no total of A1 meets rule 7 is printed whenever at least one repetition of A1 has fewer than 50 passes, also when others pass the check (lines 255 to 258).
- The page is one file: it loads no script, font or image, and it has a light colour scheme only.
- The exit status is 0 after a run that worked. A json file that cannot be read ends the program with a Python error.
- The result folder `partA-20261113T205055Z` holds a copy of this file with the same sha256, beside the page `partA-result.html` [Ref1].

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partA-analysis/make_partA_html.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (1355 lines, 108175 bytes, sha256 `1b9dc00f8e3aeaf1551f3c59eeb2e0cd713c6a2a8852a85235401c785a3d8b12`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header text and imports (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env python3` | Tells Linux to run this file with `python3`. The tool `env` finds `python3` in the search path of the user. |
| 2 | `"""make_partA_html.py [partA-summary.json] [-o partA-result.html] [--banner TEXT]` | Starts the header text of the file (a docstring, a text that Python keeps but does not run). This line is the usage. The first argument is the json file. `-o` names the output page. `--banner` gives the text of a notice for the top of the page. Without arguments the input is `partA-summary.json` and the output is `partA-result.html`. |
| 4 | `Builds one self-contained HTML result page of Part A (screening) from the json that analyze_partA.py writes.` | Header text: the script builds one HTML page with the results of Part A, from the json file that `analyze_partA.py` writes. The page needs no other file. |
| 5 | `No external script, font or image. Light background only.` | Header text: the page loads no script, font or image from another place, and it has a light background only. |
| 7 | `Every sentence that interprets data is built from the values in the json. Typed text is limited to:` | Header text: a rule of this file. Every sentence of the page that reads the data is built from the values of the json file. The list of the fixed texts starts at the end of this line. |
| 8 | `the list "Words used here", the two questions under the Short version, the columns quoted from plan.md,` | Continues the list of the fixed texts: the list of words, the two questions under the short version, and the columns that are quoted from the plan. |
| 9 | `the section "Limits of this page", the captions that say how a chart is drawn, the sentences that say` | Continues the list: the section on the limits of the page, the captions that say how a chart is drawn, and the sentences that line 10 describes. |
| 10 | `what the plan, the handoff, the run script or the analysis script ask for or do (with their reference),` | Continues the list: the sentences that say what the plan, the handoff note, the run script or the analysis script ask for or do, each with its reference. |
| 11 | `and the references. A typed sentence that depends on the data is printed only under the computed condition.` | Ends the list with the references. A fixed sentence that depends on the data is printed only when a computed condition holds. |
| 12 | `Numbers are printed with fx(): a median that lies in the middle of two printed values keeps its third decimal.` | Header text: numbers are printed with the function `fx` (line 42). A median that lies exactly in the middle of two printed values keeps its third decimal. |
| 13 | `Part A is screening: the page says "observed in screening". The sentences built from data use none of the` | Header text: Part A is screening, so the page uses the words `observed in screening`. The sentence about the decision words ends in line 14. |
| 14 | `decision words of rule 11 of the plan. The column copied from the plan quotes some of them in negated form` | Continues the text: the sentences built from data use none of the decision words of rule 11 of the plan, such as `rejected`. The column that is copied from the plan quotes some of them in a negated form. |
| 15 | `("not observed", "does not reject H2", "rejects nothing", "not resolved at this grid").` | Continues the text: the four quoted forms, for example `not observed`. |
| 16 | `"""` | Ends the header text. |
| 17 | `import sys, json, html, statistics as st` | Loads four modules of the Python standard library: `sys` (arguments and exit status), `json` (the input format), `html` (safe text for HTML) and `statistics` under the short name `st` (the median). |
| 18 | `from decimal import Decimal, ROUND_HALF_UP` | Loads the exact decimal numbers of Python (`Decimal`) and the rounding rule `ROUND_HALF_UP`, which rounds a half away from zero. The function `fx` uses both. |

### Colours, kernel names and the texts quoted from the plan (lines 20 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `C0, C1, C2 = '#2a78d6', '#eb6834', '#1baf7a'      # mesh 0 / first series, mesh 1 / second series, third` | Three chart colours as HTML colour codes. `C0`, a blue, stands for mesh 0 or the first series. `C1`, an orange, stands for mesh 1 or the second series. `C2`, a green, is meant for a third series. No other line of the file uses `C2`. |
| 21 | `INK, MUTED, GRID, BAND = '#0b0b0b', '#52514e', '#e6e5e0', '#f1f0ec'` | Four more colours. `INK`: near black. `MUTED`: a dark grey for dashed lines. `GRID`: a light grey for grid lines. `BAND`: a very light grey for the band between two limits. No other line of the file uses `INK`. |
| 22 | `ID = 'Insufficient data'` | `ID`: the fixed words `Insufficient data`. The page prints them wherever a value or a measurement is missing. |
| 23 | `KNAME = dict(read_old='old read', read_new='new read', asmread='asm read', write_old='old write', write_new='new write', asmwrite='asm write')` | `KNAME`: the name that the page prints for each kernel name of the tags, for example `old read` for `read_old` and `asm read` for `asmread`. |
| 24 | `KORDER = ['read_old', 'read_new', 'asmread', 'write_old', 'write_new', 'asmwrite']` | `KORDER`: the order of the six kernels on the page: the three read kernels, then the three write kernels. |
| 25 | `PLAN = dict(` | `PLAN`: for each step, the text of the column `What the result points to` of the Part A table of the plan. The page quotes these texts in its first table (line 1308). |
| 26 | `    A1='Which CPUs are the fast threads of old read and of the faster write repetitions.',` | Text of the page: the quoted plan text for step A1. |
| 27 | `    A2='If the totals change with the long interval, H7a gets priority in B7. If they stay, the short interval alone is not sufficient to explain Q2a. H7b is untouched: the common start stays.',` | Text of the page: the quoted plan text for step A2, about the long interval and the hypotheses H7a and H7b. |
| 28 | `    A3='Whether the second buffer changes the pattern in this session. H9b is untouched.',` | Text of the page: the quoted plan text for step A3, about the second buffer. |
| 29 | `    A4='For each kernel, the two neighbouring thread counts between which the pattern changes. Equal brackets for both kernels are "not resolved at this grid", and the grid is then refined in B8.',` | Text of the page: the quoted plan text for step A4, about the two thread counts between which the pattern changes. |
| 30 | `    A5='Whether a change of level is observed in 30 intervals, in which direction, and after how many intervals. No change in 30 intervals is "not observed". It does not reject H2. A different level in the second process says nothing about H2, because the buffer is a new allocation.',` | Text of the page: the quoted plan text for step A5, about a change of level in 30 intervals. |
| 31 | `    A6='The rate of a buffer on 4 KiB pages, as a reference value for B4. Alone it rejects nothing: it does not show which coverage the low and the high intervals had.',` | Text of the page: the quoted plan text for step A6, about the rate of a buffer on pages of 4 KiB. |
| 32 | `    A7='- (the plan gives no entry: the step collects the vector length and the event names for parts C and D)')` | Text of the page for step A7. The plan gives no entry for it, and the text says so. It ends the dictionary `PLAN`. |
| 33 | `LOOKS = dict(A1='H8, H11, item 13', A2='H7a only', A3='H9a only', A4='H8', A5='H2', A6='H3a', A7='-')` | `LOOKS`: for each step, the text of the column `Looks at` of the same table of the plan: the hypotheses and the item that the step looks at. |
| 35 | `e = html.escape` | `e`: a short name for `html.escape`. That function replaces the characters that have a meaning in HTML, such as the angle brackets and the ampersand, by safe forms. The page passes texts from the data through it. |

### Helpers for numbers and texts: `pl`, `fx`, `fs`, `f2`, `rtxt`, `missing` (lines 38 to 77)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `def pl(n, one, many):` | Starts the function `pl`. It joins a number with the right form of a word. |
| 39 | `    return f'{n} {one if n == 1 else many}'` | Returns the number, a space, and the word `one` when the number is 1, or the word `many` in every other case. Example: `pl(1, 'launch', 'launches')` gives `1 launch`. |
| 42 | `def fx(v, nd=2):` | Starts the function `fx`. It turns a number into text with `nd` decimals. `nd` is 2 unless the caller gives another number. |
| 43 | `    """Number with nd decimals. A value with 2 decimals that lies exactly in the middle of two printed values (a median of an` | Text of the function: a number with `nd` decimals. The special case starts here: a value with 2 decimals that lies exactly in the middle of two printed values. |
| 44 | `    even count of rates, or a difference of such medians) is printed with 3 decimals (0.995), so that printed values agree` | Continues the text: such a value is a median of an even count of rates, or a difference of such medians. It is printed with 3 decimals, as 0.995 is. The purpose follows in line 45. |
| 45 | `    with each other. Other half values are rounded upward."""` | Continues the text: the printed values of one sentence then agree with each other. Other half values are rounded upward. |
| 46 | `    d6 = Decimal(f'{v:.6f}')` | `d6`: the value rounded to 6 decimals, as an exact decimal number. This removes the small errors of binary floating-point numbers. |
| 47 | `    if nd == 2 and d6 == d6.quantize(Decimal('0.001')) and d6 != d6.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) and abs(d6 * 1000) % 10 == 5:` | Tests for the special case. Four conditions must hold. 2 decimals are asked for. The value has at most 3 decimals: it is equal to itself rounded to 3 decimals. It is not a value with 2 decimals. Its third decimal is 5. |
| 48 | `        nd = 3` | The value is then printed with 3 decimals. |
| 49 | `    d = d6.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)` | `d`: the value rounded to `nd` decimals. `Decimal(1).scaleb(-nd)` is the step of the rounding, 0.01 for 2 decimals. `ROUND_HALF_UP` rounds a half away from zero. For a negative value that is downward, not upward as the text of line 45 says. |
| 50 | `    if d == 0:` | Tests whether the rounded value is zero. |
| 51 | `        d = abs(d)` | Removes the minus sign of a negative zero. So the page never prints a text such as `-0.00`. |
| 52 | `    return f'{d:.{nd}f}'` | Returns the value as text with exactly `nd` decimals. |
| 55 | `def fs(v, nd=2):` | Starts the function `fs`. It prints a number with its sign. |
| 56 | `    """As fx, with a sign."""` | Text of the function: it works as `fx`, with a sign. |
| 57 | `    t = fx(v, nd)` | `t`: the text that `fx` gives. |
| 58 | `    return t if t.startswith('-') else '+' + t` | Returns the text with a plus sign in front, unless it starts with a minus sign. The page uses this form for changes and differences. |
| 61 | `def f2(v, nd=2):` | Starts the function `f2`. It prints a value that can be missing. |
| 62 | `    return '-' if v is None else fx(v, nd)` | Returns a hyphen for a missing value (`None`), and the text of `fx` for a number. |
| 65 | `def rtxt(r, nd=2, unit=''):` | Starts the function `rtxt`. It prints a range of the json file as text. |
| 66 | `    """Text of a range dict {n,min,median,max}."""` | Text of the function: a range is a dictionary with the count, the lowest value, the median and the highest value. |
| 67 | `    if not r or not r.get('n'):` | Tests whether the range is missing or holds no value. |
| 68 | `        return '-'` | Returns a hyphen in that case. |
| 69 | `    u = f' {unit}' if unit else ''` | `u`: a space and the unit, or nothing when no unit is given. |
| 70 | `    a, b = fx(r['min'], nd), fx(r['max'], nd)` | `a` and `b`: the lowest and the highest value as text. |
| 71 | `    return f"{a}{u}" if a == b else f"{a} to {b}{u}"` | Returns one number when the two texts are equal, and the form `lowest to highest` when they differ, with the unit at the end. |
| 74 | `def missing(what):` | Starts the function `missing`. It builds the notice for something that the data do not give. |
| 75 | `    return f'<p class="miss"><b>{ID}.</b> {what}</p>'` | Returns a paragraph of the class `miss`: the words `Insufficient data.` in bold, then the text `what`. The style sheet gives this class a pale orange background with a dark orange bar at the left (line 1189). |

### SVG helpers: `svg_open` and `marker` (lines 78 to 88)

| Line | Source | Explanation |
|---:|---|---|
| 78 | `def svg_open(W, H, aria):` | Starts the function `svg_open`. SVG is the vector drawing format of web pages. Every chart of the page is one SVG drawing inside the HTML text. |
| 79 | `    return [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{e(aria)}" style="max-width:{W}px">']` | Returns a list with the opening tag of a drawing. The drawing has `W` by `H` units, fills the width of the page up to `W` pixels, and carries the text `aria` as its description for screen readers. The caller adds its drawing commands to this list. |
| 82 | `def marker(x, y, shape, color, title, r=5):` | Starts the function `marker`. It draws one data point at the position (`x`, `y`) as a circle or a diamond with the radius `r`. |
| 83 | `    t = f'<title>{e(title)}</title>'` | `t`: a `title` element with the text `title`. A browser shows it when the pointer rests on the mark. |
| 84 | `    if shape == 'diamond':` | The case of a diamond. |
| 85 | `        return f'<path d="M{fx(x, 1)},{fx(y-r-1, 1)} l{r+1},{r+1} l-{r+1},{r+1} l-{r+1},-{r+1} Z" fill="{color}" stroke="#fff" stroke-width="1.5">{t}</path>'` | Returns a diamond: a path that starts above the centre, goes to the right corner, the bottom corner and the left corner, and closes. It is filled with the colour and has a white edge 1.5 units wide. |
| 86 | `    return f'<circle cx="{fx(x, 1)}" cy="{fx(y, 1)}" r="{r}" fill="{color}" stroke="#fff" stroke-width="1.5">{t}</circle>'` | Every other shape: returns a circle with the radius `r` at the point, filled with the colour, with the same white edge. |

### Function `strip_chart`: one row of dots per name (lines 89 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 89 | `def strip_chart(rows, xmin, xmax, ticks, xlabel, aria, vlines=(), band=None, nd=2, unit=''):` | Starts the function `strip_chart`. It draws a chart with one horizontal row of dots per name. Each dot is one value on a common horizontal axis from `xmin` to `xmax`. The parameters `nd` and `unit` are not used in the function. |
| 90 | `    """rows: [(name, [(value, title)], right_label)]. One row of dots per name."""` | Text of the function: `rows` is a list of triples: the row name, the list of pairs of value and hover text, and the label at the right. |
| 91 | `    W, L, R, rh, top = 840, 230, 230, 28, 30` | Sizes in drawing units: the width 840, a left margin of 230 for the row names, a right margin of 230 for the row labels, a row height of 28 and a top margin of 30. |
| 92 | `    H = top + len(rows) * rh + 48; PW = W - L - R` | `H`: the height: the top margin, the rows and 48 units for the axis. `PW`: the width of the plot area, 380 units. |
| 93 | `    x = lambda v: L + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * PW` | `x`: a function that turns a value into a horizontal position. A value outside the axis is drawn at the nearest end of the axis. |
| 94 | `    o = svg_open(W, H, aria)` | `o`: the list of the drawing commands, starting with the opening tag. |
| 95 | `    if band:` | Only when a band is given. |
| 96 | `        o.append(f'<rect x="{fx(x(band[0]), 1)}" y="{top-6}" width="{fx(x(band[1])-x(band[0]), 1)}" height="{len(rows)*rh+6}" fill="{BAND}"/>')` | Draws the band: a light grey rectangle from the value `band[0]` to the value `band[1]`, over all rows. |
| 97 | `        o.append(f'<text x="{fx((x(band[0])+x(band[1]))/2, 1)}" y="{top-12}" text-anchor="middle" class="ax">{e(band[2])}</text>')` | Writes the name of the band, `band[2]`, above its middle. |
| 98 | `    for t in ticks:` | Loop over the tick values of the horizontal axis. |
| 99 | `        o.append(f'<line x1="{fx(x(t), 1)}" y1="{top-6}" x2="{fx(x(t), 1)}" y2="{H-48}" stroke="{GRID}"/>')` | Draws a light grey vertical grid line at the tick value. |
| 100 | `        o.append(f'<text x="{fx(x(t), 1)}" y="{H-32}" text-anchor="middle" class="ax">{t:g}</text>')` | Writes the tick value under the plot. The format `g` prints it without zeros at the end. |
| 101 | `    for v, lab in vlines:` | Loop over the extra vertical lines, each a pair of a value and a label. |
| 102 | `        o.append(f'<line x1="{fx(x(v), 1)}" y1="{top-6}" x2="{fx(x(v), 1)}" y2="{H-48}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Draws a dashed dark grey vertical line at the value. |
| 103 | `        if lab:` | Only when the line has a label. |
| 104 | `            o.append(f'<text x="{fx(x(v), 1)}" y="{top-12}" text-anchor="middle" class="ax">{e(lab)}</text>')` | Writes the label above the plot. |
| 105 | `    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">{e(xlabel)}</text>')` | Writes the title of the horizontal axis, centred under the plot. |
| 106 | `    for i, (name, pts, right) in enumerate(rows):` | Loop over the rows. `i` is the row number, counted from 0. |
| 107 | `        y = top + i * rh + rh / 2` | `y`: the vertical centre of the row. |
| 108 | `        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')` | Writes the row name at the left of the plot, aligned at its right end. |
| 109 | `        o.append(f'<line x1="{L}" y1="{fx(y+rh/2, 1)}" x2="{L+PW}" y2="{fx(y+rh/2, 1)}" stroke="{GRID}"/>')` | Draws a light grey horizontal line under the row. |
| 110 | `        for j, (v, title) in enumerate(pts):` | Loop over the values of the row. `j` is the number of the value. |
| 111 | `            o.append(f'<circle cx="{fx(x(v), 1)}" cy="{fx(y + ((j*7)%5-2)*2.5, 1)}" r="4" fill="{C0}" fill-opacity="0.65" stroke="#fff" stroke-width="1"><title>{e(title)}</title></circle>')` | Draws one dot per value: a blue circle with the radius 4 that is 65 % opaque. Its vertical place is moved by one of five steps between 5 units up and 5 units down, chosen by `j`. So dots with equal values stay visible. The hover text is `title`. |
| 112 | `        o.append(f'<text x="{L+PW+10}" y="{fx(y+4, 1)}" class="val">{e(right)}</text>')` | Writes the row label at the right of the plot. |
| 113 | `    o.append('</svg>')` | Closes the drawing. |
| 114 | `    return '\n'.join(o)` | Returns the drawing as one text, one command per line. |
| 117 | `# ---------------------------------------------------------------- sections` | Comment: a divider. The functions below build the sections of the page. |

### Function `sec_load`: the section on the system load (lines 119 to 196)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `def sec_load(s):` | Starts the function `sec_load`. It builds the section on the system load of the run. `s` is the content of the json file. |
| 120 | `    o = ['<h2 id="load">System load of the run</h2>']` | `o`: the pieces of the section. It starts with the heading of the section. |
| 121 | `    envs = [x for x in s['env'] if x['present']]` | `envs`: the entries of the folders whose `env.txt` exists. |
| 122 | `    if not envs and not s['load']:` | Tests whether no `env.txt` exists and the json file has no load readings per step. |
| 123 | `        return '\n'.join(o) + missing('The system load: no <code>env.txt</code> and no header line of a launch was found in the result folders.')` | Returns the heading with an `Insufficient data` notice: no `env.txt` and no header line of a launch was found. |
| 124 | `    lc = s.get('load_check') or {}` | `lc`: the result of the function `load_check` of the analysis script, or an empty dictionary. |
| 125 | `    high = bool(lc.get('n_launches')) and lc['load1_max'] is not None and lc['load1_max'] > 2` | `high`: true when launches exist and the highest load average over 1 minute in a header line is above 2 tasks. |
| 126 | `    if lc.get('n_launches'):` | The readings are printed only when launches exist. |
| 127 | `        own = lc['own_user']` | `own`: the account that ran the run script, or `None`. |
| 128 | `        o.append('<p class="take">' + ('No reading of this run shows load from another user.' if lc['no_other_load_seen'] else` | Adds the main statement of the section, in a highlighted paragraph. When the value `no_other_load_seen` of the json file is true, it says that no reading shows load from another user. |
| 129 | `                                       'The readings of this run do not exclude load from another user. They are listed below.') + '</p>')` | Continues line 128: when the value is false, the statement says that the readings do not exclude such load and are listed below. |
| 130 | `        o.append('<p>The script took these readings directly before each launch [Ref3]:</p><ul>')` | Adds the sentence that introduces the readings, with the reference to the run script, and opens a list. |
| 131 | `        t = '<li>Runnable tasks in the header line of each launch: '` | `t`: the first list item, about the runnable tasks in the header lines. |
| 132 | `        if lc['n_many_threads']:` | Only when launches with many threads exist. |
| 133 | `            t += f"at most {lc['runnable_header_max_many']} at the {pl(lc['n_many_threads'], 'launch', 'launches')} with many threads"` | Adds the highest number of runnable tasks at these launches, and how many such launches there are. |
| 134 | `        if lc['n_one_thread']:` | Only when launches with one thread exist. |
| 135 | `            t += (', and ' if lc['n_many_threads'] else '') + f"at most {lc['runnable_header_max_one']} at the {pl(lc['n_one_thread'], 'launch', 'launches')} with one thread"` | Adds the same for the launches with one thread, after a comma and the word `and` when both kinds exist. |
| 136 | `        o.append(t + '. One of these tasks is the script that reads the value.</li>')` | Ends the item with a fixed note on how to read these numbers: the count includes the script that takes the reading. |
| 137 | `        if lc['n_with_launches_txt']:` | Only when `launches.txt` gave a second reading. |
| 138 | `            o.append(f"<li>The file <code>launches.txt</code> holds a second reading of the runnable tasks, taken a moment before the header line. Its highest value was {lc['runnable_launches_txt_max']}. "` | Adds an item about the second reading of the runnable tasks in `launches.txt`: when it was taken, and its highest value. |
| 139 | `                     f"It differs from the header line at {lc['n_runnable_differ']} of {pl(lc['n_with_launches_txt'], 'launch', 'launches')}.</li>")` | Continues the item: at how many launches the two readings differ. |
| 140 | `        o.append('<li>0 users were logged in at every launch.</li>' if lc['logins_max'] == 0 else f"<li>Logged-in users: at most {lc['logins_max']} at a launch.</li>")` | Adds an item about the logins: a fixed sentence when the highest number is 0, and the highest number in every other case. |
| 141 | `        o.append(f"<li>Waits: {lc['n_waited']} of {pl(lc['n_launches'], 'launch', 'launches')} had to wait for a quiet system.</li>")` | Adds an item about the waits: how many launches had to wait for a quiet system, of how many. |
| 142 | `        if own and lc['busiest_own']:` | The case that the own account is known and has processes in the lists. |
| 143 | `            names = [b['comm'] for b in lc['busiest_own']]` | `names`: the command names of the busiest processes of the own account. |
| 144 | `            t = (f"<li>Busiest processes in <code>launches.txt</code>: the highest values belong to the account <code>{e(own)}</code>, which ran the script: "` | `t`: an item about the busiest processes. It says that the highest values belong to the account that ran the script, and names that account. |
| 145 | `                 + ', '.join(f"{e(b['comm'])} {fx(b['pcpu'], 1)} %" for b in lc['busiest_own']) + ' of one CPU at most. ')` | Continues the item: each of these processes with its highest CPU use, with 1 decimal, in percent of one CPU. |
| 146 | `            if 'ps' in names:` | Only when `ps` is among them. |
| 147 | `                t += 'The script starts <code>ps</code> to write this list, so <code>ps</code> is the script itself [Ref3]. '` | Adds a fixed note with a reference: the `ps` process of this list is started by the run script itself. |
| 148 | `            if 'bash' in names:` | Only when `bash` is among them. |
| 149 | `                t += 'The script is a <code>bash</code> script [Ref3]. '` | Adds a fixed note with a reference: the `bash` process is the run script. |
| 150 | `            if lc['busiest_other']:` | Only when a process of another account was seen. |
| 151 | `                b = lc['busiest_other'][0]` | `b`: the busiest process of another account. |
| 152 | `                t += f"The busiest process of another account was {e(b['comm'])} of {e(b['user'])} with {fx(b['pcpu'], 1)} % of one CPU."` | Adds its command name, its user and its CPU use. |
| 153 | `            o.append(t + '</li>')` | Closes the item and adds it. |
| 154 | `        elif lc['busiest_other']:` | The case that the own account is not known and processes were seen. |
| 155 | `            o.append('<li>Busiest processes in <code>launches.txt</code>: ' + ', '.join(f"{e(b['comm'])} of {e(b['user'])} {fx(b['pcpu'], 1)} %" for b in lc['busiest_other'])` | Adds an item that lists the busiest processes with user and CPU use. |
| 156 | `                     + ' of one CPU at most. The account of the script could not be read from the list.</li>')` | Continues the item: a fixed sentence that the account of the script could not be read from the list. |
| 157 | `        o.append('</ul>')` | Closes the list of readings. |
| 158 | `        if high:` | Only when the load average was high. |
| 159 | `            o.append(f"<p>The 1-minute load went up to {fx(lc['load1_max'])} tasks. This value is an average over about the last minute. "` | Adds a paragraph: the highest load average over 1 minute, and the fact that this value is an average over about the last minute. |
| 160 | `                     f"Hypothesis: the high values are left from the threads of our own benchmark process that ended directly before the launch (up to {lc['threads_max']} threads). "` | Continues the paragraph with a hypothesis, marked as such: the high values are left from the threads of our own benchmark process that ended directly before the launch. It names the highest thread count. |
| 161 | `                     + ('The readings above agree with the hypothesis. ' if lc['no_other_load_seen'] else '')` | Continues the paragraph: when no other load was seen, a sentence that the readings agree with the hypothesis. |
| 162 | `                     + f"It is not measured. {ID}: no reading was taken while a benchmark ran. A reading of the runnable tasks of each account during an interval would decide it.</p>")` | Continues the paragraph: the hypothesis is not measured. An `Insufficient data` statement names the reading that would decide it: the runnable tasks of each account during an interval. |
| 163 | `    o.append('<ul>')` | Opens a second list, one item per result folder. |
| 164 | `    for x in s['env']:` | Loop over the folders. |
| 165 | `        if not x['present']:` | A folder without `env.txt`. |
| 166 | `            o.append(f"<li>Folder <code>{e(x['folder'])}</code>: {ID}. The file <code>env.txt</code> is missing, so the load at the start of this script is not known.</li>"); continue` | Adds an item with `Insufficient data`: the load at the start of the script is not known for this folder. `continue` goes to the next folder. |
| 167 | `        la = (x.get('start_loadavg') or '').split()` | `la`: the four load fields of the first line of `env.txt`, as a list. |
| 168 | `        end = (x.get('end_loadavg') or '').split()` | `end`: the four load fields of the end line, or an empty list. |
| 169 | `        t = f"<li>Folder <code>{e(x['folder'])}</code> (steps {e(x.get('steps') or '-')}), started at {e(x.get('start_utc') or '-')}. "` | `t`: the item of the folder. It starts with the folder name, the steps of the call and the start time. |
| 170 | `        t += (f"The 1-minute load at the start of the script was {e(la[0])} tasks, with {e(x.get('start_logins') or '-')} logged-in users. " if la else '')` | Adds the load average over 1 minute at the start and the number of logins, when the first line was read. |
| 171 | `        t += (f"The 1-minute load at the end was {e(end[0])} tasks. " if end else 'The script wrote no end line, so it did not reach its end. ')` | Adds the load average over 1 minute at the end. Without an end line it adds a fixed note that the run script did not reach its end. |
| 172 | `        if end and high and float(end[0]) > 2:` | Tests whether the end value is above 2 tasks while the hypothesis paragraph is shown. |
| 173 | `            t += 'The hypothesis above covers this value too. '` | Adds the sentence that the hypothesis covers this value too. |
| 174 | `        t += ''.join(f'The script wrote: "{e(k)}". ' for k in x.get('skipped', []))` | Adds every `skipped` line of `env.txt` as a quotation of what the script wrote. |
| 175 | `        o.append(t + '</li>')` | Closes the item and adds it. |
| 176 | `    o.append('</ul>')` | Closes the list of folders. |
| 177 | `    if s['load']:` | The table is printed only when the json file has load readings per step. |
| 178 | `        o.append('<p>The table gives the readings per step. The load, the runnable tasks, the waits and the logged-in users are from the header lines of the csv files. '` | Adds a paragraph that says where the columns of the table come from: the load, the runnable tasks, the waits and the logins come from the header lines of the csv files. |
| 179 | `                 'The second reading of the runnable tasks and the busiest processes are from <code>launches.txt</code> [Ref3].</p>')` | Continues the paragraph: the second reading of the runnable tasks and the busiest processes come from `launches.txt`. |
| 180 | `        o.append('<div class="tw"><table><tr><th>Step</th><th>Launches used</th><th>UTC first to last</th><th>1-minute load (tasks), lowest to highest</th>'` | Opens the table of the steps. This line holds the first four column headings: the step, the launches used, the first and last UTC time, and the lowest and highest load average over 1 minute. |
| 181 | `                 '<th>Runnable tasks in the header line, highest</th><th>Runnable tasks in launches.txt, highest</th><th>Launches that waited</th><th>Longest wait (s)</th><th>Launches that waited the full 20 s</th><th>Logged-in users, highest</th><th>Busiest processes seen (highest % of one CPU)</th></tr>')` | Continues the headings: the highest runnable tasks of each of the two readings, the launches that waited, the longest wait in seconds, the launches that waited the full 20 s, the highest number of logins, and the busiest processes. |
| 182 | `        for st_, L in s['load'].items():` | Loop over the steps with load readings. |
| 183 | `            busy = ', '.join(f"{e(b['comm'])} of {e(b['user'])} {fx(b['max_pcpu'], 1)} %" for b in L['busiest'][:3]) or f'{ID}: launches.txt has no entry'` | `busy`: up to 3 of the busiest processes of the step, each with user and CPU use. When `launches.txt` has no entry, the text is an `Insufficient data` note. |
| 184 | `            r2 = L.get('runnable_launches_txt') or {}` | `r2`: the range of the second reading of the runnable tasks. |
| 185 | `            o.append(f"<tr><td>{st_}</td><td>{L['launches']}</td><td>{e(L['first_utc'])} to {e(L['last_utc'])}</td><td>{rtxt(L['load1'])}</td><td>{L['runnable']['max']}</td>"` | Adds the row of the step: the step name, the number of launches, the two UTC times, the range of the load average and the highest runnable tasks of the header lines. |
| 186 | `                     f"<td>{r2['max'] if r2.get('n') else '-'}</td>"` | Continues the row: the highest value of the second reading, or a hyphen. |
| 187 | `                     f"<td>{L['n_waited']}</td><td>{L['waited_s']['max']:g}</td><td>{L['n_waited_20s']}</td><td>{L['logins']['max']}</td><td>{busy}</td></tr>")` | Continues the row: the launches that waited, the longest wait, the launches that waited 20 s, the highest number of logins and the text `busy`. |
| 188 | `        o.append('</table></div>')` | Closes the table. |
| 189 | `        o.append('<details><summary>Load of every launch</summary><div class="tw"><table><tr><th>Folder</th><th>Step</th><th>Tag</th><th>UTC</th><th>Waited (s)</th><th>1-minute load</th><th>5-minute load</th><th>Runnable tasks, header line</th><th>Runnable tasks, launches.txt</th><th>Logged-in users</th></tr>')` | Opens a part that the reader can unfold, with the title `Load of every launch`, and inside it a table with one row per launch. The line holds its ten column headings. |
| 190 | `        for l in s['launches']:` | Loop over the used launches. |
| 191 | `            r2 = l.get('runnable_launches_txt')` | `r2`: the second reading of the runnable tasks of this launch. |
| 192 | `            o.append(f"<tr><td>{e(l['folder'])}</td><td>{l['step']}</td><td>{e(l['tag'])}</td><td>{l['utc']}</td><td>{l['waited_s']:g}</td><td>{fx(l['load1'], 2)}</td><td>{fx(l['load5'], 2)}</td><td>{l['runnable']}</td><td>{'-' if r2 is None else r2}</td><td>{l['logins']}</td></tr>")` | Adds the row of the launch: folder, step, tag, UTC time, waited seconds, the load averages over 1 and 5 minutes with 2 decimals, the two readings of the runnable tasks and the number of logins. |
| 193 | `        o.append('</table></div></details>')` | Closes the table and the unfolding part. |
| 194 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `sec_blocks`: blocks that are not used, steps without data (lines 197 to 213)

| Line | Source | Explanation |
|---:|---|---|
| 197 | `def sec_blocks(s):` | Starts the function `sec_blocks`. It builds the section on the processes that were stopped, failed or repeated, and on the steps without data. |
| 198 | `    c = s['counts']` | `c`: the counts of the blocks from the json file. |
| 199 | `    o = ['<h2 id="blocks">Processes that were stopped, failed or repeated</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 200 | `    o.append(f"<p>The result folders hold {c['blocks_found']} process blocks. {c['blocks_used']} are used on this page. "` | Adds a paragraph: the number of process blocks in the result folders, and the number that the page uses. |
| 201 | `             f"{pl(c['killed'], 'was', 'were')} stopped by the script, {c['failed']} failed, and {pl(c['repeated_tags'], 'launch exists', 'launches exist')} more than once.</p>")` | Continues the paragraph: how many blocks the script stopped, how many failed, and how many launches exist more than once. |
| 202 | `    if s['not_used']:` | The table is printed only when at least one block is not used. |
| 203 | `        o.append('<p>If a launch exists more than once, the page uses its last complete block [Ref5].</p>')` | Adds a sentence: of a launch that exists more than once, the page uses the last complete block. It cites the analysis script. |
| 204 | `        o.append('<div class="tw"><table><tr><th>Folder</th><th>Step</th><th>Tag</th><th>UTC</th><th>Why it is not used</th><th>A complete block of the same launch is used</th></tr>')` | Opens a table with six column headings: folder, step, tag, UTC time, the reason why the block is not used, and whether a complete block of the same launch is used. |
| 205 | `        for x in s['not_used']:` | Loop over the blocks that are not used. |
| 206 | `            o.append(f"<tr><td>{e(x['folder'])}</td><td>{x['step']}</td><td>{e(x['tag'])}</td><td>{x['utc']}</td><td>{e(x['reason'])}</td><td>{'yes' if x['replaced'] else 'no: this launch has no data'}</td></tr>")` | Adds the row of the block. The last cell says `yes`, or that this launch has no data. |
| 207 | `        o.append('</table></div>')` | Closes the table. |
| 208 | `    for st_ in s['steps_missing']:` | Loop over the steps that have no usable data. |
| 209 | `        why = '; '.join(k for x in s['env'] for k in x.get('skipped', []) if k.startswith(st_))` | `why`: the `skipped` lines of the files `env.txt` that start with the name of this step, joined with a semicolon. |
| 210 | `        o.append(missing(f"Step {st_} has no usable data in these folders." + (f' The script wrote: "{e(why)}".' if why else '') + f" The measurement that is missing: the launches of step {st_} of <code>run_partA.sh</code>."))` | Adds an `Insufficient data` notice for the step: it has no usable data, what the script wrote about it (when `why` is not empty), and which launches of `run_partA.sh` would give the missing measurement. |
| 211 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `sec_passes`: passes per thread and the 2 % check (lines 214 to 265)

| Line | Source | Explanation |
|---:|---|---|
| 214 | `def sec_passes(s):` | Starts the function `sec_passes`. It builds the section on the passes per thread, the 2 % check of rule 7 of the plan. |
| 215 | `    lim = s['limits']['min_passes']` | `lim`: the smallest number of passes per thread, from the json file. The analysis script sets it to 50. |
| 216 | `    o = ['<h2 id="passes">Passes per thread (the 2 % check)</h2>',` | `o`: the pieces of the section, starting with its heading. |
| 217 | `         f'<p>Rule 7 of the plan asks that one pass takes at most 2 % of the interval. That means at least {lim} passes per thread [Ref1]. '` | Text of the page: what rule 7 of the plan asks. One pass may take at most 2 % of the interval. That gives at least `lim` passes per thread. |
| 218 | `         'A thread stops only after a whole pass. So with fewer passes, the last pass alone can change the rate of a repetition by more than 2 %.</p>'` | Text of the page: why the rule matters. A thread ends an interval only at the end of a pass. With few passes the last pass alone has a share of more than 2 % in the rate of a repetition. |
| 219 | `         '<p>Passes per thread = total bytes / (threads x bytes per thread), and half of that for a copy kernel. This is an average over the threads [Ref2]. '` | Text of the page: the formula. The passes per thread are the total bytes divided by the threads times the bytes per thread, and half of that for a copy kernel. The text says that this is an average over the threads. |
| 220 | `         'The handoff expected about 52 to 86 passes in 6 s for read kernels and about 55 to 67 in 15 s for write kernels (est.) [Ref2].</p>']` | Text of the page: the pass counts that the handoff note expected for 6 s and for 15 s, marked as an estimate. |
| 221 | `    rows = []` | `rows`: the rows of the table, empty at first. |
| 222 | `    for st_ in ('A1', 'A2'):` | Loop over the steps A1 and A2. |
| 223 | `        for k in KORDER:` | Loop over the six kernels in the order of the page. |
| 224 | `            if k in s[st_]:` | Takes a kernel only when the step has data for it. |
| 225 | `                x = s[st_][k]; rows.append((st_, KNAME[k], x['min_ms'], x['passes_per_thread'], x['n_below_50_passes'], len(x['reps'])))` | Adds a row: the step, the printed kernel name, the interval length in ms, the range of the passes per thread, the number of repetitions below 50 passes, and the number of repetitions. |
| 226 | `    for g, x in s['A3']['groups'].items():` | Loop over the groups of step A3. |
| 227 | `        pp = [r['passes_per_thread'] for p in x['processes'] for r in p['reps']]` | `pp`: the passes per thread of all read repetitions of the group. |
| 228 | `        rows.append(('A3', f"old read, {x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}", x['min_ms'], dict(n=len(pp), min=min(pp), max=max(pp)) if pp else None, x['n_below_50_passes'], len(pp)))` | Adds a row for the group: `A3`, the text `old read` with the number of buffers, the interval length, the lowest and the highest pass count, the number below 50 passes and the number of repetitions. |
| 229 | `    for k, x in s['A4']['kernels'].items():` | Loop over the kernels of step A4. |
| 230 | `        pp = [r['passes_per_thread'] for c in x['counts'].values() for r in c['reps']]` | `pp`: the passes per thread of all repetitions of the kernel, over all thread counts. |
| 231 | `        rows.append(('A4', KNAME.get(k, k), 6000, dict(n=len(pp), min=min(pp), max=max(pp)) if pp else None, sum(c['n_below_50_passes'] for c in x['counts'].values()), len(pp)))` | Adds a row for the kernel. The interval length is the fixed number 6000 ms, not a value of the json file. The run script uses 6000 ms for every A4 process. |
| 232 | `    if not rows:` | Tests whether the table has no row. |
| 233 | `        return '\n'.join(o) + missing('No repetition with more than one thread is in the result folders, so no pass count can be given.')` | Returns the heading and the texts with an `Insufficient data` notice: no repetition with more than one thread exists, so no pass count can be given. |
| 234 | `    o.append('<div class="tw"><table><tr><th>Step</th><th>Kernel</th><th>Shortest interval (ms)</th><th>Passes per thread, lowest to highest</th>'` | Opens the table. This line holds four column headings: step, kernel, shortest interval in ms, and passes per thread from lowest to highest. |
| 235 | `             f'<th>Repetitions below {lim} passes</th><th>Repetitions</th></tr>')` | Continues the headings: the repetitions below `lim` passes, and the repetitions. |
| 236 | `    for st_, k, ms, r, nb, n in rows:` | Loop over the rows. |
| 237 | `        o.append(f"<tr><td>{st_}</td><td>{e(k)}</td><td>{f2(ms, 0)}</td><td>{rtxt(r, 1)}</td><td>{nb}</td><td>{n}</td></tr>")` | Adds the row. The interval length is printed without decimals and the passes with 1 decimal. |
| 238 | `    o.append('</table></div>')` | Closes the table. |
| 239 | `    low = s['passes']['below_50']; n = s['passes']['n_below_50']; ntab = sum(r[4] for r in rows)` | `low`: the list of the repetitions below 50 passes from the json file. `n`: their number. `ntab`: the sum of the column `below 50 passes` of the table. |
| 240 | `    t = f"<p>{pl(n, 'repetition', 'repetitions')} with more than one thread {'has' if n == 1 else 'have'} fewer than {lim} passes per thread. The table has {ntab} of them. "` | `t`: a paragraph: how many repetitions with more than one thread have fewer than `lim` passes per thread, and how many of them the table holds. |
| 241 | `    left = [x for x in low if x['step'] == 'A3' and x['kernel'] != 'read']` | `left`: the repetitions of step A3 below 50 passes whose kernel is not `read`. |
| 242 | `    if n - ntab > 0:` | Only when the json file counts more of them than the table. |
| 243 | `        t += (f"The other {n - ntab} are the write and copy repetitions of the A3 processes with two buffers. This page does not compare these rows. " if len(left) == n - ntab` | Adds a sentence about the others. When they are exactly the write and copy repetitions of step A3, it names them and says that the page does not compare these rows. |
| 244 | `              else f"The other {n - ntab} are not in the table. ")` | Continues line 243: in every other case it says only that the others are not in the table. |
| 245 | `    o.append(t + '</p>')` | Closes the paragraph and adds it. |
| 246 | `    if low:` | The rest of the section is printed only when at least one repetition is below 50 passes. |
| 247 | `        li = []` | `li`: the list items, empty at first. |
| 248 | `        for ms in sorted(set(x['min_ms'] or 0 for x in low)):` | Loop over the interval lengths of these repetitions, in rising order. A missing length counts as 0. |
| 249 | `            xs = [x for x in low if (x['min_ms'] or 0) == ms]` | `xs`: the repetitions with this interval length. |
| 250 | `            steps = sorted(set(x['step'] for x in xs))` | `steps`: the steps in which they occur, sorted. |
| 251 | `            li.append(f"<li>Interval {ms/1000:g} s: {len(xs)}. " + ' '.join(f"Step {a}: {sum(1 for x in xs if x['step'] == a)}." for a in steps)` | Adds an item: the interval length in seconds, the number of these repetitions, and the number per step. |
| 252 | `                      + f" Their passes per thread are {fx(min(x['passes_per_thread'] for x in xs), 1)} to {fx(max(x['passes_per_thread'] for x in xs), 1)}.</li>")` | Continues the item: their lowest and highest passes per thread, with 1 decimal. |
| 253 | `        o.append('<p>By interval:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `By interval:`. |
| 254 | `        a1n = sum(len(s['A1'][k]['reps']) for k in s['A1']); a1low = sum(1 for x in low if x['step'] == 'A1')` | `a1n`: the number of all repetitions of step A1. `a1low`: the number of repetitions of A1 below 50 passes. |
| 255 | `        if a1n and a1low:` | Only when A1 has repetitions and at least one of them is below 50 passes. |
| 256 | `            pmin = min(x['passes_per_thread'] for x in low if x['step'] == 'A1')` | `pmin`: the lowest passes per thread among these repetitions of A1. |
| 257 | `            o.append(f"<p>What this means for A1: {a1low} of its {a1n} repetitions fail the check. At the lowest count ({fx(pmin, 1)} passes per thread), one whole pass is {fx(100 / pmin, 0)} % of the bytes of a thread in the interval. "` | Adds a paragraph about A1: how many of its repetitions fail the check. At the lowest pass count, one whole pass is 100 divided by `pmin` percent of the bytes of a thread in the interval. |
| 258 | `                     'So no total of A1 meets rule 7. A1 uses the default 0.5 s interval of the earlier run [Ref1]. A2 repeats the kernels with the long interval.</p>')` | Continues the paragraph with fixed sentences: no total of A1 meets rule 7, A1 uses the default interval of 0.5 s of the earlier run, and A2 repeats the kernels with the long interval. The first of them is printed whenever at least one repetition of A1 fails the check (line 255), also when not all of them fail. |
| 259 | `        longlow = [x for x in low if (x['min_ms'] or 0) >= 6000]` | `longlow`: the repetitions below 50 passes whose interval is 6000 ms or longer. |
| 260 | `        if longlow:` | Only when such repetitions exist. |
| 261 | `            o.append(f'<details><summary>The {len(longlow)} repetitions below {lim} passes with an interval of 6 s or longer</summary><ul>'` | Adds a part that the reader can unfold. Its title gives the number of these repetitions. |
| 262 | `                     + ''.join(f"<li>Step {x['step']}, launch <code>{e(x['tag'])}</code>, kernel {e(x['kernel'])}, repetition {x['rep']}: {fx(x['passes_per_thread'], 1)} passes per thread.</li>" for x in longlow) + '</ul></details>')` | Continues line 261: one list item per repetition with its step, launch, kernel, repetition number and passes per thread. |
| 263 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `qrow_name`: the chart row of one q value (lines 266 to 279)

| Line | Source | Explanation |
|---:|---|---|
| 266 | `def qrow_name(r):` | Starts the function `qrow_name`. It gives the name of the chart row to which one q row of the json file belongs. |
| 267 | `    k = r['tag'].rsplit('-r', 1)[0]` | `k`: the kernel name from the tag: the part before the last `-r`. |
| 268 | `    if r['step'] in ('A1', 'A2'):` | A row of step A1 or A2. |
| 269 | `        return f"{r['step']} {KNAME.get(k, k)}"` | The name is the step and the printed kernel name, for example `A1 old read`. |
| 270 | `    if r['step'] == 'A3':` | A row of step A3. |
| 271 | `        b = 'one buffer' if r['tag'].startswith('onebuf') else 'two buffers'` | `b`: the words `one buffer` when the tag starts with `onebuf`, and `two buffers` in the other case. |
| 272 | `        ms = r['tag'].split('-')[1][2:]` | `ms`: the interval length in ms from the tag: the second part between hyphens, without its first two letters `ms`. |
| 273 | `        return f"A3 old read, {b}, {int(ms)/1000:g} s" if r['kernel'] == 'read' else 'A3 write and copy rows'` | For a read row the name is `A3 old read`, the buffer words and the interval length in seconds. Every other row of A3 gets the name `A3 write and copy rows`. The analysis script leaves those rows out of `q.rows`, so this name does not occur in the chart. |
| 274 | `    if r['step'] == 'A4':` | A row of step A4. |
| 275 | `        k = r['tag'].rsplit('-', 1)[0]` | `k`: the kernel name from the tag: the part before the last hyphen. |
| 276 | `        return f"A4 {KNAME.get(k, k)}, all counts"` | The name is `A4`, the printed kernel name and the words `all counts`. So all thread counts of a kernel share one chart row. |
| 277 | `    return r['step']` | Every other step: the name is the step. |

### Function `sec_q`: the distribution of q and the test of the two groups (lines 280 to 350)

| Line | Source | Explanation |
|---:|---|---|
| 280 | `def sec_q(s):` | Starts the function `sec_q`. It builds the section on the distribution of q over all repetitions with many threads. |
| 281 | `    d = s['q']['decision']; lim = s['limits']` | `d`: the decision of the test of the two groups. `lim`: the limits. Both come from the json file. |
| 282 | `    o = ['<h2 id="q">Distribution of q over all repetitions with many threads</h2>',` | `o`: the pieces of the section, starting with its heading. |
| 283 | `         f"<p>q is the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one repetition. "` | Text of the page: the definition of q. It is the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile, in one repetition. |
| 284 | `         f"The provisional rule of the handoff calls a repetition split if q is below {lim['q_split_below']}, uniform if q is above {lim['q_uniform_above']}, and between otherwise [Ref2]. "` | Text of the page: the provisional rule of the handoff note, with the two limits from the json file: split below 0.65, uniform above 0.85, between in every other case. |
| 285 | `         "The handoff asks to look at the distribution first. If q does not fall into two groups, the labels are not used [Ref2].</p>"]` | Text of the page: the handoff note asks to look at the distribution first. If q does not fall into two groups, the labels are not used. |
| 286 | `    if not s['q']['rows']:` | Tests whether the json file has no q row. |
| 287 | `        return '\n'.join(o) + missing('No repetition with per-thread lines is in the result folders, so q cannot be computed. The measurement that is missing: steps A1 to A4 with <code>--per-thread</code>.')` | Returns the heading and the texts with an `Insufficient data` notice: q cannot be computed, and the steps A1 to A4 with `--per-thread` would give it. |
| 288 | `    groups = {}` | `groups`: the q values per chart row. |
| 289 | `    for r in s['q']['rows']:` | Loop over the q rows. |
| 290 | `        groups.setdefault(qrow_name(r), []).append((r['q'], f"{r['step']} {r['tag']} {r['kernel']} repetition {r['rep']}: q {fx(r['q'], 3)}"))` | Adds the q value to its chart row (line 266), with a hover text: step, tag, kernel, repetition and q with 3 decimals. |
| 291 | `    rows = [(n, p, f"{len(p)} repetitions: {fx(min(v for v, _ in p), 2)}" + (f" to {fx(max(v for v, _ in p), 2)}" if max(v for v, _ in p) - min(v for v, _ in p) >= 0.005 else '')) for n, p in groups.items()]` | `rows`: one chart row per name: the name, the points, and a label with the number of repetitions and the lowest q. The highest q is added when the two differ by at least 0.005. |
| 292 | `    o.append(strip_chart(rows, 0, 1, [0, 0.25, 0.5, 0.65, 0.85, 1], 'q (no unit: a ratio of two rates)', 'q of every repetition, one row per step and kernel',` | Adds the chart (line 89): q from 0 to 1 with tick marks at 0, 0.25, 0.5, 0.65, 0.85 and 1, an axis title that says that q is a ratio without unit, and a description for screen readers. |
| 293 | `                         band=(lim['q_split_below'], lim['q_uniform_above'], 'between'), nd=2))` | Continues the call: the grey band from 0.65 to 0.85 with the name `between`. |
| 294 | `    o.append('<p class="cap">One dot is one repetition. Dots are moved a little up or down so that equal values stay visible. The grey band is the range that the rule calls "between". Each row is labelled with its lowest and highest q.</p>')` | Adds the caption of the chart: one dot is one repetition, dots are moved a little up or down, the grey band is the range `between`, and each row carries its lowest and highest q. |
| 295 | `    gmin = lim.get('q_gap_min', 0.10)` | `gmin`: the smallest distance of the test from the json file, or 0.10 when the file does not give it. |
| 296 | `    if d['labels_usable']:` | The case that the labels are usable. |
| 297 | `        o.append(f"<p class=\"take\">Observed in screening: the {d['n']} values of q fall into two groups. {d['n_lower']} values lie from {fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, and {d['n_upper']} values lie from {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}. "` | Adds a highlighted statement, with the words `Observed in screening`: the q values fall into two groups. It gives the size and the range of each group. |
| 298 | `                 f"No value lies between {fx(d['gap_from'], 2)} and {fx(d['gap_to'], 2)}. The lower group is below {lim['q_split_below']} and the upper group is above {lim['q_uniform_above']}. So this page uses the labels split and uniform.</p>")` | Continues the statement: no value lies between the two ends of the distance, the lower group is below 0.65 and the upper group is above 0.85. So the page uses the labels. |
| 299 | `    else:` | The case that the labels are not usable. |
| 300 | `        t = f"Observed in screening: the {d['n']} values of q do not fall into two groups by the test below. "` | `t`: a statement that the q values do not fall into two groups by the test. |
| 301 | `        if 'gap' in d:` | Only when the test computed a distance. It does so with at least 4 values. |
| 302 | `            t += f"The values lie from {fx(d['q_min'], 2)} to {fx(d['q_max'], 2)}. The rule alone would give {d['n_split']} split, {d['n_between']} between and {d['n_uniform']} uniform. "` | Adds the lowest and the highest q, and the counts that the rule alone would give: split, between and uniform. |
| 303 | `            t += f"The largest distance between two neighbouring q values is {fx(d['gap'], 3)} (from {fx(d['gap_from'], 3)} to {fx(d['gap_to'], 3)}). "` | Adds the largest distance between two neighbouring q values with 3 decimals, and the two values at its ends. |
| 304 | `            if d['gap'] < gmin:` | Only when the distance is below the smallest accepted distance. |
| 305 | `                t += f"The test asks for at least {fx(gmin, 2)}. "` | Adds the sentence that the test asks for at least that distance. |
| 306 | `            if min(d['n_lower'], d['n_upper']) < 2:` | Only when one group has fewer than 2 values. |
| 307 | `                t += 'One side of the largest distance has fewer than 2 values. '` | Adds the sentence that says so. |
| 308 | `            wl, wu = d['lower_max'] - d['lower_min'], d['upper_max'] - d['upper_min']` | `wl`: the width of the lower group. `wu`: the width of the upper group. |
| 309 | `            if d['gap'] <= wu:` | Only when the distance is not larger than the width of the upper group. |
| 310 | `                t += f"The values above the distance span {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}, which is wider than the distance. "` | Adds the range of the values above the distance, and that it is wider than the distance. |
| 311 | `            if d['gap'] <= wl:` | Only when the distance is not larger than the width of the lower group. |
| 312 | `                t += f"The values below the distance span {fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, which is wider than the distance. "` | Adds the same for the values below the distance. |
| 313 | `            if d['two_groups'] and not d['limits_fit']:` | Only when q falls into two groups that do not fit the limits. |
| 314 | `                t += f"The two groups do not lie on the two sides of the limits {lim['q_split_below']} and {lim['q_uniform_above']}. "` | Adds the sentence that the two groups do not lie on the two sides of the limits. |
| 315 | `        else:` | The case without a computed distance. |
| 316 | `            t += f"Reason: {e(d['reason'])}. "` | Adds the reason text of the analysis script. |
| 317 | `        t += "So this page does not use the labels split and uniform. It gives q itself."` | Ends the statement with its consequence for the page: no labels, q itself is given. |
| 318 | `        o.append(f'<p class="take">{t}</p>')` | Adds the statement as a highlighted paragraph. |
| 319 | `    g = s['q'].get('groups')` | `g`: the description of where the q values lie (the function `q_groups` of the analysis script). |
| 320 | `    if g and not d['labels_usable']:` | The list of lines 321 to 339 is printed only when the labels are not usable. |
| 321 | `        li = []` | `li`: the list items, empty at first. |
| 322 | `        if g['below_split']:` | Only when q values below 0.65 exist. |
| 323 | `            li.append(f"<li>The {sum(x['n'] for x in g['below_split'])} values below {lim['q_split_below']} are: "` | Adds an item: the number of q values below 0.65. |
| 324 | `                      + ', '.join(f"{x['n']} of {KNAME.get(x['kname'], x['kname'])} at {x['count']} threads" for x in g['below_split']) + '.</li>')` | Continues the item: how many of them belong to which kernel at which thread count. |
| 325 | `        a, b = g['read_old'], g['load_only_read']` | `a`: the summary for the old read kernel at 64+56 threads. `b`: the summary for the new read kernel and `asmread` together. |
| 326 | `        if a['n'] and b['n']:` | Only when both summaries have repetitions. |
| 327 | `            t = (f"<li>For the read kernels at {g['count']} threads alone: q is {rtxt(a['q'], 3)} for old read ({pl(a['n'], 'repetition', 'repetitions')} of all steps). "` | `t`: an item for the read kernels at 64+56 threads alone: the range of q for the old read kernel, with 3 decimals, and its number of repetitions. |
| 328 | `                 f"It is {rtxt(b['q'], 3)} for new read and asm read ({pl(b['n'], 'repetition', 'repetitions')}). ")` | Continues the item: the same for the new read kernel and `asmread`. |
| 329 | `            if g['ranges_separate']:` | The case that the two ranges do not overlap. |
| 330 | `                lo_, hi_ = sorted([a['q'], b['q']], key=lambda z: z['min'])` | `lo_` and `hi_`: the two ranges, the one with the lower values first. |
| 331 | `                t += f"The two ranges do not overlap: no q of these kernels at this count lies between {fx(lo_['max'], 3)} and {fx(hi_['min'], 3)}."` | Adds the sentence that no q of these kernels at this count lies between the highest value of the lower range and the lowest value of the upper range. |
| 332 | `            else:` | The case that the ranges overlap. |
| 333 | `                t += 'The two ranges overlap.'` | Adds the sentence for that case. |
| 334 | `            li.append(t + '</li>')` | Closes the item and adds it. |
| 335 | `        if g['between']:` | Only when q values from 0.65 to 0.85 exist. |
| 336 | `            li.append(f"<li>The {sum(x['n'] for x in g['between'])} values from {lim['q_split_below']} to {lim['q_uniform_above']} come from: "` | Adds an item: the number of these q values. |
| 337 | `                      + ', '.join(f"{KNAME.get(x['kname'], x['kname'])} in {x['step']} ({x['n']})" for x in g['between']) + '.</li>')` | Continues the item: from which kernel and step they come, with the count of each. |
| 338 | `        li.append('<li>The handoff asks for the test over all repetitions of Part A [Ref2]. So the labels stay unused for every step and kernel on this page.</li>')` | Adds a fixed item with the reason why the labels stay unused for every step and kernel: the handoff note asks for one test over all repetitions of Part A. |
| 339 | `        o.append('<p>Where the values lie, observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `Where the values lie, observed in screening:`. |
| 340 | `    o.append('<p>The handoff gives no test for "two groups". The analysis script uses this one (choice C2) [Ref5]:</p><ul>'` | Adds a paragraph: the handoff note gives no test for two groups, and the analysis script uses choice C2. A list of the test follows. |
| 341 | `             '<li>The q values are sorted. The largest distance between two neighbours divides them into a lower and an upper group.</li>'` | Text of the page: item 1 of the test, the split of the sorted q values at the largest distance between two neighbours. |
| 342 | `             f'<li>The values count as two groups if three conditions hold. Each group has at least 2 values. The distance is at least {fx(gmin, 2)}. The distance is larger than the width of each group.</li>'` | Text of the page: item 2, the three conditions for two groups, with the smallest distance from the json file. |
| 343 | `             f"<li>The labels are used only if, in addition, the lower group is below {lim['q_split_below']} and the upper group is above {lim['q_uniform_above']}.</li></ul>")` | Text of the page: item 3. The labels are used only when the lower group is below 0.65 and the upper group is above 0.85. |
| 344 | `    left = s['q'].get('rows_left_out') or []` | `left`: the q rows that the analysis script left out. |
| 345 | `    if left:` | Only when such rows exist. |
| 346 | `        o.append(f"<p>{len(left)} repetitions are not in this chart and not in the test. They are the write and copy repetitions of the A3 processes with two buffers. "` | Adds a paragraph: how many repetitions are not in the chart and not in the test. They are the write and copy repetitions of the A3 processes with two buffers. |
| 347 | `                 'The handoff says to compare only the read rows of A3 [Ref2]. They are listed in the file <code>partA-summary.json</code> under the key <code>q.rows_left_out</code> [Ref4].</p>')` | Continues the paragraph: the handoff note says to compare only the read rows of A3, and the rows are listed in the json file under `q.rows_left_out`. |
| 348 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `mesh_pairs_chart`: median thread rate of the two meshes (lines 351 to 397)

| Line | Source | Explanation |
|---:|---|---|
| 351 | `def mesh_pairs_chart(s):` | Starts the function `mesh_pairs_chart`. It draws a chart with one row per kernel and step. Each row shows two points: the median thread rate on mesh 0 and the median thread rate on mesh 1. |
| 352 | `    rows = []` | `rows`: the rows of the chart, empty at first. |
| 353 | `    for k in KORDER:` | Loop over the six kernels in the order of the page. |
| 354 | `        for st_, lab in (('A1', '0.5 s'), ('A2', 'long')):` | Loop over the steps A1 and A2. The second value of each pair, `lab`, is not used. |
| 355 | `            if k in s[st_] and s[st_][k]['mesh0_median']['n']:` | Takes a kernel and step only when thread rates of mesh 0 exist. |
| 356 | `                x = s[st_][k]` | `x`: the entry of the kernel in this step. |
| 357 | `                ms = x['min_ms']` | `ms`: its interval length in ms. |
| 358 | `                rows.append((f"{KNAME[k]}, {ms/1000:g} s ({st_})", x['mesh0_median']['median'], x['mesh1_median']['median'] if x['mesh1_median']['n'] else None, k))` | Adds a row: a name with the kernel, the interval length in seconds and the step. Then the value for mesh 0 and the value for mesh 1, or `None` without threads on mesh 1. Each value is the median over the repetitions of the median thread rate of the mesh in one repetition, in GB/s. |
| 359 | `    if not rows:` | Tests whether the chart has no row. |
| 360 | `        return ''` | Returns an empty text: no chart is drawn. |
| 361 | `    W, L, R, rh, top = 780, 190, 60, 34, 20` | Sizes in drawing units: the width 780, a left margin of 190, a right margin of 60, a row height of 34 and a top margin of 20. |
| 362 | `    H = top + len(rows) * rh + 48; PW = W - L - R` | `H`: the height. `PW`: the width of the plot area, 530 units. |
| 363 | `    xmax = max(max(a, b or 0) for _, a, b, _ in rows) * 1.12` | `xmax`: the right end of the axis: the highest value of all rows times 1.12. |
| 364 | `    step = 1 if xmax > 4 else 0.5` | `step`: the distance of the grid lines: 1 GB/s when the axis is longer than 4 GB/s, and 0.5 GB/s when it is not. |
| 365 | `    x = lambda v: L + v / xmax * PW` | `x`: a function that turns a rate into a horizontal position. The axis starts at 0. |
| 366 | `    o = svg_open(W, H, 'Median thread rate on mesh 0 and on mesh 1, one row per kernel and interval')` | `o`: the drawing, with its description for screen readers. |
| 367 | `    t = 0` | `t`: the value of the first grid line, 0. |
| 368 | `    while t <= xmax:` | Loop over the grid lines up to the right end of the axis. |
| 369 | `        o.append(f'<line x1="{fx(x(t), 1)}" y1="{top-6}" x2="{fx(x(t), 1)}" y2="{H-48}" stroke="{GRID}"/><text x="{fx(x(t), 1)}" y="{H-32}" text-anchor="middle" class="ax">{t:g}</text>')` | Draws a light grey vertical grid line and writes its value under the plot. |
| 370 | `        t += step` | Goes to the next grid value. |
| 371 | `    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">median rate of one thread, GB/s (axis starts at 0)</text>')` | Writes the axis title. It names the unit GB/s and says that the axis starts at 0. |
| 372 | `    prev = None` | `prev`: the kernel of the row before, `None` at first. |
| 373 | `    for i, (name, a, b, k) in enumerate(rows):` | Loop over the rows. |
| 374 | `        y = top + i * rh + rh / 2` | `y`: the vertical centre of the row. |
| 375 | `        if prev and prev != k:` | Tests whether the kernel differs from the kernel of the row before. |
| 376 | `            o.append(f'<line x1="10" y1="{fx(y-rh/2, 1)}" x2="{W-R}" y2="{fx(y-rh/2, 1)}" stroke="{GRID}"/>')` | Draws a light grey horizontal line between the rows of two kernels. |
| 377 | `        prev = k` | Remembers the kernel. |
| 378 | `        o.append(f'<text x="{L-10}" y="{fx(y+4, 1)}" text-anchor="end" class="lab">{e(name)}</text>')` | Writes the row name at the left. |
| 379 | `        if b is None:` | The case without a value for mesh 1. |
| 380 | `            o.append(marker(x(a), y, 'circle', C0, f'{name}: mesh 0 {fx(a, 2)} GB/s'))` | Draws one blue circle for mesh 0, with a hover text. |
| 381 | `            o.append(f'<text x="{fx(x(a)+10, 1)}" y="{fx(y+4, 1)}" class="val">{fx(a, 2)}</text>'); continue` | Writes the value at its right, with 2 decimals. `continue` goes to the next row. |
| 382 | `        if abs(x(a) - x(b)) < 14:          # the two dots would cover each other: draw them one above the other, with one label` | The case that the two points lie less than 14 units apart. By the comment the two dots would cover each other. They are drawn one above the other, with one label. |
| 383 | `            o.append(marker(x(a), y - 6, 'circle', C0, f'{name}: mesh 0, {fx(a, 2)} GB/s', r=4))` | Draws the blue circle of mesh 0, 6 units above the row centre. |
| 384 | `            o.append(marker(x(b), y + 6, 'diamond', C1, f'{name}: mesh 1, {fx(b, 2)} GB/s', r=4))` | Draws the orange diamond of mesh 1, 6 units below the row centre. |
| 385 | `            o.append(f'<text x="{fx(max(x(a), x(b))+12, 1)}" y="{fx(y+4, 1)}" class="val">mesh 0 {fx(a, 2)}, mesh 1 {fx(b, 2)}</text>'); continue` | Writes one label at the right of both points, with the two values. `continue` goes to the next row. |
| 386 | `        o.append(f'<line x1="{fx(x(a), 1)}" y1="{y}" x2="{fx(x(b), 1)}" y2="{y}" stroke="#8a8984" stroke-width="2"/>')` | The normal case: draws a grey line between the two points. A long line means that the threads of the two meshes ran at different rates. |
| 387 | `        o.append(marker(x(a), y, 'circle', C0, f'{name}: mesh 0, {fx(a, 2)} GB/s'))` | Draws the blue circle of mesh 0. |
| 388 | `        o.append(marker(x(b), y, 'diamond', C1, f'{name}: mesh 1, {fx(b, 2)} GB/s'))` | Draws the orange diamond of mesh 1. |
| 389 | `        lo, hi = (a, b) if a <= b else (b, a)` | `lo` and `hi`: the lower and the higher of the two values. |
| 390 | `        o.append(f'<text x="{fx(x(lo)-11, 1)}" y="{fx(y+4, 1)}" text-anchor="end" class="val">{fx(lo, 2)}</text>')` | Writes the lower value at the left of the left point. |
| 391 | `        o.append(f'<text x="{fx(x(hi)+11, 1)}" y="{fx(y+4, 1)}" class="val">{fx(hi, 2)}</text>')` | Writes the higher value at the right of the right point. |
| 392 | `    o.append('</svg>')` | Closes the drawing. |
| 393 | `    leg = (f'<p><span class="lg"><i style="background:{C0}"></i>mesh 0 (CPUs 0 to 63), circle</span>'` | `leg`: the legend above the chart: a blue dot with the text for mesh 0 (CPUs 0 to 63, circle). |
| 394 | `           f'<span class="lg"><i style="background:{C1};border-radius:0;transform:rotate(45deg)"></i>mesh 1 (CPUs 64 to 119), diamond</span></p>')` | Continues the legend: an orange square turned by 45 degrees with the text for mesh 1 (CPUs 64 to 119, diamond). |
| 395 | `    return leg + '\n'.join(o)` | Returns the legend and the drawing. |

### Function `cpu_panels`: rate of each thread against its CPU (lines 398 to 437)

| Line | Source | Explanation |
|---:|---|---|
| 398 | `def cpu_panels(s, st_):` | Starts the function `cpu_panels`. For one step it draws one small panel per kernel: the rate of each thread against the number of its CPU. |
| 399 | `    """Small multiples: rate of each thread against its CPU, median over the repetitions of both rounds."""` | Text of the function: the chart is a set of small panels, and each point is a median over the repetitions of both rounds. |
| 400 | `    data = {}` | `data`: the thread rates per kernel and CPU. |
| 401 | `    for r in s['thread_rates'].get(st_, []):` | Loop over the repetitions of the step in the list `thread_rates` of the json file. |
| 402 | `        k = r['tag'].rsplit('-r', 1)[0]` | `k`: the kernel name from the tag: the part before the last `-r`. |
| 403 | `        for cpu, rate in r['threads']:` | Loop over the pairs of CPU and thread rate of the repetition. |
| 404 | `            data.setdefault(k, {}).setdefault(cpu, []).append(rate)` | Adds the rate to the list of this kernel and CPU. With 2 rounds of 3 repetitions a CPU gets 6 rates per kernel. |
| 405 | `    ks = [k for k in KORDER if k in data]` | `ks`: the kernels that have rates, in the order of the page. |
| 406 | `    if not ks:` | Tests whether no kernel has rates. |
| 407 | `        return ''` | Returns an empty text: no chart is drawn. |
| 408 | `    pw, ph, gx, gy, L, top = 215, 110, 40, 72, 60, 26` | Sizes in drawing units: a panel is 215 wide and 110 high. The gap between panels is 40 across and 72 down. The left margin is 60 and the top margin 26. |
| 409 | `    cols = 3; rows = (len(ks) + cols - 1) // cols` | `cols`: 3 panels per row. `rows`: the number of panel rows that the kernels need. |
| 410 | `    W = L + cols * pw + (cols - 1) * gx + 10; H = top + rows * (ph + gy)` | `W` and `H`: the width and the height of the whole drawing. |
| 411 | `    o = svg_open(W, H, f'Rate of each thread against its CPU number, step {st_}')` | `o`: the drawing, with a description for screen readers that names the step. |
| 412 | `    for i, k in enumerate(ks):` | Loop over the kernels. `i` is the number of the panel, counted from 0. |
| 413 | `        med = {c: st.median(v) for c, v in data[k].items()}` | `med`: for each CPU, the median of its thread rates over all repetitions of the kernel, in GB/s. |
| 414 | `        row_ks = ks[(i // cols) * cols:(i // cols) * cols + cols]` | `row_ks`: the kernels whose panels stand in the same row as this panel. |
| 415 | `        ymax = max(st.median(v) for kk in row_ks for v in data[kk].values()) * 1.15` | `ymax`: the top of the vertical axis: the highest of these medians in the panels of the row, times 1.15. So the three panels of one row share one scale. |
| 416 | `        x0 = L + (i % cols) * (pw + gx); y0 = top + (i // cols) * (ph + gy)` | `x0` and `y0`: the left edge and the top edge of the panel. |
| 417 | `        X = lambda c: x0 + c / 119 * pw` | `X`: a function that turns a CPU number into a horizontal position. CPU 0 lies at the left edge and CPU 119 at the right edge. |
| 418 | `        Y = lambda v: y0 + ph - v / ymax * ph` | `Y`: a function that turns a rate into a vertical position. A rate of 0 lies at the bottom edge. |
| 419 | `        o.append(f'<rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" fill="none" stroke="{GRID}"/>')` | Draws the frame of the panel in light grey. |
| 420 | `        o.append(f'<line x1="{fx(X(63.5), 1)}" y1="{y0}" x2="{fx(X(63.5), 1)}" y2="{y0+ph}" stroke="{MUTED}" stroke-dasharray="3 3"/>')` | Draws a dashed dark grey vertical line between CPU 63 and CPU 64. It marks the border between mesh 0 and mesh 1. |
| 421 | `        o.append(f'<text x="{x0}" y="{y0-8}" class="lab">{e(KNAME[k])}</text>')` | Writes the printed kernel name above the panel. |
| 422 | `        for tv, tl in ((0, '0'), (ymax / 1.15, f'{fx(ymax/1.15, 2)}')):` | Loop over the two labels of the vertical axis: 0, and the highest median of the row with 2 decimals. |
| 423 | `            o.append(f'<text x="{x0-5}" y="{fx(Y(tv)+(4 if tv else 0), 1)}" text-anchor="end" class="ax">{tl}</text>')` | Writes the label at the left of the panel, at the height of its value. |
| 424 | `        if i % cols == 0:` | Only for the first panel of each row. |
| 425 | `            o.append(f'<text x="10" y="{y0+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 10 {y0+ph/2})">thread rate, GB/s</text>')` | Writes the title of the vertical axis, turned by 90 degrees: the thread rate in GB/s. |
| 426 | `        for c, lab in ((0, 'CPU 0'), (64, '64'), (119, '119')):` | Loop over three labels of the horizontal axis: `CPU 0`, `64` and `119`. |
| 427 | `            o.append(f'<text x="{fx(X(c), 1)}" y="{y0+ph+13}" text-anchor="middle" class="ax">{lab}</text>')` | Writes the label under the panel, at the position of that CPU. |
| 428 | `        for c, v in sorted(med.items()):` | Loop over the CPUs in rising order. |
| 429 | `            o.append(f'<circle cx="{fx(X(c), 1)}" cy="{fx(Y(v), 1)}" r="2" fill="{C0 if c < 64 else C1}"><title>CPU {c}: {fx(v, 2)} GB/s</title></circle>')` | Draws one dot per CPU with the radius 2 at the median rate of its thread. The dot is blue for a CPU below 64 and orange for the others. The hover text gives the CPU and the rate. |
| 430 | `        x = s[st_].get(k, {})` | `x`: the summary of this kernel in this step. |
| 431 | `        for j, m in enumerate(m for m in (0, 1) if x.get(f'mesh{m}_median', {}).get('n')):` | Loop over the meshes that have thread rates. `j` counts the lines of text. |
| 432 | `            t = f"mesh {m}: {fx(x[f'mesh{m}_median']['median'], 2)} GB/s"` | `t`: the text `mesh 0:` or `mesh 1:` with the median thread rate of the mesh in GB/s. It is the median over the repetitions of the median over the threads. |
| 433 | `            o.append(f'<text x="{x0}" y="{y0+ph+28+14*j}" class="val">{e(t)}</text>')` | Writes the text under the panel, one line per mesh. |
| 434 | `    o.append('</svg>')` | Closes the drawing. |
| 435 | `    return '\n'.join(o)` | Returns the drawing as one text. |

### Helpers for the fastest half and the faster mesh (lines 438 to 469)

| Line | Source | Explanation |
|---:|---|---|
| 438 | `def fh_one(r):` | Starts the function `fh_one`. It prints the number of threads of mesh 0 in the fastest half of one repetition. |
| 439 | `    """Count of mesh-0 threads in the fastest half of one repetition. A range comes from equal rates at the limit (choice C3)."""` | Text of the function: a range comes from equal rates at the limit of the half (choice C3 of the analysis script). |
| 440 | `    f = r.get('fastest_half')` | `f`: the entry `fastest_half` of the repetition. |
| 441 | `    if not f:` | Tests whether the entry is missing. |
| 442 | `        return '-'` | Returns a hyphen in that case. |
| 443 | `    lo, hi = f['mesh0']` | `lo` and `hi`: the lowest and the highest possible count of mesh 0. |
| 444 | `    return f'{lo}' if lo == hi else f'{lo} to {hi}'` | Returns one number when the two are equal, and the form `lowest to highest` when they differ. |
| 447 | `def fh_reps(reps):` | Starts the function `fh_reps`. It prints these counts for a list of repetitions. |
| 448 | `    """The counts of all repetitions, in order, with the size of the half: '4, 4, 6 of 60'."""` | Text of the function: the counts of all repetitions in order, with the size of the half, for example `4, 4, 6 of 60`. |
| 449 | `    v = [r for r in reps if r.get('fastest_half')]` | `v`: the repetitions that have an entry `fastest_half`. |
| 450 | `    if not v:` | Tests whether there is none. |
| 451 | `        return '-'` | Returns a hyphen in that case. |
| 452 | `    return ', '.join(fh_one(r) for r in v) + f" of {v[0]['fastest_half']['n_half']}"` | Returns the counts joined with commas, then the word `of` and the size of the half of the first repetition. |
| 455 | `def fh_txt(reps):` | Starts the function `fh_txt`. No line of the file calls it. |
| 456 | `    return fh_reps(reps)` | Returns the same text as `fh_reps`. |
| 459 | `def faster_mesh(reps):` | Starts the function `faster_mesh`. It sorts repetitions by the mesh that has the higher median thread rate. |
| 460 | `    """Repetitions grouped by the mesh with the higher median thread rate. Returns {'0': [...], '1': [...], '=': [...]}."""` | Text of the function: the result has three lists, under the keys `0`, `1` and `=`. |
| 461 | `    out = {'0': [], '1': [], '=': []}` | `out`: the three lists, empty at first. |
| 462 | `    for r in reps:` | Loop over the repetitions. |
| 463 | `        a, b = r['mesh0']['median'], r['mesh1']['median']` | `a` and `b`: the median thread rate of mesh 0 and of mesh 1 in this repetition. |
| 464 | `        if a is None or b is None:` | Tests whether one of the two is missing. |
| 465 | `            continue` | Such a repetition is skipped. |
| 466 | `        out['0' if a > b else '1' if b > a else '='].append(r)` | Adds the repetition to the list `0` when mesh 0 is higher, to `1` when mesh 1 is higher, and to `=` when the two medians are equal. |
| 467 | `    return out` | Returns the three lists. |

### Texts on a changing faster mesh and on the write totals (lines 470 to 509)

| Line | Source | Explanation |
|---:|---|---|
| 470 | `def mesh_change_txt(reps):` | Starts the function `mesh_change_txt`. It builds sentences for a kernel or thread count whose faster mesh is not the same in all repetitions. |
| 471 | `    """Sentences for a kernel or count whose faster mesh is not the same in all repetitions. Empty if it is the same."""` | Text of the function: the result is empty when the faster mesh is the same in all repetitions. |
| 472 | `    g = faster_mesh(reps)` | `g`: the repetitions sorted by the faster mesh (line 459). |
| 473 | `    if not g['0'] or not g['1']:` | Tests whether one of the two meshes was never the faster one. |
| 474 | `        return ''` | Returns an empty text in that case. |
| 475 | `    n = len(g['0']) + len(g['1']) + len(g['='])` | `n`: the number of repetitions with both medians. |
| 476 | `    t = []` | `t`: the sentences, empty at first. |
| 477 | `    for m in ('0', '1'):` | Loop over the two meshes. |
| 478 | `        other = '1' if m == '0' else '0'` | `other`: the number of the other mesh. |
| 479 | `        part = f"The median thread rate was higher on mesh {m} in {len(g[m])} of {n} repetitions"` | `part`: a sentence that says in how many of the `n` repetitions the median thread rate was higher on this mesh. |
| 480 | `        if len(g[m]) <= 2:` | Only when this was the case in at most 2 repetitions. |
| 481 | `            part += ' (' + '; '.join(f"launch {r['tag']}, repetition {r['rep']}: {fx(r['mesh' + m]['median'])} against {fx(r['mesh' + other]['median'])} GB/s, "` | Adds, in brackets, each such repetition: the launch, the repetition number, and the two medians in GB/s. |
| 482 | `                                     f"fastest half on mesh 0: {fh_reps([r])}" for r in g[m]) + ')'` | Continues line 481: the count of mesh 0 in the fastest half of that repetition. |
| 483 | `        t.append(part + '.')` | Ends the sentence and adds it. |
| 484 | `    return ' '.join(t)` | Returns the sentences as one text. |
| 487 | `def write_hi_lo(s):` | Starts the function `write_hi_lo`. For each write kernel of A1 and A2 it compares the repetition with the highest total with the one with the lowest total. |
| 488 | `    """For each write kernel of A1 and A2: the repetition with the highest total against the one with the lowest."""` | Text of the function: the same in one sentence. |
| 489 | `    out = []` | `out`: one entry per kernel and step. |
| 490 | `    for st_ in ('A1', 'A2'):` | Loop over the steps A1 and A2. |
| 491 | `        for k in ('write_old', 'write_new', 'asmwrite'):` | Loop over the three write kernels. |
| 492 | `            rr = s[st_].get(k, {}).get('reps', [])` | `rr`: the repetitions of the kernel in this step, or an empty list. |
| 493 | `            rr = [r for r in rr if r['mesh0']['sum'] is not None and r['mesh1']['sum'] is not None]` | Keeps the repetitions that have a sum of thread rates for both meshes. |
| 494 | `            if len(rr) < 2: continue` | A kernel with fewer than 2 such repetitions is skipped. |
| 495 | `            hi = max(rr, key=lambda r: r['total_GBps']); lo = min(rr, key=lambda r: r['total_GBps'])` | `hi`: the repetition with the highest total. `lo`: the repetition with the lowest total. |
| 496 | `            out.append(dict(step=st_, k=k, n=len(rr), lo=lo['total_GBps'], hi=hi['total_GBps'], d0=hi['mesh0']['sum'] - lo['mesh0']['sum'], d1=hi['mesh1']['sum'] - lo['mesh1']['sum']))` | Adds an entry: the step, the kernel, the number of repetitions, the lowest and the highest total. `d0`: the sum of the thread rates of mesh 0 in the highest repetition minus that in the lowest. `d1`: the same for mesh 1. Both are in GB/s. |
| 497 | `    return out` | Returns the entries. |
| 500 | `def write_hi_lo_txt(w):` | Starts the function `write_hi_lo_txt`. It turns these entries into two or three sentences. |
| 501 | `    n0 = sum(1 for x in w if x['d0'] > x['d1']); n1 = sum(1 for x in w if x['d1'] > x['d0'])` | `n0`: the number of entries in which the change on mesh 0 is larger than the change on mesh 1. `n1`: the number with the larger change on mesh 1. |
| 502 | `    both = sum(1 for x in w if x['d0'] > 0 and x['d1'] > 0)` | `both`: the number of entries in which both changes are above 0. |
| 503 | `    t = (f"In {both} of the {pl(len(w), 'case', 'cases')} (kernel and step) the sum of the thread rates was higher on both meshes in the repetition with the highest total. "` | `t`: the first sentence: in how many of the cases the sum of the thread rates was higher on both meshes in the repetition with the highest total. A case is one kernel in one step. |
| 504 | `         f"The larger part of the change was on mesh 0 in {n0} and on mesh 1 in {n1}.")` | Continues `t`: on which mesh the larger part of the change was, with the two counts. |
| 505 | `    if n0 and n1:` | Only when each mesh had the larger part at least once. |
| 506 | `        t += ' So no single mesh was observed as the source of the higher write totals.'` | Adds the sentence that no single mesh was observed as the source of the higher write totals. |
| 507 | `    return t` | Returns the text. |

### Function `sec_a12`: the section on the steps A1 and A2 (lines 510 to 595)

| Line | Source | Explanation |
|---:|---|---|
| 510 | `def sec_a12(s):` | Starts the function `sec_a12`. It builds the section on the steps A1 and A2: the six kernels with 64 threads on mesh 0 and 56 on mesh 1, with a short and with a long interval. |
| 511 | `    o = ['<h2 id="a1">A1 and A2: six kernels with 64+56 threads, short and long interval</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 512 | `    if not s['A1'] and not s['A2']:` | Tests whether neither step has data. |
| 513 | `        return '\n'.join(o) + missing('Steps A1 and A2 have no usable data. The measurement that is missing: the 12 launches of A1 and the 12 launches of A2 of <code>run_partA.sh</code>.')` | Returns the heading with an `Insufficient data` notice that names the missing 12 launches of each step. |
| 514 | `    for st_ in ('A1', 'A2'):` | Loop over the two steps. |
| 515 | `        if not s[st_]:` | Tests whether this step has no data. |
| 516 | `            o.append(missing(f'Step {st_} has no usable data. The measurement that is missing: the 12 launches of step {st_}.'))` | Adds an `Insufficient data` notice for the step. |
| 517 | `    o.append('<h3>Median thread rate of each mesh</h3>')` | Adds the sub-heading of the first chart: the median thread rate of each mesh. |
| 518 | `    o.append(mesh_pairs_chart(s))` | Adds the chart of line 351. |
| 519 | `    o.append('<p class="cap">Each dot is the median over the repetitions of the median thread rate of one mesh. A long line between the two dots means that the threads of the two meshes ran at different rates.</p>')` | Adds its caption: each dot is the median over the repetitions of the median thread rate of one mesh, and a long line means different rates on the two meshes. |
| 520 | `    # generated statement on which mesh is fast` | Comment: the statements below, on which mesh is fast, are built from the data. |
| 521 | `    li = []; half = None; n1 = None` | `li`: the list items. `half` and `n1`: the size of the fastest half and the thread count of mesh 1, both unknown at first. |
| 522 | `    for st_ in ('A1', 'A2'):` | Loop over the two steps. |
| 523 | `        for k in KORDER:` | Loop over the six kernels. |
| 524 | `            if k not in s[st_]: continue` | A kernel without data in this step is skipped. |
| 525 | `            x = s[st_][k]` | `x`: the summary of the kernel in this step. |
| 526 | `            if not x['mesh1_median']['n']: continue` | A kernel without thread rates on mesh 1 is skipped. |
| 527 | `            a, b = x['mesh0_median']['median'], x['mesh1_median']['median']` | `a` and `b`: the median thread rate on mesh 0 and on mesh 1, each the median over the repetitions. |
| 528 | `            rel = ('The two rates were equal.' if fx(a) == fx(b) else` | `rel`: a sentence about the two rates. When both print the same with 2 decimals, it says that they were equal. |
| 529 | `                   f"The rate on mesh {'0' if a > b else '1'} was higher by {fx(abs(a-b), 2)} GB/s, which is {fx(abs(a-b)/min(a,b)*100, 0)} %.")` | Continues `rel`: in the other case it names the mesh with the higher rate, the difference in GB/s, and the difference in percent of the lower rate, without decimals. |
| 530 | `            f = next((r['fastest_half'] for r in x['reps'] if r['fastest_half']), None)` | `f`: the entry `fastest_half` of the first repetition that has one. |
| 531 | `            if f and half is None:` | Only at the first kernel that has such an entry. |
| 532 | `                half, n1 = f['n_half'], x['reps'][0]['mesh1']['n']` | Remembers the size of the fastest half and the number of threads on mesh 1. |
| 533 | `            li.append(f"<li>{st_}, {KNAME[k]}, {x['min_ms']/1000:g} s: the median thread rate was {fx(a, 2)} GB/s on mesh 0 and {fx(b, 2)} GB/s on mesh 1. {rel} "` | Adds an item: the step, the kernel and the interval length in seconds, the two median thread rates with 2 decimals, and the sentence `rel`. |
| 534 | `                      f"Threads of the fastest half on mesh 0, per repetition: {fh_reps(x['reps'])}. q was {rtxt(x['q'])}. {mesh_change_txt(x['reps'])}</li>")` | Continues the item: the count of mesh 0 in the fastest half for each repetition, the range of q, and the sentences of line 470 when the faster mesh changed. |
| 535 | `    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `Observed in screening:`. |
| 536 | `    if half is not None:` | Only when a fastest half was found. |
| 537 | `        o.append(f'<p>How to read the count of the fastest half. The fastest half is the {half} threads with the highest rates of one repetition. Mesh 1 has {n1} threads. '` | Adds a paragraph on how to read the count of the fastest half: the half is that many threads with the highest rates of one repetition, and mesh 1 has `n1` threads. |
| 538 | `                 + (f'So {half - n1} of {half} is the lowest possible count on mesh 0: all {n1} threads of mesh 1 are then in the fastest half. ' if half > n1 else '')` | Continues the paragraph, only when the half is larger than `n1`: the lowest possible count on mesh 0 is the half minus `n1`. All threads of mesh 1 are then in the fastest half. |
| 539 | `                 + f'{half} of {half} means that the fastest half is on mesh 0 only. One count is given for each repetition. '` | Continues the paragraph: what the full count means, and that the list gives one count per repetition. |
| 540 | `                 'A range inside one repetition, such as "4 to 7", means that several threads have the same printed rate at the limit of the fastest half. The count of each mesh is then not defined by the rates [Ref5].</p>')` | Continues the paragraph: how to read a range inside one repetition. It comes from equal printed rates at the limit of the half, and the rates then do not define the count per mesh. |
| 541 | `    for st_ in ('A1', 'A2'):` | Loop over the two steps. |
| 542 | `        c = cpu_panels(s, st_)` | `c`: the panels of the step (line 398). |
| 543 | `        if c:` | Only when the panels exist. |
| 544 | `            ms = sorted(set(x['min_ms'] for x in s[st_].values()))` | `ms`: the interval lengths of the kernels of the step, sorted. Step A2 has two: 6000 ms and 15000 ms. |
| 545 | `            o.append(f"<h3>{st_}: rate of each thread against its CPU number (interval {' or '.join(f'{m/1000:g} s' for m in ms)})</h3>" + c)` | Adds a sub-heading with the step and its interval lengths in seconds, then the panels. |
| 546 | `            o.append('<p class="cap">One dot is one thread: the median of its rates over all repetitions of the kernel. The dashed line is the border between mesh 0 and mesh 1. '` | Adds the caption of the panels: one dot is one thread, the median of its rates over all repetitions of the kernel, and the dashed line is the border between the meshes. |
| 547 | `                     'The vertical axis starts at 0 GB/s. The three panels of one row share one scale, and the two rows have different scales. '` | Continues the caption: where the vertical axis starts, and which panels share one scale. |
| 548 | `                     'Under each panel: the median thread rate of each mesh, the same number as in the list above and in the table below. It is the median over the repetitions of the median over the threads of one repetition.</p>')` | Continues the caption: what the number under each panel is and how it is computed. It is the same number as in the list above and in the table below. |
| 549 | `    # table per kernel` | Comment: the table with one row per kernel follows. |
| 550 | `    o.append('<h3>Numbers per kernel</h3><div class="tw"><table><tr><th>Step</th><th>Kernel</th><th>Binary</th><th>Interval (s)</th><th>Repetitions</th><th>Total GB/s, lowest to highest</th><th>Median total GB/s</th>'` | Adds a sub-heading and opens the table. This line holds the headings for the step, the kernel, the binary, the interval in seconds, the repetitions, the total from lowest to highest, and the median total. |
| 551 | `             '<th>Sum of thread rates mesh 0, GB/s</th><th>Sum of thread rates mesh 1, GB/s</th><th>Median thread rate mesh 0, GB/s</th><th>Median thread rate mesh 1, GB/s</th><th>q</th><th>Pattern</th><th>Threads of the fastest half on mesh 0, per repetition</th></tr>')` | Continues the headings: the sum of the thread rates of each mesh, the median thread rate of each mesh, q, the pattern, and the count of mesh 0 in the fastest half per repetition. |
| 552 | `    for st_ in ('A1', 'A2'):` | Loop over the two steps. |
| 553 | `        for k in KORDER:` | Loop over the six kernels. |
| 554 | `            if k not in s[st_]: continue` | A kernel without data in this step is skipped. |
| 555 | `            x = s[st_][k]` | `x`: the summary of the kernel in this step. |
| 556 | `            o.append(f"<tr><td>{st_}</td><td>{KNAME[k]}</td><td>{e(x['binary'])}</td><td>{x['min_ms']/1000:g}</td><td>{len(x['reps'])}</td><td>{rtxt(x['total_GBps'])}</td><td>{f2(x['total_GBps']['median'])}</td>"` | Adds the first cells of the row: step, printed kernel name, binary, interval in seconds, number of repetitions, range of the totals and median total in GB/s. |
| 557 | `                     f"<td>{rtxt(x['mesh0_sum'])}</td><td>{rtxt(x['mesh1_sum'])}</td><td>{rtxt(x['mesh0_median'])}</td><td>{rtxt(x['mesh1_median'])}</td><td>{rtxt(x['q'])}</td>"` | Continues the row: the ranges of the two sums of thread rates, of the two median thread rates, and of q. |
| 558 | `                     f"<td>{', '.join(x['labels']) if x['labels'] else 'labels not used'}</td><td>{fh_reps(x['reps'])}</td></tr>")` | Continues the row: the pattern labels joined with commas, or the words `labels not used`. Then the counts of the fastest half. |
| 559 | `    o.append('</table></div>')` | Closes the table. |
| 560 | `    o.append('<details><summary>Every repetition of A1 and A2</summary><div class="tw"><table><tr><th>Step</th><th>Launch</th><th>Repetition</th><th>Total GB/s</th><th>Passes per thread</th><th>Sum mesh 0, GB/s</th><th>Sum mesh 1, GB/s</th><th>Median mesh 0, GB/s</th><th>Median mesh 1, GB/s</th><th>q</th><th>Fastest half on mesh 0</th></tr>')` | Opens a part that the reader can unfold, with one row per repetition of A1 and A2. The line holds its eleven column headings. |
| 561 | `    for st_ in ('A1', 'A2'):` | Loop over the two steps. |
| 562 | `        for k in KORDER:` | Loop over the six kernels. |
| 563 | `            for r in s[st_].get(k, {}).get('reps', []):` | Loop over the repetitions of the kernel in this step. |
| 564 | `                o.append(f"<tr><td>{st_}</td><td>{e(r['tag'])}</td><td>{r['rep']}</td><td>{fx(r['total_GBps'], 2)}</td><td>{fx(r['passes_per_thread'], 1)}{' (below 50)' if r['below_50_passes'] else ''}</td>"` | Adds the first cells of the row: step, launch, repetition number, total with 2 decimals, and passes per thread with 1 decimal. The words `(below 50)` are added when the repetition fails the 2 % check. |
| 565 | `                         f"<td>{f2(r['mesh0']['sum'])}</td><td>{f2(r['mesh1']['sum'])}</td><td>{f2(r['mesh0']['median'])}</td><td>{f2(r['mesh1']['median'])}</td><td>{f2(r['q'], 3)}</td><td>{fh_reps([r])}</td></tr>")` | Continues the row: the sum and the median of the thread rates of each mesh, q with 3 decimals, and the count of mesh 0 in the fastest half. |
| 566 | `    o.append('</table></div></details>')` | Closes the table and the unfolding part. |
| 567 | `    # write repetitions: highest against lowest total (plan: "the faster write repetitions")` | Comment: the write repetitions with the highest and with the lowest total are compared. The plan speaks of the faster write repetitions. |
| 568 | `    w = write_hi_lo(s)` | `w`: the entries of line 487. |
| 569 | `    if w:` | Only when such entries exist. |
| 570 | `        li = [f"<li>{x['step']}, {KNAME[x['k']]}: the totals of the {x['n']} repetitions were {fx(x['lo'], 2)} to {fx(x['hi'], 2)} GB/s. "` | `li`: one item per write kernel and step: the lowest and the highest total of its repetitions in GB/s. |
| 571 | `              f"From the repetition with the lowest total to the one with the highest, the sum of the thread rates changed by {fs(x['d0'], 2)} GB/s on mesh 0 and by {fs(x['d1'], 2)} GB/s on mesh 1.</li>" for x in w]` | Continues the item: by how much the sum of the thread rates changed on mesh 0 and on mesh 1, from the repetition with the lowest total to the one with the highest. Both changes are printed with a sign. |
| 572 | `        o.append('<h3>Write kernels: the repetition with the highest total against the one with the lowest</h3><p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds a sub-heading and the list under the words `Observed in screening:`. |
| 573 | `        o.append(f'<p class="take">Observed in screening: {write_hi_lo_txt(w)[0].lower() + write_hi_lo_txt(w)[1:]}</p>')` | Adds a highlighted statement: the words `Observed in screening:` and the text of line 500, with its first letter in lower case. |
| 574 | `    # A1 against A2` | Comment: the comparison of A1 with A2 follows. |
| 575 | `    c = s['A1_A2']` | `c`: the comparison of the two steps from the json file. |
| 576 | `    o.append('<h3>Totals with the short and with the long interval</h3>')` | Adds the sub-heading for the totals with the short and with the long interval. |
| 577 | `    if not c['kernels']:` | Tests whether the comparison has no kernel. |
| 578 | `        o.append(missing('The comparison of the totals needs both A1 and A2. The measurement that is missing: the step that has no data above.'))` | Adds an `Insufficient data` notice: the comparison needs both A1 and A2. |
| 579 | `    else:` | The case with a comparison. |
| 580 | `        o.append('<div class="tw"><table><tr><th>Kernel</th><th>Short interval (s)</th><th>Total GB/s, short: lowest to highest</th><th>Median, short</th><th>Long interval (s)</th><th>Total GB/s, long: lowest to highest</th><th>Median, long</th><th>Change of the median, GB/s</th><th>Change, %</th><th>The two ranges overlap</th><th>Long totals outside the short range</th></tr>')` | Opens the table with eleven column headings: the kernel, then for the short and for the long interval the interval in seconds, the range of the totals and the median, then the change of the median in GB/s and in percent, whether the two ranges overlap, and the long totals outside the short range. |
| 581 | `        for k in KORDER:` | Loop over the six kernels. |
| 582 | `            if k not in c['kernels']: continue` | A kernel without a comparison is skipped. |
| 583 | `            x = c['kernels'][k]` | `x`: the comparison of the kernel. |
| 584 | `            o.append(f"<tr><td>{KNAME[k]}</td><td>{x['short_ms']/1000:g}</td><td>{rtxt(x['short'])}</td><td>{fx(x['short']['median'], 2)}</td><td>{x['long_ms']/1000:g}</td><td>{rtxt(x['long'])}</td><td>{fx(x['long']['median'], 2)}</td>"` | Adds the first cells of the row: the kernel, and for each interval its length, the range of the totals and the median. |
| 585 | `                     f"<td>{fs(x['change_GBps'], 2)}</td><td>{fs(x['change_pct'], 1)}</td><td>{'yes' if x['ranges_overlap'] else 'no'}</td><td>{x['n_long_outside_short']} of {x['n_long']}</td></tr>")` | Continues the row: the change of the median in GB/s with 2 decimals and in percent with 1 decimal, both with a sign, then `yes` or `no` for the overlap, then how many of the long totals lie outside the short range. |
| 586 | `        o.append('</table></div>')` | Closes the table. |
| 587 | `        no = [KNAME[k] for k in KORDER if k in c['kernels'] and not c['kernels'][k]['ranges_overlap']]` | `no`: the printed names of the kernels whose two ranges do not overlap. |
| 588 | `        t = f"Observed in screening: for {len(no)} of the {len(c['kernels'])} kernels, the range of the totals with the long interval does not overlap the range with the short interval" + (f" ({', '.join(no)})." if no else '.')` | `t`: a statement, `Observed in screening`: for how many of the kernels the range of the totals with the long interval does not overlap the range with the short interval, with their names in brackets. |
| 589 | `        t += ' Count of the single long totals that lie outside the short range: ' + ', '.join(f"{KNAME[k]} {c['kernels'][k]['n_long_outside_short']} of {c['kernels'][k]['n_long']}" for k in KORDER if k in c['kernels']) + '.'` | Continues `t`: for each kernel, how many of its single long totals lie outside the short range. |
| 590 | `        o.append(f'<p class="take">{t}</p>')` | Adds the statement as a highlighted paragraph. |
| 591 | `        o.append(order_b7_b8(s))` | Adds the part on the order of the steps B7 and B8 (line 596). |
| 592 | `        o.append(f'<p class="miss"><b>{ID}.</b> The difference between two copies of one loop. Part A has no such control. So this page does not say whether a change is larger than that difference. Steps B7 and B10 measure it [Ref1].</p>')` | Adds an `Insufficient data` notice about the missing control. Part A has no two copies of one loop. So the page cannot say whether a change is larger than the difference between two equal loops. The notice names the later steps that measure that difference. |
| 593 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `order_b7_b8`: what step A2 means for the order of B7 and B8 (lines 596 to 629)

| Line | Source | Explanation |
|---:|---|---|
| 596 | `def order_b7_b8(s):` | Starts the function `order_b7_b8`. It builds the part that says what A2 means for the order of the later steps B7 and B8. |
| 597 | `    """Consequence of A2 for the order of B7 and B8 (plan, 'Order and decision points', item 2)."""` | Text of the function: the plan gives this consequence in item 2 of its section `Order and decision points`. |
| 598 | `    c = s['A1_A2']; d = c['old_minus_new_read_GBps']; rd = c.get('order_reading')` | `c`: the comparison of A1 with A2. `d`: the values of the difference between the old and the new read kernel. `rd`: the reading of choice C11, or `None`. |
| 599 | `    o = ['<h3 id="order">Consequence for the order of B7 and B8</h3>',` | `o`: the pieces of the part, starting with its sub-heading. |
| 600 | `         '<p>The plan sets the order of the next read steps from A2: "if A2 changed the totals, B7 comes first; otherwise B7 and B8 are run together" [Ref1]. '` | Text of the page: the rule of the plan for the order of the two steps, as a quotation. The order depends on whether A2 changed the totals: B7 first, or B7 and B8 together. |
| 601 | `         'The plan gives no number for "changed". B7 and B8 are steps for the difference between old read and new read (Q2a).</p>']` | Text of the page: two notes. The plan gives no number for the word `changed`, and the two steps belong to question Q2a, the difference between the old and the new read kernel. |
| 602 | `    if not rd:` | Tests whether the reading is missing. |
| 603 | `        return '\n'.join(o) + missing('The reading of A2 needs the totals of old read and of new read with both intervals. At least one of them has no data.')` | Returns the texts with an `Insufficient data` notice: the totals of the old and of the new read kernel are needed with both intervals. |
| 604 | `    ks = c['kernels']; so, sn = ks['read_old'], ks['read_new']` | `ks`: the comparisons per kernel. `so`: the comparison of the old read kernel. `sn`, the one of the new read kernel, is not used below. |
| 605 | `    sh, lg = f"{so['short_ms']/1000:g} s", f"{so['long_ms']/1000:g} s"` | `sh` and `lg`: the short and the long interval length as text in seconds. |
| 606 | `    li = [f"<li>The median total of old read minus the median total of new read was {fs(d['short'])} GB/s with the {sh} interval. It was {fs(d['long'])} GB/s with the {lg} interval. "` | `li`: the list items. The first gives the median total of the old read kernel minus the median total of the new read kernel, for the short and for the long interval, with a sign, in GB/s. |
| 607 | `          + ('So the difference of Q2a got smaller with the long interval.' if rd['difference_smaller_with_long'] else 'So the difference of Q2a did not get smaller with the long interval.') + '</li>',` | Continues the item: a sentence that the difference of Q2a got smaller with the long interval, or that it did not. The value `difference_smaller_with_long` of the json file chooses it. |
| 608 | `          f"<li>From the lowest and highest totals, this difference can lie from {fx(d['short_range'][0])} to {fx(d['short_range'][1])} GB/s with the {sh} interval. "` | The second item: the range in which this difference can lie with the short interval, from the lowest and highest totals. |
| 609 | `          f"It can lie from {fx(d['long_range'][0])} to {fx(d['long_range'][1])} GB/s with the {lg} interval. The two ranges {'do not overlap' if rd['changed'] else 'overlap'}.</li>"]` | Continues the item: the same range with the long interval, and whether the two ranges overlap. |
| 610 | `    for k in ('read_old', 'read_new'):` | Loop over the old and the new read kernel. |
| 611 | `        x = ks[k]` | `x`: the comparison of the kernel. |
| 612 | `        li.append(f"<li>{KNAME[k].capitalize()}: the median total moved by {fs(x['change_pct'], 1)} %. {x['n_long_outside_short']} of its {x['n_long']} totals with the long interval lie outside its range with the short interval.</li>")` | Adds an item: by how many percent the median total moved, and how many of the totals with the long interval lie outside the range with the short interval. |
| 613 | `    o.append('<p>Observed in screening, in <code>A1.csv</code> and <code>A2.csv</code> [Ref4]:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under a sentence that names the two csv files as the source. |
| 614 | `    if rd['changed']:` | The case that choice C11 says `changed`. |
| 615 | `        t = ('Reading of this page (choice C11 of the analysis script [Ref5]): A2 changed the totals. By item 2 of the plan, B7 then comes first'` | `t`: the reading of the page: A2 changed the totals, and by item 2 of the plan B7 then comes first. The text names choice C11 of the analysis script. |
| 616 | `             + (', and H7a gets priority in B7 [Ref1].' if rd['difference_smaller_with_long'] else '. The difference did not get smaller, so the change is not in the direction that H7a names [Ref1].'))` | Continues `t`: when the difference got smaller, hypothesis H7a gets priority in B7. When it did not, the text says that the change is not in the direction that H7a names. |
| 617 | `    else:` | The case that the totals stayed. |
| 618 | `        t = ('Reading of this page (choice C11 of the analysis script [Ref5]): the totals stayed. By item 2 of the plan, H7a then gets no priority, and B7 and B8 are run together [Ref1]. '` | `t`: the reading of the page: the totals stayed. By item 2 of the plan H7a then gets no priority, and B7 and B8 are run together. |
| 619 | `             'The plan says for this case that the short interval alone is not sufficient to explain Q2a [Ref1].')` | Continues `t`: the plan says for this case that the short interval alone is not sufficient to explain Q2a. |
| 620 | `    o.append(f'<p class="take">{t} Part A has no control with two copies of one loop, so this reading is screening only.</p>')` | Adds the reading as a highlighted paragraph. A fixed end marks it as screening only, for lack of a control with two copies of one loop. |
| 621 | `    o.append('<p>One conflict is open. The handoff, section B.9 "Settings after B7", takes the settings of B8 from the analysis of B7. So B8 cannot start before B7 is analysed [Ref2]. '` | Adds a paragraph about a conflict between the plan and the handoff note on this order. By the handoff note the settings of B8 come from the analysis of B7, so B8 cannot run together with B7. |
| 622 | `             'Item 3 of the same list of the plan also says "B7 first" [Ref1]. The user decides which rule applies.</p>')` | Continues the paragraph: another item of the same list of the plan agrees with the handoff note, and the choice is left to the user. |
| 623 | `    wk = [k for k in ('write_old', 'write_new', 'asmwrite') if k in ks]` | `wk`: the write kernels that have a comparison. |
| 624 | `    if wk:` | Only when there is at least one. |
| 625 | `        o.append('<p>Item 2 does not use the write totals. The plan runs the write step B10 whatever B7 shows [Ref1]. Observed in screening for the write kernels: '` | Adds a paragraph about the write kernels: the rule of the plan does not use their totals, and their step B10 runs whatever B7 shows. |
| 626 | `                 + ' '.join(f"{KNAME[k].capitalize()}: median total {fs(ks[k]['change_pct'], 1)} %, {ks[k]['n_long_outside_short']} of {ks[k]['n_long']} long totals outside the short range." for k in wk) + '</p>')` | Continues the paragraph: for each write kernel the change of the median total in percent, and how many long totals lie outside the short range. |
| 627 | `    return '\n'.join(o)` | Returns the part as one text. |

### Function `sec_a3`: the section on step A3 (lines 630 to 661)

| Line | Source | Explanation |
|---:|---|---|
| 630 | `def sec_a3(s):` | Starts the function `sec_a3`. It builds the section on step A3: the old read kernel with one and with two buffers per thread. |
| 631 | `    o = ['<h2 id="a3">A3: old read with one and with two buffers per thread</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 632 | `    g = s['A3']['groups']` | `g`: the groups of step A3 from the json file, one per number of buffers and interval length. |
| 633 | `    if not g:` | Tests whether the step has no group. |
| 634 | `        why = '; '.join(k for x in s['env'] for k in x.get('skipped', []) if k.startswith('A3'))` | `why`: the `skipped` lines of the files `env.txt` that start with `A3`. |
| 635 | `        return '\n'.join(o) + missing('Step A3 has no usable data.' + (f' The script wrote: "{e(why)}".' if why else '') + ' The measurement that is missing: old read with <code>--kernel read</code> and with <code>--kernel all</code>, 3 processes for each of the 4 cases.')` | Returns the heading with an `Insufficient data` notice: step A3 has no usable data, what the script wrote about it, and which processes are missing. |
| 636 | `    o.append('<p>Only the rows of the read kernel are compared. With two buffers the process also times write and copy [Ref2].</p>')` | Adds a fixed paragraph: only the rows of the read kernel are compared, and with two buffers the process also times write and copy. |
| 637 | `    rows = []` | `rows`: the rows of the chart, empty at first. |
| 638 | `    for name, x in g.items():` | Loop over the groups. |
| 639 | `        pts = [(r['q'], f"{r['tag']} repetition {r['rep']}: q {fx(r['q'], 3)}, total {fx(r['total_GBps'], 2)} GB/s") for p in x['processes'] for r in p['reps'] if r['q'] is not None]` | `pts`: one point per read repetition of the group: its q, and a hover text with the tag, the repetition number, q with 3 decimals and the total in GB/s. |
| 640 | `        rows.append((f"{x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}, {x['min_ms']/1000:g} s", pts, f"q {rtxt(x['q'])}; total {f2(x['total_GBps']['median'], 0)} GB/s"))` | Adds a chart row: a name with the number of buffers and the interval length in seconds, the points, and a label with the range of q and the median total without decimals. |
| 641 | `    o.append(strip_chart(rows, 0, 1, [0, 0.25, 0.5, 0.65, 0.85, 1], 'q of the read rows (no unit)', 'q of old read with one and with two buffers',` | Adds the chart (line 89): q of the read rows from 0 to 1, with the same tick marks as the chart of q. |
| 642 | `                         band=(s['limits']['q_split_below'], s['limits']['q_uniform_above'], 'between')))` | Continues the call: the grey band from 0.65 to 0.85 with the name `between`. |
| 643 | `    o.append('<p class="cap">One dot is one repetition of the read kernel. Each row is labelled with its range of q and its median total.</p>')` | Adds the caption: one dot is one repetition of the read kernel, and each row carries its range of q and its median total. |
| 644 | `    o.append('<div class="tw"><table><tr><th>Case</th><th>Processes</th><th>Read repetitions</th><th>Total GB/s, lowest to highest</th><th>Median total GB/s</th><th>q</th><th>Pattern</th><th>Repetitions below 50 passes</th></tr>')` | Opens the table with eight column headings: the case, the processes, the read repetitions, the range of the totals, the median total, q, the pattern, and the repetitions below 50 passes. |
| 645 | `    for name, x in g.items():` | Loop over the groups. |
| 646 | `        o.append(f"<tr><td>{x['buffers']} buffer{'s' if x['buffers'] > 1 else ''}, {x['min_ms']/1000:g} s</td><td>{len(x['processes'])}</td><td>{x['q']['n']}</td><td>{rtxt(x['total_GBps'])}</td><td>{f2(x['total_GBps']['median'])}</td><td>{rtxt(x['q'])}</td><td>{x['label'] or 'labels not used'}</td><td>{x['n_below_50_passes']}</td></tr>")` | Adds the row of the group. The pattern cell shows the label of the group, or the words `labels not used`. |
| 647 | `    o.append('</table></div>')` | Closes the table. |
| 648 | `    if not s['A3']['compare']:` | Tests whether the json file has no comparison of one buffer with two. |
| 649 | `        return '\n'.join(o) + missing('The comparison needs both cases at one interval. One of them has no data.')` | Returns the section with an `Insufficient data` notice: the comparison needs both cases at one interval length. |
| 650 | `    o.append(f'<p class="take">{a3_answer(s)}</p>')` | Adds the answer of line 701 as a highlighted paragraph. |
| 651 | `    li = []` | `li`: the list items, empty at first. |
| 652 | `    for ms, c in s['A3']['compare'].items():` | Loop over the interval lengths of the comparison. |
| 653 | `        t = f"<li>Interval {int(ms)/1000:g} s: q was {rtxt(c['q_one'])} with one buffer. It was {rtxt(c['q_two'])} with two buffers. The two ranges of q {'overlap' if c['q_ranges_overlap'] else 'do not overlap'}. "` | `t`: an item: the interval in seconds, the range of q with one buffer and with two, and whether the two ranges overlap. |
| 654 | `        if c['same_label'] is not None:` | Only when both groups have a label. |
| 655 | `            t += f"The pattern label was {c['one_label']} with one buffer and {c['two_label']} with two. "` | Adds the two pattern labels. |
| 656 | `        t += f"The median total changed by {fs(c['total_change_GBps'], 2)} GB/s from one buffer to two.</li>"` | Ends the item: by how many GB/s the median total changed from one buffer to two, with a sign. |
| 657 | `        li.append(t)` | Adds the item. |
| 658 | `    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `Observed in screening:`. |
| 659 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `a4_chart`: q against the thread count (lines 662 to 700)

| Line | Source | Explanation |
|---:|---|---|
| 662 | `def a4_chart(k, x, lim, usable):` | Starts the function `a4_chart`. For one kernel of step A4 it draws q against the thread count, in two panels. `usable` says whether the pattern labels are shown. |
| 663 | `    W, H, top, bot = 780, 250, 34, 190` | Sizes in drawing units: the width 780 and the height 250. The plot area goes from 34 at the top to 190 at the bottom. |
| 664 | `    panels = [('64+b', 60, 470), ('a+a', 540, 750)]` | `panels`: the two panels with their left and right edges. The series `64+b` goes from 60 to 470, and the series `a+a` from 540 to 750. |
| 665 | `    Y = lambda q: bot - q * (bot - top)` | `Y`: a function that turns q into a vertical position. q of 0 lies at the bottom and q of 1 at the top. |
| 666 | `    o = svg_open(W, H, f'q against thread count, {KNAME.get(k, k)}')` | `o`: the drawing, with a description for screen readers that names the kernel. |
| 667 | `    for sname, xa, xb in panels:` | Loop over the two panels. |
| 668 | `        ser = x['series'][sname]; cs = ser['counts']` | `ser`: the entry of this series for the kernel. `cs`: its thread counts that have data. |
| 669 | `        o.append(f'<rect x="{xa}" y="{fx(Y(lim["q_uniform_above"]), 1)}" width="{xb-xa}" height="{fx(Y(lim["q_split_below"])-Y(lim["q_uniform_above"]), 1)}" fill="{BAND}"/>')` | Draws the grey band between the two limits of q, 0.65 and 0.85. |
| 670 | `        for t in (0, 0.25, 0.5, lim['q_split_below'], lim['q_uniform_above'], 1):` | Loop over six values of the vertical axis: 0, 0.25, 0.5, the two limits and 1. |
| 671 | `            o.append(f'<line x1="{xa}" y1="{fx(Y(t), 1)}" x2="{xb}" y2="{fx(Y(t), 1)}" stroke="{GRID}"/>')` | Draws a light grey horizontal grid line at the value. |
| 672 | `            o.append(f'<text x="{xa-6}" y="{fx(Y(t)+4, 1)}" text-anchor="end" class="ax">{t:g}</text>')` | Writes the value at the left of the panel. |
| 673 | `        o.append(f'<text x="{xa}" y="{top-18}" class="lab">{"64 threads on mesh 0, b threads on mesh 1" if sname == "64+b" else "a threads on each mesh"}</text>')` | Writes the title of the panel: 64 threads on mesh 0 and b threads on mesh 1, or a threads on each mesh. |
| 674 | `        if not cs:` | Tests whether the series has no count with data. |
| 675 | `            o.append(f'<text x="{(xa+xb)/2}" y="{(top+bot)/2}" text-anchor="middle" class="lab">{ID}: no count of this series</text>'); continue` | Writes `Insufficient data` with a note into the middle of the panel. `continue` goes to the next panel. |
| 676 | `        X = lambda i: xa + (i + 0.5) * (xb - xa) / len(cs)` | `X`: a function that gives the horizontal position of count number `i`. The counts are spread evenly over the panel. |
| 677 | `        pts = []` | `pts`: the points of the median line, empty at first. |
| 678 | `        for i, c in enumerate(cs):` | Loop over the counts. |
| 679 | `            cc = x['counts'][c]; qs = [r['q'] for r in cc['reps'] if r['q'] is not None]` | `cc`: the entry of the count. `qs`: the q values of its repetitions. |
| 680 | `            if not qs: continue` | A count without q is skipped. |
| 681 | `            pts.append((X(i), Y(st.median(qs))))` | Adds the point of the count: its position, and the median of its q values. |
| 682 | `        if len(pts) > 1:` | Only with at least 2 points. |
| 683 | `            o.append(f'<polyline points="{" ".join(f"{fx(a, 1)},{fx(b, 1)}" for a, b in pts)}" fill="none" stroke="#8a8984" stroke-width="1.5"/>')` | Draws a grey line that joins the medians of the counts. |
| 684 | `        for i, c in enumerate(cs):` | Second loop over the counts, for the dots and the labels. |
| 685 | `            cc = x['counts'][c]; qs = [r['q'] for r in cc['reps'] if r['q'] is not None]` | `cc` and `qs`: as in line 679. |
| 686 | `            for j, r in enumerate(cc['reps']):` | Loop over the repetitions of the count. |
| 687 | `                if r['q'] is not None:` | Only for a repetition with q. |
| 688 | `                    o.append(marker(X(i) + (j - (len(qs) - 1) / 2) * 7, Y(r['q']), 'circle', C0, f"{c} threads, repetition {r['rep']}: q {fx(r['q'], 3)}, total {fx(r['total_GBps'], 2)} GB/s", r=4))` | Draws one blue circle per repetition at its q. The dots of one count stand side by side, 7 units apart. The hover text gives the count, the repetition, q with 3 decimals and the total in GB/s. |
| 689 | `            if qs:` | Only for a count with q. |
| 690 | `                ylab = Y(max(qs)) - 10` | `ylab`: the height of the label, 10 units above the highest dot of the count. |
| 691 | `                if ylab < top - 2: ylab = Y(min(qs)) + 18` | When that place lies above the plot area, the label goes 18 units below the lowest dot. |
| 692 | `                o.append(f'<text x="{fx(X(i), 1)}" y="{fx(ylab, 1)}" text-anchor="middle" class="val">{fx(st.median(qs), 2)}</text>')` | Writes the median q of the count with 2 decimals. |
| 693 | `            o.append(f'<text x="{fx(X(i), 1)}" y="{bot+16}" text-anchor="middle" class="ax">{c}</text>')` | Writes the thread count under the axis. |
| 694 | `            o.append(f'<text x="{fx(X(i), 1)}" y="{bot+31}" text-anchor="middle" class="val">{(cc["label"] or "") if usable else ""}</text>')` | Writes the pattern label of the count under it, only when the labels are usable. If not, the place stays empty. |
| 695 | `        o.append(f'<text x="{(xa+xb)/2}" y="{H-4}" text-anchor="middle" class="ax">threads on mesh 0 + threads on mesh 1</text>')` | Writes the title of the horizontal axis under the panel: threads on mesh 0 plus threads on mesh 1. |
| 696 | `    o.append(f'<text x="14" y="{(top+bot)/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {(top+bot)/2})">q (ratio)</text>')` | Writes the title of the vertical axis, turned by 90 degrees: q, a ratio. |
| 697 | `    o.append('</svg>')` | Closes the drawing. |
| 698 | `    return '\n'.join(o)` | Returns the drawing as one text. |

### Functions `a3_answer` and `a4_facts`: sentences and facts without labels (lines 701 to 729)

| Line | Source | Explanation |
|---:|---|---|
| 701 | `def a3_answer(s):` | Starts the function `a3_answer`. It builds the answer to the question of the plan for step A3. |
| 702 | `    """The answer to the plan's question of A3: whether the second buffer changes the pattern in this session."""` | Text of the function: the question is whether the second buffer changes the pattern in this session. |
| 703 | `    cmp = s['A3']['compare']` | `cmp`: the comparison of one buffer with two, per interval length. |
| 704 | `    apart = [ms for ms, c in cmp.items() if not c['q_ranges_overlap']]` | `apart`: the interval lengths at which the two ranges of q do not overlap. |
| 705 | `    two = [(g['q']['max'], g['min_ms']) for g in s['A3']['groups'].values() if g['buffers'] == 2 and g['q']['n']]` | `two`: for each group with two buffers that has q values, the pair of its highest q and its interval length. |
| 706 | `    if apart:` | The case that the ranges are apart at one interval length or more. |
| 707 | `        t = ('Observed in screening: q changed with the second buffer. The range of q with two buffers does not overlap the range with one buffer at the interval '` | `t`: the sentence, `Observed in screening`: q changed with the second buffer. The range of q with two buffers does not overlap the range with one buffer. |
| 708 | `             + ' and '.join(f'{int(ms)/1000:g} s' for ms in apart) + '.')` | Continues `t`: the interval lengths in seconds at which this holds, joined with the word `and`. |
| 709 | `    else:` | The case that the ranges overlap at every interval length. |
| 710 | `        t = ('Observed in screening: no change of q with the second buffer. At ' + ('each of the ' + str(len(cmp)) + ' intervals' if len(cmp) > 1 else 'the one interval')` | `t`: the sentence, `Observed in screening`: no change of q with the second buffer. The words for the intervals depend on how many interval lengths were compared. |
| 711 | `             + ' the range of q with two buffers overlaps the range with one buffer.')` | Continues `t`: the range of q with two buffers overlaps the range with one buffer. |
| 712 | `    if two:` | Only when a group with two buffers has q values. |
| 713 | `        q, ms = max(two)` | `q` and `ms`: the highest q of these groups and its interval length. |
| 714 | `        t += f" The highest q of old read with two buffers in this session was {fx(q, 2)} (interval {ms/1000:g} s)."` | Adds a sentence with the highest q of the old read kernel with two buffers in this session, with 2 decimals, and its interval length. |
| 715 | `    return t` | Returns the text. |
| 718 | `def a4_facts(x):` | Starts the function `a4_facts`. It gives facts about one kernel of step A4 that need no labels. |
| 719 | `    """For one kernel of A4, series 64+b: the largest step of the median q between neighbouring counts with threads on both meshes, and the lowest median q."""` | Text of the function: for the series `64+b` it finds the largest step of the median q between neighbouring counts with threads on both meshes, and the lowest median q. |
| 720 | `    cs = [c for c in x['series']['64+b']['counts'] if not c.endswith('+0') and x['counts'][c]['q']['n']]` | `cs`: the counts of the series `64+b` that have q values, without the count 64+0. |
| 721 | `    if len(cs) < 2:` | Tests whether fewer than 2 counts are left. |
| 722 | `        return None` | Returns `None` in that case. |
| 723 | `    med = {c: x['counts'][c]['q']['median'] for c in cs}` | `med`: the median q of each count. |
| 724 | `    i = max(range(len(cs) - 1), key=lambda j: abs(med[cs[j + 1]] - med[cs[j]]))` | `i`: the place of the pair of neighbouring counts whose median q differs most. |
| 725 | `    low = min(cs, key=lambda c: med[c])` | `low`: the count with the lowest median q. |
| 726 | `    b = lambda c: int(c.split('+')[1])` | `b`: a function that gives the number of threads on mesh 1 of a count, the number after the `+`. |
| 727 | `    return dict(lower=cs[i], upper=cs[i + 1], q_lower=med[cs[i]], q_upper=med[cs[i + 1]], apart=b(cs[i + 1]) - b(cs[i]), lowest=low, q_lowest=med[low], last=cs[-1], q_last=med[cs[-1]])` | Returns the two counts of the largest step with their median q, how many threads they are apart, the count with the lowest median q and that q, and the last count with its median q. |

### Function `b8_consequence`: what step A4 gives for step B8 (lines 730 to 759)

| Line | Source | Explanation |
|---:|---|---|
| 730 | `def b8_consequence(s):` | Starts the function `b8_consequence`. It builds the part that says what A4 gives for the later step B8. |
| 731 | `    """Consequence of A4 for B8 (handoff B.9 row B8 and B.10 item B8)."""` | Text of the function: the handoff note names the need of B8 in the row B8 of its section B.9 and in section B.10. |
| 732 | `    ks = s['A4']['kernels']; usable = s['q']['decision']['labels_usable']` | `ks`: the kernels of step A4. `usable`: whether the pattern labels are usable. |
| 733 | `    o = ['<h3 id="b8">Consequence for B8</h3>']` | `o`: the pieces of the part, starting with its sub-heading. |
| 734 | `    if usable:` | The case that the labels are usable. |
| 735 | `        li = []` | `li`: the list items, empty at first. |
| 736 | `        for k, x in ks.items():` | Loop over the kernels. |
| 737 | `            br = x['series']['64+b']['bracket']` | `br`: the bracket of the series `64+b` for this kernel, or `None`. |
| 738 | `            li.append(f"<li>{KNAME.get(k, k)}: " + (f"the pattern changed between {br[0]} and {br[1]} threads. B8 refines the grid around these two counts in steps of 4 threads [Ref2]." if br` | Adds an item. With a bracket it says between which two thread counts the pattern changed, and that B8 refines the grid around them in steps of 4 threads. |
| 739 | `                                                 else f"{ID}. A4 gives no pair of counts for this kernel ({e(x['series']['64+b']['note'])}). So Part A gives no thread counts of this kernel for B8.") + '</li>')` | Continues the item: without a bracket it says `Insufficient data`, gives the note of the analysis script, and says that Part A gives no thread counts of this kernel for B8. |
| 740 | `        o.append('<p>B8 needs "the two counts between which A4 saw the pattern change", for each kernel [Ref2].</p><ul>' + ''.join(li) + '</ul>')` | Adds a sentence that quotes what B8 needs from A4, then the list. |
| 741 | `        return '\n'.join(o)` | Returns the part. |
| 742 | `    lim = s['limits']` | The case that the labels are not usable. `lim`: the limits. |
| 743 | `    o.append(f'<p class="miss"><b>{ID}.</b> Part A gives no thread counts for B8. B8 needs "the two counts between which A4 saw the pattern change" [Ref2]. '` | Adds an `Insufficient data` notice: Part A gives no thread counts for B8. It quotes what B8 needs. |
| 744 | `             f"The pattern rule of the handoff, with the limits {lim['q_split_below']} and {lim['q_uniform_above']}, is not used on this page. The handoff says not to use the labels if q does not fall into two groups [Ref2]. "` | Continues the notice: the pattern rule with its two limits is not used on the page, and the handoff note says not to use the labels when q does not fall into two groups. |
| 745 | `             'By the test of the analysis script (choice C2) q does not fall into two groups [Ref5]. So A4 gives no pair of counts between which the pattern changes. '` | Continues the notice: by the test of the analysis script (choice C2) q does not fall into two groups. So A4 gives no pair of counts between which the pattern changes. |
| 746 | `             'What is needed before B8: a pattern rule that fits the measured q. The steps B5 and B9 use the same label, so they need it too [Ref2].</p>')` | Continues the notice: what is needed before B8 is a pattern rule that fits the measured q. The steps B5 and B9 use the same label, so they need it too. |
| 747 | `    li = []` | `li`: the list items, empty at first. |
| 748 | `    for k, x in ks.items():` | Loop over the kernels. |
| 749 | `        f = a4_facts(x)` | `f`: the facts of line 718 for this kernel. |
| 750 | `        if not f: continue` | A kernel without such facts is skipped. |
| 751 | `        t = (f"<li>{KNAME.get(k, k).capitalize()}, series 64+b: the largest step of the median q between two neighbouring counts is from {fx(f['q_lower'])} at {f['lower']} to {fx(f['q_upper'])} at {f['upper']}. "` | `t`: an item for the series `64+b` of the kernel: the largest step of the median q between two neighbouring counts, with the two counts and their median q. |
| 752 | `             f"These two counts are {f['apart']} threads apart" + ('. That is already the step of B8 [Ref2]. ' if f['apart'] == 4 else ', and B8 uses a step of 4 threads [Ref2]. ')` | Continues the item: how many threads the two counts are apart. When that is 4, the text says that this is already the step of B8. If not, it says that B8 uses a step of 4 threads. |
| 753 | `             + f"The lowest median q of the series is {fx(f['q_lowest'])} at {f['lowest']}. At {f['last']} the median q is {fx(f['q_last'])}.</li>")` | Continues the item: the lowest median q of the series with its count, and the median q at the last count. |
| 754 | `        li.append(t)` | Adds the item. |
| 755 | `    if li:` | Only when at least one item exists. |
| 756 | `        o.append('<p>What <code>A4.csv</code> shows without labels, observed in screening (counts with threads on both meshes) [Ref4]:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under a sentence that says what `A4.csv` shows without labels, for the counts with threads on both meshes. |
| 757 | `    return '\n'.join(o)` | Returns the part. |

### Function `sec_a4`: the section on step A4 (lines 760 to 810)

| Line | Source | Explanation |
|---:|---|---|
| 760 | `def sec_a4(s):` | Starts the function `sec_a4`. It builds the section on step A4: the pattern against the thread count. |
| 761 | `    o = ['<h2 id="a4">A4: pattern against the thread count</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 762 | `    ks = s['A4']['kernels']; usable = s['q']['decision']['labels_usable']` | `ks`: the kernels of step A4. `usable`: whether the pattern labels are usable. |
| 763 | `    if not ks:` | Tests whether the step has no kernel. |
| 764 | `        return '\n'.join(o) + missing('Step A4 has no usable data. The measurement that is missing: old read and asm read at the 11 thread counts of <code>run_partA.sh</code>.')` | Returns the heading with an `Insufficient data` notice that names the missing measurement: the old read kernel and `asmread` at the 11 thread counts of the run script. |
| 765 | `    for k, x in ks.items():` | Loop over the kernels. |
| 766 | `        o.append(f'<h3>{KNAME.get(k, k)} (<code>{e(x["binary"])}</code>)</h3>' + a4_chart(k, x, s['limits'], usable))` | Adds a sub-heading with the printed kernel name and its binary, then the chart of line 662. |
| 767 | `    o.append('<p class="cap">One dot is one repetition. The line joins the medians of the counts, and the number at each count is that median. The grey band is the range "between". '` | Adds the caption of the charts: one dot is one repetition, the line joins the medians of the counts, the number at each count is that median, and the grey band is the range `between`. |
| 768 | `             + ('Under each count: the pattern label of the count.' if usable else 'No pattern label is shown, because the labels are not used on this page.') + '</p>')` | Continues the caption: with usable labels it says that the pattern label stands under each count. If not, it says that no label is shown. |
| 769 | `    li = []` | `li`: the list items, empty at first. |
| 770 | `    for k, x in ks.items():` | Loop over the kernels. |
| 771 | `        for sname, ser in x['series'].items():` | Loop over the two series of the kernel. |
| 772 | `            n = f"{KNAME.get(k, k)}, series {sname}"` | `n`: the printed kernel name and the name of the series. |
| 773 | `            if ser['missing']:` | Only when counts of the series have no usable block. |
| 774 | `                li.append(f"<li>{n}: {ID} for the counts {', '.join(ser['missing'])}. These launches have no usable block.</li>")` | Adds an item with `Insufficient data` for these counts. |
| 775 | `            if not usable:` | The case that the labels are not usable. |
| 776 | `                qs = ', '.join(f"{c}: {f2(x['counts'][c]['q']['median'])}" for c in ser['counts'])` | `qs`: the median q of each count of the series, as text. |
| 777 | `                li.append(f"<li>{n}: the labels are not used, so no change of pattern is given. Median q per count: {qs}.</li>")` | Adds an item: the labels are not used, so no change of pattern is given. Then the median q per count. |
| 778 | `            elif ser['bracket']:` | The case that the series has a bracket. |
| 779 | `                li.append(f"<li>{n}: the pattern changed between {ser['bracket'][0]} and {ser['bracket'][1]} threads. The labels in the order of the counts: {', '.join(f'{c} {l}' for c, l in zip(ser['counts'], ser['labels']))}.</li>")` | Adds an item: between which two thread counts the pattern changed, and the labels in the order of the counts. |
| 780 | `            else:` | The case with usable labels and no bracket. |
| 781 | `                li.append(f"<li>{n}: {e(ser['note'])}. The labels in the order of the counts: {', '.join(f'{c} {l}' for c, l in zip(ser['counts'], ser['labels']))}.</li>")` | Adds an item with the note of the analysis script and the labels in the order of the counts. |
| 782 | `    for sname, v in s['A4']['bracket_compare'].items():` | Loop over the comparison of the brackets of the two kernels, one entry per series. |
| 783 | `        if v == 'equal':` | The case that both kernels have the same bracket. |
| 784 | `            li.append(f"<li>Series {sname}: the two kernels changed between the same two counts. The plan calls this \"not resolved at this grid\" [Ref1].</li>")` | Adds an item: the two kernels changed between the same two counts. It quotes the words of the plan for this case, not resolved at this grid. |
| 785 | `        elif v == 'different':` | The case of two different brackets. |
| 786 | `            li.append(f"<li>Series {sname}: the two kernels changed between different counts.</li>")` | Adds an item: the two kernels changed between different counts. |
| 787 | `    for k, x in ks.items():` | Loop over the kernels. |
| 788 | `        for c, cc in x['counts'].items():` | Loop over the thread counts of the kernel. |
| 789 | `            t = mesh_change_txt(cc['reps'])` | `t`: the sentences of line 470 when the faster mesh was not the same in all repetitions of the count. |
| 790 | `            if t:` | Only when there are such sentences. |
| 791 | `                li.append(f"<li>{KNAME.get(k, k)} at {c} threads: the faster mesh was not the same in the {len(cc['reps'])} repetitions. {t}</li>")` | Adds an item with the kernel, the count, the number of repetitions and the sentences. |
| 792 | `    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `Observed in screening:`. |
| 793 | `    if usable:` | The case that the labels are usable. |
| 794 | `        o.append('<p>The count 64+0 has threads on one mesh only. It keeps its own label, and the change of pattern is looked for among the counts with threads on both meshes [Ref5].</p>')` | Adds a paragraph about the count 64+0: it has threads on one mesh only, keeps its own label, and the change of pattern is looked for among the other counts. |
| 795 | `    else:` | The case that the labels are not usable. |
| 796 | `        o.append('<p>The count 64+0 has threads on one mesh only. Its q is shown, and it is not compared with the counts that have threads on both meshes [Ref5].</p>')` | Adds a paragraph about the count 64+0: its q is shown, and it is not compared with the counts that have threads on both meshes. |
| 797 | `    o.append('<div class="tw"><table><tr><th>Kernel</th><th>Threads</th><th>Total GB/s (each repetition)</th><th>q (each repetition)</th><th>Median thread rate mesh 0, GB/s (each repetition)</th><th>Median thread rate mesh 1, GB/s (each repetition)</th><th>Threads of the fastest half on mesh 0 (each repetition)</th><th>Pattern</th><th>Passes per thread (each repetition)</th></tr>')` | Opens the table with nine column headings: the kernel, the threads, and for each repetition the total, q, the median thread rate of each mesh and the count of mesh 0 in the fastest half. Then the pattern and the passes per thread of each repetition. |
| 798 | `    for k, x in ks.items():` | Loop over the kernels. |
| 799 | `        for sname in ('64+b', 'a+a'):` | Loop over the two series. |
| 800 | `            for c in x['series'][sname]['counts']:` | Loop over the counts of the series that have data. |
| 801 | `                cc = x['counts'][c]; rr = cc['reps']` | `cc`: the entry of the count. `rr`: its repetitions. |
| 802 | `                o.append(f"<tr><td>{KNAME.get(k, k)}</td><td>{c}</td><td>{', '.join(f2(r['total_GBps']) for r in rr)}</td><td>{', '.join(f2(r['q'], 3) for r in rr)}</td>"` | Adds the first cells of the row: the kernel, the count, the totals of the repetitions joined with commas, and their q values with 3 decimals. |
| 803 | `                         f"<td>{', '.join(f2(r['mesh0']['median']) for r in rr)}</td><td>{', '.join(f2(r['mesh1']['median']) for r in rr)}</td><td>{fh_reps(rr)}</td>"` | Continues the row: the median thread rates of mesh 0 and of mesh 1 per repetition, and the counts of the fastest half. |
| 804 | `                         f"<td>{(cc['label'] or '-') if usable else 'labels not used'}</td><td>{', '.join(f2(r['passes_per_thread'], 1) for r in rr)}</td></tr>")` | Continues the row: the label of the count or the words `labels not used`, and the passes per thread of each repetition with 1 decimal. |
| 805 | `    o.append('</table></div>')` | Closes the table. |
| 806 | `    o.append('<p class="cap">The fastest half of a count is half of its threads. A range such as "26 to 32" inside one repetition comes from equal printed rates at the limit of the fastest half [Ref5].</p>')` | Adds a caption: the fastest half of a count is half of its threads, and a range inside one repetition comes from equal printed rates at the limit of the half. |
| 807 | `    o.append(b8_consequence(s))` | Adds the part on step B8 (line 730). |
| 808 | `    return '\n'.join(o)` | Returns the section as one text. |

### Functions `box_hits` and `place_label`: a free place for a value label (lines 811 to 849)

| Line | Source | Explanation |
|---:|---|---|
| 811 | `def box_hits(box, boxes, segs, hlines, plot):` | Starts the function `box_hits`. It tests whether the box of a text would touch something that is drawn already. |
| 812 | `    """True if the text box touches an earlier box, a dashed line or the data line. box = (x0, y0, x1, y1)."""` | Text of the function: it is true when the box touches an earlier box, a dashed line or the data line. A box is given by its left, top, right and bottom edge. |
| 813 | `    x0, y0, x1, y1 = box` | Takes the four edges of the box. |
| 814 | `    if any(x0 < b[2] + 2 and b[0] - 2 < x1 and y0 < b[3] + 2 and b[1] - 2 < y1 for b in boxes):` | Tests the earlier boxes: true when the box comes nearer than 2 units to one of them in both directions. |
| 815 | `        return True` | Returns true: the place is taken. |
| 816 | `    if x1 > plot[0] and x0 < plot[1] and any(y0 - 2 <= y <= y1 + 2 for y in hlines):` | Tests the dashed horizontal lines: true when the box lies inside the plot area across and a line passes through it, with 2 units of space. |
| 817 | `        return True` | Returns true. |
| 818 | `    for ax, ay, bx, by in segs:` | Loop over the pieces of the data line. Each piece goes from the point (`ax`, `ay`) to the point (`bx`, `by`). |
| 819 | `        lo, hi = max(ax, x0 - 3), min(bx, x1 + 3)` | `lo` and `hi`: the horizontal range that the piece and the box, widened by 3 units, have in common. |
| 820 | `        if lo > hi:` | Tests whether they have no common range. |
| 821 | `            continue` | Such a piece cannot touch the box. |
| 822 | `        f = lambda x: ay if bx == ax else ay + (by - ay) * (x - ax) / (bx - ax)` | `f`: a function that gives the height of the piece at a horizontal position. |
| 823 | `        ya, yb = sorted((f(lo), f(hi)))` | `ya` and `yb`: the lowest and the highest height of the piece inside the common range. |
| 824 | `        if ya <= y1 + 3 and yb >= y0 - 3:` | Tests whether these heights reach into the box, with 3 units of space. |
| 825 | `            return True` | Returns true: the data line would cross the text. |
| 826 | `    return False` | Nothing touches the box: returns false. |
| 829 | `def place_label(px, py, w, first, last, below_first, y_top, y_bot, boxes, segs, hlines, plot):` | Starts the function `place_label`. It looks for a free place for the value label of the point (`px`, `py`). `w` is the width of the text. `first` and `last` say whether the point is the first or the last of the line. |
| 830 | `    """Find a free place for the value label of the point (px, py). Returns (anchor, x, baseline) or None."""` | Text of the function: the result is the alignment, the horizontal position and the baseline of the text, or `None` when no place is free. |
| 831 | `    cands = []` | `cands`: the list of the places to try, empty at first. |
| 832 | `    dys = (16, -8, 28, -20, 40, -32) if below_first else (-8, 16, -20, 28, -32, 40)` | `dys`: six vertical distances from the point, in the order in which they are tried. For the lowest point of a line the first try is below the point. For every other point it is above. |
| 833 | `    main = 'start' if first else 'end' if last else 'middle'` | `main`: the first alignment to try. The label of the first point starts at the point, the label of the last point ends there, and every other label is centred. |
| 834 | `    for anchor, tx in [(main, px)] + ([] if first else [('end', px - 5)]) + ([] if last else [('start', px + 5)]):` | Loop over up to three alignments: the main one, then a label that ends 5 units left of the point (not for the first point), then a label that starts 5 units right of it (not for the last point). |
| 835 | `        for dy in dys:` | Loop over the six vertical distances. |
| 836 | `            cands.append((anchor, tx, py + dy, True))` | Adds the place to the list. The last value, true, says that the label must lie inside the plot area. |
| 837 | `    if first:` | Only for the first point of a line. |
| 838 | `        cands.insert(2, ('end', px - 7, py + 4, False))          # in the left margin, beside the point` | Adds one more place as the third to try: in the left margin, beside the point. This place may lie outside the plot area. |
| 839 | `    for anchor, tx, base, inside in cands:` | Loop over the places, in the order of the list. |
| 840 | `        bx0 = tx if anchor == 'start' else tx - w if anchor == 'end' else tx - w / 2` | `bx0`: the left edge of the text for this alignment. |
| 841 | `        box = (bx0, base - 9, bx0 + w, base + 2)` | `box`: the box of the text: from 9 units above the baseline to 2 units below it. |
| 842 | `        if inside and (box[1] < y_top + 1 or box[3] > y_bot - 1 or box[0] < plot[0] - 1 or box[2] > plot[1] + 1):` | Tests whether a place that must be inside leaves the plot area: above its top, below its bottom, or past its left or right edge. |
| 843 | `            continue` | Such a place is skipped. |
| 844 | `        if not box_hits(box, boxes, segs, hlines, plot):` | Tests whether the box is free (line 811). |
| 845 | `            boxes.append(box)` | Remembers the box. Later labels keep away from it. |
| 846 | `            return anchor, tx, base` | Returns the alignment, the position and the baseline. |
| 847 | `    return None` | No place was free: returns `None`. The caller then leaves the label out and counts it. |

### Function `a5_chart`: rate against interval number for each A5 process (lines 850 to 896)

| Line | Source | Explanation |
|---:|---|---|
| 850 | `def a5_chart(procs, lim):` | Starts the function `a5_chart`. It draws one panel per process of step A5: the rate of each interval against the number of the interval. |
| 851 | `    allr = [v for p in procs for v in p['rates_GBps']]` | `allr`: the rates of all intervals of all processes, in GB/s. |
| 852 | `    ymin = min(min(allr), lim['low_below_GBps']) - 0.6; ymax = max(max(allr), lim['high_above_GBps']) + 0.9` | `ymin` and `ymax`: the ends of the vertical axis, the same for all panels. The axis starts 0.6 GB/s below the lowest rate or the lower limit, whichever is lower. It ends 0.9 GB/s above the highest rate or the upper limit, whichever is higher. So the axis does not start at 0. |
| 853 | `    W, L, R, ph, gap, top = 780, 64, 170, 120, 46, 30` | Sizes in drawing units: the width 780, a left margin of 64, a right margin of 170 for the texts of the limits, a panel height of 120, a gap of 46 between panels and a top margin of 30. |
| 854 | `    H = top + len(procs) * (ph + gap)` | `H`: the height of the drawing, one panel and one gap per process. |
| 855 | `    nmax = max(max(p['n_intervals'] for p in procs), 2)` | `nmax`: the largest number of intervals of a process, at least 2. |
| 856 | `    X = lambda i: L + i / (nmax - 1) * (W - L - R)` | `X`: a function that turns an interval number into a horizontal position. Interval 0 lies at the left edge of the plot. |
| 857 | `    o = svg_open(W, H, 'Rate against interval number for each A5 process')` | `o`: the drawing, with its description for screen readers. |
| 858 | `    left_out = 0` | `left_out`: the number of value labels that found no free place, 0 at first. |
| 859 | `    for pi, p in enumerate(procs):` | Loop over the processes. `pi` is the number of the panel. |
| 860 | `        y0 = top + pi * (ph + gap)` | `y0`: the top edge of the panel. |
| 861 | `        Y = lambda v: y0 + ph - (v - ymin) / (ymax - ymin) * ph` | `Y`: a function that turns a rate into a vertical position inside the panel. |
| 862 | `        o.append(f'<rect x="{L}" y="{y0}" width="{W-L-R}" height="{ph}" fill="none" stroke="{GRID}"/>')` | Draws the frame of the panel in light grey. |
| 863 | `        o.append(f'<rect x="{L}" y="{fx(Y(lim["high_above_GBps"]), 1)}" width="{W-L-R}" height="{fx(Y(lim["low_below_GBps"])-Y(lim["high_above_GBps"]), 1)}" fill="{BAND}"/>')` | Draws the grey band between the two provisional limits, 69 GB/s and 70.5 GB/s. |
| 864 | `        o.append(f'<text x="{L}" y="{y0-8}" class="lab">CPU {p["cpu"]}, process {p["proc"]} (started {p["utc"]} UTC, waited {p["waited_s"]:g} s)</text>')` | Writes the title of the panel: the CPU, the process number, the UTC time of its start and the seconds that the run script waited before the launch. |
| 865 | `        for v, lab in ((lim['high_above_GBps'], f'{lim["high_above_GBps"]:g} GB/s: above is high'), (lim['low_below_GBps'], f'{lim["low_below_GBps"]:g} GB/s: below is low')):` | Loop over the two limits, each with a text: above the upper limit is high, below the lower limit is low. |
| 866 | `            o.append(f'<line x1="{L}" y1="{fx(Y(v), 1)}" x2="{W-R}" y2="{fx(Y(v), 1)}" stroke="{MUTED}" stroke-dasharray="4 3"/>')` | Draws a dashed dark grey horizontal line at the limit. |
| 867 | `            o.append(f'<text x="{W-R+8}" y="{fx(Y(v)+4, 1)}" class="ax">{lab}</text>')` | Writes the text of the limit at the right of the panel. |
| 868 | `        boxes = []` | `boxes`: the boxes of the texts that are placed already. The value labels keep away from them. |
| 869 | `        for v in (ymin, ymax):` | Loop over the two ends of the vertical axis. |
| 870 | `            o.append(f'<text x="{L-6}" y="{fx(Y(v)+4, 1)}" text-anchor="end" class="ax">{fx(v, 1)}</text>')` | Writes the value of the end with 1 decimal, at the left of the panel. |
| 871 | `            boxes.append((L - 36, Y(v) - 6, L - 6, Y(v) + 6))` | Adds the box of this text to the list. |
| 872 | `        for i in range(0, nmax, 5):` | Loop over every fifth interval number. |
| 873 | `            o.append(f'<text x="{fx(X(i), 1)}" y="{y0+ph+14}" text-anchor="middle" class="ax">{i}</text>')` | Writes the interval number under the panel. |
| 874 | `        r = p['rates_GBps']` | `r`: the rates of the process, in time order. |
| 875 | `        if not r: continue` | A process without rates gets an empty panel. |
| 876 | `        o.append(f'<polyline points="{" ".join(f"{fx(X(i), 1)},{fx(Y(v), 1)}" for i, v in enumerate(r))}" fill="none" stroke="{C0}" stroke-width="2"/>')` | Draws the blue line that joins the rates of the intervals. |
| 877 | `        usable = p.get('labels_usable', True)` | `usable`: whether the level labels of this process are usable. |
| 878 | `        for i, v in enumerate(r):` | Loop over the intervals. |
| 879 | `            tip = f'interval {i}: {fx(v, 2)} GB/s' + (f' ({p["levels"][i]})' if usable else '')` | `tip`: the hover text of the point: the interval number and the rate with 2 decimals. The level label is added in brackets when the labels are usable. |
| 880 | `            o.append(f'<circle cx="{fx(X(i), 1)}" cy="{fx(Y(v), 1)}" r="3" fill="{C0}" stroke="#fff" stroke-width="1"><title>{tip}</title></circle>')` | Draws a blue dot with the radius 3 at the rate of the interval. |
| 881 | `        segs = [(X(i), Y(r[i]), X(i + 1), Y(r[i + 1])) for i in range(len(r) - 1)]` | `segs`: the pieces of the line, each from one interval to the next. |
| 882 | `        hl = [Y(lim['high_above_GBps']), Y(lim['low_below_GBps'])]` | `hl`: the heights of the two dashed lines. |
| 883 | `        want = list(dict.fromkeys([r.index(min(r)), r.index(max(r)), 0, len(r) - 1] + [c['at_interval'] for c in p['changes']]))` | `want`: the intervals that get a value label, each once: the lowest rate, the highest rate, the first interval, the last interval, and the first interval after each level change. |
| 884 | `        for i in want:` | Loop over these intervals. |
| 885 | `            txt = fx(r[i], 2)` | `txt`: the rate with 2 decimals. |
| 886 | `            got = place_label(X(i), Y(r[i]), 6.4 * len(txt) + 2, i == 0, i == len(r) - 1, r[i] == min(r), y0, y0 + ph, boxes, segs, hl, (L, W - R))` | `got`: a free place for the label (line 829). The width of the text is estimated as 6.4 units per character plus 2. The label must stay inside the panel and must not touch the boxes, the line or the dashed lines. One place is the exception: the label of interval 0 may also stand in the left margin, beside its point (line 838). |
| 887 | `            if not got:` | Tests whether no place was found. |
| 888 | `                left_out += 1; continue` | Counts the label as left out. `continue` goes to the next label. |
| 889 | `            anchor, tx, base = got` | Takes the alignment, the position and the baseline of the place. |
| 890 | `            o.append(f'<text x="{fx(tx, 1)}" y="{fx(base, 1)}" text-anchor="{anchor}" class="val">{txt}</text>')` | Writes the label. |
| 891 | `    o.append(f'<text x="{L+(W-L-R)/2}" y="{H-8}" text-anchor="middle" class="ax">interval number in the process (each interval is at least 0.3 s)</text>')` | Writes the title of the horizontal axis under the last panel: the interval number in the process, with the note that each interval is at least 0.3 s long. |
| 892 | `    o.append(f'<text x="14" y="{top+ph/2}" text-anchor="middle" class="ax" transform="rotate(-90 14 {top+ph/2})">rate, GB/s</text>')` | Writes the title of the vertical axis beside the first panel, turned by 90 degrees: the rate in GB/s. |
| 893 | `    o.append('</svg>')` | Closes the drawing. |
| 894 | `    return '\n'.join(o), ymin, left_out` | Returns three values: the drawing as one text, the lower end of the vertical axis, and the number of labels that were left out. |

### Texts for the check of the level limits and for the level labels (lines 897 to 929)

| Line | Source | Explanation |
|---:|---|---|
| 897 | `def level_check_items(s):` | Starts the function `level_check_items`. It builds one list item per CPU about the two level limits. |
| 898 | `    """One list item per CPU: the result of the check of the two level limits against the rates of this run (choice C9)."""` | Text of the function: each item gives the result of the check of the limits against the rates of this run (choice C9 of the analysis script). |
| 899 | `    lv = s.get('level_check') or {}` | `lv`: the result of the level check from the json file, or an empty dictionary. |
| 900 | `    li = []` | `li`: the list items, empty at first. |
| 901 | `    for cpu, c in (lv.get('cpus') or {}).items():` | Loop over the CPUs of the check. |
| 902 | `        t = f"<li>CPU {cpu} ({pl(c['n'], 'interval', 'intervals')}, {fx(c['min'])} to {fx(c['max'])} GB/s). "` | `t`: the item of the CPU. It starts with the CPU number, the number of intervals, and the lowest and the highest rate in GB/s. |
| 903 | `        for x in c['limits']:` | Loop over the two limits. |
| 904 | `            if x['empty_range'] is None:` | The case that all rates lie on one side of the limit. |
| 905 | `                t += f"Limit {x['limit']:g} GB/s: all rates lie on one side of it. "` | Adds a sentence that says so. |
| 906 | `            elif x['separates']:` | The case that the limit separates the rates. |
| 907 | `                t += (f"Limit {x['limit']:g} GB/s: it separates the rates. The nearest rates are {fx(x['nearest_below'])} and {fx(x['nearest_at_or_above'])} GB/s, "` | Adds a sentence: the limit separates the rates, with the nearest rate on each side. |
| 908 | `                      f"so the empty range around the limit is {fx(x['empty_range'])} GB/s wide. ")` | Continues the sentence: the width of the empty range around the limit in GB/s. |
| 909 | `            else:` | The case that the limit does not separate the rates. |
| 910 | `                t += (f"Limit {x['limit']:g} GB/s: it does not separate the rates. {x['n_below']} rates are below it and {x['n_at_or_above']} are at or above it. "` | Adds sentences: the limit does not separate the rates, with the number of rates below it and the number at or above it. |
| 911 | `                      f"The nearest rates are {fx(x['nearest_below'])} and {fx(x['nearest_at_or_above'])} GB/s. {x['n_within']} of the {c['n']} rates lie within {fx(lv['gap_min_GBps'])} GB/s of the limit. ")` | Continues: the nearest rate on each side, and how many of the rates of the CPU lie within the smallest accepted distance of the limit. |
| 912 | `        t += ('The level labels are used for this CPU. They stay provisional.' if c['labels_usable'] else` | Ends the item. With usable labels it says that the level labels are used for this CPU and stay provisional. |
| 913 | `              'So the level labels are not usable for this CPU in this run. This page reports the CPU by its rates.')` | Continues line 912: if not, it says that the level labels are not usable for this CPU in this run, and that the page reports the CPU by its rates. |
| 914 | `        li.append(t + '</li>')` | Closes the item and adds it. |
| 915 | `    return li` | Returns the items. |
| 918 | `def a5_usable(p):` | Starts the function `a5_usable`. |
| 919 | `    return p.get('labels_usable', True)` | Returns whether the level labels of a process are usable. A process without that entry counts as usable. |
| 922 | `def a5_other_labels(p):` | Starts the function `a5_other_labels`. It builds a sentence for a process that has usable labels and no change between low and high. |
| 923 | `    """For a process with usable labels and no change between low and high: which labels its intervals have."""` | Text of the function: the sentence says which labels the intervals of the process have. |
| 924 | `    have = [l for l in ('low', 'changing', 'high') if p['n_' + l]]` | `have`: the labels among low, changing and high that at least one interval of the process has. |
| 925 | `    if len(have) == 1:` | The case of one label. |
| 926 | `        return f"All its intervals were {have[0]}."` | Returns the sentence that all intervals of the process had that label. |
| 927 | `    return f"Its intervals changed only between {' and '.join(have)}."` | With more labels: returns the sentence that the intervals changed only between these labels. One of them is then `changing`. |

### Function `sec_a5`: the section on step A5 (lines 930 to 993)

| Line | Source | Explanation |
|---:|---|---|
| 930 | `def sec_a5(s):` | Starts the function `sec_a5`. It builds the section on step A5: `asmread` with one thread at 8 MiB, 30 intervals per process. |
| 931 | `    o = ['<h2 id="a5">A5: asm read with one thread at 8 MiB, 30 intervals</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 932 | `    procs = s['A5']['processes']; lim = s['limits']` | `procs`: the processes of step A5. `lim`: the limits. |
| 933 | `    if not procs:` | Tests whether the step has no process. |
| 934 | `        return '\n'.join(o) + missing('Step A5 has no usable data. The measurement that is missing: 2 processes on CPU 2 and 2 processes on CPU 41, 30 intervals each.')` | Returns the heading with an `Insufficient data` notice that names the missing measurement: 2 processes on CPU 2 and 2 on CPU 41, 30 intervals each. |
| 935 | `    lv = s.get('level_check') or {}; lo, hi = lim['low_below_GBps'], lim['high_above_GBps']` | `lv`: the result of the level check. `lo` and `hi`: the two limits, 69 GB/s and 70.5 GB/s. |
| 936 | `    o.append(f"<p>An interval is low below {lo:g} GB/s, high above {hi:g} GB/s, and changing otherwise. These limits are provisional. The plan asks to check them against the new data before they are used [Ref1].</p>")` | Adds a paragraph: the definition of low, high and changing with the two limits. It says that the limits are provisional and that the plan asks to check them against the new data. |
| 937 | `    li = level_check_items(s)` | `li`: the items of the check per CPU (line 897). |
| 938 | `    if li:` | Only when the check has items. |
| 939 | `        o.append(f"<h3>Check of the two limits against the rates of this run</h3><p>The plan gives no test for this check. The analysis script uses this one (choice C9) [Ref5]. "` | Adds a sub-heading and a paragraph: the plan gives no test for this check, and the analysis script uses choice C9. |
| 940 | `                 f"A limit does not separate the rates of a CPU if rates lie on both sides of it and the empty range around it is smaller than {fx(lv['gap_min_GBps'])} GB/s. "` | Continues the paragraph: the rule of the test, with the smallest empty range from the json file. |
| 941 | `                 "The rates of A5 and A6 on one CPU are taken together.</p><ul>" + ''.join(li) + '</ul>')` | Continues the paragraph: the rates of A5 and A6 on one CPU are taken together. Then the list of the items. |
| 942 | `        lc = s['level_counts_8MiB']` | `lc`: the counts of the levels over all intervals of A5 and A6. |
| 943 | `        nch = sum(p['n_changing'] for p in procs if not a5_usable(p))` | `nch`: the number of changing intervals in the A5 processes whose labels are not usable. |
| 944 | `        t = (f"Over all {lc['n']} intervals of A5 and A6, the rates were {rtxt(lc['rate'], unit='GB/s')}. The widest empty ranges of these rates are "` | `t`: a paragraph: the number of all intervals of A5 and A6 and the range of their rates in GB/s. The sentence about the widest empty ranges starts here. |
| 945 | `             + ' and '.join(f"{fx(g['low'])} to {fx(g['high'])} GB/s ({fx(g['width'])} GB/s wide)" for g in lv['largest_empty_ranges']) + '. '` | Continues `t`: the two widest empty ranges between neighbouring rates, each with its ends and its width. |
| 946 | `             f"By the two provisional limits alone, {lc['low']} intervals would be low, {lc['changing']} changing and {lc['high']} high. ")` | Continues `t`: how many intervals would be low, changing and high by the two provisional limits alone. |
| 947 | `        if nch:` | Only when `nch` is above 0. |
| 948 | `            t += f"{nch} of the {lc['changing']} changing intervals are on a CPU whose labels are not usable. "` | Adds how many of the changing intervals are on a CPU whose labels are not usable. |
| 949 | `        o.append(f'<p>{t}The A6 processes without 2 MiB pages are included in these counts.</p>')` | Adds the paragraph with a fixed end: the A6 processes without pages of 2 MiB are included in these counts. |
| 950 | `    c, ymin, left_out = a5_chart(procs, lim)` | Draws the chart (line 850). `ymin` is the lower end of its vertical axis, and `left_out` is the number of labels without a place. |
| 951 | `    o.append(c)` | Adds the chart. |
| 952 | `    o.append(f'<p class="cap">One panel per process, in time order. All panels share one vertical scale. The vertical axis starts at {fx(ymin, 1)} GB/s, not at 0, so that a change between the two levels is visible. The grey band lies between the two provisional limits. '` | Adds its caption: one panel per process in time order, one vertical scale for all panels, and the value at which the axis starts. It says that the axis does not start at 0, and gives the reason: a change between the two levels is then visible. It also says that the grey band lies between the two provisional limits. |
| 953 | `             'Labelled points: first, last, highest, lowest, and the first interval after a change between low and high.'` | Continues the caption: which points carry a label. |
| 954 | `             + (f' {pl(left_out, "label was", "labels were")} left out, because no free place was found.' if left_out else '') + '</p>')` | Continues the caption: when labels were left out, their number and the reason, no free place. |
| 955 | `    o.append('<div class="tw"><table><tr><th>CPU</th><th>Process</th><th>Waited before start (s)</th><th>Intervals</th><th>Rate GB/s, lowest to highest</th><th>Rate of interval 0, GB/s</th><th>Rate of the last interval, GB/s</th>'` | Opens the table. This line holds the headings for the CPU, the process, the wait before the start, the intervals, the range of the rate, and the rates of interval 0 and of the last interval. |
| 956 | `             f'<th>Intervals below {lo:g} GB/s</th><th>Low</th><th>Changing</th><th>High</th><th>Changes between low and high</th><th>Sequence (L low, c changing, H high)</th></tr>')` | Continues the headings: the intervals below the lower limit, the numbers of low, changing and high intervals, the changes between low and high, and the sequence of the labels. |
| 957 | `    for p in procs:` | Loop over the processes. |
| 958 | `        r = p['rates_GBps']` | `r`: the rates of the process. |
| 959 | `        head = (f"<tr><td>{p['cpu']}</td><td>{p['proc']}</td><td>{p['waited_s']:g}</td><td>{p['n_intervals']}</td><td>{rtxt(p['rate'])}</td><td>{f2(r[0] if r else None)}</td><td>{f2(r[-1] if r else None)}</td>"` | `head`: the first cells of the row: CPU, process number, waited seconds, number of intervals, range of the rates, and the rates of the first and of the last interval. |
| 960 | `                f"<td>{p.get('n_below_low_limit', p['n_low'])}</td>")` | Continues `head`: the number of intervals below the lower limit. |
| 961 | `        if a5_usable(p):` | The case that the labels of the process are usable. |
| 962 | `            ch = '; '.join(f"{x['from_level']} to {x['to_level']} at interval {x['at_interval']} (counted from 0)" for x in p['changes']) or 'none'` | `ch`: the level changes as text: from which label to which, and at which interval, counted from 0. Without a change the text is `none`. |
| 963 | `            seq = ''.join(dict(low='L', high='H', changing='c')[l] for l in p['levels'])` | `seq`: one letter per interval: `L` for low, `H` for high and `c` for changing. |
| 964 | `            o.append(head + f"<td>{p['n_low']}</td><td>{p['n_changing']}</td><td>{p['n_high']}</td><td>{ch}</td><td><code>{seq}</code></td></tr>")` | Adds the row with the three counts, the changes and the sequence. |
| 965 | `        else:` | The case that the labels are not usable. |
| 966 | `            o.append(head + '<td>-</td><td>-</td><td>-</td><td>-</td><td>labels not used for this CPU</td></tr>')` | Adds the row with hyphens in these cells and the words `labels not used for this CPU`. |
| 967 | `    o.append('</table></div>')` | Closes the table. |
| 968 | `    li = []` | `li`: the list items of the statements, empty at first. |
| 969 | `    for p in procs:` | Loop over the processes. |
| 970 | `        n = f"CPU {p['cpu']}, process {p['proc']}"; r = p['rates_GBps']` | `n`: the name of the process, its CPU and process number. `r`: its rates. |
| 971 | `        if not a5_usable(p):` | The case that the labels are not usable. |
| 972 | `            li.append(f"<li>{n}: the labels are not used. The rate was {fx(r[0])} GB/s in interval 0 and {fx(r[-1])} GB/s in the last interval. "` | Adds an item: the labels are not used. It gives the rates of interval 0 and of the last interval. |
| 973 | `                      f"The lowest rate was {fx(min(r))} GB/s (interval {r.index(min(r))}), and the highest was {fx(max(r))} GB/s (interval {r.index(max(r))}). "` | Continues the item: the lowest and the highest rate, each with the number of its interval. |
| 974 | `                      f"{p['n_below_low_limit']} of the {p['n_intervals']} rates were below {lo:g} GB/s. Intervals are counted from 0.</li>")` | Continues the item: how many of the rates were below the lower limit. A fixed sentence says that intervals are counted from 0. |
| 975 | `        elif p['changes']:` | The case that a change between low and high was found. |
| 976 | `            li.append(f"<li>{n}: " + '; '.join(f"a change from {x['from_level']} to {x['to_level']} was observed. The first {x['to_level']} interval was number {x['at_interval']} (counted from 0)." for x in p['changes'])` | Adds an item: for each change, from which label to which, and the number of the first interval with the new label. |
| 977 | `                      + f" {p['n_low']} intervals were low, {p['n_changing']} changing and {p['n_high']} high.</li>")` | Continues the item: the numbers of low, changing and high intervals. |
| 978 | `        else:` | The case of usable labels and no change. |
| 979 | `            li.append(f"<li>{n}: no change between low and high was observed in {p['n_intervals']} intervals. {p['n_low']} intervals were low, {p['n_changing']} changing and {p['n_high']} high. {a5_other_labels(p)}</li>")` | Adds an item: no change between low and high was observed in that many intervals, the three counts, and the sentence of line 922. |
| 980 | `    by = {(p['cpu'], p['proc']): p for p in procs}` | `by`: the processes under the pair of CPU and process number. |
| 981 | `    for pr in s['A5']['pairs']:` | Loop over the pairs of first and second process on one CPU. |
| 982 | `        if not pr['have_both']:` | A pair of which one process is missing. |
| 983 | `            li.append(f"<li>CPU {pr['cpu']}: {ID}. One of the two processes of the pair has no usable block.</li>"); continue` | Adds an item with `Insufficient data` for the CPU. `continue` goes to the next pair. |
| 984 | `        p1, p2 = by[(pr['cpu'], 1)], by[(pr['cpu'], 2)]` | `p1` and `p2`: the first and the second process of the pair. |
| 985 | `        t = (f"<li>CPU {pr['cpu']}: the second process did not follow at once. It waited {pr['second_waited_s']:g} s for a quiet system. " if pr['second_not_at_once']` | `t`: an item about the second process. When it waited more than 0 s, the item says that it did not follow at once, and gives the wait for a quiet system in seconds. |
| 986 | `             else f"<li>CPU {pr['cpu']}: the second process followed with a wait of 0 s. ")` | Continues `t`: in the other case it says that the second process followed with a wait of 0 s. |
| 987 | `        t += f"The last interval of the first process had {fx(p1['rates_GBps'][-1])} GB/s, and interval 0 of the second had {fx(p2['rates_GBps'][0])} GB/s"` | Adds the rate of the last interval of the first process and the rate of interval 0 of the second process. |
| 988 | `        t += f" ({pr['last_level_first']}, then {pr['first_level_second']}).</li>" if a5_usable(p1) else '.</li>'` | Adds the two level labels in brackets, only when the labels of the first process are usable. |
| 989 | `        li.append(t)` | Adds the item. |
| 990 | `    o.append('<p>Observed in screening:</p><ul>' + ''.join(li) + '</ul>')` | Adds the list under the words `Observed in screening:`. |
| 991 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `sec_a6`: the section on step A6 (lines 994 to 1041)

| Line | Source | Explanation |
|---:|---|---|
| 994 | `def sec_a6(s):` | Starts the function `sec_a6`. It builds the section on step A6: `asmread` with one thread at 8 MiB, with and without pages of 2 MiB. |
| 995 | `    o = ['<h2 id="a6">A6: with and without 2 MiB pages</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 996 | `    a = s['A6']` | `a`: the summary of step A6 from the json file. |
| 997 | `    if not a['processes']:` | Tests whether the step has no process. |
| 998 | `        return '\n'.join(o) + missing('Step A6 has no usable data. The measurement that is missing: 8 processes with and 8 processes without <code>--no-thp</code>.')` | Returns the heading with an `Insufficient data` notice that names the missing measurement: 8 processes with and 8 without `--no-thp`. |
| 999 | `    rows = []; allv = []` | `rows`: the two rows of the chart. `allv`: all process medians. |
| 1000 | `    for kind, name in (('thp', '2 MiB pages allowed'), ('nothp', '--no-thp (4 KiB pages)')):` | Loop over the two kinds, each with its row name: pages of 2 MiB allowed, and `--no-thp` with pages of 4 KiB. |
| 1001 | `        pp = [p for p in a['processes'] if p['kind'] == kind]` | `pp`: the processes of this kind. |
| 1002 | `        pts = [(p['median_GBps'], f"{p['tag']}: median {fx(p['median_GBps'], 2)} GB/s of {len(p['rates_GBps'])} intervals ({', '.join(f2(v) for v in p['rates_GBps'])})") for p in pp]` | `pts`: one point per process: the median of its rates, and a hover text with the tag, the median, the number of intervals and the single rates. |
| 1003 | `        allv += [v for v, _ in pts]` | Adds the medians to `allv`. |
| 1004 | `        m = a[kind]['process_medians']` | `m`: the range of the process medians of this kind. |
| 1005 | `        rows.append((name, pts, f"median {f2(m['median'])} GB/s ({rtxt(m)})" if m['n'] else ID))` | Adds the chart row: the name, the points, and a label with the median of the process medians in GB/s and their range. Without processes the label is `Insufficient data`. |
| 1006 | `    lo, hi = min(allv), max(allv); pad = max((hi - lo) * 0.08, 0.5)` | `lo` and `hi`: the lowest and the highest process median. `pad`: 8 % of their distance, at least 0.5 GB/s. |
| 1007 | `    xmin, xmax = int(lo - pad), int(hi + pad) + 1` | `xmin` and `xmax`: the ends of the horizontal axis, whole numbers of GB/s around the values. The axis does not start at 0. |
| 1008 | `    stp = max(1, round((xmax - xmin) / 8))` | `stp`: the distance of the tick marks: one eighth of the axis length, rounded, at least 1 GB/s. |
| 1009 | `    lim = s['limits']` | `lim`: the limits. |
| 1010 | `    vl = [(v, f'{v:g}') for v in (lim['low_below_GBps'], lim['high_above_GBps']) if xmin < v < xmax]` | `vl`: the level limits that lie inside the axis, each with its value as text. They become dashed lines. |
| 1011 | `    o.append(strip_chart(rows, xmin, xmax, list(range(xmin, xmax + 1, stp)), f'median rate of one process, GB/s (axis starts at {xmin}, not at 0)', 'Rate with and without 2 MiB pages', vlines=vl))` | Adds the chart (line 89): the median rate of one process in GB/s. The axis title says where the axis starts and that this is not 0. |
| 1012 | `    cap = 'One dot is one process: the median of its 3 intervals. Each row is labelled with the median of its processes and their range.'` | `cap`: the caption: one dot is one process, the median of its 3 intervals, and each row carries the median of its processes and their range. The number 3 is fixed text. |
| 1013 | `    if len(vl) == 2:` | The case that both limits lie inside the axis. |
| 1014 | `        cap += f' The two dashed lines are the provisional limits of the level, {vl[0][1]} and {vl[1][1]} GB/s.'` | Adds a sentence: the two dashed lines are the provisional limits of the level, with their values. |
| 1015 | `    elif len(vl) == 1:` | The case that one limit lies inside the axis. |
| 1016 | `        cap += f' The dashed line is one provisional limit of the level, {vl[0][1]} GB/s. The other limit lies outside the range of the axis.'` | Adds a sentence: the dashed line is one provisional limit, and the other lies outside the range of the axis. |
| 1017 | `    o.append(f'<p class="cap">{cap}</p>')` | Adds the caption. |
| 1018 | `    cpus = (s.get('level_check') or {}).get('cpus') or {}` | `cpus`: the level check per CPU. |
| 1019 | `    labels_ok = all(cpus.get(str(p.get('cpu')), {}).get('labels_usable', True) for p in a['processes'])` | `labels_ok`: true when the level labels are usable for the CPU of every A6 process. |
| 1020 | `    t = "Observed in screening: "` | `t`: the statement of the section. It starts with the words `Observed in screening:`. |
| 1021 | `    if 'nothp_minus_thp_GBps' in a:` | The case that both kinds have processes. |
| 1022 | `        t += (f"the median rate was {fx(a['thp']['process_medians']['median'], 2)} GB/s with 2 MiB pages allowed and {fx(a['nothp']['process_medians']['median'], 2)} GB/s with <code>--no-thp</code>. "` | Adds the median rate with pages of 2 MiB allowed and the median rate with `--no-thp`, in GB/s with 2 decimals. Each is the median of the process medians. |
| 1023 | `              f"The difference is {fs(a['nothp_minus_thp_GBps'], 2)} GB/s ({fs(a['nothp_minus_thp_pct'], 1)} %). The two ranges of the process medians {'overlap' if a['process_ranges_overlap'] else 'do not overlap'}. ")` | Adds the difference in GB/s and in percent, with a sign, and whether the two ranges of the process medians overlap. |
| 1024 | `        if labels_ok:` | Only when the level labels are usable. |
| 1025 | `            for kind, name in (('thp', 'With 2 MiB pages allowed'), ('nothp', 'With <code>--no-thp</code>')):` | Loop over the two kinds. |
| 1026 | `                t += f"{name}, {a[kind]['n_low']} intervals were low, {a[kind]['n_changing']} changing and {a[kind]['n_high']} high. "` | Adds for each kind how many of its intervals were low, changing and high. |
| 1027 | `        else:` | The case that the labels are not usable. |
| 1028 | `            t += 'The level labels are not used for the CPU of this step (see the check in section A5). '` | Adds a sentence: the level labels are not used for the CPU of this step, with a pointer to the check in the section on A5. |
| 1029 | `    else:` | The case that one kind has no process. |
| 1030 | `        t = f"{ID}. One of the two kinds has no usable process."` | The statement is then `Insufficient data`, with that reason. |
| 1031 | `    o.append(f'<p class="take">{t}</p>')` | Adds the statement as a highlighted paragraph. |
| 1032 | `    bad = [p['tag'] for p in a['processes'] if not p['thp_line_ok']]` | `bad`: the tags of the processes whose printed page setting is not the one that their launch asked for. |
| 1033 | `    o.append(f"<p>The benchmark prints its page setting in each block. {len(a['processes']) - len(bad)} of {len(a['processes'])} blocks show the setting that their launch asked for." + (f" Not as asked: {', '.join(bad)}." if bad else '') + '</p>')` | Adds a paragraph: the benchmark prints its page setting in each block. It gives how many of the blocks show the setting that their launch asked for, and lists the others. |
| 1034 | `    o.append(f'<p class="miss"><b>{ID}.</b> The share of the buffer that was on 2 MiB pages. "2 MiB pages allowed" means only that the program asked for them. Step B4 records the share before every interval [Ref1].</p>')` | Adds an `Insufficient data` notice: the share of the buffer that was on pages of 2 MiB is not known. The setting only means that the program asked for such pages. Step B4 records the share before every interval. |
| 1035 | `    o.append('<details><summary>Every A6 process</summary><div class="tw"><table><tr><th>Launch</th><th>Page setting printed</th><th>Waited (s)</th><th>Rate of the 3 intervals, GB/s</th><th>Median, GB/s</th><th>Levels (provisional)</th></tr>')` | Opens a part that the reader can unfold, with one row per A6 process. The six column headings are the launch, the printed page setting, the wait, the rates of the 3 intervals, the median, and the provisional levels. |
| 1036 | `    for p in a['processes']:` | Loop over the processes. |
| 1037 | `        o.append(f"<tr><td>{e(p['tag'])}</td><td>{e(p['thp_line'] or '-')}</td><td>{p['waited_s']:g}</td><td>{', '.join(f2(v) for v in p['rates_GBps'])}</td><td>{f2(p['median_GBps'])}</td><td>{', '.join(p['levels']) if labels_ok else 'not used'}</td></tr>")` | Adds the row of the process. The last cell shows the level labels of its intervals, or the words `not used`. |
| 1038 | `    o.append('</table></div></details>')` | Closes the table and the unfolding part. |
| 1039 | `    return '\n'.join(o)` | Returns the section as one text. |

### Functions `a7_files`, `a7_codes_txt` and `sec_a7`: the section on step A7 (lines 1042 to 1092)

| Line | Source | Explanation |
|---:|---|---|
| 1042 | `def a7_files(s):` | Starts the function `a7_files`. It collects the files of step A7 from all result folders. |
| 1043 | `    """{file name: (folder, entry)} of the A7 files. If a file exists in several folders, the last folder is used."""` | Text of the function: the result maps each file name to its folder and its entry. When a file exists in several folders, the last folder is used. |
| 1044 | `    return {n: (x['folder'], v) for x in s['env'] for n, v in x['a7'].items()}` | Builds that dictionary from the `env.txt` entries of the json file. The folders are in time order, so a later folder replaces an earlier one. |
| 1047 | `def a7_codes_txt(p):` | Starts the function `a7_codes_txt`. It prints the counter codes of one PMU as a short text for the first table of the page. |
| 1048 | `    """One sentence group with the PMU type and the event codes of the five events of handoff B.8."""` | Text of the function: the text holds the PMU type and the event codes of the five events of section B.8 of the handoff note. |
| 1049 | `    t = f"PMU {p['name']}, type number {p['type'] or 'not listed'}. "` | `t`: the name of the PMU and its type number, or the words `not listed`. |
| 1050 | `    t += ' '.join(f"{x['event'].capitalize()} = {x['name']} {x['code']}." if x['code'] else f"{x['event'].capitalize()}: {ID}, the file has no event named {x['name']}." for x in p['b8'])` | Adds one sentence per event: the words of the handoff note, the event name and the code. For an event without a code the sentence is `Insufficient data`, with the note that the file has no event of that name. |
| 1051 | `    return t` | Returns the text. |
| 1054 | `def sec_a7(s):` | Starts the function `sec_a7`. It builds the section on step A7: the vector length and the event lists. |
| 1055 | `    o = ['<h2 id="a7">A7: vector length and event lists</h2>']` | `o`: the pieces of the section, starting with its heading. |
| 1056 | `    files = a7_files(s)` | `files`: the files of step A7 (line 1042). |
| 1057 | `    if not files:` | Tests whether there is none. |
| 1058 | `        return '\n'.join(o) + missing('Step A7 has no files. The measurement that is missing: the files <code>A7-sve.txt</code>, <code>A7-perf-list.txt</code>, <code>A7-pmu-devices.txt</code> and <code>A7-core-events.txt</code>.')` | Returns the heading with an `Insufficient data` notice that names the four missing files. |
| 1059 | `    o.append('<p>This step measures no rate. It reads values that later steps need.</p>')` | Adds a fixed paragraph: this step measures no rate. It reads values that later steps need. |
| 1060 | `    o.append('<h3 id="codes">Consequence for Part C: the counter codes</h3>')` | Adds the sub-heading of the part on Part C: the counter codes. |
| 1061 | `    o.append('<p>The counter runs of Part C take the PMU type and the event codes from the file <code>A7-core-events.txt</code> (handoff, section B.8) [Ref2]. '` | Adds a paragraph: the counter runs of Part C take the PMU type and the event codes from the file `A7-core-events.txt`, by section B.8 of the handoff note. |
| 1062 | `             'PMU means performance monitoring unit: the counter hardware of a core.</p>')` | Continues the paragraph: PMU means performance monitoring unit, the counter hardware of a core. |
| 1063 | `    ce = files.get('A7-core-events.txt')` | `ce`: the folder and the entry of the file `A7-core-events.txt`, or `None`. |
| 1064 | `    pmus = (ce[1].get('pmu_list') or []) if ce else []` | `pmus`: the PMU entries of that file, or an empty list. |
| 1065 | `    if not pmus:` | Tests whether no PMU was found. |
| 1066 | `        o.append(missing('The PMU type and the event codes for Part C. The file <code>A7-core-events.txt</code> is missing or lists no core PMU. The measurement that is missing: the <code>type</code> file and the <code>events/</code> files of the core PMU in <code>/sys/bus/event_source/devices/</code>.'))` | Adds an `Insufficient data` notice: the PMU type and the event codes for Part C. It names the files in `/sys/bus/event_source/devices/` that would give them. |
| 1067 | `    else:` | The case with at least one PMU. |
| 1068 | `        o.append(f"<p>The file <code>{e(ce[0])}/A7-core-events.txt</code> lists {pl(len(pmus), 'core PMU', 'core PMUs')} [Ref7].</p>")` | Adds a paragraph: the path of the file and the number of core PMUs that it lists. |
| 1069 | `        for p in pmus:` | Loop over the PMUs. |
| 1070 | `            o.append(f"<p>Name of the PMU: <code>{e(p['name'])}</code>. Its type number for <code>perf_event_open</code> is {e(p['type'] or ID)} (line {p['line']} of the file). The file lists {pl(p['n_events'], 'event', 'events')} for it. "` | Adds a paragraph: the name of the PMU, its type number for the system call `perf_event_open` with the line of the file that holds it, and the number of events that the file lists for it. |
| 1071 | `                     'The five events of section B.8 have these codes in the file:</p>')` | Continues the paragraph: the words that introduce the table of the five events. |
| 1072 | `            o.append('<div class="tw"><table class="pt"><tr><th>Event of B.8</th><th>Name in the file</th><th>Code (<code>event=</code>)</th><th>Line of the file</th></tr>'` | Opens the table with four column headings: the event of B.8, the name in the file, the code, and the line of the file. |
| 1073 | `                     + ''.join(f"<tr><td>{e(x['event'])}</td><td><code>{e(x['name'])}</code></td><td>{'<code>' + e(x['code']) + '</code>' if x['code'] else ID + ': the file has no event of this name'}</td><td>{x['line'] or '-'}</td></tr>" for x in p['b8'])` | Adds one row per event. An event that the file does not list gets `Insufficient data` in the code cell and a hyphen in the line cell. |
| 1074 | `                     + '</table></div>')` | Closes the table. |
| 1075 | `            for x in p['b8_other']:` | Loop over the second candidates that the file lists. |
| 1076 | `                o.append(f"<p>The file also lists <code>{e(x['name'])}</code> with the code <code>{e(x['code'])}</code> (line {x['line']}). It is a second candidate for the {e(x['event'])}. This page does not choose between the two names.</p>")` | Adds a paragraph: the file also lists this event name with its code and line. It is a second candidate for the same event, and the page does not choose between the two names. |
| 1077 | `        o.append('<p>The handoff names the five events in words. Which name of the file belongs to each event is a choice of the analysis script (choice C10) [Ref5].</p>')` | Adds a fixed paragraph: the handoff note names the five events in words. Which name of the file belongs to each event is choice C10 of the analysis script. |
| 1078 | `        o.append(f'<p class="miss"><b>{ID}.</b> Whether these events can be opened without root on CRB. Part A did not try it. The short test of section B.8 (<code>bwx --count</code> with one thread) shows it [Ref2].</p>')` | Adds an `Insufficient data` notice: whether these events can be opened without root on CRB. Part A did not try it. The short test of section B.8 shows it. |
| 1079 | `    o.append('<h3>Vector length and lists</h3><ul>')` | Adds the sub-heading for the vector length and the lists, and opens a list. |
| 1080 | `    sve = files.get('A7-sve.txt')` | `sve`: the folder and the entry of the file `A7-sve.txt`, or `None`. |
| 1081 | `    if sve and sve[1].get('sve_vector_length_bytes'):` | The case that the file holds a number. |
| 1082 | `        b = int(sve[1]['sve_vector_length_bytes'])` | `b`: the vector length in bytes, as a number. |
| 1083 | `        o.append(f"<li>The default SVE vector length of a process is {b} bytes ({b * 8} bits) [Ref8]." + (' 128 bits is the smallest SVE vector length.' if b == 16 else '')` | Adds an item: the default SVE vector length of a process in bytes and in bits (the bytes times 8). When the value is 16 bytes, a fixed sentence adds that 128 bits is the smallest SVE vector length. |
| 1084 | `                 + ' The plan needs this value for the old write kernel. The bytes of one loop turn of that kernel are not recorded [Ref1].</li>')` | Continues the item: the plan needs this value for the old write kernel, whose bytes per loop turn are not recorded. |
| 1085 | `    else:` | The case without a number. |
| 1086 | `        o.append(f"<li>{ID}: the SVE vector length. The file <code>A7-sve.txt</code> is missing or holds no number.</li>")` | Adds an item with `Insufficient data` for the SVE vector length. |
| 1087 | `    for n, what, ref in (('A7-perf-list.txt', 'The list of <code>perf</code> events', 'Ref9'), ('A7-pmu-devices.txt', 'The list of counter devices', 'Ref10')):` | Loop over two files: the list of `perf` events and the list of counter devices, each with its text and its reference number. |
| 1088 | `        o.append(f"<li>{what} has {files[n][1]['lines']} lines [{ref}].</li>" if n in files else f"<li>{ID}: the file <code>{n}</code> is missing.</li>")` | Adds an item with the number of lines of the file and its reference. For a missing file the item is `Insufficient data`. |
| 1089 | `    o.append('</ul>')` | Closes the list. |
| 1090 | `    return '\n'.join(o)` | Returns the section as one text. |

### Function `points_to`: one text per step for the first table (lines 1093 to 1179)

| Line | Source | Explanation |
|---:|---|---|
| 1093 | `def points_to(s):` | Starts the function `points_to`. It builds one short text per step for the last column of the table `What each step points to`. |
| 1094 | `    """One generated sentence group per step for the table 'What each result points to'."""` | Text of the function: each text is a group of sentences built from the data. |
| 1095 | `    d = s['q']['decision']; out = {}` | `d`: the decision of the test of the two groups. `out`: the result, one text per step. |
| 1096 | `    def miss(st_):` | Starts the inner function `miss`. |
| 1097 | `        return f'{ID}: step {st_} has no usable data.'` | Returns the text for a step without data: `Insufficient data`, and that the step has no usable data. |
| 1098 | `    # A1` | Comment: the text for step A1 follows. |
| 1099 | `    if s['A1']:` | The case that step A1 has data. |
| 1100 | `        t = []` | `t`: the sentences for A1, empty at first. |
| 1101 | `        rr = [r for st_ in ('A1', 'A2') for r in s[st_].get('read_old', {}).get('reps', []) if r['fastest_half']]` | `rr`: the repetitions of the old read kernel in A1 and A2 that have a fastest half. |
| 1102 | `        if rr:` | Only when there are such repetitions. |
| 1103 | `            allm0 = sum(1 for r in rr if r['fastest_half']['mesh0'] == [r['fastest_half']['n_half']] * 2)` | `allm0`: the number of these repetitions in which the lowest and the highest count of mesh 0 both equal the size of the half. The fastest half then lies on mesh 0 only. |
| 1104 | `            t.append(f"Old read: all {rr[0]['fastest_half']['n_half']} threads of the fastest half were on mesh 0 in {allm0} of the {len(rr)} repetitions of A1 and A2.")` | Adds a sentence for the old read kernel: in how many of its repetitions of A1 and A2 all threads of the fastest half were on mesh 0. |
| 1105 | `        w = write_hi_lo(s)` | `w`: the comparison of the highest with the lowest write totals (line 487). |
| 1106 | `        if w:` | Only when it has entries. |
| 1107 | `            t.append('Write kernels: ' + write_hi_lo_txt(w)[0].lower() + write_hi_lo_txt(w)[1:])` | Adds the sentences of line 500 after the words `Write kernels:`, with their first letter in lower case. |
| 1108 | `        for k in ('read_old', 'write_old', 'write_new', 'asmwrite'):` | Loop over four kernels: the old read kernel and the three write kernels. |
| 1109 | `            if k in s['A1'] and s['A1'][k]['mesh1_median']['n']:` | Takes a kernel only when A1 has thread rates of mesh 1 for it. |
| 1110 | `                x = s['A1'][k]` | `x`: the summary of the kernel in A1. |
| 1111 | `                t.append(f"{KNAME[k].capitalize()} in A1: median thread rate {fx(x['mesh0_median']['median'], 2)} GB/s on mesh 0 and {fx(x['mesh1_median']['median'], 2)} GB/s on mesh 1.")` | Adds a sentence with the median thread rate on mesh 0 and on mesh 1 in GB/s. |
| 1112 | `        out['A1'] = 'Observed in screening. ' + ' '.join(t)` | The text for A1: the words `Observed in screening.` and the sentences. |
| 1113 | `    else: out['A1'] = miss('A1')` | Without data the text for A1 is the one of line 1097. |
| 1114 | `    c = s['A1_A2']['kernels']` | `c`: the comparison of A1 with A2 per kernel. |
| 1115 | `    if c:` | The case that the comparison exists. |
| 1116 | `        no = [KNAME[k] for k in KORDER if k in c and not c[k]['ranges_overlap']]` | `no`: the printed names of the kernels whose two ranges do not overlap. |
| 1117 | `        t = ('Observed in screening. Change of the median total from the short to the long interval: '` | `t`: the text for A2. It starts with the words `Observed in screening.` and introduces the change of the median total from the short to the long interval. |
| 1118 | `             + ' '.join(f"{KNAME[k]} {fs(c[k]['change_GBps'], 2)} GB/s ({fs(c[k]['change_pct'], 1)} %)." for k in KORDER if k in c)` | Continues `t`: for each kernel the change in GB/s and in percent, with a sign. |
| 1119 | `             + f" The range of the long totals does not overlap the range of the short totals for {len(no)} of {len(c)} kernels" + (f" ({', '.join(no)})" if no else '') + '. '` | Continues `t`: for how many kernels the range of the long totals does not overlap the range of the short totals, with their names. |
| 1120 | `             + 'Long totals outside the short range: ' + ', '.join(f"{KNAME[k]} {c[k]['n_long_outside_short']} of {c[k]['n_long']}" for k in KORDER if k in c) + '. ')` | Continues `t`: for each kernel, how many long totals lie outside the short range. |
| 1121 | `        rd = s['A1_A2'].get('order_reading')` | `rd`: the reading of choice C11, or `None`. |
| 1122 | `        if rd:` | The case with a reading. |
| 1123 | `            dd = s['A1_A2']['old_minus_new_read_GBps']` | `dd`: the values of the difference between the old and the new read kernel. |
| 1124 | `            t += (f"Old read minus new read: {fs(dd['short'])} GB/s with the short interval and {fs(dd['long'])} GB/s with the long interval. "` | Adds the difference of the median totals, old read minus new read, with the short and with the long interval, in GB/s with a sign. |
| 1125 | `                  + ('Reading for the order of B7 and B8: A2 changed the totals, so B7 comes first. ' if rd['changed'] else 'Reading for the order of B7 and B8: the totals stayed, so by item 2 of the plan B7 and B8 are run together. ')` | Adds the reading for the order of B7 and B8: A2 changed the totals and B7 comes first, or the totals stayed and B7 and B8 are run together. |
| 1126 | `                  + 'A conflict with the handoff is open. See the section "Consequence for the order of B7 and B8".')` | Adds a fixed sentence: a conflict with the handoff note is open, with a pointer to the section on the order of B7 and B8. |
| 1127 | `        else:` | The case without a reading. |
| 1128 | `            t += f'{ID} for the order of B7 and B8: old read or new read has no totals with both intervals.'` | Adds `Insufficient data` for the order of B7 and B8: the old or the new read kernel has no totals with both intervals. |
| 1129 | `        out['A2'] = t` | Stores the text for A2. |
| 1130 | `    else: out['A2'] = miss('A1 or A2')` | Without a comparison the text is the one for missing data of A1 or A2. |
| 1131 | `    if s['A3']['compare']:` | The case that step A3 has a comparison. |
| 1132 | `        out['A3'] = a3_answer(s) + ' ' + ' '.join(f"Interval {int(ms)/1000:g} s: q was {rtxt(v['q_one'])} with one buffer. It was {rtxt(v['q_two'])} with two buffers." for ms, v in s['A3']['compare'].items())` | The text for A3: the answer of line 701, then for each interval length the range of q with one buffer and with two. |
| 1133 | `    else: out['A3'] = miss('A3')` | Without a comparison the text for A3 is the one for missing data. |
| 1134 | `    if s['A4']['kernels']:` | The case that step A4 has data. |
| 1135 | `        if not d['labels_usable']:` | The case that the pattern labels are not usable. |
| 1136 | `            t = [f'Observed in screening. {ID} for B8: the pattern labels are not used, so A4 gives no pair of counts. Median q without labels, series 64+b:']` | `t`: the text for A4. It starts with `Observed in screening.` and `Insufficient data` for B8: the labels are not used, so A4 gives no pair of counts. Then it introduces the median q of the series `64+b` without labels. |
| 1137 | `            for k, x in s['A4']['kernels'].items():` | Loop over the kernels of A4. |
| 1138 | `                f = a4_facts(x)` | `f`: the facts of line 718 for this kernel. |
| 1139 | `                if f:` | Only when the facts exist. |
| 1140 | `                    t.append(f"{KNAME.get(k, k)}: largest step from {fx(f['q_lower'])} at {f['lower']} to {fx(f['q_upper'])} at {f['upper']}, lowest {fx(f['q_lowest'])} at {f['lowest']}.")` | Adds for the kernel the largest step of the median q with its two counts, and the lowest median q with its count. |
| 1141 | `            out['A4'] = ' '.join(t) + ' See the section "Consequence for B8".'` | Stores the text for A4, with a pointer to the section on B8. |
| 1142 | `        else:` | The case that the labels are usable. |
| 1143 | `            t = []` | `t`: the pieces of the text, empty at first. |
| 1144 | `            for k, x in s['A4']['kernels'].items():` | Loop over the kernels of A4. |
| 1145 | `                for sname, ser in x['series'].items():` | Loop over the two series. |
| 1146 | `                    t.append(f"{KNAME.get(k, k)}, {sname}: " + (f"change between {ser['bracket'][0]} and {ser['bracket'][1]}" if ser['bracket'] else ser['note']))` | Adds for the kernel and series the two counts of the bracket, or the note of the analysis script when there is no bracket. |
| 1147 | `            out['A4'] = 'Observed in screening. ' + '. '.join(t) + '.'` | Stores the text for A4: `Observed in screening.` and the pieces. |
| 1148 | `    else: out['A4'] = miss('A4')` | Without data the text for A4 is the one for missing data. |
| 1149 | `    if s['A5']['processes']:` | The case that step A5 has processes. |
| 1150 | `        pp = s['A5']['processes']; ok = [p for p in pp if a5_usable(p)]; bad = [p for p in pp if not a5_usable(p)]` | `pp`: the processes of A5. `ok`: those with usable level labels. `bad`: those without. |
| 1151 | `        ch = [p for p in ok if p['changes']]` | `ch`: the processes with usable labels that have a change between low and high. |
| 1152 | `        t = 'Observed in screening. '` | `t`: the text for A5. It starts with `Observed in screening.`. |
| 1153 | `        if ok:` | Only when processes with usable labels exist. |
| 1154 | `            t += f"A change between low and high was observed in {len(ch)} of the {pl(len(ok), 'process', 'processes')} with usable labels. "` | Adds in how many of these processes a change between low and high was observed. |
| 1155 | `            t += ' '.join(f"CPU {p['cpu']}, process {p['proc']}: {x['from_level']} to {x['to_level']}, the first {x['to_level']} interval is number {x['at_interval']} (counted from 0)." for p in ch for x in p['changes'])` | Adds for each change the CPU, the process, the two labels, and the number of the first interval with the new label, counted from 0. |
| 1156 | `            t += ''.join(f" CPU {p['cpu']}, process {p['proc']}: no change between low and high. {a5_other_labels(p)}" for p in ok if not p['changes'])` | Adds for each process without a change that it had none, and the sentence of line 922 about its labels. |
| 1157 | `        cpus = (s.get('level_check') or {}).get('cpus') or {}` | `cpus`: the level check per CPU. |
| 1158 | `        for cpu in sorted(set(p['cpu'] for p in bad)):` | Loop over the CPUs whose labels are not usable. |
| 1159 | `            c = cpus[str(cpu)]` | `c`: the check of this CPU. |
| 1160 | `            lims = ' and '.join(f"{x['limit']:g} GB/s" for x in c['limits'] if not x['separates'])` | `lims`: the limits that do not separate the rates of this CPU, as text in GB/s. |
| 1161 | `            t += f" CPU {cpu} ({pl(sum(1 for p in bad if p['cpu'] == cpu), 'process', 'processes')}): the labels are not used, because the limit {lims} lies inside its rates ({fx(c['min'])} to {fx(c['max'])} GB/s)."` | Adds for the CPU the number of its processes and the sentence that the labels are not used, with the limit that lies inside its rates and the range of these rates. |
| 1162 | `        out['A5'] = t` | Stores the text for A5. |
| 1163 | `    else: out['A5'] = miss('A5')` | Without processes the text for A5 is the one for missing data. |
| 1164 | `    a = s['A6']` | `a`: the summary of step A6. |
| 1165 | `    if 'nothp_minus_thp_GBps' in a:` | The case that both kinds of A6 have processes. |
| 1166 | `        out['A6'] = f"Observed in screening. Median rate with --no-thp: {fx(a['nothp']['process_medians']['median'], 2)} GB/s ({rtxt(a['nothp']['process_medians'])}). With 2 MiB pages allowed: {fx(a['thp']['process_medians']['median'], 2)} GB/s ({rtxt(a['thp']['process_medians'])})."` | The text for A6: `Observed in screening.`, the median rate with `--no-thp` with its range, and the median rate with pages of 2 MiB allowed with its range, in GB/s. |
| 1167 | `    else: out['A6'] = miss('A6')` | In every other case the text for A6 is the one for missing data. |
| 1168 | `    files = a7_files(s)` | `files`: the files of step A7. |
| 1169 | `    if files:` | The case that files exist. |
| 1170 | `        ce = files.get('A7-core-events.txt'); pmus = (ce[1].get('pmu_list') or []) if ce else []` | `ce`: the entry of `A7-core-events.txt`. `pmus`: its PMU entries, or an empty list. |
| 1171 | `        t = ('Counter codes for Part C: ' + ' '.join(a7_codes_txt(p) for p in pmus)) if pmus else f'{ID}: no counter codes for Part C, the file A7-core-events.txt is missing or lists no core PMU.'` | `t`: the text for A7. With a PMU it gives the counter codes for Part C (line 1047). Without one it is `Insufficient data`, with the reason. |
| 1172 | `        sve = files.get('A7-sve.txt')` | `sve`: the entry of `A7-sve.txt`. |
| 1173 | `        if sve and sve[1].get('sve_vector_length_bytes'):` | Only when that file holds a number. |
| 1174 | `            t += f" SVE vector length: {sve[1]['sve_vector_length_bytes']} bytes."` | Adds the SVE vector length in bytes. |
| 1175 | `        out['A7'] = t + f" {pl(len(files), 'file was', 'files were')} written."` | Stores the text for A7, with the number of files that were written at its end. |
| 1176 | `    else: out['A7'] = miss('A7')` | Without files the text for A7 is the one for missing data. |
| 1177 | `    return out` | Returns the texts of the seven steps. |

### The style sheet of the page (lines 1180 to 1192)

| Line | Source | Explanation |
|---:|---|---|
| 1180 | `CSS = """` | `CSS`: the style sheet of the page, as one text. Line 1290 puts it into the head of the page. The text ends in line 1191. |
| 1181 | `:root{color-scheme:light}` | CSS: the page declares a light colour scheme only. A browser in dark mode keeps these colours. |
| 1182 | `body{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;background:#ffffff;color:#0b0b0b;max-width:920px;margin:0 auto;padding:24px 16px 60px;line-height:1.5;font-size:15px}` | CSS for the whole page: a system font without serifs, a white background and near black text. The content is at most 920 pixels wide and centred. The line height is 1.5, and the text size is 15 pixels. |
| 1183 | `h1{font-size:26px;margin:0 0 12px} h2{font-size:20px;margin-top:40px;border-top:1px solid #e6e5e0;padding-top:20px} h3{font-size:16px;margin-top:24px}` | CSS for the headings: the page title is 26 pixels high. A section heading is 20 pixels high, with a light grey line and space above it. A sub-heading is 16 pixels high. |
| 1184 | `.ax{font-size:11px;fill:#52514e} .lab{font-size:12px;fill:#0b0b0b} .val{font-size:11px;fill:#0b0b0b;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}` | CSS for the texts inside the charts. The class `ax` is for axis texts: 11 pixels, dark grey. The class `lab` is for names: 12 pixels, near black. The class `val` is for value labels: 11 pixels, near black, with a white outline 3 pixels wide behind the letters. A value then stays readable on top of a line. |
| 1185 | `svg text{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}` | CSS: every text inside a chart uses the same font as the page. |
| 1186 | `.lg{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e} .lg i{width:11px;height:11px;border-radius:50%;margin-right:8px;display:inline-block}` | CSS for the legend of a chart: an entry and its mark stand in one line, in dark grey text of 13 pixels. The mark is a round dot 11 pixels wide. |
| 1187 | `table{border-collapse:collapse;font-size:13px;margin:8px 0} td,th{border-bottom:1px solid #e6e5e0;padding:4px 8px;text-align:right;vertical-align:bottom;font-variant-numeric:tabular-nums} td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){text-align:left} td:first-child,td:nth-child(2){white-space:nowrap}` | CSS for tables: the borders of the cells are joined, and the text size is 13 pixels. Each cell has a light grey line below it. Numbers are aligned at the right with digits of equal width. The first two columns are aligned at the left, and their cells do not wrap. |
| 1188 | `.take{background:#f1f0ec;padding:10px 14px;border-radius:6px} .cap{font-size:13px;color:#52514e;margin-top:2px} .tw{overflow-x:auto}` | CSS for three classes. `take`, a highlighted statement: a very light grey background and round corners. `cap`, a caption: 13 pixels, dark grey. `tw`, the frame of a table: it scrolls sideways when the table is wider than the page. |
| 1189 | `.miss{background:#fdf3e7;border-left:4px solid #b85c00;padding:8px 12px} .banner{background:#fdf3e7;border:2px solid #b85c00;padding:10px 14px;font-weight:600}` | CSS for two classes. `miss`, a notice of missing data: a pale orange background and a dark orange bar at the left. `banner`, the notice at the top of the page: the same background, a dark orange frame and bold text. |
| 1190 | `code{font-size:13px} details{margin:10px 0} summary{cursor:pointer;color:#52514e} .pt td,.pt th{text-align:left;vertical-align:top} .pt td:nth-child(2){white-space:normal}` | CSS: code text is 13 pixels high. A part that can be unfolded has space above and below it, and its title is dark grey with a hand pointer. In a table of the class `pt` all cells are aligned at the left and at the top, and the second column may wrap. |
| 1191 | `"""` | Ends the style sheet. |

### The list `WORDS`: the terms that the page defines (lines 1193 to 1249)

| Line | Source | Explanation |
|---:|---|---|
| 1193 | `WORDS = [` | `WORDS`: the list of the terms for the section `Words used here` of the page. Each entry is a pair of a term and its definition. Line 1302 prints the entries as a list. |
| 1194 | `    ('CRB', 'the Arm Phoenix Reference Server (128 cores, AArch64). All measurements ran there.'),` | Entry for `CRB`: the server on which all measurements ran. |
| 1195 | `    ('Plan', 'the file <code>plan.md</code>, the reviewed test plan for the two questions [Ref1].'),` | Entry for `Plan`: the file `plan.md`, with its reference. |
| 1196 | `    ('Handoff', 'the file <code>handoff.md</code>, the instructions for the execution of the plan [Ref2].'),` | Entry for `Handoff`: the file `handoff.md`, with its reference. |
| 1197 | `    ('Part A, screening', 'the first part of the plan. It uses the existing benchmark programs. It can show where to look next. It decides no hypothesis.'),` | Entry for `Part A, screening`: the first part of the plan. It uses the existing benchmark programs and decides no hypothesis. |
| 1198 | `    ('Part B, Part C, Part D', 'the later parts of the plan. Part B uses a changed copy of the benchmark (<code>bwx</code>). Part C reads the counters of the cores. Part D needs root.'),` | Entry for the Parts B, C and D: the later parts of the plan, with what each one uses or needs. |
| 1199 | `    ('Observed in screening', 'the wording for every result of Part A. It means that the result was seen in this run. No control ran with it.'),` | Entry for the words `Observed in screening`: the wording for every result of Part A. No control ran with it. |
| 1200 | `    ('Kernel', 'one timed loop of the benchmark <code>bandwidth.c</code>. It is not the Linux kernel.'),` | Entry for `Kernel`: one timed loop of the benchmark, not the Linux kernel. |
| 1201 | `    ('Old read, old write', 'the C kernels before 2026-11-13, from the program <code>bw_old</code>.'),` | Entry for the old read and the old write kernel: the C kernels of the program `bw_old`. |
| 1202 | `    ('New read, new write', 'the C kernels since 2026-11-13, from the program <code>bw_new</code>.'),` | Entry for the new read and the new write kernel: the C kernels of the program `bw_new`. |
| 1203 | `    ('asm read, asm write', 'the kernels written in assembly, here always from <code>bw_new</code>.'),` | Entry for the two kernels written in assembly: on this page they always come from `bw_new`. |
| 1204 | `    ('Process, launch', 'one start of the benchmark program. The tag of a launch is its name in the run script.'),` | Entry for `Process, launch`: one start of the benchmark program, and the meaning of a tag. |
| 1205 | `    ('Process block', 'the lines of one process in a csv file of a result folder.'),` | Entry for `Process block`: the lines of one process in a csv file. |
| 1206 | `    ('Repetition, interval', 'one timed period inside a process. Its shortest length is set by the option <code>--min-ms</code>.'),` | Entry for `Repetition, interval`: one timed period inside a process, and the option that sets its shortest length. |
| 1207 | `    ('Pass', 'one sweep of a thread over its whole buffer. A thread runs whole passes until the interval is over.'),` | Entry for `Pass`: one sweep of a thread over its whole buffer. |
| 1208 | `    ('2 % check', 'rule 7 of the plan: one pass must take at most 2 % of the interval. That means at least 50 passes per thread.'),` | Entry for the 2 % check: rule 7 of the plan. It asks for at least 50 passes per thread. |
| 1209 | `    ('Rate', 'bytes moved per second, in GB/s (1 GB = 10<sup>9</sup> bytes).'),` | Entry for `Rate`: bytes per second in GB/s, with 1 GB as 10 to the power of 9 bytes. |
| 1210 | `    ('Total', 'the rate of a repetition as the benchmark prints it: the bytes of all threads divided by the longest time of a thread.'),` | Entry for `Total`: the rate of a repetition as the benchmark prints it, the bytes of all threads divided by the longest time of a thread. |
| 1211 | `    ('Thread rate', 'the bytes of one thread divided by its own time. The benchmark prints it with 2 decimals.'),` | Entry for `Thread rate`: the bytes of one thread divided by its own time, printed with 2 decimals. |
| 1212 | `    ('Sum of thread rates', 'the thread rates of one mesh added. It is not the same number as the total.'),` | Entry for `Sum of thread rates`: the thread rates of one mesh added. The entry says that this is not the total. |
| 1213 | `    ('Median', 'the middle value of a sorted list. With an even count it is the mean of the two middle values. Such a median can lie in the middle of two printed values. It is then printed with 3 decimals.'),` | Entry for `Median`: the middle value of a sorted list, and why some medians are printed with 3 decimals. |
| 1214 | `    ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0 to 63 are on mesh 0. CPUs 64 to 127 are on mesh 1, and we use 64 to 119.'),` | Entry for the two meshes: the CPUs of each half of the chip, and the CPUs that the tests use. |
| 1215 | `    ('a+b threads', 'a threads on mesh 0 (CPUs 0 to a-1) and b threads on mesh 1 (CPUs 64 to 64+b-1).'),` | Entry for a thread count of the form `a+b`: which CPUs the threads of each mesh use. |
| 1216 | `    ('q', 'the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one repetition. The percentile rule is "nearest rank": the P-th percentile is value number ceil(P/100 x n) of the n rates sorted upward. With 120 threads these are the 12th and the 108th value [Ref5].'),` | Entry for `q`: its definition and the nearest-rank rule of the percentile, with the 12th and the 108th value of 120 threads. |
| 1217 | `    ('Fastest half', 'the n/2 threads with the highest rates of one repetition with n threads.'),` | Entry for `Fastest half`: half of the threads of one repetition, those with the highest rates. |
| 1218 | `    ('Split, uniform, between', 'the provisional pattern labels of a repetition: q below 0.65, q above 0.85, or neither.'),` | Entry for the pattern labels split, uniform and between, with the limits 0.65 and 0.85. |
| 1219 | `    ('Low, high, changing', 'the provisional level labels of an interval with one thread at 8 MiB: below 69 GB/s, above 70.5 GB/s, or neither.'),` | Entry for the level labels low, high and changing, with the limits 69 and 70.5 GB/s. |
| 1220 | `    ('2 MiB pages, <code>--no-thp</code>', 'Linux can back memory with pages of 2 MiB instead of 4 KiB (transparent huge pages, THP). With <code>--no-thp</code> the benchmark asks for 4 KiB pages.'),` | Entry for pages of 2 MiB and the option `--no-thp`. |
| 1221 | `    ('<code>madvise</code>, <code>nohugepage</code>', 'the page setting that the benchmark prints. <code>madvise</code>: it asked for 2 MiB pages. <code>nohugepage</code>: it asked for 4 KiB pages.'),` | Entry for the two page settings that the benchmark prints, `madvise` and `nohugepage`. |
| 1222 | `    ('Load', 'the Linux 1-minute load average: the average count of tasks that run or wait to run.'),` | Entry for `Load`: the load average of Linux over 1 minute. |
| 1223 | `    ('Runnable tasks', 'the count of tasks that can run at one moment (4th field of <code>/proc/loadavg</code>).'),` | Entry for `Runnable tasks`: the fourth field of `/proc/loadavg`. |
| 1224 | `    ('Waited', 'the time the script waited for at most 2 runnable tasks before a launch, 20 s at most.'),` | Entry for `Waited`: the time that the script waited before a launch, 20 s at most. |
| 1225 | `    ('Q1', 'the first question of the plan: why one thread with an 8 MiB buffer behaves differently from the other sizes.'),` | Entry for `Q1`: the first question of the plan, about one thread with a buffer of 8 MiB. |
| 1226 | `    ('Q2a', 'a part of the second question: why old read has a higher total than new read with 120 threads.'),` | Entry for `Q2a`: the higher total of the old read kernel with 120 threads. |
| 1227 | `    ('Q2b', 'the other part: why the write kernels give several separate totals between repetitions.'),` | Entry for `Q2b`: the several separate totals of the write kernels. |
| 1228 | `    ('Item 13', 'item 13 of the list "What the existing files already show" of the plan: which threads are the fast ones was not recorded before Part A.'),` | Entry for `Item 13`: an item of the plan. Which threads are the fast ones was not recorded before Part A. |
| 1229 | `    ('H2', 'hypothesis: the low level can change to the high level while the stream runs.'),` | Entry for hypothesis `H2`. |
| 1230 | `    ('H3a', 'hypothesis: the coverage of the buffer with 2 MiB pages decides the level.'),` | Entry for hypothesis `H3a`. |
| 1231 | `    ('H7a', 'hypothesis: a part of the difference at 120 threads is made by the stop method and the short interval.'),` | Entry for hypothesis `H7a`. |
| 1232 | `    ('H7b', 'hypothesis: a part of the difference is made by the common start of all threads.'),` | Entry for hypothesis `H7b`. |
| 1233 | `    ('H8', 'hypothesis: with threads on both meshes the chip has two states, split and uniform. A loop that only loads reaches the uniform state at a lower thread count than old read.'),` | Entry for hypothesis `H8`. |
| 1234 | `    ('H9a', 'hypothesis: the second buffer per thread moved old read to the uniform pattern on 2026-10-30.'),` | Entry for hypothesis `H9a`. |
| 1235 | `    ('H9b', 'hypothesis: the pattern of old read differs between sessions for a reason other than the kernel.'),` | Entry for hypothesis `H9b`. |
| 1236 | `    ('H11', 'hypothesis: the write totals differ because the threads of one mesh run faster in some intervals.'),` | Entry for hypothesis `H11`. |
| 1237 | `    ('B4', 'step of Part B: asm read at 8 MiB for 200 intervals, with the page state before every interval.'),` | Entry for step `B4` of Part B. |
| 1238 | `    ('B7', 'step of Part B: the read kernels at 64+56 threads with two stop methods, two intervals and two start methods, and with a control of two copies of one loop.'),` | Entry for step `B7` of Part B. |
| 1239 | `    ('B8', 'step of Part B: the thread counts of A4 in steps of 4 threads around the counts where the pattern changes.'),` | Entry for step `B8` of Part B. |
| 1240 | `    ('B5, B9, B10', 'more steps of Part B. B5: read loops with added <code>nop</code> instructions. B9: old read with one and with two buffers. B10: the write kernels with the settings of B7.'),` | Entry for the steps `B5`, `B9` and `B10` of Part B. |
| 1241 | `    ('D2', 'step of Part D: the physical addresses of the buffer pages.'),` | Entry for step `D2` of Part D. |
| 1242 | `    ('PMU', 'performance monitoring unit: the counter hardware of a core.'),` | Entry for `PMU`: the counter hardware of a core. |
| 1243 | `    ('<code>perf_event_open</code>', 'the Linux system call that opens a counter.'),` | Entry for `perf_event_open`: the Linux system call that opens a counter. |
| 1244 | `    ('SVE', 'the scalable vector instruction set of AArch64.'),` | Entry for `SVE`: the scalable vector instruction set of AArch64. |
| 1245 | `    ('Choice C1 to C11', 'a definition that the analysis script had to fix where the plan and the handoff give none. All are listed at the top of <code>analyze_partA.py</code> [Ref5].'),` | Entry for the choices C1 to C11 of the analysis script, with their reference. |
| 1246 | `    ('est.', 'an estimate, not a measurement.'),` | Entry for `est.`: an estimate, not a measurement. |
| 1247 | `]` | Ends the list `WORDS`. |

### Function `short_version`: the three sentences at the top of the page (lines 1250 to 1283)

| Line | Source | Explanation |
|---:|---|---|
| 1250 | `def short_version(s):` | Starts the function `short_version`. It builds the short version of the page. |
| 1251 | `    """At most three sentences. Built from computed values."""` | Text of the function: at most three sentences, built from computed values. |
| 1252 | `    d = s['q']['decision']; g = s['q'].get('groups') or {}` | `d`: the decision of the test of the two groups. `g`: the description of where the q values lie. |
| 1253 | `    sv = 'Part A ran the existing benchmark programs on CRB (the Arm test server) as a first look, and it decides no hypothesis. '` | `sv`: the first sentence, a fixed text. It says what Part A is: a first look with the existing benchmark programs on CRB that decides no hypothesis. |
| 1254 | `    a, b = g.get('read_old') or {}, g.get('load_only_read') or {}` | `a`: the summary for the old read kernel at 64+56 threads. `b`: the summary for the new read kernel and `asmread`. |
| 1255 | `    if d['n'] == 0:` | The case that no q value exists. |
| 1256 | `        sv += f"{ID}: no repetition with per-thread lines exists, so the pattern of the threads cannot be described. "` | The second sentence is then `Insufficient data`: no repetition with per-thread lines exists, so the pattern of the threads cannot be described. |
| 1257 | `    elif a.get('n') and b.get('n'):` | The case that both summaries have repetitions. |
| 1258 | `        lo = min(b['mesh0_median']['min'], b['mesh1_median']['min']); hi = max(b['mesh0_median']['max'], b['mesh1_median']['max'])` | `lo` and `hi`: the lowest and the highest median thread rate of the new read kernel and `asmread`, over both meshes and all their repetitions. |
| 1259 | `        sv += (f"Observed in screening: with {g['count']} threads on the two halves of the chip (mesh 0 and mesh 1), the median thread of old read ran at {rtxt(a['mesh0_median'])} GB/s on mesh 0 "` | The second sentence, `Observed in screening`: with 64+56 threads the median thread of the old read kernel ran at one range of rates on mesh 0. |
| 1260 | `               f"and at {rtxt(a['mesh1_median'])} GB/s on mesh 1 in all {a['n']} repetitions, and the median thread of new read and asm read ran at {fx(lo)} to {fx(hi)} GB/s on both meshes ({b['n']} repetitions). ")` | Continues the sentence: and at another range on mesh 1, in all its repetitions. The median thread of the new read kernel and `asmread` ran from `lo` to `hi` GB/s on both meshes. |
| 1261 | `    elif d['labels_usable']:` | The case without these summaries and with usable labels. |
| 1262 | `        sv += f"Observed in screening: the ratio q of slow to fast threads falls into two groups over {d['n']} repetitions ({fx(d['lower_min'], 2)} to {fx(d['lower_max'], 2)}, and {fx(d['upper_min'], 2)} to {fx(d['upper_max'], 2)}). "` | The second sentence then says that q falls into two groups, with the number of repetitions and the two ranges. |
| 1263 | `    else:` | Every other case. |
| 1264 | `        sv += (f"Observed in screening: the ratio q of slow to fast threads does not fall into two groups over {d['n']} repetitions"` | The second sentence then says that q does not fall into two groups, with the number of repetitions. |
| 1265 | `               + (f" ({fx(d['q_min'], 2)} to {fx(d['q_max'], 2)})" if 'q_min' in d else '') + '. ')` | Continues the sentence: the lowest and the highest q in brackets, when they are known. |
| 1266 | `    parts = []` | `parts`: the pieces of the third sentence, empty at first. |
| 1267 | `    rd = s['A1_A2'].get('order_reading')` | `rd`: the reading of choice C11. |
| 1268 | `    if rd:` | The case with a reading. |
| 1269 | `        parts.append(('the long interval made' if rd['difference_smaller_with_long'] else 'the long interval did not make') + ' the difference between old read and new read smaller (A2)')` | Adds a piece about A2: the long interval made, or did not make, the difference between the old and the new read kernel smaller. |
| 1270 | `    else:` | The case without a reading. |
| 1271 | `        parts.append(f'{ID.lower()} for the order of B7 and B8 (A2)')` | Adds `insufficient data` for the order of B7 and B8. |
| 1272 | `    if not s['A4']['kernels']:` | The case that step A4 has no data. |
| 1273 | `        parts.append(f'{ID.lower()} for the thread counts of B8 (A4)')` | Adds `insufficient data` for the thread counts of B8. |
| 1274 | `    elif not d['labels_usable']:` | The case that the labels are not usable. |
| 1275 | `        parts.append('Part A gives no thread counts for B8 because the pattern rule of the handoff does not fit the data (A4)')` | Adds a fixed piece: Part A gives no thread counts for B8, and the reason is that the pattern rule of the handoff note does not fit the data. |
| 1276 | `    else:` | The case with usable labels. |
| 1277 | `        nb = sum(1 for x in s['A4']['kernels'].values() if x['series']['64+b']['bracket'])` | `nb`: the number of kernels of A4 that have a bracket in the series `64+b`. |
| 1278 | `        parts.append(f"A4 gives the thread counts for B8 for {nb} of {pl(len(s['A4']['kernels']), 'kernel', 'kernels')}")` | Adds a piece: for how many of the kernels A4 gives the thread counts for B8. |
| 1279 | `    ce = a7_files(s).get('A7-core-events.txt')` | `ce`: the entry of the file `A7-core-events.txt`. |
| 1280 | `    parts.append('the counter codes for Part C are listed under A7' if ce and ce[1].get('pmu_list') else f'{ID.lower()} for the counter codes of Part C (A7)')` | Adds a piece about A7: the counter codes for Part C are listed, or `insufficient data` for them. |
| 1281 | `    return sv + 'For the next steps: ' + ', '.join(parts[:-1]) + ', and ' + parts[-1] + '.'` | Returns the three sentences. The third starts with `For the next steps:` and joins the pieces with commas and the word `and`. |

### Function `build`: the whole page (lines 1284 to 1339)

| Line | Source | Explanation |
|---:|---|---|
| 1284 | `def build(s, banner=None):` | Starts the function `build`. It puts the whole page together. `s` is the content of the json file, and `banner` is an optional notice. |
| 1285 | `    c = s['counts']` | `c`: the counts of the blocks. |
| 1286 | `    present = [x for x in s['steps_present'] if x != 'A7']` | `present`: the steps with data, without A7. |
| 1287 | `    n7 = len(a7_files(s))` | `n7`: the number of files of step A7. |
| 1288 | `    pt = points_to(s)` | `pt`: the texts per step of line 1093. |
| 1289 | `    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',` | `o`: the pieces of the page. The first piece opens the HTML document: the document type, the language English, the character set UTF-8, and a setting that fits the page to the width of a small screen. |
| 1290 | `         '<title>Part A screening result</title>', f'<style>{CSS}</style></head><body>']` | Adds the title of the browser tab, the style sheet of line 1180 and the start of the visible page. |
| 1291 | `    if banner:` | Only when a banner text was given. |
| 1292 | `        o.append(f'<p class="banner">{e(banner)}</p>')` | Adds the banner as the first paragraph of the page. The tests use it to mark a page that is built from invented data. |
| 1293 | `    o.append('<h1>Part A: screening of the two open questions of the new C kernels</h1>')` | Adds the main heading of the page. |
| 1294 | `    o.append(f'<p class="take"><b>Short version.</b> {short_version(s)}</p>')` | Adds the short version (line 1250) as a highlighted paragraph, after the bold words `Short version.`. |
| 1295 | `    o.append('<p>The two questions come from the benchmark run of 2026-11-13 [Ref1]. Q1: why one thread with an 8 MiB buffer behaves differently from the other buffer sizes. '` | Adds a fixed paragraph with the two questions. They come from the benchmark run of 2026-11-13. This line holds Q1, about one thread with a buffer of 8 MiB. |
| 1296 | `             'Q2: why the old read kernel has a higher total than the new one when 120 threads run, and why the write kernels give several separate totals.</p>')` | Continues the paragraph with Q2, about the totals of the read and write kernels with 120 threads. |
| 1297 | `    t = f"<p>Result folders: {', '.join(f'<code>{e(f)}</code>' for f in s['folders'])} [Ref4]. "` | `t`: a paragraph that starts with the names of the result folders and their reference. |
| 1298 | `    t += f"The page is built from {pl(c['blocks_used'], 'process', 'processes')} of the steps {', '.join(present) if present else 'none'}" + (f", and from the {pl(n7, 'file', 'files')} of step A7. " if n7 else '. ')` | Continues `t`: from how many processes of which steps the page is built, and from how many files of step A7. |
| 1299 | `    t += ('Every process block of the folders is used. ' if not c['blocks_not_used'] else f"{pl(c['blocks_not_used'], 'process block is', 'process blocks are')} not used. ")` | Continues `t`: that every process block is used, or how many are not used. |
| 1300 | `    t += (f"No data: {', '.join(s['steps_missing'])}." if s['steps_missing'] else 'No step is missing.')` | Continues `t`: the steps without data, or the sentence that no step is missing. |
| 1301 | `    o.append(t + '</p>')` | Adds the paragraph. |
| 1302 | `    o.append('<h2 id="words">Words used here</h2><ul>' + ''.join(f'<li><b>{k}</b>: {v}</li>' for k, v in WORDS) + '</ul>')` | Adds the section `Words used here`: a heading and the entries of `WORDS` as a list, each term in bold. |
| 1303 | `    o.append('<h2 id="points">What each step points to</h2>')` | Adds the heading of the section `What each step points to`. |
| 1304 | `    o.append('<p>The two middle columns are quoted from the plan [Ref1]. The last column is built from the data of this run. '` | Adds a paragraph: the two middle columns of the table are quoted from the plan, and the last column is built from the data of this run. |
| 1305 | `             'Three results set later work: the order of B7 and B8 (row A2), the thread counts of B8 (row A4), and the counter codes of Part C (row A7).</p>')` | Continues the paragraph: three results set later work: the order of B7 and B8, the thread counts of B8, and the counter codes of Part C. |
| 1306 | `    o.append('<div class="tw"><table class="pt"><tr><th>Step</th><th>Looks at (quoted from the plan)</th><th>What the result points to (quoted from the plan)</th><th>This run</th></tr>')` | Opens the table with four column headings: the step, what it looks at, what the result points to, and this run. |
| 1307 | `    for st_ in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'):` | Loop over the seven steps. |
| 1308 | `        o.append(f"<tr><td>{st_}</td><td>{e(LOOKS[st_])}</td><td>{e(PLAN[st_])}</td><td>{e(pt[st_])}</td></tr>")` | Adds the row of the step: the texts of `LOOKS` and `PLAN` (lines 25 to 33) and the text of line 1093. |
| 1309 | `    o.append('</table></div>')` | Closes the table. |
| 1310 | `    o += [sec_load(s), sec_blocks(s), sec_q(s), sec_passes(s), sec_a12(s), sec_a3(s), sec_a4(s), sec_a5(s), sec_a6(s), sec_a7(s)]` | Adds the ten sections in this order: system load, blocks that are not used, the distribution of q, passes per thread, the steps A1 and A2, and then one section for each of the steps A3 to A7. |
| 1311 | `    o.append('<h2 id="limits">Limits of this page</h2><ul>'` | Adds the heading of the section `Limits of this page` and opens a list. |
| 1312 | `             f'<li>{ID}: the difference between two copies of one loop. Part A has no such control. So no difference on this page is compared with it. Steps B7 and B10 measure it [Ref1].</li>'` | Limit 1 of the page: Part A has no control with two copies of one loop. So no difference of the page is compared with the difference between two equal loops. The text names the later steps that measure it. |
| 1313 | `             '<li>An old kernel and an asm kernel come from two programs (<code>bw_old</code> and <code>bw_new</code>) [Ref2].</li>'` | Limit 2: an old kernel and a hand-written kernel never come from the same program. One runs in `bw_old`, the other in `bw_new`. |
| 1314 | `             '<li>The limits for the pattern (0.65 and 0.85) and for the level (69 and 70.5 GB/s) are provisional [Ref2].</li>'` | Limit 3: the four limits of the two label rules are provisional. |
| 1315 | `             '<li>Thread rates are printed with 2 decimals. So the sum of 64 thread rates can differ from the exact sum by up to 0.32 GB/s (64 x 0.005 GB/s).</li>'` | Limit 4: the rounding of the printed thread rates. With 2 decimals the sum of 64 thread rates can be off by up to 0.32 GB/s (64 times 0.005 GB/s). |
| 1316 | `             f'<li>{ID}: the passes of each thread. The pass count on this page is an average over the threads. The existing programs do not print the passes of each thread [Ref2]. The changed benchmark of Part B prints the passes of each thread [Ref2].</li>'` | Limit 5: the passes of a single thread are not known. The pass count of the page is an average over the threads. The text adds that the changed benchmark of Part B prints the passes of each thread. |
| 1317 | `             '<li>All threads start an interval together, and each thread stops after a whole pass. Part A does not change this timing method.</li>'` | Limit 6: the timing method of the benchmark is not changed in Part A: a common start of all threads, and a stop of each thread after a whole pass. |
| 1318 | `             f'<li>{ID}: the page state of the buffers and their physical pages. Part A did not record them. Step B4 gives the page state, and step D2 gives the physical pages [Ref1].</li>'` | Limit 7: the page state of the buffers and their physical pages were not recorded in Part A. The text names the later steps that give them. |
| 1319 | `             f'<li>{ID}: load readings during a benchmark. The script reads the load only directly before each launch [Ref3].</li>'` | Limit 8: the load was read only directly before each launch, never while a benchmark ran. |
| 1320 | `             '<li>The chart colours were not checked with the palette checker of the chart rules. The checker needs Node.js. Node.js is not installed on the machine where this page was built. Every chart also uses position, shape or a text label.</li>'` | Limit 9: the chart colours were not checked with the palette checker of the chart rules, and the text gives the reason. It adds that every chart also uses position, shape or a text label. |
| 1321 | `             '</ul>')` | Closes the list of limits. |
| 1322 | `    f7 = a7_files(s)` | `f7`: the files of step A7. |
| 1323 | `    def a7ref(n):` | Starts the inner function `a7ref`. It gives the text of a reference to one file of step A7. |
| 1324 | `        return f"<code>{e(f7[n][0])}/{n}</code>" if n in f7 else f"<code>{n}</code> (not present in these result folders)"` | Returns the folder and the file name as code text. For a file that no folder holds, it returns the file name with the note that it is not present. |
| 1325 | `    o.append('<h2 id="refs">References</h2><ul>'` | Adds the heading of the section `References` and opens a list. |
| 1326 | `             '<li>[Ref1] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md</code>: sections "The two questions", "What the existing files already show" (item 13), "Hypotheses", "Rules for the deciding measurements" (rules 5 and 7), "Part A" (the table with the column "What the result points to"), "Part B", and "Order and decision points" (items 2 to 4).</li>'` | Reference 1 of the page: the plan `plan.md`, with the sections that the page uses. |
| 1327 | `             '<li>[Ref2] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md</code>: sections "What each step runs", "Output format", "How to analyse Part A", B.3 (output rows of <code>bwx</code>), B.8 (counters), B.9 (row B8 and "Settings after B7") and B.10 (items B8 and B5).</li>'` | Reference 2: the handoff note `handoff.md`, with the sections that the page uses. |
| 1328 | `             '<li>[Ref3] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh</code>: the launches, the wait before each launch, the header line of each process, <code>launches.txt</code> and <code>env.txt</code>.</li>'` | Reference 3: the run script `run_partA.sh`: the launches, the wait before each launch, the header lines and the two text files. |
| 1329 | `             f"<li>[Ref4] The result folders {', '.join(f'<code>{e(f)}</code>' for f in s['folders'])} and the file <code>partA-summary.json</code> that <code>analyze_partA.py</code> wrote from them. Every measured rate, q, count and load on this page comes from that file.</li>"` | Reference 4: the result folders and the json file. Its text says that every measured rate, q, count and load of the page comes from that file. |
| 1330 | `             '<li>[Ref5] <code>/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partA-analysis/analyze_partA.py</code>: the choices C1 to C11 at the top of the file (percentile, test for two groups, fastest half, repeated launches, label of a count, change of level, change of pattern in A4, rows of A3 used for q, check of the level limits, event names, reading of A2 for the order of the steps).</li>'` | Reference 5: the analysis script `analyze_partA.py`, with the list of its choices C1 to C11. |
| 1331 | `             '<li>[Ref6] <code>/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c</code>, function <code>main()</code>: the output lines of a process.</li>'` | Reference 6: the benchmark source `bandwidth.c`, function `main`: the output lines of a process. |
| 1332 | `             f"<li>[Ref7] {a7ref('A7-core-events.txt')}: the type and the event codes of the core PMU.</li>"` | Reference 7: the file `A7-core-events.txt` (line 1323). |
| 1333 | `             f"<li>[Ref8] {a7ref('A7-sve.txt')}: the default SVE vector length.</li>"` | Reference 8: the file `A7-sve.txt`. |
| 1334 | `             f"<li>[Ref9] {a7ref('A7-perf-list.txt')}: the output of <code>perf list</code>.</li>"` | Reference 9: the file `A7-perf-list.txt`. |
| 1335 | `             f"<li>[Ref10] {a7ref('A7-pmu-devices.txt')}: the names of the counter devices.</li>"` | Reference 10: the file `A7-pmu-devices.txt`. |
| 1336 | `             '</ul></body></html>')` | Closes the list, the page body and the HTML document. |
| 1337 | `    return '\n'.join(o)` | Returns the page as one text, one piece per line. |

### Function `main`: arguments, input and output file (lines 1340 to 1355)

| Line | Source | Explanation |
|---:|---|---|
| 1340 | `def main(argv):` | Starts the function `main`. `argv` is the list of the arguments of the call. |
| 1341 | `    out = 'partA-result.html'; banner = None` | `out`: the path of the page, `partA-result.html` unless `-o` gives another. `banner`: no banner unless `--banner` gives a text. |
| 1342 | `    for opt in ('-o', '--banner'):` | Loop over the two options. |
| 1343 | `        if opt in argv:` | Tests whether the arguments hold the option. |
| 1344 | `            i = argv.index(opt); v = argv[i + 1]; argv = argv[:i] + argv[i + 2:]` | Takes the word after the option as its value and removes the two words from the list. |
| 1345 | `            if opt == '-o': out = v` | The value of `-o` is the output path. |
| 1346 | `            else: banner = v` | The value of `--banner` is the banner text. |
| 1347 | `    src = argv[0] if argv else 'partA-summary.json'` | `src`: the json file: the first argument that is left, or `partA-summary.json` in the working folder. |
| 1348 | `    s = json.load(open(src))` | `s`: the content of the json file. |
| 1349 | `    open(out, 'w').write(build(s, banner))` | Builds the page (line 1284) and writes it to the output file. An older file of that name is replaced. |
| 1350 | `    print(f'wrote {out}')` | Prints `wrote` and the path of the page. |
| 1351 | `    return 0` | Returns 0, the exit status of a run that worked. |
| 1354 | `if __name__ == '__main__':` | This test is true when the file is started as a program. It is false when another file imports it. The tests in `test_partA.py` import it. |
| 1355 | `    sys.exit(main(sys.argv[1:]))` | Calls `main` with the arguments of the command line, without the program name. The return value becomes the exit status. |

## References

- [Ref1] the result folder `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the files `make_partA_html.py` (sha256 `1b9dc00f8e3aeaf1551f3c59eeb2e0cd713c6a2a8852a85235401c785a3d8b12`, as the file in the code folder) and `partA-result.html`.
