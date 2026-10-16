# Drawing conventions for the PR 4959 diagram pages

Copied from exec/pr4956-diagrams-20261015/STYLE.md (the PR 4956 set) and cut
to what PR 4959 (the fourth and last PR of the split of PR 4424: "Keep short
K writes row-major; enable VNNI K in the deb preset") contains. Three pages,
one scheme. Read this whole file before drawing. Every figure is a Python
function that returns the HTML of one `<figure>` (inline SVG + caption + box
register), built only from `svg_helpers.py`.

## What PR 4959 contains (and what it does NOT)

PR 4959 = branch jhan-vnnik-4-tail-block, head 6b081187e1, base b39765ec29
(= the head of PR 4958, branch jhan-vnnik-3-shared-save). The worktree
~/workspace/ai-runs/tron-split-pr4 is at the head. Non-test source changes:
- h/tron/tensor/k_vnni.hpp (+116/-5): the constants PANEL_ROWS_4 and
  BLOCKS_PER_PAGE_MASK_0XF, the bit helpers block_bit(c) and
  offset_bit(offset), two static_asserts; Note [Row-major tail block] (a
  block holds its rows row-major inside its own 4 KiB until all 16 rows are
  saved: token t of block c lives in panel (t / 4, c), row t % 4, 256 bytes);
  row_major_row (the typed row view of a token inside a row-major block);
  store_row_major / load_row_major (one memcpy of Cols bf16 = 4 whole lines);
  block_to_vnni (16 load_row_major onto the stack, then store_block with
  FULL_BLOCK_0XFFFF) and block_to_rows (16 load_row onto the stack, then 16
  store_row_major); include <cstring>; the header comment.
- h/tron/models/kv_cache.hpp (+474/-50): a new paragraph of Note [K VNNI
  storage] (the two bit sets, who sets and drops them, why the conversion is
  at the forward end, why the transition is at 16 rows) and Note [Row-major
  blocks under hardware attention]; the consumer list rewritten (items 1-6);
  book::eagle_view_active; the page state copy (k_rows_saved_ /
  k_vnni_blocks_ copied with kv_saves_, head 2022-2027); page::k_vnni_blocks
  (the read view, one bit per block); k_storage_ref and k_storage_of;
  note_k_row_saved (returns true when the row's block now has 16 rows and is
  not converted) and note_k_block_saved (16 row bits + the block bit after a
  whole-block save); k_block_to_vnni / k_block_to_vnni_at (convert every KV
  head, then set the block bit); set_k_row and get_k_row follow the block's
  layout (k_block_is_vnni ? store_row / load_row : store_row_major /
  load_row_major); set_k_block takes no present mask any more (whole blocks
  only, FULL_BLOCK_0XFFFF); k_row_if_row_major (the row pointer of a
  row-major block for the FPGA staging, an invalid view for a converted
  block); clear_kv_complete_at calls k_forget_row; the private state
  section: EAGLE_STORAGE_SLOTS_1, k_state_ix, k_block_bits, k_block_is_vnni,
  k_with_storage_geometry, k_storage_readable, k_forget_row (drop the bits at
  and above an offset in every storage slot; a converted block that keeps rows
  below the offset is converted back first when the storage is readable); the
  members k_rows_saved_[n_slots + 1] (uint64_t, one bit per page offset) and
  k_vnni_blocks_[n_slots + 1] (uint8_t, one bit per block); copy_storage_slot
  takes a k_storage_ref and carries the bits with the rows (whole page: owner
  assignment + src bits; any other range: block_to_rows on the touched
  converted destination blocks, token by token through row-major rows, then
  block_to_vnni on every block whose 16 bits are set); copy_from builds the
  pair for every active slot and the EAGLE storage.
- h/tron/models/model.hpp (+76/-12): convert_pending_k_blocks() called at
  the forward end after wait_for_coop_gof (head 1840-1843); the Note
  [Shared block save] item 1 rewritten; k_scatter_run_len REMOVED; the
  struct pending_k_block {pg, storage, block}, the vector pending_k_blocks_
  and convert_pending_k_blocks (k_block_to_vnni_at per entry, then clear);
  store_k_block: a run shorter than a block (n < k_store_block) goes row by
  row through set_k_row (set_k_row decides the layout), a run of 16 asserts
  present == FULL_BLOCK_0XFFFF, calls set_k_block (no mask) and then
  note_k_block_saved; save_k_impl: after the join, when
  !cached_operation_uses_hw(binding.operation), the row-recording loop calls
  note_k_row_saved per item and queues {&pg, pg.k_storage_of(slot), j /
  k_store_block} when it returns true.
- h/tron/models/self_attention.hpp (+74, not a target page): the third AMX
  gate k_layout_dense (page::k_vnni_blocks == BLOCKS_PER_PAGE_MASK_0XF);
  the loop fetches vnni_blocks and the plane at the first relevant token,
  marks live bits for the tokens of converted blocks and scores the tokens of
  row-major blocks with the dotters through row_major_row; qk_group runs when
  live != 0. Cite as self_attention.hpp:NN from the head.
- h/tron/scheduler/full.hpp (+10): page_info::k_head_fn returns the row
  pointer from k_row_if_row_major when valid, else gathers with get_k_row.
- h/tron/kernels/k_vnni.hpp (+7, comment), h/tron/kernels/amx_attn_iface.hpp
  (+14, comment), CMakePresets.json (TRON_K_VNNI ON in the deb preset),
  README.ci.md, config/test-benchmarks.json (4 cost rows).
- tests (context): t_k_vnni_layout.cpp (10 cases: the tail block round trip,
  the 16th-row transition, EAGLE's own state, forgetting a row, page append
  carrying the state, ...), t_llama_unit.cpp (the save_k case: two
  hardware-attention sections), t_heterogeneous_scheduler (the forward-path
  case), t_amx_dispatch_dtype.cpp.

It does NOT contain (never draw as present): a partial set_k_block with a
present mask (REMOVED here: draw it red dashed "removed" where the contrast
helps), k_scatter_run_len (removed), the scatter store_row for a run of one
token into an unconverted block (set_k_row now takes store_row_major there;
store_row is used only when the block is already converted: "a row saved
again"). The reader k_vnni::qk_group, the AMX kernel qk_vnni_128x4, the
shared window protocol (k_store_window, k_store_shared, k_store_cut_units,
the join), store_block, transpose_16x16_epi32, the typed plane and its views,
store_row / load_row / copy_token, set_k_row / get_k_row / k_packed are
inherited from PR 4956 / 4957 / 4958 and may be drawn as context (grey, or in
their concept colour), cited from the head 6b081187e1.

## Files

- `svg_helpers.py`: primitives. `C` = the colour tokens. `rect`, `text`,
  `lines`, `arrow` (+ `marker_defs`), `card_arrow` (arrow with a how-many
  label), `label_box` (title + sub-lines + citation), `fn_cell` (function
  name + ONE-line description + citation + tag), `cite`, `bit_row`,
  `block_cell` (a 16-token block by state: empty / rm / pend / vnni / hw),
  `legend_chip`, `lane`, `work_block`, `figure`, `text_width`.
- `difflib_units.py`: the diff parser (code excerpts; not used by figures).
  WT = ~/workspace/ai-runs/tron-split-pr4, BASE b39765ec29, HEAD 6b081187e1.
  `python3 difflib_units.py h/tron/models/kv_cache.hpp` dumps the added runs
  and deletion anchors (also saved in facts/<basename>.runs.txt).
- `page_common.py`: the page skeleton; `build(spec)`. Its LEGEND is the
  global colour and font scheme of the three pages: use only the concepts it
  lists.
- `spec_builder.py`: builds a page spec from `units_<key>.json` and the
  figure modules. Keys: `kv_cache` (h/tron/models/kv_cache.hpp), `k_vnni`
  (h/tron/tensor/k_vnni.hpp), `model` (h/tron/models/model.hpp).
  Output: PR3879/new-PRs/split-4424/diagramming-code-changes-PR4959-<name>.html.
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
  set exec/pr4424-diagrams-20261009/figs/ covered the same concepts
  (base_kv_cache.py: B1 data model with the two bit arrays, B2 one block two
  layouts, B3 function model, B4 the life of one block, B5 threads;
  d_kv_cache_c2 (the state), c3 (k_storage_ref), c4 (k_vnni_blocks), c5
  (note_k_row_saved), c6 (k_block_to_vnni), c7 (row accessors follow the
  layout), c9 (k_forget_row), c10 (page copies); base_k_vnni.py and
  d_k_vnni_k8 (Note [Row-major tail block], row_major_row), k9
  (block_to_vnni / block_to_rows); base_model.py and d_model_m1 (the pending
  list), m4 (store_k_block), m6 (the row-recording loop)). Those modules carry
  PR 4424 line numbers and PR 4424's older shapes (a partial block save with
  a mask was NOT in PR 4424 either; k_scatter_run_len was): re-read the PR
  4959 head for every fact. The PR 4956 set exec/pr4956-diagrams-20261015/figs/
  has the building blocks plane_strip, panel_grid, rm_rows, caller_cell,
  ops_cell, nx_box in base_kv_cache.py.

## Figure ids and sizes

- Figure id = `<key>-<name>`: `kv_cache-b1`, `k_vnni-d3`, `model-d2a`.
  Ids are the SVG `id` and the marker-id prefix: unique per page.
- Base diagrams: viewBox width 1000 (height as needed, at most ~800).
- Change diagrams sit in a half-width column beside the code: viewBox width
  640 to 720, height as needed (at most ~900; split into two figures if more).
- Font sizes: titles 12-13, labels 10-11, sub-labels 9-9.5, citations 8.5.
  Nothing below 8.5. Monospace for identifiers, sans for prose.

## What every figure must have

1. **Names from the code only.** A box label is an identifier
   (`k_rows_saved_`, `k_storage_ref`, `block_to_vnni`, `pending_k_blocks_`)
   or a phrase quoted from a comment ("complete, may wait": kv_cache.hpp
   Note [K VNNI storage] says "a complete block may wait for its
   conversion"). No invented shorthand. The block states are named the same
   on all three pages: "no row saved" / "row-major rows" / "complete, may
   wait" / "converted: VNNI layout" / "row-major, no bits (hardware
   attention)".
2. **A citation on every box**: `cite(x, y, 'kv_cache.hpp:2641')` in the
   lower-right corner (or `ref=` of `label_box` / `fn_cell`), AND the same
   list passed to `figure(..., boxes=[(label, source), ...])` so the page can
   print "Boxes and their sources". Source = the line or Note that DEFINES
   the box. Line numbers are HEAD line numbers of PR 4959 (6b081187e1):
   verify each one with `git -C ~/workspace/ai-runs/tron-split-pr4 show
   6b081187e1:<path>`. A bare `k_vnni.hpp:NN` means h/tron/tensor/k_vnni.hpp;
   `kernels/k_vnni.hpp:NN` is the reader.
3. **Every function cell carries a one-line description** of what the
   function does (`fn_cell(..., desc=...)`), from its comment.
4. **Every arrow between data-model boxes is labelled with how many**
   (`card_arrow(..., label='1 page -> n_slots + 1 state entries')`). The
   expression must come from the code (k_rows_saved_ has layout_t::n_slots +
   EAGLE_STORAGE_SLOTS_1 entries of 64 bits = page_size offsets; k_vnni_blocks_
   the same entries of TOKEN_BLOCKS_4 bits; a block holds BLOCK_TOKENS_16
   rows; a row-major block keeps PANEL_ROWS_4 rows of 256 bytes in each of its
   4 panels; block_to_vnni copies 16 rows of Cols bf16 = 4 KiB).
5. **Colours = concepts** (see page_common.LEGEND and `svg_helpers.LEGEND`):
   VNNI blue (`vnni`, `vnni_solid`), row-major orange (`rm`, `rm_solid`: the
   row-major tail block, a row-major slot), complete-may-wait vermillion
   dashed (`pend`; solid `pend_solid` = the conversion and the way back),
   k_rows_saved_ green (`rows`), k_vnni_blocks_ pink (`blk`), empty grey
   dashed (`empty`, `bit_clear`), hardware attention yellow (`hw`: a
   hardware-scored operation's blocks stay row-major, the FPGA staging path),
   EAGLE sky blue (`eagle`), the query side violet (`q`: the dotters, the live
   mask of qk_group, s_pages, the AMX gate k_layout_dense), work units of the
   shared window grey-blue (`unit`, context), the worked example's cell
   (`hi`), "does not exist" (`deleted`), before / removed red dashed (`gone`),
   context grey (`ctx`), plain boxes (`box`), lanes and frames (`lane`),
   arrows (`arrow`, `arrow_muted`), fonts (`font_mono`, `font_sans`,
   `font_cite`, `font_tag` / `font_tag_changed`). Do NOT use the `live` key
   (its green would collide with `rows`): the live mask of the reader is drawn
   on the query side (`q`). Do NOT use `crit` or `idle` unless the figure is a
   wall-clock-lanes figure. Threads are LANES or bracketed names, never
   colours.
6. **A caption** (1-3 plain-English sentences: what the figure shows and
   what to look at) and, for change diagrams, which base diagram it updates
   and how (the caption starts with "Updates B2: ...").
7. **The worked example** of the page (below) reused wherever a concrete
   instance helps. Say "worked example" in the caption when used.
8. **Removed/old state** is drawn in `C['gone']` (red) with a dashed outline
   and the word "removed" or "before"; new state is marked "new" in
   `C['new']` where the figure contrasts before and after.

## Worked example (the same on all three pages)

- Page 7, storage slot 5 (layer 5, state entry k_state_ix = 5, no EAGLE
  view), KV head 0, a VNNI slot (128-dimension head, TRON_K_VNNI on), CPU
  attention (cached_operation_uses_hw false unless the figure says
  "hardware attention").
- The prefill pass saved offsets 0..40 (41 tokens, the shared window of PR
  4958 with units [0,16) [16,32) [32,41)): units 0 and 1 were whole-block
  saves (set_k_block -> store_block, then note_k_block_saved: 16 row bits +
  the block bit each); unit 2 (offsets 32..40, 9 tokens, n < k_store_block)
  went row by row (set_k_row -> store_row_major: 4 whole lines per token into
  the row-major form of block 2); after the join note_k_row_saved set bits
  32..40 and returned false (block 2 incomplete). Then 5 decode steps saved
  offsets 41..45 one by one (set_k_row -> store_row_major, note_k_row_saved
  false). THE MOMENT DRAWN BY DEFAULT: after offset 45: k_rows_saved_[5] =
  bits 0..45 set (0x3fff_ffff_ffff), k_vnni_blocks_[5] = 0b0011; block 0 and
  block 1 "converted: VNNI layout"; block 2 "row-major rows" (offsets 32..45,
  14 of 16 rows, offsets 46 and 47 not saved); block 3 "no row saved".
- Token 37 = block c = 2, lane t = 5. In the row-major form it lives in
  panel (t / 4, c) = (1, 2) = #6, row t % 4 = 1: element offset
  row_major_row = (1 * 4 + 2) * 512 + 1 * 128 = 3200; dimension 70 at
  element 3270, byte 6540. After the conversion the same value sits at
  k_vnni::index(37, 70) = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = 5226,
  byte 10452 (panel (2, 2) = #10, pair row 3, lane 5). Print both numbers.
- The transition: the decode step that saves offset 47 (the 16th row of
  block 2): set_k_row -> store_row_major (block 2 not converted yet);
  note_k_row_saved(slot 5, 47): before = bits 0..46, after = bits 0..47,
  (after & k_block_bits(2)) == k_block_bits(2) and block bit 2 clear ->
  true -> save_k pushes pending_k_block{&page 7, {offset slot 5, state_ix
  5}, block 2}. At the forward end (after run() joined its workers and
  wait_for_coop_gof drained the staging) convert_pending_k_blocks ->
  k_block_to_vnni_at -> block_to_vnni for every KV head (16 load_row_major
  onto the stack, store_block with FULL_BLOCK_0XFFFF) -> k_vnni_blocks_[5] =
  0b0111. A page is dense for the AMX kernel (k_layout_dense) only at
  0b1111.
- Scoring the page at the default moment (one query group of kv_mul = 4
  heads): the loop marks live bits for the relevant tokens of converted
  blocks (offsets 0..31 -> live = 0xffffffff) and scores the 14 row-major
  tokens 32..45 with the dotters through row_major_row (4 lines per token);
  qk_group scores the live tokens; k_layout_dense is false (0b0011 != 0xf),
  so the AMX kernel does not run on this page.
- Hardware attention (the same page in an FPGA-scored operation): the row
  recording loop is skipped; blocks 0 and 1 still have their bits (whole
  block saves record them); offsets 32..45 have no bit; block 2 stays
  row-major forever; the staging (page_info::k_head_fn) reads the row pointer
  from k_row_if_row_major (no copy); a tail token in block 2 is scored by the
  dotter, in blocks 0 or 1 by qk_group.
- Forgetting: a new token takes offset 37 (clear_kv_complete_at(37) ->
  k_forget_row(37)): c = 2, rows_below = bits 0..36, blocks_below = 0b0011,
  block_keeps_rows true (37 % 16 != 0). At the default moment block 2 is not
  converted: only the bits drop (rows 37..45 cleared; block bits stay 0b0011).
  After the transition (block 2 converted): block_to_rows on every KV head
  first (the storage is readable), then bits 2 and 3 of k_vnni_blocks_ drop.
- A page copy of 41 tokens from page 7 offsets 0..40 to page 9 offsets 0..40
  (copy_storage_slot, not a whole page): range = bits 0..40; new_saved =
  src bits 0..40; destination blocks 0..2 touched, none converted on an
  empty page 9; token by token: offsets 0..31 come from converted source
  blocks -> load_row into row_major_row(dst); offsets 32..40 come from the
  row-major block 2 -> store_row_major(dst, row_major_row(src)); then blocks
  0 and 1 of page 9 have 16 bits -> block_to_vnni -> new_blocks = 0b0011;
  block 2 of page 9 stays row-major with 9 rows. A copy of all 64 tokens is
  one owner assignment plus the source bits.
- EAGLE: with the EAGLE view active, slot 0 maps to state entry
  layout_t::n_slots and storage book.eagle_storage_offset(); k_storage_of
  returns that pair; the EAGLE storage keeps its own bits.
- Numbers a figure may quote: issue #4500's decode loss under FPGA attention
  (2.2 % at tp2, 9.7 % at tp4 for qwen3-4b, 2026-09-16: cite "issue #4500"),
  the Note's costs (4 lines per token row-major against 64 lines per VNNI
  column; 4 KiB read + 4 KiB written per block conversion; 8 KiB of plane
  traffic + 8 KiB stack round trip per block and KV head under hardware
  attention: kv_cache.hpp Notes), the conversion trace (3.7 to 4.2 us per
  block, once every 16 decode steps, 288 blocks per run: "PR #4959 body,
  Performance, trace pr4trace-20261015"). Label anything else "schematic".

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
  Re-derive every number from the PR 4959 head 6b081187e1.
- check_page.py rule 5 looks for the box label's identifiers within +-3
  lines of the cited range: cite the DEFINING line (the declaration or the
  comment that names the concept), not a use site.

## How to check

```
cd /home/jhan/workspace/intel-AMX/exec/pr4959-diagrams-20261016
python3 render_one.py figs/base_kv_cache.py      # -> png/kv_cache-b1.png ...
python3 render_one.py figs/d_kv_cache_c3.py      # -> png/kv_cache-d3.png
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
