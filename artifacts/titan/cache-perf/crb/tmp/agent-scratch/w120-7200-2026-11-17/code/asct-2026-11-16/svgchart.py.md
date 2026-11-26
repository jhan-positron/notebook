# `svgchart.py` explained, line by line

- Source file: `asct-2026-11-16/svgchart.py` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Python script, 210 lines, 11255 bytes).
- sha256 of the source when this page was built: `d278b6740f6c647a19c86699b15d385b63efb962669bc7d1a72758c2e8432bf9`.

## Short version: purpose

`svgchart.py` is a small library of drawing helpers for the report page of the ASCT cross-check. It holds a scale from data values to pixels and helpers that each return a piece of SVG text: a text, a marker, a legend, a plot panel with lines, and two complete chart kinds, the dumbbell chart and the horizontal bar chart. The file reads no data file and computes no result, and `figs.py` passes all values in.

## Words used here

- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **SVG**: Scalable Vector Graphics, a text format for drawings. A web page can hold SVG text directly.
- **px**: the unit of the drawing coordinates. x grows to the right and y grows downward.
- **Scale**: the rule that turns a data value into a pixel position.
- **Logarithmic scale**: a scale on which equal ratios of values have equal distances.
- **Tick**: a marked value on an axis.
- **Grid line**: a thin line across the plot at the position of a tick.
- **Mark**: a drawn shape that stands for a value: a dot, a line or a bar.
- **Marker**: the round dot of one data point.
- **Series**: a set of points that belong together and share a color.
- **Legend**: the key that says which color or line style stands for which series.
- **Tooltip**: a small text box that the page shows when the pointer rests on a mark or when the mark has the keyboard focus.
- **Hit area**: an invisible shape over a mark. It carries the tooltip text.
- **Dumbbell chart**: a chart with one row per pair of values. Two dots on a common value axis show the pair, and a line joins them.
- **Range**: the smallest and the largest value that belong to a point or a bar.
- **Dataviz skill**: a set of chart rules that the description text of the file names.
- **Old read loop, new read loop, ASCT read loop**: the three read loops that the report compares. Each has a fixed color in this file.

## Main flow

1. The file defines the colors: five ink and line colors, the background, one color for each of the three read loops and one for context (lines 8 to 17).
2. Two small helpers make text safe (`esc`) and format numbers (`fmt`). The class `Scale` turns a data value into a pixel position, on a linear or a logarithmic scale (lines 20 to 37).
3. Four functions return single shapes: a text, an invisible hit area as a circle or a rectangle, and a marker (lines 40 to 58).
4. `legend` draws the key of the series. `frame` opens a picture. `y_axis` draws the grid lines and tick labels of a value axis (lines 61 to 97).
5. `line_panel` draws one plot panel: axes, an optional vertical reference line, and for each series a line, range lines, markers and hit areas (lines 100 to 140).
6. `dumbbell` returns a complete chart with one row per pair of values (lines 143 to 177).
7. `hbars` returns a complete chart with one horizontal bar per row, an optional range line on each bar and optional shaded bands (lines 180 to 210).

## Behavior a reader must know

