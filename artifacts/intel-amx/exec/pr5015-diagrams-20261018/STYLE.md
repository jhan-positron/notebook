# Drawing conventions for the PR 5015 amx_attn.cpp diagram page

One page, one scheme. Read this whole file before drawing. Every figure is
a Python function that returns the HTML of one `<figure>` (inline SVG +
caption + legend + box register), built only from `svg_helpers.py`.

## Files

- `svg_helpers.py`: primitives. `C` = the colour tokens. `rect`, `text`,
  `lines`, `arrow` (+ `marker_defs`), `card_arrow` (arrow with a how-many
  label), `label_box` (title + sub-lines + citation), `fn_cell` (function
  name + ONE-line description + citation + tag), `cite`, `legend_chip`,
  `lane`, `work_block`, `figure`, `text_width`. `LEGEND` = the catalogue of
  legend entries (read it: the labels say what each colour means on THIS page).
- `difflib_units.py`: the diff parser (code excerpts; not used by figures).
- `page_common.py`: the page skeleton; `build(spec)`.
- `spec_builder.py amx_attn`: builds the page from `units_amx_attn.json` and
  the figure modules, writes
  `~/workspace/intel-AMX/muse-glimmer/diagramming-code-changes-PR5015-amx_attn.cpp.html`.
- `figs/base_amx_attn.py`: the base diagrams B1-B4. Exposes `b1()` .. `b4()`
  and the WORKED EXAMPLE constants and building blocks the change diagrams
  reuse (import them).
- `figs/d_amx_attn_<unit id>.py`: ONE change diagram per file (a1 .. a5).
  Exposes `fig()` (or `figs()` returning a list when a unit needs two) and a
  module-level string `BASE = "Updates B1: ..."` (which base diagram the
  unit's diagram updates, and how, one sentence). Never edit another unit's
  file.
- `render_one.py figs/<module>.py`: renders every figure of one module to
  `png/<id>.png` (run it, then LOOK at the PNG with the Read tool before you
  finish).
- `check_legend.py --show figs/<module>.py`: compares the declared legend with
  the styles the SVG uses (MISSING / UNUSED must be 0).
- `transpose_sim.py`: executes the transpose's intrinsic semantics on a
  labelled tile; the lane / selector / row facts quoted in figures come from
  its output.

Key: `amx_attn` (src/tron/kernels/amx_attn.cpp). Head 5061623a34, base
6198824246 (main), worktree /home/jhan/workspace/ai-runs/tron-glimmer-amx.

## Figure ids and sizes

- Figure id = `amx_attn-<name>`: `amx_attn-b1`, `amx_attn-d3`, `amx_attn-d3a`.
  Ids are the SVG `id` and the marker-id prefix: unique per page.
- Base diagrams: viewBox width 1000 (height as needed, at most ~900).
- Change diagrams sit in a half-width column beside the code: viewBox width
  640 to 720, height as needed (at most ~900; split into two figures if more).
- Font sizes: titles 12-13, labels 10-11, sub-labels 9-9.5, citations 8.5.
  Nothing below 8.5. Monospace for identifiers, sans for prose.

## What every figure must have

1. **Names from the code only.** A box label is an identifier
   (`q_packed`, `s_transposed`, `store_transposed_rows<lane>`, `P`,
   `ACCUMULATOR_TILE_0`) or a phrase quoted from a comment ("zero padding",
   "the group_heads useful query rows"). No invented shorthand. The two
   group sizes are always written `GROUP_HEADS_4` / `GROUP_HEADS_16` or
   "4 heads" / "16 heads"; the template parameter is `group_heads`; the
   model's ratio is `kv_mul` (the caller passes `geometry.kv_mul()` /
   `operation_kv_mul`).
