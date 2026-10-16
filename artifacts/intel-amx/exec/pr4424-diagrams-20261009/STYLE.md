# Drawing conventions for the PR 4424 diagram pages

Three pages, one scheme. Read this whole file before drawing. Every figure is
a Python function that returns the HTML of one `<figure>` (inline SVG +
caption + box register), built only from `svg_helpers.py`.

## Files

- `svg_helpers.py`: primitives. `C` = the colour tokens. `rect`, `text`,
  `lines`, `arrow` (+ `marker_defs`), `card_arrow` (arrow with a how-many
  label), `label_box` (title + sub-lines + citation), `fn_cell` (function
  name + ONE-line description + citation + tag), `cite`, `bit_row`,
  `block_cell` (a 16-token block by state), `legend_chip`, `lane`,
  `work_block`, `figure`, `text_width`.
- `difflib_units.py`: the diff parser (code excerpts; not used by figures).
- `page_common.py`: the page skeleton; `build(spec)`.
- `spec_builder.py`: builds a page spec from `units_<key>.json`, the glossary
  in `facts/<key>.json`, and the figure modules.
- `figs/base_<key>.py`: the base diagrams of one page. Exposes `b1()`,
  `b2()`, ... (each returns a figure's HTML) and the WORKED EXAMPLE constants
  and any building-block functions the change diagrams reuse (import them).
- `figs/d_<key>_<unit id>.py`: ONE change diagram per file. Exposes `fig()`
  (or `figs()` returning a list when a unit needs two) and a module-level
  string `BASE = "Updates B2: ..."` (which base diagram the unit's diagram
  updates, and how, one sentence). Never edit another unit's file.
- `render_one.py`: renders every figure of one module to `png/<id>.png`
  (run it, then LOOK at the PNG with the Read tool before you finish).

Keys: `kv_cache` (h/tron/models/kv_cache.hpp), `k_vnni`
(h/tron/tensor/k_vnni.hpp), `model` (h/tron/models/model.hpp).

## Figure ids and sizes

- Figure id = `<key>-<name>`: `kv_cache-b1`, `k_vnni-d3`, `model-d5a`.
  Ids are the SVG `id` and the marker-id prefix: unique per page.
- Base diagrams: viewBox width 1000 (height as needed, at most ~800).
- Change diagrams sit in a half-width column beside the code: viewBox width
  640 to 720, height as needed (at most ~900; split into two figures if more).
- Font sizes: titles 12-13, labels 10-11, sub-labels 9-9.5, citations 8.5.
  Nothing below 8.5. Monospace for identifiers, sans for prose.

## What every figure must have

1. **Names from the code only.** A box label is an identifier
   (`k_rows_saved_`, `k_storage_ref`, `store_block`) or a phrase quoted from
   a comment ("complete, may wait": kv_cache.hpp:684-685 says "a complete
   block may wait for its conversion"). No invented shorthand, no
   abbreviations the code does not use. The block states are named the same
   on all three pages: "no row bit" / "row-major rows" / "complete, may wait"
   / "converted: VNNI layout" / "row-major, no bits (hardware attention)".
2. **A citation on every box**: `cite(x, y, 'kv_cache.hpp:2391')` in the
   lower-right corner (or `ref=` of `label_box` / `fn_cell`), AND the same
   list passed to `figure(..., boxes=[(label, source), ...])` so the page can
   print "Boxes and their sources". Source = the line or Note that DEFINES
   the box (the declaration, or the comment that names the concept). Take
   the line numbers from `facts/<key>.json` (verified) or from the head file.
3. **Every function cell carries a one-line description** of what the
   function does (`fn_cell(..., desc=...)`), from its comment. Use the
   `one_line` of the verified function claims.
4. **Every arrow between data-model boxes is labelled with how many**
   (`card_arrow(..., label='1 page -> n_slots + 1 entries')`). Use the
   verified cardinality claims; the expression must come from the code.
5. **Colours = concepts** (see `C`): row-major orange, VNNI blue,
   complete-may-wait vermillion dashed (solid vermillion = the
   conversion of such a block), `k_rows_saved_` green, `k_vnni_blocks_`
   purple, hardware attention yellow (also the FPGA staging path), EAGLE sky
   blue, query/scores violet, work unit grey-blue (`C['unit']`), empty grey
   dashed, the worked example's cell `C['hi_fill']`. The words "new" and
   "changed" are markers in bold ink (`C['new']` is ink), not a colour. A
   function or route the code does not provide: white box, grey (`C['muted']`)
   dashed outline, the word "deleted" or "does not exist". The critical path
   of a wall-clock-lanes figure: thick SOLID red frame (`C['crit']`); removed
   code is the same red DASHED (`C['gone']`). Threads are LANES or bracketed
   names `[main thread]`, never colours.
6. **A caption** (1-3 plain-English sentences: what the figure shows and
   what to look at) and, for change diagrams, which base diagram it updates
   and how (the caption starts with "Updates B2: ...").
7. **The worked example** of the page (below) reused wherever a concrete
   instance helps. Say "worked example" in the caption when used.
8. **Removed/old state** is drawn in `C['gone']` (red) with a dashed outline
   and the word "removed" or "before"; new state is marked "new" in
   `C['new']` where the figure contrasts before and after.

## Worked examples (the same on all three pages)

- Page 7, storage slot 5 (layer 5), after the K rows of offsets 0..40 were
  saved: block 0 converted (VNNI), block 1 complete and waits for the
  forward end, block 2 holds 9 row-major rows (offsets 32..40), block 3
  empty. `k_rows_saved_[5]` = bits 0..40 set; `k_vnni_blocks_[5]` = 0b0001.
- Token 37 = block 2, t = 5. Dimension 70 = step 2, pair 3, j = 0. Its
  element index in the plane is `k_vnni::index(37, 70)`; compute it with the
  formula and print the number in the figure.
- A shared save_k window: 3 workers (main + 2 helpers), 40 items: user A
  tokens at page 7 offsets 0..31 (two whole blocks), user B tokens at page 9
  offsets 32..39 (8 tokens). Units: [0,16) [16,32) [32,40): two whole-block
  saves (`set_k_block`), one row-by-row run (`set_k_row`, row-major). Its
  continuation (model page): a later pass saves page 9 offsets 40..47, which
  completes block 2 of page 9; that block is the one queued entry of
  `pending_k_blocks_`. The page-7 example above (block 1 complete, not
  converted) is a later moment of page 7, after block 1 was saved row by row.

## Traps (found on the earlier PR 4737 page; do not repeat)

- A white dashed "idle" box drawn after text hides the text: draw idle boxes
  FIRST, text last.
- A label centred on a vertical arrow's x collides with the line: offset
  labels by 6-10 px from any line they run along.
- Marker ids must be unique per figure: always `marker_defs(fid, {...})`
  with the figure's own id, and `arrow(fid, name, ...)`.
- Lane labels need a 140 px gutter and at most 2 short lines.
- Text wider than its box: estimate with `text_width(s, size, mono)` and
  widen the box or shorten the text. Check the PNG.
- Keep every string ASCII (the page must be pure ASCII: write "->" not an
  arrow glyph, "x" not a multiplication sign, "..." not an ellipsis glyph).
- `figure()` escapes nothing inside `body`; `text()` escapes its string.
- Nothing may overlap: after rendering, look for clipped text, text on
  lines, boxes over boxes. Fix and re-render until clean.

## How to check

```
cd /home/jhan/workspace/intel-AMX/exec/pr4424-diagrams-20261009
python3 render_one.py figs/base_kv_cache.py      # -> png/kv_cache-b1.png ...
python3 render_one.py figs/d_kv_cache_c3.py      # -> png/kv_cache-d3.png
```
Then open each PNG with the Read tool and inspect it. Report what you fixed.

## The per-figure "Colour and font scheme" (added 2026-10-09, second request)

Every figure declares the styles it uses: `figure(..., legend=[...])`. The
page prints them under the SVG as chips, so each section or diagram repeats
the scheme with only the colours and fonts it uses. Items:

- `"vnni"`: a key of `svg_helpers.LEGEND` (the catalogue: concept boxes,
  arrows, fonts; read it).
- `("box", "white box, ink outline: the entities plane, token block c, token i")`:
  a catalogue key with a label specific to THIS figure. Use this form whenever
  the generic label does not say what the style marks here.
- `("orange frame: panel (1,2) #6, the row-major row of token 37", "none", C["rm"], False, True)`:
  a figure-specific box style `(label, fill, stroke, dashed, thick)`.
- `("pale orange-red band ...", C["pend"], "none", False, False, 0.10)`: the
  same five fields plus the fill opacity of a tinted band; the chip shows the
  fill at that opacity, and the data-style stays the fill's.
- `("blue arrow: as_view(), owner -> view", "arrow", C["vnni"])`: a
  figure-specific arrow colour.
- `("blue text: the converted-block branch, k_block_is_vnni -> store_row", "text", C["vnni"])`:
  coloured text when the figure has no box or arrow of that colour (a box or
  arrow entry of the same colour already covers its text).
- `("thin grey line down a lane: the order of the steps", "line", C["muted"])` (add
  `, True` for a dashed line): a thin line without an arrowhead. Optional in the
  check, like the frames.
- `("blue box and arrow: the VNNI path ...", "multi", ["vnni", ("arrow", C["vnni"])])`:
  ONE entry for the several styles of one concept. A part is a catalogue key,
  `("arrow", colour)`, `("text", colour)`, `("line", colour[, True])` or
  `(fill, stroke, dashed, thick)`.
- `"font_tag_changed"`: the tag font shown with the grey word 'changed', for a
  figure that tags nothing 'new'.

Rules: every style the SVG uses must have an entry, and every entry must be
used (no copy of the global scheme). Structural frames (`"lane"`, `"ctx"`:
white, soft-grey or no fill with the thin grey line) are optional: declare
them when the reader needs them, and only when the figure draws them. Fonts: declare `font_mono`, `font_sans`,
`font_cite` and `font_tag` when the figure has them (nearly always). A label
says what the style MARKS in this figure, in plain English, with the names
from the code. Check with `python3 check_legend.py --show figs/<module>.py`
(lists the styles each figure uses, then MISSING / UNUSED entries) until it
reports 0 problems.