- Scales: `Scale` is linear unless `log` is set. `line_panel` takes the first and the last tick as the ends of each axis. A value outside the ticks is drawn outside the plot area, not cut off (line 37, lines 104 to 105).
- The y axis of `line_panel` and the value axis of `dumbbell` and `hbars` start at the first tick. A bar of `hbars` starts at that position too. So a bar length is in proportion to its value only when the first tick is 0 (line 202).
- `line_panel` leaves out a point without a y value and joins its neighbours with a line. A caller that wants a gap must pass two series (line 123).
- A range line of `line_panel` appears only when the range is larger than 3 px (line 130). In `hbars` it appears when the high end is above the low end (line 203).
- A point gets a tooltip only when the caller passes a tooltip text (line 136).
- In `dumbbell` the hollow dot is always value `a` and the filled dot value `b`. The number beside a dot is the value itself with `nd` decimals (lines 163 to 170).
- `frame` leaves the `svg` element open. `dumbbell` and `hbars` close it. A caller that builds a picture from `frame` and `line_panel` must close it.
- The function `line_panel` has a parameter `xfmt` that it does not use (line 101).

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/svgchart.py` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (210 lines, 11255 bytes, sha256 `d278b6740f6c647a19c86699b15d385b63efb962669bc7d1a72758c2e8432bf9`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Description text, modules and colors (lines 1 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `"""svgchart.py - small inline-SVG chart helpers for the ASCT cross-check report.` | Starts the description text of the file: small helpers that draw charts as SVG text for the report of the ASCT cross-check. The SVG text is placed directly in the page. |
| 2 | `Light theme only. Marks follow the dataviz skill: 2 px lines, markers r >= 4 with a 2 px surface ring,` | Description, continued: the charts have a light theme only. The marks follow the chart rules of the dataviz skill: lines of 2 px, and markers with a radius of at least 4 px and a ring of 2 px in the background color. |
| 3 | `bars at most 24 px thick with a rounded data end, hairline solid grid, text in ink colors (never series color),` | Description, continued: bars are at most 24 px thick and have a rounded end at the value. Grid lines are thin and solid. Text has an ink color and never the color of a series. |
| 4 | `a legend for two or more series, and a hover or focus tooltip on every mark (class "hit", attribute data-tip)."""` | Description, last line: a chart with two or more series has a legend. Every mark has a tooltip that appears when the pointer or the keyboard focus is on it. The tooltip text sits in the attribute `data-tip` of an element with the class `hit`. In the code a mark gets a tooltip only where the caller passes a tooltip text (line 136). |
| 5 | `import html` | Loads the module `html`. The file uses its function `escape`. |
| 6 | `import math` | Loads the module `math`. The file uses its function `log`. |
| 8 | `INK = '#0b0b0b'` | `INK`: the color of the main text, almost black. |
| 9 | `INK2 = '#52514e'` | `INK2`: the color of the second level of text, a dark grey. |
| 10 | `MUTED = '#898781'` | `MUTED`: the color of axis labels and notes, a middle grey. |
| 11 | `GRID = '#e1e0d9'` | `GRID`: the color of the grid lines, a light grey. |
| 12 | `AXIS = '#c3c2b7'` | `AXIS`: the color of the axis lines, a grey between `GRID` and `MUTED`. |
| 13 | `SURFACE = '#fcfcfb'` | `SURFACE`: the background color of a chart, almost white. |
| 14 | `OLD = '#2a78d6'      # categorical slot 1: old read loop` | `OLD`: a blue. Comment: it is the first series color and stands for the old read loop. |
| 15 | `NEW = '#eb6834'      # categorical slot 2: new read loop` | `NEW`: an orange. Comment: it is the second series color and stands for the new read loop. |
| 16 | `ASCT = '#1baf7a'     # categorical slot 3: ASCT read loop` | `ASCT`: a green. Comment: it is the third series color and stands for the ASCT read loop. |
| 17 | `CONTEXT = '#898781'  # other machines, context only` | `CONTEXT`: a grey with the same value as `MUTED`. Comment: it stands for other machines, which are shown as context only. |

### Helpers `esc` and `fmt`, and the class `Scale` (lines 20 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `def esc(s):` | Starts the function `esc`. It makes a value safe for use inside SVG and HTML text. |
| 21 | `    return html.escape(str(s), quote=True)` | Turns the value into text and replaces the characters `&`, `<`, `>` and both quote characters by their HTML names. |
| 24 | `def fmt(v, nd=1):` | Starts the function `fmt`. It formats a number with `nd` decimals. The default is 1 decimal. |
| 25 | `    return f'{v:.{nd}f}'` | Returns the number as text with a fixed count of decimals. |
| 28 | `class Scale:` | Starts the class `Scale`. An object of it turns a data value into a pixel position. |
| 29 | `    def __init__(self, d0, d1, r0, r1, log=False):` | Starts the set-up function. `d0` and `d1` are the two ends of the data range. `r0` and `r1` are the pixel positions of these two ends. `log` selects a logarithmic scale. |
| 30 | `        self.d0, self.d1, self.r0, self.r1, self.log = d0, d1, r0, r1, log` | Stores the five values in the object. |
| 32 | `    def __call__(self, v):` | Starts the function that runs when the object is called with a value `v`. |
| 33 | `        if self.log:` | For a logarithmic scale: |
| 34 | `            t = (math.log(v) - math.log(self.d0)) / (math.log(self.d1) - math.log(self.d0))` | `t`: the place of `v` between the two ends, measured in logarithms. It is 0 at `d0` and 1 at `d1`. Equal ratios of values get equal distances. |
| 35 | `        else:` | For a linear scale: |
| 36 | `            t = (v - self.d0) / (self.d1 - self.d0)` | `t`: the place of `v` between the two ends as a plain share. It is 0 at `d0` and 1 at `d1`. |
| 37 | `        return self.r0 + t * (self.r1 - self.r0)` | Returns the pixel position: `r0` plus the share `t` of the distance to `r1`. A value outside the data range gives a position outside the pixel range. The scale does not cut it off. |

