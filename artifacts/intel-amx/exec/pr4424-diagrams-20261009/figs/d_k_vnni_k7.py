"""Change diagram of unit k7 of the PR 4424 k_vnni.hpp page: store_block
(k_vnni.hpp:382-421), 16 rows transposed in registers and written as whole
lines. Two figures:
  d7a = the data flow of one dimension step on the worked example (block 2,
        step s = 2): rows[] -> 16 loads -> r[t] -> transpose -> r[dp] ->
        16 whole-line stores -> panel (2,2) #10;
  d7b = the write pattern against 16 x store_row, the branch on `present`,
        and the callers at the head with the thread that runs them.

Every fact comes from facts/k_vnni.json (verified) or from the head file;
line numbers are head line numbers of h/tron/tensor/k_vnni.hpp unless another
file is named.
"""
import sys

from svg_helpers import (C, arrow, bit_row, cite, figure, fn_cell, label_box,
                         line, lines, marker_defs, rect, text, text_width)
from base_k_vnni import EX, BLOCK_2, panel_lines

BASE = ("Updates B4: the store_block call of step 2 (the same call page::set_k_block "
        "makes for a run of 16 tokens) is opened up: per dimension step s, 16 row "
        "loads, one transpose_16x16_epi32 in registers and 16 whole-line stores fill "
        "panel (s, c), against the 64 scatters of store_row in step 3.")

