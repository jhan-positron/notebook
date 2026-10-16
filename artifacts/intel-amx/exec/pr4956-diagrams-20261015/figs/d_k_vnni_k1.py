"""Change diagrams of unit k1 of the PR 4956 k_vnni.hpp page: the layout
constants, the two static_asserts and the index map (head lines 52-84, 97-108).

Two figures:
  k_vnni-d1a  the constants of lines 56-77 drawn on the plane geometry of the
              worked example, and the two static_asserts of lines 78-84.
  k_vnni-d1b  index(37, 70) traced to element 5226, and who reads index,
              BF16_BITS_16 and HIGH_HALF_0XFFFF0000.
Line numbers are head lines of h/tron/tensor/k_vnni.hpp (PR 4956,
a5697f86d3) unless another file is named.
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, label_box, line,
                         lines, marker_defs, rect, text, text_width)
from base_k_vnni import EX, BLOCK_2, panel_grid, panel_lines, pair_row_dwords

BASE = ("Updates B1: every count of the plane in B1 (tokens, blocks, steps, pairs, "
        "lines, panels) gets its named constant, and the static_assert at lines 78-82 "
        "pins the 10 derived constants. The second figure (d1b) updates B1 and the "
        "first cells of B3: index(37, 70) = 5226 is traced step by step, with the "
        "readers of index and of the two bf16 bit constants.")

W = 720

PANEL = EX["s"] * 4 + EX["c"]                       # 10
PAIR_ROW = PANEL * 16 + EX["dp"]                    # 163
DWORD = PAIR_ROW * 16 + EX["t"]                     # 2613
ELEM = DWORD * 2 + EX["j"]                          # 5226
assert ELEM == EX["index"] == 5226 and DWORD * 4 == EX["byte"] == 10452


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _lines(o, x, y, items, size, lh, w, fill=None, where="", mono=False, weight=None):
    for s in items:
        _w(s, size, w, mono, where)
    o.append(lines(x, y, items, size, lh, mono=mono, fill=fill, weight=weight))


# ---------------------------------------------------------------------------
# d1a: the constants on the plane geometry, and the static_asserts


def _fig_a():
    fid = "k_vnni-d1a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    o.append(text(20, 16, "the constants of lines 56-77 drawn on the plane of the worked "
                  "example (slot 5, KV head 0, page 7)", 10.5, weight=700))
    o.append(text(20, 30, "every count on the figure is a named constant; the two checks "
                  "at the bottom are the static_asserts of lines 78-84", 9.5, fill=C["muted"]))
    # ---- left column: the plane as its 16 panels ----------------------------
    o.append(text(20, 50, "plane = PAGE_TOKENS_64 x HEAD_SIZE_128 bf16", 10,
                  weight=600, fill=C["vnni"]))
    o.append(cite(20, 62, "k_vnni.hpp:21-25, 56-57", "start"))
    boxes.append(("plane = PAGE_TOKENS_64 x HEAD_SIZE_128 bf16", "k_vnni.hpp:21-25, 56-57"))
    o.append(text(20, 75, "TOKEN_BLOCKS_4 = 4 token blocks (c) of BLOCK_TOKENS_16", 9.5))
    gx, gy, cw, ch = 20, 94, 36, 30
    o.append(panel_grid(gx, gy, cw, ch, hi=(EX["s"], EX["c"]), block=BLOCK_2))
    boxes.append(("token block 2 (framed): BLOCK_TOKENS_16 tokens", "k_vnni.hpp:27-29, 63-64"))
    _lines(o, 20, 244, [
        "DIM_STEPS_4 = 4 steps (s) x STEP_DIMS_32 dims",
        "N_PANELS_16 = DIM_STEPS_4 x TOKEN_BLOCKS_4 panels",
        "block 2 (framed): BLOCK_TOKENS_16 tokens, offsets 32..47",
        "panel (2,2) #10 (blue): zoomed at the right"], 9.5, 12, 322, where="a left")
    o.append(cite(20, 294, "k_vnni.hpp:63-67, 73", "start"))
    boxes.append(("DIM_STEPS_4 steps of STEP_DIMS_32", "k_vnni.hpp:65-67"))
    boxes.append(("N_PANELS_16 = DIM_STEPS_4 x TOKEN_BLOCKS_4", "k_vnni.hpp:73"))
    cell_y = gy + EX["s"] * (ch + 4) + ch / 2
    o.append(arrow(fid, "vnni", [(212, cell_y), (341, cell_y)], C["vnni"], 1.4))
    o.append(lines(214, cell_y - 34, ["1 panel ->", "STEP_PAIRS_16 pair rows"], 8.5, 10,
                   fill=C["vnni"], weight=600))
    o.append(text(214, cell_y - 12, "[k_vnni.hpp:66, 70]", 8.5, mono=True, fill=C["cite"]))
    # ---- right column: panel #10 in its VNNI form --------------------------
    px, py, pw, ph = 345, 94, 140, 128
    o.append(text(px, 50, "panel (2,2) #10: STEP_PAIRS_16 pair rows", 10,
                  weight=600, fill=C["vnni"]))
    o.append(cite(px, 62, "k_vnni.hpp:26-27, 70-73", "start"))
    boxes.append(("panel (2,2) #10", "k_vnni.hpp:26-27, 70-73"))
    o.append(panel_lines(px, py, pw, ph, ["vnni"] * 16, hi_rows=[EX["dp"]]))
    for dp, yy in ((0, 0), (EX["dp"], EX["dp"]), (15, 15)):
        o.append(text(px - 4, py + yy * 8 + 7, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if dp == EX["dp"] else C["muted"]))
    _lines(o, px + pw + 10, 104, [
        "STEP_PAIRS_16 = 16 pair rows",
        "x LINE_BYTES_64 bytes each",
        "= PANEL_BYTES_1024 = 1 KiB",
        "= PANEL_ELEMS_512 bf16",
        "= PANEL_DWORDS_256 dwords",
        "thick row: pair row dp 3"], 9.5, 12, 200, where="a vnni labels")
    o.append(cite(px + pw + 10, 177, "k_vnni.hpp:62, 66, 70-72", "start"))
    boxes.append(("STEP_PAIRS_16 pair rows x LINE_BYTES_64 = PANEL_BYTES_1024",
                  "k_vnni.hpp:62, 66, 70-72"))
    # ---- the pair row and one dword ------------------------------------------
    o.append(card_arrow(fid, "vnni", [(415, 226), (415, 258)], C["vnni"],
                        "1 pair row -> ROW_DWORDS_16 dwords", 8, 0, anchor="start"))
    o.append(text(423, 254, "[k_vnni.hpp:61-63, 68-69]", 8.5, mono=True, fill=C["cite"]))
    rx, ry = 345, 262
    o.append(pair_row_dwords(rx, ry, 320, 24, hi_t=EX["t"], base_token=32))
    s = "pair row dp 3: ROW_DWORDS_16 dwords (ROW_ELEMS_32 bf16)"
    _w(s, 9, 360, where="a pair row title")
    o.append(text(rx, 309, s, 9, weight=600, fill=C["vnni"]))
    boxes.append(("pair row dp 3 of panel #10", "k_vnni.hpp:61-63, 68-69"))
    dx, dy, dw, dh = 345, 318, 240, 28
    o.append(rect(dx, dy, dw / 2, dh, C["vnni_fill"], C["vnni"], 1.2, 0))
    o.append(rect(dx + dw / 2, dy, dw / 2, dh, "#fff", C["vnni"], 1.2, 0))
    o.append(text(dx + dw / 4, dy + 12, "low half, j = 0", 9, "middle"))
    o.append(text(dx + dw / 4, dy + 23, "dim 70 (even)", 9, "middle", True))
    o.append(text(dx + 3 * dw / 4, dy + 12, "high half, j = 1", 9, "middle"))
    o.append(text(dx + 3 * dw / 4, dy + 23, "dim 71 (odd)", 9, "middle", True))
    _lines(o, dx + dw + 10, dy + 11, ["dword 5 = token 37:", "DWORD_BYTES_4 bytes",
                                      "= PAIR_2 bf16"], 9, 10, 100, where="a dword")
    o.append(cite(dx + dw + 10, dy + 42, "k_vnni.hpp:58-60", "start"))
    boxes.append(("dword 5 = token 37: DWORD_BYTES_4 bytes = PAIR_2 bf16",
                  "k_vnni.hpp:58-60"))
    _lines(o, dx, 364, [
        "even value << BF16_BITS_16 = the exact fp32",
        "odd value & HIGH_HALF_0XFFFF0000 = an fp32 bit pattern",
        "read only by k_vnni::qk_group's float-query path",
        "(kernels/k_vnni.hpp:79-82); no reader in this file"], 9.5, 12, 350,
        fill=C["ink"], where="a bf16 bits")
    o.append(cite(dx, 414, "k_vnni.hpp:74-77", "start"))
    boxes.append(("BF16_BITS_16, HIGH_HALF_0XFFFF0000", "k_vnni.hpp:74-77"))
    # ---- left column, row 2: the 6 literal definitions ------------------------
    o.append(text(20, 318, "the 6 literals: definitions, no static_assert names them", 10,
                  weight=600))
    _lines(o, 20, 334, [
        "PAGE_TOKENS_64 = 64 (56), HEAD_SIZE_128 = 128 (57)",
        "PAIR_2 = 2 (59), DWORD_BYTES_4 = 4 (60)",
        "LINE_BYTES_64 = 64 (62), STEP_DIMS_32 = 32 (65)",
        "every other constant is derived from these six",
        "(BLOCK_TOKENS_16 = LINE_BYTES_64 / (PAIR_2 * 2), ...)"], 9.5, 12, 322,
        where="a literals")
    o.append(cite(20, 396, "k_vnni.hpp:56-73", "start"))
    boxes.append(("PAGE_TOKENS_64, HEAD_SIZE_128, PAIR_2, DWORD_BYTES_4, LINE_BYTES_64, "
                  "STEP_DIMS_32 (the 6 literals)", "k_vnni.hpp:56-65"))
    # ---- the checks: static_asserts -----------------------------------------
    o.append(line(20, 430, 700, 430, C["line"]))
    o.append(text(20, 448, "the checks: static_asserts between the constants (lines 78-84)",
                  11, weight=700))
    sub1 = ["10 derived constants pinned to their number: BLOCK_TOKENS_16 == 16, "
            "TOKEN_BLOCKS_4 == 4, STEP_PAIRS_16 == 16,",
            "DIM_STEPS_4 == 4, ROW_ELEMS_32 == 32, ROW_DWORDS_16 == 16, PANEL_ELEMS_512 == 512, "
            "PANEL_BYTES_1024 == 1024,",
            "PANEL_DWORDS_256 == 256, N_PANELS_16 == 16"]
    for s in sub1:
        _w(s, 9, 600, where="a check 1")
    o.append(label_box(20, 458, 680, 76, 'static_assert "every constant\'s name states its value"',
                       sub1, "#fff", C["ink"], 10, ref="k_vnni.hpp:78-82"))
    boxes.append(('static_assert "every constant\'s name states its value"', "k_vnni.hpp:78-82"))
    cy = 556
    o.append(text(20, cy, 'static_assert "the VNNI plane is a permutation of the row-major '
                  'plane: same element count"', 10, weight=600))
    o.append(cite(700, cy, "k_vnni.hpp:83-84"))
    boxes.append(('static_assert "the VNNI plane is a permutation of the row-major plane: '
                  'same element count"', "k_vnni.hpp:83-84"))
    o.append(label_box(20, cy + 8, 300, 50, "N_PANELS_16 x PANEL_ELEMS_512",
                       ["16 panels x 512 bf16 = 8192 (the VNNI plane)"],
                       C["vnni_fill"], C["vnni"], 10.5, ref="k_vnni.hpp:70, 73"))
    boxes.append(("N_PANELS_16 x PANEL_ELEMS_512 (the VNNI plane)", "k_vnni.hpp:70, 73"))
    boxes.append(("PAGE_TOKENS_64 x HEAD_SIZE_128 (the row-major plane)", "k_vnni.hpp:56-57"))
    o.append(text(360, cy + 36, "==", 14, "middle", True, weight=700))
    o.append(label_box(400, cy + 8, 300, 50, "PAGE_TOKENS_64 x HEAD_SIZE_128",
                       ["64 tokens x 128 dims = 8192 (the row-major plane)"],
                       C["rm_fill"], C["rm"], 10.5, ref="k_vnni.hpp:56-57"))
    H = cy + 66
    cap = ("Updates B1: every count of the plane in B1 is now a named constant of lines "
           "56-77, drawn here on the plane of the worked example (page 7, storage slot 5, "
           "KV head 0). Six literals define the geometry, and every other constant is "
           "derived from them. Panel #10 is STEP_PAIRS_16 pair rows of LINE_BYTES_64 "
           "bytes = PANEL_BYTES_1024. The two checks at the bottom are the static_asserts "
           "that tie the constants together: each derived constant's name states its "
           "value, and the VNNI plane has the same element count as the row-major plane.")
    legend = [
        ("vnni", "blue: the VNNI form. Panel (2,2) #10 as the grid cell and as its 16 pair "
                 "rows, dword 5 (token 37) and its low half, and the VNNI-plane box of the "
                 "second check (N_PANELS_16 x PANEL_ELEMS_512). Blue headings and labels "
                 "name the VNNI form"),
        ("white box, blue outline: the high half of dword 5 (j = 1, dim 71)",
         "#fff", C["vnni"], False, False),
        ("rm", "orange: the row-major plane of the second check (PAGE_TOKENS_64 x "
               "HEAD_SIZE_128), the same element count"),
        ("lane", "white cell, thin grey outline: a panel of the grid other than (2,2) #10, "
                 "and a dword of pair row dp 3 other than token 37's"),
        ("ink outline, no fill: the frame of token block 2 in the grid, pair row dp 3 of "
         "the zoomed panel, and the border of the zoomed panel", "none", C["ink"], False,
         False),
        ("box", "white box, ink outline: the static_assert of lines 78-82. "
                "Name in bold monospace, description in grey sans-serif"),
        ("blue arrow: a how-many arrow, 1 panel -> STEP_PAIRS_16 pair rows and 1 pair row "
         "-> ROW_DWORDS_16 dwords", "arrow", C["vnni"]),
        ("font_mono", "monospace = the constant names in the titles of the check boxes "
                      "and of the static_assert box, the panel indexes (s, c) and #n, the "
                      "dp, token and dim labels, and the '==' of the check"),
        ("font_sans", "sans-serif = the figure title, the drawing titles, the constant "
                      "relations beside the drawings, the literals list, the half-dword "
                      "notes and the check descriptions"),
        ("font_cite", "small grey monospace = the lines that define a drawing, a constant "
                      "or a check (file:line)"),
    ]
    return figure(fid, W, H, "The layout constants drawn on the plane geometry, and the "
                  "static_asserts that relate them", "".join(o), cap, boxes=boxes,
                  legend=legend)


# ---------------------------------------------------------------------------
# d1b: the index map traced for the worked example, and its readers


def _fig_b():
    fid = "k_vnni-d1b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    o.append(text(20, 16, "k_vnni::index(token, dim): the header formula as code, traced for "
                  "token 37, dim 70 (worked example)", 11, weight=700))
    boxes.append(("k_vnni::index(token, dim)", "k_vnni.hpp:97-106"))
    o.append(fn_cell(20, 26, 680, 60, "k_vnni::index(token, dim)",
                     ["Element index of K[token][dim] inside the plane (the formula of the "
                      "header comment, lines 24-25);",
                      "constexpr, so a STATIC_REQUIRE can check it"], "k_vnni.hpp:97-106", "new"))
    _lines(o, 20, 104, [
        f"s = 70 / STEP_DIMS_32 = {EX['s']} ; c = 37 / BLOCK_TOKENS_16 = {EX['c']} ; "
        f"dp = (70 % STEP_DIMS_32) / PAIR_2 = {EX['dp']}",
        f"t = 37 % BLOCK_TOKENS_16 = {EX['t']} ; j = 70 % PAIR_2 = {EX['j']}"],
        9.5, 13, 680, mono=True, where="b coords")
    o.append(cite(20, 129, "k_vnni.hpp:100-102", "start"))
    bw, bh, by2 = 145, 64, 140
    chain = [
        (f"panel #{PANEL}", ["s x TOKEN_BLOCKS_4 + c", f"= 2 x 4 + 2 = {PANEL}"],
         "k_vnni.hpp:26-27, 103", f"panel #{PANEL} = s * TOKEN_BLOCKS_4 + c (line 103)"),
        (f"pair row {PAIR_ROW} of 256", [f"{PANEL} x STEP_PAIRS_16", f"+ dp 3 = {PAIR_ROW}"],
         "k_vnni.hpp:61-63, 103",
         f"pair row {PAIR_ROW} of 256 = panel * STEP_PAIRS_16 + dp (line 103)"),
        (f"dword {DWORD} of 4096", [f"{PAIR_ROW} x BLOCK_TOKENS_16", f"+ t 5 = {DWORD}"],
         "k_vnni.hpp:61-63, 103",
         f"dword {DWORD} of 4096 = pair row * BLOCK_TOKENS_16 + t (line 103)"),
        (f"index = {ELEM}", [f"{DWORD} x PAIR_2 + 0 = {ELEM}", f"x 2 B/bf16 = byte {EX['byte']}"],
         "k_vnni.hpp:103-105", f"index = {ELEM} = dword * PAIR_2 + j (lines 103-105)"),
    ]
    labels = ["x STEP_PAIRS_16 + dp", "x BLOCK_TOKENS_16 + t", "x PAIR_2 + j"]
    for i, (title, sub, ref, reg) in enumerate(chain):
        x = 20 + i * (bw + 32)
        for s in sub:
            _w(s, 9.5, bw - 8, where=f"b chain {title}")
        o.append(label_box(x, by2, bw, bh, title, sub, C["vnni_fill"], C["vnni"], 10.5,
                           ref=ref))
        boxes.append((reg, ref))
        if i < 3:
            o.append(card_arrow(fid, "vnni", [(x + bw + 2, by2 + bh / 2), (x + bw + 30, by2 + bh / 2)],
                                C["vnni"], labels[i], 0, -(bh / 2 + 6), size=9))
    # ---- the readers ------------------------------------------------------------
    ry = by2 + bh + 30
    o.append(line(20, ry - 12, 700, ry - 12, C["line"]))
    o.append(text(20, ry + 4, "who reads index, and who reads the two bf16 bit constants", 11,
                  weight=700))
    cw, ch = 335, 60
    o.append(fn_cell(20, ry + 14, cw, ch, "k_vnni_view::at(token, dim)",
                     ["Bounds-checked read: data_[k_vnni::index(token, dim)];",
                      "the one production reader of index"],
                     "k_vnni.hpp:135-140", "new"))
    boxes.append(("k_vnni_view::at(token, dim)", "k_vnni.hpp:135-140"))
    _lines(o, 22, ry + 85, ["worked example: at(37, 70) = data_[5226]",
                            "the test reads every (token, dim) back through at() (141)"],
           9, 10.5, cw, fill=C["muted"], where="b at readers")
    o.append(label_box(365, ry + 14, cw, ch, "t_k_vnni_layout.cpp (tests of index)",
                       ["STATIC_REQUIRE anchors: index(0, 0) == 0 .. (93-104);",
                        "the stored bytes agree with index() (131, 164, 183)"],
                       C["soft"], C["ink"], 10.5, ref="t_k_vnni_layout.cpp:90-104, 131"))
    boxes.append(("t_k_vnni_layout.cpp (tests of index)", "t_k_vnni_layout.cpp:90-104, 131, 164, 183"))
    _lines(o, 367, ry + 85, ["store_row does not use index(): the agreement ties the",
                             "scatter addresses to the index map (130-131)"],
           9, 10.5, cw, fill=C["muted"], where="b test readers")
    r2 = ry + 112
    o.append(label_box(20, r2, cw, ch, "BF16_BITS_16",
                       ["int 16: a bf16 shifted up by this many bits is the",
                        "exact fp32 (new)"], "#fff", C["ink"], 11, ref="k_vnni.hpp:74-75"))
    boxes.append(("BF16_BITS_16", "k_vnni.hpp:74-75"))
    _lines(o, 22, r2 + 71, ["reader: k_vnni::qk_group, float query: k_even =",
                            "_mm512_slli_epi32(k_pairs, BF16_BITS_16) (kernels/k_vnni.hpp:79-80)"],
           9, 10.5, cw, fill=C["muted"], where="b bf16 readers")
    o.append(label_box(365, r2, cw, ch, "HIGH_HALF_0XFFFF0000",
                       ["uint32_t 0xffff0000: the odd value of a dimension pair",
                        "as an fp32 bit pattern (new)"], "#fff", C["ink"], 11,
                       ref="k_vnni.hpp:76-77"))
    boxes.append(("HIGH_HALF_0XFFFF0000", "k_vnni.hpp:76-77"))
    _lines(o, 367, r2 + 71, ["reader: k_vnni::qk_group, float query: k_odd =",
                             "_mm512_and_si512(k_pairs, HIGH_HALF_0XFFFF0000) (81-82)"],
           9, 10.5, cw, fill=C["muted"], where="b high readers")
    H = r2 + 100
    cap = ("Updates B1 (and the first cells of B3): k_vnni::index(37, 70) is traced through "
           "its four nested steps to element 5226 (byte 10452), the number B1 prints. "
           "Below, the readers: k_vnni_view::at is the one production reader of index, "
           "the layout test pins the formula with compile-time anchors and checks that "
           "the bytes store_row writes agree with it, and the two bf16 bit constants "
           "serve only the float-query path of the score reader in kernels/k_vnni.hpp.")
    legend = [
        ("vnni", "blue: the four steps of k_vnni::index(37, 70), panel #10, pair row 163, "
                 "dword 2613, index 5226"),
        ("box", "white box, ink outline: k_vnni::index, k_vnni_view::at, BF16_BITS_16 and "
                "HIGH_HALF_0XFFFF0000. Name in bold monospace, description in sans-serif"),
        ("ctx_ink", "grey fill, ink outline: the layout test's anchors and checks of index"),
        ("blue arrow: one step of index(37, 70). Its label is the multiply-add of that "
         "step (x STEP_PAIRS_16 + dp, x BLOCK_TOKENS_16 + t, x PAIR_2 + j)",
         "arrow", C["vnni"]),
        ("font_mono", "monospace = the five coordinates, the four index steps with their "
                      "values, and the names of the readers"),
        ("font_sans", "sans-serif = the figure title, what each cell does, and the "
                      "readers lists"),
        ("font_cite", "small grey monospace = the lines that define a cell or an index step "
                      "(file:line)"),
        ("font_tag", "bold 'new' = k_vnni::index and k_vnni_view::at are added by this PR"),
    ]
    return figure(fid, W, H, "index(37, 70) traced to element 5226, and the readers of "
                  "index and of the bf16 bit constants", "".join(o), cap,
                  boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
