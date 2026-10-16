"""Change diagram of unit k8 of the PR 4424 page for h/tron/tensor/k_vnni.hpp:
Note [Row-major tail block] and the row-major form of a block (row_major_row,
store_row_major, load_row_major), head lines 437-493.

Two figures: k_vnni-d8a (the plane, panel (1,2) #6 in its row-major form and
why) and k_vnni-d8b (the block bit, the five callers, the three operations and
the states of a block).

Every label, count and citation comes from facts/k_vnni.json (verified claims)
or from the head file. Line numbers are head line numbers of
h/tron/tensor/k_vnni.hpp unless another file is named.
"""
import sys

from svg_helpers import (C, arrow, block_cell, cite, figure, fn_cell, label_box,
                         line, lines, marker_defs, rect, text, text_width)
from base_k_vnni import (BLOCK2_ROWS_SAVED, BLOCK_2, EX, KV_HEAD_0, PAGE_7, SLOT_5,
                         panel_grid, panel_lines, rm_forms, token_rows)

BASE = ("Updates B1: the plane gains the row-major form of one 16-token block "
        "(Note [Row-major tail block]). The same 4 panels (s, c) read as "
        "PANEL_ROWS_4 = 4 token rows of 256 bytes each, with token 37 at panel "
        "(1,2) #6, row 1. The second figure (d8b) updates B4 and B5: the three "
        "operations that read and write that form, their five callers, and the states "
        "of a block, with the hardware-attention exception.")


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _lines_w(items, size, w, where, mono=False):
    for s in items:
        _w(s, size, w, mono, where)


def _legend(o):
    t2 = (f"page {PAGE_7}, slot {SLOT_5}, KV head {KV_HEAD_0}; orange = row-major token "
          f"rows, blue = VNNI pair rows, thick outline = token {EX['token']}")
    _w(t2, 9, 700 - 40, where="legend")
    o.append(text(20, 30, t2, 9, fill=C["muted"]))