W = 700
CELL = 10            # one dword of a 16 x 16 register grid, in px
GRID = 16 * CELL     # 160 px


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def dword_grid(x, y, fill, stroke, hi_row=None, hi_col=None, hi_cell=None,
               row_labels=(), col_labels=(), row_prefix="", col_prefix="",
               cell=CELL):
    """16 x 16 dwords: 16 registers (rows) x 16 lanes (columns) of 32 bits.
    hi_row / hi_col get a thick outline; hi_cell = (row, col) is filled in the
    VNNI colour with an ink outline. row_labels / col_labels: the indexes to
    print (8.5 px mono), with a prefix."""
    n = 16
    o = []
    for r in range(n):
        for c in range(n):
            o.append(rect(x + c * cell, y + r * cell, cell, cell, fill, stroke, 0.4, 0))
    if hi_cell is not None:
        r, c = hi_cell
        o.append(rect(x + c * cell, y + r * cell, cell, cell, C["vnni"], C["ink"], 1.0, 0))
    if hi_row is not None:
        o.append(rect(x, y + hi_row * cell, n * cell, cell, "none", C["ink"], 1.6, 0))
    if hi_col is not None:
        o.append(rect(x + hi_col * cell, y, cell, n * cell, "none", C["ink"], 1.6, 0))
    o.append(rect(x, y, n * cell, n * cell, "none", C["ink"], 0.8, 0))
    for i in row_labels:
        hi = i == hi_row
        o.append(text(x - 4, y + i * cell + cell / 2 + 3, f"{row_prefix}{i}", 8.5, "end",
                      True, fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    for i in col_labels:
        hi = i == hi_col
        o.append(text(x + i * cell + cell / 2, y - 3, f"{col_prefix}{i}", 8.5, "middle",
                      True, fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    return "".join(o)


# ---------------------------------------------------------------------------
# d7a: one dimension step of store_block on the worked example


def fig_a():
    fid = "k_vnni-d7a"
    H = 790
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    # ---- the function cell of the unit ---------------------------------------
    desc = ["Store the K rows of up to 16 tokens of one token block c into a packed plane "
            "with full-line stores;",
            "the absent tokens' slots are not written. rows[t] may be null for an absent "
            "token."]
    for d in desc:
        _w(d, 9.5, 660 - 16, where="d7a fn desc")
    # two description lines: 64 px, so the second line clears the tag and cite
    o.append(fn_cell(20, 8, 660, 64, "store_block(dst, c, present, rows)", desc,
                     "k_vnni.hpp:394-420", "new"))
    boxes.append(("store_block(dst, c, present, rows)", "k_vnni.hpp:394-420"))
    sub = ["worked example: block 2 (tokens 32..47) of the plane of slot 5, KV head 0, "
           "page 7; one dimension step, s = 2:",
           "16 loads of 64 B -> one 16 x 16 transpose in registers -> 16 whole-line "
           "stores into panel (2,2) #10 (the s loop, line 401)"]
    for s in sub:
        _w(s, 9.5, 660, where="d7a sub")
    o.append(lines(20, 88, sub, 9.5, 12, fill=C["muted"]))

    # ---- section A: the inputs rows[] and present -----------------------------
    A = 112
    o.append(text(20, A + 4, "rows[BLOCK_TOKENS_16]: 16 native rows in dimension order", 10,
                  weight=700))
    rx, ry, segw, rowh = 44, A + 24, 48, 8
    for s in range(4):
        hi = s == EX["s"]
        o.append(text(rx + s * segw + segw / 2, ry - 4, f"s = {s}", 8.5, "middle", True,
                      fill=C["vnni"] if hi else C["muted"], weight=600 if hi else None))
    for t in range(16):
        for s in range(4):
            o.append(rect(rx + s * segw, ry + t * rowh, segw, rowh, C["rm_fill"], C["rm"],
                          0.5, 0))
    o.append(rect(rx + EX["s"] * segw, ry - 2, segw, 16 * rowh + 4, "none", C["vnni"], 1.6,
                  0))
    o.append(rect(rx, ry + EX["t"] * rowh, 4 * segw, rowh, "none", C["ink"], 1.6, 0))
    o.append(rect(rx, ry, 4 * segw, 16 * rowh, "none", C["ink"], 0.8, 0))
    for t, lab in ((0, "t=0"), (EX["t"], "t=5"), (15, "t=15")):
        hi = t == EX["t"]
        o.append(text(rx - 4, ry + t * rowh + rowh - 1, lab, 8.5, "end", True,
                      fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    o.append(text(rx, ry + 16 * rowh + 12, "[k_vnni.hpp:388-390, 399]", 8.5, mono=True,
                  fill=C["cite"]))
    boxes.append(("rows[BLOCK_TOKENS_16] (rows[t] = the 128 bf16 of token t)",
                  "k_vnni.hpp:388-390, 399"))
    notes = ["1 row = 128 bf16 = 256 B", "= 4 steps of 64 B", "(STEP_DIMS_32 bf16 each)",
             "token 37 = rows[5]:", "thick outline", "null for an absent token",
             "(its bit of present clear)"]
    for s in notes:
        _w(s, 9, 144, where="d7a rows notes")
    o.append(lines(rx + 4 * segw + 12, ry + 10, notes, 9, 12, fill=C["ink"]))
    # present
    px, py, pw, ph = 400, A - 10, 280, 122
    o.append(rect(px, py, pw, ph, "#fff", C["ink"], 1.2, 5))
    o.append(text(px + 10, py + 16, "present: __mmask16", 11, mono=True, weight=600))
    o.append(text(px + 10, py + 30, "bit t set = token c * 16 + t is in the save", 9.5,
                  fill=C["muted"]))
    body, bx_end = bit_row(px + 12, py + 38, "1" * 16, 11, 1, C["vnni_fill"], C["vnni"],
                           group=0)
    o.append(body)
    o.append(text(px + 12 + 5, py + 60, "t = 0", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(px + 12 + 15 * 12 + 5, py + 60, "t = 15", 8.5, "middle", True,
                  fill=C["muted"]))
    pl = ["= FULL_BLOCK_0XFFFF: every caller at the head",
          "bit clear: rows[t] may be null, r[t] = 0 (403-407)",
          "partial: masked stores, present lanes only (414-417)"]
    for s in pl:
        _w(s, 9, pw - 20, where="d7a present")
    o.append(text(px + 10, py + 78, pl[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(px + 10, py + 92, pl[1:], 9, 12, fill=C["muted"]))
    o.append(cite(px + pw - 4, py + ph - 4, "k_vnni.hpp:382-383, 398; 83-84"))
    boxes.append(("present (__mmask16)", "k_vnni.hpp:382-383, 398; 83-84"))

    # ---- the loads: rows[] -> r[t] ----------------------------------------------
    ax = rx + 46
    ly0 = ry + 16 * rowh + 16
    B = ly0 + 90                                  # section B top (headers)
    gy = B + 16                                   # grid top
    o.append(arrow(fid, "ink", [(ax, ly0), (ax, gy - 4)], C["ink"], 1.4))
    ll = ["16 loads x 64 B, one per present row:",
          "_mm512_loadu_si512(rows[t] + s * STEP_DIMS_32)",
          "-> r[t]; absent token: _mm512_setzero_si512()"]
    o.append(text(ax + 10, ly0 + 14, ll[0], 9.5, weight=600, fill=C["ink"]))
    o.append(lines(ax + 10, ly0 + 27, ll[1:], 9, 12, mono=True))
    o.append(text(ax + 10, ly0 + 63, "[k_vnni.hpp:403-407]", 8.5, mono=True, fill=C["cite"]))

    # ---- section B: the two register grids ---------------------------------------
    gx1, gx2 = 44, 352
    h1 = ["r[t] after the loads:", "register t = token 32 + t, lane = dp"]
    h2 = ["r[dp] after the transpose:", "register dp = pair row, lane = t"]
    for s_ in h1:
        _w(s_, 10, gx2 - 2 - ax - 10, where="d7a h1")
    for s_ in h2:
        _w(s_, 10, W - gx2, where="d7a h2")
    o.append(lines(ax + 10, B - 11, h1, 10, 11, weight=700))
    o.append(lines(gx2 - 2, B - 11, h2, 10, 11, weight=700))
    o.append(dword_grid(gx1, gy, C["rm_fill"], C["rm"], hi_row=EX["t"],
                        hi_cell=(EX["t"], EX["dp"]), row_labels=(0, EX["t"], 15),
                        col_labels=(0, EX["dp"], 15), row_prefix="t="))
    o.append(dword_grid(gx2, gy, C["vnni_fill"], C["vnni"], hi_row=EX["dp"], hi_col=EX["t"],
                        hi_cell=(EX["dp"], EX["t"]), row_labels=(0, EX["dp"], 15),
                        col_labels=(0, EX["t"], 15), row_prefix="dp="))
    boxes.append(("r[BLOCK_TOKENS_16] (__m512i, 16 registers of 16 dwords)",
                  "k_vnni.hpp:402-408"))
    o.append(cite(gx1 + GRID, gy + GRID + 10, "k_vnni.hpp:402-407"))
    # the right grid's citation sits left of the stores arrow (x = gx2 + GRID - 12)
    o.append(cite(gx2 + GRID - 18, gy + GRID + 10, "k_vnni.hpp:408"))
    # the transpose arrow between the grids
    my = gy + GRID / 2
    o.append(arrow(fid, "vnni", [(gx1 + GRID + 4, my), (gx2 - 28, my)], C["vnni"], 1.6))
    mx = (gx1 + GRID + 4 + gx2 - 28) / 2
    gap = gx2 - 28 - (gx1 + GRID + 4)
    tl = ["transpose_16x16_", "epi32(r)"]
    for s in tl:
        _w(s, 9, gap, True, "d7a transpose")
    o.append(text(mx, my - 30, tl[0], 9, "middle", True, fill=C["vnni"], weight=600))
    o.append(text(mx, my - 19, tl[1], 9, "middle", True, fill=C["vnni"], weight=600))
    o.append(text(mx, my - 7, "16 x 16 dwords", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 16, "in place: 4 stages,", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 27, "64 shuffles", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 39, "[k_vnni.hpp:314-341]", 8.5, "middle", True, fill=C["cite"]))
    boxes.append(("transpose_16x16_epi32(r)", "k_vnni.hpp:314-341"))
    # under-grid captions
    u = gy + GRID + 24
    o.append(text(gx1, u, "lane dp = dims 64 + 2 dp, 65 + 2 dp", 9, fill=C["muted"]))
    o.append(text(gx1, u + 12, "r[5] lane 3 = dims 70, 71 of token 37 (blue)", 9,
                  fill=C["ink"]))
    o.append(text(gx2, u, "lane t = token 32 + t", 9, fill=C["muted"]))
    o.append(text(gx2, u + 12, "r[3] lane 5 = the same dword", 9, fill=C["ink"]))

    # ---- section C: the stores -> panel (2,2) #10, and the block ----------------
    sx = gx2 + GRID - 12
    sy0 = u + 20
    Pn = sy0 + 56                                   # panel top
    # the stores leave the r[dp] grid: the arrow starts at its bottom edge
    o.append(arrow(fid, "vnni", [(sx, gy + GRID + 2), (sx, Pn - 4)], C["vnni"], 1.6))
    sl = ["16 stores x 64 B:", "_mm512_storeu_si512(", "panel + dp * ROW_ELEMS_32, r[dp])"]
    for s in sl[1:]:
        _w(s, 9, W - sx - 20, True, "d7a stores")
    o.append(text(sx + 10, sy0 + 10, sl[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(sx + 10, sy0 + 23, sl[1:], 9, 12, mono=True))
    o.append(text(sx + 10, sy0 + 47, "[k_vnni.hpp:410-413]", 8.5, mono=True, fill=C["cite"]))
    pxp, pwp, php = gx2, GRID, GRID
    o.append(panel_lines(pxp, Pn, pwp, php, ["vnni"] * 16, hi_rows=[EX["dp"]]))
    lh = php / 16
    for dp in range(16):
        hi = dp == EX["dp"]
        o.append(text(pxp - 4, Pn + dp * lh + 8, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if hi else C["muted"], weight=600 if hi else None))
    # the dword of the worked example inside pair row 3
    o.append(rect(pxp + EX["t"] * (pwp / 16), Pn + EX["dp"] * lh, pwp / 16, lh, C["vnni"],
                  C["ink"], 1.0, 0))
    o.append(cite(pxp + pwp, Pn + php + 10, "k_vnni.hpp:409"))
    boxes.append(("panel (2,2) #10 = panel (s, c) of block c", "k_vnni.hpp:409; 29-30, 78-82"))
    nx = pxp + pwp + 10
    pn = ["panel (2,2) #10", "= plane + (s * TOKEN_BLOCKS_4", "  + c) * PANEL_ELEMS_512"]
    for s in pn:
        _w(s, 9, W - nx - 10, True, "d7a panel note")
    o.append(text(nx, Pn + 12, pn[0], 10, mono=True, weight=700))
    o.append(lines(nx, Pn + 26, pn[1:], 9, 12, mono=True))
    o.append(text(nx, Pn + 50, "[k_vnni.hpp:409]", 8.5, mono=True, fill=C["cite"]))
    wn = ["pair row 3 <- r[3]:", "dims 70, 71 of tokens 32..47;",
          "dword 5 = token 37, byte 10452", "(the B1 worked example)"]
    for s in wn:
        _w(s, 9, W - nx - 10, where="d7a worked")
    o.append(text(nx, Pn + 74, wn[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(nx, Pn + 87, wn[1:], 9, 12, fill=C["ink"]))
    o.append(text(nx, Pn + 123, "[k_vnni.hpp:132-141]", 8.5, mono=True, fill=C["cite"]))
    # the block at the left: x DIM_STEPS_4 (the title sits under the cells, so
    # the link from cell (2,2) can leave its top edge)
    bx0 = 20
    o.append(text(bx0, Pn + 72, "the block: x DIM_STEPS_4 = 4 steps s", 10, weight=700))
    mw, mh, mg = 58, 40, 8
    for s in range(4):
        x = bx0 + 24 + s * (mw + mg)
        hi = s == EX["s"]
        o.append(rect(x, Pn + 16, mw, mh, C["vnni_fill"], C["vnni"], 2.0 if hi else 1.0, 3))
        o.append(text(x + mw / 2, Pn + 16 + 17, f"({s},2)", 9, "middle", True))
        o.append(text(x + mw / 2, Pn + 16 + 31, f"#{4 * s + 2}", 8.5, "middle", True,
                      fill=C["muted"]))
    cx22 = bx0 + 24 + EX["s"] * (mw + mg) + mw / 2       # the cell's centre x
    over_y = Pn - 10
    # the link leaves cell (2,2) at its top and enters the panel at its top edge
    o.append(arrow(fid, "muted", [(cx22, Pn + 16), (cx22, over_y), (pxp + 48, over_y),
                                  (pxp + 48, Pn - 2)], C["muted"], 1.2, "4 3"))
    o.append(text(cx22 + 8, over_y - 4, "s = 2 ->", 8.5, fill=C["muted"]))
    bl = ["4 steps x 16 pair rows =",
          "64 whole-line stores = 4 KiB:",
          "the block's 4 panels (s, 2),",
          "each line written once, whole"]
    for s in bl:
        _w(s, 9.5, cx22 - 6 - bx0, where="d7a block")
    o.append(text(bx0, Pn + 92, bl[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(bx0, Pn + 105, bl[1:], 9, 12, fill=C["ink"]))
    o.append(text(bx0, Pn + 153, "[k_vnni.hpp:401, 409; 390-393]", 8.5, mono=True,
                  fill=C["cite"]))
    H = int(Pn + php + 26)
    cap = ("Updates B4: step 2 of B4 calls store_block once with FULL_BLOCK_0XFFFF, and "
           "page::set_k_block makes the same call for a run of 16 tokens; this figure opens "
           "that call for one dimension step on the worked example (block 2, step s = 2). "
           "Look at the two grids. The 16 loads put token 37's 16 dimension pairs into "
           "register r[5]. The transpose moves them into lane 5 of every register. The 16 "
           "whole-line stores write register r[dp] as pair row dp of panel (2,2) #10. So "
           "dims 70, 71 of token 37 land in dword 5 of pair row 3 (byte 10452 of B1).")
    legend = [
        ("box", "white box, ink outline: the function cell store_block(dst, c, present, "
                "rows) and the input present: __mmask16; the name in bold monospace, the "
                "description in grey sans-serif"),
        ("rm", "orange: the row-major side: the 16 native rows rows[t] in dimension order "
               "(4 steps of 64 B each) and the r[t] register grid after the 16 loads"),
        ("vnni", "blue: the VNNI side: the 16 set bits of present, the r[dp] register grid "
                 "after the transpose, the 16 pair rows of panel (2,2) #10 and the block's "
                 "4 panels (s, 2), with cell (2,2) outlined heavier (the step this figure "
                 "follows); blue text = the step s = 2, the transpose, the stores and the "
                 "pair row of the worked example"),
        ("solid blue cell, ink outline: the worked example's dword, dims 70, 71 of token "
         "37: r[5] lane 3 after the loads, r[3] lane 5 after the transpose, dword 5 of "
         "pair row 3 in panel (2,2) #10", C["vnni"], C["ink"], False, False),
        ("blue frame: the column s = 2 of rows[], the dimension step this figure follows",
         "none", C["vnni"], False, False),
        ("ink outline: the frame of rows[], of each register grid and of the panel, and "
         "the highlighted row or column of the worked example: row t = 5 of rows[] and "
         "of r[t] (token 37), register dp = 3 and lane t = 5 of r[dp], pair row 3 of the "
         "panel", "none", C["ink"], False, False),
        ("arrow", "ink arrow: the 16 loads, rows[t] + s * STEP_DIMS_32 -> r[t]"),
        ("blue arrow: transpose_16x16_epi32, r[t] -> r[dp], and the 16 whole-line stores, "
         "r[dp] -> panel (2,2) #10", "arrow", C["vnni"]),
        ("arrow_muted", "grey dashed arrow: cell (2,2) of the block -> the panel it names, "
                        "panel (2,2) #10 (s = 2)"),
        ("font_mono", "monospace = store_block and present, the intrinsic calls, the t, dp "
                      "and s labels, 'panel (2,2) #10' with its address, and the cell "
                      "labels of the block"),
        ("font_sans", "sans-serif = what store_block does, the worked-example header, the "
                      "section titles, the drawing titles, the load, transpose and store "
                      "descriptions, and the notes under the grids and the panel"),
        ("font_cite", "small grey monospace = the lines that define a box, a drawing or a "
                      "step (file:line)"),
        ("font_tag", "bold 'new' = store_block is added by this PR"),
    ]
    return figure(fid, W, H, "store_block: one dimension step of the whole-block save on the "
                  "worked example", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# d7b: the write pattern, the branch on `present`, and the callers


def fig_b():
    fid = "k_vnni-d7b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "muted": C["muted"], "pend": C["pend"]})]
    o.append(text(20, 16, "the write pattern of a full block, the branch on present, and who "
                  "calls store_block", 11, weight=700))
    # ---- section 1: the write pattern of one panel -------------------------------
    T = 44
    gx1, gx2, gy = 44, 352, T + 28
    # each drawing is ONE of the block's 4 panels (1 KiB); the counts in the
    # text below are per block (4 panels, 64 lines, 4 KiB)
    o.append(text(20, T, "store_row x 16, one per token (B4 step 3)", 10, weight=700))
    o.append(text(20, T + 11, "one of the block's 4 panels (s, 2) = 1 KiB of its 4 KiB", 9,
                  fill=C["muted"]))
    o.append(text(gx2 - 2, T, "store_block, a full block (this unit)", 10, weight=700))
    o.append(text(gx2 - 2, T + 11, "the same panel (s, 2) = 1 KiB of the block's 4 KiB", 9,
                  fill=C["muted"]))
    o.append(dword_grid(gx1, gy, C["vnni_fill"], C["ink"], row_labels=(0, 15),
                        col_labels=(0, 15), row_prefix="dp=", col_prefix="t="))
    o.append(panel_lines(gx2, gy, GRID, GRID, ["vnni"] * 16))
    for dp in (0, 15):
        o.append(text(gx2 - 4, gy + dp * CELL + 8, f"dp={dp}", 8.5, "end", True,
                      fill=C["muted"]))
    o.append(cite(gx1 + GRID, gy + GRID + 10, "k_vnni.hpp:349-362"))
    o.append(cite(gx2 + GRID, gy + GRID + 10, "k_vnni.hpp:410-413"))
    u = gy + GRID + 24
    l1 = ["64 scatters per block (4 per token),",
          "each writing 4 B into 16 lines: every one",
          "of the block's 64 lines receives",
          "16 partial writes"]
    l2 = ["64 whole-line stores per block",
          "(16 per step x 4 steps): each of the",
          "64 lines is written once, whole"]
    for s in l1 + l2:
        _w(s, 9.5, 260, where="d7b pattern")
    o.append(text(gx1, u, l1[0], 9.5, weight=600, fill=C["ink"]))
    o.append(lines(gx1, u + 13, l1[1:], 9, 12, fill=C["ink"]))
    o.append(text(gx1, u + 50, "[k_vnni.hpp:390-393]", 8.5, mono=True, fill=C["cite"]))
    o.append(text(gx2, u, l2[0], 9.5, weight=600, fill=C["vnni"]))
    o.append(lines(gx2, u + 13, l2[1:], 9, 12, fill=C["ink"]))
    o.append(text(gx2, u + 50, "[k_vnni.hpp:390-393]", 8.5, mono=True, fill=C["cite"]))
    boxes.append(("store_row x 16 (the per-token write pattern)", "k_vnni.hpp:349-362; 390-393"))
    boxes.append(("store_block: the full-block write pattern", "k_vnni.hpp:390-393, 410-413"))
    # between the two: the same bytes
    mx = (gx1 + GRID + gx2) / 2
    mid = ["the same bytes,", "bit-identical;", "the write", "pattern differs", ""]
    for s in mid:
        _w(s, 9.5, gx2 - 28 - gx1 - GRID, where="d7b mid")
    o.append(lines(mx, gy + 50, mid, 9.5, 13, "middle", fill=C["ink"], weight=600))
    o.append(text(mx, gy + 50 + 5 * 13 + 2, "[kv_cache.hpp:", 8.5, "middle", True,
                  fill=C["cite"]))
    o.append(text(mx, gy + 50 + 6 * 13 + 2, "2268-2269]", 8.5, "middle", True,
                  fill=C["cite"]))
    # legend
    ly = u + 62
    o.append(rect(gx1, ly, CELL, CELL, C["vnni_fill"], C["ink"], 0.6, 0))
    o.append(text(gx1 + CELL + 6, ly + 9, "one 4-byte write (one lane of a scatter)", 9.5))
    o.append(rect(gx2, ly, 40, CELL, C["vnni_fill"], C["vnni"], 1.0, 0))
    o.append(text(gx2 + 46, ly + 9, "one 64-byte line write", 9.5))

    # ---- section 2: the branch on present ----------------------------------------
    S2 = ly + 34
    o.append(text(20, S2, "the stores by present (the 16-lane mask of the block's tokens in "
                  "the save), lines 410-418", 10, weight=700))
    by = S2 + 10
    bw, bh = 320, 66
    b1 = ["_mm512_storeu_si512(panel + dp * ROW_ELEMS_32, r[dp])",
          "x 16 per step: whole lines, no mask"]
    b2 = ["_mm512_mask_storeu_epi32(.., present, r[dp]) x 16:",
          "absent lanes not written; r[t] of a null row = 0"]
    for s in b1 + b2:
        _w(s, 10, bw - 8, where="d7b branch")
    o.append(label_box(20, by, bw, bh, "present == FULL_BLOCK_0XFFFF", b1, "#fff", C["ink"],
                       11, ref="k_vnni.hpp:410-413"))
    boxes.append(("present == FULL_BLOCK_0XFFFF (the whole-line branch)", "k_vnni.hpp:410-413"))
    o.append(label_box(360, by, bw, bh, "_mm512_mask_storeu_epi32: a partial block", b2,
                       "#fff", C["ink"], 11, dash="5 3", ref="k_vnni.hpp:414-417; 403-407"))
    boxes.append(("_mm512_mask_storeu_epi32 (else: a partial block)",
                  "k_vnni.hpp:414-417; 403-407"))

    # ---- section 3: the callers and their threads ---------------------------------
    S3 = by + bh + 44
    o.append(lines(20, S3 - 2, ["callers at the head,", "each with its thread"], 10, 11,
                   weight=700))
    cy, ch = S3 + 14, 108
    c1 = ["stores the 16 rows of block c at", "once in the VNNI layout: store_block",
          "with FULL_BLOCK_0XFFFF, then", "note_k_block_saved [any thread of",
          "the window, inside its claimed unit]"]
    c2 = ["16 x load_row_major to the", "stack, then store_block (508);",
          "[main thread], the forward end:", "no reader of the block runs"]
    c3 = ["the layout test, t_k_vnni_", "layout.cpp:261: partial masks",
          "m; the only caller of the", "masked branch"]
    for s in c1 + c2:
        _w(s, 9.5, 215 - 8, where="d7b caller")
    for s in c3:
        _w(s, 9.5, 200 - 8, where="d7b caller 3")
    o.append(label_box(20, cy, 215, ch, "page::set_k_block", c1, C["soft"], C["ink"],
                       10.5, ref="kv_cache.hpp:2265-2284"))
    boxes.append(("page::set_k_block(slot, kv_head, c, rows)", "kv_cache.hpp:2265-2284"))
    o.append(text(20, cy + ch + 11, "[model.hpp:3321-3341; kv_cache.hpp:710-711]", 8.5,
                  mono=True, fill=C["cite"]))
    o.append(label_box(250, cy, 215, ch, "block_to_vnni(plane, c)", c2, C["pend_fill"],
                       C["pend"], 10.5, ref="k_vnni.hpp:497-509"))
    boxes.append(("block_to_vnni(plane, c)", "k_vnni.hpp:497-509"))
    o.append(text(250, cy + ch + 11, "[kv_cache.hpp:2206-2207]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(label_box(480, cy, 200, ch, "store_block(.., m, rows)", c3, C["soft"],
                       C["muted"], 10.5, dash="4 3", ref="t_k_vnni_layout.cpp:261"))
    boxes.append(("store_block(blk->plane.as_view(), c, __mmask16(m), rows) (the layout test)",
                  "t_k_vnni_layout.cpp:261"))
    # arrows from the callers up to the branch they reach
    bb = by + bh
    o.append(arrow(fid, "ink", [(160, cy), (160, bb + 4)], C["ink"], 1.4))
    o.append(text(166, bb + 28, "FULL_BLOCK_0XFFFF (2283)", 9, mono=True, fill=C["ink"],
                  weight=600))
    o.append(arrow(fid, "pend", [(330, cy), (330, bb + 4)], C["pend"], 1.4))
    o.append(text(336, bb + 28, "FULL_BLOCK_0XFFFF (508)", 9, mono=True, fill=C["pend"],
                  weight=600))
    o.append(arrow(fid, "muted", [(580, cy), (580, bb + 4)], C["muted"], 1.2, "4 3"))
    o.append(text(586, bb + 28, "m: partial masks", 9, mono=True, fill=C["muted"]))
    H = int(cy + ch + 20)
    cap = ("Updates B4: the comparison that the comment of store_block makes with step 3 "
           "of B4 (store_row), and the callers of B5 that reach store_block. Left: 16 "
           "store_row calls write 4 bytes into every line, 16 times per line. Right: "
           "store_block writes each line once, whole. The bytes are bit-identical "
           "(kv_cache.hpp:2268-2269). Both callers at the head pass FULL_BLOCK_0XFFFF, so "
           "the masked branch runs only in the test.")
    legend = [
        ("blue cells, ink outline: the left panel (s, 2) as 16 x 16 dwords, one 4-byte "
         "write each (one lane of a store_row scatter)", C["vnni_fill"], C["ink"], False,
         False),
        ("vnni", "blue lines, blue outline: the right panel (s, 2) as 16 whole lines, one "
                 "64-byte line write each (store_block); blue text = the count of "
                 "whole-line stores per block"),
        ("thin ink frame: the outline of each panel drawing", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the branch present == FULL_BLOCK_0XFFFF, the "
                "whole-line stores; the name in bold monospace, the description in grey "
                "sans-serif"),
        ("idle", "white box, ink dashed outline: the else branch _mm512_mask_storeu_epi32 "
                 "(a partial block), which no caller at the head reaches"),
        ("ctx_ink", "grey fill, ink outline: the caller page::set_k_block in kv_cache.hpp, "
                    "run by any thread of the window inside its claimed unit"),
        ("pend_solid", "orange box, orange-red solid outline: the caller "
                       "block_to_vnni(plane, c), the conversion of a complete block on the "
                       "main thread; orange-red text = its FULL_BLOCK_0XFFFF call (line "
                       "508)"),
        ("grey fill, grey dashed outline: the test caller store_block(.., m, rows) in "
         "t_k_vnni_layout.cpp:261, the only caller of the masked branch",
         C["soft"], C["muted"], True, False),
        ("arrow", "ink arrow: page::set_k_block -> the branch present == FULL_BLOCK_0XFFFF "
                  "(kv_cache.hpp:2283)"),
        ("orange-red arrow: block_to_vnni(plane, c) -> the branch present == "
         "FULL_BLOCK_0XFFFF (k_vnni.hpp:508)", "arrow", C["pend"]),
        ("arrow_muted", "grey dashed arrow: the layout test -> the masked branch, with "
                        "partial masks m"),
        ("font_mono", "monospace = the two branch names, the three callers, the dp and t "
                      "labels, the FULL_BLOCK_0XFFFF arrow labels and 'm: partial masks'"),
        ("font_sans", "sans-serif = the figure title, the section headers, the two drawing "
                      "titles, the store counts, the figure's own key, the branch "
                      "descriptions and the caller descriptions"),
        ("font_cite", "small grey monospace = the lines that define a drawing, a branch or "
                      "a caller (file:line)"),
    ]
    return figure(fid, W, H, "store_block: the write pattern against store_row, the branch on "
                  "present, and the callers", "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