### Single shapes: `text`, `hit_circle`, `hit_rect` and `marker` (lines 40 to 60)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `def text(x, y, s, size=12, fill=INK2, anchor='start', weight=None, extra=''):` | Starts the function `text`. It returns one SVG text element at the position `x`, `y`. `size` is the font size in px and `fill` the color. `anchor` says which point of the text sits at `x`: `start` for its left end, `middle` or `end`. |
| 41 | `    w = f' font-weight="{weight}"' if weight else ''` | `w`: the attribute for the font weight, or nothing when `weight` is not given. |
| 42 | `    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}{extra}>{esc(s)}</text>'` | Returns the element. The coordinates are written with 1 decimal. The text `s` goes through `esc`. |
| 45 | `def hit_circle(x, y, tip, r=12):` | Starts the function `hit_circle`. It returns an invisible circle that carries a tooltip text. `r` is its radius, 12 px by default. |
| 46 | `    return (f'<circle class="hit" tabindex="0" cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="transparent" '` | The circle has the class `hit`, which the script of the page looks for. `tabindex="0"` lets the keyboard focus reach it. Its fill is transparent. The element goes on in line 47. |
| 47 | `            f'data-tip="{esc(tip)}"><title>{esc(tip)}</title></circle>')` | Continues line 46: the tooltip text in the attribute `data-tip`, and the same text as a `title` child. A browser can show the `title` text as its own tooltip, without the script of the page. |
| 50 | `def hit_rect(x, y, w, h, tip):` | Starts the function `hit_rect`. It returns an invisible rectangle with a tooltip text. `x`, `y` is its top left corner, `w` its width and `h` its height. |
| 51 | `    return (f'<rect class="hit" tabindex="0" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="transparent" '` | The rectangle has the class `hit`, can take the keyboard focus and has a transparent fill. The element goes on in line 52. |
| 52 | `            f'data-tip="{esc(tip)}"><title>{esc(tip)}</title></rect>')` | Continues line 51: the tooltip text in `data-tip` and as a `title` child. |
| 55 | `def marker(x, y, color, hollow=False, r=4.5):` | Starts the function `marker`. It returns the round dot of one data point at `x`, `y` in the color of its series. |
| 56 | `    if hollow:` | For a hollow marker: |
| 57 | `        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{SURFACE}" stroke="{color}" stroke-width="2"/>'` | returns a circle with the radius `r`, a fill in the background color and an outline of 2 px in the series color. |
| 58 | `    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 1}" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>'` | Otherwise returns a filled circle in the series color with the radius `r + 1` and an outline of 2 px in the background color. The outline separates the dot from a line below it. |

### Function `legend`: the key of the series (lines 61 to 82)

| Line | Source | Explanation |
|---:|---|---|
| 61 | `def legend(items, x, y, gap=18):` | Starts the function `legend`. It draws one entry per series in a row that starts at `x`, `y`. `gap` is the space between two entries, 18 px by default. |
| 62 | `    """items: (label, color, kind) with kind 'line', 'thin', 'dot', 'hollow', 'bar'."""` | Description of the function: an item is a label, a color and a kind. The kinds are `line`, `thin`, `dot`, `hollow` and `bar`. |
| 63 | `    out, cx = [], x` | `out`: the pieces of SVG text. `cx`: the x position of the next entry. |
| 64 | `    for label, color, kind in items:` | Starts a loop over the items. |
| 65 | `        if kind == 'bar':` | For the kind `bar`: |
| 66 | `            out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="10" rx="2" fill="{color}"/>')` | draws a small rectangle of 12 by 10 px with rounded corners in the color of the item. |
| 67 | `            tx = cx + 17` | `tx`: the x position of the label, 17 px right of the start of the entry. |
| 68 | `        else:` | For all other kinds: |
| 69 | `            sw = 1.2 if kind == 'thin' else 2` | `sw`: the line width, 1.2 px for the kind `thin` and 2 px otherwise. |
| 70 | `            if kind in ('line', 'thin'):` | For the kinds `line` and `thin`: |
| 71 | `                out.append(f'<line x1="{cx}" y1="{y - 4}" x2="{cx + 22}" y2="{y - 4}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')` | draws a sample line of 22 px in the color of the item. |
| 72 | `            if kind in ('line', 'dot'):` | For the kinds `line` and `dot`: |
| 73 | `                out.append(marker(cx + 11, y - 4, color, r=3.5))` | draws a filled marker in the middle of the sample. |
| 74 | `            if kind == 'hollow':` | For the kind `hollow`: |
| 75 | `                out.append(f'<line x1="{cx}" y1="{y - 4}" x2="{cx + 22}" y2="{y - 4}" stroke="{color}" stroke-width="2"/>')` | draws a sample line of 22 px with a width of 2 px, |
| 76 | `                out.append(marker(cx + 11, y - 4, color, hollow=True, r=3.5))` | and a hollow marker in the middle of it. |
| 77 | `            tx = cx + 28` | `tx`: the x position of the label, 28 px right of the start of the entry. |
| 78 | `        out.append(text(tx, y, label, 12, INK2))` | Draws the label in the color `INK2`, not in the color of the series. |
| 79 | `        cx = tx + 7.0 * len(label) + gap` | Moves `cx` to the start of the next entry. The width of the label is an estimate of 7 px per character. |
| 80 | `    return ''.join(out)` | Returns all pieces as one text. |

