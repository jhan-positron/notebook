"""Change diagram D8 of the PR 4424 page for h/tron/models/kv_cache.hpp:
unit c8, "set_k_block: a whole 16-token block stored in the VNNI layout"
(head lines 2265-2284, new).

Every label and citation comes from facts/kv_cache.json (kv_cache-data-31,
kv_cache-data-45, kv_cache-function-10, kv_cache-function-15, kv_cache-seq-5,
kv_cache-rule-3) or from the head files themselves. Line numbers are head
line numbers of kv_cache.hpp unless another file is named. The worked example
is the page's shared save_k window: unit items[0,16) = user A, page 7,
block 0 (a run of 16 tokens that covers its block).
"""
from svg_helpers import (C, arrow, bit_row, block_cell, card_arrow, cite,
                         figure, fn_cell, label_box, lines, marker_defs, rect,
                         text, text_width)
from base_kv_cache import WINDOW_EXAMPLE, caller_cell, fit, state_box

BASE = ("Updates B2 and B4: the arc over the top of B4 (the whole-block save) is drawn in "
        "full: 16 native rows enter set_k_block once per KV head and leave as 64 "
        "whole-line stores into the four panels of block c, then note_k_block_saved "
        "publishes the bits, so the block goes from empty straight to converted; "
        "section A redraws the four panels of block 0 of B2 (part a), section C the "
        "caller and the bits (part b).")

# the worked example unit: (0, 16, "page 7, block 0", "set_k_block (whole block)")
UNIT_A, UNIT_B, UNIT_WHERE, UNIT_HOW = WINDOW_EXAMPLE["units"][0]
assert UNIT_A == 0 and UNIT_B == 16 and UNIT_HOW.startswith("set_k_block")
BLOCK_C = 0          # block 0 of page 7 (offsets 0..15)
HI_T = 5             # the token column marked in section B (as in B2: t = 5)


def line_grid(x, y, cw, ch, whole, hi_col=None):
    """One panel as 16 pair rows (lines of 64 B) x 16 dwords.
    whole=True: each line is one solid bar (one whole-line store);
    whole=False: 16 dword cells per line, column hi_col solid (one token's
    4-byte slot in every line)."""
    o = []
    for r in range(16):
        ry = y + r * (ch + 1)
        if whole:
            o.append(rect(x, ry, 16 * cw, ch, C["vnni_fill"], C["vnni"], 0.8, 0))
        else:
            for c in range(16):
                f = C["vnni"] if c == hi_col else "#fff"
                o.append(rect(x + c * cw, ry, cw, ch, f, C["vnni"], 0.5, 0))
    o.append(rect(x, y, 16 * cw, 16 * (ch + 1) - 1, "none", C["ink"], 0.8, 0))
    # row labels (pair row 0 and 15) and dword labels (0, hi, 15)
    o.append(text(x - 4, y + ch, "pair row 0", 8.5, "end", fill=C["muted"]))
    o.append(text(x - 4, y + 15 * (ch + 1) + ch, "15", 8.5, "end", fill=C["muted"]))
    o.append(text(x - 4, y - 4, "dword", 8.5, "end", fill=C["muted"]))
    for c in (0, 15) + ((hi_col,) if hi_col is not None else ()):
        o.append(text(x + c * cw + cw / 2, y - 4, str(c), 8.5, "middle", True,
                      fill=C["ink"] if c == hi_col else C["muted"]))
    return "".join(o)


