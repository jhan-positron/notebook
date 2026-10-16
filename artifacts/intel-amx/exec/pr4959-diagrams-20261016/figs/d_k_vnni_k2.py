"""Change diagram of unit k2 of the PR 4959 page for h/tron/tensor/k_vnni.hpp:
Note [Row-major tail block] and row_major_row (head lines 403-439).

Adapted from exec/pr4424-diagrams-20261009/figs/d_k_vnni_k8.py (figure a);
line numbers re-derived from the PR 4959 head (6b081187e1)."""
from svg_helpers import C, arrow, cite, figure, fn_cell, label_box, lines, marker_defs, rect, text
from base_k_vnni import (BLOCK2_ROWS_SAVED, BLOCK_2, EX, KV_HEAD_0, PAGE_7, SLOT_5, _w,
                         panel_lines, plane_grid, rm_forms, token_rows)

BASE = ("Updates B1: the row-major form of B1 is opened up at panel (1,2) #6, the panel "
        "that holds token 37's row, with the address arithmetic of row_major_row and the "
        "Note's reason (4 lines per token instead of 64).")

W = 700


def fig():
    fid = "k_vnni-d2"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"]})]
    tok = EX["token"]
    p_step, t_lines = token_rows(tok)
    rmx = EX["rm"]
    forms4 = rm_forms(BLOCK2_ROWS_SAVED)
    t1 = (f"Note [Row-major tail block]: block {BLOCK_2} of the worked example in its "
          f"row-major form (rows 32..45 saved)")
    _w(t1, 11, W - 28, where="k2 title")
    o.append(text(14, 16, t1, 11, weight=700))
    o.append(text(14, 30, f"page {PAGE_7}, slot {SLOT_5}, KV head {KV_HEAD_0}; orange = "
                  f"row-major token rows, blue = VNNI pair rows, thick outline = token {tok}",
                  9, fill=C["muted"]))
    # ---- the plane's panels and panel (1,2) #6 zoomed --------------------------------
    gx, gy, cw, ch, gg = 30, 66, 40, 32, 4
    o.append(text(gx, 50, "the plane's 16 panels (as in B1)", 9.5, weight=700))
    o.append(plane_grid(gx, gy, cw, ch, states=["vnni", "vnni", "rm", "empty"], block=BLOCK_2,
                        gap=gg))
    px6, py6 = gx + BLOCK_2 * (cw + gg), gy + p_step * (ch + gg)
    o.append(rect(px6 - 1, py6 - 1, cw + 2, ch + 2, "none", C["rm"], 2, 3))
    boxes.append(("the plane's 16 panels", "k_vnni.hpp:24-30"))
    ay = py6 + ch / 2
    zx, zy, zw, zh = 400, 66, 180, 144
    o.append(arrow(fid, "rm", [(gx + 4 * cw + 3 * gg + 40, ay), (zx - 6, ay)], C["rm"], 1.4))
    al = ["1 panel ->", "PANEL_ROWS_4 = 4", "token rows of 256 B"]
    o.append(lines((gx + 4 * cw + 3 * gg + 40 + zx - 6) / 2, ay - 30, al, 9, 10, "middle",
                   fill=C["rm"], weight=600))
    o.append(text((gx + 4 * cw + 3 * gg + 40 + zx - 6) / 2, ay + 16, "[k_vnni.hpp:87-89, 408-410]",
                  8.5, "middle", True, fill=C["cite"]))
    zt = f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major form: 4 token rows x 4 lines"
    _w(zt, 10, 2 * (W - (zx + zw / 2)), where="k2 zoom title")
    o.append(text(zx + zw / 2, 52, zt, 10, "middle", weight=700))
    o.append(panel_lines(zx, zy, zw, zh, forms4[p_step], hi_rows=t_lines))
    boxes.append((f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major form", "k_vnni.hpp:405-411"))
    o.append(cite(zx + zw, zy + zh + 10, "k_vnni.hpp:405-411"))
    lh16 = zh / 16
    for r in range(4):
        tokn = 16 * BLOCK_2 + 4 * p_step + r
        yc = zy + (4 * r + 2) * lh16
        ex = tokn == tok
        lab = f"token {tokn}" + (f" (row {rmx['row']})" if ex else "")
        o.append(text(zx + zw + 6, yc + 3, lab, 9.5, mono=True,
                      fill=C["rm"] if ex else C["ink"], weight=600 if ex else None))
        o.append(text(zx + zw + 6, yc + 14, f"lines {4 * r}..{4 * r + 3}", 8.5, fill=C["muted"]))
    # ---- the data-model box and the address arithmetic ---------------------------------
    sub = [f"block {BLOCK_2} = panels #2, #6, #10, #14 = 4 KiB:",
           "tokens 32..35, 36..39, 40..43, 44..47;",
           "the same 4 KiB as the VNNI block"]
    for s in sub:
        _w(s, 10, 262, where="k2 block box")
    o.append(label_box(20, 222, 270, 76, "row-major block", sub, C["rm_fill"], C["rm"], 11,
                       ref="k_vnni.hpp:403-411"))
    boxes.append(("row-major block", "k_vnni.hpp:403-411"))
    fx = 300
    f1 = (f"row_major_row(plane, {tok}): panel (t / 4, c) = ({p_step},{BLOCK_2}) = "
          f"#{rmx['panel']}, row t % 4 = {rmx['row']}")
    f2 = (f"element ({p_step} * 4 + {BLOCK_2}) * 512 + {rmx['row']} * 128 = {rmx['elem']} "
          f"(byte {rmx['elem'] * 2}); dim {EX['dim']} at {EX['rm_dim_elem']}")
    f3 = "one token row = 4 whole 64-byte lines = Cols x sizeof(bf16) = 256 B"
    for s in (f1, f2):
        _w(s, 9, W - fx - 8, True, "k2 formula")
    _w(f3, 9, W - fx - 8, False, "k2 formula 3")
    o.append(text(fx, 232, f1, 9, mono=True))
    o.append(text(fx, 244, f2, 9, mono=True))
    o.append(text(fx, 256, f3, 9, fill=C["ink"]))
    o.append(text(fx, 268, "[k_vnni.hpp:425-439, 405-408]", 8.5, mono=True, fill=C["cite"]))
    # the function cell of row_major_row
    o.append(fn_cell(fx, 276, 386, 62, "row_major_row(plane, token)",
                     ["The token's row inside a row-major block, as a typed row",
                      "view: k_row_view<Cols> (bf16 plane) or const_k_row_view<Cols>"],
                     "k_vnni.hpp:425-439", "new"))
    boxes.append(("row_major_row(plane, token)", "k_vnni.hpp:425-439"))
    o.append(text(fx, 350, "-> k_vnni_access::plane(plane) + ((t / PANEL_ROWS_4) * TOKEN_BLOCKS_4 + c)",
                  8.5, mono=True, fill=C["muted"]))
    o.append(text(fx, 361, "   * PANEL_ELEMS_512 + (t % PANEL_ROWS_4) * Cols; on a 64-byte line, not DMA",
                  8.5, mono=True, fill=C["muted"]))
    o.append(text(fx, 372, "   memory; the view does not say that the block is row-major (the caller",
                  8.5, mono=True, fill=C["muted"]))
    o.append(text(fx, 383, "   knows it from page::k_vnni_blocks) [k_vnni.hpp:425-428, 435-438]",
                  8.5, mono=True, fill=C["muted"]))
    # ---- why: 4 lines against 64 ------------------------------------------------------
    h2 = ("why (lines 412-416): one token's row costs 4 lines in the row-major form, 64 lines "
          "in the VNNI form")
    _w(h2, 10.5, W - 28, where="k2 why header")
    o.append(text(14, 406, h2, 10.5, weight=700))
    mx, my, mw, mh = 30, 426, 96, 64
    o.append(text(mx, my - 5, f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major", 8.5,
                  fill=C["muted"]))
    o.append(panel_lines(mx, my, mw, mh, forms4[p_step], hi_rows=t_lines))
    boxes.append((f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major: token {tok}'s 4 lines",
                  "k_vnni.hpp:412-414, 441-449"))
    ll = ["store_row_major / load_row_major (K3):",
          f"token {tok} = 4 whole 64-byte lines of",
          f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, one memcpy of 256 B",
          "[set_k_row on main / main helpers]"]
    for s in ll:
        _w(s, 9, 360 - 132 - 6, where="k2 why left")
    o.append(lines(132, my + 10, ll, 9, 10))
    o.append(text(132, my + 52, "[k_vnni.hpp:412-414, 441-459]", 8.5, mono=True, fill=C["cite"]))
    vx = 360
    o.append(text(vx, my - 5, f"panels (s,{BLOCK_2}), VNNI form (after block_to_vnni)", 8.5,
                  fill=C["muted"]))
    for s in range(4):
        o.append(panel_lines(vx + s * 52, my, 48, mh, ["vnni"] * 16, col=EX["t"]))
    boxes.append((f"panels (s,{BLOCK_2}), VNNI form: token {tok}'s 64 pair slots",
                  "k_vnni.hpp:412-414, 311-313"))
    rl = ["store_row / load_row:", f"token {tok} = 4 bytes in", "each of 64 lines",
          "(4 panels x 16 lines)"]
    o.append(lines(570, my + 10, rl, 9, 10))
    o.append(text(570, my + 50, "[k_vnni.hpp:412-414]", 8.5, mono=True, fill=C["cite"]))
    o.append(text(570, my + 60, "[k_vnni.hpp:311-313]", 8.5, mono=True, fill=C["cite"]))
    rd = ["the readers of an incomplete block read 4 lines per token instead of 64 as well: "
          "the row-major dotter",
          "[self_attention.hpp:2010-2017] and the FPGA staging gather [full.hpp:2757-2759] "
          "(k_vnni.hpp:414-416)"]
    for s in rd:
        _w(s, 9, W - 28, where="k2 readers")
    o.append(lines(14, 502, rd, 9, 10, fill=C["muted"]))
    H = 520
    cap = ("Updates B1: the row-major form of B1, opened up at panel (1,2) #6 of block 2 "
           "while rows 32..45 are saved. Token 37 owns 4 whole lines (256 bytes) of that "
           "panel, at the address row_major_row computes: element 3200, dimension 70 at "
           "3270. So a decode-step store or a tail read touches 4 lines, not the 64 lines "
           "that the token's VNNI column costs (the four blue panels at the bottom). The "
           "view type returned is the same transfer row that store_row and load_row take.")
    legend = [
        ("rm", "orange: the row-major block 2 in the grid and its zoomed panel (1,2) #6 (4 "
               "token rows of 4 lines), and the row-major block box; orange text = token 37 "
               "(row 1) and the how-many label"),
        ("vnni", "blue: blocks 0 and 1 in the grid (converted), and the 4 panels (s,2) in the "
                 "VNNI form at the bottom (16 pair rows each)"),
        ("empty", "grey dashed: block 3 in the grid (no row saved), and the 2 unsaved rows of "
                  "panel (3,2) in the zoomed form are not drawn here (panel (1,2) is full)"),
        ("orange frame: panel (1,2) #6 in the grid, the panel that holds token 37's "
         "row-major row", "none", C["rm"], False, False),
        ("solid blue column, ink outline: token 37's 4-byte slot (t = 5) in each of the 64 "
         "VNNI lines", C["vnni"], C["ink"], False, False),
        ("ink outline, no fill: the frame of block 2 (column c = 2) in the grid, token 37's "
         "4 lines in a panel, and each panel's outline", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the function cell row_major_row(plane, token)"),
        ("orange arrow: 1 panel -> PANEL_ROWS_4 = 4 token rows, from panel (1,2) #6 to its "
         "zoomed row-major form", "arrow", C["rm"]),
        ("font_mono", "monospace = the panel indexes, the token labels, the row_major_row "
                      "arithmetic and what the function expands to"),
        ("font_sans", "sans-serif = the titles, the 'lines a..b' labels, the 'why' section "
                      "and the notes"),
        ("font_cite", "small grey monospace = the lines that define a drawing, a box or a "
                      "note (file:line)"),
        ("font_tag", "bold 'new' = row_major_row is added by this PR"),
    ]
    return figure(fid, W, H, "Note [Row-major tail block]: the row-major form of a block, "
                  "its typed row, and why", "".join(o), cap, boxes=boxes, legend=legend)
