# Drawing conventions for the PR 4958 diagram pages

Copied from exec/pr4956-diagrams-20261015/STYLE.md (the PR 4956 set) and cut
to what PR 4958 (the third PR of the split of PR 4424: "Save K in 16-token
blocks, shared with idle worker threads") contains. Three pages, one scheme.
Read this whole file before drawing. Every figure is a Python function that
returns the HTML of one `<figure>` (inline SVG + caption + box register),
built only from `svg_helpers.py`.

## What PR 4958 contains (and what it does NOT)

PR 4958 = branch jhan-vnnik-3-shared-save, head b39765ec29, base 26b86a279a
(= the head of PR 4957, branch jhan-vnnik-2-amx). The worktree
~/workspace/ai-runs/tron-split-pr3 is at the head. Non-test source changes:
- h/tron/models/common.hpp (+29): `batch::k_store_window_t` (the K store
  window of one minibatch: max_shared_workers = 128, next_unit, opened,
  finished, n_units, unit_start[max_minibatch_size + 1],
  helper_windows[max_shared_workers]) and the member `k_store_window`;
  includes <array>, <atomic>.
- h/tron/models/model.hpp (+298/-29): Note [Shared block save]; the constants
  k_store_block (= BLOCK_TOKENS_16), k_scatter_run_len (= 1),
  k_join_clock_spins (2^20), k_join_timeout_s (120); k_store_shared (the
  sharing decision, the same answer on every thread); k_store_cut_units (the
  work units); store_k_block (a run of consecutive items in one block: 1 token
  -> set_k_row scatter, 2..16 tokens -> set_k_block with the present mask;
  row-major slots: page::k(...).set per token); save_k_impl takes worker_ix
  and n_workers, runs the window protocol (main: cut, reset next_unit and
  finished, opened.fetch_add release; helper: wait opened >= its W-th window;
  all: claim units with next_unit.fetch_add; helper: finished.fetch_add and
  return; main: spin on finished with the watchdog), then the marks loop
  (mark_k_complete, GOF credits) on main only; the per-token store inside the
  marks loop is REMOVED (base lines 3095-3117); the two save_k entry points
  take worker_ix = 0 and n_workers = 1 by default.
- h/tron/tensor/k_vnni.hpp (+89/-8): FULL_BLOCK_0XFFFF, LANES_16 and two
  static_asserts; detail::transpose_16x16_epi32 (4 stages, 64 shuffles);
  store_block (per dimension step s: one 64-byte load per present row, the
  transpose, 16 line stores into panel (s, c), masked to `present` when the
  block is partial); the comment of store_row says several threads may store
  different tokens of one plane at the same time; header comments name
  store_block and page::set_k_block.
- h/tron/models/kv_cache.hpp (+42, not a target page): page::set_k_block
  (slot, kv_head, c, present, rows) -> store_block on the owner's view; Note
  [K VNNI storage] item 1 rewritten (block save for a run of 2..16 tokens,
  set_k_row scatter for a run of one token, sharing with the idle main
  helpers). Cite it as kv_cache.hpp:NN from the head.
- callers (context, cite the head): ingest/src/TronCpp.hs emits the main-side
  save_k(..., 0, n_workers) in run() and the helper-side save_k(...,
  worker_ix, n_workers) in run_main_help at the same statement position
  (AttentionStmt of runHelperStatement); h/tron/kernels/amx_attn_iface.hpp
  comment; tests t_k_vnni_layout.cpp (the block-save case: 4 blocks and 38
  masks against store_row) and t_llama_unit.cpp (the save_k case: the
  three-thread section, a helper that starts 20 ms late).

It does NOT contain (these land in PR 4959; never draw them as present):
Note [Row-major tail block], row_major_row / store_row_major / load_row_major,
block_to_vnni / block_to_rows, k_rows_saved_ / k_vnni_blocks_ and their bit
helpers (block_bit, offset_bit, BLOCKS_PER_PAGE_MASK_0XF, PANEL_ROWS_4),
note_k_row_saved / note_k_block_saved, k_block_to_vnni, k_forget_row,
pending_k_blocks_ / convert_pending_k_blocks, k_row_if_row_major,
k_layout_dense, the deb preset change. In PR 4958 a partial run of 2..16
tokens IS a (masked) block save and a run of one token IS a scatter
(set_k_row): the absent lanes of a partial block are simply not written. When
a diagram needs to say something is future work, name PR 4959 in a grey
context box, never as an existing function.

What PR 4958 inherits from PR 4956 / 4957 and may draw as context (grey or in
its concept colour, cited from the head): k_vnni_tensor / k_vnni_view, the
index map k_vnni::index, store_row / load_row / copy_token, the pair rows and
panels, page::set_k_row / get_k_row / k_packed, k_vnni::qk_group, the AMX
kernel qk_vnni_128x4 (PR 4957), the attention workers' pending sections, the
generated plugin's run() / run_main_help.

## Files

- `svg_helpers.py`: primitives. `C` = the colour tokens. `rect`, `text`,
  `lines`, `arrow` (+ `marker_defs`), `card_arrow` (arrow with a how-many
  label), `label_box` (title + sub-lines + citation), `fn_cell` (function
  name + ONE-line description + citation + tag), `cite`, `bit_row`,
  `legend_chip`, `lane`, `work_block`, `figure`, `text_width`.
- `difflib_units.py`: the diff parser (code excerpts; not used by figures).
  WT = ~/workspace/ai-runs/tron-split-pr3, BASE 26b86a279a, HEAD b39765ec29.
  `python3 difflib_units.py h/tron/models/model.hpp` dumps the added runs and
  deletion anchors (also saved in facts/<basename>.runs.txt).
- `page_common.py`: the page skeleton; `build(spec)`. Its LEGEND is the
  global colour and font scheme of the three pages: use only the concepts it
  lists.
- `spec_builder.py`: builds a page spec from `units_<key>.json` and the
  figure modules. Keys: `model` (h/tron/models/model.hpp), `k_vnni`
  (h/tron/tensor/k_vnni.hpp), `common` (h/tron/models/common.hpp).
  Output: PR3879/new-PRs/split-4424/diagramming-code-changes-PR4958-<name>.html.
- `units_<key>.json`: the page spec (copy the shape of
  exec/pr4956-diagrams-20261015/units_kv_cache.json: file, short[3],
  base_intro, changes_intro, trivial_intro, trivial_bullets, method, base[],
  units[] (id, title, kind, ranges, lead[], base), trivial[] (id, title,
  ranges, what), glossary[[term, meaning], ...]).
- `figs/base_<key>.py`: the base diagrams of one page. Exposes `b1()`,
  `b2()`, ... (each returns a figure's HTML) and the WORKED EXAMPLE constants
  and any building-block functions the change diagrams reuse (import them).
  A base figure may live in its own module `figs/base_<key>_<name>.py`
  exposing `<name>()`.
- `figs/d_<key>_<unit id>.py`: ONE change diagram per file. Exposes `fig()`
  (or `figs()` returning a list when a unit needs two) and a module-level
  string `BASE = "Updates B2: ..."` (which base diagram the unit's diagram
  updates, and how, one sentence). Never edit another unit's file.
- `render_one.py`: renders every figure of one module to `png/<id>.png`
  (run it, then LOOK at the PNG with the Read tool before you finish).
- `check_legend.py figs/<module>.py`: the per-figure scheme check.
- `check_page.py <page.html>`: the structural checks of a built page.
- Reusable earlier figures (adapt, re-derive every line number): the PR 4424
  set exec/pr4424-diagrams-20261009/figs/ (base_model.py: B1 window data
  model, B2 function model, B3 sequencing of one window, B4 wall-clock lanes,
  B5 decision model; d_model_m0..m7; d_k_vnni_k5 (transpose), k7
  (store_block)) and the PR 4956 set exec/pr4956-diagrams-20261015/figs/
  (base_k_vnni.py: the plane, panels, index map; base_kv_cache.py building
  blocks plane_strip, panel_grid, rm_rows, caller_cell, ops_cell, nx_box).
  The PR 4424 modules carry PR 4424 line numbers and PR 4959 concepts
  (pending list, row bits): strip those.

## Figure ids and sizes

- Figure id = `<key>-<name>`: `model-b1`, `k_vnni-d3`, `common-d1a`.
  Ids are the SVG `id` and the marker-id prefix: unique per page.
- Base diagrams: viewBox width 1000 (height as needed, at most ~800).
- Change diagrams sit in a half-width column beside the code: viewBox width
  640 to 720, height as needed (at most ~900; split into two figures if more).
- Font sizes: titles 12-13, labels 10-11, sub-labels 9-9.5, citations 8.5.
  Nothing below 8.5. Monospace for identifiers, sans for prose.

## What every figure must have

1. **Names from the code only.** A box label is an identifier
   (`k_store_window`, `unit_start`, `store_block`, `present`) or a phrase
   quoted from a comment. No invented shorthand, no abbreviations the code
   does not use.
2. **A citation on every box**: `cite(x, y, 'model.hpp:3104')` in the
   lower-right corner (or `ref=` of `label_box` / `fn_cell`), AND the same
   list passed to `figure(..., boxes=[(label, source), ...])` so the page can
   print "Boxes and their sources". Source = the line or Note that DEFINES
   the box. Line numbers are HEAD line numbers of PR 4958 (b39765ec29):
   verify each one with `git -C ~/workspace/ai-runs/tron-split-pr3 show
   b39765ec29:<path>`. A bare `k_vnni.hpp:NN` means h/tron/tensor/k_vnni.hpp;
   `kernels/k_vnni.hpp:NN` is the reader; `common.hpp:NN` is
   h/tron/models/common.hpp; `TronCpp.hs:NN` the code generator.
3. **Every function cell carries a one-line description** of what the
   function does (`fn_cell(..., desc=...)`), from its comment.
4. **Every arrow between data-model boxes is labelled with how many**
   (`card_arrow(..., label='1 window -> n_units units')`). The expression
   must come from the code (unit_start has max_minibatch_size + 1 entries,
   helper_windows has max_shared_workers = 128 entries, one block holds
   BLOCK_TOKENS_16 lanes, a panel has STEP_PAIRS_16 pair rows of
   LINE_BYTES_64, a plane has N_PANELS_16 panels).
5. **Colours = concepts** (see page_common.LEGEND and `svg_helpers.LEGEND`):
   VNNI blue (`vnni`, `vnni_solid`), row-major orange (`rm`, `rm_solid`: a
   native source row, the K buffer ks, a row-major slot), empty / absent lane
   grey dashed (`empty`), the present mask green (`present`), work units and
   window counters grey-blue (`unit`), the attention side that waits for the
   store violet (`q`), hardware attention yellow (`hw`, context only), the
   worked example's cell (`hi`), "does not exist" (`deleted`), before / removed
   red dashed (`gone`), the critical path thick solid red (`crit`), waiting
   ink dashed (`idle`), context grey (`ctx`), plain boxes (`box`), lanes and
   frames (`lane`), arrows (`arrow`, `arrow_muted`), fonts (`font_mono`,
   `font_sans`, `font_cite`, `font_tag` / `font_tag_changed`). Do NOT use
   `pend`, `pend_solid`, `rows`, `blk`, `live`, `eagle`: those concepts are not
   in PR 4958. Threads are LANES or bracketed names `[main]`, `[helper 1]`,
   never colours.
6. **A caption** (1-3 plain-English sentences: what the figure shows and
   what to look at) and, for change diagrams, which base diagram it updates
   and how (the caption starts with "Updates B2: ...").
7. **The worked example** of the page (below) reused wherever a concrete
   instance helps. Say "worked example" in the caption when used.
8. **Removed/old state** is drawn in `C['gone']` (red) with a dashed outline
   and the word "removed" or "before"; new state is marked "new" in
   `C['new']` where the figure contrasts before and after.

## Worked example (the same on all three pages)

- One prefill pass, layer 5 (storage slot 5), a generated plugin with
  n_workers = 3 (main = worker_ix 0, helpers worker_ix 1 and 2), one user
  with 41 items (q_batch->items = token jobs 0..40), all with
  token_jobs_do_kv set, at page 7 offsets 0..40. k_store_shared is true
  (layout on, 1 < 3 <= 128, 41 > 16). k_store_cut_units gives n_units = 3:
  unit_start = [0, 16, 32, 41]: unit 0 = block 0 (offsets 0..15), unit 1 =
  block 1 (16..31), unit 2 = block 2 (32..40, 9 tokens). The claim order in
  the figures: main claims unit 0, helper 1 claims unit 1, helper 2 claims
  unit 2 (next_unit goes 0 -> 1 -> 2 -> 3; the 4th fetch_add of every thread
  returns >= 3 and ends its loop). This is window W = 1 of the pass for this
  layer (opened goes 0 -> 1; helper_windows[1] and [2] go 0 -> 1); finished
  goes 0 -> 2; main's join waits for finished == 2.
- Unit 0 and unit 1: n = 16 -> set_k_block with present = 0xffff: per KV
  head, per dimension step s, 16 loads of 64 bytes, transpose_16x16_epi32,
  16 full-line stores into panel (s, c). Unit 2: n = 9 -> set_k_block with
  present = 0x01ff (lanes 0..8 = offsets 32..40): 9 loads and 7 zero
  registers per step, 16 masked stores (mask 0x01ff) per step; lanes 9..15
  of block 2 are never written. A run of ONE token (a decode step: 8 users,
  8 items <= 16, not shared, n = 1 for every run) takes set_k_row ->
  store_row (4 scatters that write 4 bytes into each of the token's 64
  lines).
- Token 37 = block c = 2, lane t = 5. Dimension 70 = step s = 2, pair dp =
  3, j = 0. In store_block for step s = 2: r[5] is the 64-byte load of
  token 37's dimensions 64..95; after the transpose, dword lane 5 of r[3]
  holds dimensions 70 and 71; the store of pair row dp = 3 puts it at panel
  (2, 2) = #10, line 3, lane 5: element index k_vnni::index(37, 70) =
  (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = 5226, byte offset 10452. The
  same place store_row would scatter to (store_block is bit-identical to
  set_k_row per present token: kv_cache.hpp set_k_block comment).
- The timing numbers a figure may quote: the Note's measurement (model.hpp
  Note [Shared block save]: 0.86 ms per layer, 105 ns per (token, KV head)
  row for the per-token store on main alone, qwen3-4b, 8 users, prompt
  1024, 128 tokens of each user per pass, 2026-09-14) and the join watchdog
  (k_join_timeout_s = 120 s, a clock read every k_join_clock_spins = 2^20
  pause loops). A wall-clock-lanes figure that draws the shared store
  shorter than the serial one must say "schematic, not to scale" unless it
  quotes a measured number with its source (the PR body of #4958: 80 us at
  tp2 for the block save shared with the helpers, same model and settings,
  2026-09-14; label it "PR #4958 body, Background").

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
  arrow glyph, "x" not a multiplication sign, "..." not an ellipsis glyph,
  "us" not the micro sign).
- `figure()` escapes nothing inside `body`; `text()` escapes its string.
- Nothing may overlap: after rendering, look for clipped text, text on
  lines, boxes over boxes. Fix and re-render until clean.
- Line numbers of the PR 4424 / PR 4956 modules you adapt are STALE.
  Re-derive every number from the PR 4958 head b39765ec29.
- check_page.py rule 5 looks for the box label's identifiers within +-3
  lines of the cited range: cite the DEFINING line (the declaration or the
  comment that names the concept), not a use site.

## How to check

```
cd /home/jhan/workspace/intel-AMX/exec/pr4958-diagrams-20261016
python3 render_one.py figs/base_model.py         # -> png/model-b1.png ...
python3 render_one.py figs/d_model_m3.py         # -> png/model-d3.png
python3 check_legend.py --show figs/<module>.py  # 0 problems
python3 spec_builder.py <key>                    # builds the page (asserts coverage)
python3 check_page.py <built page>               # 0 problems
python3 check_legend.py <built page>             # 0 problems
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