def fig_a():
    fid = "kv_cache-d8a"
    W, H = 700, 590
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    # ---- header: the worked example -------------------------------------------
    h1 = (f"worked example (the shared save_k window): unit items[{UNIT_A},{UNIT_B}) "
          f"= user A, {UNIT_WHERE}, offsets {16 * BLOCK_C}..{16 * BLOCK_C + 15}:")
    h2 = "a run of 16 tokens that covers its block, stored by [any thread of the shared window]"
    fit(h1, 9.5, 668, False, "header 1")
    fit(h2, 9.5, 668, False, "header 2")
    o.append(text(16, 14, h1, 9.5, fill=C["muted"]))
    o.append(text(16, 26, h2, 9.5, fill=C["muted"]))

    # ---- A: one set_k_block call -------------------------------------------------
    ta = (f"A. one set_k_block call: 16 native rows in, the four panels of block "
          f"{BLOCK_C} out (one KV head)")
    fit(ta, 11, 668, False, "title A")
    o.append(text(16, 46, ta, 11, weight=700))
    # the 16 row pointers (native rows, row-major orange)
    sx, sw, sy, ch = 16, 160, 68, 11
    o.append(text(sx, 62, "rows[k_vnni::BLOCK_TOKENS_16]", 9.5, mono=True, fill=C["rm"],
                  weight=700))
    for t in range(16):
        ry = sy + t * (ch + 1)
        o.append(rect(sx, ry, sw, ch, C["rm_fill"], C["rm"], 0.8, 1))
        o.append(text(sx + 4, ry + 8.5, f"rows[{t}]: offset {16 * BLOCK_C + t}", 8.5,
                      mono=True))
    o.append(cite(sx + sw, 272, "kv_cache.hpp:2267-2271, 2280"))
    boxes.append(("rows[k_vnni::BLOCK_TOKENS_16] (the 16 native source rows)",
                  "kv_cache.hpp:2267-2271, 2280; filled by store_k_block at "
                  "model.hpp:3326-3337"))
    # the function cell
    fx, fw, fy, fh = 236, 230, 116, 72
    desc = ["stores the 16 rows of block c of one", "KV head at once in the VNNI layout",
            "(VNNI slots only); sets no bit"]
    for d in desc:
        fit(d, 9.5, fw - 16, False, "desc set_k_block")
    o.append(fn_cell(fx, fy, fw, fh, "set_k_block", desc, "kv_cache.hpp:2273-2284", "new"))
    boxes.append(("set_k_block", "kv_cache.hpp:2273-2284 (comment 2265-2272)"))
    # rows -> set_k_block
    o.append(card_arrow(fid, "rm", [(sx + sw + 2, 152), (fx - 2, 152)], C["rm"],
                        "16 rows in", label_dy=-6, size=9))
    o.append(text((sx + sw + fx) / 2, 166, "256 B each", 8.5, "middle", fill=C["rm"]))
    # the body of set_k_block
    bx, by, bw, bh = fx, 196, fw, 88
    o.append(rect(bx, by, bw, bh, C["soft"], C["line"], 1, 4))
    body = ["TRON_ASSERT_LT(c, page_size /",
            "    k_vnni::BLOCK_TOKENS_16)",
            "store_block(kv_block<geometry>",
            "    (slot, kv_head).k.as_view(),",
            "    c, k_vnni::FULL_BLOCK_0XFFFF, rows)"]
    for s in body:
        fit(s, 8.5, bw - 16, True, "body")
    o.append(lines(bx + 8, by + 14, body, 8.5, 11, mono=True))
    o.append(text(bx + 8, by + 14 + 5 * 11, "(page_size / BLOCK_TOKENS_16 = 4 blocks)",
                  8.5, fill=C["muted"]))
    o.append(cite(bx + bw - 4, by + bh - 4, "kv_cache.hpp:2281-2283"))
    boxes.append(("the body: TRON_ASSERT_LT(c, ...) and store_block(..., "
                  "k_vnni::FULL_BLOCK_0XFFFF, rows)", "kv_cache.hpp:2281-2283; the "
                  "4 blocks per page: kv_cache.hpp:2196, 2281; tensor/k_vnni.hpp:69"))
    # the four panels of block c (VNNI blue; the panels of B2)
    px, pw, pch, pgap = 592, 92, 44, 4
    o.append(text(px + pw, 62, f"block {BLOCK_C}: panels (s, {BLOCK_C})", 9.5, "end", True,
                  fill=C["vnni"], weight=700))
    for s in range(4):
        py = sy + s * (pch + pgap)
        o.append(block_cell(px, py, pw, pch, "vnni"))
        o.append(text(px + pw / 2, py + 18, f"panel ({s},{BLOCK_C})", 9.5, "middle", True))
        o.append(text(px + pw / 2, py + 34, f"#{4 * s + BLOCK_C}", 10, "middle", True,
                      fill=C["muted"]))
    o.append(cite(px + pw, 272, "tensor/k_vnni.hpp:437-445"))
    boxes.append((f"block {BLOCK_C}: panels (s, {BLOCK_C}) = #0, #4, #8, #12",
                  "Note [Row-major tail block] (tensor/k_vnni.hpp:437-445); panel (s, c): "
                  "tensor/k_vnni.hpp:29-30"))
    # set_k_block -> the panels
    mx = (fx + fw + px) / 2
    o.append(arrow(fid, "vnni", [(fx + fw + 2, 152), (px - 2, 152)], C["vnni"], 1.4))
    o.append(lines(mx, 134, ["1 call -> 64 stores", "of whole 64 B lines"], 9, 11, "middle",
                   fill=C["vnni"], weight=600))
    o.append(text(mx, 166, "4 KiB in all", 8.5, "middle", fill=C["muted"]))
    o.append(lines(mx, 178, ["tensor/k_vnni.hpp:", "390-393, 410-413"], 8.5, 10, "middle",
                   True, fill=C["cite"]))
    # notes of section A
    na = [
        "rows[t] = the 128 bf16 (256 B) of page offset c * 16 + t, a native source row in "
        "dimension order, not",
        "packed storage [kv_cache.hpp:2267-2271]; the caller fills rows[run_t[i]] from its K "
        "buffer [model.hpp:3326-3337]",
        "the plane is kv_block<geometry>(slot, kv_head).k.as_view() [kv_cache.hpp:2282]; "
        "block c owns panels (s, c),",
        "s = 0..3, 4 KiB apart [tensor/k_vnni.hpp:437-445]; bit-identical to set_k_row per "
        "token of a complete block [2268-2269]",
    ]
    for s in na:
        fit(s, 9, 668, False, "notes A")
    o.append(lines(16, 300, na, 9, 11))

    # ---- B: the write pattern ------------------------------------------------------
    tb = ("B. the same 4 KiB, two write patterns: one panel (s, c) = 16 pair rows of "
          "64 B = 16 dwords each")
    fit(tb, 11, 668, False, "title B")
    o.append(text(16, 358, tb, 11, weight=700))
    gw, gh = 11, 6
    # left: store_block
    lx = 16
    o.append(text(lx, 376, "store_block (set_k_block): whole lines", 10, fill=C["vnni"],
                  weight=700))
    o.append(text(lx, 388, "per step s: 16 row loads, transpose in registers, 16 stores",
                  8.5, fill=C["muted"]))
    gx, gy = lx + 54, 404
    o.append(line_grid(gx, gy, gw, gh, True))
    o.append(lines(gx + 16 * gw + 6, gy + 56, ["1 store per", "line, 64 B"], 8.5, 10.5))
    lb = ["16 per panel x DIM_STEPS_4 panels = 64 whole-line stores",
          "_mm512_storeu_si512; present == FULL_BLOCK_0XFFFF, unmasked"]
    for s in lb:
        fit(s, 9, 320, False, "B left")
    o.append(lines(lx, 528, lb, 9, 11))
    o.append(cite(lx, 552, "tensor/k_vnni.hpp:390-393, 410-413", "start"))
    boxes.append(("store_block: 64 stores of whole lines (one panel drawn)",
                  "tensor/k_vnni.hpp:382-420 (comment 390-393; the full-mask stores 410-413)"))
    # right: store_row per token
    rx = 364
    o.append(text(rx, 376, "store_row per token (set_k_row into a VNNI block)", 10,
                  weight=700))
    o.append(text(rx, 388, "per step s: one scatter of 16 dwords, 4 B into each of 16 lines",
                  8.5, fill=C["muted"]))
    gx2 = rx + 54
    o.append(line_grid(gx2, gy, gw, gh, False, HI_T))
    o.append(lines(gx2 + 16 * gw + 6, gy + 50, [f"token t = {HI_T}:", "4 B x 16 lines",
                                                 "per step"], 8.5, 10.5))
    rb = ["16 tokens x 4 steps = 64 scatters, each 4 B into 16 lines",
          "every one of the block's 64 lines receives 16 partial writes"]
    for s in rb:
        fit(s, 9, 320, False, "B right")
    o.append(lines(rx, 528, rb, 9, 11))
    o.append(cite(rx, 552, "tensor/k_vnni.hpp:344-362, 390-393", "start"))
    boxes.append(("store_row per token: 64 scatters, each 4 bytes into 16 lines "
                  "(one panel drawn)", "tensor/k_vnni.hpp:344-362 (store_row); 390-393"))
    same = ("the same 4 KiB is written; only the write pattern differs "
            "[kv_cache.hpp:2268-2270; tensor/k_vnni.hpp:392-393]")
    fit(same, 9.5, 668, False, "same")
    o.append(text(350, 572, same, 9.5, "middle", weight=600))

    cap = ("Updates B2 and B4 (part a): the arc over the top of B4 (the whole-block "
           f"save) is drawn in full for the worked example, unit items[{UNIT_A},{UNIT_B}) "
           "of the shared save_k window (user A, the first user of the window in the "
           "worked example of B1; page 7, block 0). Section A is one set_k_block call: "
           "the 16 native rows of block 0 (orange, 256 bytes each) enter and 64 "
           "whole-line stores leave into the block's four panels (blue, the panels of "
           "B2). Section B contrasts that write pattern with store_row per token. "
           "store_row writes the same 4 KiB as 64 scatters, each of 4 bytes into 16 "
           "lines. Part b is the caller and the bits.")
    legend = [
        ("rm", "orange (boxes and labels): rows[t], the 16 native source rows of block 0 "
               "that enter set_k_block, 256 B each"),
        ("vnni", "blue (boxes and labels): the four panels (s, 0) of block 0 in the VNNI "
                 "layout (section A), and one whole 64 B line stored at once (section B, "
                 "left)"),
        ("vnni_solid", "solid blue: the 4 B dword of token t = 5 in each of the 16 pair "
                       "rows (section B, right)"),
        ("white cell, blue outline: a 4 B dword of one of the other 15 tokens in a pair "
         "row (section B, right)", "#fff", C["vnni"], False, False),
        ("ink frame: the outline of one panel (s, c), 16 pair rows x 16 dwords (section B)",
         "none", C["ink"], False, False),
        ("box", "white box, ink outline: the function cell set_k_block; name in bold "
                "monospace, description in sans-serif"),
        ("ctx", "grey box, thin grey outline: the body of set_k_block: TRON_ASSERT_LT, then "
                "store_block with FULL_BLOCK_0XFFFF"),
        ("orange arrow: the 16 rows -> set_k_block (16 rows in)", "arrow", C["rm"]),
        ("blue arrow: set_k_block -> the four panels (1 call -> 64 whole-line stores)",
         "arrow", C["vnni"]),
        ("font_mono", "monospace = identifiers and values from the code: rows[t], "
                      "set_k_block, panel (s, c), the body of set_k_block"),
        ("font_sans", "sans-serif = prose: the worked example, descriptions, notes"),
        "font_cite",
        ("font_tag", "bold 'new' = set_k_block is added by this PR"),
    ]
    return figure(fid, W, H, "set_k_block (part a): one call, and the two write patterns "
                  "of the same 4 KiB", "".join(o), cap, boxes=boxes, legend=legend)


