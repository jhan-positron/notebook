"""Change diagram of unit k5 of the PR 4956 k_vnni.hpp page: the internal
helpers pair_base and pair_row_offsets (head lines 226-250).

One figure, k_vnni-d5: the byte address of one token's 16 pair slots per
step, with the worked example's arithmetic. Line numbers are head lines of
PR 4956 (a5697f86d3). The worked example is the page's (token 37 = block 2,
t = 5; dimension 70 = step 2, pair 3).
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, lines, marker_defs, rect,
                         text, text_width)
from base_k_vnni import EX, panel_lines

BASE = ("Updates B1: the index map of B1 becomes byte arithmetic (pair_base points at "
        "a token's column t (i % 16) of panel (s, c), pair_row_offsets steps down the "
        "panel's 16 pair rows); together they address the 16 slots per step that "
        "store_row scatters and load_row gathers (B4).")

S, TOKEN = EX["s"], EX["token"]                       # 2, 37
C_BLK, T = TOKEN // 16, TOKEN % 16                    # 2, 5
PAIR_BASE_B = ((S * 4 + C_BLK) * 256 + T) * 4         # 10260
DP = EX["dp"]                                         # 3
LANE_B = DP * 16 * 4                                  # 192
BYTE = PAIR_BASE_B + LANE_B                           # 10452
assert BYTE == EX["byte"] == 2 * EX["index"]

W = 700


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def fig():
    fid = "k_vnni-d5"
    W_, H = W, 370
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    hdr = ("the two internal helpers of namespace k_vnni::detail; worked example: "
           "token 37 (block 2, t = 5), step s = 2, pair dp = 3")
    _w(hdr, 9.5, W - 32, where="d5 header")
    o.append(text(16, 14, hdr, 9.5, fill=C["muted"]))
    o.append(text(16, 32, "pair_base + pair_row_offsets: the byte address of one token's "
                  "16 pair slots per step", 11, weight=700))
    cw, ch = 330, 70
    cells = [
        (52, "pair_base(plane, s, token)",
         ["Byte address of dimension pair 0 of step s for a token:",
          "panel (s, c) plus the token's column t (i % 16)",
          "-> char* / const char*: plane + ((s * 4 + c) * 256 + t) * 4"],
         "k_vnni.hpp:227-239",
         ["callers: store_row 264, load_row 281:",
          "DIM_STEPS_4 = 4 calls per row (one per step s)"]),
        (148, "pair_row_offsets()",
         ["Dword offsets of the 16 pair rows of one panel",
          "(64 bytes = 16 dwords apart): the scatter / gather index",
          "-> __m512i: lane i = i * ROW_DWORDS_16 = 0, 16, ..., 240"],
         "k_vnni.hpp:240-248",
         ["callers: store_row 261, load_row 278:",
          "1 call per row: the index vector of the scatter / gather"]),
    ]
    for y, name, desc, ref, callers in cells:
        for d in desc:
            _w(d, 9.5, cw - 16, where=f"desc {name}")
        for d in callers:
            _w(d, 9, cw - 4, where=f"callers {name}")
        o.append(fn_cell(16, y, cw, ch, name, desc, ref, "new"))
        boxes.append((name, ref))
        o.append(lines(18, y + ch + 11, callers, 9, 10.5, fill=C["muted"]))
    px, py, pw, ph = 428, 70, 224, 176
    o.append(panel_lines(px, py, pw, ph, ["vnni"] * 16, hi_rows=[DP], col=T))
    o.append(text(px + pw + 4, py - 6, "lane i", 8.5, fill=C["muted"]))
    for i in range(16):
        o.append(text(px + pw + 4, py + i * 11 + 8, f"+{i * 64} B", 8.5, mono=True,
                      fill=C["vnni"] if i == DP else C["muted"]))
    col_x = px + T * (pw / 16) + pw / 32
    o.append(arrow(fid, "ink", [(346, 72), (372, 72), (372, 50), (col_x, 50), (col_x, py - 2)],
                   C["ink"], 1.4))
    lab_a = f"1 call -> 1 address: plane + {PAIR_BASE_B} B = dword {T} of pair row 0"
    _w(lab_a, 9, 700 - 378, where="label a")
    o.append(text(378, 45, lab_a, 9, fill=C["ink"], weight=600))
    o.append(arrow(fid, "vnni", [(346, 182), (px - 2, 182)], C["vnni"], 1.4))
    o.append(lines(350, 162, ["1 register ->", "16 offsets"], 8.5, 11, fill=C["vnni"],
                   weight=600))
    o.append(text(350, 198, "(16 pair rows)", 8.5, fill=C["vnni"], weight=600))
    ptitle = "panel (2,2) #10 = plane + 10 x PANEL_BYTES_1024"
    _w(ptitle, 9.5, 280, where="panel title")
    o.append(text(px + pw / 2, 260, ptitle, 9.5, "middle", weight=600))
    pnote = f"blue column = dword {T} = token {TOKEN}: 16 slots, one per pair of step {S}"
    _w(pnote, 8.5, 310, where="panel note")
    o.append(text(px + pw / 2, 273, pnote, 8.5, "middle", fill=C["muted"]))
    o.append(cite(px + pw, 287, "k_vnni.hpp:26-27, 61-63"))
    boxes.append(("panel (2,2) #10 as 16 pair rows x 16 dwords", "k_vnni.hpp:26-27, 61-63"))
    wy = 296
    o.append(rect(16, wy, 668, 60, "#fff", C["vnni"], 1.2, 5))
    o.append(text(24, wy + 15, "pair_base(plane, s = 2, token = 37) + pair_row_offsets "
                  "lane dp = 3 (worked example)", 10, weight=600, fill=C["vnni"]))
    ex_lines = [
        f"c = 37 / 16 = {C_BLK} ; t = 37 % 16 = {T} ; pair_base = plane + ((2 * 4 + 2) * 256 + 5) * 4 "
        f"= plane + {PAIR_BASE_B} B",
        f"+ lane 3 x DWORD_BYTES_4 = 3 * 16 * 4 = {LANE_B} B -> byte {BYTE} = 2 x index "
        f"{EX['index']} (k_vnni::index, B1)",
    ]
    for s in ex_lines:
        _w(s, 9.5, 650, True, "worked example")
    o.append(lines(24, wy + 31, ex_lines, 9.5, 14, mono=True))
    o.append(cite(680, wy + 56, "k_vnni.hpp:230-232, 243-247"))
    boxes.append(("pair_base(plane, 2, 37) + pair_row_offsets lane 3 (worked example)",
                  "k_vnni.hpp:230-232, 243-247"))
    cap = ("Updates B1: the index map of B1 becomes byte arithmetic. pair_base points at "
           "the token's column t (i % 16) inside panel (s, c), and pair_row_offsets steps down "
           "the panel's 16 pair rows, 64 bytes apart. Together they address the 16 slots "
           "per step that store_row scatters and load_row gathers (B4). The worked example "
           "lands on byte 10452, which is element 5226 of B1.")
    legend = [
        ("box", "white box, ink outline: the function cells pair_base and "
                "pair_row_offsets; name in bold monospace, description in sans-serif"),
        ("vnni", "blue lines: the 16 pair rows (64 B lines) of panel (2,2) #10 in the VNNI "
                 "layout; grey labels +0 B .. +960 B = their line offsets (pair_row_offsets "
                 "lane i = i x 16 dwords = i x 64 B); blue label +192 B = lane dp = 3, the "
                 "worked example's; blue text = the title of the worked-example box"),
        ("solid blue column, ink outline: dword t = 5 of every pair row = the 16 pair "
         "slots of token 37 in step s = 2, the slots pair_base + pair_row_offsets "
         "address", C["vnni"], C["ink"], False, False),
        ("ink frame: the outline of panel (2,2), and of pair row dp = 3, the lane the "
         "worked example lands in", "none", C["ink"], False, False),
        ("white box, blue outline: the worked example's arithmetic, pair_base(plane, 2, "
         "37) + lane 3 = byte 10452", "#fff", C["vnni"], False, False),
        ("ink arrow: pair_base -> the top of the token's column (1 call -> 1 address)",
         "arrow", C["ink"]),
        ("blue arrow: pair_row_offsets -> the panel's 16 pair rows (1 register -> 16 "
         "offsets)", "arrow", C["vnni"]),
        ("font_mono", "monospace = identifiers and values from the code: pair_base, "
                      "pair_row_offsets, the +i x 64 B offsets, the worked example's "
                      "arithmetic"),
        ("font_sans", "sans-serif = prose: the header line, descriptions, callers, the "
                      "panel note"),
        "font_cite",
        ("font_tag", "bold 'new' = pair_base and pair_row_offsets are added by this PR"),
    ]
    return figure(fid, W_, H, "Address arithmetic: pair_base and pair_row_offsets on the "
                  "worked example", "".join(o), cap, boxes=boxes, legend=legend)
