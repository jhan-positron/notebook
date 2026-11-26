
## Part 2: `viz.py` and `shell.py`

### Short version

- `viz.py` (imported as `V`) builds charts. Every builder takes plain Python lists and returns one SVG string.
- `shell.py` gives the page object `S`. It numbers sections, figures, tables and references, and `S.render()` checks the page text (the lint) before it returns the HTML.
- A section module exposes `KEY`, `TITLE` and `build(D, V, S)`, and only concatenates the strings that `S.*` and `V.*` return. The fixed ids are in `IDS.md`.

### Words used here

- Builder: a function of `viz.py` that returns an SVG string.
- Series: one line or one set of points of a chart.
- Series colour key: the name of a fixed colour (table below). A hex string is also accepted.
- Tip: the text of the hover tooltip. Every data mark carries it in `data-tip`. A `\n` in a tip starts a new line.
- Lint: the check that `S.render()` runs over the visible text of the page.
- Partial build: a build with `--only`, or a build in which a section module does not exist yet.
- SCR: the scratch folder of this work, `/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/44910dbc-316f-4921-a7fe-7178628c5666/scratchpad/core`.

### How the page is built

```
python3 gen_c1nano_perf.py --out SCR/build/<name>.html                 # all sections that exist
python3 gen_c1nano_perf.py --out SCR/build/<name>.html --only latency  # one section (or KEY,KEY)
```

- Always pass `--out` while the page is under review. The default output is `asimov-c1nano-perf.html` in the project folder.
- Order of the calls: `data.load()`, `refs.install(S, D)`, `words.install(S, D)`, `sec_setup.short_version(D, V, S)`, then `build(D, V, S)` of `sec_setup`, `sec_glance`, `sec_latency`, `sec_bandwidth`, `sec_multicore`, `sec_ocm`, `sec_mesh`, `sec_open`.
- `build` returns the section body without the `h2`. The generator writes the `h2` from `KEY` and `TITLE`.
- A section module that does not exist is skipped with a printed note. Without `data.py` the sections get `D = None`.
- The generator prints the size, the visible word count of the page and of each section (for the word budgets), the counts of figures, tables, references and terms, and a note for each subsection id that differs from `IDS.md`.
- The page has no time stamp. Two builds give the same bytes.

### Series colour keys

| Key | Colour | Use |
|---|---|---|
| `'f1'` | orange `#eb6834` | boot F1 and boot E (L3 on, prefetchers on). "read" in a chart of kernels inside boot F1. The default colour. |
| `'off'` | blue `#2a78d6` | boot B and boot D (prefetchers off). Where both appear, boot B is a filled dot and boot D a hollow one. |
| `'c'` | aqua `#1baf7a` | boot C and boot R3 (the L3 holds no data, prefetchers on). "write" in a chart of kernels. |
| `'alt'` | violet `#6250d6` | a fourth series, only if unavoidable. "copy" in a chart of kernels. Drawn as diamonds. |
| `'ref'` | grey `#7d838c` | reference lines, capacity markers, a part that belongs to no boot. |
| `'crit'` | red `#e34948` | the critical slice of the wall-clock lanes figure only. |
| `'f2'`, `'core'` | as `'off'`, as `'c'` | aliases, kept so that code written for `cme_page/viz.py` runs. |

The legend names the boot. One colour never means two boots in one chart.

### Rules that hold for every builder

- All text must be ASCII. A non-ASCII label raises `ValueError`. Write "us", "x", "-".
- Default width is 1040 px (the content column). Pass `width=` for a narrower chart.
- Every builder returns `<div class="figwrap"><svg class="viz" ...></svg></div>`. The chart shrinks with the page down to `MIN_SCALE` (0.92) of its drawn width. Print removes the minimum width.
- Text is drawn in ink colours. Only marks carry a series colour.
- An axis that does not start at 0 prints "axis starts at N" on the chart. A log axis prints "log axis".
- A chart with two or more series draws its own legend. A chart with one series draws none: name the series in the caption.
- A label that finds no free place is left out. The value stays in the tip, so give the exact numbers in the table beside the figure.

