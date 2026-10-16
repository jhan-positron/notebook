"""Change diagrams of unit k5 of the k_vnni.hpp page: the internal helpers
pair_base, pair_row_offsets and transpose_16x16_epi32 (head lines 285-343).

Two figures (one per subject, so each fits beside the code):
  k_vnni-d5a  pair_base + pair_row_offsets: the byte address of one token's
              16 pair slots per step, with the worked example's arithmetic;
  k_vnni-d5b  transpose_16x16_epi32: the 16 token rows of one step become the
              16 pair rows of one panel, in four stages.
Every label comes from the head file or facts/k_vnni.json; line numbers are
head line numbers of h/tron/tensor/k_vnni.hpp. The worked example is the
page's (token 37 = block 2, t = 5; dimension 70 = step 2, pair 3).
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, lines,
                         marker_defs, rect, text, text_width)
from base_k_vnni import EX, panel_lines

BASE = ("Updates B1 and B4: the index map of B1 becomes byte arithmetic (pair_base "
        "points at a token's column t (i % 16) of panel (s, c), pair_row_offsets steps "
        "down the panel's 16 pair rows), and transpose_16x16_epi32 turns the 16 token "
        "rows of one step of B4's block save into those 16 pair rows.")

# worked example numbers, computed as the code does (k_vnni.hpp:292-294, 305-309)
S, TOKEN = EX["s"], EX["token"]                       # 2, 37
C_BLK, T = TOKEN // 16, TOKEN % 16                    # 2, 5
PAIR_BASE_B = ((S * 4 + C_BLK) * 256 + T) * 4         # 10260
DP = EX["dp"]                                         # 3
LANE_B = DP * 16 * 4                                  # 192: lane dp = dp * ROW_DWORDS_16 dwords
BYTE = PAIR_BASE_B + LANE_B                           # 10452
assert BYTE == EX["byte"] == 2 * EX["index"]

W = 700


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def grid16(x, y, cell, fill, stroke, hi_row, hi_col, labels_right=False):
    """A 16 x 16 matrix of 32-bit lanes as 16 registers (rows) of 16 lanes
    (columns): row hi_row gets a thick outline, cell (hi_row, hi_col) is
    solid blue (the worked example's dword)."""
    o = []
    for r in range(16):
        for c in range(16):
            o.append(rect(x + c * cell, y + r * cell, cell, cell, fill, stroke, 0.5, 0))
    o.append(rect(x + hi_col * cell, y + hi_row * cell, cell, cell, C["vnni"], C["ink"],
                  1.0, 0))
    o.append(rect(x, y + hi_row * cell, 16 * cell, cell, "none", C["ink"], 1.6, 0))
    o.append(rect(x, y, 16 * cell, 16 * cell, "none", C["ink"], 0.8, 0))
    # row labels r[0], r[hi], r[15] and lane labels 0, hi, 15
    lx = x + 16 * cell + 4 if labels_right else x - 4
    anc = "start" if labels_right else "end"
    for r in (0, hi_row, 15):
        o.append(text(lx, y + r * cell + 8, f"r[{r}]", 8.5, anc, True,
                      fill=C["ink"] if r == hi_row else C["muted"]))
    o.append(text(lx, y - 4, "lane", 8.5, anc, fill=C["muted"]))
    for c in (0, hi_col, 15):
        o.append(text(x + c * cell + cell / 2, y - 4, str(c), 8.5, "middle", True,
                      fill=C["ink"] if c == hi_col else C["muted"]))
    return "".join(o)


# ---------------------------------------------------------------------------
# d5a: the byte address of one token's pair slots


def _fig_a():
    fid = "k_vnni-d5a"
    W_, H = W, 370
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    hdr = ("the three internal helpers of namespace k_vnni::detail; worked example: "
           "token 37 (block 2, t = 5), step s = 2, pair dp = 3")
    _w(hdr, 9.5, W - 32, where="d5a header")
    o.append(text(16, 14, hdr, 9.5, fill=C["muted"]))
    o.append(text(16, 32, "A. pair_base + pair_row_offsets: the byte address of one token's "
                  "16 pair slots per step", 11, weight=700))
    cw, ch = 330, 70
    cells = [
        (52, "pair_base(plane, s, token)",
         ["Byte address of dimension pair 0 of step s for a token:",
          "panel (s, c) plus the token's column t (i % 16)",
          "-> char* / const char*: plane + ((s * 4 + c) * 256 + t) * 4"],
         "k_vnni.hpp:290-301",
         ["callers: store_row 359, load_row 377:",
          "DIM_STEPS_4 = 4 calls per row (one per step s)"]),
        (148, "pair_row_offsets()",
         ["Dword offsets of the 16 pair rows of one panel",
          "(64 bytes = 16 dwords apart): the scatter / gather index",
          "-> __m512i: lane i = i * ROW_DWORDS_16 = 0, 16, ..., 240"],
         "k_vnni.hpp:303-310",
         ["callers: store_row 356, load_row 374:",
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
    # the panel zoom: panel (2,2) #10 as 16 lines, column t = 5 marked
    px, py, pw, ph = 428, 70, 224, 176
    o.append(panel_lines(px, py, pw, ph, ["vnni"] * 16, hi_rows=[DP], col=T))
    o.append(text(px + pw + 4, py - 6, "lane i", 8.5, fill=C["muted"]))
    for i in range(16):
        o.append(text(px + pw + 4, py + i * 11 + 8, f"+{i * 64} B", 8.5, mono=True,
                      fill=C["vnni"] if i == DP else C["muted"]))
    col_x = px + T * (pw / 16) + pw / 32
    # arrow (a): pair_base -> the top of column t = 5
    o.append(arrow(fid, "ink", [(346, 72), (372, 72), (372, 50), (col_x, 50), (col_x, py - 2)],
                   C["ink"], 1.4))
    lab_a = f"1 call -> 1 address: plane + {PAIR_BASE_B} B = dword {T} of pair row 0"
    _w(lab_a, 9, 700 - 378, where="label a")
    o.append(text(378, 45, lab_a, 9, fill=C["ink"], weight=600))
    # arrow (b): pair_row_offsets -> the 16 lines of the panel
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
    o.append(cite(px + pw, 287, "k_vnni.hpp:29-30, 75-77"))
    boxes.append(("panel (2,2) #10 as 16 pair rows x 16 dwords", "k_vnni.hpp:29-30, 75-77"))
    # worked example box
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
    o.append(cite(680, wy + 56, "k_vnni.hpp:291-294, 305-309"))
    boxes.append(("pair_base(plane, 2, 37) + pair_row_offsets lane 3 (worked example)",
                  "k_vnni.hpp:291-294, 305-309"))
    cap = ("Updates B1: the index map of B1 becomes byte arithmetic. pair_base points at "
           "the token's column t (i % 16) inside panel (s, c), and pair_row_offsets steps down "
           "the panel's 16 pair rows, 64 bytes apart. Together they address the 16 slots "
           "per step that store_row scatters and load_row gathers. The worked example "
           "lands on byte 10452, which is element 5226 of B1.")
    # the colour and font scheme of this figure (only the styles it uses)
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


# ---------------------------------------------------------------------------
# d5b: the 16 x 16 transpose


def _fig_b():
    fid = "k_vnni-d5b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    o.append(text(16, 16, "B. transpose_16x16_epi32: 16 token rows of one step become the 16 "
                  "pair rows of one panel", 11, weight=700))
    cw, ch, ty = 330, 70, 26
    tdesc = ["In-place transpose of 16 x 16 dwords: on return r[i]",
             "holds lane i of every input register; 4 stages, 64 shuffles",
             "-> void: r[0..15] rewritten in place (t[16] is the scratch)"]
    for d in tdesc:
        _w(d, 9.5, cw - 16, where="desc transpose")
    o.append(fn_cell(16, ty, cw, ch, "transpose_16x16_epi32(r)", tdesc, "k_vnni.hpp:314-341",
                     "new"))
    boxes.append(("transpose_16x16_epi32(r)", "k_vnni.hpp:314-341"))
    sdesc = ["per step s: 16 row loads (64 B each, zero for an",
             "absent token), the transpose, then 16 whole-line",
             "stores of r[dp] to panel (s, c), pair row dp"]
    for d in sdesc:
        _w(d, 9.5, 304 - 16, where="desc store_block")
    o.append(fn_cell(380, ty, 304, ch, "store_block (the caller)", sdesc,
                     "k_vnni.hpp:396-413", "new"))
    boxes.append(("store_block (the caller)", "k_vnni.hpp:396-413"))
    # the call arrow from store_block back into transpose_16x16_epi32: the
    # horizontal segment 10 px under the cells, its label 12 px under the line
    bot = ty + ch
    ly = bot + 10
    o.append(arrow(fid, "ink", [(448, bot), (448, ly), (180, ly), (180, bot + 2)],
                   C["ink"], 1.4))
    o.append(text(190, ly + 12, "DIM_STEPS_4 = 4 calls per block (one per step s)", 8.5,
                  fill=C["ink"], weight=600))
    o.append(text(458, ly + 12, "[k_vnni.hpp:401, 408]", 8.5, mono=True, fill=C["cite"]))
    # before / after grids
    gy, cell = ly + 54, 10
    gx1, gx2 = 56, 430
    o.append(lines(gx1, gy - 26, ["r[t] before the transpose: the 16 dimension",
                                  "pairs of token t at step s (one 64 B row load)"], 9, 11,
                   fill=C["rm"], weight=700))
    o.append(grid16(gx1, gy, cell, C["rm_fill"], C["rm"], T, DP))
    o.append(lines(gx2, gy - 26, ["r[dp] after the transpose: pair row dp of",
                                  "panel (s, c); lane t = token t; one 64 B line"], 9, 11,
                   fill=C["vnni"], weight=700))
    o.append(grid16(gx2, gy, cell, C["vnni_fill"], C["vnni"], DP, T, labels_right=True))
    mid = gy + 8 * cell
    o.append(arrow(fid, "vnni", [(gx1 + 16 * cell + 6, mid), (gx2 - 6, mid)], C["vnni"], 1.6))
    o.append(text((gx1 + 16 * cell + gx2) / 2, mid - 10, "16 registers -> 16 registers, in place",
                  9, "middle", fill=C["vnni"], weight=600))
    o.append(text((gx1 + 16 * cell + gx2) / 2, mid + 16, "4 stages x 16 shuffles = 64", 8.5,
                  "middle", fill=C["muted"]))
    o.append(text((gx1 + 16 * cell + gx2) / 2, mid + 28, "[k_vnni.hpp:311-313]", 8.5,
                  "middle", True, fill=C["cite"]))
    cy = gy + 16 * cell + 16
    c1 = f"r[{T}], lane {DP} = dims 70, 71 of token 37 (t = {T}, dp = {DP})"
    c2 = f"r[{DP}], lane {T} = the same dword: pair row {DP}, dword {T}"
    _w(c1, 9, gx2 - gx1 - 10, where="callout 1")
    _w(c2, 9, 700 - gx2, where="callout 2")
    o.append(text(gx1, cy, c1, 9, fill=C["ink"]))
    o.append(text(gx2, cy, c2, 9, fill=C["ink"]))
    o.append(cite(gx1 + 16 * cell + 60, cy + 14, "k_vnni.hpp:311-313, 403-407"))
    boxes.append(("r[t] before the transpose (input register t in lane t)",
                  "k_vnni.hpp:311-313; 403-407"))
    o.append(cite(gx2 + 16 * cell + 60, cy + 14, "k_vnni.hpp:311-313, 411-412"))
    boxes.append(("r[i] after the transpose (lane i of every input register): r[dp] = pair row dp",
                  "k_vnni.hpp:311-313; 411-412"))
    # the four stages
    sy = cy + 32
    o.append(text(16, sy, "the four stages: 16 two-register shuffles each, 64 in all", 10,
                  weight=700))
    stages = [
        ("_mm512_unpacklo_epi32 (stage 1)",
         ["+ _mm512_unpackhi_epi32: register pairs r[2 i], r[2 i + 1]",
          "-> t[2 i], t[2 i + 1]: 16 shuffles"],
         "k_vnni.hpp:321-324", "_mm512_unpacklo_epi32 / _mm512_unpackhi_epi32 (stage 1)"),
        ("_mm512_unpacklo_epi64 (stage 2)",
         ["+ _mm512_unpackhi_epi64: t[4 i] with t[4 i + 2], t[4 i + 1] with",
          "t[4 i + 3] -> r[4 i .. 4 i + 3]: 16 shuffles"],
         "k_vnni.hpp:325-330", "_mm512_unpacklo_epi64 / _mm512_unpackhi_epi64 (stage 2)"),
        ("_mm512_shuffle_i32x4 (stage 3)",
         ["r[i] with r[i + 4], r[i + 8] with r[i + 12] -> t: even 128-bit",
          "quarters (EVEN_QUARTERS_0X88) or odd (ODD_QUARTERS_0XDD): 16"],
         "k_vnni.hpp:331-336", "_mm512_shuffle_i32x4 (stage 3: even or odd quarters -> t)"),
        ("_mm512_shuffle_i32x4 (stage 4)",
         ["t[i] with t[i + 8] -> r[i] (EVEN_QUARTERS_0X88) and r[i + 8]",
          "(ODD_QUARTERS_0XDD): 16 shuffles; r now holds the pair rows"],
         "k_vnni.hpp:337-340", "_mm512_shuffle_i32x4 (stage 4: t -> r)"),
    ]
    for i, (title, sub, ref, reg) in enumerate(stages):
        x = 16 + (i % 2) * 338
        y = sy + 8 + (i // 2) * 72
        _w(title, 10, 322, True, f"stage title {i}")
        for s in sub:
            _w(s, 9, 322, where=f"stage sub {i}")
        o.append(label_box(x, y, 330, 64, title, sub, C["soft"], C["ink"], 10, ref=ref))
        boxes.append((reg, ref))
    H = sy + 8 + 2 * 72 + 2
    cap = ("Updates B4: transpose_16x16_epi32 turns the 16 token rows of one dimension step "
           "(orange, loaded by store_block from native rows) into the 16 pair rows of one "
           "panel (blue) in four stages of 16 shuffles. Follow the solid blue cell, token "
           "37's pair 3, from register 5 lane 3 to register 3 lane 5.")
    # the colour and font scheme of this figure (only the styles it uses)
    legend = [
        ("box", "white box, ink outline: the function cells transpose_16x16_epi32 and "
                "store_block (the caller); name in bold monospace, description in "
                "sans-serif"),
        ("rm", "orange (grid and labels): r[0..15] before the transpose, the 16 token rows "
               "of one step s that store_block loads (64 B each), 16 lanes per register"),
        ("vnni", "blue (grid and labels): r[0..15] after the transpose, the 16 pair rows "
                 "of panel (s, c) in the VNNI layout, lane t = token t"),
        ("solid blue cell, ink outline: the worked example's dword, dims 70, 71 of token "
         "37: r[5] lane 3 before, r[3] lane 5 after", C["vnni"], C["ink"], False, False),
        ("ink frame: the outline of each 16 x 16 grid, and of the worked example's "
         "register, r[5] before and r[3] after", "none", C["ink"], False, False),
        ("ctx_ink", "grey fill, ink outline: the four stages of the transpose, the "
                    "intrinsic each stage uses and its 16 shuffles"),
        ("ink arrow: store_block -> transpose_16x16_epi32 (DIM_STEPS_4 = 4 calls per "
         "block)", "arrow", C["ink"]),
        ("blue arrow: the 16 registers before -> the 16 registers after, in place",
         "arrow", C["vnni"]),
        ("font_mono", "monospace = identifiers and values from the code: "
                      "transpose_16x16_epi32, store_block, r[i], the intrinsic names, "
                      "the stage line ranges"),
        ("font_sans", "sans-serif = prose: descriptions, the grid titles, the callouts "
                      "under the grids, the stage notes"),
        "font_cite",
        ("font_tag", "bold 'new' = transpose_16x16_epi32 and store_block are added by "
                     "this PR"),
    ]
    return figure(fid, W, H, "The 16 x 16 register transpose of one dimension step",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