def _fig_a():
    fid = "k_vnni-d8a"
    W, H = 700, 432
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "muted": C["muted"]})]
    tok = EX["token"]                        # 37
    p_step, t_lines = token_rows(tok)        # panel step 1, lines 4..7 of panel (1,2)
    rmx = EX["rm"]                           # panel 6, row 1, element 3200
    forms4 = rm_forms(BLOCK2_ROWS_SAVED)     # rows 32..40 saved, row-major form

    # ---- title and legend -------------------------------------------------------
    t1 = (f"Note [Row-major tail block]: block {BLOCK_2} of the worked example in its "
          f"row-major form (rows 32..40 saved)")
    _w(t1, 11, W - 40, where="title")
    o.append(text(20, 16, t1, 11, weight=700))
    _legend(o)

    # ---- section 1: the plane's panels and panel (1,2) #6 in the row-major form ----
    gx, gy, cw, ch, gg = 30, 66, 40, 32, 4
    o.append(text(gx, 48, "the plane's 16 panels (as in B1)", 9.5, weight=700))
    o.append(panel_grid(gx, gy, cw, ch, hi=None, block=BLOCK_2, gap=gg))
    px6, py6 = gx + EX["c"] * (cw + gg), gy + p_step * (ch + gg)
    o.append(rect(px6 - 1, py6 - 1, cw + 2, ch + 2, "none", C["rm"], 1.8, 3))
    # how many: 1 panel -> PANEL_ROWS_4 token rows (data-44)
    ay = py6 + ch / 2
    zx, zy, zw, zh = 400, 66, 180, 144
    o.append(arrow(fid, "rm", [(244, ay), (zx - 6, ay)], C["rm"], 1.4))
    al = ["1 panel ->", "PANEL_ROWS_4 = 4", "token rows of 256 B"]
    _lines_w(al, 9, zx - 6 - 244, "arrow label")
    o.append(lines((244 + zx - 6) / 2, ay - 30, al, 9, 10, "middle", fill=C["rm"],
                   weight=600))
    o.append(text((244 + zx - 6) / 2, ay + 16, "[k_vnni.hpp:91-93, 443-445]", 8.5,
                  "middle", True, fill=C["cite"]))
    # the zoomed panel: 16 lines, 4 token rows of 4 lines
    zt = f"panel ({p_step},{BLOCK_2}) #{rmx['panel']} in its row-major form: 4 token rows x 4 lines"
    _w(zt, 10, 2 * (W - (zx + zw / 2)) , where="zoom title")
    o.append(text(zx + zw / 2, 52, zt, 10, "middle", weight=700))
    o.append(panel_lines(zx, zy, zw, zh, forms4[p_step], hi_rows=t_lines))
    boxes.append((f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major form",
                  "k_vnni.hpp:441-445"))
    o.append(cite(zx + zw, zy + zh + 10, "k_vnni.hpp:441-445"))
    lh16 = zh / 16
    for r in range(4):
        tokn = 16 * BLOCK_2 + 4 * p_step + r
        yc = zy + (4 * r + 2) * lh16
        ex = tokn == tok
        lab = f"token {tokn}" + (f" (row {rmx['row']})" if ex else "")
        _w(lab, 9.5, W - (zx + zw + 6), True, "token label")
        o.append(text(zx + zw + 6, yc + 3, lab, 9.5, mono=True,
                      fill=C["rm"] if ex else C["ink"], weight=600 if ex else None))
        o.append(text(zx + zw + 6, yc + 14, f"lines {4 * r}..{4 * r + 3}", 8.5,
                      fill=C["muted"]))
    # the address of the worked example (row_major_row, 467-471)
    fx = 296
    f1 = (f"row_major_row(plane, {tok}): panel (t / 4, c) = ({p_step}, {BLOCK_2}) = "
          f"#{rmx['panel']}, row t % 4 = {rmx['row']}")
    f2 = (f"= element ({p_step} * 4 + {BLOCK_2}) * 512 + {rmx['row']} * 128 = "
          f"{rmx['elem']} (byte {rmx['elem'] * 2}); dim {EX['dim']} at {EX['rm_dim_elem']}")
    f3 = "each token row = 4 whole 64-byte lines = Cols x sizeof(bf16) = 256 B"
    _w(f1, 9, W - fx, True, "formula 1")
    _w(f2, 9, W - fx, True, "formula 2")
    _w(f3, 9, W - fx, False, "formula 3")
    o.append(text(fx, 232, f1, 9, mono=True))
    o.append(text(fx, 244, f2, 9, mono=True))
    o.append(text(fx, 256, f3, 9, fill=C["ink"]))
    o.append(text(fx, 268, "[k_vnni.hpp:441-445, 467-471, 481]", 8.5, mono=True,
                  fill=C["cite"]))
    # the data-model box of the row-major block
    sub = [f"block {BLOCK_2} = panels #2, #6, #10, #14 = 4 KiB:",
           "tokens 32..35, 36..39, 40..43, 44..47;",
           "the same 4 KiB as the VNNI block (new)"]
    _lines_w(sub, 10, 262, "row-major block box")
    o.append(label_box(20, 213, 270, 76, "row-major block", sub, C["rm_fill"], C["rm"],
                       11, ref="k_vnni.hpp:437-445"))
    boxes.append(("row-major block", "k_vnni.hpp:437-445"))

    # ---- section 2: why, 4 lines vs 64 lines per token ---------------------------
    h2 = ("why (lines 446-450): one token's row costs 4 lines in the row-major form, "
          "64 lines in the VNNI form")
    _w(h2, 10.5, W - 40, where="why header")
    o.append(text(20, 310, h2, 10.5, weight=700))
    mx, my, mw, mh = 30, 330, 96, 64
    o.append(text(mx, my - 5, f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major", 8.5,
                  fill=C["muted"]))
    o.append(panel_lines(mx, my, mw, mh, forms4[p_step], hi_rows=t_lines))
    boxes.append((f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, row-major: token {tok}'s 4 lines",
                  "k_vnni.hpp:446-448, 474-482"))
    ll = ["store_row_major / load_row_major:",
          f"token {tok} = 4 whole 64-byte lines of",
          f"panel ({p_step},{BLOCK_2}) #{rmx['panel']}, one memcpy of 256 B",
          "[main / main helpers] via set_k_row"]
    _lines_w(ll, 9, 360 - 132 - 6, "why left")
    o.append(lines(132, my + 10, ll, 9, 10))
    o.append(text(132, my + 52, "[k_vnni.hpp:446-448, 474-492]", 8.5, mono=True,
                  fill=C["cite"]))
    vx = 360
    o.append(text(vx, my - 5, f"panels (s,{BLOCK_2}), VNNI form (after block_to_vnni)",
                  8.5, fill=C["muted"]))
    for s in range(4):
        o.append(panel_lines(vx + s * 52, my, 48, mh, ["vnni"] * 16, col=EX["t"]))
    boxes.append((f"panels (s,{BLOCK_2}), VNNI form: token {tok}'s 64 pair slots",
                  "k_vnni.hpp:446-448, 344-348"))
    rl = ["store_row / load_row:", f"token {tok} = 4 bytes in", "each of 64 lines",
          "(4 panels x 16 lines)"]
    _lines_w(rl, 9, W - 570, "why right")
    o.append(lines(570, my + 10, rl, 9, 10))
    o.append(text(570, my + 50, "[k_vnni.hpp:446-448]", 8.5, mono=True, fill=C["cite"]))
    o.append(text(570, my + 60, "[k_vnni.hpp:344-348]", 8.5, mono=True, fill=C["cite"]))
    rd = ["readers of an incomplete block read 4 lines per token instead of 64: the "
          "row-major dotter",
          "[self_attention.hpp:2027-2031] and the FPGA staging gather [full.hpp:2762] "
          "(k_vnni.hpp:448-450)"]
    _lines_w(rd, 9, W - 40, "readers note")
    o.append(lines(20, 406, rd, 9, 10, fill=C["muted"]))
    cap = ("Updates B1: the plane of B1 gains a second form for one 16-token block, "
           "the row-major form of Note [Row-major tail block], drawn for block 2 of "
           "the worked example while rows 32..40 are saved. Look at the zoomed panel: "
           "token 37 owns 4 whole lines (256 bytes) of panel (1,2) #6, so a decode-step "
           "store or a tail read touches 4 lines, not the 64 lines that the VNNI column "
           "costs. The next figure shows the operations of this form, their callers and "
           "when a block leaves it.")
    legend = [
        ("rm", "orange lines and box: the row-major form, token rows of 256 B in "
               "panel (1,2) #6 and the row-major block box; orange text = token 37 "
               "(row 1), the worked example's token, and the label of the orange arrow"),
        ("lane", "white cell, thin grey outline: a panel of the grid (the frames of block "
                 "2 and of panel (1,2) #6 are drawn over such cells)"),
        ("orange frame: panel (1,2) #6 in the grid, the panel that holds token 37's "
         "row-major row", "none", C["rm"], False, False),
        ("vnni", "blue lines: panels (s,2) in the VNNI form after block_to_vnni, "
                 "16 pair rows each"),
        ("solid blue column: token 37's 4-byte slot (t = 5) in each of the 64 VNNI "
         "lines", C["vnni"], C["ink"], False, False),
        ("ink outline, no fill: the frame of block 2 (column c = 2) in the grid, "
         "token 37's 4 lines in a panel, and each panel's outline",
         "none", C["ink"], False, False),
        ("orange arrow: 1 panel -> PANEL_ROWS_4 = 4 token rows, from panel (1,2) #6 "
         "to its zoomed row-major form", "arrow", C["rm"]),
        ("font_mono", "monospace = the panel indexes, the token labels beside the zoomed "
                      "panel (token 37 (row 1) in orange), 'row-major block' and the "
                      "row_major_row arithmetic"),
        ("font_sans", "sans-serif = the figure title and subtitle, the drawing titles, the "
                      "'lines a..b' labels, the 'why' section and the notes"),
        ("font_cite", "small grey monospace = the lines that define a drawing, a box or a "
                      "note (file:line)"),
    ]
    return figure(fid, W, H,
                  "Note [Row-major tail block]: the row-major form of a block and why",
                  "".join(o), cap, boxes=boxes, legend=legend)