### Format helpers

```python
V.ns(21.0051)            # '21.005 ns'      V.ns(v, digits=1)
V.gbps(52.34)            # '52.3 GB/s'
V.ratio(2.142)           # '2.14 x'
V.pct(12.34)             # '12.3 %'  (the value is already in percent)
V.signed(12.3, 1, 'ns')  # '+12.3 ns'
V.size_label(1536*1024)  # '1.5 MiB'   also '64 B', '4 KiB', '2 GiB'
V.num(1234567.891, 1)    # '1,234,567.9'
V.color('f1')            # '#eb6834'
V.tw('some text', 12)    # estimated width in px, for your own layout
V.wrap('a long text', 120, 11)   # list of lines no wider than 120 px
```

`None` gives `'n/a'` in every number helper.

### Which builder for which figure of the outline

| Figure | Builder |
|---|---|
| H1 | `hbar` (one colour, value labels, cycles in `note`) |
| S1 | `boxes` |
| S2 | `mesh_map` |
| S3, N1, P2 | `grid` |
| S4 | `boxes`, or `lanes` for the strip that marks the timed interval |
| G1, L4, B3, M1, O1, O5, N2 | `dot_rows` |
| L1, B1 | `line_chart` |
| L2 | `small_multiples` |
| L3 | `stacked_hbar` |
| L5, B2, O4, P1 | `dot_rows` with `connect=True` (L5 and N2 with `x='log'`), or `dumbbell` for two series on a linear axis |
| L6 | `lanes` |
| M2 | `stacked_hbar` with one series and `chips` |
| O2 | `dot_rows` with a list of values per row (strip plot), `median` and `tick` |
| O3 | `scatter_fit` |

### dot_rows (dot plot, strip plot, dumbbell with any number of dots, log axis)

```python
svg = V.dot_rows(
    [dict(header='Plain and prefetch variants, 32 MiB'),
     dict(label='boot E', sub='L3 on, prefetchers on', values=[2.492, 52.66], note='21.1 x'),
     dict(label='boot B', sub='the L3 holds no data, prefetchers off', values=[52.762, 52.739], note='1.00 x')],
    [dict(name='address order', color='f1'),
     dict(name='random order, every line flushed first', color='off', hollow=True)],
    x='log',                     # or 'linear' (default)
    unit='ns', fmt=lambda v: V.num(v, 3), xlabel='chain load, ns',
    connect=True,                # joins the lowest and the highest dot of a row
    xrange=None,                 # (lo, hi), either may be None
    refs=[(52.66, 'DRAM-model row')],          # grey vertical lines with a label
    band=(0.98, 1.02, 'within 2 %'),           # grey band, named in the legend
    labels='auto')               # 'auto', 'all', 'ends', 'none'
```

- `series`: dicts with `name`, `color`, and optionally `hollow=True` (a ring) and `marker`. A tuple `(name, color)` is also accepted.
- Row fields: `label`, `values` (one entry per series: a number, `None`, or a list of numbers), and optionally `sub`, `note` (bold text at the end of the row: the gap or the ratio), `tick` (a grey tick: a predicted or reference value of that row), `median` (an ink tick), `labels` (for this row), `tip`. `{'header': text}` is a group heading.
- A list of numbers in `values` gives a strip: one dot per number. Use hollow dots for a strip, so that dots that overlap still show.
- `tick_name` is the legend text of the grey tick. `median_name` is the legend text of the ink tick (default "median").
- Value labels: `'auto'` labels every dot of a row with at most 4 dots, and the two ends of a longer row. The lowest value is printed left of its dot, the highest right of it, a middle value above its dot.
- Two dots of different series closer than 9 px are set apart vertically so that both show.
- The builder never computes a gap. Compute the ratio or the difference from the data layer and pass it as `note`.

