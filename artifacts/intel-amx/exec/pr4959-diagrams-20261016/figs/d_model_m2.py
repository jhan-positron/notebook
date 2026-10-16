"""Change diagram of unit m2 (model.hpp page of PR 4959): store_k_block stores a
whole block as one VNNI block save and any shorter run row by row. Head lines
3229-3236 and 3294-3335.
"""
from svg_helpers import C, arrow, block_cell, cite, figure, lines, marker_defs, rect, text
from base_model import block_state_box, fit, note_box, stmt_row

BASE = ("Updates B5: opens B5's first decision. The run loop (context) ends with n and "
        "present; the decision n < k_store_block replaces the base's n == k_scatter_run_len; "
        "the per-row path calls set_k_row per (token, KV head) and lets the page pick the "
        "layout; the whole-block path asserts the full mask, calls set_k_block per KV head "
        "without a mask and publishes the block once with note_k_block_saved. The base's "
        "scatter branch and masked partial block save are drawn removed.")

W = 700


def fig():
    fid = "model-d2"
    o = [marker_defs(fid, {"ink": C["ink"], "gone": C["gone"]})]
    boxes = []
    o.append(text(20, 18, "store_k_block, the VNNI slot branch: one run of block c of page pg", 12,
                  weight=700))
    o.append(note_box(20, 26, 660, 48, "the run loop (unchanged context)",
                      ["consecutive items of block c of this page with distinct offsets, at most 16; "
                       "n = the run length,",
                       "present = the mask of its lanes, run_ix[i] / run_t[i] = the item and the lane "
                       "of row i"],
                      "model.hpp:3276-3296", size=8.5))
    boxes.append(("the run loop (n, present, run_ix, run_t)", "model.hpp:3276-3296"))
    # decision
    dy = 90
    o.append(rect(200, dy, 300, 44, "#fff", C["ink"], 1.6, 10))
    o.append(text(350, dy + 17, "if (n < k_store_block)", 11, "middle", True, weight=700))
    o.append(text(350, dy + 32, "a run shorter than 16 tokens?", 9, "middle"))
    o.append(cite(494, dy + 40, "model.hpp:3297"))
    boxes.append(("n < k_store_block", "model.hpp:3297"))
    o.append(arrow(fid, "ink", [(350, 74), (350, dy - 2)], C["ink"]))
    o.append(text(356, 84, "once per run", 8.5, fill=C["muted"]))
    # yes path
    yx, yy = 20, 160
    o.append(text(yx, yy - 8, "yes (1..15 tokens): row by row", 9.5, weight=600))
    o.append(arrow(fid, "ink", [(260, dy + 44), (260, yy - 2)], C["ink"]))
    o.append(rect(yx, yy, 320, 150, C["rm_fill"], C["rm"], 1.4, 5))
    yl = ["for i in 0..n-1:  j = c * k_store_block + run_t[i]",
          "  for kv_head in 0..n_kv_heads-1:",
          "    kout = row_of(run_ix[i], kv_head)",
          "    bf16: set_k_row(slot, kv_head, j, k_source_row(kout))",
          "    other types: convert into conv[0] first, then set_k_row",
          "",
          "set_k_row decides the layout from the block's bit:",
          "  block bit clear -> store_row_major (4 whole lines)",
          "  block bit set (a row saved again) -> store_row (scatter)",
          "no bit is set here: the recording is save_k_impl's (M3)"]
    for s in yl:
        fit(s, 8.5, 304, True, "d2 yes")
    o.append(lines(yx + 8, yy + 16, yl, 8.5, 12, mono=True))
    o.append(text(yx + 8, yy + 143, "changed", 9, fill=C["muted"], weight=700))
    o.append(cite(yx + 316, yy + 146, "model.hpp:3298-3315; kv_cache.hpp:2291-2301"))
    boxes.append(("the per-row path (set_k_row per token and KV head)", "model.hpp:3298-3315"))
    boxes.append(("set_k_row decides the layout (k_block_is_vnni)", "kv_cache.hpp:2291-2301"))
    # no path
    nx, ny = 360, 160
    o.append(text(680, ny - 8, "no (n == 16): the whole block", 9.5, "end", weight=600))
    o.append(arrow(fid, "ink", [(440, dy + 44), (440, ny - 2)], C["ink"]))
    o.append(rect(nx, ny, 320, 150, C["vnni_fill"], C["vnni"], 1.4, 5))
    nl = ["TRON_ASSERT(present == k_vnni::FULL_BLOCK_0XFFFF,",
          "  \"a run of 16 tokens must cover its block\");",
          "for kv_head in 0..n_kv_heads-1:",
          "  rows[run_t[i]] = the 16 native row pointers",
          "    (bf16: kout.data; other types: conv[i])",
          "  set_k_block(slot, kv_head, c, rows)   // no mask",
          "    -> store_block(plane, c, FULL_BLOCK_0XFFFF, rows)",
          "note_k_block_saved(slot, c)   // once, after the last",
          "  KV head: the 16 row bits and the block bit; any thread",
          "  of the window may run this (its unit owns the block)"]
    for s in nl:
        fit(s, 8.5, 304, True, "d2 no")
    o.append(lines(nx + 8, ny + 16, nl, 8.5, 12, mono=True))
    o.append(text(nx + 8, ny + 143, "changed", 9, fill=C["muted"], weight=700))
    o.append(cite(nx + 316, ny + 146, "model.hpp:3317-3333; kv_cache.hpp:2321, 2242"))
    boxes.append(("the whole-block path (set_k_block without a mask, note_k_block_saved)",
                  "model.hpp:3317-3333"))
    boxes.append(("set_k_block / note_k_block_saved", "kv_cache.hpp:2309-2328; 2240-2247"))
    # results
    ry = 330
    o.append(block_state_box(yx, ry, 150, 56, "rm", "row-major rows",
                             ["unit 2 of the prefill: 9", "rows (32..40), bits later"],
                             "model.hpp:3297"))
    boxes.append(("row-major rows (worked example unit 2)", "model.hpp:3297-3315"))
    o.append(block_state_box(yx + 170, ry, 150, 56, "vnni", "a row saved again",
                             ["the block was converted:", "store_row, bit stays set"],
                             "kv_cache.hpp:2297-2298"))
    boxes.append(("a row saved again (store_row into a converted block)", "kv_cache.hpp:2297-2298"))
    o.append(block_state_box(nx, ry, 320, 56, "vnni", "converted: VNNI layout",
                             ["units 0 and 1 of the prefill: 16 rows each, the 16 row bits",
                              "and the block bit set at once (bits 0..31, blocks 0b0011)"],
                             "model.hpp:3333"))
    boxes.append(("converted: VNNI layout (worked example units 0 and 1)", "model.hpp:3316-3333"))
    o.append(arrow(fid, "ink", [(95, yy + 150), (95, ry - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(265, yy + 150), (265, ry - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(520, ny + 150), (520, ry - 2)], C["ink"]))
    # removed
    gy = ry + 76
    o.append(text(20, gy - 6, "the base's two branches, removed", 10, weight=700, fill=C["gone"]))
    o.append(rect(20, gy, 320, 56, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(28, gy + 15, "if (n == k_scatter_run_len)", 9.5, mono=True, weight=600,
                  fill=C["gone"]))
    o.append(lines(28, gy + 28, ["only a run of ONE token went row by row, and that",
                                 "row went to store_row (a 4-scatter write)"], 8.5, 10.5))
    o.append(text(28, gy + 52, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(336, gy + 52, "base model.hpp:3260"))
    boxes.append(("if (n == k_scatter_run_len) (removed)", "base model.hpp:3260 (head 3297 reads n < k_store_block)"))
    o.append(rect(360, gy, 320, 56, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(368, gy + 15, "set_k_block(slot, kv_head, c, present, rows)", 9.5, mono=True,
                  weight=600, fill=C["gone"]))
    o.append(lines(368, gy + 28, ["a run of 2..16 tokens was a block save masked to its",
                                  "lanes; the absent lanes stayed unwritten"], 8.5, 10.5))
    o.append(text(368, gy + 52, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(676, gy + 52, "base model.hpp:3288"))
    boxes.append(("set_k_block with a present mask (removed)",
                  "base model.hpp:3288; head kv_cache.hpp:2321-2328 takes no mask"))
    H = gy + 70
    cap = ("Updates B5: the first decision of B5 opened to its code. A run of 16 takes the "
           "whole-block path (the assert, set_k_block per KV head without a mask, one "
           "note_k_block_saved after the last head); every shorter run takes the per-row "
           "path, where set_k_row chooses store_row_major or store_row from the block's "
           "bit. In the worked example, units 0 and 1 of the prefill take the block path "
           "and unit 2 (9 tokens) the row path. The base's one-token scatter branch and "
           "its masked partial block save are removed.")
    legend = [
        ("box", "white box, ink outline: the decision (bold monospace)"),
        ("ctx", "grey note: the unchanged run loop"),
        ("rm", "orange: the per-row path and its result, row-major rows"),
        ("vnni", "blue: the whole-block path and its result, converted: VNNI layout; a row saved again"),
        ("gone", "red dashed: the base's branches this PR removes"),
        ("arrow", "ink arrow: a branch of the decision, a path -> its block state"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag_changed", "grey 'changed' = the path is changed by this PR; red 'removed' = removed"),
    ]
    return figure(fid, W, H, "store_k_block: the whole-block decision and its two paths",
                  "".join(o), cap, boxes=boxes, legend=legend)