def fig_b():
    """Section C: the caller store_k_block, set_k_block per KV head, then the
    bits, and the B4 arc for the worked example."""
    fid = "kv_cache-d8b"
    W, H = 700, 300
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    h1 = (f"worked example (the shared save_k window): unit items[{UNIT_A},{UNIT_B}) "
          f"= user A, {UNIT_WHERE}, offsets {16 * BLOCK_C}..{16 * BLOCK_C + 15}:")
    h2 = "a run of 16 tokens that covers its block, stored by [any thread of the shared window]"
    o.append(text(16, 14, h1, 9.5, fill=C["muted"]))
    o.append(text(16, 26, h2, 9.5, fill=C["muted"]))
    tc = ("C. the caller store_k_block [any thread of the shared window]: set_k_block "
          "per KV head, then the bits")
    fit(tc, 11, 668, False, "title C")
    o.append(text(16, 40, tc, 11, weight=700))
    cx, cw = 16, 290
    ax = cx + 84
    # step 1: the caller
    c1 = ["store_k_block: a run of 16 tokens that covers",
          "its block [any thread of the shared window]:",
          "TRON_ASSERT(present == k_vnni::FULL_BLOCK_0XFFFF)"]
    o.append(caller_cell(cx, 54, cw, 56, c1, "model.hpp:3322-3324"))
    boxes.append(("store_k_block (caller): the whole-block branch",
                  "model.hpp:3232-3344; the branch 3321-3341; assert 3323-3324"))
    o.append(arrow(fid, "ink", [(ax, 112), (ax, 138)], C["ink"], 1.4))
    o.append(text(ax + 8, 129, "1 run -> n_kv_heads calls, 1 per KV head", 9,
                  fill=C["ink"], weight=600))
    # step 2: set_k_block per KV head (the same white function cell as part a)
    s2 = ["the whole-block save of one KV head (part a);",
          "sets no bit; every KV head first"]
    for s in s2:
        fit(s, 9.5, cw - 16, False, "step 2")
    o.append(fn_cell(cx, 140, cw, 62, "set_k_block", s2,
                     "kv_cache.hpp:2273-2284; model.hpp:3325-3339", "new"))
    boxes.append(("set_k_block x n_kv_heads (the KV-head loop)",
                  "kv_cache.hpp:2273-2284; the loop model.hpp:3325-3339"))
    o.append(arrow(fid, "ink", [(ax, 204), (ax, 230)], C["ink"], 1.4))
    o.append(text(ax + 8, 221, "1 call per block, after the last KV head", 9, fill=C["ink"],
                  weight=600))
    # step 3: note_k_block_saved
    d3 = ["publishes the 16 row bits (fetch_or, acq_rel),",
          "then the block bit (fetch_or, release)"]
    for s in d3:
        fit(s, 9.5, cw - 16, False, "desc note_k_block_saved")
    o.append(fn_cell(cx, 232, cw, 58, "note_k_block_saved", d3, "kv_cache.hpp:2194-2200",
                     "new"))
    boxes.append(("note_k_block_saved", "kv_cache.hpp:2192-2200; the call model.hpp:3340"))
    # right column: the result for the worked example
    rx2 = 380
    o.append(text(rx2, 68, f"result for the worked example: state entry 5, block {BLOCK_C}",
                  10, weight=700))
    o.append(text(rx2, 90, "k_rows_saved_[5]", 9.5, mono=True, fill=C["rows"]))
    body, _ = bit_row(500, 81, "1" * 16, 9, 1, C["rows_fill"], C["rows"], group=16)
    o.append(body)
    o.append(text(500, 102, "k_block_bits(0): fetch_or, acq_rel", 8.5,
                  fill=C["muted"]))
    o.append(text(rx2, 126, "k_vnni_blocks_[5]", 9.5, mono=True, fill=C["blk"]))
    for c in range(4):
        gx3 = 500 + c * 40
        on = c == BLOCK_C
        o.append(rect(gx3, 116, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx3 + 16, 126, f"bit {c}", 8.5, fill=C["muted"]))
    o.append(text(500, 138, f"block_bit({BLOCK_C}): fetch_or, release", 8.5,
                  fill=C["muted"]))
    o.append(cite(684, 151, "kv_cache.hpp:2198-2199, 2608-2622"))
    boxes.append((f"k_rows_saved_[5] / k_vnni_blocks_[5] after the unit (bits 0..15, bit "
                  f"{BLOCK_C})", "kv_cache.hpp:2198-2199; the arrays kv_cache.hpp:2608-2622"))
    # the state jump: the B4 arc, its name written on the arrow
    stw, sth, sty = 130, 64, 168
    o.append(state_box(rx2, sty, stw, sth, "empty", "empty", "no row bit",
                       "kv_cache.hpp:2608-2617"))  # the empty state of B4
    o.append(state_box(rx2 + 170, sty, stw, sth, "vnni", "converted: VNNI",
                       "16 row bits, bit set", "kv_cache.hpp:2618-2622"))
    o.append(arrow(fid, "vnni", [(rx2 + stw + 2, sty + 32), (rx2 + 168, sty + 32)],
                   C["vnni"], 1.6))
    o.append(text(rx2 + 150, sty + 26, "the B4", 8.5, "middle", fill=C["vnni"], weight=600))
    o.append(text(rx2 + 150, sty + 44, "arc", 8.5, "middle", fill=C["vnni"], weight=600))
    boxes.append(("empty -> converted: VNNI (the arc over the top of B4)",
                  "kv_cache.hpp:2608-2617, 2618-2622; Note [K VNNI storage] 705-711"))
    nc = ["no 'complete, may wait' state, no forward-end",
          "conversion: the block is VNNI at once (the B4 arc)",
          "[kv_cache.hpp:705-711]",
          "a reader must not see the block bit before every KV head",
          "holds the layout: bits are per slot, not per KV head [707-709]"]
    for s in nc:
        fit(s, 9, 320, False, "notes C")
    o.append(lines(rx2, 248, nc, 9, 11))
    cap = ("Updates B4 (part b): the caller of set_k_block. store_k_block [any thread of "
           "the shared window] calls set_k_block once per KV head and only then "
           "note_k_block_saved, which sets the 16 row bits (acq_rel) and the block bit "
           "(release), so the block goes from empty straight to converted with no wait "
           "for the forward end (the arc over the top of B4, right).")
    legend = [
        ("box", "white box, ink outline: the function cells set_k_block and "
                "note_k_block_saved; name in bold monospace, description in sans-serif"),
        ("ctx", "grey box, thin grey outline: the caller store_k_block (model.hpp), with its "
                "thread in brackets"),
        ("rows", "green (squares and label): k_rows_saved_[5], the 16 row bits of block 0, "
                 "all set by note_k_block_saved"),
        ("blk", "pink (square and label): k_vnni_blocks_[5] bit 0, the block bit set by "
                "note_k_block_saved"),
        ("bit_clear", "white square, grey outline: k_vnni_blocks_[5] bits 1..3, clear "
                      "after this unit"),
        ("empty", "grey dashed: the state empty (no row bit), the start of the B4 arc"),
        ("vnni", "blue (box and label): the state converted: VNNI (16 row bits and the "
                 "block bit set), the end of the B4 arc"),
        ("arrow", "ink arrow: a call step in store_k_block; its label says how many "
                  "(1 run -> n_kv_heads calls; 1 call per block)"),
        ("blue arrow: the B4 arc, empty -> converted: VNNI in one step", "arrow",
         C["vnni"]),
        ("font_mono", "monospace = identifiers from the code: set_k_block, "
                      "note_k_block_saved, k_rows_saved_[5], k_vnni_blocks_[5]"),
        ("font_sans", "sans-serif = prose: the worked example, the caller's lines, "
                      "descriptions, notes"),
        "font_cite",
        ("font_tag", "bold 'new' = set_k_block and note_k_block_saved are added by this PR"),
    ]
    return figure(fid, W, H, "set_k_block (part b): the caller, the bits and the B4 arc",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