### stacked_hbar (parts of a whole, and bars with a strip of boxes)

```python
svg = V.stacked_hbar(
    [dict(label='256 KiB', values=[0.23, 0.76, 0.012], note='9.5 ns'),
     dict(label='384 KiB', sub='the row to quote', values=[0.05, 0.92, 0.03], note='10.9 ns')],
    [('L2 hits', 'f1'), ('L3 hits', 'c'), ('from outside the cluster', 'ref')],
    fmt=lambda v: V.num(v, 2), xlabel='per load', total=False, xmax=1.0)

svg = V.stacked_hbar(            # one series: plain bars with chips
    [dict(label='CPUs 2, 3', values=[40.9], note='one cluster: 0.64 x',
          chips=[('2,3', True), ('4,5', False), ('6,7', False), ('8,9', False)])],
    [('16 MiB write', 'f1')], unit='GB/s', fmt=lambda v: V.num(v, 1), xlabel='aggregate rate, GB/s',
    chip_name='cluster with a writing core')
```

- Bars start at 0 always. A negative value raises. `None` counts as 0.
- Segments have a 2 px gap. A value is printed inside its segment when it fits.
- `total=True` prints the sum after the bar. `note` is printed in bold after it.
- `chips`: `[(text, on)]`, a strip of small boxes between the label and the bar. A filled box is "on". `chip_name` is its legend text.
- Use it only for parts that add up (shares of loads, per load counts of one whole). Durations that are not nested intervals must not be stacked.

### grid (matrix of conditions, counts per node, which boot measures what)

```python
on, no = dict(text='on', kind='f1'), dict(text='no data', kind='soft')
svg = V.grid(
    ['L3', 'prefetchers', 'OCM mapping'],          # '\n' starts a second heading line
    [dict(label='boot F1', sub='the main boot', cells=[on, on, '4 KiB entries'], hl=True),
     dict(label='boot B', cells=[no, dict(text='off', kind='off'), '4 KiB entries']),
     dict(label='a family with no boot', cells=[dict(text='not measured', kind='mute')] * 3)],
    legend_items=[('as boot F1', 'f1'), ('prefetchers off', 'off'), ('not measured', 'mute')],
    width=760, corner='boot')
```

- A cell is a text, `None`, or a dict: `text`, `kind`, and optionally `sub`, `shade`, `tip`.
- Kinds: `'plain'` (white), `'soft'` (grey), `'mute'` (grey text in a dashed outline), `'f1'`, `'off'`, `'c'`, `'alt'` (a light tint of the series colour with a bar of the full colour at the left edge).
- `shade` (0 to 1) makes the tint follow a magnitude, for counts: `dict(text=V.num(n, 0), kind='f1', shade=n / n_max)`. One hue from light to dark. The number stays in the cell.
- `hl=True` draws an ink outline around the row. `{'header': text}` is a group heading.
- `col_w` fixes the column width in px. The default shares the width, at most 190 px per column.

### line_chart

```python
K = 1024
svg = V.line_chart(
    [dict(name='read', color='f1', points=[(16*K, 56.1), (48*K, 27.3), (32768*K, 24.6)], label='last'),
     dict(name='write', color='c', points=[(16*K, 30.6), (48*K, 31.4), (32768*K, 32.0)])],
    x='log2',                       # or 'linear'
    xticks=None,                    # None, [x, ...] or [(x, 'label'), ...]
    xlabel='footprint', ylabel='rate, GB/s', yunit='GB/s', xfmt=V.size_label,
    hlines=[(64.0, 'documented 64 GB/s (read loop)')],   # (y, label)
    vlines=[(32*K, 'L1 32 KiB')],                         # (x, label): capacity markers
    labels=[(0, 16*K), (1, 32768*K, 'custom text')],      # (series index, x[, text])
    gaps=[dict(x=48*K, y0=27.3, y1=31.4, text='+4.1 GB/s')],
    annotations=[dict(x=48*K, y=27.3, text='line one\nline two')],
    yrange=None,                    # None = from 0, (lo, hi), (lo, None), or 'fit'
    height=380)
```