### Functions `frame` and `y_axis`: the start of a picture, and the value axis (lines 83 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 83 | `def frame(w, h, title, desc):` | Starts the function `frame`. It returns the opening of one SVG picture of `w` by `h` units, with a title and a description for screen readers. |
| 84 | `    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(title)}" '` | Opens the `svg` element. `viewBox` sets the coordinate system to `w` by `h` units. `width="100%"` lets the picture fill the width of its container. `role="img"` and `aria-label` tell a screen reader that this is one image with the title as its name. The element goes on in lines 85 to 86. |
| 85 | `            f'font-family="system-ui, -apple-system, Segoe UI, sans-serif"><title>{esc(title)}</title><desc>{esc(desc)}</desc>'` | Continues line 84: the font of all text in the picture, and the child elements `title` and `desc` with the title and the description. |
| 86 | `            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{SURFACE}"/>')` | Continues line 84: a rectangle that fills the whole picture with the background color. The `svg` element stays open. The caller adds the closing tag. |
| 89 | `def y_axis(sy, ticks, x0, x1, unit=None, nd=0):` | Starts the function `y_axis`. It draws the horizontal grid lines and the tick labels of a vertical value axis. `sy` is the scale, `ticks` the values, and `x0` to `x1` the horizontal extent of the plot. |
| 90 | `    out = []` | `out`: the pieces of SVG text. |
| 91 | `    for t in ticks:` | Starts a loop over the tick values. |
| 92 | `        y = sy(t)` | `y`: the pixel position of the tick. |
| 93 | `        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')` | Draws a grid line of 1 px from `x0` to `x1` at that height. |
| 94 | `        out.append(text(x0 - 6, y + 4, fmt(t, nd), 11, MUTED, 'end', extra=' style="font-variant-numeric:tabular-nums"'))` | Draws the tick value with `nd` decimals, right-aligned 6 px left of the plot. The style gives all digits the same width. |
| 95 | `    if unit:` | When a unit text is given: |
| 96 | `        out.append(text(x0 - 34, sy(ticks[-1]) - 12, unit, 11, MUTED))` | draws it above the highest tick, 34 px left of the plot. |
| 97 | `    return ''.join(out)` | Returns all pieces as one text. |

### Function `line_panel`: one plot panel with lines and markers (lines 100 to 142)

