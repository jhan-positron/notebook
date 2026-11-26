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

1. The file defines the colors: five ink and line colors, the background, one color for each of the three read loops and one for context ({L8-17}).
2. Two small helpers make text safe (`esc`) and format numbers (`fmt`). The class `Scale` turns a data value into a pixel position, on a linear or a logarithmic scale ({L20-37}).
3. Four functions return single shapes: a text, an invisible hit area as a circle or a rectangle, and a marker ({L40-58}).
4. `legend` draws the key of the series. `frame` opens a picture. `y_axis` draws the grid lines and tick labels of a value axis ({L61-97}).
5. `line_panel` draws one plot panel: axes, an optional vertical reference line, and for each series a line, range lines, markers and hit areas ({L100-140}).
6. `dumbbell` returns a complete chart with one row per pair of values ({L143-177}).
7. `hbars` returns a complete chart with one horizontal bar per row, an optional range line on each bar and optional shaded bands ({L180-210}).

## Behavior a reader must know

- Scales: `Scale` is linear unless `log` is set. `line_panel` takes the first and the last tick as the ends of each axis. A value outside the ticks is drawn outside the plot area, not cut off ({L37}, {L104-105}).
- The y axis of `line_panel` and the value axis of `dumbbell` and `hbars` start at the first tick. A bar of `hbars` starts at that position too. So a bar length is in proportion to its value only when the first tick is 0 ({L202}).
- `line_panel` leaves out a point without a y value and joins its neighbours with a line. A caller that wants a gap must pass two series ({L123}).
- A range line of `line_panel` appears only when the range is larger than 3 px ({L130}). In `hbars` it appears when the high end is above the low end ({L203}).
- A point gets a tooltip only when the caller passes a tooltip text ({L136}).
- In `dumbbell` the hollow dot is always value `a` and the filled dot value `b`. The number beside a dot is the value itself with `nd` decimals ({L163-170}).
- `frame` leaves the `svg` element open. `dumbbell` and `hbars` close it. A caller that builds a picture from `frame` and `line_panel` must close it.
- The function `line_panel` has a parameter `xfmt` that it does not use ({L101}).
