# Drawing conventions for the PR 4956 diagram pages

Copied from exec/pr4424-diagrams-20261009/STYLE.md (the PR 4424 set) and cut to
what PR 4956 (the first PR of the split of PR 4424: "Add the VNNI K layout and
its readers") contains. Three pages, one scheme. Read this whole file before
drawing. Every figure is a Python function that returns the HTML of one
`<figure>` (inline SVG + caption + box register), built only from
`svg_helpers.py`.

## What PR 4956 contains (and what it does NOT)

PR 4956 = branch jhan-vnnik-1-layout, head a5697f86d3, merge base 76bb0bf3f4
(main). It adds:
- h/tron/tensor/k_vnni.hpp (299 lines, new): constants, k_vnni::index,
  layout_on, k_vnni_view, k_vnni_tensor, detail::k_vnni_access, the transfer
  rows (const_k_row_view, k_row_view, k_source_row, k_destination_row),
  pair_base, pair_row_offsets, store_row, load_row, copy_token.
- h/tron/kernels/k_vnni.hpp (99 lines, new): MAX_KV_MUL_16 and the AVX-512
  score reader k_vnni::qk_group (bf16, float and fp16 queries, live mask,
  recursion above 16 heads).
- h/tron/models/kv_cache.hpp: Note [K VNNI storage]; kv_block::k becomes
  k_storage (k_vnni_tensor for a VNNI slot, native_k_storage otherwise);
  k_view / k_at / page::k exist only for row-major slots; page::k_packed,
  set_k_row, get_k_row (geometry and uniform overloads); copy_storage_slot
  copies a whole page as one owner assignment and any other range with
  copy_token; fill_storage_slot reaches a packed plane through
  detail::k_vnni_access.
- callers: model.hpp save_k (set_k_row), self_attention.hpp (the AMX page
  path is not compiled for a VNNI slot; the loop marks `live`, qk_group scores
  after the loop), full.hpp page_info::k_head_fn (get_k_row into the scratch),
  gof.hpp / gof.cpp (k_head_fn takes a scratch row, k_scratch), kv_cache_fwd.hpp
  (forward declarations), CMake option TRON_K_VNNI, tests.

It does NOT contain (these land in PR 4957 / 4958 / 4959, never draw them as
present): store_block, the register transpose, Note [Row-major tail block],
row_major_row / store_row_major / load_row_major, block_to_vnni / block_to_rows,
k_rows_saved_ / k_vnni_blocks_ and their bit helpers, note_k_row_saved,
k_block_to_vnni_at, k_forget_row, pending_k_blocks_, the shared save_k window
(k_store_shared, k_store_cut_units, store_k_block), set_k_block,
k_row_if_row_major, the AMX kernel qk_vnni_128x4 and pack_q_rows_128x4. When a
diagram needs to say that something is future work, name the later PR in a
grey context box ("lands in PR 4957"), never as an existing function.

## Files

- `svg_helpers.py`: primitives. `C` = the colour tokens. `rect`, `text`,
  `lines`, `arrow` (+ `marker_defs`), `card_arrow` (arrow with a how-many
  label), `label_box` (title + sub-lines + citation), `fn_cell` (function
  name + ONE-line description + citation + tag), `cite`, `bit_row`,
  `legend_chip`, `lane`, `work_block`, `figure`, `text_width`.
- `difflib_units.py`: the diff parser (code excerpts; not used by figures).
  WT = ~/workspace/ai-runs/tron-split-pr1, BASE 76bb0bf3f4, HEAD a5697f86d3.
- `page_common.py`: the page skeleton; `build(spec)`. Its LEGEND is the
  global colour and font scheme of the three pages: use only the concepts it
  lists.
- `spec_builder.py`: builds a page spec from `units_<key>.json` and the
  figure modules. Keys: `k_vnni` (h/tron/tensor/k_vnni.hpp), `kv_cache`
  (h/tron/models/kv_cache.hpp), `kernels` (h/tron/kernels/k_vnni.hpp).
  Output: PR3879/new-PRs/split-4424/diagramming-code-changes-PR4956-<name>.html.
- `figs/base_<key>.py`: the base diagrams of one page. Exposes `b1()`,
  `b2()`, ... (each returns a figure's HTML) and the WORKED EXAMPLE constants
  and any building-block functions the change diagrams reuse (import them).
  A base figure may live in its own module `figs/base_<key>_<name>.py`
  exposing `<name>()` (as base_k_vnni_b1a.py does).
- `figs/d_<key>_<unit id>.py`: ONE change diagram per file. Exposes `fig()`
  (or `figs()` returning a list when a unit needs two) and a module-level
  string `BASE = "Updates B2: ..."` (which base diagram the unit's diagram
  updates, and how, one sentence). Never edit another unit's file.
- `render_one.py`: renders every figure of one module to `png/<id>.png`
  (run it, then LOOK at the PNG with the Read tool before you finish).
- `check_legend.py figs/<module>.py`: the per-figure scheme check.
- `check_page.py <page.html>`: the structural checks of a built page.

## Figure ids and sizes

- Figure id = `<key>-<name>`: `kv_cache-b1`, `k_vnni-d3`, `kernels-d2a`.
  Ids are the SVG `id` and the marker-id prefix: unique per page.
- Base diagrams: viewBox width 1000 (height as needed, at most ~800).
- Change diagrams sit in a half-width column beside the code: viewBox width
  640 to 720, height as needed (at most ~900; split into two figures if more).
- Font sizes: titles 12-13, labels 10-11, sub-labels 9-9.5, citations 8.5.
  Nothing below 8.5. Monospace for identifiers, sans for prose.

## What every figure must have

1. **Names from the code only.** A box label is an identifier
   (`k_vnni_tensor`, `k_storage`, `store_row`, `live`) or a phrase quoted
   from a comment. No invented shorthand, no abbreviations the code does not
   use.
2. **A citation on every box**: `cite(x, y, 'kv_cache.hpp:2566')` in the
   lower-right corner (or `ref=` of `label_box` / `fn_cell`), AND the same
   list passed to `figure(..., boxes=[(label, source), ...])` so the page can
   print "Boxes and their sources". Source = the line or Note that DEFINES
   the box (the declaration, or the comment that names the concept). Line
   numbers are HEAD line numbers of PR 4956 (a5697f86d3): verify each one
   with `git -C ~/workspace/ai-runs/tron-split-pr1 show a5697f86d3:<path>`.
   For the kernels page cite `kernels/k_vnni.hpp:NN`; a bare `k_vnni.hpp:NN`
   means h/tron/tensor/k_vnni.hpp.
3. **Every function cell carries a one-line description** of what the
   function does (`fn_cell(..., desc=...)`), from its comment.
4. **Every arrow between data-model boxes is labelled with how many**
   (`card_arrow(..., label='1 plane -> N_PANELS_16 panels')`). The expression
   must come from the code.
5. **Colours = concepts** (see page_common.LEGEND and `svg_helpers.LEGEND`):
   VNNI blue (`vnni`, `vnni_solid`), row-major orange (`rm`, `rm_solid`),
   empty / not-live grey dashed (`empty`), the live mask green (`live`),
   hardware attention and FPGA staging yellow (`hw`), EAGLE sky blue
   (`eagle`), query side violet (`q`), the worked example's cell (`hi`),
   "does not exist" (`deleted`), before / removed red dashed (`gone`), context
   grey (`ctx`), plain boxes (`box`), lanes and frames (`lane`), arrows
   (`arrow`, `arrow_muted`), fonts (`font_mono`, `font_sans`, `font_cite`,
   `font_tag` / `font_tag_changed`). Do NOT use `pend`, `pend_solid`, `rows`,
   `blk`, `unit`, `crit`, `idle`: those concepts are not in PR 4956 (`idle`
   may be used in a wall-clock-lanes figure only). Threads are LANES or
   bracketed names `[main thread]`, never colours.
6. **A caption** (1-3 plain-English sentences: what the figure shows and
   what to look at) and, for change diagrams, which base diagram it updates
   and how (the caption starts with "Updates B2: ...").
7. **The worked example** of the page (below) reused wherever a concrete
   instance helps. Say "worked example" in the caption when used.
8. **Removed/old state** is drawn in `C['gone']` (red) with a dashed outline
   and the word "removed" or "before"; new state is marked "new" in
   `C['new']` where the figure contrasts before and after.

## Worked example (the same on all three pages)

- Page 7, storage slot 5, KV head 0, a VNNI slot (128-dimension head,
  TRON_K_VNNI on). The K rows of page offsets 0..40 are saved (41 tokens,
  one save_k call per token: set_k_row -> store_row).
- Token 37 = token block c = 2, lane t = 5. Dimension 70 = step s = 2, pair
  dp = 3, j = 0. k_vnni::index(37, 70) = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2
  + 0 = 5226; byte offset 10452; panel #10 = (s 2, c 2).
- One scoring visit: a query group of kv_mul = 4 heads (q rows of 128 bf16)
  scores page 7. The loop of apply_page_tok marks offsets 0..40 in `live`
  (relevant_k_tokens = 41). qk_group reads token blocks c = 0 and 1 with mask
  0xffff, c = 2 with mask 0x01ff (tokens 32..40), and skips c = 3 (mask 0).
  Output: s_pages[h][t] for the 41 live tokens; the other entries stay
  -infinity (the caller's fill).
- The FPGA staging of the GOF (group of four tokens) 36..39 of page 7 calls
  page_info::k_head_fn for token 37; the scheduler's callback runs get_k_row
  -> load_row into k_scratch and returns the scratch row.
- A page copy (copy_storage_slot) of 41 tokens from page 7 offset 0 to page 9
  offset 0 moves token by token (copy_token: 41 load_row + 41 store_row); a
  copy of all 64 tokens would be one owner assignment dst_block.k = src_block.k.

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
- Line numbers of the PR 4424 modules you adapt are STALE (PR 4424 head
  9d5c7a389b). Re-derive every number from the PR 4956 head.

## How to check

```
cd /home/jhan/workspace/intel-AMX/exec/pr4956-diagrams-20261015
python3 render_one.py figs/base_kv_cache.py      # -> png/kv_cache-b1.png ...
python3 render_one.py figs/d_kv_cache_c3.py      # -> png/kv_cache-d3.png
python3 check_legend.py --show figs/<module>.py  # 0 problems
python3 spec_builder.py <key>                    # builds the page (asserts coverage)
python3 check_page.py <built page>               # 0 problems
```
Then open each PNG with the Read tool and inspect it. Report what you fixed.

## The per-figure "Colour and font scheme"

Every figure declares the styles it uses: `figure(..., legend=[...])`. The
page prints them under the SVG as chips, so each section or diagram repeats
the scheme with only the colours and fonts it uses. Items:

- `"vnni"`: a key of `svg_helpers.LEGEND` (the catalogue: concept boxes,
  arrows, fonts; read it).
- `("box", "white box, ink outline: the entities plane, token block c, token i")`:
  a catalogue key with a label specific to THIS figure. Use this form whenever
  the generic label does not say what the style marks here.
- `("orange frame: the row of token 37", "none", C["rm"], False, True)`:
  a figure-specific box style `(label, fill, stroke, dashed, thick)`.
- `("pale band ...", C["q"], "none", False, False, 0.10)`: the
  same five fields plus the fill opacity of a tinted band.
- `("blue arrow: as_view(), owner -> view", "arrow", C["vnni"])`: a
  figure-specific arrow colour.
- `("blue text: ...", "text", C["vnni"])`: coloured text when the figure has
  no box or arrow of that colour.
- `("thin grey line down a lane: the order of the steps", "line", C["muted"])` (add
  `, True` for a dashed line): a thin line without an arrowhead.
- `("blue box and arrow: the VNNI path ...", "multi", ["vnni", ("arrow", C["vnni"])])`:
  ONE entry for the several styles of one concept.
- `"font_tag_changed"`: the tag font shown with the grey word 'changed', for a
  figure that tags nothing 'new'.

Rules: every style the SVG uses must have an entry, and every entry must be
used (no copy of the global scheme). Fonts: declare `font_mono`, `font_sans`,
`font_cite` and `font_tag` when the figure has them (nearly always). A label
says what the style MARKS in this figure, in plain English, with the names
from the code. Check with `python3 check_legend.py --show figs/<module>.py`
until it reports 0 problems.