- Series fields: `name`, `color`, `points` `[(x, y)]`. A `y` of `None` breaks the line. Optional: `size` (marker radius in px), `label` (`'last'`, `'first'`, `'max'`, `'min'`, `'all'` or a list of x values), `tips` (one extra tip line per point), `marker` (`'circle'`, `'square'`, `'triangle'`, `'diamond'`), `markers=False`, `dash=True`, `line=False` (points only: use it for the separate marker of the row with every line flushed first).
- `gaps` draws a bracket between two y values at one x and writes the text beside it. `dx` moves the bracket sideways in px.
- `annotations` finds a free place for the text and draws a leader line. `dx` and `dy` fix the place by hand.
- `xtick_mode`: `'auto'` (thin out, then rotate), `'thin'`, `'rotate'`.
- `yfmt`, `xfmt`: functions that format a value in tips and labels. `ytickfmt` formats the y ticks.
- One y axis only. For a second scale (bytes per cycle beside GB/s) write the second unit in the labels or in the table. Do not draw a second axis.

### small_multiples

```python
svg = V.small_multiples(
    [dict(ylabel='L1 refills per load',
          series=[dict(name='boot F1', color='f1', points=[(4*K, 0.0), (256*K, 1.0)])]),
     dict(ylabel='L3 read refills per load', yrange=(0, 1.2), hlines=[(1.0, 'one per load')],
          series=[dict(name='boot F1', color='f1', points=[(4*K, 0.0), (256*K, 0.003)])])],
    x='log2', xlabel='footprint', vlines=[(32*K, 'L1 32 KiB')], panel_height=150)
```

- The panels share the x axis and are stacked vertically. Each panel has its own y axis and y label.
- Panel fields: `ylabel`, `series`, and optionally `yunit`, `yrange`, `hlines`, `labels`, `annotations`, `gaps`, `yfmt`, `height`.

### scatter_fit

```python
svg = V.scatter_fit(
    [dict(name='0 Y steps', color='off', points=[(1, 22.7, 'region 0'), (3, 26.7)],
          fit=(1.994, 20.752), fit_label='fit: 20.752 ns + 1.994 ns per X step')],
    x='linear', xticks=[0, 1, 2, 3, 4], xlabel='X steps', ylabel='chain load, ns', yunit='ns')
```

- A point is `(x, y)` or `(x, y, label)`. `fit=(slope, intercept)` draws the straight line over the x range of the points. `fit_range=(x0, x1)` gives another range.
- It takes the other arguments of `line_chart` (`hlines`, `vlines`, `annotations`, `yrange`, `xrange`). With `yrange='fit'` the chart prints "axis starts at N".

### dumbbell (two series, linear axis)

```python
svg = V.dumbbell(
    [dict(header='Every line, one region'),
     dict(label='CPU 2, region 0', a=22.7, b=22.6, gap='0.996 x')],
    a_name='boot B', b_name='boot D', a_color='off', b_color='c', unit='ns', xlabel='chain load, ns',
    fmt=lambda v: V.num(v, 3), refs=[(20.752, 'fit at zero steps')], xrange=None)
```

- Without `gap` the builder writes `b - a` with a sign and the unit. `gap_fmt=lambda a, b: ...` gives another default.
- For hollow dots, three or more dots, or a log axis use `dot_rows` with `connect=True`.

### hbar