def _fig_b():
    fid = "k_vnni-d8b"
    W = 700
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "muted": C["muted"], "pend": C["pend"], "hw": C["hw"]})]
    t1 = "Note [Row-major tail block], continued: the operations, and the states of a block"
    _w(t1, 11, W - 40, where="title b")
    o.append(text(20, 16, t1, 11, weight=700))
    _legend(o)

    # ---- section 3: the operations, their callers, the block bit -------------------
    h3 = ("the operations (lines 458-492) and their five callers; each checks the block "
          "bit first")
    _w(h3, 10.5, W - 40, where="ops header")
    o.append(text(20, 52, h3, 10.5, weight=700))
    by, bh = 60, 78
    bt = "k_block_is_vnni(k_state_ix(slot), i_page): bit c of k_vnni_blocks_ (acquire)"
    bs = [f"worked example: k_vnni_blocks_[{SLOT_5}] = 0b0001, bit {BLOCK_2} clear: "
          f"block {BLOCK_2} holds the row-major form",
          "copy_storage_slot and apply_page_tok read the mask itself (kv_cache.hpp:2742, "
          "2749; self_attention.hpp:2024)",
          "the operations below take the layout from the caller; the view does not say "
          "which form the block holds (454-461)"]
    _w(bt, 11, 652, True, "bit box title")
    _lines_w(bs, 10, 652, "bit box sub")
    o.append(label_box(20, by, 660, bh, bt, bs, C["blk_fill"], C["blk"], 11,
                       ref="kv_cache.hpp:2514-2518"))
    boxes.append(("k_block_is_vnni(k_state_ix(slot), i_page)", "kv_cache.hpp:2514-2518"))
    # one stem from the bit box to a rail over the callers (five sub-lines in
    # a 104 px box, so the last line clears the citation)
    cy, chh, cwid, cgap = by + bh + 34, 104, 126, 7.5
    centres = [20 + i * (cwid + cgap) + cwid / 2 for i in range(5)]
    rail_y = cy - 8
    # a plain stem to the rail; the arrowheads sit where the drops meet the boxes
    o.append(line(350, by + bh, 350, rail_y, C["ink"], 1.4))
    bl = "bit clear -> this unit; bit set -> store_row / load_row (344-380)"
    _w(bl, 9, W - 358, where="bit arrow label")
    o.append(text(358, by + bh + 11, bl, 9, fill=C["ink"], weight=600))
    o.append(line(centres[0], rail_y, centres[-1], rail_y, C["ink"], 1.2))
    for cx in centres:
        o.append(arrow(fid, "ink", [(cx, rail_y), (cx, cy - 2)], C["ink"], 1.2))
    callers = [
        ("set_k_row", ["bit set: store_row", "else store_row_major",
                       "[main / main helpers]"], "kv_cache.hpp:2247-2262"),
        ("copy_storage_slot", ["mask bit: load_row or", "store_row_major, via",
                               "row_major_row", "[scheduler, tree lock]"],
         "kv_cache.hpp:2691", "kv_cache.hpp:2691, 2747-2756"),
        ("k_row_if_row_major", ["bit set: invalid view;", "else row_major_row",
                                "in place, no copy", "[GOF staging: attention",
                                "worker or main]"],
         "kv_cache.hpp:2332-2349"),
        ("apply_page_tok", ["mask bit clear:", "row_major_row ->", "the row-major dotter",
                            "[attention worker]"], "self_attention.hpp:1856", "self_attention.hpp:1856, 2029"),
        ("get_k_row", ["bit set: load_row", "else load_row_major", "[GOF staging: attention",
                       "worker or main,", "full.hpp:2765]"], "kv_cache.hpp:2291-2306"),
    ]
    for i, (name, sub, ref, *reg) in enumerate(callers):
        x = 20 + i * (cwid + cgap)
        _w(name, 10, cwid - 8, True, f"caller {name}")
        _lines_w(sub, 9, cwid - 8, f"caller sub {name}")
        _w(ref, 8.5, cwid - 6, True, f"caller cite {name}")
        o.append(label_box(x, cy, cwid, chh, name, sub, C["soft"], C["ink"], 10, ref=ref))
        # reg: a fuller register source when the drawn cite must stay short
        boxes.append((name, reg[0] if reg else ref))
    # the three operations
    fy, fh, fw, fgap = cy + chh + 30, 62, 212, 12
    cells = [
        ("store_row_major", ["One token's row into its row-major",
                             "block: 4 whole 64-byte lines"], "k_vnni.hpp:474-482",
         ["-> row_major_row(dst, token).data,",
          "std::memcpy(Cols * sizeof(bf16) = 256 B)"]),
        ("row_major_row", ["The token's row inside a row-major",
                           "block: panel (t / 4, c), row t % 4"], "k_vnni.hpp:462-472; 458-461",
         ["-> detail::k_vnni_access::plane + offset;",
          "returns k_row_view<Cols> (bf16 plane) or",
          "const_k_row_view<Cols> (const bf16 plane):",
          "flags VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE"]),
        ("load_row_major", ["One token's row out of its row-major",
                            "block (inverse of store_row_major)"], "k_vnni.hpp:484-492",
         ["-> row_major_row(src, token).data,",
          "std::memcpy(Cols * sizeof(bf16) = 256 B)"]),
    ]
    fcx = []
    for i, (name, desc, ref, callees) in enumerate(cells):
        x = 20 + i * (fw + fgap)
        fcx.append(x + fw / 2)
        _w(name, 11.5, fw - 16, True, f"fn name {name}")
        _lines_w(desc, 9.5, fw - 16, f"fn desc {name}")
        _lines_w(callees, 9, fw - 4, f"fn callees {name}")
        o.append(fn_cell(x, fy, fw, fh, name, desc, ref, "new"))
        boxes.append((name, ref))
        o.append(lines(x + 2, fy + fh + 11, callees, 9, 10, fill=C["muted"]))
    # call arrows: caller bottom -> cell top
    cb, ct = cy + chh, fy - 2
    calls = [(0, 0, 0), (1, 1, -50), (1, 0, 30), (2, 1, 0), (3, 1, 50), (4, 2, 10)]
    for ci, fi, dx in calls:
        o.append(arrow(fid, "ink", [(centres[ci], cb), (fcx[fi] + dx, ct)], C["ink"], 1.2))

    # ---- section 4: when the block changes form ------------------------------------
    h4 = (f"when a block changes form (lines 450-456): block {BLOCK_2}'s states, the way "
          "back, the hardware-attention exception")
    _w(h4, 10.5, W - 40, where="when header")
    hy = fy + fh + 11 + 4 * 10 + 20
    o.append(text(20, hy, h4, 10.5, weight=700))
    sy, sh, sw = hy + 33, 30, 138
    sx = [20, 281, 542]
    states = [("rm", "row-major", ["rows saved one at a time", "by set_k_row ->",
                                   "store_row_major (decode)", "[main / main helpers]",
                                   "[k_vnni.hpp:439-442]"], "k_vnni.hpp:439-442"),
              ("pend", "complete, may wait", ["16 row bits set, block", "bit clear: waits for the",
                                           "forward end", "[kv_cache.hpp:692-701]"],
               "kv_cache.hpp:692-701"),
              ("vnni", "VNNI", ["block_to_vnni: 4 KiB read,", "4 KiB written; then the AMX",
                                "kernel reads the page once", "every block is VNNI",
                                "[k_vnni.hpp:450-454]"], "k_vnni.hpp:450-454")]
    for (st, lab, note, ref), x in zip(states, sx):
        o.append(block_cell(x, sy, sw, sh, st, lab))
        boxes.append((f"{lab} (block state)", ref))
        _lines_w(note[:-1], 9, sw - 2, f"state note {lab}")
        _w(note[-1], 8.5, sw - 2, True, f"state cite {lab}")
        o.append(lines(x, sy + sh + 10, note[:-1], 9, 10, fill=C["ink"]))
        o.append(text(x, sy + sh + 10 + 10 * (len(note) - 1), note[-1], 8.5, mono=True,
                      fill=C["cite"]))
    ty = sy + sh / 2
    # row-major -> complete, may wait
    o.append(arrow(fid, "pend", [(sx[0] + sw, ty), (sx[1] - 2, ty)], C["pend"], 1.4))
    g1 = (sx[0] + sw + sx[1]) / 2
    o.append(text(g1, ty - 7, "16th row saved", 9, "middle", fill=C["pend"], weight=600))
    o.append(text(g1, ty + 17, "[kv_cache.hpp:692-701]", 8.5, "middle", True,
                  fill=C["cite"]))
    # complete, may wait -> VNNI
    o.append(arrow(fid, "vnni", [(sx[1] + sw, ty), (sx[2] - 2, ty)], C["vnni"], 1.4))
    g2 = (sx[1] + sw + sx[2]) / 2
    o.append(text(g2, ty - 7, "forward end", 9, "middle", fill=C["vnni"], weight=600))
    o.append(lines(g2, ty + 17, ["block_to_vnni", "[main thread]"], 9, 10, "middle",
                   fill=C["vnni"], weight=600))
    o.append(lines(g2, ty + 37, ["[k_vnni.hpp:450-453]", "[kv_cache.hpp:2206-2207]"], 8.5,
                   10, "middle", True, fill=C["cite"]))
    # the whole-block save: VNNI at once, no conversion
    wy, wh = sy + sh + 10 + 5 * 10 + 10, 36
    wl = ["whole-block save: set_k_block -> store_block writes the VNNI form at once "
          "(no conversion);",
          "note_k_block_saved sets the bit (release) [any window thread]"]
    _lines_w(wl, 9, 480 - 12, "whole-block box")
    o.append(rect(20, wy, 480, wh, C["soft"], C["ink"], 1.2, 4))
    o.append(lines(26, wy + 13, wl, 9, 11))
    o.append(cite(496, wy + wh - 4, "kv_cache.hpp:727; 2277-2284"))
    boxes.append(("whole-block save: set_k_block -> store_block, note_k_block_saved",
                  "kv_cache.hpp:727; 705-708; 2277-2284, 2195-2200"))
    o.append(arrow(fid, "ink", [(500, wy + wh / 2), (690, wy + wh / 2), (690, ty),
                                 (sx[2] + sw + 2, ty)], C["ink"], 1.4))
    o.append(text(686, wy + 10, "at once", 8.5, "end", fill=C["ink"], weight=600))
    # the return edge: a VNNI block goes back to row-major through block_to_rows
    # (k_forget_row, copy_storage_slot: the next figure), drawn above the band
    ry = hy + 25
    o.append(arrow(fid, "muted", [(sx[2] + sw / 2, sy), (sx[2] + sw / 2, ry),
                                  (sx[0] + sw / 2, ry), (sx[0] + sw / 2, sy - 2)],
                   C["muted"], 1.2, "5 3"))
    rl = ("back: k_forget_row / copy_storage_slot -> block_to_rows (next figure) "
          "[kv_cache.hpp:2472-2477, 2741-2746]")
    _w(rl, 8.5, sx[2] - sx[0], where="return edge label")
    o.append(text(sx[1] + sw / 2, hy + 16, rl, 8.5, "middle", fill=C["muted"], weight=600))
    # the fourth state (k_vnni-sequencing-40, Note [Row-major blocks under
    # hardware attention]): the rows of a hardware-scored operation get no
    # bits, so the block never leaves the row-major form; the edge from
    # 'row-major' runs along the left margin
    hy2 = wy + wh + 28
    o.append(text(24, hy2 - 8, "cached_operation_uses_hw: the rows a short run saves for a "
                  "hardware-scored operation", 9, fill=C["hw"], weight=600))
    o.append(block_cell(20, hy2, 200, sh, "hw", "hardware-scored: no bits", 10))
    boxes.append(("hardware-scored: no bits (block state)", "kv_cache.hpp:729-735"))
    hn = ["save_k records no row bits for its short runs and queues no block; the block stays",
          "row-major and a page copy does not convert it; the CPU scores only the tail above",
          "the engagement point, row by row when a tail token lies in a row-major block"]
    _lines_w(hn, 9, W - 230, "hw note")
    o.append(lines(230, hy2 + 10, hn, 9, 10, fill=C["ink"]))
    o.append(text(230, hy2 + 41, "[kv_cache.hpp:729-744; model.hpp:3420-3426]", 8.5,
                  mono=True, fill=C["cite"]))
    o.append(arrow(fid, "hw", [(sx[0], ty), (10, ty), (10, hy2 + sh / 2), (18, hy2 + sh / 2)],
                   C["hw"], 1.4))
    H = int(hy2 + 50)
    cap = ("Updates B4 and B5: the three operations of the row-major form and the five "
           "callers that read the block bit first to choose this form: set_k_row, "
           "get_k_row and k_row_if_row_major through k_block_is_vnni, copy_storage_slot "
           "and apply_page_tok through the block mask itself (kv_cache.hpp:2709-2711, "
           "2742, 2749; self_attention.hpp:2021, 2024). The band at the bottom shows when "
           "the block leaves this form: block_to_vnni at the forward end, or at once after "
           "a whole-block save. The dashed edge is the way back (block_to_rows, drawn in "
           "the next figure). The yellow cell is the hardware-attention exception: the "
           "rows of a hardware-scored operation get no bits, so their block never leaves "
           "the row-major form.")
    legend = [
        ("blk", "pink: the block bit box k_block_is_vnni(k_state_ix(slot), i_page) of "
                "k_vnni_blocks_; bit 2 clear in the worked example"),
        ("ctx_ink", "grey fill, ink outline: the five callers (set_k_row, "
                    "copy_storage_slot, k_row_if_row_major, apply_page_tok, get_k_row) "
                    "and the whole-block save band"),
        ("box", "white box, ink outline: the three operations store_row_major, "
                "row_major_row, load_row_major; name in bold monospace, description "
                "in sans-serif under it"),
        ("rm", "orange: the row-major state of block 2, rows saved one at a time by "
               "set_k_row -> store_row_major"),
        ("pend", "orange box, orange-red dashed outline (complete, may wait): 16 row bits "
                 "set, block bit clear, the block waits for the forward end; orange-red "
                 "text = the 16th-row-saved edge"),
        ("vnni", "blue (VNNI): the converted state after block_to_vnni; blue text = the "
                 "forward-end edge, block_to_vnni on the main thread"),
        ("hw", "yellow (hardware-scored: no bits): the block of a hardware-scored "
               "operation (cached_operation_uses_hw) never leaves the row-major form; "
               "yellow text = its label"),
        ("arrow", "ink arrow: the bit check to each caller, a caller's call of an "
                  "operation, and the 'at once' edge of the whole-block save to VNNI"),
        ("arrow_muted", "grey dashed arrow: the way back, k_forget_row / "
                        "copy_storage_slot -> block_to_rows (next figure)"),
        ("orange-red arrow: 16th row saved, row-major -> complete, may wait",
         "arrow", C["pend"]),
        ("blue arrow: forward end, block_to_vnni on the main thread, complete -> VNNI",
         "arrow", C["vnni"]),
        ("yellow arrow: the hardware-attention exception, row-major -> "
         "hardware-scored: no bits", "arrow", C["hw"]),
        ("font_mono", "monospace = the names of the five callers, the three operations and "
                      "k_block_is_vnni, and the four state names in the state boxes "
                      "(row-major; complete, may wait; VNNI; hardware-scored: no bits)"),
        ("font_sans", "sans-serif = the figure title and subtitle, the section titles, what "
                      "each caller and operation does, the edge labels and the notes under "
                      "the states"),
        ("font_cite", "small grey monospace = the lines that define a cell, a state or an "
                      "edge (file:line)"),
        ("font_tag", "bold 'new' = the three operations are added by this PR"),
    ]
    return figure(fid, W, H,
                  "The operations of the row-major form, their callers, and the states of a block",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