| Line | Source | Explanation |
|---:|---|---|
| 100 | `def line_panel(x0, y0, pw, ph, series, xticks, yticks, xlog=True, xlabel=None, yunit=None, title=None,` | Starts the function `line_panel`. `x0`, `y0` is the top left corner of the plot area in px, `pw` its width and `ph` its height. `xticks` is a list of pairs of a value and a label. `yticks` is a list of values. `xlog` selects a logarithmic x axis and is on by default. |
| 101 | `               vmark=None, ynd=0, xfmt=None, labels=()):` | Continues the parameter list of line 100: `vmark` for a vertical reference line, `ynd` for the decimals of the y tick labels, `xfmt`, which the function does not use, and `labels` for direct labels. |
| 102 | `    """One plot panel. series: dict(name, color, pts=[(x, y, lo, hi, tip)], kind='line'\|'thin'\|'hollow', nomarker).` | Description of the function: it draws one plot panel. A series is a dictionary with a name, a color and a list `pts` of points. A point holds x, y, the low end and the high end of a range, and a tooltip text. `kind` is `line`, `thin` or `hollow`. `nomarker` switches the markers off. |
| 103 | `    vmark: (x value, label) draws a vertical reference line. labels: (x, y, text, dx, dy, anchor) direct labels."""` | Description, last line: `vmark` is an x value and a label, and it draws a vertical reference line. An entry of `labels` holds a data position x and y, a text, a shift `dx` and `dy` in px and the anchor. |
| 104 | `    sx = Scale(xticks[0][0], xticks[-1][0], x0, x0 + pw, log=xlog)` | `sx`: the x scale. It maps the value of the first x tick to the left edge of the plot and the value of the last x tick to the right edge. It is logarithmic when `xlog` is set. |
| 105 | `    sy = Scale(yticks[0], yticks[-1], y0 + ph, y0)` | `sy`: the y scale, which is linear. It maps the first y tick to the bottom edge of the plot and the last y tick to the top edge. So the y axis starts at the value of the first tick. |
| 106 | `    out = [y_axis(sy, yticks, x0, x0 + pw, yunit, ynd)]` | Starts the output with the grid lines and the tick labels of the y axis (`y_axis`). |
| 107 | `    out.append(f'<line x1="{x0}" y1="{y0 + ph}" x2="{x0 + pw}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')` | Draws the x axis as a line along the bottom edge of the plot. |
| 108 | `    for xv, lab in xticks:` | Starts a loop over the x ticks. |
| 109 | `        if lab is None:` | A tick without a label |
| 110 | `            continue` | is not drawn: it gets no tick mark and no label. The scale of line 104 takes the values of the first and of the last tick only. So a tick without a label has an effect only as the first or the last tick, where its value sets that end of the axis. |
| 111 | `        out.append(f'<line x1="{sx(xv):.1f}" y1="{y0 + ph}" x2="{sx(xv):.1f}" y2="{y0 + ph + 4}" stroke="{AXIS}" stroke-width="1"/>')` | Draws a tick mark of 4 px below the axis. |
| 112 | `        out.append(text(sx(xv), y0 + ph + 16, lab, 11, MUTED, 'middle'))` | Draws the label of the tick, centered 16 px below the axis. |
| 113 | `    if xlabel:` | When a title of the x axis is given: |
| 114 | `        out.append(text(x0 + pw / 2, y0 + ph + 32, xlabel, 11, MUTED, 'middle'))` | draws it centered, 32 px below the axis. |
| 115 | `    if title:` | When a panel title is given: |
| 116 | `        out.append(text(x0, y0 - 12, title, 13, INK, weight=600))` | draws it in bold above the top left corner of the plot. |
| 117 | `    if vmark:` | When a reference line is asked for: |
| 118 | `        xv, lab = vmark` | `xv`: its x value. `lab`: its label. |
| 119 | `        out.append(f'<line x1="{sx(xv):.1f}" y1="{y0}" x2="{sx(xv):.1f}" y2="{y0 + ph}" stroke="{AXIS}" stroke-width="1"/>')` | Draws a vertical line over the full height of the plot at the position of `xv`. |
| 120 | `        out.append(text(sx(xv) + 4, y0 + 10, lab, 11, INK2))` | Draws the label right of that line, near the top. |
| 121 | `    hits = []` | `hits`: the hit areas. They are collected apart from the drawing. Line 140 places them after all marks. |
| 122 | `    for s in series:` | Starts a loop over the series. |
| 123 | `        pts = [p for p in s['pts'] if p[1] is not None]` | `pts`: the points of the series that have a y value. A point without a y value is left out, and the line joins its two neighbours. |
| 124 | `        if not pts:` | A series without points |
| 125 | `            continue` | is skipped. |
| 126 | `        sw = 1.2 if s.get('kind') == 'thin' else 2` | `sw`: the line width, 1.2 px for the kind `thin` and 2 px otherwise. |
| 127 | `        d = ' '.join(f'{"M" if i == 0 else "L"}{sx(p[0]):.1f},{sy(p[1]):.1f}' for i, p in enumerate(pts))` | `d`: the path of the line in pixel coordinates. `M` moves to the first point and `L` draws a straight piece to each next point. |
| 128 | `        out.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>')` | Draws the path in the color of the series, without a fill and with round joins and ends. |
| 129 | `        for p in pts:` | Starts a loop over the points, for the range lines. |
| 130 | `            if p[2] is not None and p[3] is not None and abs(sy(p[2]) - sy(p[3])) > 3:` | Takes a point that has both ends of a range, when the two ends lie more than 3 px apart on the y axis. |
| 131 | `                out.append(f'<line x1="{sx(p[0]):.1f}" y1="{sy(p[2]):.1f}" x2="{sx(p[0]):.1f}" y2="{sy(p[3]):.1f}" stroke="{s["color"]}" stroke-width="1.2" opacity="0.55"/>')` | Draws a thin vertical line from the low end to the high end at the x position of the point. So a range that is smaller than 3 px is not visible. |
| 132 | `        if not s.get('nomarker'):` | Unless the series has `nomarker` set: |
| 133 | `            for p in pts:` | starts a loop over the points, |
| 134 | `                out.append(marker(sx(p[0]), sy(p[1]), s['color'], hollow=s.get('kind') == 'hollow', r=3.2))` | and draws a marker at each point. The marker is hollow for the kind `hollow`. With `r=3.2` a filled marker has a radius of 4.2 px. |
| 135 | `        for p in pts:` | Starts a loop over the points, for the tooltips. |
| 136 | `            if len(p) > 4 and p[4]:` | Takes a point that has a fifth value which is not empty. |
| 137 | `                hits.append(hit_circle(sx(p[0]), sy(p[1]), p[4], r=9))` | Adds a hit area of 9 px radius with that tooltip text. A point without a tooltip text gets no hit area. |
| 138 | `    for lx, ly, lt, dx, dy, anchor in labels:` | Starts a loop over the direct labels. |
| 139 | `        out.append(text(sx(lx) + dx, sy(ly) + dy, lt, 11, INK, anchor, weight=600))` | Draws the label in bold at its data position, moved by `dx` and `dy` px. |
| 140 | `    return ''.join(out) + ''.join(hits)` | Returns the drawing first and the hit areas after it. In SVG a later element lies on top, so the hit areas receive the pointer. |

