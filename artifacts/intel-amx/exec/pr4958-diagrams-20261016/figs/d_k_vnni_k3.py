"""Change diagrams of unit k3 of the PR 4958 k_vnni.hpp page: store_block
(head lines 326-367) and the changed comment of store_row (290-292). Two
figures:
  k_vnni-d3a  the data flow of one dimension step on the worked example
              (block 2, present 0x01ff, step s = 2): rows[] -> loads -> r[t] ->
              transpose -> r[dp] -> 16 masked stores -> panel (2,2) #10;
  k_vnni-d3b  the branch on present, the write pattern against store_row,
              the callers at the head with their threads, and store_row's
              new comment.
Line numbers are head line numbers of h/tron/tensor/k_vnni.hpp unless
another file is named. Adapted from exec/pr4424-diagrams-20261009/figs/
d_k_vnni_k7.py with the PR 4958 facts.
"""
from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, line, lines,
                         marker_defs, rect, text)
from base_k_vnni import (EX, PRESENT_UNIT2, ABSENT_UNIT2, _w, dword_grid, panel_lines,
                         present_bits, nx_box)

BASE = ("Updates B4 and B5: the store_block call of B4's step 2 (unit 2, present 0x01ff) "
        "is opened for one dimension step, and the callers of B5 that reach store_block "
        "are listed with the mask each one passes; store_row's new comment states the "
        "rule B5 relies on.")

W = 700
CELL = 8
GRID = 16 * CELL