2. **A citation on every box**: `cite(x, y, 'amx_attn.cpp:201')` in the
   lower-right corner (or `ref=` of `label_box` / `fn_cell`), AND the same
   list passed to `figure(..., boxes=[(label, source), ...])` so the page can
   print "Boxes and their sources". Source = the line or Note that DEFINES
   the box (the declaration, or the comment that names the concept). Files
   the checker knows: amx_attn.cpp, amx_attn_iface.hpp, self_attention.hpp,
   v_vnni.hpp, kv_cache_fwd.hpp, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp,
   t_llama_unit.cpp. A removed base line is cited as `base amx_attn.cpp:209`.
3. **Every function cell carries a one-line description** of what the
   function does (`fn_cell(..., desc=...)`), from its comment.
4. **Every arrow between data-model boxes is labelled with how many**
   (`card_arrow(..., label='1 q_group -> 4 panels')`). The expression must
   come from the code (`HEAD_SIZE_128 / DIM_STEP_32` = 4 panels, `group_heads`
   columns, `TILE_ROWS_16` rows, `PAGE_TOKENS_64 / TILE_ROWS_16` = 4 K slices).
5. **Colours = concepts** (see `C` and `LEGEND` in svg_helpers.py):
   - query side violet (`q`): `q_group`, the packed Q panels (`packed` /
     `q_packed`, the B operand of QK), `Q_TILE_6`;
   - row-major K orange (`rm`): the K page `k_rows` (the A operand of QK),
     `K_EVEN_BLOCK_TILE_4` / `K_ODD_BLOCK_TILE_5`;
   - VNNI pair-interleaved V blue (`vnni`): `v_pairs` (the B operand of PV),
     `V_EVEN_SLICE_TILE_5` / `V_ODD_SLICE_TILE_6`;
   - scores and weights green (`rows`): `s_transposed`, `s`, `exp_rows`, the
     `P` scratch (the A operand of PV), `P_TILE_4`;
   - the output purple (`blk`): `o` (16 x 128 fp32) and the caller's `amx_o`;
   - a tile register grey-blue (`unit`): `ACCUMULATOR_TILE_0..3` and the
     operand tiles 4..6, the tile configuration;
   - a 128-bit lane vermillion (`pend_solid`): lane 0..3 of a 512-bit register
     `u[row_group][k]`, the `lane` template argument, `pair_sel` / `quad_sel`;
     dashed (`pend`) = a lane the 4-head kernel does not store;
   - 16-heads-only sky blue (`eagle`): what exists only when `group_heads` is
     16: lanes 1..3 of the store, columns 4..15 / rows 4..15 written;
   - the group-size gate yellow (`hw`): `group_heads_ok`, `GROUP_HEADS_4`,
     `GROUP_HEADS_16`, the `requires` clause, the explicit instantiation list;
   - zero padding / not written grey dashed (`empty`): columns
     `group_heads..15` of a packed-Q panel, rows `group_heads..15` of `P` and
     of `o` (for 4 heads);
   - the worked example's element (`hi`): query head 9, token 37;
   - before / removed red dashed (`gone`): the base code (the 4-only `for (k)`
     store loop, the `GROUP_HEADS_4` loop bounds). The words "new" and
     "changed" are markers in bold ink (`C['new']` is ink), not a colour.
   - context grey (`ctx`): the callers in self_attention.hpp and the interface
     header. Threads are LANES or bracketed names, never colours.
6. **A caption** (1-3 plain-English sentences: what the figure shows and
   what to look at) and, for change diagrams, which base diagram it updates
   and how (the caption starts with "Updates B2: ...").
7. **The worked example** of the page (below) reused wherever a concrete
   instance helps. Say "worked example" in the caption when used.
8. **Removed/old state** is drawn in `C['gone']` (red) with a dashed outline
   and the word "removed" or "before"; new state is marked "new" in
   `C['new']` where the figure contrasts before and after.
9. **A legend** (`figure(..., legend=[...])`) listing every style the figure
   uses and nothing else; `check_legend.py` must report 0 problems.

## Worked example (the same in every figure that needs an instance)