```python
svg = V.hbar(
    [dict(label='L1 (4 KiB)', value=2.002, note='(4.01 cycles)'),
     dict(label='DRAM model (8 MiB, every line flushed first)', value=52.658, color='ref')],
    unit='ns', fmt=lambda v: V.num(v, 3), xlabel='chain load, ns', refs=[(10.0, 'a reference')])

svg = V.hbar(                                   # grouped
    [dict(header='Read'), dict(label='region 0', values=[19.9, 16.5])],
    series=[('boot F1', 'f1'), ('boot R3', 'c')], unit='GB/s', xlabel='rate, GB/s', width=760)
```

- Bars start at 0 always. A negative value raises.
- Row fields: `label`, `value` or `values`, and optionally `sub`, `color`, `note` or `notes` (text after the value), `tips`.

### lanes (wall-clock lanes)

```python
svg = V.lanes(
    [dict(name='boot B: the loads of the core',
          blocks=[(0, 52.76, 'one load = one fetch, 52.76 ns', 'critical'), (52.76, 105.52, '', 'work')]),
     dict(name='boot E: line fetches, est.',
          blocks=[(i * 2.49, i * 2.49 + 52.66, '', 'wait') for i in range(21)])],
    unit='ns', t_range=(0, 110),
    spans=[(0, 52.76, '52.76 ns', 'critical')])
```

- One lane per actor. The x axis is time, to scale.
- Block kinds: `'work'` (solid), `'wait'` (dashed outline), `'critical'` (red, the serial slice). Write the cost of the critical slice in its label.
- A tiny block stays tiny (at least 0.75 px wide). `spans` draws dimension lines under the lanes.
- State every simplification in the caption. The caption of figure L6 is given word for word in the critic sheet.

### boxes (box-and-arrow diagram)

```python
svg = V.boxes(
    [dict(id='core', x=0, y=30, w=150, h=80, title='core', lines=['C1-Nano'], kind='accent'),
     dict(id='l1', x=210, y=30, w=130, h=80, title='L1', lines=['32 KiB'])],
    [dict(src='core', dst='l1', label='load')],
    groups=[dict(x=200, y=4, w=300, h=130, label='cluster')])
```

- Coordinates are px. Lay the boxes out left to right. The height of the SVG follows the lowest box.
- Node fields: `id`, `x`, `y`, `w`, `h`, `title`, and optionally `lines`, `tag`, `tag_style` (`'solid'`, `'outline'`), `kind` (`'plain'`, `'accent'`, `'soft'`, `'dashed'`), `tip`. No box uses a boot colour.
- Arrow fields: `src`, `dst`, and optionally `label`, `dashed`, `both`, `shift`, `route='hv'`, `via=[(x, y), ...]`, `label_dy`.

### mesh_map

```python
svg = V.mesh_map(
    6, 6,
    [(1, 3, 'region 0\nid 88', 'hn'), (2, 3, 'CPUs 2, 3', 'port'), (1, 2, 'fifth port', 'plain')],
    highlights=[(2, 3)],
    steps=[dict(src=(2, 3), dst=(1, 3), label='1 step')])
```

