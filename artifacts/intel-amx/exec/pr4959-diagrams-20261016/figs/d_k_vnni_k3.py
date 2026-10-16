"""Change diagram of unit k3 of the PR 4959 page for h/tron/tensor/k_vnni.hpp:
store_row_major and load_row_major (head lines 441-459).
Line numbers are head lines of PR 4959 (6b081187e1)."""
from svg_helpers import C, arrow, card_arrow, cite, figure, fn_cell, label_box, lines, marker_defs, rect, text
from base_k_vnni import BLOCK2_ROWS_SAVED, BLOCK_2, EX, _w, panel_lines, rm_forms, token_rows

BASE = ("Updates B4: steps 1 and 2 of the base sequencing diagram are drawn at the "
        "byte level: the 256-byte transfer row goes in and out of token 37's 4 lines of "
        "panel (1,2) #6 as one memcpy, and the callers that pick this pair by the block's "
        "bit are listed.")

W = 700


def _transfer_row(o, x, y, w=256, h=22):
    """A transfer row of 256 B as 4 segments of 64 B (one line each)."""
    sw = w / 4
    for s in range(4):
        o.append(rect(x + s * sw, y, sw, h, C["rm_fill"], C["rm"], 1, 0))
        o.append(text(x + s * sw + sw / 2, y + h / 2 + 3.5, f"dims {32 * s}..{32 * s + 31}", 8.5,
                      "middle", True))
    o.append(rect(x, y, w, h, "none", C["ink"], 0.9, 0))