- Model: Muse Glimmer 30B, head size 128, 2 KV heads, 32 query heads, so
  `kv_mul` = 16 = `group_heads` (the 16-head instantiation). Contrast:
  llama-8b, `kv_mul` 4 (the 4-head instantiation): query head 9 does not
  exist, lanes 1..3 are not stored, columns 4..15 of each panel and rows
  4..15 of `P` and `o` are zero padding.
- One dense 64-token page, KV head 0, query heads 0..15 of its group.
- The element: query head 9, token 37 of the page.
  - QK: `s_transposed[37][9]` is in tile r = 2 (tokens 32..47), tile row 5
    (token 37 = 32 + 5), column 9. Row 5 is row_group 1 (rows 4..7),
    position 1. After the unpack stages, lane 2 of `u[1][1]` holds column
    9 (= 4 * 2 + 1) of tokens 36..39, so the element sits at position 1 of
    that lane. `store_transposed_rows<2>` (pair_sel 0x88, quad_sel 0xdd),
    k = 1, writes s row 2 * 4 + 1 = 9: `s_rows = s_block + 2 * 4 * stride`,
    `s_block = s + 2 * 16`, so the 16-token store lands at `s + 9 * stride
    + 32`, and element 5 of it is `s[9][37]`. (transpose_sim.py prints
    exactly this chain and checks it.)
  - PV: `exp_rows + 9 * row_stride_floats + 37` is converted into `P[9][37]`
    (rounded to nearest even, `_mm512_cvtne2ps_pbh`). `P[9]` is row 9 of the
    A tile; `o[9][d]` = sum over the 64 tokens of `P[9][t] * V[t][d]`.
- Counts that recur: 4 panels per packed Q (`HEAD_SIZE_128 / DIM_STEP_32`),
  16 dim-pair rows per panel (`DIM_STEP_32 / 2`), 16 columns per row, 2
  values per column; 4 K slices of 16 tokens per page; 4 steps of 32 dims;
  16 `_tile_dpbf16ps` per kernel per page (4 steps x 4 slices in QK, 2 halves
  x 2 s x 4 tiles in PV); 64 in the binary = 2 kernels x 16 x 2
  instantiations.

## Traps (found on the earlier pages; do not repeat)

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
cd /home/jhan/workspace/intel-AMX/exec/pr5015-diagrams-20261018
python3 render_one.py figs/base_amx_attn.py      # -> png/amx_attn-b1.png ...
python3 render_one.py figs/d_amx_attn_a3.py      # -> png/amx_attn-d3.png
python3 check_legend.py --show figs/d_amx_attn_a3.py
```
Then open each PNG with the Read tool and inspect it. Report what you fixed.

## The per-figure "Colour and font scheme"

Every figure declares the styles it uses: `figure(..., legend=[...])`. The
page prints them under the SVG as chips. Items:

- `"vnni"`: a key of `svg_helpers.LEGEND` (the catalogue).
- `("box", "white box, ink outline: the four statements of ...")`:
  a catalogue key with a label specific to THIS figure. Use this form whenever
  the generic label does not say what the style marks here.
- `("orange frame: ...", "none", C["rm"], False, True)`: a figure-specific box
  style `(label, fill, stroke, dashed, thick)`.
- `("pale band ...", C["pend"], "none", False, False, 0.10)`: the same five
  fields plus the fill opacity of a tinted band.
- `("blue arrow: ...", "arrow", C["vnni"])`: a figure-specific arrow colour.
- `("blue text: ...", "text", C["vnni"])`: coloured text when the figure has no
  box or arrow of that colour.
- `("thin grey line ...", "line", C["muted"])` (add `, True` for dashed).
- `("blue box and arrow: ...", "multi", ["vnni", ("arrow", C["vnni"])])`: ONE
  entry for the several styles of one concept.
- `"font_tag_changed"`: the tag font shown with the grey word 'changed', for a
  figure that tags nothing 'new'.

Rules: every style the SVG uses must have an entry, and every entry must be
used. Fonts: declare `font_mono`, `font_sans`, `font_cite` and `font_tag` when
the figure has them (nearly always). A label says what the style MARKS in this
figure, in plain English, with the names from the code.