def fig_a():
    fid = "k_vnni-d3a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    desc = ["Store the K rows of up to 16 tokens of one token block c (the bits t set in "
            "present) into a packed plane",
            "with full-line stores; masked to the present tokens' lanes when the block is "
            "partial; absent slots not written."]
    for d in desc:
        _w(d, 9.5, 644, where="d3a fn desc")
    o.append(fn_cell(20, 8, 660, 64, "store_block(dst, c, present, rows)", desc,
                     "k_vnni.hpp:326-367", "new"))
    boxes.append(("store_block(dst, c, present, rows)", "k_vnni.hpp:326-367"))
    sub = ["worked example: unit 2 of the shared window = block 2 (tokens 32..40, present "
           "0x01ff) of the plane of slot 5, KV head 0,",
           "page 7; one dimension step, s = 2: 9 loads of 64 B + 7 zero registers -> one "
           "transpose -> 16 masked stores into panel (2,2) #10"]
    for s in sub:
        _w(s, 9.5, 660, where="d3a sub")
    o.append(lines(20, 88, sub, 9.5, 12, fill=C["muted"]))
    # ---- A: rows[] and present ----------------------------------------------------
    A = 116
    o.append(text(20, A + 4, "rows[BLOCK_TOKENS_16]: 16 native rows, null for absent lanes",
                  10, weight=700))
    rx, ry, segw, rowh = 44, A + 24, 44, 7
    for s in range(4):
        hi = s == EX["s"]
        o.append(text(rx + s * segw + segw / 2, ry - 4, f"s = {s}", 8.5, "middle", True,
                      fill=C["vnni"] if hi else C["muted"], weight=600 if hi else None))
    for t in range(16):
        for s in range(4):
            if t in ABSENT_UNIT2:
                o.append(rect(rx + s * segw, ry + t * rowh, segw, rowh, C["empty_fill"],
                              C["empty"], 0.5, 0, "2 2"))
            else:
                o.append(rect(rx + s * segw, ry + t * rowh, segw, rowh, C["rm_fill"], C["rm"],
                              0.5, 0))
    o.append(rect(rx + EX["s"] * segw, ry - 2, segw, 16 * rowh + 4, "none", C["vnni"], 1.6, 0))
    o.append(rect(rx, ry + EX["t"] * rowh, 4 * segw, rowh, "none", C["ink"], 1.6, 0))
    o.append(rect(rx, ry, 4 * segw, 16 * rowh, "none", C["ink"], 0.8, 0))
    for t, lab in ((0, "t=0"), (EX["t"], "t=5"), (9, "t=9"), (15, "t=15")):
        hi = t == EX["t"]
        o.append(text(rx - 4, ry + t * rowh + rowh - 1, lab, 8.5, "end", True,
                      fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    o.append(text(rx, ry + 16 * rowh + 12, "[k_vnni.hpp:332-334, 345]", 8.5, mono=True,
                  fill=C["cite"]))
    boxes.append(("rows[BLOCK_TOKENS_16] (rows[t] = the 128 bf16 of token c * 16 + t)",
                  "k_vnni.hpp:332-334, 345"))
    notes = ["1 row = 128 bf16 = 256 B", "= 4 steps of 64 B", "token 37 = rows[5] (thick)",
             "rows[9..15] = null (absent)"]
    for s in notes:
        _w(s, 9, 130, where="d3a rows notes")
    o.append(lines(rx + 4 * segw + 10, ry + 10, notes, 9, 12, fill=C["ink"]))
    # present
    px, py, pw, ph = 380, A - 6, 300, 118
    o.append(rect(px, py, pw, ph, "#fff", C["ink"], 1.2, 5))
    o.append(text(px + 10, py + 16, "present: __mmask16 = 0x01ff", 11, mono=True, weight=600))
    o.append(text(px + 10, py + 30, "bit t set = token c * 16 + t is in the save", 9.5,
                  fill=C["muted"]))
    body, bx_end = present_bits(px + 12, py + 38, PRESENT_UNIT2, 11, 1)
    o.append(body)
    o.append(text(px + 12 + 5, py + 60, "t = 0", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(px + 12 + 8 * 12 + 5, py + 60, "t = 8", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(px + 12 + 15 * 12 + 5, py + 60, "t = 15", 8.5, "middle", True,
                  fill=C["muted"]))
    pl = ["!= FULL_BLOCK_0XFFFF: the masked branch (361)",
          "bit clear: rows[t] may be null, r[t] = 0 (351-353)",
          "the test's 38 masks cover full, empty, halves, ..."]
    for s in pl:
        _w(s, 9, pw - 20, where="d3a present")
    o.append(text(px + 10, py + 78, pl[0], 9.5, weight=600, fill=C["ink"]))
    o.append(lines(px + 10, py + 92, pl[1:], 9, 12, fill=C["muted"]))
    o.append(cite(px + pw - 4, py + ph - 4, "k_vnni.hpp:326-327, 344; 76-77"))
    boxes.append(("present: __mmask16 = 0x01ff", "k_vnni.hpp:326-327, 344"))
    # ---- the loads --------------------------------------------------------------------
    ax = rx + 40
    ly0 = ry + 16 * rowh + 18
    B = ly0 + 94
    gy = B + 16
    o.append(arrow(fid, "ink", [(ax, ly0), (ax, gy - 4)], C["ink"], 1.4))
    ll = ["9 loads x 64 B, one per present row:",
          "_mm512_loadu_si512(rows[t] + s * STEP_DIMS_32)",
          "-> r[t]; absent: r[t] = _mm512_setzero_si512()"]
    for s in ll[1:]:
        _w(s, 9, 300, True, "d3a loads")
    o.append(text(ax + 10, ly0 + 14, ll[0], 9.5, weight=600, fill=C["ink"]))
    o.append(lines(ax + 10, ly0 + 27, ll[1:], 9, 12, mono=True))
    o.append(text(ax + 10, ly0 + 63, "[k_vnni.hpp:349-354]", 8.5, mono=True, fill=C["cite"]))
    # ---- B: the two register grids ---------------------------------------------------
    gx1, gx2 = 44, 330
    o.append(lines(ax + 10, B - 11, ["r[t] after the loads:", "rows t = 9..15 are zero"],
                   10, 11, weight=700))
    o.append(lines(gx2 - 2, B - 11, ["r[dp] after the transpose:", "lanes t = 9..15 are zero"],
                   10, 11, weight=700))
    o.append(dword_grid(gx1, gy, C["rm_fill"], C["rm"], hi_row=EX["t"],
                        hi_cell=(EX["t"], EX["dp"]), row_labels=(0, EX["t"], 9, 15),
                        col_labels=(0, EX["dp"], 15), row_prefix="t=", cell=CELL,
                        zero_rows=ABSENT_UNIT2))
    o.append(dword_grid(gx2, gy, C["vnni_fill"], C["vnni"], hi_row=EX["dp"], hi_col=EX["t"],
                        hi_cell=(EX["dp"], EX["t"]), row_labels=(0, EX["dp"], 15),
                        col_labels=(0, EX["t"], 9, 15), row_prefix="dp=", cell=CELL,
                        zero_cols=ABSENT_UNIT2))
    boxes.append(("r[BLOCK_TOKENS_16] (__m512i, 16 registers of 16 dwords)",
                  "k_vnni.hpp:349-355"))
    o.append(cite(gx1 + GRID, gy + GRID + 10, "k_vnni.hpp:349-354"))
    o.append(cite(gx2 + GRID - 14, gy + GRID + 10, "k_vnni.hpp:355"))
    my = gy + GRID / 2
    o.append(arrow(fid, "vnni", [(gx1 + GRID + 4, my), (gx2 - 28, my)], C["vnni"], 1.6))
    mx = (gx1 + GRID + 4 + gx2 - 28) / 2
    o.append(text(mx, my - 30, "transpose_16x16_", 9, "middle", True, fill=C["vnni"], weight=600))
    o.append(text(mx, my - 19, "epi32(r)", 9, "middle", True, fill=C["vnni"], weight=600))
    o.append(text(mx, my - 7, "16 x 16 dwords", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 16, "in place: 4 stages,", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 27, "64 shuffles", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 39, "[k_vnni.hpp:257-287]", 8.5, "middle", True, fill=C["cite"]))
    boxes.append(("transpose_16x16_epi32(r)", "k_vnni.hpp:257-287"))
    u = gy + GRID + 24
    o.append(text(gx1, u, "r[5] lane 3 = dims 70, 71 of token 37 (blue)", 9, fill=C["ink"]))
    o.append(text(gx2, u, "r[3] lane 5 = the same dword", 9, fill=C["ink"]))
    # ---- C: the masked stores -> panel (2,2) #10 -----------------------------------------
    sx = gx2 + GRID - 12
    sy0 = u + 14
    Pn = sy0 + 60
    o.append(arrow(fid, "vnni", [(sx, gy + GRID + 2), (sx, Pn - 4)], C["vnni"], 1.6))
    sl = ["16 masked stores x 64 B:", "_mm512_mask_storeu_epi32(",
          "panel + dp * ROW_ELEMS_32, present, r[dp])"]
    for s in sl[1:]:
        _w(s, 9, W - sx - 20, True, "d3a stores")
    o.append(text(sx + 10, sy0 + 10, sl[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(sx + 10, sy0 + 23, sl[1:], 9, 12, mono=True))
    o.append(text(sx + 10, sy0 + 47, "[k_vnni.hpp:361-365]", 8.5, mono=True, fill=C["cite"]))
    pxp, pwp, php = gx2, GRID, GRID
    o.append(panel_lines(pxp, Pn, pwp, php, ["vnni"] * 16, hi_rows=[EX["dp"]],
                         cols_present=PRESENT_UNIT2))
    lh = php / 16
    for dp in (0, EX["dp"], 15):
        hi = dp == EX["dp"]
        o.append(text(pxp - 4, Pn + dp * lh + 7, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if hi else C["muted"], weight=600 if hi else None))
    o.append(rect(pxp + EX["t"] * (pwp / 16), Pn + EX["dp"] * lh, pwp / 16, lh, C["vnni"],
                  C["ink"], 1.0, 0))
    o.append(cite(pxp + pwp, Pn + php + 10, "k_vnni.hpp:356"))
    boxes.append(("panel (2,2) #10 = panel (s, c) of block c", "k_vnni.hpp:356; 27-28"))
    nx = pxp + pwp + 10
    pn = ["panel (2,2) #10", "= plane + (s * TOKEN_BLOCKS_4", "  + c) * PANEL_ELEMS_512"]
    for s in pn:
        _w(s, 9, W - nx - 10, True, "d3a panel note")
    o.append(text(nx, Pn + 12, pn[0], 10, mono=True, weight=700))
    o.append(lines(nx, Pn + 26, pn[1:], 9, 12, mono=True))
    o.append(text(nx, Pn + 50, "[k_vnni.hpp:356]", 8.5, mono=True, fill=C["cite"]))
    wn = ["pair row 3 <- r[3], lanes 0..8:", "dims 70, 71 of tokens 32..40;",
          "lane 5 = token 37, byte 10452;", "lanes 9..15 of every line untouched"]
    for s in wn:
        _w(s, 9, W - nx - 10, where="d3a worked")
    o.append(text(nx, Pn + 72, wn[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(nx, Pn + 85, wn[1:], 9, 12, fill=C["ink"]))
    o.append(text(nx, Pn + 121, "[k_vnni.hpp:105-114, 331-332]", 8.5, mono=True, fill=C["cite"]))
    # the block at the left: x DIM_STEPS_4
    bx0 = 20
    o.append(text(bx0, Pn + 64, "the block: x DIM_STEPS_4 = 4 steps s", 10, weight=700))
    mw, mh, mg = 56, 38, 8
    for s in range(4):
        x = bx0 + 24 + s * (mw + mg)
        hi = s == EX["s"]
        o.append(rect(x, Pn + 14, mw, mh, C["vnni_fill"], C["vnni"], 2.0 if hi else 1.0, 3))
        o.append(text(x + mw / 2, Pn + 14 + 16, f"({s},2)", 9, "middle", True))
        o.append(text(x + mw / 2, Pn + 14 + 30, f"#{4 * s + 2}", 8.5, "middle", True,
                      fill=C["muted"]))
    cx22 = bx0 + 24 + EX["s"] * (mw + mg) + mw / 2
    over_y = Pn - 8
    o.append(arrow(fid, "muted", [(cx22, Pn + 14), (cx22, over_y), (pxp + 40, over_y),
                                  (pxp + 40, Pn - 2)], C["muted"], 1.2, "4 3"))
    o.append(text(cx22 + 8, over_y - 4, "s = 2 ->", 8.5, fill=C["muted"]))
    bl = ["4 steps x 16 masked stores = 64 stores:",
          "the block's 4 panels (s, 2), each line",
          "written once, 36 of its 64 B (9 lanes);",
          "a full block: 64 whole-line stores"]
    for s in bl:
        _w(s, 9.5, cx22 + 20 - bx0, where="d3a block")
    o.append(text(bx0, Pn + 84, bl[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(bx0, Pn + 97, bl[1:], 9, 12, fill=C["ink"]))
    o.append(text(bx0, Pn + 143, "[k_vnni.hpp:348, 357-365; 334-337]", 8.5, mono=True,
                  fill=C["cite"]))
    H = int(Pn + php + 30)
    cap = ("Updates B4 and B5: step 2 of B4 calls store_block with present = 0x01ff, the "
           "call helper 2 makes in B5 for unit 2; this figure opens that call for one "
           "dimension step. The 9 loads put the present rows into r[0..8] and zero "
           "r[9..15]. The transpose moves token 37's 16 pairs from r[5] into lane 5 of "
           "every register, and the zeros into lanes 9..15. The 16 masked stores write "
           "register r[dp] as pair row dp of panel (2,2) #10, lanes 0..8 only. So dims "
           "70, 71 of token 37 land in lane 5 of pair row 3 (byte 10452 of B1), and the "
           "bytes of tokens 41..47 are never touched.")
    legend = [
        ("box", "white box, ink outline: the function cell store_block(dst, c, present, "
                "rows) and the input present: __mmask16; the name in bold monospace, the "
                "description in grey sans-serif"),
        ("rm", "orange: the row-major side: the 9 present native rows rows[t] (4 steps of "
               "64 B each) and the r[t] register grid after the loads"),
        ("vnni", "blue: the VNNI side: the r[dp] register grid after the transpose, the 16 "
                 "pair rows of panel (2,2) #10 and the block's 4 panels (s, 2), with cell "
                 "(2,2) outlined heavier; blue text = the step s = 2, the transpose, the "
                 "stores and the pair row of the worked example"),
        ("present", "green: the 9 set bits of present and the 9 written columns (lanes "
                    "0..8) of the panel"),
        ("empty", "grey dashed: an absent lane: a null row, a zero register r[t], a zero "
                  "lane of r[dp], a clear bit of present, an untouched column of the panel"),
        ("solid blue cell, ink outline: the worked example's dword, dims 70, 71 of token "
         "37: r[5] lane 3 after the loads, r[3] lane 5 after the transpose, lane 5 of "
         "pair row 3 in the panel", C["vnni"], C["ink"], False, False),
        ("blue frame: the column s = 2 of rows[], the dimension step this figure follows",
         "none", C["vnni"], False, False),
        ("ink outline: the frame of rows[], of each register grid and of the panel, and "
         "the highlighted row or column of the worked example", "none", C["ink"], False, False),
        ("arrow", "ink arrow: the loads, rows[t] + s * STEP_DIMS_32 -> r[t]"),
        ("blue arrow: transpose_16x16_epi32, r[t] -> r[dp], and the 16 masked stores, "
         "r[dp] -> panel (2,2) #10", "arrow", C["vnni"]),
        ("arrow_muted", "grey dashed arrow: cell (2,2) of the block -> the panel it names"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = store_block is added by this PR"),
    ]
    return figure(fid, W, H, "store_block: one dimension step of the masked block save on the "
                  "worked example", "".join(o), cap, boxes=boxes, legend=legend)


def fig_b():
    fid = "k_vnni-d3b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "muted": C["muted"], "present": C["rows"]})]
    o.append(text(20, 16, "the branch on present, its callers at the head, the write pattern "
                  "against store_row, and store_row's comment", 10.5, weight=700))
    # ---- section 1: the branch ------------------------------------------------------
    by = 28
    bw, bh = 320, 70
    b1 = ["_mm512_storeu_si512(panel + dp * ROW_ELEMS_32, r[dp])",
          "x 16 per step: whole lines, no mask; units 0 and 1"]
    b2 = ["_mm512_mask_storeu_epi32(.., present, r[dp]) x 16:",
          "absent lanes not written; r[t] of a null row = 0; unit 2"]
    for s in b1 + b2:
        _w(s, 9.5, bw - 8, where="d3b branch")
    o.append(label_box(20, by, bw, bh, "present == FULL_BLOCK_0XFFFF", b1, "#fff", C["ink"],
                       11, ref="k_vnni.hpp:357-360"))
    boxes.append(("present == FULL_BLOCK_0XFFFF (the whole-line branch)", "k_vnni.hpp:357-360"))
    o.append(label_box(360, by, bw, bh, "else: a partial block", b2, C["rows_fill"], C["rows"],
                       11, ref="k_vnni.hpp:361-365; 350-354"))
    boxes.append(("else: a partial block (_mm512_mask_storeu_epi32)", "k_vnni.hpp:361-365"))
    # ---- section 3: the callers and their threads --------------------------------------
    S3 = by + bh + 52
    o.append(text(20, S3 - 4, "callers at the head, each with the mask it passes and its thread",
                  10, weight=700))
    cy, ch = S3 + 4, 110
    c1 = ["store_k_block -> set_k_block(slot,", "kv_head, c, present, rows) for a run",
          "of 2..16 tokens: present = the run's", "lanes (0xffff, or 0x01ff for unit 2)",
          "[any thread of the window, in its unit]"]
    c2 = ["store_block(blk->plane.as_view(),", "c, __mmask16(m), rows): 14 named",
          "masks + 24 random, x 4 blocks,", "memcmp against store_row per",
          "present token [the test thread]"]
    c3 = ["the per-row store of a run of one", "token: set_k_row -> store_row, 4",
          "scatters; also the PR 4959 conversion", "(not in this PR)"]
    for s in c1 + c2:
        _w(s, 9.5, 215 - 8, where="d3b caller")
    for s in c3:
        _w(s, 9, 200 - 16, where="d3b caller 3")
    o.append(label_box(20, cy, 215, ch, "page::set_k_block", c1, C["soft"], C["ink"],
                       10.5, ref="kv_cache.hpp:2078-2096"))
    boxes.append(("page::set_k_block(slot, kv_head, c, present, rows)", "kv_cache.hpp:2078-2096"))
    o.append(text(20, cy + ch + 11, "[model.hpp:3276-3289, 3245-3257]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(label_box(250, cy, 215, ch, "the block-save test", c2, C["soft"], C["line"],
                       10.5, ref="t_k_vnni_layout.cpp:192-250"))
    boxes.append(("the block-save test (store_block against store_row, 38 masks)",
                  "t_k_vnni_layout.cpp:192-250"))
    o.append(text(250, cy + ch + 11, "[t_k_vnni_layout.cpp:241-243]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(nx_box(480, cy, 200, ch, "no other caller", c3, "model.hpp:3260-3273"))
    boxes.append(("no other caller: a run of one token takes set_k_row -> store_row",
                  "model.hpp:3260-3273"))
    bb = by + bh
    o.append(arrow(fid, "ink", [(120, cy), (120, bb + 4)], C["ink"], 1.4))
    o.append(text(126, bb + 16, "0xffff (units 0, 1)", 9, mono=True, fill=C["ink"], weight=600))
    o.append(arrow(fid, "present", [(230, cy), (230, bb + 26), (380, bb + 26), (380, bb + 4)],
                   C["rows"], 1.4))
    o.append(text(236, bb + 22, "0x01ff (unit 2)", 9, mono=True, fill=C["rows"], weight=600))
    o.append(arrow(fid, "muted", [(440, cy), (440, bb + 4)], C["muted"], 1.2, "4 3"))
    o.append(text(446, bb + 16, "m: 38 masks", 9, mono=True, fill=C["muted"]))
    # ---- section 2: the write pattern -----------------------------------------------
    T = cy + ch + 34
    gx1, gx2, gy = 44, 380, T + 28
    o.append(text(20, T, "store_row x 16, one per token (B4 step 3)", 10, weight=700))
    o.append(text(20, T + 11, "one of the block's 4 panels = 1 KiB of its 4 KiB", 9,
                  fill=C["muted"]))
    o.append(text(gx2 - 2, T, "store_block, a full block (B4 step 1)", 10, weight=700))
    o.append(text(gx2 - 2, T + 11, "the same panel = 1 KiB of the block's 4 KiB", 9,
                  fill=C["muted"]))
    o.append(dword_grid(gx1, gy, C["vnni_fill"], C["ink"], row_labels=(0, 15),
                        col_labels=(0, 15), row_prefix="dp=", col_prefix="t=", cell=CELL))
    o.append(panel_lines(gx2, gy, GRID, GRID, ["vnni"] * 16))
    for dp in (0, 15):
        o.append(text(gx2 - 4, gy + dp * CELL + 7, f"dp={dp}", 8.5, "end", True,
                      fill=C["muted"]))
    o.append(cite(gx1 + GRID, gy + GRID + 10, "k_vnni.hpp:302-306"))
    o.append(cite(gx2 + GRID, gy + GRID + 10, "k_vnni.hpp:357-360"))
    u = gy + GRID + 24
    l1 = ["64 scatters per block (4 per token),", "each writing 4 B into 16 lines: every one",
          "of the block's 64 lines receives 16 partial writes"]
    l2 = ["64 whole-line stores per block", "(16 per step x 4 steps): each of the",
          "64 lines is written once, whole"]
    for s in l1 + l2:
        _w(s, 9.5, 300, where="d3b pattern")
    o.append(text(gx1, u, l1[0], 9.5, weight=600, fill=C["ink"]))
    o.append(lines(gx1, u + 13, l1[1:], 9, 12, fill=C["ink"]))
    o.append(text(gx1, u + 40, "[k_vnni.hpp:334-337]", 8.5, mono=True, fill=C["cite"]))
    o.append(text(gx2, u, l2[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(gx2, u + 13, l2[1:], 9, 12, fill=C["ink"]))
    o.append(text(gx2, u + 40, "[k_vnni.hpp:334-337]", 8.5, mono=True, fill=C["cite"]))
    boxes.append(("store_row x 16 (the per-token write pattern)", "k_vnni.hpp:302-306, 334-337"))
    boxes.append(("store_block: the full-block write pattern", "k_vnni.hpp:334-337, 357-360"))
    mx = (gx1 + GRID + gx2) / 2
    mid = ["the same bytes,", "bit-identical;", "the write", "pattern differs"]
    o.append(lines(mx, gy + 40, mid, 9.5, 13, "middle", fill=C["ink"], weight=600))
    o.append(text(mx, gy + 40 + 4 * 13 + 2, "[kv_cache.hpp:", 8.5, "middle", True,
                  fill=C["cite"]))
    o.append(text(mx, gy + 40 + 5 * 13 + 2, "2082-2084]", 8.5, "middle", True, fill=C["cite"]))
    ly = u + 50
    o.append(rect(gx1, ly, CELL, CELL, C["vnni_fill"], C["ink"], 0.6, 0))
    o.append(text(gx1 + CELL + 6, ly + 8, "one 4-byte write (one lane of a scatter)", 9.5))
    o.append(rect(gx2, ly, 40, CELL, C["vnni_fill"], C["vnni"], 1.0, 0))
    o.append(text(gx2 + 46, ly + 8, "one 64-byte line write", 9.5))
    # ---- section 4: store_row's new comment --------------------------------------------
    S4 = ly + 30
    o.append(rect(20, S4, 660, 58, "#fff", C["ink"], 1.2, 5))
    o.append(text(28, S4 + 16, "store_row: the comment states the concurrency rule", 10.5,
                  mono=True, weight=700))
    rl = ["'Only this token's 64 pair slots are written. So several threads may store "
          "different tokens of one plane",
          "at the same time (Note [Shared block save] in model.hpp).' The code of store_row "
          "is unchanged."]
    for r in rl:
        _w(r, 9.5, 640, where="d3b store_row")
    o.append(lines(28, S4 + 31, rl, 9.5, 11))
    o.append(text(28, S4 + 54, "changed", 9, fill=C["muted"]))
    o.append(cite(676, S4 + 54, "k_vnni.hpp:290-292"))
    boxes.append(("store_row: the comment states the concurrency rule", "k_vnni.hpp:290-292"))
    H = int(S4 + 70)
    cap = ("Updates B4 and B5: the comparison that the comment of store_block makes with "
           "step 3 of B4 (store_row), the branch on present, and the callers of B5 that "
           "reach store_block. Left: 16 store_row calls write 4 bytes into every line, 16 "
           "times per line. Right: store_block writes each line once, whole. The bytes "
           "are bit-identical (kv_cache.hpp:2082-2084). page::set_k_block passes the run's "
           "mask through: 0xffff for a full block, a partial mask such as 0x01ff for unit "
           "2, so both branches run in production; the test drives 38 masks. store_row "
           "itself only gains the comment that states why different threads may store "
           "different tokens of one plane.")
    legend = [
        ("blue cells, ink outline: the left panel as 16 x 16 dwords, one 4-byte write each "
         "(one lane of a store_row scatter)", C["vnni_fill"], C["ink"], False, False),
        ("vnni", "blue lines, blue outline: the right panel as 16 whole lines, one 64-byte "
                 "line write each (store_block); blue text = the count of whole-line stores "
                 "per block"),
        ("thin ink frame: the outline of each panel drawing", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the branch present == FULL_BLOCK_0XFFFF and the "
                "comment box of store_row; the name in bold monospace, the description in "
                "grey sans-serif"),
        ("present", "green box: the else branch, a partial block with masked stores (the "
                    "worked example's unit 2); green arrow and text = the partial mask "
                    "0x01ff that page::set_k_block passes for unit 2"),
        ("ctx_ink", "grey fill, ink outline: the caller page::set_k_block in kv_cache.hpp, "
                    "run by any thread of the window inside its claimed unit"),
        ("ctx", "grey fill, thin grey outline: the block-save test, the only caller with "
                "arbitrary masks"),
        ("deleted", "white box, grey dashed outline: 'no other caller': a run of one token "
                    "does not reach store_block"),
        ("arrow", "ink arrow: page::set_k_block -> the whole-line branch with 0xffff "
                  "(units 0 and 1)"),
        ("green arrow: page::set_k_block -> the masked branch with 0x01ff (unit 2)",
         "arrow", C["rows"]),
        ("arrow_muted", "grey dashed arrow: the test -> the branches, with 38 masks m"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag_changed", "grey 'changed' = store_row's comment is changed by this PR"),
    ]
    return figure(fid, W, H, "store_block: the branch on present, the write pattern against "
                  "store_row, the callers, and store_row's comment", "".join(o), cap,
                  boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