### Function `dumbbell`: one row per pair of values (lines 143 to 179)

| Line | Source | Explanation |
|---:|---|---|
| 143 | `def dumbbell(w, rows, x0, x1, ticks, unit, title, desc, key, rowh=40, top=58, nd=1, note=None):` | Starts the function `dumbbell`. It returns a complete picture of the width `w` with one row per pair of values. `x0` and `x1` are the pixel positions of the first and of the last tick. `key` holds the names of the two values. `rowh` is the height of a row and `top` the y position of the first row. `nd` is the number of decimals of the value labels. |
| 144 | `    """rows: dict(label, sub, a, b, ca, cb, tipa, tipb, delta). key: (label a, label b). a, b in data units."""` | Description of the function: a row is a dictionary with a label, a second label line `sub`, the two values `a` and `b` in data units, their colors `ca` and `cb`, their tooltip texts and a text `delta`. `key` holds the legend names of `a` and of `b`. |
| 145 | `    h = top + rowh * len(rows) + 46` | `h`: the height of the picture. It is the top space, the rows and 46 px for the axis below. |
| 146 | `    sx = Scale(ticks[0], ticks[-1], x0, x1)` | `sx`: a linear x scale. It maps the first tick to `x0` and the last tick to `x1`. |
| 147 | `    out = [frame(w, h, title, desc)]` | Starts the output with the opening of the picture (`frame`). |
| 148 | `    out.append(f'<circle cx="{x0 + 5}" cy="16" r="5" fill="{SURFACE}" stroke="{INK2}" stroke-width="2"/>' + text(x0 + 16, 20, key[0], 12, INK2))` | Draws the first part of the key at the top: a hollow circle and the name of value `a`. |
| 149 | `    kx = x0 + 30 + 7 * len(key[0])` | `kx`: the x position of the second part of the key. The width of the first name is an estimate of 7 px per character. |
| 150 | `    out.append(f'<circle cx="{kx + 5}" cy="16" r="5.5" fill="{INK2}"/>' + text(kx + 16, 20, key[1], 12, INK2))` | Draws the second part of the key: a filled circle and the name of value `b`. |
| 151 | `    for t in ticks:` | Starts a loop over the ticks of the value axis. |
| 152 | `        out.append(f'<line x1="{sx(t):.1f}" y1="{top - 14}" x2="{sx(t):.1f}" y2="{top + rowh * len(rows) - 8}" stroke="{GRID}" stroke-width="1"/>')` | Draws a vertical grid line over all rows. |
| 153 | `        out.append(text(sx(t), top + rowh * len(rows) + 8, fmt(t, 0), 11, MUTED, 'middle'))` | Draws the tick value without decimals below the rows. |
| 154 | `    out.append(text((x0 + x1) / 2, top + rowh * len(rows) + 26, unit, 11, MUTED, 'middle'))` | Draws the unit text centered below the tick values. |
| 155 | `    hits = []` | `hits`: the hit areas. |
| 156 | `    for i, r in enumerate(rows):` | Starts a loop over the rows. |
| 157 | `        y = top + rowh * i + 6` | `y`: the vertical position of this row in px. The two dots and the line between them are drawn at this position. |
| 158 | `        out.append(text(12, y + 1, r['label'], 12.5, INK, weight=600))` | Draws the label of the row in bold at the left edge. |
| 159 | `        if r.get('sub'):` | When the row has a second label line: |
| 160 | `            out.append(text(12, y + 15, r['sub'], 11, MUTED))` | draws it below the label in grey. |
| 161 | `        xa, xb = sx(r['a']), sx(r['b'])` | `xa`, `xb`: the pixel positions of the two values on the value axis. |
| 162 | `        out.append(f'<line x1="{xa:.1f}" y1="{y}" x2="{xb:.1f}" y2="{y}" stroke="{r["cb"]}" stroke-width="2" opacity="0.45"/>')` | Draws the line that joins the two values, in the color `cb` and half transparent. |
| 163 | `        out.append(f'<circle cx="{xa:.1f}" cy="{y}" r="5" fill="{SURFACE}" stroke="{r["ca"]}" stroke-width="2"/>')` | Draws value `a` as a hollow circle with an outline in the color `ca`. |
| 164 | `        out.append(f'<circle cx="{xb:.1f}" cy="{y}" r="6.5" fill="{r["cb"]}" stroke="{SURFACE}" stroke-width="2"/>')` | Draws value `b` as a filled circle in the color `cb`, a little larger than the hollow one. |
| 165 | `        la, lb = fmt(r['a'], nd), fmt(r['b'], nd)` | `la`, `lb`: the two values as text with `nd` decimals. |
| 166 | `        left, right = (xa, la), (xb, lb)` | `left`, `right`: the two dots with their texts, first in the order `a`, `b`. |
| 167 | `        if xa > xb:` | When `a` lies right of `b`, |
| 168 | `            left, right = (xb, lb), (xa, la)` | the two are swapped. So `left` is always the dot at the smaller x position. |
| 169 | `        out.append(text(left[0] - 10, y + 4, left[1], 11.5, INK, 'end', extra=' style="font-variant-numeric:tabular-nums"'))` | Writes the value of the left dot, right-aligned 10 px left of it. |
| 170 | `        out.append(text(right[0] + 10, y + 4, right[1], 11.5, INK, 'start', extra=' style="font-variant-numeric:tabular-nums"'))` | Writes the value of the right dot, left-aligned 10 px right of it. So each dot has its number beside it, on the outer side. |
| 171 | `        if r.get('delta'):` | When the row has a `delta` text: |
| 172 | `            out.append(text(w - 12, y + 4, r['delta'], 12, INK, 'end', weight=600))` | writes it in bold at the right edge of the picture. |
| 173 | `        hits.append(hit_circle(xa, y, r['tipa']))` | Adds a hit area with the tooltip of value `a`. |
| 174 | `        hits.append(hit_circle(xb, y, r['tipb']))` | Adds a hit area with the tooltip of value `b`. |
| 175 | `    if note:` | When a note is given: |
| 176 | `        out.append(text(12, h - 6, note, 11, MUTED))` | writes it in grey at the bottom left. |
| 177 | `    return ''.join(out) + ''.join(hits) + '</svg>'` | Returns the drawing, then the hit areas, then the closing tag of the picture. |