def fig():
    fid = "k_vnni-d3"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"]})]
    tok = EX["token"]
    p_step, t_lines = token_rows(tok)
    forms4 = rm_forms(BLOCK2_ROWS_SAVED)
    # ---- 1. store_row_major --------------------------------------------------------
    o.append(text(14, 18, "1  store_row_major(plane, 37, src): one memcpy of 256 B into the "
                  "token's 4 lines (worked example)", 11.5, weight=700))
    o.append(text(14, 31, "[main / main helpers] via page::set_k_row when the block's bit is "
                  "clear; the same lines the row-major layout's store writes", 9,
                  fill=C["muted"]))
    o.append(text(14, 42, "[k_vnni.hpp:441-449; kv_cache.hpp:2296-2303]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(label_box(14, 56, 130, 64, "src", ["const_k_row_view<128>", "256 B, any alignment"],
                       "#fff", C["ink"], 10.5, ref="k_vnni.hpp:447"))
    boxes.append(("src (const_k_row_view<Cols, Aligned, Dma>)", "k_vnni.hpp:447; 229-230"))
    _transfer_row(o, 160, 70)
    o.append(text(160, 64, "one token's row in dimension order", 8.5, fill=C["muted"]))
    px, py, pw, ph = 490, 56, 120, 96
    o.append(text(px + pw / 2, py - 4, f"panel ({p_step},{BLOCK_2}) #{EX['rm']['panel']}", 9,
                  "middle", True, fill=C["muted"]))
    o.append(panel_lines(px, py, pw, ph, forms4[p_step], hi_rows=t_lines))
    for r in range(4):
        tokn = 32 + 4 * p_step + r
        o.append(text(px + pw + 4, py + (4 * r + 2.6) * ph / 16, f"token {tokn}", 8.5, mono=True,
                      fill=C["rm"] if tokn == tok else C["muted"]))
    boxes.append((f"panel ({p_step},{BLOCK_2}) #{EX['rm']['panel']}: token {tok}'s 4 lines",
                  "k_vnni.hpp:405-411"))
    o.append(card_arrow(fid, "rm", [(416, 81), (px - 2, 81)], C["rm"],
                        "memcpy 256 B", 0, -8, 1.6, size=9))
    o.append(lines(160, 104, ["row_major_row(dst, 37).data = plane + 3200: the 4 whole lines",
                              "4..7 of panel #6 (line 1 of token 37's row is dims 32..63)"],
                   9, 11, fill=C["ink"]))
    o.append(text(160, 130, "[k_vnni.hpp:448, 429-439]", 8.5, mono=True, fill=C["cite"]))
    o.append(fn_cell(14, 150, 400, 62, "store_row_major",
                     ["One token's row into its row-major block: 4 whole",
                      "64-byte lines, the same lines the row-major layout's store writes"],
                     "k_vnni.hpp:441-449", "new"))
    boxes.append(("store_row_major", "k_vnni.hpp:441-449"))
    # ---- 2. load_row_major -----------------------------------------------------------------
    y2 = 234
    o.append(text(14, y2, "2  load_row_major(plane, 37, dst): the inverse, one memcpy of 256 B "
                  "out of the same 4 lines", 11.5, weight=700))
    o.append(text(14, y2 + 13, "[page copies] via page::get_k_row for a row-major block; "
                  "[block_to_vnni] for all 16 rows of a complete block", 9, fill=C["muted"]))
    o.append(text(14, y2 + 24, "[k_vnni.hpp:451-459; kv_cache.hpp:2340-2346; k_vnni.hpp:471]",
                  8.5, mono=True, fill=C["cite"]))
    py2 = y2 + 36
    o.append(text(px + pw / 2, py2 - 4, f"panel ({p_step},{BLOCK_2}) #{EX['rm']['panel']}", 9,
                  "middle", True, fill=C["muted"]))
    o.append(panel_lines(px, py2, pw, ph, forms4[p_step], hi_rows=t_lines, read_all=True))
    o.append(label_box(14, py2, 130, 64, "dst", ["k_row_view<128>", "256 B, any alignment"],
                       "#fff", C["ink"], 10.5, ref="k_vnni.hpp:457"))
    boxes.append(("dst (k_row_view<Cols, Aligned, Dma>)", "k_vnni.hpp:457; 232-233"))
    _transfer_row(o, 160, py2 + 14)
    o.append(card_arrow(fid, "rm", [(px - 2, py2 + 25), (416, py2 + 25)], C["rm"],
                        "memcpy 256 B", 0, -8, 1.6, size=9, dash="4 3"))
    o.append(fn_cell(14, py2 + 70, 400, 62, "load_row_major",
                     ["One token's row out of its row-major block",
                      "(the inverse of store_row_major)"],
                     "k_vnni.hpp:451-459", "new"))
    boxes.append(("load_row_major", "k_vnni.hpp:451-459"))
    # ---- the contrast: the VNNI pair ----------------------------------------------------
    cy = py2 + ph + 44
    o.append(rect(14, cy, 672, 40, C["vnni_fill"], C["vnni"], 1.2, 4))
    cl = ["for a converted block the same callers take store_row / load_row instead: 4 scatters "
          "(or gathers) of 16 dwords,",
          "4 bytes into each of the token's 64 lines (B4 step 4 shows the VNNI form); the "
          "transfer rows are the same types"]
    for s in cl:
        _w(s, 9, 656, where="k3 contrast")
    o.append(lines(22, cy + 15, cl, 9, 12))
    o.append(cite(682, cy + 36, "k_vnni.hpp:311-345, 229-233"))
    boxes.append(("store_row / load_row (the converted block's pair)", "k_vnni.hpp:311-345"))
    # ---- callers -------------------------------------------------------------------------
    ky = cy + 56
    o.append(text(14, ky, "who calls them: the block's bit decides", 11, weight=700))
    callers = [
        ("page::set_k_row", ["k_block_is_vnni(state_ix, i_page)", "? store_row :",
                             "store_row_major"], "kv_cache.hpp:2291-2307", C["rm_fill"], C["rm"]),
        ("page::get_k_row", ["k_block_is_vnni ? load_row :", "load_row_major"],
         "kv_cache.hpp:2334-2350", C["rm_fill"], C["rm"]),
        ("copy_storage_slot", ["a source token of a row-major", "block: store_row_major(dst,",
                               "i, row_major_row(src, j))"], "kv_cache.hpp:2722; 2777-2782",
         C["soft"], C["ink"]),
        ("block_to_vnni / block_to_rows", ["16 x load_row_major (461-476);", "16 x store_row_major",
                                           "(478-491): K4"], "k_vnni.hpp:466, 481",
         C["pend_fill"], C["pend"]),
    ]
    cw_, gap = 160, 10.67
    for i, (name, sub, ref, fill, stroke) in enumerate(callers):
        x = 14 + i * (cw_ + gap)
        _w(name, 9.5, cw_ - 8, True, f"k3 caller {name}")
        for s in sub:
            _w(s, 8.5, cw_ - 8, where=f"k3 caller sub {name}")
        o.append(rect(x, ky + 10, cw_, 70, fill, stroke, 1.2, 4))
        o.append(text(x + 6, ky + 24, name, 9, mono=True, weight=700))
        o.append(lines(x + 6, ky + 37, sub, 8.5, 10.5))
        o.append(cite(x + cw_ - 4, ky + 76, ref))
        boxes.append((name, ref))
    o.append(text(14, ky + 96, "the layout test stores a block row by row with store_row_major "
                  "and compares its bytes against store_row per token", 9, fill=C["muted"]))
    o.append(text(14, ky + 107, "after block_to_vnni [t_k_vnni_layout.cpp:293-320]", 9,
                  fill=C["muted"]))
    H = ky + 118
    cap = ("Updates B4 (steps 1 and 2): store_row_major copies the 256-byte transfer row "
           "into the 4 whole lines that row_major_row names for token 37 (lines 4..7 of "
           "panel (1,2) #6), and load_row_major copies them back. Both are one memcpy. "
           "The callers pick this pair or the VNNI pair (store_row / load_row) by the "
           "block's converted bit: set_k_row and get_k_row through k_block_is_vnni, the "
           "page copy by the source block's bit, and the conversions for all 16 rows.")
    legend = [
        ("rm", "orange: the transfer rows (4 segments of 64 B), the row-major panel (1,2) "
               "#6 with token 37's 4 lines, and the callers set_k_row / get_k_row; orange "
               "text = token 37's label and the memcpy labels"),
        ("vnni", "blue: the contrast box, the VNNI pair store_row / load_row that a "
                 "converted block takes"),
        ("pend_solid", "orange box, orange-red outline: the conversions block_to_vnni / "
                       "block_to_rows, which call this pair 16 times"),
        ("ctx_ink", "grey box, ink outline: the caller copy_storage_slot"),
        ("box", "white box, ink outline: the transfer-row views src and dst, and the two "
                "function cells; name in bold monospace, description in sans-serif"),
        ("ink outline: a panel's frame and the transfer row's frame; drawn heavier, "
         "token 37's 4 lines", "none", C["ink"], False, False),
        ("dashed ink outline round the panel: the 4 lines are read (step 2)",
         "none", C["ink"], True, False),
        ("orange arrow: memcpy(256 B), solid = the store (step 1), dashed = the load "
         "(step 2)", "arrow", C["rm"]),
        ("font_mono", "monospace = src, dst, the segment labels, the panel label, the "
                      "token labels, the address line and the caller names"),
        ("font_sans", "sans-serif = the two step titles, the thread notes, what each cell "
                      "and caller does, and the notes"),
        ("font_cite", "small grey monospace = the lines that define a box, a step or a "
                      "note (file:line)"),
        ("font_tag", "bold 'new' = store_row_major and load_row_major are added by this PR"),
    ]
    return figure(fid, W, H, "store_row_major and load_row_major: one token's row into and "
                  "out of its row-major block", "".join(o), cap, boxes=boxes, legend=legend)