- `cells`: `(x, y, label, kind)`. Kinds: `'hn'` (home node), `'port'` (cluster port), `'mem'` (bridge to memory), `'hyp'` (dashed outline), `'plain'`. The ports of the four clusters are documented (operator's README), so they are `'port'`, not `'hyp'`.
- `steps`: a route drawn along the mesh links, X first. `order='yx'` goes Y first. The count of X steps and of Y steps does not depend on the order.
- `y_up=True` puts y = 0 at the bottom. `kinds={'hn': 'home node'}` renames a legend entry.

### legend

```python
svg = V.legend([('boot F1', 'f1'), ('boot B', 'off', 'hollow'), ('fit', 'ref', 'tick')], width=480)
```

- An item is `(name, color)`, `(name, color, shape)` or `(name, color, shape, line)`. Shapes: the marker names, `'swatch'`, `'dashed'`, `'hollow'`, `'tick'`, `'band'`.

### shell.py: the page object

```python
body  = S.h3('lat-footprint', 'By footprint, CPU 2')        # ids from IDS.md
body += S.p('A claim %s.' % S.ref('file:F1:latency-dram-small.csv:60-62', 'the three reps of the 384 KiB chain'))
body += S.fig(svg, 'Caption.', 'One-line takeaway.', id_='fig-L1', note='Files and simplifications.')
body += S.table(['Footprint', 'Best, ns', 'Spread, %'],
                ['Walked many times',                        # a plain text row is a group heading
                 ['4 KiB', V.num(2.002), V.num(0.0, 2)]],
                caption='Exact numbers.', note='Best rows.', highlight=[0], id_='tab-TL1')
body += S.p('%s gives the rows. See %s and %s.' % (S.tabref('tab-TL1'), S.figref('fig-O1'), S.xref('ocm-quote')))
body += S.bullets(['one', 'two', ['nested under two']])
body += S.hyp('The cause is X.', 'A boot with Y would confirm or reject it.')
body += S.insufficient('Two readers on CPUs 2 and 3 against CPUs 2 and 4 at 16 MiB.')
body += S.callout('The DRAM level is an emulator memory model.', title='Note')
S.term('hit set')
```

| Method | Returns | Notes |
|---|---|---|
| `S.h3(id, title)` | html | `render` fills in the number. A duplicate id raises. Use the ids of `IDS.md`. `S.h2` is called by the generator. |
| `S.p(text)` | html | One paragraph. |
| `S.bullets(items, ordered=False)` | html | An item is a text, `(text, [sub items])`, or a list right after a text. |
| `S.takeaways(items, title='Key points')` | html | The list at the top of a section. |
| `S.fig(svg, caption, takeaway=None, id_=None, note=None)` | html | "Figure N." above, the takeaway line below, then the optional `note` in small type. Keep the caption to what the figure shows and how to read it. Files, references and simplifications go in `note`. Pass `id_='fig-<code>'`. |
| `S.table(headers, rows, caption, note, highlight, align, id_)` | html | Numeric columns are right-aligned. A column whose header starts with "Footprint" stays left-aligned. `align='lrrc'` forces it. `highlight` is a list of row indexes (group rows not counted) or a function `(index, row) -> bool`. Pass `id_='tab-<code>'`. |
| `S.next_fig()`, `S.next_table()` | int | The number the next figure or table gets. Prefer `S.figref` and `S.tabref`. |
| `S.xref(id, text=None, cap=False)` | link | "section 7.3" ("Section" with `cap=True`). With `text` it reads "section 7.3 (text)". |
| `S.figref(id, cap=True)`, `S.tabref(id, cap=True)` | link | "Figure 7", "Table 7". They work across sections and before the figure is built. |
| `S.ref(key, text=None)` | `[RefN]` link | See Part 3. `render` renumbers all links by first use in reading order. Never type a reference number. |
| `S.term(name, definition='')` | the name | See Part 3. |
| `S.hyp(text, test)` | html | Block labelled "Hypothesis". `test` is required: the measurement that would confirm or reject it. |
| `S.insufficient(text)` | html | Block labelled "Insufficient data". |
| `S.callout(text, title='Note')` | html | A plain note block. |
| `S.cols(*parts)` | html | Parts side by side. |
| `S.render(short_version_html, sections, lint_page=True)` | page html | Called by the generator. |
| `shell.esc(text)` | text | Escapes `<`, `>`, `&`. |

Order of the page: title, Short version, Contents, sections 1 to 8, "Words used here" (9), "References" (10).

Figure and table numbers are given at the call, so the generator builds the sections in page order.

#### The lint in S.render

`render` raises `shell.LintError` on these:

- A forbidden word in the visible text: hop, chase (all forms), "register control", "run N" (N from 1 to 9, unless a count follows, as in "run 4 threads"), "round three", "round four", "boot A", sparse, dense, "asm form", previously, "no longer", "L3 off" (also "L3 is off"), baseline, "dual 128-bit", validated, codex. Whole words, any letter case.
- The boot names "boot B", "boot C", "boot D", "boot E", "boot F1" and "boot R3" pass.
- A non-ASCII character inside an `<svg>` element.
- A `[RefN]` in the text with no entry, or a key passed to `S.ref` that never got a text.
- A link `href="#x"` to an id that is not on the page, or an id that is used twice.
- In a full build: an `S.xref`, `S.figref` or `S.tabref` to an id that is not on the page. In a partial build the link is written as plain text (`section "ocm-quote"`) and the generator prints a note.

`render` only warns (on stderr, and in `S.warnings`) on these:

- A semicolon in prose outside `code`, `pre`, table cells and SVG.
- "fresh", "the flushed", "flushed row", and the history words earlier, now, changed, settled, "was thought", "new in", "turned out", "used to", "was fixed", "old firmware".
- "2 MiB pages" (right for the DRAM buffers, wrong for the OCM mapping), "lines in flight" without "est.", "takes N cycles", "served by the L3", "DRAM latency", "3.75 MiB" without "est.".

Text inside `<code>` and `<pre>` is not checked for words. So put every file name in `<code>`: several file names contain "dense" or "sparse".

`shell.lint(page_html, n_refs)` returns `(errors, warnings)` without raising.

### Palette check

Validator of the dataviz skill (`validate_palette.js`), light mode.

- Four colours in the fixed order (orange, blue, aqua, violet), neighbours only: all checks pass. Worst neighbour pair aqua and blue: colour-blind distance 23.1, normal-vision distance 24.0.
- Three colours (orange, blue, aqua), every pair: all checks pass. Worst pair aqua and orange, colour-blind distance 9.2 (target 8 or more).
- Three colours (orange, aqua, violet: read, write, copy), every pair: all checks pass. Worst pair aqua and orange, 9.2.
- Aqua has contrast 2.74 to 1 against the surface (under 3 to 1). So an aqua mark needs a visible label or a table. Every chart here has a legend and every figure has a table.
- Violet against blue in one chart was not passed by the every-pair check of the sibling page (colour-blind distance 4.5). Do not put violet and blue in one chart unless the marks are labelled directly.

### Test

- `SCR/scripts/foundation/demo.py` builds `SCR/build/foundation_demo.html` from made-up data: one of each new builder, the colour keys, the references with cited lines, the cross-references of a partial build. It also checks that the lint raises on each forbidden word and passes the six boot names.
- Screenshots of it: `SCR/shots/foundation_0.png` to `foundation_2.png`.

## Part 3: one reference list and one glossary (`refs.py`, `words.py`)

### Short version

- A section cites a file with `S.ref('file:<boot>:<name>:<lines>', 'what the lines hold')`. The References then hold each file once, with every cited line listed.
- `words.install(S, D)` gives every term one definition. A section calls `S.term(name)` for a term it uses.
- Neither module reads the data layer. `refs.install` uses `D.log_lines(boot, file)` only when the data layer has it.

### refs.py

Canonical keys (`<boot>` is `F1`, `E`, `B`, `C`, `D` or `R3`):

| Key | Entry |
|---|---|
| `file:<boot>:<name>` | One file of the boot's results folder: any CSV file, `log.txt`, `sysinfo.txt`, `cmn-counts.csv`. Built on demand: boot, path, line count. The entry of `log.txt` lists the lines of the L3 status register and its value. |
| `group:<boot>:<pattern>` | A group of result files, pattern with `*`, for example `group:B:latency-ocm-region*-route-cpu*.csv`. The entry gives the count, the first and the last file. |
| `run:<boot>:dmesg.txt` | The Linux boot log. The entry counts the OCM mapping lines and gives their `cont=` value. Boot R3 has no such file. |
| `run:<boot>:SHA256SUMS` | The checksum list. |
| `readme:<boot>` | The operator's README, with the lines of the typed facts (L3 status register, prefetchers, OCM mapping, platform facts, the DRAM model for boot F1, the mesh coordinates for boot R3). |
| `src:latency.c`, `src:bandwidth.c`, `src:common.h`, `src:cmncount.c`, `src:lib_run.sh`, `src:run_asimov.sh`, `src:run_followup.sh`, `src:run_all.sh` | The benchmark sources and scripts, with typed line numbers. |
| `doc:sog` | Arm C1-Nano Core Software Optimization Guide (Tables 2-13, 2-14, 3-2, sections 3.1, 3.12). |
| `doc:plan` | `follow-up-run-plan.md` (the fit rule, how time per pass is computed). Cite it as "a prepared command set" where a script name would be needed. |
| `doc:seqread` | `sequential-reads-L3-on-better-bandwidth.md`. |
| `doc:project-readme` | `README.md` of the project folder. |

- Cited lines: end any canonical key with `:<lines>`, for example `:5`, `:5-6`, `:5,45,60-62`. The entry then ends with "Cited: lines 5 and 6 (the text you gave)". The text passed with such a key says what the lines hold. Without lines the text is ignored.
- Cite the timed row that carries the best value (it has the counters), not the `best` row. Take the line number from the data layer (`row['line']`).
- All line numbers of the page live in the References. Prose and notes carry only the `[RefN]` link and the file name in `<code>`.
- Short forms: `<boot>/<name>`, `csv:<name>` (boot F1), `readme-f1`, `log:<boot>`, `sysinfo:<boot>`, `cmn:<boot>`, `dmesg:<boot>`, `sha:<boot>`, `sog`, `plan`.
- A key that names a file that does not exist raises `ValueError` at the `S.ref` call.
- A key that `refs.resolve` does not know stays as the section wrote it (the text is then required). The generator prints a note for each such key. Prefer a canonical key.
- In a run of `[RefN]` links, `render` keeps each number once and puts the run in rising order.
- A typed fact from a README or a document says so in the sentence: "(operator's README)" or the name of the document, then the `[RefN]`.

### words.py

- `words.WORDS` is the list of `(name, definition)`, with the wording of section 8 of the critic sheet. A definition is one or more full sentences. No definition holds a measured number.
- `words.ALIAS` maps a section name to one or more terms of `WORDS` (for example "prefetchers" to "prefetcher", "one line per page" to "one line per 4 KiB page").
- `words.ALWAYS` lists the terms that every section uses (the six boot names, cluster, prefetcher, the two L3 states, DRAM model, footprint, pass, rep, best row, spread, est., operator's README, chain load, GB/s). They are listed without a section call.
- Only terms that a section registers with `S.term(name)` (or that `ALWAYS` names) are listed on the page. So call `S.term` for each term of `WORDS` that the section uses.
- A term that is not in `WORDS` is kept with the wording of the section. The generator prints a note for each such term. Report it, so that it is added to `WORDS`.

### Terms and labels that the sections share

- Boots at first use in a section: "boot E (the firmware state of boot F1, another command set)", "boot B (prefetchers off, the L3 holds no data)", "boot C (prefetchers on, the L3 holds no data)", "boot D (as boot B, OCM mapped with 64 KiB translations)", "boot R3 (boot F1's commands, the L3 holds no data, an older build)". After that the bare name.
- Legend names of the boots: "boot E (L3 on, prefetchers on)", "boot C (the L3 holds no data, prefetchers on)", "boot B (the L3 holds no data, prefetchers off)".
- Table cells for the L3 state: "on", "no data".
- Counters: "L1 refills", "L2 refills", "L3 read refills", "L1 prefetch refills", "L2 prefetch refills", "L2 refills by the L1 prefetcher", "L2 hits", "L3 hits". Event numbers appear in table TS4 and in References only.
- Levels: L1, L2, L3, "home nodes over the mesh (SLC)", OCM, "DRAM model".
- "spread" has one definition: (largest minus smallest) / best row, in percent.