### Function `hbars`: horizontal bars with a range line (lines 180 to 210)

| Line | Source | Explanation |
|---:|---|---|
| 180 | `def hbars(w, rows, x0, x1, ticks, unit, title, desc, rowh=34, top=20, nd=0, bands=()):` | Starts the function `hbars`. It returns a complete picture of the width `w` with one horizontal bar per row. `x0` and `x1` are the pixel positions of the first and of the last tick. `bands` is a list of shaded reference ranges. |
| 181 | `    """rows: dict(label, sub, v, lo, hi, color, tip, value_label). bands: (from, to, label) shaded reference ranges."""` | Description of the function: a row is a dictionary with a label, a second label line `sub`, the value `v`, the ends `lo` and `hi` of a range, a color, a tooltip text and a `value_label`. A band holds a start value, an end value and a label. |
| 182 | `    h = top + rowh * len(rows) + 44` | `h`: the height of the picture. It is the top space, the rows and 44 px for the axis below. |
| 183 | `    sx = Scale(ticks[0], ticks[-1], x0, x1)` | `sx`: a linear x scale. It maps the first tick to `x0` and the last tick to `x1`. |
| 184 | `    out = [frame(w, h, title, desc)]` | Starts the output with the opening of the picture (`frame`). |
| 185 | `    for a, b, lab in bands:` | Starts a loop over the reference bands. |
| 186 | `        out.append(f'<rect x="{sx(a):.1f}" y="{top - 6}" width="{sx(b) - sx(a):.1f}" height="{rowh * len(rows) + 4}" fill="{GRID}" opacity="0.55"/>')` | Draws a light grey, half transparent rectangle from the start value to the end value of the band, over all rows. |
| 187 | `        out.append(text((sx(a) + sx(b)) / 2, top + rowh * len(rows) + 30, lab, 10.5, MUTED, 'middle'))` | Writes the label of the band centered below it. |
| 188 | `    for t in ticks:` | Starts a loop over the ticks of the value axis. |
| 189 | `        out.append(f'<line x1="{sx(t):.1f}" y1="{top - 6}" x2="{sx(t):.1f}" y2="{top + rowh * len(rows) - 2}" stroke="{GRID}" stroke-width="1"/>')` | Draws a vertical grid line over all rows. |
| 190 | `        out.append(text(sx(t), top + rowh * len(rows) + 12, fmt(t, 0), 11, MUTED, 'middle'))` | Writes the tick value without decimals below the rows. |
| 191 | `    out.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{top + rowh * len(rows) - 2}" stroke="{AXIS}" stroke-width="1"/>')` | Draws the axis line at `x0`, where all bars start. |
| 192 | `    out.append(text(x1, top + rowh * len(rows) + 30, unit, 11, MUTED, 'end'))` | Writes the unit text right-aligned at `x1`, below the tick values. |
| 193 | `    hits = []` | `hits`: the hit areas. |
| 194 | `    for i, r in enumerate(rows):` | Starts a loop over the rows. |
| 195 | `        y = top + rowh * i` | `y`: the top edge of the bar of this row in px. |
| 196 | `        bh = 16` | `bh`: the thickness of a bar, 16 px. |
| 197 | `        out.append(text(12, y + 9, r['label'], 12.5, INK, weight=600))` | Writes the label of the row in bold at the left edge. |
| 198 | `        if r.get('sub'):` | When the row has a second label line: |
| 199 | `            out.append(text(12, y + 23, r['sub'], 10.5, MUTED))` | writes it below the label in grey. |
| 200 | `        xe = sx(r['v'])` | `xe`: the pixel position of the value `v`. The bar ends there. |
| 201 | `        rr = 4` | `rr`: the radius of the rounded corners, 4 px. |
| 202 | `        out.append(f'<path d="M{x0},{y} H{xe - rr:.1f} Q{xe:.1f},{y} {xe:.1f},{y + rr} V{y + bh - rr} Q{xe:.1f},{y + bh} {xe - rr:.1f},{y + bh} H{x0} Z" fill="{r["color"]}"/>')` | Draws the bar as a filled shape in the color of the row. It runs from `x0` to `xe`. The two corners at the value end are rounded and the two corners at the axis are square. The bar starts at the position of the first tick. So its length is in proportion to the value only when the first tick is 0. |
| 203 | `        if r.get('lo') is not None and r.get('hi') is not None and r['hi'] > r['lo']:` | When the row has both ends of a range and the high end is above the low end: |
| 204 | `            out.append(f'<line x1="{sx(r["lo"]):.1f}" y1="{y + bh / 2}" x2="{sx(r["hi"]):.1f}" y2="{y + bh / 2}" stroke="{INK}" stroke-width="1.5"/>')` | draws a horizontal line from the low end to the high end through the middle of the bar, in the ink color. |
| 205 | `            for e in (r['lo'], r['hi']):` | Starts a loop over the two ends of the range. |
| 206 | `                out.append(f'<line x1="{sx(e):.1f}" y1="{y + 3}" x2="{sx(e):.1f}" y2="{y + bh - 3}" stroke="{INK}" stroke-width="1.5"/>')` | Draws a short vertical end mark at each end. |
| 207 | `        lx = max(xe, sx(r['hi']) if r.get('hi') is not None else xe) + 8` | `lx`: the x position of the value label, 8 px right of the bar end or of the high end of the range, whichever lies further right. |
| 208 | `        out.append(text(lx, y + 12, r.get('value_label') or fmt(r['v'], nd), 12, INK, extra=' style="font-variant-numeric:tabular-nums"'))` | Writes the value label there: the text `value_label` of the row when it has one, otherwise the value with `nd` decimals. |
| 209 | `        hits.append(hit_rect(x0, y - 4, x1 - x0, bh + 8, r['tip']))` | Adds a hit area over the whole row, from `x0` to `x1`, with the tooltip text of the row. |
| 210 | `    return ''.join(out) + ''.join(hits) + '</svg>'` | Returns the drawing, then the hit areas, then the closing tag of the picture. |
